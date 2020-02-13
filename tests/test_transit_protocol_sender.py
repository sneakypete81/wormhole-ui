from unittest import mock

# from hamcrest import assert_that, is_, starts_with
import pytest
# import pytest_twisted
from twisted.internet import task, defer

from wormhole_ui.transit_protocol_sender import TransitProtocolSender


class TestTransitProtocolSender:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.transit = mocker.patch(
            "wormhole_ui.transit_protocol_sender.TransitSender"
        )()

    def test_send_file_sends_transit(self):
        wormhole = mock.Mock()
        clock = task.Clock()

        d = defer.Deferred()
        clock.callLater(1, d.callback, "hints")
        self.transit.get_connection_hints.return_value = d
        self.transit.get_connection_abilities.return_value = "abilities"

        transit_sender = TransitProtocolSender(clock, wormhole, None)
        transit_sender.send_file(mock.Mock())

        clock.advance(1)
        wormhole.send_message.assert_called_with(
            b'{"transit": {"abilities-v1": "abilities", "hints-v1": "hints"}}',
        )
