# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtWidgets import QTabWidget, QWidget, QScrollArea, QApplication, QVBoxLayout, QHBoxLayout, QComboBox, QSizePolicy, QLabel, QGridLayout, QStyleOptionComboBox, QDialog, QLineEdit, QFrame, QListView, QScrollBar, QPushButton, QSlider, QGroupBox, QMessageBox
from PyQt5.QtGui import QPalette, QPainter, QPolygon, QPen, QColor, QBrush, QPixmap, QPainterPath, QRegion

from constants import KEYCODE_BTN_RATIO
from widgets.display_keyboard import DisplayKeyboard
from widgets.display_keyboard_defs import ansi_100, ansi_80, ansi_70, iso_100, iso_80, iso_70, mods, mods_narrow, midi_layout
from widgets.combo_box import ArrowComboBox
from widgets.flowlayout import FlowLayout
from keycodes.keycodes import KEYCODES_BASIC, KEYCODES_ISO, KEYCODES_MACRO, KEYCODES_MACRO_BASE, KEYCODES_LAYERS, KEYCODES_QUANTUM, \
    KEYCODES_BOOT, KEYCODES_MODIFIERS, KEYCODES_CLEAR, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_CUSTOM2, KEYCODES_RGBSAVE, KEYCODES_EXWHEEL, KEYCODES_RGB_KC_COLOR, KEYCODES_MIDI_SPLIT_BUTTONS, KEYCODES_SETTINGS1, KEYCODES_SETTINGS2, KEYCODES_SETTINGS3, KEYCODES_BASIC, KEYCODES_SHIFTED, KEYCODES_CHORD_PROG_CONTROLS, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD, KEYCODES_C_CHORDPROG_BASIC_MINOR, KEYCODES_C_CHORDPROG_BASIC_MAJOR, KEYCODES_C_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_C_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_C_CHORDPROG_EXPERT_MINOR, KEYCODES_C_CHORDPROG_EXPERT_MAJOR, KEYCODES_C_SHARP_CHORDPROG_BASIC_MINOR, KEYCODES_C_SHARP_CHORDPROG_BASIC_MAJOR, KEYCODES_C_SHARP_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_C_SHARP_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_C_SHARP_CHORDPROG_EXPERT_MINOR, KEYCODES_C_SHARP_CHORDPROG_EXPERT_MAJOR, KEYCODES_D_CHORDPROG_BASIC_MINOR, KEYCODES_D_CHORDPROG_BASIC_MAJOR, KEYCODES_D_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_D_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_D_CHORDPROG_EXPERT_MINOR, KEYCODES_D_CHORDPROG_EXPERT_MAJOR, KEYCODES_E_FLAT_CHORDPROG_BASIC_MINOR, KEYCODES_E_FLAT_CHORDPROG_BASIC_MAJOR, KEYCODES_E_FLAT_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_E_FLAT_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_E_FLAT_CHORDPROG_EXPERT_MINOR, KEYCODES_E_FLAT_CHORDPROG_EXPERT_MAJOR, KEYCODES_E_CHORDPROG_BASIC_MINOR, KEYCODES_E_CHORDPROG_BASIC_MAJOR, KEYCODES_E_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_E_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_E_CHORDPROG_EXPERT_MINOR, KEYCODES_E_CHORDPROG_EXPERT_MAJOR, KEYCODES_F_CHORDPROG_BASIC_MINOR, KEYCODES_F_CHORDPROG_BASIC_MAJOR, KEYCODES_F_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_F_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_F_CHORDPROG_EXPERT_MINOR, KEYCODES_F_CHORDPROG_EXPERT_MAJOR, KEYCODES_F_SHARP_CHORDPROG_BASIC_MINOR, KEYCODES_F_SHARP_CHORDPROG_BASIC_MAJOR, KEYCODES_F_SHARP_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_F_SHARP_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_F_SHARP_CHORDPROG_EXPERT_MINOR, KEYCODES_F_SHARP_CHORDPROG_EXPERT_MAJOR, KEYCODES_G_CHORDPROG_BASIC_MINOR, KEYCODES_G_CHORDPROG_BASIC_MAJOR, KEYCODES_G_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_G_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_G_CHORDPROG_EXPERT_MINOR, KEYCODES_G_CHORDPROG_EXPERT_MAJOR, KEYCODES_A_FLAT_CHORDPROG_BASIC_MINOR, KEYCODES_A_FLAT_CHORDPROG_BASIC_MAJOR, KEYCODES_A_FLAT_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_A_FLAT_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_A_FLAT_CHORDPROG_EXPERT_MINOR, KEYCODES_A_FLAT_CHORDPROG_EXPERT_MAJOR, KEYCODES_A_CHORDPROG_BASIC_MINOR, KEYCODES_A_CHORDPROG_BASIC_MAJOR, KEYCODES_A_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_A_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_A_CHORDPROG_EXPERT_MINOR, KEYCODES_A_CHORDPROG_EXPERT_MAJOR, KEYCODES_B_FLAT_CHORDPROG_BASIC_MINOR, KEYCODES_B_FLAT_CHORDPROG_BASIC_MAJOR, KEYCODES_B_FLAT_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_B_FLAT_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_B_FLAT_CHORDPROG_EXPERT_MINOR, KEYCODES_B_FLAT_CHORDPROG_EXPERT_MAJOR, KEYCODES_B_CHORDPROG_BASIC_MINOR, KEYCODES_B_CHORDPROG_BASIC_MAJOR, KEYCODES_B_CHORDPROG_INTERMEDIATE_MINOR, KEYCODES_B_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_B_CHORDPROG_EXPERT_MINOR, KEYCODES_B_CHORDPROG_EXPERT_MAJOR, \
    KEYCODES_BACKLIGHT, KEYCODES_MEDIA, KEYCODES_SPECIAL, KEYCODES_SHIFTED, KEYCODES_USER, Keycode, KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_TG, KEYCODES_LAYERS_TT, KEYCODES_LAYERS_OSL, KEYCODES_LAYERS_TO, KEYCODES_LAYERS_LT, KEYCODES_VELOCITY_SHUFFLE, KEYCODES_CC_ENCODERVALUE, KEYCODES_LOOP_BUTTONS, KEYCODES_GAMING, \
    KEYCODES_DAW_ABLETON, KEYCODES_DAW_FL, KEYCODES_DAW_LOGIC, KEYCODES_DAW_PROTOOLS, KEYCODES_DAW_GARAGEBAND, \
    KEYCODES_TAP_DANCE, KEYCODES_MIDI, KEYCODES_MIDI_SPLIT, KEYCODES_MIDI_SPLIT2, KEYCODES_MIDI_CHANNEL_KEYSPLIT, KEYCODES_KEYSPLIT_BUTTONS, KEYCODES_MIDI_CHANNEL_KEYSPLIT2, KEYCODES_BASIC_NUMPAD, KEYCODES_BASIC_NAV, KEYCODES_ISO_KR, BASIC_KEYCODES, \
    KEYCODES_ARPEGGIATOR, KEYCODES_ARPEGGIATOR_PRESETS, KEYCODES_STEP_SEQUENCER, KEYCODES_STEP_SEQUENCER_PRESETS, KEYCODES_DKS, \
    KEYCODES_MIDI_CC, KEYCODES_MIDI_BANK, KEYCODES_Program_Change, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_VELOCITY, KEYCODES_Program_Change_UPDOWN, KEYCODES_MIDI_BANK, KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC_FIXED, KEYCODES_OLED, KEYCODES_EARTRAINER, KEYCODES_SAVE, KEYCODES_CHORDTRAINER, \
    KEYCODES_MIDI_OCTAVE2, KEYCODES_MIDI_OCTAVE3, KEYCODES_MIDI_KEY2, KEYCODES_MIDI_KEY3, KEYCODES_MIDI_VELOCITY2, KEYCODES_MIDI_VELOCITY3, KEYCODES_MIDI_ADVANCED, KEYCODES_MIDI_SMARTCHORDBUTTONS, KEYCODES_VELOCITY_STEPSIZE, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD, \
    KEYCODES_HE_VELOCITY_CURVE, KEYCODES_HE_VELOCITY_RANGE, \
    KEYCODES_MIDI_CHANNEL, KEYCODES_MIDI_UPDOWN, KEYCODES_MIDI_CHORD_0, KEYCODES_MIDI_CHORD_1, KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4, KEYCODES_MIDI_CHORD_5, KEYCODES_MIDI_INVERSION, KEYCODES_MIDI_SCALES, KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN, KEYCODES_MIDI_PEDAL, KEYCODES_MIDI_INOUT
from widgets.square_button import SquareButton
from widgets.big_square_button import BigSquareButton
from util import tr, KeycodeDisplay
import widgets.resources  # Import Qt resources for controller images

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

class AsyncHERangeDialog(QDialog):
    """Dialog for setting HE velocity min and max range"""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.setWindowTitle("Set Dynamic Velocity Range")
        self.setFixedSize(350, 200)

        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Set the HE velocity range (1-127):")
        layout.addWidget(instructions)

        # Min value input
        min_label = QLabel("Minimum Velocity:")
        self.min_input = QLineEdit()
        self.min_input.setPlaceholderText("Enter min value (1-127)")
        self.min_input.textChanged.connect(lambda text: self.validate_input(text, self.min_input))

        layout.addWidget(min_label)
        layout.addWidget(self.min_input)

        # Max value input
        max_label = QLabel("Maximum Velocity:")
        self.max_input = QLineEdit()
        self.max_input.setPlaceholderText("Enter max value (1-127)")
        self.max_input.textChanged.connect(lambda text: self.validate_input(text, self.max_input))

        layout.addWidget(max_label)
        layout.addWidget(self.max_input)

        # Confirm button
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.accept)
        layout.addWidget(confirm_button)

        self.finished.connect(self.on_finished)

    def validate_input(self, text, input_field):
        """Validate that input is a number between 1 and 127"""
        if text and (not text.isdigit() or not (1 <= int(text) <= 127)):
            input_field.clear()

    def on_finished(self, result):
        if result == QDialog.Accepted:
            min_val = self.min_input.text()
            max_val = self.max_input.text()
            if min_val and max_val:
                if int(min_val) <= int(max_val):
                    self.callback(min_val, max_val)
        self.deleteLater()

class HERangeDialog(QDialog):
    """Sync version of HE Range Dialog for desktop"""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.setWindowTitle("Set Dynamic Velocity Range")
        self.setFixedSize(350, 200)

        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Set the HE velocity range (1-127):")
        layout.addWidget(instructions)

        # Min value input
        min_label = QLabel("Minimum Velocity:")
        self.min_input = QLineEdit()
        self.min_input.setPlaceholderText("Enter min value (1-127)")

        layout.addWidget(min_label)
        layout.addWidget(self.min_input)

        # Max value input
        max_label = QLabel("Maximum Velocity:")
        self.max_input = QLineEdit()
        self.max_input.setPlaceholderText("Enter max value (1-127)")

        layout.addWidget(max_label)
        layout.addWidget(self.max_input)

        # Confirm button
        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.on_confirm)
        layout.addWidget(confirm_button)

    def on_confirm(self):
        min_val = self.min_input.text()
        max_val = self.max_input.text()
        if min_val and max_val and min_val.isdigit() and max_val.isdigit():
            min_int = int(min_val)
            max_int = int(max_val)
            if 1 <= min_int <= 127 and 1 <= max_int <= 127 and min_int <= max_int:
                self.callback(min_val, max_val)
                self.accept()

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

class CenteredComboBox(ArrowComboBox):
    """ComboBox with centered text and arrow drawn programmatically"""

    def paintEvent(self, event):
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        painter = QPainter(self)
        self.style().drawComplexControl(self.style().CC_ComboBox, opt, painter, self)

        # Center the text horizontally
        text_rect = self.style().subControlRect(self.style().CC_ComboBox, opt, self.style().SC_ComboBoxEditField, self)
        painter.drawText(text_rect, Qt.AlignCenter, self.currentText())

        # Draw dropdown arrow (from ArrowComboBox)
        arrow_rect = self.style().subControlRect(self.style().CC_ComboBox, opt, self.style().SC_ComboBoxArrow, self)
        arrow_center_x = arrow_rect.center().x()
        arrow_center_y = arrow_rect.center().y()

        arrow_size = 4
        arrow = QPolygon([
            QPoint(arrow_center_x - arrow_size, arrow_center_y - 2),
            QPoint(arrow_center_x + arrow_size, arrow_center_y - 2),
            QPoint(arrow_center_x, arrow_center_y + 3)
        ])

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.palette().color(QPalette.Text)))
        painter.drawPolygon(arrow)

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
        
        # Center the button layout
        button_container = QHBoxLayout()
        button_container.addStretch(1)  # Left spacer
        button_container.addLayout(self.button_layout)
        button_container.addStretch(1)  # Right spacer
        
        self.main_layout.addLayout(button_container)

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
            # Use the third value (description) and replace newlines with spaces
            try:
                # For table items, use the third element (description) with newlines replaced
                label_text = str(Keycode.description(keycode.qmk_id)).replace("\n", "  ")
            except Exception:
                # Fallback to QMK ID if anything fails
                label_text = str(keycode.qmk_id)
            
            keycode_item = QTreeWidgetItem(tree, [label_text])
            keycode_item.setData(0, Qt.UserRole, keycode.qmk_id)  # Store qmk_id for easy access

            # Force text to be on one line and left-aligned
            keycode_item.setTextAlignment(0, Qt.AlignLeft)
            
            # Ensure the text is set
            keycode_item.setText(0, label_text)

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

    def recreate_buttons(self, keycode_filter=None):
        """Recreates the buttons for the inversion keycodes."""
        for i in reversed(range(self.button_layout.count())):
            widget = self.button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        row = 0
        col = 0
        max_columns = 15  # Limit columns for better appearance
        
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedSize(50, 50)  # Set fixed size to 50x50 as requested
                
                # For inversion buttons, use the second element (label) instead of description
                try:
                    # Try to access the second element directly (the label with preserved newlines)
                    button_text = str(keycode.label)  # Use label property instead of description
                except Exception:
                    # If there's no direct access, try alternative approach
                    try:
                        # Fallback 1: Try to get label via a method if it exists
                        button_text = str(Keycode.label(keycode.qmk_id))
                    except Exception:
                        # Fallback 2: Use QMK ID if all else fails
                        button_text = str(keycode.qmk_id)
                
                btn.setText(button_text)
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
        """Relabel buttons based on keycodes."""
        for i in range(self.button_layout.count()):
            widget = self.button_layout.itemAt(i).widget()
            if isinstance(widget, SquareButton) and hasattr(widget, 'keycode'):
                keycode = widget.keycode
                if keycode:
                    # For inversion buttons, use the second element (label) instead of description
                    try:
                        # Try to access the second element directly (the label with preserved newlines)
                        button_text = str(keycode.label)  # Use label property instead of description
                    except Exception:
                        # If there's no direct access, try alternative approach
                        try:
                            # Fallback 1: Try to get label via a method if it exists
                            button_text = str(Keycode.label(keycode.qmk_id))
                        except Exception:
                            # Fallback 2: Use QMK ID if all else fails
                            button_text = str(keycode.qmk_id)
                    
                    widget.setText(button_text)

    def has_buttons(self):
        """Check if buttons exist in the layout."""
        return self.button_layout.count() > 0

