# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QPushButton, QLabel, QHBoxLayout

class SquareButton(QPushButton):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scale = 1.2
        self.label = None
        self.word_wrap = True
        self.text = ""

    def setRelSize(self, ratio):
        self.scale = ratio
        self.updateGeometry()

    def setWordWrap(self, state):
        self.word_wrap = state
        self.setText(self.text)  # Ensure text is updated when word_wrap changes

    def sizeHint(self):
        size = int(round(self.fontMetrics().height() * self.scale))
        return QSize(size, size)

    # Override setText to facilitate automatic word wrapping
    def setText(self, text):
        self.text = text
        if self.word_wrap:
            super().setText("")  # Clear button text for custom QLabel wrapping
            if self.label is None:
                self.label = QLabel(text, self)
                self.label.setWordWrap(True)
                self.label.setAlignment(Qt.AlignCenter)
                layout = QHBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
                layout.addWidget(self.label, 0, Qt.AlignCenter)
            else:
                self.label.setText(text)
            self.update_label_size()  # Update label size to fit the button
        else:
            if self.label is not None:
                self.label.deleteLater()  # Remove QLabel when word_wrap is off
                self.label = None
            super().setText(text)

    def update_label_size(self):
        """Ensure the label fits within the button size."""
        if self.label is not None:
            self.label.setFixedWidth(self.width())  # Match button width
            self.label.adjustSize()  # Adjust size for word wrapping
            self.updateGeometry()  # Update button geometry

    def resizeEvent(self, event):
        """Override resizeEvent to ensure the label resizes with the button."""
        super().resizeEvent(event)
        if self.label is not None:
            self.update_label_size()
