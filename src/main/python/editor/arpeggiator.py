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
        self.note_index = 0
        self.octave_offset = 0
        self.timing_64ths = step_num * 16  # Default 16th notes
        self.use_semitones = False

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

        # Note index selector (which note from held notes)
        self.note_selector = QSpinBox()
        self.note_selector.setRange(0, 15)
        self.note_selector.setValue(0)
        self.note_selector.setPrefix("Note: ")
        self.note_selector.setToolTip("Which held note to play (0=lowest)")
        interval_layout.addWidget(self.note_selector)

        # Octave offset selector
        self.octave_selector = QSpinBox()
        self.octave_selector.setRange(-24, 24)
        self.octave_selector.setValue(0)
        self.octave_selector.setPrefix("Oct: ")
        self.octave_selector.setSuffix(" semi")
        self.octave_selector.setToolTip("Octave offset in semitones")
        interval_layout.addWidget(self.octave_selector)

        # Timing offset
        self.timing_selector = QSpinBox()
        self.timing_selector.setRange(0, 1024)
        self.timing_selector.setValue(self.timing_64ths)
        self.timing_selector.setPrefix("T: ")
        self.timing_selector.setSuffix("/64")
        self.timing_selector.setToolTip("Timing in 64th notes")
        interval_layout.addWidget(self.timing_selector)

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
            'note_index': self.note_selector.value(),
            'octave_offset': self.octave_selector.value(),
            'timing_64ths': self.timing_selector.value()
        }

    def set_step_data(self, data):
        """Load step data from dict"""
        if 'velocity' in data:
            self.velocity_bar.set_velocity(data['velocity'])
        if 'note_index' in data:
            self.note_selector.setValue(data['note_index'])
        if 'octave_offset' in data:
            self.octave_selector.setValue(data['octave_offset'])
        if 'timing_64ths' in data:
            self.timing_selector.setValue(data['timing_64ths'])


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
            'octave_range': 1,
            'steps': []
        }

        # Initialize with 4 default steps
        for i in range(4):
            self.preset_data['steps'].append({
                'velocity': 200,
                'note_index': i % 4,
                'octave_offset': 0,
                'timing_64ths': i * 16
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

        # Name
        lbl_name = QLabel("Name:")
        self.edit_name = QLineEdit()
        self.edit_name.setMaxLength(15)
        self.edit_name.setText(self.preset_data['name'])
        params_layout.addWidget(lbl_name, 0, 0)
        params_layout.addWidget(self.edit_name, 0, 1)

        # Pattern length
        lbl_length = QLabel("Pattern Length:")
        self.spin_length = QSpinBox()
        self.spin_length.setRange(1, 1024)
        self.spin_length.setValue(64)
        self.spin_length.setSuffix(" /64ths")
        self.spin_length.setToolTip("Pattern length in 64th notes (64 = 1 bar)")
        params_layout.addWidget(lbl_length, 1, 0)
        params_layout.addWidget(self.spin_length, 1, 1)

        # Gate length
        lbl_gate = QLabel("Gate Length:")
        self.spin_gate = QSpinBox()
        self.spin_gate.setRange(10, 100)
        self.spin_gate.setValue(80)
        self.spin_gate.setSuffix("%")
        self.spin_gate.setToolTip("Note gate length percentage")
        params_layout.addWidget(lbl_gate, 2, 0)
        params_layout.addWidget(self.spin_gate, 2, 1)

        # Octave range
        lbl_octave = QLabel("Octave Range:")
        self.spin_octave = QSpinBox()
        self.spin_octave.setRange(1, 4)
        self.spin_octave.setValue(1)
        self.spin_octave.setToolTip("Octave range for preset")
        params_layout.addWidget(lbl_octave, 3, 0)
        params_layout.addWidget(self.spin_octave, 3, 1)

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

        # === Step Count Control ===
        step_control_layout = QHBoxLayout()
        lbl_steps = QLabel("Number of Steps:")
        self.spin_step_count = QSpinBox()
        self.spin_step_count.setRange(1, 16)
        self.spin_step_count.setValue(4)
        self.spin_step_count.valueChanged.connect(self.on_step_count_changed)
        self.btn_apply_steps = QPushButton("Apply Step Count")
        self.btn_apply_steps.clicked.connect(self.rebuild_steps)

        step_control_layout.addWidget(lbl_steps)
        step_control_layout.addWidget(self.spin_step_count)
        step_control_layout.addWidget(self.btn_apply_steps)
        step_control_layout.addStretch()

        main_layout.addLayout(step_control_layout)

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
        step_count = self.spin_step_count.value()
        for i in range(step_count):
            step_widget = StepWidget(i)

            # Load existing step data if available
            if i < len(self.preset_data['steps']):
                step_widget.set_step_data(self.preset_data['steps'][i])

            self.step_widgets.append(step_widget)
            self.step_layout.addWidget(step_widget)

        self.step_layout.addStretch()
        self.update_status(f"Rebuilt sequencer with {step_count} steps")

    def on_step_count_changed(self, value):
        """Step count spinbox changed"""
        self.update_status(f"Step count set to {value}. Click 'Apply Step Count' to rebuild.")

    def clear_all_steps(self):
        """Clear all step data"""
        for widget in self.step_widgets:
            widget.set_step_data({
                'velocity': 0,
                'note_index': 0,
                'octave_offset': 0,
                'timing_64ths': widget.step_num * 16
            })
        self.update_status("All steps cleared")

    def reset_all_velocity(self):
        """Reset all velocities to 200"""
        for widget in self.step_widgets:
            widget.velocity_bar.set_velocity(200)
        self.update_status("All velocities reset to 200")

    def quick_ascending(self):
        """Quick pattern: ascending notes"""
        for i, widget in enumerate(self.step_widgets):
            widget.note_selector.setValue(i % 4)
            widget.octave_selector.setValue(0)
            widget.timing_selector.setValue(i * 16)
            widget.velocity_bar.set_velocity(200)
        self.update_status("Applied ascending pattern")

    def quick_descending(self):
        """Quick pattern: descending notes"""
        for i, widget in enumerate(self.step_widgets):
            widget.note_selector.setValue(3 - (i % 4))
            widget.octave_selector.setValue(0)
            widget.timing_selector.setValue(i * 16)
            widget.velocity_bar.set_velocity(200)
        self.update_status("Applied descending pattern")

    def gather_preset_data(self):
        """Gather current UI state into preset_data dict"""
        self.preset_data['name'] = self.edit_name.text()[:15]
        self.preset_data['pattern_length_64ths'] = self.spin_length.value()
        self.preset_data['gate_length_percent'] = self.spin_gate.value()
        self.preset_data['octave_range'] = self.spin_octave.value()

        # Gather step data
        self.preset_data['steps'] = []
        for widget in self.step_widgets:
            self.preset_data['steps'].append(widget.get_step_data())

        self.preset_data['note_count'] = len(self.step_widgets)

    def apply_preset_data(self):
        """Apply preset_data to UI"""
        self.edit_name.setText(self.preset_data.get('name', 'User Preset'))
        self.spin_length.setValue(self.preset_data.get('pattern_length_64ths', 64))
        self.spin_gate.setValue(self.preset_data.get('gate_length_percent', 80))
        self.spin_octave.setValue(self.preset_data.get('octave_range', 1))

        # Apply step data
        steps = self.preset_data.get('steps', [])
        self.spin_step_count.setValue(len(steps))
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
                octave_range = data[25] if len(data) > 25 else 1

                self.preset_data['name'] = name
                self.preset_data['note_count'] = note_count
                self.preset_data['pattern_length_64ths'] = pattern_length
                self.preset_data['gate_length_percent'] = gate_length
                self.preset_data['octave_range'] = octave_range

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
        params.append(self.preset_data['octave_range'])

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
