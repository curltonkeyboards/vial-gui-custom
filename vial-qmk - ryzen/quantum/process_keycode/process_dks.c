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

#include "process_dks.h"
#include "eeconfig.h"
#include "eeprom.h"
#include "action.h"
#include "quantum.h"
#include <string.h>

// ============================================================================
// Internal Constants
// ============================================================================

// Travel conversion (from matrix.h conventions)
#define TRAVEL_SCALE        6
#define FULL_TRAVEL_UNIT    40

// EEPROM offsets
#define EEPROM_DKS_HEADER_OFFSET    0
#define EEPROM_DKS_SLOTS_OFFSET     4

// ============================================================================
// Static Storage
// ============================================================================

// DKS slot configurations (RAM cache)
static dks_slot_t dks_slots[DKS_NUM_SLOTS];

// DKS state tracking (per physical key position)
static dks_state_t dks_states[MATRIX_ROWS][MATRIX_COLS];

// Initialization flag
static bool dks_initialized = false;

// ============================================================================
// Helper Functions - Behavior Bit Packing
// ============================================================================

/**
 * Get behavior from packed uint16_t
 * Action indices: 0-3 = press, 4-7 = release
 */
dks_behavior_t dks_get_behavior(const dks_slot_t* slot, uint8_t action_index) {
    if (action_index >= DKS_TOTAL_ACTIONS) {
        return DKS_BEHAVIOR_NONE;
    }

    // Each behavior uses 2 bits
    uint8_t shift = action_index * 2;
    return (dks_behavior_t)((slot->behaviors >> shift) & 0x03);
}

/**
 * Set behavior in packed uint16_t
 */
void dks_set_behavior(dks_slot_t* slot, uint8_t action_index, dks_behavior_t behavior) {
    if (action_index >= DKS_TOTAL_ACTIONS) {
        return;
    }

    // Clear the 2 bits for this action
    uint8_t shift = action_index * 2;
    uint16_t mask = ~(0x03 << shift);
    slot->behaviors = (slot->behaviors & mask) | ((uint16_t)behavior << shift);
}

// ============================================================================
// Helper Functions - Travel Conversion
// ============================================================================

/**
 * Convert user actuation point (0-100) to internal travel units (0-240)
 * User scale: 0 = 0mm, 100 = 4.0mm (full key travel)
 * Internal scale: 0-240 (FULL_TRAVEL_UNIT * TRAVEL_SCALE)
 */
static inline uint8_t actuation_to_travel(uint8_t actuation) {
    // actuation (0-100) * FULL_TRAVEL_UNIT (40) * TRAVEL_SCALE (6) / 100
    return (uint8_t)((actuation * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100);
}

// ============================================================================
// Initialization and EEPROM Functions
// ============================================================================

/**
 * Initialize DKS system
 */
void dks_init(void) {
    // Clear all states
    memset(dks_states, 0, sizeof(dks_states));

    // Try to load from EEPROM
    if (!dks_load_from_eeprom()) {
        // EEPROM not initialized, set defaults
        dks_reset_all_slots();
    }

    dks_initialized = true;
}

/**
 * Reset all DKS slots to default (all actions disabled)
 */
void dks_reset_all_slots(void) {
    for (uint8_t i = 0; i < DKS_NUM_SLOTS; i++) {
        dks_slot_t* slot = &dks_slots[i];

        // Clear all keycodes (KC_NO = 0)
        memset(slot->press_keycode, 0, sizeof(slot->press_keycode));
        memset(slot->release_keycode, 0, sizeof(slot->release_keycode));

        // Set default actuation points (evenly distributed across 4.0mm travel)
        // Press: 0.96mm, 1.92mm, 2.88mm, 3.84mm
        slot->press_actuation[0] = 24;  // 0.96mm (24% of 4.0mm)
        slot->press_actuation[1] = 48;  // 1.92mm (48% of 4.0mm)
        slot->press_actuation[2] = 72;  // 2.88mm (72% of 4.0mm)
        slot->press_actuation[3] = 96;  // 3.84mm (96% of 4.0mm)

        // Release: mirror of press
        slot->release_actuation[0] = 96;  // 3.84mm
        slot->release_actuation[1] = 72;  // 2.88mm
        slot->release_actuation[2] = 48;  // 1.92mm
        slot->release_actuation[3] = 24;  // 0.96mm

        // Set all behaviors to TAP (default)
        slot->behaviors = 0x0000;  // All 0s = TAP for all actions
    }
}

/**
 * Validate a DKS slot has sane values.
 * Returns true if the slot looks valid, false if it appears corrupted.
 */
static bool dks_validate_slot(const dks_slot_t* slot) {
    // Check actuation points are in valid range (0-100)
    for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
        if (slot->press_actuation[i] > 100) return false;
        if (slot->release_actuation[i] > 100) return false;
    }
    // Check behaviors are valid (only 2 bits per action, packed in 16 bits)
    // Each 2-bit field should be 0-3 which is always true for uint16_t,
    // but check that reserved bits above bit 15 are not set (they can't be
    // for uint16_t, so this is just a sanity check on the overall value)
    return true;
}

