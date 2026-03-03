// arpeggiator.c - Arpeggiator implementation for orthomidi5x14
// BPM-synced programmable arpeggiator with preset system

#include QMK_KEYBOARD_H
#include "orthomidi5x14.h"
#include "process_midi.h"
#include "process_dynamic_macro.h"
#include "timer.h"
#include "eeprom.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

// =============================================================================
// GLOBAL STATE
// =============================================================================

// Arpeggiator note tracking array (for gate timing)
arp_note_t arp_notes[MAX_ARP_NOTES];
uint8_t arp_note_count = 0;

// Arpeggiator runtime state
arp_state_t arp_state = {
    .active = false,
    .sync_mode = true,  // Start with sync enabled
    .latch_mode = false,
    .mode = ARPMODE_SINGLE_NOTE_SYNCED,
    .current_preset_id = 0,
    .loaded_preset_id = 255,  // 255 = no preset loaded
    .next_note_time = 0,
    .current_position_16ths = 0,
    .current_note_in_chord = 0,
    .rate_override = 0,
    .master_gate_override = 0,
    .pattern_start_time = 0,
    .anchor_step = 0,
    .last_tap_time = 0,
    .key_held = false,
    .notes_released = false
};

// Step Sequencer runtime state (8 slots)
seq_state_t seq_state[MAX_SEQ_SLOTS] = {
    {.active = false, .sync_mode = true, .current_preset_id = 68, .loaded_preset_id = 255, .rate_override = 0, .master_gate_override = 0, .locked_channel = 0, .locked_velocity_min = 1, .locked_velocity_max = 127, .locked_transpose = 0},
    {.active = false, .sync_mode = true, .current_preset_id = 68, .loaded_preset_id = 255, .rate_override = 0, .master_gate_override = 0, .locked_channel = 0, .locked_velocity_min = 1, .locked_velocity_max = 127, .locked_transpose = 0},
    {.active = false, .sync_mode = true, .current_preset_id = 68, .loaded_preset_id = 255, .rate_override = 0, .master_gate_override = 0, .locked_channel = 0, .locked_velocity_min = 1, .locked_velocity_max = 127, .locked_transpose = 0},
    {.active = false, .sync_mode = true, .current_preset_id = 68, .loaded_preset_id = 255, .rate_override = 0, .master_gate_override = 0, .locked_channel = 0, .locked_velocity_min = 1, .locked_velocity_max = 127, .locked_transpose = 0},
    {.active = false, .sync_mode = true, .current_preset_id = 68, .loaded_preset_id = 255, .rate_override = 0, .master_gate_override = 0, .locked_channel = 0, .locked_velocity_min = 1, .locked_velocity_max = 127, .locked_transpose = 0},
    {.active = false, .sync_mode = true, .current_preset_id = 68, .loaded_preset_id = 255, .rate_override = 0, .master_gate_override = 0, .locked_channel = 0, .locked_velocity_min = 1, .locked_velocity_max = 127, .locked_transpose = 0},
    {.active = false, .sync_mode = true, .current_preset_id = 68, .loaded_preset_id = 255, .rate_override = 0, .master_gate_override = 0, .locked_channel = 0, .locked_velocity_min = 1, .locked_velocity_max = 127, .locked_transpose = 0},
    {.active = false, .sync_mode = true, .current_preset_id = 68, .loaded_preset_id = 255, .rate_override = 0, .master_gate_override = 0, .locked_channel = 0, .locked_velocity_min = 1, .locked_velocity_max = 127, .locked_transpose = 0}
};

// Step Sequencer modifier tracking
bool seq_modifier_held[MAX_SEQ_SLOTS] = {false, false, false, false, false, false, false, false};

// Helper: check if arpeggiator is active (used by process_midi.c to suppress direct MIDI output)
bool arp_is_active(void) {
    return arp_state.active;
}

// Helper: check if any step sequencer slot is active
bool seq_is_any_active(void) {
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) return true;
    }
    return false;
}

// Helper: check if any step sequencer slot is active AND has completed at least one full loop
bool seq_is_any_active_and_looped(void) {
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active && !seq_state[i].deferred_start_pending && seq_state[i].has_looped) return true;
    }
    return false;
}

// =============================================================================
// QUICK BUILD SYSTEM
// =============================================================================

// Quick build state (initialized to all zeros/false)
quick_build_state_t quick_build_state = {
    .mode = QUICK_BUILD_NONE,
    .arp_slot = 0,
    .seq_slot = 0,
    .current_step = 0,
    .note_count = 0,
    .root_note = 0,
    .has_root = false,
    .candidate_root = 0,
    .candidate_ready = false,
    .sustain_held_last_check = false,
    .button_press_time = 0,
    .has_saved_arp_build = {false},
    .active_arp_qb_slot = 255,
    .has_saved_seq_build = {false},
    .setup_param_index = 0,
    .setup_arp_mode = 0,
    .setup_note_value = NOTE_VALUE_SIXTEENTH,
    .setup_timing_mode = TIMING_MODE_STRAIGHT,
    .setup_gate_percent = 80,
    .encoder_chord_held = false
};

// Remember last-used quick build settings across builds
static uint8_t last_arp_mode = 0;
static uint8_t last_note_value = NOTE_VALUE_SIXTEENTH;
static uint8_t last_timing_mode = TIMING_MODE_STRAIGHT;
static uint8_t last_gate_percent = 80;

// =============================================================================
// NOTE POOL - Shared variable-size storage for all active preset notes
// =============================================================================
// 2048 notes × 3 bytes = 6144 bytes total.
// This replaces fixed-size inline note arrays, saving ~7KB RAM vs naive approach
// when supporting 256 arp notes / 512 seq notes.

static arp_preset_note_t note_pool[NOTE_POOL_SIZE];

typedef struct {
    uint16_t offset;   // Start index in note_pool
    uint16_t count;    // Number of notes allocated (0 = free)
} pool_slot_t;

static pool_slot_t pool_slots[POOL_NUM_SLOTS];

// Pool-based RAM storage: active presets with pointer-based notes
active_preset_t arp_active_preset;                  // Arp active slot
active_preset_t seq_active_presets[MAX_SEQ_SLOTS];  // Seq active slots
active_preset_t arp_qb_presets[MAX_ARP_QB_SLOTS];   // Arp quick build storage

// External references
extern uint8_t live_notes[MAX_LIVE_NOTES][3];  // [channel, note, velocity]
extern uint8_t live_note_count;
extern uint32_t current_bpm;  // BPM in format: actual_bpm * 100000
extern uint8_t channel_number;  // Current MIDI channel
extern int8_t transpose_number;  // Global transpose
extern uint8_t he_velocity_min;  // Global HE velocity minimum
extern uint8_t he_velocity_max;  // Global HE velocity maximum
extern uint8_t he_velocity_curve;  // Global HE velocity curve index

// =============================================================================
// NOTE POOL MANAGEMENT
// =============================================================================

// Update all notes pointers after pool compaction
static void pool_update_pointers(void) {
    arp_active_preset.notes = pool_slots[POOL_SLOT_ARP].count > 0 ?
        &note_pool[pool_slots[POOL_SLOT_ARP].offset] : NULL;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        seq_active_presets[i].notes = pool_slots[POOL_SLOT_SEQ(i)].count > 0 ?
            &note_pool[pool_slots[POOL_SLOT_SEQ(i)].offset] : NULL;
    }
    for (uint8_t i = 0; i < MAX_ARP_QB_SLOTS; i++) {
        arp_qb_presets[i].notes = pool_slots[POOL_SLOT_QB(i)].count > 0 ?
            &note_pool[pool_slots[POOL_SLOT_QB(i)].offset] : NULL;
    }
}

// Compact pool: pack all allocations to front, eliminate gaps
static void pool_compact(void) {
    uint16_t write_pos = 0;

    // Process slots in order of their current offset (simple O(n²), n=13)
    for (uint8_t pass = 0; pass < POOL_NUM_SLOTS; pass++) {
        // Find the in-use slot with the lowest offset >= write_pos
        int8_t best = -1;
        uint16_t best_offset = UINT16_MAX;
        for (uint8_t i = 0; i < POOL_NUM_SLOTS; i++) {
            if (pool_slots[i].count > 0 && pool_slots[i].offset < best_offset) {
                best = i;
                best_offset = pool_slots[i].offset;
            }
        }
        if (best < 0) break;  // No more allocations

        // Move this allocation down if there's a gap
        if (pool_slots[best].offset != write_pos) {
            memmove(&note_pool[write_pos], &note_pool[pool_slots[best].offset],
                    pool_slots[best].count * sizeof(arp_preset_note_t));
            pool_slots[best].offset = write_pos;
        }
        write_pos += pool_slots[best].count;
    }

    // Update all notes pointers to reflect new positions
    pool_update_pointers();
}

void note_pool_init(void) {
    memset(pool_slots, 0, sizeof(pool_slots));
    memset(note_pool, 0, sizeof(note_pool));
    // Clear all notes pointers
    arp_active_preset.notes = NULL;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        seq_active_presets[i].notes = NULL;
    }
    for (uint8_t i = 0; i < MAX_ARP_QB_SLOTS; i++) {
        arp_qb_presets[i].notes = NULL;
    }
}

arp_preset_note_t *note_pool_alloc(uint8_t slot_id, uint16_t count) {
    if (count == 0 || slot_id >= POOL_NUM_SLOTS) return NULL;

    // Free existing allocation for this slot
    pool_slots[slot_id].count = 0;

    // Compact to reclaim fragmented space
    pool_compact();

    // Find end of used space
    uint16_t used = 0;
    for (uint8_t i = 0; i < POOL_NUM_SLOTS; i++) {
        if (pool_slots[i].count > 0) {
            uint16_t end = pool_slots[i].offset + pool_slots[i].count;
            if (end > used) used = end;
        }
    }

    if (used + count > NOTE_POOL_SIZE) {
        dprintf("pool: alloc failed, need %d notes but only %d free\n",
                count, NOTE_POOL_SIZE - used);
        return NULL;
    }

    pool_slots[slot_id].offset = used;
    pool_slots[slot_id].count = count;

    arp_preset_note_t *ptr = &note_pool[used];
    memset(ptr, 0, count * sizeof(arp_preset_note_t));
    return ptr;
}

void note_pool_free(uint8_t slot_id) {
    if (slot_id >= POOL_NUM_SLOTS) return;
    pool_slots[slot_id].count = 0;
    pool_slots[slot_id].offset = 0;
    // Update the corresponding preset's notes pointer
    pool_update_pointers();
}

// Load helpers: copy from EEPROM-format struct to active preset using pool
// Converts 7-bit timing format → 8-bit timing format
void load_arp_to_active(const arp_preset_t *src, active_preset_t *dest, uint8_t pool_slot) {
    arp_preset_note_t *notes = note_pool_alloc(pool_slot, src->note_count);
    if (!notes && src->note_count > 0) {
        dprintf("pool: failed to allocate %d notes for arp\n", src->note_count);
        return;
    }

    dest->preset_type = src->preset_type;
    dest->note_count = src->note_count;
    dest->pattern_length_16ths = src->pattern_length_16ths;
    dest->gate_length_percent = src->gate_length_percent;
    dest->timing_mode = src->timing_mode;
    dest->note_value = src->note_value;
    dest->magic = src->magic;
    dest->notes = notes;

    // Convert notes from 7-bit to 8-bit timing format
    for (uint16_t i = 0; i < src->note_count; i++) {
        dest->notes[i].packed_timing_vel = NOTE_CONVERT_7TO8(src->notes[i].packed_timing_vel);
        dest->notes[i].note_octave = src->notes[i].note_octave;
    }
}

void load_seq_to_active(const seq_preset_t *src, active_preset_t *dest, uint8_t pool_slot) {
    arp_preset_note_t *notes = note_pool_alloc(pool_slot, src->note_count);
    if (!notes && src->note_count > 0) {
        dprintf("pool: failed to allocate %d notes for seq\n", src->note_count);
        return;
    }

    dest->preset_type = src->preset_type;
    dest->note_count = src->note_count;
    dest->pattern_length_16ths = src->pattern_length_16ths;
    dest->gate_length_percent = src->gate_length_percent;
    dest->timing_mode = src->timing_mode;
    dest->note_value = src->note_value;
    dest->magic = src->magic;
    dest->notes = notes;

    // Convert notes from 7-bit to 8-bit timing format
    for (uint16_t i = 0; i < src->note_count; i++) {
        dest->notes[i].packed_timing_vel = NOTE_CONVERT_7TO8(src->notes[i].packed_timing_vel);
        dest->notes[i].note_octave = src->notes[i].note_octave;
    }
}

// Validate active preset (8-bit timing format)
bool active_validate_arp(const active_preset_t *preset) {
    if (!preset || !preset->notes) {
        dprintf("arp: active validate failed - NULL\n");
        return false;
    }
    if (preset->magic != ARP_PRESET_MAGIC) {
        dprintf("arp: active validate failed - bad magic 0x%04X\n", preset->magic);
        return false;
    }
    if (preset->note_count > MAX_ACTIVE_ARP_NOTES) {
        dprintf("arp: active validate failed - note_count %d > %d\n",
                preset->note_count, MAX_ACTIVE_ARP_NOTES);
        return false;
    }
    if (preset->gate_length_percent > 100) {
        dprintf("arp: active validate failed - gate %d > 100\n", preset->gate_length_percent);
        return false;
    }
    if (preset->pattern_length_16ths < 1 || preset->pattern_length_16ths > MAX_ACTIVE_ARP_STEPS) {
        dprintf("arp: active validate failed - pattern_length %d\n", preset->pattern_length_16ths);
        return false;
    }
    for (uint16_t i = 0; i < preset->note_count; i++) {
        uint8_t timing = NOTE_GET_TIMING(preset->notes[i].packed_timing_vel);
        if (timing >= preset->pattern_length_16ths) {
            dprintf("arp: active validate failed - note[%d] timing %d >= length %d\n",
                    i, timing, preset->pattern_length_16ths);
            return false;
        }
    }
    return true;
}

bool active_validate_seq(const active_preset_t *preset) {
    if (!preset || !preset->notes) {
        dprintf("seq: active validate failed - NULL\n");
        return false;
    }
    if (preset->magic != ARP_PRESET_MAGIC) {
        dprintf("seq: active validate failed - bad magic 0x%04X\n", preset->magic);
        return false;
    }
    if (preset->note_count > MAX_ACTIVE_SEQ_NOTES) {
        dprintf("seq: active validate failed - note_count %d > %d\n",
                preset->note_count, MAX_ACTIVE_SEQ_NOTES);
        return false;
    }
    if (preset->gate_length_percent > 100) {
        dprintf("seq: active validate failed - gate %d > 100\n", preset->gate_length_percent);
        return false;
    }
    if (preset->pattern_length_16ths < 1 || preset->pattern_length_16ths > MAX_ACTIVE_SEQ_STEPS) {
        dprintf("seq: active validate failed - pattern_length %d\n", preset->pattern_length_16ths);
        return false;
    }
    for (uint16_t i = 0; i < preset->note_count; i++) {
        uint16_t timing = NOTE_GET_TIMING(preset->notes[i].packed_timing_vel);
        if (timing >= preset->pattern_length_16ths) {
            dprintf("seq: active validate failed - note[%d] timing %d >= length %d\n",
                    i, timing, preset->pattern_length_16ths);
            return false;
        }
    }
    return true;
}

// =============================================================================
// LIVE NOTE PRESS ORDER TRACKING (for arpeggiator modes)
// =============================================================================
// Tracks the sequence number of each live note to determine press order.
// The most recently pressed note still held has the highest sequence number.

static uint32_t live_note_sequence[MAX_LIVE_NOTES];  // Sequence number for each live note slot
static uint32_t live_note_next_sequence = 1;         // Next sequence number to assign

// Called when a note is added to live_notes (hooked from process_midi.c)
void arp_track_note_pressed(uint8_t live_note_index) {
    if (live_note_index < MAX_LIVE_NOTES) {
        live_note_sequence[live_note_index] = live_note_next_sequence++;
    }
}

// Called when a note is removed and another is moved to fill the gap
void arp_track_note_moved(uint8_t from_index, uint8_t to_index) {
    if (from_index < MAX_LIVE_NOTES && to_index < MAX_LIVE_NOTES) {
        live_note_sequence[to_index] = live_note_sequence[from_index];
        live_note_sequence[from_index] = 0;  // Clear stale source slot
    }
}

// Reset sequence tracking (called when all live notes are force-cleared)
void arp_reset_note_sequence(void) {
    memset(live_note_sequence, 0, sizeof(live_note_sequence));
    live_note_next_sequence = 1;
}

// Get index of most recently pressed note that's still held
static uint8_t get_most_recent_live_note_index(void) {
    if (live_note_count == 0) return 0;

    uint8_t most_recent_idx = 0;
    uint32_t highest_seq = 0;

    for (uint8_t i = 0; i < live_note_count; i++) {
        if (live_note_sequence[i] > highest_seq) {
            highest_seq = live_note_sequence[i];
            most_recent_idx = i;
        }
    }

    return most_recent_idx;
}

// Get indices of live notes sorted by press order (oldest first)
static void sort_live_notes_by_press_order(uint8_t sorted_indices[], uint8_t count) {
    // Create array of indices
    for (uint8_t i = 0; i < count; i++) {
        sorted_indices[i] = i;
    }

    // Simple bubble sort by sequence number (ascending = oldest first)
    for (uint8_t i = 0; i < count - 1; i++) {
        for (uint8_t j = 0; j < count - i - 1; j++) {
            if (live_note_sequence[sorted_indices[j]] > live_note_sequence[sorted_indices[j+1]]) {
                uint8_t temp = sorted_indices[j];
                sorted_indices[j] = sorted_indices[j+1];
                sorted_indices[j+1] = temp;
            }
        }
    }
}

// =============================================================================
// CHORD UNSYNCED PER-NOTE STATE (each held note runs its own arp independently)
// =============================================================================

typedef struct {
    uint8_t midi_note;        // MIDI note number this is tracking (0 = slot inactive)
    uint8_t channel;          // MIDI channel
    uint32_t next_note_time;  // When to play next arp step for this note
    uint32_t anchor_start_time;  // When this note's pattern started (for anchored timing)
    uint16_t current_position_16ths;  // This note's position in the pattern
    bool active;
} unsynced_note_state_t;

#define MAX_UNSYNCED_NOTES MAX_LIVE_NOTES
static unsynced_note_state_t unsynced_notes[MAX_UNSYNCED_NOTES];
static uint8_t unsynced_note_count = 0;

