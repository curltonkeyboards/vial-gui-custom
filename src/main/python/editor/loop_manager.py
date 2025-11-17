# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import os
import threading
import time
import logging
from datetime import datetime
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, pyqtSignal, QObject, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSizePolicy,
                             QLabel, QGroupBox, QFileDialog, QMessageBox, QProgressBar,
                             QListWidget, QListWidgetItem, QGridLayout, QCheckBox, QButtonGroup,
                             QRadioButton, QScrollArea, QFrame)

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard

# Setup logging to file for standalone builds
LOG_FILE = os.path.join(os.path.expanduser("~"), "vial-loop-manager.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),  # Overwrite each session
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)


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

    # Signals for thread-safe UI updates
    transfer_progress = pyqtSignal(int, str)  # progress, message
    transfer_complete = pyqtSignal(bool, str)  # success, message
    hid_data_received = pyqtSignal(bytes)  # raw HID data

    def __init__(self):
        super().__init__()

        # Log startup
        logger.info("="*60)
        logger.info("Loop Manager initialized")
        logger.info(f"Log file: {LOG_FILE}")
        logger.info("="*60)

        self.current_transfer = {
            'active': False,
            'is_loading': False,
            'loop_num': 0,
            'expected_packets': 0,
            'received_packets': 0,
            'total_size': 0,
            'received_data': bytearray(),
            'file_name': '',
            'save_format': 'loop',  # 'loop' or 'midi'
            'save_all_mode': False,
            'save_all_directory': '',
            'save_all_current': 0
        }

        self.loaded_files = {}  # Dict: filename -> {'tracks': [], 'bpm': 120}
        self.loop_contents = {}  # Track what's in each loop (1-4)
        self.overdub_contents = {}  # Track what's in each overdub (1-4)
        self.selected_track = None  # Currently selected track {file_idx, track_idx}
        self.pending_assignments = {}  # Track assignments pending load

        self.hid_listener_thread = None
        self.hid_listening = False

        # Connect signals
        self.transfer_progress.connect(self.on_transfer_progress)
        self.transfer_complete.connect(self.on_transfer_complete)
        self.hid_data_received.connect(self.handle_device_response)

        self.setup_ui()

    def setup_ui(self):
        # No stretch at top - goes directly to content

        # Create scrollable main widget
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 5, 10, 10)  # Reduce top margin
        main_widget.setLayout(main_layout)
        scroll.setWidget(main_widget)

        self.addWidget(scroll)

        # Title
        title = QLabel(tr("LoopManager", "Loop Manager"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title)

        # Main container with two columns
        columns_layout = QHBoxLayout()
        main_layout.addLayout(columns_layout)

        # === SAVE SECTION (Left Column) ===
        save_group = QGroupBox(tr("LoopManager", "Save from Device"))
        save_layout = QVBoxLayout()
        save_group.setLayout(save_layout)
        save_group.setMaximumWidth(500)
        columns_layout.addWidget(save_group)

        # Save All Loops button (use theme colors)
        save_all_btn = QPushButton(tr("LoopManager", "Save All Loops"))
        save_all_btn.setMinimumHeight(45)
        save_all_btn.clicked.connect(self.on_save_all_loops)
        save_layout.addWidget(save_all_btn)

        save_layout.addWidget(QLabel(tr("LoopManager", "Save individual loops:")))

        # Individual loop save buttons (4 in a row)
        loop_buttons_layout = QGridLayout()
        self.save_loop_btns = []
        for i in range(4):
            btn = QPushButton(tr("LoopManager", f"Loop {i+1}"))
            btn.setMinimumHeight(35)
            btn.clicked.connect(lambda checked, loop=i+1: self.on_save_loop(loop))
            loop_buttons_layout.addWidget(btn, 0, i)
            self.save_loop_btns.append(btn)

        save_layout.addLayout(loop_buttons_layout)

        # Save format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel(tr("LoopManager", "Save as:")))
        self.format_group = QButtonGroup(self)
        self.format_loop_radio = QRadioButton(tr("LoopManager", ".loop file"))
        self.format_midi_radio = QRadioButton(tr("LoopManager", "MIDI file"))
        self.format_loop_radio.setChecked(True)
        self.format_group.addButton(self.format_loop_radio)
        self.format_group.addButton(self.format_midi_radio)
        format_layout.addWidget(self.format_loop_radio)
        format_layout.addWidget(self.format_midi_radio)
        format_layout.addStretch()
        save_layout.addLayout(format_layout)

        # Save progress
        self.save_progress_label = QLabel("")
        save_layout.addWidget(self.save_progress_label)

        self.save_progress_bar = QProgressBar()
        self.save_progress_bar.setMinimum(0)
        self.save_progress_bar.setMaximum(100)
        self.save_progress_bar.setValue(0)
        self.save_progress_bar.setVisible(False)
        save_layout.addWidget(self.save_progress_bar)

        # Log file button
        log_button_layout = QHBoxLayout()
        self.view_log_btn = QPushButton(tr("LoopManager", "📋 View Debug Log"))
        self.view_log_btn.setMaximumWidth(200)
        self.view_log_btn.clicked.connect(self.on_view_log)
        log_button_layout.addWidget(self.view_log_btn)
        log_button_layout.addStretch()
        save_layout.addLayout(log_button_layout)

        save_layout.addStretch()

        # === LOAD SECTION (Right Column) ===
        load_group = QGroupBox(tr("LoopManager", "Load to Device"))
        load_layout = QVBoxLayout()
        load_group.setLayout(load_layout)
        load_group.setMaximumWidth(500)
        columns_layout.addWidget(load_group)

        # Browse button
        browse_btn = QPushButton(tr("LoopManager", "Browse for Loop/MIDI Files"))
        browse_btn.setMinimumHeight(45)
        browse_btn.clicked.connect(self.on_browse_files)
        load_layout.addWidget(browse_btn)

        # File list
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(100)
        self.file_list.setMaximumHeight(150)
        self.file_list.currentItemChanged.connect(self.on_file_selected)
        load_layout.addWidget(self.file_list)

        # Clear list button
        clear_btn = QPushButton(tr("LoopManager", "Clear File List"))
        clear_btn.clicked.connect(self.on_clear_file_list)
        load_layout.addWidget(clear_btn)

        # Load All button
        self.load_all_btn = QPushButton(tr("LoopManager", "Load All Tracks to Device"))
        self.load_all_btn.setMinimumHeight(35)
        self.load_all_btn.setEnabled(False)
        self.load_all_btn.clicked.connect(self.on_load_all_tracks)
        load_layout.addWidget(self.load_all_btn)

        # Advanced track assignment toggle
        self.advanced_toggle = QCheckBox(tr("LoopManager", "Show Advanced Track Assignment"))
        self.advanced_toggle.stateChanged.connect(self.on_toggle_advanced)
        load_layout.addWidget(self.advanced_toggle)

        # Load progress
        self.load_progress_label = QLabel("")
        load_layout.addWidget(self.load_progress_label)

        self.load_progress_bar = QProgressBar()
        self.load_progress_bar.setMinimum(0)
        self.load_progress_bar.setMaximum(100)
        self.load_progress_bar.setValue(0)
        self.load_progress_bar.setVisible(False)
        load_layout.addWidget(self.load_progress_bar)

        load_layout.addStretch()

        # === ADVANCED TRACK ASSIGNMENT SECTION ===
        self.advanced_section = QGroupBox(tr("LoopManager", "Advanced Track Assignment"))
        advanced_layout = QVBoxLayout()
        self.advanced_section.setLayout(advanced_layout)
        self.advanced_section.setVisible(False)
        main_layout.addWidget(self.advanced_section)

        # Track selection area
        track_select_label = QLabel(tr("LoopManager", "Select Track:"))
        track_select_label.setStyleSheet("font-weight: bold;")
        advanced_layout.addWidget(track_select_label)

        self.track_info_label = QLabel(tr("LoopManager", "Select a MIDI file to see tracks"))
        self.track_info_label.setStyleSheet("font-style: italic;")
        advanced_layout.addWidget(self.track_info_label)

        self.track_buttons_widget = QWidget()
        self.track_buttons_layout = QGridLayout()
        self.track_buttons_widget.setLayout(self.track_buttons_layout)
        advanced_layout.addWidget(self.track_buttons_widget)

        self.track_button_group = QButtonGroup(self)
        self.track_button_group.setExclusive(True)
        self.track_button_group.buttonClicked.connect(self.on_track_button_clicked)

        # Loop assignment area
        assign_label = QLabel(tr("LoopManager", "Assign Selected Track to Loop:"))
        assign_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        advanced_layout.addWidget(assign_label)

        # Main loop buttons
        main_label = QLabel(tr("LoopManager", "Main:"))
        advanced_layout.addWidget(main_label)

        main_buttons_layout = QGridLayout()
        self.main_assign_btns = []
        for i in range(4):
            btn = QPushButton(f"Loop {i+1}")
            btn.setMinimumHeight(35)
            btn.clicked.connect(lambda checked, loop=i+1: self.on_assign_main(loop))
            main_buttons_layout.addWidget(btn, 0, i)
            self.main_assign_btns.append(btn)
        advanced_layout.addLayout(main_buttons_layout)

        # Overdub loop buttons
        overdub_label = QLabel(tr("LoopManager", "Overdub:"))
        advanced_layout.addWidget(overdub_label)

        overdub_buttons_layout = QGridLayout()
        self.overdub_assign_btns = []
        for i in range(4):
            btn = QPushButton(f"Loop {i+1} Overdub")
            btn.setMinimumHeight(35)
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked, loop=i+1: self.on_assign_overdub(loop))
            overdub_buttons_layout.addWidget(btn, 0, i)
            self.overdub_assign_btns.append(btn)
        advanced_layout.addLayout(overdub_buttons_layout)

        # Info text
        info_label = QLabel(tr("LoopManager",
            "💡 Overdub tracks are only available for loops that already have main content. "
            "Select a track above, then click a loop button to assign."))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 11px; padding: 8px;")
        advanced_layout.addWidget(info_label)

        # Load assignments button
        self.load_assignments_btn = QPushButton(tr("LoopManager", "Load Assigned Tracks to Device"))
        self.load_assignments_btn.setMinimumHeight(40)
        self.load_assignments_btn.setEnabled(False)
        self.load_assignments_btn.clicked.connect(self.on_load_assignments)
        advanced_layout.addWidget(self.load_assignments_btn)

        # === CURRENT LOOP CONTENTS ===
        contents_group = QGroupBox(tr("LoopManager", "Current Loop Contents"))
        contents_layout = QGridLayout()
        contents_group.setLayout(contents_layout)
        main_layout.addWidget(contents_group)

        self.loop_content_labels = []
        for i in range(4):
            label = QLabel(f"Loop {i+1}:")
            label.setStyleSheet("font-weight: bold;")
            contents_layout.addWidget(label, i // 2, (i % 2) * 2)

            content_label = QLabel(tr("LoopManager", "Empty"))
            content_label.setStyleSheet("font-style: italic;")
            contents_layout.addWidget(content_label, i // 2, (i % 2) * 2 + 1)
            self.loop_content_labels.append(content_label)

    def send_hid_packet(self, command, macro_num, status=0, data=None):
        """Send raw HID packet to device"""
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
            # Send raw HID data (not VIA command)
            self.device.send(bytes(packet))
        except Exception as e:
            raise Exception(f"Failed to send HID packet: {str(e)}")

    def start_hid_listener(self):
        """Start background thread to listen for HID responses"""
        if self.hid_listening:
            return

        self.hid_listening = True
        self.hid_listener_thread = threading.Thread(target=self.hid_listener_loop, daemon=True)
        self.hid_listener_thread.start()

    def stop_hid_listener(self):
        """Stop the HID listener thread"""
        self.hid_listening = False
        if self.hid_listener_thread:
            self.hid_listener_thread.join(timeout=1.0)

    def hid_listener_loop(self):
        """Background thread loop to receive HID data"""
        logger.info("HID listener thread started")
        while self.hid_listening and self.device:
            try:
                # Read HID data with longer timeout
                data = self.device.recv(self.HID_PACKET_SIZE, timeout_ms=500)
                if data and len(data) > 0:
                    logger.info(f"HID received {len(data)} bytes: {data[:10].hex()}...")
                    if len(data) == self.HID_PACKET_SIZE:
                        # Emit signal for thread-safe UI update
                        self.hid_data_received.emit(bytes(data))
                    else:
                        logger.info(f"Warning: Received {len(data)} bytes, expected {self.HID_PACKET_SIZE}")
            except Exception as e:
                # Ignore timeout errors but log others
                error_msg = str(e).lower()
                if "timeout" not in error_msg and "timed out" not in error_msg:
                    logger.info(f"HID listener error: {e}")
        logger.info("HID listener thread stopped")

    def on_view_log(self):
        """Open the debug log file"""
        try:
            if os.path.exists(LOG_FILE):
                # Open log file in default text editor
                QDesktopServices.openUrl(QUrl.fromLocalFile(LOG_FILE))
                QMessageBox.information(None, "Debug Log",
                    f"Log file location:\n{LOG_FILE}\n\n"
                    "The log file contains detailed debug information about HID communication.")
            else:
                QMessageBox.warning(None, "Log Not Found",
                    f"Log file not found at:\n{LOG_FILE}\n\n"
                    "The log will be created when you perform save/load operations.")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to open log file: {str(e)}")

    def on_save_loop(self, loop_num):
        """Request to save a specific loop from device"""
        try:
            # Determine file extension based on format selection
            if self.format_midi_radio.isChecked():
                filter_str = "MIDI Files (*.mid);;All Files (*)"
                default_name = f"loop{loop_num}.mid"
            else:
                filter_str = "Loop Files (*.loop);;All Files (*)"
                default_name = f"loop{loop_num}.loop"

            filename, _ = QFileDialog.getSaveFileName(
                None, f"Save Loop {loop_num}", default_name, filter_str
            )

            if not filename:
                return

            logger.info(f"\n=== Saving Loop {loop_num} to {filename} ===")

            # Initialize transfer state
            self.current_transfer = {
                'active': True,
                'is_loading': False,
                'loop_num': loop_num,
                'expected_packets': 0,
                'received_packets': 0,
                'total_size': 0,
                'received_data': bytearray(),
                'file_name': filename,
                'save_format': 'midi' if self.format_midi_radio.isChecked() else 'loop',
                'save_all_mode': False,
                'save_all_directory': '',
                'save_all_current': 0
            }

            # Start HID listener if not already running
            self.start_hid_listener()

            # Wait a moment for listener to be ready
            time.sleep(0.1)

            # Update UI
            self.save_progress_label.setText(f"Requesting Loop {loop_num} from device...")
            self.save_progress_bar.setValue(0)
            self.save_progress_bar.setVisible(True)

            logger.info(f"Sending REQUEST_SAVE command for loop {loop_num}")
            # Send request to device
            self.send_hid_packet(self.HID_CMD_REQUEST_SAVE, loop_num)
            logger.info("REQUEST_SAVE sent, waiting for response...")

        except Exception as e:
            logger.info(f"Error in on_save_loop: {e}")
            QMessageBox.critical(None, "Error", f"Failed to request loop save: {str(e)}")
            self.reset_transfer_state()

    def on_save_all_loops(self):
        """Save all loops from device - prompts for each filename"""
        try:
            # Determine format
            save_format = 'midi' if self.format_midi_radio.isChecked() else 'loop'
            extension = '.mid' if save_format == 'midi' else '.loop'

            # Ask user if they want to choose directory or individual filenames
            reply = QMessageBox.question(None, "Save All Loops",
                "Choose how to save:\n\n"
                "Yes - Choose directory (files named loop1-4" + extension + ")\n"
                "No - Choose each filename individually",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

            if reply == QMessageBox.Cancel:
                return

            if reply == QMessageBox.Yes:
                # Directory mode
                directory = QFileDialog.getExistingDirectory(
                    None, "Select Directory to Save All Loops"
                )
                if not directory:
                    return

                # Initialize for save all in directory mode
                self.current_transfer['save_all_mode'] = True
                self.current_transfer['save_all_directory'] = directory
                self.current_transfer['save_format'] = save_format
                self.current_transfer['save_all_current'] = 1

            else:
                # Individual filename mode - will prompt for each
                self.current_transfer['save_all_mode'] = 'individual'
                self.current_transfer['save_format'] = save_format
                self.current_transfer['save_all_current'] = 1

            # Start HID listener
            self.start_hid_listener()

            # Send trigger to save all
            self.send_hid_packet(self.HID_CMD_TRIGGER_SAVE_ALL, 0)

            # Start saving first loop
            self.save_next_loop_in_sequence()

        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save all loops: {str(e)}")
            self.reset_transfer_state()

    def save_next_loop_in_sequence(self):
        """Continue save all sequence"""
        loop_num = self.current_transfer.get('save_all_current', 0)

        if loop_num > 4:
            # All done
            QMessageBox.information(None, "Success", "All loops saved successfully!")
            self.reset_transfer_state()
            return

        # Determine filename
        save_format = self.current_transfer['save_format']
        extension = '.mid' if save_format == 'midi' else '.loop'

        if self.current_transfer['save_all_mode'] == True:  # Directory mode
            directory = self.current_transfer['save_all_directory']
            filename = os.path.join(directory, f"loop{loop_num}{extension}")
        else:  # Individual mode
            if self.format_midi_radio.isChecked():
                filter_str = "MIDI Files (*.mid);;All Files (*)"
            else:
                filter_str = "Loop Files (*.loop);;All Files (*)"

            filename, _ = QFileDialog.getSaveFileName(
                None, f"Save Loop {loop_num}", f"loop{loop_num}{extension}", filter_str
            )

            if not filename:
                # User cancelled - stop sequence
                self.reset_transfer_state()
                return

        # Setup for this loop
        self.current_transfer['active'] = True
        self.current_transfer['loop_num'] = loop_num
        self.current_transfer['file_name'] = filename
        self.current_transfer['expected_packets'] = 0
        self.current_transfer['received_packets'] = 0
        self.current_transfer['total_size'] = 0
        self.current_transfer['received_data'] = bytearray()

        # Update UI
        self.save_progress_label.setText(f"Saving Loop {loop_num} of 4...")
        self.save_progress_bar.setValue((loop_num - 1) * 25)
        self.save_progress_bar.setVisible(True)

        # Send request
        self.send_hid_packet(self.HID_CMD_REQUEST_SAVE, loop_num)

    def parse_loop_file(self, filename):
        """Parse a .loop file and extract track info"""
        try:
            with open(filename, 'rb') as f:
                data = f.read()

            # Basic validation
            if len(data) < 4:
                return None

            # Check magic bytes
            if data[0] != 0xAA or data[1] != 0x55:
                return None

            # This is a single track loop file
            return {
                'tracks': [{'name': 'Main Loop', 'index': 0}],
                'bpm': 120  # TODO: Extract BPM from file
            }

        except Exception as e:
            logger.info(f"Error parsing loop file: {e}")
            return None

    def parse_midi_file(self, filename):
        """Parse a MIDI file and extract track info"""
        try:
            with open(filename, 'rb') as f:
                data = f.read()

            # Basic MIDI file validation
            if len(data) < 14:
                return None

            # Check "MThd" header
            if data[0:4] != b'MThd':
                return None

            # Parse header
            track_count = (data[10] << 8) | data[11]

            # Create track list
            tracks = []
            for i in range(track_count):
                tracks.append({
                    'name': f'Track {i+1}',
                    'index': i
                })

            return {
                'tracks': tracks,
                'bpm': 120  # TODO: Extract BPM from MIDI file
            }

        except Exception as e:
            logger.info(f"Error parsing MIDI file: {e}")
            return None

    def on_browse_files(self):
        """Browse for loop/MIDI files to load"""
        filenames, _ = QFileDialog.getOpenFileNames(
            None, "Select Loop or MIDI Files", "",
            "All Supported (*.loop *.mid *.midi);;Loop Files (*.loop);;MIDI Files (*.mid *.midi);;All Files (*)"
        )

        for filename in filenames:
            # Check if already in list
            found = False
            for i in range(self.file_list.count()):
                if self.file_list.item(i).data(QtCore.Qt.UserRole) == filename:
                    found = True
                    break

            if not found:
                # Parse file to get track info
                file_info = None
                if filename.endswith('.loop'):
                    file_info = self.parse_loop_file(filename)
                elif filename.endswith('.mid') or filename.endswith('.midi'):
                    file_info = self.parse_midi_file(filename)

                if file_info:
                    # Store file info
                    self.loaded_files[filename] = file_info

                # Add to list
                display_name = os.path.basename(filename)
                file_size = os.path.getsize(filename)
                track_count = len(file_info['tracks']) if file_info else 0
                display_text = f"{display_name} ({track_count} tracks, {file_size} bytes)"

                item = QListWidgetItem(display_text)
                item.setData(QtCore.Qt.UserRole, filename)
                self.file_list.addItem(item)

        # Enable load all button if files loaded
        if self.file_list.count() > 0:
            self.load_all_btn.setEnabled(True)

    def on_clear_file_list(self):
        """Clear the file list"""
        self.file_list.clear()
        self.loaded_files.clear()
        self.load_all_btn.setEnabled(False)
        self.pending_assignments.clear()
        self.selected_track = None
        self.update_track_display()
        self.update_assignment_buttons()

    def on_file_selected(self, current, previous):
        """Handle file selection - show tracks"""
        if not current:
            self.update_track_display()
            return

        filename = current.data(QtCore.Qt.UserRole)
        if filename in self.loaded_files:
            self.update_track_display(filename)

        # Enable load all
        self.load_all_btn.setEnabled(True)

    def update_track_display(self, filename=None):
        """Update the track selection display"""
        # Clear existing track buttons
        for i in reversed(range(self.track_buttons_layout.count())):
            self.track_buttons_layout.itemAt(i).widget().deleteLater()

        # Clear button group
        for button in self.track_button_group.buttons():
            self.track_button_group.removeButton(button)

        if not filename or filename not in self.loaded_files:
            self.track_info_label.setText(tr("LoopManager", "Select a MIDI file to see tracks"))
            self.track_info_label.setVisible(True)
            self.track_buttons_widget.setVisible(False)
            return

        file_info = self.loaded_files[filename]
        tracks = file_info['tracks']

        if len(tracks) == 0:
            self.track_info_label.setText(tr("LoopManager", "No tracks found in file"))
            self.track_info_label.setVisible(True)
            self.track_buttons_widget.setVisible(False)
            return

        # Hide info label, show track buttons
        self.track_info_label.setVisible(False)
        self.track_buttons_widget.setVisible(True)

        # Create track buttons (max 4 per row)
        for idx, track in enumerate(tracks):
            row = idx // 4
            col = idx % 4

            btn = QPushButton(track['name'])
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setProperty('filename', filename)
            btn.setProperty('track_idx', idx)

            self.track_button_group.addButton(btn)
            self.track_buttons_layout.addWidget(btn, row, col)

    def on_track_button_clicked(self, button):
        """Handle track button click"""
        filename = button.property('filename')
        track_idx = button.property('track_idx')

        self.selected_track = {
            'filename': filename,
            'track_idx': track_idx
        }

    def on_toggle_advanced(self, state):
        """Toggle advanced track assignment section"""
        self.advanced_section.setVisible(state == QtCore.Qt.Checked)

    def on_assign_main(self, loop_num):
        """Assign selected track to main loop"""
        if not self.selected_track:
            QMessageBox.warning(None, "Warning", "Please select a track first")
            return

        # Store pending assignment
        if loop_num not in self.pending_assignments:
            self.pending_assignments[loop_num] = {}
        self.pending_assignments[loop_num]['main'] = self.selected_track.copy()

        self.update_assignment_buttons()
        self.load_assignments_btn.setEnabled(True)

    def on_assign_overdub(self, loop_num):
        """Assign selected track to overdub loop"""
        if not self.selected_track:
            QMessageBox.warning(None, "Warning", "Please select a track first")
            return

        # Check if main loop has content
        if loop_num not in self.loop_contents and loop_num not in self.pending_assignments:
            QMessageBox.warning(None, "Warning",
                f"Loop {loop_num} must have main content before adding overdub")
            return

        # Store pending assignment
        if loop_num not in self.pending_assignments:
            self.pending_assignments[loop_num] = {}
        self.pending_assignments[loop_num]['overdub'] = self.selected_track.copy()

        self.update_assignment_buttons()
        self.load_assignments_btn.setEnabled(True)

    def on_load_all_tracks(self):
        """Load all tracks from selected file"""
        # TODO: Implement batch loading logic
        QMessageBox.information(None, "Info", "Load all tracks feature coming soon!")

    def on_load_assignments(self):
        """Load assigned tracks to device"""
        # TODO: Implement assignment loading logic
        QMessageBox.information(None, "Info", "Loading assigned tracks...")

    def update_assignment_buttons(self):
        """Update assignment button states and labels"""
        for i in range(4):
            loop_num = i + 1

            # Main button
            if loop_num in self.pending_assignments and 'main' in self.pending_assignments[loop_num]:
                track_info = self.pending_assignments[loop_num]['main']
                filename = track_info['filename']
                file_info = self.loaded_files.get(filename)
                if file_info:
                    track_name = file_info['tracks'][track_info['track_idx']]['name']
                    self.main_assign_btns[i].setText(f"Loop {loop_num}: {track_name[:10]}")
                else:
                    self.main_assign_btns[i].setText(f"Loop {loop_num}: Pending")
            else:
                self.main_assign_btns[i].setText(f"Loop {loop_num}")

            # Overdub button
            has_main = loop_num in self.loop_contents or (
                loop_num in self.pending_assignments and 'main' in self.pending_assignments[loop_num]
            )
            self.overdub_assign_btns[i].setEnabled(has_main)

            if loop_num in self.pending_assignments and 'overdub' in self.pending_assignments[loop_num]:
                track_info = self.pending_assignments[loop_num]['overdub']
                filename = track_info['filename']
                file_info = self.loaded_files.get(filename)
                if file_info:
                    track_name = file_info['tracks'][track_info['track_idx']]['name']
                    self.overdub_assign_btns[i].setText(f"Loop {loop_num}: {track_name[:10]}")
                else:
                    self.overdub_assign_btns[i].setText(f"Loop {loop_num}: Pending")
            else:
                self.overdub_assign_btns[i].setText(f"Loop {loop_num} Overdub")

    def handle_device_response(self, data):
        """Handle incoming HID data from device"""
        logger.info(f"handle_device_response called with {len(data)} bytes")

        if len(data) < self.HID_HEADER_SIZE:
            logger.info(f"Data too short: {len(data)} < {self.HID_HEADER_SIZE}")
            return

        # Validate header
        if (data[0] != self.MANUFACTURER_ID or
            data[1] != self.SUB_ID or
            data[2] != self.DEVICE_ID):
            logger.info(f"Invalid header: {data[0]:02x} {data[1]:02x} {data[2]:02x}")
            return

        command = data[3]
        macro_num = data[4]
        status = data[5]
        payload = data[self.HID_HEADER_SIZE:]

        logger.info(f"Valid packet - Command: 0x{command:02x}, Loop: {macro_num}, Status: {status}")

        if command == self.HID_CMD_SAVE_START:
            logger.info("-> SAVE_START")
            self.handle_save_start(macro_num, status, payload)
        elif command == self.HID_CMD_SAVE_CHUNK:
            logger.info("-> SAVE_CHUNK")
            self.handle_save_chunk(macro_num, status, payload)
        elif command == self.HID_CMD_SAVE_END:
            logger.info("-> SAVE_END")
            self.handle_save_end(macro_num, status)
        else:
            logger.info(f"-> Unknown command: 0x{command:02x}")

    def handle_save_start(self, macro_num, status, data):
        """Handle SAVE_START response from device"""
        logger.info(f"handle_save_start: loop={macro_num}, status={status}, data_len={len(data)}")

        if status != 0:
            logger.info(f"Loop {macro_num} status error: {status}")
            # Loop is empty, skip if in save all mode
            if self.current_transfer.get('save_all_mode'):
                logger.info(f"Loop {macro_num} is empty, skipping...")
                # Move to next loop
                self.current_transfer['save_all_current'] += 1
                QTimer.singleShot(100, self.save_next_loop_in_sequence)
            else:
                self.transfer_complete.emit(False, f"Loop {macro_num} is empty or error occurred")
            return

        # Extract total packets and size from payload - MATCHES WEBAPP FORMAT!
        # Webapp: totalPackets = data[0] | (data[1] << 8); totalSize = data[2] | (data[3] << 8);
        if len(data) >= 4:
            total_packets = data[0] | (data[1] << 8)
            total_size = data[2] | (data[3] << 8)

            self.current_transfer['expected_packets'] = total_packets
            self.current_transfer['total_size'] = total_size

            logger.info(f"SAVE_START: {total_packets} packets, {total_size} bytes total")
        else:
            logger.info(f"Warning: SAVE_START payload too short: {len(data)} bytes")

        self.transfer_progress.emit(0,
            f"Receiving Loop {macro_num}: 0 / {self.current_transfer['total_size']} bytes")

    def handle_save_chunk(self, macro_num, status, data):
        """Handle SAVE_CHUNK response from device"""
        if not self.current_transfer['active']:
            logger.info("handle_save_chunk: transfer not active, ignoring")
            return

        # Parse chunk header - MATCHES WEBAPP FORMAT!
        # Webapp: packetNum = data[0] | (data[1] << 8); chunkLen = data[2] | (data[3] << 8);
        if len(data) >= 4:
            packet_num = data[0] | (data[1] << 8)
            chunk_len = data[2] | (data[3] << 8)

            if chunk_len > 0 and len(data) >= 4 + chunk_len:
                # Extract actual chunk data
                chunk_data = data[4:4 + chunk_len]
                self.current_transfer['received_data'].extend(chunk_data)
                self.current_transfer['received_packets'] += 1

                # Calculate progress
                received = len(self.current_transfer['received_data'])
                total = self.current_transfer['total_size']
                expected_packets = self.current_transfer['expected_packets']

                logger.info(f"Chunk {self.current_transfer['received_packets']}/{expected_packets}: packet#{packet_num}, {chunk_len} bytes (total: {received}/{total})")

                if expected_packets > 0:
                    progress = int((self.current_transfer['received_packets'] / expected_packets) * 100)
                    self.transfer_progress.emit(progress,
                        f"Receiving Loop {macro_num}: {received} / {total} bytes ({progress}%)")
            else:
                logger.info(f"handle_save_chunk: invalid chunk - len={chunk_len}, data_len={len(data)}")
        else:
            logger.info(f"handle_save_chunk: payload too short: {len(data)} bytes")

    def handle_save_end(self, macro_num, status):
        """Handle SAVE_END response from device"""
        logger.info(f"handle_save_end: loop={macro_num}, status={status}")

        if not self.current_transfer['active']:
            logger.info("handle_save_end: transfer not active, ignoring")
            return

        if status == 0:
            # Save to file
            try:
                received_size = len(self.current_transfer['received_data'])
                logger.info(f"Saving {received_size} bytes to {self.current_transfer['file_name']}")

                if self.current_transfer['save_format'] == 'midi':
                    # TODO: Convert loop data to MIDI format
                    data = self.current_transfer['received_data']
                else:
                    data = self.current_transfer['received_data']

                with open(self.current_transfer['file_name'], 'wb') as f:
                    f.write(data)

                logger.info(f"File saved successfully: {self.current_transfer['file_name']}")

                # Check if in save all mode
                if self.current_transfer.get('save_all_mode'):
                    logger.info("Save all mode: moving to next loop")
                    # Continue to next loop
                    self.current_transfer['save_all_current'] += 1
                    self.current_transfer['active'] = False  # Reset for next loop
                    QTimer.singleShot(100, self.save_next_loop_in_sequence)
                else:
                    self.transfer_complete.emit(True,
                        f"Successfully saved Loop {macro_num} to {os.path.basename(self.current_transfer['file_name'])}")

            except Exception as e:
                logger.info(f"Error saving file: {e}")
                self.transfer_complete.emit(False, f"Failed to save file: {str(e)}")

        else:
            logger.info(f"SAVE_END with error status: {status}")
            # Check if in save all mode
            if self.current_transfer.get('save_all_mode'):
                # Continue to next loop even on error
                self.current_transfer['save_all_current'] += 1
                self.current_transfer['active'] = False
                QTimer.singleShot(100, self.save_next_loop_in_sequence)
            else:
                self.transfer_complete.emit(False, f"Failed to receive Loop {macro_num}")

    def on_transfer_progress(self, progress, message):
        """Update UI with transfer progress (thread-safe)"""
        self.save_progress_label.setText(message)
        self.save_progress_bar.setValue(progress)

    def on_transfer_complete(self, success, message):
        """Handle transfer completion (thread-safe)"""
        if success:
            QMessageBox.information(None, "Success", message)
        else:
            QMessageBox.warning(None, "Warning", message)

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
            'file_name': '',
            'save_format': 'loop',
            'save_all_mode': False,
            'save_all_directory': '',
            'save_all_current': 0
        }

        self.save_progress_label.setText("")
        self.save_progress_bar.setValue(0)
        self.save_progress_bar.setVisible(False)

        self.load_progress_label.setText("")
        self.load_progress_bar.setValue(0)
        self.load_progress_bar.setVisible(False)

    def update_loop_contents_display(self):
        """Update the loop contents display"""
        for i in range(4):
            loop_num = i + 1
            if loop_num in self.loop_contents:
                self.loop_content_labels[i].setText(self.loop_contents[loop_num])
            else:
                self.loop_content_labels[i].setText(tr("LoopManager", "Empty"))

    def valid(self):
        """This tab is valid for all VialKeyboard devices"""
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            self.stop_hid_listener()
            return

        # Start HID listener when device connects
        self.start_hid_listener()

        # Reset state when device changes
        self.reset_transfer_state()
        self.loop_contents = {}
        self.overdub_contents = {}
        self.update_loop_contents_display()

    def __del__(self):
        """Cleanup on deletion"""
        self.stop_hid_listener()
