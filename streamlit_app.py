from __future__ import annotations

import time

import streamlit as st

from graphs.interview_graph import continue_interview, start_interview
from services.ats import analyse_resume
from services.auth import authenticate_user, register_user
from services.database import (DatabaseConfigurationError, create_interview, init_database,
                               list_interviews, load_interview, progress_summary, save_resume,
                               update_interview)
from services.report_pdf import generate_interview_report
from services.resume_parser import extract_resume_text


ROLES = ["Data Analyst", "Data Scientist", "Business Analyst", "AI Engineer", "Data Engineer"]
STYLES = ["Technical", "Behavioral", "Case study", "Mixed"]

st.set_page_config(page_title="Get interview ready with AI", page_icon="🎯", layout="wide")
st.title("🎯 Get interview ready with AI")
st.caption("Persistent AI interview coaching powered by Groq, LangGraph, and PostgreSQL")

try:
    init_database()
except Exception as exc:
    st.error(f"Database setup failed: {exc}")
    st.info("Set DATABASE_URL, DATA_ENCRYPTION_KEY, and LANGGRAPH_AES_KEY in .env, then start PostgreSQL with `docker compose up -d`.")
    st.stop()

for key, default in {"user_id": None, "user_email": None, "ats_report": None, "resume_text": "", "resume_id": None, "job_description": "", "interview": None, "active_interview_id": None, "interview_started_at": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    if not st.session_state.user_id:
        st.header("Account")
        auth_tab, signup_tab = st.tabs(["Sign in", "Create account"])
        with auth_tab:
            with st.form("signin"):
                email = st.text_input("Email", key="signin_email")
                password = st.text_input("Password", type="password", key="signin_password")
                submitted = st.form_submit_button("Sign in", type="primary")
            if submitted:
                user = authenticate_user(email, password)
                if user:
                    st.session_state.user_id = user.id
                    st.session_state.user_email = user.email
                    st.rerun()
                st.error("Invalid email or password.")
        with signup_tab:
            with st.form("signup"):
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_password")
                submitted = st.form_submit_button("Create account")
            if submitted:
                try:
                    user = register_user(email, password)
                    st.session_state.user_id = user.id
                    st.session_state.user_email = user.email
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        st.stop()

    st.success(f"Signed in as {st.session_state.user_email}")
    if st.button("Sign out"):
        for key in ["user_id", "user_email", "ats_report", "resume_text", "resume_id", "job_description", "interview", "active_interview_id", "interview_started_at"]:
            st.session_state[key] = None if key not in {"resume_text", "job_description"} else ""
        st.rerun()
    st.divider()
    st.header("Interview setup")
    role = st.selectbox("Target role", ROLES)
    difficulty = st.selectbox("Experience level", ["Junior", "Mid-level", "Senior"])
    style = st.selectbox("Interview style", STYLES)
    st.caption("Sensitive records are encrypted before being saved to PostgreSQL.")

resume_tab, interview_tab, history_tab = st.tabs(["1. AI resume assessment", "2. 15-minute mock interview", "3. History & progress"])

with resume_tab:
    st.subheader("Assess your resume against a job description")
    uploaded = st.file_uploader("Upload a PDF, DOCX, or TXT resume", type=["pdf", "docx", "txt"])
    job_description = st.text_area("Paste the job description", height=180, placeholder="A job description is required for a tailored AI assessment.")
    if st.button("Analyse and save resume", type="primary", disabled=uploaded is None or not job_description.strip()):
        try:
            resume_text = extract_resume_text(uploaded.name, uploaded.getvalue())
            with st.spinner("Groq is comparing your resume to the job description…"):
                report = analyse_resume(resume_text, role, job_description).model_dump()
            resume = save_resume(user_id=st.session_state.user_id, filename=uploaded.name, text=resume_text, assessment=report)
            st.session_state.ats_report = report
            st.session_state.resume_text = resume_text
            st.session_state.resume_id = resume.id
            st.session_state.job_description = job_description
            st.success("Encrypted resume record and AI assessment saved.")
        except Exception as exc:
            st.error(f"AI assessment failed ({type(exc).__name__}): {exc}")

    report = st.session_state.ats_report
    if report:
        left, right = st.columns([1, 2])
        left.metric("ATS-readiness estimate", f"{report['overall_score']}/100")
        right.write(report["executive_summary"])
        st.dataframe(report["criteria"], use_container_width=True, hide_index=True)
        first, second = st.columns(2)
        with first:
            st.write("**Strengths**")
            for item in report["strengths"]:
                st.markdown(f"- {item}")
        with second:
            st.write("**Gaps to address**")
            for item in report["gaps"]:
                st.markdown(f"- {item}")
        st.write("**Tailored recommendations**")
        for item in report["tailored_recommendations"]:
            st.markdown(f"- {item}")

with interview_tab:
    st.subheader("Persistent AI-led interview")
    st.caption("Questions adapt to your previous answers. Feedback appears only when the interview ends.")
    if st.session_state.interview is None:
        if not st.session_state.resume_id:
            st.warning("Complete and save an AI resume assessment first.")
        elif st.button("Start 15-minute interview", type="primary"):
            try:
                placeholder = create_interview(user_id=st.session_state.user_id, resume_id=st.session_state.resume_id, role=role, difficulty=difficulty, interview_style=style, job_description=st.session_state.job_description, state={})
                with st.spinner("Your AI interviewer is preparing…"):
                    state = start_interview(session_id=placeholder.id, role=role, difficulty=difficulty, interview_style=style, resume_text=st.session_state.resume_text, job_description=st.session_state.job_description)
                update_interview(interview_id=placeholder.id, user_id=st.session_state.user_id, state=state)
                st.session_state.interview = state
                st.session_state.active_interview_id = placeholder.id
                st.session_state.interview_started_at = time.time()
                st.rerun()
            except Exception as exc:
                st.error(f"Interview start failed ({type(exc).__name__}): {exc}")
    else:
        interview = st.session_state.interview
        elapsed = int(time.time() - st.session_state.interview_started_at)
        st.caption(f"Elapsed: {min(elapsed, 900) // 60:02d}:{min(elapsed, 900) % 60:02d} / 15:00")
        for item in interview["transcript"]:
            with st.chat_message(item["role"]):
                st.write(item["content"])
        if interview["status"] == "active":
            col, end_col = st.columns([4, 1])
            with end_col:
                end_now = st.button("End interview")
            answer = st.chat_input("Type your answer…")
            message = "Please end the interview now." if end_now else answer
            if message:
                try:
                    with st.spinner("Interviewer is evaluating and planning the next step…"):
                        state = continue_interview(interview, message, elapsed, st.session_state.active_interview_id)
                    update_interview(interview_id=st.session_state.active_interview_id, user_id=st.session_state.user_id, state=state)
                    st.session_state.interview = state
                    st.rerun()
                except Exception as exc:
                    st.error(f"Interview turn failed ({type(exc).__name__}): {exc}")
        else:
            report = interview.get("final_report")
            if report:
                st.divider()
                st.metric("Overall interview score", f"{report['overall_score']}/100")
                st.write(report["summary"])
                st.dataframe(report["rubric_scores"], use_container_width=True, hide_index=True)
                left, right = st.columns(2)
                with left:
                    st.write("**Strengths**")
                    for item in report["strengths"]:
                        st.markdown(f"- {item}")
                with right:
                    st.write("**Improvement areas**")
                    for item in report["improvement_areas"]:
                        st.markdown(f"- {item}")
                st.write("**Practice plan**")
                for item in report["practice_plan"]:
                    st.markdown(f"- {item}")
                pdf = generate_interview_report(report=report, role=interview["target_role"], difficulty=interview["difficulty"], interview_style=interview["interview_style"])
                st.download_button("Download PDF report", data=pdf, file_name="interview-feedback-report.pdf", mime="application/pdf")
            if st.button("Start a new interview"):
                st.session_state.interview = None
                st.session_state.active_interview_id = None
                st.session_state.interview_started_at = None
                st.rerun()

with history_tab:
    st.subheader("Your interview progress")
    summary = progress_summary(st.session_state.user_id)
    one, two, three, four = st.columns(4)
    one.metric("Total sessions", summary["total"])
    two.metric("Completed", summary["completed"])
    three.metric("In progress", summary["active"])
    four.metric("Average score", f"{summary['average_score']}/100" if summary["average_score"] is not None else "-" )
    sessions = list_interviews(st.session_state.user_id)
    if not sessions:
        st.info("Your saved interview sessions will appear here.")
    for saved in sessions:
        with st.expander(f"{saved.target_role} - {saved.difficulty} - {saved.status} - {saved.updated_at.strftime('%d %b %Y %H:%M')}"):
            if saved.status == "active" and st.button("Resume this interview", key=f"resume-{saved.id}"):
                loaded = load_interview(interview_id=saved.id, user_id=st.session_state.user_id)
                st.session_state.interview = loaded["state"]
                st.session_state.active_interview_id = saved.id
                st.session_state.interview_started_at = time.time()
                st.rerun()
            elif saved.encrypted_final_report:
                loaded = load_interview(interview_id=saved.id, user_id=st.session_state.user_id)
                st.metric("Saved score", f"{loaded['report']['overall_score']}/100")
