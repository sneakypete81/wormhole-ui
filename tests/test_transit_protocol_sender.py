from hamcrest import assert_that, is_, starts_with
import pytest
from twisted.internet import defer

from wormhole_ui.errors import SendFileError
from wormhole_ui.protocol.transit.transit_protocol_sender import TransitProtocolSender
from wormhole_ui.protocol.transit.source import SourceDir, SourceFile


class TestBase:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.transit = mocker.patch(
            "wormhole_ui.protocol.transit.transit_protocol_sender.TransitSender"
        )()
        self.file_sender = mocker.patch(
            "wormhole_ui.protocol.transit.transit_protocol_sender.FileSender"
        )()
        self.wormhole = mocker.Mock()
        self.delegate = mocker.Mock()


class TestSendTransit(TestBase):
    def test_sends_transit(self, mocker):
        self.transit.get_connection_abilities.return_value = "abilities"
        self.transit.get_connection_hints.return_value = defer.Deferred()

        transit_sender = TransitProtocolSender(None, self.wormhole, None)
        transit_sender.send_transit()
        self.transit.get_connection_hints.return_value.callback("hints")

        self.wormhole.send_message.assert_called_once_with(
            b'{"transit": {"abilities-v1": "abilities", "hints-v1": "hints"}}',
        )

    def test_emits_transit_error_on_exception(self, mocker):
        self.transit.get_connection_abilities.return_value = "abilities"
        self.transit.get_connection_hints.return_value = defer.Deferred()

        transit_sender = TransitProtocolSender(None, self.wormhole, self.delegate)
        transit_sender.send_transit()
        self.transit.get_connection_hints.return_value.errback(Exception("Error"))

        self.delegate.transit_error.assert_called_once()
        kwargs = self.delegate.transit_error.call_args[1]
        assert_that(kwargs["exception"], is_(Exception))
        assert_that(kwargs["traceback"], starts_with("Traceback"))


class TestHandleTransit(TestBase):
    def test_adds_hints(self, mocker):
        transit_sender = TransitProtocolSender(None, self.wormhole, None)
        transit_sender.handle_transit({"hints-v1": "received_hints"})

        self.transit.add_connection_hints.assert_called_once_with("received_hints")

    def test_sets_key(self, mocker):
        self.transit.TRANSIT_KEY_LENGTH = 128
        self.wormhole.derive_key.return_value = mocker.sentinel.key

        transit_sender = TransitProtocolSender(None, self.wormhole, None)
        transit_sender.handle_transit({})

        self.wormhole.derive_key.assert_called_once_with(
            "lothar.com/wormhole/text-or-file-xfer/transit-key", 128
        )
        self.transit.set_transit_key.assert_called_once_with(mocker.sentinel.key)


class TestSendOffer(TestBase):
    def test_file_offer_is_sent(self, mocker):
        source_file = mocker.Mock(spec=SourceFile, final_bytes=42)
        source_file.name = "test_file"
        source_file.open.return_value = defer.Deferred()

        transit_sender = TransitProtocolSender(None, self.wormhole, None)
        transit_sender.send_offer(source_file)

        source_file.open.return_value.callback(None)

        self.wormhole.send_message.assert_called_with(
            b'{"offer": {"file": {"filename": "test_file", "filesize": 42}}}',
        )

    def test_dir_offer_is_sent(self, mocker):
        source_dir = mocker.Mock(
            spec=SourceDir, final_bytes=42, transfer_bytes=24, num_files=2
        )
        source_dir.name = "test_dir"
        source_dir.open.return_value = defer.Deferred()

        transit_sender = TransitProtocolSender(None, self.wormhole, None)
        transit_sender.send_offer(source_dir)

        source_dir.open.return_value.callback(None)

        self.wormhole.send_message.assert_called_with(
            (
                b'{"offer": {"directory": {'
                b'"mode": "zipfile/deflated", '
                b'"dirname": "test_dir", '
                b'"zipsize": 24, '
                b'"numbytes": 42, '
                b'"numfiles": 2}}}'
            )
        )


class TestSendFile(TestBase):
    def test_sends_file_and_calls_transit_complete(self, mocker):
        source_file = mocker.Mock(id=13, final_bytes=42)
        source_file.name = "test_file"
        self.file_sender.open.return_value = defer.Deferred()
        self.file_sender.send.return_value = defer.Deferred()
        self.file_sender.wait_for_ack.return_value = defer.Deferred()
        send_finished_handler = mocker.Mock()

        transit_sender = TransitProtocolSender(None, self.wormhole, self.delegate)
        transit_sender.send_file(source_file, send_finished_handler)

        self.file_sender.open.return_value.callback(None)
        self.file_sender.send.return_value.callback("1234")
        self.file_sender.wait_for_ack.return_value.callback("1234")

        self.file_sender.open.assert_called_once()
        self.file_sender.send.assert_called_once_with(source_file, mocker.ANY)
        self.file_sender.wait_for_ack.assert_called_once()
        self.delegate.transit_complete.assert_called_once_with(13, "test_file")
        self.delegate.transit_error.assert_not_called()
        send_finished_handler.assert_called_once()

    def test_raises_error_on_hash_mismatch(self, mocker):
        source_file = mocker.Mock(id=13, final_bytes=42)
        source_file.name = "test_file"
        self.file_sender.send.return_value = "4321"
        self.file_sender.wait_for_ack.return_value = "1234"
        send_finished_handler = mocker.Mock()

        transit_sender = TransitProtocolSender(None, self.wormhole, self.delegate)
        transit_sender.send_file(source_file, send_finished_handler)

        self.delegate.transit_complete.assert_not_called()
        kwargs = self.delegate.transit_error.call_args[1]
        assert_that(kwargs["exception"], is_(SendFileError))
        assert_that(kwargs["traceback"], starts_with("Traceback"))
        send_finished_handler.assert_called_once()

    def test_doesnt_raise_error_if_hash_missing(self, mocker):
        source_file = mocker.Mock(id=13, final_bytes=42)
        source_file.name = "test_file"
        self.file_sender.send.return_value = "4321"
        self.file_sender.wait_for_ack.return_value = None
        send_finished_handler = mocker.Mock()

        transit_sender = TransitProtocolSender(None, self.wormhole, self.delegate)
        transit_sender.send_file(source_file, send_finished_handler)

        self.delegate.transit_complete.assert_called_once_with(13, "test_file")
        self.delegate.transit_error.assert_not_called()
        send_finished_handler.assert_called_once()
