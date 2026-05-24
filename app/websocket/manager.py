from fastapi import WebSocket

from .game import Room


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.dashboard_connections: set[WebSocket] = set()

    async def broadcast_room(self, code: str, event: dict) -> None:
        room = self.rooms.get(code)
        if not room:
            return
        dead: list[str] = []
        for user_id, ws in room.connections.items():
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(user_id)
        for uid in dead:
            room.connections.pop(uid, None)

        # Mirror every room event to the dashboard
        await self.broadcast_dashboard({"room": code, **event})

    async def broadcast_dashboard(self, event: dict) -> None:
        dead: set[WebSocket] = set()
        for ws in self.dashboard_connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.add(ws)
        self.dashboard_connections -= dead

    async def send(self, ws: WebSocket, event: dict) -> None:
        try:
            await ws.send_json(event)
        except Exception:
            pass

    def remove_player(self, code: str, user_id: str) -> bool:
        """Remove player from room. Returns True if the room was fully destroyed."""
        room = self.rooms.get(code)
        if not room:
            return False
        room.connections.pop(user_id, None)
        if not room.connections:
            if room.match_task and not room.match_task.done():
                room.match_task.cancel()
            self.rooms.pop(code, None)
            return True
        return False

    def room_snapshot(self) -> list[dict]:
        return [
            {
                "code": r.code,
                "match_type": r.match_type,
                "status": r.status,
                "score_a": r.score_a,
                "score_b": r.score_b,
                "current_round": r.current_round,
                "team_a": r.team_a,
                "team_b": r.team_b,
                "players_online": len(r.connections),
            }
            for r in self.rooms.values()
        ]


# Singleton shared across all WebSocket handlers
manager = ConnectionManager()
