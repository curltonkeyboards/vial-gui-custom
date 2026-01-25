// arpeggiator_hid.c - Raw HID handlers for VIAL arpeggiator integration

#include QMK_KEYBOARD_H
#include "orthomidi5x14.h"
#include "raw_hid.h"
#include "process_midi.h"
#include "matrix.h"
#include "process_dynamic_macro.h"
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
#define ARP_CMD_SET_MODE         0xCC  // Set arpeggiator mode only

// HID Protocol IDs (matching dynamic macro protocol)
#define HID_MANUFACTURER_ID 0x7D
#define HID_SUB_ID          0x00
#define HID_DEVICE_ID       0x4D

// Temporary buffer for HID preset editing (since presets are lazy-loaded)
// Use seq_preset_t since it's larger (392 bytes) and can hold both arp and seq presets
static seq_preset_t hid_edit_preset;
static uint8_t hid_edit_preset_id = 255;  // Which preset is being edited (255 = none)

void arp_hid_receive(uint8_t *data, uint8_t length) {
    uint8_t cmd = data[3];
    uint8_t *params = &data[4];  // Parameters start at byte 4

    dprintf("ARP HID: cmd=0x%02X\n", cmd);

    switch (cmd) {
        case ARP_CMD_GET_INFO: {
            // Return system info
            // params[0] = status (0 = success)
            // params[1] = num_factory_arp_presets (48)
            // params[2] = num_user_arp_presets (20)
            // params[3] = num_factory_seq_presets (48)
            // params[4] = num_user_seq_presets (20)
            // params[5] = max_arp_notes (64)
            // params[6] = max_seq_notes (128)
            params[0] = 0;  // Success
            params[1] = NUM_FACTORY_ARP_PRESETS;  // 48
            params[2] = NUM_USER_ARP_PRESETS;     // 20
            params[3] = NUM_FACTORY_SEQ_PRESETS;  // 48
            params[4] = NUM_USER_SEQ_PRESETS;     // 20
            params[5] = MAX_ARP_PRESET_NOTES;     // 64
            params[6] = MAX_SEQ_PRESET_NOTES;     // 128
            dprintf("ARP HID: GET_INFO - arp:%d+%d seq:%d+%d\n",
                    NUM_FACTORY_ARP_PRESETS, NUM_USER_ARP_PRESETS,
                    NUM_FACTORY_SEQ_PRESETS, NUM_USER_SEQ_PRESETS);
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
            // Save preset to EEPROM from HID edit buffer
            // params[0] = preset_id
            uint8_t preset_id = params[0];

            // Check if this preset is currently in the edit buffer
            if (hid_edit_preset_id != preset_id) {
                params[0] = 1;  // Error: preset not loaded in edit buffer
                dprintf("ARP HID: SAVE_PRESET failed - preset %d not in edit buffer (have %d)\n",
                        preset_id, hid_edit_preset_id);
                break;
            }

            // Route to correct save function based on preset type
            bool success = false;
            if (hid_edit_preset.preset_type == PRESET_TYPE_ARPEGGIATOR) {
                success = arp_save_preset_to_eeprom(preset_id, (arp_preset_t*)&hid_edit_preset);
            } else if (hid_edit_preset.preset_type == PRESET_TYPE_STEP_SEQUENCER) {
                success = seq_save_preset_to_eeprom(preset_id, &hid_edit_preset);
            }

            params[0] = success ? 0 : 1;  // 0=success, 1=error
            dprintf("ARP HID: SAVE_PRESET id=%d type=%d result=%d\n",
                    preset_id, hid_edit_preset.preset_type, success);
            break;
        }

        case ARP_CMD_LOAD_PRESET: {
            // Load preset into active slot
            // params[0] = preset_id
            // params[1] = seq_slot (0-3, only used for sequencer presets)
            uint8_t preset_id = params[0];
            uint8_t seq_slot = params[1];
            bool success = false;

            // Route based on preset ID range
            if (preset_id < 68) {
                // Arpeggiator preset (0-67)
                success = arp_load_preset_into_slot(preset_id);
            } else if (preset_id >= 68 && preset_id < 136) {
                // Sequencer preset (68-135)
                success = seq_load_preset_into_slot(preset_id, seq_slot);
            }

            params[0] = success ? 0 : 1;  // 0=success, 1=error
            dprintf("ARP HID: LOAD_PRESET id=%d slot=%d result=%d\n", preset_id, seq_slot, success);
            break;
        }

        case ARP_CMD_CLEAR_PRESET: {
            // Clear preset
            // params[0] = preset_id
            uint8_t preset_id = params[0];
            bool success = false;

            // Route based on preset ID range
            if (preset_id >= 48 && preset_id < 68) {
                // Arpeggiator user preset (48-67)
                success = arp_clear_preset(preset_id);
            } else if (preset_id >= 116 && preset_id < 136) {
                // Sequencer user preset (116-135)
                success = seq_clear_preset(preset_id);
            }

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
            bool success = false;

            // Determine type based on destination ID and route accordingly
            if (dest_id >= 48 && dest_id < 68) {
                // Arpeggiator destination (must also have arp source)
                success = arp_copy_preset(source_id, dest_id);
            } else if (dest_id >= 116 && dest_id < 136) {
                // Sequencer destination (must also have seq source)
                success = seq_copy_preset(source_id, dest_id);
            }

            params[0] = success ? 0 : 1;
            dprintf("ARP HID: COPY_PRESET src=%d dst=%d result=%d\n",
                    source_id, dest_id, success);
            break;
        }

        case ARP_CMD_RESET_ALL: {
            // Reset all user presets (both arp and seq)
            // params[0] = preset_type (0=arp, 1=seq, 2=both)
            uint8_t type = params[0];

            if (type == 0 || type == 2) {
                arp_reset_all_user_presets();
            }
            if (type == 1 || type == 2) {
                seq_reset_all_user_presets();
            }

            params[0] = 0;  // Success
            dprintf("ARP HID: RESET_ALL type=%d completed\n", type);
            break;
        }

        case ARP_CMD_GET_PRESET: {
            // Get preset data (basic info) and load into HID edit buffer
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

            // Lazy-load preset into HID edit buffer based on ID range
            bool loaded = false;

            if (preset_id < 68) {
                // Arpeggiator preset (0-67)
                if (preset_id >= 48) {
                    // User preset (48-67)
                    loaded = arp_load_preset_from_eeprom(preset_id, (arp_preset_t*)&hid_edit_preset);
                } else {
                    // Factory preset (0-47)
                    arp_load_factory_preset(preset_id, (arp_preset_t*)&hid_edit_preset);
                    loaded = true;
                }
            } else if (preset_id >= 68 && preset_id < 136) {
                // Sequencer preset (68-135)
                if (preset_id >= 116) {
                    // User preset (116-135)
                    loaded = seq_load_preset_from_eeprom(preset_id, &hid_edit_preset);
                } else {
                    // Factory preset (68-115, maps to internal 0-47)
                    uint8_t factory_id = preset_id - 68;
                    seq_load_factory_preset(factory_id, &hid_edit_preset);
                    loaded = true;
                }
            }

            if (!loaded) {
                params[0] = 1;  // Error
                dprintf("ARP HID: GET_PRESET failed - could not load preset %d\n", preset_id);
                break;
            }

            hid_edit_preset_id = preset_id;

            params[0] = 0;  // Success
            params[1] = hid_edit_preset.preset_type;
            params[2] = hid_edit_preset.note_count;
            params[3] = (hid_edit_preset.pattern_length_16ths >> 8) & 0xFF;
            params[4] = hid_edit_preset.pattern_length_16ths & 0xFF;
            params[5] = hid_edit_preset.gate_length_percent;
            params[6] = hid_edit_preset.timing_mode;
            params[7] = hid_edit_preset.note_value;

            dprintf("ARP HID: GET_PRESET id=%d type=%d notes=%d timing=%d/%d\n",
                    preset_id, hid_edit_preset.preset_type, hid_edit_preset.note_count,
                    hid_edit_preset.note_value, hid_edit_preset.timing_mode);
            break;
        }

        case ARP_CMD_SET_PRESET: {
            // Set preset data (basic info only) in HID edit buffer
            // params[0] = preset_id
            // params[1] = preset_type
            // params[2] = note_count
            // params[3] = pattern_length_16ths (high byte)
            // params[4] = pattern_length_16ths (low byte)
            // params[5] = gate_length_percent
            // params[6] = timing_mode (0=straight, 1=triplet, 2=dotted)
            // params[7] = note_value (0=quarter, 1=eighth, 2=sixteenth)
            uint8_t preset_id = params[0];

            // Determine preset type based on ID range
            bool is_arp = (preset_id < 68);
            bool is_seq = (preset_id >= 68 && preset_id < 136);

            if (!is_arp && !is_seq) {
                params[0] = 1;  // Error: invalid preset ID
                dprintf("ARP HID: SET_PRESET failed - invalid id %d\n", preset_id);
                break;
            }

            // Check if this is a factory preset (cannot modify)
            if (is_arp && preset_id < USER_ARP_PRESET_START) {
                params[0] = 1;  // Error: cannot modify arp factory presets (0-47)
                dprintf("ARP HID: SET_PRESET failed - cannot modify factory preset %d\n", preset_id);
                break;
            }
            if (is_seq && preset_id < USER_SEQ_PRESET_START) {
                params[0] = 1;  // Error: cannot modify seq factory presets (68-115)
                dprintf("ARP HID: SET_PRESET failed - cannot modify factory preset %d\n", preset_id);
                break;
            }

            // Load preset into edit buffer if not already there
            if (hid_edit_preset_id != preset_id) {
                if (is_arp) {
                    // Arpeggiator preset (48-67 user)
                    if (!arp_load_preset_from_eeprom(preset_id, (arp_preset_t*)&hid_edit_preset)) {
                        // If load fails, initialize as empty arp preset
                        memset(&hid_edit_preset, 0, sizeof(arp_preset_t));
                        hid_edit_preset.preset_type = PRESET_TYPE_ARPEGGIATOR;
                    }
                } else {
                    // Sequencer preset (116-135 user)
                    if (!seq_load_preset_from_eeprom(preset_id, &hid_edit_preset)) {
                        // If load fails, initialize as empty seq preset
                        memset(&hid_edit_preset, 0, sizeof(seq_preset_t));
                        hid_edit_preset.preset_type = PRESET_TYPE_STEP_SEQUENCER;
                    }
                }
                hid_edit_preset_id = preset_id;
            }

            // Set basic preset info in edit buffer
            hid_edit_preset.preset_type = params[1];
            hid_edit_preset.note_count = params[2];
            hid_edit_preset.pattern_length_16ths = (params[3] << 8) | params[4];
            hid_edit_preset.gate_length_percent = params[5];
            hid_edit_preset.timing_mode = params[6];
            hid_edit_preset.note_value = params[7];
            hid_edit_preset.magic = ARP_PRESET_MAGIC;

            // Validate using appropriate function
            bool valid = false;
            if (hid_edit_preset.preset_type == PRESET_TYPE_ARPEGGIATOR) {
                valid = arp_validate_preset((arp_preset_t*)&hid_edit_preset);
            } else if (hid_edit_preset.preset_type == PRESET_TYPE_STEP_SEQUENCER) {
                valid = seq_validate_preset(&hid_edit_preset);
            }

            if (!valid) {
                params[0] = 1;  // Error: validation failed
                dprintf("ARP HID: SET_PRESET validation failed for preset %d\n", preset_id);
                break;
            }

            params[0] = 0;  // Success
            dprintf("ARP HID: SET_PRESET id=%d type=%d notes=%d timing=%d/%d\n",
                    preset_id, hid_edit_preset.preset_type, hid_edit_preset.note_count,
                    hid_edit_preset.note_value, hid_edit_preset.timing_mode);
            break;
        }

        case ARP_CMD_SET_NOTE: {
            // Set a single note in the HID edit buffer
            // params[0] = preset_id
            // params[1] = note_index (0-127)
            // params[2-3] = packed_timing_vel (uint16_t, little-endian)
            // params[4] = note_octave (uint8_t)
            uint8_t preset_id = params[0];
            uint8_t note_index = params[1];

            // Determine preset type and validate ranges
            bool is_arp = (preset_id < 68);
            bool is_seq = (preset_id >= 68 && preset_id < 136);

            if (!is_arp && !is_seq) {
                params[0] = 1;  // Error: invalid preset ID
                dprintf("ARP HID: SET_NOTE failed - invalid preset id %d\n", preset_id);
                break;
            }

            // Check if this is a user preset (only user presets can be modified)
            if (is_arp && (preset_id < USER_ARP_PRESET_START || preset_id >= MAX_ARP_PRESETS)) {
                params[0] = 1;  // Error: invalid arp preset ID or factory preset
                dprintf("ARP HID: SET_NOTE failed - invalid arp preset id %d\n", preset_id);
                break;
            }
            if (is_seq && (preset_id < USER_SEQ_PRESET_START || preset_id >= MAX_SEQ_PRESETS)) {
                params[0] = 1;  // Error: invalid seq preset ID or factory preset
                dprintf("ARP HID: SET_NOTE failed - invalid seq preset id %d\n", preset_id);
                break;
            }

            // Check note index against correct max
            uint8_t max_notes = is_arp ? MAX_ARP_PRESET_NOTES : MAX_SEQ_PRESET_NOTES;
            if (note_index >= max_notes) {
                params[0] = 1;  // Error: invalid note index
                dprintf("ARP HID: SET_NOTE failed - invalid note index %d (max %d)\n", note_index, max_notes);
                break;
            }

            // Check if this preset is in the edit buffer
            if (hid_edit_preset_id != preset_id) {
                params[0] = 1;  // Error: preset not loaded in edit buffer
                dprintf("ARP HID: SET_NOTE failed - preset %d not in edit buffer\n", preset_id);
                break;
            }

            // Unpack note data from params
            uint16_t packed_timing_vel = params[2] | (params[3] << 8);
            uint8_t note_octave = params[4];

            // Set note data in edit buffer
            hid_edit_preset.notes[note_index].packed_timing_vel = packed_timing_vel;
            hid_edit_preset.notes[note_index].note_octave = note_octave;

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

            // Determine preset type and validate ranges
            bool is_arp = (preset_id < 68);
            bool is_seq = (preset_id >= 68 && preset_id < 136);

            if (!is_arp && !is_seq) {
                params[0] = 1;  // Error: invalid preset ID
                dprintf("ARP HID: SET_NOTES_CHUNK failed - invalid preset id %d\n", preset_id);
                break;
            }

            // Check if this is a user preset (only user presets can be modified)
            if (is_arp && (preset_id < USER_ARP_PRESET_START || preset_id >= MAX_ARP_PRESETS)) {
                params[0] = 1;  // Error: invalid arp preset ID or factory preset
                dprintf("ARP HID: SET_NOTES_CHUNK failed - invalid arp preset id %d\n", preset_id);
                break;
            }
            if (is_seq && (preset_id < USER_SEQ_PRESET_START || preset_id >= MAX_SEQ_PRESETS)) {
                params[0] = 1;  // Error: invalid seq preset ID or factory preset
                dprintf("ARP HID: SET_NOTES_CHUNK failed - invalid seq preset id %d\n", preset_id);
                break;
            }

            // Check note index against correct max
            uint8_t max_notes = is_arp ? MAX_ARP_PRESET_NOTES : MAX_SEQ_PRESET_NOTES;
            if (start_index >= max_notes) {
                params[0] = 1;  // Error: invalid start index
                dprintf("ARP HID: SET_NOTES_CHUNK failed - invalid start index %d (max %d)\n", start_index, max_notes);
                break;
            }

            if (chunk_count == 0 || chunk_count > 9) {
                params[0] = 1;  // Error: invalid chunk count (max 9 notes per packet)
                dprintf("ARP HID: SET_NOTES_CHUNK failed - invalid chunk count %d\n", chunk_count);
                break;
            }

            if (start_index + chunk_count > max_notes) {
                params[0] = 1;  // Error: would exceed preset note array
                dprintf("ARP HID: SET_NOTES_CHUNK failed - would exceed array (start=%d count=%d max=%d)\n",
                        start_index, chunk_count, max_notes);
                break;
            }

            // Check if this preset is in the edit buffer
            if (hid_edit_preset_id != preset_id) {
                params[0] = 1;  // Error: preset not loaded in edit buffer
                dprintf("ARP HID: SET_NOTES_CHUNK failed - preset %d not in edit buffer\n", preset_id);
                break;
            }

            // Parse and set notes in edit buffer
            uint8_t *note_data = &params[3];  // Note data starts at params[3]
            for (uint8_t i = 0; i < chunk_count; i++) {
                uint8_t note_idx = start_index + i;
                uint8_t offset = i * 3;  // 3 bytes per note

                // Extract note data (little-endian for packed_timing_vel)
                uint16_t packed_timing_vel = note_data[offset] | (note_data[offset + 1] << 8);
                uint8_t note_octave = note_data[offset + 2];

                // Set note data in edit buffer
                hid_edit_preset.notes[note_idx].packed_timing_vel = packed_timing_vel;
                hid_edit_preset.notes[note_idx].note_octave = note_octave;
            }

            params[0] = 0;  // Success
            params[1] = chunk_count;  // Echo back how many notes were written
            dprintf("ARP HID: SET_NOTES_CHUNK preset=%d start=%d count=%d\n",
                    preset_id, start_index, chunk_count);
            break;
        }

        case ARP_CMD_SET_MODE: {
            // Set arpeggiator mode only (without affecting active state)
            // params[0] = mode (0=SINGLE_NOTE, 1=CHORD_BASIC, 2=CHORD_ADVANCED)
            uint8_t mode = params[0];
            if (mode < ARPMODE_COUNT) {
                arp_set_mode((arp_mode_t)mode);
                params[0] = 0;  // Success
                dprintf("ARP HID: SET_MODE - mode=%d\n", mode);
            } else {
                params[0] = 1;  // Error: invalid mode
                dprintf("ARP HID: SET_MODE failed - invalid mode %d\n", mode);
            }
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
        data[3] >= 0xC0 && data[3] <= 0xCC) {

        dprintf("raw_hid_receive_kb: Arpeggiator packet detected, forwarding\n");
        arp_hid_receive(data, length);
        return;
    }

    // Check if this is a per-key actuation command (0xE0-0xE6)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] >= 0xE0 && data[3] <= 0xE6) {

        dprintf("raw_hid_receive_kb: Per-key actuation command detected (0x%02X)\n", data[3]);

        uint8_t cmd = data[3];
        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = cmd;

        switch (cmd) {
            case 0xE0:  // HID_CMD_SET_PER_KEY_ACTUATION
                // Format: [layer, key_index, settings...] at data[6] (Python puts data at byte 6)
                handle_set_per_key_actuation(&data[6]);
                response[4] = 0x01;  // Success
                break;

            case 0xE1:  // HID_CMD_GET_PER_KEY_ACTUATION
                // Format: [layer, key_index] at data[6]
                // Response: [status at 4] [8 data bytes at 5-12]
                response[4] = 0x01;  // Success status
                handle_get_per_key_actuation(&data[6], &response[5]);
                break;

            case 0xE2: {  // HID_CMD_GET_ALL_PER_KEY_ACTUATIONS
                // Bulk read: Returns all 70 keys for one layer in multiple packets
                // Request format: data[6] = layer number (0-11)
                // Response: 24 packets, each with up to 3 keys (8 bytes each)
                // Packet format: [header(4)] [status(1)] [layer(1)] [packet_num(1)] [total(1)] [key_data(24)]
                uint8_t layer = data[6];

                if (layer >= 12) {
                    response[4] = 0x00;  // Error - invalid layer
                    raw_hid_send(response, 32);
                    break;
                }

                // Send 24 packets (70 keys / 3 per packet = 24 packets, last has 1 key)
                const uint8_t KEYS_PER_PACKET = 3;
                const uint8_t TOTAL_PACKETS = 24;

                for (uint8_t pkt = 0; pkt < TOTAL_PACKETS; pkt++) {
                    uint8_t bulk_response[32] = {0};

                    // Header
                    bulk_response[0] = HID_MANUFACTURER_ID;
                    bulk_response[1] = HID_SUB_ID;
                    bulk_response[2] = HID_DEVICE_ID;
                    bulk_response[3] = 0xE2;

                    // Metadata
                    bulk_response[4] = 0x01;  // Success
                    bulk_response[5] = layer;
                    bulk_response[6] = pkt;
                    bulk_response[7] = TOTAL_PACKETS;

                    // Key data (up to 3 keys × 8 bytes = 24 bytes at offset 8)
                    uint8_t start_key = pkt * KEYS_PER_PACKET;
                    for (uint8_t k = 0; k < KEYS_PER_PACKET && (start_key + k) < 70; k++) {
                        uint8_t key_idx = start_key + k;
                        uint8_t offset = 8 + (k * 8);

                        bulk_response[offset + 0] = per_key_actuations[layer].keys[key_idx].actuation;
                        bulk_response[offset + 1] = per_key_actuations[layer].keys[key_idx].deadzone_top;
                        bulk_response[offset + 2] = per_key_actuations[layer].keys[key_idx].deadzone_bottom;
                        bulk_response[offset + 3] = per_key_actuations[layer].keys[key_idx].velocity_curve;
                        bulk_response[offset + 4] = per_key_actuations[layer].keys[key_idx].flags;
                        bulk_response[offset + 5] = per_key_actuations[layer].keys[key_idx].rapidfire_press_sens;
                        bulk_response[offset + 6] = per_key_actuations[layer].keys[key_idx].rapidfire_release_sens;
                        bulk_response[offset + 7] = (uint8_t)per_key_actuations[layer].keys[key_idx].rapidfire_velocity_mod;
                    }

                    raw_hid_send(bulk_response, 32);
                }
                return;  // Already sent responses, don't send again
            }

            case 0xE3:  // HID_CMD_RESET_PER_KEY_ACTUATIONS
                handle_reset_per_key_actuations_hid();
                response[4] = 0x01;  // Success
                break;

            case 0xE4:  // HID_CMD_SET_PER_KEY_MODE
                // Format: [mode_enabled, per_layer_enabled] at data[6]
                handle_set_per_key_mode(&data[6]);
                response[4] = 0x01;  // Success
                break;

            case 0xE5:  // HID_CMD_GET_PER_KEY_MODE
                handle_get_per_key_mode(&response[4]);
                break;

            case 0xE6:  // HID_CMD_COPY_LAYER_ACTUATIONS
                // Format: [source_layer, dest_layer] at data[6]
                handle_copy_layer_actuations(&data[6]);
                response[4] = 0x01;  // Success
                break;

            default:
                response[4] = 0x00;  // Error - unknown command
                break;
        }

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // =================================================================
    // LAYER ACTUATION COMMANDS (0xEB-0xEE)
    // Moved from 0xCA-0xCD to avoid conflict with arpeggiator commands
    // Using 0xEB-0xEE to avoid conflict with 0xE9 (EQ Curve Tuning)
    // =================================================================
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] >= 0xEB && data[3] <= 0xEE) {

        dprintf("raw_hid_receive_kb: Layer actuation command detected (0x%02X)\n", data[3]);

        uint8_t cmd = data[3];
        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = cmd;

        switch (cmd) {
            case 0xEB: {  // HID_CMD_GET_LAYER_ACTUATION (individual)
                // Format: data[6] = layer number (0-11)
                // Response: [status, normal, midi, velocity, vel_speed, flags,
                //            aftertouch_mode, aftertouch_cc, vibrato_sens, decay_lo, decay_hi]
                uint8_t layer = data[6];
                if (layer < 12) {
                    handle_get_layer_actuation(layer, &response[5]);
                    response[4] = 0x01;  // Success
                } else {
                    response[4] = 0x00;  // Error - invalid layer
                }
                break;
            }

            case 0xEC: {  // HID_CMD_SET_LAYER_ACTUATION
                // Format: data[6...] = layer settings
                handle_set_layer_actuation(&data[6]);
                response[4] = 0x01;  // Success
                break;
            }

            case 0xED: {  // HID_CMD_GET_ALL_LAYER_ACTUATIONS (bulk)
                // Response: 6 packets with all 12 layers (10 bytes each = 120 bytes total)
                // Each packet has 2 layers (20 bytes) to fit in 32-byte packets
                const uint8_t BYTES_PER_LAYER = 10;
                const uint8_t LAYERS_PER_PACKET = 2;  // 2 layers × 10 bytes = 20 bytes per packet
                const uint8_t TOTAL_PACKETS = 6;  // 12 layers / 2 = 6 packets

                for (uint8_t pkt = 0; pkt < TOTAL_PACKETS; pkt++) {
                    uint8_t bulk_response[32] = {0};

                    // Header
                    bulk_response[0] = HID_MANUFACTURER_ID;
                    bulk_response[1] = HID_SUB_ID;
                    bulk_response[2] = HID_DEVICE_ID;
                    bulk_response[3] = 0xED;

                    // Metadata
                    bulk_response[4] = 0x01;  // Success
                    bulk_response[5] = pkt;   // Packet number
                    bulk_response[6] = TOTAL_PACKETS;

                    // Layer data (2 layers per packet, 10 bytes each)
                    for (uint8_t l = 0; l < LAYERS_PER_PACKET; l++) {
                        uint8_t layer_idx = pkt * LAYERS_PER_PACKET + l;
                        if (layer_idx >= 12) break;

                        uint8_t offset = 7 + (l * BYTES_PER_LAYER);
                        handle_get_layer_actuation(layer_idx, &bulk_response[offset]);
                    }

                    raw_hid_send(bulk_response, 32);
                }
                return;  // Already sent responses
            }

            case 0xEE:  // HID_CMD_RESET_LAYER_ACTUATIONS
                handle_reset_layer_actuations();
                response[4] = 0x01;  // Success
                break;

            default:
                response[4] = 0x00;  // Error - unknown command
                break;
        }

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is an ADC matrix tester command (0xDF)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xDF) {

        dprintf("raw_hid_receive_kb: ADC Matrix command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xDF;

        uint8_t row = data[4];  // Row index from request

        // Validate row number
        if (row >= MATRIX_ROWS) {
            response[4] = row;
            response[5] = 0x00;  // Error - invalid row
            dprintf("ADC Matrix: Invalid row %d (max %d)\n", row, MATRIX_ROWS);
        } else {
            response[4] = row;
            response[5] = 0x01;  // Success

            // Get raw ADC values for each column in the row
            // Use 16-bit little-endian format for full 12-bit resolution (0-4095)
            // response[6+] = adc_low_0, adc_high_0, adc_low_1, adc_high_1, ...
            // With 32-byte packet and 6-byte header, we have 26 bytes = 13 columns max
            uint8_t max_cols = (MATRIX_COLS < 13) ? MATRIX_COLS : 13;
            for (uint8_t col = 0; col < max_cols; col++) {
                uint16_t adc_value = analog_matrix_get_raw_adc(row, col);
                response[6 + col * 2] = adc_value & 0xFF;           // Low byte
                response[6 + col * 2 + 1] = (adc_value >> 8) & 0xFF; // High byte
            }
        }

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is a Calibration Debug command (0xE8)
    // Returns calibration values (rest, bottom, raw ADC) for specific keys
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xE8) {

        dprintf("raw_hid_receive_kb: Calibration Debug command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xE8;

        // Request format: [header(4), _, num_keys, row0, col0, row1, col1, ...]
        uint8_t num_keys = data[6];

        // Max 4 keys per request (each key uses 6 bytes: rest(2) + bottom(2) + raw(2))
        if (num_keys > 4) {
            num_keys = 4;
        }

        response[4] = num_keys;
        response[5] = 0x01;  // Success

        // Get calibration for each requested key
        // Response format: [header(4), num_keys, status, rest_lo, rest_hi, bottom_lo, bottom_hi, raw_lo, raw_hi, ...]
        for (uint8_t i = 0; i < num_keys; i++) {
            uint8_t row = data[7 + i * 2];
            uint8_t col = data[8 + i * 2];

            // Use accessor functions from matrix.h
            uint16_t rest = analog_matrix_get_rest_adc(row, col);
            uint16_t bottom = analog_matrix_get_bottom_adc(row, col);
            uint16_t raw = analog_matrix_get_raw_adc(row, col);

            uint8_t offset = 6 + i * 6;
            response[offset + 0] = rest & 0xFF;
            response[offset + 1] = (rest >> 8) & 0xFF;
            response[offset + 2] = bottom & 0xFF;
            response[offset + 3] = (bottom >> 8) & 0xFF;
            response[offset + 4] = raw & 0xFF;
            response[offset + 5] = (raw >> 8) & 0xFF;
        }

        dprintf("Calibration Debug: %d keys queried\n", num_keys);

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is a Distance Matrix command (0xE7)
    // Returns key travel distance in 0.01mm units for specific keys
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xE7) {

        dprintf("raw_hid_receive_kb: Distance Matrix command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xE7;

        // Request format: [header(4), num_keys, row0, col0, row1, col1, ...]
        // Data starts at byte 6 after _create_hid_packet (bytes 4-5 are macro_num and status)
        uint8_t num_keys = data[6];

        // Validate number of keys (max 8 to fit in response)
        if (num_keys > 8) {
            num_keys = 8;
        }

        response[4] = num_keys;
        response[5] = 0x01;  // Success

        // Get distance for each requested key
        // Response format: [header(4), num_keys, status, dist_low_0, dist_high_0, ...]
        for (uint8_t i = 0; i < num_keys; i++) {
            uint8_t row = data[7 + i * 2];
            uint8_t col = data[8 + i * 2];

            uint16_t distance_hundredths = 0;

            if (row < MATRIX_ROWS && col < MATRIX_COLS) {
                // Get distance from firmware (0-255 scale)
                uint8_t distance_255 = analog_matrix_get_distance(row, col);

                // Convert to 0.01mm units (0-400 for 0-4.0mm)
                // 255 = 4.0mm = 400 hundredths, so: hundredths = (distance * 400) / 255
                distance_hundredths = ((uint32_t)distance_255 * 400) / 255;
            }

            // Store as 16-bit little-endian
            response[6 + i * 2] = distance_hundredths & 0xFF;           // Low byte
            response[6 + i * 2 + 1] = (distance_hundredths >> 8) & 0xFF; // High byte
        }

        dprintf("Distance Matrix: %d keys queried\n", num_keys);

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is an EQ Curve Tuning command (0xE9)
    // Sets EQ-style sensitivity curve parameters for real-time adjustment
    // Request format: [header(4), _, _,
    //                  range_low_lo, range_low_hi, range_high_lo, range_high_hi,
    //                  r0_b0, r0_b1, r0_b2, r0_b3, r0_b4,  (range 0: low rest)
    //                  r1_b0, r1_b1, r1_b2, r1_b3, r1_b4,  (range 1: mid rest)
    //                  r2_b0, r2_b1, r2_b2, r2_b3, r2_b4,  (range 2: high rest)
    //                  scale_0, scale_1, scale_2]          (range scale multipliers)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xE9) {

        dprintf("raw_hid_receive_kb: EQ Curve Tuning command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xE9;

        // Data starts at byte 6 after _create_hid_packet
        // Parse range boundaries (4 bytes)
        uint16_t range_low = data[6] | (data[7] << 8);
        uint16_t range_high = data[8] | (data[9] << 8);

        // Update the global EQ variables (defined in matrix.c)
        extern uint16_t eq_range_low;
        extern uint16_t eq_range_high;
        extern uint8_t eq_bands[3][5];
        extern uint8_t eq_range_scale[3];

        eq_range_low = range_low;
        eq_range_high = range_high;

        // Parse and set all 15 EQ bands (3 ranges × 5 bands)
        // Data layout: data[10-14] = range 0, data[15-19] = range 1, data[20-24] = range 2
        for (uint8_t range = 0; range < 3; range++) {
            for (uint8_t band = 0; band < 5; band++) {
                eq_bands[range][band] = data[10 + range * 5 + band];
            }
        }

        // Parse range scale multipliers (3 bytes at data[25-27])
        eq_range_scale[0] = data[25];
        eq_range_scale[1] = data[26];
        eq_range_scale[2] = data[27];

        response[4] = 0x01;  // Success

        dprintf("EQ Curve: low=%d, high=%d, scale=[%d,%d,%d]\n",
                range_low, range_high,
                eq_range_scale[0], eq_range_scale[1], eq_range_scale[2]);

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is an EQ Curve Save to EEPROM command (0xEA)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xEA) {

        dprintf("raw_hid_receive_kb: EQ Curve Save to EEPROM command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xEA;

        // Call the save function from matrix.c
        eq_curve_save_to_eeprom();

        // Also save keyboard settings (includes LUT correction strength)
        save_keyboard_settings();

        response[4] = 0x01;  // Success

        dprintf("EQ Curve and keyboard settings saved to EEPROM\n");

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is a null bind, toggle, or EEPROM diag command (0xF0-0xFB)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] >= 0xF0 && data[3] <= 0xFB) {

        dprintf("raw_hid_receive_kb: Command detected (0x%02X)\n", data[3]);

        uint8_t cmd = data[3];
        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = cmd;

        switch (cmd) {
            case HID_CMD_NULLBIND_GET_GROUP:  // 0xF0
                // Format: [group_num] at data[6] (Python _create_hid_packet puts data at byte 6)
                handle_nullbind_get_group(data[6], &response[4]);
                break;

            case HID_CMD_NULLBIND_SET_GROUP:  // 0xF1
                // Format: [group_num, behavior, key_count, keys[8], reserved[8]] at data[6]
                handle_nullbind_set_group(&data[6]);
                response[4] = 0;  // Success status
                break;

            case HID_CMD_NULLBIND_SAVE_EEPROM:  // 0xF2
                handle_nullbind_save_eeprom();
                response[4] = 0;  // Success status
                break;

            case HID_CMD_NULLBIND_LOAD_EEPROM:  // 0xF3
                handle_nullbind_load_eeprom();
                response[4] = 0;  // Success status
                break;

            case HID_CMD_NULLBIND_RESET_ALL:  // 0xF4
                handle_nullbind_reset_all();
                response[4] = 0;  // Success status
                break;

            // Toggle Keys commands (0xF5-0xF9)
            case HID_CMD_TOGGLE_GET_SLOT:  // 0xF5
                // Format: [slot_num] at data[6] (Python _create_hid_packet puts data at byte 6)
                handle_toggle_get_slot(data[6], &response[4]);
                break;

            case HID_CMD_TOGGLE_SET_SLOT:  // 0xF6
                // Format: [slot_num, target_keycode_low, target_keycode_high, reserved[2]] at data[6]
                handle_toggle_set_slot(&data[6]);
                response[4] = 0;  // Success status
                break;

            case HID_CMD_TOGGLE_SAVE_EEPROM:  // 0xF7
                handle_toggle_save_eeprom();
                response[4] = 0;  // Success status
                break;

            case HID_CMD_TOGGLE_LOAD_EEPROM:  // 0xF8
                handle_toggle_load_eeprom();
                response[4] = 0;  // Success status
                break;

            case HID_CMD_TOGGLE_RESET_ALL:  // 0xF9
                handle_toggle_reset_all();
                response[4] = 0;  // Success status
                break;

            case HID_CMD_EEPROM_DIAG_RUN:  // 0xFA
                handle_eeprom_diag_run(response);
                break;

            case HID_CMD_EEPROM_DIAG_GET:  // 0xFB
                handle_eeprom_diag_get(response);
                break;

            default:
                response[4] = 1;  // Error - unknown command
                break;
        }

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Not an arpeggiator command - ignore or handle other custom commands
    dprintf("raw_hid_receive_kb: Unhandled packet\n");
}
