# SPDX-License-Identifier: GPL-2.0-or-later

"""
Curve Editor Widget
A reusable widget for editing analog curves with 4 coordinate points.
The curve passes through all 4 points using linear interpolation.
Used for both gaming analog curves and per-key velocity curves.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QDialog, QListWidget, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import Qt, QPoint, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPolygonF, QFont, QFontMetrics

from util import tr


class CurveEditorWidget(QWidget):
    """
    Interactive curve editor with 4 coordinate points.

    Features:
    - Visual curve display (300x300 canvas)
    - 4 draggable points (all on the curve, points 0/3 x-constrained)
    - Real-time polyline curve rendering through all points
    - Preset loading (factory + user curves)
    - "Save to User" functionality with local caching

    Signals:
    - curve_changed: Emitted when curve points change
    - save_to_user_requested: Emitted when user wants to save curve to a slot
    - user_curve_selected: Emitted when user curve is selected from dropdown
    """

    curve_changed = pyqtSignal(list)  # [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
    save_to_user_requested = pyqtSignal(int, str)  # (slot_index, curve_name)
    user_curve_selected = pyqtSignal(int)  # slot_index (0-9) when user curve is selected

    # Factory curve names (indices 0-6)
    FACTORY_CURVES = [
        "Softest",
        "Soft",
        "Linear",
        "Hard",
        "Hardest",
        "Aggro",
        "Digital"
    ]

    # Factory curve presets (same as firmware)
    # All 4 points are on the curve, connected by straight line segments (piecewise linear)
    FACTORY_CURVE_POINTS = [
        # Softest - Very gentle, output much lower than input
        [[0, 0], [85, 28], [170, 85], [255, 255]],
        # Soft - Gentle curve, gradual response
        [[0, 0], [85, 42], [170, 128], [255, 255]],
        # Linear - 1:1 response
        [[0, 0], [85, 85], [170, 170], [255, 255]],
        # Hard - Steeper curve, faster response
        [[0, 0], [85, 128], [170, 213], [255, 255]],
        # Hardest - Very steep, aggressive response
        [[0, 0], [64, 160], [128, 230], [255, 255]],
        # Aggro - Rapid acceleration
        [[0, 0], [42, 170], [85, 220], [255, 255]],
        # Digital - Binary-like instant response
        [[0, 0], [10, 255], [20, 255], [255, 255]]
    ]

    def __init__(self, parent=None, show_save_button=True):
        super().__init__(parent)
        self.show_save_button = show_save_button
        self.user_curve_names = ["User 1", "User 2", "User 3", "User 4", "User 5",
                                 "User 6", "User 7", "User 8", "User 9", "User 10"]

        # Local cache for user curves (persists when switching presets)
        # Key: slot_index (0-9), Value: [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
        self.user_curves_cache = {}

        # Initialize with linear curve
        self.points = [[0, 0], [85, 85], [170, 170], [255, 255]]
        self.dragging_point = -1  # Which point is being dragged (-1 = none)

        # Canvas settings
        self.canvas_size = 300
        self.margin = 20
        self.grid_divisions = 10

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Preset selector widget (can be hidden as a unit)
        self.preset_selector_widget = QWidget()
        preset_layout = QHBoxLayout()
        preset_layout.setContentsMargins(0, 0, 0, 0)
        self.preset_selector_widget.setLayout(preset_layout)

        self.preset_label = QLabel(tr("CurveEditor", "Preset:"))
        self.preset_combo = QComboBox()

        # Add factory curves
        for i, name in enumerate(self.FACTORY_CURVES):
            self.preset_combo.addItem(name, i)

        # Add separator
        self.preset_combo.insertSeparator(len(self.FACTORY_CURVES))

        # Add user curves (indices 7-16)
        for i, name in enumerate(self.user_curve_names):
            self.preset_combo.addItem(name, 7 + i)

        # Add custom option
        self.preset_combo.insertSeparator(self.preset_combo.count())
        self.preset_combo.addItem("Custom", -1)

        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)

        preset_layout.addWidget(self.preset_label)
        preset_layout.addWidget(self.preset_combo, 1)

        if self.show_save_button:
            self.save_to_user_btn = QPushButton(tr("CurveEditor", "Save to User..."))
            self.save_to_user_btn.clicked.connect(self.on_save_to_user_clicked)
            preset_layout.addWidget(self.save_to_user_btn)

        layout.addWidget(self.preset_selector_widget)

        # Canvas (drawing area)
        self.canvas = CurveCanvas(self, self.points, self.canvas_size, self.margin, self.grid_divisions)
        self.canvas.point_moved.connect(self.on_point_moved)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def on_preset_changed(self, index):
        """Load selected preset curve"""
        curve_index = self.preset_combo.currentData()

        if curve_index == -1:
            # Custom - don't change anything
            return
        elif curve_index < 7:
            # Factory curve - load points directly
            self.set_points(self.FACTORY_CURVE_POINTS[curve_index])
        else:
            # User curve (7-16) - always emit signal to load full preset from keyboard
            # This ensures all settings (velocity, aftertouch, etc.) are reloaded, not just curve points
            slot_index = curve_index - 7  # Convert to 0-9 slot index
            self.user_curve_selected.emit(slot_index)

    def on_point_moved(self, point_index, x, y):
        """Called when user drags a point"""
        if point_index >= 0 and point_index < 4:
            self.points[point_index] = [x, y]

            # Switch to "Custom" preset
            custom_index = self.preset_combo.findData(-1)
            if custom_index >= 0:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentIndex(custom_index)
                self.preset_combo.blockSignals(False)

            self.curve_changed.emit(self.points)

    def on_save_to_user_clicked(self):
        """Show dialog to save current curve to a user slot"""
        dialog = SaveToUserDialog(self, self.user_curve_names)
        if dialog.exec_() == QDialog.Accepted:
            slot_index = dialog.get_selected_slot()
            slot_name = dialog.get_curve_name()
            if slot_index >= 0 and slot_index < 10:
                # Cache the curve locally so it persists when switching presets
                self.cache_user_curve(slot_index, self.points)
                self.save_to_user_requested.emit(slot_index, slot_name)

    def cache_user_curve(self, slot_index, points):
        """Cache a user curve locally for quick access when switching presets"""
        if 0 <= slot_index < 10 and len(points) == 4:
            self.user_curves_cache[slot_index] = [list(p) for p in points]  # Deep copy

    def set_points(self, points):
        """Set curve points programmatically"""
        if len(points) == 4:
            self.points = [list(p) for p in points]  # Deep copy
            self.canvas.set_points(self.points)
            self.canvas.update()
            self.curve_changed.emit(self.points)

    def get_points(self):
        """Get current curve points"""
        return [list(p) for p in self.points]  # Deep copy

    def set_user_curve_names(self, names):
        """Update user curve names in dropdown"""
        if len(names) == 10:
            self.user_curve_names = list(names)

            # Update combo box
            self.preset_combo.blockSignals(True)
            for i in range(10):
                # User curves start after factory curves + separator
                combo_index = len(self.FACTORY_CURVES) + 1 + i
                self.preset_combo.setItemText(combo_index, names[i])
            self.preset_combo.blockSignals(False)

    def set_user_curve_name(self, slot_index, name):
        """Update a single user curve name in dropdown"""
        if slot_index < 0 or slot_index >= 10:
            return
        self.user_curve_names[slot_index] = name
        # User curves start after factory curves + separator
        combo_index = len(self.FACTORY_CURVES) + 1 + slot_index
        self.preset_combo.blockSignals(True)
        self.preset_combo.setItemText(combo_index, name)
        self.preset_combo.blockSignals(False)

    def select_curve(self, curve_index):
        """Select a curve by index (0-16 or -1 for custom)"""
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemData(i) == curve_index:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentIndex(i)
                self.preset_combo.blockSignals(False)
                break

    def get_selected_curve_index(self):
        """Get the currently selected curve index (0-16 or -1 for custom)"""
        return self.preset_combo.currentData()

    def load_user_curve_points(self, points, slot_index=None):
        """Load user curve points without emitting curve_changed signal.
        Used when loading curve data from keyboard for display.
        Optionally caches the curve if slot_index is provided."""
        if len(points) == 4:
            self.points = [list(p) for p in points]  # Deep copy
            self.canvas.set_points(self.points)
            self.canvas.update()
            # Cache the curve if slot_index is provided
            if slot_index is not None:
                self.cache_user_curve(slot_index, points)


class CurveCanvas(QWidget):
    """
    Canvas widget for drawing and interacting with the curve.
    All 4 points are on the curve and connected by straight lines (polyline).
    Points 0 and 3 have x-axis constraints (0 and 255 respectively).
    """

    point_moved = pyqtSignal(int, int, int)  # (point_index, x, y)

    def __init__(self, parent, points, size, margin, grid_divisions):
        super().__init__(parent)
        self.points = points
        self.canvas_size = size
        self.margin_top = margin
        self.margin_right = margin
        self.margin_left = margin + 20   # Extra space for Y axis label
        self.margin_bottom = margin + 18  # Extra space for X axis label
        self.grid_divisions = grid_divisions
        self.dragging_point = -1

        # Draw area stays the same as original (size - 2*margin)
        draw_area = size - 2 * margin
        widget_w = self.margin_left + draw_area + self.margin_right
        widget_h = self.margin_top + draw_area + self.margin_bottom
        self.setFixedSize(widget_w, widget_h)
        self.setMouseTracking(True)

        # Visual settings
        self.point_radius = 6
        self.hover_point = -1

    def set_points(self, points):
        self.points = self._validate_points(points)

    def _validate_points(self, points):
        """Ensure points have valid, non-overlapping x values.
        Points must maintain order: P0.x < P1.x < P2.x < P3.x"""
        if len(points) != 4:
            return points

        validated = [list(p) for p in points]  # Deep copy

        # Clamp all values to 0-255
        for p in validated:
            p[0] = max(0, min(255, p[0]))
            p[1] = max(0, min(255, p[1]))

        # Fix P0 and P3 x-coordinates
        validated[0][0] = 0
        validated[3][0] = 255

        # Ensure P1.x is between P0.x and P2.x (with minimum gap of 1)
        validated[1][0] = max(1, min(validated[2][0] - 1, validated[1][0]))

        # Ensure P2.x is between P1.x and P3.x (with minimum gap of 1)
        validated[2][0] = max(validated[1][0] + 1, min(254, validated[2][0]))

        # Re-check P1 in case P2 was adjusted
        validated[1][0] = max(1, min(validated[2][0] - 1, validated[1][0]))

        return validated

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        # Draw grid
        self.draw_grid(painter)

        # Draw curve
        self.draw_curve(painter)

        # Draw control points
        self.draw_control_points(painter)

    def _draw_area(self):
        """Return (draw_w, draw_h) of the plot area"""
        w = self.width() - self.margin_left - self.margin_right
        h = self.height() - self.margin_top - self.margin_bottom
        return w, h

    def draw_grid(self, painter):
        """Draw grid background"""
        pen = QPen(QColor(50, 50, 50))
        painter.setPen(pen)

        draw_w, draw_h = self._draw_area()
        step_x = draw_w // self.grid_divisions
        step_y = draw_h // self.grid_divisions

        # Vertical lines
        for i in range(self.grid_divisions + 1):
            x = self.margin_left + i * step_x
            painter.drawLine(x, self.margin_top, x, self.margin_top + draw_h)

        # Horizontal lines
        for i in range(self.grid_divisions + 1):
            y = self.margin_top + i * step_y
            painter.drawLine(self.margin_left, y, self.margin_left + draw_w, y)

        # Axis labels
        label_font = QFont()
        label_font.setPixelSize(10)
        painter.setFont(label_font)
        painter.setPen(QPen(QColor(160, 160, 160)))

        # X axis title: "Time to press (ms)" centered below the plot
        x_label = "Time to press (ms)"
        fm = QFontMetrics(label_font)
        text_w = fm.horizontalAdvance(x_label)
        x_center = self.margin_left + draw_w // 2 - text_w // 2
        painter.drawText(x_center, self.margin_top + draw_h + self.margin_bottom - 2, x_label)

        # Y axis title: "Velocity" rotated, centered along left edge
        painter.save()
        y_label = "Velocity"
        text_w_y = fm.horizontalAdvance(y_label)
        y_center = self.margin_top + draw_h // 2 + text_w_y // 2
        painter.translate(12, y_center)
        painter.rotate(-90)
        painter.drawText(0, 0, y_label)
        painter.restore()

    def draw_curve(self, painter):
        """Draw the curve as polyline through all 4 points"""
        pen = QPen(QColor(255, 165, 0), 2)  # Orange
        painter.setPen(pen)

        # Convert points to canvas coordinates
        canvas_points = [self.value_to_canvas(p) for p in self.points]

        # Draw polyline connecting all points
        for i in range(len(canvas_points) - 1):
            painter.drawLine(canvas_points[i], canvas_points[i + 1])

    def draw_control_points(self, painter):
        """Draw draggable control points - all 4 points are draggable"""
        for i, point in enumerate(self.points):
            canvas_point = self.value_to_canvas(point)

            # All points are draggable (0 and 3 are x-constrained but still draggable)
            if i == self.hover_point or i == self.dragging_point:
                color = QColor(255, 200, 0)  # Bright yellow (hover/dragging)
            elif i == 0 or i == 3:
                color = QColor(200, 100, 50)  # Darker orange for constrained points
            else:
                color = QColor(255, 165, 0)  # Orange

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.white, 2))
            painter.drawEllipse(canvas_point, self.point_radius, self.point_radius)

    def value_to_canvas(self, point):
        """Convert value coordinates (0-255) to canvas coordinates"""
        draw_w, draw_h = self._draw_area()
        x = self.margin_left + (point[0] / 255.0) * draw_w
        # Invert Y axis (0 at bottom, 255 at top)
        y = self.margin_top + draw_h - (point[1] / 255.0) * draw_h
        return QPointF(x, y)

    def canvas_to_value(self, pos):
        """Convert canvas coordinates to value coordinates (0-255)"""
        draw_w, draw_h = self._draw_area()
        x = ((pos.x() - self.margin_left) / draw_w) * 255.0
        # Invert Y axis
        y = ((self.margin_top + draw_h - pos.y()) / draw_h) * 255.0

        # Clamp to 0-255
        x = max(0, min(255, x))
        y = max(0, min(255, y))

        return [int(x), int(y)]

    def mousePressEvent(self, event):
        """Start dragging a point - all 4 points are draggable"""
        if event.button() == Qt.LeftButton:
            for i in range(4):  # All 4 points are draggable
                canvas_point = self.value_to_canvas(self.points[i])
                dist = (event.pos() - canvas_point.toPoint()).manhattanLength()
                if dist <= self.point_radius + 5:
                    self.dragging_point = i
                    break

    def mouseMoveEvent(self, event):
        """Drag point or update hover state"""
        if self.dragging_point >= 0:
            # Update dragged point with constraints
            new_value = self.canvas_to_value(event.pos())

            # Apply x-axis constraints to prevent points from crossing each other
            # Points must maintain order: P0.x < P1.x < P2.x < P3.x
            if self.dragging_point == 0:
                new_value[0] = 0  # Point 0 fixed at x=0
            elif self.dragging_point == 1:
                # Point 1 must stay between P0 (x=0) and P2
                min_x = 1  # At least 1 more than P0
                max_x = self.points[2][0] - 1  # At least 1 less than P2
                new_value[0] = max(min_x, min(max_x, new_value[0]))
            elif self.dragging_point == 2:
                # Point 2 must stay between P1 and P3 (x=255)
                min_x = self.points[1][0] + 1  # At least 1 more than P1
                max_x = 254  # At least 1 less than P3
                new_value[0] = max(min_x, min(max_x, new_value[0]))
            elif self.dragging_point == 3:
                new_value[0] = 255  # Point 3 fixed at x=255

            self.points[self.dragging_point] = new_value
            self.point_moved.emit(self.dragging_point, new_value[0], new_value[1])
            self.update()
        else:
            # Update hover state
            old_hover = self.hover_point
            self.hover_point = -1
            for i in range(4):  # All 4 points
                canvas_point = self.value_to_canvas(self.points[i])
                dist = (event.pos() - canvas_point.toPoint()).manhattanLength()
                if dist <= self.point_radius + 5:
                    self.hover_point = i
                    break

            if old_hover != self.hover_point:
                self.update()

    def mouseReleaseEvent(self, event):
        """Stop dragging"""
        if event.button() == Qt.LeftButton:
            self.dragging_point = -1


class SaveToUserDialog(QDialog):
    """Dialog for saving curve to a user slot with custom name input"""

    def __init__(self, parent, user_curve_names):
        super().__init__(parent)
        self.user_curve_names = user_curve_names
        self.setWindowTitle(tr("SaveToUserDialog", "Save to User Curve"))
        self.setup_ui()

    def setup_ui(self):
        from PyQt5.QtWidgets import QLineEdit, QFormLayout

        layout = QVBoxLayout()

        # Instructions
        label = QLabel(tr("SaveToUserDialog", "Select a user curve slot to save to:"))
        layout.addWidget(label)

        # List of user slots
        self.list_widget = QListWidget()
        for i, name in enumerate(self.user_curve_names):
            self.list_widget.addItem(f"User {i+1}: {name}")
        self.list_widget.setCurrentRow(0)
        self.list_widget.currentRowChanged.connect(self.on_slot_changed)
        layout.addWidget(self.list_widget)

        # Name input field
        name_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(16)
        self.name_input.setPlaceholderText(tr("SaveToUserDialog", "Enter curve name (max 16 chars)"))
        self.name_input.setText("User 1")  # Default name for first slot
        name_layout.addRow(tr("SaveToUserDialog", "Curve Name:"), self.name_input)
        layout.addLayout(name_layout)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setMinimumWidth(350)

    def on_slot_changed(self, row):
        """Update name input when slot selection changes"""
        if row >= 0 and row < len(self.user_curve_names):
            current_name = self.user_curve_names[row]
            # If the current name looks like a default (User N or XX...), suggest "User N"
            if current_name.startswith("User ") or current_name.endswith("..."):
                self.name_input.setText(f"User {row + 1}")
            else:
                self.name_input.setText(current_name)

    def get_selected_slot(self):
        """Get selected slot index (0-9)"""
        return self.list_widget.currentRow()

    def get_curve_name(self):
        """Get name for the curve from input field"""
        name = self.name_input.text().strip()
        if not name:
            slot = self.get_selected_slot()
            return f"User {slot + 1}"
        return name[:16]  # Truncate to 16 chars
