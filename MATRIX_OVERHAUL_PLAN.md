# Matrix Scanning System Overhaul Plan
## Migrating orthomidi5x14 to libhmk Architecture

**Objective:** Replace the current matrix scanning system with libhmk's superior approach, prioritizing CPU efficiency and robust analog key handling while maintaining existing MIDI and layer functionality.

**Rationale:** libhmk's matrix scanning is superior in CPU efficiency, noise immunity (EMA filtering), automatic calibration, and built-in rapid trigger implementation. These features eliminate key delays and noise issues that are the primary concern.

---

## PHASE 1: Core Matrix Infrastructure

### 1.1 Data Structure Migration

**Current State (orthomidi5x14):**
```c
// Per-key actuation (optional, 8 bytes × 70 keys × 12 layers = 6,720 bytes)
typedef struct {
    uint8_t actuation;
    uint8_t deadzone_top;
    uint8_t deadzone_bottom;
    uint8_t velocity_curve;
    uint8_t flags;
    uint8_t rapidfire_press_sens;
    uint8_t rapidfire_release_sens;
    int8_t  rapidfire_velocity_mod;
} per_key_actuation_t;

// Layer-wide actuation (simple, ~100 bytes total)
typedef struct {
    uint8_t normal_actuation;
    uint8_t midi_actuation;
    uint8_t velocity_mode;
    uint8_t velocity_speed_scale;
    uint8_t flags;
} layer_actuation_t;
```

**Target State (libhmk approach):**
```c
// Per-key state (10 bytes × 70 keys = 700 bytes)
typedef struct {
    uint16_t adc_filtered;          // 2 bytes - EMA filtered ADC value
    uint16_t adc_rest_value;        // 2 bytes - Calibrated rest position
    uint16_t adc_bottom_out_value;  // 2 bytes - Calibrated bottom-out
    uint8_t  distance;              // 1 byte - Normalized travel (0-255)
    uint8_t  extremum;              // 1 byte - Peak detection for rapid trigger
    uint8_t  key_dir;               // 1 byte - KEY_DIR_INACTIVE/DOWN/UP
    bool     is_pressed;            // 1 byte - Current press state
} key_state_t;

key_state_t key_matrix[MATRIX_ROWS][MATRIX_COLS];
```

**Action Items:**
- [ ] Define `key_state_t` structure in `keyboards/orthomidi5x14/orthomidi5x14.h`
- [ ] Allocate `key_matrix[5][14]` global array (700 bytes)
- [ ] Define `key_dir_t` enum: `KEY_DIR_INACTIVE = 0, KEY_DIR_DOWN, KEY_DIR_UP`
- [ ] Remove dependency on `per_key_actuations[]` array (saves 6,720 bytes)
- [ ] Keep `layer_actuations[]` for MIDI-specific settings (velocity mode, etc.)

**Memory Impact:** 700 bytes (new) - 6,720 bytes (removed) = **-6,020 bytes saved**

---

### 1.2 EMA Filtering Implementation

**Current State:** No filtering, raw ADC values used directly

**Target State:**
```c
// Constants
#define MATRIX_EMA_ALPHA_EXPONENT 4  // Smoothing factor (higher = more smoothing)

// Macro for efficient EMA calculation
#define EMA(current, previous) \
    (((uint32_t)(current) + \
      ((uint32_t)(previous) * ((1 << MATRIX_EMA_ALPHA_EXPONENT) - 1))) >> \
     MATRIX_EMA_ALPHA_EXPONENT)

// In matrix scan loop:
void matrix_scan_key(uint8_t row, uint8_t col) {
    key_state_t *key = &key_matrix[row][col];

    // Read raw ADC value
    uint16_t raw_adc = analog_matrix_read(row, col);

    // Apply EMA filter
    key->adc_filtered = EMA(raw_adc, key->adc_filtered);

    // ... rest of processing
}
```

**Action Items:**
- [ ] Add `MATRIX_EMA_ALPHA_EXPONENT` to config (default: 4)
- [ ] Implement `EMA()` macro in `quantum/matrix.c`
- [ ] Modify `analog_matrix_task_internal()` to store filtered values in `key_matrix[]`
- [ ] Replace all direct ADC reads with `key->adc_filtered` access

**CPU Impact:** ~20 cycles per key (efficient bitshift math)
**Benefit:** Eliminates noise-induced false triggers, improves consistency

---

### 1.3 Automatic Calibration System

**Current State:** Manual calibration, static rest/bottom-out values

