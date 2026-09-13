# Project handoff: Get interview ready with us

## Goal

Build a Streamlit application named **Get interview ready with AI**. A candidate selects a target role, uploads a résumé, pastes a job description, receives an AI-generated ATS-readiness assessment, and completes a guarded 15-minute text mock interview.

## Confirmed product decisions

- Provider: Groq, configured locally through `GROQ_API_KEY` in `.env`.
- Recommended model: `openai/gpt-oss-120b`; fallback: `openai/gpt-oss-20b`.
- Interview modality: text only initially.
- Roles: Data Analyst, Data Scientist, Business Analyst, AI Engineer, Data Engineer.
- Candidate selects: Junior, Mid-level, or Senior; Technical, Behavioral, Case study, or Mixed interview.
- Job description: user must paste it into the UI; there is no external job-board integration.
- Interview duration: 15 minutes.
- Feedback: reveal only after the interview completes.
- Data retention: résumé text, job description, transcript, and reports must exist only in `st.session_state`; do not add a database or file storage.
- The user explicitly rejected predefined role question banks, keyword heuristics, and deterministic scoring. Model output drives the assessment, questions, guardrail classifications, and answer evaluation.

## Current implementation

```text
streamlit_app.py              Streamlit UI and session-only state
services/resume_parser.py     Local PDF/DOCX/TXT text extraction
services/llm.py               Groq SDK client + strict structured-output helper
services/ats.py               Groq-powered ATSReport schema and assessment call
graphs/interview_graph.py     LangGraph interview graph and Groq-based nodes
requirements.txt              Python dependencies
.env.example                  Required environment variable template
README.md                     Basic local run instructions
```

### User flow

1. Candidate chooses role, seniority, and interview style in the sidebar.
2. Candidate uploads PDF/DOCX/TXT résumé and pastes a job description.
3. `services.resume_parser.extract_resume_text()` extracts local text.
4. `services.ats.analyse_resume()` sends résumé + job description to Groq and requests a structured `ATSReport`.
5. Streamlit displays score, strengths, gaps, criterion assessments, recommendations, and example bullets.
6. Candidate starts interview; `graphs.interview_graph.start_interview()` invokes the LangGraph `initialise` node.
7. Groq dynamically generates each question using role, selected level/style, résumé, job description, transcript, and elapsed time.
8. Every candidate message is sent to a Groq guardrail-classifier node and routed to `answer`, `off_topic`, `unsafe`, or `end_interview`.
9. Valid answers are evaluated privately against six dimensions; feedback is not displayed during the interview.
10. When the candidate ends the interview or the timer reaches 900 seconds, Groq produces a structured `FinalReport` and Streamlit displays it.

## LangGraph graph

```text
START → classify
  start          → initialise → END
  answer         → evaluate_and_continue → END
  off_topic      → redirect → END
  unsafe         → redirect → END
  end_interview  → finish → END
```

The compiled graph intentionally has no checkpointer. This enforces the user’s session-only privacy requirement. State is retained only in the Streamlit browser session.

## Phase 2 implementation

Phase 2 has been implemented with PostgreSQL-ready SQLAlchemy models, bcrypt password authentication, Fernet encryption for application data, encrypted LangGraph PostgreSQL checkpoints, history/progress UI, adaptive question prompts, and an in-memory downloadable PDF report.

The user must configure `DATABASE_URL`, `DATA_ENCRYPTION_KEY`, and `LANGGRAPH_AES_KEY` before launching the new version. `docker-compose.yml` contains the local PostgreSQL development service. See `README.md` for setup commands.

## Important current issue and fix

Groq strict structured output rejected the initial JSON schema with:

```text
additionalProperties:false must be set on every object
```

This has been corrected by making all Pydantic response schemas inherit `StrictSchema`, which sets `ConfigDict(extra="forbid")`. Before further feature work, rerun a minimal Groq structured-output request and then run an end-to-end résumé/interview test.

## Verification already completed

- Python syntax compilation passed before Groq SDK installation.
- Original deterministic LangGraph workflow tests passed before it was replaced.
- Groq SDK installation completed successfully.
- A network request reached Groq successfully; it exposed the strict JSON-schema issue above, so API key and network connectivity are confirmed without exposing the key.
- A full post-fix API verification has not yet been run.

## Run commands

```bash
python3 -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Security constraints

- Never print, commit, or send the `.env` contents.
- `.env` is already ignored by `.gitignore`.
- Do not persist résumé text or transcripts.
- ATS results are estimates, not a claim that a real ATS has evaluated the résumé.

## MCP status

MCP is not yet implemented because the agreed MVP receives the job description directly from the user and requires no external tools. LangGraph is actively used for orchestration. Add MCP only when introducing a concrete external capability (for example, a curated job-description source, question repository, reporting service, or voice service); do not add an MCP server merely for architecture branding.

## Suggested next steps

1. Start local PostgreSQL and complete an end-to-end test of account creation, persistence, checkpoint recovery, and PDF download.
2. Add account recovery, email verification, rate limiting, CSRF protection, and a formal retention/deletion policy before public deployment.
3. Add transcript token/context management for long interviews.
4. Add automated tests by mocking `structured_completion` rather than calling the live Groq service.
5. Add MCP only alongside a needed external integration.
