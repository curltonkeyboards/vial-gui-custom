# Per-Key Actuation System Overhaul - Compatibility Fixes

## Overview
This document details all changes made to fix compilation errors after the actuation system overhaul that moved rapidfire and other settings from layer-based to per-key based configuration.

## Date
December 29, 2025

## Problem Summary
After implementing the actuation system overhaul, compilation errors occurred due to:
1. Missing structure fields in `keyboard_settings_t`
2. Changed structure member names in `layer_actuation_t` and `layer_key_actuations_t`
3. Function signature mismatches
4. References to deprecated rapidfire fields

---

## Structural Changes

### 1. `keyboard_settings_t` Structure Updates

**File:** `quantum/process_keycode/process_dynamic_macro.h`

**Added Fields:**
```c
// Keysplit HE Velocity curve and range
uint8_t keysplit_he_velocity_curve;   // 0-4 (SOFTEST, SOFT, MEDIUM, HARD, HARDEST)
uint8_t keysplit_he_velocity_min;     // 1-127 (minimum velocity)
uint8_t keysplit_he_velocity_max;     // 1-127 (maximum velocity)

// Triplesplit HE Velocity curve and range
uint8_t triplesplit_he_velocity_curve; // 0-4 (SOFTEST, SOFT, MEDIUM, HARD, HARDEST)
uint8_t triplesplit_he_velocity_min;   // 1-127 (minimum velocity)
uint8_t triplesplit_he_velocity_max;   // 1-127 (maximum velocity)
```

**Reason:** Implement 3-tier velocity curve priority system while maintaining split-specific velocity ranges.

---

### 2. `layer_actuation_t` Structure Changes

**File:** `quantum/process_keycode/process_midi.h`

**Current Structure (after overhaul):**
```c
typedef struct {
    uint8_t normal_actuation;      // 0-100 (0-2.5mm)
    uint8_t midi_actuation;        // 0-100 (0-2.5mm)
    uint8_t velocity_mode;         // 0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak
    uint8_t velocity_speed_scale;  // 1-20 (velocity scale multiplier)
    uint8_t flags;                 // Bit 2: use_fixed_velocity
} layer_actuation_t;
```

**Removed Fields:**
- `rapidfire_sensitivity` - Moved to per-key actuations
- `midi_rapidfire_sensitivity` - Moved to per-key actuations
- `midi_rapidfire_velocity` - Moved to per-key actuations

**Impact:** Reduced from 8 bytes to 5 bytes per layer (60 bytes total vs 96 bytes).

---

### 3. `layer_key_actuations_t` Structure Changes

**File:** `quantum/process_keycode/process_midi.h`

**Old Structure:**
```c
typedef struct {
    uint8_t actuation[70];  // Single actuation value per key
} layer_key_actuations_t;
```

**New Structure:**
```c
typedef struct {
    per_key_actuation_t keys[70];  // Full settings per key
} layer_key_actuations_t;

typedef struct {
    uint8_t actuation;              // 0-100 (0-2.5mm)
    uint8_t deadzone_top;           // 0-100 (0-2.5mm)
    uint8_t deadzone_bottom;        // 0-100 (0-2.5mm)
    uint8_t velocity_curve;         // 0-4
    uint8_t flags;                  // Bit 0: rapidfire_enabled, Bit 1: use_per_key_velocity_curve
    uint8_t rapidfire_press_sens;   // 0-100 (0-2.5mm)
    uint8_t rapidfire_release_sens; // 0-100 (0-2.5mm)
    int8_t  rapidfire_velocity_mod; // -64 to +64
} per_key_actuation_t;
```

**Impact:** Increased from 70 bytes to 560 bytes per layer (840 bytes total → 6,720 bytes total).

---

## Implementation: 3-Tier Velocity Curve Priority System

### Velocity Curve Selection Logic

**File:** `keyboards/orthomidi5x14/orthomidi5x14.c`

**Function:** `get_key_velocity_curve(uint8_t layer, uint8_t row, uint8_t col, uint8_t split_type)`

**Priority Hierarchy:**

