class WormholeGuiError(Exception):
    pass


class RespondError(WormholeGuiError):
    """Error that needs to be signalled across the wormhole"""

    def __init__(self, cause):
        self.cause = cause


class RemoteError(WormholeGuiError):
    """Error that was signaled from the other end of the wormhole"""

    pass


class SendTextError(WormholeGuiError):
    """Other side sent message_ack not ok"""

    pass


class SendFileError(WormholeGuiError):
    """Other side sent file_ack not ok"""

    pass


class ReceiveFileError(WormholeGuiError):
    """Transit connection closed before full file was received"""

    pass


class OfferError(WormholeGuiError):
    """Invalid offer received"""

    pass


class DiskSpaceError(WormholeGuiError):
    """Couldn't receive a file due to low disk space"""

    pass


class RefusedError(WormholeGuiError):
    """The file transfer was refused"""

    pass
