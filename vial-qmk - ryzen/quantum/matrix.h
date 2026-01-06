/*
Copyright 2011 Jun Wako <wakojun@gmail.com>
Copyright 2024 Your Name (Analog Matrix Extensions)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "gpio.h"

// ============================================================================
// STANDARD QMK MATRIX DEFINITIONS
// ============================================================================

/* diode directions */
#define COL2ROW 0
#define ROW2COL 1

#if (MATRIX_COLS <= 8)
typedef uint8_t matrix_row_t;
#elif (MATRIX_COLS <= 16)
typedef uint16_t matrix_row_t;
#elif (MATRIX_COLS <= 32)
typedef uint32_t matrix_row_t;
#else
#    error "MATRIX_COLS: invalid value"
#endif

#define MATRIX_ROW_SHIFTER ((matrix_row_t)1)

// ============================================================================
// ANALOG MATRIX HARDWARE CONFIGURATION
// ============================================================================

// Matrix dimensions (define in config.h if different)
#ifndef MATRIX_ROWS
#    define MATRIX_ROWS 5
#endif
#ifndef MATRIX_COLS
#    define MATRIX_COLS 14
#endif

// Row pins (ADC-capable pins) - define in config.h
#ifndef MATRIX_ROW_PINS
#    define MATRIX_ROW_PINS { A0, A1, A2, A3, A4 }
#endif

// ADG706 Multiplexer pins - define in config.h to match your wiring
#ifndef ADG706_A0
#    define ADG706_A0 A5  // Address bit 0 (LSB)
#endif
#ifndef ADG706_A1
#    define ADG706_A1 A6  // Address bit 1
#endif
#ifndef ADG706_A2
#    define ADG706_A2 A7  // Address bit 2
#endif
#ifndef ADG706_A3
#    define ADG706_A3 A8  // Address bit 3 (MSB)
#endif
#ifndef ADG706_EN
#    define ADG706_EN NO_PIN  // Enable (active LOW) - NO_PIN if hardwired to GND
#endif

// ============================================================================
// ANALOG CONFIGURATION
// ============================================================================

// Travel distance unit (4.0mm max travel = 40 units of 0.1mm)
#define FULL_TRAVEL_UNIT 40

// Default actuation point (in 0.1mm units, 20 = 2.0mm)
#ifndef DEFAULT_ACTUATION_POINT
#    define DEFAULT_ACTUATION_POINT 20
#endif

// Default rapid trigger sensitivity (in 0.1mm units, 4 = 0.4mm)
#ifndef DEFAULT_RAPID_TRIGGER_SENSITIVITY
#    define DEFAULT_RAPID_TRIGGER_SENSITIVITY 4
#endif

// Calibration defaults (ADC values for 12-bit ADC: 0-4095)
#ifndef DEFAULT_ZERO_TRAVEL_VALUE
#    define DEFAULT_ZERO_TRAVEL_VALUE 3000  // Rest position
#endif
#ifndef DEFAULT_FULL_RANGE
#    define DEFAULT_FULL_RANGE 900  // Range from rest to full press
#endif

// Travel scaling factor for internal precision
#define TRAVEL_SCALE 6

// ADC valid range
#define VALID_ANALOG_RAW_VALUE_MIN 1200
#define VALID_ANALOG_RAW_VALUE_MAX 3500

// Debounce attempts
#ifndef ANALOG_DEBOUCE_TIME
#    define ANALOG_DEBOUCE_TIME 3
#endif

// Hysteresis for static mode (in 0.1mm units)
#define STATIC_HYSTERESIS 5

// Dead zones (in 0.1mm units)
#define ZERO_TRAVEL_DEAD_ZONE 20
#define BOTTOM_DEAD_ZONE 38

// Auto-calibration thresholds
#define AUTO_CALIB_ZERO_TRAVEL_JITTER 50
#define AUTO_CALIB_FULL_TRAVEL_JITTER 100
#define AUTO_CALIB_VALID_RELEASE_TIME 1000  // ms

// ============================================================================
// KEY MODES AND STATES
// ============================================================================

enum {
    AKM_REGULAR = 1,  // Static actuation point
    AKM_RAPID = 2,    // Rapid trigger mode
};

enum {
    AKS_REGULAR_RELEASED,
    AKS_REGULAR_PRESSED,
    AKS_RAPID_RELEASED,
    AKS_RAPID_PRESSED,
};

