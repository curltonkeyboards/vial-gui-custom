# SPDX-License-Identifier: GPL-2.0-or-later
import math
import struct
import json

from PyQt5.QtWidgets import (QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel,
                           QSizePolicy, QGroupBox, QGridLayout, QComboBox, QCheckBox,
                           QTableWidget, QHeaderView, QMessageBox, QFileDialog, QFrame,
                           QScrollArea, QSlider, QMenu)
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore
from PyQt5.QtGui import QPainterPath, QRegion, QPainter, QColor, QBrush, QPen, QFont, QLinearGradient

from widgets.combo_box import ArrowComboBox
from editor.basic_editor import BasicEditor
from protocol.constants import VIAL_PROTOCOL_MATRIX_TESTER
from tabbed_keycodes import GamepadWidget, DpadButton
from protocol.keyboard_comm import (
    PARAM_CHANNEL_NUMBER, PARAM_TRANSPOSE_NUMBER, PARAM_TRANSPOSE_NUMBER2, PARAM_TRANSPOSE_NUMBER3,
    PARAM_HE_VELOCITY_CURVE, PARAM_HE_VELOCITY_MIN, PARAM_HE_VELOCITY_MAX,
    PARAM_KEYSPLIT_HE_VELOCITY_CURVE, PARAM_KEYSPLIT_HE_VELOCITY_MIN, PARAM_KEYSPLIT_HE_VELOCITY_MAX,
    PARAM_TRIPLESPLIT_HE_VELOCITY_CURVE, PARAM_TRIPLESPLIT_HE_VELOCITY_MIN, PARAM_TRIPLESPLIT_HE_VELOCITY_MAX,
    # PARAM_AFTERTOUCH_MODE and PARAM_AFTERTOUCH_CC removed - aftertouch is now per-layer
    PARAM_BASE_SUSTAIN, PARAM_KEYSPLIT_SUSTAIN, PARAM_TRIPLESPLIT_SUSTAIN,
    PARAM_KEYSPLITCHANNEL, PARAM_KEYSPLIT2CHANNEL, PARAM_KEYSPLITSTATUS,
    PARAM_KEYSPLITTRANSPOSESTATUS, PARAM_KEYSPLITVELOCITYSTATUS,
    # MIDI Routing Override Settings
    PARAM_CHANNEL_OVERRIDE, PARAM_VELOCITY_OVERRIDE, PARAM_TRANSPOSE_OVERRIDE,
    PARAM_MIDI_IN_MODE, PARAM_USB_MIDI_MODE, PARAM_MIDI_CLOCK_SOURCE
)
from widgets.keyboard_widget import KeyboardWidget2, KeyboardWidgetSimple
from util import tr
from vial_device import VialKeyboard
from unlocker import Unlocker


