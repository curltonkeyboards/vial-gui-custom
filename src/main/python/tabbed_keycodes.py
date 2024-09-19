# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTabWidget, QWidget, QScrollArea, QApplication, QVBoxLayout, QComboBox, QSizePolicy, QLabel, QGridLayout
from PyQt5.QtGui import QPalette

from constants import KEYCODE_BTN_RATIO
from widgets.display_keyboard import DisplayKeyboard
from widgets.display_keyboard_defs import ansi_100, ansi_80, ansi_70, iso_100, iso_80, iso_70, mods, mods_narrow, midi_layout
from widgets.flowlayout import FlowLayout
from keycodes.keycodes import KEYCODES_BASIC, KEYCODES_ISO, KEYCODES_MACRO, KEYCODES_LAYERS, KEYCODES_QUANTUM, \
    KEYCODES_BOOT, KEYCODES_MODIFIERS, \
    KEYCODES_BACKLIGHT, KEYCODES_MEDIA, KEYCODES_SPECIAL, KEYCODES_SHIFTED, KEYCODES_USER, Keycode, \
    KEYCODES_TAP_DANCE, KEYCODES_MIDI, KEYCODES_BASIC_NUMPAD, KEYCODES_BASIC_NAV, KEYCODES_ISO_KR, BASIC_KEYCODES, \
    KEYCODES_MIDI_CC, KEYCODES_MIDI_BANK, KEYCODES_Program_Change, KEYCODES_ENCODER_SENSITIVITY, KEYCODES_MIDI_VELOCITY, \
    KEYCODES_MIDI_VELOCITYENCODER, KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_TRANSPOSITION, KEYCODES_MIDI_CHORD, KEYCODES_MIDI_INVERSION, KEYCODES_MIDI_SCALES
from widgets.square_button import SquareButton
from widgets.big_square_button import BigSquareButton
from util import tr, KeycodeDisplay


class AlternativeDisplay(QWidget):

    keycode_changed = pyqtSignal(str)

    def __init__(self, kbdef, keycodes, prefix_buttons):
        super().__init__()

        self.kb_display = None
        self.keycodes = keycodes
        self.buttons = []

        self.key_layout = FlowLayout()

        if prefix_buttons:
            for title, code in prefix_buttons:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setText(title)
                btn.clicked.connect(lambda st, k=code: self.keycode_changed.emit(title))
                self.key_layout.addWidget(btn)

        layout = QVBoxLayout()
        if kbdef:
            self.kb_display = DisplayKeyboard(kbdef)
            self.kb_display.keycode_changed.connect(self.keycode_changed)
            layout.addWidget(self.kb_display)
            layout.setAlignment(self.kb_display, Qt.AlignHCenter)
        layout.addLayout(self.key_layout)
        self.setLayout(layout)

    def recreate_buttons(self, keycode_filter):
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons = []

        for keycode in self.keycodes:
            if not keycode_filter(keycode.qmk_id):
                continue
            btn = SquareButton()
            btn.setRelSize(KEYCODE_BTN_RATIO)
            btn.setToolTip(Keycode.tooltip(keycode.qmk_id))
            btn.clicked.connect(lambda st, k=keycode: self.keycode_changed.emit(k.qmk_id))
            btn.keycode = keycode
            self.key_layout.addWidget(btn)
            self.buttons.append(btn)

        self.relabel_buttons()

    def relabel_buttons(self):
        if self.kb_display:
            self.kb_display.relabel_buttons()

        KeycodeDisplay.relabel_buttons(self.buttons)

    def required_width(self):
        return self.kb_display.sizeHint().width() if self.kb_display else 0

    def has_buttons(self):
        return len(self.buttons) > 0


class Tab(QScrollArea):

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, alts, prefix_buttons=None):
        super().__init__(parent)

        self.label = label
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.alternatives = []
        for kb, keys in alts:
            alt = AlternativeDisplay(kb, keys, prefix_buttons)
            alt.keycode_changed.connect(self.keycode_changed)
            self.layout.addWidget(alt)
            self.alternatives.append(alt)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)

        w = QWidget()
        w.setLayout(self.layout)
        self.setWidget(w)

    def recreate_buttons(self, keycode_filter):
        for alt in self.alternatives:
            alt.recreate_buttons(keycode_filter)
        self.setVisible(self.has_buttons())

    def relabel_buttons(self):
        for alt in self.alternatives:
            alt.relabel_buttons()

    def has_buttons(self):
        for alt in self.alternatives:
            if alt.has_buttons():
                return True
        return False

    def select_alternative(self):
        # hide everything first
        for alt in self.alternatives:
            alt.hide()

        # then display first alternative which fits on screen w/o horizontal scroll
        for alt in self.alternatives:
            if self.width() - self.verticalScrollBar().width() > alt.required_width():
                alt.show()
                break

    def resizeEvent(self, evt):
        super().resizeEvent(evt)
        self.select_alternative()
        
