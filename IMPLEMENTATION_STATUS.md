# Implementation Status - Rapid Trigger & Per-Key Actuation

## Completed ✅

### Phase 1: Data Structures (process_midi.h, process_dynamic_macro.h)
- ✅ Defined `per_key_actuation_t` structure (8 bytes per key)
- ✅ Updated `layer_key_actuations_t` to use new structure
- ✅ Removed deprecated fields from `layer_actuation_t`:
  - Removed `rapidfire_sensitivity`
  - Removed `midi_rapidfire_sensitivity`
  - Removed `midi_rapidfire_velocity`
- ✅ Added `LAYER_ACTUATION_FLAG_USE_PER_KEY_VELOCITY_CURVE` flag
- ✅ Updated function signatures (removed rapidfire params)
- ✅ Reorganized EEPROM layout:
  - Per-Key Actuation: 67000-73721 (6,722 bytes)
  - Layer Actuation: 74000-74059 (60 bytes)
  - Gaming Settings: 74100-74199 (100 bytes)

### Phase 2 (Partial): Matrix.c Structure Updates
- ✅ Added per-key rapid trigger state to `analog_key_t`:
  - `uint8_t base_velocity`
  - `bool rapid_cycle_active`
  - `bool awaiting_release`
  - `uint8_t last_direction`
- ✅ Removed duplicate fields from `midi_key_state_t`
- ✅ Updated `active_settings` cache (removed rapidfire fields)

---

## In Progress 🔄

### Phase 2: Matrix.c Rapid Trigger Implementation

**Remaining Tasks:**

1. **Delete Old Rapid Trigger Code**
   - Delete `calculate_rapid_velocity_modifier()` function (line ~426)
   - Delete old MIDI rapid trigger block (lines ~477-509)

2. **Add Helper Functions** (add after line ~441)
   ```c
   // Check if travel is in deadzone
   static bool is_in_deadzone(uint8_t travel, uint8_t deadzone_top, uint8_t deadzone_bottom) {
       // Top deadzone: 0 to deadzone_top
       if (travel <= deadzone_top) return true;

       // Bottom deadzone: (240 - deadzone_bottom) to 240
       uint8_t bottom_threshold = 240 - deadzone_bottom;
       if (travel >= bottom_threshold) return true;

       return false;
   }
   ```

3. **Implement New Rapid Trigger Logic**
   - Replace lines ~476-509 with new per-key RT state machine:
     - Check if `per_key_mode_enabled` and key has `rapidfire_enabled`
     - Implement state machine:
       1. **Initial Press**: Travel crosses actuation → ACTUATE (calculate velocity, store as base)
       2. **Awaiting Release**: Set `awaiting_release = true`
       3. **Release Detected**: Travel decreased by ≥ `rapidfire_release_sens` → `awaiting_release = false`
       4. **Re-trigger**: After release, travel increased by ≥ `rapidfire_press_sens` → ACTUATE
       5. **Velocity**: `new_vel = base_velocity + rapidfire_velocity_mod` (accumulate and clamp 1-127)
     - Apply deadzones: Disable RT when in top or bottom deadzone
     - Full release: Reset state when travel < deadzone_top

4. **Update All References**
   - Find all references to `state->rapid_cycle_active` and `state->base_velocity`
   - Update to use `key->rapid_cycle_active` and `key->base_velocity` instead

---

## Pending 📋

### Phase 3: Velocity Calculation Functions (orthomidi5x14.c)

**Files:** `vial-qmk - ryzen/keyboards/orthomidi5x14/orthomidi5x14.c`

**Tasks:**
1. **Update `get_he_velocity_from_position()`** (line ~454)
   - Check `layer_use_per_key_velocity_curve(layer)` flag
   - If true: Read curve from `per_key_actuations[layer].keys[key_index].velocity_curve`
   - If false: Read curve from global `keyboard_settings.he_velocity_curve`
   - Keep using global `keyboard_settings.he_velocity_min/max`

2. **Update `get_keysplit_he_velocity_from_position()`** (line ~508)
   - Check per-key velocity curve flag
   - Read curve from per-key if enabled, else global
   - Keep using `keyboard_settings.keysplit_he_velocity_min/max`

3. **Update `get_triplesplit_he_velocity_from_position()`** (line ~555)
   - Same as keysplit
   - Keep using `keyboard_settings.triplesplit_he_velocity_min/max`

4. **Implement helper function**
   ```c
   uint8_t get_key_velocity_curve(uint8_t layer, uint8_t row, uint8_t col) {
       if (layer_use_per_key_velocity_curve(layer) && per_key_mode_enabled) {
           uint8_t key_index = row * 14 + col;
           if (key_index < 70) {
               return per_key_actuations[layer].keys[key_index].velocity_curve;
           }
       }
       // Fallback to global
       return keyboard_settings.he_velocity_curve;
   }
   ```

---

### Phase 4: EEPROM & Persistence Functions (orthomidi5x14.c, process_midi.c)

**Tasks:**

1. **Update `initialize_per_key_actuations()`**
   - Initialize all 70 keys × 12 layers with defaults:
     ```c
     actuation: 60, deadzone_top: 4, deadzone_bottom: 4,
     velocity_curve: 2, rapidfire_enabled: 0,
     rapidfire_press_sens: 4, rapidfire_release_sens: 4,
     rapidfire_velocity_mod: 0
     ```

2. **Update `save_per_key_actuations()`**
   - Use new `PER_KEY_ACTUATION_SIZE` (6,720 bytes)
   - Save flags at `PER_KEY_ACTUATION_FLAGS_ADDR` (73720)

3. **Update `load_per_key_actuations()`**
   - Load 6,720 bytes from EEPROM
   - Check for old structure (840 bytes) and migrate if needed

