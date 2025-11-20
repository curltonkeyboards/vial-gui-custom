# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import QComboBox, QStyleOptionComboBox
from PyQt5.QtGui import QPalette, QPainter, QPolygon, QBrush
from PyQt5.QtCore import Qt, QPoint, QEvent, QObject


class LineEditEventFilter(QObject):
    """Event filter to make lineEdit in combobox open the dropdown when clicked"""

    def __init__(self, combobox):
        super().__init__()
        self.combobox = combobox

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.combobox.showPopup()
            return True
        return super().eventFilter(obj, event)


class ArrowComboBox(QComboBox):
    """
    QComboBox with programmatically drawn dropdown arrow.
    Fixes issues where CSS border triangles don't render properly on some systems.
    Also allows clicking anywhere on the combobox to open the dropdown.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.line_edit_filter = None

    def setEditable(self, editable):
        """Override setEditable to install event filter on lineEdit"""
        super().setEditable(editable)
        if editable and self.lineEdit():
            self.line_edit_filter = LineEditEventFilter(self)
            self.lineEdit().installEventFilter(self.line_edit_filter)

    def paintEvent(self, event):
        # Draw the standard combobox
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        painter = QPainter(self)
        self.style().drawComplexControl(self.style().CC_ComboBox, opt, painter, self)
        self.style().drawControl(self.style().CE_ComboBoxLabel, opt, painter, self)

        # Draw dropdown arrow manually
        arrow_rect = self.style().subControlRect(self.style().CC_ComboBox, opt, self.style().SC_ComboBoxArrow, self)
        arrow_center_x = arrow_rect.center().x()
        arrow_center_y = arrow_rect.center().y()

        # Create triangle pointing down
        arrow_size = 4
        arrow = QPolygon([
            QPoint(arrow_center_x - arrow_size, arrow_center_y - 2),
            QPoint(arrow_center_x + arrow_size, arrow_center_y - 2),
            QPoint(arrow_center_x, arrow_center_y + 3)
        ])

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.palette().color(QPalette.Text)))
        painter.drawPolygon(arrow)

    def mousePressEvent(self, event):
        """Make the entire combobox clickable to open the dropdown"""
        if event.button() == Qt.LeftButton:
            self.showPopup()
        else:
            super().mousePressEvent(event)
