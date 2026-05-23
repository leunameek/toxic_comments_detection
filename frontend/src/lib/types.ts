export type MatchType = '1v1' | '2v2' | '5v5';
export type Team = 'A' | 'B';
export type ModerationAction = 'WARN' | 'TIMEOUT' | 'KICK' | 'BAN';
export type ToxicAction = 'APPROVE' | 'REVIEW' | 'TOXIC_ALERT' | 'BLOCK';
export type UserStatus = 'ACTIVE' | 'WARNED' | 'TIMEOUT' | 'BANNED';

export interface ChatMessage {
  user_id: string;
  username?: string;
  text: string;
  action: ToxicAction;
  score: number;
  auto_action: ModerationAction | null;
  timestamp: Date;
}

export interface KillFeedEntry {
  text: string;
  round: number;
  timestamp: Date;
}

export interface RoundRecord {
  round: number;
  winner: Team;
  score_a: number;
  score_b: number;
  is_sudden_death: boolean;
}

export interface RoomState {
  code: string;
  match_type: MatchType;
  max_players: number;
  max_per_team: number;
  team_a: string[];
  team_b: string[];
  usernames: Record<string, string>;
  score_a: number;
  score_b: number;
  current_round: number;
  status: 'WAITING' | 'IN_PROGRESS' | 'FINISHED';
  is_sudden_death: boolean;
  rounds: RoundRecord[];
  my_team: Team | null;
}

export interface PlayerState {
  user_id: string;
  username: string;
  strikes: number;
  status: UserStatus;
  toxicity_score: number;
  total_messages: number;
  toxic_messages: number;
}

export interface ActiveRoom {
  code: string;
  match_type: MatchType;
  status: string;
  score_a: number;
  score_b: number;
  current_round: number;
  team_a: string[];
  team_b: string[];
  players_online: number;
}

export interface DashboardEvent {
  room: string;
  type: string;
  payload: Record<string, unknown>;
  timestamp: Date;
}
