# Velocity & Aftertouch Calculation Analysis (Updated)

## Executive Summary

This document analyzes the velocity and aftertouch calculation methods implemented in the orthomidi5x14 Hall effect keyboard firmware. The system has **two parallel velocity calculation paths** that operate independently:

1. **matrix.c velocity modes**: Calculate velocity from peak travel, speed, or combined (stored in array)
2. **orthomidi5x14.c HE velocity**: Read current travel at note-on time, apply curves

**Key Finding:** The main MIDI path uses the HE velocity path (with curves), NOT the matrix.c velocity modes. The velocity modes in matrix.c are largely unused in practice.

---

## Complete Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           COMPLETE SYSTEM ARCHITECTURE                            │
└──────────────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────────────┐
                            │     Raw ADC         │
                            │  (Hall Effect)      │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │    EMA Filter       │
                            │   key->adc_filtered │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │  LUT Linearization  │
                            │  distance_lut.h     │
                            │  (0-255 output)     │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │   key->distance     │
                            │     (0-255)         │
                            └──────────┬──────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │   PATH 1:        │    │   PATH 2:        │    │   AFTERTOUCH     │
   │   matrix.c       │    │   orthomidi5x14  │    │   matrix.c       │
   │   velocity modes │    │   HE velocity    │    │   modes 1-4      │
   └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
            │                       │                       │
            ▼                       ▼                       ▼
   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │ Velocity Modes:  │    │ CURRENT travel   │    │ AT Modes:        │
   │ 0: Fixed (64)    │    │ at note-on time  │    │ 1: Reverse       │
   │ 1: Peak Travel   │    │      │           │    │ 2: Bottom-out    │
   │ 2: Speed-based   │    │      ▼           │    │ 3: Post-actuat.  │
   │ 3: Combined      │    │ apply_curve()    │    │ 4: Vibrato       │
   └────────┬─────────┘    │      │           │    └────────┬─────────┘
            │              │      ▼           │             │
            │              │ Scale to         │             │
            ▼              │ [min, max]       │             ▼
   ┌──────────────────┐    └────────┬─────────┘    ┌──────────────────┐
   │ store_midi_      │             │              │ midi_send_cc()   │
   │ velocity()       │             │              │ aftertouch_cc    │
   │      │           │             │              └──────────────────┘
   │      ▼           │             │
   │ optimized_midi_  │             │
   │ velocities[]     │             │
   └────────┬─────────┘             │
            │                       │
            ▼                       ▼
   ┌──────────────────┐    ┌──────────────────┐
   │ get_midi_        │    │ get_he_velocity_ │
   │ velocity()       │    │ from_position()  │
   │ (RARELY USED)    │    │ (MAIN PATH)      │
   └────────┬─────────┘    └────────┬─────────┘
            │                       │
            └───────────┬───────────┘
                        │
                        ▼
            ┌──────────────────────┐
            │   process_midi.c    │
            │                      │
            │ if (analog_mode > 0) │───► apply_he_velocity_from_record() ───► CURVES APPLIED ✓
            │ else                 │───► apply_velocity_mode()           ───► NO CURVES ✗
            └──────────────────────┘
                        │
                        ▼
            ┌──────────────────────┐
            │  midi_send_noteon()  │
            │  Final velocity sent │
            └──────────────────────┘
