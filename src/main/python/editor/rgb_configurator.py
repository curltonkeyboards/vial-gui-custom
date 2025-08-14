# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy, QGridLayout, QLabel, QSlider, \
    QComboBox, QColorDialog, QCheckBox

from editor.basic_editor import BasicEditor
from widgets.clickable_label import ClickableLabel
from util import tr
from vial_device import VialKeyboard
from protocol.constants import CMD_VIA_VIAL_PREFIX, CMD_VIAL_LAYER_RGB_SAVE, CMD_VIAL_LAYER_RGB_LOAD, \
    CMD_VIAL_LAYER_RGB_ENABLE, CMD_VIAL_LAYER_RGB_GET_STATUS, CMD_VIAL_CUSTOM_ANIM_SET_PARAM, \
    CMD_VIAL_CUSTOM_ANIM_GET_PARAM, CMD_VIAL_CUSTOM_ANIM_SET_ALL, CMD_VIAL_CUSTOM_ANIM_GET_ALL, \
    CMD_VIAL_CUSTOM_ANIM_SAVE, CMD_VIAL_CUSTOM_ANIM_LOAD, CMD_VIAL_CUSTOM_ANIM_RESET_SLOT, \
    CMD_VIAL_CUSTOM_ANIM_GET_STATUS


class QmkRgblightEffect:

    def __init__(self, idx, name, color_picker):
        self.idx = idx
        self.name = name
        self.color_picker = color_picker


QMK_RGBLIGHT_EFFECTS = [
    QmkRgblightEffect(0, "All Off", False),
    QmkRgblightEffect(1, "Solid Color", True),
    QmkRgblightEffect(2, "Breathing 1", True),
    QmkRgblightEffect(3, "Breathing 2", True),
    QmkRgblightEffect(4, "Breathing 3", True),
    QmkRgblightEffect(5, "Breathing 4", True),
    QmkRgblightEffect(6, "Rainbow Mood 1", False),
    QmkRgblightEffect(7, "Rainbow Mood 2", False),
    QmkRgblightEffect(8, "Rainbow Mood 3", False),
    QmkRgblightEffect(9, "Rainbow Swirl 1", False),
    QmkRgblightEffect(10, "Rainbow Swirl 2", False),
    QmkRgblightEffect(11, "Rainbow Swirl 3", False),
    QmkRgblightEffect(12, "Rainbow Swirl 4", False),
    QmkRgblightEffect(13, "Rainbow Swirl 5", False),
    QmkRgblightEffect(14, "Rainbow Swirl 6", False),
    QmkRgblightEffect(15, "Snake 1", True),
    QmkRgblightEffect(16, "Snake 2", True),
    QmkRgblightEffect(17, "Snake 3", True),
    QmkRgblightEffect(18, "Snake 4", True),
    QmkRgblightEffect(19, "Snake 5", True),
    QmkRgblightEffect(20, "Snake 6", True),
    QmkRgblightEffect(21, "Knight 1", True),
    QmkRgblightEffect(22, "Knight 2", True),
    QmkRgblightEffect(23, "Knight 3", True),
    QmkRgblightEffect(24, "Christmas", True),
    QmkRgblightEffect(25, "Gradient 1", True),
    QmkRgblightEffect(26, "Gradient 2", True),
    QmkRgblightEffect(27, "Gradient 3", True),
    QmkRgblightEffect(28, "Gradient 4", True),
    QmkRgblightEffect(29, "Gradient 5", True),
    QmkRgblightEffect(30, "Gradient 6", True),
    QmkRgblightEffect(31, "Gradient 7", True),
    QmkRgblightEffect(32, "Gradient 8", True),
    QmkRgblightEffect(33, "Gradient 9", True),
    QmkRgblightEffect(34, "Gradient 10", True),
    QmkRgblightEffect(35, "RGB Test", True),
    QmkRgblightEffect(36, "Alternating", True),
]


class VialRGBEffect:

    def __init__(self, idx, name):
        self.idx = idx
        self.name = name


