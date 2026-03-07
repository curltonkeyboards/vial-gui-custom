# MIDI Delay System - Implementation Plan

## Summary

A delay effect system for the orthomidi5x14 keyboard that repeats MIDI note-on/note-off events with configurable timing, velocity decay, channel routing, and semitone transposition. 100 independent delay slots, each with its own settings, toggled via keycodes.

---

## Design Decisions (from user answers)

- **100 independent slots**, each with full settings (rate, decay, repeats, channel, transpose)
- **BPM-synced + fixed ms** delay rate options
- **Semitone transpose** with cumulative offset mode
- **Mirror original note duration** for note-offs (delay note-off by same interval as note-on)
- **All 100 persistent** in EEPROM (~1600 bytes)
- **64 pending delay events** queue cap
- **Fixed ms range**: 10-5000ms
- **Batch save** from GUI to firmware

---

## Firmware Implementation

### 1. New files: `midi_delay.c` + `midi_delay.h`

Location: `vial-qmk - ryzen/keyboards/orthomidi5x14/`

#### Data Structures

```c
// Per-slot configuration (16 bytes each, 100 slots = 1600 bytes EEPROM)
typedef struct {
    uint8_t  rate_mode;        // 0=BPM-synced, 1=fixed ms
    uint8_t  note_value;       // NOTE_VALUE_QUARTER/EIGHTH/SIXTEENTH (when BPM-synced)
    uint8_t  timing_mode;      // TIMING_MODE_STRAIGHT/TRIPLET/DOTTED (when BPM-synced)
    uint8_t  decay_percent;    // 0-100: velocity reduction per repeat (from original)
    uint16_t fixed_delay_ms;   // 10-5000ms (when fixed ms mode)
    uint8_t  max_repeats;      // 1-255: max number of delay repeats (0=infinite until decay kills it)
    uint8_t  channel;          // 0=same as original, 1-16=specific MIDI channel
    int8_t   transpose_semi;   // -48 to +48 semitones offset
    uint8_t  transpose_mode;   // 0=fixed (all repeats same offset), 1=cumulative (+offset each repeat)
    uint8_t  reserved[6];      // Future use, padding to 16 bytes
} delay_slot_config_t;

// Runtime state per slot (1 byte each, 100 slots = 100 bytes RAM)
// Separate from config so toggle state doesn't require EEPROM write
typedef struct {
    uint8_t active;            // 0=off, 1=on (toggled by keycode at runtime)
} delay_slot_runtime_t;

// Pending delay event (16 bytes each, 64 max = 1024 bytes RAM)
typedef struct {
    uint32_t fire_time;        // When to send this event (timer_read32() target)
    uint32_t note_on_time;     // When the original note-on was played (for duration mirroring)
    uint8_t  channel;          // MIDI channel to send on
    uint8_t  note;             // MIDI note number (after transpose)
    uint8_t  velocity;         // Velocity (after decay applied)
    uint8_t  is_note_off;      // 0=note-on pending, 1=note-off pending
    uint8_t  original_note;    // Original note (before transpose) - for matching note-offs
    uint8_t  original_channel; // Original channel - for matching note-offs
    uint8_t  note_on_sent;     // Was the corresponding delay note-on actually sent? (for note-off gating)
    uint8_t  slot_id;          // Which delay slot spawned this
} delay_event_t;
```

#### Core Functions

- `midi_delay_init()` - Load configs from EEPROM, clear queue, all slots inactive
- `midi_delay_tick()` - Called from `matrix_scan_user()`, fires pending events whose time has arrived
- `midi_delay_schedule_note_on(channel, note, velocity)` - Called after live note-on. For each active slot, schedules all repeat note-ons into the queue
- `midi_delay_schedule_note_off(channel, note)` - Called after live note-off. For each pending note-on event matching this note, schedules a corresponding note-off mirroring the held duration
- `midi_delay_toggle_slot(slot_id)` - Toggle slot active/inactive at runtime
- `midi_delay_save()` / `midi_delay_load()` - EEPROM persistence for configs
- `midi_delay_clear_queue()` - Kill all pending events (panic button)

