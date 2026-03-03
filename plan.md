# Quick Build Persistent Pool Storage - Implementation Plan

## Overview

Replace the current RAM-only quick build storage with a persistent pool allocator backed by EEPROM. Quick builds will survive power cycles. Uses Option A (compact-on-delete) with a 16KB EEPROM pool and variable-size presets.

---

## Architecture

### Pool Layout (EEPROM)

```
EEPROM Address 45000 (after per-key actuation ends ~44722)
┌─────────────────────────────────────────────────────┐
│ Pool Header (16 bytes)                               │
│   magic (2B) | version (1B) | pool_used (2B)        │
│   arp_count (1B) | seq_count (1B) | reserved (9B)   │
├─────────────────────────────────────────────────────┤
│ Slot Index (12 entries × 8 bytes = 96 bytes)         │
│   [0] type(1) | flags(1) | offset(2) | size(2) |   │
│       channel(1) | reserved(1)                       │
│   ...                                                │
│   [11] ...                                           │
├─────────────────────────────────────────────────────┤
│ Pool Data Area (~16272 bytes)                        │
│   [preset bytes packed contiguously]                 │
│   [free space...]                                    │
└─────────────────────────────────────────────────────┘
```

**Total: 16 + 96 + 16272 = 16384 bytes (16KB)**

### Slot Mapping

- Slots 0-3: ARP quick builds (maps to arp_slot 0-3)
- Slots 4-11: SEQ quick builds (maps to seq_slot 0-7, pool_index = seq_slot + 4)

### Variable-Size Storage

Only store actual notes, not full fixed-size arrays:
- **ARP actual size:** `8 + (note_count × 3)` bytes (min 8, max 200)
- **SEQ actual size:** `8 + (note_count × 3)` bytes (min 8, max 392)

Since `magic` is at the end of the struct (after the notes array), we store presets in pool format:
```
[6 header bytes][magic 2B][note_count × 3 note bytes]
```
On load: read 8B header+magic, read notes into dest, zero the rest.

---

## Changes by File

### 1. `orthomidi5x14.h` — New types and constants

**Add after line 872:**

```c
// Pool storage constants
#define PRESET_POOL_EEPROM_ADDR 45000
#define PRESET_POOL_SIZE        16384
#define PRESET_POOL_MAGIC       0x5142  // "QB"
#define PRESET_POOL_VERSION     1
#define POOL_HEADER_SIZE        16
#define POOL_MAX_SLOTS          12      // 4 arp + 8 seq
#define POOL_INDEX_ENTRY_SIZE   8
#define POOL_INDEX_SIZE         (POOL_MAX_SLOTS * POOL_INDEX_ENTRY_SIZE)  // 96
#define POOL_DATA_OFFSET        (POOL_HEADER_SIZE + POOL_INDEX_SIZE)      // 112
#define POOL_DATA_SIZE          (PRESET_POOL_SIZE - POOL_DATA_OFFSET)     // 16272

#define POOL_SLOT_EMPTY  0
#define POOL_SLOT_ARP    1
#define POOL_SLOT_SEQ    2
#define POOL_SLOT_FLAG_VALID 0x01

typedef struct __attribute__((packed)) {
    uint8_t  type;       // POOL_SLOT_EMPTY/ARP/SEQ
    uint8_t  flags;      // bit 0: valid
    uint16_t offset;     // Offset into pool data area
    uint16_t size;       // Size of preset data in pool
    uint8_t  channel;    // MIDI channel at build time (seq only)
    uint8_t  reserved;
} pool_slot_index_t;

typedef struct {
    uint16_t pool_used;                          // Bytes used in data area
    pool_slot_index_t slots[POOL_MAX_SLOTS];     // 12 × 8 = 96 bytes
} qb_pool_state_t;

extern qb_pool_state_t qb_pool;

// Pool API
void qb_pool_init(void);
void qb_pool_load(void);
bool qb_pool_save_arp(uint8_t arp_slot, const arp_preset_t *preset);
bool qb_pool_save_seq(uint8_t seq_slot, const seq_preset_t *preset, uint8_t channel);
bool qb_pool_load_arp(uint8_t arp_slot, arp_preset_t *dest);
bool qb_pool_load_seq(uint8_t seq_slot, seq_preset_t *dest);
void qb_pool_erase_slot(uint8_t pool_index);
bool qb_pool_has_build(uint8_t pool_index);
uint8_t qb_pool_get_channel(uint8_t pool_index);
```

