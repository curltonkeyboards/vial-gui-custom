// arpeggiator_hid.c - Raw HID handlers for VIAL arpeggiator integration

#include QMK_KEYBOARD_H
#include "orthomidi5x14.h"
#include "raw_hid.h"
#include <string.h>

// =============================================================================
// ARPEGGIATOR RAW HID HANDLERS
// =============================================================================

// Arpeggiator HID command IDs
#define ARP_CMD_GET_PRESET       0xC0  // Get preset data (chunked)
#define ARP_CMD_SET_PRESET       0xC1  // Set preset data (chunked)
#define ARP_CMD_SAVE_PRESET      0xC2  // Save preset to EEPROM
#define ARP_CMD_LOAD_PRESET      0xC3  // Load preset from EEPROM
#define ARP_CMD_CLEAR_PRESET     0xC4  // Clear a preset
#define ARP_CMD_COPY_PRESET      0xC5  // Copy preset
#define ARP_CMD_RESET_ALL        0xC6  // Reset all user presets
#define ARP_CMD_GET_STATE        0xC7  // Get arpeggiator state
#define ARP_CMD_SET_STATE        0xC8  // Set arpeggiator state
#define ARP_CMD_GET_INFO         0xC9  // Get arp system info
#define ARP_CMD_SET_NOTE         0xCA  // Set single note data
#define ARP_CMD_SET_NOTES_CHUNK  0xCB  // Set multiple notes (chunked)

// HID Protocol IDs (matching dynamic macro protocol)
#define HID_MANUFACTURER_ID 0x7D
#define HID_SUB_ID          0x00
#define HID_DEVICE_ID       0x4D

