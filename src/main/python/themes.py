# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor

themes = [
    ("Light", {
        QPalette.Window: "#ffefebe7",
        QPalette.WindowText: "#ff000000",
        QPalette.Base: "#ffffffff",
        QPalette.AlternateBase: "#fff7f5f3",
        QPalette.ToolTipBase: "#ffffffdc",
        QPalette.ToolTipText: "#ff000000",
        QPalette.Text: "#ff000000",
        QPalette.Button: "#ffefebe7",
        QPalette.ButtonText: "#ff000000",
        QPalette.BrightText: "#ffffffff",
        QPalette.Link: "#ff0000ff",
        QPalette.Highlight: "#ff308cc6",
        QPalette.HighlightedText: "#ffffffff",
        (QPalette.Active, QPalette.Button): "#ffefebe7",
        (QPalette.Disabled, QPalette.ButtonText): "#ffbebebe",
        (QPalette.Disabled, QPalette.WindowText): "#ffbebebe",
        (QPalette.Disabled, QPalette.Text): "#ffbebebe",
        (QPalette.Disabled, QPalette.Light): "#ffffffff",
    }),
    ("Dark", {
        QPalette.Window: "#353535",
        QPalette.WindowText: "#ffffff",
        QPalette.Base: "#232323",
        QPalette.AlternateBase: "#353535",
        QPalette.ToolTipBase: "#191919",
        QPalette.ToolTipText: "#ffffff",
        QPalette.Text: "#ffffff",
        QPalette.Button: "#353535",
        QPalette.ButtonText: "#ffffff",
        QPalette.BrightText: "#ff0000",
        QPalette.Link: "#f7a948",
        QPalette.Highlight: "#bababa",
        QPalette.HighlightedText: "#232323",
        (QPalette.Active, QPalette.Button): "#353535",
        (QPalette.Disabled, QPalette.ButtonText): "#808080",
        (QPalette.Disabled, QPalette.WindowText): "#808080",
        (QPalette.Disabled, QPalette.Text): "#808080",
        (QPalette.Disabled, QPalette.Light): "#353535",
    }),
    ("Arc", {
        QPalette.Window: "#333333",
        QPalette.WindowText: "#cc5200",
        QPalette.Base: "#61574a",
        QPalette.AlternateBase: "#baaa93",
        QPalette.ToolTipBase: "#3e2308",
        QPalette.ToolTipText: "#cc5200",
        QPalette.Text: "#cc5200",
        QPalette.Button: "#baaa93",
        QPalette.ButtonText: "#cc5200",
        QPalette.BrightText: "#cc5200",
        QPalette.Link: "#baaa93",
        QPalette.Highlight: "#a59783",
        QPalette.HighlightedText: "#cc5200",
        (QPalette.Active, QPalette.Button): "#baaa93",
        (QPalette.Disabled, QPalette.ButtonText): "#cc5200",
        (QPalette.Disabled, QPalette.WindowText): "#cc5200",
        (QPalette.Disabled, QPalette.Text): "#baaa93",
        (QPalette.Disabled, QPalette.Light): "#baaa93",
    }),
    ("Nord", {
        QPalette.Window: "#4b3832",
        QPalette.WindowText: "#fff4e6",
        QPalette.Base: "#be9b7b",
        QPalette.AlternateBase: "#434c5e",
        QPalette.ToolTipBase: "#4c566a",
        QPalette.ToolTipText: "#3c2f2f",
        QPalette.Text: "#eceff4",
        QPalette.Button: "#4b3832",
        QPalette.ButtonText: "#eceff4",
        QPalette.BrightText: "#88c0d0",
        QPalette.Link: "#88c0d0",
        QPalette.Highlight: "#88c0d0",
        QPalette.HighlightedText: "#eceff4",
        (QPalette.Active, QPalette.Button): "#4b3832",
        (QPalette.Disabled, QPalette.ButtonText): "#eceff4",
        (QPalette.Disabled, QPalette.WindowText): "#eceff4",
        (QPalette.Disabled, QPalette.Text): "#eceff4",
        (QPalette.Disabled, QPalette.Light): "#88c0d0",
    }),
    ("Olivia", {
        QPalette.Window: "#181818",
        QPalette.WindowText: "#d9d9d9",
        QPalette.Base: "#181818",
        QPalette.AlternateBase: "#2c2c2c",
        QPalette.ToolTipBase: "#363636 ",
        QPalette.ToolTipText: "#d9d9d9",
        QPalette.Text: "#d9d9d9",
        QPalette.Button: "#181818",
        QPalette.ButtonText: "#d9d9d9",
        QPalette.BrightText: "#fabcad",
        QPalette.Link: "#fabcad",
        QPalette.Highlight: "#fabcad",
        QPalette.HighlightedText: "#2c2c2c",
        (QPalette.Active, QPalette.Button): "#181818",
        (QPalette.Disabled, QPalette.ButtonText): "#d9d9d9",
        (QPalette.Disabled, QPalette.WindowText): "#d9d9d9",
        (QPalette.Disabled, QPalette.Text): "#d9d9d9",
        (QPalette.Disabled, QPalette.Light): "#fabcad",
    }),
    ("Dracula", {
        QPalette.Window: "#282a36",
        QPalette.WindowText: "#f8f8f2",
        QPalette.Base: "#282a36",
        QPalette.AlternateBase: "#44475a",
        QPalette.ToolTipBase: "#6272a4",
        QPalette.ToolTipText: "#f8f8f2",
        QPalette.Text: "#f8f8f2",
        QPalette.Button: "#282a36",
        QPalette.ButtonText: "#f8f8f2",
        QPalette.BrightText: "#8be9fd",
        QPalette.Link: "#8be9fd",
        QPalette.Highlight: "#8be9fd",
        QPalette.HighlightedText: "#f8f8f2",
        (QPalette.Active, QPalette.Button): "#282a36",
        (QPalette.Disabled, QPalette.ButtonText): "#f8f8f2",
        (QPalette.Disabled, QPalette.WindowText): "#f8f8f2",
        (QPalette.Disabled, QPalette.Text): "#f8f8f2",
        (QPalette.Disabled, QPalette.Light): "#8be9fd",
    }),
    ("Bliss", {
        QPalette.Window: "#343434",
        QPalette.WindowText: "#cbc8c9",
        QPalette.Base: "#343434",
        QPalette.AlternateBase: "#3b3b3b",
        QPalette.ToolTipBase: "#424242",
        QPalette.ToolTipText: "#cbc8c9",
        QPalette.Text: "#cbc8c9",
        QPalette.Button: "#343434",
        QPalette.ButtonText: "#cbc8c9",
        QPalette.BrightText: "#f5d1c8",
        QPalette.Link: "#f5d1c8",
        QPalette.Highlight: "#f5d1c8",
        QPalette.HighlightedText: "#424242",
        (QPalette.Active, QPalette.Button): "#343434",
        (QPalette.Disabled, QPalette.ButtonText): "#cbc8c9",
        (QPalette.Disabled, QPalette.WindowText): "#cbc8c9",
        (QPalette.Disabled, QPalette.Text): "#cbc8c9",
        (QPalette.Disabled, QPalette.Light): "#f5d1c8",
    }),
    # Modern 2025 Pastel Themes
    ("Lavender Dream", {
        QPalette.Window: "#f5f3ff",
        QPalette.WindowText: "#4a4458",
        QPalette.Base: "#ffffff",
        QPalette.AlternateBase: "#faf9ff",
        QPalette.ToolTipBase: "#e8e4ff",
        QPalette.ToolTipText: "#4a4458",
        QPalette.Text: "#4a4458",
        QPalette.Button: "#f5f3ff",
        QPalette.ButtonText: "#4a4458",
        QPalette.BrightText: "#8b7ab8",
        QPalette.Link: "#9d8ac7",
        QPalette.Highlight: "#c4b5fd",
        QPalette.HighlightedText: "#2d2438",
        (QPalette.Active, QPalette.Button): "#f0ecff",
        (QPalette.Disabled, QPalette.ButtonText): "#b4adc4",
        (QPalette.Disabled, QPalette.WindowText): "#b4adc4",
        (QPalette.Disabled, QPalette.Text): "#b4adc4",
        (QPalette.Disabled, QPalette.Light): "#e8e4ff",
    }),
    ("Mint Fresh", {
        QPalette.Window: "#f0fdf9",
        QPalette.WindowText: "#1e4d3f",
        QPalette.Base: "#ffffff",
        QPalette.AlternateBase: "#f4fefb",
        QPalette.ToolTipBase: "#d1fae5",
        QPalette.ToolTipText: "#1e4d3f",
        QPalette.Text: "#1e4d3f",
        QPalette.Button: "#f0fdf9",
        QPalette.ButtonText: "#1e4d3f",
        QPalette.BrightText: "#34d399",
        QPalette.Link: "#6ee7b7",
        QPalette.Highlight: "#a7f3d0",
        QPalette.HighlightedText: "#064e3b",
        (QPalette.Active, QPalette.Button): "#ecfdf5",
        (QPalette.Disabled, QPalette.ButtonText): "#9ca3af",
        (QPalette.Disabled, QPalette.WindowText): "#9ca3af",
        (QPalette.Disabled, QPalette.Text): "#9ca3af",
        (QPalette.Disabled, QPalette.Light): "#d1fae5",
    }),
    ("Peachy Keen", {
        QPalette.Window: "#fff8f3",
        QPalette.WindowText: "#5c3d2e",
        QPalette.Base: "#ffffff",
        QPalette.AlternateBase: "#fffbf7",
        QPalette.ToolTipBase: "#ffe8d9",
        QPalette.ToolTipText: "#5c3d2e",
        QPalette.Text: "#5c3d2e",
        QPalette.Button: "#fff8f3",
        QPalette.ButtonText: "#5c3d2e",
        QPalette.BrightText: "#fb923c",
        QPalette.Link: "#fdba74",
        QPalette.Highlight: "#fed7aa",
        QPalette.HighlightedText: "#431407",
        (QPalette.Active, QPalette.Button): "#fff4ed",
        (QPalette.Disabled, QPalette.ButtonText): "#b8a99f",
        (QPalette.Disabled, QPalette.WindowText): "#b8a99f",
        (QPalette.Disabled, QPalette.Text): "#b8a99f",
        (QPalette.Disabled, QPalette.Light): "#ffe8d9",
    }),
    ("Sky Serenity", {
        QPalette.Window: "#f0f9ff",
        QPalette.WindowText: "#1e3a5f",
        QPalette.Base: "#ffffff",
        QPalette.AlternateBase: "#f5fbff",
        QPalette.ToolTipBase: "#dbeafe",
        QPalette.ToolTipText: "#1e3a5f",
        QPalette.Text: "#1e3a5f",
        QPalette.Button: "#f0f9ff",
        QPalette.ButtonText: "#1e3a5f",
        QPalette.BrightText: "#38bdf8",
        QPalette.Link: "#7dd3fc",
        QPalette.Highlight: "#bae6fd",
        QPalette.HighlightedText: "#0c4a6e",
        (QPalette.Active, QPalette.Button): "#e0f2fe",
        (QPalette.Disabled, QPalette.ButtonText): "#94a3b8",
        (QPalette.Disabled, QPalette.WindowText): "#94a3b8",
        (QPalette.Disabled, QPalette.Text): "#94a3b8",
        (QPalette.Disabled, QPalette.Light): "#dbeafe",
    }),
    ("Rose Garden", {
        QPalette.Window: "#fef3f6",
        QPalette.WindowText: "#4a2533",
        QPalette.Base: "#ffffff",
        QPalette.AlternateBase: "#fff8fa",
        QPalette.ToolTipBase: "#fce7f3",
        QPalette.ToolTipText: "#4a2533",
        QPalette.Text: "#4a2533",
        QPalette.Button: "#fef3f6",
        QPalette.ButtonText: "#4a2533",
        QPalette.BrightText: "#f472b6",
        QPalette.Link: "#f9a8d4",
        QPalette.Highlight: "#fbcfe8",
        QPalette.HighlightedText: "#500724",
        (QPalette.Active, QPalette.Button): "#fce7f3",
        (QPalette.Disabled, QPalette.ButtonText): "#b8a5ad",
        (QPalette.Disabled, QPalette.WindowText): "#b8a5ad",
        (QPalette.Disabled, QPalette.Text): "#b8a5ad",
        (QPalette.Disabled, QPalette.Light): "#fce7f3",
    }),
]

