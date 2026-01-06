# libhmk vs orthomidi5x14 Implementation Comparison
## Focus: Matrix Scanning Efficiency & DKS Implementation

---

## Executive Summary

This document compares the implementation approaches between **peppapighs/libhmk** and **orthomidi5x14 firmware**, focusing on:
1. Generic matrix scanning algorithms and efficiency
2. DKS (Dynamic Keystroke) implementation architecture
3. Data structures and memory footprint
4. Algorithmic performance characteristics

---

## 1. MATRIX SCANNING: ARCHITECTURAL COMPARISON

### orthomidi5x14 Approach

**File:** `quantum/matrix.c` (integrated with QMK)

#### Scanning Strategy:
```c
matrix_scan_custom() {
    analog_matrix_task_internal()  // Read all ADCs
    ├─ For each key:
    │   ├─ Read analog travel (0-100 normalized)
    │   ├─ Get actuation point (per-key OR layer-wide)
    │   └─ Compare: travel > actuation → pressed/released
    │
    ├─ Process MIDI keys (velocity calculation)
    └─ Process DKS keys (if keycode in 0xED00-0xED31 range)
}
```

#### Key Characteristics:
- **Dual-mode actuation system**: Uses `get_key_actuation_point()` to switch between:
  - Layer-wide: `layer_actuations[layer].midi_actuation` (simple lookup)
  - Per-key: `per_key_actuations[layer].keys[key_index].actuation` (indexed array)
- **No filtering**: Raw ADC values directly compared to thresholds
- **Post-processing pipeline**: MIDI → DKS → Matrix generation
- **QMK integration**: Hooks into QMK's matrix API, maintains compatibility

#### Data Structure (Per-Key Actuation):
```c
typedef struct {
    uint8_t actuation;              // 1 byte
    uint8_t deadzone_top;           // 1 byte
    uint8_t deadzone_bottom;        // 1 byte
    uint8_t velocity_curve;         // 1 byte
    uint8_t flags;                  // 1 byte
    uint8_t rapidfire_press_sens;   // 1 byte
    uint8_t rapidfire_release_sens; // 1 byte
    int8_t  rapidfire_velocity_mod; // 1 byte
} per_key_actuation_t;  // 8 bytes × 70 keys = 560 bytes per layer
```

**Total Memory (12 layers):** 6,720 bytes for per-key mode

---

### libhmk Approach

**File:** `src/matrix.c`

#### Scanning Strategy:
```c
matrix_scan() {
    for each key:
        ├─ Read analog value (matrix_analog_read)
        ├─ Apply EMA filter: filtered = EMA(current, previous)
        ├─ Calculate distance: normalize(filtered, rest, bottom_out)
        ├─ State machine:
        │   ├─ Update extremum (peak detection)
        │   ├─ Check rapid trigger thresholds
        │   └─ Determine press/release state
        └─ Update key_matrix[key].is_pressed
}
```

#### Key Characteristics:
- **Exponential Moving Average (EMA)**: Built-in noise filtering
  - Formula: `filtered = (filtered * (2^alpha - 1) + current) >> alpha`
  - Alpha exponent = 4 (configurable)
- **Automatic calibration**: Learns rest/bottom-out values during idle periods
- **Rapid Trigger built-in**: Matrix-level implementation (not per-key feature)
- **State machine**: Tracks `KEY_DIR_INACTIVE`, `KEY_DIR_DOWN`, `KEY_DIR_UP`
- **Single-pass processing**: All logic in one loop

#### Data Structure:
```c
typedef struct {
    uint16_t adc_filtered;          // 2 bytes
    uint16_t adc_rest_value;        // 2 bytes
    uint16_t adc_bottom_out_value;  // 2 bytes
    uint8_t  distance;              // 1 byte
    uint8_t  extremum;              // 1 byte (peak detection)
    uint8_t  key_dir;               // 1 byte (enum: inactive/down/up)
    bool     is_pressed;            // 1 byte
} key_state_t;  // 10 bytes per key
```

