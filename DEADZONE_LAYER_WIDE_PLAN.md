# Layer-Wide Deadzone Implementation Plan

## Overview
Add deadzone configuration for normal and MIDI keys at the layer-wide level (when per-key actuation mode is disabled). This extends the existing per-key deadzone framework to work in global/layer-wide mode.

## Current State Analysis

### Existing Deadzone Implementation (Per-Key Mode)
- **Data Structure**: `per_key_actuation_t` (8 bytes per key)
  - Fields: `deadzone_top` and `deadzone_bottom` (0-100 scale, 0-2.5mm)
  - Storage: 70 keys × 12 layers = 6,720 bytes
- **Logic**: `is_in_deadzone()` function in `matrix.c:431-444`
  - Converts 0-100 scale to 0-240 travel units
  - Disables rapid trigger when in deadzone
  - Works for both MIDI and normal keys
- **Limitation**: Only available when `per_key_mode_enabled = true`

### Existing Layer-Wide Settings
- **Data Structure**: `layer_actuation_t` (5 bytes per layer)
  ```c
  typedef struct {
      uint8_t normal_actuation;      // 0-100 (0-2.5mm)
      uint8_t midi_actuation;        // 0-100 (0-2.5mm)
      uint8_t velocity_mode;         // 0-3
      uint8_t velocity_speed_scale;  // 1-20
      uint8_t flags;                 // Feature flags
  } layer_actuation_t;
  ```
- **Storage**: 12 layers × 5 bytes = 60 bytes
- **Location**: `vial-qmk - ryzen/quantum/process_keycode/process_midi.h:898-904`

### Key Type Differentiation
- **MIDI Keys**: Have `is_midi_key = true` and a valid `note_index`
  - Detected by `check_is_midi_key()` in `matrix.c:390`
  - Use `midi_actuation` threshold
- **Normal Keys**: Regular HID keyboard keys
  - Use `normal_actuation` threshold

---

## Proposed Changes

### 1. Data Structure Extension (Firmware)

#### Modify `layer_actuation_t` Structure
**File**: `vial-qmk - ryzen/quantum/process_keycode/process_midi.h:898-904`

**BEFORE (5 bytes)**:
```c
typedef struct {
    uint8_t normal_actuation;              // 0-100 (0-2.5mm)
    uint8_t midi_actuation;                // 0-100 (0-2.5mm)
    uint8_t velocity_mode;                 // 0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak
    uint8_t velocity_speed_scale;          // 1-20 (velocity scale multiplier)
    uint8_t flags;                         // Bit 2: use_fixed_velocity
} layer_actuation_t;
```

**AFTER (9 bytes)**:
```c
typedef struct {
    uint8_t normal_actuation;              // 0-100 (0-2.5mm)
    uint8_t midi_actuation;                // 0-100 (0-2.5mm)
    uint8_t velocity_mode;                 // 0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak
    uint8_t velocity_speed_scale;          // 1-20 (velocity scale multiplier)
    uint8_t flags;                         // Bit 2: use_fixed_velocity
    // NEW: Layer-wide deadzone settings
    uint8_t normal_deadzone_top;           // 0-100 (0-2.5mm) - Default: 4 (0.1mm)
    uint8_t normal_deadzone_bottom;        // 0-100 (0-2.5mm) - Default: 4 (0.1mm)
    uint8_t midi_deadzone_top;             // 0-100 (0-2.5mm) - Default: 4 (0.1mm)
    uint8_t midi_deadzone_bottom;          // 0-100 (0-2.5mm) - Default: 4 (0.1mm)
} layer_actuation_t;
```

**Storage Impact**:
- Old: 12 layers × 5 bytes = 60 bytes
- New: 12 layers × 9 bytes = 108 bytes
- **Additional EEPROM**: +48 bytes

**Default Values**:
```c
#define DEFAULT_LAYER_DEADZONE_TOP 4       // 0.1mm (same as per-key default)
#define DEFAULT_LAYER_DEADZONE_BOTTOM 4    // 0.1mm (same as per-key default)
```

---

### 2. Firmware Logic Changes

#### A. Add Deadzone Retrieval Functions
**File**: `vial-qmk - ryzen/keyboards/orthomidi5x14/orthomidi5x14.c`

