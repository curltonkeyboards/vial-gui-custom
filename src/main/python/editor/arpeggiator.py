# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import logging
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPalette
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                             QLabel, QGroupBox, QMessageBox, QGridLayout,
                             QComboBox, QSpinBox, QLineEdit, QScrollArea,
                             QFrame, QButtonGroup, QRadioButton, QCheckBox, QSlider,
                             QInputDialog, QTabWidget, QDialog, QDialogButtonBox)

from editor.basic_editor import BasicEditor
from util import tr
from vial_device import VialKeyboard
from widgets.combo_box import ArrowComboBox

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def flat_semitones_to_interval_octave(flat_semitones):
    """
    Convert flat semitones to (interval, octave) pair for firmware.
    Examples:
        +29 → (interval=+5, octave=+2)
        -1 → (interval=-1, octave=0)
        -13 → (interval=-1, octave=-1)
        +12 → (interval=0, octave=+1)
    """
    # Calculate octave (how many complete 12-semitone octaves)
    octave = flat_semitones // 12
    # Calculate interval within octave (-11 to +11)
    interval = flat_semitones % 12

    # Handle negative intervals properly
    # If we have a negative remainder, adjust
    if flat_semitones < 0 and interval != 0:
        octave -= 1
        interval = 12 + interval

    return interval, octave


def interval_octave_to_flat_semitones(interval, octave):
    """
    Convert (interval, octave) pair to flat semitones.
    Examples:
        (interval=+5, octave=+2) → +29
        (interval=-1, octave=0) → -1
        (interval=-1, octave=-1) → -13
        (interval=0, octave=+1) → +12
    """
    return interval + (octave * 12)


# =============================================================================
# GRID-BASED INTERFACE WIDGETS (for Basic Tab)
# =============================================================================

class GridCell(QFrame):
    """Individual grid cell for Basic tab - handles clicks and visual state"""

    leftClicked = pyqtSignal(int, int)  # row, col
    rightClicked = pyqtSignal(int, int)  # row, col

    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.active = False
        self.velocity = 255  # Default velocity (max)
        self.octave = 0  # For arpeggiator only
        self.in_scale = True  # Default to in scale (for scale filtering)

        # Set size based on whether this is step sequencer or arpeggiator
        if hasattr(parent, 'is_arpeggiator') and not parent.is_arpeggiator:
            # Step sequencer - 50x50
            self.setFixedSize(50, 50)
        else:
            # Arpeggiator - 20x20
            self.setFixedSize(20, 20)
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)

        self.update_style()

    def set_active(self, active, velocity=127, octave=0):
        """Set cell state"""
        self.active = active
        self.velocity = velocity
        self.octave = octave
        self.update_style()

    def get_octave_color(self):
        """Get color based on octave for arpeggiator - uses theme-relative hue shifts"""
        # Get theme highlight color as base
        palette = self.palette()
        highlight = palette.color(QPalette.Highlight)

        # Convert to HSV for hue shifting
        h = highlight.hsvHue()
        s = highlight.hsvSaturation()
        v = highlight.value()

        # Root octave (0) uses the theme color
        if self.octave == 0:
            return QColor(200, 200, 200)  # Neutral gray for root

        # Apply hue shift based on octave
        # Negative octaves shift hue one direction, positive the other
        # Each octave shifts hue by 30 degrees (360/12 for chromatic scale feel)
        hue_shift = self.octave * 30
        new_hue = (h + hue_shift) % 360

        # Adjust saturation and value based on octave distance from root
        # Further octaves = more saturated and slightly darker
        octave_distance = abs(self.octave)
        saturation_boost = min(255, s + (octave_distance * 30))
        value_adjust = max(128, v - (octave_distance * 10))

        color = QColor.fromHsv(new_hue, saturation_boost, value_adjust)
        return color if color.isValid() else QColor(200, 200, 200)

    def update_style(self):
        """Update visual appearance based on state"""
        # Check if this is the Base Note cell in arpeggiator (row 11, interval 0)
        is_root_note = hasattr(self.parent(), 'is_arpeggiator') and self.parent().is_arpeggiator and self.row == 11

        # Base Note row gets theme-based border (white on dark, black on light)
        if is_root_note:
            # Determine theme (light vs dark) based on window background
            palette = self.palette()
            bg_color = palette.color(QPalette.Window)
            # If background is light (luminance > 128), use black border, else white
            is_light_theme = bg_color.lightness() > 128
            border_color = "black" if is_light_theme else "white"
            border_width = 2
        else:
            border_color = "#666" if self.active else "#555"
            border_width = 1

        if self.active:
            # Get theme highlight color
            palette = self.palette()
            highlight = palette.color(QPalette.Highlight)

            # Intensity based on velocity (velocity is 0-255, display as 0-127)
            intensity = self.velocity / 255.0

            # For arpeggiator, blend with octave color
            if hasattr(self.parent(), 'is_arpeggiator') and self.parent().is_arpeggiator:
                octave_color = self.get_octave_color()
                # Blend octave color with intensity
                r = int(octave_color.red() * (0.3 + 0.7 * intensity))
                g = int(octave_color.green() * (0.3 + 0.7 * intensity))
                b = int(octave_color.blue() * (0.3 + 0.7 * intensity))
                color = QColor(r, g, b)
            else:
                # For step sequencer, use theme color with intensity
                r = int(highlight.red() * (0.3 + 0.7 * intensity))
                g = int(highlight.green() * (0.3 + 0.7 * intensity))
                b = int(highlight.blue() * (0.3 + 0.7 * intensity))
                color = QColor(r, g, b)

            # Darken significantly if not in scale
            if not self.in_scale:
                r = int(color.red() * 0.2)  # Very dark - 20% of original
                g = int(color.green() * 0.2)
                b = int(color.blue() * 0.2)
                color = QColor(r, g, b)

            self.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: {border_width}px solid {border_color};")
        else:
            # Inactive state
            if not self.in_scale:
                # Very dark gray for non-scale rows
                self.setStyleSheet(f"background-color: #0a0a0a; border: {border_width}px solid {border_color};")
            else:
                # Normal dark gray
                self.setStyleSheet(f"background-color: #2a2a2a; border: {border_width}px solid {border_color};")

    def mousePressEvent(self, event):
        """Handle mouse clicks"""
        if event.button() == Qt.LeftButton:
            self.leftClicked.emit(self.row, self.col)
        elif event.button() == Qt.RightButton:
            self.rightClicked.emit(self.row, self.col)


