from wormhole_ui.protocol.transit.progress import Progress


class TestProgress:
    def test_delegate_called_on_the_first_update(self, mocker):
        time_mock = mocker.patch("wormhole_ui.protocol.transit.progress.time")
        delegate = mocker.Mock()
        progress = Progress(delegate, 24, 42)

        time_mock.monotonic.return_value = 10.1
        progress.update(10)

        delegate.transit_progress.assert_called_with(24, 10, 42)

    def test_delegate_not_called_too_often(self, mocker):
        time_mock = mocker.patch("wormhole_ui.protocol.transit.progress.time")
        delegate = mocker.Mock()
        progress = Progress(delegate, 24, 42)

        time_mock.monotonic.return_value = 10.1
        progress.update(10)

        delegate.transit_progress.assert_called_with(24, 10, 42)
        delegate.transit_progress.reset_mock()

        time_mock.monotonic.return_value = 10.19
        progress.update(5)

        delegate.transit_progress.assert_not_called()

    def test_delegate_called_after_100ms(self, mocker):
        time_mock = mocker.patch("wormhole_ui.protocol.transit.progress.time")
        delegate = mocker.Mock()
        progress = Progress(delegate, 24, 42)

        time_mock.monotonic.return_value = 10.1
        progress.update(10)

        delegate.transit_progress.assert_called_with(24, 10, 42)
        delegate.transit_progress.reset_mock()

        time_mock.monotonic.return_value = 10.21
        progress.update(5)

        delegate.transit_progress.assert_called_with(24, 15, 42)
