# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTabWidget, QWidget, QScrollArea, QApplication, QVBoxLayout, QComboBox, QSizePolicy, QLabel, QGridLayout, QStyleOptionComboBox, QDialog, QLineEdit
from PyQt5.QtGui import QPalette, QPainter

from constants import KEYCODE_BTN_RATIO
from widgets.display_keyboard import DisplayKeyboard
from widgets.display_keyboard_defs import ansi_100, ansi_80, ansi_70, iso_100, iso_80, iso_70, mods, mods_narrow, midi_layout
from widgets.flowlayout import FlowLayout
from keycodes.keycodes import KEYCODES_BASIC, KEYCODES_ISO, KEYCODES_MACRO, KEYCODES_MACRO_BASE, KEYCODES_LAYERS, KEYCODES_QUANTUM, \
    KEYCODES_BOOT, KEYCODES_MODIFIERS, KEYCODES_CLEAR, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_CUSTOM2, KEYCODES_RGBSAVE, KEYCODES_EXWHEEL, KEYCODES_RGB_KC_COLOR, KEYCODES_MIDI_SPLIT_BUTTONS, \
    KEYCODES_BACKLIGHT, KEYCODES_MEDIA, KEYCODES_SPECIAL, KEYCODES_SHIFTED, KEYCODES_USER, Keycode, KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_TG, KEYCODES_LAYERS_TT, KEYCODES_LAYERS_OSL, KEYCODES_LAYERS_TO, KEYCODES_LAYERS_LT, KEYCODES_VELOCITY_SHUFFLE, KEYCODES_CC_ENCODERVALUE,\
    KEYCODES_TAP_DANCE, KEYCODES_MIDI, KEYCODES_MIDI_SPLIT, KEYCODES_MIDI_SPLIT2, KEYCODES_MIDI_CHANNEL_KEYSPLIT, KEYCODES_KEYSPLIT_BUTTONS, KEYCODES_MIDI_CHANNEL_KEYSPLIT2, KEYCODES_BASIC_NUMPAD, KEYCODES_BASIC_NAV, KEYCODES_ISO_KR, BASIC_KEYCODES, \
    KEYCODES_MIDI_CC, KEYCODES_MIDI_BANK, KEYCODES_Program_Change, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_VELOCITY, KEYCODES_Program_Change_UPDOWN, KEYCODES_MIDI_BANK, KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC_FIXED, KEYCODES_OLED, KEYCODES_EARTRAINER, KEYCODES_SAVE, KEYCODES_CHORDTRAINER, \
    KEYCODES_MIDI_OCTAVE2, KEYCODES_MIDI_OCTAVE3, KEYCODES_MIDI_KEY2, KEYCODES_MIDI_KEY3, KEYCODES_MIDI_VELOCITY2, KEYCODES_MIDI_VELOCITY3, KEYCODES_MIDI_ADVANCED, KEYCODES_MIDI_SMARTCHORDBUTTONS, KEYCODES_VELOCITY_STEPSIZE, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD, \
    KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_UPDOWN, KEYCODES_MIDI_CHORD_0, KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_CHORD_5, KEYCODES_MIDI_INVERSION, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN, KEYCODES_MIDI_PEDAL
from widgets.square_button import SquareButton
from widgets.big_square_button import BigSquareButton
from util import tr, KeycodeDisplay

class AsyncValueDialog(QDialog):
    def __init__(self, parent, title, min_val, max_val, callback):
        super().__init__(parent)
        self.callback = callback
        self.setWindowTitle(title)
        self.setFixedSize(300, 150)

        layout = QVBoxLayout(self)
        
        label_widget = QLabel(f"Enter value ({min_val}-{max_val}):")
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText(f"Enter a number between {min_val} and {max_val}")
        
        self.min_val = min_val
        self.max_val = max_val
        self.value_input.textChanged.connect(self.validate_input)
        
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.accept)
        
        layout.addWidget(label_widget)
        layout.addWidget(self.value_input)
        layout.addWidget(confirm_button)

        self.finished.connect(self.on_finished)

    def validate_input(self, text):
        if text and (not text.isdigit() or not (self.min_val <= int(text) <= self.max_val)):
            self.value_input.clear()
            
    def on_finished(self, result):
        if result == QDialog.Accepted and self.value_input.text():
            self.callback(self.value_input.text())
        self.deleteLater()

