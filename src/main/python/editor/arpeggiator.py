# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import logging
import math
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                             QLabel, QGroupBox, QMessageBox, QGridLayout,
                             QComboBox, QSpinBox, QLineEdit, QScrollArea,
                             QFrame, QButtonGroup, QRadioButton, QCheckBox, QSlider,
                             QInputDialog)

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard
from widgets.combo_box import ArrowComboBox

logger = logging.getLogger(__name__)


class IntervalSelector(QWidget):
    """Custom interval selector with +/- buttons and editable value box"""

    valueChanged = pyqtSignal(int)

    # Interval names mapping
    INTERVAL_NAMES = {
        -1: "Empty",
        0: "Root Note",
        1: "Minor Second",
        2: "Major Second",
        3: "Minor Third",
        4: "Major Third",
        5: "Perfect Fourth",
        6: "Tritone",
        7: "Perfect Fifth",
        8: "Minor Sixth",
        9: "Major Sixth",
        10: "Minor Seventh",
        11: "Major Seventh"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = -1  # Default to None

        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        # Interval name label (above the box)
        self.name_label = QLabel("Empty")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(self.name_label)

        # Container for the value box with integrated +/- buttons
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        container.setMaximumWidth(120)

        box_layout = QHBoxLayout()
        box_layout.setSpacing(0)
        box_layout.setContentsMargins(2, 2, 2, 2)

        # Minus button (inside container, on left)
        self.btn_minus = QPushButton("-")
        self.btn_minus.setFixedSize(25, 25)
        self.btn_minus.clicked.connect(self.decrement)
        box_layout.addWidget(self.btn_minus)

        # Value box (center)
        self.value_box = QLabel("Empty")
        self.value_box.setAlignment(Qt.AlignCenter)
        self.value_box.setMinimumWidth(50)
        box_layout.addWidget(self.value_box, 1)

        # Plus button (inside container, on right)
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(25, 25)
        self.btn_plus.clicked.connect(self.increment)
        box_layout.addWidget(self.btn_plus)

        container.setLayout(box_layout)
        layout.addWidget(container, 0, Qt.AlignCenter)
        self.setLayout(layout)

        self.update_display()

    def get_value(self):
        """Get current interval value"""
        return self.value

    def set_value(self, value):
        """Set interval value"""
        # Clamp to valid range (-1 to 11)
        value = max(-1, min(11, value))

        if self.value != value:
            self.value = value
            self.update_display()
            self.valueChanged.emit(self.value)

    def increment(self):
        """Increment interval value"""
        if self.value < 11:
            new_value = self.value + 1
            self.set_value(new_value)

    def decrement(self):
        """Decrement interval value"""
        # Cannot go below -1 (Empty)
        if self.value > -1:
            new_value = self.value - 1
            self.set_value(new_value)

    def update_display(self):
        """Update the display text"""
        # Update interval name
        self.name_label.setText(self.INTERVAL_NAMES.get(self.value, "Unknown"))

        # Update value box
        if self.value == -1:
            self.value_box.setText("Empty")
        elif self.value >= 0:
            self.value_box.setText(f"+{self.value}")

        # Enable/disable buttons
        self.btn_minus.setEnabled(self.value > -1)
        self.btn_plus.setEnabled(self.value < 11)


class OctaveSelector(QWidget):
    """Custom octave selector with +/- buttons"""

    valueChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0  # Default to 0

        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        # Octave label (above the box)
        self.name_label = QLabel("Octave")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(self.name_label)

        # Container for the value box with integrated +/- buttons
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        container.setMaximumWidth(120)

        box_layout = QHBoxLayout()
        box_layout.setSpacing(0)
        box_layout.setContentsMargins(2, 2, 2, 2)

        # Minus button (inside container, on left)
        self.btn_minus = QPushButton("-")
        self.btn_minus.setFixedSize(25, 25)
        self.btn_minus.clicked.connect(self.decrement)
        box_layout.addWidget(self.btn_minus)

        # Value box (center)
        self.value_box = QLabel("0")
        self.value_box.setAlignment(Qt.AlignCenter)
        self.value_box.setMinimumWidth(50)
        box_layout.addWidget(self.value_box, 1)

        # Plus button (inside container, on right)
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(25, 25)
        self.btn_plus.clicked.connect(self.increment)
        box_layout.addWidget(self.btn_plus)

        container.setLayout(box_layout)
        layout.addWidget(container, 0, Qt.AlignCenter)
        self.setLayout(layout)

        self.update_display()

    def get_value(self):
        """Get current octave value"""
        return self.value

    def set_value(self, value):
        """Set octave value"""
        # Clamp to valid range
        if value < -2:
            value = -2
        elif value > 2:
            value = 2

        if self.value != value:
            self.value = value
            self.update_display()
            self.valueChanged.emit(self.value)

    def increment(self):
        """Increment octave value"""
        if self.value < 2:
            self.set_value(self.value + 1)

    def decrement(self):
        """Decrement octave value"""
        if self.value > -2:
            self.set_value(self.value - 1)

    def update_display(self):
        """Update the display text"""
        # Update value box with + or - prefix
        if self.value > 0:
            self.value_box.setText(f"+{self.value}")
        else:
            self.value_box.setText(str(self.value))

        # Enable/disable buttons
        self.btn_minus.setEnabled(self.value > -2)
        self.btn_plus.setEnabled(self.value < 2)


class VelocityBar(QWidget):
    """Interactive velocity bar for step sequencer - click height sets velocity"""

    clicked = pyqtSignal(int)  # Emits velocity value 0-255

    def __init__(self, parent=None):
        super().__init__(parent)
        self.velocity = 200  # Default velocity
        self.setMinimumSize(30, 120)
        self.setMaximumSize(40, 150)
        self.setSizePolicy(self.sizePolicy().Minimum, self.sizePolicy().Expanding)

    def set_velocity(self, velocity):
        """Set velocity value (0-255)"""
        self.velocity = max(0, min(255, velocity))
        self.update()

    def get_velocity(self):
        """Get current velocity"""
        return self.velocity

    def paintEvent(self, event):
        from PyQt5.QtGui import QPalette

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get theme colors from palette
        palette = self.palette()
        bg_color = palette.color(QPalette.Window)
        highlight_color = palette.color(QPalette.Highlight)

        # Background
        painter.fillRect(self.rect(), bg_color.darker(120))

        # Border
        painter.setPen(QPen(palette.color(QPalette.Mid), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        # Velocity bar with theme highlight color
        if self.velocity > 0:
            bar_height = int((self.velocity / 255.0) * self.height())
            bar_y = self.height() - bar_height

            # Use theme highlight color with intensity based on velocity
            intensity = self.velocity / 255.0
            color = QColor(
                int(highlight_color.red() * (0.5 + 0.5 * intensity)),
                int(highlight_color.green() * (0.5 + 0.5 * intensity)),
                int(highlight_color.blue() * (0.5 + 0.5 * intensity))
            )

            painter.fillRect(1, bar_y, self.width() - 2, bar_height, color)

        # Velocity text
        painter.setPen(palette.color(QPalette.Text))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.rect(), Qt.AlignCenter, str(self.velocity))

    def mousePressEvent(self, event):
        """Click to set velocity based on Y position"""
        if event.button() == Qt.LeftButton:
            # Invert Y (top = high velocity, bottom = low)
            relative_y = event.pos().y() / self.height()
            velocity = int((1.0 - relative_y) * 255)
            self.set_velocity(velocity)
            self.clicked.emit(self.velocity)


class StepWidget(QFrame):
    """Single step in the sequencer with velocity bar and interval selector"""

    def __init__(self, step_num, parent=None):
        super().__init__(parent)
        self.step_num = step_num
        self.semitone_offset = -1  # -1 = None (skip step)
        self.octave_offset = 0

        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        # Step number label
        lbl_step = QLabel(f"Step {step_num + 1}")
        lbl_step.setAlignment(Qt.AlignCenter)
        lbl_step.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(lbl_step)

        # Velocity label
        self.velocity_label = QLabel("Velocity")
        self.velocity_label.setAlignment(Qt.AlignCenter)
        self.velocity_label.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(self.velocity_label)

        # Velocity bar - centered
        velocity_container = QWidget()
        velocity_container_layout = QHBoxLayout()
        velocity_container_layout.setContentsMargins(0, 0, 0, 0)
        velocity_container.setLayout(velocity_container_layout)

        velocity_container_layout.addStretch()
        self.velocity_bar = VelocityBar()
        self.velocity_bar.clicked.connect(self.on_velocity_changed)
        velocity_container_layout.addWidget(self.velocity_bar)
        velocity_container_layout.addStretch()

        self.velocity_container = velocity_container
        layout.addWidget(velocity_container, 1)

        # Add stretch between velocity and note to push them apart
        layout.addStretch(1)

        # Interval/Semitone selector - centered
        self.interval_selector = IntervalSelector()
        self.interval_selector.valueChanged.connect(self.on_interval_changed)
        layout.addWidget(self.interval_selector)

        # Add stretch above octave to push it down
        layout.addStretch(1)

        # Octave offset selector - centered
        self.octave_selector = OctaveSelector()
        self.octave_selector.valueChanged.connect(self.on_octave_changed)
        layout.addWidget(self.octave_selector)

        self.setLayout(layout)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)

        # Initialize empty state
        self.update_empty_state()

    def on_velocity_changed(self, velocity):
        """Velocity bar was clicked"""
        pass  # Parent will handle this

    def on_interval_changed(self, value):
        """Interval selector changed"""
        self.update_empty_state()

    def on_octave_changed(self, value):
        """Octave selector changed"""
        pass  # No visual state changes needed

    def update_empty_state(self):
        """Update visual state based on whether note is empty"""
        is_empty = self.interval_selector.get_value() == -1

        if is_empty:
            # When empty, dim everything and hide velocity bar
            self.velocity_label.setText("Empty")
            self.velocity_container.setVisible(False)

            # Dim the octave selector
            self.octave_selector.setEnabled(False)

            # Don't change background color, just dim the controls
            opacity_effect = "QWidget { opacity: 0.5; }"
            self.interval_selector.setStyleSheet("")  # Keep interval selector normal
        else:
            # When not empty, show everything normally
            self.velocity_label.setText("Velocity")
            self.velocity_container.setVisible(True)

            # Enable octave selector
            self.octave_selector.setEnabled(True)

            # Clear any dimming
            self.interval_selector.setStyleSheet("")

    def get_step_data(self):
        """Return step data as dict"""
        return {
            'velocity': self.velocity_bar.get_velocity(),
            'semitone_offset': self.interval_selector.get_value(),
            'octave_offset': self.octave_selector.get_value()
        }

    def set_step_data(self, data):
        """Load step data from dict"""
        if 'velocity' in data:
            self.velocity_bar.set_velocity(data['velocity'])
        if 'semitone_offset' in data:
            self.interval_selector.set_value(data['semitone_offset'])
        if 'octave_offset' in data:
            self.octave_selector.set_value(data['octave_offset'])
        self.update_empty_state()


class Arpeggiator(BasicEditor):
    """Arpeggiator tab for creating and managing arpeggiator presets"""

    # HID Command constants for arpeggiator
    ARP_CMD_GET_PRESET = 0xC0
    ARP_CMD_SET_PRESET = 0xC1
    ARP_CMD_SAVE_PRESET = 0xC2
    ARP_CMD_LOAD_PRESET = 0xC3
    ARP_CMD_CLEAR_PRESET = 0xC4
    ARP_CMD_COPY_PRESET = 0xC5
    ARP_CMD_RESET_ALL = 0xC6
    ARP_CMD_GET_STATE = 0xC7
    ARP_CMD_SET_STATE = 0xC8
    ARP_CMD_GET_INFO = 0xC9

    MANUFACTURER_ID = 0x7D
    SUB_ID = 0x00
    DEVICE_ID = 0x4D

    # Signals
    hid_data_received = pyqtSignal(bytes)

    def __init__(self):
        super().__init__()

        logger.info("Arpeggiator tab initialized")

        self.current_preset_id = 0
        self.preset_data = {
            'name': 'User Preset',
            'note_count': 4,
            'pattern_length_64ths': 64,
            'gate_length_percent': 80,
            'steps': []
        }

        # Initialize with 4 default steps
        for i in range(4):
            self.preset_data['steps'].append({
                'velocity': 200,
                'semitone_offset': -1,  # None by default
                'octave_offset': 0
            })

        self.step_widgets = []
        self.clipboard_preset = None  # Internal clipboard for copy/paste
        self.hid_data_received.connect(self.handle_hid_response)

        self.setup_ui()

    def setup_ui(self):
        """Build the UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # === Status ===
        self.lbl_status = QLabel("Ready. Select a preset to begin.")
        self.lbl_status.setStyleSheet("color: #00aaff; padding: 5px;")
        # === Header Section ===
        header_layout = QHBoxLayout()

        # Preset selector
        preset_group = QGroupBox("Preset")
        preset_layout = QGridLayout()

        # === Sequencer Section ===
        sequencer_group = QGroupBox("Step Sequencer")

        # Create scrollable area for steps
        self.step_scroll = QScrollArea()
        self.step_scroll.setWidgetResizable(True)
        self.step_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.step_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.step_scroll.setMinimumHeight(300)

        self.step_container = QWidget()
        self.step_layout = QHBoxLayout()
        self.step_layout.setSpacing(2)
        self.step_layout.setDirection(QHBoxLayout.LeftToRight)  # Ensure left-to-right
        self.step_container.setLayout(self.step_layout)
        self.step_scroll.setWidget(self.step_container)

        sequencer_layout = QVBoxLayout()
        sequencer_layout.addWidget(self.step_scroll)
        sequencer_group.setLayout(sequencer_layout)

        main_layout.addWidget(sequencer_group, 1)

        # === Bottom Section: Two containers side by side ===
        bottom_layout = QHBoxLayout()

        # Add left spacer to push containers closer together
        bottom_layout.addStretch(1)

        # Left Container: Preset Parameters (no title)
        params_group = QGroupBox()
        params_group.setMaximumWidth(500)
        params_layout = QGridLayout()

        # Arpeggiator Mode (moved from separate section)
        lbl_mode = QLabel("Arpeggiator Mode:")
        self.combo_mode = ArrowComboBox()
        self.combo_mode.setMinimumWidth(150)
        self.combo_mode.setMaximumHeight(30)
        self.combo_mode.setEditable(True)
        self.combo_mode.lineEdit().setReadOnly(True)
        self.combo_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.combo_mode.addItem("Single Note (Classic Arp)", 0)
        self.combo_mode.addItem("Chord Basic (All Notes)", 1)
        self.combo_mode.addItem("Chord Advanced (Rotation)", 2)
        self.combo_mode.setToolTip("Select how the arpeggiator plays notes")
        params_layout.addWidget(lbl_mode, 0, 0)
        params_layout.addWidget(self.combo_mode, 0, 1)

        # Pattern Rate (now a dropdown)
        lbl_pattern_rate = QLabel("Pattern Rate:")
        self.combo_pattern_rate = ArrowComboBox()
        self.combo_pattern_rate.setMinimumWidth(150)
        self.combo_pattern_rate.setMaximumHeight(30)
        self.combo_pattern_rate.setEditable(True)
        self.combo_pattern_rate.lineEdit().setReadOnly(True)
        self.combo_pattern_rate.lineEdit().setAlignment(Qt.AlignCenter)
        self.combo_pattern_rate.addItem("1/4", 0)
        self.combo_pattern_rate.addItem("1/8", 1)
        self.combo_pattern_rate.addItem("1/16", 2)
        self.combo_pattern_rate.addItem("1/32", 3)
        self.combo_pattern_rate.addItem("1/64", 4)
        self.combo_pattern_rate.setCurrentIndex(2)  # Default to 1/16
        self.combo_pattern_rate.setToolTip("Note subdivision for steps")
        self.combo_pattern_rate.currentIndexChanged.connect(self.on_pattern_rate_changed)
        params_layout.addWidget(lbl_pattern_rate, 1, 0)
        params_layout.addWidget(self.combo_pattern_rate, 1, 1)

        # Number of steps
        lbl_num_steps = QLabel("Number of Steps:")
        self.spin_num_steps = QSpinBox()
        self.spin_num_steps.setRange(1, 128)
        self.spin_num_steps.setValue(4)
        self.spin_num_steps.setButtonSymbols(QSpinBox.UpDownArrows)
        self.spin_num_steps.setToolTip("Number of steps in the pattern")
        self.spin_num_steps.valueChanged.connect(self.on_num_steps_changed)
        params_layout.addWidget(lbl_num_steps, 2, 0)
        params_layout.addWidget(self.spin_num_steps, 2, 1)

        # Pattern length (auto-calculated, read-only display)
        lbl_length = QLabel("Pattern Length:")
        self.lbl_pattern_length = QLabel("4/16")
        self.lbl_pattern_length.setToolTip("Total pattern length (auto-calculated from steps/rate)")
        params_layout.addWidget(lbl_length, 3, 0)
        params_layout.addWidget(self.lbl_pattern_length, 3, 1)

        # Gate length
        lbl_gate = QLabel("Gate Length:")
        self.spin_gate = QSpinBox()
        self.spin_gate.setRange(10, 100)
        self.spin_gate.setValue(80)
        self.spin_gate.setSuffix("%")
        self.spin_gate.setButtonSymbols(QSpinBox.UpDownArrows)
        self.spin_gate.setToolTip("Note gate length percentage")
        params_layout.addWidget(lbl_gate, 4, 0)
        params_layout.addWidget(self.spin_gate, 4, 1)

        params_group.setLayout(params_layout)
        bottom_layout.addWidget(params_group)

        # Right Container: Preset Selection (no title)
        preset_group = QGroupBox()
        preset_group.setMaximumWidth(500)
        preset_layout = QGridLayout()

        lbl_preset = QLabel("Select Preset:")
        self.combo_preset = ArrowComboBox()
        self.combo_preset.setMinimumWidth(150)
        self.combo_preset.setMaximumHeight(30)
        self.combo_preset.setEditable(True)
        self.combo_preset.lineEdit().setReadOnly(True)
        self.combo_preset.lineEdit().setAlignment(Qt.AlignCenter)
        for i in range(32):
            if i < 8:
                self.combo_preset.addItem(f"Factory {i}")
            else:
                self.combo_preset.addItem(f"User {i}")
        self.combo_preset.currentIndexChanged.connect(self.on_preset_changed)

        preset_layout.addWidget(lbl_preset, 0, 0)
        preset_layout.addWidget(self.combo_preset, 0, 1, 1, 2)

        # Preset buttons - 35px tall
        button_style = "QPushButton { min-height: 35px; max-height: 35px; }"

        self.btn_load = QPushButton("Load from Device")
        self.btn_load.setStyleSheet(button_style)
        self.btn_load.clicked.connect(self.load_preset)
        self.btn_save = QPushButton("Save to Device")
        self.btn_save.setStyleSheet(button_style)
        self.btn_save.clicked.connect(self.save_preset)

        preset_layout.addWidget(self.btn_load, 1, 0, 1, 3)
        preset_layout.addWidget(self.btn_save, 2, 0, 1, 3)

        # Copy and Paste buttons - same size
        copy_paste_layout = QHBoxLayout()
        copy_paste_layout.setSpacing(5)

        self.btn_copy = QPushButton("Copy Preset")
        self.btn_copy.setStyleSheet(button_style)
        self.btn_copy.clicked.connect(self.copy_preset_to_clipboard)
        self.btn_paste = QPushButton("Paste Preset")
        self.btn_paste.setStyleSheet(button_style)
        self.btn_paste.clicked.connect(self.paste_preset_from_clipboard)

        copy_paste_layout.addWidget(self.btn_copy)
        copy_paste_layout.addWidget(self.btn_paste)

        preset_layout.addLayout(copy_paste_layout, 3, 0, 1, 3)

        # Reset All Steps button (replacing Clear All Steps)
        self.btn_reset_all = QPushButton("Reset All Steps")
        self.btn_reset_all.setStyleSheet(button_style)
        self.btn_reset_all.clicked.connect(self.reset_all_steps)
        preset_layout.addWidget(self.btn_reset_all, 4, 0, 1, 3)

        preset_group.setLayout(preset_layout)
        bottom_layout.addWidget(preset_group)

        # Add right spacer to push containers closer together
        bottom_layout.addStretch(1)

        main_layout.addLayout(bottom_layout)

        # Build initial steps
        self.rebuild_steps()

        # === Quick Actions ===
        actions_layout = QHBoxLayout()

        main_layout.addLayout(actions_layout)

        main_layout.addWidget(self.lbl_status)

        self.addLayout(main_layout)

    def rebuild_steps(self):
        """Rebuild step widgets based on step count"""
        # Clear existing steps
        for widget in self.step_widgets:
            self.step_layout.removeWidget(widget)
            widget.deleteLater()
        self.step_widgets.clear()

        # Remove stretch if it exists
        while self.step_layout.count() > 0:
            item = self.step_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create new steps (they will be added from left to right)
        step_count = self.spin_num_steps.value()
        for i in range(step_count):
            step_widget = StepWidget(i)

            # Load existing step data if available
            if i < len(self.preset_data['steps']):
                step_widget.set_step_data(self.preset_data['steps'][i])

            self.step_widgets.append(step_widget)
            self.step_layout.addWidget(step_widget, 0, Qt.AlignLeft)  # Explicitly align left

        self.step_layout.addStretch()  # Add stretch at the end to push steps to the left
        self.update_pattern_length_display()
        self.update_status(f"Rebuilt sequencer with {step_count} steps")

    def on_pattern_rate_changed(self, index):
        """Pattern rate changed - update pattern length display"""
        rate_text = self.combo_pattern_rate.currentText()
        self.update_pattern_length_display()
        self.update_status(f"Pattern rate changed to {rate_text}")

    def on_num_steps_changed(self, value):
        """Number of steps changed - rebuild and update pattern length"""
        self.rebuild_steps()

    def update_pattern_length_display(self):
        """Update the pattern length display using proper music notation with GCD simplification"""
        # Map combo box index to note value denominator (4 = quarter note, 8 = eighth, etc.)
        rate_to_denominator = {0: 4, 1: 8, 2: 16, 3: 32, 4: 64}
        denominator = rate_to_denominator.get(self.combo_pattern_rate.currentData(), 16)

        num_steps = self.spin_num_steps.value()

        # Pattern rhythm is: num_steps / denominator
        # For example: 4 steps of 1/16 notes = 4/16
        #             5 steps of 1/4 notes = 5/4
        #             10 steps of 1/8 notes = 10/8 = 5/4 (after simplification)
        numerator = num_steps

        # Simplify the fraction using GCD (Greatest Common Divisor)
        gcd = math.gcd(numerator, denominator)
        simplified_numerator = numerator // gcd
        simplified_denominator = denominator // gcd

        # Update pattern_length_64ths for internal use (still needed for firmware)
        # Calculate how many 64th notes this pattern is:
        # If we have n/d notes, that's (n/d) * 64 sixty-fourth notes for a whole note pattern
        # But we need to convert based on the actual note value
        # 1/4 note = 16 sixty-fourths, 1/8 = 8 sixty-fourths, 1/16 = 4 sixty-fourths, etc.
        sixty_fourths_per_note = {4: 16, 8: 8, 16: 4, 32: 2, 64: 1}
        pattern_length_64ths = num_steps * sixty_fourths_per_note.get(denominator, 4)

        self.lbl_pattern_length.setText(f"{simplified_numerator}/{simplified_denominator}")

    def reset_all_steps(self):
        """Reset all steps to None with max velocity (with confirmation)"""
        reply = QMessageBox.question(
            None,
            "Reset All Steps",
            "Are you sure you want to reset all steps to None with max velocity?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for widget in self.step_widgets:
                widget.set_step_data({
                    'velocity': 255,  # Max velocity
                    'semitone_offset': -1,  # None
                    'octave_offset': 0
                })
            self.update_status("All steps reset to None with max velocity")

    def copy_preset_to_clipboard(self):
        """Copy current preset data to internal clipboard"""
        self.gather_preset_data()
        self.clipboard_preset = self.preset_data.copy()
        self.clipboard_preset['steps'] = [step.copy() for step in self.preset_data['steps']]
        self.update_status("Preset copied to clipboard")

    def paste_preset_from_clipboard(self):
        """Paste preset data from internal clipboard"""
        if not hasattr(self, 'clipboard_preset') or self.clipboard_preset is None:
            self.update_status("No preset in clipboard", error=True)
            return

        self.preset_data = self.clipboard_preset.copy()
        self.preset_data['steps'] = [step.copy() for step in self.clipboard_preset['steps']]
        self.apply_preset_data()
        self.update_status("Preset pasted from clipboard")

    def gather_preset_data(self):
        """Gather current UI state into preset_data dict"""
        # Calculate pattern length using proper note value conversion
        rate_to_denominator = {0: 4, 1: 8, 2: 16, 3: 32, 4: 64}
        denominator = rate_to_denominator.get(self.combo_pattern_rate.currentData(), 16)
        num_steps = self.spin_num_steps.value()

        # Convert to sixty-fourth notes for firmware
        # 1/4 note = 16 sixty-fourths, 1/8 = 8, 1/16 = 4, 1/32 = 2, 1/64 = 1
        sixty_fourths_per_note = {4: 16, 8: 8, 16: 4, 32: 2, 64: 1}
        rate_64ths = sixty_fourths_per_note.get(denominator, 4)

        self.preset_data['pattern_length_64ths'] = rate_64ths * num_steps
        self.preset_data['gate_length_percent'] = self.spin_gate.value()

        # Gather step data, filtering out "None" steps and calculating timing
        self.preset_data['steps'] = []
        for i, widget in enumerate(self.step_widgets):
            step_data = widget.get_step_data()
            # Skip steps with semitone_offset = -1 (None)
            if step_data['semitone_offset'] != -1:
                # Calculate timing based on pattern rate and step position
                step_data['timing_64ths'] = i * rate_64ths
                # Convert semitone_offset to note_index for firmware compatibility
                # (we'll map semitone_offset as the note_index field in firmware)
                step_data['note_index'] = step_data['semitone_offset']
                self.preset_data['steps'].append(step_data)

        self.preset_data['note_count'] = len(self.preset_data['steps'])
        # Keep name in data structure for firmware compatibility
        if 'name' not in self.preset_data:
            self.preset_data['name'] = 'User Preset'

    def apply_preset_data(self):
        """Apply preset_data to UI"""
        self.spin_gate.setValue(self.preset_data.get('gate_length_percent', 80))

        # Apply step data
        steps = self.preset_data.get('steps', [])
        self.spin_num_steps.setValue(len(steps) if len(steps) > 0 else 4)
        self.rebuild_steps()

    def on_preset_changed(self, index):
        """Preset selection changed"""
        self.current_preset_id = index

        # Update UI state
        is_factory = (index < 8)
        self.btn_save.setEnabled(not is_factory)

        if is_factory:
            self.update_status(f"Factory preset {index} selected (read-only)")
        else:
            self.update_status(f"User preset {index} selected")

    def send_hid_command(self, cmd, params):
        """Send HID command to device"""
        if not isinstance(self.device, VialKeyboard):
            self.update_status("Error: Device not connected", error=True)
            return False

        # Build HID packet
        data = bytearray(32)
        data[0] = self.MANUFACTURER_ID
        data[1] = self.SUB_ID
        data[2] = self.DEVICE_ID
        data[3] = cmd

        # Add parameters
        for i, param in enumerate(params):
            if i + 4 < len(data):
                if isinstance(param, int):
                    data[i + 4] = param & 0xFF
                elif isinstance(param, str):
                    # String encoding
                    encoded = param.encode('ascii')[:16]
                    for j, byte in enumerate(encoded):
                        if i + 4 + j < len(data):
                            data[i + 4 + j] = byte
                    break

        try:
            self.device.keyboard.raw_hid_send(bytes(data))
            logger.info(f"Sent HID command: 0x{cmd:02X}")
            return True
        except Exception as e:
            logger.error(f"HID send error: {e}")
            self.update_status(f"HID error: {e}", error=True)
            return False

    def handle_hid_response(self, data):
        """Handle HID response from device"""
        if len(data) < 4:
            return

        cmd = data[3]
        status = data[4] if len(data) > 4 else 0xFF

        if status == 0:
            self.update_status("Command successful")

            if cmd == self.ARP_CMD_GET_PRESET:
                # Parse preset data
                name = data[5:21].decode('ascii', errors='ignore').rstrip('\x00')
                note_count = data[21] if len(data) > 21 else 0
                pattern_length = ((data[22] << 8) | data[23]) if len(data) > 23 else 64
                gate_length = data[24] if len(data) > 24 else 80

                self.preset_data['name'] = name
                self.preset_data['note_count'] = note_count
                self.preset_data['pattern_length_64ths'] = pattern_length
                self.preset_data['gate_length_percent'] = gate_length

                self.apply_preset_data()
                self.update_status(f"Loaded preset: {name}")
        else:
            error_msg = {
                1: "Error: Invalid preset or operation failed",
                0xFF: "Error: Unknown command"
            }.get(status, f"Error: Status code {status}")
            self.update_status(error_msg, error=True)

    def load_preset(self):
        """Load preset from device via HID"""
        self.gather_preset_data()

        preset_id = self.current_preset_id
        self.send_hid_command(self.ARP_CMD_GET_PRESET, [preset_id])
        self.update_status(f"Requesting preset {preset_id} from device...")

    def save_preset(self):
        """Save preset to device via HID"""
        if self.current_preset_id < 8:
            self.update_status("Cannot save to factory preset!", error=True)
            return

        self.gather_preset_data()

        # Build parameter list
        params = [self.current_preset_id]
        params.append(self.preset_data['name'])  # String will be encoded in send_hid_command
        params.extend([0] * (16 - len(self.preset_data['name'])))  # Padding
        params.append(self.preset_data['note_count'])
        params.append((self.preset_data['pattern_length_64ths'] >> 8) & 0xFF)
        params.append(self.preset_data['pattern_length_64ths'] & 0xFF)
        params.append(self.preset_data['gate_length_percent'])

        if self.send_hid_command(self.ARP_CMD_SET_PRESET, params):
            # Also save to EEPROM
            QTimer.singleShot(100, lambda: self.send_hid_command(
                self.ARP_CMD_SAVE_PRESET, [self.current_preset_id]))
            self.update_status(f"Saving preset {self.current_preset_id}...")

    def update_status(self, message, error=False):
        """Update status label"""
        logger.info(message)
        self.lbl_status.setText(message)
        if error:
            self.lbl_status.setStyleSheet("color: #ff4444; padding: 5px;")
        else:
            self.lbl_status.setStyleSheet("color: #00aaff; padding: 5px;")

    def valid(self):
        """Check if this tab should be visible"""
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        """Rebuild for new device"""
        super().rebuild(device)

        if self.valid():
            self.update_status("Arpeggiator ready")
            # Request system info
            self.send_hid_command(self.ARP_CMD_GET_INFO, [])
        else:
            self.update_status("Connect a Vial device to use arpeggiator")

    def activate(self):
        """Tab activated"""
        logger.info("Arpeggiator tab activated")

    def deactivate(self):
        """Tab deactivated"""
        logger.info("Arpeggiator tab deactivated")