/**
 * Load DKS configurations from EEPROM
 * Reads slot-by-slot (32 bytes each) to avoid large stack allocations
 * and validates each slot individually.
 */
bool dks_load_from_eeprom(void) {
    // Read header
    dks_eeprom_header_t header;
    eeprom_read_block(&header, (void*)(EEPROM_DKS_BASE + EEPROM_DKS_HEADER_OFFSET), sizeof(header));

    // Validate magic number and version
    if (header.magic != EEPROM_DKS_MAGIC || header.version != EEPROM_DKS_VERSION) {
        return false;  // Not initialized or wrong version
    }

    // Read slots one at a time (32 bytes each - safe for stack)
    // and validate each to prevent corrupted EEPROM data from crashing
    for (uint8_t i = 0; i < DKS_NUM_SLOTS; i++) {
        dks_slot_t temp_slot;
        eeprom_read_block(
            &temp_slot,
            (void*)(EEPROM_DKS_BASE + EEPROM_DKS_SLOTS_OFFSET + (i * sizeof(dks_slot_t))),
            sizeof(dks_slot_t)
        );

        if (dks_validate_slot(&temp_slot)) {
            memcpy(&dks_slots[i], &temp_slot, sizeof(dks_slot_t));
        } else {
            // Slot is corrupted - reset to defaults instead of loading garbage
            memset(dks_slots[i].press_keycode, 0, sizeof(dks_slots[i].press_keycode));
            memset(dks_slots[i].release_keycode, 0, sizeof(dks_slots[i].release_keycode));
            dks_slots[i].press_actuation[0] = 24;
            dks_slots[i].press_actuation[1] = 48;
            dks_slots[i].press_actuation[2] = 72;
            dks_slots[i].press_actuation[3] = 96;
            dks_slots[i].release_actuation[0] = 96;
            dks_slots[i].release_actuation[1] = 72;
            dks_slots[i].release_actuation[2] = 48;
            dks_slots[i].release_actuation[3] = 24;
            dks_slots[i].behaviors = 0x0000;
        }
    }

    return true;
}

/**
 * Save DKS configurations to EEPROM
 *
 * Writes slot-by-slot (32 bytes each) instead of the entire 1600-byte array
 * at once, because eeprom_update_block() allocates a VLA of the same size on
 * the stack for its read-compare buffer. 1600 bytes on stack would overflow
 * the limited ARM Cortex-M stack.
 */
