# SPDX-License-Identifier: GPL-2.0-or-later
"""Keymap tuning presets for the orthomidi5x14 keyboard (5 rows x 14 columns).

Each preset defines a musical tuning layout mapping MIDI note keycodes
to the 70-key grid. Presets are designed for different playing styles
and musical theory concepts.

Grid convention:
  - Row 0 = top row (visually / matrix), Row 4 = bottom row
  - User-facing labels use 1-5 (Row 1 = top, Row 5 = bottom)
  - Lower notes are placed at the bottom, higher at top
  - Col 0 = leftmost, Col 13 = rightmost

Preset types:
  - TUNING: Multi-row note layouts that scale to selected rows
  - SINGLE_ROW: Function key rows (loop, arp, etc.) applied to one row
  - ENCODER: Encoder assignments (separate from the grid)
"""

# Chromatic note names matching QMK MI_* keycode naming
CHROMATIC_NAMES = ['C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B']

ROWS = 5
COLS = 14

# Preset type constants
PRESET_TYPE_TUNING = "tuning"
PRESET_TYPE_SINGLE_ROW = "single_row"


def note_to_keycode(note_index):
    """Convert 0-71 note index to MI_* keycode string.

    Note indices: 0=C0, 1=C#0, ..., 11=B0, 12=C1, ..., 71=B5.
    Returns KC_NO if out of the valid 0-71 range.
    """
    if note_index < 0 or note_index > 71:
        return "KC_NO"
    octave = note_index // 12
    note = note_index % 12
    name = CHROMATIC_NAMES[note]
    if octave == 0:
        return "MI_{}".format(name)
    return "MI_{}_{}".format(name, octave)


def _make_grid(num_rows):
    """Create a num_rows x 14 grid filled with KC_NO."""
    return [["KC_NO"] * COLS for _ in range(num_rows)]


def _fill_grid_continuous(notes, num_rows):
    """Fill grid bottom-to-top, left-to-right with given note indices."""
    grid = _make_grid(num_rows)
    idx = 0
    for row in range(num_rows - 1, -1, -1):  # bottom to top
        for col in range(COLS):
            if idx < len(notes):
                grid[row][col] = note_to_keycode(notes[idx])
                idx += 1
    return grid


def _generate_scale_notes(root, intervals, start_octave=1, end_octave=5):
    """Generate all note indices for a scale across an octave range.

    root: root note offset (0=C, 1=C#, 2=D, etc.)
    intervals: semitone offsets from root within one octave
    """
    notes = []
    for octave in range(start_octave, end_octave + 1):
        for interval in intervals:
            note = octave * 12 + root + interval
            if 0 <= note <= 71:
                notes.append(note)
    return sorted(notes)


# ── Tuning Preset Generators ──────────────────────────────────────────────────
# All tuning generators accept num_rows (1-5) and scale accordingly.


def preset_chromatic(num_rows=5):
    """Linear chromatic: every semitone from C1 upward."""
    notes = list(range(12, 72))  # C1 through B5 (60 notes)
    return _fill_grid_continuous(notes, num_rows)


def preset_octave_rows(num_rows=5):
    """Each row is one complete chromatic octave starting on C."""
    grid = _make_grid(num_rows)
    for i in range(num_rows):
        row = num_rows - 1 - i  # bottom to top
        octave = i + 1  # octaves 1 through num_rows
        base = octave * 12
        for col in range(12):
            note = base + col
            if note <= 71:
                grid[row][col] = note_to_keycode(note)
    return grid


def preset_guitar_standard(num_rows=5):
    """Standard guitar tuning: EADGB strings from bottom to top."""
    # Full 5-string bases: E1, A1, D2, G2, B2
    all_bases = [16, 21, 26, 31, 35]
    bases = all_bases[:num_rows]
    grid = _make_grid(num_rows)
    for i, base in enumerate(bases):
        row = num_rows - 1 - i
        for col in range(COLS):
            grid[row][col] = note_to_keycode(base + col)
    return grid