class ActuationVisualizer(QWidget):
    """Vertical bar widget that shows key travel distance in real-time"""

    def __init__(self, row, col, label=None, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.label = label if label else f"R{row}C{col}"
        self.distance_mm = 0.0  # Current distance in mm
        self.max_travel_mm = 4.0  # Maximum key travel in mm

        # Calibration debug values
        self.rest_adc = 0
        self.bottom_adc = 0
        self.raw_adc = 0

        # Widget size - compact but shows debug info
        self.setMinimumWidth(85)
        self.setMinimumHeight(280)
        self.setMaximumWidth(95)

    def set_distance(self, distance_hundredths_mm):
        """Set the current distance in 0.01mm units (0-400 for 0-4.0mm)"""
        self.distance_mm = distance_hundredths_mm / 100.0
        self.update()

    def set_calibration(self, rest, bottom, raw):
        """Set calibration debug values"""
        self.rest_adc = rest
        self.bottom_adc = bottom
        self.raw_adc = raw
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Margins - reduced for compact display
        margin_top = 20
        margin_bottom = 90  # Space for debug info
        margin_side = 5
        bar_width = width - 2 * margin_side
        bar_height = height - margin_top - margin_bottom

        # Draw label at top
        painter.setPen(QColor(200, 200, 200))
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(0, 0, width, margin_top - 2, Qt.AlignCenter, self.label)

        # Draw outer frame (the track)
        track_rect = QtCore.QRectF(margin_side, margin_top, bar_width, bar_height)
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.drawRoundedRect(track_rect, 5, 5)

        # Calculate fill height based on distance (0mm = top, 4mm = bottom)
        fill_ratio = min(self.distance_mm / self.max_travel_mm, 1.0)
        fill_height = fill_ratio * (bar_height - 4)  # -4 for inner padding

        # Draw the fill bar (grows from top down as key is pressed)
        if fill_height > 0:
            fill_rect = QtCore.QRectF(
                margin_side + 2,
                margin_top + 2,
                bar_width - 4,
                fill_height
            )

            # Gradient color: green at top, yellow in middle, red at bottom
            gradient = QLinearGradient(0, margin_top, 0, margin_top + bar_height)
            gradient.setColorAt(0.0, QColor(0, 200, 0))      # Green at top (released)
            gradient.setColorAt(0.5, QColor(255, 200, 0))    # Yellow in middle
            gradient.setColorAt(1.0, QColor(255, 50, 50))    # Red at bottom (fully pressed)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(fill_rect, 3, 3)

        # Draw scale markers on the right side
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        small_font = QFont()
        small_font.setPointSize(7)
        painter.setFont(small_font)

        for mm in [0, 1, 2, 3, 4]:
            y_pos = margin_top + (mm / self.max_travel_mm) * bar_height
            # Draw tick mark
            painter.drawLine(int(width - margin_side + 2), int(y_pos),
                           int(width - margin_side + 6), int(y_pos))
            # Draw label
            painter.drawText(int(width - margin_side + 8), int(y_pos - 6),
                           30, 12, Qt.AlignLeft | Qt.AlignVCenter, f"{mm}")

        # Draw current distance value
        painter.setPen(QColor(255, 255, 255))
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        distance_text = f"{self.distance_mm:.2f}mm"
        y_start = height - margin_bottom + 5
        painter.drawText(0, y_start, width, 18, Qt.AlignCenter, distance_text)

        # Draw calibration debug info
        small_font.setPointSize(7)
        small_font.setBold(False)
        painter.setFont(small_font)
        painter.setPen(QColor(180, 180, 180))

        # Rest ADC
        painter.drawText(0, y_start + 20, width, 14, Qt.AlignCenter, f"Rest: {self.rest_adc}")
        # Bottom ADC
        painter.drawText(0, y_start + 34, width, 14, Qt.AlignCenter, f"Bot: {self.bottom_adc}")
        # Raw ADC (current)
        painter.setPen(QColor(100, 200, 255))  # Cyan for current reading
        painter.drawText(0, y_start + 48, width, 14, Qt.AlignCenter, f"Raw: {self.raw_adc}")
        # Calculated range
        painter.setPen(QColor(255, 200, 100))  # Orange for range
        range_val = self.rest_adc - self.bottom_adc if self.rest_adc > self.bottom_adc else 0
        painter.drawText(0, y_start + 62, width, 14, Qt.AlignCenter, f"Rng: {range_val}")


class MatrixTest(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor

        self.addStretch()

        # Container for title, description, keyboard widget and buttons
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setSpacing(6)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(container_layout)

        # Title
        title_label = QLabel(tr("MatrixTest", "Matrix Tester"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.addWidget(title_label)

        # Description
        desc_label = QLabel(tr("MatrixTest",
            "Test individual key switches by pressing them. Each key will light up when its switch\n"
            "is activated, helping identify faulty or stuck switches."))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 9pt;")
        desc_label.setAlignment(QtCore.Qt.AlignCenter)
        container_layout.addWidget(desc_label)

        self.KeyboardWidget2 = KeyboardWidgetSimple(layout_editor)
        self.KeyboardWidget2.set_enabled(False)

        self.unlock_btn = QPushButton("Unlock")
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setMinimumHeight(30)
        self.reset_btn.setMaximumHeight(30)
        self.reset_btn.setMinimumWidth(80)
        self.reset_btn.setStyleSheet("QPushButton { border-radius: 5px; }")

        # Horizontal layout for keyboard widget and actuation visualizers
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(20)

        # Keyboard widget
        keyboard_layout = QVBoxLayout()
        keyboard_layout.addWidget(self.KeyboardWidget2)
        keyboard_layout.setAlignment(self.KeyboardWidget2, Qt.AlignCenter)
        main_content_layout.addLayout(keyboard_layout)

        # Actuation Visualizer section
        visualizer_container = QWidget()
        visualizer_layout = QVBoxLayout()
        visualizer_layout.setSpacing(5)
        visualizer_layout.setContentsMargins(0, 0, 0, 0)
        visualizer_container.setLayout(visualizer_layout)

        # Visualizer title
        viz_title = QLabel(tr("MatrixTest", "Key Travel (mm)"))
        viz_title.setStyleSheet("font-weight: bold; font-size: 10pt;")
        viz_title.setAlignment(Qt.AlignCenter)
        visualizer_layout.addWidget(viz_title)

        # Create 4 visualizer slots with dropdown selectors
        self.actuation_visualizers = {}
        self.visualizer_widgets = []  # Store (viz, row_combo, col_combo) tuples
        self.distance_keys = []  # Will be populated dynamically

        visualizer_bars_layout = QHBoxLayout()
        visualizer_bars_layout.setSpacing(5)

        # Default keys to visualize (0-indexed internally, displayed as 1-indexed)
        default_keys = [(0, 0), (0, 3), (0, 11), (3, 0)]

        for idx, (default_row, default_col) in enumerate(default_keys):
            # Container for each visualizer + its dropdowns
            viz_container = QWidget()
            viz_layout = QVBoxLayout()
            viz_layout.setContentsMargins(0, 0, 0, 0)
            viz_layout.setSpacing(2)
            viz_container.setLayout(viz_layout)

            # Row/Col selector dropdowns (displayed as 1-indexed)
            selector_layout = QHBoxLayout()
            selector_layout.setSpacing(1)
            selector_layout.setContentsMargins(0, 0, 0, 0)

            row_label = QLabel("Row")
            row_label.setStyleSheet("font-size: 7pt;")
            row_combo = QComboBox()
            row_combo.setMaximumWidth(40)
            row_combo.setStyleSheet("font-size: 7pt; padding: 0px;")
            # Add rows 1-5 (internally 0-4)
            for r in range(1, 6):
                row_combo.addItem(str(r), r - 1)  # Display 1-indexed, store 0-indexed
            row_combo.setCurrentIndex(default_row)

            col_label = QLabel("Col")
            col_label.setStyleSheet("font-size: 7pt;")
            col_combo = QComboBox()
            col_combo.setMaximumWidth(40)
            col_combo.setStyleSheet("font-size: 7pt; padding: 0px;")
            # Add cols 1-14 (internally 0-13)
            for c in range(1, 15):
                col_combo.addItem(str(c), c - 1)  # Display 1-indexed, store 0-indexed
            col_combo.setCurrentIndex(default_col)

            selector_layout.addWidget(row_label)
            selector_layout.addWidget(row_combo)
            selector_layout.addWidget(col_label)
            selector_layout.addWidget(col_combo)
            viz_layout.addLayout(selector_layout)

            # Create the visualizer bar
            label = f"R{default_row + 1}C{default_col + 1}"
            viz = ActuationVisualizer(default_row, default_col, label)
            viz_layout.addWidget(viz)

            # Connect dropdowns to update visualizer
            def make_key_updater(v, rc, cc, i):
                def update():
                    row = rc.currentData()
                    col = cc.currentData()
                    v.row = row
                    v.col = col
                    v.label = f"R{row + 1}C{col + 1}"
                    self.update_distance_keys()
                return update

            row_combo.currentIndexChanged.connect(make_key_updater(viz, row_combo, col_combo, idx))
            col_combo.currentIndexChanged.connect(make_key_updater(viz, row_combo, col_combo, idx))

            visualizer_bars_layout.addWidget(viz_container)

            self.visualizer_widgets.append((viz, row_combo, col_combo))
            self.actuation_visualizers[(default_row, default_col)] = viz

        visualizer_layout.addLayout(visualizer_bars_layout)
        self.update_distance_keys()

        # Show Advanced Tuning toggle button
        self.advanced_tuning_btn = QPushButton("Show Advanced Tuning")
        self.advanced_tuning_btn.setCheckable(True)
        self.advanced_tuning_btn.setMaximumWidth(150)
        self.advanced_tuning_btn.clicked.connect(self.toggle_advanced_tuning)
        visualizer_layout.addWidget(self.advanced_tuning_btn)

        # Advanced tuning container (hidden by default)
        self.advanced_tuning_widget = QWidget()
        self.advanced_tuning_widget.setVisible(False)
        advanced_layout = QVBoxLayout()
        advanced_layout.setContentsMargins(0, 5, 0, 0)
        self.advanced_tuning_widget.setLayout(advanced_layout)

        # EQ-Style Sensitivity Curve Controls
        eq_group = QGroupBox(tr("MatrixTest", "Sensitivity EQ (by Rest ADC Range)"))
        eq_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        eq_main_layout = QVBoxLayout()
        eq_main_layout.setSpacing(8)
        eq_group.setLayout(eq_main_layout)

        # Range boundary controls
        range_layout = QHBoxLayout()
        range_layout.setSpacing(10)

        range_layout.addWidget(QLabel("Low/Mid boundary:"))
        self.eq_range_low_slider = QSlider(Qt.Horizontal)
        self.eq_range_low_slider.setRange(1400, 2200)
        self.eq_range_low_slider.setValue(1745)  # Updated default
        self.eq_range_low_slider.setMaximumWidth(100)
        self.eq_range_low_label = QLabel("1745")
        self.eq_range_low_label.setMinimumWidth(35)
        self.eq_range_low_slider.valueChanged.connect(lambda v: self.eq_range_low_label.setText(str(v)))
        self.eq_range_low_slider.valueChanged.connect(self.send_eq_settings)
        range_layout.addWidget(self.eq_range_low_slider)
        range_layout.addWidget(self.eq_range_low_label)

        range_layout.addWidget(QLabel("Mid/High boundary:"))
        self.eq_range_high_slider = QSlider(Qt.Horizontal)
        self.eq_range_high_slider.setRange(1600, 2500)
        self.eq_range_high_slider.setValue(2082)  # Updated default
        self.eq_range_high_slider.setMaximumWidth(100)
        self.eq_range_high_label = QLabel("2082")
        self.eq_range_high_label.setMinimumWidth(35)
        self.eq_range_high_slider.valueChanged.connect(lambda v: self.eq_range_high_label.setText(str(v)))
        self.eq_range_high_slider.valueChanged.connect(self.send_eq_settings)
        range_layout.addWidget(self.eq_range_high_slider)
        range_layout.addWidget(self.eq_range_high_label)

        range_layout.addStretch()
        eq_main_layout.addLayout(range_layout)

        # Band labels for columns
        band_names = ["Low\n0-20%", "Low-Mid\n20-40%", "Mid\n40-60%", "High-Mid\n60-80%", "High\n80-100%"]
        # Range 1 (Mid) is the neutral baseline at the midpoint between boundaries
        # Range 0 (Low) defines adjustment at/below low boundary (extrapolates further below)
        # Range 2 (High) defines adjustment at/above high boundary (extrapolates further above)
        range_names = ["Low Rest\n(at low bound)", "Mid Rest\n(NEUTRAL)", "High Rest\n(at high bound)"]

        # EQ sliders grid: 3 ranges × 5 bands + 1 range scale
        self.eq_sliders = []  # [range][band]
        self.eq_labels = []
        self.eq_range_scale_sliders = []  # [range]
        self.eq_range_scale_labels = []

        eq_grid = QGridLayout()
        eq_grid.setSpacing(3)

        # Header row with band names
        for band in range(5):
            header = QLabel(band_names[band])
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("font-size: 7pt; color: #aaa;")
            eq_grid.addWidget(header, 0, band + 1)

        # Range Scale header (column 6)
        scale_header = QLabel("Range\nScale")
        scale_header.setAlignment(Qt.AlignCenter)
        scale_header.setStyleSheet("font-size: 7pt; color: #ffa500; font-weight: bold;")
        eq_grid.addWidget(scale_header, 0, 6)

        # Create sliders for each range
        for range_idx in range(3):
            self.eq_sliders.append([])
            self.eq_labels.append([])

            # Range label
            range_label = QLabel(range_names[range_idx])
            range_label.setStyleSheet("font-size: 8pt; font-weight: bold;")
            eq_grid.addWidget(range_label, range_idx + 1, 0)

            for band in range(5):
                # Create vertical slider (25% to 400%, stored as 12-200)
                slider = QSlider(Qt.Vertical)
                slider.setRange(12, 200)  # Half-percentage: 12=25%, 50=100%, 200=400%
                slider.setValue(50)  # Default 100%
                slider.setMinimumHeight(60)
                slider.setMaximumHeight(80)
                slider.setTickPosition(QSlider.TicksBothSides)
                slider.setTickInterval(25)

                # Create value label
                value_label = QLabel("100%")
                value_label.setAlignment(Qt.AlignCenter)
                value_label.setStyleSheet("font-size: 7pt;")
                value_label.setMinimumWidth(35)

                # Connect slider to update label and send settings
                def make_updater(lbl, r, b):
                    def update(v):
                        lbl.setText(f"{v*2}%")
                        self.send_eq_settings()
                    return update

                slider.valueChanged.connect(make_updater(value_label, range_idx, band))

                # Container for slider + label
                slider_container = QWidget()
                slider_layout = QVBoxLayout()
                slider_layout.setContentsMargins(2, 2, 2, 2)
                slider_layout.setSpacing(2)
                slider_layout.addWidget(slider, alignment=Qt.AlignCenter)
                slider_layout.addWidget(value_label, alignment=Qt.AlignCenter)
                slider_container.setLayout(slider_layout)

                eq_grid.addWidget(slider_container, range_idx + 1, band + 1)

                self.eq_sliders[range_idx].append(slider)
                self.eq_labels[range_idx].append(value_label)

            # Range Scale slider for this range (column 6)
            scale_slider = QSlider(Qt.Vertical)
            scale_slider.setRange(25, 100)  # Half-percentage: 25=50%, 50=100%, 100=200%
            scale_slider.setValue(50)  # Default 100%
            scale_slider.setMinimumHeight(60)
            scale_slider.setMaximumHeight(80)
            scale_slider.setTickPosition(QSlider.TicksBothSides)
            scale_slider.setTickInterval(25)

            scale_label = QLabel("100%")
            scale_label.setAlignment(Qt.AlignCenter)
            scale_label.setStyleSheet("font-size: 7pt; color: #ffa500;")
            scale_label.setMinimumWidth(35)

            def make_scale_updater(lbl):
                def update(v):
                    lbl.setText(f"{v*2}%")
                    self.send_eq_settings()
                return update

            scale_slider.valueChanged.connect(make_scale_updater(scale_label))

            # Container for scale slider + label
            scale_container = QWidget()
            scale_layout = QVBoxLayout()
            scale_layout.setContentsMargins(2, 2, 2, 2)
            scale_layout.setSpacing(2)
            scale_layout.addWidget(scale_slider, alignment=Qt.AlignCenter)
            scale_layout.addWidget(scale_label, alignment=Qt.AlignCenter)
            scale_container.setLayout(scale_layout)

            eq_grid.addWidget(scale_container, range_idx + 1, 6)

            self.eq_range_scale_sliders.append(scale_slider)
            self.eq_range_scale_labels.append(scale_label)

        eq_main_layout.addLayout(eq_grid)

        # Buttons row: Reset and Save
        eq_buttons_layout = QHBoxLayout()
        eq_buttons_layout.addStretch()

        reset_eq_btn = QPushButton("Reset to Defaults")
        reset_eq_btn.setMaximumWidth(120)
        reset_eq_btn.clicked.connect(self.reset_eq_to_defaults)
        eq_buttons_layout.addWidget(reset_eq_btn)

        save_eq_btn = QPushButton("Save to Device")
        save_eq_btn.setMaximumWidth(120)
        save_eq_btn.setStyleSheet("QPushButton { background-color: #4a9f4a; }")
        save_eq_btn.clicked.connect(self.save_eq_to_eeprom)
        eq_buttons_layout.addWidget(save_eq_btn)

        eq_main_layout.addLayout(eq_buttons_layout)

        advanced_layout.addWidget(eq_group)
        visualizer_layout.addWidget(self.advanced_tuning_widget)
        visualizer_layout.addStretch()

        main_content_layout.addWidget(visualizer_container)

        container_layout.addLayout(main_content_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.unlock_lbl = QLabel(tr("MatrixTest", "Unlock the keyboard before testing:"))
        btn_layout.addWidget(self.unlock_lbl)
        btn_layout.addWidget(self.unlock_btn)
        btn_layout.addWidget(self.reset_btn)
        container_layout.addLayout(btn_layout)

        # Wrap container in scroll area for resizable window
        scroll_area = QScrollArea()
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.addWidget(scroll_area)
        self.addStretch()

        self.keyboard = None
        self.device = None
        self.polling = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.matrix_poller)

        # ADC polling timer - runs slower to avoid overloading HID
        self.adc_timer = QTimer()
        self.adc_timer.timeout.connect(self.adc_poller)
        self.adc_poll_half = 0  # 0 = first half of rows, 1 = second half

        # Distance polling timer for actuation visualizers - fast updates for real-time feel
        self.distance_timer = QTimer()
        self.distance_timer.timeout.connect(self.distance_poller)
        # Keys to poll for distance: [(row, col), ...]
        self.distance_keys = [(0, 0), (0, 3), (0, 11), (3, 0)]

        self.unlock_btn.clicked.connect(self.unlock)
        self.reset_btn.clicked.connect(self.reset_keyboard_widget)

        self.grabber = QWidget()

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard

            self.KeyboardWidget2.set_keys(self.keyboard.keys, self.keyboard.encoders)
        self.KeyboardWidget2.setEnabled(self.valid())

    def valid(self):
        # Check if vial protocol is v3 or later
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard and self.device.keyboard.vial_protocol >= VIAL_PROTOCOL_MATRIX_TESTER) and \
               ((self.device.keyboard.cols // 8 + 1) * self.device.keyboard.rows <= 28)

    def reset_keyboard_widget(self):
        # reset keyboard widget
        for w in self.KeyboardWidget2.widgets:
            w.setPressed(False)
            w.setOn(False)
            w.setAdcValue(None)  # Clear ADC values

        # Reset actuation visualizers
        for viz in self.actuation_visualizers.values():
            viz.set_distance(0)

        self.KeyboardWidget2.update_layout()
        self.KeyboardWidget2.update()
        self.KeyboardWidget2.updateGeometry()

    def matrix_poller(self):
        if not self.valid():
            self.timer.stop()
            return

        try:
            unlocked = self.keyboard.get_unlock_status(3)
        except (RuntimeError, ValueError):
            self.timer.stop()
            return

        if not unlocked:
            self.unlock_btn.show()
            self.unlock_lbl.show()
            return

        # we're unlocked, so hide unlock button and label
        self.unlock_btn.hide()
        self.unlock_lbl.hide()

        # Get size for matrix
        rows = self.keyboard.rows
        cols = self.keyboard.cols
        # Generate 2d array of matrix
        matrix = [[None] * cols for x in range(rows)]

        # Get matrix data from keyboard
        try:
            data = self.keyboard.matrix_poll()
        except (RuntimeError, ValueError):
            self.timer.stop()
            return

        # Calculate the amount of bytes belong to 1 row, each bit is 1 key, so per 8 keys in a row,
        # a byte is needed for the row.
        row_size = math.ceil(cols / 8)

        for row in range(rows):
            # Make slice of bytes for the row (skip first 2 bytes, they're for VIAL)
            row_data_start = 2 + (row * row_size)
            row_data_end = row_data_start + row_size
            row_data = data[row_data_start:row_data_end]

            # Get each bit representing pressed state for col
            for col in range(cols):
                # row_data is array of bytes, calculate in which byte the col is located
                col_byte = len(row_data) - 1 - math.floor(col / 8)
                # since we select a single byte as slice of byte, mod 8 to get nth pos of byte
                col_mod = (col % 8)
                # write to matrix array
                matrix[row][col] = (row_data[col_byte] >> col_mod) & 1

        # write matrix state to keyboard widget
        for w in self.KeyboardWidget2.widgets:
            if w.desc.row is not None and w.desc.col is not None:
                row = w.desc.row
                col = w.desc.col

                if row < len(matrix) and col < len(matrix[row]):
                    w.setPressed(matrix[row][col])
                    if matrix[row][col]:
                        w.setOn(True)

        self.KeyboardWidget2.update_layout()
        self.KeyboardWidget2.update()
        self.KeyboardWidget2.updateGeometry()

    def adc_poller(self):
        """Poll ADC values for half the matrix rows each cycle"""
        if not self.valid():
            self.adc_timer.stop()
            return

        try:
            unlocked = self.keyboard.get_unlock_status(1)
        except (RuntimeError, ValueError):
            return

        if not unlocked:
            return

        rows = self.keyboard.rows
        cols = self.keyboard.cols

        # Determine which rows to poll this cycle (alternate between first and second half)
        half_rows = (rows + 1) // 2  # Round up for odd number of rows
        if self.adc_poll_half == 0:
            row_start = 0
            row_end = half_rows
        else:
            row_start = half_rows
            row_end = rows

        # Poll ADC values for the selected rows
        adc_matrix = {}
        for row in range(row_start, row_end):
            try:
                adc_values = self.keyboard.adc_matrix_poll(row)
                if adc_values:
                    adc_matrix[row] = adc_values
            except (RuntimeError, ValueError):
                continue

        # Update keyboard widget with ADC values
        for w in self.KeyboardWidget2.widgets:
            if w.desc.row is not None and w.desc.col is not None:
                row = w.desc.row
                col = w.desc.col

                # Only update keys in the rows we just polled
                if row in adc_matrix and col < len(adc_matrix[row]):
                    w.setAdcValue(adc_matrix[row][col])

        # Alternate to the other half for next poll
        self.adc_poll_half = 1 - self.adc_poll_half

        self.KeyboardWidget2.update()

    def distance_poller(self):
        """Poll distance and calibration values for specific keys to update actuation visualizers"""
        if not self.valid():
            self.distance_timer.stop()
            return

        try:
            unlocked = self.keyboard.get_unlock_status(1)
        except (RuntimeError, ValueError):
            return

        if not unlocked:
            return

        # Poll distance values for the visualized keys
        try:
            distances = self.keyboard.distance_matrix_poll(self.distance_keys)
            if distances:
                for (row, col), distance in distances.items():
                    if (row, col) in self.actuation_visualizers:
                        self.actuation_visualizers[(row, col)].set_distance(distance)
        except (RuntimeError, ValueError):
            pass

        # Poll calibration debug values (less frequently - every other call)
        if not hasattr(self, '_calib_poll_counter'):
            self._calib_poll_counter = 0
        self._calib_poll_counter += 1

        if self._calib_poll_counter >= 4:  # Every 4th poll (~200ms)
            self._calib_poll_counter = 0
            try:
                calibration = self.keyboard.calibration_debug_poll(self.distance_keys)
                if calibration:
                    for (row, col), calib in calibration.items():
                        if (row, col) in self.actuation_visualizers:
                            self.actuation_visualizers[(row, col)].set_calibration(
                                calib['rest'], calib['bottom'], calib['raw']
                            )
            except (RuntimeError, ValueError):
                pass

    def send_eq_settings(self):
        """Send EQ curve settings to the keyboard firmware"""
        if not self.keyboard:
            return

        range_low = self.eq_range_low_slider.value()
        range_high = self.eq_range_high_slider.value()

        # Collect all 15 band values (stored as half-percentage: 50 = 100%)
        bands = []
        for range_idx in range(3):
            for band in range(5):
                bands.append(self.eq_sliders[range_idx][band].value())

        # Collect 3 range scale values
        range_scales = []
        for range_idx in range(3):
            range_scales.append(self.eq_range_scale_sliders[range_idx].value())

        try:
            self.keyboard.set_eq_curve_settings(range_low, range_high, bands, range_scales)
        except (RuntimeError, ValueError, AttributeError):
            pass

    def reset_eq_to_defaults(self):
        """Reset all EQ sliders to tuned baseline values"""
        # Tuned default values (half-percentage: value * 2 = percentage)
        # Low rest: 98%, 98%, 100%, 100%, 100% -> 49, 49, 50, 50, 50
        # Mid rest: 100%, 100%, 100%, 100%, 100% -> 50, 50, 50, 50, 50
        # High rest: 130%, 118%, 100%, 100%, 100% -> 65, 59, 50, 50, 50
        default_bands = [
            [49, 49, 50, 50, 50],  # Low rest
            [50, 50, 50, 50, 50],  # Mid rest (neutral)
            [65, 59, 50, 50, 50],  # High rest
        ]
        # Range scales: 110%, 100%, 106% -> 55, 50, 53
        default_scales = [55, 50, 53]

        # Block signals to avoid sending multiple updates
        for range_idx in range(3):
            for band in range(5):
                val = default_bands[range_idx][band]
                self.eq_sliders[range_idx][band].blockSignals(True)
                self.eq_sliders[range_idx][band].setValue(val)
                self.eq_labels[range_idx][band].setText(f"{val * 2}%")
                self.eq_sliders[range_idx][band].blockSignals(False)

            # Set range scale sliders
            scale_val = default_scales[range_idx]
            self.eq_range_scale_sliders[range_idx].blockSignals(True)
            self.eq_range_scale_sliders[range_idx].setValue(scale_val)
            self.eq_range_scale_labels[range_idx].setText(f"{scale_val * 2}%")
            self.eq_range_scale_sliders[range_idx].blockSignals(False)

        # Reset range boundaries to tuned values
        self.eq_range_low_slider.blockSignals(True)
        self.eq_range_low_slider.setValue(1745)
        self.eq_range_low_label.setText("1745")
        self.eq_range_low_slider.blockSignals(False)

        self.eq_range_high_slider.blockSignals(True)
        self.eq_range_high_slider.setValue(2082)
        self.eq_range_high_label.setText("2082")
        self.eq_range_high_slider.blockSignals(False)

        # Send the reset values
        self.send_eq_settings()

    def toggle_advanced_tuning(self):
        """Toggle visibility of advanced tuning widget"""
        visible = self.advanced_tuning_btn.isChecked()
        self.advanced_tuning_widget.setVisible(visible)
        if visible:
            self.advanced_tuning_btn.setText("Hide Advanced Tuning")
        else:
            self.advanced_tuning_btn.setText("Show Advanced Tuning")

    def update_distance_keys(self):
        """Update the distance_keys list and actuation_visualizers dict based on dropdown selections"""
        # Clear and rebuild
        self.distance_keys = []
        self.actuation_visualizers = {}

        for viz, row_combo, col_combo in self.visualizer_widgets:
            row = row_combo.currentData()
            col = col_combo.currentData()
            key = (row, col)
            self.distance_keys.append(key)
            self.actuation_visualizers[key] = viz

    def save_eq_to_eeprom(self):
        """Save current EQ settings to device EEPROM for persistence"""
        if not self.keyboard:
            return

        try:
            success = self.keyboard.save_eq_to_eeprom()
            if success:
                # Visual feedback could be added here (e.g., button flash)
                pass
        except (RuntimeError, ValueError, AttributeError):
            pass

    def unlock(self):
        Unlocker.unlock(self.keyboard)

    def activate(self):
        self.grabber.grabKeyboard()
        self.timer.start(20)
        # Start ADC polling at 500ms intervals (slower to avoid HID overload)
        self.adc_poll_half = 0  # Reset to first half
        self.adc_timer.start(500)
        # Start distance polling at 50ms intervals for smooth visualization
        self.distance_timer.start(50)

    def deactivate(self):
        self.grabber.releaseKeyboard()
        self.timer.stop()
        self.adc_timer.stop()
        self.distance_timer.stop()
        # Clear ADC values when leaving the matrix tester
        for w in self.KeyboardWidget2.widgets:
            w.setAdcValue(None)
        # Reset actuation visualizers
        for viz in self.actuation_visualizers.values():
            viz.set_distance(0)


class ThruLoopConfigurator(BasicEditor):

    def __init__(self):
        super().__init__()

        self.single_loopchop_label = None
        self.master_cc = None
        self.single_loopchop_widgets = []
        self.nav_widget = None

        self.setup_ui()

    def setup_ui(self):
        # Create scroll area for better window resizing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        main_widget = QWidget()
        outer_layout = QVBoxLayout()  # Outer layout for title + columns
        outer_layout.setSpacing(15)
        main_widget.setLayout(outer_layout)

        scroll_area.setWidget(main_widget)
        self.addWidget(scroll_area, 1)

        # TOP: Title and Description (centered)
        title_container = QWidget()
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_container.setLayout(title_layout)

        title_label = QLabel(tr("ThruLoopConfigurator", "ThruLoop"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_layout.addWidget(title_label)

        desc_label = QLabel(tr("ThruLoopConfigurator",
            "Configure ThruLoop MIDI looping and LoopChop navigation. "
            "Set up CC mappings for recording, playback, and loop control."))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 9pt;")
        desc_label.setAlignment(QtCore.Qt.AlignCenter)
        title_layout.addWidget(desc_label)

        outer_layout.addWidget(title_container)

        # COLUMNS: Side by side layout
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(15)
        outer_layout.addLayout(main_h_layout)

        # Left spacer for centering
        main_h_layout.addStretch(1)

        # LEFT COLUMN: Basic Settings + LoopChop (400px width)
        left_column = QVBoxLayout()
        left_column.setSpacing(8)

        # Basic Settings Group
        self.basic_group = QGroupBox(tr("ThruLoopConfigurator", "Basic Settings"))
        self.basic_group.setFixedWidth(400)
        basic_layout = QGridLayout()
        self.basic_group.setLayout(basic_layout)
        left_column.addWidget(self.basic_group)

        # ThruLoop Channel
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "ThruLoop Channel")), 0, 0)
        self.loop_channel = ArrowComboBox()
        self.loop_channel.setMinimumWidth(150)
        self.loop_channel.setMaximumHeight(30)
        self.loop_channel.setEditable(True)
        self.loop_channel.lineEdit().setReadOnly(True)
        self.loop_channel.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(1, 17):
            self.loop_channel.addItem(f"Channel {i}", i)
        self.loop_channel.setCurrentIndex(15)
        basic_layout.addWidget(self.loop_channel, 0, 1)

        # Send Restart Messages and Alternate Restart Mode (side by side)
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "Restart Settings:")), 1, 0, 1, 2)

        self.sync_midi = QCheckBox(tr("ThruLoopConfigurator", "Send Restart Messages"))
        basic_layout.addWidget(self.sync_midi, 2, 0)

        self.alternate_restart = QCheckBox(tr("ThruLoopConfigurator", "Alternate Restart Mode"))
        basic_layout.addWidget(self.alternate_restart, 2, 1)

        # Disable ThruLoop and CC Loop Recording (side by side)
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "Loop Controls:")), 3, 0, 1, 2)

        self.loop_enabled = QCheckBox(tr("ThruLoopConfigurator", "Disable ThruLoop"))
        basic_layout.addWidget(self.loop_enabled, 4, 0)

        self.cc_loop_recording = QCheckBox(tr("ThruLoopConfigurator", "CC Loop Recording"))
        basic_layout.addWidget(self.cc_loop_recording, 4, 1)

        # LoopChop Settings (below Basic Settings)
        self.loopchop_group = QGroupBox(tr("ThruLoopConfigurator", "LoopChop"))
        self.loopchop_group.setFixedWidth(400)
        loopchop_layout = QGridLayout()
        loopchop_layout.setSpacing(5)
        loopchop_layout.setContentsMargins(10, 10, 10, 10)
        self.loopchop_group.setLayout(loopchop_layout)
        left_column.addWidget(self.loopchop_group)

        # Separate CCs for LoopChop checkbox
        self.separate_loopchop = QCheckBox(tr("ThruLoopConfigurator", "Separate CCs for LoopChop"))
        loopchop_layout.addWidget(self.separate_loopchop, 0, 0, 1, 4)

        # Single LoopChop CC - Always visible
        self.single_loopchop_label = QLabel(tr("ThruLoopConfigurator", "Loop Chop"))
        loopchop_layout.addWidget(self.single_loopchop_label, 1, 0)
        self.master_cc = self.create_cc_combo(narrow=True)
        loopchop_layout.addWidget(self.master_cc, 1, 1, 1, 3, Qt.AlignLeft)

        # Individual LoopChop CCs (8 navigation CCs) - More compact layout
        nav_layout = QGridLayout()
        nav_layout.setSpacing(3)
        self.nav_combos = []
        for i in range(8):
            row = i // 4
            col = i % 4
            label = QLabel(f"{i}/8")
            label.setMaximumWidth(30)
            nav_layout.addWidget(label, row * 2, col)
            combo = self.create_cc_combo(narrow=True)
            nav_layout.addWidget(combo, row * 2 + 1, col)
            self.nav_combos.append(combo)

        self.nav_widget = QWidget()
        self.nav_widget.setLayout(nav_layout)
        loopchop_layout.addWidget(self.nav_widget, 2, 0, 1, 4)

        left_column.addStretch()
        main_h_layout.addLayout(left_column)

        # RIGHT COLUMN: Main Functions with Overdub inside (fixed 630x550)
        right_column = QVBoxLayout()
        right_column.setSpacing(8)

        self.main_group = QGroupBox(tr("ThruLoopConfigurator", "Main Functions"))
        self.main_group.setFixedWidth(630)
        self.main_group.setFixedHeight(550)
        main_group_layout = QVBoxLayout()
        main_group_layout.setSpacing(5)
        main_group_layout.setContentsMargins(10, 8, 10, 10)
        self.main_group.setLayout(main_group_layout)

        # Main Functions grid
        main_grid = QGridLayout()
        main_grid.setSpacing(5)
        main_grid.setContentsMargins(0, 0, 0, 0)

        # Add column headers
        for col in range(4):
            header = QLabel(f"Loop {col + 1}")
            header.setAlignment(QtCore.Qt.AlignCenter)
            header.setStyleSheet("font-weight: bold;")
            main_grid.addWidget(header, 0, col + 1)

        # Add function rows
        functions = ["Start Recording", "Stop Recording", "Start Playing", "Stop Playing", "Clear", "Restart"]
        self.main_combos = []
        for row_idx, func_name in enumerate(functions):
            # Row label
            label = QLabel(func_name)
            label.setStyleSheet("font-weight: bold;")
            main_grid.addWidget(label, row_idx + 1, 0)

            # Combo boxes for each loop
            row_combos = []
            for col_idx in range(4):
                combo = self.create_cc_combo(for_table=True)
                main_grid.addWidget(combo, row_idx + 1, col_idx + 1)
                row_combos.append(combo)
            self.main_combos.append(row_combos)

        main_group_layout.addLayout(main_grid)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_group_layout.addWidget(separator)

        # Overdub Functions section inside Main Functions
        overdub_grid = QGridLayout()
        overdub_grid.setSpacing(5)
        overdub_grid.setContentsMargins(0, 0, 0, 0)

        # Add column headers
        for col in range(4):
            header = QLabel(f"Overdub {col + 1}")
            header.setAlignment(QtCore.Qt.AlignCenter)
            header.setStyleSheet("font-weight: bold;")
            overdub_grid.addWidget(header, 0, col + 1)

        # Add function rows (same as main functions)
        self.overdub_combos = []
        for row_idx, func_name in enumerate(functions):
            # Row label
            label = QLabel(func_name)
            label.setStyleSheet("font-weight: bold;")
            overdub_grid.addWidget(label, row_idx + 1, 0)

            # Combo boxes for each loop
            row_combos = []
            for col_idx in range(4):
                combo = self.create_cc_combo(for_table=True)
                overdub_grid.addWidget(combo, row_idx + 1, col_idx + 1)
                row_combos.append(combo)
            self.overdub_combos.append(row_combos)

        main_group_layout.addLayout(overdub_grid)
        right_column.addWidget(self.main_group)
        right_column.addStretch()
        main_h_layout.addLayout(right_column)

        # Right spacer for centering
        main_h_layout.addStretch(1)

        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Button style - bigger and less rounded
        button_style = "QPushButton { border-radius: 3px; padding: 8px 16px; }"

        save_btn = QPushButton(tr("ThruLoopConfigurator", "Save Configuration"))
        save_btn.setMinimumHeight(45)
        save_btn.setMinimumWidth(200)
        save_btn.setStyleSheet(button_style)
        save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_btn)

        load_btn = QPushButton(tr("ThruLoopConfigurator", "Load from Keyboard"))
        load_btn.setMinimumHeight(45)
        load_btn.setMinimumWidth(210)
        load_btn.setStyleSheet(button_style)
        load_btn.clicked.connect(self.on_load_from_keyboard)
        buttons_layout.addWidget(load_btn)

        reset_btn = QPushButton(tr("ThruLoopConfigurator", "Reset to Defaults"))
        reset_btn.setMinimumHeight(45)
        reset_btn.setMinimumWidth(180)
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)

        self.addLayout(buttons_layout)
        
        # Apply stylesheet to prevent bold focus styling and center combo box text
        main_widget.setStyleSheet("""
            QCheckBox:focus {
                font-weight: normal;
                outline: none;
            }
            QPushButton:focus {
                font-weight: normal;
                outline: none;
            }
            QComboBox {
                text-align: center;
            }
            QComboBox:focus {
                font-weight: normal;
                outline: none;
            }
        """)
        
        # Connect signals AFTER all widgets are created
        self.loop_enabled.stateChanged.connect(self.on_loop_enabled_changed)
        self.separate_loopchop.stateChanged.connect(self.on_separate_loopchop_changed)
        
        # Initialize UI state AFTER all widgets and connections are set up
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
        
    def create_cc_combo(self, for_table=False, narrow=False):
        """Create a CC selector combobox

        Args:
            for_table: If True, creates a narrower combo for use in tables
            narrow: If True, creates an even narrower combo (80px max)
        """
        combo = ArrowComboBox()
        if narrow:
            # Override global stylesheet min-width and padding to allow 80px max
            combo.setStyleSheet("""
                QComboBox {
                    min-width: 0px;
                    max-width: 80px;
                    padding: 4px 6px;
                    padding-right: 20px;
                }
            """)
            combo.setMaximumWidth(80)
            combo.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        elif for_table:
            combo.setMaximumWidth(100)  # Narrower for tables to show arrow
        else:
            combo.setMinimumWidth(120)
        combo.setMaximumHeight(30)
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)

        # Add "None" option
        combo.addItem("None", 128)

        # Add CC options
        for cc_num in range(128):
            combo.addItem(f"CC# {cc_num}", cc_num)

        combo.setCurrentIndex(0)
        return combo
    
    def get_cc_value(self, combo):
        """Get the current CC value from a CC combo"""
        return combo.currentData()
    
    def set_cc_value(self, combo, value):
        """Set the CC value for a combo"""
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)
    
    def on_loop_enabled_changed(self):
        enabled = not self.loop_enabled.isChecked()
        self.main_group.setEnabled(enabled)
        self.loopchop_group.setEnabled(enabled)
    
    def on_separate_loopchop_changed(self):
        separate = self.separate_loopchop.isChecked()
        if self.single_loopchop_label:
            self.single_loopchop_label.setEnabled(not separate)
        if self.master_cc:
            self.master_cc.setEnabled(not separate)
        if self.nav_widget:
            self.nav_widget.setEnabled(separate)
    
    def get_combos_cc_values(self, combos_array):
        """Get CC values from a 2D array of combos"""
        values = []
        for row_combos in combos_array:
            for combo in row_combos:
                values.append(self.get_cc_value(combo))
        return values

    def set_combos_cc_values(self, combos_array, values):
        """Set CC values to a 2D array of combos"""
        idx = 0
        for row_combos in combos_array:
            for combo in row_combos:
                if idx < len(values):
                    self.set_cc_value(combo, values[idx])
                    idx += 1
    
    def get_restart_cc_values(self):
        """Get restart CCs from the main combos (last row)"""
        restart_values = []
        for col in range(4):
            combo = self.main_combos[5][col]  # Row 5 is "Restart"
            restart_values.append(self.get_cc_value(combo))
        return restart_values

    def set_restart_cc_values(self, values):
        """Set restart CCs in the main combos (last row)"""
        for col in range(4):
            if col < len(values):
                combo = self.main_combos[5][col]  # Row 5 is "Restart"
                self.set_cc_value(combo, values[col])
    
    def on_save(self):
        """Save all configuration to keyboard"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            # 1. Send basic loop configuration
            loop_config_data = [
                0 if self.loop_enabled.isChecked() else 1,
                self.loop_channel.currentData(),
                1 if self.sync_midi.isChecked() else 0,
                1 if self.alternate_restart.isChecked() else 0,
            ]
            # Add restart CCs from main table
            restart_values = self.get_restart_cc_values()
            loop_config_data.extend(restart_values)
            # Add CC loop recording
            loop_config_data.append(1 if self.cc_loop_recording.isChecked() else 0)
            
            if not self.device.keyboard.set_thruloop_config(loop_config_data):
                raise RuntimeError("Failed to set ThruLoop config")
            
            # 2. Send main loop CCs (excluding restart row - first 5 rows only)
            main_values = self.get_combos_cc_values(self.main_combos[:5])  # First 5 rows

            if not self.device.keyboard.set_thruloop_main_ccs(main_values):
                raise RuntimeError("Failed to set main CCs")

            # 3. Send overdub CCs (all 6 rows - 24 values total)
            overdub_values = self.get_combos_cc_values(self.overdub_combos)
            if not self.device.keyboard.set_thruloop_overdub_ccs(overdub_values):
                raise RuntimeError("Failed to set overdub CCs")
            
            # 4. Send navigation configuration
            nav_config_data = [
                1 if self.separate_loopchop.isChecked() else 0,
                self.get_cc_value(self.master_cc),
            ]
            for combo in self.nav_combos:
                nav_config_data.append(self.get_cc_value(combo))
            
            if not self.device.keyboard.set_thruloop_navigation(nav_config_data):
                raise RuntimeError("Failed to set navigation config")
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save configuration: {str(e)}")   
        
    def on_load_from_keyboard(self):
        """Load configuration from keyboard using multi-packet collection"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
                
            # Request and collect multi-packet configuration
            config = self.device.keyboard.get_thruloop_config()
            
            if not config:
                raise RuntimeError("Failed to load config from keyboard")
            
            # Apply the configuration to the UI
            self.apply_config(config)
                
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load from keyboard: {str(e)}")
    
    def apply_config(self, config):
        """Apply configuration dictionary to UI"""
        # Basic settings
        if 'loopEnabled' in config:
            self.loop_enabled.setChecked(not config.get("loopEnabled", True))
        
        if 'loopChannel' in config:
            for i in range(self.loop_channel.count()):
                if self.loop_channel.itemData(i) == config.get("loopChannel", 16):
                    self.loop_channel.setCurrentIndex(i)
                    break
        
        if 'syncMidi' in config:
            self.sync_midi.setChecked(config.get("syncMidi", False))
        if 'alternateRestart' in config:
            self.alternate_restart.setChecked(config.get("alternateRestart", False))
        if 'ccLoopRecording' in config:
            self.cc_loop_recording.setChecked(config.get("ccLoopRecording", False))
        
        # LoopChop settings
        if 'separateLoopChopCC' in config:
            self.separate_loopchop.setChecked(config.get("separateLoopChopCC", False))
        if 'masterCC' in config:
            self.set_cc_value(self.master_cc, config.get("masterCC", 128))
        
        # Set restart CCs
        if 'restartCCs' in config:
            restart_ccs = config.get("restartCCs", [128] * 4)
            self.set_restart_cc_values(restart_ccs)
        
        # Set main combos CCs (first 5 rows only)
        if 'mainCCs' in config:
            main_ccs = config.get("mainCCs", [128] * 20)
            self.set_combos_cc_values(self.main_combos[:5], main_ccs)

        # Set overdub combos CCs (all 6 rows - 24 values)
        if 'overdubCCs' in config:
            overdub_ccs = config.get("overdubCCs", [128] * 24)
            self.set_combos_cc_values(self.overdub_combos, overdub_ccs)
        
        # Set navigation CCs
        if 'navCCs' in config:
            nav_ccs = config.get("navCCs", [128] * 8)
            for i, combo in enumerate(self.nav_combos):
                if i < len(nav_ccs):
                    self.set_cc_value(combo, nav_ccs[i])
        
        # Update UI state
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
        
    def on_reset(self):
        """Reset ThruLoop configuration to defaults"""
        try:
            reply = QMessageBox.question(None, "Confirm Reset", 
                                       "Reset ThruLoop configuration to defaults? This cannot be undone.",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                if not self.device or not isinstance(self.device, VialKeyboard):
                    raise RuntimeError("Device not connected")
                    
                if not self.device.keyboard.reset_thruloop_config():
                    raise RuntimeError("Failed to reset ThruLoop config")
                    
                self.reset_ui_to_defaults()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to reset configuration: {str(e)}")
    
    def reset_ui_to_defaults(self):
        """Reset UI to default values"""
        self.loop_enabled.setChecked(False)
        self.loop_channel.setCurrentIndex(15)
        self.sync_midi.setChecked(False)
        self.alternate_restart.setChecked(False)
        self.cc_loop_recording.setChecked(False)
        self.separate_loopchop.setChecked(False)
        self.set_cc_value(self.master_cc, 128)
        
        # Reset all combos to None (128)
        for row_combos in self.main_combos:
            for combo in row_combos:
                self.set_cc_value(combo, 128)

        for row_combos in self.overdub_combos:
            for combo in row_combos:
                self.set_cc_value(combo, 128)
        
        for combo in self.nav_combos:
            self.set_cc_value(combo, 128)
        
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
    
    def get_current_config(self):
        """Get current UI configuration as dictionary"""
        config = {
            "version": "1.0",
            "loopEnabled": not self.loop_enabled.isChecked(),
            "loopChannel": self.loop_channel.currentData(), 
            "syncMidi": self.sync_midi.isChecked(),
            "alternateRestart": self.alternate_restart.isChecked(),
            "ccLoopRecording": self.cc_loop_recording.isChecked(),
            "separateLoopChopCC": self.separate_loopchop.isChecked(),
            "masterCC": self.get_cc_value(self.master_cc),
            "restartCCs": self.get_restart_cc_values(),
            "mainCCs": self.get_combos_cc_values(self.main_combos[:5]),  # First 5 rows only
            "overdubCCs": self.get_combos_cc_values(self.overdub_combos),  # All 6 rows - 24 values
            "navCCs": [self.get_cc_value(combo) for combo in self.nav_combos]
        }
        return config
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        # Load ThruLoop configuration from keyboard
        if hasattr(self.device.keyboard, 'thruloop_config') and self.device.keyboard.thruloop_config:
            self.apply_config(self.device.keyboard.thruloop_config)

class MIDIswitchSettingsConfigurator(BasicEditor):

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def create_help_label(self, tooltip_text):
        """Create a small question mark button with tooltip for help"""
        help_btn = QPushButton("?")
        help_btn.setStyleSheet("""
            QPushButton {
                color: #888;
                font-weight: bold;
                font-size: 10pt;
                border: 1px solid #888;
                border-radius: 9px;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                padding: 0px;
                margin: 0px;
                background: transparent;
            }
            QPushButton:hover {
                color: #fff;
                background-color: #555;
                border-color: #fff;
            }
        """)
        help_btn.setToolTip(tooltip_text)
        help_btn.setFocusPolicy(Qt.NoFocus)
        return help_btn

    def create_label_with_help(self, text, tooltip_text):
        """Create a horizontal layout with label and help icon"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        label = QLabel(text)
        help_icon = self.create_help_label(tooltip_text)

        layout.addWidget(help_icon)
        layout.addWidget(label)
        layout.addStretch()
        container.setLayout(layout)
        return container

    def setup_ui(self):
        # Create scroll area for better window resizing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        scroll_area.setWidget(main_widget)
        self.addWidget(scroll_area, 1)

        main_layout.addSpacing(10)

        # Global MIDI Settings Group - contains title/description on left, then base settings, keysplit, and triplesplit
        global_midi_group = QGroupBox()
        global_midi_group_layout = QHBoxLayout()
        global_midi_group_layout.setSpacing(15)
        global_midi_group.setLayout(global_midi_group_layout)

        # MIDI Settings title and description container (left side)
        midi_title_container = QWidget()
        midi_title_container.setMaximumWidth(200)
        midi_title_layout = QVBoxLayout()
        midi_title_layout.setContentsMargins(0, 0, 0, 0)
        midi_title_container.setLayout(midi_title_layout)

        title_label = QLabel(tr("MIDIswitchSettingsConfigurator", "MIDI Settings"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        title_label.setAlignment(QtCore.Qt.AlignLeft)
        midi_title_layout.addWidget(title_label)

        desc_label = QLabel(tr("MIDIswitchSettingsConfigurator",
            "Configure global MIDI settings including channel, transpose, velocity curves, "
            "sustain behavior, and aftertouch options for your keyboard."))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 9pt;")
        desc_label.setAlignment(QtCore.Qt.AlignLeft)
        midi_title_layout.addWidget(desc_label)

        midi_title_layout.addSpacing(15)

        # Buttons in the title container with popup menus
        midi_btn_style = "QPushButton { border-radius: 5px; font-size: 9pt; }"

        # Save Settings button with popup menu
        save_settings_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Save Settings"))
        save_settings_btn.setMinimumHeight(28)
        save_settings_btn.setMaximumHeight(28)
        save_settings_btn.setStyleSheet(midi_btn_style)
        save_settings_btn.setToolTip("Save current settings to a slot")

        save_menu = QMenu(save_settings_btn)
        save_menu.addAction(tr("MIDIswitchSettingsConfigurator", "Save as Default"), lambda: self.on_save_slot(0))
        save_menu.addSeparator()
        for i in range(1, 5):
            save_menu.addAction(tr("MIDIswitchSettingsConfigurator", f"Save to Slot {i}"), lambda checked=False, slot=i: self.on_save_slot(slot))
        save_settings_btn.setMenu(save_menu)
        midi_title_layout.addWidget(save_settings_btn)

        # Load Settings button with popup menu
        load_settings_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Load Settings"))
        load_settings_btn.setMinimumHeight(28)
        load_settings_btn.setMaximumHeight(28)
        load_settings_btn.setStyleSheet(midi_btn_style)
        load_settings_btn.setToolTip("Load settings from a slot")

        load_menu = QMenu(load_settings_btn)
        load_menu.addAction(tr("MIDIswitchSettingsConfigurator", "Load Default"), lambda: self.on_load_slot(0))
        load_menu.addSeparator()
        for i in range(1, 5):
            load_menu.addAction(tr("MIDIswitchSettingsConfigurator", f"Load Slot {i}"), lambda checked=False, slot=i: self.on_load_slot(slot))
        load_settings_btn.setMenu(load_menu)
        midi_title_layout.addWidget(load_settings_btn)

        # Load Active Settings button (individual)
        load_active_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Load Active Settings"))
        load_active_btn.setMinimumHeight(28)
        load_active_btn.setMaximumHeight(28)
        load_active_btn.setStyleSheet(midi_btn_style)
        load_active_btn.setToolTip("Refresh display with current keyboard settings.\nUpdates all fields to match the keyboard's active configuration.")
        load_active_btn.clicked.connect(self.on_load_current_settings)
        midi_title_layout.addWidget(load_active_btn)

        # Reset to Defaults button (individual)
        reset_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Reset to Defaults"))
        reset_btn.setMinimumHeight(28)
        reset_btn.setMaximumHeight(28)
        reset_btn.setStyleSheet(midi_btn_style)
        reset_btn.setToolTip("Reset all MIDI settings to factory defaults.\nThis cannot be undone.")
        reset_btn.clicked.connect(self.on_reset)
        midi_title_layout.addWidget(reset_btn)

        midi_title_layout.addStretch()

        # Base MIDI Settings container (limited width like keysplit)
        base_settings_container = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Base Settings"))
        base_settings_container.setMaximumWidth(300)
        base_layout = QGridLayout()
        base_layout.setVerticalSpacing(10)
        base_layout.setHorizontalSpacing(10)
        base_settings_container.setLayout(base_layout)

        row = 0

        # Channel with help
        channel_label_container = QWidget()
        channel_label_layout = QHBoxLayout()
        channel_label_layout.setContentsMargins(0, 0, 0, 0)
        channel_label_layout.setSpacing(5)
        channel_label_layout.addWidget(self.create_help_label("MIDI channel for note output (1-16)"))
        channel_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")))
        channel_label_layout.addStretch()
        channel_label_container.setLayout(channel_label_layout)
        base_layout.addWidget(channel_label_container, row, 0)

        self.global_channel = ArrowComboBox()
        self.global_channel.setMinimumWidth(80)
        self.global_channel.setMaximumWidth(120)
        self.global_channel.setMinimumHeight(25)
        self.global_channel.setMaximumHeight(25)
        for i in range(16):
            self.global_channel.addItem(f"{i + 1}", i)
        self.global_channel.setCurrentIndex(0)
        self.global_channel.setEditable(True)
        self.global_channel.lineEdit().setReadOnly(True)
        self.global_channel.lineEdit().setAlignment(Qt.AlignCenter)
        base_layout.addWidget(self.global_channel, row, 1)
        row += 1

        # Transpose with help
        transpose_label_container = QWidget()
        transpose_label_layout = QHBoxLayout()
        transpose_label_layout.setContentsMargins(0, 0, 0, 0)
        transpose_label_layout.setSpacing(5)
        transpose_label_layout.addWidget(self.create_help_label("Shift all notes up or down by semitones (-64 to +64)"))
        transpose_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")))
        transpose_label_layout.addStretch()
        transpose_label_container.setLayout(transpose_label_layout)
        base_layout.addWidget(transpose_label_container, row, 0)

        self.global_transpose = ArrowComboBox()
        self.global_transpose.setMinimumWidth(80)
        self.global_transpose.setMaximumWidth(120)
        self.global_transpose.setMinimumHeight(25)
        self.global_transpose.setMaximumHeight(25)
        for i in range(-64, 65):
            self.global_transpose.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.global_transpose.setCurrentIndex(64)
        self.global_transpose.setEditable(True)
        self.global_transpose.lineEdit().setReadOnly(True)
        self.global_transpose.lineEdit().setAlignment(Qt.AlignCenter)
        base_layout.addWidget(self.global_transpose, row, 1)
        row += 1

        # Velocity Curve with help
        velocity_curve_label_container = QWidget()
        velocity_curve_label_layout = QHBoxLayout()
        velocity_curve_label_layout.setContentsMargins(0, 0, 0, 0)
        velocity_curve_label_layout.setSpacing(5)
        velocity_curve_label_layout.addWidget(self.create_help_label(
            "How key press force maps to MIDI velocity:\n"
            "Linear: Direct 1:1 mapping\n"
            "Aggro: More sensitive at low velocities\n"
            "Slow: Less sensitive at low velocities\n"
            "Smooth: Gradual S-curve response\n"
            "Steep: Sharp response curve\n"
            "Instant: Maximum velocity always\n"
            "Turbo: Enhanced high velocity response\n"
            "User 1-10: Custom user-defined curves"
        ))
        velocity_curve_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Curve:")))
        velocity_curve_label_layout.addStretch()
        velocity_curve_label_container.setLayout(velocity_curve_label_layout)
        base_layout.addWidget(velocity_curve_label_container, row, 0)

        self.global_velocity_curve = ArrowComboBox()
        self.global_velocity_curve.setMinimumWidth(80)
        self.global_velocity_curve.setMaximumWidth(120)
        self.global_velocity_curve.setMinimumHeight(25)
        self.global_velocity_curve.setMaximumHeight(25)
        self.global_velocity_curve.addItem("Linear", 0)
        self.global_velocity_curve.addItem("Aggro", 1)
        self.global_velocity_curve.addItem("Slow", 2)
        self.global_velocity_curve.addItem("Smooth", 3)
        self.global_velocity_curve.addItem("Steep", 4)
        self.global_velocity_curve.addItem("Instant", 5)
        self.global_velocity_curve.addItem("Turbo", 6)
        for i in range(10):
            self.global_velocity_curve.addItem(f"User {i+1}", 7 + i)
        self.global_velocity_curve.setCurrentIndex(0)
        self.global_velocity_curve.setEditable(True)
        self.global_velocity_curve.lineEdit().setReadOnly(True)
        self.global_velocity_curve.lineEdit().setAlignment(Qt.AlignCenter)
        base_layout.addWidget(self.global_velocity_curve, row, 1)
        row += 1

        # Velocity Min with help
        velocity_min_label_container = QWidget()
        velocity_min_label_layout = QHBoxLayout()
        velocity_min_label_layout.setContentsMargins(0, 0, 0, 0)
        velocity_min_label_layout.setSpacing(5)
        velocity_min_label_layout.addWidget(self.create_help_label("Minimum MIDI velocity value (1-127)"))
        velocity_min_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Min:")))
        velocity_min_label_layout.addStretch()
        velocity_min_label_container.setLayout(velocity_min_label_layout)
        base_layout.addWidget(velocity_min_label_container, row, 0)

        self.global_velocity_min = QSlider(Qt.Horizontal)
        self.global_velocity_min.setMinimum(1)
        self.global_velocity_min.setMaximum(127)
        self.global_velocity_min.setValue(1)
        base_layout.addWidget(self.global_velocity_min, row, 1)
        self.velocity_min_value_label = QLabel("1")
        self.velocity_min_value_label.setMinimumWidth(30)
        self.velocity_min_value_label.setAlignment(Qt.AlignCenter)
        base_layout.addWidget(self.velocity_min_value_label, row, 2)
        self.global_velocity_min.valueChanged.connect(
            lambda v: self.velocity_min_value_label.setText(str(v))
        )
        row += 1

        # Velocity Max with help
        velocity_max_label_container = QWidget()
        velocity_max_label_layout = QHBoxLayout()
        velocity_max_label_layout.setContentsMargins(0, 0, 0, 0)
        velocity_max_label_layout.setSpacing(5)
        velocity_max_label_layout.addWidget(self.create_help_label("Maximum MIDI velocity value (1-127)"))
        velocity_max_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Max:")))
        velocity_max_label_layout.addStretch()
        velocity_max_label_container.setLayout(velocity_max_label_layout)
        base_layout.addWidget(velocity_max_label_container, row, 0)

        self.global_velocity_max = QSlider(Qt.Horizontal)
        self.global_velocity_max.setMinimum(1)
        self.global_velocity_max.setMaximum(127)
        self.global_velocity_max.setValue(127)
        base_layout.addWidget(self.global_velocity_max, row, 1)
        self.velocity_max_value_label = QLabel("127")
        self.velocity_max_value_label.setMinimumWidth(30)
        self.velocity_max_value_label.setAlignment(Qt.AlignCenter)
        base_layout.addWidget(self.velocity_max_value_label, row, 2)
        self.global_velocity_max.valueChanged.connect(
            lambda v: self.velocity_max_value_label.setText(str(v))
        )
        row += 1

        # Sustain with help
        sustain_label_container = QWidget()
        sustain_label_layout = QHBoxLayout()
        sustain_label_layout.setContentsMargins(0, 0, 0, 0)
        sustain_label_layout.setSpacing(5)
        sustain_label_layout.addWidget(self.create_help_label(
            "How the keyboard responds to sustain pedal:\n"
            "Ignore: Sustain pedal messages are ignored\n"
            "Allow: Sustain pedal affects note release"
        ))
        sustain_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sustain:")))
        sustain_label_layout.addStretch()
        sustain_label_container.setLayout(sustain_label_layout)
        base_layout.addWidget(sustain_label_container, row, 0)

        self.base_sustain = ArrowComboBox()
        self.base_sustain.setMinimumWidth(80)
        self.base_sustain.setMaximumWidth(120)
        self.base_sustain.setMinimumHeight(25)
        self.base_sustain.setMaximumHeight(25)
        self.base_sustain.addItem("Ignore", 0)
        self.base_sustain.addItem("Allow", 1)
        self.base_sustain.setCurrentIndex(0)
        self.base_sustain.setEditable(True)
        self.base_sustain.lineEdit().setReadOnly(True)
        self.base_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        base_layout.addWidget(self.base_sustain, row, 1)

        # KeySplit Settings container
        self.keysplit_offshoot = QGroupBox()
        self.keysplit_offshoot.setMaximumWidth(350)
        keysplit_layout = QGridLayout()
        keysplit_layout.setVerticalSpacing(8)
        keysplit_layout.setHorizontalSpacing(8)
        self.keysplit_offshoot.setLayout(keysplit_layout)

        ks_row = 0

        # Channel: Value dropdown | On/Off
        ch_label = QWidget()
        ch_label_layout = QHBoxLayout()
        ch_label_layout.setContentsMargins(0, 0, 0, 0)
        ch_label_layout.setSpacing(3)
        ch_label_layout.addWidget(self.create_help_label("MIDI channel (1-16) for KeySplit keys"))
        ch_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")))
        ch_label_layout.addStretch()
        ch_label.setLayout(ch_label_layout)
        keysplit_layout.addWidget(ch_label, ks_row, 0)

        self.key_split_channel = ArrowComboBox()
        self.key_split_channel.setMinimumWidth(60)
        self.key_split_channel.setMaximumWidth(80)
        self.key_split_channel.setMinimumHeight(25)
        self.key_split_channel.setMaximumHeight(25)
        for i in range(16):
            self.key_split_channel.addItem(f"{i + 1}", i)
        self.key_split_channel.setEditable(True)
        self.key_split_channel.lineEdit().setReadOnly(True)
        self.key_split_channel.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.key_split_channel, ks_row, 1)

        self.keysplit_channel_enable = ArrowComboBox()
        self.keysplit_channel_enable.setMinimumWidth(50)
        self.keysplit_channel_enable.setMaximumWidth(60)
        self.keysplit_channel_enable.setMinimumHeight(25)
        self.keysplit_channel_enable.setMaximumHeight(25)
        self.keysplit_channel_enable.addItem("Off", 0)
        self.keysplit_channel_enable.addItem("On", 1)
        self.keysplit_channel_enable.setEditable(True)
        self.keysplit_channel_enable.lineEdit().setReadOnly(True)
        self.keysplit_channel_enable.lineEdit().setAlignment(Qt.AlignCenter)
        self.keysplit_channel_enable.currentIndexChanged.connect(self._on_split_enable_changed)
        keysplit_layout.addWidget(self.keysplit_channel_enable, ks_row, 2)
        ks_row += 1

        # Transpose: Value dropdown | On/Off
        tr_label = QWidget()
        tr_label_layout = QHBoxLayout()
        tr_label_layout.setContentsMargins(0, 0, 0, 0)
        tr_label_layout.setSpacing(3)
        tr_label_layout.addWidget(self.create_help_label("Semitone offset (-64 to +64) for KeySplit keys"))
        tr_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")))
        tr_label_layout.addStretch()
        tr_label.setLayout(tr_label_layout)
        keysplit_layout.addWidget(tr_label, ks_row, 0)

        self.transpose_number2 = ArrowComboBox()
        self.transpose_number2.setMinimumWidth(60)
        self.transpose_number2.setMaximumWidth(80)
        self.transpose_number2.setMinimumHeight(25)
        self.transpose_number2.setMaximumHeight(25)
        for i in range(-64, 65):
            self.transpose_number2.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number2.setCurrentIndex(64)
        self.transpose_number2.setEditable(True)
        self.transpose_number2.lineEdit().setReadOnly(True)
        self.transpose_number2.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.transpose_number2, ks_row, 1)

        self.keysplit_transpose_enable = ArrowComboBox()
        self.keysplit_transpose_enable.setMinimumWidth(50)
        self.keysplit_transpose_enable.setMaximumWidth(60)
        self.keysplit_transpose_enable.setMinimumHeight(25)
        self.keysplit_transpose_enable.setMaximumHeight(25)
        self.keysplit_transpose_enable.addItem("Off", 0)
        self.keysplit_transpose_enable.addItem("On", 1)
        self.keysplit_transpose_enable.setEditable(True)
        self.keysplit_transpose_enable.lineEdit().setReadOnly(True)
        self.keysplit_transpose_enable.lineEdit().setAlignment(Qt.AlignCenter)
        self.keysplit_transpose_enable.currentIndexChanged.connect(self._on_split_enable_changed)
        keysplit_layout.addWidget(self.keysplit_transpose_enable, ks_row, 2)
        ks_row += 1

        # Velocity Curve: Curve dropdown | On/Off (merged)
        vc_label = QWidget()
        vc_label_layout = QHBoxLayout()
        vc_label_layout.setContentsMargins(0, 0, 0, 0)
        vc_label_layout.setSpacing(3)
        vc_label_layout.addWidget(self.create_help_label(
            "Velocity response curve for KeySplit keys:\n"
            "Linear: Direct 1:1 mapping\n"
            "Aggro: More sensitive at low velocities\n"
            "Slow: Less sensitive at low velocities\n"
            "Smooth: Gradual S-curve response\n"
            "Steep: Sharp response curve\n"
            "Instant: Maximum velocity always\n"
            "Turbo: Enhanced high velocity response"
        ))
        vc_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Curve:")))
        vc_label_layout.addStretch()
        vc_label.setLayout(vc_label_layout)
        keysplit_layout.addWidget(vc_label, ks_row, 0)

        self.velocity_curve2 = ArrowComboBox()
        self.velocity_curve2.setMinimumWidth(80)
        self.velocity_curve2.setMaximumWidth(100)
        self.velocity_curve2.setMinimumHeight(25)
        self.velocity_curve2.setMaximumHeight(25)
        self.velocity_curve2.addItem("Linear", 0)
        self.velocity_curve2.addItem("Aggro", 1)
        self.velocity_curve2.addItem("Slow", 2)
        self.velocity_curve2.addItem("Smooth", 3)
        self.velocity_curve2.addItem("Steep", 4)
        self.velocity_curve2.addItem("Instant", 5)
        self.velocity_curve2.addItem("Turbo", 6)
        for i in range(10):
            self.velocity_curve2.addItem(f"User {i+1}", 7 + i)
        self.velocity_curve2.setCurrentIndex(0)
        self.velocity_curve2.setEditable(True)
        self.velocity_curve2.lineEdit().setReadOnly(True)
        self.velocity_curve2.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.velocity_curve2, ks_row, 1)

        self.keysplit_velocity_enable = ArrowComboBox()
        self.keysplit_velocity_enable.setMinimumWidth(50)
        self.keysplit_velocity_enable.setMaximumWidth(60)
        self.keysplit_velocity_enable.setMinimumHeight(25)
        self.keysplit_velocity_enable.setMaximumHeight(25)
        self.keysplit_velocity_enable.addItem("Off", 0)
        self.keysplit_velocity_enable.addItem("On", 1)
        self.keysplit_velocity_enable.setEditable(True)
        self.keysplit_velocity_enable.lineEdit().setReadOnly(True)
        self.keysplit_velocity_enable.lineEdit().setAlignment(Qt.AlignCenter)
        self.keysplit_velocity_enable.currentIndexChanged.connect(self._on_split_enable_changed)
        keysplit_layout.addWidget(self.keysplit_velocity_enable, ks_row, 2)
        ks_row += 1

        # Velocity Min with help
        vmin_label = QWidget()
        vmin_label_layout = QHBoxLayout()
        vmin_label_layout.setContentsMargins(0, 0, 0, 0)
        vmin_label_layout.setSpacing(3)
        vmin_label_layout.addWidget(self.create_help_label("Minimum MIDI velocity (1-127) for KeySplit keys"))
        vmin_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Min:")))
        vmin_label_layout.addStretch()
        vmin_label.setLayout(vmin_label_layout)
        keysplit_layout.addWidget(vmin_label, ks_row, 0)

        self.velocity_min2 = QSlider(Qt.Horizontal)
        self.velocity_min2.setMinimum(1)
        self.velocity_min2.setMaximum(127)
        self.velocity_min2.setValue(1)
        keysplit_layout.addWidget(self.velocity_min2, ks_row, 1)
        self.velocity_min2_value = QLabel("1")
        self.velocity_min2_value.setMinimumWidth(30)
        self.velocity_min2_value.setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.velocity_min2_value, ks_row, 2)
        self.velocity_min2.valueChanged.connect(lambda v: self.velocity_min2_value.setText(str(v)))
        ks_row += 1

        # Velocity Max with help
        vmax_label = QWidget()
        vmax_label_layout = QHBoxLayout()
        vmax_label_layout.setContentsMargins(0, 0, 0, 0)
        vmax_label_layout.setSpacing(3)
        vmax_label_layout.addWidget(self.create_help_label("Maximum MIDI velocity (1-127) for KeySplit keys"))
        vmax_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Max:")))
        vmax_label_layout.addStretch()
        vmax_label.setLayout(vmax_label_layout)
        keysplit_layout.addWidget(vmax_label, ks_row, 0)

        self.velocity_max2 = QSlider(Qt.Horizontal)
        self.velocity_max2.setMinimum(1)
        self.velocity_max2.setMaximum(127)
        self.velocity_max2.setValue(127)
        keysplit_layout.addWidget(self.velocity_max2, ks_row, 1)
        self.velocity_max2_value = QLabel("127")
        self.velocity_max2_value.setMinimumWidth(30)
        self.velocity_max2_value.setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.velocity_max2_value, ks_row, 2)
        self.velocity_max2.valueChanged.connect(lambda v: self.velocity_max2_value.setText(str(v)))
        ks_row += 1

        # Sustain with help
        sus_label = QWidget()
        sus_label_layout = QHBoxLayout()
        sus_label_layout.setContentsMargins(0, 0, 0, 0)
        sus_label_layout.setSpacing(3)
        sus_label_layout.addWidget(self.create_help_label(
            "Sustain pedal behavior for KeySplit keys:\n"
            "Ignore: Sustain pedal has no effect\n"
            "Allow: Notes sustain when pedal is held"
        ))
        sus_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sustain:")))
        sus_label_layout.addStretch()
        sus_label.setLayout(sus_label_layout)
        keysplit_layout.addWidget(sus_label, ks_row, 0)

        self.keysplit_sustain = ArrowComboBox()
        self.keysplit_sustain.setMinimumWidth(80)
        self.keysplit_sustain.setMaximumWidth(120)
        self.keysplit_sustain.setMinimumHeight(25)
        self.keysplit_sustain.setMaximumHeight(25)
        self.keysplit_sustain.addItem("Ignore", 0)
        self.keysplit_sustain.addItem("Allow", 1)
        self.keysplit_sustain.setCurrentIndex(0)
        self.keysplit_sustain.setEditable(True)
        self.keysplit_sustain.lineEdit().setReadOnly(True)
        self.keysplit_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.keysplit_sustain, ks_row, 1, 1, 2)

        # TripleSplit Settings container
        self.triplesplit_offshoot = QGroupBox()
        self.triplesplit_offshoot.setMaximumWidth(350)
        triplesplit_layout = QGridLayout()
        triplesplit_layout.setVerticalSpacing(8)
        triplesplit_layout.setHorizontalSpacing(8)
        self.triplesplit_offshoot.setLayout(triplesplit_layout)

        ts_row = 0

        # Channel: Value dropdown | On/Off
        ts_ch_label = QWidget()
        ts_ch_label_layout = QHBoxLayout()
        ts_ch_label_layout.setContentsMargins(0, 0, 0, 0)
        ts_ch_label_layout.setSpacing(3)
        ts_ch_label_layout.addWidget(self.create_help_label("MIDI channel (1-16) for TripleSplit keys"))
        ts_ch_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")))
        ts_ch_label_layout.addStretch()
        ts_ch_label.setLayout(ts_ch_label_layout)
        triplesplit_layout.addWidget(ts_ch_label, ts_row, 0)

        self.key_split2_channel = ArrowComboBox()
        self.key_split2_channel.setMinimumWidth(60)
        self.key_split2_channel.setMaximumWidth(80)
        self.key_split2_channel.setMinimumHeight(25)
        self.key_split2_channel.setMaximumHeight(25)
        for i in range(16):
            self.key_split2_channel.addItem(f"{i + 1}", i)
        self.key_split2_channel.setEditable(True)
        self.key_split2_channel.lineEdit().setReadOnly(True)
        self.key_split2_channel.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.key_split2_channel, ts_row, 1)

        self.triplesplit_channel_enable = ArrowComboBox()
        self.triplesplit_channel_enable.setMinimumWidth(50)
        self.triplesplit_channel_enable.setMaximumWidth(60)
        self.triplesplit_channel_enable.setMinimumHeight(25)
        self.triplesplit_channel_enable.setMaximumHeight(25)
        self.triplesplit_channel_enable.addItem("Off", 0)
        self.triplesplit_channel_enable.addItem("On", 1)
        self.triplesplit_channel_enable.setEditable(True)
        self.triplesplit_channel_enable.lineEdit().setReadOnly(True)
        self.triplesplit_channel_enable.lineEdit().setAlignment(Qt.AlignCenter)
        self.triplesplit_channel_enable.currentIndexChanged.connect(self._on_split_enable_changed)
        triplesplit_layout.addWidget(self.triplesplit_channel_enable, ts_row, 2)
        ts_row += 1

        # Transpose: Value dropdown | On/Off
        ts_tr_label = QWidget()
        ts_tr_label_layout = QHBoxLayout()
        ts_tr_label_layout.setContentsMargins(0, 0, 0, 0)
        ts_tr_label_layout.setSpacing(3)
        ts_tr_label_layout.addWidget(self.create_help_label("Semitone offset (-64 to +64) for TripleSplit keys"))
        ts_tr_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")))
        ts_tr_label_layout.addStretch()
        ts_tr_label.setLayout(ts_tr_label_layout)
        triplesplit_layout.addWidget(ts_tr_label, ts_row, 0)

        self.transpose_number3 = ArrowComboBox()
        self.transpose_number3.setMinimumWidth(60)
        self.transpose_number3.setMaximumWidth(80)
        self.transpose_number3.setMinimumHeight(25)
        self.transpose_number3.setMaximumHeight(25)
        for i in range(-64, 65):
            self.transpose_number3.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number3.setCurrentIndex(64)
        self.transpose_number3.setEditable(True)
        self.transpose_number3.lineEdit().setReadOnly(True)
        self.transpose_number3.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.transpose_number3, ts_row, 1)

        self.triplesplit_transpose_enable = ArrowComboBox()
        self.triplesplit_transpose_enable.setMinimumWidth(50)
        self.triplesplit_transpose_enable.setMaximumWidth(60)
        self.triplesplit_transpose_enable.setMinimumHeight(25)
        self.triplesplit_transpose_enable.setMaximumHeight(25)
        self.triplesplit_transpose_enable.addItem("Off", 0)
        self.triplesplit_transpose_enable.addItem("On", 1)
        self.triplesplit_transpose_enable.setEditable(True)
        self.triplesplit_transpose_enable.lineEdit().setReadOnly(True)
        self.triplesplit_transpose_enable.lineEdit().setAlignment(Qt.AlignCenter)
        self.triplesplit_transpose_enable.currentIndexChanged.connect(self._on_split_enable_changed)
        triplesplit_layout.addWidget(self.triplesplit_transpose_enable, ts_row, 2)
        ts_row += 1

        # Velocity Curve: Curve dropdown | On/Off (merged)
        ts_vc_label = QWidget()
        ts_vc_label_layout = QHBoxLayout()
        ts_vc_label_layout.setContentsMargins(0, 0, 0, 0)
        ts_vc_label_layout.setSpacing(3)
        ts_vc_label_layout.addWidget(self.create_help_label(
            "Velocity response curve for TripleSplit keys:\n"
            "Linear: Direct 1:1 mapping\n"
            "Aggro: More sensitive at low velocities\n"
            "Slow: Less sensitive at low velocities\n"
            "Smooth: Gradual S-curve response\n"
            "Steep: Sharp response curve\n"
            "Instant: Maximum velocity always\n"
            "Turbo: Enhanced high velocity response"
        ))
        ts_vc_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Curve:")))
        ts_vc_label_layout.addStretch()
        ts_vc_label.setLayout(ts_vc_label_layout)
        triplesplit_layout.addWidget(ts_vc_label, ts_row, 0)

        self.velocity_curve3 = ArrowComboBox()
        self.velocity_curve3.setMinimumWidth(80)
        self.velocity_curve3.setMaximumWidth(100)
        self.velocity_curve3.setMinimumHeight(25)
        self.velocity_curve3.setMaximumHeight(25)
        self.velocity_curve3.addItem("Linear", 0)
        self.velocity_curve3.addItem("Aggro", 1)
        self.velocity_curve3.addItem("Slow", 2)
        self.velocity_curve3.addItem("Smooth", 3)
        self.velocity_curve3.addItem("Steep", 4)
        self.velocity_curve3.addItem("Instant", 5)
        self.velocity_curve3.addItem("Turbo", 6)
        for i in range(10):
            self.velocity_curve3.addItem(f"User {i+1}", 7 + i)
        self.velocity_curve3.setCurrentIndex(0)
        self.velocity_curve3.setEditable(True)
        self.velocity_curve3.lineEdit().setReadOnly(True)
        self.velocity_curve3.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.velocity_curve3, ts_row, 1)

        self.triplesplit_velocity_enable = ArrowComboBox()
        self.triplesplit_velocity_enable.setMinimumWidth(50)
        self.triplesplit_velocity_enable.setMaximumWidth(60)
        self.triplesplit_velocity_enable.setMinimumHeight(25)
        self.triplesplit_velocity_enable.setMaximumHeight(25)
        self.triplesplit_velocity_enable.addItem("Off", 0)
        self.triplesplit_velocity_enable.addItem("On", 1)
        self.triplesplit_velocity_enable.setEditable(True)
        self.triplesplit_velocity_enable.lineEdit().setReadOnly(True)
        self.triplesplit_velocity_enable.lineEdit().setAlignment(Qt.AlignCenter)
        self.triplesplit_velocity_enable.currentIndexChanged.connect(self._on_split_enable_changed)
        triplesplit_layout.addWidget(self.triplesplit_velocity_enable, ts_row, 2)
        ts_row += 1

        # Velocity Min with help
        ts_vmin_label = QWidget()
        ts_vmin_label_layout = QHBoxLayout()
        ts_vmin_label_layout.setContentsMargins(0, 0, 0, 0)
        ts_vmin_label_layout.setSpacing(3)
        ts_vmin_label_layout.addWidget(self.create_help_label("Minimum MIDI velocity (1-127) for TripleSplit keys"))
        ts_vmin_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Min:")))
        ts_vmin_label_layout.addStretch()
        ts_vmin_label.setLayout(ts_vmin_label_layout)
        triplesplit_layout.addWidget(ts_vmin_label, ts_row, 0)

        self.velocity_min3 = QSlider(Qt.Horizontal)
        self.velocity_min3.setMinimum(1)
        self.velocity_min3.setMaximum(127)
        self.velocity_min3.setValue(1)
        triplesplit_layout.addWidget(self.velocity_min3, ts_row, 1)
        self.velocity_min3_value = QLabel("1")
        self.velocity_min3_value.setMinimumWidth(30)
        self.velocity_min3_value.setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.velocity_min3_value, ts_row, 2)
        self.velocity_min3.valueChanged.connect(lambda v: self.velocity_min3_value.setText(str(v)))
        ts_row += 1

        # Velocity Max with help
        ts_vmax_label = QWidget()
        ts_vmax_label_layout = QHBoxLayout()
        ts_vmax_label_layout.setContentsMargins(0, 0, 0, 0)
        ts_vmax_label_layout.setSpacing(3)
        ts_vmax_label_layout.addWidget(self.create_help_label("Maximum MIDI velocity (1-127) for TripleSplit keys"))
        ts_vmax_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Max:")))
        ts_vmax_label_layout.addStretch()
        ts_vmax_label.setLayout(ts_vmax_label_layout)
        triplesplit_layout.addWidget(ts_vmax_label, ts_row, 0)

        self.velocity_max3 = QSlider(Qt.Horizontal)
        self.velocity_max3.setMinimum(1)
        self.velocity_max3.setMaximum(127)
        self.velocity_max3.setValue(127)
        triplesplit_layout.addWidget(self.velocity_max3, ts_row, 1)
        self.velocity_max3_value = QLabel("127")
        self.velocity_max3_value.setMinimumWidth(30)
        self.velocity_max3_value.setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.velocity_max3_value, ts_row, 2)
        self.velocity_max3.valueChanged.connect(lambda v: self.velocity_max3_value.setText(str(v)))
        ts_row += 1

        # Sustain with help
        ts_sus_label = QWidget()
        ts_sus_label_layout = QHBoxLayout()
        ts_sus_label_layout.setContentsMargins(0, 0, 0, 0)
        ts_sus_label_layout.setSpacing(3)
        ts_sus_label_layout.addWidget(self.create_help_label(
            "Sustain pedal behavior for TripleSplit keys:\n"
            "Ignore: Sustain pedal has no effect\n"
            "Allow: Notes sustain when pedal is held"
        ))
        ts_sus_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sustain:")))
        ts_sus_label_layout.addStretch()
        ts_sus_label.setLayout(ts_sus_label_layout)
        triplesplit_layout.addWidget(ts_sus_label, ts_row, 0)

        self.triplesplit_sustain = ArrowComboBox()
        self.triplesplit_sustain.setMinimumWidth(80)
        self.triplesplit_sustain.setMaximumWidth(120)
        self.triplesplit_sustain.setMinimumHeight(25)
        self.triplesplit_sustain.setMaximumHeight(25)
        self.triplesplit_sustain.addItem("Ignore", 0)
        self.triplesplit_sustain.addItem("Allow", 1)
        self.triplesplit_sustain.setCurrentIndex(0)
        self.triplesplit_sustain.setEditable(True)
        self.triplesplit_sustain.lineEdit().setReadOnly(True)
        self.triplesplit_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.triplesplit_sustain, ts_row, 1, 1, 2)

        # Create wrapper for keysplit with title above
        keysplit_wrapper = QWidget()
        keysplit_wrapper_layout = QVBoxLayout()
        keysplit_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        keysplit_wrapper_layout.setSpacing(5)
        keysplit_wrapper.setLayout(keysplit_wrapper_layout)

        # KeySplit title with help icon (above container)
        ks_header = QWidget()
        ks_header_layout = QHBoxLayout()
        ks_header_layout.setContentsMargins(0, 0, 0, 0)
        ks_header_layout.setSpacing(5)
        ks_header_title = QLabel(tr("MIDIswitchSettingsConfigurator", "KeySplit Settings"))
        ks_header_title.setStyleSheet("font-weight: bold;")
        ks_header_layout.addWidget(self.create_help_label(
            "KeySplit allows keys assigned to the KeySplit layer to use\n"
            "different MIDI settings than the base layer.\n\n"
            "Enable each parameter to apply separate settings for split keys."
        ))
        ks_header_layout.addWidget(ks_header_title)
        ks_header_layout.addStretch()
        ks_header.setLayout(ks_header_layout)
        keysplit_wrapper_layout.addWidget(ks_header)
        keysplit_wrapper_layout.addWidget(self.keysplit_offshoot)

        # Create wrapper for triplesplit with title above
        triplesplit_wrapper = QWidget()
        triplesplit_wrapper_layout = QVBoxLayout()
        triplesplit_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        triplesplit_wrapper_layout.setSpacing(5)
        triplesplit_wrapper.setLayout(triplesplit_wrapper_layout)

        # TripleSplit title with help icon (above container)
        ts_header = QWidget()
        ts_header_layout = QHBoxLayout()
        ts_header_layout.setContentsMargins(0, 0, 0, 0)
        ts_header_layout.setSpacing(5)
        ts_header_title = QLabel(tr("MIDIswitchSettingsConfigurator", "TripleSplit Settings"))
        ts_header_title.setStyleSheet("font-weight: bold;")
        ts_header_layout.addWidget(self.create_help_label(
            "TripleSplit allows keys assigned to the TripleSplit layer to use\n"
            "different MIDI settings than both base and KeySplit layers.\n\n"
            "Enable each parameter to apply separate settings for third split keys."
        ))
        ts_header_layout.addWidget(ts_header_title)
        ts_header_layout.addStretch()
        ts_header.setLayout(ts_header_layout)
        triplesplit_wrapper_layout.addWidget(ts_header)
        triplesplit_wrapper_layout.addWidget(self.triplesplit_offshoot)

        # Add all containers to the horizontal layout
        global_midi_group_layout.addWidget(midi_title_container)
        global_midi_group_layout.addStretch()
        global_midi_group_layout.addWidget(base_settings_container)
        global_midi_group_layout.addWidget(keysplit_wrapper)
        global_midi_group_layout.addWidget(triplesplit_wrapper)
        global_midi_group_layout.addStretch()

        # Add global MIDI group to main layout
        main_layout.addWidget(global_midi_group)

        # Loop Settings Group with title on left, container centered
        loop_row_container = QWidget()
        loop_row_layout = QHBoxLayout()
        loop_row_layout.setContentsMargins(0, 0, 0, 0)
        loop_row_container.setLayout(loop_row_layout)

        # Loop title container (left of centered container, vertically centered)
        loop_title_widget = QWidget()
        loop_title_widget.setFixedWidth(150)
        loop_title_layout = QVBoxLayout()
        loop_title_layout.setContentsMargins(0, 0, 0, 0)
        loop_title_widget.setLayout(loop_title_layout)

        loop_title_layout.addStretch()
        loop_title_label = QLabel(tr("MIDIswitchSettingsConfigurator", "Loop Settings"))
        loop_title_layout.addWidget(loop_title_label)
        loop_title_layout.addStretch()

        loop_group = QGroupBox()
        loop_layout = QGridLayout()
        loop_group.setLayout(loop_layout)
        loop_layout.setHorizontalSpacing(25)

        loop_row_layout.addStretch()
        loop_row_layout.addWidget(loop_title_widget)
        loop_row_layout.addWidget(loop_group)
        loop_row_layout.addStretch()
        main_layout.addWidget(loop_row_container)

        # Sync Mode with help
        sync_mode_label = QWidget()
        sync_mode_layout = QHBoxLayout()
        sync_mode_layout.setContentsMargins(0, 0, 0, 0)
        sync_mode_layout.setSpacing(5)
        sync_mode_layout.addWidget(self.create_help_label(
            "Loop: Free-running loop mode\n"
            "Sync Mode: Synced to external clock\n"
            "BPM Bar/Beat: Sync to BPM timing\n"
            "Note Prime On/Off: Whether notes prime the loop"
        ))
        sync_mode_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sync Mode:")))
        sync_mode_label.setLayout(sync_mode_layout)
        loop_layout.addWidget(sync_mode_label, 0, 1)
        self.unsynced_mode = ArrowComboBox()
        self.unsynced_mode.setMinimumWidth(120)
        self.unsynced_mode.setMinimumHeight(25)
        self.unsynced_mode.setMaximumHeight(25)
        self.unsynced_mode.setEditable(True)
        self.unsynced_mode.lineEdit().setReadOnly(True)
        self.unsynced_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.unsynced_mode.addItem("Loop (Note Prime On)", 0)
        self.unsynced_mode.addItem("Loop (Note Prime Off)", 4)
        self.unsynced_mode.addItem("Sync Mode (Note Prime On)", 2)
        self.unsynced_mode.addItem("Sync Mode (Note Prime Off)", 5)
        self.unsynced_mode.addItem("BPM Bar", 1)
        self.unsynced_mode.addItem("BPM Beat", 3)
        loop_layout.addWidget(self.unsynced_mode, 0, 2)

        # Sample Mode with help
        sample_mode_label = QWidget()
        sample_mode_label_layout = QHBoxLayout()
        sample_mode_label_layout.setContentsMargins(0, 0, 0, 0)
        sample_mode_label_layout.setSpacing(5)
        sample_mode_label_layout.addWidget(self.create_help_label(
            "Enable one-shot sample playback mode.\n"
            "Off: Normal loop behavior\n"
            "On: Loops play once and stop"
        ))
        sample_mode_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sample Mode:")))
        sample_mode_label.setLayout(sample_mode_label_layout)
        loop_layout.addWidget(sample_mode_label, 0, 3)
        self.sample_mode = ArrowComboBox()
        self.sample_mode.setMinimumWidth(120)
        self.sample_mode.setMinimumHeight(25)
        self.sample_mode.setMaximumHeight(25)
        self.sample_mode.setEditable(True)
        self.sample_mode.lineEdit().setReadOnly(True)
        self.sample_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.sample_mode.addItem("Off", False)
        self.sample_mode.addItem("On", True)
        loop_layout.addWidget(self.sample_mode, 0, 4)

        # Loop Messaging with help
        thruloop_label = QWidget()
        thruloop_label_layout = QHBoxLayout()
        thruloop_label_layout.setContentsMargins(0, 0, 0, 0)
        thruloop_label_layout.setSpacing(5)
        thruloop_label_layout.addWidget(self.create_help_label(
            "Pass MIDI messages through the looper.\n"
            "Off: MIDI is not passed through\n"
            "On: MIDI messages are forwarded"
        ))
        thruloop_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop:")))
        thruloop_label.setLayout(thruloop_label_layout)
        loop_layout.addWidget(thruloop_label, 1, 1)
        self.loop_messaging_enabled = ArrowComboBox()
        self.loop_messaging_enabled.setMinimumWidth(120)
        self.loop_messaging_enabled.setMinimumHeight(25)
        self.loop_messaging_enabled.setMaximumHeight(25)
        self.loop_messaging_enabled.setEditable(True)
        self.loop_messaging_enabled.lineEdit().setReadOnly(True)
        self.loop_messaging_enabled.lineEdit().setAlignment(Qt.AlignCenter)
        self.loop_messaging_enabled.addItem("Off", False)
        self.loop_messaging_enabled.addItem("On", True)
        loop_layout.addWidget(self.loop_messaging_enabled, 1, 2)

        # Messaging Channel with help
        thruloop_ch_label = QWidget()
        thruloop_ch_label_layout = QHBoxLayout()
        thruloop_ch_label_layout.setContentsMargins(0, 0, 0, 0)
        thruloop_ch_label_layout.setSpacing(5)
        thruloop_ch_label_layout.addWidget(self.create_help_label(
            "MIDI channel (1-16) used for ThruLoop messages.\n"
            "ThruLoop messages will be sent on this channel."
        ))
        thruloop_ch_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop Channel:")))
        thruloop_ch_label.setLayout(thruloop_ch_label_layout)
        loop_layout.addWidget(thruloop_ch_label, 1, 3)
        self.loop_messaging_channel = ArrowComboBox()
        self.loop_messaging_channel.setMinimumWidth(120)
        self.loop_messaging_channel.setMinimumHeight(25)
        self.loop_messaging_channel.setMaximumHeight(25)
        self.loop_messaging_channel.setEditable(True)
        self.loop_messaging_channel.lineEdit().setReadOnly(True)
        self.loop_messaging_channel.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(1, 17):
            self.loop_messaging_channel.addItem(str(i), i)
        self.loop_messaging_channel.setCurrentIndex(15)
        loop_layout.addWidget(self.loop_messaging_channel, 1, 4)

        # Sync MIDI Mode with help
        restart_msg_label = QWidget()
        restart_msg_label_layout = QHBoxLayout()
        restart_msg_label_layout.setContentsMargins(0, 0, 0, 0)
        restart_msg_label_layout.setSpacing(5)
        restart_msg_label_layout.addWidget(self.create_help_label(
            "Send restart messages when loop restarts.\n"
            "Off: No restart messages sent\n"
            "On: Send restart messages to external devices"
        ))
        restart_msg_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "ThruLoop Restart Messaging:")))
        restart_msg_label.setLayout(restart_msg_label_layout)
        loop_layout.addWidget(restart_msg_label, 2, 1)
        self.sync_midi_mode = ArrowComboBox()
        self.sync_midi_mode.setMinimumWidth(120)
        self.sync_midi_mode.setMinimumHeight(25)
        self.sync_midi_mode.setMaximumHeight(25)
        self.sync_midi_mode.setEditable(True)
        self.sync_midi_mode.lineEdit().setReadOnly(True)
        self.sync_midi_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.sync_midi_mode.addItem("Off", False)
        self.sync_midi_mode.addItem("On", True)
        loop_layout.addWidget(self.sync_midi_mode, 2, 2)

        # Restart Mode with help
        restart_mode_label = QWidget()
        restart_mode_label_layout = QHBoxLayout()
        restart_mode_label_layout.setContentsMargins(0, 0, 0, 0)
        restart_mode_label_layout.setSpacing(5)
        restart_mode_label_layout.addWidget(self.create_help_label(
            "How to signal loop restart to external devices.\n"
            "Restart CC: Send a CC message to restart\n"
            "Stop+Start: Send stop then start messages"
        ))
        restart_mode_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Thruloop Restart Mode:")))
        restart_mode_label.setLayout(restart_mode_label_layout)
        loop_layout.addWidget(restart_mode_label, 2, 3)
        self.alternate_restart_mode = ArrowComboBox()
        self.alternate_restart_mode.setMinimumWidth(120)
        self.alternate_restart_mode.setMinimumHeight(25)
        self.alternate_restart_mode.setMaximumHeight(25)
        self.alternate_restart_mode.setEditable(True)
        self.alternate_restart_mode.lineEdit().setReadOnly(True)
        self.alternate_restart_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.alternate_restart_mode.addItem("Restart CC", False)
        self.alternate_restart_mode.addItem("Stop+Start", True)
        loop_layout.addWidget(self.alternate_restart_mode, 2, 4)

        # Overdub Mode with help
        overdub_label = QWidget()
        overdub_label_layout = QHBoxLayout()
        overdub_label_layout.setContentsMargins(0, 0, 0, 0)
        overdub_label_layout.setSpacing(5)
        overdub_label_layout.addWidget(self.create_help_label(
            "Loop overdub behavior mode.\n"
            "Default: Standard overdub behavior\n"
            "8 Track Looper: Optimized for 8-track looper workflow"
        ))
        overdub_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Overdub Mode:")))
        overdub_label.setLayout(overdub_label_layout)
        loop_layout.addWidget(overdub_label, 3, 1)
        self.smart_chord_light = ArrowComboBox()
        self.smart_chord_light.setMinimumWidth(120)
        self.smart_chord_light.setMinimumHeight(25)
        self.smart_chord_light.setMaximumHeight(25)
        self.smart_chord_light.setEditable(True)
        self.smart_chord_light.lineEdit().setReadOnly(True)
        self.smart_chord_light.lineEdit().setAlignment(Qt.AlignCenter)
        self.smart_chord_light.addItem("Default", 0)
        self.smart_chord_light.addItem("8 Track Looper", 1)
        loop_layout.addWidget(self.smart_chord_light, 3, 2)

        # Advanced Settings Group with title on left, container centered
        advanced_row_container = QWidget()
        advanced_row_layout = QHBoxLayout()
        advanced_row_layout.setContentsMargins(0, 0, 0, 0)
        advanced_row_container.setLayout(advanced_row_layout)

        # Advanced title container (left of centered container, vertically centered)
        advanced_title_widget = QWidget()
        advanced_title_widget.setFixedWidth(150)
        advanced_title_layout = QVBoxLayout()
        advanced_title_layout.setContentsMargins(0, 0, 0, 0)
        advanced_title_widget.setLayout(advanced_title_layout)

        advanced_title_layout.addStretch()
        advanced_title_label = QLabel(tr("MIDIswitchSettingsConfigurator", "Advanced Settings"))
        advanced_title_layout.addWidget(advanced_title_label)
        advanced_title_layout.addStretch()

        advanced_group = QGroupBox()
        advanced_layout = QGridLayout()
        advanced_layout.setHorizontalSpacing(25)
        advanced_group.setLayout(advanced_layout)

        advanced_row_layout.addStretch()
        advanced_row_layout.addWidget(advanced_title_widget)
        advanced_row_layout.addWidget(advanced_group)
        advanced_row_layout.addStretch()

        # Velocity Interval with help
        vel_interval_label = QWidget()
        vel_interval_label_layout = QHBoxLayout()
        vel_interval_label_layout.setContentsMargins(0, 0, 0, 0)
        vel_interval_label_layout.setSpacing(5)
        vel_interval_label_layout.addWidget(self.create_help_label(
            "Velocity step amount (1-10).\n"
            "When using velocity +/- keys, this is the\n"
            "amount velocity will increase or decrease."
        ))
        vel_interval_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Interval:")))
        vel_interval_label.setLayout(vel_interval_label_layout)
        advanced_layout.addWidget(vel_interval_label, 0, 1)
        self.velocity_sensitivity = ArrowComboBox()
        self.velocity_sensitivity.setMinimumWidth(120)
        self.velocity_sensitivity.setMinimumHeight(25)
        self.velocity_sensitivity.setMaximumHeight(25)
        self.velocity_sensitivity.setEditable(True)
        self.velocity_sensitivity.lineEdit().setReadOnly(True)
        self.velocity_sensitivity.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(1, 11):
            self.velocity_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.velocity_sensitivity, 0, 2)

        # CC Interval with help
        cc_interval_label = QWidget()
        cc_interval_label_layout = QHBoxLayout()
        cc_interval_label_layout.setContentsMargins(0, 0, 0, 0)
        cc_interval_label_layout.setSpacing(5)
        cc_interval_label_layout.addWidget(self.create_help_label(
            "CC step amount (1-16).\n"
            "When using CC +/- keys, this is the\n"
            "amount the CC value will increase or decrease."
        ))
        cc_interval_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Interval:")))
        cc_interval_label.setLayout(cc_interval_label_layout)
        advanced_layout.addWidget(cc_interval_label, 0, 3)
        self.cc_sensitivity = ArrowComboBox()
        self.cc_sensitivity.setMinimumWidth(120)
        self.cc_sensitivity.setMinimumHeight(25)
        self.cc_sensitivity.setMaximumHeight(25)
        self.cc_sensitivity.setEditable(True)
        self.cc_sensitivity.lineEdit().setReadOnly(True)
        self.cc_sensitivity.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(1, 17):
            self.cc_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.cc_sensitivity, 0, 4)

        # Dynamic Range with help
        dynamic_range_label = QWidget()
        dynamic_range_label_layout = QHBoxLayout()
        dynamic_range_label_layout.setContentsMargins(0, 0, 0, 0)
        dynamic_range_label_layout.setSpacing(5)
        dynamic_range_label_layout.addWidget(self.create_help_label(
            "Random velocity variation amount (0-127).\n"
            "Adds human-like variation to velocity values.\n"
            "0 = No variation, higher = more randomness."
        ))
        dynamic_range_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Dynamic Range:")))
        dynamic_range_label.setLayout(dynamic_range_label_layout)
        advanced_layout.addWidget(dynamic_range_label, 1, 1)
        self.random_velocity_modifier = ArrowComboBox()
        self.random_velocity_modifier.setMinimumWidth(120)
        self.random_velocity_modifier.setMinimumHeight(25)
        self.random_velocity_modifier.setMaximumHeight(25)
        self.random_velocity_modifier.setEditable(True)
        self.random_velocity_modifier.lineEdit().setReadOnly(True)
        self.random_velocity_modifier.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(128):
            self.random_velocity_modifier.addItem(str(i), i)
        advanced_layout.addWidget(self.random_velocity_modifier, 1, 2)

        # OLED Keyboard with help
        oled_label = QWidget()
        oled_label_layout = QHBoxLayout()
        oled_label_layout.setContentsMargins(0, 0, 0, 0)
        oled_label_layout.setSpacing(5)
        oled_label_layout.addWidget(self.create_help_label(
            "OLED display keyboard visualization style.\n"
            "Style 1: Standard keyboard display\n"
            "Style 2: Alternative keyboard layout"
        ))
        oled_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "OLED Keyboard:")))
        oled_label.setLayout(oled_label_layout)
        advanced_layout.addWidget(oled_label, 1, 3)
        self.oled_keyboard = ArrowComboBox()
        self.oled_keyboard.setMinimumWidth(120)
        self.oled_keyboard.setMinimumHeight(25)
        self.oled_keyboard.setMaximumHeight(25)
        self.oled_keyboard.setEditable(True)
        self.oled_keyboard.lineEdit().setReadOnly(True)
        self.oled_keyboard.lineEdit().setAlignment(Qt.AlignCenter)
        self.oled_keyboard.addItem("Style 1", 0)
        self.oled_keyboard.addItem("Style 2", 12)
        advanced_layout.addWidget(self.oled_keyboard, 1, 4)

        # SC Light Mode with help
        guide_lights_label = QWidget()
        guide_lights_label_layout = QHBoxLayout()
        guide_lights_label_layout.setContentsMargins(0, 0, 0, 0)
        guide_lights_label_layout.setSpacing(5)
        guide_lights_label_layout.addWidget(self.create_help_label(
            "SmartChord guide light behavior.\n"
            "All Off: No guide lights\n"
            "SmartChord Off: Guide lights off for SmartChord\n"
            "All On: Dynamic: Lights follow chord changes\n"
            "Guitar EADGB/ADGBE: Guitar string tuning layouts"
        ))
        guide_lights_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Guide Lights:")))
        guide_lights_label.setLayout(guide_lights_label_layout)
        advanced_layout.addWidget(guide_lights_label, 2, 1)
        self.smart_chord_light_mode = ArrowComboBox()
        self.smart_chord_light_mode.setMinimumWidth(120)
        self.smart_chord_light_mode.setMinimumHeight(25)
        self.smart_chord_light_mode.setMaximumHeight(25)
        self.smart_chord_light_mode.setEditable(True)
        self.smart_chord_light_mode.lineEdit().setReadOnly(True)
        self.smart_chord_light_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.smart_chord_light_mode.addItem("All Off", 1)
        self.smart_chord_light_mode.addItem("SmartChord Off", 2)
        self.smart_chord_light_mode.addItem("All On: Dynamic", 0)
        self.smart_chord_light_mode.addItem("All on: Guitar EADGB", 3)
        self.smart_chord_light_mode.addItem("All on: Guitar ADGBE", 4)
        advanced_layout.addWidget(self.smart_chord_light_mode, 2, 2)

        # Colorblind Mode with help
        colorblind_label = QWidget()
        colorblind_label_layout = QHBoxLayout()
        colorblind_label_layout.setContentsMargins(0, 0, 0, 0)
        colorblind_label_layout.setSpacing(5)
        colorblind_label_layout.addWidget(self.create_help_label(
            "Enable colorblind-friendly LED colors.\n"
            "Off: Standard color scheme\n"
            "On: High-contrast colors for better visibility"
        ))
        colorblind_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Colorblind Mode:")))
        colorblind_label.setLayout(colorblind_label_layout)
        advanced_layout.addWidget(colorblind_label, 2, 3)
        self.colorblind_mode = ArrowComboBox()
        self.colorblind_mode.setMinimumWidth(120)
        self.colorblind_mode.setMinimumHeight(25)
        self.colorblind_mode.setMaximumHeight(25)
        self.colorblind_mode.setEditable(True)
        self.colorblind_mode.lineEdit().setReadOnly(True)
        self.colorblind_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.colorblind_mode.addItem("Off", 0)
        self.colorblind_mode.addItem("On", 1)
        advanced_layout.addWidget(self.colorblind_mode, 2, 4)

        # RGB Layer Mode with help
        rgb_layer_label = QWidget()
        rgb_layer_label_layout = QHBoxLayout()
        rgb_layer_label_layout.setContentsMargins(0, 0, 0, 0)
        rgb_layer_label_layout.setSpacing(5)
        rgb_layer_label_layout.addWidget(self.create_help_label(
            "Enable custom RGB animations per layer.\n"
            "Off: Use global RGB settings\n"
            "On: Each layer can have unique RGB animations"
        ))
        rgb_layer_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "RGB Layer Mode:")))
        rgb_layer_label.setLayout(rgb_layer_label_layout)
        advanced_layout.addWidget(rgb_layer_label, 3, 1)
        self.custom_layer_animations = ArrowComboBox()
        self.custom_layer_animations.setMinimumWidth(120)
        self.custom_layer_animations.setMinimumHeight(25)
        self.custom_layer_animations.setMaximumHeight(25)
        self.custom_layer_animations.setEditable(True)
        self.custom_layer_animations.lineEdit().setReadOnly(True)
        self.custom_layer_animations.lineEdit().setAlignment(Qt.AlignCenter)
        self.custom_layer_animations.addItem("Off", False)
        self.custom_layer_animations.addItem("On", True)
        advanced_layout.addWidget(self.custom_layer_animations, 3, 2)

        # CC Loop Recording with help
        cc_loop_label = QWidget()
        cc_loop_label_layout = QHBoxLayout()
        cc_loop_label_layout.setContentsMargins(0, 0, 0, 0)
        cc_loop_label_layout.setSpacing(5)
        cc_loop_label_layout.addWidget(self.create_help_label(
            "Record Control Change messages in loops.\n"
            "Off: Only record note events\n"
            "On: Record CC messages alongside notes"
        ))
        cc_loop_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Loop Recording:")))
        cc_loop_label.setLayout(cc_loop_label_layout)
        advanced_layout.addWidget(cc_loop_label, 3, 3)
        self.cc_loop_recording = ArrowComboBox()
        self.cc_loop_recording.setMinimumWidth(120)
        self.cc_loop_recording.setMinimumHeight(25)
        self.cc_loop_recording.setMaximumHeight(25)
        self.cc_loop_recording.setEditable(True)
        self.cc_loop_recording.lineEdit().setReadOnly(True)
        self.cc_loop_recording.lineEdit().setAlignment(Qt.AlignCenter)
        self.cc_loop_recording.addItem("Off", False)
        self.cc_loop_recording.addItem("On", True)
        advanced_layout.addWidget(self.cc_loop_recording, 3, 4)

        # True Sustain with help
        true_sustain_label = QWidget()
        true_sustain_label_layout = QHBoxLayout()
        true_sustain_label_layout.setContentsMargins(0, 0, 0, 0)
        true_sustain_label_layout.setSpacing(5)
        true_sustain_label_layout.addWidget(self.create_help_label(
            "Enable true sustain pedal behavior.\n"
            "Off: Standard sustain behavior\n"
            "On: More realistic piano-style sustain"
        ))
        true_sustain_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "True Sustain:")))
        true_sustain_label.setLayout(true_sustain_label_layout)
        advanced_layout.addWidget(true_sustain_label, 4, 1)
        self.true_sustain = ArrowComboBox()
        self.true_sustain.setMinimumWidth(120)
        self.true_sustain.setMinimumHeight(25)
        self.true_sustain.setMaximumHeight(25)
        self.true_sustain.setEditable(True)
        self.true_sustain.lineEdit().setReadOnly(True)
        self.true_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        self.true_sustain.addItem("Off", False)
        self.true_sustain.addItem("On", True)
        advanced_layout.addWidget(self.true_sustain, 4, 2)

        # Aftertouch is now per-layer (configured in Layer Actuation section)
        aftertouch_note = QLabel(tr("MIDIswitchSettingsConfigurator", "Aftertouch: Per-Layer"))
        aftertouch_note.setStyleSheet("QLabel { color: #888; font-style: italic; }")
        aftertouch_note.setToolTip(
            "Aftertouch settings are configured per-layer.\n"
            "Go to the Layer Actuation section to configure\n"
            "aftertouch mode and CC number for each layer."
        )
        advanced_layout.addWidget(aftertouch_note, 4, 3, 1, 2)  # Spans cols 3-4

        # MIDI Routing Settings Group with title on left, container centered
        routing_row_container = QWidget()
        routing_row_layout = QHBoxLayout()
        routing_row_layout.setContentsMargins(0, 0, 0, 0)
        routing_row_container.setLayout(routing_row_layout)

        # Routing title container (left of centered container, vertically centered)
        routing_title_widget = QWidget()
        routing_title_widget.setFixedWidth(150)
        routing_title_layout = QVBoxLayout()
        routing_title_layout.setContentsMargins(0, 0, 0, 0)
        routing_title_widget.setLayout(routing_title_layout)

        routing_title_layout.addStretch()
        routing_title_label = QLabel(tr("MIDIswitchSettingsConfigurator", "MIDI Routing"))
        routing_title_layout.addWidget(routing_title_label)
        routing_title_layout.addStretch()

        midi_routing_group = QGroupBox()
        midi_routing_layout = QGridLayout()
        midi_routing_layout.setHorizontalSpacing(25)
        midi_routing_group.setLayout(midi_routing_layout)

        routing_row_layout.addStretch()
        routing_row_layout.addWidget(routing_title_widget)
        routing_row_layout.addWidget(midi_routing_group)
        routing_row_layout.addStretch()

        # Row 0: Override settings with help icons
        ch_override_label = QWidget()
        ch_override_layout = QHBoxLayout()
        ch_override_layout.setContentsMargins(0, 0, 0, 0)
        ch_override_layout.setSpacing(5)
        ch_override_layout.addWidget(self.create_help_label("Override channel for incoming MIDI"))
        ch_override_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel Override:")))
        ch_override_label.setLayout(ch_override_layout)
        midi_routing_layout.addWidget(ch_override_label, 0, 1)
        self.channel_override = ArrowComboBox()
        self.channel_override.setMinimumWidth(80)
        self.channel_override.setMinimumHeight(25)
        self.channel_override.setMaximumHeight(25)
        self.channel_override.setEditable(True)
        self.channel_override.lineEdit().setReadOnly(True)
        self.channel_override.lineEdit().setAlignment(Qt.AlignCenter)
        self.channel_override.addItem("Off", False)
        self.channel_override.addItem("On", True)
        midi_routing_layout.addWidget(self.channel_override, 0, 2)

        vel_override_label = QWidget()
        vel_override_label_layout = QHBoxLayout()
        vel_override_label_layout.setContentsMargins(0, 0, 0, 0)
        vel_override_label_layout.setSpacing(5)
        vel_override_label_layout.addWidget(self.create_help_label(
            "Override velocity for incoming MIDI notes.\n"
            "Off: Use incoming velocity values\n"
            "On: Apply keyboard velocity settings to input"
        ))
        vel_override_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Override:")))
        vel_override_label.setLayout(vel_override_label_layout)
        midi_routing_layout.addWidget(vel_override_label, 0, 3)
        self.velocity_override = ArrowComboBox()
        self.velocity_override.setMinimumWidth(80)
        self.velocity_override.setMinimumHeight(25)
        self.velocity_override.setMaximumHeight(25)
        self.velocity_override.setEditable(True)
        self.velocity_override.lineEdit().setReadOnly(True)
        self.velocity_override.lineEdit().setAlignment(Qt.AlignCenter)
        self.velocity_override.addItem("Off", False)
        self.velocity_override.addItem("On", True)
        midi_routing_layout.addWidget(self.velocity_override, 0, 4)

        trans_override_label = QWidget()
        trans_override_label_layout = QHBoxLayout()
        trans_override_label_layout.setContentsMargins(0, 0, 0, 0)
        trans_override_label_layout.setSpacing(5)
        trans_override_label_layout.addWidget(self.create_help_label(
            "Override transpose for incoming MIDI notes.\n"
            "Off: Use incoming note values\n"
            "On: Apply keyboard transpose settings to input"
        ))
        trans_override_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose Override:")))
        trans_override_label.setLayout(trans_override_label_layout)
        midi_routing_layout.addWidget(trans_override_label, 0, 5)
        self.transpose_override = ArrowComboBox()
        self.transpose_override.setMinimumWidth(80)
        self.transpose_override.setMinimumHeight(25)
        self.transpose_override.setMaximumHeight(25)
        self.transpose_override.setEditable(True)
        self.transpose_override.lineEdit().setReadOnly(True)
        self.transpose_override.lineEdit().setAlignment(Qt.AlignCenter)
        self.transpose_override.addItem("Off", False)
        self.transpose_override.addItem("On", True)
        midi_routing_layout.addWidget(self.transpose_override, 0, 6)

        # Row 1: MIDI routing modes with help
        midi_in_label = QWidget()
        midi_in_label_layout = QHBoxLayout()
        midi_in_label_layout.setContentsMargins(0, 0, 0, 0)
        midi_in_label_layout.setSpacing(5)
        midi_in_label_layout.addWidget(self.create_help_label(
            "How incoming MIDI from DIN port is processed.\n"
            "Process All: Process all incoming MIDI\n"
            "Thru: Pass MIDI through unchanged\n"
            "Clock Only: Only process clock messages\n"
            "Ignore: Ignore all incoming MIDI"
        ))
        midi_in_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "MIDI IN Mode:")))
        midi_in_label.setLayout(midi_in_label_layout)
        midi_routing_layout.addWidget(midi_in_label, 1, 1)
        self.midi_in_mode = ArrowComboBox()
        self.midi_in_mode.setMinimumWidth(120)
        self.midi_in_mode.setMinimumHeight(25)
        self.midi_in_mode.setMaximumHeight(25)
        self.midi_in_mode.setEditable(True)
        self.midi_in_mode.lineEdit().setReadOnly(True)
        self.midi_in_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.midi_in_mode.addItem("Process All", 0)
        self.midi_in_mode.addItem("Thru", 1)
        self.midi_in_mode.addItem("Clock Only", 2)
        self.midi_in_mode.addItem("Ignore", 3)
        midi_routing_layout.addWidget(self.midi_in_mode, 1, 2)

        usb_midi_label = QWidget()
        usb_midi_label_layout = QHBoxLayout()
        usb_midi_label_layout.setContentsMargins(0, 0, 0, 0)
        usb_midi_label_layout.setSpacing(5)
        usb_midi_label_layout.addWidget(self.create_help_label(
            "How incoming USB MIDI is processed.\n"
            "Process All: Process all incoming MIDI\n"
            "Thru: Pass MIDI through unchanged\n"
            "Clock Only: Only process clock messages\n"
            "Ignore: Ignore all incoming USB MIDI"
        ))
        usb_midi_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "USB MIDI Mode:")))
        usb_midi_label.setLayout(usb_midi_label_layout)
        midi_routing_layout.addWidget(usb_midi_label, 1, 3)
        self.usb_midi_mode = ArrowComboBox()
        self.usb_midi_mode.setMinimumWidth(120)
        self.usb_midi_mode.setMinimumHeight(25)
        self.usb_midi_mode.setMaximumHeight(25)
        self.usb_midi_mode.setEditable(True)
        self.usb_midi_mode.lineEdit().setReadOnly(True)
        self.usb_midi_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.usb_midi_mode.addItem("Process All", 0)
        self.usb_midi_mode.addItem("Thru", 1)
        self.usb_midi_mode.addItem("Clock Only", 2)
        self.usb_midi_mode.addItem("Ignore", 3)
        midi_routing_layout.addWidget(self.usb_midi_mode, 1, 4)

        clock_source_label = QWidget()
        clock_source_label_layout = QHBoxLayout()
        clock_source_label_layout.setContentsMargins(0, 0, 0, 0)
        clock_source_label_layout.setSpacing(5)
        clock_source_label_layout.addWidget(self.create_help_label(
            "Where MIDI timing clock comes from.\n"
            "Local: Use internal clock\n"
            "USB: Sync to USB MIDI clock\n"
            "MIDI IN: Sync to DIN MIDI input clock"
        ))
        clock_source_label_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Clock Source:")))
        clock_source_label.setLayout(clock_source_label_layout)
        midi_routing_layout.addWidget(clock_source_label, 1, 5)
        self.midi_clock_source = ArrowComboBox()
        self.midi_clock_source.setMinimumWidth(120)
        self.midi_clock_source.setMinimumHeight(25)
        self.midi_clock_source.setMaximumHeight(25)
        self.midi_clock_source.setEditable(True)
        self.midi_clock_source.lineEdit().setReadOnly(True)
        self.midi_clock_source.lineEdit().setAlignment(Qt.AlignCenter)
        self.midi_clock_source.addItem("Local", 0)
        self.midi_clock_source.addItem("USB", 1)
        self.midi_clock_source.addItem("MIDI IN", 2)
        midi_routing_layout.addWidget(self.midi_clock_source, 1, 6)

        # Add MIDI Routing before Advanced Settings (swapped order)
        main_layout.addWidget(routing_row_container)
        main_layout.addWidget(advanced_row_container)

        # Apply stylesheet to center combo box text and remove padding
        main_widget.setStyleSheet("""
            QComboBox {
                text-align: center;
                padding: 0px;
            }
            QComboBox::drop-down {
                padding: 0px;
            }
            QComboBox QAbstractItemView {
                padding: 0px;
            }
        """)

        # Connect widgets to real-time HID updates
        self.global_channel.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_CHANNEL_NUMBER, self.global_channel.currentData())
        )
        self.global_transpose.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRANSPOSE_NUMBER, self.global_transpose.currentData())
        )
        self.global_velocity_curve.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_HE_VELOCITY_CURVE, self.global_velocity_curve.currentData())
        )
        self.global_velocity_min.valueChanged.connect(
            lambda v: [self.velocity_min_value_label.setText(str(v)),
                      self.send_param_update(PARAM_HE_VELOCITY_MIN, v)]
        )
        self.global_velocity_max.valueChanged.connect(
            lambda v: [self.velocity_max_value_label.setText(str(v)),
                      self.send_param_update(PARAM_HE_VELOCITY_MAX, v)]
        )
        self.base_sustain.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_BASE_SUSTAIN, self.base_sustain.currentData())
        )
        # global_aftertouch connections removed - aftertouch is now per-layer

        # KeySplit widgets
        self.key_split_channel.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLITCHANNEL, self.key_split_channel.currentData())
        )
        self.transpose_number2.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRANSPOSE_NUMBER2, self.transpose_number2.currentData())
        )
        self.velocity_curve2.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLIT_HE_VELOCITY_CURVE, self.velocity_curve2.currentData())
        )
        self.velocity_min2.valueChanged.connect(
            lambda v: [self.velocity_min2_value.setText(str(v)),
                      self.send_param_update(PARAM_KEYSPLIT_HE_VELOCITY_MIN, v)]
        )
        self.velocity_max2.valueChanged.connect(
            lambda v: [self.velocity_max2_value.setText(str(v)),
                      self.send_param_update(PARAM_KEYSPLIT_HE_VELOCITY_MAX, v)]
        )
        self.keysplit_sustain.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLIT_SUSTAIN, self.keysplit_sustain.currentData())
        )

        # TripleSplit widgets
        self.key_split2_channel.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_KEYSPLIT2CHANNEL, self.key_split2_channel.currentData())
        )
        self.transpose_number3.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRANSPOSE_NUMBER3, self.transpose_number3.currentData())
        )
        self.velocity_curve3.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRIPLESPLIT_HE_VELOCITY_CURVE, self.velocity_curve3.currentData())
        )
        self.velocity_min3.valueChanged.connect(
            lambda v: [self.velocity_min3_value.setText(str(v)),
                      self.send_param_update(PARAM_TRIPLESPLIT_HE_VELOCITY_MIN, v)]
        )
        self.velocity_max3.valueChanged.connect(
            lambda v: [self.velocity_max3_value.setText(str(v)),
                      self.send_param_update(PARAM_TRIPLESPLIT_HE_VELOCITY_MAX, v)]
        )
        self.triplesplit_sustain.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRIPLESPLIT_SUSTAIN, self.triplesplit_sustain.currentData())
        )

        # Split status updates are now handled by _on_split_enable_changed connected to the on/off dropdowns

        # MIDI Routing Override Settings
        self.channel_override.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_CHANNEL_OVERRIDE, 1 if self.channel_override.currentData() else 0)
        )
        self.velocity_override.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_VELOCITY_OVERRIDE, 1 if self.velocity_override.currentData() else 0)
        )
        self.transpose_override.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_TRANSPOSE_OVERRIDE, 1 if self.transpose_override.currentData() else 0)
        )
        self.midi_in_mode.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_MIDI_IN_MODE, self.midi_in_mode.currentData())
        )
        self.usb_midi_mode.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_USB_MIDI_MODE, self.usb_midi_mode.currentData())
        )
        self.midi_clock_source.currentIndexChanged.connect(
            lambda: self.send_param_update(PARAM_MIDI_CLOCK_SOURCE, self.midi_clock_source.currentData())
        )

    def send_param_update(self, param_id, value):
        """Send real-time HID parameter update to keyboard"""
        try:
            if self.device and isinstance(self.device, VialKeyboard):
                self.device.keyboard.set_keyboard_param_single(param_id, value)
        except Exception as e:
            # Silently fail - firmware may not support this parameter yet
            pass

    def _on_split_enable_changed(self):
        """Handle split enable changes - compute and send split status based on on/off combinations"""
        # Compute channel split status: 0=disabled, 1=keysplit, 2=triplesplit, 3=both
        channel_status = self._compute_split_status(
            self.keysplit_channel_enable.currentData(),
            self.triplesplit_channel_enable.currentData()
        )
        self.send_param_update(PARAM_KEYSPLITSTATUS, channel_status)

        # Compute transpose split status
        transpose_status = self._compute_split_status(
            self.keysplit_transpose_enable.currentData(),
            self.triplesplit_transpose_enable.currentData()
        )
        self.send_param_update(PARAM_KEYSPLITTRANSPOSESTATUS, transpose_status)

        # Compute velocity split status
        velocity_status = self._compute_split_status(
            self.keysplit_velocity_enable.currentData(),
            self.triplesplit_velocity_enable.currentData()
        )
        self.send_param_update(PARAM_KEYSPLITVELOCITYSTATUS, velocity_status)

    def _compute_split_status(self, keysplit_on, triplesplit_on):
        """Compute split status from keysplit and triplesplit enable states.
        Returns: 0=disabled, 1=keysplit only, 2=triplesplit only, 3=both"""
        if keysplit_on and triplesplit_on:
            return 3  # Both Splits On
        elif keysplit_on:
            return 1  # KeySplit On
        elif triplesplit_on:
            return 2  # TripleSplit On
        else:
            return 0  # Disable Keysplit

    def get_channel_split_status(self):
        """Get computed channel split status"""
        return self._compute_split_status(
            self.keysplit_channel_enable.currentData(),
            self.triplesplit_channel_enable.currentData()
        )

    def get_transpose_split_status(self):
        """Get computed transpose split status"""
        return self._compute_split_status(
            self.keysplit_transpose_enable.currentData(),
            self.triplesplit_transpose_enable.currentData()
        )

    def get_velocity_split_status(self):
        """Get computed velocity split status"""
        return self._compute_split_status(
            self.keysplit_velocity_enable.currentData(),
            self.triplesplit_velocity_enable.currentData()
        )

    def get_current_settings(self):
        """Get current UI settings as dictionary"""
        return {
            "velocity_sensitivity": self.velocity_sensitivity.currentData(),
            "cc_sensitivity": self.cc_sensitivity.currentData(),
            "transpose_number2": self.transpose_number2.currentData(),
            "transpose_number3": self.transpose_number3.currentData(),
            "random_velocity_modifier": self.random_velocity_modifier.currentData(),
            "oled_keyboard": self.oled_keyboard.currentData(),
            "smart_chord_light": self.smart_chord_light.currentData(),
            "smart_chord_light_mode": self.smart_chord_light_mode.currentData(),
            "key_split_channel": self.key_split_channel.currentData(),
            "key_split2_channel": self.key_split2_channel.currentData(),
            "key_split_status": self.get_channel_split_status(),
            "key_split_transpose_status": self.get_transpose_split_status(),
            "key_split_velocity_status": self.get_velocity_split_status(),
            # New enable flags for save/load
            "keysplit_channel_enable": self.keysplit_channel_enable.currentData(),
            "keysplit_transpose_enable": self.keysplit_transpose_enable.currentData(),
            "keysplit_velocity_enable": self.keysplit_velocity_enable.currentData(),
            "triplesplit_channel_enable": self.triplesplit_channel_enable.currentData(),
            "triplesplit_transpose_enable": self.triplesplit_transpose_enable.currentData(),
            "triplesplit_velocity_enable": self.triplesplit_velocity_enable.currentData(),
            "custom_layer_animations_enabled": self.custom_layer_animations.currentData(),
            "unsynced_mode_active": self.unsynced_mode.currentData(),
            "sample_mode_active": self.sample_mode.currentData(),
            "loop_messaging_enabled": self.loop_messaging_enabled.currentData(),
            "loop_messaging_channel": self.loop_messaging_channel.currentData(),
            "sync_midi_mode": self.sync_midi_mode.currentData(),
            "alternate_restart_mode": self.alternate_restart_mode.currentData(),
            "colorblindmode": self.colorblind_mode.currentData(),
            "cclooprecording": self.cc_loop_recording.currentData(),
            "truesustain": self.true_sustain.currentData(),
            # KeySplit/TripleSplit velocity settings
            "velocity_curve2": self.velocity_curve2.currentData(),
            "velocity_min2": self.velocity_min2.value(),  # Changed from currentData() to value()
            "velocity_max2": self.velocity_max2.value(),  # Changed from currentData() to value()
            "velocity_curve3": self.velocity_curve3.currentData(),
            "velocity_min3": self.velocity_min3.value(),  # Changed from currentData() to value()
            "velocity_max3": self.velocity_max3.value(),  # Changed from currentData() to value()
            # Global MIDI settings
            "global_transpose": self.global_transpose.currentData(),
            "global_channel": self.global_channel.currentData(),
            "global_velocity_curve": self.global_velocity_curve.currentData(),
            # global_aftertouch removed - now per-layer
            "global_velocity_min": self.global_velocity_min.value(),  # Changed from currentData() to value()
            "global_velocity_max": self.global_velocity_max.value(),  # Changed from currentData() to value()
            # global_aftertouch_cc removed - now per-layer
            # Sustain settings
            "base_sustain": self.base_sustain.currentData(),
            "keysplit_sustain": self.keysplit_sustain.currentData(),
            "triplesplit_sustain": self.triplesplit_sustain.currentData(),
            # MIDI Routing Override settings
            "channel_override": self.channel_override.currentData(),
            "velocity_override": self.velocity_override.currentData(),
            "transpose_override": self.transpose_override.currentData(),
            "midi_in_mode": self.midi_in_mode.currentData(),
            "usb_midi_mode": self.usb_midi_mode.currentData(),
            "midi_clock_source": self.midi_clock_source.currentData()
        }

    def apply_settings(self, config):
        """Apply settings dictionary to UI"""
        def set_combo_by_data(combo, value, default_value=None):
            for i in range(combo.count()):
                if combo.itemData(i) == value:
                    combo.setCurrentIndex(i)
                    return
            if default_value is not None:
                for i in range(combo.count()):
                    if combo.itemData(i) == default_value:
                        combo.setCurrentIndex(i)
                        return
        
        set_combo_by_data(self.velocity_sensitivity, config.get("velocity_sensitivity"), 1)
        set_combo_by_data(self.cc_sensitivity, config.get("cc_sensitivity"), 1)
        set_combo_by_data(self.transpose_number2, config.get("transpose_number2"), 0)
        set_combo_by_data(self.transpose_number3, config.get("transpose_number3"), 0)
        set_combo_by_data(self.random_velocity_modifier, config.get("random_velocity_modifier"), 0)
        set_combo_by_data(self.oled_keyboard, config.get("oled_keyboard"), 0)
        set_combo_by_data(self.smart_chord_light, config.get("smart_chord_light"), 0)
        set_combo_by_data(self.smart_chord_light_mode, config.get("smart_chord_light_mode"), 0)
        set_combo_by_data(self.key_split_channel, config.get("key_split_channel"), 0)
        set_combo_by_data(self.key_split2_channel, config.get("key_split2_channel"), 0)

        # Handle new enable flags, with backward compatibility for old split status values
        def split_status_to_enables(status):
            """Convert split status (0-3) to keysplit_on, triplesplit_on tuple"""
            if status == 3:
                return (1, 1)  # Both on
            elif status == 2:
                return (0, 1)  # Triplesplit only
            elif status == 1:
                return (1, 0)  # Keysplit only
            else:
                return (0, 0)  # Both off

        # Channel enable flags
        if "keysplit_channel_enable" in config:
            set_combo_by_data(self.keysplit_channel_enable, config.get("keysplit_channel_enable"), 0)
            set_combo_by_data(self.triplesplit_channel_enable, config.get("triplesplit_channel_enable"), 0)
        else:
            ks, ts = split_status_to_enables(config.get("key_split_status", 0))
            set_combo_by_data(self.keysplit_channel_enable, ks, 0)
            set_combo_by_data(self.triplesplit_channel_enable, ts, 0)

        # Transpose enable flags
        if "keysplit_transpose_enable" in config:
            set_combo_by_data(self.keysplit_transpose_enable, config.get("keysplit_transpose_enable"), 0)
            set_combo_by_data(self.triplesplit_transpose_enable, config.get("triplesplit_transpose_enable"), 0)
        else:
            ks, ts = split_status_to_enables(config.get("key_split_transpose_status", 0))
            set_combo_by_data(self.keysplit_transpose_enable, ks, 0)
            set_combo_by_data(self.triplesplit_transpose_enable, ts, 0)

        # Velocity enable flags
        if "keysplit_velocity_enable" in config:
            set_combo_by_data(self.keysplit_velocity_enable, config.get("keysplit_velocity_enable"), 0)
            set_combo_by_data(self.triplesplit_velocity_enable, config.get("triplesplit_velocity_enable"), 0)
        else:
            ks, ts = split_status_to_enables(config.get("key_split_velocity_status", 0))
            set_combo_by_data(self.keysplit_velocity_enable, ks, 0)
            set_combo_by_data(self.triplesplit_velocity_enable, ts, 0)
        set_combo_by_data(self.custom_layer_animations, config.get("custom_layer_animations_enabled"), False)
        set_combo_by_data(self.unsynced_mode, config.get("unsynced_mode_active"), False)
        set_combo_by_data(self.sample_mode, config.get("sample_mode_active"), False)
        set_combo_by_data(self.loop_messaging_enabled, config.get("loop_messaging_enabled"), False)
        set_combo_by_data(self.loop_messaging_channel, config.get("loop_messaging_channel"), 16)
        set_combo_by_data(self.sync_midi_mode, config.get("sync_midi_mode"), False)
        set_combo_by_data(self.alternate_restart_mode, config.get("alternate_restart_mode"), False)
        set_combo_by_data(self.colorblind_mode, config.get("colorblindmode"), 0)
        set_combo_by_data(self.cc_loop_recording, config.get("cclooprecording"), False)
        set_combo_by_data(self.true_sustain, config.get("truesustain"), False)
        # KeySplit/TripleSplit velocity settings
        set_combo_by_data(self.velocity_curve2, config.get("velocity_curve2"), 2)
        self.velocity_min2.setValue(config.get("velocity_min2", 1))  # Changed to slider setValue
        self.velocity_max2.setValue(config.get("velocity_max2", 127))  # Changed to slider setValue
        set_combo_by_data(self.velocity_curve3, config.get("velocity_curve3"), 2)
        self.velocity_min3.setValue(config.get("velocity_min3", 1))  # Changed to slider setValue
        self.velocity_max3.setValue(config.get("velocity_max3", 127))  # Changed to slider setValue
        # Global MIDI settings
        set_combo_by_data(self.global_transpose, config.get("global_transpose"), 0)
        set_combo_by_data(self.global_channel, config.get("global_channel"), 0)
        set_combo_by_data(self.global_velocity_curve, config.get("global_velocity_curve"), 2)
        # global_aftertouch removed - now per-layer
        self.global_velocity_min.setValue(config.get("global_velocity_min", 1))  # Changed to slider setValue
        self.global_velocity_max.setValue(config.get("global_velocity_max", 127))  # Changed to slider setValue
        # global_aftertouch_cc removed - now per-layer
        # Sustain settings
        set_combo_by_data(self.base_sustain, config.get("base_sustain"), 0)
        set_combo_by_data(self.keysplit_sustain, config.get("keysplit_sustain"), 0)
        set_combo_by_data(self.triplesplit_sustain, config.get("triplesplit_sustain"), 0)
        # MIDI Routing Override settings
        set_combo_by_data(self.channel_override, config.get("channel_override"), False)
        set_combo_by_data(self.velocity_override, config.get("velocity_override"), False)
        set_combo_by_data(self.transpose_override, config.get("transpose_override"), False)
        set_combo_by_data(self.midi_in_mode, config.get("midi_in_mode"), 0)
        set_combo_by_data(self.usb_midi_mode, config.get("usb_midi_mode"), 0)
        set_combo_by_data(self.midi_clock_source, config.get("midi_clock_source"), 0)

    def pack_basic_data(self, settings):
        """Pack basic settings into 17-byte structure"""
        data = bytearray(17)

        struct.pack_into('<I', data, 0, settings["velocity_sensitivity"])
        struct.pack_into('<I', data, 4, settings["cc_sensitivity"])

        offset = 8
        data[offset] = settings["global_channel"]; offset += 1  # global channel
        data[offset] = settings["global_transpose"] & 0xFF; offset += 1  # global transpose
        data[offset] = 0; offset += 1  # octave_number
        data[offset] = settings["transpose_number2"] & 0xFF; offset += 1
        data[offset] = 0; offset += 1  # octave_number2
        data[offset] = settings["transpose_number3"] & 0xFF; offset += 1
        data[offset] = 0; offset += 1  # octave_number3
        data[offset] = settings["random_velocity_modifier"]; offset += 1

        struct.pack_into('<I', data, offset, settings["oled_keyboard"]); offset += 4

        data[offset] = settings["smart_chord_light"]; offset += 1
        data[offset] = settings["smart_chord_light_mode"]; offset += 1

        return data
    
    def pack_advanced_data(self, settings):
        """Pack advanced settings into 21-byte structure (expanded for MIDI routing overrides)"""
        data = bytearray(21)

        offset = 0
        data[offset] = settings["key_split_channel"]; offset += 1
        data[offset] = settings["key_split2_channel"]; offset += 1
        data[offset] = settings["key_split_status"]; offset += 1
        data[offset] = settings["key_split_transpose_status"]; offset += 1
        data[offset] = settings["key_split_velocity_status"]; offset += 1
        data[offset] = 1 if settings["custom_layer_animations_enabled"] else 0; offset += 1
        data[offset] = settings["unsynced_mode_active"]; offset += 1
        data[offset] = 1 if settings["sample_mode_active"] else 0; offset += 1
        data[offset] = 1 if settings["loop_messaging_enabled"] else 0; offset += 1
        data[offset] = settings["loop_messaging_channel"]; offset += 1
        data[offset] = 1 if settings["sync_midi_mode"] else 0; offset += 1
        data[offset] = 1 if settings["alternate_restart_mode"] else 0; offset += 1
        data[offset] = settings["colorblindmode"]; offset += 1
        data[offset] = 1 if settings["cclooprecording"] else 0; offset += 1
        data[offset] = 1 if settings["truesustain"] else 0; offset += 1
        # MIDI Routing Override settings (bytes 15-20)
        data[offset] = 1 if settings.get("channel_override", False) else 0; offset += 1
        data[offset] = 1 if settings.get("velocity_override", False) else 0; offset += 1
        data[offset] = 1 if settings.get("transpose_override", False) else 0; offset += 1
        data[offset] = settings.get("midi_in_mode", 0); offset += 1
        data[offset] = settings.get("usb_midi_mode", 0); offset += 1
        data[offset] = settings.get("midi_clock_source", 0); offset += 1

        return data
    
    def on_save_slot(self, slot):
        """Save current settings to slot"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            settings = self.get_current_settings()
            
            basic_data = self.pack_basic_data(settings)
            if not self.device.keyboard.save_midi_slot(slot, basic_data):
                raise RuntimeError(f"Failed to save to slot {slot}")
            
            QtCore.QTimer.singleShot(50, lambda: self._send_advanced_data(settings))
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save to slot {slot}: {str(e)}")
    
    def _send_advanced_data(self, settings):
        """Send advanced data (helper for save operations)"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                return
                
            advanced_data = self.pack_advanced_data(settings)
            if not self.device.keyboard.set_midi_advanced_config(advanced_data):
                raise RuntimeError("Failed to send advanced config")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to send advanced data: {str(e)}")
    
    def on_load_slot(self, slot):
        """Load settings from slot with multi-packet handling"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
                
            if not self.device.keyboard.load_midi_slot(slot):
                raise RuntimeError(f"Failed to load from slot {slot}")
                
            # Small delay then get the loaded configuration
            QtCore.QTimer.singleShot(100, lambda: self._load_config_after_slot_load(slot))
                
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load from slot {slot}: {str(e)}")
    
    def _load_config_after_slot_load(self, slot):
        """Get and apply configuration after slot load"""
        try:
            config = self.device.keyboard.get_midi_config()
            
            if not config:
                raise RuntimeError("Failed to get config after slot load")
            
            self.apply_settings(config)
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to apply loaded config: {str(e)}")
    
    def on_load_current_settings(self):
        """Load current settings from keyboard using multi-packet collection"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            config = self.device.keyboard.get_midi_config()
            
            if not config:
                raise RuntimeError("Failed to load current settings")
            
            self.apply_settings(config)
                
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load current settings: {str(e)}")
    
    def on_reset(self):
        """Reset to default settings"""
        try:
            reply = QMessageBox.question(None, "Confirm Reset", 
                                       "Reset all keyboard settings to defaults? This cannot be undone.",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                if not self.device or not isinstance(self.device, VialKeyboard):
                    raise RuntimeError("Device not connected")
                    
                if not self.device.keyboard.reset_midi_config():
                    raise RuntimeError("Failed to reset settings")
                    
                self.reset_ui_to_defaults()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to reset settings: {str(e)}")
    
    def reset_ui_to_defaults(self):
        """Reset UI to default values"""
        defaults = {
            "velocity_sensitivity": 1,
            "cc_sensitivity": 1,
            "transpose_number2": 0,
            "transpose_number3": 0,
            "random_velocity_modifier": 127,
            "oled_keyboard": 0,
            "smart_chord_light": 0,
            "smart_chord_light_mode": 0,
            "key_split_channel": 0,
            "key_split2_channel": 0,
            "key_split_status": 0,
            "key_split_transpose_status": 0,
            "key_split_velocity_status": 0,
            "custom_layer_animations_enabled": False,
            "unsynced_mode_active": 0,
            "sample_mode_active": False,
            "loop_messaging_enabled": False,
            "loop_messaging_channel": 16,
            "sync_midi_mode": False,
            "alternate_restart_mode": False,
            "colorblindmode": 0,
            "cclooprecording": False,
            "truesustain": False,
            "velocity_curve2": 2,
            "velocity_min2": 1,
            "velocity_max2": 127,
            "velocity_curve3": 2,
            "velocity_min3": 1,
            "velocity_max3": 127,
            "global_transpose": 0,
            "global_channel": 0,
            "global_velocity_curve": 2,
            # global_aftertouch removed - now per-layer
            "global_velocity_min": 1,
            "global_velocity_max": 127,
            # global_aftertouch_cc removed - now per-layer
            "base_sustain": 0,
            "keysplit_sustain": 0,
            "triplesplit_sustain": 0,
            # MIDI Routing Override settings
            "channel_override": False,
            "velocity_override": False,
            "transpose_override": False,
            "midi_in_mode": 0,
            "usb_midi_mode": 0,
            "midi_clock_source": 0
        }
        self.apply_settings(defaults)
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        # Load MIDI configuration from keyboard
        if hasattr(self.device.keyboard, 'midi_config') and self.device.keyboard.midi_config:
            self.apply_settings(self.device.keyboard.midi_config)

# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import (QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel, 
                           QSizePolicy, QGroupBox, QGridLayout, QSlider, QCheckBox,
                           QMessageBox, QScrollArea, QFrame, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5 import QtCore

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard

class LayerActuationConfigurator(BasicEditor):
    
    def __init__(self):
        super().__init__()
        
        # Master widgets
        self.master_widgets = {}
        
        # Single layer widgets
        self.layer_widgets = {}
        
        # Current layer being viewed
        self.current_layer = 0
        
        # All layer data stored in memory
        self.layer_data = []
        for _ in range(12):
            self.layer_data.append({
                'normal': 80,
                'midi': 80,
                'aftertouch': 0,
                'velocity': 2,
                'rapid': 4,
                'midi_rapid_sens': 10,
                'midi_rapid_vel': 10,
                'vel_speed': 10,
                'aftertouch_cc': 255,  # 255 = off (no CC sent)
                'vibrato_sensitivity': 100,  # 100% = normal
                'vibrato_decay_time': 200,   # 200ms decay
                'rapidfire_enabled': False,
                'midi_rapidfire_enabled': False,
                # HE Velocity defaults
                'use_fixed_velocity': False,
                'he_curve': 2,  # Medium (linear)
                'he_min': 1,
                'he_max': 127
            })
        
        # Flag to prevent recursion
        self.updating_from_master = False
        
        # Per-layer mode
        self.per_layer_enabled = False
        
        # Advanced options shown
        self.advanced_shown = False
        
        self.setup_ui()
        
    def setup_ui(self):
        self.addStretch()
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumSize(900, 600)
        
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_widget.setLayout(main_layout)
        
        scroll.setWidget(main_widget)
        self.addWidget(scroll)
        self.setAlignment(scroll, QtCore.Qt.AlignHCenter)
        
        # Info label
        info_label = QLabel(tr("LayerActuationConfigurator", 
            "Configure actuation distances and settings per layer"))
        info_label.setStyleSheet("QLabel { color: #666; font-style: italic; font-size: 10px; margin: 5px; }")
        main_layout.addWidget(info_label, alignment=QtCore.Qt.AlignCenter)
        
        # Create master controls group
        self.master_group = self.create_master_group()
        main_layout.addWidget(self.master_group)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Layer selector container (hidden by default)
        self.layer_selector_container = QWidget()
        layer_selector_layout = QVBoxLayout()
        layer_selector_layout.setSpacing(10)
        self.layer_selector_container.setLayout(layer_selector_layout)
        
        # Layer dropdown
        selector_row = QHBoxLayout()
        selector_row.addStretch()
        selector_label = QLabel(tr("LayerActuationConfigurator", "Select Layer:"))
        selector_label.setStyleSheet("QLabel { font-weight: bold; font-size: 11px; }")
        selector_row.addWidget(selector_label)
        
        self.layer_dropdown = ArrowComboBox()
        self.layer_dropdown.setMinimumWidth(150)
        self.layer_dropdown.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        for i in range(12):
            self.layer_dropdown.addItem(f"Layer {i}", i)
        self.layer_dropdown.setEditable(True)
        self.layer_dropdown.lineEdit().setReadOnly(True)
        self.layer_dropdown.lineEdit().setAlignment(Qt.AlignCenter)
        self.layer_dropdown.currentIndexChanged.connect(self.on_layer_changed)
        selector_row.addWidget(self.layer_dropdown)
        selector_row.addStretch()
        
        layer_selector_layout.addLayout(selector_row)
        
        # Single layer group
        self.layer_group = self.create_layer_group()
        layer_selector_layout.addWidget(self.layer_group, alignment=QtCore.Qt.AlignCenter)
        
        self.layer_selector_container.setVisible(False)
        main_layout.addWidget(self.layer_selector_container)
        
        main_layout.addStretch()
        
        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Button style - bigger and less rounded
        button_style = "QPushButton { border-radius: 3px; padding: 8px 16px; }"

        save_btn = QPushButton(tr("LayerActuationConfigurator", "Save to Keyboard"))
        save_btn.setMinimumHeight(45)
        save_btn.setMinimumWidth(180)
        save_btn.setStyleSheet(button_style)
        save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_btn)

        load_btn = QPushButton(tr("LayerActuationConfigurator", "Load from Keyboard"))
        load_btn.setMinimumHeight(45)
        load_btn.setMinimumWidth(210)
        load_btn.setStyleSheet(button_style)
        load_btn.clicked.connect(self.on_load_from_keyboard)
        buttons_layout.addWidget(load_btn)

        reset_btn = QPushButton(tr("LayerActuationConfigurator", "Reset All to Defaults"))
        reset_btn.setMinimumHeight(45)
        reset_btn.setMinimumWidth(210)
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)

        self.addLayout(buttons_layout)
    
    def create_master_group(self):
        """Create the master control group with all settings"""
        group = QGroupBox(tr("LayerActuationConfigurator", "Master Settings (All Layers)"))
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; }")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        group.setLayout(layout)
        
        # Top row with both checkboxes
        checkboxes_layout = QHBoxLayout()
        
        # Master per-layer checkbox
        self.per_layer_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable Per-Layer Settings"))
        self.per_layer_checkbox.setStyleSheet("QCheckBox { font-weight: bold; font-size: 11px; }")
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_toggled)
        checkboxes_layout.addWidget(self.per_layer_checkbox)
        
        checkboxes_layout.addSpacing(20)
        
        # Show Advanced Options checkbox
        self.advanced_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Show Advanced Actuation Options"))
        self.advanced_checkbox.setStyleSheet("QCheckBox { font-size: 11px; }")
        self.advanced_checkbox.stateChanged.connect(self.on_advanced_toggled)
        checkboxes_layout.addWidget(self.advanced_checkbox)
        
        checkboxes_layout.addStretch()
        layout.addLayout(checkboxes_layout)
        
        # Add separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Normal Keys Actuation (slider) - ALWAYS VISIBLE
        slider_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Normal Keys Actuation:"))
        label.setMinimumWidth(200)
        slider_layout.addWidget(label)
        
        normal_slider = QSlider(Qt.Horizontal)
        normal_slider.setMinimum(0)
        normal_slider.setMaximum(100)
        normal_slider.setValue(80)
        slider_layout.addWidget(normal_slider)
        
        normal_value_label = QLabel("2.00mm (80)")
        normal_value_label.setMinimumWidth(100)
        normal_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        slider_layout.addWidget(normal_value_label)
        
        layout.addLayout(slider_layout)
        normal_slider.valueChanged.connect(
            lambda v, lbl=normal_value_label: self.on_master_slider_changed('normal', v, lbl)
        )
        
        # Enable Rapidfire checkbox - ALWAYS VISIBLE
        rapid_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable Rapidfire"))
        rapid_checkbox.setChecked(False)
        layout.addWidget(rapid_checkbox)
        rapid_checkbox.stateChanged.connect(self.on_rapidfire_toggled)
        
        # Rapidfire Sensitivity (slider) - hidden by default
        rapid_slider_layout = QHBoxLayout()
        rapid_label = QLabel(tr("LayerActuationConfigurator", "Rapidfire Sensitivity:"))
        rapid_label.setMinimumWidth(200)
        rapid_slider_layout.addWidget(rapid_label)
        
        rapid_slider = QSlider(Qt.Horizontal)
        rapid_slider.setMinimum(1)
        rapid_slider.setMaximum(100)
        rapid_slider.setValue(4)
        rapid_slider_layout.addWidget(rapid_slider)
        
        rapid_value_label = QLabel("4")
        rapid_value_label.setMinimumWidth(100)
        rapid_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        rapid_slider_layout.addWidget(rapid_value_label)
        
        rapid_slider_widget = QWidget()
        rapid_slider_widget.setLayout(rapid_slider_layout)
        rapid_slider_widget.setVisible(False)
        layout.addWidget(rapid_slider_widget)
        
        rapid_slider.valueChanged.connect(
            lambda v, lbl=rapid_value_label: self.on_master_slider_changed('rapid', v, lbl)
        )

        # === AFTERTOUCH CONTROLS (always visible) ===
        # Aftertouch Mode dropdown
        aftertouch_layout = QHBoxLayout()
        aftertouch_label = QLabel(tr("LayerActuationConfigurator", "Aftertouch Mode:"))
        aftertouch_label.setMinimumWidth(200)
        aftertouch_layout.addWidget(aftertouch_label)

        aftertouch_combo = ArrowComboBox()
        aftertouch_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        aftertouch_combo.addItem("Off", 0)
        aftertouch_combo.addItem("Reverse", 1)
        aftertouch_combo.addItem("Bottom-Out", 2)
        aftertouch_combo.addItem("Post-Actuation", 3)
        aftertouch_combo.addItem("Vibrato", 4)
        aftertouch_combo.setCurrentIndex(0)
        aftertouch_combo.setEditable(True)
        aftertouch_combo.lineEdit().setReadOnly(True)
        aftertouch_combo.lineEdit().setAlignment(Qt.AlignCenter)
        aftertouch_layout.addWidget(aftertouch_combo)
        aftertouch_layout.addStretch()
        layout.addLayout(aftertouch_layout)
        aftertouch_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('aftertouch', aftertouch_combo)
        )

        # Aftertouch CC dropdown
        aftertouch_cc_layout = QHBoxLayout()
        aftertouch_cc_label = QLabel(tr("LayerActuationConfigurator", "Aftertouch CC:"))
        aftertouch_cc_label.setMinimumWidth(200)
        aftertouch_cc_layout.addWidget(aftertouch_cc_label)

        aftertouch_cc_combo = ArrowComboBox()
        aftertouch_cc_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        aftertouch_cc_combo.addItem("Off", 255)
        for cc in range(128):
            aftertouch_cc_combo.addItem(f"CC#{cc}", cc)
        aftertouch_cc_combo.setCurrentIndex(0)
        aftertouch_cc_combo.setEditable(True)
        aftertouch_cc_combo.lineEdit().setReadOnly(True)
        aftertouch_cc_combo.lineEdit().setAlignment(Qt.AlignCenter)
        aftertouch_cc_layout.addWidget(aftertouch_cc_combo)
        aftertouch_cc_layout.addStretch()
        layout.addLayout(aftertouch_cc_layout)
        aftertouch_cc_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('aftertouch_cc', aftertouch_cc_combo)
        )

        # Vibrato Sensitivity slider (hidden by default, shown when Vibrato mode)
        vibrato_sens_widget = QWidget()
        vibrato_sens_layout = QHBoxLayout()
        vibrato_sens_layout.setContentsMargins(0, 0, 0, 0)
        vibrato_sens_widget.setLayout(vibrato_sens_layout)

        vibrato_sens_label = QLabel(tr("LayerActuationConfigurator", "Vibrato Sensitivity:"))
        vibrato_sens_label.setMinimumWidth(200)
        vibrato_sens_layout.addWidget(vibrato_sens_label)

        vibrato_sens_slider = QSlider(Qt.Horizontal)
        vibrato_sens_slider.setMinimum(50)
        vibrato_sens_slider.setMaximum(200)
        vibrato_sens_slider.setValue(100)
        vibrato_sens_layout.addWidget(vibrato_sens_slider)

        vibrato_sens_value_label = QLabel("100%")
        vibrato_sens_value_label.setMinimumWidth(60)
        vibrato_sens_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        vibrato_sens_layout.addWidget(vibrato_sens_value_label)

        layout.addWidget(vibrato_sens_widget)
        vibrato_sens_widget.setVisible(False)
        vibrato_sens_slider.valueChanged.connect(
            lambda v, lbl=vibrato_sens_value_label: self.on_master_slider_changed('vibrato_sensitivity', v, lbl)
        )

        # Vibrato Decay Time slider (hidden by default, shown when Vibrato mode)
        vibrato_decay_widget = QWidget()
        vibrato_decay_layout = QHBoxLayout()
        vibrato_decay_layout.setContentsMargins(0, 0, 0, 0)
        vibrato_decay_widget.setLayout(vibrato_decay_layout)

        vibrato_decay_label = QLabel(tr("LayerActuationConfigurator", "Vibrato Decay Time:"))
        vibrato_decay_label.setMinimumWidth(200)
        vibrato_decay_layout.addWidget(vibrato_decay_label)

        vibrato_decay_slider = QSlider(Qt.Horizontal)
        vibrato_decay_slider.setMinimum(0)
        vibrato_decay_slider.setMaximum(2000)
        vibrato_decay_slider.setValue(200)
        vibrato_decay_layout.addWidget(vibrato_decay_slider)

        vibrato_decay_value_label = QLabel("200ms")
        vibrato_decay_value_label.setMinimumWidth(60)
        vibrato_decay_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        vibrato_decay_layout.addWidget(vibrato_decay_value_label)

        layout.addWidget(vibrato_decay_widget)
        vibrato_decay_widget.setVisible(False)
        vibrato_decay_slider.valueChanged.connect(
            lambda v, lbl=vibrato_decay_value_label: self.on_master_slider_changed('vibrato_decay_time', v, lbl)
        )

        # Connect aftertouch mode to show/hide vibrato controls
        aftertouch_combo.currentIndexChanged.connect(
            lambda idx: self.on_aftertouch_mode_changed(aftertouch_combo, vibrato_sens_widget, vibrato_decay_widget)
        )

        # === ADVANCED OPTIONS (hidden by default) ===
        self.advanced_widget = QWidget()
        advanced_layout_main = QVBoxLayout()
        advanced_layout_main.setSpacing(8)
        advanced_layout_main.setContentsMargins(0, 10, 0, 0)
        self.advanced_widget.setLayout(advanced_layout_main)
        self.advanced_widget.setVisible(False)

        # Add separator
        adv_line = QFrame()
        adv_line.setFrameShape(QFrame.HLine)
        adv_line.setFrameShadow(QFrame.Sunken)
        advanced_layout_main.addWidget(adv_line)

        # Title for MIDI settings section
        midi_settings_title = QLabel(tr("LayerActuationConfigurator", "Basic MIDI Settings"))
        midi_settings_title.setStyleSheet("QLabel { font-weight: bold; font-size: 11px; margin: 5px 0px; }")
        advanced_layout_main.addWidget(midi_settings_title)

        # Container for MIDI settings and split offshoots (side by side)
        content_container = QHBoxLayout()
        advanced_layout = QVBoxLayout()

        # Split Mode control
        split_mode_layout = QHBoxLayout()
        split_mode_label = QLabel(tr("LayerActuationConfigurator", "Split Mode:"))
        split_mode_label.setMinimumWidth(200)
        split_mode_layout.addWidget(split_mode_label)

        self.actuation_split_mode = ArrowComboBox()
        self.actuation_split_mode.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        self.actuation_split_mode.addItem("Disable Keysplit", 0)
        self.actuation_split_mode.addItem("KeySplit On", 1)
        self.actuation_split_mode.addItem("TripleSplit On", 2)
        self.actuation_split_mode.addItem("Both Splits On", 3)
        self.actuation_split_mode.setCurrentIndex(0)
        self.actuation_split_mode.setEditable(True)
        self.actuation_split_mode.lineEdit().setReadOnly(True)
        self.actuation_split_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.actuation_split_mode.currentIndexChanged.connect(self.on_actuation_split_mode_changed)
        split_mode_layout.addWidget(self.actuation_split_mode)
        split_mode_layout.addStretch()

        advanced_layout.addLayout(split_mode_layout)

        # MIDI Keys Actuation (slider)
        midi_slider_layout = QHBoxLayout()
        midi_label = QLabel(tr("LayerActuationConfigurator", "MIDI Keys Actuation:"))
        midi_label.setMinimumWidth(200)
        midi_slider_layout.addWidget(midi_label)
        
        midi_slider = QSlider(Qt.Horizontal)
        midi_slider.setMinimum(0)
        midi_slider.setMaximum(100)
        midi_slider.setValue(80)
        midi_slider_layout.addWidget(midi_slider)
        
        midi_value_label = QLabel("2.00mm (80)")
        midi_value_label.setMinimumWidth(100)
        midi_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_slider_layout.addWidget(midi_value_label)
        
        advanced_layout.addLayout(midi_slider_layout)
        midi_slider.valueChanged.connect(
            lambda v, lbl=midi_value_label: self.on_master_slider_changed('midi', v, lbl)
        )

        # Note: Aftertouch controls moved outside advanced section (always visible)

        # Velocity Mode (dropdown)
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Velocity Mode:"))
        label.setMinimumWidth(200)
        combo_layout.addWidget(label)
        
        velocity_combo = ArrowComboBox()
        velocity_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        velocity_combo.addItem("Fixed (64)", 0)
        velocity_combo.addItem("Peak at Apex", 1)
        velocity_combo.addItem("Speed-Based", 2)
        velocity_combo.addItem("Speed + Peak Combined", 3)
        velocity_combo.setCurrentIndex(2)
        velocity_combo.setEditable(True)
        velocity_combo.lineEdit().setReadOnly(True)
        velocity_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(velocity_combo)
        combo_layout.addStretch()
        
        advanced_layout.addLayout(combo_layout)
        velocity_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('velocity', velocity_combo)
        )
        
        # Velocity Speed Scale (dropdown)
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Velocity Speed Scale:"))
        label.setMinimumWidth(200)
        combo_layout.addWidget(label)
        
        vel_speed_combo = ArrowComboBox()
        vel_speed_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        for i in range(1, 21):
            vel_speed_combo.addItem(str(i), i)
        vel_speed_combo.setCurrentIndex(9)
        vel_speed_combo.setEditable(True)
        vel_speed_combo.lineEdit().setReadOnly(True)
        vel_speed_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(vel_speed_combo)
        combo_layout.addStretch()
        
        advanced_layout.addLayout(combo_layout)
        vel_speed_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('vel_speed', vel_speed_combo)
        )
        
        # Enable MIDI Rapidfire checkbox
        midi_rapid_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable MIDI Rapidfire"))
        midi_rapid_checkbox.setChecked(False)
        advanced_layout.addWidget(midi_rapid_checkbox)
        midi_rapid_checkbox.stateChanged.connect(self.on_midi_rapidfire_toggled)
        
        # MIDI Rapidfire Sensitivity (slider) - hidden by default
        midi_rapid_sens_layout = QHBoxLayout()
        midi_rapid_sens_label = QLabel(tr("LayerActuationConfigurator", "MIDI Rapidfire Sensitivity:"))
        midi_rapid_sens_label.setMinimumWidth(200)
        midi_rapid_sens_layout.addWidget(midi_rapid_sens_label)
        
        midi_rapid_sens_slider = QSlider(Qt.Horizontal)
        midi_rapid_sens_slider.setMinimum(1)
        midi_rapid_sens_slider.setMaximum(100)
        midi_rapid_sens_slider.setValue(10)
        midi_rapid_sens_layout.addWidget(midi_rapid_sens_slider)
        
        midi_rapid_sens_value_label = QLabel("10")
        midi_rapid_sens_value_label.setMinimumWidth(100)
        midi_rapid_sens_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_sens_layout.addWidget(midi_rapid_sens_value_label)
        
        midi_rapid_sens_widget = QWidget()
        midi_rapid_sens_widget.setLayout(midi_rapid_sens_layout)
        midi_rapid_sens_widget.setVisible(False)
        advanced_layout.addWidget(midi_rapid_sens_widget)
        
        midi_rapid_sens_slider.valueChanged.connect(
            lambda v, lbl=midi_rapid_sens_value_label: self.on_master_slider_changed('midi_rapid_sens', v, lbl)
        )
        
        # MIDI Rapidfire Velocity Range (slider) - hidden by default
        midi_rapid_vel_layout = QHBoxLayout()
        midi_rapid_vel_label = QLabel(tr("LayerActuationConfigurator", "MIDI Rapidfire Velocity Range:"))
        midi_rapid_vel_label.setMinimumWidth(200)
        midi_rapid_vel_layout.addWidget(midi_rapid_vel_label)
        
        midi_rapid_vel_slider = QSlider(Qt.Horizontal)
        midi_rapid_vel_slider.setMinimum(0)
        midi_rapid_vel_slider.setMaximum(20)
        midi_rapid_vel_slider.setValue(10)
        midi_rapid_vel_layout.addWidget(midi_rapid_vel_slider)
        
        midi_rapid_vel_value_label = QLabel("±10")
        midi_rapid_vel_value_label.setMinimumWidth(100)
        midi_rapid_vel_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_vel_layout.addWidget(midi_rapid_vel_value_label)
        
        midi_rapid_vel_widget = QWidget()
        midi_rapid_vel_widget.setLayout(midi_rapid_vel_layout)
        midi_rapid_vel_widget.setVisible(False)
        advanced_layout.addWidget(midi_rapid_vel_widget)
        
        midi_rapid_vel_slider.valueChanged.connect(
            lambda v, lbl=midi_rapid_vel_value_label: self.on_master_slider_changed('midi_rapid_vel', v, lbl)
        )

        # === HE VELOCITY CONTROLS ===
        # Add separator
        he_line = QFrame()
        he_line.setFrameShape(QFrame.HLine)
        he_line.setFrameShadow(QFrame.Sunken)
        advanced_layout.addWidget(he_line)

        # Use Fixed Velocity checkbox
        use_fixed_vel_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Use Fixed Velocity"))
        use_fixed_vel_checkbox.setChecked(False)
        use_fixed_vel_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        advanced_layout.addWidget(use_fixed_vel_checkbox)
        use_fixed_vel_checkbox.stateChanged.connect(self.on_use_fixed_velocity_toggled)

        # HE Velocity Curve (dropdown)
        curve_layout = QHBoxLayout()
        curve_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Curve:"))
        curve_label.setMinimumWidth(200)
        curve_layout.addWidget(curve_label)

        he_curve_combo = ArrowComboBox()
        he_curve_combo.setMinimumHeight(30)
        he_curve_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; font-size: 12px; } QComboBox QAbstractItemView { min-height: 125px; }")
        # Factory curves (0-6)
        he_curve_combo.addItem("Linear", 0)
        he_curve_combo.addItem("Aggro", 1)
        he_curve_combo.addItem("Slow", 2)
        he_curve_combo.addItem("Smooth", 3)
        he_curve_combo.addItem("Steep", 4)
        he_curve_combo.addItem("Instant", 5)
        he_curve_combo.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            he_curve_combo.addItem(f"User {i+1}", 7 + i)
        he_curve_combo.setCurrentIndex(0)  # Default: Linear
        he_curve_combo.setEditable(True)
        he_curve_combo.lineEdit().setReadOnly(True)
        he_curve_combo.lineEdit().setAlignment(Qt.AlignCenter)
        curve_layout.addWidget(he_curve_combo)
        curve_layout.addStretch()

        advanced_layout.addLayout(curve_layout)
        he_curve_combo.currentIndexChanged.connect(
            lambda: self.on_master_combo_changed('he_curve', he_curve_combo)
        )

        # HE Velocity Min (slider)
        he_min_layout = QHBoxLayout()
        he_min_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Min:"))
        he_min_label.setMinimumWidth(200)
        he_min_layout.addWidget(he_min_label)

        he_min_slider = QSlider(Qt.Horizontal)
        he_min_slider.setMinimum(1)
        he_min_slider.setMaximum(127)
        he_min_slider.setValue(1)
        he_min_layout.addWidget(he_min_slider)

        he_min_value_label = QLabel("1")
        he_min_value_label.setMinimumWidth(100)
        he_min_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        he_min_layout.addWidget(he_min_value_label)

        advanced_layout.addLayout(he_min_layout)
        he_min_slider.valueChanged.connect(
            lambda v, lbl=he_min_value_label: self.on_master_slider_changed('he_min', v, lbl)
        )

        # HE Velocity Max (slider)
        he_max_layout = QHBoxLayout()
        he_max_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Max:"))
        he_max_label.setMinimumWidth(200)
        he_max_layout.addWidget(he_max_label)

        he_max_slider = QSlider(Qt.Horizontal)
        he_max_slider.setMinimum(1)
        he_max_slider.setMaximum(127)
        he_max_slider.setValue(127)
        he_max_layout.addWidget(he_max_slider)

        he_max_value_label = QLabel("127")
        he_max_value_label.setMinimumWidth(100)
        he_max_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        he_max_layout.addWidget(he_max_value_label)

        advanced_layout.addLayout(he_max_layout)
        he_max_slider.valueChanged.connect(
            lambda v, lbl=he_max_value_label: self.on_master_slider_changed('he_max', v, lbl)
        )

        # Add the MIDI settings layout to the content container
        content_container.addLayout(advanced_layout, 1)

        # Create KeySplit offshoot window
        self.keysplit_actuation_offshoot = QGroupBox(tr("LayerActuationConfigurator", "KeySplit Settings"))
        self.keysplit_actuation_offshoot.setMaximumWidth(300)
        keysplit_layout = QGridLayout()
        keysplit_layout.setVerticalSpacing(10)
        keysplit_layout.setHorizontalSpacing(10)
        self.keysplit_actuation_offshoot.setLayout(keysplit_layout)

        ks_row = 0
        keysplit_layout.addWidget(QLabel(tr("LayerActuationConfigurator", "Sustain:")), ks_row, 0)
        self.keysplit_actuation_sustain = ArrowComboBox()
        self.keysplit_actuation_sustain.setMinimumWidth(80)
        self.keysplit_actuation_sustain.setMaximumWidth(120)
        self.keysplit_actuation_sustain.setMinimumHeight(25)
        self.keysplit_actuation_sustain.setMaximumHeight(25)
        self.keysplit_actuation_sustain.addItem("Ignore", 0)
        self.keysplit_actuation_sustain.addItem("Allow", 1)
        self.keysplit_actuation_sustain.setCurrentIndex(0)
        self.keysplit_actuation_sustain.setEditable(True)
        self.keysplit_actuation_sustain.lineEdit().setReadOnly(True)
        self.keysplit_actuation_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        keysplit_layout.addWidget(self.keysplit_actuation_sustain, ks_row, 1)

        self.keysplit_actuation_offshoot.hide()

        # TripleSplit offshoot window
        self.triplesplit_actuation_offshoot = QGroupBox(tr("LayerActuationConfigurator", "TripleSplit Settings"))
        self.triplesplit_actuation_offshoot.setMaximumWidth(300)
        triplesplit_layout = QGridLayout()
        triplesplit_layout.setVerticalSpacing(10)
        triplesplit_layout.setHorizontalSpacing(10)
        self.triplesplit_actuation_offshoot.setLayout(triplesplit_layout)

        ts_row = 0
        triplesplit_layout.addWidget(QLabel(tr("LayerActuationConfigurator", "Sustain:")), ts_row, 0)
        self.triplesplit_actuation_sustain = ArrowComboBox()
        self.triplesplit_actuation_sustain.setMinimumWidth(80)
        self.triplesplit_actuation_sustain.setMaximumWidth(120)
        self.triplesplit_actuation_sustain.setMinimumHeight(25)
        self.triplesplit_actuation_sustain.setMaximumHeight(25)
        self.triplesplit_actuation_sustain.addItem("Ignore", 0)
        self.triplesplit_actuation_sustain.addItem("Allow", 1)
        self.triplesplit_actuation_sustain.setCurrentIndex(0)
        self.triplesplit_actuation_sustain.setEditable(True)
        self.triplesplit_actuation_sustain.lineEdit().setReadOnly(True)
        self.triplesplit_actuation_sustain.lineEdit().setAlignment(Qt.AlignCenter)
        triplesplit_layout.addWidget(self.triplesplit_actuation_sustain, ts_row, 1)

        self.triplesplit_actuation_offshoot.hide()

        # Add offshoots to content container (side by side)
        content_container.addWidget(self.keysplit_actuation_offshoot)
        content_container.addWidget(self.triplesplit_actuation_offshoot)

        # Add content container to main advanced layout
        advanced_layout_main.addLayout(content_container)

        layout.addWidget(self.advanced_widget)
        
        # Store widgets
        self.master_widgets = {
            'normal_slider': normal_slider,
            'normal_label': normal_value_label,
            'midi_slider': midi_slider,
            'midi_label': midi_value_label,
            'aftertouch_combo': aftertouch_combo,
            'aftertouch_cc_combo': aftertouch_cc_combo,
            'vibrato_sensitivity_slider': vibrato_sens_slider,
            'vibrato_sensitivity_label': vibrato_sens_value_label,
            'vibrato_sensitivity_widget': vibrato_sens_widget,
            'vibrato_decay_time_slider': vibrato_decay_slider,
            'vibrato_decay_time_label': vibrato_decay_value_label,
            'vibrato_decay_time_widget': vibrato_decay_widget,
            'velocity_combo': velocity_combo,
            'vel_speed_combo': vel_speed_combo,
            'rapid_checkbox': rapid_checkbox,
            'rapid_slider': rapid_slider,
            'rapid_label': rapid_value_label,
            'rapid_widget': rapid_slider_widget,
            'midi_rapid_checkbox': midi_rapid_checkbox,
            'midi_rapid_sens_slider': midi_rapid_sens_slider,
            'midi_rapid_sens_label': midi_rapid_sens_value_label,
            'midi_rapid_sens_widget': midi_rapid_sens_widget,
            'midi_rapid_vel_slider': midi_rapid_vel_slider,
            'midi_rapid_vel_label': midi_rapid_vel_value_label,
            'midi_rapid_vel_widget': midi_rapid_vel_widget,
            # HE Velocity controls
            'use_fixed_vel_checkbox': use_fixed_vel_checkbox,
            'he_curve_combo': he_curve_combo,
            'he_min_slider': he_min_slider,
            'he_min_label': he_min_value_label,
            'he_max_slider': he_max_slider,
            'he_max_label': he_max_value_label
        }
        
        return group
    
    def create_layer_group(self):
        """Create a group for the currently selected layer's settings"""
        group = QGroupBox(tr("LayerActuationConfigurator", f"Layer {self.current_layer} Settings"))
        group.setMaximumWidth(500)
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11px; }")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        group.setLayout(layout)
        
        # Show Advanced Options checkbox
        layer_advanced_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Show Advanced Actuation Options"))
        layer_advanced_checkbox.setStyleSheet("QCheckBox { font-size: 11px; margin-bottom: 5px; }")
        layer_advanced_checkbox.stateChanged.connect(self.on_layer_advanced_toggled)
        layout.addWidget(layer_advanced_checkbox)
        
        # Add separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Normal actuation slider - ALWAYS VISIBLE
        normal_slider_layout = QHBoxLayout()
        normal_label = QLabel(tr("LayerActuationConfigurator", "Normal Keys Actuation:"))
        normal_label.setMinimumWidth(180)
        normal_slider_layout.addWidget(normal_label)
        
        normal_slider = QSlider(Qt.Horizontal)
        normal_slider.setMinimum(0)
        normal_slider.setMaximum(100)
        normal_slider.setValue(80)
        normal_slider_layout.addWidget(normal_slider)
        
        normal_value_label = QLabel("2.00mm (80)")
        normal_value_label.setMinimumWidth(100)
        normal_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        normal_slider_layout.addWidget(normal_value_label)
        
        layout.addLayout(normal_slider_layout)
        normal_slider.valueChanged.connect(
            lambda v, lbl=normal_value_label: self.on_layer_slider_changed('normal', v, lbl)
        )
        self.layer_widgets['normal_slider'] = normal_slider
        self.layer_widgets['normal_label'] = normal_value_label
        
        # Enable Rapidfire checkbox - ALWAYS VISIBLE
        rapid_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable Rapidfire"))
        rapid_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        layout.addWidget(rapid_checkbox)
        self.layer_widgets['rapid_checkbox'] = rapid_checkbox
        
        # Rapidfire Sensitivity slider - hidden by default
        rapid_sens_slider_layout = QHBoxLayout()
        rapid_sens_label = QLabel(tr("LayerActuationConfigurator", "Rapidfire Sensitivity:"))
        rapid_sens_label.setMinimumWidth(180)
        rapid_sens_slider_layout.addWidget(rapid_sens_label)
        
        rapid_sens_slider = QSlider(Qt.Horizontal)
        rapid_sens_slider.setMinimum(1)
        rapid_sens_slider.setMaximum(100)
        rapid_sens_slider.setValue(4)
        rapid_sens_slider_layout.addWidget(rapid_sens_slider)
        
        rapid_sens_value_label = QLabel("4")
        rapid_sens_value_label.setMinimumWidth(100)
        rapid_sens_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        rapid_sens_slider_layout.addWidget(rapid_sens_value_label)
        
        rapid_widget = QWidget()
        rapid_widget.setLayout(rapid_sens_slider_layout)
        rapid_widget.setVisible(False)
        layout.addWidget(rapid_widget)
        
        rapid_sens_slider.valueChanged.connect(
            lambda v, lbl=rapid_sens_value_label: self.on_layer_slider_changed('rapid', v, lbl)
        )
        self.layer_widgets['rapid_slider'] = rapid_sens_slider
        self.layer_widgets['rapid_label'] = rapid_sens_value_label
        self.layer_widgets['rapid_widget'] = rapid_widget
        
        rapid_checkbox.stateChanged.connect(
            lambda state: rapid_widget.setVisible(state == Qt.Checked)
        )
        
        # === ADVANCED OPTIONS (hidden by default) ===
        layer_advanced_widget = QWidget()
        layer_advanced_layout = QVBoxLayout()
        layer_advanced_layout.setSpacing(8)
        layer_advanced_layout.setContentsMargins(0, 10, 0, 0)
        layer_advanced_widget.setLayout(layer_advanced_layout)
        layer_advanced_widget.setVisible(False)
        
        # Add separator
        adv_line = QFrame()
        adv_line.setFrameShape(QFrame.HLine)
        adv_line.setFrameShadow(QFrame.Sunken)
        layer_advanced_layout.addWidget(adv_line)
        
        # MIDI actuation slider
        midi_slider_layout = QHBoxLayout()
        midi_label = QLabel(tr("LayerActuationConfigurator", "MIDI Keys Actuation:"))
        midi_label.setMinimumWidth(180)
        midi_slider_layout.addWidget(midi_label)
        
        midi_slider = QSlider(Qt.Horizontal)
        midi_slider.setMinimum(0)
        midi_slider.setMaximum(100)
        midi_slider.setValue(80)
        midi_slider_layout.addWidget(midi_slider)
        
        midi_value_label = QLabel("2.00mm (80)")
        midi_value_label.setMinimumWidth(100)
        midi_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_slider_layout.addWidget(midi_value_label)
        
        layer_advanced_layout.addLayout(midi_slider_layout)
        midi_slider.valueChanged.connect(
            lambda v, lbl=midi_value_label: self.on_layer_slider_changed('midi', v, lbl)
        )
        self.layer_widgets['midi_slider'] = midi_slider
        self.layer_widgets['midi_label'] = midi_value_label
        
        # Aftertouch Mode combo
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Aftertouch Mode:"))
        label.setMinimumWidth(180)
        combo_layout.addWidget(label)
        
        combo = ArrowComboBox()
        combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        combo.addItem("Off", 0)
        combo.addItem("Reverse", 1)
        combo.addItem("Bottom-Out", 2)
        combo.addItem("Post-Actuation", 3)
        combo.addItem("Vibrato", 4)
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(combo)
        combo_layout.addStretch()

        layer_advanced_layout.addLayout(combo_layout)
        combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('aftertouch', combo)
        )
        self.layer_widgets['aftertouch_combo'] = combo
        
        # Aftertouch CC combo
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Aftertouch CC:"))
        label.setMinimumWidth(180)
        combo_layout.addWidget(label)
        
        combo = ArrowComboBox()
        combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        combo.addItem("Off", 255)  # 255 = no CC sent, only poly aftertouch
        for cc in range(128):
            combo.addItem(f"CC#{cc}", cc)
        combo.setCurrentIndex(0)  # Default: Off
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(combo)
        combo_layout.addStretch()

        layer_advanced_layout.addLayout(combo_layout)
        combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('aftertouch_cc', combo)
        )
        self.layer_widgets['aftertouch_cc_combo'] = combo
        
        # Velocity Mode combo
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Velocity Mode:"))
        label.setMinimumWidth(180)
        combo_layout.addWidget(label)
        
        combo = ArrowComboBox()
        combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        combo.addItem("Fixed (64)", 0)
        combo.addItem("Peak at Apex", 1)
        combo.addItem("Speed-Based", 2)
        combo.addItem("Speed + Peak Combined", 3)
        combo.setCurrentIndex(2)
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(combo)
        combo_layout.addStretch()

        layer_advanced_layout.addLayout(combo_layout)
        combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('velocity', combo)
        )
        self.layer_widgets['velocity_combo'] = combo
        
        # Velocity Speed Scale combo
        combo_layout = QHBoxLayout()
        label = QLabel(tr("LayerActuationConfigurator", "Velocity Speed Scale:"))
        label.setMinimumWidth(180)
        combo_layout.addWidget(label)
        
        combo = ArrowComboBox()
        combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; }")
        for i in range(1, 21):
            combo.addItem(str(i), i)
        combo.setCurrentIndex(9)
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(combo)
        combo_layout.addStretch()

        layer_advanced_layout.addLayout(combo_layout)
        combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('vel_speed', combo)
        )
        self.layer_widgets['vel_speed_combo'] = combo
        
        # Enable MIDI Rapidfire checkbox
        midi_rapid_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Enable MIDI Rapidfire"))
        midi_rapid_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        layer_advanced_layout.addWidget(midi_rapid_checkbox)
        self.layer_widgets['midi_rapid_checkbox'] = midi_rapid_checkbox
        
        # MIDI Rapidfire Sensitivity slider - hidden by default
        midi_rapid_sens_slider_layout = QHBoxLayout()
        midi_rapid_sens_label = QLabel(tr("LayerActuationConfigurator", "MIDI Rapidfire Sensitivity:"))
        midi_rapid_sens_label.setMinimumWidth(180)
        midi_rapid_sens_slider_layout.addWidget(midi_rapid_sens_label)
        
        midi_rapid_sens_slider = QSlider(Qt.Horizontal)
        midi_rapid_sens_slider.setMinimum(1)
        midi_rapid_sens_slider.setMaximum(100)
        midi_rapid_sens_slider.setValue(10)
        midi_rapid_sens_slider_layout.addWidget(midi_rapid_sens_slider)
        
        midi_rapid_sens_value_label = QLabel("10")
        midi_rapid_sens_value_label.setMinimumWidth(100)
        midi_rapid_sens_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_sens_slider_layout.addWidget(midi_rapid_sens_value_label)
        
        midi_rapid_sens_widget = QWidget()
        midi_rapid_sens_widget.setLayout(midi_rapid_sens_slider_layout)
        midi_rapid_sens_widget.setVisible(False)
        layer_advanced_layout.addWidget(midi_rapid_sens_widget)
        
        midi_rapid_sens_slider.valueChanged.connect(
            lambda v, lbl=midi_rapid_sens_value_label: self.on_layer_slider_changed('midi_rapid_sens', v, lbl)
        )
        self.layer_widgets['midi_rapid_sens_slider'] = midi_rapid_sens_slider
        self.layer_widgets['midi_rapid_sens_label'] = midi_rapid_sens_value_label
        self.layer_widgets['midi_rapid_sens_widget'] = midi_rapid_sens_widget
        
        # MIDI Rapidfire Velocity Range slider - hidden by default
        midi_rapid_vel_slider_layout = QHBoxLayout()
        midi_rapid_vel_label = QLabel(tr("LayerActuationConfigurator", "MIDI Rapidfire Velocity Range:"))
        midi_rapid_vel_label.setMinimumWidth(180)
        midi_rapid_vel_slider_layout.addWidget(midi_rapid_vel_label)
        
        midi_rapid_vel_slider = QSlider(Qt.Horizontal)
        midi_rapid_vel_slider.setMinimum(0)
        midi_rapid_vel_slider.setMaximum(20)
        midi_rapid_vel_slider.setValue(10)
        midi_rapid_vel_slider_layout.addWidget(midi_rapid_vel_slider)
        
        midi_rapid_vel_value_label = QLabel("±10")
        midi_rapid_vel_value_label.setMinimumWidth(100)
        midi_rapid_vel_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        midi_rapid_vel_slider_layout.addWidget(midi_rapid_vel_value_label)
        
        midi_rapid_vel_widget = QWidget()
        midi_rapid_vel_widget.setLayout(midi_rapid_vel_slider_layout)
        midi_rapid_vel_widget.setVisible(False)
        layer_advanced_layout.addWidget(midi_rapid_vel_widget)
        
        midi_rapid_vel_slider.valueChanged.connect(
            lambda v, lbl=midi_rapid_vel_value_label: self.on_layer_slider_changed('midi_rapid_vel', v, lbl)
        )
        self.layer_widgets['midi_rapid_vel_slider'] = midi_rapid_vel_slider
        self.layer_widgets['midi_rapid_vel_label'] = midi_rapid_vel_value_label
        self.layer_widgets['midi_rapid_vel_widget'] = midi_rapid_vel_widget
        
        # Connect checkbox to show/hide both MIDI rapidfire widgets
        def toggle_midi_rapid_widgets(state):
            enabled = (state == Qt.Checked)
            midi_rapid_sens_widget.setVisible(enabled)
            midi_rapid_vel_widget.setVisible(enabled)
        
        midi_rapid_checkbox.stateChanged.connect(toggle_midi_rapid_widgets)

        # === HE VELOCITY CONTROLS (PER-LAYER) ===
        # Add separator
        he_line = QFrame()
        he_line.setFrameShape(QFrame.HLine)
        he_line.setFrameShadow(QFrame.Sunken)
        layer_advanced_layout.addWidget(he_line)

        # Use Fixed Velocity checkbox
        use_fixed_vel_checkbox = QCheckBox(tr("LayerActuationConfigurator", "Use Fixed Velocity"))
        use_fixed_vel_checkbox.setChecked(False)
        use_fixed_vel_checkbox.setStyleSheet("QCheckBox { font-size: 10px; }")
        layer_advanced_layout.addWidget(use_fixed_vel_checkbox)
        self.layer_widgets['use_fixed_vel_checkbox'] = use_fixed_vel_checkbox

        # HE Velocity Curve (dropdown)
        curve_layout = QHBoxLayout()
        curve_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Curve:"))
        curve_label.setMinimumWidth(180)
        curve_layout.addWidget(curve_label)

        he_curve_combo = ArrowComboBox()
        he_curve_combo.setMinimumHeight(30)
        he_curve_combo.setStyleSheet("QComboBox { padding: 0px; text-align: center; font-size: 12px; } QComboBox QAbstractItemView { min-height: 125px; }")
        # Factory curves (0-6)
        he_curve_combo.addItem("Linear", 0)
        he_curve_combo.addItem("Aggro", 1)
        he_curve_combo.addItem("Slow", 2)
        he_curve_combo.addItem("Smooth", 3)
        he_curve_combo.addItem("Steep", 4)
        he_curve_combo.addItem("Instant", 5)
        he_curve_combo.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            he_curve_combo.addItem(f"User {i+1}", 7 + i)
        he_curve_combo.setCurrentIndex(0)  # Default: Linear
        he_curve_combo.setEditable(True)
        he_curve_combo.lineEdit().setReadOnly(True)
        he_curve_combo.lineEdit().setAlignment(Qt.AlignCenter)
        curve_layout.addWidget(he_curve_combo)
        curve_layout.addStretch()

        layer_advanced_layout.addLayout(curve_layout)
        he_curve_combo.currentIndexChanged.connect(
            lambda: self.on_layer_combo_changed('he_curve', he_curve_combo)
        )
        self.layer_widgets['he_curve_combo'] = he_curve_combo

        # HE Velocity Min (slider)
        he_min_layout = QHBoxLayout()
        he_min_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Min:"))
        he_min_label.setMinimumWidth(180)
        he_min_layout.addWidget(he_min_label)

        he_min_slider = QSlider(Qt.Horizontal)
        he_min_slider.setMinimum(1)
        he_min_slider.setMaximum(127)
        he_min_slider.setValue(1)
        he_min_layout.addWidget(he_min_slider)

        he_min_value_label = QLabel("1")
        he_min_value_label.setMinimumWidth(100)
        he_min_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        he_min_layout.addWidget(he_min_value_label)

        layer_advanced_layout.addLayout(he_min_layout)
        he_min_slider.valueChanged.connect(
            lambda v, lbl=he_min_value_label: self.on_layer_slider_changed('he_min', v, lbl)
        )
        self.layer_widgets['he_min_slider'] = he_min_slider
        self.layer_widgets['he_min_label'] = he_min_value_label

        # HE Velocity Max (slider)
        he_max_layout = QHBoxLayout()
        he_max_label = QLabel(tr("LayerActuationConfigurator", "HE Velocity Max:"))
        he_max_label.setMinimumWidth(180)
        he_max_layout.addWidget(he_max_label)

        he_max_slider = QSlider(Qt.Horizontal)
        he_max_slider.setMinimum(1)
        he_max_slider.setMaximum(127)
        he_max_slider.setValue(127)
        he_max_layout.addWidget(he_max_slider)

        he_max_value_label = QLabel("127")
        he_max_value_label.setMinimumWidth(100)
        he_max_value_label.setStyleSheet("QLabel { font-weight: bold; }")
        he_max_layout.addWidget(he_max_value_label)

        layer_advanced_layout.addLayout(he_max_layout)
        he_max_slider.valueChanged.connect(
            lambda v, lbl=he_max_value_label: self.on_layer_slider_changed('he_max', v, lbl)
        )
        self.layer_widgets['he_max_slider'] = he_max_slider
        self.layer_widgets['he_max_label'] = he_max_value_label

        layout.addWidget(layer_advanced_widget)
        self.layer_widgets['advanced_widget'] = layer_advanced_widget
        self.layer_widgets['advanced_checkbox'] = layer_advanced_checkbox
        self.layer_widgets['group'] = group
        
        return group
    
    def on_advanced_toggled(self):
        """Show/hide advanced options in master controls"""
        self.advanced_shown = self.advanced_checkbox.isChecked()
        self.advanced_widget.setVisible(self.advanced_shown)

    def on_actuation_split_mode_changed(self):
        """Show/hide split offshoots based on split mode"""
        if not hasattr(self, 'actuation_split_mode'):
            return

        split_status = self.actuation_split_mode.currentData()

        # Show/hide offshoot windows based on split mode
        if split_status == 0:  # No splits
            self.keysplit_actuation_offshoot.hide()
            self.triplesplit_actuation_offshoot.hide()
        elif split_status == 1:  # KeySplit only
            self.keysplit_actuation_offshoot.show()
            self.triplesplit_actuation_offshoot.hide()
        elif split_status == 2:  # TripleSplit only
            self.keysplit_actuation_offshoot.hide()
            self.triplesplit_actuation_offshoot.show()
        elif split_status == 3:  # Both splits
            self.keysplit_actuation_offshoot.show()
            self.triplesplit_actuation_offshoot.show()

    def on_layer_advanced_toggled(self):
        """Show/hide advanced options in layer controls"""
        shown = self.layer_widgets['advanced_checkbox'].isChecked()
        self.layer_widgets['advanced_widget'].setVisible(shown)
    
    def on_per_layer_toggled(self):
        """Handle master per-layer checkbox toggle"""
        self.per_layer_enabled = self.per_layer_checkbox.isChecked()
        self.layer_selector_container.setVisible(self.per_layer_enabled)
        
        # Enable/disable master controls based on per-layer mode
        self.master_group.setEnabled(not self.per_layer_enabled)
        
        if not self.per_layer_enabled:
            self.sync_all_to_master()
        else:
            # Load current layer data into UI
            self.load_layer_to_ui(self.current_layer)
    
    def on_layer_changed(self, index):
        """Handle layer dropdown change"""
        # Save current layer data from UI
        self.save_ui_to_layer(self.current_layer)
        
        # Update current layer
        self.current_layer = index
        
        # Update group title
        self.layer_widgets['group'].setTitle(tr("LayerActuationConfigurator", f"Layer {self.current_layer} Settings"))
        
        # Load new layer data to UI
        self.load_layer_to_ui(self.current_layer)
    
    def save_ui_to_layer(self, layer):
        """Save current UI values to layer data"""
        self.layer_data[layer]['normal'] = self.layer_widgets['normal_slider'].value()
        self.layer_data[layer]['midi'] = self.layer_widgets['midi_slider'].value()
        self.layer_data[layer]['aftertouch'] = self.layer_widgets['aftertouch_combo'].currentData()
        self.layer_data[layer]['velocity'] = self.layer_widgets['velocity_combo'].currentData()
        self.layer_data[layer]['rapid'] = self.layer_widgets['rapid_slider'].value()
        self.layer_data[layer]['midi_rapid_sens'] = self.layer_widgets['midi_rapid_sens_slider'].value()
        self.layer_data[layer]['midi_rapid_vel'] = self.layer_widgets['midi_rapid_vel_slider'].value()
        self.layer_data[layer]['vel_speed'] = self.layer_widgets['vel_speed_combo'].currentData()
        self.layer_data[layer]['aftertouch_cc'] = self.layer_widgets['aftertouch_cc_combo'].currentData()
        self.layer_data[layer]['rapidfire_enabled'] = self.layer_widgets['rapid_checkbox'].isChecked()
        self.layer_data[layer]['midi_rapidfire_enabled'] = self.layer_widgets['midi_rapid_checkbox'].isChecked()
        # HE Velocity fields
        self.layer_data[layer]['use_fixed_velocity'] = self.layer_widgets['use_fixed_vel_checkbox'].isChecked()
        self.layer_data[layer]['he_curve'] = self.layer_widgets['he_curve_combo'].currentData()
        self.layer_data[layer]['he_min'] = self.layer_widgets['he_min_slider'].value()
        self.layer_data[layer]['he_max'] = self.layer_widgets['he_max_slider'].value()
    
    def load_layer_to_ui(self, layer):
        """Load layer data to UI"""
        data = self.layer_data[layer]

        # Set sliders
        self.layer_widgets['normal_slider'].setValue(data['normal'])
        self.layer_widgets['midi_slider'].setValue(data['midi'])

        # Set combos
        for key in ['aftertouch', 'aftertouch_cc', 'velocity', 'vel_speed', 'he_curve']:
            combo = self.layer_widgets[f'{key}_combo']
            for i in range(combo.count()):
                if combo.itemData(i) == data[key]:
                    combo.setCurrentIndex(i)
                    break

        # Set rapidfire
        self.layer_widgets['rapid_checkbox'].setChecked(data['rapidfire_enabled'])
        self.layer_widgets['rapid_widget'].setVisible(data['rapidfire_enabled'])
        self.layer_widgets['rapid_slider'].setValue(data['rapid'])

        # Set MIDI rapidfire
        self.layer_widgets['midi_rapid_checkbox'].setChecked(data['midi_rapidfire_enabled'])
        self.layer_widgets['midi_rapid_sens_widget'].setVisible(data['midi_rapidfire_enabled'])
        self.layer_widgets['midi_rapid_vel_widget'].setVisible(data['midi_rapidfire_enabled'])
        self.layer_widgets['midi_rapid_sens_slider'].setValue(data['midi_rapid_sens'])
        self.layer_widgets['midi_rapid_vel_slider'].setValue(data['midi_rapid_vel'])

        # Set HE Velocity settings
        self.layer_widgets['use_fixed_vel_checkbox'].setChecked(data['use_fixed_velocity'])
        self.layer_widgets['he_min_slider'].setValue(data['he_min'])
        self.layer_widgets['he_max_slider'].setValue(data['he_max'])
    
    def on_rapidfire_toggled(self):
        """Show/hide rapidfire sensitivity based on checkbox"""
        enabled = self.master_widgets['rapid_checkbox'].isChecked()
        self.master_widgets['rapid_widget'].setVisible(enabled)
        
        if not self.per_layer_enabled:
            for layer_data in self.layer_data:
                layer_data['rapidfire_enabled'] = enabled
    
    def on_midi_rapidfire_toggled(self):
        """Show/hide MIDI rapidfire widgets based on checkbox"""
        enabled = self.master_widgets['midi_rapid_checkbox'].isChecked()
        self.master_widgets['midi_rapid_sens_widget'].setVisible(enabled)
        self.master_widgets['midi_rapid_vel_widget'].setVisible(enabled)

        if not self.per_layer_enabled:
            for layer_data in self.layer_data:
                layer_data['midi_rapidfire_enabled'] = enabled

    def on_use_fixed_velocity_toggled(self):
        """Handle Use Fixed Velocity checkbox toggle"""
        enabled = self.master_widgets['use_fixed_vel_checkbox'].isChecked()

        if not self.per_layer_enabled:
            for layer_data in self.layer_data:
                layer_data['use_fixed_velocity'] = enabled

    def on_aftertouch_mode_changed(self, combo, vibrato_sens_widget, vibrato_decay_widget):
        """Handle aftertouch mode changes - show/hide vibrato controls"""
        mode = combo.currentData()
        is_vibrato = (mode == 4)  # Mode 4 = Vibrato
        vibrato_sens_widget.setVisible(is_vibrato)
        vibrato_decay_widget.setVisible(is_vibrato)

    def on_master_slider_changed(self, key, value, label):
        """Handle master slider changes"""
        if key in ['normal', 'midi']:
            label.setText(f"{value * 0.025:.2f}mm ({value})")
        elif key == 'midi_rapid_vel':
            label.setText(f"±{value}")
        elif key == 'vibrato_sensitivity':
            label.setText(f"{value}%")
        elif key == 'vibrato_decay_time':
            label.setText(f"{value}ms")
        else:
            label.setText(str(value))
        
        # If changing normal actuation and advanced is NOT shown, also update MIDI
        if key == 'normal' and not self.advanced_shown:
            self.master_widgets['midi_slider'].setValue(value)
            self.master_widgets['midi_label'].setText(f"{value * 0.025:.2f}mm ({value})")
        
        if not self.per_layer_enabled:
            for layer_data in self.layer_data:
                layer_data[key] = value
                # Also sync MIDI when changing normal without advanced shown
                if key == 'normal' and not self.advanced_shown:
                    layer_data['midi'] = value
    
    def on_master_combo_changed(self, key, combo):
        """Handle master combo changes"""
        if not self.per_layer_enabled:
            value = combo.currentData()
            for layer_data in self.layer_data:
                layer_data[key] = value
    
    def on_layer_slider_changed(self, key, value, label):
        """Handle layer slider changes"""
        if key in ['normal', 'midi']:
            label.setText(f"{value * 0.025:.2f}mm ({value})")
        elif key == 'midi_rapid_vel':
            label.setText(f"±{value}")
        else:
            label.setText(str(value))
        
        # If changing normal actuation and advanced is NOT shown, also update MIDI
        if key == 'normal' and not self.layer_widgets['advanced_checkbox'].isChecked():
            self.layer_widgets['midi_slider'].setValue(value)
            self.layer_widgets['midi_label'].setText(f"{value * 0.025:.2f}mm ({value})")
            self.layer_data[self.current_layer]['midi'] = value
        
        # Update layer data
        self.layer_data[self.current_layer][key] = value
    
    def on_layer_combo_changed(self, key, combo):
        """Handle layer combo changes"""
        self.layer_data[self.current_layer][key] = combo.currentData()
    
    def sync_all_to_master(self):
        """Sync all layer settings to master values"""
        master_data = {
            'normal': self.master_widgets['normal_slider'].value(),
            'midi': self.master_widgets['midi_slider'].value(),
            'aftertouch': self.master_widgets['aftertouch_combo'].currentData(),
            'velocity': self.master_widgets['velocity_combo'].currentData(),
            'rapid': self.master_widgets['rapid_slider'].value(),
            'midi_rapid_sens': self.master_widgets['midi_rapid_sens_slider'].value(),
            'midi_rapid_vel': self.master_widgets['midi_rapid_vel_slider'].value(),
            'vel_speed': self.master_widgets['vel_speed_combo'].currentData(),
            'aftertouch_cc': self.master_widgets['aftertouch_cc_combo'].currentData(),
            'vibrato_sensitivity': self.master_widgets['vibrato_sensitivity_slider'].value(),
            'vibrato_decay_time': self.master_widgets['vibrato_decay_time_slider'].value(),
            'rapidfire_enabled': self.master_widgets['rapid_checkbox'].isChecked(),
            'midi_rapidfire_enabled': self.master_widgets['midi_rapid_checkbox'].isChecked(),
            # HE Velocity settings
            'use_fixed_velocity': self.master_widgets['use_fixed_vel_checkbox'].isChecked(),
            'he_curve': self.master_widgets['he_curve_combo'].currentData(),
            'he_min': self.master_widgets['he_min_slider'].value(),
            'he_max': self.master_widgets['he_max_slider'].value()
        }

        for i in range(12):
            self.layer_data[i] = master_data.copy()
    
    def get_all_actuations(self):
        """Get all actuation values as a list of dicts"""
        actuations = []
        for layer_data in self.layer_data:
            # Build flags byte
            flags = 0
            if layer_data['rapidfire_enabled']:
                flags |= 0x01
            if layer_data['midi_rapidfire_enabled']:
                flags |= 0x02
            if layer_data['use_fixed_velocity']:
                flags |= 0x04

            data_dict = {
                'normal': layer_data['normal'],
                'midi': layer_data['midi'],
                'aftertouch': layer_data.get('aftertouch', 0),
                'velocity': layer_data['velocity'],
                'rapid': layer_data['rapid'],
                'midi_rapid_sens': layer_data['midi_rapid_sens'],
                'midi_rapid_vel': layer_data['midi_rapid_vel'],
                'vel_speed': layer_data['vel_speed'],
                'aftertouch_cc': layer_data.get('aftertouch_cc', 255),
                'vibrato_sensitivity': layer_data.get('vibrato_sensitivity', 100),
                'vibrato_decay_time': layer_data.get('vibrato_decay_time', 200),
                'flags': flags,
                # HE Velocity settings
                'he_curve': layer_data['he_curve'],
                'he_min': layer_data['he_min'],
                'he_max': layer_data['he_max']
            }
            actuations.append(data_dict)
        return actuations
    
    def on_save(self):
        """Save all actuation settings to keyboard"""
        try:
            # Save current layer UI to data before saving
            if self.per_layer_enabled:
                self.save_ui_to_layer(self.current_layer)

            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")

            actuations = self.get_all_actuations()

            # Send all 12 layers (11 bytes each)
            # Protocol: [layer, normal, midi, velocity_mode, vel_speed, flags,
            #            aftertouch_mode, aftertouch_cc, vibrato_sensitivity,
            #            vibrato_decay_time_low, vibrato_decay_time_high]
            for layer, values in enumerate(actuations):
                vibrato_decay = values['vibrato_decay_time']
                data = bytearray([
                    layer,
                    values['normal'],
                    values['midi'],
                    values['velocity'],
                    values['vel_speed'],
                    values['flags'],
                    values['aftertouch'],
                    values['aftertouch_cc'],
                    values['vibrato_sensitivity'],
                    vibrato_decay & 0xFF,           # Low byte
                    (vibrato_decay >> 8) & 0xFF     # High byte
                ])

                if not self.device.keyboard.set_layer_actuation(data):
                    raise RuntimeError(f"Failed to set actuation for layer {layer}")

            QMessageBox.information(None, "Success",
                "Layer actuations saved successfully!")

        except Exception as e:
            QMessageBox.critical(None, "Error",
                f"Failed to save actuations: {str(e)}")
    
    def on_load_from_keyboard(self):
        """Load all actuation settings from keyboard"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")

            # Get all actuations (120 bytes = 12 layers × 10 bytes)
            # [normal, midi, velocity_mode, vel_speed, flags,
            #  aftertouch_mode, aftertouch_cc, vibrato_sensitivity,
            #  vibrato_decay_time_low, vibrato_decay_time_high]
            actuations = self.device.keyboard.get_all_layer_actuations()

            if not actuations or len(actuations) < 120:
                raise RuntimeError("Failed to load actuations from keyboard")

            # Check if all layers are the same
            all_same = True
            first_values = {}

            # New protocol: 10 bytes per layer
            keys = ['normal', 'midi', 'velocity', 'vel_speed', 'flags',
                    'aftertouch', 'aftertouch_cc', 'vibrato_sensitivity',
                    'vibrato_decay_low', 'vibrato_decay_high']

            for key_idx, key in enumerate(keys):
                first_values[key] = actuations[key_idx]

                for layer in range(1, 12):
                    offset = layer * 10 + key_idx
                    if actuations[offset] != first_values[key]:
                        all_same = False
                        break
                if not all_same:
                    break

            # Compute vibrato_decay_time from low/high bytes
            first_values['vibrato_decay_time'] = first_values['vibrato_decay_low'] | (first_values['vibrato_decay_high'] << 8)

            # Load into layer data
            for layer in range(12):
                offset = layer * 10
                flags = actuations[offset + 4]
                vibrato_decay = actuations[offset + 8] | (actuations[offset + 9] << 8)

                self.layer_data[layer] = {
                    'normal': actuations[offset + 0],
                    'midi': actuations[offset + 1],
                    'velocity': actuations[offset + 2],
                    'vel_speed': actuations[offset + 3],
                    'aftertouch': actuations[offset + 5],
                    'aftertouch_cc': actuations[offset + 6],
                    'vibrato_sensitivity': actuations[offset + 7],
                    'vibrato_decay_time': vibrato_decay,
                    'rapidfire_enabled': (flags & 0x01) != 0,
                    'midi_rapidfire_enabled': (flags & 0x02) != 0,
                    'use_fixed_velocity': (flags & 0x04) != 0,
                    # Defaults for fields not in new protocol (per-key now)
                    'rapid': 4,
                    'midi_rapid_sens': 4,
                    'midi_rapid_vel': 0,
                    'he_curve': 2,
                    'he_min': 1,
                    'he_max': 127
                }

            # Set master controls
            self.master_widgets['normal_slider'].setValue(first_values['normal'])
            self.master_widgets['midi_slider'].setValue(first_values['midi'])

            for key in ['aftertouch', 'aftertouch_cc', 'velocity', 'vel_speed']:
                combo = self.master_widgets[f'{key}_combo']
                for i in range(combo.count()):
                    if combo.itemData(i) == first_values[key]:
                        combo.setCurrentIndex(i)
                        break

            # Vibrato sensitivity and decay
            self.master_widgets['vibrato_sensitivity_slider'].setValue(first_values['vibrato_sensitivity'])
            self.master_widgets['vibrato_decay_time_slider'].setValue(first_values['vibrato_decay_time'])

            # Show/hide vibrato controls based on mode
            is_vibrato = (first_values['aftertouch'] == 4)
            self.master_widgets['vibrato_sensitivity_widget'].setVisible(is_vibrato)
            self.master_widgets['vibrato_decay_time_widget'].setVisible(is_vibrato)

            # Rapidfire (flags-based)
            first_flags = first_values['flags']
            rapid_enabled = (first_flags & 0x01) != 0
            self.master_widgets['rapid_checkbox'].setChecked(rapid_enabled)
            self.master_widgets['rapid_widget'].setVisible(rapid_enabled)

            # MIDI Rapidfire
            midi_rapid_enabled = (first_flags & 0x02) != 0
            self.master_widgets['midi_rapid_checkbox'].setChecked(midi_rapid_enabled)
            self.master_widgets['midi_rapid_sens_widget'].setVisible(midi_rapid_enabled)
            self.master_widgets['midi_rapid_vel_widget'].setVisible(midi_rapid_enabled)

            # HE Velocity settings (use defaults since not in layer protocol anymore)
            use_fixed_vel = (first_flags & 0x04) != 0
            self.master_widgets['use_fixed_vel_checkbox'].setChecked(use_fixed_vel)

            # Load current layer to UI if in per-layer mode
            if self.per_layer_enabled:
                self.load_layer_to_ui(self.current_layer)

            self.per_layer_checkbox.setChecked(not all_same)

            QMessageBox.information(None, "Success",
                "Layer actuations loaded successfully!")

        except Exception as e:
            QMessageBox.critical(None, "Error",
                f"Failed to load actuations: {str(e)}")
    
    def on_reset(self):
        """Reset all actuations to defaults"""
        try:
            reply = QMessageBox.question(None, "Confirm Reset", 
                "Reset all layer actuations to defaults? This cannot be undone.",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                if not self.device or not isinstance(self.device, VialKeyboard):
                    raise RuntimeError("Device not connected")
                
                if not self.device.keyboard.reset_layer_actuations():
                    raise RuntimeError("Failed to reset actuations")
                
                # Update UI to defaults
                defaults = {
                    'normal': 80,
                    'midi': 80,
                    'aftertouch': 0,
                    'velocity': 2,
                    'rapid': 4,
                    'midi_rapid_sens': 10,
                    'midi_rapid_vel': 10,
                    'vel_speed': 10,
                    'aftertouch_cc': 255,  # 255 = off (no CC sent)
                    'vibrato_sensitivity': 100,  # 100% = normal
                    'vibrato_decay_time': 200,   # 200ms decay
                    'rapidfire_enabled': False,
                    'midi_rapidfire_enabled': False,
                    'use_fixed_velocity': False,
                    'he_curve': 2,
                    'he_min': 1,
                    'he_max': 127
                }

                # Reset master
                self.master_widgets['normal_slider'].setValue(defaults['normal'])
                self.master_widgets['midi_slider'].setValue(defaults['midi'])

                for key in ['aftertouch', 'aftertouch_cc', 'velocity', 'vel_speed']:
                    combo = self.master_widgets[f'{key}_combo']
                    for i in range(combo.count()):
                        if combo.itemData(i) == defaults[key]:
                            combo.setCurrentIndex(i)
                            break

                # Vibrato controls
                self.master_widgets['vibrato_sensitivity_slider'].setValue(defaults['vibrato_sensitivity'])
                self.master_widgets['vibrato_decay_time_slider'].setValue(defaults['vibrato_decay_time'])
                self.master_widgets['vibrato_sensitivity_widget'].setVisible(False)
                self.master_widgets['vibrato_decay_time_widget'].setVisible(False)

                self.master_widgets['rapid_checkbox'].setChecked(False)
                self.master_widgets['rapid_widget'].setVisible(False)
                self.master_widgets['rapid_slider'].setValue(defaults['rapid'])

                self.master_widgets['midi_rapid_checkbox'].setChecked(False)
                self.master_widgets['midi_rapid_sens_widget'].setVisible(False)
                self.master_widgets['midi_rapid_vel_widget'].setVisible(False)
                self.master_widgets['midi_rapid_sens_slider'].setValue(defaults['midi_rapid_sens'])
                self.master_widgets['midi_rapid_vel_slider'].setValue(defaults['midi_rapid_vel'])

                # Reset all layer data
                for i in range(12):
                    self.layer_data[i] = defaults.copy()
                
                # Reload current layer to UI if in per-layer mode
                if self.per_layer_enabled:
                    self.load_layer_to_ui(self.current_layer)
                
                self.per_layer_checkbox.setChecked(False)
                
                QMessageBox.information(None, "Success", 
                    "Layer actuations reset to defaults!")
                    
        except Exception as e:
            QMessageBox.critical(None, "Error", 
                f"Failed to reset actuations: {str(e)}")
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        # Load actuation settings from keyboard
        self.on_load_from_keyboard_silent()

    def on_load_from_keyboard_silent(self):
        """Load settings without showing success message"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            return
        
        actuations = self.device.keyboard.get_all_layer_actuations()
        
        if not actuations or len(actuations) != 120:
            return
        
        # Parse and apply (same logic as on_load_from_keyboard but silent)
        all_same = True
        first_values = {}
        
        for key_idx, key in enumerate(['normal', 'midi', 'aftertouch', 'velocity', 'rapid', 
                                      'midi_rapid_sens', 'midi_rapid_vel', 'vel_speed', 
                                      'aftertouch_cc', 'flags']):
            first_values[key] = actuations[key_idx]
            
            for layer in range(1, 12):
                offset = layer * 10 + key_idx
                if actuations[offset] != first_values[key]:
                    all_same = False
                    break
            if not all_same:
                break
        
        for layer in range(12):
            offset = layer * 10
            flags = actuations[offset + 9]
            
            self.layer_data[layer] = {
                'normal': actuations[offset + 0],
                'midi': actuations[offset + 1],
                'aftertouch': actuations[offset + 2],
                'velocity': actuations[offset + 3],
                'rapid': actuations[offset + 4],
                'midi_rapid_sens': actuations[offset + 5],
                'midi_rapid_vel': actuations[offset + 6],
                'vel_speed': actuations[offset + 7],
                'aftertouch_cc': actuations[offset + 8],
                'rapidfire_enabled': (flags & 0x01) != 0,
                'midi_rapidfire_enabled': (flags & 0x02) != 0
            }
        
        self.master_widgets['normal_slider'].setValue(first_values['normal'])
        self.master_widgets['midi_slider'].setValue(first_values['midi'])
        
        for key in ['aftertouch', 'aftertouch_cc', 'velocity', 'vel_speed']:
            combo = self.master_widgets[f'{key}_combo']
            for i in range(combo.count()):
                if combo.itemData(i) == first_values[key]:
                    combo.setCurrentIndex(i)
                    break
        
        first_flags = first_values['flags']
        rapid_enabled = (first_flags & 0x01) != 0
        self.master_widgets['rapid_checkbox'].setChecked(rapid_enabled)
        self.master_widgets['rapid_widget'].setVisible(rapid_enabled)
        self.master_widgets['rapid_slider'].setValue(first_values['rapid'])
        
        midi_rapid_enabled = (first_flags & 0x02) != 0
        self.master_widgets['midi_rapid_checkbox'].setChecked(midi_rapid_enabled)
        self.master_widgets['midi_rapid_sens_widget'].setVisible(midi_rapid_enabled)
        self.master_widgets['midi_rapid_vel_widget'].setVisible(midi_rapid_enabled)
        self.master_widgets['midi_rapid_sens_slider'].setValue(first_values['midi_rapid_sens'])
        self.master_widgets['midi_rapid_vel_slider'].setValue(first_values['midi_rapid_vel'])
        
        if self.per_layer_enabled:
            self.load_layer_to_ui(self.current_layer)
        
        self.per_layer_checkbox.setChecked(not all_same)




