# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import os
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSizePolicy,
                             QLabel, QGroupBox, QFileDialog, QMessageBox, QProgressBar,
                             QListWidget, QListWidgetItem, QGridLayout)

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard


class LoopManager(BasicEditor):
    """Loop Manager tab for uploading/downloading loops to/from MIDIswitch"""

    # HID Command constants
    HID_CMD_SAVE_START = 0x01
    HID_CMD_SAVE_CHUNK = 0x02
    HID_CMD_SAVE_END = 0x03
    HID_CMD_LOAD_START = 0x04
    HID_CMD_LOAD_CHUNK = 0x05
    HID_CMD_LOAD_END = 0x06
    HID_CMD_LOAD_OVERDUB_START = 0x07
    HID_CMD_REQUEST_SAVE = 0x10
    HID_CMD_TRIGGER_SAVE_ALL = 0x30

    HID_PACKET_SIZE = 32
    HID_HEADER_SIZE = 6
    HID_DATA_SIZE = HID_PACKET_SIZE - HID_HEADER_SIZE

    MANUFACTURER_ID = 0x7D
    SUB_ID = 0x00
    DEVICE_ID = 0x4D

    def __init__(self):
        super().__init__()

        self.current_transfer = {
            'active': False,
            'is_loading': False,
            'loop_num': 0,
            'expected_packets': 0,
            'received_packets': 0,
            'total_size': 0,
            'received_data': bytearray(),
            'file_name': ''
        }

        self.loaded_files = []  # List of loaded .loop files
        self.loop_contents = {}  # Track what's in each loop (1-4)

        self.setup_ui()

    def setup_ui(self):
        self.addStretch()

        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.addWidget(main_widget)
        self.setAlignment(main_widget, QtCore.Qt.AlignHCenter)

        # Title
        title = QLabel(tr("LoopManager", "Loop Manager"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title)

        # Save Section
        save_group = QGroupBox(tr("LoopManager", "Save Loops from Device"))
        save_layout = QVBoxLayout()
        save_group.setLayout(save_layout)
        main_layout.addWidget(save_group)

        # Individual loop save buttons
        loop_buttons_layout = QGridLayout()
        self.save_loop_btns = []
        for i in range(4):
            btn = QPushButton(tr("LoopManager", f"Save Loop {i+1}"))
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked, loop=i+1: self.on_save_loop(loop))
            loop_buttons_layout.addWidget(btn, 0, i)
            self.save_loop_btns.append(btn)

        save_layout.addLayout(loop_buttons_layout)

        # Save all button
        save_all_btn = QPushButton(tr("LoopManager", "Save All Loops"))
        save_all_btn.setMinimumHeight(45)
        save_all_btn.setStyleSheet(
            "background: #1e3a8a; color: white; font-size: 14px; font-weight: bold;"
        )
        save_all_btn.clicked.connect(self.on_save_all_loops)
        save_layout.addWidget(save_all_btn)

        # Load Section
        load_group = QGroupBox(tr("LoopManager", "Load Loops to Device"))
        load_layout = QVBoxLayout()
        load_group.setLayout(load_layout)
        main_layout.addWidget(load_group)

        # File browser button
        browse_layout = QHBoxLayout()
        browse_btn = QPushButton(tr("LoopManager", "Browse for Loop Files"))
        browse_btn.setMinimumHeight(35)
        browse_btn.clicked.connect(self.on_browse_files)
        browse_layout.addWidget(browse_btn)

        clear_list_btn = QPushButton(tr("LoopManager", "Clear List"))
        clear_list_btn.setMinimumHeight(35)
        clear_list_btn.clicked.connect(self.on_clear_file_list)
        browse_layout.addWidget(clear_list_btn)
        load_layout.addLayout(browse_layout)

        # File list
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(120)
        load_layout.addWidget(self.file_list)

        # Loop assignment buttons
        assign_layout = QGridLayout()
        assign_layout.addWidget(QLabel(tr("LoopManager", "Load selected file to:")), 0, 0, 1, 4)

        self.load_loop_btns = []
        for i in range(4):
            btn = QPushButton(tr("LoopManager", f"Loop {i+1}"))
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked, loop=i+1: self.on_load_to_loop(loop))
            assign_layout.addWidget(btn, 1, i)
            self.load_loop_btns.append(btn)

        load_layout.addLayout(assign_layout)

        # Progress section
        progress_group = QGroupBox(tr("LoopManager", "Transfer Progress"))
        progress_layout = QVBoxLayout()
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        self.progress_label = QLabel(tr("LoopManager", "No transfer in progress"))
        self.progress_label.setAlignment(QtCore.Qt.AlignCenter)
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        # Current loop contents
        contents_group = QGroupBox(tr("LoopManager", "Current Loop Contents"))
        contents_layout = QGridLayout()
        contents_group.setLayout(contents_layout)
        main_layout.addWidget(contents_group)

        self.loop_content_labels = []
        for i in range(4):
            label = QLabel(f"Loop {i+1}:")
            contents_layout.addWidget(label, i // 2, (i % 2) * 2)

            content_label = QLabel(tr("LoopManager", "Empty"))
            content_label.setStyleSheet("color: gray; font-style: italic;")
            contents_layout.addWidget(content_label, i // 2, (i % 2) * 2 + 1)
            self.loop_content_labels.append(content_label)

        self.addStretch()

    def send_hid_packet(self, command, macro_num, status=0, data=None):
        """Send HID packet to device"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            raise Exception("Device not connected")

        packet = bytearray(self.HID_PACKET_SIZE)
        packet[0] = self.MANUFACTURER_ID
        packet[1] = self.SUB_ID
        packet[2] = self.DEVICE_ID
        packet[3] = command
        packet[4] = macro_num
        packet[5] = status

        if data:
            data_len = min(len(data), self.HID_DATA_SIZE)
            packet[6:6 + data_len] = data[:data_len]

        try:
            self.device.keyboard.via_command(packet)
        except Exception as e:
            raise Exception(f"Failed to send HID command: {str(e)}")

    def on_save_loop(self, loop_num):
        """Request to save a specific loop from device"""
        try:
            # Choose save location
            default_name = f"loop{loop_num}.loop"
            filename, _ = QFileDialog.getSaveFileName(
                None, f"Save Loop {loop_num}", default_name,
                "Loop Files (*.loop);;All Files (*)"
            )

            if not filename:
                return

            # Initialize transfer state
            self.current_transfer = {
                'active': True,
                'is_loading': False,
                'loop_num': loop_num,
                'expected_packets': 0,
                'received_packets': 0,
                'total_size': 0,
                'received_data': bytearray(),
                'file_name': filename
            }

            # Update UI
            self.progress_label.setText(f"Requesting Loop {loop_num} from device...")
            self.progress_bar.setValue(0)

            # Send request to device
            self.send_hid_packet(self.HID_CMD_REQUEST_SAVE, loop_num)

            # Start timeout timer (10 seconds)
            QTimer.singleShot(10000, self.on_transfer_timeout)

        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to request loop save: {str(e)}")
            self.reset_transfer_state()

    def on_save_all_loops(self):
        """Save all loops from device"""
        try:
            # Choose save directory
            directory = QFileDialog.getExistingDirectory(
                None, "Select Directory to Save All Loops"
            )

            if not directory:
                return

            # Send trigger to save all
            self.send_hid_packet(self.HID_CMD_TRIGGER_SAVE_ALL, 0)

            # Save each loop individually
            for loop_num in range(1, 5):
                filename = os.path.join(directory, f"loop{loop_num}.loop")

                self.current_transfer = {
                    'active': True,
                    'is_loading': False,
                    'loop_num': loop_num,
                    'expected_packets': 0,
                    'received_packets': 0,
                    'total_size': 0,
                    'received_data': bytearray(),
                    'file_name': filename
                }

                self.progress_label.setText(f"Saving Loop {loop_num} of 4...")
                self.progress_bar.setValue((loop_num - 1) * 25)

                # Send request
                self.send_hid_packet(self.HID_CMD_REQUEST_SAVE, loop_num)

                # Wait for transfer to complete (simplified - in real implementation
                # you'd use proper async/await or threading)
                QtCore.QCoreApplication.processEvents()

        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save all loops: {str(e)}")
            self.reset_transfer_state()

    def on_browse_files(self):
        """Browse for loop files to load"""
        filenames, _ = QFileDialog.getOpenFileNames(
            None, "Select Loop Files", "",
            "Loop Files (*.loop);;MIDI Files (*.mid *.midi);;All Files (*)"
        )

        for filename in filenames:
            # Check if already in list
            found = False
            for i in range(self.file_list.count()):
                if self.file_list.item(i).data(QtCore.Qt.UserRole) == filename:
                    found = True
                    break

            if not found:
                # Add to list
                file_info = os.path.basename(filename)
                file_size = os.path.getsize(filename)
                display_text = f"{file_info} ({file_size} bytes)"

                item = QListWidgetItem(display_text)
                item.setData(QtCore.Qt.UserRole, filename)
                self.file_list.addItem(item)

    def on_clear_file_list(self):
        """Clear the file list"""
        self.file_list.clear()

    def on_load_to_loop(self, loop_num):
        """Load selected file to specified loop"""
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(None, "Warning", "Please select a file to load")
            return

        filename = current_item.data(QtCore.Qt.UserRole)

        try:
            # Read loop file
            with open(filename, 'rb') as f:
                loop_data = f.read()

            # Validate file
            if len(loop_data) < 4:
                raise Exception("Invalid loop file: too short")

            # Check magic bytes
            if loop_data[0] != 0xAA or loop_data[1] != 0x55:
                raise Exception("Invalid loop file: bad magic bytes")

            # Update UI
            self.progress_label.setText(f"Loading to Loop {loop_num}...")
            self.progress_bar.setValue(0)

            # Send loop data
            self.send_loop_data(loop_data, loop_num)

            # Update loop contents
            self.loop_contents[loop_num] = os.path.basename(filename)
            self.update_loop_contents_display()

            QMessageBox.information(None, "Success",
                                  f"Successfully loaded {os.path.basename(filename)} to Loop {loop_num}")

        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to load loop: {str(e)}")
            self.reset_transfer_state()

    def send_loop_data(self, loop_data, loop_num):
        """Send loop data to device in chunks"""
        try:
            # Send LOAD_START
            self.send_hid_packet(self.HID_CMD_LOAD_START, loop_num)
            self.progress_bar.setValue(10)

            # Send data in chunks
            total_size = len(loop_data)
            chunk_size = self.HID_DATA_SIZE - 4  # Reserve 4 bytes for chunk info
            total_chunks = (total_size + chunk_size - 1) // chunk_size

            for chunk_idx in range(total_chunks):
                offset = chunk_idx * chunk_size
                chunk = loop_data[offset:offset + chunk_size]

                # Create chunk packet
                chunk_data = bytearray(4)
                struct.pack_into('<H', chunk_data, 0, chunk_idx)  # Chunk index
                struct.pack_into('<H', chunk_data, 2, len(chunk))  # Chunk size
                chunk_data.extend(chunk)

                self.send_hid_packet(self.HID_CMD_LOAD_CHUNK, loop_num, data=chunk_data)

                # Update progress
                progress = 10 + int((chunk_idx + 1) / total_chunks * 80)
                self.progress_bar.setValue(progress)

                # Process events to keep UI responsive
                QtCore.QCoreApplication.processEvents()

            # Send LOAD_END
            self.send_hid_packet(self.HID_CMD_LOAD_END, loop_num)
            self.progress_bar.setValue(100)

            self.progress_label.setText(f"Successfully loaded to Loop {loop_num}")

            # Reset after delay
            QTimer.singleShot(2000, self.reset_transfer_state)

        except Exception as e:
            raise Exception(f"Failed to send loop data: {str(e)}")

    def handle_device_response(self, data):
        """Handle incoming HID data from device
        This would be called by the device communication layer
        """
        if len(data) < self.HID_HEADER_SIZE:
            return

        # Validate header
        if (data[0] != self.MANUFACTURER_ID or
            data[1] != self.SUB_ID or
            data[2] != self.DEVICE_ID):
            return

        command = data[3]
        macro_num = data[4]
        status = data[5]
        payload = data[self.HID_HEADER_SIZE:]

        if command == self.HID_CMD_SAVE_START:
            self.handle_save_start(macro_num, status, payload)
        elif command == self.HID_CMD_SAVE_CHUNK:
            self.handle_save_chunk(macro_num, status, payload)
        elif command == self.HID_CMD_SAVE_END:
            self.handle_save_end(macro_num, status)

    def handle_save_start(self, macro_num, status, data):
        """Handle SAVE_START response from device"""
        if status != 0:
            QMessageBox.warning(None, "Warning", f"Loop {macro_num} is empty or error occurred")
            self.reset_transfer_state()
            return

        # Extract total size from payload
        if len(data) >= 4:
            self.current_transfer['total_size'] = struct.unpack('<I', data[:4])[0]
            chunk_size = self.HID_DATA_SIZE - 4
            self.current_transfer['expected_packets'] = \
                (self.current_transfer['total_size'] + chunk_size - 1) // chunk_size

        self.progress_label.setText(
            f"Receiving Loop {macro_num}: 0 / {self.current_transfer['total_size']} bytes"
        )

    def handle_save_chunk(self, macro_num, status, data):
        """Handle SAVE_CHUNK response from device"""
        if not self.current_transfer['active']:
            return

        # Extract chunk data (skip chunk info bytes)
        if len(data) > 4:
            chunk_data = data[4:]
            self.current_transfer['received_data'].extend(chunk_data)
            self.current_transfer['received_packets'] += 1

            # Update progress
            received = len(self.current_transfer['received_data'])
            total = self.current_transfer['total_size']

            if total > 0:
                progress = int((received / total) * 100)
                self.progress_bar.setValue(progress)
                self.progress_label.setText(
                    f"Receiving Loop {macro_num}: {received} / {total} bytes"
                )

    def handle_save_end(self, macro_num, status):
        """Handle SAVE_END response from device"""
        if not self.current_transfer['active']:
            return

        if status == 0:
            # Save to file
            try:
                with open(self.current_transfer['file_name'], 'wb') as f:
                    f.write(self.current_transfer['received_data'])

                QMessageBox.information(None, "Success",
                    f"Successfully saved Loop {macro_num} to {self.current_transfer['file_name']}")

            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to save file: {str(e)}")

        else:
            QMessageBox.critical(None, "Error", f"Failed to receive Loop {macro_num}")

        self.reset_transfer_state()

    def on_transfer_timeout(self):
        """Handle transfer timeout"""
        if self.current_transfer['active']:
            QMessageBox.critical(None, "Error", "Transfer timed out")
            self.reset_transfer_state()

    def reset_transfer_state(self):
        """Reset transfer state"""
        self.current_transfer = {
            'active': False,
            'is_loading': False,
            'loop_num': 0,
            'expected_packets': 0,
            'received_packets': 0,
            'total_size': 0,
            'received_data': bytearray(),
            'file_name': ''
        }

        self.progress_label.setText(tr("LoopManager", "No transfer in progress"))
        self.progress_bar.setValue(0)

    def update_loop_contents_display(self):
        """Update the loop contents display"""
        for i in range(4):
            loop_num = i + 1
            if loop_num in self.loop_contents:
                self.loop_content_labels[i].setText(self.loop_contents[loop_num])
                self.loop_content_labels[i].setStyleSheet("color: green; font-weight: bold;")
            else:
                self.loop_content_labels[i].setText(tr("LoopManager", "Empty"))
                self.loop_content_labels[i].setStyleSheet("color: gray; font-style: italic;")

    def valid(self):
        """This tab is valid for all VialKeyboard devices"""
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        # Reset state when device changes
        self.reset_transfer_state()
        self.loop_contents = {}
        self.update_loop_contents_display()
