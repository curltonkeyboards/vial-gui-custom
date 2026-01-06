# Matrix Overhaul: Focused Implementation Plan
## orthomidi5x14 → libhmk Reference Architecture

---

## Overview

This plan focuses on **overhauling the core matrix scanning system** to adopt libhmk's superior architecture while preserving orthomidi's unique features. The goal is to eliminate noise/delays through robust filtering and efficient CPU usage.

---

## Current System Analysis

### What We Have Now

#### 1. **Matrix Scanning** (quantum/matrix.c)
- **ADC Reading:** Raw analog values, no filtering
- **Actuation:** Direct threshold comparison
- **Per-Key Actuation:** Optional 8-byte structure × 70 keys × 12 layers = 6,720 bytes
- **Rapidfire (our current "rapid trigger"):**
  - Part of per-key actuation system
  - Delta-based: compares `current_travel` vs `last_travel`
  - Release when: `last_travel - current_travel >= release_sens`
  - Re-trigger when: `current_travel - last_travel >= press_sens`
  - Requires per-key mode enabled
  - CPU cost: ~10-15 cycles when enabled

#### 2. **Advanced Keys**
- **DKS (Dynamic Keystroke):** 8 thresholds (4 press + 4 release), keycodes 0xED00-0xED31 (50 slots)
- **Tap Dance:** QMK feature, based on tap COUNT (1 tap, 2 taps, etc.) - NOT the same as tap-hold

#### 3. **MIDI System**
- Velocity modes: Fixed, Peak, Speed, Speed+Peak
- Per-key velocity curves (optional)
- Layer-wide settings

---

## Reference Implementation: libhmk

### What libhmk Does Better

#### 1. **Matrix Scanning** (src/matrix.c)
- **EMA Filtering:** `filtered = (current + (previous * 15)) >> 4` - Noise immunity via exponential moving average
- **Auto-Calibration:** Learns rest/bottom-out during 500ms idle periods, tracks drift
- **Distance Normalization:** Converts ADC → 0-255 range based on calibrated rest/bottom values
- **Rapid Trigger State Machine:**
  - **Extremum-based:** Tracks peak (going down) and valley (going up)
  - Built into matrix, always available
  - Release when: `distance + rt_up < extremum` (upward motion from peak)
  - Re-press when: `extremum + rt_down < distance` (downward motion from valley)
  - State: `KEY_DIR_INACTIVE` → `KEY_DIR_DOWN` → `KEY_DIR_UP` → `KEY_DIR_DOWN` (continuous)
  - CPU cost: ~25 cycles (always on, no conditional)

**Key Difference:** libhmk's extremum tracking is more sophisticated than our delta-based rapidfire. It finds actual peaks/valleys, making it more responsive.

#### 2. **Advanced Keys** (src/advanced_keys.c)
- **Null Bind:** Monitor 2 keys, register both when either pressed
- **Dynamic Keystroke:** 4 keycode slots × 4 events (PRESS, BOTTOM_OUT, RELEASE_FROM_BOTTOM_OUT, RELEASE)
  - Note: Only 2 travel zones (actuation, bottom-out) vs our 8 zones
- **Tap-Hold:** Different actions for quick tap vs long hold (time-based, NOT tap count)
- **Toggle:** Toggle key state on tap, normal on hold

**Key Difference:** Their DKS is simpler (2 zones) than ours (8 zones). We should keep our 8-zone DKS for expressiveness.

---

## What We're Overhauling

### ✅ ADOPT FROM LIBHMK:

#### 1. **Core Matrix Data Structure**
**Replace:**
```c
// Current: No unified state
uint16_t raw_adc;
uint8_t travel;  // 0-240 internal units
```

**With:**
```c
// Target: Unified key state (10 bytes per key)
typedef struct {
    uint16_t adc_filtered;          // EMA filtered value
    uint16_t adc_rest_value;        // Calibrated rest
    uint16_t adc_bottom_out_value;  // Calibrated bottom-out
    uint8_t  distance;              // 0-255 normalized
    uint8_t  extremum;              // Peak/valley for RT
    uint8_t  key_dir;               // INACTIVE/DOWN/UP
    bool     is_pressed;            // Current state
} key_state_t;

key_state_t key_matrix[5][14];  // 700 bytes total
```

**Benefit:** Consolidated state, enables filtering/calibration/RT in one structure

---

#### 2. **EMA Filtering**
**Add:**
```c
#define MATRIX_EMA_ALPHA_EXPONENT 4

#define EMA(current, previous) \
    (((uint32_t)(current) + \
      ((uint32_t)(previous) * 15)) >> 4)

// In scan loop:
key->adc_filtered = EMA(raw_adc, key->adc_filtered);
```

