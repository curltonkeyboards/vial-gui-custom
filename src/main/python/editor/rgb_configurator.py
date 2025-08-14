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
    # Custom Slot Effects (12 slots)
    VialRGBEffect(96, "Custom Slot 1"),
    VialRGBEffect(97, "Custom Slot 2"),
    VialRGBEffect(98, "Custom Slot 3"),
    VialRGBEffect(99, "Custom Slot 4"),
    VialRGBEffect(100, "Custom Slot 5"),
    VialRGBEffect(101, "Custom Slot 6"),
    VialRGBEffect(102, "Custom Slot 7"),
    VialRGBEffect(103, "Custom Slot 8"),
    VialRGBEffect(104, "Custom Slot 9"),
    VialRGBEffect(105, "Custom Slot 10"),
    VialRGBEffect(106, "Custom Slot 11"),
    VialRGBEffect(107, "Custom Slot 12"),
]


# Preset definitions combining position + animation + influence
LIVE_ANIMATION_PRESETS = [
    # TrueKey presets
    ("TrueKey Normal", 0, 0, False),      # LIVE_POS_TRUEKEY, LIVE_ANIM_NONE, no influence
    ("TrueKey Wide", 0, 0, True),         # LIVE_POS_TRUEKEY, LIVE_ANIM_NONE, wide influence
    ("TrueKey Heat1", 0, 1, False),       # LIVE_POS_TRUEKEY, LIVE_ANIM_HEAT, no influence
    ("TrueKey Heat1 Wide", 0, 1, True),   # LIVE_POS_TRUEKEY, LIVE_ANIM_HEAT, wide influence
    ("TrueKey Heat2", 0, 2, False),       # LIVE_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, no influence
    ("TrueKey Heat2 Wide", 0, 2, True),   # LIVE_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, wide influence
    
    # Zone presets
    ("Zone Normal", 1, 0, False),         # LIVE_POS_ZONE, LIVE_ANIM_NONE, no influence
    ("Zone Wide", 1, 0, True),            # LIVE_POS_ZONE, LIVE_ANIM_NONE, wide influence
    ("Zone Heat", 1, 1, False),           # LIVE_POS_ZONE, LIVE_ANIM_HEAT, no influence
    ("Zone Heat Wide", 1, 1, True),       # LIVE_POS_ZONE, LIVE_ANIM_HEAT, wide influence
    
    # Quadrant presets
    ("Quadrant Normal", 2, 0, False),     # LIVE_POS_QUADRANT, LIVE_ANIM_NONE, no influence
    ("Quadrant Wide", 2, 0, True),        # LIVE_POS_QUADRANT, LIVE_ANIM_NONE, wide influence
    
    # Row presets (only work with row animations)
    ("Row Left", 3, 3, False),            # LIVE_POS_NOTE_ROW_COL0, LIVE_ANIM_MOVING_DOTS_ROW, no influence
    ("Row Left Wide", 3, 3, True),        # LIVE_POS_NOTE_ROW_COL0, LIVE_ANIM_MOVING_DOTS_ROW, wide influence
    ("Row Right", 4, 3, False),           # LIVE_POS_NOTE_ROW_COL13, LIVE_ANIM_MOVING_DOTS_ROW, no influence
    ("Row Right Wide", 4, 3, True),       # LIVE_POS_NOTE_ROW_COL13, LIVE_ANIM_MOVING_DOTS_ROW, wide influence
    ("Row Mixed", 7, 3, False),           # LIVE_POS_NOTE_ROW_MIXED, LIVE_ANIM_MOVING_DOTS_ROW, no influence
    ("Row Mixed Wide", 7, 3, True),       # LIVE_POS_NOTE_ROW_MIXED, LIVE_ANIM_MOVING_DOTS_ROW, wide influence
    ("Row Zone", 1, 3, False),            # LIVE_POS_ZONE, LIVE_ANIM_MOVING_DOTS_ROW, no influence
    ("Row Zone Wide", 1, 3, True),        # LIVE_POS_ZONE, LIVE_ANIM_MOVING_DOTS_ROW, wide influence
    
    # Column presets (only work with column animations)
    ("Column Top", 5, 4, False),          # LIVE_POS_NOTE_COL_ROW0, LIVE_ANIM_MOVING_DOTS_COL, no influence
    ("Column Top Wide", 5, 4, True),      # LIVE_POS_NOTE_COL_ROW0, LIVE_ANIM_MOVING_DOTS_COL, wide influence
    ("Column Bottom", 6, 4, False),       # LIVE_POS_NOTE_COL_ROW4, LIVE_ANIM_MOVING_DOTS_COL, no influence
    ("Column Bottom Wide", 6, 4, True),   # LIVE_POS_NOTE_COL_ROW4, LIVE_ANIM_MOVING_DOTS_COL, wide influence
    ("Column Mixed", 8, 4, False),        # LIVE_POS_NOTE_COL_MIXED, LIVE_ANIM_MOVING_DOTS_COL, no influence
    ("Column Mixed Wide", 8, 4, True),    # LIVE_POS_NOTE_COL_MIXED, LIVE_ANIM_MOVING_DOTS_COL, wide influence
    ("Column Zone", 1, 4, False),         # LIVE_POS_ZONE, LIVE_ANIM_MOVING_DOTS_COL, no influence
    ("Column Zone Wide", 1, 4, True),     # LIVE_POS_ZONE, LIVE_ANIM_MOVING_DOTS_COL, wide influence
]

