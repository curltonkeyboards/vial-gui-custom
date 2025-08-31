# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy, QGridLayout, QLabel, QSlider, \
    QComboBox, QColorDialog, QCheckBox, QTabWidget, QMenu, QAction

from editor.basic_editor import BasicEditor
from widgets.clickable_label import ClickableLabel
from util import tr
from vial_device import VialKeyboard
from protocol.constants import CMD_VIA_VIAL_PREFIX, CMD_VIAL_LAYER_RGB_SAVE, CMD_VIAL_LAYER_RGB_LOAD, \
    CMD_VIAL_LAYER_RGB_ENABLE, CMD_VIAL_LAYER_RGB_GET_STATUS, CMD_VIAL_CUSTOM_ANIM_SET_PARAM, \
    CMD_VIAL_CUSTOM_ANIM_GET_PARAM, CMD_VIAL_CUSTOM_ANIM_SET_ALL, CMD_VIAL_CUSTOM_ANIM_GET_ALL, \
    CMD_VIAL_CUSTOM_ANIM_SAVE, CMD_VIAL_CUSTOM_ANIM_LOAD, CMD_VIAL_CUSTOM_ANIM_RESET_SLOT, \
    CMD_VIAL_CUSTOM_ANIM_GET_STATUS, CMD_VIAL_CUSTOM_ANIM_RESCAN_LEDS
import time

NUM_CUSTOM_SLOTS = 50  # Change this to your desi5red number

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
    VialRGBEffect(4, "Gradient Column"),
    VialRGBEffect(5, "Gradient Row"),
    VialRGBEffect(6, "Breathing"),
    VialRGBEffect(7, "Band Sat"),
    VialRGBEffect(8, "Band Val"),
    VialRGBEffect(9, "Band Pinwheel Sat"),
    VialRGBEffect(10, "Band Pinwheel Val"),
    VialRGBEffect(11, "Band Spiral Sat"),
    VialRGBEffect(12, "Band Spiral Val"),
    VialRGBEffect(13, "Cycle All"),
    VialRGBEffect(14, "Cycle Row"),
    VialRGBEffect(15, "Cycle Column"),
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
    VialRGBEffect(106, "Random 1 - Loop"),
    VialRGBEffect(107, "Random 2 - Loop"),
    VialRGBEffect(108, "Random 3 - Loop"),
    VialRGBEffect(109, "Random 1 - BPM"),
    VialRGBEffect(110, "Random 2 - BPM"),
    VialRGBEffect(111, "Random 3 - BPM"),
    VialRGBEffect(112, "Random 1 - Manual"),
    VialRGBEffect(113, "Random 2 - Manual"),
    VialRGBEffect(114, "Random 3 - Manual"),
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
    VialRGBEffect(69, "Custom Slot 13"),
    VialRGBEffect(70, "Custom Slot 14"),
    VialRGBEffect(71, "Custom Slot 15"),
    VialRGBEffect(72, "Custom Slot 16"),
    VialRGBEffect(73, "Custom Slot 17"),
    VialRGBEffect(74, "Custom Slot 18"),
    VialRGBEffect(75, "Custom Slot 19"),
    VialRGBEffect(76, "Custom Slot 20"),
    VialRGBEffect(77, "Custom Slot 21"),
    VialRGBEffect(78, "Custom Slot 22"),
    VialRGBEffect(79, "Custom Slot 23"),
    VialRGBEffect(80, "Custom Slot 24"),
    VialRGBEffect(81, "Custom Slot 25"),
    VialRGBEffect(82, "Custom Slot 26"),
    VialRGBEffect(83, "Custom Slot 27"),
    VialRGBEffect(84, "Custom Slot 28"),
    VialRGBEffect(85, "Custom Slot 29"),
    VialRGBEffect(86, "Custom Slot 30"),
    VialRGBEffect(87, "Custom Slot 31"),
    VialRGBEffect(88, "Custom Slot 32"),
    VialRGBEffect(89, "Custom Slot 33"),
    VialRGBEffect(90, "Custom Slot 34"),
    VialRGBEffect(91, "Custom Slot 35"),
    VialRGBEffect(92, "Custom Slot 36"),
    VialRGBEffect(93, "Custom Slot 37"),
    VialRGBEffect(94, "Custom Slot 38"),
    VialRGBEffect(95, "Custom Slot 39"),
    VialRGBEffect(96, "Custom Slot 40"),
    VialRGBEffect(97, "Custom Slot 41"),
    VialRGBEffect(98, "Custom Slot 42"),
    VialRGBEffect(99, "Custom Slot 43"),
    VialRGBEffect(100, "Custom Slot 44"),
    VialRGBEffect(101, "Custom Slot 45"),
    VialRGBEffect(102, "Custom Slot 46"),
    VialRGBEffect(103, "Custom Slot 47"),
    VialRGBEffect(104, "Custom Slot 48"),
    VialRGBEffect(105, "Custom Slot 49"),
]