**Modify `quick_build_state_t` (line 884):**
Remove these fields (now tracked in `qb_pool`):
- `has_saved_arp_build[MAX_ARP_QB_SLOTS]`
- `has_saved_seq_build[8]`
- `saved_seq_channel[8]`

Keep `active_arp_qb_slot` (still needed for arp swap tracking).

### 2. `arpeggiator.c` — Pool implementation + updated functions

**Remove:** `static arp_preset_t arp_quick_build_storage[MAX_ARP_QB_SLOTS];` (line 107) — saves 800 bytes of RAM.

**Add:** `qb_pool_state_t qb_pool;` global.

**New functions to add:**

#### `qb_pool_init()` — Reset pool to empty
Write magic + version + zero index to EEPROM.

#### `qb_pool_load()` — Boot-time load
Read header from EEPROM. If magic mismatch, call `qb_pool_init()`. Otherwise read `pool_used` and all 12 index entries into `qb_pool`.

#### `qb_pool_write_header_and_index()` — Flush metadata to EEPROM
Write the 16-byte header and 96-byte index (112 bytes total) to EEPROM. Called after every pool mutation.

#### `qb_pool_save_arp(arp_slot, preset)` — Save arp to pool
1. `pool_idx = arp_slot` (0-3)
2. Calculate `data_size = 8 + preset->note_count * 3`
3. If slot already occupied, call `qb_pool_erase_slot(pool_idx)` first
4. Check `pool_used + data_size <= POOL_DATA_SIZE`
5. Append: write header (6B) + magic (2B) + notes to EEPROM at `POOL_DATA_OFFSET + pool_used`
6. Update index entry: type=ARP, flags=VALID, offset=pool_used, size=data_size
7. `pool_used += data_size`
8. `qb_pool_write_header_and_index()`

#### `qb_pool_save_seq(seq_slot, preset, channel)` — Save seq to pool
Same as arp but `pool_idx = seq_slot + 4`, type=SEQ, stores channel.

#### `qb_pool_load_arp(arp_slot, dest)` — Load arp from pool
1. `pool_idx = arp_slot`
2. Check type == POOL_SLOT_ARP
3. Zero dest, read header (8B), read notes into dest
4. Validate with `arp_validate_preset()`

#### `qb_pool_load_seq(seq_slot, dest)` — Load seq from pool
Same pattern, `pool_idx = seq_slot + 4`.

#### `qb_pool_erase_slot(pool_index)` — Erase with compaction
1. Get slot's offset and size
2. Calculate `after_bytes = pool_used - (offset + size)`
3. If `after_bytes > 0`: compact EEPROM in 64-byte chunks (memmove via read/write)
4. Update all index entries with `offset > deleted_offset`: subtract size
5. Mark slot empty
6. `pool_used -= size`
7. `qb_pool_write_header_and_index()`

#### Helper functions
- `qb_pool_has_build(pool_idx)`: return `slots[pool_idx].type != POOL_SLOT_EMPTY`
- `qb_pool_get_channel(pool_idx)`: return `slots[pool_idx].channel`

**Modify existing functions:**

#### `quick_build_finish()` (~line 2671)
ARP path:
- Replace `memcpy(&arp_quick_build_storage[arp_slot], &arp_active_preset, ...)` with `qb_pool_save_arp(arp_slot, &arp_active_preset)`
- Remove `has_saved_arp_build[arp_slot] = true`

SEQ path:
- Add `qb_pool_save_seq(slot, &seq_active_presets[slot], channel_number)`
- Remove `has_saved_seq_build[slot] = true` and `saved_seq_channel[slot] = channel_number`

