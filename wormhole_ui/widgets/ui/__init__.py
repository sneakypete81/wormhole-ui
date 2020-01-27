# Adapted from https://gist.github.com/cpbotha/1b42a20c8f3eb9bb7cb8
#
# Copyright (c) 2011 Sebastian Wiesner <lunaryorn@gmail.com>
# Modifications by Charl Botha <cpbotha@vxlabs.com>
# found this here:
# https://github.com/lunaryorn/snippets/blob/master/qt4/designer/pyside_dynamic.py
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from pathlib import Path

from PySide2.QtCore import QFile
from PySide2.QtUiTools import QUiLoader


class CustomWidget:
    def __init__(self, Widget, *args, **kwds):
        self.Widget = Widget
        self.name = self.Widget.__name__
        self.args = args
        self.kwds = kwds

    def create(self, parent):
        return self.Widget(parent, *self.args, **self.kwds)


class CustomUiLoader(QUiLoader):
    def __init__(self, base_instance=None, custom_widgets=None):
        super().__init__()
        self.base_instance = base_instance
        if custom_widgets is None:
            self.custom_widgets = {}
        else:
            self.custom_widgets = {w.name: w for w in custom_widgets}

    def createWidget(self, className, parent=None, name=""):
        if parent is None and self.base_instance:
            # No parent, this is the top-level widget
            return self.base_instance

        if className in QUiLoader.availableWidgets(self):
            widget = super().createWidget(className, parent, name)
        else:
            if className in self.custom_widgets:
                widget = self.custom_widgets[className].create(parent)
            else:
                raise KeyError("Unknown widget '%s'" % className)

        if self.base_instance:
            # Set an attribute for the new child widget on the base instance
            setattr(self.base_instance, name, widget)

        return widget


def load_ui(filename, base_instance=None, custom_widgets=None):
    ui_file = QFile(str(Path(__file__).parent / filename))
    ui_file.open(QFile.ReadOnly)

    loader = CustomUiLoader(base_instance, custom_widgets)
    ui = loader.load(ui_file)
    ui_file.close()

    return ui
