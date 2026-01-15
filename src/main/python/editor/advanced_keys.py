# SPDX-License-Identifier: GPL-2.0-or-later
"""
Advanced Keys Tab - Consolidated tab for DKS, Macros, Toggle, TapDance, Combos, and Key Override

This tab uses a side-tab navigation pattern similar to KeyboardTab in tabbed_keycodes.py
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QSizePolicy)
from PyQt5.QtCore import Qt

from editor.basic_editor import BasicEditor
from widgets.editor_container import EditorContainer
from vial_device import VialKeyboard


class AdvancedKeysTab(BasicEditor):
    """Consolidated tab for advanced key configuration features"""

    def __init__(self, layout_editor, dks_settings, macro_recorder, toggle_settings,
                 tap_dance, combos, key_override):
        super().__init__()
        self.layout_editor = layout_editor

        # Store references to the editor components (these are QVBoxLayout subclasses)
        self.dks_settings = dks_settings
        self.macro_recorder = macro_recorder
        self.toggle_settings = toggle_settings
        self.tap_dance = tap_dance
        self.combos = combos
        self.key_override = key_override

        # Track which sections are valid for the current device
        self.section_validity = {}

        # Track EditorContainers for each section
        self.editor_containers = {}

        # Define sections (editor, display_name, short_name)
        self.sections = [
            (self.dks_settings, "Dynamic Keystroke", "DKS"),
            (self.macro_recorder, "Macro", "Macro"),
            (self.toggle_settings, "Toggle", "Toggle"),
            (self.tap_dance, "Tapdance", "TapDance"),
            (self.combos, "Combos", "Combos"),
            (self.key_override, "Key Override", "KeyOvr"),
        ]

        self._build_ui()

    def _build_ui(self):
        """Build the side-tab UI layout"""
        # Create horizontal layout: side tabs on left, content on right
        main_layout_h = QHBoxLayout()
        main_layout_h.setSpacing(0)
        main_layout_h.setContentsMargins(0, 0, 0, 0)

        # Create side tabs container
        side_tabs_container = QWidget()
        side_tabs_container.setObjectName("advanced_keys_side_tabs")
        side_tabs_container.setStyleSheet("""
            QWidget#advanced_keys_side_tabs {
                background: palette(window);
                border: 1px solid palette(mid);
                border-right: none;
            }
        """)
        side_tabs_layout = QVBoxLayout(side_tabs_container)
        side_tabs_layout.setSpacing(0)
        side_tabs_layout.setContentsMargins(0, 0, 0, 0)

        # Create side tab buttons
        self.side_tab_buttons = {}
        for editor, display_name, short_name in self.sections:
            btn = QPushButton(display_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(50)
            btn.setMinimumWidth(140)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid palette(mid);
                    border-radius: 0px;
                    border-right: none;
                    background: palette(button);
                    text-align: left;
                    padding-left: 15px;
                    font-size: 10pt;
                }
                QPushButton:hover:!checked {
                    background: palette(light);
                }
                QPushButton:checked {
                    background: palette(base);
                    font-weight: 600;
                    border-right: 1px solid palette(base);
                }
                QPushButton:disabled {
                    color: palette(mid);
                    background: palette(window);
                }
            """)
            btn.clicked.connect(lambda checked, dn=display_name: self.show_section(dn))
            side_tabs_layout.addWidget(btn)
            self.side_tab_buttons[display_name] = btn

        side_tabs_layout.addStretch(1)
        main_layout_h.addWidget(side_tabs_container)

        # Create content container
        self.content_wrapper = QWidget()
        self.content_wrapper.setObjectName("advanced_keys_content")
        self.content_wrapper.setStyleSheet("""
            QWidget#advanced_keys_content {
                border: 1px solid palette(mid);
                background: palette(base);
            }
        """)
        self.content_layout = QVBoxLayout(self.content_wrapper)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # Create EditorContainers for each section
        # Each editor is a QVBoxLayout, so we wrap it in EditorContainer
        self.section_widgets = {}
        for editor, display_name, short_name in self.sections:
            # Create an EditorContainer to wrap the editor layout
            container = EditorContainer(editor)
            container.hide()
            self.content_layout.addWidget(container)
            self.section_widgets[display_name] = container
            self.editor_containers[display_name] = container

        main_layout_h.addWidget(self.content_wrapper, 1)  # Give content area more space

        # Create main widget to hold the layout
        main_widget = QWidget()
        main_widget.setLayout(main_layout_h)
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.addWidget(main_widget)

        # Track current section
        self.current_section = None

    def show_section(self, section_name):
        """Show the specified section and update tab button states"""
        # Check if this section is valid
        if section_name not in self.section_validity or not self.section_validity[section_name]:
            return

        # Hide all section containers
        for container in self.section_widgets.values():
            container.hide()

        # Uncheck all tab buttons
        for btn in self.side_tab_buttons.values():
            btn.setChecked(False)

        # Show the selected section and check its button
        if section_name in self.section_widgets:
            container = self.section_widgets[section_name]
            container.show()
            if section_name in self.side_tab_buttons:
                self.side_tab_buttons[section_name].setChecked(True)
            self.current_section = section_name

    def _show_first_valid_section(self):
        """Show the first section that is valid for the current device"""
        for editor, display_name, short_name in self.sections:
            if self.section_validity.get(display_name, False):
                self.show_section(display_name)
                return

    def rebuild(self, device):
        """Rebuild the tab when device changes"""
        super().rebuild(device)

        if not self.valid():
            return

        # Update section validity based on individual editor validity
        for editor, display_name, short_name in self.sections:
            is_valid = editor.valid()
            self.section_validity[display_name] = is_valid

            # Enable/disable side tab button based on validity
            if display_name in self.side_tab_buttons:
                self.side_tab_buttons[display_name].setEnabled(is_valid)

        # Show first valid section
        self._show_first_valid_section()

    def valid(self):
        """Check if this tab should be shown - valid if any section is valid"""
        # This tab is valid if the device is a VialKeyboard
        if not isinstance(self.device, VialKeyboard):
            return False

        # Check if at least one section is valid
        return any(editor.valid() for editor, _, _ in self.sections)

    def activate(self):
        """Called when tab becomes active"""
        # Activate the current section's editor
        if self.current_section:
            container = self.editor_containers.get(self.current_section)
            if container and hasattr(container, 'editor') and hasattr(container.editor, 'activate'):
                container.editor.activate()

    def deactivate(self):
        """Called when tab becomes inactive"""
        # Deactivate the current section's editor
        if self.current_section:
            container = self.editor_containers.get(self.current_section)
            if container and hasattr(container, 'editor') and hasattr(container.editor, 'deactivate'):
                container.editor.deactivate()
