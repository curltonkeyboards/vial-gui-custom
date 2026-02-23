# CLAUDE.md - Project Knowledge Base

## Project Overview

This is a custom Vial GUI + QMK firmware for the **orthomidi5x14** Hall effect MIDI keyboard (5 rows x 14 columns = 70 keys). It combines a Python/PyQt5 desktop configurator with a ChibiOS-based QMK firmware fork that implements analog Hall effect sensing, MIDI velocity, aftertouch, rapid trigger, and per-key calibration.

## Repository Structure

```
vial-gui-custom/
├── src/main/python/              # PyQt5 GUI application
│   ├── main.py                   # Entry point
│   ├── main_window.py            # Main application window
│   ├── editor/
│   │   ├── velocity_tab.py       # Velocity config, preset management, live visualization
│   │   ├── trigger_settings.py   # Per-key actuation/RT/deadzone configuration
│   │   ├── matrix_test.py        # Matrix testing/debugging
│   │   ├── keymap_editor.py      # Keymap layout editor
│   │   └── rgb_configurator.py   # LED configuration
│   └── widgets/
│       └── curve_editor.py       # Interactive 4-point velocity curve editor (300x300 canvas)
├── vial-qmk - ryzen/            # Firmware (QMK fork)
│   ├── quantum/
│   │   ├── matrix.c              # Core analog matrix (2660+ lines) - calibration, RT, MIDI, velocity
│   │   ├── matrix.h              # Constants, structs, public API
│   │   └── distance_lut.h        # 1024-entry log LUT + EQ curve adjustment
│   └── keyboards/orthomidi5x14/
│       └── config.h              # Hardware config (ADC defaults, pin mappings)
├── requirements.txt              # Python deps (PyQt5==5.9.2, fbs==0.9.0, python-rtmidi)
└── *.md                          # Various implementation/analysis docs
```

## Build System

- **GUI:** Python 3.6+ with PyQt5, built via `fbs` (Flask-Based Setup)
- **Firmware:** QMK build system (ChibiOS-based for ARM)
- **Entry point:** `src/main/python/main.py`

---

## Firmware Architecture (matrix.c)

### Scan Cycle Pipeline

Every scan cycle, each key goes through this pipeline (matrix.c ~line 2180):

```
1. Read raw ADC sample
2. Filter (EMA currently BYPASSED - line 2192, using raw directly)
3. Update calibration (continuous auto-calibration)
4. Calculate distance: adc_to_distance(filtered, rest, bottom) → 0-255
5. Apply rest dead zone: distance <= 3 → 0  (prevents ADC noise residuals)
6. Process rapid trigger state machine (3-state FSM)
7. Process MIDI key (velocity modes, aftertouch, retrigger)
```

### Key State Structure (`key_state_t`, line 110)

```c
typedef struct {
    uint16_t adc_raw;               // Raw ADC (no filtering)
    uint16_t adc_filtered;          // Filtered ADC (EMA bypassed, currently = raw)
    uint16_t adc_rest_value;        // Calibrated rest position
    uint16_t adc_bottom_out_value;  // Calibrated bottom-out position
    uint8_t  distance;              // 0-255 (0=rest, 255=full press)
    uint8_t  extremum;              // Peak/trough for RT FSM
    key_dir_t key_dir;              // KEY_DIR_INACTIVE / DOWN / UP
    bool     is_pressed;            // Logical pressed state
    bool     calibrated;            // Has been bottom-out calibrated
    uint8_t  base_velocity;         // For RT velocity accumulation
    uint16_t last_adc_value;        // Previous ADC (stability detection)
    uint16_t stable_start_adc;      // ADC when stability was first detected
    uint32_t stable_time;           // Timestamp when key became stable
    bool     is_stable;             // Currently stable
} key_state_t;
```

### Hardware Constants (matrix.h)