def preset_guitar_fourths(num_rows=5):
    """All-fourths tuning: EADGC strings from bottom to top."""
    grid = _make_grid(num_rows)
    for i in range(num_rows):
        row = num_rows - 1 - i
        base = 16 + i * 5  # E1=16, then +5 per string
        for col in range(COLS):
            grid[row][col] = note_to_keycode(base + col)
    return grid


def preset_wicki_hayden(num_rows=5):
    """Wicki-Hayden isomorphic layout.
    Columns: +2 semitones (whole tone). Rows up: +5 (perfect fourth)."""
    grid = _make_grid(num_rows)
    base = 24  # C2
    for i in range(num_rows):
        row = num_rows - 1 - i
        row_base = base + i * 5
        for col in range(COLS):
            note = row_base + col * 2
            grid[row][col] = note_to_keycode(note)
    return grid


def preset_janko(num_rows=5):
    """Janko keyboard isomorphic layout.
    Whole tones per row, odd rows offset by one semitone."""
    grid = _make_grid(num_rows)
    for i in range(num_rows):
        row = num_rows - 1 - i
        pair = i // 2
        offset = i % 2
        base = 24 + pair * 12 + offset
        for col in range(COLS):
            note = base + col * 2
            grid[row][col] = note_to_keycode(note)
    return grid


def preset_c_major(num_rows=5):
    """C Major diatonic scale with overlapping octave rows."""
    major = [0, 2, 4, 5, 7, 9, 11]
    grid = _make_grid(num_rows)
    for i in range(num_rows):
        row = num_rows - 1 - i
        start_octave = i + 1
        notes = _generate_scale_notes(0, major, start_octave, start_octave + 1)
        for col in range(min(COLS, len(notes))):
            grid[row][col] = note_to_keycode(notes[col])
    return grid


def preset_fifths(num_rows=5):
    """Chromatic rows separated by perfect fifths (+7 semitones)."""
    grid = _make_grid(num_rows)
    base = 12  # C1
    for i in range(num_rows):
        row = num_rows - 1 - i
        row_base = base + i * 7
        for col in range(COLS):
            grid[row][col] = note_to_keycode(row_base + col)
    return grid


def preset_major_thirds(num_rows=5):
    """Chromatic rows separated by major thirds (+4 semitones)."""
    grid = _make_grid(num_rows)
    base = 12  # C1
    for i in range(num_rows):
        row = num_rows - 1 - i
        row_base = base + i * 4
        for col in range(COLS):
            grid[row][col] = note_to_keycode(row_base + col)
    return grid


# ── Single-Row Function Presets ───────────────────────────────────────────────
# Each returns a single list of 14 keycodes.


def preset_row_loop_control():
    """Loop/macro control row."""
    return [
        "DM_MACRO_1", "DM_MACRO_2", "DM_MACRO_3", "DM_MACRO_4",
        "DM_MUTE", "DM_OVERDUB", "DM_PLAY_PAUSE", "DM_UNSYNC",
        "DM_SPEED_ALL", "DM_SLOW_ALL", "DM_RESET_SPEED",
        "DM_SAVE_ALL", "DM_COPY", "DM_SAMPLE",
    ]


def preset_row_smart_chord():
    """Smart chord row - 13 chord presets + cycle down."""
    return [
        "MI_CHORD_0", "MI_CHORD_1", "MI_CHORD_2", "MI_CHORD_3",
        "MI_CHORD_4", "MI_CHORD_5", "MI_CHORD_6", "MI_CHORD_7",
        "MI_CHORD_8", "MI_CHORD_9", "MI_CHORD_10", "MI_CHORD_11",
        "MI_CHORD_12", "SMARTCHORD_DOWN",
    ]


def preset_row_arpeggiator():
    """Arpeggiator control row."""
    return [
        "ARP_PLAY", "ARP_NEXT_PRESET", "ARP_PREV_PRESET",
        "ARP_RATE_UP", "ARP_RATE_DOWN", "ARP_GATE_UP", "ARP_GATE_DOWN",
        "ARP_RATE_EIGHTH", "ARP_RATE_SIXTEENTH", "ARP_RATE_QUARTER",
        "ARP_MODE_SINGLE", "ARP_MODE_CHORD_BASIC",
        "ARP_SYNC_MODE", "ARP_RESET_OVERRIDES",
    ]


