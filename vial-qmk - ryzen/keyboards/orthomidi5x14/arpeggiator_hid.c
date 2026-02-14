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

            // Set magic at the correct struct offset based on preset type.
            // arp_preset_t has magic at offset 198 (after 64 notes),
            // seq_preset_t has magic at offset 390 (after 128 notes).
            // Since hid_edit_preset is seq_preset_t, we must cast for arp presets.
            if (hid_edit_preset.preset_type == PRESET_TYPE_ARPEGGIATOR) {
                ((arp_preset_t*)&hid_edit_preset)->magic = ARP_PRESET_MAGIC;
            } else {
                hid_edit_preset.magic = ARP_PRESET_MAGIC;
            }

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
            // params[0] = mode (0=SINGLE_SYNCED, 1=SINGLE_UNSYNCED, 2=CHORD_SYNCED, 3=CHORD_UNSYNCED, 4=CHORD_ADVANCED)
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

    // =========================================================================
    // GAMING/JOYSTICK COMMANDS (0xCE-0xD2)
    // These handle gamepad/joystick functionality for the keyboard
    // =========================================================================

    // Check if this is a gaming command (0xCE-0xD2)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] >= 0xCE && data[3] <= 0xD2) {

        uint8_t cmd = data[3];
        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = cmd;

        switch (cmd) {
            case 0xCE: {  // HID_CMD_GAMING_SET_MODE
                #ifdef JOYSTICK_ENABLE
                gaming_mode_active = data[6] != 0;
                gaming_settings.gaming_mode_enabled = gaming_mode_active;
                gaming_save_settings();
                response[5] = 0x00;  // Success
                dprintf("Gaming mode set to: %s\n", gaming_mode_active ? "ON" : "OFF");
                #else
                response[5] = 0x01;  // Error - joystick not enabled
                #endif
                break;
            }

            case 0xCF: {  // HID_CMD_GAMING_SET_KEY_MAP
                #ifdef JOYSTICK_ENABLE
                // Format: [header(6), control_id, row, col, enabled]
                uint8_t control_id = data[6];
                uint8_t row = data[7];
                uint8_t col = data[8];
                uint8_t enabled = data[9];

                gaming_key_map_t* target = NULL;

                // Map control_id to the correct structure member
                switch (control_id) {
                    case 0: target = &gaming_settings.ls_up; break;
                    case 1: target = &gaming_settings.ls_down; break;
                    case 2: target = &gaming_settings.ls_left; break;
                    case 3: target = &gaming_settings.ls_right; break;
                    case 4: target = &gaming_settings.rs_up; break;
                    case 5: target = &gaming_settings.rs_down; break;
                    case 6: target = &gaming_settings.rs_left; break;
                    case 7: target = &gaming_settings.rs_right; break;
                    case 8: target = &gaming_settings.lt; break;
                    case 9: target = &gaming_settings.rt; break;
                    default:
                        if (control_id >= 10 && control_id < 26) {
                            target = &gaming_settings.buttons[control_id - 10];
                        }
                        break;
                }

                if (target != NULL) {
                    target->row = row;
                    target->col = col;
                    target->enabled = enabled;
                    gaming_save_settings();
                    response[5] = 0x00;  // Success
                } else {
                    response[5] = 0x01;  // Error - invalid control_id
                }
                #else
                response[5] = 0x01;  // Error - joystick not enabled
                #endif
                break;
            }

            case 0xD0: {  // HID_CMD_GAMING_SET_ANALOG_CONFIG
                #ifdef JOYSTICK_ENABLE
                // Format: [header(6), ls_min, ls_max, rs_min, rs_max, trigger_min, trigger_max]
                gaming_settings.ls_config.min_travel_mm_x10 = data[6];
                gaming_settings.ls_config.max_travel_mm_x10 = data[7];
                gaming_settings.rs_config.min_travel_mm_x10 = data[8];
                gaming_settings.rs_config.max_travel_mm_x10 = data[9];
                gaming_settings.trigger_config.min_travel_mm_x10 = data[10];
                gaming_settings.trigger_config.max_travel_mm_x10 = data[11];
                gaming_save_settings();
                response[5] = 0x00;  // Success
                #else
                response[5] = 0x01;  // Error - joystick not enabled
                #endif
                break;
            }

            case 0xD1: {  // HID_CMD_GAMING_GET_SETTINGS
                #ifdef JOYSTICK_ENABLE
                response[5] = 0x00;  // Success
                response[6] = gaming_mode_active ? 1 : 0;
                response[7] = gaming_settings.ls_config.min_travel_mm_x10;
                response[8] = gaming_settings.ls_config.max_travel_mm_x10;
                response[9] = gaming_settings.rs_config.min_travel_mm_x10;
                response[10] = gaming_settings.rs_config.max_travel_mm_x10;
                response[11] = gaming_settings.trigger_config.min_travel_mm_x10;
                response[12] = gaming_settings.trigger_config.max_travel_mm_x10;
                #else
                response[5] = 0x01;  // Error - joystick not enabled
                #endif
                break;
            }

            case 0xD2: {  // HID_CMD_GAMING_RESET
                #ifdef JOYSTICK_ENABLE
                // Reset to defaults
                gaming_mode_active = false;
                gaming_settings.gaming_mode_enabled = false;
                gaming_settings.ls_config.min_travel_mm_x10 = 10;   // 1.0mm
                gaming_settings.ls_config.max_travel_mm_x10 = 20;   // 2.0mm
                gaming_settings.rs_config.min_travel_mm_x10 = 10;
                gaming_settings.rs_config.max_travel_mm_x10 = 20;
                gaming_settings.trigger_config.min_travel_mm_x10 = 10;
                gaming_settings.trigger_config.max_travel_mm_x10 = 20;

                // Clear all key mappings
                memset(&gaming_settings.ls_up, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.ls_down, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.ls_left, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.ls_right, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.rs_up, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.rs_down, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.rs_left, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.rs_right, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.lt, 0, sizeof(gaming_key_map_t));
                memset(&gaming_settings.rt, 0, sizeof(gaming_key_map_t));
                memset(gaming_settings.buttons, 0, sizeof(gaming_settings.buttons));

                gaming_save_settings();
                response[5] = 0x00;  // Success
                dprintf("Gaming settings reset to defaults\n");
                #else
                response[5] = 0x01;  // Error - joystick not enabled
                #endif
                break;
            }

            default:
                response[5] = 0x01;  // Error - unknown command
                break;
        }

        raw_hid_send(response, 32);
        return;
    }

    // =========================================================================
    // USER CURVE COMMANDS (0xD9-0xDC)
    // Save/load custom velocity curves (10 user slots, 4 points each)
    // =========================================================================

    // Check if this is a user curve command (0xD9-0xDC)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] >= 0xD9 && data[3] <= 0xDC) {

        uint8_t cmd = data[3];
        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = cmd;

        switch (cmd) {
            case 0xD9: {  // HID_CMD_VELOCITY_PRESET_SET
                // Set velocity preset using chunked transfer (4 chunks for zone-based presets)
                // Format: [header(6), slot, chunk_id, chunk_data...]
                // Chunk 0: name[16] + zone_flags[1] + reserved[1] = 18 bytes
                // Chunk 1: base zone settings (23 bytes)
                // Chunk 2: keysplit zone settings (23 bytes)
                // Chunk 3: triplesplit zone settings (23 bytes)
                uint8_t slot = data[6];
                uint8_t chunk_id = data[7];

                dprintf("VELOCITY_PRESET_SET: slot=%d, chunk=%d\n", slot, chunk_id);

                if (slot < 10) {
                    velocity_preset_t* preset = &user_curves.presets[slot];

                    if (chunk_id == 0) {
                        // Chunk 0: name (16 bytes) + zone_flags (1 byte) + reserved (1 byte)
                        memcpy(preset->name, &data[8], 16);
                        preset->name[15] = '\0';  // Ensure null termination
                        preset->zone_flags = data[24];
                        preset->reserved = data[25];
                        response[5] = 0x01;  // Success
                        dprintf("  Chunk 0: name='%s', zone_flags=0x%02X\n", preset->name, preset->zone_flags);
                    } else if (chunk_id >= 1 && chunk_id <= 3) {
                        // Chunk 1-3: zone settings (base, keysplit, triplesplit)
                        zone_settings_t* zone;
                        if (chunk_id == 1) zone = &preset->base;
                        else if (chunk_id == 2) zone = &preset->keysplit;
                        else zone = &preset->triplesplit;

                        // Deserialize zone settings (23 bytes)
                        memcpy(zone->points, &data[8], 8);  // 8 bytes
                        zone->velocity_min = data[16];
                        zone->velocity_max = data[17];
                        zone->slow_press_time = data[18] | (data[19] << 8);
                        zone->fast_press_time = data[20] | (data[21] << 8);
                        zone->aftertouch_mode = data[22];
                        zone->aftertouch_cc = data[23];
                        zone->vibrato_sensitivity = data[24];
                        zone->vibrato_decay = data[25] | (data[26] << 8);
                        zone->flags = data[27];
                        zone->actuation_point = data[28];
                        zone->speed_peak_ratio = data[29];
                        zone->retrigger_distance = data[30];

                        // Save to EEPROM after last chunk (chunk 3)
                        if (chunk_id == 3) {
                            user_curves_save();
                            dprintf("  Saved preset to EEPROM\n");
                        }
                        response[5] = 0x01;  // Success
                        dprintf("  Chunk %d: zone vel=%d-%d, time=%d-%dms\n",
                            chunk_id, zone->velocity_min, zone->velocity_max,
                            zone->fast_press_time, zone->slow_press_time);
                    } else {
                        response[5] = 0x00;  // Error - invalid chunk
                    }
                    response[4] = 0x00;
                } else {
                    response[4] = 0x00;
                    response[5] = 0x00;  // Error - invalid slot
                }
                break;
            }

            case 0xDA: {  // HID_CMD_VELOCITY_PRESET_GET
                // Get velocity preset - sends 4 response packets (zone-based format)
                // Request format: [header(6), slot]
                // Response: 4 packets with all preset data
                uint8_t slot = data[6];

                dprintf("VELOCITY_PRESET_GET: slot=%d\n", slot);

                if (slot < 10) {
                    velocity_preset_t* preset = &user_curves.presets[slot];

                    // Send Chunk 0: name + zone_flags
                    uint8_t chunk0[32] = {0};
                    chunk0[0] = HID_MANUFACTURER_ID;
                    chunk0[1] = HID_SUB_ID;
                    chunk0[2] = HID_DEVICE_ID;
                    chunk0[3] = 0xDA;
                    chunk0[4] = 0x00;  // Reserved
                    chunk0[5] = 0x01;  // Success
                    chunk0[6] = slot;
                    chunk0[7] = 0;     // Chunk ID 0
                    memcpy(&chunk0[8], preset->name, 16);
                    chunk0[24] = preset->zone_flags;
                    chunk0[25] = preset->reserved;
                    raw_hid_send(chunk0, 32);

                    // Helper macro for serializing zone settings
                    #define SEND_ZONE_CHUNK(chunk_id, zone_ptr) do { \
                        uint8_t chunk[32] = {0}; \
                        chunk[0] = HID_MANUFACTURER_ID; \
                        chunk[1] = HID_SUB_ID; \
                        chunk[2] = HID_DEVICE_ID; \
                        chunk[3] = 0xDA; \
                        chunk[4] = 0x00; \
                        chunk[5] = 0x01; \
                        chunk[6] = slot; \
                        chunk[7] = chunk_id; \
                        memcpy(&chunk[8], (zone_ptr)->points, 8); \
                        chunk[16] = (zone_ptr)->velocity_min; \
                        chunk[17] = (zone_ptr)->velocity_max; \
                        chunk[18] = (zone_ptr)->slow_press_time & 0xFF; \
                        chunk[19] = ((zone_ptr)->slow_press_time >> 8) & 0xFF; \
                        chunk[20] = (zone_ptr)->fast_press_time & 0xFF; \
                        chunk[21] = ((zone_ptr)->fast_press_time >> 8) & 0xFF; \
                        chunk[22] = (zone_ptr)->aftertouch_mode; \
                        chunk[23] = (zone_ptr)->aftertouch_cc; \
                        chunk[24] = (zone_ptr)->vibrato_sensitivity; \
                        chunk[25] = (zone_ptr)->vibrato_decay & 0xFF; \
                        chunk[26] = ((zone_ptr)->vibrato_decay >> 8) & 0xFF; \
                        chunk[27] = (zone_ptr)->flags; \
                        chunk[28] = (zone_ptr)->actuation_point; \
                        chunk[29] = (zone_ptr)->speed_peak_ratio; \
                        chunk[30] = (zone_ptr)->retrigger_distance; \
                        raw_hid_send(chunk, 32); \
                    } while(0)

                    // Send Chunk 1: base zone
                    SEND_ZONE_CHUNK(1, &preset->base);

                    // Send Chunk 2: keysplit zone
                    SEND_ZONE_CHUNK(2, &preset->keysplit);

                    // Send Chunk 3: triplesplit zone
                    SEND_ZONE_CHUNK(3, &preset->triplesplit);

                    #undef SEND_ZONE_CHUNK

                    dprintf("  Sent 4 chunks for preset '%s'\n", preset->name);
                    return;  // Already sent response packets
                } else {
                    response[4] = 0x00;
                    response[5] = 0x00;  // Error - invalid slot
                }
                break;
            }

            case 0xDB: {  // HID_CMD_VELOCITY_PRESET_GET_ALL_NAMES
                // Get all preset names (truncated to 2 chars each to fit in one packet)
                dprintf("VELOCITY_PRESET_GET_ALL_NAMES\n");

                response[4] = 0x00;  // Reserved
                response[5] = 0x01;  // Success

                // Return 10 names truncated to 2 chars each (20 bytes) at response[6]
                for (int i = 0; i < 10; i++) {
                    response[6 + i*2] = user_curves.presets[i].name[0];
                    response[6 + i*2 + 1] = user_curves.presets[i].name[1];
                }
                break;
            }

            case 0xDC: {  // HID_CMD_VELOCITY_PRESET_RESET
                // Reset all velocity presets to defaults
                dprintf("VELOCITY_PRESET_RESET\n");

                user_curves_reset();

                response[4] = 0x00;  // Reserved
                response[5] = 0x01;  // Success
                break;
            }

            case 0xDD: {  // HID_CMD_VELOCITY_PRESET_DEBUG_TOGGLE
                // Toggle velocity preset debug display on OLED
                extern bool velocity_preset_debug_mode;
                velocity_preset_debug_mode = !velocity_preset_debug_mode;
                dprintf("VELOCITY_PRESET_DEBUG: %s\n", velocity_preset_debug_mode ? "ON" : "OFF");

                response[4] = 0x00;  // Reserved
                response[5] = 0x01;  // Success
                response[6] = velocity_preset_debug_mode ? 0x01 : 0x00;  // Current state
                break;
            }

            default:
                response[4] = 0x00;
                response[5] = 0x00;  // Error - unknown command
                break;
        }

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

    // Check if this is a SET_KEYBOARD_PARAM_SINGLE command (0xE8)
    // Sets individual keyboard parameters (velocity curve, velocity mode, aftertouch, etc.)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xE8) {

        dprintf("raw_hid_receive_kb: SET_KEYBOARD_PARAM_SINGLE command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xE8;

        // Format: [header(6), param_id, value_byte(s)...]
        // For 16-bit params: [header(6), param_id, low_byte, high_byte]
        uint8_t param_id = data[6];
        uint8_t value8 = data[7];
        uint16_t value16 = data[7] | (data[8] << 8);  // Little-endian for 16-bit params
        bool settings_changed = false;
        bool success = true;

        switch (param_id) {
            // Velocity curve and range parameters (update keyboard_settings)
            case 4:  // PARAM_HE_VELOCITY_CURVE (0-16)
                keyboard_settings.he_velocity_curve = value8;
                he_velocity_curve = value8;  // Also update global for OLED display
                // Apply all preset settings (factory curves reset to defaults,
                // user curves apply their stored settings)
                velocity_preset_apply(value8);
                settings_changed = true;
                dprintf("SET param 4 (velocity_curve) = %d\n", value8);
                break;
            case 5:  // PARAM_HE_VELOCITY_MIN (1-127)
                keyboard_settings.he_velocity_min = value8;
                he_velocity_min = value8;
                settings_changed = true;
                dprintf("SET param 5 (velocity_min) = %d\n", value8);
                break;
            case 6:  // PARAM_HE_VELOCITY_MAX (1-127)
                keyboard_settings.he_velocity_max = value8;
                he_velocity_max = value8;
                settings_changed = true;
                dprintf("SET param 6 (velocity_max) = %d\n", value8);
                break;

            // Global MIDI settings (update global variables)
            case 13:  // PARAM_VELOCITY_MODE - DEPRECATED, fixed at 3 (Speed+Peak)
                // Ignore velocity_mode changes - always use Speed+Peak mode
                dprintf("SET param 13 (velocity_mode) = %d [IGNORED - fixed at mode 3]\n", value8);
                break;
            case 14:  // PARAM_AFTERTOUCH_MODE (0-4)
                aftertouch_mode = value8;
                settings_changed = true;
                dprintf("SET param 14 (aftertouch_mode) = %d\n", value8);
                break;
            case 39:  // PARAM_AFTERTOUCH_CC (0-127, 255=off)
                aftertouch_cc = value8;
                settings_changed = true;
                dprintf("SET param 39 (aftertouch_cc) = %d\n", value8);
                break;
            case 40:  // PARAM_VIBRATO_SENSITIVITY (50-200)
                vibrato_sensitivity = value8;
                settings_changed = true;
                dprintf("SET param 40 (vibrato_sensitivity) = %d\n", value8);
                break;
            case 41:  // PARAM_VIBRATO_DECAY_TIME (0-2000ms, 16-bit)
                vibrato_decay_time = value16;
                settings_changed = true;
                dprintf("SET param 41 (vibrato_decay_time) = %d\n", value16);
                break;
            case 42:  // PARAM_MIN_PRESS_TIME (50-500ms, 16-bit)
                min_press_time = value16;
                keyboard_settings.min_press_time = value16;
                settings_changed = true;
                dprintf("SET param 42 (min_press_time) = %d\n", value16);
                break;
            case 43:  // PARAM_MAX_PRESS_TIME (5-100ms, 16-bit)
                max_press_time = value16;
                keyboard_settings.max_press_time = value16;
                settings_changed = true;
                dprintf("SET param 43 (max_press_time) = %d\n", value16);
                break;
            case 45:  // PARAM_MACRO_OVERRIDE_LIVE_NOTES
                macro_override_live_notes = (value8 != 0);
                keyboard_settings.macro_override_live_notes = macro_override_live_notes;
                dprintf("SET param 45 (macro_override_live_notes) = %d\n", value8);
                break;
            case 46:  // PARAM_SMARTCHORD_MODE (0=Hold, 1=Toggle)
                smartchord_mode = value8;
                keyboard_settings.smartchord_mode = smartchord_mode;
                dprintf("SET param 46 (smartchord_mode) = %d\n", value8);
                break;
            case 47:  // PARAM_BASE_SMARTCHORD_IGNORE (0=Allow, 1=Ignore)
                base_smartchord_ignore = value8;
                keyboard_settings.base_smartchord_ignore = base_smartchord_ignore;
                dprintf("SET param 47 (base_smartchord_ignore) = %d\n", value8);
                break;
            case 48:  // PARAM_KEYSPLIT_SMARTCHORD_IGNORE (0=Allow, 1=Ignore)
                keysplit_smartchord_ignore = value8;
                keyboard_settings.keysplit_smartchord_ignore = keysplit_smartchord_ignore;
                dprintf("SET param 48 (keysplit_smartchord_ignore) = %d\n", value8);
                break;
            case 49:  // PARAM_TRIPLESPLIT_SMARTCHORD_IGNORE (0=Allow, 1=Ignore)
                triplesplit_smartchord_ignore = value8;
                keyboard_settings.triplesplit_smartchord_ignore = triplesplit_smartchord_ignore;
                dprintf("SET param 49 (triplesplit_smartchord_ignore) = %d\n", value8);
                break;
            default:
                success = false;
                dprintf("SET param %d: UNKNOWN param_id\n", param_id);
                break;
        }

        // Force refresh active_settings so changes take effect immediately
        if (settings_changed) {
            analog_matrix_refresh_settings();
        }

        // Response format: [header(4), status, param_id, value8]
        response[4] = 0x00;  // Reserved
        response[5] = success ? 0x01 : 0x00;  // Status
        response[6] = param_id;
        response[7] = value8;

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is a Calibration Debug command (0xD5) - moved from 0xE8 to avoid collision
    // with SET_KEYBOARD_PARAM_SINGLE which also uses 0xE8
    // Returns calibration values (rest, bottom, raw ADC) for specific keys
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xD5) {

        dprintf("raw_hid_receive_kb: Calibration Debug command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xD5;

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

    // Check if this is a Velocity Matrix Poll command (0xE5)
    // Returns velocity (0-127, after curve) and travel time (ms) for specific keys
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xD3) {

        dprintf("raw_hid_receive_kb: Velocity Matrix Poll command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xD3;

        // Request format: [header(4), _, num_keys, row0, col0, row1, col1, ...]
        uint8_t num_keys = data[6];

        // Validate number of keys (max 6 to fit in response: 6 + 6*4 = 30 bytes)
        // Each key: velocity(1) + travel_time(2) + raw_velocity(1) = 4 bytes
        if (num_keys > 6) {
            num_keys = 6;
        }

        response[4] = num_keys;
        response[5] = 0x01;  // Success

        // Get velocity data for each requested key
        for (uint8_t i = 0; i < num_keys; i++) {
            uint8_t row = data[7 + i * 2];
            uint8_t col = data[8 + i * 2];

            uint8_t final_velocity = 0;
            uint16_t travel_time_ms = 0;
            uint8_t raw_velocity = 0;

            if (row < MATRIX_ROWS && col < MATRIX_COLS) {
                // Get the ACTUAL final velocity that was sent with the MIDI note
                // This shows the real velocity assigned to the note, not the current position
                final_velocity = analog_matrix_get_final_velocity(row, col);
                // Get travel time in milliseconds
                travel_time_ms = analog_matrix_get_travel_time_ms(row, col);
                // Get raw velocity (before curve)
                raw_velocity = analog_matrix_get_velocity_raw(row, col);
            }

            uint8_t offset = 6 + i * 4;
            response[offset + 0] = final_velocity;
            response[offset + 1] = travel_time_ms & 0xFF;         // Low byte
            response[offset + 2] = (travel_time_ms >> 8) & 0xFF;  // High byte
            response[offset + 3] = raw_velocity;
        }

        dprintf("Velocity Matrix: %d keys queried\n", num_keys);

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is a Global Velocity Time Settings command (0xD4)
    // Get or Set the global min_press_time and max_press_time settings
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xD4) {

        dprintf("raw_hid_receive_kb: Global Velocity Time Settings command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xD4;

        // Request format: [header(4), _, sub_cmd, min_time_lo, min_time_hi, max_time_lo, max_time_hi]
        // sub_cmd: 0 = GET, 1 = SET, 2 = SAVE to EEPROM
        uint8_t sub_cmd = data[6];

        if (sub_cmd == 0) {
            // GET: Return current settings
            response[4] = 0x01;  // Success
            response[5] = min_press_time & 0xFF;
            response[6] = (min_press_time >> 8) & 0xFF;
            response[7] = max_press_time & 0xFF;
            response[8] = (max_press_time >> 8) & 0xFF;
            dprintf("GET Velocity Time: min=%d, max=%d\n", min_press_time, max_press_time);
        } else if (sub_cmd == 1) {
            // SET: Update settings from request
            uint16_t new_min = data[7] | (data[8] << 8);
            uint16_t new_max = data[9] | (data[10] << 8);

            // Validate ranges (50-500 for min, 1-100 for max)
            if (new_min >= 50 && new_min <= 500 && new_max >= 1 && new_max <= 100 && new_max < new_min) {
                min_press_time = new_min;
                max_press_time = new_max;
                keyboard_settings.min_press_time = min_press_time;
                keyboard_settings.max_press_time = max_press_time;
                response[4] = 0x01;  // Success
                dprintf("SET Velocity Time: min=%d, max=%d\n", min_press_time, max_press_time);
            } else {
                response[4] = 0x00;  // Error - invalid values
                dprintf("SET Velocity Time: INVALID min=%d, max=%d\n", new_min, new_max);
            }
            // Return current values
            response[5] = min_press_time & 0xFF;
            response[6] = (min_press_time >> 8) & 0xFF;
            response[7] = max_press_time & 0xFF;
            response[8] = (max_press_time >> 8) & 0xFF;
        } else if (sub_cmd == 2) {
            // SAVE: Save current settings to EEPROM (via keyboard_settings)
            save_keyboard_settings();
            response[4] = 0x01;  // Success
            response[5] = min_press_time & 0xFF;
            response[6] = (min_press_time >> 8) & 0xFF;
            response[7] = max_press_time & 0xFF;
            response[8] = (max_press_time >> 8) & 0xFF;
            dprintf("SAVE Velocity Time to EEPROM: min=%d, max=%d\n", min_press_time, max_press_time);
        } else {
            response[4] = 0x00;  // Error - unknown sub-command
        }

        // Send response
        raw_hid_send(response, 32);
        return;
    }

    // Check if this is a GET EQ Curve Settings command (0xEF)
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] == 0xEF) {

        dprintf("raw_hid_receive_kb: GET EQ Curve Settings command detected\n");

        uint8_t response[32] = {0};

        // Copy header to response
        response[0] = HID_MANUFACTURER_ID;
        response[1] = HID_SUB_ID;
        response[2] = HID_DEVICE_ID;
        response[3] = 0xEF;

        // Get the global EQ variables (defined in matrix.c)
        extern uint16_t eq_range_low;
        extern uint16_t eq_range_high;
        extern uint8_t eq_bands[3][5];
        extern uint8_t eq_range_scale[3];
        extern uint8_t lut_correction_strength;

        // Pack range boundaries (4 bytes)
        response[4] = eq_range_low & 0xFF;
        response[5] = (eq_range_low >> 8) & 0xFF;
        response[6] = eq_range_high & 0xFF;
        response[7] = (eq_range_high >> 8) & 0xFF;

        // Pack all 15 EQ bands (3 ranges × 5 bands)
        for (uint8_t range = 0; range < 3; range++) {
            for (uint8_t band = 0; band < 5; band++) {
                response[8 + range * 5 + band] = eq_bands[range][band];
            }
        }

        // Pack range scale multipliers (3 bytes at response[23-25])
        response[23] = eq_range_scale[0];
        response[24] = eq_range_scale[1];
        response[25] = eq_range_scale[2];

        // Pack LUT correction strength (1 byte at response[26])
        response[26] = lut_correction_strength;

        dprintf("GET EQ: low=%d, high=%d, lut=%d\n", eq_range_low, eq_range_high, lut_correction_strength);

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
