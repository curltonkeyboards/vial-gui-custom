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

## Next Steps

1. Implement Option B or D for proper per-key actuation support
2. Consider restructuring per_key_actuations for better cache performance
3. Profile actual timing to understand exact USB timing constraints
