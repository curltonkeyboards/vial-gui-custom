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
    .mode = ARP_MODE_SINGLE_NOTE,
    .current_preset_id = 0,
    .next_note_time = 0,
    .current_position_16ths = 0,
    .current_note_in_chord = 0,
    .subdivision_override = 0,
    .master_gate_override = 0,
    .pattern_start_time = 0,
    .last_tap_time = 0,
    .key_held = false
};

// Preset storage
arp_preset_t arp_presets[MAX_ARP_PRESETS];
uint8_t arp_preset_count = 0;

// External references
extern uint8_t live_notes[MAX_LIVE_NOTES][3];  // [channel, note, velocity]
extern uint8_t live_note_count;
extern uint32_t current_bpm;  // BPM in format: actual_bpm * 100000
extern uint8_t channel_number;  // Current MIDI channel

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

void arp_init_presets(void) {
    // Clear all presets
    memset(arp_presets, 0, sizeof(arp_presets));
    arp_preset_count = 0;

    // =========================================================================
    // ARPEGGIATOR FACTORY PRESETS (0-7)
    // =========================================================================

    // =========================================================================
    // PRESET 0: Up 16ths - Classic ascending 16th notes
    // =========================================================================
    arp_presets[0].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[0].note_count = 4;
    arp_presets[0].pattern_length_16ths = 16;  // 1 bar
    arp_presets[0].gate_length_percent = 80;   // 80% gate
    arp_presets[0].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[0].note_value = NOTE_VALUE_QUARTER;
    arp_presets[0].magic = ARP_PRESET_MAGIC;

    // Step 1: Note 0 at beat 0 (velocity 200/2 = 100)
    arp_presets[0].notes[0].packed_timing_vel = NOTE_PACK_TIMING_VEL(0, 100, 0);
    arp_presets[0].notes[0].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 0);

    // Step 2: Note 1 at beat 1 (4 16ths per beat)
    arp_presets[0].notes[1].packed_timing_vel = NOTE_PACK_TIMING_VEL(4, 100, 0);
    arp_presets[0].notes[1].note_octave = NOTE_PACK_NOTE_OCTAVE(1, 0);

    // Step 3: Note 2 at beat 2
    arp_presets[0].notes[2].packed_timing_vel = NOTE_PACK_TIMING_VEL(8, 100, 0);
    arp_presets[0].notes[2].note_octave = NOTE_PACK_NOTE_OCTAVE(2, 0);

    // Step 4: Note 3 at beat 3
    arp_presets[0].notes[3].packed_timing_vel = NOTE_PACK_TIMING_VEL(12, 100, 0);
    arp_presets[0].notes[3].note_octave = NOTE_PACK_NOTE_OCTAVE(3, 0);

    // =========================================================================
    // PRESET 1: Down 16ths - Classic descending 16th notes
    // =========================================================================
    arp_presets[1].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[1].note_count = 4;
    arp_presets[1].pattern_length_16ths = 16;
    arp_presets[1].gate_length_percent = 80;
    arp_presets[1].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[1].note_value = NOTE_VALUE_QUARTER;
    arp_presets[1].magic = ARP_PRESET_MAGIC;

    // Descending: 3, 2, 1, 0 (velocity 200/2 = 100)
    arp_presets[1].notes[0].packed_timing_vel = NOTE_PACK_TIMING_VEL(0, 100, 0);
    arp_presets[1].notes[0].note_octave = NOTE_PACK_NOTE_OCTAVE(3, 0);

    arp_presets[1].notes[1].packed_timing_vel = NOTE_PACK_TIMING_VEL(4, 100, 0);
    arp_presets[1].notes[1].note_octave = NOTE_PACK_NOTE_OCTAVE(2, 0);

    arp_presets[1].notes[2].packed_timing_vel = NOTE_PACK_TIMING_VEL(8, 100, 0);
    arp_presets[1].notes[2].note_octave = NOTE_PACK_NOTE_OCTAVE(1, 0);

    arp_presets[1].notes[3].packed_timing_vel = NOTE_PACK_TIMING_VEL(12, 100, 0);
    arp_presets[1].notes[3].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 0);

    // =========================================================================
    // PRESET 2: Up-Down 16ths (Exclusive) - Up then down, no repeat
    // =========================================================================
    arp_presets[2].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[2].note_count = 6;
    arp_presets[2].pattern_length_16ths = 24;  // 1.5 bars for up-down pattern
    arp_presets[2].gate_length_percent = 80;
    arp_presets[2].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[2].note_value = NOTE_VALUE_QUARTER;
    arp_presets[2].magic = ARP_PRESET_MAGIC;

    // Up: 0, 1, 2, 3 (velocity 100)
    arp_presets[2].notes[0].packed_timing_vel = NOTE_PACK_TIMING_VEL(0, 100, 0);
    arp_presets[2].notes[0].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 0);

    arp_presets[2].notes[1].packed_timing_vel = NOTE_PACK_TIMING_VEL(4, 100, 0);
    arp_presets[2].notes[1].note_octave = NOTE_PACK_NOTE_OCTAVE(1, 0);

    arp_presets[2].notes[2].packed_timing_vel = NOTE_PACK_TIMING_VEL(8, 100, 0);
    arp_presets[2].notes[2].note_octave = NOTE_PACK_NOTE_OCTAVE(2, 0);

    arp_presets[2].notes[3].packed_timing_vel = NOTE_PACK_TIMING_VEL(12, 100, 0);
    arp_presets[2].notes[3].note_octave = NOTE_PACK_NOTE_OCTAVE(3, 0);

    // Down: 2, 1 (exclusive - don't repeat 3 and 0)
    arp_presets[2].notes[4].packed_timing_vel = NOTE_PACK_TIMING_VEL(16, 100, 0);
    arp_presets[2].notes[4].note_octave = NOTE_PACK_NOTE_OCTAVE(2, 0);

    arp_presets[2].notes[5].packed_timing_vel = NOTE_PACK_TIMING_VEL(20, 100, 0);
    arp_presets[2].notes[5].note_octave = NOTE_PACK_NOTE_OCTAVE(1, 0);

    // =========================================================================
    // PRESET 3: Random 8ths - Random note selection with 8th note timing
    // =========================================================================
    arp_presets[3].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[3].note_count = 4;
    arp_presets[3].pattern_length_16ths = 32;  // 2 bars
    arp_presets[3].gate_length_percent = 75;
    arp_presets[3].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[3].note_value = NOTE_VALUE_EIGHTH;
    arp_presets[3].magic = ARP_PRESET_MAGIC;

    // Random pattern (will be randomized at runtime, but set defaults)
    // 8th notes = 2 16ths apart (velocity 90)
    for (uint8_t i = 0; i < 4; i++) {
        arp_presets[3].notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 8, 90, 0);
        arp_presets[3].notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 0);  // Will be randomized
    }

    // =========================================================================
    // PRESET 4: Up 2 Octaves - Ascending with 2 octave range
    // =========================================================================
    arp_presets[4].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[4].note_count = 8;
    arp_presets[4].pattern_length_16ths = 32;  // 2 bars
    arp_presets[4].gate_length_percent = 80;
    arp_presets[4].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[4].note_value = NOTE_VALUE_SIXTEENTH;
    arp_presets[4].magic = ARP_PRESET_MAGIC;

    // First octave (velocity 100)
    for (uint8_t i = 0; i < 4; i++) {
        arp_presets[4].notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 100, 0);
        arp_presets[4].notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(i, 0);
    }
    // Second octave (+1 octave = +12 semitones, but octave field is in octaves not semitones so +1)
    for (uint8_t i = 0; i < 4; i++) {
        arp_presets[4].notes[i + 4].packed_timing_vel = NOTE_PACK_TIMING_VEL((i + 4) * 4, 100, 0);
        arp_presets[4].notes[i + 4].note_octave = NOTE_PACK_NOTE_OCTAVE(i, 1);
    }

    // =========================================================================
    // PRESET 5: Down 2 Octaves - Descending with 2 octave range
    // =========================================================================
    arp_presets[5].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[5].note_count = 8;
    arp_presets[5].pattern_length_16ths = 32;  // 2 bars
    arp_presets[5].gate_length_percent = 80;
    arp_presets[5].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[5].note_value = NOTE_VALUE_SIXTEENTH;
    arp_presets[5].magic = ARP_PRESET_MAGIC;

    // Start from high octave (velocity 100)
    for (uint8_t i = 0; i < 4; i++) {
        arp_presets[5].notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 100, 0);
        arp_presets[5].notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(3 - i, 1);
    }
    // Then base octave
    for (uint8_t i = 0; i < 4; i++) {
        arp_presets[5].notes[i + 4].packed_timing_vel = NOTE_PACK_TIMING_VEL((i + 4) * 4, 100, 0);
        arp_presets[5].notes[i + 4].note_octave = NOTE_PACK_NOTE_OCTAVE(3 - i, 0);
    }

    // =========================================================================
    // PRESET 6: Octave Jump - Alternates between base and +1 octave
    // =========================================================================
    arp_presets[6].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[6].note_count = 8;
    arp_presets[6].pattern_length_16ths = 32;  // 2 bars
    arp_presets[6].gate_length_percent = 75;
    arp_presets[6].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[6].note_value = NOTE_VALUE_EIGHTH;
    arp_presets[6].magic = ARP_PRESET_MAGIC;

    // Alternate between octaves: 0, 0+1oct, 1, 1+1oct, 2, 2+1oct, 3, 3+1oct (velocity 100)
    for (uint8_t i = 0; i < 4; i++) {
        // Base note
        arp_presets[6].notes[i * 2].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 8, 100, 0);
        arp_presets[6].notes[i * 2].note_octave = NOTE_PACK_NOTE_OCTAVE(i, 0);

        // Same note +1 octave
        arp_presets[6].notes[i * 2 + 1].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 8 + 4, 100, 0);
        arp_presets[6].notes[i * 2 + 1].note_octave = NOTE_PACK_NOTE_OCTAVE(i, 1);
    }

    // =========================================================================
    // PRESET 7: Rapid 16ths - Fast 16th note ascending
    // =========================================================================
    arp_presets[7].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[7].note_count = 8;
    arp_presets[7].pattern_length_16ths = 16;   // 1 bar
    arp_presets[7].gate_length_percent = 60;    // Shorter gate for clarity
    arp_presets[7].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[7].note_value = NOTE_VALUE_SIXTEENTH;
    arp_presets[7].magic = ARP_PRESET_MAGIC;

    // 16th notes = 1 16th apart (velocity 90)
    for (uint8_t i = 0; i < 8; i++) {
        arp_presets[7].notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 2, 90, 0);
        arp_presets[7].notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(i % 4, 0);  // Cycle through 4 notes
    }

    // =========================================================================
    // STEP SEQUENCER FACTORY PRESETS (32-39)
    // =========================================================================

    // =========================================================================
    // PRESET 32: C Major Scale - Simple ascending scale
    // =========================================================================
    arp_presets[32].preset_type = PRESET_TYPE_STEP_SEQUENCER;
    arp_presets[32].note_count = 8;
    arp_presets[32].pattern_length_16ths = 32;  // 2 bars
    arp_presets[32].gate_length_percent = 80;
    arp_presets[32].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[32].note_value = NOTE_VALUE_QUARTER;
    arp_presets[32].magic = ARP_PRESET_MAGIC;

    // C Major: C, D, E, F, G, A, B, C (octave 4) (velocity 100)
    const uint8_t c_major_notes[] = {0, 2, 4, 5, 7, 9, 11, 0};  // C, D, E, F, G, A, B, C
    const uint8_t c_major_octaves[] = {4, 4, 4, 4, 4, 4, 4, 5};  // Last C is in octave 5
    for (uint8_t i = 0; i < 8; i++) {
        arp_presets[32].notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 100, 0);  // Every beat (4 16ths per beat)
        arp_presets[32].notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(c_major_notes[i], c_major_octaves[i]);
    }

    // =========================================================================
    // PRESET 33: Bass Line - Simple four-note bass pattern
    // =========================================================================
    arp_presets[33].preset_type = PRESET_TYPE_STEP_SEQUENCER;
    arp_presets[33].note_count = 4;
    arp_presets[33].pattern_length_16ths = 16;  // 1 bar
    arp_presets[33].gate_length_percent = 70;
    arp_presets[33].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[33].note_value = NOTE_VALUE_QUARTER;
    arp_presets[33].magic = ARP_PRESET_MAGIC;

    // Bass pattern: C, C, G, C (octave 2-3) (velocity 110)
    const uint8_t bass_notes[] = {0, 0, 7, 0};  // C, C, G, C
    const uint8_t bass_octaves[] = {2, 2, 2, 3};  // Low octaves
    for (uint8_t i = 0; i < 4; i++) {
        arp_presets[33].notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 110, 0);
        arp_presets[33].notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(bass_notes[i], bass_octaves[i]);
    }

    // =========================================================================
    // PRESET 34: Techno Kick - Repeating low note pattern
    // =========================================================================
    arp_presets[34].preset_type = PRESET_TYPE_STEP_SEQUENCER;
    arp_presets[34].note_count = 4;
    arp_presets[34].pattern_length_16ths = 16;  // 1 bar
    arp_presets[34].gate_length_percent = 50;
    arp_presets[34].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[34].note_value = NOTE_VALUE_QUARTER;
    arp_presets[34].magic = ARP_PRESET_MAGIC;

    // Four-on-the-floor: C1 on each beat (velocity 127 = max)
    for (uint8_t i = 0; i < 4; i++) {
        arp_presets[34].notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 127, 0);
        arp_presets[34].notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 1);  // C, Octave 1
    }

    // =========================================================================
    // PRESET 35: Melody 1 - Simple melodic pattern
    // =========================================================================
    arp_presets[35].preset_type = PRESET_TYPE_STEP_SEQUENCER;
    arp_presets[35].note_count = 8;
    arp_presets[35].pattern_length_16ths = 32;  // 2 bars
    arp_presets[35].gate_length_percent = 75;
    arp_presets[35].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[35].note_value = NOTE_VALUE_QUARTER;
    arp_presets[35].magic = ARP_PRESET_MAGIC;

    // Melodic pattern: E, G, A, G, E, D, C, D (velocity 90)
    const uint8_t melody_notes[] = {4, 7, 9, 7, 4, 2, 0, 2};  // E, G, A, G, E, D, C, D
    for (uint8_t i = 0; i < 8; i++) {
        arp_presets[35].notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 90, 0);
        arp_presets[35].notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(melody_notes[i], 4);  // Octave 4
    }

    // =========================================================================
    // PRESET 36-39: Reserved for future factory presets
    // =========================================================================
    for (uint8_t p = 36; p <= 39; p++) {
        arp_presets[p].preset_type = PRESET_TYPE_STEP_SEQUENCER;
        arp_presets[p].note_count = 0;
        arp_presets[p].pattern_length_16ths = 16;
        arp_presets[p].gate_length_percent = 80;
        arp_presets[p].timing_mode = TIMING_MODE_STRAIGHT;
        arp_presets[p].note_value = NOTE_VALUE_QUARTER;
        arp_presets[p].magic = ARP_PRESET_MAGIC;
    }

    arp_preset_count = 64;

    dprintf("arp: initialized %d presets (8 arp + 4 seq factory)\n", arp_preset_count);
}

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
static uint32_t get_ms_per_16th(const arp_preset_t *preset) {
    uint32_t actual_bpm = get_effective_bpm() / 100000;
    if (actual_bpm == 0) actual_bpm = 120;

    // Base calculation: quarter note duration / 4 = 16th note duration
    uint32_t base_ms = (60000 / actual_bpm) / 4;

    // Apply note value multiplier (quarter=4x, eighth=2x, sixteenth=1x)
    uint8_t multiplier = 1;
    switch (preset->note_value) {
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
    if (preset->timing_mode & TIMING_MODE_TRIPLET) {
        // Triplet timing: compress to 2/3 of normal duration
        base_ms = (base_ms * 2) / 3;
    } else if (preset->timing_mode & TIMING_MODE_DOTTED) {
        // Dotted timing: extend to 3/2 of normal duration
        base_ms = (base_ms * 3) / 2;
    }

    return base_ms;
}

// Sort live notes by pitch (for consistent ordering)
static void sort_live_notes_by_pitch(uint8_t sorted_indices[], uint8_t count) {
    // Create array of indices
    for (uint8_t i = 0; i < count; i++) {
        sorted_indices[i] = i;
    }

    // Simple bubble sort by note pitch
    for (uint8_t i = 0; i < count - 1; i++) {
        for (uint8_t j = 0; j < count - i - 1; j++) {
            if (live_notes[sorted_indices[j]][1] > live_notes[sorted_indices[j+1]][1]) {
                uint8_t temp = sorted_indices[j];
                sorted_indices[j] = sorted_indices[j+1];
                sorted_indices[j+1] = temp;
            }
        }
    }
}

void arp_init(void) {
    // Initialize factory presets (0-7)
    arp_init_presets();

    // Load user presets from EEPROM (8-31)
    arp_load_all_user_presets();

    // Clear arp notes
    memset(arp_notes, 0, sizeof(arp_notes));
    arp_note_count = 0;

    // Reset state
    arp_state.active = false;
    arp_state.latch_mode = false;
    arp_state.current_preset_id = 0;
    arp_state.sync_mode = true;
    arp_state.mode = ARP_MODE_SINGLE_NOTE;

    dprintf("arp: initialized with %d total presets\n", MAX_ARP_PRESETS);
}

void arp_start(uint8_t preset_id) {
    if (preset_id >= arp_preset_count) {
        dprintf("arp: invalid preset id %d\n", preset_id);
        return;
    }

    // If already active and switching presets
    if (arp_state.active && preset_id != arp_state.current_preset_id) {
        // Handle preset switching based on sync mode
        if (arp_state.sync_mode) {
            // Calculate relative position in old pattern
            arp_preset_t *old_preset = &arp_presets[arp_state.current_preset_id];
            uint16_t old_length = old_preset->pattern_length_16ths;
            float progress = (float)arp_state.current_position_16ths / old_length;

            // Apply to new pattern
            arp_preset_t *new_preset = &arp_presets[preset_id];
            arp_state.current_position_16ths = (uint16_t)(progress * new_preset->pattern_length_16ths);

            dprintf("arp: switching preset with sync, progress: %d%%\n", (int)(progress * 100));
        } else {
            // Unsynced: restart from beginning
            arp_state.current_position_16ths = 0;
            arp_state.pattern_start_time = timer_read32();
        }
    } else {
        // Starting fresh
        arp_state.current_position_16ths = 0;
        arp_state.pattern_start_time = timer_read32();

        // If sync mode, wait for next beat to start
        if (arp_state.sync_mode) {
            // TODO: Sync to BPM beat boundary
            // For now, start immediately
        }
    }

    arp_state.current_preset_id = preset_id;
    arp_state.active = true;
    arp_state.current_note_in_chord = 0;
    arp_state.next_note_time = timer_read32();  // Start immediately

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

    // Note: We don't immediately send note-offs here
    // Let the gate timing system handle it naturally
}

void arp_update(void) {
    // Process any notes that need to be gated off
    process_arp_note_offs();

    // If not active, nothing to do
    if (!arp_state.active) return;

    // Get current preset
    arp_preset_t *preset = &arp_presets[arp_state.current_preset_id];

    // Check requirements based on preset type
    if (preset->preset_type == PRESET_TYPE_ARPEGGIATOR) {
        // Arpeggiator requires live notes (master note)
        if (live_note_count == 0) {
            // No notes held - stop if not in latch mode
            if (!arp_state.latch_mode) {
                arp_stop();
            }
            return;
        }
    }
    // Step sequencer plays independently, no live notes required

    // Check if it's time to play next note
    uint32_t current_time = timer_read32();
    if (current_time < arp_state.next_note_time) {
        return;  // Not yet time
    }

    // Special case: Random preset - randomize note indices
    if (arp_state.current_preset_id == 3) {  // Random 8ths preset
        for (uint8_t i = 0; i < preset->note_count; i++) {
            preset->notes[i].note_index = rand() % live_note_count;
        }
    }

    // Find notes to play at current position
    uint8_t notes_to_play[MAX_PRESET_NOTES];
    uint8_t note_count_to_play = 0;
    unpacked_note_t unpacked_notes[MAX_PRESET_NOTES];

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

                // Scale velocity from 0-127 to raw_travel (0-255)
                uint8_t raw_travel = (note->velocity * 2);  // Simple 2x scaling
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
            // Sort live notes for consistent ordering
            uint8_t sorted_indices[MAX_LIVE_NOTES];
            sort_live_notes_by_pitch(sorted_indices, live_note_count);

            // Handle different playback modes
            switch (arp_state.mode) {
                case ARP_MODE_SINGLE_NOTE: {
                // Single Note Mode: Play master note + semitone offset
                // Master note = lowest/first held note
                if (live_note_count == 0) break;

                uint8_t master_idx = sorted_indices[0];  // Lowest held note
                uint8_t master_note = live_notes[master_idx][1];
                uint8_t channel = live_notes[master_idx][0];

                for (uint8_t i = 0; i < note_count_to_play; i++) {
                    uint8_t preset_note_idx = notes_to_play[i];
                    unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                    // Calculate note: master + semitone_offset + octave_offset
                    // note_index field contains semitone offset (-11 to +11 with sign)
                    int16_t semitone_offset = note->note_index;
                    int16_t octave_semitones = note->octave_offset * 12;
                    int16_t final_note = master_note + semitone_offset + octave_semitones;

                    // Clamp to MIDI range
                    if (final_note < 0) final_note = 0;
                    if (final_note > 127) final_note = 127;

                    // Scale velocity from 0-127 to raw_travel (0-255)
                    uint8_t raw_travel = (note->velocity * 2);

                    // Send note-on
                    midi_send_noteon_arp(channel, (uint8_t)final_note, raw_travel, raw_travel);

                    // Add to arp_notes for gate tracking
                    uint32_t note_off_time = current_time + gate_duration_ms;
                    add_arp_note(channel, (uint8_t)final_note, raw_travel, note_off_time);
                }
                break;
            }

            case ARP_MODE_CHORD_BASIC: {
                // Chord Basic Mode: Apply semitone offset to ALL held notes
                // Each step plays all held notes + the semitone offset
                for (uint8_t i = 0; i < note_count_to_play; i++) {
                    uint8_t preset_note_idx = notes_to_play[i];
                    unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                    int16_t semitone_offset = note->note_index;
                    int16_t octave_semitones = note->octave_offset * 12;

                    // Apply offset to ALL held notes
                    for (uint8_t n = 0; n < live_note_count; n++) {
                        uint8_t live_idx = sorted_indices[n];
                        uint8_t channel = live_notes[live_idx][0];
                        uint8_t master_note = live_notes[live_idx][1];

                        int16_t final_note = master_note + semitone_offset + octave_semitones;

                        // Clamp to MIDI range
                        if (final_note < 0) final_note = 0;
                        if (final_note > 127) final_note = 127;

                        uint8_t raw_travel = (note->velocity * 2);

                        // Send note-on
                        midi_send_noteon_arp(channel, (uint8_t)final_note, raw_travel, raw_travel);

                        // Add to arp_notes for gate tracking
                        uint32_t note_off_time = current_time + gate_duration_ms;
                        add_arp_note(channel, (uint8_t)final_note, raw_travel, note_off_time);
                    }
                }
                break;
            }

            case ARP_MODE_CHORD_ADVANCED: {
                // Chord Advanced Mode: Rotate through held notes, applying semitone offset to each
                // Each step plays one held note + offset, rotating through all held notes

                for (uint8_t i = 0; i < note_count_to_play; i++) {
                    uint8_t preset_note_idx = notes_to_play[i];
                    unpacked_note_t *note = &unpacked_notes[preset_note_idx];

                    // Play the next note in rotation
                    uint8_t note_to_play = arp_state.current_note_in_chord % live_note_count;
                    uint8_t live_idx = sorted_indices[note_to_play];
                    uint8_t channel = live_notes[live_idx][0];
                    uint8_t master_note = live_notes[live_idx][1];

                    int16_t semitone_offset = note->note_index;
                    int16_t octave_semitones = note->octave_offset * 12;
                    int16_t final_note = master_note + semitone_offset + octave_semitones;

                    // Clamp to MIDI range
                    if (final_note < 0) final_note = 0;
                    if (final_note > 127) final_note = 127;

                    uint8_t raw_travel = (note->velocity * 2);

                    // Send note-on
                    midi_send_noteon_arp(channel, (uint8_t)final_note, raw_travel, raw_travel);

                    // Add to arp_notes for gate tracking
                    uint32_t note_off_time = current_time + gate_duration_ms;
                    add_arp_note(channel, (uint8_t)final_note, raw_travel, note_off_time);

                    // Advance to next note in chord for next trigger
                    arp_state.current_note_in_chord = (arp_state.current_note_in_chord + 1) % live_note_count;
                }
                break;
            }

                default:
                    break;
            }
        }
    }

    // Advance position
    arp_state.current_position_16ths++;

    // Check for loop
    if (arp_state.current_position_16ths >= preset->pattern_length_16ths) {
        arp_state.current_position_16ths = 0;
        arp_state.pattern_start_time = current_time;
        dprintf("arp: pattern loop\n");
    }

    // Calculate next note time
    uint32_t ms_per_16th = get_ms_per_16th(preset);
    arp_state.next_note_time = current_time + ms_per_16th;
}

