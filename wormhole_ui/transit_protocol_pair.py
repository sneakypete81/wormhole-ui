from .transit_protocol import TransitProtocolReceiver, TransitProtocolSender


class TransitProtocolPair:
    def __init__(self, reactor, wormhole, delegate):
        self.receiver = TransitProtocolReceiver(reactor, wormhole, delegate)
        self.sender = TransitProtocolSender(reactor, wormhole, delegate)

    def handle_transit(self, transit_message):
        if self.sender.awaiting_transit_response:
            # We're waiting for a response, so this is for the sender
            self.sender.handle_transit(transit_message)
        else:
            # We've received a transit message first, so this is for the receiver
            self.receiver.handle_transit(transit_message)

    def close(self):
        self.sender.close()
        self.receiver.close()
