/* Copyright 2020 Ilya Zhuravlev
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "vial.h"

#include <string.h>

// TROUBLESHOOTING: Conditionally include keyboard-specific headers
// These should be moved to keyboard-level code, not in quantum/vial.c
#ifdef ORTHOMIDI_CUSTOM_HID_ENABLE
#include "orthomidi5x14.h"
#include "process_midi.h"
#include "process_dynamic_macro.h"  // For velocity_mode, min_press_time, etc. extern declarations
#include "matrix.h"                 // For analog_matrix_refresh_settings()
#include "../keyboards/orthomidi5x14/per_key_rgb.h"
#endif

#include "dynamic_keymap.h"
#include "quantum.h"
#include "vial_generated_keyboard_definition.h"

#include "vial_ensure_keycode.h"

#define VIAL_UNLOCK_COUNTER_MAX 50
#define vial_layer_rgb_save         0xBC
#define vial_layer_rgb_load         0xBD  
#define vial_layer_rgb_enable       0xBE
#define vial_layer_rgb_get_status   0xBF
#define vial_custom_anim_set_param      0xC0
#define vial_custom_anim_get_param      0xC1  
#define vial_custom_anim_set_all        0xC2
#define vial_custom_anim_get_all        0xC3
#define vial_custom_anim_save           0xC4
#define vial_custom_anim_load           0xC5
#define vial_custom_anim_reset_slot     0xC6
#define vial_custom_anim_get_status     0xC7
#define vial_custom_rescan_led     0xC8
#define vial_custom_anim_get_ram_state    0xC9  // New command

// Per-Key RGB Commands (0xD3-0xD8)
#define vial_per_key_get_palette        0xD3
#define vial_per_key_set_palette_color  0xD4
#define vial_per_key_get_preset_data    0xD5
#define vial_per_key_set_led_color      0xD6
#define vial_per_key_save               0xD7
#define vial_per_key_load               0xD8

// User Curve Commands (0xD9-0xDE)
#define HID_CMD_USER_CURVE_SET          0xD9  // Set user curve points
#define HID_CMD_USER_CURVE_GET          0xDA  // Get user curve
#define HID_CMD_USER_CURVE_GET_ALL      0xDB  // Get all user curve names
#define HID_CMD_USER_CURVE_RESET        0xDC  // Reset user curves
#define HID_CMD_GAMING_SET_RESPONSE     0xDD  // Set gamepad response settings
#define HID_CMD_GAMING_GET_RESPONSE     0xDE  // Get gamepad response settings

// ADC Matrix Tester Command (0xDF)
#define HID_CMD_GET_ADC_MATRIX          0xDF  // Get ADC values for matrix row

// Distance Matrix Command (0xE7)
#define HID_CMD_GET_DISTANCE_MATRIX     0xE7  // Get distance (mm) for specific keys

#define HID_CMD_SET_LOOP_CONFIG 0xB0
#define HID_CMD_SET_MAIN_LOOP_CCS 0xB1  
#define HID_CMD_SET_OVERDUB_CCS 0xB2
#define HID_CMD_SET_NAVIGATION_CONFIG 0xB3
#define HID_CMD_GET_ALL_CONFIG 0xB4
#define HID_CMD_RESET_LOOP_CONFIG 0xB5

// MIDIswitch Commands (0xB6-0xBB, 0xE8)
#define HID_CMD_SET_KEYBOARD_CONFIG 0xB6
#define HID_CMD_GET_KEYBOARD_CONFIG 0xB7
#define HID_CMD_RESET_KEYBOARD_CONFIG 0xB8
#define HID_CMD_SAVE_KEYBOARD_SLOT 0xB9
#define HID_CMD_LOAD_KEYBOARD_SLOT 0xBA
#define HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED 0xBB
#define HID_CMD_SET_KEYBOARD_PARAM_SINGLE 0xE8  // Changed from 0xBD (collision with vial_layer_rgb_load)

// Per-Key Actuation Commands (0xE0-0xE6)
#define HID_CMD_SET_PER_KEY_ACTUATION       0xE0
#define HID_CMD_GET_PER_KEY_ACTUATION       0xE1
#define HID_CMD_GET_ALL_PER_KEY_ACTUATIONS  0xE2
#define HID_CMD_RESET_PER_KEY_ACTUATIONS    0xE3
#define HID_CMD_SET_PER_KEY_MODE            0xE4
#define HID_CMD_GET_PER_KEY_MODE            0xE5
#define HID_CMD_COPY_LAYER_ACTUATIONS       0xE6

#ifdef VIAL_INSECURE
#pragma message "Building Vial-enabled firmware in insecure mode."
int vial_unlocked = 1;
#else
int vial_unlocked = 0;
#endif
int vial_unlock_in_progress = 0;
static int vial_unlock_counter = 0;
static uint16_t vial_unlock_timer;

#ifndef VIAL_INSECURE
static uint8_t vial_unlock_combo_rows[] = VIAL_UNLOCK_COMBO_ROWS;
static uint8_t vial_unlock_combo_cols[] = VIAL_UNLOCK_COMBO_COLS;
#define VIAL_UNLOCK_NUM_KEYS (sizeof(vial_unlock_combo_rows)/sizeof(vial_unlock_combo_rows[0]))
_Static_assert(VIAL_UNLOCK_NUM_KEYS < 15, "Max 15 unlock keys");
_Static_assert(sizeof(vial_unlock_combo_rows) == sizeof(vial_unlock_combo_cols), "The number of unlock cols and rows should be the same");
#endif

#include "qmk_settings.h"

#ifdef VIAL_TAP_DANCE_ENABLE
static void reload_tap_dance(void);
#endif

#ifdef VIAL_COMBO_ENABLE
static void reload_combo(void);
#endif

#ifdef VIAL_KEY_OVERRIDE_ENABLE
static void reload_key_override(void);
#endif

void vial_init(void) {
#ifdef VIAL_TAP_DANCE_ENABLE
    reload_tap_dance();
#endif
#ifdef VIAL_COMBO_ENABLE
    reload_combo();
#endif
#ifdef VIAL_KEY_OVERRIDE_ENABLE
    reload_key_override();
#endif
}

__attribute__((unused)) static uint16_t vial_keycode_firewall(uint16_t in) {
    if (in == QK_BOOT && !vial_unlocked)
        return 0;
    return in;
}

void vial_handle_cmd(uint8_t *msg, uint8_t length) {
    /* All packets must be fixed 32 bytes */
    if (length != VIAL_RAW_EPSIZE)
        return;

    /* msg[0] is 0xFE -- prefix vial magic */
    switch (msg[1]) {
        /* Get keyboard ID and Vial protocol version */
        case vial_get_keyboard_id: {
            uint8_t keyboard_uid[] = VIAL_KEYBOARD_UID;

            memset(msg, 0, length);
            msg[0] = VIAL_PROTOCOL_VERSION & 0xFF;
            msg[1] = (VIAL_PROTOCOL_VERSION >> 8) & 0xFF;
            msg[2] = (VIAL_PROTOCOL_VERSION >> 16) & 0xFF;
            msg[3] = (VIAL_PROTOCOL_VERSION >> 24) & 0xFF;
            memcpy(&msg[4], keyboard_uid, 8);
#ifdef VIALRGB_ENABLE
            msg[12] = 1; /* bit flag to indicate vialrgb is supported - so third-party apps don't have to query json */
#endif
            break;
        }
        /* Retrieve keyboard definition size */
        case vial_get_size: {
            uint32_t sz = sizeof(keyboard_definition);
            msg[0] = sz & 0xFF;
            msg[1] = (sz >> 8) & 0xFF;
            msg[2] = (sz >> 16) & 0xFF;
            msg[3] = (sz >> 24) & 0xFF;
            break;
        }
        /* Retrieve 32-bytes block of the definition, page ID encoded within 2 bytes */
        case vial_get_def: {
            uint32_t page = msg[2] + (msg[3] << 8);
            uint32_t start = page * VIAL_RAW_EPSIZE;
            uint32_t end = start + VIAL_RAW_EPSIZE;
            if (end < start || start >= sizeof(keyboard_definition))
                return;
            if (end > sizeof(keyboard_definition))
                end = sizeof(keyboard_definition);
            memcpy_P(msg, &keyboard_definition[start], end - start);
            break;
        }
#ifdef ENCODER_MAP_ENABLE
        case vial_get_encoder: {
            uint8_t layer = msg[2];
            uint8_t idx = msg[3];
            uint16_t keycode = dynamic_keymap_get_encoder(layer, idx, 0);
            msg[0]  = keycode >> 8;
            msg[1]  = keycode & 0xFF;
            keycode = dynamic_keymap_get_encoder(layer, idx, 1);
            msg[2] = keycode >> 8;
            msg[3] = keycode & 0xFF;
            break;
        }
        case vial_set_encoder: {
            dynamic_keymap_set_encoder(msg[2], msg[3], msg[4], vial_keycode_firewall((msg[5] << 8) | msg[6]));
            break;
        }
#endif
        case vial_get_unlock_status: {
            /* Reset message to all FF's */
            memset(msg, 0xFF, length);
            /* First byte of message contains the status: whether board is unlocked */
            msg[0] = vial_unlocked;
            /* Second byte is whether unlock is in progress */
            msg[1] = vial_unlock_in_progress;
#ifndef VIAL_INSECURE
            /* Rest of the message are keys in the matrix that should be held to unlock the board */
            for (size_t i = 0; i < VIAL_UNLOCK_NUM_KEYS; ++i) {
                msg[2 + i * 2] = vial_unlock_combo_rows[i];
                msg[2 + i * 2 + 1] = vial_unlock_combo_cols[i];
            }
#endif
            break;
        }
        case vial_unlock_start: {
            vial_unlock_in_progress = 1;
            vial_unlock_counter = VIAL_UNLOCK_COUNTER_MAX;
            vial_unlock_timer = timer_read();
            break;
        }
        case vial_unlock_poll: {
#ifndef VIAL_INSECURE
            if (vial_unlock_in_progress) {
                int holding = 1;
                for (size_t i = 0; i < VIAL_UNLOCK_NUM_KEYS; ++i)
                    holding &= matrix_is_on(vial_unlock_combo_rows[i], vial_unlock_combo_cols[i]);

                if (timer_elapsed(vial_unlock_timer) > 100 && holding) {
                    vial_unlock_timer = timer_read();

                    vial_unlock_counter--;
                    if (vial_unlock_counter == 0) {
                        /* ok unlock succeeded */
                        vial_unlock_in_progress = 0;
                        vial_unlocked = 1;
                    }
                } else {
                    vial_unlock_counter = VIAL_UNLOCK_COUNTER_MAX;
                }
            }
#endif
            msg[0] = vial_unlocked;
            msg[1] = vial_unlock_in_progress;
            msg[2] = vial_unlock_counter;
            break;
        }
        case vial_lock: {
#ifndef VIAL_INSECURE
            vial_unlocked = 0;
#endif
            break;
        }
        case vial_qmk_settings_query: {
#ifdef QMK_SETTINGS
            uint16_t qsid_greater_than = msg[2] | (msg[3] << 8);
            qmk_settings_query(qsid_greater_than, msg, length);
#else
            memset(msg, 0xFF, length); /* indicate that we don't support any qsid */
#endif
            break;
        }
#ifdef QMK_SETTINGS
        case vial_qmk_settings_get: {
            uint16_t qsid = msg[2] | (msg[3] << 8);
            msg[0] = qmk_settings_get(qsid, &msg[1], length - 1);

            break;
        }
        case vial_qmk_settings_set: {
            uint16_t qsid = msg[2] | (msg[3] << 8);
            msg[0] = qmk_settings_set(qsid, &msg[4], length - 4);

            break;
        }
        case vial_qmk_settings_reset: {
            qmk_settings_reset();
            break;
        }
#endif

#ifdef ORTHOMIDI_CUSTOM_HID_ENABLE
        // ============================================================================
        // ORTHOMIDI CUSTOM HID HANDLERS (Layer RGB, Custom Animations, Actuation, etc.)
        // These handlers require keyboard-specific code and are disabled by default
        // for troubleshooting. Enable with ORTHOMIDI_CUSTOM_HID_ENABLE=yes in rules.mk
        // ============================================================================

        // ADD YOUR LAYER RGB CASES HERE
        case vial_layer_rgb_save: {  // 0xBC
            uint8_t layer = msg[2];
            if (layer < NUM_LAYERS) {
                save_current_rgb_settings(layer);
                msg[0] = 0x01; // Success response
            } else {
                msg[0] = 0x00; // Error - invalid layer
            }
            break;
        }

        case vial_layer_rgb_load: {  // 0xBD
            uint8_t layer = msg[2];
            if (layer < NUM_LAYERS) {
                apply_layer_rgb_settings(layer);
                msg[0] = 0x01; // Success response
            } else {
                msg[0] = 0x00; // Error - invalid layer
            }
            break;
        }

		case vial_layer_rgb_enable: {  // 0xBE
			uint8_t enable = msg[2];
			bool new_value = (enable != 0);
			// This function sets the global variable AND saves to EEPROM slot 0
			update_layer_animations_setting_slot0_direct(new_value);
			
			msg[0] = 0x01; // Success response
			break;
		}

        case vial_layer_rgb_get_status: {  // 0xBF
            msg[0] = custom_layer_animations_enabled ? 0x01 : 0x00;
            msg[1] = NUM_LAYERS;
            // msg[2-31] reserved for future use, already zeroed by memset if needed
            break;
        }
		
		case vial_custom_rescan_led: {  // vial_custom_anim_rescan_leds
            // Call the LED scanning functions
            scan_keycode_categories();
            scan_current_layer_midi_leds();
            
            msg[0] = 0x01; // Success response
            break;
			}
		
		        // ADD YOUR CUSTOM ANIMATION CASES HERE (after the layer RGB cases)
        case vial_custom_anim_set_param: {  // 0xC0
			uint8_t slot = msg[2];
			uint8_t param = msg[3];
			uint8_t value = msg[4];
			
			if (slot >= NUM_CUSTOM_SLOTS) {
				msg[0] = 0x00; // Error - invalid slot
				break;
			}
			
			// Set individual parameter (now supports parameters 10 and 11)
			switch (param) {
				case 0: set_and_save_custom_slot_live_positioning(slot, value); break;
				case 1: set_and_save_custom_slot_macro_positioning(slot, value); break;
				case 2: set_and_save_custom_slot_live_animation(slot, value); break;
				case 3: set_and_save_custom_slot_macro_animation(slot, value); break;
				case 4: set_and_save_custom_slot_use_influence(slot, value != 0); break;
				case 5: set_and_save_custom_slot_background_mode(slot, value); break;
				case 6: set_and_save_custom_slot_pulse_mode(slot, value); break;
				case 7: set_and_save_custom_slot_color_type(slot, value); break;
				case 8: set_and_save_custom_slot_enabled(slot, value != 0); break;
				case 9: set_and_save_custom_slot_background_brightness(slot, value); break;
				case 10: set_and_save_custom_slot_live_speed(slot, value); break;          // NEW
				case 11: set_and_save_custom_slot_macro_speed(slot, value); break;        // NEW
				default:
					msg[0] = 0x00; // Error - invalid parameter
					break;
			}
			
			if (param <= 11) {  // Updated from 9 to 11
				msg[0] = 0x01; // Success
			}
			break;
		}

		case vial_custom_anim_get_param: {  // 0xC1
			uint8_t slot = msg[2];
			uint8_t param = msg[3];
			
			if (slot >= NUM_CUSTOM_SLOTS) {
				msg[0] = 0x00; // Error - invalid slot
				break;
			}
			
			uint8_t data[12];  // Updated from 10 to 12 parameters
			get_custom_slot_parameters_as_bytes(slot, data);
			
			if (param <= 11) {  // Updated from 9 to 11
				msg[0] = 0x01; // Success
				msg[4] = data[param]; // Return parameter value
			} else {
				msg[0] = 0x00; // Error - invalid parameter
			}
			break;
		}

		case vial_custom_anim_set_all: {  // 0xC2
			uint8_t slot = msg[2];
			
			if (slot >= NUM_CUSTOM_SLOTS) {
				msg[0] = 0x00; // Error - invalid slot
				break;
			}
			
			// Parameters are in msg[3] through msg[14] (12 bytes total - updated from 10)
			uint8_t data[12];  // Updated from 10 to 12
			for (int i = 0; i < 12; i++) {  // Updated from 10 to 12
				data[i] = msg[3 + i];
			}
			
			set_custom_slot_parameters_from_bytes(slot, data);
			msg[0] = 0x01; // Success
			break;
		}

		case vial_custom_anim_get_all: {  // 0xC3
			uint8_t slot = msg[2];
			uint8_t source = msg[3];  // NEW: 0 = RAM, 1 = EEPROM
			
			if (slot >= NUM_CUSTOM_SLOTS) {
				msg[0] = 0x00; // Error - invalid slot
				break;
			}
			
			uint8_t data[12];
			
			if (source == 1) {
				// Read from EEPROM
				get_custom_slot_parameters_from_eeprom(slot, data);  // NEW function needed
			} else {
				// Read from RAM (existing behavior)
				get_custom_slot_parameters_as_bytes(slot, data);
			}
			
			msg[0] = 0x01; // Success
			for (int i = 0; i < 12; i++) {
				msg[3 + i] = data[i];
			}
			break;
		}

        case vial_custom_anim_save: {  // 0xC4
            save_custom_animations_to_eeprom();
            msg[0] = 0x01; // Success
            break;
        }

        case vial_custom_anim_load: {  // 0xC5
            load_custom_animations_from_eeprom();
            msg[0] = 0x01; // Success
            break;
        }

        case vial_custom_anim_reset_slot: {  // 0xC6
            uint8_t slot = msg[2];
            
            if (slot >= NUM_CUSTOM_SLOTS) {
                msg[0] = 0x00; // Error - invalid slot
                break;
            }
            
            // Reset slot to basic default (including background brightness)
            set_custom_slot_live_positioning(slot, LIVE_POS_ZONE);
            set_custom_slot_macro_positioning(slot, MACRO_POS_ZONE);
            set_custom_slot_live_animation(slot, LIVE_ANIM_NONE);
            set_custom_slot_macro_animation(slot, MACRO_ANIM_NONE);
            set_custom_slot_use_influence(slot, false);
            set_custom_slot_background_mode(slot, BACKGROUND_NONE);
            set_custom_slot_pulse_mode(slot, 3);
            set_custom_slot_color_type(slot, 1);
            set_custom_slot_enabled(slot, true);
            set_custom_slot_background_brightness(slot, 30);  // NEW: Set default background brightness
            
            save_custom_slot_to_eeprom(slot);
            msg[0] = 0x01; // Success
            break;
        }
		
		case vial_custom_anim_get_ram_state: {  // 0xC9 - Get current RAM state
			uint8_t slot = msg[2];
			
			if (slot >= NUM_CUSTOM_SLOTS) {
				msg[0] = 0x00; // Error - invalid slot
				break;
			}
			
			// Get current RAM parameters (not EEPROM)
			uint8_t data[12];
			get_custom_slot_ram_stuff(slot, data);  // New function needed
			
			msg[0] = 0x01; // Success
			// Copy all parameters to response
			for (int i = 0; i < 12; i++) {
				msg[3 + i] = data[i];
			}
			break;
		}


		case vial_custom_anim_get_status: {  // 0xC7
			msg[0] = 0x01; // Success
			msg[1] = NUM_CUSTOM_SLOTS; // Number of available slots (50)
			msg[2] = current_custom_slot; // Currently active slot
			
			// Pack enabled status for all slots into bytes 3-9 (50 bits needed = 7 bytes)
			memset(&msg[3], 0, 7); // Clear 7 bytes for enabled flags
			for (uint8_t i = 0; i < NUM_CUSTOM_SLOTS; i++) {
				if (custom_slots[i].enabled) {
					uint8_t byte_index = i / 8;
					uint8_t bit_index = i % 8;
					msg[3 + byte_index] |= (1 << bit_index);
				}
			}
			
			// Add parameter count info for GUI
			msg[10] = NUM_CUSTOM_PARAMETERS;  // Should be 12 parameters
			
			// msg[12-31] reserved for future use
			break;
		}
		
		// =========================================================================
		// DEPRECATED: Layer actuation commands (0xCA-0xCD)
		// =========================================================================
		// These commands conflict with arpeggiator commands in arpeggiator_hid.c:
		//   0xCA = ARP_CMD_SET_NOTE (arpeggiator) - conflicts with SET_LAYER_ACTUATION
		//   0xCB = ARP_CMD_SET_NOTES_CHUNK (arpeggiator) - conflicts with GET_LAYER_ACTUATION
		//   0xCC = ARP_CMD_SET_MODE (arpeggiator) - conflicts with GET_ALL_LAYER_ACTUATIONS
		//
		// When using custom HID protocol (0x7D prefix), raw_hid_receive_kb intercepts
		// 0xC0-0xCC and routes to arp_hid_receive, so these handlers are never reached.
		//
		// Layer-wide actuation is now handled via per-key commands (0xE0-0xE6).
		// The GUI sends 70 per-key commands to set all keys when doing layer-wide changes.
		// These cases are kept for Vial protocol compatibility but are effectively dead code.
		// =========================================================================

		case 0xCA: {  // DEPRECATED: HID_CMD_SET_LAYER_ACTUATION - conflicts with arpeggiator
			// This code is never reached via custom HID protocol due to arpeggiator intercept
			if (length >= 13) {
				handle_set_layer_actuation(&msg[2]);
				msg[0] = 0x01;
			} else {
				msg[0] = 0x00;
			}
			break;
		}

		case 0xCB: {  // DEPRECATED: HID_CMD_GET_LAYER_ACTUATION - conflicts with arpeggiator
			// This code is never reached via custom HID protocol due to arpeggiator intercept
			uint8_t layer = msg[2];
			if (layer < 12) {
				handle_get_layer_actuation(layer, msg);
			} else {
				msg[0] = 0x00;
			}
			break;
		}

		case 0xCC: {  // DEPRECATED: HID_CMD_GET_ALL_LAYER_ACTUATIONS - conflicts with arpeggiator
			// This code is never reached via custom HID protocol due to arpeggiator intercept
			handle_get_all_layer_actuations();
			break;
		}

		case 0xCD: {  // HID_CMD_RESET_LAYER_ACTUATIONS (no conflict, still works)
			handle_reset_layer_actuations();
			msg[0] = 0x01;
			break;
		}

		// Gaming/Joystick HID Commands (0xCE-0xD2)
#ifdef JOYSTICK_ENABLE
		case 0xCE: {  // HID_CMD_GAMING_SET_MODE
			if (length >= 3) {
				extern bool gaming_mode_active;
				extern gaming_settings_t gaming_settings;
				extern void gaming_save_settings(void);

				gaming_mode_active = msg[2];
				gaming_settings.gaming_mode_enabled = gaming_mode_active;
				gaming_save_settings();
				msg[0] = 0x01; // Success
			} else {
				msg[0] = 0x00; // Error
			}
			break;
		}

		case 0xCF: {  // HID_CMD_GAMING_SET_KEY_MAP
			// Format: [cmd, channel, control_id, row, col, enabled]
			// control_id: 0-3=LS, 4-7=RS, 8=LT, 9=RT, 10-25=Buttons
			if (length >= 6) {
				extern gaming_settings_t gaming_settings;
				extern void gaming_save_settings(void);

				uint8_t control_id = msg[2];
				uint8_t row = msg[3];
				uint8_t col = msg[4];
				uint8_t enabled = msg[5];

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
					msg[0] = 0x01; // Success
				} else {
					msg[0] = 0x00; // Error: invalid control_id
				}
			} else {
				msg[0] = 0x00; // Error: insufficient data
			}
			break;
		}

		case 0xD0: {  // HID_CMD_GAMING_SET_ANALOG_CONFIG
			// Format: [cmd, channel, ls_min, ls_max, rs_min, rs_max, trigger_min, trigger_max]
			if (length >= 8) {
				extern gaming_settings_t gaming_settings;
				extern void gaming_save_settings(void);

				gaming_settings.ls_config.min_travel_mm_x10 = msg[2];
				gaming_settings.ls_config.max_travel_mm_x10 = msg[3];
				gaming_settings.rs_config.min_travel_mm_x10 = msg[4];
				gaming_settings.rs_config.max_travel_mm_x10 = msg[5];
				gaming_settings.trigger_config.min_travel_mm_x10 = msg[6];
				gaming_settings.trigger_config.max_travel_mm_x10 = msg[7];
				gaming_save_settings();
				msg[0] = 0x01; // Success
			} else {
				msg[0] = 0x00; // Error
			}
			break;
		}

		case 0xD1: {  // HID_CMD_GAMING_GET_SETTINGS
			// Return all gaming settings
			extern gaming_settings_t gaming_settings;

			memset(msg, 0, length);
			msg[0] = 0x01; // Success
			msg[6] = gaming_settings.gaming_mode_enabled;
			msg[7] = gaming_settings.ls_config.min_travel_mm_x10;
			msg[8] = gaming_settings.ls_config.max_travel_mm_x10;
			msg[9] = gaming_settings.rs_config.min_travel_mm_x10;
			msg[10] = gaming_settings.rs_config.max_travel_mm_x10;
			msg[11] = gaming_settings.trigger_config.min_travel_mm_x10;
			msg[12] = gaming_settings.trigger_config.max_travel_mm_x10;
			// Additional settings can be queried separately via 0xCF for each control
			break;
		}

		case 0xD2: {  // HID_CMD_GAMING_RESET
			extern void gaming_reset_settings(void);
			extern void gaming_save_settings(void);

			gaming_reset_settings();
			gaming_save_settings();
			msg[0] = 0x01; // Success
			break;
		}