VIALRGB_EFFECTS = [
    VialRGBEffect(0, "Disable"),
    VialRGBEffect(1, "Direct Control"),
    VialRGBEffect(2, "Solid Color"),
    VialRGBEffect(3, "Alphas Mods"),
    VialRGBEffect(4, "Gradient Up Down"),
    VialRGBEffect(5, "Gradient Left Right"),
    VialRGBEffect(6, "Breathing"),
    VialRGBEffect(7, "Band Sat"),
    VialRGBEffect(8, "Band Val"),
    VialRGBEffect(9, "Band Pinwheel Sat"),
    VialRGBEffect(10, "Band Pinwheel Val"),
    VialRGBEffect(11, "Band Spiral Sat"),
    VialRGBEffect(12, "Band Spiral Val"),
    VialRGBEffect(13, "Cycle All"),
    VialRGBEffect(14, "Cycle Left Right"),
    VialRGBEffect(15, "Cycle Up Down"),
    VialRGBEffect(16, "Rainbow Moving Chevron"),
    VialRGBEffect(17, "Cycle Out In"),
    VialRGBEffect(18, "Cycle Out In Dual"),
    VialRGBEffect(19, "Cycle Pinwheel"),
    VialRGBEffect(20, "Cycle Spiral"),
    VialRGBEffect(21, "Dual Beacon"),
    VialRGBEffect(22, "Rainbow Beacon"),
    VialRGBEffect(23, "Rainbow Pinwheels"),
    VialRGBEffect(24, "Raindrops"),
    VialRGBEffect(25, "Jellybean Raindrops"),
    VialRGBEffect(26, "Hue Breathing"),
    VialRGBEffect(27, "Hue Pendulum"),
    VialRGBEffect(28, "Hue Wave"),
    VialRGBEffect(29, "Typing Heatmap"),
    VialRGBEffect(30, "Digital Rain"),
    VialRGBEffect(31, "Solid Reactive Simple"),
    VialRGBEffect(32, "Solid Reactive"),
    VialRGBEffect(33, "Solid Reactive Wide"),
    VialRGBEffect(34, "Solid Reactive Multiwide"),
    VialRGBEffect(35, "Solid Reactive Cross"),
    VialRGBEffect(36, "Solid Reactive Multicross"),
    VialRGBEffect(37, "Solid Reactive Nexus"),
    VialRGBEffect(38, "Solid Reactive Multinexus"),
    VialRGBEffect(39, "Splash"),
    VialRGBEffect(40, "Multisplash"),
    VialRGBEffect(41, "Solid Splash"),
    VialRGBEffect(42, "Solid Multisplash"),
    VialRGBEffect(43, "Pixel Rain"),
    VialRGBEffect(44, "Pixel Fractal"),
    VialRGBEffect(45, "MIDI Switch Auto Light"),
    VialRGBEffect(46, "Reactive Lightning"),
    VialRGBEffect(47, "Reactive Ripple"),
    VialRGBEffect(48, "Reactive Fireworks"),
    VialRGBEffect(49, "Comet Trail"),
    VialRGBEffect(50, "Tetris Vertical"),
    VialRGBEffect(51, "Tetris Horizontal"),
    VialRGBEffect(52, "Fireplace"),
    VialRGBEffect(53, "Pong"),
    VialRGBEffect(54, "L/R Sweep Static"),
    VialRGBEffect(55, "L/R Sweep Rainbow"),
    VialRGBEffect(56, "L/R Sweep Random"),
    VialRGBEffect(57, "BPM Pulse Fade"),
    VialRGBEffect(58, "BPM Pulse Fade Disco"),
    VialRGBEffect(59, "BPM Pulse Fade Backlight"),
    VialRGBEffect(60, "BPM Pulse Fade Disco Backlight"),
    VialRGBEffect(61, "BPM Quadrants"),
    VialRGBEffect(62, "BPM Quadrants Disco"),
    VialRGBEffect(63, "BPM Quadrants Backlight"),
    VialRGBEffect(64, "BPM Quadrants Disco Backlight"),
    VialRGBEffect(65, "BPM Row"),
    VialRGBEffect(66, "BPM Row Disco"),
    VialRGBEffect(67, "BPM Row Backlight"),
    VialRGBEffect(68, "BPM Row Disco Backlight"),
    VialRGBEffect(69, "BPM Column"),
    VialRGBEffect(70, "BPM Column Disco"),
    VialRGBEffect(71, "BPM Column Backlight"),
    VialRGBEffect(72, "BPM Column Disco Backlight"),
    VialRGBEffect(73, "BPM All"),
    VialRGBEffect(74, "BPM All Disco"),
    VialRGBEffect(75, "BPM All Backlight"),
    VialRGBEffect(76, "BPM All Disco Backlight"), 
    VialRGBEffect(77, "Channel Colors"),
    VialRGBEffect(78, "Channel Colors Backlight"),
    VialRGBEffect(79, "Loop Zones"),
    VialRGBEffect(80, "Loop Zones Backlight"),
    VialRGBEffect(81, "Truekey Wide"),
    VialRGBEffect(82, "Truekey Wide Backlight"),
    VialRGBEffect(83, "Truekey Basic"),
    VialRGBEffect(84, "Truekey Basic Backlight"),
    VialRGBEffect(85, "Truekey Heatmap Narrow"),
    VialRGBEffect(86, "Truekey Heatmap Narrow Backlight"),
    VialRGBEffect(87, "Truekey Heatmap Wide"),
    VialRGBEffect(88, "Truekey Heatmap Wide Backlight"),
    VialRGBEffect(89, "Quadrants Sustain"),
    VialRGBEffect(90, "Quadrants Sustain Backlight"),
    VialRGBEffect(91, "Truekey Sustain"),
    VialRGBEffect(92, "Truekey Sustain Backlight"),
    VialRGBEffect(93, "Truekey Subwoof"),
    VialRGBEffect(94, "Truekey Line"),
    VialRGBEffect(95, "Truekey Row"),
    # Custom Slot Effects
    VialRGBEffect(96, "Custom Slot 0"),
    VialRGBEffect(97, "Custom Slot 1"),
    VialRGBEffect(98, "Custom Slot 2"),
    VialRGBEffect(99, "Custom Slot 3"),
    VialRGBEffect(100, "Custom Slot 4"),
    VialRGBEffect(101, "Custom Slot 5"),
    VialRGBEffect(102, "Custom Slot 6"),
    VialRGBEffect(103, "Custom Slot 7"),
    VialRGBEffect(104, "Custom Slot 8"),
    VialRGBEffect(105, "Custom Slot 9"),
]


# Custom Lights Configuration Constants
CUSTOM_LIGHT_LIVE_POSITIONS = [
    "TrueKey", "Zone", "Quadrant", "Note Row Col0", "Note Row Col13", 
    "Note Col Row0", "Note Col Row4", "Note Row Mixed", "Note Col Mixed"
]

CUSTOM_LIGHT_MACRO_POSITIONS = [
    "TrueKey", "Zone", "Quadrant", "Note Row Col0", "Note Row Col13",
    "Note Col Row0", "Note Col Row4", "Loop Row Col0", "Loop Row Col13", 
    "Loop Row Alt", "Loop Col"
]

CUSTOM_LIGHT_ANIMATIONS = [
    "None", "Heat", "Sustain", "Moving Dots Row", "Moving Dots Col"
]

CUSTOM_LIGHT_BACKGROUNDS = [
    "None", "Static", "BPM Pulse Fade", "BPM All Disco"
]

CUSTOM_LIGHT_COLOR_TYPES = [
    "Base", "Channel", "Macro", "Heat"
]

CUSTOM_LIGHT_PULSE_MODES = [
    "None", "Live Only", "Macro Only", "All"
]

CUSTOM_LIGHT_PRESETS = [
    "Classic TrueKey", "Heat Effects", "Moving Dots", "BPM Disco",
    "Zone Lighting", "Sustain Mode", "Performance Setup"
]


class BasicHandler(QObject):

    update = pyqtSignal()

    def __init__(self, container):
        super().__init__()
        self.device = self.keyboard = None
        self.widgets = []

    def set_device(self, device):
        self.device = device
        if self.valid():
            self.keyboard = self.device.keyboard
            self.show()
        else:
            self.hide()

    def show(self):
        for w in self.widgets:
            w.show()

    def hide(self):
        for w in self.widgets:
            w.hide()

    def block_signals(self):
        for w in self.widgets:
            w.blockSignals(True)

    def unblock_signals(self):
        for w in self.widgets:
            w.blockSignals(False)

    def update_from_keyboard(self):
        raise NotImplementedError

    def valid(self):
        raise NotImplementedError


