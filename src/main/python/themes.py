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
        # For default/system theme, do nothing
        # User will have to restart the application for it to be applied

    @classmethod
    def get_theme(cls):
        return cls.theme

    @classmethod
    def mask_light_factor(cls):
        if cls.theme == "Light":
            return 103
        return 150

    @classmethod
    def get_tab_stylesheet(cls):
        """Returns stylesheet for QTabWidget and QTabBar with theme-specific colors and rounded edges"""
        theme_colors = {
            "Light": {
                "tab_bg": "#e0e0e0",
                "tab_selected": "#ffffff",
                "tab_hover": "#ececec",
                "tab_text": "#000000",
                "tab_selected_text": "#000000",
                "pane_border": "#c0c0c0",
                "pane_bg": "#ffffff"
            },
            "Dark": {
                "tab_bg": "#2a2a2a",
                "tab_selected": "#3d3d3d",
                "tab_hover": "#353535",
                "tab_text": "#ffffff",
                "tab_selected_text": "#ffffff",
                "pane_border": "#1a1a1a",
                "pane_bg": "#353535"
            },
            "Arc": {
                "tab_bg": "#4a4237",
                "tab_selected": "#61574a",
                "tab_hover": "#554d42",
                "tab_text": "#cc5200",
                "tab_selected_text": "#cc5200",
                "pane_border": "#3e3832",
                "pane_bg": "#61574a"
            },
            "Nord": {
                "tab_bg": "#3b302b",
                "tab_selected": "#5d4e47",
                "tab_hover": "#4a3d38",
                "tab_text": "#eceff4",
                "tab_selected_text": "#fff4e6",
                "pane_border": "#2e2520",
                "pane_bg": "#4b3832"
            },
            "Olivia": {
                "tab_bg": "#0f0f0f",
                "tab_selected": "#2c2c2c",
                "tab_hover": "#1a1a1a",
                "tab_text": "#d9d9d9",
                "tab_selected_text": "#fabcad",
                "pane_border": "#000000",
                "pane_bg": "#181818"
            },
            "Dracula": {
                "tab_bg": "#1e2029",
                "tab_selected": "#44475a",
                "tab_hover": "#313341",
                "tab_text": "#f8f8f2",
                "tab_selected_text": "#8be9fd",
                "pane_border": "#191a21",
                "pane_bg": "#282a36"
            },
            "Bliss": {
                "tab_bg": "#2a2a2a",
                "tab_selected": "#3b3b3b",
                "tab_hover": "#323232",
                "tab_text": "#cbc8c9",
                "tab_selected_text": "#f5d1c8",
                "pane_border": "#1e1e1e",
                "pane_bg": "#343434"
            }
        }

        colors = theme_colors.get(cls.theme, theme_colors["Dark"])

        return f"""
            QTabWidget::pane {{
                border: 2px solid {colors['pane_border']};
                border-radius: 8px;
                background-color: {colors['pane_bg']};
                top: -1px;
            }}

            QTabBar::tab {{
                background-color: {colors['tab_bg']};
                color: {colors['tab_text']};
                border: 1px solid {colors['pane_border']};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 16px;
                margin-right: 2px;
                min-width: 80px;
            }}

            QTabBar::tab:selected {{
                background-color: {colors['tab_selected']};
                color: {colors['tab_selected_text']};
                border-bottom: 2px solid {colors['tab_selected']};
                margin-bottom: -2px;
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {colors['tab_hover']};
            }}

            QTabBar::tab:first {{
                margin-left: 0px;
            }}
        """

    @classmethod
    def get_button_stylesheet(cls):
        """Returns stylesheet for QPushButton with theme-specific colors and rounded edges"""
        theme_colors = {
            "Light": {
                "button_bg": "#d4d4d4",
                "button_hover": "#e0e0e0",
                "button_pressed": "#c0c0c0",
                "button_text": "#000000",
                "button_border": "#a0a0a0"
            },
            "Dark": {
                "button_bg": "#454545",
                "button_hover": "#505050",
                "button_pressed": "#3a3a3a",
                "button_text": "#ffffff",
                "button_border": "#2a2a2a"
            },
            "Arc": {
                "button_bg": "#8a7a63",
                "button_hover": "#9a8a73",
                "button_pressed": "#7a6a53",
                "button_text": "#cc5200",
                "button_border": "#6a5a43"
            },
            "Nord": {
                "button_bg": "#6d5e57",
                "button_hover": "#7d6e67",
                "button_pressed": "#5d4e47",
                "button_text": "#eceff4",
                "button_border": "#4d3e37"
            },
            "Olivia": {
                "button_bg": "#3c3c3c",
                "button_hover": "#4c4c4c",
                "button_pressed": "#2c2c2c",
                "button_text": "#d9d9d9",
                "button_border": "#1c1c1c"
            },
            "Dracula": {
                "button_bg": "#54576a",
                "button_hover": "#64677a",
                "button_pressed": "#44475a",
                "button_text": "#f8f8f2",
                "button_border": "#34374a"
            },
            "Bliss": {
                "button_bg": "#4b4b4b",
                "button_hover": "#5b5b5b",
                "button_pressed": "#3b3b3b",
                "button_text": "#cbc8c9",
                "button_border": "#2b2b2b"
            }
        }

        colors = theme_colors.get(cls.theme, theme_colors["Dark"])

        return f"""
            QPushButton {{
                background-color: {colors['button_bg']};
                color: {colors['button_text']};
                border: 1px solid {colors['button_border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}

            QPushButton:hover {{
                background-color: {colors['button_hover']};
            }}

            QPushButton:pressed {{
                background-color: {colors['button_pressed']};
            }}
        """

    @classmethod
    def get_scrollbar_stylesheet(cls):
        """Returns stylesheet for QScrollBar with theme-specific colors"""
        theme_colors = {
            "Light": {
                "scrollbar_bg": "#f0f0f0",
                "scrollbar_handle": "#c0c0c0",
                "scrollbar_handle_hover": "#a0a0a0",
                "scrollbar_handle_pressed": "#808080"
            },
            "Dark": {
                "scrollbar_bg": "#1a1a1a",
                "scrollbar_handle": "#505050",
                "scrollbar_handle_hover": "#606060",
                "scrollbar_handle_pressed": "#404040"
            },
            "Arc": {
                "scrollbar_bg": "#3e3832",
                "scrollbar_handle": "#7a6a53",
                "scrollbar_handle_hover": "#8a7a63",
                "scrollbar_handle_pressed": "#6a5a43"
            },
            "Nord": {
                "scrollbar_bg": "#2e2520",
                "scrollbar_handle": "#5d4e47",
                "scrollbar_handle_hover": "#6d5e57",
                "scrollbar_handle_pressed": "#4d3e37"
            },
            "Olivia": {
                "scrollbar_bg": "#0a0a0a",
                "scrollbar_handle": "#2c2c2c",
                "scrollbar_handle_hover": "#3c3c3c",
                "scrollbar_handle_pressed": "#1c1c1c"
            },
            "Dracula": {
                "scrollbar_bg": "#191a21",
                "scrollbar_handle": "#44475a",
                "scrollbar_handle_hover": "#54576a",
                "scrollbar_handle_pressed": "#34374a"
            },
            "Bliss": {
                "scrollbar_bg": "#1e1e1e",
                "scrollbar_handle": "#3b3b3b",
                "scrollbar_handle_hover": "#4b4b4b",
                "scrollbar_handle_pressed": "#2b2b2b"
            }
        }

        colors = theme_colors.get(cls.theme, theme_colors["Dark"])

        return f"""
            QScrollBar:vertical {{
                background: {colors['scrollbar_bg']};
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }}

            QScrollBar::handle:vertical {{
                background: {colors['scrollbar_handle']};
                border-radius: 6px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {colors['scrollbar_handle_hover']};
            }}

            QScrollBar::handle:vertical:pressed {{
                background: {colors['scrollbar_handle_pressed']};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                background: {colors['scrollbar_bg']};
                height: 12px;
                border-radius: 6px;
                margin: 0px;
            }}

            QScrollBar::handle:horizontal {{
                background: {colors['scrollbar_handle']};
                border-radius: 6px;
                min-width: 20px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {colors['scrollbar_handle_hover']};
            }}

            QScrollBar::handle:horizontal:pressed {{
                background: {colors['scrollbar_handle_pressed']};
            }}

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

    @classmethod
    def get_tree_stylesheet(cls):
        """Returns stylesheet for QTreeWidget with theme-specific colors and self-contained columns"""
        theme_colors = {
            "Light": {
                "tree_bg": "#ffffff",
                "tree_alternate": "#f5f5f5",
                "tree_border": "#c0c0c0",
                "tree_header": "#e0e0e0",
                "tree_text": "#000000"
            },
            "Dark": {
                "tree_bg": "#2a2a2a",
                "tree_alternate": "#323232",
                "tree_border": "#1a1a1a",
                "tree_header": "#3a3a3a",
                "tree_text": "#ffffff"
            },
            "Arc": {
                "tree_bg": "#61574a",
                "tree_alternate": "#6a5f52",
                "tree_border": "#4a4237",
                "tree_header": "#7a6a5d",
                "tree_text": "#cc5200"
            },
            "Nord": {
                "tree_bg": "#4b3832",
                "tree_alternate": "#54413a",
                "tree_border": "#3b302b",
                "tree_header": "#5d4e47",
                "tree_text": "#eceff4"
            },
            "Olivia": {
                "tree_bg": "#181818",
                "tree_alternate": "#202020",
                "tree_border": "#0f0f0f",
                "tree_header": "#2c2c2c",
                "tree_text": "#d9d9d9"
            },
            "Dracula": {
                "tree_bg": "#282a36",
                "tree_alternate": "#30323e",
                "tree_border": "#1e2029",
                "tree_header": "#44475a",
                "tree_text": "#f8f8f2"
            },
            "Bliss": {
                "tree_bg": "#343434",
                "tree_alternate": "#3b3b3b",
                "tree_border": "#2a2a2a",
                "tree_header": "#424242",
                "tree_text": "#cbc8c9"
            }
        }

        colors = theme_colors.get(cls.theme, theme_colors["Dark"])

        return f"""
            QTreeWidget {{
                background-color: {colors['tree_bg']};
                alternate-background-color: {colors['tree_alternate']};
                color: {colors['tree_text']};
                border: 2px solid {colors['tree_border']};
                border-radius: 8px;
                padding: 4px;
            }}

            QTreeWidget::item {{
                border: 1px solid {colors['tree_border']};
                border-radius: 4px;
                padding: 4px;
                margin: 1px;
            }}

            QTreeWidget::item:selected {{
                background-color: {colors['tree_header']};
            }}

            QTreeWidget::item:hover {{
                background-color: {colors['tree_alternate']};
            }}

            QHeaderView::section {{
                background-color: {colors['tree_header']};
                color: {colors['tree_text']};
                border: 1px solid {colors['tree_border']};
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
            }}
        """
