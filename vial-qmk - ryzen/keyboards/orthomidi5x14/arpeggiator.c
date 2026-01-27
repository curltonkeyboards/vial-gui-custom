// arpeggiator.c - Arpeggiator implementation for orthomidi5x14
// BPM-synced programmable arpeggiator with preset system

#include QMK_KEYBOARD_H
#include "orthomidi5x14.h"
#include "process_midi.h"
#include "timer.h"
#include "eeprom.h"
#include <string.h>
#include <stdlib.h>

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

// =============================================================================
// QUICK BUILD SYSTEM
// =============================================================================

// Quick build state (initialized to all zeros/false)
quick_build_state_t quick_build_state = {
    .mode = QUICK_BUILD_NONE,
    .seq_slot = 0,
    .current_step = 0,
    .note_count = 0,
    .root_note = 0,
    .has_root = false,
    .sustain_held_last_check = false,
    .button_press_time = 0,
    .has_saved_build = false
};

// Efficient RAM storage: Only active presets loaded
arp_preset_t arp_active_preset;           // 1 slot for arpeggiator (200 bytes)
seq_preset_t seq_active_presets[MAX_SEQ_SLOTS];  // 8 slots for sequencers (8 × 392 = 3136 bytes)

// External references
extern uint8_t live_notes[MAX_LIVE_NOTES][3];  // [channel, note, velocity]
extern uint8_t live_note_count;
extern uint32_t current_bpm;  // BPM in format: actual_bpm * 100000
extern uint8_t channel_number;  // Current MIDI channel
extern int8_t transpose_number;  // Global transpose
extern uint8_t he_velocity_min;  // Global HE velocity minimum
extern uint8_t he_velocity_max;  // Global HE velocity maximum

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
            arp_note_count++;
            dprintf("arp: added note ch:%d note:%d vel:%d off_time:%lu (count:%d)\n",
                    channel, note, velocity, note_off_time, arp_note_count);
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
            midi_send_noteoff_arp(arp_notes[i].channel,
                                 arp_notes[i].note,
                                 arp_notes[i].velocity);

            // Mark as inactive
            arp_notes[i].active = false;
            arp_note_count--;

            dprintf("arp: gated off note ch:%d note:%d\n",
                    arp_notes[i].channel, arp_notes[i].note);
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
// Preset IDs: 0-47 (factory), 48-67 (user, 20 slots)
bool arp_load_preset_into_slot(uint8_t preset_id) {
    if (preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: load_preset_into_slot - invalid preset_id %d (max %d)\n", preset_id, MAX_ARP_PRESETS - 1);
        return false;
    }

    // Check if already loaded
    if (arp_state.loaded_preset_id == preset_id) {
        dprintf("arp: preset %d already loaded\n", preset_id);
        return true;
    }

    // Load preset based on type
    if (preset_id >= USER_ARP_PRESET_START) {
        // User preset: load from EEPROM (48-67)
        if (!arp_load_preset_from_eeprom(preset_id, &arp_active_preset)) {
            dprintf("arp: failed to load user preset %d from EEPROM\n", preset_id);
            return false;
        }
    } else {
        // Factory preset: load from PROGMEM (0-47)
        arp_load_factory_preset(preset_id, &arp_active_preset);
    }

    arp_state.loaded_preset_id = preset_id;
    dprintf("arp: loaded preset %d into active slot\n", preset_id);
    return true;
}

// Load sequencer preset into specified slot (lazy-load from EEPROM or factory data)
// Preset IDs: 68-115 (factory, 48 slots), 116-135 (user, 20 slots)
bool seq_load_preset_into_slot(uint8_t preset_id, uint8_t slot) {
    if (preset_id < 68 || preset_id >= MAX_SEQ_PRESETS || slot >= MAX_SEQ_SLOTS) {
        dprintf("seq: load_preset_into_slot - invalid preset_id %d or slot %d\n", preset_id, slot);
        return false;
    }

    // Check if already loaded in this slot
    if (seq_state[slot].loaded_preset_id == preset_id) {
        dprintf("seq: preset %d already loaded in slot %d\n", preset_id, slot);
        return true;
    }

    // Load preset based on type
    if (preset_id >= USER_SEQ_PRESET_START) {
        // User preset: load from EEPROM (116-135)
        if (!seq_load_preset_from_eeprom(preset_id, &seq_active_presets[slot])) {
            dprintf("seq: failed to load user preset %d from EEPROM\n", preset_id);
            return false;
        }
    } else {
        // Factory preset: load from PROGMEM (68-115 maps to internal 0-47)
        uint8_t factory_id = preset_id - 68;
        seq_load_factory_preset(factory_id, &seq_active_presets[slot]);
    }

    seq_state[slot].loaded_preset_id = preset_id;
    dprintf("seq: loaded preset %d into slot %d\n", preset_id, slot);
    return true;
}