// Reset all unsynced note states (called on mode change, arp start, notes released)
static void reset_unsynced_notes(void) {
    memset(unsynced_notes, 0, sizeof(unsynced_notes));
    unsynced_note_count = 0;
}

// Find unsynced state for a specific MIDI note, returns -1 if not found
static int8_t find_unsynced_note(uint8_t midi_note, uint8_t channel) {
    for (uint8_t i = 0; i < MAX_UNSYNCED_NOTES; i++) {
        if (unsynced_notes[i].active &&
            unsynced_notes[i].midi_note == midi_note &&
            unsynced_notes[i].channel == channel) {
            return i;
        }
    }
    return -1;
}

// Add a new unsynced note state, returns slot index or -1 if full
static int8_t add_unsynced_note(uint8_t midi_note, uint8_t channel, uint32_t start_time) {
    // Check if already tracked
    int8_t existing = find_unsynced_note(midi_note, channel);
    if (existing >= 0) return existing;

    // Find empty slot
    for (uint8_t i = 0; i < MAX_UNSYNCED_NOTES; i++) {
        if (!unsynced_notes[i].active) {
            unsynced_notes[i].midi_note = midi_note;
            unsynced_notes[i].channel = channel;
            unsynced_notes[i].next_note_time = start_time;
            unsynced_notes[i].anchor_start_time = start_time;  // Anchor for drift-free timing
            unsynced_notes[i].current_position_16ths = 0;
            unsynced_notes[i].active = true;
            unsynced_note_count++;
            return i;
        }
    }
    return -1;  // No available slots
}

// Sync unsynced note tracking with current live_notes array
// Adds new notes, removes notes no longer held
static void sync_unsynced_with_live_notes(uint32_t current_time) {
    // Mark notes that are no longer in live_notes for removal
    for (uint8_t i = 0; i < MAX_UNSYNCED_NOTES; i++) {
        if (!unsynced_notes[i].active) continue;

        bool found = false;
        for (uint8_t j = 0; j < live_note_count; j++) {
            if (live_notes[j][1] == unsynced_notes[i].midi_note &&
                live_notes[j][0] == unsynced_notes[i].channel) {
                found = true;
                break;
            }
        }
        if (!found) {
            unsynced_notes[i].active = false;
            unsynced_note_count--;
        }
    }

    // Add new notes that aren't being tracked yet
    for (uint8_t j = 0; j < live_note_count; j++) {
        add_unsynced_note(live_notes[j][1], live_notes[j][0], current_time);
    }
}

// =============================================================================
// ARP NOTES TRACKING (for gate timing)
// =============================================================================

void add_arp_note(uint8_t channel, uint8_t note, uint8_t velocity, uint32_t note_off_time) {
    if (arp_note_count >= MAX_ARP_NOTES) {
        dprintf("arp: note buffer full, cannot add note\n");
        return;
    }

    // Find an empty slot
    for (uint8_t i = 0; i < MAX_ARP_NOTES; i++) {
        if (!arp_notes[i].active) {
            arp_notes[i].channel = channel;
            arp_notes[i].note = note;
            arp_notes[i].velocity = velocity;
            arp_notes[i].note_off_time = note_off_time;
            arp_notes[i].active = true;
            arp_notes[i].from_seq = false;
            arp_notes[i].seq_slot = 0;
            arp_note_count++;
            dprintf("arp: added note ch:%d note:%d vel:%d off_time:%lu (count:%d)\n",
                    channel, note, velocity, note_off_time, arp_note_count);
            return;
        }
    }
}

// Add a sequencer note to the gate tracking array (marked as macro note)
static void add_seq_note(uint8_t channel, uint8_t note, uint8_t velocity, uint32_t note_off_time, uint8_t slot) {
    if (arp_note_count >= MAX_ARP_NOTES) {
        dprintf("seq: note buffer full, cannot add note\n");
        return;
    }

    for (uint8_t i = 0; i < MAX_ARP_NOTES; i++) {
        if (!arp_notes[i].active) {
            arp_notes[i].channel = channel;
            arp_notes[i].note = note;
            arp_notes[i].velocity = velocity;
            arp_notes[i].note_off_time = note_off_time;
            arp_notes[i].active = true;
            arp_notes[i].from_seq = true;
            arp_notes[i].seq_slot = slot;
            arp_note_count++;
            dprintf("seq: added note ch:%d note:%d vel:%d slot:%d off_time:%lu (count:%d)\n",
                    channel, note, velocity, slot, note_off_time, arp_note_count);
            return;
        }
    }
}

void remove_arp_note(uint8_t channel, uint8_t note) {
    for (uint8_t i = 0; i < MAX_ARP_NOTES; i++) {
        if (arp_notes[i].active &&
            arp_notes[i].channel == channel &&
            arp_notes[i].note == note) {
            arp_notes[i].active = false;
            arp_note_count--;
            dprintf("arp: removed note ch:%d note:%d (remaining:%d)\n",
                    channel, note, arp_note_count);
            return;
        }
    }
}

// Check for notes that need gate-off and send note-offs
void process_arp_note_offs(void) {
    if (arp_note_count == 0) return;

    uint32_t current_time = timer_read32();

    for (uint8_t i = 0; i < MAX_ARP_NOTES; i++) {
        if (arp_notes[i].active && current_time >= arp_notes[i].note_off_time) {
            // Time to send note-off
            if (arp_notes[i].from_seq) {
                // Sequencer note: use macro-style note-off (not recorded by looper)
                midi_send_noteoff_seq_macro(arp_notes[i].channel,
                                            arp_notes[i].note,
                                            arp_notes[i].velocity,
                                            arp_notes[i].seq_slot);
            } else {
                // Arpeggiator note: use normal arp note-off
                midi_send_noteoff_arp(arp_notes[i].channel,
                                     arp_notes[i].note,
                                     arp_notes[i].velocity);
            }

            // Mark as inactive
            arp_notes[i].active = false;
            arp_note_count--;

            dprintf("arp: gated off note ch:%d note:%d from_seq:%d\n",
                    arp_notes[i].channel, arp_notes[i].note, arp_notes[i].from_seq);
        }
    }
}

// =============================================================================
// PRESET DEFINITIONS
// =============================================================================

// =============================================================================
// LAZY-LOADING PRESET SYSTEM
// =============================================================================

// Load arpeggiator preset into active slot (lazy-load from EEPROM or factory data)
// Loads into temp buffer (7-bit format), converts to active preset (8-bit format) via pool
bool arp_load_preset_into_slot(uint8_t preset_id) {
    // Quick build sentinel: RAM already contains the custom pattern, don't reload
    if (preset_id == PRESET_ID_QUICK_BUILD) {
        dprintf("arp: quick build preset in RAM, skipping load\n");
        arp_state.loaded_preset_id = PRESET_ID_QUICK_BUILD;
        return true;
    }

    if (preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: load_preset_into_slot - invalid preset_id %d (max %d)\n", preset_id, MAX_ARP_PRESETS - 1);
        return false;
    }

    // Check if already loaded
    if (arp_state.loaded_preset_id == preset_id) {
        dprintf("arp: preset %d already loaded\n", preset_id);
        return true;
    }

    // Load into temp buffer (7-bit EEPROM format)
    arp_preset_t temp;
    if (preset_id >= USER_ARP_PRESET_START) {
        if (!arp_load_preset_from_eeprom(preset_id, &temp)) {
            dprintf("arp: failed to load user preset %d from EEPROM\n", preset_id);
            return false;
        }
    } else {
        arp_load_factory_preset(preset_id, &temp);
    }

    // Convert 7-bit → 8-bit and load into active preset via pool
    load_arp_to_active(&temp, &arp_active_preset, POOL_SLOT_ARP);

    arp_state.loaded_preset_id = preset_id;
    dprintf("arp: loaded preset %d into active slot\n", preset_id);
    return true;
}

// Load sequencer preset into specified slot (lazy-load from EEPROM or factory data)
// Loads into temp buffer (7-bit format), converts to active preset (8-bit format) via pool
bool seq_load_preset_into_slot(uint8_t preset_id, uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) {
        dprintf("seq: load_preset_into_slot - invalid slot %d\n", slot);
        return false;
    }

    // Quick build sentinel: RAM already contains the custom pattern, don't reload
    if (preset_id == PRESET_ID_QUICK_BUILD) {
        dprintf("seq: quick build preset in RAM for slot %d, skipping load\n", slot);
        seq_state[slot].loaded_preset_id = PRESET_ID_QUICK_BUILD;
        return true;
    }

    if (preset_id < 68 || preset_id >= MAX_SEQ_PRESETS) {
        dprintf("seq: load_preset_into_slot - invalid preset_id %d\n", preset_id);
        return false;
    }

    // Check if already loaded in this slot
    if (seq_state[slot].loaded_preset_id == preset_id) {
        dprintf("seq: preset %d already loaded in slot %d\n", preset_id, slot);
        return true;
    }

    // Load into temp buffer (7-bit EEPROM format)
    seq_preset_t temp;
    if (preset_id >= USER_SEQ_PRESET_START) {
        if (!seq_load_preset_from_eeprom(preset_id, &temp)) {
            dprintf("seq: failed to load user preset %d from EEPROM\n", preset_id);
            return false;
        }
    } else {
        uint8_t factory_id = preset_id - 68;
        seq_load_factory_preset(factory_id, &temp);
    }

    // Convert 7-bit → 8-bit and load into active preset via pool
    load_seq_to_active(&temp, &seq_active_presets[slot], POOL_SLOT_SEQ(slot));

    seq_state[slot].loaded_preset_id = preset_id;
    dprintf("seq: loaded preset %d into slot %d\n", preset_id, slot);
    return true;
}

// Find an available sequencer slot (-1 if none available)
int8_t seq_find_available_slot(void) {
    // First pass: prefer slots without saved quick build data (avoid overwriting QB presets)
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (!seq_state[i].active && !quick_build_state.has_saved_seq_build[i]) {
            return i;
        }
    }
    // Second pass: fall back to any inactive slot (even with saved QB data)
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (!seq_state[i].active) {
            return i;
        }
    }
    return -1;  // No available slots
}

// Find which slot (if any) is playing a specific preset (-1 if not found)
int8_t seq_find_slot_with_preset(uint8_t preset_id) {
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active && seq_state[i].current_preset_id == preset_id) {
            return i;
        }
    }
    return -1;  // Preset not currently playing
}

// Smart preset selection: toggle if playing, or start in new slot
void seq_select_preset(uint8_t preset_id) {
    if (preset_id < 68 || preset_id >= MAX_SEQ_PRESETS) {
        dprintf("seq: invalid preset id %d\n", preset_id);
        return;
    }

    // Check if this preset is already playing
    int8_t existing_slot = seq_find_slot_with_preset(preset_id);

    if (existing_slot >= 0) {
        if (seq_state[existing_slot].deferred_start_pending) {
            // Double-press while deferred: force start at next step of running seq (polyrhythm mode)
            seq_state[existing_slot].deferred_start_pending = false;
            seq_state[existing_slot].has_looped = false;
            seq_state[existing_slot].current_position_16ths = 0;
            // Find a running seq and align to its next step time
            bool found_running = false;
            for (uint8_t s = 0; s < MAX_SEQ_SLOTS; s++) {
                if (s == existing_slot) continue;
                if (seq_state[s].active && !seq_state[s].deferred_start_pending) {
                    seq_state[existing_slot].pattern_start_time = seq_state[s].next_note_time;
                    seq_state[existing_slot].next_note_time = seq_state[s].next_note_time;
                    found_running = true;
                    dprintf("seq: force-start preset %d at next step of slot %d (polyrhythm)\n", preset_id, s);
                    break;
                }
            }
            if (!found_running) {
                // No running seq found, start immediately
                uint32_t now = timer_read32();
                seq_state[existing_slot].pattern_start_time = now;
                seq_state[existing_slot].next_note_time = now;
                dprintf("seq: force-started preset %d immediately (no running seq)\n", preset_id);
            }
        } else {
            // Preset is playing: toggle it off
            seq_stop(existing_slot);
            dprintf("seq: toggled OFF preset %d from slot %d\n", preset_id, existing_slot);
        }
    } else {
        // Preset not playing: start in next available slot
        // (seq_start will find the slot and load the preset)
        seq_start(preset_id);
    }
}

// Forward declaration - actual implementation in arp_factory_presets.c
// (kept here as stub for now, will be removed when linking with factory preset file)

// =============================================================================
// CORE ARPEGGIATOR LOGIC
// =============================================================================

// Get effective BPM (with fallback to 120 if BPM is 0)
static uint32_t get_effective_bpm(void) {
    return (current_bpm == 0) ? 12000000 : current_bpm;  // 120.00000 BPM default
}

// Unpack a note structure to extract individual fields
typedef struct {
    uint16_t timing;         // uint16_t for 8-bit timing support (0-255)
    uint8_t velocity;
    int8_t note_index;      // For arp: interval with sign; For seq: note 0-11
    int8_t octave_offset;
} unpacked_note_t;

// Unpack from 8-bit timing format (active presets in RAM)
static void unpack_note(const arp_preset_note_t *packed, unpacked_note_t *unpacked, bool is_arpeggiator) {
    unpacked->timing = NOTE_GET_TIMING(packed->packed_timing_vel);
    unpacked->velocity = NOTE_GET_VELOCITY(packed->packed_timing_vel);

    uint8_t note_val = NOTE_GET_NOTE(packed->note_octave);
    unpacked->octave_offset = NOTE_GET_OCTAVE(packed->note_octave);

    if (is_arpeggiator) {
        uint8_t sign = NOTE_GET_SIGN(packed->packed_timing_vel);
        unpacked->note_index = sign ? -(int8_t)note_val : (int8_t)note_val;
    } else {
        unpacked->note_index = note_val;
    }
}

// Unpack from 7-bit timing format (EEPROM/factory presets)
static void unpack_note_7bit(const arp_preset_note_t *packed, unpacked_note_t *unpacked, bool is_arpeggiator) {
    unpacked->timing = NOTE7_GET_TIMING(packed->packed_timing_vel);
    unpacked->velocity = NOTE7_GET_VELOCITY(packed->packed_timing_vel);

    uint8_t note_val = NOTE_GET_NOTE(packed->note_octave);
    unpacked->octave_offset = NOTE_GET_OCTAVE(packed->note_octave);

    if (is_arpeggiator) {
        uint8_t sign = NOTE7_GET_SIGN(packed->packed_timing_vel);
        unpacked->note_index = sign ? -(int8_t)note_val : (int8_t)note_val;
    } else {
        unpacked->note_index = note_val;
    }
}

// =============================================================================
// HIGH-PRECISION ANCHORED TIMING
// =============================================================================
//
// Computes the exact millisecond offset for step N using 64-bit math and the
// full-precision BPM value (stored as BPM * 100000). This eliminates cumulative
// drift that occurred with the old approach of integer-truncating BPM then adding
// a truncated ms_per_step to current_time each step.
//
// Formula: offset_ms = (step * 6,000,000,000 * multiplier * timing_num)
//                      / (4 * bpm_format * timing_den)
//
// Where bpm_format = actual_bpm * 100000 (e.g., 120.55 BPM = 12055000)
//
// The anchored pattern is:
//   next_note_time = pattern_start_time + compute_step_time_offset(next_step, ...)
// Instead of the drifting:
//   next_note_time = current_time + ms_per_step
//
// At the pattern loop boundary, pattern_start_time advances by the exact pattern
// duration rather than resetting to current_time, maintaining alignment.
// =============================================================================

// Compute millisecond offset for step N at the given note value and timing mode.
// Uses full-precision BPM (no integer truncation).
static uint32_t compute_step_time_offset(uint16_t step, uint8_t note_value, uint8_t timing_mode) {
    uint32_t bpm = get_effective_bpm();  // BPM * 100000 format

    // Note value multiplier (how many 16ths per step)
    uint8_t multiplier = 1;
    switch (note_value) {
        case NOTE_VALUE_QUARTER:   multiplier = 4; break;
        case NOTE_VALUE_EIGHTH:    multiplier = 2; break;
        case NOTE_VALUE_SIXTEENTH:
        default:                   multiplier = 1; break;
    }

    // Timing mode numerator/denominator
    uint8_t timing_num = 1, timing_den = 1;
    if (timing_mode & TIMING_MODE_TRIPLET) {
        timing_num = 2; timing_den = 3;  // 2/3 duration
    } else if (timing_mode & TIMING_MODE_DOTTED) {
        timing_num = 3; timing_den = 2;  // 3/2 duration
    }

    // 64-bit calculation: (step * 6,000,000,000 * multiplier * timing_num) / (4 * bpm * timing_den)
    // Max numerator: 127 * 6e9 * 4 * 3 = 9.144e12, well within uint64_t range
    uint64_t numerator = (uint64_t)step * 6000000000ULL * multiplier * timing_num;
    uint64_t denominator = (uint64_t)4 * bpm * timing_den;

    return (uint32_t)(numerator / denominator);
}

// Calculate milliseconds per step for arpeggiator (used for gate duration calculations).
// Uses arp_state.rate_override if set, otherwise uses preset values.
static uint32_t get_ms_per_16th(const active_preset_t *preset) {
    uint8_t note_value, timing_mode;
    if (arp_state.rate_override != 0) {
        note_value = arp_state.rate_override & ~TIMING_MODE_MASK;
        timing_mode = arp_state.rate_override & TIMING_MODE_MASK;
    } else {
        note_value = preset->note_value;
        timing_mode = preset->timing_mode;
    }
    return compute_step_time_offset(1, note_value, timing_mode);
}

// Compute anchored next_note_time for arpeggiator.
// Returns: pattern_start_time + exact offset for the given step number.
static uint32_t arp_anchored_next_time(const active_preset_t *preset, uint16_t step) {
    uint8_t note_value, timing_mode;
    if (arp_state.rate_override != 0) {
        note_value = arp_state.rate_override & ~TIMING_MODE_MASK;
        timing_mode = arp_state.rate_override & TIMING_MODE_MASK;
    } else {
        note_value = preset->note_value;
        timing_mode = preset->timing_mode;
    }
    return arp_state.pattern_start_time + compute_step_time_offset(step, note_value, timing_mode);
}