class AsyncCCDialog(QDialog):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.setWindowTitle("Enter CC Value")
        self.setFixedHeight(170)

        layout = QVBoxLayout(self)

        cc_x_label = QLabel("CC(0-127):")
        self.cc_x_input = QLineEdit()
        self.cc_x_input.textChanged.connect(lambda text: self.validate_input(text, self.cc_x_input))

        cc_y_label = QLabel("Value(0-127):")
        self.cc_y_input = QLineEdit()
        self.cc_y_input.textChanged.connect(lambda text: self.validate_input(text, self.cc_y_input))

        layout.addWidget(cc_x_label)
        layout.addWidget(self.cc_x_input)
        layout.addWidget(cc_y_label)
        layout.addWidget(self.cc_y_input)

        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.accept)
        layout.addWidget(confirm_button)

        self.finished.connect(self.on_finished)

    def validate_input(self, text, input_field):
        if text and (not text.isdigit() or not (0 <= int(text) <= 127)):
            input_field.clear()

    def on_finished(self, result):
        if result == QDialog.Accepted:
            x_value = self.cc_x_input.text()
            y_value = self.cc_y_input.text()
            if x_value and y_value:
                self.callback(int(x_value), int(y_value))
        self.deleteLater()

def show_value_dialog(parent, title, min_val, max_val, callback):
    """Factory function that handles both web and desktop environments"""
    try:
        # Check if we're in web environment
        import emscripten
        # For web, show non-modal dialog
        dialog = AsyncValueDialog(parent, title, min_val, max_val, callback)
        dialog.show()
    except ImportError:
        # For desktop, use traditional modal dialog
        dialog = AsyncValueDialog(parent, title, min_val, max_val, callback)
        dialog.exec_()

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

    GLASS_BLACK = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(40, 40, 40, 255),
                stop:0.5 rgba(30, 30, 30, 255),
                stop:1 rgba(20, 20, 20, 255));
            border: 1px solid rgba(0, 0, 0, 255);
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

    KS_BLACK = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(128, 87, 87, 255),
                stop:0.5 rgba(118, 77, 77, 255),
                stop:1 rgba(108, 67, 67, 255));
            border: 1px solid rgba(88, 47, 47, 255);
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

    TS_BLACK = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(128, 128, 87, 255),
                stop:0.5 rgba(118, 118, 77, 255),
                stop:1 rgba(108, 108, 67, 255));
            border: 1px solid rgba(88, 88, 47, 255);
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

    def __init__(self, parent, label, inversion_keycodes, smartchord_program_change, smartchord_LSB, smartchord_MSB, smartchord_CC_toggle, CCfixed, CCup, CCdown, velocity_multiplier_options, cc_multiplier_options, channel_options, velocity_options, channel_oneshot, channel_hold, smartchord_octave_1, smartchord_key, ksvelocity2, ksvelocity3, kskey2, kskey3, ksoctave2, ksoctave3, kschannel2, kschannel3, inversion_keycodes2, CCencoder, velocityshuffle, inversion_keycodesspecial):
        super().__init__(parent)
        self.label = label
        
        # Initialize dictionaries first
        self.buttons = {}
        self.containers = {}
        
        # Store all the parameters as instance variables
        self.inversion_keycodes = inversion_keycodes
        self.inversion_keycodes2 = inversion_keycodes2  # Add new parameter
        self.inversion_keycodesspecial = inversion_keycodesspecial
        self.smartchord_program_change = smartchord_program_change
        self.smartchord_LSB = smartchord_LSB
        self.smartchord_MSB = smartchord_MSB
        self.smartchord_CC_toggle = smartchord_CC_toggle
        self.CCfixed = CCfixed
        self.CCup = CCup
        self.CCdown = CCdown
        self.CCencoder = CCencoder
        self.velocityshuffle = velocityshuffle
        self.velocity_multiplier_options = velocity_multiplier_options
        self.cc_multiplier_options = cc_multiplier_options
        self.channel_options = channel_options
        self.velocity_options = velocity_options
        self.channel_oneshot = channel_oneshot
        self.channel_hold = channel_hold
        self.smartchord_octave_1 = smartchord_octave_1
        self.smartchord_key = smartchord_key
        self.ksvelocity2 = ksvelocity2
        self.ksvelocity3 = ksvelocity3
        self.kskey2 = kskey2
        self.kskey3 = kskey3
        self.ksoctave2 = ksoctave2
        self.ksoctave3 = ksoctave3
        self.kschannel2 = kschannel2
        self.kschannel3 = kschannel3

        # Create scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setSpacing(60)

        # Create buttons layout with stretches
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(0)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add initial stretch before buttons
        self.button_layout.addStretch(1)

        # Define sections
        sections = [
            "Show\nChannel\nOptions",
            "Show\nCC Options",
            "Show\nTransposition\nSettings",
            "Show\nKeySplit\nOptions",
            "Show\nAdvanced MIDI\nOptions",
            "Show\nVelocity\nOptions",
            "Show\nTouch Dial\nOptions"  # New section
        ]

        # Create buttons and containers for each section
        for section in sections:
            btn = QPushButton(section)
            btn.setFixedSize(80, 50)
            btn.clicked.connect(lambda checked, s=section: self.toggle_section(s))
            self.button_layout.addWidget(btn)
            self.buttons[section] = btn

            # Create container
            container = QWidget()
            container_layout = QVBoxLayout()
            
            # If this is the Show\nAdvanced MIDI\nOptions section
            if section == "Show\nAdvanced MIDI\nOptions":
                advanced_h_layout = QHBoxLayout()
                advanced_h_layout.addStretch(1)
                self.advanced_grid = QGridLayout()
                advanced_h_layout.addLayout(self.advanced_grid)
                advanced_h_layout.addStretch(1)
                container_layout.addLayout(advanced_h_layout)
            
            # If this is the KeySplit section
            elif section == "Show\nKeySplit\nOptions":
                keysplit_h_layout = QHBoxLayout()
                keysplit_h_layout.addStretch(1)
                self.keysplit_grid = QGridLayout()
                keysplit_h_layout.addLayout(self.keysplit_grid)
                keysplit_h_layout.addStretch(1)
                container_layout.addLayout(keysplit_h_layout)
                
            container.setLayout(container_layout)
            container.hide()
            self.main_layout.addWidget(container)
            self.containers[section] = container

        self.button_layout.addStretch(1)
        self.main_layout.insertLayout(0, self.button_layout)
        
        # Add 100 pixel spacer below buttons
        spacer = QWidget()
        spacer.setFixedHeight(100)
        self.main_layout.addWidget(spacer)

        # Populate all sections
        self.populate_channel_section()
        self.populate_cc_velocity_section()
        self.populate_transposition_section()
        self.populate_keysplit_section()  # This will now add the inversion_keycodes2 buttons
        self.populate_advanced_section()
        self.populate_velocity_section()
        self.populate_expression_wheel_section()  # New method call

        self.main_layout.addStretch()

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.toggle_section(sections[0])

    def populate_keysplit_section(self):
        """Populate the KeySplit section with dropdowns and buttons."""
        # Add dropdowns
        layout = QHBoxLayout()
        self.add_header_dropdown2("Key Switch\nVelocity", self.ksvelocity2, layout)
        self.add_header_dropdown2("Key Switch\nOctave", self.ksoctave2, layout)
        self.add_header_dropdown2("Key Switch\nKey", self.kskey2, layout)
        self.add_header_dropdown2("Key Switch\nChannel", self.kschannel2, layout)
        self.add_value_button2("Triple Switch\nVelocity", self.ksvelocity3, layout)
        self.add_header_dropdown2("Triple Switch\nOctave", self.ksoctave3, layout)
        self.add_header_dropdown2("Triple Switch\nKey", self.kskey3, layout)
        self.add_header_dropdown2("Triple Switch\nChannel", self.kschannel3, layout)
        self.keysplit_dropdowns.addLayout(layout)

        # Clear existing buttons
        for i in reversed(range(self.keysplit_grid.count())):
            widget = self.keysplit_grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Add buttons in a grid layout
        row = 0
        col = 0
        max_cols = 4

        for keycode in self.inversion_keycodes2:
            btn = SquareButton()
            btn.setFixedSize(55, 55)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            
            self.keysplit_grid.addWidget(btn, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def populate_advanced_section(self):
        """Populate the Show\nAdvanced MIDI\nOptions section with inversion buttons."""
        # Clear existing buttons
        for i in reversed(range(self.advanced_grid.count())):
            widget = self.advanced_grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Add inversion buttons in a grid layout
        row = 0
        col = 0
        max_cols = 8  # Adjust this value to change number of columns

        for keycode in self.inversion_keycodes:
            btn = SquareButton()
            btn.setFixedSize(55, 55)  # Set fixed size for inversion buttons
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            
            self.advanced_grid.addWidget(btn, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1


    # Add new populate_velocity_section method
    def populate_velocity_section(self):
        
        container = self.containers["Show\nVelocity\nOptions"]
        layout = container.layout()
        
        velocity_layout = QHBoxLayout()
        self.add_value_button("Set Velocity", self.velocity_options, velocity_layout)
        self.add_header_dropdown("Velocity Increment", self.velocity_multiplier_options, velocity_layout)
        self.add_header_dropdown("Velocity Shuffle", self.velocityshuffle, velocity_layout)
        layout.addLayout(velocity_layout)
        layout.addStretch()
  
    def populate_expression_wheel_section(self):
        """Populate the Touch Dial Options section."""
        container = self.containers["Show\nTouch Dial\nOptions"]
        layout = container.layout()
        
        # First row: Touch Dial controls
        top_row_layout = QHBoxLayout()
        top_row_layout.addStretch(1)  # Add stretch before buttons
        
        # Create grid layout for the Touch Dial buttons
        button_grid = QGridLayout()
        button_grid.setSpacing(4)
        
        # Create Touch Dial CC button
        cc_button = QPushButton("Touch\nDial\nCC")
        cc_button.setFixedSize(80, 80)
        cc_button.clicked.connect(lambda: self.open_value_dialog("Touch Dial CC", self.CCencoder))
        button_grid.addWidget(cc_button, 0, 0)
        
        # Add the three special inversion buttons
        col = 1
        for keycode in self.inversion_keycodesspecial:
            btn = SquareButton()
            btn.setFixedSize(80, 80)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            button_grid.addWidget(btn, 0, col)
            col += 1
        
        top_row_layout.addLayout(button_grid)
        top_row_layout.addStretch(1)  # Add stretch after buttons
        
        # Second row: Dropdowns
        bottom_row_layout = QHBoxLayout()
        
        # Add Velocity Up/Down Increment dropdown
        self.add_header_dropdown("Velocity Increment", self.velocity_multiplier_options, bottom_row_layout)
        
        # Add CC Up/Down Increment dropdown
        self.add_header_dropdown("CC Increment", self.cc_multiplier_options, bottom_row_layout)
        
        # Add rows to the main container
        layout.addLayout(top_row_layout)
        
        # Add spacing between rows
        spacer = QWidget()
        spacer.setFixedHeight(20)
        layout.addWidget(spacer)
        
        layout.addLayout(bottom_row_layout)
        layout.addStretch()

    def toggle_section(self, section_name):
        # Reset all buttons and hide all containers
        for btn in self.buttons.values():
            btn.setStyleSheet("")
        for container in self.containers.values():
            container.hide()

        # Show selected section and highlight button
        self.containers[section_name].show()
        self.buttons[section_name].setStyleSheet("""
            background-color: #B8D8EB;
            color: #395968;
        """)

    def populate_channel_section(self):
        layout = QHBoxLayout()
        self.add_header_dropdown("MIDI Channel", self.channel_options, layout)
        self.add_header_dropdown("Temporary MIDI Channel", self.channel_oneshot, layout)
        self.add_header_dropdown("Hold MIDI Channel", self.channel_hold, layout)
        self.containers["Show\nChannel\nOptions"].layout().addLayout(layout)

    def populate_cc_velocity_section(self):
        layout = QHBoxLayout()
        self.add_cc_x_y_menu(layout)
        self.add_value_button("CC On/Off", self.smartchord_CC_toggle, layout)
        self.add_value_button("CC Up", self.CCup, layout)
        self.add_value_button("CC Down", self.CCdown, layout)
        self.add_value_button("Touch Dial CC", self.CCencoder, layout)
        self.add_header_dropdown("CC Increment", self.cc_multiplier_options, layout)
        self.add_value_button("Program Change", self.smartchord_program_change, layout)
        self.add_value_button("Bank LSB", self.smartchord_LSB, layout)
        self.add_value_button("Bank MSB", self.smartchord_MSB, layout)
        self.containers["Show\nCC Options"].layout().addLayout(layout)

    def populate_transposition_section(self):
        layout = QHBoxLayout()
        self.add_header_dropdown("Octave Selector", self.smartchord_octave_1, layout)
        self.add_header_dropdown("Key Selector", self.smartchord_key, layout)
        self.containers["Show\nTransposition\nSettings"].layout().addLayout(layout)

    def populate_keysplit_section(self):
        # Get the container and its layout
        container = self.containers["Show\nKeySplit\nOptions"]
        container_layout = container.layout()

        # 1. First add dropdowns in a horizontal layout
        dropdown_layout = QHBoxLayout()
        self.add_value_button2("Key Switch\nVelocity", self.ksvelocity2, dropdown_layout)
        self.add_header_dropdown2("Key Switch\nOctave", self.ksoctave2, dropdown_layout)
        self.add_header_dropdown2("Key Switch\nKey", self.kskey2, dropdown_layout)
        self.add_header_dropdown2("Key Switch\nChannel", self.kschannel2, dropdown_layout)
        self.add_value_button2("Triple Switch\nVelocity", self.ksvelocity3, dropdown_layout)
        self.add_header_dropdown2("Triple Switch\nOctave", self.ksoctave3, dropdown_layout)
        self.add_header_dropdown2("Triple Switch\nKey", self.kskey3, dropdown_layout)
        self.add_header_dropdown2("Triple Switch\nChannel", self.kschannel3, dropdown_layout)
        container_layout.addLayout(dropdown_layout)

        # 2. Then add buttons in a centered grid layout
        button_container = QHBoxLayout()
        button_container.addStretch(1)
        self.keysplit_grid = QGridLayout()
        self.keysplit_grid.setSpacing(4)  # Add some spacing between buttons

        # Add buttons to the grid
        row = 0
        col = 0
        max_cols = 8

        for keycode in self.inversion_keycodes2:
            btn = SquareButton()
            btn.setFixedSize(55, 55)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            
            self.keysplit_grid.addWidget(btn, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        button_container.addLayout(self.keysplit_grid)
        button_container.addStretch(1)
        container_layout.addLayout(button_container)

    def add_header_dropdown(self, label_text, items, layout):
        dropdown = QComboBox()
        dropdown.addItems(items)
        label = QLabel(label_text)
        layout.addWidget(label)
        layout.addWidget(dropdown)
        
    def add_header_dropdown2(self, label_text, items, layout):
        dropdown = QComboBox()
        dropdown.addItems(items)
        label = QLabel(label_text)
        layout.addWidget(label)
        layout.addWidget(dropdown)

    def add_value_button(self, label_text, keycode_set, layout):
            """Create a button that opens a dialog to input a value for the corresponding keycode."""
            button = QPushButton(label_text)
            button.setFixedHeight(40)
            
            def handle_value(value):
                if value and value.isdigit() and 0 <= int(value) <= 127:
                    keycode_map = {
                        "CC On/Off": f"MI_CC_{value}_TOG",
                        "CC Up": f"MI_CC_{value}_UP",
                        "CC Down": f"MI_CC_{value}_DWN",
                        "Touch Dial CC": f"MI_CCENCODER_{value}",
                        "Program Change": f"MI_PROG_{value}",
                        "Bank LSB": f"MI_BANK_LSB_{value}",
                        "Bank MSB": f"MI_BANK_MSB_{value}",
                        "Set Velocity": f"MI_VELOCITY_{value}",
                        "Key Switch\nVelocity": f"MI_VELOCITY2_{value}",
                        "Triple Switch\nVelocity": f"MI_VELOCITY3_{value}"
                    }
                    
                    if label_text in keycode_map:
                        self.keycode_changed.emit(keycode_map[label_text])
            
            button.clicked.connect(lambda: show_value_dialog(
                self,
                f"Set Value for {label_text}",
                0,
                127,
                handle_value
            ))
            layout.addWidget(button)
        
    def add_value_button2(self, label_text, keycode_set, layout):
        """Create a button that opens a dialog to input a value for the corresponding keycode."""
        button = QPushButton(label_text)
        button.setFixedHeight(60)
        
        def handle_value(value):
            if value and value.isdigit() and 0 <= int(value) <= 127:
                keycode_map = {
                    "Key Switch\nVelocity": f"MI_VELOCITY2_{value}",
                    "Triple Switch\nVelocity": f"MI_VELOCITY3_{value}"
                }
                
                if label_text in keycode_map:
                    self.keycode_changed.emit(keycode_map[label_text])
        
        button.clicked.connect(lambda: show_value_dialog(
            self,
            f"Set Value for {label_text}",
            0,
            127,
            handle_value
        ))
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
                "Touch Dial CC": f"MI_CCENCODER_{value}",
                "Program Change": f"MI_PROG_{value}",
                "Bank LSB": f"MI_BANK_LSB_{value}",
                "Bank MSB": f"MI_BANK_MSB_{value}",
                "Set Velocity": f"MI_VELOCITY_{value}",
                "Key Switch\nVelocity": f"MI_VELOCITY2_{value}",
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
        def handle_cc_values(x, y):
            self.keycode_changed.emit(f"MI_CC_{x}_{y}")

        try:
            import emscripten
            dialog = AsyncCCDialog(self, handle_cc_values)
            dialog.show()
        except ImportError:
            dialog = AsyncCCDialog(self, handle_cc_values)
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
        
    def add_header_dropdown2(self, header_text, keycodes, layout):
        """Helper method to add a header and dropdown side by side."""
        # Create a vertical layout to hold header and dropdown
        vbox = QVBoxLayout()

        # Create header
        header_label = QLabel(header_text)
        header_label.setAlignment(Qt.AlignCenter)
        #vbox.addWidget(header_label)

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(60)  # Set height of dropdown

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
        """Update to include both advanced and keysplit section buttons."""
        # Clear and recreate the advanced section
        for i in reversed(range(self.advanced_grid.count())):
            widget = self.advanced_grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Clear and recreate the keysplit section
        for i in reversed(range(self.keysplit_grid.count())):
            widget = self.keysplit_grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Repopulate advanced section
        row = 0
        col = 0
        max_cols = 8

        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedSize(55, 55)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                
                self.advanced_grid.addWidget(btn, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        # Repopulate keysplit section
        row = 0
        col = 0

        for keycode in self.inversion_keycodes2:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedSize(55, 55)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                
                self.keysplit_grid.addWidget(btn, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
        

    def relabel_buttons(self):
        # Only need to relabel buttons in the advanced section
        advanced_container = self.containers["Show\nAdvanced MIDI\nOptions"]
        for i in range(advanced_container.layout().count()):
            item = advanced_container.layout().itemAt(i)
            if isinstance(item, QGridLayout):
                for j in range(item.count()):
                    widget = item.itemAt(j).widget()
                    if isinstance(widget, SquareButton) and hasattr(widget, 'keycode'):
                        widget.setText(Keycode.label(widget.keycode.qmk_id))

    def has_buttons(self):
        return True

    def on_selection_change(self, index):
        selected_qmk_id = self.sender().itemData(index)
        if selected_qmk_id:
            self.keycode_changed.emit(selected_qmk_id)
        
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
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        # Toggle buttons with center alignment
        button_layout = QHBoxLayout()
        button_layout.setSpacing(0)  # No spacing between buttons
        
        # Add stretch before buttons
        button_layout.addStretch(1)
        
        self.toggle_intervals = QPushButton("Inverval Trainer")
        self.toggle_intervals.clicked.connect(self.show_intervals)
        self.toggle_intervals.setFixedSize(120, 40)
        button_layout.addWidget(self.toggle_intervals)
        
        self.toggle_chords = QPushButton("Chord Trainer")
        self.toggle_chords.clicked.connect(self.show_chords)
        self.toggle_chords.setFixedSize(120, 40)
        button_layout.addWidget(self.toggle_chords)
        
        # Add stretch after buttons
        button_layout.addStretch(1)
        
        self.main_layout.addLayout(button_layout)
        
        # Container for button sections with horizontal centering
        self.intervals_container = QWidget()
        intervals_outer_layout = QHBoxLayout(self.intervals_container)
        intervals_outer_layout.addStretch(1)  # Left spacer
        self.intervals_grid = QGridLayout()
        self.intervals_grid.setSpacing(10)
        intervals_outer_layout.addLayout(self.intervals_grid)
        intervals_outer_layout.addStretch(1)  # Right spacer
        self.main_layout.addWidget(self.intervals_container)
        
        self.chords_container = QWidget()
        chords_outer_layout = QHBoxLayout(self.chords_container)
        chords_outer_layout.addStretch(1)  # Left spacer
        self.chords_grid = QGridLayout()
        self.chords_grid.setSpacing(10)
        chords_outer_layout.addLayout(self.chords_grid)
        chords_outer_layout.addStretch(1)  # Right spacer
        self.main_layout.addWidget(self.chords_container)
        self.chords_container.hide()
        
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        
        # Show intervals by default and highlight its button
        self.show_intervals()
        self.recreate_buttons()

    def show_intervals(self):
        self.intervals_container.show()
        self.chords_container.hide()
        self.toggle_intervals.setStyleSheet("""
            background-color: #B8D8EB;
            color: #395968;
        """)
        self.toggle_chords.setStyleSheet("")  # Reset to default

    def show_chords(self):
        self.intervals_container.hide()
        self.chords_container.show()
        self.toggle_chords.setStyleSheet("""
            background-color: #C9E4CA;
            color: #4A654B;
        """)
        self.toggle_intervals.setStyleSheet("")  # Reset to default

    def recreate_buttons(self, keycode_filter=None):
        # Clear existing layouts
        while self.intervals_grid.count():
            item = self.intervals_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        while self.chords_grid.count():
            item = self.chords_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create Interval Trainer buttons (4 columns)
        for i, keycode in enumerate(self.eartrainer_keycodes):
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                row = i // 4
                col = i % 4
                btn = QPushButton(Keycode.label(keycode.qmk_id))
                btn.setFixedSize(80, 50)
                btn.setStyleSheet("background-color: #B8D8EB; color: #395968;")
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                self.intervals_grid.addWidget(btn, row, col)

        # Create Chord Trainer buttons (5 columns)
        for i, keycode in enumerate(self.chordtrainer_keycodes):
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                row = i // 5
                col = i % 5
                btn = QPushButton(Keycode.label(keycode.qmk_id))
                btn.setFixedSize(80, 50)
                btn.setStyleSheet("background-color: #C9E4CA; color: #4A654B;")
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                self.chords_grid.addWidget(btn, row, col)

    def relabel_buttons(self):
        for grid in [self.intervals_grid, self.chords_grid]:
            for i in range(grid.count()):
                widget = grid.itemAt(i).widget()
                if hasattr(widget, 'keycode'):
                    widget.setText(Keycode.label(widget.keycode.qmk_id))

    def has_buttons(self):
        return (self.intervals_grid.count() > 0 or 
                self.chords_grid.count() > 0)



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
            dropdown.currentIndexChanged.connect(self.on_selection_change)
            dropdown.currentIndexChanged.connect(lambda _, d=dropdown, h=header_text: self.reset_dropdown(d, h))
            
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

    def __init__(self, parent, label, inversion_keycodes, inversion_keycodes4, smartchord_LSB, smartchord_MSB, smartchord_LSB2):
        super().__init__(parent)
        self.label = label     
        self.inversion_keycodes = inversion_keycodes
        self.inversion_keycodes4 = inversion_keycodes4
        self.smartchord_LSB = smartchord_LSB
        self.smartchord_MSB = smartchord_MSB
        self.smartchord_LSB2 = smartchord_LSB2

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

        # First row - exactly as original
        # Add RGB Mode dropdown
        dropdown1 = ScrollableComboBox()
        dropdown1.setFixedHeight(40)
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
        dropdown1.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown1, "RGB Mode"))
        self.button_layout.addWidget(dropdown1, row, col)
        col += 1

        # Add RGB Color dropdown
        dropdown2 = ScrollableComboBox()
        dropdown2.setFixedHeight(40)
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
        dropdown2.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown2, "RGB Color"))
        self.button_layout.addWidget(dropdown2, row, col)
        col += 1
        
        # Add RGB Layer Save dropdown (slightly wider than first row dropdowns)
        dropdown3 = ScrollableComboBox()
        dropdown3.setFixedHeight(40)
        dropdown3.addItem("Record Layer RGB")
        for keycode in self.smartchord_LSB2:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                label = Keycode.label(keycode.qmk_id)
                tooltip = Keycode.description(keycode.qmk_id)
                dropdown3.addItem(label, keycode.qmk_id)
                item = dropdown3.model().item(dropdown3.count() - 1)
                item.setToolTip(tooltip)
        dropdown3.model().item(0).setEnabled(False)
        dropdown3.currentIndexChanged.connect(self.on_selection_change)
        dropdown3.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown3, "RGB Layer Save"))
        self.button_layout.addWidget(dropdown3, row, col)
        col += 1

        

        # Add first row buttons
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(40)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                self.button_layout.addWidget(btn, row, col)
                col += 1
                    
        for keycode in self.inversion_keycodes4:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(40)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                self.button_layout.addWidget(btn, row, col)
                col += 1


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
        """Open a dialog to input a value between 0 and the max allowed value."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Set Value for {label}")
        dialog.setFixedSize(300, 150)

        # Set max value based on the button type
        max_value = 100 if label == "Tapdance Selection" else 255
        
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
        max_value = 100 if label == "Tapdance Selection" else 255
        
        if value.isdigit() and 0 <= int(value) <= max_value:
            keycode_map = {
                "Tapdance Selection": f"TD({value})",
                "Macro Selection": f"M{value}"
            }
            
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
        
        # Main layout with minimal spacing
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setSpacing(0)  # Set consistent 10px spacing
       
        # Toggle buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(0)
        button_layout.addStretch(1)
        
        self.toggle_button = QPushButton("Show KeySplit")
        self.toggle_button.clicked.connect(self.toggle_midi_layouts)
        self.toggle_button.setFixedSize(120, 40)
        self.toggle_button.setStyleSheet("background-color: #f3d1d1; color: #805757;")
        button_layout.addWidget(self.toggle_button)
        
        self.toggle_button2 = QPushButton("Show TripleSplit")
        self.toggle_button2.clicked.connect(self.toggle_midi_layouts2)
        self.toggle_button2.setFixedSize(120, 40)
        button_layout.addWidget(self.toggle_button2)
        button_layout.addStretch(1)
        
        # Add layouts with explicit spacing
        self.main_layout.addLayout(button_layout)

        # Piano keyboards
        self.keysplit_piano = PianoKeyboard(color_scheme='keysplit')
        self.keysplit_piano.keyPressed.connect(self.keycode_changed)
        self.main_layout.addWidget(self.keysplit_piano)
        
        self.triplesplit_piano = PianoKeyboard(color_scheme='triplesplit')
        self.triplesplit_piano.keyPressed.connect(self.keycode_changed)
        self.main_layout.addWidget(self.triplesplit_piano)
        self.triplesplit_piano.hide()
        
        # Control buttons
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

        # Add the split buttons at the bottom
        split_buttons_container = QWidget()
        split_buttons_layout = QHBoxLayout(split_buttons_container)
        split_buttons_layout.setAlignment(Qt.AlignCenter)
        
        split_buttons = [
            ("Channel\nSplit", "MI_Cs"),
            ("Velocity\nSplit", "MI_Vs"),
            ("Transpose\nSplit", "MI_Ts")
        ]
        
        for text, code in split_buttons:
            btn = QPushButton(text)
            btn.setFixedSize(60, 60)  # Increased from 50x50 to 60x60
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
            btn.clicked.connect(lambda _, k=code: self.keycode_changed.emit(k))
            split_buttons_layout.addWidget(btn)
            
        self.main_layout.addWidget(split_buttons_container)

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def relabel_buttons(self):
        """Relabel all piano keys and control buttons"""
        # Relabel KeySplit piano keys
        for key in self.keysplit_piano.white_keys + self.keysplit_piano.black_keys:
            if hasattr(key, 'midi_id'):
                key.setText(Keycode.label(key.midi_id))

        # Relabel TripleSplit piano keys
        for key in self.triplesplit_piano.white_keys + self.triplesplit_piano.black_keys:
            if hasattr(key, 'midi_id'):
                key.setText(Keycode.label(key.midi_id))

        # Relabel control buttons
        for controls in [self.ks_controls, self.ts_controls]:
            layout = controls.layout()
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QPushButton) and hasattr(widget, 'midi_id'):
                    widget.setText(Keycode.label(widget.midi_id))

    def create_piano_keys(self, midi_mappings, key_prefix='MI'):
        """Modified create_piano_keys method to store midi_id"""
        # ... (previous piano key creation code) ...
        # Add this line when creating each key:
        key.midi_id = midi_id  # Store the midi_id for relabeling

    def create_control_buttons(self, layout, prefix):
        controls = [
            (f"{prefix}\nChannel\n-", f"{'KS2' if prefix == 'TS' else prefix}_CHAN_DOWN"),
            (f"{prefix}\nChannel\n+", f"{'KS2' if prefix == 'TS' else prefix}_CHAN_UP"),
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
            btn.midi_id = code
            
            # Set only background color and text color
            if prefix == 'KS':
                btn.setStyleSheet("background-color: rgba(243, 209, 209, 1); color: rgba(128, 87, 87, 1);")
            else:
                btn.setStyleSheet("background-color: rgba(209, 243, 215, 1); color: rgba(128, 128, 87, 1);")
                
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
        self.white_key_height = 80
        self.black_key_width = 31
        self.black_key_height = 55
        self.row_spacing = 15
        
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
            ["KC_NO", "MI_ALLOFF", "MI_SUS", "MI_CHORD_99", "KC_NO", "SAVE_SETTINGS", "DEFAULT_SETTINGS"]
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
            elif item == "SAVE_SETTINGS":
                btn.setText("Save\nSettings")
            elif item == "DEFAULT_SETTINGS":
                btn.setText("Reset\nDefault\nSettings")
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
            LightingTab(self, "Lighting", KEYCODES_BACKLIGHT, KEYCODES_RGBSAVE, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_COLOR, KEYCODES_RGB_KC_CUSTOM2),            
            LayerTab(self, "Layers", KEYCODES_LAYERS, KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_TG, KEYCODES_LAYERS_TT, KEYCODES_LAYERS_OSL, KEYCODES_LAYERS_TO),
            midiTab(self, "MIDIswitch", KEYCODES_MIDI_UPDOWN),   # Updated to SmartChordTab
            SmartChordTab(self, "SmartChord", KEYCODES_MIDI_CHORD_0, KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_CHORD_5, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_SMARTCHORDBUTTONS+KEYCODES_MIDI_INVERSION),
            KeySplitTab(self, "KeySplit", KEYCODES_KEYSPLIT_BUTTONS),   # Updated to SmartChordTa
            EarTrainerTab(self, "Ear Training", KEYCODES_EARTRAINER, KEYCODES_CHORDTRAINER), 
            midiadvancedTab(self, "MIDI Advanced",  KEYCODES_MIDI_ADVANCED, KEYCODES_Program_Change, KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC, KEYCODES_MIDI_CC_FIXED, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN, KEYCODES_VELOCITY_STEPSIZE, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_VELOCITY, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD, KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_VELOCITY2, KEYCODES_MIDI_VELOCITY3, KEYCODES_MIDI_KEY2, KEYCODES_MIDI_KEY3, KEYCODES_MIDI_OCTAVE2, KEYCODES_MIDI_OCTAVE3, KEYCODES_MIDI_CHANNEL_KEYSPLIT, KEYCODES_MIDI_CHANNEL_KEYSPLIT2, KEYCODES_MIDI_SPLIT_BUTTONS, KEYCODES_CC_ENCODERVALUE, KEYCODES_VELOCITY_SHUFFLE, KEYCODES_EXWHEEL),
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
