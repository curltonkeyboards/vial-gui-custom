# SPDX-License-Identifier: GPL-2.0-or-later
"""
MIDIPatch - MIDI Routing/Patchbay Tab
Allows routing MIDI inputs to outputs with filtering and channel remapping
"""

import logging
from typing import Dict, Set, Optional, List
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QGroupBox, QGridLayout, QCheckBox, QScrollArea,
                              QSizePolicy, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore

from editor.basic_editor import BasicEditor
from widgets.combo_box import ArrowComboBox
from util import tr

try:
    import mido
    from mido import open_input, open_output
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    logging.warning("mido library not available - MIDI routing will be disabled")


class MIDIConnection:
    """Represents a single MIDI input->output connection with filters"""

    def __init__(self, input_name: str, output_name: str):
        self.input_name = input_name
        self.output_name = output_name
        self.input_port = None
        self.output_port = None

        # Filter settings
        self.filter_enabled = False
        self.allowed_message_types: Set[str] = set()

        # Channel filter
        self.channel_filter_enabled = False
        self.allowed_channels: Set[int] = set()  # 1-16

        # Channel remap
        self.remap_enabled = False
        self.remap_channel = 1  # 1-16

    def should_filter(self, msg) -> bool:
        """Check if message should be filtered out"""
        # Type filter
        if self.filter_enabled and self.allowed_message_types:
            msg_type = self._get_message_type(msg)
            if msg_type not in self.allowed_message_types:
                return True

        # Channel filter
        if self.channel_filter_enabled and self.allowed_channels:
            if hasattr(msg, 'channel'):
                # mido uses 0-15, we use 1-16
                if (msg.channel + 1) not in self.allowed_channels:
                    return True

        return False

    def _get_message_type(self, msg) -> str:
        """Get simplified message type string"""
        msg_type = msg.type

        # Group similar types
        if msg_type in ['note_on', 'note_off']:
            return 'note'
        elif msg_type == 'control_change':
            return 'cc'
        elif msg_type == 'program_change':
            return 'program'
        elif msg_type == 'pitchwheel':
            return 'pitch'
        elif msg_type in ['polytouch', 'aftertouch']:
            return 'aftertouch'
        elif msg_type == 'sysex':
            return 'sysex'
        elif msg_type == 'clock':
            return 'clock'
        elif msg_type == 'start':
            return 'start'
        elif msg_type == 'continue':
            return 'continue'
        elif msg_type == 'stop':
            return 'stop'
        elif msg_type == 'active_sensing':
            return 'activesense'
        elif msg_type == 'reset':
            return 'reset'
        elif msg_type == 'quarter_frame':
            return 'mtc'
        elif msg_type == 'songpos':
            return 'songpos'
        elif msg_type == 'song_select':
            return 'songsel'
        elif msg_type == 'tune_request':
            return 'tunereq'

        return msg_type

    def process_message(self, msg):
        """Process and potentially modify a message"""
        # Apply channel remapping if enabled
        if self.remap_enabled and hasattr(msg, 'channel'):
            msg = msg.copy(channel=self.remap_channel - 1)  # mido uses 0-15

        return msg