def preset_row_step_sequencer():
    """Step sequencer control row."""
    return [
        "SEQ_PLAY", "SEQ_STOP_ALL", "SEQ_NEXT_PRESET", "SEQ_PREV_PRESET",
        "SEQ_RATE_UP", "SEQ_RATE_DOWN", "SEQ_GATE_UP", "SEQ_GATE_DOWN",
        "SEQ_RATE_EIGHTH", "SEQ_RATE_SIXTEENTH", "SEQ_RATE_QUARTER",
        "SEQ_SYNC_MODE", "SEQ_RESET_OVERRIDES", "SEQ_MOD_1",
    ]


def preset_row_ear_training():
    """Ear training row - grouped by type, levels 1-3."""
    return [
        # Basic intervals L1-L3
        "MI_ET_1", "MI_ET_2", "MI_ET_13",
        # Octave intervals L1-L3
        "MI_ET_4", "MI_ET_5", "MI_ET_14",
        # Extended intervals L1-L3
        "MI_ET_7", "MI_ET_8", "MI_ET_15",
        # All intervals L1-L3
        "MI_ET_10", "MI_ET_11", "MI_ET_16",
        "KC_NO", "KC_NO",
    ]


def preset_row_chord_training():
    """Chord training row - grouped by type, levels 1-4."""
    return [
        # Triads L1-L4
        "MI_CET_1", "MI_CET_6", "MI_CET_11", "MI_CET_16",
        # Basic 7ths L1-L4
        "MI_CET_2", "MI_CET_7", "MI_CET_12", "MI_CET_17",
        # All 7ths L1-L4
        "MI_CET_3", "MI_CET_8", "MI_CET_13", "MI_CET_18",
        # Triads & Basic 7ths L1-L2
        "MI_CET_4", "MI_CET_9",
    ]


def preset_row_transport():
    """Transport / utility control row."""
    return [
        "MI_ALLOFF", "MI_SUS", "MI_SOFT", "MI_SOST",
        "MI_PORT", "MI_LEG",
        "MI_OCTU", "MI_OCTD", "MI_TRNSU", "MI_TRNSD",
        "MI_CHU", "MI_CHD", "MI_BENDU", "MI_BENDD",
    ]


# ── Encoder Presets ───────────────────────────────────────────────────────────
# Each entry: (name, description, enc1_cw, enc1_ccw, enc1_press,
#              enc2_cw, enc2_ccw, enc2_press)

ENCODER_PRESETS = [
    (
        "Volume + Octave",
        "Enc 1: Volume Up/Down/Mute. Enc 2: Octave Up/Down/All Notes Off.",
        "KC_VOLU", "KC_VOLD", "KC_MUTE",
        "MI_OCTU", "MI_OCTD", "MI_ALLOFF",
    ),
    (
        "Octave + Transpose",
        "Enc 1: Octave Up/Down/All Notes Off. Enc 2: Transpose Up/Down/Reset.",
        "MI_OCTU", "MI_OCTD", "MI_ALLOFF",
        "MI_TRNSU", "MI_TRNSD", "MI_TRNS_0",
    ),
    (
        "BPM + Arp Rate",
        "Enc 1: BPM Up/Down/Play-Pause. Enc 2: Arp Rate Up/Down/Play.",
        "BPM_UP", "BPM_DOWN", "DM_PLAY_PAUSE",
        "ARP_RATE_UP", "ARP_RATE_DOWN", "ARP_PLAY",
    ),
    (
        "Program + Bank",
        "Enc 1: Program Change Up/Down/All Off. Enc 2: Bank Up/Down/Mute.",
        "MI_PROG_UP", "MI_PROG_DWN", "MI_ALLOFF",
        "MI_BANK_UP", "MI_BANK_DWN", "KC_MUTE",
    ),
    (
        "Channel + Velocity",
        "Enc 1: MIDI Channel Up/Down/All Off. Enc 2: Velocity Up/Down/Mute.",
        "MI_CHU", "MI_CHD", "MI_ALLOFF",
        "MI_VELOCITY_UP", "MI_VELOCITY_DOWN", "KC_MUTE",
    ),
    (
        "Pitch Bend + Mod",
        "Enc 1: Pitch Bend Up/Down/All Off. Enc 2: Mod Speed Up/Down/Mod.",
        "MI_BENDU", "MI_BENDD", "MI_ALLOFF",
        "MI_MODSU", "MI_MODSD", "MI_MOD",
    ),
]