class MidiTab(QScrollArea):

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, alts, prefix_buttons=None):
        super().__init__(parent)

        self.label = label
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.alternatives = []
        for kb, keys in alts:
            alt = AlternativeDisplay(kb, keys, prefix_buttons)
            alt.keycode_changed.connect(self.keycode_changed)
            self.layout.addWidget(alt)
            self.alternatives.append(alt)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)

        w = QWidget()
        w.setLayout(self.layout)
        self.setWidget(w)

    def recreate_buttons(self, keycode_filter):
        for alt in self.alternatives:
            alt.recreate_buttons(keycode_filter)
        self.setVisible(self.has_buttons())

    def relabel_buttons(self):
        for alt in self.alternatives:
            alt.relabel_buttons()

    def has_buttons(self):
        for alt in self.alternatives:
            if alt.has_buttons():
                return True
        return False

    def select_alternative(self):
        # hide everything first
        for alt in self.alternatives:
            alt.hide()

        # then display first alternative which fits on screen w/o horizontal scroll
        for alt in self.alternatives:
            if self.width() - self.verticalScrollBar().width() > alt.required_width():
                alt.show()
                break

    def resizeEvent(self, evt):
        super().resizeEvent(evt)
        self.select_alternative()
        
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QGridLayout, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtCore import pyqtSignal