#endif

		// User Curve Commands (0xD9-0xDE)
		case HID_CMD_USER_CURVE_SET: {  // 0xD9
			// Set user curve: [cmd, slot, p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y, name[16]]
			extern user_curves_t user_curves;
			extern void user_curves_save(void);

			uint8_t slot = msg[2];
			if (slot < 10) {
				// Copy 4 points (8 bytes) - points are in base zone
				memcpy(user_curves.presets[slot].base.points, &msg[3], 8);

				// Copy name (16 bytes) - msg[11] to msg[26]
				memcpy(user_curves.presets[slot].name, &msg[11], 16);
				user_curves.presets[slot].name[15] = '\0';  // Ensure null termination

				user_curves_save();
				msg[0] = 0x01; // Success
			} else {
				msg[0] = 0x00; // Error - invalid slot
			}
			break;
		}

		case HID_CMD_USER_CURVE_GET: {  // 0xDA
			// Get user curve: [cmd, slot] -> [status, slot, p0x, p0y, ..., name[16]]
			extern user_curves_t user_curves;

			uint8_t slot = msg[2];
			if (slot < 10) {
				msg[0] = 0x01; // Success
				msg[1] = slot;

				// Copy 4 points (8 bytes) - points are in base zone
				memcpy(&msg[2], user_curves.presets[slot].base.points, 8);

				// Copy name (16 bytes)
				memcpy(&msg[10], user_curves.presets[slot].name, 16);
			} else {
				msg[0] = 0x00; // Error - invalid slot
			}
			break;
		}

		case HID_CMD_USER_CURVE_GET_ALL: {  // 0xDB
			// Get all user curve names: [cmd] -> [status, name1[10], name2[10], ...]
			extern user_curves_t user_curves;

			msg[0] = 0x01; // Success

			// Return all 10 curve names (truncated to 10 chars each = 100 bytes total)
			for (int i = 0; i < 10; i++) {
				memcpy(&msg[1 + i*10], user_curves.presets[i].name, 10);
			}
			break;
		}

		case HID_CMD_USER_CURVE_RESET: {  // 0xDC
			// Reset all user curves to defaults
			extern void user_curves_reset(void);

			user_curves_reset();
			msg[0] = 0x01; // Success
			break;
		}

		case HID_CMD_GAMING_SET_RESPONSE: {  // 0xDD
			// Set gamepad response: [cmd, angle_adj_enabled, angle, square_output, snappy_joystick, curve_index]
#ifdef JOYSTICK_ENABLE
			extern gaming_settings_t gaming_settings;
			extern void gaming_save_settings(void);

			gaming_settings.angle_adjustment_enabled = msg[2] != 0;
			gaming_settings.diagonal_angle = msg[3];  // 0-90
			gaming_settings.use_square_output = msg[4] != 0;
			gaming_settings.snappy_joystick_enabled = msg[5] != 0;
			gaming_settings.analog_curve_index = msg[6];  // 0-16

			gaming_save_settings();
			msg[0] = 0x01; // Success
#else
			msg[0] = 0x00; // Error - joystick not enabled
#endif
			break;
		}

		case HID_CMD_GAMING_GET_RESPONSE: {  // 0xDE
			// Get gamepad response settings
#ifdef JOYSTICK_ENABLE
			extern gaming_settings_t gaming_settings;

			msg[0] = 0x01; // Success
			msg[1] = gaming_settings.angle_adjustment_enabled ? 0x01 : 0x00;
			msg[2] = gaming_settings.diagonal_angle;
			msg[3] = gaming_settings.use_square_output ? 0x01 : 0x00;
			msg[4] = gaming_settings.snappy_joystick_enabled ? 0x01 : 0x00;
			msg[5] = gaming_settings.analog_curve_index;
#else
			msg[0] = 0x00; // Error - joystick not enabled
#endif
			break;
		}

		// Per-Key RGB Commands (0xD3-0xD8)
		case vial_per_key_get_palette: {  // 0xD3
			// Format: [cmd, channel, offset, count] - offset/count in palette color indices
			// Returns: [success, h0, s0, v0, h1, s1, v1, ...] - count*3 bytes
			// Initialize per-key RGB if not already done
			if (!per_key_rgb_initialized) {
				per_key_rgb_init();
			}

			uint8_t offset = msg[2];  // Palette color index offset (0-15)
			uint8_t count = msg[3];   // Number of colors to return

			// Validate and limit parameters
			if (offset >= PER_KEY_PALETTE_SIZE) {
				offset = 0;
				count = 10;  // Default: first 10 colors
			}
			if (count == 0) count = 10;  // Default count
			if (offset + count > PER_KEY_PALETTE_SIZE) {
				count = PER_KEY_PALETTE_SIZE - offset;
			}
			// Limit to what fits in response (31 bytes max = 10 colors max)
			if (count > 10) count = 10;

			memset(msg, 0, length);
			msg[0] = 0x01; // Success

			// Write requested palette colors
			for (uint8_t i = 0; i < count; i++) {
				uint8_t idx = offset + i;
				msg[1 + i * 3] = per_key_rgb_config.palette[idx].h;
				msg[1 + i * 3 + 1] = per_key_rgb_config.palette[idx].s;
				msg[1 + i * 3 + 2] = per_key_rgb_config.palette[idx].v;
			}
			break;
		}

		case vial_per_key_set_palette_color: {  // 0xD4
			// Format: [cmd, channel, palette_index, h, s, v]
			if (length >= 6) {
				// Initialize per-key RGB if not already done
				if (!per_key_rgb_initialized) {
					per_key_rgb_init();
				}

				uint8_t palette_index = msg[2];
				uint8_t h = msg[3];
				uint8_t s = msg[4];
				uint8_t v = msg[5];

				if (palette_index < PER_KEY_PALETTE_SIZE) {
					per_key_set_palette_color(palette_index, h, s, v);
					msg[0] = 0x01; // Success
				} else {
					msg[0] = 0x00; // Error - invalid palette index
				}
			} else {
				msg[0] = 0x00; // Error - insufficient data
			}
			break;
		}

		case vial_per_key_get_preset_data: {  // 0xD5
			// Format: [cmd, channel, preset, offset, count]
			// Returns: [success, data...]
			if (length >= 5) {
				// Initialize per-key RGB if not already done
				if (!per_key_rgb_initialized) {
					per_key_rgb_init();
				}

				uint8_t preset = msg[2];
				uint8_t offset = msg[3];
				uint8_t count = msg[4];

				if (preset < PER_KEY_NUM_PRESETS && offset < PER_KEY_NUM_LEDS) {
					// Limit count to fit in message (32 bytes - 1 for success byte = 31 max)
					if (count > 31) count = 31;
					if (offset + count > PER_KEY_NUM_LEDS) {
						count = PER_KEY_NUM_LEDS - offset;
					}

					memset(msg, 0, length);
					msg[0] = 0x01; // Success
					per_key_get_preset_data(preset, offset, count, &msg[1]);
				} else {
					msg[0] = 0x00; // Error - invalid preset or offset
				}
			} else {
				msg[0] = 0x00; // Error - insufficient data
			}
			break;
		}

		case vial_per_key_set_led_color: {  // 0xD6
			// Format: [cmd, channel, preset, led_index, palette_index]
			if (length >= 5) {
				// Initialize per-key RGB if not already done
				if (!per_key_rgb_initialized) {
					per_key_rgb_init();
				}

				uint8_t preset = msg[2];
				uint8_t led_index = msg[3];
				uint8_t palette_index = msg[4];

				if (preset < PER_KEY_NUM_PRESETS && led_index < PER_KEY_NUM_LEDS &&
					palette_index < PER_KEY_PALETTE_SIZE) {
					per_key_set_led_color(preset, led_index, palette_index);
					msg[0] = 0x01; // Success
				} else {
					msg[0] = 0x00; // Error - invalid indices
				}
			} else {
				msg[0] = 0x00; // Error - insufficient data
			}
			break;
		}

		case vial_per_key_save: {  // 0xD7
			// Save all per-key data to EEPROM
			// Initialize per-key RGB if not already done
			if (!per_key_rgb_initialized) {
				per_key_rgb_init();
			}

			per_key_rgb_save_to_eeprom();
			msg[0] = 0x01; // Success
			break;
		}

		case vial_per_key_load: {  // 0xD8
			// Load all per-key data from EEPROM
			// If msg[2] == 0xFF, force reset to defaults instead
			if (msg[2] == 0xFF) {
				// Force reset to defaults
				per_key_rgb_reset_to_defaults();
				per_key_rgb_save_to_eeprom();
				per_key_rgb_initialized = true;
			} else {
				// Normal load from EEPROM
				if (!per_key_rgb_initialized) {
					per_key_rgb_init();
				} else {
					// Already initialized, force reload from EEPROM
					per_key_rgb_load_from_eeprom();
				}
			}
			msg[0] = 0x01; // Success
			break;
		}

		// Per-Key Actuation Commands (0xE0-0xE6)
		case HID_CMD_SET_PER_KEY_ACTUATION: {  // 0xE0
			// Format: [layer, key_index, actuation, deadzone_top, deadzone_bottom, velocity_curve,
			//          flags, rapidfire_press_sens, rapidfire_release_sens, rapidfire_velocity_mod]
			// flags: Bit 0=rapidfire_enabled, Bit 1=use_per_key_velocity_curve
			// Total: 10 data bytes + 2 overhead = 12 bytes minimum
			if (length >= 12) {
				handle_set_per_key_actuation(&msg[2]);
				msg[0] = 0x01; // Success
			} else {
				msg[0] = 0x00; // Error
			}
			break;
		}

		case HID_CMD_GET_PER_KEY_ACTUATION: {  // 0xE1
			// Format: [layer, key_index]
			// Response: [actuation, deadzone_top, deadzone_bottom, velocity_curve,
			//            flags, rapidfire_press_sens, rapidfire_release_sens, rapidfire_velocity_mod]
			// flags: Bit 0=rapidfire_enabled, Bit 1=use_per_key_velocity_curve
			// Total: 8 response bytes
			if (length >= 4) {
				handle_get_per_key_actuation(&msg[2], msg);
				msg[0] = 0x01; // Success - 8 bytes returned in msg[0-7]
			} else {
				msg[0] = 0x00; // Error
			}
			break;
		}

		case HID_CMD_GET_ALL_PER_KEY_ACTUATIONS: {  // 0xE2
			// TODO: Implement chunked response for 6,720 bytes (12 layers × 70 keys × 8 bytes)
			// For now, return error as this needs multi-packet protocol
			msg[0] = 0x00; // Not implemented yet
			break;
		}

		case HID_CMD_RESET_PER_KEY_ACTUATIONS: {  // 0xE3
			handle_reset_per_key_actuations_hid();
			msg[0] = 0x01; // Success
			break;
		}

		case HID_CMD_SET_PER_KEY_MODE: {  // 0xE4 - DEPRECATED
			// NOTE: Mode flags have been REMOVED. Firmware ALWAYS uses per-key per-layer.
			// This handler is kept for backward compatibility - it's a no-op.
			// Format: [per_key_enabled, per_layer_enabled]
			if (length >= 4) {
				handle_set_per_key_mode(&msg[2]);
				msg[0] = 0x01; // Success (no-op)
			} else {
				msg[0] = 0x00; // Error
			}
			break;
		}

		case HID_CMD_GET_PER_KEY_MODE: {  // 0xE5 - DEPRECATED
			// NOTE: Mode flags have been REMOVED. Firmware ALWAYS uses per-key per-layer.
			// Returns 1,1 (both enabled) for backward compatibility.
			// Response: [per_key_enabled, per_layer_enabled]
			handle_get_per_key_mode(&msg[1]);
			msg[0] = 0x01; // Success
			break;
		}

		case HID_CMD_COPY_LAYER_ACTUATIONS: {  // 0xE6
			// Format: [source_layer, dest_layer]
			if (length >= 4) {
				handle_copy_layer_actuations(&msg[2]);
				msg[0] = 0x01; // Success
			} else {
				msg[0] = 0x00; // Error
			}
			break;
		}

		case HID_CMD_SET_KEYBOARD_PARAM_SINGLE: {  // 0xE8 - Set individual keyboard parameter
			// Format: [param_id, value_byte(s)...]
			// For 16-bit params: [param_id, low_byte, high_byte]
			if (length >= 4) {
				uint8_t param_id = msg[2];
				uint8_t value8 = msg[3];
				uint16_t value16 = msg[3] | (msg[4] << 8);  // Little-endian for 16-bit params
				bool settings_changed = false;

				switch (param_id) {
					// Velocity curve and range parameters (update keyboard_settings)
					case 4:  // PARAM_HE_VELOCITY_CURVE (0-16)
						keyboard_settings.he_velocity_curve = value8;
						he_velocity_curve = value8;  // Also update global for OLED display
						settings_changed = true;
						msg[0] = 0x01;
						break;
					case 5:  // PARAM_HE_VELOCITY_MIN (1-127)
						keyboard_settings.he_velocity_min = value8;
						he_velocity_min = value8;
						settings_changed = true;
						msg[0] = 0x01;
						break;
					case 6:  // PARAM_HE_VELOCITY_MAX (1-127)
						keyboard_settings.he_velocity_max = value8;
						he_velocity_max = value8;
						settings_changed = true;
						msg[0] = 0x01;
						break;

					// Global MIDI settings (update global variables)
					case 13:  // PARAM_VELOCITY_MODE (0-3)
						velocity_mode = value8;
						settings_changed = true;
						msg[0] = 0x01;
						break;
					case 14:  // PARAM_AFTERTOUCH_MODE (0-6)
						aftertouch_mode = value8;
						settings_changed = true;
						msg[0] = 0x01;
						break;
					case 39:  // PARAM_AFTERTOUCH_CC (0-127, 255=off)
						aftertouch_cc = value8;
						settings_changed = true;
						msg[0] = 0x01;
						break;
					case 40:  // PARAM_VIBRATO_SENSITIVITY (50-200)
						vibrato_sensitivity = value8;
						settings_changed = true;
						msg[0] = 0x01;
						break;
					case 41:  // PARAM_VIBRATO_DECAY_TIME (0-2000ms, 16-bit)
						vibrato_decay_time = value16;
						settings_changed = true;
						msg[0] = 0x01;
						break;
					case 42:  // PARAM_MIN_PRESS_TIME (50-500ms, 16-bit)
						min_press_time = value16;
						settings_changed = true;
						msg[0] = 0x01;
						break;
					case 43:  // PARAM_MAX_PRESS_TIME (5-100ms, 16-bit)
						max_press_time = value16;
						settings_changed = true;
						msg[0] = 0x01;
						break;
					default:
						msg[0] = 0x00;  // Unknown param_id
						break;
				}

				// Force refresh active_settings so changes take effect immediately
				if (settings_changed) {
					analog_matrix_refresh_settings();
				}

				// Echo back the param_id and value for debugging
				msg[1] = param_id;
				msg[2] = value8;
			} else {
				msg[0] = 0x00; // Error - invalid length
			}
			break;
		}

        // END LAYER RGB CASES
