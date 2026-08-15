from datetime import datetime

from pydantic import BaseModel


class InterviewTurn(BaseModel):
    role: str
    content: str


class InterviewFindings(BaseModel):
    verdict: str = ""
    strengths: list[str] = []
    gaps: list[str] = []
    # False unless the transcript shows it was actually discussed — defaulting
    # to true would let a silent interview pass a check it never faced.
    complexity_handled: bool = False
    advice: str = ""


class InterviewOut(BaseModel):
    id: int
    topic: str | None = None
    platform: str | None = None
    problem_name: str | None = None
    problem_url: str | None = None
    status: str
    turns: list[InterviewTurn] = []
    findings: InterviewFindings | None = None
    created_at: datetime | None = None


class InterviewsOut(BaseModel):
    interviews: list[InterviewOut] = []


class InterviewReply(BaseModel):
    answer: str