// Find an available sequencer slot (-1 if none available)
int8_t seq_find_available_slot(void) {
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
        // Preset is playing: toggle it off
        seq_stop(existing_slot);
        dprintf("seq: toggled OFF preset %d from slot %d\n", preset_id, existing_slot);
    } else {
        // Preset not playing: find available slot and start
        int8_t slot = seq_find_available_slot();
        if (slot < 0) {
            dprintf("seq: no available slots for preset %d\n", preset_id);
            return;
        }

        // Initialize BPM if not set
        if (current_bpm == 0) {
            current_bpm = 12000000;  // 120.00000 BPM
            dprintf("seq: initialized BPM to 120\n");
        }

        // Set current preset for this slot
        seq_state[slot].current_preset_id = preset_id;
        seq_start(preset_id);
        dprintf("seq: started preset %d in slot %d\n", preset_id, slot);
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
    uint8_t timing;
    uint8_t velocity;
    int8_t note_index;      // For arp: interval with sign; For seq: note 0-11
    int8_t octave_offset;
} unpacked_note_t;

static void unpack_note(const arp_preset_note_t *packed, unpacked_note_t *unpacked, bool is_arpeggiator) {
    unpacked->timing = NOTE_GET_TIMING(packed->packed_timing_vel);
    unpacked->velocity = NOTE_GET_VELOCITY(packed->packed_timing_vel);

    uint8_t note_val = NOTE_GET_NOTE(packed->note_octave);
    unpacked->octave_offset = NOTE_GET_OCTAVE(packed->note_octave);

    if (is_arpeggiator) {
        // For arpeggiator: apply sign bit to interval
        uint8_t sign = NOTE_GET_SIGN(packed->packed_timing_vel);
        unpacked->note_index = sign ? -(int8_t)note_val : (int8_t)note_val;
    } else {
        // For step sequencer: note is unsigned 0-11
        unpacked->note_index = note_val;
    }
}

// Calculate milliseconds per 16th note based on current BPM and timing mode
// Uses arp_state.rate_override if set, otherwise uses preset values
static uint32_t get_ms_per_16th(const arp_preset_t *preset) {
    uint32_t actual_bpm = get_effective_bpm() / 100000;
    if (actual_bpm == 0) actual_bpm = 120;

    // Base calculation: quarter note duration / 4 = 16th note duration
    uint32_t base_ms = (60000 / actual_bpm) / 4;

    // Determine note_value and timing_mode - use override if set
    uint8_t note_value, timing_mode;
    if (arp_state.rate_override != 0) {
        // Extract note value and timing mode from rate_override
        note_value = arp_state.rate_override & ~TIMING_MODE_MASK;
        timing_mode = arp_state.rate_override & TIMING_MODE_MASK;
    } else {
        // Use preset values
        note_value = preset->note_value;
        timing_mode = preset->timing_mode;
    }

    // Apply note value multiplier (quarter=4x, eighth=2x, sixteenth=1x)
    uint8_t multiplier = 1;
    switch (note_value) {
        case NOTE_VALUE_QUARTER:
            multiplier = 4;  // Quarter notes are 4× 16ths
            break;
        case NOTE_VALUE_EIGHTH:
            multiplier = 2;  // Eighth notes are 2× 16ths
            break;
        case NOTE_VALUE_SIXTEENTH:
        default:
            multiplier = 1;  // Sixteenth notes are 1× 16ths
            break;
    }
    base_ms *= multiplier;

    // Apply timing mode (triplet or dotted)
    if (timing_mode & TIMING_MODE_TRIPLET) {
        // Triplet timing: compress to 2/3 of normal duration
        base_ms = (base_ms * 2) / 3;
    } else if (timing_mode & TIMING_MODE_DOTTED) {
        // Dotted timing: extend to 3/2 of normal duration
        base_ms = (base_ms * 3) / 2;
    }

    return base_ms;
}