class ConnectionWidget(QWidget):
    """Widget displaying a single MIDI connection with controls"""

    def __init__(self, connection: MIDIConnection, on_remove, on_update, parent=None):
        super().__init__(parent)
        self.connection = connection
        self.on_remove_callback = on_remove
        self.on_update_callback = on_update

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        # Header with connection info and buttons
        header = QHBoxLayout()

        conn_label = QLabel(f"{self.connection.input_name} → {self.connection.output_name}")
        conn_label.setStyleSheet("font-weight: 500; color: #2d3748;")
        header.addWidget(conn_label)

        header.addStretch()

        advanced_btn = QPushButton("Advanced")
        advanced_btn.setCheckable(True)
        advanced_btn.clicked.connect(self.toggle_advanced)
        header.addWidget(advanced_btn)

        remove_btn = QPushButton("Disconnect")
        remove_btn.clicked.connect(lambda: self.on_remove_callback(self.connection))
        header.addWidget(remove_btn)

        layout.addLayout(header)

        # Advanced settings (hidden by default)
        self.advanced_widget = QWidget()
        advanced_layout = QVBoxLayout()
        self.advanced_widget.setLayout(advanced_layout)
        self.advanced_widget.hide()

        # Message type filter
        filter_group = QGroupBox("Message Type Filter")
        filter_layout = QVBoxLayout()

        self.filter_enabled_cb = QCheckBox("Enable message type filtering")
        self.filter_enabled_cb.setChecked(self.connection.filter_enabled)
        self.filter_enabled_cb.stateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_enabled_cb)

        # Message type buttons
        msg_types_layout = QGridLayout()
        self.msg_type_buttons = {}
        msg_types = [
            ('note', 'Note'), ('cc', 'CC'), ('program', 'Program'),
            ('pitch', 'Pitch'), ('aftertouch', 'Aftertouch'), ('sysex', 'SysEx'),
            ('clock', 'Clock'), ('start', 'Start'), ('continue', 'Continue'),
            ('stop', 'Stop'), ('activesense', 'Active Sense'), ('reset', 'Reset'),
            ('mtc', 'MTC'), ('songpos', 'Song Pos'), ('songsel', 'Song Sel'),
            ('tunereq', 'Tune Req')
        ]

        for idx, (key, label) in enumerate(msg_types):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(key in self.connection.allowed_message_types)
            btn.clicked.connect(lambda checked, k=key: self.toggle_message_type(k, checked))
            self.msg_type_buttons[key] = btn
            msg_types_layout.addWidget(btn, idx // 4, idx % 4)

        filter_layout.addLayout(msg_types_layout)
        filter_group.setLayout(filter_layout)
        advanced_layout.addWidget(filter_group)

        # Channel filter
        channel_filter_group = QGroupBox("Channel Filter")
        channel_filter_layout = QVBoxLayout()

        self.channel_filter_enabled_cb = QCheckBox("Enable channel filtering")
        self.channel_filter_enabled_cb.setChecked(self.connection.channel_filter_enabled)
        self.channel_filter_enabled_cb.stateChanged.connect(self.on_channel_filter_changed)
        channel_filter_layout.addWidget(self.channel_filter_enabled_cb)

        # Channel buttons (1-16)
        channels_layout = QGridLayout()
        self.channel_buttons = {}
        for i in range(16):
            channel = i + 1
            btn = QPushButton(str(channel))
            btn.setCheckable(True)
            btn.setChecked(channel in self.connection.allowed_channels)
            btn.clicked.connect(lambda checked, ch=channel: self.toggle_channel(ch, checked))
            self.channel_buttons[channel] = btn
            channels_layout.addWidget(btn, i // 8, i % 8)

        channel_filter_layout.addLayout(channels_layout)
        channel_filter_group.setLayout(channel_filter_layout)
        advanced_layout.addWidget(channel_filter_group)

        # Channel remap
        remap_group = QGroupBox("Channel Remap")
        remap_layout = QVBoxLayout()

        self.remap_enabled_cb = QCheckBox("Enable channel remapping")
        self.remap_enabled_cb.setChecked(self.connection.remap_enabled)
        self.remap_enabled_cb.stateChanged.connect(self.on_remap_changed)
        remap_layout.addWidget(self.remap_enabled_cb)

        remap_channel_layout = QHBoxLayout()
        remap_channel_layout.addWidget(QLabel("Remap to channel:"))

        self.remap_combo = QComboBox()
        for i in range(16):
            self.remap_combo.addItem(str(i + 1))
        self.remap_combo.setCurrentIndex(self.connection.remap_channel - 1)
        self.remap_combo.currentIndexChanged.connect(self.on_remap_channel_changed)
        remap_channel_layout.addWidget(self.remap_combo)
        remap_channel_layout.addStretch()

        remap_layout.addLayout(remap_channel_layout)
        remap_group.setLayout(remap_layout)
        advanced_layout.addWidget(remap_group)

        layout.addWidget(self.advanced_widget)

        # Styling
        self.setStyleSheet("""
            ConnectionWidget {
                background: #ebf8ff;
                border: 1px solid #4299e1;
                border-radius: 6px;
            }
            QGroupBox {
                font-weight: 500;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
            QPushButton {
                padding: 6px 12px;
            }
            QPushButton:checkable:checked {
                background-color: #4299e1;
                color: white;
            }
        """)

        self.setLayout(layout)

    def toggle_advanced(self):
        self.advanced_widget.setVisible(not self.advanced_widget.isVisible())

    def on_filter_changed(self):
        self.connection.filter_enabled = self.filter_enabled_cb.isChecked()
        self.on_update_callback()

    def toggle_message_type(self, msg_type: str, checked: bool):
        if checked:
            self.connection.allowed_message_types.add(msg_type)
        else:
            self.connection.allowed_message_types.discard(msg_type)
        self.on_update_callback()

    def on_channel_filter_changed(self):
        self.connection.channel_filter_enabled = self.channel_filter_enabled_cb.isChecked()
        self.on_update_callback()

    def toggle_channel(self, channel: int, checked: bool):
        if checked:
            self.connection.allowed_channels.add(channel)
        else:
            self.connection.allowed_channels.discard(channel)
        self.on_update_callback()

    def on_remap_changed(self):
        self.connection.remap_enabled = self.remap_enabled_cb.isChecked()
        self.on_update_callback()

    def on_remap_channel_changed(self, index: int):
        self.connection.remap_channel = index + 1
        self.on_update_callback()


class MIDIPatchbay(BasicEditor):
    """MIDI Patchbay tab - route MIDI inputs to outputs with filtering"""

    def __init__(self):
        super().__init__()

        self.connections: List[MIDIConnection] = []
        self.connection_widgets: List[ConnectionWidget] = []
        self.midi_available = MIDI_AVAILABLE

        # Timer for processing MIDI messages
        self.midi_timer = QTimer()
        self.midi_timer.timeout.connect(self.process_midi)

        self.setup_ui()

        if self.midi_available:
            self.refresh_ports()
            # Start MIDI processing
            self.midi_timer.start(10)  # Process every 10ms

    def setup_ui(self):
        self.addStretch()

        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        main_widget.setMinimumWidth(900)
        main_widget.setMaximumWidth(1200)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.addWidget(main_widget)
        self.setAlignment(main_widget, QtCore.Qt.AlignHCenter)

        # Title
        title = QLabel("MIDI Patchbay")
        title.setStyleSheet("font-size: 24px; font-weight: 300; color: #1a202c; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        if not self.midi_available:
            error_label = QLabel("⚠️ MIDI library not available. Please install: pip install mido python-rtmidi")
            error_label.setStyleSheet("color: #c53030; background: #fed7d7; padding: 16px; border-radius: 8px;")
            error_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(error_label)
            self.addStretch()
            return

        # Add connection section
        add_group = QGroupBox("Add New Connection")
        add_group.setStyleSheet("font-size: 14px; font-weight: 500;")
        add_layout = QGridLayout()
        add_group.setLayout(add_layout)
        main_layout.addWidget(add_group)

        add_layout.addWidget(QLabel("MIDI Input:"), 0, 0)
        self.input_combo = ArrowComboBox()
        self.input_combo.setMinimumWidth(250)
        add_layout.addWidget(self.input_combo, 0, 1)

        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 20px; color: #4299e1; font-weight: 500;")
        add_layout.addWidget(arrow_label, 0, 2, Qt.AlignCenter)

        add_layout.addWidget(QLabel("MIDI Output:"), 0, 3)
        self.output_combo = ArrowComboBox()
        self.output_combo.setMinimumWidth(250)
        add_layout.addWidget(self.output_combo, 0, 4)

        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.add_connection)
        connect_btn.setStyleSheet("padding: 8px 20px;")
        add_layout.addWidget(connect_btn, 0, 5)

        refresh_btn = QPushButton("Refresh Ports")
        refresh_btn.clicked.connect(self.refresh_ports)
        add_layout.addWidget(refresh_btn, 0, 6)

        # Active connections section
        connections_label = QLabel("Active Connections")
        connections_label.setStyleSheet("font-size: 16px; font-weight: 500; color: #2d3748; margin-top: 20px; border-bottom: 2px solid #4299e1; padding-bottom: 8px;")
        main_layout.addWidget(connections_label)

        # Scroll area for connections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(300)
        scroll.setStyleSheet("border: none;")

        self.connections_container = QWidget()
        self.connections_layout = QVBoxLayout()
        self.connections_layout.setSpacing(10)
        self.connections_container.setLayout(self.connections_layout)
        scroll.setWidget(self.connections_container)

        main_layout.addWidget(scroll)

        # Status info
        self.status_label = QLabel("No active connections")
        self.status_label.setStyleSheet("color: #718096; padding: 10px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.addStretch()

    def refresh_ports(self):
        """Refresh available MIDI input and output ports"""
        if not self.midi_available:
            return

        # Save current selections
        current_input = self.input_combo.currentText()
        current_output = self.output_combo.currentText()

        # Clear and repopulate
        self.input_combo.clear()
        self.output_combo.clear()

        try:
            input_names = mido.get_input_names()
            output_names = mido.get_output_names()

            for name in input_names:
                self.input_combo.addItem(name)

            for name in output_names:
                self.output_combo.addItem(name)

            # Restore selections if still available
            input_idx = self.input_combo.findText(current_input)
            if input_idx >= 0:
                self.input_combo.setCurrentIndex(input_idx)

            output_idx = self.output_combo.findText(current_output)
            if output_idx >= 0:
                self.output_combo.setCurrentIndex(output_idx)

            logging.info(f"MIDI ports refreshed: {len(input_names)} inputs, {len(output_names)} outputs")

        except Exception as e:
            logging.error(f"Error refreshing MIDI ports: {e}")
            QMessageBox.warning(self.connections_container, "MIDI Error",
                              f"Failed to refresh MIDI ports: {str(e)}")

    def add_connection(self):
        """Add a new MIDI routing connection"""
        if not self.midi_available:
            return

        input_name = self.input_combo.currentText()
        output_name = self.output_combo.currentText()

        if not input_name or not output_name:
            QMessageBox.warning(self.connections_container, "Invalid Selection",
                              "Please select both an input and output port")
            return

        # Check for duplicate
        for conn in self.connections:
            if conn.input_name == input_name and conn.output_name == output_name:
                QMessageBox.warning(self.connections_container, "Duplicate Connection",
                                  "This connection already exists")
                return

        try:
            # Create connection
            connection = MIDIConnection(input_name, output_name)

            # Open ports
            connection.input_port = mido.open_input(input_name)
            connection.output_port = mido.open_output(output_name)

            self.connections.append(connection)

            # Create widget
            widget = ConnectionWidget(connection, self.remove_connection, self.update_connections)
            self.connection_widgets.append(widget)
            self.connections_layout.addWidget(widget)

            self.update_status()
            logging.info(f"Added MIDI connection: {input_name} → {output_name}")

        except Exception as e:
            logging.error(f"Error adding connection: {e}")
            QMessageBox.critical(self.connections_container, "Connection Error",
                               f"Failed to create connection: {str(e)}")

    def remove_connection(self, connection: MIDIConnection):
        """Remove a MIDI connection"""
        try:
            # Close ports
            if connection.input_port:
                connection.input_port.close()
            if connection.output_port:
                connection.output_port.close()

            # Find and remove widget
            for i, conn in enumerate(self.connections):
                if conn == connection:
                    widget = self.connection_widgets[i]
                    self.connections_layout.removeWidget(widget)
                    widget.deleteLater()

                    del self.connections[i]
                    del self.connection_widgets[i]
                    break

            self.update_status()
            logging.info(f"Removed MIDI connection: {connection.input_name} → {connection.output_name}")

        except Exception as e:
            logging.error(f"Error removing connection: {e}")

    def update_connections(self):
        """Called when connection settings are updated"""
        # Nothing special needed, filters are applied in real-time
        pass

    def update_status(self):
        """Update status label"""
        count = len(self.connections)
        if count == 0:
            self.status_label.setText("No active connections")
        elif count == 1:
            self.status_label.setText("1 active connection")
        else:
            self.status_label.setText(f"{count} active connections")

    def process_midi(self):
        """Process MIDI messages from all connections"""
        if not self.midi_available:
            return

        for connection in self.connections:
            if not connection.input_port or not connection.output_port:
                continue

            try:
                # Process all pending messages (non-blocking)
                for msg in connection.input_port.iter_pending():
                    # Check filters
                    if connection.should_filter(msg):
                        continue

                    # Process (remap if needed)
                    processed_msg = connection.process_message(msg)

                    # Send to output
                    connection.output_port.send(processed_msg)

            except Exception as e:
                logging.error(f"Error processing MIDI: {e}")

    def valid(self):
        """This tab is always valid (doesn't require a connected keyboard)"""
        return True

    def rebuild(self, device):
        """Called when device changes - not needed for this tab"""
        super().rebuild(device)

    def activate(self):
        """Called when tab becomes active"""
        if self.midi_available and not self.midi_timer.isActive():
            self.midi_timer.start(10)
            self.refresh_ports()

    def deactivate(self):
        """Called when tab becomes inactive"""
        # Keep connections running even when tab is not active
        pass

    def cleanup(self):
        """Clean up MIDI connections when closing"""
        for connection in self.connections:
            try:
                if connection.input_port:
                    connection.input_port.close()
                if connection.output_port:
                    connection.output_port.close()
            except:
                pass

        self.connections.clear()
        self.midi_timer.stop()