**Target State:**
```c
// Calibration constants
#define MATRIX_CALIBRATION_DURATION 500      // 500ms calibration period
#define MATRIX_CALIBRATION_EPSILON 5         // Minimum ADC change threshold
#define MATRIX_INACTIVITY_TIMEOUT 3000       // 3s idle before recalibration

typedef struct {
    uint32_t calibration_start;              // Timestamp for calibration
    bool     is_calibrating;                 // Calibration active flag
    uint32_t last_activity;                  // Last key press timestamp
} calibration_state_t;

void matrix_calibration_update(uint8_t row, uint8_t col) {
    key_state_t *key = &key_matrix[row][col];
    uint32_t now = timer_read32();

    // Check for inactivity (no keys pressed for 3s)
    if (now - calibration.last_activity > MATRIX_INACTIVITY_TIMEOUT) {
        if (!calibration.is_calibrating) {
            calibration.is_calibrating = true;
            calibration.calibration_start = now;
        }

        // Update rest value during calibration period
        if (now - calibration.calibration_start < MATRIX_CALIBRATION_DURATION) {
            if (key->adc_filtered < key->adc_rest_value - MATRIX_CALIBRATION_EPSILON) {
                key->adc_rest_value = key->adc_filtered;

                // Recalculate bottom-out (rest + threshold)
                key->adc_bottom_out_value = key->adc_rest_value +
                    get_bottom_out_threshold(row, col);

                // Cap at ADC_MAX_VALUE
                if (key->adc_bottom_out_value > ADC_MAX_VALUE) {
                    key->adc_bottom_out_value = ADC_MAX_VALUE;
                }
            }
        } else {
            calibration.is_calibrating = false;
        }
    } else {
        calibration.is_calibrating = false;
    }
}
```

**Action Items:**
- [ ] Add calibration constants to `config.h`
- [ ] Implement `calibration_state_t` in `quantum/matrix.c`
- [ ] Add `matrix_calibration_update()` function
- [ ] Call calibration update during matrix scan
- [ ] Initialize rest values to first ADC readings on boot
- [ ] Store calibrated values in EEPROM (optional persistence)

**CPU Impact:** ~15 cycles per key during calibration, ~5 cycles otherwise
**Benefit:** Automatic compensation for temperature drift, wear, manufacturing variance

---

### 1.4 Distance Normalization

**Current State:** Direct ADC comparison to actuation thresholds

**Target State:**
```c
// Normalize ADC value to 0-255 distance range
uint8_t calculate_distance(key_state_t *key) {
    uint16_t adc = key->adc_filtered;
    uint16_t rest = key->adc_rest_value;
    uint16_t bottom = key->adc_bottom_out_value;

    if (adc <= rest) {
        return 0;  // At or above rest position
    }

    if (adc >= bottom) {
        return 255;  // At or below bottom-out
    }

    // Linear interpolation between rest and bottom-out
    uint32_t range = bottom - rest;
    uint32_t position = adc - rest;
    return (position * 255) / range;
}

void matrix_scan_key(uint8_t row, uint8_t col) {
    key_state_t *key = &key_matrix[row][col];

    // Calculate normalized distance
    key->distance = calculate_distance(key);

    // ... use key->distance for all comparisons
}
```

**Action Items:**
- [ ] Implement `calculate_distance()` function
- [ ] Update all actuation checks to use normalized distance (0-255)
- [ ] Convert existing actuation thresholds from "0-100" to "0-255" range
- [ ] Update MIDI velocity calculations to use `key->distance`

**CPU Impact:** ~15 cycles per key (simple arithmetic)
**Benefit:** Consistent behavior across keys with different ADC ranges, easier threshold tuning

---

### 1.5 Rapid Trigger State Machine

**Current State:** Per-key rapidfire feature (part of per-key actuation system)

