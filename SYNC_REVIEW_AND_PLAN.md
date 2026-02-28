# Loop / Arpeggiator / Step Sequencer Sync Review & Implementation Plan

## Table of Contents
1. [System Architecture Overview](#1-system-architecture-overview)
2. [Timing Mechanisms: How Each System Works](#2-timing-mechanisms)
3. [BPM Precision Analysis: The Core Problem](#3-bpm-precision-analysis)
4. [Proximity Threshold Analysis](#4-proximity-threshold-analysis)
5. [Interaction Analysis: Recording a Loop While Arp is Held](#5-interaction-analysis)
6. [Root Cause Summary](#6-root-cause-summary)
7. [Implementation Plan](#7-implementation-plan)

---

## 1. System Architecture Overview

There are three independent timing systems that all need to agree on tempo:

### A. Loop System (`process_dynamic_macro.c`)
- **Timing source**: Hardware TIM5 ISR at 1kHz (1ms resolution) via ChibiOS GPT driver
- **Time base**: `timer_read32()` synced to DWT cycle counter for ISR-safe reads
- **BPM storage**: `uint32_t current_bpm` in format `actual_bpm * 100000` (e.g., 130.47 BPM = 13047000)
- **Loop length**: Stored as `uint32_t` milliseconds with full precision
- **Playback precision**: Events dispatched from ISR with ±0.5ms accuracy
- **Speed adjustment**: `float macro_speed_factor[]` applied to event timestamps

### B. Arpeggiator (`arpeggiator.c`)
- **Timing source**: `timer_read32()` polled from main loop (scan cycle dependent)
- **BPM access**: `extern uint32_t current_bpm` (same global variable)
- **Step timing**: Calculated via `get_ms_per_16th()` — returns `uint32_t` milliseconds
- **Advance method**: `arp_state.next_note_time = current_time + ms_per_16th`
- **Pattern position**: Tracked as `current_position_16ths` (integer counter)

### C. Step Sequencer (`arpeggiator.c`, `seq_update()`)
- **Timing source**: Same `timer_read32()` polled from main loop
- **BPM access**: Same `extern uint32_t current_bpm`
- **Step timing**: Calculated via `seq_get_ms_per_16th()` — same algorithm as arp
- **Advance method**: `seq_state[slot].next_note_time = current_time + ms_per_16th`
- **Pattern position**: `seq_state[slot].current_position_16ths` (integer counter)

---

## 2. Timing Mechanisms: How Each System Works

### 2A. Loop System Timing (HIGH PRECISION)

The loop system has the most sophisticated timing:

1. **Recording**: Events are timestamped with `timer_read32()` relative to `recording_start_time`. Timestamps are stored as absolute millisecond offsets in the `midi_event_t.timestamp` field.

2. **Playback**: The TIM5 ISR fires every 1ms and checks:
   ```c
   // ISR: lt_isr_process_state()
   state->next_event_time = base_time + (uint32_t)(event->timestamp / speed);
   if (now >= state->next_event_time) { /* queue event */ }
   ```

3. **Loop restart**: When the last event is reached, a `loop_gap_time` pause occurs, then the ISR signals `lt_restart_pending[]` and the main loop handles the restart.

4. **BPM calculation** (at record end):
   ```c
   // Assumes 4 beats in the loop
   uint32_t calculated_bpm = (24000000000ULL) / state->loop_length;
   // Halve/double to fit 80-200 BPM range
   ```
   This preserves the full precision of the loop length. A 1846.15ms loop produces BPM = 24000000000 / 1846 = 12997834 = 129.97834 BPM.

5. **Loop quantization**: When `unsynced_mode_active == 1 || 3`, loops are quantized to exact quarter-note multiples:
   ```c
   uint32_t quarter_note_ms = 6000000000ULL / current_bpm;
   float num_quarter_notes = (float)calculated_length / (float)quarter_note_ms;
   uint32_t rounded = (uint32_t)(num_quarter_notes + 0.5f);
   state->loop_length = rounded * quarter_note_ms;
   ```

**KEY INSIGHT**: The loop system works in **absolute millisecond timestamps**. Its precision is limited only by the 1ms ISR tick and the 32-bit millisecond counters.

### 2B. Arpeggiator/Sequencer Timing (LOW PRECISION)

Both `get_ms_per_16th()` and `seq_get_ms_per_16th()` use the same algorithm:

```c
static uint32_t get_ms_per_16th(const arp_preset_t *preset) {
    uint32_t actual_bpm = get_effective_bpm() / 100000;  // <-- TRUNCATION HERE
    if (actual_bpm == 0) actual_bpm = 120;

    uint32_t base_ms = (60000 / actual_bpm) / 4;  // <-- INTEGER DIVISION

    // Apply note value multiplier
    base_ms *= multiplier;  // 1, 2, or 4

    // Apply timing mode
    if (triplet) base_ms = (base_ms * 2) / 3;
    if (dotted)  base_ms = (base_ms * 3) / 2;

    return base_ms;
}
```

**THE CRITICAL BUG IS ON LINE 510/559:**
```c
uint32_t actual_bpm = get_effective_bpm() / 100000;
```

This performs **integer division**, truncating the fractional BPM.

| Actual BPM | `current_bpm` | After `/100000` | Effective BPM | Error |
|-----------|---------------|-----------------|---------------|-------|
| 130.47    | 13047000      | 130             | 130.00        | -0.36% |
| 120.50    | 12050000      | 120             | 120.00        | -0.41% |
| 99.99     | 9999000       | 99              | 99.00         | -0.99% |
| 140.75    | 14075000      | 140             | 140.00        | -0.53% |

Then the `60000 / actual_bpm` division introduces another truncation:

| BPM | 60000/BPM | Actual ms/beat | ms/16th (÷4) | Actual ms/16th | Error/16th |
|-----|-----------|----------------|---------------|----------------|------------|
| 130 | 461       | 461.538...     | 115           | 115.385...     | -0.38ms    |
| 120 | 500       | 500.000        | 125           | 125.000        | 0          |
| 140 | 428       | 428.571...     | 107           | 107.143...     | -0.14ms    |

**Cumulative drift over time**: At 130.47 BPM with sixteenth notes:
- Actual ms per 16th: `60000 / 130.47 / 4 = 114.946ms`
- Computed ms per 16th: `60000 / 130 / 4 = 115ms` (two integer divisions)
- Error per step: `+0.054ms`
- Error per bar (16 steps): `+0.86ms`
- **Error per 4 bars: +3.46ms**
- **Error per 8 bars: +6.92ms**
- **Error per minute (~34 bars at 130 BPM): ~29ms**

This means after just a few bars, arp/seq notes visibly drift from the loop. At 30 seconds the arp is nearly 15ms behind/ahead of where it should be relative to the loop.

### 2C. The Step Accumulation Problem

Both arp and seq advance timing like this:
```c
arp_state.next_note_time = current_time + ms_per_16th;
```

This means **each step's timing error compounds**. If `ms_per_16th` is 115ms instead of 114.946ms, every single step adds 0.054ms of drift. This is the classic "accumulating rounding error" problem.

Contrast with the loop system: loop events have **absolute timestamps** from the recording, so there is zero drift — every event plays at its exact recorded position relative to `state->timer`.

### 2D. Multiple Sequencers Drifting Apart

When two sequencers start at different times (e.g., user starts seq slot 0, then starts seq slot 1 a few bars later), they each independently compute `next_note_time = current_time + ms_per_16th`. Since they started at different absolute times, even with the **same** ms_per_16th value, they will never re-align to each other unless they share a common time reference.

Currently each sequencer's `pattern_start_time` is independently set to `timer_read32()` when it starts. There is no shared "beat grid" that all sequencers lock to.

---

## 3. BPM Precision Analysis: The Core Problem

### Where Precision is Preserved

| System | BPM Format | Math | Precision |
|--------|-----------|------|-----------|
| Loop record/playback | `current_bpm` (×100000) | `6000000000ULL / current_bpm` | Full (64-bit math) |
| Loop quantization | Same | `6000000000ULL / current_bpm` | Full |
| Proximity threshold | Same | `6000000000ULL / current_bpm` | Full |
| BPM flash LED | Same | Direct calculation | Full |

### Where Precision is LOST

| System | Operation | Precision Loss |
|--------|-----------|----------------|
| `get_ms_per_16th()` | `current_bpm / 100000` → integer | **Fractional BPM truncated** |
| `get_ms_per_16th()` | `60000 / actual_bpm` → integer | **Sub-ms truncated** |
| `get_ms_per_16th()` | `result / 4` → integer | **More truncation** |
| `seq_get_ms_per_16th()` | Same three operations | **Same precision loss** |
| Both arp/seq | `next_time = current + ms_per_16th` | **Cumulative drift** |

### The Fix Needed

Instead of computing an integer ms-per-step, we need to compute **absolute beat-grid timestamps** using the full-precision BPM, just like the loop system uses absolute event timestamps.

---

## 4. Proximity Threshold Analysis

### Current Implementation
```c
// process_dynamic_macro.c line 641
static uint32_t calculate_restart_proximity_threshold(uint8_t macro_idx) {
    if (unsynced_mode_active == 2 || unsynced_mode_active == 5) return 0;

    if (current_bpm > 0 && unsynced_mode_active == 1) {
        uint32_t quarter_note_ms = 6000000000ULL / current_bpm;
        return quarter_note_ms;  // Up to ~500ms at 120 BPM
    }
    if (current_bpm > 0 && unsynced_mode_active == 3) {
        return (6000000000ULL / current_bpm) / 3;  // ~167ms at 120 BPM
    }
    // Fallback: 25% of shortest loop
    ...
}
```

### Why It Exists & Why It Causes Problems

The proximity threshold exists because when you press a button to restart/sync loops, the button press doesn't land exactly at the loop boundary. The loop might be at 1843ms into a 1846ms loop. Without the threshold, the system would wait for the remaining 3ms, then restart — but by that time the user's intent to restart "now" is stale.

**The fundamental problem**: Loop lengths are derived from human performance (recording), so they're inherently imprecise. A loop recorded at "130 BPM" might be 1843ms, 1847ms, or 1850ms. When you record a second loop, it might be 3694ms (targeting 2x). The proximity threshold papers over the ~4ms gap.

**Why this is wrong**: The threshold is a band-aid. The real fix is to ensure all loops have **exact multiplicative lengths** from the start. If BPM = 130.47 and a quarter note = 460.184ms, then:
- 4-beat loop = 1840.736ms (exactly)
- 8-beat loop = 3681.472ms (exactly 2x)
- 16-beat loop = 7362.944ms (exactly 4x)

With exact multiplicative lengths, loops will **never** go out of sync because they share a common period. No proximity threshold needed.

### What Prevents This Today

1. **BPM is calculated FROM the first loop**, not the other way around. The first loop's raw length determines BPM, and fractional milliseconds are lost.

2. **Subsequent loops are quantized to multiples of the master loop length** (in mode 0), not to multiples of the BPM-derived period. Since the master loop length itself has rounding error from the BPM calculation, the error propagates.

3. **The quarter-note calculation uses full precision** (`6000000000ULL / current_bpm`), but the loop length was already rounded when it was stored as a `uint32_t` millisecond count.

---

## 5. Interaction Analysis: Recording a Loop While Arp is Held

### Current Flow (Step by Step)

1. **User holds arp button** → `arp_handle_key_press()` → `arp_start(preset_id)`
   - Sets `arp_state.active = true`
   - Sets `arp_state.next_note_time = timer_read32()` (starts immediately)
   - Arp begins stepping through pattern using `get_ms_per_16th()` (imprecise)

2. **User presses loop record button** (while still holding arp)
   - `process_midi_macro_key_event()` → starts recording macro
   - `recording_start_time = timer_read32()`
   - MIDI events from arp note-ons are captured into the macro buffer
   - Events timestamped relative to `recording_start_time`

3. **Arp continues running** during recording
   - Notes are generated by `arp_update()` at the imprecise step rate
   - These notes go through `midi_send_noteon_arp()` → normal MIDI output
   - If loop system intercepts them, they're recorded with their actual timestamps

4. **User presses loop button again to stop recording**
   - **Special case detected**: `current_bpm == 0 && arp_is_active()` → line 9951
   - Sets `loop_deferred_record_stop_pending = true`
   - Recording continues until next arp step boundary

5. **At next arp step boundary** (`arp_update()` line 852):
   ```c
   if (loop_deferred_record_stop_pending) {
       execute_deferred_record_stop();
       // Advance timing but don't play notes this step
   }
   ```

6. **`execute_deferred_record_stop()`** (line 6481):
   - Calls `dynamic_macro_record_end()` which calculates loop length and BPM
   - **THEN overrides BPM to exactly 120**: `current_bpm = 12000000`
   - This is a hardcoded override regardless of actual tempo
   - Starts MIDI clock at 120 BPM

### Problems with This Interaction

1. **BPM override to 120**: The deferred stop forces BPM to 120.0 regardless of the actual arp tempo. If the user had set up their arp at a specific rate, the loop BPM won't match.

2. **Arp timing is imprecise**: The arp steps that got recorded into the loop used the truncated BPM math. When the loop plays back, it plays the events at their recorded timestamps (precise), but the arp continues using its imprecise step timing. They drift apart.

3. **No shared beat grid**: The arp's `pattern_start_time` and the loop's `state->timer` are independent time references. There's no mechanism to align the arp's pattern position with the loop's playback position.

4. **Deferred stop timing**: The recording ends at an arp step boundary, which is determined by the imprecise `get_ms_per_16th()`. So the loop length itself inherits the arp's timing imprecision.

---

## 6. Root Cause Summary

### Problem 1: BPM Truncation in Arp/Seq
- **Location**: `arpeggiator.c` lines 510, 559
- **Cause**: `get_effective_bpm() / 100000` performs integer division, losing fractional BPM
- **Impact**: All arp and seq step timing is based on a rounded-down BPM

### Problem 2: Integer Division Cascade
- **Location**: `arpeggiator.c` lines 513-514, 562-563
- **Cause**: `(60000 / actual_bpm) / 4` — two successive integer divisions
- **Impact**: Additional sub-millisecond precision loss per step

### Problem 3: Cumulative Drift (No Absolute Time Reference)
- **Location**: `arpeggiator.c` lines 835, 1097, 1277
- **Cause**: `next_note_time = current_time + ms_per_16th` — each step adds a rounded value
- **Impact**: Drift accumulates linearly over time; grows to multiple ms within bars

### Problem 4: No Shared Beat Grid
- **Location**: Each system has independent start times
- **Cause**: Arp uses `pattern_start_time`, seq uses `seq_state[slot].pattern_start_time`, loop uses `state->timer` — all set independently via `timer_read32()`
- **Impact**: Multiple sequencers cannot align to each other; arp cannot align to loop

### Problem 5: Proximity Threshold as Band-Aid
- **Location**: `process_dynamic_macro.c` line 641
- **Cause**: Loop lengths aren't exact BPM multiples, so restarts need fuzzy matching
- **Impact**: Inconsistent restart behavior, sometimes snapping early/late

### Problem 6: Hardcoded 120 BPM Override
- **Location**: `process_dynamic_macro.c` line 6498
- **Cause**: `execute_deferred_record_stop()` forces `current_bpm = 12000000`
- **Impact**: Recording-while-arp ignores actual performance tempo

---

## 7. Implementation Plan

### Phase 1: High-Precision BPM-to-Microsecond Conversion (CORE FIX)

**Goal**: Replace the truncating `get_ms_per_16th()` with a function that preserves full BPM precision.

**File**: `arpeggiator.c`

#### Step 1.1: Create `get_us_per_step()` — Microsecond-Precision Step Duration

Replace the two functions `get_ms_per_16th()` and `seq_get_ms_per_16th()` with versions that return microseconds (or fractional milliseconds using fixed-point):

```c
// Returns microseconds per step with full BPM precision
// Uses 64-bit math to avoid overflow: 60,000,000 us/min * 1000 / bpm_x100000
static uint32_t get_us_per_step(uint8_t note_value, uint8_t timing_mode) {
    uint32_t bpm = get_effective_bpm();  // Format: actual_bpm * 100000

    // Quarter note duration in microseconds:
    // = 60,000,000 us / (bpm / 100000)
    // = 60,000,000 * 100000 / bpm
    // = 6,000,000,000,000 / bpm
    // This gives us microsecond precision
    uint64_t quarter_us = 6000000000000ULL / bpm;

    // 16th note = quarter / 4
    uint64_t step_us = quarter_us / 4;

    // Apply note value multiplier
    switch (note_value) {
        case NOTE_VALUE_QUARTER:   step_us *= 4; break;
        case NOTE_VALUE_EIGHTH:    step_us *= 2; break;
        case NOTE_VALUE_SIXTEENTH:
        default: break;
    }

    // Apply timing mode
    if (timing_mode & TIMING_MODE_TRIPLET) {
        step_us = (step_us * 2) / 3;
    } else if (timing_mode & TIMING_MODE_DOTTED) {
        step_us = (step_us * 3) / 2;
    }

    return (uint32_t)step_us;  // Microseconds per step
}
```

**Precision comparison at 130.47 BPM (sixteenth notes)**:

| Method | Result | Actual | Error |
|--------|--------|--------|-------|
| Old: `60000/130/4` | 115ms = 115000us | 114,946us | +54us/step |
| New: `6000000000000/13047000/4` | 114,946us | 114,946us | ~0us/step |

#### Step 1.2: Update `get_ms_per_16th()` and `seq_get_ms_per_16th()` Wrappers

Keep the existing function signatures for backward compatibility but have them call the new precise function:

```c
static uint32_t get_ms_per_16th(const arp_preset_t *preset) {
    uint8_t note_value, timing_mode;
    // ... extract from preset or override (existing logic) ...
    return get_us_per_step(note_value, timing_mode) / 1000;  // For gate calculations
}
```

The ms version is still needed for gate duration calculations where microsecond precision doesn't matter.

### Phase 2: Absolute Beat Grid (DRIFT ELIMINATION)

**Goal**: Replace the accumulating `next_time = current + step_duration` pattern with absolute grid timestamps.

**Files**: `arpeggiator.c`

#### Step 2.1: Add a Global Beat Grid Origin

```c
// Global beat grid: all arp/seq timing derives from this single reference point
static uint32_t beat_grid_origin_us = 0;  // Microsecond timestamp of beat 0
static bool beat_grid_active = false;

// Set when first loop starts playing or when BPM is first established
void sync_beat_grid_origin(uint32_t origin_ms) {
    beat_grid_origin_us = origin_ms * 1000;
    beat_grid_active = true;
}
```

#### Step 2.2: Replace Accumulative Timing in `arp_update()`

Instead of:
```c
arp_state.next_note_time = current_time + ms_per_16th;
```

Use:
```c
// Calculate the absolute time of the next step on the beat grid
uint32_t step_us = get_us_per_step(note_value, timing_mode);
uint32_t next_step_abs_us = beat_grid_origin_us +
    (uint64_t)(arp_state.current_position_16ths + 1) * step_us;
arp_state.next_note_time = next_step_abs_us / 1000;  // Convert back to ms
```

This way, step N always fires at `origin + N * step_duration`, regardless of any per-step rounding. No drift can accumulate.

#### Step 2.3: Replace Accumulative Timing in `seq_update()`

Same pattern for each sequencer slot:
```c
uint32_t step_us = seq_get_us_per_step(preset, slot);
uint32_t abs_position = seq_state[slot].grid_start_position +
    seq_state[slot].current_position_16ths + 1;
seq_state[slot].next_note_time = (beat_grid_origin_us +
    (uint64_t)abs_position * step_us) / 1000;
```

#### Step 2.4: Replace Accumulative Timing in Chord Unsynced Mode

The per-note `unsynced_notes[u].next_note_time` also uses the accumulative pattern. Apply the same absolute grid approach per-note.

### Phase 3: Shared Beat Grid for Multi-Sequencer Sync

**Goal**: All sequencers share a common beat grid so they stay aligned regardless of start time.

**Files**: `arpeggiator.c`

#### Step 3.1: Track Grid Position Globally

```c
// When a seq starts, snap its position to the nearest grid point
void seq_start(uint8_t preset_id) {
    // ... existing slot finding and preset loading ...

    if (beat_grid_active) {
        uint32_t current_us = timer_read32() * 1000;
        uint32_t step_us = seq_get_us_per_step(preset, slot);

        // Calculate which global step we're on
        uint64_t elapsed = current_us - beat_grid_origin_us;
        uint32_t global_step = (uint32_t)(elapsed / step_us);

        // Store the global step offset so this seq's position 0 = this global step
        seq_state[slot].grid_start_position = global_step;
        seq_state[slot].current_position_16ths = 0;
        seq_state[slot].next_note_time = ((beat_grid_origin_us +
            (uint64_t)(global_step + 1) * step_us) / 1000);
    } else {
        // No grid yet - start immediately (existing behavior)
        seq_state[slot].grid_start_position = 0;
    }
}
```

This ensures that when sequencer B starts 8 bars after sequencer A, its steps still land on the global beat grid. Both sequencers' 16th notes will align perfectly.

### Phase 4: Eliminate Proximity Threshold (EXACT LOOP LENGTHS)

**Goal**: Make all loop lengths exact multiples of the BPM-derived period, eliminating the need for fuzzy restart matching.

**Files**: `process_dynamic_macro.c`

#### Step 4.1: Compute Exact Loop Length from BPM at Record End

When a loop recording ends and a BPM exists:

```c
// In dynamic_macro_record_end():
if (current_bpm > 0) {
    // Calculate exact quarter note in microseconds
    uint64_t quarter_us = 6000000000000ULL / current_bpm;

    // Convert raw loop length to microseconds
    uint64_t raw_length_us = (uint64_t)state->loop_length * 1000;

    // Find nearest whole number of quarter notes
    uint32_t num_quarters = (uint32_t)((raw_length_us + quarter_us/2) / quarter_us);
    if (num_quarters < 1) num_quarters = 1;

    // Set loop length to EXACT multiple
    // Store in microseconds internally, or convert back to ms with rounding
    uint64_t exact_length_us = num_quarters * quarter_us;
    state->loop_length = (uint32_t)((exact_length_us + 500) / 1000);  // Round to nearest ms

    // Also store the exact microsecond length for ISR use
    state->loop_length_us = exact_length_us;
}
```

#### Step 4.2: For the FIRST Loop (BPM Calculated FROM Loop)

When BPM is derived from the first loop, we reverse the process:

```c
// After calculating BPM from loop length:
// Re-derive an exact loop length that is a perfect multiple of the derived BPM
uint64_t quarter_us = 6000000000000ULL / current_bpm;
uint32_t num_quarters = (uint32_t)(((uint64_t)state->loop_length * 1000 + quarter_us/2) / quarter_us);
state->loop_length = (uint32_t)((num_quarters * quarter_us + 500) / 1000);
```

This creates a "clean" loop length that, when divided by the BPM-derived quarter note, yields an exact integer. No remainder, no drift.

#### Step 4.3: Remove `calculate_restart_proximity_threshold()`

With exact multiplicative loop lengths, the restart check becomes trivial:

```c
// OLD: fuzzy proximity check
uint32_t threshold = calculate_restart_proximity_threshold(i);
if (time_to_real_end <= threshold) { should_restart = true; }

// NEW: exact boundary check (allow 1ms tolerance for timer granularity)
if (time_to_real_end <= 1) { should_restart = true; }
```

Or better: use the ISR's `waiting_for_loop_gap` mechanism which already handles exact end-of-loop detection.

### Phase 5: Connect Loop Playback Start to Beat Grid

**Goal**: When a loop starts playing, sync the beat grid so arp/seq are aligned.

**Files**: `process_dynamic_macro.c`, `arpeggiator.c`

#### Step 5.1: Set Beat Grid on First Loop Play

```c
// In dynamic_macro_play():
state->timer = timer_read32();
state->is_playing = true;

// Establish/reset beat grid for arp and seq
if (current_bpm > 0) {
    sync_beat_grid_origin(state->timer);
}
```

#### Step 5.2: Realign Beat Grid on Loop Restart

When `check_loop_trigger()` restarts all loops simultaneously:

```c
// In the synchronized restart section:
uint32_t restart_time = timer_read32();
for (each restarting macro) {
    macro_playback[i].timer = restart_time;
}
// Re-anchor the beat grid
sync_beat_grid_origin(restart_time);
```

#### Step 5.3: Realign Running Arp/Seq to New Grid

When the beat grid is reset (e.g., loop restarts), running arp/seq should snap to the new grid without audible glitch:

```c
void sync_beat_grid_origin(uint32_t origin_ms) {
    beat_grid_origin_us = (uint64_t)origin_ms * 1000;
    beat_grid_active = true;

    // Recalculate next_note_time for running arp
    if (arp_state.active) {
        uint32_t step_us = get_us_per_step(...);
        // Find next step on new grid
        arp_state.next_note_time = origin_ms;  // Next step is now
    }

    // Recalculate for all active seq slots
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) {
            seq_state[i].next_note_time = origin_ms;
        }
    }
}
```

### Phase 6: Fix Deferred Record Stop BPM Override

**Goal**: Remove the hardcoded 120 BPM override when recording with arp active.

**File**: `process_dynamic_macro.c`

#### Step 6.1: Use Actual BPM Instead of 120

```c
void execute_deferred_record_stop(void) {
    // ... existing code ...

    dynamic_macro_record_end(rec_start, macro_pointer, +1, rec_end_ptr, &recording_start_time);

    // REMOVE: current_bpm = 12000000;  // Don't force 120 BPM
    // INSTEAD: Let record_end's BPM calculation stand, or if arp had a
    // specific BPM set via tap tempo / manual entry, preserve that

    if (current_bpm == 0) {
        // BPM wasn't set before, and record_end calculated one from loop length
        // That's fine - use it as-is
    }
    bpm_source_macro = saved_macro_id;

    // ... rest of existing code ...
}
```

### Phase 7: Add `loop_length_us` to Playback State (Microsecond Precision)

**Goal**: Store loop lengths with microsecond precision for exact arithmetic.

**Files**: `process_dynamic_macro.c`, `process_dynamic_macro.h`

#### Step 7.1: Extend `macro_playback_state_t`

```c
typedef struct {
    // ... existing fields ...
    uint32_t loop_length;      // Milliseconds (kept for backward compat)
    uint64_t loop_length_us;   // Microseconds (new, for precise calculations)
    // ...
} macro_playback_state_t;
```

#### Step 7.2: Set Both Values at Record End

Wherever `state->loop_length` is set, also set `state->loop_length_us`:
```c
state->loop_length = quantized_ms;
state->loop_length_us = (uint64_t)num_quarters * quarter_us;
```

---

## Implementation Order & Dependencies

```
Phase 1 (BPM Precision)     ← No dependencies, pure math fix
    ↓
Phase 2 (Beat Grid)         ← Depends on Phase 1 for precise step_us
    ↓
Phase 3 (Multi-Seq Sync)    ← Depends on Phase 2 for shared grid
    ↓
Phase 4 (Exact Loop Lengths)← Independent of Phases 2-3
    ↓
Phase 5 (Loop↔Grid Connect) ← Depends on Phases 2 + 4
    ↓
Phase 6 (Deferred Stop Fix) ← Independent, can be done anytime
    ↓
Phase 7 (Microsecond State) ← Supports Phases 4 + 5, can be done with Phase 4
```

**Suggested implementation order**: 1 → 7 → 4 → 2 → 3 → 5 → 6

This order builds precision from the bottom up: first fix the math, then fix the data structures, then fix the coordination.

---

## Risk Assessment

| Phase | Risk | Mitigation |
|-------|------|------------|
| 1 | 64-bit math on ARM Cortex-M4 | Cortex-M4 has hardware multiplier; 64÷32 division compiles to `__aeabi_uldivmod` (~40 cycles) — acceptable for once-per-step |
| 2 | Beat grid reset during active arp | Snap-to-grid logic prevents audible glitch |
| 3 | Memory cost of `grid_start_position` | 4 bytes per seq slot (32 bytes total) — negligible |
| 4 | Changing loop lengths of existing recordings | Only affects NEW recordings; existing loops keep their stored lengths |
| 5 | Tight coupling between loop and arp systems | Use the existing `extern` pattern — no new coupling paradigm |
| 6 | Removing 120 BPM override may break specific workflows | Make it conditional on whether BPM was already set |
| 7 | Adding `uint64_t` to playback state struct | 8 bytes per macro × 4 macros = 32 bytes — negligible |

---

## Summary of Changes by File

| File | Changes |
|------|---------|
| `arpeggiator.c` | New `get_us_per_step()`, rewrite `get_ms_per_16th()` / `seq_get_ms_per_16th()`, beat grid globals, absolute timing in `arp_update()` / `seq_update()` / `seq_start()` |
| `orthomidi5x14.h` | Declare `sync_beat_grid_origin()`, add `grid_start_position` to `seq_state_t`, add `loop_length_us` to playback state |
| `process_dynamic_macro.c` | Exact loop length quantization at record end, remove proximity threshold, call `sync_beat_grid_origin()` on play/restart, fix deferred stop BPM override |
| `process_dynamic_macro.h` | Add `loop_length_us` field to `macro_playback_state_t` |
