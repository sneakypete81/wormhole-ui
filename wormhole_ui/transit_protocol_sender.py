import json
import logging

from twisted.internet import defer
from wormhole.cli import public_relay
from wormhole.transit import TransitSender

from .transit_protocol_base import TransitProtocolBase
from .errors import SendFileError
from .progress import Progress
from .file_sender import FileSender


class TransitProtocolSender(TransitProtocolBase):
    def __init__(self, reactor, wormhole, delegate):
        transit = TransitSender(
            transit_relay=public_relay.TRANSIT_RELAY, reactor=reactor,
        )
        super().__init__(wormhole, delegate, transit)

        self._file_sender = FileSender(transit)
        self._send_transit_deferred = None
        self._transfer_file_deferred = None
        self._source = None

        self._transit_handshake_complete = False
        self.awaiting_transit_response = False
        self.is_sending_file = False

    def send_file(self, source_file):
        logging.debug("TransitProtocolSender::send_file")
        assert not self.is_sending_file
        self.is_sending_file = True

        self._source = source_file
        self._source.open()

        if not self._transit_handshake_complete:
            self.awaiting_transit_response = True
            self._send_transit_deferred = self._send_transit()
            self._send_transit_deferred.addErrback(self._on_deferred_error)
        else:
            self._send_offer()

    def handle_transit(self, transit_message):
        logging.debug("TransitProtocolSender::handle_transit")
        assert self.is_sending_file

        if not self._transit_handshake_complete:
            self._transit_handshake_complete = True
            super().handle_transit(transit_message)

        self.awaiting_transit_response = False
        self._send_offer()

    def _send_offer(self):
        self._send_data(
            {
                "offer": {
                    "file": {
                        "filename": self._source.name,
                        "filesize": self._source.final_bytes,
                    },
                }
            }
        )

    def handle_file_ack(self):
        assert self.is_sending_file

        self._transfer_file_deferred = self._transfer_file()
        self._transfer_file_deferred.addErrback(self._on_deferred_error)

    @defer.inlineCallbacks
    def _transfer_file(self):
        progress = Progress(
            self._delegate, self._source.id, self._source.transfer_bytes
        )

        yield self._file_sender.open()
        expected_hash = yield self._file_sender.send(self._source, progress)
        logging.info("File sent, awaiting confirmation")
        ack_bytes = yield self._file_sender.wait_for_ack()

        self.is_sending_file = False

        ack = json.loads(ack_bytes.decode("utf-8"))
        ok = ack.get("ack", "")
        if ok != "ok":
            raise SendFileError(f"Transfer failed: {ack}")
        if "sha256" in ack:
            if ack["sha256"] != expected_hash:
                raise SendFileError("Transfer failed (bad remote hash)")

        logging.info("Confirmation received, transfer complete")
        self._delegate.transit_complete(self._source.id, self._source.name)

    def close(self):
        self._transit_handshake_complete = False
        self.awaiting_transit_response = False
        self.is_sending_file = False

        self._file_sender.close()
        if self._send_transit_deferred is not None:
            self._send_transit_deferred.cancel()
        if self._transfer_file_deferred is not None:
            self._transfer_file_deferred.cancel()
