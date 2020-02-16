import traceback

from PySide2.QtCore import QObject, Signal, Slot
from twisted.internet.defer import CancelledError

from .errors import RefusedError, RespondError
from .file_transfer_protocol import FileTransferProtocol


class WormholeSignals(QObject):
    code_received = Signal(str)
    versions_received = Signal(dict)
    wormhole_open = Signal()
    wormhole_closed = Signal()
    wormhole_shutdown = Signal()
    wormhole_shutdown_received = Signal()
    message_sent = Signal(bool)
    message_received = Signal(str)
    file_receive_pending = Signal(str, int)
    file_transfer_progress = Signal(int, int, int)
    file_transfer_complete = Signal(int, str)
    error = Signal(Exception, str)
    respond_error = Signal(Exception, str)


class WormholeController:
    def __init__(self, reactor):
        super().__init__()
        self.signals = WormholeSignals()
        self._protocol = FileTransferProtocol(reactor, self.signals)

    @Slot(str)
    def open(self, code=None):
        self._capture_errors(self._protocol.open, code)

    @Slot(str)
    def set_code(self, code):
        @Slot(str)
        def open_with_code():
            self.signals.wormhole_closed.disconnect(open_with_code)
            self.open(code)

        self.signals.wormhole_closed.connect(open_with_code)
        self.close()

    @Slot()
    def close(self):
        self._capture_errors(self._protocol.close)

    @Slot()
    def shutdown(self):
        self._capture_errors(self._protocol.shutdown)

    @Slot()
    def send_message(self, message):
        self._capture_errors(self._protocol.send_message, message)

    @Slot(str, str)
    def send_file(self, id, file_path):
        self._capture_errors(self._protocol.send_file, id, file_path)

    @Slot(str, str)
    def receive_file(self, id, dest_path):
        self._capture_errors(self._protocol.receive_file, id, dest_path)

    @Slot()
    def reject_file(self):
        self.signals.respond_error.emit(
            RefusedError("The file was refused by the user"), None
        )

    def is_receiving_file(self):
        return self._protocol.is_receiving_file()

    def is_sending_file(self):
        return self._protocol.is_sending_file()

    def _capture_errors(self, command, *args, **kwds):
        try:
            command(*args, **kwds)
        except CancelledError:
            pass
        except RespondError as exception:
            self.signals.respond_error.emit(exception.cause, traceback.format.exc())
        except Exception as exception:
            self.signals.error.emit(exception, traceback.format_exc())