| Constant | Value | Meaning |
|----------|-------|---------|
| `MATRIX_ROWS` x `MATRIX_COLS` | 5 x 14 = 70 keys | Physical matrix |
| `FULL_TRAVEL_UNIT` | 40 | 4.0mm max travel (0.1mm per unit) |
| `TRAVEL_SCALE` | 6 | Internal precision multiplier |
| `DISTANCE_MAX` | 255 | Full-range distance scale |
| `DEFAULT_ZERO_TRAVEL_VALUE` | 3000 | Default rest ADC (overridden per-key at boot) |
| `DEFAULT_FULL_RANGE` | 900 | Typical ADC range rest-to-bottom |
| `VALID_ANALOG_RAW_VALUE_MIN/MAX` | 1000 / 2500 | Valid ADC bounds |
| `CALIBRATION_EPSILON` | 5 | Minimum meaningful ADC movement |
| `AUTO_CALIB_ZERO_TRAVEL_JITTER` | 50 | Minimum stability threshold |
| `AUTO_CALIB_STABILITY_PERCENT` | 2 | Must be within 2% of stable value |
| `AUTO_CALIB_MAX_REST_DRIFT_PERCENT` | 10 | Only recalibrate if within 10% of rest |
| `AUTO_CALIB_VALID_RELEASE_TIME` | 5000 | 5 seconds stability required for recalibration |

### Hall Effect Sensor Characteristics

- **Inverted operation:** Higher ADC = more released, lower ADC = more pressed
- **Typical rest ADC:** 1650-2250
- **Typical pressed ADC:** 1100-1350
- **Warm-up estimation:** `bottom = rest * 0.52 + 200` (linear fit from measured data)

---

## Calibration System (matrix.c, `update_calibration()` ~line 882)

### How It Works

Auto-calibration continuously tracks the true rest and bottom-out positions:

1. **Stability Detection:** Key must stay within 2% of a stable reference value. If it drifts beyond 2% or moves more than `CALIBRATION_EPSILON` (5 ADC units), stability resets.

2. **Rest Recalibration:** When the key is:
   - Stable (not jittering)
   - Not pressed (`is_pressed == false`)
   - Near rest (raw ADC within 10% of current `adc_rest_value`)
   - Stable for **5 seconds** (`AUTO_CALIB_VALID_RELEASE_TIME`)
   - ADC has drifted more than `CALIBRATION_EPSILON` from current rest

   Then `adc_rest_value` is updated to the current filtered ADC.

3. **Bottom-out Recalibration:** Whenever a new minimum ADC is seen (below current `adc_bottom_out_value - CALIBRATION_EPSILON`), the bottom is updated immediately. This expands the range continuously.

### Critical Design Decision: Both Directions Require 5s Wait

**Both** "away from pressed" (upward ADC) **and** "toward pressed" (downward ADC) drift require the 5-second stability wait before recalibrating rest. This was changed because the previous instant upward recalibration allowed transient ADC spikes (20-30 units) to be immediately locked in as the new rest position, creating persistent 0.1-0.2mm residual readings.

### Initialization (Warm-up, ~line 2270)

During the first 5 scan cycles:
- `adc_rest_value` = actual ADC reading
- `adc_bottom_out_value` = estimated via `rest * 0.52 + 200`
- `adc_filtered` = actual ADC reading

---

## Distance Calculation (distance_lut.h)

### Pipeline: ADC → Distance (0-255)

```
1. Normalize: (rest - adc) * 1023 / (rest - bottom)  → 0-1023
2. Apply EQ curve adjustment (per-range sensitivity)   → 0-1023
3. Calculate linear distance: normalized * 255 / 1023  → 0-255
4. Look up LUT-corrected distance: distance_lut[normalized] → 0-255
5. Blend: linear * (100 - strength) + lut * strength) / 100
```

**Boundary behavior:**
- `adc >= rest` → distance = 0 (at or above rest)
- `adc <= bottom` → distance = 255 (at or below bottom)

### Rest Dead Zone (matrix.c, after `adc_to_distance()`)

After distance calculation: `if (distance <= 3) distance = 0`

This eliminates 1-2 ADC unit noise residuals (~0.05mm) that would otherwise produce non-zero distance at rest and break the `last_travel == 0 && travel > 0` velocity timer gate.

### EQ Curve Adjustment (distance_lut.h, `apply_eq_curve_adjustment()`)

A 5-band parametric equalizer for the distance curve, with 3 range presets based on the key's rest ADC value:
- **Range 0** (rest < 1745): Low rest sensors
- **Range 1** (rest 1745-2082): Mid rest (neutral baseline)
- **Range 2** (rest >= 2082): High rest sensors

Each range has 5 frequency bands covering 20% of the input range each, with adjustable weights (25%-400%). A range scale multiplier applies an overall gain. Quadratic blending between ranges based on rest position.