**Total Memory:** 10 bytes × NUM_KEYS (e.g., 700 bytes for 70 keys)

---

## 2. MATRIX SCANNING EFFICIENCY ANALYSIS

### Computational Complexity

| Aspect | orthomidi5x14 | libhmk |
|--------|---------------|--------|
| **Per-key operations** | O(1) lookup + compare | O(1) EMA + normalize + state logic |
| **Filtering** | None (raw ADC) | EMA every scan |
| **Calibration** | Manual/static | Automatic (periodic) |
| **Rapid Trigger** | Per-key feature (separate check) | Built into matrix (continuous extremum tracking) |
| **Pipeline stages** | 3 (ADC → Actuation → Post-process) | 1 (unified scan) |

### Memory Efficiency

| Implementation | Per-Key Memory | 70 Keys | 12 Layers (orthomidi) |
|----------------|----------------|---------|------------------------|
| **orthomidi (non per-key)** | 0 bytes | 0 bytes | ~100 bytes (layer-wide) |
| **orthomidi (per-key)** | 8 bytes | 560 bytes | 6,720 bytes |
| **libhmk** | 10 bytes | 700 bytes | 700 bytes (no layer concept) |

**Winner:** libhmk uses consistent memory (700 bytes) regardless of layer count. orthomidi per-key mode scales with layers (12× multiplier).

### Algorithmic Efficiency

#### orthomidi:
```c
// Best case (non per-key): O(n) scan, simple comparison
for each key:
    actuation = layer_actuations[layer].midi_actuation;  // O(1)
    if (travel > actuation) → pressed;                   // O(1)

// Worst case (per-key + DKS):
for each key:
    actuation = per_key_actuations[layer].keys[idx].actuation;  // O(1) indexed
    if (is_dks_keycode) dks_process_key();                      // O(8) - check 8 thresholds
```

**Complexity:** O(n) where n = number of keys, with constant factors for DKS keys

#### libhmk:
```c
for each key:
    // EMA filtering
    filtered = (filtered * 15 + current) >> 4;           // O(1) bitshift multiply

    // Distance calculation
    distance = normalize(filtered, rest, bottom_out);    // O(1) arithmetic

    // Rapid trigger state machine
    if (going_down && distance > extremum) extremum = distance;  // O(1)
    if (going_up && extremum - distance > rt_up) release();      // O(1)
```

**Complexity:** O(n) with consistent overhead per key (no branches for special keys)

### CPU Cycle Estimates (per key)

| Operation | orthomidi (simple) | orthomidi (per-key+DKS) | libhmk |
|-----------|-------------------|-------------------------|--------|
| **ADC Read** | ~10 cycles | ~10 cycles | ~10 cycles |
| **Actuation lookup** | ~5 cycles | ~15 cycles (indexed) | N/A |
| **Filtering** | 0 | 0 | ~20 cycles (bitshift EMA) |
| **Distance calc** | 0 | 0 | ~15 cycles (normalize) |
| **State logic** | ~5 cycles | ~10 cycles | ~25 cycles (state machine) |
| **DKS check** | 0 | ~80 cycles (if DKS key) | N/A |
| **Total (typical)** | ~20 cycles | ~35 cycles (no DKS), ~115 (DKS) | ~70 cycles |

**Analysis:**
- **orthomidi (non per-key):** Fastest for simple use cases
- **libhmk:** Consistent overhead, built-in filtering makes it robust against noise
- **orthomidi (DKS keys):** Higher overhead when DKS keys are present

---

## 3. DKS IMPLEMENTATION COMPARISON

### orthomidi5x14 DKS

**File:** `quantum/process_keycode/process_dks.c`

