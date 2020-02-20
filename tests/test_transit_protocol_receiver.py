from hamcrest import assert_that, is_, starts_with, calling, raises
import pytest
from twisted.internet import defer

from wormhole_ui.errors import RespondError
from wormhole_ui.protocol.transit.transit_protocol_receiver import (
    TransitProtocolReceiver,
)


class TestBase:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.transit = mocker.patch(
            "wormhole_ui.protocol.transit.transit_protocol_receiver.TransitReceiver"
        )()
        self.file_receiver = mocker.patch(
            "wormhole_ui.protocol.transit.transit_protocol_receiver.FileReceiver"
        )()
        self.wormhole = mocker.Mock()
        self.delegate = mocker.Mock()


class TestHandleTransit(TestBase):
    def test_adds_hints(self, mocker):
        transit_receiver = TransitProtocolReceiver(None, self.wormhole, None)
        transit_receiver.handle_transit({"hints-v1": "received_hints"})

        self.transit.add_connection_hints.assert_called_once_with("received_hints")

    def test_sets_key(self, mocker):
        self.transit.TRANSIT_KEY_LENGTH = 128
        self.wormhole.derive_key.return_value = mocker.sentinel.key

        transit_receiver = TransitProtocolReceiver(None, self.wormhole, None)
        transit_receiver.handle_transit({})

        self.wormhole.derive_key.assert_called_once_with(
            "lothar.com/wormhole/text-or-file-xfer/transit-key", 128
        )
        self.transit.set_transit_key.assert_called_once_with(mocker.sentinel.key)


class TestSendTransit(TestBase):
    def test_sends_transit(self, mocker):
        self.transit.get_connection_abilities.return_value = "abilities"
        self.transit.get_connection_hints.return_value = defer.Deferred()

        transit_receiver = TransitProtocolReceiver(None, self.wormhole, None)
        transit_receiver.send_transit()
        self.transit.get_connection_hints.return_value.callback("hints")

        self.wormhole.send_message.assert_called_once_with(
            b'{"transit": {"abilities-v1": "abilities", "hints-v1": "hints"}}',
        )

    def test_emits_transit_error_on_exception(self, mocker):
        self.transit.get_connection_abilities.return_value = "abilities"
        self.transit.get_connection_hints.return_value = defer.Deferred()

        transit_receiver = TransitProtocolReceiver(None, self.wormhole, self.delegate)
        transit_receiver.send_transit()
        self.transit.get_connection_hints.return_value.errback(Exception("Error"))

        self.delegate.transit_error.assert_called_once()
        kwargs = self.delegate.transit_error.call_args[1]
        assert_that(kwargs["exception"], is_(Exception))
        assert_that(kwargs["traceback"], starts_with("Traceback"))


class TestHandleOffer(TestBase):
    def test_offer_is_parsed(self, mocker):
        transit_receiver = TransitProtocolReceiver(None, self.wormhole, None)
        result = transit_receiver.handle_offer(
            {"file": {"filename": "test_file", "filesize": 42}}
        )

        assert_that(result.name, is_("test_file"))
        assert_that(result.final_bytes, is_(42))

    def test_invalid_offer_raises_exception(self, mocker):
        transit_receiver = TransitProtocolReceiver(None, self.wormhole, None)

        assert_that(
            calling(transit_receiver.handle_offer).with_args({"invalid": "test_file"}),
            raises(RespondError),
        )


class TestReceiveFile(TestBase):
    def test_receives_file_and_calls_transit_complete(self, mocker):
        dest_file = mocker.Mock(id=13)
        dest_file.name = "test_file"
        self.file_receiver.open.return_value = defer.Deferred()
        self.file_receiver.receive.return_value = defer.Deferred()
        self.file_receiver.send_ack.return_value = defer.Deferred()
        receive_finished_handler = mocker.Mock()

        transit_receiver = TransitProtocolReceiver(None, self.wormhole, self.delegate)
        transit_receiver.receive_file(dest_file, receive_finished_handler)

        self.file_receiver.open.return_value.callback(None)
        self.file_receiver.receive.return_value.callback("1234")
        self.file_receiver.send_ack.return_value.callback(None)

        self.file_receiver.open.assert_called_once()
        self.file_receiver.receive.assert_called_once_with(dest_file, mocker.ANY)
        self.file_receiver.send_ack.assert_called_once_with("1234")
        dest_file.finalise.assert_called_once()
        self.delegate.transit_complete.assert_called_once_with(13, "test_file")
        receive_finished_handler.assert_called_once()

    def test_raises_error_if_exception_thrown(self, mocker):
        self.file_receiver.open.return_value = defer.Deferred()
        receive_finished_handler = mocker.Mock()

        transit_receiver = TransitProtocolReceiver(None, self.wormhole, self.delegate)
        transit_receiver.receive_file(mocker.Mock(), receive_finished_handler)

        self.file_receiver.open.return_value.errback(Exception("Error"))

        self.delegate.transit_complete.assert_not_called()
        kwargs = self.delegate.transit_error.call_args[1]
        assert_that(kwargs["exception"], is_(Exception))
        assert_that(kwargs["traceback"], starts_with("Traceback"))
        receive_finished_handler.assert_called_once()
