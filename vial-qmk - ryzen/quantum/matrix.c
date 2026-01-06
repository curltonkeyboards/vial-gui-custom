/* Copyright 2024 Your Name
 *
 * libhmk-inspired Analog Matrix Implementation for QMK with MIDI Velocity
 * Architecture migration: Flat arrays, EMA filtering, 3-state RT FSM
 */

#include "quantum.h"
#include "matrix.h"
#include "debounce.h"
#include "wait.h"
#include "hal.h"
#include "gpio.h"
#include <string.h>
#include <stdlib.h>

#ifdef MIDI_ENABLE
#include "midi.h"
#include "process_midi.h"
#include "qmk_midi.h"
#endif

#include "process_keycode/process_dks.h"
#include "dynamic_keymap.h"

// ============================================================================
// CONSTANTS (libhmk-inspired)
// ============================================================================

#define NUM_KEYS (MATRIX_ROWS * MATRIX_COLS)  // 70 for 5x14 matrix
#define KEY_INDEX(row, col) ((row) * MATRIX_COLS + (col))
#define KEY_ROW(idx) ((idx) / MATRIX_COLS)
#define KEY_COL(idx) ((idx) % MATRIX_COLS)

// EMA filter: alpha = 1/16 = 0.0625
#define MATRIX_EMA_ALPHA_EXPONENT 4
#define EMA(x, y) \
    (((uint32_t)(x) + ((uint32_t)(y) * ((1 << MATRIX_EMA_ALPHA_EXPONENT) - 1))) >> \
     MATRIX_EMA_ALPHA_EXPONENT)

#define CALIBRATION_EPSILON 5
#define INACTIVITY_TIMEOUT_MS 3000

// Distance scale (0-255 for libhmk compatibility)
#define DISTANCE_MAX 255

// Conversion: old travel (0-240) to new distance (0-255)
#define TRAVEL_TO_DISTANCE(t) (((uint32_t)(t) * 255) / 240)
#define DISTANCE_TO_TRAVEL(d) (((uint32_t)(d) * 240) / 255)

// ============================================================================
// EXTERNAL DECLARATIONS
// ============================================================================

extern uint8_t (*optimized_midi_positions)[72][6];
extern uint8_t (*optimized_midi_velocities)[72];
extern uint8_t layer_to_index_map[12];
extern uint8_t ACTUAL_MIDI_LAYERS;
extern uint8_t aftertouch_mode;
extern uint8_t aftertouch_cc;
extern uint8_t channel_number;
extern layer_actuation_t layer_actuations[12];
extern bool aftertouch_pedal_active;
extern layer_key_actuations_t per_key_actuations[12];
extern bool per_key_per_layer_enabled;

// Speed threshold for modes 1 & 3 (travel units per millisecond)
#define SPEED_TRIGGER_THRESHOLD 20

// Key direction enum (key_dir_t) is defined in matrix.h

// ============================================================================
// UNIFIED KEY STATE (replaces analog_key_t + calibration_t)
// ============================================================================

typedef struct {
    // ADC state (with EMA filtering)
    uint16_t adc_filtered;          // EMA-filtered ADC value
    uint16_t adc_rest_value;        // Calibrated rest position
    uint16_t adc_bottom_out_value;  // Calibrated bottom-out position

    // Distance (0-255 scale, libhmk style)
    uint8_t distance;

    // RT state machine (libhmk 3-state)
    uint8_t extremum;               // Peak (DOWN) or trough (UP) position
    key_dir_t key_dir;              // Current direction state
    bool is_pressed;                // Logical pressed state for matrix
    bool calibrated;                // Whether this key has been calibrated

    // MIDI velocity (kept from orthomidi5x14)
    uint8_t base_velocity;          // For RT velocity accumulation

    // Calibration tracking
    uint16_t last_adc_value;        // For stability detection
    uint32_t stable_time;           // When key became stable
    bool is_stable;                 // Key is at stable position
} key_state_t;

// ============================================================================
// MIDI KEY STATE (kept from orthomidi5x14)
// ============================================================================

typedef struct {
    bool is_midi_key;
    uint8_t note_index;
    bool pressed;
    bool was_pressed;

    // Mode 1: Peak travel at apex
    uint8_t peak_travel;
    bool send_on_release;

    // Mode 2 & 3: Speed-based
    uint8_t last_travel;
    uint16_t last_time;
    uint8_t calculated_velocity;
    uint8_t peak_velocity;

    // Mode 3: Speed threshold
    bool speed_threshold_met;
    uint8_t speed_samples[4];
    uint8_t speed_sample_idx;

    // Aftertouch
    uint8_t last_aftertouch;
} midi_key_state_t;

// ============================================================================
// STATIC VARIABLES
// ============================================================================

// Single flat array (libhmk style)
static key_state_t key_matrix[NUM_KEYS];

// MIDI state tracking (kept from orthomidi5x14)
static midi_key_state_t midi_key_states[NUM_KEYS];