**New Helper Function**:
```c
// Get deadzone values for a specific key (checks per-key mode and key type)
// Returns true if using per-key deadzones, false if using layer-wide
bool get_key_deadzone(uint8_t layer, uint8_t row, uint8_t col, bool is_midi,
                      uint8_t *deadzone_top, uint8_t *deadzone_bottom) {

    // Check if per-key mode is enabled
    if (per_key_mode_enabled) {
        // Use per-key deadzones
        uint8_t key_index = row * 14 + col;
        if (key_index >= 70) {
            *deadzone_top = DEFAULT_DEADZONE_TOP;
            *deadzone_bottom = DEFAULT_DEADZONE_BOTTOM;
            return true;
        }

        uint8_t target_layer = per_key_per_layer_enabled ? layer : 0;
        per_key_actuation_t *settings = &per_key_actuations[target_layer].keys[key_index];
        *deadzone_top = settings->deadzone_top;
        *deadzone_bottom = settings->deadzone_bottom;
        return true;
    }

    // Per-key mode disabled - use layer-wide deadzones
    if (layer >= 12) layer = 0;

    if (is_midi) {
        *deadzone_top = layer_actuations[layer].midi_deadzone_top;
        *deadzone_bottom = layer_actuations[layer].midi_deadzone_bottom;
    } else {
        *deadzone_top = layer_actuations[layer].normal_deadzone_top;
        *deadzone_bottom = layer_actuations[layer].normal_deadzone_bottom;
    }
    return false;
}
```

#### B. Update Matrix Scanning Logic
**File**: `vial-qmk - ryzen/quantum/matrix.c`

**Modify `process_midi_key_analog()` (line 463)**:

**Current Code** (lines 479-494):
```c
// Handle per-key rapid trigger mode (for ALL keys - MIDI and non-MIDI)
// Per-key rapidfire works independently of per_key_mode_enabled
if (key->mode == AKM_RAPID) {
    // Get per-key settings
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    if (current_layer >= 12) current_layer = 0;
    uint8_t key_index = row * 14 + col;

    if (key_index < 70) {
        uint8_t target_layer = per_key_per_layer_enabled ? current_layer : 0;
        per_key_actuation_t *settings = &per_key_actuations[target_layer].keys[key_index];

        // Check if rapidfire is enabled for this key (using flags field)
        if (settings->flags & PER_KEY_FLAG_RAPIDFIRE_ENABLED) {
            // Check if we're in a deadzone - if so, disable rapid trigger
            bool in_deadzone = is_in_deadzone(travel, settings->deadzone_top, settings->deadzone_bottom);
            // ... rest of rapidfire logic
        }
    }
}
```

**NEW CODE**:
```c
// Handle rapid trigger mode (for ALL keys - MIDI and non-MIDI)
if (key->mode == AKM_RAPID) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    if (current_layer >= 12) current_layer = 0;
    uint8_t key_index = row * 14 + col;

    if (key_index < 70) {
        // Determine if this is a MIDI key
        bool is_midi = state->is_midi_key;

        // Get appropriate deadzone values (per-key or layer-wide)
        uint8_t deadzone_top, deadzone_bottom;
        bool using_per_key = get_key_deadzone(current_layer, row, col, is_midi,
                                              &deadzone_top, &deadzone_bottom);

        // For per-key mode, also check if rapidfire is enabled
        bool rapidfire_enabled = false;
        per_key_actuation_t *settings = NULL;

        if (using_per_key) {
            uint8_t target_layer = per_key_per_layer_enabled ? current_layer : 0;
            settings = &per_key_actuations[target_layer].keys[key_index];
            rapidfire_enabled = (settings->flags & PER_KEY_FLAG_RAPIDFIRE_ENABLED);
        } else {
            // Layer-wide mode: rapidfire is always available
            rapidfire_enabled = true;
        }

        if (rapidfire_enabled) {
            // Check if we're in a deadzone
            bool in_deadzone = is_in_deadzone(travel, deadzone_top, deadzone_bottom);

            // ... rest of rapidfire logic (use settings for sens values if per-key mode)
        }
    }
}
```

