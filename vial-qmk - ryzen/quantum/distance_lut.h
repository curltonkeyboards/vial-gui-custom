/* Copyright 2025
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Distance Lookup Table for Hall Effect Sensor Linearization
 *
 * Hall effect sensors have a non-linear response due to magnetic field decay
 * following approximately 1/d² or 1/d³. This LUT compensates for that non-linearity
 * to provide accurate physical position readings.
 *
 * Formula: LUT[x] = round(255 × log₁₀(1 + a×x) / log₁₀(1 + a×1023))
 * where a = 0.01 (tuned for typical Hall sensors like SS49E/SLSS49E3)
 *
 * Based on libhmk by peppapighs: https://github.com/peppapighs/libhmk
 */

#pragma once

#include <stdint.h>
#include "progmem.h"

// LUT size - 1024 entries for high precision
#define DISTANCE_LUT_SIZE 1024

// The logarithmic correction LUT
// Generated with a = 0.01, optimized for Hall effect sensors with ~3-4mm rest to ~0.5-1mm bottom
// Input: normalized ADC (0-1023), Output: linearized distance (0-255)
static const uint8_t distance_lut[DISTANCE_LUT_SIZE] PROGMEM = {
    // Row 0-63: Near rest position (highest sensitivity zone)
      0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,  14,  15,
     16,  17,  18,  18,  19,  20,  21,  22,  23,  23,  24,  25,  26,  27,  27,  28,
     29,  30,  30,  31,  32,  33,  33,  34,  35,  35,  36,  37,  37,  38,  39,  39,
     40,  41,  41,  42,  43,  43,  44,  45,  45,  46,  46,  47,  48,  48,  49,  49,
    // Row 64-127
     50,  51,  51,  52,  52,  53,  54,  54,  55,  55,  56,  56,  57,  58,  58,  59,
     59,  60,  60,  61,  61,  62,  62,  63,  64,  64,  65,  65,  66,  66,  67,  67,
     68,  68,  69,  69,  70,  70,  71,  71,  72,  72,  73,  73,  74,  74,  75,  75,
     76,  76,  77,  77,  78,  78,  79,  79,  79,  80,  80,  81,  81,  82,  82,  83,
    // Row 128-191
     83,  84,  84,  84,  85,  85,  86,  86,  87,  87,  88,  88,  88,  89,  89,  90,
     90,  91,  91,  91,  92,  92,  93,  93,  94,  94,  94,  95,  95,  96,  96,  96,
     97,  97,  98,  98,  98,  99,  99, 100, 100, 100, 101, 101, 102, 102, 102, 103,
    103, 104, 104, 104, 105, 105, 105, 106, 106, 107, 107, 107, 108, 108, 108, 109,
    // Row 192-255
    109, 110, 110, 110, 111, 111, 111, 112, 112, 113, 113, 113, 114, 114, 114, 115,
    115, 115, 116, 116, 116, 117, 117, 118, 118, 118, 119, 119, 119, 120, 120, 120,
    121, 121, 121, 122, 122, 122, 123, 123, 123, 124, 124, 124, 125, 125, 125, 126,
    126, 126, 127, 127, 127, 128, 128, 128, 129, 129, 129, 130, 130, 130, 131, 131,
    // Row 256-319
    131, 132, 132, 132, 132, 133, 133, 133, 134, 134, 134, 135, 135, 135, 136, 136,
    136, 136, 137, 137, 137, 138, 138, 138, 139, 139, 139, 139, 140, 140, 140, 141,
    141, 141, 141, 142, 142, 142, 143, 143, 143, 143, 144, 144, 144, 145, 145, 145,
    145, 146, 146, 146, 147, 147, 147, 147, 148, 148, 148, 148, 149, 149, 149, 150,
    // Row 320-383
    150, 150, 150, 151, 151, 151, 151, 152, 152, 152, 152, 153, 153, 153, 154, 154,
    154, 154, 155, 155, 155, 155, 156, 156, 156, 156, 157, 157, 157, 157, 158, 158,
    158, 158, 159, 159, 159, 159, 160, 160, 160, 160, 161, 161, 161, 161, 162, 162,
    162, 162, 163, 163, 163, 163, 164, 164, 164, 164, 165, 165, 165, 165, 165, 166,
    // Row 384-447
    166, 166, 166, 167, 167, 167, 167, 168, 168, 168, 168, 169, 169, 169, 169, 169,
    170, 170, 170, 170, 171, 171, 171, 171, 171, 172, 172, 172, 172, 173, 173, 173,
    173, 173, 174, 174, 174, 174, 175, 175, 175, 175, 175, 176, 176, 176, 176, 177,
    177, 177, 177, 177, 178, 178, 178, 178, 178, 179, 179, 179, 179, 180, 180, 180,
    // Row 448-511
    180, 180, 181, 181, 181, 181, 181, 182, 182, 182, 182, 182, 183, 183, 183, 183,
    183, 184, 184, 184, 184, 185, 185, 185, 185, 185, 186, 186, 186, 186, 186, 187,
    187, 187, 187, 187, 188, 188, 188, 188, 188, 189, 189, 189, 189, 189, 189, 190,
    190, 190, 190, 190, 191, 191, 191, 191, 191, 192, 192, 192, 192, 192, 193, 193,
    // Row 512-575
    193, 193, 193, 194, 194, 194, 194, 194, 194, 195, 195, 195, 195, 195, 196, 196,
    196, 196, 196, 196, 197, 197, 197, 197, 197, 198, 198, 198, 198, 198, 198, 199,
    199, 199, 199, 199, 200, 200, 200, 200, 200, 200, 201, 201, 201, 201, 201, 201,
    202, 202, 202, 202, 202, 203, 203, 203, 203, 203, 203, 204, 204, 204, 204, 204,
    // Row 576-639
    204, 205, 205, 205, 205, 205, 205, 206, 206, 206, 206, 206, 206, 207, 207, 207,
    207, 207, 207, 208, 208, 208, 208, 208, 208, 209, 209, 209, 209, 209, 209, 210,
    210, 210, 210, 210, 210, 211, 211, 211, 211, 211, 211, 212, 212, 212, 212, 212,
    212, 212, 213, 213, 213, 213, 213, 213, 214, 214, 214, 214, 214, 214, 215, 215,
    // Row 640-703
    215, 215, 215, 215, 215, 216, 216, 216, 216, 216, 216, 217, 217, 217, 217, 217,
    217, 217, 218, 218, 218, 218, 218, 218, 218, 219, 219, 219, 219, 219, 219, 220,
    220, 220, 220, 220, 220, 220, 221, 221, 221, 221, 221, 221, 221, 222, 222, 222,
    222, 222, 222, 222, 223, 223, 223, 223, 223, 223, 223, 224, 224, 224, 224, 224,
    // Row 704-767
    224, 224, 225, 225, 225, 225, 225, 225, 225, 226, 226, 226, 226, 226, 226, 226,
    227, 227, 227, 227, 227, 227, 227, 228, 228, 228, 228, 228, 228, 228, 228, 229,
    229, 229, 229, 229, 229, 229, 230, 230, 230, 230, 230, 230, 230, 230, 231, 231,
    231, 231, 231, 231, 231, 232, 232, 232, 232, 232, 232, 232, 232, 233, 233, 233,
    // Row 768-831
    233, 233, 233, 233, 233, 234, 234, 234, 234, 234, 234, 234, 234, 235, 235, 235,
    235, 235, 235, 235, 235, 236, 236, 236, 236, 236, 236, 236, 236, 237, 237, 237,
    237, 237, 237, 237, 237, 238, 238, 238, 238, 238, 238, 238, 238, 239, 239, 239,
    239, 239, 239, 239, 239, 239, 240, 240, 240, 240, 240, 240, 240, 240, 241, 241,
    // Row 832-895
    241, 241, 241, 241, 241, 241, 241, 242, 242, 242, 242, 242, 242, 242, 242, 242,
    243, 243, 243, 243, 243, 243, 243, 243, 244, 244, 244, 244, 244, 244, 244, 244,
    244, 245, 245, 245, 245, 245, 245, 245, 245, 245, 246, 246, 246, 246, 246, 246,
    246, 246, 246, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 248, 248, 248,
    // Row 896-959
    248, 248, 248, 248, 248, 248, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249,
    250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 251, 251, 251, 251, 251, 251,
    251, 251, 251, 251, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 253, 253,
    253, 253, 253, 253, 253, 253, 253, 253, 253, 254, 254, 254, 254, 254, 254, 254,
    // Row 960-1023: Near bottom-out (lowest sensitivity zone)
    254, 254, 254, 254, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255
};

