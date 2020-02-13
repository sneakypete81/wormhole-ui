import pytest
from twisted.internet import defer

from wormhole_ui.transit_protocol_sender import TransitProtocolSender


class TestTransitProtocolSender:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.transit = mocker.patch(
            "wormhole_ui.transit_protocol_sender.TransitSender"
        )()
        self.wormhole = mocker.Mock()

    def test_send_file_sends_transit(self, mocker):
        self.transit.get_connection_hints.return_value = defer.Deferred()
        self.transit.get_connection_abilities.return_value = "abilities"

        transit_sender = TransitProtocolSender(None, self.wormhole, None)
        transit_sender.send_file(mocker.Mock())
        self.transit.get_connection_hints.return_value.callback("hints")

        self.wormhole.send_message.assert_called_with(
            b'{"transit": {"abilities-v1": "abilities", "hints-v1": "hints"}}',
        )