// Calculate milliseconds per step for sequencer (used for gate duration calculations).
// Uses seq_state[slot].rate_override if set, otherwise uses preset values.
static uint32_t seq_get_ms_per_16th(const active_preset_t *preset, uint8_t slot) {
    uint8_t note_value, timing_mode;
    if (slot < MAX_SEQ_SLOTS && seq_state[slot].rate_override != 0) {
        note_value = seq_state[slot].rate_override & ~TIMING_MODE_MASK;
        timing_mode = seq_state[slot].rate_override & TIMING_MODE_MASK;
    } else {
        note_value = preset->note_value;
        timing_mode = preset->timing_mode;
    }
    return compute_step_time_offset(1, note_value, timing_mode);
}

// Compute anchored next_note_time for sequencer slot.
// Returns: pattern_start_time + exact offset for the given step number.
static uint32_t seq_anchored_next_time(const active_preset_t *preset, uint8_t slot, uint16_t step) {
    uint8_t note_value, timing_mode;
    if (slot < MAX_SEQ_SLOTS && seq_state[slot].rate_override != 0) {
        note_value = seq_state[slot].rate_override & ~TIMING_MODE_MASK;
        timing_mode = seq_state[slot].rate_override & TIMING_MODE_MASK;
    } else {
        note_value = preset->note_value;
        timing_mode = preset->timing_mode;
    }
    return seq_state[slot].pattern_start_time + compute_step_time_offset(step, note_value, timing_mode);
}


void arp_init(void) {
    // Clear arp notes
    memset(arp_notes, 0, sizeof(arp_notes));
    arp_note_count = 0;

    // Initialize note pool and clear active preset headers
    note_pool_init();
    memset(&arp_active_preset, 0, sizeof(active_preset_t));
    memset(seq_active_presets, 0, sizeof(seq_active_presets));
    memset(arp_qb_presets, 0, sizeof(arp_qb_presets));

    // Reset press order tracking (prevents stale sequence data)
    memset(live_note_sequence, 0, sizeof(live_note_sequence));
    live_note_next_sequence = 1;

    // Reset arpeggiator state
    arp_state.active = false;
    arp_state.latch_mode = false;
    arp_state.current_preset_id = 0;
    arp_state.loaded_preset_id = 255;  // No preset loaded
    arp_state.sync_mode = true;
    arp_state.mode = ARPMODE_SINGLE_NOTE_SYNCED;
    arp_state.rate_override = 0;
    arp_state.master_gate_override = 0;

    // Reset chord unsynced per-note tracking
    reset_unsynced_notes();

    // Reset sequencer states
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        seq_state[i].active = false;
        seq_state[i].sync_mode = true;
        seq_state[i].current_preset_id = 68;  // Default to first seq preset
        seq_state[i].loaded_preset_id = 255;  // No preset loaded
        seq_state[i].rate_override = 0;
        seq_state[i].master_gate_override = 0;
        seq_state[i].locked_channel = 0;
        seq_state[i].locked_velocity_min = 1;
        seq_state[i].locked_velocity_max = 127;
        seq_state[i].locked_transpose = 0;
        seq_modifier_held[i] = false;
    }

    dprintf("arp: initialized with lazy-loading preset system (64 total presets)\n");
}

void arp_start(uint8_t preset_id) {
    // QUICK BUILD HOOK: Cancel quick build if active (arp play takes priority)
    if (quick_build_is_active()) {
        quick_build_cancel();
    }

    if (preset_id != PRESET_ID_QUICK_BUILD && preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: invalid preset id %d (max %d)\n", preset_id, MAX_ARP_PRESETS - 1);
        return;
    }

    // If already active and switching presets
    if (arp_state.active && preset_id != arp_state.current_preset_id) {
        // Calculate relative position in old pattern BEFORE loading new preset
        uint16_t old_length = arp_active_preset.pattern_length_16ths;
        float progress = (float)arp_state.current_position_16ths / old_length;

        // Lazy-load the new preset into active slot
        if (!arp_load_preset_into_slot(preset_id)) {
            dprintf("arp: failed to load preset %d\n", preset_id);
            return;
        }

        // Handle preset switching based on sync mode
        if (arp_state.sync_mode) {
            // Apply progress to new pattern
            arp_state.current_position_16ths = (uint16_t)(progress * arp_active_preset.pattern_length_16ths);
            dprintf("arp: switching preset with sync, progress: %d%%\n", (int)(progress * 100));
        } else {
            // Unsynced: restart from beginning
            arp_state.current_position_16ths = 0;
            arp_state.pattern_start_time = timer_read32();
        }
    } else {
        // Lazy-load the preset into active slot
        if (!arp_load_preset_into_slot(preset_id)) {
            dprintf("arp: failed to load preset %d\n", preset_id);
            return;
        }

        // Starting fresh
        arp_state.current_position_16ths = 0;
        arp_state.pattern_start_time = timer_read32();

        // If sync mode, wait for next beat to start
        if (arp_state.sync_mode) {
            // TODO: Sync to BPM beat boundary
            // For now, start immediately
        }
    }

    // Flush any notes that had their note-on sent before arp was active
    // This prevents stuck notes when keys are held before arp activates
    extern void flush_live_notes_for_arp(void);
    if (!arp_state.active) {
        flush_live_notes_for_arp();
    }

    arp_state.current_preset_id = preset_id;
    arp_state.active = true;
    arp_state.current_note_in_chord = 0;
    arp_state.anchor_step = 0;
    arp_state.notes_released = false;

    // Defer start to next seq step if synced mode and a step sequencer is running
    bool is_synced_mode = (arp_state.mode == ARPMODE_SINGLE_NOTE_SYNCED ||
                           arp_state.mode == ARPMODE_CHORD_SYNCED ||
                           arp_state.mode == ARPMODE_CHORD_ADVANCED);
    if (is_synced_mode && seq_is_any_active()) {
        arp_state.deferred_start_pending = true;
        arp_state.next_note_time = UINT32_MAX;  // Don't play until seq step releases us
        dprintf("arp: deferred start (synced mode + seq active)\n");
    } else {
        arp_state.deferred_start_pending = false;
        arp_state.next_note_time = timer_read32();  // Start immediately
    }

    // Reset chord unsynced per-note tracking on fresh start
    reset_unsynced_notes();

    dprintf("arp: started preset %d\n", preset_id);
}

void arp_stop(void) {
    if (!arp_state.active) return;

    dprintf("arp: stopping\n");

    arp_state.active = false;
    arp_state.latch_mode = false;
    arp_state.key_held = false;
    arp_state.notes_released = false;
    arp_state.deferred_start_pending = false;

    // Immediately send note-offs for all active arp notes to prevent stuck notes
    for (uint8_t i = 0; i < MAX_ARP_NOTES; i++) {
        if (arp_notes[i].active) {
            if (arp_notes[i].from_seq) {
                midi_send_noteoff_seq_macro(arp_notes[i].channel,
                                            arp_notes[i].note,
                                            arp_notes[i].velocity,
                                            arp_notes[i].seq_slot);
            } else {
                midi_send_noteoff_arp(arp_notes[i].channel,
                                     arp_notes[i].note,
                                     arp_notes[i].velocity);
            }
            arp_notes[i].active = false;
            arp_note_count--;
            dprintf("arp: force-off note ch:%d note:%d from_seq:%d\n",
                    arp_notes[i].channel, arp_notes[i].note, arp_notes[i].from_seq);
        }
    }
    arp_note_count = 0;  // Safety reset
}

void arp_update(void) {
    // Process any notes that need to be gated off
    process_arp_note_offs();

    // If not active, nothing to do
    if (!arp_state.active) return;

    // Use the active preset slot (already loaded by arp_start)
    active_preset_t *preset = &arp_active_preset;

    // Check requirements based on preset type
    if (preset->preset_type == PRESET_TYPE_ARPEGGIATOR) {
        if (live_note_count == 0 && !loop_deferred_record_stop_pending) {
            // No notes held - mark for pattern restart when notes return
            // Don't stop: arp stays armed while button is held or latched
            // (Skip this early return if deferred stop is pending so it can execute at step boundary)
            arp_state.notes_released = true;
            return;
        }

        // Notes are held - check if we need to restart pattern from step 0
        if (arp_state.notes_released) {
            arp_state.notes_released = false;
            arp_state.current_position_16ths = 0;
            arp_state.current_note_in_chord = 0;
            arp_state.anchor_step = 0;
            arp_state.pattern_start_time = timer_read32();
            arp_state.next_note_time = timer_read32();  // Play immediately
            reset_unsynced_notes();  // Clear per-note states for chord unsynced
            dprintf("arp: pattern restart (new note after release)\n");
        }
    }
    // Step sequencer plays independently, no live notes required

    // =========================================================================
    // CHORD UNSYNCED: Each held note runs its own independent arp pattern
    // Handled separately because each note has its own timing/position
    // =========================================================================
    if (preset->preset_type == PRESET_TYPE_ARPEGGIATOR &&
        arp_state.mode == ARPMODE_CHORD_UNSYNCED) {

        uint32_t current_time = timer_read32();

        // Sync per-note tracking with current live_notes
        sync_unsynced_with_live_notes(current_time);

        // Gate/timing setup
        uint8_t gate_percent = (arp_state.master_gate_override > 0) ?
                               arp_state.master_gate_override :
                               preset->gate_length_percent;
        uint32_t ms_per_16th = get_ms_per_16th(preset);
        uint32_t gate_duration_ms = (ms_per_16th * gate_percent) / 100;

        // Process each note independently
        for (uint8_t u = 0; u < MAX_UNSYNCED_NOTES; u++) {
            if (!unsynced_notes[u].active) continue;
            if (current_time < unsynced_notes[u].next_note_time) continue;

            // Find preset notes at this note's current position
            for (uint16_t i = 0; i < preset->note_count; i++) {
                unpacked_note_t unpacked;
                unpack_note(&preset->notes[i], &unpacked, true);

                if (unpacked.timing != unsynced_notes[u].current_position_16ths) continue;

                // Calculate final note: this live note + preset offset
                int16_t semitone_offset = unpacked.note_index;
                int16_t octave_semitones = unpacked.octave_offset * 12;
                int16_t final_note = unsynced_notes[u].midi_note + semitone_offset + octave_semitones;

                // Clamp to MIDI range
                if (final_note < 0) final_note = 0;
                if (final_note > 127) final_note = 127;

                uint8_t raw_travel = apply_arp_velocity_pipeline(unpacked.velocity);

                // Send note-on
                midi_send_noteon_arp(unsynced_notes[u].channel, (uint8_t)final_note, raw_travel, raw_travel);

                // Add to arp_notes for gate tracking
                uint32_t note_off_time = current_time + gate_duration_ms;
                add_arp_note(unsynced_notes[u].channel, (uint8_t)final_note, raw_travel, note_off_time);
            }

            // Advance this note's position
            unsynced_notes[u].current_position_16ths++;
            if (unsynced_notes[u].current_position_16ths >= preset->pattern_length_16ths) {
                // Pattern loop: advance anchor by exact pattern duration (no drift)
                uint8_t nv, tm;
                if (arp_state.rate_override != 0) {
                    nv = arp_state.rate_override & ~TIMING_MODE_MASK;
                    tm = arp_state.rate_override & TIMING_MODE_MASK;
                } else {
                    nv = preset->note_value;
                    tm = preset->timing_mode;
                }
                unsynced_notes[u].anchor_start_time += compute_step_time_offset(
                    preset->pattern_length_16ths, nv, tm);
                unsynced_notes[u].current_position_16ths = 0;
            }

            // Anchored next note time: anchor_start + offset for next position
            {
                uint8_t nv, tm;
                if (arp_state.rate_override != 0) {
                    nv = arp_state.rate_override & ~TIMING_MODE_MASK;
                    tm = arp_state.rate_override & TIMING_MODE_MASK;
                } else {
                    nv = preset->note_value;
                    tm = preset->timing_mode;
                }
                unsynced_notes[u].next_note_time = unsynced_notes[u].anchor_start_time +
                    compute_step_time_offset(unsynced_notes[u].current_position_16ths, nv, tm);
            }
        }

        // Fire loop trigger on every arp step (when no macro loop is playing)
        if (!dynamic_macro_is_playing()) {
            dynamic_macro_handle_loop_trigger();
        }

        return;  // Chord unsynced handles everything independently
    }

    // =========================================================================
    // STANDARD TIMING: Shared timing check for all other modes
    // =========================================================================

    // Check if it's time to play next note
    uint32_t current_time = timer_read32();
    if (current_time < arp_state.next_note_time) {
        return;  // Not yet time
    }

    // Check for deferred loop record stop at this step boundary
    if (loop_deferred_record_stop_pending) {
        execute_deferred_record_stop();
        // Don't play this step's notes - stop happens before the step
        // Still advance timing so arp continues normally
        arp_state.current_position_16ths++;
        if (arp_state.current_position_16ths >= preset->pattern_length_16ths) {
            // Pattern loop: advance anchor by exact pattern duration (no drift)
            arp_state.pattern_start_time += compute_step_time_offset(
                preset->pattern_length_16ths,
                (arp_state.rate_override != 0) ? (arp_state.rate_override & ~TIMING_MODE_MASK) : preset->note_value,
                (arp_state.rate_override != 0) ? (arp_state.rate_override & TIMING_MODE_MASK) : preset->timing_mode);
            arp_state.current_position_16ths = 0;
        }
        arp_state.next_note_time = arp_anchored_next_time(preset, arp_state.current_position_16ths);

        // Fire loop trigger on every arp step (when no macro loop is playing)
        if (!dynamic_macro_is_playing()) {
            dynamic_macro_handle_loop_trigger();
        }
        return;
    }

    // Special case: Random preset - randomize note indices
    if (arp_state.current_preset_id == 3) {  // Random 8ths preset
        for (uint16_t i = 0; i < preset->note_count; i++) {
            // Extract current octave_offset from packed field
            int8_t current_octave = NOTE_GET_OCTAVE(preset->notes[i].note_octave);

            // Generate random semitone offset (0-11 for notes within an octave)
            uint8_t random_note_index = rand() % 12;

            // Repack note_octave with new random note_index, preserving octave_offset
            preset->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(random_note_index, current_octave);
        }
    }

    // Find notes to play at current position
    uint16_t notes_to_play[MAX_ACTIVE_ARP_NOTES];
    uint16_t note_count_to_play = 0;
    unpacked_note_t unpacked_notes[MAX_ACTIVE_ARP_NOTES];

    bool is_arpeggiator = (preset->preset_type == PRESET_TYPE_ARPEGGIATOR);

    for (uint16_t i = 0; i < preset->note_count; i++) {
        // Unpack the note to check its timing (8-bit active format)
        unpack_note(&preset->notes[i], &unpacked_notes[i], is_arpeggiator);

        if (unpacked_notes[i].timing == arp_state.current_position_16ths) {
            notes_to_play[note_count_to_play++] = i;
        }
    }

    // Play notes based on mode and preset type
    if (note_count_to_play > 0) {
        // Calculate gate length
        uint8_t gate_percent = (arp_state.master_gate_override > 0) ?
                               arp_state.master_gate_override :
                               preset->gate_length_percent;

        uint32_t ms_per_16th = get_ms_per_16th(preset);
        uint32_t note_duration_ms = ms_per_16th;  // Default: one 16th note
        uint32_t gate_duration_ms = (note_duration_ms * gate_percent) / 100;

        // Handle Step Sequencer (absolute notes)
        if (preset->preset_type == PRESET_TYPE_STEP_SEQUENCER) {
            // Step sequencer: play absolute MIDI notes
            for (uint16_t i = 0; i < note_count_to_play; i++) {
                uint16_t preset_note_idx = notes_to_play[i];
                unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                // Calculate absolute MIDI note: (octave × 12) + note_index
                // note_index = 0-11 (C-B), octave_offset = -8 to +7
                int16_t midi_note = (note->octave_offset * 12) + note->note_index;

                // Clamp to MIDI range (0-127)
                if (midi_note < 0) midi_note = 0;
                if (midi_note > 127) midi_note = 127;

                uint8_t raw_travel = apply_arp_velocity_pipeline(note->velocity);
                uint8_t channel = channel_number;  // Use current MIDI channel

                // Send note-on
                midi_send_noteon_arp(channel, (uint8_t)midi_note, raw_travel, raw_travel);

                // Add to arp_notes for gate tracking
                uint32_t note_off_time = current_time + gate_duration_ms;
                add_arp_note(channel, (uint8_t)midi_note, raw_travel, note_off_time);
            }
        }
        // Handle Arpeggiator (relative intervals)
        else {
            // Sort live notes by press order (for chord modes)
            uint8_t press_order_indices[MAX_LIVE_NOTES];
            sort_live_notes_by_press_order(press_order_indices, live_note_count);

            // Handle different playback modes
            switch (arp_state.mode) {
                case ARPMODE_SINGLE_NOTE_SYNCED:
                case ARPMODE_SINGLE_NOTE_UNSYNCED: {
                    // Single Note Mode: Play master note + semitone offset
                    // Master note = most recently pressed note that's still held
                    // Both synced and unsynced use the same logic:
                    // pattern continues on overlap, restarts when all notes released
                    if (live_note_count == 0) break;

                    uint8_t master_idx = get_most_recent_live_note_index();
                    uint8_t master_note = live_notes[master_idx][1];
                    uint8_t channel = live_notes[master_idx][0];

                    for (uint16_t i = 0; i < note_count_to_play; i++) {
                        uint16_t preset_note_idx = notes_to_play[i];
                        unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                        // Calculate note: master + semitone_offset + octave_offset
                        int16_t semitone_offset = note->note_index;
                        int16_t octave_semitones = note->octave_offset * 12;
                        int16_t final_note = master_note + semitone_offset + octave_semitones;

                        // Clamp to MIDI range
                        if (final_note < 0) final_note = 0;
                        if (final_note > 127) final_note = 127;

                        uint8_t raw_travel = apply_arp_velocity_pipeline(note->velocity);

                        // Send note-on
                        midi_send_noteon_arp(channel, (uint8_t)final_note, raw_travel, raw_travel);

                        // Add to arp_notes for gate tracking
                        uint32_t note_off_time = current_time + gate_duration_ms;
                        add_arp_note(channel, (uint8_t)final_note, raw_travel, note_off_time);
                    }
                    break;
                }

                case ARPMODE_CHORD_SYNCED: {
                    // Chord Synced Mode: Apply semitone offset to ALL held notes simultaneously
                    // All notes share the same timing grid
                    for (uint16_t i = 0; i < note_count_to_play; i++) {
                        uint16_t preset_note_idx = notes_to_play[i];
                        unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                        int16_t semitone_offset = note->note_index;
                        int16_t octave_semitones = note->octave_offset * 12;

                        // Apply offset to ALL held notes (in press order)
                        for (uint8_t n = 0; n < live_note_count; n++) {
                            uint8_t live_idx = press_order_indices[n];
                            uint8_t channel = live_notes[live_idx][0];
                            uint8_t master_note = live_notes[live_idx][1];

                            int16_t final_note = master_note + semitone_offset + octave_semitones;

                            // Clamp to MIDI range
                            if (final_note < 0) final_note = 0;
                            if (final_note > 127) final_note = 127;

                            uint8_t raw_travel = apply_arp_velocity_pipeline(note->velocity);

                            // Send note-on
                            midi_send_noteon_arp(channel, (uint8_t)final_note, raw_travel, raw_travel);

                            // Add to arp_notes for gate tracking
                            uint32_t note_off_time = current_time + gate_duration_ms;
                            add_arp_note(channel, (uint8_t)final_note, raw_travel, note_off_time);
                        }
                    }
                    break;
                }

                case ARPMODE_CHORD_ADVANCED: {
                    // Chord Advanced Mode: Rotates through held notes at base rate
                    // Each note gets the full step duration (NOT subdivided)
                    // Pattern: N1+S0, N2+S0, N3+S0, N1+S1, N2+S1, N3+S1, etc.
                    // Each note plays at ms_per_16th intervals

                    if (note_count_to_play == 0) break;

                    uint16_t preset_note_idx = notes_to_play[0];  // Use first step at this position
                    unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                    int16_t semitone_offset = note->note_index;
                    int16_t octave_semitones = note->octave_offset * 12;

                    // Get the note to play based on current_note_in_chord (in press order)
                    uint8_t chord_note_idx = arp_state.current_note_in_chord % live_note_count;
                    uint8_t live_idx = press_order_indices[chord_note_idx];
                    uint8_t channel = live_notes[live_idx][0];
                    uint8_t master_note = live_notes[live_idx][1];

                    int16_t final_note = master_note + semitone_offset + octave_semitones;

                    // Clamp to MIDI range
                    if (final_note < 0) final_note = 0;
                    if (final_note > 127) final_note = 127;

                    uint8_t raw_travel = apply_arp_velocity_pipeline(note->velocity);

                    // Gate at base rate (NOT subdivided - each note gets full step duration)
                    uint32_t base_gate_ms = (ms_per_16th * gate_percent) / 100;
                    if (base_gate_ms < 10) base_gate_ms = 10;  // Minimum 10ms gate

                    // Send note-on
                    midi_send_noteon_arp(channel, (uint8_t)final_note, raw_travel, raw_travel);

                    // Add to arp_notes for gate tracking at base rate
                    uint32_t note_off_time = current_time + base_gate_ms;
                    add_arp_note(channel, (uint8_t)final_note, raw_travel, note_off_time);

                    // Advance to next note in chord
                    arp_state.current_note_in_chord++;
                    arp_state.anchor_step++;

                    // Check if we've played all notes for this step
                    if (arp_state.current_note_in_chord >= live_note_count) {
                        // Reset for next step and advance pattern position
                        arp_state.current_note_in_chord = 0;

                        // Advance pattern position
                        arp_state.current_position_16ths++;

                        // Check for loop
                        if (arp_state.current_position_16ths >= preset->pattern_length_16ths) {
                            // Pattern loop: advance anchor by exact pattern duration (no drift)
                            // Use anchor_step to compute exact elapsed time for variable chord sizes
                            uint8_t nv = (arp_state.rate_override != 0) ? (arp_state.rate_override & ~TIMING_MODE_MASK) : preset->note_value;
                            uint8_t tm = (arp_state.rate_override != 0) ? (arp_state.rate_override & TIMING_MODE_MASK) : preset->timing_mode;
                            arp_state.pattern_start_time += compute_step_time_offset(arp_state.anchor_step, nv, tm);
                            arp_state.anchor_step = 0;
                            arp_state.current_position_16ths = 0;
                            dprintf("arp: pattern loop\n");
                        }
                    }

                    // Anchored next note time using total steps since pattern start
                    {
                        uint8_t nv = (arp_state.rate_override != 0) ? (arp_state.rate_override & ~TIMING_MODE_MASK) : preset->note_value;
                        uint8_t tm = (arp_state.rate_override != 0) ? (arp_state.rate_override & TIMING_MODE_MASK) : preset->timing_mode;
                        arp_state.next_note_time = arp_state.pattern_start_time +
                            compute_step_time_offset(arp_state.anchor_step, nv, tm);
                    }

                    // Fire loop trigger on every arp step (when no macro loop is playing)
                    if (!dynamic_macro_is_playing()) {
                        dynamic_macro_handle_loop_trigger();
                    }

                    // Return early - chord advanced handles position advancement above
                    return;
                }

                // ARPMODE_CHORD_UNSYNCED handled above (separate code path)
                default:
                    break;
            }
        }
    }

    // Advance position (not used for CHORD_ADVANCED which handles this itself)
    arp_state.current_position_16ths++;

    // Check for loop
    if (arp_state.current_position_16ths >= preset->pattern_length_16ths) {
        // Pattern loop: advance anchor by exact pattern duration (no drift)
        arp_state.pattern_start_time += compute_step_time_offset(
            preset->pattern_length_16ths,
            (arp_state.rate_override != 0) ? (arp_state.rate_override & ~TIMING_MODE_MASK) : preset->note_value,
            (arp_state.rate_override != 0) ? (arp_state.rate_override & TIMING_MODE_MASK) : preset->timing_mode);
        arp_state.current_position_16ths = 0;
        dprintf("arp: pattern loop\n");
    }

    // Anchored next note time: pattern_start + offset for next position
    arp_state.next_note_time = arp_anchored_next_time(preset, arp_state.current_position_16ths);

    // Fire loop trigger on every arp step (when no macro loop is playing)
    if (!dynamic_macro_is_playing()) {
        dynamic_macro_handle_loop_trigger();
    }
}

