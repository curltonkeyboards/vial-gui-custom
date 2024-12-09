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
    KEYCODES_MIDI_CC, KEYCODES_MIDI_BANK, KEYCODES_Program_Change, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_VELOCITY, KEYCODES_Program_Change_UPDOWN, KEYCODES_MIDI_BANK, KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC_FIXED, KEYCODES_OLED, KEYCODES_EARTRAINER, KEYCODES_CHORDTRAINER, \
    KEYCODES_MIDI_OCTAVE2, KEYCODES_MIDI_OCTAVE3, KEYCODES_MIDI_KEY2, KEYCODES_MIDI_KEY3, KEYCODES_MIDI_VELOCITY2, KEYCODES_MIDI_VELOCITY3, KEYCODES_MIDI_ADVANCED, KEYCODES_MIDI_SMARTCHORDBUTTONS, KEYCODES_VELOCITY_STEPSIZE, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD, \
    KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_UPDOWN, KEYCODES_MIDI_CHORD_0, KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_CHORD_5, KEYCODES_MIDI_INVERSION, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN, KEYCODES_MIDI_PEDAL
from widgets.square_button import SquareButton
from widgets.big_square_button import BigSquareButton
from util import tr, KeycodeDisplay



class PianoButton(SquareButton):
    def __init__(self, key_type='white', color_scheme='default'):
        super().__init__()
        if color_scheme == 'default':
            self.setStyleSheet(self.GLASS_WHITE if key_type == 'white' else self.GLASS_BLACK)
        elif color_scheme == 'keysplit':
            self.setStyleSheet(self.KS_WHITE if key_type == 'white' else self.KS_BLACK)
        elif color_scheme == 'triplesplit':
            self.setStyleSheet(self.TS_WHITE if key_type == 'white' else self.TS_BLACK)

    # Original styles
    GLASS_WHITE = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 240), 
                stop:0.5 rgba(240, 240, 240, 240),
                stop:1 rgba(230, 230, 230, 240));
            border: 1px solid rgba(200, 200, 200, 180);
            border-radius: 4px;
            color: #303030;
            padding: 2px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 255),
                stop:1 rgba(240, 240, 240, 255));
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(230, 230, 230, 255),
                stop:1 rgba(220, 220, 220, 255));
        }
    """

    GLASS_BLACK = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(40, 40, 40, 240),
                stop:0.5 rgba(30, 30, 30, 240),
                stop:1 rgba(20, 20, 20, 240));
            border: 1px solid rgba(0, 0, 0, 180);
            border-radius: 4px;
            color: #FFFFFF;
            padding: 2px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(50, 50, 50, 255),
                stop:1 rgba(40, 40, 40, 255));
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(30, 30, 30, 255),
                stop:1 rgba(20, 20, 20, 255));
        }
    """

    # KeySplit styles
    KS_WHITE = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(243, 209, 209, 240),
                stop:0.5 rgba(238, 204, 204, 240),
                stop:1 rgba(233, 199, 199, 240));
            border: 1px solid rgba(128, 87, 87, 180);
            border-radius: 4px;
            color: rgba(128, 87, 87, 255);
            padding: 2px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(248, 214, 214, 255),
                stop:1 rgba(243, 209, 209, 255));
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(238, 204, 204, 255),
                stop:1 rgba(233, 199, 199, 255));
        }
    """

    KS_BLACK = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(128, 87, 87, 240),
                stop:0.5 rgba(118, 77, 77, 240),
                stop:1 rgba(108, 67, 67, 240));
            border: 1px solid rgba(88, 47, 47, 180);
            border-radius: 4px;
            color: rgba(243, 209, 209, 255);
            padding: 2px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(138, 97, 97, 255),
                stop:1 rgba(128, 87, 87, 255));
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(118, 77, 77, 255),
                stop:1 rgba(108, 67, 67, 255));
        }
    """

    # TripleSplit styles
    TS_WHITE = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(209, 243, 215, 240),
                stop:0.5 rgba(204, 238, 210, 240),
                stop:1 rgba(199, 233, 205, 240));
            border: 1px solid rgba(128, 128, 87, 180);
            border-radius: 4px;
            color: rgba(128, 128, 87, 255);
            padding: 2px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(214, 248, 220, 255),
                stop:1 rgba(209, 243, 215, 255));
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(204, 238, 210, 255),
                stop:1 rgba(199, 233, 205, 255));
        }
    """

    TS_BLACK = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(128, 128, 87, 240),
                stop:0.5 rgba(118, 118, 77, 240),
                stop:1 rgba(108, 108, 67, 240));
            border: 1px solid rgba(88, 88, 47, 180);
            border-radius: 4px;
            color: rgba(209, 243, 215, 255);
            padding: 2px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(138, 138, 97, 255),
                stop:1 rgba(128, 128, 87, 255));
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(118, 118, 77, 255),
                stop:1 rgba(108, 108, 67, 255));
        }
    """

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

    def __init__(self, parent, label, smartchord_keycodes_0, smartchord_keycodes_1, smartchord_keycodes_2, smartchord_keycodes_3, smartchord_keycodes_4, smartchord_keycodes_5, scales_modes_keycodes, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.smartchord_keycodes_0 = smartchord_keycodes_0
        self.smartchord_keycodes_1 = smartchord_keycodes_1
        self.smartchord_keycodes_2 = smartchord_keycodes_2
        self.smartchord_keycodes_3 = smartchord_keycodes_3
        self.smartchord_keycodes_4 = smartchord_keycodes_4
        self.smartchord_keycodes_5 = smartchord_keycodes_5
        self.scales_modes_keycodes = scales_modes_keycodes
        self.inversion_keycodes = inversion_keycodes

        
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
        self.create_keycode_tree(self.smartchord_keycodes_4, "6 Note Chords")
        self.create_keycode_tree(self.smartchord_keycodes_5, "Other")
        self.create_keycode_tree(self.scales_modes_keycodes, "Scales/Modes")
        


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
                if col >= 20:
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
        
class ModernButton(QPushButton):
    def __init__(self, text, color="#4a90e2"):
        super().__init__(text)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 6px;
                color: white;
                padding: 10px;
                font-weight: bold;
                min-height: 40px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color, 20)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color, 20)};
            }}
        """)
        
    def lighten_color(self, color, amount):
        # Convert hex to RGB and lighten
        c = color.lstrip('#')
        rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, x + amount) for x in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*rgb)
        
    def darken_color(self, color, amount):
        c = color.lstrip('#')
        rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(max(0, x - amount) for x in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

import math

class EarTrainerTab(QScrollArea):
    keycode_changed = pyqtSignal(str)
    
    def __init__(self, parent, label, eartrainer_keycodes, chordtrainer_keycodes):
        super().__init__(parent)
        self.label = label
        self.eartrainer_keycodes = eartrainer_keycodes
        self.chordtrainer_keycodes = chordtrainer_keycodes
        
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        
        # Add heading row
        headers = QWidget()
        headers_layout = QHBoxLayout(headers)
        headers_layout.setContentsMargins(20, 0, 20, 0)
        
        # Interval Trainer header
        interval_header = QLabel("Interval Trainer")
        interval_header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
            }
        """)
        interval_header.setAlignment(Qt.AlignCenter)
        headers_layout.addWidget(interval_header)
        
        # Spacer for divider space
        headers_layout.addSpacing(40)
        
        # Chord Trainer header
        chord_header = QLabel("Chord Trainer")
        chord_header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
            }
        """)
        chord_header.setAlignment(Qt.AlignCenter)
        headers_layout.addWidget(chord_header)
        
        self.main_layout.addWidget(headers)
        
        # Container for both sections
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setSpacing(20)
        
        # Left section (Interval Trainer) - 3 columns, 4 rows
        left_section = QWidget()
        left_layout = QGridLayout(left_section)
        left_layout.setSpacing(10)
        
        # Right section (Chord Trainer) - 5 columns, 4 rows
        right_section = QWidget()
        right_layout = QGridLayout(right_section)
        right_layout.setSpacing(10)
        
        # Add sections to container
        container_layout.addWidget(left_section)
        container_layout.addWidget(right_section)
        
        # Add container to main layout
        self.main_layout.addWidget(container)
        
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        
        self.left_layout = left_layout
        self.right_layout = right_layout
        
        self.recreate_buttons()

    def create_gradient_button(self, text, position, total_positions, section):
        """Create a button with gradient based on its position"""
        btn = QPushButton(text)
        
        # Calculate darkness factor based on distance from center
        if section == 'interval':
            max_distance = math.sqrt(2**2 + 3**2)  # max distance from center in either direction
            x_dist = abs(position[1] - 1)  # distance from center column (0-based)
            y_dist = abs(position[0] - 1.5)  # distance from center row (0-based)
        else:  # chord
            max_distance = math.sqrt(2**2 + 4**2)  # max distance from center
            x_dist = abs(position[1] - 2)  # distance from center column
            y_dist = abs(position[0] - 1.5)  # distance from center row
            
        distance = math.sqrt(x_dist**2 + y_dist**2) / max_distance
        darkness = int(40 * distance)  # Adjust the multiplier to control gradient intensity
        
        if section == 'interval':
            base_color = (184, 216, 235)  # Light blue base
        else:
            base_color = (201, 228, 202)  # Light green base
            
        darker_color = tuple(max(0, c - darkness) for c in base_color)
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb{darker_color};
                border: none;
                border-radius: 6px;
                color: #303030;
                padding: 10px;
                font-weight: bold;
                min-height: 40px;
            }}
            QPushButton:hover {{
                background-color: rgb{tuple(min(255, c + 20) for c in darker_color)};
            }}
            QPushButton:pressed {{
                background-color: rgb{tuple(max(0, c - 20) for c in darker_color)};
            }}
        """)
        
        return btn

    def recreate_buttons(self, keycode_filter=None):
        # Clear existing layouts
        for layout in [self.left_layout, self.right_layout]:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Create Interval Trainer buttons (3x4 grid)
        for i, keycode in enumerate(self.eartrainer_keycodes):
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                row = i // 3
                col = i % 3
                btn = self.create_gradient_button(
                    Keycode.label(keycode.qmk_id),
                    (row, col),
                    (4, 3),
                    'interval'
                )
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                self.left_layout.addWidget(btn, row, col)

        # Create Chord Trainer buttons (5x4 grid)
        for i, keycode in enumerate(self.chordtrainer_keycodes):
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                row = i // 5
                col = i % 5
                btn = self.create_gradient_button(
                    Keycode.label(keycode.qmk_id),
                    (row, col),
                    (4, 5),
                    'chord'
                )
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                self.right_layout.addWidget(btn, row, col)

    def relabel_buttons(self):
        for layout in [self.left_layout, self.right_layout]:
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if hasattr(widget, 'keycode'):
                    widget.setText(Keycode.label(widget.keycode.qmk_id))

    def has_buttons(self):
        return (self.left_layout.count() > 0 or 
                self.right_layout.count() > 0)



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

        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        self.recreate_buttons()
        self.main_layout.addStretch()

    def recreate_buttons(self, keycode_filter=None):
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        row = 0
        col = 0

        # Add dropdowns
        dropdown_configs = [
            ("Active/Default Layer", self.smartchord_CC_toggle),
            ("Hold Layer", self.smartchord_program_change),
            ("Toggle Layer", self.smartchord_LSB),
            ("Tap-Toggle Layer", self.smartchord_MSB),
            ("One Shot Layer", self.smartchord_LSB2),
            ("Double Layer", self.smartchord_CC_toggle2)
        ]

        for header_text, keycodes in dropdown_configs:
            dropdown = CenteredComboBox()
            dropdown.setFixedHeight(40)
            dropdown.addItem(header_text)
            
            for keycode in keycodes:
                if keycode_filter is None or keycode_filter(keycode.qmk_id):
                    label = Keycode.label(keycode.qmk_id)
                    tooltip = Keycode.description(keycode.qmk_id)
                    dropdown.addItem(label, keycode.qmk_id)
                    item = dropdown.model().item(dropdown.count() - 1)
                    item.setToolTip(tooltip)
            
            dropdown.model().item(0).setEnabled(False)
            dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, header_text))
            dropdown.currentIndexChanged.connect(lambda d=dropdown, h=header_text: self.reset_dropdown(d, h))
            
            self.button_layout.addWidget(dropdown, row, col)
            col += 1

        # Add regular buttons
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(40)
                btn.setFixedWidth(40)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                self.button_layout.addWidget(btn, row, col)
                col += 1
                if col >= 15:
                    col = 0
                    row += 1

    def reset_dropdown(self, dropdown, header_text):
        selected_index = dropdown.currentIndex()
        if selected_index > 0:
            selected_value = dropdown.itemData(selected_index)
        dropdown.setCurrentIndex(0)

    def on_selection_change(self, index):
        selected_qmk_id = self.sender().itemData(index)
        if selected_qmk_id:
            self.keycode_changed.emit(selected_qmk_id)

    def relabel_buttons(self):
        for i in range(self.button_layout.count()):
            widget = self.button_layout.itemAt(i).widget()
            if isinstance(widget, SquareButton):
                keycode = widget.keycode
                if keycode:
                    widget.setText(Keycode.label(keycode.qmk_id))

    def has_buttons(self):
        return self.button_layout.count() > 0
        