### LUT Correction (distance_lut.h)

1024-entry logarithmic lookup table compensating for Hall effect sensor non-linearity. Strength parameter (0-100) blends between linear and LUT-corrected distance. Formula: `LUT[x] = round(255 * log10(1 + a*x) / log10(1 + a*1023))`

---

## Rapid Trigger State Machine (matrix.c, `process_rapid_trigger()` ~line 1003)

3-state FSM inspired by libhmk:

```
KEY_DIR_INACTIVE → (distance > actuation_point) → KEY_DIR_DOWN [pressed]
KEY_DIR_DOWN     → (distance <= reset_point)     → KEY_DIR_INACTIVE [released]
KEY_DIR_DOWN     → (distance + rt_up < extremum) → KEY_DIR_UP [released by RT]
KEY_DIR_UP       → (distance <= reset_point)     → KEY_DIR_INACTIVE [released]
KEY_DIR_UP       → (extremum + rt_down < distance) → KEY_DIR_DOWN [re-pressed by RT]
```

- **Continuous RT mode:** `reset_point = 0` (must fully release to reset)
- **Normal RT mode:** `reset_point = actuation_point`

### Deadzone Remapping (inside `process_rapid_trigger()`)

Before RT logic, distance is remapped through per-key deadzones:
- `distance <= dz_bottom` → 0
- `distance >= 255 - dz_top` → 255
- Otherwise: linearly rescaled `[dz_bottom, 255-dz_top]` → `[0, 255]`

---

## Velocity Modes (matrix.c, `process_midi_key_analog()` ~line 1230)

### Mode 0: Fixed Velocity
Raw velocity = 255. The velocity curve determines actual output.

### Mode 1: Peak Travel (Direction Reversal)
- Triggers at max velocity when actuation point is crossed
- OR triggers on direction reversal (key starts moving up after pressing down)
- Velocity = peak travel depth (deeper = louder)
- Min peak: 12 units (~0.2mm), reversal threshold: 3 units
- Note off at travel < 30 (~0.5mm)

### Mode 2: Speed-Based (Rest to Actuation)
- Timer starts when `last_travel == 0 && travel > 0` (key starts moving from rest)
- Velocity captured when travel crosses the actuation threshold
- Linear interpolation: `max_press_time` → velocity 255, `min_press_time` → velocity 1
- Supports partial re-press with midpoint velocity scaling
- Deadzone compensation scales elapsed time by `255 / effective_range`

### Mode 3: Speed + Peak Combined
- Blends speed-based and peak travel velocity using `zone_speed_peak_ratio`
- Triggers on direction reversal (blended) OR actuation point (blended)
- `blended = (speed * ratio + peak * (100 - ratio)) / 100`

### Critical: `last_travel` Reset on Release

In all speed-based modes (1, 2, 3), when a note-off condition triggers, `last_travel` is set to 0 and the `last_travel = travel` update is **skipped that cycle** (via an else branch). This ensures the `last_travel == 0 && travel > 0` gate fires correctly on the next press. Previously, `last_travel = travel` at the bottom of each mode unconditionally overwrote the 0 with residual travel, preventing the speed timer from ever restarting.

---

## Aftertouch Modes (matrix.c ~line 1850)

| Mode | Name | Formula | Sustain Suppression |
|------|------|---------|-------------------|
| 0 | Off | None | - |
| 1 | Bottom-out | `travel * 127 / 240` | Yes |
| 2 | Bottom-out (NS) | `travel * 127 / 240` | No |
| 3 | Reverse | `127 - (travel * 127 / 240)` | Yes |
| 4 | Reverse (NS) | `127 - (travel * 127 / 240)` | No |
| 5 | Post-actuation | `extra_travel * 127 / (240 - actuation)` | Yes |
| 6 | Post-actuation (NS) | Same | No |
| 7 | Vibrato | Leaky integrator of travel deltas | Yes |
| 8 | Vibrato (NS) | Same | No |

When aftertouch is active, the retrigger byte is repurposed as smoothness (0-100%) which acts as a slew rate limiter.

---

## Per-Key Configuration