void dks_save_to_eeprom(void) {
    // Write header (4 bytes - safe for stack)
    dks_eeprom_header_t header = {
        .magic = EEPROM_DKS_MAGIC,
        .version = EEPROM_DKS_VERSION,
        .reserved = 0
    };
    eeprom_update_block(&header, (void*)(EEPROM_DKS_BASE + EEPROM_DKS_HEADER_OFFSET), sizeof(header));

    // Write slots one at a time (32 bytes each - safe for stack)
    for (uint8_t i = 0; i < DKS_NUM_SLOTS; i++) {
        eeprom_update_block(
            &dks_slots[i],
            (void*)(EEPROM_DKS_BASE + EEPROM_DKS_SLOTS_OFFSET + (i * sizeof(dks_slot_t))),
            sizeof(dks_slot_t)
        );
    }
}

/**
 * Reset all DKS states
 */
void dks_reset_states(void) {
    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            dks_state_t* state = &dks_states[row][col];

            // Release any active keycodes
            if (state->is_dks_key && state->active_keycodes) {
                const dks_slot_t* slot = &dks_slots[state->dks_slot];

                // Release press actions
                for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
                    if (state->active_keycodes & (1 << i)) {
                        unregister_code16(slot->press_keycode[i]);
                    }
                }

                // Release release actions
                for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
                    if (state->active_keycodes & (1 << (i + 4))) {
                        unregister_code16(slot->release_keycode[i]);
                    }
                }
            }

            // Clear state
            state->press_triggered = 0;
            state->release_triggered = 0;
            state->active_keycodes = 0;
            state->last_travel = 0;
            state->max_travel = 0;
            state->key_was_down = false;
            state->release_pending = false;
        }
    }
}

// ============================================================================
// Slot Access Functions
// ============================================================================

const dks_slot_t* dks_get_slot(uint8_t slot) {
    if (slot >= DKS_NUM_SLOTS) {
        return NULL;
    }
    return &dks_slots[slot];
}

void dks_set_slot(uint8_t slot, const dks_slot_t* config) {
    if (slot >= DKS_NUM_SLOTS || config == NULL) {
        return;
    }
    memcpy(&dks_slots[slot], config, sizeof(dks_slot_t));
}

// ============================================================================
// Core DKS Processing Logic
// ============================================================================

/**
 * Trigger a DKS action
 */
static void trigger_action(uint16_t keycode, dks_behavior_t behavior, uint8_t action_bit) {
    if (keycode == KC_NO) {
        return;  // Disabled action
    }

    switch (behavior) {
        case DKS_BEHAVIOR_TAP:
            // Send press and release immediately
            tap_code16(keycode);
            break;

        case DKS_BEHAVIOR_PRESS:
            // Send press and hold
            register_code16(keycode);
            break;

        case DKS_BEHAVIOR_RELEASE:
            // Send release only
            unregister_code16(keycode);
            break;

        default:
            break;
    }
}

/**
 * Release a held action (for PRESS behavior)
 */
static void release_action(uint16_t keycode, dks_behavior_t behavior) {
    if (keycode == KC_NO) {
        return;
    }

    if (behavior == DKS_BEHAVIOR_PRESS) {
        unregister_code16(keycode);
    }
    // TAP and RELEASE don't need cleanup
}

/**
 * Process press actions (downstroke)
 */
static void process_press_actions(dks_state_t* state, const dks_slot_t* slot, uint8_t travel) {
    for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
        // Skip if already triggered
        if (state->press_triggered & (1 << i)) {
            continue;
        }

        // Skip if keycode is disabled
        if (slot->press_keycode[i] == KC_NO) {
            continue;
        }

        // Convert actuation point to travel units
        uint8_t threshold = actuation_to_travel(slot->press_actuation[i]);

        // Check if we crossed threshold (going down)
        if (state->last_travel < threshold && travel >= threshold) {
            // Trigger this action!
            dks_behavior_t behavior = dks_get_behavior(slot, i);
            trigger_action(slot->press_keycode[i], behavior, i);

            // Mark as triggered
            state->press_triggered |= (1 << i);

            // Track if it's active (for PRESS behavior release later)
            if (behavior == DKS_BEHAVIOR_PRESS) {
                state->active_keycodes |= (1 << i);
            }
        }
    }
}

