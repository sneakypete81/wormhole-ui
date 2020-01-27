from binascii import hexlify
import hashlib
import json
import logging
import os
from pathlib import Path

import twisted.internet
from twisted.internet import defer
import twisted.protocols
from wormhole.cli import public_relay
from wormhole.transit import TransitReceiver, TransitSender

from .errors import (
    DiskSpaceError,
    OfferError,
    ReceiveFileError,
    RespondError,
    SendFileError,
)
from .progress import Progress


class _TransitProtocol:
    def __init__(self, wormhole, delegate, transit):
        self._wormhole = wormhole
        self._delegate = delegate
        self._transit = transit

    def handle_transit(self, transit_message):
        self._add_hints(transit_message)
        self._derive_key()

    @defer.inlineCallbacks
    def _send_transit(self):
        our_abilities = self._transit.get_connection_abilities()
        our_hints = yield self._transit.get_connection_hints()
        our_transit_message = {
            "abilities-v1": our_abilities,
            "hints-v1": our_hints,
        }
        self._send_data({"transit": our_transit_message})

    def _derive_key(self):
        # Fixed APPID (see https://github.com/warner/magic-wormhole/issues/339)
        BUG339_APPID = "lothar.com/wormhole/text-or-file-xfer"
        transit_key = self._wormhole.derive_key(
            BUG339_APPID + "/transit-key", self._transit.TRANSIT_KEY_LENGTH
        )
        self._transit.set_transit_key(transit_key)

    def _add_hints(self, transit_message):
        hints = transit_message.get("hints-v1", [])
        if hints:
            self._transit.add_connection_hints(hints)

    def _send_data(self, data):
        assert isinstance(data, dict)
        logging.debug(f"Sending: {data}")
        self._wormhole.send_message(json.dumps(data).encode("utf-8"))

    def _on_deferred_error(self, failure):
        self._delegate.transit_error(
            exception=failure.value,
            traceback=failure.getTraceback(elideFrameworkCode=True),
        )


class TransitProtocolReceiver(_TransitProtocol):
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

        self._send_transit_deferred = self._send_transit()
        self._send_transit_deferred.addErrback(self._on_deferred_error)

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


class TransitProtocolSender(_TransitProtocol):
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


class DestFile:
    def __init__(self, file_offer):
        self.id = None
        # Path().name is intended to protect us against
        # "~/.ssh/authorized_keys" and other attacks
        self.name = Path(file_offer["filename"]).name
        self.full_path = None
        self.final_bytes = file_offer["filesize"]
        self.transfer_bytes = self.final_bytes
        self.file_object = None
        self._temp_path = None

    def open(self, id, dest_path):
        self.id = id
        self.full_path = Path(dest_path).resolve() / self.name
        self._temp_path = _find_unique_path(
            self.full_path.with_suffix(self.full_path.suffix + ".part")
        )

        if not _has_disk_space(self.full_path, self.transfer_bytes):
            raise RespondError(
                DiskSpaceError(
                    f"Insufficient free disk space (need {self.transfer_bytes}B)"
                )
            )

        self.file_object = open(self._temp_path, "wb")

    def finalise(self):
        self.file_object.close()

        self.full_path = _find_unique_path(self.full_path)
        self.name = self.full_path.name
        return self._temp_path.rename(self.full_path)

    def cleanup(self):
        self.file_object.close()
        try:
            self._temp_path.unlink()
        except Exception:
            pass


def _find_unique_path(path):
    path_attempt = path
    count = 1
    while path_attempt.exists():
        path_attempt = path.with_suffix(f".{count}" + path.suffix)
        count += 1

    return path_attempt


def _has_disk_space(target, target_size):
    # f_bfree is the blocks available to a root user. It might be more
    # accurate to use f_bavail (blocks available to non-root user), but we
    # don't know which user is running us, and a lot of installations don't
    # bother with reserving extra space for root, so let's just stick to the
    # basic (larger) estimate.
    try:
        s = os.statvfs(target.parent)
        return s.f_frsize * s.f_bfree > target_size
    except AttributeError:
        return True
