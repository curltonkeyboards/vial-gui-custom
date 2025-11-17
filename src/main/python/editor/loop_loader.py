# SPDX-License-Identifier: GPL-2.0-or-later
"""
LoopLoader - Save and Load loops to/from keyboard via SysEx
Allows backup and transfer of loop data between devices
"""

import logging
import time
from datetime import datetime
from typing import Optional, List
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QGroupBox, QGridLayout, QProgressBar, QFileDialog,
                              QSizePolicy, QMessageBox, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore

from editor.basic_editor import BasicEditor
from util import tr

try:
    import mido
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    logging.warning("mido library not available - Loop transfer will be disabled")


# SysEx Protocol Constants (matching the Tauri app)
SYSEX_MANUFACTURER_ID = 0x7D
SYSEX_DEVICE_ID = 0x4D
SYSEX_SUB_ID = 0x00

SYSEX_CMD_SAVE_START = 0x01
SYSEX_CMD_SAVE_CHUNK = 0x02
SYSEX_CMD_SAVE_END = 0x03
SYSEX_CMD_LOAD_START = 0x04
SYSEX_CMD_LOAD_CHUNK = 0x05
SYSEX_CMD_LOAD_END = 0x06
SYSEX_CMD_REQUEST_SAVE = 0x10

SYSEX_CHUNK_SIZE = 448


class LoopTransferState:
    """Tracks the state of an ongoing loop transfer"""

    def __init__(self):
        self.active = False
        self.is_loading = False
        self.loop_num = 0
        self.expected_chunks = 0
        self.received_chunks = 0
        self.total_size = 0
        self.received_data = bytearray()
        self.file_name = ""


class LoopFile:
    """Represents a loop file"""

    def __init__(self, name: str, data: bytes, date: datetime):
        self.name = name
        self.data = data
        self.date = date
        self.size = len(data)


