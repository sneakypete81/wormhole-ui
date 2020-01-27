class Progress:
    def __init__(self, delegate, id, total_bytes):
        self._delegate = delegate
        self._id = id
        self._total_bytes = total_bytes
        self._transferred_bytes = 0

    def update(self, increment_bytes):
        self._transferred_bytes += increment_bytes
        self._delegate.transit_progress(
            self._id, self._transferred_bytes, self._total_bytes
        )