/**
 * Process release actions (upstroke) - rate-limited to ONE action per scan
 *
 * On fast upstroke, travel can jump a large distance in a single scan cycle
 * (e.g., 240→20), crossing multiple release thresholds simultaneously.
 * If all actions fire in the same scan, tap_code16 calls happen within
 * microseconds and the ChibiOS USB endpoint buffer gets overwritten before
 * the host polls - causing missed keystrokes and wrong ordering.
 *
 * Fix: fire only the highest-threshold unfired action per scan cycle.
 * This matches the physical upstroke crossing order (highest threshold is
 * crossed first) and gives USB ~1ms between each action to transmit.
 *
 * Uses max_travel (peak travel during this press cycle) instead of
 * last_travel to validate that the key actually reached the threshold
 * depth. This prevents false triggering when the key bounces during
 * release or when release_pending re-enters on a stationary key.
 *
 * Returns true if an action was fired (caller should check release_pending).
 */
static bool process_release_actions(dks_state_t* state, const dks_slot_t* slot, uint8_t travel) {
    // Find the unfired action with the HIGHEST threshold that travel is now below.
    // This ensures correct physical ordering regardless of how indices are arranged.
    int8_t best_idx = -1;
    uint8_t best_threshold = 0;

    for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
        if (state->release_triggered & (1 << i)) {
            continue;
        }
        if (slot->release_keycode[i] == KC_NO) {
            continue;
        }

        uint8_t threshold = actuation_to_travel(slot->release_actuation[i]);

        // Key must have actually reached this depth (max_travel >= threshold)
        // and travel must now be below it
        if (state->max_travel >= threshold && travel < threshold) {
            if (threshold > best_threshold) {
                best_threshold = threshold;
                best_idx = i;
            }
        }
    }

    if (best_idx < 0) {
        state->release_pending = false;
        return false;
    }

    // Fire the selected action
    dks_behavior_t behavior = dks_get_behavior(slot, best_idx + 4);
    trigger_action(slot->release_keycode[best_idx], behavior, best_idx + 4);
    state->release_triggered |= (1 << best_idx);
    if (behavior == DKS_BEHAVIOR_PRESS) {
        state->active_keycodes |= (1 << (best_idx + 4));
    }

    // Check if more actions are still pending below current travel
    state->release_pending = false;
    for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
        if (state->release_triggered & (1 << i)) {
            continue;
        }
        if (slot->release_keycode[i] == KC_NO) {
            continue;
        }
        uint8_t threshold = actuation_to_travel(slot->release_actuation[i]);
        if (state->max_travel >= threshold && travel < threshold) {
            state->release_pending = true;
            break;
        }
    }

    return true;
}

/**
 * Release any press actions that are going back up past their threshold
 */
static void cleanup_press_actions(dks_state_t* state, const dks_slot_t* slot, uint8_t travel) {
    for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
        // Skip if not triggered or not active
        if (!(state->press_triggered & (1 << i))) {
            continue;
        }
        if (!(state->active_keycodes & (1 << i))) {
            continue;
        }

        // Convert actuation point to travel units
        uint8_t threshold = actuation_to_travel(slot->press_actuation[i]);

        // If travel went back below threshold, release it
        if (travel < threshold) {
            dks_behavior_t behavior = dks_get_behavior(slot, i);
            release_action(slot->press_keycode[i], behavior);

            // Clear triggered and active flags
            state->press_triggered &= ~(1 << i);
            state->active_keycodes &= ~(1 << i);
        }
    }
}

/**
 * Main DKS processing function
 * Called from matrix scanning for each DKS key
 */