```

---

## Critical Finding: Two Parallel Paths

### Path 1: matrix.c Velocity Modes (STORED BUT RARELY USED)

**Location:** `matrix.c` lines 500-688

This path calculates velocity using sophisticated algorithms but stores the result for later retrieval:

```c
// Calculation in matrix.c
switch (analog_mode) {
    case 0: key->base_velocity = 64; break;                    // Fixed
    case 2: key->base_velocity = calculate_speed_velocity(...); break;  // Speed
    // etc.
}
store_midi_velocity(state->note_index, key->base_velocity);  // STORED HERE
```

**When is this used?**
- Only via `apply_velocity_mode()` which calls `get_midi_velocity()`
- Only when `analog_mode == 0` (fixed mode)
- Or as a fallback when HE velocity returns 0

### Path 2: orthomidi5x14.c HE Velocity (MAIN PATH - CURVES APPLIED)

**Location:** `orthomidi5x14.c` lines 448-528

This is the path actually used for MIDI note-on when `analog_mode > 0`:

```c
uint8_t get_he_velocity_from_position(uint8_t row, uint8_t col) {
    // 1. Get CURRENT travel value (not peak, not speed-based!)
    uint8_t travel = analog_matrix_get_travel_normalized(row, col);

    // 2. Get curve index (per-key or global)
    uint8_t curve_index = get_key_velocity_curve(current_layer, row, col, 0);

    // 3. CURVES ARE APPLIED HERE
    uint8_t curved_travel = apply_curve(travel, curve_index);

    // 4. Scale to velocity range
    uint8_t velocity = min_vel + ((curved_travel * range) / 255);

    return velocity;
}
```

### The Disconnect

| Aspect | Path 1 (matrix.c) | Path 2 (orthomidi5x14.c) |
|--------|-------------------|--------------------------|
| **Input** | Peak travel, speed, or combined | Current travel at note-on |
| **Curves applied?** | NO | YES |
| **Used in practice?** | Rarely (fallback only) | YES (main MIDI path) |
| **Measurement** | Sophisticated (peak, speed, apex detection) | Simple (instantaneous travel) |

---

## Detailed Velocity Mode Flowcharts

### Mode 0: Fixed Velocity

```
┌─────────────────────────────────────────────────────────────┐
│                    MODE 0: FIXED VELOCITY                    │
└─────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  Key is pressed │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ velocity = 64   │
                    │ (constant)      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ store_midi_     │
                    │ velocity(64)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────────────────────────┐
                    │ process_midi.c: analog_mode == 0   │
                    │ → apply_velocity_mode() called     │
                    │ → get_midi_velocity() returns 64   │
                    │ → FINAL VELOCITY = 64              │
                    └─────────────────────────────────────┘

WHAT IS MEASURED: Nothing (constant output)
CURVES APPLIED: NO
RESULT: Always 64 regardless of how key is pressed
```

---

### Mode 1: Peak Travel at Apex

```
┌─────────────────────────────────────────────────────────────┐
│                MODE 1: PEAK TRAVEL AT APEX                   │
└─────────────────────────────────────────────────────────────┘

Time ──────────────────────────────────────────────────────────►

                    WHAT matrix.c CALCULATES:
                    ─────────────────────────

     Key Rest ────────────────────────────────────────────────
         ↓
         │    Speed exceeds threshold (20 units/ms)
         │    ┌─ speed_threshold_met = true
         │    ▼
Travel   │    ●─────────────────●   ← Peak travel tracked
(0-240)  │   ╱                   ╲
         │  ╱                     ╲     Speed drops below threshold
         │ ╱                       ╲    ┌─ Velocity calculated HERE
         │╱                         ╲   ▼
         ●───────────────────────────●────────────────────────
                                      │
                                      ▼
                            ┌─────────────────────┐
                            │ velocity =          │
                            │ peak_travel × 127   │
                            │ ─────────────────   │
                            │        240          │
                            └────────┬────────────┘
                                     │
                                     ▼
                            ┌─────────────────────┐
                            │ store_midi_velocity │
                            │ (STORED, rarely     │
                            │  retrieved)         │
                            └─────────────────────┘

                    WHAT ACTUALLY HAPPENS (Main Path):
                    ────────────────────────────────

     Key Rest ────────────────────────────────────────────────
         ↓
         │    Actuation point crossed
         │    ┌─ NOTE-ON triggered
         │    ▼
Travel   │    ●   ← CURRENT travel read at this instant
(0-255)  │   ╱ ╲
         │  ╱   ╲
         │ ╱     ╲
         │╱       ╲
         ●─────────●──────────────────────────────────────────

                  │
                  ▼
         ┌──────────────────────────┐
         │ travel = analog_matrix_  │
         │ get_travel_normalized()  │  ← Instantaneous value!
         └────────────┬─────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │ curved = apply_curve(    │
         │   travel, curve_index)   │  ← CURVE APPLIED ✓
         └────────────┬─────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │ velocity = min +         │
         │ (curved × range) / 255   │
         └──────────────────────────┘

WHAT IS MEASURED:
  - matrix.c: Peak travel reached during keystroke (sophisticated)
  - orthomidi5x14.c: Current travel at actuation moment (simple)