class GamingConfigurator(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None
        self.gaming_controls = {}
        self.active_control_id = None  # Track which control is being assigned
        self._needs_loading = False  # Flag for lazy loading - defer heavy HID calls until tab is opened
        self.setup_ui()

    def create_help_label(self, tooltip_text):
        """Create a small question mark button with tooltip for help"""
        help_btn = QPushButton("?")
        help_btn.setStyleSheet("""
            QPushButton {
                color: #888;
                font-weight: bold;
                font-size: 9pt;
                border: 1px solid #888;
                border-radius: 9px;
                min-width: 16px;
                max-width: 16px;
                min-height: 16px;
                max-height: 16px;
                padding: 0px;
                margin: 0px;
                background: transparent;
            }
            QPushButton:hover {
                color: #fff;
                background-color: #555;
                border-color: #fff;
            }
        """)
        help_btn.setToolTip(tooltip_text)
        help_btn.setFocusPolicy(Qt.NoFocus)
        return help_btn

    def setup_ui(self):
        # Create scroll area for better window resizing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        scroll_area.setWidget(main_widget)
        self.addWidget(scroll_area)

        # Create horizontal layout: Settings (title+desc+response+calibration) | Gamepad | Curve
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        main_layout.addLayout(controls_layout)

        # COLUMN 1: Title, Description, and Response+Calibration side by side
        settings_column = QVBoxLayout()
        settings_column.setSpacing(8)

        # Title at top
        title_label = QLabel(tr("GamingConfigurator", "Gaming Mode"))
        title_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        settings_column.addWidget(title_label)

        # Description below title
        desc_label = QLabel(tr("GamingConfigurator",
            "Assign keyboard keys to gamepad buttons. "
            "Assigned keys will act as gamepad inputs when Gaming Mode is enabled, "
            "and function normally when disabled. "
            "Click a button on the controller, then select a key from the keycodes below."))
        desc_label.setWordWrap(True)
        desc_label.setMaximumWidth(400)
        desc_label.setStyleSheet("color: gray; font-size: 9pt;")
        settings_column.addWidget(desc_label)

        # Horizontal layout for Response and Calibration side by side
        response_calibration_layout = QHBoxLayout()
        response_calibration_layout.setSpacing(8)

        # Gamepad Response Section
        response_group = QGroupBox(tr("GamingConfigurator", "Gamepad Response"))
        response_group.setMaximumWidth(200)
        response_layout = QVBoxLayout()
        response_layout.setSpacing(4)
        response_group.setLayout(response_layout)

        # Angle Adjustment
        angle_adj_row = QHBoxLayout()
        angle_adj_row.addWidget(self.create_help_label("Enable diagonal angle adjustment.\nModifies the angle at which diagonals are registered."))
        self.angle_adj_checkbox = QCheckBox(tr("GamingConfigurator", "Angle adjustment"))
        angle_adj_row.addWidget(self.angle_adj_checkbox)
        angle_adj_row.addStretch()
        response_layout.addLayout(angle_adj_row)

        # Diagonal Angle Slider
        angle_widget = QWidget()
        angle_layout = QVBoxLayout()
        angle_layout.setSpacing(2)
        angle_layout.setContentsMargins(15, 0, 0, 0)  # Indent
        angle_widget.setLayout(angle_layout)

        angle_label_row = QHBoxLayout()
        angle_label_row.addWidget(self.create_help_label("Angle offset for diagonal detection (0-90°).\nHigher values make diagonals easier to hit."))
        self.diagonal_angle_label = QLabel("Angle: 0°")
        angle_label_row.addWidget(self.diagonal_angle_label)
        angle_label_row.addStretch()
        angle_layout.addLayout(angle_label_row)

        self.diagonal_angle_slider = QSlider(Qt.Horizontal)
        self.diagonal_angle_slider.setMinimum(0)
        self.diagonal_angle_slider.setMaximum(90)
        self.diagonal_angle_slider.setValue(0)
        self.diagonal_angle_slider.setTickInterval(10)
        self.diagonal_angle_slider.valueChanged.connect(
            lambda val: self.diagonal_angle_label.setText(f"Angle: {val}°")
        )
        angle_layout.addWidget(self.diagonal_angle_slider)
        response_layout.addWidget(angle_widget)

        # Square Output
        square_row = QHBoxLayout()
        square_row.addWidget(self.create_help_label(
            "Restrict joystick movement to a square instead of circle.\n"
            "Allows maximum axis output. Recommended for Rocket League and CS:GO."))
        self.square_output_checkbox = QCheckBox(tr("GamingConfigurator", "Square output"))
        square_row.addWidget(self.square_output_checkbox)
        square_row.addStretch()
        response_layout.addLayout(square_row)

        # Snappy Joystick
        snappy_row = QHBoxLayout()
        snappy_row.addWidget(self.create_help_label(
            "Use maximum value of opposite sides of axis rather than combining them."))
        self.snappy_joystick_checkbox = QCheckBox(tr("GamingConfigurator", "Snappy Joystick"))
        snappy_row.addWidget(self.snappy_joystick_checkbox)
        snappy_row.addStretch()
        response_layout.addLayout(snappy_row)

        response_calibration_layout.addWidget(response_group, alignment=QtCore.Qt.AlignTop)

        # Analog Calibration Group
        calibration_group = QGroupBox(tr("GamingConfigurator", "Analog Calibration"))
        calibration_group.setMaximumWidth(400)
        calibration_layout = QVBoxLayout()
        calibration_layout.setSpacing(6)
        calibration_group.setLayout(calibration_layout)

        # Helper function to create stacked slider pair (min on top, max below)
        def create_minmax_slider_row(section_name, default_min, default_max):
            container = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(2)
            layout.setContentsMargins(0, 0, 0, 0)
            container.setLayout(layout)

            section_label = QLabel(f"<b>{section_name}</b>")
            layout.addWidget(section_label)

            # Min slider
            min_label = QLabel(f"Min: {default_min/100:.2f}mm")
            min_label.setStyleSheet("font-size: 8pt;")
            layout.addWidget(min_label)

            min_slider = QSlider(Qt.Horizontal)
            min_slider.setMinimum(0)
            min_slider.setMaximum(250)  # 0.00 to 2.50mm in 0.01mm increments
            min_slider.setValue(default_min)
            min_slider.valueChanged.connect(
                lambda val, lbl=min_label: lbl.setText(f"Min: {val/100:.2f}mm")
            )
            layout.addWidget(min_slider)

            # Max slider
            max_label = QLabel(f"Max: {default_max/100:.2f}mm")
            max_label.setStyleSheet("font-size: 8pt;")
            layout.addWidget(max_label)

            max_slider = QSlider(Qt.Horizontal)
            max_slider.setMinimum(0)
            max_slider.setMaximum(250)  # 0.00 to 2.50mm in 0.01mm increments
            max_slider.setValue(default_max)
            max_slider.valueChanged.connect(
                lambda val, lbl=max_label: lbl.setText(f"Max: {val/100:.2f}mm")
            )
            layout.addWidget(max_slider)

            return container, min_slider, max_slider, min_label, max_label

        # LS (Left Stick) Calibration
        ls_widget, self.ls_min_travel_slider, self.ls_max_travel_slider, self.ls_min_travel_label, self.ls_max_travel_label = create_minmax_slider_row(
            tr("GamingConfigurator", "Left Stick"), 100, 200
        )
        calibration_layout.addWidget(ls_widget)

        # RS (Right Stick) Calibration
        rs_widget, self.rs_min_travel_slider, self.rs_max_travel_slider, self.rs_min_travel_label, self.rs_max_travel_label = create_minmax_slider_row(
            tr("GamingConfigurator", "Right Stick"), 100, 200
        )
        calibration_layout.addWidget(rs_widget)

        # Triggers Calibration
        trigger_widget, self.trigger_min_travel_slider, self.trigger_max_travel_slider, self.trigger_min_travel_label, self.trigger_max_travel_label = create_minmax_slider_row(
            tr("GamingConfigurator", "Triggers"), 100, 200
        )
        calibration_layout.addWidget(trigger_widget)

        response_calibration_layout.addWidget(calibration_group, alignment=QtCore.Qt.AlignTop)

        settings_column.addLayout(response_calibration_layout)
        settings_column.addStretch()

        controls_layout.addLayout(settings_column)

        # COLUMN 3: Gamepad widget with drawn outline
        gamepad_widget = GamepadWidget()
        gamepad_widget.setFixedSize(750, 560)
        controls_layout.addWidget(gamepad_widget)

        # RIGHT COLUMN: Analog Curve
        from widgets.curve_editor import CurveEditorWidget
        curve_group = QGroupBox(tr("GamingConfigurator", "Analog Curve"))
        curve_group.setMaximumWidth(320)
        curve_group_layout = QVBoxLayout()
        curve_group.setLayout(curve_group_layout)

        self.curve_editor = CurveEditorWidget(show_save_button=True)
        self.curve_editor.curve_changed.connect(self.on_curve_changed)
        self.curve_editor.save_to_user_requested.connect(self.on_save_curve_to_user)
        self.curve_editor.user_curve_selected.connect(self.on_user_curve_selected)
        curve_group_layout.addWidget(self.curve_editor)

        controls_layout.addWidget(curve_group, alignment=QtCore.Qt.AlignTop)

        # Map control IDs to positions and names (matching the original control IDs)
        control_mapping = {
            # D-pad
            10: ("D-pad Up", "dpad_up", 180, 105, 56, 58, "↑"),
            11: ("D-pad Down", "dpad_down", 180, 163, 56, 58, "↓"),
            12: ("D-pad Left", "dpad_left", 150, 135, 58, 56, "←"),
            13: ("D-pad Right", "dpad_right", 208, 135, 58, 56, "→"),
            # Face buttons
            14: ("Button 1", "btn1", 517, 178, 50, 50, "1"),  # A
            15: ("Button 2", "btn2", 553, 139, 50, 50, "2"),  # B
            16: ("Button 3", "btn3", 481, 139, 50, 50, "3"),  # X
            17: ("Button 4", "btn4", 517, 103, 50, 50, "4"),  # Y
            # Sticks
            0: ("LS Up", "ls_up", 275, 185, 38, 38, "↑"),
            1: ("LS Down", "ls_down", 275, 261, 38, 38, "↓"),
            2: ("LS Left", "ls_left", 237, 223, 38, 38, "←"),
            3: ("LS Right", "ls_right", 313, 223, 38, 38, "→"),
            22: ("LS Click", "l3", 275, 223, 38, 38, "L3"),
            4: ("RS Up", "rs_up", 439, 185, 38, 38, "↑"),
            5: ("RS Down", "rs_down", 439, 261, 38, 38, "↓"),
            6: ("RS Left", "rs_left", 401, 223, 38, 38, "←"),
            7: ("RS Right", "rs_right", 477, 223, 38, 38, "→"),
            23: ("RS Click", "r3", 439, 223, 38, 38, "R3"),
            # Bumpers and triggers
            18: ("LB", "lb", 177, 65, 60, 30, "LB"),
            19: ("RB", "rb", 503, 65, 60, 30, "RB"),
            8: ("LT", "lt", 177, 25, 60, 35, "LT"),
            9: ("RT", "rt", 503, 25, 60, 35, "RT"),
            # Center buttons
            20: ("Back", "back", 320, 170, 50, 30, "Back"),
            21: ("Start", "start", 380, 170, 50, 30, "Start"),
        }

        # Create buttons positioned over gamepad
        for control_id, (name, key, x, y, w, h, text) in control_mapping.items():
            # Create button based on type
            if "dpad" in key:
                # Use DpadButton for d-pad with shaped paths
                btn = DpadButton("Not Set")
                btn.setFixedSize(w, h)
                btn.setParent(gamepad_widget)
                btn.move(x, y)

                # Set shaped path for d-pad buttons
                path = QPainterPath()
                if key == "dpad_up":
                    path.moveTo(28, 58)
                    path.lineTo(3, 33)
                    path.lineTo(3, 8)
                    path.quadTo(8, 3, 15, 3)
                    path.lineTo(41, 3)
                    path.quadTo(48, 3, 53, 8)
                    path.lineTo(53, 33)
                    path.lineTo(28, 58)
                    path.closeSubpath()
                elif key == "dpad_down":
                    path.moveTo(28, 0)
                    path.lineTo(3, 25)
                    path.lineTo(3, 50)
                    path.quadTo(8, 55, 15, 55)
                    path.lineTo(41, 55)
                    path.quadTo(48, 55, 53, 50)
                    path.lineTo(53, 25)
                    path.lineTo(28, 0)
                    path.closeSubpath()
                elif key == "dpad_left":
                    path.moveTo(58, 28)
                    path.lineTo(33, 3)
                    path.lineTo(8, 3)
                    path.quadTo(3, 8, 3, 15)
                    path.lineTo(3, 41)
                    path.quadTo(3, 48, 8, 53)
                    path.lineTo(33, 53)
                    path.lineTo(58, 28)
                    path.closeSubpath()
                elif key == "dpad_right":
                    path.moveTo(0, 28)
                    path.lineTo(25, 3)
                    path.lineTo(50, 3)
                    path.quadTo(55, 8, 55, 15)
                    path.lineTo(55, 41)
                    path.quadTo(55, 48, 50, 53)
                    path.lineTo(25, 53)
                    path.lineTo(0, 28)
                    path.closeSubpath()

                btn.setMask(QRegion(path.toFillPolygon().toPolygon()))
                btn.set_border_path(path)
            elif "btn" in key and key in ["btn1", "btn2", "btn3", "btn4"]:
                # Circular face buttons (exactly like GamingTab)
                btn = QPushButton("Not Set")
                btn.setFixedSize(w, h)
                btn.setParent(gamepad_widget)
                btn.move(x, y)
                btn.setStyleSheet("border-radius: 25px;")
            else:
                # Regular rectangular buttons (no special styling, exactly like GamingTab)
                btn = QPushButton("Not Set")
                btn.setFixedSize(w, h)
                btn.setParent(gamepad_widget)
                btn.move(x, y)

            btn.clicked.connect(lambda checked, cid=control_id: self.on_assign_key(cid))
            btn.setProperty("control_id", control_id)

            # Store reference with button type
            button_type = "dpad" if "dpad" in key else ("face" if key in ["btn1", "btn2", "btn3", "btn4"] else "regular")
            self.gaming_controls[control_id] = {
                'button': btn,
                'button_type': button_type,
                'keycode': None,
                'row': None,
                'col': None,
                'enabled': False
            }

        # Add outer stretch on the right
        controls_layout.addStretch(1)

        # Buttons
        main_layout.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Button style
        button_style = "QPushButton { border-radius: 3px; padding: 8px 16px; }"

        save_btn = QPushButton(tr("GamingConfigurator", "Save Configuration"))
        save_btn.setMinimumHeight(45)
        save_btn.setMinimumWidth(200)
        save_btn.setStyleSheet(button_style)
        save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_btn)

        load_btn = QPushButton(tr("GamingConfigurator", "Load from Keyboard"))
        load_btn.setMinimumHeight(45)
        load_btn.setMinimumWidth(210)
        load_btn.setStyleSheet(button_style)
        load_btn.clicked.connect(self.on_load_from_keyboard)
        buttons_layout.addWidget(load_btn)

        reset_btn = QPushButton(tr("GamingConfigurator", "Reset to Defaults"))
        reset_btn.setMinimumHeight(45)
        reset_btn.setMinimumWidth(180)
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)

        main_layout.addLayout(buttons_layout)

        # Add TabbedKeycodes at the bottom like in Macros tab
        from tabbed_keycodes import TabbedKeycodes
        self.tabbed_keycodes = TabbedKeycodes()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_selected)
        self.addWidget(self.tabbed_keycodes)

        # Apply stylesheet
        main_widget.setStyleSheet("""
            QCheckBox:focus {
                font-weight: normal;
                outline: none;
            }
            QPushButton:focus {
                font-weight: normal;
                outline: none;
            }
        """)

    def get_button_style(self, button_type, highlighted=False):
        """Get the appropriate style for a button based on its type"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QPalette

        if button_type == "face":
            # Face buttons are circular
            base_style = "border-radius: 25px;"
        elif button_type == "dpad":
            # D-pad buttons don't have inline styles (they use masks)
            base_style = ""
        else:
            # Regular buttons have no special styling
            base_style = ""

        if highlighted:
            # Use theme colors for highlighting
            palette = QApplication.palette()
            highlight_color = palette.color(QPalette.Highlight).name()
            highlight_text = palette.color(QPalette.HighlightedText).name()
            return f"QPushButton {{ {base_style} background-color: {highlight_color}; color: {highlight_text}; }}"
        else:
            # Return empty stylesheet to clear any previous styling (except base_style)
            return f"QPushButton {{ {base_style} }}"

    def on_assign_key(self, control_id):
        """Handle key assignment for a gaming control"""
        self.active_control_id = control_id
        # Highlight the button being assigned and unhighlight all others
        for cid, data in self.gaming_controls.items():
            button_type = data.get('button_type', 'regular')
            if cid == control_id:
                data['button'].setStyleSheet(self.get_button_style(button_type, highlighted=True))
            else:
                # Always set style to clear any previous highlighting
                data['button'].setStyleSheet(self.get_button_style(button_type, highlighted=False))

    def on_keycode_selected(self, keycode):
        """Called when a keycode is selected from TabbedKeycodes"""
        if self.active_control_id is None or not self.keyboard:
            return

        # Find the physical position (row, col) of this keycode - search ALL layers
        row, col = self.find_keycode_position(keycode)

        if row is not None and col is not None:
            # Assign to the active control
            data = self.gaming_controls[self.active_control_id]
            data['keycode'] = keycode
            data['row'] = row
            data['col'] = col
            data['enabled'] = True

            # Update button text to show the keycode label
            from keycodes.keycodes import Keycode
            label = Keycode.label(keycode)
            # Truncate label to fit in 50x50 button
            if len(label) > 7:
                label = label[:6] + ".."
            data['button'].setText(label)

            # Reset button style based on its type (clears highlighting)
            button_type = data.get('button_type', 'regular')
            data['button'].setStyleSheet(self.get_button_style(button_type, highlighted=False))

            # Clear active control
            self.active_control_id = None
        else:
            # Keycode not found in any layer - show error
            QMessageBox.warning(None, "Key Not Found",
                              f"The selected keycode is not found in your keymap on any layer.\n"
                              f"Please select a key that exists in your keymap.")
            # Reset the button style (clears highlighting)
            data = self.gaming_controls[self.active_control_id]
            button_type = data.get('button_type', 'regular')
            data['button'].setStyleSheet(self.get_button_style(button_type, highlighted=False))
            self.active_control_id = None

    def find_keycode_position(self, keycode):
        """Find the matrix position (row, col) of a keycode - searches ALL layers"""
        if not self.keyboard:
            return None, None

        # Search through ALL layers for this keycode (prefer layer 0 first)
        for (layer, row, col), kc in sorted(self.keyboard.layout.items()):
            if kc == keycode:
                return row, col

        return None, None

    def on_save(self):
        """Save gaming configuration to keyboard"""
        if not self.keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        try:
            # Save analog configuration - separate for LS, RS, and Triggers
            ls_min = self.ls_min_travel_slider.value()
            ls_max = self.ls_max_travel_slider.value()
            rs_min = self.rs_min_travel_slider.value()
            rs_max = self.rs_max_travel_slider.value()
            trigger_min = self.trigger_min_travel_slider.value()
            trigger_max = self.trigger_max_travel_slider.value()

            # Validate ranges
            if ls_min >= ls_max:
                QMessageBox.warning(None, "Invalid Range", "LS Min travel must be less than LS Max travel")
                return
            if rs_min >= rs_max:
                QMessageBox.warning(None, "Invalid Range", "RS Min travel must be less than RS Max travel")
                return
            if trigger_min >= trigger_max:
                QMessageBox.warning(None, "Invalid Range", "Trigger Min travel must be less than Trigger Max travel")
                return

            success = self.keyboard.set_gaming_analog_config(ls_min, ls_max, rs_min, rs_max, trigger_min, trigger_max)

            # Save key mappings
            for control_id, data in self.gaming_controls.items():
                if data['enabled'] and data['row'] is not None and data['col'] is not None:
                    self.keyboard.set_gaming_key_map(control_id, data['row'], data['col'], 1)
                else:
                    self.keyboard.set_gaming_key_map(control_id, 0, 0, 0)

            # Save gamepad response settings
            angle_adj_enabled = self.angle_adj_checkbox.isChecked()
            diagonal_angle = self.diagonal_angle_slider.value()
            square_output = self.square_output_checkbox.isChecked()
            snappy_joystick = self.snappy_joystick_checkbox.isChecked()

            # Get current curve index from preset combo
            current_curve_index = self.curve_editor.preset_combo.currentData()
            if current_curve_index is None or current_curve_index < 0:
                current_curve_index = 0  # Default to linear

            response_success = self.keyboard.set_gaming_response(
                angle_adj_enabled, diagonal_angle, square_output, snappy_joystick, current_curve_index
            )

            if success and response_success:
                QMessageBox.information(None, "Success", "Gaming configuration saved successfully")
            else:
                QMessageBox.warning(None, "Error", "Failed to save gaming configuration")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error saving configuration: {str(e)}")

    def on_load_from_keyboard(self):
        """Load gaming configuration from keyboard"""
        if not self.keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        try:
            settings = self.keyboard.get_gaming_settings()
            if settings:
                # Block signals while updating
                self.ls_min_travel_slider.blockSignals(True)
                self.ls_max_travel_slider.blockSignals(True)
                self.rs_min_travel_slider.blockSignals(True)
                self.rs_max_travel_slider.blockSignals(True)
                self.trigger_min_travel_slider.blockSignals(True)
                self.trigger_max_travel_slider.blockSignals(True)

                # Set values for LS/RS/Triggers
                self.ls_min_travel_slider.setValue(settings.get('ls_min_travel_mm_x10', 10))
                self.ls_max_travel_slider.setValue(settings.get('ls_max_travel_mm_x10', 20))
                self.rs_min_travel_slider.setValue(settings.get('rs_min_travel_mm_x10', 10))
                self.rs_max_travel_slider.setValue(settings.get('rs_max_travel_mm_x10', 20))
                self.trigger_min_travel_slider.setValue(settings.get('trigger_min_travel_mm_x10', 10))
                self.trigger_max_travel_slider.setValue(settings.get('trigger_max_travel_mm_x10', 20))

                self.ls_min_travel_slider.blockSignals(False)
                self.ls_max_travel_slider.blockSignals(False)
                self.rs_min_travel_slider.blockSignals(False)
                self.rs_max_travel_slider.blockSignals(False)
                self.trigger_min_travel_slider.blockSignals(False)
                self.trigger_max_travel_slider.blockSignals(False)

                # Update labels (with inline format)
                self.ls_min_travel_label.setText(f"Min Travel (mm): {settings.get('ls_min_travel_mm_x10', 10)/10:.1f}")
                self.ls_max_travel_label.setText(f"Max Travel (mm): {settings.get('ls_max_travel_mm_x10', 20)/10:.1f}")
                self.rs_min_travel_label.setText(f"Min Travel (mm): {settings.get('rs_min_travel_mm_x10', 10)/10:.1f}")
                self.rs_max_travel_label.setText(f"Max Travel (mm): {settings.get('rs_max_travel_mm_x10', 20)/10:.1f}")
                self.trigger_min_travel_label.setText(f"Min Travel (mm): {settings.get('trigger_min_travel_mm_x10', 10)/10:.1f}")
                self.trigger_max_travel_label.setText(f"Max Travel (mm): {settings.get('trigger_max_travel_mm_x10', 20)/10:.1f}")

                # Load user curve names first (so dropdown is populated)
                user_curve_names = self.keyboard.get_all_user_curve_names()
                if user_curve_names and len(user_curve_names) == 10:
                    self.curve_editor.set_user_curve_names(user_curve_names)

                # Load gamepad response settings
                response = self.keyboard.get_gaming_response()
                if response:
                    self.angle_adj_checkbox.setChecked(response.get('angle_adj_enabled', False))
                    self.diagonal_angle_slider.setValue(response.get('diagonal_angle', 0))
                    self.diagonal_angle_label.setText(f"Diagonal Angle: {response.get('diagonal_angle', 0)}°")
                    self.square_output_checkbox.setChecked(response.get('square_output', False))
                    self.snappy_joystick_checkbox.setChecked(response.get('snappy_joystick', False))

                    # Select curve in combo box
                    curve_index = response.get('curve_index', 0)
                    self.curve_editor.select_curve(curve_index)

                    # If it's a user curve (7-16), load the actual points
                    if curve_index >= 7 and curve_index <= 16:
                        slot_index = curve_index - 7
                        curve_data = self.keyboard.get_user_curve(slot_index)
                        if curve_data and 'points' in curve_data:
                            self.curve_editor.load_user_curve_points(curve_data['points'])

                QMessageBox.information(None, "Success", "Gaming configuration loaded from keyboard")
            else:
                QMessageBox.warning(None, "Error", "Failed to load gaming configuration")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error loading configuration: {str(e)}")

    def on_reset(self):
        """Reset gaming configuration to defaults"""
        if not self.keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        reply = QMessageBox.question(None, "Confirm Reset",
                                     "Reset gaming configuration to defaults?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                success = self.keyboard.reset_gaming_settings()
                if success:
                    self.on_load_from_keyboard()
                    # Clear all assignments
                    for data in self.gaming_controls.values():
                        data['button'].setText("Not Set")
                        data['button'].setStyleSheet("QPushButton { text-align: center; border-radius: 3px; font-size: 9px; }")
                        data['keycode'] = None
                        data['row'] = None
                        data['col'] = None
                        data['enabled'] = False
                    QMessageBox.information(None, "Success", "Gaming configuration reset to defaults")
                else:
                    QMessageBox.warning(None, "Error", "Failed to reset gaming configuration")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Error resetting configuration: {str(e)}")

    def on_curve_changed(self, points):
        """Called when curve points are changed - IMMEDIATE SAVE for analog curves"""
        if not self.keyboard:
            return

        # Get curve index from preset combo (0-16 or -1 for custom)
        curve_index = self.curve_editor.get_selected_curve_index()
        if curve_index is None or curve_index < 0:
            # Custom curve - user needs to save to a user slot first
            return

        try:
            # Get current response settings and update with new curve index
            response = self.keyboard.get_gaming_response()
            if response:
                self.keyboard.set_gaming_response(
                    response['angle_adj_enabled'],
                    response['diagonal_angle'],
                    response['square_output'],
                    response['snappy_joystick'],
                    curve_index
                )
        except Exception as e:
            print(f"Error saving analog curve: {e}")

    def on_user_curve_selected(self, slot_index):
        """Handle user curve selection - load curve points from keyboard and save immediately"""
        if not self.keyboard:
            return

        try:
            # Fetch user curve from keyboard
            curve_data = self.keyboard.get_user_curve(slot_index)
            if curve_data and 'points' in curve_data:
                # Load points into editor and cache for later (pass slot_index for caching)
                self.curve_editor.load_user_curve_points(curve_data['points'], slot_index)

                # Save with the correct curve index (7 + slot_index)
                curve_index = 7 + slot_index
                response = self.keyboard.get_gaming_response()
                if response:
                    self.keyboard.set_gaming_response(
                        response['angle_adj_enabled'],
                        response['diagonal_angle'],
                        response['square_output'],
                        response['snappy_joystick'],
                        curve_index
                    )
        except Exception as e:
            print(f"Error loading user curve: {e}")

    def on_save_curve_to_user(self, slot_index, curve_name):
        """Called when user wants to save current curve to a user slot"""
        if not self.keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        try:
            # Get current curve points
            points = self.curve_editor.get_points()

            # Save to keyboard
            success = self.keyboard.set_user_curve(slot_index, points, curve_name)

            if success:
                QMessageBox.information(None, "Success",
                                      f"Curve saved to {curve_name}")

                # Reload user curve names to show the updated name
                user_curve_names = self.keyboard.get_all_user_curve_names()
                if user_curve_names and len(user_curve_names) == 10:
                    self.curve_editor.set_user_curve_names(user_curve_names)

                # Select the newly saved curve (curve index = 7 + slot_index)
                self.curve_editor.select_curve(7 + slot_index)

                # Immediately save to gaming response
                curve_index = 7 + slot_index
                response = self.keyboard.get_gaming_response()
                if response:
                    self.keyboard.set_gaming_response(
                        response['angle_adj_enabled'],
                        response['diagonal_angle'],
                        response['square_output'],
                        response['snappy_joystick'],
                        curve_index
                    )
            else:
                QMessageBox.warning(None, "Error", "Failed to save curve")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error saving curve: {str(e)}")

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            # Set keyboard reference for tabbed keycodes (so GamingTab can access it)
            self.tabbed_keycodes.set_keyboard(self.keyboard)
            self.tabbed_keycodes.recreate_keycode_buttons()
            # Defer gaming data loading until tab is actually opened (lazy loading)
            self._needs_loading = True

    def activate(self):
        """Called when tab is selected - load heavy data if needed"""
        if self._needs_loading and self.keyboard:
            self._load_gaming_data()
            self._needs_loading = False

    def _load_gaming_data(self):
        """Load gaming settings from device (heavy operation - multiple HID calls)"""
        print("GamingConfigurator: Loading gaming data (this may take a while)...")
        try:
            # Use cached gaming settings if available, otherwise fetch them
            settings = getattr(self.keyboard, 'gaming_settings', None) or self.keyboard.get_gaming_settings()
            if settings:
                # Block signals while updating
                self.ls_min_travel_slider.blockSignals(True)
                self.ls_max_travel_slider.blockSignals(True)
                self.rs_min_travel_slider.blockSignals(True)
                self.rs_max_travel_slider.blockSignals(True)
                self.trigger_min_travel_slider.blockSignals(True)
                self.trigger_max_travel_slider.blockSignals(True)

                self.ls_min_travel_slider.setValue(settings.get('ls_min_travel_mm_x10', 10))
                self.ls_max_travel_slider.setValue(settings.get('ls_max_travel_mm_x10', 20))
                self.rs_min_travel_slider.setValue(settings.get('rs_min_travel_mm_x10', 10))
                self.rs_max_travel_slider.setValue(settings.get('rs_max_travel_mm_x10', 20))
                self.trigger_min_travel_slider.setValue(settings.get('trigger_min_travel_mm_x10', 10))
                self.trigger_max_travel_slider.setValue(settings.get('trigger_max_travel_mm_x10', 20))

                self.ls_min_travel_slider.blockSignals(False)
                self.ls_max_travel_slider.blockSignals(False)
                self.rs_min_travel_slider.blockSignals(False)
                self.rs_max_travel_slider.blockSignals(False)
                self.trigger_min_travel_slider.blockSignals(False)
                self.trigger_max_travel_slider.blockSignals(False)

                # Update labels (with inline format)
                self.ls_min_travel_label.setText(f"Min Travel (mm): {settings.get('ls_min_travel_mm_x10', 10)/10:.1f}")
                self.ls_max_travel_label.setText(f"Max Travel (mm): {settings.get('ls_max_travel_mm_x10', 20)/10:.1f}")
                self.rs_min_travel_label.setText(f"Min Travel (mm): {settings.get('rs_min_travel_mm_x10', 10)/10:.1f}")
                self.rs_max_travel_label.setText(f"Max Travel (mm): {settings.get('rs_max_travel_mm_x10', 20)/10:.1f}")
                self.trigger_min_travel_label.setText(f"Min Travel (mm): {settings.get('trigger_min_travel_mm_x10', 10)/10:.1f}")
                self.trigger_max_travel_label.setText(f"Max Travel (mm): {settings.get('trigger_max_travel_mm_x10', 20)/10:.1f}")

            # Load user curve names (so dropdown is populated)
            user_curve_names = self.keyboard.get_all_user_curve_names()
            if user_curve_names and len(user_curve_names) == 10:
                self.curve_editor.set_user_curve_names(user_curve_names)

            # Load gamepad response settings including curve
            response = self.keyboard.get_gaming_response()
            if response:
                self.angle_adj_checkbox.blockSignals(True)
                self.diagonal_angle_slider.blockSignals(True)
                self.square_output_checkbox.blockSignals(True)
                self.snappy_joystick_checkbox.blockSignals(True)

                self.angle_adj_checkbox.setChecked(response.get('angle_adj_enabled', False))
                self.diagonal_angle_slider.setValue(response.get('diagonal_angle', 0))
                self.diagonal_angle_label.setText(f"Diagonal Angle: {response.get('diagonal_angle', 0)}°")
                self.square_output_checkbox.setChecked(response.get('square_output', False))
                self.snappy_joystick_checkbox.setChecked(response.get('snappy_joystick', False))

                self.angle_adj_checkbox.blockSignals(False)
                self.diagonal_angle_slider.blockSignals(False)
                self.square_output_checkbox.blockSignals(False)
                self.snappy_joystick_checkbox.blockSignals(False)

                # Select curve in combo box
                curve_index = response.get('curve_index', 0)
                self.curve_editor.select_curve(curve_index)

                # If it's a user curve (7-16), load the actual points
                if curve_index >= 7 and curve_index <= 16:
                    slot_index = curve_index - 7
                    curve_data = self.keyboard.get_user_curve(slot_index)
                    if curve_data and 'points' in curve_data:
                        self.curve_editor.load_user_curve_points(curve_data['points'])
            print("GamingConfigurator: Gaming data loading complete")
        except Exception as e:
            # Silently fail during load - user can manually load if needed
            print(f"GamingConfigurator: Error loading data: {e}")

    def valid(self):
        return isinstance(self.device, VialKeyboard)
