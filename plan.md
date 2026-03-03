# Quick Build & OLED Refactor - Implementation Plan

## Summary of Changes
1. **Fix quick build playback bug** - builds currently play factory presets instead of custom patterns
2. **Add parameter setup phase** before note recording (encoder-driven UI on OLED)
3. **Hijack encoder 0** during quick build to control parameters/recording instead of normal keycodes
4. **Route arp/seq playback velocity through the main velocity curve**
5. **New OLED screens** for parameter selection and recording mode

---

## Bug Fix: Quick Build Plays Factory Presets Instead of Custom Patterns

### Root Cause (confirmed by code analysis)
When the user finishes a quick build and presses the button again to play:

**Arp path** (orthomidi5x14.c:13938):
- `arp_toggle()` → `arp_start(arp_state.current_preset_id)` where `current_preset_id` is still **0** (factory default)
- `arp_start(0)` → `arp_load_preset_into_slot(0)`
- `loaded_preset_id` is **255** (set by quick_build_start_arp), so `255 != 0` → load factory preset 0 → **overwrites the quick-built pattern in RAM**

**Seq path** (orthomidi5x14.c:13969):
- `seq_start(seq_state[slot].current_preset_id)` where `current_preset_id` is still **68** (factory default)
- Same overwrite problem, PLUS `seq_find_available_slot()` may return a different slot than the one built into

### Fix
**File: arpeggiator.c**
1. Add `PRESET_ID_QUICK_BUILD` sentinel (value 255)
2. In `arp_load_preset_into_slot()`: if `preset_id == 255`, return true immediately (RAM already has the data)
3. In `arp_start()`: allow `preset_id == 255` to bypass the `>= MAX_ARP_PRESETS` bounds check
4. In `quick_build_finish()`: set `arp_state.current_preset_id = 255` (arp) or `seq_state[slot].current_preset_id = 255` (seq)

**File: orthomidi5x14.c**
5. Seq play path: use the known quick build slot directly instead of calling `seq_start()` which uses `seq_find_available_slot()`. Instead, directly activate the specific slot:
   ```c
   // Instead of seq_start(seq_state[slot].current_preset_id):
   seq_start_slot(slot);  // New function that starts a specific slot without reloading
   ```
6. Add `seq_start_slot(uint8_t slot)` in arpeggiator.c that activates a specific slot without lazy-loading (for quick build playback)

---

## Phase 1: Quick Build State Machine Refactor

### New Quick Build States
Currently: `QUICK_BUILD_NONE` / `QUICK_BUILD_ARP` / `QUICK_BUILD_SEQ`

New states to add to `quick_build_mode_t` enum:
```
QUICK_BUILD_NONE          = 0   (idle)
QUICK_BUILD_ARP_SETUP     = 1   (arp parameter selection phase)
QUICK_BUILD_SEQ_SETUP     = 2   (seq parameter selection phase)
QUICK_BUILD_ARP_RECORD    = 3   (arp note recording phase)
QUICK_BUILD_SEQ_RECORD    = 4   (seq note recording phase)
```

### New Fields in `quick_build_state_t`
```c
uint8_t setup_param_index;       // Which parameter is being configured (0, 1, 2...)
uint8_t setup_arp_mode;          // Selected arp mode during setup
uint8_t setup_note_value;        // Selected speed (quarter/eighth/sixteenth)
uint8_t setup_timing_mode;       // Selected timing (straight/triplet/dotted)
uint8_t setup_gate_percent;      // Selected gate length
bool encoder_chord_held;         // Encoder click held = chord mode (momentary)
```

### Updated Flow

**Button press → Setup phase → Recording phase → Finish**

1. Press ARP_QUICK_BUILD / SEQ_QUICK_BUILD → enters `_SETUP` state
2. OLED shows first parameter (arp mode or speed)
3. Encoder 0 rotation cycles through options
4. Encoder 0 click OR quick build button press confirms and advances to next parameter
5. After all parameters confirmed → enters `_RECORD` state
6. Note recording works as before, but encoder 0 is now: rotate CW = skip step, rotate CCW = undo step, click = momentary chord mode
7. Quick build button press → finish