// Initialization flags
static bool analog_initialized = false;
static bool midi_states_initialized = false;

// Calibration auto-save tracking
static uint32_t last_calibration_change = 0;
static bool calibration_dirty = false;

// Layer caching (libhmk style optimization)
static uint8_t cached_layer = 0xFF;
static uint8_t cached_layer_settings_layer = 0xFF;

// Cached layer settings for hot path
static struct {
    uint8_t normal_actuation;
    uint8_t midi_actuation;
    uint8_t velocity_mode;
    uint8_t velocity_speed_scale;
} active_settings;

// ADC configuration
#define ADC_GRP_NUM_CHANNELS MATRIX_ROWS
#define ADC_GRP_BUF_DEPTH 1
static adcsample_t samples[ADC_GRP_NUM_CHANNELS * ADC_GRP_BUF_DEPTH];

static pin_t row_pins[MATRIX_ROWS] = MATRIX_ROW_PINS;

matrix_row_t raw_matrix[MATRIX_ROWS];
matrix_row_t matrix[MATRIX_ROWS];

// ============================================================================
// VELOCITY CALCULATION CONSTANTS
// ============================================================================

#define VELOCITY_SCALE 10
#define MIN_VELOCITY 1
#define MAX_VELOCITY 127
#define RELEASE_THRESHOLD 50
#define SPEED_THRESHOLD 15

// ============================================================================
// ADC CONFIGURATION
// ============================================================================

static void adcerrorcallback(ADCDriver *adcp, adcerror_t err) {
    (void)adcp;
    (void)err;
}

static ADCConversionGroup adcgrpcfg = {
    FALSE,
    ADC_GRP_NUM_CHANNELS,
    NULL,
    adcerrorcallback,
    0,
    ADC_CR2_SWSTART,
    0,
    0,
    0,
    0,
    0,
    0,
    0
};

// ============================================================================
// HARDWARE HELPER FUNCTIONS
// ============================================================================

static uint8_t pin_to_adc_channel(pin_t pin) {
    switch (pin) {
        case A0:  return ADC_CHANNEL_IN0;
        case A1:  return ADC_CHANNEL_IN1;
        case A2:  return ADC_CHANNEL_IN2;
        case A3:  return ADC_CHANNEL_IN3;
        case A4:  return ADC_CHANNEL_IN4;
        case A5:  return ADC_CHANNEL_IN5;
        case A6:  return ADC_CHANNEL_IN6;
        case A7:  return ADC_CHANNEL_IN7;
        case B0:  return ADC_CHANNEL_IN8;
        case B1:  return ADC_CHANNEL_IN9;
        case C0:  return ADC_CHANNEL_IN10;
        case C1:  return ADC_CHANNEL_IN11;
        case C2:  return ADC_CHANNEL_IN12;
        case C3:  return ADC_CHANNEL_IN13;
        case C4:  return ADC_CHANNEL_IN14;
        case C5:  return ADC_CHANNEL_IN15;
    }
    return 0xFF;
}

static void select_column(uint8_t col) {
    if (col >= 16) return;

    writePin(ADG706_A0, col & 0x01);
    writePin(ADG706_A1, col & 0x02);
    writePin(ADG706_A2, col & 0x04);
    writePin(ADG706_A3, col & 0x08);

    if (ADG706_EN != NO_PIN) {
        writePinLow(ADG706_EN);
    }
}

static void unselect_column(void) {
    if (ADG706_EN != NO_PIN) {
        writePinHigh(ADG706_EN);
    }
}

// ============================================================================
// DISTANCE CALCULATION (libhmk style)
// ============================================================================

static inline uint8_t adc_to_distance(uint16_t adc, uint16_t rest, uint16_t bottom) {
    // Handle inverted ADC (rest > bottom for Hall Effect)
    if (rest > bottom) {
        // Hall effect: higher ADC = less pressed
        if (adc >= rest) return 0;
        if (adc <= bottom) return DISTANCE_MAX;
        return ((uint32_t)(rest - adc) * DISTANCE_MAX) / (rest - bottom);
    } else {
        // Normal case: higher ADC = more pressed
        if (adc <= rest) return 0;
        if (adc >= bottom) return DISTANCE_MAX;
        return ((uint32_t)(adc - rest) * DISTANCE_MAX) / (bottom - rest);
    }
}

// Convert actuation point from 0-100 scale to 0-255 distance
static inline uint8_t actuation_to_distance(uint8_t actuation) {
    return (uint8_t)(((uint32_t)actuation * DISTANCE_MAX) / 100);
}

