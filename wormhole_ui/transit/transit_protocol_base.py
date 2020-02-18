import json
import logging

from twisted.internet import defer


class TransitProtocolBase:
    def __init__(self, wormhole, delegate, transit):
        self._wormhole = wormhole
        self._delegate = delegate
        self._transit = transit

        self._send_transit_deferred = None

    def handle_transit(self, transit_message):
        self._add_hints(transit_message)
        self._derive_key()

    def send_transit(self):
        self._send_transit_deferred = self._send_transit()
        self._send_transit_deferred.addErrback(self._on_deferred_error)

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
        return failure

    def close(self):
        if self._send_transit_deferred is not None:
            self._send_transit_deferred.cancel()