### Parameter Screens

**Arp setup has 3 parameters (shown in order):**

| # | Parameter | Small text (top) | Big text (middle) | Options (encoder cycles) |
|---|-----------|-----------------|-------------------|--------------------------|
| 1 | Arp Mode | "How arp responds to" / "multiple midi notes" | Mode name | Single Synced, Single Unsynced, Chord Synced, Chord Unsynced, Chord Advanced |
| 2 | Speed | "Pattern rate" | Rate name | Quarter, Eighth, Sixteenth (× Straight/Triplet/Dotted = 9 combos) |
| 3 | Gate Length | "Note sustain length" | Percentage | 10%, 20%, 30%, ... 100% |

**Seq setup has 2 parameters (shown in order):**

| # | Parameter | Small text (top) | Big text (middle) | Options (encoder cycles) |
|---|-----------|-----------------|-------------------|--------------------------|
| 1 | Speed | "Pattern rate" | Rate name | Quarter, Eighth, Sixteenth (× Straight/Triplet/Dotted = 9 combos) |
| 2 | Gate Length | "Note sustain length" | Percentage | 10%, 20%, 30%, ... 100% |

---

## Phase 2: Encoder 0 Hijacking

### Where to Intercept

**File: orthomidi5x14.c, in `process_record_user()` (line 13556)**

Add an early intercept at the top of `process_record_user()` (after the EEPROM/velocity debug mode checks, before normal keycode processing):

```c
// Quick build encoder hijack - encoder 0 only
if (quick_build_is_setup_or_recording()) {
    // Check if this is encoder 0 rotation
    if ((record->event.key.row == KEYLOC_ENCODER_CW ||
         record->event.key.row == KEYLOC_ENCODER_CCW) &&
        record->event.key.col == 0) {  // Encoder 0 only

        if (record->event.pressed) {
            bool clockwise = (record->event.key.row == KEYLOC_ENCODER_CW);
            quick_build_handle_encoder(clockwise);
        }
        return false;  // Consume the event, don't process normally
    }

    // Check if this is encoder 0 click (row 5, col 0)
    if (record->event.key.row == 5 && record->event.key.col == 0) {
        if (record->event.pressed) {
            quick_build_handle_encoder_click(true);
        } else {
            quick_build_handle_encoder_click(false);
        }
        return false;  // Consume
    }
}
```

Also intercept in `set_keylog()` (line 8851) to prevent encoder 0 from triggering CC/transpose/velocity/channel changes during quick build. Add early return before the CC encoder check:

```c
if (quick_build_is_setup_or_recording() &&
    (record->event.key.row == KEYLOC_ENCODER_CW || record->event.key.row == KEYLOC_ENCODER_CCW) &&
    record->event.key.col == 0) {
    return;  // Don't process encoder 0 in set_keylog during quick build
}
```

### Encoder Behavior by Phase

**Setup phase** (`_ARP_SETUP` / `_SEQ_SETUP`):
- Encoder 0 CW: next option value
- Encoder 0 CCW: previous option value
- Encoder 0 click: confirm current parameter, advance to next (or enter recording if last)
- Quick build button: same as encoder click (confirm)

**Recording phase** (`_ARP_RECORD` / `_SEQ_RECORD`):
- Encoder 0 CW: skip step (advance without recording a note)
- Encoder 0 CCW: undo last step (remove last note(s), go back one step)
- Encoder 0 click (held): momentary chord mode - notes pile on same step while held
- Quick build button: finish build

---

## Phase 3: OLED Display Changes

### File: orthomidi5x14.c

**Modify `oled_task_user()` (line 16597)**

Update the quick build check to differentiate setup vs recording:

```c
if (quick_build_is_setup_or_recording()) {
    if (quick_build_is_setup()) {
        render_quick_build_setup();
    } else {
        render_quick_build_recording();
    }
    return false;
}
```

### New function: `render_quick_build_setup()`

