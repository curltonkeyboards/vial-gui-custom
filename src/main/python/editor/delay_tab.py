# SPDX-License-Identifier: GPL-2.0-or-later
"""
MIDI Delay Settings Editor

Configures delay slots (DELAY_1 - DELAY_100) that repeat MIDI notes
with configurable timing, decay, channel routing, and transposition.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QGroupBox, QMessageBox, QSpinBox, QSlider,
                              QListWidget, QListWidgetItem, QStackedWidget,
                              QSizePolicy, QScrollArea, QFrame)
from PyQt5.QtCore import Qt

from editor.basic_editor import BasicEditor
from protocol.delay_protocol import (ProtocolDelay, DelaySlot,
                                      DELAY_NUM_SLOTS, RATE_MODE_BPM, RATE_MODE_FIXED_MS,
                                      TRANSPOSE_FIXED, TRANSPOSE_CUMULATIVE)


class DelaySlotEditor(QWidget):
    """Editor widget for a single delay slot's settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slot = DelaySlot()
        self._building = False

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # ---- Rate Settings ----
        rate_group = QGroupBox("Rate")
        rate_layout = QVBoxLayout()

        # Rate mode
        row = QHBoxLayout()
        row.addWidget(QLabel("Mode:"))
        self.rate_mode_combo = QComboBox()
        self.rate_mode_combo.addItems(["BPM Synced", "Fixed ms"])
        self.rate_mode_combo.currentIndexChanged.connect(self._on_rate_mode_changed)
        row.addWidget(self.rate_mode_combo)
        row.addStretch()
        rate_layout.addLayout(row)

        # BPM-synced controls
        self.bpm_widget = QWidget()
        bpm_layout = QHBoxLayout()
        bpm_layout.setContentsMargins(0, 0, 0, 0)

        bpm_layout.addWidget(QLabel("Note Value:"))
        self.note_value_combo = QComboBox()
        self.note_value_combo.addItems(["Quarter", "Eighth", "Sixteenth"])
        bpm_layout.addWidget(self.note_value_combo)

        bpm_layout.addWidget(QLabel("Timing:"))
        self.timing_combo = QComboBox()
        self.timing_combo.addItems(["Straight", "Triplet", "Dotted"])
        bpm_layout.addWidget(self.timing_combo)

        bpm_layout.addStretch()
        self.bpm_widget.setLayout(bpm_layout)
        rate_layout.addWidget(self.bpm_widget)

        # Fixed ms controls
        self.fixed_widget = QWidget()
        fixed_layout = QHBoxLayout()
        fixed_layout.setContentsMargins(0, 0, 0, 0)

        fixed_layout.addWidget(QLabel("Delay:"))
        self.fixed_ms_spin = QSpinBox()
        self.fixed_ms_spin.setRange(10, 5000)
        self.fixed_ms_spin.setSuffix(" ms")
        self.fixed_ms_spin.setSingleStep(10)
        fixed_layout.addWidget(self.fixed_ms_spin)

        fixed_layout.addStretch()
        self.fixed_widget.setLayout(fixed_layout)
        rate_layout.addWidget(self.fixed_widget)

        rate_group.setLayout(rate_layout)
        layout.addWidget(rate_group)

        # ---- Decay & Repeats ----
        decay_group = QGroupBox("Decay & Repeats")
        decay_layout = QVBoxLayout()

        # Decay slider
        row = QHBoxLayout()
        row.addWidget(QLabel("Decay:"))
        self.decay_slider = QSlider(Qt.Horizontal)
        self.decay_slider.setRange(0, 100)
        self.decay_slider.setTickInterval(10)
        self.decay_slider.setTickPosition(QSlider.TicksBelow)
        row.addWidget(self.decay_slider)
        self.decay_label = QLabel("50%")
        self.decay_label.setMinimumWidth(40)
        row.addWidget(self.decay_label)
        self.decay_slider.valueChanged.connect(
            lambda v: self.decay_label.setText(f"{v}%"))
        decay_layout.addLayout(row)

        # Max repeats
        row = QHBoxLayout()
        row.addWidget(QLabel("Max Repeats:"))
        self.repeats_spin = QSpinBox()
        self.repeats_spin.setRange(0, 255)
        self.repeats_spin.setSpecialValueText("Infinite")
        row.addWidget(self.repeats_spin)
        row.addStretch()
        decay_layout.addLayout(row)

        decay_group.setLayout(decay_layout)
        layout.addWidget(decay_group)

        # ---- Channel & Transpose ----
        routing_group = QGroupBox("Channel & Transpose")
        routing_layout = QVBoxLayout()

        # Channel
        row = QHBoxLayout()
        row.addWidget(QLabel("Channel:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItem("Same as Original")
        for i in range(1, 17):
            self.channel_combo.addItem(f"Channel {i}")
        row.addWidget(self.channel_combo)
        row.addStretch()
        routing_layout.addLayout(row)

        # Transpose
        row = QHBoxLayout()
        row.addWidget(QLabel("Transpose:"))
        self.transpose_spin = QSpinBox()
        self.transpose_spin.setRange(-48, 48)
        self.transpose_spin.setSuffix(" semitones")
        row.addWidget(self.transpose_spin)
        row.addStretch()
        routing_layout.addLayout(row)

        # Transpose mode
        row = QHBoxLayout()
        row.addWidget(QLabel("Transpose Mode:"))
        self.transpose_mode_combo = QComboBox()
        self.transpose_mode_combo.addItems(["Fixed (same offset for all repeats)",
                                             "Cumulative (adds offset each repeat)"])
        row.addWidget(self.transpose_mode_combo)
        row.addStretch()
        routing_layout.addLayout(row)

        routing_group.setLayout(routing_layout)
        layout.addWidget(routing_group)

        layout.addStretch()
        self.setLayout(layout)

        # Initial visibility
        self._on_rate_mode_changed(0)

    def _on_rate_mode_changed(self, index):
        """Show/hide rate controls based on mode"""
        self.bpm_widget.setVisible(index == RATE_MODE_BPM)
        self.fixed_widget.setVisible(index == RATE_MODE_FIXED_MS)

    def load_from_slot(self, slot):
        """Load settings from a DelaySlot object"""
        self._building = True
        self.slot = slot

        self.rate_mode_combo.setCurrentIndex(slot.rate_mode)
        self.note_value_combo.setCurrentIndex(slot.note_value)
        self.timing_combo.setCurrentIndex(slot.timing_mode)
        self.fixed_ms_spin.setValue(slot.fixed_delay_ms)
        self.decay_slider.setValue(slot.decay_percent)
        self.decay_label.setText(f"{slot.decay_percent}%")
        self.repeats_spin.setValue(slot.max_repeats)
        self.channel_combo.setCurrentIndex(slot.channel)
        self.transpose_spin.setValue(slot.transpose_semi)
        self.transpose_mode_combo.setCurrentIndex(slot.transpose_mode)

        self._on_rate_mode_changed(slot.rate_mode)
        self._building = False

    def save_to_slot(self):
        """Save current settings to a DelaySlot object"""
        slot = DelaySlot()
        slot.rate_mode = self.rate_mode_combo.currentIndex()
        slot.note_value = self.note_value_combo.currentIndex()
        slot.timing_mode = self.timing_combo.currentIndex()
        slot.fixed_delay_ms = self.fixed_ms_spin.value()
        slot.decay_percent = self.decay_slider.value()
        slot.max_repeats = self.repeats_spin.value()
        slot.channel = self.channel_combo.currentIndex()
        slot.transpose_semi = self.transpose_spin.value()
        slot.transpose_mode = self.transpose_mode_combo.currentIndex()
        return slot


class DelayTab(BasicEditor):
    """Main Delay settings editor tab"""

    def __init__(self):
        super().__init__()
        self.delay_protocol = None
        self.keyboard = None
        self.loaded_slots = {}  # slot_num -> DelaySlot

        # Main horizontal layout: slot list | settings editor
        main_layout = QHBoxLayout()

        # ---- Left: Slot List ----
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Delay Slots"))

        self.slot_list = QListWidget()
        self.slot_list.setMaximumWidth(180)
        for i in range(DELAY_NUM_SLOTS):
            self.slot_list.addItem(f"Delay {i + 1}")
        self.slot_list.currentRowChanged.connect(self._on_slot_selected)
        left_layout.addWidget(self.slot_list)

        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget)

        # ---- Right: Settings Editor ----
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.slot_editor = DelaySlotEditor()
        scroll = QScrollArea()
        scroll.setWidget(self.slot_editor)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_layout.addWidget(scroll)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.save_slot_btn = QPushButton("Save Slot to Keyboard")
        self.save_slot_btn.clicked.connect(self._on_save_slot)
        btn_layout.addWidget(self.save_slot_btn)

        self.save_all_btn = QPushButton("Save All to EEPROM")
        self.save_all_btn.clicked.connect(self._on_save_all)
        btn_layout.addWidget(self.save_all_btn)

        btn_layout.addStretch()

        self.load_slot_btn = QPushButton("Reload Slot")
        self.load_slot_btn.clicked.connect(self._on_load_slot)
        btn_layout.addWidget(self.load_slot_btn)

        right_layout.addLayout(btn_layout)
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, 1)

        # Wrap in a container widget
        container = QWidget()
        container.setLayout(main_layout)
        self.addWidget(container)

    def valid(self):
        """Tab is valid when a device is connected"""
        return isinstance(self.device, object) and self.device is not None

    def rebuild(self, device):
        """Rebuild when device changes"""
        super().rebuild(device)

        if self.valid():
            self.keyboard = device.keyboard
            self.delay_protocol = ProtocolDelay(self.keyboard)
            self.loaded_slots.clear()

            # Load first slot
            self.slot_list.setCurrentRow(0)
            self._load_slot(0)

    def _on_slot_selected(self, row):
        """Handle slot selection from list"""
        if row < 0 or row >= DELAY_NUM_SLOTS:
            return

        if row in self.loaded_slots:
            self.slot_editor.load_from_slot(self.loaded_slots[row])
        else:
            self._load_slot(row)

    def _load_slot(self, slot_num):
        """Load a slot from the keyboard"""
        if not self.delay_protocol:
            return

        slot = self.delay_protocol.get_slot(slot_num)
        if slot:
            self.loaded_slots[slot_num] = slot
            self.slot_editor.load_from_slot(slot)

    def _on_save_slot(self):
        """Save current slot settings to keyboard"""
        if not self.delay_protocol:
            return

        row = self.slot_list.currentRow()
        if row < 0:
            return

        slot = self.slot_editor.save_to_slot()
        if self.delay_protocol.set_slot(row, slot):
            self.loaded_slots[row] = slot
        else:
            QMessageBox.warning(None, "Error", f"Failed to save delay slot {row + 1}")

    def _on_save_all(self):
        """Save all slot configs to EEPROM"""
        if not self.delay_protocol:
            return

        # First save any unsaved current slot
        row = self.slot_list.currentRow()
        if row >= 0:
            slot = self.slot_editor.save_to_slot()
            self.delay_protocol.set_slot(row, slot)
            self.loaded_slots[row] = slot

        # Trigger EEPROM save
        if self.delay_protocol.save_to_eeprom():
            QMessageBox.information(None, "Success", "All delay settings saved to EEPROM")
        else:
            QMessageBox.warning(None, "Error", "Failed to save to EEPROM")

    def _on_load_slot(self):
        """Reload current slot from keyboard"""
        row = self.slot_list.currentRow()
        if row >= 0:
            # Clear cache for this slot to force reload
            self.loaded_slots.pop(row, None)
            self._load_slot(row)
