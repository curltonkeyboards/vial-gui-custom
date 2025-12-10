// arp_factory_presets.c - Factory preset initialization for lazy-loading
// This file contains the factory preset definitions that get loaded on-demand

#include "orthomidi5x14.h"
#include <string.h>

// Load factory preset into destination (called by lazy-loading system)
void arp_load_factory_preset(uint8_t preset_id, arp_preset_t *dest) {
    if (dest == NULL) {
        return;
    }

    // Clear destination
    memset(dest, 0, sizeof(arp_preset_t));

    switch (preset_id) {
    // =========================================================================
    // ARPEGGIATOR FACTORY PRESETS (0-7)
    // =========================================================================
    case 0:  // Up 16ths - Classic ascending 16th notes
        dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
        dest->note_count = 4;
        dest->pattern_length_16ths = 16;
        dest->gate_length_percent = 80;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_QUARTER;
        dest->magic = ARP_PRESET_MAGIC;
        dest->notes[0].packed_timing_vel = NOTE_PACK_TIMING_VEL(0, 100, 0);
        dest->notes[0].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 0);
        dest->notes[1].packed_timing_vel = NOTE_PACK_TIMING_VEL(4, 100, 0);
        dest->notes[1].note_octave = NOTE_PACK_NOTE_OCTAVE(1, 0);
        dest->notes[2].packed_timing_vel = NOTE_PACK_TIMING_VEL(8, 100, 0);
        dest->notes[2].note_octave = NOTE_PACK_NOTE_OCTAVE(2, 0);
        dest->notes[3].packed_timing_vel = NOTE_PACK_TIMING_VEL(12, 100, 0);
        dest->notes[3].note_octave = NOTE_PACK_NOTE_OCTAVE(3, 0);
        break;

    case 1:  // Down 16ths - Classic descending 16th notes
        dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
        dest->note_count = 4;
        dest->pattern_length_16ths = 16;
        dest->gate_length_percent = 80;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_QUARTER;
        dest->magic = ARP_PRESET_MAGIC;
        dest->notes[0].packed_timing_vel = NOTE_PACK_TIMING_VEL(0, 100, 0);
        dest->notes[0].note_octave = NOTE_PACK_NOTE_OCTAVE(3, 0);
        dest->notes[1].packed_timing_vel = NOTE_PACK_TIMING_VEL(4, 100, 0);
        dest->notes[1].note_octave = NOTE_PACK_NOTE_OCTAVE(2, 0);
        dest->notes[2].packed_timing_vel = NOTE_PACK_TIMING_VEL(8, 100, 0);
        dest->notes[2].note_octave = NOTE_PACK_NOTE_OCTAVE(1, 0);
        dest->notes[3].packed_timing_vel = NOTE_PACK_TIMING_VEL(12, 100, 0);
        dest->notes[3].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 0);
        break;

    case 2:  // Up-Down 16ths (Exclusive)
        dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
        dest->note_count = 6;
        dest->pattern_length_16ths = 24;
        dest->gate_length_percent = 80;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_QUARTER;
        dest->magic = ARP_PRESET_MAGIC;
        dest->notes[0].packed_timing_vel = NOTE_PACK_TIMING_VEL(0, 100, 0);
        dest->notes[0].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 0);
        dest->notes[1].packed_timing_vel = NOTE_PACK_TIMING_VEL(4, 100, 0);
        dest->notes[1].note_octave = NOTE_PACK_NOTE_OCTAVE(1, 0);
        dest->notes[2].packed_timing_vel = NOTE_PACK_TIMING_VEL(8, 100, 0);
        dest->notes[2].note_octave = NOTE_PACK_NOTE_OCTAVE(2, 0);
        dest->notes[3].packed_timing_vel = NOTE_PACK_TIMING_VEL(12, 100, 0);
        dest->notes[3].note_octave = NOTE_PACK_NOTE_OCTAVE(3, 0);
        dest->notes[4].packed_timing_vel = NOTE_PACK_TIMING_VEL(16, 100, 0);
        dest->notes[4].note_octave = NOTE_PACK_NOTE_OCTAVE(2, 0);
        dest->notes[5].packed_timing_vel = NOTE_PACK_TIMING_VEL(20, 100, 0);
        dest->notes[5].note_octave = NOTE_PACK_NOTE_OCTAVE(1, 0);
        break;

    case 3:  // Random 8ths
        dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
        dest->note_count = 4;
        dest->pattern_length_16ths = 32;
        dest->gate_length_percent = 75;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_EIGHTH;
        dest->magic = ARP_PRESET_MAGIC;
        for (uint8_t i = 0; i < 4; i++) {
            dest->notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 8, 90, 0);
            dest->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 0);
        }
        break;

    case 4:  // Up 2 Octaves
        dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
        dest->note_count = 8;
        dest->pattern_length_16ths = 32;
        dest->gate_length_percent = 80;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_SIXTEENTH;
        dest->magic = ARP_PRESET_MAGIC;
        for (uint8_t i = 0; i < 4; i++) {
            dest->notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 100, 0);
            dest->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(i, 0);
        }
        for (uint8_t i = 0; i < 4; i++) {
            dest->notes[i + 4].packed_timing_vel = NOTE_PACK_TIMING_VEL((i + 4) * 4, 100, 0);
            dest->notes[i + 4].note_octave = NOTE_PACK_NOTE_OCTAVE(i, 1);
        }
        break;

    case 5:  // Down 2 Octaves
        dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
        dest->note_count = 8;
        dest->pattern_length_16ths = 32;
        dest->gate_length_percent = 80;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_SIXTEENTH;
        dest->magic = ARP_PRESET_MAGIC;
        for (uint8_t i = 0; i < 4; i++) {
            dest->notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 100, 0);
            dest->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(3 - i, 1);
        }
        for (uint8_t i = 0; i < 4; i++) {
            dest->notes[i + 4].packed_timing_vel = NOTE_PACK_TIMING_VEL((i + 4) * 4, 100, 0);
            dest->notes[i + 4].note_octave = NOTE_PACK_NOTE_OCTAVE(3 - i, 0);
        }
        break;

    case 6:  // Octave Jump
        dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
        dest->note_count = 8;
        dest->pattern_length_16ths = 32;
        dest->gate_length_percent = 75;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_EIGHTH;
        dest->magic = ARP_PRESET_MAGIC;
        for (uint8_t i = 0; i < 4; i++) {
            dest->notes[i * 2].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 8, 100, 0);
            dest->notes[i * 2].note_octave = NOTE_PACK_NOTE_OCTAVE(i, 0);
            dest->notes[i * 2 + 1].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 8 + 4, 100, 0);
            dest->notes[i * 2 + 1].note_octave = NOTE_PACK_NOTE_OCTAVE(i, 1);
        }
        break;

    case 7:  // Rapid 16ths
        dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
        dest->note_count = 8;
        dest->pattern_length_16ths = 16;
        dest->gate_length_percent = 60;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_SIXTEENTH;
        dest->magic = ARP_PRESET_MAGIC;
        for (uint8_t i = 0; i < 8; i++) {
            dest->notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 2, 90, 0);
            dest->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(i % 4, 0);
        }
        break;

    // Reserved arpeggiator factory presets (8-47) - Initialize as empty
    default:
        if (preset_id >= 0 && preset_id < NUM_FACTORY_ARP_PRESETS) {
            dest->preset_type = PRESET_TYPE_ARPEGGIATOR;
            dest->note_count = 0;
            dest->pattern_length_16ths = 16;
            dest->gate_length_percent = 80;
            dest->timing_mode = TIMING_MODE_STRAIGHT;
            dest->note_value = NOTE_VALUE_QUARTER;
            dest->magic = ARP_PRESET_MAGIC;
        }
        break;
    }
}

