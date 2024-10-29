# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTabWidget, QWidget, QScrollArea, QApplication, QVBoxLayout, QComboBox, QSizePolicy, QLabel, QGridLayout, QStyleOptionComboBox, QDialog, QLineEdit
from PyQt5.QtGui import QPalette, QPainter

from constants import KEYCODE_BTN_RATIO
from widgets.display_keyboard import DisplayKeyboard
from widgets.display_keyboard_defs import ansi_100, ansi_80, ansi_70, iso_100, iso_80, iso_70, mods, mods_narrow, midi_layout
from widgets.flowlayout import FlowLayout
from keycodes.keycodes import KEYCODES_BASIC, KEYCODES_ISO, KEYCODES_MACRO, KEYCODES_MACRO_BASE, KEYCODES_LAYERS, KEYCODES_QUANTUM, \
    KEYCODES_BOOT, KEYCODES_MODIFIERS, KEYCODES_CLEAR, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_COLOR, \
    KEYCODES_BACKLIGHT, KEYCODES_MEDIA, KEYCODES_SPECIAL, KEYCODES_SHIFTED, KEYCODES_USER, Keycode, KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_TG, KEYCODES_LAYERS_TT, KEYCODES_LAYERS_OSL, KEYCODES_LAYERS_TO, KEYCODES_LAYERS_LT, \
    KEYCODES_TAP_DANCE, KEYCODES_MIDI, KEYCODES_BASIC_NUMPAD, KEYCODES_BASIC_NAV, KEYCODES_ISO_KR, BASIC_KEYCODES, KEYCODES_MIDI_ADVANCED, KEYCODES_MIDI_SMARTCHORDBUTTONS, KEYCODES_VELOCITY_STEPSIZE, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD, \
    KEYCODES_MIDI_CC, KEYCODES_MIDI_BANK, KEYCODES_Program_Change, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_VELOCITY, KEYCODES_Program_Change_UPDOWN, KEYCODES_MIDI_BANK, KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC_FIXED, KEYCODES_OLED, \
    KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_UPDOWN, KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_INVERSION, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN, KEYCODES_MIDI_PEDAL
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
        
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QGridLayout, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtCore import pyqtSignal

class CenteredComboBox(QComboBox):
    def paintEvent(self, event):
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        painter = QPainter(self)
        self.style().drawComplexControl(self.style().CC_ComboBox, opt, painter, self)

        # Center the text horizontally
        text_rect = self.style().subControlRect(self.style().CC_ComboBox, opt, self.style().SC_ComboBoxEditField, self)
        painter.drawText(text_rect, Qt.AlignCenter, self.currentText())
        
    def wheelEvent(self, event):
        # Ignore the wheel event to prevent changing selection
        event.ignore()

class SmartChordTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, smartchord_keycodes_1, smartchord_keycodes_2, smartchord_keycodes_3, smartchord_keycodes_4, scales_modes_keycodes, smartchord_octave_1, smartchord_key, inversiondropdown, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.smartchord_keycodes_1 = smartchord_keycodes_1
        self.smartchord_keycodes_2 = smartchord_keycodes_2
        self.smartchord_keycodes_3 = smartchord_keycodes_3
        self.smartchord_keycodes_4 = smartchord_keycodes_4
        self.scales_modes_keycodes = scales_modes_keycodes
        self.smartchord_octave_1 = smartchord_octave_1
        self.smartchord_key = smartchord_key
        self.inversion_keycodes = inversion_keycodes
        self.inversion_dropdown = inversiondropdown
        

        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)

        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
                
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
             "MI_C_5", "MI_D_5", "MI_E_5", "MI_F_5", "MI_G_5", "MI_A_5", "MI_B_5"],
            
            ["KC_NO", "MI_ALLOFF", "MI_SUS", "MI_CHORD_99"]
        ]
        
        # 1. MIDI Layout
        self.add_midi_layout2(self.midi_layout2)

        # Create a horizontal layout for the Smart Chord dropdowns
        self.smartchord_dropdown_layout = QHBoxLayout()
        self.add_header_dropdown("3 Note Chords", self.smartchord_keycodes_1, self.smartchord_dropdown_layout)
        self.add_header_dropdown("4 Note Chords", self.smartchord_keycodes_2, self.smartchord_dropdown_layout)
        self.add_header_dropdown("5 Note Chords", self.smartchord_keycodes_3, self.smartchord_dropdown_layout)
        self.add_header_dropdown("Advanced Chords", self.smartchord_keycodes_4, self.smartchord_dropdown_layout)
        self.add_header_dropdown("Scales/Modes", self.scales_modes_keycodes, self.smartchord_dropdown_layout)
        self.main_layout.addLayout(self.smartchord_dropdown_layout)

        # Create a horizontal layout for the Octave, Key, and Program Change dropdowns
        self.additional_dropdown_layout = QHBoxLayout()
        self.add_smallheader_dropdown("Octave Selector", self.smartchord_octave_1, self.additional_dropdown_layout)
        self.add_smallheader_dropdown("Key Selector", self.smartchord_key, self.additional_dropdown_layout)
        self.add_smallheader_dropdown("Chord Inversion/Position", self.inversion_dropdown, self.additional_dropdown_layout)
        self.main_layout.addLayout(self.additional_dropdown_layout)

        # Layout for inversion buttons
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the inversion buttons
        self.recreate_buttons()

        # Spacer to push everything to the top
        self.main_layout.addStretch()
        
    def add_midi_layout2(self, layout):
        """Helper method to add staggered buttons based on MIDI layout."""
        midi_container = QWidget()
        midi_container_layout = QVBoxLayout()  # Use QVBoxLayout for rows
        midi_container.setLayout(midi_container_layout)

        # Create the MIDI buttons
        self.create_midi_buttons(layout, midi_container_layout)

        # Add MIDI container to the main layout
        self.main_layout.addWidget(midi_container)
        
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
            "MI_B": "B",
            "MI_ALLOFF": "All\nNotes\nOff", 
            "MI_SUS" : "Sustain\nPedal",
            "KC_NO" : " ",
            "MI_CHORD_99": "SmartChord"
        }

        for row_index, row in enumerate(layout):
            hbox = QHBoxLayout()  # New horizontal row layout
            hbox.setAlignment(Qt.AlignCenter)
            for col_index, item in enumerate(row):
                if isinstance(item, str):
                    readable_name = name_mapping.get(item, item)
                    button = SquareButton()
                    button.setText(readable_name)

                    button.setStyleSheet("background-color: rgba(190, 190, 190, 1); color: rgba(30, 30, 30, 1);")
                    
                    if "#" in readable_name:  # Sharp keys have # in their name
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        # Add an empty space before the black keys to stagger
                        
                    if "Pedal" in readable_name or "All" in readable_name or " " in readable_name or "Smart" in readable_name:
                        button.setStyleSheet("")
  
                    if readable_name in ["C#\nDb", "C#3\nDb3"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        
                    if readable_name in ["C#1\nDb1", "C#2\nDb2", "C#4\nDb4", "C#5\nDb5"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        hbox.addSpacing(60)                      
                        
                    if readable_name in ["F#\nGb", "F#1\nGb1", "F#2\nGb2", "F#3\nGb3", "F#4\nGb4", "F#5\nGb5"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        hbox.addSpacing(50)
                        
                    if readable_name in ["C1", "C2", "C4", "C5"]:
                        button.setStyleSheet("background-color: rgba(190, 190, 190, 1); color: rgba(30, 30, 30, 1);")
                        hbox.addSpacing(20)

                    

                    button.setFixedHeight(40)  # Set size as needed
                    if "Pedal" in readable_name or "All" in readable_name or "Smart" in readable_name:
                        button.setFixedWidth(80)  # Set fixed width of 80 for 'Pedal' or 'All' in readable_name
                    else:
                        button.setFixedWidth(40)  # Set fixed width of 40 for other buttons
                    button.clicked.connect(lambda _, text=item: self.keycode_changed.emit(text))
                    hbox.addWidget(button)  # Add button to horizontal layout

            container_layout.addLayout(hbox)  # Add row to vertical layout          

    def add_header_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
        #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"{header_text}")  # Placeholder item

        # Add the keycodes as options
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)

        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))

        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)
        
    def reset_dropdown(self, dropdown, header_text):
        """Reset the dropdown to show default text while storing the selected value."""
        selected_index = dropdown.currentIndex()

        if selected_index > 0:  # Ensure an actual selection was made
            selected_value = dropdown.itemData(selected_index)  # Get the selected keycode value
            # Process the selected value if necessary here
            # Example: print(f"Selected: {selected_value}")

        # Reset the visible text to the default
        dropdown.setCurrentIndex(0)
        
    def add_smallheader_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"{header_text}")  # Placeholder item

        # Add the keycodes as options
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)

        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))

        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)

    def recreate_buttons(self, keycode_filter=None):
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Populate inversion buttons
        row = 0
        col = 0
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode  # Make sure keycode attribute is set

                # Add button to the grid layout
                self.button_layout.addWidget(btn, row, col)

                # Move to the next column; if the limit is reached, reset to column 0 and increment the row
                col += 1
                if col >= 15:  # Adjust the number of columns as needed
                    col = 0
                    row += 1

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