// Calculate milliseconds per 16th note for sequencer presets
// Uses seq_state[slot].rate_override if set, otherwise uses preset values
static uint32_t seq_get_ms_per_16th(const seq_preset_t *preset, uint8_t slot) {
    uint32_t actual_bpm = get_effective_bpm() / 100000;
    if (actual_bpm == 0) actual_bpm = 120;

    // Base calculation: quarter note duration / 4 = 16th note duration
    uint32_t base_ms = (60000 / actual_bpm) / 4;

    // Determine note_value and timing_mode - use override if set
    uint8_t note_value, timing_mode;
    if (slot < MAX_SEQ_SLOTS && seq_state[slot].rate_override != 0) {
        // Extract note value and timing mode from rate_override
        note_value = seq_state[slot].rate_override & ~TIMING_MODE_MASK;
        timing_mode = seq_state[slot].rate_override & TIMING_MODE_MASK;
    } else {
        // Use preset values
        note_value = preset->note_value;
        timing_mode = preset->timing_mode;
    }

    // Apply note value multiplier (quarter=4x, eighth=2x, sixteenth=1x)
    uint8_t multiplier = 1;
    switch (note_value) {
        case NOTE_VALUE_QUARTER:
            multiplier = 4;  // Quarter notes are 4× 16ths
            break;
        case NOTE_VALUE_EIGHTH:
            multiplier = 2;  // Eighth notes are 2× 16ths
            break;
        case NOTE_VALUE_SIXTEENTH:
        default:
            multiplier = 1;  // Sixteenth notes are 1× 16ths
            break;
    }
    base_ms *= multiplier;

    // Apply timing mode (triplet or dotted)
    if (timing_mode & TIMING_MODE_TRIPLET) {
        // Triplet timing: compress to 2/3 of normal duration
        base_ms = (base_ms * 2) / 3;
    } else if (timing_mode & TIMING_MODE_DOTTED) {
        // Dotted timing: extend to 3/2 of normal duration
        base_ms = (base_ms * 3) / 2;
    }

    return base_ms;
}


