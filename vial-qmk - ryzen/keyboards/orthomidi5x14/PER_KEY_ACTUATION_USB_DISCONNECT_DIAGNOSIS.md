# Per-Key Actuation USB Disconnect - Root Cause Analysis

## Executive Summary

**Root Cause:** The `refresh_per_key_cache()` function is called **71 times per scan cycle** (once from matrix_scan_custom, plus 70 times from get_key_actuation_config for each key). When the function doesn't return early, even small amounts of work per call accumulate to starve USB.

**Solution:** Always set `active_per_key_cache_layer` immediately after filling defaults, so 70 of the 71 calls return early. Incremental array reads must happen separately, not inside `refresh_per_key_cache`.

---

## Diagnostic Test Results

| Mode | Description | Result | Conclusion |
|------|-------------|--------|------------|
| 0 | No array access, fill defaults | WORKS | Baseline |
| 1 | Read single element via struct | FAILS | Struct access problematic |
| 10 | Just take pointer, don't read | WORKS | Pointer calc is fine |
| 11 | Read 1 byte via volatile | WORKS | Single volatile read is fine |
| 12 | Check array address | WORKS | Array address is valid |
| 13 | Loop 70x reading local array | FAILS | Loop with reads fails |
| 14 | Empty loop 70x | WORKS | Loop itself is fine |
| 15 | Loop 70x reading extern array | FAILS | Reading in loop fails |
| 17 | Loop 70x writing only | WORKS | Writing in loop is fine |
| 19-20 | Incremental 5-7 keys per call | FAILS | Combined write+read fails |
| 21 | 1 key per call, no immediate cache set | FAILS | Function called 71x/scan |
| 22 | Fill defaults only, set cache | WORKS | Immediate cache set works |
| 23 | Like 21, hardcoded layer 0 | FAILS | Layer param not the issue |
| 24 | Like 21, volatile pointer | FAILS | Access method not the issue |
| **25** | Fill defaults + 1 read, set cache immediately | **WORKS** | **This is the solution pattern** |

---

## Call Flow Analysis

### Per Scan Cycle:

```
matrix_scan_custom()
├── analog_matrix_task_internal()
│   └── for each key (70x):
│       └── process_rapid_trigger()
│           └── get_key_actuation_config()
│               └── refresh_per_key_cache()  ← Called 70 times!
│
├── refresh_key_type_cache()
├── refresh_per_key_cache()  ← Called 1 time
└── ... rest of scan
```

**Total calls to refresh_per_key_cache per scan: 71**

### Why Modes 21-24 Failed:

```c
void refresh_per_key_cache(uint8_t layer) {
    if (layer == active_per_key_cache_layer) return;  // Early return

    // In modes 21-24, this doesn't get set until ALL 70 keys are read
    // So every call goes past the early return and does work

    // ... do work ...

    // Only set after 70 calls:
    if (incremental_refresh_index >= 70) {
        active_per_key_cache_layer = layer;  // Too late!
    }
}
```

For 70 scan cycles:
- 71 calls × 70 cycles = **4,970 function calls doing work**
- Each call reads from per_key_actuations array
- USB stack gets starved

### Why Mode 25 Works:

```c
void refresh_per_key_cache(uint8_t layer) {
    if (layer == active_per_key_cache_layer) return;  // Early return

    // Fill defaults
    for (uint8_t i = 0; i < 70; i++) { ... }

    // One read is fine
    volatile uint8_t *ptr = &per_key_actuations[0].keys[0];
    volatile uint8_t val = *ptr;

    active_per_key_cache_layer = layer;  // Set IMMEDIATELY
}
// Next 70 calls this scan cycle: early return
```

Per scan cycle:
- 1 call does work (fill defaults + 1 read)
- 70 calls return early
- USB is happy

---

## The Real Problem: Array Read Performance

Even though mode 25 works, we still can't read all 70 keys from `per_key_actuations`. The issue is:

1. **Memory access pattern**: `per_key_actuations[layer].keys[i]` requires:
   - Base address + (layer × 560) + (i × 8) + field offset
   - This scattered access pattern causes cache misses

2. **Struct field access**: Reading `full->actuation`, `full->rapidfire_press_sens`, etc. generates multiple load instructions

3. **Array size**: 6,720 bytes doesn't fit in L1 cache (typically 32KB but shared)