// =============================================================================
// USER INTERFACE FUNCTIONS
// =============================================================================

void arp_next_preset(void) {
    if (arp_preset_count == 0) return;

    arp_state.current_preset_id = (arp_state.current_preset_id + 1) % arp_preset_count;
    dprintf("arp: next preset -> %d\n", arp_state.current_preset_id);

    // TODO: Update OLED display
}

void arp_prev_preset(void) {
    if (arp_preset_count == 0) return;

    if (arp_state.current_preset_id == 0) {
        arp_state.current_preset_id = arp_preset_count - 1;
    } else {
        arp_state.current_preset_id--;
    }

    dprintf("arp: prev preset -> %d\n", arp_state.current_preset_id);

    // TODO: Update OLED display
}

#define ARP_DOUBLE_TAP_WINDOW 300  // ms for double-tap detection

void arp_handle_button_press(void) {
    uint32_t current_time = timer_read32();
    uint32_t time_since_last = current_time - arp_state.last_tap_time;

    // Check for double-tap (latch mode)
    if (time_since_last < ARP_DOUBLE_TAP_WINDOW) {
        // Double-tap detected - toggle latch mode
        arp_state.latch_mode = !arp_state.latch_mode;
        dprintf("arp: double-tap detected, latch mode: %d\n", arp_state.latch_mode);

        if (arp_state.latch_mode) {
            // Start arp in latch mode (acts as if button is held)
            arp_start(arp_state.current_preset_id);
        }
    } else {
        // Single press - start arp normally
        arp_state.key_held = true;
        arp_start(arp_state.current_preset_id);
    }

    arp_state.last_tap_time = current_time;
}

