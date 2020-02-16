from binascii import hexlify
import hashlib
import json
import logging

from twisted.internet import defer
from wormhole.cli import public_relay
from wormhole.transit import TransitReceiver

from .transit_protocol_base import TransitProtocolBase
from .dest_file import DestFile
from .errors import (
    OfferError,
    ReceiveFileError,
    RespondError,
)
from .progress import Progress


class TransitProtocolReceiver(TransitProtocolBase):
    def __init__(self, reactor, wormhole, delegate):
        transit = TransitReceiver(
            transit_relay=public_relay.TRANSIT_RELAY, reactor=reactor,
        )
        super().__init__(wormhole, delegate, transit)

        self._send_transit_deferred = None
        self._receive_file_deferred = None
        self._transit_handshake_complete = False
        self._dest = None
        self._pipe = None

        self.is_receiving_file = False

    def handle_transit(self, transit_message):
        logging.debug("TransitProtocolReceiver::handle_transit")
        assert not self.is_receiving_file

        if not self._transit_handshake_complete:
            self._transit_handshake_complete = True
            super().handle_transit(transit_message)

        self.send_transit()

    def handle_offer(self, offer):
        assert not self.is_receiving_file

        if "file" in offer:
            self._dest = DestFile(offer["file"])
            return self._dest

        else:
            raise RespondError(OfferError(f"Unknown offer: {offer}"))

    def receive_file(self, id, dest_path):
        assert self._dest is not None
        assert not self.is_receiving_file

        self._send_data({"answer": {"file_ack": "ok"}})
        self._dest.open(id, dest_path)

        self._receive_file_deferred = self._receive_file()
        self._receive_file_deferred.addErrback(self._on_deferred_error)

    @defer.inlineCallbacks
    def _receive_file(self):
        self.is_receiving_file = True
        try:
            if self._pipe is None:
                self._pipe = yield self._transit.connect()

            datahash = yield self._transfer_data(self._pipe)
            self._dest.finalise()
            yield self._close_transit(self._pipe, datahash)

            logging.info("File received, transfer complete")
        finally:
            self.is_receiving_file = False
            self._dest.cleanup()

        self._delegate.transit_complete(self._dest.id, self._dest.name)

    @defer.inlineCallbacks
    def _transfer_data(self, pipe):
        hasher = hashlib.sha256()
        progress = Progress(self._delegate, self._dest.id, self._dest.transfer_bytes)
        received = yield pipe.writeToFile(
            self._dest.file_object,
            self._dest.transfer_bytes,
            progress=progress.update,
            hasher=hasher.update,
        )
        datahash = hasher.digest()

        if received < self._dest.transfer_bytes:
            raise ReceiveFileError("Connection dropped before full file received")
        assert received == self._dest.transfer_bytes
        return datahash

    @defer.inlineCallbacks
    def _close_transit(self, pipe, datahash):
        datahash_hex = hexlify(datahash).decode("ascii")
        ack = {"ack": "ok", "sha256": datahash_hex}
        ack_bytes = json.dumps(ack).encode("utf-8")

        yield pipe.send_record(ack_bytes)

    def close(self):
        if self._pipe is not None:
            self._pipe.close()
        if self._send_transit_deferred is not None:
            self._send_transit_deferred.cancel()
        if self._receive_file_deferred is not None:
            self._receive_file_deferred.cancel()
