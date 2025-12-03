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
            params[1] = MAX_ARP_PRESETS;
            params[2] = 8;  // Factory presets 0-7
            params[3] = 8;  // User presets start at slot 8
            dprintf("ARP HID: GET_INFO - %d presets total\n", MAX_ARP_PRESETS);
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
            // Get preset data (simplified - send basic info)
            // params[0] = preset_id
            // Returns: params[1-16] = name, params[17] = note_count, etc.
            uint8_t preset_id = params[0];
            if (preset_id >= MAX_ARP_PRESETS) {
                params[0] = 1;  // Error
                break;
            }

            arp_preset_t *preset = &arp_presets[preset_id];

            // Copy preset name (16 bytes)
            memcpy(&params[1], preset->name, ARP_PRESET_NAME_LENGTH);
            params[17] = preset->note_count;
            params[18] = (preset->pattern_length_64ths >> 8) & 0xFF;
            params[19] = preset->pattern_length_64ths & 0xFF;
            params[20] = preset->gate_length_percent;

            params[0] = 0;  // Success
            dprintf("ARP HID: GET_PRESET id=%d name=%s notes=%d\n",
                    preset_id, preset->name, preset->note_count);
            break;
        }

        case ARP_CMD_SET_PRESET: {
            // Set preset data (simplified - basic info only)
            // params[0] = preset_id
            // params[1-16] = name
            // params[17] = note_count
            // params[18-19] = pattern_length_64ths
            // params[20] = gate_length_percent
            uint8_t preset_id = params[0];

            if (preset_id < 8) {
                params[0] = 1;  // Error: cannot modify factory presets
                dprintf("ARP HID: SET_PRESET failed - cannot modify factory preset %d\n", preset_id);
                break;
            }

            if (preset_id >= MAX_ARP_PRESETS) {
                params[0] = 1;  // Error: invalid preset ID
                break;
            }

            arp_preset_t *preset = &arp_presets[preset_id];

            // Set basic preset info
            memcpy(preset->name, &params[1], ARP_PRESET_NAME_LENGTH);
            preset->note_count = params[17];
            preset->pattern_length_64ths = (params[18] << 8) | params[19];
            preset->gate_length_percent = params[20];
            preset->magic = ARP_PRESET_MAGIC;

            // Validate
            if (!arp_validate_preset(preset)) {
                params[0] = 1;  // Error: validation failed
                dprintf("ARP HID: SET_PRESET validation failed\n");
                break;
            }

            params[0] = 0;  // Success
            dprintf("ARP HID: SET_PRESET id=%d name=%s notes=%d\n",
                    preset_id, preset->name, preset->note_count);
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
    // Check if this is an arpeggiator command
    if (length >= 32 &&
        data[0] == HID_MANUFACTURER_ID &&
        data[1] == HID_SUB_ID &&
        data[2] == HID_DEVICE_ID &&
        data[3] >= 0xC0 && data[3] <= 0xC9) {

        dprintf("raw_hid_receive_kb: Arpeggiator packet detected, forwarding\n");
        arp_hid_receive(data, length);
        return;
    }

    // Not an arpeggiator command - ignore or handle other custom commands
    dprintf("raw_hid_receive_kb: Unhandled packet\n");
}
