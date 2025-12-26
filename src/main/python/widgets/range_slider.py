# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient


class MultiHandleSlider(QWidget):
    """
    A slider with multiple draggable handles and colored sections.

    For trigger settings:
    - 3 handles: deadzone_bottom, actuation, deadzone_top
    - Constraint: deadzone_bottom <= actuation <= deadzone_top

    For rapid trigger:
    - 2 handles: press_sens, release_sens
    """

    valuesChanged = pyqtSignal(list)  # Emits list of all handle values

    def __init__(self, num_handles=3, minimum=0, maximum=100, parent=None):
        super().__init__(parent)
        self.num_handles = num_handles
        self.minimum = minimum
        self.maximum = maximum

        # Handle values (positions)
        self.values = []
        for i in range(num_handles):
            # Default spacing
            self.values.append(minimum + (maximum - minimum) * (i + 1) / (num_handles + 1))

        # Handle being dragged
        self.active_handle = None

        # Visual settings
        self.handle_radius = 10
        self.track_height = 8
        self.margin = 25  # Space on left/right for handles

        # Color scheme
        self.track_bg_color = QColor(45, 45, 50)
        self.handle_color = QColor(255, 255, 255)
        self.handle_border_color = QColor(120, 120, 130)

        # Section colors (for 3-handle mode)
        # Gray - Deadzone Bottom - Orange (Trigger) - Cyan (Reset) - Deadzone Top - Gray
        self.section_colors = [
            QColor(80, 80, 85),     # Before deadzone bottom (gray)
            QColor(255, 140, 50),   # Orange - trigger zone (between deadzone_bottom and actuation)
            QColor(100, 200, 255),  # Cyan - release zone (between actuation and deadzone_top)
            QColor(80, 80, 85),     # After deadzone top (gray)
        ]

        # For 2-handle mode (rapid trigger)
        self.rf_section_colors = [
            QColor(80, 80, 85),     # Before first handle (gray)
            QColor(255, 140, 50),   # Orange - press zone
            QColor(100, 200, 255),  # Cyan - release zone
            QColor(80, 80, 85),     # After last handle (gray)
        ]

        self.setMinimumHeight(40)
        self.setMinimumWidth(200)

        # Labels for handles (optional)
        self.handle_labels = []

    def set_values(self, values):
        """Set all handle values at once"""
        if len(values) != self.num_handles:
            return
        self.values = list(values)
        self.update()

    def set_value(self, handle_index, value):
        """Set a specific handle value"""
        if 0 <= handle_index < self.num_handles:
            self.values[handle_index] = max(self.minimum, min(self.maximum, value))
            self.update()

    def get_values(self):
        """Get all handle values"""
        return list(self.values)

    def set_handle_labels(self, labels):
        """Set labels to display below each handle"""
        self.handle_labels = labels
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Calculate track geometry
        track_y = height // 2 - self.track_height // 2
        track_x = self.margin
        track_width = width - 2 * self.margin

        # Draw background track with shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.drawRoundedRect(track_x + 1, track_y + 1, track_width, self.track_height, 4, 4)

        # Draw background track
        painter.setBrush(QBrush(self.track_bg_color))
        painter.drawRoundedRect(track_x, track_y, track_width, self.track_height, 4, 4)

        # Draw colored sections
        self._draw_sections(painter, track_x, track_y, track_width)

        # Draw handles
        for i, value in enumerate(self.values):
            pos_x = self._value_to_pixel(value)
            self._draw_handle(painter, pos_x, height // 2, i)

        # Draw labels
        if self.handle_labels and len(self.handle_labels) == self.num_handles:
            painter.setPen(QPen(QColor(180, 180, 180)))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)

            for i, label in enumerate(self.handle_labels):
                pos_x = self._value_to_pixel(self.values[i])
                # Draw label below handle
                label_rect = QRectF(pos_x - 30, height // 2 + self.handle_radius + 5, 60, 15)
                painter.drawText(label_rect, Qt.AlignCenter, label)

    def _draw_sections(self, painter, track_x, track_y, track_width):
        """Draw colored sections between handles with rounded corners"""
        # Get handle positions
        positions = [track_x] + [self._value_to_pixel(v) for v in self.values] + [track_x + track_width]

        colors = self.section_colors if self.num_handles == 3 else self.rf_section_colors

        # Draw each section with rounded corners at edges
        for i in range(len(positions) - 1):
            x1 = positions[i]
            x2 = positions[i + 1]

            if x2 - x1 > 0:
                painter.setBrush(QBrush(colors[i]))
                painter.setPen(Qt.NoPen)

                # Use rounded rectangle only for first and last sections
                if i == 0:
                    # First section - round left corners only
                    painter.drawRoundedRect(int(x1), track_y, int(x2 - x1), self.track_height, 4, 4)
                    # Cover right side to make it square
                    painter.drawRect(int(x2 - 4), track_y, 4, self.track_height)
                elif i == len(positions) - 2:
                    # Last section - round right corners only
                    painter.drawRoundedRect(int(x1), track_y, int(x2 - x1), self.track_height, 4, 4)
                    # Cover left side to make it square
                    painter.drawRect(int(x1), track_y, 4, self.track_height)
                else:
                    # Middle sections - no rounding
                    painter.drawRect(int(x1), track_y, int(x2 - x1), self.track_height)

    def _draw_handle(self, painter, x, y, index):
        """Draw a single handle with depth and modern styling"""
        # Draw shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 80)))
        painter.drawEllipse(QPointF(x + 2, y + 2), self.handle_radius, self.handle_radius)

        # Draw outer glow for active handle
        if index == self.active_handle:
            painter.setBrush(QBrush(QColor(100, 150, 255, 60)))
            painter.drawEllipse(QPointF(x, y), self.handle_radius + 3, self.handle_radius + 3)

        # Draw handle with gradient
        gradient = QLinearGradient(x, y - self.handle_radius, x, y + self.handle_radius)
        gradient.setColorAt(0, QColor(255, 255, 255))
        gradient.setColorAt(1, QColor(230, 230, 235))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(self.handle_border_color, 2))
        painter.drawEllipse(QPointF(x, y), self.handle_radius, self.handle_radius)

        # Draw inner indicator/grip
        if index == self.active_handle:
            painter.setBrush(QBrush(QColor(100, 150, 255)))
        else:
            painter.setBrush(QBrush(QColor(140, 140, 145)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(x, y), self.handle_radius - 4, self.handle_radius - 4)

    def _value_to_pixel(self, value):
        """Convert value to pixel position"""
        track_width = self.width() - 2 * self.margin
        ratio = (value - self.minimum) / (self.maximum - self.minimum)
        return self.margin + ratio * track_width

    def _pixel_to_value(self, pixel):
        """Convert pixel position to value"""
        track_width = self.width() - 2 * self.margin
        ratio = (pixel - self.margin) / track_width
        value = self.minimum + ratio * (self.maximum - self.minimum)
        return max(self.minimum, min(self.maximum, value))

    def _get_handle_at_position(self, x, y):
        """Get handle index at position, or None"""
        center_y = self.height() // 2

        # Check each handle
        for i, value in enumerate(self.values):
            handle_x = self._value_to_pixel(value)

            # Check if click is within handle circle
            dx = x - handle_x
            dy = y - center_y
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance <= self.handle_radius + 5:  # 5px tolerance
                return i

        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.active_handle = self._get_handle_at_position(event.x(), event.y())
            if self.active_handle is not None:
                self.update()

    def mouseMoveEvent(self, event):
        if self.active_handle is not None:
            new_value = self._pixel_to_value(event.x())

            # Apply constraints based on handle type
            new_value = self._apply_constraints(self.active_handle, new_value)

            if new_value != self.values[self.active_handle]:
                self.values[self.active_handle] = new_value
                self.update()
                self.valuesChanged.emit(self.get_values())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.active_handle = None
            self.update()

    def _apply_constraints(self, handle_index, new_value):
        """Apply constraints to handle movement"""
        if self.num_handles == 3:
            # For 3-handle mode (deadzone_bottom, actuation, deadzone_top)
            if handle_index == 0:  # Deadzone bottom
                # Must be less than actuation
                max_val = self.values[1] - 1
                return max(self.minimum, min(new_value, max_val))
            elif handle_index == 1:  # Actuation
                # Must be between deadzones
                min_val = self.values[0] + 1
                max_val = self.values[2] - 1
                return max(min_val, min(new_value, max_val))
            elif handle_index == 2:  # Deadzone top
                # Must be greater than actuation
                min_val = self.values[1] + 1
                return max(min_val, min(new_value, self.maximum))

        elif self.num_handles == 2:
            # For 2-handle mode (no strict ordering required)
            # But typically press_sens should be <= release_sens
            return max(self.minimum, min(new_value, self.maximum))

        return new_value


class TriggerSlider(MultiHandleSlider):
    """
    Specialized slider for trigger settings with 3 handles:
    - Deadzone bottom (from left: 0-20, where 0=0mm, 20=0.5mm)
    - Actuation point (normal: 0-100)
    - Deadzone top (from right: 0-20, where 0=0mm from top, 20=0.5mm from top)

    Deadzone top is inverted - stored internally as (100 - user_value)
    """

    deadzoneBottomChanged = pyqtSignal(int)
    actuationChanged = pyqtSignal(int)
    deadzoneTopChanged = pyqtSignal(int)

    def __init__(self, minimum=0, maximum=100, parent=None):
        super().__init__(num_handles=3, minimum=minimum, maximum=maximum, parent=parent)

        # Set default values: bottom=4 (0.1mm), actuation=60 (1.5mm), top=96 (which is 4 from right = 0.1mm)
        # Internal representation: [deadzone_bottom, actuation, 100 - deadzone_top]
        self.values = [4, 60, 96]  # 96 = 100 - 4

        # Store the actual user-facing deadzone_top value (inverted)
        self._user_deadzone_top = 4

        # Connect to emit individual signals
        self.valuesChanged.connect(self._on_values_changed)

    def _on_values_changed(self, values):
        """Emit individual signals for each handle"""
        self.deadzoneBottomChanged.emit(int(values[0]))
        self.actuationChanged.emit(int(values[1]))
        # For deadzone_top, emit the inverted value (distance from right)
        inverted_top = 100 - int(values[2])
        self._user_deadzone_top = inverted_top
        self.deadzoneTopChanged.emit(inverted_top)

    def set_deadzone_bottom(self, value):
        """Set deadzone bottom value (0-20)"""
        self.set_value(0, value)

    def set_actuation(self, value):
        """Set actuation point value (0-100)"""
        self.set_value(1, value)

    def set_deadzone_top(self, value):
        """Set deadzone top value (0-20, inverted internally to 100-80)"""
        # Convert user value (distance from top) to internal position
        self._user_deadzone_top = value
        internal_value = 100 - value
        self.set_value(2, internal_value)

    def get_deadzone_bottom(self):
        """Get deadzone bottom value"""
        return int(self.values[0])

    def get_actuation(self):
        """Get actuation point value"""
        return int(self.values[1])

    def get_deadzone_top(self):
        """Get deadzone top value (user-facing, inverted)"""
        return self._user_deadzone_top

    def _apply_constraints(self, handle_index, new_value):
        """Apply constraints to handle movement"""
        if handle_index == 0:  # Deadzone bottom
            # Must be less than actuation, max 20 (0.5mm)
            max_val = min(self.values[1] - 1, 20)
            return max(self.minimum, min(new_value, max_val))
        elif handle_index == 1:  # Actuation
            # Must be between deadzones
            min_val = self.values[0] + 1
            max_val = self.values[2] - 1
            return max(min_val, min(new_value, max_val))
        elif handle_index == 2:  # Deadzone top (inverted)
            # Must be greater than actuation
            # User value range is 0-20, internal is 100-80
            min_val = max(self.values[1] + 1, 80)  # 80 = 100 - 20 (max 0.5mm deadzone)
            return max(min_val, min(new_value, self.maximum))

        return new_value


class RapidTriggerSlider(MultiHandleSlider):
    """
    Specialized slider for rapid trigger settings with 2 handles:
    - Press sensitivity (from left: 1-100, where 1=0.025mm, 100=2.5mm)
    - Release sensitivity (from right: 1-100, where 1=0.025mm from right, inverted)

    Release is inverted - stored internally as (101 - user_value)
    """

    pressSensChanged = pyqtSignal(int)
    releaseSensChanged = pyqtSignal(int)

    def __init__(self, minimum=1, maximum=100, parent=None):
        super().__init__(num_handles=2, minimum=minimum, maximum=maximum, parent=parent)

        # Set default values: press=4 (0.1mm), release=96 (which is 4 from right = 0.1mm)
        # Internal representation: [press, 101 - release]
        self.values = [4, 96]  # 96 = 100 - 4 + 1 (accounting for minimum=1)

        # Store the actual user-facing release value (inverted)
        self._user_release = 4

        # Connect to emit individual signals
        self.valuesChanged.connect(self._on_values_changed)

    def _on_values_changed(self, values):
        """Emit individual signals for each handle"""
        self.pressSensChanged.emit(int(values[0]))
        # For release, emit the inverted value (distance from right)
        inverted_release = 101 - int(values[1])  # 101 because minimum is 1
        self._user_release = inverted_release
        self.releaseSensChanged.emit(inverted_release)

    def set_press_sens(self, value):
        """Set press sensitivity value (1-100)"""
        self.set_value(0, value)

    def set_release_sens(self, value):
        """Set release sensitivity value (1-100, inverted internally)"""
        # Convert user value (distance from right) to internal position
        self._user_release = value
        internal_value = 101 - value
        self.set_value(1, internal_value)

    def get_press_sens(self):
        """Get press sensitivity value"""
        return int(self.values[0])

    def get_release_sens(self):
        """Get release sensitivity value (user-facing, inverted)"""
        return self._user_release

    def _apply_constraints(self, handle_index, new_value):
        """Apply constraints to handle movement for rapid trigger"""
        # No strict ordering required, but keep within bounds
        return max(self.minimum, min(new_value, self.maximum))
