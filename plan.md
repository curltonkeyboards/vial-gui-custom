# Implementation Plan: Quick Build Refactor + OLED Display Changes

## Summary of Changes

Refactor Quick Build for arp/seq to add a **parameter setup phase** (using encoder 0 to scroll options, button to confirm), change **note recording controls** (encoder 0: undo/skip/chord), apply **velocity curves** to arp/seq playback, and update **OLED rendering** for each phase.

---

## Phase 1: Extend Quick Build State Machine

**Files:** `orthomidi5x14.h`, `arpeggiator.c`

### 1.1 Add new state fields to `quick_build_state_t` (orthomidi5x14.h ~line 861)

```c
typedef enum {
    QB_PHASE_PARAMS,     // Setting up parameters (mode/speed/gate)
    QB_PHASE_RECORDING,  // Recording notes
} quick_build_phase_t;

typedef enum {
    QB_PARAM_ARP_MODE,   // Arp only: which arp mode (5 options)
    QB_PARAM_SPEED,      // Note value (quarter/eighth/sixteenth × straight/triplet/dotted = 9 combos)
    QB_PARAM_GATE,       // Gate length percent (10%, 20%, ... 100% = 10 steps)
    QB_PARAM_COUNT_ARP,  // Sentinel for arp (3 params)
    QB_PARAM_SPEED_SEQ = 0, // Seq starts at speed (no mode param)
    QB_PARAM_GATE_SEQ,
    QB_PARAM_COUNT_SEQ,  // Sentinel for seq (2 params)
} quick_build_param_t;
```

Add fields to `quick_build_state_t`:
```c
quick_build_phase_t phase;           // Current phase (params or recording)
uint8_t current_param;               // Which parameter is being configured
uint8_t param_selection;             // Current encoder position within parameter options
bool encoder_chord_held;             // Encoder click held = momentary chord grouping
```

### 1.2 Update `quick_build_start_arp()` / `quick_build_start_seq()` (arpeggiator.c)

- Set `phase = QB_PHASE_PARAMS`
- Set `current_param = 0` (first parameter)
- Set `param_selection` to sensible defaults (e.g., current arp mode, 16th note straight, 80% gate)
- Still clear the preset and initialize defaults

### 1.3 Add parameter option arrays (arpeggiator.c)

Define arrays for each parameter's options:

**Arp Mode options (5):** Single Synced, Single Unsynced, Chord Synced, Chord Unsynced, Chord Advanced
**Speed options (9):** Quarter, Quarter Dot, Quarter Trip, Eighth, Eighth Dot, Eighth Trip, 16th, 16th Dot, 16th Trip
**Gate options (10):** 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90%, 100%

### 1.4 Add new functions (arpeggiator.c, declared in orthomidi5x14.h)

```c
void quick_build_encoder_rotate(bool clockwise);  // Handle encoder 0 rotation
void quick_build_encoder_click(bool pressed);      // Handle encoder 0 click press/release
void quick_build_confirm_param(void);              // Confirm current param, advance to next or start recording
uint8_t quick_build_get_param_option_count(void);  // How many options for current param
const char* quick_build_get_param_label(void);     // Small text label for current param
const char* quick_build_get_param_value(void);     // Big text value for current param
```

---

## Phase 2: Encoder 0 Hijacking During Quick Build

**File:** `orthomidi5x14.c`

### 2.1 Intercept encoder 0 rotation in `process_record_user()` (~line 8837)

Add an early return check at the **top** of the encoder handling section (before the ccencoder/transpose/velocity/channel handlers):

```c
// Hijack encoder 0 during quick build
if ((record->event.key.row == KEYLOC_ENCODER_CW || record->event.key.row == KEYLOC_ENCODER_CCW)
    && record->event.key.col == 0  // Encoder 0 only
    && quick_build_is_active()) {
    if (record->event.pressed) {
        bool clockwise = (record->event.key.row == KEYLOC_ENCODER_CW);
        quick_build_encoder_rotate(clockwise);
    }
    return false;  // Swallow the event
}
```

### 2.2 Intercept encoder 0 click in `matrix_scan_user()` (~line 16678)

Modify the encoder 0 click handling block. When quick build is active:
- Press → `quick_build_encoder_click(true)`
- Release → `quick_build_encoder_click(false)`
- Skip the normal `action_exec(MAKE_KEYEVENT(5, 0, ...))` so it doesn't fire normal keycodes

### 2.3 Also intercept the quick build button press as "confirm"