CURVES APPLIED:
  - matrix.c path: NO
  - orthomidi5x14.c path: YES ✓

ACTUAL BEHAVIOR: Velocity depends on travel depth at actuation point,
NOT the peak travel depth. This may result in lower velocity for fast
strikes that cross actuation before reaching peak travel.
```

---

### Mode 2: Speed-Based Velocity

```
┌─────────────────────────────────────────────────────────────┐
│                 MODE 2: SPEED-BASED VELOCITY                 │
└─────────────────────────────────────────────────────────────┘

Time ──────────────────────────────────────────────────────────►

                    WHAT matrix.c CALCULATES:
                    ─────────────────────────

     Key Rest ────────────────────────────────────────────────
         ↓
         │         Δt (time_delta)
         │    ◄─────────────────────►
Travel   │
(0-240)  │    ●─────────────────────●
         │   ╱ │
         │  ╱  │ Δtravel
         │ ╱   │ (travel_delta)
         │╱    ▼
         ●─────────────────────────────────────────────────────

              │
              ▼
    ┌───────────────────────────────────────────────┐
    │  speed = (travel_delta × 1000) / time_delta   │
    │                                               │
    │  velocity = (speed × velocity_speed_scale)    │
    │             ─────────────────────────────     │
    │                       100                     │
    │                                               │
    │  (velocity_speed_scale: 1-20, configurable)   │
    └───────────────────────────────────────────────┘
              │
              ▼
    ┌───────────────────────────────────────────────┐
    │  store_midi_velocity() → STORED, RARELY USED  │
    └───────────────────────────────────────────────┘


                    WHAT ACTUALLY HAPPENS:
                    ─────────────────────

    Same as Mode 1: Current travel at actuation → apply_curve() → velocity

WHAT IS MEASURED:
  - matrix.c: Keystroke speed (travel distance / time)
  - orthomidi5x14.c: Current travel depth (ignores speed entirely!)

CURVES APPLIED:
  - matrix.c path: NO
  - orthomidi5x14.c path: YES ✓

ISSUE: Speed-based velocity is calculated but NOT USED in main path!
The actual velocity depends only on travel depth at actuation.
```

---

### Mode 3: Speed + Peak Combined (70/30)

```
┌─────────────────────────────────────────────────────────────┐
│            MODE 3: SPEED + PEAK COMBINED (70/30)             │
└─────────────────────────────────────────────────────────────┘

                    WHAT matrix.c CALCULATES:
                    ─────────────────────────

     Key Rest ────────────────────────────────────────────────
         ↓
         │
Travel   │    ●──────●   ← Peak travel
(0-240)  │   ╱ ╲      ╲
         │  ╱   ╲      ╲
         │ ╱     ╲      ╲
         │╱       ╲      ╲
         ●─────────●──────●────────────────────────────────────

         │
         ▼
    ┌───────────────────────────────────────────────┐
    │  Peak speed tracked during descent            │
    │  Peak travel tracked during descent           │
    │                                               │
    │  travel_vel = (peak_travel × 127) / 240       │
    │  speed_vel = calculate_speed_velocity(...)    │
    │                                               │
    │  final = (speed_vel × 70) + (travel_vel × 30) │
    │          ─────────────────────────────────────│
    │                       100                     │
    └───────────────────────────────────────────────┘
              │
              ▼
    ┌───────────────────────────────────────────────┐
    │  store_midi_velocity() → STORED, RARELY USED  │
    └───────────────────────────────────────────────┘


                    WHAT ACTUALLY HAPPENS:
                    ─────────────────────

    Same as Modes 1 & 2: Current travel at actuation → apply_curve() → velocity

WHAT IS MEASURED:
  - matrix.c: 70% keystroke speed + 30% peak travel depth
  - orthomidi5x14.c: Current travel depth only (ignores speed & peak!)

CURVES APPLIED:
  - matrix.c path: NO
  - orthomidi5x14.c path: YES ✓

ISSUE: The sophisticated 70/30 blending is calculated but NOT USED!
```

---

## Aftertouch Mode Flowcharts

### Aftertouch Mode 1: Reverse (Pedal-Controlled)

```
┌─────────────────────────────────────────────────────────────┐
│              AFTERTOUCH MODE 1: REVERSE                      │
└─────────────────────────────────────────────────────────────┘