# ── Preset Registries ─────────────────────────────────────────────────────────
# Tuning presets: (name, description, generator_func)
# generator_func(num_rows) -> list of lists of keycodes

TUNING_PRESETS = [
    (
        "Chromatic",
        "Linear chromatic from C1. Every semitone in order, bottom-to-top.",
        preset_chromatic,
    ),
    (
        "Octave Rows",
        "Each row is one chromatic octave (C to B). C1 through B5.",
        preset_octave_rows,
    ),
    (
        "Guitar Standard",
        "Guitar fretboard: EADGB tuning. 14 frets per string.",
        preset_guitar_standard,
    ),
    (
        "Guitar All Fourths",
        "All-fourths tuning (EADGC). Consistent intervals between strings.",
        preset_guitar_fourths,
    ),
    (
        "Wicki-Hayden",
        "Isomorphic: whole tones horizontal, fourths vertical. Same shapes in all keys.",
        preset_wicki_hayden,
    ),
    (
        "Janko",
        "Janko keyboard: whole tones per row, offset by semitone. Uniform fingering.",
        preset_janko,
    ),
    (
        "C Major Scale",
        "Diatonic C major (white notes). Overlapping 2-octave rows. No wrong notes.",
        preset_c_major,
    ),
    (
        "Fifths",
        "Chromatic rows separated by perfect fifths. Circle of fifths = vertical line.",
        preset_fifths,
    ),
    (
        "Major Thirds",
        "Chromatic rows separated by major thirds. 3 rows up = 1 octave.",
        preset_major_thirds,
    ),
]

# Single-row presets: (name, description, generator_func)
# generator_func() -> list of 14 keycodes

SINGLE_ROW_PRESETS = [
    (
        "Loop Control",
        "Loop macros 1-4, mute, overdub, play/pause, sync, speed, save.",
        preset_row_loop_control,
    ),
    (
        "Smart Chord",
        "13 smart chord presets (one per root note) + cycle chord type.",
        preset_row_smart_chord,
    ),
    (
        "Arpeggiator",
        "Arp play, preset nav, rate/gate controls, modes, sync.",
        preset_row_arpeggiator,
    ),
    (
        "Step Sequencer",
        "Seq play/stop, preset nav, rate/gate controls, sync, mod.",
        preset_row_step_sequencer,
    ),
    (
        "Ear Training",
        "12 ear training modes: Basic/Octave/Extended/All intervals, levels 1-3.",
        preset_row_ear_training,
    ),
    (
        "Chord Training",
        "14 chord training modes: Triads/7ths/All 7ths/Combined, levels 1-4.",
        preset_row_chord_training,
    ),
    (
        "Transport / Utility",
        "All notes off, sustain, soft, sostenuto, octave, transpose, channel, bend.",
        preset_row_transport,
    ),
]

# Combined list for the dropdown (with category markers)
# Category markers use None as the generator to indicate a separator
KEYMAP_PRESETS = []
KEYMAP_PRESETS.append(("--- Tuning (Multi-Row) ---", "", None, PRESET_TYPE_TUNING))
for name, desc, gen in TUNING_PRESETS:
    KEYMAP_PRESETS.append((name, desc, gen, PRESET_TYPE_TUNING))
KEYMAP_PRESETS.append(("--- Single Row ---", "", None, PRESET_TYPE_SINGLE_ROW))
for name, desc, gen in SINGLE_ROW_PRESETS:
    KEYMAP_PRESETS.append((name, desc, gen, PRESET_TYPE_SINGLE_ROW))
