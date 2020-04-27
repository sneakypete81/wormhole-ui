import time

UPDATE_RATE_SECONDS = 0.1


class Progress:
    def __init__(self, delegate, id, total_bytes):
        self._delegate = delegate
        self._id = id
        self._total_bytes = total_bytes
        self._transferred_bytes = 0
        self._last_update_sent = 0

    def update(self, increment_bytes):
        self._transferred_bytes += increment_bytes
        now = time.monotonic()

        if now - self._last_update_sent > UPDATE_RATE_SECONDS:
            self._delegate.transit_progress(
                self._id, self._transferred_bytes, self._total_bytes
            )
            self._last_update_sent = now