void arp_init(void) {
    // Clear arp notes
    memset(arp_notes, 0, sizeof(arp_notes));
    arp_note_count = 0;

    // Clear active preset slots
    memset(&arp_active_preset, 0, sizeof(arp_preset_t));
    memset(seq_active_presets, 0, sizeof(seq_active_presets));

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

    if (preset_id >= MAX_ARP_PRESETS) {
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
    arp_state.notes_released = false;
    arp_state.next_note_time = timer_read32();  // Start immediately

    // Reset chord unsynced per-note tracking on fresh start
    reset_unsynced_notes();

    dprintf("arp: started preset %d\n", preset_id);
}

void arp_stop(void) {
    if (!arp_state.active) return;

    // Behavior depends on sync mode
    if (arp_state.sync_mode) {
        // Finish gates: let current notes complete their gate length
        // process_arp_note_offs() will handle this naturally
        dprintf("arp: stopping (sync mode - finishing gates)\n");
    } else {
        // Next step: immediately stop on next step boundary
        // For now, stop immediately (can refine later)
        dprintf("arp: stopping (unsync mode - immediate)\n");
    }

    arp_state.active = false;
    arp_state.latch_mode = false;
    arp_state.key_held = false;
    arp_state.notes_released = false;

    // Note: We don't immediately send note-offs here
    // Let the gate timing system handle it naturally
}

void arp_update(void) {
    // Process any notes that need to be gated off
    process_arp_note_offs();

    // If not active, nothing to do
    if (!arp_state.active) return;

    // Use the active preset slot (already loaded by arp_start)
    arp_preset_t *preset = &arp_active_preset;

    // Check requirements based on preset type
    if (preset->preset_type == PRESET_TYPE_ARPEGGIATOR) {
        if (live_note_count == 0) {
            // No notes held - mark for pattern restart when notes return
            // Don't stop: arp stays armed while button is held or latched
            arp_state.notes_released = true;
            return;
        }

        // Notes are held - check if we need to restart pattern from step 0
        if (arp_state.notes_released) {
            arp_state.notes_released = false;
            arp_state.current_position_16ths = 0;
            arp_state.current_note_in_chord = 0;
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
            for (uint8_t i = 0; i < preset->note_count; i++) {
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

                uint8_t raw_travel = unpacked.velocity;

                // Send note-on
                midi_send_noteon_arp(unsynced_notes[u].channel, (uint8_t)final_note, raw_travel, raw_travel);

                // Add to arp_notes for gate tracking
                uint32_t note_off_time = current_time + gate_duration_ms;
                add_arp_note(unsynced_notes[u].channel, (uint8_t)final_note, raw_travel, note_off_time);
            }

            // Advance this note's position
            unsynced_notes[u].current_position_16ths++;
            if (unsynced_notes[u].current_position_16ths >= preset->pattern_length_16ths) {
                unsynced_notes[u].current_position_16ths = 0;
            }

            // Set this note's next note time
            unsynced_notes[u].next_note_time = current_time + ms_per_16th;
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

    // Special case: Random preset - randomize note indices
    if (arp_state.current_preset_id == 3) {  // Random 8ths preset
        for (uint8_t i = 0; i < preset->note_count; i++) {
            // Extract current octave_offset from packed field
            int8_t current_octave = NOTE_GET_OCTAVE(preset->notes[i].note_octave);

            // Generate random semitone offset (0-11 for notes within an octave)
            uint8_t random_note_index = rand() % 12;

            // Repack note_octave with new random note_index, preserving octave_offset
            preset->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(random_note_index, current_octave);
        }
    }

    // Find notes to play at current position
    uint8_t notes_to_play[MAX_ARP_PRESET_NOTES];
    uint8_t note_count_to_play = 0;
    unpacked_note_t unpacked_notes[MAX_ARP_PRESET_NOTES];

    bool is_arpeggiator = (preset->preset_type == PRESET_TYPE_ARPEGGIATOR);

    for (uint8_t i = 0; i < preset->note_count; i++) {
        // Unpack the note to check its timing
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
            for (uint8_t i = 0; i < note_count_to_play; i++) {
                uint8_t preset_note_idx = notes_to_play[i];
                unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                // Calculate absolute MIDI note: (octave × 12) + note_index
                // note_index = 0-11 (C-B), octave_offset = -8 to +7
                int16_t midi_note = (note->octave_offset * 12) + note->note_index;

                // Clamp to MIDI range (0-127)
                if (midi_note < 0) midi_note = 0;
                if (midi_note > 127) midi_note = 127;

                uint8_t raw_travel = note->velocity;
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

                    for (uint8_t i = 0; i < note_count_to_play; i++) {
                        uint8_t preset_note_idx = notes_to_play[i];
                        unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                        // Calculate note: master + semitone_offset + octave_offset
                        int16_t semitone_offset = note->note_index;
                        int16_t octave_semitones = note->octave_offset * 12;
                        int16_t final_note = master_note + semitone_offset + octave_semitones;

                        // Clamp to MIDI range
                        if (final_note < 0) final_note = 0;
                        if (final_note > 127) final_note = 127;

                        uint8_t raw_travel = note->velocity;

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
                    for (uint8_t i = 0; i < note_count_to_play; i++) {
                        uint8_t preset_note_idx = notes_to_play[i];
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

                            uint8_t raw_travel = note->velocity;

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

                    uint8_t preset_note_idx = notes_to_play[0];  // Use first step at this position
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

                    uint8_t raw_travel = note->velocity;

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

                    // Check if we've played all notes for this step
                    if (arp_state.current_note_in_chord >= live_note_count) {
                        // Reset for next step and advance pattern position
                        arp_state.current_note_in_chord = 0;

                        // Advance pattern position
                        arp_state.current_position_16ths++;

                        // Check for loop
                        if (arp_state.current_position_16ths >= preset->pattern_length_16ths) {
                            arp_state.current_position_16ths = 0;
                            arp_state.pattern_start_time = current_time;
                            dprintf("arp: pattern loop\n");
                        }
                    }

                    // Next note at base rate (each note gets full step timing)
                    arp_state.next_note_time = current_time + ms_per_16th;

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
        arp_state.current_position_16ths = 0;
        arp_state.pattern_start_time = current_time;
        dprintf("arp: pattern loop\n");
    }

    // Calculate next note time
    uint32_t ms_per_16th_final = get_ms_per_16th(preset);
    arp_state.next_note_time = current_time + ms_per_16th_final;
}

// =============================================================================
// STEP SEQUENCER FUNCTIONS
// =============================================================================

void seq_start(uint8_t preset_id) {
    // QUICK BUILD HOOK: Cancel quick build if active (seq play takes priority)
    if (quick_build_is_active()) {
        quick_build_cancel();
    }

    if (preset_id < 68 || preset_id >= MAX_SEQ_PRESETS) {
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
    seq_state[slot].pattern_start_time = timer_read32();
    seq_state[slot].next_note_time = timer_read32();  // Start immediately

    // Lock in global values when sequencer starts
    seq_state[slot].locked_channel = channel_number;
    seq_state[slot].locked_velocity_min = he_velocity_min;
    seq_state[slot].locked_velocity_max = he_velocity_max;
    seq_state[slot].locked_transpose = 0;  // Always starts at 0, changes only with modifier

    dprintf("seq: started preset %d in slot %d (ch:%d vel:%d-%d trans:%d)\n",
            preset_id, slot, seq_state[slot].locked_channel,
            seq_state[slot].locked_velocity_min, seq_state[slot].locked_velocity_max,
            seq_state[slot].locked_transpose);
}

void seq_stop(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) return;

    if (seq_state[slot].active) {
        seq_state[slot].active = false;
        dprintf("seq: stopped slot %d\n", slot);
    }
}

void seq_stop_all(void) {
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_state[i].active) {
            seq_state[i].active = false;
            dprintf("seq: stopped slot %d\n", i);
        }
    }
    dprintf("seq: stopped all sequencers\n");
}

void seq_update(void) {
    // Update all active sequencer slots
    for (uint8_t slot = 0; slot < MAX_SEQ_SLOTS; slot++) {
        if (!seq_state[slot].active) continue;

        // Get preset for this slot
        seq_preset_t *preset = &seq_active_presets[slot];

        // Check if it's time to play next note
        uint32_t current_time = timer_read32();
        if (current_time < seq_state[slot].next_note_time) {
            continue;  // Not yet time
        }

        // Find notes to play at current position
        uint8_t notes_to_play[MAX_SEQ_PRESET_NOTES];
        uint8_t note_count_to_play = 0;
        unpacked_note_t unpacked_notes[MAX_SEQ_PRESET_NOTES];

        for (uint8_t i = 0; i < preset->note_count; i++) {
            unpack_note(&preset->notes[i], &unpacked_notes[i], false);  // false = step sequencer

            if (unpacked_notes[i].timing == seq_state[slot].current_position_16ths) {
                notes_to_play[note_count_to_play++] = i;
            }
        }

        // Play notes (step sequencer uses absolute MIDI notes)
        if (note_count_to_play > 0) {
            // Calculate gate length
            uint8_t gate_percent = (seq_state[slot].master_gate_override > 0) ?
                                   seq_state[slot].master_gate_override :
                                   preset->gate_length_percent;

            uint32_t ms_per_16th = seq_get_ms_per_16th(preset, slot);
            uint32_t note_duration_ms = ms_per_16th;
            uint32_t gate_duration_ms = (note_duration_ms * gate_percent) / 100;

            for (uint8_t i = 0; i < note_count_to_play; i++) {
                uint8_t preset_note_idx = notes_to_play[i];
                unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                // Calculate absolute MIDI note: (octave × 12) + note_index
                int16_t midi_note = (note->octave_offset * 12) + note->note_index;

                // Clamp to MIDI range (0-127)
                if (midi_note < 0) midi_note = 0;
                if (midi_note > 127) midi_note = 127;

                // Send note-on using sequencer's locked-in values
                midi_send_noteon_seq(slot, (uint8_t)midi_note, note->velocity);

                // Add to arp_notes for gate tracking (use locked channel)
                uint32_t note_off_time = current_time + gate_duration_ms;
                add_arp_note(seq_state[slot].locked_channel, (uint8_t)midi_note, note->velocity, note_off_time);
            }
        }

        // Advance position
        seq_state[slot].current_position_16ths++;

        // Check for loop
        if (seq_state[slot].current_position_16ths >= preset->pattern_length_16ths) {
            seq_state[slot].current_position_16ths = 0;
            seq_state[slot].pattern_start_time = current_time;
        }

        // Calculate next note time
        uint32_t ms_per_16th = seq_get_ms_per_16th(preset, slot);
        seq_state[slot].next_note_time = current_time + ms_per_16th;
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

    // Scale velocity using locked-in min/max range
    uint8_t min_vel = seq_state[slot].locked_velocity_min;
    uint8_t max_vel = seq_state[slot].locked_velocity_max;

    // Scale from 0-127 to min_vel-max_vel
    uint8_t scaled_velocity = min_vel + ((velocity_0_127 * (max_vel - min_vel)) / 127);

    uint8_t raw_travel = scaled_velocity;

    // Send the note
    midi_send_noteon_arp(channel, (uint8_t)transposed_note, raw_travel, raw_travel);
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

    // Initialize BPM if not set
    if (current_bpm == 0) {
        current_bpm = 12000000;  // 120.00000 BPM
        dprintf("arp: initialized BPM to 120\n");
    }

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
        if (current_bpm == 0) {
            current_bpm = 12000000;
            dprintf("arp: initialized BPM to 120\n");
        }
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

    // Validate individual notes
    bool is_arpeggiator = (preset->preset_type == PRESET_TYPE_ARPEGGIATOR);
    for (uint8_t i = 0; i < preset->note_count; i++) {
        const arp_preset_note_t *packed_note = &preset->notes[i];
        unpacked_note_t note;
        unpack_note(packed_note, &note, is_arpeggiator);

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

        // Velocity is 0-127, always valid for unpacked value
        // Note index for arp is -11 to +11, for seq is 0-11, both within int8_t range
    }

    dprintf("arp: preset validation passed\n");
    return true;
}

// Validate step sequencer preset structure
bool seq_validate_preset(const seq_preset_t *preset) {
    if (preset == NULL) {
        dprintf("seq: validate failed - NULL pointer\n");
        return false;
    }

    // Check magic number
    if (preset->magic != ARP_PRESET_MAGIC) {
        dprintf("seq: validate failed - bad magic: 0x%04X (expected 0x%04X)\n",
                preset->magic, ARP_PRESET_MAGIC);
        return false;
    }

    // Check note count bounds for step sequencer (max 128 notes)
    if (preset->note_count > MAX_SEQ_PRESET_NOTES) {
        dprintf("seq: validate failed - note_count %d exceeds max %d\n",
                preset->note_count, MAX_SEQ_PRESET_NOTES);
        return false;
    }

    // Check gate length bounds
    if (preset->gate_length_percent > 100) {
        dprintf("seq: validate failed - gate_length_percent %d > 100\n",
                preset->gate_length_percent);
        return false;
    }

    // Check pattern length bounds (at least 1 16th, max 127 = ~8 bars)
    if (preset->pattern_length_16ths < 1 || preset->pattern_length_16ths > 127) {
        dprintf("seq: validate failed - pattern_length %d not in [1,127]\n",
                preset->pattern_length_16ths);
        return false;
    }

    // Validate individual notes
    bool is_arpeggiator = (preset->preset_type == PRESET_TYPE_ARPEGGIATOR);
    for (uint8_t i = 0; i < preset->note_count; i++) {
        const arp_preset_note_t *packed_note = &preset->notes[i];
        unpacked_note_t note;
        unpack_note(packed_note, &note, is_arpeggiator);

        // Check timing is within pattern length
        if (note.timing >= preset->pattern_length_16ths) {
            dprintf("seq: validate failed - note[%d] timing %d >= pattern_length %d\n",
                    i, note.timing, preset->pattern_length_16ths);
            return false;
        }

        // Check octave offset is within new packed range (-8 to +7)
        if (note.octave_offset < -8 || note.octave_offset > 7) {
            dprintf("seq: validate failed - note[%d] octave_offset %d not in [-8,7]\n",
                    i, note.octave_offset);
            return false;
        }

        // Velocity is 0-127, always valid for unpacked value
        // Note index for seq is 0-11, within int8_t range
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

// Get current step number (1-indexed for display)
uint8_t quick_build_get_current_step(void) {
    return quick_build_state.current_step + 1;  // Return 1-indexed
}

// Start quick build for arpeggiator
void quick_build_start_arp(void) {
    dprintf("quick_build: starting arp builder\n");

    // Stop any playing arp
    if (arp_state.active) {
        arp_stop();
    }

    // Cancel seq quick build if active
    if (quick_build_state.mode == QUICK_BUILD_SEQ) {
        quick_build_cancel();
    }

    // Initialize state
    quick_build_state.mode = QUICK_BUILD_ARP;
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    quick_build_state.has_root = false;
    quick_build_state.has_saved_build = false;
    quick_build_state.sustain_held_last_check = false;

    // Clear and initialize arp_active_preset
    memset(&arp_active_preset, 0, sizeof(arp_preset_t));
    arp_active_preset.preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_active_preset.note_count = 0;
    arp_active_preset.pattern_length_16ths = 1;  // Start with 1 step
    arp_active_preset.gate_length_percent = 80;
    arp_active_preset.timing_mode = TIMING_MODE_STRAIGHT;
    arp_active_preset.note_value = NOTE_VALUE_SIXTEENTH;
    arp_active_preset.magic = ARP_PRESET_MAGIC;

    // Mark as custom preset (not from EEPROM)
    arp_state.loaded_preset_id = 255;

    dprintf("quick_build: arp builder ready, waiting for first note\n");
}

// Start quick build for step sequencer (specific slot)
void quick_build_start_seq(uint8_t slot) {
    if (slot >= MAX_SEQ_SLOTS) {
        dprintf("quick_build: invalid slot %d\n", slot);
        return;
    }

    dprintf("quick_build: starting seq builder for slot %d\n", slot);

    // Stop all playing sequencers
    seq_stop_all();

    // Cancel arp quick build if active
    if (quick_build_state.mode == QUICK_BUILD_ARP) {
        quick_build_cancel();
    }

    // Initialize state
    quick_build_state.mode = QUICK_BUILD_SEQ;
    quick_build_state.seq_slot = slot;
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    quick_build_state.has_saved_build = false;
    quick_build_state.sustain_held_last_check = false;

    // Clear and initialize seq preset for this slot
    memset(&seq_active_presets[slot], 0, sizeof(seq_preset_t));
    seq_active_presets[slot].preset_type = PRESET_TYPE_STEP_SEQUENCER;
    seq_active_presets[slot].note_count = 0;
    seq_active_presets[slot].pattern_length_16ths = 1;  // Start with 1 step
    seq_active_presets[slot].gate_length_percent = 80;
    seq_active_presets[slot].timing_mode = TIMING_MODE_STRAIGHT;
    seq_active_presets[slot].note_value = NOTE_VALUE_SIXTEENTH;
    seq_active_presets[slot].magic = ARP_PRESET_MAGIC;

    // Mark as custom preset (not from EEPROM)
    seq_state[slot].loaded_preset_id = 255;

    dprintf("quick_build: seq builder ready for slot %d, waiting for first note\n", slot);
}

// Cancel quick build and return to normal mode
void quick_build_cancel(void) {
    if (!quick_build_is_active()) return;

    dprintf("quick_build: canceling build mode %d\n", quick_build_state.mode);

    quick_build_state.mode = QUICK_BUILD_NONE;
    quick_build_state.has_saved_build = false;
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    quick_build_state.has_root = false;

    dprintf("quick_build: canceled\n");
}

// Finish and save the quick build
void quick_build_finish(void) {
    if (!quick_build_is_active()) return;

    if (quick_build_state.mode == QUICK_BUILD_ARP) {
        // Validate arpeggiator preset
        if (!arp_validate_preset(&arp_active_preset)) {
            dprintf("quick_build: arp validation failed, canceling\n");
            quick_build_cancel();
            return;
        }

        dprintf("quick_build: arp finished with %d notes, %d steps\n",
                quick_build_state.note_count, quick_build_state.current_step + 1);
        quick_build_state.has_saved_build = true;

    } else if (quick_build_state.mode == QUICK_BUILD_SEQ) {
        uint8_t slot = quick_build_state.seq_slot;

        // Validate sequencer preset
        if (!seq_validate_preset(&seq_active_presets[slot])) {
            dprintf("quick_build: seq validation failed, canceling\n");
            quick_build_cancel();
            return;
        }

        dprintf("quick_build: seq slot %d finished with %d notes, %d steps\n",
                slot, quick_build_state.note_count, quick_build_state.current_step + 1);
        quick_build_state.has_saved_build = true;
    }

    // Exit build mode but keep the build in RAM
    quick_build_state.mode = QUICK_BUILD_NONE;

    dprintf("quick_build: saved to RAM, ready to play\n");
}

// Erase the saved quick build
void quick_build_erase(void) {
    dprintf("quick_build: erasing saved build\n");

    quick_build_state.has_saved_build = false;
    quick_build_state.mode = QUICK_BUILD_NONE;
    quick_build_state.current_step = 0;
    quick_build_state.note_count = 0;
    quick_build_state.has_root = false;

    dprintf("quick_build: erased\n");
}

// Advance to next step
static void quick_build_advance_step(void) {
    quick_build_state.current_step++;

    // Update pattern length in active preset
    if (quick_build_state.mode == QUICK_BUILD_ARP) {
        arp_active_preset.pattern_length_16ths = quick_build_state.current_step + 1;
        dprintf("quick_build: arp advanced to step %d\n", quick_build_state.current_step + 1);
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ) {
        uint8_t slot = quick_build_state.seq_slot;
        seq_active_presets[slot].pattern_length_16ths = quick_build_state.current_step + 1;
        dprintf("quick_build: seq slot %d advanced to step %d\n", slot, quick_build_state.current_step + 1);
    }
}

// Handle incoming MIDI note during quick build
void quick_build_handle_note(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel) {
    if (!quick_build_is_active()) return;

    // Use raw_travel for velocity if available (0-255), otherwise use velocity (0-127)
    uint8_t record_velocity = (raw_travel > 0) ? (raw_travel >> 1) : velocity;  // Scale to 0-127

    // Track if we need to advance step (only if sustain is NOT held)
    extern bool get_live_sustain_state(void);
    bool sustain_held = get_live_sustain_state();
    bool should_advance = false;

    if (quick_build_state.mode == QUICK_BUILD_ARP) {
        // Check if we've hit max notes
        if (quick_build_state.note_count >= MAX_ARP_PRESET_NOTES) {
            dprintf("quick_build: arp max notes reached, finishing\n");
            quick_build_finish();
            return;
        }

        // First note = root
        if (!quick_build_state.has_root) {
            quick_build_state.root_note = note;
            quick_build_state.has_root = true;
            dprintf("quick_build: arp root note set to %d\n", note);
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

        // Advance step if sustain not held
        if (!sustain_held) {
            should_advance = true;
        }

    } else if (quick_build_state.mode == QUICK_BUILD_SEQ) {
        uint8_t slot = quick_build_state.seq_slot;

        // Check max notes
        if (quick_build_state.note_count >= MAX_SEQ_PRESET_NOTES) {
            dprintf("quick_build: seq max notes reached, finishing\n");
            quick_build_finish();
            return;
        }

        // For sequencer: store absolute MIDI note
        uint8_t note_index = note % 12;  // 0-11 (C-B)
        int8_t octave_offset = (note / 12) - 5;  // Relative to middle C octave

        // Pack note data
        seq_active_presets[slot].notes[quick_build_state.note_count].packed_timing_vel =
            NOTE_PACK_TIMING_VEL(quick_build_state.current_step, record_velocity, 0);
        seq_active_presets[slot].notes[quick_build_state.note_count].note_octave =
            NOTE_PACK_NOTE_OCTAVE(note_index, octave_offset);

        quick_build_state.note_count++;
        seq_active_presets[slot].note_count = quick_build_state.note_count;

        dprintf("quick_build: seq slot %d recorded note %d at step %d\n",
                slot, note, quick_build_state.current_step + 1);

        // Advance step if sustain not held
        if (!sustain_held) {
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
    if (!quick_build_is_active()) return;

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
