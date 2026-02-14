/* Copyright 2025
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

#pragma once

#include "quantum.h"
#include <stdint.h>
#include <stdbool.h>

// ============================================================================
// DKS (Dynamic Keystroke) System Configuration
// ============================================================================

#define DKS_NUM_SLOTS           50      // Total number of DKS configurations
#define DKS_ACTIONS_PER_STAGE   4       // 4 press + 4 release actions
#define DKS_TOTAL_ACTIONS       8       // 4 press + 4 release

// DKS Keycode Range (50 keycodes: DKS_00 through DKS_49)
#define DKS_KEY_BASE            0xED00
#define DKS_KEY_MAX             (DKS_KEY_BASE + DKS_NUM_SLOTS - 1)  // 0xED31

// EEPROM Configuration
#define EEPROM_DKS_BASE         52000   // Was 75000 - MOVED: CAT24C512 is 64KB (max addr 65535)
#define EEPROM_DKS_MAGIC        0xDC57  // "DKS" magic number
#define EEPROM_DKS_VERSION      0x01

// ============================================================================
// DKS Behavior Types
// ============================================================================

typedef enum {
    DKS_BEHAVIOR_TAP     = 0,  // Press + immediate release (default)
    DKS_BEHAVIOR_PRESS   = 1,  // Press and hold until key released
    DKS_BEHAVIOR_RELEASE = 2,  // Release only (for upstroke actions)
    DKS_BEHAVIOR_NONE    = 3   // Reserved/disabled
} dks_behavior_t;

// ============================================================================
// DKS Data Structures
// ============================================================================

/**
 * DKS Slot Configuration
 * Each slot contains 4 press actions and 4 release actions
 * Total size: 32 bytes per slot
 */
typedef struct {
    // Press actions (downstroke) - 16 bytes
    uint16_t press_keycode[DKS_ACTIONS_PER_STAGE];      // 8 bytes: keycodes to send
    uint8_t  press_actuation[DKS_ACTIONS_PER_STAGE];    // 4 bytes: actuation points (0-100)

    // Release actions (upstroke) - 16 bytes
    uint16_t release_keycode[DKS_ACTIONS_PER_STAGE];    // 8 bytes: keycodes to send
    uint8_t  release_actuation[DKS_ACTIONS_PER_STAGE];  // 4 bytes: actuation points (0-100)

    // Behaviors - 2 bytes (bit-packed: 2 bits per action × 8 actions = 16 bits)
    // Bits 0-1:   press_behavior[0]
    // Bits 2-3:   press_behavior[1]
    // Bits 4-5:   press_behavior[2]
    // Bits 6-7:   press_behavior[3]
    // Bits 8-9:   release_behavior[0]
    // Bits 10-11: release_behavior[1]
    // Bits 12-13: release_behavior[2]
    // Bits 14-15: release_behavior[3]
    uint16_t behaviors;

    // Padding - 6 bytes (reserved for future use)
    uint8_t  reserved[6];
} dks_slot_t;

// Compile-time size check
_Static_assert(sizeof(dks_slot_t) == 32, "dks_slot_t must be exactly 32 bytes");

/**
 * DKS State Tracking (Per Physical Key)
 * Tracks which actions are currently active for each physical key position
 */
typedef struct {
    uint8_t  dks_slot;              // Which DKS slot this key is using (0-49)
    uint8_t  last_travel;           // Last travel position (0-240 internal units)
    uint8_t  press_triggered;       // Bitmask: which press actions have been triggered
    uint8_t  release_triggered;     // Bitmask: which release actions have been triggered
    uint16_t active_keycodes;       // Bitmask: which keycodes are currently held down
    bool     is_dks_key;            // Is this physical key a DKS key?
    bool     key_was_down;          // Was key down on last scan?
} dks_state_t;

/**
 * EEPROM Header Structure
 */
typedef struct {
    uint16_t magic;         // Magic number for validation (0xDC57)
    uint8_t  version;       // Version number
    uint8_t  reserved;      // Reserved for future use
} dks_eeprom_header_t;

// ============================================================================
// Public Functions
// ============================================================================

/**
 * Initialize DKS system
 * Call during keyboard initialization
 */
void dks_init(void);

/**
 * Process a DKS key during matrix scanning
 * @param row Physical row of the key
 * @param col Physical column of the key
 * @param travel Current travel value (0-240 internal units)
 * @param keycode The DKS keycode (DKS_KEY_BASE + slot)
 */
void dks_process_key(uint8_t row, uint8_t col, uint8_t travel, uint16_t keycode);

/**
 * Reset all DKS states when layer changes or keyboard resets
 */
void dks_reset_states(void);

/**
 * Get a DKS slot configuration
 * @param slot Slot number (0-49)
 * @return Pointer to slot configuration (read-only)
 */
const dks_slot_t* dks_get_slot(uint8_t slot);

/**
 * Set a DKS slot configuration
 * @param slot Slot number (0-49)
 * @param config Pointer to new configuration
 */
void dks_set_slot(uint8_t slot, const dks_slot_t* config);

/**
 * Get behavior for a specific action
 * @param slot Pointer to slot configuration
 * @param action_index Action index (0-7: 0-3=press, 4-7=release)
 * @return Behavior type
 */
dks_behavior_t dks_get_behavior(const dks_slot_t* slot, uint8_t action_index);

/**
 * Set behavior for a specific action
 * @param slot Pointer to slot configuration
 * @param action_index Action index (0-7: 0-3=press, 4-7=release)
 * @param behavior Behavior type
 */
void dks_set_behavior(dks_slot_t* slot, uint8_t action_index, dks_behavior_t behavior);

/**
 * Load all DKS configurations from EEPROM
 * @return true if loaded successfully, false if not initialized
 */
bool dks_load_from_eeprom(void);

/**
 * Save all DKS configurations to EEPROM
 */
void dks_save_to_eeprom(void);

/**
 * Save a single DKS slot to EEPROM
 * @param slot_num Slot number (0-49)
 */
void dks_save_slot_to_eeprom(uint8_t slot_num);

/**
 * Reset all DKS configurations to default (all KC_NO)
 */
void dks_reset_all_slots(void);

/**
 * Check if a keycode is a DKS keycode
 * @param keycode Keycode to check
 * @return true if keycode is in DKS range
 */
static inline bool is_dks_keycode(uint16_t keycode) {
    return (keycode >= DKS_KEY_BASE && keycode <= DKS_KEY_MAX);
}

/**
 * Get slot number from DKS keycode
 * @param keycode DKS keycode
 * @return Slot number (0-49)
 */
static inline uint8_t dks_keycode_to_slot(uint16_t keycode) {
    return (uint8_t)(keycode - DKS_KEY_BASE);
}

// ============================================================================
// Debug Functions (optional, can be disabled for production)
// ============================================================================

#ifdef DKS_DEBUG
void dks_print_slot(uint8_t slot);
void dks_print_state(uint8_t row, uint8_t col);
#endif