**Target State (built into matrix):**
```c
// Rapid trigger settings (global or per-key via bitmap)
typedef struct {
    uint8_t actuation_point;     // Primary actuation threshold (0-255)
    uint8_t reset_point;         // Full release threshold (0-255)
    uint8_t rt_down;             // Re-press sensitivity (distance units)
    uint8_t rt_up;               // Release sensitivity (distance units)
    bool    continuous_mode;     // If true, no reset point required
} rapid_trigger_config_t;

rapid_trigger_config_t rt_config;

// Bitmap for per-key RT disable
static bitmap_t rapid_trigger_disabled[BITMAP_SIZE(MATRIX_ROWS * MATRIX_COLS)];

void matrix_rapid_trigger_process(uint8_t row, uint8_t col) {
    key_state_t *key = &key_matrix[row][col];
    uint8_t key_index = row * MATRIX_COLS + col;

    // Check if RT is disabled for this key
    bool rt_disabled = bitmap_get(rapid_trigger_disabled, key_index);

    if (rt_disabled) {
        // Simple threshold detection
        if (key->distance >= rt_config.actuation_point) {
            key->is_pressed = true;
        } else if (key->distance <= rt_config.reset_point) {
            key->is_pressed = false;
        }
        return;
    }

    // Rapid Trigger state machine
    switch (key->key_dir) {
        case KEY_DIR_INACTIVE:
            // Check for initial press
            if (key->distance >= rt_config.actuation_point) {
                key->is_pressed = true;
                key->key_dir = KEY_DIR_DOWN;
                key->extremum = key->distance;
            }
            break;

        case KEY_DIR_DOWN:
            // Update peak
            if (key->distance > key->extremum) {
                key->extremum = key->distance;
            }

            // Check for release via rapid trigger (upward motion)
            if (key->distance + rt_config.rt_up < key->extremum) {
                key->is_pressed = false;
                key->key_dir = KEY_DIR_UP;
                key->extremum = key->distance;
            }

            // Check for full release to inactive
            if (!rt_config.continuous_mode && key->distance <= rt_config.reset_point) {
                key->is_pressed = false;
                key->key_dir = KEY_DIR_INACTIVE;
                key->extremum = 0;
            }
            break;

        case KEY_DIR_UP:
            // Update valley
            if (key->distance < key->extremum) {
                key->extremum = key->distance;
            }

            // Check for re-press via rapid trigger (downward motion)
            if (key->extremum + rt_config.rt_down < key->distance) {
                key->is_pressed = true;
                key->key_dir = KEY_DIR_DOWN;
                key->extremum = key->distance;
            }

            // Check for full release to inactive
            if (!rt_config.continuous_mode && key->distance <= rt_config.reset_point) {
                key->key_dir = KEY_DIR_INACTIVE;
                key->extremum = 0;
            }
            break;
    }
}
```

**Action Items:**
- [ ] Define `rapid_trigger_config_t` structure
- [ ] Allocate `rapid_trigger_disabled[]` bitmap
- [ ] Implement `matrix_rapid_trigger_process()` function
- [ ] Integrate RT processing into main matrix scan loop
- [ ] Add HID commands to configure RT settings (actuation, reset, rt_up, rt_down)
- [ ] Add HID command to toggle RT per-key via bitmap
- [ ] Remove old per-key rapidfire implementation

**CPU Impact:** ~25 cycles per key (simple state machine, no divisions)
**Benefit:**
- Always available, no extra memory per key
- Continuous mode allows instant re-actuation
- More responsive than threshold-based systems

---

## PHASE 2: Advanced Keys System

### 2.1 Advanced Key Types

**Implement 4 types of advanced keys from libhmk:**

#### 2.1.1 Null Bind
```c
typedef struct {
    uint16_t keycodes[2];        // Primary and secondary keycodes
} null_bind_config_t;

typedef struct {
    bool is_pressed[2];          // Track both key states
    uint16_t active_keycodes[2]; // Currently active keycodes
} ak_state_null_bind_t;
```

**Behavior:** Monitor 2 selected keys, register both when either is pressed. Useful for simultaneous Shift+Key combinations.

---

#### 2.1.2 Dynamic Keystroke
```c
typedef struct {
    uint16_t keycodes[4];        // 4 keycode slots
    uint8_t  bitmap[4];          // 2 bits × 4 events × 4 slots = 32 bits
    uint8_t  bottom_out_point;   // Bottom-out threshold (0-255)
} dynamic_keystroke_config_t;

typedef struct {
    bool is_pressed[4];          // Track each keycode slot
    bool is_bottomed_out;        // Bottom-out state
} ak_state_dynamic_keystroke_t;

// Event types
typedef enum {
    AK_EVENT_TYPE_HOLD = 0,                      // Unused in DKS
    AK_EVENT_TYPE_PRESS,                         // On actuation
    AK_EVENT_TYPE_BOTTOM_OUT,                    // On bottom-out
    AK_EVENT_TYPE_RELEASE_FROM_BOTTOM_OUT,       // On upstroke from bottom
    AK_EVENT_TYPE_RELEASE                        // On full release
} ak_event_type_t;

// Actions (2 bits)
typedef enum {
    DKS_ACTION_NONE = 0,
    DKS_ACTION_PRESS = 1,        // Press and hold
    DKS_ACTION_TAP = 2,          // Instant tap
    DKS_ACTION_HOLD = 3          // Hold until released
} dks_action_t;
```

**Behavior:** 4 keycode slots, each can trigger on 4 events (PRESS, BOTTOM_OUT, RELEASE_FROM_BOTTOM_OUT, RELEASE). Compact bitmap encoding.

**Note:** This is simpler than orthomidi's current DKS (2 zones vs 8 zones). To maintain current DKS expressiveness, we'll keep orthomidi's 8-threshold DKS as a separate advanced key type.

---