#### Architecture:
```
Keycode Assignment → DKS Slot (0-49)
                      ↓
Each slot: 32 bytes (4 press + 4 release actions)
├─ press_keycode[4]         (8 bytes)
├─ press_actuation[4]       (4 bytes)
├─ release_keycode[4]       (8 bytes)
├─ release_actuation[4]     (4 bytes)
├─ behaviors (bit-packed)   (2 bytes)
└─ reserved                 (6 bytes)
```

#### Processing Flow:
1. **Detection:** Check if keycode ∈ [0xED00, 0xED31] during matrix scan
2. **Slot lookup:** `slot_num = keycode - 0xED00`
3. **Direction detection:** Compare `travel` vs `last_travel`
4. **Threshold crossing:**
   ```c
   // Press actions (downstroke)
   if (last_travel < threshold && travel >= threshold)
       trigger_action(press_keycode[i], behavior);

   // Release actions (upstroke)
   if (last_travel > threshold && travel <= threshold)
       trigger_action(release_keycode[i], behavior);
   ```
5. **Behavior execution:**
   - `TAP`: `tap_code16()` - instant press+release
   - `PRESS`: `register_code16()` - hold until release
   - `RELEASE`: `unregister_code16()` - release only

#### State Tracking (per physical key):
```c
typedef struct {
    uint8_t  dks_slot;              // 1 byte
    uint8_t  last_travel;           // 1 byte
    uint8_t  press_triggered;       // 1 byte (bitmask)
    uint8_t  release_triggered;     // 1 byte (bitmask)
    uint16_t active_keycodes;       // 2 bytes (bitmask)
    bool     is_dks_key;            // 1 byte
    bool     key_was_down;          // 1 byte
} dks_state_t;  // 8 bytes per key
```

**Memory:** 8 bytes × MATRIX_ROWS × MATRIX_COLS + (32 bytes × 50 slots) = ~1,960 bytes (70 keys)

