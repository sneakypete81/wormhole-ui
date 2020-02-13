from binascii import hexlify
import hashlib
import json
import logging
from pathlib import Path

import twisted.internet
from twisted.internet import defer
import twisted.protocols
from wormhole.cli import public_relay
from wormhole.transit import TransitSender

from .transit_protocol_base import TransitProtocolBase
from .errors import SendFileError
from .progress import Progress


class TransitProtocolSender(TransitProtocolBase):
    def __init__(self, reactor, wormhole, delegate):
        transit = TransitSender(
            transit_relay=public_relay.TRANSIT_RELAY, reactor=reactor,
        )
        super().__init__(wormhole, delegate, transit)

        self._send_transit_deferred = None
        self._transfer_file_deferred = None
        self._source = None
        self._pipe = None

        self._transit_handshake_complete = False
        self.awaiting_transit_response = False
        self.is_sending_file = False

    def send_file(self, id, file_path):
        logging.debug("TransitProtocolSender::send_file")
        assert not self.is_sending_file
        self.is_sending_file = True

        self._source = SourceFile(id, file_path)
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
        if self._pipe is None:
            self._pipe = yield self._transit.connect()

        logging.info(f"Sending ({self._pipe.describe()})..")

        sender = twisted.protocols.basic.FileSender()
        hasher = hashlib.sha256()
        progress = Progress(
            self._delegate, self._source.id, self._source.transfer_bytes
        )

        def _update(data):
            hasher.update(data)
            progress.update(len(data))
            return data

        if self._source.final_bytes > 0:
            yield sender.beginFileTransfer(
                self._source.file_object, self._pipe, transform=_update
            )

        expected_hash = hexlify(hasher.digest()).decode("ascii")

        logging.info("File sent, awaiting confirmation")

        ack_bytes = yield self._pipe.receive_record()
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
        self.is_sending_file = False

        if self._pipe is not None:
            self._pipe.close()
        if self._send_transit_deferred is not None:
            self._send_transit_deferred.cancel()
        if self._transfer_file_deferred is not None:
            self._transfer_file_deferred.cancel()


class SourceFile:
    def __init__(self, id, file_path):
        file_path = Path(file_path).resolve()
        assert file_path.exists()

        self.id = id
        self.name = file_path.name
        self.full_path = file_path
        self.final_bytes = None
        self.transfer_bytes = None
        self.file_object = None

    def open(self):
        self.file_object = f = open(self.full_path, "rb")
        f.seek(0, 2)
        self.final_bytes = f.tell()
        self.transfer_bytes = self.final_bytes
        f.seek(0, 0)