#endif // ORTHOMIDI_CUSTOM_HID_ENABLE

        case vial_dynamic_entry_op: {
            switch (msg[2]) {
            case dynamic_vial_get_number_of_entries: {
                memset(msg, 0, length);
                msg[0] = VIAL_TAP_DANCE_ENTRIES;
                msg[1] = VIAL_COMBO_ENTRIES;
                msg[2] = VIAL_KEY_OVERRIDE_ENTRIES;
                break;
            }
#ifdef VIAL_TAP_DANCE_ENABLE
            case dynamic_vial_tap_dance_get: {
                uint8_t idx = msg[3];
                vial_tap_dance_entry_t td = { 0 };
                msg[0] = dynamic_keymap_get_tap_dance(idx, &td);
                memcpy(&msg[1], &td, sizeof(td));
                break;
            }
            case dynamic_vial_tap_dance_set: {
                uint8_t idx = msg[3];
                vial_tap_dance_entry_t td;
                memcpy(&td, &msg[4], sizeof(td));
                td.on_tap = vial_keycode_firewall(td.on_tap);
                td.on_hold = vial_keycode_firewall(td.on_hold);
                td.on_double_tap = vial_keycode_firewall(td.on_double_tap);
                td.on_tap_hold = vial_keycode_firewall(td.on_tap_hold);
                msg[0] = dynamic_keymap_set_tap_dance(idx, &td);
                reload_tap_dance();
                break;
            }
#endif
#ifdef VIAL_COMBO_ENABLE
            case dynamic_vial_combo_get: {
                uint8_t idx = msg[3];
                vial_combo_entry_t entry = { 0 };
                msg[0] = dynamic_keymap_get_combo(idx, &entry);
                memcpy(&msg[1], &entry, sizeof(entry));
                break;
            }
            case dynamic_vial_combo_set: {
                uint8_t idx = msg[3];
                vial_combo_entry_t entry;
                memcpy(&entry, &msg[4], sizeof(entry));
                entry.output = vial_keycode_firewall(entry.output);
                msg[0] = dynamic_keymap_set_combo(idx, &entry);
                reload_combo();
                break;
            }
#endif
#ifdef VIAL_KEY_OVERRIDE_ENABLE
            case dynamic_vial_key_override_get: {
                uint8_t idx = msg[3];
                vial_key_override_entry_t entry = { 0 };
                msg[0] = dynamic_keymap_get_key_override(idx, &entry);
                memcpy(&msg[1], &entry, sizeof(entry));
                break;
            }
            case dynamic_vial_key_override_set: {
                uint8_t idx = msg[3];
                vial_key_override_entry_t entry;
                memcpy(&entry, &msg[4], sizeof(entry));
                entry.replacement = vial_keycode_firewall(entry.replacement);
                msg[0] = dynamic_keymap_set_key_override(idx, &entry);
                reload_key_override();
                break;
			}
            }
#endif
            }

            break;
        }
    }