# Hierarchical structure for effects
# Hierarchical structure for effects - COMPLETE REWRITE WITH SHIFTED INDICES
LIVE_EFFECTS_HIERARCHY = {
    "Simple": [
        {"name": "Simple", "index": 0},
        {"name": "Simple Solo", "index": 1}
    ],
    "Wide": [
        {"name": "Wide", "index": 2},
        {"name": "Wide Solo", "index": 3},
        {"name": "Wider", "index": 4},
        {"name": "Wider Solo", "index": 5}
    ],
    "Heatmap": [
        {"name": "Heatmap", "index": 6},
        {"name": "Heatmap 2", "index": 7}
    ],
    "Column": [
        {"name": "Column Short", "index": 8},
        {"name": "Column Short Solo", "index": 9}
    ],
    "Row": [
        {"name": "Row Short", "index": 10},
        {"name": "Row Short Solo", "index": 11}
    ],
    "Cross": [
        {"name": "Cross Short", "index": 12},
        {"name": "Cross Short Solo", "index": 13},
        {"name": "Criss Cross", "index": 14},
        {"name": "Criss Cross Solo", "index": 15}
    ],
    "Horizontal Dots": [
        {"name": "Horizontal Dots Short", "index": 16},
        {"name": "Horizontal Dots Short Solo", "index": 17},
        {"name": "Horizontal Dots Long", "index": 18},
        {"name": "Horizontal Dots Long Solo", "index": 19},
        {"name": "Horizontal Dots Short Reverse", "index": 106},
        {"name": "Horizontal Dots Short Reverse Solo", "index": 107},
        {"name": "Horizontal Dots Long Reverse", "index": 108},
        {"name": "Horizontal Dots Long Reverse Solo", "index": 109}
    ],
    "Vertical Dots": [
        {"name": "Vertical Dots Short", "index": 20},
        {"name": "Vertical Dots Short Solo", "index": 21},
        {"name": "Vertical Dots Long", "index": 22},
        {"name": "Vertical Dots Long Solo", "index": 23},
        {"name": "Vertical Dots Short Reverse", "index": 110},
        {"name": "Vertical Dots Short Reverse Solo", "index": 111},
        {"name": "Vertical Dots Long Reverse", "index": 112},
        {"name": "Vertical Dots Long Reverse Solo", "index": 113}
    ],
    "Diagonal Dots": [
        {"name": "Diagonal Dots 1", "index": 24},
        {"name": "Diagonal Dots 1 Solo", "index": 25},
        {"name": "Diagonal Dots 2", "index": 26},
        {"name": "Diagonal Dots 2 Solo", "index": 27}
    ],
    "Cross Dots": [
        {"name": "Cross Dots Short", "index": 28},
        {"name": "Cross Dots Short Solo", "index": 29},
        {"name": "Cross Dots Long", "index": 30},
        {"name": "Cross Dots Long Solo", "index": 31}
    ],
    "Diagonal Burst": [
        {"name": "Diagonal Burst", "index": 32},
        {"name": "Diagonal Burst Solo", "index": 33}
    ],
    "Criss Cross Dots": [
        {"name": "Criss Cross Dots", "index": 34},
        {"name": "Criss Cross Dots Solo", "index": 35}
    ],
    "Ripple": [
        {"name": "Ripple Small", "index": 36},
        {"name": "Ripple Small Solo", "index": 37},
        {"name": "Ripple Med", "index": 38},
        {"name": "Ripple Med Solo", "index": 39},
        {"name": "Ripple Large", "index": 40},
        {"name": "Ripple Large Solo", "index": 41},
        {"name": "Ripple Massive", "index": 42},
        {"name": "Ripple Massive Solo", "index": 43}
    ],
    "Reverse Ripple": [
        {"name": "Reverse Ripple Small", "index": 44},
        {"name": "Reverse Ripple Small Solo", "index": 48},
        {"name": "Reverse Ripple Med", "index": 45},
        {"name": "Reverse Ripple Med Solo", "index": 49},
        {"name": "Reverse Ripple Large", "index": 46},
        {"name": "Reverse Ripple Large Solo", "index": 50},
        {"name": "Reverse Ripple Massive", "index": 47},
        {"name": "Reverse Ripple Massive Solo", "index": 51}
    ],
    "Expanding Row": [
        {"name": "Expanding Row Short", "index": 52},
        {"name": "Expanding Row Short Solo", "index": 53},
        {"name": "Expanding Row Long", "index": 54},
        {"name": "Expanding Row Long Solo", "index": 55}
    ],
    "Expanding Column": [
        {"name": "Expanding Column Short", "index": 56},
        {"name": "Expanding Column Short Solo", "index": 57},
        {"name": "Expanding Column Long", "index": 58},
        {"name": "Expanding Column Long Solo", "index": 59}
    ],
    "Outward Burst": [
        {"name": "Outward Burst Small", "index": 60},
        {"name": "Outward Burst Small Solo", "index": 61},
        {"name": "Outward Burst Med", "index": 62},
        {"name": "Outward Burst Med Solo", "index": 63},
        {"name": "Outward Burst Large", "index": 64},
        {"name": "Outward Burst Large Solo", "index": 65}
    ],
        "Inward Burst": [
        {"name": "Inward Burst Small", "index": 166},
        {"name": "Inward Burst Small Solo", "index": 167},
        {"name": "Inward Burst Med", "index": 168},
        {"name": "Inward Burst Med Solo", "index": 169},
        {"name": "Inward Burst Large", "index": 170},
        {"name": "Inward Burst Large Solo", "index": 171}
    ],
    "Volume Column": [
        {"name": "Volume Column Small", "index": 66},
        {"name": "Volume Column Small Solo", "index": 67},
        {"name": "Volume Column Small Wide", "index": 68},
        {"name": "Volume Column Small Wide Solo", "index": 69},
        {"name": "Volume Column Large", "index": 70},
        {"name": "Volume Column Large Solo", "index": 71},
        {"name": "Volume Column Large Wide", "index": 72},
        {"name": "Volume Column Large Wide Solo", "index": 73}
    ],
    "Volume Row": [
        {"name": "Volume Row Small", "index": 74},
        {"name": "Volume Row Small Solo", "index": 75},
        {"name": "Volume Row Small Wide", "index": 76},
        {"name": "Volume Row Small Wide Solo", "index": 77},
        {"name": "Volume Row Med", "index": 78},
        {"name": "Volume Row Med Solo", "index": 79},
        {"name": "Volume Row Med Wide", "index": 80},
        {"name": "Volume Row Med Wide Solo", "index": 81},
        {"name": "Volume Row Large", "index": 82},
        {"name": "Volume Row Large Solo", "index": 83},
        {"name": "Volume Row Large Wide", "index": 84},
        {"name": "Volume Row Large Wide Solo", "index": 85}
    ],
    "Collapsing Column": [
        {"name": "Collapsing Column Small", "index": 86},
        {"name": "Collapsing Column Small Solo", "index": 87},
        {"name": "Collapsing Column Small Wide", "index": 88},
        {"name": "Collapsing Column Small Wide Solo", "index": 89},
        {"name": "Collapsing Column Large", "index": 90},
        {"name": "Collapsing Column Large Solo", "index": 91},
        {"name": "Collapsing Column Large Wide", "index": 92},
        {"name": "Collapsing Column Large Wide Solo", "index": 93}
    ],
    "Collapsing Row": [
        {"name": "Collapsing Row Small", "index": 94},
        {"name": "Collapsing Row Small Solo", "index": 95},
        {"name": "Collapsing Row Small Wide", "index": 96},
        {"name": "Collapsing Row Small Wide Solo", "index": 97},
        {"name": "Collapsing Row Med", "index": 98},
        {"name": "Collapsing Row Med Solo", "index": 99},
        {"name": "Collapsing Row Med Wide", "index": 100},
        {"name": "Collapsing Row Med Wide Solo", "index": 101},
        {"name": "Collapsing Row Large", "index": 102},
        {"name": "Collapsing Row Large Solo", "index": 103},
        {"name": "Collapsing Row Large Wide", "index": 104},
        {"name": "Collapsing Row Large Wide Solo", "index": 105}
    ],
    "3-Pixel Columns": [
        {"name": "3-Pixel Columns Expand", "index": 114},
        {"name": "3-Pixel Columns Expand Solo", "index": 115},
        {"name": "3-Pixel Columns Expand No Fade", "index": 116},
        {"name": "3-Pixel Columns Expand No Fade Solo", "index": 117},
        {"name": "3-Pixel Columns Reverse", "index": 118},
        {"name": "3-Pixel Columns Reverse Solo", "index": 119},
        {"name": "3-Pixel Columns Reverse No Fade", "index": 120},
        {"name": "3-Pixel Columns Reverse No Fade Solo", "index": 121}
    ],
    "3-Pixel Rows": [
        {"name": "3-Pixel Rows Expand", "index": 122},
        {"name": "3-Pixel Rows Expand Solo", "index": 123},
        {"name": "3-Pixel Rows Expand No Fade", "index": 124},
        {"name": "3-Pixel Rows Expand No Fade Solo", "index": 125},
        {"name": "3-Pixel Rows Reverse", "index": 126},
        {"name": "3-Pixel Rows Reverse Solo", "index": 127},
        {"name": "3-Pixel Rows Reverse No Fade", "index": 128},
        {"name": "3-Pixel Rows Reverse No Fade Solo", "index": 129}
    ],
    "8-Pixel Columns": [
        {"name": "8-Pixel Columns Expand", "index": 130},
        {"name": "8-Pixel Columns Expand Solo", "index": 131},
        {"name": "8-Pixel Columns Expand No Fade", "index": 132},
        {"name": "8-Pixel Columns Expand No Fade Solo", "index": 133},
        {"name": "8-Pixel Columns Reverse", "index": 134},
        {"name": "8-Pixel Columns Reverse Solo", "index": 135},
        {"name": "8-Pixel Columns Reverse No Fade", "index": 136},
        {"name": "8-Pixel Columns Reverse No Fade Solo", "index": 137}
    ],
    "8-Pixel Rows": [
        {"name": "8-Pixel Rows Expand", "index": 138},
        {"name": "8-Pixel Rows Expand Solo", "index": 139},
        {"name": "8-Pixel Rows Expand No Fade", "index": 140},
        {"name": "8-Pixel Rows Expand No Fade Solo", "index": 141},
        {"name": "8-Pixel Rows Reverse", "index": 142},
        {"name": "8-Pixel Rows Reverse Solo", "index": 143},
        {"name": "8-Pixel Rows Reverse No Fade", "index": 144},
        {"name": "8-Pixel Rows Reverse No Fade Solo", "index": 145}
    ],
    "All Orthogonal": [
        {"name": "All Orthogonal Dots Reverse", "index": 146},
        {"name": "All Orthogonal Dots Reverse Solo", "index": 147},
        {"name": "All Orthogonal Dots Reverse No Fade", "index": 148},
        {"name": "All Orthogonal Dots Reverse No Fade Solo", "index": 149},
        {"name": "All Orthogonal 3-Pixel Expand", "index": 150},
        {"name": "All Orthogonal 3-Pixel Expand Solo", "index": 151},
        {"name": "All Orthogonal 3-Pixel Expand No Fade", "index": 152},
        {"name": "All Orthogonal 3-Pixel Expand No Fade Solo", "index": 153},
        {"name": "All Orthogonal 3-Pixel Reverse", "index": 154},
        {"name": "All Orthogonal 3-Pixel Reverse Solo", "index": 155},
        {"name": "All Orthogonal 3-Pixel Reverse No Fade", "index": 156},
        {"name": "All Orthogonal 3-Pixel Reverse No Fade Solo", "index": 157},
        {"name": "All Orthogonal 8-Pixel Expand", "index": 158},
        {"name": "All Orthogonal 8-Pixel Expand Solo", "index": 159},
        {"name": "All Orthogonal 8-Pixel Expand No Fade", "index": 160},
        {"name": "All Orthogonal 8-Pixel Expand No Fade Solo", "index": 161},
        {"name": "All Orthogonal 8-Pixel Reverse", "index": 162},
        {"name": "All Orthogonal 8-Pixel Reverse Solo", "index": 163},
        {"name": "All Orthogonal 8-Pixel Reverse No Fade", "index": 164},
        {"name": "All Orthogonal 8-Pixel Reverse No Fade Solo", "index": 165}
    ]
}