// =============================================================================
// STEP SEQUENCER DEFERRED START SYSTEM
// =============================================================================

// Get the note value multiplier (how many 16ths per step)
static uint8_t get_note_value_multiplier(uint8_t note_value) {
    switch (note_value) {
        case NOTE_VALUE_QUARTER:   return 4;
        case NOTE_VALUE_EIGHTH:    return 2;
        case NOTE_VALUE_SIXTEENTH:
        default:                   return 1;
    }
}

// Get the effective note value for a slot (respects rate override)
static uint8_t get_slot_note_value(const active_preset_t *preset, uint8_t slot) {
    if (slot < MAX_SEQ_SLOTS && seq_state[slot].rate_override != 0) {
        return seq_state[slot].rate_override & ~TIMING_MODE_MASK;
    }
    return preset->note_value;
}

// Get steps per cycle (bar boundary) for a given note value.
// Quarter = 4 steps per bar, Eighth = 8, Sixteenth = 16
static uint8_t get_steps_per_cycle(uint8_t note_value) {
    uint8_t multiplier = get_note_value_multiplier(note_value);
    return 16 / multiplier;  // Quarter: 16/4=4, Eighth: 16/2=8, Sixteenth: 16/1=16
}

// Release all deferred step sequencer starts.
// align_time: the time to use as the pattern start for released seqs.
// Released seqs play catch-up notes that would have already sounded.
void seq_release_deferred_starts(uint32_t align_time) {
    for (uint8_t slot = 0; slot < MAX_SEQ_SLOTS; slot++) {
        if (!seq_state[slot].active || !seq_state[slot].deferred_start_pending) continue;

        seq_state[slot].deferred_start_pending = false;
        seq_state[slot].pattern_start_time = align_time;
        seq_state[slot].current_position_16ths = 0;
        seq_state[slot].has_looped = false;

        // Calculate how many steps have elapsed since align_time (for catch-up)
        uint32_t now = timer_read32();
        uint32_t elapsed = now - align_time;  // Will be 0 if align_time == now

        active_preset_t *preset = &seq_active_presets[slot];
        if (elapsed > 0 && preset->note_count > 0) {
            // Calculate ms per step for this preset
            uint32_t ms_per_step = seq_get_ms_per_16th(preset, slot);
            if (ms_per_step == 0) ms_per_step = 1;

            // How many steps have elapsed
            uint16_t elapsed_steps = (uint16_t)(elapsed / ms_per_step);
            if (elapsed_steps > preset->pattern_length_16ths) {
                elapsed_steps = preset->pattern_length_16ths;
            }

            // Play catch-up notes whose gates are still active
            if (elapsed_steps > 0) {
                uint8_t gate_percent = (seq_state[slot].master_gate_override > 0) ?
                                       seq_state[slot].master_gate_override :
                                       preset->gate_length_percent;
                uint32_t gate_ms = (ms_per_step * gate_percent) / 100;

                for (uint16_t i = 0; i < preset->note_count; i++) {
                    unpacked_note_t unpacked;
                    unpack_note(&preset->notes[i], &unpacked, false);

                    // Only catch up notes within the elapsed window
                    if (unpacked.timing >= elapsed_steps) continue;

                    // Check if this note's gate is still active
                    uint32_t note_start = align_time + (uint32_t)unpacked.timing * ms_per_step;
                    uint32_t note_end = note_start + gate_ms;

                    if (now < note_end) {
                        // Gate still active - play it now with remaining gate
                        int16_t midi_note = (unpacked.octave_offset * 12) + unpacked.note_index;
                        if (midi_note < 0) midi_note = 0;
                        if (midi_note > 127) midi_note = 127;

                        midi_send_noteon_seq(slot, (uint8_t)midi_note, unpacked.velocity);

                        uint32_t remaining_gate = note_end - now;
                        add_seq_note(seq_state[slot].locked_channel, (uint8_t)midi_note,
                                     unpacked.velocity, now + remaining_gate, slot);

                        dprintf("seq: catch-up note ch:%d note:%d vel:%d remaining:%lu\n",
                                seq_state[slot].locked_channel, midi_note, unpacked.velocity, remaining_gate);
                    }
                }

                // Advance position past the caught-up steps
                seq_state[slot].current_position_16ths = elapsed_steps;
            }
        }

        // Set next note time using anchored timing
        seq_state[slot].next_note_time = seq_anchored_next_time(preset, slot,
            seq_state[slot].current_position_16ths);

        dprintf("seq: released deferred slot %d at pos %d (align_time:%lu)\n",
                slot, seq_state[slot].current_position_16ths, align_time);
    }
}

// Common deferred/group/immediate start logic for step sequencers.
// Called by both seq_start() and seq_start_slot() after slot is set up.
// Returns true if the seq was deferred (caller should skip further init).
static bool seq_apply_start_logic(uint8_t slot) {
    bool any_macro_playing = dynamic_macro_is_playing();
    bool in_group_window = group_start_active &&
                           (timer_elapsed32(group_start_time) < GROUP_START_WINDOW_MS);

    // Scan all other seq slots for state
    bool any_looped_seq = false;
    bool any_running_seq = false;   // Any active, non-deferred seq (looped or not)
    bool any_just_started = false;  // Active, not-yet-looped, started within GROUP_START_WINDOW_MS
    uint32_t just_started_time = 0;
    for (uint8_t s = 0; s < MAX_SEQ_SLOTS; s++) {
        if (s == slot) continue;
        if (seq_state[s].active && !seq_state[s].deferred_start_pending) {
            any_running_seq = true;
            if (seq_state[s].has_looped) {
                any_looped_seq = true;
            } else {
                // Not-yet-looped seq: only count as "just started" if within group window
                uint32_t elapsed = timer_elapsed32(seq_state[s].pattern_start_time);
                if (elapsed < GROUP_START_WINDOW_MS) {
                    just_started_time = seq_state[s].pattern_start_time;
                    any_just_started = true;
                }
            }
        }
    }

    if (any_just_started) {
        // Another seq started within the group window - align to its pattern start (catch-up)
        seq_state[slot].deferred_start_pending = false;
        seq_state[slot].pattern_start_time = just_started_time;
        seq_state[slot].next_note_time = just_started_time;
        dprintf("seq: slot %d aligned to just-started seq (time:%lu)\n", slot, just_started_time);

        // Play catch-up for any missed steps
        uint32_t now = timer_read32();
        uint32_t elapsed = now - just_started_time;
        active_preset_t *preset = &seq_active_presets[slot];
        uint32_t ms_per_step = seq_get_ms_per_16th(preset, slot);
        if (ms_per_step > 0 && elapsed > 0) {
            uint16_t elapsed_steps = (uint16_t)(elapsed / ms_per_step);
            if (elapsed_steps > 0 && elapsed_steps < preset->pattern_length_16ths) {
                seq_state[slot].current_position_16ths = elapsed_steps;
                seq_state[slot].next_note_time = seq_anchored_next_time(preset, slot, elapsed_steps);
            }
        }
        return false;
    } else if (in_group_window) {
        // Group start window active (from a loop start) - align to group time
        seq_state[slot].deferred_start_pending = false;
        seq_state[slot].pattern_start_time = group_start_time;
        seq_state[slot].next_note_time = group_start_time;
        dprintf("seq: slot %d aligned to group start (time:%lu)\n", slot, group_start_time);
        return false;
    } else if (any_running_seq || any_macro_playing) {
        // Something running but outside group window - defer until next cycle point
        seq_state[slot].deferred_start_pending = true;
        seq_state[slot].next_note_time = UINT32_MAX;  // Don't play until released
        dprintf("seq: slot %d deferred (running_seq:%d looped:%d macro:%d)\n",
                slot, any_running_seq, any_looped_seq, any_macro_playing);
        return true;
    } else {
        // Nothing playing - start now, open group window
        uint32_t now = timer_read32();
        seq_state[slot].deferred_start_pending = false;
        seq_state[slot].pattern_start_time = now;
        seq_state[slot].next_note_time = now;
        group_start_time = now;
        group_start_active = true;
        dprintf("seq: slot %d started immediately, group window opened\n", slot);
        return false;
    }
}

// =============================================================================
// STEP SEQUENCER FUNCTIONS
// =============================================================================

void seq_start(uint8_t preset_id) {
    // QUICK BUILD HOOK: Cancel quick build if active (seq play takes priority)
    if (quick_build_is_active()) {
        quick_build_cancel();
    }

    if (preset_id != PRESET_ID_QUICK_BUILD && (preset_id < 68 || preset_id >= MAX_SEQ_PRESETS)) {
        dprintf("seq: invalid preset id %d (valid range 68-135)\n", preset_id);
        return;
    }

    // Find available slot
    int8_t slot = seq_find_available_slot();
    if (slot < 0) {
        dprintf("seq: no available slots (all 4 occupied)\n");
        return;
    }

    // Lazy-load preset into the available slot
    if (!seq_load_preset_into_slot(preset_id, slot)) {
        dprintf("seq: failed to load preset %d into slot %d\n", preset_id, slot);
        return;
    }

    // Initialize sequencer state for this slot
    seq_state[slot].current_preset_id = preset_id;
    seq_state[slot].active = true;
    seq_state[slot].current_position_16ths = 0;
    seq_state[slot].has_looped = false;
    seq_state[slot].deferred_start_pending = false;

    // Lock in global values when sequencer starts
    seq_state[slot].locked_channel = channel_number;
    seq_state[slot].locked_velocity_min = he_velocity_min;
    seq_state[slot].locked_velocity_max = he_velocity_max;
    seq_state[slot].locked_transpose = 0;

    // Apply deferred/group/immediate start logic
    seq_apply_start_logic(slot);

    dprintf("seq: started preset %d in slot %d (ch:%d vel:%d-%d deferred:%d)\n",
            preset_id, slot, seq_state[slot].locked_channel,
            seq_state[slot].locked_velocity_min, seq_state[slot].locked_velocity_max,
            seq_state[slot].deferred_start_pending);
}

void seq_stop(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) return;

    if (seq_state[slot].active) {
        seq_state[slot].active = false;
        seq_state[slot].deferred_start_pending = false;

        // Immediately send note-offs for all active arp notes to prevent stuck notes
        // (seq uses arp_notes[] for gate tracking)
        for (uint8_t i = 0; i < MAX_ARP_NOTES; i++) {
            if (arp_notes[i].active) {
                if (arp_notes[i].from_seq) {
                    midi_send_noteoff_seq_macro(arp_notes[i].channel,
                                                arp_notes[i].note,
                                                arp_notes[i].velocity,
                                                arp_notes[i].seq_slot);
                } else {
                    midi_send_noteoff_arp(arp_notes[i].channel,
                                         arp_notes[i].note,
                                         arp_notes[i].velocity);
                }
                arp_notes[i].active = false;
                arp_note_count--;
                dprintf("seq: force-off note ch:%d note:%d from_seq:%d\n",
                        arp_notes[i].channel, arp_notes[i].note, arp_notes[i].from_seq);
            }
        }
        arp_note_count = 0;  // Safety reset

        dprintf("seq: stopped slot %d\n", slot);
    }
}

void seq_stop_all(void) {
    // Send note-offs for all active arp notes first (seq uses arp_notes[])
    for (uint8_t i = 0; i < MAX_ARP_NOTES; i++) {
        if (arp_notes[i].active) {
            if (arp_notes[i].from_seq) {
                midi_send_noteoff_seq_macro(arp_notes[i].channel,
                                            arp_notes[i].note,
                                            arp_notes[i].velocity,
                                            arp_notes[i].seq_slot);
            } else {
                midi_send_noteoff_arp(arp_notes[i].channel,
                                     arp_notes[i].note,
                                     arp_notes[i].velocity);
            }
            arp_notes[i].active = false;
            dprintf("seq: force-off note ch:%d note:%d from_seq:%d\n",
                    arp_notes[i].channel, arp_notes[i].note, arp_notes[i].from_seq);
        }
    }
    arp_note_count = 0;  // Safety reset

    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) {
            seq_state[i].active = false;
            seq_state[i].deferred_start_pending = false;
            dprintf("seq: stopped slot %d\n", i);
        }
    }
    dprintf("seq: stopped all sequencers\n");
}