palettes = dict()

for name, colors in themes:
    palette = QPalette()
    for role, color in colors.items():
        if not hasattr(type(role), '__iter__'):
            role = [role]
        palette.setColor(*role, QColor(color))
    palettes[name] = palette


class Theme:

    theme = ""

    @classmethod
    def set_theme(cls, theme):
        cls.theme = theme
        if theme in palettes:
            QApplication.setPalette(palettes[theme])
            QApplication.setStyle("Fusion")
            QApplication.instance().setStyleSheet(cls.get_stylesheet())
        # For default/system theme, do nothing
        # User will have to restart the application for it to be applied

    @classmethod
    def get_theme(cls):
        return cls.theme

    @classmethod
    def mask_light_factor(cls):
        light_themes = ["Light", "Lavender Dream", "Mint Fresh", "Peachy Keen", "Sky Serenity", "Rose Garden"]
        if cls.theme in light_themes:
            return 103
        return 150

    @classmethod
    def get_stylesheet(cls):
        """Return modern 2025 stylesheet for tabs and UI elements"""
        return """
            /* Modern Tab Styling - Connected to Content Box */
            QTabWidget::pane {
                border: 1px solid palette(mid);
                border-top: none;
                background: transparent;
                top: 0px;
                margin-top: 0px;
            }

            QTabBar::tab {
                background: palette(button);
                border: 1px solid palette(mid);
                padding: 12px 22px;
                margin-right: 2px;
                margin-bottom: 0px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: none;
                font-weight: 500;
            }

            QTabBar::tab:selected {
                background: palette(base);
                color: palette(text);
                border-bottom: 1px solid palette(base);
                padding-bottom: 13px;
                margin-bottom: -1px;
            }

            QTabBar::tab:hover:!selected {
                background: palette(light);
            }

            /* Rounded Keycode Buttons - Using object name selector */
            QPushButton[keycode_button="true"] {
                border-radius: 8px;
                border: 1px solid palette(mid);
                background: palette(button);
                font-size: 9pt;
            }

            QPushButton[keycode_button="true"]:hover {
                background: palette(light);
                border-color: palette(highlight);
            }

            QPushButton[keycode_button="true"]:pressed {
                background: palette(highlight);
                color: palette(highlighted-text);
            }

            /* Layer Selection Button Styling */
            QPushButton[keycode_button="true"]:checked {
                background: palette(highlight);
                color: palette(highlighted-text);
                border: 2px solid palette(highlight);
                font-weight: 600;
            }

            /* Modern Dropdown/ComboBox Styling with Down Arrow */
            QComboBox {
                border: 1px solid palette(mid);
                border-radius: 6px;
                padding: 6px 12px;
                padding-right: 28px;
                background: palette(base);
                min-width: 80px;
            }

            QComboBox:hover {
                border-color: palette(highlight);
            }

            QComboBox:focus {
                border-color: palette(highlight);
                background: palette(alternate-base);
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
            }

            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid palette(text);
                margin-right: 5px;
            }

            QComboBox QAbstractItemView {
                border: 1px solid palette(mid);
                border-radius: 6px;
                background: palette(base);
                selection-background-color: palette(highlight);
                selection-color: palette(highlighted-text);
                padding: 4px;
                outline: 0px;
            }

            QComboBox QAbstractItemView::item {
                padding: 6px;
                min-height: 24px;
            }

            /* Modern Table Styling */
            QTableWidget, QTableView {
                border: 1px solid palette(mid);
                border-radius: 6px;
                background: palette(base);
                gridline-color: palette(midlight);
                selection-background-color: palette(highlight);
                selection-color: palette(highlighted-text);
            }

            QTableWidget::item, QTableView::item {
                padding: 6px;
                border: none;
            }

            QTableWidget::item:hover, QTableView::item:hover {
                background: palette(alternate-base);
            }

            QHeaderView::section {
                background: palette(window);
                padding: 8px;
                border: none;
                border-bottom: 2px solid palette(mid);
                font-weight: 500;
            }

            QHeaderView::section:hover {
                background: palette(alternate-base);
            }

            /* Modern Oval Scrollbars */
            QScrollBar:vertical {
                background: palette(base);
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: palette(mid);
                border-radius: 5px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background: palette(dark);
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }

            QScrollBar:horizontal {
                background: palette(base);
                height: 10px;
                border-radius: 5px;
                margin: 0px;
            }

            QScrollBar::handle:horizontal {
                background: palette(mid);
                border-radius: 5px;
                min-width: 30px;
            }

            QScrollBar::handle:horizontal:hover {
                background: palette(dark);
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }
        """

    @classmethod
    def get_button_stylesheet(cls):
        """Return stylesheet for keycode buttons"""
        return """
            QPushButton {
                border-radius: 8px;
                border: 1px solid palette(mid);
            }
        """