# Hierarchical structure for backgrounds
BACKGROUNDS_HIERARCHY = {
    "None": [
        {"name": "None", "index": 0},
    ],
    "Basic": [
        {"name": "Basic", "index": 1},
        {"name": "Basic Desaturated", "index": 79},
        {"name": "Basic 2", "index": 2},
        {"name": "Basic 2 Desaturated", "index": 80},
        {"name": "Basic 3", "index": 3},
        {"name": "Basic 3 Desaturated", "index": 81},
        {"name": "Basic 4", "index": 4},
        {"name": "Basic 4 Desaturated", "index": 82},
    ],
    "Autolight": [
        {"name": "Autolight", "index": 5},
        {"name": "Autolight Desaturated", "index": 83},
        {"name": "Autolight 2", "index": 6},
        {"name": "Autolight 2 Desaturated", "index": 84},
        {"name": "Autolight Cycle", "index": 7},
        {"name": "Autolight Cycle Desaturated", "index": 85},
        {"name": "Autolight Breathing", "index": 8},
        {"name": "Autolight Breathing Desaturated", "index": 86},
    ],
    "Cycle Effects": [
        {"name": "Cycle All", "index": 59},
        {"name": "Cycle All Desaturated", "index": 87},
        {"name": "Cycle Left Right", "index": 60},
        {"name": "Cycle Left Right Desaturated", "index": 88},
        {"name": "Cycle Up Down", "index": 61},
        {"name": "Cycle Up Down Desaturated", "index": 89},
    ],
    "Ripple Effects": [
        {"name": "Cycle Out In", "index": 62},
        {"name": "Cycle Out In Desaturated", "index": 90},
        {"name": "Cycle Out In Dual", "index": 63},
        {"name": "Cycle Out In Dual Desaturated", "index": 91},
        {"name": "Rainbow Pinwheel", "index": 64},
        {"name": "Rainbow Pinwheel Desaturated", "index": 92},
    ],
    "Wave Effects": [
        {"name": "Wave Left Right", "index": 66},
        {"name": "Wave Left Right Desaturated", "index": 94},
        {"name": "Diagonal Wave", "index": 67},
        {"name": "Diagonal Wave Desaturated", "index": 95},
        # NEW DIAGONAL WAVE VARIATIONS
        {"name": "Diagonal Wave Hue Cycle", "index": 107},
        {"name": "Diagonal Wave Hue Cycle Desaturated", "index": 114},
        {"name": "Diagonal Wave Dual Color", "index": 108},
        {"name": "Diagonal Wave Dual Color Desaturated", "index": 115},
        {"name": "Diagonal Wave Dual Hue Cycle", "index": 109},
        {"name": "Diagonal Wave Dual Hue Cycle Desaturated", "index": 116},
        {"name": "Diagonal Wave Reverse", "index": 110},
        {"name": "Diagonal Wave Reverse Desaturated", "index": 117},
        {"name": "Diagonal Wave Reverse Hue Cycle", "index": 111},
        {"name": "Diagonal Wave Reverse Hue Cycle Desaturated", "index": 118},
        {"name": "Diagonal Wave Reverse Dual Color", "index": 112},
        {"name": "Diagonal Wave Reverse Dual Color Desaturated", "index": 119},
        {"name": "Diagonal Wave Reverse Dual Hue Cycle", "index": 113},
        {"name": "Diagonal Wave Reverse Dual Hue Cycle Desaturated", "index": 120},
    ],
    "Breathing Effects": [
        {"name": "Breathing", "index": 65},
        {"name": "Breathing Desaturated", "index": 93},
    ],
    "Gradient Effects": [
        {"name": "Gradient Up Down", "index": 68},
        {"name": "Gradient Up Down Desaturated", "index": 96},
        {"name": "Gradient Left Right", "index": 69},
        {"name": "Gradient Left Right Desaturated", "index": 97},
        {"name": "Gradient Diagonal", "index": 70},
        {"name": "Gradient Diagonal Desaturated", "index": 98},
    ],
    "Hue Effects": [
        {"name": "Hue Breathing", "index": 71},
        {"name": "Hue Breathing Desaturated", "index": 99},
        {"name": "Hue Pendulum", "index": 72},
        {"name": "Hue Pendulum Desaturated", "index": 100},
        {"name": "Hue Wave", "index": 73},
        {"name": "Hue Wave Desaturated", "index": 101},
    ],
    "Rainbow Effects": [
        {"name": "Rainbow Moving Chevron", "index": 74},
        {"name": "Rainbow Moving Chevron Desaturated", "index": 102},
    ],
    "Band Effects": [
        {"name": "Band Pinwheel Sat", "index": 75},
        {"name": "Band Pinwheel Sat Desaturated", "index": 103},
        {"name": "Band Pinwheel Val", "index": 76},
        {"name": "Band Pinwheel Val Desaturated", "index": 104},
        {"name": "Band Spiral Sat", "index": 77},
        {"name": "Band Spiral Sat Desaturated", "index": 105},
        {"name": "Band Spiral Val", "index": 78},
        {"name": "Band Spiral Val Desaturated", "index": 106},
    ],
        "BPM Pulse Fade": [
        {"name": "BPM Pulse Fade", "index": 9},
        {"name": "BPM Pulse Fade 2", "index": 10},
        {"name": "BPM Pulse Fade Desaturated", "index": 11},
        {"name": "BPM Pulse Fade Disco", "index": 12},
        {"name": "BPM Pulse Fade Solid Background", "index": 13},
        {"name": "BPM Pulse Fade Solid Background 2", "index": 14},
        {"name": "BPM Pulse Fade Solid Disco", "index": 15},
        {"name": "BPM Pulse Fade Autolight", "index": 16},
        {"name": "BPM Pulse Fade Autolight 2", "index": 17},
        {"name": "BPM Pulse Fade Autolight Disco", "index": 18},
    ],
    "BPM Quadrants": [
        {"name": "BPM Quadrants", "index": 19},
        {"name": "BPM Quadrants 2", "index": 20},
        {"name": "BPM Quadrants Desaturated", "index": 21},
        {"name": "BPM Quadrants Disco", "index": 22},
        {"name": "BPM Quadrants Solid Background", "index": 23},
        {"name": "BPM Quadrants Solid Background 2", "index": 24},
        {"name": "BPM Quadrants Solid Disco", "index": 25},
        {"name": "BPM Quadrants Autolight", "index": 26},
        {"name": "BPM Quadrants Autolight 2", "index": 27},
        {"name": "BPM Quadrants Autolight Disco", "index": 28},
    ],
    "BPM Row": [
        {"name": "BPM Row", "index": 29},
        {"name": "BPM Row 2", "index": 30},
        {"name": "BPM Row Desaturated", "index": 31},
        {"name": "BPM Row Disco", "index": 32},
        {"name": "BPM Row Solid Background", "index": 33},
        {"name": "BPM Row Solid Background 2", "index": 34},
        {"name": "BPM Row Solid Disco", "index": 35},
        {"name": "BPM Row Autolight", "index": 36},
        {"name": "BPM Row Autolight 2", "index": 37},
        {"name": "BPM Row Autolight Disco", "index": 38},
    ],
    "BPM Column": [
        {"name": "BPM Column", "index": 39},
        {"name": "BPM Column 2", "index": 40},
        {"name": "BPM Column Desaturated", "index": 41},
        {"name": "BPM Column Disco", "index": 42},
        {"name": "BPM Column Solid Background", "index": 43},
        {"name": "BPM Column Solid Background 2", "index": 44},
        {"name": "BPM Column Solid Disco", "index": 45},
        {"name": "BPM Column Autolight", "index": 46},
        {"name": "BPM Column Autolight 2", "index": 47},
        {"name": "BPM Column Autolight Disco", "index": 48},
    ],
    "BPM All": [
        {"name": "BPM All", "index": 49},
        {"name": "BPM All 2", "index": 50},
        {"name": "BPM All Desaturated", "index": 51},
        {"name": "BPM All Disco", "index": 52},
        {"name": "BPM All Solid Background", "index": 53},
        {"name": "BPM All Solid Background 2", "index": 54},
        {"name": "BPM All Solid Disco", "index": 55},
        {"name": "BPM All Autolight", "index": 56},
        {"name": "BPM All Autolight 2", "index": 57},
        {"name": "BPM All Autolight Disco", "index": 58},
    ]
}

