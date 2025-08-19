# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy, QGridLayout, QLabel, QSlider, \
    QComboBox, QColorDialog, QCheckBox, QTabWidget

from editor.basic_editor import BasicEditor
from widgets.clickable_label import ClickableLabel
from util import tr
from vial_device import VialKeyboard
from protocol.constants import CMD_VIA_VIAL_PREFIX, CMD_VIAL_LAYER_RGB_SAVE, CMD_VIAL_LAYER_RGB_LOAD, \
    CMD_VIAL_LAYER_RGB_ENABLE, CMD_VIAL_LAYER_RGB_GET_STATUS, CMD_VIAL_CUSTOM_ANIM_SET_PARAM, \
    CMD_VIAL_CUSTOM_ANIM_GET_PARAM, CMD_VIAL_CUSTOM_ANIM_SET_ALL, CMD_VIAL_CUSTOM_ANIM_GET_ALL, \
    CMD_VIAL_CUSTOM_ANIM_SAVE, CMD_VIAL_CUSTOM_ANIM_LOAD, CMD_VIAL_CUSTOM_ANIM_RESET_SLOT, \
    CMD_VIAL_CUSTOM_ANIM_GET_STATUS, CMD_VIAL_CUSTOM_ANIM_RESCAN_LEDS


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
    VialRGBEffect(57, "Custom Slot 1"),
    VialRGBEffect(58, "Custom Slot 2"),
    VialRGBEffect(59, "Custom Slot 3"),
    VialRGBEffect(60, "Custom Slot 4"),
    VialRGBEffect(61, "Custom Slot 5"),
    VialRGBEffect(62, "Custom Slot 6"),
    VialRGBEffect(63, "Custom Slot 7"),
    VialRGBEffect(64, "Custom Slot 8"),
    VialRGBEffect(65, "Custom Slot 9"),
    VialRGBEffect(66, "Custom Slot 10"),
    VialRGBEffect(67, "Custom Slot 11"),
    VialRGBEffect(68, "Custom Slot 12"),
]


# Separate effect and style arrays for custom lights
LIVE_EFFECTS = [
    "None",               # MACRO_ANIM_NONE
    "Wide",               # MACRO_ANIM_HEAT
    "Wider",               # MACRO_ANIM_HEAT
    "Heatmap",
    "Heatmap 2",            # MACRO_ANIM_SUSTAIN
    "Horizontal Dots",    # MACRO_ANIM_MOVING_DOTS_ROW
    "Horizontal Dots Long",    # MACRO_ANIM_MOVING_DOTS_ROW
    "Vertical Dots",     # MACRO_ANIM_MOVING_DOTS_COL
    "Vertical Dots Long",     # MACRO_ANIM_MOVING_DOTS_COL
    "Diagonal Dots 1",     # MACRO_ANIM_MOVING_DOTS_COL
    "Diagonal Dots 2",     # MACRO_ANIM_MOVING_DOTS_COL
    "Cross 1",     # MACRO_ANIM_MOVING_DOTS_COL
    "Cross 2",     # MACRO_ANIM_MOVING_DOTS_COL
    "X Dots",     # MACRO_ANIM_MOVING_DOTS_COL
    "Firework",     # MACRO_ANIM_MOVING_DOTS_COL    
    "Ripples",
    "Waves",
    "Fireworks",
    "Spirals"
]

LIVE_STYLES = [
    "TrueKey",            # LIVE_POS_TRUEKEY
    "Zone",               # LIVE_POS_ZONE
    "Quadrant",           # LIVE_POS_QUADRANT
    "Note Row Col0",      # LIVE_POS_NOTE_ROW_COL0
    "Note Row Col13",     # LIVE_POS_NOTE_ROW_COL13
    "Note Col Row0",      # LIVE_POS_NOTE_COL_ROW0
    "Note Col Row4",      # LIVE_POS_NOTE_COL_ROW4
    "Note Row Mixed",     # LIVE_POS_NOTE_ROW_MIXED
    "Note Col Mixed"      # LIVE_POS_NOTE_COL_MIXED
]

