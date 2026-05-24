import type {
  ActiveRoom, ChatMessage, DashboardEvent,
  KillFeedEntry, PlayerState, RoomState, Team
} from './types';

// ---------------------------------------------------------------------------
// Game socket (player view)
// ---------------------------------------------------------------------------

class GameSocketManager {
  ws: WebSocket | null = null;
  private connectArgs: { url: string; myTeam: Team | null; userId: string } | null = null;

  connected = $state(false);
  room = $state<RoomState | null>(null);
  messages = $state<ChatMessage[]>([]);
  killFeed = $state<KillFeedEntry[]>([]);
  matchOver = $state(false);
  matchWinner = $state<Team | null>(null);
  error = $state<string | null>(null);
  errorCode = $state<string | null>(null);
  kicked = $state(false);
  timedOut = $state(false);
  timeoutUntil = $state<Date | null>(null);
  myUserId = $state<string>('');

  connect(url: string, myTeam: Team | null = null, userId = '') {
    this.connectArgs = { url, myTeam, userId };
    this.myUserId = userId;
    this.reset();
    this.ws = new WebSocket(url);

    this.ws.onopen = () => { this.connected = true; };

    this.ws.onclose = () => { this.connected = false; };

    this.ws.onerror = () => { this.error = 'Connection error'; };

    this.ws.onmessage = (e) => {
      const event = JSON.parse(e.data) as { type: string; payload: Record<string, unknown> };
      this.handle(event, myTeam);
    };
  }

  private handle(event: { type: string; payload: Record<string, unknown> }, myTeam: Team | null) {
    const p = event.payload;

    switch (event.type) {
      case 'room_created':
      case 'room_joined':
        this.room = {
          code: p.code as string,
          match_type: p.match_type as never,
          max_players: p.max_players as number,
          max_per_team: p.max_per_team as number,
          team_a: p.team_a as string[],
          team_b: p.team_b as string[],
          usernames: (p.usernames as Record<string, string>) ?? {},
          score_a: 0,
          score_b: 0,
          current_round: 0,
          status: 'WAITING',
          is_sudden_death: false,
          rounds: [],
          my_team: p.team as Team,
        };
        break;

      case 'player_joined':
        if (this.room) {
          this.room.team_a = p.team_a as string[];
          this.room.team_b = p.team_b as string[];
          this.room.usernames = { ...this.room.usernames, ...(p.usernames as Record<string, string>) };
        }
        break;

      case 'match_start':
        if (this.room) {
          this.room.status = 'IN_PROGRESS';
          this.room.team_a = p.team_a as string[];
          this.room.team_b = p.team_b as string[];
        }
        break;

      case 'round_start':
        if (this.room) {
          this.room.current_round = p.round as number;
          this.room.is_sudden_death = p.is_sudden_death as boolean;
        }
        break;

      case 'kill_feed':
        this.killFeed = [
          { text: p.text as string, round: p.round as number, timestamp: new Date() },
          ...this.killFeed,
        ].slice(0, 50);
        break;

      case 'round_end':
        if (this.room) {
          this.room.score_a = p.score_a as number;
          this.room.score_b = p.score_b as number;
          this.room.rounds = [...this.room.rounds, p as never];
        }
        break;

      case 'match_end':
        this.matchOver = true;
        this.matchWinner = p.winner as Team;
        if (this.room) this.room.status = 'FINISHED';
        break;

      case 'chat':
        this.messages = [
          ...this.messages,
          { ...p, timestamp: new Date() } as unknown as ChatMessage,
        ];
        break;

      case 'kicked':
        this.kicked = true;
        break;

      case 'timed_out':
        this.timedOut = true;
        this.timeoutUntil = p.timeout_until ? new Date(p.timeout_until as string) : null;
        break;

      case 'moderation':
        if (p.user_id === this.myUserId) {
          if (p.action === 'TIMEOUT') {
            this.timedOut = true;
          }
          if (p.action === 'PARDON') {
            this.timedOut = false;
            this.error = null;
            this.errorCode = null;
          }
          if (p.action === 'BAN') {
            this.error = 'Has sido baneado permanentemente.';
            this.errorCode = 'BANNED';
          }
        }
        break;

      case 'error':
        this.error = p.message as string;
        this.errorCode = (p.code as string) ?? null;
        break;
    }
  }

  reconnect() {
    if (this.connectArgs) {
      const { url, myTeam, userId } = this.connectArgs;
      this.connect(url, myTeam, userId);
    }
  }

  sendChat(text: string) {
    this.ws?.send(JSON.stringify({ type: 'chat', text }));
  }

