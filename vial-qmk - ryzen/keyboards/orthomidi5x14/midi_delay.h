// midi_delay.h - MIDI Delay Effect System
// Repeats note-on/note-off events with configurable timing, decay, channel, and transpose

#ifndef MIDI_DELAY_H
#define MIDI_DELAY_H

#include <stdint.h>
#include <stdbool.h>

// =============================================================================
// CONSTANTS
// =============================================================================

#define DELAY_SLOT_COUNT        100     // Number of independent delay slots
#define DELAY_MAX_PENDING       256     // Maximum pending delay events in queue
#define DELAY_CONFIG_SIZE       16      // Bytes per slot config (for EEPROM alignment)
#define DELAY_EEPROM_ADDR       43000   // EEPROM base address
#define DELAY_EEPROM_MAGIC      0xDE01  // Validation magic
#define DELAY_FIXED_MS_MIN      10      // Minimum fixed delay (ms)
#define DELAY_FIXED_MS_MAX      5000    // Maximum fixed delay (ms)
#define DELAY_TRANSPOSE_MIN     (-48)   // Minimum semitone transpose
#define DELAY_TRANSPOSE_MAX     48      // Maximum semitone transpose

// =============================================================================
// DATA STRUCTURES
// =============================================================================

// Per-slot configuration (16 bytes each, stored in EEPROM)
typedef struct {
    uint8_t  rate_mode;        // 0=BPM-synced, 1=fixed ms
    uint8_t  note_value;       // 0=1/1, 1=1/2, 2=1/4, 3=1/8, 4=1/16
    uint8_t  timing_mode;      // TIMING_MODE_STRAIGHT/TRIPLET/DOTTED (when BPM-synced)
    uint8_t  decay_percent;    // 0-100: velocity reduction per repeat (from original)
    uint16_t fixed_delay_ms;   // 10-5000ms (when fixed ms mode)
    uint8_t  max_repeats;      // 1-255: max delay repeats (0=infinite until decay kills it)
    uint8_t  channel;          // 0=same as original, 1-16=specific MIDI channel
    int8_t   transpose_semi;   // -48 to +48 semitones offset per repeat
    uint8_t  transpose_mode;   // 0=fixed (all repeats same offset), 1=cumulative
    uint8_t  max_active_notes;  // 0=no limit, 1-12=max simultaneous delay notes per slot
    uint8_t  reserved[5];      // Future use, padding to 16 bytes
} delay_slot_config_t;

// Runtime toggle state per slot (not persisted - all off at boot)
typedef struct {
    bool active;               // Toggled on/off by keycode
} delay_slot_runtime_t;

// Pending delay event in the queue
typedef struct {
    uint32_t fire_time;        // When to fire (timer_read32() target)
    uint32_t note_on_time;     // When original note-on was played (for duration mirroring)
    uint8_t  channel;          // MIDI channel to send on
    uint8_t  note;             // MIDI note (after transpose)
    uint8_t  velocity;         // Velocity (after decay)
    uint8_t  is_note_off;      // 0=note-on, 1=note-off
    uint8_t  original_note;    // Original note before transpose (for matching note-offs)
    uint8_t  original_channel; // Original channel (for matching note-offs)
    uint8_t  note_on_sent;     // Was the corresponding note-on actually sent?
    uint8_t  slot_id;          // Which delay slot spawned this
} delay_event_t;

// Full delay system state
typedef struct {
    delay_slot_config_t  configs[DELAY_SLOT_COUNT];   // Slot configurations
    delay_slot_runtime_t runtime[DELAY_SLOT_COUNT];    // Runtime toggle states
    delay_event_t        queue[DELAY_MAX_PENDING];     // Pending event queue
    uint8_t              queue_count;                   // Number of events in queue
    uint16_t             magic;                         // EEPROM validation
} delay_system_t;

extern delay_system_t delay_system;

// =============================================================================
// PUBLIC API
// =============================================================================

// Initialization and persistence
void midi_delay_init(void);
void midi_delay_save(void);
void midi_delay_load(void);
void midi_delay_reset(void);

// Core engine (called from scan loop)
void midi_delay_tick(void);

// Note event hooks (called from process_midi.c)
void midi_delay_schedule_note_on(uint8_t channel, uint8_t note, uint8_t velocity);
void midi_delay_schedule_note_off(uint8_t channel, uint8_t note);

// Slot control
void midi_delay_toggle_slot(uint8_t slot_id);
bool midi_delay_slot_active(uint8_t slot_id);
void midi_delay_clear_queue(void);

// Query helpers
bool midi_delay_any_bpm_synced_active(void);

// HID handlers
void midi_delay_hid_get_slot(uint8_t slot_id, uint8_t *response);
void midi_delay_hid_set_slot(uint8_t slot_id, const uint8_t *data);
void midi_delay_hid_get_bulk(uint8_t start, uint8_t count, uint8_t *data, uint8_t length);

#endif // MIDI_DELAY_H
