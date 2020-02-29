import logging

from .source_file import SourceFile
from .transit_protocol_sender import TransitProtocolSender
from .transit_protocol_receiver import TransitProtocolReceiver


class TransitProtocolPair:
    def __init__(self, reactor, wormhole, delegate):
        self._receiver = TransitProtocolReceiver(reactor, wormhole, delegate)
        self._sender = TransitProtocolSender(reactor, wormhole, delegate)

        self._source_file = None
        self._dest_file = None

        self._send_transit_handshake_complete = False
        self._receive_transit_handshake_complete = False
        self._awaiting_transit_response = False
        self.is_sending_file = False
        self.is_receiving_file = False

    def send_file(self, id, file_path):
        logging.debug("TransitProtocolPair::send_file")
        assert not self.is_sending_file
        self.is_sending_file = True

        self._source_file = SourceFile(id, file_path)
        self._source_file.open()

        if not self._send_transit_handshake_complete:
            self._awaiting_transit_response = True
            self._sender.send_transit()
        else:
            self._sender.send_offer(self._source_file)

    def handle_transit(self, transit_message):
        logging.debug("TransitProtocolPair::handle_transit")

        if self._awaiting_transit_response:
            # We're waiting for a response, so this is for the sender
            assert self.is_sending_file

            if not self._send_transit_handshake_complete:
                self._send_transit_handshake_complete = True
                self._sender.handle_transit(transit_message)

            self._awaiting_transit_response = False
            self._sender.send_offer(self._source_file)

        else:
            # We haven't sent a transit message, so this is for the receiver
            assert not self.is_receiving_file

            if not self._receive_transit_handshake_complete:
                self._receive_transit_handshake_complete = True
                self._receiver.handle_transit(transit_message)

            self._receiver.send_transit()

    def handle_file_ack(self):
        logging.debug("TransitProtocolPair::handle_file_ack")
        assert self.is_sending_file

        def on_send_finished():
            self.is_sending_file = False
            self._source_file = None

        self._sender.send_file(self._source_file, on_send_finished)

    def handle_offer(self, offer):
        logging.debug("TransitProtocolPair::handle_offer")
        assert not self.is_receiving_file

        self._dest_file = self._receiver.handle_offer(offer)
        return self._dest_file

    def receive_file(self, id, dest_path):
        logging.debug("TransitProtocolPair::receive_file")
        assert not self.is_receiving_file
        self.is_receiving_file = True

        def on_receive_finished():
            self.is_receiving_file = False
            if self._dest_file is not None:
                self._dest_file.cleanup()
                self._dest_file = None

        self._dest_file.open(id, dest_path)
        self._receiver.receive_file(self._dest_file, on_receive_finished)

    def close(self):
        self._source_file = None
        self._dest_file = None
        self._send_transit_handshake_complete = False
        self._receive_transit_handshake_complete = False
        self._awaiting_transit_response = False
        self.is_sending_file = False
        self.is_receiving_file = False

        self._sender.close()
        self._receiver.close()
