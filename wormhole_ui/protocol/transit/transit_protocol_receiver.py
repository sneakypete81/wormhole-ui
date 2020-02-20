import logging

from twisted.internet import defer
from wormhole.cli import public_relay
from wormhole.transit import TransitReceiver

from .dest_file import DestFile
from ...errors import (
    OfferError,
    RespondError,
)
from .file_receiver import FileReceiver
from .progress import Progress
from .transit_protocol_base import TransitProtocolBase


class TransitProtocolReceiver(TransitProtocolBase):
    def __init__(self, reactor, wormhole, delegate):
        transit = TransitReceiver(
            transit_relay=public_relay.TRANSIT_RELAY, reactor=reactor,
        )
        super().__init__(wormhole, delegate, transit)

        self._file_receiver = FileReceiver(transit)
        self._send_transit_deferred = None
        self._receive_file_deferred = None

    def handle_offer(self, offer):
        if "file" not in offer:
            raise RespondError(OfferError(f"Unknown offer: {offer}"))

        filename = offer["file"]["filename"]
        filesize = offer["file"]["filesize"]
        return DestFile(filename, filesize)

    def receive_file(self, dest_file, receive_finished_handler):
        self._send_data({"answer": {"file_ack": "ok"}})

        self._receive_file_deferred = self._receive_file(dest_file)
        self._receive_file_deferred.addErrback(self._on_deferred_error)
        self._receive_file_deferred.addBoth(lambda _: receive_finished_handler())

    @defer.inlineCallbacks
    def _receive_file(self, dest_file):
        progress = Progress(self._delegate, dest_file.id, dest_file.transfer_bytes)

        yield self._file_receiver.open()
        datahash = yield self._file_receiver.receive(dest_file, progress)

        dest_file.finalise()
        yield self._file_receiver.send_ack(datahash)

        logging.info("File received, transfer complete")
        self._delegate.transit_complete(dest_file.id, dest_file.name)

    def close(self):
        super().close()

        self._file_receiver.close()
        if self._send_transit_deferred is not None:
            self._send_transit_deferred.cancel()
        if self._receive_file_deferred is not None:
            self._receive_file_deferred.cancel()