uint16_t g_vial_magic_keycode_override;

void vial_keycode_down(uint16_t keycode) {
    g_vial_magic_keycode_override = keycode;

    if (keycode <= QK_MODS_MAX) {
        register_code16(keycode);
    } else {
        action_exec((keyevent_t){
            .type = KEY_EVENT,
            .key = (keypos_t){.row = VIAL_MATRIX_MAGIC, .col = VIAL_MATRIX_MAGIC}, .pressed = 1, .time = (timer_read() | 1) /* time should not be 0 */
        });
    }
}

void vial_keycode_up(uint16_t keycode) {
    g_vial_magic_keycode_override = keycode;

    if (keycode <= QK_MODS_MAX) {
        unregister_code16(keycode);
    } else {
        action_exec((keyevent_t){
            .type = KEY_EVENT,
            .key = (keypos_t){.row = VIAL_MATRIX_MAGIC, .col = VIAL_MATRIX_MAGIC}, .pressed = 0, .time = (timer_read() | 1) /* time should not be 0 */
        });
    }
}

void vial_keycode_tap(uint16_t keycode) {
    vial_keycode_down(keycode);
    qs_wait_ms(QS_tap_code_delay);
    vial_keycode_up(keycode);
}

#ifdef VIAL_TAP_DANCE_ENABLE
#include "process_tap_dance.h"

