from enum import StrEnum


class EventType(StrEnum):
    # Game flow
    ROOM_CREATED = "room_created"
    ROOM_JOINED = "room_joined"
    PLAYER_JOINED = "player_joined"
    MATCH_START = "match_start"
    ROUND_START = "round_start"
    KILL_FEED = "kill_feed"
    ROUND_END = "round_end"
    MATCH_END = "match_end"
    PLAYER_LEFT = "player_left"
    KICKED = "kicked"
    TIMED_OUT = "timed_out"
    # Chat & moderation
    CHAT = "chat"
    MODERATION = "moderation"
    # Dashboard
    ROOM_LIST = "room_list"
    PLAYER_STATE = "player_state"
    # Utility
    ERROR = "error"
    PONG = "pong"


def make_event(type: EventType | str, **payload) -> dict:
    return {"type": str(type), "payload": payload}