**Key Changes**:
1. Determine if key is MIDI or normal: `bool is_midi = state->is_midi_key;`
2. Call `get_key_deadzone()` to get appropriate deadzone values
3. Handle layer-wide mode where rapidfire is always available (no per-key flags)
4. Use retrieved deadzone values in `is_in_deadzone()` call

#### C. Update Active Settings Cache
**File**: `vial-qmk - ryzen/quantum/matrix.c:46-59`

**Current Cache**:
```c
static struct {
    uint8_t normal_actuation;
    uint8_t midi_actuation;
    uint8_t velocity_mode;
    uint8_t velocity_speed_scale;
    uint8_t cached_layer;
    bool needs_update;
} active_settings = { ... };
```

**OPTION 1: Extend Cache (Recommended)**:
```c
static struct {
    uint8_t normal_actuation;
    uint8_t midi_actuation;
    uint8_t velocity_mode;
    uint8_t velocity_speed_scale;
    uint8_t normal_deadzone_top;      // NEW
    uint8_t normal_deadzone_bottom;   // NEW
    uint8_t midi_deadzone_top;        // NEW
    uint8_t midi_deadzone_bottom;     // NEW
    uint8_t cached_layer;
    bool needs_update;
} active_settings = {
    .normal_actuation = 80,
    .midi_actuation = 80,
    .velocity_mode = 2,
    .velocity_speed_scale = 10,
    .normal_deadzone_top = 4,         // NEW
    .normal_deadzone_bottom = 4,      // NEW
    .midi_deadzone_top = 4,           // NEW
    .midi_deadzone_bottom = 4,        // NEW
    .cached_layer = 0,
    .needs_update = false
};
```

**Update Cache Refresh** (`refresh_active_settings()` at line 67):
```c
void refresh_active_settings(void) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    if (current_layer >= 12) current_layer = 0;

    if (active_settings.cached_layer != current_layer || active_settings.needs_update) {
        active_settings.normal_actuation = layer_actuations[current_layer].normal_actuation;
        active_settings.midi_actuation = layer_actuations[current_layer].midi_actuation;
        active_settings.velocity_mode = layer_actuations[current_layer].velocity_mode;
        active_settings.velocity_speed_scale = layer_actuations[current_layer].velocity_speed_scale;
        active_settings.normal_deadzone_top = layer_actuations[current_layer].normal_deadzone_top;        // NEW
        active_settings.normal_deadzone_bottom = layer_actuations[current_layer].normal_deadzone_bottom;  // NEW
        active_settings.midi_deadzone_top = layer_actuations[current_layer].midi_deadzone_top;            // NEW
        active_settings.midi_deadzone_bottom = layer_actuations[current_layer].midi_deadzone_bottom;      // NEW
        active_settings.cached_layer = current_layer;
        active_settings.needs_update = false;
    }
}
```

**Usage in `get_key_deadzone()`** (optimized version):
```c
bool get_key_deadzone(uint8_t layer, uint8_t row, uint8_t col, bool is_midi,
                      uint8_t *deadzone_top, uint8_t *deadzone_bottom) {

    if (per_key_mode_enabled) {
        // Use per-key deadzones
        uint8_t key_index = row * 14 + col;
        if (key_index >= 70) {
            *deadzone_top = DEFAULT_DEADZONE_TOP;
            *deadzone_bottom = DEFAULT_DEADZONE_BOTTOM;
            return true;
        }

        uint8_t target_layer = per_key_per_layer_enabled ? layer : 0;
        per_key_actuation_t *settings = &per_key_actuations[target_layer].keys[key_index];
        *deadzone_top = settings->deadzone_top;
        *deadzone_bottom = settings->deadzone_bottom;
        return true;
    }

    // Use cached layer-wide deadzones (no array lookup!)
    if (is_midi) {
        *deadzone_top = active_settings.midi_deadzone_top;
        *deadzone_bottom = active_settings.midi_deadzone_bottom;
    } else {
        *deadzone_top = active_settings.normal_deadzone_top;
        *deadzone_bottom = active_settings.normal_deadzone_bottom;
    }
    return false;
}
```

---

### 3. EEPROM Storage Updates

#### A. Update Initialization
**File**: `vial-qmk - ryzen/keyboards/orthomidi5x14/orthomidi5x14.c:2175-2182`