/* based on ZSA configurator generated code */

enum {
    SINGLE_TAP = 1,
    SINGLE_HOLD,
    DOUBLE_TAP,
    DOUBLE_HOLD,
    DOUBLE_SINGLE_TAP,
    MORE_TAPS
};

static uint8_t dance_state[VIAL_TAP_DANCE_ENTRIES];
static vial_tap_dance_entry_t td_entry;

static uint8_t dance_step(tap_dance_state_t *state) {
    if (state->count == 1) {
        if (state->interrupted || !state->pressed) return SINGLE_TAP;
        else return SINGLE_HOLD;
    } else if (state->count == 2) {
        if (state->interrupted) return DOUBLE_SINGLE_TAP;
        else if (state->pressed) return DOUBLE_HOLD;
        else return DOUBLE_TAP;
    }
    return MORE_TAPS;
}

static void on_dance(tap_dance_state_t *state, void *user_data) {
    uint8_t index = (uintptr_t)user_data;
    if (dynamic_keymap_get_tap_dance(index, &td_entry) != 0)
        return;
    uint16_t kc = td_entry.on_tap;
    if (kc) {
        if (state->count == 3) {
            vial_keycode_tap(kc);
            vial_keycode_tap(kc);
            vial_keycode_tap(kc);
        } else if (state->count > 3) {
            vial_keycode_tap(kc);
        }
    }
}

