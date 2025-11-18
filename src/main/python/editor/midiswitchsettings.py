# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import json
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy, QGridLayout, QLabel, \
    QComboBox, QCheckBox, QGroupBox, QVBoxLayout, QFileDialog, QMessageBox, QSpinBox, QScrollArea

from widgets.combo_box import ArrowComboBox
from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard


class MIDIswitchSettingsConfigurator(BasicEditor):
    
    def __init__(self):
        super().__init__()
        
        # HID Command constants (0xB6-0xBB range)
        self.HID_CMD_SET_KEYBOARD_CONFIG = 0xB6
        self.HID_CMD_GET_KEYBOARD_CONFIG = 0xB7
        self.HID_CMD_RESET_KEYBOARD_CONFIG = 0xB8
        self.HID_CMD_SAVE_KEYBOARD_SLOT = 0xB9
        self.HID_CMD_LOAD_KEYBOARD_SLOT = 0xBA
        self.HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED = 0xBB
        
        self.MANUFACTURER_ID = 0x7D
        self.SUB_ID = 0x00
        self.DEVICE_ID = 0x4D
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create scrollable main widget (like Loop Manager)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        main_widget = QWidget()
        main_widget.setStyleSheet("QComboBox { max-width: 150px; }")
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 5, 10, 10)
        main_widget.setLayout(main_layout)
        scroll.setWidget(main_widget)

        self.addWidget(scroll)
        
        # Basic Settings Group
        basic_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Basic Settings"))
        basic_layout = QGridLayout()
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # Transpose
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 0, 0)
        self.transpose_number = ArrowComboBox()
        self.transpose_number.setMaximumWidth(100)
        for i in range(-64, 65):
            self.transpose_number.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number.setCurrentIndex(64)  # Default to 0
        basic_layout.addWidget(self.transpose_number, 0, 1)

        # Channel
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 0, 2)
        self.channel_number = ArrowComboBox()
        self.channel_number.setMaximumWidth(80)
        for i in range(16):
            self.channel_number.addItem(str(i + 1), i)
        basic_layout.addWidget(self.channel_number, 0, 3)

        # Velocity
        basic_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 0, 4)
        self.velocity_number = ArrowComboBox()
        self.velocity_number.setMaximumWidth(80)
        for i in range(1, 128):
            self.velocity_number.addItem(str(i), i)
        self.velocity_number.setCurrentIndex(126)  # Default to 127
        basic_layout.addWidget(self.velocity_number, 0, 5)
        
        # Loop Settings Group
        loop_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Loop Settings"))
        loop_layout = QGridLayout()
        loop_group.setLayout(loop_layout)
        main_layout.addWidget(loop_group)
        
        # Unsynced Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sync Mode:")), 0, 0)
        self.unsynced_mode = ArrowComboBox()
        self.unsynced_mode.addItem("Loop", 0)
        self.unsynced_mode.addItem("BPM 1", 1)
        self.unsynced_mode.addItem("No Sync", 2)
        loop_layout.addWidget(self.unsynced_mode, 0, 1)
                
        # Sample Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Sample Mode:")), 0, 2)
        self.sample_mode = ArrowComboBox()
        self.sample_mode.addItem("Off", False)
        self.sample_mode.addItem("On", True)
        loop_layout.addWidget(self.sample_mode, 0, 3)
        
        # Loop Messaging
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Loop Messaging:")), 1, 0)
        self.loop_messaging_enabled = ArrowComboBox()
        self.loop_messaging_enabled.addItem("Off", False)
        self.loop_messaging_enabled.addItem("On", True)
        loop_layout.addWidget(self.loop_messaging_enabled, 1, 1)
        
        # Messaging Channel
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Messaging Channel:")), 1, 2)
        self.loop_messaging_channel = ArrowComboBox()
        for i in range(1, 17):
            self.loop_messaging_channel.addItem(str(i), i)
        self.loop_messaging_channel.setCurrentIndex(15)  # Default to 16
        loop_layout.addWidget(self.loop_messaging_channel, 1, 3)
        
        # Sync MIDI Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "ThruLoop:")), 2, 0)
        self.sync_midi_mode = ArrowComboBox()
        self.sync_midi_mode.addItem("Off", False)
        self.sync_midi_mode.addItem("On", True)
        loop_layout.addWidget(self.sync_midi_mode, 2, 1)
        
        # Restart Mode
        loop_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Restart Mode:")), 2, 2)
        self.alternate_restart_mode = ArrowComboBox()
        self.alternate_restart_mode.addItem("Restart CC", False)
        self.alternate_restart_mode.addItem("Stop+Start", True)
        loop_layout.addWidget(self.alternate_restart_mode, 2, 3)
        
        # Advanced Settings Group
        advanced_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "Advanced Settings"))
        advanced_layout = QGridLayout()
        advanced_group.setLayout(advanced_layout)
        main_layout.addWidget(advanced_group)
        
        # Velocity Interval
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Interval:")), 0, 0)
        self.velocity_sensitivity = ArrowComboBox()
        for i in range(1, 11):
            self.velocity_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.velocity_sensitivity, 0, 1)
        
        # CC Interval
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Interval:")), 0, 2)
        self.cc_sensitivity = ArrowComboBox()
        for i in range(1, 17):
            self.cc_sensitivity.addItem(str(i), i)
        advanced_layout.addWidget(self.cc_sensitivity, 0, 3)
        
        # Velocity Shuffle
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity Shuffle:")), 1, 0)
        self.random_velocity_modifier = ArrowComboBox()
        for i in range(17):
            self.random_velocity_modifier.addItem(str(i), i)
        advanced_layout.addWidget(self.random_velocity_modifier, 1, 1)
        
        # OLED Keyboard
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "OLED Keyboard:")), 1, 2)
        self.oled_keyboard = ArrowComboBox()
        self.oled_keyboard.addItem("Style 1", 0)
        self.oled_keyboard.addItem("Style 2", 12)
        advanced_layout.addWidget(self.oled_keyboard, 1, 3)
        
        # SmartChord Lights
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Overdub Mode:")), 2, 0)
        self.smart_chord_light = ArrowComboBox()
        self.smart_chord_light.addItem("Basic Overdub", 0)
        self.smart_chord_light.addItem("8 Track Looper", 1)
        advanced_layout.addWidget(self.smart_chord_light, 2, 1)
        
        # SC Light Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "SC Light Mode:")), 2, 2)
        self.smart_chord_light_mode = ArrowComboBox()
        self.smart_chord_light_mode.addItem("Custom", 0)
        self.smart_chord_light_mode.addItem("Off", 2)
        self.smart_chord_light_mode.addItem("Guitar Low E", 3)
        self.smart_chord_light_mode.addItem("Guitar High E", 4)
        advanced_layout.addWidget(self.smart_chord_light_mode, 2, 3)
        
        # RGB Layer Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "RGB Layer Mode:")), 3, 0)
        self.custom_layer_animations = ArrowComboBox()
        self.custom_layer_animations.addItem("Off", False)
        self.custom_layer_animations.addItem("On", True)
        advanced_layout.addWidget(self.custom_layer_animations, 3, 1)
        
        # Colorblind Mode
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Colorblind Mode:")), 3, 2)
        self.colorblind_mode = ArrowComboBox()
        self.colorblind_mode.addItem("Off", 0)
        self.colorblind_mode.addItem("On", 1)
        advanced_layout.addWidget(self.colorblind_mode, 3, 3)
        
        # CC Loop Recording
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "CC Loop Recording:")), 4, 0)
        self.cc_loop_recording = ArrowComboBox()
        self.cc_loop_recording.addItem("Off", False)
        self.cc_loop_recording.addItem("On", True)
        advanced_layout.addWidget(self.cc_loop_recording, 4, 1)
        
        # True Sustain
        advanced_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "True Sustain:")), 4, 2)
        self.true_sustain = ArrowComboBox()
        self.true_sustain.addItem("Off", False)
        self.true_sustain.addItem("On", True)
        advanced_layout.addWidget(self.true_sustain, 4, 3)
        
        # KeySplit Modes Group
        keysplit_modes_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "KeySplit Modes"))
        keysplit_modes_layout = QGridLayout()
        keysplit_modes_group.setLayout(keysplit_modes_layout)
        main_layout.addWidget(keysplit_modes_group)
        
        # Channel Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 0, 0)
        self.key_split_status = ArrowComboBox()
        self.key_split_status.addItem("Disable Keysplit", 0)
        self.key_split_status.addItem("KeySplit On", 1)
        self.key_split_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_status, 0, 1)
        
        # Transpose Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 0, 2)
        self.key_split_transpose_status = ArrowComboBox()
        self.key_split_transpose_status.addItem("Disable Keysplit", 0)
        self.key_split_transpose_status.addItem("KeySplit On", 1)
        self.key_split_transpose_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_transpose_status, 0, 3)
        
        # Velocity Mode
        keysplit_modes_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 0, 4)
        self.key_split_velocity_status = ArrowComboBox()
        self.key_split_velocity_status.addItem("Disable Keysplit", 0)
        self.key_split_velocity_status.addItem("KeySplit On", 1)
        self.key_split_velocity_status.addItem("TripleSplit On", 2)
        keysplit_modes_layout.addWidget(self.key_split_velocity_status, 0, 5)
        
        # KeySplit Settings Group
        keysplit_group = QGroupBox(tr("MIDIswitchSettingsConfigurator", "KeySplit & TripleSplit Settings"))
        keysplit_layout = QGridLayout()
        keysplit_group.setLayout(keysplit_layout)
        main_layout.addWidget(keysplit_group)
        
        # KeySplit settings (left column)
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "KeySplit Settings")), 0, 0, 1, 2)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 1, 0)
        self.key_split_channel = ArrowComboBox()
        for i in range(16):
            self.key_split_channel.addItem(str(i + 1), i)
        keysplit_layout.addWidget(self.key_split_channel, 1, 1)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 2, 0)
        self.transpose_number2 = ArrowComboBox()
        for i in range(-64, 65):
            self.transpose_number2.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number2.setCurrentIndex(64)  # Default to 0
        keysplit_layout.addWidget(self.transpose_number2, 2, 1)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 3, 0)
        self.velocity_number2 = ArrowComboBox()
        for i in range(1, 128):
            self.velocity_number2.addItem(str(i), i)
        self.velocity_number2.setCurrentIndex(126)  # Default to 127
        keysplit_layout.addWidget(self.velocity_number2, 3, 1)
        
        # TripleSplit settings (right column)
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "TripleSplit Settings")), 0, 2, 1, 2)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Channel:")), 1, 2)
        self.key_split2_channel = ArrowComboBox()
        for i in range(16):
            self.key_split2_channel.addItem(str(i + 1), i)
        keysplit_layout.addWidget(self.key_split2_channel, 1, 3)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Transpose:")), 2, 2)
        self.transpose_number3 = ArrowComboBox()
        for i in range(-64, 65):
            self.transpose_number3.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_number3.setCurrentIndex(64)  # Default to 0
        keysplit_layout.addWidget(self.transpose_number3, 2, 3)
        
        keysplit_layout.addWidget(QLabel(tr("MIDIswitchSettingsConfigurator", "Velocity:")), 3, 2)
        self.velocity_number3 = ArrowComboBox()
        for i in range(1, 128):
            self.velocity_number3.addItem(str(i), i)
        self.velocity_number3.setCurrentIndex(126)  # Default to 127
        keysplit_layout.addWidget(self.velocity_number3, 3, 3)

        # Buttons
        main_layout.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Default and File buttons
        save_default_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Save as Default"))
        save_default_btn.setMinimumHeight(35)
        save_default_btn.setMinimumWidth(140)
        save_default_btn.clicked.connect(lambda: self.on_save_slot(0))
        buttons_layout.addWidget(save_default_btn)

        load_default_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Load Default"))
        load_default_btn.setMinimumHeight(35)
        load_default_btn.setMinimumWidth(130)
        load_default_btn.clicked.connect(lambda: self.on_load_slot(0))
        buttons_layout.addWidget(load_default_btn)

        reset_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Reset to Defaults"))
        reset_btn.setMinimumHeight(35)
        reset_btn.setMinimumWidth(150)
        reset_btn.clicked.connect(self.on_reset)
        buttons_layout.addWidget(reset_btn)

        save_file_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Save to File"))
        save_file_btn.setMinimumHeight(35)
        save_file_btn.setMinimumWidth(130)
        save_file_btn.clicked.connect(self.on_save_to_file)
        buttons_layout.addWidget(save_file_btn)

        load_file_btn = QPushButton(tr("MIDIswitchSettingsConfigurator", "Load from File"))
        load_file_btn.setMinimumHeight(35)
        load_file_btn.setMinimumWidth(140)
        load_file_btn.clicked.connect(self.on_load_from_file)
        buttons_layout.addWidget(load_file_btn)

        main_layout.addLayout(buttons_layout)

        # Save slot buttons
        save_slots_layout = QHBoxLayout()
        save_slots_layout.addStretch()
        for i in range(1, 5):
            btn = QPushButton(tr("MIDIswitchSettingsConfigurator", f"Save to Slot {i}"))
            btn.setMinimumHeight(35)
            btn.setMinimumWidth(120)
            btn.clicked.connect(lambda checked, slot=i: self.on_save_slot(slot))
            save_slots_layout.addWidget(btn)
        main_layout.addLayout(save_slots_layout)

        # Load slot buttons
        load_slots_layout = QHBoxLayout()
        load_slots_layout.addStretch()
        for i in range(1, 5):
            btn = QPushButton(tr("MIDIswitchSettingsConfigurator", f"Load Slot {i}"))
            btn.setMinimumHeight(35)
            btn.setMinimumWidth(120)
            btn.clicked.connect(lambda checked, slot=i: self.on_load_slot(slot))
            load_slots_layout.addWidget(btn)
        main_layout.addLayout(load_slots_layout)
        
    def send_hid_packet(self, command, data):
        """Send HID packet to device"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            return
        
        packet = bytearray(32)
        packet[0] = self.MANUFACTURER_ID
        packet[1] = self.SUB_ID
        packet[2] = self.DEVICE_ID
        packet[3] = command
        packet[4] = 0  # Macro num
        packet[5] = 0  # Status
        
        # Copy data payload (max 26 bytes)
        data_len = min(len(data), 26)
        packet[6:6+data_len] = data[:data_len]
        
        try:
            self.device.keyboard.via_command(packet)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send command: {str(e)}")
    
    def get_current_settings(self):
        """Get current UI settings as dictionary"""
        return {
            "velocity_sensitivity": self.velocity_sensitivity.currentData(),
            "cc_sensitivity": self.cc_sensitivity.currentData(),
            "channel_number": self.channel_number.currentData(),
            "transpose_number": self.transpose_number.currentData(),
            "transpose_number2": self.transpose_number2.currentData(),
            "transpose_number3": self.transpose_number3.currentData(),
            "velocity_number": self.velocity_number.currentData(),
            "velocity_number2": self.velocity_number2.currentData(),
            "velocity_number3": self.velocity_number3.currentData(),
            "random_velocity_modifier": self.random_velocity_modifier.currentData(),
            "oled_keyboard": self.oled_keyboard.currentData(),
            "smart_chord_light": self.smart_chord_light.currentData(),
            "smart_chord_light_mode": self.smart_chord_light_mode.currentData(),
            "key_split_channel": self.key_split_channel.currentData(),
            "key_split2_channel": self.key_split2_channel.currentData(),
            "key_split_status": self.key_split_status.currentData(),
            "key_split_transpose_status": self.key_split_transpose_status.currentData(),
            "key_split_velocity_status": self.key_split_velocity_status.currentData(),
            "custom_layer_animations_enabled": self.custom_layer_animations.currentData(),
            "unsynced_mode_active": self.unsynced_mode.currentData(),
            "sample_mode_active": self.sample_mode.currentData(),
            "loop_messaging_enabled": self.loop_messaging_enabled.currentData(),
            "loop_messaging_channel": self.loop_messaging_channel.currentData(),
            "sync_midi_mode": self.sync_midi_mode.currentData(),
            "alternate_restart_mode": self.alternate_restart_mode.currentData(),
            "colorblindmode": self.colorblind_mode.currentData(),
            "cclooprecording": self.cc_loop_recording.currentData(),
            "truesustain": self.true_sustain.currentData()
        }
    
    def apply_settings(self, settings):
        """Apply settings dictionary to UI"""
        # Set combo box values by finding matching data
        def set_combo_by_data(combo, value):
            for i in range(combo.count()):
                if combo.itemData(i) == value:
                    combo.setCurrentIndex(i)
                    break
        
        set_combo_by_data(self.velocity_sensitivity, settings.get("velocity_sensitivity", 1))
        set_combo_by_data(self.cc_sensitivity, settings.get("cc_sensitivity", 1))
        set_combo_by_data(self.channel_number, settings.get("channel_number", 0))
        set_combo_by_data(self.transpose_number, settings.get("transpose_number", 0))
        set_combo_by_data(self.transpose_number2, settings.get("transpose_number2", 0))
        set_combo_by_data(self.transpose_number3, settings.get("transpose_number3", 0))
        set_combo_by_data(self.velocity_number, settings.get("velocity_number", 127))
        set_combo_by_data(self.velocity_number2, settings.get("velocity_number2", 127))
        set_combo_by_data(self.velocity_number3, settings.get("velocity_number3", 127))
        set_combo_by_data(self.random_velocity_modifier, settings.get("random_velocity_modifier", 0))
        set_combo_by_data(self.oled_keyboard, settings.get("oled_keyboard", 0))
        set_combo_by_data(self.smart_chord_light, settings.get("smart_chord_light", 0))
        set_combo_by_data(self.smart_chord_light_mode, settings.get("smart_chord_light_mode", 0))
        set_combo_by_data(self.key_split_channel, settings.get("key_split_channel", 0))
        set_combo_by_data(self.key_split2_channel, settings.get("key_split2_channel", 0))
        set_combo_by_data(self.key_split_status, settings.get("key_split_status", 0))
        set_combo_by_data(self.key_split_transpose_status, settings.get("key_split_transpose_status", 0))
        set_combo_by_data(self.key_split_velocity_status, settings.get("key_split_velocity_status", 0))
        set_combo_by_data(self.custom_layer_animations, settings.get("custom_layer_animations_enabled", False))
        set_combo_by_data(self.unsynced_mode, settings.get("unsynced_mode_active", 0))
        set_combo_by_data(self.sample_mode, settings.get("sample_mode_active", False))
        set_combo_by_data(self.loop_messaging_enabled, settings.get("loop_messaging_enabled", False))
        set_combo_by_data(self.loop_messaging_channel, settings.get("loop_messaging_channel", 16))
        set_combo_by_data(self.sync_midi_mode, settings.get("sync_midi_mode", False))
        set_combo_by_data(self.alternate_restart_mode, settings.get("alternate_restart_mode", False))
        set_combo_by_data(self.colorblind_mode, settings.get("colorblindmode", 0))
        set_combo_by_data(self.cc_loop_recording, settings.get("cclooprecording", False))
        set_combo_by_data(self.true_sustain, settings.get("truesustain", False))
    
    # Rest of the methods remain the same as original...
    def pack_basic_data(self, settings):
        """Pack basic settings into 26-byte structure"""
        data = bytearray(26)
        
        # Pack 32-bit integers (little endian)
        struct.pack_into('<I', data, 0, settings["velocity_sensitivity"])  # 4 bytes
        struct.pack_into('<I', data, 4, settings["cc_sensitivity"])  # 4 bytes
        
        # Pack single bytes
        offset = 8
        data[offset] = settings["channel_number"]; offset += 1
        data[offset] = settings["transpose_number"] & 0xFF; offset += 1  # Handle signed
        data[offset] = 0; offset += 1  # octave_number (not in UI)
        data[offset] = settings["transpose_number2"] & 0xFF; offset += 1  # Handle signed
        data[offset] = 0; offset += 1  # octave_number2 (not in UI) 
        data[offset] = settings["transpose_number3"] & 0xFF; offset += 1  # Handle signed
        data[offset] = 0; offset += 1  # octave_number3 (not in UI)
        data[offset] = settings["velocity_number"]; offset += 1
        data[offset] = settings["velocity_number2"]; offset += 1
        data[offset] = settings["velocity_number3"]; offset += 1
        data[offset] = settings["random_velocity_modifier"]; offset += 1
        
        # Pack 32-bit integer for oled_keyboard (4 bytes)
        struct.pack_into('<I', data, offset, settings["oled_keyboard"]); offset += 4
        
        # Pack remaining single bytes
        data[offset] = settings["smart_chord_light"]; offset += 1
        data[offset] = settings["smart_chord_light_mode"]; offset += 1
        
        return data
    
    def pack_advanced_data(self, settings):
        """Pack advanced settings into 15-byte structure"""
        data = bytearray(15)
        
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
        
        return data
    
    def on_save_slot(self, slot):
        """Save current settings to slot"""
        try:
            settings = self.get_current_settings()
            
            # Pack and send basic data with slot number
            basic_data = self.pack_basic_data(settings)
            data_with_slot = bytearray([slot]) + basic_data
            self.send_hid_packet(self.HID_CMD_SAVE_KEYBOARD_SLOT, data_with_slot)
            
            # Small delay then send advanced data
            QtCore.QTimer.singleShot(50, lambda: self._send_advanced_data(settings))
            
            slot_name = "default settings" if slot == 0 else f"Slot {slot}"
            QMessageBox.information(self, "Success", f"Settings saved as {slot_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save to slot {slot}: {str(e)}")
    
    def _send_advanced_data(self, settings):
        """Send advanced data (helper for save operations)"""
        advanced_data = self.pack_advanced_data(settings)
        self.send_hid_packet(self.HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED, advanced_data)
    
    def on_load_slot(self, slot):
        """Load settings from slot"""
        try:
            self.send_hid_packet(self.HID_CMD_LOAD_KEYBOARD_SLOT, [slot])
            slot_name = "default settings" if slot == 0 else f"Slot {slot}"
            QMessageBox.information(self, "Info", f"Load request sent for {slot_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load from slot {slot}: {str(e)}")
    
    def on_reset(self):
        """Reset to default settings"""
        try:
            reply = QMessageBox.question(self, "Confirm Reset", 
                                       "Reset all keyboard settings to defaults? This cannot be undone.",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.send_hid_packet(self.HID_CMD_RESET_KEYBOARD_CONFIG, [])
                # Also reset UI to defaults
                self.reset_ui_to_defaults()
                QMessageBox.information(self, "Success", "Settings reset to defaults")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset settings: {str(e)}")
    
    def reset_ui_to_defaults(self):
        """Reset UI to default values"""
        defaults = {
            "velocity_sensitivity": 1,
            "cc_sensitivity": 1,
            "channel_number": 0,
            "transpose_number": 0,
            "transpose_number2": 0,
            "transpose_number3": 0,
            "velocity_number": 127,
            "velocity_number2": 127,
            "velocity_number3": 127,
            "random_velocity_modifier": 0,
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
            "truesustain": False
        }
        self.apply_settings(defaults)
    
    def on_save_to_file(self):
        """Save current configuration to JSON file"""
        try:
            config = {
                "version": "1.0",
                "settings": self.get_current_settings()
            }
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Keyboard Configuration", "", "JSON Files (*.json)"
            )
            if filename:
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                QMessageBox.information(self, "Success", "Configuration saved to file!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save to file: {str(e)}")
    
    def on_load_from_file(self):
        """Load configuration from JSON file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load Keyboard Configuration", "", "JSON Files (*.json)"
            )
            if filename:
                with open(filename, 'r') as f:
                    config = json.load(f)
                if "settings" in config:
                    self.apply_settings(config["settings"])
                    QMessageBox.information(self, "Success", "Configuration loaded from file!")
                else:
                    QMessageBox.critical(self, "Error", "Invalid configuration file format")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load from file: {str(e)}")
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)
    
    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return