MACRO_ANIMATION_PRESETS = [
    # TrueKey presets
    ("TrueKey Normal", 0, 0, False),      # MACRO_POS_TRUEKEY, MACRO_ANIM_NONE, no influence
    ("TrueKey Wide", 0, 0, True),         # MACRO_POS_TRUEKEY, MACRO_ANIM_NONE, wide influence
    ("TrueKey Heat1", 0, 1, False),       # MACRO_POS_TRUEKEY, MACRO_ANIM_HEAT, no influence
    ("TrueKey Heat1 Wide", 0, 1, True),   # MACRO_POS_TRUEKEY, MACRO_ANIM_HEAT, wide influence
    ("TrueKey Heat2", 0, 2, False),       # MACRO_POS_TRUEKEY, MACRO_ANIM_SUSTAIN, no influence
    ("TrueKey Heat2 Wide", 0, 2, True),   # MACRO_POS_TRUEKEY, MACRO_ANIM_SUSTAIN, wide influence
    
    # Zone presets
    ("Zone Normal", 1, 0, False),         # MACRO_POS_ZONE, MACRO_ANIM_NONE, no influence
    ("Zone Wide", 1, 0, True),            # MACRO_POS_ZONE, MACRO_ANIM_NONE, wide influence
    ("Zone Heat", 1, 1, False),           # MACRO_POS_ZONE, MACRO_ANIM_HEAT, no influence
    ("Zone Heat Wide", 1, 1, True),       # MACRO_POS_ZONE, MACRO_ANIM_HEAT, wide influence
    
    # Loop Zones (Quadrant)
    ("Loop Zones", 2, 0, False),          # MACRO_POS_QUADRANT, MACRO_ANIM_NONE, no influence
    ("Loop Zones Wide", 2, 0, True),      # MACRO_POS_QUADRANT, MACRO_ANIM_NONE, wide influence
    
    # Row presets (only work with row animations)
    ("Row Left", 7, 3, False),            # MACRO_POS_LOOP_ROW_COL0, MACRO_ANIM_MOVING_DOTS_ROW, no influence
    ("Row Left Wide", 7, 3, True),        # MACRO_POS_LOOP_ROW_COL0, MACRO_ANIM_MOVING_DOTS_ROW, wide influence
    ("Row Right", 8, 3, False),           # MACRO_POS_LOOP_ROW_COL13, MACRO_ANIM_MOVING_DOTS_ROW, no influence
    ("Row Right Wide", 8, 3, True),       # MACRO_POS_LOOP_ROW_COL13, MACRO_ANIM_MOVING_DOTS_ROW, wide influence
    ("Row Alt", 9, 3, False),             # MACRO_POS_LOOP_ROW_ALT, MACRO_ANIM_MOVING_DOTS_ROW, no influence
    ("Row Alt Wide", 9, 3, True),         # MACRO_POS_LOOP_ROW_ALT, MACRO_ANIM_MOVING_DOTS_ROW, wide influence
    ("Row Zone", 1, 3, False),            # MACRO_POS_ZONE, MACRO_ANIM_MOVING_DOTS_ROW, no influence
    ("Row Zone Wide", 1, 3, True),        # MACRO_POS_ZONE, MACRO_ANIM_MOVING_DOTS_ROW, wide influence
    
    # Column presets (only work with column animations)
    ("Column Loops", 10, 4, False),       # MACRO_POS_LOOP_COL, MACRO_ANIM_MOVING_DOTS_COL, no influence
    ("Column Loops Wide", 10, 4, True),   # MACRO_POS_LOOP_COL, MACRO_ANIM_MOVING_DOTS_COL, wide influence
    ("Column Zone", 1, 4, False),         # MACRO_POS_ZONE, MACRO_ANIM_MOVING_DOTS_COL, no influence
    ("Column Zone Wide", 1, 4, True),     # MACRO_POS_ZONE, MACRO_ANIM_MOVING_DOTS_COL, wide influence
]