class VelocityOctavePopup(QDialog):
    """Popup dialog for configuring velocity and octave (arpeggiator only)"""

    def __init__(self, velocity, octave=None, allow_negative_octave=True, allow_positive_octave=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cell Configuration")
        self.setModal(True)

        layout = QVBoxLayout()

        # Velocity slider
        vel_label = QLabel("Velocity:")
        layout.addWidget(vel_label)

        self.velocity_slider = QSlider(Qt.Horizontal)
        self.velocity_slider.setRange(1, 255)  # Internal range 1-255
        self.velocity_slider.setValue(velocity)
        self.velocity_slider.valueChanged.connect(self.update_velocity_label)
        layout.addWidget(self.velocity_slider)

        # Velocity value label (display as half: 1-127)
        self.velocity_value_label = QLabel(str(velocity // 2))
        self.velocity_value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.velocity_value_label)

        # Octave spinner (only for arpeggiator)
        self.octave_spinner = None
        if octave is not None:
            oct_label = QLabel("Octave:")
            layout.addWidget(oct_label)

            self.octave_spinner = QSpinBox()

            # Determine min/max based on constraints
            min_octave = -4 if allow_negative_octave else 0
            max_octave = 4 if allow_positive_octave else 0

            self.octave_spinner.setRange(min_octave, max_octave)
            self.octave_spinner.setValue(octave)
            layout.addWidget(self.octave_spinner)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def update_velocity_label(self, value):
        """Update the velocity label to show half the internal value"""
        self.velocity_value_label.setText(str(value // 2))

    def get_values(self):
        """Get configured values"""
        velocity = self.velocity_slider.value()
        octave = self.octave_spinner.value() if self.octave_spinner else 0
        return velocity, octave


class BasicStepSequencerGrid(QWidget):
    """Grid widget for step sequencer basic tab with dynamic rows"""

    dataChanged = pyqtSignal()  # Emitted when grid data changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_arpeggiator = False  # For octave color logic
        self.num_steps = 8  # Default number of columns
        self.default_velocity = 255  # Default velocity for new cells
        self.rows = []  # List of row data: {'note': 0, 'octave': 4, 'cells': [GridCell, ...]}

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(2)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        # Create scroll area for grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.grid_container.setLayout(self.grid_layout)

        scroll.setWidget(self.grid_container)
        self.main_layout.addWidget(scroll, 1)

        self.setLayout(self.main_layout)

        # Create header row (step numbers)
        self.rebuild_header()

        # Create "Add Note" button (will be positioned after rows)
        self.btn_add_note = QPushButton("+")
        self.btn_add_note.setMinimumSize(60, 30)
        self.btn_add_note.setMaximumSize(60, 30)
        palette = self.palette()
        highlight = palette.color(QPalette.Highlight)
        self.btn_add_note.setStyleSheet(f"""
            QPushButton {{
                font-size: 18px;
                font-weight: bold;
                border: 2px solid {highlight.name()};
                background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 50);
            }}
            QPushButton:hover {{
                background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 100);
            }}
        """)
        self.btn_add_note.setCursor(Qt.PointingHandCursor)
        self.btn_add_note.clicked.connect(self.add_note_row)

        # Add 4 default rows
        default_notes = [
            ('C', 1),
            ('D', 1),
            ('E', 1),
            ('F', 1)
        ]
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        for note_name, octave in default_notes:
            note_index = note_names.index(note_name)
            self._create_row(note_index, octave)

        # Position the "+" button after all rows
        self._update_add_button_position()

    def _update_add_button_position(self):
        """Update the position of the '+' button to be after all note rows"""
        # Remove the button from its current position if it exists
        if self.btn_add_note.parent() is not None:
            self.grid_layout.removeWidget(self.btn_add_note)

        # Add it at the row after all existing rows (len(self.rows) + 1, accounting for header)
        row_position = len(self.rows) + 1
        self.grid_layout.addWidget(self.btn_add_note, row_position, 0)

    def rebuild_header(self):
        """Rebuild the header row with step numbers"""
        # Clear first row
        for col in range(self.grid_layout.columnCount()):
            item = self.grid_layout.itemAtPosition(0, col)
            if item and item.widget():
                item.widget().deleteLater()

        # Add label for note column
        note_header = QLabel("Note")
        note_header.setStyleSheet("font-weight: bold; padding-right: 5px;")
        self.grid_layout.addWidget(note_header, 0, 0)

        # Add step numbers
        for step in range(self.num_steps):
            lbl = QLabel(f"{step + 1}")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold;")
            self.grid_layout.addWidget(lbl, 0, step + 1)

    def on_steps_changed(self, new_steps):
        """Handle number of steps changed"""
        old_steps = self.num_steps
        self.num_steps = new_steps

        if new_steps > old_steps:
            # Add columns
            for row_idx, row_data in enumerate(self.rows):
                for step in range(old_steps, new_steps):
                    cell = GridCell(row_idx, step, self)
                    cell.leftClicked.connect(self.on_cell_left_click)
                    cell.rightClicked.connect(self.on_cell_right_click)
                    row_data['cells'].append(cell)
                    self.grid_layout.addWidget(cell, row_idx + 1, step + 1)
        elif new_steps < old_steps:
            # Remove columns
            for row_data in self.rows:
                for step in range(new_steps, old_steps):
                    cell = row_data['cells'].pop()
                    self.grid_layout.removeWidget(cell)
                    cell.deleteLater()

        self.rebuild_header()
        self.dataChanged.emit()

    def on_default_velocity_changed(self, value):
        """Handle default velocity changed"""
        self.default_velocity = value * 2  # Store as 0-255 internally

    def _create_row(self, note_index, octave):
        """Internal method to create a row with given note and octave"""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        # Create row
        row_idx = len(self.rows)
        row_data = {
            'note': note_index,
            'octave': octave,
            'cells': []
        }

        # Create note label with delete button
        note_widget = QWidget()
        note_layout = QHBoxLayout()
        note_layout.setContentsMargins(0, 0, 0, 0)
        note_layout.setSpacing(2)

        # Note label - clickable with theme styling
        note_label = QPushButton(f"{note_names[note_index]}{octave}")
        palette = self.palette()
        highlight = palette.color(QPalette.Highlight)
        note_label.setStyleSheet(f"""
            QPushButton {{
                font-weight: bold;
                min-width: 50px;
                text-align: center;
                border: 2px solid {highlight.name()};
                background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 50);
                padding: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 100);
            }}
        """)
        note_label.setCursor(Qt.PointingHandCursor)
        note_label.clicked.connect(lambda: self.edit_note_row(row_idx))
        note_layout.addWidget(note_label)

        # Delete button
        delete_btn = QPushButton("X")
        delete_btn.setFixedSize(20, 20)
        delete_btn.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
        delete_btn.clicked.connect(lambda: self.delete_note_row(row_idx))
        note_layout.addWidget(delete_btn)

        note_widget.setLayout(note_layout)
        self.grid_layout.addWidget(note_widget, row_idx + 1, 0)

        # Create cells for this row
        for step in range(self.num_steps):
            cell = GridCell(row_idx, step, self)
            cell.leftClicked.connect(self.on_cell_left_click)
            cell.rightClicked.connect(self.on_cell_right_click)
            row_data['cells'].append(cell)
            self.grid_layout.addWidget(cell, row_idx + 1, step + 1)

        self.rows.append(row_data)
        self._update_add_button_position()

    def add_note_row(self):
        """Add a new note row"""
        if len(self.rows) >= 128:  # MAX_PRESET_NOTES
            QMessageBox.warning(self, "Maximum Rows", "Maximum 128 note rows reached")
            return

        # Ask user to select note and octave
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        note, ok1 = QInputDialog.getItem(self, "Select Note", "Choose note:", note_names, 0, False)
        if not ok1:
            return

        octave, ok2 = QInputDialog.getInt(self, "Select Octave", "Choose octave:", 4, 0, 7, 1)
        if not ok2:
            return

        note_index = note_names.index(note)
        self._create_row(note_index, octave)
        self._update_add_button_position()
        self.dataChanged.emit()

    def edit_note_row(self, row_idx):
        """Edit an existing note row"""
        if row_idx >= len(self.rows):
            return

        row_data = self.rows[row_idx]
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        # Ask user to select new note and octave
        current_note = note_names[row_data['note']]
        note, ok1 = QInputDialog.getItem(self, "Edit Note", "Choose note:", note_names, note_names.index(current_note), False)
        if not ok1:
            return

        octave, ok2 = QInputDialog.getInt(self, "Edit Octave", "Choose octave:", row_data['octave'], 0, 7, 1)
        if not ok2:
            return

        # Update row data
        row_data['note'] = note_names.index(note)
        row_data['octave'] = octave

        # Update label
        item = self.grid_layout.itemAtPosition(row_idx + 1, 0)
        if item and item.widget():
            widget = item.widget()
            # Find the button (first child)
            note_button = widget.findChild(QPushButton)
            if note_button and note_button.text() != "X":  # Make sure it's not the delete button
                note_button.setText(f"{note}{octave}")

        self.dataChanged.emit()

    def delete_note_row(self, row_idx):
        """Delete a note row"""
        reply = QMessageBox.question(
            self,
            "Delete Row",
            "Are you sure you want to delete this note row?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Remove widgets
        row_data = self.rows[row_idx]

        # Remove note label (column 0)
        item = self.grid_layout.itemAtPosition(row_idx + 1, 0)
        if item and item.widget():
            item.widget().deleteLater()

        # Remove cells
        for cell in row_data['cells']:
            self.grid_layout.removeWidget(cell)
            cell.deleteLater()

        # Remove from list
        self.rows.pop(row_idx)

        # Rebuild grid (re-index rows)
        self.rebuild_grid()
        self._update_add_button_position()
        self.dataChanged.emit()

    def rebuild_grid(self):
        """Rebuild entire grid after deletion"""
        # Save cell states before clearing
        cell_states = []
        for row_data in self.rows:
            row_states = []
            for cell in row_data['cells']:
                row_states.append({
                    'active': cell.active,
                    'velocity': cell.velocity,
                    'octave': cell.octave
                })
            cell_states.append(row_states)

        # Clear grid widgets
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        # Rebuild header
        self.rebuild_header()

        # Rebuild rows with NEW cells
        for row_idx, row_data in enumerate(self.rows):
            # Recreate note label
            note_widget = QWidget()
            note_layout = QHBoxLayout()
            note_layout.setContentsMargins(0, 0, 0, 0)
            note_layout.setSpacing(2)

            # Note label - clickable with theme styling
            note_label = QPushButton(f"{note_names[row_data['note']]}{row_data['octave']}")
            palette = self.palette()
            highlight = palette.color(QPalette.Highlight)
            note_label.setStyleSheet(f"""
                QPushButton {{
                    font-weight: bold;
                    min-width: 50px;
                    text-align: center;
                    border: 2px solid {highlight.name()};
                    background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 50);
                    padding: 3px;
                }}
                QPushButton:hover {{
                    background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 100);
                }}
            """)
            note_label.setCursor(Qt.PointingHandCursor)
            note_label.clicked.connect(lambda checked, r=row_idx: self.edit_note_row(r))
            note_layout.addWidget(note_label)

            delete_btn = QPushButton("X")
            delete_btn.setFixedSize(20, 20)
            delete_btn.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
            delete_btn.clicked.connect(lambda checked, r=row_idx: self.delete_note_row(r))
            note_layout.addWidget(delete_btn)

            note_widget.setLayout(note_layout)
            self.grid_layout.addWidget(note_widget, row_idx + 1, 0)

            # Create NEW cells and restore their states
            new_cells = []
            for step in range(len(row_data['cells'])):
                cell = GridCell(row_idx, step, self)
                cell.leftClicked.connect(self.on_cell_left_click)
                cell.rightClicked.connect(self.on_cell_right_click)

                # Restore state if available
                if row_idx < len(cell_states) and step < len(cell_states[row_idx]):
                    state = cell_states[row_idx][step]
                    cell.set_active(state['active'], state['velocity'], state['octave'])

                new_cells.append(cell)
                self.grid_layout.addWidget(cell, row_idx + 1, step + 1)

            # Replace old cells list with new cells
            row_data['cells'] = new_cells

        self._update_add_button_position()

    def on_cell_left_click(self, row, col):
        """Handle left click - toggle cell"""
        if row >= len(self.rows):
            return

        row_data = self.rows[row]
        cell = row_data['cells'][col]

        # Toggle active state - reset to defaults when activating
        if cell.active:
            # Deactivate - clear data
            cell.set_active(False, self.default_velocity, 0)
        else:
            # Activate - use default values
            cell.set_active(True, self.default_velocity, 0)
        self.dataChanged.emit()

    def on_cell_right_click(self, row, col):
        """Handle right click - activate and configure with current or default values"""
        if row >= len(self.rows):
            return

        row_data = self.rows[row]
        cell = row_data['cells'][col]

        # Show velocity popup (no octave for step sequencer) - use current value if active
        current_velocity = cell.velocity if cell.active else self.default_velocity
        popup = VelocityOctavePopup(current_velocity, octave=None, parent=self)
        if popup.exec_() == QDialog.Accepted:
            velocity, _ = popup.get_values()
            cell.set_active(True, velocity, 0)
            self.dataChanged.emit()

    def get_grid_data(self, rate_16ths=16):
        """Get grid data as list of notes with timing

        Args:
            rate_16ths: Timing in 16th notes per step (default 1 = 1/16 notes)
        """
        notes = []
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        for row_idx, row_data in enumerate(self.rows):
            for step, cell in enumerate(row_data['cells']):
                if cell.active:
                    # Calculate timing based on actual rate
                    timing_16ths = step * rate_16ths

                    notes.append({
                        'timing_16ths': timing_16ths,
                        'note_index': row_data['note'],  # Absolute note (0-11)
                        'octave_offset': row_data['octave'],  # Absolute octave (0-7)
                        'velocity': cell.velocity,
                        'raw_travel': cell.velocity
                    })

        return notes

    def set_grid_data(self, notes_data, num_steps=8, rate_16ths=16):
        """Set grid data from notes list

        Args:
            notes_data: List of note dictionaries
            num_steps: Number of steps in the grid
            rate_16ths: Timing in 16th notes per step (default 1 = 1/16 notes)
        """
        # Clear existing rows - iterate with index to avoid lookup issues
        for i in range(len(self.rows) - 1, -1, -1):
            row_data = self.rows[i]
            # Remove and delete cells
            for cell in row_data['cells']:
                self.grid_layout.removeWidget(cell)
                cell.deleteLater()
            # Remove and delete note label widget
            item = self.grid_layout.itemAtPosition(i + 1, 0)
            if item and item.widget():
                item.widget().deleteLater()

        self.rows.clear()

        # Set number of steps
        self.num_steps = num_steps
        self.rebuild_header()

        # Group notes by (note_index, octave) to create rows
        note_groups = {}
        for note in notes_data:
            key = (note.get('note_index', 0), note.get('octave_offset', 4))
            if key not in note_groups:
                note_groups[key] = []
            note_groups[key].append(note)

        # If no data, create default rows (C1, D1, E1, F1)
        if not note_groups:
            note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            default_notes = [
                ('C', 1),
                ('D', 1),
                ('E', 1),
                ('F', 1)
            ]
            for note_name, octave in default_notes:
                note_index = note_names.index(note_name)
                self._create_row(note_index, octave)
            self._update_add_button_position()
            return

        # Create rows
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        for (note_idx, octave), notes in note_groups.items():
            row_idx = len(self.rows)
            row_data = {
                'note': note_idx,
                'octave': octave,
                'cells': []
            }

            # Create note label
            note_widget = QWidget()
            note_layout = QHBoxLayout()
            note_layout.setContentsMargins(0, 0, 0, 0)
            note_layout.setSpacing(2)

            # Note label - clickable with theme styling
            note_label = QPushButton(f"{note_names[note_idx]}{octave}")
            palette = self.palette()
            highlight = palette.color(QPalette.Highlight)
            note_label.setStyleSheet(f"""
                QPushButton {{
                    font-weight: bold;
                    min-width: 50px;
                    text-align: center;
                    border: 2px solid {highlight.name()};
                    background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 50);
                    padding: 3px;
                }}
                QPushButton:hover {{
                    background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 100);
                }}
            """)
            note_label.setCursor(Qt.PointingHandCursor)
            note_label.clicked.connect(lambda checked, r=row_idx: self.edit_note_row(r))
            note_layout.addWidget(note_label)

            delete_btn = QPushButton("X")
            delete_btn.setFixedSize(20, 20)
            delete_btn.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
            delete_btn.clicked.connect(lambda checked, r=row_idx: self.delete_note_row(r))
            note_layout.addWidget(delete_btn)

            note_widget.setLayout(note_layout)
            self.grid_layout.addWidget(note_widget, row_idx + 1, 0)

            # Create cells
            for step in range(num_steps):
                cell = GridCell(row_idx, step, self)
                cell.leftClicked.connect(self.on_cell_left_click)
                cell.rightClicked.connect(self.on_cell_right_click)

                # Check if this step has a note - use actual rate
                timing_16ths = step * rate_16ths
                matching_note = next((n for n in notes if abs(n['timing_16ths'] - timing_16ths) < (rate_16ths // 2)), None)

                if matching_note:
                    cell.set_active(True, matching_note.get('velocity', 127), 0)

                row_data['cells'].append(cell)
                self.grid_layout.addWidget(cell, row_idx + 1, step + 1)

            self.rows.append(row_data)

        self._update_add_button_position()


class BasicArpeggiatorGrid(QWidget):
    """Grid widget for arpeggiator basic tab with fixed 23 rows (intervals -11 to +11)"""

    dataChanged = pyqtSignal()  # Emitted when grid data changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_arpeggiator = True  # For octave color logic
        self.num_steps = 8  # Default number of columns
        self.default_velocity = 255  # Default velocity for new cells
        self.cells = []  # 25 rows x num_steps columns
        self.show_negative_intervals = False  # Hide negative intervals by default

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(2)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        # Create scroll area for grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.grid_container.setLayout(self.grid_layout)

        scroll.setWidget(self.grid_container)
        self.main_layout.addWidget(scroll, 1)

        # Scale selector
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scale:"))

        self.combo_scale = ArrowComboBox()
        self.combo_scale.setMinimumWidth(150)
        self.combo_scale.setMaximumHeight(30)
        self.combo_scale.setEditable(True)
        self.combo_scale.lineEdit().setReadOnly(True)
        self.combo_scale.lineEdit().setAlignment(Qt.AlignCenter)

        # Define all scales and modes
        self.scale_definitions = {
            'Chromatic': list(range(-11, 12)),  # All 23 semitones
            'Major': [0, 2, 4, 5, 7, 9, 11],
            'Minor': [0, 2, 3, 5, 7, 8, 10],
            'Pentatonic Major': [0, 2, 4, 7, 9],
            'Pentatonic Minor': [0, 3, 5, 7, 10],
            'Blues': [0, 3, 5, 6, 7, 10],
            'Dorian': [0, 2, 3, 5, 7, 9, 10],
            'Phrygian': [0, 1, 3, 5, 7, 8, 10],
            'Lydian': [0, 2, 4, 6, 7, 9, 11],
            'Mixolydian': [0, 2, 4, 5, 7, 9, 10],
            'Locrian': [0, 1, 3, 5, 6, 8, 10],
            'Harmonic Minor': [0, 2, 3, 5, 7, 8, 11],
            'Melodic Minor': [0, 2, 3, 5, 7, 9, 11],
            'Whole Tone': [0, 2, 4, 6, 8, 10],
            'Diminished': [0, 2, 3, 5, 6, 8, 9, 11],
        }

        for scale_name in self.scale_definitions.keys():
            self.combo_scale.addItem(scale_name)
        self.combo_scale.setCurrentText('Chromatic')
        self.combo_scale.setToolTip("Select scale to highlight intervals")
        self.combo_scale.currentTextChanged.connect(self.on_scale_changed)
        scale_layout.addWidget(self.combo_scale)
        scale_layout.addStretch()
        self.main_layout.addLayout(scale_layout)

        # Add octave color legend note
        legend_layout = QHBoxLayout()
        legend_label = QLabel("Octave colors use theme-relative hue shifts (0 = root, ±1-4 = shifted hues)")
        legend_label.setStyleSheet("color: #aaa; font-size: 10px; font-style: italic;")
        legend_layout.addWidget(legend_label)
        legend_layout.addStretch()
        self.main_layout.addLayout(legend_layout)

        self.setLayout(self.main_layout)

        # Build grid
        self.build_grid()

    def build_grid(self):
        """Build the complete grid with 23 rows"""
        # Clear existing
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        self.cells = []

        # Header row (step numbers)
        self.grid_layout.addWidget(QLabel("Interval"), 0, 0)
        for step in range(self.num_steps):
            lbl = QLabel(f"{step + 1}")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold;")
            self.grid_layout.addWidget(lbl, 0, step + 1)

        # Create 23 rows (intervals -11 to +11)
        for row in range(23):
            interval = 11 - row  # Row 0 = +11, row 11 = 0, row 22 = -11

            # Interval label
            if interval == 0:
                lbl_text = "Base Note"
            elif interval > 0:
                lbl_text = f"+{interval}"
            else:
                lbl_text = str(interval)

            lbl = QLabel(lbl_text)
            lbl.setAlignment(Qt.AlignRight)

            # Highlight the Base Note row (interval 0, which is row 11)
            if interval == 0:
                lbl.setStyleSheet("min-width: 30px; padding-right: 5px; font-weight: bold; color: white;")
            else:
                lbl.setStyleSheet("min-width: 30px; padding-right: 5px;")
            self.grid_layout.addWidget(lbl, row + 1, 0)

            # Create cells for this row
            row_cells = []
            for step in range(self.num_steps):
                cell = GridCell(row, step, self)
                cell.leftClicked.connect(self.on_cell_left_click)
                cell.rightClicked.connect(self.on_cell_right_click)
                row_cells.append(cell)
                self.grid_layout.addWidget(cell, row + 1, step + 1)

            self.cells.append(row_cells)

        # Add "Show negative intervals" checkbox below Base Note row (row 12, which is after row 11 + header)
        self.chk_show_negative = QCheckBox("Show negative intervals")
        self.chk_show_negative.setChecked(self.show_negative_intervals)
        self.chk_show_negative.stateChanged.connect(self.on_show_negative_changed)
        self.grid_layout.addWidget(self.chk_show_negative, 13, 0, 1, self.num_steps + 1)  # Span across all columns

        # Hide negative interval rows by default (rows 12-22, intervals -1 to -11)
        self.update_negative_interval_visibility()

    def on_show_negative_changed(self, state):
        """Handle show negative intervals checkbox change"""
        self.show_negative_intervals = (state == Qt.Checked)
        self.update_negative_interval_visibility()

    def update_negative_interval_visibility(self):
        """Show or hide negative interval rows based on checkbox state"""
        # Rows 12-22 are intervals -1 to -11
        for row in range(12, 23):
            # Hide/show the label
            label_item = self.grid_layout.itemAtPosition(row + 1, 0)
            if label_item and label_item.widget():
                label_item.widget().setVisible(self.show_negative_intervals)

            # Hide/show all cells in this row
            if row < len(self.cells):
                for cell in self.cells[row]:
                    cell.setVisible(self.show_negative_intervals)

    def on_steps_changed(self, new_steps):
        """Handle number of steps changed - preserve existing data"""
        old_steps = self.num_steps
        self.num_steps = new_steps

        if new_steps > old_steps:
            # Add columns - append new cells to each row
            for row_idx, row_cells in enumerate(self.cells):
                for step in range(old_steps, new_steps):
                    cell = GridCell(row_idx, step, self)
                    cell.leftClicked.connect(self.on_cell_left_click)
                    cell.rightClicked.connect(self.on_cell_right_click)
                    row_cells.append(cell)
                    self.grid_layout.addWidget(cell, row_idx + 1, step + 1)
                    # Set visibility based on negative interval setting
                    if row_idx >= 12 and not self.show_negative_intervals:
                        cell.setVisible(False)
        elif new_steps < old_steps:
            # Remove columns - remove cells from end of each row
            for row_cells in self.cells:
                for step in range(new_steps, old_steps):
                    cell = row_cells.pop()
                    self.grid_layout.removeWidget(cell)
                    cell.deleteLater()

        # Update header row
        # Clear header first (row 0)
        for col in range(self.grid_layout.columnCount()):
            item = self.grid_layout.itemAtPosition(0, col)
            if item and item.widget():
                item.widget().deleteLater()

        # Rebuild header
        self.grid_layout.addWidget(QLabel("Interval"), 0, 0)
        for step in range(self.num_steps):
            lbl = QLabel(f"{step + 1}")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold;")
            self.grid_layout.addWidget(lbl, 0, step + 1)

        # Update checkbox position to span new number of columns
        if hasattr(self, 'chk_show_negative'):
            self.grid_layout.removeWidget(self.chk_show_negative)
            self.grid_layout.addWidget(self.chk_show_negative, 13, 0, 1, self.num_steps + 1)

        # Update negative interval visibility after column changes
        if hasattr(self, 'show_negative_intervals'):
            self.update_negative_interval_visibility()

        self.dataChanged.emit()

    def on_default_velocity_changed(self, value):
        """Handle default velocity changed"""
        self.default_velocity = value * 2  # Store as 0-255 internally

    def on_cell_left_click(self, row, col):
        """Handle left click - toggle cell"""
        if row >= len(self.cells):
            return

        cell = self.cells[row][col]

        # Toggle active state - reset to defaults when activating
        if cell.active:
            # Deactivate - clear data
            cell.set_active(False, self.default_velocity, 0)
        else:
            # Activate - use default values
            cell.set_active(True, self.default_velocity, 0)
        self.dataChanged.emit()

    def on_cell_right_click(self, row, col):
        """Handle right click - activate and configure (always reset to defaults)"""
        if row >= len(self.cells):
            return

        cell = self.cells[row][col]
        interval = 11 - row  # Calculate interval from row

        # Determine octave constraints based on row position
        # Row 11 (interval 0) allows both negative and positive
        # Rows above 11 (positive intervals) only allow positive octaves
        # Rows below 11 (negative intervals) only allow negative octaves
        allow_negative = (interval <= 0)
        allow_positive = (interval >= 0)

        # Show velocity + octave popup - use current cell values if active
        current_velocity = cell.velocity if cell.active else self.default_velocity
        current_octave = cell.octave if cell.active else 0

        popup = VelocityOctavePopup(current_velocity, octave=current_octave,
                                    allow_negative_octave=allow_negative,
                                    allow_positive_octave=allow_positive,
                                    parent=self)
        if popup.exec_() == QDialog.Accepted:
            velocity, octave = popup.get_values()
            cell.set_active(True, velocity, octave)
            self.dataChanged.emit()

    def get_grid_data(self, rate_16ths=16):
        """Get grid data as list of notes with timing

        Args:
            rate_16ths: Timing in 16th notes per step (default 1 = 1/16 notes)
        """
        notes = []

        for row_idx, row_cells in enumerate(self.cells):
            interval = 11 - row_idx  # Calculate interval

            for step, cell in enumerate(row_cells):
                if cell.active:
                    # Calculate timing based on actual rate
                    timing_16ths = step * rate_16ths

                    notes.append({
                        'timing_16ths': timing_16ths,
                        'note_index': interval,  # Semitone offset for arpeggiator
                        'semitone_offset': interval,  # Also store as semitone_offset
                        'octave_offset': cell.octave,
                        'velocity': cell.velocity,
                        'raw_travel': cell.velocity
                    })

        return notes

    def set_grid_data(self, notes_data, num_steps=8, rate_16ths=16):
        """Set grid data from notes list

        Args:
            notes_data: List of note dictionaries
            num_steps: Number of steps in the grid
            rate_16ths: Timing in 16th notes per step (default 1 = 1/16 notes)
        """
        # Set number of steps
        self.num_steps = num_steps
        self.build_grid()

        # Populate cells
        for note in notes_data:
            interval = note.get('semitone_offset', note.get('note_index', 0))
            octave = note.get('octave_offset', 0)
            velocity = note.get('velocity', 127)
            timing_16ths = note.get('timing_16ths', 0)

            # Calculate step from timing using actual rate
            step = timing_16ths // rate_16ths

            # Calculate row from interval (row 0 = +11, row 11 = 0, row 22 = -11)
            row = 11 - interval

            if 0 <= row < 23 and 0 <= step < self.num_steps:
                cell = self.cells[row][step]
                cell.set_active(True, velocity, octave)

    def filter_rows_by_scale(self, allowed_intervals):
        """Darken rows that aren't in the selected scale"""
        # allowed_intervals is a set of semitone offsets (-11 to +11)
        for row in range(23):
            interval = 11 - row  # Row 0 = +11, row 11 = 0, row 22 = -11

            # Determine if this interval is in the scale
            in_scale = interval in allowed_intervals

            # Darken the interval label if not in scale - grey out LOTS
            label_item = self.grid_layout.itemAtPosition(row + 1, 0)
            if label_item and label_item.widget():
                label = label_item.widget()
                if in_scale:
                    label.setStyleSheet("min-width: 30px; padding-right: 5px;")
                else:
                    # Grey out label significantly
                    label.setStyleSheet("min-width: 30px; padding-right: 5px; color: #333;")

            # Darken all cells in this row if not in scale - keep them selectable
            if row < len(self.cells):
                for cell in self.cells[row]:
                    # Store scale state in cell for use in update_style
                    cell.in_scale = in_scale
                    # Force update of cell style
                    cell.update_style()

    def on_scale_changed(self, scale_name):
        """Handle scale selection change"""
        # Get the intervals for this scale
        scale_intervals = self.scale_definitions.get(scale_name, list(range(-11, 12)))

        # Expand scale to cover all octaves
        expanded_intervals = set()
        for interval in scale_intervals:
            # Add interval in all octaves (-11 to +11)
            for octave in range(-1, 2):  # -1, 0, +1 octaves
                semitone = interval + (octave * 12)
                if -11 <= semitone <= 11:
                    expanded_intervals.add(semitone)

        # Filter rows based on scale
        self.filter_rows_by_scale(expanded_intervals)


class IntervalSelector(QWidget):
    """Custom interval selector with +/- buttons and editable value box"""

    valueChanged = pyqtSignal(int)

    # Interval names mapping (extended range)
    # Note: -1 is now a valid interval (minor second down), not "Empty"
    INTERVAL_NAMES = {
        0: "Root Note",
        1: "Minor Second",
        2: "Major Second",
        3: "Minor Third",
        4: "Major Third",
        5: "Perfect Fourth",
        6: "Tritone",
        7: "Perfect Fifth",
        8: "Minor Sixth",
        9: "Major Sixth",
        10: "Minor Seventh",
        11: "Major Seventh",
        12: "Octave",
        13: "Minor 9th",
        14: "Major 9th",
        15: "Minor 10th",
        16: "Major 10th",
        17: "Perfect 11th",
        18: "Augmented 11th",
        19: "Perfect 12th",
        20: "Minor 13th",
        21: "Major 13th",
        22: "Minor 14th",
        23: "Major 14th"
    }

    # Generate negative interval names (mirror positive ones)
    NEGATIVE_INTERVAL_NAMES = {
        -1: "-Minor Second",
        -2: "-Major Second",
        -3: "-Minor Third",
        -4: "-Major Third",
        -5: "-Perfect Fourth",
        -6: "-Tritone",
        -7: "-Perfect Fifth",
        -8: "-Minor Sixth",
        -9: "-Major Sixth",
        -10: "-Minor Seventh",
        -11: "-Major Seventh",
        -12: "-Octave",
        -13: "-Minor 9th",
        -14: "-Major 9th",
        -15: "-Minor 10th",
        -16: "-Major 10th",
        -17: "-Perfect 11th",
        -18: "-Augmented 11th",
        -19: "-Perfect 12th",
        -20: "-Minor 13th",
        -21: "-Major 13th",
        -22: "-Minor 14th",
        -23: "-Major 14th"
    }

    # Combine mappings
    INTERVAL_NAMES.update(NEGATIVE_INTERVAL_NAMES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0  # Default to Root Note

        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        # Interval name label (above the box)
        self.name_label = QLabel("Root Note")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(self.name_label)

        # Container for the value box with integrated +/- buttons
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        container.setMaximumWidth(120)

        box_layout = QHBoxLayout()
        box_layout.setSpacing(0)
        box_layout.setContentsMargins(2, 2, 2, 2)

        # Minus button (inside container, on left)
        self.btn_minus = QPushButton("-")
        self.btn_minus.setFixedSize(25, 25)
        self.btn_minus.clicked.connect(self.decrement)
        box_layout.addWidget(self.btn_minus)

        # Value box (center)
        self.value_box = QLabel("+0")
        self.value_box.setAlignment(Qt.AlignCenter)
        self.value_box.setMinimumWidth(50)
        box_layout.addWidget(self.value_box, 1)

        # Plus button (inside container, on right)
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(25, 25)
        self.btn_plus.clicked.connect(self.increment)
        box_layout.addWidget(self.btn_plus)

        container.setLayout(box_layout)
        layout.addWidget(container, 0, Qt.AlignCenter)
        self.setLayout(layout)

        self.update_display()

    def get_value(self):
        """Get current interval value"""
        return self.value

    def set_value(self, value):
        """Set interval value"""
        # Clamp to valid range (-23 to +23)
        if value < -23:
            value = -23
        elif value > 23:
            value = 23

        if self.value != value:
            self.value = value
            self.update_display()
            self.valueChanged.emit(self.value)

    def increment(self):
        """Increment interval value"""
        if self.value < 23:
            self.set_value(self.value + 1)

    def decrement(self):
        """Decrement interval value"""
        if self.value > -23:
            self.set_value(self.value - 1)

    def update_display(self):
        """Update the display text"""
        # Update interval name
        self.name_label.setText(self.INTERVAL_NAMES.get(self.value, "Unknown"))

        # Update value box
        if self.value >= 0:
            self.value_box.setText(f"+{self.value}")
        else:
            self.value_box.setText(str(self.value))

        # Enable/disable buttons
        self.btn_minus.setEnabled(self.value > -23)
        self.btn_plus.setEnabled(self.value < 23)


class NoteSelector(QWidget):
    """Note selector for step sequencer (C-B dropdown)"""

    valueChanged = pyqtSignal(int)

    # Note names
    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0  # Default to C

        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        # Note dropdown
        self.combo_note = ArrowComboBox()
        self.combo_note.setEditable(True)
        self.combo_note.lineEdit().setReadOnly(True)
        self.combo_note.lineEdit().setAlignment(Qt.AlignCenter)
        self.combo_note.setMinimumWidth(60)
        for i, note_name in enumerate(self.NOTE_NAMES):
            self.combo_note.addItem(note_name, i)
        self.combo_note.currentIndexChanged.connect(self.on_value_changed)
        layout.addWidget(self.combo_note)

        self.setLayout(layout)

    def get_value(self):
        """Get current note value (0-11)"""
        return self.value

    def set_value(self, value):
        """Set note value (0-11)"""
        if value < 0:
            value = 0
        elif value > 11:
            value = 11

        if self.value != value:
            self.value = value
            self.combo_note.setCurrentIndex(value)
            self.valueChanged.emit(self.value)

    def on_value_changed(self, index):
        """Combo box selection changed"""
        if index >= 0:
            self.value = index
            self.valueChanged.emit(self.value)


class OctaveSelector(QWidget):
    """Custom octave selector with +/- buttons"""

    valueChanged = pyqtSignal(int)

    def __init__(self, min_octave=-2, max_octave=2, default_octave=0, parent=None):
        super().__init__(parent)
        self.min_octave = min_octave
        self.max_octave = max_octave
        self.value = default_octave  # Default

        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        # Container for the value box with integrated +/- buttons
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        container.setMaximumWidth(120)

        box_layout = QHBoxLayout()
        box_layout.setSpacing(0)
        box_layout.setContentsMargins(2, 2, 2, 2)

        # Minus button (inside container, on left)
        self.btn_minus = QPushButton("-")
        self.btn_minus.setFixedSize(25, 25)
        self.btn_minus.clicked.connect(self.decrement)
        box_layout.addWidget(self.btn_minus)

        # Value box (center)
        self.value_box = QLabel("0")
        self.value_box.setAlignment(Qt.AlignCenter)
        self.value_box.setMinimumWidth(50)
        box_layout.addWidget(self.value_box, 1)

        # Plus button (inside container, on right)
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(25, 25)
        self.btn_plus.clicked.connect(self.increment)
        box_layout.addWidget(self.btn_plus)

        container.setLayout(box_layout)
        layout.addWidget(container, 0, Qt.AlignCenter)
        self.setLayout(layout)

        self.update_display()

    def get_value(self):
        """Get current octave value"""
        return self.value

    def set_value(self, value):
        """Set octave value"""
        # Clamp to valid range
        if value < self.min_octave:
            value = self.min_octave
        elif value > self.max_octave:
            value = self.max_octave

        if self.value != value:
            self.value = value
            self.update_display()
            self.valueChanged.emit(self.value)

    def increment(self):
        """Increment octave value"""
        if self.value < self.max_octave:
            self.set_value(self.value + 1)

    def decrement(self):
        """Decrement octave value"""
        if self.value > self.min_octave:
            self.set_value(self.value - 1)

    def update_display(self):
        """Update the display text"""
        # Update value box with + or - prefix (for arpeggiator) or absolute (for step seq)
        if self.min_octave < 0:
            # Arpeggiator mode (relative octaves)
            if self.value > 0:
                self.value_box.setText(f"+{self.value}")
            else:
                self.value_box.setText(str(self.value))
        else:
            # Step sequencer mode (absolute octaves)
            self.value_box.setText(str(self.value))

        # Enable/disable buttons
        self.btn_minus.setEnabled(self.value > self.min_octave)
        self.btn_plus.setEnabled(self.value < self.max_octave)


class VelocityBar(QWidget):
    """Interactive velocity bar for step sequencer - click height sets velocity"""

    clicked = pyqtSignal(int)  # Emits velocity value 0-255

    def __init__(self, parent=None):
        super().__init__(parent)
        self.velocity = 200  # Default velocity
        self.setMinimumSize(30, 120)
        self.setMaximumSize(40, 150)
        self.setSizePolicy(self.sizePolicy().Minimum, self.sizePolicy().Expanding)

    def set_velocity(self, velocity):
        """Set velocity value (0-255)"""
        self.velocity = max(0, min(255, velocity))
        self.update()

    def get_velocity(self):
        """Get current velocity"""
        return self.velocity

    def paintEvent(self, event):
        from PyQt5.QtGui import QPalette

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get theme colors from palette
        palette = self.palette()
        bg_color = palette.color(QPalette.Window)
        highlight_color = palette.color(QPalette.Highlight)

        # Background
        painter.fillRect(self.rect(), bg_color.darker(120))

        # Border
        painter.setPen(QPen(palette.color(QPalette.Mid), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        # Velocity bar with theme highlight color
        if self.velocity > 0:
            bar_height = int((self.velocity / 255.0) * self.height())
            bar_y = self.height() - bar_height

            # Use theme highlight color with intensity based on velocity
            intensity = self.velocity / 255.0
            color = QColor(
                int(highlight_color.red() * (0.5 + 0.5 * intensity)),
                int(highlight_color.green() * (0.5 + 0.5 * intensity)),
                int(highlight_color.blue() * (0.5 + 0.5 * intensity))
            )

            painter.fillRect(1, bar_y, self.width() - 2, bar_height, color)

        # Velocity text (display half the value, rounded down)
        painter.setPen(palette.color(QPalette.Text))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.rect(), Qt.AlignCenter, str(self.velocity // 2))

    def mousePressEvent(self, event):
        """Click to set velocity based on Y position"""
        if event.button() == Qt.LeftButton:
            # Invert Y (top = high velocity, bottom = low)
            relative_y = event.pos().y() / self.height()
            velocity = int((1.0 - relative_y) * 255)
            self.set_velocity(velocity)
            self.clicked.emit(self.velocity)

    def mouseMoveEvent(self, event):
        """Drag to set velocity based on Y position"""
        if event.buttons() & Qt.LeftButton:
            # Invert Y (top = high velocity, bottom = low)
            relative_y = max(0, min(1, event.pos().y() / self.height()))
            velocity = int((1.0 - relative_y) * 255)
            self.set_velocity(velocity)
            self.clicked.emit(self.velocity)


class CompactNoteLabel(QPushButton):
    """Compact clickable label for a note in the list"""

    removed = pyqtSignal()  # Signal to remove this note
    selected = pyqtSignal()  # Signal when clicked to select

    def __init__(self, note_num, is_step_sequencer=False, parent=None):
        super().__init__(parent)
        self.note_num = note_num
        self.is_step_sequencer = is_step_sequencer
        self.note_data = {
            'velocity': 200,
            'octave_offset': 4 if is_step_sequencer else 0,
            'note_index': 0 if is_step_sequencer else None,
            'semitone_offset': 0 if not is_step_sequencer else None
        }
        self.is_selected = False

        # Setup as checkable button
        self.setCheckable(True)
        self.clicked.connect(self.on_clicked)
        self.setMinimumHeight(25)
        self.setMaximumHeight(25)

        self.update_label()
        self.set_selected(False)  # Initialize with unselected style

    def on_clicked(self):
        """Button clicked - emit selected signal"""
        self.selected.emit()

    def set_selected(self, selected):
        """Set selection state"""
        self.is_selected = selected
        self.setChecked(selected)

        # Update style to highlight border when selected
        palette = self.palette()
        highlight = palette.color(QPalette.Highlight)
        if selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    border: 3px solid {highlight.name()};
                    background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 50);
                    padding: 3px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {highlight.darker(150).name()};
                    background-color: rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 20);
                    padding: 3px;
                }}
            """)

    def update_label(self):
        """Update label text based on note data"""
        note_str = ""
        if self.is_step_sequencer:
            # Step sequencer: show "C#4" (note + octave)
            note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            note_idx = self.note_data.get('note_index', 0)
            octave = self.note_data.get('octave_offset', 4)
            note_str = f"{note_names[note_idx]}{octave}"
        else:
            # Arpeggiator: show "Int +5, Oct +1"
            interval = self.note_data.get('semitone_offset', 0)
            octave = self.note_data.get('octave_offset', 0)
            int_str = f"+{interval}" if interval > 0 else str(interval)
            oct_str = f"+{octave}" if octave > 0 else str(octave)
            note_str = f"Int {int_str}, Oct {oct_str}"

        self.setText(note_str)

    def get_note_data(self):
        """Get note data dict"""
        return self.note_data.copy()

    def set_note_data(self, data):
        """Set note data and update label"""
        self.note_data.update(data)
        self.update_label()


class StepWidget(QFrame):
    """Single step in the sequencer - narrow vertical layout with compact note list"""

    def __init__(self, step_num, is_step_sequencer=False, parent=None):
        super().__init__(parent)
        self.step_num = step_num
        self.is_step_sequencer = is_step_sequencer
        self.note_labels = []
        self.selected_note_index = None

        # Main vertical layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(4)
        self.main_layout.setContentsMargins(4, 4, 4, 4)

        # Step number label
        lbl_step = QLabel(f"Step {step_num + 1}")
        lbl_step.setAlignment(Qt.AlignCenter)
        lbl_step.setFont(QFont("Arial", 10, QFont.Bold))
        self.main_layout.addWidget(lbl_step)

        # Create empty state widgets
        self.empty_container = QWidget()
        empty_layout = QVBoxLayout()
        empty_layout.addStretch()
        self.btn_add_note_empty = QPushButton("Add Note")
        self.btn_add_note_empty.setStyleSheet("QPushButton { min-height: 30px; max-height: 30px; }")
        self.btn_add_note_empty.clicked.connect(self.add_note)
        empty_layout.addWidget(self.btn_add_note_empty)
        empty_layout.addStretch()
        self.empty_container.setLayout(empty_layout)
        self.main_layout.addWidget(self.empty_container, 1)

        # Create filled state widgets (hidden initially)
        self.filled_container = QWidget()
        filled_layout = QVBoxLayout()
        filled_layout.setSpacing(2)
        filled_layout.setContentsMargins(0, 0, 0, 0)

        # Velocity title
        lbl_velocity = QLabel("Velocity")
        lbl_velocity.setAlignment(Qt.AlignCenter)
        lbl_velocity.setFont(QFont("Arial", 9, QFont.Bold))
        filled_layout.addWidget(lbl_velocity)

        # Velocity bar (centered)
        velocity_bar_container = QWidget()
        velocity_bar_layout = QHBoxLayout()
        velocity_bar_layout.setContentsMargins(0, 0, 0, 0)
        velocity_bar_layout.addStretch()
        self.velocity_bar = VelocityBar()
        self.velocity_bar.clicked.connect(self.on_velocity_changed)
        velocity_bar_layout.addWidget(self.velocity_bar)
        velocity_bar_layout.addStretch()
        velocity_bar_container.setLayout(velocity_bar_layout)
        filled_layout.addWidget(velocity_bar_container)

        # Note/Interval label
        if self.is_step_sequencer:
            lbl_note = QLabel("Note")
            lbl_note.setAlignment(Qt.AlignCenter)
            lbl_note.setFont(QFont("Arial", 9, QFont.Bold))
            filled_layout.addWidget(lbl_note)
        else:
            lbl_interval = QLabel("Interval")
            lbl_interval.setAlignment(Qt.AlignCenter)
            lbl_interval.setFont(QFont("Arial", 9, QFont.Bold))
            filled_layout.addWidget(lbl_interval)

        # Interval/Note selector
        if self.is_step_sequencer:
            self.note_selector = NoteSelector()
            self.note_selector.valueChanged.connect(self.on_note_changed)
            filled_layout.addWidget(self.note_selector)
        else:
            self.interval_selector = IntervalSelector()
            self.interval_selector.valueChanged.connect(self.on_interval_changed)
            filled_layout.addWidget(self.interval_selector)

        # Octave title
        lbl_octave = QLabel("Octave")
        lbl_octave.setAlignment(Qt.AlignCenter)
        lbl_octave.setFont(QFont("Arial", 9, QFont.Bold))
        filled_layout.addWidget(lbl_octave)

        # Octave selector
        if self.is_step_sequencer:
            self.octave_selector = OctaveSelector(min_octave=0, max_octave=7, default_octave=4)
        else:
            self.octave_selector = OctaveSelector(min_octave=-4, max_octave=4, default_octave=0)
        self.octave_selector.valueChanged.connect(self.on_octave_changed)
        filled_layout.addWidget(self.octave_selector)

        # Add Note button
        self.btn_add_note = QPushButton("Add Note")
        self.btn_add_note.setStyleSheet("QPushButton { min-height: 25px; max-height: 25px; }")
        self.btn_add_note.clicked.connect(self.add_note)
        filled_layout.addWidget(self.btn_add_note)

        # Small spacer
        filled_layout.addSpacing(8)

        # Scroll area for note labels
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(60)

        # Container for note labels
        self.notes_container = QWidget()
        self.notes_layout = QVBoxLayout()
        self.notes_layout.setSpacing(0)  # No space between notes
        self.notes_layout.setContentsMargins(0, 0, 0, 0)
        self.notes_layout.addStretch()  # Push notes from bottom
        self.notes_container.setLayout(self.notes_layout)
        scroll_area.setWidget(self.notes_container)

        filled_layout.addWidget(scroll_area, 1)

        # Remove Note button at bottom
        self.btn_remove = QPushButton("Remove Note")
        self.btn_remove.setStyleSheet("QPushButton { min-height: 25px; max-height: 25px; }")
        self.btn_remove.clicked.connect(self.remove_selected_note)
        filled_layout.addWidget(self.btn_remove)

        self.filled_container.setLayout(filled_layout)
        self.main_layout.addWidget(self.filled_container, 1)
        self.filled_container.setVisible(False)

        self.setLayout(self.main_layout)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setMinimumWidth(140)
        self.setMaximumWidth(140)

        # Update empty state styling
        self.update_empty_state()

    def update_empty_state(self):
        """Update styling based on whether step is empty"""
        is_empty = len(self.note_labels) == 0

        if is_empty:
            # Grey out the container
            self.setStyleSheet("QFrame { background-color: #3a3a3a; }")
            self.empty_container.setVisible(True)
            self.filled_container.setVisible(False)
        else:
            # Normal styling
            self.setStyleSheet("")
            self.empty_container.setVisible(False)
            self.filled_container.setVisible(True)

    def add_note(self):
        """Add a new note to this step"""
        if len(self.note_labels) >= 8:
            QMessageBox.warning(None, "Maximum Notes", "Maximum 8 notes per step reached")
            return

        note_label = CompactNoteLabel(len(self.note_labels), self.is_step_sequencer)
        note_label.selected.connect(lambda: self.select_note(note_label))
        self.note_labels.append(note_label)
        # Insert before the stretch (which is the last item)
        self.notes_layout.insertWidget(self.notes_layout.count() - 1, note_label)

        # Auto-select the new note
        self.select_note(note_label)

        # Update button state
        self.btn_add_note.setEnabled(len(self.note_labels) < 8)

        # Update empty state
        self.update_empty_state()

    def select_note(self, note_label):
        """Select a note and show its data in the controls"""
        # Deselect all notes
        for label in self.note_labels:
            label.set_selected(False)

        # Select this note
        note_label.set_selected(True)
        self.selected_note_index = self.note_labels.index(note_label)

        # Load note data into controls
        data = note_label.get_note_data()
        self.velocity_bar.set_velocity(data.get('velocity', 200))

        if self.is_step_sequencer:
            self.note_selector.set_value(data.get('note_index', 0))
            self.octave_selector.set_value(data.get('octave_offset', 4))
        else:
            self.interval_selector.set_value(data.get('semitone_offset', 0))
            self.octave_selector.set_value(data.get('octave_offset', 0))

    def on_velocity_changed(self, velocity):
        """Velocity changed - update selected note"""
        if self.selected_note_index is not None and self.selected_note_index < len(self.note_labels):
            note_label = self.note_labels[self.selected_note_index]
            data = note_label.get_note_data()
            data['velocity'] = velocity
            note_label.set_note_data(data)

    def on_interval_changed(self, value):
        """Interval changed - update selected note"""
        if self.selected_note_index is not None and self.selected_note_index < len(self.note_labels):
            note_label = self.note_labels[self.selected_note_index]
            data = note_label.get_note_data()
            data['semitone_offset'] = value
            note_label.set_note_data(data)

    def on_note_changed(self, value):
        """Note changed - update selected note"""
        if self.selected_note_index is not None and self.selected_note_index < len(self.note_labels):
            note_label = self.note_labels[self.selected_note_index]
            data = note_label.get_note_data()
            data['note_index'] = value
            note_label.set_note_data(data)

    def on_octave_changed(self, value):
        """Octave changed - update selected note"""
        if self.selected_note_index is not None and self.selected_note_index < len(self.note_labels):
            note_label = self.note_labels[self.selected_note_index]
            data = note_label.get_note_data()
            data['octave_offset'] = value
            note_label.set_note_data(data)

    def remove_selected_note(self):
        """Remove the currently selected note"""
        if self.selected_note_index is not None and self.selected_note_index < len(self.note_labels):
            note_label = self.note_labels[self.selected_note_index]
            self.note_labels.remove(note_label)
            self.notes_layout.removeWidget(note_label)
            note_label.deleteLater()

            # Renumber remaining notes
            for i, label in enumerate(self.note_labels):
                label.note_num = i
                label.update_label()

            # Clear selection
            self.selected_note_index = None

            # Update button state
            self.btn_add_note.setEnabled(len(self.note_labels) < 8)

            # Update empty state
            self.update_empty_state()

            # If there are still notes, select the first one
            if len(self.note_labels) > 0:
                self.select_note(self.note_labels[0])

    def get_step_data(self):
        """Return step data as list of note dicts"""
        notes = []
        for label in self.note_labels:
            notes.append(label.get_note_data())
        return notes

    def set_step_data(self, notes_data):
        """Load step data from list of note dicts"""
        # Clear existing notes
        for label in self.note_labels[:]:
            self.notes_layout.removeWidget(label)
            label.deleteLater()
        self.note_labels.clear()
        self.selected_note_index = None

        # Add notes from data
        for note_data in notes_data:
            note_label = CompactNoteLabel(len(self.note_labels), self.is_step_sequencer)
            note_label.selected.connect(lambda nl=note_label: self.select_note(nl))
            note_label.set_note_data(note_data)
            self.note_labels.append(note_label)
            # Insert before the stretch (which is the last item)
            self.notes_layout.insertWidget(self.notes_layout.count() - 1, note_label)

        # Update button state
        self.btn_add_note.setEnabled(len(self.note_labels) < 8)

        # Update empty state
        self.update_empty_state()

        # Select first note if any
        if len(self.note_labels) > 0:
            self.select_note(self.note_labels[0])




class Arpeggiator(BasicEditor):
    """Arpeggiator tab for creating and managing arpeggiator presets"""

    # HID Command constants for arpeggiator
    ARP_CMD_GET_PRESET = 0xC0
    ARP_CMD_SET_PRESET = 0xC1
    ARP_CMD_SAVE_PRESET = 0xC2
    ARP_CMD_LOAD_PRESET = 0xC3
    ARP_CMD_CLEAR_PRESET = 0xC4
    ARP_CMD_COPY_PRESET = 0xC5
    ARP_CMD_RESET_ALL = 0xC6
    ARP_CMD_GET_STATE = 0xC7
    ARP_CMD_SET_STATE = 0xC8
    ARP_CMD_GET_INFO = 0xC9

    MANUFACTURER_ID = 0x7D
    SUB_ID = 0x00
    DEVICE_ID = 0x4D

    # Signals
    hid_data_received = pyqtSignal(bytes)

    def __init__(self):
        super().__init__()

        logger.info("Arpeggiator tab initialized")

        self.current_preset_id = 0  # Presets 0-31 for arpeggiator
        self.is_step_sequencer = False  # This is the arpeggiator tab
        self.preset_data = {
            'name': 'User Preset',
            'preset_type': 0,  # PRESET_TYPE_ARPEGGIATOR
            'note_count': 0,
            'pattern_length_16ths': 16,
            'gate_length_percent': 80,
            'steps': []  # Flat list of notes with timing
        }

        self.step_widgets = []
        self.clipboard_preset = None  # Internal clipboard for copy/paste
        self.hid_data_received.connect(self.handle_hid_response)

        self.setup_ui()

    def setup_ui(self):
        """Build the UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)

        # === Status ===
        self.lbl_status = QLabel("Ready. Select a preset to begin.")
        self.lbl_status.setStyleSheet("color: #00aaff; padding: 5px;")
        # === Header Section ===
        header_layout = QHBoxLayout()

        # Preset selector
        preset_group = QGroupBox("Preset")
        preset_layout = QGridLayout()

        # === Sequencer Section with Tabs ===
        sequencer_group = QGroupBox("Arpeggiator")

        # Create tab widget for Basic and Advanced views
        self.tabs = QTabWidget()

        # === BASIC TAB ===
        self.basic_grid = BasicArpeggiatorGrid()
        self.basic_grid.dataChanged.connect(self.on_basic_grid_changed)
        self.tabs.addTab(self.basic_grid, "Basic")

        # === ADVANCED TAB ===
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout()
        advanced_layout.setContentsMargins(0, 0, 0, 0)

        # Create scrollable area for steps (Advanced UI)
        self.step_scroll = QScrollArea()
        self.step_scroll.setWidgetResizable(True)
        self.step_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.step_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.step_scroll.setMinimumHeight(300)

        self.step_container = QWidget()
        self.step_layout = QHBoxLayout()
        self.step_layout.setSpacing(2)
        self.step_layout.setDirection(QHBoxLayout.LeftToRight)  # Ensure left-to-right
        self.step_container.setLayout(self.step_layout)
        self.step_scroll.setWidget(self.step_container)

        advanced_layout.addWidget(self.step_scroll)
        advanced_tab.setLayout(advanced_layout)
        self.tabs.addTab(advanced_tab, "Advanced")

        # Connect tab change to sync data
        self.tabs.currentChanged.connect(self.on_tab_changed)

        sequencer_layout = QVBoxLayout()
        sequencer_layout.addWidget(self.tabs)
        sequencer_group.setLayout(sequencer_layout)

        main_layout.addWidget(sequencer_group, 1)

        # === Bottom Section: Two containers side by side ===
        bottom_layout = QHBoxLayout()

        # Add left spacer to push containers closer together
        bottom_layout.addStretch(1)

        # Left Container: Preset Parameters (no title)
        params_group = QGroupBox()
        params_group.setMaximumWidth(500)
        params_layout = QGridLayout()

        # Arpeggiator Mode (moved from separate section)
        lbl_mode = QLabel("Arpeggiator Mode:")
        self.combo_mode = ArrowComboBox()
        self.combo_mode.setMinimumWidth(150)
        self.combo_mode.setMaximumHeight(30)
        self.combo_mode.setEditable(True)
        self.combo_mode.lineEdit().setReadOnly(True)
        self.combo_mode.lineEdit().setAlignment(Qt.AlignCenter)
        self.combo_mode.addItem("Single Note (Classic Arp)", 0)
        self.combo_mode.addItem("Chord Basic (All Notes)", 1)
        self.combo_mode.addItem("Chord Advanced (Rotation)", 2)
        self.combo_mode.setToolTip("Select how the arpeggiator plays notes")
        params_layout.addWidget(lbl_mode, 0, 0)
        params_layout.addWidget(self.combo_mode, 0, 1)

        # Pattern Rate (now a dropdown)
        lbl_pattern_rate = QLabel("Pattern Rate:")
        self.combo_pattern_rate = ArrowComboBox()
        self.combo_pattern_rate.setMinimumWidth(150)
        self.combo_pattern_rate.setMaximumHeight(30)
        self.combo_pattern_rate.setEditable(True)
        self.combo_pattern_rate.lineEdit().setReadOnly(True)
        self.combo_pattern_rate.lineEdit().setAlignment(Qt.AlignCenter)
        self.combo_pattern_rate.addItem("1/4", 0)
        self.combo_pattern_rate.addItem("1/8", 1)
        self.combo_pattern_rate.addItem("1/16", 2)
        self.combo_pattern_rate.setCurrentIndex(2)  # Default to 1/16
        self.combo_pattern_rate.setToolTip("Note subdivision for steps")
        self.combo_pattern_rate.currentIndexChanged.connect(self.on_pattern_rate_changed)
        params_layout.addWidget(lbl_pattern_rate, 1, 0)
        params_layout.addWidget(self.combo_pattern_rate, 1, 1)

        # Number of steps
        lbl_num_steps = QLabel("Number of Steps:")
        self.spin_num_steps = QSpinBox()
        self.spin_num_steps.setRange(1, 128)
        self.spin_num_steps.setValue(8)  # Default 8 for arpeggiator
        self.spin_num_steps.setButtonSymbols(QSpinBox.UpDownArrows)
        self.spin_num_steps.setToolTip("Number of steps in the pattern")
        self.spin_num_steps.valueChanged.connect(self.on_num_steps_changed)
        params_layout.addWidget(lbl_num_steps, 2, 0)
        params_layout.addWidget(self.spin_num_steps, 2, 1)

        # Pattern rhythm (auto-calculated, read-only display)
        lbl_rhythm = QLabel("Pattern Rhythm:")
        self.lbl_pattern_length = QLabel("4/16")
        self.lbl_pattern_length.setToolTip("Total pattern rhythm (auto-calculated from steps/rate)")
        params_layout.addWidget(lbl_rhythm, 3, 0)
        params_layout.addWidget(self.lbl_pattern_length, 3, 1)

        # Gate length
        lbl_gate = QLabel("Gate Length:")
        self.spin_gate = QSpinBox()
        self.spin_gate.setRange(10, 100)
        self.spin_gate.setValue(80)
        self.spin_gate.setSuffix("%")
        self.spin_gate.setButtonSymbols(QSpinBox.UpDownArrows)
        self.spin_gate.setToolTip("Note gate length percentage")
        params_layout.addWidget(lbl_gate, 4, 0)
        params_layout.addWidget(self.spin_gate, 4, 1)

        # Default velocity
        lbl_default_velocity = QLabel("Default Velocity:")
        self.spin_default_velocity = QSpinBox()
        self.spin_default_velocity.setRange(1, 127)
        self.spin_default_velocity.setValue(127)
        self.spin_default_velocity.setButtonSymbols(QSpinBox.UpDownArrows)
        self.spin_default_velocity.setToolTip("Default velocity for new notes in basic grid")
        self.spin_default_velocity.valueChanged.connect(self.on_default_velocity_changed)
        params_layout.addWidget(lbl_default_velocity, 5, 0)
        params_layout.addWidget(self.spin_default_velocity, 5, 1)

        params_group.setLayout(params_layout)
        bottom_layout.addWidget(params_group)

        # Right Container: Preset Selection (no title)
        preset_group = QGroupBox()
        preset_group.setMaximumWidth(500)
        preset_layout = QGridLayout()

        lbl_preset = QLabel("Select Preset:")
        self.combo_preset = ArrowComboBox()
        self.combo_preset.setMinimumWidth(150)
        self.combo_preset.setMaximumHeight(30)
        self.combo_preset.setEditable(True)
        self.combo_preset.lineEdit().setReadOnly(True)
        self.combo_preset.lineEdit().setAlignment(Qt.AlignCenter)
        # Arpeggiator presets: 0-31
        for i in range(32):
            if i < 8:
                self.combo_preset.addItem(f"Factory Arp {i}", i)
            else:
                self.combo_preset.addItem(f"User Arp {i - 7}", i)
        self.combo_preset.currentIndexChanged.connect(self.on_preset_changed)

        preset_layout.addWidget(lbl_preset, 0, 0)
        preset_layout.addWidget(self.combo_preset, 0, 1, 1, 2)

        # Preset buttons - 30px tall
        button_style = "QPushButton { min-height: 30px; max-height: 30px; }"

        self.btn_load = QPushButton("Load from Device")
        self.btn_load.setStyleSheet(button_style)
        self.btn_load.clicked.connect(self.load_preset)
        self.btn_save = QPushButton("Save to Device")
        self.btn_save.setStyleSheet(button_style)
        self.btn_save.clicked.connect(self.save_preset)

        preset_layout.addWidget(self.btn_load, 1, 0, 1, 3)
        preset_layout.addWidget(self.btn_save, 2, 0, 1, 3)

        # Copy and Paste buttons - same size
        copy_paste_layout = QHBoxLayout()
        copy_paste_layout.setSpacing(5)

        self.btn_copy = QPushButton("Copy Preset")
        self.btn_copy.setStyleSheet(button_style)
        self.btn_copy.clicked.connect(self.copy_preset_to_clipboard)
        self.btn_paste = QPushButton("Paste Preset")
        self.btn_paste.setStyleSheet(button_style)
        self.btn_paste.clicked.connect(self.paste_preset_from_clipboard)

        copy_paste_layout.addWidget(self.btn_copy)
        copy_paste_layout.addWidget(self.btn_paste)

        preset_layout.addLayout(copy_paste_layout, 3, 0, 1, 3)

        # Reset All Steps button (replacing Clear All Steps)
        self.btn_reset_all = QPushButton("Reset All Steps")
        self.btn_reset_all.setStyleSheet(button_style)
        self.btn_reset_all.clicked.connect(self.reset_all_steps)
        preset_layout.addWidget(self.btn_reset_all, 4, 0, 1, 3)

        preset_group.setLayout(preset_layout)
        bottom_layout.addWidget(preset_group)

        # Add right spacer to push containers closer together
        bottom_layout.addStretch(1)

        main_layout.addLayout(bottom_layout)

        # Build initial steps
        self.rebuild_steps()

        # === Quick Actions ===
        actions_layout = QHBoxLayout()

        main_layout.addLayout(actions_layout)

        main_layout.addWidget(self.lbl_status)

        self.addLayout(main_layout)

        # Initialize default velocity in basic grid from preset container
        if hasattr(self, 'basic_grid') and hasattr(self, 'spin_default_velocity'):
            self.basic_grid.default_velocity = self.spin_default_velocity.value() * 2

        # Set default tab to Basic (index 0)
        self.tabs.setCurrentIndex(0)

        # Initialize step count from spin box to ensure basic grid is in sync
        initial_steps = self.spin_num_steps.value()
        self.basic_grid.on_steps_changed(initial_steps)

        # Initialize preset_data with current grid state (empty but with correct step count)
        self.on_basic_grid_changed()

    def rebuild_steps(self):
        """Rebuild step widgets based on step count - preserve existing data"""
        # Save existing step data before clearing
        old_step_data = []
        for widget in self.step_widgets:
            old_step_data.append(widget.get_step_data())

        # Clear existing steps
        for widget in self.step_widgets:
            self.step_layout.removeWidget(widget)
            widget.deleteLater()
        self.step_widgets.clear()

        # Remove stretch if it exists
        while self.step_layout.count() > 0:
            item = self.step_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create new steps (they will be added from left to right)
        step_count = self.spin_num_steps.value()
        for i in range(step_count):
            step_widget = StepWidget(i, is_step_sequencer=self.is_step_sequencer)

            # Restore existing step data if available from old widgets
            if i < len(old_step_data):
                step_widget.set_step_data(old_step_data[i])

            self.step_widgets.append(step_widget)
            self.step_layout.addWidget(step_widget, 0, Qt.AlignLeft)  # Explicitly align left

        self.step_layout.addStretch()  # Add stretch at the end to push steps to the left
        self.update_pattern_length_display()
        self.update_status(f"Rebuilt sequencer with {step_count} steps")

    def on_pattern_rate_changed(self, index):
        """Pattern rate changed - update pattern length display"""
        rate_text = self.combo_pattern_rate.currentText()
        self.update_pattern_length_display()
        self.update_status(f"Pattern rate changed to {rate_text}")

    def on_num_steps_changed(self, value):
        """Number of steps changed - rebuild and update pattern length"""
        self.rebuild_steps()
        # Also update basic grid's num_steps when changed from preset container
        if hasattr(self, 'basic_grid') and self.basic_grid.num_steps != value:
            self.basic_grid.on_steps_changed(value)

    def on_default_velocity_changed(self, value):
        """Default velocity changed - update basic grid"""
        if hasattr(self, 'basic_grid'):
            # Convert display value (1-127) to internal value (2-254)
            internal_value = value * 2
            self.basic_grid.default_velocity = internal_value
            self.update_status(f"Default velocity changed to {value}")

    def update_pattern_length_display(self):
        """Update the pattern length display in x/y format with halving logic"""
        # Get rate_16ths from combo box value
        rate_map = {0: 4, 1: 2, 2: 1}  # /4, /8, /16
        rate_16ths = rate_map.get(self.combo_pattern_rate.currentData(), 1)

        num_steps = self.spin_num_steps.value()

        # Calculate pattern length in 16ths
        pattern_length_16ths = rate_16ths * num_steps

        # Calculate denominator from rate (y value)
        # rate_16ths = 4 means /4, 2 means /8, 1 means /16
        # Denominator: 4 -> /4, 2 -> /8, 1 -> /16
        denominator_map = {4: 4, 2: 8, 1: 16}
        y = denominator_map.get(rate_16ths, 16)

        # x is the number of steps
        x = num_steps

        # Apply halving logic: keep halving both x and y if possible, stop at y=4
        import math
        while x % 2 == 0 and y % 2 == 0 and y > 4:
            x = x // 2
            y = y // 2

        self.lbl_pattern_length.setText(f"{x}/{y}")

    def _get_complete_steps_from_grid(self, grid_data, num_steps, rate_16ths):
        """Helper: Convert basic grid data to steps array (no empty placeholders needed)"""
        # Group grid data by timing to see which steps have notes
        notes_by_timing = {}
        for note in grid_data:
            timing = note['timing_16ths']
            if timing not in notes_by_timing:
                notes_by_timing[timing] = []
            notes_by_timing[timing].append(note)

        # Build steps array - only include steps that have notes
        # Empty steps are simply absent from the data
        complete_steps = []
        for step_idx in range(num_steps):
            step_timing = step_idx * rate_16ths

            if step_timing in notes_by_timing:
                # This step has notes from the grid - use them
                complete_steps.extend(notes_by_timing[step_timing])
            # No else - empty steps are not represented

        return complete_steps

    def on_basic_grid_changed(self):
        """Handle changes in basic grid - live update preset data"""
        # Get current rate
        rate_map = {0: 4, 1: 2, 2: 1}
        rate_16ths = rate_map.get(self.combo_pattern_rate.currentData(), 1)

        # Get grid data (flat list with timing) - ONLY returns active cells
        grid_data = self.basic_grid.get_grid_data(rate_16ths)

        # Get complete steps
        num_steps = self.spin_num_steps.value()

        complete_steps = self._get_complete_steps_from_grid(grid_data, num_steps, rate_16ths)

        # Update preset_data with COMPLETE steps (including empty ones)
        self.preset_data['steps'] = complete_steps
        self.preset_data['note_count'] = len(complete_steps)

        # Calculate pattern length
        self.preset_data['pattern_length_16ths'] = rate_16ths * num_steps

        # Note: Don't rebuild advanced view here - only sync when switching tabs

    def on_tab_changed(self, index):
        """Handle tab switching - sync data between views"""
        if index == 0:  # Switched to Basic tab
            # Sync data from Advanced to Basic
            self.sync_advanced_to_basic()
        elif index == 1:  # Switched to Advanced tab
            # Sync data from Basic to Advanced
            self.sync_basic_to_advanced()

    def sync_advanced_to_basic(self):
        """Sync data from Advanced view to Basic grid"""
        # Gather current data from advanced view
        self.gather_preset_data()

        # Get current rate
        rate_map = {0: 4, 1: 2, 2: 1}
        rate_16ths = rate_map.get(self.combo_pattern_rate.currentData(), 1)

        # preset_data['steps'] is already a flat list with timing_16ths
        # Just pass it directly to the basic grid
        flat_notes = self.preset_data.get('steps', [])
        num_steps = self.spin_num_steps.value()

        # Set grid data (includes num_steps sync and rate)
        self.basic_grid.set_grid_data(flat_notes, num_steps, rate_16ths)

    def sync_basic_to_advanced(self):
        """Sync data from Basic grid to Advanced view"""
        # Calculate rate to determine timing for each step
        rate_map = {0: 4, 1: 2, 2: 1}
        rate_16ths = rate_map.get(self.combo_pattern_rate.currentData(), 1)

        # Get grid data (flat list with timing) - ONLY returns active cells
        grid_data = self.basic_grid.get_grid_data(rate_16ths)

        # Number of steps comes from preset container (spin_num_steps)
        num_steps = self.spin_num_steps.value()

        # Ensure basic grid is in sync with preset container
        if self.basic_grid.num_steps != num_steps:
            self.basic_grid.on_steps_changed(num_steps)

        # Get complete steps including Empty placeholders for empty steps
        complete_steps = self._get_complete_steps_from_grid(grid_data, num_steps, rate_16ths)

        # Update preset_data with COMPLETE steps (including empty ones)
        self.preset_data['steps'] = complete_steps
        self.preset_data['note_count'] = len(complete_steps)

        # CRITICAL: Update pattern_length and gate from preset container before applying
        # These are the authoritative source and must be synced to preset_data
        self.preset_data['pattern_length_16ths'] = rate_16ths * num_steps
        self.preset_data['gate_length_percent'] = self.spin_gate.value()

        # Rebuild advanced view using apply_preset_data
        # Use recalculate_from_pattern_length=False to preserve existing num_steps and rate
        # (we already have the correct values from the UI controls)
        self.apply_preset_data(recalculate_from_pattern_length=False)

    def reset_all_steps(self):
        """Reset all steps to empty (with confirmation)"""
        reply = QMessageBox.question(
            None,
            "Reset All Steps",
            "Are you sure you want to clear all notes from all steps?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for widget in self.step_widgets:
                widget.set_step_data([])  # Empty list of notes
            self.update_status("All steps reset to empty")

    def copy_preset_to_clipboard(self):
        """Copy current preset data to internal clipboard"""
        self.gather_preset_data()
        self.clipboard_preset = self.preset_data.copy()
        self.clipboard_preset['steps'] = [step.copy() for step in self.preset_data['steps']]
        self.update_status("Preset copied to clipboard")

    def paste_preset_from_clipboard(self):
        """Paste preset data from internal clipboard"""
        if not hasattr(self, 'clipboard_preset') or self.clipboard_preset is None:
            self.update_status("No preset in clipboard", error=True)
            return

        self.preset_data = self.clipboard_preset.copy()
        self.preset_data['steps'] = [step.copy() for step in self.clipboard_preset['steps']]
        self.apply_preset_data()
        self.update_status("Preset pasted from clipboard")

    def gather_preset_data(self):
        """Gather current UI state into preset_data dict - preserves ALL notes including empty ones"""
        # Calculate pattern length from rate × steps
        rate_map = {0: 4, 1: 2, 2: 1}  # /4, /8, /16
        rate_16ths = rate_map.get(self.combo_pattern_rate.currentData(), 1)
        num_steps = self.spin_num_steps.value()
        self.preset_data['pattern_length_16ths'] = rate_16ths * num_steps
        self.preset_data['gate_length_percent'] = self.spin_gate.value()
        self.preset_data['preset_type'] = 0  # PRESET_TYPE_ARPEGGIATOR

        # Gather notes from all steps
        # Each step can have multiple notes, all at the same timing
        # IMPORTANT: Preserve ALL notes including empty ones (semitone_offset = -1) for tab switching
        all_notes = []
        for i, widget in enumerate(self.step_widgets):
            step_notes = widget.get_step_data()  # Returns list of note dicts
            timing_16ths = i * rate_16ths

            for note_data in step_notes:
                # Add timing to note
                note_data['timing_16ths'] = timing_16ths

                # Convert to firmware format
                if self.is_step_sequencer:
                    # Step sequencer: note_index already contains absolute note (0-11)
                    # octave_offset contains absolute octave (0-7)
                    pass  # Data is already in the right format
                else:
                    # Arpeggiator: Convert flat semitones to (interval, octave) for firmware
                    # GUI stores semitone_offset and octave_offset separately
                    # Firmware needs them combined as flat semitones, then split into note_index and octave_offset
                    semitone = note_data.get('semitone_offset', 0)
                    octave = note_data.get('octave_offset', 0)

                    # Convert to flat semitones
                    flat_semitones = interval_octave_to_flat_semitones(semitone, octave)

                    # Convert back to firmware format (interval within octave + octave offset)
                    interval, octave_offset = flat_semitones_to_interval_octave(flat_semitones)

                    # Store in firmware format
                    note_data['note_index'] = interval
                    note_data['octave_offset'] = octave_offset

                # Raw travel is velocity
                note_data['raw_travel'] = note_data.get('velocity', 200)

                all_notes.append(note_data)

        self.preset_data['steps'] = all_notes
        # Note count includes ALL notes for internal tracking - firmware will filter empty ones
        self.preset_data['note_count'] = len(all_notes)

        # Keep name in data structure for firmware compatibility
        if 'name' not in self.preset_data:
            self.preset_data['name'] = 'User Preset'

    def get_firmware_notes(self):
        """Get notes for firmware - all notes are valid (no empty placeholders exist)"""
        # Return all notes - there are no empty placeholders to filter
        return self.preset_data.get('steps', [])

    def apply_preset_data(self, recalculate_from_pattern_length=True):
        """Apply preset_data to UI - convert flat note list to step-based structure

        Args:
            recalculate_from_pattern_length: If True, recalculate num_steps and rate from
                pattern_length_16ths (used when loading from device/clipboard).
                If False, use existing UI values (used when syncing from Basic to Advanced).
        """
        self.spin_gate.setValue(self.preset_data.get('gate_length_percent', 80))

        # Convert flat note list back to step-based structure
        # Group notes by timing
        notes_by_timing = {}
        for note in self.preset_data.get('steps', []):
            timing = note.get('timing_16ths', 0)
            if timing not in notes_by_timing:
                notes_by_timing[timing] = []
            notes_by_timing[timing].append(note)

        # Determine number of steps from pattern length and rate
        rate_map = {0: 4, 1: 2, 2: 1}

        if recalculate_from_pattern_length:
            # Recalculate num_steps and rate from pattern_length_16ths
            # (used when loading preset from device or clipboard)
            pattern_length = self.preset_data.get('pattern_length_16ths', 16)

            # Find rate that matches the pattern
            for rate_index, rate_16ths in rate_map.items():
                num_steps = pattern_length // rate_16ths
                if pattern_length % rate_16ths == 0 and 1 <= num_steps <= 128:
                    self.combo_pattern_rate.setCurrentIndex(rate_index)
                    self.spin_num_steps.setValue(num_steps)
                    break
            else:
                # Fallback: use 1/16 notes
                self.combo_pattern_rate.setCurrentIndex(2)
                self.spin_num_steps.setValue(max(1, min(128, pattern_length // 16)))

        # Rebuild steps and populate with notes
        self.rebuild_steps()

        # Populate steps with notes
        rate_16ths = rate_map.get(self.combo_pattern_rate.currentData(), 1)
        for i, widget in enumerate(self.step_widgets):
            step_timing = i * rate_16ths
            step_notes = notes_by_timing.get(step_timing, [])
            widget.set_step_data(step_notes)

    def on_preset_changed(self, index):
        """Preset selection changed"""
        self.current_preset_id = index

        # Update UI state
        is_factory = (index < 8)
        self.btn_save.setEnabled(not is_factory)

        if is_factory:
            self.update_status(f"Factory preset {index} selected (read-only)")
        else:
            self.update_status(f"User preset {index} selected")

    def send_hid_command(self, cmd, params):
        """Send HID command to device"""
        if not isinstance(self.device, VialKeyboard):
            self.update_status("Error: Device not connected", error=True)
            return False

        # Build HID packet
        data = bytearray(32)
        data[0] = self.MANUFACTURER_ID
        data[1] = self.SUB_ID
        data[2] = self.DEVICE_ID
        data[3] = cmd

        # Add parameters
        for i, param in enumerate(params):
            if i + 4 < len(data):
                if isinstance(param, int):
                    data[i + 4] = param & 0xFF
                elif isinstance(param, str):
                    # String encoding
                    encoded = param.encode('ascii')[:16]
                    for j, byte in enumerate(encoded):
                        if i + 4 + j < len(data):
                            data[i + 4 + j] = byte
                    break

        try:
            self.device.keyboard.raw_hid_send(bytes(data))
            logger.info(f"Sent HID command: 0x{cmd:02X}")
            return True
        except Exception as e:
            logger.error(f"HID send error: {e}")
            self.update_status(f"HID error: {e}", error=True)
            return False

    def handle_hid_response(self, data):
        """Handle HID response from device"""
        if len(data) < 4:
            return

        cmd = data[3]
        status = data[4] if len(data) > 4 else 0xFF

        if status == 0:
            self.update_status("Command successful")

            if cmd == self.ARP_CMD_GET_PRESET:
                # Parse preset data
                name = data[5:21].decode('ascii', errors='ignore').rstrip('\x00')
                note_count = data[21] if len(data) > 21 else 0
                pattern_length = ((data[22] << 8) | data[23]) if len(data) > 23 else 16
                gate_length = data[24] if len(data) > 24 else 80

                self.preset_data['name'] = name
                self.preset_data['note_count'] = note_count
                self.preset_data['pattern_length_16ths'] = pattern_length
                self.preset_data['gate_length_percent'] = gate_length

                self.apply_preset_data()
                self.update_status(f"Loaded preset: {name}")
        else:
            error_msg = {
                1: "Error: Invalid preset or operation failed",
                0xFF: "Error: Unknown command"
            }.get(status, f"Error: Status code {status}")
            self.update_status(error_msg, error=True)

    def load_preset(self):
        """Load preset from device via HID"""
        self.gather_preset_data()

        preset_id = self.current_preset_id
        self.send_hid_command(self.ARP_CMD_GET_PRESET, [preset_id])
        self.update_status(f"Requesting preset {preset_id} from device...")

    def save_preset(self):
        """Save preset to device via HID"""
        if self.current_preset_id < 8:
            self.update_status("Cannot save to factory preset!", error=True)
            return

        self.gather_preset_data()

        # Get filtered notes for firmware (excludes empty arpeggiator notes)
        firmware_notes = self.get_firmware_notes()
        firmware_note_count = len(firmware_notes)

        # Build parameter list
        params = [self.current_preset_id]
        params.append(self.preset_data['name'])  # String will be encoded in send_hid_command
        params.extend([0] * (16 - len(self.preset_data['name'])))  # Padding
        params.append(firmware_note_count)  # Use filtered count for firmware
        params.append((self.preset_data['pattern_length_16ths'] >> 8) & 0xFF)
        params.append(self.preset_data['pattern_length_16ths'] & 0xFF)
        params.append(self.preset_data['gate_length_percent'])

        if self.send_hid_command(self.ARP_CMD_SET_PRESET, params):
            # Also save to EEPROM
            QTimer.singleShot(100, lambda: self.send_hid_command(
                self.ARP_CMD_SAVE_PRESET, [self.current_preset_id]))
            self.update_status(f"Saving preset {self.current_preset_id}...")

    def update_status(self, message, error=False):
        """Update status label"""
        logger.info(message)
        self.lbl_status.setText(message)
        if error:
            self.lbl_status.setStyleSheet("color: #ff4444; padding: 5px;")
        else:
            self.lbl_status.setStyleSheet("color: #00aaff; padding: 5px;")

    def valid(self):
        """Check if this tab should be visible"""
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        """Rebuild for new device"""
        super().rebuild(device)

        if self.valid():
            self.update_status("Arpeggiator ready")
            # Request system info
            self.send_hid_command(self.ARP_CMD_GET_INFO, [])
        else:
            self.update_status("Connect a Vial device to use arpeggiator")

    def activate(self):
        """Tab activated"""
        logger.info("Arpeggiator tab activated")

    def deactivate(self):
        """Tab deactivated"""
        logger.info("Arpeggiator tab deactivated")


class StepSequencer(Arpeggiator):
    """Step Sequencer tab - plays absolute MIDI notes independently"""

    def __init__(self):
        # Call parent but override key attributes
        BasicEditor.__init__(self)

        logger.info("Step Sequencer tab initialized")

        self.current_preset_id = 32  # Presets 32-63 for step sequencer
        self.is_step_sequencer = True  # This is the step sequencer tab
        self.preset_data = {
            'name': 'User Seq',
            'preset_type': 1,  # PRESET_TYPE_STEP_SEQUENCER
            'note_count': 0,
            'pattern_length_16ths': 16,
            'gate_length_percent': 80,
            'steps': []  # Flat list of notes with timing
        }

        self.step_widgets = []
        self.clipboard_preset = None  # Internal clipboard for copy/paste
        self.hid_data_received.connect(self.handle_hid_response)

        self.setup_ui()

    def setup_ui(self):
        """Build the UI - override to use step sequencer grid and customize preset selector"""
        # Call parent setup_ui first
        super().setup_ui()

        # Set default steps to 16 for step sequencer
        self.spin_num_steps.setValue(16)

        # Replace the arpeggiator grid with step sequencer grid
        self.tabs.removeTab(0)  # Remove the Basic tab (arpeggiator grid)

        # Create step sequencer grid
        self.basic_grid = BasicStepSequencerGrid()
        self.basic_grid.dataChanged.connect(self.on_basic_grid_changed)
        self.tabs.insertTab(0, self.basic_grid, "Basic")

        # Sync the default rows from Basic grid to preset_data
        # This prevents them from being cleared when setCurrentIndex triggers on_tab_changed
        rate_map = {0: 4, 1: 2, 2: 1}
        rate_16ths = rate_map.get(self.combo_pattern_rate.currentData(), 1)
        grid_data = self.basic_grid.get_grid_data(rate_16ths)
        self.preset_data['steps'] = grid_data
        self.preset_data['note_count'] = len(grid_data)

        # Update group box title
        sequencer_group = self.findChild(QGroupBox, "")
        for child in self.findChildren(QGroupBox):
            if child.title() == "Arpeggiator":
                child.setTitle("Step Sequencer")
                break

        # Update preset selector for step sequencer range (32-63)
        self.combo_preset.clear()
        for i in range(32, 64):
            if i < 40:
                self.combo_preset.addItem(f"Factory Seq {i - 31}", i)
            else:
                self.combo_preset.addItem(f"User Seq {i - 39}", i)

        # Set default to first step sequencer preset
        self.combo_preset.setCurrentIndex(0)

        # Set default tab to Basic (index 0)
        self.tabs.setCurrentIndex(0)

    def gather_preset_data(self):
        """Override to set preset_type to step sequencer"""
        super().gather_preset_data()
        self.preset_data['preset_type'] = 1  # PRESET_TYPE_STEP_SEQUENCER

    def activate(self):
        """Tab activated"""
        logger.info("Step Sequencer tab activated")

    def deactivate(self):
        """Tab deactivated"""
        logger.info("Step Sequencer tab deactivated")