from PyQt5.QtWidgets import QFrame, QListView, QScrollBar

class ScrollableComboBox(CenteredComboBox):
    def showPopup(self):
        popup = self.findChild(QFrame)
        if popup:
            popup.setFixedHeight(300)
            view = popup.findChild(QListView)
            if view:
                view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
                view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                view.verticalScrollBar().setValue(0)
        super().showPopup()
        
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

        # Layout for buttons
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate the buttons (including dropdowns)
        self.recreate_buttons()

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def recreate_buttons(self, keycode_filter=None):
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        row = 0
        col = 0

        # Add RGB Mode dropdown
        dropdown1 = ScrollableComboBox()
        dropdown1.setFixedHeight(40)
        dropdown1.setMinimumWidth(150)
        dropdown1.addItem("RGB Mode")
        for keycode in self.smartchord_LSB:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                label = Keycode.label(keycode.qmk_id)
                tooltip = Keycode.description(keycode.qmk_id)
                dropdown1.addItem(label, keycode.qmk_id)
                item = dropdown1.model().item(dropdown1.count() - 1)
                item.setToolTip(tooltip)
        dropdown1.model().item(0).setEnabled(False)
        dropdown1.currentIndexChanged.connect(self.on_selection_change)
        dropdown1.currentIndexChanged.connect(lambda x: self.reset_dropdown(dropdown1, "RGB Mode"))
        self.button_layout.addWidget(dropdown1, row, col)
        col += 1

        # Add RGB Color dropdown
        dropdown2 = ScrollableComboBox()
        dropdown2.setFixedHeight(40)
        dropdown2.setMinimumWidth(150)
        dropdown2.addItem("RGB Color")
        for keycode in self.smartchord_MSB:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                label = Keycode.label(keycode.qmk_id)
                tooltip = Keycode.description(keycode.qmk_id)
                dropdown2.addItem(label, keycode.qmk_id)
                item = dropdown2.model().item(dropdown2.count() - 1)
                item.setToolTip(tooltip)
        dropdown2.model().item(0).setEnabled(False)
        dropdown2.currentIndexChanged.connect(self.on_selection_change)
        dropdown2.currentIndexChanged.connect(lambda x: self.reset_dropdown(dropdown2, "RGB Color"))
        self.button_layout.addWidget(dropdown2, row, col)
        col += 1

        # Add regular buttons
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(40)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                self.button_layout.addWidget(btn, row, col)
                col += 1
                if col >= 15:
                    col = 0
                    row += 1                  

    def reset_dropdown(self, dropdown, header_text):
        """Reset the dropdown to show default text while storing the selected value."""
        selected_index = dropdown.currentIndex()
        if selected_index > 0:  # Ensure an actual selection was made
            selected_value = dropdown.itemData(selected_index)
            # Process the selected value if necessary here
            # Example: print(f"Selected: {selected_value}")
        dropdown.setCurrentIndex(0)

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
        return self.button_layout.count() > 0

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

        # Layout for buttons using QGridLayout
        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)

        # Populate all buttons including value buttons
        self.recreate_buttons()

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def add_value_button(self, label_text, row, col):
        """Create a button that opens a dialog to input a value for the corresponding keycode."""
        button = QPushButton(label_text)
        button.setFixedHeight(40)
        button.clicked.connect(lambda: self.open_value_dialog(label_text))
        self.button_layout.addWidget(button, row, col)

    def open_value_dialog(self, label):
        """Open a dialog to input a value between 0 and 127 and set the keycode accordingly."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Set Value for {label}")
        dialog.setFixedSize(300, 150)

        max_value = 31 if label == "Tapdance Selection" else 255
        
        layout = QVBoxLayout(dialog)
        label_widget = QLabel(f"Enter value for {label} (0-{max_value}):")
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText(f"Enter a number between 0 and {max_value}")
        self.value_input.textChanged.connect(lambda text: self.validate_value_input(text, max_value))

        layout.addWidget(label_widget)
        layout.addWidget(self.value_input)

        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(lambda: self.confirm_value(dialog, label))
        layout.addWidget(confirm_button)

        dialog.exec_()

    def validate_value_input(self, text, max_value):
        if text and (not text.isdigit() or not (0 <= int(text) <= max_value)):
            self.value_input.clear()

    def confirm_value(self, dialog, label):
        """Confirm the value input and emit the corresponding keycode."""
        value = self.value_input.text()
        max_value = 31 if label == "Tapdance Selection" else 255
        
        if value.isdigit() and 0 <= int(value) <= max_value:
            keycode_map = {
                "TapDance Selection": f"TD({value})",
                "Macro Selection": f"M{value}"
            }
            
            # Construct the keycode using the label as a key
            if label in keycode_map:
                selected_keycode = keycode_map[label]
                self.keycode_changed.emit(selected_keycode)
                dialog.accept()

    def recreate_buttons(self, keycode_filter=None):
        # Clear previous widgets
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
    
        row = 0
        col = 0
        max_columns = 15  # Maximum number of columns
    
        # Add value buttons first (on the left)
        self.add_value_button("Macro Selection", row, col)
        col += 1
        self.add_value_button("Tapdance Selection", row, col)
        col += 1

        # Add regular buttons after the value buttons
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(40)
                btn.setFixedWidth(40)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                # Add button to the grid layout
                self.button_layout.addWidget(btn, row, col)

                # Move to the next column
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

class KeySplitTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.scroll_content = QWidget()
        
        # Main layout
        self.main_layout = QVBoxLayout(self.scroll_content)
        
        # Toggle buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        
        self.toggle_button = QPushButton("Show KeySplit")
        self.toggle_button.clicked.connect(self.toggle_midi_layouts)
        self.toggle_button.setFixedSize(120, 40)
        self.toggle_button.setStyleSheet("""
            background-color: #f3d1d1;
            color: #805757;
        """)
        button_layout.addWidget(self.toggle_button)
        
        self.toggle_button2 = QPushButton("Show TripleSplit")
        self.toggle_button2.clicked.connect(self.toggle_midi_layouts2)
        self.toggle_button2.setFixedSize(120, 40)
        button_layout.addWidget(self.toggle_button2)
        button_layout.addStretch(1)
        
        self.main_layout.addLayout(button_layout)

        # Create piano keyboards
        self.keysplit_piano = PianoKeyboard(color_scheme='keysplit')
        self.keysplit_piano.keyPressed.connect(self.keycode_changed)
        
        self.triplesplit_piano = PianoKeyboard(color_scheme='triplesplit')
        self.triplesplit_piano.keyPressed.connect(self.keycode_changed)
        
        self.main_layout.addWidget(self.keysplit_piano)
        self.main_layout.addWidget(self.triplesplit_piano)
        self.triplesplit_piano.hide()

        # Control buttons for KeySplit
        self.ks_controls = QWidget()
        ks_control_layout = QHBoxLayout(self.ks_controls)
        ks_control_layout.setAlignment(Qt.AlignCenter)
        self.create_control_buttons(ks_control_layout, 'KS')
        self.main_layout.addWidget(self.ks_controls)
        
        # Control buttons for TripleSplit
        self.ts_controls = QWidget()
        ts_control_layout = QHBoxLayout(self.ts_controls)
        ts_control_layout.setAlignment(Qt.AlignCenter)
        self.create_control_buttons(ts_control_layout, 'TS')
        self.main_layout.addWidget(self.ts_controls)
        self.ts_controls.hide()

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def create_control_buttons(self, layout, prefix):
        controls = [
            (f"{prefix}\nChannel\n-", f"{prefix}_CHAN_DOWN"),
            (f"{prefix}\nChannel\n+", f"{prefix}_CHAN_UP"),
            (f"{prefix}\nVelocity\n-", f"MI_VELOCITY{2 if prefix == 'KS' else 3}_DOWN"),
            (f"{prefix}\nVelocity\n+", f"MI_VELOCITY{2 if prefix == 'KS' else 3}_UP"),
            (f"{prefix}\nTranspose\n-", f"MI_TRANSPOSE{2 if prefix == 'KS' else 3}_DOWN"),
            (f"{prefix}\nTranspose\n+", f"MI_TRANSPOSE{2 if prefix == 'KS' else 3}_UP"),
            (f"{prefix}\nOctave\n-", f"MI_OCTAVE{2 if prefix == 'KS' else 3}_DOWN"),
            (f"{prefix}\nOctave\n+", f"MI_OCTAVE{2 if prefix == 'KS' else 3}_UP")
        ]

        for text, code in controls:
            btn = QPushButton(text)
            btn.setFixedSize(80, 50)
            if prefix == 'KS':
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(243, 209, 209, 1);
                        color: rgba(128, 87, 87, 1);
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: rgba(248, 214, 214, 1);
                    }
                    QPushButton:pressed {
                        background-color: rgba(238, 204, 204, 1);
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(209, 243, 215, 1);
                        color: rgba(128, 128, 87, 1);
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: rgba(214, 248, 220, 1);
                    }
                    QPushButton:pressed {
                        background-color: rgba(204, 238, 210, 1);
                    }
                """)
            btn.clicked.connect(lambda _, k=code: self.keycode_changed.emit(k))
            layout.addWidget(btn)

    def toggle_midi_layouts(self):
        self.keysplit_piano.show()
        self.triplesplit_piano.hide()
        self.ks_controls.show()
        self.ts_controls.hide()
        self.set_highlighted(self.toggle_button)
        self.set_normal(self.toggle_button2)

    def toggle_midi_layouts2(self):
        self.keysplit_piano.hide()
        self.triplesplit_piano.show()
        self.ks_controls.hide()
        self.ts_controls.show()
        self.set_highlighted2(self.toggle_button2)
        self.set_normal(self.toggle_button)

    def set_highlighted(self, button):
        button.setStyleSheet("""
            background-color: #f3d1d1;
            color: #805757;
        """)

    def set_highlighted2(self, button):
        button.setStyleSheet("""
            background-color: #808057;
            color: #d1f3d7;
        """)

    def set_normal(self, button):
        button.setStyleSheet("")

    def recreate_buttons(self, keycode_filter=None):
        self.keysplit_piano.create_piano_keys(self.inversion_keycodes, 'MI_SPLIT')
        self.triplesplit_piano.create_piano_keys(self.inversion_keycodes, 'MI_SPLIT2')

    def has_buttons(self):
        return True