# Hierarchical structure for live positioning styles
LIVE_STYLES_HIERARCHY = {
    "Basic Positions": [
        {"name": "TrueKey", "index": 0},
        {"name": "Zone", "index": 1},
        {"name": "Quadrant", "index": 2},
    ],
    "Note Row Positions": [
        {"name": "Note Row Left", "index": 3},
        {"name": "Note Row Right", "index": 4},
        {"name": "Note Row Center", "index": 5},
        {"name": "Note Row Mixed", "index": 9},
    ],
    "Note Column Positions": [
        {"name": "Note Col Top", "index": 6},
        {"name": "Note Col Bottom", "index": 7},
        {"name": "Note Col Center", "index": 8},
        {"name": "Note Col Mixed", "index": 10},
    ],
    "Single Dots": [
        {"name": "Top Dot", "index": 11},
        {"name": "Left Dot", "index": 12},
        {"name": "Right Dot", "index": 13},
        {"name": "Bottom Dot", "index": 14},
        {"name": "Center Dot", "index": 15},
        {"name": "Top Left Dot", "index": 16},
        {"name": "Top Right Dot", "index": 17},
        {"name": "Bottom Left Dot", "index": 18},
        {"name": "Bottom Right Dot", "index": 19},
    ],
    "Note-Based Dots": [
        {"name": "Note Corner Dots", "index": 20},
        {"name": "Note Edge Dots", "index": 21},
        {"name": "Note All Dots", "index": 22},
    ]
}

# Hierarchical structure for macro positioning styles
MACRO_STYLES_HIERARCHY = {
    "Basic Positions": [
        {"name": "TrueKey", "index": 0},
        {"name": "Zone", "index": 1},
        {"name": "Quadrant", "index": 2},
    ],
    "Note Row Positions": [
        {"name": "Note Row Left", "index": 3},
        {"name": "Note Row Right", "index": 4},
        {"name": "Note Row Center", "index": 5},
        {"name": "Note Row Mixed", "index": 9},
    ],
    "Note Column Positions": [
        {"name": "Note Col Top", "index": 6},
        {"name": "Note Col Bottom", "index": 7},
        {"name": "Note Col Center", "index": 8},
        {"name": "Note Col Mixed", "index": 10},
    ],
    "Loop Row Positions": [
        {"name": "Loop Row Left", "index": 11},
        {"name": "Loop Row Right", "index": 12},
        {"name": "Loop Row Center", "index": 13},
        {"name": "Loop Row Alt", "index": 14},
    ],
    "Loop Column Positions": [
        {"name": "Loop Col Top", "index": 15},
        {"name": "Loop Col Bottom", "index": 16},
        {"name": "Loop Col Center", "index": 17},
    ],
    "Loop Blocks": [
        {"name": "Loop Block 3x3", "index": 18},
        {"name": "Loop Block Center", "index": 19},
    ],
    "Single Dots": [
        {"name": "Top Dot", "index": 20},
        {"name": "Left Dot", "index": 21},
        {"name": "Right Dot", "index": 22},
        {"name": "Bottom Dot", "index": 23},
        {"name": "Center Dot", "index": 24},
        {"name": "Top Left Dot", "index": 25},
        {"name": "Top Right Dot", "index": 26},
        {"name": "Bottom Left Dot", "index": 27},
        {"name": "Bottom Right Dot", "index": 28},
    ],
    "Note-Based Dots": [
        {"name": "Note Corner Dots", "index": 29},
        {"name": "Note Edge Dots", "index": 30},
        {"name": "Note All Dots", "index": 31},
    ],
    "Loop-Based Dots": [
        {"name": "Loop Corner Dots", "index": 32},
        {"name": "Loop Edge Dots", "index": 33},
    ]
}