MACRO_EFFECTS = [
    "None",               # MACRO_ANIM_NONE
    "Wide",               # MACRO_ANIM_HEAT
    "Wider",               # MACRO_ANIM_HEAT
    "Heatmap",
    "Heatmap 2",            # MACRO_ANIM_SUSTAIN
    "Horizontal Dots",    # MACRO_ANIM_MOVING_DOTS_ROW
    "Horizontal Dots Long",    # MACRO_ANIM_MOVING_DOTS_ROW
    "Vertical Dots",     # MACRO_ANIM_MOVING_DOTS_COL
    "Vertical Dots Long",     # MACRO_ANIM_MOVING_DOTS_COL
    "Diagonal Dots 1",     # MACRO_ANIM_MOVING_DOTS_COL
    "Diagonal Dots 2",     # MACRO_ANIM_MOVING_DOTS_COL
    "Cross 1",     # MACRO_ANIM_MOVING_DOTS_COL
    "Cross 2",     # MACRO_ANIM_MOVING_DOTS_COL
    "X Dots",     # MACRO_ANIM_MOVING_DOTS_COL
    "Firework",     # MACRO_ANIM_MOVING_DOTS_COL    
    "Ripples",
    "Waves",
    "Fireworks",
    "Spirals"
]

MACRO_STYLES = [
    "TrueKey",            # MACRO_POS_TRUEKEY
    "Zone",               # MACRO_POS_ZONE
    "Quadrant",           # MACRO_POS_QUADRANT
    "Note Row Col0",      # MACRO_POS_NOTE_ROW_COL0
    "Note Row Col13",     # MACRO_POS_NOTE_ROW_COL13
    "Note Col Row0",      # MACRO_POS_NOTE_COL_ROW0
    "Note Col Row4",      # MACRO_POS_NOTE_COL_ROW4
    "Loop Row Col0",      # MACRO_POS_LOOP_ROW_COL0
    "Loop Row Col13",     # MACRO_POS_LOOP_ROW_COL13
    "Loop Row Alt",       # MACRO_POS_LOOP_ROW_ALT
    "Loop Col"            # MACRO_POS_LOOP_COL
]

CUSTOM_LIGHT_BACKGROUNDS = [
    "None",                           # 0
    "Basic",                          # 1
    "Basic 2",                        # 2
    "Basic 3",                        # 3
    "Basic 4",                        # 4
    "Basic 5",                        # 5
    "Basic 6",                        # 6
    "Autolight",                      # 7
    "Autolight 2",                    # 8
    "Autolight 3",                    # 9
    "Autolight 4",                    # 10
    "Autolight 5",                    # 11
    "Autolight 6",                    # 12
    
    # BPM PULSE FADE (13-22)
    "BPM Pulse Fade",                 # 13
    "BPM Pulse Fade 2",               # 14
    "BPM Pulse Fade Desaturated",     # 15
    "BPM Pulse Fade Disco",           # 16
    "BPM Pulse Fade Solid Background", # 17
    "BPM Pulse Fade Solid Background 2", # 18
    "BPM Pulse Fade Solid Disco",     # 19
    "BPM Pulse Fade Autolight",       # 20
    "BPM Pulse Fade Autolight 2",     # 21
    "BPM Pulse Fade Autolight Disco", # 22
    
    # BPM QUADRANTS (23-32)
    "BPM Quadrants",                  # 23
    "BPM Quadrants 2",                # 24
    "BPM Quadrants Desaturated",      # 25
    "BPM Quadrants Disco",            # 26
    "BPM Quadrants Solid Background", # 27
    "BPM Quadrants Solid Background 2", # 28
    "BPM Quadrants Solid Disco",      # 29
    "BPM Quadrants Autolight",        # 30
    "BPM Quadrants Autolight 2",      # 31
    "BPM Quadrants Autolight Disco",  # 32
    
    # BPM ROW (33-42)
    "BPM Row",                        # 33
    "BPM Row 2",                      # 34
    "BPM Row Desaturated",            # 35
    "BPM Row Disco",                  # 36
    "BPM Row Solid Background",       # 37
    "BPM Row Solid Background 2",     # 38
    "BPM Row Solid Disco",            # 39
    "BPM Row Autolight",              # 40
    "BPM Row Autolight 2",            # 41
    "BPM Row Autolight Disco",        # 42
    
    # BPM COLUMN (43-52)
    "BPM Column",                     # 43
    "BPM Column 2",                   # 44
    "BPM Column Desaturated",         # 45
    "BPM Column Disco",               # 46
    "BPM Column Solid Background",    # 47
    "BPM Column Solid Background 2",  # 48
    "BPM Column Solid Disco",         # 49
    "BPM Column Autolight",           # 50
    "BPM Column Autolight 2",         # 51
    "BPM Column Autolight Disco",     # 52
    
    # BPM ALL (53-62)
    "BPM All",                        # 53
    "BPM All 2",                      # 54
    "BPM All Desaturated",            # 55
    "BPM All Disco",                  # 56
    "BPM All Solid Background",       # 57
    "BPM All Solid Background 2",     # 58
    "BPM All Solid Disco",            # 59
    "BPM All Autolight",              # 60
    "BPM All Autolight 2",            # 61
    "BPM All Autolight Disco"         # 62
]