**Benefit:** ~20 cycles/key, eliminates ±10 ADC noise automatically

---

#### 3. **Automatic Calibration**
**Add:**
```c
// During 500ms idle periods:
if (idle_for_3s && calibration_active) {
    if (adc_filtered < rest_value - 5) {
        rest_value = adc_filtered;
        bottom_out_value = rest_value + threshold;
    }
}
```

**Benefit:** Handles temperature drift, wear, no manual calibration needed

---

#### 4. **Distance Normalization**
**Replace:**
```c
// Current: Internal 0-240 scale
uint8_t travel = calculate_travel(adc);
```

**With:**
```c
// Target: Normalized 0-255 distance
uint8_t distance = ((adc - rest) * 255) / (bottom - rest);
```

**Benefit:** Consistent range, easier threshold tuning, same scale everywhere

---

#### 5. **Rapid Trigger State Machine (replace our rapidfire)**
**Replace:**
```c
// Current rapidfire (delta-based, per-key feature):
if (last_travel - travel >= release_sens) release();
if (travel - last_travel >= press_sens) re_trigger();
```

**With:**
```c
// Target rapid trigger (extremum-based, built-in):
switch (key_dir) {
    case KEY_DIR_DOWN:
        if (distance > extremum) extremum = distance;  // Track peak
        if (distance + rt_up < extremum) {  // Upward motion
            release();
            key_dir = KEY_DIR_UP;
            extremum = distance;
        }
        break;

    case KEY_DIR_UP:
        if (distance < extremum) extremum = distance;  // Track valley
        if (extremum + rt_down < distance) {  // Downward motion
            re_press();
            key_dir = KEY_DIR_DOWN;
            extremum = distance;
        }
        break;
}
```

**Benefit:**
- More responsive (tracks actual peaks, not just deltas)
- Always available (not per-key feature)
- Continuous mode (no reset point needed)
- Consistent ~25 cycles overhead

---

#### 6. **Advanced Keys from libhmk**
**Add as new keycode ranges (like DKS_00-DKS_49):**

| Feature | Keycode Range | Count | Description |
|---------|---------------|-------|-------------|
| **Null Bind** | NB_00 - NB_49 | 50 | Monitor 2 keys, register both |
| **Tap-Hold** | TH_00 - TH_49 | 50 | Quick tap = kc1, long hold = kc2 |
| **Toggle** | TG_00 - TG_49 | 50 | Tap = toggle, hold = normal |

**Note:** libhmk's "Dynamic Keystroke" is simpler than our DKS (2 zones vs 8), so we'll skip it and keep our superior 8-zone DKS.

**Benefit:** More expressive key behaviors, follows same pattern as DKS (separate keycodes for each slot)

---

### ✅ KEEP FROM ORTHOMIDI:

#### 1. **8-Threshold DKS**
- Current: 4 press + 4 release actions with custom thresholds each
- libhmk: Only 2 zones (actuation, bottom-out)
- **Decision:** Keep our DKS, it's more expressive for music/gaming

#### 2. **Full MIDI System**
- Velocity modes, curves, layer-wide settings
- libhmk doesn't have MIDI
- **Decision:** Keep all MIDI features, update to use `key->distance` instead of raw travel

#### 3. **QMK Layer System**
- We use standard QMK layers
- libhmk uses "profiles"
- **Decision:** Keep QMK layers

---

## Comparison: Rapidfire vs Rapid Trigger

### Current: Rapidfire (Delta-Based)

```c
// State
bool awaiting_release;
uint8_t last_travel;

// Algorithm
if (awaiting_release && last_travel > travel) {
    if (last_travel - travel >= release_sens) {
        awaiting_release = false;  // Released
    }
}
if (!awaiting_release && travel > last_travel) {
    if (travel - last_travel >= press_sens) {
        re_trigger();  // Re-press
        awaiting_release = true;
    }
}
```

**Issues:**
- Compares only current vs previous (1 sample memory)
- Misses peak if travel oscillates
- Part of per-key system (not always available)

---

### Target: Rapid Trigger (Extremum-Based)

