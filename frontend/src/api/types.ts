// Mirrors backend/app/schemas/*.py. Keep in sync with the Pydantic models.

export interface User {
  id: number;
  email: string;
  display_name: string | null;
  codeforces_handle: string | null;
  leetcode_repo: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Stats {
  problems_solved: number;
  total_submissions: number;
  accepted_submissions: number;
  acceptance_rate: number;
  avg_difficulty: number | null;
  max_difficulty: number | null;
  current_streak_days: number;
  longest_streak_days: number;
}

export interface TagCount {
  tag: string;
  solved_count: number;
}

export interface TagBreakdown {
  total_tags: number;
  tags: TagCount[];
}

export interface RatingBucket {
  rating: number;
  solved_count: number;
}

export interface DifficultyLabelCount {
  label: string;
  solved_count: number;
}

export interface RatingDistribution {
  buckets: RatingBucket[];
  labels: DifficultyLabelCount[];
  unrated_count: number;
}

export interface TimelinePoint {
  day: string;
  solved_count: number;
}

export interface Timeline {
  days: number;
  points: TimelinePoint[];
}

export interface WeakTag {
  tag: string;
  solved_count: number;
  deficit: number;
}

export interface RecommendedProblem {
  problem_id: string;
  contest_id: number;
  name: string;
  rating: number;
  tags: string[];
  matched_tags: string[];
  url: string;
}

export interface Recommendations {
  target_rating: number;
  weak_tags: WeakTag[];
  problems: RecommendedProblem[];
  note: string | null;
}

export interface TopicScore {
  tag: string;
  attempts: number;
  accepted: number;
  solved: number;
  accuracy: number | null;
  last_solved_at: string | null;
  days_since_last_solve: number | null;
  weakness: number;
  status: string;
}

export interface WeakTopics {
  topics: TopicScore[];
  total_topics: number;
  skipped_low_volume: number;
  min_attempts: number;
  scored_on_accuracy: number;
  stale_count: number;
  stale_horizon_days: number;
  stale_topics: string[];
}

export type Platform = "codeforces" | "leetcode";
