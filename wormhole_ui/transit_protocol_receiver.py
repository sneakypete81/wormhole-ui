from binascii import hexlify
import hashlib
import json
import logging

from twisted.internet import defer
from wormhole.cli import public_relay
from wormhole.transit import TransitReceiver

from .transit_protocol_base import TransitProtocolBase
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
        self._pipe = None

    def handle_offer(self, offer):
        if "file" not in offer:
            raise RespondError(OfferError(f"Unknown offer: {offer}"))

        return offer["file"]

    def receive_file(self, dest_file, receive_finished_handler):
        self._send_data({"answer": {"file_ack": "ok"}})

        self._receive_file_deferred = self._receive_file(dest_file)
        self._receive_file_deferred.addErrback(self._on_deferred_error)
        self._receive_file_deferred.addBoth(lambda _: receive_finished_handler())

    @defer.inlineCallbacks
    def _receive_file(self, dest_file):
        if self._pipe is None:
            self._pipe = yield self._transit.connect()

        datahash = yield self._transfer_data(self._pipe, dest_file)
        dest_file.finalise()
        yield self._close_transit(self._pipe, datahash)

        logging.info("File received, transfer complete")
        self._delegate.transit_complete(dest_file.id, dest_file.name)

    @defer.inlineCallbacks
    def _transfer_data(self, pipe, dest_file):
        hasher = hashlib.sha256()
        progress = Progress(self._delegate, dest_file.id, dest_file.transfer_bytes)
        received = yield pipe.writeToFile(
            dest_file.file_object,
            dest_file.transfer_bytes,
            progress=progress.update,
            hasher=hasher.update,
        )
        datahash = hasher.digest()

        if received < dest_file.transfer_bytes:
            raise ReceiveFileError("Connection dropped before full file received")
        assert received == dest_file.transfer_bytes
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