4. **Update `reset_per_key_actuations()`**
   - Reset all keys to new defaults

5. **Update Layer Actuation Functions**
   - Modify `set_layer_actuation()` - remove rapid params
   - Modify `get_layer_actuation()` - remove rapid params
   - Implement `layer_use_per_key_velocity_curve(layer)`:
     ```c
     return (layer_actuations[layer].flags & LAYER_ACTUATION_FLAG_USE_PER_KEY_VELOCITY_CURVE) != 0;
     ```

6. **Implement Per-Key Helper Functions** (in orthomidi5x14.c)
   ```c
   uint8_t get_key_actuation_point(uint8_t layer, uint8_t row, uint8_t col) {
       if (!per_key_mode_enabled) {
           return layer_actuations[layer].midi_actuation;
       }
       uint8_t key_index = row * 14 + col;
       if (key_index >= 70) return DEFAULT_ACTUATION_VALUE;

       if (per_key_per_layer_enabled) {
           return per_key_actuations[layer].keys[key_index].actuation;
       } else {
           return per_key_actuations[0].keys[key_index].actuation;
       }
   }

   per_key_actuation_t* get_key_settings(uint8_t layer, uint8_t row, uint8_t col) {
       uint8_t key_index = row * 14 + col;
       if (key_index >= 70) return NULL;

       uint8_t target_layer = per_key_per_layer_enabled ? layer : 0;
       return &per_key_actuations[target_layer].keys[key_index];
   }
   ```

---

### Phase 5: HID Protocol (vial.c, quantum/vial.c)

**Tasks:**

1. **Update `handle_set_layer_actuation()`**
   - Remove rapidfire params from packet
   - New packet format (6 bytes):
     ```
     [layer, normal_actuation, midi_actuation, velocity_mode, velocity_speed_scale, flags]
     ```

2. **Update `handle_get_layer_actuation()`**
   - Return 6-byte packet (removed rapid fields)

3. **Update `handle_set_per_key_actuation()`**
   - New packet format (10 bytes):
     ```
     [layer, key_index, actuation, deadzone_top, deadzone_bottom, velocity_curve,
      rapidfire_enabled, rapidfire_press_sens, rapidfire_release_sens, rapidfire_velocity_mod]
     ```

4. **Update `handle_get_per_key_actuation()`**
   - Return 8-byte per-key structure

---

### Phase 6: Python GUI (src/main/python/)

**Files:**
- `protocol/keyboard_comm.py`
- `editor/trigger_settings.py`

**Tasks:**

1. **Update `keyboard_comm.py`**
   - Update `set_layer_actuation()` - remove rapid params
   - Update `get_layer_actuation()` - parse 6-byte packet
   - Update `set_per_key_actuation()` - send 10-byte packet:
     ```python
     def set_per_key_actuation(self, layer, key_index, settings):
         data = bytearray([
             layer, key_index,
             settings['actuation'],
             settings['deadzone_top'],
             settings['deadzone_bottom'],
             settings['velocity_curve'],
             settings['rapidfire_enabled'],
             settings['rapidfire_press_sens'],
             settings['rapidfire_release_sens'],
             settings['rapidfire_velocity_mod'] & 0xFF  # signed to unsigned
         ])
     ```
   - Update `get_per_key_actuation()` - parse 8-byte response

2. **Update `trigger_settings.py` (or equivalent UI file)**
   - **Remove:**
     - Keysplit velocity curve selector
     - Triplesplit velocity curve selector
     - Layer MIDI rapidfire toggle
     - Layer MIDI rapidfire sensitivity slider
     - Layer rapidfire sensitivity slider

   - **Add:**
     - Per-key deadzone top slider (0-20 display as 0-0.5mm)
     - Per-key deadzone bottom slider (0-20 display as 0-0.5mm)
     - Per-key velocity curve dropdown (5 options: Softest/Soft/Medium/Hard/Hardest)
     - Per-key rapidfire enable checkbox
     - Per-key rapidfire press sensitivity slider (0-100 display as 0-2.5mm)
     - Per-key rapidfire release sensitivity slider (0-100)
     - Per-key rapidfire velocity modifier slider (-64 to +64)

   - **Add Layer Settings:**
     - "Use Per-Key Velocity Curve" checkbox (sets flag bit 3)

   - **Add Convenience:**
     - "Set All Keys" button (copies current key to all 70 keys)
     - "Copy to Layer" button (copies all keys to another layer)

---

## Critical Remaining Issues

1. **Velocity Curve Fallback:**
   - ✅ RESOLVED: Use global `keyboard_settings.he_velocity_curve` when per-key flag is disabled

2. **Remove `keysplit/triplesplit_he_velocity_curve` from:**
   - ❌ `keyboard_settings_t` structure (process_dynamic_macro.h)
   - ❌ GUI displays
   - ❌ EEPROM save/load
   - ❌ HID get/set keyboard settings

---

## Testing Checklist

- [ ] Normal actuation works without per-key mode
- [ ] Per-key actuation works with per_key_mode_enabled
- [ ] Top deadzone prevents ghost triggers (0-0.1mm)
- [ ] Bottom deadzone prevents wobble (3.7-4.0mm)
- [ ] Rapid trigger requires release THEN press
- [ ] Velocity accumulates correctly (100→95→90→85)
- [ ] Velocity clamps at 1-127
- [ ] Keysplit uses per-key curve + keysplit min/max
- [ ] Triplesplit uses per-key curve + triplesplit min/max
- [ ] EEPROM save/load preserves all 8 fields
- [ ] GUI displays all new controls correctly
- [ ] "Set All Keys" button works
- [ ] Layer flag "Use Per-Key Velocity Curve" toggles correctly
