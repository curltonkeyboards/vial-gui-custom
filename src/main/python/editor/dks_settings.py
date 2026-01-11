# SPDX-License-Identifier: GPL-2.0-or-later
"""
DKS (Dynamic Keystroke) Settings Editor

Allows configuration of multi-action analog keys with customizable actuation points.
Users configure DKS slots (DKS_00 - DKS_49) and then assign them to keys via the keymap editor.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QSlider, QGroupBox, QMessageBox, QFrame,
                              QSizePolicy, QCheckBox, QSpinBox, QScrollArea, QApplication, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPalette, QPixmap, QImage

from editor.basic_editor import BasicEditor
from protocol.dks_protocol import (ProtocolDKS, DKSSlot, DKS_BEHAVIOR_TAP,
                                   DKS_BEHAVIOR_PRESS, DKS_BEHAVIOR_RELEASE,
                                   DKS_NUM_SLOTS, DKS_ACTIONS_PER_STAGE)
from keycodes.keycodes import Keycode
from widgets.key_widget import KeyWidget
from tabbed_keycodes import TabbedKeycodes, FilteredTabbedKeycodes, keycode_filter_any, keycode_filter_masked
from tabbed_keycodes import KeyboardTab, MusicTab, GamingTab, MacroTab, LightingTab, LightingTab2, MIDITab, SimpleTab
from keycodes.keycodes import (KEYCODES_MACRO_BASE, KEYCODES_MACRO, KEYCODES_TAP_DANCE, KEYCODES_BACKLIGHT,
                               KEYCODES_RGBSAVE, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_COLOR,
                               KEYCODES_RGB_KC_CUSTOM2, KEYCODES_CLEAR, KEYCODES_GAMING,
                               KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_OSL)
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard
import widgets.resources  # Import Qt resources for switch crossection image


class FilteredTabbedKeycodesNoLayers(QTabWidget):
    """Custom FilteredTabbedKeycodes without LayerTab to avoid overlay issues"""

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self, parent=None, keycode_filter=keycode_filter_any):
        super().__init__(parent)

        self.keycode_filter = keycode_filter

        # Create tabs WITHOUT LayerTab
        self.tabs = [
            KeyboardTab(self),
            MusicTab(self),
            GamingTab(self, "Gaming", KEYCODES_GAMING),
            MacroTab(self, "Macro", KEYCODES_MACRO_BASE, KEYCODES_MACRO, KEYCODES_TAP_DANCE),
            # LayerTab intentionally EXCLUDED to prevent overlay issue
            LightingTab2(self, "Layers", KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_OSL),
            LightingTab(self, "Lighting", KEYCODES_BACKLIGHT, KEYCODES_RGBSAVE, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_COLOR, KEYCODES_RGB_KC_CUSTOM2),
            MIDITab(self),
            SimpleTab(self, " ", KEYCODES_CLEAR),
        ]

        for tab in self.tabs:
            tab.keycode_changed.connect(self.on_keycode_changed)

        self.recreate_keycode_buttons()
        KeycodeDisplay.notify_keymap_override(self)

    def on_keycode_changed(self, code):
        """Handle keycode changes from tabs"""
        if code == "Any":
            self.anykey.emit()
        else:
            self.keycode_changed.emit(Keycode.normalize(code))

    def recreate_keycode_buttons(self):
        """Recreate all keycode buttons based on filter"""
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
        """Update button labels when keymap overrides change"""
        for tab in self.tabs:
            tab.relabel_buttons()

    def set_keyboard(self, keyboard):
        """Set keyboard reference for tabs that need it"""
        for tab in self.tabs:
            if hasattr(tab, 'keyboard'):
                tab.keyboard = keyboard


class TabbedKeycodesNoLayers(QWidget):
    """Custom TabbedKeycodes without LayerTab for DKS settings"""

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.target = None
        self.is_tray = False

        self.layout = QVBoxLayout()

        # Use our custom FilteredTabbedKeycodes without layers
        self.all_keycodes = FilteredTabbedKeycodesNoLayers()
        self.basic_keycodes = FilteredTabbedKeycodesNoLayers(keycode_filter=keycode_filter_masked)
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.keycode_changed.connect(self.keycode_changed)
            opt.anykey.connect(self.anykey)
            self.layout.addWidget(opt)

        self.setLayout(self.layout)
        self.set_keycode_filter(keycode_filter_any)

    def set_keycode_filter(self, keycode_filter):
        """Show/hide filtered keycode widgets"""
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


class DKSKeyWidget(KeyWidget):
    """Custom KeyWidget that doesn't open tray - parent will handle keycode selection"""

    selected = pyqtSignal(object)  # Emits self when clicked

    def __init__(self):
        super().__init__()
        self.is_selected = False

    def mousePressEvent(self, ev):
        # Set active_key to the actual widget so KeyboardWidget draws the highlight
        if len(self.widgets) > 0:
            self.active_key = self.widgets[0]
            self.active_mask = False

        # Emit that we're selected (don't call parent which opens tray)
        self.selected.emit(self)
        self.update()  # Force repaint to show highlight
        ev.accept()

    def mouseReleaseEvent(self, ev):
        # Override to prevent any tray behavior
        ev.accept()

    def set_selected(self, selected):
        """Visual feedback for selection"""
        self.is_selected = selected
        if selected:
            # Set active_key to show native KeyboardWidget highlighting
            if len(self.widgets) > 0:
                self.active_key = self.widgets[0]
                self.active_mask = False
        else:
            # Clear active_key to remove highlighting
            self.active_key = None
        self.update()


