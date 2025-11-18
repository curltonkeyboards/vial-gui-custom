/* Copyright 2024 Your Name
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 */

#include "analog_matrix.h"
#include "quantum.h"
#include "hal.h"
#include "gpio.h"
#include <string.h>
#include <stdlib.h>

// ============================================================================
// INTERNAL DATA STRUCTURES
// ============================================================================

typedef struct {
    uint16_t zero_travel;  // ADC value at rest
    uint16_t full_travel;  // ADC value at full press
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
    uint8_t  actn_pt;    // Actuation point
    uint8_t  deactn_pt;  // Deactuation point
} threshold_t;

typedef struct {
    // Mode and state
    uint8_t mode;   // AKM_REGULAR or AKM_RAPID
    uint8_t state;  // Current state
    
    // Travel data
    uint8_t  travel;      // Current travel (0-240)
    uint8_t  last_travel; // Previous travel
    uint16_t raw_value;   // Current raw ADC value
    
    // Thresholds
    threshold_t regular;  // Regular mode thresholds
    threshold_t rapid;    // Rapid trigger thresholds
    
    // Settings
    uint8_t act_pt;              // Custom actuation point (0 = use default)
    uint8_t rpd_trig_sen;        // Rapid trigger sensitivity (0 = use default)
    uint8_t rpd_trig_sen_release; // Rapid trigger release sensitivity
} analog_key_t;

// ============================================================================
// STATIC VARIABLES
// ============================================================================

static analog_key_t  keys[MATRIX_ROWS][MATRIX_COLS];
static calibration_t calibration[MATRIX_ROWS][MATRIX_COLS];
static bool          initialized = false;

// ADC sampling
#define ADC_GRP_NUM_CHANNELS MATRIX_ROWS
#define ADC_GRP_BUF_DEPTH 1
static adcsample_t samples[ADC_GRP_NUM_CHANNELS * ADC_GRP_BUF_DEPTH];

// Pin configuration
static pin_t row_pins[MATRIX_ROWS] = MATRIX_ROW_PINS;

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
    0,                    // CR1
    ADC_CR2_SWSTART,      // CR2
    0,                    // SMPR1
    0,                    // SMPR2
    0,                    // HTR
    0,                    // LTR
    0,                    // SQR1
    0,                    // SQR2
    0                     // SQR3
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

static inline void shifter_delay(uint16_t n) {
    while (n-- > 0) {
        asm volatile("nop" ::: "memory");
    }
}

static void hc164_output(uint16_t data, bool single_bit) {
    uint8_t n = 50;
    ATOMIC_BLOCK_FORCEON {
        for (uint8_t i = 0; i < 15; i++) {
            writePinLow(HC164_CP);
            if (data & 0x1) {
                writePinHigh(HC164_DS);
            } else {
                writePinLow(HC164_DS);
            }
            shifter_delay(n);
            writePinHigh(HC164_CP);
            shifter_delay(n);
            if (single_bit) break;
            data = data >> 1;
        }
        writePinLow(HC164_CP);
    }
}

static void select_column(uint8_t col) {
    if (col == 0) {
        writePinLow(HC164_MR);
        shifter_delay(20);
        writePinHigh(HC164_MR);
        shifter_delay(20);
    }
    hc164_output(0x01, true);
}

static void unselect_column(void) {
    hc164_output(0x00, true);
}

// ============================================================================
// CALIBRATION FUNCTIONS
// ============================================================================

