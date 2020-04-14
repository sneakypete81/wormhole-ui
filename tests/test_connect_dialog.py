from hamcrest import assert_that, calling, is_, raises
import pytest
from PySide2.QtCore import Qt

from wormhole_ui.protocol.wormhole_protocol import WormholeSignals
from wormhole_ui.widgets.connect_dialog import ConnectDialog


@pytest.fixture()
def dialog(mocker, qtbot):
    wormhole = mocker.Mock()
    wormhole.signals = WormholeSignals()
    connect_dialog = ConnectDialog(parent=None, wormhole=wormhole)
    qtbot.addWidget(connect_dialog)
    return connect_dialog


class TestOpen:
    def test_opens_wormhole(self, dialog):
        dialog.open()

        dialog.wormhole.open.assert_called_once()

    def test_indicates_code_is_being_requested(self, dialog):
        dialog.open()

        assert_that(dialog.code_label.text(), is_("[obtaining code...]"))

    def test_clears_and_disables_code_entry(self, dialog):
        dialog.code_edit.setText("Delete me")

        dialog.open()

        assert_that(dialog.set_code_button.isEnabled(), is_(False))
        assert_that(dialog.code_edit.text(), is_(""))


class TestCodeReceived:
    def test_updates_code_label(self, dialog):
        dialog.open()

        dialog.wormhole.signals.code_received.emit("1-test-code")

        assert_that(dialog.code_label.text(), is_("1-test-code"))

    def test_code_label_limited_to_100_characters(self, dialog):
        dialog.open()

        dialog.wormhole.signals.code_received.emit("1" * 200)

        assert_that(dialog.code_label.text(), is_("1" * 100))

    def test_enables_code_entry(self, dialog):
        dialog.open()

        dialog.wormhole.signals.code_received.emit("1-test-code")

        assert_that(dialog.set_code_button.isEnabled(), is_(True))


class TestSetCodeButton:
    def test_sets_the_code(self, qtbot, dialog):
        dialog.open()
        dialog.wormhole.signals.code_received.emit("1-test-code")
        dialog.code_edit.setText("2-test-code")

        qtbot.mouseClick(dialog.set_code_button, Qt.LeftButton)

        dialog.wormhole.set_code.assert_called_with("2-test-code")

    def test_strips_whitespace(self, qtbot, dialog):
        dialog.open()
        dialog.wormhole.signals.code_received.emit("1-test-code")
        dialog.code_edit.setText(" 2-test-code  ")

        qtbot.mouseClick(dialog.set_code_button, Qt.LeftButton)

        dialog.wormhole.set_code.assert_called_with("2-test-code")

    def test_sets_an_empty_code(self, qtbot, dialog):
        dialog.open()
        dialog.wormhole.signals.code_received.emit("1-test-code")

        qtbot.mouseClick(dialog.set_code_button, Qt.LeftButton)

        dialog.wormhole.set_code.assert_called_with("")

    def test_disables_button(self, qtbot, dialog):
        dialog.open()
        dialog.wormhole.signals.code_received.emit("1-test-code")
        dialog.code_edit.setText("2-test-code")

        qtbot.mouseClick(dialog.set_code_button, Qt.LeftButton)

        assert_that(dialog.set_code_button.isEnabled(), is_(False))