class TravelBarWidget(QWidget):
    """Visual representation of key travel with actuation points"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMaximumHeight(140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.press_actuations = []      # List of (actuation_point, enabled) tuples
        self.release_actuations = []    # List of (actuation_point, enabled) tuples

    def set_actuations(self, press_points, release_points):
        """Set actuation points to display

        Args:
            press_points: List of (actuation, enabled) tuples for press actions
            release_points: List of (actuation, enabled) tuples for release actions
        """
        self.press_actuations = press_points
        self.release_actuations = release_points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get theme colors
        palette = QApplication.palette()
        window_color = palette.color(QPalette.Window)
        brightness = (window_color.red() * 0.299 +
                      window_color.green() * 0.587 +
                      window_color.blue() * 0.114)
        is_dark = brightness < 127

        # Calculate drawing area
        width = self.width()
        height = self.height()
        margin = 40
        bar_height = 30
        bar_y = (height - bar_height) // 2

        # Draw travel bar background - use theme colors
        bar_bg = palette.color(QPalette.AlternateBase)
        bar_border = palette.color(QPalette.Mid)
        text_color = palette.color(QPalette.Text)

        # Get theme accent colors for press/release
        press_color = palette.color(QPalette.Highlight)
        release_color = palette.color(QPalette.Link)

        painter.setBrush(bar_bg)
        painter.setPen(QPen(bar_border, 2))
        painter.drawRect(margin, bar_y, width - 2 * margin, bar_height)

        # Draw 0mm and 2.5mm labels
        painter.setPen(text_color)
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(margin - 10, bar_y + bar_height + 20, "0.0mm")
        painter.drawText(width - margin - 35, bar_y + bar_height + 20, "2.5mm")

        # Draw press actuation points (theme press color, above bar)
        for actuation, enabled in self.press_actuations:
            if not enabled:
                continue

            x = margin + int((actuation / 100.0) * (width - 2 * margin))

            # Draw line
            painter.setPen(QPen(press_color, 3))  # Theme press color
            painter.drawLine(x, bar_y - 20, x, bar_y)

            # Draw circle at top
            painter.setBrush(press_color)
            painter.drawEllipse(x - 5, bar_y - 28, 10, 10)

            # Draw actuation value
            mm_value = (actuation / 100.0) * 2.5
            painter.setPen(text_color)  # Use theme text color for readability
            font_small = QFont()
            font_small.setPointSize(8)
            painter.setFont(font_small)
            painter.drawText(x - 18, bar_y - 32, f"{mm_value:.2f}")
            painter.setFont(font)

        # Draw release actuation points (theme release color, below bar)
        for actuation, enabled in self.release_actuations:
            if not enabled:
                continue

            x = margin + int((actuation / 100.0) * (width - 2 * margin))

            # Draw line
            painter.setPen(QPen(release_color, 3))  # Theme release color
            painter.drawLine(x, bar_y + bar_height, x, bar_y + bar_height + 20)

            # Draw circle at bottom
            painter.setBrush(release_color)
            painter.drawEllipse(x - 5, bar_y + bar_height + 20, 10, 10)

            # Draw actuation value
            mm_value = (actuation / 100.0) * 2.5
            painter.setPen(text_color)  # Use theme text color for readability
            font_small = QFont()
            font_small.setPointSize(8)
            painter.setFont(font_small)
            painter.drawText(x - 18, bar_y + bar_height + 42, f"{mm_value:.2f}")
            painter.setFont(font)


class KeyswitchDiagramWidget(QWidget):
    """Visual diagram of a mechanical keyswitch cross-section using the actual image"""

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(450)
        self.setMinimumHeight(750)
        self.setMaximumWidth(450)
        self.setMaximumHeight(750)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Detect dark mode
        palette = QApplication.palette()
        window_color = palette.color(QPalette.Window)
        brightness = (window_color.red() * 0.299 +
                      window_color.green() * 0.587 +
                      window_color.blue() * 0.114)
        is_dark = brightness < 127

        # Load the switch crossection image from Qt resources
        pixmap = QPixmap(":/switchcrossection")

        if not pixmap.isNull():
            # Calculate scaling to fit widget while maintaining aspect ratio
            widget_width = self.width()
            widget_height = self.height()

            # Scale the pixmap to fit the widget
            scaled_pixmap = pixmap.scaled(
                widget_width, widget_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # Invert colors if in dark mode
            if is_dark:
                image = scaled_pixmap.toImage()
                image.invertPixels()
                scaled_pixmap = QPixmap.fromImage(image)

            # Center horizontally, align to top vertically (to match travel bar alignment)
            x = (widget_width - scaled_pixmap.width()) // 2 - 35  # Move 35 pixels left
            y = -30  # Move 30 pixels higher

            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            # Fallback: draw a simple placeholder if image fails to load
            painter.setPen(QColor(128, 128, 128))
            painter.drawText(self.rect(), Qt.AlignCenter, "Switch\nDiagram")


class VerticalTravelBarWidget(QWidget):
    """Vertical representation of key travel with actuation points"""

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(400)  # Wide enough for all labels without cutoff
        self.setMinimumHeight(250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.press_actuations = []      # List of (actuation_point, enabled) tuples
        self.release_actuations = []    # List of (actuation_point, enabled) tuples
        self.rapidfire_mode = False     # Flag to enable rapidfire visualization mode
        self.deadzone_top = 0           # Top deadzone value (0-20, representing 0-0.5mm)
        self.deadzone_bottom = 0        # Bottom deadzone value (0-20, representing 0-0.5mm)
        self.actuation_point = 60       # First activation point (0-100, representing 0-2.5mm)
        self.simple_labels = False      # If True, use "Actuation Point" for all press labels

    def set_actuations(self, press_points, release_points, rapidfire_mode=False,
                      deadzone_top=0, deadzone_bottom=0, actuation_point=60, simple_labels=False):
        """Set actuation points to display

        Args:
            press_points: List of (actuation, enabled) tuples for press actions
            release_points: List of (actuation, enabled) tuples for release actions
            rapidfire_mode: If True, show relative to actuation point with first activation line
            deadzone_top: Top deadzone value (0-20, 0-0.5mm from top, internally inverted)
            deadzone_bottom: Bottom deadzone value (0-20, 0-0.5mm from bottom)
            actuation_point: First activation point (0-100, 0-2.5mm)
            simple_labels: If True, use "Actuation Point" for all press labels (DKS mode)
        """
        self.press_actuations = press_points
        self.release_actuations = release_points
        self.rapidfire_mode = rapidfire_mode
        self.deadzone_top = deadzone_top
        self.deadzone_bottom = deadzone_bottom
        self.actuation_point = actuation_point
        self.simple_labels = simple_labels
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get theme colors
        palette = QApplication.palette()
        window_color = palette.color(QPalette.Window)
        brightness = (window_color.red() * 0.299 +
                      window_color.green() * 0.587 +
                      window_color.blue() * 0.114)
        is_dark = brightness < 127

        # Calculate drawing area
        width = self.width()
        height = self.height()
        margin_top = 40
        margin_bottom = 20
        bar_width = 30
        # Center the bar with room for labels on both sides
        bar_x = 120

        # Draw travel bar background (vertical) - use theme colors
        bar_bg = palette.color(QPalette.AlternateBase)
        bar_border = palette.color(QPalette.Mid)
        text_color = palette.color(QPalette.Text)

        # Get theme accent colors for press/release
        press_color = palette.color(QPalette.Highlight)
        release_color = palette.color(QPalette.Link)

        painter.setBrush(bar_bg)
        painter.setPen(QPen(bar_border, 2))
        painter.drawRect(bar_x, margin_top, bar_width, height - margin_top - margin_bottom)

        # Calculate bar height for vertical positioning
        bar_height = height - margin_top - margin_bottom

        # Draw deadzone fills (light grey) - shown in all modes
        deadzone_color = QColor(128, 128, 128, 80)  # Light grey with transparency

        # Top deadzone: from top to deadzone_bottom value
        # deadzone_bottom is 0-20 (0-0.5mm from bottom of range)
        # Convert to 0-100 range: deadzone_bottom * 5 = percentage from top
        if self.deadzone_bottom > 0:
            deadzone_bottom_percent = (self.deadzone_bottom / 20.0) * 12.5  # 0-20 maps to 0-12.5%
            deadzone_bottom_height = int(bar_height * deadzone_bottom_percent / 100.0)
            painter.fillRect(bar_x, margin_top, bar_width, deadzone_bottom_height, deadzone_color)

            # Draw "Top Deadzone" label
            font_small = QFont()
            font_small.setPointSize(7)
            painter.setFont(font_small)

            label_text = "Top Deadzone"
            label_x = bar_x + bar_width + 5
            label_y = margin_top + deadzone_bottom_height // 2 - 6

            # Theme background
            if is_dark:
                label_bg = palette.color(QPalette.Window).darker(110)
                label_border = palette.color(QPalette.Mid)
            else:
                label_bg = palette.color(QPalette.Base)
                label_border = palette.color(QPalette.Mid)

            fm = painter.fontMetrics()
            text_width = fm.width(label_text)
            text_height = fm.height()
            padding = 2

            painter.fillRect(label_x - padding, label_y - padding,
                           text_width + 2 * padding, text_height + 2 * padding, label_bg)
            painter.setPen(QPen(label_border, 1))
            painter.drawRect(label_x - padding, label_y - padding,
                           text_width + 2 * padding, text_height + 2 * padding)

            painter.setPen(text_color)  # Use theme text color for deadzone labels
            painter.drawText(label_x, label_y + text_height - 4, label_text)

        # Bottom deadzone: from bottom up to (max_travel - deadzone_top)
        # deadzone_top is 0-20 (0-0.5mm from top, internally inverted)
        # For visualization: fill from bottom upward
        if self.deadzone_top > 0:
            deadzone_top_percent = (self.deadzone_top / 20.0) * 12.5  # 0-20 maps to 0-12.5%
            deadzone_top_height = int(bar_height * deadzone_top_percent / 100.0)
            deadzone_top_y = margin_top + bar_height - deadzone_top_height
            painter.fillRect(bar_x, deadzone_top_y, bar_width, deadzone_top_height, deadzone_color)

            # Draw "Bottom Deadzone" label
            font_small = QFont()
            font_small.setPointSize(7)
            painter.setFont(font_small)

            label_text = "Bottom Deadzone"
            label_x = bar_x + bar_width + 5
            label_y = deadzone_top_y + deadzone_top_height // 2 - 6

            # Theme background
            if is_dark:
                label_bg = palette.color(QPalette.Window).darker(110)
                label_border = palette.color(QPalette.Mid)
            else:
                label_bg = palette.color(QPalette.Base)
                label_border = palette.color(QPalette.Mid)

            fm = painter.fontMetrics()
            text_width = fm.width(label_text)
            text_height = fm.height()
            padding = 2

            painter.fillRect(label_x - padding, label_y - padding,
                           text_width + 2 * padding, text_height + 2 * padding, label_bg)
            painter.setPen(QPen(label_border, 1))
            painter.drawRect(label_x - padding, label_y - padding,
                           text_width + 2 * padding, text_height + 2 * padding)

            painter.setPen(text_color)  # Use theme text color for deadzone labels
            painter.drawText(label_x, label_y + text_height - 4, label_text)

        if self.rapidfire_mode:

            # Draw actuation line for "First Activation" at actual actuation point
            actuation_y = margin_top + int((self.actuation_point / 100.0) * bar_height)
            painter.setPen(QPen(QColor(255, 200, 0), 2, Qt.DashLine))  # Yellow dashed line
            painter.drawLine(bar_x, actuation_y, bar_x + bar_width, actuation_y)

            # Draw "First Activation" label with button-like styling
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)

            # Calculate label background
            label_text = "First Activation"
            label_x = bar_x + bar_width + 15  # Closer to bar, consistent with other labels
            label_y = actuation_y - 10

            # Button-like styling with highlight color (active button)
            button_bg = palette.color(QPalette.Highlight)
            button_border = palette.color(QPalette.Highlight)

            # Measure text to size the box
            fm = painter.fontMetrics()
            text_width = fm.width(label_text)
            text_height = fm.height()
            padding = 6

            # Draw rounded button background
            painter.setPen(QPen(button_border, 1))
            painter.setBrush(button_bg)
            painter.drawRoundedRect(label_x - padding, label_y - padding,
                                   text_width + 2 * padding, text_height + 2 * padding, 6, 6)

            painter.setPen(palette.color(QPalette.HighlightedText))  # Use theme highlighted text for first activation label
            painter.drawText(label_x, actuation_y + 3, label_text)
        else:
            # Draw 0mm and 2.5mm labels (top and bottom) for normal mode
            painter.setPen(text_color)
            font = QFont()
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(bar_x + bar_width // 2 - 15, margin_top - 10, "0.0mm")
            painter.drawText(bar_x + bar_width // 2 - 15, height - margin_bottom + 15, "2.5mm")

        # Draw press and release actuation points
        if self.rapidfire_mode:
            # In rapidfire mode:
            # - Release is relative to first activation (actuation_y), going upward
            # - Press is relative to release, going downward
            bar_height = height - margin_top - margin_bottom
            actuation_y = margin_top + int((self.actuation_point / 100.0) * bar_height)

            # Draw release actuation points first (theme release color, above actuation line)
            release_y = actuation_y  # Default to actuation line
            for actuation, enabled in self.release_actuations:
                if not enabled:
                    continue

                # Release is upward from actuation point
                # actuation is sensitivity in 0-100 (representing 0-2.5mm distance)
                y = actuation_y - int((actuation / 100.0) * bar_height)
                release_y = y

                # Draw line to right
                painter.setPen(QPen(release_color, 3))  # Theme release color
                painter.drawLine(bar_x + bar_width, y, bar_x + bar_width + 20, y)

                # Draw circle on right
                painter.setBrush(release_color)
                painter.drawEllipse(bar_x + bar_width + 18, y - 5, 10, 10)

                # Draw "Release Threshold" identifier and mm value with button-like styling
                mm_value = (actuation / 100.0) * 2.5

                # Use bigger font for button-like appearance
                font_label = QFont()
                font_label.setPointSize(9)
                font_label.setBold(True)
                painter.setFont(font_label)

                fm = painter.fontMetrics()
                padding = 6  # Bigger padding for button-like appearance
                label_x = bar_x + bar_width + 15  # Closer to bar

                # Button-like background
                button_bg = palette.color(QPalette.Button)
                button_border = palette.color(QPalette.Light)

                # Draw "Release Threshold" identifier (button-like)
                id_text = "Release Threshold"
                id_width = fm.width(id_text)
                id_height = fm.height()
                id_y = y - id_height - 10

                # Draw rounded button background
                painter.setPen(QPen(button_border, 1))
                painter.setBrush(button_bg)
                painter.drawRoundedRect(label_x - padding, id_y - padding,
                                       id_width + 2 * padding, id_height + 2 * padding, 6, 6)
                painter.setPen(palette.color(QPalette.ButtonText))  # Use button text color
                painter.drawText(label_x, id_y + id_height - 4, id_text)

                # Draw mm value below identifier (smaller, secondary label)
                font_mm = QFont()
                font_mm.setPointSize(8)
                painter.setFont(font_mm)
                fm = painter.fontMetrics()

                mm_text = f"{mm_value:.2f}mm"
                mm_width = fm.width(mm_text)
                mm_height = fm.height()
                mm_y = y + 6

                painter.setPen(QPen(button_border, 1))
                painter.setBrush(palette.color(QPalette.AlternateBase))
                painter.drawRoundedRect(label_x - 4, mm_y - mm_height,
                                       mm_width + 8, mm_height + 4, 4, 4)
                painter.setPen(text_color)  # Use theme text color for readability
                painter.drawText(label_x, mm_y, mm_text)

            # Draw press actuation points (theme press color, below release line)
            for actuation, enabled in self.press_actuations:
                if not enabled:
                    continue

                # Press is downward from release point
                # actuation is sensitivity in 0-100 (representing 0-2.5mm distance)
                y = release_y + int((actuation / 100.0) * bar_height)

                # Draw line to left
                painter.setPen(QPen(press_color, 3))  # Theme press color
                painter.drawLine(bar_x - 20, y, bar_x, y)

                # Draw circle on left
                painter.setBrush(press_color)
                painter.drawEllipse(bar_x - 28, y - 5, 10, 10)

                # Draw "Press Threshold" identifier and mm value with button-like styling
                mm_value = (actuation / 100.0) * 2.5

                # Use bigger font for button-like appearance
                font_label = QFont()
                font_label.setPointSize(9)
                font_label.setBold(True)
                painter.setFont(font_label)

                fm = painter.fontMetrics()
                padding = 6  # Bigger padding for button-like appearance

                # Button-like background
                button_bg = palette.color(QPalette.Button)
                button_border = palette.color(QPalette.Light)

                # Draw "Press Threshold" identifier (button-like)
                id_text = "Press Threshold"
                id_width = fm.width(id_text)
                id_height = fm.height()
                label_x = bar_x - id_width - 15
                id_y = y - id_height - 10

                # Draw rounded button background
                painter.setPen(QPen(button_border, 1))
                painter.setBrush(button_bg)
                painter.drawRoundedRect(label_x - padding, id_y - padding,
                                       id_width + 2 * padding, id_height + 2 * padding, 6, 6)
                painter.setPen(palette.color(QPalette.ButtonText))  # Use button text color
                painter.drawText(label_x, id_y + id_height - 4, id_text)

                # Draw mm value below identifier (smaller, secondary label)
                font_mm = QFont()
                font_mm.setPointSize(8)
                painter.setFont(font_mm)
                fm = painter.fontMetrics()

                mm_text = f"{mm_value:.2f}mm"
                mm_width = fm.width(mm_text)
                mm_height = fm.height()
                mm_x = bar_x - mm_width - 12
                mm_y = y + 6

                painter.setPen(QPen(button_border, 1))
                painter.setBrush(palette.color(QPalette.AlternateBase))
                painter.drawRoundedRect(mm_x - 4, mm_y - mm_height,
                                       mm_width + 8, mm_height + 4, 4, 4)
                painter.setPen(text_color)  # Use theme text color for readability
                painter.drawText(mm_x, mm_y, mm_text)
        else:
            # Normal mode: draw from top to bottom
            font = QFont()
            font.setPointSize(9)

            # Draw press actuation points (theme press color, left side)
            # These represent Normal and MIDI actuation points (or "Actuation Point" in DKS simple mode)
            if self.simple_labels:
                actuation_labels = ["Actuation Point", "Actuation Point"]
            else:
                actuation_labels = ["Normal Actuation", "MIDI Actuation"]
            for idx, (actuation, enabled) in enumerate(self.press_actuations):
                if not enabled:
                    continue

                y = margin_top + int((actuation / 100.0) * (height - margin_top - margin_bottom))

                # Draw line to left
                painter.setPen(QPen(press_color, 3))  # Theme press color
                painter.drawLine(bar_x - 20, y, bar_x, y)

                # Draw circle on left
                painter.setBrush(press_color)
                painter.drawEllipse(bar_x - 28, y - 5, 10, 10)

                # Draw identifier and mm value with button-like styling
                mm_value = (actuation / 100.0) * 2.5

                # Use bigger font for button-like appearance
                font_label = QFont()
                font_label.setPointSize(9)
                font_label.setBold(True)
                painter.setFont(font_label)

                fm = painter.fontMetrics()
                padding = 6  # Bigger padding for button-like appearance

                # Draw identifier label (button-like)
                id_text = actuation_labels[idx] if idx < len(actuation_labels) else "Actuation"
                id_width = fm.width(id_text)
                id_height = fm.height()
                label_x = bar_x - id_width - 15
                id_y = y - id_height - 10

                # Button-like background with highlight color
                button_bg = palette.color(QPalette.Button)
                button_border = palette.color(QPalette.Light)

                # Draw rounded button background
                painter.setPen(QPen(button_border, 1))
                painter.setBrush(button_bg)
                painter.drawRoundedRect(label_x - padding, id_y - padding,
                                       id_width + 2 * padding, id_height + 2 * padding, 6, 6)
                painter.setPen(palette.color(QPalette.ButtonText))  # Use button text color
                painter.drawText(label_x, id_y + id_height - 4, id_text)

                # Draw mm value below identifier (smaller, secondary label)
                font_mm = QFont()
                font_mm.setPointSize(8)
                painter.setFont(font_mm)
                fm = painter.fontMetrics()

                mm_text = f"{mm_value:.2f}mm"
                mm_width = fm.width(mm_text)
                mm_height = fm.height()
                mm_x = bar_x - mm_width - 12
                mm_y = y + 6

                painter.setPen(QPen(button_border, 1))
                painter.setBrush(palette.color(QPalette.AlternateBase))
                painter.drawRoundedRect(mm_x - 4, mm_y - mm_height,
                                       mm_width + 8, mm_height + 4, 4, 4)
                painter.setPen(text_color)  # Use theme text color for readability
                painter.drawText(mm_x, mm_y, mm_text)

            # Draw release actuation points (theme release color, right side)
            for actuation, enabled in self.release_actuations:
                if not enabled:
                    continue

                y = margin_top + int((actuation / 100.0) * (height - margin_top - margin_bottom))

                # Draw line to right
                painter.setPen(QPen(release_color, 3))  # Theme release color
                painter.drawLine(bar_x + bar_width, y, bar_x + bar_width + 20, y)

                # Draw circle on right
                painter.setBrush(release_color)
                painter.drawEllipse(bar_x + bar_width + 18, y - 5, 10, 10)

                # Draw identifier and mm value with button-like styling
                mm_value = (actuation / 100.0) * 2.5

                # Use bigger font for button-like appearance
                font_label = QFont()
                font_label.setPointSize(9)
                font_label.setBold(True)
                painter.setFont(font_label)

                fm = painter.fontMetrics()
                padding = 6  # Bigger padding for button-like appearance
                label_x = bar_x + bar_width + 15  # Closer to bar

                # Button-like background
                button_bg = palette.color(QPalette.Button)
                button_border = palette.color(QPalette.Light)

                # Draw identifier label (button-like)
                id_text = "Release Point"
                id_width = fm.width(id_text)
                id_height = fm.height()
                id_y = y - id_height - 10

                # Draw rounded button background
                painter.setPen(QPen(button_border, 1))
                painter.setBrush(button_bg)
                painter.drawRoundedRect(label_x - padding, id_y - padding,
                                       id_width + 2 * padding, id_height + 2 * padding, 6, 6)
                painter.setPen(palette.color(QPalette.ButtonText))  # Use button text color
                painter.drawText(label_x, id_y + id_height - 4, id_text)

                # Draw mm value below identifier (smaller, secondary label)
                font_mm = QFont()
                font_mm.setPointSize(8)
                painter.setFont(font_mm)
                fm = painter.fontMetrics()

                mm_text = f"{mm_value:.2f}mm"
                mm_width = fm.width(mm_text)
                mm_height = fm.height()
                mm_y = y + 6

                painter.setPen(QPen(button_border, 1))
                painter.setBrush(palette.color(QPalette.AlternateBase))
                painter.drawRoundedRect(label_x - 4, mm_y - mm_height,
                                       mm_width + 8, mm_height + 4, 4, 4)
                painter.setPen(text_color)  # Use theme text color for readability
                painter.drawText(label_x, mm_y, mm_text)


class DKSActionEditor(QWidget):
    """Editor for a single DKS action with DKSKeyWidget integration"""

    changed = pyqtSignal()
    key_selected = pyqtSignal(object)  # Emits the DKSKeyWidget when clicked

    def __init__(self, action_num, is_press=True):
        super().__init__()
        self.action_num = action_num
        self.is_press = is_press

        # Main horizontal layout
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        if is_press:
            # Press layout: Stretch | Dropdown | Key | Slider (left to right)
            # Add stretch before dropdown to push content together
            layout.addStretch()

            # Behavior selector on the outside (left)
            self.behavior_combo = QComboBox()
            self.behavior_combo.addItems(["Tap", "Press", "Release"])
            self.behavior_combo.setCurrentIndex(DKS_BEHAVIOR_TAP)
            self.behavior_combo.currentIndexChanged.connect(self._on_changed)
            self.behavior_combo.setFixedSize(70, 25)
            layout.addWidget(self.behavior_combo)

            # Key widget in middle
            key_container = QVBoxLayout()
            key_container.setSpacing(2)

            action_label = QLabel(f"Press {action_num + 1}")
            action_label.setAlignment(Qt.AlignCenter)
            action_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 10px;
                    color: palette(highlighted-text);
                    background-color: palette(highlight);
                    border-radius: 4px;
                    padding: 2px 6px;
                }
            """)
            key_container.addWidget(action_label)

            self.key_widget = DKSKeyWidget()
            self.key_widget.setFixedSize(60, 50)
            self.key_widget.changed.connect(self._on_changed)
            self.key_widget.selected.connect(self._on_key_selected)
            key_container.addWidget(self.key_widget, alignment=Qt.AlignCenter)

            layout.addLayout(key_container)

            # Slider on the inside (right) - horizontal
            slider_container = QVBoxLayout()
            slider_container.setSpacing(2)

            self.actuation_label = QLabel("1.50mm")
            self.actuation_label.setAlignment(Qt.AlignCenter)
            self.actuation_label.setStyleSheet("font-size: 9px;")
            slider_container.addWidget(self.actuation_label)

            self.actuation_slider = QSlider(Qt.Horizontal)
            self.actuation_slider.setMinimum(0)
            self.actuation_slider.setMaximum(100)
            self.actuation_slider.setValue(60)
            self.actuation_slider.setFixedWidth(80)
            self.actuation_slider.valueChanged.connect(self._update_actuation_label)
            self.actuation_slider.valueChanged.connect(self._on_changed)
            slider_container.addWidget(self.actuation_slider)

            layout.addLayout(slider_container)
        else:
            # Release layout: Slider | Key | Dropdown (left to right)
            # Slider on the inside (left) - horizontal
            slider_container = QVBoxLayout()
            slider_container.setSpacing(2)

            self.actuation_label = QLabel("1.50mm")
            self.actuation_label.setAlignment(Qt.AlignCenter)
            self.actuation_label.setStyleSheet("font-size: 9px;")
            slider_container.addWidget(self.actuation_label)

            self.actuation_slider = QSlider(Qt.Horizontal)
            self.actuation_slider.setMinimum(0)
            self.actuation_slider.setMaximum(100)
            self.actuation_slider.setValue(60)
            self.actuation_slider.setFixedWidth(80)
            self.actuation_slider.valueChanged.connect(self._update_actuation_label)
            self.actuation_slider.valueChanged.connect(self._on_changed)
            slider_container.addWidget(self.actuation_slider)

            layout.addLayout(slider_container)

            # Key widget in middle
            key_container = QVBoxLayout()
            key_container.setSpacing(2)

            action_label = QLabel(f"Release {action_num + 1}")
            action_label.setAlignment(Qt.AlignCenter)
            action_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 10px;
                    color: palette(highlighted-text);
                    background-color: palette(highlight);
                    border-radius: 4px;
                    padding: 2px 6px;
                }
            """)
            key_container.addWidget(action_label)

            self.key_widget = DKSKeyWidget()
            self.key_widget.setFixedSize(60, 50)
            self.key_widget.changed.connect(self._on_changed)
            self.key_widget.selected.connect(self._on_key_selected)
            key_container.addWidget(self.key_widget, alignment=Qt.AlignCenter)

            layout.addLayout(key_container)

            # Behavior selector on the outside (right)
            self.behavior_combo = QComboBox()
            self.behavior_combo.addItems(["Tap", "Press", "Release"])
            self.behavior_combo.setCurrentIndex(DKS_BEHAVIOR_TAP)
            self.behavior_combo.currentIndexChanged.connect(self._on_changed)
            self.behavior_combo.setFixedSize(70, 25)
            layout.addWidget(self.behavior_combo)

            # Add stretch after dropdown to push content together
            layout.addStretch()

        # Store label reference for color styling
        self.label = action_label

        self.setLayout(layout)
        self._update_actuation_label()

        # Style the widget with theme colors
        self.setStyleSheet("""
            DKSActionEditor {
                border: 1px solid palette(mid);
                border-radius: 5px;
                background: palette(base);
            }
        """)

    def _update_actuation_label(self):
        """Update actuation label with mm value"""
        value = self.actuation_slider.value()
        mm = (value / 100.0) * 2.5
        self.actuation_label.setText(f"{mm:.2f}mm")

    def _on_changed(self):
        """Emit changed signal"""
        self.changed.emit()

    def _on_key_selected(self, widget):
        """Forward key selection signal to parent"""
        self.key_selected.emit(widget)

    def set_action(self, keycode, actuation, behavior):
        """Set action values"""
        # Convert keycode integer to string qmk_id
        if isinstance(keycode, int):
            if keycode == 0:
                keycode_str = "KC_NO"
            else:
                keycode_str = Keycode.serialize(keycode)
        else:
            keycode_str = keycode

        self.key_widget.set_keycode(keycode_str)
        self.actuation_slider.setValue(actuation)
        self.behavior_combo.setCurrentIndex(behavior)

    def get_action(self):
        """Get action values as (keycode, actuation, behavior) tuple"""
        keycode_str = self.key_widget.keycode

        # Convert keycode string to integer
        if keycode_str == "KC_NO" or keycode_str == "":
            keycode = 0
        else:
            keycode = Keycode.deserialize(keycode_str)

        actuation = self.actuation_slider.value()
        behavior = self.behavior_combo.currentIndex()
        return (keycode, actuation, behavior)


class DKSVisualWidget(QWidget):
    """Visual layout widget for DKS actions - horizontal layout"""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(1100, 300)  # Wide enough for labels
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Will be set by parent
        self.press_editors = []
        self.release_editors = []

        # Main horizontal layout
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(20)
        self.setLayout(self.main_layout)

    def set_editors(self, press_editors, release_editors):
        """Position the action editors in horizontal layout"""
        self.press_editors = press_editors
        self.release_editors = release_editors

        # Clear existing layout
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Left section: Press actions (vertical stack)
        press_container = QWidget()
        press_layout = QVBoxLayout()
        press_layout.setContentsMargins(0, 0, 0, 0)
        press_layout.setSpacing(10)

        press_label = QLabel("Key Press (Downstroke)")
        press_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 12px;
                color: palette(highlighted-text);
                background-color: palette(highlight);
                border-radius: 6px;
                padding: 4px 10px;
            }
        """)
        press_label.setAlignment(Qt.AlignCenter)
        press_layout.addWidget(press_label)

        for editor in self.press_editors:
            editor.setParent(press_container)
            press_layout.addWidget(editor)
            # Label styling is now done in DKSActionEditor.__init__

        press_layout.addStretch()
        press_container.setLayout(press_layout)
        self.main_layout.addWidget(press_container)

        # Middle: Keyswitch diagram + Vertical travel bar
        middle_container = QWidget()
        middle_container.setMinimumWidth(800)  # Wide enough for all labels without cutoff
        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)  # No spacing between diagram and bar

        # Add keyswitch diagram
        self.keyswitch_diagram = KeyswitchDiagramWidget()
        middle_layout.addWidget(self.keyswitch_diagram)

        # Add vertical travel bar with negative left margin to move it 130px closer to diagram
        travel_bar_container = QWidget()
        travel_bar_layout = QHBoxLayout()
        travel_bar_layout.setContentsMargins(-130, 0, 0, 0)  # Move 130px closer to diagram
        travel_bar_layout.setSpacing(0)
        travel_bar_layout.addWidget(self.create_vertical_travel_bar())
        travel_bar_container.setLayout(travel_bar_layout)
        middle_layout.addWidget(travel_bar_container)

        middle_container.setLayout(middle_layout)
        self.main_layout.addWidget(middle_container)

        # Right section: Release actions (vertical stack)
        release_container = QWidget()
        release_layout = QVBoxLayout()
        release_layout.setContentsMargins(0, 0, 0, 0)
        release_layout.setSpacing(10)

        release_label = QLabel("Key Release (Upstroke)")
        release_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 12px;
                color: palette(highlighted-text);
                background-color: palette(highlight);
                border-radius: 6px;
                padding: 4px 10px;
            }
        """)
        release_label.setAlignment(Qt.AlignCenter)
        release_layout.addWidget(release_label)

        for editor in self.release_editors:
            editor.setParent(release_container)
            release_layout.addWidget(editor)
            # Label styling is now done in DKSActionEditor.__init__

        release_layout.addStretch()
        release_container.setLayout(release_layout)
        self.main_layout.addWidget(release_container)

    def create_vertical_travel_bar(self):
        """Create a vertical travel bar indicator"""
        self.vertical_travel_bar = VerticalTravelBarWidget()
        return self.vertical_travel_bar

    def update_travel_bar(self, press_points, release_points):
        """Update the vertical travel bar with actuation points"""
        if hasattr(self, 'vertical_travel_bar'):
            self.vertical_travel_bar.set_actuations(press_points, release_points, simple_labels=True)


class DKSEntryUI(QWidget):
    """UI for a single DKS slot"""

    changed = pyqtSignal()

    def __init__(self, slot_idx):
        super().__init__()
        self.slot_idx = slot_idx
        self.dks_protocol = None
        self.selected_key_widget = None  # Track which key widget is selected

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)


        # Visual action editor (includes travel bar)
        visual_group = QGroupBox("Action Configuration")
        visual_group.setStyleSheet("""
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
                padding: 0 5px 0 5px;
            }
        """)
        visual_layout = QHBoxLayout()
        visual_layout.setContentsMargins(0, 0, 0, 0)

        self.visual_widget = DKSVisualWidget()

        # Create action editors
        self.press_editors = []
        self.release_editors = []

        for i in range(DKS_ACTIONS_PER_STAGE):
            press_editor = DKSActionEditor(i, is_press=True)
            press_editor.changed.connect(self._on_action_changed)
            press_editor.key_selected.connect(self._on_key_selected)
            self.press_editors.append(press_editor)

            release_editor = DKSActionEditor(i, is_press=False)
            release_editor.changed.connect(self._on_action_changed)
            release_editor.key_selected.connect(self._on_key_selected)
            self.release_editors.append(release_editor)

        # Set editors in visual widget
        self.visual_widget.set_editors(self.press_editors, self.release_editors)

        # Center the visual widget with stretches on both sides
        visual_layout.addStretch()
        visual_layout.addWidget(self.visual_widget)
        visual_layout.addStretch()
        visual_group.setLayout(visual_layout)
        main_layout.addWidget(visual_group)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.reset_btn = QPushButton("Reset Slot")
        self.reset_btn.setFixedWidth(150)
        self.reset_btn.clicked.connect(self._on_reset)
        bottom_layout.addWidget(self.reset_btn)

        self.save_eeprom_btn = QPushButton("Save to EEPROM")
        self.save_eeprom_btn.setFixedWidth(150)
        self.save_eeprom_btn.clicked.connect(self._on_save_eeprom)
        bottom_layout.addWidget(self.save_eeprom_btn)

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

    def set_dks_protocol(self, protocol):
        """Set the DKS protocol handler"""
        self.dks_protocol = protocol

    def _on_load(self):
        """Load slot from keyboard"""
        if not self.dks_protocol:
            return

        slot = self.dks_protocol.get_slot(self.slot_idx)
        if not slot:
            # Silently fail if firmware doesn't support DKS - don't show error popup
            # This allows the tab to show even if firmware doesn't have DKS enabled
            return

        self.load_from_slot(slot)

    def load_from_slot(self, slot):
        """Load UI from slot data"""
        # Press actions
        for i, editor in enumerate(self.press_editors):
            action = slot.press_actions[i]
            editor.set_action(action.keycode, action.actuation, action.behavior)

        # Release actions
        for i, editor in enumerate(self.release_editors):
            action = slot.release_actions[i]
            editor.set_action(action.keycode, action.actuation, action.behavior)

        self._update_travel_bar()

    def save_to_slot(self):
        """Save UI to slot (returns tuple of press and release actions)"""
        press_actions = []
        for editor in self.press_editors:
            press_actions.append(editor.get_action())

        release_actions = []
        for editor in self.release_editors:
            release_actions.append(editor.get_action())

        return (press_actions, release_actions)

    def _on_action_changed(self):
        """Handle action change"""
        self._update_travel_bar()
        self._send_to_keyboard()
        self.changed.emit()

    def _on_key_selected(self, widget):
        """Handle key widget selection - update visual feedback"""
        # Clear previous selection
        if self.selected_key_widget:
            self.selected_key_widget.set_selected(False)

        # Set new selection
        self.selected_key_widget = widget
        widget.set_selected(True)

    def on_keycode_selected(self, keycode):
        """Called when a keycode is selected from TabbedKeycodes"""
        if self.selected_key_widget:
            self.selected_key_widget.on_keycode_changed(keycode)

    def _send_to_keyboard(self):
        """Send current configuration to keyboard"""
        if not self.dks_protocol:
            return

        # Send press actions
        for i, editor in enumerate(self.press_editors):
            keycode, actuation, behavior = editor.get_action()
            self.dks_protocol.set_action(
                self.slot_idx, True, i, keycode, actuation, behavior
            )

        # Send release actions
        for i, editor in enumerate(self.release_editors):
            keycode, actuation, behavior = editor.get_action()
            self.dks_protocol.set_action(
                self.slot_idx, False, i, keycode, actuation, behavior
            )

    def _update_travel_bar(self):
        """Update travel bar visualization"""
        press_points = []
        for editor in self.press_editors:
            keycode, actuation, behavior = editor.get_action()
            enabled = (keycode != 0)
            press_points.append((actuation, enabled))

        release_points = []
        for editor in self.release_editors:
            keycode, actuation, behavior = editor.get_action()
            enabled = (keycode != 0)
            release_points.append((actuation, enabled))

        self.visual_widget.update_travel_bar(press_points, release_points)

    def _on_reset(self):
        """Reset slot to defaults"""
        if not self.dks_protocol:
            return

        reply = QMessageBox.question(
            self, "Confirm Reset",
            f"Reset DKS_{self.slot_idx:02d} to default configuration?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.dks_protocol.reset_slot(self.slot_idx):
                QMessageBox.information(self, "Success", "Slot reset to defaults")
                self._on_load()
            else:
                QMessageBox.warning(self, "Error", "Failed to reset slot")

    def _on_save_eeprom(self):
        """Save to EEPROM"""
        if not self.dks_protocol:
            return

        if self.dks_protocol.save_to_eeprom():
            QMessageBox.information(self, "Success", "DKS configuration saved to EEPROM")
        else:
            QMessageBox.warning(self, "Error", "Failed to save to EEPROM")


class DKSSettingsTab(BasicEditor):
    """Main DKS settings editor tab with filtered slots"""

    def __init__(self, layout_editor):
        super().__init__()
        self.layout_editor = layout_editor
        self.dks_protocol = None
        self.dks_entries = []
        self.loaded_slots = set()  # Track which slots have been loaded

        # Create tab widget for DKS slots
        self.tabs = QTabWidget()

        # Create all DKS entries (pre-create like TapDance does)
        for i in range(DKS_NUM_SLOTS):
            entry = DKSEntryUI(i)
            entry.changed.connect(self.on_entry_changed)
            self.dks_entries.append(entry)

        # Add tabs to widget
        for i, entry in enumerate(self.dks_entries):
            scroll = QScrollArea()
            scroll.setWidget(entry)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.tabs.addTab(scroll, f"DKS{i}")

        self.addWidget(self.tabs)

        # Connect tab changes for lazy loading
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Bottom action buttons
        button_layout = QHBoxLayout()

        self.reset_all_btn = QPushButton("Reset All Slots")
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        button_layout.addWidget(self.reset_all_btn)

        button_layout.addStretch()

        self.load_eeprom_btn = QPushButton("Load All from EEPROM")
        self.load_eeprom_btn.clicked.connect(self._on_load_eeprom)
        button_layout.addWidget(self.load_eeprom_btn)

        self.addLayout(button_layout)

        # Add TabbedKeycodes at the bottom like in GamingConfigurator
        # Use custom version without LayerTab to prevent overlay issue
        self.tabbed_keycodes = TabbedKeycodesNoLayers()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_selected)
        self.addWidget(self.tabbed_keycodes)

    def on_entry_changed(self):
        """Handle entry change (can be used for modified indicators)"""
        # Future: Add modified state tracking like TapDance
        pass

    def on_keycode_selected(self, keycode):
        """Called when a keycode is selected from TabbedKeycodes"""
        current_idx = self.tabs.currentIndex()
        if current_idx >= 0 and current_idx < len(self.dks_entries):
            self.dks_entries[current_idx].on_keycode_selected(keycode)

    def _on_tab_changed(self, index):
        """Handle tab change - lazy load slot data"""
        if index >= 0 and index < len(self.dks_entries):
            # Lazy load: Only load slot data when first viewing the tab
            if self.dks_protocol and index not in self.loaded_slots:
                self.dks_entries[index]._on_load()
                self.loaded_slots.add(index)

    def _on_reset_all(self):
        """Reset all slots to defaults"""
        if not self.dks_protocol:
            return

        reply = QMessageBox.question(
            None, "Confirm Reset",
            "Reset ALL DKS slots to default configuration? This cannot be undone!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.dks_protocol.reset_all_slots():
                QMessageBox.information(None, "Success", "All slots reset to defaults")
                # Reload current tab
                current_idx = self.tabs.currentIndex()
                self.dks_entries[current_idx]._on_load()
            else:
                QMessageBox.warning(None, "Error", "Failed to reset slots")

    def _on_load_eeprom(self):
        """Load all slots from EEPROM"""
        if not self.dks_protocol:
            return

        if self.dks_protocol.load_from_eeprom():
            QMessageBox.information(None, "Success", "DKS configurations loaded from EEPROM")
            # Reload current tab
            current_idx = self.tabs.currentIndex()
            self.dks_entries[current_idx]._on_load()
        else:
            QMessageBox.warning(None, "Error", "Failed to load from EEPROM")

    def rebuild(self, device):
        """Rebuild the editor when device changes"""
        super().rebuild(device)

        if not self.valid():
            self.dks_protocol = None
            return

        # Create DKS protocol handler
        self.dks_protocol = ProtocolDKS(device)

        # Set protocol for all entries
        for entry in self.dks_entries:
            entry.set_dks_protocol(self.dks_protocol)

        # Clear loaded slots cache on device change
        self.loaded_slots.clear()

    def valid(self):
        """Check if this tab is valid for the current device"""
        return isinstance(self.device, VialKeyboard)