void seq_update(void) {
    // Check for deferred loop record stop at pattern restart (position 0 only)
    if (loop_deferred_record_stop_pending) {
        for (uint8_t s = 0; s < MAX_SEQ_SLOTS; s++) {
            if (!seq_state[s].active || seq_state[s].deferred_start_pending) continue;
            uint32_t ct = timer_read32();
            if (seq_state[s].current_position_16ths == 0 && seq_state[s].has_looped && ct >= seq_state[s].next_note_time) {
                // Pattern restart boundary reached - execute deferred stop
                execute_deferred_record_stop();
                break;  // Only execute once
            }
        }
    }

    // Update all active sequencer slots
    for (uint8_t slot = 0; slot < MAX_SEQ_SLOTS; slot++) {
        if (!seq_state[slot].active) continue;

        // Skip deferred slots - they're waiting for a cycle point to be released
        if (seq_state[slot].deferred_start_pending) continue;

        // Get preset for this slot
        active_preset_t *preset = &seq_active_presets[slot];

        // Check if it's time to play next note
        uint32_t current_time = timer_read32();
        if (current_time < seq_state[slot].next_note_time) {
            continue;  // Not yet time
        }

        // Cycle point detection: release deferred starts at bar boundaries
        if (seq_state[slot].has_looped) {
            uint8_t nv = get_slot_note_value(preset, slot);
            uint8_t steps_per_cycle = get_steps_per_cycle(nv);
            uint16_t pos = seq_state[slot].current_position_16ths;

            if (steps_per_cycle > 0 && (pos % steps_per_cycle) == 0) {
                // This is a cycle point (bar boundary)
                // Fires at step 0 AND at mid-pattern cycle points (e.g., steps 4, 8, 12 in 1/4 mode)
                // Releases deferred seq starts, processes batched loop commands, handles primed recordings
                dynamic_macro_handle_loop_trigger();
            }
        }

        // Play notes at current position (inline processing to avoid large stack arrays)
        // Pre-compute gate duration for any notes that match
        uint8_t gate_percent = (seq_state[slot].master_gate_override > 0) ?
                               seq_state[slot].master_gate_override :
                               preset->gate_length_percent;
        uint32_t ms_per_16th = seq_get_ms_per_16th(preset, slot);
        uint32_t gate_duration_ms = (ms_per_16th * gate_percent) / 100;

        for (uint16_t i = 0; i < preset->note_count; i++) {
            unpacked_note_t note;
            unpack_note(&preset->notes[i], &note, false);  // false = step sequencer

            if (note.timing != seq_state[slot].current_position_16ths) continue;

            // Calculate absolute MIDI note: (octave × 12) + note_index
            int16_t midi_note = (note.octave_offset * 12) + note.note_index;

            // Clamp to MIDI range (0-127)
            if (midi_note < 0) midi_note = 0;
            if (midi_note > 127) midi_note = 127;

            // Send note-on using sequencer's locked-in values (as macro note, not recorded by looper)
            midi_send_noteon_seq(slot, (uint8_t)midi_note, note.velocity);

            // Add to arp_notes for gate tracking (marked as seq note for macro-style note-off)
            uint32_t note_off_time = current_time + gate_duration_ms;
            add_seq_note(seq_state[slot].locked_channel, (uint8_t)midi_note, note.velocity, note_off_time, slot);
        }

        // Advance position
        seq_state[slot].current_position_16ths++;

        // Check for loop (restart)
        if (seq_state[slot].current_position_16ths >= preset->pattern_length_16ths) {
            // Pattern loop: advance anchor by exact pattern duration (no drift)
            uint8_t nv, tm;
            if (slot < MAX_SEQ_SLOTS && seq_state[slot].rate_override != 0) {
                nv = seq_state[slot].rate_override & ~TIMING_MODE_MASK;
                tm = seq_state[slot].rate_override & TIMING_MODE_MASK;
            } else {
                nv = preset->note_value;
                tm = preset->timing_mode;
            }
            seq_state[slot].pattern_start_time += compute_step_time_offset(
                preset->pattern_length_16ths, nv, tm);
            seq_state[slot].current_position_16ths = 0;
            seq_state[slot].has_looped = true;
        }

        // Release deferred arp start on any seq step
        if (arp_state.deferred_start_pending) {
            arp_state.deferred_start_pending = false;
            arp_state.next_note_time = current_time;
            arp_state.pattern_start_time = current_time;
            arp_state.current_position_16ths = 0;
            arp_state.anchor_step = 0;
            dprintf("arp: deferred start released by seq step\n");
        }

        // Anchored next note time: pattern_start + offset for next position
        seq_state[slot].next_note_time = seq_anchored_next_time(preset, slot,
            seq_state[slot].current_position_16ths);
    }
}

// =============================================================================
// MIDI NOTE SENDING FOR SEQUENCER (with locked-in values)
// =============================================================================

// Send note-on for sequencer using locked-in channel/velocity/transpose
void midi_send_noteon_seq(uint8_t slot, uint8_t note, uint8_t velocity_0_127) {
    if (slot >= MAX_SEQ_SLOTS) return;

    // Use locked-in channel
    uint8_t channel = seq_state[slot].locked_channel;

    // Apply locked-in transpose
    int16_t transposed_note = note + seq_state[slot].locked_transpose;

    // Clamp to MIDI range
    if (transposed_note < 0) transposed_note = 0;
    if (transposed_note > 127) transposed_note = 127;

    // Apply velocity curve + locked per-slot vel range
    uint8_t raw_travel = apply_seq_velocity_pipeline(velocity_0_127, slot);

    // Send as macro note (not recorded by looper)
    midi_send_noteon_seq_macro(channel, (uint8_t)transposed_note, raw_travel, slot);
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

void arp_set_rate_override(uint8_t note_value, uint8_t timing_mode) {
    arp_state.rate_override = note_value | timing_mode;
    dprintf("arp: rate override set to note_value=%d timing_mode=%d\n", note_value, timing_mode);
}

void seq_set_rate_override(uint8_t note_value, uint8_t timing_mode) {
    // Apply to all active sequencer slots
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) {
            seq_state[i].rate_override = note_value | timing_mode;
        }
    }
    dprintf("seq: rate override set for all active slots\n");
}

void arp_reset_overrides(void) {
    arp_state.rate_override = 0;
    arp_state.master_gate_override = 0;
    dprintf("arp: all overrides reset\n");
}

void seq_reset_overrides(void) {
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        seq_state[i].rate_override = 0;
        seq_state[i].master_gate_override = 0;
    }
    dprintf("seq: all overrides reset for all slots\n");
}

void seq_toggle_sync_mode(void) {
    // Toggle sync mode for all sequencer slots
    bool new_mode = !seq_state[0].sync_mode;  // Use slot 0 as reference
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        seq_state[i].sync_mode = new_mode;
    }
    dprintf("seq: sync mode: %d\n", new_mode);
}

void seq_set_master_gate(uint8_t gate_percent) {
    if (gate_percent > 100) gate_percent = 100;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) {
            seq_state[i].master_gate_override = gate_percent;
        }
    }
    dprintf("seq: master gate override: %d%% for all active slots\n", gate_percent);
}

void seq_next_preset(void) {
    // Navigate through sequencer presets (68-135, 68 total)
    uint8_t current = seq_state[0].current_preset_id;  // Use slot 0 as reference

    current++;
    if (current >= MAX_SEQ_PRESETS) {
        current = 68;  // Wrap back to first seq preset
    }

    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        seq_state[i].current_preset_id = current;
    }

    dprintf("seq: next preset -> %d\n", current);
}

void seq_prev_preset(void) {
    uint8_t current = seq_state[0].current_preset_id;  // Use slot 0 as reference

    if (current <= 68) {
        current = MAX_SEQ_PRESETS - 1;  // Wrap to last seq preset (135)
    } else {
        current--;
    }

    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        seq_state[i].current_preset_id = current;
    }

    dprintf("seq: prev preset -> %d\n", current);
}

// =============================================================================
// USER INTERFACE FUNCTIONS
// =============================================================================

void arp_next_preset(void) {
    // Navigate through arpeggiator presets (0-67, 68 total)
    arp_state.current_preset_id = (arp_state.current_preset_id + 1) % MAX_ARP_PRESETS;
    dprintf("arp: next preset -> %d\n", arp_state.current_preset_id);

    // TODO: Update OLED display
}

void arp_prev_preset(void) {
    // Navigate through arpeggiator presets (0-67, 68 total)
    if (arp_state.current_preset_id == 0) {
        arp_state.current_preset_id = MAX_ARP_PRESETS - 1;
    } else {
        arp_state.current_preset_id--;
    }

    dprintf("arp: prev preset -> %d\n", arp_state.current_preset_id);

    // TODO: Update OLED display
}

#define ARP_DOUBLE_TAP_WINDOW 300  // ms for double-tap detection

// Handle arp key press (momentary + double-tap latch)
// Called for both ARP_PLAY and ARP_PRESET_BASE keycodes
void arp_handle_key_press(uint8_t preset_id) {
    uint32_t now = timer_read32();

    // If currently latched with the same preset, unlatch and stop
    if (arp_state.active && arp_state.latch_mode && arp_state.current_preset_id == preset_id) {
        arp_stop();
        arp_state.last_tap_time = 0;  // Reset to prevent accidental re-latch
        dprintf("arp: unlatched preset %d\n", preset_id);
        return;
    }

    // If a different arp is active (latched or momentary), deactivate it first
    if (arp_state.active) {
        arp_stop();
        dprintf("arp: deactivated previous arp for new preset %d\n", preset_id);
    }

    // Check for double-tap to enable latch
    bool is_double_tap = (arp_state.last_tap_time > 0) &&
                         (now - arp_state.last_tap_time) < ARP_DOUBLE_TAP_WINDOW;

    // Start arp with the requested preset
    arp_start(preset_id);

    if (is_double_tap) {
        arp_state.latch_mode = true;
        dprintf("arp: LATCHED preset %d (double-tap)\n", preset_id);
    } else {
        dprintf("arp: momentary ON preset %d\n", preset_id);
    }

    arp_state.key_held = true;
    arp_state.last_tap_time = now;
}

// Handle arp key release (stop if not latched)
void arp_handle_key_release(void) {
    arp_state.key_held = false;

    if (arp_state.latch_mode) {
        // Latched - keep running after release
        dprintf("arp: key released (latched, staying on)\n");
        return;
    }

    // Momentary - stop on release
    if (arp_state.active) {
        arp_stop();
        dprintf("arp: momentary OFF (key released)\n");
    }
}

// Legacy toggle (kept for any other callers)
void arp_toggle(void) {
    if (arp_state.active) {
        arp_stop();
        dprintf("arp: toggled OFF\n");
    } else {
        arp_start(arp_state.current_preset_id);
        dprintf("arp: toggled ON with preset %d\n", arp_state.current_preset_id);
    }
}

// Legacy select (kept for any other callers)
void arp_select_preset(uint8_t preset_id) {
    if (preset_id >= MAX_ARP_PRESETS) return;
    arp_handle_key_press(preset_id);
}

// DEPRECATED: Old button press/release handlers
void arp_handle_button_press(void) {
    arp_handle_key_press(arp_state.current_preset_id);
}

void arp_handle_button_release(void) {
    arp_handle_key_release();
}

void arp_toggle_sync_mode(void) {
    arp_state.sync_mode = !arp_state.sync_mode;
    dprintf("arp: sync mode: %d\n", arp_state.sync_mode);

    // TODO: Update OLED display
}

void arp_set_master_gate(uint8_t gate_percent) {
    if (gate_percent > 100) gate_percent = 100;
    arp_state.master_gate_override = gate_percent;
    dprintf("arp: master gate override: %d%%\n", gate_percent);
}

void arp_set_mode(arp_mode_t mode) {
    if (mode >= ARPMODE_COUNT) return;
    arp_state.mode = mode;
    arp_state.current_note_in_chord = 0;  // Reset chord rotation on mode change
    reset_unsynced_notes();  // Reset per-note state for chord unsynced
    dprintf("arp: mode set to %d\n", mode);
}

// =============================================================================
// RATE CYCLING FUNCTIONS
// =============================================================================

// Helper function to get next rate in the cycle
// Cycle: 1/4 → 1/4 dot → 1/4 trip → 1/8 → 1/8 dot → 1/8 trip → 1/16 → 1/16 dot → 1/16 trip → (wrap)
static void cycle_rate(uint8_t *rate_override, bool up) {
    // Rate states: 0-8 representing the 9 positions in the cycle
    uint8_t current_state = 0;

    // Determine current state from rate_override
    uint8_t note_val = (*rate_override) & ~TIMING_MODE_MASK;  // Note value (0, 1, or 2)
    uint8_t timing = (*rate_override) & TIMING_MODE_MASK;      // Timing mode (0, 1, or 2)

    // Map to state (0-8)
    if (note_val == NOTE_VALUE_QUARTER && timing == TIMING_MODE_STRAIGHT) current_state = 0;
    else if (note_val == NOTE_VALUE_QUARTER && timing == TIMING_MODE_DOTTED) current_state = 1;
    else if (note_val == NOTE_VALUE_QUARTER && timing == TIMING_MODE_TRIPLET) current_state = 2;
    else if (note_val == NOTE_VALUE_EIGHTH && timing == TIMING_MODE_STRAIGHT) current_state = 3;
    else if (note_val == NOTE_VALUE_EIGHTH && timing == TIMING_MODE_DOTTED) current_state = 4;
    else if (note_val == NOTE_VALUE_EIGHTH && timing == TIMING_MODE_TRIPLET) current_state = 5;
    else if (note_val == NOTE_VALUE_SIXTEENTH && timing == TIMING_MODE_STRAIGHT) current_state = 6;
    else if (note_val == NOTE_VALUE_SIXTEENTH && timing == TIMING_MODE_DOTTED) current_state = 7;
    else if (note_val == NOTE_VALUE_SIXTEENTH && timing == TIMING_MODE_TRIPLET) current_state = 8;

    // Cycle state
    if (up) {
        current_state = (current_state + 1) % 9;
    } else {
        current_state = (current_state == 0) ? 8 : current_state - 1;
    }

    // Map state back to note_val and timing
    switch (current_state) {
        case 0: *rate_override = NOTE_VALUE_QUARTER | TIMING_MODE_STRAIGHT; break;
        case 1: *rate_override = NOTE_VALUE_QUARTER | TIMING_MODE_DOTTED; break;
        case 2: *rate_override = NOTE_VALUE_QUARTER | TIMING_MODE_TRIPLET; break;
        case 3: *rate_override = NOTE_VALUE_EIGHTH | TIMING_MODE_STRAIGHT; break;
        case 4: *rate_override = NOTE_VALUE_EIGHTH | TIMING_MODE_DOTTED; break;
        case 5: *rate_override = NOTE_VALUE_EIGHTH | TIMING_MODE_TRIPLET; break;
        case 6: *rate_override = NOTE_VALUE_SIXTEENTH | TIMING_MODE_STRAIGHT; break;
        case 7: *rate_override = NOTE_VALUE_SIXTEENTH | TIMING_MODE_DOTTED; break;
        case 8: *rate_override = NOTE_VALUE_SIXTEENTH | TIMING_MODE_TRIPLET; break;
    }
}

// Arpeggiator rate cycling
void arp_rate_up(void) {
    if (arp_state.rate_override == 0) {
        // Start from 1/4 straight
        arp_state.rate_override = NOTE_VALUE_QUARTER | TIMING_MODE_STRAIGHT;
    } else {
        cycle_rate(&arp_state.rate_override, true);
    }
    dprintf("arp: rate cycled up to %d\n", arp_state.rate_override);
}

void arp_rate_down(void) {
    if (arp_state.rate_override == 0) {
        // Start from 1/16 triplet
        arp_state.rate_override = NOTE_VALUE_SIXTEENTH | TIMING_MODE_TRIPLET;
    } else {
        cycle_rate(&arp_state.rate_override, false);
    }
    dprintf("arp: rate cycled down to %d\n", arp_state.rate_override);
}

// Step sequencer rate cycling (affects all active slots)
void seq_rate_up(void) {
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) {
            seq_rate_up_for_slot(i);
        }
    }
}

void seq_rate_down(void) {
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) {
            seq_rate_down_for_slot(i);
        }
    }
}

// Step sequencer rate cycling for specific slot
void seq_rate_up_for_slot(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) return;

    if (seq_state[slot].rate_override == 0) {
        // Start from 1/4 straight
        seq_state[slot].rate_override = NOTE_VALUE_QUARTER | TIMING_MODE_STRAIGHT;
    } else {
        cycle_rate(&seq_state[slot].rate_override, true);
    }
    dprintf("seq: slot %d rate cycled up to %d\n", slot, seq_state[slot].rate_override);
}

void seq_rate_down_for_slot(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) return;

    if (seq_state[slot].rate_override == 0) {
        // Start from 1/16 triplet
        seq_state[slot].rate_override = NOTE_VALUE_SIXTEENTH | TIMING_MODE_TRIPLET;
    } else {
        cycle_rate(&seq_state[slot].rate_override, false);
    }
    dprintf("seq: slot %d rate cycled down to %d\n", slot, seq_state[slot].rate_override);
}

// =============================================================================
// STATIC GATE SETTING FUNCTIONS
// =============================================================================

void arp_set_gate_static(uint8_t gate_percent) {
    if (gate_percent > 100) gate_percent = 100;
    arp_state.master_gate_override = gate_percent;
    dprintf("arp: gate set to %d%%\n", gate_percent);
}

void seq_set_gate_static(uint8_t gate_percent) {
    if (gate_percent > 100) gate_percent = 100;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) {
            seq_state[i].master_gate_override = gate_percent;
        }
    }
    dprintf("seq: gate set to %d%% for all active slots\n", gate_percent);
}

void seq_set_gate_for_slot(uint8_t slot, uint8_t gate_percent) {
    if (slot >= MAX_SEQ_SLOTS) return;
    if (gate_percent > 100) gate_percent = 100;

    seq_state[slot].master_gate_override = gate_percent;
    dprintf("seq: slot %d gate set to %d%%\n", slot, gate_percent);
}

// =============================================================================
// PHASE 3: EEPROM STORAGE & PRESET MANAGEMENT
// =============================================================================

// Calculate EEPROM address for arpeggiator presets
// Factory arp presets: 0-47 (not in EEPROM, in PROGMEM)
// User arp presets: 48-67 (20 slots, maps to EEPROM slots 0-19)
// Note: USER_ARP_PRESET_START and MAX_ARP_PRESETS defined in orthomidi5x14.h

static uint32_t arp_get_preset_eeprom_addr(uint8_t preset_id) {
    if (preset_id < USER_ARP_PRESET_START) {
        return 0;  // Factory preset, not in EEPROM
    }
    if (preset_id >= MAX_ARP_PRESETS) {
        return 0;  // Invalid preset
    }
    uint8_t eeprom_slot = preset_id - USER_ARP_PRESET_START;  // Maps 48-67 to 0-19
    return ARP_EEPROM_ADDR + (eeprom_slot * ARP_PRESET_SIZE);
}