1. **Priority 1: Per-Key Curve** (Highest)
   - Checks if `PER_KEY_FLAG_USE_PER_KEY_VELOCITY_CURVE` flag is set
   - Returns `per_key_actuations[layer].keys[key].velocity_curve`

2. **Priority 2: Split-Specific Curve** (Middle)
   - Checks `keyboard_settings.keysplitvelocitystatus`:
     - `0` = disabled
     - `1` = keysplit only
     - `2` = triplesplit only
     - `3` = both enabled
   - If `split_type == 1` AND status allows: Returns `keyboard_settings.keysplit_he_velocity_curve`
   - If `split_type == 2` AND status allows: Returns `keyboard_settings.triplesplit_he_velocity_curve`

3. **Priority 3: Global Fallback** (Lowest)
   - Returns `keyboard_settings.he_velocity_curve`

**Split Types:**
- `0` = Base/Main MIDI
- `1` = Keysplit
- `2` = Triplesplit

### Function Signature Update

**Old:**
```c
uint8_t get_key_velocity_curve(uint8_t layer, uint8_t row, uint8_t col);
```

**New:**
```c
uint8_t get_key_velocity_curve(uint8_t layer, uint8_t row, uint8_t col, uint8_t split_type);
```

**Updated in:**
- `quantum/process_keycode/process_midi.h` (declaration)
- `keyboards/orthomidi5x14/orthomidi5x14.c` (implementation)

**Callers Updated:**
- `get_he_velocity_from_position()` → calls with `split_type=0`
- `get_keysplit_he_velocity_from_position()` → calls with `split_type=1`
- `get_triplesplit_he_velocity_from_position()` → calls with `split_type=2`

---

## Code Fixes by File

### File: `keyboards/orthomidi5x14/orthomidi5x14.c`

#### 1. Variable Definitions (Lines 95-104)
**Added:**
```c
velocity_curve_t keysplit_he_velocity_curve = VELOCITY_CURVE_MEDIUM;
uint8_t keysplit_he_velocity_min = 1;
uint8_t keysplit_he_velocity_max = 127;
velocity_curve_t triplesplit_he_velocity_curve = VELOCITY_CURVE_MEDIUM;
uint8_t triplesplit_he_velocity_min = 1;
uint8_t triplesplit_he_velocity_max = 127;
```

#### 2. Removed Duplicate Definitions (Lines 351-360)
**Removed:** Duplicate definitions that were causing redefinition errors.

#### 3. Layer Actuation Initialization (Lines 2286-2296)
**Removed:**
```c
layer_actuations[i].rapidfire_sensitivity = 50;
layer_actuations[i].midi_rapidfire_sensitivity = 50;
layer_actuations[i].midi_rapidfire_velocity = 0;
```

**Reason:** These fields no longer exist in `layer_actuation_t`.

#### 4. Settings Reset Function (Lines 2633-2647)
**Added:**
```c
keysplit_he_velocity_curve = VELOCITY_CURVE_MEDIUM;
triplesplit_he_velocity_curve = VELOCITY_CURVE_MEDIUM;
```

**Removed comment:** "Note: keysplit/triplesplit curves now use per-key or global fallback"

#### 5. Settings Struct Sync (Lines 2678-2692)
**Added:**
```c
keyboard_settings.keysplit_he_velocity_curve = keysplit_he_velocity_curve;
keyboard_settings.triplesplit_he_velocity_curve = triplesplit_he_velocity_curve;
```

#### 6. Settings Load Function (Lines 2736-2750)
**Added:**
```c
keysplit_he_velocity_curve = keyboard_settings.keysplit_he_velocity_curve;
triplesplit_he_velocity_curve = keyboard_settings.triplesplit_he_velocity_curve;
```

#### 7. Per-Key Actuation Copy (Line 3343)
**Old:**
```c
per_key_actuations[dest].actuation[i] = per_key_actuations[source].actuation[i];
```

**New:**
```c
per_key_actuations[dest].keys[i] = per_key_actuations[source].keys[i];
```

**Reason:** Now copying entire `per_key_actuation_t` struct instead of single byte.

#### 8. EEPROM Initialization Check (Line 3739)
**Old:**
```c
if (per_key_actuations[0].actuation[0] == 0xFF)
```

