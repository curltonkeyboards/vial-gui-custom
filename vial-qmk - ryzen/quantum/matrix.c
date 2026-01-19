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
#include "distance_lut.h"

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
// aftertouch_mode and aftertouch_cc are now per-layer (in layer_actuations)
extern uint8_t channel_number;
extern layer_actuation_t layer_actuations[12];
extern bool aftertouch_pedal_active;
extern layer_key_actuations_t per_key_actuations[12];
// NOTE: per_key_per_layer_enabled removed - firmware always uses per-key per-layer

// Keysplit/transpose variables for aftertouch channel determination
extern uint8_t keysplitchannel;
extern uint8_t keysplit2channel;
extern uint8_t keysplitstatus;
extern int8_t transpose_number;
extern int8_t octave_number;

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
    bool velocity_captured;      // True when velocity has been captured for this press

    // Mode 2 & 3: Speed-based
    uint8_t last_travel;
    uint16_t last_time;
    uint8_t calculated_velocity;
    uint8_t peak_velocity;
    uint8_t peak_speed;          // Peak instantaneous speed (for apex detection)
    uint8_t travel_at_actuation; // Travel when actuation point was crossed (for Mode 2)

    // Mode 3: Speed threshold
    bool speed_threshold_met;
    uint8_t speed_samples[4];
    uint8_t speed_sample_idx;

    // Raw velocity for curve application (0-255)
    uint8_t raw_velocity;        // Raw velocity value before curve/scaling

    // Aftertouch
    uint8_t last_aftertouch;
    uint8_t note_channel;        // Channel this note was sent on (for poly aftertouch)
    uint8_t midi_note;           // Actual MIDI note number (for poly aftertouch)

    // Vibrato decay tracking
    uint8_t vibrato_value;       // Current vibrato value (for decay)
    uint16_t vibrato_last_time;  // Last time vibrato was updated (for decay calculation)
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
    // Per-layer aftertouch settings
    uint8_t aftertouch_mode;
    uint8_t aftertouch_cc;
    uint8_t vibrato_sensitivity;
    uint16_t vibrato_decay_time;
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
// DISTANCE CALCULATION (libhmk style with LUT linearization)
// ============================================================================

// Global LUT correction strength (defined in orthomidi5x14.c, declared in process_dynamic_macro.h)
// 0 = linear (no correction), 100 = full logarithmic LUT correction