// Calculate EEPROM address for step sequencer presets
// Factory seq presets: 68-115 (48 slots, not in EEPROM, in PROGMEM, maps internally to 0-47)
// User seq presets: 116-135 (20 slots, maps to EEPROM slots 0-19)
// Note: USER_SEQ_PRESET_START and MAX_SEQ_PRESETS defined in orthomidi5x14.h

static uint32_t seq_get_preset_eeprom_addr(uint8_t preset_id) {
    if (preset_id < USER_SEQ_PRESET_START) {
        return 0;  // Factory preset, not in EEPROM
    }
    if (preset_id >= MAX_SEQ_PRESETS) {
        return 0;  // Invalid preset
    }
    uint8_t eeprom_slot = preset_id - USER_SEQ_PRESET_START;  // Maps 116-135 to 0-19
    return SEQ_EEPROM_ADDR + (eeprom_slot * SEQ_PRESET_SIZE);
}

// Validate arpeggiator preset structure
bool arp_validate_preset(const arp_preset_t *preset) {
    if (preset == NULL) {
        dprintf("arp: validate failed - NULL pointer\n");
        return false;
    }

    // Check magic number
    if (preset->magic != ARP_PRESET_MAGIC) {
        dprintf("arp: validate failed - bad magic: 0x%04X (expected 0x%04X)\n",
                preset->magic, ARP_PRESET_MAGIC);
        return false;
    }

    // Check note count bounds for arpeggiator (max 64 notes)
    if (preset->note_count > MAX_ARP_PRESET_NOTES) {
        dprintf("arp: validate failed - note_count %d exceeds max %d\n",
                preset->note_count, MAX_ARP_PRESET_NOTES);
        return false;
    }

    // Check gate length bounds
    if (preset->gate_length_percent > 100) {
        dprintf("arp: validate failed - gate_length_percent %d > 100\n",
                preset->gate_length_percent);
        return false;
    }

    // Check pattern length bounds (at least 1 16th, max 127 = ~8 bars)
    if (preset->pattern_length_16ths < 1 || preset->pattern_length_16ths > 127) {
        dprintf("arp: validate failed - pattern_length %d not in [1,127]\n",
                preset->pattern_length_16ths);
        return false;
    }

    // Validate individual notes (7-bit EEPROM format)
    bool is_arpeggiator = (preset->preset_type == PRESET_TYPE_ARPEGGIATOR);
    for (uint8_t i = 0; i < preset->note_count; i++) {
        const arp_preset_note_t *packed_note = &preset->notes[i];
        unpacked_note_t note;
        unpack_note_7bit(packed_note, &note, is_arpeggiator);

        // Check timing is within pattern length
        if (note.timing >= preset->pattern_length_16ths) {
            dprintf("arp: validate failed - note[%d] timing %d >= pattern_length %d\n",
                    i, note.timing, preset->pattern_length_16ths);
            return false;
        }

        // Check octave offset is within new packed range (-8 to +7)
        if (note.octave_offset < -8 || note.octave_offset > 7) {
            dprintf("arp: validate failed - note[%d] octave_offset %d not in [-8,7]\n",
                    i, note.octave_offset);
            return false;
        }
    }

    dprintf("arp: preset validation passed\n");
    return true;
}

// Validate step sequencer preset structure (7-bit EEPROM format)
bool seq_validate_preset(const seq_preset_t *preset) {
    if (preset == NULL) {
        dprintf("seq: validate failed - NULL pointer\n");
        return false;
    }

    if (preset->magic != ARP_PRESET_MAGIC) {
        dprintf("seq: validate failed - bad magic: 0x%04X (expected 0x%04X)\n",
                preset->magic, ARP_PRESET_MAGIC);
        return false;
    }

    if (preset->note_count > MAX_SEQ_PRESET_NOTES) {
        dprintf("seq: validate failed - note_count %d exceeds max %d\n",
                preset->note_count, MAX_SEQ_PRESET_NOTES);
        return false;
    }

    if (preset->gate_length_percent > 100) {
        dprintf("seq: validate failed - gate_length_percent %d > 100\n",
                preset->gate_length_percent);
        return false;
    }

    if (preset->pattern_length_16ths < 1 || preset->pattern_length_16ths > 127) {
        dprintf("seq: validate failed - pattern_length %d not in [1,127]\n",
                preset->pattern_length_16ths);
        return false;
    }

    // Validate individual notes (7-bit EEPROM format)
    bool is_arpeggiator = (preset->preset_type == PRESET_TYPE_ARPEGGIATOR);
    for (uint8_t i = 0; i < preset->note_count; i++) {
        const arp_preset_note_t *packed_note = &preset->notes[i];
        unpacked_note_t note;
        unpack_note_7bit(packed_note, &note, is_arpeggiator);

        if (note.timing >= preset->pattern_length_16ths) {
            dprintf("seq: validate failed - note[%d] timing %d >= pattern_length %d\n",
                    i, note.timing, preset->pattern_length_16ths);
            return false;
        }

        if (note.octave_offset < -8 || note.octave_offset > 7) {
            dprintf("seq: validate failed - note[%d] octave_offset %d not in [-8,7]\n",
                    i, note.octave_offset);
            return false;
        }
    }

    dprintf("seq: preset validation passed\n");
    return true;
}

// Save an arpeggiator preset to EEPROM (user slots 48-67)
bool arp_save_preset_to_eeprom(uint8_t preset_id, const arp_preset_t *source) {
    if (preset_id < USER_ARP_PRESET_START || preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: save failed - preset_id %d is not a user preset slot (48-67)\n", preset_id);
        return false;
    }

    if (source == NULL) {
        dprintf("arp: save failed - NULL source pointer\n");
        return false;
    }

    // Validate preset before saving
    if (!arp_validate_preset(source)) {
        dprintf("arp: save failed - preset %d validation failed\n", preset_id);
        return false;
    }

    uint32_t addr = arp_get_preset_eeprom_addr(preset_id);

    dprintf("arp: saving preset %d to EEPROM addr 0x%08lX (size=%u bytes)\n",
            preset_id, addr, ARP_PRESET_SIZE);

    eeprom_update_block(source, (void*)addr, ARP_PRESET_SIZE);

    dprintf("arp: preset %d saved successfully\n", preset_id);
    return true;
}

// Load an arpeggiator preset from EEPROM (user slots 48-67)
bool arp_load_preset_from_eeprom(uint8_t preset_id, arp_preset_t *dest) {
    if (preset_id < USER_ARP_PRESET_START || preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: load failed - preset_id %d is not a user preset slot (48-67)\n", preset_id);
        return false;
    }

    if (dest == NULL) {
        dprintf("arp: load failed - NULL destination\n");
        return false;
    }

    uint32_t addr = arp_get_preset_eeprom_addr(preset_id);

    dprintf("arp: loading preset %d from EEPROM addr 0x%08lX\n", preset_id, addr);

    // Read directly into destination
    eeprom_read_block(dest, (void*)addr, ARP_PRESET_SIZE);

    // Validate loaded preset
    if (!arp_validate_preset(dest)) {
        dprintf("arp: load failed - preset %d failed validation (corrupted or uninitialized)\n",
                preset_id);
        return false;
    }

    dprintf("arp: preset %d loaded successfully\n", preset_id);
    return true;
}

// Save a step sequencer preset to EEPROM (user slots 116-135)
bool seq_save_preset_to_eeprom(uint8_t preset_id, const seq_preset_t *source) {
    if (preset_id < USER_SEQ_PRESET_START || preset_id >= MAX_SEQ_PRESETS) {
        dprintf("seq: save failed - preset_id %d is not a user preset slot (116-135)\n", preset_id);
        return false;
    }

    if (source == NULL) {
        dprintf("seq: save failed - NULL source pointer\n");
        return false;
    }

    // Validate preset before saving
    if (!seq_validate_preset(source)) {
        dprintf("seq: save failed - preset %d validation failed\n", preset_id);
        return false;
    }

    uint32_t addr = seq_get_preset_eeprom_addr(preset_id);

    dprintf("seq: saving preset %d to EEPROM addr 0x%08lX (size=%u bytes)\n",
            preset_id, addr, SEQ_PRESET_SIZE);

    eeprom_update_block(source, (void*)addr, SEQ_PRESET_SIZE);

    dprintf("seq: preset %d saved successfully\n", preset_id);
    return true;
}

// Load a step sequencer preset from EEPROM (user slots 116-135)
bool seq_load_preset_from_eeprom(uint8_t preset_id, seq_preset_t *dest) {
    if (preset_id < USER_SEQ_PRESET_START || preset_id >= MAX_SEQ_PRESETS) {
        dprintf("seq: load failed - preset_id %d is not a user preset slot (116-135)\n", preset_id);
        return false;
    }

    if (dest == NULL) {
        dprintf("seq: load failed - NULL destination\n");
        return false;
    }

    uint32_t addr = seq_get_preset_eeprom_addr(preset_id);

    dprintf("seq: loading preset %d from EEPROM addr 0x%08lX\n", preset_id, addr);

    // Read directly into destination
    eeprom_read_block(dest, (void*)addr, SEQ_PRESET_SIZE);

    // Validate loaded preset
    if (!seq_validate_preset(dest)) {
        dprintf("seq: load failed - preset %d failed validation (corrupted or uninitialized)\n",
                preset_id);
        return false;
    }

    dprintf("seq: preset %d loaded successfully\n", preset_id);
    return true;
}

// OBSOLETE: No longer needed with lazy-loading system
// User presets are loaded on-demand when selected
// This function is kept for potential future EEPROM validation/migration
void arp_load_all_user_presets(void) {
    dprintf("arp: arp_load_all_user_presets() is obsolete with lazy-loading\n");
    dprintf("arp: User presets (48-63) will be loaded on-demand from EEPROM\n");
}

// Clear an arpeggiator user preset (fill with empty/default values)
bool arp_clear_preset(uint8_t preset_id) {
    if (preset_id < USER_ARP_PRESET_START || preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: clear failed - preset_id %d is not a user preset slot (48-67)\n", preset_id);
        return false;
    }

    dprintf("arp: clearing preset %d\n", preset_id);

    // Create temporary empty preset
    arp_preset_t empty_preset;
    memset(&empty_preset, 0, sizeof(arp_preset_t));

    empty_preset.preset_type = PRESET_TYPE_ARPEGGIATOR;
    empty_preset.note_count = 0;
    empty_preset.pattern_length_16ths = 16;
    empty_preset.gate_length_percent = 80;
    empty_preset.timing_mode = TIMING_MODE_STRAIGHT;
    empty_preset.note_value = NOTE_VALUE_QUARTER;
    empty_preset.magic = ARP_PRESET_MAGIC;

    // Save to EEPROM
    return arp_save_preset_to_eeprom(preset_id, &empty_preset);
}

// Clear a sequencer user preset (fill with empty/default values)
bool seq_clear_preset(uint8_t preset_id) {
    if (preset_id < USER_SEQ_PRESET_START || preset_id >= MAX_SEQ_PRESETS) {
        dprintf("seq: clear failed - preset_id %d is not a user preset slot (116-135)\n", preset_id);
        return false;
    }

    dprintf("seq: clearing preset %d\n", preset_id);

    // Create temporary empty preset
    seq_preset_t empty_preset;
    memset(&empty_preset, 0, sizeof(seq_preset_t));

    empty_preset.preset_type = PRESET_TYPE_STEP_SEQUENCER;
    empty_preset.note_count = 0;
    empty_preset.pattern_length_16ths = 16;
    empty_preset.gate_length_percent = 80;
    empty_preset.timing_mode = TIMING_MODE_STRAIGHT;
    empty_preset.note_value = NOTE_VALUE_QUARTER;
    empty_preset.magic = ARP_PRESET_MAGIC;

    // Save to EEPROM
    return seq_save_preset_to_eeprom(preset_id, &empty_preset);
}

// Copy an arpeggiator preset to another slot
bool arp_copy_preset(uint8_t source_id, uint8_t dest_id) {
    if (source_id >= MAX_ARP_PRESETS || dest_id >= MAX_ARP_PRESETS) {
        dprintf("arp: copy failed - invalid source %d or dest %d\n", source_id, dest_id);
        return false;
    }

    // Check if destination is a user preset slot (48-67)
    if (dest_id < USER_ARP_PRESET_START) {
        dprintf("arp: copy failed - cannot overwrite factory preset %d\n", dest_id);
        return false;
    }

    dprintf("arp: copying preset %d to %d\n", source_id, dest_id);

    // Create temporary preset for copying
    arp_preset_t temp_preset;

    // Load source preset (from EEPROM or factory data)
    if (source_id >= USER_ARP_PRESET_START) {
        // User preset: load from EEPROM
        if (!arp_load_preset_from_eeprom(source_id, &temp_preset)) {
            dprintf("arp: copy failed - could not load source preset %d from EEPROM\n", source_id);
            return false;
        }
    } else {
        // Factory preset: load from PROGMEM
        arp_load_factory_preset(source_id, &temp_preset);
    }

    // Validate source
    if (!arp_validate_preset(&temp_preset)) {
        dprintf("arp: copy failed - source preset %d invalid\n", source_id);
        return false;
    }

    // Save to destination in EEPROM
    return arp_save_preset_to_eeprom(dest_id, &temp_preset);
}

// Copy a sequencer preset to another slot
bool seq_copy_preset(uint8_t source_id, uint8_t dest_id) {
    if (source_id >= MAX_SEQ_PRESETS || dest_id >= MAX_SEQ_PRESETS) {
        dprintf("seq: copy failed - invalid source %d or dest %d\n", source_id, dest_id);
        return false;
    }

    // Check if destination is a user preset slot (116-135)
    if (dest_id < USER_SEQ_PRESET_START) {
        dprintf("seq: copy failed - cannot overwrite factory preset %d\n", dest_id);
        return false;
    }

    dprintf("seq: copying preset %d to %d\n", source_id, dest_id);

    // Create temporary preset for copying
    seq_preset_t temp_preset;

    // Load source preset (from EEPROM or factory data)
    if (source_id >= USER_SEQ_PRESET_START) {
        // User preset: load from EEPROM
        if (!seq_load_preset_from_eeprom(source_id, &temp_preset)) {
            dprintf("seq: copy failed - could not load source preset %d from EEPROM\n", source_id);
            return false;
        }
    } else {
        // Factory preset: load from PROGMEM (68-115 maps to internal 0-47)
        uint8_t factory_id = source_id - 68;  // Map 68-115 to 0-47
        seq_load_factory_preset(factory_id, &temp_preset);
    }

    // Validate source
    if (!seq_validate_preset(&temp_preset)) {
        dprintf("seq: copy failed - source preset %d invalid\n", source_id);
        return false;
    }

    // Save to destination in EEPROM
    return seq_save_preset_to_eeprom(dest_id, &temp_preset);
}

// Reset all arpeggiator user presets to empty state and clear EEPROM
void arp_reset_all_user_presets(void) {
    dprintf("arp: resetting all user presets...\n");

    // Reset all user arp presets (48-67, 20 slots)
    for (uint8_t i = USER_ARP_PRESET_START; i < MAX_ARP_PRESETS; i++) {
        arp_clear_preset(i);
    }

    dprintf("arp: all user presets reset\n");
}

// Reset all sequencer user presets to empty state and clear EEPROM
void seq_reset_all_user_presets(void) {
    dprintf("seq: resetting all user presets...\n");

    // Reset all user seq presets (116-135, 20 slots)
    for (uint8_t i = USER_SEQ_PRESET_START; i < MAX_SEQ_PRESETS; i++) {
        seq_clear_preset(i);
    }

    dprintf("seq: all user presets reset\n");
}

// =============================================================================
// QUICK BUILD IMPLEMENTATION
// =============================================================================

// Check if quick build is currently active
bool quick_build_is_active(void) {
    return (quick_build_state.mode != QUICK_BUILD_NONE);
}

bool quick_build_is_setup(void) {
    return (quick_build_state.mode == QUICK_BUILD_ARP_SETUP ||
            quick_build_state.mode == QUICK_BUILD_SEQ_SETUP ||
            quick_build_state.mode == QUICK_BUILD_ARP_ROOT);
}

bool quick_build_is_recording(void) {
    return (quick_build_state.mode == QUICK_BUILD_ARP_RECORD ||
            quick_build_state.mode == QUICK_BUILD_SEQ_RECORD);
}

bool quick_build_is_summary(void) {
    return (quick_build_state.mode == QUICK_BUILD_SUMMARY);
}

// Dismiss summary screen and return to normal
void quick_build_dismiss_summary(void) {
    if (quick_build_state.mode == QUICK_BUILD_SUMMARY) {
        quick_build_state.mode = QUICK_BUILD_NONE;
    }
}

// Get current step number (1-indexed for display)
uint16_t quick_build_get_current_step(void) {
    return quick_build_state.current_step + 1;  // Return 1-indexed
}

// Get arp active preset total pattern length in milliseconds (for summary display)
uint32_t quick_build_get_arp_pattern_ms(void) {
    return compute_step_time_offset(
        arp_active_preset.pattern_length_16ths,
        arp_active_preset.note_value,
        arp_active_preset.timing_mode);
}

// Get seq preset total pattern length in milliseconds for a specific slot (for summary display)
uint32_t quick_build_get_seq_pattern_ms(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) return 0;
    return compute_step_time_offset(
        seq_active_presets[slot].pattern_length_16ths,
        seq_active_presets[slot].note_value,
        seq_active_presets[slot].timing_mode);
}

// Start quick build for arpeggiator (slot 0-3)
void quick_build_start_arp(uint8_t slot) {
    if (slot >= MAX_ARP_QB_SLOTS) return;

    // Ignore if already in any quick build mode
    if (quick_build_state.mode != QUICK_BUILD_NONE) {
        dprintf("quick_build: ignoring arp start, already in quick build mode %d\n", quick_build_state.mode);
        return;
    }

    dprintf("quick_build: starting arp slot %d builder (setup phase)\n", slot);

    // Stop any playing arp
    if (arp_state.active) {
        arp_stop();
    }

    // Enter setup phase (parameter selection before recording)
    quick_build_state.mode = QUICK_BUILD_ARP_SETUP;
    quick_build_state.arp_slot = slot;
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    quick_build_state.has_root = false;
    quick_build_state.candidate_root = 0;
    quick_build_state.candidate_ready = false;
    quick_build_state.has_saved_arp_build[slot] = false;
    quick_build_state.sustain_held_last_check = false;
    quick_build_state.encoder_chord_held = false;

    // Setup phase: start with last-used values
    quick_build_state.setup_param_index = 0;
    quick_build_state.setup_arp_mode = last_arp_mode;
    quick_build_state.setup_note_value = last_note_value;
    quick_build_state.setup_timing_mode = last_timing_mode;
    quick_build_state.setup_gate_percent = last_gate_percent;

    dprintf("quick_build: arp slot %d setup phase started\n", slot);
}

