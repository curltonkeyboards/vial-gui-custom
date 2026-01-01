# SPDX-License-Identifier: GPL-2.0-or-later
"""
Loading Banner Widget
Displays a modern Apple-like loading screen with gradient and branding
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QLinearGradient, QColor, QFont, QPixmap, QPainterPath


class LoadingBanner(QWidget):
    """Modern loading banner with gradient background and keyboard image"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set size
        self.setFixedSize(600, 400)

        # Center on parent or screen
        if parent:
            parent_rect = parent.geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)

        # Setup UI
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Spacer
        layout.addStretch(1)

        # Keyswitch image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedHeight(200)

        # Try to load keyswitch image from filesystem
        import os
        script_dir = os.path.dirname(__file__)
        image_path = os.path.join(script_dir, "keyswitch.png")

        pixmap = QPixmap(image_path)
        if pixmap.isNull() or not os.path.exists(image_path):
            # Fallback: Create a simple text-based indicator
            self.image_label.setText("⌨")
            self.image_label.setStyleSheet("font-size: 120px; color: white;")
        else:
            # Scale image to fit
            scaled_pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)

        layout.addWidget(self.image_label)

        # Loading text
        self.text_label = QLabel("SwitchStation Loading")
        self.text_label.setAlignment(Qt.AlignCenter)

        # Modern Apple-like font
        font = QFont()
        font.setFamily("SF Pro Display" if hasattr(QFont, "SF Pro Display") else "Segoe UI")
        font.setPointSize(28)
        font.setWeight(QFont.Light)
        self.text_label.setFont(font)
        self.text_label.setStyleSheet("color: white;")

        layout.addWidget(self.text_label)

        # Animated dots
        self.dots_label = QLabel("...")
        self.dots_label.setAlignment(Qt.AlignCenter)
        dots_font = QFont()
        dots_font.setPointSize(20)
        self.dots_label.setFont(dots_font)
        self.dots_label.setStyleSheet("color: rgba(255, 255, 255, 200);")
        layout.addWidget(self.dots_label)

        # Spacer
        layout.addStretch(1)

        self.setLayout(layout)

        # Animation for dots
        self.dot_count = 0
        self.dot_timer = QTimer()
        self.dot_timer.timeout.connect(self._update_dots)
        self.dot_timer.start(500)  # Update every 500ms

        # Fade in animation
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)

    def _update_dots(self):
        """Animate the loading dots"""
        self.dot_count = (self.dot_count + 1) % 4
        self.dots_label.setText("." * self.dot_count if self.dot_count > 0 else "")

    def paintEvent(self, event):
        """Draw gradient background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Create modern Apple-like gradient (purple/blue gradient)
        gradient = QLinearGradient(0, 0, 0, self.height())

        # Color stops for a modern gradient (similar to macOS Big Sur style)
        gradient.setColorAt(0.0, QColor(120, 81, 169))   # Purple
        gradient.setColorAt(0.5, QColor(88, 86, 214))     # Blue-purple
        gradient.setColorAt(1.0, QColor(58, 123, 213))    # Blue

        # Draw rounded rectangle with gradient
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)

        # Create rounded path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 20, 20)
        painter.drawPath(path)

    def show_with_fade(self):
        """Show the banner with fade-in animation"""
        self.show()
        self.raise_()
        self.fade_in_animation.start()

    def hide_with_fade(self, callback=None):
        """Hide the banner with fade-out animation"""
        fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InOutQuad)

        if callback:
            fade_out.finished.connect(callback)
        else:
            fade_out.finished.connect(self.close)

        self.dot_timer.stop()
        fade_out.start()

        # Keep reference to prevent garbage collection
        self._fade_out_animation = fade_out