**Current**:
```c
void initialize_layer_actuations(void) {
    for (uint8_t i = 0; i < 12; i++) {
        layer_actuations[i].normal_actuation = 80;
        layer_actuations[i].midi_actuation = 80;
        layer_actuations[i].velocity_mode = 0;
        layer_actuations[i].velocity_speed_scale = 10;
        layer_actuations[i].flags = 0;
    }
}
```

**NEW**:
```c
void initialize_layer_actuations(void) {
    for (uint8_t i = 0; i < 12; i++) {
        layer_actuations[i].normal_actuation = 80;
        layer_actuations[i].midi_actuation = 80;
        layer_actuations[i].velocity_mode = 0;
        layer_actuations[i].velocity_speed_scale = 10;
        layer_actuations[i].flags = 0;
        layer_actuations[i].normal_deadzone_top = DEFAULT_LAYER_DEADZONE_TOP;       // NEW: 4
        layer_actuations[i].normal_deadzone_bottom = DEFAULT_LAYER_DEADZONE_BOTTOM; // NEW: 4
        layer_actuations[i].midi_deadzone_top = DEFAULT_LAYER_DEADZONE_TOP;         // NEW: 4
        layer_actuations[i].midi_deadzone_bottom = DEFAULT_LAYER_DEADZONE_BOTTOM;   // NEW: 4
    }
}
```

#### B. Update Validation (Load from EEPROM)
**File**: `vial-qmk - ryzen/quantum/process_keycode/process_dynamic_macro.c:13188-13202`

**Add Validation**:
```c
for (uint8_t layer = 0; layer < 12; layer++) {
    if (layer_actuations[layer].normal_actuation > 100) {
        layer_actuations[layer].normal_actuation = 80;
    }
    if (layer_actuations[layer].midi_actuation > 100) {
        layer_actuations[layer].midi_actuation = 80;
    }
    if (layer_actuations[layer].velocity_mode > 3) {
        layer_actuations[layer].velocity_mode = 2;
    }
    if (layer_actuations[layer].velocity_speed_scale < 1 || layer_actuations[layer].velocity_speed_scale > 20) {
        layer_actuations[layer].velocity_speed_scale = 10;
    }

    // NEW: Validate deadzone values
    if (layer_actuations[layer].normal_deadzone_top > 100) {
        layer_actuations[layer].normal_deadzone_top = DEFAULT_LAYER_DEADZONE_TOP;
    }
    if (layer_actuations[layer].normal_deadzone_bottom > 100) {
        layer_actuations[layer].normal_deadzone_bottom = DEFAULT_LAYER_DEADZONE_BOTTOM;
    }
    if (layer_actuations[layer].midi_deadzone_top > 100) {
        layer_actuations[layer].midi_deadzone_top = DEFAULT_LAYER_DEADZONE_TOP;
    }
    if (layer_actuations[layer].midi_deadzone_bottom > 100) {
        layer_actuations[layer].midi_deadzone_bottom = DEFAULT_LAYER_DEADZONE_BOTTOM;
    }
}
```

#### C. Update Reset Function
**File**: `vial-qmk - ryzen/quantum/process_keycode/process_dynamic_macro.c:13209-13214`

**Add Deadzone Reset**:
```c
void reset_layer_actuations(void) {
    for (uint8_t layer = 0; layer < 12; layer++) {
        layer_actuations[layer].normal_actuation = 80;
        layer_actuations[layer].midi_actuation = 80;
        layer_actuations[layer].velocity_mode = 2;
        layer_actuations[layer].velocity_speed_scale = 10;
        layer_actuations[layer].flags = 0;
        layer_actuations[layer].normal_deadzone_top = DEFAULT_LAYER_DEADZONE_TOP;       // NEW
        layer_actuations[layer].normal_deadzone_bottom = DEFAULT_LAYER_DEADZONE_BOTTOM; // NEW
        layer_actuations[layer].midi_deadzone_top = DEFAULT_LAYER_DEADZONE_TOP;         // NEW
        layer_actuations[layer].midi_deadzone_bottom = DEFAULT_LAYER_DEADZONE_BOTTOM;   // NEW
    }
    save_layer_actuations();
}
```

---

### 4. HID Protocol Changes