static void update_calibration(uint8_t row, uint8_t col, uint16_t raw_value) {
    calibration_t *cal = &calibration[row][col];
    analog_key_t  *key = &keys[row][col];
    uint32_t now = timer_read32();
    
    // Check if value is stable
    if (abs(raw_value - cal->last_value) < AUTO_CALIB_ZERO_TRAVEL_JITTER) {
        if (!cal->stable) {
            cal->stable = true;
            cal->stable_time = now;
        }
    } else {
        cal->stable = false;
    }
    
    // Update zero travel (rest position) when stable and not pressed
    if (cal->stable && !cal->pressed && 
        timer_elapsed32(cal->stable_time) > AUTO_CALIB_VALID_RELEASE_TIME) {
        if (!cal->calibrated || abs(raw_value - cal->value.zero_travel) > AUTO_CALIB_ZERO_TRAVEL_JITTER) {
            cal->value.zero_travel = raw_value;
            dprintf("Calibrated zero for key[%d,%d]: %d\n", row, col, raw_value);
        }
    }
    
    // Update full travel (bottom position) when pressed and stable
    if (key->travel > (BOTTOM_DEAD_ZONE * TRAVEL_SCALE - 10)) {
        if (!cal->pressed) {
            cal->pressed = true;
            cal->press_time = now;
        }
        if (timer_elapsed32(cal->press_time) > 100 && cal->stable) {
            if (!cal->calibrated || abs(raw_value - cal->value.full_travel) > AUTO_CALIB_FULL_TRAVEL_JITTER) {
                cal->value.full_travel = raw_value;
                cal->calibrated = true;
                dprintf("Calibrated full for key[%d,%d]: %d\n", row, col, raw_value);
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
    
    // Clamp raw value
    if (raw_value > zero_val) raw_value = zero_val;
    if (raw_value < full_val) raw_value = full_val;
    
    range = zero_val - full_val;
    if (range == 0) range = 1;  // Prevent division by zero
    
    // Calculate travel: 0 at rest, increases as key is pressed
    uint32_t current = zero_val - raw_value;
    uint8_t travel = (current * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / range;
    
    // Clamp to valid range
    if (travel > FULL_TRAVEL_UNIT * TRAVEL_SCALE) {
        travel = FULL_TRAVEL_UNIT * TRAVEL_SCALE;
    }
    
    return travel;
}

// ============================================================================
// STATE MACHINE
// ============================================================================

static bool process_key_state(analog_key_t *key) {
    bool changed = false;
    
    if (key->mode == AKM_REGULAR) {
        // Static actuation point mode
        switch (key->state) {
            case AKS_REGULAR_RELEASED:
                if (key->travel >= key->regular.actn_pt) {
                    key->state = AKS_REGULAR_PRESSED;
                    changed = true;
                }
                break;
                
            case AKS_REGULAR_PRESSED:
                if (key->travel <= key->regular.deactn_pt) {
                    key->state = AKS_REGULAR_RELEASED;
                    changed = true;
                }
                break;
        }
    } else {
        // Rapid trigger mode
        switch (key->state) {
            case AKS_REGULAR_RELEASED:
                if (key->travel >= key->regular.actn_pt) {
                    key->state = AKS_REGULAR_PRESSED;
                    changed = true;
                    // Update rapid trigger points
                    key->rapid.deactn_pt = key->travel > key->rpd_trig_sen_release ? 
                                          key->travel - key->rpd_trig_sen_release : 0;
                    key->rapid.actn_pt = key->travel;
                }
                break;
                
            case AKS_REGULAR_PRESSED:
                if (key->travel <= key->regular.deactn_pt) {
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
                break;
                
            case AKS_RAPID_RELEASED:
                if (key->travel <= key->regular.deactn_pt) {
                    key->state = AKS_REGULAR_RELEASED;
                } else if (key->travel >= key->rapid.actn_pt && 
                          key->travel >= key->regular.actn_pt) {
                    key->state = AKS_RAPID_PRESSED;
                    changed = true;
                    key->rapid.deactn_pt = key->travel > key->rpd_trig_sen_release ? 
                                          key->travel - key->rpd_trig_sen_release : 0;
                    key->rapid.actn_pt = key->travel;
                } else if (key->travel < key->rapid.deactn_pt) {
                    key->rapid.deactn_pt = key->travel;
                    key->rapid.actn_pt = key->travel + key->rpd_trig_sen;
                }
                break;
                
            case AKS_RAPID_PRESSED:
                if (key->travel > FULL_TRAVEL_UNIT * TRAVEL_SCALE) break;
                
                if (key->travel <= key->regular.deactn_pt) {
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
                break;
        }
    }
    
    key->last_travel = key->travel;
    return changed;
}

// ============================================================================
// INITIALIZATION
// ============================================================================

void analog_matrix_init(void) {
    if (initialized) return;
    
    // Initialize shift register pins
    setPinOutput(HC164_DS);
    setPinOutput(HC164_CP);
    setPinOutput(HC164_MR);
    writePinLow(HC164_MR);
    shifter_delay(20);
    writePinHigh(HC164_MR);
    
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
    
    // STM32 AN4073 Option 2
    SYSCFG->PMC |= SYSCFG_PMC_ADC1DC2;
    
    // Initialize key data
    for (uint8_t r = 0; r < MATRIX_ROWS; r++) {
        for (uint8_t c = 0; c < MATRIX_COLS; c++) {
            analog_key_t *key = &keys[r][c];
            calibration_t *cal = &calibration[r][c];
            
            // Default mode
            key->mode = AKM_REGULAR;
            key->state = AKS_REGULAR_RELEASED;
            
            // Default thresholds
            uint8_t act_pt = DEFAULT_ACTUATION_POINT * TRAVEL_SCALE;
            key->regular.actn_pt = act_pt;
            key->regular.deactn_pt = act_pt > STATIC_HYSTERESIS * TRAVEL_SCALE ? 
                                     act_pt - STATIC_HYSTERESIS * TRAVEL_SCALE : 0;
            
            key->rpd_trig_sen = DEFAULT_RAPID_TRIGGER_SENSITIVITY * TRAVEL_SCALE;
            key->rpd_trig_sen_release = key->rpd_trig_sen;
            
            // Default calibration
            cal->value.zero_travel = DEFAULT_ZERO_TRAVEL_VALUE;
            cal->value.full_travel = DEFAULT_ZERO_TRAVEL_VALUE - DEFAULT_FULL_RANGE;
            cal->calibrated = false;
            cal->stable = false;
            cal->pressed = false;
        }
    }
    
    // Dummy scans to stabilize ADC
    for (uint8_t i = 0; i < 5; i++) {
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            select_column(col);
            wait_us(40);
            adcConvert(&ADCD1, &adcgrpcfg, samples, ADC_GRP_BUF_DEPTH);
            unselect_column();
        }
    }
    
    initialized = true;
    dprintf("Analog matrix initialized\n");
}

// ============================================================================
// MAIN TASK
// ============================================================================

void analog_matrix_task(void) {
    if (!initialized) return;
    
    // Scan all columns
    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
        select_column(col);
        wait_us(40);
        
        // Read ADC for all rows
        adcConvert(&ADCD1, &adcgrpcfg, samples, ADC_GRP_BUF_DEPTH);
        
        for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
            analog_key_t *key = &keys[row][col];
            uint16_t raw_value = samples[row];
            
            // Store raw value
            key->raw_value = raw_value;
            
            // Calculate travel
            key->travel = calculate_travel(row, col, raw_value);
            
            // Update calibration
            update_calibration(row, col, raw_value);
            
            // Process state machine
            process_key_state(key);
        }
        
        unselect_column();
    }
}

// ============================================================================
// PUBLIC API FUNCTIONS
// ============================================================================

uint8_t analog_matrix_get_travel(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    return keys[row][col].travel;
}

uint8_t analog_matrix_get_travel_normalized(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    // Convert 0-240 to 0-255
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