static void on_dance_finished(tap_dance_state_t *state, void *user_data) {
    uint8_t index = (uintptr_t)user_data;
    if (dynamic_keymap_get_tap_dance(index, &td_entry) != 0)
        return;
    dance_state[index] = dance_step(state);
    switch (dance_state[index]) {
        case SINGLE_TAP: {
            if (td_entry.on_tap)
                vial_keycode_down(td_entry.on_tap);
            break;
        }
        case SINGLE_HOLD: {
            if (td_entry.on_hold)
                vial_keycode_down(td_entry.on_hold);
            else if (td_entry.on_tap)
                vial_keycode_down(td_entry.on_tap);
            break;
        }
        case DOUBLE_TAP: {
            if (td_entry.on_double_tap) {
                vial_keycode_down(td_entry.on_double_tap);
            } else if (td_entry.on_tap) {
                vial_keycode_tap(td_entry.on_tap);
                vial_keycode_down(td_entry.on_tap);
            }
            break;
        }
        case DOUBLE_HOLD: {
            if (td_entry.on_tap_hold) {
                vial_keycode_down(td_entry.on_tap_hold);
            } else {
                if (td_entry.on_tap) {
                    vial_keycode_tap(td_entry.on_tap);
                    if (td_entry.on_hold)
                        vial_keycode_down(td_entry.on_hold);
                    else
                        vial_keycode_down(td_entry.on_tap);
                } else if (td_entry.on_hold) {
                    vial_keycode_down(td_entry.on_hold);
                }
            }
            break;
        }
        case DOUBLE_SINGLE_TAP: {
            if (td_entry.on_tap) {
                vial_keycode_tap(td_entry.on_tap);
                vial_keycode_down(td_entry.on_tap);
            }
            break;
        }
    }
}