void dks_process_key(uint8_t row, uint8_t col, uint8_t travel, uint16_t keycode) {
    if (!dks_initialized) {
        return;
    }

    // Validate row/col
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) {
        return;
    }

    // Get slot number from keycode
    uint8_t slot_num = dks_keycode_to_slot(keycode);
    if (slot_num >= DKS_NUM_SLOTS) {
        return;
    }

    // Get state and configuration
    dks_state_t* state = &dks_states[row][col];
    const dks_slot_t* slot = &dks_slots[slot_num];

    // Initialize state if this is the first time seeing this key
    if (!state->is_dks_key) {
        state->is_dks_key = true;
        state->dks_slot = slot_num;
        state->last_travel = travel;
        state->max_travel = 0;
        state->press_triggered = 0;
        state->release_triggered = 0;
        state->active_keycodes = 0;
        state->key_was_down = false;
        state->release_pending = false;
        return;  // Skip processing on first detection
    }

    // Update slot if keycode changed
    if (state->dks_slot != slot_num) {
        // Release any active actions from old slot
        dks_reset_states();
        state->is_dks_key = true;
        state->dks_slot = slot_num;
    }

    // Track peak travel during this press cycle (for release threshold validation)
    if (travel > state->max_travel) {
        state->max_travel = travel;
    }

    // Determine direction
    bool going_down = (travel > state->last_travel);
    bool going_up = (travel < state->last_travel);

    // Detect full press/release for state reset
    bool key_is_down = (travel > actuation_to_travel(5));  // Consider "down" if > 0.125mm

    // Process based on direction.
    // release_pending: continue firing deferred release actions even when
    // the key is stationary (going_up would be false if key isn't moving).
    if (going_down) {
        // New press direction cancels any pending releases
        state->release_pending = false;
        process_press_actions(state, slot, travel);
    } else if (going_up || state->release_pending) {
        process_release_actions(state, slot, travel);
        // Only clean up press actions when all releases are done,
        // to avoid interleaving press cleanup with release firing.
        if (!state->release_pending) {
            cleanup_press_actions(state, slot, travel);
        }
    }

    // Full release - reset triggered flags AFTER processing.
    // Defer the reset if release actions are still pending (rate-limited),
    // otherwise the bitmask would be cleared before deferred actions fire.
    if (state->key_was_down && !key_is_down && !state->release_pending) {
        state->press_triggered = 0;
        state->release_triggered = 0;
        state->max_travel = 0;
        // Keep active_keycodes to track held PRESS actions
    }

    // Update state
    state->last_travel = travel;
    state->key_was_down = key_is_down;
}

// ============================================================================
// Debug Functions
// ============================================================================

#ifdef DKS_DEBUG
#include <stdio.h>

void dks_print_slot(uint8_t slot) {
    if (slot >= DKS_NUM_SLOTS) {
        printf("DKS: Invalid slot %d\n", slot);
        return;
    }

    const dks_slot_t* s = &dks_slots[slot];
    printf("DKS Slot %d:\n", slot);
    printf("  Press actions:\n");
    for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
        printf("    [%d] KC=0x%04X Act=%d Beh=%d\n",
               i, s->press_keycode[i], s->press_actuation[i], dks_get_behavior(s, i));
    }
    printf("  Release actions:\n");
    for (uint8_t i = 0; i < DKS_ACTIONS_PER_STAGE; i++) {
        printf("    [%d] KC=0x%04X Act=%d Beh=%d\n",
               i, s->release_keycode[i], s->release_actuation[i], dks_get_behavior(s, i + 4));
    }
}

void dks_print_state(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) {
        printf("DKS: Invalid position %d,%d\n", row, col);
        return;
    }

    const dks_state_t* state = &dks_states[row][col];
    printf("DKS State [%d,%d]:\n", row, col);
    printf("  is_dks=%d slot=%d travel=%d\n", state->is_dks_key, state->dks_slot, state->last_travel);
    printf("  press_trig=0x%02X rel_trig=0x%02X active=0x%04X\n",
           state->press_triggered, state->release_triggered, state->active_keycodes);
}
#endif
