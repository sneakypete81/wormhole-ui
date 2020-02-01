from unittest import mock

from hamcrest import assert_that, is_, starts_with
import pytest

from wormhole_ui.file_transfer_protocol import FileTransferProtocol
from wormhole_ui.errors import (
    MessageError,
    OfferError,
    RefusedError,
    RemoteError,
    RespondError,
    SendFileError,
    SendTextError,
)


class TestBase:
    @pytest.fixture(autouse=True)
    def patch_wormhole(self, mocker):
        wormhole = mocker.patch("wormhole_ui.file_transfer_protocol.wormhole")
        self.wormhole = wormhole.create()
        self.wormhole_create = wormhole.create

        self.transit = mocker.patch(
            "wormhole_ui.file_transfer_protocol.TransitProtocolPair"
        )()

        self.reactor = mocker.Mock()
        self.signals = mocker.Mock()

    def connect(self, signal):
        return signal.connect.call_args[0][0]


class TestOpen(TestBase):
    def test_creates_a_wormhole(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        ftp.open(None)

        self.wormhole_create.assert_called_with(
            appid="lothar.com/wormhole/text-or-file-xfer",
            relay_url="ws://relay.magic-wormhole.io:4000/v1",
            reactor=self.reactor,
            delegate=mock.ANY,
            versions={"v0": {"mode": "connect"}},
        )

    def test_can_allocate_a_code(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)

        self.wormhole.allocate_code.assert_called()

    def test_can_set_a_code(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open("42-is-a-code")

        self.wormhole.set_code.assert_called_with("42-is-a-code")


class TestClose(TestBase):
    def test_can_close_the_wormhole_and_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp.close()

        self.wormhole.close.assert_called()
        self.transit.close.assert_called()

    def test_emits_signal_once_wormhole_is_closed(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp.close()
        ftp._wormhole_delegate.wormhole_closed(result="ok")

        self.signals.wormhole_closed.emit.assert_called()

    def test_still_emits_signal_if_wormhole_was_not_open(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.close()

        self.signals.wormhole_closed.emit.assert_called()


class TestShutdown(TestBase):
    def test_can_close_the_wormhole_and_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp.shutdown()

        self.wormhole.close.assert_called()
        self.transit.close.assert_called()

    def test_emits_signal_once_wormhole_is_closed(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp.shutdown()
        ftp._wormhole_delegate.wormhole_closed(result="ok")

        self.signals.wormhole_shutdown.emit.assert_called()

    def test_still_emits_signal_if_wormhole_is_not_open(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.shutdown()

        self.signals.wormhole_shutdown.emit.assert_called()

    def test_sends_message_if_connected_and_connect_mode_supported(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        wormhole_open = self.connect(self.signals.wormhole_open)
        versions_received = self.connect(self.signals.versions_received)

        ftp.open(None)
        wormhole_open()
        versions_received({"v0": {"mode": "connect"}})
        ftp.shutdown()

        self.wormhole.send_message.assert_called_with(b'{"command": "shutdown"}')

    def test_doesnt_send_message_if_not_connected(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        versions_received = self.connect(self.signals.versions_received)

        ftp.open(None)
        versions_received({"v0": {"mode": "connect"}})
        ftp.shutdown()

        self.wormhole.send_message.assert_not_called()

    def test_doesnt_send_message_if_already_closed(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        wormhole_open = self.connect(self.signals.wormhole_open)
        versions_received = self.connect(self.signals.versions_received)
        wormhole_closed = self.connect(self.signals.wormhole_closed)

        ftp.open(None)
        wormhole_open()
        versions_received({"v0": {"mode": "connect"}})
        wormhole_closed()
        ftp.shutdown()

        self.wormhole.send_message.assert_not_called()

    def test_doesnt_send_message_if_peer_connect_mode_not_supported(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        wormhole_open = self.connect(self.signals.wormhole_open)

        ftp.open(None)
        wormhole_open()
        ftp.shutdown()

        self.wormhole.send_message.assert_not_called()


class TestSendMessage(TestBase):
    def test_can_send_data(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp.send_message("hello world")

        self.wormhole.send_message.assert_called_with(
            b'{"offer": {"message": "hello world"}}'
        )


class TestSendFile(TestBase):
    def test_calls_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp.send_file(42, "path/to/file")

        self.transit.sender.send_file.assert_called_with(42, "path/to/file")

    def test_is_sending_file_calls_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        self.transit.sender.is_sending_file = mock.sentinel.value

        assert_that(ftp.is_sending_file(), is_(mock.sentinel.value))


class TestReceiveFile(TestBase):
    def test_calls_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp.receive_file(42, "path/to/file")

        self.transit.receiver.receive_file.assert_called_with(42, "path/to/file")

    def test_is_receiving_file_calls_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        self.transit.receiver.is_receiving_file = mock.sentinel.value

        assert_that(ftp.is_receiving_file(), is_(mock.sentinel.value))

    def test_wormhole_closed_after_receiving_file_if_connect_mode_not_supported(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        file_transfer_complete = self.connect(self.signals.file_transfer_complete)

        ftp.open(None)
        file_transfer_complete(42, "filename")

        self.wormhole.close.assert_called()

    def test_wormhole_not_closed_after_receiving_file_if_connect_mode_supported(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        versions_received = self.connect(self.signals.versions_received)
        file_transfer_complete = self.connect(self.signals.file_transfer_complete)

        ftp.open(None)
        versions_received({"v0": {"mode": "connect"}})
        file_transfer_complete(42, "filename")

        self.wormhole.close.assert_not_called()


class TestRespondError(TestBase):
    def test_sends_error_to_peer(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        respond_error = self.connect(self.signals.respond_error)

        ftp.open(None)
        respond_error(OfferError("Invalid Offer"), "traceback")

        self.wormhole.send_message.assert_called_with(b'{"error": "Invalid Offer"}')

    def test_emits_error_signals(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        respond_error = self.connect(self.signals.respond_error)

        ftp.open(None)
        respond_error(OfferError("Invalid Offer"), "traceback")

        self.signals.error.emit.assert_called()
        args = self.signals.error.emit.call_args[0]
        assert_that(args[0], is_(OfferError))
        assert_that(args[1], is_("traceback"))

    def test_refused_error_closes_wormhole(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        respond_error = self.connect(self.signals.respond_error)

        ftp.open(None)
        respond_error(RefusedError("User Cancelled"), "traceback")

        self.wormhole.send_message.assert_called_with(b'{"error": "User Cancelled"}')
        self.wormhole.close.assert_called()
        self.signals.error.emit.assert_not_called()


class TestErrorMessage(TestBase):
    def test_emits_error_signal(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"error": "message"}')

        self.signals.error.emit.assert_called_once()
        args = self.signals.error.emit.call_args[0]
        assert_that(args[0], is_(RemoteError))
        assert_that(args[1], starts_with("Traceback"))


class TestHandleMessage(TestBase):
    def test_message_offer_sends_answer(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"offer": {"message": "test"}}')

        self.wormhole.send_message.assert_called_with(
            b'{"answer": {"message_ack": "ok"}}'
        )

    def test_message_offer_emits_message_received(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"offer": {"message": "test"}}')

        self.signals.message_received.emit.assert_called_with("test")

    def test_wormhole_closed_after_receiving_message_if_connect_mode_not_supported(
        self,
    ):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"offer": {"message": "test"}}')

        self.wormhole.close.assert_called()

    def test_wormhole_not_closed_after_receiving_message_if_connect_mode_supported(
        self,
    ):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        versions_received = self.connect(self.signals.versions_received)

        ftp.open(None)
        versions_received({"v0": {"mode": "connect"}})
        ftp._wormhole_delegate.wormhole_got_message(b'{"offer": {"message": "test"}}')

        self.wormhole.close.assert_not_called()

    def test_file_offer_calls_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"offer": {"file": "test"}}')

        self.transit.receiver.handle_offer.assert_called_with({"file": "test"})

    def test_file_offer_emits_receive_pending(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        dest = mock.Mock()
        dest.name = "filename"
        dest.final_bytes = 24000
        self.transit.receiver.handle_offer.return_value = dest

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"offer": {"file": "test"}}')

        self.signals.file_receive_pending.emit.assert_called_with("filename", 24000)

    def test_invalid_offer_emits_respond_error(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        self.transit.receiver.handle_offer.side_effect = RespondError("test")

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"offer": "illegal"}')

        self.signals.respond_error.emit.assert_called()

    def test_transit_message_calls_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"transit": "contents"}')

        self.transit.handle_transit.assert_called_with("contents")

    def test_message_ack_with_ok_emits_message_sent(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(
            b'{"answer": {"message_ack": "ok"}}'
        )

        self.signals.message_sent.emit.assert_called_with(True)
        self.signals.error.emit.assert_not_called()

    def test_message_ack_with_error_emits_message_sent_and_error(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(
            b'{"answer": {"message_ack": "error"}}'
        )

        self.signals.message_sent.emit.assert_called_with(False)
        self.signals.error.emit.assert_called_once()
        args = self.signals.error.emit.call_args[0]
        assert_that(args[0], is_(SendTextError))
        assert_that(args[1], starts_with("Traceback"))

    def test_wormhole_closed_after_receiving_message_ack_if_connect_mode_not_supported(
        self,
    ):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(
            b'{"answer": {"message_ack": "ok"}}'
        )

        self.wormhole.close.assert_called()

    def test_wormhole_not_closed_after_receiving_message_ack_if_connect_mode_supported(
        self,
    ):
        ftp = FileTransferProtocol(self.reactor, self.signals)
        versions_received = self.connect(self.signals.versions_received)

        ftp.open(None)
        versions_received({"v0": {"mode": "connect"}})
        ftp._wormhole_delegate.wormhole_got_message(
            b'{"answer": {"message_ack": "ok"}}'
        )

        self.wormhole.close.assert_not_called()

    def test_file_ack_with_ok_calls_transit(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"answer": {"file_ack": "ok"}}')

        self.transit.sender.handle_file_ack.assert_called()
        self.signals.error.emit.assert_not_called()

    def test_file_ack_with_error_emits_error(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(
            b'{"answer": {"file_ack": "error"}}'
        )

        self.signals.error.emit.assert_called_once()
        args = self.signals.error.emit.call_args[0]
        assert_that(args[0], is_(SendFileError))
        assert_that(args[1], starts_with("Traceback"))

    def test_empty_message_emits_error(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b"")

        self.signals.error.emit.assert_called_once()
        args = self.signals.error.emit.call_args[0]
        assert_that(args[0], is_(MessageError))
        assert_that(args[1], starts_with("Traceback"))

    def test_invalid_json_emits_error(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_message(b'{"invalid": {"json"}')

        self.signals.error.emit.assert_called_once()
        args = self.signals.error.emit.call_args[0]
        assert_that(args[0], is_(MessageError))
        assert_that(args[1], starts_with("Traceback"))


class TestWormholeDelegate(TestBase):
    """Most of this functionality is tested elsewhere"""
    def test_got_code_emits_signal(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_code("1-a-code")

        self.signals.code_received.emit.assert_called_once_with("1-a-code")

    def test_got_versions_emits_signals(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._wormhole_delegate.wormhole_got_versions("versions")

        self.signals.versions_received.emit.assert_called_once_with("versions")
        self.signals.wormhole_open.emit.assert_called_once()


class TestTransitDelegate(TestBase):
    def test_transit_progress_emits_signal(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._transit_delegate.transit_progress(42, 50, 100)

        self.signals.file_transfer_progress.emit.assert_called_once_with(42, 50, 100)

    def test_transit_complete_emits_signal(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._transit_delegate.transit_complete(42, "filename")

        self.signals.file_transfer_complete.emit.assert_called_once_with(42, "filename")

    def test_transit_error_emits_signal(self):
        ftp = FileTransferProtocol(self.reactor, self.signals)

        ftp.open(None)
        ftp._transit_delegate.transit_error(ValueError("error"), "traceback")

        self.signals.error.emit.assert_called_once()
        args = self.signals.error.emit.call_args[0]
        assert_that(args[0], is_(ValueError))
        assert_that(args[1], is_("traceback"))