void arp_hid_receive(uint8_t *data, uint8_t length) {
    uint8_t cmd = data[3];
    uint8_t *params = &data[4];  // Parameters start at byte 4

    dprintf("ARP HID: cmd=0x%02X\n", cmd);

    switch (cmd) {
        case ARP_CMD_GET_INFO: {
            // Return system info
            // params[0] = status (0 = success)
            // params[1] = number of presets
            // params[2] = factory preset count
            // params[3] = user preset start slot
            params[0] = 0;  // Success
            params[1] = MAX_ARP_PRESETS;      // 64 total presets
            params[2] = NUM_FACTORY_PRESETS;  // 48 factory presets (0-47)
            params[3] = USER_PRESET_START;    // User presets start at slot 48
            dprintf("ARP HID: GET_INFO - %d presets total, %d factory, %d user start\n",
                    MAX_ARP_PRESETS, NUM_FACTORY_PRESETS, USER_PRESET_START);
            break;
        }

        case ARP_CMD_GET_STATE: {
            // Return arpeggiator state
            // params[0] = status
            // params[1] = active
            // params[2] = sync_mode
            // params[3] = latch_mode
            // params[4] = mode
            // params[5] = current_preset_id
            params[0] = 0;  // Success
            params[1] = arp_state.active ? 1 : 0;
            params[2] = arp_state.sync_mode ? 1 : 0;
            params[3] = arp_state.latch_mode ? 1 : 0;
            params[4] = arp_state.mode;
            params[5] = arp_state.current_preset_id;
            dprintf("ARP HID: GET_STATE - preset=%d active=%d\n",
                    arp_state.current_preset_id, arp_state.active);
            break;
        }

        case ARP_CMD_SET_STATE: {
            // Set arpeggiator state
            // params[0] = active
            // params[1] = sync_mode
            // params[2] = latch_mode
            // params[3] = mode
            // params[4] = preset_id
            if (params[0]) {
                arp_start(params[4]);
            } else {
                arp_stop();
            }
            arp_state.sync_mode = params[1] ? true : false;
            arp_state.latch_mode = params[2] ? true : false;
            arp_set_mode((arp_mode_t)params[3]);

            params[0] = 0;  // Success status
            dprintf("ARP HID: SET_STATE - preset=%d active=%d\n", params[4], params[0]);
            break;
        }

        case ARP_CMD_SAVE_PRESET: {
            // Save preset to EEPROM
            // params[0] = preset_id
            uint8_t preset_id = params[0];
            bool success = arp_save_preset_to_eeprom(preset_id);
            params[0] = success ? 0 : 1;  // 0=success, 1=error
            dprintf("ARP HID: SAVE_PRESET id=%d result=%d\n", preset_id, success);
            break;
        }

        case ARP_CMD_LOAD_PRESET: {
            // Load preset from EEPROM
            // params[0] = preset_id
            uint8_t preset_id = params[0];
            bool success = arp_load_preset_from_eeprom(preset_id);
            params[0] = success ? 0 : 1;  // 0=success, 1=error
            dprintf("ARP HID: LOAD_PRESET id=%d result=%d\n", preset_id, success);
            break;
        }

        case ARP_CMD_CLEAR_PRESET: {
            // Clear preset
            // params[0] = preset_id
            uint8_t preset_id = params[0];
            bool success = arp_clear_preset(preset_id);
            params[0] = success ? 0 : 1;
            dprintf("ARP HID: CLEAR_PRESET id=%d result=%d\n", preset_id, success);
            break;
        }

        case ARP_CMD_COPY_PRESET: {
            // Copy preset
            // params[0] = source_id
            // params[1] = dest_id
            uint8_t source_id = params[0];
            uint8_t dest_id = params[1];
            bool success = arp_copy_preset(source_id, dest_id);
            params[0] = success ? 0 : 1;
            dprintf("ARP HID: COPY_PRESET src=%d dst=%d result=%d\n",
                    source_id, dest_id, success);
            break;
        }

        case ARP_CMD_RESET_ALL: {
            // Reset all user presets
            arp_reset_all_user_presets();
            params[0] = 0;  // Success
            dprintf("ARP HID: RESET_ALL completed\n");
            break;
        }

        case ARP_CMD_GET_PRESET: {
            // Get preset data (basic info)
            // params[0] = preset_id (input)
            // Returns:
            //   params[0] = status (0=success, 1=error)
            //   params[1] = preset_type
            //   params[2] = note_count
            //   params[3] = pattern_length_16ths (high byte)
            //   params[4] = pattern_length_16ths (low byte)
            //   params[5] = gate_length_percent
            //   params[6] = timing_mode (0=straight, 1=triplet, 2=dotted)
            //   params[7] = note_value (0=quarter, 1=eighth, 2=sixteenth)
            uint8_t preset_id = params[0];
            if (preset_id >= MAX_ARP_PRESETS) {
                params[0] = 1;  // Error
                dprintf("ARP HID: GET_PRESET failed - invalid id %d\n", preset_id);
                break;
            }

            arp_preset_t *preset = &arp_presets[preset_id];

            params[0] = 0;  // Success
            params[1] = preset->preset_type;
            params[2] = preset->note_count;
            params[3] = (preset->pattern_length_16ths >> 8) & 0xFF;
            params[4] = preset->pattern_length_16ths & 0xFF;
            params[5] = preset->gate_length_percent;
            params[6] = preset->timing_mode;
            params[7] = preset->note_value;

            dprintf("ARP HID: GET_PRESET id=%d type=%d notes=%d timing=%d/%d\n",
                    preset_id, preset->preset_type, preset->note_count,
                    preset->note_value, preset->timing_mode);
            break;
        }

        case ARP_CMD_SET_PRESET: {
            // Set preset data (basic info only)
            // params[0] = preset_id
            // params[1] = preset_type
            // params[2] = note_count
            // params[3] = pattern_length_16ths (high byte)
            // params[4] = pattern_length_16ths (low byte)
            // params[5] = gate_length_percent
            // params[6] = timing_mode (0=straight, 1=triplet, 2=dotted)
            // params[7] = note_value (0=quarter, 1=eighth, 2=sixteenth)
            uint8_t preset_id = params[0];

            if (preset_id < USER_PRESET_START) {
                params[0] = 1;  // Error: cannot modify factory presets (0-47)
                dprintf("ARP HID: SET_PRESET failed - cannot modify factory preset %d\n", preset_id);
                break;
            }

            if (preset_id >= MAX_ARP_PRESETS) {
                params[0] = 1;  // Error: invalid preset ID
                dprintf("ARP HID: SET_PRESET failed - invalid id %d\n", preset_id);
                break;
            }

            arp_preset_t *preset = &arp_presets[preset_id];

            // Set basic preset info
            preset->preset_type = params[1];
            preset->note_count = params[2];
            preset->pattern_length_16ths = (params[3] << 8) | params[4];
            preset->gate_length_percent = params[5];
            preset->timing_mode = params[6];
            preset->note_value = params[7];
            preset->magic = ARP_PRESET_MAGIC;

            // Validate
            if (!arp_validate_preset(preset)) {
                params[0] = 1;  // Error: validation failed
                dprintf("ARP HID: SET_PRESET validation failed for preset %d\n", preset_id);
                break;
            }

            params[0] = 0;  // Success
            dprintf("ARP HID: SET_PRESET id=%d type=%d notes=%d timing=%d/%d\n",
                    preset_id, preset->preset_type, preset->note_count,
                    preset->note_value, preset->timing_mode);
            break;
        }

        case ARP_CMD_SET_NOTE: {
            // Set a single note in a preset
            // params[0] = preset_id
            // params[1] = note_index (0-127)
            // params[2-3] = packed_timing_vel (uint16_t, little-endian)
            // params[4] = note_octave (uint8_t)
            uint8_t preset_id = params[0];
            uint8_t note_index = params[1];

            if (preset_id < USER_PRESET_START || preset_id >= MAX_ARP_PRESETS) {
                params[0] = 1;  // Error: invalid preset ID
                dprintf("ARP HID: SET_NOTE failed - invalid preset id %d\n", preset_id);
                break;
            }

            if (note_index >= MAX_PRESET_NOTES) {
                params[0] = 1;  // Error: invalid note index
                dprintf("ARP HID: SET_NOTE failed - invalid note index %d\n", note_index);
                break;
            }

            arp_preset_t *preset = &arp_presets[preset_id];

            // Unpack note data from params
            uint16_t packed_timing_vel = params[2] | (params[3] << 8);
            uint8_t note_octave = params[4];

            // Set note data
            preset->notes[note_index].packed_timing_vel = packed_timing_vel;
            preset->notes[note_index].note_octave = note_octave;

            params[0] = 0;  // Success
            dprintf("ARP HID: SET_NOTE preset=%d idx=%d timing=%d vel=%d\n",
                    preset_id, note_index,
                    NOTE_GET_TIMING(packed_timing_vel),
                    NOTE_GET_VELOCITY(packed_timing_vel));
            break;
        }

        case ARP_CMD_SET_NOTES_CHUNK: {
            // Set multiple notes in one packet (chunked transfer)
            // params[0] = preset_id
            // params[1] = start_note_index
            // params[2] = note_count (how many notes in this chunk, max 9)
            // params[3+] = note data (3 bytes per note)
            //   Each note:
            //     [0-1] = packed_timing_vel (uint16_t, little-endian)
            //     [2]   = note_octave (uint8_t)
            uint8_t preset_id = params[0];
            uint8_t start_index = params[1];
            uint8_t chunk_count = params[2];

            if (preset_id < USER_PRESET_START || preset_id >= MAX_ARP_PRESETS) {
                params[0] = 1;  // Error: invalid preset ID
                dprintf("ARP HID: SET_NOTES_CHUNK failed - invalid preset id %d\n", preset_id);
                break;
            }

            if (start_index >= MAX_PRESET_NOTES) {
                params[0] = 1;  // Error: invalid start index
                dprintf("ARP HID: SET_NOTES_CHUNK failed - invalid start index %d\n", start_index);
                break;
            }

            if (chunk_count == 0 || chunk_count > 9) {
                params[0] = 1;  // Error: invalid chunk count (max 9 notes per packet)
                dprintf("ARP HID: SET_NOTES_CHUNK failed - invalid chunk count %d\n", chunk_count);
                break;
            }

            if (start_index + chunk_count > MAX_PRESET_NOTES) {
                params[0] = 1;  // Error: would exceed preset note array
                dprintf("ARP HID: SET_NOTES_CHUNK failed - would exceed array (start=%d count=%d)\n",
                        start_index, chunk_count);
                break;
            }

            arp_preset_t *preset = &arp_presets[preset_id];

            // Parse and set notes
            uint8_t *note_data = &params[3];  // Note data starts at params[3]
            for (uint8_t i = 0; i < chunk_count; i++) {
                uint8_t note_idx = start_index + i;
                uint8_t offset = i * 3;  // 3 bytes per note

                // Extract note data (little-endian for packed_timing_vel)
                uint16_t packed_timing_vel = note_data[offset] | (note_data[offset + 1] << 8);
                uint8_t note_octave = note_data[offset + 2];

                // Set note data
                preset->notes[note_idx].packed_timing_vel = packed_timing_vel;
                preset->notes[note_idx].note_octave = note_octave;
            }

            params[0] = 0;  // Success
            params[1] = chunk_count;  // Echo back how many notes were written
            dprintf("ARP HID: SET_NOTES_CHUNK preset=%d start=%d count=%d\n",
                    preset_id, start_index, chunk_count);
            break;
        }

        default:
            params[0] = 0xFF;  // Unknown command
            dprintf("ARP HID: Unknown command 0x%02X\n", cmd);
            break;
    }

    raw_hid_send(data, length);
}

void raw_hid_receive_kb(uint8_t *data, uint8_t length) {
    // Check if this is an arpeggiator command (0xC0-0xCB)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] >= 0xC0 && data[3] <= 0xCB) {

        dprintf("raw_hid_receive_kb: Arpeggiator packet detected, forwarding\n");
        arp_hid_receive(data, length);
        return;
    }

    // Not an arpeggiator command - ignore or handle other custom commands
    dprintf("raw_hid_receive_kb: Unhandled packet\n");
}