class QmkRgblightHandler(BasicHandler):

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        self.lbl_underglow_effect = QLabel(tr("RGBConfigurator", "Underglow Effect"))
        container.addWidget(self.lbl_underglow_effect, row, 0)
        self.underglow_effect = QComboBox()
        for ef in QMK_RGBLIGHT_EFFECTS:
            self.underglow_effect.addItem(ef.name)
        container.addWidget(self.underglow_effect, row, 1)

        self.lbl_underglow_brightness = QLabel(tr("RGBConfigurator", "Underglow Brightness"))
        container.addWidget(self.lbl_underglow_brightness, row + 1, 0)
        self.underglow_brightness = QSlider(QtCore.Qt.Horizontal)
        self.underglow_brightness.setMinimum(0)
        self.underglow_brightness.setMaximum(255)
        self.underglow_brightness.valueChanged.connect(self.on_underglow_brightness_changed)
        container.addWidget(self.underglow_brightness, row + 1, 1)

        self.lbl_underglow_color = QLabel(tr("RGBConfigurator", "Underglow Color"))
        container.addWidget(self.lbl_underglow_color, row + 2, 0)
        self.underglow_color = ClickableLabel(" ")
        self.underglow_color.clicked.connect(self.on_underglow_color)
        container.addWidget(self.underglow_color, row + 2, 1)

        self.underglow_effect.currentIndexChanged.connect(self.on_underglow_effect_changed)

        self.widgets = [self.lbl_underglow_effect, self.underglow_effect, self.lbl_underglow_brightness,
                        self.underglow_brightness, self.lbl_underglow_color, self.underglow_color]

    def update_from_keyboard(self):
        if not self.valid():
            return

        self.underglow_brightness.setValue(self.device.keyboard.underglow_brightness)
        self.underglow_effect.setCurrentIndex(self.device.keyboard.underglow_effect)
        self.underglow_color.setStyleSheet("QWidget { background-color: %s}" % self.current_color().name())

    def valid(self):
        return isinstance(self.device, VialKeyboard) and self.device.keyboard.lighting_qmk_rgblight

    def on_underglow_brightness_changed(self, value):
        self.device.keyboard.set_qmk_rgblight_brightness(value)
        self.update.emit()

    def on_underglow_effect_changed(self, index):
        self.lbl_underglow_color.setVisible(QMK_RGBLIGHT_EFFECTS[index].color_picker)
        self.underglow_color.setVisible(QMK_RGBLIGHT_EFFECTS[index].color_picker)

        self.device.keyboard.set_qmk_rgblight_effect(index)

    def on_underglow_color(self):
        self.dlg_color = QColorDialog()
        self.dlg_color.setModal(True)
        self.dlg_color.finished.connect(self.on_underglow_color_finished)
        self.dlg_color.setCurrentColor(self.current_color())
        self.dlg_color.show()

    def on_underglow_color_finished(self):
        color = self.dlg_color.selectedColor()
        if not color.isValid():
            return
        self.underglow_color.setStyleSheet("QWidget { background-color: %s}" % color.name())
        h, s, v, a = color.getHsvF()
        if h < 0:
            h = 0
        self.device.keyboard.set_qmk_rgblight_color(int(255 * h), int(255 * s), int(255 * v))
        self.update.emit()

    def current_color(self):
        return QColor.fromHsvF(self.device.keyboard.underglow_color[0] / 255.0,
                               self.device.keyboard.underglow_color[1] / 255.0,
                               self.device.keyboard.underglow_brightness / 255.0)


class QmkBacklightHandler(BasicHandler):

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        self.lbl_backlight_brightness = QLabel(tr("RGBConfigurator", "Backlight Brightness"))
        container.addWidget(self.lbl_backlight_brightness, row, 0)
        self.backlight_brightness = QSlider(QtCore.Qt.Horizontal)
        self.backlight_brightness.setMinimum(0)
        self.backlight_brightness.setMaximum(255)
        self.backlight_brightness.valueChanged.connect(self.on_backlight_brightness_changed)
        container.addWidget(self.backlight_brightness, row, 1)

        self.lbl_backlight_breathing = QLabel(tr("RGBConfigurator", "Backlight Breathing"))
        container.addWidget(self.lbl_backlight_breathing, row + 1, 0)
        self.backlight_breathing = QCheckBox()
        self.backlight_breathing.stateChanged.connect(self.on_backlight_breathing_changed)
        container.addWidget(self.backlight_breathing, row + 1, 1)

        self.widgets = [self.lbl_backlight_brightness, self.backlight_brightness, self.lbl_backlight_breathing,
                        self.backlight_breathing]

    def update_from_keyboard(self):
        if not self.valid():
            return

        self.backlight_brightness.setValue(self.device.keyboard.backlight_brightness)
        self.backlight_breathing.setChecked(self.device.keyboard.backlight_effect == 1)

    def valid(self):
        return isinstance(self.device, VialKeyboard) and self.device.keyboard.lighting_qmk_backlight

    def on_backlight_brightness_changed(self, value):
        self.device.keyboard.set_qmk_backlight_brightness(value)

    def on_backlight_breathing_changed(self, checked):
        self.device.keyboard.set_qmk_backlight_effect(int(checked))