class LoopLoader(BasicEditor):
    """Loop Loader tab - save and load loops via SysEx"""

    def __init__(self):
        super().__init__()

        self.midi_available = MIDI_AVAILABLE
        self.midiswitch_output = None
        self.midiswitch_input = None
        self.transfer_state = LoopTransferState()
        self.loaded_files: List[LoopFile] = []
        self.selected_file_idx: Optional[int] = None

        # Timer for checking MIDI messages
        self.midi_timer = QTimer()
        self.midi_timer.timeout.connect(self.process_sysex)

        self.setup_ui()

        if self.midi_available:
            self.find_midiswitch()
            self.midi_timer.start(50)  # Check every 50ms

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
        title = QLabel("Loop Manager")
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

        # Connection status
        self.connection_status = QLabel("MIDIswitch: Not Connected")
        self.connection_status.setStyleSheet("background: #fffaf0; border: 1px solid #ed8936; border-radius: 6px; padding: 12px; font-weight: 500; color: #744210;")
        self.connection_status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.connection_status)

        # Reconnect button
        reconnect_btn = QPushButton("Reconnect to MIDIswitch")
        reconnect_btn.clicked.connect(self.find_midiswitch)
        main_layout.addWidget(reconnect_btn)

        # Two column layout for save/load
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        main_layout.addLayout(columns_layout)

        # Save Section (left)
        save_group = QGroupBox("Save Loops from Keyboard")
        save_group.setStyleSheet("font-size: 14px; font-weight: 500;")
        save_layout = QVBoxLayout()
        save_group.setLayout(save_layout)
        columns_layout.addWidget(save_group, 1)

        save_label = QLabel("Click a loop number to save from keyboard to file:")
        save_layout.addWidget(save_label)

        # Loop buttons for saving
        save_buttons_layout = QGridLayout()
        self.save_buttons = []
        for i in range(4):
            loop_num = i + 1
            btn = QPushButton(f"Loop {loop_num}")
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, n=loop_num: self.request_save_loop(n))
            save_buttons_layout.addWidget(btn, i // 2, i % 2)
            self.save_buttons.append(btn)

        save_layout.addLayout(save_buttons_layout)

        # Save progress
        self.save_progress_widget = QWidget()
        save_progress_layout = QVBoxLayout()
        self.save_progress_widget.setLayout(save_progress_layout)
        self.save_progress_widget.hide()

        save_progress_label = QLabel("Receiving loop data...")
        save_progress_label.setStyleSheet("font-weight: 500; color: #2c5aa0;")
        save_progress_layout.addWidget(save_progress_label)

        self.save_progress_bar = QProgressBar()
        self.save_progress_bar.setTextVisible(True)
        save_progress_layout.addWidget(self.save_progress_bar)

        save_layout.addWidget(self.save_progress_widget)

        # Load Section (right)
        load_group = QGroupBox("Load Loops to Keyboard")
        load_group.setStyleSheet("font-size: 14px; font-weight: 500;")
        load_layout = QVBoxLayout()
        load_group.setLayout(load_layout)
        columns_layout.addWidget(load_group, 1)

        browse_btn = QPushButton("Browse for Loop Files...")
        browse_btn.clicked.connect(self.browse_loop_files)
        load_layout.addWidget(browse_btn)

        # File list
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(200)
        self.file_list.itemClicked.connect(self.on_file_selected)
        load_layout.addWidget(self.file_list)

        load_label = QLabel("Select a loop slot to load the selected file:")
        load_layout.addWidget(load_label)

        # Loop buttons for loading
        load_buttons_layout = QGridLayout()
        self.load_buttons = []
        for i in range(4):
            loop_num = i + 1
            btn = QPushButton(f"Loop {loop_num}")
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, n=loop_num: self.load_to_loop(n))
            load_buttons_layout.addWidget(btn, i // 2, i % 2)
            self.load_buttons.append(btn)

        load_layout.addLayout(load_buttons_layout)

        # Load progress
        self.load_progress_widget = QWidget()
        load_progress_layout = QVBoxLayout()
        self.load_progress_widget.setLayout(load_progress_layout)
        self.load_progress_widget.hide()

        load_progress_label = QLabel("Sending loop data...")
        load_progress_label.setStyleSheet("font-weight: 500; color: #2c5aa0;")
        load_progress_layout.addWidget(load_progress_label)

        self.load_progress_bar = QProgressBar()
        self.load_progress_bar.setTextVisible(True)
        load_progress_layout.addWidget(self.load_progress_bar)

        load_layout.addWidget(self.load_progress_widget)

        self.addStretch()

        self.update_file_list()

    def find_midiswitch(self):
        """Find and connect to MIDIswitch input/output"""
        if not self.midi_available:
            return

        try:
            # Close existing connections
            if self.midiswitch_input:
                self.midiswitch_input.close()
                self.midiswitch_input = None
            if self.midiswitch_output:
                self.midiswitch_output.close()
                self.midiswitch_output = None

            # Find MIDIswitch
            input_names = mido.get_input_names()
            output_names = mido.get_output_names()

            midiswitch_input_name = None
            midiswitch_output_name = None

            for name in input_names:
                if 'midiswitch' in name.lower():
                    midiswitch_input_name = name
                    break

            for name in output_names:
                if 'midiswitch' in name.lower():
                    midiswitch_output_name = name
                    break

            if midiswitch_input_name and midiswitch_output_name:
                self.midiswitch_input = mido.open_input(midiswitch_input_name)
                self.midiswitch_output = mido.open_output(midiswitch_output_name)

                self.connection_status.setText(f"MIDIswitch: Connected ({midiswitch_output_name})")
                self.connection_status.setStyleSheet("background: #f0fff4; border: 1px solid #48bb78; border-radius: 6px; padding: 12px; font-weight: 500; color: #22543d;")
                logging.info(f"Connected to MIDIswitch: {midiswitch_output_name}")
            else:
                self.connection_status.setText("MIDIswitch: Not Found")
                self.connection_status.setStyleSheet("background: #fffaf0; border: 1px solid #ed8936; border-radius: 6px; padding: 12px; font-weight: 500; color: #744210;")
                logging.warning("MIDIswitch not found in available MIDI ports")

        except Exception as e:
            logging.error(f"Error connecting to MIDIswitch: {e}")
            self.connection_status.setText(f"MIDIswitch: Error - {str(e)}")

    def request_save_loop(self, loop_num: int):
        """Request the keyboard to send loop data via SysEx"""
        if not self.midiswitch_output:
            QMessageBox.warning(None, "Not Connected", "MIDIswitch is not connected")
            return

        logging.info(f"Requesting save of loop {loop_num}")

        # Set up transfer state
        self.transfer_state = LoopTransferState()
        self.transfer_state.active = True
        self.transfer_state.is_loading = False
        self.transfer_state.loop_num = loop_num
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.transfer_state.file_name = f"loop{loop_num}_{timestamp}.loop"

        # Send SysEx save request
        save_request_msg = [
            0xF0,                    # SysEx start
            SYSEX_MANUFACTURER_ID,   # Manufacturer ID
            SYSEX_SUB_ID,           # Sub ID
            SYSEX_DEVICE_ID,        # Device ID
            SYSEX_CMD_REQUEST_SAVE, # Command
            loop_num,               # Loop number
            0xF7                    # SysEx end
        ]

        try:
            self.midiswitch_output.send(mido.Message('sysex', data=save_request_msg[1:-1]))
            self.save_progress_widget.show()
            self.save_progress_bar.setValue(0)
            logging.info(f"Sent save request for loop {loop_num}")
        except Exception as e:
            logging.error(f"Error sending save request: {e}")
            QMessageBox.critical(None, "SysEx Error", f"Failed to send save request: {str(e)}")
            self.transfer_state.active = False

    def browse_loop_files(self):
        """Browse and load loop files from disk"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            None,
            "Select Loop Files",
            "",
            "Loop Files (*.loop);;All Files (*)"
        )

        if not file_paths:
            return

        for file_path in file_paths:
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()

                import os
                file_name = os.path.basename(file_path)
                file_date = datetime.fromtimestamp(os.path.getmtime(file_path))

                loop_file = LoopFile(file_name, data, file_date)
                self.loaded_files.append(loop_file)

                logging.info(f"Loaded loop file: {file_name} ({len(data)} bytes)")

            except Exception as e:
                logging.error(f"Error loading file {file_path}: {e}")
                QMessageBox.warning(None, "Load Error", f"Failed to load {file_path}: {str(e)}")

        self.update_file_list()

    def update_file_list(self):
        """Update the file list widget"""
        self.file_list.clear()

        if not self.loaded_files:
            item = QListWidgetItem("No loop files loaded")
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(Qt.gray)
            self.file_list.addItem(item)
            return

        for idx, loop_file in enumerate(self.loaded_files):
            item_text = f"{loop_file.name}\n{loop_file.date.strftime('%Y-%m-%d %H:%M:%S')} • {loop_file.size / 1024:.1f} KB"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, idx)
            self.file_list.addItem(item)

    def on_file_selected(self, item: QListWidgetItem):
        """Handle file selection"""
        idx = item.data(Qt.UserRole)
        if idx is not None:
            self.selected_file_idx = idx

    def load_to_loop(self, loop_num: int):
        """Load selected file to keyboard loop"""
        if self.selected_file_idx is None or self.selected_file_idx >= len(self.loaded_files):
            QMessageBox.warning(None, "No File Selected", "Please select a file to load first")
            return

        if not self.midiswitch_output:
            QMessageBox.warning(None, "Not Connected", "MIDIswitch is not connected")
            return

        loop_file = self.loaded_files[self.selected_file_idx]
        logging.info(f"Loading {loop_file.name} to loop {loop_num}")

        # Encode to 7-bit
        encoded_data = self.encode_8to7(loop_file.data)

        # Calculate chunks
        num_chunks = (len(encoded_data) + SYSEX_CHUNK_SIZE - 1) // SYSEX_CHUNK_SIZE

        # Set up transfer state
        self.transfer_state = LoopTransferState()
        self.transfer_state.active = True
        self.transfer_state.is_loading = True
        self.transfer_state.loop_num = loop_num
        self.transfer_state.expected_chunks = num_chunks
        self.transfer_state.file_name = loop_file.name

        # Show progress
        self.load_progress_widget.show()
        self.load_progress_bar.setValue(0)

        try:
            # Send start message
            start_msg = [
                SYSEX_MANUFACTURER_ID, SYSEX_SUB_ID, SYSEX_DEVICE_ID,
                SYSEX_CMD_LOAD_START, loop_num, num_chunks,
                (len(encoded_data) >> 8) & 0x7F, len(encoded_data) & 0x7F
            ]
            self.midiswitch_output.send(mido.Message('sysex', data=start_msg))

            # Send chunks
            for chunk_idx in range(num_chunks):
                chunk_start = chunk_idx * SYSEX_CHUNK_SIZE
                chunk_end = min(chunk_start + SYSEX_CHUNK_SIZE, len(encoded_data))
                chunk_size = chunk_end - chunk_start
                chunk_data = encoded_data[chunk_start:chunk_end]

                chunk_msg = [
                    SYSEX_MANUFACTURER_ID, SYSEX_SUB_ID, SYSEX_DEVICE_ID,
                    SYSEX_CMD_LOAD_CHUNK, loop_num, chunk_idx,
                    (chunk_size >> 7) & 0x7F, chunk_size & 0x7F,
                ] + list(chunk_data)

                self.midiswitch_output.send(mido.Message('sysex', data=chunk_msg))

                # Update progress
                progress = int((chunk_idx + 1) / num_chunks * 100)
                self.load_progress_bar.setValue(progress)

                # Small delay to avoid overwhelming the device
                time.sleep(0.05)

            # Send end message
            end_msg = [
                SYSEX_MANUFACTURER_ID, SYSEX_SUB_ID, SYSEX_DEVICE_ID,
                SYSEX_CMD_LOAD_END, loop_num
            ]
            self.midiswitch_output.send(mido.Message('sysex', data=end_msg))

            self.load_progress_widget.hide()
            self.transfer_state.active = False

            QMessageBox.information(None, "Load Complete", f"Loaded {loop_file.name} to Loop {loop_num}")
            logging.info(f"Load complete: {loop_file.name} → Loop {loop_num}")

        except Exception as e:
            logging.error(f"Error loading to loop: {e}")
            QMessageBox.critical(None, "Load Error", f"Failed to load loop: {str(e)}")
            self.load_progress_widget.hide()
            self.transfer_state.active = False

    def process_sysex(self):
        """Process incoming SysEx messages"""
        if not self.midiswitch_input:
            return

        try:
            for msg in self.midiswitch_input.iter_pending():
                if msg.type == 'sysex':
                    self.handle_sysex_message(msg.data)
        except Exception as e:
            logging.error(f"Error processing SysEx: {e}")

    def handle_sysex_message(self, data: List[int]):
        """Handle a received SysEx message"""
        # Check if it's our message
        if len(data) < 4:
            return

        if data[0] != SYSEX_MANUFACTURER_ID or data[1] != SYSEX_SUB_ID or data[2] != SYSEX_DEVICE_ID:
            return

        command = data[3]
        loop_num = data[4] if len(data) > 4 else 0

        if command == SYSEX_CMD_SAVE_START:
            self.handle_save_start(data, loop_num)
        elif command == SYSEX_CMD_SAVE_CHUNK:
            self.handle_save_chunk(data, loop_num)
        elif command == SYSEX_CMD_SAVE_END:
            self.handle_save_end(data, loop_num)

    def handle_save_start(self, data: List[int], loop_num: int):
        """Handle SAVE_START command"""
        if len(data) < 7:
            return

        # Auto-setup if needed (device-initiated save)
        if not self.transfer_state.active or self.transfer_state.loop_num != loop_num:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.transfer_state = LoopTransferState()
            self.transfer_state.active = True
            self.transfer_state.is_loading = False
            self.transfer_state.loop_num = loop_num
            self.transfer_state.file_name = f"loop{loop_num}_{timestamp}.loop"
            self.save_progress_widget.show()

        self.transfer_state.expected_chunks = data[5]
        self.transfer_state.total_size = ((data[6] & 0x7F) << 8) | (data[7] & 0x7F)
        self.transfer_state.received_chunks = 0
        self.transfer_state.received_data = bytearray()

        self.save_progress_bar.setValue(0)
        logging.info(f"Receiving loop {loop_num}: {self.transfer_state.expected_chunks} chunks, {self.transfer_state.total_size} bytes")

    def handle_save_chunk(self, data: List[int], loop_num: int):
        """Handle SAVE_CHUNK command"""
        if not self.transfer_state.active or self.transfer_state.loop_num != loop_num:
            return

        if len(data) < 8:
            return

        chunk_num = data[5]
        chunk_size = ((data[6] & 0x7F) << 7) | (data[7] & 0x7F)

        if len(data) >= 8 + chunk_size:
            chunk_data = data[8:8 + chunk_size]
            self.transfer_state.received_data.extend(chunk_data)
            self.transfer_state.received_chunks += 1

            progress = int(self.transfer_state.received_chunks / self.transfer_state.expected_chunks * 100)
            self.save_progress_bar.setValue(progress)

            logging.debug(f"Received chunk {self.transfer_state.received_chunks}/{self.transfer_state.expected_chunks}")

    def handle_save_end(self, data: List[int], loop_num: int):
        """Handle SAVE_END command"""
        if not self.transfer_state.active or self.transfer_state.loop_num != loop_num:
            return

        if self.transfer_state.received_chunks != self.transfer_state.expected_chunks:
            logging.error(f"Save failed: received {self.transfer_state.received_chunks}/{self.transfer_state.expected_chunks} chunks")
            QMessageBox.critical(None, "Save Error", "Incomplete transfer - not all chunks received")
            self.save_progress_widget.hide()
            self.transfer_state.active = False
            return

        # Decode 7-bit to 8-bit
        decoded_data = self.decode_7to8(bytes(self.transfer_state.received_data))

        # Save to file
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Save Loop File",
                self.transfer_state.file_name,
                "Loop Files (*.loop);;All Files (*)"
            )

            if file_path:
                with open(file_path, 'wb') as f:
                    f.write(decoded_data)

                import os
                file_name = os.path.basename(file_path)
                file_date = datetime.now()
                loop_file = LoopFile(file_name, decoded_data, file_date)
                self.loaded_files.append(loop_file)
                self.update_file_list()

                QMessageBox.information(None, "Save Complete", f"Saved {file_name} ({len(decoded_data)} bytes)")
                logging.info(f"Saved loop {loop_num} to {file_path}")

        except Exception as e:
            logging.error(f"Error saving file: {e}")
            QMessageBox.critical(None, "Save Error", f"Failed to save file: {str(e)}")

        self.save_progress_widget.hide()
        self.transfer_state.active = False

    @staticmethod
    def decode_7to8(data: bytes) -> bytes:
        """Decode 7-bit encoded data to 8-bit"""
        output = bytearray()
        bits_buffer = 0
        bits_count = 0

        for byte in data:
            bits_buffer |= ((byte & 0x7F) << bits_count)
            bits_count += 7

            while bits_count >= 8:
                output.append(bits_buffer & 0xFF)
                bits_buffer >>= 8
                bits_count -= 8

        return bytes(output)

    @staticmethod
    def encode_8to7(data: bytes) -> bytes:
        """Encode 8-bit data to 7-bit for SysEx transmission"""
        output = bytearray()
        bits_buffer = 0
        bits_count = 0

        for byte in data:
            bits_buffer |= (byte << bits_count)
            bits_count += 8

            while bits_count >= 7:
                output.append(bits_buffer & 0x7F)
                bits_buffer >>= 7
                bits_count -= 7

        if bits_count > 0:
            output.append(bits_buffer & 0x7F)

        return bytes(output)

    def valid(self):
        """This tab is always valid (doesn't require a connected keyboard)"""
        return True

    def rebuild(self, device):
        """Called when device changes"""
        super().rebuild(device)

    def activate(self):
        """Called when tab becomes active"""
        if self.midi_available and not self.midi_timer.isActive():
            self.midi_timer.start(50)
            self.find_midiswitch()

    def deactivate(self):
        """Called when tab becomes inactive"""
        pass

    def cleanup(self):
        """Clean up MIDI connections"""
        if self.midiswitch_input:
            self.midiswitch_input.close()
        if self.midiswitch_output:
            self.midiswitch_output.close()

        self.midi_timer.stop()