#### Key Features:
- ✓ 8 actions per key (4 press + 4 release)
- ✓ Directional awareness (upstroke vs downstroke)
- ✓ 3 behaviors (TAP, PRESS, RELEASE)
- ✓ Hysteresis (actions don't re-trigger until full release)
- ✓ EEPROM persistence
- ✓ 50 independent slots (shareable across keys)

---

### libhmk DKS

**File:** `src/advanced_keys.c` (function: `advanced_key_dynamic_keystroke`)

#### Architecture:
```
Dynamic Keystroke Config:
├─ keycodes[4]              (8 bytes) - 4 keycode slots
├─ bitmap[4]                (4 bytes) - action encoding (2 bits × 4 events × 4 slots)
└─ bottom_out_point         (1 byte)
Total: ~13 bytes per DKS key
```

#### Action Encoding (Bitmap):
```c
// Each keycode slot has 2 bits per event type (4 events = 8 bits)
uint8_t action = (dks->bitmap[i] >> ((event_type - AK_EVENT_TYPE_PRESS) * 2)) & 3;

// Event types:
0: HOLD (unused in DKS)
1: PRESS (on actuation)
2: BOTTOM_OUT (on full travel)
3: RELEASE_FROM_BOTTOM_OUT (on upstroke from bottom)
4: RELEASE (on full release)
```

#### Processing Flow:
1. **Event generation:** Matrix determines event type based on travel distance
2. **Slot iteration:** Check all 4 keycode slots
3. **Action decode:** Extract 2-bit action from bitmap
4. **Deferred execution:** Queue action via `deferred_action_push()`
5. **Actions:**
   - `DKS_ACTION_NONE = 0` - No action
   - `DKS_ACTION_PRESS = 1` - Press keycode
   - `DKS_ACTION_TAP = 2` - Tap keycode
   - `DKS_ACTION_HOLD = 3` - Hold keycode

#### State Tracking:
```c
typedef struct {
    bool is_pressed[4];         // 4 bytes (one per keycode slot)
    bool is_bottomed_out;       // 1 byte
} ak_state_dynamic_keystroke_t;  // 5 bytes
```

**Memory:** ~13 bytes config + 5 bytes state = **18 bytes per DKS key**

#### Key Features:
- ✓ 4 keycode slots (vs 8 in orthomidi)
- ✓ 4 event types (PRESS, BOTTOM_OUT, RELEASE_FROM_BOTTOM_OUT, RELEASE)
- ✓ Compact bitmap encoding (2 bits per action)
- ✓ Deferred action queue (prevents race conditions)
- ✗ No custom thresholds per action (fixed: actuation point, bottom-out point)
- ✗ Only 2 physical travel zones (actuation, bottom-out) vs 8 in orthomidi

---

## 4. DKS COMPARISON TABLE

| Feature | orthomidi5x14 | libhmk |
|---------|---------------|--------|
| **Actions per key** | 8 (4 press + 4 release) | 4 keycode slots × 4 events = 16 (but same keycode) |
| **Unique thresholds** | 8 (each action has custom travel point) | 2 (actuation + bottom-out) |
| **Behaviors** | TAP, PRESS, RELEASE | NONE, PRESS, TAP, HOLD |
| **Direction awareness** | Explicit (press vs release arrays) | Implicit (event type determined by matrix) |
| **Hysteresis** | Manual (reset on full release) | Automatic (bottom-out flag) |
| **Memory per slot** | 32 bytes | ~13 bytes config |
| **State per key** | 8 bytes | 5 bytes |
| **Slot reuse** | Yes (50 shared slots) | No (per-key config) |
| **Threshold precision** | 0-100 (0-2.5mm) per action | 2 fixed points only |
| **Encoding efficiency** | Direct (8 keycodes stored) | Bitmap (2 bits per action) |
| **EEPROM storage** | 1,604 bytes (50 × 32 + header) | ~13 bytes per DKS key |

### Winner by Category:

| Category | Winner | Reasoning |
|----------|--------|-----------|
| **Flexibility** | **orthomidi** | 8 custom thresholds vs 2 fixed points |
| **Memory efficiency** | **libhmk** | 13 bytes vs 32 bytes per slot |
| **Granularity** | **orthomidi** | Each action at any travel depth |
| **Slot management** | **orthomidi** | 50 shared slots, reusable |
| **Ease of implementation** | **libhmk** | Simpler 4-event model |
| **Expression** | **orthomidi** | More zones = more musical/gaming potential |

---

## 5. ALGORITHMIC EFFICIENCY: DKS PROCESSING

### orthomidi DKS Processing

```c
void dks_process_key(row, col, travel, keycode) {
    slot = &dks_slots[keycode - 0xED00];
    state = &dks_states[row][col];

    // Direction determination
    going_down = (travel > last_travel);
    going_up = (travel < last_travel);

    if (going_down) {
        // Check 4 press thresholds
        for (i = 0; i < 4; i++) {
            if (!triggered[i] && crossed_threshold(i)) {
                trigger_action(slot->press_keycode[i], behavior[i]);
                mark_triggered(i);
            }
        }
    }

    if (going_up) {
        // Check 4 release thresholds
        for (i = 0; i < 4; i++) {
            if (!triggered[i] && crossed_threshold(i)) {
                trigger_action(slot->release_keycode[i], behavior[i]);
                mark_triggered(i);
            }
        }

        // Cleanup PRESS behaviors that dropped below threshold
        cleanup_held_keys();
    }

    // Full release detection
    if (travel < 0.125mm && was_down) {
        reset_all_triggered_flags();
    }
}
```

**Complexity:** O(8) - Always checks 8 thresholds (4 press + 4 release)

**Per-key cost:** ~80-120 cycles (8 comparisons + potential actions)

---

### libhmk DKS Processing

```c
void advanced_key_dynamic_keystroke(event, dks, state) {
    // Event already determined by matrix (PRESS, BOTTOM_OUT, etc.)

    // Check 4 keycode slots
    for (i = 0; i < 4; i++) {
        if (dks->keycodes[i] == 0) continue;

        // Decode action from bitmap (2-bit lookup)
        action = (dks->bitmap[i] >> ((event->type - 1) * 2)) & 3;

        switch (action) {
            case DKS_ACTION_PRESS:
                deferred_action_push(event->key, dks->keycodes[i], PRESS);
                state->is_pressed[i] = true;
                break;
            case DKS_ACTION_TAP:
                deferred_action_push(event->key, dks->keycodes[i], TAP);
                break;
            case DKS_ACTION_HOLD:
                deferred_action_push(event->key, dks->keycodes[i], HOLD);
                break;
        }
    }
}
```

**Complexity:** O(4) - Only checks 4 keycode slots

**Per-key cost:** ~40-60 cycles (4 iterations, bitshift decode, queue push)

---

## 6. RAPID TRIGGER COMPARISON

### orthomidi: Per-Key Rapidfire

**Implementation:** Part of per-key actuation system (separate from matrix)

```c
per_key_actuation_t {
    uint8_t rapidfire_press_sens;    // Custom threshold per key
    uint8_t rapidfire_release_sens;  // Custom threshold per key
    uint8_t flags;                   // Bit 0: rapidfire_enabled
}
```

- ✓ Per-key enable/disable
- ✓ Independent press/release sensitivity
- ✗ Requires per-key mode (6,720 bytes)
- ✗ Not integrated with DKS keys

---

### libhmk: Built-in Rapid Trigger

**Implementation:** Integrated into matrix scanning (part of state machine)

```c
key_state_t {
    uint8_t extremum;  // Peak detection for RT
    uint8_t key_dir;   // Direction tracking
}

// In matrix_scan():
if (key_dir == DOWN) {
    if (distance > extremum) extremum = distance;  // Track peak
    if (distance + rt_up < extremum) release();    // Trigger on upward motion
}
if (key_dir == UP) {
    if (distance < extremum) extremum = distance;
    if (extremum + rt_down < distance) press();    // Re-trigger on downward motion
}
```

- ✓ Built into matrix (no extra memory per key)
- ✓ Continuous mode (no reset point)
- ✓ Works with all keys automatically
- ✗ Global RT thresholds (not per-key)
- ✗ Bitmap for per-key disable (adds overhead)

**Winner:** libhmk - more efficient, always available, less memory

---

## 7. CALIBRATION & NOISE HANDLING

### orthomidi:
- **Filtering:** None (raw ADC values)
- **Calibration:** Static/manual (stored in EEPROM)
- **Noise immunity:** Relies on deadzones (per-key mode)
- **Drift compensation:** Manual recalibration needed

### libhmk:
- **Filtering:** EMA with configurable alpha (default: 4)
- **Calibration:** Automatic during 500ms idle periods
- **Noise immunity:** EMA smoothing + epsilon threshold (5 ADC units)
- **Drift compensation:** Continuous learning of rest/bottom-out values

**Winner:** libhmk - automatic calibration and noise filtering are superior for real-world use

---

## 8. OVERALL EFFICIENCY SUMMARY

### Matrix Scanning:

| Metric | orthomidi (non per-key) | orthomidi (per-key) | libhmk |
|--------|-------------------------|---------------------|--------|
| **Memory** | ~100 bytes | 6,720 bytes | 700 bytes |
| **CPU per key** | ~20 cycles | ~35 cycles | ~70 cycles |
| **Filtering** | ❌ None | ❌ None | ✅ EMA |
| **Calibration** | ❌ Manual | ❌ Manual | ✅ Automatic |
| **Rapid Trigger** | ❌ No (or per-key add-on) | ✅ Per-key | ✅ Built-in |

**Trade-off:**
- **orthomidi non per-key:** Fastest but least flexible
- **orthomidi per-key:** Most flexible but highest memory cost
- **libhmk:** Balanced - consistent overhead, robust filtering, moderate memory

---

### DKS Implementation:

| Metric | orthomidi | libhmk |
|--------|-----------|--------|
| **Flexibility** | 8 custom thresholds | 2 fixed thresholds |
| **Memory per key** | 8 bytes state | 5 bytes state |
| **Memory per config** | 32 bytes (shared slots) | 13 bytes (per-key) |
| **Processing cost** | O(8) checks | O(4) checks |
| **Expressiveness** | High (8 zones) | Medium (4 slots × 2 zones) |

**Trade-off:**
- **orthomidi:** More expressive, better for musical/gaming applications with many zones
- **libhmk:** More memory efficient per key, simpler to configure

---

## 9. ARCHITECTURAL PHILOSOPHY

### orthomidi5x14:
- **Layered approach:** Modular (per-key actuation, DKS, MIDI all separate)
- **QMK compatibility:** Maintains QMK's API structure
- **Memory vs flexibility:** Willing to use more memory for per-key customization
- **Feature-rich:** Many specialized systems (per-key actuation, DKS, rapidfire, velocity curves)

### libhmk:
- **Unified approach:** Matrix handles filtering, calibration, rapid trigger in one pass
- **Memory conscious:** Compact data structures, no layer duplication
- **Robust defaults:** Automatic calibration and filtering built-in
- **Simpler model:** Fewer configuration options, but more consistent behavior

---

## 10. CONCLUSION

### Generic Matrix Scanning Winner: **libhmk**

**Reasons:**
1. Built-in EMA filtering for noise immunity
2. Automatic calibration reduces user burden
3. Rapid trigger integrated into matrix (no extra overhead)
4. Consistent memory usage (700 bytes vs 6,720 bytes for orthomidi per-key)
5. Better for real-world conditions (temperature drift, noise)

**Caveat:** orthomidi's non per-key mode is faster (~20 vs ~70 cycles), but lacks robustness

---

### DKS Implementation Winner: **orthomidi5x14**

**Reasons:**
1. 8 custom thresholds vs 2 fixed zones (4× more granular)
2. Directional awareness (separate press/release arrays)
3. 3 behaviors (TAP, PRESS, RELEASE) with better control
4. Shared slot system (50 slots, reusable) saves memory for multiple DKS keys
5. Better for expressive applications (music, gaming) where travel zones matter

**Caveat:** libhmk uses less memory per key (18 vs 40 bytes) if you have many DKS keys

---

### Overall Implementation Quality:

**libhmk:**
- More elegant, unified architecture
- Better engineering for real-world conditions
- Lower cognitive overhead (fewer config options)
- Production-ready defaults

**orthomidi5x14:**
- More powerful customization (per-key everything)
- Better for power users and enthusiasts
- Modular design allows feature selection
- Superior DKS expressiveness

---

## 11. RECOMMENDATIONS

### If you prioritize:
- **Efficiency & robustness:** Use libhmk's matrix approach (EMA, auto-cal, built-in RT)
- **Flexibility & expression:** Use orthomidi's per-key and DKS systems
- **Memory constraints:** libhmk (700 bytes vs 6,720 bytes)
- **Musical/gaming expressiveness:** orthomidi DKS (8 zones vs 2)
- **Ease of use:** libhmk (automatic everything)
- **Power user features:** orthomidi (more knobs to turn)

### Hybrid Recommendation:
Combine the best of both:
1. Use **libhmk's matrix scanning** (EMA, auto-calibration, built-in RT)
2. Implement **orthomidi's DKS system** (8 thresholds, directional actions)
3. Keep **libhmk's memory model** (no layer duplication)
4. Add **orthomidi's per-key actuation** as optional feature (not required)

This would create a maximally efficient, expressive, and robust analog keyboard firmware.