class VialRGBHandler(BasicHandler):

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        self.lbl_rgb_effect = QLabel(tr("RGBConfigurator", "RGB Effect"))
        container.addWidget(self.lbl_rgb_effect, row, 0)
        self.rgb_effect = QComboBox()
        self.rgb_effect.addItem("0")
        self.rgb_effect.addItem("1")
        self.rgb_effect.addItem("2")
        self.rgb_effect.addItem("3")
        self.rgb_effect.currentIndexChanged.connect(self.on_rgb_effect_changed)
        container.addWidget(self.rgb_effect, row, 1)

        self.lbl_rgb_color = QLabel(tr("RGBConfigurator", "RGB Color"))
        container.addWidget(self.lbl_rgb_color, row + 1, 0)
        self.rgb_color = ClickableLabel(" ")
        self.rgb_color.clicked.connect(self.on_rgb_color)
        container.addWidget(self.rgb_color, row + 1, 1)

        self.lbl_rgb_brightness = QLabel(tr("RGBConfigurator", "RGB Brightness"))
        container.addWidget(self.lbl_rgb_brightness, row + 2, 0)
        self.rgb_brightness = QSlider(QtCore.Qt.Horizontal)
        self.rgb_brightness.setMinimum(0)
        self.rgb_brightness.setMaximum(255)
        self.rgb_brightness.valueChanged.connect(self.on_rgb_brightness_changed)
        container.addWidget(self.rgb_brightness, row + 2, 1)

        self.lbl_rgb_speed = QLabel(tr("RGBConfigurator", "RGB Speed"))
        container.addWidget(self.lbl_rgb_speed, row + 3, 0)
        self.rgb_speed = QSlider(QtCore.Qt.Horizontal)
        self.rgb_speed.setMinimum(0)
        self.rgb_speed.setMaximum(255)
        self.rgb_speed.valueChanged.connect(self.on_rgb_speed_changed)
        container.addWidget(self.rgb_speed, row + 3, 1)

        self.widgets = [self.lbl_rgb_effect, self.rgb_effect, self.lbl_rgb_brightness, self.rgb_brightness,
                        self.lbl_rgb_color, self.rgb_color, self.lbl_rgb_speed, self.rgb_speed]

        self.effects = []

    def on_rgb_brightness_changed(self, value):
        self.keyboard.set_vialrgb_brightness(value)

    def on_rgb_speed_changed(self, value):
        self.keyboard.set_vialrgb_speed(value)

    def on_rgb_effect_changed(self, index):
        self.keyboard.set_vialrgb_mode(self.effects[index].idx)

    def on_rgb_color(self):
        self.dlg_color = QColorDialog()
        self.dlg_color.setModal(True)
        self.dlg_color.finished.connect(self.on_rgb_color_finished)
        self.dlg_color.setCurrentColor(self.current_color())
        self.dlg_color.show()

    def on_rgb_color_finished(self):
        color = self.dlg_color.selectedColor()
        if not color.isValid():
            return
        self.rgb_color.setStyleSheet("QWidget { background-color: %s}" % color.name())
        h, s, v, a = color.getHsvF()
        if h < 0:
            h = 0
        self.keyboard.set_vialrgb_color(int(255 * h), int(255 * s), self.keyboard.rgb_hsv[2])
        self.update.emit()

    def current_color(self):
        return QColor.fromHsvF(self.keyboard.rgb_hsv[0] / 255.0,
                               self.keyboard.rgb_hsv[1] / 255.0,
                               1.0)

    def rebuild_effects(self):
        self.effects = []
        for effect in VIALRGB_EFFECTS:
            if effect.idx in self.keyboard.rgb_supported_effects:
                self.effects.append(effect)

        self.rgb_effect.clear()
        for effect in self.effects:
            self.rgb_effect.addItem(effect.name)

    def update_from_keyboard(self):
        if not self.valid():
            return

        self.rebuild_effects()
        for x, effect in enumerate(self.effects):
            if effect.idx == self.keyboard.rgb_mode:
                self.rgb_effect.setCurrentIndex(x)
                break
        self.rgb_brightness.setMaximum(self.keyboard.rgb_maximum_brightness)
        self.rgb_brightness.setValue(self.keyboard.rgb_hsv[2])
        self.rgb_speed.setValue(self.keyboard.rgb_speed)
        self.rgb_color.setStyleSheet("QWidget { background-color: %s}" % self.current_color().name())

    def valid(self):
        return isinstance(self.device, VialKeyboard) and self.device.keyboard.lighting_vialrgb