In the ARP_QUICK_BUILD / SEQ_QUICK_BUILD handler (~line 13917), when `phase == QB_PHASE_PARAMS`:
- Button press → `quick_build_confirm_param()` (same as encoder click confirm)
- Don't finish/toggle - that only happens in recording phase

---

## Phase 3: Parameter Setup Phase Logic

**File:** `arpeggiator.c`

### 3.1 `quick_build_encoder_rotate()` - Phase-dependent behavior

**During QB_PHASE_PARAMS:**
- Scroll `param_selection` through available options for `current_param`
- Wrap around at boundaries
- The OLED will update automatically on next render cycle

**During QB_PHASE_RECORDING:**
- CW (clockwise / up) → **skip step** (advance to next step without recording a note)
- CCW (counter-clockwise / down) → **undo step** (remove last recorded note, decrement step if that was the only note on the step)

### 3.2 `quick_build_encoder_click()` - Phase-dependent behavior

**During QB_PHASE_PARAMS:**
- On press: `quick_build_confirm_param()` - apply current selection, move to next param or enter recording

**During QB_PHASE_RECORDING:**
- On press: Set `encoder_chord_held = true` (momentary chord mode - notes pile on same step)
- On release: Set `encoder_chord_held = false`, advance step (like sustain release)

### 3.3 `quick_build_confirm_param()`

1. Apply the current `param_selection` to the preset being built:
   - ARP_MODE: Set `arp_state.mode` to the selected mode
   - SPEED: Set `note_value` and `timing_mode` on the preset
   - GATE: Set `gate_length_percent` on the preset
2. Increment `current_param`
3. If all params configured → transition to `QB_PHASE_RECORDING`
4. Reset `param_selection` to default for next param

### 3.4 Modify `quick_build_handle_note()` - chord grouping via encoder

Currently checks `get_live_sustain_state()` for chord grouping. Add:
```c
bool chord_mode = sustain_held || quick_build_state.encoder_chord_held;
```
So either sustain pedal OR encoder click will group notes.

### 3.5 Add undo/skip functions

```c
static void quick_build_undo_step(void) {
    // Remove the last recorded note
    // If that was the only note at current_step, also decrement current_step
    // Decrement note_count
    // Update pattern_length_16ths
}

static void quick_build_skip_step(void) {
    // Advance step without recording (leaves an empty step - or just advances pointer)
    quick_build_advance_step();
}
```

### 3.6 Modify button handlers for phase awareness

In `orthomidi5x14.c` keycode handlers for ARP_QUICK_BUILD and SEQ_QUICK_BUILD:
- If `phase == QB_PHASE_PARAMS` and pressed → `quick_build_confirm_param()`
- If `phase == QB_PHASE_RECORDING` and pressed → `quick_build_finish()` (existing behavior)
- Release 3-second hold logic stays the same

---

## Phase 4: Velocity Curve Application for Arp/Seq Playback

**Files:** `arpeggiator.c`, `orthomidi5x14.c`, `process_midi.c`

### 4.1 Create `apply_arp_velocity_curve()` helper (orthomidi5x14.c)

New function that takes a stored 0-127 velocity from a preset note and runs it through the current velocity curve + min/max:

```c
uint8_t apply_arp_velocity_curve(uint8_t stored_velocity_0_127) {
    // Scale 0-127 to 0-255 range (the curve input domain)
    uint8_t raw_value = (uint16_t)stored_velocity_0_127 * 255 / 127;

    // Apply current velocity curve
    uint8_t curve_index = keyboard_settings.he_velocity_curve;
    uint8_t curved_value = apply_curve(raw_value, curve_index);

    // Map through min/max
    uint8_t min_vel = keyboard_settings.he_velocity_min;
    uint8_t max_vel = keyboard_settings.he_velocity_max;
    uint8_t range = max_vel - min_vel;
    int16_t velocity = min_vel + ((int16_t)curved_value * range) / 255;

    if (velocity < 1) velocity = 1;
    if (velocity > 127) velocity = 127;
    return (uint8_t)velocity;
}
```

### 4.2 Modify arp playback to use velocity curve (arpeggiator.c)

In all places where arp notes are sent (there are ~6 call sites in arp_update):
- **Before:** `uint8_t raw_travel = unpacked.velocity;` then `midi_send_noteon_arp(ch, note, raw_travel, raw_travel);`
- **After:** `uint8_t final_vel = apply_arp_velocity_curve(unpacked.velocity);` then `midi_send_noteon_arp(ch, note, final_vel, final_vel);`

### 4.3 Modify seq playback to use velocity curve (arpeggiator.c)