```c
// State
uint8_t extremum;   // Peak (going down) or valley (going up)
uint8_t key_dir;    // DOWN or UP

// Algorithm (going down)
if (distance > extremum) extremum = distance;  // Update peak
if (distance + rt_up < extremum) {
    // Moved UP by rt_up units from peak
    release();
    key_dir = UP;
    extremum = distance;  // Reset to current (new valley)
}

// Algorithm (going up)
if (distance < extremum) extremum = distance;  // Update valley
if (extremum + rt_down < distance) {
    // Moved DOWN by rt_down units from valley
    re_press();
    key_dir = DOWN;
    extremum = distance;  // Reset to current (new peak)
}
```

**Advantages:**
- Tracks actual peak/valley (handles oscillation)
- Directional state machine (more robust)
- Built into matrix (always available)
- Continuous mode (re-trigger without full release)

**Example:**
```
Travel: 100 → 150 → 140 → 160 → 130

Delta-based (ours):
  100→150: +50 (maybe trigger)
  150→140: -10 (no release yet)
  140→160: +20 (maybe re-trigger? but didn't fully release)
  160→130: -30 (release?)
  Problem: Missed peak at 150, confused by 140→160 bump

Extremum-based (libhmk):
  100→150: extremum=150 (peak so far)
  150→140: extremum=150, distance+rt_up < 150? If rt_up=10, then 140+10=150, equal (no release)
  140→160: extremum=160 (new peak)
  160→130: 130+10=140 < 160, RELEASE! extremum=130 (valley)
  Clean detection: Peak was 160, released when dropped to 130
```

---

## Comparison: Tap Dance vs Tap-Hold

### QMK Tap Dance (Already Have)

- **Based on:** Tap COUNT
- **Example:**
  - 1 tap → Send 'A'
  - 2 taps → Send 'B'
  - 3 taps → Send 'C'
- **Use case:** Cramming multiple keys onto one physical key via tapping patterns

---

### libhmk Tap-Hold (Want to Add)

- **Based on:** Hold DURATION
- **Example:**
  - Quick tap (<200ms) → Send 'A'
  - Long hold (≥200ms) → Send 'B'
- **Use case:** Dual-role keys (e.g., tap for Esc, hold for Ctrl)

**Decision:** These are DIFFERENT features. We already have Tap Dance. We want to ADD Tap-Hold as separate keycode range (TH_00-TH_49).

---

## Implementation Plan: Concise Version

### Phase 1: Core Matrix (Priority 1)
**Goal:** Replace matrix scanning with libhmk approach

**Tasks:**
1. Add `key_state_t` structure (10 bytes × 70 = 700 bytes)
2. Implement EMA filtering (~20 cycles/key)
3. Implement auto-calibration (idle detection)
4. Implement distance normalization
5. **Replace rapidfire with rapid trigger state machine** (~25 cycles/key)
6. Update MIDI to use `key->distance`

**Outcome:** Robust, filtered matrix scanning with built-in rapid trigger

**CPU Impact:** ~70 cycles/key (consistent, vs current 20-115 variable)

**Memory Impact:** +700 bytes (new state) - 6,720 bytes (remove per-key actuation) = **-6,020 bytes saved**

---

### Phase 2: Advanced Keys (Priority 2)
**Goal:** Add libhmk advanced key types as separate keycode ranges

**Tasks:**
1. Define keycode ranges:
   - `NB_00` - `NB_49` (0xEE00-0xEE31): Null Bind
   - `TH_00` - `TH_49` (0xEF00-0xEF31): Tap-Hold
   - `TG_00` - `TG_49` (0xF000-0xF031): Toggle
2. Implement config structures for each type
3. Implement processing logic
4. Add to matrix scan loop
5. **Keep existing DKS_00-DKS_49** (don't touch, it's better)

**Outcome:** 3 new advanced key types + existing DKS

---

### Phase 3: GUI Integration (Priority 3)
**Goal:** Add configuration tabs without changing existing layout

**Tasks:**
1. **Trigger Settings tab:**
   - Add "Null Bind" sub-tab
   - Add "Tap-Hold" sub-tab
   - Add "Toggle" sub-tab
2. Each sub-tab shows 50 slots (like DKS)
3. Click slot → configure keycodes/settings
4. **Do NOT change existing tabs** (layout is good)

**Outcome:** Full GUI support for new features

---

### Phase 4: Migration (Priority 4)
**Goal:** Convert existing rapidfire configs to rapid trigger

**Tasks:**
1. Migration function: convert rapidfire settings to RT settings
2. HID command to trigger migration
3. Backup/restore functionality
4. Test with existing configs

**Outcome:** Smooth transition for users

---

## Performance Targets