#### 2.1.3 Tap-Hold
```c
typedef struct {
    uint16_t tap_keycode;        // Keycode for tap
    uint16_t hold_keycode;       // Keycode for hold
    uint16_t tapping_term;       // Threshold time (ms)
} tap_hold_config_t;

typedef enum {
    TAP_HOLD_STAGE_NONE = 0,
    TAP_HOLD_STAGE_TAP,
    TAP_HOLD_STAGE_HOLD
} tap_hold_stage_t;

typedef struct {
    uint32_t since;              // Timestamp of press
    uint8_t  stage;              // Current stage
} ak_state_tap_hold_t;
```

**Behavior:** Send different keycodes based on press duration. If released before `tapping_term`, send `tap_keycode`. If held beyond `tapping_term`, send `hold_keycode`.

---

#### 2.1.4 Toggle
```c
typedef struct {
    uint16_t keycode;            // Keycode to toggle
    uint16_t tapping_term;       // Threshold time (ms)
} toggle_config_t;

typedef enum {
    TOGGLE_STAGE_NONE = 0,
    TOGGLE_STAGE_TOGGLE,
    TOGGLE_STAGE_NORMAL
} toggle_stage_t;

typedef struct {
    uint32_t since;              // Timestamp of press
    uint8_t  stage;              // Current stage
    bool     is_toggled;         // Toggle state
} ak_state_toggle_t;
```

**Behavior:** Toggles key state on quick tap. If held beyond `tapping_term`, acts as normal key press/release.

---

### 2.2 Advanced Key Infrastructure

**Unified State Structure:**
```c
// Advanced key type enum
typedef enum {
    AK_TYPE_NONE = 0,
    AK_TYPE_NULL_BIND,
    AK_TYPE_DYNAMIC_KEYSTROKE,
    AK_TYPE_TAP_HOLD,
    AK_TYPE_TOGGLE,
    AK_TYPE_ORTHOMIDI_DKS,       // Keep existing 8-threshold DKS
} advanced_key_type_t;

// Union for all state types
typedef union {
    ak_state_null_bind_t null_bind;
    ak_state_dynamic_keystroke_t dynamic_keystroke;
    ak_state_tap_hold_t tap_hold;
    ak_state_toggle_t toggle;
    dks_state_t orthomidi_dks;   // Existing DKS state
} advanced_key_state_t;

// Per-key advanced key mapping
typedef struct {
    uint8_t type;                // advanced_key_type_t
    uint8_t config_index;        // Index into type-specific config array
} advanced_key_mapping_t;

advanced_key_mapping_t ak_map[MATRIX_ROWS][MATRIX_COLS];
advanced_key_state_t ak_states[MATRIX_ROWS][MATRIX_COLS];
```

**Action Items:**
- [ ] Define all advanced key structs in `quantum/process_keycode/process_advanced_keys.h`
- [ ] Implement unified `advanced_key_mapping_t` system
- [ ] Create config arrays for each advanced key type
- [ ] Implement event processing functions for each type
- [ ] Add deferred action queue for race condition prevention
- [ ] Integrate advanced key processing into matrix scan

**Memory Impact:**
- Mapping: 2 bytes × 70 keys = 140 bytes
- States: ~8 bytes × 70 keys = 560 bytes (assuming not all keys use advanced features)
- Total: ~700 bytes

---

### 2.3 Deferred Action Queue

**Purpose:** Prevent race conditions when multiple actions trigger in the same scan

```c
typedef enum {
    DEFERRED_ACTION_PRESS = 0,
    DEFERRED_ACTION_TAP,
    DEFERRED_ACTION_RELEASE,
    DEFERRED_ACTION_HOLD
} deferred_action_type_t;

typedef struct {
    uint8_t  key;                // Key index
    uint16_t keycode;            // Keycode to send
    uint8_t  action_type;        // PRESS/TAP/RELEASE/HOLD
} deferred_action_t;

#define DEFERRED_ACTION_QUEUE_SIZE 16
deferred_action_t deferred_queue[DEFERRED_ACTION_QUEUE_SIZE];
uint8_t deferred_queue_head = 0;
uint8_t deferred_queue_tail = 0;

void deferred_action_push(uint8_t key, uint16_t keycode, deferred_action_type_t type);
void deferred_action_process_all(void);
```

**Action Items:**
- [ ] Implement deferred action queue
- [ ] Add `deferred_action_push()` function
- [ ] Call `deferred_action_process_all()` at end of matrix scan
- [ ] Use deferred actions in all advanced key implementations

**CPU Impact:** ~10 cycles per queued action
**Benefit:** Prevents HID report corruption when multiple actions occur simultaneously

---

## PHASE 3: Integration & Migration

### 3.1 Matrix Scan Loop Restructuring

**Current Flow:**
```
matrix_scan_custom()
  ├─ analog_matrix_task_internal()  // Read ADCs
  ├─ For each key: compare travel > actuation
  ├─ Process MIDI keys
  └─ Process DKS keys (if keycode in range)
```

