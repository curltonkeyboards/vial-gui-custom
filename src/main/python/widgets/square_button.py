from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QPainter, QPolygonF
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout

class PentagonButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.label = None
        self.word_wrap = False
        self.text = ""

    def setWordWrap(self, state):
        self.word_wrap = state
        self.setText(self.text)

    def sizeHint(self):
        return QSize(100, 100)  # Set an initial size

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(self.palette().brush(self.backgroundRole()))
        
        # Define the points for a regular pentagon
        side_length = 50
        half_width = side_length / (2 * (1 + (5 ** 0.5) / 2))
        points = [
            (50, 0),
            (50 + half_width, 50 - side_length / 2),
            (50 + half_width / 2, 50 + side_length / 2),
            (50 - half_width / 2, 50 + side_length / 2),
            (50 - half_width, 50 - side_length / 2),
        ]
        polygon = QPolygonF([Qt.QPointF(*point) for point in points])
        
        painter.drawPolygon(polygon)

    def setText(self, text):
        self.text = text
        if self.word_wrap:
            super().setText("")
            if self.label is None:
                self.label = QLabel(text, self)
                self.label.setWordWrap(True)
                self.label.setAlignment(Qt.AlignCenter)
                layout = QHBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(self.label, 0, Qt.AlignCenter)
            else:
                self.label.setText(text)
        else:
            if self.label is not None:
                self.label.deleteLater()
            super().setText(text)