static void on_dance_reset(tap_dance_state_t *state, void *user_data) {
    uint8_t index = (uintptr_t)user_data;
    if (dynamic_keymap_get_tap_dance(index, &td_entry) != 0)
        return;
    qs_wait_ms(QS_tap_code_delay);
    uint8_t st = dance_state[index];
    state->count = 0;
    dance_state[index] = 0;
    switch (st) {
        case SINGLE_TAP: {
            if (td_entry.on_tap)
                vial_keycode_up(td_entry.on_tap);
            break;
        }
        case SINGLE_HOLD: {
            if (td_entry.on_hold)
                vial_keycode_up(td_entry.on_hold);
            else if (td_entry.on_tap)
                vial_keycode_up(td_entry.on_tap);
            break;
        }
        case DOUBLE_TAP: {
            if (td_entry.on_double_tap) {
                vial_keycode_up(td_entry.on_double_tap);
            } else if (td_entry.on_tap) {
                vial_keycode_up(td_entry.on_tap);
            }
            break;
        }
        case DOUBLE_HOLD: {
            if (td_entry.on_tap_hold) {
                vial_keycode_up(td_entry.on_tap_hold);
            } else {
                if (td_entry.on_tap) {
                    if (td_entry.on_hold)
                        vial_keycode_up(td_entry.on_hold);
                    else
                        vial_keycode_up(td_entry.on_tap);
                } else if (td_entry.on_hold) {
                    vial_keycode_up(td_entry.on_hold);
                }
            }
            break;
        }
        case DOUBLE_SINGLE_TAP: {
            if (td_entry.on_tap) {
                vial_keycode_up(td_entry.on_tap);
            }
            break;
        }
    }
}

