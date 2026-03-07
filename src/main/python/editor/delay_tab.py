# SPDX-License-Identifier: GPL-2.0-or-later
"""
MIDI Delay Settings Editor

Configures delay slots (DELAY_01 - DELAY_100) that repeat MIDI notes
with configurable timing, decay, channel routing, and transposition.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QGroupBox, QMessageBox, QSpinBox, QSlider,
                              QCheckBox, QSizePolicy, QScrollArea, QTabWidget)
from PyQt5.QtCore import Qt

from editor.basic_editor import BasicEditor
from protocol.delay_protocol import (ProtocolDelay, DelaySlot,
                                      DELAY_NUM_SLOTS, RATE_MODE_BPM, RATE_MODE_FIXED_MS,
                                      TRANSPOSE_FIXED, TRANSPOSE_CUMULATIVE)
from vial_device import VialKeyboard


# Repeats slider: positions 0-9 map to [1,2,3,4,5,6,7,8,9,255]
REPEATS_VALUES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 255]
REPEATS_LABELS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "\u221E"]  # infinity symbol


def repeats_to_slider(val):
    """Convert max_repeats value to slider position"""
    if val >= 255 or val == 0:
        return 9  # Infinite
    if val < 1:
        return 0
    if val > 9:
        return 9
    return val - 1


def slider_to_repeats(pos):
    """Convert slider position to max_repeats value"""
    if pos < 0:
        pos = 0
    if pos >= len(REPEATS_VALUES):
        pos = len(REPEATS_VALUES) - 1
    return REPEATS_VALUES[pos]


class DelaySlotEditor(QWidget):
    """Editor widget for a single delay slot's settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slot = DelaySlot()
        self._building = False

        outer = QHBoxLayout()
        outer.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ---- Rate & Decay (combined box) ----
        rate_group = QGroupBox("Rate && Decay")
        rate_layout = QVBoxLayout()
        rate_layout.setSpacing(6)

        # Row 1: Mode + Note Value + Timing (BPM) or Mode + Delay ms (Fixed)
        row = QHBoxLayout()
        row.addWidget(QLabel("Mode:"))
        self.rate_mode_combo = QComboBox()
        self.rate_mode_combo.addItems(["BPM Synced", "Fixed ms"])
        self.rate_mode_combo.setMinimumWidth(110)
        self.rate_mode_combo.currentIndexChanged.connect(self._on_rate_mode_changed)
        row.addWidget(self.rate_mode_combo)

        # BPM controls (inline)
        self.note_value_label = QLabel("  Note:")
        row.addWidget(self.note_value_label)
        self.note_value_combo = QComboBox()
        self.note_value_combo.addItems(["1/1", "1/2", "1/4", "1/8", "1/16"])
        self.note_value_combo.setMinimumWidth(70)
        row.addWidget(self.note_value_combo)

        self.timing_label = QLabel("  Timing:")
        row.addWidget(self.timing_label)
        self.timing_combo = QComboBox()
        self.timing_combo.addItems(["Note", "Triplet", "Dotted"])
        self.timing_combo.setMinimumWidth(90)
        row.addWidget(self.timing_combo)

        # Fixed ms control (inline, hidden by default)
        self.fixed_ms_label = QLabel("  Delay:")
        self.fixed_ms_label.setVisible(False)
        row.addWidget(self.fixed_ms_label)
        self.fixed_ms_spin = QSpinBox()
        self.fixed_ms_spin.setRange(10, 5000)
        self.fixed_ms_spin.setSuffix(" ms")
        self.fixed_ms_spin.setSingleStep(10)
        self.fixed_ms_spin.setMinimumWidth(110)
        self.fixed_ms_spin.setVisible(False)
        row.addWidget(self.fixed_ms_spin)

        row.addStretch()
        rate_layout.addLayout(row)

        # Row 2: Decay slider
        row = QHBoxLayout()
        row.addWidget(QLabel("Decay:"))
        self.decay_slider = QSlider(Qt.Horizontal)
        self.decay_slider.setRange(0, 100)
        self.decay_slider.setTickInterval(25)
        self.decay_slider.setTickPosition(QSlider.TicksBelow)
        row.addWidget(self.decay_slider)
        self.decay_label = QLabel("50%")
        self.decay_label.setMinimumWidth(36)
        row.addWidget(self.decay_label)
        self.decay_slider.valueChanged.connect(
            lambda v: self.decay_label.setText(f"{v}%"))
        rate_layout.addLayout(row)

        # Row 3: Max Repeats slider
        row = QHBoxLayout()
        row.addWidget(QLabel("Repeats:"))
        self.repeats_slider = QSlider(Qt.Horizontal)
        self.repeats_slider.setRange(0, 9)
        self.repeats_slider.setTickInterval(1)
        self.repeats_slider.setTickPosition(QSlider.TicksBelow)
        row.addWidget(self.repeats_slider)
        self.repeats_label = QLabel("3")
        self.repeats_label.setMinimumWidth(20)
        row.addWidget(self.repeats_label)
        self.repeats_slider.valueChanged.connect(self._on_repeats_changed)
        rate_layout.addLayout(row)

        rate_group.setLayout(rate_layout)
        layout.addWidget(rate_group)

        # ---- Channel Delay ----
        channel_group = QGroupBox("Channel Delay")
        channel_layout = QVBoxLayout()
        channel_layout.setSpacing(4)

        self.channel_check = QCheckBox("Send delay to different channel")
        self.channel_check.stateChanged.connect(self._on_channel_check_changed)
        channel_layout.addWidget(self.channel_check)

        self.channel_row = QHBoxLayout()
        self.channel_row_label = QLabel("Output Channel:")
        self.channel_row.addWidget(self.channel_row_label)
        self.channel_combo = QComboBox()
        for i in range(1, 17):
            self.channel_combo.addItem(f"Channel {i}")
        self.channel_combo.setMinimumWidth(140)
        self.channel_row.addWidget(self.channel_combo)
        self.channel_row.addStretch()
        channel_layout.addLayout(self.channel_row)

        # Initially hidden
        self.channel_row_label.setVisible(False)
        self.channel_combo.setVisible(False)

        channel_group.setLayout(channel_layout)
        layout.addWidget(channel_group)

        # ---- Pitch Delay ----
        pitch_group = QGroupBox("Pitch Delay")
        pitch_layout = QVBoxLayout()
        pitch_layout.setSpacing(6)

        # Transpose slider
        row = QHBoxLayout()
        row.addWidget(QLabel("Semitones:"))
        self.transpose_slider = QSlider(Qt.Horizontal)
        self.transpose_slider.setRange(-24, 24)
        self.transpose_slider.setTickInterval(12)
        self.transpose_slider.setTickPosition(QSlider.TicksBelow)
        row.addWidget(self.transpose_slider)
        self.transpose_label = QLabel("0")
        self.transpose_label.setMinimumWidth(32)
        row.addWidget(self.transpose_label)
        self.transpose_slider.valueChanged.connect(self._on_transpose_changed)
        pitch_layout.addLayout(row)

        # Tick labels for -24, -12, 0, +12, +24
        tick_row = QHBoxLayout()
        tick_row.addSpacing(72)
        for lbl in ["-24", "-12", "0", "+12", "+24"]:
            t = QLabel(lbl)
            t.setStyleSheet("font-size: 9px; color: gray;")
            tick_row.addWidget(t)
            if lbl != "+24":
                tick_row.addStretch()
        tick_row.addSpacing(40)
        pitch_layout.addLayout(tick_row)

        # Transpose mode
        row = QHBoxLayout()
        row.addWidget(QLabel("Mode:"))
        self.transpose_mode_combo = QComboBox()
        self.transpose_mode_combo.addItems(["Fixed", "Cumulative"])
        self.transpose_mode_combo.setMinimumWidth(120)
        row.addWidget(self.transpose_mode_combo)
        row.addStretch()
        pitch_layout.addLayout(row)

        pitch_group.setLayout(pitch_layout)
        layout.addWidget(pitch_group)

        # ---- Options ----
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        self.solo_check = QCheckBox("Solo mode (new note cancels pending delays)")
        options_layout.addWidget(self.solo_check)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        layout.addStretch()

        center_widget = QWidget()
        center_widget.setMaximumWidth(640)
        center_widget.setLayout(layout)
        outer.addWidget(center_widget)
        outer.addStretch()
        self.setLayout(outer)

        # Initial visibility
        self._on_rate_mode_changed(0)

    def _on_rate_mode_changed(self, index):
        """Show/hide rate controls based on mode"""
        is_bpm = (index == RATE_MODE_BPM)
        self.note_value_label.setVisible(is_bpm)
        self.note_value_combo.setVisible(is_bpm)
        self.timing_label.setVisible(is_bpm)
        self.timing_combo.setVisible(is_bpm)
        self.fixed_ms_label.setVisible(not is_bpm)
        self.fixed_ms_spin.setVisible(not is_bpm)

    def _on_channel_check_changed(self, state):
        """Show/hide channel dropdown based on checkbox"""
        checked = (state == Qt.Checked)
        self.channel_row_label.setVisible(checked)
        self.channel_combo.setVisible(checked)

    def _on_repeats_changed(self, pos):
        """Update repeats label from slider position"""
        self.repeats_label.setText(REPEATS_LABELS[pos])

    def _on_transpose_changed(self, val):
        """Update transpose label"""
        self.transpose_label.setText(f"{val:+d}" if val != 0 else "0")

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
        self.repeats_slider.setValue(repeats_to_slider(slot.max_repeats))
        self._on_repeats_changed(repeats_to_slider(slot.max_repeats))

        # Channel: 0=same (unchecked), 1-16=different channel (checked)
        if slot.channel == 0:
            self.channel_check.setChecked(False)
            self.channel_combo.setCurrentIndex(0)
        else:
            self.channel_check.setChecked(True)
            self.channel_combo.setCurrentIndex(slot.channel - 1)

        self.transpose_slider.setValue(slot.transpose_semi)
        self._on_transpose_changed(slot.transpose_semi)
        self.transpose_mode_combo.setCurrentIndex(slot.transpose_mode)
        self.solo_check.setChecked(slot.solo_mode)

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
        slot.max_repeats = slider_to_repeats(self.repeats_slider.value())

        # Channel: unchecked=0 (same), checked=1-16
        if self.channel_check.isChecked():
            slot.channel = self.channel_combo.currentIndex() + 1
        else:
            slot.channel = 0

        slot.transpose_semi = self.transpose_slider.value()
        slot.transpose_mode = self.transpose_mode_combo.currentIndex()
        slot.solo_mode = self.solo_check.isChecked()
        return slot