CUSTOM_LIGHT_BACKGROUNDS = [
    "None", "Static", "BPM Pulse Fade", "BPM All Disco"
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
    """Handler for the Rescan LED Positions button - uses VialKeyboard infrastructure"""

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
        """Rescan LED positions on the keyboard using VialKeyboard infrastructure"""
        try:
            if hasattr(self.device.keyboard, 'rescan_led_positions'):
                success = self.device.keyboard.rescan_led_positions()
                if success:
                    print("LED positions rescanned successfully")
                    self.update.emit()
                else:
                    print("Failed to rescan LED positions")
            else:
                print("Rescan LED positions method not implemented on keyboard")
        except Exception as e:
            print(f"Error rescanning LED positions: {e}")


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
        layout.addWidget(live_label, 0, 0, 1, 2)

        live_animation = QComboBox()
        for preset_name, _, _, _ in LIVE_ANIMATION_PRESETS:
            live_animation.addItem(preset_name)
        live_animation.currentIndexChanged.connect(lambda idx, s=slot: self.on_live_animation_changed(s, idx))
        layout.addWidget(live_animation, 1, 0, 1, 2)

        # Macro Animation section
        macro_label = QLabel(tr("RGBConfigurator", "Macro Animation:"))
        macro_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(macro_label, 2, 0, 1, 2)

        macro_animation = QComboBox()
        for preset_name, _, _, _ in MACRO_ANIMATION_PRESETS:
            macro_animation.addItem(preset_name)
        macro_animation.currentIndexChanged.connect(lambda idx, s=slot: self.on_macro_animation_changed(s, idx))
        layout.addWidget(macro_animation, 3, 0, 1, 2)

        # Effects section
        effects_label = QLabel(tr("RGBConfigurator", "Effects:"))
        effects_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(effects_label, 4, 0, 1, 2)

        # Background
        layout.addWidget(QLabel(tr("RGBConfigurator", "Background:")), 5, 0)
        background = QComboBox()
        for bg in CUSTOM_LIGHT_BACKGROUNDS:
            background.addItem(bg)
        background.currentIndexChanged.connect(lambda idx, s=slot: self.on_background_changed(s, idx))
        layout.addWidget(background, 5, 1)

        # Color Type
        layout.addWidget(QLabel(tr("RGBConfigurator", "Color Type:")), 6, 0)
        color_type = QComboBox()
        for color in CUSTOM_LIGHT_COLOR_TYPES:
            color_type.addItem(color)
        color_type.currentIndexChanged.connect(lambda idx, s=slot: self.on_color_type_changed(s, idx))
        layout.addWidget(color_type, 6, 1)

        # Sustain Mode (renamed from Pulse Mode)
        layout.addWidget(QLabel(tr("RGBConfigurator", "Sustain:")), 7, 0)
        sustain_mode = QComboBox()
        for sustain in CUSTOM_LIGHT_SUSTAIN_MODES:
            sustain_mode.addItem(sustain)
        sustain_mode.currentIndexChanged.connect(lambda idx, s=slot: self.on_sustain_mode_changed(s, idx))
        layout.addWidget(sustain_mode, 7, 1)

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
        layout.addWidget(buttons_widget, 8, 0, 1, 2)

        # Store widgets for this slot
        self.slot_widgets[slot] = {
            'live_animation': live_animation,
            'macro_animation': macro_animation,
            'background': background,
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
                    if config:
                        widgets = self.slot_widgets[slot]
                        
                        # Find matching live animation preset
                        live_pos, live_anim, influence = config[0], config[2], bool(config[4])
                        live_preset_idx = self.find_live_preset_index(live_pos, live_anim, influence)
                        widgets['live_animation'].setCurrentIndex(live_preset_idx)
                        
                        # Find matching macro animation preset
                        macro_pos, macro_anim = config[1], config[3]
                        macro_preset_idx = self.find_macro_preset_index(macro_pos, macro_anim, influence)
                        widgets['macro_animation'].setCurrentIndex(macro_preset_idx)
                        
                        widgets['background'].setCurrentIndex(min(config[5], len(CUSTOM_LIGHT_BACKGROUNDS) - 1))
                        widgets['sustain_mode'].setCurrentIndex(min(config[6], len(CUSTOM_LIGHT_SUSTAIN_MODES) - 1))
                        widgets['color_type'].setCurrentIndex(min(config[7], len(CUSTOM_LIGHT_COLOR_TYPES) - 1))
                    else:
                        self.set_slot_defaults(slot)
                else:
                    print(f"Custom slot config methods not implemented on keyboard")
                    self.set_slot_defaults(slot)
            except Exception as e:
                print(f"Error updating custom lights slot {slot}: {e}")
                self.set_slot_defaults(slot)

        self.unblock_signals()

    def find_live_preset_index(self, position, animation, influence):
        """Find the index of a live preset matching the given parameters"""
        for i, (_, pos, anim, inf) in enumerate(LIVE_ANIMATION_PRESETS):
            if pos == position and anim == animation and inf == influence:
                return i
        return 0  # Default to first preset if no match

    def find_macro_preset_index(self, position, animation, influence):
        """Find the index of a macro preset matching the given parameters"""
        for i, (_, pos, anim, inf) in enumerate(MACRO_ANIMATION_PRESETS):
            if pos == position and anim == animation and inf == influence:
                return i
        return 0  # Default to first preset if no match

    def set_slot_defaults(self, slot):
        """Set default values for a slot"""
        widgets = self.slot_widgets[slot]
        widgets['live_animation'].setCurrentIndex(0)      # TrueKey Normal
        widgets['macro_animation'].setCurrentIndex(0)     # TrueKey Normal
        widgets['background'].setCurrentIndex(0)          # None
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

    # Event handlers using VialKeyboard infrastructure
    def on_live_animation_changed(self, slot, index):
        """Handle live animation preset change"""
        if index < len(LIVE_ANIMATION_PRESETS):
            _, position, animation, influence = LIVE_ANIMATION_PRESETS[index]
            if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
                self.device.keyboard.set_custom_slot_parameter(slot, 0, position)    # live_positioning
                self.device.keyboard.set_custom_slot_parameter(slot, 2, animation)   # live_animation
                self.device.keyboard.set_custom_slot_parameter(slot, 4, 1 if influence else 0)  # influence
                self.update.emit()
            else:
                print(f"Live animation changed: slot {slot}, position {position}, animation {animation}, influence {influence}")

    def on_macro_animation_changed(self, slot, index):
        """Handle macro animation preset change"""
        if index < len(MACRO_ANIMATION_PRESETS):
            _, position, animation, influence = MACRO_ANIMATION_PRESETS[index]
            if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
                self.device.keyboard.set_custom_slot_parameter(slot, 1, position)    # macro_positioning
                self.device.keyboard.set_custom_slot_parameter(slot, 3, animation)   # macro_animation
                self.device.keyboard.set_custom_slot_parameter(slot, 4, 1 if influence else 0)  # influence
                self.update.emit()
            else:
                print(f"Macro animation changed: slot {slot}, position {position}, animation {animation}, influence {influence}")

    def on_background_changed(self, slot, index):
        """Handle background change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 5, index)
            self.update.emit()
        else:
            print(f"Background changed: slot {slot}, index {index}")

    def on_sustain_mode_changed(self, slot, index):
        """Handle sustain mode change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 6, index)
            self.update.emit()
        else:
            print(f"Sustain mode changed: slot {slot}, index {index}")

    def on_color_type_changed(self, slot, index):
        """Handle color type change"""
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(slot, 7, index)
            self.update.emit()
        else:
            print(f"Color type changed: slot {slot}, index {index}")

    def on_save_slot(self, slot):
        """Save current settings for a slot (with auto-enable)"""
        try:
            # Force update from current UI state
            widgets = self.slot_widgets[slot]
            
            # Get live animation preset
            live_idx = widgets['live_animation'].currentIndex()
            _, live_pos, live_anim, influence = LIVE_ANIMATION_PRESETS[live_idx]
            
            # Get macro animation preset
            macro_idx = widgets['macro_animation'].currentIndex()
            _, macro_pos, macro_anim, _ = MACRO_ANIMATION_PRESETS[macro_idx]  # Use live influence for both
            
            # Create parameters array
            params = [
                live_pos,                                    # live_positioning
                macro_pos,                                   # macro_positioning
                live_anim,                                   # live_animation
                macro_anim,                                  # macro_animation
                1 if influence else 0,                       # influence
                widgets['background'].currentIndex(),        # background_mode
                widgets['sustain_mode'].currentIndex(),      # sustain_mode (was pulse_mode)
                widgets['color_type'].currentIndex(),        # color_type
                1                                           # enabled (always enabled when saving)
            ]
            
            if hasattr(self.device.keyboard, 'set_all_custom_slot_parameters'):
                success = self.device.keyboard.set_all_custom_slot_parameters(slot, params)
                if success:
                    print(f"Saved all settings to slot {slot + 1}")
                    self.update.emit()
                else:
                    print(f"Failed to save settings to slot {slot + 1}")
            else:
                print(f"Save slot {slot + 1} with params: {params} (keyboard method not implemented)")
                
        except Exception as e:
            print(f"Error saving slot {slot + 1} settings: {e}")

    def on_reset_slot(self, slot):
        """Reset a slot to defaults"""
        try:
            if hasattr(self.device.keyboard, 'reset_custom_slot'):
                success = self.device.keyboard.reset_custom_slot(slot)
                if success:
                    self.set_slot_defaults(slot)
                    self.update.emit()
                    print(f"Reset slot {slot + 1} to defaults")
                else:
                    print(f"Failed to reset slot {slot + 1}")
            else:
                print(f"Reset slot {slot + 1} to defaults (keyboard method not implemented)")
                self.set_slot_defaults(slot)
        except Exception as e:
            print(f"Error resetting slot {slot + 1}: {e}")

    def on_load_preset(self, slot, index):
        """Load a preset configuration"""
        if index == 0:  # "Load Preset..." header
            return
            
        preset_index = index - 1  # Adjust for header
        try:
            if hasattr(self.device.keyboard, 'load_custom_slot_preset'):
                success = self.device.keyboard.load_custom_slot_preset(slot, preset_index)
                if success:
                    # Update the UI for this slot
                    self.update_from_keyboard()
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
        
        # Add the rescan button handler BEFORE the layer RGB handler
        self.handler_rescan = RescanButtonHandler(self.container)
        self.handler_rescan.update.connect(self.update_from_keyboard)
        
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