### Full Structure (8 bytes, EEPROM/HID)
```
actuation (0-255, default 127 = 2.0mm)
deadzone_top (0-51, default 6)
deadzone_bottom (0-51, default 6)
velocity_curve (0-16: 0-6 factory, 7-16 user)
flags (bit 0: RT enabled, bit 1: per-key velocity, bit 2: continuous RT)
rapidfire_press_sens (0-100, default 6)
rapidfire_release_sens (0-100, default 6)
rapidfire_velocity_mod (-64 to +64, default 0)
```

### Optimized Cache (6 bytes, RAM - `per_key_config_lite_t`)
```
actuation, rt_down, rt_up, flags, dz_bottom, dz_top
```
70 keys x 6 bytes = 420 bytes per layer, fits in L1 cache.

---

## Zone System

Three independent zones for split keyboard configurations:
- **ZONE_TYPE_BASE (0):** Main zone (MI_* keycodes)
- **ZONE_TYPE_KEYSPLIT (1):** Left/right split (MI_SPLIT_* keycodes, 0xC600-0xC647)
- **ZONE_TYPE_TRIPLESPLIT (2):** Three zones (MI_SPLIT2_* keycodes, 0xC670-0xC6B7)

Each zone can have independent velocity curves, actuation overrides, retrigger distances, and speed/peak blend ratios. Controlled by `keysplitvelocitystatus`: 0=all same, 1=keysplit only, 2=triplesplit only, 3=both.

---

## GUI: Velocity Curve Editor (widgets/curve_editor.py)

- 300x300 canvas with 10x10 grid
- 4 draggable control points connected by polyline
- Points 0 and 3 are x-constrained (x=0 and x=255)
- X axis: input (time/travel), Y axis: output (velocity)
- Factory curves: Softest, Soft, Linear, Hard, Hardest, Aggro, Digital (indices 0-6)
- User curves: 10 slots (indices 7-16)
- Current labels: 0%/100% at corners

## GUI: Preset Settings Layout (editor/velocity_tab.py ~line 1005)

Two side-by-side boxes:
- **Presets list** (left): `maxWidth(180)`, contains scrollable list of factory + user presets
- **Preset Settings** (right): Contains zone tabs with embedded curve editors + controls

---

## Bugs Fixed in This Session

### 1. Instant Upward Rest Recalibration (Root Cause of 0.1-0.2mm Residual)
**File:** `matrix.c` line 952
**Problem:** When ADC drifted "away from pressed" (upward for inverted Hall sensors), `adc_rest_value` was updated **instantly** with no stability wait. Random ADC spikes of 20-30 units were immediately locked in as the new rest, creating a persistent gap between calibrated rest and actual rest.
**Fix:** Both drift directions now require the 5-second stability wait (`AUTO_CALIB_VALID_RELEASE_TIME`).

### 2. `last_travel` Overwrite in Velocity Modes 1, 2, 3
**File:** `matrix.c` lines ~1389, ~1483, ~1618
**Problem:** On release, each mode set `state->last_travel = 0`, but the unconditional `state->last_travel = travel` at the bottom of each case block immediately overwrote it with the residual travel value. The `last_travel == 0 && travel > 0` speed timer gate could never fire on the next press.
**Fix:** Wrapped `state->last_travel = travel` in an `else` branch so it's skipped on the same cycle as the release reset.

### 3. Distance Dead Zone at Rest
**File:** `matrix.c` line ~2202
**Problem:** 1-2 ADC unit noise produced distance 1-3 (non-zero) at rest, even with correct calibration.
**Fix:** Added `if (key->distance <= 3) key->distance = 0` after `adc_to_distance()`. Eliminates ~0.05mm noise residuals.

---

## EEPROM Memory Map

| Address | Size | Content |
|---------|------|---------|
| 38000-39249 | 5 x 250 bytes | Keyboard settings (5 slots) |
| 40000 | 5 x ~10 bytes | Layer actuation settings (deprecated) |
| 41300 | 24 bytes | EQ curve config (magic 0xEA01) |
| Per-key actuations | 70 x 8 x 12 layers | 6,720 bytes total |

## EMA Filter Status

Currently **bypassed** for troubleshooting (line 2192):
```c
// TROUBLESHOOTING: Bypass EMA filter, use raw ADC directly
// Original: key->adc_filtered = EMA(raw_value, key->adc_filtered);
key->adc_filtered = raw_value;
```
EMA alpha = 1/16 (exponent 4). Re-enabling would smooth noise but add ~16 scan cycle latency.