// Convert distance to old travel scale (for backward compatibility with DKS/MIDI)
static inline uint8_t distance_to_travel_compat(uint8_t distance) {
    // Old scale: 0-240 (FULL_TRAVEL_UNIT * TRAVEL_SCALE)
    return (uint8_t)(((uint32_t)distance * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / DISTANCE_MAX);
}

// ============================================================================
// LAYER SETTINGS CACHE
// ============================================================================

void analog_matrix_refresh_settings(void) {
    cached_layer_settings_layer = 0xFF;  // Force refresh
}

static inline void update_active_settings(uint8_t current_layer) {
    if (current_layer >= 12) current_layer = 0;

    if (cached_layer_settings_layer != current_layer) {
        active_settings.normal_actuation = layer_actuations[current_layer].normal_actuation;
        active_settings.midi_actuation = layer_actuations[current_layer].midi_actuation;
        active_settings.velocity_mode = layer_actuations[current_layer].velocity_mode;
        active_settings.velocity_speed_scale = layer_actuations[current_layer].velocity_speed_scale;
        cached_layer_settings_layer = current_layer;
    }
}

// ============================================================================
// PER-KEY ACTUATION LOOKUP (always per-key, layer-aware)
// ============================================================================

static inline void get_key_actuation_config(uint32_t key_idx, uint8_t layer,
                                            uint8_t *actuation_point,
                                            uint8_t *rt_down,
                                            uint8_t *rt_up,
                                            uint8_t *flags) {
    if (key_idx >= NUM_KEYS || layer >= 12) {
        *actuation_point = actuation_to_distance(DEFAULT_ACTUATION_VALUE);
        *rt_down = 0;
        *rt_up = 0;
        *flags = 0;
        return;
    }

    // Always use per-key settings (no more mode toggle)
    uint8_t target_layer = per_key_per_layer_enabled ? layer : 0;
    per_key_actuation_t *settings = &per_key_actuations[target_layer].keys[key_idx];

    // Convert from 0-100 scale to 0-255 distance
    *actuation_point = actuation_to_distance(settings->actuation);

    // RT sensitivity: convert from 0-100 scale to 0-255 distance
    if (settings->flags & PER_KEY_FLAG_RAPIDFIRE_ENABLED) {
        *rt_down = actuation_to_distance(settings->rapidfire_press_sens);
        *rt_up = actuation_to_distance(settings->rapidfire_release_sens);
    } else {
        *rt_down = 0;  // RT disabled
        *rt_up = 0;
    }

    *flags = settings->flags;
}

// ============================================================================
// CALIBRATION FUNCTIONS (libhmk style continuous calibration)
// ============================================================================

static void update_calibration(uint32_t key_idx) {
    key_state_t *key = &key_matrix[key_idx];
    uint32_t now = timer_read32();

    // Stability detection
    if (abs((int)key->adc_filtered - (int)key->last_adc_value) < AUTO_CALIB_ZERO_TRAVEL_JITTER) {
        if (!key->is_stable) {
            key->is_stable = true;
            key->stable_time = now;
        }
    } else {
        key->is_stable = false;
    }

    // Auto-calibrate rest position when stable and not pressed
    if (key->is_stable && !key->is_pressed &&
        timer_elapsed32(key->stable_time) > AUTO_CALIB_VALID_RELEASE_TIME) {
        // For Hall effect sensors: rest value is typically higher ADC
        if (key->adc_filtered > key->adc_rest_value + AUTO_CALIB_ZERO_TRAVEL_JITTER ||
            key->adc_filtered < key->adc_rest_value - AUTO_CALIB_ZERO_TRAVEL_JITTER) {
            key->adc_rest_value = key->adc_filtered;
            calibration_dirty = true;
            last_calibration_change = timer_read();
        }
    }

    // Continuous bottom-out calibration (libhmk style)
    // For Hall effect: bottom is lower ADC value
    if (key->adc_rest_value > key->adc_bottom_out_value) {
        // Hall effect inverted
        if (key->adc_filtered < key->adc_bottom_out_value - CALIBRATION_EPSILON) {
            key->adc_bottom_out_value = key->adc_filtered;
            key->calibrated = true;
            calibration_dirty = true;
            last_calibration_change = timer_read();
        }
    } else {
        // Normal orientation
        if (key->adc_filtered > key->adc_bottom_out_value + CALIBRATION_EPSILON) {
            key->adc_bottom_out_value = key->adc_filtered;
            key->calibrated = true;
            calibration_dirty = true;
            last_calibration_change = timer_read();
        }
    }

    key->last_adc_value = key->adc_filtered;
}

static void save_calibration_to_eeprom(void) {
    // TODO: Implement EEPROM save for calibration
    // For now, just mark as clean
    calibration_dirty = false;
}

// ============================================================================
// RT STATE MACHINE (libhmk 3-state FSM)
// ============================================================================

static void process_rapid_trigger(uint32_t key_idx, uint8_t current_layer) {
    key_state_t *key = &key_matrix[key_idx];

    // Get per-key actuation config
    uint8_t actuation_point, rt_down, rt_up, flags;
    get_key_actuation_config(key_idx, current_layer,
                            &actuation_point, &rt_down, &rt_up, &flags);

    // Determine reset point (continuous mode = 0, normal = actuation_point)
    // Note: continuous RT uses flag bit 0 in the new system
    // For compatibility, we check the rapidfire flag
    uint8_t reset_point = actuation_point;  // Normal mode: reset at actuation

    if (rt_down == 0) {
        // RT disabled - simple threshold mode
        bool was_pressed = key->is_pressed;
        key->is_pressed = (key->distance >= actuation_point);
        key->key_dir = KEY_DIR_INACTIVE;

        // Velocity capture on initial press (for MIDI)
        if (key->is_pressed && !was_pressed) {
            key->base_velocity = 0;  // Will be calculated by MIDI processor
        }
    } else {
        // RT enabled - libhmk 3-state FSM
        if (rt_up == 0) rt_up = rt_down;  // Symmetric if not specified

        switch (key->key_dir) {
            case KEY_DIR_INACTIVE:
                if (key->distance > actuation_point) {
                    // Initial press
                    key->extremum = key->distance;
                    key->key_dir = KEY_DIR_DOWN;
                    key->is_pressed = true;
                    key->base_velocity = 0;  // Reset for new press cycle
                }
                break;

            case KEY_DIR_DOWN:
                if (key->distance <= reset_point) {
                    // Full release to inactive
                    key->extremum = key->distance;
                    key->key_dir = KEY_DIR_INACTIVE;
                    key->is_pressed = false;
                    key->base_velocity = 0;
                } else if (key->distance + rt_up < key->extremum) {
                    // RT release (moved up by rt_up from peak)
                    key->extremum = key->distance;
                    key->key_dir = KEY_DIR_UP;
                    key->is_pressed = false;
                } else if (key->distance > key->extremum) {
                    // Track deeper press
                    key->extremum = key->distance;
                }
                break;

            case KEY_DIR_UP:
                if (key->distance <= reset_point) {
                    // Full release to inactive
                    key->extremum = key->distance;
                    key->key_dir = KEY_DIR_INACTIVE;
                    key->is_pressed = false;
                    key->base_velocity = 0;
                } else if (key->extremum + rt_down < key->distance) {
                    // RT re-press (moved down by rt_down from trough)
                    key->extremum = key->distance;
                    key->key_dir = KEY_DIR_DOWN;
                    key->is_pressed = true;
                } else if (key->distance < key->extremum) {
                    // Track higher release
                    key->extremum = key->distance;
                }
                break;
        }
    }
}

// ============================================================================
// MIDI KEY DETECTION
// ============================================================================

static bool check_is_midi_key(uint8_t row, uint8_t col, uint8_t *note_index_out) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    if (current_layer >= 12) return false;

    uint8_t array_index = layer_to_index_map[current_layer];
    if (array_index == 255) return false;

    if (optimized_midi_positions == NULL) return false;

    uint8_t led_index = g_led_config.matrix_co[row][col];

    for (uint8_t note = 0; note < 72; note++) {
        for (uint8_t pos = 0; pos < 6; pos++) {
            if (optimized_midi_positions[array_index][note][pos] == led_index) {
                *note_index_out = note;
                return true;
            }
        }
    }

    return false;
}