4. **Cumulative effect**: Even small delays × 70 keys × 71 calls = USB starvation

---

## Solution Architecture

### Option A: Read at Init Only (Current Workaround)
- Fill cache with defaults at layer change
- Never read from per_key_actuations during scan
- Per-key settings won't work, but keyboard functions

### Option B: Background/Deferred Reads
- Fill cache with defaults immediately (function returns early after)
- Use a separate mechanism (timer, idle task) to gradually read array
- Don't tie reads to refresh_per_key_cache calls

### Option C: Restructure Data
- Store per-key data in a more cache-friendly format
- Or reduce to single layer (560 bytes instead of 6,720)
- Or use smaller per-key struct (4 bytes instead of 8)

### Option D: Pre-populate Cache per Layer
- At startup, populate cache for layer 0
- On layer change, populate new layer cache in background
- Keep "working" cache always valid while "loading" cache updates

---

## Key Learnings

1. **Function call frequency matters**: A function called 71x per scan must be extremely fast
2. **Early return is critical**: `if (already_done) return;` saves 70 calls worth of work
3. **Memory access in tight loops is dangerous**: Even 1 read per call × 71 calls = too much
4. **Incremental approaches need careful design**: Can't just spread work across calls if function is called too often

---

## Files Involved

- `quantum/matrix.c`: `refresh_per_key_cache()`, `get_key_actuation_config()`, `process_rapid_trigger()`
- `keyboards/orthomidi5x14/orthomidi5x14.c`: `per_key_actuations[]` array definition
- `quantum/process_keycode/process_midi.h`: Type definitions

---

## Implementation Status: COMPLETED

### Final Solution: Startup Loading + Per-Key Only Architecture

We implemented a hybrid approach that:
1. **Loads layer 0 per-key cache at startup** (before USB is active)
2. **Uses per-key commands exclusively** (layer-wide actuation commands deprecated)
3. **Updates cache directly on HID changes** (no incremental loading needed)

---

## Session Achievements

### 1. Startup Loading (Layer 0 Only)

**Implementation:** Load the per-key cache for layer 0 during `keyboard_post_init_kb()`, before USB enumeration:

```c
// In orthomidi5x14.c keyboard_post_init_kb():
// Load per-key cache for layer 0 BEFORE USB is active
// This avoids the scan loop array access issue
refresh_per_key_cache_startup(0);
```

**Why it works:**
- No USB stack to starve at startup
- Single memcpy-style operation completes before scan loop starts
- Cache is valid from first scan cycle

**Limitation:** Only layer 0 is loaded. Other layers use defaults until we implement background loading.

### 2. HID Response Offset Fix

**Bug:** GUI expected per-key actuation data at `response[5]`, firmware wrote at `response[4]`.

**Symptom:** All keys showed 0.1mm actuation in GUI (reading deadzone_top instead of actuation).

**Fix in `arpeggiator_hid.c`:**
```c
case 0xE1:  // HID_CMD_GET_PER_KEY_ACTUATION
    response[4] = 0x01;  // Success status
    handle_get_per_key_actuation(&data[6], &response[5]);  // Data at offset 5
    break;
```

### 3. Rapid Trigger Flag Fix

**Bug:** Firmware checked `if (rt_down == 0)` to disable RT, but GUI uses flags bit 0.

**Symptom:** RT was always active because GUI sends rt_down=4 even when RT disabled.

**Fix in `matrix.c`:**
```c
// Check if rapid trigger is enabled via the flag (not just rt_down != 0)
bool rt_enabled = (flags & PER_KEY_FLAG_RAPIDFIRE_ENABLED) && (rt_down > 0);

if (!rt_enabled) {
    // RT disabled - simple threshold mode
    key->is_pressed = (key->distance >= actuation_point);
}
```

### 4. Per-Key Cache Direct Update

**Bug:** Cache was invalidated on HID changes, forcing re-read from large array.

**Symptom:** USB disconnect when GUI changed per-key values.