// Global correction strength (0 = linear/no correction, 100 = full logarithmic)
extern uint8_t lut_correction_strength;

// ============================================================================
// EQ-STYLE SENSITIVITY CURVE SYSTEM
// ============================================================================
//
// 3 Rest Value Ranges:
//   Range 0 (Low):  rest < eq_range_low
//   Range 1 (Mid):  eq_range_low <= rest < eq_range_high
//   Range 2 (High): rest >= eq_range_high
//
// 5 Travel Position Bands per Range:
//   Band 0 (Low):      0-20% travel   (0-204 normalized)
//   Band 1 (Low-Mid):  20-40% travel  (205-409 normalized)
//   Band 2 (Mid):      40-60% travel  (410-613 normalized)
//   Band 3 (High-Mid): 60-80% travel  (614-818 normalized)
//   Band 4 (High):     80-100% travel (819-1023 normalized)
//
// Each band has a sensitivity multiplier: 25% to 400%
// Stored as uint8_t where actual_percent = stored_value * 2
// Default value = 50 (100% = no change)
// ============================================================================

// EQ range boundaries (can be adjusted via HID)
extern uint16_t eq_range_low;   // Below this = low rest range (default 1900)
extern uint16_t eq_range_high;  // At or above this = high rest range (default 2100)

