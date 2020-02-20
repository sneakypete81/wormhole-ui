from hamcrest import assert_that, is_
import pytest

from wormhole_ui.transit.transit_protocol_pair import TransitProtocolPair


class TestBase:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.sender = mocker.patch(
            "wormhole_ui.transit.transit_protocol_pair.TransitProtocolSender"
        )()
        self.receiver = mocker.patch(
            "wormhole_ui.transit.transit_protocol_pair.TransitProtocolReceiver"
        )()
        self.source_file = mocker.patch(
            "wormhole_ui.transit.transit_protocol_pair.SourceFile"
        )()


class TestSendFile(TestBase):
    def test_sends_transit(self):
        transit = TransitProtocolPair(None, None, None)

        transit.send_file(13, "test_file")

        self.sender.send_transit.assert_called_once()

    def test_skips_transit_handshake_if_already_complete(self):
        transit = TransitProtocolPair(None, None, None)
        transit.send_file(13, "test_file")
        transit.handle_transit("transit")
        transit.handle_file_ack()
        on_send_finished = self.sender.send_file.call_args[0][1]
        on_send_finished()

        transit.send_file(13, "test_file")

        self.sender.send_transit.assert_called_once()
        assert_that(self.sender.send_offer.call_count, is_(2))
        self.sender.send_offer.assert_called_with(self.source_file)

    def test_opens_source_file(self):
        transit = TransitProtocolPair(None, None, None)

        transit.send_file(13, "test_file")

        self.source_file.open.assert_called_once()


class TestHandleTransit(TestBase):
    def test_handles_transit_when_sending(self):
        transit = TransitProtocolPair(None, None, None)
        transit.send_file(13, "test_file")

        transit.handle_transit("transit")

        self.sender.handle_transit.assert_called_once_with("transit")

    def test_only_handles_transit_the_first_time_when_sending(self):
        transit = TransitProtocolPair(None, None, None)
        transit.send_file(13, "test_file")
        transit.handle_transit("transit")
        transit.handle_file_ack()
        on_send_finished = self.sender.send_file.call_args[0][1]
        on_send_finished()

        transit.send_file(13, "test_file")
        transit.handle_transit("transit")

        self.sender.handle_transit.assert_called_once_with("transit")

    def test_sends_offer_when_sending(self):
        transit = TransitProtocolPair(None, None, None)
        transit.send_file(13, "test_file")

        transit.handle_transit("transit")

        self.sender.send_offer.assert_called_once_with(self.source_file)

    def test_handles_transit_when_receiving(self):
        transit = TransitProtocolPair(None, None, None)

        transit.handle_transit("transit")

        self.receiver.handle_transit.assert_called_once_with("transit")

    def test_only_handles_transit_the_first_time_when_receiving(self):
        transit = TransitProtocolPair(None, None, None)
        transit.handle_transit("transit")
        transit.handle_offer("offer")
        transit.receive_file(13, "test_file")
        on_receive_finished = self.receiver.receive_file.call_args[0][1]
        on_receive_finished()

        transit.handle_transit("transit")

        self.receiver.handle_transit.assert_called_once_with("transit")

    def test_sends_transit_when_receiving(self):
        transit = TransitProtocolPair(None, None, None)

        transit.handle_transit("transit")

        self.receiver.send_transit.assert_called_once()


class TestHandleFileAck(TestBase):
    def test_sends_file(self, mocker):
        transit = TransitProtocolPair(None, None, None)
        transit.send_file(13, "test_file")
        transit.handle_transit("transit")

        transit.handle_file_ack()

        self.sender.send_file.assert_called_once_with(self.source_file, mocker.ANY)


class TestHandleOffer(TestBase):
    def test_handles_offer(self):
        transit = TransitProtocolPair(None, None, None)
        transit.handle_transit("transit")

        transit.handle_offer("offer")

        self.receiver.handle_offer.assert_called_once_with("offer")

    def test_returns_dest_file(self, mocker):
        dest_file = mocker.Mock()
        self.receiver.handle_offer.return_value = dest_file
        transit = TransitProtocolPair(None, None, None)
        transit.handle_transit("transit")

        result = transit.handle_offer("offer")

        assert_that(result, is_(dest_file))


class TestReceiveFile(TestBase):
    def test_file_is_received(self, mocker):
        dest_file = mocker.Mock()
        self.receiver.handle_offer.return_value = dest_file
        transit = TransitProtocolPair(None, None, None)
        transit.handle_transit("transit")
        transit.handle_offer("offer")

        transit.receive_file(13, "test_file")

        self.receiver.receive_file.assert_called_once_with(dest_file, mocker.ANY)


class TestIsSendingFile(TestBase):
    def test_is_false_before_sending(self):
        transit = TransitProtocolPair(None, None, None)

        assert_that(transit.is_sending_file, is_(False))

    def test_is_true_while_sending(self):
        transit = TransitProtocolPair(None, None, None)
        transit.send_file(13, "test_file")

        assert_that(transit.is_sending_file, is_(True))

    def test_is_false_after_sending(self):
        transit = TransitProtocolPair(None, None, None)
        transit.send_file(13, "test_file")
        transit.handle_transit("transit")
        transit.handle_file_ack()
        assert_that(transit.is_sending_file, is_(True))

        on_send_finished = self.sender.send_file.call_args[0][1]
        on_send_finished()

        assert_that(transit.is_sending_file, is_(False))


class TestIsReceivingFile(TestBase):
    def test_is_false_before_receiving(self):
        transit = TransitProtocolPair(None, None, None)

        assert_that(transit.is_receiving_file, is_(False))

    def test_is_true_while_receiving(self):
        transit = TransitProtocolPair(None, None, None)
        transit.handle_transit("transit")
        transit.handle_offer("offer")
        transit.receive_file(13, "test_file")

        assert_that(transit.is_receiving_file, is_(True))

    def test_is_false_after_receiving(self):
        transit = TransitProtocolPair(None, None, None)
        transit.handle_transit("transit")
        transit.handle_offer("offer")
        transit.receive_file(13, "test_file")

        on_receive_finished = self.receiver.receive_file.call_args[0][1]
        on_receive_finished()

        assert_that(transit.is_receiving_file, is_(False))
