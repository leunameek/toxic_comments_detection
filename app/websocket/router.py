import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from .events import EventType, make_event
from .game import MATCH_SIZES, Room, generate_code, run_match
from .manager import manager
from ..config import get_settings
from ..database import SessionLocal
from ..models import GameSession, Message, User
from ..services import classifier
from ..services.moderation_service import apply_strike

router = APIRouter(prefix="/ws", tags=["WebSocket"])


def _as_utc(dt: datetime) -> datetime:
    """Return dt as UTC-aware; handles naive datetimes stored by SQLite."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _scope(api_key: str | None) -> str | None:
    if not api_key:
        return None
    s = get_settings()
    if api_key in s.get_admin_keys():
        return "ADMIN"
    if api_key in s.get_moderator_keys():
        return "MODERATOR"
    if api_key in s.get_player_keys():
        return "PLAYER"
    return None


def _get_or_create_user(db, user_id: str, username: str | None = None) -> User:
    user = db.get(User, user_id)
    display = username or user_id
    if not user:
        user = User(user_id=user_id, username=display)
        db.add(user)
    elif username:
        user.username = display
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Shared chat handler (used by both create and join loops)
# ---------------------------------------------------------------------------

async def _handle_chat(db, room: Room, user_id: str, text: str) -> dict:
    """Classify text, persist message, apply strikes. Returns broadcast payload."""
    prediction = {"label": 0, "score": 0.0, "action": "APPROVE", "top_features": [], "processing_ms": 0.0}
    auto_action = None
    strikes = 0

    if classifier.is_model_loaded():
        prediction = classifier.predict(text)

    user = _get_or_create_user(db, user_id)

    msg = Message(
        message_id=f"msg_{uuid.uuid4().hex[:10]}",
        session_id=room.session_id,
        user_id=user_id,
        text=text,
        timestamp=datetime.now(timezone.utc),
        label=prediction["label"],
        score=prediction["score"],
        action=prediction["action"],
        top_features=prediction["top_features"],
        processing_ms=prediction["processing_ms"],
    )
    db.add(msg)

    user.total_messages += 1
    if prediction["label"] == 1:
        user.toxic_messages += 1
        user.toxicity_score = round(0.9 * user.toxicity_score + 0.1 * prediction["score"], 4)
        if user.status != "BANNED":
            mod = apply_strike(db, user, prediction["score"], msg.message_id, room.session_id)
            if mod:
                auto_action = mod.type

    db.commit()
    db.refresh(user)
    strikes = user.strikes

    return {
        "chat_payload": {
            "user_id": user_id,
            "text": text,
            "action": prediction["action"],
            "score": prediction["score"],
            "top_features": prediction["top_features"],
            "auto_action": auto_action,
        },
        "auto_action": auto_action,
        "strikes": strikes,
        "score": prediction["score"],
    }


# ---------------------------------------------------------------------------
# Main player message loop
# ---------------------------------------------------------------------------

async def _player_loop(ws: WebSocket, room: Room, user_id: str) -> None:
    was_kicked = False
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await manager.send(ws, {"type": "pong"})
                continue

            if msg_type == "chat":
                text = (data.get("text") or "").strip()
                if not text:
                    continue

                # Timeout check — block chat but keep them in the room
                db = SessionLocal()
                try:
                    user = db.get(User, user_id)
                    if user and user.status == "TIMEOUT":
                        if user.timeout_until and _as_utc(user.timeout_until) > datetime.now(timezone.utc):
                            await manager.send(ws, make_event(
                                EventType.TIMED_OUT,
                                message="Estás en timeout y no puedes enviar mensajes.",
                                timeout_until=user.timeout_until.isoformat(),
                            ))
                            continue
                        else:
                            # Timeout expired — restore to warned
                            user.status = "WARNED"
                            user.timeout_until = None
                            db.commit()
                finally:
                    db.close()

                db = SessionLocal()
                try:
                    result = await _handle_chat(db, room, user_id, text)
                finally:
                    db.close()

                await manager.broadcast_room(room.code, make_event(
                    EventType.CHAT, **result["chat_payload"]
                ))

                if result["auto_action"]:
                    await manager.broadcast_room(room.code, make_event(
                        EventType.MODERATION,
                        user_id=user_id,
                        action=result["auto_action"],
                        strikes=result["strikes"],
                        reason=f"Score {result['score']:.2f}",
                    ))

                    # Kick: send personal event then close their connection
                    if result["auto_action"] == "KICK":
                        was_kicked = True
                        room.kicked_users.add(user_id)
                        await manager.send(ws, make_event(
                            EventType.KICKED,
                            reason="Has sido expulsado por comportamiento tóxico.",
                        ))
                        await ws.close(code=1008)
                        return

                    # Ban: also close their connection immediately
                    if result["auto_action"] == "BAN":
                        await manager.send(ws, make_event(
                            EventType.ERROR,
                            message="Has sido baneado permanentemente.",
                            code="BANNED",
                        ))
                        await ws.close(code=1008)
                        return

    except WebSocketDisconnect:
        pass
    finally:
        # Record which team the player was on before freeing their slot
        if user_id in room.team_a:
            room.past_players[user_id] = "A"
        elif user_id in room.team_b:
            room.past_players[user_id] = "B"
        room.team_a = [p for p in room.team_a if p != user_id]
        room.team_b = [p for p in room.team_b if p != user_id]

        room_closed = manager.remove_player(room.code, user_id)
        if not was_kicked:
            await manager.broadcast_room(room.code, make_event(
                EventType.PLAYER_LEFT,
                user_id=user_id,
                team_a=room.team_a,
                team_b=room.team_b,
            ))
        if room_closed:
            await manager.broadcast_dashboard(make_event(EventType.ROOM_CLOSED, code=room.code))


# ---------------------------------------------------------------------------
# WS /ws/room/new  — host creates a room
# ---------------------------------------------------------------------------

@router.websocket("/room/new")
async def ws_create_room(
    ws: WebSocket,
    user_id: str = Query(...),
    username: str | None = Query(None),
    match_type: str = Query("5v5"),
    api_key: str | None = Query(None),
):
    await ws.accept()

    if not _scope(api_key):
        await manager.send(ws, make_event(EventType.ERROR, message="Invalid API key"))
        await ws.close()
        return

    # Ban check
    db = SessionLocal()
    try:
        existing = db.get(User, user_id)
        if existing and existing.status == "BANNED":
            await manager.send(ws, make_event(EventType.ERROR, message="Has sido baneado permanentemente y no puedes jugar.", code="BANNED"))
            await ws.close()
            return
    finally:
        db.close()

    if match_type not in MATCH_SIZES:
        await manager.send(ws, make_event(
            EventType.ERROR, message=f"match_type must be one of {list(MATCH_SIZES)}"
        ))
        await ws.close()
        return

    # Persist game session
    session_id = f"session_{uuid.uuid4().hex[:10]}"
    display = username or user_id
    db = SessionLocal()
    try:
        _get_or_create_user(db, user_id, username)
        db.add(GameSession(
            session_id=session_id,
            match_type=match_type,
            players=[user_id],
            status="WAITING",
        ))
        db.commit()
    finally:
        db.close()

    # Build room
    code = generate_code()
    while code in manager.rooms:
        code = generate_code()

    room = Room(
        code=code,
        session_id=session_id,
        match_type=match_type,
        max_per_team=MATCH_SIZES[match_type],
        team_a=[user_id],
        connections={user_id: ws},
        usernames={user_id: display},
    )
    manager.rooms[code] = room

    # Notify all connected dashboard clients about the new room
    await manager.broadcast_dashboard(make_event(
        EventType.ROOM_CREATED,
        code=code,
        match_type=match_type,
        max_players=room.max_players,
        max_per_team=room.max_per_team,
        status=room.status,
        players_online=0,
    ))

    await manager.send(ws, make_event(
        EventType.ROOM_CREATED,
        code=code,
        match_type=match_type,
        max_players=room.max_players,
        max_per_team=room.max_per_team,
        team="A",
        team_a=room.team_a,
        team_b=room.team_b,
        username=display,
    ))

    await _player_loop(ws, room, user_id)


# ---------------------------------------------------------------------------
# WS /ws/room/{code}  — guest joins a room
# ---------------------------------------------------------------------------

@router.websocket("/room/{code}")
async def ws_join_room(
    ws: WebSocket,
    code: str,
    user_id: str = Query(...),
    username: str | None = Query(None),
    team: str | None = Query(None),
    api_key: str | None = Query(None),
):
    await ws.accept()

    if not _scope(api_key):
        await manager.send(ws, make_event(EventType.ERROR, message="Invalid API key"))
        await ws.close()
        return

    # Ban check
    db = SessionLocal()
    try:
        existing = db.get(User, user_id)
        if existing and existing.status == "BANNED":
            await manager.send(ws, make_event(EventType.ERROR, message="Has sido baneado permanentemente y no puedes jugar.", code="BANNED"))
            await ws.close()
            return
    finally:
        db.close()

    room = manager.rooms.get(code)
    if not room:
        await manager.send(ws, make_event(EventType.ERROR, message="Room not found"))
        await ws.close()
        return

    # ── RECONNECT PATH ────────────────────────────────────────────────────────
    # Player was in this room before (disconnected or kicked + pardoned).
    prev_team = room.past_players.get(user_id)
    if prev_team and user_id not in room.connections:
        if user_id in room.kicked_users:
            await manager.send(ws, make_event(EventType.ERROR, message="Fuiste expulsado y no puedes volver a unirte.", code="KICKED"))
            await ws.close()
            return

        if room.status == "FINISHED":
            await manager.send(ws, make_event(EventType.ERROR, message="La partida ya terminó."))
            await ws.close()
            return

        # Restore to original team; for WAITING rooms check the slot is free
        if room.status == "WAITING" and not room.can_join_team(prev_team):
            await manager.send(ws, make_event(EventType.ERROR, message="Tu equipo ya está lleno."))
            await ws.close()
            return

        display = username or room.usernames.get(user_id, user_id)
        room.usernames[user_id] = display
        if prev_team == "A":
            room.team_a.append(user_id)
        else:
            room.team_b.append(user_id)
        room.connections[user_id] = ws

        await manager.send(ws, make_event(
            EventType.ROOM_JOINED,
            code=room.code,
            match_type=room.match_type,
            max_players=room.max_players,
            max_per_team=room.max_per_team,
            team=prev_team,
            team_a=room.team_a,
            team_b=room.team_b,
            usernames=room.usernames,
            score_a=room.score_a,
            score_b=room.score_b,
            current_round=room.current_round,
            status=room.status,
        ))
        await manager.broadcast_room(room.code, make_event(
            EventType.PLAYER_JOINED,
            user_id=user_id,
            username=display,
            team=prev_team,
            team_a=room.team_a,
            team_b=room.team_b,
            usernames=room.usernames,
        ))
        await _player_loop(ws, room, user_id)
        return
    # ── END RECONNECT PATH ────────────────────────────────────────────────────

    if user_id in room.kicked_users:
        await manager.send(ws, make_event(EventType.ERROR, message="Fuiste expulsado de esta sala y no puedes volver a unirte.", code="KICKED"))
        await ws.close()
        return

    if room.status != "WAITING":
        await manager.send(ws, make_event(EventType.ERROR, message="Match already in progress"))
        await ws.close()
        return

    if user_id in room.all_players:
        await manager.send(ws, make_event(EventType.ERROR, message="Already in this room"))
        await ws.close()
        return

    if room.is_full:
        await manager.send(ws, make_event(EventType.ERROR, message="Room is full"))
        await ws.close()
        return

    # Assign team
    if room.match_type == "1v1":
        assigned = "B"
    else:
        if not team or team not in ("A", "B"):
            await manager.send(ws, make_event(EventType.ERROR, message="Provide team='A' or 'B'"))
            await ws.close()
            return
        if not room.can_join_team(team):
            await manager.send(ws, make_event(EventType.ERROR, message=f"Team {team} is full"))
            await ws.close()
            return
        assigned = team

    if assigned == "A":
        room.team_a.append(user_id)
    else:
        room.team_b.append(user_id)

    display = username or user_id
    room.connections[user_id] = ws
    room.usernames[user_id] = display

    db = SessionLocal()
    try:
        _get_or_create_user(db, user_id, username)
        session = db.get(GameSession, room.session_id)
        if session:
            session.players = room.all_players
            db.commit()
    finally:
        db.close()

    # Send full room state to the joining player only
    await manager.send(ws, make_event(
        EventType.ROOM_JOINED,
        code=code,
        match_type=room.match_type,
        max_players=room.max_players,
        max_per_team=room.max_per_team,
        team=assigned,
        team_a=room.team_a,
        team_b=room.team_b,
        usernames=room.usernames,
        username=display,
    ))

    # Notify everyone else
    await manager.broadcast_room(code, make_event(
        EventType.PLAYER_JOINED,
        user_id=user_id,
        username=display,
        team=assigned,
        team_a=room.team_a,
        team_b=room.team_b,
        usernames=room.usernames,
        players_needed=room.max_players - len(room.all_players),
    ))

    if room.is_full:
        room.status = "IN_PROGRESS"
        await manager.broadcast_room(code, make_event(
            EventType.MATCH_START,
            team_a=room.team_a,
            team_b=room.team_b,
            match_type=room.match_type,
            win_score=5,
        ))
        room.match_task = asyncio.create_task(run_match(room, manager))

    await _player_loop(ws, room, user_id)


# ---------------------------------------------------------------------------
# WS /ws/dashboard  — admin/moderator live view
# ---------------------------------------------------------------------------

@router.websocket("/dashboard")
async def ws_dashboard(
    ws: WebSocket,
    api_key: str | None = Query(None),
):
    await ws.accept()

    if _scope(api_key) not in ("MODERATOR", "ADMIN"):
        await manager.send(ws, make_event(EventType.ERROR, message="Insufficient scope"))
        await ws.close()
        return

    manager.dashboard_connections.add(ws)

    # Send snapshot of active rooms
    await manager.send(ws, make_event(EventType.ROOM_LIST, rooms=manager.room_snapshot()))

    # Send current player states
    active_ids = {uid for r in manager.rooms.values() for uid in r.all_players}
    if active_ids:
        db = SessionLocal()
        try:
            for uid in active_ids:
                user = db.get(User, uid)
                if user:
                    await manager.send(ws, make_event(
                        EventType.PLAYER_STATE,
                        user_id=uid,
                        username=user.username,
                        strikes=user.strikes,
                        status=user.status,
                        toxicity_score=user.toxicity_score,
                        total_messages=user.total_messages,
                        toxic_messages=user.toxic_messages,
                    ))
        finally:
            db.close()

    try:
        while True:
            data = await ws.receive_json()

            if data.get("type") == "ping":
                await manager.send(ws, {"type": "pong"})
                continue

            if data.get("type") == "mod_action":
                payload = data.get("payload", {})
                target_id = payload.get("user_id")
                action = payload.get("action")  # BAN | KICK | TIMEOUT | WARN
                reason = payload.get("reason", "Moderator action")

                if not target_id or not action:
                    await manager.send(ws, make_event(EventType.ERROR, message="mod_action requires user_id and action"))
                    continue

                db = SessionLocal()
                try:
                    user = db.get(User, target_id)
                    if not user:
                        await manager.send(ws, make_event(EventType.ERROR, message=f"User '{target_id}' not found"))
                        continue

                    from datetime import timedelta
                    from ..models import ModerationAction

                    if action == "BAN":
                        user.status = "BANNED"
                        user.timeout_until = None
                    elif action == "KICK":
                        user.status = "TIMEOUT"
                        user.timeout_until = datetime.now(timezone.utc) + timedelta(seconds=180)
                    elif action == "TIMEOUT":
                        user.status = "TIMEOUT"
                        user.timeout_until = datetime.now(timezone.utc) + timedelta(seconds=300)
                    elif action == "WARN":
                        user.status = "WARNED"
                    elif action == "PARDON":
                        user.status = "ACTIVE"
                        user.timeout_until = None
                        user.strikes = 0
                        for r in manager.rooms.values():
                            r.kicked_users.discard(target_id)

                    db.add(ModerationAction(
                        target_user_id=target_id,
                        type=action,
                        reason=reason,
                        triggered_by="HUMAN",
                    ))
                    db.commit()
                finally:
                    db.close()

                # Notify the target player if they are in a room
                for room in manager.rooms.values():
                    if target_id in room.connections:
                        target_ws = room.connections[target_id]
                        if action == "BAN":
                            await manager.send(target_ws, make_event(EventType.ERROR, message="Has sido baneado por un moderador.", code="BANNED"))
                            await target_ws.close(code=1008)
                        elif action in ("KICK", "TIMEOUT"):
                            await manager.send(target_ws, make_event(EventType.KICKED, reason=reason))
                            await target_ws.close(code=1008)
                        elif action == "WARN":
                            await manager.send(target_ws, make_event(EventType.MODERATION, user_id=target_id, action="WARN", reason=reason))
                        elif action == "PARDON":
                            await manager.send(target_ws, make_event(EventType.MODERATION, user_id=target_id, action="PARDON", reason=reason))
                        break

                await manager.send(ws, make_event(EventType.MOD_ACK, user_id=target_id, action=action, success=True))

    except WebSocketDisconnect:
        manager.dashboard_connections.discard(ws)