**New:**
```c
if (per_key_actuations[0].keys[0].actuation == 0xFF)
```

**Reason:** Access pattern changed from array to struct array.

---

### File: `keyboards/orthomidi5x14/orthomidi5x14.h`

#### Extern Declarations (Lines 128-136)
**Added:**
```c
extern velocity_curve_t keysplit_he_velocity_curve;
extern uint8_t keysplit_he_velocity_min;
extern uint8_t keysplit_he_velocity_max;
extern velocity_curve_t triplesplit_he_velocity_curve;
extern uint8_t triplesplit_he_velocity_min;
extern uint8_t triplesplit_he_velocity_max;
```

---

### File: `quantum/process_keycode/process_dynamic_macro.c`

#### 1. Load Layer Actuations (Lines 13083-13089)
**Removed:**
```c
if (layer_actuations[layer].rapidfire_sensitivity < 1 || ...) {
    layer_actuations[layer].rapidfire_sensitivity = 4;
}
if (layer_actuations[layer].midi_rapidfire_sensitivity < 1 || ...) {
    layer_actuations[layer].midi_rapidfire_sensitivity = 10;
}
if (layer_actuations[layer].midi_rapidfire_velocity > 20) {
    layer_actuations[layer].midi_rapidfire_velocity = 10;
}
```

**Added comment:** "Note: rapidfire settings moved to per-key actuations"

#### 2. Reset Layer Actuations (Lines 13095-13107)
**Removed:**
```c
layer_actuations[layer].rapidfire_sensitivity = 4;
layer_actuations[layer].midi_rapidfire_sensitivity = 10;
layer_actuations[layer].midi_rapidfire_velocity = 10;
```

#### 3. Set Layer Actuation Function (Lines 13109-13130)
**Old Signature:**
```c
void set_layer_actuation(uint8_t layer, uint8_t normal, uint8_t midi, uint8_t velocity,
                         uint8_t rapid, uint8_t midi_rapid_sens, uint8_t midi_rapid_vel,
                         uint8_t vel_speed, uint8_t flags)
```

**New Signature:**
```c
void set_layer_actuation(uint8_t layer, uint8_t normal, uint8_t midi, uint8_t velocity,
                         uint8_t vel_speed, uint8_t flags)
```

**Removed:** All rapidfire parameter validation and assignments.

#### 4. Get Layer Actuation Function (Lines 13132-13150)
**Old Signature:**
```c
void get_layer_actuation(uint8_t layer, uint8_t *normal, uint8_t *midi, uint8_t *velocity,
                         uint8_t *rapid, uint8_t *midi_rapid_sens, uint8_t *midi_rapid_vel,
                         uint8_t *vel_speed, uint8_t *flags)
```

**New Signature:**
```c
void get_layer_actuation(uint8_t layer, uint8_t *normal, uint8_t *midi, uint8_t *velocity,
                         uint8_t *vel_speed, uint8_t *flags)
```

**Removed:** All rapidfire output assignments.

#### 5. Helper Functions (Lines 13152-13162)
**Changed:**
```c
bool layer_rapidfire_enabled(uint8_t layer) {
    (void)layer;
    return false;  // Rapidfire moved to per-key actuations
}

bool layer_midi_rapidfire_enabled(uint8_t layer) {
    (void)layer;
    return false;  // MIDI rapidfire moved to per-key actuations
}
```

**Reason:** These functions now always return false since rapidfire is per-key.

#### 6. HID Set Layer Actuation Handler (Lines 13168-13189)
**Old Call:**
```c
set_layer_actuation(layer, normal, midi, velocity, rapid,
                   midi_rapid_sens, midi_rapid_vel, vel_speed, flags);
```

**New Call:**
```c
set_layer_actuation(layer, normal, midi, velocity, vel_speed, flags);
```

**Updated Comments:**
```c
// data[5-7] were rapidfire parameters (now per-key, ignored)
```

#### 7. HID Get All Layer Actuations Handler (Lines 13209-13254)
**Old Format:** 12 layers × 8 bytes = 96 bytes (4 packets of 24 bytes)
**New Format:** 12 layers × 5 bytes = 60 bytes (3 packets of 20 bytes)