CUSTOM_LIGHT_COLOR_TYPES_HIERARCHY = {
    "Fundamentals": [
        {"name": "Base", "index": 0},
        {"name": "Channel", "index": 1},
        {"name": "Macro", "index": 2},
        {"name": "Rainbow", "index": 3},
        {"name": "Pitch Colors Up", "index": 4},
        {"name": "Pitch Colors Down", "index": 5},
    ],
    "Fundamentals + Max Saturation": [
        {"name": "Base Max Sat", "index": 6},
        {"name": "Channel Max Sat", "index": 7},
        {"name": "Macro Max Sat", "index": 8},
        {"name": "Rainbow Max Sat", "index": 9},
        {"name": "Pitch Colors Up Max Sat", "index": 10},
        {"name": "Pitch Colors Down Max Sat", "index": 11},
    ],
    "Fundamentals + Desaturated": [
        {"name": "Base Desat", "index": 12},
        {"name": "Channel Desat", "index": 13},
        {"name": "Macro Desat", "index": 14},
        {"name": "Rainbow Desat", "index": 15},
        {"name": "Pitch Colors Up Desat", "index": 16},
        {"name": "Pitch Colors Down Desat", "index": 17},
    ],
    "Distance Effects": [
        {"name": "Base Distance", "index": 18},
        {"name": "Channel Distance", "index": 19},
        {"name": "Macro Distance", "index": 20},
        {"name": "Rainbow Distance", "index": 21},
        {"name": "Pitch Colors Up Distance", "index": 22},
        {"name": "Pitch Colors Down Distance", "index": 23},
    ],
    "Distance + Max Saturation": [
        {"name": "Base Distance Max Sat", "index": 24},
        {"name": "Channel Distance Max Sat", "index": 25},
        {"name": "Macro Distance Max Sat", "index": 26},
        {"name": "Rainbow Distance Max Sat", "index": 27},
        {"name": "Pitch Colors Up Distance Max Sat", "index": 28},
        {"name": "Pitch Colors Down Distance Max Sat", "index": 29},
    ],
    "Distance + Desaturated": [
        {"name": "Base Distance Desat", "index": 30},
        {"name": "Channel Distance Desat", "index": 31},
        {"name": "Macro Distance Desat", "index": 32},
        {"name": "Rainbow Distance Desat", "index": 33},
        {"name": "Pitch Colors Up Distance Desat", "index": 34},
        {"name": "Pitch Colors Down Distance Desat", "index": 35},
    ],
    "Special Effects": [
        {"name": "Beat Sync", "index": 36},
        {"name": "Temperature Gradient", "index": 37},
    ],
    "Horizontal Gradients": [
        {"name": "Horizontal Soft", "index": 38},
        {"name": "Horizontal Soft Max Sat", "index": 39},
        {"name": "Horizontal Soft Desat", "index": 40},
        {"name": "Horizontal Medium", "index": 41},
        {"name": "Horizontal Medium Max Sat", "index": 42},
        {"name": "Horizontal Medium Desat", "index": 43},
        {"name": "Horizontal Strong", "index": 44},
        {"name": "Horizontal Strong Max Sat", "index": 45},
        {"name": "Horizontal Strong Desat", "index": 46},
    ],
    "Diagonal Gradients": [
        {"name": "Diagonal Soft", "index": 47},
        {"name": "Diagonal Soft Max Sat", "index": 48},
        {"name": "Diagonal Soft Desat", "index": 49},
        {"name": "Diagonal Medium", "index": 50},
        {"name": "Diagonal Medium Max Sat", "index": 51},
        {"name": "Diagonal Medium Desat", "index": 52},
        {"name": "Diagonal Strong", "index": 53},
        {"name": "Diagonal Strong Max Sat", "index": 54},
        {"name": "Diagonal Strong Desat", "index": 55},
    ],
    "Vertical Gradients": [
        {"name": "Vertical Soft", "index": 56},
        {"name": "Vertical Soft Max Sat", "index": 57},
        {"name": "Vertical Soft Desat", "index": 58},
        {"name": "Vertical Medium", "index": 59},
        {"name": "Vertical Medium Max Sat", "index": 60},
        {"name": "Vertical Medium Desat", "index": 61},
        {"name": "Vertical Strong", "index": 62},
        {"name": "Vertical Strong Max Sat", "index": 63},
        {"name": "Vertical Strong Desat", "index": 64},
    ]
}

# Keep the old list for backward compatibility in validation functions
CUSTOM_LIGHT_COLOR_TYPES = [
    "Base",              # 0
    "Channel",           # 1  
    "Macro",             # 2
    "Heat",              # 3
    "Rainbow",           # 4
    "Channel Distance",  # 5
    "Macro Split",       # 6
    "Macro Distance",    # 7
    "Disco Live",        # 8
    "Disco All",         # 9
    "Channel SAT",       # 10
    "Macro SAT",         # 11
    "Velocity Colors",   # 12
    "Time Shift",        # 13
    "Beat Sync",         # 14
    "Temperature Gradient", # 15
    "Spectrum Cycle"     # 16
]

CUSTOM_LIGHT_SUSTAIN_MODES = [
    "None", "Live Only", "Macro Only", "All"
]

CUSTOM_LIGHT_PRESETS = [
    "Classic TrueKey", "Heat Effects", "Moving Dots", "BPM Disco",
    "Zone Lighting", "Sustain Mode", "Performance Setup"
]