class LayerRGBHandler(BasicHandler):
    """Handler for per-layer RGB functionality - always shows all buttons"""

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        # Enable per-layer RGB checkbox
        self.lbl_layer_rgb_enable = QLabel(tr("RGBConfigurator", "Enable Per-Layer RGB"))
        container.addWidget(self.lbl_layer_rgb_enable, row, 0)
        self.layer_rgb_enable = QCheckBox()
        self.layer_rgb_enable.stateChanged.connect(self.on_layer_rgb_enable_changed)
        container.addWidget(self.layer_rgb_enable, row, 1)

        # Layer buttons container
        self.lbl_layer_buttons = QLabel(tr("RGBConfigurator", "Save RGB to Layer"))
        container.addWidget(self.lbl_layer_buttons, row + 1, 0)
        
        # Create a grid layout for layer buttons (3 rows x 4 columns)
        self.layer_buttons_widget = QWidget()
        self.layer_buttons_layout = QGridLayout(self.layer_buttons_widget)
        self.layer_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.layer_buttons_layout.setSpacing(2)  # Smaller spacing between buttons
        container.addWidget(self.layer_buttons_widget, row + 1, 1)

        self.layer_buttons = []
        self.per_layer_enabled = False
        self.initial_load_complete = False  # Track if we've done the initial load
        self.user_set_state = None  # Track what the user manually set

        self.widgets = [self.lbl_layer_rgb_enable, self.layer_rgb_enable, 
                       self.lbl_layer_buttons, self.layer_buttons_widget]

        # Create initial buttons (they will be updated when device connects)
        self.create_layer_buttons()

    def create_layer_buttons(self):
        """Create buttons for each layer in a 3x4 grid - always create 12 buttons regardless of layer count"""
        # Clear existing buttons
        for button in self.layer_buttons:
            button.setParent(None)
        self.layer_buttons.clear()

        # Always create 12 buttons for 3x4 grid regardless of layer count
        for layer in range(12):
            button = QPushButton(f"Layer {layer}")
            button.clicked.connect(lambda checked, l=layer: self.on_save_to_layer(l))
            button.setEnabled(self.per_layer_enabled)
            button.setMaximumWidth(80)  # Set a reasonable button width
            button.setMinimumWidth(60)  # Minimum width for readability
            
            # Calculate row and column for 3x4 grid
            row = layer // 4  # 4 buttons per row
            col = layer % 4   # Column position within row
            
            self.layer_buttons_layout.addWidget(button, row, col)
            self.layer_buttons.append(button)

    def update_from_keyboard(self):
        """Update from keyboard - NEVER update checkbox after initial load"""
        if not self.valid():
            return

        # Block signals to prevent triggering state change events during update
        self.block_signals()

        # Only update checkbox state on the very first load
        # After that, NEVER touch the checkbox regardless of keyboard state
        if not self.initial_load_complete:
            print("LayerRGBHandler: Initial load - checking keyboard state")
            # Try to get per-layer RGB status if methods exist
            if hasattr(self.device.keyboard, 'get_layer_rgb_status'):
                try:
                    data = self.device.keyboard.get_layer_rgb_status()
                    if data and len(data) > 0:
                        keyboard_state = bool(data[0])
                        self.per_layer_enabled = keyboard_state
                        self.user_set_state = keyboard_state  # Initialize user state
                        print(f"Initial layer RGB status from keyboard: {keyboard_state}")
                        # Set checkbox state ONLY on initial load
                        self.layer_rgb_enable.setChecked(self.per_layer_enabled)
                    else:
                        self.per_layer_enabled = False
                        self.user_set_state = False
                        print("No initial layer RGB status data received")
                        self.layer_rgb_enable.setChecked(False)
                except Exception as e:
                    print(f"Error getting initial layer RGB status: {e}")
                    self.per_layer_enabled = False
                    self.user_set_state = False
                    self.layer_rgb_enable.setChecked(False)
            else:
                # Default values for testing when keyboard methods aren't implemented yet
                self.per_layer_enabled = False
                self.user_set_state = False
                print("Layer RGB methods not implemented on keyboard")
                self.layer_rgb_enable.setChecked(False)

            self.initial_load_complete = True
        else:
            # On subsequent updates (e.g., when other RGB settings change),
            # COMPLETELY IGNORE keyboard state and preserve checkbox as-is
            print("LayerRGBHandler: Subsequent update - completely ignoring keyboard state, preserving checkbox")
            # Don't touch the checkbox at all - let it stay exactly as the user set it
            # Just update our internal state to match the checkbox
            self.per_layer_enabled = self.layer_rgb_enable.isChecked()
        
        # Always recreate buttons to ensure they're in sync with current checkbox state
        self.create_layer_buttons()

        # Unblock signals after update is complete
        self.unblock_signals()

    def valid(self):
        # Always return True so buttons are always shown
        return isinstance(self.device, VialKeyboard)

    def on_layer_rgb_enable_changed(self, checked):
        self.per_layer_enabled = checked
        
        # Try to call the keyboard method if it exists
        if hasattr(self.device.keyboard, 'set_layer_rgb_enable'):
            self.device.keyboard.set_layer_rgb_enable(checked)
        else:
            print(f"Layer RGB enable changed to: {checked} (keyboard method not implemented yet)")
        
        # Enable/disable layer buttons
        for button in self.layer_buttons:
            button.setEnabled(checked)

    def on_save_to_layer(self, layer):
        """Save current RGB settings to specified layer"""
        if self.per_layer_enabled:
            # Try to call the keyboard method if it exists
            if hasattr(self.device.keyboard, 'save_rgb_to_layer'):
                success = self.device.keyboard.save_rgb_to_layer(layer)
                if success:
                    print(f"Successfully saved RGB to layer {layer}")
                    self.update.emit()
                else:
                    print(f"Failed to save RGB to layer {layer}")
            else:
                print(f"Save RGB to layer {layer} (keyboard method not implemented yet)")

    def block_signals(self):
        """Override to ensure checkbox signals are properly blocked"""
        super().block_signals()
        # Extra safety - explicitly block the checkbox signal
        self.layer_rgb_enable.blockSignals(True)
        print("LayerRGBHandler: Signals blocked")

    def unblock_signals(self):
        """Override to ensure checkbox signals are properly unblocked"""
        super().unblock_signals()
        # Extra safety - explicitly unblock the checkbox signal
        self.layer_rgb_enable.blockSignals(False)
        print("LayerRGBHandler: Signals unblocked")

    def show(self):
        # Always show all widgets - no conditional visibility
        for w in self.widgets:
            w.show()

    def hide(self):
        # Always show all widgets - no hiding capability
        for w in self.widgets:
            w.show()


from PyQt5.QtWidgets import QTabWidget