// Load step sequencer factory preset into destination (called by lazy-loading system)
void seq_load_factory_preset(uint8_t preset_id, seq_preset_t *dest) {
    if (dest == NULL) {
        return;
    }

    // Clear destination
    memset(dest, 0, sizeof(seq_preset_t));

    switch (preset_id) {
    // =========================================================================
    // STEP SEQUENCER FACTORY PRESETS (0-47)
    // =========================================================================
    case 0:  // C Major Scale
        dest->preset_type = PRESET_TYPE_STEP_SEQUENCER;
        dest->note_count = 8;
        dest->pattern_length_16ths = 32;
        dest->gate_length_percent = 80;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_QUARTER;
        dest->magic = ARP_PRESET_MAGIC;
        {
            const uint8_t c_major_notes[] = {0, 2, 4, 5, 7, 9, 11, 0};
            const uint8_t c_major_octaves[] = {4, 4, 4, 4, 4, 4, 4, 5};
            for (uint8_t i = 0; i < 8; i++) {
                dest->notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 100, 0);
                dest->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(c_major_notes[i], c_major_octaves[i]);
            }
        }
        break;

    case 1:  // Bass Line
        dest->preset_type = PRESET_TYPE_STEP_SEQUENCER;
        dest->note_count = 4;
        dest->pattern_length_16ths = 16;
        dest->gate_length_percent = 70;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_QUARTER;
        dest->magic = ARP_PRESET_MAGIC;
        {
            const uint8_t bass_notes[] = {0, 0, 7, 0};
            const uint8_t bass_octaves[] = {2, 2, 2, 3};
            for (uint8_t i = 0; i < 4; i++) {
                dest->notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 110, 0);
                dest->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(bass_notes[i], bass_octaves[i]);
            }
        }
        break;

    case 2:  // Techno Kick
        dest->preset_type = PRESET_TYPE_STEP_SEQUENCER;
        dest->note_count = 4;
        dest->pattern_length_16ths = 16;
        dest->gate_length_percent = 50;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_QUARTER;
        dest->magic = ARP_PRESET_MAGIC;
        for (uint8_t i = 0; i < 4; i++) {
            dest->notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 127, 0);
            dest->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(0, 1);
        }
        break;

    case 3:  // Melody 1
        dest->preset_type = PRESET_TYPE_STEP_SEQUENCER;
        dest->note_count = 8;
        dest->pattern_length_16ths = 32;
        dest->gate_length_percent = 75;
        dest->timing_mode = TIMING_MODE_STRAIGHT;
        dest->note_value = NOTE_VALUE_QUARTER;
        dest->magic = ARP_PRESET_MAGIC;
        {
            const uint8_t melody_notes[] = {4, 7, 9, 7, 4, 2, 0, 2};
            for (uint8_t i = 0; i < 8; i++) {
                dest->notes[i].packed_timing_vel = NOTE_PACK_TIMING_VEL(i * 4, 90, 0);
                dest->notes[i].note_octave = NOTE_PACK_NOTE_OCTAVE(melody_notes[i], 4);
            }
        }
        break;

    // Reserved sequencer factory presets (4-47) - Initialize as empty
    default:
        if (preset_id >= 0 && preset_id < NUM_FACTORY_SEQ_PRESETS) {
            dest->preset_type = PRESET_TYPE_STEP_SEQUENCER;
            dest->note_count = 0;
            dest->pattern_length_16ths = 16;
            dest->gate_length_percent = 80;
            dest->timing_mode = TIMING_MODE_STRAIGHT;
            dest->note_value = NOTE_VALUE_QUARTER;
            dest->magic = ARP_PRESET_MAGIC;
        }
        break;
    }
}