**New Flow:**
```
matrix_scan_custom()
  ├─ analog_matrix_task_internal()  // Read ADCs
  ├─ For each key:
  │   ├─ Apply EMA filter → key->adc_filtered
  │   ├─ Update calibration (if idle)
  │   ├─ Calculate distance → key->distance
  │   ├─ Process rapid trigger state machine → key->is_pressed
  │   ├─ Detect advanced key events (PRESS, BOTTOM_OUT, RELEASE, etc.)
  │   └─ Call advanced key handler (if mapped)
  ├─ Process MIDI velocity (use key->distance instead of raw travel)
  ├─ Process deferred actions
  └─ Generate matrix for QMK
```

**Action Items:**
- [ ] Refactor `analog_matrix_task_internal()` to populate `key_matrix[]`
- [ ] Move actuation logic into `matrix_rapid_trigger_process()`
- [ ] Add calibration update calls
- [ ] Add distance calculation
- [ ] Add advanced key event detection
- [ ] Update MIDI velocity to use `key->distance`
- [ ] Add deferred action processing at end

**CPU Impact:** Similar total cycles, but distributed more evenly across features

---

### 3.2 Per-Key Actuation Compatibility Layer

**Strategy:** Maintain compatibility with existing per-key actuation configurations during migration

```c
// Migration function: convert old per-key actuation to new system
void migrate_per_key_actuation(void) {
    for (uint8_t layer = 0; layer < 12; layer++) {
        for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
            for (uint8_t col = 0; col < MATRIX_COLS; col++) {
                per_key_actuation_t *old = &per_key_actuations[layer].keys[row * 14 + col];

                // Convert actuation point (0-100 → 0-255)
                uint8_t actuation_255 = (old->actuation * 255) / 100;
                set_key_actuation(row, col, actuation_255);

                // Convert rapidfire to rapid trigger settings
                if (old->flags & PER_KEY_FLAG_RAPIDFIRE_ENABLED) {
                    uint8_t rt_up = (old->rapidfire_release_sens * 255) / 100;
                    uint8_t rt_down = (old->rapidfire_press_sens * 255) / 100;
                    set_rapid_trigger(row, col, rt_up, rt_down);
                } else {
                    // Disable rapid trigger for this key
                    bitmap_set(rapid_trigger_disabled, row * MATRIX_COLS + col, true);
                }

                // Convert velocity curve to advanced key if needed
                // (store per-key velocity curve in advanced key config)
            }
        }
    }
}
```

**Action Items:**
- [ ] Implement migration function
- [ ] Add HID command to trigger migration
- [ ] Test migration with existing configurations
- [ ] Add fallback to old system if migration fails
- [ ] Document migration process for users

---

### 3.3 MIDI Integration

**Keep existing MIDI velocity system, update to use new distance values:**

```c
// Update velocity calculation to use key->distance
uint8_t get_he_velocity_from_position(uint8_t row, uint8_t col) {
    key_state_t *key = &key_matrix[row][col];
    uint8_t layer = get_highest_layer(layer_state);

    // Use existing velocity mode from layer_actuations
    uint8_t velocity_mode = layer_actuations[layer].velocity_mode;

    switch (velocity_mode) {
        case VELOCITY_MODE_FIXED:
            return 64;  // Fixed velocity

        case VELOCITY_MODE_PEAK:
            // Use key->extremum for peak detection
            return apply_velocity_curve(key->extremum);

        case VELOCITY_MODE_SPEED:
            // Calculate speed from distance change
            uint8_t speed = key->distance - key->last_distance;
            return apply_velocity_curve(speed);

        case VELOCITY_MODE_SPEED_PEAK:
            // Combination of speed and peak
            return apply_velocity_curve(max(key->extremum, speed));
    }
}
```

**Action Items:**
- [ ] Update `get_he_velocity_from_position()` to use `key->distance`
- [ ] Update peak detection to use `key->extremum`
- [ ] Add `last_distance` field to `key_state_t` for speed calculation
- [ ] Test MIDI velocity with new system
- [ ] Keep existing velocity curve system

**Benefit:** More accurate velocity with filtered values, built-in peak detection

---

### 3.4 Layer System Compatibility

**Current:** Per-key actuation can be per-layer or global (via `per_key_per_layer_enabled`)

**New:** Actuation points are per-key, not per-layer (following libhmk model)

**Solution:** Add layer-based actuation override system:

```c
// Optional: layer-based actuation overrides
typedef struct {
    bool     enabled;
    uint8_t  actuation_override;  // Override actuation point for this layer
} layer_actuation_override_t;

layer_actuation_override_t layer_overrides[12][MATRIX_ROWS][MATRIX_COLS];

uint8_t get_effective_actuation(uint8_t row, uint8_t col) {
    uint8_t layer = get_highest_layer(layer_state);

    // Check for layer override
    if (layer_overrides[layer][row][col].enabled) {
        return layer_overrides[layer][row][col].actuation_override;
    }

    // Use base per-key actuation
    return key_actuation_points[row][col];
}
```