PREREQUISITE: aftertouch_pedal_active == true

Travel ───────────────────────────────────────────────────────►
(0-240)

      0        60       120       180       240
      │         │         │         │         │
      ▼         ▼         ▼         ▼         ▼
      ┌─────────────────────────────────────────┐
      │                                         │
AT    │ 127 ●                                   │
Value │      ╲                                  │
      │       ╲                                 │
      │        ╲                                │
      │         ╲                               │
      │          ╲                              │
      │           ╲                             │
      │  64        ╲                            │
      │             ╲                           │
      │              ╲                          │
      │               ╲                         │
      │                ╲                        │
      │   0             ╲●                      │
      │                                         │
      └─────────────────────────────────────────┘

FORMULA: aftertouch = 127 - (travel × 127) / 240

WHAT IS MEASURED: Current travel position (inverted)
BEHAVIOR: Less travel = MORE aftertouch
USE CASE: Sustain pedal modulation, lift-off expression
REQUIRES: Pedal active to send values
```

---

### Aftertouch Mode 2: Bottom-Out (Travel-Based)

```
┌─────────────────────────────────────────────────────────────┐
│            AFTERTOUCH MODE 2: BOTTOM-OUT                     │
└─────────────────────────────────────────────────────────────┘

PREREQUISITE: aftertouch_pedal_active == true

Travel ───────────────────────────────────────────────────────►
(0-240)

      0        60       120       180       240
      │         │         │         │         │
      ▼         ▼         ▼         ▼         ▼
      ┌─────────────────────────────────────────┐
      │                                         │
AT    │ 127                              ●      │
Value │                                ╱        │
      │                              ╱          │
      │                            ╱            │
      │                          ╱              │
      │                        ╱                │
      │  64                  ╱                  │
      │                    ╱                    │
      │                  ╱                      │
      │                ╱                        │
      │              ╱                          │
      │   0 ●──────╱                            │
      │                                         │
      └─────────────────────────────────────────┘

FORMULA: aftertouch = (travel × 127) / 240

WHAT IS MEASURED: Current travel position (direct mapping)
BEHAVIOR: More travel = MORE aftertouch
USE CASE: Pressure-sensitive expression after note-on
REQUIRES: Pedal active to send values
```

---

### Aftertouch Mode 3: Post-Actuation

```
┌─────────────────────────────────────────────────────────────┐
│            AFTERTOUCH MODE 3: POST-ACTUATION                 │
└─────────────────────────────────────────────────────────────┘

NO PEDAL REQUIRED - Always active when key pressed

Travel ───────────────────────────────────────────────────────►
(0-240)

      0     ACT      120       180       240
      │      │         │         │         │
      ▼      ▼         ▼         ▼         ▼
      ┌─────────────────────────────────────────┐
      │      ┆                                  │
AT    │ 127  ┆                           ●      │
Value │      ┆                         ╱        │
      │      ┆                       ╱          │
      │      ┆                     ╱            │
      │      ┆                   ╱              │
      │  64  ┆                 ╱                │
      │      ┆               ╱                  │
      │      ┆             ╱                    │
      │      ┆           ╱                      │
      │      ┆         ╱                        │
      │   0  ●─────────●                        │
      │      ┆ (dead zone before actuation)     │
      └─────────────────────────────────────────┘
             │
             └─ Actuation threshold (normal_actuation)

FORMULA:
  if (travel >= normal_threshold) {
      additional = travel - normal_threshold
      range = 240 - normal_threshold
      aftertouch = (additional × 127) / range
  } else {
      aftertouch = 0  // Dead zone
  }

WHAT IS MEASURED: Travel beyond actuation point only
BEHAVIOR: Aftertouch only active after note triggers
USE CASE: Separates "note trigger zone" from "expression zone"
REQUIRES: Nothing (always works when key pressed past actuation)
```

---

### Aftertouch Mode 4: Vibrato (Movement Speed)

```
┌─────────────────────────────────────────────────────────────┐
│              AFTERTOUCH MODE 4: VIBRATO                      │
└─────────────────────────────────────────────────────────────┘

Time ─────────────────────────────────────────────────────────►

