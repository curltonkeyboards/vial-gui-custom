# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import json
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy, QGridLayout, QLabel, \
    QComboBox, QCheckBox, QGroupBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QFileDialog, \
    QMessageBox, QHeaderView

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard


class ThruLoopConfigurator(BasicEditor):
    
    def __init__(self):
        super().__init__()
        
        # HID Command constants (0xB0-0xB5 range)
        self.HID_CMD_SET_LOOP_CONFIG = 0xB0
        self.HID_CMD_SET_MAIN_LOOP_CCS = 0xB1
        self.HID_CMD_SET_OVERDUB_CCS = 0xB2
        self.HID_CMD_SET_NAVIGATION_CONFIG = 0xB3
        self.HID_CMD_GET_ALL_CONFIG = 0xB4
        self.HID_CMD_RESET_LOOP_CONFIG = 0xB5
        
        self.MANUFACTURER_ID = 0x7D
        self.SUB_ID = 0x00
        self.DEVICE_ID = 0x4D
        
        # Initialize references to None - will be set in setup_ui
        self.single_loopchop_label = None
        self.master_cc = None
        self.single_loopchop_widgets = []
        self.nav_widget = None
        
        self.setup_ui()
        
    def setup_ui(self):
        self.addStretch()
        
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.addWidget(main_widget)
        self.setAlignment(main_widget, QtCore.Qt.AlignHCenter)
        
        # Basic Settings Group
        basic_group = QGroupBox(tr("ThruLoopConfigurator", "Basic Settings"))
        basic_layout = QGridLayout()
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # ThruLoop Channel
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "ThruLoop Channel")), 0, 0)
        self.loop_channel = QComboBox()
        for i in range(1, 17):
            self.loop_channel.addItem(f"Channel {i}", i)
        self.loop_channel.setCurrentIndex(15)  # Default to channel 16
        basic_layout.addWidget(self.loop_channel, 0, 1)
        
        # Send Restart Messages
        self.sync_midi = QCheckBox(tr("ThruLoopConfigurator", "Send Restart Messages"))
        basic_layout.addWidget(self.sync_midi, 1, 0, 1, 2)
        
        # Alternate Restart Mode
        self.alternate_restart = QCheckBox(tr("ThruLoopConfigurator", "Alternate Restart Mode"))
        basic_layout.addWidget(self.alternate_restart, 2, 0, 1, 2)
        
        # CC Loop Recording
        self.cc_loop_recording = QCheckBox(tr("ThruLoopConfigurator", "CC Loop Recording"))
        basic_layout.addWidget(self.cc_loop_recording, 3, 0, 1, 2)
        
        # Disable ThruLoop
        self.loop_enabled = QCheckBox(tr("ThruLoopConfigurator", "Disable ThruLoop"))
        basic_layout.addWidget(self.loop_enabled, 4, 0, 1, 2)
        
        # Restart CCs
        basic_layout.addWidget(QLabel(tr("ThruLoopConfigurator", "Restart CCs")), 5, 0, 1, 2)
        self.restart_combos = []
        for i in range(4):
            basic_layout.addWidget(QLabel(f"Loop {i+1}"), 6, i if i < 2 else i-2)
            combo = self.create_cc_combo()
            basic_layout.addWidget(combo, 7 if i >= 2 else 6, (i+1) if i < 2 else (i-1))
            self.restart_combos.append(combo)
        
        # Main Functions Table
        main_group = QGroupBox(tr("ThruLoopConfigurator", "Main Functions"))
        main_layout.addWidget(main_group)
        self.main_table = self.create_function_table()
        main_group_layout = QVBoxLayout()
        main_group_layout.addWidget(self.main_table)
        main_group.setLayout(main_group_layout)
        self.main_group = main_group
        
        # Overdub Functions Table  
        overdub_group = QGroupBox(tr("ThruLoopConfigurator", "Overdub Functions"))
        main_layout.addWidget(overdub_group)
        self.overdub_table = self.create_function_table()
        overdub_group_layout = QVBoxLayout()
        overdub_group_layout.addWidget(self.overdub_table)
        overdub_group.setLayout(overdub_group_layout)
        self.overdub_group = overdub_group
        
        # LoopChop Settings
        loopchop_group = QGroupBox(tr("ThruLoopConfigurator", "LoopChop"))
        loopchop_layout = QGridLayout()
        loopchop_group.setLayout(loopchop_layout)
        main_layout.addWidget(loopchop_group)
        self.loopchop_group = loopchop_group
        
        # Separate CCs for LoopChop checkbox
        self.separate_loopchop = QCheckBox(tr("ThruLoopConfigurator", "Separate CCs for LoopChop"))
        loopchop_layout.addWidget(self.separate_loopchop, 0, 0, 1, 2)
        
        # Single LoopChop CC - Store references properly
        self.single_loopchop_label = QLabel(tr("ThruLoopConfigurator", "Loop Chop"))
        loopchop_layout.addWidget(self.single_loopchop_label, 1, 0)
        self.master_cc = self.create_cc_combo()
        loopchop_layout.addWidget(self.master_cc, 1, 1)
        
        # Store widgets for show/hide operations
        self.single_loopchop_widgets = [self.single_loopchop_label, self.master_cc]
        
        # Individual LoopChop CCs (8 navigation CCs)
        nav_layout = QGridLayout()
        self.nav_combos = []
        for i in range(8):
            row = i // 4
            col = i % 4
            nav_layout.addWidget(QLabel(f"{i}/8"), row * 2, col)
            combo = self.create_cc_combo()
            nav_layout.addWidget(combo, row * 2 + 1, col)
            self.nav_combos.append(combo)
        
        self.nav_widget = QWidget()
        self.nav_widget.setLayout(nav_layout)
        loopchop_layout.addWidget(self.nav_widget, 2, 0, 1, 2)
        
        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton(tr("ThruLoopConfigurator", "Save Configuration"))
        save_btn.setMinimumHeight(35)
        save_btn.setMinimumWidth(150)
        save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_btn)

        load_btn = QPushButton(tr("ThruLoopConfigurator", "Load from Keyboard"))
        load_btn.setMinimumHeight(35)
        load_btn.setMinimumWidth(160)
        load_btn.clicked.connect(self.on_load_from_keyboard)
        buttons_layout.addWidget(load_btn)

        save_file_btn = QPushButton(tr("ThruLoopConfigurator", "Save to File"))
        save_file_btn.setMinimumHeight(35)
        save_file_btn.setMinimumWidth(130)
        save_file_btn.clicked.connect(self.on_save_to_file)
        buttons_layout.addWidget(save_file_btn)

        load_file_btn = QPushButton(tr("ThruLoopConfigurator", "Load from File"))
        load_file_btn.setMinimumHeight(35)
        load_file_btn.setMinimumWidth(130)
        load_file_btn.clicked.connect(self.on_load_from_file)
        buttons_layout.addWidget(load_file_btn)
        
        self.addLayout(buttons_layout)
        
        # Connect signals AFTER all widgets are created
        self.loop_enabled.stateChanged.connect(self.on_loop_enabled_changed)
        self.separate_loopchop.stateChanged.connect(self.on_separate_loopchop_changed)
        
        # Initialize UI state AFTER all widgets and connections are set up
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
    
    def create_cc_combo(self):
        combo = QComboBox()
        combo.addItem("None", 128)
        for i in range(128):
            combo.addItem(f"CC# {i}", i)
        combo.setCurrentIndex(0)  # Default to "None"
        return combo
    
    def create_function_table(self):
        table = QTableWidget(5, 4)  # 5 functions x 4 loops
        table.setHorizontalHeaderLabels([f"Loop {i+1}" for i in range(4)])
        table.setVerticalHeaderLabels([
            "Start Recording", "Stop Recording", "Start Playing", "Stop Playing", "Clear"
        ])

        # Remove cell padding and set styling
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: palette(mid);
            }
            QTableWidget::item {
                padding: 0px;
            }
            QHeaderView::section {
                padding: 4px;
                background: palette(button);
                border: 1px solid palette(mid);
            }
        """)

        # Fill table with CC combo boxes
        for row in range(5):
            for col in range(4):
                combo = self.create_cc_combo()
                combo.setStyleSheet("QComboBox { margin: 0px; border-radius: 0px; }")
                table.setCellWidget(row, col, combo)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMaximumHeight(200)
        return table
    
    def on_loop_enabled_changed(self):
        # When checked, ThruLoop is disabled (reversed logic from webapp)
        enabled = not self.loop_enabled.isChecked()
        self.main_group.setEnabled(enabled)
        self.overdub_group.setEnabled(enabled) 
        self.loopchop_group.setEnabled(enabled)
        for combo in self.restart_combos:
            combo.setEnabled(enabled)
    
    def on_separate_loopchop_changed(self):
        separate = self.separate_loopchop.isChecked()
        for widget in self.single_loopchop_widgets:
            if widget is not None:  # Safety check
                widget.setVisible(not separate)
        if self.nav_widget is not None:  # Safety check
            self.nav_widget.setVisible(separate)
    
    # ... rest of the methods remain the same ...
    def send_hid_packet(self, command, macro_num, data):
        """Send HID packet to device"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            return
        
        packet = bytearray(32)
        packet[0] = self.MANUFACTURER_ID
        packet[1] = self.SUB_ID  
        packet[2] = self.DEVICE_ID
        packet[3] = command
        packet[4] = macro_num
        packet[5] = 0  # Status
        
        # Copy data payload (max 26 bytes)
        data_len = min(len(data), 26)
        packet[6:6+data_len] = data[:data_len]
        
        try:
            self.device.keyboard.via_command(packet)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send command: {str(e)}")
    
    def get_cc_value(self, combo):
        return combo.currentData()
    
    def set_cc_value(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                break
    
    def get_table_cc_values(self, table):
        values = []
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                combo = table.cellWidget(row, col)
                values.append(self.get_cc_value(combo))
        return values
    
    def set_table_cc_values(self, table, values):
        idx = 0
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                if idx < len(values):
                    combo = table.cellWidget(row, col)
                    self.set_cc_value(combo, values[idx])
                    idx += 1
    
    def on_save(self):
        """Save all configuration to keyboard"""
        try:
            # 1. Send basic loop configuration
            loop_config_data = [
                0 if self.loop_enabled.isChecked() else 1,  # Reversed logic
                self.loop_channel.currentData(),
                1 if self.sync_midi.isChecked() else 0,
                1 if self.alternate_restart.isChecked() else 0,
            ]
            # Add restart CCs
            for combo in self.restart_combos:
                loop_config_data.append(self.get_cc_value(combo))
            # Add CC loop recording
            loop_config_data.append(1 if self.cc_loop_recording.isChecked() else 0)
            
            self.send_hid_packet(self.HID_CMD_SET_LOOP_CONFIG, 0, loop_config_data)
            
            # 2. Send main loop CCs
            main_values = self.get_table_cc_values(self.main_table)
            self.send_hid_packet(self.HID_CMD_SET_MAIN_LOOP_CCS, 0, main_values)
            
            # 3. Send overdub CCs  
            overdub_values = self.get_table_cc_values(self.overdub_table)
            self.send_hid_packet(self.HID_CMD_SET_OVERDUB_CCS, 0, overdub_values)
            
            # 4. Send navigation configuration
            nav_config_data = [
                1 if self.separate_loopchop.isChecked() else 0,
                self.get_cc_value(self.master_cc),
            ]
            for combo in self.nav_combos:
                nav_config_data.append(self.get_cc_value(combo))
            
            self.send_hid_packet(self.HID_CMD_SET_NAVIGATION_CONFIG, 0, nav_config_data)
            
            QMessageBox.information(self, "Success", "ThruLoop configuration saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")
    
    def on_load_from_keyboard(self):
        """Load configuration from keyboard"""
        try:
            self.send_hid_packet(self.HID_CMD_GET_ALL_CONFIG, 0, [])
            QMessageBox.information(self, "Info", "Load request sent to keyboard")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load from keyboard: {str(e)}")
    
    def get_current_config(self):
        """Get current UI configuration as dictionary"""
        config = {
            "version": "1.0",
            "loopEnabled": not self.loop_enabled.isChecked(),  # Reversed for file storage
            "loopChannel": self.loop_channel.currentData(), 
            "syncMidi": self.sync_midi.isChecked(),
            "alternateRestart": self.alternate_restart.isChecked(),
            "ccLoopRecording": self.cc_loop_recording.isChecked(),
            "separateLoopChopCC": self.separate_loopchop.isChecked(),
            "masterCC": self.get_cc_value(self.master_cc),
            "restartCCs": [self.get_cc_value(combo) for combo in self.restart_combos],
            "mainCCs": self.get_table_cc_values(self.main_table),
            "overdubCCs": self.get_table_cc_values(self.overdub_table),
            "navCCs": [self.get_cc_value(combo) for combo in self.nav_combos]
        }
        return config
    
    def apply_config(self, config):
        """Apply configuration dictionary to UI"""
        self.loop_enabled.setChecked(not config.get("loopEnabled", True))  # Reversed
        
        # Set channel
        for i in range(self.loop_channel.count()):
            if self.loop_channel.itemData(i) == config.get("loopChannel", 16):
                self.loop_channel.setCurrentIndex(i)
                break
        
        self.sync_midi.setChecked(config.get("syncMidi", False))
        self.alternate_restart.setChecked(config.get("alternateRestart", False))
        self.cc_loop_recording.setChecked(config.get("ccLoopRecording", False))
        self.separate_loopchop.setChecked(config.get("separateLoopChopCC", False))
        self.set_cc_value(self.master_cc, config.get("masterCC", 128))
        
        # Set restart CCs
        restart_ccs = config.get("restartCCs", [128] * 4)
        for i, combo in enumerate(self.restart_combos):
            if i < len(restart_ccs):
                self.set_cc_value(combo, restart_ccs[i])
        
        # Set main table CCs
        main_ccs = config.get("mainCCs", [128] * 20)
        self.set_table_cc_values(self.main_table, main_ccs)
        
        # Set overdub table CCs
        overdub_ccs = config.get("overdubCCs", [128] * 20)  
        self.set_table_cc_values(self.overdub_table, overdub_ccs)
        
        # Set navigation CCs
        nav_ccs = config.get("navCCs", [128] * 8)
        for i, combo in enumerate(self.nav_combos):
            if i < len(nav_ccs):
                self.set_cc_value(combo, nav_ccs[i])
        
        # Update UI state
        self.on_loop_enabled_changed()
        self.on_separate_loopchop_changed()
    
    def on_save_to_file(self):
        """Save configuration to JSON file"""
        try:
            config = self.get_current_config()
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save ThruLoop Configuration", "", "JSON Files (*.json)"
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
                self, "Load ThruLoop Configuration", "", "JSON Files (*.json)"
            )
            if filename:
                with open(filename, 'r') as f:
                    config = json.load(f)
                self.apply_config(config)
                QMessageBox.information(self, "Success", "Configuration loaded from file!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load from file: {str(e)}")
    
    def valid(self):
        return isinstance(self.device, VialKeyboard)
    
    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return