**Action Items:**
- [ ] Decide if layer-based overrides are needed (adds complexity)
- [ ] If yes, implement `layer_actuation_override_t` system
- [ ] If no, document that actuation is per-key only (simpler, follows libhmk)
- [ ] Update HID commands accordingly

**Recommendation:** Skip layer overrides initially, add only if users request it

---

## PHASE 4: Configuration & EEPROM

### 4.1 EEPROM Layout

**New configuration structure (following libhmk model):**

```c
typedef struct {
    // Magic numbers for validation
    uint32_t magic_start;
    uint8_t  version;

    // Global calibration data
    uint16_t initial_rest_values[MATRIX_ROWS][MATRIX_COLS];
    uint16_t bottom_out_thresholds[MATRIX_ROWS][MATRIX_COLS];

    // Per-key actuation points
    uint8_t actuation_points[MATRIX_ROWS][MATRIX_COLS];

    // Rapid trigger settings
    rapid_trigger_config_t rapid_trigger;
    bitmap_t rapid_trigger_disabled[BITMAP_SIZE(MATRIX_ROWS * MATRIX_COLS)];

    // Advanced key configs
    advanced_key_mapping_t ak_mappings[MATRIX_ROWS][MATRIX_COLS];

    // Type-specific config arrays
    null_bind_config_t null_bind_configs[MAX_NULL_BIND_KEYS];
    dynamic_keystroke_config_t dks_configs[MAX_DKS_KEYS];
    tap_hold_config_t tap_hold_configs[MAX_TAP_HOLD_KEYS];
    toggle_config_t toggle_configs[MAX_TOGGLE_KEYS];

    // Keep existing MIDI settings
    layer_actuation_t layer_actuations[12];
    keyboard_settings_t keyboard_settings;

    uint32_t magic_end;
} eeprom_config_t;
```

**Action Items:**
- [ ] Design new EEPROM layout
- [ ] Implement versioning system
- [ ] Add migration from old EEPROM format
- [ ] Implement save/load functions
- [ ] Add wear leveling (optional, following libhmk)
- [ ] Test EEPROM corruption detection

**Memory Impact:** ~3-4KB EEPROM usage (depends on max advanced key counts)

---

### 4.2 Default Configuration

```c
// Default values on first boot or reset
void load_default_config(void) {
    // Calibration: will auto-calibrate on first scan
    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            key_matrix[row][col].adc_rest_value = ADC_MAX_VALUE;  // Will learn
            key_matrix[row][col].adc_bottom_out_value = 0;        // Will learn
        }
    }

    // Actuation points: 128 (50% travel)
    memset(actuation_points, 128, sizeof(actuation_points));

    // Rapid trigger: moderate settings
    rt_config.actuation_point = 128;
    rt_config.reset_point = 32;
    rt_config.rt_up = 10;      // Release after 10 units upward travel
    rt_config.rt_down = 10;    // Re-press after 10 units downward travel
    rt_config.continuous_mode = false;

    // Advanced keys: none by default
    memset(ak_mappings, 0, sizeof(ak_mappings));

    // MIDI: keep existing defaults
    // ...
}
```

**Action Items:**
- [ ] Implement `load_default_config()`
- [ ] Add factory reset HID command
- [ ] Document default settings

---

### 4.3 HID Command Extensions

**New HID commands for configuration:**

```c
// Matrix configuration
#define HID_CMD_SET_ACTUATION_POINT       0x40
#define HID_CMD_GET_ACTUATION_POINT       0x41
#define HID_CMD_SET_RT_CONFIG             0x42
#define HID_CMD_GET_RT_CONFIG             0x43
#define HID_CMD_SET_RT_DISABLED           0x44  // Bitmap
#define HID_CMD_GET_RT_DISABLED           0x45

// Advanced key configuration
#define HID_CMD_SET_AK_MAPPING            0x50
#define HID_CMD_GET_AK_MAPPING            0x51
#define HID_CMD_SET_NULL_BIND_CONFIG      0x52
#define HID_CMD_SET_DKS_CONFIG            0x53
#define HID_CMD_SET_TAP_HOLD_CONFIG       0x54
#define HID_CMD_SET_TOGGLE_CONFIG         0x55

// Calibration
#define HID_CMD_TRIGGER_CALIBRATION       0x60
#define HID_CMD_GET_CALIBRATION_STATUS    0x61
#define HID_CMD_RESET_CALIBRATION         0x62

// Debug/monitoring
#define HID_CMD_GET_KEY_STATE             0x70  // Get full key_state_t
#define HID_CMD_GET_DISTANCE              0x71  // Get distance for all keys
#define HID_CMD_GET_EXTREMUM              0x72  // Get extremum for all keys
```

