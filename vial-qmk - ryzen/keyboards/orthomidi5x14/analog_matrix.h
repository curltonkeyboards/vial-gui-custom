/* Copyright 2024 Your Name
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "matrix.h"

// ============================================================================
// HARDWARE CONFIGURATION
// ============================================================================

// Matrix dimensions
#ifndef MATRIX_ROWS
#    define MATRIX_ROWS 6
#endif
#ifndef MATRIX_COLS
#    define MATRIX_COLS 15
#endif

// Row pins (ADC-capable pins)
#ifndef MATRIX_ROW_PINS
#    define MATRIX_ROW_PINS { A0, A1, A2, A3, A4, A5 }
#endif

// HC164 Shift Register pins for column selection
#ifndef HC164_DS
#    define HC164_DS B3  // Data Serial
#endif
#ifndef HC164_CP
#    define HC164_CP B5  // Clock Pulse
#endif
#ifndef HC164_MR
#    define HC164_MR D2  // Master Reset
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

// Calibration defaults (ADC values)
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
// KEY MODES
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
// PUBLIC API
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