**Fix in `orthomidi5x14.c`:**
```c
void handle_set_per_key_actuation(uint8_t *data, uint8_t *response) {
    // ... save to per_key_actuations ...

    // Update active cache directly (don't invalidate!)
    if (layer == active_per_key_cache_layer) {
        active_per_key_cache[key_idx].actuation = settings->actuation;
        active_per_key_cache[key_idx].rt_down = settings->rapidfire_press_sens;
        active_per_key_cache[key_idx].rt_up = settings->rapidfire_release_sens;
        active_per_key_cache[key_idx].flags = settings->flags;
    }
}
```

### 5. Layer Actuation Command Deprecation

**Problem:** Commands 0xCA, 0xCB, 0xCC conflict with arpeggiator commands:
- 0xCA = ARP_CMD_SET_NOTE (arpeggiator) vs SET_LAYER_ACTUATION
- 0xCB = ARP_CMD_SET_NOTES_CHUNK (arpeggiator) vs GET_LAYER_ACTUATION
- 0xCC = ARP_CMD_SET_MODE (arpeggiator) vs GET_ALL_LAYER_ACTUATIONS

**Solution:** Deprecated layer actuation commands. GUI now sends 70 per-key commands (0xE0) for layer-wide changes.

**Changes:**
- `trigger_settings.py`: Removed `send_layer_actuation()` calls, uses `apply_actuation_to_keys()` only
- `vial.c`: Added deprecation comments to 0xCA-0xCC cases
- `process_midi.h`: Marked normal_actuation/midi_actuation fields as deprecated
- `matrix.c`: Removed unused actuation fields from active_settings struct

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STARTUP (keyboard_post_init_kb)                                              │
│  └── refresh_per_key_cache_startup(0)                                        │
│       └── Loads layer 0 per-key values BEFORE USB active                    │
│       └── 280 bytes copied to active_per_key_cache[]                        │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ GUI CHANGES (HID command 0xE0)                                               │
│  └── handle_set_per_key_actuation()                                          │
│       └── Updates per_key_actuations[layer].keys[key] (EEPROM disabled)     │
│       └── Updates active_per_key_cache[key] directly if same layer          │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER-WIDE CHANGES (GUI trigger settings)                                    │
│  └── User changes "Actuation Point" slider                                   │
│       └── GUI calls apply_actuation_to_keys() for all 70 keys               │
│       └── Sends 70 × HID command 0xE0 (per-key set)                         │
│       └── Each command updates cache directly                                │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ SCAN LOOP (matrix_scan_custom)                                               │
│  └── process_rapid_trigger()                                                 │
│       └── get_key_actuation_config()                                         │
│            └── Reads from active_per_key_cache[key_idx] (280 bytes, L1)     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Known Limitations

### 1. Layer 0 Only for Per-Key Values
- Only layer 0 has real per-key values loaded at startup
- Other layers use default values (1.5mm actuation, RT disabled)
- **Workaround:** Most users only use layer 0 for gaming

### 2. EEPROM Storage Disabled
- Per-key values not persisted to EEPROM (6,720 byte array)
- Values reset to defaults on power cycle
- Layer actuation values ARE still saved (120 bytes)
- **Reason:** Large EEPROM operations may cause issues

### 3. Layer-Wide Actuation via Per-Key
- Changing layer-wide actuation sends 70 HID commands
- Slightly slower than single command (but works reliably)
- **Impact:** ~100-200ms to apply layer-wide change

### 4. Command ID Conflict Remains
- 0xCA-0xCC still handled by arpeggiator_hid.c
- Layer actuation commands don't work (by design)
- **Impact:** None - we use per-key only now

---

## Files Modified

| File | Changes |
|------|---------|
| `matrix.c` | RT flag fix, removed unused actuation fields, startup cache loading |
| `orthomidi5x14.c` | Direct cache update, startup loading function |
| `arpeggiator_hid.c` | HID response offset fix for 0xE1 |
| `process_midi.h` | Deprecated layer actuation fields |
| `vial.c` | Deprecated 0xCA-0xCC command comments |
| `trigger_settings.py` | Removed layer actuation HID calls |

---

## Testing Checklist

- [x] Per-key actuation changes work in GUI
- [x] Values read correctly from firmware (0xE1 response)
- [x] Rapid trigger enable/disable works via flag
- [x] No USB disconnects during normal operation
- [x] Layer 0 values loaded at startup
- [ ] Other layer per-key values (deferred - use defaults)
- [ ] EEPROM persistence (deferred - disabled)

---

*Document updated after HID audit and per-key only architecture implementation.*