In `midi_send_noteon_seq()` (~line 1182):
- **Remove** the old `locked_velocity_min/max` scaling
- **Replace** with `apply_arp_velocity_curve(velocity_0_127)`
- This replaces the deprecated per-seq-slot velocity system

### 4.4 Remove deprecated arp/seq velocity system

- Remove `locked_velocity_min` / `locked_velocity_max` from `seq_state_t` (orthomidi5x14.h)
- Remove the locked velocity initialization in seq_start
- The seq velocity is now determined by recorded velocity + global velocity curve, not per-slot min/max

---

## Phase 5: OLED Display Updates

**File:** `orthomidi5x14.c`

### 5.1 Refactor `render_big_number()` → `render_quick_build()`

Replace the single function with a phase-aware renderer:

**During QB_PHASE_PARAMS:**
```
Line 0: small font - parameter description (e.g., "how the arp responds")
Line 1: separator "---------------------"
Line 3: BIG centered - current option value (e.g., "SINGLE SYNC")
Line 5: small font - "turn to change"
Line 7: small font - "press to confirm"
```

**During QB_PHASE_RECORDING:**
```
Line 0: "ARP QUICK BUILD" / "SEQ SLOT N BUILD"
Line 1: separator "---------------------"
Line 3: "STEP X" (large, centered)
Line 5: "Y NOTES TOTAL"
Line 7: "enc: undo/skip/chord"
```

### 5.2 Update `oled_task_user()` (~line 16583)

Change `render_big_number(quick_build_get_current_step())` → `render_quick_build()`

### 5.3 Parameter display strings

Define compact display strings for each option:

**Arp modes:** "SINGLE SYNC", "SINGLE UNSYNC", "CHORD SYNC", "CHORD UNSYNC", "CHORD ADV"
**Speeds:** "QUARTER", "QUARTER DOT", "QUARTER TRIP", "EIGHTH", "EIGHTH DOT", "EIGHTH TRIP", "16TH", "16TH DOT", "16TH TRIP"
**Gates:** "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"

**Small font labels:**
- Arp mode: "how arp handles notes"
- Speed: "pattern rate"
- Gate: "note sustain length"

---

## Phase 6: Integration & Edge Cases

### 6.1 Ensure encoder 0 click works as confirm in params phase

The encoder 0 click fires as matrix position (5, 0) via `action_exec(MAKE_KEYEVENT(5, 0, ...))` in `matrix_scan_user()`. During QB_PHASE_PARAMS, we intercept this to call `quick_build_confirm_param()`. During QB_PHASE_RECORDING, it acts as momentary chord mode.

### 6.2 Quick build cancel resets phase

`quick_build_cancel()` should also reset `phase`, `current_param`, `encoder_chord_held`.

### 6.3 The 3-second hold erase should still work

The 3-second hold detection happens on the quick build button release. This must still work in both phases. During params phase, a 3-second hold cancels/exits quick build entirely.

### 6.4 Sustain pedal still works for chord grouping during recording

Keep existing sustain pedal chord grouping alongside the new encoder chord mode. Both can coexist.

---

## File Change Summary

| File | Changes |
|------|---------|
| `orthomidi5x14.h` | Add phase/param enums, extend `quick_build_state_t`, add new function declarations, remove `locked_velocity_min/max` from `seq_state_t` |
| `arpeggiator.c` | Add parameter setup logic, encoder handlers, undo/skip, modify quick_build_start_*, modify note recording for encoder chord mode, modify arp/seq playback velocity |
| `orthomidi5x14.c` | Add encoder 0 hijack in `process_record_user`, modify encoder 0 click in `matrix_scan_user`, modify quick build button handlers for phase awareness, add `apply_arp_velocity_curve()`, refactor OLED rendering |
| `process_midi.c` | No changes needed (midi_send_noteon_arp stays as-is, velocity changes happen upstream) |

---

## Implementation Order

1. **Phase 1** - State machine extensions (header + struct changes)
2. **Phase 5** - OLED rendering (so we can see what's happening)
3. **Phase 2** - Encoder hijacking (intercept in process_record_user + matrix_scan_user)
4. **Phase 3** - Parameter setup phase logic
5. **Phase 4** - Velocity curve changes
6. **Phase 6** - Integration, edge cases, testing

---

## Questions Resolved

- **Encoder 0 only** is hijacked (col == 0)
- **Either button confirms** during parameter setup (encoder click or quick build button)
- **Momentary chord mode** on encoder click during recording
- **Velocity curve**: stored 0-127 → scale to 0-255 → apply_curve() → map through min/max → final 1-127 MIDI velocity
- **Sustain pedal** chord grouping still works alongside encoder chord mode