  ping() {
    this.ws?.send(JSON.stringify({ type: 'ping' }));
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }

  private reset() {
    this.connected = false;
    this.room = null;
    this.messages = [];
    this.killFeed = [];
    this.matchOver = false;
    this.matchWinner = null;
    this.error = null;
    this.errorCode = null;
    this.kicked = false;
    this.timedOut = false;
    this.timeoutUntil = null;
    this.myUserId = '';
  }
}

// ---------------------------------------------------------------------------
// Dashboard socket (admin view)
// ---------------------------------------------------------------------------

class DashboardSocketManager {
  ws: WebSocket | null = null;

  connected = $state(false);
  rooms = $state<ActiveRoom[]>([]);
  players = $state<Record<string, PlayerState>>({});
  events = $state<DashboardEvent[]>([]);
  error = $state<string | null>(null);

  connect(url: string) {
    this.ws = new WebSocket(url);
    this.ws.onopen = () => { this.connected = true; };
    this.ws.onclose = () => { this.connected = false; };
    this.ws.onerror = () => { this.error = 'Connection error'; };
    this.ws.onmessage = (e) => {
      const event = JSON.parse(e.data) as { type: string; room?: string; payload: Record<string, unknown> };
      this.handle(event);
    };
  }

  private handle(event: { type: string; room?: string; payload: Record<string, unknown> }) {
    const p = event.payload;

    if (event.type === 'room_list') {
      this.rooms = p.rooms as ActiveRoom[];
      return;
    }

    if (event.type === 'player_state') {
      this.players = { ...this.players, [p.user_id as string]: p as unknown as PlayerState };
      return;
    }

    if (event.type === 'room_created') {
      const exists = this.rooms.some(r => r.code === (p.code as string));
      if (!exists) {
        this.rooms = [...this.rooms, {
          code: p.code as string,
          match_type: p.match_type as never,
          status: p.status as string ?? 'WAITING',
          score_a: 0, score_b: 0, current_round: 0,
          team_a: [], team_b: [],
          players_online: p.players_online as number ?? 0,
        }];
      }
      return;
    }

    if (event.type === 'room_closed') {
      this.rooms = this.rooms.filter(r => r.code !== (p.code as string));
      return;
    }

    // Log all other events to the live feed
    this.events = [
      { room: event.room || '—', type: event.type, payload: p, timestamp: new Date() },
      ...this.events,
    ].slice(0, 200);

    // Sync room state from broadcast events
    if (event.room) {
      if (event.type === 'round_end') {
        this.rooms = this.rooms.map(r =>
          r.code === event.room
            ? { ...r, score_a: p.score_a as number, score_b: p.score_b as number, current_round: p.round as number }
            : r
        );
      }
      if (event.type === 'player_joined' || event.type === 'player_left') {
        this.rooms = this.rooms.map(r =>
          r.code === event.room
            ? { ...r, players_online: ((p.team_a as string[])?.length ?? 0) + ((p.team_b as string[])?.length ?? 0) }
            : r
        );
      }
      if (event.type === 'match_start') {
        this.rooms = this.rooms.map(r =>
          r.code === event.room ? { ...r, status: 'IN_PROGRESS' } : r
        );
      }
      if (event.type === 'match_end') {
        this.rooms = this.rooms.map(r =>
          r.code === event.room ? { ...r, status: 'FINISHED' } : r
        );
      }
    }

    if (event.type === 'moderation') {
      const uid = p.user_id as string;
      if (this.players[uid]) {
        this.players = {
          ...this.players,
          [uid]: { ...this.players[uid], strikes: p.strikes as number },
        };
      }
    }

    if (event.type === 'mod_ack' && (p.success as boolean)) {
      const uid = p.user_id as string;
      if (this.players[uid]) {
        const STATUS_MAP: Record<string, string> = {
          WARN:    'WARNED',
          TIMEOUT: 'TIMEOUT',
          KICK:    'TIMEOUT',
          BAN:     'BANNED',
          PARDON:  'ACTIVE',
        };
        const newStatus = STATUS_MAP[p.action as string];
        if (newStatus) {
          this.players = {
            ...this.players,
            [uid]: {
              ...this.players[uid],
              status: newStatus as import('./types').UserStatus,
              ...(p.action === 'PARDON' ? { strikes: 0 } : {}),
            },
          };
        }
      }
    }
  }

  sendModAction(userId: string, action: string, reason = 'Acción manual del moderador') {
    this.ws?.send(JSON.stringify({ type: 'mod_action', payload: { user_id: userId, action, reason } }));
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }
}

export const gameSocket = new GameSocketManager();
export const dashSocket = new DashboardSocketManager();
