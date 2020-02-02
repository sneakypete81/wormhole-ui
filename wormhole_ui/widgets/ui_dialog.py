from PySide2.QtWidgets import QDialog

from .ui import load_ui


class UiDialog(QDialog):
    def __init__(self, parent, ui_name):
        super().__init__(parent)
        load_ui(ui_name, base_instance=self)

    def open(self):
        self._position_over_parent(self.parent())
        super().open()

    def _position_over_parent(self, parent):
        parent_y = parent.window().pos().y()
        parent_center = parent.window().mapToGlobal(parent.window().rect().center())

        self.move(parent_center.x() - self.width() / 2, parent_y)