class DelayTab(BasicEditor):
    """Main Delay settings editor tab - tabbed slot interface like Toggle Keys"""

    def __init__(self):
        super().__init__()
        self.delay_protocol = None
        self.keyboard = None
        self.loaded_slots = {}  # slot_num -> DelaySlot
        self.slot_editors = []
        self.slot_scroll_widgets = []

        # Dynamic tab tracking
        self._visible_tab_count = 1
        self._manually_expanded_count = 0

        # Title
        title = QLabel("MIDI Delay")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.addWidget(title)

        # Tab widget for delay slots
        self.tabs = QTabWidget()

        # Create all slot editors and scroll wrappers
        for i in range(DELAY_NUM_SLOTS):
            editor = DelaySlotEditor()
            self.slot_editors.append(editor)

            scroll = QScrollArea()
            scroll.setWidget(editor)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.slot_scroll_widgets.append(scroll)

        self.addWidget(self.tabs)

        # Connect tab changes for lazy loading and "+" tab handling
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Bottom action buttons
        button_layout = QHBoxLayout()

        self.save_slot_btn = QPushButton("Save Slot")
        self.save_slot_btn.clicked.connect(self._on_save_slot)
        button_layout.addWidget(self.save_slot_btn)

        self.save_all_btn = QPushButton("Save All to EEPROM")
        self.save_all_btn.clicked.connect(self._on_save_all)
        button_layout.addWidget(self.save_all_btn)

        button_layout.addStretch()

        self.reload_btn = QPushButton("Reload Slot")
        self.reload_btn.clicked.connect(self._on_reload_slot)
        button_layout.addWidget(self.reload_btn)

        self.addLayout(button_layout)

    def valid(self):
        """Tab is valid when a Vial keyboard is connected"""
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        """Rebuild when device changes"""
        super().rebuild(device)

        if self.valid():
            self.keyboard = device.keyboard
            self.delay_protocol = ProtocolDelay(self.keyboard)
            self.loaded_slots.clear()

            # Reset manual expansion and scan for used slots
            self._manually_expanded_count = 0
            self._scan_and_update_visible_tabs()

    def _scan_and_update_visible_tabs(self):
        """Scan all slots to find which have non-default config and update visible tabs"""
        if not self.delay_protocol:
            return

        last_used = -1
        for i in range(DELAY_NUM_SLOTS):
            slot = self.delay_protocol.get_slot(i)
            if slot:
                self.loaded_slots[i] = slot
                self.slot_editors[i].load_from_slot(slot)
                if not slot.is_default():
                    last_used = i

        self._update_visible_tabs_with_last_used(last_used)

    def _update_visible_tabs_with_last_used(self, last_used):
        """Update visible tabs given the last used index"""
        base_visible = max(1, last_used + 1)
        self._visible_tab_count = min(DELAY_NUM_SLOTS, base_visible + self._manually_expanded_count)

        # Remove all tabs
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)

        # Add visible delay tabs
        for x in range(self._visible_tab_count):
            self.tabs.addTab(self.slot_scroll_widgets[x], f"Delay {x + 1}")

        # Add "+" tab if not all tabs are visible
        if self._visible_tab_count < DELAY_NUM_SLOTS:
            plus_widget = QWidget()
            self.tabs.addTab(plus_widget, "+")

    def _on_tab_changed(self, index):
        """Handle tab change - lazy load and handle '+' tab"""
        # Check if "+" tab was clicked
        if self._visible_tab_count < DELAY_NUM_SLOTS and index == self._visible_tab_count:
            self._manually_expanded_count += 1
            self._update_visible_tabs()
            self.tabs.setCurrentIndex(self._visible_tab_count - 1)
            return

        # Lazy load: Only load slot data when first viewing the tab
        if 0 <= index < DELAY_NUM_SLOTS:
            if self.delay_protocol and index not in self.loaded_slots:
                slot = self.delay_protocol.get_slot(index)
                if slot:
                    self.loaded_slots[index] = slot
                    self.slot_editors[index].load_from_slot(slot)

    def _find_last_used_index(self):
        """Find the index of the last delay slot that has non-default config"""
        for idx in range(DELAY_NUM_SLOTS - 1, -1, -1):
            if idx in self.loaded_slots and not self.loaded_slots[idx].is_default():
                return idx
        return -1

    def _update_visible_tabs(self):
        """Update which tabs are visible based on content and manual expansion"""
        last_used = self._find_last_used_index()
        self._update_visible_tabs_with_last_used(last_used)

    def _on_save_slot(self):
        """Save current slot settings to keyboard"""
        if not self.delay_protocol:
            return

        index = self.tabs.currentIndex()
        if index < 0 or index >= DELAY_NUM_SLOTS:
            return

        slot = self.slot_editors[index].save_to_slot()
        if self.delay_protocol.set_slot(index, slot):
            self.loaded_slots[index] = slot
        else:
            QMessageBox.warning(None, "Error", f"Failed to save delay slot {index + 1}")

    def _on_save_all(self):
        """Save all slot configs to EEPROM"""
        if not self.delay_protocol:
            return

        # Save current slot first
        index = self.tabs.currentIndex()
        if 0 <= index < DELAY_NUM_SLOTS:
            slot = self.slot_editors[index].save_to_slot()
            self.delay_protocol.set_slot(index, slot)
            self.loaded_slots[index] = slot

        # Trigger EEPROM save
        if self.delay_protocol.save_to_eeprom():
            QMessageBox.information(None, "Success", "All delay settings saved to EEPROM")
        else:
            QMessageBox.warning(None, "Error", "Failed to save to EEPROM")

    def _on_reload_slot(self):
        """Reload current slot from keyboard"""
        index = self.tabs.currentIndex()
        if 0 <= index < DELAY_NUM_SLOTS:
            self.loaded_slots.pop(index, None)
            if self.delay_protocol:
                slot = self.delay_protocol.get_slot(index)
                if slot:
                    self.loaded_slots[index] = slot
                    self.slot_editors[index].load_from_slot(slot)
