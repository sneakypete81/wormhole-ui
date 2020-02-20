from binascii import hexlify
import hashlib
import json
import logging

import twisted.internet
from twisted.internet import defer
import twisted.protocols

from ...errors import SendFileError


class FileSender:
    def __init__(self, transit):
        self._transit = transit
        self._pipe = None

    @defer.inlineCallbacks
    def open(self):
        if self._pipe is None:
            self._pipe = yield self._transit.connect()

    def close(self):
        if self._pipe is not None:
            self._pipe.close()
            self._pipe = None

    @defer.inlineCallbacks
    def send(self, source_file, progress):
        logging.info(f"Sending ({self._pipe.describe()})..")
        sender = twisted.protocols.basic.FileSender()
        hasher = hashlib.sha256()

        def _update(data):
            hasher.update(data)
            progress.update(len(data))
            return data

        if source_file.final_bytes > 0:
            yield sender.beginFileTransfer(
                source_file.file_object, self._pipe, transform=_update
            )
        return hexlify(hasher.digest()).decode("ascii")

    @defer.inlineCallbacks
    def wait_for_ack(self):
        ack_bytes = yield self._pipe.receive_record()
        ack = json.loads(ack_bytes.decode("utf-8"))

        ok = ack.get("ack", "")
        if ok != "ok":
            raise SendFileError(f"Transfer failed: {ack}")

        return ack.get("sha256", None)