// ============================================================================
// VELOCITY CALCULATION
// ============================================================================

static uint8_t calculate_speed_velocity(uint8_t travel_delta, uint16_t time_delta) {
    if (time_delta == 0) return 64;

    uint32_t speed = ((uint32_t)travel_delta * 1000) / time_delta;
    uint8_t velocity = (speed * active_settings.velocity_speed_scale) / 100;

    if (velocity < MIN_VELOCITY) velocity = MIN_VELOCITY;
    if (velocity > MAX_VELOCITY) velocity = MAX_VELOCITY;

    return velocity;
}

static void store_midi_velocity(uint8_t note_index, uint8_t velocity) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    if (current_layer >= 12) return;

    uint8_t array_index = layer_to_index_map[current_layer];
    if (array_index == 255 || array_index >= ACTUAL_MIDI_LAYERS) return;

    if (optimized_midi_velocities == NULL) return;
    if (note_index >= 72) return;

    optimized_midi_velocities[array_index][note_index] = velocity;
}

// ============================================================================
// MIDI KEY ANALOG PROCESSING
// ============================================================================

static void process_midi_key_analog(uint32_t key_idx, uint8_t current_layer) {
    midi_key_state_t *state = &midi_key_states[key_idx];
    key_state_t *key = &key_matrix[key_idx];

    // Convert distance to old travel format for compatibility
    uint8_t travel = distance_to_travel_compat(key->distance);
    bool pressed = key->is_pressed;
    uint16_t now = timer_read();

    // Use cached settings
    uint8_t midi_threshold = (active_settings.midi_actuation * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100;
    uint8_t analog_mode = active_settings.velocity_mode;

    state->was_pressed = state->pressed;
    state->pressed = pressed;

    // Handle RT velocity accumulation
    if (key->key_dir != KEY_DIR_INACTIVE) {
        // Get per-key settings for velocity modification
        per_key_actuation_t *settings = &per_key_actuations[per_key_per_layer_enabled ? current_layer : 0].keys[key_idx];

        // Initial press - calculate base velocity
        if (pressed && !state->was_pressed && key->base_velocity == 0) {
            uint16_t time_delta = now - state->last_time;
            uint8_t travel_delta = (travel > state->last_travel) ? (travel - state->last_travel) : 0;

            switch (analog_mode) {
                case 0:  // Fixed
                    key->base_velocity = 64;
                    break;
                case 2:  // Speed-based
                    key->base_velocity = calculate_speed_velocity(travel_delta, time_delta);
                    break;
                default:
                    key->base_velocity = 64;
                    break;
            }
            store_midi_velocity(state->note_index, key->base_velocity);
        }
        // RT re-trigger - accumulate velocity
        else if (pressed && !state->was_pressed && key->base_velocity > 0) {
            int16_t new_velocity = key->base_velocity + settings->rapidfire_velocity_mod;

            if (new_velocity < MIN_VELOCITY) new_velocity = MIN_VELOCITY;
            if (new_velocity > MAX_VELOCITY) new_velocity = MAX_VELOCITY;

            key->base_velocity = (uint8_t)new_velocity;
            store_midi_velocity(state->note_index, key->base_velocity);
        }
    }

    // Standard velocity modes
    switch (analog_mode) {
        case 0:  // Fixed
            break;

        case 1:  // Peak travel at apex
            {
                uint16_t time_delta = now - state->last_time;
                uint8_t travel_delta = (travel > state->last_travel) ? (travel - state->last_travel) : 0;

                uint8_t current_speed = (time_delta > 0) ? ((travel_delta * 100) / time_delta) : 0;

                if (current_speed >= SPEED_TRIGGER_THRESHOLD) {
                    state->speed_threshold_met = true;
                }

                if (travel > state->peak_travel) {
                    state->peak_travel = travel;
                }

                if (state->speed_threshold_met &&
                    current_speed < SPEED_TRIGGER_THRESHOLD &&
                    travel >= midi_threshold &&
                    !state->send_on_release) {

                    uint8_t velocity = (state->peak_travel * 127) / 240;
                    if (velocity < MIN_VELOCITY) velocity = MIN_VELOCITY;
                    if (velocity > MAX_VELOCITY) velocity = MAX_VELOCITY;

                    store_midi_velocity(state->note_index, velocity);
                    state->send_on_release = true;
                    key->base_velocity = velocity;
                }

                if (state->was_pressed && !pressed) {
                    state->peak_travel = 0;
                    state->speed_threshold_met = false;
                    state->send_on_release = false;
                }

                state->last_travel = travel;
                state->last_time = now;
            }
            break;

        case 2:  // Speed-based
            if (pressed && !state->was_pressed && key->key_dir == KEY_DIR_INACTIVE) {
                // Only on initial press (not RT re-trigger)
                uint16_t time_delta = now - state->last_time;
                uint8_t travel_delta = (travel > state->last_travel) ? (travel - state->last_travel) : 0;

                uint8_t velocity = calculate_speed_velocity(travel_delta, time_delta);
                store_midi_velocity(state->note_index, velocity);
                state->calculated_velocity = velocity;
                key->base_velocity = velocity;
            }

            state->last_travel = travel;
            state->last_time = now;
            break;

        case 3:  // Speed + peak combined
            {
                uint16_t time_delta = now - state->last_time;
                uint8_t travel_delta = (travel > state->last_travel) ? (travel - state->last_travel) : 0;

                uint8_t current_speed = (time_delta > 0) ? ((travel_delta * 100) / time_delta) : 0;
                uint8_t speed_velocity = calculate_speed_velocity(travel_delta, time_delta);

                if (speed_velocity > state->peak_velocity) {
                    state->peak_velocity = speed_velocity;
                }

                if (travel > state->peak_travel) {
                    state->peak_travel = travel;
                }

                if (current_speed >= SPEED_TRIGGER_THRESHOLD) {
                    state->speed_threshold_met = true;
                }

                if (state->speed_threshold_met &&
                    current_speed < SPEED_TRIGGER_THRESHOLD &&
                    travel >= midi_threshold &&
                    !state->send_on_release) {

                    uint8_t travel_vel = (state->peak_travel * 127) / 240;
                    uint8_t final_velocity = (state->peak_velocity * 70 + travel_vel * 30) / 100;

                    if (final_velocity < MIN_VELOCITY) final_velocity = MIN_VELOCITY;
                    if (final_velocity > MAX_VELOCITY) final_velocity = MAX_VELOCITY;

                    store_midi_velocity(state->note_index, final_velocity);
                    state->send_on_release = true;
                    key->base_velocity = final_velocity;
                }

                if (state->was_pressed && !pressed) {
                    state->speed_threshold_met = false;
                    state->peak_velocity = 0;
                    state->peak_travel = 0;
                    state->send_on_release = false;
                }

                state->last_travel = travel;
                state->last_time = now;
            }
            break;
    }

    // Aftertouch handling
    if (aftertouch_mode > 0 && pressed) {
        uint8_t aftertouch_value = 0;
        bool send_aftertouch = false;

        uint8_t normal_threshold = (active_settings.normal_actuation * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100;

        switch (aftertouch_mode) {
            case 1:  // Reverse
                if (aftertouch_pedal_active) {
                    aftertouch_value = 127 - ((travel * 127) / 240);
                    send_aftertouch = true;
                }
                break;

            case 2:  // Bottom-out
                if (aftertouch_pedal_active) {
                    aftertouch_value = (travel * 127) / 240;
                    send_aftertouch = true;
                }
                break;

            case 3:  // Post-actuation
                if (travel >= normal_threshold) {
                    uint8_t additional_travel = travel - normal_threshold;
                    uint8_t range = 240 - normal_threshold;
                    if (range > 0) {
                        aftertouch_value = (additional_travel * 127) / range;
                        send_aftertouch = true;
                    }
                }
                break;

            case 4:  // Vibrato
                if (travel >= normal_threshold) {
                    uint16_t time_delta = now - state->last_time;
                    uint8_t travel_delta = abs((int)travel - (int)state->last_travel);

                    if (time_delta > 0 && travel_delta > 0) {
                        uint8_t movement_speed = (travel_delta * 100) / time_delta;
                        aftertouch_value = (movement_speed > 127) ? 127 : movement_speed;
                        send_aftertouch = true;
                    }
                }
                break;
        }

        if (send_aftertouch && abs((int)aftertouch_value - (int)state->last_aftertouch) > 2) {
            #ifdef MIDI_ENABLE
            midi_send_cc(&midi_device, channel_number, aftertouch_cc, aftertouch_value);
            state->last_aftertouch = aftertouch_value;
            #endif
        }
    } else if (!pressed) {
        state->last_aftertouch = 0;
    }
}

static void initialize_midi_states(void) {
    if (midi_states_initialized) return;

    memset(midi_key_states, 0, sizeof(midi_key_states));

    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            uint32_t key_idx = KEY_INDEX(row, col);
            uint8_t note_index;
            if (check_is_midi_key(row, col, &note_index)) {
                midi_key_states[key_idx].is_midi_key = true;
                midi_key_states[key_idx].note_index = note_index;
            }
        }
    }

    midi_states_initialized = true;
}