| Metric | Current | Target | Delta |
|--------|---------|--------|-------|
| **CPU per key** | 20 (simple) / 35-115 (per-key+DKS) | ~70 (consistent) | More consistent |
| **Memory** | 100 bytes (simple) / 6,720 (per-key) | 700 bytes | -6,020 bytes |
| **Noise immunity** | ❌ None (raw ADC) | ✅ ±10 ADC units | New feature |
| **Calibration** | ❌ Manual | ✅ Automatic | New feature |
| **Rapid trigger** | ⚠️ Per-key only | ✅ Always on | More available |
| **RT algorithm** | Delta-based | Extremum-based | More responsive |
| **Advanced keys** | 1 type (DKS) | 4 types (DKS + 3 new) | More options |

---

## Key Decisions

### ✅ CONFIRMED:

1. **Adopt libhmk matrix scanning** (EMA, auto-cal, distance, RT state machine)
2. **Replace rapidfire with rapid trigger** (extremum-based, more responsive)
3. **Keep our 8-zone DKS** (more expressive than libhmk's 2-zone)
4. **Add new advanced keys as separate keycodes** (NB_00-49, TH_00-49, TG_00-49)
5. **Keep MIDI system** (update to use filtered values)
6. **Keep QMK layers** (no profiles)
7. **Don't change existing GUI tabs** (only add to Trigger Settings)

### ❓ QUESTIONS:

1. **Per-key rapid trigger disable?**
   - Option A: Global only (simpler)
   - Option B: Add bitmap for per-key disable (like libhmk)
   - **Recommendation:** Option B (libhmk does it, minimal overhead)

2. **Continuous rapid trigger mode?**
   - Option A: Always continuous (no reset point)
   - Option B: Configurable continuous/reset modes
   - **Recommendation:** Option B (more flexible)

3. **Migration timeline?**
   - Option A: Force migration on first update
   - Option B: Support both systems for 1-2 releases
   - **Recommendation:** Option A (clean break, easier maintenance)

---

## File Changes Summary

### New Files:
- `quantum/matrix_libhmk.c` - New matrix scanning implementation
- `quantum/process_keycode/process_null_bind.c/h` - Null bind
- `quantum/process_keycode/process_tap_hold.c/h` - Tap-hold
- `quantum/process_keycode/process_toggle.c/h` - Toggle

### Modified Files:
- `quantum/matrix.c` - Replace scanning logic
- `quantum/process_keycode/process_midi.h` - Remove rapidfire from per_key_actuation_t
- `keyboards/orthomidi5x14/orthomidi5x14.c` - Update MIDI to use key->distance
- `src/main/python/editor/trigger_settings.py` - Add new tabs

### Removed:
- Per-key actuation system (6,720 bytes) - Replaced by key_state_t (700 bytes)
- Rapidfire logic - Replaced by rapid trigger state machine

---

## Timeline

| Phase | Duration | Outcome |
|-------|----------|---------|
| **Phase 1: Core Matrix** | 2-3 weeks | New scanning system working |
| **Phase 2: Advanced Keys** | 1-2 weeks | NB/TH/TG implemented |
| **Phase 3: GUI** | 1-2 weeks | Full configuration UI |
| **Phase 4: Migration** | 1 week | Smooth user transition |
| **Testing** | 1-2 weeks | Validation, bug fixes |
| **Total** | **6-10 weeks** | Release ready |

---

## Success Criteria

- ✅ **No false triggers** with ±10 ADC noise
- ✅ **Auto-calibration** converges in <500ms
- ✅ **Rapid trigger** more responsive than current rapidfire
- ✅ **CPU usage** ≤70 cycles/key (consistent)
- ✅ **Memory usage** ≤1KB total (vs 6.7KB current per-key)
- ✅ **All advanced keys** work reliably
- ✅ **MIDI velocity** ±5% accuracy vs current
- ✅ **Migration** success rate >95%

---

## Next Steps

1. **Review this plan** - Confirm approach, answer questions above
2. **Approve to proceed** - Begin Phase 1 implementation
3. **Set up testing** - Benchmark current system for comparison
4. **Begin coding** - Start with key_state_t structure and EMA

---

## Summary

**What we're doing:** Overhauling matrix scanning to use libhmk's robust architecture (EMA filtering, auto-calibration, extremum-based rapid trigger) while preserving orthomidi's strengths (8-zone DKS, MIDI, layers).

**Why:** Eliminate noise/delays, more responsive rapid trigger, automatic calibration, cleaner architecture.

**Impact:** -6KB memory, ~70 cycles/key (consistent), 3 new advanced key types, better user experience.

**Timeline:** 6-10 weeks to release.

**Risk:** Low - libhmk is proven, we're adopting a reference implementation.