#### Option A: Extend Existing Commands (RECOMMENDED)

**Current `handle_set_layer_actuation()` Format**:
- Input: `[layer, normal, midi, velocity, vel_speed, flags]` (6 bytes)
- Response: `[success]` (1 byte)

**Current `handle_get_layer_actuation()` Format**:
- Input: `[layer]` (1 byte)
- Response: `[success, normal, midi, velocity, vel_speed, flags]` (6 bytes)

**NEW Format (Extended)**:

**SET Command** (10 bytes input):
```c
void handle_set_layer_actuation(const uint8_t* data) {
    // data[0] = layer
    // data[1] = normal_actuation
    // data[2] = midi_actuation
    // data[3] = velocity_mode
    // data[4] = velocity_speed_scale
    // data[5] = flags
    // data[6] = normal_deadzone_top        // NEW
    // data[7] = normal_deadzone_bottom     // NEW
    // data[8] = midi_deadzone_top          // NEW
    // data[9] = midi_deadzone_bottom       // NEW

    uint8_t layer = data[0];
    if (layer >= 12) return;

    layer_actuations[layer].normal_actuation = data[1];
    layer_actuations[layer].midi_actuation = data[2];
    layer_actuations[layer].velocity_mode = data[3];
    layer_actuations[layer].velocity_speed_scale = data[4];
    layer_actuations[layer].flags = data[5];
    layer_actuations[layer].normal_deadzone_top = data[6];      // NEW
    layer_actuations[layer].normal_deadzone_bottom = data[7];   // NEW
    layer_actuations[layer].midi_deadzone_top = data[8];        // NEW
    layer_actuations[layer].midi_deadzone_bottom = data[9];     // NEW

    save_layer_actuations();
    refresh_active_settings();
}
```

**GET Command** (10 bytes response):
```c
void handle_get_layer_actuation(uint8_t layer, uint8_t* response) {
    if (layer >= 12) {
        response[0] = 0;  // Error
        return;
    }

    response[0] = 0x01;  // Success
    response[1] = layer_actuations[layer].normal_actuation;
    response[2] = layer_actuations[layer].midi_actuation;
    response[3] = layer_actuations[layer].velocity_mode;
    response[4] = layer_actuations[layer].velocity_speed_scale;
    response[5] = layer_actuations[layer].flags;
    response[6] = layer_actuations[layer].normal_deadzone_top;      // NEW
    response[7] = layer_actuations[layer].normal_deadzone_bottom;   // NEW
    response[8] = layer_actuations[layer].midi_deadzone_top;        // NEW
    response[9] = layer_actuations[layer].midi_deadzone_bottom;     // NEW
}
```

**HID Command IDs** (unchanged - extending existing commands):
- `HID_CMD_SET_LAYER_ACTUATION` = 0xB8
- `HID_CMD_GET_LAYER_ACTUATION` = 0xB9

---

### 5. GUI Changes (Python)

#### A. Update Communication Layer
**File**: `vial-gui-custom/src/main/python/protocol/keyboard_comm.py`

**Extend `set_layer_actuation()` method**:
```python
def set_layer_actuation(self, layer, normal, midi, velocity, vel_speed, flags,
                       normal_dz_top=4, normal_dz_bottom=4,  # NEW with defaults
                       midi_dz_top=4, midi_dz_bottom=4):     # NEW with defaults
    """Set layer actuation settings including deadzones"""
    data = bytes([
        layer,
        normal,
        midi,
        velocity,
        vel_speed,
        flags,
        normal_dz_top,      # NEW
        normal_dz_bottom,   # NEW
        midi_dz_top,        # NEW
        midi_dz_bottom      # NEW
    ])

    self.send_command(HID_CMD_SET_LAYER_ACTUATION, data)
```