// ============================================================================
// ANALOG MATRIX TASK (INTERNAL) - libhmk style scan
// ============================================================================

static void analog_matrix_task_internal(void) {
    if (!analog_initialized) return;

    // Get current layer ONCE per scan
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);

    // Update layer cache
    if (current_layer != cached_layer) {
        cached_layer = current_layer;
    }
    update_active_settings(current_layer);

    // Scan by column (hardware-optimized)
    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
        select_column(col);
        wait_us(40);

        adcConvert(&ADCD1, &adcgrpcfg, samples, ADC_GRP_BUF_DEPTH);

        for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
            uint32_t key_idx = KEY_INDEX(row, col);
            key_state_t *key = &key_matrix[key_idx];
            uint16_t raw_value = samples[row];

            // 1. Apply EMA filter (libhmk style)
            key->adc_filtered = EMA(raw_value, key->adc_filtered);

            // 2. Update calibration (continuous)
            update_calibration(key_idx);

            // 3. Calculate distance (0-255)
            key->distance = adc_to_distance(key->adc_filtered,
                                            key->adc_rest_value,
                                            key->adc_bottom_out_value);

            // 4. Process RT state machine
            process_rapid_trigger(key_idx, current_layer);
        }

        unselect_column();
    }

    // Auto-save calibration after inactivity
    if (calibration_dirty && timer_elapsed(last_calibration_change) >= INACTIVITY_TIMEOUT_MS) {
        save_calibration_to_eeprom();
    }
}