CUSTOM_LIGHT_COLOR_TYPES = [
    "Base", "Channel", "Macro", "Heat"
]

CUSTOM_LIGHT_SUSTAIN_MODES = [
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


class RescanButtonHandler(BasicHandler):
    """Handler for the Rescan LED Positions button - ONLY sends HID command"""

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        # Centered rescan button
        rescan_button = QPushButton(tr("RGBConfigurator", "Rescan LED Positions"))
        rescan_button.clicked.connect(self.on_rescan_led_positions)
        rescan_button.setStyleSheet("QPushButton { padding: 8px; }")
        rescan_button.setMinimumHeight(30)
        
        # Center the button using a horizontal layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(rescan_button)
        button_layout.addStretch()
        
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        container.addWidget(button_widget, row, 0, 1, 2)

        self.widgets = [button_widget]

    def update_from_keyboard(self):
        # No updates needed for this button
        pass

    def valid(self):
        # Always show the rescan button
        return isinstance(self.device, VialKeyboard)

    def on_rescan_led_positions(self):
        """Rescan LED positions and force RGB state refresh"""
        try:
            if hasattr(self.device.keyboard, 'rescan_led_positions'):
                self.device.keyboard.rescan_led_positions()
                print("Rescan LED command sent")
                
                # Wait for firmware to finish intensive processing
                import time
                time.sleep(1.0)
                
                # Force a complete RGB reload to clear any corrupted cached state
                self.device.keyboard.reload_rgb()
                
                # Force GUI update with fresh data
                # Find the RGB configurator and update it
                if hasattr(self, 'parent') and hasattr(self.parent, 'update_from_keyboard'):
                    self.parent.update_from_keyboard()
                    
            else:
                print("Rescan LED method not available")
        except Exception as e:
            print(f"Error sending rescan LED command: {e}")

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
                    status = self.device.keyboard.get_layer_rgb_status()
                    if status is not None:
                        keyboard_state = bool(status)
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

class CustomLightsHandler(BasicHandler):
    """Handler for custom animation slot configuration - uses VialKeyboard infrastructure"""

    def __init__(self, container):
        super().__init__(container)

        row = container.rowCount()

        # Custom Lights label
        self.lbl_custom_lights = QLabel(tr("RGBConfigurator", "Custom Lights"))
        container.addWidget(self.lbl_custom_lights, row, 0, 1, 2)

        # Create tab widget
        self.tab_widget = QTabWidget()
        container.addWidget(self.tab_widget, row + 1, 0, 1, 2)

        # Create tabs for each slot (12 slots)
        self.slot_tabs = []
        self.slot_widgets = {}
        
        for slot in range(12):
            self.create_slot_tab(slot)

        self.widgets = [self.lbl_custom_lights, self.tab_widget]

    def create_slot_tab(self, slot):
        """Create a tab for a single slot"""
        # Create tab widget
        tab_widget = QWidget()
        self.tab_widget.addTab(tab_widget, str(slot + 1))  # Tab names: "1", "2", "3", etc.
        
        # Create layout for this tab
        layout = QGridLayout(tab_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Live Animation section
        live_label = QLabel(tr("RGBConfigurator", "Live Animation:"))
        live_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(live_label, 0, 0, 1, 3)

        # Live Effect and Style dropdowns below each other
        layout.addWidget(QLabel(tr("RGBConfigurator", "Effect:")), 1, 0)
        live_effect = QComboBox()
        for effect in LIVE_EFFECTS:
            live_effect.addItem(effect)
        live_effect.currentIndexChanged.connect(lambda idx, s=slot: self.on_live_effect_changed(s, idx))
        layout.addWidget(live_effect, 1, 1, 1, 2)

        layout.addWidget(QLabel(tr("RGBConfigurator", "Style:")), 2, 0)
        live_style = QComboBox()
        for style in LIVE_STYLES:
            live_style.addItem(style)
        live_style.currentIndexChanged.connect(lambda idx, s=slot: self.on_live_style_changed(s, idx))
        layout.addWidget(live_style, 2, 1, 1, 2)

        # Live Animation Speed slider
        layout.addWidget(QLabel(tr("RGBConfigurator", "Live Speed:")), 3, 0)
        live_speed = QSlider(QtCore.Qt.Horizontal)
        live_speed.setMinimum(0)
        live_speed.setMaximum(255)
        live_speed.setValue(128)  # Default speed
        live_speed.valueChanged.connect(lambda value, s=slot: self.on_live_speed_changed(s, value))
        layout.addWidget(live_speed, 3, 1, 1, 2)

        # Macro Animation section
        macro_label = QLabel(tr("RGBConfigurator", "Macro Animation:"))
        macro_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(macro_label, 4, 0, 1, 3)

        # Macro Effect and Style dropdowns below each other
        layout.addWidget(QLabel(tr("RGBConfigurator", "Effect:")), 5, 0)
        macro_effect = QComboBox()
        for effect in MACRO_EFFECTS:
            macro_effect.addItem(effect)
        macro_effect.currentIndexChanged.connect(lambda idx, s=slot: self.on_macro_effect_changed(s, idx))
        layout.addWidget(macro_effect, 5, 1, 1, 2)

        layout.addWidget(QLabel(tr("RGBConfigurator", "Style:")), 6, 0)
        macro_style = QComboBox()
        for style in MACRO_STYLES:
            macro_style.addItem(style)
        macro_style.currentIndexChanged.connect(lambda idx, s=slot: self.on_macro_style_changed(s, idx))
        layout.addWidget(macro_style, 6, 1, 1, 2)

        # Macro Animation Speed slider
        layout.addWidget(QLabel(tr("RGBConfigurator", "Macro Speed:")), 7, 0)
        macro_speed = QSlider(QtCore.Qt.Horizontal)
        macro_speed.setMinimum(0)
        macro_speed.setMaximum(255)
        macro_speed.setValue(128)  # Default speed
        macro_speed.valueChanged.connect(lambda value, s=slot: self.on_macro_speed_changed(s, value))
        layout.addWidget(macro_speed, 7, 1, 1, 2)

        # Effects section
        effects_label = QLabel(tr("RGBConfigurator", "Effects:"))
        effects_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(effects_label, 8, 0, 1, 3)

        # Background
        layout.addWidget(QLabel(tr("RGBConfigurator", "Background:")), 9, 0)
        background = QComboBox()
        for bg in CUSTOM_LIGHT_BACKGROUNDS:
            background.addItem(bg)
        background.currentIndexChanged.connect(lambda idx, s=slot: self.on_background_changed(s, idx))
        layout.addWidget(background, 9, 1, 1, 2)

        # Background Brightness slider
        layout.addWidget(QLabel(tr("RGBConfigurator", "Background Brightness:")), 10, 0)
        background_brightness = QSlider(QtCore.Qt.Horizontal)
        background_brightness.setMinimum(0)
        background_brightness.setMaximum(100)
        background_brightness.setValue(30)  # Default 30%
        background_brightness.valueChanged.connect(lambda value, s=slot: self.on_background_brightness_changed(s, value))
        layout.addWidget(background_brightness, 10, 1, 1, 2)

        # Color Type
        layout.addWidget(QLabel(tr("RGBConfigurator", "Color Type:")), 11, 0)
        color_type = QComboBox()
        for color in CUSTOM_LIGHT_COLOR_TYPES:
            color_type.addItem(color)
        color_type.currentIndexChanged.connect(lambda idx, s=slot: self.on_color_type_changed(s, idx))
        layout.addWidget(color_type, 11, 1, 1, 2)

        # Sustain Mode
        layout.addWidget(QLabel(tr("RGBConfigurator", "Sustain:")), 12, 0)
        sustain_mode = QComboBox()
        for sustain in CUSTOM_LIGHT_SUSTAIN_MODES:
            sustain_mode.addItem(sustain)
        sustain_mode.currentIndexChanged.connect(lambda idx, s=slot: self.on_sustain_mode_changed(s, idx))
        layout.addWidget(sustain_mode, 12, 1, 1, 2)

        # Buttons
        buttons_layout = QHBoxLayout()
        
        save_button = QPushButton(tr("RGBConfigurator", "Save"))
        save_button.clicked.connect(lambda checked, s=slot: self.on_save_slot(s))
        buttons_layout.addWidget(save_button)
        
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
        layout.addWidget(buttons_widget, 13, 0, 1, 3)

        # Store widgets for this slot
        self.slot_widgets[slot] = {
            'live_effect': live_effect,
            'live_style': live_style,
            'live_speed': live_speed,
            'macro_effect': macro_effect,
            'macro_style': macro_style,
            'macro_speed': macro_speed,
            'background': background,
            'background_brightness': background_brightness,
            'color_type': color_type,
            'sustain_mode': sustain_mode,
            'preset_combo': preset_combo
        }

        self.slot_tabs.append(tab_widget)

    def update_from_keyboard(self):
        """Update UI from keyboard state using VialKeyboard infrastructure"""
        self.block_signals()
        
        # Update all slots
        for slot in range(12):
            try:
                if hasattr(self.device.keyboard, 'get_custom_slot_config'):
                    config = self.device.keyboard.get_custom_slot_config(slot)
                    if config and len(config) >= 12:  # Expecting 12 parameters
                        widgets = self.slot_widgets[slot]
                        
                        # Set individual effect and style dropdowns
                        widgets['live_effect'].setCurrentIndex(min(config[2], len(LIVE_EFFECTS) - 1))  # live_animation
                        widgets['live_style'].setCurrentIndex(min(config[0], len(LIVE_STYLES) - 1))    # live_positioning
                        widgets['macro_effect'].setCurrentIndex(min(config[3], len(MACRO_EFFECTS) - 1)) # macro_animation
                        widgets['macro_style'].setCurrentIndex(min(config[1], len(MACRO_STYLES) - 1))   # macro_positioning
                        
                        # Skip config[4] (influence) - no longer used
                        widgets['background'].setCurrentIndex(min(config[5], len(CUSTOM_LIGHT_BACKGROUNDS) - 1))
                        widgets['sustain_mode'].setCurrentIndex(min(config[6], len(CUSTOM_LIGHT_SUSTAIN_MODES) - 1))
                        widgets['color_type'].setCurrentIndex(min(config[7], len(CUSTOM_LIGHT_COLOR_TYPES) - 1))
                        # config[8] is enabled - not shown in UI
                        widgets['background_brightness'].setValue(config[9] if len(config) > 9 else 30)  # Background brightness
                        widgets['live_speed'].setValue(config[10] if len(config) > 10 else 128)  # Live speed
                        widgets['macro_speed'].setValue(config[11] if len(config) > 11 else 128)  # Macro speed
                    else:
                        self.set_slot_defaults(slot)
                else:
                    print(f"Custom slot config methods not implemented on keyboard")
                    self.set_slot_defaults(slot)
            except Exception as e:
                print(f"Error updating custom lights slot {slot}: {e}")
                self.set_slot_defaults(slot)

        self.unblock_signals()

    def set_slot_defaults(self, slot):
        """Set default values for a slot"""
        widgets = self.slot_widgets[slot]
        widgets['live_effect'].setCurrentIndex(0)         # None
        widgets['live_style'].setCurrentIndex(0)          # TrueKey
        widgets['live_speed'].setValue(128)               # Default live speed
        widgets['macro_effect'].setCurrentIndex(0)        # None
        widgets['macro_style'].setCurrentIndex(0)         # TrueKey
        widgets['macro_speed'].setValue(128)              # Default macro speed
        widgets['background'].setCurrentIndex(0)          # None
        widgets['background_brightness'].setValue(30)     # 30% background brightness
        widgets['color_type'].setCurrentIndex(1)          # Channel
        widgets['sustain_mode'].setCurrentIndex(3)        # All

    def valid(self):
        """Always return True - always show custom lights section"""
        return isinstance(self.device, VialKeyboard)

    def block_signals(self):
        """Block signals for all widgets"""
        for slot in range(12):
            widgets = self.slot_widgets[slot]
            for widget in widgets.values():
                widget.blockSignals(True)

    def unblock_signals(self):
        """Unblock signals for all widgets"""
        for slot in range(12):
            widgets = self.slot_widgets[slot]
            for widget in widgets.values():
                widget.blockSignals(False)

    # Event handlers using VialKeyboard infrastructure - NO UPDATE CALLS
    def on_live_effect_changed(self, slot, index):
        """Handle live effect change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 2, index)  # live_animation
        else:
            print(f"Live effect changed: slot {slot}, effect {index}")

    def on_live_style_changed(self, slot, index):
        """Handle live style change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 0, index)  # live_positioning
        else:
            print(f"Live style changed: slot {slot}, style {index}")

    def on_live_speed_changed(self, slot, value):
        """Handle live animation speed change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 10, value)  # Parameter 10: live speed
        else:
            print(f"Live speed changed: slot {slot}, speed {value}")

    def on_macro_effect_changed(self, slot, index):
        """Handle macro effect change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 3, index)  # macro_animation
        else:
            print(f"Macro effect changed: slot {slot}, effect {index}")

    def on_macro_style_changed(self, slot, index):
        """Handle macro style change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 1, index)  # macro_positioning
        else:
            print(f"Macro style changed: slot {slot}, style {index}")

    def on_macro_speed_changed(self, slot, value):
        """Handle macro animation speed change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 11, value)  # Parameter 11: macro speed
        else:
            print(f"Macro speed changed: slot {slot}, speed {value}")

    def on_wide_influence_changed(self, slot, checked):
        """Handle wide influence checkbox change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 4, 1 if checked else 0)  # influence
        else:
            print(f"Wide influence changed: slot {slot}, checked {checked}")

    def on_background_changed(self, slot, index):
        """Handle background change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 5, index)
        else:
            print(f"Background changed: slot {slot}, index {index}")

    def on_background_brightness_changed(self, slot, value):
        """Handle background brightness change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 9, value)  # Parameter 9: background brightness
        else:
            print(f"Background brightness changed: slot {slot}, brightness {value}%")

    def on_sustain_mode_changed(self, slot, index):
        """Handle sustain mode change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 6, index)
        else:
            print(f"Sustain mode changed: slot {slot}, index {index}")

    def on_color_type_changed(self, slot, index):
        """Handle color type change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 7, index)
        else:
            print(f"Color type changed: slot {slot}, index {index}")

    def on_save_slot(self, slot):
        """Save current slot configuration to EEPROM"""
        try:
            if hasattr(self.device.keyboard, 'save_custom_slot'):
                success = self.device.keyboard.save_custom_slot(slot)
                if success:
                    print(f"Saved slot {slot + 1} to EEPROM")
                else:
                    print(f"Failed to save slot {slot + 1}")
            else:
                print(f"Save slot {slot + 1} (keyboard method not implemented)")
                    
        except Exception as e:
            print(f"Error saving slot {slot + 1}: {e}")

    def on_reset_slot(self, slot):
        """Reset a slot to defaults"""
        try:
            if hasattr(self.device.keyboard, 'reset_custom_slot'):
                success = self.device.keyboard.reset_custom_slot(slot)
                if success:
                    self.set_slot_defaults(slot)
                    print(f"Reset slot {slot + 1} to defaults")
                else:
                    print(f"Failed to reset slot {slot + 1}")
            else:
                print(f"Reset slot {slot + 1} to defaults (keyboard method not implemented)")
                self.set_slot_defaults(slot)
        except Exception as e:
            print(f"Error resetting slot {slot + 1}: {e}")

    def on_load_preset(self, slot, index):
        """Load a preset configuration - now sets individual parameters"""
        if index == 0:  # "Load Preset..." header
            return
            
        preset_index = index - 1  # Adjust for header
        
        # Define preset configurations as individual parameter sets
        presets = [
            # Classic TrueKey: live(TrueKey,None), macro(TrueKey,None), Basic bg, All sustain, Channel color
            {'live_pos': 0, 'live_anim': 0, 'macro_pos': 0, 'macro_anim': 0, 'background': 1, 'sustain': 3, 'color': 1, 'bg_brightness': 30, 'live_speed': 128, 'macro_speed': 128},
            # Heat Effects: live(TrueKey,Heat), macro(TrueKey,Heat), Basic bg, All sustain, Heat color
            {'live_pos': 0, 'live_anim': 1, 'macro_pos': 0, 'macro_anim': 1, 'background': 1, 'sustain': 3, 'color': 3, 'bg_brightness': 25, 'live_speed': 200, 'macro_speed': 200},
            # Moving Dots: live(Zone,Moving Dots Row), macro(Zone,Moving Dots Row), Basic bg, All sustain, Channel color
            {'live_pos': 1, 'live_anim': 3, 'macro_pos': 1, 'macro_anim': 3, 'background': 1, 'sustain': 3, 'color': 1, 'bg_brightness': 35, 'live_speed': 150, 'macro_speed': 150},
            # BPM Disco: live(Quadrant,None), macro(Quadrant,None), BPM All Disco bg, All sustain, Macro color
            {'live_pos': 2, 'live_anim': 0, 'macro_pos': 2, 'macro_anim': 0, 'background': 46, 'sustain': 3, 'color': 2, 'bg_brightness': 40, 'live_speed': 100, 'macro_speed': 100},
            # Zone Lighting: live(Zone,None), macro(Zone,None), None bg, All sustain, Base color
            {'live_pos': 1, 'live_anim': 0, 'macro_pos': 1, 'macro_anim': 0, 'background': 0, 'sustain': 3, 'color': 0, 'bg_brightness': 0, 'live_speed': 128, 'macro_speed': 128},
            # Sustain Mode: live(TrueKey,Sustain), macro(TrueKey,Sustain), None bg, All sustain, Channel color
            {'live_pos': 0, 'live_anim': 2, 'macro_pos': 0, 'macro_anim': 2, 'background': 0, 'sustain': 3, 'color': 1, 'bg_brightness': 0, 'live_speed': 80, 'macro_speed': 80},
            # Performance Setup: live(TrueKey,None), macro(Zone,Heat), Basic bg, All sustain, Channel color
            {'live_pos': 0, 'live_anim': 0, 'macro_pos': 1, 'macro_anim': 1, 'background': 1, 'sustain': 3, 'color': 1, 'bg_brightness': 30, 'live_speed': 180, 'macro_speed': 180},
        ]
        
        if preset_index >= len(presets):
            return
            
        preset = presets[preset_index]
        
        try:
            # Set all parameters using individual calls
            if hasattr(self.device.keyboard, 'set_custom_slot_all_parameters'):
                success = self.device.keyboard.set_custom_slot_all_parameters(
                    slot, 
                    preset['live_pos'], preset['macro_pos'], preset['live_anim'], preset['macro_anim'],
                    0, preset['background'], preset['sustain'], 
                    preset['color'], 1, preset['bg_brightness'], preset['live_speed'], preset['macro_speed']
                )
                if success:
                    # Update GUI to reflect the loaded preset
                    widgets = self.slot_widgets[slot]
                    widgets['live_effect'].setCurrentIndex(preset['live_anim'])
                    widgets['live_style'].setCurrentIndex(preset['live_pos'])
                    widgets['macro_effect'].setCurrentIndex(preset['macro_anim'])
                    widgets['macro_style'].setCurrentIndex(preset['macro_pos'])
                    widgets['background'].setCurrentIndex(preset['background'])
                    widgets['sustain_mode'].setCurrentIndex(preset['sustain'])
                    widgets['color_type'].setCurrentIndex(preset['color'])
                    widgets['background_brightness'].setValue(preset['bg_brightness'])
                    widgets['live_speed'].setValue(preset['live_speed'])
                    widgets['macro_speed'].setValue(preset['macro_speed'])
                    print(f"Loaded preset {preset_index} to slot {slot + 1}")
                else:
                    print(f"Failed to load preset {preset_index}")
            else:
                print(f"Load preset {preset_index} to slot {slot + 1} (keyboard method not implemented)")
        except Exception as e:
            print(f"Error loading preset: {e}")
        
        # Reset combo box to header
        self.slot_widgets[slot]['preset_combo'].setCurrentIndex(0)

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
        
        # Add the rescan button handler - NO UPDATE CONNECTION
        self.handler_rescan = RescanButtonHandler(self.container)
        # REMOVED: self.handler_rescan.update.connect(self.update_from_keyboard)
        
        # Add the per-layer RGB handler
        self.handler_layer_rgb = LayerRGBHandler(self.container)
        self.handler_layer_rgb.update.connect(self.update_from_keyboard)
        
        # Add the custom lights handler
        self.handler_custom_lights = CustomLightsHandler(self.container)
        self.handler_custom_lights.update.connect(self.update_from_keyboard)
        
        self.handlers = [self.handler_backlight, self.handler_rgblight, 
                        self.handler_vialrgb, self.handler_rescan,
                        self.handler_layer_rgb, self.handler_custom_lights]

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
        # Always show RGB configurator for VialKeyboard
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

        # Check for custom lights support  
        if hasattr(self.device.keyboard, 'reload_custom_lights_support'):
            self.device.keyboard.reload_custom_lights_support()

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