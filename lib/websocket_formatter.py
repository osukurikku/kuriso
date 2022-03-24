from enum import unique, Enum

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.BanchoObjects import Message
    from objects.Channel import Channel
    from objects.WebsocketPlayer import WebsocketPlayer


@unique
class WebsocketEvents(str, Enum):
    # base
    PING = "PING"
    PONG = "PONG"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    NOTIFICATION = "NOTIFICATION"

    # chat
    JOIN_CHANNEL = "JOIN_CHANNEL"
    FAILED_JOIN_CHANNEL = "FAILED_JOIN_CHANNEL"
    PART_CHANNEL = "PART_CHANNEL"
    SEND_MESSAGE = "SEND_MESSAGE"
    RECEIVE_MESSAGE = "RECEIVE_MESSAGE"
    CHANNEL_STATS = "CHANNEL_STATS"

    # user communication
    USER_JOINED = "USER_JOINED"
    USER_LEAVED = "USER_LEAVED"
    MESSAGE_SEND_FAILED = "MESSAGE_SEND_FAILED"


@unique
class WebsocketErrors(str, Enum):
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    CONN_REJECTED = "CONN_REJECTED"
    NO_ACCESS = "NO_ACCESS"


class WebsocketEvent:
    @staticmethod
    def base_event_response(event: WebsocketEvents, data: dict) -> dict:
        return {"event": event.value, "data": data}

    @staticmethod
    def base_error_event_response(error: WebsocketErrors, data: dict) -> dict:
        return {
            "error": {"code": error.value, "data": data},
        }

    @staticmethod
    def build_message(from_id: int, message: "Message"):
        return WebsocketEvent.base_event_response(
            WebsocketEvents.RECEIVE_MESSAGE,
            {
                "sender": message.sender,
                "message": message.body,
                "to": message.to,
                "from": from_id,
            },
        )

    @staticmethod
    def join_channel(name):
        return WebsocketEvent.base_event_response(WebsocketEvents.JOIN_CHANNEL, {"name": name})

    @staticmethod
    def part_channel(name):
        return WebsocketEvent.base_event_response(WebsocketEvents.PART_CHANNEL, {"name": name})

    @staticmethod
    def channel_users(channel: "Channel"):
        def prepare_users():
            return [{token.id: token.name} for token in channel.users]

        return WebsocketEvent.base_event_response(
            WebsocketEvents.CHANNEL_STATS,
            {"name": channel.server_name, "users": prepare_users()},
        )

    @staticmethod
    def user_leaved(uid: int):
        return WebsocketEvent.base_event_response(WebsocketEvents.USER_LEAVED, {"id": uid})

    @staticmethod
    def user_joined(uid: int):
        return WebsocketEvent.base_event_response(WebsocketEvents.USER_JOINED, {"id": uid})

    @staticmethod
    def failed_message(reason: str):
        return WebsocketEvent.base_event_response(
            WebsocketEvents.MESSAGE_SEND_FAILED, {"reason": reason}
        )

    @staticmethod
    def error_disconnect(reason: str):
        return WebsocketEvent.base_event_response(
            WebsocketEvents.DISCONNECTED, {"reason": reason}
        )

    @staticmethod
    def ping():
        return WebsocketEvent.base_event_response(WebsocketEvents.PING, {})

    @staticmethod
    def welcome_message(player: "WebsocketPlayer"):
        return WebsocketEvent.base_event_response(
            WebsocketEvents.CONNECTED,
            {
                "id": player.id,
                "username": player.name,
                "safe_name": player.safe_name,
                "bancho_privs": player.bancho_privs,
                "privileges": player.privileges,
                "silence_end_time": player.silence_end,
            },
        )