// ============================================================================
// QMK CUSTOM MATRIX IMPLEMENTATION
// ============================================================================

void matrix_init_custom(void) {
    if (analog_initialized) return;

    // Initialize mux pins
    setPinOutput(ADG706_A0);
    setPinOutput(ADG706_A1);
    setPinOutput(ADG706_A2);
    setPinOutput(ADG706_A3);

    if (ADG706_EN != NO_PIN) {
        setPinOutput(ADG706_EN);
        writePinHigh(ADG706_EN);
    }

    writePinLow(ADG706_A0);
    writePinLow(ADG706_A1);
    writePinLow(ADG706_A2);
    writePinLow(ADG706_A3);

    // Configure ADC
    uint32_t smpr[2] = {0, 0};
    uint32_t sqr[3] = {0, 0, 0};
    uint8_t chn_cnt = 0;

    for (uint8_t x = 0; x < MATRIX_ROWS; x++) {
        if (row_pins[x] != NO_PIN) {
            palSetLineMode(row_pins[x], PAL_MODE_INPUT_ANALOG);

            uint8_t chn = pin_to_adc_channel(row_pins[x]);
            if (chn < 0xFF) {
                if (chn > 9) {
                    smpr[0] |= ADC_SAMPLE_56 << ((chn - 10) * 3);
                } else {
                    smpr[1] |= ADC_SAMPLE_56 << (chn * 3);
                }
                sqr[chn_cnt / 6] |= chn << ((chn_cnt % 6) * 5);
                chn_cnt++;
            }
        }
    }

    adcgrpcfg.smpr1 = smpr[0];
    adcgrpcfg.smpr2 = smpr[1];
    adcgrpcfg.sqr3 = sqr[0];
    adcgrpcfg.sqr2 = sqr[1];
    adcgrpcfg.sqr1 = sqr[2];
    adcgrpcfg.num_channels = chn_cnt;

    adcStart(&ADCD1, NULL);

    SYSCFG->PMC |= SYSCFG_PMC_ADC1DC2;

    // Initialize all keys (flat array)
    for (uint32_t i = 0; i < NUM_KEYS; i++) {
        key_state_t *key = &key_matrix[i];

        // ADC/calibration defaults
        key->adc_filtered = DEFAULT_ZERO_TRAVEL_VALUE;
        key->adc_rest_value = DEFAULT_ZERO_TRAVEL_VALUE;
        key->adc_bottom_out_value = DEFAULT_ZERO_TRAVEL_VALUE - DEFAULT_FULL_RANGE;

        // State defaults
        key->distance = 0;
        key->extremum = 0;
        key->key_dir = KEY_DIR_INACTIVE;
        key->is_pressed = false;
        key->calibrated = false;

        // MIDI
        key->base_velocity = 0;

        // Calibration tracking
        key->last_adc_value = DEFAULT_ZERO_TRAVEL_VALUE;
        key->stable_time = 0;
        key->is_stable = false;
    }

    // Initialize matrix arrays
    for (uint8_t i = 0; i < MATRIX_ROWS; i++) {
        raw_matrix[i] = 0;
        matrix[i] = 0;
    }

    // Warm up ADC
    for (uint8_t i = 0; i < 5; i++) {
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            select_column(col);
            wait_us(40);
            adcConvert(&ADCD1, &adcgrpcfg, samples, ADC_GRP_BUF_DEPTH);

            // Initialize EMA with first readings
            for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
                uint32_t key_idx = KEY_INDEX(row, col);
                key_matrix[key_idx].adc_filtered = samples[row];
                key_matrix[key_idx].adc_rest_value = samples[row];
            }

            unselect_column();
        }
    }

    analog_initialized = true;

    // Initialize DKS system
    dks_init();
}