#### `quick_build_load_arp_slot()` (~line 2764)
- Replace `memcpy(&arp_active_preset, &arp_quick_build_storage[slot], ...)` with `qb_pool_load_arp(slot, &arp_active_preset)`
- Keep `active_arp_qb_slot` tracking

#### `quick_build_erase_arp()` (~line 2752)
- Add `qb_pool_erase_slot(slot)` (slots 0-3 for arp)
- Remove `has_saved_arp_build[slot] = false`

#### `quick_build_erase_seq()` (~line 2782)
- Add `qb_pool_erase_slot(slot + 4)` (slots 4-11 for seq)
- Remove `has_saved_seq_build[slot] = false`

#### `seq_start_slot()` (~line 3322)
- Before starting playback, load from pool: `qb_pool_load_seq(slot, &seq_active_presets[slot])`
- Get channel from pool: `qb_pool_get_channel(slot + 4)` instead of `saved_seq_channel[slot]`

### 3. `orthomidi5x14.c` — Init + button handler updates

**Add to `keyboard_post_init_user()` or equivalent:**
```c
qb_pool_load();  // Load pool index from EEPROM at boot
```

**Modify ARP_QUICK_BUILD handler (~line 14150):**
```c
// Before: quick_build_state.has_saved_arp_build[slot]
// After:  qb_pool_has_build(slot)
```

**Modify SEQ_QUICK_BUILD handler (~line 14220):**
```c
// Before: quick_build_state.has_saved_seq_build[slot]
// After:  qb_pool_has_build(slot + 4)
```

**Update `quick_build_state` initializer (~line 83 in arpeggiator.c):**
Remove initializers for deleted fields (`has_saved_arp_build`, `has_saved_seq_build`, `saved_seq_channel`).

### 4. Validation update

In both `arp_validate_preset()` and `seq_validate_preset()`: remove the `> 127` check on `pattern_length_16ths`. Since it's `uint8_t`, it naturally caps at 255 (16 bars at 16th resolution). The note timing position is still 7 bits (0-127) in the packed format, so steps 128-255 are just empty loop time.

---

## Performance Analysis

**Compaction (worst case):** ~16KB EEPROM copy in 64-byte chunks = 256 iterations. Each `eeprom_read_block` + `eeprom_update_block` pair takes ~5ms for 64 bytes on I2C EEPROM at 400kHz. Total: ~1.3 seconds worst case. This only happens on delete (1.5s button hold), never during recording or playback.

**Save (typical):** Write header+index (112B) + preset data (32-56B typical) = ~170B. Takes ~25ms.

**Load (typical):** Read header+index (112B) on boot. Read single preset (~50B) on button press. <10ms.

**RAM savings:** Remove `arp_quick_build_storage[4]` (800 bytes). Add `qb_pool_state_t` (~100 bytes). Net saving: ~700 bytes.

---

## Implementation Order

1. Add pool types/constants to `orthomidi5x14.h`
2. Implement pool core functions in `arpeggiator.c`
3. Update `quick_build_state_t` (remove old fields)
4. Update `quick_build_finish/load/erase` functions
5. Update `seq_start_slot()` to load from pool
6. Update button handlers in `orthomidi5x14.c`
7. Add `qb_pool_load()` to boot init
8. Relax pattern_length validation (remove 127 cap)
9. Update `quick_build_state` initializer
10. Test compilation

---

## Edge Cases

- **Pool full:** `qb_pool_save_*()` returns false. Build still works in RAM for the session but won't persist. Could show OLED "Pool Full" warning.
- **Corrupt EEPROM:** Magic mismatch → `qb_pool_init()` resets pool to empty.
- **Overwriting existing slot:** Erase-then-save (compact + append).
- **Boot with saved builds:** `qb_pool_load()` reads index. `qb_pool_has_build()` returns true. First button press loads data from EEPROM into the existing playback arrays.
- **Compaction during erase:** Only happens on long-press erase (1.5s hold), never in the hot path.
- **Factory preset overwrites seq slot:** If user loads a factory/user preset into a seq slot that had a quick build, the pool data persists in EEPROM. Next QB button press reloads from pool.