static inline uint8_t adc_to_distance(uint16_t adc, uint16_t rest, uint16_t bottom) {
    // Use the LUT-corrected distance calculation with global strength setting
    // This compensates for Hall effect sensor non-linearity
    return adc_to_distance_corrected(adc, rest, bottom, lut_correction_strength);
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
        // Per-layer aftertouch settings
        active_settings.aftertouch_mode = layer_actuations[current_layer].aftertouch_mode;
        active_settings.aftertouch_cc = layer_actuations[current_layer].aftertouch_cc;
        active_settings.vibrato_sensitivity = layer_actuations[current_layer].vibrato_sensitivity;
        active_settings.vibrato_decay_time = layer_actuations[current_layer].vibrato_decay_time;
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

    // Always use per-key per-layer settings - firmware always reads from current layer
    per_key_actuation_t *settings = &per_key_actuations[layer].keys[key_idx];

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

__attribute__((unused))
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

__attribute__((unused))
static void save_calibration_to_eeprom(void) {
    // TODO: Implement EEPROM save for calibration
    // For now, just mark as clean
    calibration_dirty = false;
}

// ============================================================================
// RT STATE MACHINE (libhmk 3-state FSM)
// ============================================================================

__attribute__((unused))
static void process_rapid_trigger(uint32_t key_idx, uint8_t current_layer) {
    key_state_t *key = &key_matrix[key_idx];

    // DEBUG Step 7e: Test actuation_to_distance() without array access
    // Use default actuation value (20 = 2.0mm), don't access per_key_actuations
    uint8_t actuation_point = actuation_to_distance(DEFAULT_ACTUATION_VALUE);

    // Simple threshold mode only
    key->is_pressed = (key->distance >= actuation_point);
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
// MIDI KEY ANALOG PROCESSING
// ============================================================================

__attribute__((unused))
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

    // Get per-key settings for velocity modification (used by RT)
    per_key_actuation_t *per_key_settings = &per_key_actuations[current_layer].keys[key_idx];

    // ========================================================================
    // VELOCITY MODE PROCESSING
    // All modes store raw_velocity (0-255) for curve application later
    // ========================================================================

    switch (analog_mode) {
        case 0:  // Fixed velocity
            // raw_velocity stays at default (will be handled by get_he_velocity_from_position)
            state->raw_velocity = 255;  // Max raw value, curve will determine actual velocity
            break;

        case 1:  // Peak Travel at Apex
            // Measures peak travel distance, captures velocity when speed drastically slows
            // Ignores actuation point - just uses deadzone to avoid misstriggers
            {
                uint16_t time_delta = now - state->last_time;
                uint8_t travel_delta = (travel > state->last_travel) ? (travel - state->last_travel) : 0;

                // Calculate current instantaneous speed (travel units per ms * 100 for precision)
                uint8_t current_speed = (time_delta > 0) ? ((travel_delta * 100) / time_delta) : 0;

                // Track peak speed during descent
                if (current_speed > state->peak_speed) {
                    state->peak_speed = current_speed;
                }

                // Track peak travel during descent
                if (travel > state->peak_travel) {
                    state->peak_travel = travel;
                }

                // Detect fast movement started
                if (current_speed >= SPEED_TRIGGER_THRESHOLD) {
                    state->speed_threshold_met = true;
                }

                // Apex detection: speed has dropped significantly from peak (drastic slowing)
                // Capture velocity when:
                // 1. We've seen fast movement (speed_threshold_met)
                // 2. Current speed has dropped below threshold (apex reached)
                // 3. We haven't already captured for this press
                // 4. Key has moved past deadzone (travel > 0 means past deadzone)
                if (state->speed_threshold_met &&
                    current_speed < SPEED_TRIGGER_THRESHOLD &&
                    travel > 0 &&
                    !state->velocity_captured) {

                    // Store raw velocity as normalized peak travel (0-255)
                    // peak_travel is in 0-240 range, scale to 0-255
                    state->raw_velocity = (state->peak_travel * 255) / 240;
                    state->velocity_captured = true;

                    // Also update base_velocity for RT accumulation (scaled to 1-127 for now)
                    key->base_velocity = (state->raw_velocity * 127) / 255;
                    if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
                }

                // On release, reset tracking state
                if (state->was_pressed && !pressed) {
                    state->peak_travel = 0;
                    state->peak_speed = 0;
                    state->speed_threshold_met = false;
                    state->velocity_captured = false;
                }

                state->last_travel = travel;
                state->last_time = now;
            }
            break;

        case 2:  // Speed-based (deadzone to actuation)
            // Measures average speed from key release/deadzone to actuation point
            // Deeper actuation point = more travel distance = more reliable speed measurement
            {
                uint16_t time_delta = now - state->last_time;

                // Track when key starts moving from rest (crosses deadzone)
                if (state->last_travel == 0 && travel > 0) {
                    // Key just started moving - record start time
                    state->last_time = now;
                    state->travel_at_actuation = 0;
                    state->velocity_captured = false;
                }

                // Capture velocity when actuation point is crossed
                if (!state->velocity_captured && travel >= midi_threshold && state->last_travel < midi_threshold) {
                    // Calculate average speed from deadzone to actuation
                    // time_delta = time from when key started moving
                    // travel at actuation = midi_threshold
                    if (time_delta > 0) {
                        // Speed = distance / time, normalize to 0-255
                        // midi_threshold is typically 80-200 (in 0-240 range)
                        // Scale speed to give good dynamic range
                        uint32_t avg_speed = ((uint32_t)midi_threshold * 1000) / time_delta;

                        // Scale speed to 0-255 range
                        // Typical fast press: ~50-100 travel units in 20-50ms = ~2000-5000 units/sec
                        // Scale factor adjusts sensitivity
                        uint32_t raw = (avg_speed * active_settings.velocity_speed_scale) / 100;
                        if (raw > 255) raw = 255;

                        state->raw_velocity = (uint8_t)raw;
                        state->velocity_captured = true;

                        // Update base_velocity for RT
                        key->base_velocity = (state->raw_velocity * 127) / 255;
                        if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
                    } else {
                        // Instant press - max velocity
                        state->raw_velocity = 255;
                        state->velocity_captured = true;
                        key->base_velocity = MAX_VELOCITY;
                    }
                }

                // On release, reset
                if (state->was_pressed && !pressed) {
                    state->velocity_captured = false;
                    state->travel_at_actuation = 0;
                }

                state->last_travel = travel;
                // Only update last_time if key is at rest (for next press measurement)
                if (travel == 0) {
                    state->last_time = now;
                }
            }
            break;

        case 3:  // Speed + Peak Combined
            // Measures both speed and peak travel until apex (drastic slowing)
            // Blends speed (70%) and peak travel (30%) for final velocity
            {
                uint16_t time_delta = now - state->last_time;
                uint8_t travel_delta = (travel > state->last_travel) ? (travel - state->last_travel) : 0;

                // Calculate current instantaneous speed
                uint8_t current_speed = (time_delta > 0) ? ((travel_delta * 100) / time_delta) : 0;

                // Track peak speed during descent
                if (current_speed > state->peak_speed) {
                    state->peak_speed = current_speed;
                }

                // Track peak travel during descent
                if (travel > state->peak_travel) {
                    state->peak_travel = travel;
                }

                // Detect fast movement started
                if (current_speed >= SPEED_TRIGGER_THRESHOLD) {
                    state->speed_threshold_met = true;
                }

                // Apex detection: speed has dropped significantly
                if (state->speed_threshold_met &&
                    current_speed < SPEED_TRIGGER_THRESHOLD &&
                    travel > 0 &&
                    !state->velocity_captured) {

                    // Calculate speed component (0-255)
                    // peak_speed is in travel_units*100/ms, scale to 0-255
                    uint32_t speed_raw = ((uint32_t)state->peak_speed * active_settings.velocity_speed_scale) / 10;
                    if (speed_raw > 255) speed_raw = 255;

                    // Calculate travel component (0-255)
                    uint8_t travel_raw = (state->peak_travel * 255) / 240;

                    // Blend: 70% speed + 30% travel
                    state->raw_velocity = (uint8_t)(((uint16_t)speed_raw * 70 + (uint16_t)travel_raw * 30) / 100);
                    state->velocity_captured = true;

                    // Update base_velocity for RT
                    key->base_velocity = (state->raw_velocity * 127) / 255;
                    if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
                }

                // On release, reset
                if (state->was_pressed && !pressed) {
                    state->peak_travel = 0;
                    state->peak_speed = 0;
                    state->speed_threshold_met = false;
                    state->velocity_captured = false;
                }

                state->last_travel = travel;
                state->last_time = now;
            }
            break;
    }

    // ========================================================================
    // RT VELOCITY ACCUMULATION
    // Applies velocity modifier on rapid trigger re-presses
    // ========================================================================
    if (key->key_dir != KEY_DIR_INACTIVE && pressed && !state->was_pressed && state->velocity_captured) {
        // RT re-trigger with existing velocity - accumulate modifier
        int16_t new_raw = state->raw_velocity + (per_key_settings->rapidfire_velocity_mod * 2);  // Scale modifier to 0-255 range
        if (new_raw < 0) new_raw = 0;
        if (new_raw > 255) new_raw = 255;
        state->raw_velocity = (uint8_t)new_raw;

        // Update base_velocity to match
        key->base_velocity = (state->raw_velocity * 127) / 255;
        if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
    }

    // Capture channel and MIDI note when note first becomes pressed
    if (pressed && !state->was_pressed) {
        // Determine channel and MIDI note based on keycode
        uint8_t row = KEY_ROW(key_idx);
        uint8_t col = KEY_COL(key_idx);
        uint16_t keycode = dynamic_keymap_get_keycode(current_layer, row, col);

        // Determine channel based on keycode range
        if (keycode >= 0xC600 && keycode <= 0xC647) {
            // Keysplit note - use keysplitchannel if keysplit is enabled
            state->note_channel = (keysplitstatus == 1 || keysplitstatus == 3) ? keysplitchannel : channel_number;
        } else if (keycode >= 0xC670 && keycode <= 0xC6B7) {
            // Triplesplit note - use keysplit2channel if triplesplit is enabled
            state->note_channel = (keysplitstatus == 2 || keysplitstatus == 3) ? keysplit2channel : channel_number;
        } else {
            // Base note or other - use base channel
            state->note_channel = channel_number;
        }

        // Compute actual MIDI note: note_index + transpose + octave + 24
        state->midi_note = state->note_index + transpose_number + octave_number + 24;

        // Clamp to valid MIDI range
        if (state->midi_note > 127) state->midi_note = 127;
    }

    // Aftertouch handling - now sends polyphonic aftertouch + optional CC
    // Uses per-layer settings from active_settings
    if (active_settings.aftertouch_mode > 0 && pressed) {
        uint8_t aftertouch_value = 0;
        bool send_aftertouch = false;

        uint8_t normal_threshold = (active_settings.normal_actuation * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100;

        switch (active_settings.aftertouch_mode) {
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

            case 4:  // Vibrato with sensitivity and decay
                if (travel >= normal_threshold) {
                    uint16_t time_delta = now - state->last_time;
                    uint8_t travel_delta = abs((int)travel - (int)state->last_travel);

                    // Calculate new vibrato value from movement
                    uint8_t new_vibrato = 0;
                    if (time_delta > 0 && travel_delta > 0) {
                        // Apply sensitivity scaling (50-200, where 100 = normal)
                        uint16_t sensitivity = active_settings.vibrato_sensitivity;
                        if (sensitivity < 50) sensitivity = 50;
                        if (sensitivity > 200) sensitivity = 200;

                        // movement_speed with sensitivity: (travel_delta * sensitivity) / time_delta
                        uint16_t movement_speed = ((uint16_t)travel_delta * sensitivity) / time_delta;
                        new_vibrato = (movement_speed > 127) ? 127 : (uint8_t)movement_speed;
                    }

                    // Apply decay to current vibrato value
                    uint16_t decay_time = active_settings.vibrato_decay_time;
                    if (decay_time > 0 && state->vibrato_value > 0) {
                        // Calculate how much to decay based on time elapsed
                        uint16_t decay_elapsed = now - state->vibrato_last_time;
                        // Linear decay: reduce by (127 * elapsed_ms / decay_time) per cycle
                        uint16_t decay_amount = ((uint32_t)127 * decay_elapsed) / decay_time;
                        if (decay_amount >= state->vibrato_value) {
                            state->vibrato_value = 0;
                        } else {
                            state->vibrato_value -= decay_amount;
                        }
                    } else if (decay_time == 0) {
                        // Instant decay when no movement
                        if (new_vibrato == 0) {
                            state->vibrato_value = 0;
                        }
                    }

                    // Take the max of new vibrato and decayed value
                    if (new_vibrato > state->vibrato_value) {
                        state->vibrato_value = new_vibrato;
                    }

                    state->vibrato_last_time = now;
                    aftertouch_value = state->vibrato_value;
                    send_aftertouch = true;
                } else {
                    // Below threshold - decay to zero
                    state->vibrato_value = 0;
                    state->vibrato_last_time = now;
                }
                break;
        }

        if (send_aftertouch && abs((int)aftertouch_value - (int)state->last_aftertouch) > 2) {
            #ifdef MIDI_ENABLE
            // Always send polyphonic aftertouch (per-note pressure)
            midi_send_aftertouch(&midi_device, state->note_channel, state->midi_note, aftertouch_value);

            // Optionally also send CC if aftertouch_cc is not "off" (255)
            if (active_settings.aftertouch_cc != 255) {
                midi_send_cc(&midi_device, state->note_channel, active_settings.aftertouch_cc, aftertouch_value);
            }

            state->last_aftertouch = aftertouch_value;
            #endif
        }
    } else if (!pressed && state->was_pressed) {
        // Key released - send aftertouch reset (value 0) for all modes
        if (active_settings.aftertouch_mode > 0 && state->last_aftertouch > 0) {
            #ifdef MIDI_ENABLE
            midi_send_aftertouch(&midi_device, state->note_channel, state->midi_note, 0);
            if (active_settings.aftertouch_cc != 255) {
                midi_send_cc(&midi_device, state->note_channel, active_settings.aftertouch_cc, 0);
            }
            #endif
        }
        state->last_aftertouch = 0;
        state->vibrato_value = 0;
    }
}

__attribute__((unused))
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
    // DEBUG Step 7: Add rapid trigger processing back
    // Testing if RT causes the issue

    if (!analog_initialized) return;

    // Get current layer for RT processing
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    if (current_layer >= 12) current_layer = 0;

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

            // 1. Apply EMA filter
            key->adc_filtered = EMA(raw_value, key->adc_filtered);

            // 2. Update calibration
            update_calibration(key_idx);

            // 3. Calculate distance
            key->distance = adc_to_distance(key->adc_filtered,
                                            key->adc_rest_value,
                                            key->adc_bottom_out_value);

            // 4. RT processing (re-enabled)
            process_rapid_trigger(key_idx, current_layer);
        }

        unselect_column();
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

    // DEBUG Step 2: Re-enable ADC init, keep scanning disabled
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

    // DEBUG Step 3: Re-enable warm-up loop, keep continuous scanning disabled
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

    // Run analog matrix scan
    analog_matrix_task_internal();

    // DEBUG Step 7: Use RT is_pressed state for key detection
    // Still no MIDI, DKS, or null bind processing
    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        matrix_row_t current_row_value = 0;

        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            uint32_t key_idx = KEY_INDEX(row, col);
            key_state_t *key = &key_matrix[key_idx];

            // Use RT is_pressed state
            if (key->is_pressed) {
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

// Get raw velocity value (0-255) for curve application
// This is the pre-calculated velocity from velocity modes 1-3
uint8_t analog_matrix_get_velocity_raw(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return midi_key_states[key_idx].raw_velocity;
}

// Get current velocity mode for a key's layer
uint8_t analog_matrix_get_velocity_mode(void) {
    return active_settings.velocity_mode;
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
    if (cached_layer >= 12) return;  // Bounds check for layer

    uint8_t key_idx = row * MATRIX_COLS + col;
    if (key_idx >= 70) return;

    if (point == 0) point = DEFAULT_ACTUATION_VALUE;

    // Always update current layer - firmware is always per-key per-layer
    per_key_actuations[cached_layer].keys[key_idx].actuation = point;
}

void analog_matrix_set_rapid_trigger(uint8_t row, uint8_t col, uint8_t sensitivity) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;
    if (cached_layer >= 12) return;  // Bounds check for layer

    uint8_t key_idx = row * MATRIX_COLS + col;
    if (key_idx >= 70) return;

    // Always update current layer - firmware is always per-key per-layer
    if (sensitivity == 0) {
        // Disable rapid trigger
        per_key_actuations[cached_layer].keys[key_idx].flags &= ~PER_KEY_FLAG_RAPIDFIRE_ENABLED;
    } else {
        // Enable rapid trigger with given sensitivity
        per_key_actuations[cached_layer].keys[key_idx].flags |= PER_KEY_FLAG_RAPIDFIRE_ENABLED;
        per_key_actuations[cached_layer].keys[key_idx].rapidfire_press_sens = sensitivity;
        per_key_actuations[cached_layer].keys[key_idx].rapidfire_release_sens = sensitivity;
    }
}

void analog_matrix_set_key_mode(uint8_t row, uint8_t col, uint8_t mode) {
    // Deprecated in new architecture - RT is always per-key
    // Mode is now controlled via per_key_actuations[].flags
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;
    if (cached_layer >= 12) return;  // Bounds check for layer

    uint8_t key_idx = row * MATRIX_COLS + col;
    if (key_idx >= 70) return;

    // Always update current layer - firmware is always per-key per-layer
    if (mode == AKM_RAPID) {
        per_key_actuations[cached_layer].keys[key_idx].flags |= PER_KEY_FLAG_RAPIDFIRE_ENABLED;
    } else {
        per_key_actuations[cached_layer].keys[key_idx].flags &= ~PER_KEY_FLAG_RAPIDFIRE_ENABLED;
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