// Transition from setup to recording phase (called after all params confirmed)
static void quick_build_enter_recording(void) {
    if (quick_build_state.mode == QUICK_BUILD_ARP_SETUP) {
        // Allocate max arp notes from pool
        arp_preset_note_t *notes = note_pool_alloc(POOL_SLOT_ARP, MAX_ACTIVE_ARP_NOTES);
        if (!notes) {
            dprintf("quick_build: pool alloc failed for arp\n");
            return;
        }

        // Clear and initialize arp_active_preset with selected settings
        memset(&arp_active_preset, 0, sizeof(active_preset_t));
        arp_active_preset.notes = notes;
        arp_active_preset.preset_type = PRESET_TYPE_ARPEGGIATOR;
        arp_active_preset.note_count = 0;
        arp_active_preset.pattern_length_16ths = 1;
        arp_active_preset.gate_length_percent = quick_build_state.setup_gate_percent;
        arp_active_preset.timing_mode = quick_build_state.setup_timing_mode;
        arp_active_preset.note_value = quick_build_state.setup_note_value;
        arp_active_preset.magic = ARP_PRESET_MAGIC;

        // Apply arp mode
        arp_state.mode = (arp_mode_t)quick_build_state.setup_arp_mode;
        arp_state.loaded_preset_id = PRESET_ID_QUICK_BUILD;

        // Arp goes to root note selection first (not straight to recording)
        quick_build_state.mode = QUICK_BUILD_ARP_ROOT;
        quick_build_state.has_root = false;
        dprintf("quick_build: arp waiting for root note (mode:%d speed:%d timing:%d gate:%d%%)\n",
                quick_build_state.setup_arp_mode, quick_build_state.setup_note_value,
                quick_build_state.setup_timing_mode, quick_build_state.setup_gate_percent);

    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_SETUP) {
        uint8_t slot = quick_build_state.seq_slot;

        // Allocate max seq notes from pool
        arp_preset_note_t *notes = note_pool_alloc(POOL_SLOT_SEQ(slot), MAX_ACTIVE_SEQ_NOTES);
        if (!notes) {
            dprintf("quick_build: pool alloc failed for seq slot %d\n", slot);
            return;
        }

        // Clear and initialize seq preset with selected settings
        memset(&seq_active_presets[slot], 0, sizeof(active_preset_t));
        seq_active_presets[slot].notes = notes;
        seq_active_presets[slot].preset_type = PRESET_TYPE_STEP_SEQUENCER;
        seq_active_presets[slot].note_count = 0;
        seq_active_presets[slot].pattern_length_16ths = 1;
        seq_active_presets[slot].gate_length_percent = quick_build_state.setup_gate_percent;
        seq_active_presets[slot].timing_mode = quick_build_state.setup_timing_mode;
        seq_active_presets[slot].note_value = quick_build_state.setup_note_value;
        seq_active_presets[slot].magic = ARP_PRESET_MAGIC;

        seq_state[slot].loaded_preset_id = PRESET_ID_QUICK_BUILD;

        quick_build_state.mode = QUICK_BUILD_SEQ_RECORD;
        dprintf("quick_build: seq slot %d recording phase started (speed:%d timing:%d gate:%d%%)\n",
                slot, quick_build_state.setup_note_value,
                quick_build_state.setup_timing_mode, quick_build_state.setup_gate_percent);
    }
}

// Start quick build for step sequencer (specific slot)
void quick_build_start_seq(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) {
        dprintf("quick_build: invalid slot %d\n", slot);
        return;
    }

    // Ignore if already in any quick build mode
    if (quick_build_state.mode != QUICK_BUILD_NONE) {
        dprintf("quick_build: ignoring seq start, already in quick build mode %d\n", quick_build_state.mode);
        return;
    }

    dprintf("quick_build: starting seq builder for slot %d (setup phase)\n", slot);

    // Stop all playing sequencers
    seq_stop_all();

    // Enter setup phase
    quick_build_state.mode = QUICK_BUILD_SEQ_SETUP;
    quick_build_state.seq_slot = slot;
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    quick_build_state.has_saved_seq_build[slot] = false;
    quick_build_state.sustain_held_last_check = false;
    quick_build_state.encoder_chord_held = false;

    // Setup phase: start with last-used values
    quick_build_state.setup_param_index = 0;
    quick_build_state.setup_note_value = last_note_value;
    quick_build_state.setup_timing_mode = last_timing_mode;
    quick_build_state.setup_gate_percent = last_gate_percent;

    dprintf("quick_build: seq slot %d setup phase started\n", slot);
}

// Cancel quick build and return to normal mode
void quick_build_cancel(void) {
    if (!quick_build_is_active()) return;

    dprintf("quick_build: canceling build mode %d\n", quick_build_state.mode);

    quick_build_state.mode = QUICK_BUILD_NONE;
    // Don't clear saved flags - cancel only aborts the in-progress build,
    // not previously completed builds of either type
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    quick_build_state.has_root = false;

    dprintf("quick_build: canceled\n");
}

// Finish and save the quick build
void quick_build_finish(void) {
    if (!quick_build_is_active()) return;

    if (quick_build_state.mode == QUICK_BUILD_ARP_RECORD) {
        uint8_t arp_slot = quick_build_state.arp_slot;

        // Fix pattern length: find actual highest step that has notes recorded
        uint16_t max_step = 0;
        for (uint16_t i = 0; i < quick_build_state.note_count; i++) {
            uint16_t step = NOTE_GET_TIMING(arp_active_preset.notes[i].packed_timing_vel);
            if (step > max_step) max_step = step;
        }
        arp_active_preset.pattern_length_16ths = max_step + 1;

        // Validate active arp preset (8-bit format)
        if (!active_validate_arp(&arp_active_preset)) {
            dprintf("quick_build: arp validation failed, canceling\n");
            quick_build_cancel();
            return;
        }

        dprintf("quick_build: arp slot %d finished with %d notes, %d steps\n",
                arp_slot, quick_build_state.note_count, arp_active_preset.pattern_length_16ths);

        // Save to QB storage: allocate pool space and copy notes
        uint16_t count = arp_active_preset.note_count;
        arp_preset_note_t *qb_notes = note_pool_alloc(POOL_SLOT_QB(arp_slot), count);
        if (qb_notes && count > 0) {
            memcpy(qb_notes, arp_active_preset.notes, count * sizeof(arp_preset_note_t));
        }
        arp_qb_presets[arp_slot] = arp_active_preset;  // Copy header
        arp_qb_presets[arp_slot].notes = qb_notes;     // Point to QB pool allocation

        quick_build_state.has_saved_arp_build[arp_slot] = true;
        quick_build_state.active_arp_qb_slot = arp_slot;

        // Mark arp to play this quick build pattern (not a factory/user preset)
        arp_state.current_preset_id = PRESET_ID_QUICK_BUILD;
        arp_state.loaded_preset_id = PRESET_ID_QUICK_BUILD;

        // Save last-used settings for next build
        last_arp_mode = quick_build_state.setup_arp_mode;
        last_note_value = quick_build_state.setup_note_value;
        last_timing_mode = quick_build_state.setup_timing_mode;
        last_gate_percent = quick_build_state.setup_gate_percent;

    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_RECORD) {
        uint8_t slot = quick_build_state.seq_slot;

        // Fix pattern length: find actual highest step with notes
        uint16_t max_step = 0;
        for (uint16_t i = 0; i < quick_build_state.note_count; i++) {
            uint16_t step = NOTE_GET_TIMING(seq_active_presets[slot].notes[i].packed_timing_vel);
            if (step > max_step) max_step = step;
        }
        seq_active_presets[slot].pattern_length_16ths = max_step + 1;

        // Validate active seq preset (8-bit format)
        if (!active_validate_seq(&seq_active_presets[slot])) {
            dprintf("quick_build: seq validation failed, canceling\n");
            quick_build_cancel();
            return;
        }

        dprintf("quick_build: seq slot %d finished with %d notes, %d steps\n",
                slot, quick_build_state.note_count, seq_active_presets[slot].pattern_length_16ths);
        quick_build_state.has_saved_seq_build[slot] = true;
        quick_build_state.saved_seq_channel[slot] = channel_number;  // Remember channel at build time

        // Mark seq slot to play this quick build pattern
        seq_state[slot].current_preset_id = PRESET_ID_QUICK_BUILD;
        seq_state[slot].loaded_preset_id = PRESET_ID_QUICK_BUILD;

        // Save last-used settings for next build
        last_note_value = quick_build_state.setup_note_value;
        last_timing_mode = quick_build_state.setup_timing_mode;
        last_gate_percent = quick_build_state.setup_gate_percent;
    }

    // Show summary screen (stays on OLED until dismissed)
    quick_build_state.mode = QUICK_BUILD_SUMMARY;

    dprintf("quick_build: saved to RAM, showing summary\n");
}

// Erase the saved arp quick build for a specific slot
void quick_build_erase_arp(uint8_t slot) {
    if (slot >= MAX_ARP_QB_SLOTS) return;
    dprintf("quick_build: erasing saved arp build slot %d\n", slot);
    note_pool_free(POOL_SLOT_QB(slot));
    memset(&arp_qb_presets[slot], 0, sizeof(active_preset_t));
    quick_build_state.has_saved_arp_build[slot] = false;
    quick_build_state.mode = QUICK_BUILD_NONE;
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    quick_build_state.has_root = false;
    dprintf("quick_build: arp slot %d erased\n", slot);
}

// Load an arp quick build slot into the active preset for playback
void quick_build_load_arp_slot(uint8_t slot) {
    if (slot >= MAX_ARP_QB_SLOTS) return;
    if (!quick_build_state.has_saved_arp_build[slot]) return;

    // Allocate pool space for active arp and copy notes from QB storage
    uint16_t count = arp_qb_presets[slot].note_count;
    arp_preset_note_t *notes = note_pool_alloc(POOL_SLOT_ARP, count);
    if (!notes && count > 0) {
        dprintf("quick_build: pool alloc failed for arp load from QB slot %d\n", slot);
        return;
    }
    // Copy header fields
    arp_active_preset = arp_qb_presets[slot];
    arp_active_preset.notes = notes;
    // Copy note data
    if (count > 0) {
        memcpy(notes, arp_qb_presets[slot].notes, count * sizeof(arp_preset_note_t));
    }

    // Track which slot is active
    quick_build_state.active_arp_qb_slot = slot;

    // Mark arp to use this quick build preset
    arp_state.current_preset_id = PRESET_ID_QUICK_BUILD;
    arp_state.loaded_preset_id = PRESET_ID_QUICK_BUILD;

    dprintf("quick_build: loaded arp slot %d into active preset\n", slot);
}

// Erase the saved seq quick build for a specific slot
void quick_build_erase_seq(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) return;
    dprintf("quick_build: erasing saved seq build slot %d\n", slot);
    note_pool_free(POOL_SLOT_SEQ(slot));
    memset(&seq_active_presets[slot], 0, sizeof(active_preset_t));
    quick_build_state.has_saved_seq_build[slot] = false;
    quick_build_state.mode = QUICK_BUILD_NONE;
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    dprintf("quick_build: seq slot %d erased\n", slot);
}

// Advance to next step (with max step limit checks)
static void quick_build_advance_step(void) {
    quick_build_state.current_step++;

    // Check max step limits and auto-finish if reached
    if (quick_build_state.mode == QUICK_BUILD_ARP_RECORD) {
        if (quick_build_state.current_step >= MAX_ACTIVE_ARP_STEPS) {
            dprintf("quick_build: arp max steps reached (%d), finishing\n", MAX_ACTIVE_ARP_STEPS);
            quick_build_finish();
            return;
        }
        arp_active_preset.pattern_length_16ths = quick_build_state.current_step + 1;
        dprintf("quick_build: arp advanced to step %d\n", quick_build_state.current_step + 1);
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_RECORD) {
        if (quick_build_state.current_step >= MAX_ACTIVE_SEQ_STEPS) {
            dprintf("quick_build: seq max steps reached (%d), finishing\n", MAX_ACTIVE_SEQ_STEPS);
            quick_build_finish();
            return;
        }
        uint8_t slot = quick_build_state.seq_slot;
        seq_active_presets[slot].pattern_length_16ths = quick_build_state.current_step + 1;
        dprintf("quick_build: seq slot %d advanced to step %d\n", slot, quick_build_state.current_step + 1);
    }
}

// Handle incoming MIDI note during quick build
void quick_build_handle_note(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel) {
    // Handle root note selection phase (arp only)
    // Note press just sets candidate - user must press encoder/button to confirm
    if (quick_build_state.mode == QUICK_BUILD_ARP_ROOT) {
        quick_build_state.candidate_root = note;
        quick_build_state.candidate_ready = true;
        dprintf("quick_build: candidate root note %d, waiting for confirm\n", note);
        return;  // Don't record, don't transition yet
    }

    if (!quick_build_is_recording()) return;

    // raw_travel carries the velocity mode output (0-255, pre-curve) from the matrix scan.
    // This captures the actual played velocity regardless of velocity mode (speed, peak, fixed, blend).
    // On playback, apply_arp_velocity_pipeline() will re-apply the curve + range mapping.
    uint8_t record_velocity = (raw_travel > 0) ? (raw_travel >> 1) : velocity;  // Scale to 0-127

    // Track if we need to advance step (only if sustain/chord mode is NOT held)
    extern bool get_live_sustain_state(void);
    bool sustain_held = get_live_sustain_state();
    bool chord_mode = sustain_held || quick_build_state.encoder_chord_held;
    bool should_advance = false;

    if (quick_build_state.mode == QUICK_BUILD_ARP_RECORD) {
        // Check if we've hit max notes
        if (quick_build_state.note_count >= MAX_ACTIVE_ARP_NOTES) {
            dprintf("quick_build: arp max notes reached (%d), finishing\n", MAX_ACTIVE_ARP_NOTES);
            quick_build_finish();
            return;
        }

        // Calculate interval from root
        int16_t interval = note - quick_build_state.root_note;
        uint8_t interval_sign = (interval < 0) ? 1 : 0;
        uint8_t interval_mag = abs(interval) % 12;  // 0-11
        int8_t octave_offset = interval / 12;  // Can be negative

        // Pack note data
        arp_active_preset.notes[quick_build_state.note_count].packed_timing_vel =
            NOTE_PACK_TIMING_VEL(quick_build_state.current_step, record_velocity, interval_sign);
        arp_active_preset.notes[quick_build_state.note_count].note_octave =
            NOTE_PACK_NOTE_OCTAVE(interval_mag, octave_offset);

        quick_build_state.note_count++;
        arp_active_preset.note_count = quick_build_state.note_count;

        dprintf("quick_build: arp recorded note %d (interval %+d) at step %d\n",
                note, interval, quick_build_state.current_step + 1);

        // Advance step if not in chord mode
        if (!chord_mode) {
            should_advance = true;
        }

    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_RECORD) {
        uint8_t slot = quick_build_state.seq_slot;

        // Check max notes
        if (quick_build_state.note_count >= MAX_ACTIVE_SEQ_NOTES) {
            dprintf("quick_build: seq max notes reached (%d), finishing\n", MAX_ACTIVE_SEQ_NOTES);
            quick_build_finish();
            return;
        }

        // For sequencer: store absolute MIDI note
        uint8_t note_index = note % 12;  // 0-11 (C-B)
        int8_t octave_offset = note / 12;  // Direct MIDI octave (playback = octave*12 + note_index)

        // Pack note data
        seq_active_presets[slot].notes[quick_build_state.note_count].packed_timing_vel =
            NOTE_PACK_TIMING_VEL(quick_build_state.current_step, record_velocity, 0);
        seq_active_presets[slot].notes[quick_build_state.note_count].note_octave =
            NOTE_PACK_NOTE_OCTAVE(note_index, octave_offset);

        quick_build_state.note_count++;
        seq_active_presets[slot].note_count = quick_build_state.note_count;

        dprintf("quick_build: seq slot %d recorded note %d at step %d\n",
                slot, note, quick_build_state.current_step + 1);

        // Advance step if not in chord mode
        if (!chord_mode) {
            should_advance = true;
        }
    }

    // Actually advance the step if needed (after recording all notes in potential chord)
    // This is done AFTER the note recording so if multiple notes come in quickly (chord),
    // they all get recorded to the same step before advancing
    if (should_advance) {
        quick_build_advance_step();
    }
}

// Called when sustain pedal is released
void quick_build_handle_sustain_release(void) {
    if (!quick_build_is_active()) return;

    // Advance to next step when sustain is released
    quick_build_advance_step();
}

// Update function - call this from matrix_scan or similar periodic location
void quick_build_update(void) {
    if (!quick_build_is_recording()) return;

    // Check for sustain state changes (need external function)
    extern bool get_live_sustain_state(void);
    bool sustain_now = get_live_sustain_state();

    // Detect sustain release (was held, now released)
    if (quick_build_state.sustain_held_last_check && !sustain_now) {
        // Sustain was released - advance to next step
        quick_build_handle_sustain_release();
    }

    quick_build_state.sustain_held_last_check = sustain_now;
}

// =============================================================================
// QUICK BUILD: SETUP PHASE (PARAMETER SELECTION)
// =============================================================================

// Speed options: flat list of 9 combinations (note_value × timing_mode)
typedef struct {
    uint8_t note_value;
    uint8_t timing_mode;
    const char *name;
    const char *short_name;  // Abbreviated name for 2x OLED font (max 8 chars)
} speed_option_t;