**Extend `get_layer_actuation()` method**:
```python
def get_layer_actuation(self, layer):
    """Get layer actuation settings including deadzones"""
    response = self.send_command(HID_CMD_GET_LAYER_ACTUATION, bytes([layer]))

    if len(response) < 10:
        # Old firmware - return defaults for new fields
        return {
            'normal_actuation': response[1] if len(response) > 1 else 80,
            'midi_actuation': response[2] if len(response) > 2 else 80,
            'velocity_mode': response[3] if len(response) > 3 else 0,
            'velocity_speed_scale': response[4] if len(response) > 4 else 10,
            'flags': response[5] if len(response) > 5 else 0,
            'normal_deadzone_top': 4,      # Default
            'normal_deadzone_bottom': 4,   # Default
            'midi_deadzone_top': 4,        # Default
            'midi_deadzone_bottom': 4      # Default
        }

    return {
        'normal_actuation': response[1],
        'midi_actuation': response[2],
        'velocity_mode': response[3],
        'velocity_speed_scale': response[4],
        'flags': response[5],
        'normal_deadzone_top': response[6],      # NEW
        'normal_deadzone_bottom': response[7],   # NEW
        'midi_deadzone_top': response[8],        # NEW
        'midi_deadzone_bottom': response[9]      # NEW
    }
```

#### B. Update GUI State Management
**File**: `vial-gui-custom/src/main/python/editor/trigger_settings.py`

**Extend Layer Settings Cache**:
```python
# In __init__ or initialization:
self.layer_settings = []
for _ in range(12):
    self.layer_settings.append({
        'normal_actuation': 80,
        'midi_actuation': 80,
        'velocity_mode': 0,
        'velocity_speed_scale': 10,
        'flags': 0,
        'normal_deadzone_top': 4,      # NEW
        'normal_deadzone_bottom': 4,   # NEW
        'midi_deadzone_top': 4,        # NEW
        'midi_deadzone_bottom': 4      # NEW
    })
```

**Load Layer Settings from Firmware**:
```python
def load_layer_settings(self):
    """Load all layer settings from firmware"""
    for layer in range(12):
        settings = self.keyboard_comm.get_layer_actuation(layer)
        self.layer_settings[layer] = settings

    # Refresh UI
    self.update_layer_deadzone_ui()
```

#### C. Add UI Controls for Layer-Wide Deadzones

**NEW Section in Settings Tab** (when per-key mode is disabled):

```
┌─ Layer-Wide Deadzone Settings ─────────────────────────┐
│                                                         │
│  Normal Keys:                                           │
│    Top Deadzone:    [====|--------------------] 4      │
│                      0.1mm  (prevents ghost triggers)   │
│                                                         │
│    Bottom Deadzone: [====|--------------------] 4      │
│                      0.1mm  (prevents wobble)           │
│                                                         │
│  MIDI Keys:                                             │
│    Top Deadzone:    [====|--------------------] 4      │
│                      0.1mm  (prevents ghost triggers)   │
│                                                         │
│    Bottom Deadzone: [====|--------------------] 4      │
│                      0.1mm  (prevents wobble)           │
│                                                         │
│  [Apply to Layer]  [Copy to All Layers]                │
└─────────────────────────────────────────────────────────┘
```

**UI Components**:
1. **Four Sliders** (0-100 range, default 4):
   - `normal_deadzone_top_slider`
   - `normal_deadzone_bottom_slider`
   - `midi_deadzone_top_slider`
   - `midi_deadzone_bottom_slider`

2. **Visual Feedback**:
   - Show mm value next to slider: `0.1mm` (value × 0.025mm)
   - Show deadzone zones on a visual travel diagram

3. **Buttons**:
   - "Apply to Layer": Save current settings to active layer
   - "Copy to All Layers": Copy current layer settings to all 12 layers

**Visibility Logic**:
```python
def update_deadzone_ui_visibility(self):
    """Show layer-wide deadzone controls only when per-key mode is disabled"""
    per_key_enabled = self.per_key_mode_checkbox.isChecked()

    # Show layer-wide controls when per-key mode is OFF
    self.layer_deadzone_group.setVisible(not per_key_enabled)

    # Show per-key controls when per-key mode is ON
    self.per_key_group.setVisible(per_key_enabled)
```

---

### 6. Rapid Trigger Sensitivity (Layer-Wide Mode)

**QUESTION FOR USER**: When per-key mode is disabled, how should rapid trigger sensitivity be handled?

**Option 1: Use Layer-Wide Defaults**
- Add `normal_rapid_press_sens`, `normal_rapid_release_sens` to `layer_actuation_t`
- Add `midi_rapid_press_sens`, `midi_rapid_release_sens` to `layer_actuation_t`
- This adds 4 more bytes to the structure (13 bytes total)

