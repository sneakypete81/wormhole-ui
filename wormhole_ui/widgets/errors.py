from twisted.internet.error import ConnectionClosed

from wormhole.errors import ServerConnectionError

from ..errors import RemoteError


EXCEPTION_CLASS_MAP = {
    ServerConnectionError: "Could not connect to the Magic Wormhole server",
    ConnectionClosed: "The wormhole connection has closed",
}


EXCEPTION_MESSAGE_MAP = {
    "Exception: Consumer asked us to stop producing": (
        "The wormhole connection has closed"
    )
}


def get_error_text(exception):
    exception_message = f"{exception.__class__.__name__}: {exception}"
    if exception_message in EXCEPTION_MESSAGE_MAP:
        return EXCEPTION_MESSAGE_MAP[exception_message]
    if exception.__class__ in EXCEPTION_CLASS_MAP:
        return EXCEPTION_CLASS_MAP[exception.__class__]
    if exception.__class__ == RemoteError:
        return str(exception)

    return exception_message
