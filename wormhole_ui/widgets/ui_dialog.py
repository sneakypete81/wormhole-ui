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
        dialog_y = self.pos().y()
        dialog_center = self.mapToGlobal(self.rect().center())

        parent_y = parent.window().pos().y()
        parent_center = parent.window().mapToGlobal(parent.window().rect().center())

        self.move(parent_center.x() - dialog_center.x(), parent_y - dialog_y)
