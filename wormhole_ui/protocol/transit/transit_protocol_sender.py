import logging

from twisted.internet import defer
from wormhole.cli import public_relay
from wormhole.transit import TransitSender

from ...errors import SendFileError
from .file_sender import FileSender
from .progress import Progress
from .transit_protocol_base import TransitProtocolBase


class TransitProtocolSender(TransitProtocolBase):
    def __init__(self, reactor, wormhole, delegate):
        transit = TransitSender(
            transit_relay=public_relay.TRANSIT_RELAY, reactor=reactor,
        )
        super().__init__(wormhole, delegate, transit)

        self._file_sender = FileSender(transit)
        self._send_file_deferred = None

    def send_offer(self, source_file):
        self._send_data(
            {
                "offer": {
                    "file": {
                        "filename": source_file.name,
                        "filesize": source_file.final_bytes,
                    },
                }
            }
        )

    def send_file(self, source_file, send_finished_handler):
        self._send_file_deferred = self._send_file(source_file)
        self._send_file_deferred.addErrback(self._on_deferred_error)
        self._send_file_deferred.addBoth(lambda _: send_finished_handler())

    @defer.inlineCallbacks
    def _send_file(self, source_file):
        progress = Progress(self._delegate, source_file.id, source_file.transfer_bytes)

        yield self._file_sender.open()
        expected_hash = yield self._file_sender.send(source_file, progress)

        logging.info("File sent, awaiting confirmation")
        ack_hash = yield self._file_sender.wait_for_ack()
        if ack_hash is not None and ack_hash != expected_hash:
            raise SendFileError("Transfer failed (bad remote hash)")

        logging.info("Confirmation received, transfer complete")
        self._delegate.transit_complete(source_file.id, source_file.name)

    def close(self):
        super().close()

        self._file_sender.close()
        if self._send_file_deferred is not None:
            self._send_file_deferred.cancel()