Travel
(0-240)

      │    Physical vibrato motion
      │    ┌───┐ ┌───┐ ┌───┐ ┌───┐
      │   ╱     ╳     ╳     ╳     ╲
      │  ╱               ╲
      │ ╱                 ╲
      │╱                   ╲
      ●─────────────────────────●────────────────────────────

                │         │
                ▼         ▼
      ┌────────────────────────────────────────────────┐
      │  travel_delta = |current_travel - last_travel| │
      │  time_delta = current_time - last_time         │
      │                                                │
      │  movement_speed = (travel_delta × 100)         │
      │                   ─────────────────            │
      │                     time_delta                 │
      │                                                │
      │  aftertouch = min(movement_speed, 127)         │
      └────────────────────────────────────────────────┘

AT
Value    Fast       Slow     Fast      Slow     Stop
      │  shake     shake    shake     shake
      │   ●         ●         ●         ●
      │  ╱│╲       ╱│╲       ╱│╲       ╱│╲
      │ ╱ │ ╲     ╱ │ ╲     ╱ │ ╲     ╱ │ ╲
      │╱  │  ╲   ╱  │  ╲   ╱  │  ╲   ╱  │  ╲
      ●───●───●─●───●───●─●───●───●─●───●───●─●──────────────

WHAT IS MEASURED: Key movement velocity (not position)
BEHAVIOR: Faster shaking = higher aftertouch
USE CASE: Physical vibrato technique
NOTE: Direction-agnostic (both up and down motion counted)
ISSUE: No smoothing - can be jittery
```

---

## Summary: What Each Mode ACTUALLY Measures

| Mode | What matrix.c Calculates | What Is Actually Used | Curves Applied |
|------|--------------------------|----------------------|----------------|
| **Velocity 0** | Fixed 64 | Fixed 64 | NO |
| **Velocity 1** | Peak travel during keystroke | Current travel at actuation | YES ✓ |
| **Velocity 2** | Keystroke speed (Δtravel/Δtime) | Current travel at actuation | YES ✓ |
| **Velocity 3** | 70% speed + 30% peak travel | Current travel at actuation | YES ✓ |
| **Aftertouch 1** | - | 127 - travel (inverted) | NO |
| **Aftertouch 2** | - | travel (direct) | NO |
| **Aftertouch 3** | - | travel beyond actuation | NO |
| **Aftertouch 4** | - | Movement speed (vibrato) | NO |

---

## Recommendations

### High Priority

1. **Connect velocity modes to the main path**: The sophisticated velocity calculations in matrix.c should feed into `get_he_velocity_from_position()` instead of being stored and ignored.

2. **Apply curves to velocity mode output**: Instead of applying curves to current travel, apply them to the velocity mode result:
   ```c
   uint8_t mode_velocity = get_mode_velocity();  // From matrix.c
   uint8_t curved = apply_curve(mode_velocity, curve_index);
   ```

3. **Add curves to aftertouch**: Consider applying velocity curves to aftertouch values for consistency.

### Medium Priority

4. **Smooth aftertouch Mode 4**: Add EMA filtering to vibrato aftertouch to reduce jitter.

5. **Configurable speed threshold**: Make `SPEED_TRIGGER_THRESHOLD` adjustable.

6. **Configurable 70/30 blend**: Make Mode 3 blend ratio user-adjustable.

---

## Code Locations Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| **LUT Linearization** | `quantum/distance_lut.h` | 1-192 | Working ✓ |
| **Velocity Modes** | `quantum/matrix.c` | 500-688 | Calculated but unused ⚠ |
| **Aftertouch Modes** | `quantum/matrix.c` | 690-745 | Working ✓ |
| **HE Velocity (main path)** | `keyboards/orthomidi5x14/orthomidi5x14.c` | 448-528 | Working ✓ |
| **Curve Application** | `keyboards/orthomidi5x14/orthomidi5x14.c` | 3462 | Working ✓ |
| **MIDI Routing** | `quantum/process_keycode/process_midi.c` | 848-863 | Working ✓ |
| **Velocity Storage** | `quantum/matrix.c` | 512-523 | Working (but rarely read) |
| **Velocity Retrieval** | `keyboards/orthomidi5x14/orthomidi5x14.c` | 2400-2409 | Rarely used ⚠ |