**Option 2: Use Fixed Defaults**
- When per-key mode is disabled, use hardcoded defaults (e.g., 4 = 0.1mm)
- No additional storage needed

**Option 3: Reuse Existing Per-Key Storage (Layer 0)**
- When per-key mode is disabled, read rapid trigger sens from `per_key_actuations[0]`
- This is consistent with how per-key mode works in "global" mode

**RECOMMENDATION**: Start with Option 2 (fixed defaults) for simplicity. Can extend to Option 1 later if needed.

---

## Implementation Checklist

### Phase 1: Firmware Data Structure
- [ ] Add 4 deadzone fields to `layer_actuation_t` in `process_midi.h`
- [ ] Define `DEFAULT_LAYER_DEADZONE_TOP` and `DEFAULT_LAYER_DEADZONE_BOTTOM` constants
- [ ] Update `initialize_layer_actuations()` to set default values
- [ ] Update `reset_layer_actuations()` to reset new fields
- [ ] Update EEPROM validation to check new fields

### Phase 2: Firmware Logic
- [ ] Add `active_settings` cache fields for layer-wide deadzones
- [ ] Update `refresh_active_settings()` to cache new fields
- [ ] Implement `get_key_deadzone()` helper function
- [ ] Modify `process_midi_key_analog()` to use new helper
- [ ] Test that MIDI vs normal key differentiation works correctly

### Phase 3: HID Protocol
- [ ] Extend `handle_set_layer_actuation()` to accept 10 bytes
- [ ] Extend `handle_get_layer_actuation()` to return 10 bytes
- [ ] Test HID communication with existing firmware

### Phase 4: GUI Implementation
- [ ] Update `keyboard_comm.py` with extended methods
- [ ] Update `trigger_settings.py` state management
- [ ] Add UI controls for layer-wide deadzones
- [ ] Implement visibility toggle (per-key vs layer-wide)
- [ ] Add "Copy to All Layers" functionality
- [ ] Test full round-trip (GUI → Firmware → GUI)

### Phase 5: Testing & Validation
- [ ] Test normal keys with layer-wide deadzones
- [ ] Test MIDI keys with layer-wide deadzones
- [ ] Test switching between per-key and layer-wide modes
- [ ] Test layer switching preserves settings
- [ ] Test EEPROM save/load persistence
- [ ] Test rapid trigger with deadzones in both modes

---

## Questions for Review

1. **Rapid Trigger Sensitivity**: Which option (1, 2, or 3) should we use for rapid trigger sensitivity in layer-wide mode?

2. **EEPROM Layout**: The structure size increase (5 → 9 bytes) is backward-compatible since we're loading from EEPROM with validation. Should we add a version flag?

3. **GUI Layout**: Should layer-wide deadzone controls be in a separate tab, or in the same tab with visibility toggle?

4. **Default Values**: Are the defaults (4 = 0.1mm) appropriate for both normal and MIDI keys?

5. **Differentiation Logic**: Currently, MIDI keys are detected via `check_is_midi_key()`. Should we cache the MIDI/normal status in the key state structure for performance?

---

## Files to Modify

### Firmware (vial-qmk - ryzen)
1. `quantum/process_keycode/process_midi.h` - Data structure
2. `quantum/matrix.c` - Matrix scanning logic, active_settings cache
3. `keyboards/orthomidi5x14/orthomidi5x14.c` - HID handlers, helper functions
4. `quantum/process_keycode/process_dynamic_macro.c` - EEPROM validation

### GUI (vial-gui-custom)
5. `src/main/python/protocol/keyboard_comm.py` - HID communication
6. `src/main/python/editor/trigger_settings.py` - UI and state management

---

## Estimated Storage Impact

| Component | Old Size | New Size | Increase |
|-----------|----------|----------|----------|
| `layer_actuation_t` | 5 bytes | 9 bytes | +4 bytes |
| 12 Layers | 60 bytes | 108 bytes | +48 bytes |
| **Total EEPROM** | **60 bytes** | **108 bytes** | **+48 bytes** |

**Current EEPROM Budget**: See `EEPROM_USAGE_REPORT.md` for available space
