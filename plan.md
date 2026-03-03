# Plan: Shared Note Pool for Quick Build Arp/Seq Presets

## Design Summary

- **Pool**: 4096 notes × 3 bytes = 12,288 bytes shared across all quick build presets
- **Per-preset limit**: Soft (pool space), `note_count` upgraded to `uint16_t`
- **Existing arrays**: `seq_active_presets[8]` and `arp_active_preset` kept as staging for factory/user presets
- **Playback**: Static scratch buffer (16 notes per step max) replaces stack VLAs

## Implementation Steps

### Step 1: Add pool infrastructure (orthomidi5x14.h + arpeggiator.c)

**orthomidi5x14.h changes:**
- Add `#define NOTE_POOL_SIZE 4096`
- Add `#define MAX_NOTES_PER_STEP 16`
- Add `pool_preset_t` struct (header only, no embedded notes)
- Change `quick_build_state_t.note_count` from `uint8_t` to `uint16_t`
- Add extern declarations for pool arrays and functions

**arpeggiator.c changes:**
- Add `static arp_preset_note_t note_pool[NOTE_POOL_SIZE]`
- Add `static uint16_t note_pool_used = 0`
- Add pool header arrays:
  - `static pool_preset_t arp_pool_headers[MAX_ARP_QB_SLOTS]`
  - `static pool_preset_t seq_pool_headers[MAX_SEQ_SLOTS]`
- Remove `static arp_preset_t arp_quick_build_storage[MAX_ARP_QB_SLOTS]` (800 bytes saved)
- Add pool management functions:
  - `pool_reset()`
  - `pool_alloc(uint16_t count)` → offset or UINT16_MAX
  - `pool_free(pool_preset_t *header)` → compact + update all offsets
  - `pool_get_notes(pool_preset_t *header)` → &note_pool[offset]
  - `pool_notes_available()` → remaining capacity

### Step 2: Modify quick build recording

**quick_build_enter_recording():**
- Arp path: `pool_free(&arp_pool_headers[slot])` then `pool_alloc(NOTE_POOL_SIZE - note_pool_used)` to give it all remaining space. Still init arp_active_preset header for validation.
- Seq path: Same pattern with `seq_pool_headers[slot]`

**quick_build_handle_note() arp:**
- Replace `arp_active_preset.notes[note_count]` with `note_pool[header->pool_offset + note_count]`
- Max check: `note_count >= (NOTE_POOL_SIZE - header->pool_offset)` instead of `>= MAX_ARP_PRESET_NOTES`

**quick_build_handle_note() seq:**
- Replace `seq_active_presets[slot].notes[note_count]` with `note_pool[header->pool_offset + note_count]`
- Same pool-based max check

### Step 3: Modify quick build finish/load/erase

**quick_build_finish() arp:**
- Scan `note_pool[offset..offset+count]` for max_step (instead of arp_active_preset.notes[])
- Trim pool allocation: `header->pool_capacity = note_count` (shrink, shift subsequent allocations)
- Copy header metadata (pattern_length, gate, timing, etc.) into pool_preset_t
- No more memcpy to arp_quick_build_storage

**quick_build_finish() seq:**
- Same pool-based approach

**quick_build_load_arp_slot():**
- Copy pool notes to arp_active_preset.notes[] (truncated to MAX_ARP_PRESET_NOTES for the staging struct)
- OR: change arp_update() to read directly from pool when preset_id == PRESET_ID_QUICK_BUILD

**quick_build_erase_arp/seq():**
- Call `pool_free(header)` to release pool space

### Step 4: Modify quick_build_undo_step

- Both arp and seq paths: scan `note_pool[offset..offset+count]` instead of preset.notes[]
- Compact within the allocation (shift notes down within the slot's pool region)

### Step 5: Modify playback to use pool for QB presets

**arp_update():**
- When `arp_state.loaded_preset_id == PRESET_ID_QUICK_BUILD`:
  - Get notes from `pool_get_notes(&arp_pool_headers[active_slot])`
  - Use pool_preset_t header for note_count, pattern_length, etc.
- Otherwise: use arp_active_preset as before (factory/user presets)
- Replace stack VLAs with static scratch:
  ```c
  static unpacked_note_t step_scratch[MAX_NOTES_PER_STEP];
  static uint8_t step_scratch_indices[MAX_NOTES_PER_STEP];
  uint8_t scratch_count = 0;
  for (i = 0; i < note_count; i++) {
      unpack_note(&notes[i], &tmp, is_arp);
      if (tmp.timing == current_pos && scratch_count < MAX_NOTES_PER_STEP) {
          step_scratch[scratch_count] = tmp;
          scratch_count++;
      }
  }
  ```

**seq_update():**
- Same pattern: pool for QB presets, seq_active_presets for factory/user
- Same static scratch buffer approach

### Step 6: Factory/user preset loading through pool

**arp_load_preset_into_slot():**
- No change needed: factory/user presets still load into arp_active_preset
- Playback checks preset_id to decide pool vs arp_active_preset

**seq_load_preset_into_slot():**
- No change needed: factory/user presets still load into seq_active_presets[slot]
- Playback checks preset_id to decide pool vs seq_active_presets[slot]

## Files Modified

| File | Changes |
|------|---------|
| `orthomidi5x14.h` | Add pool_preset_t, NOTE_POOL_SIZE, MAX_NOTES_PER_STEP, change note_count to uint16_t |
| `arpeggiator.c` | Add pool + management functions, modify all 13 code paths listed in assessment |

## RAM Impact

| Item | Before | After |
|------|--------|-------|
| note_pool | — | 12,288 B |
| arp_quick_build_storage[4] | 800 B | 0 B (removed) |
| pool headers (12 × ~12B) | — | 144 B |
| Stack per seq_update call | 640 B | 0 B (static scratch) |
| Static scratch buffer | — | 80 B |
| **Net new RAM** | | **~11,712 B** |

Total new RAM: ~12KB on a 256KB MCU (4.7%). Existing arp_active_preset (200B) and seq_active_presets (3,136B) kept for factory/user staging.