tap_dance_action_t tap_dance_actions[VIAL_TAP_DANCE_ENTRIES] = { };

/* Load timings from eeprom into custom_tapping_term */
static void reload_tap_dance(void) {
    for (size_t i = 0; i < VIAL_TAP_DANCE_ENTRIES; ++i) {
        tap_dance_actions[i].fn.on_each_tap = on_dance;
        tap_dance_actions[i].fn.on_dance_finished = on_dance_finished;
        tap_dance_actions[i].fn.on_reset = on_dance_reset;
        tap_dance_actions[i].user_data = (void*)i;
    }
}
#endif

#ifdef TAPPING_TERM_PER_KEY
uint16_t get_tapping_term(uint16_t keycode, keyrecord_t *record) {
#ifdef VIAL_TAP_DANCE_ENABLE
    if (keycode >= QK_TAP_DANCE && keycode <= QK_TAP_DANCE_MAX) {
        vial_tap_dance_entry_t td;
        if (dynamic_keymap_get_tap_dance(keycode & 0xFF, &td) == 0)
            return td.custom_tapping_term;
    }
#endif
#ifdef QMK_SETTINGS
    return qs_get_tapping_term(keycode, record);
#else
    return TAPPING_TERM;
#endif
}
#endif

#ifdef VIAL_COMBO_ENABLE
combo_t key_combos[VIAL_COMBO_ENTRIES] = { };
uint16_t key_combos_keys[VIAL_COMBO_ENTRIES][5];

static void reload_combo(void) {
    /* initialize with all keys = COMBO_END */
    memset(key_combos_keys, 0, sizeof(key_combos_keys));
    memset(key_combos, 0, sizeof(key_combos));

    /* reload from eeprom */
    for (size_t i = 0; i < VIAL_COMBO_ENTRIES; ++i) {
        uint16_t *seq = key_combos_keys[i];
        key_combos[i].keys = seq;

        vial_combo_entry_t entry;
        if (dynamic_keymap_get_combo(i, &entry) == 0) {
            memcpy(seq, entry.input, sizeof(entry.input));
            key_combos[i].keycode = entry.output;
        }
    }
}
#endif

#ifdef VIAL_TAP_DANCE_ENABLE
void process_tap_dance_action_on_dance_finished(tap_dance_action_t *action);
#endif

bool process_record_vial(uint16_t keycode, keyrecord_t *record) {
#ifdef VIAL_TAP_DANCE_ENABLE
    /* process releases before tap-dance timeout arrives */
    if (!record->event.pressed && keycode >= QK_TAP_DANCE && keycode <= QK_TAP_DANCE_MAX) {
        uint16_t idx = keycode - QK_TAP_DANCE;
        if (dynamic_keymap_get_tap_dance(idx, &td_entry) != 0)
            return true;

        tap_dance_action_t *action = &tap_dance_actions[idx];

        /* only care about 2 possibilities here
           - tap and hold set, everything else unset: process first release early (count == 1)
           - double tap set: process second release early (count == 2)
         */
        if ((action->state.count == 1 && td_entry.on_tap && td_entry.on_hold && !td_entry.on_double_tap && !td_entry.on_tap_hold)
            || (action->state.count == 2 && td_entry.on_double_tap)) {
                action->state.pressed = false;
                process_tap_dance_action_on_dance_finished(action);
                /* reset_tap_dance() will get called in process_tap_dance() */
            }
    }
#endif

    return true;
}

#ifdef VIAL_KEY_OVERRIDE_ENABLE
static bool vial_key_override_disabled = 0;
static key_override_t overrides[VIAL_KEY_OVERRIDE_ENTRIES] = { 0 };
static key_override_t *override_ptrs[VIAL_KEY_OVERRIDE_ENTRIES + 1] = { 0 };
const key_override_t **key_overrides = (const key_override_t**)override_ptrs;

static int vial_get_key_override(uint8_t index, key_override_t *out) {
    vial_key_override_entry_t entry;
    int ret;
    if ((ret = dynamic_keymap_get_key_override(index, &entry)) != 0)
        return ret;

    memset(out, 0, sizeof(*out));
    out->trigger = entry.trigger;
    out->trigger_mods = entry.trigger_mods;
    out->layers = entry.layers;
    out->negative_mod_mask = entry.negative_mod_mask;
    out->suppressed_mods = entry.suppressed_mods;
    out->replacement = entry.replacement;
    out->options = 0;
    uint8_t opt = entry.options;
    if (opt & vial_ko_enabled)
        out->enabled = NULL;
    else
        out->enabled = &vial_key_override_disabled;
    /* right now these options match one-to-one so this isn't strictly necessary,
       nevertheless future-proof the code by parsing them out to ensure "stable" abi */
    if (opt & vial_ko_option_activation_trigger_down) out->options |= ko_option_activation_trigger_down;
    if (opt & vial_ko_option_activation_required_mod_down) out->options |= ko_option_activation_required_mod_down;
    if (opt & vial_ko_option_activation_negative_mod_up) out->options |= ko_option_activation_negative_mod_up;
    if (opt & vial_ko_option_one_mod) out->options |= ko_option_one_mod;
    if (opt & vial_ko_option_no_reregister_trigger) out->options |= ko_option_no_reregister_trigger;
    if (opt & vial_ko_option_no_unregister_on_other_key_down) out->options |= ko_option_no_unregister_on_other_key_down;

    return 0;
}

static void reload_key_override(void) {
    for (size_t i = 0; i < VIAL_KEY_OVERRIDE_ENTRIES; ++i) {
        override_ptrs[i] = &overrides[i];
        vial_get_key_override(i, &overrides[i]);
    }
}
#endif