# Get interview ready with AI

A LangGraph + Streamlit application for Groq-powered, role-specific résumé feedback and guarded mock interviews.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Create a local `.env` file with `GROQ_API_KEY` and (optionally) `GROQ_MODEL`. The application uses model-generated structured assessments and interview turns; it does not use a hardcoded question bank or heuristic scoring. Reports are clearly labelled as **ATS-readiness estimates**, not a score from a real applicant-tracking system.

## Phase 2 setup

Phase 2 requires PostgreSQL for accounts, interview history, encrypted résumé records, and LangGraph checkpoints.

```bash
docker compose up -d
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

Add these values to `.env` (preserving your existing Groq variables):

```env
DATABASE_URL=postgresql+psycopg://interview_user:change_me@localhost:5432/interview_ready
DATA_ENCRYPTION_KEY=<the Fernet value from the first command>
LANGGRAPH_AES_KEY=<the 32-byte value from the second command>
```

The app automatically creates application tables and LangGraph creates its checkpoint tables on the first interview run. Use a managed PostgreSQL instance, TLS, a non-default database password, and a secrets manager before production deployment.

## What is included

- Upload PDF, DOCX, or TXT resumes
- Select a target role and optionally paste a job description
- AI-generated ATS-readiness score and tailored recommendations from the résumé and job description
- LangGraph interview workflow with AI-generated questions, evaluation, and off-topic/prompt-injection guardrails
- Password authentication, encrypted PostgreSQL persistence, interview history, progress metrics, LangGraph checkpoints, and downloadable PDF reports

## Next production steps

1. Add account recovery, verification email, rate limiting, and a formal retention/deletion policy.
2. Add database migrations and an automated deployment workflow.
3. Add voice using a real-time speech-to-text/text-to-speech provider.