from PyQt5.QtWidgets import (
    QScrollArea, QVBoxLayout, QGridLayout, QLabel, QMenu, QPushButton, QHBoxLayout, QWidget, QDialog, QLineEdit, QComboBox
)
from PyQt5.QtCore import pyqtSignal, Qt
class midiadvancedTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes, smartchord_program_change, smartchord_LSB, smartchord_MSB, smartchord_CC_toggle, CCfixed, CCup, CCdown, velocity_multiplier_options, cc_multiplier_options, channel_options, velocity_options, channel_oneshot, channel_hold, smartchord_octave_1, smartchord_key, ksvelocity2, ksvelocity3, kskey2, kskey3, ksoctave2, ksoctave3, kschannel2, kschannel3, inversion_keycodes2, CCencoder, velocityshuffle, inversion_keycodesspecial, KEYCODES_SETTINGS1, KEYCODES_SETTINGS2, KEYCODES_SETTINGS3, keycodes_midi_inout=None):
        super().__init__(parent)
        self.label = label

        # Initialize dictionaries first
        self.buttons = {}

        # Store all the parameters as instance variables
        self.inversion_keycodes = inversion_keycodes
        self.inversion_keycodes2 = inversion_keycodes2
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
        self.keycodes_settings1 = KEYCODES_SETTINGS1
        self.keycodes_settings2 = KEYCODES_SETTINGS2
        self.keycodes_settings3 = KEYCODES_SETTINGS3
        self.keycodes_midi_inout = keycodes_midi_inout if keycodes_midi_inout is not None else KEYCODES_MIDI_INOUT

        # Create scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Define sections
        self.sections = [
            ("Channel", "Show\nChannel\nOptions"),
            ("CC Options", "Show\nCC Options"),
            ("Transposition", "Show\nTransposition\nSettings"),
            ("KeySplit", "Show\nKeySplit\nOptions"),
            ("Advanced MIDI", "Show\nAdvanced MIDI\nOptions"),
            ("Velocity", "Show\nVelocity\nOptions"),
            ("In/Out", "Show\nIn/Out\nOptions"),
            ("Touch Dial", "Show\nTouch Dial\nOptions"),
            ("Presets", "Show\nSetting\nPresets")
        ]

        # Create horizontal layout: side tabs on left, content box on right (VIA style)
        main_layout_h = QHBoxLayout()
        main_layout_h.setSpacing(0)
        main_layout_h.setContentsMargins(0, 0, 0, 0)

        # Create side tabs container with border
        side_tabs_container = QWidget()
        side_tabs_container.setObjectName("side_tabs_container")
        side_tabs_container.setStyleSheet("""
            QWidget#side_tabs_container {
                background: palette(window);
                border: 1px solid palette(mid);
                border-right: none;
            }
        """)
        side_tabs_layout = QVBoxLayout(side_tabs_container)
        side_tabs_layout.setSpacing(0)
        side_tabs_layout.setContentsMargins(0, 0, 0, 0)

        self.side_tab_buttons = {}
        for display_name, section_key in self.sections:
            btn = QPushButton(display_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(120)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid palette(mid);
                    border-radius: 0px;
                    border-right: none;
                    background: palette(button);
                    text-align: left;
                    padding-left: 15px;
                    font-size: 9pt;
                }
                QPushButton:hover:!checked {
                    background: palette(light);
                }
                QPushButton:checked {
                    background: palette(base);
                    font-weight: 600;
                    border-right: 1px solid palette(base);
                }
            """)
            btn.clicked.connect(lambda checked, sk=section_key: self.show_section(sk))
            side_tabs_layout.addWidget(btn)
            self.side_tab_buttons[section_key] = btn

        side_tabs_layout.addStretch(1)
        main_layout_h.addWidget(side_tabs_container)

        # Create content container with border
        self.content_wrapper = QWidget()
        self.content_wrapper.setObjectName("content_wrapper")
        self.content_wrapper.setStyleSheet("""
            QWidget#content_wrapper {
                border: 1px solid palette(mid);
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0.1,
                                           stop: 0 palette(alternate-base),
                                           stop: 1 palette(base));
            }
        """)
        self.content_layout = QVBoxLayout(self.content_wrapper)
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(15, 15, 15, 15)

        # Create layouts for sections
        # Advanced MIDI grid
        self.advanced_h_layout = QHBoxLayout()
        self.advanced_h_layout.addStretch(1)
        self.advanced_grid = QGridLayout()
        self.advanced_h_layout.addLayout(self.advanced_grid)
        self.advanced_h_layout.addStretch(1)

        # KeySplit grid
        self.keysplit_h_layout = QHBoxLayout()
        self.keysplit_h_layout.addStretch(1)
        self.keysplit_grid = QGridLayout()
        self.keysplit_h_layout.addLayout(self.keysplit_grid)
        self.keysplit_h_layout.addStretch(1)

        # Create wrapper widgets for each section
        self.section_widgets = {}
        self.section_layouts = {
            "Show\nAdvanced MIDI\nOptions": self.advanced_h_layout,
            "Show\nKeySplit\nOptions": self.keysplit_h_layout,
        }

        # Create VBoxLayouts for other sections
        for display_name, section_key in self.sections:
            if section_key not in self.section_layouts:
                section_layout = QVBoxLayout()
                section_layout.setSpacing(10)
                self.section_layouts[section_key] = section_layout

        # Wrap each layout in a QWidget container
        for section_key, section_layout in self.section_layouts.items():
            wrapper = QWidget()
            wrapper.setObjectName("section_wrapper")
            # Make wrapper border invisible - use ID selector to avoid affecting children
            wrapper.setStyleSheet("""
                QWidget#section_wrapper {
                    border: none;
                }
            """)
            wrapper.setLayout(section_layout)
            wrapper.hide()  # Hide all initially
            self.content_layout.addWidget(wrapper)
            self.section_widgets[section_key] = wrapper

        self.content_layout.addStretch(1)
        main_layout_h.addWidget(self.content_wrapper)
        self.main_layout.addLayout(main_layout_h)

        # Populate all sections
        self.populate_channel_section()
        self.populate_cc_velocity_section()
        self.populate_transposition_section()
        self.populate_keysplit_section()
        self.populate_advanced_section()
        self.populate_velocity_section()
        self.populate_inout_section()
        self.populate_expression_wheel_section()
        self.populate_settings_presets_section()

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Show first section by default
        self.show_section("Show\nChannel\nOptions")
        
    def populate_settings_presets_section(self):
        """Populate the Setting Presets section with three rows of buttons."""
        layout = self.section_layouts["Show\nSetting\nPresets"]

        # First row - KEYCODES_SETTINGS1 (centered)
        row1_layout = QHBoxLayout()
        row1_layout.addStretch(1)

        for keycode in self.keycodes_settings1:
            btn = SquareButton()
            btn.setFixedSize(50, 50)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            row1_layout.addWidget(btn)

        row1_layout.addStretch(1)
        layout.addLayout(row1_layout)

        # Second row - KEYCODES_SETTINGS2
        row2_layout = QHBoxLayout()
        row2_layout.addStretch(1)

        for keycode in self.keycodes_settings2:
            btn = SquareButton()
            btn.setFixedSize(50, 50)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            row2_layout.addWidget(btn)

        row2_layout.addStretch(1)
        layout.addLayout(row2_layout)

        # Third row - KEYCODES_SETTINGS3
        row3_layout = QHBoxLayout()
        row3_layout.addStretch(1)

        for keycode in self.keycodes_settings3:
            btn = SquareButton()
            btn.setFixedSize(50, 50)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            row3_layout.addWidget(btn)

        row3_layout.addStretch(1)
        layout.addLayout(row3_layout)

        layout.addStretch()

    def populate_channel_section(self):
        """Populate the Channel Options section with a single row of dropdowns."""
        layout = self.section_layouts["Show\nChannel\nOptions"]

        row_layout = QHBoxLayout()
        row_layout.addStretch(1)  # Left spacer

        # Create and add dropdowns with fixed width of 200 pixels
        self.add_header_dropdown("MIDI Channel", self.channel_options, row_layout, 200)
        self.add_header_dropdown("Temporary MIDI Channel", self.channel_oneshot, row_layout, 200)
        self.add_header_dropdown("Hold MIDI Channel", self.channel_hold, row_layout, 200)

        row_layout.addStretch(1)  # Right spacer
        layout.addLayout(row_layout)
        layout.addStretch()

    def populate_cc_velocity_section(self):
        """Populate the CC Options section with three rows of buttons/dropdowns."""
        layout = self.section_layouts["Show\nCC Options"]

        # First row
        row1_layout = QHBoxLayout()
        row1_layout.addStretch(1)  # Left spacer

        # Add CC Value, CC On/Off, CC Up, and CC Down buttons
        self.add_cc_x_y_menu(row1_layout, 200)
        self.add_value_button("CC On/Off", self.smartchord_CC_toggle, row1_layout, 200)
        self.add_value_button("CC Up", self.CCup, row1_layout, 200)
        self.add_value_button("CC Down", self.CCdown, row1_layout, 200)

        row1_layout.addStretch(1)  # Right spacer
        layout.addLayout(row1_layout)

        # Spacer between rows
        row_spacer1 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        layout.addItem(row_spacer1)

        # Second row
        row2_layout = QHBoxLayout()
        row2_layout.addStretch(1)  # Left spacer

        # Add Touch Dial CC and CC Increment buttons/dropdowns
        self.add_value_button("Touch Dial CC", self.CCencoder, row2_layout, 200)
        self.add_header_dropdown("CC Increment", self.cc_multiplier_options, row2_layout, 200)

        row2_layout.addStretch(1)  # Right spacer
        layout.addLayout(row2_layout)

        # Spacer between rows
        row_spacer2 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        layout.addItem(row_spacer2)

        # Third row
        row3_layout = QHBoxLayout()
        row3_layout.addStretch(1)  # Left spacer

        # Add Program Change, Bank LSB, and Bank MSB buttons
        self.add_value_button("Program Change", self.smartchord_program_change, row3_layout, 200)
        self.add_value_button("Bank LSB", self.smartchord_LSB, row3_layout, 200)
        self.add_value_button("Bank MSB", self.smartchord_MSB, row3_layout, 200)

        row3_layout.addStretch(1)  # Right spacer
        layout.addLayout(row3_layout)

        layout.addStretch()

    def populate_transposition_section(self):
        """Populate the Transposition Settings section with a single row of dropdowns."""
        layout = self.section_layouts["Show\nTransposition\nSettings"]

        row_layout = QHBoxLayout()
        row_layout.addStretch(1)  # Left spacer

        # Create and add dropdowns with fixed width of 200 pixels
        self.add_header_dropdown("Octave Selector", self.smartchord_octave_1, row_layout, 200)
        self.add_header_dropdown("Key Selector", self.smartchord_key, row_layout, 200)

        row_layout.addStretch(1)  # Right spacer
        layout.addLayout(row_layout)
        layout.addStretch()

    def populate_keysplit_section(self):
        """Populate the KeySplit Options section with dropdowns and buttons."""
        # Add buttons to the grid (grid was already created and added to container in __init__)
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

        # Add KeySplit modifier buttons below the grid
        modifiers_layout = QHBoxLayout()
        modifiers_layout.addStretch(1)

        split_buttons = [
            ("Enable\nChannel\nKeySplit", "KS_TOGGLE"),
            ("Enable\nVelocity\nKeySplit", "KS_VELOCITY_TOGGLE"),
            ("Enable\nTranspose\nKeySplit", "KS_TRANSPOSE_TOGGLE")
        ]

        for text, code in split_buttons:
            btn = QPushButton(text)
            btn.setFixedSize(60, 60)
            btn.setStyleSheet("""
                QPushButton {
                    background: palette(button);
                    border: 1px solid palette(mid);
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background: palette(light);
                }
                QPushButton:pressed {
                    background: palette(highlight);
                    color: palette(highlighted-text);
                }
            """)
            btn.clicked.connect(lambda _, k=code: self.keycode_changed.emit(k))
            modifiers_layout.addWidget(btn)

        modifiers_layout.addStretch(1)

        # Add modifiers layout to the keysplit section layout
        if hasattr(self, 'keysplit_h_layout'):
            # Create a vertical layout to hold both grid and modifiers
            keysplit_section_layout = self.section_layouts.get("Show\nKeySplit\nOptions")
            if keysplit_section_layout:
                # keysplit_section_layout is the keysplit_h_layout from __init__
                # We need to add the modifiers below it
                # Since we can't easily restructure, add a wrapper
                pass

        # Since the keysplit_h_layout is already set, we need to add the modifiers after the grid
        # Add a spacer and then the modifiers row
        self.keysplit_grid.addItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed), row+1, 0, 1, max_cols)

        # Create container for modifier buttons and add to grid
        modifiers_widget = QWidget()
        modifiers_widget.setLayout(modifiers_layout)
        self.keysplit_grid.addWidget(modifiers_widget, row+2, 0, 1, max_cols)

    def populate_advanced_section(self):
        """Populate the Advanced MIDI Options section with buttons."""
        # Clear existing buttons
        for i in reversed(range(self.advanced_grid.count())):
            widget = self.advanced_grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Add buttons in a grid layout
        row = 0
        col = 0
        max_cols = 8

        for keycode in self.inversion_keycodes:
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

    def populate_velocity_section(self):
        """Populate the Velocity Options section with HE velocity controls."""
        layout = self.section_layouts["Show\nVelocity\nOptions"]

        # First row - Velocity Increment (kept for legacy support)
        row_layout = QHBoxLayout()
        row_layout.addStretch(1)  # Left spacer

        # Velocity Increment dropdown
        self.add_header_dropdown("Velocity Increment", self.velocity_multiplier_options, row_layout, 200)

        row_layout.addStretch(1)  # Right spacer
        layout.addLayout(row_layout)

        # Second row - HE Velocity controls (replaces fixed velocity and shuffle)
        he_row_layout = QHBoxLayout()
        he_row_layout.addStretch(1)  # Left spacer

        # HE Velocity Range button (replaces fixed velocity)
        self.add_he_velocity_range_button(he_row_layout, 200)

        # HE Velocity Curve dropdown
        self.add_header_dropdown("HE Velocity Curve", KEYCODES_HE_VELOCITY_CURVE, he_row_layout, 200)

        he_row_layout.addStretch(1)  # Right spacer
        layout.addLayout(he_row_layout)

        layout.addStretch()

    def populate_inout_section(self):
        """Populate the In/Out Options section with MIDI routing and override toggles."""
        layout = self.section_layouts["Show\nIn/Out\nOptions"]

        # Section 1: MIDI Routing Controls
        routing_label = QLabel("MIDI Routing")
        routing_label.setStyleSheet("font-weight: bold; font-size: 10pt; margin-top: 5px;")
        layout.addWidget(routing_label)

        routing_row_layout = QHBoxLayout()
        routing_row_layout.addStretch(1)

        # MIDI routing keycodes from KEYCODES_MIDI_INOUT
        routing_keycodes = [kc for kc in self.keycodes_midi_inout if kc.qmk_id in [
            "MIDI_IN_MODE_TOG", "USB_MIDI_MODE_TOG", "MIDI_CLOCK_SRC_TOG"
        ]]
        for keycode in routing_keycodes:
            btn = SquareButton()
            btn.setFixedSize(70, 50)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            routing_row_layout.addWidget(btn)
            self.buttons[keycode.qmk_id] = btn

        routing_row_layout.addStretch(1)
        layout.addLayout(routing_row_layout)

        # Section 2: Override Toggles
        override_label = QLabel("Override Toggles")
        override_label.setStyleSheet("font-weight: bold; font-size: 10pt; margin-top: 15px;")
        layout.addWidget(override_label)

        override_row_layout = QHBoxLayout()
        override_row_layout.addStretch(1)

        override_keycodes = [kc for kc in self.keycodes_midi_inout if kc.qmk_id in [
            "MI_CH_OVR_TOG", "MI_VEL_OVR_TOG", "MI_TRNS_OVR_TOG"
        ]]
        for keycode in override_keycodes:
            btn = SquareButton()
            btn.setFixedSize(70, 50)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            override_row_layout.addWidget(btn)
            self.buttons[keycode.qmk_id] = btn

        override_row_layout.addStretch(1)
        layout.addLayout(override_row_layout)

        # Section 3: Additional MIDI Toggles
        additional_label = QLabel("Additional MIDI Toggles")
        additional_label.setStyleSheet("font-weight: bold; font-size: 10pt; margin-top: 15px;")
        layout.addWidget(additional_label)

        additional_row_layout = QHBoxLayout()
        additional_row_layout.addStretch(1)

        additional_keycodes = [kc for kc in self.keycodes_midi_inout if kc.qmk_id in [
            "MI_TRUE_SUS_TOG", "MI_CC_LOOP_TOG"
        ]]
        for keycode in additional_keycodes:
            btn = SquareButton()
            btn.setFixedSize(70, 50)
            btn.setText(Keycode.label(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            additional_row_layout.addWidget(btn)
            self.buttons[keycode.qmk_id] = btn

        additional_row_layout.addStretch(1)
        layout.addLayout(additional_row_layout)

        layout.addStretch()

    def populate_expression_wheel_section(self):
        """Populate the Touch Dial Options section with buttons and dropdowns."""
        layout = self.section_layouts["Show\nTouch Dial\nOptions"]
        
        # First row: Touch Dial controls
        top_row_layout = QHBoxLayout()
        top_row_layout.addStretch(1)  # Left spacer
        
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
        top_row_layout.addStretch(1)  # Right spacer
        layout.addLayout(top_row_layout)
        
        # Spacer between rows
        spacer = QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        layout.addItem(spacer)
        
        # Second row: Dropdowns
        bottom_row_layout = QHBoxLayout()
        bottom_row_layout.addStretch(1)  # Left spacer
        
        # Add dropdowns with fixed width of 200 pixels
        self.add_header_dropdown("Velocity Increment", self.velocity_multiplier_options, bottom_row_layout, 200)
        self.add_header_dropdown("CC Increment", self.cc_multiplier_options, bottom_row_layout, 200)
        
        bottom_row_layout.addStretch(1)  # Right spacer
        layout.addLayout(bottom_row_layout)
        
        layout.addStretch()

    def show_section(self, section_name):
        """Show the specified section and update tab button states"""
        # Hide all section widgets
        for widget in self.section_widgets.values():
            widget.hide()

        # Uncheck all tab buttons
        for btn in self.side_tab_buttons.values():
            btn.setChecked(False)

        # Show the selected section widget and check its tab button
        if section_name in self.section_widgets:
            self.section_widgets[section_name].show()
            if section_name in self.side_tab_buttons:
                self.side_tab_buttons[section_name].setChecked(True)

    def add_cc_x_y_menu(self, layout, width=None):
        button = QPushButton("CC Value")
        button.setFixedHeight(40)
        if width:
            button.setFixedWidth(width)
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

    def add_value_button(self, label_text, keycode_set, layout, width=None):
        """Create a button that opens a dialog to input a value for the corresponding keycode."""
        button = QPushButton(label_text)
        button.setFixedHeight(40)
        if width:
            button.setFixedWidth(width)
        
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
                    "Set Fixed Velocity": f"MI_VELOCITY_{value}",
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

    def add_value_button2(self, label_text, keycode_set, layout, width=None):
        """Create a button for keysplit section with specific height."""
        button = QPushButton(label_text)
        button.setFixedHeight(60)
        if width:
            button.setFixedWidth(width)
        
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

    def add_he_velocity_range_button(self, layout, width=None):
        """Create a button that opens a dialog to set HE velocity min and max range."""
        button = QPushButton("Set Dynamic Velocity Range")
        button.setFixedHeight(40)
        if width:
            button.setFixedWidth(width)

        def handle_range_values(min_val, max_val):
            if min_val and max_val and min_val.isdigit() and max_val.isdigit():
                min_int = int(min_val)
                max_int = int(max_val)
                if 1 <= min_int <= 127 and 1 <= max_int <= 127 and min_int <= max_int:
                    self.keycode_changed.emit(f"HE_VEL_RANGE_{min_int}_{max_int}")

        button.clicked.connect(lambda: self.open_he_range_dialog(handle_range_values))
        layout.addWidget(button)

    def open_he_range_dialog(self, callback):
        """Open a dialog to input HE velocity min and max values."""
        try:
            import emscripten
            # Async dialog for web version
            dialog = AsyncHERangeDialog(self, callback)
            dialog.show()
        except ImportError:
            # Sync dialog for desktop version
            dialog = HERangeDialog(self, callback)
            dialog.exec_()

    def open_value_dialog(self, label, keycode_set):
        """Open a dialog to input a value between 0 and 127."""
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

    def add_header_dropdown(self, header_text, keycodes, layout, width=None):
        """Add a dropdown with optional fixed width."""
        vbox = QVBoxLayout()

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)
        if width:
            dropdown.setFixedWidth(width)

        # Add a placeholder item as the first item
        dropdown.addItem(f"{header_text}")

        # Add the keycodes as options
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)

        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box to the provided layout
        layout.addLayout(vbox)
        
    def add_header_dropdown2(self, header_text, keycodes, layout, width=None):
        """Add a dropdown for keysplit section with specific height."""
        vbox = QVBoxLayout()

        # Create dropdown
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(60)
        if width:
            dropdown.setFixedWidth(width)

        # Add a placeholder item as the first item
        dropdown.addItem(f"{header_text}")

        # Add the keycodes as options
        for keycode in keycodes:
            dropdown.addItem(Keycode.label(keycode.qmk_id), keycode.qmk_id)

        # Prevent the first item from being selected again
        dropdown.model().item(0).setEnabled(False)

        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda: self.reset_dropdown(dropdown, header_text))
        vbox.addWidget(dropdown)

        # Add the vertical box to the provided layout
        layout.addLayout(vbox)
        
    def reset_dropdown(self, dropdown, header_text):
        """Reset the dropdown to show default text while storing the selected value."""
        selected_index = dropdown.currentIndex()

        if selected_index > 0:
            selected_value = dropdown.itemData(selected_index)

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
        # Relabel buttons in the advanced section
        for i in range(self.advanced_grid.count()):
            widget = self.advanced_grid.itemAt(i).widget()
            if isinstance(widget, SquareButton) and hasattr(widget, 'keycode'):
                widget.setText(Keycode.label(widget.keycode.qmk_id))
                
        # Relabel buttons in the keysplit section
        for i in range(self.keysplit_grid.count()):
            widget = self.keysplit_grid.itemAt(i).widget()
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

class LoopTab(QScrollArea):
    """Loop Control tab with simplified layout"""
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, loop_keycodes):
        super().__init__(parent)
        self.label = label
        self.loop_keycodes = loop_keycodes
        self.current_keycode_filter = None

        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.main_layout.setAlignment(Qt.AlignTop)

        # Create initial buttons
        self.recreate_buttons(keycode_filter_any)

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def recreate_buttons(self, keycode_filter):
        self.current_keycode_filter = keycode_filter

        # Clear existing layout
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Main Loop Controls section - includes main loops and modifier buttons
        main_loop_group = QGroupBox("Main Loop Controls")
        main_loop_layout = FlowLayout()
        for keycode in self.loop_keycodes:
            if keycode_filter(keycode) and keycode.qmk_id in ["DM_MACRO_1", "DM_MACRO_2", "DM_MACRO_3", "DM_MACRO_4", "DM_MUTE", "DM_OVERDUB", "DM_OCT_MOD"]:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                main_loop_layout.addWidget(btn)
        main_loop_group.setLayout(main_loop_layout)
        self.main_layout.addWidget(main_loop_group)

        # Extra Loop Buttons section - combines overdub loop, mute loop, overdub mute, and octave doubler
        extra_loop_group = QGroupBox("Extra Loop Buttons")
        extra_loop_layout = FlowLayout()
        # Order: Overdub Loop, Mute Loop, Overdub Mute, Octave Doubler
        button_order = []
        # Overdub Loop buttons
        for keycode in self.loop_keycodes:
            if keycode.qmk_id.startswith("DM_OVERDUB_") and not keycode.qmk_id.startswith("DM_OVERDUB_MUTE_") and keycode.qmk_id != "DM_OVERDUB":
                button_order.append(keycode)
        # Mute Loop buttons
        for keycode in self.loop_keycodes:
            if keycode.qmk_id.startswith("DM_MUTE_") and keycode.qmk_id != "DM_MUTE":
                button_order.append(keycode)
        # Overdub Mute buttons
        for keycode in self.loop_keycodes:
            if keycode.qmk_id.startswith("DM_OVERDUB_MUTE_"):
                button_order.append(keycode)
        # Octave Doubler buttons
        for keycode in self.loop_keycodes:
            if keycode.qmk_id.startswith("DM_OCT_") and keycode.qmk_id != "DM_OCT_MOD":
                button_order.append(keycode)
        # Add all buttons to layout
        for keycode in button_order:
            if keycode_filter(keycode):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                extra_loop_layout.addWidget(btn)
        extra_loop_group.setLayout(extra_loop_layout)
        self.main_layout.addWidget(extra_loop_group)

        # Mode Select section - includes Sync, Sample Mode, Loop Quantize, Advanced Overdub
        mode_group = QGroupBox("Mode Select")
        mode_layout = FlowLayout()
        for keycode in self.loop_keycodes:
            if keycode_filter(keycode) and keycode.qmk_id in ["DM_UNSYNC", "DM_SAMPLE", "LOOP_QUANTIZE", "DM_ADVANCED_OVERDUB"]:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                mode_layout.addWidget(btn)
        mode_group.setLayout(mode_layout)
        self.main_layout.addWidget(mode_group)

        # Modifier Buttons section - includes loop modifiers, speed/slow modifiers, octave modifier, mute, overdub
        modifier_group = QGroupBox("Modifier Buttons")
        modifier_layout = FlowLayout()
        for keycode in self.loop_keycodes:
            if keycode_filter(keycode) and keycode.qmk_id in ["DM_LOOP_MOD_1", "DM_LOOP_MOD_2", "DM_LOOP_MOD_3", "DM_LOOP_MOD_4", "DM_OCT_MOD", "DM_SPEED_MOD", "DM_SLOW_MOD", "DM_MUTE", "DM_OVERDUB"]:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                modifier_layout.addWidget(btn)
        modifier_group.setLayout(modifier_layout)
        self.main_layout.addWidget(modifier_group)

        # BeatSkip section
        beatskip_group = QGroupBox("BeatSkip")
        beatskip_layout = FlowLayout()
        for keycode in self.loop_keycodes:
            if keycode_filter(keycode) and keycode.qmk_id.startswith("DM_SKIP_"):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                beatskip_layout.addWidget(btn)
        beatskip_group.setLayout(beatskip_layout)
        self.main_layout.addWidget(beatskip_group)

        # Speed Controls section - only individual speed/slow buttons and reset
        speed_group = QGroupBox("Speed Controls")
        speed_layout = FlowLayout()
        for keycode in self.loop_keycodes:
            if keycode_filter(keycode) and (keycode.qmk_id.startswith("DM_SPEED_") or keycode.qmk_id.startswith("DM_SLOW_") or keycode.qmk_id == "DM_RESET_SPEED") and keycode.qmk_id not in ["DM_SPEED_MOD", "DM_SLOW_MOD"]:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                speed_layout.addWidget(btn)
        speed_group.setLayout(speed_layout)
        self.main_layout.addWidget(speed_group)

        # Navigation section
        nav_group = QGroupBox("Navigation")
        nav_layout = FlowLayout()
        for keycode in self.loop_keycodes:
            if keycode_filter(keycode) and (keycode.qmk_id.startswith("DM_NAV_") or keycode.qmk_id in ["DM_PLAY_PAUSE", "DM_COPY"]):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                nav_layout.addWidget(btn)
        nav_group.setLayout(nav_layout)
        self.main_layout.addWidget(nav_group)

        self.main_layout.addStretch(1)

    def has_buttons(self):
        return len(self.loop_keycodes) > 0

    def relabel_buttons(self):
        pass  # Implement if needed

class EarTrainerTab(QScrollArea):
    keycode_changed = pyqtSignal(str)
    def __init__(self, parent, label, eartrainer_keycodes, chordtrainer_keycodes):
        super().__init__(parent)
        self.label = label
        self.eartrainer_keycodes = eartrainer_keycodes
        self.chordtrainer_keycodes = chordtrainer_keycodes
        
        self.scroll_content = QWidget()
        main_layout = QVBoxLayout(self.scroll_content)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Horizontal layout with trainers side by side, both aligned to top
        sections_layout = QHBoxLayout()
        sections_layout.setSpacing(40)  # Horizontal spacing between sections
        sections_layout.setAlignment(Qt.AlignTop)  # Align to top
        sections_layout.addStretch(1)

        # Interval Trainer section (left side)
        intervals_section = QVBoxLayout()
        intervals_section.setSpacing(5)
        intervals_section.setAlignment(Qt.AlignTop)  # Align to top
        interval_label = QLabel("Interval Trainer")
        interval_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        interval_label.setAlignment(Qt.AlignCenter)
        intervals_section.addWidget(interval_label)

        self.intervals_grid = QGridLayout()
        self.intervals_grid.setSpacing(10)
        intervals_section.addLayout(self.intervals_grid)

        sections_layout.addLayout(intervals_section)

        # Chord Trainer section (right side)
        chords_section = QVBoxLayout()
        chords_section.setSpacing(5)
        chords_section.setAlignment(Qt.AlignTop)  # Align to top
        chord_label = QLabel("Chord Trainer")
        chord_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        chord_label.setAlignment(Qt.AlignCenter)
        chords_section.addWidget(chord_label)

        self.chords_grid = QGridLayout()
        self.chords_grid.setSpacing(10)
        chords_section.addLayout(self.chords_grid)

        sections_layout.addLayout(chords_section)
        sections_layout.addStretch(1)

        main_layout.addLayout(sections_layout)
        main_layout.addStretch(1)

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)

        self.recreate_buttons()

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
                btn.setStyleSheet("""
                    background: palette(button);
                    border: 1px solid palette(mid);
                    border-radius: 6px;
                """)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                self.intervals_grid.addWidget(btn, row, col)

        # Create Chord Trainer buttons (5 columns x 4 rows)
        for i, keycode in enumerate(self.chordtrainer_keycodes):
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                row = i // 5
                col = i % 5
                btn = QPushButton(Keycode.label(keycode.qmk_id))
                btn.setFixedSize(80, 50)
                btn.setStyleSheet("""
                    background: palette(button);
                    border: 1px solid palette(mid);
                    border-radius: 6px;
                """)
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

    def __init__(self, parent, label, smartchord_DF, smartchord_MO, smartchord_OSL):
        super().__init__(parent)
        self.label = label
        self.smartchord_DF = smartchord_DF
        self.smartchord_MO = smartchord_MO
        self.smartchord_OSL = smartchord_OSL

        self.scroll_content = QWidget(self)
        self.main_layout = QVBoxLayout(self.scroll_content)

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Add a spacer at the top to push everything down by 100 pixels
        top_spacer = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.main_layout.addItem(top_spacer)

        # Add "Layer Controls" title
        self.lighting_controls_label = QLabel("Layer Selection")
        self.lighting_controls_label.setAlignment(Qt.AlignCenter)
        self.lighting_controls_label.setStyleSheet("font-size: 13px;")
        self.main_layout.addWidget(self.lighting_controls_label)

        # Add another spacer (10px)
        top_spacer2 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.main_layout.addItem(top_spacer2)

        # Row 1: Three Layer dropdowns
        self.row1_layout = QHBoxLayout()
        self.row1_layout.addStretch()  # Left spacer

        # Create and add dropdowns with fixed width
        self.default_layer_dropdown = self.create_default_layer_dropdown()
        self.default_layer_dropdown.setFixedWidth(200)
        self.row1_layout.addWidget(self.default_layer_dropdown)

        self.hold_layer_dropdown = self.create_hold_layer_dropdown()
        self.hold_layer_dropdown.setFixedWidth(200)
        self.row1_layout.addWidget(self.hold_layer_dropdown)

        self.oneshot_layer_dropdown = self.create_oneshot_layer_dropdown()
        self.oneshot_layer_dropdown.setFixedWidth(200)
        self.row1_layout.addWidget(self.oneshot_layer_dropdown)

        self.row1_layout.addStretch()  # Right spacer
        self.main_layout.addLayout(self.row1_layout)

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def create_default_layer_dropdown(self, keycode_filter=None):
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("Default Layer")

        for keycode in self.smartchord_DF:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                label = Keycode.label(keycode.qmk_id)
                tooltip = Keycode.description(keycode.qmk_id)
                dropdown.addItem(label, keycode.qmk_id)
                item = dropdown.model().item(dropdown.count() - 1)
                item.setToolTip(tooltip)

        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "Default Layer"))

        return dropdown

    def create_hold_layer_dropdown(self, keycode_filter=None):
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("Hold Layer")

        for keycode in self.smartchord_MO:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                label = Keycode.label(keycode.qmk_id)
                tooltip = Keycode.description(keycode.qmk_id)
                dropdown.addItem(label, keycode.qmk_id)
                item = dropdown.model().item(dropdown.count() - 1)
                item.setToolTip(tooltip)

        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "Hold Layer"))

        return dropdown

    def create_oneshot_layer_dropdown(self, keycode_filter=None):
        dropdown = CenteredComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("One Shot Layer")

        for keycode in self.smartchord_OSL:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                label = Keycode.label(keycode.qmk_id)
                tooltip = Keycode.description(keycode.qmk_id)
                dropdown.addItem(label, keycode.qmk_id)
                item = dropdown.model().item(dropdown.count() - 1)
                item.setToolTip(tooltip)

        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "One Shot Layer"))

        return dropdown

    def recreate_buttons(self, keycode_filter=None):
        # Clear and recreate all three dropdowns
        self.row1_layout.removeWidget(self.default_layer_dropdown)
        self.row1_layout.removeWidget(self.hold_layer_dropdown)
        self.row1_layout.removeWidget(self.oneshot_layer_dropdown)

        self.default_layer_dropdown.deleteLater()
        self.hold_layer_dropdown.deleteLater()
        self.oneshot_layer_dropdown.deleteLater()

        self.default_layer_dropdown = self.create_default_layer_dropdown(keycode_filter)
        self.default_layer_dropdown.setFixedWidth(200)
        self.row1_layout.insertWidget(1, self.default_layer_dropdown)

        self.hold_layer_dropdown = self.create_hold_layer_dropdown(keycode_filter)
        self.hold_layer_dropdown.setFixedWidth(200)
        self.row1_layout.insertWidget(2, self.hold_layer_dropdown)

        self.oneshot_layer_dropdown = self.create_oneshot_layer_dropdown(keycode_filter)
        self.oneshot_layer_dropdown.setFixedWidth(200)
        self.row1_layout.insertWidget(3, self.oneshot_layer_dropdown)

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
        # No buttons to relabel in this simplified version
        pass

    def has_buttons(self):
        return True  # Always has dropdowns

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
        
        # Import QFrame if it's not already imported
        from PyQt5.QtWidgets import QFrame, QListView, QScrollBar

        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        
        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        # Add a spacer at the top (20px)
        top_spacer1 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.main_layout.addItem(top_spacer1)
        
        # Add "Lighting Controls" title
        self.lighting_controls_label = QLabel("Lighting Controls")
        self.lighting_controls_label.setAlignment(Qt.AlignCenter)
        self.lighting_controls_label.setStyleSheet("font-size: 13px;")
        self.main_layout.addWidget(self.lighting_controls_label)
        
        # Add another spacer (10px)
        top_spacer2 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.main_layout.addItem(top_spacer2)

        # Row 1: RGB Mode and RGB Color dropdowns
        self.row1_layout = QHBoxLayout()
        self.row1_layout.addStretch()  # Left spacer
        
        # Create and add dropdowns with fixed width
        self.rgb_mode_dropdown = self.create_rgb_mode_dropdown()
        self.rgb_mode_dropdown.setFixedWidth(200)
        self.row1_layout.addWidget(self.rgb_mode_dropdown)
        
        self.rgb_color_dropdown = self.create_rgb_color_dropdown()
        self.rgb_color_dropdown.setFixedWidth(200)
        self.row1_layout.addWidget(self.rgb_color_dropdown)
        
        self.row1_layout.addStretch()  # Right spacer
        self.main_layout.addLayout(self.row1_layout)
        
        # Row 2: Buttons from inversion_keycodes
        self.buttons1_container = QWidget()
        self.buttons1_layout = QGridLayout(self.buttons1_container)
        self.buttons1_layout.setHorizontalSpacing(5)
        self.buttons1_layout.setVerticalSpacing(5)
        
        # Create a horizontal layout for the button container with spacers
        self.centered_buttons1_layout = QHBoxLayout()
        self.centered_buttons1_layout.addStretch()  # Left spacer
        self.centered_buttons1_layout.addWidget(self.buttons1_container)
        self.centered_buttons1_layout.addStretch()  # Right spacer
        
        # Add the centered button layout to the main layout
        self.main_layout.addLayout(self.centered_buttons1_layout)
        
        # Add a small spacer between rows
        row_spacer2 = QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.main_layout.addItem(row_spacer2)
        
        # Add "Layer Lighting Controls" label
        self.layer_lighting_label = QLabel("Layer Lighting Controls")
        self.layer_lighting_label.setAlignment(Qt.AlignCenter)
        self.layer_lighting_label.setStyleSheet("font-size: 13px;")
        self.main_layout.addWidget(self.layer_lighting_label)
        
        # Small spacer after the label - REDUCED from 10 to 2 pixels
        label_spacer = QSpacerItem(0, 2, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.main_layout.addItem(label_spacer)
        
        # Row 3: Record Layer RGB dropdown and buttons from inversion_keycodes4
        self.row3_layout = QHBoxLayout()
        self.row3_layout.addStretch()  # Left spacer
        
        # Add Record Layer RGB dropdown
        self.rgb_layer_dropdown = self.create_rgb_layer_dropdown()
        self.rgb_layer_dropdown.setFixedWidth(200)
        self.row3_layout.addWidget(self.rgb_layer_dropdown)
        
        # Create a container for the second set of buttons
        self.buttons2_container = QWidget()
        self.buttons2_layout = QGridLayout(self.buttons2_container)
        self.buttons2_layout.setHorizontalSpacing(5)
        self.buttons2_layout.setVerticalSpacing(5)
        
        self.row3_layout.addWidget(self.buttons2_container)
        self.row3_layout.addStretch()  # Right spacer
        
        self.main_layout.addLayout(self.row3_layout)

        # Populate all buttons
        self.populate_buttons()

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def create_rgb_mode_dropdown(self):
        dropdown = ScrollableComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("RGB Mode")
        for keycode in self.smartchord_LSB:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)
            dropdown.addItem(label, keycode.qmk_id)
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)
        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "RGB Mode"))
        return dropdown

    def create_rgb_color_dropdown(self):
        dropdown = ScrollableComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("RGB Color")
        for keycode in self.smartchord_MSB:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)
            dropdown.addItem(label, keycode.qmk_id)
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)
        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "RGB Color"))
        return dropdown

    def create_rgb_layer_dropdown(self):
        dropdown = ScrollableComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("Record Layer RGB")
        for keycode in self.smartchord_LSB2:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)
            dropdown.addItem(label, keycode.qmk_id)
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)
        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "RGB Layer Save"))
        return dropdown

    def populate_buttons(self, keycode_filter=None):
        # Clear previous widgets in buttons1 layout
        for i in reversed(range(self.buttons1_layout.count())):
            widget = self.buttons1_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
                
        # Clear previous widgets in buttons2 layout
        for i in reversed(range(self.buttons2_layout.count())):
            widget = self.buttons2_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Add buttons from inversion_keycodes to the first button grid
        row = 0
        col = 0
        max_columns = 15  # Maximum number of columns
        
        for keycode in self.inversion_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(50)
                btn.setFixedWidth(50)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                self.buttons1_layout.addWidget(btn, row, col)
                col += 1
                # Move to the next row if we reach max columns
                if col >= max_columns:
                    col = 0
                    row += 1
        
        # Add buttons from inversion_keycodes4 to the second button grid
        row = 0
        col = 0
        
        for keycode in self.inversion_keycodes4:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                btn = SquareButton()
                btn.setFixedHeight(50)
                btn.setFixedWidth(50)
                btn.setText(Keycode.label(keycode.qmk_id))
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode

                self.buttons2_layout.addWidget(btn, row, col)
                col += 1
                # Move to the next row if we reach max columns
                if col >= max_columns:
                    col = 0
                    row += 1

    def recreate_buttons(self, keycode_filter=None):
        # Clear and recreate the dropdowns in row 1
        self.row1_layout.removeWidget(self.rgb_mode_dropdown)
        self.row1_layout.removeWidget(self.rgb_color_dropdown)
        
        self.rgb_mode_dropdown.deleteLater()
        self.rgb_color_dropdown.deleteLater()
        
        self.rgb_mode_dropdown = self.create_rgb_mode_dropdown()
        self.rgb_mode_dropdown.setFixedWidth(200)
        self.row1_layout.insertWidget(1, self.rgb_mode_dropdown)
        
        self.rgb_color_dropdown = self.create_rgb_color_dropdown()
        self.rgb_color_dropdown.setFixedWidth(200)
        self.row1_layout.insertWidget(2, self.rgb_color_dropdown)
        
        # Clear and recreate the dropdown in row 3
        self.row3_layout.removeWidget(self.rgb_layer_dropdown)
        self.rgb_layer_dropdown.deleteLater()
        
        self.rgb_layer_dropdown = self.create_rgb_layer_dropdown()
        self.rgb_layer_dropdown.setFixedWidth(200)
        self.row3_layout.insertWidget(1, self.rgb_layer_dropdown)
        
        # Repopulate all buttons
        self.populate_buttons(keycode_filter)

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
        # Handle relabeling for buttons in first grid
        for i in range(self.buttons1_layout.count()):
            widget = self.buttons1_layout.itemAt(i).widget()
            if isinstance(widget, SquareButton):
                keycode = widget.keycode
                if keycode:
                    widget.setText(Keycode.label(keycode.qmk_id))
                    
        # Handle relabeling for buttons in second grid
        for i in range(self.buttons2_layout.count()):
            widget = self.buttons2_layout.itemAt(i).widget()
            if isinstance(widget, SquareButton):
                keycode = widget.keycode
                if keycode:
                    widget.setText(Keycode.label(keycode.qmk_id))

    def has_buttons(self):
        """Check if there are buttons or dropdown items."""
        return (self.buttons1_layout.count() > 0 or self.buttons2_layout.count() > 0)

class LightingTab2(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, smartchord_DF, smartchord_MO, smartchord_OSL):
        super().__init__(parent)
        self.label = label
        self.smartchord_DF = smartchord_DF
        self.smartchord_MO = smartchord_MO
        self.smartchord_OSL = smartchord_OSL

        # Import QFrame if it's not already imported
        from PyQt5.QtWidgets import QFrame, QListView, QScrollBar

        # Create a widget for the scroll area content
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)

        # Set the scroll area properties
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Add a spacer at the top (20px)
        top_spacer1 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.main_layout.addItem(top_spacer1)

        # Add "Layer Controls" title
        self.lighting_controls_label = QLabel("Layer Controls")
        self.lighting_controls_label.setAlignment(Qt.AlignCenter)
        self.lighting_controls_label.setStyleSheet("font-size: 13px;")
        self.main_layout.addWidget(self.lighting_controls_label)

        # Add another spacer (10px)
        top_spacer2 = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.main_layout.addItem(top_spacer2)

        # Row 1: Three Layer dropdowns
        self.row1_layout = QHBoxLayout()
        self.row1_layout.addStretch()  # Left spacer

        # Create and add dropdowns with fixed width
        self.default_layer_dropdown = self.create_default_layer_dropdown()
        self.default_layer_dropdown.setFixedWidth(200)
        self.row1_layout.addWidget(self.default_layer_dropdown)

        self.hold_layer_dropdown = self.create_hold_layer_dropdown()
        self.hold_layer_dropdown.setFixedWidth(200)
        self.row1_layout.addWidget(self.hold_layer_dropdown)

        self.oneshot_layer_dropdown = self.create_oneshot_layer_dropdown()
        self.oneshot_layer_dropdown.setFixedWidth(200)
        self.row1_layout.addWidget(self.oneshot_layer_dropdown)

        self.row1_layout.addStretch()  # Right spacer
        self.main_layout.addLayout(self.row1_layout)

        # Spacer to push everything to the top
        self.main_layout.addStretch()

    def create_default_layer_dropdown(self):
        dropdown = ScrollableComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("Default Layer")
        for keycode in self.smartchord_DF:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)
            dropdown.addItem(label, keycode.qmk_id)
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)
        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "Default Layer"))
        return dropdown

    def create_hold_layer_dropdown(self):
        dropdown = ScrollableComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("Hold Layer")
        for keycode in self.smartchord_MO:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)
            dropdown.addItem(label, keycode.qmk_id)
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)
        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "Hold Layer"))
        return dropdown

    def create_oneshot_layer_dropdown(self):
        dropdown = ScrollableComboBox()
        dropdown.setFixedHeight(40)
        dropdown.addItem("One Shot Layer")
        for keycode in self.smartchord_OSL:
            label = Keycode.label(keycode.qmk_id)
            tooltip = Keycode.description(keycode.qmk_id)
            dropdown.addItem(label, keycode.qmk_id)
            item = dropdown.model().item(dropdown.count() - 1)
            item.setToolTip(tooltip)
        dropdown.model().item(0).setEnabled(False)
        dropdown.currentIndexChanged.connect(self.on_selection_change)
        dropdown.currentIndexChanged.connect(lambda _: self.reset_dropdown(dropdown, "One Shot Layer"))
        return dropdown

    def recreate_buttons(self, keycode_filter=None):
        # Clear and recreate all three dropdowns
        self.row1_layout.removeWidget(self.default_layer_dropdown)
        self.row1_layout.removeWidget(self.hold_layer_dropdown)
        self.row1_layout.removeWidget(self.oneshot_layer_dropdown)

        self.default_layer_dropdown.deleteLater()
        self.hold_layer_dropdown.deleteLater()
        self.oneshot_layer_dropdown.deleteLater()

        self.default_layer_dropdown = self.create_default_layer_dropdown()
        self.default_layer_dropdown.setFixedWidth(200)
        self.row1_layout.insertWidget(1, self.default_layer_dropdown)

        self.hold_layer_dropdown = self.create_hold_layer_dropdown()
        self.hold_layer_dropdown.setFixedWidth(200)
        self.row1_layout.insertWidget(2, self.hold_layer_dropdown)

        self.oneshot_layer_dropdown = self.create_oneshot_layer_dropdown()
        self.oneshot_layer_dropdown.setFixedWidth(200)
        self.row1_layout.insertWidget(3, self.oneshot_layer_dropdown)

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
        # No buttons to relabel in this simplified version
        pass

    def has_buttons(self):
        """Check if there are buttons or dropdown items."""
        return True  # Always has dropdowns

class MacroContentTab(QWidget):
    """Sub-tab showing all macro keycodes"""
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.keyboard = None
        self.buttons = []

        # Create scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Content widget with flow layout
        self.content = QWidget()
        self.flow_layout = FlowLayout()
        self.flow_layout.setContentsMargins(10, 10, 10, 10)
        self.content.setLayout(self.flow_layout)
        self.scroll.setWidget(self.content)

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

    def set_keyboard(self, keyboard):
        self.keyboard = keyboard
        self.recreate_buttons()

    def recreate_buttons(self):
        # Clear existing buttons
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons = []

        # Use KEYCODES_MACRO list which is populated based on keyboard.macro_count
        for keycode in KEYCODES_MACRO:
            btn = SquareButton()
            btn.setRelSize(KEYCODE_BTN_RATIO)
            btn.setToolTip(Keycode.tooltip(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode: self.keycode_changed.emit(k.qmk_id))
            btn.keycode = keycode
            self.flow_layout.addWidget(btn)
            self.buttons.append(btn)

        self.relabel_buttons()

    def relabel_buttons(self):
        KeycodeDisplay.relabel_buttons(self.buttons)

    def has_buttons(self):
        return len(self.buttons) > 0


class TapDanceContentTab(QWidget):
    """Sub-tab showing all tap dance keycodes"""
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.keyboard = None
        self.buttons = []

        # Create scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Content widget with flow layout
        self.content = QWidget()
        self.flow_layout = FlowLayout()
        self.flow_layout.setContentsMargins(10, 10, 10, 10)
        self.content.setLayout(self.flow_layout)
        self.scroll.setWidget(self.content)

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

    def set_keyboard(self, keyboard):
        self.keyboard = keyboard
        self.recreate_buttons()

    def recreate_buttons(self):
        # Clear existing buttons
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons = []

        # Use KEYCODES_TAP_DANCE list which is populated based on keyboard.tap_dance_count
        for keycode in KEYCODES_TAP_DANCE:
            btn = SquareButton()
            btn.setRelSize(KEYCODE_BTN_RATIO)
            btn.setToolTip(Keycode.tooltip(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode: self.keycode_changed.emit(k.qmk_id))
            btn.keycode = keycode
            self.flow_layout.addWidget(btn)
            self.buttons.append(btn)

        self.relabel_buttons()

    def relabel_buttons(self):
        KeycodeDisplay.relabel_buttons(self.buttons)

    def has_buttons(self):
        return len(self.buttons) > 0


class DKSContentTab(QWidget):
    """Sub-tab showing all DKS keycodes"""
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.keyboard = None
        self.buttons = []

        # Create scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Content widget with flow layout
        self.content = QWidget()
        self.flow_layout = FlowLayout()
        self.flow_layout.setContentsMargins(10, 10, 10, 10)
        self.content.setLayout(self.flow_layout)
        self.scroll.setWidget(self.content)

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

    def set_keyboard(self, keyboard):
        self.keyboard = keyboard
        self.recreate_buttons()

    def recreate_buttons(self):
        # Clear existing buttons
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons = []

        # Use KEYCODES_DKS list (50 DKS slots)
        for keycode in KEYCODES_DKS:
            btn = SquareButton()
            btn.setRelSize(KEYCODE_BTN_RATIO)
            btn.setToolTip(Keycode.tooltip(keycode.qmk_id))
            btn.clicked.connect(lambda _, k=keycode: self.keycode_changed.emit(k.qmk_id))
            btn.keycode = keycode
            self.flow_layout.addWidget(btn)
            self.buttons.append(btn)

        self.relabel_buttons()

    def relabel_buttons(self):
        KeycodeDisplay.relabel_buttons(self.buttons)

    def has_buttons(self):
        return len(self.buttons) > 0


class ToggleContentTab(QWidget):
    """Sub-tab showing all toggle keycodes"""
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.keyboard = None
        self.buttons = []

        # Create scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Content widget with flow layout
        self.content = QWidget()
        self.flow_layout = FlowLayout()
        self.flow_layout.setContentsMargins(10, 10, 10, 10)
        self.content.setLayout(self.flow_layout)
        self.scroll.setWidget(self.content)

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

    def set_keyboard(self, keyboard):
        self.keyboard = keyboard
        self.recreate_buttons()

    def recreate_buttons(self):
        from protocol.toggle_protocol import TOGGLE_NUM_SLOTS

        # Clear existing buttons
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons = []

        # Create toggle keycodes dynamically (100 toggle slots)
        for idx in range(TOGGLE_NUM_SLOTS):
            qmk_id = f"TGL_{idx:02d}"
            keycode = Keycode(qmk_id, f"TGL\n{idx:02d}", f"Toggle slot {idx}")
            btn = SquareButton()
            btn.setRelSize(KEYCODE_BTN_RATIO)
            btn.setToolTip(f"Toggle slot {idx}")
            btn.clicked.connect(lambda _, k=keycode: self.keycode_changed.emit(k.qmk_id))
            btn.keycode = keycode
            self.flow_layout.addWidget(btn)
            self.buttons.append(btn)

        self.relabel_buttons()

    def relabel_buttons(self):
        KeycodeDisplay.relabel_buttons(self.buttons)

    def has_buttons(self):
        return len(self.buttons) > 0


class MacroTab(QWidget):
    """Master tab for Macro, TapDance, DKS, and Toggle with side-tab style"""

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes, smartchord_LSB, smartchord_MSB):
        super().__init__(parent)
        self.label = label
        self.parent_widget = parent
        self.keyboard = None

        # Create the sub-tabs
        self.macro_tab = MacroContentTab(self)
        self.tapdance_tab = TapDanceContentTab(self)
        self.dks_tab = DKSContentTab(self)
        self.toggle_tab = ToggleContentTab(self)

        # Connect signals
        self.macro_tab.keycode_changed.connect(self.on_keycode_changed)
        self.tapdance_tab.keycode_changed.connect(self.on_keycode_changed)
        self.dks_tab.keycode_changed.connect(self.on_keycode_changed)
        self.toggle_tab.keycode_changed.connect(self.on_keycode_changed)

        # Define sections (tab_widget, display_name)
        self.sections = [
            (self.macro_tab, "Macro"),
            (self.tapdance_tab, "Tap Dance"),
            (self.dks_tab, "DKS"),
            (self.toggle_tab, "Toggle")
        ]

        # Create horizontal layout: side tabs on left, content on right
        main_layout_h = QHBoxLayout()
        main_layout_h.setSpacing(0)
        main_layout_h.setContentsMargins(0, 0, 0, 0)

        # Create side tabs container
        side_tabs_container = QWidget()
        side_tabs_container.setObjectName("macro_side_tabs_container")
        side_tabs_container.setStyleSheet("""
            QWidget#macro_side_tabs_container {
                background: palette(window);
                border: 1px solid palette(mid);
                border-right: none;
            }
        """)
        side_tabs_layout = QVBoxLayout(side_tabs_container)
        side_tabs_layout.setSpacing(0)
        side_tabs_layout.setContentsMargins(0, 0, 0, 0)

        self.side_tab_buttons = {}
        for tab_widget, display_name in self.sections:
            btn = QPushButton(display_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(120)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid palette(mid);
                    border-radius: 0px;
                    border-right: none;
                    background: palette(button);
                    text-align: left;
                    padding-left: 15px;
                    font-size: 9pt;
                }
                QPushButton:hover:!checked {
                    background: palette(light);
                }
                QPushButton:checked {
                    background: palette(base);
                    font-weight: 600;
                    border-right: 1px solid palette(base);
                }
            """)
            btn.clicked.connect(lambda checked, dn=display_name: self.show_section(dn))
            side_tabs_layout.addWidget(btn)
            self.side_tab_buttons[display_name] = btn

        side_tabs_layout.addStretch(1)
        main_layout_h.addWidget(side_tabs_container)

        # Create content container
        self.content_wrapper = QWidget()
        self.content_wrapper.setObjectName("macro_content_wrapper")
        self.content_wrapper.setStyleSheet("""
            QWidget#macro_content_wrapper {
                border: 1px solid palette(mid);
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0.1,
                                           stop: 0 palette(alternate-base),
                                           stop: 1 palette(base));
            }
        """)
        self.content_layout = QVBoxLayout(self.content_wrapper)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # Add all section widgets to content area
        self.section_widgets = {}
        for tab_widget, display_name in self.sections:
            tab_widget.hide()
            self.content_layout.addWidget(tab_widget)
            self.section_widgets[display_name] = tab_widget

        main_layout_h.addWidget(self.content_wrapper)
        self.setLayout(main_layout_h)

        # Show first section by default
        self.show_section("Macro")

    def show_section(self, section_name):
        """Show the specified section and update tab button states"""
        # Hide all section widgets
        for widget in self.section_widgets.values():
            widget.hide()

        # Uncheck all tab buttons
        for btn in self.side_tab_buttons.values():
            btn.setChecked(False)

        # Show the selected section widget and check its tab button
        if section_name in self.section_widgets:
            self.section_widgets[section_name].show()
            if section_name in self.side_tab_buttons:
                self.side_tab_buttons[section_name].setChecked(True)

    def on_keycode_changed(self, code):
        self.keycode_changed.emit(code)

    def set_keyboard(self, keyboard):
        """Set keyboard and update all sub-tabs"""
        self.keyboard = keyboard
        self.macro_tab.set_keyboard(keyboard)
        self.tapdance_tab.set_keyboard(keyboard)
        self.dks_tab.set_keyboard(keyboard)
        self.toggle_tab.set_keyboard(keyboard)

    def recreate_buttons(self, keycode_filter=None):
        """Recreate buttons in all sub-tabs"""
        if self.keyboard:
            self.macro_tab.recreate_buttons()
            self.tapdance_tab.recreate_buttons()
            self.dks_tab.recreate_buttons()
            self.toggle_tab.recreate_buttons()

    def has_buttons(self):
        """Check if any sub-tab has buttons"""
        return True  # Always show the tab

    def relabel_buttons(self):
        """Relabel buttons in all sub-tabs"""
        self.macro_tab.relabel_buttons()
        self.tapdance_tab.relabel_buttons()
        self.dks_tab.relabel_buttons()
        self.toggle_tab.relabel_buttons()

class KeySplitTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.scroll_content = QWidget()
        
        # Main layout
        main_layout = QVBoxLayout(self.scroll_content)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Create horizontal tab buttons layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(0)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.toggle_button = QPushButton("KeySplit")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setProperty("inner_tab", "true")
        self.toggle_button.clicked.connect(self.toggle_midi_layouts)
        button_layout.addWidget(self.toggle_button)

        self.toggle_button2 = QPushButton("TripleSplit")
        self.toggle_button2.setCheckable(True)
        self.toggle_button2.setProperty("inner_tab", "true")
        self.toggle_button2.clicked.connect(self.toggle_midi_layouts2)
        button_layout.addWidget(self.toggle_button2)

        button_layout.addStretch(1)
        main_layout.addLayout(button_layout)

        # Create content wrapper with border (like QTabWidget::pane)
        content_wrapper = QWidget()
        content_wrapper.setStyleSheet("""
            QWidget {
                border: 1px solid palette(mid);
                border-top: 1px solid palette(mid);
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0.1,
                                           stop: 0 palette(alternate-base),
                                           stop: 1 palette(base));
                margin-top: -1px;
            }
        """)
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Piano keyboards
        self.keysplit_piano = PianoKeyboard(color_scheme='keysplit')
        self.keysplit_piano.keyPressed.connect(self.keycode_changed)
        content_layout.addWidget(self.keysplit_piano)

        self.triplesplit_piano = PianoKeyboard(color_scheme='triplesplit')
        self.triplesplit_piano.keyPressed.connect(self.keycode_changed)
        content_layout.addWidget(self.triplesplit_piano)
        self.triplesplit_piano.hide()

        # Control buttons
        self.ks_controls = QWidget()
        ks_control_layout = QHBoxLayout(self.ks_controls)
        ks_control_layout.setAlignment(Qt.AlignCenter)
        self.create_control_buttons(ks_control_layout, 'KS')
        content_layout.addWidget(self.ks_controls)

        # Control buttons for TripleSplit
        self.ts_controls = QWidget()
        ts_control_layout = QHBoxLayout(self.ts_controls)
        ts_control_layout.setAlignment(Qt.AlignCenter)
        self.create_control_buttons(ts_control_layout, 'TS')
        content_layout.addWidget(self.ts_controls)
        self.ts_controls.hide()

        # Add the modifier button at the bottom
        modifier_button_container = QWidget()
        modifier_button_layout = QHBoxLayout(modifier_button_container)
        modifier_button_layout.setAlignment(Qt.AlignCenter)

        modifier_btn = QPushButton("KeySplit\nModifier")
        modifier_btn.setFixedSize(80, 50)
        modifier_btn.setStyleSheet("background-color: rgba(243, 209, 209, 1); color: rgba(128, 87, 87, 1);")
        modifier_btn.clicked.connect(lambda: self.keycode_changed.emit("KS_MODIFIER"))
        modifier_button_layout.addWidget(modifier_btn)

        content_layout.addWidget(modifier_button_container)
        content_layout.addStretch(1)
        main_layout.addWidget(content_wrapper)

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Show KeySplit by default
        self.toggle_button.setChecked(True)

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

            # Make buttons theme-related
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
        self.toggle_button.setChecked(True)
        self.toggle_button2.setChecked(False)

    def toggle_midi_layouts2(self):
        self.keysplit_piano.hide()
        self.triplesplit_piano.show()
        self.ks_controls.hide()
        self.ts_controls.show()
        self.toggle_button2.setChecked(True)
        self.toggle_button.setChecked(False)

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