void arp_handle_button_release(void) {
    arp_state.key_held = false;

    // Only stop if not in latch mode
    if (!arp_state.latch_mode) {
        arp_stop();
    }
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
    if (mode >= ARP_MODE_COUNT) return;
    arp_state.mode = mode;
    dprintf("arp: mode set to %d\n", mode);
}

// =============================================================================
// PHASE 3: EEPROM STORAGE & PRESET MANAGEMENT
// =============================================================================

// Calculate EEPROM address for a given preset slot
// Slots 0-7: Factory arpeggiator presets (not stored in EEPROM)
// Slots 8-31: User arpeggiator presets (stored in EEPROM)
// Slots 32-39: Factory step sequencer presets (not stored in EEPROM)
// Slots 40-63: User step sequencer presets (stored in EEPROM)

static uint32_t arp_get_preset_eeprom_addr(uint8_t preset_id) {
    // Factory presets (0-47) are not stored in EEPROM (in PROGMEM instead)
    if (preset_id < USER_PRESET_START) {
        return 0;
    }

    // User presets are 48-63 (16 total slots)
    if (preset_id >= MAX_ARP_PRESETS) {
        return 0;  // Invalid preset ID
    }

    // Calculate EEPROM slot (0-15 for presets 48-63)
    uint8_t eeprom_slot = preset_id - USER_PRESET_START;

    // Fixed allocation: each preset gets max size regardless of note_count
    // This simplifies addressing at the cost of some wasted space
    return ARP_EEPROM_ADDR + (eeprom_slot * ARP_MAX_PRESET_EEPROM_SIZE);
}