from PyQt5.QtWidgets import (
    QScrollArea, QVBoxLayout, QGridLayout, QLabel, QMenu, QPushButton, QHBoxLayout, QWidget, QAction
)
from PyQt5.QtCore import pyqtSignal, Qt

class midiadvancedTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes, smartchord_program_change, smartchord_LSB, smartchord_MSB, smartchord_CC_toggle, CCfixed, CCup, CCdown, velocity_multiplier_options, cc_multiplier_options, channel_options, velocity_options, channel_oneshot, channel_hold):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.smartchord_program_change = smartchord_program_change
        self.smartchord_LSB = smartchord_LSB
        self.smartchord_MSB = smartchord_MSB
        self.smartchord_CC_toggle = smartchord_CC_toggle
        self.CCfixed = CCfixed
        self.CCup = CCup
        self.CCdown = CCdown
        self.velocity_multiplier_options = velocity_multiplier_options  # Dropdown options for Velocity Multiplier
        self.cc_multiplier_options = cc_multiplier_options  # Dropdown options for CC Multiplier
        self.channel_options = channel_options  # Dropdown options for Channel
        self.velocity_options = velocity_options  # Dropdown options for Velocity
        self.channel_oneshot = channel_oneshot  # Dropdown options for Channel
        self.channel_hold = channel_hold  # Dropdown options for Velocity

        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)

        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Add CC X and CC Y menu
        self.add_cc_x_y_menu()
        
        # Add Channel and Velocity dropdowns in the second row
        self.additional_dropdown_layout4 = QHBoxLayout()
        self.add_header_dropdown("Default MIDI Channel", self.channel_options, self.additional_dropdown_layout4)
        self.add_header_dropdown("Next Key MIDI Channel", self.channel_oneshot, self.additional_dropdown_layout4)
        self.add_header_dropdown("Hold for MIDI Channel", self.channel_hold, self.additional_dropdown_layout4)
        self.add_header_dropdown("Velocity", self.velocity_options, self.additional_dropdown_layout4)
        self.main_layout.addLayout(self.additional_dropdown_layout4)
        
        # Create a horizontal layout for the additional dropdowns (second row)
        self.additional_dropdown_layout2 = QHBoxLayout()
        self.add_header_dropdown("CC On/Off", self.smartchord_CC_toggle, self.additional_dropdown_layout2)
        self.add_header_dropdown("CC ▲", self.CCup, self.additional_dropdown_layout2)
        self.add_header_dropdown("CC ▼", self.CCdown, self.additional_dropdown_layout2)
        self.add_header_dropdown("Program Change", self.smartchord_program_change, self.additional_dropdown_layout2)
        self.add_header_dropdown("Bank LSB", self.smartchord_LSB, self.additional_dropdown_layout2)
        self.add_header_dropdown("Bank MSB", self.smartchord_MSB, self.additional_dropdown_layout2)
        self.main_layout.addLayout(self.additional_dropdown_layout2)

        # Add Channel and Velocity dropdowns in the second row
        self.additional_dropdown_layout3 = QHBoxLayout()
        self.add_header_dropdown("CC ▲▼ Multiplier", self.cc_multiplier_options, self.additional_dropdown_layout3)
        self.add_header_dropdown("Velocity ▲▼ Multiplier", self.velocity_multiplier_options, self.additional_dropdown_layout3) 
        self.main_layout.addLayout(self.additional_dropdown_layout3)

        self.inversion_label = QLabel("Advanced Midi Settings")
        self.inversion_label.setAlignment(Qt.AlignCenter)  # Center the label text
        self.main_layout.addWidget(self.inversion_label, alignment=Qt.AlignCenter)  # Add with center alignment

        # Layout for inversion buttons
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the inversion buttons
        self.recreate_buttons()

        # Spacer to push everything to the top
        self.main_layout.addStretch()


    def add_header_dropdown(self, label_text, items, layout):
        dropdown = QComboBox()
        dropdown.addItems(items)
        label = QLabel(label_text)
        layout.addWidget(label)
        layout.addWidget(dropdown)


    def add_cc_x_y_menu(self):
        """Add a button that opens a CC X -> CC Y submenu."""
        self.cc_layout = QVBoxLayout()

        # Create a button to represent the CC X -> CC Y dropdown
        self.cc_button = QPushButton("CC Value")
        self.cc_button.setFixedHeight(40)
        self.cc_button.setFixedWidth(500)
        self.cc_button.clicked.connect(self.open_cc_xy_dialog)

        # Add the button to the layout
        self.cc_layout.addWidget(self.cc_button, alignment=Qt.AlignCenter)

        # Add the layout to the main layout
        self.main_layout.addLayout(self.cc_layout)

    def open_cc_xy_dialog(self):
        """Open a dialog to input CC values."""
        dialog = QDialog(self)  # Create a local dialog instance
        dialog.setWindowTitle("Enter CC Value")
        dialog.setFixedHeight(170)  # Set fixed height for the dialog

        layout = QVBoxLayout(dialog)

        # Create a scroll area for CC X values
        cc_x_scroll_area = QScrollArea()
        cc_x_scroll_area.setWidgetResizable(True)

        # Create a widget for the scroll area content
        cc_x_content_widget = QWidget()
        cc_x_content_layout = QVBoxLayout(cc_x_content_widget)

        # Add a label and text box for CC X input
        cc_x_label = QLabel("CC(0-127):")
        self.cc_x_input = QLineEdit()
        self.cc_x_input.textChanged.connect(self.validate_cc_x_input)
        cc_x_content_layout.addWidget(cc_x_label)
        cc_x_content_layout.addWidget(self.cc_x_input)

        # Add a label and text box for CC Y input
        cc_y_label = QLabel("Value(0-127):")
        self.cc_y_input = QLineEdit()
        self.cc_y_input.textChanged.connect(self.validate_cc_y_input)
        cc_x_content_layout.addWidget(cc_y_label)
        cc_x_content_layout.addWidget(self.cc_y_input)

        cc_x_content_widget.setLayout(cc_x_content_layout)
        cc_x_scroll_area.setWidget(cc_x_content_widget)

        # Add the scroll area to the main layout of the dialog
        layout.addWidget(cc_x_scroll_area)
        dialog.setLayout(layout)

        # Optional: Add a button to confirm the selection
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(lambda: self.confirm_cc_values(dialog))  # Pass dialog instance
        layout.addWidget(confirm_button)

        dialog.exec_()

    def confirm_cc_values(self, dialog):
        """Handle the confirmation of CC values and close the dialog."""
        cc_x_value = self.cc_x_input.text()
        cc_y_value = self.cc_y_input.text()
        if cc_x_value and cc_y_value:
            # Emit the values or handle them as needed
            self.on_cc_selection(int(cc_x_value), int(cc_y_value))
            dialog.accept()  # Close the dialog
        
    def validate_cc_x_input(self, text):
        if text and (not text.isdigit() or not (0 <= int(text) <= 127)):
            # If the input is not a digit or is out of the range, clear the input
            self.cc_x_input.clear()
            
    def validate_cc_y_input(self, text):
        if text and (not text.isdigit() or not (0 <= int(text) <= 127)):
            # If the input is not a digit or is out of the range, clear the input
            self.cc_y_input.clear()


    def open_cc_y_submenu(self, selected_x):
        """Open a submenu dialog for selecting CC Y values based on selected CC X."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"CC X {selected_x} -> CC Y Selection")
        dialog.setFixedHeight(300)  # Set fixed height for the dialog

        layout = QVBoxLayout(dialog)

        # Create a scroll area for CC Y values
        cc_y_scroll_area = QScrollArea()
        cc_y_scroll_area.setWidgetResizable(True)

        # Create a widget for the scroll area content
        cc_y_content_widget = QWidget()
        cc_y_content_layout = QVBoxLayout(cc_y_content_widget)

        # Populate the CC Y buttons based on CCfixed
        for keycode in self.CCfixed:
            try:
                x_value, y_value = map(int, keycode.qmk_id.split('_')[2:])  # Extract x and y
                if x_value == selected_x:  # Only add CC Y if it matches the CC X value
                    button = QPushButton(f"CC Y {y_value}")
                    button.clicked.connect(lambda _, x=selected_x, y=y_value: self.on_cc_selection(x, y))
                    cc_y_content_layout.addWidget(button)
            except ValueError:
                continue  # Skip if the format is unexpected

        cc_y_content_widget.setLayout(cc_y_content_layout)
        cc_y_scroll_area.setWidget(cc_y_content_widget)

        # Add the scroll area to the main layout of the dialog
        layout.addWidget(cc_y_scroll_area)
        dialog.setLayout(layout)
        dialog.exec_()



    def on_cc_selection(self, x, y):
        """Handle CC X and CC Y selection."""
        print(f"Selected CC X: {x}, CC Y: {y}")
        # Emit a signal or perform any additional action here
        self.keycode_changed.emit(f"MI_CC_{x}_{y}")

    def add_header_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
        #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"{header_text}")  # Placeholder item

        # Add the keycodes as options
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)

        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)
        
    def update_header_label(self, dropdown, header_label):
        """Update the header label based on the selected dropdown item."""
        selected_item = dropdown.currentText()
        header_label.setText(selected_item)
        
    def reset_dropdown(self, dropdown, header_text):
        """Reset the dropdown to show default text while storing the selected value."""
        selected_index = dropdown.currentIndex()

        if selected_index > 0:  # Ensure an actual selection was made
            selected_value = dropdown.itemData(selected_index)  # Get the selected keycode value
            # Process the selected value if necessary here
            # Example: print(f"Selected: {selected_value}")

        # Reset the visible text to the default
        dropdown.setCurrentIndex(0)
        
    def recreate_buttons(self, keycode_filter=None):
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Populate inversion buttons
        row = 0
        col = 0
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode  # Make sure keycode attribute is set

                # Add button to the grid layout
                self.button_layout.addWidget(btn, row, col)

                # Move to the next column; if the limit is reached, reset to column 0 and increment the row
                col += 1
                if col >= 12:  # Adjust the number of columns as needed
                    col = 0
                    row += 1

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


class LayerTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes, smartchord_CC_toggle, smartchord_program_change, smartchord_LSB, smartchord_MSB, smartchord_LSB2, smartchord_CC_toggle2):
        super().__init__(parent)
        self.label = label     
        self.inversion_keycodes = inversion_keycodes
        self.smartchord_program_change = smartchord_program_change
        self.smartchord_LSB = smartchord_LSB
        self.smartchord_MSB = smartchord_MSB
        self.smartchord_CC_toggle = smartchord_CC_toggle
        self.smartchord_LSB2 = smartchord_LSB2
        self.smartchord_CC_toggle2 = smartchord_CC_toggle2
        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        
        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Inversions Header
        #self.inversion_label = QLabel("Function Buttons")
        #self.inversion_label.setAlignment(Qt.AlignCenter)  # Center the label text
        #self.main_layout.addWidget(self.inversion_label, alignment=Qt.AlignCenter)  # Add to layout with center alignment


        # Layout for inversion buttons
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the inversion buttons
        self.recreate_buttons()

        # Create a horizontal layout for the additional dropdowns
        self.additional_dropdown_layout2 = QHBoxLayout()
        self.add_header_dropdown("Active/Default Layer", self.smartchord_CC_toggle, self.additional_dropdown_layout2)
        self.add_header_dropdown("Hold Layer", self.smartchord_program_change, self.additional_dropdown_layout2)
        self.add_header_dropdown("Toggle Layer", self.smartchord_LSB, self.additional_dropdown_layout2)
        self.add_header_dropdown("Tap-Toggle Layer", self.smartchord_MSB, self.additional_dropdown_layout2)
        self.add_header_dropdown("One Shot Layer", self.smartchord_LSB2, self.additional_dropdown_layout2)
        self.add_header_dropdown("Double Layer", self.smartchord_CC_toggle2, self.additional_dropdown_layout2)
        self.main_layout.addLayout(self.additional_dropdown_layout2)

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def add_header_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
        #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"{header_text}")  # Placeholder item

        for keycode in keycodes:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)  # Get the description
            dropdown.addItem(label, keycode.qmk_id)

            # Set the tooltip for the item
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)


        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)
        
    def reset_dropdown(self, dropdown, header_text):
        """Reset the dropdown to show default text while storing the selected value."""
        selected_index = dropdown.currentIndex()

        if selected_index > 0:  # Ensure an actual selection was made
            selected_value = dropdown.itemData(selected_index)  # Get the selected keycode value
            # Process the selected value if necessary here
            # Example: print(f"Selected: {selected_value}")

        # Reset the visible text to the default
        dropdown.setCurrentIndex(0)
        
    def add_smallheader_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
            #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown
        dropdown.setFixedWidth(150)  # Set width of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"Select {header_text}")  # Placeholder item

        # Add the keycodes as options
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)

        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)

    def recreate_buttons(self, keycode_filter=None):
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Populate inversion buttons
        row = 0
        col = 0
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(40)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode  # Make sure keycode attribute is set

                # Add button to the grid layout
                self.button_layout.addWidget(btn, row, col)

                # Move to the next column; if the limit is reached, reset to column 0 and increment the row
                col += 1
                if col >= 15:  # Adjust the number of columns as needed
                    col = 0
                    row += 1

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
        
class LightingTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes, smartchord_LSB, smartchord_MSB):
        super().__init__(parent)
        self.label = label     
        self.inversion_keycodes = inversion_keycodes
        self.smartchord_LSB = smartchord_LSB
        self.smartchord_MSB = smartchord_MSB

        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        
        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Inversions Header
        #self.inversion_label = QLabel("Function Buttons")
        #self.inversion_label.setAlignment(Qt.AlignCenter)  # Center the label text
        #self.main_layout.addWidget(self.inversion_label, alignment=Qt.AlignCenter)  # Add to layout with center alignment


        # Layout for inversion buttons
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the inversion buttons
        self.recreate_buttons()

        # Create a horizontal layout for the additional dropdowns
        self.additional_dropdown_layout2 = QHBoxLayout()
        self.add_header_dropdown("RGB Mode", self.smartchord_LSB, self.additional_dropdown_layout2)
        self.add_header_dropdown("RGB Color", self.smartchord_MSB, self.additional_dropdown_layout2)
        self.main_layout.addLayout(self.additional_dropdown_layout2)

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def add_header_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
        #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"{header_text}")  # Placeholder item

        for keycode in keycodes:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)  # Get the description
            dropdown.addItem(label, keycode.qmk_id)

            # Set the tooltip for the item
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)


        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)
        
    def reset_dropdown(self, dropdown, header_text):
        """Reset the dropdown to show default text while storing the selected value."""
        selected_index = dropdown.currentIndex()

        if selected_index > 0:  # Ensure an actual selection was made
            selected_value = dropdown.itemData(selected_index)  # Get the selected keycode value
            # Process the selected value if necessary here
            # Example: print(f"Selected: {selected_value}")

        # Reset the visible text to the default
        dropdown.setCurrentIndex(0)
        
    def add_smallheader_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
            #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown
        dropdown.setFixedWidth(150)  # Set width of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"Select {header_text}")  # Placeholder item

        # Add the keycodes as options
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)

        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)

    def recreate_buttons(self, keycode_filter=None):
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Populate inversion buttons
        row = 0
        col = 0
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(40)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode  # Make sure keycode attribute is set

                # Add button to the grid layout
                self.button_layout.addWidget(btn, row, col)

                # Move to the next column; if the limit is reached, reset to column 0 and increment the row
                col += 1
                if col >= 15:  # Adjust the number of columns as needed
                    col = 0
                    row += 1

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

class MacroTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes, smartchord_LSB, smartchord_MSB):
        super().__init__(parent)
        self.label = label     
        self.inversion_keycodes = inversion_keycodes
        self.smartchord_LSB = smartchord_LSB
        self.smartchord_MSB = smartchord_MSB

        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        
        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Inversions Header
        #self.inversion_label = QLabel("Function Buttons")
        #self.inversion_label.setAlignment(Qt.AlignCenter)  # Center the label text
        #self.main_layout.addWidget(self.inversion_label, alignment=Qt.AlignCenter)  # Add to layout with center alignment


        # Layout for inversion buttons
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the inversion buttons
        self.recreate_buttons()

        # Create a horizontal layout for the additional dropdowns
        self.additional_dropdown_layout2 = QHBoxLayout()
        self.add_header_dropdown("Macro Selection", self.smartchord_LSB, self.additional_dropdown_layout2)
        self.add_header_dropdown("Tapdance Selection", self.smartchord_MSB, self.additional_dropdown_layout2)
        self.main_layout.addLayout(self.additional_dropdown_layout2)

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def add_header_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
        #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"{header_text}")  # Placeholder item

        for keycode in keycodes:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)  # Get the description
            dropdown.addItem(label, keycode.qmk_id)

            # Set the tooltip for the item
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)


        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)
        
    def reset_dropdown(self, dropdown, header_text):
        """Reset the dropdown to show default text while storing the selected value."""
        selected_index = dropdown.currentIndex()

        if selected_index > 0:  # Ensure an actual selection was made
            selected_value = dropdown.itemData(selected_index)  # Get the selected keycode value
            # Process the selected value if necessary here
            # Example: print(f"Selected: {selected_value}")

        # Reset the visible text to the default
        dropdown.setCurrentIndex(0)
        
    def add_smallheader_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
            #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)  # Set height of dropdown
        dropdown.setFixedWidth(150)  # Set width of dropdown

        # Add a placeholder item as the first item
        dropdown.addItem(f"Select {header_text}")  # Placeholder item

        # Add the keycodes as options
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)

        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box (header + dropdown) to the provided layout
        layout.addLayout(vbox)

    def recreate_buttons(self, keycode_filter=None):
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Populate inversion buttons
        row = 0
        col = 0
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(40)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode  # Make sure keycode attribute is set

                # Add button to the grid layout
                self.button_layout.addWidget(btn, row, col)

                # Move to the next column; if the limit is reached, reset to column 0 and increment the row
                col += 1
                if col >= 15:  # Adjust the number of columns as needed
                    col = 0
                    row += 1

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



class midiTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.scroll_content = QWidget()

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
             "MI_C_5", "MI_D_5", "MI_E_5", "MI_F_5", "MI_G_5", "MI_A_5", "MI_B_5"],
            
            ["KC_NO", "MI_ALLOFF", "MI_SUS", "MI_CHORD_99"]
        ]

        # Main layout for the scroll area
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.main_layout = QVBoxLayout(self.scroll_content)

        # 1. MIDI Layout
        self.add_midi_layout2(self.midi_layout2)
        
        # 2. Dropdowns and Headers (Horizontal Layout)
        self.dropdown_layout = QVBoxLayout()
        self.main_layout.addLayout(self.dropdown_layout)

        # Create a horizontal layout for the dropdowns
        self.horizontal_dropdown_layout = QHBoxLayout()
        self.dropdown_layout.addLayout(self.horizontal_dropdown_layout)
        # 3. Inversions Header
        self.inversion_label = QLabel(" ")
        self.main_layout.addWidget(self.inversion_label)

        # Layout for buttons (Inversions) using QGridLayout
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the inversion buttons
        self.recreate_buttons()

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def add_header_dropdown(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown above it."""
        # Create a vertical layout for the header and dropdown
        header_dropdown_layout = QVBoxLayout()
    
        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
        #header_dropdown_layout.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedWidth(300)
        dropdown.setFixedHeight(40)
        
         # Add a placeholder item as the first item
        dropdown.addItem(f"Select {header_text}")  # Placeholder item
        dropdown.model().item(0).setEnabled(False)
        
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        header_dropdown_layout.addWidget(dropdown)

        # Add the vertical layout to the main horizontal layout
        layout.addLayout(header_dropdown_layout)
        
    def reset_dropdown(self, dropdown, header_text):
        """Reset the dropdown to show default text while storing the selected value."""
        selected_index = dropdown.currentIndex()

        if selected_index > 0:  # Ensure an actual selection was made
            selected_value = dropdown.itemData(selected_index)  # Get the selected keycode value
            # Process the selected value if necessary here
            # Example: print(f"Selected: {selected_value}")

        # Reset the visible text to the default
        dropdown.setCurrentIndex(0)


    def add_midi_layout2(self, layout):
        """Helper method to add staggered buttons based on MIDI layout."""
        midi_container = QWidget()
        midi_container_layout = QVBoxLayout()  # Use QVBoxLayout for rows
        midi_container.setLayout(midi_container_layout)

        # Create the MIDI buttons
        self.create_midi_buttons(layout, midi_container_layout)

        # Add MIDI container to the main layout
        self.main_layout.addWidget(midi_container)

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
            "MI_B": "B",
            "MI_ALLOFF": "All\nNotes\nOff", 
            "MI_SUS" : "Sustain\nPedal",
            "KC_NO" : " ",
            "MI_CHORD_99": "SmartChord"
        }

        for row_index, row in enumerate(layout):
            hbox = QHBoxLayout()  # New horizontal row layout
            hbox.setAlignment(Qt.AlignCenter)
            for col_index, item in enumerate(row):
                if isinstance(item, str):
                    readable_name = name_mapping.get(item, item)
                    button = SquareButton()
                    button.setText(readable_name)

                    button.setStyleSheet("background-color: rgba(190, 190, 190, 1); color: rgba(30, 30, 30, 1);")
                    
                    if "#" in readable_name:  # Sharp keys have # in their name
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        # Add an empty space before the black keys to stagger
                        
                    if "Pedal" in readable_name or "All" in readable_name or " " in readable_name or "Smart" in readable_name:
                        button.setStyleSheet("")
  
                    if readable_name in ["C#\nDb", "C#3\nDb3"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        
                    if readable_name in ["C#1\nDb1", "C#2\nDb2", "C#4\nDb4", "C#5\nDb5"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        hbox.addSpacing(60)                      
                        
                    if readable_name in ["F#\nGb", "F#1\nGb1", "F#2\nGb2", "F#3\nGb3", "F#4\nGb4", "F#5\nGb5"]:
                        button.setStyleSheet("background-color: rgba(30, 30, 30, 1); color: rgba(190, 190, 190, 1);")
                        hbox.addSpacing(50)
                        
                    if readable_name in ["C1", "C2", "C4", "C5"]:
                        button.setStyleSheet("background-color: rgba(190, 190, 190, 1); color: rgba(30, 30, 30, 1);")
                        hbox.addSpacing(20)

                    

                    button.setFixedHeight(40)  # Set size as needed
                    if "Pedal" in readable_name or "All" in readable_name or "Smart" in readable_name:
                        button.setFixedWidth(80)  # Set fixed width of 80 for 'Pedal' or 'All' in readable_name
                    else:
                        button.setFixedWidth(40)  # Set fixed width of 40 for other buttons
                    button.clicked.connect(lambda _, text=item: self.keycode_changed.emit(text))
                    hbox.addWidget(button)  # Add button to horizontal layout

            container_layout.addLayout(hbox)  # Add row to vertical layout            

    def recreate_buttons(self, keycode_filter=None):
        """Recreate inversion buttons and add MIDI_CC dropdowns."""
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        row = 0
        col = 0
        max_columns = 5  # Maximum number of columns before dropdown

        # Add inversion buttons
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                self.button_layout.addWidget(btn, row, col)

                col += 1
                if col >= max_columns:
                    col = 0
                    row += 1

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
            SimpleTab(self, "App, Media and Mouse", KEYCODES_MEDIA),            
            SimpleTab(self, "Advanced", KEYCODES_BOOT + KEYCODES_MODIFIERS + KEYCODES_QUANTUM),
            LightingTab(self, "Lighting", KEYCODES_BACKLIGHT, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_COLOR),            
            LayerTab(self, "Layers", KEYCODES_LAYERS, KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_TG, KEYCODES_LAYERS_TT, KEYCODES_LAYERS_OSL, KEYCODES_LAYERS_TO),
            midiTab(self, "Instrument", KEYCODES_MIDI_UPDOWN),   # Updated to SmartChordTab
            SmartChordTab(self, "SmartChord", KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_INVERSION, KEYCODES_MIDI_SMARTCHORDBUTTONS),
            midiadvancedTab(self, "MIDI",  KEYCODES_MIDI_ADVANCED, KEYCODES_Program_Change, KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC, KEYCODES_MIDI_CC_FIXED, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN, KEYCODES_VELOCITY_STEPSIZE, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_VELOCITY, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD),
            MacroTab(self, "Macro", KEYCODES_MACRO_BASE, KEYCODES_MACRO, KEYCODES_TAP_DANCE),
            SimpleTab(self, " ", KEYCODES_CLEAR),     
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
                    
        for midiadvancedTab in self.tabs:
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