**Action Items:**
- [ ] Implement all HID command handlers
- [ ] Update HID descriptor
- [ ] Add error handling and validation
- [ ] Document HID protocol

---

## PHASE 5: GUI Integration (Vial-GUI)

### 5.1 Vial-GUI Matrix Configuration Tab

**New UI elements needed:**

1. **Per-Key Actuation Editor:**
   - Visual keyboard layout
   - Click key to edit actuation point (slider 0-255)
   - Real-time distance visualization
   - Calibration status indicator

2. **Rapid Trigger Configuration:**
   - Global RT settings (actuation, reset, rt_up, rt_down)
   - Continuous mode toggle
   - Per-key RT enable/disable (visual grid)

3. **Advanced Key Assignment:**
   - Dropdown to select advanced key type per key
   - Type-specific configuration dialogs:
     - Null Bind: Select 2 keys to monitor
     - DKS: Configure 4 keycode slots + bitmap
     - Tap-Hold: Set tap/hold keycodes + tapping term
     - Toggle: Set keycode + tapping term

4. **Calibration Control:**
   - Manual calibration trigger button
   - Calibration status display
   - Reset calibration button
   - View current rest/bottom-out values

5. **Debug View:**
   - Real-time distance heatmap
   - Extremum visualization
   - Key state indicators (INACTIVE/DOWN/UP)
   - ADC value monitor

**Action Items:**
- [ ] Design UI mockups for each tab
- [ ] Implement Qt widgets for configuration
- [ ] Add HID communication layer
- [ ] Implement real-time monitoring
- [ ] Add validation and error handling
- [ ] Write user documentation

---

### 5.2 Migration Wizard

**Create a wizard to help users migrate from old system:**

1. **Welcome screen:** Explain new matrix system benefits
2. **Backup current config:** Save old EEPROM to file
3. **Detect existing settings:** Analyze current per-key actuation, rapidfire, DKS
4. **Auto-migrate:** Convert to new format
5. **Manual adjustments:** Allow user to tweak migrated settings
6. **Flash to keyboard:** Write new config
7. **Verify:** Test all keys, compare to old behavior

**Action Items:**
- [ ] Implement migration wizard in Vial-GUI
- [ ] Add backup/restore functionality
- [ ] Implement setting comparison tool
- [ ] Add rollback option
- [ ] Write migration guide

---

## PHASE 6: Testing & Validation

### 6.1 Unit Tests

**Test coverage needed:**

- [ ] EMA filtering accuracy (known input/output pairs)
- [ ] Distance normalization edge cases (rest=0, bottom=max, etc.)
- [ ] Rapid trigger state machine (all transitions)
- [ ] Advanced key event generation (PRESS, BOTTOM_OUT, RELEASE, etc.)
- [ ] Deferred action queue (overflow, ordering, etc.)
- [ ] Calibration algorithm (drift, stability, convergence)
- [ ] EEPROM save/load (corruption detection, versioning)

---

### 6.2 Integration Tests

**End-to-end testing:**

- [ ] Matrix scan performance (measure CPU cycles per scan)
- [ ] Latency testing (actuation to HID report time)
- [ ] Noise immunity (inject ADC noise, verify filtering)
- [ ] Temperature drift (simulate ADC drift, verify auto-calibration)
- [ ] Rapid trigger responsiveness (compare to old rapidfire)
- [ ] MIDI velocity accuracy (compare to old system)
- [ ] Advanced key combinations (DKS + tap-hold, etc.)
- [ ] Layer switching with actuation changes
- [ ] EEPROM wear testing (many save cycles)

---

### 6.3 User Acceptance Testing

**Real-world testing scenarios:**

- [ ] Gaming: Rapid trigger in FPS games (WASD)
- [ ] Music: MIDI velocity consistency, DKS chords
- [ ] Typing: Normal typing feel, no false triggers
- [ ] Mixed use: Layers with different actuation points
- [ ] Long-term: Temperature drift compensation over hours

---

## PHASE 7: Documentation

### 7.1 Developer Documentation

- [ ] Architecture overview (data structures, flow diagrams)
- [ ] API reference (all functions, parameters, return values)
- [ ] HID protocol specification
- [ ] EEPROM layout documentation
- [ ] Porting guide (for other keyboards)

---

### 7.2 User Documentation

- [ ] Feature comparison (old vs new system)
- [ ] Configuration guide (how to use Vial-GUI)
- [ ] Migration guide (step-by-step)
- [ ] Troubleshooting (common issues, solutions)
- [ ] FAQ (rapid trigger, calibration, advanced keys)

---

