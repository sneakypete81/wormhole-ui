class Timeout:
    def __init__(self, reactor, timeout_seconds):
        self._reactor = reactor
        self._timeout_seconds = timeout_seconds
        self._deferred = None

    def start(self, callback, *args, **kwds):
        self.stop()

        self._deferred = self._reactor.callLater(
            self._timeout_seconds, callback, *args, **kwds
        )

    def stop(self):
        if self._deferred is not None:
            self._deferred.cancel()
        self._deferred = None