class HierarchicalDropdown(QPushButton):
    """Custom dropdown that supports hierarchical menus"""
    
    valueChanged = pyqtSignal(int)
    
    def __init__(self, hierarchy_dict, parent=None):
        super().__init__(parent)
        self.hierarchy = hierarchy_dict
        self.current_index = 0
        self.current_text = ""
        self.setText("Select...")
        
        # Build the menu
        self.menu = QMenu(self)
        self.build_menu()
        self.setMenu(self.menu)
    
    def build_menu(self):
        """Build hierarchical menu from dictionary"""
        self.menu.clear()
        
        for category, items in self.hierarchy.items():
            if len(items) == 1:
                # Single item - add directly
                action = QAction(items[0]["name"], self)
                action.triggered.connect(lambda checked, idx=items[0]["index"], name=items[0]["name"]: 
                                       self.select_item(idx, name))
                self.menu.addAction(action)
            else:
                # Multiple items - create submenu
                submenu = QMenu(category, self)
                for item in items:
                    action = QAction(item["name"], submenu)
                    action.triggered.connect(lambda checked, idx=item["index"], name=item["name"]: 
                                           self.select_item(idx, name))
                    submenu.addAction(action)
                self.menu.addMenu(submenu)
    
    def select_item(self, index, name):
        """Handle item selection"""
        self.current_index = index
        self.current_text = name
        self.setText(name)
        self.valueChanged.emit(index)
    
    def setCurrentIndex(self, index):
        """Set current selection by index"""
        # Find the item with this index
        for category, items in self.hierarchy.items():
            for item in items:
                if item["index"] == index:
                    self.current_index = index
                    self.current_text = item["name"]
                    self.setText(item["name"])
                    return
        
        # If not found, set to first item
        if self.hierarchy:
            first_category = list(self.hierarchy.keys())[0]
            first_item = self.hierarchy[first_category][0]
            self.current_index = first_item["index"]
            self.current_text = first_item["name"]
            self.setText(first_item["name"])
    
    def currentIndex(self):
        """Get current index"""
        return self.current_index
    
    def blockSignals(self, block):
        """Override to maintain compatibility"""
        super().blockSignals(block)


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
        self.rescan_button = QPushButton(tr("RGBConfigurator", "Rescan LED Positions"))
        self.rescan_button.clicked.connect(self.on_rescan_led_positions)
        self.rescan_button.setStyleSheet("QPushButton { padding: 8px; }")
        self.rescan_button.setMinimumHeight(30)
        
        # Center the button using a horizontal layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.rescan_button)
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
        """Rescan LED positions and restart the application"""
        try:
            print("Starting LED rescan process...")
            
            # Disable the button to prevent multiple clicks
            self.rescan_button.setEnabled(False)
            self.rescan_button.setText("Rescanning... App will restart in 10 seconds")
            
            # Force immediate GUI update to show disabled state
            from PyQt5.QtWidgets import QApplication, QMessageBox
            QApplication.processEvents()
            
            # Send the rescan command
            if hasattr(self.device.keyboard, 'rescan_led_positions'):
                self.device.keyboard.rescan_led_positions()
                print("Rescan LED command sent")
            else:
                print("Rescan LED method not available")
                self.restore_button()
                return
                
            # Wait 10 seconds for firmware to complete processing
            print("Waiting 10 seconds for firmware to complete...")
            import time
            time.sleep(10.0)
            
            print("LED rescan completed, restarting application...")
            
            # Try to restart the application
            self.restart_application()
            
        except Exception as e:
            print(f"Error during LED rescan process: {e}")
            self.restore_button()

    def restart_application(self):
        """Restart the application or shut down with message"""
        try:
            import sys
            import os
            from PyQt5.QtWidgets import QMessageBox, QApplication
            from PyQt5.QtCore import QTimer
            
            # Try to restart the application
            try:
                print("Attempting to restart application...")
                
                # Get the current executable and arguments
                executable = sys.executable
                args = sys.argv
                
                # Show message about restart
                msg = QMessageBox()
                msg.setWindowTitle("LED Rescan Complete")
                msg.setText("LED positions have been rescanned.\nThe application will now restart to refresh all settings.")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setIcon(QMessageBox.Information)
                msg.exec_()
                
                # Close current instance and restart
                QApplication.quit()
                os.execv(executable, [executable] + args[1:])
                
            except Exception as restart_error:
                print(f"Could not restart application: {restart_error}")
                
                # Fall back to shutdown with message
                msg = QMessageBox()
                msg.setWindowTitle("LED Rescan Complete - Please Restart")
                msg.setText("LED positions have been rescanned successfully.\n\n"
                           "Please manually restart the application to ensure "
                           "all RGB settings are properly refreshed.\n\n"
                           "The application will now close.")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setIcon(QMessageBox.Information)
                msg.exec_()
                
                # Shutdown the application
                print("Shutting down application...")
                QApplication.quit()
                sys.exit(0)
                
        except Exception as e:
            print(f"Error during application restart/shutdown: {e}")
            # Emergency shutdown
            import sys
            sys.exit(1)

    def restore_button(self):
        """Restore button to normal state"""
        try:
            self.rescan_button.setEnabled(True)
            self.rescan_button.setText("Rescan LED Positions")
        except Exception as e:
            print(f"Error restoring button: {e}")
            
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

        # Create main tab widget for groups
        self.main_tab_widget = QTabWidget()
        container.addWidget(self.main_tab_widget, row + 1, 0, 1, 2)
        
        # Track the currently active slot (for parameter changes)
        self.current_active_slot = None
        self.current_randomize_slot = None
        
        # Create grouped tabs
        self.slot_tabs = []
        self.slot_widgets = {}
        self.group_tab_widgets = {}  # Store sub-tab widgets for each group
        
        # Define groups: 1-9, 10-19, 20-29, 30-39, 40-49 (removed the single "50" group)
        self.groups = [
            ("1-9", 0, 9),
            ("10-19", 9, 19), 
            ("20-29", 19, 29),
            ("30-39", 29, 39),
            ("40-49", 39, 50)  # Changed to go up to 50 (slots 39-49)
        ]
        
        # Connect main tab change to load lowest slot in group
        self.main_tab_widget.currentChanged.connect(self.on_main_tab_changed)
        
        for group_name, start_idx, end_idx in self.groups:
            self.create_group_tab(group_name, start_idx, end_idx)

        self.widgets = [self.lbl_custom_lights, self.main_tab_widget]

    def create_group_tab(self, group_name, start_idx, end_idx):
        """Create a main tab containing sub-tabs for a group of slots"""
        # Create the main tab widget
        group_widget = QWidget()
        self.main_tab_widget.addTab(group_widget, group_name)
        
        # Create layout for the group
        group_layout = QHBoxLayout(group_widget)
        group_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create sub-tab widget for individual slots in this group
        sub_tab_widget = QTabWidget()
        group_layout.addWidget(sub_tab_widget)
        
        # Store reference to sub-tab widget
        self.group_tab_widgets[group_name] = sub_tab_widget
        
        # Connect tab change signal for this sub-tab widget
        sub_tab_widget.currentChanged.connect(lambda index, start=start_idx: self.on_sub_tab_changed(index, start))
        
        # Create individual slot tabs within this group
        for slot in range(start_idx, end_idx):
            self.create_slot_tab(slot, sub_tab_widget)
        
    def create_slot_tab(self, slot, parent_tab_widget):
        """Create a tab for a single slot within a group's sub-tab widget"""
        # Create tab widget
        tab_widget = QWidget()
        parent_tab_widget.addTab(tab_widget, str(slot + 1))  # Tab names: "1", "2", "3", etc.
        
        # Create layout for this tab
        layout = QGridLayout(tab_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Live Animation section
        live_label = QLabel(tr("RGBConfigurator", "Live Animation:"))
        live_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(live_label, 0, 0, 1, 3)

        # Live Effect - hierarchical dropdown
        layout.addWidget(QLabel(tr("RGBConfigurator", "Effect:")), 1, 0)
        live_effect = HierarchicalDropdown(LIVE_EFFECTS_HIERARCHY)
        live_effect.valueChanged.connect(lambda idx, s=slot: self.on_live_effect_changed(s, idx))
        layout.addWidget(live_effect, 1, 1, 1, 2)

        # Live Style - hierarchical dropdown
        layout.addWidget(QLabel(tr("RGBConfigurator", "Position:")), 2, 0)
        live_style = HierarchicalDropdown(LIVE_STYLES_HIERARCHY)
        live_style.valueChanged.connect(lambda idx, s=slot: self.on_live_style_changed(s, idx))
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

        # Macro Effect - hierarchical dropdown (same as live effects)
        layout.addWidget(QLabel(tr("RGBConfigurator", "Effect:")), 5, 0)
        macro_effect = HierarchicalDropdown(LIVE_EFFECTS_HIERARCHY)  # Same hierarchy as live effects
        macro_effect.valueChanged.connect(lambda idx, s=slot: self.on_macro_effect_changed(s, idx))
        layout.addWidget(macro_effect, 5, 1, 1, 2)

        # Macro Style - hierarchical dropdown
        layout.addWidget(QLabel(tr("RGBConfigurator", "Position:")), 6, 0)
        macro_style = HierarchicalDropdown(MACRO_STYLES_HIERARCHY)
        macro_style.valueChanged.connect(lambda idx, s=slot: self.on_macro_style_changed(s, idx))
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
        effects_label = QLabel(tr("RGBConfigurator", "Background:"))
        effects_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(effects_label, 8, 0, 1, 3)

        # Background - hierarchical dropdown
        layout.addWidget(QLabel(tr("RGBConfigurator", "Background:")), 9, 0)
        background = HierarchicalDropdown(BACKGROUNDS_HIERARCHY)
        background.valueChanged.connect(lambda idx, s=slot: self.on_background_changed(s, idx))
        layout.addWidget(background, 9, 1, 1, 2)

        # Background Brightness slider
        layout.addWidget(QLabel(tr("RGBConfigurator", "Background Brightness:")), 10, 0)
        background_brightness = QSlider(QtCore.Qt.Horizontal)
        background_brightness.setMinimum(0)
        background_brightness.setMaximum(100)
        background_brightness.setValue(30)  # Default 30%
        background_brightness.valueChanged.connect(lambda value, s=slot: self.on_background_brightness_changed(s, value))
        layout.addWidget(background_brightness, 10, 1, 1, 2)

        # Effect Colours section header
        effects_label = QLabel(tr("RGBConfigurator", "Effect Colours:"))
        effects_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(effects_label, 11, 0, 1, 3)

        # Colour Scheme - moved to row 12
        layout.addWidget(QLabel(tr("RGBConfigurator", "Colour Scheme:")), 12, 0)
        color_type = HierarchicalDropdown(CUSTOM_LIGHT_COLOR_TYPES_HIERARCHY)
        color_type.valueChanged.connect(lambda idx, s=slot: self.on_color_type_changed(s, idx))
        layout.addWidget(color_type, 12, 1, 1, 2)

        # Sustain Mode - moved to row 13
        layout.addWidget(QLabel(tr("RGBConfigurator", "Sustain:")), 13, 0)
        sustain_mode = QComboBox()
        for sustain in CUSTOM_LIGHT_SUSTAIN_MODES:
            sustain_mode.addItem(sustain)
        sustain_mode.currentIndexChanged.connect(lambda idx, s=slot: self.on_sustain_mode_changed(s, idx))
        layout.addWidget(sustain_mode, 13, 1, 1, 2)

        # Buttons - moved to row 14
        buttons_layout = QHBoxLayout()
        
        save_button = QPushButton(tr("RGBConfigurator", "Save"))
        save_button.clicked.connect(lambda checked, s=slot: self.on_save_slot(s))
        buttons_layout.addWidget(save_button)
        
        load_button = QPushButton(tr("RGBConfigurator", "Load Settings from Keyboard"))
        load_button.clicked.connect(lambda checked, s=slot: self.on_load_from_keyboard(s))
        buttons_layout.addWidget(load_button)
        
        preset_combo = QComboBox()
        preset_combo.addItem("Load Preset...")
        for preset in CUSTOM_LIGHT_PRESETS:
            preset_combo.addItem(preset)
        preset_combo.currentIndexChanged.connect(lambda idx, s=slot: self.on_load_preset(s, idx))
        buttons_layout.addWidget(preset_combo)
        
        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        layout.addWidget(buttons_widget, 14, 0, 1, 3)

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

    def on_main_tab_changed(self, index):
        """Handle main tab change - load EEPROM for lowest slot in group"""
        if index >= len(self.groups):
            return
            
        group_name, start_idx, end_idx = self.groups[index]
        lowest_slot = start_idx
        
        print(f"Main tab changed to {group_name}, loading EEPROM for lowest slot {lowest_slot}")
        self.block_signals()
        self.load_slot_from_eeprom(lowest_slot)
        self.unblock_signals()
        
    def on_sub_tab_changed(self, index, start_slot):
        """Handle sub-tab switching within a group"""
        actual_slot = start_slot + index
        print(f"Sub-tab changed to {index}, actual slot {actual_slot}, loading EEPROM state")
        self.block_signals()
        self.load_slot_from_eeprom(actual_slot)
        self.unblock_signals()
        
    def get_current_slot_index(self):
        """Get the currently selected slot index across all groups"""
        # Get current main tab (group)
        main_tab_index = self.main_tab_widget.currentIndex()
        if main_tab_index >= len(self.groups):
            return 0
            
        group_name, start_idx, end_idx = self.groups[main_tab_index]
        
        # Get current sub-tab within the group
        sub_tab_widget = self.group_tab_widgets[group_name]
        sub_tab_index = sub_tab_widget.currentIndex()
        
        # Calculate actual slot index
        actual_slot = start_idx + sub_tab_index
        return min(actual_slot, 49)  # Ensure we don't exceed slot 49
            
    def get_currently_active_slot(self):
        """Get the slot number that is currently active - FIXED to use current slot"""
        try:
            if hasattr(self.device.keyboard, 'get_custom_animation_status'):
                status = self.device.keyboard.get_custom_animation_status()
                if status and len(status) > 1:
                    current_slot = status[1]  # Use status[1] (current slot) NOT status[2] (active slot)
                    # Validate slot is in valid range
                    if 0 <= current_slot < 50:
                        return current_slot
            # Fallback to slot 0 if anything fails
            return 0
        except Exception as e:
            print(f"Error getting current slot: {e}")
            return 0

    def on_load_from_keyboard(self, slot):
        """Load current RAM settings from CURRENT slot into this tab's GUI - FIXED VERSION"""
        try:
            self.block_signals()
            
            # Get the current slot (the one that's actually active)
            current_slot = self.get_currently_active_slot()
            print(f"Loading from current slot {current_slot} into tab {slot}")
            
            # Get the RAM data from the current slot
            config = self.device.keyboard.get_custom_slot_config(current_slot, from_eeprom=False)
            if config and len(config) >= 12:
                # Update the GUI widgets for the CURRENT TAB (slot), not the current slot
                self.update_slot_widgets(slot, config)
                print(f"Successfully loaded current slot {current_slot} settings into tab {slot}")
            else:
                print(f"Failed to get RAM config for current slot {current_slot}")
                
        except Exception as e:
            print(f"Error loading from current slot: {e}")
        finally:
            self.unblock_signals()
        
    def show_debug_popup(self, debug_info, title="Debug Info"):
        """Show debug information in a popup - ALWAYS appears"""
        try:
            from PyQt5.QtWidgets import QMessageBox, QTextEdit, QVBoxLayout, QDialog, QPushButton
            from PyQt5.QtCore import Qt
            
            # Create custom dialog for better text display
            dialog = QDialog()
            dialog.setWindowTitle(title)
            dialog.setModal(True)
            dialog.resize(800, 600)
            
            layout = QVBoxLayout()
            
            # Create text edit for scrollable debug info
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFont(QtGui.QFont("Courier", 9))  # Monospace font
            text_edit.setText('\n'.join(debug_info))
            text_edit.setLineWrapMode(QTextEdit.NoWrap)
            layout.addWidget(text_edit)
            
            # Add close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            # Fallback to simple message box if custom dialog fails
            try:
                from PyQt5.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setWindowTitle(title)
                msg.setText("DEBUG INFO (Custom dialog failed):\n\n" + '\n'.join(debug_info[:20]))  # First 20 lines
                msg.setDetailedText('\n'.join(debug_info))  # All debug info in details
                msg.exec_()
            except Exception as e2:
                print(f"CRITICAL: Both popup methods failed!")
                print(f"Original error: {e}")
                print(f"Fallback error: {e2}")
                print("Debug info:")
                for line in debug_info:
                    print(line)
                
    def load_slot_from_eeprom(self, slot):
        """Load slot settings from EEPROM"""
        try:
            config = self.device.keyboard.get_custom_slot_config(slot, from_eeprom=True)  # Explicit EEPROM
            if config and len(config) >= 12:
                self.update_slot_widgets(slot, config)
        except Exception as e:
            print(f"Error loading EEPROM state for slot {slot}: {e}")

    def load_slot_from_ram(self, slot):
        """Load slot settings from current RAM state"""
        try:
            config = self.device.keyboard.get_custom_slot_config(slot, from_eeprom=False)  # Explicit RAM
            if config and len(config) >= 12:
                self.update_slot_widgets(slot, config)
        except Exception as e:
            print(f"Error loading RAM state for slot {slot}: {e}")
    
    def update_slot_widgets(self, slot, config):
        """Update GUI widgets for a slot with given config"""
        if slot not in self.slot_widgets:
            print(f"Warning: slot {slot} not in slot_widgets dict")
            return
            
        widgets = self.slot_widgets[slot]
        widgets['live_effect'].setCurrentIndex(min(config[2], 171))
        widgets['live_style'].setCurrentIndex(min(config[0], 23))
        widgets['macro_effect'].setCurrentIndex(min(config[3], 171))
        widgets['macro_style'].setCurrentIndex(min(config[1], 34))
        widgets['background'].setCurrentIndex(min(config[5], 121))
        widgets['sustain_mode'].setCurrentIndex(min(config[6], len(CUSTOM_LIGHT_SUSTAIN_MODES) - 1))
        widgets['color_type'].setCurrentIndex(min(config[7], 64))
        widgets['background_brightness'].setValue(config[9] if len(config) > 9 else 30)
        widgets['live_speed'].setValue(config[10] if len(config) > 10 else 128)
        widgets['macro_speed'].setValue(config[11] if len(config) > 11 else 128)
            
    def update_from_keyboard(self):
        """Load current state and track active slot"""
        self.block_signals()
        
        try:
            # Check if randomize mode is active
            if hasattr(self.device.keyboard, 'get_custom_animation_status'):
                status = self.device.keyboard.get_custom_animation_status()
                randomize_active = status[6] if len(status) > 6 else 0
                active_slot = status[2] if len(status) > 2 else 0
                
                if randomize_active:
                    # In randomize mode - track randomize slot as active
                    self.current_randomize_slot = active_slot
                    self.current_active_slot = active_slot
                    print(f"Randomize mode active, active slot: {active_slot}")
                else:
                    # In normal mode - determine active slot
                    self.current_randomize_slot = None
                    self.current_active_slot = self.get_currently_active_slot()
                    print(f"Normal mode, active slot: {self.current_active_slot}")
                    
                # Always load EEPROM state for current tab (tab switching behavior)
                current_slot = self.get_current_slot_index()
                self.load_slot_from_eeprom(current_slot)
            else:
                self.current_randomize_slot = None
                self.current_active_slot = self.get_current_slot_index()
                
        except Exception as e:
            print(f"Error in update_from_keyboard: {e}")
            
        self.unblock_signals()

    def set_slot_defaults(self, slot):
        """Set default values for a slot"""
        if slot not in self.slot_widgets:
            return
            
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
        for slot in self.slot_widgets.keys():  # Only iterate through actually created slots
            widgets = self.slot_widgets[slot]
            for widget in widgets.values():
                widget.blockSignals(True)

    def unblock_signals(self):
        """Unblock signals for all widgets"""
        for slot in self.slot_widgets.keys():  # Only iterate through actually created slots
            widgets = self.slot_widgets[slot]
            for widget in widgets.values():
                widget.blockSignals(False)

     # Event handlers - ALL FIXED to use current slot
    def on_live_effect_changed(self, slot, index):
        """Handle live effect change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Live effect changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 2, index)
        else:
            print(f"Live effect changed: tab {slot} -> current slot {current_slot}, effect {index}")

    def on_live_style_changed(self, slot, index):
        """Handle live style change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Live style changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 0, index)
        else:
            print(f"Live style changed: tab {slot} -> current slot {current_slot}, style {index}")

    def on_live_speed_changed(self, slot, value):
        """Handle live animation speed change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Live speed changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 10, value)
        else:
            print(f"Live speed changed: tab {slot} -> current slot {current_slot}, speed {value}")

    def on_macro_effect_changed(self, slot, index):
        """Handle macro effect change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Macro effect changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 3, index)
        else:
            print(f"Macro effect changed: tab {slot} -> current slot {current_slot}, effect {index}")

    def on_macro_style_changed(self, slot, index):
        """Handle macro style change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Macro style changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 1, index)
        else:
            print(f"Macro style changed: tab {slot} -> current slot {current_slot}, style {index}")

    def on_macro_speed_changed(self, slot, value):
        """Handle macro animation speed change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Macro speed changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 11, value)
        else:
            print(f"Macro speed changed: tab {slot} -> current slot {current_slot}, speed {value}")

    def on_background_changed(self, slot, index):
        """Handle background change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Background changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 5, index)
        else:
            print(f"Background changed: tab {slot} -> current slot {current_slot}, index {index}")

    def on_background_brightness_changed(self, slot, value):
        """Handle background brightness change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Background brightness changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 9, value)
        else:
            print(f"Background brightness changed: tab {slot} -> current slot {current_slot}, brightness {value}%")

    def on_sustain_mode_changed(self, slot, index):
        """Handle sustain mode change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Sustain mode changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 6, index)
        else:
            print(f"Sustain mode changed: tab {slot} -> current slot {current_slot}, index {index}")

    def on_color_type_changed(self, slot, index):
        """Handle color type change - send to CURRENT slot"""
        current_slot = self.get_currently_active_slot()
        print(f"Color type changed on tab {slot}, sending to current slot {current_slot}")
        
        if hasattr(self.device.keyboard, 'set_custom_slot_parameter'):
            self.device.keyboard.set_custom_slot_parameter(current_slot, 7, index)
        else:
            print(f"Color type changed: tab {slot} -> current slot {current_slot}, index {index}")

    def on_save_slot(self, slot):
        """Save current GUI configuration to the tab slot's EEPROM"""
        try:
            # Get current GUI state for this tab
            widgets = self.slot_widgets[slot]
            
            # Collect all parameters from GUI
            live_pos = widgets['live_style'].currentIndex()
            macro_pos = widgets['macro_style'].currentIndex() 
            live_anim = widgets['live_effect'].currentIndex()
            macro_anim = widgets['macro_effect'].currentIndex()
            influence = 0  # You might need to add this widget
            background = widgets['background'].currentIndex()
            sustain = widgets['sustain_mode'].currentIndex()
            color_type = widgets['color_type'].currentIndex()
            enabled = 1  # You might need to add this widget
            bg_brightness = widgets['background_brightness'].value()
            live_speed = widgets['live_speed'].value()
            macro_speed = widgets['macro_speed'].value()
            
            # Send GUI state directly to the tab slot and save to EEPROM
            if hasattr(self.device.keyboard, 'set_custom_slot_all_parameters'):
                success = self.device.keyboard.set_custom_slot_all_parameters(
                    slot, live_pos, macro_pos, live_anim, macro_anim, influence,
                    background, sustain, color_type, enabled, bg_brightness, 
                    live_speed, macro_speed
                )
                if success:
                    print(f"Saved GUI state to tab slot {slot + 1} EEPROM")
                else:
                    print(f"Failed to save to tab slot {slot + 1}")
            else:
                print(f"Save slot {slot + 1} (keyboard method not implemented)")
                    
        except Exception as e:
            print(f"Error saving slot {slot + 1}: {e}")

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
        
        