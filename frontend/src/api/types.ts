// Mirrors backend/app/schemas/*.py. Keep in sync with the Pydantic models.

export interface User {
  id: number;
  email: string;
  display_name: string | null;
  codeforces_handle: string | null;
  leetcode_repo: string | null;
  leetcode_username: string | null;
  has_avatar: boolean;
}

export interface PendingEmailChange {
  new_email: string;
  expires_at: string;
  attempts_left: number;
  resend_in_seconds: number;
}

/** A partial edit: an omitted key is left alone, an explicit null clears it. */
export interface ProfileChanges {
  display_name?: string | null;
  codeforces_handle?: string;
  leetcode_username?: string | null;
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

export interface PlanTask {
  title: string;
  detail: string;
  minutes: number;
}

export interface DailyPlan {
  date: string;
  generated: boolean;
  focus: string[];
  tasks: PlanTask[];
  note: string;
  unavailable: string | null;
}

export interface TopicHighlight {
  tag: string;
  accuracy: number | null;
  solved: number;
}

export interface WeeklyReport {
  week_start: string;
  week_end: string;
  in_progress: boolean;
  problems_solved: number;
  by_platform: Record<string, number>;
  active_days: number;
  weakest: TopicHighlight[];
  strongest: TopicHighlight[];
}

export interface ReminderItem {
  kind: string;
  platform: string;
  subject: string;
  title: string;
  reason: string;
  // Problem reminders only — a topic is not a page anywhere.
  url: string | null;
}

export interface Reminders {
  run_date: string;
  generated: number;
  reminders: ReminderItem[];
}

export interface SolvedProblem {
  id: string;
  name: string;
  platform: string;
  last_solved_at: string;
  days_ago: number;
  url: string | null;
}

export interface SolvedInTopic {
  tag: string;
  problems: SolvedProblem[];
}

export interface UnsolvedProblem {
  id: string;
  name: string;
  difficulty: string | null;
  rating: number | null;
  tags: string[];
  url: string;
}

export interface UnsolvedInTopic {
  tag: string;
  platform: string;
  problems: UnsolvedProblem[];
}

export interface ProfileTagCount {
  tag: string;
  solved: number;
}

export interface LeetCodeProfile {
  username: string;
  total_solved: number;
  easy: number;
  medium: number;
  hard: number;
  tags: ProfileTagCount[];
  coverage: { tracked: number; missing: number; percent: number };
  imported: number;
}

export type Platform = "codeforces" | "leetcode";

export interface Health {
  status: string;
  db: string;
  version: string;
}