class PianoKeyboard(QWidget):
    keyPressed = pyqtSignal(str)

    def __init__(self, parent=None, color_scheme='default'):
        super().__init__(parent)
        self.color_scheme = color_scheme
        
        # Key dimensions
        self.white_key_width = 45
        self.white_key_height = 90
        self.black_key_width = 31
        self.black_key_height = 60
        self.row_spacing = 30
        
        # Calculate size for two rows of 3 octaves each
        self.octaves_per_row = 3
        self.white_keys_per_octave = 7
        self.total_white_keys_per_row = self.octaves_per_row * self.white_keys_per_octave
        
        # Set fixed widget size
        total_width = self.total_white_keys_per_row * self.white_key_width
        total_height = (self.white_key_height * 2) + self.row_spacing
        
        # Create a container for centering
        self.container = QWidget(self)
        self.container.setFixedSize(total_width, total_height)
        
        # Center the container
        self.setMinimumSize(total_width + 40, total_height + 30)
        
        self.white_keys = []
        self.black_keys = []

    def resizeEvent(self, event):
        # Center the container in the widget
        x = (self.width() - self.container.width()) // 2
        y = (self.height() - self.container.height()) // 2
        self.container.move(x, y)
        super().resizeEvent(event)

    def create_piano_keys(self, midi_mappings, key_prefix='MI'):
        for key in self.white_keys + self.black_keys:
            key.deleteLater()
        self.white_keys.clear()
        self.black_keys.clear()

        key_pattern = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        for row in range(2):
            white_index = 0
            y_offset = row * (self.white_key_height + self.row_spacing)
            start_octave = 0 if row == 0 else 3

            # Create white keys first
            for octave in range(start_octave, start_octave + 3):
                for i, is_black in enumerate(key_pattern):
                    if not is_black:
                        x = white_index * self.white_key_width
                        key = PianoButton(key_type='white', color_scheme=self.color_scheme)
                        key.setParent(self.container)
                        key.setGeometry(x, y_offset, self.white_key_width, self.white_key_height)
                        
                        note = notes[i]
                        midi_id = f"{key_prefix}_{note}" if octave == 0 else f"{key_prefix}_{note}_{octave}"
                        display_text = f"\n\n\n\n{note}{octave}"
                        
                        key.setText(display_text)
                        key.clicked.connect(lambda checked, k=midi_id: self.keyPressed.emit(k))
                        self.white_keys.append(key)
                        white_index += 1

            # Create black keys on top
            white_index = 0
            for octave in range(start_octave, start_octave + 3):
                for i, is_black in enumerate(key_pattern):
                    if is_black:
                        x = white_index * self.white_key_width - (self.black_key_width // 2)
                        key = PianoButton(key_type='black', color_scheme=self.color_scheme)
                        key.setParent(self.container)
                        key.setGeometry(x, y_offset, self.black_key_width, self.black_key_height)
                        
                        note = notes[i].replace('#', 's')
                        midi_id = f"{key_prefix}_{note}" if octave == 0 else f"{key_prefix}_{note}_{octave}"
                        display_text = f"\n\n{notes[i]}{octave}"
                        
                        key.setText(display_text)
                        key.clicked.connect(lambda checked, k=midi_id: self.keyPressed.emit(k))
                        self.black_keys.append(key)
                    if not is_black:
                        white_index += 1

class midiTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.scroll_content = QWidget()

        # In midiTab class, restore original control buttons
        self.midi_layout2 = [
            ["KC_NO", "MI_ALLOFF", "MI_SUS", "MI_CHORD_99"]
]

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.main_layout = QVBoxLayout(self.scroll_content)

        # Piano keyboard
        self.piano = PianoKeyboard()
        self.piano.keyPressed.connect(self.keycode_changed)
        self.main_layout.addWidget(self.piano)

                # Control buttons
        control_container = QWidget()
        control_layout = QHBoxLayout(control_container)
        control_layout.setAlignment(Qt.AlignCenter)

        for item in self.midi_layout2[0]:
            btn = QPushButton()
            btn.setFixedSize(50, 50)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                    border-radius: 8px;
                    color: #333333;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            if item == "MI_ALLOFF":
                btn.setText("All\nNotes\nOff")
            elif item == "MI_SUS":
                btn.setText("Sustain\nPedal")
            elif item == "MI_CHORD_99":
                btn.setText("Smart\nChord")
            elif item == "KC_NO":
                btn.setText("")
            btn.clicked.connect(lambda _, k=item: self.keycode_changed.emit(k))
            control_layout.addWidget(btn)

        self.main_layout.addWidget(control_container)

        self.main_layout.addWidget(control_container)
        
        self.main_layout.addWidget(control_container)
        
        # Additional layouts
        self.dropdown_layout = QVBoxLayout()
        self.main_layout.addLayout(self.dropdown_layout)
        self.horizontal_dropdown_layout = QHBoxLayout()
        self.dropdown_layout.addLayout(self.horizontal_dropdown_layout)
        
        self.inversion_label = QLabel(" ")
        self.main_layout.addWidget(self.inversion_label)

        self.button_layout = QGridLayout()
        self.main_layout.addLayout(self.button_layout)
        self.recreate_buttons()
        self.main_layout.addStretch()

    def add_header_dropdown(self, header_text, keycodes, layout):
        header_dropdown_layout = QVBoxLayout()
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
        
        dropdown = CenteredComboBox()
        dropdown.setFixedWidth(300)
        dropdown.setFixedHeight(40)
        dropdown.addItem(f"Select {header_text}")
        dropdown.model().item(0).setEnabled(False)
        
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        header_dropdown_layout.addWidget(dropdown)
        layout.addLayout(header_dropdown_layout)

    def reset_dropdown(self, dropdown, header_text):
        selected_index = dropdown.currentIndex()
        if selected_index > 0:
            selected_value = dropdown.itemData(selected_index)
        dropdown.setCurrentIndex(0)

        # In midiTab class:
    def recreate_buttons(self, keycode_filter=None):
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        midi_mappings = {kc.qmk_id: kc for kc in self.inversion_keycodes 
                        if keycode_filter is None or keycode_filter(kc.qmk_id)}
        self.piano.create_piano_keys(midi_mappings)

        row = 0
        col = 0
        # Remove the MI_ check since we want these MIDI controls to show
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                grid_btn = SquareButton()
                grid_btn.setRelSize(KEYCODE_BTN_RATIO)
                grid_btn.setText(Keycode.label(keycode.qmk_id))
                grid_btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                grid_btn.keycode = keycode
                self.button_layout.addWidget(grid_btn, row, col)
                col += 1
                if col >= 5:
                    col = 0
                    row += 1

    def on_selection_change(self, index):
        selected_qmk_id = self.sender().itemData(index)
        if selected_qmk_id:
            self.keycode_changed.emit(selected_qmk_id)

    def relabel_buttons(self):
        # First relabel piano keys
        for widget in self.piano.white_keys + self.piano.black_keys:
            if hasattr(widget, 'keycode'):
                widget.setText(Keycode.label(widget.keycode.qmk_id))
        
        # Then relabel other buttons
        for i in range(self.button_layout.count()):
            widget = self.button_layout.itemAt(i).widget()
            if isinstance(widget, SquareButton) and hasattr(widget, 'keycode'):
                widget.setText(Keycode.label(widget.keycode.qmk_id))

    def has_buttons(self):
        return True


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
            SmartChordTab(self, "SmartChord", KEYCODES_MIDI_CHORD_0, KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_CHORD_5, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_SMARTCHORDBUTTONS+KEYCODES_MIDI_INVERSION),
            KeySplitTab(self, "KeySplit", KEYCODES_KEYSPLIT_BUTTONS),   # Updated to SmartChordTab
            EarTrainerTab(self, "Ear Training", KEYCODES_EARTRAINER, KEYCODES_CHORDTRAINER), 
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