class KeySplitOnlyTab(QScrollArea):
    """KeySplit tab - simplified to show only KeySplit"""
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.scroll_content = QWidget()

        # Main layout
        main_layout = QVBoxLayout(self.scroll_content)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Piano keyboard
        self.keysplit_piano = PianoKeyboard(color_scheme='keysplit')
        self.keysplit_piano.keyPressed.connect(self.keycode_changed)
        main_layout.addWidget(self.keysplit_piano)

        # Control buttons
        ks_control_layout = QHBoxLayout()
        ks_control_layout.setAlignment(Qt.AlignCenter)
        self.create_control_buttons(ks_control_layout, 'KS')
        main_layout.addLayout(ks_control_layout)

        # Modifier button at the bottom
        modifier_button_container = QWidget()
        modifier_button_layout = QHBoxLayout(modifier_button_container)
        modifier_button_layout.setAlignment(Qt.AlignCenter)

        modifier_btn = QPushButton("KeySplit\nModifier")
        modifier_btn.setFixedSize(80, 50)
        modifier_btn.setStyleSheet("background-color: rgba(243, 209, 209, 1); color: rgba(128, 87, 87, 1);")
        modifier_btn.clicked.connect(lambda: self.keycode_changed.emit("KS_MODIFIER"))
        modifier_button_layout.addWidget(modifier_btn)

        main_layout.addWidget(modifier_button_container)
        main_layout.addStretch(1)

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def create_control_buttons(self, layout, prefix):
        controls = [
            (f"{prefix}\nChannel\n-", f"{prefix}_CHAN_DOWN"),
            (f"{prefix}\nChannel\n+", f"{prefix}_CHAN_UP"),
            (f"{prefix}\nVelocity\n-", "MI_VELOCITY2_DOWN"),
            (f"{prefix}\nVelocity\n+", "MI_VELOCITY2_UP"),
            (f"{prefix}\nTranspose\n-", "MI_TRANSPOSE2_DOWN"),
            (f"{prefix}\nTranspose\n+", "MI_TRANSPOSE2_UP"),
            (f"{prefix}\nOctave\n-", "MI_OCTAVE2_DOWN"),
            (f"{prefix}\nOctave\n+", "MI_OCTAVE2_UP")
        ]

        for text, code in controls:
            btn = QPushButton(text)
            btn.setFixedSize(80, 50)
            btn.setStyleSheet("background-color: rgba(243, 209, 209, 1); color: rgba(128, 87, 87, 1);")
            btn.clicked.connect(lambda _, k=code: self.keycode_changed.emit(k))
            layout.addWidget(btn)

    def recreate_buttons(self, keycode_filter=None):
        self.keysplit_piano.create_piano_keys(self.inversion_keycodes, 'MI_SPLIT')

    def has_buttons(self):
        return True

    def relabel_buttons(self):
        pass