bool matrix_scan_custom(matrix_row_t current_matrix[]) {
    bool changed = false;

    // Initialize MIDI states if needed
    if (!midi_states_initialized && optimized_midi_positions != NULL) {
        initialize_midi_states();
    }

    // Run analog matrix scan
    analog_matrix_task_internal();

    // Get current layer
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    if (current_layer >= 12) current_layer = 0;

    // Process MIDI keys
    if (midi_states_initialized && active_settings.velocity_mode > 0) {
        for (uint32_t i = 0; i < NUM_KEYS; i++) {
            if (midi_key_states[i].is_midi_key) {
                process_midi_key_analog(i, current_layer);
            }
        }
    }

    // Process DKS keys
    for (uint32_t i = 0; i < NUM_KEYS; i++) {
        uint8_t row = KEY_ROW(i);
        uint8_t col = KEY_COL(i);
        uint16_t keycode = dynamic_keymap_get_keycode(current_layer, row, col);

        if (is_dks_keycode(keycode)) {
            // Convert distance to travel for DKS (backward compatibility)
            uint8_t travel = distance_to_travel_compat(key_matrix[i].distance);
            dks_process_key(row, col, travel, keycode);
        }
    }

    // Build matrix from key states
    uint8_t midi_threshold = (active_settings.midi_actuation * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100;
    uint8_t analog_mode = active_settings.velocity_mode;

    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        matrix_row_t current_row_value = 0;

        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            uint32_t key_idx = KEY_INDEX(row, col);
            key_state_t *key = &key_matrix[key_idx];
            bool pressed = false;

            // Check if this is a DKS key
            uint16_t keycode = dynamic_keymap_get_keycode(current_layer, row, col);
            bool is_dks = is_dks_keycode(keycode);

            if (is_dks) {
                // DKS keys handle their own keycodes internally
                pressed = false;
            } else if (midi_key_states[key_idx].is_midi_key) {
                midi_key_state_t *state = &midi_key_states[key_idx];
                uint8_t travel = distance_to_travel_compat(key->distance);

                switch (analog_mode) {
                    case 0:  // Fixed
                        pressed = key->is_pressed && (travel >= midi_threshold);
                        break;
                    case 1:  // Peak
                        pressed = state->send_on_release;
                        break;
                    case 2:  // Speed
                        pressed = (travel >= midi_threshold) && state->calculated_velocity > 0;
                        break;
                    case 3:  // Speed+Peak
                        pressed = state->send_on_release;
                        break;
                }

                if ((aftertouch_mode == 1 || aftertouch_mode == 2) &&
                    aftertouch_pedal_active && state->was_pressed) {
                    pressed = true;
                }
            } else {
                // Normal key - use RT state
                pressed = key->is_pressed;
            }

            if (pressed) {
                current_row_value |= (MATRIX_ROW_SHIFTER << col);
            }
        }

        if (current_matrix[row] != current_row_value) {
            current_matrix[row] = current_row_value;
            changed = true;
        }
    }

    return changed;
}

