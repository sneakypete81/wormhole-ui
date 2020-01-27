import json
import logging
import traceback

from PySide2.QtCore import QObject, Slot
import wormhole
from wormhole.cli import public_relay
from wormhole.errors import LonelyError

from .errors import (
    RefusedError,
    RemoteError,
    RespondError,
    SendFileError,
    SendTextError,
)
from .timeout import Timeout
from .transit_protocol_pair import TransitProtocolPair

TIMEOUT_SECONDS = 2
APPID = "lothar.com/wormhole/text-or-file-xfer"


class FileTransferProtocol(QObject):
    def __init__(self, reactor, signals):
        self._reactor = reactor
        self._wormhole = None
        self._is_wormhole_connected = False
        self._transit = None
        self._peer_versions = {}
        self._wormhole_delegate = WormholeDelegate(signals, self._handle_message)
        self._transit_delegate = TransitDelegate(signals)
        self._timeout = Timeout(reactor, TIMEOUT_SECONDS)

        self._signals = signals
        self._signals.versions_received.connect(self._on_versions_received)
        self._signals.wormhole_open.connect(self._on_wormhole_open)
        self._signals.wormhole_closed.connect(self._on_wormhole_closed)
        self._signals.file_transfer_complete.connect(self._on_file_transfer_complete)
        self._signals.respond_error.connect(self._on_respond_error)

    def open(self, code):
        logging.debug("open wormhole")
        assert self._wormhole is None

        self._wormhole = wormhole.create(
            appid=APPID,
            relay_url=public_relay.RENDEZVOUS_RELAY,
            reactor=self._reactor,
            delegate=self._wormhole_delegate,
            versions={"v0": {"mode": "connect"}},
        )

        self._transit = TransitProtocolPair(
            self._reactor, self._wormhole, self._transit_delegate
        )

        if code is None or code == "":
            self._wormhole.allocate_code()
        else:
            self._wormhole.set_code(code)

    def close(self):
        logging.debug("close wormhole")
        if self._wormhole is None:
            self._signals.wormhole_closed.emit()
        else:
            self._transit.close()
            self._wormhole.close()

    def shutdown(self):
        logging.debug("shutdown wormhole")
        if self._wormhole is None:
            self._signals.wormhole_shutdown.emit()
        else:
            if self._is_wormhole_connected and self._peer_supports_connect_mode():
                self.send_command("shutdown")

            self._wormhole_delegate.shutdown()
            self.close()

    @Slot()
    def _on_wormhole_open(self):
        self._is_wormhole_connected = True

    @Slot()
    def _on_wormhole_closed(self):
        self._wormhole = None
        self._is_wormhole_connected = False

    @Slot(dict)
    def _on_versions_received(self, versions):
        self._peer_versions = versions

    @Slot(int, str)
    def _on_file_transfer_complete(self, id, filename):
        if not self._peer_supports_connect_mode():
            self.close()

    @Slot(Exception, str)
    def _on_respond_error(self, exception, traceback):
        self._send_data({"error": str(exception)})
        if isinstance(exception, RefusedError):
            self.close()
            return
        self._signals.error.emit(exception, traceback)

    def _peer_supports_connect_mode(self):
        if "v0" not in self._peer_versions:
            return False
        return self._peer_versions["v0"].get("mode") == "connect"

    def send_message(self, message):
        self._send_data({"offer": {"message": message}})

    def send_command(self, command):
        self._send_data({"command": command})

    def send_file(self, id, file_path):
        self._transit.sender.send_file(id, file_path)

    def receive_file(self, id, dest_path):
        self._transit.receiver.receive_file(id, dest_path)

    def is_sending_file(self):
        return self._transit.sender.is_sending_file

    def is_receiving_file(self):
        return self._transit.sender.is_receiving_file

    def _send_data(self, data):
        assert isinstance(data, dict)
        logging.debug(f"Sending: {data}")
        self._wormhole.send_message(json.dumps(data).encode("utf-8"))

    def _handle_message(self, data_bytes):
        data = json.loads(data_bytes.decode("utf-8"))
        if "error" in data:
            raise RemoteError(data["error"])

        for key, contents in data.items():
            if key == "offer":
                self._handle_offer(contents)

            elif key == "transit":
                self._transit.handle_transit(contents)

            elif key == "command" and contents == "shutdown":
                self._signals.wormhole_shutdown_received.emit()
                self.close()

            elif key == "answer" and "message_ack" in contents:
                result = contents["message_ack"]
                is_ok = result == "ok"
                self._signals.message_sent.emit(is_ok)
                if not is_ok:
                    raise SendTextError(result)
                if not self._peer_supports_connect_mode():
                    self.close()

            elif key == "answer" and "file_ack" in contents:
                result = contents["file_ack"]
                if result == "ok":
                    self._transit.sender.handle_file_ack()
                else:
                    raise SendFileError(result)

            else:
                logging.warning(f"Unexpected data received: {key}: {contents}")

    def _handle_offer(self, offer):
        if "message" in offer:
            self._send_data({"answer": {"message_ack": "ok"}})
            self._signals.message_received.emit(offer["message"])
            if not self._peer_supports_connect_mode():
                self.close()
        else:
            dest = self._transit.receiver.handle_offer(offer)
            self._signals.file_receive_pending.emit(dest.name, dest.final_bytes)


class WormholeDelegate:
    def __init__(self, signals, message_handler):
        self._signals = signals
        self._message_handler = message_handler
        self._shutting_down = False

    def shutdown(self):
        self._shutting_down = True

    def wormhole_got_welcome(self, welcome):
        logging.debug(f"wormhole_got_welcome: {welcome}")

    def wormhole_got_code(self, code):
        logging.debug(f"wormhole_got_code: {code}")
        self._signals.code_received.emit(code)

    def wormhole_got_unverified_key(self, key):
        logging.debug(f"wormhole_got_unverified_key: {key}")

    def wormhole_got_verifier(self, verifier):
        logging.debug(f"wormhole_got_verifier: {verifier}")

    def wormhole_got_versions(self, versions):
        logging.debug(f"wormhole_got_versions: {versions}")
        self._signals.versions_received.emit(versions)
        self._signals.wormhole_open.emit()

    def wormhole_got_message(self, data):
        logging.debug(f"wormhole_got_message: {data}")
        try:
            self._message_handler(data)
        except RespondError as exception:
            self._signals.respond_error.emit(exception.cause, traceback.format.exc())
        except Exception as exception:
            self._signals.error.emit(exception, traceback.format_exc())

    def wormhole_closed(self, result):
        logging.debug(f"wormhole_closed: {repr(result)}")
        if self._shutting_down:
            logging.debug("Emit wormhole_shutdown")
            self._signals.wormhole_shutdown.emit()
        else:
            if isinstance(result, LonelyError):
                pass
            elif isinstance(result, Exception):
                self._signals.error.emit(result, None)
            self._signals.wormhole_closed.emit()


class TransitDelegate:
    def __init__(self, signals):
        self._signals = signals

    def transit_progress(self, id, transferred_bytes, total_bytes):
        self._signals.file_transfer_progress.emit(id, transferred_bytes, total_bytes)

    def transit_complete(self, id, filename):
        logging.debug(f"transit_complete: {id}, {filename}")
        self._signals.file_transfer_complete.emit(id, filename)

    def transit_error(self, exception, traceback=None):
        self._signals.error.emit(exception, traceback)