OLED layout (128x128 = 21 chars × 16 rows):
```
Row 0:  "  ARP QUICK BUILD  " or "SEQ SLOT N BUILD"
Row 1:  "---------------------"
Row 2:  (blank)
Row 3:  small text: description line 1
Row 4:  small text: description line 2
Row 5:  (blank)
Row 6:  "  >> VALUE NAME << "   ← big centered text with selection arrows
Row 7:  (blank)
Row 8:  "  Turn to select    "
Row 9:  "  Press to confirm  "
Row 10: (blank)
Row 11: " Param 1/3          "   ← progress indicator
```

Note: The 128x128 OLED uses standard 6x8 font (no actual "big font" hardware support). We use centering and `>>` `<<` arrows to emphasize the selected value. The current `render_big_number()` also uses standard font - it just centers text on the screen.

### New function: `render_quick_build_recording()`

OLED layout during recording:
```
Row 0:  "  ARP QUICK BUILD  " or "SEQ SLOT N BUILD"
Row 1:  "---------------------"
Row 2:  (blank)
Row 3:  "      STEP NN       "
Row 4:  "   NN NOTES TOTAL   "
Row 5:  (blank)
Row 6:  " ENC: << Undo  Skip >>"
Row 7:  " ENC CLICK: Chord   "
Row 8:  (blank)
Row 9:  " Press btn to finish"
```

This replaces the current `render_big_number()` during recording to also show encoder controls.

---

## Phase 4: Velocity Curve for Arp/Seq Playback

### Current Behavior
- **Arp**: Raw preset velocity (0-127) → direct to MIDI out via `midi_send_noteon_arp()`
- **Seq**: Raw preset velocity → linear vel_min/vel_max scaling → `midi_send_noteon_arp()`
- **Normal notes**: raw_velocity (0-255) → `apply_curve()` → vel_min/vel_max mapping → MIDI out

### New Behavior
Route arp/seq velocities through the same pipeline as normal notes:
1. Take preset velocity (0-127)
2. Scale to 0-255 range: `travel_equiv = velocity * 2` (to match the 0-255 input `apply_curve` expects)
3. Apply `apply_curve(travel_equiv, curve_index)` → 0-255
4. Map through vel_min/vel_max: `final = min + (curved * (max - min)) / 255`
5. Clamp to 1-127

### Implementation

**File: arpeggiator.c**

Create a new helper function:
```c
// Apply velocity curve + min/max to arp/seq preset velocity
static uint8_t apply_velocity_pipeline(uint8_t preset_velocity_0_127) {
    // Scale 0-127 to 0-255 (matching normal note travel range)
    uint16_t travel_equiv = (uint16_t)preset_velocity_0_127 * 2;
    if (travel_equiv > 255) travel_equiv = 255;

    // Get current velocity curve (use base zone curve for arp/seq)
    extern uint8_t he_velocity_curve;
    extern uint8_t he_velocity_min;
    extern uint8_t he_velocity_max;

    // Apply curve (0-255 → 0-255)
    uint8_t curved = apply_curve((uint8_t)travel_equiv, he_velocity_curve);

    // Map to velocity range
    uint8_t range = he_velocity_max - he_velocity_min;
    int16_t velocity = he_velocity_min + ((int16_t)curved * range) / 255;

    // Clamp
    if (velocity < 1) velocity = 1;
    if (velocity > 127) velocity = 127;

    return (uint8_t)velocity;
}
```

**Modify all arp send sites** (lines ~771, ~860, ~904, ~938, ~977):
Change from:
```c
uint8_t raw_travel = note->velocity;
midi_send_noteon_arp(channel, final_note, raw_travel, raw_travel);
```
To:
```c
uint8_t processed_vel = apply_velocity_pipeline(note->velocity);
midi_send_noteon_arp(channel, final_note, processed_vel, processed_vel);
```

