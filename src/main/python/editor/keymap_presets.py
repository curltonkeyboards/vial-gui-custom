# SPDX-License-Identifier: GPL-2.0-or-later
"""Keymap tuning presets for the orthomidi5x14 keyboard (5 rows x 14 columns).

Each preset defines a musical tuning layout mapping MIDI note keycodes
to the 70-key grid. Presets are designed for different playing styles
and musical theory concepts.

Grid convention:
  - Row 0 = top row (visually), Row 4 = bottom row
  - Lower notes are placed at the bottom (row 4), higher at top (row 0)
  - Col 0 = leftmost, Col 13 = rightmost
"""

# Chromatic note names matching QMK MI_* keycode naming
CHROMATIC_NAMES = ['C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B']

ROWS = 5
COLS = 14


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


def _make_empty_grid():
    """Create a 5x14 grid filled with KC_NO."""
    return [["KC_NO"] * COLS for _ in range(ROWS)]


def _fill_grid_continuous(notes):
    """Fill grid bottom-to-top, left-to-right with given note indices."""
    grid = _make_empty_grid()
    idx = 0
    for row in range(ROWS - 1, -1, -1):  # row 4 (bottom) to row 0 (top)
        for col in range(COLS):
            if idx < len(notes):
                grid[row][col] = note_to_keycode(notes[idx])
                idx += 1
    return grid


def _generate_scale_notes(root, intervals, start_octave=0, end_octave=5):
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


# ── Preset Generators ──────────────────────────────────────────────────────────


def preset_chromatic():
    """Linear chromatic: every semitone from C0 upward.

    Left-to-right, bottom-to-top. Covers C0 to A#5 (70 of 72 available notes).
    The most straightforward layout - each key is one semitone higher than the
    previous. Good as a reference layout.
    """
    notes = list(range(0, 70))  # C0 through A#5
    return _fill_grid_continuous(notes)


def preset_octave_rows():
    """Each row is one complete chromatic octave starting on C.

    5 rows = 5 octaves (C1 through B5). The last 2 columns of each row are
    blank. Octave relationships are immediately visible as vertical columns.
    """
    grid = _make_empty_grid()
    for i in range(5):
        row = 4 - i  # bottom to top
        octave = i + 1  # octaves 1 through 5
        base = octave * 12
        for col in range(12):
            note = base + col
            if note <= 71:
                grid[row][col] = note_to_keycode(note)
    return grid


def preset_guitar_standard():
    """Standard guitar tuning: EADGB strings from bottom to top.

    Each row is a guitar string with 14 frets (semitones). String intervals
    match standard guitar: E-A (+5), A-D (+5), D-G (+5), G-B (+4).
    Familiar to guitarists - chord shapes transfer directly.
    """
    # String open notes: E1, A1, D2, G2, B2
    string_bases = [16, 21, 26, 31, 35]
    grid = _make_empty_grid()
    for i, base in enumerate(string_bases):
        row = 4 - i  # bottom string = bottom row
        for col in range(COLS):
            grid[row][col] = note_to_keycode(base + col)
    return grid


def preset_guitar_fourths():
    """All-fourths tuning: EADGC strings from bottom to top.

    Like guitar but every string interval is a perfect fourth (+5 semitones).
    More regular than standard tuning - all chord and scale shapes stay
    consistent across all strings.
    """
    # String open notes: E1, A1, D2, G2, C3
    string_bases = [16, 21, 26, 31, 36]
    grid = _make_empty_grid()
    for i, base in enumerate(string_bases):
        row = 4 - i
        for col in range(COLS):
            grid[row][col] = note_to_keycode(base + col)
    return grid


def preset_wicki_hayden():
    """Wicki-Hayden isomorphic layout.

    Columns advance by whole tone (+2 semitones). Each row up shifts by a
    perfect fourth (+5 semitones). Used on concertinas and modern isomorphic
    controllers. Any scale or chord has the same fingering pattern in every key.
    """
    grid = _make_empty_grid()
    base = 24  # C2
    for i in range(5):
        row = 4 - i
        row_base = base + i * 5  # +5 (perfect fourth) per row up
        for col in range(COLS):
            note = row_base + col * 2  # +2 (whole tone) per column
            grid[row][col] = note_to_keycode(note)
    return grid


