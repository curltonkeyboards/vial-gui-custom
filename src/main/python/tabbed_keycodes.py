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
    KEYCODES_TAP_DANCE, KEYCODES_MIDI, KEYCODES_MIDI_SPLIT, KEYCODES_MIDI_SPLIT2, KEYCODES_MIDI_CHANNEL_KEYSPLIT, KEYCODES_KEYSPLIT_BUTTONS, KEYCODES_MIDI_CHANNEL_KEYSPLIT2, KEYCODES_BASIC_NUMPAD, KEYCODES_BASIC_NAV, KEYCODES_ISO_KR, BASIC_KEYCODES, \
    KEYCODES_MIDI_CC, KEYCODES_MIDI_BANK, KEYCODES_Program_Change, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_VELOCITY, KEYCODES_Program_Change_UPDOWN, KEYCODES_MIDI_BANK, KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC_FIXED, KEYCODES_OLED, \
    KEYCODES_MIDI_OCTAVE2, KEYCODES_MIDI_OCTAVE3, KEYCODES_MIDI_KEY2, KEYCODES_MIDI_KEY3, KEYCODES_MIDI_VELOCITY2, KEYCODES_MIDI_VELOCITY3, KEYCODES_MIDI_ADVANCED, KEYCODES_MIDI_SMARTCHORDBUTTONS, KEYCODES_VELOCITY_STEPSIZE, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD, \
    KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_UPDOWN, KEYCODES_MIDI_CHORD_0, KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_INVERSION, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN, KEYCODES_MIDI_PEDAL
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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
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

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
    QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QScrollArea, QAction
)
from PyQt5.QtCore import Qt, pyqtSignal

class SmartChordTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, smartchord_keycodes_0, smartchord_keycodes_1, smartchord_keycodes_2, smartchord_keycodes_3, smartchord_keycodes_4, scales_modes_keycodes, inversiondropdown, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.smartchord_keycodes_0 = smartchord_keycodes_0
        self.smartchord_keycodes_1 = smartchord_keycodes_1
        self.smartchord_keycodes_2 = smartchord_keycodes_2
        self.smartchord_keycodes_3 = smartchord_keycodes_3
        self.smartchord_keycodes_4 = smartchord_keycodes_4
        self.scales_modes_keycodes = scales_modes_keycodes
        self.inversion_keycodes = inversion_keycodes
        self.inversion_dropdown = inversiondropdown
        
        # Store all tree widgets for managing selections
        self.trees = []

        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)

        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Create a horizontal layout to hold the QTreeWidgets
        self.tree_layout = QHBoxLayout()
        self.tree_layout.setSpacing(1)
        self.populate_tree()

        # Add the QTreeWidget layout to the main layout
        self.main_layout.addLayout(self.tree_layout)

        # Layout for inversion buttons
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the inversion buttons
        self.recreate_buttons()

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def populate_tree(self):
        """Populate the QTreeWidget with categories and keycodes."""
        # Create the QTreeWidgetItems for each category
        self.create_keycode_tree(self.smartchord_keycodes_0, "Intervals")
        self.create_keycode_tree(self.smartchord_keycodes_1, "3 Note Chords")
        self.create_keycode_tree(self.smartchord_keycodes_2, "4 Note Chords")
        self.create_keycode_tree(self.smartchord_keycodes_3, "5 Note Chords")
        self.create_keycode_tree(self.smartchord_keycodes_4, "Advanced Chords")
        self.create_keycode_tree(self.scales_modes_keycodes, "Scales/Modes")
        self.create_keycode_tree(self.inversion_dropdown, "Inversions")
        


    def create_keycode_tree(self, keycodes, title):
        """Create a QTreeWidget and add keycodes under it."""
        tree = QTreeWidget()
        tree.setHeaderLabel(title)
        self.add_keycode_group(tree, title, keycodes)
        tree.setFixedHeight(300)
        tree.setStyleSheet("border: 2px;")
        tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set selection mode to single selection
        tree.setSelectionMode(QTreeWidget.SingleSelection)
        
        # Connect itemClicked signal to on_item_selected
        tree.itemClicked.connect(self.on_item_selected)
        
        # Add tree to our list of trees
        self.trees.append(tree)

        # Add the QTreeWidget instance to the horizontal layout
        self.tree_layout.addWidget(tree)

    def add_keycode_group(self, tree, title, keycodes):
        """Helper function to add keycodes to a QTreeWidget."""
        for keycode in keycodes:
            label = Keycode.label(keycode.qmk_id).replace("\n", " ")  # Replace \n with space
            keycode_item = QTreeWidgetItem(tree, [label])
            keycode_item.setData(0, Qt.UserRole, keycode.qmk_id)  # Store qmk_id for easy access

            # Force text to be on one line and left-aligned
            keycode_item.setTextAlignment(0, Qt.AlignLeft)
            keycode_item.setText(0, label)  # Set the label again to ensure no wrapping

    def on_item_selected(self, clicked_item, column):
        """Handle tree item selection and clear other trees' selections."""
        # Get the tree that was clicked
        clicked_tree = clicked_item.treeWidget()
        
        # Block signals temporarily to prevent recursion
        for tree in self.trees:
            tree.blockSignals(True)
            
        try:
            # Clear selection in all other trees
            for tree in self.trees:
                if tree != clicked_tree:
                    tree.clearSelection()
                    tree.setCurrentItem(None)
            
            # Ensure the clicked item is selected
            clicked_item.setSelected(True)
            
            # Get the data from the clicked item
            qmk_id = clicked_item.data(0, Qt.UserRole)
            if qmk_id:
                self.keycode_changed.emit(qmk_id)
                
        finally:
            # Restore signals
            for tree in self.trees:
                tree.blockSignals(False)

                
    def add_keycode_group(self, tree, title, keycodes):
        """Helper function to add keycodes to a QTreeWidget."""
        for keycode in keycodes:
            label = Keycode.label(keycode.qmk_id).replace("\n", " ")  # Replace \n with space
            keycode_item = QTreeWidgetItem(tree, [label])
            keycode_item.setData(0, Qt.UserRole, keycode.qmk_id)  # Store qmk_id for easy access

            # Force text to be on one line and left-aligned
            keycode_item.setTextAlignment(0, Qt.AlignLeft)
            keycode_item.setText(0, label)  # Set the label again to ensure no wrapping
            

    def recreate_buttons(self, keycode_filter=None):
        """Recreates the buttons for the inversion keycodes."""
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        row = 0
        col = 0
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                self.button_layout.addWidget(btn, row, col)
                col += 1
                if col >= 15:
                    col = 0
                    row += 1

    def on_selection_change(self, index):
        selected_qmk_id = self.sender().itemData(index)
        if selected_qmk_id:
            self.keycode_changed.emit(selected_qmk_id)

    def relabel_buttons(self):
        """Relabel buttons based on keycodes."""
        for i in range(self.button_layout.count()):
            widget = self.button_layout.itemAt(i).widget()
            if isinstance(widget, SquareButton):
                keycode = widget.keycode
                if keycode:
                    widget.setText(Keycode.label(keycode.qmk_id))

    def has_buttons(self):
        """Check if buttons exist in the layout."""
        return self.button_layout.count() > 0
       



