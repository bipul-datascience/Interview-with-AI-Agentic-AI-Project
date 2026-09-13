"""Model-driven résumé and job-description assessment."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from services.llm import structured_completion


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CriterionAssessment(StrictSchema):
    criterion: str
    score: int = Field(ge=0, le=100)
    evidence: str
    improvement: str


class ATSReport(StrictSchema):
    overall_score: int = Field(ge=0, le=100)
    executive_summary: str
    strengths: list[str]
    gaps: list[str]
    criteria: list[CriterionAssessment]
    tailored_recommendations: list[str]
    rewritten_bullets: list[str]


def analyse_resume(resume_text: str, role: str, job_description: str) -> ATSReport:
    if not resume_text.strip():
        raise ValueError("No readable text was found in the resume.")
    if not job_description.strip():
        raise ValueError("Please paste or upload a job description for an AI-tailored ATS assessment.")
    return structured_completion(
        schema=ATSReport,
        temperature=0.15,
        system="""You are an expert resume reviewer. Produce a fair ATS-readiness estimate, not a claim about any real applicant tracking system. Compare the candidate only against the supplied job description and target role. Do not invent resume facts. Score each criterion from 0 to 100 and make recommendations practical, specific, and truthful. Evaluate role/skill match, relevant experience, quantified impact, communication clarity, technical correctness, and problem-solving evidence.""",
        user=f"""Target role: {role}
Job description:
---
{job_description}
---
Candidate resume:
---
{resume_text}
---
Return the assessment in the requested schema. Rewritten bullets must be labelled as examples and must not fabricate accomplishments.""",
    )