### 7.3 Performance Documentation

- [ ] CPU cycle analysis (per feature, total)
- [ ] Memory usage breakdown
- [ ] Latency measurements
- [ ] Comparison to libhmk (where we differ and why)
- [ ] Comparison to old system (improvements, trade-offs)

---

## IMPLEMENTATION TIMELINE

### Week 1-2: Phase 1 (Core Matrix)
- Implement data structures
- Implement EMA filtering
- Implement auto-calibration
- Implement distance normalization
- Implement rapid trigger state machine
- Test matrix scanning performance

### Week 3-4: Phase 2 (Advanced Keys)
- Implement advanced key types
- Implement deferred action queue
- Integrate with matrix scan
- Test advanced key functionality

### Week 5-6: Phase 3 (Integration)
- Refactor matrix scan loop
- Update MIDI integration
- Test compatibility with existing features

### Week 7-8: Phase 4 (Configuration)
- Design EEPROM layout
- Implement HID commands
- Implement save/load
- Test configuration persistence

### Week 9-10: Phase 5 (GUI)
- Implement Vial-GUI tabs
- Implement migration wizard
- Test GUI ↔ firmware communication

### Week 11-12: Phase 6 (Testing)
- Unit tests
- Integration tests
- User acceptance testing
- Performance validation

### Week 13-14: Phase 7 (Documentation)
- Write developer docs
- Write user docs
- Create video tutorials
- Publish release

---

## SUCCESS CRITERIA

### Performance Targets:
- [ ] **CPU usage:** ≤ 100 cycles per key per scan (target: ~70)
- [ ] **Latency:** ≤ 1ms from actuation to HID report
- [ ] **Noise immunity:** No false triggers with ±10 ADC units noise
- [ ] **Calibration:** Converge within 500ms, track ±50 ADC drift

### Functional Requirements:
- [ ] **Rapid trigger:** Re-actuation within 0.1mm (configurable)
- [ ] **Advanced keys:** All 4 types working reliably
- [ ] **MIDI:** Velocity accuracy ±5% vs old system
- [ ] **Compatibility:** Migrate existing configs without manual work

### Quality Standards:
- [ ] **Code coverage:** ≥ 80% for all new code
- [ ] **Documentation:** Complete API docs, user guide
- [ ] **User testing:** 10+ users test and approve before release

---

## RISK MITIGATION

### Risk 1: Performance Regression
- **Mitigation:** Benchmark at each phase, optimize hot paths
- **Fallback:** Keep old matrix code as compile-time option

### Risk 2: Configuration Migration Failure
- **Mitigation:** Extensive testing, backup/restore functionality
- **Fallback:** Manual migration guide, support old format

### Risk 3: Advanced Key Complexity
- **Mitigation:** Implement one type at a time, thorough testing
- **Fallback:** Ship with subset of advanced keys, add later

### Risk 4: EEPROM Wear
- **Mitigation:** Implement wear leveling, limit save frequency
- **Fallback:** Use default values, warn user

### Risk 5: User Adoption
- **Mitigation:** Clear documentation, migration wizard, video tutorials
- **Fallback:** Support old system in parallel for transition period

---

## NOTES

### Differences from libhmk:

1. **Keep orthomidi's 8-threshold DKS:** More expressive than libhmk's 2-zone DKS
2. **Keep MIDI system:** libhmk doesn't have MIDI, we do
3. **Keep layer system:** libhmk uses profiles, we use QMK layers
4. **Add layer overrides (optional):** libhmk is per-key only, we might want per-layer

### Advantages of this overhaul:

1. **CPU efficiency:** EMA + RT state machine = consistent ~70 cycles/key
2. **Noise immunity:** Built-in filtering eliminates false triggers
3. **Auto-calibration:** No manual calibration needed, handles drift
4. **Unified system:** Everything in one coherent architecture
5. **Memory savings:** -6,020 bytes vs current per-key system
6. **Better RT:** Always available, continuous mode, more responsive

### Challenges:

1. **Large refactor:** Touches core matrix scanning, risky
2. **Migration complexity:** Converting existing configs
3. **GUI work:** Significant UI development needed
4. **Testing burden:** Many edge cases to cover
5. **Documentation:** Comprehensive docs required

---

## CONCLUSION

This overhaul replaces the current matrix scanning system with libhmk's superior architecture while maintaining orthomidi's expressive features (8-threshold DKS, MIDI, layers). The result will be a more efficient, robust, and user-friendly analog keyboard firmware.

**Recommended approach:** Implement in phases, test thoroughly at each stage, maintain backward compatibility during transition, provide comprehensive migration tools.

**Expected outcome:** Faster scanning, better noise immunity, automatic calibration, unified configuration, happier users.

**Next steps:** Review this plan, approve phases, begin Week 1 implementation.
