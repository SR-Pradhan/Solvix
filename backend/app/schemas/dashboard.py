from datetime import date

from pydantic import BaseModel


class StatsOut(BaseModel):
    problems_solved: int
    total_submissions: int
    accepted_submissions: int
    acceptance_rate: float
    avg_difficulty: float | None = None
    max_difficulty: int | None = None
    current_streak_days: int
    longest_streak_days: int


class TagCount(BaseModel):
    tag: str
    solved_count: int


class TagBreakdownOut(BaseModel):
    total_tags: int
    tags: list[TagCount]


class RatingBucket(BaseModel):
    rating: int
    solved_count: int


class DifficultyLabelCount(BaseModel):
    label: str
    solved_count: int


class RatingDistributionOut(BaseModel):
    buckets: list[RatingBucket]
    labels: list[DifficultyLabelCount] = []
    unrated_count: int


class PlanTask(BaseModel):
    title: str
    detail: str = ""
    minutes: int


class DailyPlanOut(BaseModel):
    date: date
    generated: bool
    focus: list[str] = []
    tasks: list[PlanTask] = []
    note: str = ""
    # Set when there is not enough practice data to plan a session.
    unavailable: str | None = None


class TopicHighlight(BaseModel):
    tag: str
    accuracy: float | None = None
    solved: int


class WeeklyReportOut(BaseModel):
    week_start: date
    week_end: date
    in_progress: bool
    problems_solved: int
    by_platform: dict[str, int] = {}
    active_days: int
    weakest: list[TopicHighlight] = []
    strongest: list[TopicHighlight] = []


class ReminderItem(BaseModel):
    kind: str
    subject: str
    title: str
    reason: str


class RemindersOut(BaseModel):
    run_date: date
    generated: int
    reminders: list[ReminderItem] = []


class SolvedProblem(BaseModel):
    id: str
    name: str
    platform: str
    last_solved_at: date
    days_ago: int
    url: str | None = None


class SolvedInTopicOut(BaseModel):
    tag: str
    problems: list[SolvedProblem] = []


class UnsolvedProblem(BaseModel):
    id: str
    name: str
    difficulty: str | None = None
    rating: int | None = None
    tags: list[str] = []
    url: str


class UnsolvedInTopicOut(BaseModel):
    tag: str
    platform: str
    problems: list[UnsolvedProblem] = []


class TopicScore(BaseModel):
    tag: str
    attempts: int
    accepted: int
    solved: int
    accuracy: float | None = None
    last_solved_at: date | None = None
    days_since_last_solve: int | None = None
    weakness: float
    status: str


class WeakTopicsOut(BaseModel):
    topics: list[TopicScore]
    total_topics: int
    skipped_low_volume: int
    min_attempts: int
    scored_on_accuracy: int
    stale_count: int
    stale_horizon_days: int
    stale_topics: list[str] = []


class WeakTag(BaseModel):
    tag: str
    solved_count: int
    deficit: float


class RecommendedProblem(BaseModel):
    problem_id: str
    contest_id: int
    name: str
    rating: int
    tags: list[str]
    matched_tags: list[str]
    url: str


class RecommendationsOut(BaseModel):
    target_rating: int
    weak_tags: list[WeakTag]
    problems: list[RecommendedProblem]
    note: str | None = None


class TimelinePoint(BaseModel):
    day: date
    solved_count: int


class TimelineOut(BaseModel):
    days: int
    points: list[TimelinePoint]