// EQ bands: 3 ranges × 5 bands
// Value stored as half-percentage: actual_percent = value * 2
// So 50 = 100%, 12 = 25%, 200 = 400%
extern uint8_t eq_bands[3][5];

// Band boundaries in normalized space (0-1023)
#define EQ_BAND_0_END   204   // 0-20%
#define EQ_BAND_1_END   409   // 20-40%
#define EQ_BAND_2_END   613   // 40-60%
#define EQ_BAND_3_END   818   // 60-80%
// Band 4: 819-1023 (80-100%)

/**
 * Apply EQ-style sensitivity curve adjustment
 *
 * This function applies a 5-band equalizer curve based on the sensor's rest value.
 * Different rest value ranges can have completely different sensitivity profiles.
 *
 * @param normalized  Linear normalized position (0-1023)
 * @param rest        Rest ADC value for this key
 * @return            Adjusted normalized position (0-1023)
 */
static inline __attribute__((always_inline)) uint32_t apply_eq_curve_adjustment(
    uint32_t normalized,
    uint16_t rest
) {
    // Determine which range based on rest value
    uint8_t range;
    if (rest < eq_range_low) {
        range = 0;  // Low rest sensors
    } else if (rest < eq_range_high) {
        range = 1;  // Mid rest sensors
    } else {
        range = 2;  // High rest sensors
    }

    // Determine which band and interpolation factor based on position
    // We interpolate between adjacent band values for smooth transitions
    uint8_t band_low, band_high;
    uint32_t interp_factor;  // 0-1023 interpolation within band

    if (normalized <= EQ_BAND_0_END) {
        // Band 0: 0-204
        band_low = 0;
        band_high = 0;
        interp_factor = 512;  // Use band 0 value directly (center of interpolation)
    } else if (normalized <= EQ_BAND_1_END) {
        // Transition from band 0 to band 1: 205-409
        band_low = 0;
        band_high = 1;
        // Interpolate: 0 at start (205), 1023 at end (409)
        interp_factor = ((normalized - EQ_BAND_0_END - 1) * 1023) / (EQ_BAND_1_END - EQ_BAND_0_END);
    } else if (normalized <= EQ_BAND_2_END) {
        // Transition from band 1 to band 2: 410-613
        band_low = 1;
        band_high = 2;
        interp_factor = ((normalized - EQ_BAND_1_END - 1) * 1023) / (EQ_BAND_2_END - EQ_BAND_1_END);
    } else if (normalized <= EQ_BAND_3_END) {
        // Transition from band 2 to band 3: 614-818
        band_low = 2;
        band_high = 3;
        interp_factor = ((normalized - EQ_BAND_2_END - 1) * 1023) / (EQ_BAND_3_END - EQ_BAND_2_END);
    } else {
        // Band 4: 819-1023
        band_low = 4;
        band_high = 4;
        interp_factor = 512;  // Use band 4 value directly
    }

    // Get the sensitivity multipliers for the two bands (stored as half-percentage)
    uint16_t mult_low = (uint16_t)eq_bands[range][band_low] * 2;   // Convert to actual percentage
    uint16_t mult_high = (uint16_t)eq_bands[range][band_high] * 2;

    // Interpolate between the two multipliers
    // multiplier = mult_low + (mult_high - mult_low) * interp_factor / 1023
    int32_t multiplier;
    if (band_low == band_high) {
        multiplier = mult_low;
    } else {
        multiplier = mult_low + ((int32_t)(mult_high - mult_low) * (int32_t)interp_factor) / 1023;
    }

    // Apply multiplier: adjusted = normalized * multiplier / 100
    int32_t adjusted = ((int32_t)normalized * multiplier) / 100;

    // Clamp to valid range
    if (adjusted < 0) adjusted = 0;
    if (adjusted > 1023) adjusted = 1023;

    return (uint32_t)adjusted;
}