class TripleSplitTab(QScrollArea):
    """TripleSplit tab - simplified to show only TripleSplit"""
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.scroll_content = QWidget()

        # Main layout
        main_layout = QVBoxLayout(self.scroll_content)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Piano keyboard
        self.triplesplit_piano = PianoKeyboard(color_scheme='triplesplit')
        self.triplesplit_piano.keyPressed.connect(self.keycode_changed)
        main_layout.addWidget(self.triplesplit_piano)

        # Control buttons
        ts_control_layout = QHBoxLayout()
        ts_control_layout.setAlignment(Qt.AlignCenter)
        self.create_control_buttons(ts_control_layout, 'TS')
        main_layout.addLayout(ts_control_layout)

        # Modifier button at the bottom
        modifier_button_container = QWidget()
        modifier_button_layout = QHBoxLayout(modifier_button_container)
        modifier_button_layout.setAlignment(Qt.AlignCenter)

        modifier_btn = QPushButton("TripleSplit\nModifier")
        modifier_btn.setFixedSize(80, 50)
        modifier_btn.setStyleSheet("background-color: rgba(209, 243, 215, 1); color: rgba(128, 128, 87, 1);")
        modifier_btn.clicked.connect(lambda: self.keycode_changed.emit("TS_MODIFIER"))
        modifier_button_layout.addWidget(modifier_btn)

        main_layout.addWidget(modifier_button_container)
        main_layout.addStretch(1)

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def create_control_buttons(self, layout, prefix):
        controls = [
            ("TS\nChannel\n-", "KS2_CHAN_DOWN"),
            ("TS\nChannel\n+", "KS2_CHAN_UP"),
            ("TS\nVelocity\n-", "MI_VELOCITY3_DOWN"),
            ("TS\nVelocity\n+", "MI_VELOCITY3_UP"),
            ("TS\nTranspose\n-", "MI_TRANSPOSE3_DOWN"),
            ("TS\nTranspose\n+", "MI_TRANSPOSE3_UP"),
            ("TS\nOctave\n-", "MI_OCTAVE3_DOWN"),
            ("TS\nOctave\n+", "MI_OCTAVE3_UP")
        ]

        for text, code in controls:
            btn = QPushButton(text)
            btn.setFixedSize(80, 50)
            btn.setStyleSheet("background-color: rgba(209, 243, 215, 1); color: rgba(128, 128, 87, 1);")
            btn.clicked.connect(lambda _, k=code: self.keycode_changed.emit(k))
            layout.addWidget(btn)

    def recreate_buttons(self, keycode_filter=None):
        self.triplesplit_piano.create_piano_keys(self.inversion_keycodes, 'MI_SPLIT2')

    def has_buttons(self):
        return True

    def relabel_buttons(self):
        pass


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
                        
class ChordProgressionTab(QScrollArea):
    keycode_changed = pyqtSignal(str)
    
    def __init__(self, parent, label):
        super().__init__(parent)
        self.label = label
        
        # Display mode for progression buttons:
        # 0 = Roman Numerals ("i-VII-VI")
        # 1 = Chord Names ("Am-G-F")
        # 2 = Name ("The Simple Minor") 
        # 3 = Key & Number ("A Minor Prog 1")
        self.display_mode = 1  # Default to showing chord names
        
        # Current difficulty level
        # 0 = Basic, 1 = Intermediate, 2 = Advanced
        self.current_difficulty = 0
        
        # Define key names for tabs
        self.keys = [
            "C Major\nA Minor", 
            "C# Major\nBb Minor", 
            "D Major\nB Minor",
            "Eb Major\nC Minor",
            "E Major\nC# Minor",
            "F Major\nD Minor",
            "F# Major\nD# Minor",
            "G Major\nE Minor",
            "Ab Major\nF Minor",
            "A Major\nF# Minor",
            "Bb Major\nG Minor",
            "B Major\nG# Minor"
        ]

        # Updated keycode map to match the new organization by difficulty level
        self.keycode_map = {
            "C Major\nA Minor": {
                "Basic": (KEYCODES_C_CHORDPROG_BASIC_MAJOR, KEYCODES_C_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_C_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_C_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_C_CHORDPROG_EXPERT_MAJOR, KEYCODES_C_CHORDPROG_EXPERT_MINOR)
            },
            "C# Major\nBb Minor": {
                "Basic": (KEYCODES_C_SHARP_CHORDPROG_BASIC_MAJOR, KEYCODES_C_SHARP_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_C_SHARP_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_C_SHARP_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_C_SHARP_CHORDPROG_EXPERT_MAJOR, KEYCODES_C_SHARP_CHORDPROG_EXPERT_MINOR)
            },
            "D Major\nB Minor": {
                "Basic": (KEYCODES_D_CHORDPROG_BASIC_MAJOR, KEYCODES_D_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_D_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_D_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_D_CHORDPROG_EXPERT_MAJOR, KEYCODES_D_CHORDPROG_EXPERT_MINOR)
            },
            "Eb Major\nC Minor": {
                "Basic": (KEYCODES_E_FLAT_CHORDPROG_BASIC_MAJOR, KEYCODES_E_FLAT_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_E_FLAT_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_E_FLAT_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_E_FLAT_CHORDPROG_EXPERT_MAJOR, KEYCODES_E_FLAT_CHORDPROG_EXPERT_MINOR)
            },
            "E Major\nC# Minor": {
                "Basic": (KEYCODES_E_CHORDPROG_BASIC_MAJOR, KEYCODES_E_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_E_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_E_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_E_CHORDPROG_EXPERT_MAJOR, KEYCODES_E_CHORDPROG_EXPERT_MINOR)
            },
            "F Major\nD Minor": {
                "Basic": (KEYCODES_F_CHORDPROG_BASIC_MAJOR, KEYCODES_F_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_F_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_F_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_F_CHORDPROG_EXPERT_MAJOR, KEYCODES_F_CHORDPROG_EXPERT_MINOR)
            },
            "F# Major\nD# Minor": {
                "Basic": (KEYCODES_F_SHARP_CHORDPROG_BASIC_MAJOR, KEYCODES_F_SHARP_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_F_SHARP_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_F_SHARP_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_F_SHARP_CHORDPROG_EXPERT_MAJOR, KEYCODES_F_SHARP_CHORDPROG_EXPERT_MINOR)
            },
            "G Major\nE Minor": {
                "Basic": (KEYCODES_G_CHORDPROG_BASIC_MAJOR, KEYCODES_G_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_G_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_G_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_G_CHORDPROG_EXPERT_MAJOR, KEYCODES_G_CHORDPROG_EXPERT_MINOR)
            },
            "Ab Major\nF Minor": {
                "Basic": (KEYCODES_A_FLAT_CHORDPROG_BASIC_MAJOR, KEYCODES_A_FLAT_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_A_FLAT_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_A_FLAT_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_A_FLAT_CHORDPROG_EXPERT_MAJOR, KEYCODES_A_FLAT_CHORDPROG_EXPERT_MINOR)
            },
            "A Major\nF# Minor": {
                "Basic": (KEYCODES_A_CHORDPROG_BASIC_MAJOR, KEYCODES_A_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_A_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_A_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_A_CHORDPROG_EXPERT_MAJOR, KEYCODES_A_CHORDPROG_EXPERT_MINOR)
            },
            "Bb Major\nG Minor": {
                "Basic": (KEYCODES_B_FLAT_CHORDPROG_BASIC_MAJOR, KEYCODES_B_FLAT_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_B_FLAT_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_B_FLAT_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_B_FLAT_CHORDPROG_EXPERT_MAJOR, KEYCODES_B_FLAT_CHORDPROG_EXPERT_MINOR)
            },
            "B Major\nG# Minor": {
                "Basic": (KEYCODES_B_CHORDPROG_BASIC_MAJOR, KEYCODES_B_CHORDPROG_BASIC_MINOR),
                "Intermediate": (KEYCODES_B_CHORDPROG_INTERMEDIATE_MAJOR, KEYCODES_B_CHORDPROG_INTERMEDIATE_MINOR),
                "Advanced": (KEYCODES_B_CHORDPROG_EXPERT_MAJOR, KEYCODES_B_CHORDPROG_EXPERT_MINOR)
            },
        }
        
        # Difficulty levels
        self.difficulty_levels = ["Basic", "Intermediate", "Advanced"]
        
        # Add control keycodes at the end
        self.control_keycodes = KEYCODES_CHORD_PROG_CONTROLS
        
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        # Create tab buttons for keys at the top with spacers for centering
        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(2)
        
        # Add stretch before buttons
        tab_layout.addStretch(1)
        
        self.tab_buttons = []
        for key in self.keys:
            btn = QPushButton(key)
            btn.setFixedHeight(40)
            btn.setFixedWidth(70)
            btn.setStyleSheet("background-color: #FFE0B2; color: #8D6E63;")
            btn.clicked.connect(lambda _, k=key: self.show_key(k))
            self.tab_buttons.append(btn)
            tab_layout.addWidget(btn)
        
        # Add stretch after buttons
        tab_layout.addStretch(1)
        
        self.main_layout.addLayout(tab_layout)
        
        # Add difficulty level buttons with legends on sides (closer to center)
        difficulty_layout = QHBoxLayout()
        difficulty_layout.setAlignment(Qt.AlignCenter)
        difficulty_layout.setSpacing(5)  # Reduced spacing
        
        # Add major legend on the left - closer to difficulty buttons
        major_legend = QLabel("■ Major Progressions")
        major_legend.setStyleSheet("color: #1565C0;")
        
        # Add minor legend on the right - closer to difficulty buttons
        minor_legend = QLabel("■ Minor Progressions")
        minor_legend.setStyleSheet("color: #7D3C98;")
        
        self.difficulty_buttons = []
        
        # Create a layout that will contain the first button and major legend
        first_button_layout = QHBoxLayout()
        first_button_layout.addWidget(major_legend)
        first_button_layout.addSpacing(5)  # Small space between legend and button
        
        # Add first button
        btn = QPushButton(self.difficulty_levels[0])
        btn.setFixedSize(120, 40)
        btn.clicked.connect(lambda _, l=self.difficulty_levels[0]: self.show_difficulty(l))
        self.difficulty_buttons.append(btn)
        first_button_layout.addWidget(btn)
        
        # Add the first button layout to the difficulty layout
        difficulty_layout.addLayout(first_button_layout)
        
        # Add the middle button directly
        btn = QPushButton(self.difficulty_levels[1])
        btn.setFixedSize(120, 40)
        btn.clicked.connect(lambda _, l=self.difficulty_levels[1]: self.show_difficulty(l))
        self.difficulty_buttons.append(btn)
        difficulty_layout.addWidget(btn)
        
        # Create a layout that will contain the last button and minor legend
        last_button_layout = QHBoxLayout()
        
        # Add last button
        btn = QPushButton(self.difficulty_levels[2])
        btn.setFixedSize(120, 40)
        btn.clicked.connect(lambda _, l=self.difficulty_levels[2]: self.show_difficulty(l))
        self.difficulty_buttons.append(btn)
        last_button_layout.addWidget(btn)
        
        last_button_layout.addSpacing(5)  # Small space between button and legend
        last_button_layout.addWidget(minor_legend)
        
        # Add the last button layout to the difficulty layout
        difficulty_layout.addLayout(last_button_layout)
        
        self.main_layout.addLayout(difficulty_layout)
        self.main_layout.addSpacing(5)  # Add a small space after difficulty buttons
        
        # Container for progression buttons
        self.progressions_container = QWidget()
        progressions_layout = QHBoxLayout(self.progressions_container)
        
        # Add stretch before grid
        progressions_layout.addStretch(1)
        
        # Create a container for the grid
        grid_container = QWidget()
        grid_layout = QVBoxLayout(grid_container)
        
        self.progressions_grid = QGridLayout()
        self.progressions_grid.setSpacing(10)  # Same spacing as chord trainer
        grid_layout.addLayout(self.progressions_grid)
        
        progressions_layout.addWidget(grid_container)
        
        # Add stretch after grid
        progressions_layout.addStretch(1)
        
        self.main_layout.addWidget(self.progressions_container)
        
        # Control buttons section at the bottom
        self.controls_container = QWidget()
        controls_layout = QHBoxLayout(self.controls_container)

        # Add stretch before controls
        controls_layout.addStretch(1)

        self.controls_layout_inner = QHBoxLayout()
        self.controls_layout_inner.setSpacing(10)
        controls_layout.addLayout(self.controls_layout_inner)

        # Add stretch after controls
        controls_layout.addStretch(1)

        self.main_layout.addWidget(self.controls_container)
        
        # Add the toggle button at the bottom
        toggle_btn_layout = QHBoxLayout()
        toggle_btn_layout.setAlignment(Qt.AlignCenter)
        
        # Create the toggle description button with light green background
        self.toggle_desc_btn = QPushButton("Showing: Chord Names")  # Set default to chord names
        self.toggle_desc_btn.setFixedSize(170, 50)
        self.toggle_desc_btn.setStyleSheet("background-color: #FFE0B2; color: #8D6E63;")  # Light green background with darker green text
        self.toggle_desc_btn.clicked.connect(self.toggle_button_description)
        toggle_btn_layout.addWidget(self.toggle_desc_btn)
        
        self.main_layout.addLayout(toggle_btn_layout)
        
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        
        # Show first key (C) by default and Basic difficulty
        self.current_key = self.keys[0]
        self.current_difficulty_level = self.difficulty_levels[0]
        self.show_difficulty(self.current_difficulty_level)
        self.populate_controls()

    def toggle_button_description(self):
        # Cycle through display modes (0-3)
        self.display_mode = (self.display_mode + 1) % 4
        
        # Update button text based on the new mode
        mode_names = ["Showing: Roman Numerals", "Showing: Chord Names", 
                     "Showing: Names", "Showing: Prog Numbers"]
        self.toggle_desc_btn.setText(mode_names[self.display_mode])
        
        # Use QTimer to revert the styling after a short delay but keep the green color
        QTimer.singleShot(100, lambda: self.toggle_desc_btn.setStyleSheet("background-color: #FFE0B2; color: #8D6E63;"))
        
        # Refresh the buttons with the new display mode
        self.relabel_buttons()

    def show_key(self, key):
        # Update the active tab button highlight - use darker version of yellow
        for btn in self.tab_buttons:
            if btn.text() == key:
                btn.setStyleSheet("""
                    background-color: #D4A76A;
                    color: #4A3828;
                """)
            else:
                btn.setStyleSheet("background-color: #FFE0B2; color: #8D6E63;")
        
        self.current_key = key
        self.recreate_buttons()

    def show_difficulty(self, difficulty_level):
        # Update the active difficulty button highlight
        for btn in self.difficulty_buttons:
            if btn.text() == difficulty_level:
                # Highlighted button with gold color (similar to key selectors)
                btn.setStyleSheet("background-color: #FFE0B2; color: #8D6E63;")
            else:
                    # Default styling - empty stylesheet to use system defaults
                btn.setStyleSheet("")
        
        self.current_difficulty_level = difficulty_level
        self.recreate_buttons()

    def populate_controls(self):
        # Clear existing controls
        while self.controls_layout_inner.count():
            item = self.controls_layout_inner.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create control buttons (all in same row)
        for keycode in self.control_keycodes:
            btn = QPushButton(Keycode.label(keycode.qmk_id))
            btn.setFixedSize(50, 50)  # 50x50 as requested
            btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
            btn.keycode = keycode
            self.controls_layout_inner.addWidget(btn)

    def recreate_buttons(self, keycode_filter=None):
        # Clear existing layouts
        while self.progressions_grid.count():
            item = self.progressions_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Get keycodes for current key and difficulty level
        major_keycodes, minor_keycodes = self.keycode_map[self.current_key][self.current_difficulty_level]
        
        # Create a combined list of all keycodes with their types
        all_progression_keycodes = []
        
        # Add major keycodes with a flag
        for keycode in major_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                all_progression_keycodes.append((keycode, True))
                
        # Add minor keycodes with a flag
        for keycode in minor_keycodes:
            if keycode_filter is None or keycode_filter(keycode.qmk_id):
                all_progression_keycodes.append((keycode, False))
        
        # Extract the numeric part of keycode ID for sorting
        def get_progression_number(keycode_tuple):
            keycode = keycode_tuple[0]
            # Extract just the number from the keycode ID (e.g., "C_CHORDPROG28" -> 28)
            qmk_id = keycode.qmk_id
            try:
                num = int(qmk_id.split('PROG')[1])
                return num
            except (IndexError, ValueError):
                return 0  # Default if no number found
        
        # Sort by the numeric progression number
        all_progression_keycodes.sort(key=get_progression_number)
        
        # Calculate how many rows we'll need
        total_buttons = len(all_progression_keycodes)
        cols_per_row = 8  # 8 columns per row
        total_rows = (total_buttons + cols_per_row - 1) // cols_per_row  # Ceiling division
        
        # For each row, calculate buttons and add spacers if needed
        buttons_added = 0
        for row in range(total_rows):
            # Calculate buttons in this row
            remaining_buttons = total_buttons - buttons_added
            buttons_in_row = min(remaining_buttons, cols_per_row)
            
            # If this row has fewer than 8 buttons, calculate spacers
            if buttons_in_row < cols_per_row:
                # Calculate how many spacers to add on each side
                spacers_per_side = (cols_per_row - buttons_in_row) // 2
                start_col = spacers_per_side
            else:
                start_col = 0
            
            # Add the buttons for this row
            for col in range(buttons_in_row):
                i = buttons_added
                keycode, is_major = all_progression_keycodes[i]
                
                btn = QPushButton()
                
                # Get label and description
                label = Keycode.label(keycode.qmk_id)
                description = Keycode.description(keycode.qmk_id)
                
                # Extract roman numerals (everything before the first opening parenthesis)
                if "(" in description:
                    roman_numerals = description.split("(")[0].strip()
                else:
                    roman_numerals = description.split("\n")[0].strip()
                
                # Extract chord names (text inside parentheses)
                chord_names = ""
                if "(" in description and ")" in description:
                    chord_names = description[description.find("(")+1:description.find(")")]
                
                # Extract progression name (everything after the closing parenthesis)
                prog_name = ""
                if ")" in description:
                    prog_name = description.split(")")[-1].strip()
                
                # Set button text based on display mode
                if self.display_mode == 0:  # Roman Numerals
                    btn.setText(roman_numerals)
                elif self.display_mode == 1:  # Chord Names
                    btn.setText(chord_names)
                elif self.display_mode == 2:  # Name
                    btn.setText(prog_name)
                else:  # Key & Number (mode 3)
                    btn.setText(label.replace("\n", " "))
                
                # When setting tooltip - replace newlines with spaces only in the label
                clean_label = label.replace("\n", " ")
                btn.setToolTip(f"{clean_label} - {description}")
                
                btn.setFixedSize(110, 60)  # Same size as chord trainer
                
                # Apply different styling based on major/minor
                if is_major:
                    btn.setStyleSheet("background-color: #E3F2FD; color: #1565C0; text-align: center;")
                else:
                    btn.setStyleSheet("background-color: #E8DAEF; color: #7D3C98; text-align: center;")
                    
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                
                # Place button in the grid with appropriate offset
                actual_col = start_col + col
                self.progressions_grid.addWidget(btn, row, actual_col)
                
                buttons_added += 1

    def relabel_buttons(self):
        for i in range(self.progressions_grid.count()):
            widget = self.progressions_grid.itemAt(i).widget()
            if hasattr(widget, 'keycode'):
                # Get label and description
                label = Keycode.label(widget.keycode.qmk_id)
                description = Keycode.description(widget.keycode.qmk_id)
                
                # Extract roman numerals (everything before the first opening parenthesis)
                if "(" in description:
                    roman_numerals = description.split("(")[0].strip()
                else:
                    roman_numerals = description.split("\n")[0].strip()
                
                # Extract chord names (text inside parentheses)
                chord_names = ""
                if "(" in description and ")" in description:
                    chord_names = description[description.find("(")+1:description.find(")")]
                
                # Extract progression name (everything after the closing parenthesis)
                prog_name = ""
                if ")" in description:
                    prog_name = description.split(")")[-1].strip()
                
                # Set button text based on display mode
                if self.display_mode == 0:  # Roman Numerals
                    widget.setText(roman_numerals)
                elif self.display_mode == 1:  # Chord Names
                    widget.setText(chord_names)
                elif self.display_mode == 2:  # Name
                    widget.setText(prog_name)
                else:  # Key & Number (mode 3)
                    widget.setText(label.replace("\n", " "))

                # When setting tooltip
                clean_label = label.replace("\n", " ")
                widget.setToolTip(f"{clean_label} - {description}")

        for i in range(self.controls_layout_inner.count()):
            widget = self.controls_layout_inner.itemAt(i).widget()
            if hasattr(widget, 'keycode'):
                widget.setText(Keycode.label(widget.keycode.qmk_id))

    def has_buttons(self):
        return self.progressions_grid.count() > 0

class midiTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, inversion_keycodes):
        super().__init__(parent)
        self.label = label
        self.inversion_keycodes = inversion_keycodes
        self.scroll_content = QWidget()

        # In midiTab class, restore original control buttons
        self.midi_layout2 = [
            ["MI_TAP", "BPM_DOWN", "BPM_UP", "MI_ALLOFF", "MI_SUS", "MI_CHORD_99"]
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
            # Use normal theme button styling - no custom colors
            if item == "MI_ALLOFF":
                btn.setText("All\nNotes\nOff")
            elif item == "MI_SUS":
                btn.setText("Sustain\nPedal")
            elif item == "MI_CHORD_99":
                btn.setText("Smart\nChord")
            elif item == "MI_TAP":
                btn.setText("Tap\nBPM")
            elif item == "BPM_UP":
                btn.setText("BPM\nUp")
            elif item == "BPM_DOWN":
                btn.setText("BPM\nDown")
            elif item == "SAVE_SETTINGS":
                btn.setText("Save\nSettings")
            elif item == "DEFAULT_SETTINGS":
                btn.setText("Reset\nDefault\nSettings")
            elif item == "KC_NO":
                btn.setText("")
            btn.clicked.connect(lambda _, k=item: self.keycode_changed.emit(k))
            control_layout.addWidget(btn)

        self.main_layout.addWidget(control_container)
        
        # Additional layouts
        self.dropdown_layout = QVBoxLayout()
        self.main_layout.addLayout(self.dropdown_layout)
        self.horizontal_dropdown_layout = QHBoxLayout()
        self.dropdown_layout.addLayout(self.horizontal_dropdown_layout)
        
        self.inversion_label = QLabel(" ")
        self.main_layout.addWidget(self.inversion_label)

        # Container to center the button grid
        button_container = QHBoxLayout()
        button_container.addStretch(1)  # Left spacer
        
        self.button_layout = QGridLayout()
        button_container.addLayout(self.button_layout)
        
        button_container.addStretch(1)  # Right spacer
        self.main_layout.addLayout(button_container)
        
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
                grid_btn.setFixedWidth(150)  # Set maximum width to 200px as requested
                grid_btn.setFixedHeight(50)  # Set a minimum height for visibility
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


class GamepadWidget(QWidget):
    """Custom widget that displays a gamepad image as background with buttons overlaid"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(750, 560)

        # Create QLabel to display the image - manually positioned instead of using layout
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Detect theme and load appropriate controller image
        window_color = QApplication.palette().color(QPalette.Window)
        brightness = (window_color.red() * 0.299 + window_color.green() * 0.587 + window_color.blue() * 0.114)

        # Choose controller image based on brightness (light or dark theme)
        if brightness > 127:  # Threshold for light/dark theme
            pixmap = QPixmap(":/controllerlight")  # Light theme alias
        else:
            pixmap = QPixmap(":/controllerdark")  # Dark theme alias

        if not pixmap.isNull():
            # Scale the pixmap to fit width while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                750, 560,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setFixedSize(scaled_pixmap.size())
            # Position image label at top center, shifted up 50px to reduce gap
            x_offset = (750 - scaled_pixmap.width()) // 2
            self.image_label.move(x_offset, -50)
        else:
            # Set a fallback text if image doesn't load
            self.image_label.setFixedSize(750, 560)
            self.image_label.move(0, 0)
            self.image_label.setText("Controller Image\nNot Loaded")
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: palette(base);
                    border: 2px solid palette(mid);
                    color: palette(text);
                    font-size: 16px;
                }
            """)


