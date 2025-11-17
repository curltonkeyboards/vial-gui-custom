# SPDX-License-Identifier: GPL-2.0-or-later
import time
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSizePolicy,
                             QLabel, QComboBox, QListWidget, QListWidgetItem, QGroupBox,
                             QMessageBox, QCheckBox)

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard

try:
    import rtmidi
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False


class MIDIPatchBay(BasicEditor):
    """MIDI Patchbay tab for routing MIDI devices to/from MIDIswitch"""

    def __init__(self):
        super().__init__()

        self.midi_in = None
        self.midi_out = None
        self.midiswitch_output = None
        self.active_connections = {}  # {input_id: {input, output, callback}}
        self.device_refresh_timer = QTimer()
        self.device_refresh_timer.timeout.connect(self.refresh_devices)

        self.setup_ui()

        if MIDI_AVAILABLE:
            self.initialize_midi()
            self.device_refresh_timer.start(2000)  # Refresh every 2 seconds

    def setup_ui(self):
        self.addStretch()

        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.addWidget(main_widget)
        self.setAlignment(main_widget, QtCore.Qt.AlignHCenter)

        # Title
        title = QLabel(tr("MIDIPatchBay", "MIDI Patchbay"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title)

        if not MIDI_AVAILABLE:
            error_label = QLabel(tr("MIDIPatchBay",
                "MIDI support not available. Please install python-rtmidi:\npip install python-rtmidi"))
            error_label.setStyleSheet("color: red; padding: 20px;")
            error_label.setAlignment(QtCore.Qt.AlignCenter)
            main_layout.addWidget(error_label)
            self.addStretch()
            return

        # Connection section
        connection_group = QGroupBox(tr("MIDIPatchBay", "MIDI Device Routing"))
        connection_layout = QVBoxLayout()
        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)

        # Status display
        status_layout = QHBoxLayout()
        self.status_label = QLabel(tr("MIDIPatchBay", "MIDIswitch Status:"))
        status_layout.addWidget(self.status_label)

        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet(
            "color: red; font-size: 16px; font-weight: bold;"
        )
        status_layout.addWidget(self.status_indicator)
        status_layout.addStretch()
        connection_layout.addLayout(status_layout)

        # Device selector
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel(tr("MIDIPatchBay", "MIDI Input Device:")))

        self.device_selector = QComboBox()
        self.device_selector.setMinimumWidth(250)
        device_layout.addWidget(self.device_selector)

        self.connect_btn = QPushButton(tr("MIDIPatchBay", "Connect"))
        self.connect_btn.setMinimumHeight(30)
        self.connect_btn.clicked.connect(self.on_connect_device)
        device_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton(tr("MIDIPatchBay", "Disconnect"))
        self.disconnect_btn.setMinimumHeight(30)
        self.disconnect_btn.clicked.connect(self.on_disconnect_device)
        self.disconnect_btn.setEnabled(False)
        device_layout.addWidget(self.disconnect_btn)

        device_layout.addStretch()
        connection_layout.addLayout(device_layout)

        # Message filtering section
        filter_group = QGroupBox(tr("MIDIPatchBay", "Message Filtering (Optional)"))
        filter_layout = QVBoxLayout()
        filter_group.setLayout(filter_layout)
        connection_layout.addWidget(filter_group)

        self.filter_enabled = QCheckBox(tr("MIDIPatchBay", "Enable Message Filtering"))
        filter_layout.addWidget(self.filter_enabled)

        filter_types_layout = QHBoxLayout()
        self.filter_note = QCheckBox(tr("MIDIPatchBay", "Notes"))
        self.filter_cc = QCheckBox(tr("MIDIPatchBay", "CC"))
        self.filter_pc = QCheckBox(tr("MIDIPatchBay", "Program Change"))
        self.filter_pb = QCheckBox(tr("MIDIPatchBay", "Pitch Bend"))

        filter_types_layout.addWidget(self.filter_note)
        filter_types_layout.addWidget(self.filter_cc)
        filter_types_layout.addWidget(self.filter_pc)
        filter_types_layout.addWidget(self.filter_pb)
        filter_types_layout.addStretch()
        filter_layout.addLayout(filter_types_layout)

        # Active connections list
        connections_group = QGroupBox(tr("MIDIPatchBay", "Active Connections"))
        connections_layout = QVBoxLayout()
        connections_group.setLayout(connections_layout)
        main_layout.addWidget(connections_group)

        self.connections_list = QListWidget()
        self.connections_list.setMinimumHeight(150)
        connections_layout.addWidget(self.connections_list)

        disconnect_selected_btn = QPushButton(tr("MIDIPatchBay", "Disconnect Selected"))
        disconnect_selected_btn.clicked.connect(self.on_disconnect_selected)
        connections_layout.addWidget(disconnect_selected_btn)

        # Buttons
        self.addStretch()
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        refresh_btn = QPushButton(tr("MIDIPatchBay", "Refresh Devices"))
        refresh_btn.setMinimumHeight(35)
        refresh_btn.setMinimumWidth(150)
        refresh_btn.clicked.connect(self.refresh_devices)
        buttons_layout.addWidget(refresh_btn)

        disconnect_all_btn = QPushButton(tr("MIDIPatchBay", "Disconnect All"))
        disconnect_all_btn.setMinimumHeight(35)
        disconnect_all_btn.setMinimumWidth(150)
        disconnect_all_btn.clicked.connect(self.on_disconnect_all)
        buttons_layout.addWidget(disconnect_all_btn)

        self.addLayout(buttons_layout)

    def initialize_midi(self):
        """Initialize MIDI input/output"""
        try:
            self.midi_in = rtmidi.MidiIn()
            self.midi_out = rtmidi.MidiOut()
            self.refresh_devices()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to initialize MIDI: {str(e)}")

    def refresh_devices(self):
        """Refresh MIDI device lists"""
        if not MIDI_AVAILABLE or not self.midi_in or not self.midi_out:
            return

        try:
            # Save current selection
            current_text = self.device_selector.currentText()

            # Get available input devices
            input_ports = self.midi_in.get_ports()

            # Find MIDIswitch output
            output_ports = self.midi_out.get_ports()
            self.midiswitch_output = None
            for i, port in enumerate(output_ports):
                if "midiswitch" in port.lower() or "curlton" in port.lower():
                    self.midiswitch_output = (i, port)
                    break

            # Update status indicator
            if self.midiswitch_output:
                self.status_indicator.setStyleSheet(
                    "color: green; font-size: 16px; font-weight: bold;"
                )
                self.status_label.setText(
                    tr("MIDIPatchBay", f"MIDIswitch Found: {self.midiswitch_output[1]}")
                )
            else:
                self.status_indicator.setStyleSheet(
                    "color: red; font-size: 16px; font-weight: bold;"
                )
                self.status_label.setText(tr("MIDIPatchBay", "MIDIswitch Not Found"))

            # Update device selector (exclude MIDIswitch from inputs to prevent feedback)
            self.device_selector.clear()
            for i, port in enumerate(input_ports):
                if "midiswitch" not in port.lower() and "curlton" not in port.lower():
                    self.device_selector.addItem(port, i)

            # Restore selection if possible
            index = self.device_selector.findText(current_text)
            if index >= 0:
                self.device_selector.setCurrentIndex(index)

        except Exception as e:
            print(f"Error refreshing devices: {e}")

    def on_connect_device(self):
        """Connect selected MIDI input to MIDIswitch output"""
        if not self.midiswitch_output:
            QMessageBox.warning(None, "Warning",
                "MIDIswitch output not found. Please ensure the device is connected.")
            return

        if self.device_selector.currentIndex() < 0:
            QMessageBox.warning(None, "Warning", "Please select a MIDI input device.")
            return

        input_port_idx = self.device_selector.currentData()
        input_port_name = self.device_selector.currentText()

        # Check if already connected
        if input_port_idx in self.active_connections:
            QMessageBox.information(None, "Info", "This device is already connected.")
            return

        try:
            # Create new MIDI input for this connection
            midi_in = rtmidi.MidiIn()
            midi_in.open_port(input_port_idx)

            # Create MIDI output for MIDIswitch
            midi_out = rtmidi.MidiOut()
            midi_out.open_port(self.midiswitch_output[0])

            # Create callback for MIDI message routing
            def create_callback(output, filters):
                def callback(event, data=None):
                    message, deltatime = event

                    # Apply filtering if enabled
                    if filters['enabled'] and len(message) > 0:
                        status = message[0] & 0xF0

                        # Check message type
                        allow = False
                        if status in [0x80, 0x90] and filters['note']:  # Note On/Off
                            allow = True
                        elif status == 0xB0 and filters['cc']:  # CC
                            allow = True
                        elif status == 0xC0 and filters['pc']:  # Program Change
                            allow = True
                        elif status == 0xE0 and filters['pb']:  # Pitch Bend
                            allow = True
                        elif not any([filters['note'], filters['cc'], filters['pc'], filters['pb']]):
                            # If no filters selected, allow all
                            allow = True

                        if not allow:
                            return

                    # Filter out SysEx to prevent feedback loops
                    if len(message) > 0 and message[0] == 0xF0:
                        return

                    # Forward message to MIDIswitch
                    try:
                        output.send_message(message)
                    except:
                        pass

                return callback

            # Get filter settings
            filters = {
                'enabled': self.filter_enabled.isChecked(),
                'note': self.filter_note.isChecked(),
                'cc': self.filter_cc.isChecked(),
                'pc': self.filter_pc.isChecked(),
                'pb': self.filter_pb.isChecked()
            }

            callback = create_callback(midi_out, filters)
            midi_in.set_callback(callback)

            # Store connection
            self.active_connections[input_port_idx] = {
                'input': midi_in,
                'output': midi_out,
                'name': input_port_name,
                'callback': callback
            }

            # Update UI
            self.update_connections_list()
            self.disconnect_btn.setEnabled(True)

            QMessageBox.information(None, "Success",
                f"Connected {input_port_name} → {self.midiswitch_output[1]}")

        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to connect device: {str(e)}")

    def on_disconnect_device(self):
        """Disconnect currently selected device"""
        if self.device_selector.currentIndex() < 0:
            return

        input_port_idx = self.device_selector.currentData()
        self.disconnect_connection(input_port_idx)

    def on_disconnect_selected(self):
        """Disconnect selected connection from list"""
        current_item = self.connections_list.currentItem()
        if not current_item:
            return

        # Extract port index from item data
        input_port_idx = current_item.data(QtCore.Qt.UserRole)
        self.disconnect_connection(input_port_idx)

    def disconnect_connection(self, input_port_idx):
        """Disconnect a specific connection"""
        if input_port_idx not in self.active_connections:
            return

        try:
            conn = self.active_connections[input_port_idx]

            # Close MIDI ports
            conn['input'].close_port()
            conn['output'].close_port()

            # Remove from active connections
            del self.active_connections[input_port_idx]

            # Update UI
            self.update_connections_list()

            if len(self.active_connections) == 0:
                self.disconnect_btn.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to disconnect: {str(e)}")

    def on_disconnect_all(self):
        """Disconnect all active connections"""
        port_indices = list(self.active_connections.keys())
        for port_idx in port_indices:
            self.disconnect_connection(port_idx)

        QMessageBox.information(None, "Info", "All connections disconnected.")

    def update_connections_list(self):
        """Update the active connections list widget"""
        self.connections_list.clear()

        for port_idx, conn in self.active_connections.items():
            item_text = f"{conn['name']} → {self.midiswitch_output[1]}"
            item = QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, port_idx)
            self.connections_list.addItem(item)

    def valid(self):
        """This tab is always valid for MIDIswitch keyboards"""
        return isinstance(self.device, VialKeyboard) and MIDI_AVAILABLE

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        # Refresh devices when keyboard connects
        if MIDI_AVAILABLE:
            self.refresh_devices()

    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'device_refresh_timer'):
            self.device_refresh_timer.stop()

        # Disconnect all connections
        if hasattr(self, 'active_connections'):
            port_indices = list(self.active_connections.keys())
            for port_idx in port_indices:
                try:
                    self.disconnect_connection(port_idx)
                except:
                    pass