/**
 * Convert ADC reading to linearized distance with adjustable correction strength
 *
 * @param adc            Raw ADC value from sensor
 * @param rest           Calibrated rest position ADC value
 * @param bottom_out     Calibrated bottom-out ADC value
 * @param strength       Correction strength (0-100): 0=linear, 100=full LUT
 * @return               Linearized distance (0-255)
 *
 * The strength parameter allows blending between:
 * - 0: Pure linear (current behavior, no correction)
 * - 100: Full logarithmic LUT (compensates for sensor non-linearity)
 * - 1-99: Blend between linear and logarithmic
 */
static inline __attribute__((always_inline)) uint8_t adc_to_distance_corrected(
    uint16_t adc,
    uint16_t rest,
    uint16_t bottom_out,
    uint8_t strength
) {
    // Handle edge cases - only return 0 if calibration is truly invalid (equal values)
    if (rest == bottom_out) return 0;  // Invalid calibration

    // Handle inverted ADC (Hall effect: higher ADC = less pressed)
    // Most Hall sensors work this way - rest value is HIGHER than bottom_out
    if (rest > bottom_out) {
        // Inverted Hall effect sensor: rest=2000, bottom=1100
        // We need to invert the ADC reading so that:
        // - At rest (adc=2000): distance should be 0
        // - At bottom (adc=1100): distance should be 255

        // Calculate distance directly for inverted sensors
        // distance = (rest - adc) / (rest - bottom_out) * 255
        if (adc >= rest) return 0;        // At or above rest = no travel
        if (adc <= bottom_out) return 255; // At or below bottom = full travel

        // Normalize to 0-1023 range
        // For inverted: higher ADC = less pressed, so invert the calculation
        uint32_t normalized = ((uint32_t)(rest - adc) * 1023) / (rest - bottom_out);
        if (normalized > 1023) normalized = 1023;

        // Apply EQ-style sensitivity curve adjustment
        // Different curves for different rest value ranges
        normalized = apply_eq_curve_adjustment(normalized, rest);

        // Calculate adjusted linear distance (0-255) from curve-adjusted normalized
        uint8_t linear_distance = (uint8_t)((normalized * 255) / 1023);

        // If no LUT correction, return curve-adjusted linear distance
        if (strength == 0) {
            return linear_distance;
        }

        // Look up corrected distance from LUT using curve-adjusted normalized
        uint8_t lut_distance = pgm_read_byte(&distance_lut[normalized]);

        // Blend based on strength
        if (strength >= 100) {
            return lut_distance;
        }

        uint16_t blended = ((uint16_t)linear_distance * (100 - strength) + (uint16_t)lut_distance * strength) / 100;
        return (uint8_t)blended;
    }

    // Boundary checks
    if (adc <= rest) return 0;
    if (adc >= bottom_out) return 255;

    // Step 1: Normalize to 0-1023 range for LUT lookup
    uint32_t normalized = ((uint32_t)(adc - rest) * 1023) / (bottom_out - rest);
    if (normalized > 1023) normalized = 1023;

    // Step 2: Calculate linear distance (0-255)
    uint8_t linear_distance = (uint8_t)(((uint32_t)(adc - rest) * 255) / (bottom_out - rest));

    // If no correction, return linear
    if (strength == 0) {
        return linear_distance;
    }

    // Step 3: Look up corrected distance from LUT
    uint8_t lut_distance = pgm_read_byte(&distance_lut[normalized]);

    // Step 4: Blend between linear and LUT based on strength
    if (strength >= 100) {
        return lut_distance;
    }

    // Weighted average: result = linear * (100-strength)/100 + lut * strength/100
    uint16_t blended = ((uint16_t)linear_distance * (100 - strength) + (uint16_t)lut_distance * strength) / 100;
    return (uint8_t)blended;
}

/**
 * Simple wrapper using global correction strength
 */
static inline __attribute__((always_inline)) uint8_t adc_to_distance_with_lut(
    uint16_t adc,
    uint16_t rest,
    uint16_t bottom_out
) {
    extern uint8_t lut_correction_strength;
    return adc_to_distance_corrected(adc, rest, bottom_out, lut_correction_strength);
}