**Modify `midi_send_noteon_seq()`** (line ~1182):
Remove the old locked-in vel_min/vel_max scaling and replace with the pipeline:
```c
void midi_send_noteon_seq(uint8_t slot, uint8_t note, uint8_t velocity_0_127) {
    // ... channel and transpose as before ...

    // Apply velocity curve + min/max (replaces old linear scaling)
    uint8_t final_velocity = apply_velocity_pipeline(velocity_0_127);

    midi_send_noteon_arp(channel, transposed_note, final_velocity, final_velocity);
}
```

Remove the now-unused `locked_velocity_min` / `locked_velocity_max` fields from `seq_state_t`, and remove them from `seq_start()`.

---

## Phase 5: Undo/Skip Step Encoder Functions

### File: arpeggiator.c

**New function: `quick_build_skip_step()`**
```c
void quick_build_skip_step(void) {
    // Advance to next step without recording a note (empty step)
    quick_build_advance_step();
}
```

**New function: `quick_build_undo_step()`**
```c
void quick_build_undo_step(void) {
    if (quick_build_state.current_step == 0 && quick_build_state.note_count == 0) return;

    // Remove all notes on the current step (and previous step if current is empty)
    uint8_t target_step = quick_build_state.current_step;

    // If current step has no notes yet, undo the previous step
    bool current_has_notes = false;
    // Count notes on current step
    // ... (scan backward through notes to find ones matching current_step)

    // Remove notes and decrement counters
    // Decrement current_step
    // Update pattern_length_16ths
}
```

### Chord Mode (Encoder Click)

The encoder 0 click at matrix position (5, 0) will be intercepted during recording mode. While held (`encoder_chord_held = true`), notes are grouped onto the same step. On release, the step advances (same behavior as sustain pedal release).

In `quick_build_handle_note()`, check `quick_build_state.encoder_chord_held` alongside the existing `sustain_held` check:
```c
bool chord_mode = sustain_held || quick_build_state.encoder_chord_held;
if (!chord_mode) {
    should_advance = true;
}
```

---

## File Change Summary

| File | Changes |
|------|---------|
| `orthomidi5x14.h` | Add new quick build states to enum, new fields to `quick_build_state_t`, add `PRESET_ID_QUICK_BUILD` define, function declarations |
| `arpeggiator.c` | Fix playback bug, add setup phase logic, add encoder handlers, add `apply_velocity_pipeline()`, add undo/skip, add `seq_start_slot()` |
| `orthomidi5x14.c` | Encoder 0 intercept in `process_record_user()` and `set_keylog()`, new OLED render functions, update quick build button handlers for new state machine |

---

## Implementation Order

1. **Bug fix first** - Fix the quick build playback overwrite (small, critical)
2. **State machine expansion** - Add new states and fields to structs/enums
3. **OLED rendering** - Add `render_quick_build_setup()` and `render_quick_build_recording()`
4. **Encoder hijacking** - Intercept encoder 0 in process_record_user and set_keylog
5. **Setup phase logic** - Parameter cycling and confirmation flow
6. **Recording phase encoder** - Skip/undo/chord mode
7. **Velocity pipeline** - Route arp/seq through apply_curve + vel_min/vel_max

---

## Questions / Decisions Needed

1. **Speed parameter display**: Should the 9 speed combinations (3 note values × 3 timing modes) be shown as a flat list like "16th", "16th Triplet", "16th Dotted", "8th", "8th Triplet", etc? Or as two separate parameters (note value + timing mode)?

2. **Gate length granularity**: Steps of 10% (10 options: 10%-100%) or finer like 5% (20 options)?

3. **Default values in setup**: Should parameters start at the current/previous values, or always at sensible defaults (e.g., Single Note Synced, Sixteenth, 80% gate)?

4. **Undo behavior detail**: When undoing, should it undo the entire last step (removing all notes on that step), or note-by-note?

5. **Seq locked_velocity_min/max removal**: The sequencer currently locks in vel_min/vel_max at start time so changing global settings doesn't affect running sequences. With the new pipeline calling apply_curve() live, running sequences will respond to live velocity curve/range changes. Is that the desired behavior? (It makes it consistent with how arp will work.)