// Validate preset structure
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

    // Check note count bounds
    if (preset->note_count > MAX_PRESET_NOTES) {
        dprintf("arp: validate failed - note_count %d exceeds max %d\n",
                preset->note_count, MAX_PRESET_NOTES);
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

// Save a preset to EEPROM (only for user slots 48-63)
bool arp_save_preset_to_eeprom(uint8_t preset_id) {
    // Check if this is a user preset slot (48-63)
    if (preset_id < USER_PRESET_START || preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: save failed - preset_id %d is not a user preset slot (48-63)\n", preset_id);
        return false;
    }

    // Validate preset before saving
    if (!arp_validate_preset(&arp_presets[preset_id])) {
        dprintf("arp: save failed - preset %d validation failed\n", preset_id);
        return false;
    }

    uint32_t addr = arp_get_preset_eeprom_addr(preset_id);

    dprintf("arp: saving preset %d to EEPROM addr 0x%08lX (size=%u bytes)\n",
            preset_id, addr, sizeof(arp_preset_t));

    eeprom_update_block(&arp_presets[preset_id], (void*)addr, sizeof(arp_preset_t));

    dprintf("arp: preset %d saved successfully\n", preset_id);
    return true;
}

// Load a preset from EEPROM (only for user slots 48-63)
bool arp_load_preset_from_eeprom(uint8_t preset_id) {
    // Check if this is a user preset slot (48-63)
    if (preset_id < USER_PRESET_START || preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: load failed - preset_id %d is not a user preset slot (48-63)\n", preset_id);
        return false;
    }

    uint32_t addr = arp_get_preset_eeprom_addr(preset_id);
    arp_preset_t temp_preset;

    dprintf("arp: loading preset %d from EEPROM addr 0x%08lX\n", preset_id, addr);

    // Read into temporary buffer first
    eeprom_read_block(&temp_preset, (void*)addr, sizeof(arp_preset_t));

    // Validate before copying to active preset
    if (!arp_validate_preset(&temp_preset)) {
        dprintf("arp: load failed - preset %d failed validation (corrupted or uninitialized)\n",
                preset_id);
        return false;
    }

    // Copy to active preset array
    memcpy(&arp_presets[preset_id], &temp_preset, sizeof(arp_preset_t));

    dprintf("arp: preset %d loaded successfully\n", preset_id);
    return true;
}

// Load all user presets from EEPROM (called at init)
void arp_load_all_user_presets(void) {
    uint8_t loaded_count = 0;

    dprintf("arp: loading all user presets from EEPROM...\n");

    // Load user presets (48-63) - can be either arpeggiator or sequencer
    for (uint8_t i = USER_PRESET_START; i < MAX_ARP_PRESETS; i++) {
        if (arp_load_preset_from_eeprom(i)) {
            loaded_count++;
        } else {
            // If load fails, initialize as empty arpeggiator preset
            dprintf("arp: preset %d not found or invalid, initializing as empty\n", i);
            memset(&arp_presets[i], 0, sizeof(arp_preset_t));
            arp_presets[i].preset_type = PRESET_TYPE_ARPEGGIATOR;
            arp_presets[i].note_count = 0;
            arp_presets[i].pattern_length_16ths = 16;  // 1 bar default
            arp_presets[i].gate_length_percent = 80;
            arp_presets[i].timing_mode = TIMING_MODE_STRAIGHT;
            arp_presets[i].note_value = NOTE_VALUE_QUARTER;
            arp_presets[i].magic = ARP_PRESET_MAGIC;
        }
    }

    dprintf("arp: loaded %d user presets from EEPROM\n", loaded_count);
}

// Clear a user preset (fill with empty/default values)
bool arp_clear_preset(uint8_t preset_id) {
    // Check if this is a user preset slot (48-63)
    if (preset_id < USER_PRESET_START || preset_id >= MAX_ARP_PRESETS) {
        dprintf("arp: clear failed - preset_id %d is not a user preset slot (48-63)\n", preset_id);
        return false;
    }

    dprintf("arp: clearing preset %d\n", preset_id);

    // Initialize as empty arpeggiator preset (user can change type later)
    memset(&arp_presets[preset_id], 0, sizeof(arp_preset_t));

    arp_presets[preset_id].preset_type = PRESET_TYPE_ARPEGGIATOR;
    arp_presets[preset_id].note_count = 0;
    arp_presets[preset_id].pattern_length_16ths = 16;
    arp_presets[preset_id].gate_length_percent = 80;
    arp_presets[preset_id].timing_mode = TIMING_MODE_STRAIGHT;
    arp_presets[preset_id].note_value = NOTE_VALUE_QUARTER;
    arp_presets[preset_id].magic = ARP_PRESET_MAGIC;

    // Save to EEPROM
    return arp_save_preset_to_eeprom(preset_id);
}

// Copy a preset to another slot
bool arp_copy_preset(uint8_t source_id, uint8_t dest_id) {
    if (source_id >= MAX_ARP_PRESETS || dest_id >= MAX_ARP_PRESETS) {
        dprintf("arp: copy failed - invalid source %d or dest %d\n", source_id, dest_id);
        return false;
    }

    // Check if destination is a user preset slot (48-63)
    if (dest_id < USER_PRESET_START) {
        dprintf("arp: copy failed - cannot overwrite factory preset %d\n", dest_id);
        return false;
    }

    // Validate source
    if (!arp_validate_preset(&arp_presets[source_id])) {
        dprintf("arp: copy failed - source preset %d invalid\n", source_id);
        return false;
    }

    dprintf("arp: copying preset %d to %d\n", source_id, dest_id);

    // Copy preset data
    memcpy(&arp_presets[dest_id], &arp_presets[source_id], sizeof(arp_preset_t));

    // Save to EEPROM
    return arp_save_preset_to_eeprom(dest_id);
}

// Reset all user presets to empty state and clear EEPROM
void arp_reset_all_user_presets(void) {
    dprintf("arp: resetting all user presets...\n");

    // Reset all user presets (48-63)
    for (uint8_t i = USER_PRESET_START; i < MAX_ARP_PRESETS; i++) {
        arp_clear_preset(i);
    }

    dprintf("arp: all user presets reset\n");
}
