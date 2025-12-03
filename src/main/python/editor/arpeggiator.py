# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import logging
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                             QLabel, QGroupBox, QMessageBox, QGridLayout,
                             QComboBox, QSpinBox, QLineEdit, QScrollArea,
                             QFrame, QButtonGroup, QRadioButton, QCheckBox)

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard

logger = logging.getLogger(__name__)


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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(40, 40, 40))

        # Border
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        # Velocity bar
        if self.velocity > 0:
            bar_height = int((self.velocity / 255.0) * self.height())
            bar_y = self.height() - bar_height

            # Color gradient based on velocity
            if self.velocity < 85:
                color = QColor(100, 200, 100)  # Green - soft
            elif self.velocity < 170:
                color = QColor(200, 200, 100)  # Yellow - medium
            else:
                color = QColor(200, 100, 100)  # Red - hard

            painter.fillRect(1, bar_y, self.width() - 2, bar_height, color)

        # Velocity text
        painter.setPen(QColor(255, 255, 255))
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

        # Velocity bar
        self.velocity_bar = VelocityBar()
        self.velocity_bar.clicked.connect(self.on_velocity_changed)
        layout.addWidget(self.velocity_bar, 1)

        # Interval/Semitone selector
        interval_group = QGroupBox("Interval")
        interval_layout = QVBoxLayout()
        interval_layout.setSpacing(2)

        # Interval selector (semitone offset from master note)
        self.interval_selector = QComboBox()
        self.interval_selector.addItem("None", -1)
        self.interval_selector.addItem("Unison (0)", 0)
        self.interval_selector.addItem("Minor 2nd (1)", 1)
        self.interval_selector.addItem("Major 2nd (2)", 2)
        self.interval_selector.addItem("Minor 3rd (3)", 3)
        self.interval_selector.addItem("Major 3rd (4)", 4)
        self.interval_selector.addItem("Perfect 4th (5)", 5)
        self.interval_selector.addItem("Tritone (6)", 6)
        self.interval_selector.addItem("Perfect 5th (7)", 7)
        self.interval_selector.addItem("Minor 6th (8)", 8)
        self.interval_selector.addItem("Major 6th (9)", 9)
        self.interval_selector.addItem("Minor 7th (10)", 10)
        self.interval_selector.addItem("Major 7th (11)", 11)
        self.interval_selector.setCurrentIndex(0)  # Default to "None"
        self.interval_selector.setToolTip("Interval offset from master note")
        interval_layout.addWidget(self.interval_selector)

        # Octave offset selector
        self.octave_selector = QSpinBox()
        self.octave_selector.setRange(-2, 2)
        self.octave_selector.setValue(0)
        self.octave_selector.setPrefix("Oct: ")
        self.octave_selector.setToolTip("Octave offset (+/- 12 semitones)")
        interval_layout.addWidget(self.octave_selector)

        interval_group.setLayout(interval_layout)
        layout.addWidget(interval_group)

        self.setLayout(layout)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)

    def on_velocity_changed(self, velocity):
        """Velocity bar was clicked"""
        pass  # Parent will handle this

    def get_step_data(self):
        """Return step data as dict"""
        return {
            'velocity': self.velocity_bar.get_velocity(),
            'semitone_offset': self.interval_selector.currentData(),
            'octave_offset': self.octave_selector.value()
        }

    def set_step_data(self, data):
        """Load step data from dict"""
        if 'velocity' in data:
            self.velocity_bar.set_velocity(data['velocity'])
        if 'semitone_offset' in data:
            # Find the index for this semitone offset
            semitone = data['semitone_offset']
            for i in range(self.interval_selector.count()):
                if self.interval_selector.itemData(i) == semitone:
                    self.interval_selector.setCurrentIndex(i)
                    break
        if 'octave_offset' in data:
            self.octave_selector.setValue(data['octave_offset'])


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
        self.hid_data_received.connect(self.handle_hid_response)

        self.setup_ui()

    def setup_ui(self):
        """Build the UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # === Header Section ===
        header_layout = QHBoxLayout()

        # Preset selector
        preset_group = QGroupBox("Preset")
        preset_layout = QGridLayout()

        lbl_preset = QLabel("Select Preset:")
        self.combo_preset = QComboBox()
        for i in range(32):
            if i < 8:
                self.combo_preset.addItem(f"Factory {i}")
            else:
                self.combo_preset.addItem(f"User {i}")
        self.combo_preset.currentIndexChanged.connect(self.on_preset_changed)

        preset_layout.addWidget(lbl_preset, 0, 0)
        preset_layout.addWidget(self.combo_preset, 0, 1, 1, 2)

        # Preset buttons
        self.btn_load = QPushButton("Load from Device")
        self.btn_load.clicked.connect(self.load_preset)
        self.btn_save = QPushButton("Save to Device")
        self.btn_save.clicked.connect(self.save_preset)
        self.btn_copy = QPushButton("Copy Preset")
        self.btn_copy.clicked.connect(self.copy_preset)

        preset_layout.addWidget(self.btn_load, 1, 0)
        preset_layout.addWidget(self.btn_save, 1, 1)
        preset_layout.addWidget(self.btn_copy, 1, 2)

        preset_group.setLayout(preset_layout)
        header_layout.addWidget(preset_group, 1)

        # Preset parameters
        params_group = QGroupBox("Preset Parameters")
        params_layout = QGridLayout()

        # Pattern Rate
        lbl_pattern_rate = QLabel("Pattern Rate:")
        self.combo_pattern_rate = QComboBox()
        self.combo_pattern_rate.addItem("1/4", 64)   # 64 64ths per quarter note
        self.combo_pattern_rate.addItem("1/8", 32)   # 32 64ths per 8th note
        self.combo_pattern_rate.addItem("1/16", 16)  # 16 64ths per 16th note
        self.combo_pattern_rate.addItem("1/32", 8)   # 8 64ths per 32nd note
        self.combo_pattern_rate.addItem("1/64", 4)   # 4 64ths per 64th note
        self.combo_pattern_rate.setCurrentIndex(2)   # Default to 1/16
        self.combo_pattern_rate.setToolTip("Note subdivision for steps")
        self.combo_pattern_rate.currentIndexChanged.connect(self.on_pattern_rate_changed)
        params_layout.addWidget(lbl_pattern_rate, 0, 0)
        params_layout.addWidget(self.combo_pattern_rate, 0, 1)

        # Number of steps
        lbl_num_steps = QLabel("Number of Steps:")
        self.spin_num_steps = QSpinBox()
        self.spin_num_steps.setRange(1, 16)
        self.spin_num_steps.setValue(4)
        self.spin_num_steps.setToolTip("Number of steps in the pattern")
        self.spin_num_steps.valueChanged.connect(self.on_num_steps_changed)
        params_layout.addWidget(lbl_num_steps, 1, 0)
        params_layout.addWidget(self.spin_num_steps, 1, 1)

        # Pattern length (auto-calculated, read-only display)
        lbl_length = QLabel("Pattern Length:")
        self.lbl_pattern_length = QLabel("64 /64ths")
        self.lbl_pattern_length.setToolTip("Total pattern length (auto-calculated from rate × steps)")
        params_layout.addWidget(lbl_length, 2, 0)
        params_layout.addWidget(self.lbl_pattern_length, 2, 1)

        # Gate length
        lbl_gate = QLabel("Gate Length:")
        self.spin_gate = QSpinBox()
        self.spin_gate.setRange(10, 100)
        self.spin_gate.setValue(80)
        self.spin_gate.setSuffix("%")
        self.spin_gate.setToolTip("Note gate length percentage")
        params_layout.addWidget(lbl_gate, 3, 0)
        params_layout.addWidget(self.spin_gate, 3, 1)

        params_group.setLayout(params_layout)
        header_layout.addWidget(params_group, 1)

        main_layout.addLayout(header_layout)

        # === Mode Selection ===
        mode_group = QGroupBox("Arpeggiator Mode")
        mode_layout = QHBoxLayout()

        self.mode_button_group = QButtonGroup()
        self.radio_single = QRadioButton("Single Note (Classic Arp)")
        self.radio_chord_basic = QRadioButton("Chord Basic (All Notes)")
        self.radio_chord_advanced = QRadioButton("Chord Advanced (Rotation)")

        self.radio_single.setChecked(True)

        self.mode_button_group.addButton(self.radio_single, 0)
        self.mode_button_group.addButton(self.radio_chord_basic, 1)
        self.mode_button_group.addButton(self.radio_chord_advanced, 2)

        mode_layout.addWidget(self.radio_single)
        mode_layout.addWidget(self.radio_chord_basic)
        mode_layout.addWidget(self.radio_chord_advanced)

        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        # === Step Sequencer ===
        sequencer_group = QGroupBox("Step Sequencer")
        sequencer_group.setToolTip("Click on velocity bars to set note velocity (higher = louder)")

        # Create scrollable area for steps
        self.step_scroll = QScrollArea()
        self.step_scroll.setWidgetResizable(True)
        self.step_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.step_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.step_scroll.setMinimumHeight(300)

        self.step_container = QWidget()
        self.step_layout = QHBoxLayout()
        self.step_layout.setSpacing(2)
        self.step_container.setLayout(self.step_layout)
        self.step_scroll.setWidget(self.step_container)

        sequencer_layout = QVBoxLayout()
        sequencer_layout.addWidget(self.step_scroll)
        sequencer_group.setLayout(sequencer_layout)

        main_layout.addWidget(sequencer_group, 1)

        # Build initial steps
        self.rebuild_steps()

        # === Quick Actions ===
        actions_layout = QHBoxLayout()

        self.btn_clear_all = QPushButton("Clear All Steps")
        self.btn_clear_all.clicked.connect(self.clear_all_steps)

        self.btn_reset_velocity = QPushButton("Reset All Velocity (200)")
        self.btn_reset_velocity.clicked.connect(self.reset_all_velocity)

        self.btn_ascending = QPushButton("Quick: Ascending")
        self.btn_ascending.clicked.connect(self.quick_ascending)

        self.btn_descending = QPushButton("Quick: Descending")
        self.btn_descending.clicked.connect(self.quick_descending)

        actions_layout.addWidget(self.btn_clear_all)
        actions_layout.addWidget(self.btn_reset_velocity)
        actions_layout.addWidget(self.btn_ascending)
        actions_layout.addWidget(self.btn_descending)

        main_layout.addLayout(actions_layout)

        # === Status ===
        self.lbl_status = QLabel("Ready. Select a preset to begin.")
        self.lbl_status.setStyleSheet("color: #00aaff; padding: 5px;")
        main_layout.addWidget(self.lbl_status)

        self.addLayout(main_layout)

    def rebuild_steps(self):
        """Rebuild step widgets based on step count"""
        # Clear existing steps
        for widget in self.step_widgets:
            self.step_layout.removeWidget(widget)
            widget.deleteLater()
        self.step_widgets.clear()

        # Create new steps
        step_count = self.spin_num_steps.value()
        for i in range(step_count):
            step_widget = StepWidget(i)

            # Load existing step data if available
            if i < len(self.preset_data['steps']):
                step_widget.set_step_data(self.preset_data['steps'][i])

            self.step_widgets.append(step_widget)
            self.step_layout.addWidget(step_widget)

        self.step_layout.addStretch()
        self.update_pattern_length_display()
        self.update_status(f"Rebuilt sequencer with {step_count} steps")

    def on_pattern_rate_changed(self, index):
        """Pattern rate changed - update pattern length display"""
        self.update_pattern_length_display()
        self.update_status(f"Pattern rate changed to {self.combo_pattern_rate.currentText()}")

    def on_num_steps_changed(self, value):
        """Number of steps changed - rebuild and update pattern length"""
        self.rebuild_steps()

    def update_pattern_length_display(self):
        """Update the pattern length display based on rate × steps"""
        rate_64ths = self.combo_pattern_rate.currentData()
        num_steps = self.spin_num_steps.value()
        pattern_length = rate_64ths * num_steps
        self.lbl_pattern_length.setText(f"{pattern_length} /64ths")

    def clear_all_steps(self):
        """Clear all step data"""
        for widget in self.step_widgets:
            widget.set_step_data({
                'velocity': 0,
                'semitone_offset': -1,  # None
                'octave_offset': 0
            })
        self.update_status("All steps cleared")

    def reset_all_velocity(self):
        """Reset all velocities to 200"""
        for widget in self.step_widgets:
            widget.velocity_bar.set_velocity(200)
        self.update_status("All velocities reset to 200")

    def quick_ascending(self):
        """Quick pattern: ascending intervals (0, 2, 4, 7 semitones - C, D, E, G)"""
        intervals = [0, 2, 4, 7]  # Major scale intervals
        for i, widget in enumerate(self.step_widgets):
            # Set interval based on position
            interval = intervals[i % len(intervals)]
            # Find the combo box index for this interval
            for idx in range(widget.interval_selector.count()):
                if widget.interval_selector.itemData(idx) == interval:
                    widget.interval_selector.setCurrentIndex(idx)
                    break
            widget.octave_selector.setValue(0)
            widget.velocity_bar.set_velocity(200)
        self.update_status("Applied ascending pattern")

    def quick_descending(self):
        """Quick pattern: descending intervals"""
        intervals = [7, 4, 2, 0]  # Descending major scale intervals
        for i, widget in enumerate(self.step_widgets):
            # Set interval based on position
            interval = intervals[i % len(intervals)]
            # Find the combo box index for this interval
            for idx in range(widget.interval_selector.count()):
                if widget.interval_selector.itemData(idx) == interval:
                    widget.interval_selector.setCurrentIndex(idx)
                    break
            widget.octave_selector.setValue(0)
            widget.velocity_bar.set_velocity(200)
        self.update_status("Applied descending pattern")

    def gather_preset_data(self):
        """Gather current UI state into preset_data dict"""
        # Calculate pattern length from rate × steps
        rate_64ths = self.combo_pattern_rate.currentData()
        num_steps = self.spin_num_steps.value()
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

    def copy_preset(self):
        """Copy current preset to another slot"""
        from PyQt5.QtWidgets import QInputDialog

        source_id = self.current_preset_id
        dest_id, ok = QInputDialog.getInt(
            None, "Copy Preset",
            f"Copy preset {source_id} to slot (8-31):",
            8, 8, 31, 1)

        if ok:
            self.send_hid_command(self.ARP_CMD_COPY_PRESET, [source_id, dest_id])
            self.update_status(f"Copying preset {source_id} to {dest_id}...")

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