// ============================================================================
// PUBLIC API FUNCTIONS
// ============================================================================

void analog_matrix_init(void) {
    matrix_init_custom();
}

void analog_matrix_task(void) {
    analog_matrix_task_internal();
}

uint8_t analog_matrix_get_travel(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    // Convert distance to old travel format
    return distance_to_travel_compat(key_matrix[key_idx].distance);
}

uint8_t analog_matrix_get_travel_normalized(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].distance;  // Already 0-255
}

bool analog_matrix_get_key_state(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return false;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].is_pressed;
}

uint16_t analog_matrix_get_raw_value(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].adc_filtered;
}

bool analog_matrix_is_calibrated(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return false;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].calibrated;
}

bool analog_matrix_calibrating(void) {
    for (uint32_t i = 0; i < NUM_KEYS; i++) {
        if (!key_matrix[i].calibrated) return true;
    }
    return false;
}

void analog_matrix_set_actuation_point(uint8_t row, uint8_t col, uint8_t point) {
    // In the new architecture, actuation is per-key in per_key_actuations[]
    // This function updates the per-key setting
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;

    uint8_t key_idx = row * MATRIX_COLS + col;
    if (key_idx >= 70) return;

    if (point == 0) point = DEFAULT_ACTUATION_VALUE;

    // Update all layers (or just current layer based on per_key_per_layer_enabled)
    uint8_t target_layer = per_key_per_layer_enabled ? cached_layer : 0;
    per_key_actuations[target_layer].keys[key_idx].actuation = point;
}

void analog_matrix_set_rapid_trigger(uint8_t row, uint8_t col, uint8_t sensitivity) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;

    uint8_t key_idx = row * MATRIX_COLS + col;
    if (key_idx >= 70) return;

    uint8_t target_layer = per_key_per_layer_enabled ? cached_layer : 0;

    if (sensitivity == 0) {
        // Disable rapid trigger
        per_key_actuations[target_layer].keys[key_idx].flags &= ~PER_KEY_FLAG_RAPIDFIRE_ENABLED;
    } else {
        // Enable rapid trigger with given sensitivity
        per_key_actuations[target_layer].keys[key_idx].flags |= PER_KEY_FLAG_RAPIDFIRE_ENABLED;
        per_key_actuations[target_layer].keys[key_idx].rapidfire_press_sens = sensitivity;
        per_key_actuations[target_layer].keys[key_idx].rapidfire_release_sens = sensitivity;
    }
}

void analog_matrix_set_key_mode(uint8_t row, uint8_t col, uint8_t mode) {
    // Deprecated in new architecture - RT is always per-key
    // Mode is now controlled via per_key_actuations[].flags
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;

    uint8_t key_idx = row * MATRIX_COLS + col;
    if (key_idx >= 70) return;

    uint8_t target_layer = per_key_per_layer_enabled ? cached_layer : 0;

    if (mode == AKM_RAPID) {
        per_key_actuations[target_layer].keys[key_idx].flags |= PER_KEY_FLAG_RAPIDFIRE_ENABLED;
    } else {
        per_key_actuations[target_layer].keys[key_idx].flags &= ~PER_KEY_FLAG_RAPIDFIRE_ENABLED;
    }
}

void analog_matrix_reset_calibration(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;
    uint32_t key_idx = KEY_INDEX(row, col);
    key_state_t *key = &key_matrix[key_idx];

    key->calibrated = false;
    key->adc_rest_value = DEFAULT_ZERO_TRAVEL_VALUE;
    key->adc_bottom_out_value = DEFAULT_ZERO_TRAVEL_VALUE - DEFAULT_FULL_RANGE;
}

void analog_matrix_reset_all_calibration(void) {
    for (uint32_t i = 0; i < NUM_KEYS; i++) {
        key_state_t *key = &key_matrix[i];
        key->calibrated = false;
        key->adc_rest_value = DEFAULT_ZERO_TRAVEL_VALUE;
        key->adc_bottom_out_value = DEFAULT_ZERO_TRAVEL_VALUE - DEFAULT_FULL_RANGE;
    }
}

// ============================================================================
// NEW PUBLIC API FUNCTIONS (libhmk style)
// ============================================================================

// Get key distance (0-255)
uint8_t analog_matrix_get_distance(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].distance;
}

// Get RT direction state
uint8_t analog_matrix_get_key_direction(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return KEY_DIR_INACTIVE;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].key_dir;
}

// Get RT extremum value
uint8_t analog_matrix_get_extremum(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].extremum;
}

// Get filtered ADC value
uint16_t analog_matrix_get_filtered_adc(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].adc_filtered;
}
