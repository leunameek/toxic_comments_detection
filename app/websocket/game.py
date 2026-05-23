import asyncio
import random
import string
from dataclasses import dataclass, field

from fastapi import WebSocket

MATCH_SIZES: dict[str, int] = {"1v1": 1, "2v2": 2, "5v5": 5}  # max players per team

WIN_SCORE = 5

KILL_TEMPLATES = [
    "{killer} mató a {victim} saltando",
    "{killer} le hizo t-bag a {victim} después de eliminarle",
    "{killer} eliminó a {victim} con escopeta a quemarropa",
    "{killer} lanzó una granada y eliminó a {victim}",
    "{killer} le hizo un headshot a {victim} con AWP",
    "{killer} mató a {victim} con pistola mientras corría",
    "{killer} apuñaló a {victim} por la espalda",
    "{killer} hizo volar a {victim} con C4",
    "{killer} cazó a {victim} mientras recargaba",
    "{killer} corrió hasta {victim} y lo eliminó cuerpo a cuerpo",
    "{killer} le pegó un tiro a {victim} en pleno salto",
    "{killer} dueleó a {victim} con Desert Eagle",
    "{killer} reventó a {victim} con escopeta",
    "{killer} usó un molotov para acabar con {victim}",
    "{killer} tomó por sorpresa a {victim} en spawn",
    "{killer} no le dio ninguna oportunidad a {victim}",
    "{killer} eliminó a {victim} con un tiro a través de la pared",
    "{killer} le hizo un ace y {victim} fue el último en caer",
]


def generate_code(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


@dataclass
class Room:
    code: str
    session_id: str
    match_type: str
    max_per_team: int
    team_a: list[str] = field(default_factory=list)
    team_b: list[str] = field(default_factory=list)
    connections: dict[str, WebSocket] = field(default_factory=dict)
    usernames: dict[str, str] = field(default_factory=dict)
    score_a: int = 0
    score_b: int = 0
    current_round: int = 0
    rounds_history: list[dict] = field(default_factory=list)
    status: str = "WAITING"
    kicked_users: set[str] = field(default_factory=set)
    match_task: asyncio.Task | None = None

    @property
    def max_players(self) -> int:
        return self.max_per_team * 2

    @property
    def all_players(self) -> list[str]:
        return self.team_a + self.team_b

    @property
    def is_full(self) -> bool:
        return len(self.all_players) >= self.max_players

    def can_join_team(self, team: str) -> bool:
        target = self.team_a if team == "A" else self.team_b
        return len(target) < self.max_per_team


def _kill_feed_messages(room: Room, n: int) -> list[str]:
    players = room.all_players
    if len(players) < 2:
        return []
    messages = []
    for _ in range(n):
        killer_id, victim_id = random.sample(players, 2)
        killer = room.usernames.get(killer_id, killer_id)
        victim = room.usernames.get(victim_id, victim_id)
        messages.append(random.choice(KILL_TEMPLATES).format(killer=killer, victim=victim))
    return messages


async def run_match(room: Room, manager) -> None:
    """Drives the full match lifecycle as a background asyncio task."""
    from .events import EventType, make_event
    from ..database import SessionLocal
    from ..models import GameSession

    # Small grace period so all players receive MATCH_START before rounds begin
    await asyncio.sleep(2.0)

    while room.score_a < WIN_SCORE and room.score_b < WIN_SCORE:
        room.current_round += 1
        is_sudden_death = (
            room.score_a == WIN_SCORE - 1 and room.score_b == WIN_SCORE - 1
        )

        await manager.broadcast_room(room.code, make_event(
            EventType.ROUND_START,
            round=room.current_round,
            is_sudden_death=is_sudden_death,
            score_a=room.score_a,
            score_b=room.score_b,
        ))

        # Kill feed: 3–6 messages, one every 2–4 seconds
        for text in _kill_feed_messages(room, n=random.randint(3, 6)):
            await asyncio.sleep(random.uniform(2.0, 4.0))
            await manager.broadcast_room(room.code, make_event(
                EventType.KILL_FEED,
                text=text,
                round=room.current_round,
            ))

        await asyncio.sleep(1.5)

        winner = random.choice(["A", "B"])
        if winner == "A":
            room.score_a += 1
        else:
            room.score_b += 1

        record = {
            "round": room.current_round,
            "winner": winner,
            "score_a": room.score_a,
            "score_b": room.score_b,
            "is_sudden_death": is_sudden_death,
        }
        room.rounds_history.append(record)

        await manager.broadcast_room(room.code, make_event(EventType.ROUND_END, **record))

        if room.score_a < WIN_SCORE and room.score_b < WIN_SCORE:
            await asyncio.sleep(3.0)

    room.status = "FINISHED"
    match_winner = "A" if room.score_a >= WIN_SCORE else "B"

    await manager.broadcast_room(room.code, make_event(
        EventType.MATCH_END,
        winner=match_winner,
        score_a=room.score_a,
        score_b=room.score_b,
        total_rounds=room.current_round,
        rounds=room.rounds_history,
        team_a=room.team_a,
        team_b=room.team_b,
    ))

    db = SessionLocal()
    try:
        from datetime import datetime, timezone
        session = db.get(GameSession, room.session_id)
        if session:
            session.status = "FINISHED"
            session.ended_at = datetime.now(timezone.utc)
            session.context = "WIN" if match_winner == "A" else "LOSS"
            db.commit()
    finally:
        db.close()
