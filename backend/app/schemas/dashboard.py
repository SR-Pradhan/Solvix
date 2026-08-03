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


class RatingDistributionOut(BaseModel):
    buckets: list[RatingBucket]
    unrated_count: int


class TimelinePoint(BaseModel):
    day: date
    solved_count: int


class TimelineOut(BaseModel):
    days: int
    points: list[TimelinePoint]