**Removed from each layer:**
```c
response[idx++] = layer_actuations[layer].rapidfire_sensitivity;
response[idx++] = layer_actuations[layer].midi_rapidfire_sensitivity;
response[idx++] = layer_actuations[layer].midi_rapidfire_velocity;
```

**Packet Structure Changed:**
- Packet 0: Layers 0-3 (20 bytes)
- Packet 1: Layers 4-7 (20 bytes)
- Packet 2: Layers 8-11 (20 bytes)

---

## Default Values

All new fields initialized with **MEDIUM (2)** curve and **full range (1-127)**:

```c
keysplit_he_velocity_curve = VELOCITY_CURVE_MEDIUM;      // 2
keysplit_he_velocity_min = 1;
keysplit_he_velocity_max = 127;
triplesplit_he_velocity_curve = VELOCITY_CURVE_MEDIUM;   // 2
triplesplit_he_velocity_min = 1;
triplesplit_he_velocity_max = 127;
```

---

## Backward Compatibility Notes

### HID Protocol Changes
- **Layer actuation packet size reduced:** 8 bytes → 5 bytes per layer
- **Rapidfire parameters removed:** GUI/host software must use per-key actuation HID commands for rapidfire settings
- **Data byte positions changed:** Bytes 5-7 in HID packets now ignored (were rapidfire)

### EEPROM Layout Impact
- **keyboard_settings_t increased:** +2 bytes (added 2 curve fields)
- **layer_actuation_t decreased:** -3 bytes per layer (-36 bytes total)
- **per_key_actuations increased:** +490 bytes per layer (+5,880 bytes total)

**Net EEPROM Change:** Significant increase due to per-key storage (~5,846 bytes).

---

## Testing Recommendations

### 1. Velocity Curve Priority Testing
- [ ] Test per-key curve override works (Priority 1)
- [ ] Test split-specific curves with different `keysplitvelocitystatus` values (Priority 2)
- [ ] Test global fallback when no overrides set (Priority 3)

### 2. Settings Persistence
- [ ] Verify keysplit/triplesplit curves save to EEPROM
- [ ] Test settings load correctly after power cycle
- [ ] Verify settings reset to MEDIUM (2) on factory reset

### 3. HID Communication
- [ ] Test GUI can read layer actuations (new 5-byte format)
- [ ] Test GUI ignores bytes 5-7 when setting layer actuations
- [ ] Verify per-key actuation HID commands work for rapidfire

### 4. Functional Testing
- [ ] Test keysplit velocity curve changes take effect
- [ ] Test triplesplit velocity curve changes take effect
- [ ] Verify velocity ranges (min/max) work correctly for each split
- [ ] Test per-key rapidfire still functions

---

## Related Commits

1. **50b49d31** - "Fix actuation system struct compatibility after overhaul"
   - Added missing struct fields
   - Implemented 3-tier priority system
   - Fixed struct member access

2. **b2c1762d** - "Fix redefinition errors and function signature mismatch"
   - Removed duplicate variable definitions
   - Updated function signatures

3. **7ee86ba4** - "Remove deprecated rapidfire fields from process_dynamic_macro.c"
   - Cleaned up all rapidfire references
   - Updated HID handlers

---

## Future Considerations

### GUI Updates Required
The GUI/host software will need updates to:
1. Use per-key actuation HID commands for rapidfire settings
2. Handle new 5-byte layer actuation format
3. Support keysplit/triplesplit velocity curve settings
4. Display 3-tier priority indicator for velocity curves

### Performance Impact
- **Memory:** Increased RAM usage for per-key storage
- **Speed:** Negligible - priority check is simple bitwise operations
- **EEPROM:** More writes needed when changing per-key settings

---

## Summary

This overhaul successfully:
✅ Moved rapidfire from layer-based to per-key configuration
✅ Implemented 3-tier velocity curve priority system
✅ Maintained split-specific velocity ranges
✅ Reduced layer actuation struct size (8→5 bytes)
✅ Fixed all compilation errors
✅ Maintained backward compatibility where possible

**Total Code Impact:**
- 3 header files modified
- 2 source files modified
- ~150 lines changed/removed
- 0 compilation errors remaining
