from binascii import hexlify
import hashlib
import json

from twisted.internet import defer

from ...errors import ReceiveFileError


class FileReceiver:
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
    def receive(self, dest_file, progress):
        hasher = hashlib.sha256()
        received = yield self._pipe.writeToFile(
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
    def send_ack(self, datahash):
        datahash_hex = hexlify(datahash).decode("ascii")
        ack = {"ack": "ok", "sha256": datahash_hex}
        ack_bytes = json.dumps(ack).encode("utf-8")

        yield self._pipe.send_record(ack_bytes)