def preset_janko():
    """Janko keyboard isomorphic layout.

    Each row advances by whole tones (+2 semitones per column). Even rows
    (bottom, middle, top) start on C; odd rows start on C# (+1 offset).
    Each row pair covers one octave higher. The same visual pattern plays
    the same chord in any key - a favorite of chromatic keyboard designers.
    """
    grid = _make_empty_grid()
    for i in range(5):
        row = 4 - i
        pair = i // 2        # row pair index (0,0,1,1,2)
        offset = i % 2       # 0 for even rows, 1 for odd rows
        base = 24 + pair * 12 + offset  # C2 base, +octave per pair, +1 for odd
        for col in range(COLS):
            note = base + col * 2
            grid[row][col] = note_to_keycode(note)
    return grid


def preset_c_major():
    """C Major diatonic scale with overlapping octave rows.

    Each row spans 2 octaves of white notes (C major / A minor). Adjacent rows
    overlap by 1 octave for smooth transitions. Impossible to hit a wrong note.
    Great for beginners, composition sketches, or modal exploration.
    """
    major = [0, 2, 4, 5, 7, 9, 11]
    grid = _make_empty_grid()
    for i in range(5):
        row = 4 - i
        start_octave = i + 1
        notes = _generate_scale_notes(0, major, start_octave, start_octave + 1)
        for col in range(min(COLS, len(notes))):
            grid[row][col] = note_to_keycode(notes[col])
    return grid


def preset_fifths():
    """Chromatic rows separated by perfect fifths.

    Each row is a chromatic run of 14 semitones. Moving up one row jumps a
    perfect fifth (+7 semitones). The circle of fifths becomes a straight
    vertical line. Great for exploring key relationships and jazz voicings.
    """
    grid = _make_empty_grid()
    base = 12  # C1
    for i in range(5):
        row = 4 - i
        row_base = base + i * 7  # +7 (perfect fifth) per row up
        for col in range(COLS):
            grid[row][col] = note_to_keycode(row_base + col)
    return grid


def preset_major_thirds():
    """Chromatic rows separated by major thirds.

    Each row is a chromatic run. Moving up one row jumps a major third
    (+4 semitones). Three rows up equals one octave. Vertical lines form
    augmented triads. Diagonal patterns reveal major and minor chords.
    Excellent for exploring voice leading and harmonic relationships.
    """
    grid = _make_empty_grid()
    base = 12  # C1
    for i in range(5):
        row = 4 - i
        row_base = base + i * 4  # +4 (major third) per row up
        for col in range(COLS):
            grid[row][col] = note_to_keycode(row_base + col)
    return grid


# ── Preset Registry ────────────────────────────────────────────────────────────
# Each entry: (display_name, description, generator_function)

KEYMAP_PRESETS = [
    (
        "Chromatic",
        "Linear chromatic scale, left-to-right, bottom-to-top. Every semitone in order.",
        preset_chromatic,
    ),
    (
        "Octave Rows",
        "Each row is one chromatic octave (C to B). 5 octaves, C1 through B5.",
        preset_octave_rows,
    ),
    (
        "Guitar Standard",
        "Guitar fretboard layout with standard EADGB tuning. 14 frets per string.",
        preset_guitar_standard,
    ),
    (
        "Guitar All Fourths",
        "Guitar fretboard with all-fourths tuning (EADGC). Consistent intervals.",
        preset_guitar_fourths,
    ),
    (
        "Wicki-Hayden",
        "Isomorphic layout: whole tones horizontal, fourths vertical. Same shapes in all keys.",
        preset_wicki_hayden,
    ),
    (
        "Janko",
        "Janko keyboard: whole tones per row, rows offset by semitone. Uniform fingering.",
        preset_janko,
    ),
    (
        "C Major Scale",
        "Diatonic C major only (white notes). Overlapping 2-octave rows. No wrong notes.",
        preset_c_major,
    ),
    (
        "Fifths",
        "Chromatic rows separated by perfect fifths. Circle of fifths = vertical line.",
        preset_fifths,
    ),
    (
        "Major Thirds",
        "Chromatic rows separated by major thirds. 3 rows up = 1 octave. Reveals triads.",
        preset_major_thirds,
    ),
]