from PyQt5.QtWidgets import (
    QScrollArea, QVBoxLayout, QGridLayout, QLabel, QMenu, QPushButton, QHBoxLayout, QWidget, QDialog, QLineEdit, QComboBox
)
from PyQt5.QtCore import pyqtSignal, Qt

class midiadvancedTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes, smartchord_program_change, smartchord_LSB, smartchord_MSB, smartchord_CC_toggle, CCfixed, CCup, CCdown, velocity_multiplier_options, cc_multiplier_options, channel_options, velocity_options, channel_oneshot, channel_hold, smartchord_octave_1, smartchord_key, ksvelocity2, ksvelocity3, kskey2, kskey3, ksoctave2, ksoctave3, kschannel2, kschannel3):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.smartchord_program_change = smartchord_program_change
        self.smartchord_LSB = smartchord_LSB
        self.smartchord_MSB = smartchord_MSB
        self.smartchord_CC_toggle = smartchord_CC_toggle
        self.smartchord_octave_1 = smartchord_octave_1
        self.smartchord_key = smartchord_key
        self.CCfixed = CCfixed
        self.CCup = CCup
        self.CCdown = CCdown
        self.velocity_multiplier_options = velocity_multiplier_options
        self.cc_multiplier_options = cc_multiplier_options
        self.channel_options = channel_options
        self.velocity_options = velocity_options
        self.channel_oneshot = channel_oneshot
        self.channel_hold = channel_hold
        self.ksvelocity2 = ksvelocity2
        self.ksvelocity3 = ksvelocity3
        self.kskey2 = kskey2
        self.kskey3 = kskey3
        self.ksoctave2 = ksoctave2 
        self.ksoctave3 = ksoctave3
        self.kschannel2 = kschannel2 
        self.kschannel3 = kschannel3
        
        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)

        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Add CC X and CC Y menu
        

        # Add Channel and Velocity dropdowns in the second row
        
        self.inversion4_label = QLabel("MIDI Channel Options")
        self.inversion4_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.inversion4_label, alignment=Qt.AlignCenter)
        
        self.additional_dropdown_layout4 = QHBoxLayout()
        self.add_header_dropdown("MIDI Channel", self.channel_options, self.additional_dropdown_layout4)
        self.add_header_dropdown("Temporary MIDI Channel", self.channel_oneshot, self.additional_dropdown_layout4)
        self.add_header_dropdown("Hold MIDI Channel", self.channel_hold, self.additional_dropdown_layout4)
        self.main_layout.addLayout(self.additional_dropdown_layout4)
        
                
        self.inversion2_label = QLabel("Control Changes (CC) and Velocity")
        self.inversion2_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.inversion2_label, alignment=Qt.AlignCenter)
        
        # Replace dropdowns with individual buttons in the modified layout
        self.additional_button_layout2 = QHBoxLayout()
        self.add_value_button("Set Velocity", self.velocity_options, self.additional_button_layout2)
        self.add_cc_x_y_menu(self.additional_button_layout2)
        self.add_value_button("CC On/Off", self.smartchord_CC_toggle, self.additional_button_layout2)
        self.add_value_button("CC Up", self.CCup, self.additional_button_layout2)
        self.add_value_button("CC Down", self.CCdown, self.additional_button_layout2)
        self.add_value_button("Program Change", self.smartchord_program_change, self.additional_button_layout2)
        self.add_value_button("Bank LSB", self.smartchord_LSB, self.additional_button_layout2)
        self.add_value_button("Bank MSB", self.smartchord_MSB, self.additional_button_layout2)
        self.main_layout.addLayout(self.additional_button_layout2)
        
                
        self.inversion3_label = QLabel("Up/Down Increments / Advanced Transposition settings")
        self.inversion3_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.inversion3_label, alignment=Qt.AlignCenter)

        # Add Channel and Velocity dropdowns in the third row
        self.additional_dropdown_layout3 = QHBoxLayout()
        self.add_header_dropdown("CC Up/Down Increment", self.cc_multiplier_options, self.additional_dropdown_layout3)
        self.add_header_dropdown("Velocity Up/Down Increment", self.velocity_multiplier_options, self.additional_dropdown_layout3)
        self.add_header_dropdown("Octave Selector", self.smartchord_octave_1, self.additional_dropdown_layout3)
        self.add_header_dropdown("Key Selector", self.smartchord_key, self.additional_dropdown_layout3)        
        self.main_layout.addLayout(self.additional_dropdown_layout3)
        
        self.inversion6_label = QLabel("KeySplit/Triplesplit")
        self.inversion6_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.inversion6_label, alignment=Qt.AlignCenter)
        
        # Replace dropdowns with individual buttons in the modified layout
        self.keysplit_layout6 = QHBoxLayout()
        self.add_value_button("KS Velocity", self.ksvelocity2, self.keysplit_layout6)
        self.add_header_dropdown("KS Octave", self.ksoctave2, self.keysplit_layout6)
        self.add_header_dropdown("KS Key", self.kskey2, self.keysplit_layout6)  
        self.add_header_dropdown("KS Channel", self.kschannel2, self.keysplit_layout6)
        self.add_value_button("TS Velocity", self.ksvelocity3, self.keysplit_layout6)
        self.add_header_dropdown("TS Octave", self.ksoctave3, self.keysplit_layout6)
        self.add_header_dropdown("TS Key", self.kskey3, self.keysplit_layout6)  
        self.add_header_dropdown("TS Channel", self.kschannel3, self.keysplit_layout6)
        
        self.main_layout.addLayout(self.keysplit_layout6)

        self.inversion_label = QLabel("Advanced Midi Settings")
        self.inversion_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.inversion_label, alignment=Qt.AlignCenter)

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

    def add_value_button(self, label_text, keycode_set, layout):
        """Create a button that opens a dialog to input a value for the corresponding keycode."""
        button = QPushButton(label_text)
        button.setFixedHeight(40)
        button.clicked.connect(lambda: self.open_value_dialog(label_text, keycode_set))
        layout.addWidget(button)

    def open_value_dialog(self, label, keycode_set):
        """Open a dialog to input a value between 0 and 127 and set the keycode accordingly."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Set Value for {label}")
        dialog.setFixedSize(300, 150)

        layout = QVBoxLayout(dialog)
        label_widget = QLabel(f"Enter value for {label} (0-127):")
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Enter a number between 0 and 127")
        self.value_input.textChanged.connect(self.validate_value_input)

        layout.addWidget(label_widget)
        layout.addWidget(self.value_input)

        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(lambda: self.confirm_value(dialog, label, keycode_set))
        layout.addWidget(confirm_button)

        dialog.exec_()

    def confirm_value(self, dialog, label, keycode_set):
        """Confirm the value input and emit the corresponding keycode."""
        value = self.value_input.text()
        if value.isdigit() and 0 <= int(value) <= 127:
            keycode_map = {
                "CC On/Off": f"MI_CC_{value}_TOG",
                "CC Up": f"MI_CC_{value}_UP",
                "CC Down": f"MI_CC_{value}_DWN",
                "Program Change": f"MI_PROG_{value}",
                "Bank LSB": f"MI_BANK_LSB_{value}",
                "Bank MSB": f"MI_BANK_MSB_{value}",
                "Set Velocity": f"MI_VELOCITY_{value}",
                "KS Velocity": f"MI_VELOCITY2_{value}",
                "TS Velocity": f"MI_VELOCITY3_{value}"
            }
        
            # Construct the keycode using the label as a key
            if label in keycode_map:
                selected_keycode = keycode_map[label]
                self.keycode_changed.emit(selected_keycode)
                dialog.accept()

    def validate_value_input(self, text):
        if text and (not text.isdigit() or not (0 <= int(text) <= 127)):
            self.value_input.clear()


    def add_cc_x_y_menu(self, layout):
        button = QPushButton("CC Value")
        button.setFixedHeight(40)
        button.clicked.connect(self.open_cc_xy_dialog)
        layout.addWidget(button)

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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

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

class KeySplitTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.scroll_content = QWidget()

        # Define MIDI layout
        self.midi_layout2 = [
            ["MI_SPLIT_Cs", "MI_SPLIT_Ds", "MI_SPLIT_Fs", "MI_SPLIT_Gs", "MI_SPLIT_As",
             "MI_SPLIT_Cs_1", "MI_SPLIT_Ds_1", "MI_SPLIT_Fs_1", "MI_SPLIT_Gs_1", "MI_SPLIT_As_1",
             "MI_SPLIT_Cs_2", "MI_SPLIT_Ds_2", "MI_SPLIT_Fs_2", "MI_SPLIT_Gs_2", "MI_SPLIT_As_2"],

            ["MI_SPLIT_C", "MI_SPLIT_D", "MI_SPLIT_E", "MI_SPLIT_F", "MI_SPLIT_G", "MI_SPLIT_A", "MI_SPLIT_B",
             "MI_SPLIT_C_1", "MI_SPLIT_D_1", "MI_SPLIT_E_1", "MI_SPLIT_F_1", "MI_SPLIT_G_1", "MI_SPLIT_A_1", "MI_SPLIT_B_1",
             "MI_SPLIT_C_2", "MI_SPLIT_D_2", "MI_SPLIT_E_2", "MI_SPLIT_F_2", "MI_SPLIT_G_2", "MI_SPLIT_A_2", "MI_SPLIT_B_2"],

            ["MI_SPLIT_Cs_3", "MI_SPLIT_Ds_3", "MI_SPLIT_Fs_3", "MI_SPLIT_Gs_3", "MI_SPLIT_As_3",
             "MI_SPLIT_Cs_4", "MI_SPLIT_Ds_4", "MI_SPLIT_Fs_4", "MI_SPLIT_Gs_4", "MI_SPLIT_As_4",
             "MI_SPLIT_Cs_5", "MI_SPLIT_Ds_5", "MI_SPLIT_Fs_5", "MI_SPLIT_Gs_5", "MI_SPLIT_As_5"],

            ["MI_SPLIT_C_3", "MI_SPLIT_D_3", "MI_SPLIT_E_3", "MI_SPLIT_F_3", "MI_SPLIT_G_3", "MI_SPLIT_A_3", "MI_SPLIT_B_3",
             "MI_SPLIT_C_4", "MI_SPLIT_D_4", "MI_SPLIT_E_4", "MI_SPLIT_F_4", "MI_SPLIT_G_4", "MI_SPLIT_A_4", "MI_SPLIT_B_4",
             "MI_SPLIT_C_5", "MI_SPLIT_D_5", "MI_SPLIT_E_5", "MI_SPLIT_F_5", "MI_SPLIT_G_5", "MI_SPLIT_A_5", "MI_SPLIT_B_5"], 
             
            ["KS_CHAN_DOWN", "KS_CHAN_UP", "MI_VELOCITY2_DOWN", "MI_VELOCITY2_UP", "MI_TRANSPOSE2_DOWN", "MI_TRANSPOSE2_UP", "MI_OCTAVE2_DOWN", "MI_OCTAVE2_UP"]
        ]
        
        self.midi_layout3 = [
            ["MI_SPLIT2_Cs", "MI_SPLIT2_Ds", "MI_SPLIT2_Fs", "MI_SPLIT2_Gs", "MI_SPLIT2_As",
             "MI_SPLIT2_Cs_1", "MI_SPLIT2_Ds_1", "MI_SPLIT2_Fs_1", "MI_SPLIT2_Gs_1", "MI_SPLIT2_As_1",
             "MI_SPLIT2_Cs_2", "MI_SPLIT2_Ds_2", "MI_SPLIT2_Fs_2", "MI_SPLIT2_Gs_2", "MI_SPLIT2_As_2"],

            ["MI_SPLIT2_C", "MI_SPLIT2_D", "MI_SPLIT2_E", "MI_SPLIT2_F", "MI_SPLIT2_G", "MI_SPLIT2_A", "MI_SPLIT2_B",
             "MI_SPLIT2_C_1", "MI_SPLIT2_D_1", "MI_SPLIT2_E_1", "MI_SPLIT2_F_1", "MI_SPLIT2_G_1", "MI_SPLIT2_A_1", "MI_SPLIT2_B_1",
             "MI_SPLIT2_C_2", "MI_SPLIT2_D_2", "MI_SPLIT2_E_2", "MI_SPLIT2_F_2", "MI_SPLIT2_G_2", "MI_SPLIT2_A_2", "MI_SPLIT2_B_2"],

            ["MI_SPLIT2_Cs_3", "MI_SPLIT2_Ds_3", "MI_SPLIT2_Fs_3", "MI_SPLIT2_Gs_3", "MI_SPLIT2_As_3",
             "MI_SPLIT2_Cs_4", "MI_SPLIT2_Ds_4", "MI_SPLIT2_Fs_4", "MI_SPLIT2_Gs_4", "MI_SPLIT2_As_4",
             "MI_SPLIT2_Cs_5", "MI_SPLIT2_Ds_5", "MI_SPLIT2_Fs_5", "MI_SPLIT2_Gs_5", "MI_SPLIT2_As_5"],

            ["MI_SPLIT2_C_3", "MI_SPLIT2_D_3", "MI_SPLIT2_E_3", "MI_SPLIT2_F_3", "MI_SPLIT2_G_3", "MI_SPLIT2_A_3", "MI_SPLIT2_B_3",
             "MI_SPLIT2_C_4", "MI_SPLIT2_D_4", "MI_SPLIT2_E_4", "MI_SPLIT2_F_4", "MI_SPLIT2_G_4", "MI_SPLIT2_A_4", "MI_SPLIT2_B_4",
             "MI_SPLIT2_C_5", "MI_SPLIT2_D_5", "MI_SPLIT2_E_5", "MI_SPLIT2_F_5", "MI_SPLIT2_G_5", "MI_SPLIT2_A_5", "MI_SPLIT2_B_5"],
            
            ["KS2_CHAN_DOWN", "KS2_CHAN_UP", "MI_VELOCITY3_DOWN", "MI_VELOCITY3_UP", "MI_TRANSPOSE3_DOWN", "MI_TRANSPOSE3_UP", "MI_OCTAVE3_DOWN", "MI_OCTAVE3_UP"]
        ]

        # Main layout for the scroll area
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.main_layout = QVBoxLayout(self.scroll_content)
        
        button_layout2 = QHBoxLayout()
        button_layout2.addStretch(1)
        # Add the toggle buttons to the horizontal layout
        self.toggle_button = QPushButton("Show KeySplit")
        self.toggle_button.clicked.connect(self.toggle_midi_layouts)
        self.toggle_button.setFixedSize(120, 40)  # Set width to 80 and height to 40
        self.toggle_button.setStyleSheet("""
            background-color: #f3d1d1;  /* Set background color (hex for rgba(243, 209, 209)) */
            color: #805757;  /* Set text color (hex for rgba(128, 87, 87)) */
        """)
        button_layout2.addWidget(self.toggle_button)
        button_layout2.setSpacing(0)
        self.toggle_button2 = QPushButton("Show TripleSplit")
        self.toggle_button2.clicked.connect(self.toggle_midi_layouts2)
        self.toggle_button2.setFixedSize(120, 40)  # Set width to 80 and height to 40
        button_layout2.addWidget(self.toggle_button2)
        button_layout2.addStretch(1)
        # Add the horizontal layout (button_layout) to the main layout
        self.main_layout.addLayout(button_layout2)       

        # 1. MIDI Layout
        self.add_midi_layout2(self.midi_layout2)
        self.add_midi_layout3(self.midi_layout3)
     
        self.midi_layout3_widget.hide()  # Hide midi_layout2
     
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
        self.centering_layout = QHBoxLayout()

        # Create the grid layout for the buttons
        self.button_layout = QGridLayout()

        # Add the grid layout to the centering layout
        self.centering_layout.addStretch()  # Add stretch before the grid layout
        self.centering_layout.addLayout(self.button_layout)
        self.centering_layout.addStretch()  # Add stretch after the grid layout

        # Add the centering layout to the main vertical layout
        self.main_layout.addLayout(self.centering_layout)

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
        
    def toggle_midi_layouts(self):
            self.midi_layout3_widget.hide()  # Hide midi_layout3
            self.midi_layout2_widget.show()  # Show midi_layout2
            self.set_highlighted(self.toggle_button)
            self.set_normal(self.toggle_button2)
            
    def toggle_midi_layouts2(self):
            self.midi_layout2_widget.hide()  # Hide midi_layout2
            self.midi_layout3_widget.show()  # Show midi_layout3
            self.set_highlighted2(self.toggle_button2)
            self.set_normal(self.toggle_button)
            
    def set_highlighted(self, button):
        button.setStyleSheet("""
            background-color: #f3d1d1;  /* Set background color (hex for rgba(243, 209, 209)) */
            color: #805757;  /* Set text color (hex for rgba(128, 87, 87)) */
        """)

    def set_highlighted2(self, button):
        button.setStyleSheet("""
            background-color: #808057;  /* Set background color (hex for rgba(128, 128, 87)) */
            color: #d1f3d7;  /* Set text color (hex for rgba(209, 243, 215)) */
        """)


    def set_normal(self, button):
        # Unset the stylesheet to revert to the default button style
        button.setStyleSheet("")  # Clears the stylesheet, using the default style


    def add_midi_layout2(self, layout):
        """Helper method to add staggered buttons based on MIDI layout."""
        # Create a QWidget for midi_layout2
        midi_container2 = QWidget()
        midi_container2_layout = QVBoxLayout()  # Use QVBoxLayout for rows
        midi_container2.setLayout(midi_container2_layout)

        # Create the MIDI buttons
        self.create_midi_buttons(layout, midi_container2_layout)

        # Add MIDI container to the main layout
        self.main_layout.addWidget(midi_container2)

        # Store a reference to the midi_layout2 widget
        self.midi_layout2_widget = midi_container2

    def add_midi_layout3(self, layout):
        """Helper method to add staggered buttons based on MIDI layout."""
        # Create a QWidget for midi_layout3
        midi_container3 = QWidget()
        midi_container3_layout = QVBoxLayout()  # Use QVBoxLayout for rows
        midi_container3.setLayout(midi_container3_layout)
    
        # Create the MIDI buttons
        self.create_midi_buttons2(layout, midi_container3_layout)

        # Add MIDI container to the main layout
        self.main_layout.addWidget(midi_container3)
    
        # Store a reference to the midi_layout3 widget
        self.midi_layout3_widget = midi_container3
            
    def create_midi_buttons(self, layout, container_layout):
        """Create buttons based on MIDI layout coordinates."""
        name_mapping = {
            "MI_SPLIT_Cs": "C#\nDb\nKS",
            "MI_SPLIT_Ds": "D#\nEb\nKS",
            "MI_SPLIT_Fs": "F#\nGb\nKS",
            "MI_SPLIT_Gs": "G#\nAb\nKS",
            "MI_SPLIT_As": "A#\nBb\nKS",
            "MI_SPLIT_Cs_1": "C#1\nDb1\nKS",
            "MI_SPLIT_Ds_1": "D#1\nEb1\nKS",
            "MI_SPLIT_Fs_1": "F#1\nGb1\nKS",
            "MI_SPLIT_Gs_1": "G#1\nAb1\nKS",
            "MI_SPLIT_As_1": "A#1\nBb1\nKS",
            "MI_SPLIT_Cs_2": "C#2\nDb2\nKS",
            "MI_SPLIT_Ds_2": "D#2\nEb2\nKS",
            "MI_SPLIT_Fs_2": "F#2\nGb2\nKS",
            "MI_SPLIT_Gs_2": "G#2\nAb2\nKS",
            "MI_SPLIT_As_2": "A#2\nBb2\nKS",
            "MI_SPLIT_C_1": "C1\nKS",
            "MI_SPLIT_D_1": "D1\nKS",
            "MI_SPLIT_E_1": "E1\nKS",
            "MI_SPLIT_F_1": "F1\nKS",
            "MI_SPLIT_G_1": "G1\nKS",
            "MI_SPLIT_A_1": "A1\nKS",
            "MI_SPLIT_B_1": "B1\nKS",
            "MI_SPLIT_C_2": "C2\nKS",
            "MI_SPLIT_D_2": "D2\nKS",
            "MI_SPLIT_E_2": "E2\nKS",
            "MI_SPLIT_F_2": "F2\nKS",
            "MI_SPLIT_G_2": "G2\nKS",
            "MI_SPLIT_A_2": "A2\nKS",
            "MI_SPLIT_B_2": "B2\nKS",
            "MI_SPLIT_Cs_3": "C#3\nDb3\nKS",
            "MI_SPLIT_Ds_3": "D#3\nEb3\nKS",
            "MI_SPLIT_Fs_3": "F#3\nGb3\nKS",
            "MI_SPLIT_Gs_3": "G#3\nAb3\nKS",
            "MI_SPLIT_As_3": "A#3\nBb3\nKS",
            "MI_SPLIT_Cs_4": "C#4\nDb4\nKS",
            "MI_SPLIT_Ds_4": "D#4\nEb4\nKS",
            "MI_SPLIT_Fs_4": "F#4\nGb4\nKS",
            "MI_SPLIT_Gs_4": "G#4\nAb4\nKS",
            "MI_SPLIT_As_4": "A#4\nBb4\nKS",
            "MI_SPLIT_Cs_5": "C#5\nDb5\nKS",
            "MI_SPLIT_Ds_5": "D#5\nEb5\nKS",
            "MI_SPLIT_Fs_5": "F#5\nGb5\nKS",
            "MI_SPLIT_Gs_5": "G#5\nAb5\nKS",
            "MI_SPLIT_As_5": "A#5\nBb5\nKS",
            "MI_SPLIT_C_3": "C3\nKS",
            "MI_SPLIT_D_3": "D3\nKS",
            "MI_SPLIT_E_3": "E3\nKS",
            "MI_SPLIT_F_3": "F3\nKS",
            "MI_SPLIT_G_3": "G3\nKS",
            "MI_SPLIT_A_3": "A3\nKS",
            "MI_SPLIT_B_3": "B3\nKS",
            "MI_SPLIT_C_4": "C4\nKS",
            "MI_SPLIT_D_4": "D4\nKS",
            "MI_SPLIT_E_4": "E4\nKS",
            "MI_SPLIT_F_4": "F4\nKS",
            "MI_SPLIT_G_4": "G4\nKS",
            "MI_SPLIT_A_4": "A4\nKS",
            "MI_SPLIT_B_4": "B4\nKS",
            "MI_SPLIT_C_5": "C5\nKS",
            "MI_SPLIT_D_5": "D5\nKS",
            "MI_SPLIT_E_5": "E5\nKS",
            "MI_SPLIT_F_5": "F5\nKS",
            "MI_SPLIT_G_5": "G5\nKS",
            "MI_SPLIT_A_5": "A5\nKS",
            "MI_SPLIT_B_5": "B5\nKS",
            "MI_SPLIT_C": "C\nKS",
            "MI_SPLIT_D": "D\nKS",
            "MI_SPLIT_E": "E\nKS",
            "MI_SPLIT_F": "F\nKS",
            "MI_SPLIT_G": "G\nKS",
            "MI_SPLIT_A": "A\nKS",
            "MI_SPLIT_B": "B\nKS",
            "KS_CHAN_DOWN": "KS\nChannel\n-", 
            "KS_CHAN_UP": "KS\nChannel\n+", 
            "MI_VELOCITY2_DOWN": "KS\nVelocity\n-", 
            "MI_VELOCITY2_UP": "KS\nVelocity\n+", 
            "MI_TRANSPOSE2_DOWN": "KS\nTranspose\n-", 
            "MI_TRANSPOSE2_UP": "KS\nTranspose\n+", 
            "MI_OCTAVE2_DOWN": "KS\nOctave\n-", 
            "MI_OCTAVE2_UP": "KS\nOctave\n+"
        }

        
        for row_index, row in enumerate(layout):
            hbox = QHBoxLayout()  # New horizontal row layout
            hbox.setAlignment(Qt.AlignCenter)
            for col_index, item in enumerate(row):
                if isinstance(item, str):
                    readable_name = name_mapping.get(item, item)
                    button = SquareButton()
                    button.setText(readable_name)

                    button.setStyleSheet("background-color: rgba(243, 209, 209, 1); color: rgba(128, 87, 87, 1);")
                    
                    if "#" in readable_name:  # Sharp keys have # in their name
                        button.setStyleSheet("background-color: rgba(128, 87, 87, 1); color: rgba(243, 209, 209, 1);")
                        # Add an empty space before the black keys to stagger
                        
                    if "Pedal" in readable_name or "Velocity" in readable_name or "Transpose" in readable_name or "Channel" in readable_name or "Octave" in readable_name:
                        button.setStyleSheet("background-color: rgba(243, 209, 209, 1); color: rgba(128, 87, 87, 1);")
  
                    if readable_name in ["C#\nDb\nKS", "C#3\nDb3\nKS"]:
                        button.setStyleSheet("background-color: rgba(128, 87, 87, 1); color: rgba(243, 209, 209, 1);")
                        
                    if readable_name in ["C#1\nDb1\nKS", "C#2\nDb2\nKS", "C#4\nDb4\nKS", "C#5\nDb5\nKS"]:
                        button.setStyleSheet("background-color: rgba(128, 87, 87, 1); color: rgba(243, 209, 209, 1);")
                        hbox.addSpacing(60)                      
                        
                    if readable_name in ["F#\nGb\nKS", "F#1\nGb1\nKS", "F#2\nGb2\nKS", "F#3\nGb3\nKS", "F#4\nGb4\nKS", "F#5\nGb5\nKS"]:
                        button.setStyleSheet("background-color: rgba(128, 87, 87, 1); color: rgba(243, 209, 209, 1);")
                        hbox.addSpacing(50)
                        
                    if readable_name in ["C1\nKS", "C2\nKS", "C4\nKS", "C5\nKS"]:
                        button.setStyleSheet("background-color: rgba(243, 209, 209, 1); color: rgba(128, 87, 87, 1);")
                        hbox.addSpacing(20)

                    

                    button.setFixedHeight(40)  # Set size as needed
                    if "Pedal" in readable_name or "Velocity" in readable_name or "Transpose" in readable_name or "Channel" in readable_name or "Octave" in readable_name:
                        button.setFixedWidth(80)  # Set fixed width of 80 for 'Pedal' or 'All' in readable_name
                    else:
                        button.setFixedWidth(40)  # Set fixed width of 40 for other buttons
                    button.clicked.connect(lambda _, text=item: self.keycode_changed.emit(text))
                    hbox.addWidget(button)  # Add button to horizontal layout

            container_layout.addLayout(hbox)  # Add row to vertical layout            

    def create_midi_buttons2(self, layout, container_layout):
        """Create buttons based on MIDI layout coordinates."""
        name_mapping = {
            "MI_SPLIT2_Cs": "C#\nDb\nTS",
            "MI_SPLIT2_Ds": "D#\nEb\nTS",
            "MI_SPLIT2_Fs": "F#\nGb\nTS",
            "MI_SPLIT2_Gs": "G#\nAb\nTS",
            "MI_SPLIT2_As": "A#\nBb\nTS",
            "MI_SPLIT2_Cs_1": "C#1\nDb1\nTS",
            "MI_SPLIT2_Ds_1": "D#1\nEb1\nTS",
            "MI_SPLIT2_Fs_1": "F#1\nGb1\nTS",
            "MI_SPLIT2_Gs_1": "G#1\nAb1\nTS",
            "MI_SPLIT2_As_1": "A#1\nBb1\nTS",
            "MI_SPLIT2_Cs_2": "C#2\nDb2\nTS",
            "MI_SPLIT2_Ds_2": "D#2\nEb2\nTS",
            "MI_SPLIT2_Fs_2": "F#2\nGb2\nTS",
            "MI_SPLIT2_Gs_2": "G#2\nAb2\nTS",
            "MI_SPLIT2_As_2": "A#2\nBb2\nTS",
            "MI_SPLIT2_C_1": "C1\nTS",
            "MI_SPLIT2_D_1": "D1\nTS",
            "MI_SPLIT2_E_1": "E1\nTS",
            "MI_SPLIT2_F_1": "F1\nTS",
            "MI_SPLIT2_G_1": "G1\nTS",
            "MI_SPLIT2_A_1": "A1\nTS",
            "MI_SPLIT2_B_1": "B1\nTS",
            "MI_SPLIT2_C_2": "C2\nTS",
            "MI_SPLIT2_D_2": "D2\nTS",
            "MI_SPLIT2_E_2": "E2\nTS",
            "MI_SPLIT2_F_2": "F2\nTS",
            "MI_SPLIT2_G_2": "G2\nTS",
            "MI_SPLIT2_A_2": "A2\nTS",
            "MI_SPLIT2_B_2": "B2\nTS",
            "MI_SPLIT2_Cs_3": "C#3\nDb3\nTS",
            "MI_SPLIT2_Ds_3": "D#3\nEb3\nTS",
            "MI_SPLIT2_Fs_3": "F#3\nGb3\nTS",
            "MI_SPLIT2_Gs_3": "G#3\nAb3\nTS",
            "MI_SPLIT2_As_3": "A#3\nBb3\nTS",
            "MI_SPLIT2_Cs_4": "C#4\nDb4\nTS",
            "MI_SPLIT2_Ds_4": "D#4\nEb4\nTS",
            "MI_SPLIT2_Fs_4": "F#4\nGb4\nTS",
            "MI_SPLIT2_Gs_4": "G#4\nAb4\nTS",
            "MI_SPLIT2_As_4": "A#4\nBb4\nTS",
            "MI_SPLIT2_Cs_5": "C#5\nDb5\nTS",
            "MI_SPLIT2_Ds_5": "D#5\nEb5\nTS",
            "MI_SPLIT2_Fs_5": "F#5\nGb5\nTS",
            "MI_SPLIT2_Gs_5": "G#5\nAb5\nTS",
            "MI_SPLIT2_As_5": "A#5\nBb5\nTS",
            "MI_SPLIT2_C_3": "C3\nTS",
            "MI_SPLIT2_D_3": "D3\nTS",
            "MI_SPLIT2_E_3": "E3\nTS",
            "MI_SPLIT2_F_3": "F3\nTS",
            "MI_SPLIT2_G_3": "G3\nTS",
            "MI_SPLIT2_A_3": "A3\nTS",
            "MI_SPLIT2_B_3": "B3\nTS",
            "MI_SPLIT2_C_4": "C4\nTS",
            "MI_SPLIT2_D_4": "D4\nTS",
            "MI_SPLIT2_E_4": "E4\nTS",
            "MI_SPLIT2_F_4": "F4\nTS",
            "MI_SPLIT2_G_4": "G4\nTS",
            "MI_SPLIT2_A_4": "A4\nTS",
            "MI_SPLIT2_B_4": "B4\nTS",
            "MI_SPLIT2_C_5": "C5\nTS",
            "MI_SPLIT2_D_5": "D5\nTS",
            "MI_SPLIT2_E_5": "E5\nTS",
            "MI_SPLIT2_F_5": "F5\nTS",
            "MI_SPLIT2_G_5": "G5\nTS",
            "MI_SPLIT2_A_5": "A5\nTS",
            "MI_SPLIT2_B_5": "B5\nTS",
            "MI_SPLIT2_C": "C\nTS",
            "MI_SPLIT2_D": "D\nTS",
            "MI_SPLIT2_E": "E\nTS",
            "MI_SPLIT2_F": "F\nTS",
            "MI_SPLIT2_G": "G\nTS",
            "MI_SPLIT2_A": "A\nTS",
            "MI_SPLIT2_B": "B\nTS",
            "KS2_CHAN_DOWN": "TS\nChannel\n-", 
            "KS2_CHAN_UP": "TS\nChannel\n+", 
            "MI_VELOCITY3_DOWN": "TS\nVelocity\n-", 
            "MI_VELOCITY3_UP": "TS\nVelocity\n+", 
            "MI_TRANSPOSE3_DOWN": "TS\nTranspose\n-", 
            "MI_TRANSPOSE3_UP": "TS\nTranspose\n+", 
            "MI_OCTAVE3_DOWN": "TS\nOctave\n-", 
            "MI_OCTAVE3_UP": "TS\nOctave\n+"
        }

        
        for row_index, row in enumerate(layout):
            hbox = QHBoxLayout()  # New horizontal row layout
            hbox.setAlignment(Qt.AlignCenter)
            for col_index, item in enumerate(row):
                if isinstance(item, str):
                    readable_name = name_mapping.get(item, item)
                    button = SquareButton()
                    button.setText(readable_name)

                    button.setStyleSheet("background-color: rgba(209, 243, 215, 1); color: rgba(128, 128, 87, 1);")
                    
                    if "#" in readable_name:  # Sharp keys have # in their name
                        button.setStyleSheet("background-color: rgba(128, 128, 87, 1); color: rgba(209, 243, 215, 1);")
                        # Add an empty space before the black keys to stagger
                        
                    if "Pedal" in readable_name or "Velocity" in readable_name or "Transpose" in readable_name or "Channel" in readable_name or "Octave" in readable_name:
                         button.setStyleSheet("background-color: rgba(209, 243, 215, 1); color: rgba(128, 128, 87, 1);")
  
                    if readable_name in ["C#\nDb\nTS", "C#3\nDb3\nTS"]:
                        button.setStyleSheet("background-color: rgba(128, 128, 87, 1); color: rgba(209, 243, 215, 1);")
                        
                    if readable_name in ["C#1\nDb1\nTS", "C#2\nDb2\nTS", "C#4\nDb4\nTS", "C#5\nDb5\nTS"]:
                        button.setStyleSheet("background-color: rgba(128, 128, 87, 1); color: rgba(209, 243, 215, 1);")
                        hbox.addSpacing(60)                      
                        
                    if readable_name in ["F#\nGb\nTS", "F#1\nGb1\nTS", "F#2\nGb2\nTS", "F#3\nGb3\nTS", "F#4\nGb4\nTS", "F#5\nGb5\nTS"]:
                        button.setStyleSheet("background-color: rgba(128, 128, 87, 1); color: rgba(209, 243, 215, 1);")
                        hbox.addSpacing(50)
                        
                    if readable_name in ["C1\nTS", "C2\nTS", "C4\nTS", "C5\nTS"]:
                        button.setStyleSheet("background-color: rgba(209, 243, 215, 1); color: rgba(128, 128, 87, 1);")
                        hbox.addSpacing(20)

                    

                    button.setFixedHeight(40)  # Set size as needed
                    if "Pedal" in readable_name or "Velocity" in readable_name or "Transpose" in readable_name or "Channel" in readable_name or "Octave" in readable_name:
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
                btn.setFixedSize(60, 60)  # Set fixed width and height
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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

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

                    button.setStyleSheet("background-color: rgba(255, 255, 204, 1); color: rgba(128, 102, 0, 1);")
                    
                    if "#" in readable_name:  # Sharp keys have # in their name
                        button.setStyleSheet("background-color: rgba(204, 255, 255, 1); color: rgba(0, 102, 102, 1);")
                        # Add an empty space before the black keys to stagger
                        
                    if "Pedal" in readable_name or "All" in readable_name or " " in readable_name or "Smart" in readable_name:
                        button.setStyleSheet("background-color: rgba(255, 255, 204, 1); color: rgba(128, 102, 0, 1);")
  
                    if readable_name in ["C#\nDb", "C#3\nDb3"]:
                        button.setStyleSheet("background-color: rgba(204, 255, 255, 1); color: rgba(0, 102, 102, 1);")
                        
                    if readable_name in ["C#1\nDb1", "C#2\nDb2", "C#4\nDb4", "C#5\nDb5"]:
                        button.setStyleSheet("background-color: rgba(204, 255, 255, 1); color: rgba(0, 102, 102, 1);")
                        hbox.addSpacing(60)                      
                        
                    if readable_name in ["F#\nGb", "F#1\nGb1", "F#2\nGb2", "F#3\nGb3", "F#4\nGb4", "F#5\nGb5"]:
                        button.setStyleSheet("background-color: rgba(204, 255, 255, 1); color: rgba(0, 102, 102, 1);")
                        hbox.addSpacing(50)
                        
                    if readable_name in ["C1", "C2", "C4", "C5"]:
                        button.setStyleSheet("background-color: rgba(255, 255, 204, 1); color: rgba(128, 102, 0, 1);")
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
            midiTab(self, "MIDIswitch", KEYCODES_MIDI_UPDOWN),   # Updated to SmartChordTab
            SmartChordTab(self, "SmartChord", KEYCODES_MIDI_CHORD_0, KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_INVERSION, KEYCODES_MIDI_SMARTCHORDBUTTONS),
            KeySplitTab(self, "KeySplit", KEYCODES_KEYSPLIT_BUTTONS),   # Updated to SmartChordTab
            midiadvancedTab(self, "MIDI Advanced",  KEYCODES_MIDI_ADVANCED, KEYCODES_Program_Change, KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC, KEYCODES_MIDI_CC_FIXED, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN, KEYCODES_VELOCITY_STEPSIZE, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_VELOCITY, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD, KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_VELOCITY2, KEYCODES_MIDI_VELOCITY3, KEYCODES_MIDI_KEY2, KEYCODES_MIDI_KEY3, KEYCODES_MIDI_OCTAVE2, KEYCODES_MIDI_OCTAVE3, KEYCODES_MIDI_CHANNEL_KEYSPLIT, KEYCODES_MIDI_CHANNEL_KEYSPLIT2),
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