class CustomLightsHandler(BasicHandler):
    """Handler for custom animation slot configuration - tabbed interface"""

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        # Custom Lights label
        self.lbl_custom_lights = QLabel(tr("RGBConfigurator", "Custom Lights"))
        container.addWidget(self.lbl_custom_lights, row, 0, 1, 2)

        # Create tab widget
        self.tab_widget = QTabWidget()
        container.addWidget(self.tab_widget, row + 1, 0, 1, 2)

        # Create tabs for each slot
        self.slot_tabs = []
        self.slot_widgets = {}
        
        for slot in range(10):
            self.create_slot_tab(slot)

        self.widgets = [self.lbl_custom_lights, self.tab_widget]

    def create_slot_tab(self, slot):
        """Create a tab for a single slot"""
        # Create tab widget
        tab_widget = QWidget()
        self.tab_widget.addTab(tab_widget, f"Slot {slot}")
        
        # Create layout for this tab
        layout = QGridLayout(tab_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Enabled checkbox
        enabled_cb = QCheckBox(tr("RGBConfigurator", "Enabled"))
        enabled_cb.setChecked(True)  # Default enabled
        enabled_cb.stateChanged.connect(lambda checked, s=slot: self.on_slot_enabled_changed(s, checked))
        layout.addWidget(enabled_cb, 0, 0, 1, 2)

        # Live Controls section
        live_label = QLabel(tr("RGBConfigurator", "Live Controls:"))
        live_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(live_label, 1, 0, 1, 2)

        # Live Position
        layout.addWidget(QLabel(tr("RGBConfigurator", "Position:")), 2, 0)
        live_position = QComboBox()
        for pos in CUSTOM_LIGHT_LIVE_POSITIONS:
            live_position.addItem(pos)
        live_position.currentIndexChanged.connect(lambda idx, s=slot: self.on_live_position_changed(s, idx))
        layout.addWidget(live_position, 2, 1)

        # Live Animation
        layout.addWidget(QLabel(tr("RGBConfigurator", "Animation:")), 3, 0)
        live_animation = QComboBox()
        for anim in CUSTOM_LIGHT_ANIMATIONS:
            live_animation.addItem(anim)
        live_animation.currentIndexChanged.connect(lambda idx, s=slot: self.on_live_animation_changed(s, idx))
        layout.addWidget(live_animation, 3, 1)

        # Macro Controls section
        macro_label = QLabel(tr("RGBConfigurator", "Macro Controls:"))
        macro_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(macro_label, 4, 0, 1, 2)

        # Macro Position
        layout.addWidget(QLabel(tr("RGBConfigurator", "Position:")), 5, 0)
        macro_position = QComboBox()
        for pos in CUSTOM_LIGHT_MACRO_POSITIONS:
            macro_position.addItem(pos)
        macro_position.currentIndexChanged.connect(lambda idx, s=slot: self.on_macro_position_changed(s, idx))
        layout.addWidget(macro_position, 5, 1)

        # Macro Animation
        layout.addWidget(QLabel(tr("RGBConfigurator", "Animation:")), 6, 0)
        macro_animation = QComboBox()
        for anim in CUSTOM_LIGHT_ANIMATIONS:
            macro_animation.addItem(anim)
        macro_animation.currentIndexChanged.connect(lambda idx, s=slot: self.on_macro_animation_changed(s, idx))
        layout.addWidget(macro_animation, 6, 1)

        # Effects section
        effects_label = QLabel(tr("RGBConfigurator", "Effects:"))
        effects_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(effects_label, 7, 0, 1, 2)

        # Background
        layout.addWidget(QLabel(tr("RGBConfigurator", "Background:")), 8, 0)
        background = QComboBox()
        for bg in CUSTOM_LIGHT_BACKGROUNDS:
            background.addItem(bg)
        background.currentIndexChanged.connect(lambda idx, s=slot: self.on_background_changed(s, idx))
        layout.addWidget(background, 8, 1)

        # Color Type
        layout.addWidget(QLabel(tr("RGBConfigurator", "Color Type:")), 9, 0)
        color_type = QComboBox()
        for color in CUSTOM_LIGHT_COLOR_TYPES:
            color_type.addItem(color)
        color_type.currentIndexChanged.connect(lambda idx, s=slot: self.on_color_type_changed(s, idx))
        layout.addWidget(color_type, 9, 1)

        # Pulse Mode
        layout.addWidget(QLabel(tr("RGBConfigurator", "Pulse Mode:")), 10, 0)
        pulse_mode = QComboBox()
        for pulse in CUSTOM_LIGHT_PULSE_MODES:
            pulse_mode.addItem(pulse)
        pulse_mode.currentIndexChanged.connect(lambda idx, s=slot: self.on_pulse_mode_changed(s, idx))
        layout.addWidget(pulse_mode, 10, 1)

        # Wide Influence
        wide_influence = QCheckBox(tr("RGBConfigurator", "Wide Influence"))
        wide_influence.stateChanged.connect(lambda checked, s=slot: self.on_wide_influence_changed(s, checked))
        layout.addWidget(wide_influence, 11, 0, 1, 2)

        # Buttons
        buttons_layout = QHBoxLayout()
        
        apply_button = QPushButton(tr("RGBConfigurator", "Apply Changes"))
        apply_button.clicked.connect(lambda checked, s=slot: self.on_apply_slot(s))
        buttons_layout.addWidget(apply_button)
        
        reset_button = QPushButton(tr("RGBConfigurator", "Reset to Default"))
        reset_button.clicked.connect(lambda checked, s=slot: self.on_reset_slot(s))
        buttons_layout.addWidget(reset_button)
        
        preset_combo = QComboBox()
        preset_combo.addItem("Load Preset...")
        for preset in CUSTOM_LIGHT_PRESETS:
            preset_combo.addItem(preset)
        preset_combo.currentIndexChanged.connect(lambda idx, s=slot: self.on_load_preset(s, idx))
        buttons_layout.addWidget(preset_combo)
        
        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        layout.addWidget(buttons_widget, 12, 0, 1, 2)

        # Store widgets for this slot
        self.slot_widgets[slot] = {
            'enabled': enabled_cb,
            'live_position': live_position,
            'live_animation': live_animation,
            'macro_position': macro_position,
            'macro_animation': macro_animation,
            'background': background,
            'color_type': color_type,
            'pulse_mode': pulse_mode,
            'wide_influence': wide_influence,
            'preset_combo': preset_combo
        }

        self.slot_tabs.append(tab_widget)

    def update_from_keyboard(self):
        """Update UI from keyboard state"""
        self.block_signals()
        
        # Update all slots
        for slot in range(10):
            try:
                config = self.get_custom_slot_config(slot)
                if config:
                    widgets = self.slot_widgets[slot]
                    widgets['live_position'].setCurrentIndex(min(config[0], len(CUSTOM_LIGHT_LIVE_POSITIONS) - 1))
                    widgets['macro_position'].setCurrentIndex(min(config[1], len(CUSTOM_LIGHT_MACRO_POSITIONS) - 1))
                    widgets['live_animation'].setCurrentIndex(min(config[2], len(CUSTOM_LIGHT_ANIMATIONS) - 1))
                    widgets['macro_animation'].setCurrentIndex(min(config[3], len(CUSTOM_LIGHT_ANIMATIONS) - 1))
                    widgets['wide_influence'].setChecked(bool(config[4]))
                    widgets['background'].setCurrentIndex(min(config[5], len(CUSTOM_LIGHT_BACKGROUNDS) - 1))
                    widgets['pulse_mode'].setCurrentIndex(min(config[6], len(CUSTOM_LIGHT_PULSE_MODES) - 1))
                    widgets['color_type'].setCurrentIndex(min(config[7], len(CUSTOM_LIGHT_COLOR_TYPES) - 1))
                    widgets['enabled'].setChecked(bool(config[8]) if len(config) > 8 else True)
                else:
                    self.set_slot_defaults(slot)
            except Exception as e:
                print(f"Error updating custom lights slot {slot}: {e}")
                self.set_slot_defaults(slot)

        self.unblock_signals()

    def set_slot_defaults(self, slot):
        """Set default values for a slot"""
        widgets = self.slot_widgets[slot]
        widgets['live_position'].setCurrentIndex(0)  # TrueKey
        widgets['macro_position'].setCurrentIndex(0)  # TrueKey
        widgets['live_animation'].setCurrentIndex(0)  # None
        widgets['macro_animation'].setCurrentIndex(0)  # None
        widgets['background'].setCurrentIndex(0)  # None
        widgets['color_type'].setCurrentIndex(1)  # Channel
        widgets['pulse_mode'].setCurrentIndex(3)  # All
        widgets['wide_influence'].setChecked(False)
        widgets['enabled'].setChecked(True)

    def valid(self):
        """Always return True - always show custom lights section"""
        return isinstance(self.device, VialKeyboard)

    def block_signals(self):
        """Block signals for all widgets"""
        for slot in range(10):
            widgets = self.slot_widgets[slot]
            for widget in widgets.values():
                widget.blockSignals(True)

    def unblock_signals(self):
        """Unblock signals for all widgets"""
        for slot in range(10):
            widgets = self.slot_widgets[slot]
            for widget in widgets.values():
                widget.blockSignals(False)

    # Event handlers
    def on_slot_enabled_changed(self, slot, checked):
        """Handle slot enabled/disabled"""
        self.send_parameter_change(slot, 8, 1 if checked else 0)

    def on_live_position_changed(self, slot, index):
        """Handle live position change"""
        self.send_parameter_change(slot, 0, index)

    def on_macro_position_changed(self, slot, index):
        """Handle macro position change"""
        self.send_parameter_change(slot, 1, index)

    def on_live_animation_changed(self, slot, index):
        """Handle live animation change"""
        self.send_parameter_change(slot, 2, index)

    def on_macro_animation_changed(self, slot, index):
        """Handle macro animation change"""
        self.send_parameter_change(slot, 3, index)

    def on_wide_influence_changed(self, slot, checked):
        """Handle wide influence toggle"""
        self.send_parameter_change(slot, 4, 1 if checked else 0)

    def on_background_changed(self, slot, index):
        """Handle background change"""
        self.send_parameter_change(slot, 5, index)

    def on_pulse_mode_changed(self, slot, index):
        """Handle pulse mode change"""
        self.send_parameter_change(slot, 6, index)

    def on_color_type_changed(self, slot, index):
        """Handle color type change"""
        self.send_parameter_change(slot, 7, index)

    def on_apply_slot(self, slot):
        """Apply current settings for a slot"""
        try:
            # Force update from current UI state
            widgets = self.slot_widgets[slot]
            
            # Send all parameters for this slot
            params = [
                widgets['live_position'].currentIndex(),
                widgets['macro_position'].currentIndex(),
                widgets['live_animation'].currentIndex(),
                widgets['macro_animation'].currentIndex(),
                1 if widgets['wide_influence'].isChecked() else 0,
                widgets['background'].currentIndex(),
                widgets['pulse_mode'].currentIndex(),
                widgets['color_type'].currentIndex(),
                1 if widgets['enabled'].isChecked() else 0
            ]
            
            success = self.set_all_slot_parameters(slot, params)
            if success:
                print(f"Applied all settings to slot {slot}")
                self.update.emit()
            else:
                print(f"Failed to apply settings to slot {slot}")
                
        except Exception as e:
            print(f"Error applying slot {slot} settings: {e}")

    def on_reset_slot(self, slot):
        """Reset a slot to defaults"""
        try:
            success = self.reset_custom_slot(slot)
            if success:
                self.set_slot_defaults(slot)
                self.update.emit()
                print(f"Reset slot {slot} to defaults")
            else:
                print(f"Failed to reset slot {slot}")
        except Exception as e:
            print(f"Error resetting slot {slot}: {e}")

    def on_load_preset(self, slot, index):
        """Load a preset configuration"""
        if index == 0:  # "Load Preset..." header
            return
            
        preset_index = index - 1  # Adjust for header
        try:
            success = self.load_custom_slot_preset(slot, preset_index)
            if success:
                # Update the UI for this slot
                config = self.get_custom_slot_config(slot)
                if config:
                    widgets = self.slot_widgets[slot]
                    self.block_signals()
                    widgets['live_position'].setCurrentIndex(min(config[0], len(CUSTOM_LIGHT_LIVE_POSITIONS) - 1))
                    widgets['macro_position'].setCurrentIndex(min(config[1], len(CUSTOM_LIGHT_MACRO_POSITIONS) - 1))
                    widgets['live_animation'].setCurrentIndex(min(config[2], len(CUSTOM_LIGHT_ANIMATIONS) - 1))
                    widgets['macro_animation'].setCurrentIndex(min(config[3], len(CUSTOM_LIGHT_ANIMATIONS) - 1))
                    widgets['wide_influence'].setChecked(bool(config[4]))
                    widgets['background'].setCurrentIndex(min(config[5], len(CUSTOM_LIGHT_BACKGROUNDS) - 1))
                    widgets['pulse_mode'].setCurrentIndex(min(config[6], len(CUSTOM_LIGHT_PULSE_MODES) - 1))
                    widgets['color_type'].setCurrentIndex(min(config[7], len(CUSTOM_LIGHT_COLOR_TYPES) - 1))
                    self.unblock_signals()
                
                self.update.emit()
                print(f"Loaded preset {preset_index} to slot {slot}")
            else:
                print(f"Failed to load preset {preset_index}")
        except Exception as e:
            print(f"Error loading preset: {e}")
        
        # Reset combo box to header
        self.slot_widgets[slot]['preset_combo'].setCurrentIndex(0)

    def send_parameter_change(self, slot, param_index, value):
        """Send parameter change to keyboard"""
        try:
            success = self.set_custom_slot_parameter(slot, param_index, value)
            if success:
                print(f"Set slot {slot} param {param_index} to {value}")
                self.update.emit()
            else:
                print(f"Failed to set slot {slot} param {param_index} to {value}")
        except Exception as e:
            print(f"Error setting custom slot parameter: {e}")

    # Simple HID command methods
    def get_custom_slot_config(self, slot):
        """Get all parameters for a custom animation slot"""
        try:
            if slot >= 10:
                return None
                
            data = self._send_vial_command(CMD_VIAL_CUSTOM_ANIM_GET_ALL, [slot])
            if data and len(data) > 2 and data[0] == 0x01:
                return data[3:11]  # 8 parameters starting at index 3
            return None
        except Exception as e:
            print(f"Error getting custom slot {slot} config: {e}")
            return None

    def set_custom_slot_parameter(self, slot, param_index, value):
        """Set a single parameter for a custom animation slot"""
        try:
            if slot >= 10 or param_index >= 9:
                return False
                
            data = self._send_vial_command(CMD_VIAL_CUSTOM_ANIM_SET_PARAM, [slot, param_index, value])
            return data and len(data) > 0 and data[0] == 0x01
        except Exception as e:
            print(f"Error setting custom slot {slot} parameter {param_index}: {e}")
            return False

    def set_all_slot_parameters(self, slot, params):
        """Set all parameters for a slot at once"""
        try:
            if slot >= 10 or len(params) != 9:
                return False
                
            data = self._send_vial_command(CMD_VIAL_CUSTOM_ANIM_SET_ALL, [slot] + params)
            return data and len(data) > 0 and data[0] == 0x01
        except Exception as e:
            print(f"Error setting all parameters for slot {slot}: {e}")
            return False

    def reset_custom_slot(self, slot):
        """Reset a slot to defaults"""
        try:
            if slot >= 10:
                return False
                
            data = self._send_vial_command(CMD_VIAL_CUSTOM_ANIM_RESET_SLOT, [slot])
            return data and len(data) > 0 and data[0] == 0x01
        except Exception as e:
            print(f"Error resetting slot {slot}: {e}")
            return False

    def load_custom_slot_preset(self, slot, preset_index):
        """Load a preset configuration into a slot"""
        try:
            if slot >= 10:
                return False

            # Define preset configurations
            presets = [
                [0, 0, 0, 0, 0, 1, 0, 1, 1],  # Classic TrueKey + enabled
                [0, 0, 1, 1, 0, 1, 3, 3, 1],  # Heat Effects + enabled
                [1, 1, 3, 3, 0, 2, 3, 1, 1],  # Moving Dots + enabled
                [2, 2, 0, 0, 1, 3, 0, 2, 1],  # BPM Disco + enabled
                [1, 1, 0, 0, 0, 0, 3, 1, 1],  # Zone Lighting + enabled
                [0, 0, 2, 2, 1, 0, 0, 1, 1],  # Sustain Mode + enabled
                [0, 2, 1, 0, 0, 2, 1, 1, 1],  # Performance Setup + enabled
            ]
            
            if preset_index >= len(presets):
                return False
                
            return self.set_all_slot_parameters(slot, presets[preset_index])
            
        except Exception as e:
            print(f"Error loading preset {preset_index} to slot {slot}: {e}")
            return False

    def _send_vial_command(self, command, data):
        """Send a Vial command and return response"""
        try:
            # Prepare packet: [0xFE, command, ...data, padding to 32 bytes]
            packet = [CMD_VIA_VIAL_PREFIX, command] + data
            packet += [0] * (32 - len(packet))  # Pad to 32 bytes
            
            # Send command
            self.device.dev.write(packet)
            
            # Read response
            response = self.device.dev.read(32, timeout_ms=1000)
            return response
            
        except Exception as e:
            print(f"Error sending Vial command 0x{command:02X}: {e}")
            return None

class RGBConfigurator(BasicEditor):

    def __init__(self):
        super().__init__()

        self.addStretch()

        w = QWidget()
        w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.container = QGridLayout()
        w.setLayout(self.container)
        self.addWidget(w)
        self.setAlignment(w, QtCore.Qt.AlignHCenter)

        self.handler_backlight = QmkBacklightHandler(self.container)
        self.handler_backlight.update.connect(self.update_from_keyboard)
        self.handler_rgblight = QmkRgblightHandler(self.container)
        self.handler_rgblight.update.connect(self.update_from_keyboard)
        self.handler_vialrgb = VialRGBHandler(self.container)
        self.handler_vialrgb.update.connect(self.update_from_keyboard)
        
        # Add the per-layer RGB handler
        self.handler_layer_rgb = LayerRGBHandler(self.container)
        self.handler_layer_rgb.update.connect(self.update_from_keyboard)
        
        # Add the custom lights handler RIGHT AFTER layer RGB
        self.handler_custom_lights = CustomLightsHandler(self.container)
        self.handler_custom_lights.update.connect(self.update_from_keyboard)
        
        self.handlers = [self.handler_backlight, self.handler_rgblight, 
                        self.handler_vialrgb, self.handler_layer_rgb,
                        self.handler_custom_lights]

        self.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        save_btn = QPushButton(tr("RGBConfigurator", "Save"))
        buttons.addWidget(save_btn)
        save_btn.clicked.connect(self.on_save)
        self.addLayout(buttons)

    def on_save(self):
        self.device.keyboard.save_rgb()

    def valid(self):
        # Always show RGB configurator for VialKeyboard (includes custom lights)
        return isinstance(self.device, VialKeyboard)

    def block_signals(self):
        for h in self.handlers:
            h.block_signals()

    def unblock_signals(self):
        for h in self.handlers:
            h.unblock_signals()

    def update_from_keyboard(self):
        self.device.keyboard.reload_rgb()
        
        # Check for layer RGB support
        if hasattr(self.device.keyboard, 'reload_layer_rgb_support'):
            self.device.keyboard.reload_layer_rgb_support()

        self.block_signals()

        for h in self.handlers:
            h.update_from_keyboard()

        self.unblock_signals()

    def rebuild(self, device):
        super().rebuild(device)

        for h in self.handlers:
            h.set_device(device)

        if not self.valid():
            return

        self.update_from_keyboard()