static const speed_option_t speed_options[] = {
    { NOTE_VALUE_SIXTEENTH, TIMING_MODE_STRAIGHT, "1/16",       "1/16"    },
    { NOTE_VALUE_SIXTEENTH, TIMING_MODE_TRIPLET,  "1/16 Trp",   "1/16Trp" },
    { NOTE_VALUE_SIXTEENTH, TIMING_MODE_DOTTED,   "1/16 Dot",   "1/16Dot" },
    { NOTE_VALUE_EIGHTH,    TIMING_MODE_STRAIGHT, "1/8",        "1/8"     },
    { NOTE_VALUE_EIGHTH,    TIMING_MODE_TRIPLET,  "1/8 Trp",    "1/8 Trp" },
    { NOTE_VALUE_EIGHTH,    TIMING_MODE_DOTTED,   "1/8 Dot",    "1/8 Dot" },
    { NOTE_VALUE_QUARTER,   TIMING_MODE_STRAIGHT, "1/4",        "1/4"     },
    { NOTE_VALUE_QUARTER,   TIMING_MODE_TRIPLET,  "1/4 Trp",    "1/4 Trp" },
    { NOTE_VALUE_QUARTER,   TIMING_MODE_DOTTED,   "1/4 Dot",    "1/4 Dot" }
};
#define NUM_SPEED_OPTIONS 9

// Arp mode names
static const char *arp_mode_names[] = {
    "Single Synced",
    "Single Unsynced",
    "Chord Synced",
    "Chord Unsynced",
    "Chord Advanced"
};
#define NUM_ARP_MODES ARPMODE_COUNT

// Get the current speed option index from note_value + timing_mode
static uint8_t get_speed_index(uint8_t note_value, uint8_t timing_mode) {
    for (uint8_t i = 0; i < NUM_SPEED_OPTIONS; i++) {
        if (speed_options[i].note_value == note_value &&
            speed_options[i].timing_mode == timing_mode) {
            return i;
        }
    }
    return 0;  // Default to 16th straight
}

// How many setup parameters for current mode
static uint8_t get_setup_param_count(void) {
    if (quick_build_state.mode == QUICK_BUILD_ARP_SETUP) return 3;  // mode, speed, gate
    if (quick_build_state.mode == QUICK_BUILD_SEQ_SETUP) return 2;  // speed, gate
    return 0;
}

// Get the name of the current parameter being configured
const char* quick_build_get_param_name(void) {
    if (quick_build_state.mode == QUICK_BUILD_ARP_SETUP) {
        switch (quick_build_state.setup_param_index) {
            case 0: return "Arp Mode";
            case 1: return "Speed";
            case 2: return "Gate Length";
        }
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_SETUP) {
        switch (quick_build_state.setup_param_index) {
            case 0: return "Speed";
            case 1: return "Gate Length";
        }
    }
    return "";
}

// Get the description text (small font top line)
const char* quick_build_get_param_desc1(void) {
    if (quick_build_state.mode == QUICK_BUILD_ARP_SETUP) {
        switch (quick_build_state.setup_param_index) {
            case 0: return "How arp responds to";
            case 1: return "Pattern rate of";
            case 2: return "Length which notes";
        }
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_SETUP) {
        switch (quick_build_state.setup_param_index) {
            case 0: return "Pattern rate of";
            case 1: return "Length which notes";
        }
    }
    return "";
}

const char* quick_build_get_param_desc2(void) {
    if (quick_build_state.mode == QUICK_BUILD_ARP_SETUP) {
        switch (quick_build_state.setup_param_index) {
            case 0: return "multiple midi notes";
            case 1: return "the arpeggiator";
            case 2: return "are sustained";
        }
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_SETUP) {
        switch (quick_build_state.setup_param_index) {
            case 0: return "the step sequencer";
            case 1: return "are sustained";
        }
    }
    return "";
}

// Get the current value display string for the active parameter
const char* quick_build_get_param_value(void) {
    static char buf[16];
    if (quick_build_state.mode == QUICK_BUILD_ARP_SETUP) {
        switch (quick_build_state.setup_param_index) {
            case 0: // Arp mode
                if (quick_build_state.setup_arp_mode < NUM_ARP_MODES)
                    return arp_mode_names[quick_build_state.setup_arp_mode];
                return "Unknown";
            case 1: { // Speed
                uint8_t idx = get_speed_index(quick_build_state.setup_note_value,
                                              quick_build_state.setup_timing_mode);
                return speed_options[idx].name;
            }
            case 2: // Gate
                snprintf(buf, sizeof(buf), "%d%%", quick_build_state.setup_gate_percent);
                return buf;
        }
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_SETUP) {
        switch (quick_build_state.setup_param_index) {
            case 0: { // Speed
                uint8_t idx = get_speed_index(quick_build_state.setup_note_value,
                                              quick_build_state.setup_timing_mode);
                return speed_options[idx].name;
            }
            case 1: // Gate
                snprintf(buf, sizeof(buf), "%d%%", quick_build_state.setup_gate_percent);
                return buf;
        }
    }
    return "";
}

// Get shortened value string for 2x big font display (speed/gate only)
// Returns NULL for params that should use normal font (e.g. arp mode)
const char* quick_build_get_param_value_big(void) {
    static char buf[16];
    bool is_arp = (quick_build_state.mode == QUICK_BUILD_ARP_SETUP);
    uint8_t param = quick_build_state.setup_param_index;

    bool is_speed_param = (is_arp && param == 1) || (!is_arp && param == 0);
    bool is_gate_param = (is_arp && param == 2) || (!is_arp && param == 1);

    if (is_speed_param) {
        uint8_t idx = get_speed_index(quick_build_state.setup_note_value,
                                      quick_build_state.setup_timing_mode);
        return speed_options[idx].short_name;
    }
    if (is_gate_param) {
        snprintf(buf, sizeof(buf), "%d%%", quick_build_state.setup_gate_percent);
        return buf;
    }
    return NULL;  // Arp mode: use normal font
}

// Cycle the current parameter value (encoder rotation)
static void quick_build_cycle_param(bool forward) {
    bool is_arp = (quick_build_state.mode == QUICK_BUILD_ARP_SETUP);
    uint8_t param = quick_build_state.setup_param_index;

    // Map seq param indices: seq has no arp mode, so param 0=speed, 1=gate
    // Arp: 0=mode, 1=speed, 2=gate
    bool is_mode_param = (is_arp && param == 0);
    bool is_speed_param = (is_arp && param == 1) || (!is_arp && param == 0);
    bool is_gate_param = (is_arp && param == 2) || (!is_arp && param == 1);

    if (is_mode_param) {
        if (forward) {
            quick_build_state.setup_arp_mode = (quick_build_state.setup_arp_mode + 1) % NUM_ARP_MODES;
        } else {
            if (quick_build_state.setup_arp_mode == 0)
                quick_build_state.setup_arp_mode = NUM_ARP_MODES - 1;
            else
                quick_build_state.setup_arp_mode--;
        }
    } else if (is_speed_param) {
        uint8_t idx = get_speed_index(quick_build_state.setup_note_value,
                                      quick_build_state.setup_timing_mode);
        if (forward) {
            idx = (idx + 1) % NUM_SPEED_OPTIONS;
        } else {
            if (idx == 0) idx = NUM_SPEED_OPTIONS - 1;
            else idx--;
        }
        quick_build_state.setup_note_value = speed_options[idx].note_value;
        quick_build_state.setup_timing_mode = speed_options[idx].timing_mode;
    } else if (is_gate_param) {
        if (forward) {
            if (quick_build_state.setup_gate_percent < 100)
                quick_build_state.setup_gate_percent += 5;
            else
                quick_build_state.setup_gate_percent = 5;  // Wrap around
        } else {
            if (quick_build_state.setup_gate_percent > 5)
                quick_build_state.setup_gate_percent -= 5;
            else
                quick_build_state.setup_gate_percent = 100;  // Wrap around
        }
    }
}

// Confirm current parameter and advance to next (or enter recording)
void quick_build_confirm_param(void) {
    uint8_t total = get_setup_param_count();
    quick_build_state.setup_param_index++;

    if (quick_build_state.setup_param_index >= total) {
        // All parameters confirmed - enter recording phase
        quick_build_enter_recording();
    } else {
        dprintf("quick_build: param %d/%d confirmed, advancing\n",
                quick_build_state.setup_param_index, total);
    }
}

// =============================================================================
// QUICK BUILD: ENCODER HANDLERS
// =============================================================================

void quick_build_handle_encoder(bool clockwise) {
    if (quick_build_is_setup()) {
        // Setup phase: cycle parameter values
        quick_build_cycle_param(clockwise);
    } else if (quick_build_is_recording()) {
        // Recording phase: CW = skip step, CCW = undo step
        if (clockwise) {
            quick_build_skip_step();
        } else {
            quick_build_undo_step();
        }
    }
}

// Confirm root note and enter recording phase
void quick_build_confirm_root(void) {
    if (quick_build_state.mode != QUICK_BUILD_ARP_ROOT) return;
    if (!quick_build_state.candidate_ready) return;

    quick_build_state.root_note = quick_build_state.candidate_root;
    quick_build_state.has_root = true;
    quick_build_state.mode = QUICK_BUILD_ARP_RECORD;
    dprintf("quick_build: root note confirmed as %d, entering recording\n", quick_build_state.root_note);
}

void quick_build_handle_encoder_click(bool pressed) {
    if (quick_build_state.mode == QUICK_BUILD_SUMMARY) {
        // Summary screen: click dismisses
        if (pressed) {
            quick_build_dismiss_summary();
        }
        return;
    }
    if (quick_build_state.mode == QUICK_BUILD_ARP_SETUP ||
        quick_build_state.mode == QUICK_BUILD_SEQ_SETUP) {
        // Setup param phase: click confirms parameter (on press only)
        if (pressed) {
            quick_build_confirm_param();
        }
    } else if (quick_build_state.mode == QUICK_BUILD_ARP_ROOT) {
        // Root note phase: click confirms root (on press only)
        if (pressed) {
            quick_build_confirm_root();
        }
    } else if (quick_build_is_recording()) {
        // Recording phase: momentary chord mode
        quick_build_state.encoder_chord_held = pressed;

        // On release, advance step (same as sustain release behavior)
        if (!pressed && quick_build_state.note_count > 0) {
            // Only advance if notes were recorded during the chord hold
            // Check if current step has any notes
            bool has_notes_on_step = false;
            if (quick_build_state.mode == QUICK_BUILD_ARP_RECORD) {
                for (uint16_t i = 0; i < quick_build_state.note_count; i++) {
                    if (NOTE_GET_TIMING(arp_active_preset.notes[i].packed_timing_vel)
                        == quick_build_state.current_step) {
                        has_notes_on_step = true;
                        break;
                    }
                }
            } else if (quick_build_state.mode == QUICK_BUILD_SEQ_RECORD) {
                uint8_t slot = quick_build_state.seq_slot;
                for (uint16_t i = 0; i < quick_build_state.note_count; i++) {
                    if (NOTE_GET_TIMING(seq_active_presets[slot].notes[i].packed_timing_vel)
                        == quick_build_state.current_step) {
                        has_notes_on_step = true;
                        break;
                    }
                }
            }

            if (has_notes_on_step) {
                quick_build_advance_step();
            }
        }
    }
}

// =============================================================================
// QUICK BUILD: SKIP AND UNDO STEP
// =============================================================================

void quick_build_skip_step(void) {
    if (!quick_build_is_recording()) return;

    // Advance to next step without recording a note (empty step)
    quick_build_advance_step();
    dprintf("quick_build: skipped to step %d\n", quick_build_state.current_step + 1);
}

void quick_build_undo_step(void) {
    if (!quick_build_is_recording()) return;
    if (quick_build_state.current_step == 0 && quick_build_state.note_count == 0) return;

    // Find the step to undo: if current step has notes, undo current; else undo previous
    uint16_t target_step = quick_build_state.current_step;

    // Check if current step has any notes
    bool current_has_notes = false;
    if (quick_build_state.mode == QUICK_BUILD_ARP_RECORD) {
        for (uint16_t i = 0; i < quick_build_state.note_count; i++) {
            if (NOTE_GET_TIMING(arp_active_preset.notes[i].packed_timing_vel) == target_step) {
                current_has_notes = true;
                break;
            }
        }
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_RECORD) {
        uint8_t slot = quick_build_state.seq_slot;
        for (uint16_t i = 0; i < quick_build_state.note_count; i++) {
            if (NOTE_GET_TIMING(seq_active_presets[slot].notes[i].packed_timing_vel) == target_step) {
                current_has_notes = true;
                break;
            }
        }
    }

    // If current step is empty, go back to previous step
    if (!current_has_notes && target_step > 0) {
        target_step--;
    }

    // Remove all notes on the target step
    uint8_t removed = 0;
    if (quick_build_state.mode == QUICK_BUILD_ARP_RECORD) {
        uint16_t write_idx = 0;
        for (uint16_t i = 0; i < quick_build_state.note_count; i++) {
            if (NOTE_GET_TIMING(arp_active_preset.notes[i].packed_timing_vel) != target_step) {
                if (write_idx != i) {
                    arp_active_preset.notes[write_idx] = arp_active_preset.notes[i];
                }
                write_idx++;
            } else {
                removed++;
            }
        }
        quick_build_state.note_count = write_idx;
        arp_active_preset.note_count = write_idx;
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_RECORD) {
        uint8_t slot = quick_build_state.seq_slot;
        uint16_t write_idx = 0;
        for (uint16_t i = 0; i < quick_build_state.note_count; i++) {
            if (NOTE_GET_TIMING(seq_active_presets[slot].notes[i].packed_timing_vel) != target_step) {
                if (write_idx != i) {
                    seq_active_presets[slot].notes[write_idx] = seq_active_presets[slot].notes[i];
                }
                write_idx++;
            } else {
                removed++;
            }
        }
        quick_build_state.note_count = write_idx;
        seq_active_presets[slot].note_count = write_idx;
    }

    // Move step back to the target
    quick_build_state.current_step = target_step;

    // Update pattern length
    if (quick_build_state.mode == QUICK_BUILD_ARP_RECORD) {
        arp_active_preset.pattern_length_16ths = target_step + 1;
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ_RECORD) {
        seq_active_presets[quick_build_state.seq_slot].pattern_length_16ths = target_step + 1;
    }

    dprintf("quick_build: undid step %d (removed %d notes), now at step %d\n",
            target_step + 1, removed, quick_build_state.current_step + 1);
}

// =============================================================================
// SEQ START SLOT (for quick build playback - no preset reload)
// =============================================================================

void seq_start_slot(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) return;

    if (seq_state[slot].active) {
        if (seq_state[slot].deferred_start_pending) {
            // Double-press while deferred: force start at next step of running seq (polyrhythm mode)
            seq_state[slot].deferred_start_pending = false;
            seq_state[slot].has_looped = false;
            seq_state[slot].current_position_16ths = 0;
            // Find a running seq and align to its next step time
            bool found_running = false;
            for (uint8_t s = 0; s < MAX_SEQ_SLOTS; s++) {
                if (s == slot) continue;
                if (seq_state[s].active && !seq_state[s].deferred_start_pending) {
                    seq_state[slot].pattern_start_time = seq_state[s].next_note_time;
                    seq_state[slot].next_note_time = seq_state[s].next_note_time;
                    found_running = true;
                    dprintf("seq: slot %d force-start at next step of slot %d (polyrhythm)\n", slot, s);
                    break;
                }
            }
            if (!found_running) {
                // No running seq found, start immediately
                uint32_t now = timer_read32();
                seq_state[slot].pattern_start_time = now;
                seq_state[slot].next_note_time = now;
                dprintf("seq: slot %d force-started immediately (no running seq)\n", slot);
            }
        } else {
            // Already playing: toggle off
            seq_stop(slot);
            dprintf("seq: slot %d toggled OFF\n", slot);
        }
        return;
    }

    // Start the slot directly (preset already in RAM)
    seq_state[slot].active = true;
    seq_state[slot].current_position_16ths = 0;
    seq_state[slot].has_looped = false;
    seq_state[slot].deferred_start_pending = false;

    // Use the channel from when the seq was built (not the current keyboard channel)
    seq_state[slot].locked_channel = quick_build_state.saved_seq_channel[slot];
    seq_state[slot].locked_velocity_min = he_velocity_min;
    seq_state[slot].locked_velocity_max = he_velocity_max;
    seq_state[slot].locked_transpose = 0;

    // Apply deferred/group/immediate start logic (same as factory presets)
    seq_apply_start_logic(slot);

    dprintf("seq: started slot %d directly (quick build, ch:%d vel:%d-%d deferred:%d)\n",
            slot, seq_state[slot].locked_channel,
            seq_state[slot].locked_velocity_min, seq_state[slot].locked_velocity_max,
            seq_state[slot].deferred_start_pending);
}

// =============================================================================
// VELOCITY PIPELINE FOR ARP/SEQ PLAYBACK
// =============================================================================

// Apply velocity curve + live vel range to arp preset velocity
uint8_t apply_arp_velocity_pipeline(uint8_t preset_velocity_0_127) {
    // Scale 0-127 to 0-255 to match velocity curve input range
    uint16_t travel_equiv = (uint16_t)preset_velocity_0_127 * 2;
    if (travel_equiv > 255) travel_equiv = 255;

    // Apply curve (0-255 -> 0-255)
    extern uint8_t apply_curve(uint8_t input, uint8_t curve_index);
    uint8_t curved = apply_curve((uint8_t)travel_equiv, he_velocity_curve);

    // Map to live velocity range
    uint8_t range = he_velocity_max - he_velocity_min;
    int16_t velocity = he_velocity_min + ((int16_t)curved * range) / 255;

    if (velocity < 1) velocity = 1;
    if (velocity > 127) velocity = 127;
    return (uint8_t)velocity;
}

// Apply velocity curve + locked per-slot vel range to seq preset velocity
uint8_t apply_seq_velocity_pipeline(uint8_t preset_velocity_0_127, uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) return preset_velocity_0_127;

    // Scale 0-127 to 0-255 to match velocity curve input range
    uint16_t travel_equiv = (uint16_t)preset_velocity_0_127 * 2;
    if (travel_equiv > 255) travel_equiv = 255;

    // Apply live velocity curve (0-255 -> 0-255)
    extern uint8_t apply_curve(uint8_t input, uint8_t curve_index);
    uint8_t curved = apply_curve((uint8_t)travel_equiv, he_velocity_curve);

    // Map to locked per-slot velocity range
    uint8_t min_vel = seq_state[slot].locked_velocity_min;
    uint8_t max_vel = seq_state[slot].locked_velocity_max;
    uint8_t range = max_vel - min_vel;
    int16_t velocity = min_vel + ((int16_t)curved * range) / 255;

    if (velocity < 1) velocity = 1;
    if (velocity > 127) velocity = 127;
    return (uint8_t)velocity;
}