class DpadButton(QPushButton):
    """Custom QPushButton that draws a border along its masked shape"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_path = None
        self.border_width = 3  # Increased from 2 to 3 (1px thicker)

    def set_border_path(self, path):
        """Set the path to draw the border along"""
        self.border_path = QPainterPath(path)

    def paintEvent(self, event):
        # Let the parent draw the button normally
        super().paintEvent(event)

        # Draw the border on top
        if self.border_path:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            # Use theme-related color from palette
            border_color = QApplication.palette().color(QPalette.Mid)
            pen = QPen(border_color, self.border_width)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self.border_path)


class GamingTab(QScrollArea):
    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, gaming_keycodes):
        super().__init__(parent)
        self.label = label
        self.gaming_keycodes = gaming_keycodes
        self.current_keycode_filter = None
        self.keyboard = None  # Will be set by parent when keyboard is connected

        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 0, 20, 20)  # Remove top margin to eliminate gap
        self.main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.recreate_buttons()

    def get_keycode(self, qmk_id):
        """Helper to get keycode by qmk_id"""
        for kc in self.gaming_keycodes:
            if kc.qmk_id == qmk_id:
                return kc
        return None

    def create_button(self, qmk_id, width=50, height=50):
        """Create a button for a keycode"""
        kc = self.get_keycode(qmk_id)
        if not kc:
            return None

        btn = QPushButton(Keycode.label(kc.qmk_id))
        btn.setFixedSize(width, height)
        btn.clicked.connect(lambda: self.keycode_changed.emit(kc.qmk_id))
        btn.keycode = kc
        return btn

    def recreate_buttons(self, keycode_filter=None):
        """Recreate all buttons for the gaming controller layout"""
        self.current_keycode_filter = keycode_filter

        # Clear existing layout
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

        # Create gamepad widget with drawn outline
        gamepad_widget = GamepadWidget()
        gamepad_widget.setFixedSize(750, 560)  # Increased height to accommodate repositioned buttons

        # Use absolute positioning for buttons on the gamepad
        # We'll position buttons using move() after creating them as children of gamepad_widget

        # Triggers (LT and RT) - LT moved 23px left, RT moved 13px right, both up 15px
        lt_btn = self.create_button("LT", 60, 35)
        if lt_btn:
            lt_btn.setParent(gamepad_widget)
            lt_btn.move(177, 25)  # Moved 23px left from 200, 15px up

        rt_btn = self.create_button("RT", 60, 35)
        if rt_btn:
            rt_btn.setParent(gamepad_widget)
            rt_btn.move(503, 25)  # Moved 13px right from 490, 15px up

        # Gaming Mode Toggle (in middle of shoulder buttons) - moved up 10px only
        gaming_mode_btn = self.create_button("GAMING_MODE", 100, 40)
        if gaming_mode_btn:
            gaming_mode_btn.setParent(gamepad_widget)
            gaming_mode_btn.move(325, 75)  # Moved up 10px from 85

        # Bumpers (LB and RB) - LB moved 23px left, RB moved 13px right, both up 15px
        lb_btn = self.create_button("XBOX_LB", 60, 30)
        if lb_btn:
            lb_btn.setParent(gamepad_widget)
            lb_btn.move(177, 65)  # Moved 23px left from 200, 15px up

        rb_btn = self.create_button("XBOX_RB", 60, 30)
        if rb_btn:
            rb_btn.setParent(gamepad_widget)
            rb_btn.move(503, 65)  # Moved 13px right from 490, 15px up

        # D-pad (left side) - tapered arrow-shaped buttons, moved up 60px
        # Create custom polygon buttons for dpad with tapered ends

        # D-pad up: curved top (outside), tapers to point at bottom (inside, 25px taper)
        kc = self.get_keycode("DPAD_UP")
        if kc:
            dpad_up = DpadButton(Keycode.label(kc.qmk_id))
            dpad_up.setFixedSize(56, 58)
            dpad_up.clicked.connect(lambda: self.keycode_changed.emit(kc.qmk_id))
            dpad_up.keycode = kc
            dpad_up.setText("↑")
            dpad_up.setParent(gamepad_widget)
            dpad_up.move(180, 105)  # 2px left, 3px down
            # Curved top edge (outside), point at bottom (inside) with 25px taper
            path = QPainterPath()
            path.moveTo(28, 58)  # Bottom point (inside)
            path.lineTo(3, 33)   # Left side of taper (58-25=33)
            path.lineTo(3, 8)    # Left straight section
            path.quadTo(8, 3, 15, 3)   # Curved top-left corner
            path.lineTo(41, 3)   # Top straight section (curved edge)
            path.quadTo(48, 3, 53, 8)  # Curved top-right corner
            path.lineTo(53, 33)  # Right straight section
            path.lineTo(28, 58)  # Back to bottom point
            path.closeSubpath()
            dpad_up.setMask(QRegion(path.toFillPolygon().toPolygon()))
            dpad_up.set_border_path(path)

        # D-pad down: curved bottom (outside), tapers to point at top (inside, 25px taper)
        kc = self.get_keycode("DPAD_DOWN")
        if kc:
            dpad_down = DpadButton(Keycode.label(kc.qmk_id))
            dpad_down.setFixedSize(56, 58)
            dpad_down.clicked.connect(lambda: self.keycode_changed.emit(kc.qmk_id))
            dpad_down.keycode = kc
            dpad_down.setText("↓")
            dpad_down.setParent(gamepad_widget)
            dpad_down.move(180, 163)  # 2px left, 3px down
            path = QPainterPath()
            path.moveTo(28, 0)   # Top point (inside)
            path.lineTo(3, 25)   # Left side of taper (25px from point)
            path.lineTo(3, 50)   # Left straight section
            path.quadTo(8, 55, 15, 55)  # Curved bottom-left corner
            path.lineTo(41, 55)  # Bottom straight section (curved edge)
            path.quadTo(48, 55, 53, 50)  # Curved bottom-right corner
            path.lineTo(53, 25)  # Right straight section
            path.lineTo(28, 0)   # Back to top point
            path.closeSubpath()
            dpad_down.setMask(QRegion(path.toFillPolygon().toPolygon()))
            dpad_down.set_border_path(path)

        # D-pad left: curved left (outside), tapers to point at right (inside, 25px taper)
        kc = self.get_keycode("DPAD_LEFT")
        if kc:
            dpad_left = DpadButton(Keycode.label(kc.qmk_id))
            dpad_left.setFixedSize(58, 56)
            dpad_left.clicked.connect(lambda: self.keycode_changed.emit(kc.qmk_id))
            dpad_left.keycode = kc
            dpad_left.setText("←")
            dpad_left.setParent(gamepad_widget)
            dpad_left.move(150, 135)  # 2px left, 3px down
            path = QPainterPath()
            path.moveTo(58, 28)  # Right point (inside)
            path.lineTo(33, 3)   # Top side of taper (58-25=33)
            path.lineTo(8, 3)    # Top straight section
            path.quadTo(3, 8, 3, 15)   # Curved top-left corner
            path.lineTo(3, 41)   # Left straight section (curved edge)
            path.quadTo(3, 48, 8, 53)  # Curved bottom-left corner
            path.lineTo(33, 53)  # Bottom straight section
            path.lineTo(58, 28)  # Back to right point
            path.closeSubpath()
            dpad_left.setMask(QRegion(path.toFillPolygon().toPolygon()))
            dpad_left.set_border_path(path)

        # D-pad right: curved right (outside), tapers to point at left (inside, 25px taper)
        kc = self.get_keycode("DPAD_RIGHT")
        if kc:
            dpad_right = DpadButton(Keycode.label(kc.qmk_id))
            dpad_right.setFixedSize(58, 56)
            dpad_right.clicked.connect(lambda: self.keycode_changed.emit(kc.qmk_id))
            dpad_right.keycode = kc
            dpad_right.setText("→")
            dpad_right.setParent(gamepad_widget)
            dpad_right.move(208, 135)  # 2px left, 3px down
            path = QPainterPath()
            path.moveTo(0, 28)   # Left point (inside)
            path.lineTo(25, 3)   # Top side of taper (25px from point)
            path.lineTo(50, 3)   # Top straight section
            path.quadTo(55, 8, 55, 15)  # Curved top-right corner
            path.lineTo(55, 41)  # Right straight section (curved edge)
            path.quadTo(55, 48, 50, 53)  # Curved bottom-right corner
            path.lineTo(25, 53)  # Bottom straight section
            path.lineTo(0, 28)   # Back to left point
            path.closeSubpath()
            dpad_right.setMask(QRegion(path.toFillPolygon().toPolygon()))
            dpad_right.set_border_path(path)

        # Left Analog Stick - moved 23px left, then 8px right and 25px up
        ls_up = self.create_button("LS_UP", 38, 38)
        if ls_up:
            ls_up.setParent(gamepad_widget)
            ls_up.move(275, 185)  # Moved 23px left from 290, then 8px right and 25px up

        ls_down = self.create_button("LS_DOWN", 38, 38)
        if ls_down:
            ls_down.setParent(gamepad_widget)
            ls_down.move(275, 261)  # Moved 23px left from 290, then 8px right and 25px up

        ls_left = self.create_button("LS_LEFT", 38, 38)
        if ls_left:
            ls_left.setParent(gamepad_widget)
            ls_left.move(237, 223)  # Moved 23px left from 252, then 8px right and 25px up

        ls_right = self.create_button("LS_RIGHT", 38, 38)
        if ls_right:
            ls_right.setParent(gamepad_widget)
            ls_right.move(313, 223)  # Moved 23px left from 328, then 8px right and 25px up

        l3_btn = self.create_button("XBOX_L3", 38, 38)
        if l3_btn:
            l3_btn.setParent(gamepad_widget)
            l3_btn.move(275, 223)  # Center - moved 23px left from 290, then 8px right and 25px up

        # Center buttons (Back and Start) - moved up 20px
        back_btn = self.create_button("XBOX_BACK", 50, 30)
        if back_btn:
            back_btn.setParent(gamepad_widget)
            back_btn.move(320, 170)  # Moved up 20px

        start_btn = self.create_button("XBOX_START", 50, 30)
        if start_btn:
            start_btn.setParent(gamepad_widget)
            start_btn.move(380, 170)  # Moved up 20px

        # Right Analog Stick - moved 13px right, then 25px up
        rs_up = self.create_button("RS_UP", 38, 38)
        if rs_up:
            rs_up.setParent(gamepad_widget)
            rs_up.move(439, 185)  # Moved 13px right from 426, then 25px up

        rs_down = self.create_button("RS_DOWN", 38, 38)
        if rs_down:
            rs_down.setParent(gamepad_widget)
            rs_down.move(439, 261)  # Moved 13px right from 426, then 25px up

        rs_left = self.create_button("RS_LEFT", 38, 38)
        if rs_left:
            rs_left.setParent(gamepad_widget)
            rs_left.move(401, 223)  # Moved 13px right from 388, then 25px up

        rs_right = self.create_button("RS_RIGHT", 38, 38)
        if rs_right:
            rs_right.setParent(gamepad_widget)
            rs_right.move(477, 223)  # Moved 13px right from 464, then 25px up

        r3_btn = self.create_button("XBOX_R3", 38, 38)
        if r3_btn:
            r3_btn.setParent(gamepad_widget)
            r3_btn.move(439, 223)  # Center - moved 13px right from 426, then 25px up

        # Face Buttons (right side) - Button 1-4, 20% bigger (50x50) and repositioned
        btn4 = self.create_button("XBOX_Y", 50, 50)
        if btn4:
            btn4.setText("Button\n4")
            btn4.setParent(gamepad_widget)
            btn4.setStyleSheet("border-radius: 25px;")  # Make circular
            btn4.move(517, 103)  # Centered between btn3 and btn2, up 4px

        btn3 = self.create_button("XBOX_X", 50, 50)
        if btn3:
            btn3.setText("Button\n3")
            btn3.setParent(gamepad_widget)
            btn3.setStyleSheet("border-radius: 25px;")  # Make circular
            btn3.move(481, 139)  # Size adjusted to keep center

        btn2 = self.create_button("XBOX_B", 50, 50)
        if btn2:
            btn2.setText("Button\n2")
            btn2.setParent(gamepad_widget)
            btn2.setStyleSheet("border-radius: 25px;")  # Make circular
            btn2.move(553, 139)  # Same vertical as btn3, size adjusted

        btn1 = self.create_button("XBOX_A", 50, 50)
        if btn1:
            btn1.setText("Button\n1")
            btn1.setParent(gamepad_widget)
            btn1.setStyleSheet("border-radius: 25px;")  # Make circular
            btn1.move(517, 178)  # Centered between btn3 and btn2, down 6px

        # Create horizontal container for calibration (left) and gamepad (right)
        controller_and_calibration_container = QWidget()
        controller_calibration_layout = QHBoxLayout()
        controller_calibration_layout.setSpacing(20)
        controller_calibration_layout.setContentsMargins(0, 0, 0, 0)
        controller_and_calibration_container.setLayout(controller_calibration_layout)

        # Calibration group (LEFT SIDE)
        calibration_group = QGroupBox(tr("GamingTab", "Analog Calibration"))
        calibration_group.setMaximumWidth(250)
        calib_content_layout = QVBoxLayout()
        calib_content_layout.setSpacing(8)
        calibration_group.setLayout(calib_content_layout)

        # Helper function to create compact slider
        def create_compact_slider(label_text, default_value):
            widget = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(2)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)

            # Label with value inline
            label_with_value = QLabel(f"{label_text}: {default_value/10:.1f}")
            layout.addWidget(label_with_value)

            # Slider
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(25)
            slider.setValue(default_value)
            slider.setTickInterval(1)
            slider.setMinimumWidth(200)
            layout.addWidget(slider)

            # Connect slider to update label
            slider.valueChanged.connect(
                lambda val, lbl=label_with_value, txt=label_text: lbl.setText(f"{txt}: {val/10:.1f}")
            )

            return widget, slider, label_with_value

        # LS (Left Stick) Calibration
        ls_label = QLabel("<b>Left Stick</b>")
        calib_content_layout.addWidget(ls_label)

        ls_min_widget, self.ls_min_slider, self.ls_min_label = create_compact_slider(
            tr("GamingTab", "Min Travel (mm)"), 10
        )
        calib_content_layout.addWidget(ls_min_widget)

        ls_max_widget, self.ls_max_slider, self.ls_max_label = create_compact_slider(
            tr("GamingTab", "Max Travel (mm)"), 20
        )
        calib_content_layout.addWidget(ls_max_widget)

        # RS (Right Stick) Calibration
        rs_label = QLabel("<b>Right Stick</b>")
        calib_content_layout.addWidget(rs_label)

        rs_min_widget, self.rs_min_slider, self.rs_min_label = create_compact_slider(
            tr("GamingTab", "Min Travel (mm)"), 10
        )
        calib_content_layout.addWidget(rs_min_widget)

        rs_max_widget, self.rs_max_slider, self.rs_max_label = create_compact_slider(
            tr("GamingTab", "Max Travel (mm)"), 20
        )
        calib_content_layout.addWidget(rs_max_widget)

        # Triggers Calibration
        trigger_label = QLabel("<b>Triggers</b>")
        calib_content_layout.addWidget(trigger_label)

        trigger_min_widget, self.trigger_min_slider, self.trigger_min_label = create_compact_slider(
            tr("GamingTab", "Min Travel (mm)"), 10
        )
        calib_content_layout.addWidget(trigger_min_widget)

        trigger_max_widget, self.trigger_max_slider, self.trigger_max_label = create_compact_slider(
            tr("GamingTab", "Max Travel (mm)"), 20
        )
        calib_content_layout.addWidget(trigger_max_widget)

        # Add buttons (Save, Load, Reset)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        save_btn = QPushButton(tr("GamingTab", "Save"))
        save_btn.setFixedSize(75, 30)
        save_btn.clicked.connect(self.on_save_calibration)
        button_layout.addWidget(save_btn)

        load_btn = QPushButton(tr("GamingTab", "Load"))
        load_btn.setFixedSize(75, 30)
        load_btn.clicked.connect(self.on_load_calibration)
        button_layout.addWidget(load_btn)

        reset_btn = QPushButton(tr("GamingTab", "Reset"))
        reset_btn.setFixedSize(75, 30)
        reset_btn.clicked.connect(self.on_reset_calibration)
        button_layout.addWidget(reset_btn)

        calib_content_layout.addLayout(button_layout)

        # Add outer spacers to push calibration and controller together
        controller_calibration_layout.addStretch(1)

        # Add calibration group to left side of horizontal layout
        controller_calibration_layout.addWidget(calibration_group, alignment=Qt.AlignTop)

        # Add gamepad widget to right side of horizontal layout
        controller_calibration_layout.addWidget(gamepad_widget)

        # Add outer spacer on the right
        controller_calibration_layout.addStretch(1)

        # Add the horizontal container to main layout
        self.main_layout.addWidget(controller_and_calibration_container)
        self.main_layout.addStretch()

    def clear_layout(self, layout):
        """Helper to clear a layout recursively"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def has_buttons(self):
        """Check if tab has any buttons"""
        return len(self.gaming_keycodes) > 0

    def relabel_buttons(self):
        """Relabel all buttons (called when keymap changes)"""
        self.recreate_buttons(self.current_keycode_filter)

    def get_keyboard(self):
        """Helper method to get keyboard reference"""
        # Try to get keyboard from stored reference
        if self.keyboard is not None:
            return self.keyboard

        # Try to get from parent chain
        try:
            parent = self.parent()
            if hasattr(parent, 'keyboard') and parent.keyboard is not None:
                return parent.keyboard
            # Try parent's parent
            if hasattr(parent, 'parent') and callable(parent.parent):
                grandparent = parent.parent()
                if hasattr(grandparent, 'keyboard') and grandparent.keyboard is not None:
                    return grandparent.keyboard
        except:
            pass

        return None

    def on_save_calibration(self):
        """Save analog calibration settings to keyboard (Gaming tab version)"""
        keyboard = self.get_keyboard()
        if not keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        try:
            # Get values from sliders
            ls_min = self.ls_min_slider.value()
            ls_max = self.ls_max_slider.value()
            rs_min = self.rs_min_slider.value()
            rs_max = self.rs_max_slider.value()
            trigger_min = self.trigger_min_slider.value()
            trigger_max = self.trigger_max_slider.value()

            # Validate ranges
            if ls_min >= ls_max:
                QMessageBox.warning(None, "Invalid Range", "LS Min travel must be less than LS Max travel")
                return
            if rs_min >= rs_max:
                QMessageBox.warning(None, "Invalid Range", "RS Min travel must be less than RS Max travel")
                return
            if trigger_min >= trigger_max:
                QMessageBox.warning(None, "Invalid Range", "Trigger Min travel must be less than Trigger Max travel")
                return

            # Save to keyboard
            success = keyboard.set_gaming_analog_config(ls_min, ls_max, rs_min, rs_max, trigger_min, trigger_max)

            if success:
                QMessageBox.information(None, "Success", "Calibration settings saved successfully")
            else:
                QMessageBox.warning(None, "Error", "Failed to save calibration settings")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error saving calibration: {str(e)}")

    def on_load_calibration(self):
        """Load analog calibration from keyboard (Gaming tab version)"""
        keyboard = self.get_keyboard()
        if not keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        try:
            settings = keyboard.get_gaming_settings()
            if settings:
                # Block signals while updating
                self.ls_min_slider.blockSignals(True)
                self.ls_max_slider.blockSignals(True)
                self.rs_min_slider.blockSignals(True)
                self.rs_max_slider.blockSignals(True)
                self.trigger_min_slider.blockSignals(True)
                self.trigger_max_slider.blockSignals(True)

                # Set slider values
                self.ls_min_slider.setValue(settings.get('ls_min_travel_mm_x10', 10))
                self.ls_max_slider.setValue(settings.get('ls_max_travel_mm_x10', 20))
                self.rs_min_slider.setValue(settings.get('rs_min_travel_mm_x10', 10))
                self.rs_max_slider.setValue(settings.get('rs_max_travel_mm_x10', 20))
                self.trigger_min_slider.setValue(settings.get('trigger_min_travel_mm_x10', 10))
                self.trigger_max_slider.setValue(settings.get('trigger_max_travel_mm_x10', 20))

                # Unblock signals
                self.ls_min_slider.blockSignals(False)
                self.ls_max_slider.blockSignals(False)
                self.rs_min_slider.blockSignals(False)
                self.rs_max_slider.blockSignals(False)
                self.trigger_min_slider.blockSignals(False)
                self.trigger_max_slider.blockSignals(False)

                # Update labels
                self.ls_min_label.setText(f"Min Travel (mm): {settings.get('ls_min_travel_mm_x10', 10)/10:.1f}")
                self.ls_max_label.setText(f"Max Travel (mm): {settings.get('ls_max_travel_mm_x10', 20)/10:.1f}")
                self.rs_min_label.setText(f"Min Travel (mm): {settings.get('rs_min_travel_mm_x10', 10)/10:.1f}")
                self.rs_max_label.setText(f"Max Travel (mm): {settings.get('rs_max_travel_mm_x10', 20)/10:.1f}")
                self.trigger_min_label.setText(f"Min Travel (mm): {settings.get('trigger_min_travel_mm_x10', 10)/10:.1f}")
                self.trigger_max_label.setText(f"Max Travel (mm): {settings.get('trigger_max_travel_mm_x10', 20)/10:.1f}")

                QMessageBox.information(None, "Success", "Calibration settings loaded from keyboard")
            else:
                QMessageBox.warning(None, "Error", "Failed to load calibration settings")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error loading calibration: {str(e)}")

    def on_reset_calibration(self):
        """Reset calibration to defaults (Gaming tab version)"""
        keyboard = self.get_keyboard()
        if not keyboard:
            QMessageBox.warning(None, "No Keyboard", "No keyboard connected")
            return

        reply = QMessageBox.question(None, "Confirm Reset",
                                     "Reset calibration to defaults (1.0mm min, 2.0mm max)?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # Reset to defaults: 10 for min (1.0mm), 20 for max (2.0mm)
                success = keyboard.set_gaming_analog_config(10, 20, 10, 20, 10, 20)

                if success:
                    # Update UI
                    self.ls_min_slider.blockSignals(True)
                    self.ls_max_slider.blockSignals(True)
                    self.rs_min_slider.blockSignals(True)
                    self.rs_max_slider.blockSignals(True)
                    self.trigger_min_slider.blockSignals(True)
                    self.trigger_max_slider.blockSignals(True)

                    self.ls_min_slider.setValue(10)
                    self.ls_max_slider.setValue(20)
                    self.rs_min_slider.setValue(10)
                    self.rs_max_slider.setValue(20)
                    self.trigger_min_slider.setValue(10)
                    self.trigger_max_slider.setValue(20)

                    self.ls_min_slider.blockSignals(False)
                    self.ls_max_slider.blockSignals(False)
                    self.rs_min_slider.blockSignals(False)
                    self.rs_max_slider.blockSignals(False)
                    self.trigger_min_slider.blockSignals(False)
                    self.trigger_max_slider.blockSignals(False)

                    # Update labels
                    self.ls_min_label.setText("Min Travel (mm): 1.0")
                    self.ls_max_label.setText("Max Travel (mm): 2.0")
                    self.rs_min_label.setText("Min Travel (mm): 1.0")
                    self.rs_max_label.setText("Max Travel (mm): 2.0")
                    self.trigger_min_label.setText("Min Travel (mm): 1.0")
                    self.trigger_max_label.setText("Max Travel (mm): 2.0")

                    QMessageBox.information(None, "Success", "Calibration reset to defaults")
                else:
                    QMessageBox.warning(None, "Error", "Failed to reset calibration")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Error resetting calibration: {str(e)}")


class KeyboardTab(QWidget):
    """Nested tab container for Keyboard-related tabs with side-tab style"""

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.label = "Keyboard"
        self.parent_widget = parent
        self.current_keycode_filter = keycode_filter_any

        # Create the individual tabs
        self.basic_tab = Tab(parent, "Basic", [
            (ansi_100, KEYCODES_SPECIAL + KEYCODES_SHIFTED),
            (ansi_80, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_SHIFTED),
            (ansi_70, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_BASIC_NAV + KEYCODES_SHIFTED),
            (None, KEYCODES_SPECIAL + KEYCODES_BASIC + KEYCODES_SHIFTED),
        ], prefix_buttons=[("Any", -1)])

        self.iso_tab = Tab(parent, "ISO/JIS", [
            (iso_100, KEYCODES_SPECIAL + KEYCODES_SHIFTED + KEYCODES_ISO_KR),
            (iso_80, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_SHIFTED + KEYCODES_ISO_KR),
            (iso_70, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_BASIC_NAV + KEYCODES_SHIFTED +
             KEYCODES_ISO_KR),
            (None, KEYCODES_ISO),
        ], prefix_buttons=[("Any", -1)])

        self.app_tab = SimpleTab(parent, "App", KEYCODES_MEDIA)
        self.advanced_tab = SimpleTab(parent, "Advanced", KEYCODES_BOOT + KEYCODES_MODIFIERS + KEYCODES_QUANTUM)

        # Connect signals
        self.basic_tab.keycode_changed.connect(self.on_keycode_changed)
        self.iso_tab.keycode_changed.connect(self.on_keycode_changed)
        self.app_tab.keycode_changed.connect(self.on_keycode_changed)
        self.advanced_tab.keycode_changed.connect(self.on_keycode_changed)

        # Define sections (tab_widget, display_name)
        self.sections = [
            (self.basic_tab, "Basic"),
            (self.iso_tab, "ISO/JIS"),
            (self.app_tab, "App"),
            (self.advanced_tab, "Advanced")
        ]

        # Create horizontal layout: side tabs on left, content on right
        main_layout_h = QHBoxLayout()
        main_layout_h.setSpacing(0)
        main_layout_h.setContentsMargins(0, 0, 0, 0)

        # Create side tabs container
        side_tabs_container = QWidget()
        side_tabs_container.setObjectName("side_tabs_container")
        side_tabs_container.setStyleSheet("""
            QWidget#side_tabs_container {
                background: palette(window);
                border: 1px solid palette(mid);
                border-right: none;
            }
        """)
        side_tabs_layout = QVBoxLayout(side_tabs_container)
        side_tabs_layout.setSpacing(0)
        side_tabs_layout.setContentsMargins(0, 0, 0, 0)

        self.side_tab_buttons = {}
        for tab_widget, display_name in self.sections:
            btn = QPushButton(display_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(120)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid palette(mid);
                    border-radius: 0px;
                    border-right: none;
                    background: palette(button);
                    text-align: left;
                    padding-left: 15px;
                    font-size: 9pt;
                }
                QPushButton:hover:!checked {
                    background: palette(light);
                }
                QPushButton:checked {
                    background: palette(base);
                    font-weight: 600;
                    border-right: 1px solid palette(base);
                }
            """)
            btn.clicked.connect(lambda checked, dn=display_name: self.show_section(dn))
            side_tabs_layout.addWidget(btn)
            self.side_tab_buttons[display_name] = btn

        side_tabs_layout.addStretch(1)
        main_layout_h.addWidget(side_tabs_container)

        # Create content container
        self.content_wrapper = QWidget()
        self.content_wrapper.setObjectName("content_wrapper")
        self.content_wrapper.setStyleSheet("""
            QWidget#content_wrapper {
                border: 1px solid palette(mid);
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0.1,
                                           stop: 0 palette(alternate-base),
                                           stop: 1 palette(base));
            }
        """)
        self.content_layout = QVBoxLayout(self.content_wrapper)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # Add all section widgets to content area
        self.section_widgets = {}
        for tab_widget, display_name in self.sections:
            tab_widget.hide()
            self.content_layout.addWidget(tab_widget)
            self.section_widgets[display_name] = tab_widget

        main_layout_h.addWidget(self.content_wrapper)
        self.setLayout(main_layout_h)

        # Show first section by default
        self.show_section("Basic")

    def show_section(self, section_name):
        """Show the specified section and update tab button states"""
        # Hide all section widgets
        for widget in self.section_widgets.values():
            widget.hide()

        # Uncheck all tab buttons
        for btn in self.side_tab_buttons.values():
            btn.setChecked(False)

        # Show the selected section widget and check its tab button
        if section_name in self.section_widgets:
            self.section_widgets[section_name].show()
            if section_name in self.side_tab_buttons:
                self.side_tab_buttons[section_name].setChecked(True)

    def on_keycode_changed(self, code):
        self.keycode_changed.emit(code)

    def recreate_buttons(self, keycode_filter):
        self.current_keycode_filter = keycode_filter

        # Store currently selected section before recreating
        current_section = None
        for section_name, widget in self.section_widgets.items():
            if widget.isVisible():
                current_section = section_name
                break

        # Recreate buttons for each tab
        for tab_widget, display_name in self.sections:
            tab_widget.recreate_buttons(keycode_filter)

        # Restore the previously selected section, or default to first
        if current_section and current_section in self.section_widgets:
            self.show_section(current_section)
        else:
            self.show_section("Basic")

    def has_buttons(self):
        return any(tab.has_buttons() for tab, _ in self.sections)

    def relabel_buttons(self):
        for tab_widget, _ in self.sections:
            tab_widget.relabel_buttons()



class ArpeggiatorTab(QScrollArea):
    """Arpeggiator control tab"""
    keycode_changed = pyqtSignal(str)
    
    def __init__(self, parent, label, arp_keycodes, arp_preset_keycodes):
        super().__init__(parent)
        self.label = label
        self.arp_keycodes = arp_keycodes
        self.arp_preset_keycodes = arp_preset_keycodes
        self.current_keycode_filter = None
        
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        # Create initial buttons
        self.recreate_buttons(keycode_filter_any)
        
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    def recreate_buttons(self, keycode_filter):
        self.current_keycode_filter = keycode_filter
        
        # Clear existing layout
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Control section
        control_group = QGroupBox("Arpeggiator Controls")
        control_layout = FlowLayout()
        for keycode in self.arp_keycodes:
            if keycode_filter(keycode):
                if "GATE" not in keycode.qmk_id and "RATE" not in keycode.qmk_id and "MODE" not in keycode.qmk_id:
                    btn = SquareButton()
                    btn.setRelSize(KEYCODE_BTN_RATIO)
                    btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                    btn.keycode = keycode
                    btn.setText(keycode.label)
                    btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                    control_layout.addWidget(btn)
        control_group.setLayout(control_layout)
        self.main_layout.addWidget(control_group)
        
        # Gate section
        gate_group = QGroupBox("Gate Length")
        gate_layout = FlowLayout()
        for keycode in self.arp_keycodes:
            if keycode_filter(keycode) and "GATE" in keycode.qmk_id:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                gate_layout.addWidget(btn)
        gate_group.setLayout(gate_layout)
        self.main_layout.addWidget(gate_group)
        
        # Rate section
        rate_group = QGroupBox("Rate Overrides")
        rate_layout = FlowLayout()
        for keycode in self.arp_keycodes:
            if keycode_filter(keycode) and "RATE" in keycode.qmk_id:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                rate_layout.addWidget(btn)
        rate_group.setLayout(rate_layout)
        self.main_layout.addWidget(rate_group)
        
        # Mode section
        mode_group = QGroupBox("Playback Modes")
        mode_layout = FlowLayout()
        for keycode in self.arp_keycodes:
            if keycode_filter(keycode) and "MODE" in keycode.qmk_id:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                mode_layout.addWidget(btn)
        mode_group.setLayout(mode_layout)
        self.main_layout.addWidget(mode_group)
        
        # Factory Presets section (first 48 presets)
        factory_preset_group = QGroupBox("Factory Presets (48)")
        factory_preset_layout = FlowLayout()
        for i, keycode in enumerate(self.arp_preset_keycodes[:48]):
            if keycode_filter(keycode):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                factory_preset_layout.addWidget(btn)
        factory_preset_group.setLayout(factory_preset_layout)
        self.main_layout.addWidget(factory_preset_group)

        # User Presets section (last 20 presets)
        user_preset_group = QGroupBox("User Presets (20)")
        user_preset_layout = FlowLayout()
        for i, keycode in enumerate(self.arp_preset_keycodes[48:68]):
            if keycode_filter(keycode):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                user_preset_layout.addWidget(btn)
        user_preset_group.setLayout(user_preset_layout)
        self.main_layout.addWidget(user_preset_group)
        
        self.main_layout.addStretch(1)
    
    def has_buttons(self):
        return len(self.arp_keycodes) > 0
    
    def relabel_buttons(self):
        pass  # Implement if needed


class StepSequencerTab(QScrollArea):
    """Step Sequencer control tab"""
    keycode_changed = pyqtSignal(str)
    
    def __init__(self, parent, label, seq_keycodes, seq_preset_keycodes):
        super().__init__(parent)
        self.label = label
        self.seq_keycodes = seq_keycodes
        self.seq_preset_keycodes = seq_preset_keycodes
        self.current_keycode_filter = None
        
        self.scroll_content = QWidget()
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 15, 20, 15)
        self.main_layout.setAlignment(Qt.AlignTop)
        
        # Create initial buttons
        self.recreate_buttons(keycode_filter_any)
        
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    def recreate_buttons(self, keycode_filter):
        self.current_keycode_filter = keycode_filter
        
        # Clear existing layout
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Control section
        control_group = QGroupBox("Sequencer Controls")
        control_layout = FlowLayout()
        for keycode in self.seq_keycodes:
            if keycode_filter(keycode):
                if "GATE" not in keycode.qmk_id and "RATE" not in keycode.qmk_id:
                    btn = SquareButton()
                    btn.setRelSize(KEYCODE_BTN_RATIO)
                    btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                    btn.keycode = keycode
                    btn.setText(keycode.label)
                    btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                    control_layout.addWidget(btn)
        control_group.setLayout(control_layout)
        self.main_layout.addWidget(control_group)
        
        # Gate section
        gate_group = QGroupBox("Gate Length")
        gate_layout = FlowLayout()
        for keycode in self.seq_keycodes:
            if keycode_filter(keycode) and "GATE" in keycode.qmk_id:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                gate_layout.addWidget(btn)
        gate_group.setLayout(gate_layout)
        self.main_layout.addWidget(gate_group)
        
        # Rate section
        rate_group = QGroupBox("Rate Overrides")
        rate_layout = FlowLayout()
        for keycode in self.seq_keycodes:
            if keycode_filter(keycode) and "RATE" in keycode.qmk_id:
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                rate_layout.addWidget(btn)
        rate_group.setLayout(rate_layout)
        self.main_layout.addWidget(rate_group)
        
        # Factory Presets section (first 48 presets)
        factory_preset_group = QGroupBox("Factory Presets (48)")
        factory_preset_layout = FlowLayout()
        for i, keycode in enumerate(self.seq_preset_keycodes[:48]):
            if keycode_filter(keycode):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                factory_preset_layout.addWidget(btn)
        factory_preset_group.setLayout(factory_preset_layout)
        self.main_layout.addWidget(factory_preset_group)

        # User Presets section (last 20 presets)
        user_preset_group = QGroupBox("User Presets (20)")
        user_preset_layout = FlowLayout()
        for i, keycode in enumerate(self.seq_preset_keycodes[48:68]):
            if keycode_filter(keycode):
                btn = SquareButton()
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.clicked.connect(lambda _, k=keycode.qmk_id: self.keycode_changed.emit(k))
                btn.keycode = keycode
                btn.setText(keycode.label)
                btn.setToolTip(keycode.tooltip if keycode.tooltip else keycode.label)
                user_preset_layout.addWidget(btn)
        user_preset_group.setLayout(user_preset_layout)
        self.main_layout.addWidget(user_preset_group)
        
        self.main_layout.addStretch(1)
    
    def has_buttons(self):
        return len(self.seq_keycodes) > 0
    
    def relabel_buttons(self):
        pass  # Implement if needed


class MusicTab(QWidget):
    """Nested tab container for Music-related tabs with side-tab style"""

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.label = "Music"
        self.parent_widget = parent
        self.current_keycode_filter = keycode_filter_any

        # Create the individual tabs
        self.midiswitch_tab = midiTab(parent, "MIDIswitch", KEYCODES_MIDI_UPDOWN)
        self.loop_control_tab = LoopTab(parent, "Loop Control", KEYCODES_LOOP_BUTTONS)
        self.smartchord_tab = SmartChordTab(parent, "SmartChord", KEYCODES_MIDI_CHORD_0, KEYCODES_MIDI_CHORD_1,
                                           KEYCODES_MIDI_CHORD_2, KEYCODES_MIDI_CHORD_3, KEYCODES_MIDI_CHORD_4,
                                           KEYCODES_MIDI_CHORD_5, KEYCODES_MIDI_SCALES,
                                           KEYCODES_MIDI_SMARTCHORDBUTTONS+KEYCODES_MIDI_INVERSION)
        self.arpeggiator_tab = ArpeggiatorTab(parent, "Arpeggiator", KEYCODES_ARPEGGIATOR, KEYCODES_ARPEGGIATOR_PRESETS)
        self.step_sequencer_tab = StepSequencerTab(parent, "Step Sequencer", KEYCODES_STEP_SEQUENCER, KEYCODES_STEP_SEQUENCER_PRESETS)
        self.ear_training_tab = EarTrainerTab(parent, "Ear Training", KEYCODES_EARTRAINER, KEYCODES_CHORDTRAINER)
        self.key_split_tab = KeySplitOnlyTab(parent, "KeySplit", KEYCODES_KEYSPLIT_BUTTONS)
        self.triple_split_tab = TripleSplitTab(parent, "TripleSplit", KEYCODES_KEYSPLIT_BUTTONS)
        self.chord_progressions_tab = ChordProgressionTab(parent, "Chord Progressions")

        # Connect signals
        self.midiswitch_tab.keycode_changed.connect(self.on_keycode_changed)
        self.loop_control_tab.keycode_changed.connect(self.on_keycode_changed)
        self.smartchord_tab.keycode_changed.connect(self.on_keycode_changed)
        self.ear_training_tab.keycode_changed.connect(self.on_keycode_changed)
        self.key_split_tab.keycode_changed.connect(self.on_keycode_changed)
        self.triple_split_tab.keycode_changed.connect(self.on_keycode_changed)
        self.chord_progressions_tab.keycode_changed.connect(self.on_keycode_changed)
        self.arpeggiator_tab.keycode_changed.connect(self.on_keycode_changed)
        self.step_sequencer_tab.keycode_changed.connect(self.on_keycode_changed)

        # Define sections (tab_widget, display_name)
        self.sections = [
            (self.midiswitch_tab, "MIDIswitch"),
            (self.loop_control_tab, "Loop Control"),
            (self.smartchord_tab, "SmartChord"),
            (self.ear_training_tab, "Ear Training"),
            (self.key_split_tab, "KeySplit"),
            (self.triple_split_tab, "TripleSplit"),
            (self.chord_progressions_tab, "Chord Progressions"),
            (self.arpeggiator_tab, "Arpeggiator"),
            (self.step_sequencer_tab, "Step Sequencer")
        ]

        # Create horizontal layout: side tabs on left, content on right
        main_layout_h = QHBoxLayout()
        main_layout_h.setSpacing(0)
        main_layout_h.setContentsMargins(0, 0, 0, 0)

        # Create side tabs container
        side_tabs_container = QWidget()
        side_tabs_container.setObjectName("side_tabs_container")
        side_tabs_container.setStyleSheet("""
            QWidget#side_tabs_container {
                background: palette(window);
                border: 1px solid palette(mid);
                border-right: none;
            }
        """)
        side_tabs_layout = QVBoxLayout(side_tabs_container)
        side_tabs_layout.setSpacing(0)
        side_tabs_layout.setContentsMargins(0, 0, 0, 0)

        self.side_tab_buttons = {}
        for tab_widget, display_name in self.sections:
            btn = QPushButton(display_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(120)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid palette(mid);
                    border-radius: 0px;
                    border-right: none;
                    background: palette(button);
                    text-align: left;
                    padding-left: 15px;
                    font-size: 9pt;
                }
                QPushButton:hover:!checked {
                    background: palette(light);
                }
                QPushButton:checked {
                    background: palette(base);
                    font-weight: 600;
                    border-right: 1px solid palette(base);
                }
            """)
            btn.clicked.connect(lambda checked, dn=display_name: self.show_section(dn))
            side_tabs_layout.addWidget(btn)
            self.side_tab_buttons[display_name] = btn

        side_tabs_layout.addStretch(1)
        main_layout_h.addWidget(side_tabs_container)

        # Create content container
        self.content_wrapper = QWidget()
        self.content_wrapper.setObjectName("content_wrapper")
        self.content_wrapper.setStyleSheet("""
            QWidget#content_wrapper {
                border: 1px solid palette(mid);
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0.1,
                                           stop: 0 palette(alternate-base),
                                           stop: 1 palette(base));
            }
        """)
        self.content_layout = QVBoxLayout(self.content_wrapper)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # Add all section widgets to content area
        self.section_widgets = {}
        for tab_widget, display_name in self.sections:
            tab_widget.hide()
            self.content_layout.addWidget(tab_widget)
            self.section_widgets[display_name] = tab_widget

        main_layout_h.addWidget(self.content_wrapper)
        self.setLayout(main_layout_h)

        # Show first section by default
        self.show_section("MIDIswitch")

    def show_section(self, section_name):
        """Show the specified section and update tab button states"""
        # Hide all section widgets
        for widget in self.section_widgets.values():
            widget.hide()

        # Uncheck all tab buttons
        for btn in self.side_tab_buttons.values():
            btn.setChecked(False)

        # Show the selected section widget and check its tab button
        if section_name in self.section_widgets:
            self.section_widgets[section_name].show()
            if section_name in self.side_tab_buttons:
                self.side_tab_buttons[section_name].setChecked(True)

    def on_keycode_changed(self, code):
        self.keycode_changed.emit(code)

    def recreate_buttons(self, keycode_filter):
        self.current_keycode_filter = keycode_filter

        # Store currently selected section before recreating
        current_section = None
        for section_name, widget in self.section_widgets.items():
            if widget.isVisible():
                current_section = section_name
                break

        # Recreate buttons for each tab
        for tab_widget, display_name in self.sections:
            tab_widget.recreate_buttons(keycode_filter)

        # Restore the previously selected section, or default to first
        if current_section and current_section in self.section_widgets:
            self.show_section(current_section)
        else:
            self.show_section("MIDIswitch")

    def has_buttons(self):
        return any(tab.has_buttons() for tab, _ in self.sections)

    def relabel_buttons(self):
        for tab_widget, _ in self.sections:
            tab_widget.relabel_buttons()


