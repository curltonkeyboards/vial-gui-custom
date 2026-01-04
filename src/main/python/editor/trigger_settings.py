# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QWidget,
                              QSlider, QCheckBox, QPushButton, QComboBox, QFrame,
                              QSizePolicy, QScrollArea, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QColor

from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget2
from widgets.square_button import SquareButton
from widgets.range_slider import TriggerSlider, RapidTriggerSlider, StyledSlider
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard


class ClickableWidget(QWidget):
    """Widget that emits clicked signal when clicked anywhere"""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class TriggerSettingsTab(BasicEditor):
    """Per-key actuation settings editor"""

    def __init__(self, layout_editor):
        print("TriggerSettingsTab.__init__ called")
        super().__init__()

        self.layout_editor = layout_editor
        self.keyboard = None
        self.current_layer = 0
        self.syncing = False
        self.actuation_widget_ref = None  # Reference to QuickActuationWidget for synchronization

        # Track which tab is active (replaces hover_state)
        # Possible values: 'actuation', 'rapidfire', 'velocity'
        self.active_tab = 'actuation'
        self.showing_keymap = False  # Track if hovering over keyboard

        # Cache for per-key actuation values (70 keys × 12 layers)
        # Each key now stores 8 fields
        # Note: deadzone values are ALWAYS enabled (non-zero by default)
        self.per_key_values = []
        for layer in range(12):
            layer_keys = []
            for _ in range(70):
                layer_keys.append({
                    'actuation': 60,                    # 0-100 = 0-2.5mm, default 1.5mm (60/40 = 1.5)
                    'deadzone_top': 4,                  # 0-20 = 0-0.5mm, default 0.1mm (4/40 = 0.1) - FROM RIGHT
                    'deadzone_bottom': 4,               # 0-20 = 0-0.5mm, default 0.1mm (4/40 = 0.1) - FROM LEFT
                    'velocity_curve': 0,                # 0-16 (0-6: Factory curves, 7-16: User curves), default Linear
                    'flags': 0,                         # Bit 0: rapidfire_enabled, Bit 1: use_per_key_velocity_curve
                    'rapidfire_press_sens': 4,          # 1-100 = 0.025-2.5mm, default 0.1mm (4/40 = 0.1) - FROM LEFT
                    'rapidfire_release_sens': 4,        # 1-100 = 0.025-2.5mm, default 0.1mm (4/40 = 0.1) - FROM RIGHT
                    'rapidfire_velocity_mod': 0         # -64 to +64, default 0
                })
            self.per_key_values.append(layer_keys)

        # Mode flags
        self.mode_enabled = False
        self.per_layer_enabled = False

        # Cache for layer actuation settings
        self.layer_data = []
        for _ in range(12):
            self.layer_data.append({
                'normal': 80,
                'midi': 80,
                'velocity': 2,  # Velocity mode (0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak)
                'vel_speed': 10  # Velocity speed scale
            })

        # Track unsaved changes for global actuation settings
        self.has_unsaved_changes = False
        self.pending_layer_data = None  # Will store pending changes before save

        # Top bar with layer selection
        self.layout_layers = QHBoxLayout()
        self.layout_layers.setSpacing(6)  # Add spacing between layer buttons
        self.layout_size = QVBoxLayout()
        self.layout_size.setSpacing(6)  # Add spacing between size buttons
        layer_label = QLabel(tr("TriggerSettings", "Layer"))

        layout_labels_container = QHBoxLayout()
        layout_labels_container.addWidget(layer_label)
        layout_labels_container.addLayout(self.layout_layers)
        layout_labels_container.addStretch()
        layout_labels_container.addLayout(self.layout_size)

        # Keyboard display
        self.container = KeyboardWidget2(layout_editor)
        self.container.clicked.connect(self.on_key_clicked)
        self.container.deselected.connect(self.on_key_deselected)
        self.container.installEventFilter(self)

        # Checkboxes for enable modes (will be placed left of keyboard)
        self.enable_checkbox = QCheckBox(tr("TriggerSettings", "Enable Per-Key Actuation"))
        self.enable_checkbox.setStyleSheet("QCheckBox { font-weight: bold; }")
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)

        self.per_layer_checkbox = QCheckBox(tr("TriggerSettings", "Enable Per-Layer Actuation"))
        self.per_layer_checkbox.setStyleSheet("QCheckBox { font-weight: bold; }")
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_changed)

        # Selection buttons column (left of keyboard)
        selection_buttons_layout = QVBoxLayout()
        selection_buttons_layout.setSpacing(8)  # Add spacing between buttons

        # Add checkboxes at the top
        selection_buttons_layout.addWidget(self.enable_checkbox)
        selection_buttons_layout.addWidget(self.per_layer_checkbox)
        selection_buttons_layout.addSpacing(15)  # Add space after checkboxes

        self.select_all_btn = QPushButton(tr("TriggerSettings", "Select All"))
        self.select_all_btn.setMinimumHeight(32)  # Make buttons bigger
        self.select_all_btn.clicked.connect(self.on_select_all)
        selection_buttons_layout.addWidget(self.select_all_btn)

        self.unselect_all_btn = QPushButton(tr("TriggerSettings", "Unselect All"))
        self.unselect_all_btn.setMinimumHeight(32)  # Make buttons bigger
        self.unselect_all_btn.clicked.connect(self.on_unselect_all)
        selection_buttons_layout.addWidget(self.unselect_all_btn)

        self.invert_selection_btn = QPushButton(tr("TriggerSettings", "Invert Selection"))
        self.invert_selection_btn.setMinimumHeight(32)  # Make buttons bigger
        self.invert_selection_btn.clicked.connect(self.on_invert_selection)
        selection_buttons_layout.addWidget(self.invert_selection_btn)

        # Add layer management buttons to selection section
        self.copy_layer_btn = QPushButton(tr("TriggerSettings", "Copy from Layer..."))
        self.copy_layer_btn.setMinimumHeight(32)  # Make buttons bigger
        self.copy_layer_btn.setEnabled(False)
        self.copy_layer_btn.clicked.connect(self.on_copy_layer)
        selection_buttons_layout.addWidget(self.copy_layer_btn)

        self.copy_all_layers_btn = QPushButton(tr("TriggerSettings", "Copy Settings to All Layers"))
        self.copy_all_layers_btn.setMinimumHeight(32)  # Make buttons bigger
        self.copy_all_layers_btn.setEnabled(False)
        self.copy_all_layers_btn.clicked.connect(self.on_copy_to_all_layers)
        selection_buttons_layout.addWidget(self.copy_all_layers_btn)

        self.reset_btn = QPushButton(tr("TriggerSettings", "Reset All to Default"))
        self.reset_btn.setMinimumHeight(32)  # Make buttons bigger
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self.on_reset_all)
        selection_buttons_layout.addWidget(self.reset_btn)

        self.save_btn = QPushButton(tr("TriggerSettings", "Save"))
        self.save_btn.setMinimumHeight(32)  # Make buttons bigger
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("QPushButton:enabled { font-weight: bold; color: #ff8c32; }")
        self.save_btn.clicked.connect(self.on_save)
        selection_buttons_layout.addWidget(self.save_btn)

        selection_buttons_layout.addStretch()

        # Keyboard area with layer buttons
        keyboard_area = QVBoxLayout()
        keyboard_area.addLayout(layout_labels_container)

        keyboard_layout = QHBoxLayout()
        keyboard_layout.addStretch(1)  # Add spacer to center the buttons and keyboard
        keyboard_layout.addSpacing(15)  # Add left margin so buttons aren't against the wall
        keyboard_layout.addLayout(selection_buttons_layout)
        keyboard_layout.addSpacing(20)  # Add spacing between buttons and keyboard
        keyboard_layout.addWidget(self.container, 0, Qt.AlignTop)
        keyboard_layout.addStretch(1)
        keyboard_area.addLayout(keyboard_layout)
        keyboard_area.setContentsMargins(0, 0, 0, 0)  # Remove margins
        keyboard_area.setSpacing(0)  # Remove spacing
        keyboard_area.addStretch()  # Push keyboard to top to minimize gap

        w = ClickableWidget()
        w.setLayout(keyboard_area)
        w.clicked.connect(self.on_empty_space_clicked)

        # Wrap keyboard area in scroll area with max height
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMaximumHeight(500)  # Set maximum height of 500 pixels
        scroll_area.setWidget(w)

        # Control panel at bottom
        control_panel = self.create_control_panel()

        self.layer_buttons = []
        self.device = None

        layout_editor.changed.connect(self.on_layout_changed)

        # Add widgets to BasicEditor layout (QVBoxLayout)
        self.addWidget(scroll_area)
        self.addWidget(control_panel)

    def eventFilter(self, obj, event):
        """Filter events to track hover state for keyboard widget"""
        if event.type() == QEvent.Enter:
            if obj == self.container:
                # Show keymap when hovering over keyboard
                self.showing_keymap = True
                self.refresh_layer_display()
        elif event.type() == QEvent.Leave:
            if obj == self.container:
                # Revert to tab-based display when leaving keyboard
                self.showing_keymap = False
                self.refresh_layer_display()

        return super().eventFilter(obj, event)

    def create_control_panel(self):
        """Create the bottom control panel"""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setMaximumHeight(500)  # Increased to allow more expansion for rapidfire mode
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(15, 3, 15, 8)

        # Create settings content directly (no tabs)
        settings_widget = self.create_settings_content()
        layout.addWidget(settings_widget)

        # Buttons moved to selection section, so removed from here

        panel.setLayout(layout)
        return panel

    def create_trigger_container(self):
        """Create the trigger travel configuration container"""
        container = QFrame()
        container.setFrameShape(QFrame.StyledPanel)
        container.setStyleSheet("QFrame { background-color: palette(base); }")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # Global actuation widget (shown when per-key mode is disabled)
        self.global_actuation_widget = QWidget()
        global_actuation_layout = QVBoxLayout()
        global_actuation_layout.setSpacing(6)
        global_actuation_layout.setContentsMargins(0, 0, 0, 0)

        # Normal Keys Actuation slider
        normal_layout = QVBoxLayout()
        normal_header = QHBoxLayout()
        normal_label = QLabel(tr("TriggerSettings", "Normal Keys"))
        normal_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; }")
        normal_header.addWidget(normal_label)
        normal_header.addStretch()
        self.global_normal_value_label = QLabel("2.00mm")
        self.global_normal_value_label.setStyleSheet("QLabel { font-weight: bold; color: #ff8c32; }")
        normal_header.addWidget(self.global_normal_value_label)
        normal_layout.addLayout(normal_header)

        self.global_normal_slider = StyledSlider(minimum=0, maximum=100)
        self.global_normal_slider.setValue(80)
        self.global_normal_slider.valueChanged.connect(self.on_global_normal_changed)
        self.global_normal_slider.setMinimumHeight(50)
        normal_layout.addWidget(self.global_normal_slider)

        global_actuation_layout.addLayout(normal_layout)

        # MIDI Keys Actuation slider
        midi_layout = QVBoxLayout()
        midi_header = QHBoxLayout()
        midi_label = QLabel(tr("TriggerSettings", "MIDI Keys"))
        midi_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; }")
        midi_header.addWidget(midi_label)
        midi_header.addStretch()
        self.global_midi_value_label = QLabel("2.00mm")
        self.global_midi_value_label.setStyleSheet("QLabel { font-weight: bold; color: #ff8c32; }")
        midi_header.addWidget(self.global_midi_value_label)
        midi_layout.addLayout(midi_header)

        self.global_midi_slider = StyledSlider(minimum=0, maximum=100)
        self.global_midi_slider.setValue(80)
        self.global_midi_slider.valueChanged.connect(self.on_global_midi_changed)
        self.global_midi_slider.setMinimumHeight(50)
        midi_layout.addWidget(self.global_midi_slider)

        global_actuation_layout.addLayout(midi_layout)

        self.global_actuation_widget.setLayout(global_actuation_layout)
        self.global_actuation_widget.setVisible(True)
        layout.addWidget(self.global_actuation_widget)

        # Per-Key Trigger Travel widget
        self.per_key_actuation_widget = QWidget()
        per_key_layout = QVBoxLayout()
        per_key_layout.setSpacing(6)
        per_key_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title_label = QLabel("Trigger Travel")
        title_label.setStyleSheet("QLabel { font-weight: bold; font-size: 10pt; }")
        per_key_layout.addWidget(title_label)

        # Value display row
        values_layout = QHBoxLayout()

        # Deadzone bottom
        dz_bottom_container = QVBoxLayout()
        dz_bottom_title = QLabel("DZ Min")
        dz_bottom_title.setStyleSheet("QLabel { color: gray; font-size: 7pt; }")
        self.deadzone_bottom_value_label = QLabel("0.1mm")
        self.deadzone_bottom_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; }")
        dz_bottom_container.addWidget(dz_bottom_title, 0, Qt.AlignCenter)
        dz_bottom_container.addWidget(self.deadzone_bottom_value_label, 0, Qt.AlignCenter)
        values_layout.addLayout(dz_bottom_container)

        values_layout.addStretch()

        # Actuation
        actuation_container = QVBoxLayout()
        actuation_title = QLabel("Actuation")
        actuation_title.setStyleSheet("QLabel { color: gray; font-size: 7pt; }")
        self.actuation_value_label = QLabel("1.5mm")
        self.actuation_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 10pt; color: #ff8c32; }")
        actuation_container.addWidget(actuation_title, 0, Qt.AlignCenter)
        actuation_container.addWidget(self.actuation_value_label, 0, Qt.AlignCenter)
        values_layout.addLayout(actuation_container)

        values_layout.addStretch()

        # Deadzone top
        dz_top_container = QVBoxLayout()
        dz_top_title = QLabel("DZ Max")
        dz_top_title.setStyleSheet("QLabel { color: gray; font-size: 7pt; }")
        self.deadzone_top_value_label = QLabel("0.1mm")
        self.deadzone_top_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; }")
        dz_top_container.addWidget(dz_top_title, 0, Qt.AlignCenter)
        dz_top_container.addWidget(self.deadzone_top_value_label, 0, Qt.AlignCenter)
        values_layout.addLayout(dz_top_container)

        per_key_layout.addLayout(values_layout)

        # Combined trigger slider
        self.trigger_slider = TriggerSlider(minimum=0, maximum=100)
        self.trigger_slider.setEnabled(False)
        self.trigger_slider.deadzoneBottomChanged.connect(self.on_deadzone_bottom_changed)
        self.trigger_slider.actuationChanged.connect(self.on_key_actuation_changed)
        self.trigger_slider.deadzoneTopChanged.connect(self.on_deadzone_top_changed)
        self.trigger_slider.setMinimumHeight(50)
        per_key_layout.addWidget(self.trigger_slider)

        self.per_key_actuation_widget.setLayout(per_key_layout)
        self.per_key_actuation_widget.setVisible(False)
        layout.addWidget(self.per_key_actuation_widget)

        # Add spacer to push everything to the top
        layout.addStretch()

        container.setLayout(layout)
        return container

    def create_rapidfire_container(self):
        """Create the rapidfire configuration container"""
        container = QFrame()
        container.setFrameShape(QFrame.StyledPanel)
        container.setStyleSheet("QFrame { background-color: palette(base); }")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # Enable checkbox container for centering
        self.rapidfire_checkbox_container = QWidget()
        checkbox_container_layout = QVBoxLayout()
        checkbox_container_layout.setContentsMargins(0, 0, 0, 0)

        # Enable checkbox
        self.rapidfire_checkbox = QCheckBox(tr("TriggerSettings", "Enable Rapidfire"))
        self.rapidfire_checkbox.setEnabled(False)
        self.rapidfire_checkbox.stateChanged.connect(self.on_rapidfire_toggled)
        # Make it bigger and bold when unchecked - will be updated in on_rapidfire_toggled
        self.rapidfire_checkbox.setStyleSheet("QCheckBox { font-size: 14pt; font-weight: bold; }")

        checkbox_container_layout.addStretch()
        checkbox_container_layout.addWidget(self.rapidfire_checkbox, 0, Qt.AlignCenter)
        checkbox_container_layout.addStretch()

        self.rapidfire_checkbox_container.setLayout(checkbox_container_layout)
        layout.addWidget(self.rapidfire_checkbox_container)

        # Rapidfire widget
        self.rf_widget = QWidget()
        rf_layout = QVBoxLayout()
        rf_layout.setSpacing(6)
        rf_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        rf_title = QLabel("Rapid Trigger")
        rf_title.setStyleSheet("QLabel { font-weight: bold; font-size: 10pt; }")
        rf_layout.addWidget(rf_title)

        # Value display row
        rf_values_layout = QHBoxLayout()

        # Press sensitivity
        press_container = QVBoxLayout()
        press_title = QLabel("Press")
        press_title.setStyleSheet("QLabel { color: gray; font-size: 7pt; }")
        self.rf_press_value_label = QLabel("0.1mm")
        self.rf_press_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; color: #ff8c32; }")
        press_container.addWidget(press_title, 0, Qt.AlignCenter)
        press_container.addWidget(self.rf_press_value_label, 0, Qt.AlignCenter)
        rf_values_layout.addLayout(press_container)

        rf_values_layout.addStretch()

        # Release sensitivity
        release_container = QVBoxLayout()
        release_title = QLabel("Release")
        release_title.setStyleSheet("QLabel { color: gray; font-size: 7pt; }")
        self.rf_release_value_label = QLabel("0.1mm")
        self.rf_release_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; color: #64c8ff; }")
        release_container.addWidget(release_title, 0, Qt.AlignCenter)
        release_container.addWidget(self.rf_release_value_label, 0, Qt.AlignCenter)
        rf_values_layout.addLayout(release_container)

        rf_layout.addLayout(rf_values_layout)

        # Combined rapid trigger slider
        self.rapid_trigger_slider = RapidTriggerSlider(minimum=1, maximum=100)
        self.rapid_trigger_slider.setEnabled(False)
        self.rapid_trigger_slider.pressSensChanged.connect(self.on_rf_press_changed)
        self.rapid_trigger_slider.releaseSensChanged.connect(self.on_rf_release_changed)
        self.rapid_trigger_slider.setMinimumHeight(50)
        rf_layout.addWidget(self.rapid_trigger_slider)

        # Velocity modifier
        rf_vel_layout = QVBoxLayout()
        rf_vel_header = QHBoxLayout()
        rf_vel_label = QLabel("Velocity Mod")
        rf_vel_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; }")
        rf_vel_header.addWidget(rf_vel_label)
        self.rf_vel_mod_value_label = QLabel("0")
        self.rf_vel_mod_value_label.setStyleSheet("QLabel { font-weight: bold; color: #ff8c32; margin-left: 8px; }")
        rf_vel_header.addWidget(self.rf_vel_mod_value_label)
        rf_vel_header.addStretch()
        rf_vel_layout.addLayout(rf_vel_header)

        self.rf_vel_mod_slider = StyledSlider(minimum=-64, maximum=64)
        self.rf_vel_mod_slider.setValue(0)
        self.rf_vel_mod_slider.setEnabled(False)
        self.rf_vel_mod_slider.valueChanged.connect(self.on_rf_vel_mod_changed)
        self.rf_vel_mod_slider.setMinimumHeight(50)
        rf_vel_layout.addWidget(self.rf_vel_mod_slider)

        rf_layout.addLayout(rf_vel_layout)

        self.rf_widget.setLayout(rf_layout)
        self.rf_widget.setVisible(False)
        layout.addWidget(self.rf_widget)

        container.setLayout(layout)
        return container

    def create_settings_content(self):
        """Create the settings content with tabbed layout and visualization"""
        widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(5, 3, 5, 5)

        # Left side: Tabbed settings container
        tabs_container = QFrame()
        tabs_container.setFrameShape(QFrame.StyledPanel)
        tabs_container.setStyleSheet("QFrame { background-color: palette(alternate-base); }")
        tabs_layout = QVBoxLayout()
        tabs_layout.setSpacing(6)
        tabs_layout.setContentsMargins(10, 10, 10, 10)

        # Create tab widget
        self.settings_tabs = QTabWidget()
        self.settings_tabs.currentChanged.connect(self.on_tab_changed)

        # Actuation Tab
        actuation_tab = QWidget()
        actuation_layout = QVBoxLayout()
        actuation_layout.setContentsMargins(8, 8, 8, 8)

        self.trigger_container = self.create_trigger_container()
        actuation_layout.addWidget(self.trigger_container)
        actuation_layout.addStretch()

        actuation_tab.setLayout(actuation_layout)
        self.settings_tabs.addTab(actuation_tab, "Actuation")

        # Rapidfire Tab
        rapidfire_tab = QWidget()
        rapidfire_layout = QVBoxLayout()
        rapidfire_layout.setContentsMargins(8, 8, 8, 8)

        self.rapidfire_container = self.create_rapidfire_container()
        rapidfire_layout.addWidget(self.rapidfire_container)
        rapidfire_layout.addStretch()

        rapidfire_tab.setLayout(rapidfire_layout)
        self.settings_tabs.addTab(rapidfire_tab, "Rapidfire")

        # Velocity Curve Tab
        velocity_tab = QWidget()
        velocity_layout = QVBoxLayout()
        velocity_layout.setContentsMargins(8, 8, 8, 8)

        # Use Per-Key Velocity Curve checkbox
        self.use_per_key_curve_checkbox = QCheckBox(tr("TriggerSettings", "Use Per-Key Velocity Curve"))
        self.use_per_key_curve_checkbox.setToolTip("When enabled, this key uses its own velocity curve.")
        self.use_per_key_curve_checkbox.setEnabled(False)
        self.use_per_key_curve_checkbox.stateChanged.connect(self.on_use_per_key_curve_changed)
        velocity_layout.addWidget(self.use_per_key_curve_checkbox)

        # Velocity Curve Editor
        from widgets.curve_editor import CurveEditorWidget
        self.velocity_curve_editor = CurveEditorWidget(show_save_button=True)
        self.velocity_curve_editor.setEnabled(False)
        self.velocity_curve_editor.curve_changed.connect(self.on_velocity_curve_changed)
        self.velocity_curve_editor.save_to_user_requested.connect(self.on_save_velocity_curve_to_user)
        velocity_layout.addWidget(self.velocity_curve_editor)
        velocity_layout.addStretch()

        velocity_tab.setLayout(velocity_layout)
        self.settings_tabs.addTab(velocity_tab, "Velocity Curve")

        tabs_layout.addWidget(self.settings_tabs)
        tabs_container.setLayout(tabs_layout)
        main_layout.addWidget(tabs_container, 2)

        # Right side: Visualization container (crossection + actuation visualizer)
        viz_container = QFrame()
        viz_container.setFrameShape(QFrame.StyledPanel)
        viz_container.setStyleSheet("QFrame { background-color: palette(base); }")
        viz_layout = QVBoxLayout()
        viz_layout.setContentsMargins(10, 10, 10, 10)
        viz_layout.setSpacing(10)

        # Import widgets from dks_settings
        from editor.dks_settings import KeyswitchDiagramWidget, VerticalTravelBarWidget

        # Horizontal layout for diagram and travel bar
        viz_h_layout = QHBoxLayout()

        # Keyswitch diagram
        self.keyswitch_diagram = KeyswitchDiagramWidget()
        viz_h_layout.addWidget(self.keyswitch_diagram)

        # Vertical travel bar
        self.actuation_visualizer = VerticalTravelBarWidget()
        viz_h_layout.addWidget(self.actuation_visualizer)

        viz_layout.addLayout(viz_h_layout)
        viz_layout.addStretch()

        viz_container.setLayout(viz_layout)
        main_layout.addWidget(viz_container, 1)

        widget.setLayout(main_layout)
        return widget

    def on_tab_changed(self, index):
        """Handle tab change - update active_tab and refresh display"""
        tab_names = ['actuation', 'rapidfire', 'velocity']
        if index >= 0 and index < len(tab_names):
            self.active_tab = tab_names[index]
            self.refresh_layer_display()
            self.update_actuation_visualizer()

    def update_actuation_visualizer(self):
        """Update the actuation visualizer based on current tab and selected key"""
        if not hasattr(self, 'actuation_visualizer'):
            return

        # Get current layer
        layer = self.current_layer if self.per_layer_enabled else 0

        # Get active key if selected
        if self.container.active_key and self.container.active_key.desc.row is not None:
            row, col = self.container.active_key.desc.row, self.container.active_key.desc.col
            key_index = row * 14 + col
            if key_index < 70:
                settings = self.per_key_values[layer][key_index]

                # Build actuation points based on active tab
                if self.active_tab == 'actuation':
                    # Show actuation point and deadzones
                    press_points = [(settings['actuation'], True)]
                    # Deadzones aren't shown as separate actuation points in the visualizer
                    release_points = []
                elif self.active_tab == 'rapidfire':
                    # Show rapidfire press/release sensitivities if enabled
                    rapidfire_enabled = (settings['flags'] & 0x01) != 0
                    if rapidfire_enabled:
                        press_points = [(settings['rapidfire_press_sens'], True)]
                        release_points = [(settings['rapidfire_release_sens'], True)]
                    else:
                        press_points = []
                        release_points = []
                elif self.active_tab == 'velocity':
                    # Show actuation point for velocity curve reference
                    press_points = [(settings['actuation'], True)]
                    release_points = []
                else:
                    press_points = []
                    release_points = []

                self.actuation_visualizer.set_actuations(press_points, release_points)
                return

        # No key selected or in global mode - show global actuation
        if not self.mode_enabled:
            data_source = self.pending_layer_data if self.pending_layer_data else self.layer_data
            layer_to_use = self.current_layer if self.per_layer_enabled else 0

            if self.active_tab == 'actuation':
                # Show both normal and MIDI actuation points
                press_points = [
                    (data_source[layer_to_use]['normal'], True),
                    (data_source[layer_to_use]['midi'], True)
                ]
                release_points = []
            else:
                # Rapidfire and velocity tabs don't apply to global mode
                press_points = []
                release_points = []

            self.actuation_visualizer.set_actuations(press_points, release_points)
        else:
            # Per-key mode but no key selected - clear visualizer
            self.actuation_visualizer.set_actuations([], [])

    def value_to_mm(self, value):
        """Convert 0-100 value to millimeters string"""
        mm = (value / 40.0)  # 0-100 maps to 0-2.5mm (100/40 = 2.5)
        return f"{mm:.2f}mm"

    def on_global_normal_changed(self, value):
        """Handle global normal actuation slider change"""
        self.global_normal_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Initialize pending data if not already
        if self.pending_layer_data is None:
            self.pending_layer_data = []
            for layer_data in self.layer_data:
                self.pending_layer_data.append(layer_data.copy())

        # Update pending_layer_data for current layer (or all layers if not per-layer)
        layer = self.current_layer if self.per_layer_enabled else 0

        if self.per_layer_enabled:
            # Update only current layer
            self.pending_layer_data[layer]['normal'] = value
        else:
            # Update all layers
            for i in range(12):
                self.pending_layer_data[i]['normal'] = value

        # Mark as having unsaved changes
        self.has_unsaved_changes = True
        self.save_btn.setEnabled(True)

        # Update display to show pending value
        self.refresh_layer_display()
        self.update_actuation_visualizer()

    def on_global_midi_changed(self, value):
        """Handle global MIDI actuation slider change"""
        self.global_midi_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Initialize pending data if not already
        if self.pending_layer_data is None:
            self.pending_layer_data = []
            for layer_data in self.layer_data:
                self.pending_layer_data.append(layer_data.copy())

        # Update pending_layer_data for current layer (or all layers if not per-layer)
        layer = self.current_layer if self.per_layer_enabled else 0

        if self.per_layer_enabled:
            # Update only current layer
            self.pending_layer_data[layer]['midi'] = value
        else:
            # Update all layers
            for i in range(12):
                self.pending_layer_data[i]['midi'] = value

        # Mark as having unsaved changes
        self.has_unsaved_changes = True
        self.save_btn.setEnabled(True)

        # Update display to show pending value
        self.refresh_layer_display()
        self.update_actuation_visualizer()

    def on_save(self):
        """Save pending global actuation changes to device"""
        if not self.has_unsaved_changes or self.pending_layer_data is None:
            return

        # Apply pending changes to layer_data
        for i in range(12):
            self.layer_data[i]['normal'] = self.pending_layer_data[i]['normal']
            self.layer_data[i]['midi'] = self.pending_layer_data[i]['midi']

        # Send to device
        if self.device and isinstance(self.device, VialKeyboard):
            if self.per_layer_enabled:
                # Send all layers if per-layer is enabled
                for layer in range(12):
                    self.send_layer_actuation(layer)
            else:
                # Send only layer 0 if not per-layer
                self.send_layer_actuation(0)

        # Clear unsaved changes flag
        self.has_unsaved_changes = False
        self.pending_layer_data = None
        self.save_btn.setEnabled(False)

    def on_empty_space_clicked(self):
        """Deselect key when clicking empty space"""
        self.container.deselect()
        self.container.update()

    def on_key_clicked(self):
        """Handle key click - load all per-key settings"""
        if self.container.active_key is None:
            return

        key = self.container.active_key
        if key.desc.row is None:
            # Encoder, not a key
            return

        row, col = key.desc.row, key.desc.col
        key_index = row * 14 + col

        if key_index >= 70:
            return

        # Get current layer to use
        layer = self.current_layer if self.per_layer_enabled else 0

        # Load all settings from cache
        settings = self.per_key_values[layer][key_index]
        self.syncing = True

        # Load trigger slider (actuation + deadzones)
        self.trigger_slider.set_deadzone_bottom(settings['deadzone_bottom'])
        self.trigger_slider.set_actuation(settings['actuation'])
        self.trigger_slider.set_deadzone_top(settings['deadzone_top'])

        # Update labels
        self.deadzone_bottom_value_label.setText(self.value_to_mm(settings['deadzone_bottom']))
        self.actuation_value_label.setText(self.value_to_mm(settings['actuation']))
        self.deadzone_top_value_label.setText(self.value_to_mm(settings['deadzone_top']))

        # Load velocity curve (now supports 0-16 instead of 0-4)
        curve_index = settings.get('velocity_curve', 0)
        self.velocity_curve_editor.select_curve(curve_index)

        # Load rapidfire settings (extract bit 0 from flags)
        rapidfire_enabled = (settings['flags'] & 0x01) != 0
        self.rapidfire_checkbox.setChecked(rapidfire_enabled)

        # Load rapid trigger slider
        self.rapid_trigger_slider.set_press_sens(settings['rapidfire_press_sens'])
        self.rapid_trigger_slider.set_release_sens(settings['rapidfire_release_sens'])
        self.rf_press_value_label.setText(self.value_to_mm(settings['rapidfire_press_sens']))
        self.rf_release_value_label.setText(self.value_to_mm(settings['rapidfire_release_sens']))

        # Load velocity modifier
        self.rf_vel_mod_slider.setValue(settings['rapidfire_velocity_mod'])
        self.rf_vel_mod_value_label.setText(str(settings['rapidfire_velocity_mod']))

        # Load per-key velocity curve checkbox (extract bit 1 from flags)
        use_per_key_curve = (settings['flags'] & 0x02) != 0
        self.use_per_key_curve_checkbox.setChecked(use_per_key_curve)

        self.syncing = False

        # Enable controls when key is selected
        key_selected = self.container.active_key is not None
        self.trigger_slider.setEnabled(key_selected and self.mode_enabled)
        self.use_per_key_curve_checkbox.setEnabled(key_selected)
        self.velocity_curve_editor.setEnabled(key_selected and use_per_key_curve)
        self.rapidfire_checkbox.setEnabled(key_selected)
        self.rapid_trigger_slider.setEnabled(key_selected and rapidfire_enabled)
        self.rf_widget.setVisible(rapidfire_enabled)
        self.rf_vel_mod_slider.setEnabled(key_selected and rapidfire_enabled)

        # Update actuation visualizer
        self.update_actuation_visualizer()

    def on_key_deselected(self):
        """Handle key deselection - disable all controls"""
        self.trigger_slider.setEnabled(False)
        self.velocity_curve_editor.setEnabled(False)
        self.rapidfire_checkbox.setEnabled(False)
        self.rapid_trigger_slider.setEnabled(False)
        self.rf_vel_mod_slider.setEnabled(False)
        self.rf_widget.setVisible(False)

        # Update actuation visualizer
        self.update_actuation_visualizer()

    def save_current_key_settings(self):
        """Helper to save current key's settings to device"""
        if not self.container.active_key or self.container.active_key.desc.row is None:
            return

        row = self.container.active_key.desc.row
        col = self.container.active_key.desc.col
        key_index = row * 14 + col

        if key_index >= 70:
            return

        layer = self.current_layer if self.per_layer_enabled else 0
        settings = self.per_key_values[layer][key_index]

        # Send to device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        # Refresh display
        self.refresh_layer_display()

    def on_key_actuation_changed(self, value):
        """Handle key actuation slider value change - applies to all selected keys"""
        self.actuation_value_label.setText(self.value_to_mm(value))

        if self.syncing or not self.mode_enabled:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['actuation'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_velocity_curve_changed(self, points):
        """Handle velocity curve change - applies to all selected keys (NO AUTO-SAVE)"""
        if self.syncing:
            return

        # Get curve index from preset combo (0-16 or -1 for custom)
        curve_index = self.velocity_curve_editor.preset_combo.currentData()
        if curve_index is None or curve_index < 0:
            curve_index = 0  # Default to linear if custom

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys (in memory only - no auto-save)
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['velocity_curve'] = curve_index

        # Mark as having unsaved changes
        self.has_unsaved_changes = True
        self.save_btn.setEnabled(True)

        self.refresh_layer_display()
        self.update_actuation_visualizer()

    def on_save_velocity_curve_to_user(self, slot_index, curve_name):
        """Called when user wants to save current velocity curve to a user slot"""
        if not self.device or not isinstance(self.device, VialKeyboard):
            return

        try:
            # Get current curve points from editor
            points = self.velocity_curve_editor.get_points()

            # Save to keyboard
            success = self.device.keyboard.set_user_curve(slot_index, points, curve_name)

            if success:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(None, "Success", f"Velocity curve saved to {curve_name}")

                # Reload user curve names
                user_curve_names = self.device.keyboard.get_all_user_curve_names()
                if user_curve_names and len(user_curve_names) == 10:
                    self.velocity_curve_editor.set_user_curve_names(user_curve_names)

                # Select the newly saved curve (curve index = 7 + slot_index)
                self.velocity_curve_editor.select_curve(7 + slot_index)

                # Update the velocity curve index for selected keys
                self.on_velocity_curve_changed(points)
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Error saving velocity curve: {str(e)}")

    def on_deadzone_top_changed(self, value):
        """Handle top deadzone slider change - applies to all selected keys"""
        self.deadzone_top_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['deadzone_top'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()
        self.update_actuation_visualizer()

    def on_deadzone_bottom_changed(self, value):
        """Handle bottom deadzone slider change - applies to all selected keys"""
        self.deadzone_bottom_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['deadzone_bottom'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()
        self.update_actuation_visualizer()

    def on_rapidfire_toggled(self, state):
        """Handle rapidfire checkbox toggle"""
        enabled = (state == Qt.Checked)

        # Update checkbox styling based on state
        if enabled:
            # When checked: normal size, left-aligned
            self.rapidfire_checkbox.setStyleSheet("QCheckBox { font-size: 9pt; font-weight: normal; }")
            # Clear the checkbox container layout and re-add without centering
            for i in reversed(range(self.rapidfire_checkbox_container.layout().count())):
                item = self.rapidfire_checkbox_container.layout().itemAt(i)
                if item.widget():
                    item.widget().setParent(None)
                elif item.spacerItem():
                    self.rapidfire_checkbox_container.layout().removeItem(item)
            self.rapidfire_checkbox_container.layout().addWidget(self.rapidfire_checkbox)
        else:
            # When unchecked: bigger, bold, centered
            self.rapidfire_checkbox.setStyleSheet("QCheckBox { font-size: 14pt; font-weight: bold; }")
            # Clear and re-add with centering
            for i in reversed(range(self.rapidfire_checkbox_container.layout().count())):
                item = self.rapidfire_checkbox_container.layout().itemAt(i)
                if item.widget():
                    item.widget().setParent(None)
                elif item.spacerItem():
                    self.rapidfire_checkbox_container.layout().removeItem(item)
            self.rapidfire_checkbox_container.layout().addStretch()
            self.rapidfire_checkbox_container.layout().addWidget(self.rapidfire_checkbox, 0, Qt.AlignCenter)
            self.rapidfire_checkbox_container.layout().addStretch()

        if not self.syncing:
            # Show/hide rapidfire widget and enable sliders
            self.rf_widget.setVisible(enabled)
            self.rapid_trigger_slider.setEnabled(enabled)
            self.rf_vel_mod_slider.setEnabled(enabled)

            # Get all selected keys (or just active key if none selected)
            selected_keys = self.container.get_selected_keys()
            if not selected_keys and self.container.active_key:
                selected_keys = [self.container.active_key]

            layer = self.current_layer if self.per_layer_enabled else 0

            # Apply to all selected keys
            for key in selected_keys:
                if key.desc.row is not None:
                    row, col = key.desc.row, key.desc.col
                    key_index = row * 14 + col

                    if key_index < 70:
                        # Update flags field: set or clear bit 0
                        if enabled:
                            self.per_key_values[layer][key_index]['flags'] |= 0x01  # Set bit 0
                        else:
                            self.per_key_values[layer][key_index]['flags'] &= ~0x01  # Clear bit 0

                        # Send to device
                        if self.device and isinstance(self.device, VialKeyboard):
                            settings = self.per_key_values[layer][key_index]
                            self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

            self.refresh_layer_display()
            self.update_actuation_visualizer()

    def on_rf_press_changed(self, value):
        """Handle rapidfire press sensitivity slider change - applies to all selected keys"""
        self.rf_press_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['rapidfire_press_sens'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()
        self.update_actuation_visualizer()

    def on_rf_release_changed(self, value):
        """Handle rapidfire release sensitivity slider change - applies to all selected keys"""
        self.rf_release_value_label.setText(self.value_to_mm(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['rapidfire_release_sens'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()
        self.update_actuation_visualizer()

    def on_rf_vel_mod_changed(self, value):
        """Handle rapidfire velocity modifier slider change - applies to all selected keys"""
        self.rf_vel_mod_value_label.setText(str(value))

        if self.syncing:
            return

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    self.per_key_values[layer][key_index]['rapidfire_velocity_mod'] = value
                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        self.refresh_layer_display()

    def on_use_per_key_curve_changed(self, state):
        """Handle 'Use Per-Key Velocity Curve' checkbox toggle (per-key setting)"""
        if self.syncing:
            return

        enabled = (state == Qt.Checked)

        # Get all selected keys (or just active key if none selected)
        selected_keys = self.container.get_selected_keys()
        if not selected_keys and self.container.active_key:
            selected_keys = [self.container.active_key]

        layer = self.current_layer if self.per_layer_enabled else 0

        # Apply to all selected keys
        for key in selected_keys:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    # Update flags field: set or clear bit 1
                    if enabled:
                        self.per_key_values[layer][key_index]['flags'] |= 0x02  # Set bit 1
                    else:
                        self.per_key_values[layer][key_index]['flags'] &= ~0x02  # Clear bit 1

                    # Send to device
                    if self.device and isinstance(self.device, VialKeyboard):
                        settings = self.per_key_values[layer][key_index]
                        self.device.keyboard.set_per_key_actuation(layer, key_index, settings)

        # Enable/disable velocity curve editor based on this flag
        self.velocity_curve_editor.setEnabled(enabled)
        self.refresh_layer_display()

    def send_layer_actuation(self, layer):
        """Send layer actuation settings to device"""
        data = self.layer_data[layer]

        # Build flags byte (no velocity curve flag - that's now per-key)
        flags = 0
        # Bit 2 (use_fixed_velocity) is set in the actuation settings tab, not here

        # Build payload: [layer, normal, midi, velocity, vel_speed, flags] (6 bytes)
        payload = bytes([
            layer,
            data['normal'],
            data['midi'],
            data['velocity'],
            data['vel_speed'],
            flags
        ])

        # Send to device
        self.device.keyboard.set_layer_actuation(payload)

    def on_enable_changed(self, state):
        """Handle enable checkbox toggle"""
        if self.syncing:
            return

        self.mode_enabled = (state == Qt.Checked)
        # Keep per_layer_checkbox always enabled (arrays are not mutually exclusive)
        self.copy_layer_btn.setEnabled(self.mode_enabled)
        self.copy_all_layers_btn.setEnabled(self.mode_enabled)
        self.reset_btn.setEnabled(self.mode_enabled)

        # Toggle between global and per-key actuation sliders only
        self.global_actuation_widget.setVisible(not self.mode_enabled)
        self.per_key_actuation_widget.setVisible(self.mode_enabled)

        # Load appropriate values for the visible widget
        if not self.mode_enabled:
            # Load global actuation values
            self.load_global_actuation()

        # Update enabled state of trigger slider when in per-key mode
        if self.mode_enabled:
            key_selected = self.container.active_key is not None
            self.trigger_slider.setEnabled(key_selected)

        # Update device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_mode(self.mode_enabled, self.per_layer_enabled)

        self.refresh_layer_display()

    def update_slider_states(self):
        """Update slider visibility based on per-key mode (no-op since we removed old sliders)"""
        # All controls are now in the per-key settings tab
        pass

    def on_per_layer_changed(self, state):
        """Handle per-layer checkbox toggle"""
        if self.syncing:
            return

        self.per_layer_enabled = (state == Qt.Checked)

        # Update device
        if self.device and isinstance(self.device, VialKeyboard):
            self.device.keyboard.set_per_key_mode(self.mode_enabled, self.per_layer_enabled)

        # Synchronize with Actuation Settings tab
        if self.actuation_widget_ref:
            self.actuation_widget_ref.syncing = True
            self.actuation_widget_ref.per_layer_checkbox.setChecked(self.per_layer_enabled)
            self.actuation_widget_ref.syncing = False

        self.refresh_layer_display()

    def on_copy_layer(self):
        """Show dialog to copy actuations from another layer"""
        if not self.mode_enabled:
            return

        # Create simple combo box dialog
        msg = QMessageBox(self.widget())
        msg.setWindowTitle(tr("TriggerSettings", "Copy Layer"))
        msg.setText(tr("TriggerSettings", "Copy actuation settings from which layer?"))

        combo = QComboBox()
        for i in range(12):
            combo.addItem(f"Layer {i}", i)
        combo.setCurrentIndex(0 if self.current_layer == 0 else 0)

        msg.layout().addWidget(combo, 1, 1)
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        if msg.exec_() == QMessageBox.Ok:
            source_layer = combo.currentData()
            dest_layer = self.current_layer

            # Copy in memory (deep copy of dicts)
            for key_index in range(70):
                self.per_key_values[dest_layer][key_index] = self.per_key_values[source_layer][key_index].copy()

            # Copy on device
            if self.device and isinstance(self.device, VialKeyboard):
                self.device.keyboard.copy_layer_actuations(source_layer, dest_layer)

            self.refresh_layer_display()

    def on_copy_to_all_layers(self):
        """Copy current layer's per-key settings to all layers"""
        if not self.mode_enabled:
            return

        ret = QMessageBox.question(
            self.widget(),
            tr("TriggerSettings", "Copy to All Layers"),
            tr("TriggerSettings", f"Copy per-key settings from Layer {self.current_layer} to all layers?"),
            QMessageBox.Yes | QMessageBox.No
        )

        if ret == QMessageBox.Yes:
            source_layer = self.current_layer

            # Copy to all layers in memory and on device
            for dest_layer in range(12):
                if dest_layer != source_layer:
                    # Copy in memory (deep copy of dicts)
                    for key_index in range(70):
                        self.per_key_values[dest_layer][key_index] = self.per_key_values[source_layer][key_index].copy()

                    # Copy on device
                    if self.device and isinstance(self.device, VialKeyboard):
                        self.device.keyboard.copy_layer_actuations(source_layer, dest_layer)

            self.refresh_layer_display()
            QMessageBox.information(
                self.widget(),
                tr("TriggerSettings", "Copy Complete"),
                tr("TriggerSettings", f"Per-key settings copied to all layers.")
            )

    def on_reset_all(self):
        """Reset all actuations to default with confirmation"""
        ret = QMessageBox.question(
            self.widget(),
            tr("TriggerSettings", "Reset All"),
            tr("TriggerSettings", "Reset all per-key actuations to default (1.5mm)?"),
            QMessageBox.Yes | QMessageBox.No
        )

        if ret == QMessageBox.Yes:
            # Reset in memory to defaults (deadzones always enabled)
            for layer in range(12):
                for key_index in range(70):
                    self.per_key_values[layer][key_index] = {
                        'actuation': 60,                    # 1.5mm
                        'deadzone_top': 4,                  # 0.1mm from right
                        'deadzone_bottom': 4,               # 0.1mm from left
                        'velocity_curve': 2,                # Medium
                        'flags': 0,                         # Both rapidfire and per-key velocity curve disabled
                        'rapidfire_press_sens': 4,          # 0.1mm from left
                        'rapidfire_release_sens': 4,        # 0.1mm from right
                        'rapidfire_velocity_mod': 0         # No modifier
                    }

            # Reset on device
            if self.device and isinstance(self.device, VialKeyboard):
                self.device.keyboard.reset_per_key_actuations()

            self.refresh_layer_display()

    def rebuild_layers(self):
        """Create layer selection buttons"""
        # Delete old buttons
        for btn in self.layer_buttons:
            btn.hide()
            btn.deleteLater()
        self.layer_buttons = []

        # Create layer buttons
        for x in range(self.keyboard.layers):
            btn = SquareButton(str(x))
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setRelSize(2.0)  # Increased from 1.667 to 2.0 for bigger buttons
            btn.setCheckable(True)
            btn.clicked.connect(lambda state, idx=x: self.switch_layer(idx))
            self.layout_layers.addWidget(btn)
            self.layer_buttons.append(btn)

        # Size adjustment buttons
        for x in range(0, 2):
            btn = SquareButton("-") if x else SquareButton("+")
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setRelSize(2.0)  # Increased from 1.667 to 2.0 for bigger buttons
            btn.setCheckable(False)
            btn.clicked.connect(lambda state, idx=x: self.adjust_size(idx))
            self.layout_size.addWidget(btn)
            self.layer_buttons.append(btn)

    def adjust_size(self, minus):
        """Adjust keyboard display size"""
        if minus:
            self.container.set_scale(self.container.get_scale() - 0.1)
        else:
            self.container.set_scale(self.container.get_scale() + 0.1)
        self.refresh_layer_display()

    def switch_layer(self, layer):
        """Switch to a different layer"""
        self.current_layer = layer
        for idx, btn in enumerate(self.layer_buttons[:self.keyboard.layers]):
            btn.setChecked(idx == layer)

        # Load layer data into controls
        self.load_layer_controls()

        self.refresh_layer_display()

    def load_layer_controls(self):
        """Load current layer's data into control widgets"""
        if not self.valid():
            return

        # Load global actuation values if per-key mode is disabled
        if not self.mode_enabled:
            self.load_global_actuation()

    def load_global_actuation(self):
        """Load global actuation values from layer_data"""
        if not self.valid():
            return

        self.syncing = True

        # Get layer to use
        layer = self.current_layer if self.per_layer_enabled else 0

        # Use pending data if available, otherwise use saved data
        data_source = self.pending_layer_data if self.pending_layer_data else self.layer_data

        # Load normal and MIDI actuation values
        self.global_normal_slider.setValue(data_source[layer]['normal'])
        self.global_normal_value_label.setText(self.value_to_mm(data_source[layer]['normal']))

        self.global_midi_slider.setValue(data_source[layer]['midi'])
        self.global_midi_value_label.setText(self.value_to_mm(data_source[layer]['midi']))

        self.syncing = False

    def on_layout_changed(self):
        """Handle layout change from layout editor"""
        self.refresh_layer_display()

    def rebuild(self, device):
        """Rebuild UI with new device"""
        print(f"TriggerSettingsTab.rebuild() called with device={device}")
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard

            self.rebuild_layers()
            self.container.set_keys(self.keyboard.keys, self.keyboard.encoders)
            self.current_layer = 0

            # Load mode flags from device
            mode_data = self.keyboard.get_per_key_mode()
            if mode_data:
                self.syncing = True
                self.mode_enabled = mode_data['mode_enabled']
                self.per_layer_enabled = mode_data['per_layer_enabled']
                self.enable_checkbox.setChecked(self.mode_enabled)
                self.per_layer_checkbox.setChecked(self.per_layer_enabled)
                # Keep per_layer_checkbox always enabled
                self.copy_layer_btn.setEnabled(self.mode_enabled)
                self.copy_all_layers_btn.setEnabled(self.mode_enabled)
                self.reset_btn.setEnabled(self.mode_enabled)
                self.syncing = False

            # Load all per-key values from device (now returns dict with 8 fields)
            # If communication fails or returns None, set safe defaults
            communication_failed = False
            try:
                for layer in range(12):
                    for key_index in range(70):
                        settings = self.keyboard.get_per_key_actuation(layer, key_index)
                        if settings is not None:
                            # get_per_key_actuation now returns a dict with all 8 fields
                            self.per_key_values[layer][key_index] = settings
                        else:
                            communication_failed = True
                            break
                    if communication_failed:
                        break
            except Exception as e:
                print(f"Error loading per-key actuations from device: {e}")
                communication_failed = True

            # If communication failed, set all keys to safe defaults
            if communication_failed:
                print("Setting all keys to safe defaults: 0.1mm deadzones, 2.0mm actuation")
                for layer in range(12):
                    for key_index in range(70):
                        self.per_key_values[layer][key_index] = {
                            'actuation': 80,                    # 2.0mm (80/40 = 2.0)
                            'deadzone_top': 4,                  # 0.1mm from right
                            'deadzone_bottom': 4,               # 0.1mm from left
                            'velocity_curve': 2,                # Medium
                            'flags': 0,                         # All disabled
                            'rapidfire_press_sens': 4,          # 0.1mm from left
                            'rapidfire_release_sens': 4,        # 0.1mm from right
                            'rapidfire_velocity_mod': 0         # No modifier
                        }

            # Load layer actuation data from device (6 bytes per layer)
            try:
                for layer in range(12):
                    data = self.keyboard.get_layer_actuation(layer)
                    if data:
                        self.layer_data[layer] = {
                            'normal': data['normal'],
                            'midi': data['midi'],
                            'velocity': data['velocity'],
                            'vel_speed': data['vel_speed']
                            # Removed: 'use_per_key_velocity_curve' - now per-key
                        }
            except Exception as e:
                print(f"Error loading layer actuations: {e}")

            # Clear any unsaved changes when loading from device
            self.has_unsaved_changes = False
            self.pending_layer_data = None
            self.save_btn.setEnabled(False)

            # Update slider states
            self.update_slider_states()

            # Load current layer data into controls
            self.load_layer_controls()

            self.refresh_layer_display()

            # Load user curve names for velocity curve editor
            try:
                user_curve_names = self.keyboard.get_all_user_curve_names()
                if user_curve_names and len(user_curve_names) == 10:
                    self.velocity_curve_editor.set_user_curve_names(user_curve_names)
            except Exception as e:
                print(f"Error loading user curve names: {e}")

        self.container.setEnabled(self.valid())

    def valid(self):
        """Check if device is valid"""
        result = isinstance(self.device, VialKeyboard)
        print(f"TriggerSettingsTab.valid() called: device={self.device}, result={result}")
        return result

    def refresh_layer_display(self):
        """Refresh keyboard display based on active tab and hover state"""
        if not self.valid():
            return

        # Update layer button highlighting
        for idx, btn in enumerate(self.layer_buttons[:self.keyboard.layers]):
            btn.setChecked(idx == self.current_layer)

        # Update keyboard key displays
        layer = self.current_layer if self.per_layer_enabled else 0

        # Use pending data if available, otherwise use saved data
        data_source = self.pending_layer_data if self.pending_layer_data else self.layer_data

        for key in self.container.widgets:
            if key.desc.row is not None:
                row, col = key.desc.row, key.desc.col
                key_index = row * 14 + col

                if key_index < 70:
                    # Get settings for this key
                    settings = self.per_key_values[layer][key_index]
                    rapidfire_enabled = (settings['flags'] & 0x01) != 0

                    # Default: clear mask text
                    key.setMaskText("")

                    # Display content based on showing_keymap flag and active tab
                    if self.showing_keymap:
                        # Hovering over keyboard: show keycodes like keymap tab
                        if self.keyboard and hasattr(self.keyboard, 'layout'):
                            code = self.keyboard.layout.get((self.current_layer, row, col), "KC_NO")
                            KeycodeDisplay.display_keycode(key, code)
                        else:
                            key.setText("")
                            key.setColor(None)
                    elif self.active_tab == 'rapidfire':
                        # Rapidfire tab: show press/release values or nothing
                        if rapidfire_enabled:
                            press_mm = self.value_to_mm(settings['rapidfire_press_sens'])
                            release_mm = self.value_to_mm(settings['rapidfire_release_sens'])
                            # Use same format as normal/midi display
                            key.setText(f"{press_mm}\n{release_mm}")
                            key.masked = False
                            key.setColor(None)
                        else:
                            key.setText("")
                            key.setColor(None)
                    elif self.active_tab == 'velocity':
                        # Velocity curve tab: show assigned curve or nothing
                        use_per_key_curve = (settings['flags'] & 0x02) != 0
                        if use_per_key_curve:
                            curve_idx = settings['velocity_curve']
                            if curve_idx == 0:
                                curve_name = "Linear"
                            elif curve_idx <= 6:
                                curve_name = f"F{curve_idx}"
                            else:
                                curve_name = f"U{curve_idx-6}"
                            key.setText(curve_name)
                            key.setColor(None)
                        else:
                            key.setText("")
                            key.setColor(None)
                    else:  # self.active_tab == 'actuation'
                        # Actuation tab: show actuation values
                        if rapidfire_enabled:
                            key.setColor(QColor(255, 140, 50))
                        else:
                            key.setColor(None)

                        if self.mode_enabled:
                            # Per-key mode: show per-key actuation value
                            key.setText(self.value_to_mm(settings['actuation']))
                        else:
                            # Global mode: show both Normal and MIDI actuation values
                            layer_to_use = self.current_layer if self.per_layer_enabled else 0
                            normal_value = data_source[layer_to_use]['normal']
                            midi_value = data_source[layer_to_use]['midi']
                            key.setText(f"{self.value_to_mm(normal_value)}\n{self.value_to_mm(midi_value)}")
                else:
                    key.setText("")

        self.container.update()

    def on_select_all(self):
        """Handle Select All button click"""
        self.container.select_all()

    def on_unselect_all(self):
        """Handle Unselect All button click"""
        self.container.unselect_all()

    def on_invert_selection(self):
        """Handle Invert Selection button click"""
        self.container.invert_selection()