// ============================================================================
// STANDARD QMK MATRIX API
// ============================================================================

#ifdef __cplusplus
extern "C" {
#endif

/* number of matrix rows */
uint8_t matrix_rows(void);
/* number of matrix columns */
uint8_t matrix_cols(void);
/* should be called at early stage of startup before matrix_init.(optional) */
void matrix_setup(void);
/* intialize matrix for scaning. */
void matrix_init(void);
/* scan all key states on matrix */
uint8_t matrix_scan(void);
/* whether matrix scanning operations should be executed */
bool matrix_can_read(void);
/* whether a switch is on */
bool matrix_is_on(uint8_t row, uint8_t col);
/* matrix state on row */
matrix_row_t matrix_get_row(uint8_t row);
/* print matrix for debug */
void matrix_print(void);
/* delay between changing matrix pin state and reading values */
void matrix_output_select_delay(void);
void matrix_output_unselect_delay(uint8_t line, bool key_pressed);
/* only for backwards compatibility. delay between changing matrix pin state and reading values */
void matrix_io_delay(void);
/* power control */
void matrix_power_up(void);
void matrix_power_down(void);

void matrix_init_kb(void);
void matrix_scan_kb(void);
void matrix_init_user(void);
void matrix_scan_user(void);

#ifdef SPLIT_KEYBOARD
bool matrix_post_scan(void);
void matrix_slave_scan_kb(void);
void matrix_slave_scan_user(void);
#endif

// ============================================================================
// ANALOG MATRIX PUBLIC API
// ============================================================================

// Initialize analog matrix system
void analog_matrix_init(void);

// Process analog matrix (call from matrix_scan_kb)
void analog_matrix_task(void);

// Get current travel distance for a key (0-240 = 0.0mm to 4.0mm scaled)
uint8_t analog_matrix_get_travel(uint8_t row, uint8_t col);

// Get normalized travel (0-255 for easy conversion)
uint8_t analog_matrix_get_travel_normalized(uint8_t row, uint8_t col);

// Get current key state (true = pressed, false = released)
bool analog_matrix_get_key_state(uint8_t row, uint8_t col);

// Get raw ADC value for debugging
uint16_t analog_matrix_get_raw_value(uint8_t row, uint8_t col);

// Check if key is calibrated
bool analog_matrix_is_calibrated(uint8_t row, uint8_t col);

// Check if any calibration is in progress
bool analog_matrix_calibrating(void);

// Set actuation point for a specific key (0 = use default)
void analog_matrix_set_actuation_point(uint8_t row, uint8_t col, uint8_t point);

// Set rapid trigger sensitivity for a specific key (0 = use default)
void analog_matrix_set_rapid_trigger(uint8_t row, uint8_t col, uint8_t sensitivity);

// Set key mode (AKM_REGULAR or AKM_RAPID)
void analog_matrix_set_key_mode(uint8_t row, uint8_t col, uint8_t mode);

// Reset calibration for a key
void analog_matrix_reset_calibration(uint8_t row, uint8_t col);

// Reset all calibration
void analog_matrix_reset_all_calibration(void);

// ============================================================================
// LIBHMK-STYLE API (new in architecture migration)
// ============================================================================

// Key direction states (libhmk 3-state FSM)
typedef enum {
    KEY_DIR_INACTIVE = 0,  // Key at rest or below actuation
    KEY_DIR_DOWN     = 1,  // Key pressed, tracking deepest point
    KEY_DIR_UP       = 2   // Key released by RT, tracking highest point
} key_dir_t;

// Get key distance (0-255 scale, libhmk compatible)
uint8_t analog_matrix_get_distance(uint8_t row, uint8_t col);

// Get RT direction state (KEY_DIR_INACTIVE, KEY_DIR_DOWN, KEY_DIR_UP)
uint8_t analog_matrix_get_key_direction(uint8_t row, uint8_t col);

// Get RT extremum value (peak or trough being tracked)
uint8_t analog_matrix_get_extremum(uint8_t row, uint8_t col);

// Get EMA-filtered ADC value
uint16_t analog_matrix_get_filtered_adc(uint8_t row, uint8_t col);

// Refresh cached layer settings (call when layer actuations change)
void analog_matrix_refresh_settings(void);

#ifdef __cplusplus
}
#endif