#### Note-on scheduling logic

When `midi_delay_schedule_note_on()` is called:
1. For each active slot:
   a. Calculate delay interval (BPM-synced reusing arpeggiator's `compute_step_time_offset()` logic, or fixed ms)
   b. For each repeat (1 to max_repeats):
      - Velocity = `original_velocity - (original_velocity * decay_percent * repeat_num / 100)`
      - If velocity <= 0, stop scheduling
      - Note = `original_note + transpose_semi * (cumulative ? repeat_num : 1)`
      - If note out of 0-127, skip this repeat
      - Add note-on event to queue at `now + interval * repeat_num`
      - Store `note_on_time = now` and `original_note/channel` for later note-off matching

#### Note-off mirroring logic

When `midi_delay_schedule_note_off()` is called:
1. `note_off_time = timer_read32()`
2. Scan pending note-on events matching `original_note` and `original_channel`
3. For each match, calculate `held_duration = note_off_time - event.note_on_time`
4. Schedule note-off at `event.fire_time + held_duration`
5. Link note-off's `note_on_sent` to the corresponding note-on event
6. For note-on events already fired: schedule note-off at `now + held_duration` (if note-on was sent)

#### Firing events in tick

In `midi_delay_tick()` (called every scan cycle from `matrix_scan_user()`):
- Iterate pending events, fire any where `timer_read32() >= fire_time`
- For note-ons: `midi_send_noteon(&midi_device, channel, note, velocity)` — raw MIDI send, no recording/display/live-note tracking (avoids recursion and keeps OLED clean)
- For note-offs: only send if corresponding note-on was sent; `midi_send_noteoff(&midi_device, channel, note, 0)` — raw MIDI send
- Remove fired events from queue (compact array)

### 2. Keycodes (`orthomidi5x14.h`)

Range: `0xEF90` to `0xEFF3` (100 keycodes for delay slots 0-99)

```c
#define DELAY_SLOT_BASE     0xEF90  // Delay slot toggle keycodes
#define DELAY_SLOT_1        0xEF90
// ... DELAY_SLOT_2 = 0xEF91, etc.
#define DELAY_SLOT_100      0xEFF3
#define DELAY_SLOT_COUNT    100
```

### 3. Keycode handling (`orthomidi5x14.c` in `process_record_user()`)

```c
// MIDI DELAY TOGGLE (0xEF90-0xEFF3)
if (keycode >= DELAY_SLOT_BASE && keycode < DELAY_SLOT_BASE + DELAY_SLOT_COUNT) {
    if (record->event.pressed) {
        uint8_t slot = keycode - DELAY_SLOT_BASE;
        midi_delay_toggle_slot(slot);
        // OLED: show "Delay N: ON/OFF"
    }
    set_keylog(keycode, record);
    return false;
}
```

### 4. EEPROM layout

```c
#define DELAY_EEPROM_ADDR   43000   // After EQ curve (42200, 26 bytes) and gaming (42000, 100 bytes)
#define DELAY_EEPROM_MAGIC  0xDE01  // Validation magic
// Total: 1602 bytes (100 × 16 + 2 magic)
```

### 5. HID Commands

```c
#define HID_CMD_DELAY_GET_SLOT    0xD6  // Get single slot config: [slot_id] → [16 bytes config]
#define HID_CMD_DELAY_SET_SLOT    0xD7  // Set single slot config: [slot_id, 16 bytes config]
#define HID_CMD_DELAY_SAVE        0xD8  // Save all configs to EEPROM
#define HID_CMD_DELAY_GET_BULK    0xDA  // Get multiple slots: [start, count] → configs
```

### 6. Integration points

- **`process_midi.c`**: In `midi_send_noteon_with_recording()`, after the live note is sent (line ~792), add `midi_delay_schedule_note_on(channel, note, final_velocity)`. In `midi_send_noteoff_with_recording()`, after the note-off processing, add `midi_delay_schedule_note_off(channel, note)`.
- **`orthomidi5x14.c` `matrix_scan_user()`**: Add `midi_delay_tick()` call alongside arpeggiator/sequencer ticks.
- **`rules.mk`**: Add `SRC += midi_delay.c`
- **`orthomidi5x14.c` `process_record_user()`**: Add keycode handler for delay toggle keycodes.
- **`orthomidi5x14.c` OLED**: Add display for delay slot toggle status.

---

## GUI Implementation

### 1. New file: `src/main/python/editor/delay_tab.py`

A new "Delay" tab in the main window, following the same patterns as `velocity_tab.py`.

#### Layout

```
┌─────────────────────────────────────────────────────┐
│ Delay                                               │
├──────────────┬──────────────────────────────────────┤
│ Slot List    │  Slot Settings                       │
│              │                                      │
│ [1] Off      │  Rate Mode: [BPM Synced ▼]          │
│ [2] Off      │  Note Value: [Eighth ▼]             │
│ [3] Off      │  Timing: [Straight ▼]               │
│ ...          │  Fixed Delay: [500] ms               │
│              │  Decay: [50] %  ═══════○             │
│              │  Max Repeats: [4]                    │
│              │  Channel: [Same as Original ▼]       │
│              │  Transpose: [0] semitones             │
│              │  Transpose Mode: [Fixed ▼]           │
│              │                                      │
│              │  [Save to Keyboard]                  │
└──────────────┴──────────────────────────────────────┘
```

#### Key Behaviors

- Left panel: scrollable list of 100 slots showing number + status
- Right panel: edits selected slot's config
- Rate mode combo: switching between BPM-synced and Fixed ms shows/hides relevant controls
- "Save to Keyboard" button: sends all modified slot configs via HID, then triggers EEPROM save
- On tab activation (`rebuild()`): loads all slot configs from firmware

### 2. Registration in `main_window.py`

```python
self.delay_tab = DelayTab()
# Add to editors list:
(self.delay_tab, "Delay"),
```

### 3. Communication protocol (`keyboard_comm.py`)

Add methods:
- `delay_get_slot(slot_id)` → sends `HID_CMD_DELAY_GET_SLOT` with slot_id, returns 16-byte config
- `delay_set_slot(slot_id, config_bytes)` → sends `HID_CMD_DELAY_SET_SLOT` with slot_id + 16 bytes
- `delay_save()` → sends `HID_CMD_DELAY_SAVE`
- `delay_get_bulk(start, count)` → sends `HID_CMD_DELAY_GET_BULK` for efficient loading

### 4. Keycode definitions (`keycodes_v6.py`)

Add entries for `DELAY_1` through `DELAY_100` at `0xEF90`-`0xEFF3` so they show up in the keymap editor's keycode picker.

---

## Implementation Order

1. `midi_delay.h` - Data structures, constants, function declarations
2. `midi_delay.c` - Core delay engine (init, tick, schedule, toggle, EEPROM, HID handlers)
3. `orthomidi5x14.h` - Keycode defines + EEPROM address
4. `orthomidi5x14.c` - Keycode handling in process_record_user + matrix_scan_user tick + OLED
5. `process_midi.c` - Hook note-on/off into delay scheduler
6. `rules.mk` - Add source file
7. `src/main/python/editor/delay_tab.py` - GUI tab
8. `src/main/python/protocol/keyboard_comm.py` - HID protocol methods
9. `src/main/python/main_window.py` - Register tab
10. `src/main/python/keycodes/keycodes_v6.py` - Keycode definitions

## RAM/EEPROM Budget

| Item | Size |
|------|------|
| EEPROM: 100 slot configs | 1,602 bytes |
| RAM: 100 slot configs (cache) | 1,600 bytes |
| RAM: 100 runtime states | 100 bytes |
| RAM: 64 pending events | 1,024 bytes |
| **Total RAM** | **~2,724 bytes** |
| **Total EEPROM** | **~1,602 bytes** |