class SmartChordTab(QWidget):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, smartchord_keycodes, scales_modes_keycodes, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.smartchord_keycodes = smartchord_keycodes
        self.scales_modes_keycodes = scales_modes_keycodes
        self.inversion_keycodes = inversion_keycodes

        # Define MIDI layout
        self.midi_layout2 = [
            ["MI_Cs", "MI_Ds", "MI_Fs", "MI_Gs", "MI_As",
            "MI_Cs_1", "MI_Ds_1", "MI_Fs_1", "MI_Gs_1", "MI_As_1",
            "MI_Cs_2", "MI_Ds_2", "MI_Fs_2", "MI_Gs_2", "MI_As_2"],

            ["MI_C", "MI_D", "MI_E", "MI_F", "MI_G", "MI_A", "MI_B",
             "MI_C_1", "MI_D_1", "MI_E_1", "MI_F_1", "MI_G_1", "MI_A_1", "MI_B_1",
             "MI_C_2", "MI_D_2", "MI_E_2", "MI_F_2", "MI_G_2", "MI_A_2", "MI_B_2"],

            ["MI_Cs_3", "MI_Ds_3", "MI_Fs_3", "MI_Gs_3", "MI_As_3",
             "MI_Cs_4", "MI_Ds_4", "MI_Fs_4", "MI_Gs_4", "MI_As_4",
             "MI_Cs_5", "MI_Ds_5", "MI_Fs_5", "MI_Gs_5", "MI_As_5"],

            ["MI_C_3", "MI_D_3", "MI_E_3", "MI_F_3", "MI_G_3", "MI_A_3", "MI_B_3",
             "MI_C_4", "MI_D_4", "MI_E_4", "MI_F_4", "MI_G_4", "MI_A_4", "MI_B_4",
             "MI_C_5", "MI_D_5", "MI_E_5", "MI_F_5", "MI_G_5", "MI_A_5", "MI_B_5"]
        ]

        # Main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # 3. MIDI Layout
        self.add_midi_layout2(self.midi_layout2)

        # 1. SmartChord Header and Dropdown
        self.add_header_dropdown("Chords", self.smartchord_keycodes)

        # 2. Scales/Modes Header and Dropdown
        self.add_header_dropdown("Scales/Modes", self.scales_modes_keycodes)

        # 4. Inversions Header
        self.inversion_label = QLabel("Chord Inversions")
        self.main_layout.addWidget(self.inversion_label)

        # Layout for buttons (Inversions)
        self.button_layout = QHBoxLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the inversion buttons
        self.recreate_buttons()  # Call without arguments initially

        # 5. Spacer to push everything to the top
        self.main_layout.addStretch()

    def add_header_dropdown(self, header_text, keycodes):
        """Helper method to add a header and dropdown."""
        # Create header
        header_label = QLabel(header_text)
        self.main_layout.addWidget(header_label)

        # Create dropdown
        dropdown = QComboBox()
        dropdown.setFixedWidth(300)  # Width stays at 300
        dropdown.setFixedHeight(40)  # Increase the height to 40 pixels
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        self.main_layout.addWidget(dropdown)

    def add_midi_layout2(self, layout):
        """Helper method to add staggered buttons based on MIDI layout."""
        midi_container = QWidget()
        midi_container_layout = QVBoxLayout()  # Use QVBoxLayout for rows
        midi_container.setLayout(midi_container_layout)
        self.main_layout.addWidget(midi_container)

        # Parse and add staggered buttons for black and white keys
        self.create_midi_buttons(layout, midi_container_layout)

    def create_midi_buttons(self, layout, container_layout):
        """Create buttons based on MIDI layout coordinates."""
        name_mapping = {
            "MI_Cs": "C#\nDb",
            "MI_Ds": "D#\nEb",
            "MI_Fs": "F#\nGb",
            "MI_Gs": "G#\nAb",
            "MI_As": "A#\nBb",
            "MI_Cs_1": "C#1\nDb1",
            "MI_Ds_1": "D#1\nEb1",
            "MI_Fs_1": "F#1\nGb1",
            "MI_Gs_1": "G#1\nAb1",
            "MI_As_1": "A#1\nBb1",
            "MI_Cs_2": "C#2\nDb2",
            "MI_Ds_2": "D#2\nEb2",
            "MI_Fs_2": "F#2\nGb2",
            "MI_Gs_2": "G#2\nAb2",
            "MI_As_2": "A#2\nBb2",
            "MI_C_1": "C1",
            "MI_D_1": "D1",
            "MI_E_1": "E1",
            "MI_F_1": "F1",
            "MI_G_1": "G1",
            "MI_A_1": "A1",
            "MI_B_1": "B1",
            "MI_C_2": "C2",
            "MI_D_2": "D2",
            "MI_E_2": "E2",
            "MI_F_2": "F2",
            "MI_G_2": "G2",
            "MI_A_2": "A2",
            "MI_B_2": "B2",
            "MI_Cs_3": "C#3\nDb3",
            "MI_Ds_3": "D#3\nEb3",
            "MI_Fs_3": "F#3\nGb3",
            "MI_Gs_3": "G#3\nAb3",
            "MI_As_3": "A#3\nBb3",
            "MI_Cs_4": "C#4\nDb4",
            "MI_Ds_4": "D#4\nEb4",
            "MI_Fs_4": "F#4\nGb4",
            "MI_Gs_4": "G#4\nAb4",
            "MI_As_4": "A#4\nBb4",
            "MI_Cs_5": "C#5\nDb5",
            "MI_Ds_5": "D#5\nEb5",
            "MI_Fs_5": "F#5\nGb5",
            "MI_Gs_5": "G#5\nAb5",
            "MI_As_5": "A#5\nBb5",
            "MI_C_3": "C3",
            "MI_D_3": "D3",
            "MI_E_3": "E3",
            "MI_F_3": "F3",
            "MI_G_3": "G3",
            "MI_A_3": "A3",
            "MI_B_3": "B3",
            "MI_C_4": "C4",
            "MI_D_4": "D4",
            "MI_E_4": "E4",
            "MI_F_4": "F4",
            "MI_G_4": "G4",
            "MI_A_4": "A4",
            "MI_B_4": "B4",
            "MI_C_5": "C5",
            "MI_D_5": "D5",
            "MI_E_5": "E5",
            "MI_F_5": "F5",
            "MI_G_5": "G5",
            "MI_A_5": "A5",
            "MI_B_5": "B5",
            "MI_C": "C",
            "MI_D": "D",
            "MI_E": "E",
            "MI_F": "F",
            "MI_G": "G",
            "MI_A": "A",
            "MI_B": "B"
        }

        for row_index, row in enumerate(layout):
            hbox = QHBoxLayout()  # New horizontal row layout
            for col_index, item in enumerate(row):
                if isinstance(item, str):
                    readable_name = name_mapping.get(item, item)
                    button = SquareButton()
                    button.setText(readable_name)
                    button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    hbox.setSpacing(0)    # Set spacing between widgets in this layout to 0
                    hbox.setContentsMargins(0, 0, 0, 0)  # Remove margins

                    if "#" in readable_name:  # Sharp keys have # in their name
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        # Add an empty space before the black keys to stagger
                        
                    else:
                        button.setStyleSheet("background-color: rgba(190, 190, 190, 1); color: rgba(30, 30, 30, 1);")
                        
                    if readable_name in ["C#\nDb", "C#3\nDb3"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        hbox.addSpacing(20)
                        
                    if readable_name in ["C#1\nDb1", "C#2\nDb2", "C#4\nDb4", "C#5\nDb5"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        hbox.addSpacing(40)
                        
                    if readable_name in ["F#\nGb", "F#1\nGb1", "F#2\nGb2", "F#3\nGb3", "F#4\nGb4", "F#5\nGb5"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        hbox.addSpacing(50)
                        
                    if readable_name in ["C1", "C2", "C4", "C5"]:
                        button.setStyleSheet("background-color: rgba(190, 190, 190, 1); color: rgba(30, 30, 30, 1);")
                        hbox.addSpacing(20)

                    

                    button.setFixedHeight(30)  # Set size as needed
                    button.setFixedWidth(40)  # Set size as needed
                    button.clicked.connect(lambda _, text=item: self.keycode_changed.emit(text))
                    hbox.addWidget(button)  # Add button to horizontal layout

            container_layout.addLayout(hbox)  # Add row to vertical layout    
            container_layout.setRowStretch(row_index, 0)
            container_layout.setColumnStretch(0, 0)            

    def recreate_buttons(self, keycode_filter=None):
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Populate inversion buttons
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = BigSquareButton()
                btn.setFixedWidth(100)  # Set a fixed width for buttons
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode  # Make sure keycode attribute is set
                self.button_layout.addWidget(btn)

    def on_selection_change(self, index):
        selected_qmk_id = self.sender().itemData(index)
        if selected_qmk_id:
            self.keycode_changed.emit(selected_qmk_id)

    def relabel_buttons(self):
        # Handle relabeling only for buttons
        for i in range(self.button_layout.count()):
            widget = self.button_layout.itemAt(i).widget()
            if isinstance(widget, SquareButton):
                keycode = widget.keycode
                if keycode:
                    widget.setText(Keycode.label(keycode.qmk_id))

    def has_buttons(self):
        """Check if there are buttons or dropdown items."""
        return (self.button_layout.count() > 0)


class SimpleTab(Tab):

    def __init__(self, parent, label, keycodes):
        super().__init__(parent, label, [(None, keycodes)])


def keycode_filter_any(kc):
    return True


def keycode_filter_masked(kc):
    return Keycode.is_basic(kc)


class FilteredTabbedKeycodes(QTabWidget):

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self, parent=None, keycode_filter=keycode_filter_any):
        super().__init__(parent)

        self.keycode_filter = keycode_filter

        self.tabs = [
            Tab(self, "Basic", [
                (ansi_100, KEYCODES_SPECIAL + KEYCODES_SHIFTED),
                (ansi_80, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_SHIFTED),
                (ansi_70, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_BASIC_NAV + KEYCODES_SHIFTED),
                (None, KEYCODES_SPECIAL + KEYCODES_BASIC + KEYCODES_SHIFTED),
            ], prefix_buttons=[("Any", -1)]),
            Tab(self, "ISO/JIS", [
                (iso_100, KEYCODES_SPECIAL + KEYCODES_SHIFTED + KEYCODES_ISO_KR),
                (iso_80, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_SHIFTED + KEYCODES_ISO_KR),
                (iso_70, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_BASIC_NAV + KEYCODES_SHIFTED +
                 KEYCODES_ISO_KR),
                (None, KEYCODES_ISO),
            ], prefix_buttons=[("Any", -1)]),
            SimpleTab(self, "Layers", KEYCODES_LAYERS),
            Tab(self, "Quantum", [(mods, (KEYCODES_BOOT + KEYCODES_QUANTUM)),
                                  (mods_narrow, (KEYCODES_BOOT + KEYCODES_QUANTUM)),
                                  (None, (KEYCODES_BOOT + KEYCODES_MODIFIERS + KEYCODES_QUANTUM))]),
            SimpleTab(self, "Backlight", KEYCODES_BACKLIGHT),
            SimpleTab(self, "App, Media and Mouse", KEYCODES_MEDIA),
            SimpleTab(self, "Macro", KEYCODES_MACRO),
            SimpleTab(self, "MIDI Notes", KEYCODES_MIDI),
            MidiTab(self, "MIDI", [
                (midi_layout, KEYCODES_MIDI_CHANNEL),                
            ], prefix_buttons=None),
            SmartChordTab(self, "SmartChord", KEYCODES_MIDI_CHORD, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_INVERSION),   # Updated to SmartChordTab
            SimpleTab(self, "MIDI Channel", KEYCODES_MIDI_CHANNEL),
            SimpleTab(self, "MIDI Transpose", KEYCODES_MIDI_TRANSPOSITION),
            SimpleTab(self, "MIDI Velocity", KEYCODES_MIDI_VELOCITYENCODER + KEYCODES_MIDI_VELOCITY),            
            SimpleTab(self, "MIDI CC", KEYCODES_MIDI_CC),
            SimpleTab(self, "MIDI Program Change", KEYCODES_Program_Change),
            SimpleTab(self, "Encoder Sensitivity", KEYCODES_ENCODER_SENSITIVITY),
            SimpleTab(self, "Tap Dance", KEYCODES_TAP_DANCE),
            SimpleTab(self, "User", KEYCODES_USER),
            SimpleTab(self, "MIDI BANK", KEYCODES_MIDI_BANK),
        ]

        for tab in self.tabs:
            tab.keycode_changed.connect(self.on_keycode_changed)

        self.recreate_keycode_buttons()
        KeycodeDisplay.notify_keymap_override(self)
        
        for miditab in self.tabs:
            tab.keycode_changed.connect(self.on_keycode_changed)

        self.recreate_keycode_buttons()
        KeycodeDisplay.notify_keymap_override(self)

    def on_keycode_changed(self, code):
        if code == "Any":
            self.anykey.emit()
        else:
            self.keycode_changed.emit(Keycode.normalize(code))

    def recreate_keycode_buttons(self):
        prev_tab = self.tabText(self.currentIndex()) if self.currentIndex() >= 0 else ""
        while self.count() > 0:
            self.removeTab(0)

        for tab in self.tabs:
            tab.recreate_buttons(self.keycode_filter)
            if tab.has_buttons():
                self.addTab(tab, tr("TabbedKeycodes", tab.label))
                if tab.label == prev_tab:
                    self.setCurrentIndex(self.count() - 1)
                    
        for miditab in self.tabs:
            tab.recreate_buttons(self.keycode_filter)
            if tab.has_buttons():
                self.addTab(tab, tr("TabbedKeycodes", tab.label))
                if tab.label == prev_tab:
                    self.setCurrentIndex(self.count() - 1)

    def on_keymap_override(self):
        for tab in self.tabs:
            tab.relabel_buttons()


class TabbedKeycodes(QWidget):

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.target = None
        self.is_tray = False

        self.layout = QVBoxLayout()

        self.all_keycodes = FilteredTabbedKeycodes()
        self.basic_keycodes = FilteredTabbedKeycodes(keycode_filter=keycode_filter_masked)
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.keycode_changed.connect(self.keycode_changed)
            opt.anykey.connect(self.anykey)
            self.layout.addWidget(opt)

        self.setLayout(self.layout)
        self.set_keycode_filter(keycode_filter_any)

    @classmethod
    def set_tray(cls, tray):
        cls.tray = tray

    @classmethod
    def open_tray(cls, target, keycode_filter=None):
        cls.tray.set_keycode_filter(keycode_filter)
        cls.tray.show()
        if cls.tray.target is not None and cls.tray.target != target:
            cls.tray.target.deselect()
        cls.tray.target = target

    @classmethod
    def close_tray(cls):
        if cls.tray.target is not None:
            cls.tray.target.deselect()
        cls.tray.target = None
        cls.tray.hide()

    def make_tray(self):
        self.is_tray = True
        TabbedKeycodes.set_tray(self)

        self.keycode_changed.connect(self.on_tray_keycode_changed)
        self.anykey.connect(self.on_tray_anykey)

    def on_tray_keycode_changed(self, kc):
        if self.target is not None:
            self.target.on_keycode_changed(kc)

    def on_tray_anykey(self):
        if self.target is not None:
            self.target.on_anykey()

    def recreate_keycode_buttons(self):
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.recreate_keycode_buttons()

    def set_keycode_filter(self, keycode_filter):
        if keycode_filter == keycode_filter_masked:
            self.all_keycodes.hide()
            self.basic_keycodes.show()
        else:
            self.all_keycodes.show()
            self.basic_keycodes.hide()
