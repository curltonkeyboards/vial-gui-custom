/* Copyright 2024 Your Name
 *
 * Complete Analog Matrix Implementation for QMK with MIDI Velocity
 * CPU-Optimized Version with Cached Layer Settings
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

// Speed threshold for modes 1 & 3 (travel units per millisecond)
#define SPEED_TRIGGER_THRESHOLD 20

// ============================================================================
// CACHED ACTIVE LAYER SETTINGS (CPU-optimized hot path)
// ============================================================================

static struct {
    uint8_t normal_actuation;
    uint8_t midi_actuation;
    uint8_t velocity_mode;
    uint8_t velocity_speed_scale;
    uint8_t cached_layer;
    bool needs_update;
} active_settings = {
    .normal_actuation = 80,
    .midi_actuation = 80,
    .velocity_mode = 2,
    .velocity_speed_scale = 10,
    .cached_layer = 0,
    .needs_update = true
};

// Call this when layer actuations are loaded/changed
void analog_matrix_refresh_settings(void) {
    active_settings.needs_update = true;
}

static inline void update_active_settings(uint8_t current_layer) {
    if (current_layer >= 12) current_layer = 0;

    if (active_settings.cached_layer != current_layer || active_settings.needs_update) {
        active_settings.normal_actuation = layer_actuations[current_layer].normal_actuation;
        active_settings.midi_actuation = layer_actuations[current_layer].midi_actuation;
        active_settings.velocity_mode = layer_actuations[current_layer].velocity_mode;
        active_settings.velocity_speed_scale = layer_actuations[current_layer].velocity_speed_scale;
        active_settings.cached_layer = current_layer;
        active_settings.needs_update = false;
    }
}

// ============================================================================
// INTERNAL DATA STRUCTURES
// ============================================================================

typedef struct {
    uint16_t zero_travel;
    uint16_t full_travel;
} calibration_value_t;

typedef struct {
    bool     calibrated;
    bool     pressed;
    bool     stable;
    uint32_t stable_time;
    uint32_t press_time;
    uint16_t last_value;
    calibration_value_t value;
} calibration_t;

typedef struct {
    uint8_t  actn_pt;
    uint8_t  deactn_pt;
} threshold_t;

typedef struct {
    uint8_t mode;
    uint8_t state;
    uint8_t  travel;
    uint8_t  last_travel;
    uint16_t raw_value;
    threshold_t regular;
    threshold_t rapid;
    uint8_t act_pt;
    uint8_t rpd_trig_sen;
    uint8_t rpd_trig_sen_release;

    // Per-key rapid trigger state
    uint8_t base_velocity;        // Stored first-press velocity for RT
    bool rapid_cycle_active;      // Flag: in rapid trigger mode
    bool awaiting_release;        // Flag: waiting for release_sens
    uint8_t last_direction;       // 0=none, 1=up, 2=down
} analog_key_t;

// MIDI key state tracking for analog velocity
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

static analog_key_t  keys[MATRIX_ROWS][MATRIX_COLS];
static calibration_t calibration[MATRIX_ROWS][MATRIX_COLS];
static midi_key_state_t midi_key_states[MATRIX_ROWS][MATRIX_COLS];
static bool          analog_initialized = false;
static bool          midi_states_initialized = false;

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
// CALIBRATION FUNCTIONS
// ============================================================================

static void update_calibration(uint8_t row, uint8_t col, uint16_t raw_value) {
    calibration_t *cal = &calibration[row][col];
    analog_key_t  *key = &keys[row][col];
    uint32_t now = timer_read32();
    
    if (abs(raw_value - cal->last_value) < AUTO_CALIB_ZERO_TRAVEL_JITTER) {
        if (!cal->stable) {
            cal->stable = true;
            cal->stable_time = now;
        }
    } else {
        cal->stable = false;
    }
    
    if (cal->stable && !cal->pressed && 
        timer_elapsed32(cal->stable_time) > AUTO_CALIB_VALID_RELEASE_TIME) {
        if (!cal->calibrated || abs(raw_value - cal->value.zero_travel) > AUTO_CALIB_ZERO_TRAVEL_JITTER) {
            cal->value.zero_travel = raw_value;
        }
    }
    
    if (key->travel > (BOTTOM_DEAD_ZONE * TRAVEL_SCALE - 10)) {
        if (!cal->pressed) {
            cal->pressed = true;
            cal->press_time = now;
        }
        if (timer_elapsed32(cal->press_time) > 100 && cal->stable) {
            if (!cal->calibrated || abs(raw_value - cal->value.full_travel) > AUTO_CALIB_FULL_TRAVEL_JITTER) {
                cal->value.full_travel = raw_value;
                cal->calibrated = true;
            }
        }
    } else {
        cal->pressed = false;
    }
    
    cal->last_value = raw_value;
}

// ============================================================================
// TRAVEL CALCULATION
// ============================================================================

static uint8_t calculate_travel(uint8_t row, uint8_t col, uint16_t raw_value) {
    calibration_t *cal = &calibration[row][col];
    
    uint16_t zero_val, full_val, range;
    
    if (cal->calibrated) {
        zero_val = cal->value.zero_travel;
        full_val = cal->value.full_travel;
    } else {
        zero_val = DEFAULT_ZERO_TRAVEL_VALUE;
        full_val = DEFAULT_ZERO_TRAVEL_VALUE - DEFAULT_FULL_RANGE;
    }
    
    if (raw_value > zero_val) raw_value = zero_val;
    if (raw_value < full_val) raw_value = full_val;
    
    range = zero_val - full_val;
    if (range == 0) return 0;
    
    uint32_t travel = ((uint32_t)(zero_val - raw_value) * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / range;
    
    if (travel < ZERO_TRAVEL_DEAD_ZONE * TRAVEL_SCALE) {
        travel = 0;
    } else if (travel > BOTTOM_DEAD_ZONE * TRAVEL_SCALE) {
        travel = FULL_TRAVEL_UNIT * TRAVEL_SCALE;
    }
    
    return (uint8_t)travel;
}

// ============================================================================
// STATE MACHINE
// ============================================================================

static bool process_key_state(analog_key_t *key) {
    bool changed = false;
    
    if (key->travel != key->last_travel) {
        switch (key->mode) {
            case AKM_REGULAR:
                if (key->state == AKS_REGULAR_RELEASED) {
                    if (key->travel >= key->regular.actn_pt) {
                        key->state = AKS_REGULAR_PRESSED;
                        changed = true;
                    }
                } else {
                    if (key->travel <= key->regular.deactn_pt) {
                        key->state = AKS_REGULAR_RELEASED;
                        changed = true;
                    }
                }
                break;
                
            case AKM_RAPID:
                if (key->state == AKS_RAPID_RELEASED) {
                    if (key->travel >= key->rapid.actn_pt && 
                        key->travel > ZERO_TRAVEL_DEAD_ZONE * TRAVEL_SCALE) {
                        key->state = AKS_RAPID_PRESSED;
                        changed = true;
                        key->rapid.actn_pt = key->travel;
                        key->rapid.deactn_pt = key->travel > key->rpd_trig_sen_release ? 
                                              key->travel - key->rpd_trig_sen_release : 0;
                    } else if (key->travel < key->rapid.deactn_pt) {
                        key->rapid.actn_pt = key->travel + key->rpd_trig_sen;
                        key->rapid.deactn_pt = key->travel;
                    }
                } else {
                    if (key->travel <= key->regular.deactn_pt && 
                        key->travel < ZERO_TRAVEL_DEAD_ZONE * TRAVEL_SCALE + key->rpd_trig_sen) {
                        key->state = AKS_REGULAR_RELEASED;
                        changed = true;
                    } else if (key->travel <= key->rapid.deactn_pt && 
                              key->travel < BOTTOM_DEAD_ZONE * TRAVEL_SCALE - key->rpd_trig_sen_release) {
                        key->state = AKS_RAPID_RELEASED;
                        changed = true;
                        key->rapid.deactn_pt = key->travel;
                        key->rapid.actn_pt = key->travel + key->rpd_trig_sen;
                    } else if (key->travel > key->rapid.actn_pt) {
                        key->rapid.deactn_pt = key->travel > key->rpd_trig_sen_release ? 
                                              key->travel - key->rpd_trig_sen_release : 0;
                        key->rapid.actn_pt = key->travel;
                    }
                }
                break;
        }
    }
    
    key->last_travel = key->travel;
    return changed;
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
// VELOCITY CALCULATION (CPU-OPTIMIZED)
// ============================================================================

static uint8_t calculate_speed_velocity(uint8_t travel_delta, uint16_t time_delta) {
    if (time_delta == 0) return 64;
    
    uint32_t speed = ((uint32_t)travel_delta * 1000) / time_delta;
    uint8_t velocity = (speed * active_settings.velocity_speed_scale) / 100;
    
    if (velocity < MIN_VELOCITY) velocity = MIN_VELOCITY;
    if (velocity > MAX_VELOCITY) velocity = MAX_VELOCITY;
    
    return velocity;
}

// Helper: Check if travel is in deadzone (top or bottom)
// deadzone values are 0-100 scale (0-2.5mm), converted to 0-240 travel units
static inline bool is_in_deadzone(uint8_t travel, uint8_t deadzone_top, uint8_t deadzone_bottom) {
    // Convert deadzone from 0-100 scale to 0-240 travel units
    // Formula: travel_units = (deadzone * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100 = (deadzone * 240) / 100
    uint8_t top_threshold = (deadzone_top * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100;
    uint8_t bottom_threshold = (FULL_TRAVEL_UNIT * TRAVEL_SCALE) - ((deadzone_bottom * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100);

    // Top deadzone: 0 to top_threshold
    if (travel <= top_threshold) return true;

    // Bottom deadzone: bottom_threshold to max (240)
    if (travel >= bottom_threshold) return true;

    return false;
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
// MIDI KEY ANALOG PROCESSING (CPU-OPTIMIZED)
// ============================================================================

static void process_midi_key_analog(uint8_t row, uint8_t col) {
    midi_key_state_t *state = &midi_key_states[row][col];
    analog_key_t *key = &keys[row][col];
    
    uint8_t travel = key->travel;
    bool pressed = (key->state == AKS_REGULAR_PRESSED || key->state == AKS_RAPID_PRESSED);
    uint16_t now = timer_read();
    
    // Use cached settings - no array lookups needed
    uint8_t midi_threshold = active_settings.midi_actuation;
    uint8_t normal_threshold = active_settings.normal_actuation;
    uint8_t analog_mode = active_settings.velocity_mode;
    
    state->was_pressed = state->pressed;
    state->pressed = pressed;

    // Handle per-key rapid trigger mode (for MIDI keys)
    if (key->mode == AKM_RAPID && state->is_midi_key && per_key_mode_enabled) {
        // Get per-key settings
        uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
        if (current_layer >= 12) current_layer = 0;
        uint8_t key_index = row * 14 + col;

        if (key_index < 70) {
            uint8_t target_layer = per_key_per_layer_enabled ? current_layer : 0;
            per_key_actuation_t *settings = &per_key_actuations[target_layer].keys[key_index];

            // Check if rapidfire is enabled for this key
            if (settings->rapidfire_enabled) {
                // Check if we're in a deadzone - if so, disable rapid trigger
                bool in_deadzone = is_in_deadzone(travel, settings->deadzone_top, settings->deadzone_bottom);

                // Full release detection - reset rapid trigger state
                uint8_t top_threshold = (settings->deadzone_top * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100;
                if (travel <= top_threshold) {
                    key->rapid_cycle_active = false;
                    key->awaiting_release = false;
                    key->base_velocity = 0;
                }

                if (!in_deadzone) {
                    uint16_t time_delta = now - state->last_time;
                    uint8_t travel_delta = (travel > state->last_travel) ? (travel - state->last_travel) : 0;

                    // Initial press - cross actuation point
                    if (pressed && !state->was_pressed && !key->rapid_cycle_active) {
                        key->rapid_cycle_active = true;
                        key->awaiting_release = true;

                        // Calculate initial velocity
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
                    // Rapid re-trigger logic
                    else if (key->rapid_cycle_active) {
                        // Convert rapidfire sensitivity from 0-100 scale to travel units
                        uint8_t press_sens = (settings->rapidfire_press_sens * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100;
                        uint8_t release_sens = (settings->rapidfire_release_sens * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 100;

                        // Detect release: travel decreased by >= release_sens
                        if (key->awaiting_release && state->last_travel > travel) {
                            uint8_t down_travel = state->last_travel - travel;
                            if (down_travel >= release_sens) {
                                key->awaiting_release = false;
                            }
                        }

                        // Detect re-trigger: travel increased by >= press_sens (after release detected)
                        if (!key->awaiting_release && travel > state->last_travel) {
                            uint8_t up_travel = travel - state->last_travel;
                            if (up_travel >= press_sens) {
                                // Re-trigger! Accumulate velocity
                                int16_t new_velocity = key->base_velocity + settings->rapidfire_velocity_mod;

                                // Clamp to valid range
                                if (new_velocity < MIN_VELOCITY) new_velocity = MIN_VELOCITY;
                                if (new_velocity > MAX_VELOCITY) new_velocity = MAX_VELOCITY;

                                key->base_velocity = (uint8_t)new_velocity;  // Update base for next cycle
                                store_midi_velocity(state->note_index, key->base_velocity);

                                key->awaiting_release = true;  // Wait for next release
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Standard velocity modes
    switch (analog_mode) {
        case 0:
            break;
            
        case 1: // Peak travel at apex
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

                    if (key->mode == AKM_RAPID) {
                        key->base_velocity = velocity;
                    }
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
            
        case 2: // Speed-based
            if (pressed && !state->was_pressed && !(key->mode == AKM_RAPID && key->rapid_cycle_active)) {
                uint16_t time_delta = now - state->last_time;
                uint8_t travel_delta = (travel > state->last_travel) ? (travel - state->last_travel) : 0;

                uint8_t velocity = calculate_speed_velocity(travel_delta, time_delta);

                store_midi_velocity(state->note_index, velocity);
                state->calculated_velocity = velocity;

                if (key->mode == AKM_RAPID) {
                    key->base_velocity = velocity;
                }
            }
            
            state->last_travel = travel;
            state->last_time = now;
            break;
            
        case 3: // Speed + peak combined
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

                    if (key->mode == AKM_RAPID) {
                        key->base_velocity = final_velocity;
                    }
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
    
// In process_midi_key_analog() function, replace the aftertouch sending code:

	// Aftertouch handling
	if (aftertouch_mode > 0 && pressed) {
		uint8_t aftertouch_value = 0;
		bool send_aftertouch = false;
		
		// Get the aftertouch CC for the current layer
		uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
		if (current_layer >= 12) current_layer = 0;
		uint8_t at_cc = aftertouch_cc;
		
		switch (aftertouch_mode) {
			case 1: // Reverse
				if (aftertouch_pedal_active) {
					aftertouch_value = 127 - ((travel * 127) / 240);
					send_aftertouch = true;
				}
				break;
				
			case 2: // Bottom-out
				if (aftertouch_pedal_active) {
					aftertouch_value = 127 - (127 - ((travel * 127) / 240));
					send_aftertouch = true;
				}
				break;
				
			case 3: // Post-actuation
				if (travel >= normal_threshold) {
					uint8_t additional_travel = travel - normal_threshold;
					uint8_t range = 240 - normal_threshold;
					if (range > 0) {
						aftertouch_value = (additional_travel * 127) / range;
						send_aftertouch = true;
					}
				}
				break;
				
			case 4: // Vibrato
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

			// Use the layer's CC instead of global aftertouch_cc
			midi_send_cc(&midi_device, channel_number, at_cc, aftertouch_value);
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
            uint8_t note_index;
            if (check_is_midi_key(row, col, &note_index)) {
                midi_key_states[row][col].is_midi_key = true;
                midi_key_states[row][col].note_index = note_index;
            }
        }
    }
    
    midi_states_initialized = true;
}

// ============================================================================
// ANALOG MATRIX TASK (INTERNAL)
// ============================================================================

static void analog_matrix_task_internal(void) {
    if (!analog_initialized) return;
    
    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
        select_column(col);
        wait_us(40);
        
        adcConvert(&ADCD1, &adcgrpcfg, samples, ADC_GRP_BUF_DEPTH);
        
        for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
            analog_key_t *key = &keys[row][col];
            uint16_t raw_value = samples[row];
            
            key->raw_value = raw_value;
            key->travel = calculate_travel(row, col, raw_value);
            update_calibration(row, col, raw_value);
            process_key_state(key);
        }
        
        unselect_column();
    }
}

// ============================================================================
// QMK CUSTOM MATRIX IMPLEMENTATION
// ============================================================================

void matrix_init_custom(void) {
    if (analog_initialized) return;
    
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
    
    for (uint8_t r = 0; r < MATRIX_ROWS; r++) {
        for (uint8_t c = 0; c < MATRIX_COLS; c++) {
            analog_key_t *key = &keys[r][c];
            calibration_t *cal = &calibration[r][c];
            
            key->mode = AKM_REGULAR;
            key->state = AKS_REGULAR_RELEASED;

            uint8_t act_pt = DEFAULT_ACTUATION_POINT * TRAVEL_SCALE;
            key->regular.actn_pt = act_pt;
            key->regular.deactn_pt = act_pt > STATIC_HYSTERESIS * TRAVEL_SCALE ?
                                     act_pt - STATIC_HYSTERESIS * TRAVEL_SCALE : 0;

            key->rpd_trig_sen = DEFAULT_RAPID_TRIGGER_SENSITIVITY * TRAVEL_SCALE;
            key->rpd_trig_sen_release = key->rpd_trig_sen;

            // Initialize per-key rapid trigger state
            key->base_velocity = 0;
            key->rapid_cycle_active = false;
            key->awaiting_release = false;
            key->last_direction = 0;
            
            cal->value.zero_travel = DEFAULT_ZERO_TRAVEL_VALUE;
            cal->value.full_travel = DEFAULT_ZERO_TRAVEL_VALUE - DEFAULT_FULL_RANGE;
            cal->calibrated = false;
            cal->stable = false;
            cal->pressed = false;
        }
    }
    
    for (uint8_t i = 0; i < MATRIX_ROWS; i++) {
        raw_matrix[i] = 0;
        matrix[i] = 0;
    }
    
    for (uint8_t i = 0; i < 5; i++) {
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            select_column(col);
            wait_us(40);
            adcConvert(&ADCD1, &adcgrpcfg, samples, ADC_GRP_BUF_DEPTH);
            unselect_column();
        }
    }
    
    analog_initialized = true;
}

bool matrix_scan_custom(matrix_row_t current_matrix[]) {
    bool changed = false;
    
    if (!midi_states_initialized && optimized_midi_positions != NULL) {
        initialize_midi_states();
    }
    
    analog_matrix_task_internal();
    
    // Get current layer ONCE per scan cycle
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    
    // Update cached settings if layer changed (very cheap check)
    update_active_settings(current_layer);
    
    // Process MIDI keys using cached settings
    if (midi_states_initialized && active_settings.velocity_mode > 0) {
        for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
            for (uint8_t col = 0; col < MATRIX_COLS; col++) {
                if (midi_key_states[row][col].is_midi_key) {
                    process_midi_key_analog(row, col);
                }
            }
        }
    }
    
    // Build matrix using cached thresholds
    uint8_t midi_threshold = active_settings.midi_actuation;
    uint8_t analog_mode = active_settings.velocity_mode;
    
    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        matrix_row_t current_row_value = 0;
        
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            analog_key_t *key = &keys[row][col];
            bool pressed = false;
            
            if (midi_key_states[row][col].is_midi_key) {
                uint8_t travel = key->travel;
                midi_key_state_t *state = &midi_key_states[row][col];
                
                switch (analog_mode) {
                    case 0:
                        pressed = (key->state == AKS_REGULAR_PRESSED || key->state == AKS_RAPID_PRESSED) &&
                                  (travel >= midi_threshold);
                        break;
                    case 1:
                        pressed = state->send_on_release;
                        break;
                    case 2:
                        pressed = (travel >= midi_threshold) && state->calculated_velocity > 0;
                        break;
                    case 3:
                        pressed = state->send_on_release;
                        break;
                }
                
                if ((aftertouch_mode == 1 || aftertouch_mode == 2) && 
                    aftertouch_pedal_active && state->was_pressed) {
                    pressed = true;
                }
            } else {
                pressed = (key->state == AKS_REGULAR_PRESSED || key->state == AKS_RAPID_PRESSED);
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
    return keys[row][col].travel;
}

uint8_t analog_matrix_get_travel_normalized(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint16_t travel = keys[row][col].travel;
    return (travel * 255) / (FULL_TRAVEL_UNIT * TRAVEL_SCALE);
}

bool analog_matrix_get_key_state(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return false;
    analog_key_t *key = &keys[row][col];
    return (key->state == AKS_REGULAR_PRESSED || key->state == AKS_RAPID_PRESSED);
}

uint16_t analog_matrix_get_raw_value(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    return keys[row][col].raw_value;
}

bool analog_matrix_is_calibrated(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return false;
    return calibration[row][col].calibrated;
}

bool analog_matrix_calibrating(void) {
    for (uint8_t r = 0; r < MATRIX_ROWS; r++) {
        for (uint8_t c = 0; c < MATRIX_COLS; c++) {
            if (!calibration[r][c].calibrated) return true;
        }
    }
    return false;
}

void analog_matrix_set_actuation_point(uint8_t row, uint8_t col, uint8_t point) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;
    analog_key_t *key = &keys[row][col];
    
    if (point == 0) point = DEFAULT_ACTUATION_POINT;
    
    uint8_t act_pt = point * TRAVEL_SCALE;
    key->regular.actn_pt = act_pt;
    key->regular.deactn_pt = act_pt > STATIC_HYSTERESIS * TRAVEL_SCALE ? 
                             act_pt - STATIC_HYSTERESIS * TRAVEL_SCALE : 0;
    key->act_pt = point;
}

void analog_matrix_set_rapid_trigger(uint8_t row, uint8_t col, uint8_t sensitivity) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;
    analog_key_t *key = &keys[row][col];
    
    if (sensitivity == 0) sensitivity = DEFAULT_RAPID_TRIGGER_SENSITIVITY;
    
    key->rpd_trig_sen = sensitivity * TRAVEL_SCALE;
    key->rpd_trig_sen_release = key->rpd_trig_sen;
}

void analog_matrix_set_key_mode(uint8_t row, uint8_t col, uint8_t mode) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;
    if (mode != AKM_REGULAR && mode != AKM_RAPID) return;
    keys[row][col].mode = mode;
}

void analog_matrix_reset_calibration(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;
    calibration_t *cal = &calibration[row][col];
    cal->calibrated = false;
    cal->value.zero_travel = DEFAULT_ZERO_TRAVEL_VALUE;
    cal->value.full_travel = DEFAULT_ZERO_TRAVEL_VALUE - DEFAULT_FULL_RANGE;
}

void analog_matrix_reset_all_calibration(void) {
    for (uint8_t r = 0; r < MATRIX_ROWS; r++) {
        for (uint8_t c = 0; c < MATRIX_COLS; c++) {
            analog_matrix_reset_calibration(r, c);
        }
    }
}