class MIDITab(midiadvancedTab):
    """MIDI tab that directly exposes all MIDI advanced sections"""

    def __init__(self, parent):
        # Initialize with all the MIDI advanced parameters
        super().__init__(parent, "MIDI", KEYCODES_MIDI_ADVANCED, KEYCODES_Program_Change,
                        KEYCODES_MIDI_BANK_LSB, KEYCODES_MIDI_BANK_MSB, KEYCODES_MIDI_CC,
                        KEYCODES_MIDI_CC_FIXED, KEYCODES_MIDI_CC_UP, KEYCODES_MIDI_CC_DOWN,
                        KEYCODES_VELOCITY_STEPSIZE, KEYCODES_CC_STEPSIZE, KEYCODES_MIDI_CHANNEL,
                        KEYCODES_MIDI_VELOCITY, KEYCODES_MIDI_CHANNEL_OS, KEYCODES_MIDI_CHANNEL_HOLD,
                        KEYCODES_MIDI_OCTAVE, KEYCODES_MIDI_KEY, KEYCODES_MIDI_VELOCITY2,
                        KEYCODES_MIDI_VELOCITY3, KEYCODES_MIDI_KEY2, KEYCODES_MIDI_KEY3,
                        KEYCODES_MIDI_OCTAVE2, KEYCODES_MIDI_OCTAVE3, KEYCODES_MIDI_CHANNEL_KEYSPLIT,
                        KEYCODES_MIDI_CHANNEL_KEYSPLIT2, KEYCODES_MIDI_SPLIT_BUTTONS,
                        KEYCODES_CC_ENCODERVALUE, KEYCODES_VELOCITY_SHUFFLE, KEYCODES_EXWHEEL,
                        KEYCODES_SETTINGS1, KEYCODES_SETTINGS2, KEYCODES_SETTINGS3)

        # Update label to just "MIDI"
        self.label = "MIDI"


# =============================================================================
# DAW (Digital Audio Workstation) Shortcut Tabs
# =============================================================================

class DAWSimpleTab(QScrollArea):
    """Simple scrollable tab for DAW shortcuts with organized sections"""

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, keycodes):
        super().__init__(parent)
        self.label = label
        self.keycodes = keycodes
        self.buttons = []
        self.current_keycode_filter = None

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(15)

        self.setWidget(self.container)

    def recreate_buttons(self, keycode_filter):
        self.current_keycode_filter = keycode_filter

        # Clear existing buttons
        for btn in self.buttons:
            btn.setParent(None)
            btn.deleteLater()
        self.buttons.clear()

        # Clear layout
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        # Create sections based on keycode categories
        current_section = None
        current_flow = None
        current_group = None

        for kc in self.keycodes:
            if keycode_filter and not keycode_filter(kc.qmk_id):
                continue

            # Determine section from tooltip
            tooltip = kc.tooltip or ""
            if "Transport" in tooltip or any(x in kc.qmk_id for x in ["PLAY", "STOP", "RECORD", "LOOP", "REWIND", "METRO", "TAP_TEMPO", "FOLLOW", "COUNT", "PAT_MODE"]):
                section = "Transport"
            elif "Edit" in tooltip or any(x in kc.qmk_id for x in ["UNDO", "REDO", "CUT", "COPY", "PASTE", "DUPLICATE", "DELETE", "SPLIT", "QUANTIZE", "CONSOLIDATE", "HEAL", "SEPARATE", "JOIN", "QUICK_QUANT"]):
                section = "Editing"
            elif "Track" in tooltip or any(x in kc.qmk_id for x in ["SOLO", "MUTE", "ARM", "TRACK", "NEW_AUDIO", "NEW_MIDI", "GROUP", "CHANNEL", "NEW_PATTERN", "CLONE", "ADD_CHANNEL", "NEW_TRACK", "NEW_SOFTWARE", "NEW_DRUMMER", "INPUT_MON", "DUPLICATE_TRK"]):
                section = "Track Control"
            elif "Zoom" in tooltip or "Marker" in tooltip or any(x in kc.qmk_id for x in ["ZOOM", "MARKER"]):
                section = "Navigation"
            elif "View" in tooltip or any(x in kc.qmk_id for x in ["SESSION", "BROWSER", "DETAIL", "MIXER", "SENDS", "PLAYLIST", "PIANO_ROLL", "CHANNEL_RACK", "SMART_CTRL", "LIBRARY", "LOOPS", "EDITOR", "NOTE_PAD", "MIX_WIN", "EDIT_WIN", "TRANSPORT", "MIDI_EDIT"]):
                section = "Views"
            elif "Auto" in tooltip or any(x in kc.qmk_id for x in ["AUTO"]):
                section = "Automation"
            elif "Tempo" in tooltip or any(x in kc.qmk_id for x in ["BPM"]):
                section = "Tempo"
            else:
                section = "Other"

            if section != current_section:
                current_section = section
                current_group = QGroupBox(section)
                current_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        border: 1px solid palette(mid);
                        border-radius: 5px;
                        margin-top: 10px;
                        padding-top: 10px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px;
                    }
                """)
                current_flow = FlowLayout()
                current_flow.setSpacing(4)
                current_group.setLayout(current_flow)
                self.container_layout.addWidget(current_group)

            btn = SquareButton()
            btn.setRelSize(KEYCODE_BTN_RATIO)
            btn.setToolTip(kc.tooltip)
            btn.clicked.connect(lambda _, k=kc: self.keycode_changed.emit(k.qmk_id))
            btn.keycode = kc
            self.buttons.append(btn)
            current_flow.addWidget(btn)

        self.container_layout.addStretch(1)
        self.relabel_buttons()

    def relabel_buttons(self):
        KeycodeDisplay.relabel_buttons(self.buttons)

    def has_buttons(self):
        return len(self.buttons) > 0


class DAWTab(QWidget):
    """Nested tab container for DAW-related tabs with side-tab style"""

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.label = "DAW"
        self.parent_widget = parent
        self.current_keycode_filter = keycode_filter_any

        # Create the individual DAW tabs
        self.ableton_tab = DAWSimpleTab(parent, "Ableton Live", KEYCODES_DAW_ABLETON)
        self.fl_studio_tab = DAWSimpleTab(parent, "FL Studio", KEYCODES_DAW_FL)
        self.logic_tab = DAWSimpleTab(parent, "Logic Pro", KEYCODES_DAW_LOGIC)
        self.protools_tab = DAWSimpleTab(parent, "Pro Tools", KEYCODES_DAW_PROTOOLS)
        self.garageband_tab = DAWSimpleTab(parent, "GarageBand", KEYCODES_DAW_GARAGEBAND)

        # Connect signals
        self.ableton_tab.keycode_changed.connect(self.on_keycode_changed)
        self.fl_studio_tab.keycode_changed.connect(self.on_keycode_changed)
        self.logic_tab.keycode_changed.connect(self.on_keycode_changed)
        self.protools_tab.keycode_changed.connect(self.on_keycode_changed)
        self.garageband_tab.keycode_changed.connect(self.on_keycode_changed)

        # Define sections (tab_widget, display_name)
        self.sections = [
            (self.ableton_tab, "Ableton Live"),
            (self.fl_studio_tab, "FL Studio"),
            (self.logic_tab, "Logic Pro"),
            (self.protools_tab, "Pro Tools"),
            (self.garageband_tab, "GarageBand"),
        ]

        # Create horizontal layout: side tabs on left, content on right
        main_layout_h = QHBoxLayout()
        main_layout_h.setSpacing(0)
        main_layout_h.setContentsMargins(0, 0, 0, 0)

        # Create side tabs container
        side_tabs_container = QWidget()
        side_tabs_container.setObjectName("daw_side_tabs_container")
        side_tabs_container.setStyleSheet("""
            QWidget#daw_side_tabs_container {
                background: palette(window);
                border: 1px solid palette(mid);
                border-right: none;
            }
        """)
        side_tabs_layout = QVBoxLayout(side_tabs_container)
        side_tabs_layout.setSpacing(0)
        side_tabs_layout.setContentsMargins(0, 0, 0, 0)

        self.side_tab_buttons = {}
        for tab_widget, display_name in self.sections:
            btn = QPushButton(display_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(120)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid palette(mid);
                    border-radius: 0px;
                    border-right: none;
                    background: palette(button);
                    text-align: left;
                    padding-left: 15px;
                    font-size: 9pt;
                }
                QPushButton:hover:!checked {
                    background: palette(light);
                }
                QPushButton:checked {
                    background: palette(base);
                    font-weight: 600;
                    border-right: 1px solid palette(base);
                }
            """)
            btn.clicked.connect(lambda checked, dn=display_name: self.show_section(dn))
            side_tabs_layout.addWidget(btn)
            self.side_tab_buttons[display_name] = btn

        side_tabs_layout.addStretch(1)
        main_layout_h.addWidget(side_tabs_container)

        # Create content container
        self.content_wrapper = QWidget()
        self.content_wrapper.setObjectName("daw_content_wrapper")
        self.content_wrapper.setStyleSheet("""
            QWidget#daw_content_wrapper {
                border: 1px solid palette(mid);
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0.1,
                                           stop: 0 palette(alternate-base),
                                           stop: 1 palette(base));
            }
        """)
        self.content_layout = QVBoxLayout(self.content_wrapper)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # Add all section widgets to content area
        self.section_widgets = {}
        for tab_widget, display_name in self.sections:
            tab_widget.hide()
            self.content_layout.addWidget(tab_widget)
            self.section_widgets[display_name] = tab_widget

        main_layout_h.addWidget(self.content_wrapper)
        self.setLayout(main_layout_h)

        # Show first section by default
        self.show_section("Ableton Live")

    def show_section(self, section_name):
        """Show the specified section and update tab button states"""
        # Hide all section widgets
        for widget in self.section_widgets.values():
            widget.hide()

        # Uncheck all tab buttons
        for btn in self.side_tab_buttons.values():
            btn.setChecked(False)

        # Show the selected section widget and check its tab button
        if section_name in self.section_widgets:
            self.section_widgets[section_name].show()
            if section_name in self.side_tab_buttons:
                self.side_tab_buttons[section_name].setChecked(True)

    def on_keycode_changed(self, code):
        self.keycode_changed.emit(code)

    def recreate_buttons(self, keycode_filter):
        self.current_keycode_filter = keycode_filter

        # Store currently selected section before recreating
        current_section = None
        for section_name, widget in self.section_widgets.items():
            if widget.isVisible():
                current_section = section_name
                break

        # Recreate buttons for each tab
        for tab_widget, display_name in self.sections:
            tab_widget.recreate_buttons(keycode_filter)

        # Restore the previously selected section, or default to first
        if current_section and current_section in self.section_widgets:
            self.show_section(current_section)
        else:
            self.show_section("Ableton Live")

    def has_buttons(self):
        return any(tab.has_buttons() for tab, _ in self.sections)

    def relabel_buttons(self):
        for tab_widget, _ in self.sections:
            tab_widget.relabel_buttons()


class FilteredTabbedKeycodes(QTabWidget):

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self, parent=None, keycode_filter=keycode_filter_any):
        super().__init__(parent)

        self.keycode_filter = keycode_filter

        self.tabs = [
            KeyboardTab(self),
            MusicTab(self),
            DAWTab(self),
            GamingTab(self, "Gaming", KEYCODES_GAMING),
            MacroTab(self, "Macro", KEYCODES_MACRO_BASE, KEYCODES_MACRO, KEYCODES_TAP_DANCE),
            LayerTab(self, "Layers", KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_OSL),
            LightingTab(self, "Lighting", KEYCODES_BACKLIGHT, KEYCODES_RGBSAVE, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_COLOR, KEYCODES_RGB_KC_CUSTOM2),
            MIDITab(self),
            SimpleTab(self, " ", KEYCODES_CLEAR),
        ]

        for tab in self.tabs:
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

    def on_keymap_override(self):
        for tab in self.tabs:
            tab.relabel_buttons()

    def set_keyboard(self, keyboard):
        """Set keyboard reference for tabs that need it (e.g., GamingTab, MacroTab)"""
        for tab in self.tabs:
            if hasattr(tab, 'set_keyboard') and callable(tab.set_keyboard):
                tab.set_keyboard(keyboard)
            elif hasattr(tab, 'keyboard'):
                tab.keyboard = keyboard


class TabbedKeycodes(QWidget):

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.target = None
        self.is_tray = False

        self.layout = QVBoxLayout()

        self.all_keycodes = FilteredTabbedKeycodes(self)
        self.basic_keycodes = FilteredTabbedKeycodes(self, keycode_filter=keycode_filter_masked)
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

    def set_keyboard(self, keyboard):
        """Set keyboard reference for all tab widgets"""
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.set_keyboard(keyboard)

