// Copyright 2023 QMK
// SPDX-License-Identifier: GPL-2.0-or-later

#include "midi_function_types.h"
#include "process_midi.h"
#include "process_rgb.h"
#include <printf/printf.h>
#include QMK_KEYBOARD_H
#include "orthomidi5x14.h"
#include "via.h"
#include "vial.h"
#include "dynamic_keymap.h"
#include "process_dynamic_macro.h"
#include "matrix.h"
#include <math.h>
extern MidiDevice midi_device;
extern void force_load_per_key_cache_at_init(uint8_t layer);  // matrix.c

#define BANK_SEL_MSB_CC 0
#define BANK_SEL_LSB_CC 32

// new midi keycodes
#define MI_CC_TOG_0 0x8000
#define MI_CC_UP_0 (0x8000 + 128)
#define MI_CC_DWN_0 (0x8000 + 128 * 2)
#define MI_CC_0_0 (0x8000 + 128 * 3)
#define MI_BANK_MSB_0 ((0x8000 + 128 * 3) + 128 * 128)
#define MI_BANK_LSB_0 ((0x8000 + 128 * 4) + 128 * 128)
#define MI_PROG_0 ((0x8000 + 128 * 5) + 128 * 128)
#define MI_BANK_UP ((0x8000 + 128 * 6) + 128 * 128 + 1)
#define MI_BANK_DWN ((0x8000 + 128 * 6) + 128 * 128 + 2)
#define MI_PROG_UP ((0x8000 + 128 * 6) + 128 * 128 + 3)
#define MI_PROG_DWN ((0x8000 + 128 * 6) + 128 * 128 + 4)
#define KC_CUSTOM ((0x8000 + 128 * 6) + 128 * 128 + 5)
#define MI_VELOCITY_0 ((0x8000 + 128 * 6) + 128 * 128 + 5)
#define ENCODER_STEP_1 0xEF74  // Moved from 0xC385 to avoid collision with MI_INV (SmartChord intervals)
#undef KC_CUSTOM
#define KC_CUSTOM (0x8000 + 128 * 7) + 128 * 128 + 5 + 17

// MIDI Routing Toggle Keycodes - Fixed addresses (0xEE29-0xEE2B)
// Moved from KC_CUSTOM+1/2/3 (0xC397-0xC399) to avoid collision with SmartChord MI_CHORD_1/2/3
#define MIDI_IN_MODE_TOG    0xEE29  // Toggle MIDI In routing mode
#define USB_MIDI_MODE_TOG   0xEE2A  // Toggle USB MIDI routing mode
#define MIDI_CLOCK_SRC_TOG  0xEE2B  // Toggle MIDI clock source

// HE Velocity Curve Keycodes - Fixed addresses (0xEE2C-0xEE2D)
// Moved from KC_CUSTOM+4/5 (0xC39A-0xC39B) to avoid collision with SmartChord MI_CHORD_4/5
#define HE_VEL_CURVE_UP     0xEE2C  // Cycle to next velocity curve
#define HE_VEL_CURVE_DOWN   0xEE2D  // Cycle to previous velocity curve

// Direct HE Curve Selection (5 keycodes: 0xCCB0-0xCCB4)
#define HE_CURVE_SOFTEST    0xCCB0
#define HE_CURVE_SOFT       0xCCB1
#define HE_CURVE_MEDIUM     0xCCB2
#define HE_CURVE_HARD       0xCCB3
#define HE_CURVE_HARDEST    0xCCB4

// HE Velocity Range keycodes (combined min/max where min ≤ max) - starts at 0xCCB5
// Base address for range keycodes (8,128 keycodes total: 127×128/2 triangular number)
#define HE_VEL_RANGE_BASE   0xCCB5

// Macro-aware HE Velocity Controls (0xEC90-0xEC95)
// These modify pending values during macro recording, or layer settings when not recording
#define HE_MACRO_CURVE_UP   0xEC90  // Increment curve (with macro awareness)
#define HE_MACRO_CURVE_DOWN 0xEC91  // Decrement curve (with macro awareness)
#define HE_MACRO_MIN_UP     0xEC92  // Increment min velocity (with macro awareness)
#define HE_MACRO_MIN_DOWN   0xEC93  // Decrement min velocity (with macro awareness)
#define HE_MACRO_MAX_UP     0xEC94  // Increment max velocity (with macro awareness)
#define HE_MACRO_MAX_DOWN   0xEC95  // Decrement max velocity (with macro awareness)

// Direct HE Curve Selection (0xEC96-0xEC9A)
// These directly set the curve to a specific value (with macro/modifier awareness)
#define HE_MACRO_CURVE_0    0xEC96  // Set to SOFTEST (curve 0)
#define HE_MACRO_CURVE_1    0xEC97  // Set to SOFT (curve 1)
#define HE_MACRO_CURVE_2    0xEC98  // Set to MEDIUM (curve 2)
#define HE_MACRO_CURVE_3    0xEC99  // Set to HARD (curve 3)
#define HE_MACRO_CURVE_4    0xEC9A  // Set to HARDEST (curve 4)

// Arpeggiator & Sequencer Keycodes now defined in orthomidi5x14.h (0xCD00-0xCDFF range)


// enum custom_keycodes { MY_CUSTOM_KC = KC_CUSTOM, CUSTOM_KC_2, CUSTOM_KC_3 };

static uint8_t  CCValue[128]    = {};
static uint16_t MidiCurrentBank = 0;
static uint8_t  MidiCurrentProg = 0;
//static uint8_t tone_status[2][MIDI_TONE_COUNT];
static uint8_t tone2_status[2][MIDI_TONE_COUNT];
static uint8_t tone3_status[2][MIDI_TONE_COUNT];
static uint8_t tone4_status[2][MIDI_TONE_COUNT];
static uint8_t tone5_status[2][MIDI_TONE_COUNT];
static uint8_t tone6_status[2][MIDI_TONE_COUNT];
static uint8_t tone7_status[2][MIDI_TONE_COUNT];
bool macro_modifier_held[4] = {false, false, false, false};  // The actual definition


uint8_t modified_note;
uint8_t original_note;

// MIDI velocity and sustain settings (defined here, declared extern in process_dynamic_macro.h)
uint8_t keysplit_he_velocity_curve = 0;  // Default: Linear (curve index 0)
uint8_t keysplit_he_velocity_min = 1;
uint8_t keysplit_he_velocity_max = 127;
uint8_t triplesplit_he_velocity_curve = 0;  // Default: Linear (curve index 0)
uint8_t triplesplit_he_velocity_min = 1;
uint8_t triplesplit_he_velocity_max = 127;
uint8_t base_sustain = 0;
uint8_t keysplit_sustain = 0;
uint8_t triplesplit_sustain = 0;
// Hall Effect Sensor Linearization LUT
uint8_t lut_correction_strength = 0;  // 0=linear (no correction), 100=full logarithmic LUT

/* KEYLOGREND */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>

char keylog_str[44] = {};
int8_t transpose_number = 0;  // Variable to store the special number
int8_t octave_number = 0;
int8_t transpose_number2 = 0;  // Variable to store the special number
int8_t octave_number2 = 0;
int8_t transpose_number3 = 0;  // Variable to store the special number
int8_t octave_number3 = 0;
uint8_t velocity_number = 127;
uint8_t velocityplaceholder = 127;
int cc_up_value1[128] = {0};   // (value 1) for CC UP for each CC#
int cc_updown_value[128] = {0};   // (value 2) for CC UP for each CC#[128] = {0};   // (value 2) for CC UP for each CC#
int cc_down_value1[128] = {0};   // (value 1) for CC UP for each CC#
int velocity_sensitivity = 1;     
int cc_sensitivity = 1;   // Initial sensitivity value
uint8_t channel_number = 0;
int channelplaceholder = 0;
int hsvplaceholder = 0;
int oneshotchannel = 0;
int heldkey1 = 0;
int heldkey2 = 0;
int heldkey3 = 0;
int heldkey4 = 0;
int heldkey5 = 0;
int heldkey6 = 0;
int heldkey7 = 0;
int octaveheldkey1 = 0;
int octaveheldkey2 = 0;
int octaveheldkey3 = 0;
int octaveheldkey4 = 0;
int octaveheldkey1difference = 0; 
int octaveheldkey2difference = 0; 
int octaveheldkey3difference = 0; 
int octaveheldkey4difference = 0; 
int heldkey1difference = 0; 
int heldkey2difference = 0; 
int heldkey3difference = 0; 
int heldkey4difference = 0;
int heldkey5difference = 0; 
int heldkey6difference = 0; 
int heldkey7difference = 0; 
int trueoctaveheldkey1 = 0;
int trueoctaveheldkey2 = 0;
int trueoctaveheldkey3 = 0;
int trueoctaveheldkey4 = 0;
int trueheldkey1 = 0;
int trueheldkey2 = 0;
int trueheldkey3 = 0;
int trueheldkey4 = 0;
int trueheldkey5 = 0;
int trueheldkey6 = 0;
int trueheldkey7 = 0;
int chordkey1 = 0;
int chordkey2 = 0;
int chordkey3 = 0;
int chordkey4 = 0;
int chordkey5 = 0;
int chordkey6 = 0;
int chordkey7 = 0;
int smartchordkey2 = 0;
int smartchordkey3 = 0;
int smartchordkey4 = 0;
int smartchordkey5 = 0;
int smartchordkey6 = 0;
int smartchordkey7 = 0;
int smartchordstatus = 0;
int inversionposition = 0;
int rootnote = 13;
int bassnote = 13;
int trueheldkey[7];
uint8_t chordkey1_led_index = 99;
uint8_t chordkey2_led_index = 99;
uint8_t chordkey3_led_index = 99;
uint8_t chordkey4_led_index = 99;
uint8_t chordkey5_led_index = 99;
uint8_t chordkey6_led_index = 99;
uint8_t chordkey7_led_index = 99;
uint8_t chordkey1_led_index2 = 99;
uint8_t chordkey2_led_index2 = 99;
uint8_t chordkey3_led_index2 = 99;
uint8_t chordkey4_led_index2 = 99;
uint8_t chordkey5_led_index2 = 99;
uint8_t chordkey6_led_index2 = 99;
uint8_t chordkey7_led_index2 = 99;
uint8_t chordkey1_led_index3 = 99;
uint8_t chordkey2_led_index3 = 99;
uint8_t chordkey3_led_index3 = 99;
uint8_t chordkey4_led_index3 = 99;
uint8_t chordkey5_led_index3 = 99;
uint8_t chordkey6_led_index3 = 99;
uint8_t chordkey7_led_index3 = 99;
uint8_t chordkey1_led_index4 = 99;
uint8_t chordkey2_led_index4 = 99;
uint8_t chordkey3_led_index4 = 99;
uint8_t chordkey4_led_index4 = 99;
uint8_t chordkey5_led_index4 = 99;
uint8_t chordkey6_led_index4 = 99;
uint8_t chordkey7_led_index4 = 99;
uint8_t chordkey1_led_index5 = 99;
uint8_t chordkey2_led_index5 = 99;
uint8_t chordkey3_led_index5 = 99;
uint8_t chordkey4_led_index5 = 99;
uint8_t chordkey5_led_index5 = 99;
uint8_t chordkey6_led_index5 = 99;
uint8_t chordkey7_led_index5 = 99;
uint8_t chordkey1_led_index6 = 99;
uint8_t chordkey2_led_index6 = 99;
uint8_t chordkey3_led_index6 = 99;
uint8_t chordkey4_led_index6 = 99;
uint8_t chordkey5_led_index6 = 99;
uint8_t chordkey6_led_index6 = 99;
uint8_t chordkey7_led_index6 = 99;
uint8_t dynamic_range = 127;  // Maximum allowed differential between velocity min and max
int ccencoder = 130;
int velocityencoder = 130;
int channelencoder = 130;
int transposeencoder = 130;
int oledkeyboard = 0;
int smartchordchanger = 0;
int colorblindmode = 0;
int smartchordlight = 0;
int smartchordlightmode = 0;
int keysplitnumber = 28931;
uint8_t keysplitchannel = 0;
uint8_t keysplit2channel = 0;
uint8_t keysplitstatus = 0;
uint8_t keysplittransposestatus = 0;
uint8_t keysplitvelocitystatus = 0;
uint8_t positiveinversion = 0;
int8_t transpositionplaceholder = 0;
int8_t progression_octave_offset = 0;
int8_t randomprogression = 0;
static uint8_t spaceheld = 0;
bool cclooprecording = false;
bool channeloverride = false;
bool velocityoverride = false;
bool transposeoverride = false;
bool truesustain = false;
bool keysplitmodifierheld = false;
bool triplesplitmodifierheld = false;
bool global_edit_modifier_held = false;
uint16_t last_keysplit_press_time = 0;
uint16_t last_triplesplit_press_time = 0;

uint32_t last_bpm_flash_time = 0;
bool bpm_flash_state = false;

static uint32_t tap_key_press_time = 0;
static bool tap_key_held = false;

// ============================================================================
// DWT CYCLE COUNTER SETUP - 48MHz STM32F412CE
// ============================================================================

#define DWT_CTRL   (*(volatile uint32_t*)0xE0001000)
#define DWT_CYCCNT (*(volatile uint32_t*)0xE0001004)
#define DEM_CR     (*(volatile uint32_t*)0xE000EDFC)
#define DEM_CR_TRCENA (1 << 24)

#define CPU_FREQ_MHZ 48  // STM32F412CE at 48MHz

// MIDI Clock constants
#define MIDI_CLOCK    0xF8
#define MIDI_START    0xFA
#define MIDI_STOP     0xFC
#define MIDI_CONTINUE 0xFB

// Initialize DWT cycle counter
void dwt_init(void) {
    // Enable trace
    DEM_CR |= DEM_CR_TRCENA;
    
    // Unlock DWT (required on some STM32)
    *((volatile uint32_t*)0xE0001FB0) = 0xC5ACCE55;
    
    // Reset cycle counter
    DWT_CYCCNT = 0;
    
    // Enable cycle counter
    DWT_CTRL |= 1;
}

// Get current cycle count
static inline uint32_t dwt_get_cycles(void) {
    return DWT_CYCCNT;
}

// Convert cycles to microseconds (48MHz clock)
static inline uint32_t cycles_to_us(uint32_t cycles) {
    return cycles / CPU_FREQ_MHZ;  // 48 cycles = 1 microsecond at 48MHz
}

// Convert microseconds to cycles
static inline uint32_t us_to_cycles(uint32_t us) {
    return us * CPU_FREQ_MHZ;  // microseconds * 48 cycles/us
}

// ============================================================================
// CLOCK MODE AND STATE
// ============================================================================

typedef enum {
    CLOCK_MODE_INTERNAL,  // Generating clock from tap tempo/manual BPM
    CLOCK_MODE_EXTERNAL   // Receiving clock from Reaper/external source
} clock_mode_t;

static clock_mode_t clock_mode = CLOCK_MODE_INTERNAL;

// ============================================================================
// MIDI ROUTING MODES
// ============================================================================

// MIDI routing mode variables (types defined in orthomidi5x14.h)
// Both default to PROCESS_ALL for full QMK processing (smartchord, LED, recording)
midi_in_mode_t midi_in_mode = MIDI_ROUTE_PROCESS_ALL;
usb_midi_mode_t usb_midi_mode = MIDI_ROUTE_PROCESS_ALL;
midi_clock_source_t midi_clock_source = CLOCK_SOURCE_LOCAL;  // Default: local clock

// MIDI routing state strings for OLED (must match enum order)
// Order: PROCESS_ALL, THRU, CLOCK_ONLY, IGNORE
static const char* midi_in_mode_names[] = {
    "IN:PROC",    // MIDI_ROUTE_PROCESS_ALL - process through QMK
    "IN:THRU",    // MIDI_ROUTE_THRU - forward to USB+HW out
    "IN:CLK",     // MIDI_ROUTE_CLOCK_ONLY - process clock, thru rest
    "IN:IGN"      // MIDI_ROUTE_IGNORE - ignore all
};

static const char* usb_midi_mode_names[] = {
    "USB:PROC",   // MIDI_ROUTE_PROCESS_ALL - process through QMK
    "USB:THRU",   // MIDI_ROUTE_THRU - forward to USB+HW out
    "USB:CLK",    // MIDI_ROUTE_CLOCK_ONLY - process clock, thru rest
    "USB:IGN"     // MIDI_ROUTE_IGNORE - ignore all
};

static const char* clock_source_names[] = {
    "CLK:LOC",
    "CLK:USB",
    "CLK:IN"
};

// ============================================================================
// HE VELOCITY CURVE AND RANGE SYSTEM
// ============================================================================

// Global velocity curve and range settings
uint8_t he_velocity_curve = 0;  // Default: Linear (curve index 0)
uint8_t he_velocity_min = 1;    // Default: 1
uint8_t he_velocity_max = 127;  // Default: 127

// Velocity curve names for display
__attribute__((unused)) static const char* velocity_curve_names[] = {
    "SOFTEST",
    "SOFT",
    "MEDIUM",
    "HARD",
    "HARDEST"
};

// Apply velocity curve and range to travel value (0-255) -> MIDI velocity (1-127)
// DEPRECATED: Use get_he_velocity_from_position() instead for per-key support
uint8_t apply_he_velocity_curve(uint8_t travel_value) {
    // Input: travel_value is 0-255 from analog_matrix_get_travel_normalized()
    // Output: MIDI velocity 1-127 with curve applied

    // Apply curve to travel (0-255 input -> 0-255 output)
    uint8_t curved_travel = apply_curve(travel_value, he_velocity_curve);

    // Map curved travel to velocity range (he_velocity_min to he_velocity_max)
    uint8_t range = he_velocity_max - he_velocity_min;
    int16_t velocity = he_velocity_min + ((int16_t)curved_travel * range) / 255;

    // Clamp to valid MIDI velocity range (1-127)
    if (velocity < 1) velocity = 1;
    if (velocity > 127) velocity = 127;

    return (uint8_t)velocity;
}

// Cycle through velocity curves (0-16: 7 factory + 10 user = 17 total)
void cycle_he_velocity_curve(bool forward) {
    if (forward) {
        he_velocity_curve = (he_velocity_curve + 1) % 17;
    } else {
        if (he_velocity_curve == 0) {
            he_velocity_curve = 16;
        } else {
            he_velocity_curve--;
        }
    }
}

// Set velocity range with validation
void set_he_velocity_range(uint8_t min, uint8_t max) {
    // Ensure valid range
    if (min < 1) min = 1;
    if (max > 127) max = 127;
    if (min > max) {
        // Swap if reversed
        uint8_t temp = min;
        min = max;
        max = temp;
    }

    he_velocity_min = min;
    he_velocity_max = max;
}

// Helper: Get velocity curve for a specific key with 3-tier priority
// split_type: 0=base, 1=keysplit, 2=triplesplit
// Priority 1: Per-key curve (if flag enabled)
// Priority 2: Split-specific curve (if keysplitvelocitystatus enables it)
// Priority 3: Global fallback curve
uint8_t get_key_velocity_curve(uint8_t layer, uint8_t row, uint8_t col, uint8_t split_type) {
    uint8_t key_index = row * 14 + col;
    if (key_index < 70 && layer < 12) {
        // DIAGNOSTIC: Only use cache, never access large per_key_actuations[] array
        // This tests whether accessing that array is causing USB disconnect
        uint8_t flags;
        if (layer == active_per_key_cache_layer) {
            flags = active_per_key_cache[key_index].flags;
        } else {
            // Don't access large array - use 0 (no per-key velocity flag set)
            flags = 0;
        }

        // Priority 1: Check if this specific key uses per-key velocity curve
        // DISABLED: Per-key velocity curve requires accessing large array
        // if (flags & PER_KEY_FLAG_USE_PER_KEY_VELOCITY_CURVE) {
        //     return per_key_actuations[layer].keys[key_index].velocity_curve;
        // }
        (void)flags;  // Suppress unused variable warning
    }

    // Priority 2: Check for split-specific curve
    // keysplitvelocitystatus: 0=disabled, 1=keysplit only, 2=triplesplit only, 3=both
    if (split_type == 1 && (keyboard_settings.keysplitvelocitystatus == 1 || keyboard_settings.keysplitvelocitystatus == 3)) {
        return keyboard_settings.keysplit_he_velocity_curve;
    } else if (split_type == 2 && (keyboard_settings.keysplitvelocitystatus == 2 || keyboard_settings.keysplitvelocitystatus == 3)) {
        return keyboard_settings.triplesplit_he_velocity_curve;
    }

    // Priority 3: Fallback to global curve
    return keyboard_settings.he_velocity_curve;
}

// Get HE velocity from matrix position (row, col) using per-key or global settings
// This is called when a MIDI note is triggered to get the velocity from the analog matrix
// Now uses pre-calculated velocity from velocity modes (peak, speed, combined) in matrix.c
uint8_t get_he_velocity_from_position(uint8_t row, uint8_t col) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);

    // Check if this layer uses fixed velocity
    if (layer_actuations[current_layer].flags & LAYER_ACTUATION_FLAG_USE_FIXED_VELOCITY) {
        return velocity_number;  // Use global fixed velocity
    }

    // Get velocity mode from layer settings
    uint8_t velocity_mode = analog_matrix_get_velocity_mode();

    // Get velocity curve (per-key or global) and global min/max
    uint8_t curve_index = get_key_velocity_curve(current_layer, row, col, 0);  // split_type=0 (base)
    uint8_t min_vel = keyboard_settings.he_velocity_min;
    uint8_t max_vel = keyboard_settings.he_velocity_max;

    uint8_t raw_value;

    if (velocity_mode == 0) {
        // Mode 0: Fixed velocity - use the global velocity_number directly
        // No curve or scaling applied, just the user's chosen fixed velocity
        return velocity_number;
    }

    // Modes 1-3: Use pre-calculated raw velocity from matrix.c
    // This is the velocity calculated from peak travel, speed, or combined
    raw_value = analog_matrix_get_velocity_raw(row, col);

    // If raw_velocity is 0 (not yet captured), fall back to current travel
    if (raw_value == 0) {
        raw_value = analog_matrix_get_travel_normalized(row, col);
    }

    // Apply curve to raw value (0-255 input, 0-255 output)
    uint8_t curved_value = apply_curve(raw_value, curve_index);

    // Map curved value to velocity range (min_vel to max_vel)
    uint8_t range = max_vel - min_vel;
    int16_t velocity = min_vel + ((int16_t)curved_value * range) / 255;

    // Clamp to valid MIDI velocity range (1-127)
    if (velocity < 1) velocity = 1;
    if (velocity > 127) velocity = 127;

    return (uint8_t)velocity;
}

// Get Keysplit HE velocity from matrix position (row, col) using per-key or global settings
// Now uses pre-calculated velocity from velocity modes (peak, speed, combined) in matrix.c
uint8_t get_keysplit_he_velocity_from_position(uint8_t row, uint8_t col) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);

    // Get velocity mode from layer settings
    uint8_t velocity_mode = analog_matrix_get_velocity_mode();

    if (velocity_mode == 0) {
        // Mode 0: Fixed velocity - use the global velocity_number directly
        return velocity_number;
    }

    // Get velocity curve (per-key or global) and keysplit min/max
    uint8_t curve_index = get_key_velocity_curve(current_layer, row, col, 1);  // split_type=1 (keysplit)
    uint8_t min_vel = keyboard_settings.keysplit_he_velocity_min;
    uint8_t max_vel = keyboard_settings.keysplit_he_velocity_max;

    // Modes 1-3: Use pre-calculated raw velocity from matrix.c
    uint8_t raw_value = analog_matrix_get_velocity_raw(row, col);

    // If raw_velocity is 0 (not yet captured), fall back to current travel
    if (raw_value == 0) {
        raw_value = analog_matrix_get_travel_normalized(row, col);
    }

    // Apply curve to raw value (0-255 input, 0-255 output)
    uint8_t curved_value = apply_curve(raw_value, curve_index);

    // Map curved value to velocity range (min_vel to max_vel)
    uint8_t range = max_vel - min_vel;
    int16_t velocity = min_vel + ((int16_t)curved_value * range) / 255;

    // Clamp to valid MIDI velocity range (1-127)
    if (velocity < 1) velocity = 1;
    if (velocity > 127) velocity = 127;

    return (uint8_t)velocity;
}

// Get Triplesplit HE velocity from matrix position (row, col) using per-key or global settings
// Now uses pre-calculated velocity from velocity modes (peak, speed, combined) in matrix.c
uint8_t get_triplesplit_he_velocity_from_position(uint8_t row, uint8_t col) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);

    // Get velocity mode from layer settings
    uint8_t velocity_mode = analog_matrix_get_velocity_mode();

    if (velocity_mode == 0) {
        // Mode 0: Fixed velocity - use the global velocity_number directly
        return velocity_number;
    }

    // Get velocity curve (per-key or global) and triplesplit min/max
    uint8_t curve_index = get_key_velocity_curve(current_layer, row, col, 2);  // split_type=2 (triplesplit)
    uint8_t min_vel = keyboard_settings.triplesplit_he_velocity_min;
    uint8_t max_vel = keyboard_settings.triplesplit_he_velocity_max;

    // Modes 1-3: Use pre-calculated raw velocity from matrix.c
    uint8_t raw_value = analog_matrix_get_velocity_raw(row, col);

    // If raw_velocity is 0 (not yet captured), fall back to current travel
    if (raw_value == 0) {
        raw_value = analog_matrix_get_travel_normalized(row, col);
    }

    // Apply curve to raw value (0-255 input, 0-255 output)
    uint8_t curved_value = apply_curve(raw_value, curve_index);

    // Map curved value to velocity range (min_vel to max_vel)
    uint8_t range = max_vel - min_vel;
    int16_t velocity = min_vel + ((int16_t)curved_value * range) / 255;

    // Clamp to valid MIDI velocity range (1-127)
    if (velocity < 1) velocity = 1;
    if (velocity > 127) velocity = 127;

    return (uint8_t)velocity;
}

// Temporary mode display variables
static uint32_t mode_display_timer = 0;
static char mode_display_msg[64] = "";
static bool mode_display_active = false;
#define MODE_DISPLAY_DURATION 2000  // Show for 2 seconds

// ============================================================================
// EXTERNAL CLOCK RECEPTION STATE
// ============================================================================

#define EXT_CLOCK_BUFFER_SIZE 32  // Increased from 8 for better averaging
#define EXT_CLOCK_TIMEOUT_CYCLES (48000000 * 2)  // 2 seconds at 48MHz
#define BPM_UPDATE_THRESHOLD 100000  // 0.5 BPM - only update if change is larger
#define BPM_SMOOTH_FACTOR 32  // Higher = slower response, smoother

typedef struct {
    volatile uint32_t last_cycle_count;
    volatile uint32_t interval_buffer_us[EXT_CLOCK_BUFFER_SIZE];
    volatile uint8_t buffer_index;
    volatile uint8_t pulse_count;  // 0-23 for MIDI clock
    volatile bool running;
    volatile bool synced;  // True after we have enough samples
    volatile uint32_t last_pulse_cycles;  // For timeout detection
    volatile uint32_t smoothed_bpm;  // Running average of BPM
    volatile bool bpm_locked;  // True when BPM is stable
} external_clock_state_t;

static external_clock_state_t ext_clock = {
    .last_cycle_count = 0,
    .buffer_index = 0,
    .pulse_count = 0,
    .running = false,
    .synced = false,
    .last_pulse_cycles = 0,
    .smoothed_bpm = 0,
    .bpm_locked = false
};

// ============================================================================
// INTERNAL CLOCK TRANSMISSION STATE
// ============================================================================

typedef struct {
    volatile bool running;
    volatile uint32_t next_pulse_cycles;  // When to send next pulse (in DWT cycles)
    volatile uint32_t pulse_interval_us;  // Microseconds between pulses
    volatile uint8_t pulse_count;  // 0-23 for beat tracking
} internal_clock_state_t;

static internal_clock_state_t int_clock = {
    .running = false,
    .next_pulse_cycles = 0,
    .pulse_interval_us = 0,
    .pulse_count = 0
};

// Add these variables at the top with your other global variables
static bool sustain_pedal_held = false;
static bool sustain_keys_captured = false;

// Arrays to track keys pressed/released while sustain is held
static uint16_t sustain_pressed_keys[20];  // Keys pressed while sustain held
static uint16_t sustain_released_keys[20]; // Keys released while sustain held
static uint8_t sustain_pressed_count = 0;
static uint8_t sustain_released_count = 0;

// Add these definitions at the top
#define TAP_TIMEOUT_MS 2000    // Reset tap counting after 2 seconds of no taps
#define MAX_TAPS_AVERAGE 8     // How many taps to average

static uint32_t last_tap_time = 0;
static uint32_t tap_times[MAX_TAPS_AVERAGE];

// Hold detection for sequencer buttons (500ms threshold)
#define SEQ_HOLD_THRESHOLD 500
static uint32_t seq_play_press_time = 0;
static uint32_t seq_preset_press_time = 0;
static uint16_t seq_preset_held_keycode = 0;
static uint8_t active_taps = 0;
uint32_t current_bpm = 0;  // Starting with 120 as default
static bool tap_tempo_active = false;
uint8_t bpm_beat_count = 0;  // Track which beat we're on (0-3)

extern bool overdub_button_held;
extern bool mute_button_held;
extern bool octave_doubler_button_held;
extern uint8_t unsynced_mode_active;
extern bool sample_mode_active;

static bool display_copy_active = false;
static bool display_paste_active = false; 
static uint8_t display_source_macro = 0;



// Backup of held keys when sustain was first pressed
static struct {
    int trueheldkey1, trueheldkey2, trueheldkey3, trueheldkey4, trueheldkey5, trueheldkey6, trueheldkey7;
    int heldkey1, heldkey2, heldkey3, heldkey4, heldkey5, heldkey6, heldkey7;
    int heldkey1difference, heldkey2difference, heldkey3difference, heldkey4difference, heldkey5difference, heldkey6difference, heldkey7difference;
    int trueoctaveheldkey1, trueoctaveheldkey2, trueoctaveheldkey3, trueoctaveheldkey4;
    int octaveheldkey1, octaveheldkey2, octaveheldkey3, octaveheldkey4;
    int octaveheldkey1difference, octaveheldkey2difference, octaveheldkey3difference, octaveheldkey4difference;
} sustain_backup;


uint32_t calculate_tap_bpm(void) {
    uint32_t total_interval = 0;
    uint8_t intervals = 0;
    
    // Calculate the average interval between taps
    for (uint8_t i = 1; i < active_taps; i++) {
        uint32_t interval = tap_times[i] - tap_times[i-1];
        total_interval += interval;
        intervals++;
    }
    
    if (intervals == 0) return current_bpm; // Return current if not enough taps
    
    // Calculate BPM with high precision: (60,000 ms/minute * 100000) / (average interval in ms)
    uint32_t calculated_bpm = (uint32_t)((6000000000ULL) / (total_interval / intervals));
    
    // SNAP TO NEAREST INTEGER BPM
    // Round to nearest whole number
    uint32_t bpm_integer = (calculated_bpm + 50000) / 100000;  // +50000 rounds to nearest
    calculated_bpm = bpm_integer * 100000;  // Convert back to internal format
    
    // Clamp to reasonable BPM range (30-300 BPM)
    if (calculated_bpm < 3000000) calculated_bpm = 3000000;      // 30.00000 BPM
    if (calculated_bpm > 30000000) calculated_bpm = 30000000;   // 300.00000 BPM
    
    return calculated_bpm;
}



// Forward declarations
void stop_chord_progression(void);

#define CHORD_MAJOR      0xC396 // Major triad
#define CHORD_MINOR      0xC397 // Minor triad
#define CHORD_DIM        0xC398 // Diminished triad
#define CHORD_AUG        0xC399 // Augmented triad
#define CHORD_MAJ6       0xC3A2 // Major 6th
#define CHORD_MAJ7       0xC3A9 // Major 7th
#define CHORD_MIN7       0xC3AA // Minor 7th
#define CHORD_MIN7B5     0xC3AB // Minor 7 flat 5 (half-diminished)
#define CHORD_DIM7       0xC3AC // Diminished 7th
#define CHORD_DOM7       0xC3A8 // Dominant 7 (using Minor 7th chord type)
#define CHORD_SUS2       0xC39B // Sus2 chord
#define CHORD_SUS4       0xC39C // Sus4 chord
#define CHORD_MAJ9       0xC3B5 // Major 9th chord
#define CHORD_MIN9       0xC3B4 // Minor 9th chord
#define CHORD_DOM7B9     0xC3B8 // Dominant 7 flat 9
#define CHORD_MAJ6       0xC3A2 // Major 6th chord
#define CHORD_ADD4       0xC3A6 // Add4 chord
#define CHORD_ADD2       0xC3A4 // Add2 chord
#define CHORD_DOM9       0xC3B3 // Dominant 9 chord
#define CHORD_ADD9       0xC3AF // Add9 chord


// Base note keycode (C note)
#define BASE_NOTE_KEYCODE 28931

// Global variables for chord progression
bool progression_active = false;
bool progression_key_held = false;
uint8_t current_progression = 0;
uint8_t current_chord_index = 0;
uint32_t next_chord_time = 0;
uint8_t progression_key_offset = 0;

// Variables to track currently pressed keys in the progression
uint16_t current_chord_type = 0;
uint16_t current_note_keycode = 0;
uint8_t current_root_midi_note = 0;

// Progression data structure
typedef struct {
    uint8_t length;              // Number of chords in progression
    uint16_t chord_types[16];    // Type of each chord (major, minor, etc)
    uint8_t note_offsets[16];    // Scale degree of each chord (0=I, 2=ii, etc)
    uint8_t chord_durations[16]; // Duration in bars (1 = one bar, 2 = two bars)
    bool is_minor;               // Whether this is a minor progression
} chord_progression_t;

const chord_progression_t chord_progressions[] = {
    // 1. Simple Minor: i-VII-VI (Am-G-F)
    {
        .length = 3,
        .chord_types = {CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {9, 7, 5}, // Am, G, F (relative to C major)
        .chord_durations = {4, 4, 8},
        .is_minor = true
    },
    
    // 2. Simple Major: I-IV-V (C-F-G)
    {
        .length = 3,
        .chord_types = {CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {0, 5, 7}, // C, F, G (relative to C major)
        .chord_durations = {4, 4, 8},
        .is_minor = false
    },
    
    // 3. Hopeful Minor: VI-VII-i (F-G-Am)
    {
        .length = 3,
        .chord_types = {CHORD_MAJOR, CHORD_MAJOR, CHORD_MINOR},
        .note_offsets = {5, 7, 9}, // F, G, Am (relative to C major)
        .chord_durations = {4, 4, 8},
        .is_minor = true
    },
    
    // 4. 50s Progression: I-vi-IV-V (C-Am-F-G)
    {
        .length = 4,
        .chord_types = {CHORD_MAJOR, CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {0, 9, 5, 7}, // C, Am, F, G (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 5. Classic Four-Chord: I-V-vi-IV (C-G-Am-F)
    {
        .length = 4,
        .chord_types = {CHORD_MAJOR, CHORD_MAJOR, CHORD_MINOR, CHORD_MAJOR},
        .note_offsets = {0, 7, 9, 5}, // C, G, Am, F (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 6. Axis Progression: vi-IV-I-V (Am-F-C-G)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {9, 5, 0, 7}, // Am, F, C, G (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 7. Natural Minor: i-iv-VII-I (Am-Dm-G-C)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {9, 2, 7, 0}, // Am, Dm, G, C (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 8. Rock Progression: I-V-IV-IV (C-G-F-F)
    {
        .length = 4,
        .chord_types = {CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {0, 7, 5, 5}, // C, G, F, F (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 9. Downward Minor: iv-III-i-VII (Dm-C-Am-G)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MAJOR, CHORD_MINOR, CHORD_MAJOR},
        .note_offsets = {2, 0, 9, 7}, // Dm, C, Am, G (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 10. Sensitive Minor: i-VII-v-VI (Am-G-Em-F)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MAJOR, CHORD_MINOR, CHORD_MAJOR},
        .note_offsets = {9, 7, 4, 5}, // Am, G, Em, F (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 11. Circular Minor: i-v-VI-ii (Am-Em-F-Dm)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MINOR, CHORD_MAJOR, CHORD_MINOR},
        .note_offsets = {9, 4, 5, 2}, // Am, Em, F, Dm (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 12. Summer Hit: I-ii-vi-V (C-Dm-Am-G)
    {
        .length = 4,
        .chord_types = {CHORD_MAJOR, CHORD_MINOR, CHORD_MINOR, CHORD_MAJOR},
        .note_offsets = {0, 2, 9, 7}, // C, Dm, Am, G (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 13. Canon Progression: I-V-vi-iii-IV-I-IV-V (C-G-Am-Em-F-C-F-G)
    {
        .length = 8,
        .chord_types = {CHORD_MAJOR, CHORD_MAJOR, CHORD_MINOR, CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {0, 7, 9, 4, 5, 0, 5, 7}, // C, G, Am, Em, F, C, F, G (relative to C major)
        .chord_durations = {4, 4, 4, 4, 4, 4, 4, 4},
        .is_minor = false
    },
    
    // 14. Andalusian Cadence: i-VII-VI-V (Am-G-F-E)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {9, 7, 5, 4}, // Am, G, F, E (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 15. Harmonic Tension: i-bVI-bVII-V (Am-F-G-E)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {9, 5, 7, 4}, // Am, F, G, E (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 16. Creep Progression: I-III-IV-iv (C-E-F-Fm)
    {
        .length = 4,
        .chord_types = {CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MINOR},
        .note_offsets = {0, 4, 5, 5}, // C, E, F, Fm (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 17. Pumped Kicks: I-III-VII-II (C-E-G-D)
    {
        .length = 4,
        .chord_types = {CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {0, 4, 7, 2}, // C, E, G, D (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 18. Melancholic Minor: i-bVII-VI-V (Am-Ab-G-F)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {9, 8, 7, 5}, // Am, Ab, G, F (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 19. Rebel Progression: I-V-bVII-IV (C-G-Bb-F)
    {
        .length = 4,
        .chord_types = {CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MAJOR},
        .note_offsets = {0, 7, 10, 5}, // C, G, Bb, F (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 20. Darkening Minor: i-V-VI-VIm (Am-E-F-Fm)
    {
        .length = 4,
        .chord_types = {CHORD_MINOR, CHORD_MAJOR, CHORD_MAJOR, CHORD_MINOR},
        .note_offsets = {9, 4, 5, 5}, // Am, E, F, Fm (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 21. Ambient Float: Isus2-IVsus2-vi-V (Csus2-Fsus2-Am-G)
    {
        .length = 4,
        .chord_types = {CHORD_SUS2, CHORD_SUS2, CHORD_MINOR, CHORD_MAJOR},
        .note_offsets = {0, 5, 9, 7}, // Csus2, Fsus2, Am, G (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 22. Shoegaze Shimmer: IVsus2-Vsus4-Isus2-vi (Fsus2-Gsus4-Csus2-Am)
    {
        .length = 4,
        .chord_types = {CHORD_SUS2, CHORD_SUS4, CHORD_SUS2, CHORD_MINOR},
        .note_offsets = {5, 7, 0, 9}, // Fsus2, Gsus4, Csus2, Am (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 23. 2-5-1 Progression: ii7-V7-Imaj7 (Dm7-G7-Cmaj7)
    {
        .length = 3,
        .chord_types = {CHORD_MIN7, CHORD_DOM7, CHORD_MAJ7},
        .note_offsets = {2, 7, 0}, // Dm7, G7, Cmaj7 (relative to C major)
        .chord_durations = {4, 4, 8},
        .is_minor = false
    },
    
    // 24. Jazz Minor: im7-bVImaj7-bVII7-V7 (Am7-Fmaj7-G7-E7)
    {
        .length = 4,
        .chord_types = {CHORD_MIN7, CHORD_MAJ7, CHORD_DOM7, CHORD_DOM7},
        .note_offsets = {9, 5, 7, 4}, // Am7, Fmaj7, G7, E7 (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 25. 6-2-5-1 Progression: vi7-ii7-V7-Imaj7 (Am7-Dm7-G7-Cmaj7)
    {
        .length = 4,
        .chord_types = {CHORD_MIN7, CHORD_MIN7, CHORD_DOM7, CHORD_MAJ7},
        .note_offsets = {9, 2, 7, 0}, // Am7, Dm7, G7, Cmaj7 (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 26. Gentle City: Imaj7-iim7-iiim7-IVadd2 (Cmaj7-Dm7-Em7-Fadd2)
    {
        .length = 4,
        .chord_types = {CHORD_MAJ7, CHORD_MIN7, CHORD_MIN7, CHORD_ADD2},
        .note_offsets = {0, 2, 4, 5}, // Cmaj7, Dm7, Em7, Fadd2 (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 27. Diminished Dominant: VI-#viidim-V7-i-VII (F-Abdim-E7-Am-G)
    {
        .length = 5,
        .chord_types = {CHORD_MAJOR, CHORD_DIM, CHORD_DOM7, CHORD_MINOR, CHORD_MAJOR},
        .note_offsets = {5, 8, 4, 9, 7}, // F, Abdim, E7, Am, G (relative to C major)
        .chord_durations = {4, 2, 2, 4, 4},
        .is_minor = true
    },
    
    // 28. Anime Progression: IVmaj7-V7-iiim7-vim7-iim7-III7-vim7 (Fmaj7-G7-Em7-Am7-Dm7-E7-Am7)
    {
        .length = 7,
        .chord_types = {CHORD_MAJ7, CHORD_DOM7, CHORD_MIN7, CHORD_MIN7, CHORD_MIN7, CHORD_DOM7, CHORD_MIN7},
        .note_offsets = {5, 7, 4, 9, 2, 4, 9}, // Fmaj7, G7, Em7, Am7, Dm7, E7, Am7
        .chord_durations = {4, 4, 4, 4, 4, 4, 8},
        .is_minor = false
    },
    
    // 29. She's Lovely: IVmaj7-III7-vim7-II7-iim7-V7-Imaj7 (Fmaj7-E7-Am7-D7-Dm7-G7-Cmaj7)
    {
        .length = 7,
        .chord_types = {CHORD_MAJ7, CHORD_DOM7, CHORD_MIN7, CHORD_DOM7, CHORD_MIN7, CHORD_DOM7, CHORD_MAJ7},
        .note_offsets = {5, 4, 9, 2, 2, 7, 0}, // Fmaj7, E7, Am7, D7, Dm7, G7, Cmaj7
        .chord_durations = {4, 4, 4, 4, 4, 4, 8},
        .is_minor = false
    },
    
    // 30. Bring The 9th: vim9-iiim9-iim9-Imaj9 (Am9-Em9-Dm9-Cmaj9)
    {
        .length = 4,
        .chord_types = {CHORD_MIN9, CHORD_MIN9, CHORD_MIN9, CHORD_MAJ9},
        .note_offsets = {9, 4, 2, 0}, // Am9, Em9, Dm9, Cmaj9 (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 31. Neo-Pop Turnaround: IVmaj7-V7-iiim9-vim7 (Fmaj7-G7-Em9-Am7)
    {
        .length = 4,
        .chord_types = {CHORD_MAJ7, CHORD_DOM7, CHORD_MIN9, CHORD_MIN7},
        .note_offsets = {5, 7, 4, 9}, // Fmaj7, G7, Em9, Am7 (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 32. Modern Minor 9: im9-ivaddD-bVImaj7-bVII9 (Am9-Dmadd9-Fmaj7-G9)
    {
        .length = 4,
        .chord_types = {CHORD_MIN9, CHORD_ADD9, CHORD_MAJ7, CHORD_ADD2},
        .note_offsets = {9, 2, 5, 7}, // Am9, Dmadd9, Fmaj7, Gadd2 (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 33. Lo-Fi Ninths: im9-iim9-vm9 (Am9-Dm9-Em9)
    {
        .length = 3,
        .chord_types = {CHORD_MIN9, CHORD_MIN9, CHORD_MIN9},
        .note_offsets = {9, 2, 4}, // Am9, Dm9, Em9 (relative to C major)
        .chord_durations = {4, 4, 8},
        .is_minor = true
    },
    
    // 34. Ninth Journey: im9-vm9-VImaj9-im9-VImaj9-viim9 (Am9-Em9-Fmaj9-Am9-Fmaj9-Gm9)
    {
        .length = 6,
        .chord_types = {CHORD_MIN9, CHORD_MIN9, CHORD_MAJ9, CHORD_MIN9, CHORD_MAJ9, CHORD_MIN9},
        .note_offsets = {9, 4, 5, 9, 5, 7}, // Am9, Em9, Fmaj9, Am9, Fmaj9, Gm9 (relative to C major)
        .chord_durations = {4, 4, 8, 4, 4, 8},
        .is_minor = true
    },
    
    // 35. Descending Diminished: IVmaj7-iiim7-#iiidim7-iim7-iim7b5-Imaj7 (Fmaj7-Em7-Ebdim7-Dm7-Dm7b5-Cmaj7)
    {
        .length = 6,
        .chord_types = {CHORD_MAJ7, CHORD_MIN7, CHORD_DIM7, CHORD_MIN7, CHORD_MIN7B5, CHORD_MAJ7},
        .note_offsets = {5, 4, 3, 2, 2, 0}, // Fmaj7, Em7, Ebdim7, Dm7, Dm7b5, Cmaj7
        .chord_durations = {4, 2, 2, 2, 2, 4},
        .is_minor = false
    },
    
    // 36. Diminished Bridge: Imaj7-#idim7-iim7-#iidim7-iiim7-biiidim7 (Cmaj7-C#dim7-Dm7-Ebdim7-Em7-Ebdim7)
    {
        .length = 6,
        .chord_types = {CHORD_MAJ7, CHORD_DIM7, CHORD_MIN7, CHORD_DIM7, CHORD_MIN7, CHORD_DIM7},
        .note_offsets = {0, 1, 2, 3, 4, 3}, // Cmaj7, C#dim7, Dm7, Ebdim7, Em7, Ebdim7
        .chord_durations = {4, 2, 4, 2, 4, 2},
        .is_minor = false
    },
    
    // 37. Minor Jazz II-V-I: im9-IVmaj7-iim7b5-V7 (Am9-Fmaj7-Dm7b5-E7)
    {
        .length = 4,
        .chord_types = {CHORD_MIN9, CHORD_MAJ7, CHORD_MIN7B5, CHORD_DOM7},
        .note_offsets = {9, 5, 2, 4}, // Am9, Fmaj7, Dm7b5, E7 (relative to C major)
        .chord_durations = {4, 4, 4, 4},
        .is_minor = true
    },
    
    // 38. Backdoor Progression: I-vi-ii-bVII7-I (Cmaj7-Am7-Dm7-Bb7)
    {
        .length = 4,
        .chord_types = {CHORD_MAJ7, CHORD_MIN7, CHORD_MIN7, CHORD_DOM7},
        .note_offsets = {0, 9, 2, 10, 0}, // Cmaj7, Am7, Dm7, Bb7
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 39. Modal Mixture: Imaj7-bIIImaj7-iim7-IVm6 (Cmaj7-Ebmaj7-Dm7-Em7)
    {
        .length = 4,
        .chord_types = {CHORD_MAJ7, CHORD_MAJ7, CHORD_MIN7, CHORD_MIN7},
        .note_offsets = {0, 3, 2, 4}, // Cmaj7, Ebmaj7, Dm7, Em7
        .chord_durations = {4, 4, 4, 4},
        .is_minor = false
    },
    
    // 40. Altered Dominant Resolution: im9-V7b9-VImaj9-iim9-vm7 (Am9-E7b9-Fmaj9-Dm9-Em7)
    {
        .length = 5,
        .chord_types = {CHORD_MIN9, CHORD_DOM7B9, CHORD_MAJ9, CHORD_MIN9, CHORD_MIN7},
        .note_offsets = {9, 4, 5, 2, 4}, // Am9, E7b9, Fmaj9, Dm9, Em7 (relative to C major)
        .chord_durations = {4, 4, 4, 2, 2},
        .is_minor = true
    },
    
    // 41. Complex 2-5-1-4: Imaj9-I7-iim7-VII7b9-V7-III7b9-IV-IVdim7 (Cmaj9-C7-Dm7-B7b9-G7-E7b9-Fmaj7-Fdim7)
    {
        .length = 8,
        .chord_types = {CHORD_MAJ9, CHORD_DOM7, CHORD_MIN7, CHORD_DOM7B9, CHORD_DOM7, CHORD_DOM7B9, CHORD_MAJOR, CHORD_DIM7},
        .note_offsets = {0, 0, 2, 11, 7, 4, 5, 5}, // Cmaj9, C7, Dm7, B7b9, G7, E7b9, Fmaj7, Fdim7
        .chord_durations = {4, 2, 4, 2, 4, 2, 4, 2},
        .is_minor = false
    },
    
    // 42. Tritone Substitution: Imaj7-vi7-ii7-bII7-Imaj7 (Cmaj7-Am7-Dm7-Db7)
    {
        .length = 4,
        .chord_types = {CHORD_MAJ7, CHORD_MIN7, CHORD_MIN7, CHORD_DOM7},
        .note_offsets = {0, 9, 2, 1, 0}, // Cmaj7, Am7, Dm7, Db7
        .chord_durations = {4, 4, 4, 4, 4},
        .is_minor = false
    }
};

// Function to get effective BPM (with fallback to 120 if BPM is 0)
uint16_t get_effective_bpm(void) {
   return (current_bpm == 0) ? 12000000 : current_bpm;  // Default to 120.00000 BPM
}

// Function to simulate pressing/releasing a key
void simulate_key(uint16_t keycode, bool pressed) {
    keyrecord_t simulated_record = {
        .event.pressed = pressed,
        .event.key.col = 0,
        .event.key.row = 0,
    };
    
    process_record_user(keycode, &simulated_record);
}

uint8_t progression_channel = 20;
uint8_t progression_velocity = 0;

void release_current_chord(void) {
    // Use the saved channel and velocity for the progression
    uint8_t channel = progression_channel;
    uint8_t velocity = progression_velocity;
	uint8_t travelvelocity = (progression_velocity + progression_velocity);
    
    if (current_chord_type != 0) {
        // Release the note key first
        if (current_note_keycode != 0) {
            simulate_key(current_note_keycode, false);
            current_note_keycode = 0;
        }
        
        // Release the chord type key
        simulate_key(current_chord_type, false);
        current_chord_type = 0;
        
        // Send MIDI note-off for the root note
        if (current_root_midi_note != 0) {
            midi_send_noteoff_with_recording(channel, current_root_midi_note, velocity, travelvelocity, 0);
            current_root_midi_note = 0;
        }
    }
}


static uint8_t frozen_chord_leds[42] = {99}; // Store frozen LED indices
static bool leds_frozen = false;


void freeze_chord_leds(void) {
    frozen_chord_leds[0] = chordkey1_led_index;
    frozen_chord_leds[1] = chordkey1_led_index2;
    frozen_chord_leds[2] = chordkey1_led_index3;
    frozen_chord_leds[3] = chordkey1_led_index4;
    frozen_chord_leds[4] = chordkey1_led_index5;
    frozen_chord_leds[5] = chordkey1_led_index6;
    frozen_chord_leds[6] = chordkey2_led_index;
    frozen_chord_leds[7] = chordkey2_led_index2;
    frozen_chord_leds[8] = chordkey2_led_index3;
    frozen_chord_leds[9] = chordkey2_led_index4;
    frozen_chord_leds[10] = chordkey2_led_index5;
    frozen_chord_leds[11] = chordkey2_led_index6;
    frozen_chord_leds[12] = chordkey3_led_index;
    frozen_chord_leds[13] = chordkey3_led_index2;
    frozen_chord_leds[14] = chordkey3_led_index3;
    frozen_chord_leds[15] = chordkey3_led_index4;
    frozen_chord_leds[16] = chordkey3_led_index5;
    frozen_chord_leds[17] = chordkey3_led_index6;
    frozen_chord_leds[18] = chordkey4_led_index;
    frozen_chord_leds[19] = chordkey4_led_index2;
    frozen_chord_leds[20] = chordkey4_led_index3;
    frozen_chord_leds[21] = chordkey4_led_index4;
    frozen_chord_leds[22] = chordkey4_led_index5;
    frozen_chord_leds[23] = chordkey4_led_index6;
    frozen_chord_leds[24] = chordkey5_led_index;
    frozen_chord_leds[25] = chordkey5_led_index2;
    frozen_chord_leds[26] = chordkey5_led_index3;
    frozen_chord_leds[27] = chordkey5_led_index4;
    frozen_chord_leds[28] = chordkey5_led_index5;
    frozen_chord_leds[29] = chordkey5_led_index6;
    frozen_chord_leds[30] = chordkey6_led_index;
    frozen_chord_leds[31] = chordkey6_led_index2;
    frozen_chord_leds[32] = chordkey6_led_index3;
    frozen_chord_leds[33] = chordkey6_led_index4;
    frozen_chord_leds[34] = chordkey6_led_index5;
    frozen_chord_leds[35] = chordkey6_led_index6;
    frozen_chord_leds[36] = chordkey7_led_index;
    frozen_chord_leds[37] = chordkey7_led_index2;
    frozen_chord_leds[38] = chordkey7_led_index3;
    frozen_chord_leds[39] = chordkey7_led_index4;
    frozen_chord_leds[40] = chordkey7_led_index5;
    frozen_chord_leds[41] = chordkey7_led_index6;
    
    leds_frozen = true;
}


// Function to stop a chord progression and clean up
void stop_chord_progression(void) {
    progression_active = false;
    progression_key_held = false;
    
    // Release any currently pressed chord keys
    release_current_chord();
    
    // Reset all the variables
    smartchordstatus = 0;
    if (smartchordlight != 3) {smartchordlight = 0;}
	if (smartchordstatus == 0) {
    chordkey2 = 0;
    chordkey3 = 0;
    chordkey4 = 0;
    chordkey5 = 0;
    chordkey6 = 0;
    chordkey7 = 0;
    trueheldkey2 = 0;
    heldkey2 = 0;
    heldkey2difference = 0;
    trueheldkey3 = 0;
    heldkey3 = 0;
    heldkey3difference = 0;
    trueheldkey4 = 0;
    heldkey4 = 0;
    heldkey4difference = 0;
    trueheldkey5 = 0;
    heldkey5 = 0;
    heldkey5difference = 0;
    trueheldkey6 = 0;
    heldkey6 = 0;
    heldkey6difference = 0;
    trueheldkey7 = 0;
    heldkey7 = 0;
    heldkey7difference = 0;
    rootnote = 13;
    bassnote = 13;
	leds_frozen = false;
	}
    
    // Set progression_channel to 20 when not in use
    progression_channel = 20;
}



uint8_t progressionvoicing = 1;  // Default to basic voicings

uint8_t previous_highest_note = 0;
uint8_t previous_lowest_note = 127;

// Function to determine and set the appropriate inversion position for a chord
void apply_inversion_for_chord(uint16_t chord_type, uint8_t note_offset, bool is_minor_progression, 
                               uint16_t *note_keycode_ptr, uint8_t *midi_note_ptr) {
    // Declare chord_tones at the beginning so it's available to all code blocks
    uint8_t chord_tones[4] = {0, 0, 0, 0}; // Max 4 chord tones
    
    // Get local copies of the values
    uint16_t note_keycode = *note_keycode_ptr;
    uint8_t midi_note = *midi_note_ptr;
    
	switch (chord_type) {
		case CHORD_MAJOR:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			break;
		case CHORD_MINOR:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 7;  // Perfect 5th
			break;
		case CHORD_DIM:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 6;  // Diminished 5th
			break;
		case CHORD_AUG:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 8;  // Augmented 5th
			break;
		case CHORD_MAJ7:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 11; // Major 7th
			break;
		case CHORD_MIN7:
		case CHORD_DOM7:
			chord_tones[0] = (chord_type == CHORD_MIN7) ? 3 : 4; // 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 10; // Minor 7th
			break;
		case CHORD_MIN7B5:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 6;  // Diminished 5th
			chord_tones[2] = 10; // Minor 7th
			break;
		case CHORD_DIM7:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 6;  // Diminished 5th
			chord_tones[2] = 9;  // Diminished 7th
			break;
		case CHORD_SUS2:
			chord_tones[0] = 2;  // Major 2nd
			chord_tones[1] = 7;  // Perfect 5th
			break;
		case CHORD_SUS4:
			chord_tones[0] = 5;  // Perfect 4th
			chord_tones[1] = 7;  // Perfect 5th
			break;
		case CHORD_MAJ9:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 11; // Major 7th
			chord_tones[3] = 14; // Major 9th (maj7 + maj2)
			break;
		case CHORD_MIN9:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 10; // Minor 7th
			chord_tones[3] = 14; // Major 9th
			break;
		case CHORD_DOM7B9:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 10; // Minor 7th
			chord_tones[3] = 13; // Flat 9th
			break;
		case CHORD_MAJ6:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 9;  // Major 6th
			break;
		case CHORD_ADD4:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 5;  // Perfect 4th
			chord_tones[2] = 7;  // Perfect 5th
			break;
		case CHORD_ADD2:
			chord_tones[0] = 2;  // Major 2nd
			chord_tones[1] = 4;  // Major 3rd
			chord_tones[2] = 7;  // Perfect 5th
			break;
		case CHORD_DOM9:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 10; // Minor 7th
			chord_tones[3] = 14; // Major 9th
			break;
		case CHORD_ADD9:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 14; // Major 9th
			break;
	}
	
	if (randomprogression == 1) {

            // For subsequent chords, randomly change progressionvoicing to 3 or 4
            progressionvoicing = (timer_read32() % 2) ? 3 : 4;
            
            // Continue with the rest of the function to apply the selected voicing
        
    }
    
    // Base case - normal voicing
    if (progressionvoicing == 1) {
        // Send inversion position 0 keycode
        simulate_key(0xC420, true);
        simulate_key(0xC420, false);
        return;
    }
    
    // For octave adjust voicing - as you already implemented
    if (progressionvoicing == 2) {
        // Calculate the total offset for each chord tone
        uint8_t total_offsets[4] = {0, 0, 0, 0};
        for (uint8_t i = 0; i < 4; i++) {
            if (chord_tones[i] != 0) {
                total_offsets[i] = note_offset + chord_tones[i];
            }
        }
        
        // Set the threshold based on whether this is a minor or major progression
        uint8_t threshold = is_minor_progression ? 5 : 12;
        
        // Check which tones are over the threshold
        bool has_3rd_over = (total_offsets[0] > threshold);
        bool has_5th_over = (total_offsets[1] > threshold);
        bool has_7th_over = (total_offsets[2] > threshold);
        
        // Determine appropriate inversion keycode
        uint16_t inversion_keycode = 0xC420; // Default to position 0
        
        if (has_3rd_over && has_5th_over && has_7th_over) {
            inversion_keycode = 0xC421; // Position 1 - lower all
        } else if (has_5th_over && has_7th_over) {
            inversion_keycode = 0xC422; // Position 2 - lower 5th and 7th
        } else if (has_7th_over) {
            inversion_keycode = 0xC423; // Position 3 - lower 7th
        } else if (has_5th_over) {
            inversion_keycode = 0xC422; // Position 2 - lower 5th
        } else if (has_3rd_over) {
            inversion_keycode = 0xC421; // Position 1 - lower 3rd (and others)
        }
        
        // Send the inversion position keycode
        simulate_key(inversion_keycode, true);
        simulate_key(inversion_keycode, false);
        return;
    }
	
if (progressionvoicing == 4 && previous_lowest_note < 127) {
    // Calculate the MIDI note that would be played
    uint8_t base_note = midi_note;
    
    // Determine the expected highest note based on chord type
    uint8_t highest_interval = 6;  // Default for triads (root + perfect fifth)
    
	if (chord_type == CHORD_MAJ7 || chord_type == CHORD_MIN7 || 
		chord_type == CHORD_DOM7 || chord_type == CHORD_MIN7B5 || 
		chord_type == CHORD_DIM7 || chord_type == CHORD_MAJ9 || 
		chord_type == CHORD_MIN9 || chord_type == CHORD_DOM7B9 || 
		chord_type == CHORD_MAJ6 || chord_type == CHORD_ADD4 || 
		chord_type == CHORD_ADD2 || chord_type == CHORD_DOM9 || 
		chord_type == CHORD_ADD9) {
		highest_interval = 9;  // For 7th chords (root + major 7th)
	}

	// For 9th chords, use even higher interval
	if (chord_type == CHORD_MAJ9 || chord_type == CHORD_MIN9 || 
		chord_type == CHORD_DOM7B9 || chord_type == CHORD_DOM9 || 
		chord_type == CHORD_ADD9) {
		highest_interval = 12;  // For 9th chords (root + 9th)
	}
    
    // Check if the chord's highest note would be lower than previous lowest
    if (base_note + highest_interval < previous_lowest_note) {
        // Raise by an octave
        note_keycode += 12;
        midi_note += 12;
        base_note += 12;
        
        // Update the values immediately
        *note_keycode_ptr = note_keycode;
        *midi_note_ptr = midi_note;
    }
}
    
if (progressionvoicing == 4) {
    // Only proceed if we have a valid previous highest note
    if (previous_highest_note > 0) {
        // Calculate base note for this chord
        uint8_t base_note = 48 + note_offset + progression_key_offset + progression_octave_offset;
		
		//if (base_note < previous_lowest_note - 7) {  // Using 6 semitones as threshold
            // Raise the entire chord by an octave
        //    note_keycode += 12;
        //    midi_note += 12;
        //    base_note += 12;
       // }
        
        // First, determine the highest note in this chord (before any inversions)
        uint8_t chord_highest = base_note;
        for (uint8_t i = 0; i < 3; i++) {
            if (chord_tones[i] != 0 && base_note + chord_tones[i] > chord_highest) {
                chord_highest = base_note + chord_tones[i];
            }
        }
		
        
        // Count how many notes are higher than OR EQUAL TO previous highest
        int notes_above_previous = 0;
        if (base_note > previous_highest_note) notes_above_previous++;
        for (uint8_t i = 0; i < 3; i++) {
            if (chord_tones[i] != 0 && base_note + chord_tones[i] > previous_highest_note) {
                notes_above_previous++;
            }
        }
        
        // If we need to raise the chord (all notes below previous highest)
        if (notes_above_previous == 0 || (chord_highest < previous_highest_note && 
                                         previous_highest_note - chord_highest > 7)) {
            // Raise the entire chord by an octave
            note_keycode += 12;
            midi_note += 12;
            base_note += 12;
            
            // Recalculate highest note after raising
            chord_highest = base_note;
            for (uint8_t i = 0; i < 3; i++) {
                if (chord_tones[i] != 0 && base_note + chord_tones[i] > chord_highest) {
                    chord_highest = base_note + chord_tones[i];
                }
            }
            
            // Recount notes above previous
            notes_above_previous = 0;
            if (base_note > previous_highest_note) notes_above_previous++;
            for (uint8_t i = 0; i < 3; i++) {
                if (chord_tones[i] != 0 && base_note + chord_tones[i] > previous_highest_note) {
                    notes_above_previous++;
                }
            }
        }
        
        // If too many notes are above OR EQUAL TO, apply inversions to get down to just one
        if (notes_above_previous > 1) {
            // Determine which specific notes are above OR EQUAL TO previous highest
            bool root_above = (base_note > previous_highest_note);
            bool third_above = (chord_tones[0] != 0 && base_note + chord_tones[0] > previous_highest_note);
            bool fifth_above = (chord_tones[1] != 0 && base_note + chord_tones[1] > previous_highest_note);
            bool seventh_above = (chord_tones[2] != 0 && base_note + chord_tones[2] > previous_highest_note);
            bool ninth_above = (chord_tones[3] != 0 && base_note + chord_tones[3] > previous_highest_note);
            
            // Choose appropriate inversion to minimize notes above previous highest
            uint16_t inversion_keycode = 0xC420; // Default to no inversion
            
            // If all are above OR EQUAL TO, we need to choose which to keep high
            if (root_above) {
                // Lower 3rd
                inversion_keycode = 0xC421; // 1st inversion - lower all
                // Update chord_highest after inversion
                for (uint8_t i = 0; i < 3; i++) {
                    uint8_t this_note = base_note + chord_tones[i];
                    // Adjust for 1st inversion (lower all)
                    this_note -= 12;
                    if (this_note > chord_highest) chord_highest = this_note;
                }
            
            } else if (third_above) {
                // Lower 3rd
                inversion_keycode = 0xC422; // 1st inversion - lower all
                // Update chord_highest after inversion
                for (uint8_t i = 0; i < 3; i++) {
                    uint8_t this_note = base_note + chord_tones[i];
                    // Adjust for 1st inversion (lower all)
                    this_note -= 12;
                    if (this_note > chord_highest) chord_highest = this_note;
                }
            } else if (fifth_above) {
                // Lower 5th
                inversion_keycode = 0xC423; // 2nd inversion - lower 5th
                // Update chord_highest after inversion
                for (uint8_t i = 0; i < 3; i++) {
                    uint8_t this_note = base_note + chord_tones[i];
                    // Adjust for 2nd inversion (lower 5th)
                    if (i == 1) this_note -= 12; // 5th is lowered
                    if (this_note > chord_highest) chord_highest = this_note;
                }
            } else if (seventh_above) {
                // Lower the 7th if it's above (will also lower root for first inversion)
                inversion_keycode = 0xC424; // 3rd inversion - lower 7th
                // Update chord_highest after inversion
                for (uint8_t i = 0; i < 3; i++) {
                    uint8_t this_note = base_note + chord_tones[i];
                    // Adjust for 3rd inversion (lower 7th)
                    if (i == 2) this_note -= 12; // 7th is lowered
                    if (this_note > chord_highest) chord_highest = this_note;
                }
            } else if (ninth_above) {
                // Lower the 9th if it's above
                inversion_keycode = 0xC425; // 4th inversion - lower 9th
                // Update chord_highest after inversion
                for (uint8_t i = 0; i < 3; i++) {
                    uint8_t this_note = base_note + chord_tones[i];
                    // Adjust for 4th inversion (lower 9th)
                    if (i == 3) this_note -= 12; // 9th is lowered
                    if (this_note > chord_highest) chord_highest = this_note;
                }
            }
            
            // Send the inversion position keycode
            simulate_key(inversion_keycode, true);
            simulate_key(inversion_keycode, false);
            
            // Update the pointer values
            *note_keycode_ptr = note_keycode;
            *midi_note_ptr = midi_note;
        } else {
            // Default - no inversion needed
            simulate_key(0xC420, true);
            simulate_key(0xC420, false);
        }
        
        return;
    }
    
    // Default - first chord or no previous highest
    simulate_key(0xC420, true);
    simulate_key(0xC420, false);
}
    
    if (progressionvoicing == 3) {
        // Only apply if we have a previous highest note
        if (previous_highest_note > 0) {
            // Calculate the base note and find the highest note in the chord
            uint8_t base_note = 48 + note_offset + progression_key_offset + progression_octave_offset;
            uint8_t highest_note = base_note;
            
            for (uint8_t i = 0; i < 3; i++) {
                if (chord_tones[i] != 0 && base_note + chord_tones[i] > highest_note) {
                    highest_note = base_note + chord_tones[i];
                }
            }
            
            // If highest note is higher than previous highest
            if (highest_note > previous_highest_note) {
				// Find out which notes are too high
				bool third_too_high = (chord_tones[0] != 0 && 
									  (base_note + chord_tones[0] > previous_highest_note));
				bool fifth_too_high = (chord_tones[1] != 0 && 
									  (base_note + chord_tones[1] > previous_highest_note));
				bool seventh_too_high = (chord_tones[2] != 0 && 
										(base_note + chord_tones[2] > previous_highest_note));
				bool ninth_too_high = (chord_tones[3] != 0 && 
									  (base_note + chord_tones[3] > previous_highest_note));
				
				// Choose the appropriate inversion
				uint16_t inversion_keycode = 0xC420; // Default
				
				// Choose inversion based on which notes need to be lowered
				if (base_note > previous_highest_note) {
					// Root note is too high, we need to lower the entire chord
					note_keycode -= 12;
					midi_note -= 12;
					inversion_keycode = 0xC420; // No additional inversion needed
				} else if (third_too_high && fifth_too_high && seventh_too_high && ninth_too_high) {
					inversion_keycode = 0xC421; // Lower all notes
				} else if (fifth_too_high && seventh_too_high && ninth_too_high) {
					inversion_keycode = 0xC422; // Lower 5th, 7th and 9th
				} else if (seventh_too_high && ninth_too_high) {
					inversion_keycode = 0xC423; // Lower 7th and 9th
				} else if (ninth_too_high) {
					inversion_keycode = 0xC424; // Lower just 9th
				} else if (third_too_high && fifth_too_high) {
					inversion_keycode = 0xC421; // Lower all notes
				} else if (fifth_too_high && seventh_too_high) {
					inversion_keycode = 0xC422; // Lower 5th and 7th
				} else if (fifth_too_high) {
					inversion_keycode = 0xC422; // Lower just 5th
				} else if (seventh_too_high) {
					inversion_keycode = 0xC423; // Lower just 7th
				} else if (third_too_high) {
					inversion_keycode = 0xC421; // Lower all notes for 3rd
				}
                
                // Send the inversion position keycode
                simulate_key(inversion_keycode, true);
                simulate_key(inversion_keycode, false);
                
                // Update the pointers with the new values
                *note_keycode_ptr = note_keycode;
                *midi_note_ptr = midi_note;
                
                return;
            }
        }
    }
	
	if (randomprogression == 1) {
    static bool first_chord_played = false;
    static bool use_ascending = true;  // Start with ascending voicing
    
    // For the first chord, apply a random inversion
    if (!first_chord_played || previous_highest_note == 0) {
        // Generate a random inversion between 0 and 4
        // Using simple timer-based randomization since rand() might not be available
        uint8_t random_inversion = (timer_read32() % 5);
        uint16_t inversion_keycode = 0xC420 + random_inversion;
        
        // Send the random inversion keycode
        simulate_key(inversion_keycode, true);
        simulate_key(inversion_keycode, false);
        
        // Mark that we've played the first chord
        first_chord_played = true;
        
        // Alternate the voicing direction for next chord
        use_ascending = !use_ascending;
        
        return;
    }
    
    // For subsequent chords, use either ascending or descending voice leading
    if (use_ascending) {
        // Use ascending voice leading (mode 4 logic)
        // Only proceed if we have a valid previous highest note
        if (previous_highest_note > 0) {
            // Calculate base note for this chord
            uint8_t base_note = 48 + note_offset + progression_key_offset + progression_octave_offset;
            
            // First, determine the highest note in this chord (before any inversions)
            uint8_t chord_highest = base_note;
            for (uint8_t i = 0; i < 3; i++) {
                if (chord_tones[i] != 0 && base_note + chord_tones[i] > chord_highest) {
                    chord_highest = base_note + chord_tones[i];
                }
            }
            
            // Count how many notes are higher than OR EQUAL TO previous highest
            int notes_above_previous = 0;
            if (base_note >= previous_highest_note) notes_above_previous++;
            for (uint8_t i = 0; i < 3; i++) {
                if (chord_tones[i] != 0 && base_note + chord_tones[i] >= previous_highest_note) {
                    notes_above_previous++;
                }
            }
            
            // If we need to raise the chord (all notes below previous highest)
            if (notes_above_previous == 0 || (chord_highest < previous_highest_note && 
                                             previous_highest_note - chord_highest > 7)) {
                // Raise the entire chord by an octave
                note_keycode += 12;
                midi_note += 12;
                base_note += 12;
                
                // Recalculate highest note after raising
                chord_highest = base_note;
                for (uint8_t i = 0; i < 3; i++) {
                    if (chord_tones[i] != 0 && base_note + chord_tones[i] > chord_highest) {
                        chord_highest = base_note + chord_tones[i];
                    }
                }
                
                // Recount notes above previous
                notes_above_previous = 0;
                if (base_note >= previous_highest_note) notes_above_previous++;
                for (uint8_t i = 0; i < 3; i++) {
                    if (chord_tones[i] != 0 && base_note + chord_tones[i] >= previous_highest_note) {
                        notes_above_previous++;
                    }
                }
            }
            
            // If too many notes are above OR EQUAL TO, apply inversions to get down to just one
            if (notes_above_previous > 1) {
                // Determine which specific notes are above OR EQUAL TO previous highest
                bool root_above = (base_note >= previous_highest_note);
                bool third_above = (chord_tones[0] != 0 && base_note + chord_tones[0] >= previous_highest_note);
                bool fifth_above = (chord_tones[1] != 0 && base_note + chord_tones[1] >= previous_highest_note);
                bool seventh_above = (chord_tones[2] != 0 && base_note + chord_tones[2] >= previous_highest_note);
                bool ninth_above = (chord_tones[3] != 0 && base_note + chord_tones[3] >= previous_highest_note);
                
                // Choose appropriate inversion to minimize notes above previous highest
                uint16_t inversion_keycode = 0xC420; // Default to no inversion
                
                // If all are above OR EQUAL TO, we need to choose which to keep high
                if (root_above) {
                    inversion_keycode = 0xC421; // 1st inversion - lower all
                } else if (third_above) {
                    inversion_keycode = 0xC422; // 1st inversion - lower all
                } else if (fifth_above) {
                    inversion_keycode = 0xC423; // 2nd inversion - lower 5th
                } else if (seventh_above) {
                    inversion_keycode = 0xC424; // 3rd inversion - lower 7th
                } else if (ninth_above) {
                    inversion_keycode = 0xC425; // 4th inversion - lower 9th
                }
                
                // Send the inversion position keycode
                simulate_key(inversion_keycode, true);
                simulate_key(inversion_keycode, false);
                
                // Update the pointer values
                *note_keycode_ptr = note_keycode;
                *midi_note_ptr = midi_note;
            } else {
                // Default - no inversion needed
                simulate_key(0xC420, true);
                simulate_key(0xC420, false);
            }
        } else {
            // Default - no previous highest
            simulate_key(0xC420, true);
            simulate_key(0xC420, false);
        }
    } else {
        // Use descending voice leading (mode 3 logic)
        // Only apply if we have a previous lowest note
        if (previous_lowest_note < 127) {
            // Calculate the base note and find the lowest note in the chord
            uint8_t base_note = 48 + note_offset + progression_key_offset + progression_octave_offset;
            uint8_t highest_note = base_note;
            
            for (uint8_t i = 0; i < 3; i++) {
                if (chord_tones[i] != 0 && base_note + chord_tones[i] > highest_note) {
                    highest_note = base_note + chord_tones[i];
                }
            }
            
            // If highest note is higher than OR EQUAL TO previous highest
            if (highest_note >= previous_highest_note) {
                // Find out which notes are too high
                bool third_too_high = (chord_tones[0] != 0 && 
                                      (base_note + chord_tones[0] >= previous_highest_note));
                bool fifth_too_high = (chord_tones[1] != 0 && 
                                      (base_note + chord_tones[1] >= previous_highest_note));
                bool seventh_too_high = (chord_tones[2] != 0 && 
                                        (base_note + chord_tones[2] >= previous_highest_note));
                bool ninth_too_high = (chord_tones[3] != 0 && 
                                      (base_note + chord_tones[3] >= previous_highest_note));
                
                // Choose the appropriate inversion
                uint16_t inversion_keycode = 0xC420; // Default
                
                // Choose inversion based on which notes need to be lowered
                if (base_note >= previous_highest_note) {
                    // Root note is too high, we need to lower the entire chord
                    note_keycode -= 12;
                    midi_note -= 12;
                    inversion_keycode = 0xC420; // No additional inversion needed
                } else if (third_too_high && fifth_too_high && seventh_too_high && ninth_too_high) {
                    inversion_keycode = 0xC421; // Lower all notes
                } else if (fifth_too_high && seventh_too_high && ninth_too_high) {
                    inversion_keycode = 0xC422; // Lower 5th, 7th and 9th
                } else if (seventh_too_high && ninth_too_high) {
                    inversion_keycode = 0xC423; // Lower 7th and 9th
                } else if (ninth_too_high) {
                    inversion_keycode = 0xC424; // Lower just 9th
                } else if (third_too_high && fifth_too_high) {
                    inversion_keycode = 0xC421; // Lower all notes
                } else if (fifth_too_high && seventh_too_high) {
                    inversion_keycode = 0xC422; // Lower 5th and 7th
                } else if (fifth_too_high) {
                    inversion_keycode = 0xC422; // Lower just 5th
                } else if (seventh_too_high) {
                    inversion_keycode = 0xC423; // Lower just 7th
                } else if (third_too_high) {
                    inversion_keycode = 0xC421; // Lower all notes for 3rd
                }
                
                // Send the inversion position keycode
                simulate_key(inversion_keycode, true);
                simulate_key(inversion_keycode, false);
                
                // Update the pointers with the new values
                *note_keycode_ptr = note_keycode;
                *midi_note_ptr = midi_note;
            } else {
                // Default - no inversion needed
                simulate_key(0xC420, true);
                simulate_key(0xC420, false);
            }
        } else {
            // Default - no previous lowest
            simulate_key(0xC420, true);
            simulate_key(0xC420, false);
        }
    }
    
    // Toggle between ascending and descending for next chord
    use_ascending = !use_ascending;
    
    return;
}
  
    // Default - no inversion needed
    simulate_key(0xC420, true); // No inversion
    simulate_key(0xC420, false);
}


// Update play_chord to track the highest and lowest notes
void play_chord(uint16_t chord_type, uint8_t note_offset, bool is_minor_progression) {
    uint8_t channel = progression_channel;
    uint8_t velocity = progression_velocity;
	uint8_t travelvelocity = (progression_velocity + progression_velocity);
    leds_frozen = false;
    // Set progression_active to false to allow chord functions to work correctly
    progression_active = false;
    
    // Release any currently pressed chord
    release_current_chord();
    
    // Calculate offsets for the chord progression
    int16_t chord_offset = note_offset + progression_key_offset  + progression_octave_offset;
    
    // Calculate the note keycode - compensate for transpose and octave
    uint16_t note_keycode = BASE_NOTE_KEYCODE + 24 + chord_offset - transpose_number - octave_number;
    
    // Calculate the MIDI note
    uint8_t midi_note = 48 + chord_offset;
    
    // Apply the appropriate inversion position by sending keycode
    // Pass pointers to note_keycode and midi_note so they can be updated
    apply_inversion_for_chord(chord_type, note_offset, is_minor_progression, &note_keycode, &midi_note);
    
    // Press the chord type key 
    simulate_key(chord_type, true);
    current_chord_type = chord_type;
    
    // Press the note key
    simulate_key(note_keycode, true);
    current_note_keycode = note_keycode;
    
    // Store the current root MIDI note for later release
    current_root_midi_note = midi_note;
    
    // Manually send MIDI note-on for the root note
    midi_send_noteon_with_recording(channel, midi_note, velocity, travelvelocity);
    
    // Track the highest and lowest notes of this chord for voice leading
    if (progressionvoicing == 3 || progressionvoicing == 4) {
        // Get the chord structure
        uint8_t chord_tones[4] = {0, 0, 0, 0};
        
	switch (chord_type) {
		case CHORD_MAJOR:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			break;
		case CHORD_MINOR:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 7;  // Perfect 5th
			break;
		case CHORD_DIM:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 6;  // Diminished 5th
			break;
		case CHORD_AUG:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 8;  // Augmented 5th
			break;
		case CHORD_MAJ7:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 11; // Major 7th
			break;
		case CHORD_MIN7:
		case CHORD_DOM7:
			chord_tones[0] = (chord_type == CHORD_MIN7) ? 3 : 4; // 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 10; // Minor 7th
			break;
		case CHORD_MIN7B5:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 6;  // Diminished 5th
			chord_tones[2] = 10; // Minor 7th
			break;
		case CHORD_DIM7:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 6;  // Diminished 5th
			chord_tones[2] = 9;  // Diminished 7th
			break;
		case CHORD_SUS2:
			chord_tones[0] = 2;  // Major 2nd
			chord_tones[1] = 7;  // Perfect 5th
			break;
		case CHORD_SUS4:
			chord_tones[0] = 5;  // Perfect 4th
			chord_tones[1] = 7;  // Perfect 5th
			break;
		case CHORD_MAJ9:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 11; // Major 7th
			chord_tones[3] = 14; // Major 9th (maj7 + maj2)
			break;
		case CHORD_MIN9:
			chord_tones[0] = 3;  // Minor 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 10; // Minor 7th
			chord_tones[3] = 14; // Major 9th
			break;
		case CHORD_DOM7B9:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 10; // Minor 7th
			chord_tones[3] = 13; // Flat 9th
			break;
		case CHORD_MAJ6:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 9;  // Major 6th
			break;
		case CHORD_ADD4:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 5;  // Perfect 4th
			chord_tones[2] = 7;  // Perfect 5th
			break;
		case CHORD_ADD2:
			chord_tones[0] = 2;  // Major 2nd
			chord_tones[1] = 4;  // Major 3rd
			chord_tones[2] = 7;  // Perfect 5th
			break;
		case CHORD_DOM9:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 10; // Minor 7th
			chord_tones[3] = 14; // Major 9th
			break;
		case CHORD_ADD9:
			chord_tones[0] = 4;  // Major 3rd
			chord_tones[1] = 7;  // Perfect 5th
			chord_tones[2] = 14; // Major 9th
			break;
	}

        
        // Find the highest and lowest notes, accounting for inversions and positive inversions
        uint8_t highest_note = midi_note;
        uint8_t lowest_note = midi_note;
        
        for (uint8_t i = 0; i < 4; i++) {
            if (chord_tones[i] != 0) {
                uint8_t this_note = midi_note + chord_tones[i];
                
                // Adjust for inversions (lowering notes)
                if (inversionposition == 1) { // All notes lowered
                    this_note -= 12;
                } else if (inversionposition == 2 && i >= 1) { // 5th and 7th lowered
                    this_note -= 12;
                } else if (inversionposition == 3 && i >= 2) { // 7th lowered
                    this_note -= 12;
                }
                
                // Adjust for positive inversion (raising notes)
                if (positiveinversion == 1) {
                    this_note += 12;
                }
                
                if (this_note > highest_note) {
                    highest_note = this_note;
                }
                if (this_note < lowest_note) {
                    lowest_note = this_note;
                }
            }
        }
        
        // Store for next chord
        previous_highest_note = highest_note;
        previous_lowest_note = lowest_note;
    }
    
    // Chord is established, set progression_active to true to allow riffing
    progression_active = true;
	freeze_chord_leds();
}

// Call this from your matrix scan function to handle chord progression timing
void update_chord_progression(void) {
    if (!progression_active || !progression_key_held) return;
    
    uint32_t current_time = timer_read32();
    
    if (current_time >= next_chord_time) {
        bool was_last_chord = (current_chord_index == chord_progressions[current_progression].length - 1);
        
        // Move to next chord
        current_chord_index++;
        
        // Check if we've reached the end of the progression
        if (current_chord_index >= chord_progressions[current_progression].length) {
            // Only reset tracking variables when not using randomprogression
            if (randomprogression == 0) {
                previous_highest_note = 0;
                previous_lowest_note = 127;
            }
            
            // Loop back to beginning
            current_chord_index = 0;
        }
        
        // If random progression is enabled, randomly set progressionvoicing to either 3 or 4
        // But only do this if it's not the first chord (after a reset) or we're continuing cycles
        if (randomprogression && (current_chord_index > 0 || was_last_chord)) {
            // Use timer value to generate pseudo-random number
            progressionvoicing = ((timer_read32() % 2) == 0) ? 3 : 4;
        }
        
        // Get the chord information
        uint16_t chord_type = chord_progressions[current_progression].chord_types[current_chord_index];
        uint8_t note_offset = chord_progressions[current_progression].note_offsets[current_chord_index];
        bool is_minor = chord_progressions[current_progression].is_minor;
        
        // Play the chord
        play_chord(chord_type, note_offset, is_minor);
        
				// Calculate time for next chord based on effective BPM
		uint32_t actual_bpm = current_bpm / 100000;
		if (actual_bpm == 0) actual_bpm = 120;  // Fallback if no BPM set
		uint32_t ms_per_beat = 60000 / actual_bpm;
		uint32_t chord_duration = ms_per_beat * chord_progressions[current_progression].chord_durations[current_chord_index];
        
        // Set time for next chord
        next_chord_time = current_time + chord_duration;
    }
}
void start_chord_progression(uint8_t progression_id, uint8_t key_offset) {
    if (progression_id < sizeof(chord_progressions)/sizeof(chord_progressions[0])) {
        // Store current voice leading history if we're already in a random progression
        uint8_t old_highest = previous_highest_note;
        uint8_t old_lowest = previous_lowest_note;
        bool was_random = randomprogression && progression_active;
        
        // Stop any current progression
        if (progression_active) {
            stop_chord_progression();
        }
        
        // Take a snapshot of the current channel and velocity
        progression_channel = channel_number;
        progression_velocity = he_velocity_min + ((he_velocity_max - he_velocity_min)/2);
        
        // Set up new progression
        current_progression = progression_id;
        current_chord_index = 0;
        progression_active = true;
        progression_key_held = true;
        progression_key_offset = key_offset;
        
        // Only reset voice leading history if not using randomprogression
        // or if this is the first progression being started
        if (!randomprogression || !was_random) {
            previous_highest_note = 0;
            previous_lowest_note = 127;
        } else {
            // Restore the previous voice leading history
            previous_highest_note = old_highest;
            previous_lowest_note = old_lowest;
        }
        
        // Play the first chord immediately
        uint16_t chord_type = chord_progressions[current_progression].chord_types[0];
        uint8_t note_offset = chord_progressions[current_progression].note_offsets[0];
        bool is_minor = chord_progressions[current_progression].is_minor;
        
        // Play the first chord
        play_chord(chord_type, note_offset, is_minor);

		uint32_t start_actual_bpm = current_bpm / 100000;
		if (start_actual_bpm == 0) start_actual_bpm = 120;
		next_chord_time = timer_read32() + 
			(60000 / start_actual_bpm) * chord_progressions[current_progression].chord_durations[0];
    }
}

// Function to extract progression ID and key offset from keycode
void start_progression_from_keycode(uint16_t keycode) {
    uint16_t base_keycode = 0xCA10;
    uint8_t keys_per_progression = 12;
    
    // Calculate which progression and which key
    uint8_t progression_id = (keycode - base_keycode) / keys_per_progression;
    uint8_t key_offset = (keycode - base_keycode) % keys_per_progression;
    
    // Start the progression with the right key offset
    start_chord_progression(progression_id, key_offset);
}
// Discovery phase variables
uint8_t discovered_layers_with_midi = 0;
uint8_t discovered_max_notes_per_layer = 0;
uint8_t layers_with_midi_list[12];  // Which layers have MIDI keys

// Dynamic sizing variables (set after discovery)
uint8_t ACTUAL_MIDI_LAYERS = 0;
uint8_t ACTUAL_MAX_NOTES_PER_LAYER = 0;

// Hybrid approach: Dynamic 3D array + fast lookup
uint8_t layer_to_index_map[12];  // Maps layer number to array index
uint8_t (*optimized_midi_positions)[72][6] = NULL;  // Dynamic 3D array for LED positions
uint8_t (*optimized_midi_velocities)[72] = NULL;     // Dynamic 2D array for velocities

// Aftertouch pedal state (runtime, not saved)
bool aftertouch_pedal_active = false;

// Layer actuations with per-layer aftertouch settings
// {normal_actuation, midi_actuation, velocity_mode, velocity_speed_scale, flags,
//  aftertouch_mode, aftertouch_cc, vibrato_sensitivity, vibrato_decay_time}
// FIX: Set actuation to 99 (nearly full press) to prevent empty sockets from triggering
layer_actuation_t layer_actuations[12] = {
    {99, 99, 2, 10, 0, 0, 255, 100, 200}, {99, 99, 2, 10, 0, 0, 255, 100, 200},
    {99, 99, 2, 10, 0, 0, 255, 100, 200}, {99, 99, 2, 10, 0, 0, 255, 100, 200},
    {99, 99, 2, 10, 0, 0, 255, 100, 200}, {99, 99, 2, 10, 0, 0, 255, 100, 200},
    {99, 99, 2, 10, 0, 0, 255, 100, 200}, {99, 99, 2, 10, 0, 0, 255, 100, 200},
    {99, 99, 2, 10, 0, 0, 255, 100, 200}, {99, 99, 2, 10, 0, 0, 255, 100, 200},
    {99, 99, 2, 10, 0, 0, 255, 100, 200}, {99, 99, 2, 10, 0, 0, 255, 100, 200}
};

// =============================================================================
// PER-KEY ACTUATION GLOBAL VARIABLES
// =============================================================================

layer_key_actuations_t per_key_actuations[12];  // 840 bytes total (70 keys × 12 layers)
// NOTE: per_key_mode_enabled and per_key_per_layer_enabled have been REMOVED
// Firmware now ALWAYS uses per-key per-layer settings. The GUI handles "apply to all"
// by writing the same values to all keys/layers when the user wants uniform settings.

// =============================================================================
// NULL BIND (SOCD) GLOBAL VARIABLES
// =============================================================================
nullbind_group_t nullbind_groups[NULLBIND_NUM_GROUPS];
nullbind_runtime_t nullbind_runtime[NULLBIND_NUM_GROUPS];
bool nullbind_enabled = true;  // Global enable flag

// Key travel values for distance-based null bind (updated during matrix scan)
// Non-static so matrix.c can update it directly for continuous distance tracking
uint8_t nullbind_key_travel[70];  // Current travel value for each key (0-255)

// =============================================================================
// TOGGLE KEYS GLOBAL VARIABLES
// =============================================================================
toggle_slot_t toggle_slots[TOGGLE_NUM_SLOTS];
toggle_runtime_t toggle_runtime[TOGGLE_NUM_SLOTS];
bool toggle_enabled = true;  // Global enable flag

// Initialize default values
void initialize_layer_actuations(void) {
    for (uint8_t i = 0; i < 12; i++) {
        // TROUBLESHOOTING: Using 30% actuation for easy triggering
        // At 30%: actuation_point = 76, key registers when ADC drops to ~1732
        // This should trigger with even a light press
        layer_actuations[i].normal_actuation = 30;
        layer_actuations[i].midi_actuation = 30;
        layer_actuations[i].velocity_mode = 2;      // Speed-Based (matches GUI default)
        layer_actuations[i].velocity_speed_scale = 10;
        layer_actuations[i].flags = 0;              // All flags off
        layer_actuations[i].aftertouch_mode = 0;    // Off
        layer_actuations[i].aftertouch_cc = 255;    // Off (no CC)
        layer_actuations[i].vibrato_sensitivity = 100;  // 100% (normal)
        layer_actuations[i].vibrato_decay_time = 200;   // 200ms
        // Note: Rapidfire settings are now per-key in per_key_actuations
        // Note: Velocity curve/min/max settings and aftertouch are now global in keyboard_settings
    }
}

// Phase 1: Discovery scan
void discover_midi_usage(void) {
    discovered_layers_with_midi = 0;
    discovered_max_notes_per_layer = 0;
    
    for (int layer = 0; layer < 12; layer++) {
        uint8_t notes_in_this_layer = 0;
        bool layer_has_midi = false;
        
        // Count unique MIDI notes in this layer
        bool note_found[72] = {false};  // Track which notes we've seen
        
        for (int row = 0; row < MATRIX_ROWS; row++) {
            for (int col = 0; col < MATRIX_COLS; col++) {
                uint16_t keycode = dynamic_keymap_get_keycode(layer, row, col);
                uint8_t note_index = 255;
                
                if (keycode >= 28931 && keycode <= 29002) {
                    note_index = keycode - 28931;
                } else if (keycode >= 50688 && keycode <= 50759) {
                    note_index = keycode - 50688;
                } else if (keycode >= 50800 && keycode <= 50871) {
                    note_index = keycode - 50800;
                }
                
                if (note_index != 255 && !note_found[note_index]) {
                    note_found[note_index] = true;
                    notes_in_this_layer++;
                    layer_has_midi = true;
                }
            }
        }
        
        if (layer_has_midi) {
            layers_with_midi_list[discovered_layers_with_midi] = layer;
            discovered_layers_with_midi++;
            
            if (notes_in_this_layer > discovered_max_notes_per_layer) {
                discovered_max_notes_per_layer = notes_in_this_layer;
            }
        }
    }
    
    // Set the actual sizes we'll use
    ACTUAL_MIDI_LAYERS = discovered_layers_with_midi;
    ACTUAL_MAX_NOTES_PER_LAYER = discovered_max_notes_per_layer;
}

// Phase 2: Allocate optimal-sized arrays
void allocate_midi_storage(void) {
    // Free existing storage if any
    if (optimized_midi_positions != NULL) {
        free(optimized_midi_positions);
        optimized_midi_positions = NULL;
    }
    if (optimized_midi_velocities != NULL) {
        free(optimized_midi_velocities);
        optimized_midi_velocities = NULL;
    }
    
    // Only allocate if we have MIDI layers
    if (ACTUAL_MIDI_LAYERS == 0) {
        return;
    }
    
    // Allocate optimal-sized 3D array for LED positions
    size_t positions_size = ACTUAL_MIDI_LAYERS * 72 * 6 * sizeof(uint8_t);
    optimized_midi_positions = malloc(positions_size);
    
    // Allocate optimal-sized 2D array for velocities
    size_t velocities_size = ACTUAL_MIDI_LAYERS * 72 * sizeof(uint8_t);
    optimized_midi_velocities = malloc(velocities_size);
    
    // Initialize all positions to 99
    for (int i = 0; i < ACTUAL_MIDI_LAYERS; i++) {
        for (int j = 0; j < 72; j++) {
            for (int k = 0; k < 6; k++) {
                optimized_midi_positions[i][j][k] = 99;
            }
            // Initialize velocities to 64 (default)
            optimized_midi_velocities[i][j] = 64;
        }
    }
    
    // Create layer mapping
    for (int i = 0; i < 12; i++) {
        layer_to_index_map[i] = 255;  // Invalid index
    }
    for (int i = 0; i < ACTUAL_MIDI_LAYERS; i++) {
        layer_to_index_map[layers_with_midi_list[i]] = i;
    }
}

// Phase 3: Populate the optimally-sized arrays
void populate_midi_data(void) {
    if (optimized_midi_positions == NULL || optimized_midi_velocities == NULL) return;
    
    if (smartchordlightmode == 0 || smartchordlightmode == 2 || smartchordlightmode == 1) {
        // CLEAR THE ARRAYS FIRST
        for (int i = 0; i < ACTUAL_MIDI_LAYERS; i++) {
            for (int j = 0; j < 72; j++) {
                for (int k = 0; k < 6; k++) {
                    optimized_midi_positions[i][j][k] = 99;
                }
                optimized_midi_velocities[i][j] = 64;
            }
        }
        
        // Now populate from actual keymap data
        for (uint8_t current_layer = 0; current_layer < ACTUAL_MIDI_LAYERS; current_layer++) {
            uint8_t layer = layers_with_midi_list[current_layer];
            uint8_t note_count[72] = {0};  // Track positions per note
            
            for (int row = 0; row < MATRIX_ROWS; row++) {
                for (int col = 0; col < MATRIX_COLS; col++) {
                    uint16_t keycode = dynamic_keymap_get_keycode(layer, row, col);
                    uint8_t led_index = g_led_config.matrix_co[row][col];
                    uint8_t note_index = 255;
                    
                    if (keycode >= 28931 && keycode <= 29002) {
                        note_index = keycode - 28931;
                    } else if (keycode >= 50688 && keycode <= 50759) {
                        note_index = keycode - 50688;
                    } else if (keycode >= 50800 && keycode <= 50871) {
                        note_index = keycode - 50800;
                    }
                    
                    if (note_index != 255 && note_count[note_index] < 6) {
                        optimized_midi_positions[current_layer][note_index][note_count[note_index]] = led_index;
                        note_count[note_index]++;
                    }
                }
            }
        }
    } else if (smartchordlightmode == 3 || smartchordlightmode == 4) {
        // For predefined modes, populate all layers with all 72 notes
        static const uint8_t mode3_positions[72][6] = {
            {64, 45, 38, 19, 1, 13},   // Note 0  (C)
            {65, 46, 39, 20, 2, 99},   // Note 1  (C#)
            {66, 47, 28, 40, 21, 3},   // Note 2  (D)
            {67, 48, 29, 41, 22, 4},   // Note 3  (Eb)
            {56, 68, 49, 30, 23, 5},   // Note 4  (E)
            {57, 69, 50, 31, 24, 6},   // Note 5  (F)
            {58, 51, 32, 25, 7, 99},   // Note 6  (F#)
            {59, 52, 33, 14, 26, 8},   // Note 7  (G)
            {60, 53, 34, 15, 27, 9},   // Note 8  (Ab)
            {61, 42, 54, 35, 16, 10},  // Note 9  (A)
            {62, 43, 55, 36, 17, 11},  // Note 10 (Bb)
            {63, 44, 37, 18, 0, 12},   // Note 11 (B)
            // Repeat pattern for other octaves (12-71)
            {64, 45, 38, 19, 1, 13}, {65, 46, 39, 20, 2, 99}, {66, 47, 28, 40, 21, 3}, {67, 48, 29, 41, 22, 4}, {56, 68, 49, 30, 23, 5}, {57, 69, 50, 31, 24, 6}, {58, 51, 32, 25, 7, 99}, {59, 52, 33, 14, 26, 8}, {60, 53, 34, 15, 27, 9}, {61, 42, 54, 35, 16, 10}, {62, 43, 55, 36, 17, 11}, {63, 44, 37, 18, 0, 12},
            {64, 45, 38, 19, 1, 13}, {65, 46, 39, 20, 2, 99}, {66, 47, 28, 40, 21, 3}, {67, 48, 29, 41, 22, 4}, {56, 68, 49, 30, 23, 5}, {57, 69, 50, 31, 24, 6}, {58, 51, 32, 25, 7, 99}, {59, 52, 33, 14, 26, 8}, {60, 53, 34, 15, 27, 9}, {61, 42, 54, 35, 16, 10}, {62, 43, 55, 36, 17, 11}, {63, 44, 37, 18, 0, 12},
            {64, 45, 38, 19, 1, 13}, {65, 46, 39, 20, 2, 99}, {66, 47, 28, 40, 21, 3}, {67, 48, 29, 41, 22, 4}, {56, 68, 49, 30, 23, 5}, {57, 69, 50, 31, 24, 6}, {58, 51, 32, 25, 7, 99}, {59, 52, 33, 14, 26, 8}, {60, 53, 34, 15, 27, 9}, {61, 42, 54, 35, 16, 10}, {62, 43, 55, 36, 17, 11}, {63, 44, 37, 18, 0, 12},
            {64, 45, 38, 19, 1, 13}, {65, 46, 39, 20, 2, 99}, {66, 47, 28, 40, 21, 3}, {67, 48, 29, 41, 22, 4}, {56, 68, 49, 30, 23, 5}, {57, 69, 50, 31, 24, 6}, {58, 51, 32, 25, 7, 99}, {59, 52, 33, 14, 26, 8}, {60, 53, 34, 15, 27, 9}, {61, 42, 54, 35, 16, 10}, {62, 43, 55, 36, 17, 11}, {63, 44, 37, 18, 0, 12},
            {64, 45, 38, 19, 1, 13}, {65, 46, 39, 20, 2, 99}, {66, 47, 28, 40, 21, 3}, {67, 48, 29, 41, 22, 4}, {56, 68, 49, 30, 23, 5}, {57, 69, 50, 31, 24, 6}, {58, 51, 32, 25, 7, 99}, {59, 52, 33, 14, 26, 8}, {60, 53, 34, 15, 27, 9}, {61, 42, 54, 35, 16, 10}, {62, 43, 55, 36, 17, 11}, {63, 44, 37, 18, 0, 12}
        };
        
        static const uint8_t mode4_positions[72][6] = {
            {59, 52, 33, 15, 27, 8},   // Note 0  (C)
            {60, 53, 34, 16, 9, 99},   // Note 1  (C#)
            {61, 42, 54, 35, 17, 10},  // Note 2  (D)
            {62, 43, 55, 36, 18, 11},  // Note 3  (Eb)
            {63, 44, 37, 19, 0, 12},   // Note 4  (E)
            {64, 45, 38, 20, 1, 13},   // Note 5  (F)
            {65, 46, 39, 21, 2, 99},   // Note 6  (F#)
            {66, 47, 28, 40, 22, 3},   // Note 7  (G)
            {67, 48, 29, 41, 23, 4},   // Note 8  (Ab)
            {56, 68, 49, 30, 24, 5},   // Note 9  (A)
            {57, 69, 50, 31, 25, 6},   // Note 10 (Bb)
            {58, 51, 32, 14, 26, 7},   // Note 11 (B)
            // Repeat pattern for other octaves (12-71)
            {59, 52, 33, 15, 27, 8}, {60, 53, 34, 16, 9, 99}, {61, 42, 54, 35, 17, 10}, {62, 43, 55, 36, 18, 11}, {63, 44, 37, 19, 0, 12}, {64, 45, 38, 20, 1, 13}, {65, 46, 39, 21, 2, 99}, {66, 47, 28, 40, 22, 3}, {67, 48, 29, 41, 23, 4}, {56, 68, 49, 30, 24, 5}, {57, 69, 50, 31, 25, 6}, {58, 51, 32, 14, 26, 7},
            {59, 52, 33, 15, 27, 8}, {60, 53, 34, 16, 9, 99}, {61, 42, 54, 35, 17, 10}, {62, 43, 55, 36, 18, 11}, {63, 44, 37, 19, 0, 12}, {64, 45, 38, 20, 1, 13}, {65, 46, 39, 21, 2, 99}, {66, 47, 28, 40, 22, 3}, {67, 48, 29, 41, 23, 4}, {56, 68, 49, 30, 24, 5}, {57, 69, 50, 31, 25, 6}, {58, 51, 32, 14, 26, 7},
            {59, 52, 33, 15, 27, 8}, {60, 53, 34, 16, 9, 99}, {61, 42, 54, 35, 17, 10}, {62, 43, 55, 36, 18, 11}, {63, 44, 37, 19, 0, 12}, {64, 45, 38, 20, 1, 13}, {65, 46, 39, 21, 2, 99}, {66, 47, 28, 40, 22, 3}, {67, 48, 29, 41, 23, 4}, {56, 68, 49, 30, 24, 5}, {57, 69, 50, 31, 25, 6}, {58, 51, 32, 14, 26, 7},
            {59, 52, 33, 15, 27, 8}, {60, 53, 34, 16, 9, 99}, {61, 42, 54, 35, 17, 10}, {62, 43, 55, 36, 18, 11}, {63, 44, 37, 19, 0, 12}, {64, 45, 38, 20, 1, 13}, {65, 46, 39, 21, 2, 99}, {66, 47, 28, 40, 22, 3}, {67, 48, 29, 41, 23, 4}, {56, 68, 49, 30, 24, 5}, {57, 69, 50, 31, 25, 6}, {58, 51, 32, 14, 26, 7},
            {59, 52, 33, 15, 27, 8}, {60, 53, 34, 16, 9, 99}, {61, 42, 54, 35, 17, 10}, {62, 43, 55, 36, 18, 11}, {63, 44, 37, 19, 0, 12}, {64, 45, 38, 20, 1, 13}, {65, 46, 39, 21, 2, 99}, {66, 47, 28, 40, 22, 3}, {67, 48, 29, 41, 23, 4}, {56, 68, 49, 30, 24, 5}, {57, 69, 50, 31, 25, 6}, {58, 51, 32, 14, 26, 7}
        };
        
        const uint8_t (*selected_positions)[6] = (smartchordlightmode == 3) ? mode3_positions : mode4_positions;
        
        for (uint8_t current_layer = 0; current_layer < ACTUAL_MIDI_LAYERS; current_layer++) {
            for (uint8_t note = 0; note < 72; note++) {
                for (uint8_t pos = 0; pos < 6; pos++) {
                    optimized_midi_positions[current_layer][note][pos] = selected_positions[note][pos];
                }
                optimized_midi_velocities[current_layer][note] = 64;
            }
        }
    }
}

// REPLACEMENT MAIN FUNCTION
void scan_current_layer_midi_leds(void) {
    discover_midi_usage();      // Phase 1: Find actual requirements
    allocate_midi_storage();    // Phase 2: Allocate optimal storage
    populate_midi_data();       // Phase 3: Fill with data
}

// Ultra-fast lookup function
uint8_t get_midi_led_position(uint8_t layer, uint8_t note_index, uint8_t position_index) {
    if (optimized_midi_positions == NULL) return 99;
    if (layer >= 12) return 99;
    
    uint8_t array_index = layer_to_index_map[layer];
    if (array_index == 255) return 99;
    if (note_index >= 72 || position_index >= 6) return 99;
    
    return optimized_midi_positions[array_index][note_index][position_index];
}

// Get stored velocity for a note
uint8_t get_midi_velocity(uint8_t layer, uint8_t note_index) {
    if (optimized_midi_velocities == NULL) return 64;
    if (layer >= 12) return 64;
    
    uint8_t array_index = layer_to_index_map[layer];
    if (array_index == 255) return 64;
    if (note_index >= 72) return 64;
    
    return optimized_midi_velocities[array_index][note_index];
}

// REPLACEMENT UPDATE FUNCTION
void update_chord_key_indices(uint8_t note_index, int chord_num) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    
    switch(chord_num) {
        case 1:
            chordkey1_led_index = get_midi_led_position(current_layer, note_index, 0);
            chordkey1_led_index2 = get_midi_led_position(current_layer, note_index, 1);
            chordkey1_led_index3 = get_midi_led_position(current_layer, note_index, 2);
            chordkey1_led_index4 = get_midi_led_position(current_layer, note_index, 3);
            chordkey1_led_index5 = get_midi_led_position(current_layer, note_index, 4);
            chordkey1_led_index6 = get_midi_led_position(current_layer, note_index, 5);
            break;
        case 2:
            chordkey2_led_index = get_midi_led_position(current_layer, note_index, 0);
            chordkey2_led_index2 = get_midi_led_position(current_layer, note_index, 1);
            chordkey2_led_index3 = get_midi_led_position(current_layer, note_index, 2);
            chordkey2_led_index4 = get_midi_led_position(current_layer, note_index, 3);
            chordkey2_led_index5 = get_midi_led_position(current_layer, note_index, 4);
            chordkey2_led_index6 = get_midi_led_position(current_layer, note_index, 5);
            break;
        case 3:
            chordkey3_led_index = get_midi_led_position(current_layer, note_index, 0);
            chordkey3_led_index2 = get_midi_led_position(current_layer, note_index, 1);
            chordkey3_led_index3 = get_midi_led_position(current_layer, note_index, 2);
            chordkey3_led_index4 = get_midi_led_position(current_layer, note_index, 3);
            chordkey3_led_index5 = get_midi_led_position(current_layer, note_index, 4);
            chordkey3_led_index6 = get_midi_led_position(current_layer, note_index, 5);
            break;
        case 4:
            chordkey4_led_index = get_midi_led_position(current_layer, note_index, 0);
            chordkey4_led_index2 = get_midi_led_position(current_layer, note_index, 1);
            chordkey4_led_index3 = get_midi_led_position(current_layer, note_index, 2);
            chordkey4_led_index4 = get_midi_led_position(current_layer, note_index, 3);
            chordkey4_led_index5 = get_midi_led_position(current_layer, note_index, 4);
            chordkey4_led_index6 = get_midi_led_position(current_layer, note_index, 5);
            break;
        case 5:
            chordkey5_led_index = get_midi_led_position(current_layer, note_index, 0);
            chordkey5_led_index2 = get_midi_led_position(current_layer, note_index, 1);
            chordkey5_led_index3 = get_midi_led_position(current_layer, note_index, 2);
            chordkey5_led_index4 = get_midi_led_position(current_layer, note_index, 3);
            chordkey5_led_index5 = get_midi_led_position(current_layer, note_index, 4);
            chordkey5_led_index6 = get_midi_led_position(current_layer, note_index, 5);
            break;
        case 6:
            chordkey6_led_index = get_midi_led_position(current_layer, note_index, 0);
            chordkey6_led_index2 = get_midi_led_position(current_layer, note_index, 1);
            chordkey6_led_index3 = get_midi_led_position(current_layer, note_index, 2);
            chordkey6_led_index4 = get_midi_led_position(current_layer, note_index, 3);
            chordkey6_led_index5 = get_midi_led_position(current_layer, note_index, 4);
            chordkey6_led_index6 = get_midi_led_position(current_layer, note_index, 5);
            break;
        case 7:
            chordkey7_led_index = get_midi_led_position(current_layer, note_index, 0);
            chordkey7_led_index2 = get_midi_led_position(current_layer, note_index, 1);
            chordkey7_led_index3 = get_midi_led_position(current_layer, note_index, 2);
            chordkey7_led_index4 = get_midi_led_position(current_layer, note_index, 3);
            chordkey7_led_index5 = get_midi_led_position(current_layer, note_index, 4);
            chordkey7_led_index6 = get_midi_led_position(current_layer, note_index, 5);
            break;
    }
}

// Helper function to get all 6 LED positions for a note at once (for optimization)
void get_all_note_positions(uint8_t layer, uint8_t note_index, uint8_t* positions) {
    if (optimized_midi_positions == NULL || layer >= 12) {
        for (int i = 0; i < 6; i++) positions[i] = 99;
        return;
    }
    
    uint8_t array_index = layer_to_index_map[layer];
    if (array_index == 255 || note_index >= 72) {
        for (int i = 0; i < 6; i++) positions[i] = 99;
        return;
    }
    
    for (int i = 0; i < 6; i++) {
        positions[i] = optimized_midi_positions[array_index][note_index][i];
    }
}

bool custom_layer_animations_enabled = false;
keyboard_settings_t keyboard_settings;

void reset_keyboard_settings(void) {
    // Reset to default values
    velocity_sensitivity = 1;
    cc_sensitivity = 1;
    channel_number = 0;
    transpose_number = 0;
    octave_number = 0;
    transpose_number2 = 0;
    octave_number2 = 0;
    transpose_number3 = 0;
    octave_number3 = 0;
    velocity_number = 127;
    dynamic_range = 127;
    oledkeyboard = 0;
    smartchordlight = 0;
    smartchordlightmode = 0;
    keysplitchannel = 0;
    keysplit2channel = 0;
    keysplitstatus = 0;
    keysplittransposestatus = 0;
    keysplitvelocitystatus = 0;
    custom_layer_animations_enabled = false;
    sample_mode_active = false;
    unsynced_mode_active = 0;
    loop_messaging_enabled = false;
    loop_messaging_channel = 16;
    sync_midi_mode = false;
    alternate_restart_mode = false;
    colorblindmode = 0;
    cclooprecording = false;
    truesustain = false;

    // Reset Global MIDI Settings (velocity curves, sustain)
    // Note: aftertouch_mode and aftertouch_cc are now per-layer (in layer_actuations)
    he_velocity_curve = 0;  // Linear (curve index 0)
    he_velocity_min = 1;
    he_velocity_max = 127;
    keysplit_he_velocity_curve = 0;  // Linear (curve index 0)
    keysplit_he_velocity_min = 1;
    keysplit_he_velocity_max = 127;
    triplesplit_he_velocity_curve = 0;  // Linear (curve index 0)
    triplesplit_he_velocity_min = 1;
    triplesplit_he_velocity_max = 127;
    base_sustain = 0;
    keysplit_sustain = 0;
    triplesplit_sustain = 0;
    // Hall Effect Sensor Linearization
    lut_correction_strength = 0;  // Default: linear (no correction)

    // Update keyboard settings structure
    keyboard_settings.velocity_sensitivity = velocity_sensitivity;
    keyboard_settings.cc_sensitivity = cc_sensitivity;
    keyboard_settings.channel_number = channel_number;
    keyboard_settings.transpose_number = transpose_number;
    keyboard_settings.octave_number = octave_number;
    keyboard_settings.transpose_number2 = transpose_number2;
    keyboard_settings.octave_number2 = octave_number2;
    keyboard_settings.transpose_number3 = transpose_number3;
    keyboard_settings.octave_number3 = octave_number3;
    keyboard_settings.dynamic_range = dynamic_range;
    keyboard_settings.oledkeyboard = oledkeyboard;
    keyboard_settings.overdub_advanced_mode = overdub_advanced_mode;
    keyboard_settings.smartchordlightmode = smartchordlightmode;
    keyboard_settings.keysplitchannel = keysplitchannel;
    keyboard_settings.keysplit2channel = keysplit2channel;
    keyboard_settings.keysplitstatus = keysplitstatus;
    keyboard_settings.keysplittransposestatus = keysplittransposestatus;
    keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
    keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
    keyboard_settings.unsynced_mode_active = unsynced_mode_active;
    keyboard_settings.sample_mode_active = sample_mode_active;
    keyboard_settings.loop_messaging_enabled = loop_messaging_enabled;
    keyboard_settings.loop_messaging_channel = loop_messaging_channel;
    keyboard_settings.sync_midi_mode = sync_midi_mode;
    keyboard_settings.alternate_restart_mode = alternate_restart_mode;
    keyboard_settings.colorblindmode = colorblindmode;
    keyboard_settings.cclooprecording = cclooprecording;
    keyboard_settings.truesustain = truesustain;
    // Global MIDI Settings (aftertouch settings are now per-layer)
    keyboard_settings.he_velocity_curve = he_velocity_curve;
    keyboard_settings.he_velocity_min = he_velocity_min;
    keyboard_settings.he_velocity_max = he_velocity_max;
    keyboard_settings.keysplit_he_velocity_curve = keysplit_he_velocity_curve;
    keyboard_settings.keysplit_he_velocity_min = keysplit_he_velocity_min;
    keyboard_settings.keysplit_he_velocity_max = keysplit_he_velocity_max;
    keyboard_settings.triplesplit_he_velocity_curve = triplesplit_he_velocity_curve;
    keyboard_settings.triplesplit_he_velocity_min = triplesplit_he_velocity_min;
    keyboard_settings.triplesplit_he_velocity_max = triplesplit_he_velocity_max;
    keyboard_settings.base_sustain = base_sustain;
    keyboard_settings.keysplit_sustain = keysplit_sustain;
    keyboard_settings.triplesplit_sustain = triplesplit_sustain;
    // Hall Effect Sensor Linearization
    keyboard_settings.lut_correction_strength = lut_correction_strength;
    // MIDI Routing Override Settings
    keyboard_settings.channeloverride = channeloverride;
    keyboard_settings.velocityoverride = velocityoverride;
    keyboard_settings.transposeoverride = transposeoverride;
    keyboard_settings.midi_in_mode = midi_in_mode;
    keyboard_settings.usb_midi_mode = usb_midi_mode;
    keyboard_settings.midi_clock_source = midi_clock_source;
}

void save_keyboard_settings_to_slot(uint8_t slot) {
    // Ensure slot is between 0-4
    slot = slot % 5;
    eeprom_update_block(&keyboard_settings, (uint8_t*)SETTINGS_EEPROM_ADDR(slot), SETTINGS_SIZE);
}

void load_keyboard_settings_from_slot(uint8_t slot) {
    // Ensure slot is between 0-4
    slot = slot % 5;
    eeprom_read_block(&keyboard_settings, (uint8_t*)SETTINGS_EEPROM_ADDR(slot), SETTINGS_SIZE);
    
    // Update ALL global variables with loaded settings
    velocity_sensitivity = keyboard_settings.velocity_sensitivity;
    cc_sensitivity = keyboard_settings.cc_sensitivity;
    channel_number = keyboard_settings.channel_number;
    transpose_number = keyboard_settings.transpose_number;
    octave_number = keyboard_settings.octave_number;
    transpose_number2 = keyboard_settings.transpose_number2;
    octave_number2 = keyboard_settings.octave_number2;
    transpose_number3 = keyboard_settings.transpose_number3;
    octave_number3 = keyboard_settings.octave_number3;
    dynamic_range = keyboard_settings.dynamic_range;
    oledkeyboard = keyboard_settings.oledkeyboard;
    overdub_advanced_mode = keyboard_settings.overdub_advanced_mode;
    smartchordlightmode = keyboard_settings.smartchordlightmode;
    keysplitchannel = keyboard_settings.keysplitchannel;
    keysplit2channel = keyboard_settings.keysplit2channel;
    keysplitstatus = keyboard_settings.keysplitstatus;
    keysplittransposestatus = keyboard_settings.keysplittransposestatus;
    keysplitvelocitystatus = keyboard_settings.keysplitvelocitystatus;
    custom_layer_animations_enabled = keyboard_settings.custom_layer_animations_enabled;
    unsynced_mode_active = keyboard_settings.unsynced_mode_active;
    sample_mode_active = keyboard_settings.sample_mode_active;
    
    // Load ALL the new variables properly
    loop_messaging_enabled = keyboard_settings.loop_messaging_enabled;
    loop_messaging_channel = keyboard_settings.loop_messaging_channel;
    sync_midi_mode = keyboard_settings.sync_midi_mode;
    alternate_restart_mode = keyboard_settings.alternate_restart_mode;
    colorblindmode = keyboard_settings.colorblindmode;
    cclooprecording = keyboard_settings.cclooprecording;
    truesustain = keyboard_settings.truesustain;

    // Load Global MIDI Settings (velocity curves, sustain)
    // Note: aftertouch_mode and aftertouch_cc are now per-layer (in layer_actuations)
    he_velocity_curve = keyboard_settings.he_velocity_curve;
    he_velocity_min = keyboard_settings.he_velocity_min;
    he_velocity_max = keyboard_settings.he_velocity_max;
    keysplit_he_velocity_curve = keyboard_settings.keysplit_he_velocity_curve;
    keysplit_he_velocity_min = keyboard_settings.keysplit_he_velocity_min;
    keysplit_he_velocity_max = keyboard_settings.keysplit_he_velocity_max;
    triplesplit_he_velocity_curve = keyboard_settings.triplesplit_he_velocity_curve;
    triplesplit_he_velocity_min = keyboard_settings.triplesplit_he_velocity_min;
    triplesplit_he_velocity_max = keyboard_settings.triplesplit_he_velocity_max;
    base_sustain = keyboard_settings.base_sustain;
    keysplit_sustain = keyboard_settings.keysplit_sustain;
    triplesplit_sustain = keyboard_settings.triplesplit_sustain;
    // Hall Effect Sensor Linearization
    lut_correction_strength = keyboard_settings.lut_correction_strength;
    // MIDI Routing Override Settings
    channeloverride = keyboard_settings.channeloverride;
    velocityoverride = keyboard_settings.velocityoverride;
    transposeoverride = keyboard_settings.transposeoverride;
    midi_in_mode = (midi_in_mode_t)keyboard_settings.midi_in_mode;
    usb_midi_mode = (usb_midi_mode_t)keyboard_settings.usb_midi_mode;
    midi_clock_source = (midi_clock_source_t)keyboard_settings.midi_clock_source;

    // NO struct assignments here - we just loaded FROM the struct TO the globals
}

// Keep original functions for backward compatibility
void save_keyboard_settings(void) {
    save_keyboard_settings_to_slot(0);  // Default slot is 0
}

void load_keyboard_settings(void) {
    load_keyboard_settings_from_slot(0);  // Default slot is 0
}

void update_layer_animations_setting_slot0_direct(bool new_value) {
    // Calculate the exact EEPROM address for the custom_layer_animations_enabled field
    uint8_t* base_addr = (uint8_t*)SETTINGS_EEPROM_ADDR(0);
    uint8_t* field_addr = base_addr + offsetof(keyboard_settings_t, custom_layer_animations_enabled);
    
    // Update ONLY that specific byte in EEPROM - leaves all other settings untouched
    eeprom_update_byte(field_addr, new_value ? 1 : 0);
    
    // Update the global variable to keep it in sync
    custom_layer_animations_enabled = new_value;
}

// In orthomidi5x14.c
layer_categories_t led_categories[NUM_LAYERS] = {0};

void scan_keycode_categories(void) {
    // Reset all layers
    for (int layer = 0; layer < NUM_LAYERS; layer++) {
        led_categories[layer].count = 0;
    }
    
    // Scan through all layers
    for (int layer = 0; layer < NUM_LAYERS; layer++) {
        uint8_t led_count = 0;
        
        // Scan through the matrix for each layer
        for (int row = 0; row < MATRIX_ROWS; row++) {
            for (int col = 0; col < MATRIX_COLS; col++) {
                uint16_t keycode = dynamic_keymap_get_keycode(layer, row, col);
                uint8_t led_index = g_led_config.matrix_co[row][col];
                
                // Only process valid LED indices
                if (led_index < RGB_MATRIX_LED_COUNT) {
                    uint8_t category = 0;
                    
                    if (keycode >= 28931 && keycode <= 29002) { // Midi keys
                        category = 1;  // Red
                    }
                    else if (keycode >= 50688 && keycode <= 50759) { // keysplit 1 keys
                        category = 2;  // Blue
                    }

                    else if (keycode >= 50800 && keycode <= 50871) { // keysplit 2 keys
                        category = 3;  // Green
                    }
					
					else if (keycode >= 0xC93C && keycode <= 0xC94F ) { // Chord Trainer
                        category = 4;  // Green
                    }
					
					else if (keycode >= 0xC92A && keycode <= 0xC93B) { // Ear Trainer
                        category = 5;  // Green
                    }
					
					else if ((keycode >= 0xC802 && keycode <= 0xC80B) || (keycode >= 0xC7FC && keycode <= 0xC7FF) || (keycode >= 0xC766 && keycode <= 0xC771)) {  // keysplit 3 transpose
                        category = 6;  // Green
                    }
					
					else if (keycode >= 0xC77A && keycode <= 0xC7FB) { // keysplit 2 velocity
                        category = 7;  // Green
                    }
					
					else if ((keycode == 0xC662) || (keycode >= 0xC800 && keycode <= 0xC801)) { // keysplit toggles
                        category = 8;  // Green
                    }
					
					else if (keycode >= 0xC74C && keycode <= 0xC765) { // keysplit transpose 
                        category = 9;  // Green
                    }
					
					else if (keycode >= 0xC7CA && keycode <= 0xC74B) { // keysplit velocity
                        category = 10;  // Green
                    }
					
					else if (keycode >= 0xC6B8 && keycode <= 0xC6C9) { // keysplit 2 channel
                        category = 11;  // Green
                    }
					
					else if (keycode >= 0xC650 && keycode <= 0xC661) { // keysplit channel
                        category = 12;  // Green					
                    }
					
					else if ((keycode == 0xC9E1) || (keycode >= 0xC4A2 && keycode <= 0xC4A3) || (keycode >= 0xC458 && keycode <= 0xC49F) || (keycode >= 0x7820 && keycode <= 0x7833)) { // RGB modes and colors 0x7820 33
                        category = 13;  // Green
                    }
					
					else if ((keycode >= 0xC42C && keycode <= 0xC437) || (keycode >= 0xC950 && keycode <= 0xC960) || (keycode >= 0xC305 && keycode <= 0xC384) || (keycode >= 0xC436 && keycode <= 0xC437)) { // VELOCITY MAIN
                        category = 14;  // Green
                    }
					
					else if ((keycode >= 0xC438 && keycode <= 0xC457) || (keycode >= 0xC4A2 && keycode <= 0xC4A2) || (keycode >= 0x7173 && keycode <= 0x7184) ) { // CHANNEL MAIN 
                        category = 15;  // Green
                    }
					
					else if ((keycode >= 0xC80C && keycode <= 0xC81B) || (keycode >= 0x8180 && keycode <= 0xC17F) || (keycode >= 0x8000 && keycode <= 0x807F) || (keycode >= 0x8080 && keycode <= 0x817F) || (keycode >= 0xC961 && keycode <= 0xC9E0) || (keycode >= 0xC280 && keycode <= 0xC2FF)  || (keycode >= 0xC180 && keycode <= 0xC27F) || (keycode >= 0xC303 && keycode <= 0xC304)) { // CC MAIN
                        category = 16;  // Green
                    }
					
					else if ((keycode >= 0xC4A0 && keycode <= 0xC4A1) || (keycode >= 0xC38B && keycode <= 0xC42B)){ // SMARTCHORDMAIN 
                        category = 17;  // Green
                    }
					
					else if ((keycode >= 0xC81E && keycode <= 0xC8E6) || (keycode >= 0x7C53 && keycode <= 0x7C57)) { // MACRO 0x7C53
                        category = 18;  // Green
                    }
					else if (keycode >= 0x714B && keycode <= 0x7165) { // TRANSPOSE MAIN
                        category = 19;  // Green
                    }
					
					else if (keycode >= 0x5700 && keycode <= 0x5763) { // tapdance
                        category = 20;  // Green
                    }
					
					
					else if (keycode >= 0x04 && keycode <= 0x1D) { // LETTERS
                        category = 21;  // Green
                    }
					
					else if ((keycode >= 0x1E && keycode <= 0x27) || (keycode >= 0x59 && keycode <= 0x62)) { // NUMBERS
                        category = 22;  // Green
                    }
					
					else if ((keycode >= 0x28 && keycode <= 0x38) || (keycode >= 0x46 && keycode <= 0x4E) || (keycode == 0x63) || (keycode == 0x67) || (keycode == 0x85) || (keycode >= 0x53 && keycode <= 0x58) ) { // PUNCTUATION
                        category = 23;  // Green
                    }
					
					else if ((keycode >= 0x3A && keycode <= 0x45) || (keycode >= 0x68 && keycode <= 0x73)) { // F KEYS
                        category = 24;  // Green
                    }
					
					else if ((keycode >= 0x5240 && keycode <= 0x524B) || (keycode >= 0x5220 && keycode <= 0x522B) || (keycode >= 0x5260 && keycode <= 0x526B)  || (keycode >= 0x52C0 && keycode <= 0x52CB)  || (keycode >= 0x5280 && keycode <= 0x528B)  || (keycode >= 0x5200 && keycode <= 0x520B) || (keycode >= 0x7C77 && keycode <= 0x7C78) )  { // LAYERS
                        category = 25;  // Green
                    }
					
					else if (keycode >= 0x4F && keycode <= 0x52) { // ARROWS
                        category = 26;  // Green
                    }
					
					else if (keycode >= 0x7186 && keycode <= 0x718F) { // MIDI MISC
                        category = 27;  // Green
                    }
					else if (keycode == 0x39) { // Caps Lock
					category = 29;  // New category for caps lock
					}
					else if (keycode == 0xC929) { // Tap Tempo
					category = 30;  // New category for tap tempo
					}
					else if (keycode >= 0xCC08 && keycode <= 0xCC0B) { // Macro keys 1-4
					category = 31 + (keycode - 0xCC08);  // Categories 31-34 for macros 1-4
					}
					
					//else { // REST OF EVERYTHING
                    //    category = 28;  // THE REST
                    //}
                    
                    // Only store if we found a category
                    if (category > 0 && led_count < MAX_CATEGORIZED_LEDS) {
                        led_categories[layer].leds[led_count].led_index = led_index;
                        led_categories[layer].leds[led_count].category = category;
                        led_count++;
                    }
                }
            }
        }
        led_categories[layer].count = led_count;
    }
}

void save_current_rgb_settings(uint8_t layer) {
    if (layer >= NUM_LAYERS) return;
    
    uint8_t block_data[LAYER_BLOCK_SIZE] = {
        rgb_matrix_get_mode(),    // Index 0: Mode
        rgb_matrix_get_hue(),     // Index 1: Hue
        rgb_matrix_get_sat(),     // Index 2: Saturation
        rgb_matrix_get_val(),     // Index 3: Brightness
        rgb_matrix_get_speed(),   // Index 4: Speed
        1,                        // Index 5: is_set flag
        0,                        // Index 6-8: Reserved for future use
        0,
        0
    };
    
    save_layer_block(layer, block_data);
}

void save_layer_block(uint8_t layer, uint8_t data[LAYER_BLOCK_SIZE]) {
    uint16_t addr = LAYER_SETTINGS_EEPROM_ADDR + (layer * LAYER_BLOCK_SIZE);
    for (int i = 0; i < LAYER_BLOCK_SIZE; i++) {
        eeprom_update_byte((uint8_t*)(addr + i), data[i]);
    }
}

void load_layer_block(uint8_t layer, uint8_t data[LAYER_BLOCK_SIZE]) {
    uint16_t addr = LAYER_SETTINGS_EEPROM_ADDR + (layer * LAYER_BLOCK_SIZE);
    for (int i = 0; i < LAYER_BLOCK_SIZE; i++) {
        data[i] = eeprom_read_byte((uint8_t*)(addr + i));
    }
}

void apply_layer_block(uint8_t data[LAYER_BLOCK_SIZE]) {
    rgb_matrix_mode(data[0]);         // Mode
    rgb_matrix_sethsv(data[1],        // Hue
                      data[2],        // Saturation
                      data[3]);       // Brightness
    rgb_matrix_set_speed(data[4]);    // Speed
}

void apply_layer_rgb_settings(uint8_t layer) {
    if (layer >= NUM_LAYERS) return;
    
    uint8_t block_data[LAYER_BLOCK_SIZE];
    load_layer_block(layer, block_data);
    
    // Check if this layer has settings saved (index 5 is our is_set flag)
    if (block_data[5]) {
        apply_layer_block(block_data);
    }
}

layer_state_t layer_state_set_user(layer_state_t state) {
    if (custom_layer_animations_enabled && (smartchordstatus == 0)) {
        uint8_t current_layer = get_highest_layer(state | default_layer_state);
        apply_layer_rgb_settings(current_layer);
    }
    return state;
}

bool rgb_matrix_indicators_user(void) {
    // Check if we're in the custom layersets mode
    if (rgb_matrix_get_mode() == RGB_MATRIX_CUSTOM_LAYERSETS) {
        uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
        apply_layer_rgb_settings(current_layer);
        return false; // Skip other indicators
    }
    return true; // Continue with other indicators
}

// =============================================================================
// CUSTOM ANIMATION EEPROM FUNCTIONS
// =============================================================================

// Save all custom slots to EEPROM
void save_custom_animations_to_eeprom(void) {
    eeprom_update_block(custom_slots, (uint8_t*)EECONFIG_CUSTOM_ANIMATIONS, sizeof(custom_slots));
}

// Load all custom slots from EEPROM
void load_custom_animations_from_eeprom(void) {
    eeprom_read_block(custom_slots, (uint8_t*)EECONFIG_CUSTOM_ANIMATIONS, EECONFIG_CUSTOM_ANIMATIONS_SIZE);
}

// Save single slot to EEPROM
void save_custom_slot_to_eeprom(uint8_t slot) {
    if (slot < NUM_CUSTOM_SLOTS) {
        eeprom_update_block(&custom_slots[slot], (uint8_t*)(EECONFIG_CUSTOM_ANIMATIONS + (slot * sizeof(custom_animation_config_t))), sizeof(custom_animation_config_t));
    }
}

// Load single slot from EEPROM
void load_custom_slot_from_eeprom(uint8_t slot) {
    if (slot < NUM_CUSTOM_SLOTS) {
        eeprom_read_block(&custom_slots[slot], (uint8_t*)(EECONFIG_CUSTOM_ANIMATIONS + (slot * sizeof(custom_animation_config_t))), sizeof(custom_animation_config_t));
    }
}
// =============================================================================
// PARAMETER SETTING FUNCTIONS WITH EEPROM SAVE
// =============================================================================

void set_and_save_custom_slot_live_positioning(uint8_t slot, uint8_t value) {
    set_custom_slot_live_positioning(slot, value);  
}

void set_and_save_custom_slot_macro_positioning(uint8_t slot, uint8_t value) {
    set_custom_slot_macro_positioning(slot, value);   
}

void set_and_save_custom_slot_live_animation(uint8_t slot, uint8_t value) {
    set_custom_slot_live_animation(slot, value);   
}

void set_and_save_custom_slot_macro_animation(uint8_t slot, uint8_t value) {
    set_custom_slot_macro_animation(slot, value);   
}

void set_and_save_custom_slot_use_influence(uint8_t slot, bool value) {
    set_custom_slot_use_influence(slot, value);
}

// =============================================================================
// LAYER ACTUATION EEPROM FUNCTIONS
// =============================================================================

// Define EEPROM address for layer actuations (place after custom animations)
#ifndef EECONFIG_LAYER_ACTUATIONS
#define EECONFIG_LAYER_ACTUATIONS (EECONFIG_CUSTOM_ANIMATIONS + EECONFIG_CUSTOM_ANIMATIONS_SIZE)
#endif

// Save all layer actuations to EEPROM
void save_layer_actuations(void) {
    eeprom_update_block(layer_actuations, (uint8_t*)EECONFIG_LAYER_ACTUATIONS, sizeof(layer_actuations));
}

// Load all layer actuations from EEPROM
void load_layer_actuations(void) {
    // TROUBLESHOOTING: Bypass EEPROM and use hardcoded defaults
    // This ensures we have known-good actuation values for testing
    // TODO: Re-enable EEPROM loading once key detection is working
    initialize_layer_actuations();

    // Original EEPROM loading code (disabled for troubleshooting):
    // eeprom_read_block(layer_actuations, (uint8_t*)EECONFIG_LAYER_ACTUATIONS, sizeof(layer_actuations));
}

// Reset all layer actuations to defaults
void reset_layer_actuations(void) {
    initialize_layer_actuations();
    save_layer_actuations();
}

// Set layer actuation parameters (extended with aftertouch settings)
void set_layer_actuation(uint8_t layer, uint8_t normal, uint8_t midi, uint8_t velocity,
                         uint8_t vel_speed, uint8_t flags, uint8_t aftertouch_mode,
                         uint8_t aftertouch_cc, uint8_t vibrato_sensitivity,
                         uint16_t vibrato_decay_time) {
    if (layer >= 12) return;

    layer_actuations[layer].normal_actuation = normal;
    layer_actuations[layer].midi_actuation = midi;
    layer_actuations[layer].velocity_mode = velocity;
    layer_actuations[layer].velocity_speed_scale = vel_speed;
    layer_actuations[layer].flags = flags;
    layer_actuations[layer].aftertouch_mode = aftertouch_mode;
    layer_actuations[layer].aftertouch_cc = aftertouch_cc;
    layer_actuations[layer].vibrato_sensitivity = vibrato_sensitivity;
    layer_actuations[layer].vibrato_decay_time = vibrato_decay_time;
}

// Get layer actuation parameters (extended with aftertouch settings)
void get_layer_actuation(uint8_t layer, uint8_t *normal, uint8_t *midi, uint8_t *velocity,
                         uint8_t *vel_speed, uint8_t *flags, uint8_t *aftertouch_mode,
                         uint8_t *aftertouch_cc, uint8_t *vibrato_sensitivity,
                         uint16_t *vibrato_decay_time) {
    if (layer >= 12) return;

    *normal = layer_actuations[layer].normal_actuation;
    *midi = layer_actuations[layer].midi_actuation;
    *velocity = layer_actuations[layer].velocity_mode;
    *vel_speed = layer_actuations[layer].velocity_speed_scale;
    *flags = layer_actuations[layer].flags;
    *aftertouch_mode = layer_actuations[layer].aftertouch_mode;
    *aftertouch_cc = layer_actuations[layer].aftertouch_cc;
    *vibrato_sensitivity = layer_actuations[layer].vibrato_sensitivity;
    *vibrato_decay_time = layer_actuations[layer].vibrato_decay_time;
}

// Helper function for flag checking (already defined in orthomidi5x14.c earlier - this is the implementation)

bool layer_use_fixed_velocity(uint8_t layer) {
    if (layer >= 12) return false;
    return (layer_actuations[layer].flags & LAYER_ACTUATION_FLAG_USE_FIXED_VELOCITY) != 0;
}

// =============================================================================
// HID HANDLERS FOR LAYER ACTUATION (VIA/VIAL Communication)
// =============================================================================

// HID command IDs are defined in quantum/process_keycode/process_dynamic_macro.h

// Set layer actuation from HID data (extended with aftertouch settings)
void handle_set_layer_actuation(const uint8_t* data) {
    // New protocol: 11 bytes per layer
    // [0]=layer, [1]=normal, [2]=midi, [3]=velocity_mode, [4]=vel_speed, [5]=flags,
    // [6]=aftertouch_mode, [7]=aftertouch_cc, [8]=vibrato_sensitivity,
    // [9-10]=vibrato_decay_time (little endian)
    uint8_t layer = data[0];
    if (layer >= 12) return;

    uint8_t normal = data[1];
    uint8_t midi = data[2];
    uint8_t velocity = data[3];
    uint8_t vel_speed = data[4];
    uint8_t flags = data[5];
    uint8_t aftertouch_mode = data[6];
    uint8_t aftertouch_cc = data[7];
    uint8_t vibrato_sensitivity = data[8];
    uint16_t vibrato_decay_time = data[9] | (data[10] << 8);  // Little endian

    set_layer_actuation(layer, normal, midi, velocity, vel_speed, flags,
                        aftertouch_mode, aftertouch_cc, vibrato_sensitivity, vibrato_decay_time);
    save_layer_actuations();
}

// Get layer actuation and send back via HID
// Response format: [success, normal, midi, velocity_mode, vel_speed, flags, aftertouch_mode, aftertouch_cc, vibrato_sensitivity, decay_lo, decay_hi] (11 bytes)
void handle_get_layer_actuation(uint8_t layer, uint8_t* response) {
    if (layer >= 12) {
        response[0] = 0;  // Error indicator
        return;
    }

    uint8_t normal, midi, velocity, vel_speed, flags;
    uint8_t aftertouch_mode, aftertouch_cc, vibrato_sensitivity;
    uint16_t vibrato_decay_time;

    get_layer_actuation(layer, &normal, &midi, &velocity, &vel_speed, &flags,
                        &aftertouch_mode, &aftertouch_cc, &vibrato_sensitivity, &vibrato_decay_time);

    response[0] = 0x01;  // Success
    response[1] = normal;
    response[2] = midi;
    response[3] = velocity;
    response[4] = vel_speed;
    response[5] = flags;
    response[6] = aftertouch_mode;
    response[7] = aftertouch_cc;
    response[8] = vibrato_sensitivity;
    response[9] = vibrato_decay_time & 0xFF;         // Low byte
    response[10] = (vibrato_decay_time >> 8) & 0xFF; // High byte
}

// Get all layer actuations
void handle_get_all_layer_actuations(void) {
    // This would send all layers back via HID
    // Implementation depends on your HID protocol
    // Placeholder for now
}

// Reset all layer actuations to defaults
void handle_reset_layer_actuations(void) {
    reset_layer_actuations();
}

// =============================================================================
// PER-KEY ACTUATION FUNCTIONS
// =============================================================================

// Initialize all keys to default 1.5mm (value 60)
void initialize_per_key_actuations(void) {
    for (uint8_t layer = 0; layer < 12; layer++) {
        for (uint8_t key = 0; key < 70; key++) {
            per_key_actuations[layer].keys[key].actuation = DEFAULT_ACTUATION_VALUE;
            per_key_actuations[layer].keys[key].deadzone_top = DEFAULT_DEADZONE_TOP;
            per_key_actuations[layer].keys[key].deadzone_bottom = DEFAULT_DEADZONE_BOTTOM;
            per_key_actuations[layer].keys[key].velocity_curve = DEFAULT_VELOCITY_CURVE;
            per_key_actuations[layer].keys[key].flags = DEFAULT_PER_KEY_FLAGS;  // Now using flags field
            per_key_actuations[layer].keys[key].rapidfire_press_sens = DEFAULT_RAPIDFIRE_PRESS_SENS;
            per_key_actuations[layer].keys[key].rapidfire_release_sens = DEFAULT_RAPIDFIRE_RELEASE_SENS;
            per_key_actuations[layer].keys[key].rapidfire_velocity_mod = DEFAULT_RAPIDFIRE_VELOCITY_MOD;
        }
    }
    // NOTE: Mode flags removed - firmware always uses per-key per-layer
}

// Save per-key actuations to EEPROM (ALL - 6.7KB, use sparingly)
void save_per_key_actuations(void) {
    eeprom_update_block(per_key_actuations,
                        (uint8_t*)PER_KEY_ACTUATION_EEPROM_ADDR,
                        PER_KEY_ACTUATION_SIZE);
    // NOTE: Mode flags removed - firmware always uses per-key per-layer
}

// Save a SINGLE key's actuation settings to EEPROM (8 bytes only)
// This is much faster than save_per_key_actuations() and won't cause USB issues
void save_single_key_actuation(uint8_t layer, uint8_t key_index) {
    if (layer >= 12 || key_index >= 70) return;

    // Calculate EEPROM offset for this specific key
    // Layout: per_key_actuations[layer][key] = base + (layer * 70 * 8) + (key * 8)
    uint32_t offset = PER_KEY_ACTUATION_EEPROM_ADDR +
                      (layer * 70 * sizeof(per_key_actuation_t)) +
                      (key_index * sizeof(per_key_actuation_t));

    // Write only this key's 8 bytes
    eeprom_update_block(&per_key_actuations[layer].keys[key_index],
                        (uint8_t*)offset,
                        sizeof(per_key_actuation_t));
}

// Save a single LAYER's per-key actuation settings to EEPROM (560 bytes)
// Used for operations like copy layer that affect all keys in one layer
void save_layer_per_key_actuations(uint8_t layer) {
    if (layer >= 12) return;

    // Calculate EEPROM offset for this layer
    // Layout: per_key_actuations[layer] = base + (layer * 70 * 8)
    uint32_t offset = PER_KEY_ACTUATION_EEPROM_ADDR +
                      (layer * 70 * sizeof(per_key_actuation_t));

    // Write this layer's 560 bytes (70 keys × 8 bytes)
    eeprom_update_block(&per_key_actuations[layer],
                        (uint8_t*)offset,
                        70 * sizeof(per_key_actuation_t));
}

// Load per-key actuations from EEPROM
void load_per_key_actuations(void) {
    eeprom_read_block(per_key_actuations,
                      (uint8_t*)PER_KEY_ACTUATION_EEPROM_ADDR,
                      PER_KEY_ACTUATION_SIZE);
    // NOTE: Mode flags removed - firmware always uses per-key per-layer
    // Invalidate per-key cache so loaded values take effect
    active_per_key_cache_layer = 0xFF;
}

// Reset all per-key actuations to default
void reset_per_key_actuations(void) {
    initialize_per_key_actuations();
    // Full save is acceptable here - reset is a rare user-initiated action
    save_per_key_actuations();
    // Invalidate per-key cache so changes take effect immediately
    active_per_key_cache_layer = 0xFF;
}

// Get actuation point for a specific key
// This function is called by matrix scanning code to determine actuation threshold
//
// INTEGRATION NOTE FOR MATRIX SCANNING:
// This function should be called from the analog matrix scanning code (likely in
// quantum/matrix or a custom matrix implementation) wherever the actuation threshold
// is checked. Replace direct accesses to:
//   - layer_actuations[layer].normal_actuation
//   - layer_actuations[layer].midi_actuation
// with calls to:
//   - get_key_actuation_point(layer, row, col)
//
// The function returns a value 0-100 representing 0-2.5mm of travel.
// NOTE: Firmware ALWAYS uses per-key per-layer settings now.
// The GUI handles "apply to all keys/layers" by writing the same values.
uint8_t get_key_actuation_point(uint8_t layer, uint8_t row, uint8_t col) {
    uint8_t key_index = row * 14 + col;  // 14 columns per row
    if (key_index >= 70 || layer >= 12) return DEFAULT_ACTUATION_VALUE;

    // Always return per-key per-layer actuation
    return per_key_actuations[layer].keys[key_index].actuation;
}

// Get pointer to per-key settings for a specific key
// NOTE: Firmware ALWAYS uses per-key per-layer settings now.
per_key_actuation_t* get_key_settings(uint8_t layer, uint8_t row, uint8_t col) {
    uint8_t key_index = row * 14 + col;
    if (key_index >= 70 || layer >= 12) return NULL;

    // Always return settings from the specified layer
    return &per_key_actuations[layer].keys[key_index];
}

// =============================================================================
// PER-KEY ACTUATION HID HANDLERS
// =============================================================================

// Set per-key actuation from HID data
// Format: [layer, key_index, actuation, deadzone_top, deadzone_bottom, velocity_curve,
//          flags, rapidfire_press_sens, rapidfire_release_sens, rapidfire_velocity_mod]
// flags: Bit 0=rapidfire_enabled, Bit 1=use_per_key_velocity_curve
// Total: 10 bytes
void handle_set_per_key_actuation(const uint8_t* data) {
    uint8_t layer = data[0];
    uint8_t key_index = data[1];

    if (layer >= 12 || key_index >= 70) {
        return;  // Invalid parameters
    }

    // Set all 8 fields of the per-key structure
    per_key_actuations[layer].keys[key_index].actuation = data[2];
    per_key_actuations[layer].keys[key_index].deadzone_top = data[3];
    per_key_actuations[layer].keys[key_index].deadzone_bottom = data[4];
    per_key_actuations[layer].keys[key_index].velocity_curve = data[5];
    per_key_actuations[layer].keys[key_index].flags = data[6];  // Now using flags field
    per_key_actuations[layer].keys[key_index].rapidfire_press_sens = data[7];
    per_key_actuations[layer].keys[key_index].rapidfire_release_sens = data[8];
    per_key_actuations[layer].keys[key_index].rapidfire_velocity_mod = (int8_t)data[9];

    // Update the cache directly if this is the currently cached layer
    // This avoids invalidating the cache which would cause it to be refilled with defaults
    if (layer == active_per_key_cache_layer && key_index < 70) {
        active_per_key_cache[key_index].actuation = data[2];
        active_per_key_cache[key_index].rt_down = data[7];   // rapidfire_press_sens
        active_per_key_cache[key_index].rt_up = data[8];     // rapidfire_release_sens
        active_per_key_cache[key_index].flags = data[6];
    }
    // If editing a different layer, no cache update needed - it will be loaded when that layer is activated

    // Save only this key to EEPROM (8 bytes, fast)
    save_single_key_actuation(layer, key_index);
}

// Get per-key actuation and send back via HID
// Format: [layer, key_index]
// Response: [actuation, deadzone_top, deadzone_bottom, velocity_curve,
//            flags, rapidfire_press_sens, rapidfire_release_sens, rapidfire_velocity_mod]
// flags: Bit 0=rapidfire_enabled, Bit 1=use_per_key_velocity_curve
// Total: 8 bytes
void handle_get_per_key_actuation(const uint8_t* data, uint8_t* response) {
    uint8_t layer = data[0];
    uint8_t key_index = data[1];

    if (layer >= 12 || key_index >= 70) {
        response[0] = 0;  // Error - set first byte to 0
        return;
    }

    // Return all 8 fields of the per-key structure
    response[0] = per_key_actuations[layer].keys[key_index].actuation;
    response[1] = per_key_actuations[layer].keys[key_index].deadzone_top;
    response[2] = per_key_actuations[layer].keys[key_index].deadzone_bottom;
    response[3] = per_key_actuations[layer].keys[key_index].velocity_curve;
    response[4] = per_key_actuations[layer].keys[key_index].flags;  // Now using flags field
    response[5] = per_key_actuations[layer].keys[key_index].rapidfire_press_sens;
    response[6] = per_key_actuations[layer].keys[key_index].rapidfire_release_sens;
    response[7] = (uint8_t)per_key_actuations[layer].keys[key_index].rapidfire_velocity_mod;
}

// Set per-key mode flags (GUI preference storage)
// The firmware always uses per-key, but this stores the GUI's preference
// so the UI shows the same state after restart.
// Format: [mode_enabled, per_layer_enabled]
void handle_set_per_key_mode(const uint8_t* data) {
    // Store GUI preference in EEPROM (2 bytes)
    eeprom_update_byte((uint8_t*)PER_KEY_ACTUATION_FLAGS_ADDR, data[0]);
    eeprom_update_byte((uint8_t*)(PER_KEY_ACTUATION_FLAGS_ADDR + 1), data[1]);
}

// Get per-key mode flags (GUI preference)
// Returns stored GUI preference, or defaults (1,1) if never set.
// Response: [mode_enabled, per_layer_enabled]
void handle_get_per_key_mode(uint8_t* response) {
    uint8_t mode_enabled = eeprom_read_byte((uint8_t*)PER_KEY_ACTUATION_FLAGS_ADDR);
    uint8_t per_layer_enabled = eeprom_read_byte((uint8_t*)(PER_KEY_ACTUATION_FLAGS_ADDR + 1));

    // If EEPROM uninitialized (0xFF), default to enabled
    if (mode_enabled == 0xFF) mode_enabled = 0x01;
    if (per_layer_enabled == 0xFF) per_layer_enabled = 0x01;

    response[0] = mode_enabled;
    response[1] = per_layer_enabled;
}

// Reset all per-key actuations to default (HID handler)
void handle_reset_per_key_actuations_hid(void) {
    reset_per_key_actuations();
}

// Copy layer actuations from one layer to another
// Format: [source_layer, dest_layer]
void handle_copy_layer_actuations(const uint8_t* data) {
    uint8_t source = data[0];
    uint8_t dest = data[1];

    if (source >= 12 || dest >= 12) {
        return;  // Invalid parameters
    }

    // Copy all 70 per-key actuation settings from source to dest
    for (uint8_t i = 0; i < 70; i++) {
        per_key_actuations[dest].keys[i] = per_key_actuations[source].keys[i];
    }

    // Update cache directly if destination is the currently cached layer
    if (dest == active_per_key_cache_layer) {
        for (uint8_t i = 0; i < 70; i++) {
            active_per_key_cache[i].actuation = per_key_actuations[dest].keys[i].actuation;
            active_per_key_cache[i].rt_down = per_key_actuations[dest].keys[i].rapidfire_press_sens;
            active_per_key_cache[i].rt_up = per_key_actuations[dest].keys[i].rapidfire_release_sens;
            active_per_key_cache[i].flags = per_key_actuations[dest].keys[i].flags;
        }
    }

    // Save only the destination layer (560 bytes instead of 6.7KB)
    save_layer_per_key_actuations(dest);
}

// =============================================================================
// NULL BIND (SOCD) IMPLEMENTATION
// =============================================================================

// Initialize null bind system to defaults
void nullbind_init(void) {
    for (uint8_t g = 0; g < NULLBIND_NUM_GROUPS; g++) {
        nullbind_groups[g].behavior = NULLBIND_BEHAVIOR_NEUTRAL;
        nullbind_groups[g].key_count = 0;
        nullbind_groups[g].layer = 0;  // Default to layer 0
        for (uint8_t k = 0; k < NULLBIND_MAX_KEYS_PER_GROUP; k++) {
            nullbind_groups[g].keys[k] = 0xFF;  // 0xFF = unused
        }
        for (uint8_t k = 0; k < 7; k++) {
            nullbind_groups[g].reserved[k] = 0;
        }

        // Initialize runtime state
        nullbind_runtime[g].last_pressed_key = 0xFF;
        nullbind_runtime[g].active_key = 0xFF;
        for (uint8_t k = 0; k < NULLBIND_MAX_KEYS_PER_GROUP; k++) {
            nullbind_runtime[g].keys_pressed[k] = false;
            nullbind_runtime[g].press_times[k] = 0;
        }
    }

    // Initialize key travel tracking
    for (uint8_t k = 0; k < 70; k++) {
        nullbind_key_travel[k] = 0;
    }

    nullbind_enabled = true;
}

// Save null bind groups to EEPROM
void nullbind_save_to_eeprom(void) {
    eeprom_update_block(nullbind_groups,
                        (uint8_t*)NULLBIND_EEPROM_ADDR,
                        sizeof(nullbind_groups));

    // Write magic number at end for validation
    eeprom_update_word((uint16_t*)(NULLBIND_EEPROM_ADDR + sizeof(nullbind_groups)),
                       NULLBIND_MAGIC);
}

// Load null bind groups from EEPROM
void nullbind_load_from_eeprom(void) {
    // Check magic number first
    uint16_t magic = eeprom_read_word((uint16_t*)(NULLBIND_EEPROM_ADDR + sizeof(nullbind_groups)));

    if (magic != NULLBIND_MAGIC) {
        // Invalid or uninitialized - use defaults
        nullbind_init();
        nullbind_save_to_eeprom();
        return;
    }

    // Load groups
    eeprom_read_block(nullbind_groups,
                      (uint8_t*)NULLBIND_EEPROM_ADDR,
                      sizeof(nullbind_groups));

    // Initialize runtime state
    for (uint8_t g = 0; g < NULLBIND_NUM_GROUPS; g++) {
        nullbind_runtime[g].last_pressed_key = 0xFF;
        nullbind_runtime[g].active_key = 0xFF;
        for (uint8_t k = 0; k < NULLBIND_MAX_KEYS_PER_GROUP; k++) {
            nullbind_runtime[g].keys_pressed[k] = false;
            nullbind_runtime[g].press_times[k] = 0;
        }
    }
}

// Reset all null bind groups to defaults
void nullbind_reset_all(void) {
    nullbind_init();
    nullbind_save_to_eeprom();
}

// Add a key to a null bind group
bool nullbind_add_key_to_group(uint8_t group_num, uint8_t key_index) {
    if (group_num >= NULLBIND_NUM_GROUPS || key_index >= 70) {
        return false;
    }

    nullbind_group_t* group = &nullbind_groups[group_num];

    // Check if group is full
    if (group->key_count >= NULLBIND_MAX_KEYS_PER_GROUP) {
        return false;
    }

    // Check if key already in group
    for (uint8_t i = 0; i < group->key_count; i++) {
        if (group->keys[i] == key_index) {
            return false;  // Already in group
        }
    }

    // Add key
    group->keys[group->key_count] = key_index;
    group->key_count++;
    return true;
}

// Remove a key from a null bind group
bool nullbind_remove_key_from_group(uint8_t group_num, uint8_t key_index) {
    if (group_num >= NULLBIND_NUM_GROUPS) {
        return false;
    }

    nullbind_group_t* group = &nullbind_groups[group_num];

    // Find the key
    for (uint8_t i = 0; i < group->key_count; i++) {
        if (group->keys[i] == key_index) {
            // Shift remaining keys down
            for (uint8_t j = i; j < group->key_count - 1; j++) {
                group->keys[j] = group->keys[j + 1];
            }
            group->keys[group->key_count - 1] = 0xFF;
            group->key_count--;

            // Adjust behavior if it was priority for removed key
            if (group->behavior >= NULLBIND_BEHAVIOR_PRIORITY_BASE) {
                uint8_t priority_idx = group->behavior - NULLBIND_BEHAVIOR_PRIORITY_BASE;
                if (priority_idx >= group->key_count) {
                    // Priority key was removed or index now invalid - reset to neutral
                    group->behavior = NULLBIND_BEHAVIOR_NEUTRAL;
                }
            }
            return true;
        }
    }
    return false;
}

// Clear all keys from a null bind group
void nullbind_clear_group(uint8_t group_num) {
    if (group_num >= NULLBIND_NUM_GROUPS) {
        return;
    }

    nullbind_group_t* group = &nullbind_groups[group_num];
    group->behavior = NULLBIND_BEHAVIOR_NEUTRAL;
    group->key_count = 0;
    for (uint8_t i = 0; i < NULLBIND_MAX_KEYS_PER_GROUP; i++) {
        group->keys[i] = 0xFF;
    }
}

// Check if a key is in a specific null bind group
bool nullbind_key_in_group(uint8_t group_num, uint8_t key_index) {
    if (group_num >= NULLBIND_NUM_GROUPS) {
        return false;
    }

    nullbind_group_t* group = &nullbind_groups[group_num];
    for (uint8_t i = 0; i < group->key_count; i++) {
        if (group->keys[i] == key_index) {
            return true;
        }
    }
    return false;
}

// Find which null bind group a key belongs to (ignoring layer)
// Returns group number (0-19) or -1 if not in any group
// NOTE: This is the legacy function - use nullbind_find_key_group_for_layer for layer-aware lookup
int8_t nullbind_find_key_group(uint8_t key_index) {
    for (uint8_t g = 0; g < NULLBIND_NUM_GROUPS; g++) {
        if (nullbind_key_in_group(g, key_index)) {
            return (int8_t)g;
        }
    }
    return -1;
}

// Find which null bind group a key belongs to for a specific layer
// Returns group number (0-19) or -1 if not in any group on this layer
int8_t nullbind_find_key_group_for_layer(uint8_t key_index, uint8_t layer) {
    for (uint8_t g = 0; g < NULLBIND_NUM_GROUPS; g++) {
        // Check if group is for this layer
        if (nullbind_groups[g].layer != layer) {
            continue;  // Group is for a different layer
        }
        if (nullbind_key_in_group(g, key_index)) {
            return (int8_t)g;
        }
    }
    return -1;
}

// Get the index of a key within its group (0-7)
// Returns 0xFF if not found
static uint8_t nullbind_get_key_index_in_group(uint8_t group_num, uint8_t key_index) {
    if (group_num >= NULLBIND_NUM_GROUPS) {
        return 0xFF;
    }

    nullbind_group_t* group = &nullbind_groups[group_num];
    for (uint8_t i = 0; i < group->key_count; i++) {
        if (group->keys[i] == key_index) {
            return i;
        }
    }
    return 0xFF;
}

// Count how many keys in a group are currently pressed
static uint8_t nullbind_count_pressed_keys(uint8_t group_num) {
    if (group_num >= NULLBIND_NUM_GROUPS) {
        return 0;
    }

    uint8_t count = 0;
    nullbind_runtime_t* rt = &nullbind_runtime[group_num];
    nullbind_group_t* group = &nullbind_groups[group_num];

    for (uint8_t i = 0; i < group->key_count; i++) {
        if (rt->keys_pressed[i]) {
            count++;
        }
    }
    return count;
}

// Update the active key for a group based on current behavior
void nullbind_update_group_state(uint8_t group_num) {
    if (group_num >= NULLBIND_NUM_GROUPS) {
        return;
    }

    nullbind_group_t* group = &nullbind_groups[group_num];
    nullbind_runtime_t* rt = &nullbind_runtime[group_num];

    if (group->key_count == 0) {
        rt->active_key = 0xFF;
        return;
    }

    uint8_t pressed_count = nullbind_count_pressed_keys(group_num);

    // No keys pressed - no active key
    if (pressed_count == 0) {
        rt->active_key = 0xFF;
        return;
    }

    // Only one key pressed - that key is active (no conflict)
    if (pressed_count == 1) {
        for (uint8_t i = 0; i < group->key_count; i++) {
            if (rt->keys_pressed[i]) {
                rt->active_key = i;
                return;
            }
        }
    }

    // Multiple keys pressed - apply behavior
    uint8_t behavior = group->behavior;

    if (behavior == NULLBIND_BEHAVIOR_NEUTRAL) {
        // All keys nulled
        rt->active_key = 0xFF;
    }
    else if (behavior == NULLBIND_BEHAVIOR_LAST_INPUT) {
        // Last pressed key wins (already tracked in last_pressed_key)
        rt->active_key = rt->last_pressed_key;
    }
    else if (behavior == NULLBIND_BEHAVIOR_DISTANCE) {
        // Key with most travel wins
        uint8_t max_travel = 0;
        uint8_t max_travel_key = 0xFF;

        for (uint8_t i = 0; i < group->key_count; i++) {
            if (rt->keys_pressed[i]) {
                uint8_t key_idx = group->keys[i];
                if (key_idx < 70) {
                    uint8_t travel = nullbind_key_travel[key_idx];
                    if (travel > max_travel) {
                        max_travel = travel;
                        max_travel_key = i;
                    }
                }
            }
        }
        rt->active_key = max_travel_key;
    }
    else if (behavior >= NULLBIND_BEHAVIOR_PRIORITY_BASE) {
        // Absolute priority for specific key
        uint8_t priority_idx = behavior - NULLBIND_BEHAVIOR_PRIORITY_BASE;

        if (priority_idx < group->key_count && rt->keys_pressed[priority_idx]) {
            // Priority key is pressed - it wins
            rt->active_key = priority_idx;
        } else {
            // Priority key not pressed - find first non-priority pressed key
            // (other keys activate when priority key releases)
            for (uint8_t i = 0; i < group->key_count; i++) {
                if (rt->keys_pressed[i] && i != priority_idx) {
                    rt->active_key = i;
                    return;
                }
            }
            rt->active_key = 0xFF;
        }
    }
}

// Called when a key is pressed - updates null bind state
// NOTE: Now layer-aware - only processes groups assigned to the current layer
void nullbind_key_pressed(uint8_t row, uint8_t col, uint8_t travel, uint8_t layer) {
    if (!nullbind_enabled) return;

    uint8_t key_index = row * 14 + col;
    if (key_index >= 70) return;

    // Update travel for distance-based null bind
    nullbind_key_travel[key_index] = travel;

    // Find which group this key belongs to on this specific layer
    int8_t group_num = nullbind_find_key_group_for_layer(key_index, layer);
    if (group_num < 0) return;  // Key not in any null bind group on this layer

    // Get key's index within the group
    uint8_t key_idx_in_group = nullbind_get_key_index_in_group(group_num, key_index);
    if (key_idx_in_group == 0xFF) return;

    nullbind_runtime_t* rt = &nullbind_runtime[group_num];

    // Mark key as pressed
    rt->keys_pressed[key_idx_in_group] = true;
    rt->last_pressed_key = key_idx_in_group;
    rt->press_times[key_idx_in_group] = timer_read32();

    // Update which key should be active
    nullbind_update_group_state(group_num);
}

// Called when a key is released - updates null bind state
// NOTE: Now layer-aware - only processes groups assigned to the current layer
void nullbind_key_released(uint8_t row, uint8_t col, uint8_t layer) {
    if (!nullbind_enabled) return;

    uint8_t key_index = row * 14 + col;
    if (key_index >= 70) return;

    // Clear travel
    nullbind_key_travel[key_index] = 0;

    // Find which group this key belongs to on this specific layer
    int8_t group_num = nullbind_find_key_group_for_layer(key_index, layer);
    if (group_num < 0) return;

    // Get key's index within the group
    uint8_t key_idx_in_group = nullbind_get_key_index_in_group(group_num, key_index);
    if (key_idx_in_group == 0xFF) return;

    nullbind_runtime_t* rt = &nullbind_runtime[group_num];

    // Mark key as released
    rt->keys_pressed[key_idx_in_group] = false;

    // If this was the last pressed key, find new last pressed
    if (rt->last_pressed_key == key_idx_in_group) {
        // Find most recently pressed key still held
        uint32_t latest_time = 0;
        rt->last_pressed_key = 0xFF;

        nullbind_group_t* group = &nullbind_groups[group_num];
        for (uint8_t i = 0; i < group->key_count; i++) {
            if (rt->keys_pressed[i] && rt->press_times[i] > latest_time) {
                latest_time = rt->press_times[i];
                rt->last_pressed_key = i;
            }
        }
    }

    // Update which key should be active
    nullbind_update_group_state(group_num);
}

// Check if a key should be nulled (blocked from registering)
// Returns true if key should be nulled, false if it should register normally
// NOTE: Now layer-aware - only checks groups assigned to the current layer
bool nullbind_should_null_key(uint8_t row, uint8_t col, uint8_t layer) {
    if (!nullbind_enabled) return false;

    uint8_t key_index = row * 14 + col;
    if (key_index >= 70) return false;

    // Find which group this key belongs to on this specific layer
    int8_t group_num = nullbind_find_key_group_for_layer(key_index, layer);
    if (group_num < 0) return false;  // Key not in any null bind group on this layer - don't null

    // Get key's index within the group
    uint8_t key_idx_in_group = nullbind_get_key_index_in_group(group_num, key_index);
    if (key_idx_in_group == 0xFF) return false;

    nullbind_runtime_t* rt = &nullbind_runtime[group_num];

    // If this key is not the active key, null it
    // If active_key is 0xFF (no active key), all keys should be nulled
    if (rt->active_key != key_idx_in_group) {
        return true;  // Null this key
    }

    return false;  // Don't null - this is the active key
}

// =============================================================================
// NULL BIND HID HANDLERS
// =============================================================================

// Get null bind group configuration
// Response: [status, behavior, key_count, keys[8], layer, reserved[7]]
// NOTE: layer field added - groups are now layer-specific
void handle_nullbind_get_group(uint8_t group_num, uint8_t* response) {
    if (group_num >= NULLBIND_NUM_GROUPS) {
        response[0] = 1;  // Error status
        return;
    }

    response[0] = 0;  // Success status

    nullbind_group_t* group = &nullbind_groups[group_num];
    response[1] = group->behavior;
    response[2] = group->key_count;

    // Copy keys
    for (uint8_t i = 0; i < NULLBIND_MAX_KEYS_PER_GROUP; i++) {
        response[3 + i] = group->keys[i];
    }

    // Layer field (byte 11)
    response[11] = group->layer;

    // Copy reserved bytes (7 bytes starting at byte 12)
    for (uint8_t i = 0; i < 7; i++) {
        response[12 + i] = group->reserved[i];
    }
}

// Set null bind group configuration
// Format: [group_num, behavior, key_count, keys[8], layer, reserved[7]]
// NOTE: layer field added - groups are now layer-specific
void handle_nullbind_set_group(const uint8_t* data) {
    uint8_t group_num = data[0];

    if (group_num >= NULLBIND_NUM_GROUPS) {
        return;
    }

    nullbind_group_t* group = &nullbind_groups[group_num];

    group->behavior = data[1];
    group->key_count = data[2];
    if (group->key_count > NULLBIND_MAX_KEYS_PER_GROUP) {
        group->key_count = NULLBIND_MAX_KEYS_PER_GROUP;
    }

    // Copy keys
    for (uint8_t i = 0; i < NULLBIND_MAX_KEYS_PER_GROUP; i++) {
        group->keys[i] = data[3 + i];
    }

    // Layer field (byte 11)
    group->layer = data[11];
    if (group->layer >= 12) {
        group->layer = 0;  // Default to layer 0 if invalid
    }

    // Copy reserved bytes (7 bytes starting at byte 12)
    for (uint8_t i = 0; i < 7; i++) {
        group->reserved[i] = data[12 + i];
    }

    // Reset runtime state for this group
    nullbind_runtime_t* rt = &nullbind_runtime[group_num];
    rt->last_pressed_key = 0xFF;
    rt->active_key = 0xFF;
    for (uint8_t i = 0; i < NULLBIND_MAX_KEYS_PER_GROUP; i++) {
        rt->keys_pressed[i] = false;
        rt->press_times[i] = 0;
    }
}

// Save all groups to EEPROM (wrapper for HID handler)
void handle_nullbind_save_eeprom(void) {
    nullbind_save_to_eeprom();
}

// Load all groups from EEPROM (wrapper for HID handler)
void handle_nullbind_load_eeprom(void) {
    nullbind_load_from_eeprom();
}

// Reset all groups (wrapper for HID handler)
void handle_nullbind_reset_all(void) {
    nullbind_reset_all();
}

// =============================================================================
// TOGGLE KEYS IMPLEMENTATION
// =============================================================================

// Initialize toggle system
void toggle_init(void) {
    memset(toggle_slots, 0, sizeof(toggle_slots));
    memset(toggle_runtime, 0, sizeof(toggle_runtime));
    toggle_enabled = true;
}

// Save toggle slots to EEPROM
void toggle_save_to_eeprom(void) {
    // Write magic number first
    uint16_t magic = TOGGLE_MAGIC;
    eeprom_update_word((uint16_t*)(TOGGLE_EEPROM_ADDR), magic);

    // Write slot data
    uint32_t addr = TOGGLE_EEPROM_ADDR + 2;
    for (uint8_t i = 0; i < TOGGLE_NUM_SLOTS; i++) {
        eeprom_update_word((uint16_t*)addr, toggle_slots[i].target_keycode);
        addr += 2;
        // Reserved bytes (2 bytes)
        eeprom_update_byte((uint8_t*)addr, toggle_slots[i].reserved[0]);
        addr++;
        eeprom_update_byte((uint8_t*)addr, toggle_slots[i].reserved[1]);
        addr++;
    }
}

// Load toggle slots from EEPROM
void toggle_load_from_eeprom(void) {
    // Check magic number
    uint16_t magic = eeprom_read_word((uint16_t*)(TOGGLE_EEPROM_ADDR));
    if (magic != TOGGLE_MAGIC) {
        // Not initialized, reset to defaults
        toggle_init();
        return;
    }

    // Read slot data
    uint32_t addr = TOGGLE_EEPROM_ADDR + 2;
    for (uint8_t i = 0; i < TOGGLE_NUM_SLOTS; i++) {
        toggle_slots[i].target_keycode = eeprom_read_word((uint16_t*)addr);
        addr += 2;
        // Reserved bytes (2 bytes)
        toggle_slots[i].reserved[0] = eeprom_read_byte((uint8_t*)addr);
        addr++;
        toggle_slots[i].reserved[1] = eeprom_read_byte((uint8_t*)addr);
        addr++;
    }

    // Reset runtime state
    memset(toggle_runtime, 0, sizeof(toggle_runtime));
}

// Reset all toggle slots to defaults
void toggle_reset_all(void) {
    toggle_init();
}

// Process a toggle key press
void toggle_process_key(uint16_t keycode, bool pressed) {
    if (!toggle_enabled) return;
    if (!is_toggle_keycode(keycode)) return;

    // Only process on key press, not release
    if (!pressed) return;

    uint8_t slot_num = toggle_keycode_to_slot(keycode);
    if (slot_num >= TOGGLE_NUM_SLOTS) return;

    toggle_slot_t* slot = &toggle_slots[slot_num];
    toggle_runtime_t* runtime = &toggle_runtime[slot_num];

    // Skip if no target keycode configured
    if (slot->target_keycode == 0) return;

    // Toggle the state
    // Use vial_keycode_down/up for extended keycode support (MIDI, macros, etc.)
    if (runtime->is_held) {
        // Release the target keycode
        vial_keycode_up(slot->target_keycode);
        runtime->is_held = false;
    } else {
        // Press and hold the target keycode
        vial_keycode_down(slot->target_keycode);
        runtime->is_held = true;
    }
}

// Release all held toggle keys (call on layer change, etc.)
void toggle_release_all(void) {
    for (uint8_t i = 0; i < TOGGLE_NUM_SLOTS; i++) {
        if (toggle_runtime[i].is_held && toggle_slots[i].target_keycode != 0) {
            vial_keycode_up(toggle_slots[i].target_keycode);
            toggle_runtime[i].is_held = false;
        }
    }
}

// HID handler: Get toggle slot configuration
void handle_toggle_get_slot(uint8_t slot_num, uint8_t* response) {
    // Response format: [status, target_keycode_low, target_keycode_high, reserved[2]]
    if (slot_num >= TOGGLE_NUM_SLOTS) {
        response[0] = 1;  // Error
        return;
    }

    response[0] = 0;  // Success
    toggle_slot_t* slot = &toggle_slots[slot_num];
    response[1] = slot->target_keycode & 0xFF;
    response[2] = (slot->target_keycode >> 8) & 0xFF;
    response[3] = slot->reserved[0];
    response[4] = slot->reserved[1];
}

// HID handler: Set toggle slot configuration
void handle_toggle_set_slot(const uint8_t* data) {
    // Data format: [slot_num, target_keycode_low, target_keycode_high, reserved[2]]
    uint8_t slot_num = data[0];
    if (slot_num >= TOGGLE_NUM_SLOTS) return;

    toggle_slot_t* slot = &toggle_slots[slot_num];
    slot->target_keycode = data[1] | (data[2] << 8);
    slot->reserved[0] = data[3];
    slot->reserved[1] = data[4];

    // If target keycode changed and the slot was held, release it
    if (toggle_runtime[slot_num].is_held) {
        unregister_code16(toggle_slots[slot_num].target_keycode);
        toggle_runtime[slot_num].is_held = false;
    }
}

// HID handler: Save toggle slots to EEPROM
void handle_toggle_save_eeprom(void) {
    toggle_save_to_eeprom();
}

// HID handler: Load toggle slots from EEPROM
void handle_toggle_load_eeprom(void) {
    toggle_load_from_eeprom();
}

// HID handler: Reset all toggle slots
void handle_toggle_reset_all(void) {
    toggle_reset_all();
    toggle_save_to_eeprom();  // Persist the reset to EEPROM
}

// =============================================================================
// EEPROM DIAGNOSTIC SYSTEM IMPLEMENTATION
// =============================================================================

eeprom_diag_t eeprom_diag = {0};
bool eeprom_diag_display_mode = false;
static uint32_t eeprom_diag_timer = 0;

void eeprom_diag_run_test(void) {
    // Read values from test addresses
    eeprom_diag.read_val[0] = eeprom_read_byte((uint8_t*)EEPROM_DIAG_ADDR_1);
    eeprom_diag.read_val[1] = eeprom_read_byte((uint8_t*)EEPROM_DIAG_ADDR_2);
    eeprom_diag.read_val[2] = eeprom_read_byte((uint8_t*)EEPROM_DIAG_ADDR_3);
    eeprom_diag.read_val[3] = eeprom_read_byte((uint8_t*)EEPROM_DIAG_ADDR_4);
    eeprom_diag.read_val[4] = eeprom_read_byte((uint8_t*)EEPROM_DIAG_ADDR_5);

    // Read raw bytes from toggle EEPROM area
    for (int i = 0; i < 8; i++) {
        eeprom_diag.toggle_raw[i] = eeprom_read_byte((uint8_t*)(TOGGLE_EEPROM_ADDR + i));
    }

    // Read null bind group 1 (18 bytes at NULLBIND_EEPROM_ADDR + 18)
    for (int i = 0; i < 18; i++) {
        eeprom_diag.nullbind_g1[i] = eeprom_read_byte((uint8_t*)(NULLBIND_EEPROM_ADDR + 18 + i));
    }

    // Read tap dance 37 using the dynamic_keymap function
    vial_tap_dance_entry_t td37;
    if (dynamic_keymap_get_tap_dance(37, &td37) == 0) {
        // Copy raw bytes from the tap dance entry (10 bytes)
        uint8_t *td_bytes = (uint8_t*)&td37;
        for (int i = 0; i < 10; i++) {
            eeprom_diag.tapdance_37[i] = td_bytes[i];
        }
    } else {
        // Error reading - fill with 0xFF
        for (int i = 0; i < 10; i++) {
            eeprom_diag.tapdance_37[i] = 0xFF;
        }
    }

    eeprom_diag.test_complete = true;
    eeprom_diag_display_mode = true;
    eeprom_diag_timer = timer_read32();
}

void eeprom_diag_display_oled(void) {
    char buf[64];

    // Refresh every 2 seconds
    if (timer_elapsed32(eeprom_diag_timer) > 2000) {
        eeprom_diag_run_test();
    }

    oled_clear();

    // Line 0: Title
    oled_set_cursor(0, 0);
    oled_write_P(PSTR("NB G1 + TD37 DBG"), false);

    // Line 1-2: Null bind group 1 (first 8 bytes: behavior, key_count, keys[0-5])
    // Format: [behavior, key_count, keys[8], layer, reserved[7]]
    oled_set_cursor(0, 1);
    snprintf(buf, 22, "NB1:%02X %02X k:%02X%02X",
        eeprom_diag.nullbind_g1[0],  // behavior
        eeprom_diag.nullbind_g1[1],  // key_count
        eeprom_diag.nullbind_g1[2],  // keys[0]
        eeprom_diag.nullbind_g1[3]); // keys[1]
    oled_write(buf, false);

    // Line 2: More null bind keys
    oled_set_cursor(0, 2);
    snprintf(buf, 22, "k:%02X%02X%02X%02X L:%02X",
        eeprom_diag.nullbind_g1[4],  // keys[2]
        eeprom_diag.nullbind_g1[5],  // keys[3]
        eeprom_diag.nullbind_g1[6],  // keys[4]
        eeprom_diag.nullbind_g1[7],  // keys[5]
        eeprom_diag.nullbind_g1[10]); // layer
    oled_write(buf, false);

    // Line 3-4: Tap dance 37 (10 bytes = 5 uint16 keycodes)
    // Format: [on_tap(2), on_hold(2), on_double_tap(2), on_tap_hold(2), tapping_term(2)]
    uint16_t td_tap = eeprom_diag.tapdance_37[0] | (eeprom_diag.tapdance_37[1] << 8);
    uint16_t td_hold = eeprom_diag.tapdance_37[2] | (eeprom_diag.tapdance_37[3] << 8);
    uint16_t td_dtap = eeprom_diag.tapdance_37[4] | (eeprom_diag.tapdance_37[5] << 8);

    oled_set_cursor(0, 3);
    snprintf(buf, 22, "TD37 T:%04X H:%04X", td_tap, td_hold);
    oled_write(buf, false);

    uint16_t td_thold = eeprom_diag.tapdance_37[6] | (eeprom_diag.tapdance_37[7] << 8);
    uint16_t td_term = eeprom_diag.tapdance_37[8] | (eeprom_diag.tapdance_37[9] << 8);

    oled_set_cursor(0, 4);
    snprintf(buf, 22, "DT:%04X TH:%04X", td_dtap, td_thold);
    oled_write(buf, false);

    oled_set_cursor(0, 5);
    snprintf(buf, 22, "Term:%04X", td_term);
    oled_write(buf, false);

    // Line 6-7: Raw bytes for reference
    oled_set_cursor(0, 6);
    snprintf(buf, 22, "NB:%02X%02X%02X%02X%02X%02X",
        eeprom_diag.nullbind_g1[0], eeprom_diag.nullbind_g1[1],
        eeprom_diag.nullbind_g1[2], eeprom_diag.nullbind_g1[3],
        eeprom_diag.nullbind_g1[4], eeprom_diag.nullbind_g1[5]);
    oled_write(buf, false);

    oled_set_cursor(0, 7);
    snprintf(buf, 22, "TD:%02X%02X%02X%02X%02X%02X",
        eeprom_diag.tapdance_37[0], eeprom_diag.tapdance_37[1],
        eeprom_diag.tapdance_37[2], eeprom_diag.tapdance_37[3],
        eeprom_diag.tapdance_37[4], eeprom_diag.tapdance_37[5]);
    oled_write(buf, false);
}

void handle_eeprom_diag_run(uint8_t* response) {
    eeprom_diag_run_test();
    response[0] = 0;  // Success
}

void handle_eeprom_diag_get(uint8_t* response) {
    response[0] = eeprom_diag.test_complete ? 0 : 1;  // 0 = complete, 1 = not ready
    response[1] = eeprom_diag.match[0] ? 1 : 0;
    response[2] = eeprom_diag.match[1] ? 1 : 0;
    response[3] = eeprom_diag.match[2] ? 1 : 0;
    response[4] = eeprom_diag.match[3] ? 1 : 0;
    response[5] = eeprom_diag.match[4] ? 1 : 0;
    // Raw toggle bytes
    for (int i = 0; i < 8; i++) {
        response[6 + i] = eeprom_diag.toggle_raw[i];
    }
}

// =============================================================================
// END EEPROM DIAGNOSTIC SYSTEM
// =============================================================================

void set_and_save_custom_slot_background_mode(uint8_t slot, uint8_t value) {
    set_custom_slot_background_mode(slot, value); 
}

void set_and_save_custom_slot_pulse_mode(uint8_t slot, uint8_t value) {
    set_custom_slot_pulse_mode(slot, value);
    
}

void set_and_save_custom_slot_color_type(uint8_t slot, uint8_t value) {
    set_custom_slot_color_type(slot, value);
}

void set_and_save_custom_slot_enabled(uint8_t slot, bool value) {
    set_custom_slot_enabled(slot, value);
}

void set_and_save_custom_slot_background_brightness(uint8_t slot, uint8_t value) {
    set_custom_slot_background_brightness(slot, value);
}

void set_custom_slot_live_speed(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value <= 255) {  // 0-255 range for speed
        custom_slots[slot].live_speed = value;
    }
}

void set_custom_slot_macro_speed(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value <= 255) {  // 0-255 range for speed
        custom_slots[slot].macro_speed = value;
    }
}

// =============================================================================
// NEW SPEED PARAMETER SETTING WITH EEPROM SAVE
// =============================================================================

void set_and_save_custom_slot_live_speed(uint8_t slot, uint8_t value) {
    set_custom_slot_live_speed(slot, value);
}

void set_and_save_custom_slot_macro_speed(uint8_t slot, uint8_t value) {
    set_custom_slot_macro_speed(slot, value);
}

// =============================================================================
// BATCH PARAMETER SETTING (for HID interface)
// =============================================================================

void set_custom_slot_parameters_from_bytes(uint8_t slot, uint8_t* data) {
    if (slot >= NUM_CUSTOM_SLOTS) return;
    
    // Byte layout: [live_pos, macro_pos, live_anim, macro_anim, influence, bg_mode, pulse_mode, color_type, enabled, background_brightness, live_speed, macro_speed]
    set_custom_slot_live_positioning(slot, data[0]);
    set_custom_slot_macro_positioning(slot, data[1]);
    set_custom_slot_live_animation(slot, data[2]);
    set_custom_slot_macro_animation(slot, data[3]);
    set_custom_slot_use_influence(slot, data[4] != 0);
    set_custom_slot_background_mode(slot, data[5]);
    set_custom_slot_pulse_mode(slot, data[6]);
    set_custom_slot_color_type(slot, data[7]);
    set_custom_slot_enabled(slot, data[8] != 0);
    set_custom_slot_background_brightness(slot, data[9]);
    set_custom_slot_live_speed(slot, data[10]);      // NEW parameter
    set_custom_slot_macro_speed(slot, data[11]);     // NEW parameter
    
    save_custom_slot_to_eeprom(slot);
}


void get_custom_slot_parameters_as_bytes(uint8_t slot, uint8_t* data) {
    if (slot >= NUM_CUSTOM_SLOTS) return;
    
    custom_animation_config_t* config = &custom_slots[slot];
    
    data[0] = (uint8_t)config->live_positioning;
    data[1] = (uint8_t)config->macro_positioning;
    data[2] = (uint8_t)config->live_animation;
    data[3] = (uint8_t)config->macro_animation;
    data[4] = config->use_influence ? 1 : 0;
    data[5] = (uint8_t)config->background_mode;
    data[6] = config->pulse_mode;
    data[7] = config->color_type;
    data[8] = config->enabled ? 1 : 0;
    data[9] = config->background_brightness;
    data[10] = config->live_speed;      // NEW parameter
    data[11] = config->macro_speed;     // NEW parameter
}

// New function to get current RAM state (not EEPROM)
void get_custom_slot_ram_stuff(uint8_t slot, uint8_t* data) {
    data[0] = custom_slots[slot].live_positioning;
    data[1] = custom_slots[slot].macro_positioning; 
    data[2] = custom_slots[slot].live_animation;
    data[3] = custom_slots[slot].macro_animation;
    data[4] = custom_slots[slot].use_influence ? 1 : 0;
    data[5] = custom_slots[slot].background_mode;
    data[6] = custom_slots[slot].pulse_mode;
    data[7] = custom_slots[slot].color_type;
    data[8] = custom_slots[slot].enabled ? 1 : 0;
    data[9] = custom_slots[slot].background_brightness;
    data[10] = custom_slots[slot].live_speed;
    data[11] = custom_slots[slot].macro_speed;
}

// NEW function to read parameters from EEPROM using existing infrastructure
void get_custom_slot_parameters_from_eeprom(uint8_t slot, uint8_t* data) {
    if (slot >= NUM_CUSTOM_SLOTS) {
        // Set safe defaults if invalid slot
        memset(data, 0, 12);
        data[1] = MACRO_POS_ZONE;  // Safe default
        data[7] = 1;               // Safe color type
        data[8] = 1;               // Enabled
        data[9] = 30;              // 30% background brightness
        data[10] = 128;            // Default live speed
        data[11] = 128;            // Default macro speed
        return;
    }
    
    custom_animation_config_t temp_slot;
    eeprom_read_block(&temp_slot, 
                     (uint8_t*)(EECONFIG_CUSTOM_ANIMATIONS + (slot * sizeof(custom_animation_config_t))), 
                     sizeof(custom_animation_config_t));
    
    
    // Extract validated parameters
    data[0] = temp_slot.live_positioning;
    data[1] = temp_slot.macro_positioning;
    data[2] = temp_slot.live_animation;
    data[3] = temp_slot.macro_animation;
    data[4] = temp_slot.use_influence ? 1 : 0;
    data[5] = temp_slot.background_mode;
    data[6] = temp_slot.pulse_mode;
    data[7] = temp_slot.color_type;
    data[8] = temp_slot.enabled ? 1 : 0;
    data[9] = temp_slot.background_brightness;
    data[10] = temp_slot.live_speed;
    data[11] = temp_slot.macro_speed;
}

// =============================================================================
// INITIALIZATION FUNCTION
// =============================================================================

// Add these functions to your lighting file
bool is_custom_animations_eeprom_initialized(void) {
    uint16_t magic = eeprom_read_word((uint16_t*)RGB_DEFAULTS_MAGIC_ADDR);
    return (magic == RGB_DEFAULTS_MAGIC_NUMBER);
}

void set_custom_animations_eeprom_initialized(void) {
    eeprom_update_word((uint16_t*)RGB_DEFAULTS_MAGIC_ADDR, RGB_DEFAULTS_MAGIC_NUMBER);
}

// Update your existing init function
void init_custom_animations(void) {
    if (!is_custom_animations_eeprom_initialized()) {
        // First time startup - save compiled defaults to EEPROM
        save_custom_animations_to_eeprom();
        set_custom_animations_eeprom_initialized();
		reset_keyboard_settings();
		save_keyboard_settings();
		save_keyboard_settings_to_slot(1);
		save_keyboard_settings_to_slot(2);
		save_keyboard_settings_to_slot(3);
		save_keyboard_settings_to_slot(4);		
    }
    
    // Load from EEPROM (either the defaults we just saved, or existing data)
    load_custom_animations_from_eeprom();
}

// =============================================================================
// CURVE SYSTEM IMPLEMENTATION (For Gaming & Velocity Curves)
// =============================================================================

#include <math.h>

// Global user curves
user_curves_t user_curves;

// Factory curve presets (7 curves, 4 points each)
// Points are stored as [x, y] where x and y are 0-255
// All 4 points are on the curve, connected by straight line segments (piecewise linear)
// Point 0 x is always 0, Point 3 x is always 255
const uint8_t FACTORY_CURVES[7][4][2] PROGMEM = {
    // 0: Softest - very gentle, output much lower than input
    {{0, 0}, {85, 28}, {170, 85}, {255, 255}},

    // 1: Soft - gentle curve, gradual response
    {{0, 0}, {85, 42}, {170, 128}, {255, 255}},

    // 2: Linear - straight 1:1 mapping
    {{0, 0}, {85, 85}, {170, 170}, {255, 255}},

    // 3: Hard - steeper curve, faster response
    {{0, 0}, {85, 128}, {170, 213}, {255, 255}},

    // 4: Hardest - very steep, aggressive response
    {{0, 0}, {64, 160}, {128, 230}, {255, 255}},

    // 5: Aggro - rapid acceleration
    {{0, 0}, {42, 170}, {85, 220}, {255, 255}},

    // 6: Digital - binary-like instant response
    {{0, 0}, {10, 255}, {20, 255}, {255, 255}}
};

const char* FACTORY_CURVE_NAMES[7] PROGMEM = {
    "Softest", "Soft", "Linear", "Hard", "Hardest", "Aggro", "Digital"
};

// Apply curve using piecewise linear interpolation through 4 points
// input: 0-255 input value
// curve_index: 0-6 = factory, 7-16 = user curves
// returns: 0-255 output value
uint8_t apply_curve(uint8_t input, uint8_t curve_index) {
    uint8_t points[4][2];

    // Load curve points
    if (curve_index <= CURVE_FACTORY_DIGITAL) {
        // Factory curve - read from PROGMEM
        memcpy_P(points, FACTORY_CURVES[curve_index], 8);
    } else if (curve_index >= CURVE_USER_START && curve_index <= CURVE_USER_END) {
        // User curve - read from RAM
        uint8_t user_idx = curve_index - CURVE_USER_START;
        if (user_idx < 10) {
            memcpy(points, user_curves.curves[user_idx].points, 8);
        } else {
            // Invalid index - use linear
            return input;
        }
    } else {
        // Invalid index - use linear (1:1)
        return input;
    }

    // Piecewise linear interpolation through all 4 points
    // Find which segment the input falls into and interpolate
    for (int i = 0; i < 3; i++) {
        uint8_t x0 = points[i][0];
        uint8_t x1 = points[i + 1][0];
        uint8_t y0 = points[i][1];
        uint8_t y1 = points[i + 1][1];

        if (input <= x1 || i == 2) {
            // Found the segment - linearly interpolate
            if (x1 == x0) {
                // Avoid division by zero - return start point y
                return y0;
            }
            // Linear interpolation: y = y0 + (y1 - y0) * (input - x0) / (x1 - x0)
            int16_t dy = (int16_t)y1 - (int16_t)y0;
            int16_t dx = (int16_t)x1 - (int16_t)x0;
            int16_t offset = (int16_t)input - (int16_t)x0;
            int16_t result = (int16_t)y0 + (dy * offset) / dx;

            // Clamp to 0-255
            if (result < 0) result = 0;
            if (result > 255) result = 255;

            return (uint8_t)result;
        }
    }

    // Fallback (shouldn't reach here)
    return input;
}

// Initialize user curves with defaults (all linear)
void user_curves_init(void) {
    memset(&user_curves, 0, sizeof(user_curves_t));

    for (int i = 0; i < 10; i++) {
        // Set default name
        snprintf(user_curves.curves[i].name, 16, "User %d", i + 1);

        // Set to linear curve (0,0), (85,85), (170,170), (255,255)
        user_curves.curves[i].points[0][0] = 0;   user_curves.curves[i].points[0][1] = 0;
        user_curves.curves[i].points[1][0] = 85;  user_curves.curves[i].points[1][1] = 85;
        user_curves.curves[i].points[2][0] = 170; user_curves.curves[i].points[2][1] = 170;
        user_curves.curves[i].points[3][0] = 255; user_curves.curves[i].points[3][1] = 255;
    }

    user_curves.magic = USER_CURVES_MAGIC;
}

// Save user curves to EEPROM
void user_curves_save(void) {
    user_curves.magic = USER_CURVES_MAGIC;
    eeprom_update_block(&user_curves, (void*)USER_CURVES_EEPROM_ADDR, sizeof(user_curves_t));
}

// Load user curves from EEPROM
void user_curves_load(void) {
    eeprom_read_block(&user_curves, (void*)USER_CURVES_EEPROM_ADDR, sizeof(user_curves_t));

    if (user_curves.magic != USER_CURVES_MAGIC) {
        // First time or corrupted - initialize with defaults
        user_curves_init();
        user_curves_save();
    }
}

// Reset user curves to defaults
void user_curves_reset(void) {
    user_curves_init();
    user_curves_save();
}

// Migrate old velocity curve value (0-4) to new index (0-16)
// New curve order: Softest(0), Soft(1), Linear(2), Hard(3), Hardest(4), Aggro(5), Digital(6)
uint8_t migrate_velocity_curve(uint8_t old_value) {
    switch(old_value) {
        case 0: return CURVE_FACTORY_SOFTEST;  // Softest → Softest
        case 1: return CURVE_FACTORY_SOFT;     // Soft → Soft
        case 2: return CURVE_FACTORY_LINEAR;   // Medium → Linear (default)
        case 3: return CURVE_FACTORY_HARD;     // Hard → Hard
        case 4: return CURVE_FACTORY_HARDEST;  // Hardest → Hardest
        default: return CURVE_FACTORY_LINEAR;  // Default to Linear
    }
}

// =============================================================================
// GAMING / JOYSTICK SYSTEM IMPLEMENTATION
// =============================================================================

#ifdef JOYSTICK_ENABLE
#include "joystick.h"

// Global gaming state
bool gaming_mode_active = false;
gaming_settings_t gaming_settings;

// Reset gaming settings to defaults
void gaming_reset_settings(void) {
    gaming_settings.gaming_mode_enabled = false;

    // Default analog calibration for LS/RS/Triggers: 1.0mm min, 2.0mm max
    gaming_settings.ls_config.min_travel_mm_x10 = 10;      // 1.0mm
    gaming_settings.ls_config.max_travel_mm_x10 = 20;      // 2.0mm
    gaming_settings.rs_config.min_travel_mm_x10 = 10;      // 1.0mm
    gaming_settings.rs_config.max_travel_mm_x10 = 20;      // 2.0mm
    gaming_settings.trigger_config.min_travel_mm_x10 = 10; // 1.0mm
    gaming_settings.trigger_config.max_travel_mm_x10 = 20; // 2.0mm

    // Disable all mappings by default
    gaming_settings.ls_up.enabled = 0;
    gaming_settings.ls_down.enabled = 0;
    gaming_settings.ls_left.enabled = 0;
    gaming_settings.ls_right.enabled = 0;

    gaming_settings.rs_up.enabled = 0;
    gaming_settings.rs_down.enabled = 0;
    gaming_settings.rs_left.enabled = 0;
    gaming_settings.rs_right.enabled = 0;

    gaming_settings.lt.enabled = 0;
    gaming_settings.rt.enabled = 0;

    for (uint8_t i = 0; i < 16; i++) {
        gaming_settings.buttons[i].enabled = 0;
    }

    // Initialize new curve and gamepad response settings
    gaming_settings.analog_curve_index = CURVE_FACTORY_LINEAR;  // Default to linear
    gaming_settings.angle_adjustment_enabled = false;
    gaming_settings.diagonal_angle = 0;  // 0 degrees (no adjustment)
    gaming_settings.use_square_output = false;
    gaming_settings.snappy_joystick_enabled = false;

    gaming_settings.magic = GAMING_SETTINGS_MAGIC;
}

// Save gaming settings to EEPROM
void gaming_save_settings(void) {
    eeprom_update_block(&gaming_settings, (void*)GAMING_SETTINGS_EEPROM_ADDR, sizeof(gaming_settings_t));
}

// Load gaming settings from EEPROM
void gaming_load_settings(void) {
    eeprom_read_block(&gaming_settings, (void*)GAMING_SETTINGS_EEPROM_ADDR, sizeof(gaming_settings_t));

    // Check magic number - if invalid, reset to defaults
    if (gaming_settings.magic != GAMING_SETTINGS_MAGIC) {
        gaming_reset_settings();
        gaming_save_settings();
    }

    // Update runtime state
    gaming_mode_active = gaming_settings.gaming_mode_enabled;
}

// Initialize gaming system
void gaming_init(void) {
    gaming_load_settings();
}

// =============================================================================
// GAMEPAD RESPONSE TRANSFORMATION FUNCTIONS
// =============================================================================

// Apply diagonal angle adjustment
// Rotates the input vector by the specified angle (in degrees)
void apply_angle_adjustment(int16_t* x, int16_t* y, uint8_t angle_deg) {
    if (angle_deg == 0) return;  // No adjustment needed

    // Convert angle to radians
    float angle_rad = (float)angle_deg * 3.14159265f / 180.0f;
    float cos_a = cosf(angle_rad);
    float sin_a = sinf(angle_rad);

    // Normalize to -1.0 to 1.0 range for rotation
    float fx = (float)(*x) / 32767.0f;
    float fy = (float)(*y) / 32767.0f;

    // Apply rotation matrix
    float rotated_x = fx * cos_a - fy * sin_a;
    float rotated_y = fx * sin_a + fy * cos_a;

    // Convert back to int16_t range
    *x = (int16_t)(rotated_x * 32767.0f);
    *y = (int16_t)(rotated_y * 32767.0f);
}

// Apply square output transformation
// Scales circular joystick input to square output (allows 100% on both axes simultaneously)
void apply_square_output(int16_t* x, int16_t* y) {
    // Normalize to -1.0 to 1.0 range
    float fx = (float)(*x) / 32767.0f;
    float fy = (float)(*y) / 32767.0f;

    // Find the maximum absolute value of either axis
    float max_axis = fmaxf(fabsf(fx), fabsf(fy));

    if (max_axis > 0.01f) {  // Avoid division by zero
        // Scale both axes so the maximum reaches 1.0
        float scale = 1.0f / max_axis;
        fx *= scale;
        fy *= scale;
    }

    // Convert back to int16_t range
    *x = (int16_t)(fx * 32767.0f);
    *y = (int16_t)(fy * 32767.0f);
}

// Apply snappy joystick transformation
// When opposing directions are pressed, use the maximum value instead of combining
void apply_snappy_joystick(int16_t* axis_val, int16_t pos, int16_t neg) {
    // If both positive and negative inputs are active
    if (pos > 0 && neg > 0) {
        // Use whichever is greater
        if (pos > neg) {
            *axis_val = pos;   // Positive direction wins
        } else {
            *axis_val = -neg;  // Negative direction wins
        }
    }
}

// Convert analog travel to joystick axis value (-32767 to +32767)
// row, col: Matrix position
// invert: true to invert direction (for down/right axes)
// config: Which calibration config to use (ls_config or rs_config)
int16_t gaming_analog_to_axis(uint8_t row, uint8_t col, bool invert, gaming_analog_config_t* config) {
    // Get normalized travel (0-255)
    uint8_t travel_norm = analog_matrix_get_travel_normalized(row, col);

    // Convert mm*10 to travel units (0-255 maps to 0-4.0mm, so 255/40 per 0.1mm)
    uint8_t min_threshold = (config->min_travel_mm_x10 * 255) / 40;
    uint8_t max_threshold = (config->max_travel_mm_x10 * 255) / 40;

    // Below minimum threshold = no input
    if (travel_norm < min_threshold) return 0;

    // Above maximum threshold = full deflection (apply curve to 255)
    if (travel_norm > max_threshold) {
        uint8_t curved_max = apply_curve(255, gaming_settings.analog_curve_index);
        int16_t axis_value = ((int32_t)curved_max * 32767) / 255;
        return invert ? -axis_value : axis_value;
    }

    // Normalize travel to 0-255 range within min/max thresholds
    uint32_t range = max_threshold - min_threshold;
    if (range == 0) return 0;  // Avoid division by zero

    uint8_t normalized_travel = ((uint32_t)(travel_norm - min_threshold) * 255) / range;

    // Apply analog curve (0-255 input -> 0-255 output)
    uint8_t curved_travel = apply_curve(normalized_travel, gaming_settings.analog_curve_index);

    // Convert curved travel to axis value (-32767 to +32767)
    int16_t value = ((int32_t)curved_travel * 32767) / 255;

    return invert ? -value : value;
}

// Convert analog travel to trigger value (0 to +32767)
// Returns true if key is pressed enough to register, false otherwise
bool gaming_analog_to_trigger(uint8_t row, uint8_t col, int16_t* value) {
    uint8_t travel_norm = analog_matrix_get_travel_normalized(row, col);

    // Use trigger-specific config
    uint8_t min_threshold = (gaming_settings.trigger_config.min_travel_mm_x10 * 255) / 40;
    uint8_t max_threshold = (gaming_settings.trigger_config.max_travel_mm_x10 * 255) / 40;

    if (travel_norm < min_threshold) {
        *value = 0;
        return false;
    }

    if (travel_norm > max_threshold) {
        // Apply curve to maximum value
        uint8_t curved_max = apply_curve(255, gaming_settings.analog_curve_index);
        *value = ((int32_t)curved_max * 32767) / 255;
        return true;
    }

    uint32_t range = max_threshold - min_threshold;
    if (range == 0) {
        *value = 0;
        return false;
    }

    // Normalize travel to 0-255 range within min/max thresholds
    uint8_t normalized_travel = ((uint32_t)(travel_norm - min_threshold) * 255) / range;

    // Apply analog curve (0-255 input -> 0-255 output)
    uint8_t curved_travel = apply_curve(normalized_travel, gaming_settings.analog_curve_index);

    // Convert curved travel to trigger value (0 to +32767)
    *value = ((int32_t)curved_travel * 32767) / 255;
    return true;
}

// Update joystick state based on current key states
void gaming_update_joystick(void) {
    if (!gaming_mode_active) return;

    // Left stick X axis (left/right) - use LS config
    int16_t ls_x_pos = 0, ls_x_neg = 0;
    if (gaming_settings.ls_right.enabled) {
        ls_x_pos = gaming_analog_to_axis(gaming_settings.ls_right.row, gaming_settings.ls_right.col, false, &gaming_settings.ls_config);
    }
    if (gaming_settings.ls_left.enabled) {
        int16_t left_val = gaming_analog_to_axis(gaming_settings.ls_left.row, gaming_settings.ls_left.col, true, &gaming_settings.ls_config);
        ls_x_neg = -left_val;  // Store as positive for snappy joystick
    }

    int16_t ls_x = ls_x_pos + (ls_x_neg > 0 ? -ls_x_neg : 0);

    // Apply snappy joystick to left stick X if enabled
    if (gaming_settings.snappy_joystick_enabled) {
        apply_snappy_joystick(&ls_x, ls_x_pos, ls_x_neg);
    }

    // Left stick Y axis (up/down) - use LS config
    int16_t ls_y_pos = 0, ls_y_neg = 0;
    if (gaming_settings.ls_down.enabled) {
        ls_y_pos = gaming_analog_to_axis(gaming_settings.ls_down.row, gaming_settings.ls_down.col, false, &gaming_settings.ls_config);
    }
    if (gaming_settings.ls_up.enabled) {
        int16_t up_val = gaming_analog_to_axis(gaming_settings.ls_up.row, gaming_settings.ls_up.col, true, &gaming_settings.ls_config);
        ls_y_neg = -up_val;  // Store as positive for snappy joystick
    }

    int16_t ls_y = ls_y_pos + (ls_y_neg > 0 ? -ls_y_neg : 0);

    // Apply snappy joystick to left stick Y if enabled
    if (gaming_settings.snappy_joystick_enabled) {
        apply_snappy_joystick(&ls_y, ls_y_pos, ls_y_neg);
    }

    // Apply gamepad response transformations to left stick
    if (gaming_settings.angle_adjustment_enabled) {
        apply_angle_adjustment(&ls_x, &ls_y, gaming_settings.diagonal_angle);
    }
    if (gaming_settings.use_square_output) {
        apply_square_output(&ls_x, &ls_y);
    }

    joystick_set_axis(0, ls_x);  // Axis 0 = Left Stick X
    joystick_set_axis(1, ls_y);  // Axis 1 = Left Stick Y

    // Right stick X axis (left/right) - use RS config
    int16_t rs_x_pos = 0, rs_x_neg = 0;
    if (gaming_settings.rs_right.enabled) {
        rs_x_pos = gaming_analog_to_axis(gaming_settings.rs_right.row, gaming_settings.rs_right.col, false, &gaming_settings.rs_config);
    }
    if (gaming_settings.rs_left.enabled) {
        int16_t left_val = gaming_analog_to_axis(gaming_settings.rs_left.row, gaming_settings.rs_left.col, true, &gaming_settings.rs_config);
        rs_x_neg = -left_val;  // Store as positive for snappy joystick
    }

    int16_t rs_x = rs_x_pos + (rs_x_neg > 0 ? -rs_x_neg : 0);

    // Apply snappy joystick to right stick X if enabled
    if (gaming_settings.snappy_joystick_enabled) {
        apply_snappy_joystick(&rs_x, rs_x_pos, rs_x_neg);
    }

    // Right stick Y axis (up/down) - use RS config
    int16_t rs_y_pos = 0, rs_y_neg = 0;
    if (gaming_settings.rs_down.enabled) {
        rs_y_pos = gaming_analog_to_axis(gaming_settings.rs_down.row, gaming_settings.rs_down.col, false, &gaming_settings.rs_config);
    }
    if (gaming_settings.rs_up.enabled) {
        int16_t up_val = gaming_analog_to_axis(gaming_settings.rs_up.row, gaming_settings.rs_up.col, true, &gaming_settings.rs_config);
        rs_y_neg = -up_val;  // Store as positive for snappy joystick
    }

    int16_t rs_y = rs_y_pos + (rs_y_neg > 0 ? -rs_y_neg : 0);

    // Apply snappy joystick to right stick Y if enabled
    if (gaming_settings.snappy_joystick_enabled) {
        apply_snappy_joystick(&rs_y, rs_y_pos, rs_y_neg);
    }

    // Apply gamepad response transformations to right stick
    if (gaming_settings.angle_adjustment_enabled) {
        apply_angle_adjustment(&rs_x, &rs_y, gaming_settings.diagonal_angle);
    }
    if (gaming_settings.use_square_output) {
        apply_square_output(&rs_x, &rs_y);
    }

    joystick_set_axis(2, rs_x);  // Axis 2 = Right Stick X
    joystick_set_axis(3, rs_y);  // Axis 3 = Right Stick Y

    // Left trigger
    int16_t lt_val = 0;
    if (gaming_settings.lt.enabled) {
        gaming_analog_to_trigger(gaming_settings.lt.row, gaming_settings.lt.col, &lt_val);
    }
    joystick_set_axis(4, lt_val);  // Axis 4 = Left Trigger

    // Right trigger
    int16_t rt_val = 0;
    if (gaming_settings.rt.enabled) {
        gaming_analog_to_trigger(gaming_settings.rt.row, gaming_settings.rt.col, &rt_val);
    }
    joystick_set_axis(5, rt_val);  // Axis 5 = Right Trigger

    // Buttons (simple on/off based on key press state)
    for (uint8_t i = 0; i < 16; i++) {
        if (gaming_settings.buttons[i].enabled) {
            bool pressed = analog_matrix_get_key_state(
                gaming_settings.buttons[i].row,
                gaming_settings.buttons[i].col
            );

            if (pressed) {
                register_joystick_button(i);
            } else {
                unregister_joystick_button(i);
            }
        }
    }
}

#endif // JOYSTICK_ENABLE

// =============================================================================
// END GAMING / JOYSTICK SYSTEM
// =============================================================================

void keyboard_post_init_user(void) {
	// Enable analog (HE) velocity mode - this keyboard has analog hall-effect sensors
	// Without this, process_midi.c bypasses get_he_velocity_from_position() entirely
	// and always uses the fixed velocity_number slider value
	analog_mode = 1;

	scan_keycode_categories();
	scan_current_layer_midi_leds();
	load_keyboard_settings();
	dynamic_macro_init();
	init_custom_animations();
	load_layer_actuations();  // Load HE velocity settings from EEPROM

	// EEPROM loading disabled - 6.7KB read during init causes keyboard hang
	// (OLED gibberish, slow RGB, no keystrokes)
	// Instead: initialize to defaults, granular saves still work for persistence
	initialize_per_key_actuations();

	// Load per-key cache for layer 0 from defaults
	// This populates the 280-byte fast cache used during scan loop
	force_load_per_key_cache_at_init(0);

	// TODO: Implement deferred EEPROM loading during idle time
	// For now, changes are saved per-key (8 bytes) but not restored on boot

	// Load user curves from EEPROM
	user_curves_load();

	dwt_init();

#ifdef JOYSTICK_ENABLE
	gaming_init();  // Load gaming/joystick settings from EEPROM
#endif

	// Initialize arpeggiator system
	arp_init();

	// Initialize null bind (SOCD) system
	nullbind_load_from_eeprom();

	// Initialize toggle keys system
	toggle_load_from_eeprom();

	// Initialize encoder click buttons and footswitch pins
	setPinInputHigh(B14);  // Encoder 0 click (directly polled GPIO)
	setPinInputHigh(B15);  // Encoder 1 click (directly polled GPIO)
	setPinInputHigh(A9);   // Footswitch / Sustain pedal (directly polled GPIO)

#ifdef MIDI_SERIAL_ENABLE
	// Initialize MIDI serial - using USART1 on PA15 (TX) and PB3 (RX)
	// Pin configuration is handled by QMK's uart_init() via SD1_TX_PIN/SD1_RX_PIN defines in config.h
	// PA15/PB3 are JTAG pins remapped to USART1 AF7
	setup_serial_midi();
#endif
}

   
led_config_t g_led_config = {
  // Key Matrix to LED Index
  {
    // Row 0
    { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 },
    // Row 1
    { 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27 },
    // Row 2
    { 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41 },
    // Row 3
    { 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 },
    // Row 4
    { 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69 },
    // Row 5 (virtual: encoder clicks + sustain pedal - no physical LEDs)
    { NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED, NO_LED }
  },
  // LED Index to Physical Position
  {
    // LED positions, equally spaced
    // Row 0
    { 0, 0 }, { 16, 0 }, { 32, 0 }, { 48, 0 }, { 64, 0 }, { 80, 0 }, { 96, 0 }, { 112, 0 }, { 128, 0 }, { 144, 0 }, { 160, 0 }, { 176, 0 }, { 192, 0 }, { 208, 0 },
    // Row 1
    { 0, 16 }, { 16, 16 }, { 32, 16 }, { 48, 16 }, { 64, 16 }, { 80, 16 }, { 96, 16 }, { 112, 16 }, { 128, 16 }, { 144, 16 }, { 160, 16 }, { 176, 16 }, { 192, 16 }, { 208, 16 },
    // Row 2
    { 0, 32 }, { 16, 32 }, { 32, 32 }, { 48, 32 }, { 64, 32 }, { 80, 32 }, { 96, 32 }, { 112, 32 }, { 128, 32 }, { 144, 32 }, { 160, 32 }, { 176, 32 }, { 192, 32 }, { 208, 32 },
    // Row 3
    { 0, 48 }, { 16, 48 }, { 32, 48 }, { 48, 48 }, { 64, 48 }, { 80, 48 }, { 96, 48 }, { 112, 48 }, { 128, 48 }, { 144, 48 }, { 160, 48 }, { 176, 48 }, { 192, 48 }, { 208, 48 },
    // Row 4
    { 0, 64 }, { 16, 64 }, { 32, 64 }, { 48, 64 }, { 64, 64 }, { 80, 64 }, { 96, 64 }, { 112, 64 }, { 128, 64 }, { 144, 64 }, { 160, 64 }, { 176, 64 }, { 192, 64 }, { 208, 64 }
  },
  // LED Index to Flag
  {
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4
  }
};


const char* getRootName(void) {
	if (rootnote == 0) {
		return "B";  // Return NULL to indicate individual note calculation
	}
		else if (rootnote == 1) {
	return "C";  
	}
		else if (rootnote == 2) {
	return "C#";  
	}
		else if (rootnote == 3) {
	return "D";  
	}
		else if (rootnote == 4) {
	return "Eb";  
	}
		else if (rootnote == 5) {
	return "E";  
	}
		else if (rootnote == 6) {
	return "F";  
	}
		else if (rootnote == 7) {
	return "F#";  
	}
		else if (rootnote == 8) {
	return "G";  
	}
		else if (rootnote == 9) {
	return "Ab";  
	}
		else if (rootnote == 10) {
	return "A";  
	}
		else if (rootnote == 11) {
	return "Bb";  
	}
		else if (rootnote == 12) {
	return "B";  
	}
		else { 
	return "";
		}
}

const char* getBassName(void) {
	if (bassnote == 0) {
		return "/B";  // Return NULL to indicate individual note calculatio
	}
		else if (bassnote == 1) {
	return "/C";  
	}
		else if (bassnote == 2) {
	return "/C#";  
	}
		else if (bassnote == 3) {
	return "/D";  
	}
		else if (bassnote == 4) {
	return "/Eb";  
	}
		else if (bassnote == 5) {
	return "/E";  
	}
		else if (bassnote == 6) {
	return "/F";  
	}
		else if (bassnote == 7) {
	return "/F#";  
	}
		else if (bassnote == 8) {
	return "/G";  
	}
		else if (bassnote == 9) {
	return "/Ab";  
	}
		else if (bassnote == 10) {
	return "/A";  
	}
		else if (bassnote == 11) {
	return "/Bb";  
	}
		else if (bassnote == 12) {
	return "/B";  
	}
		else { 
	return "";
		}
}

// Basic type definitions
typedef struct {
    uint16_t interval_mask;  
    const char* name;
} OptimizedChord;

typedef struct {
    uint16_t interval_mask;   
    uint8_t shiftnumber;     
    const char* name;
} OptimizedInversionChord;

typedef struct {
    uint16_t interval_mask;
    const char* name1;
    const char* name2;
    uint8_t target_interval;
    uint8_t shiftnumber;  // Added shiftnumber field
} OptimizedIntervalChord;

typedef struct {
    uint16_t interval_mask;
    const char* name;
} OptimizedScale;

typedef struct {
    int8_t interval;
    const char* name;
} IntervalDefinition;

// Helper function prototypes
uint16_t intervals_to_bitmask(const uint8_t intervals[6]);
bool intervals_match_optimized(uint16_t pattern, uint16_t expected);
bool intervals_match_with_inversion(uint16_t pattern, uint16_t expected, uint8_t shift);
int8_t get_signed_interval(uint8_t note1, uint8_t note2);
const char* binary_search_interval(int8_t interval);
bool has_interval_between_keys_optimized(uint8_t target);
uint16_t get_inversion_mask(const uint8_t intervals[6], uint8_t shift);

// Interval definitions
static const IntervalDefinition INTERVALS[] = {
    {-23, "Major Fourteenth"},
    {-22, "Minor Fourteenth"},
    {-21, "Major Thirteenth"},
    {-20, "Minor Thirteenth"},
    {-19, "Perfect Twelfth"},
    {-18, "Augmented Eleventh"},
    {-17, "Perfect Eleventh"},
    {-16, "Major Tenth"},
    {-15, "Minor Tenth"},
    {-14, "Major Ninth"},
    {-13, "Minor Ninth"},
	{-12, "Octave"},
    {-11, "Major Seventh"},
    {-10, "Minor Seventh"},
    {-9, "Major Sixth"},
    {-8, "Minor Sixth"},
    {-7, "Perfect Fifth"},
    {-6, "Tritone"},
    {-5, "Perfect Fourth"},
    {-4, "Major Third"},
    {-3, "Minor Third"},
    {-2, "Major Second"},
    {-1, "Minor Second"},
    {1, "Minor Second"},
    {2, "Major Second"},
    {3, "Minor Third"},
    {4, "Major Third"},
    {5, "Perfect Fourth"},
    {6, "Tritone"},
    {7, "Perfect Fifth"},
    {8, "Minor Sixth"},
    {9, "Major Sixth"},
    {10, "Minor Seventh"},
    {11, "Major Seventh"},
	{12, "Octave"},
    {13, "Minor Ninth"},
    {14, "Major Ninth"},
    {15, "Minor Tenth"},
    {16, "Major Tenth"},
    {17, "Perfect Eleventh"},
    {18, "Augmented Eleventh"},
    {19, "Perfect Twelfth"},
    {20, "Minor Thirteenth"},
    {21, "Major Thirteenth"},
    {22, "Minor Fourteenth"},
    {23, "Major Fourteenth"},
    {0, NULL}  // Terminator
};

// Optimized chord definitions
static const OptimizedChord OPTIMIZED_CHORDS[] = {
{0b000000000000, "     "},          // Empty chord -> 0b000000000000

{0b000100100000, ""},            // (5,8)
{0b000100010000, "m"},     
{0b000010010000, "dim"},  
{0b001000100000, "aug"},            // (5,9)
{0b000010100000, "b5"},            // (5,7)
{0b000100001000, "sus2"},           // (3,8)
{0b000101000000, "sus4"},           // (6,8)
{0b010100010000, "m6"},             // (4,8,10)
{0b010100100000, "6"},              // (5,8,10)

{0b000110100000, "(addb5)"}, 

{0b100100100000, "7"}, 
{0b1000100100000, "Maj7"}, 
{0b100100010000, "m7"}, 
{0b1000100010000, "minMaj7"}, 
{0b100010010000, "m7b5"}, 
{0b010010010000, "dim7"}, 
{0b100101000000, "7sus4"}, 
{0b1000101000000, "maj7sus4"}, 

{0b101000100000, "7#5"}, 
{0b100010100000, "7b5"}, 
{0b100100100100, "7b9"}, 
{0b100100110000, "7#9"}, 
{0b1001000100000, "maj7#5"}, 
{0b1000010100000, "maj7b5"}, 

{0b100100101000, "9"}, 
{0b100100011000, "m9"}, 
{0b1000100101000, "Maj9"}, 

{0b100000101000, "9no5"}, 
{0b100000011000, "m9no5"}, 
{0b1000000101000, "Maj9no5"}, 

{0b010100101000, "6/9"}, 
{0b010100011000, "m6/9"}, 

{0b100101101000, "11"},
{0b100101011000, "m11"}, 
{0b1000101101000, "Maj11"},

{0b100101100000, "7(11)"},
{0b100101010000, "m7(11)"},
{0b1000101100000, "maj7(11)"},

{0b110101100000, "7(11)(13)"}, 
{0b110101010000, "m7(11)(13)"}, 
{0b1010101100000, "maj7(11)(13)"}, 

{0b110100100000, "7(13)"}, 
{0b110100010000, "m7(13)"}, 
{0b1010100100000, "Maj7(13)"}, 

{0b110100101000, "9(13)"}, 
{0b110100011000, "m9(13)"},
{0b1010100101000, "maj9(13)"},

{0b110101101000, "13"}, 
{0b110101011000, "m13"}, 
{0b1010101101000, "Maj13"},                                                                                                                                                                                                                      

{0b100100000000, "7no3"}, 
{0b1000100000000, "maj7no3"}, 
{0b100000100000, "7no5"}, 
{0b100000010000, "m7no5"},
{0b1000000100000, "maj7no5"}, 
//{0b100010000000, "7b5no3"}, 
//{0b101000000000, "7#5no3"}, 


{0b100101100100, "7b9(11)"}, 
{0b100101001000, "9sus4"}, 
{0b1000101001000, "maj9sus4"}, 
{0b100100001000, "7sus2"}, 
{0b100010100100, "7b5b9"}, 
{0b100010110000, "7b5#9"}, 
{0b110100100100, "7b9(13)"}, 
{0b100010101000, "9b5"}, 
{0b100010011000, "m9b5"}, 
{0b101000101000, "9#5"}, 
{0b110100110000, "7#9(13)"}, 
{0b111000100100, "7#5b9"}, 
{0b111000110000, "7#5#9"}, 
{0b100110101000, "9#11"}, 
{0b100110011000, "m9#11"},
{0b100011100000, "7b5(11)"}, 
{0b1000101010000, "minMaj7(11)"}, 
{0b1000110100000, "Maj7(#11)"}, 
{0b100110100000, "7(#11)"},

    {0, NULL}  // Terminator
};

// Optimized inversion chord definitions
static const OptimizedInversionChord OPTIMIZED_INVERSIONS[] = {
	
// Major - 4,9	shiftnumber=4
{0b001000010000, 4, ""},
// Major - 10,6	shiftnumber=7
{0b010001000000, 7, ""},

// Minor - 5,10	shiftnumber=3
{0b010000100000, 3, "m"},
// Minor - 9,6	shiftnumber=7
{0b001001000000, 7, "m"},

// Dim - 4,10	shiftnumber=3
{0b010000010000, 3, "dim"},
// Dim - 10,7	shiftnumber=6
{0b010010000000, 6, "dim"},

// b5 - 3,9	shiftnumber=3
{0b001000001000, 4, "b5"},
// b5 - 11,7	shiftnumber=6
{0b100010000000, 6, "b5"},

// Sus4 - 3,8	shiftnumber=5
{0b000100001000, 5, "sus4"},
// Sus4 - 11,6	shiftnumber=7
{0b100001000000, 7, "sus4"},

// 7no3 {4,6} shiftnumber=7
{0b000001010000, 7, "7no3"},
// 7no3 {10,3} shiftnumber=10
{0b010000001000, 10, "7no3"},

// maj7no3 {5,6} shiftnumber=7
{0b000001100000, 7, "maj7no3"},
// maj7no3 {9,2} shiftnumber=11
{0b001000000100, 11, "maj7no3"},

// maj7no5 {8,9} shiftnumber=7
{0b001100000000, 4, "maj7no5"},
// maj7no5 {6,2} shiftnumber=11
{0b000001000100, 11, "maj7no5"},

// 7no5 {7,9} shiftnumber=4
{0b001010000000, 4, "7no5"},
// 7no5 {7,3} shiftnumber=10
{0b000010001000, 10, "7no5"},

// m7no5 {8,10} shiftnumber=3
{0b010100000000, 3, "m7no5"},
// m7no5 {6,3} shiftnumber=10
{0b000001001000, 10, "m7no5"},

// m7no5 {8,10} shiftnumber=3
{0b001010000000, 4, "maj7no5"},
// m7no5 {6,3} shiftnumber=10
{0b000010001000, 10, "maj7no5"},

// 7 {4,7,9} shiftnumber=4
{0b001010010000, 4, "7"},
// 7 {10,4,6} shiftnumber=7
{0b010001010000, 7, "7"},
// 7 {7,10,3} shiftnumber=10
{0b010010001000, 10, "7"},

// maj7 {4,8,9} shiftnumber=4
{0b001100010000, 4, "maj7"},
// maj7 {10,5,6} shiftnumber=7
{0b010001100000, 7, "maj7"},
// maj7 {6,9,2} shiftnumber=11
{0b001001000100, 11, "maj7"},

// minMaj7 {4,8,9} shiftnumber=3
{0b011000100000, 3, "minMaj7"},
// maj7 {10,5,6} shiftnumber=7
{0b001001100000, 7, "minMaj7"},
// maj7 {6,9,2} shiftnumber=11
{0b001000100100, 11, "minMaj7"},

// m7 {5,8,10} shiftnumber=3
{0b010100100000, 3, "m7"},
// m7 {9,4,6} shiftnumber=7
{0b001001010000, 7, "m7"},
// m7 {6,10,3} shiftnumber=10
{0b010001001000, 10, "m7"},

// m7b5 {4,8,10} shiftnumber=3
{0b010100010000, 3, "m7b5"},
// m7b5 {10,5,7} shiftnumber=6
{0b010010100000, 6, "m7b5"},
// m7b5 {6,9,3} shiftnumber=10
{0b001001001000, 10, "m7b5"},

// 7sus4 {3,6,8} shiftnumber=5
{0b000101001000, 5, "7sus4"},
// 7sus4 {11,4,6} shiftnumber=7
{0b100001010000, 7, "7sus4"},
// 7sus4 {8,10,3} shiftnumber=10
{0b010100001000, 10, "7sus4"},

// 7b9 {4,7,9,10} shiftnumber=4
{0b011010010000, 4, "7b9"},
// 7b9 {10,4,6,7} shiftnumber=7
{0b010011010000, 7, "7b9"},
// 7b9 {7,10,3,4} shiftnumber=10
{0b010010011000, 10, "7b9"},
// 7b9 {4,7,10,12} shiftnumber=1
{0b1010010010000, 1, "7b9"},

// 7#9 {4,7,9,12} shiftnumber=4
{0b1001010010000, 4, "7#9"},
// 7#9 {10,4,6,9} shiftnumber=7
{0b011001010000, 7, "7#9"},
// 7#9 {7,10,3,6} shiftnumber=10
{0b010011001000, 10, "7#9"},
// 7#9 {2,5,8,10} shiftnumber=3
{0b010100100010, 3, "7#9"},

// 9 {4,7,9,11} shiftnumber=4
{0b101010010000, 4, "9"},
// 9 {10,4,6,8} shiftnumber=7
{0b010101010000, 7, "9"},
// 9 {7,10,3,5} shiftnumber=10
{0b010010101000, 10, "9"},
// 9 {3,6,9,11} shiftnumber=2
{0b101001001000, 2, "9"},

// 9no5 {4,7,9,11} shiftnumber=4
{0b101010000000, 4, "9no5"},
// 9no5 {10,4,6,8} shiftnumber=7
{0b101000001000, 2, "9no5"},
// 9no5 {7,10,3,5} shiftnumber=10
{0b000010101000, 10, "9no5"},

// Maj9 {4,8,9,11} shiftnumber=4
{0b101100010000, 4, "Maj9"},
// Maj9 {10,5,6,8} shiftnumber=7
{0b010101100000, 7, "Maj9"},
// Maj9 {6,9,2,4} shiftnumber=11
{0b001001010100, 11, "Maj9"},
// Maj9 {3,6,10,11} shiftnumber=2
{0b110001001000, 2, "Maj9"},

// Maj9no5 {4,8,9,11} shiftnumber=4
{0b101100000000, 4, "Maj9no5"},
// Maj9no5 {10,5,6,8} shiftnumber=7
{0b110000001000, 2, "Maj9no5"},
// Maj9no5 {6,9,2,4} shiftnumber=11
{0b000001010100, 11, "Maj9no5"},

// m9no5 {9,4,6,8} shiftnumber=7
{0b1010100000000, 3, "m9no5"},
// m9no5 {6,10,3,5} shiftnumber=10
{0b000001101000, 10, "m9no5"},
// m9no5 {2,6,9,11} shiftnumber=2
{0b101000000100, 2, "m9no5"},

// m9 {9,4,6,8} shiftnumber=7
{0b001101010000, 7, "m9"},
// m9 {6,10,3,5} shiftnumber=10
{0b010001101000, 10, "m9"},
// m9 {2,6,9,11} shiftnumber=2
{0b101001000100, 2, "m9"},

// 7#5 {5,7,9} shiftnumber=4
{0b001010100000, 4, "7#5"},
// 7#5 {9,3,5} shiftnumber=8
{0b001000101000, 8, "7#5"},
// 7#5 {7,11,3} shiftnumber=10
{0b100010001000, 10, "7#5"},

// maj7#5 {5,8,9} shiftnumber=4
{0b001100100000, 4, "maj7#5"},
// maj7#5 {9,4,5} shiftnumber=8
{0b001000110000, 8, "maj7#5"},
// maj7#5 {6,10,2} shiftnumber=10
{0b010001000100, 11, "maj7#5"},

// maj7sus4 {{3, 7, 8, 0, 0, 0},5} shiftnumber=4
{0b000110001000, 5, "maj7sus4"},
// maj7sus4 {{11, 5, 6, 0, 0, 0},7} shiftnumber=8
{0b100001100000, 7, "maj7sus4"},
// maj7sus4 {{7, 9, 2, 0, 0, 0},11} shiftnumber=10
{0b001010000100, 11, "maj7sus4"},

// maj7b5 {3,8,9} shiftnumber=4
{0b001100001000, 4, "maj7b5"},
// maj7b5 {11,6,7} shiftnumber=8
{0b100011000000, 6, "maj7b5"},
// maj7b5 {6,8,2} shiftnumber=10
{0b000101000100, 11, "maj7b5"},

// 7b5 {3,7,9} shiftnumber=4
{0b001010001000, 4, "7b5"},
// 7b5 {11,5,7} shiftnumber=8
{0b100010100000, 6, "7b5"},
// 7b5 {7,9,3} shiftnumber=10
{0b001010001000, 10, "7b5"},

// 6/9 {4,6,9,11} shiftnumber=4
{0b101001010000, 4, "6/9"},
// 6/9 {10,3,6,8} shiftnumber=7
{0b010101001000, 7, "6/9"},
// 6/9 {8,11,4,6} shiftnumber=9
{0b100101010000, 9, "6/9"},
// 6/9 {3,6,8,11} shiftnumber=2
{0b100101001000, 2, "6/9"},

// m6/9 {5,7,10,12} shiftnumber=3
{0b1010010100000, 3, "m6/9"},
// m6/9 {9,3,6,8} shiftnumber=7
{0b001101001000, 7, "m6/9"},
// m6/9 {7,11,4,6} shiftnumber=9
{0b100011010000, 9, "m6/9"},
// m6/9 {2,6,8,11} shiftnumber=2
{0b100101000100, 2, "m6/9"},

// 7(11) {4,7,9,11,2} shiftnumber=4
{0b001010010100, 4, "7(11)"},
// 7(11) {7,10,3,5,8} shiftnumber=10
{0b010110001000, 10, "7(11)"},
// 7(11) {3,6,9,11,4} shiftnumber=2
{0b110001010000, 7, "7(11)"},
// 7(11) {12,3,6,8,10} shiftnumber=5
{0b1000101001000, 5, "7(11)"},

// maj7(11) {4,7,9,11,2} shiftnumber=4
{0b001100010100, 4, "maj7(11)"},
// maj7(11) {7,10,3,5,8} shiftnumber=10
{0b001011000100, 11, "maj7(11)"},
// maj7(11) {3,6,9,11,4} shiftnumber=2
{0b110001100000, 7, "maj7(11)"},
// maj7(11) {12,3,6,8,10} shiftnumber=5
{0b1000110001000, 5, "maj7(11)"},

// 11 {4,7,9,11,2} shiftnumber=4
{0b101010010100, 4, "11"},
// 11 {7,10,3,5,8} shiftnumber=10
{0b010110101000, 10, "11"},
// 11 {3,6,9,11,4} shiftnumber=2
{0b101001011000, 2, "11"},
// 11 {12,3,6,8,10} shiftnumber=5
{0b1010101001000, 5, "11"},

// m11 {5,8,10,12,3} shiftnumber=3
{0b110100101000, 3, "m11"},
// m11 {9,4,6,8,11} shiftnumber=7
{0b101101010000, 7, "m11"},
// m11 {6,10,3,5,8} shiftnumber=10
{0b010101101000, 10, "m11"},
// m11 {2,6,9,11,4} shiftnumber=2
{0b101001010100, 2, "m11"},
// m11 {11,3,6,8,10} shiftnumber=5
{0b110101001000, 5, "m11"},

// maj11 {4,8,9,11,2} shiftnumber=4
{0b101100010100, 4, "maj11"},
// maj11 {10,5,6,8,11} shiftnumber=7
{0b110101100000, 7, "maj11"},
// maj11 {6,9,2,4,7} shiftnumber=11
{0b001011010100, 11, "maj11"},
// maj11 {3,6,10,11,4} shiftnumber=2
{0b110001011000, 2, "maj11"},
// maj11 {12,3,7,8,10} shiftnumber=5
{0b1010110001000, 5, "maj11"},

// 13 {4,7,9,11,2,6} shiftnumber=4
{0b101011010100, 4, "13"},
// 13 {10,4,6,8,11,3} shiftnumber=7
{0b110101011000, 7, "13"},
// 13 {7,10,3,5,8,12} shiftnumber=10
{0b1010110101000, 10, "13"},
// 13 {3,6,9,11,4,8} shiftnumber=2
{0b101101011000, 2, "13"},
// 13 {12,3,6,8,10,5} shiftnumber=5
{0b110101101000, 5, "13"},
// 13 {8,11,2,4,6,9} shiftnumber=9
{0b101101010100, 9, "13"},

// 7(13) {4,7,9,11,2,6} shiftnumber=4
{0b001011010000, 4, "7(13)"},
// 7(13) {10,4,6,8,11,3} shiftnumber=7
{0b010001011000, 7, "7(13)"},
// 7(13) {7,10,3,5,8,12} shiftnumber=10
{0b1010010001000, 10, "7(13)"},
// 7(13) {3,6,9,11,4,8} shiftnumber=2
{0b100100010100, 9, "7(13)"},

// m7(13) {4,7,9,11,2,6} shiftnumber=4
{0b010110100000, 3, "m7(13)"},
// m7(13) {10,4,6,8,11,3} shiftnumber=7
{0b001001011000, 7, "m7(13)"},
// m7(13) {7,10,3,5,8,12} shiftnumber=10
{0b1010001001000, 10, "m7(13)"},
// m7(13) {3,6,9,11,4,8} shiftnumber=2
{0b100010010100, 9, "m7(13)"},

    {0, 0, NULL}  // Terminator
};

// Optimized interval chord definitions
static const OptimizedIntervalChord OPTIMIZED_INTERVAL_CHORDS[] = {
// m(add2)/m(add9) (4,8,2)
{0b000100011000, "m(add2)", "m(add9)", 2, 0},
// m(add2)/m(add9) (5,12,10)
{0b1010000100000, "m(add2)", "m(add9)", 2, 3},
// m(add2)/m(add9) (9,8,6)
{0b001101000000, "m(add2)", "m(add9)", 2, 7},
// m(add2)/m(add9) (2,6,11)
{0b100001000100, "m(add2)", "m(add9)", 2, 2},


// (add2)/(add9) (5,8,2)
// 2,5,8 -> 0b000100101000
{0b000100101000, "(add2)", "(add9)", 2, 0},
// add2/add9 (4,11,9)
{0b101000010000, "(add2)", "(add9)", 2, 4},
// add2/add9 (10,8,6)
{0b010101000000, "(add2)", "(add9)", 2 , 7},
// add2/add9 (3,6,11)
{0b100001001000, "(add2)", "(add9)", 2, 2},


// m(add11)/m(add4) (4,8,6)
// 4,6,8 -> 0b000101010000
{0b000101010000, "m(add11)", "m(add4)", 17, 0},
// m(add4)/m(add11) (4,8,2)
{0b010000101000, "m(add11)", "m(add4)", 17, 3},
// m(add4)/m(add11) (4,8,2)
{0b101001000000, "m(add11)", "m(add4)", 17, 7},
// m(add4)/m(add11) (4,8,2)
{0b100100001000, "m(add11)", "m(add4)", 17, 5},

// (add11)/(add4) (5,8,6)
// 5,6,8 -> 0b000101100000
{0b000101100000, "(add11)", "(add4)", 17, 0},
// add4/add11 (4,8,2)
{0b001000010100, "(add11)", "(add4)", 17, 4},
// add4/add11 (4,8,2)
{0b110001000000, "(add11)", "(add4)", 17, 7},
// add4/add11 (4,8,2)
{0b1000100001000, "(add11)", "(add4)", 17, 5},
    {0, NULL, NULL, 0}  // Terminator
};

// Optimized scale definitions
static const OptimizedScale OPTIMIZED_SCALES[] = {
// Major(Ionian) (2,4,5,7,9,11)
// 2,4,5,7,9,11 -> 0b1010101101000
{0b1010101101000, "Major(Ionian)"},

// Dorian (2,3,5,7,9,10)
// 2,3,5,7,9,10 -> 0b110101011000
{0b110101011000, "Dorian"},

// Phrygian (1,3,5,7,8,10)
// 1,3,5,7,8,10 -> 0b101101010100
{0b101101010100, "Phrygian"},

// Lydian (2,4,6,7,9,11)
// 2,4,6,7,9,11 -> 0b1010110101000
{0b1010110101000, "Lydian"},

// Mixolydian (2,4,5,7,9,10)
// 2,4,5,7,9,10 -> 0b010110110100
{0b010110110100, "Mixolydian"},

// Minor(Aeolian) (2,3,5,7,8,10)
// 2,3,5,7,8,10 -> 0b101101011000
{0b101101011000, "Minor(Aeolian)"},

// Locrian (1,3,5,6,8,10)
// 1,3,5,6,8,10 -> 0b101011010100
{0b101011010100, "Locrian"},

// Melodic Minor (2,3,5,7,9,11)
// 2,3,5,7,9,11 -> 0b1010101011000
{0b1010101011000, "Melodic Minor"},

// Lydian Dominant (2,4,6,7,9,10)
// 2,4,6,7,9,10 -> 0b110110101000
{0b110110101000, "Lydian Dominant"},

// Altered Scale (1,3,4,6,8,10)
// 1,3,4,6,8,10 -> 0b010101011010
{0b101010110100, "Altered Scale"},

// Harmonic Minor (2,3,5,7,8,11)
// 2,3,5,7,8,11 -> 0b100100110100
{0b1001101011000, "Harmonic Minor"},

// Major Pentatonic (2,4,7,9)
// 2,4,7,9 -> 0b010100101000
{0b010100101000, "Major Pentatonic"},

// Minor Pentatonic (3,5,7,10)
// 3,5,7,10 -> 0b100101010000
{0b100101010000, "Minor Pentatonic"},

// Whole Tone (2,4,6,8,10)
// 2,4,6,8,10 -> 0b101010101000
{0b101010101000, "Whole Tone"},

// Diminished (1,3,4,6,7,9)
// 1,3,4,6,7,9 -> 0b010110110100
{0b010110110100, "Diminished"},

// Blues (3,5,6,7,10)
// 3,5,6,7,10 -> 0b100111010000
{0b100111010000, "Blues"},

    {0, NULL}  // Terminator
};

// Helper function implementations
uint16_t intervals_to_bitmask(const uint8_t intervals[6]) {
    uint16_t mask = 0;
    for (int i = 0; i < 6; i++) {
        if (intervals[i] == 0) break;
        mask |= (1 << intervals[i]);
    }
    return mask;
}

bool intervals_match_optimized(uint16_t pattern, uint16_t expected) {
    uint16_t pattern_bits = __builtin_popcount(pattern);
    uint16_t expected_bits = __builtin_popcount(expected);
    
    if (pattern_bits != expected_bits)
        return false;
        
    return (pattern ^ expected) == 0;
}

bool intervals_match_with_inversion(uint16_t pattern, uint16_t expected, uint8_t shift) {
    uint16_t shifted_pattern = ((pattern << shift) | (pattern >> (12 - shift))) & 0xFFF;
    return intervals_match_optimized(shifted_pattern, expected);
}

int8_t get_signed_interval(uint8_t note1, uint8_t note2) {
    int diff = note2 - note1;
    while (diff > 23) diff -= 12;
    while (diff < -23) diff += 12;
    return diff;
}

const char* binary_search_interval(int8_t interval) {
    int left = 0;
    int right = sizeof(INTERVALS) / sizeof(INTERVALS[0]) - 1;
    
    while (left <= right) {
        int mid = left + (right - left) / 2;
        if (INTERVALS[mid].interval == interval)
            return INTERVALS[mid].name;
        if (INTERVALS[mid].interval < interval)
            left = mid + 1;
        else
            right = mid - 1;
    }
    return "     ";
}

bool has_interval_between_keys_optimized(uint8_t target) {
    int held_keys[] = {
        heldkey1 ? trueheldkey1 : 0,
        heldkey2 ? trueheldkey2 : 0,
        heldkey3 ? trueheldkey3 : 0,
        heldkey4 ? trueheldkey4 : 0,
        heldkey5 ? trueheldkey5 : 0,
        heldkey6 ? trueheldkey6 : 0,
        heldkey7 ? trueheldkey7 : 0
    };
    
    // Check all possible pairs
    for(int i = 0; i < 7; i++) {
        if(!held_keys[i]) continue;
        for(int j = i + 1; j < 7; j++) {
            if(!held_keys[j]) continue;
            if(abs(held_keys[i] - held_keys[j]) == target) {
                return true;
            }
        }
    }
    return false;
}

uint16_t get_inversion_mask(const uint8_t intervals[6], uint8_t shift) {
    uint16_t mask = intervals_to_bitmask(intervals);
    if (shift > 0) {
        mask = ((mask << shift) | (mask >> (12 - shift))) & 0xFFF;
    }
    return mask;
}

bool all_intervals_within_scale(uint16_t scale_mask) {
    uint8_t held_keys[] = {
        heldkey1 ? trueheldkey1 : 0,
        heldkey2 ? trueheldkey2 : 0,
        heldkey3 ? trueheldkey3 : 0,
        heldkey4 ? trueheldkey4 : 0,
        heldkey5 ? trueheldkey5 : 0,
        heldkey6 ? trueheldkey6 : 0,
        heldkey7 ? trueheldkey7 : 0
    };
    
    // For each pair of held keys
    for (int i = 0; i < 7; i++) {
        if (!held_keys[i]) continue;
        for (int j = i + 1; j < 7; j++) {
            if (!held_keys[j]) continue;
            
            // Calculate the interval between these keys
            int interval = (held_keys[j] - held_keys[i] + 12) % 12;
            // Check if this interval exists in the scale mask
            if (!(scale_mask & (1 << interval))) {
                return false;
            }
        }
    }
    return true;
}

// Main chord recognition function
const char* getChordName(void) {
    // Handle single note
    if (!heldkey2) {
        rootnote = 13;
        bassnote = 13;
        return "     ";
    }
    
    // Handle two notes
    if (!heldkey3) {
        int8_t signed_interval = get_signed_interval(trueheldkey1, trueheldkey2);
        rootnote = 13;
        bassnote = 13;
        return binary_search_interval(signed_interval);
    }
    
    // Create current intervals bit mask
    uint16_t current_mask = 0;
    if (heldkey2) current_mask |= (1 << heldkey2difference);
    if (heldkey3) current_mask |= (1 << heldkey3difference);
    if (heldkey4) current_mask |= (1 << heldkey4difference);
    if (heldkey5) current_mask |= (1 << heldkey5difference);
    if (heldkey6) current_mask |= (1 << heldkey6difference);
    if (heldkey7) current_mask |= (1 << heldkey7difference);
    
    // Find lowest note
    uint8_t lowest_value = trueheldkey1;
    uint8_t lowest_interval = 0;
    bool root_is_lowest = true;
    
    if (heldkey2 && trueheldkey2 < lowest_value) {
        lowest_value = trueheldkey2;
        lowest_interval = heldkey2difference;
        root_is_lowest = false;
    }
    if (heldkey3 && trueheldkey3 < lowest_value) {
        lowest_value = trueheldkey3;
        lowest_interval = heldkey3difference;
        root_is_lowest = false;
    }
    if (heldkey4 && trueheldkey4 < lowest_value) {
        lowest_value = trueheldkey4;
        lowest_interval = heldkey4difference;
        root_is_lowest = false;
    }
    if (heldkey5 && trueheldkey5 < lowest_value) {
        lowest_value = trueheldkey5;
        lowest_interval = heldkey5difference;
        root_is_lowest = false;
    }
    if (heldkey6 && trueheldkey6 < lowest_value) {
        lowest_value = trueheldkey6;
        lowest_interval = heldkey6difference;
        root_is_lowest = false;
    }
    if (heldkey7 && trueheldkey7 < lowest_value) {
        lowest_value = trueheldkey7;
        lowest_interval = heldkey7difference;
        root_is_lowest = false;
    }

    // Check interval chords
    for (const OptimizedIntervalChord* chord = OPTIMIZED_INTERVAL_CHORDS; chord->name1; chord++) {
         if (intervals_match_optimized(current_mask, chord->interval_mask)) {
            rootnote = (heldkey1 + 12 - chord->shiftnumber) % 12;
            
            if (root_is_lowest) {
                bassnote = (heldkey1 + lowest_interval) % 12;
            } else {
                bassnote = (heldkey1 + (lowest_interval - 1)) % 12;
            }
            if (bassnote == rootnote) {
                bassnote = 13;
            }
            return has_interval_between_keys_optimized(chord->target_interval) ? 
                   chord->name1 : chord->name2;
        }
    }

    // Check scales
    for (const OptimizedScale* scale = OPTIMIZED_SCALES; scale->name; scale++) {
        if (intervals_match_optimized(current_mask, scale->interval_mask)) {
            // Check if all intervals between held keys are within the scale pattern
            if (all_intervals_within_scale(scale->interval_mask)) {
                rootnote = heldkey1;
                bassnote = 13;
                return scale->name;
            }
        }
    }

    // Check basic chords
    for (const OptimizedChord* chord = OPTIMIZED_CHORDS; chord->name; chord++) {
        if (intervals_match_optimized(current_mask, chord->interval_mask)) {
            rootnote = heldkey1;
            if (root_is_lowest || ((heldkey1 + (lowest_interval - 1)) % 12) == heldkey1) {
                bassnote = 13;
            } else {
                bassnote = (heldkey1 + (lowest_interval - 1)) % 12;
            }
            return chord->name;
        }
    }
    
    // Check inversions
    for (const OptimizedInversionChord* inv = OPTIMIZED_INVERSIONS; inv->name; inv++) {
        if (intervals_match_optimized(current_mask, inv->interval_mask)) {
            rootnote = (heldkey1 + 12 - inv->shiftnumber) % 12;
            
            if (root_is_lowest) {
                bassnote = (heldkey1 + lowest_interval) % 12;
            } else {
                bassnote = (heldkey1 + (lowest_interval - 1)) % 12;
            }
            if (bassnote == rootnote) {
                bassnote = 13;
            }
            return inv->name;
        }
    }

    rootnote = 13;
    bassnote = 13;
    return "     ";
}

const char code_to_name[60][25] = {
    "  ", "  ", "  ", "  ", "A", "B", "C", "D", "E", "F",
    "G", "H", "I", "J", "K", "L", "M", "N", "O", "P",
    "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "Enter", "Delete", "Back space", "Tab", "Space", "-", "=", "[", "]", "\\",
    "#", ";", "'", "`", ",", ".", "/", "  ", "  ", "  "};
	
const char* noteNames[] = {"C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"};
	
const char midi_note_names[168][5] = {
	"C-4", "C#-4", "D-4", "Eb-4", "E-4", "F-4", "F#-4", "G-4", "Ab-4", "A-4", "Bb-4", "B-4",
	"C-3", "C#-3", "D-3", "Eb-3", "E-3", "F-3", "F#-3", "G-3", "Ab-3", "A-3", "Bb-3", "B-3",
	"C-2", "C#-2", "D-2", "Eb-2", "E-2", "F-2", "F#-2", "G-2", "Ab-2", "A-2", "Bb-2", "B-2",
	"C-1", "C#-1", "D-1", "Eb-1", "E-1", "F-1", "F#-1", "G-1", "Ab-1", "A-1", "Bb-1", "B-1",
    "C0", "C#0", "D0", "Eb0", "E0", "F0", "F#0", "G0", "Ab0", "A0", "Bb0", "B0",
    "C1", "C#1", "D1", "Eb1", "E1", "F1", "F#1", "G1", "Ab1", "A1", "Bb1", "B1",
    "C2", "C#2", "D2", "Eb2", "E2", "F2", "F#2", "G2", "Ab2", "A2", "Bb2", "B2",
    "C3", "C#3", "D3", "Eb3", "E3", "F3", "F#3", "G3", "Ab3", "A3", "Bb3", "B3",
    "C4", "C#4", "D4", "Eb4", "E4", "F4", "F#4", "G4", "Ab4", "A4", "Bb4", "B4",
    "C5", "C#5", "D5", "Eb5", "E5", "F5", "F#5", "G5", "Ab5", "A5", "Bb5", "B5",
	"C6", "C#6", "D6", "Eb6", "E6", "F6", "F#6", "G6", "Ab6", "A6", "Bb6", "B6",
	"C7", "C#7", "D7", "Eb7", "E7", "F7", "F#7", "G7", "Ab7", "A7", "Bb7", "B7",
	"C8", "C#8", "D8", "Eb8", "E8", "F8", "F#8", "G8", "Ab8", "A8", "Bb8", "B8",
	"C9", "C#9", "D8", "Eb9", "E9", "F9", "F#9", "G9", "Ab9", "A9", "Bb9", "B9"
};

const char chord_note_names[12][5] = {
	"C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"

};

const char majorminor_note_names[96][11] = {
	"G MAJE MIN", "AbMAJFMIN", "A MAJF#MIN", "BbMAJG MIN", "B MAJAbMIN", "C MAJA MIN", "C#MAJBbMIN", "D MAJB MIN", "EbMAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJEbMIN",
	"G MAJE MIN", "AbMAJFMIN", "A MAJF#MIN", "BbMAJG MIN", "B MAJAbMIN", "C MAJA MIN", "C#MAJBbMIN", "D MAJB MIN", "EbMAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJEbMIN",
	"G MAJE MIN", "AbMAJFMIN", "A MAJF#MIN", "BbMAJG MIN", "B MAJAbMIN", "C MAJA MIN", "C#MAJBbMIN", "D MAJB MIN", "EbMAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJEbMIN",
	"G MAJE MIN", "AbMAJFMIN", "A MAJF#MIN", "BbMAJG MIN", "B MAJAbMIN", "C MAJA MIN", "C#MAJBbMIN", "D MAJB MIN", "EbMAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJEbMIN",
	"G MAJE MIN", "AbMAJFMIN", "A MAJF#MIN", "BbMAJG MIN", "B MAJAbMIN", "C MAJA MIN", "C#MAJBbMIN", "D MAJB MIN", "EbMAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJEbMIN",
	"G MAJE MIN", "AbMAJFMIN", "A MAJF#MIN", "BbMAJG MIN", "B MAJAbMIN", "C MAJA MIN", "C#MAJBbMIN", "D MAJB MIN", "EbMAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJEbMIN",
	"G MAJE MIN", "AbMAJFMIN", "A MAJF#MIN", "BbMAJG MIN", "B MAJAbMIN", "C MAJA MIN", "C#MAJBbMIN", "D MAJB MIN", "EbMAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJEbMIN",
	"G MAJE MIN", "AbMAJFMIN", "A MAJF#MIN", "BbMAJG MIN", "B MAJAbMIN", "C MAJA MIN", "C#MAJBbMIN", "D MAJB MIN", "EbMAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJEbMIN",
};

const char inversion_note_names[7][14] = {
	"ROOT POSITION", "1ST INVERSION", "2ND INVERSION", "3RD INVERSION", "4TH INVERSION", "5TH INVERSION", "6TH INVERSION",
};

// Replace both individual functions with this merged one:
uint8_t get_special_key_led_index(uint8_t category) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    
    // Search through the categorized LEDs for the specified category
    for (int i = 0; i < led_categories[current_layer].count; i++) {
        if (led_categories[current_layer].leds[i].category == category) {
            return led_categories[current_layer].leds[i].led_index;
        }
    }
    
    return 99;  // Not found
}

void update_bpm_flash(void) {   
    if (current_bpm == 0) {
        bpm_flash_state = false;
        bpm_beat_count = 0;
        return;
    }
    
    // For automatic BPM, only flash when loops are actually playing
    if (bpm_source_macro != 0) {
        bool any_loops_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (is_macro_effectively_playing(i)) {
                any_loops_playing = true;
                break;
            }
        }
        
        if (!any_loops_playing) {
            bpm_flash_state = false;
            bpm_beat_count = 0;
            return;
        }
    }
        
    uint32_t current_time = timer_read32();
    
    // High precision beat interval: (60,000 ms/minute * 100000) / (BPM * 100000) = 6000000000 / BPM
    uint32_t beat_interval = (6000000000ULL) / current_bpm;  // Time between beats in ms
    uint32_t flash_on_time = 100;    // Fixed 100ms flash duration
    uint32_t elapsed_time = current_time - last_bpm_flash_time;
    
    if (elapsed_time >= beat_interval) {
        // New beat - start flash and reset timer
        bpm_flash_state = true;
        last_bpm_flash_time = current_time;
        
        bpm_beat_count = (bpm_beat_count + 1) % 4;  // Cycle through 0-3
    } else if (elapsed_time >= flash_on_time) {
        // Flash duration exceeded - turn off LED
        bpm_flash_state = false;
    }
}

void reset_bpm_timing_for_loop_start(void) {
    if (current_bpm != 0 && bpm_source_macro != 0) {
        // Reset to beat 1 and start timing from now
        last_bpm_flash_time = timer_read32();
        bpm_beat_count = 1;
        bpm_flash_state = true;  // Start with flash on for beat 1
        dprintf("bpm: reset timing for loop start (automatic BPM)\n");
    }
}

// Calculate median of buffer (outlier-resistant)
static uint32_t calculate_median_interval(void) {
    uint32_t sorted[EXT_CLOCK_BUFFER_SIZE];
    uint8_t count = 0;
    
    // Copy valid intervals to temp array
    for (uint8_t i = 0; i < EXT_CLOCK_BUFFER_SIZE; i++) {
        if (ext_clock.interval_buffer_us[i] > 0) {
            sorted[count++] = ext_clock.interval_buffer_us[i];
        }
    }
    
    if (count == 0) return 0;
    if (count == 1) return sorted[0];
    
    // Simple bubble sort (fine for small arrays)
    for (uint8_t i = 0; i < count - 1; i++) {
        for (uint8_t j = 0; j < count - i - 1; j++) {
            if (sorted[j] > sorted[j + 1]) {
                uint32_t temp = sorted[j];
                sorted[j] = sorted[j + 1];
                sorted[j + 1] = temp;
            }
        }
    }
    
    // Return median
    if (count % 2 == 0) {
        return (sorted[count/2 - 1] + sorted[count/2]) / 2;
    } else {
        return sorted[count/2];
    }
}

// Calculate average excluding outliers
static uint32_t calculate_filtered_average(void) {
    if (ext_clock.interval_buffer_us[EXT_CLOCK_BUFFER_SIZE - 1] == 0) {
        // Buffer not full yet, just use simple average
        uint32_t total = 0;
        uint8_t count = 0;
        
        for (uint8_t i = 0; i < EXT_CLOCK_BUFFER_SIZE; i++) {
            if (ext_clock.interval_buffer_us[i] > 0) {
                total += ext_clock.interval_buffer_us[i];
                count++;
            }
        }
        
        return (count > 0) ? (total / count) : 0;
    }
    
    // Buffer is full - use median-based outlier rejection
    uint32_t median = calculate_median_interval();
    
    // Calculate average and standard deviation for outlier detection
    uint32_t sum = 0;
    uint32_t sum_sq = 0;
    uint8_t count = 0;
    
    for (uint8_t i = 0; i < EXT_CLOCK_BUFFER_SIZE; i++) {
        if (ext_clock.interval_buffer_us[i] > 0) {
            sum += ext_clock.interval_buffer_us[i];
            sum_sq += (ext_clock.interval_buffer_us[i] / 100) * (ext_clock.interval_buffer_us[i] / 100);
            count++;
        }
    }
    
    if (count < 3) return median;
    
    uint32_t mean = sum / count;
    uint32_t variance = (sum_sq / count) - ((mean / 100) * (mean / 100));
    uint32_t std_dev = 1;
    
    // Simple integer square root for std deviation
    if (variance > 0) {
        uint32_t x = variance;
        uint32_t y = (x + 1) / 2;
        while (y < x) {
            x = y;
            y = (x + variance / x) / 2;
        }
        std_dev = x;
    }
    
    // Reject outliers beyond 2 standard deviations
    sum = 0;
    count = 0;
    uint32_t outlier_threshold = std_dev * 200;  // 2 std dev (scaled by 100)
    
    for (uint8_t i = 0; i < EXT_CLOCK_BUFFER_SIZE; i++) {
        if (ext_clock.interval_buffer_us[i] > 0) {
            int32_t diff = (int32_t)ext_clock.interval_buffer_us[i] - (int32_t)mean;
            if (diff < 0) diff = -diff;
            
            // Include if within 2 standard deviations
            if (diff < (int32_t)outlier_threshold) {
                sum += ext_clock.interval_buffer_us[i];
                count++;
            }
        }
    }
    
    return (count > 0) ? (sum / count) : median;
}

// Apply exponential moving average to BPM
static uint32_t apply_bpm_smoothing(uint32_t new_bpm) {
    if (ext_clock.smoothed_bpm == 0) {
        // First reading
        ext_clock.smoothed_bpm = new_bpm;
        return new_bpm;
    }
    
    // Exponential moving average: smoothed = (smoothed * (N-1) + new) / N
    // Using BPM_SMOOTH_FACTOR for smoothing strength
    uint64_t smoothed = ((uint64_t)ext_clock.smoothed_bpm * (BPM_SMOOTH_FACTOR - 1) + new_bpm) / BPM_SMOOTH_FACTOR;
    ext_clock.smoothed_bpm = (uint32_t)smoothed;
    
    return ext_clock.smoothed_bpm;
}

// ============================================================================
// EXTERNAL CLOCK RECEPTION HANDLERS (UPDATED)
// ============================================================================

void handle_external_clock_pulse(void) {
    // Mark that we're receiving external clock
    if (clock_mode != CLOCK_MODE_EXTERNAL) {
        clock_mode = CLOCK_MODE_EXTERNAL;
        ext_clock.smoothed_bpm = 0;  // Reset smoothing
        ext_clock.bpm_locked = false;
        dprintf("Switched to EXTERNAL clock mode\n");
    }
    
    if (!ext_clock.running) return;
    
    uint32_t current_cycles = dwt_get_cycles();
    ext_clock.last_pulse_cycles = current_cycles;
    
    // Calculate interval if we have a previous timestamp
    if (ext_clock.last_cycle_count > 0) {
        uint32_t cycle_interval;
        
        // Handle 32-bit overflow
        if (current_cycles >= ext_clock.last_cycle_count) {
            cycle_interval = current_cycles - ext_clock.last_cycle_count;
        } else {
            // Overflow occurred
            cycle_interval = (0xFFFFFFFF - ext_clock.last_cycle_count) + current_cycles + 1;
        }
        
        // Convert to microseconds (48MHz = 48 cycles per microsecond)
        uint32_t interval_us = cycles_to_us(cycle_interval);
        
        // Sanity check: MIDI clock at 30-300 BPM gives intervals of 8.3ms - 83.3ms
        // 24 pulses per beat: at 300 BPM = 120 pulses/sec = 8333us per pulse
        //                     at 30 BPM  = 12 pulses/sec  = 83333us per pulse
        if (interval_us > 5000 && interval_us < 100000) {  // 5ms to 100ms
            // Store in ring buffer
            ext_clock.interval_buffer_us[ext_clock.buffer_index] = interval_us;
            ext_clock.buffer_index = (ext_clock.buffer_index + 1) % EXT_CLOCK_BUFFER_SIZE;
            
            // Wait for buffer to have enough samples before calculating
            uint8_t valid_count = 0;
            for (uint8_t i = 0; i < EXT_CLOCK_BUFFER_SIZE; i++) {
                if (ext_clock.interval_buffer_us[i] > 0) {
                    valid_count++;
                }
            }
            
            if (valid_count >= 8) {  // Need at least half buffer full
                ext_clock.synced = true;
                
                // Calculate filtered average interval
                uint32_t avg_interval_us = calculate_filtered_average();
                
                if (avg_interval_us > 0) {
                    // Calculate BPM from average interval
                    // One pulse interval in microseconds
                    // 24 pulses per quarter note
                    // BPM = 60,000,000 / (avg_interval_us * 24)
                    // In your format (BPM * 100000):
                    uint64_t calculated_bpm = (60000000ULL * 100000ULL) / (avg_interval_us * 24);
                    
                    // Clamp to reasonable range (30-300 BPM)
                    if (calculated_bpm < 3000000) calculated_bpm = 3000000;
                    if (calculated_bpm > 30000000) calculated_bpm = 30000000;
                    
                    // Apply smoothing
                    uint32_t smoothed_bpm = apply_bpm_smoothing((uint32_t)calculated_bpm);
                    
                    // Check if BPM is stable (difference between smoothed and raw < 0.5 BPM)
                    int32_t stability_diff = (int32_t)calculated_bpm - (int32_t)smoothed_bpm;
                    if (stability_diff < 0) stability_diff = -stability_diff;
                    
                    if (stability_diff < 50000 && valid_count >= 12) {
                        ext_clock.bpm_locked = true;
                    }
                    
                    // Only update current_bpm if change is significant
                    int32_t diff = (int32_t)smoothed_bpm - (int32_t)current_bpm;
                    if (diff < 0) diff = -diff;
                    
                    if (diff > BPM_UPDATE_THRESHOLD || current_bpm == 0) {
                        current_bpm = smoothed_bpm;
                        dynamic_macro_bpm_changed(current_bpm);
                    }
                }
            }
        }
    }
    
    ext_clock.last_cycle_count = current_cycles;
    
    // Count pulses for beat detection (24 PPQN)
    ext_clock.pulse_count++;
    if (ext_clock.pulse_count >= 24) {
        ext_clock.pulse_count = 0;
        
        // Beat occurred - trigger your beat logic
        bpm_flash_state = true;
        last_bpm_flash_time = timer_read32();
        
    if ((unsynced_mode_active == 3) || 
			(bpm_beat_count == 0 && (unsynced_mode_active == 1))){
        dynamic_macro_handle_loop_trigger();
    }
        
        bpm_beat_count = (bpm_beat_count + 1) % 4;
    }
    
    // RELAY THE CLOCK: Send it back out when receiving external clock
    midi_send_data(&midi_device, 1, MIDI_CLOCK, 0, 0);
}

void handle_external_clock_start(void) {
    // Switch to external mode
    clock_mode = CLOCK_MODE_EXTERNAL;
    
    // Clear all external clock state
    ext_clock.running = true;
    ext_clock.synced = false;
    ext_clock.pulse_count = 0;
    ext_clock.last_cycle_count = 0;
    ext_clock.buffer_index = 0;
    ext_clock.last_pulse_cycles = dwt_get_cycles();
    ext_clock.smoothed_bpm = 0;  // Reset smoothing
    ext_clock.bpm_locked = false;
    
    // Clear interval buffer
    for (uint8_t i = 0; i < EXT_CLOCK_BUFFER_SIZE; i++) {
        ext_clock.interval_buffer_us[i] = 0;
    }
    
    // Reset beat counter
    bpm_beat_count = 0;
    
    // Stop internal clock if running
    int_clock.running = false;
    
    // Relay START message
    midi_send_data(&midi_device, 1, MIDI_START, 0, 0);
    
    dprintf("Ext MIDI clock: START\n");
}

void handle_external_clock_stop(void) {
    ext_clock.running = false;
    ext_clock.synced = false;
    ext_clock.pulse_count = 0;
    ext_clock.bpm_locked = false;
    
    // Reset BPM to 0 when external clock stops
    if (clock_mode == CLOCK_MODE_EXTERNAL) {
        current_bpm = 0;
        ext_clock.smoothed_bpm = 0;
        bpm_source_macro = 0;  // Clear external marker
        dynamic_macro_bpm_changed(current_bpm);
        
        // Clear the interval buffer
        for (uint8_t i = 0; i < EXT_CLOCK_BUFFER_SIZE; i++) {
            ext_clock.interval_buffer_us[i] = 0;
        }
        ext_clock.buffer_index = 0;
    }
    
    // Relay STOP message
    midi_send_data(&midi_device, 1, MIDI_STOP, 0, 0);
    
    dprintf("Ext MIDI clock: STOP (BPM reset to 0)\n");
}

void handle_external_clock_continue(void) {
    ext_clock.running = true;
    ext_clock.last_pulse_cycles = dwt_get_cycles();
    // Don't reset pulse_count or beat_count - continue from where we were
    
    // Relay CONTINUE message
    midi_send_data(&midi_device, 1, MIDI_CONTINUE, 0, 0);
    
    dprintf("Ext MIDI clock: CONTINUE\n");
}

// ============================================================================
// INTERNAL CLOCK TRANSMISSION FUNCTIONS
// ============================================================================

// Calculate pulse interval from BPM
static void calculate_pulse_interval(void) {
    if (current_bpm == 0) {
        int_clock.pulse_interval_us = 0;
        return;
    }
    
    // BPM is in format (BPM * 100000), e.g., 120.55 BPM = 12055000
    // Calculate microseconds per pulse with FULL PRECISION
    // 24 pulses per quarter note
    // microseconds per pulse = (60,000,000 * 100000) / (current_bpm * 24)
    // Simplify: = 6,000,000,000,000 / (current_bpm * 24)
    
    uint64_t interval_us = (6000000000000ULL) / (current_bpm * 24);
    int_clock.pulse_interval_us = (uint32_t)interval_us;
}

// Start internal clock generation
void internal_clock_start(void) {
    if (clock_mode == CLOCK_MODE_EXTERNAL && ext_clock.running) {
        // Don't start internal clock if external is active
        dprintf("Cannot start internal clock - external clock active\n");
        return;
    }
    
    clock_mode = CLOCK_MODE_INTERNAL;
    
    calculate_pulse_interval();
    
    int_clock.running = true;
    int_clock.pulse_count = 0;
    int_clock.next_pulse_cycles = dwt_get_cycles() + us_to_cycles(int_clock.pulse_interval_us);
    
    // Reset beat counter
    bpm_beat_count = 0;
    
    // Send MIDI START
    midi_send_data(&midi_device, 1, MIDI_START, 0, 0);
    
    dprintf("Internal clock: START at %lu.%05lu BPM\n", 
            current_bpm / 100000, current_bpm % 100000);
}

// Stop internal clock generation
void internal_clock_stop(void) {
    int_clock.running = false;
    int_clock.pulse_count = 0;
    
    // Send MIDI STOP
    midi_send_data(&midi_device, 1, MIDI_STOP, 0, 0);
    
    dprintf("Internal clock: STOP\n");
}

// Continue internal clock generation
void internal_clock_continue(void) {
    if (clock_mode == CLOCK_MODE_EXTERNAL && ext_clock.running) {
        return;
    }
    
    clock_mode = CLOCK_MODE_INTERNAL;
    
    calculate_pulse_interval();
    
    int_clock.running = true;
    int_clock.next_pulse_cycles = dwt_get_cycles() + us_to_cycles(int_clock.pulse_interval_us);
    
    // Send MIDI CONTINUE
    midi_send_data(&midi_device, 1, MIDI_CONTINUE, 0, 0);
    
    dprintf("Internal clock: CONTINUE\n");
}

// Update internal clock tempo (call this when BPM changes)
void internal_clock_tempo_changed(void) {
    if (clock_mode == CLOCK_MODE_INTERNAL && int_clock.running) {
        calculate_pulse_interval();
        // Recalculate next pulse time from now
        int_clock.next_pulse_cycles = dwt_get_cycles() + us_to_cycles(int_clock.pulse_interval_us);
        dprintf("Internal clock tempo updated: %lu.%05lu BPM\n",
                current_bpm / 100000, current_bpm % 100000);
    }
}

// ============================================================================
// CLOCK UPDATE - CALL THIS IN YOUR MAIN LOOP (matrix_scan_user)
// ============================================================================

// ============================================================================
// CLOCK UPDATE - CALL THIS IN YOUR MAIN LOOP (matrix_scan_user)
// ============================================================================

void midi_clock_task(void) {
    uint32_t current_cycles = dwt_get_cycles();
    uint32_t current_time = timer_read32();  // For flash timing
    
    // ====== HANDLE BPM FLASH TIMEOUT ======
    // Turn off flash after 100ms
    if (bpm_flash_state) {
        uint32_t elapsed = current_time - last_bpm_flash_time;
        if (elapsed >= 100) {  // 100ms flash duration
            bpm_flash_state = false;
        }
    }
    
    // Check for external clock timeout
    if (clock_mode == CLOCK_MODE_EXTERNAL && ext_clock.running) {
        uint32_t cycles_since_last;
        if (current_cycles >= ext_clock.last_pulse_cycles) {
            cycles_since_last = current_cycles - ext_clock.last_pulse_cycles;
        } else {
            cycles_since_last = (0xFFFFFFFF - ext_clock.last_pulse_cycles) + current_cycles + 1;
        }
        
        // If no pulse for 2 seconds, switch back to internal
        if (cycles_since_last > EXT_CLOCK_TIMEOUT_CYCLES) {
            ext_clock.running = false;
            ext_clock.synced = false;
            clock_mode = CLOCK_MODE_INTERNAL;
            dprintf("External clock timeout - switched to INTERNAL mode\n");
        }
    }
    
    // Handle internal clock generation
    if (clock_mode == CLOCK_MODE_INTERNAL && int_clock.running) {
        // Check if it's time to send next pulse (accounting for 32-bit wraparound)
        // Difference will be < 0x80000000 if current_cycles has passed next_pulse_cycles
        uint32_t diff = current_cycles - int_clock.next_pulse_cycles;
        
        // If diff is small (< half of uint32 max), we've passed the trigger time
        if (diff < 0x80000000) {
            // Send clock pulse
            midi_send_data(&midi_device, 1, MIDI_CLOCK, 0, 0);
            
            // Schedule next pulse (add interval to the scheduled time, not current time)
            int_clock.next_pulse_cycles += us_to_cycles(int_clock.pulse_interval_us);
            
            // Count pulses for beat detection (24 PPQN)
            int_clock.pulse_count++;
            if (int_clock.pulse_count >= 24) {
                int_clock.pulse_count = 0;
                
                // Beat occurred - trigger your beat logic
                bpm_flash_state = true;
                last_bpm_flash_time = current_time;  // Use current_time here
                
    if ((unsynced_mode_active == 3) || 
			(bpm_beat_count == 0 && (unsynced_mode_active == 1))){
        dynamic_macro_handle_loop_trigger();
    }
                
                bpm_beat_count = (bpm_beat_count + 1) % 4;
            }
        }
    }
}

// Check if internal clock is active
bool is_internal_clock_active(void) {
    return (clock_mode == CLOCK_MODE_INTERNAL) && int_clock.running;
}

// ============================================================================
// MIDI ROUTING FUNCTIONS
// ============================================================================

#ifdef MIDI_SERIAL_ENABLE
#include "uart.h"
#include "midi.h"          // For midi_register_* callback functions
#include "process_midi.h"  // For midi_send_*_smartchord and recording functions

// Define the serial MIDI device
MidiDevice midi_serial_device;

// =============================================================================
// HARDWARE MIDI SEND FUNCTION
// =============================================================================

// Serial MIDI send function - sends data to hardware MIDI OUT
void serial_midi_send_func(MidiDevice* device, uint16_t cnt, uint8_t byte0, uint8_t byte1, uint8_t byte2) {
    // Send bytes to USART1 (hardware MIDI OUT via PA15)
    if (cnt >= 1) {
        uart_putchar(MIDI_SERIAL_PORT, byte0);
    }
    if (cnt >= 2) {
        uart_putchar(MIDI_SERIAL_PORT, byte1);
    }
    if (cnt >= 3) {
        uart_putchar(MIDI_SERIAL_PORT, byte2);
    }
}

// =============================================================================
// EFFICIENT MIDI RECEIVE - BYTE-BY-BYTE WITH REALTIME PRIORITY
// =============================================================================

// Efficient serial MIDI receive with proper running status and ultra-low latency realtime thru
// This function is called as a pre-input-process callback before midi_device_process()
void serial_midi_get_func(MidiDevice* device) {
    uint16_t available = uart_available(MIDI_SERIAL_PORT);

    for (uint16_t i = 0; i < available; i++) {
        uint8_t byte = uart_getchar(MIDI_SERIAL_PORT);

        // =================================================================
        // REALTIME MESSAGES (0xF8-0xFF) - ULTRA LOW LATENCY PATH
        // These can occur ANYWHERE, even mid-message, and must be transparent
        // Forward immediately without going through the parser for minimal latency
        // =================================================================
        if (byte >= 0xF8) {
            // Handle based on routing mode
            switch (midi_in_mode) {
                case MIDI_ROUTE_THRU:
                    // THRU mode: Forward to both outputs WITHOUT processing clock
                    // (pure pass-through, no BPM sync from this source)
                    midi_send_data(&midi_device, 1, byte, 0, 0);  // USB out
                    uart_putchar(MIDI_SERIAL_PORT, byte);         // Hardware MIDI out
                    break;

                case MIDI_ROUTE_CLOCK_ONLY:
                    // CLOCK_ONLY mode: Process clock for BPM sync AND forward to both outputs
                    switch (byte) {
                        case MIDI_CLOCK:  // 0xF8
                            if (midi_clock_source == CLOCK_SOURCE_MIDI_IN) {
                                handle_external_clock_pulse();
                            }
                            break;
                        case MIDI_START:  // 0xFA
                            if (midi_clock_source == CLOCK_SOURCE_MIDI_IN) {
                                handle_external_clock_start();
                            }
                            break;
                        case MIDI_STOP:   // 0xFC
                            if (midi_clock_source == CLOCK_SOURCE_MIDI_IN) {
                                handle_external_clock_stop();
                            }
                            break;
                        case MIDI_CONTINUE:  // 0xFB
                            if (midi_clock_source == CLOCK_SOURCE_MIDI_IN) {
                                handle_external_clock_continue();
                            }
                            break;
                    }
                    // Forward to both outputs
                    midi_send_data(&midi_device, 1, byte, 0, 0);
                    uart_putchar(MIDI_SERIAL_PORT, byte);
                    break;

                case MIDI_ROUTE_PROCESS_ALL:
                    // PROCESS_ALL mode: Process clock for BPM sync (if source matches)
                    switch (byte) {
                        case MIDI_CLOCK:  // 0xF8
                            if (midi_clock_source == CLOCK_SOURCE_MIDI_IN) {
                                handle_external_clock_pulse();
                            }
                            break;
                        case MIDI_START:  // 0xFA
                            if (midi_clock_source == CLOCK_SOURCE_MIDI_IN) {
                                handle_external_clock_start();
                            }
                            break;
                        case MIDI_STOP:   // 0xFC
                            if (midi_clock_source == CLOCK_SOURCE_MIDI_IN) {
                                handle_external_clock_stop();
                            }
                            break;
                        case MIDI_CONTINUE:  // 0xFB
                            if (midi_clock_source == CLOCK_SOURCE_MIDI_IN) {
                                handle_external_clock_continue();
                            }
                            break;
                    }
                    // Don't forward realtime in PROCESS mode (processed locally)
                    break;

                case MIDI_ROUTE_IGNORE:
                    // IGNORE mode: Don't process or forward
                    break;
            }

            // Don't queue realtime for parser - they're handled immediately
            // Note: QMK's midi_process_byte also handles realtime transparently (lines 91-96)
            // but we want the fastest possible path for clock messages
            continue;
        }

        // =================================================================
        // ALL OTHER MESSAGES - QUEUE FOR STATE MACHINE PARSER
        // The parser handles running status, multi-byte messages, and SysEx
        // =================================================================

        // In IGNORE mode, don't even queue the bytes
        if (midi_in_mode == MIDI_ROUTE_IGNORE) {
            continue;
        }

        // Queue byte for the QMK MIDI parser (handles running status automatically)
        // The parser will call our registered callbacks when messages are complete
        midi_device_input(device, 1, &byte);
    }
}

// =============================================================================
// MIDI ROUTING CALLBACKS - Called by QMK parser when messages are complete
// These provide feature parity with USB MIDI (overrides, smart chords, RGB)
// =============================================================================

// Note On callback - routes based on mode with full processing in PROCESS mode
void serial_midi_noteon_callback(MidiDevice* device, uint8_t channel, uint8_t note, uint8_t velocity) {
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_noteon(&midi_device, channel, note, velocity);
            midi_send_noteon(&midi_serial_device, channel, note, velocity);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward non-clock messages thru to both outputs
            midi_send_noteon(&midi_device, channel, note, velocity);
            midi_send_noteon(&midi_serial_device, channel, note, velocity);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            // Full processing with overrides - same as USB path
            if (channeloverride) {
                channel = channel_number & 0x0F;
            }
            if (transposeoverride) {
                int16_t transposed = note + transpose_number + octave_number;
                note = (transposed < 0) ? 0 : (transposed > 127) ? 127 : (uint8_t)transposed;
            }
            if (velocityoverride) {
                velocity = velocity_number & 0x7F;
            }
            midi_send_noteon_smartchord(channel, note, velocity);
            // RGB effects for MIDI notes
            if (velocity > 0) {
                process_midi_basic_noteon(note);
            } else {
                process_midi_basic_noteoff(note);
            }
            break;

        case MIDI_ROUTE_IGNORE:
            // Don't forward note messages in IGNORE mode
            break;
    }
}

// Note Off callback
void serial_midi_noteoff_callback(MidiDevice* device, uint8_t channel, uint8_t note, uint8_t velocity) {
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_noteoff(&midi_device, channel, note, velocity);
            midi_send_noteoff(&midi_serial_device, channel, note, velocity);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward non-clock messages thru to both outputs
            midi_send_noteoff(&midi_device, channel, note, velocity);
            midi_send_noteoff(&midi_serial_device, channel, note, velocity);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            if (channeloverride) {
                channel = channel_number & 0x0F;
            }
            if (transposeoverride) {
                int16_t transposed = note + transpose_number + octave_number;
                note = (transposed < 0) ? 0 : (transposed > 127) ? 127 : (uint8_t)transposed;
            }
            if (velocityoverride) {
                velocity = velocity_number & 0x7F;
            }
            midi_send_noteoff_smartchord(channel, note, velocity);
            process_midi_basic_noteoff(note);
            break;

        case MIDI_ROUTE_IGNORE:
            break;
    }
}

// CC callback
void serial_midi_cc_callback(MidiDevice* device, uint8_t channel, uint8_t control, uint8_t value) {
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_cc(&midi_device, channel, control, value);
            midi_send_cc(&midi_serial_device, channel, control, value);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward non-clock messages thru to both outputs
            midi_send_cc(&midi_device, channel, control, value);
            midi_send_cc(&midi_serial_device, channel, control, value);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            if (channeloverride) {
                channel = channel_number & 0x0F;
            }
            midi_send_external_cc_with_recording(channel, control, value);
            break;

        case MIDI_ROUTE_IGNORE:
            break;
    }
}

// Pitch bend callback
void serial_midi_pitchbend_callback(MidiDevice* device, uint8_t channel, uint8_t lsb, uint8_t msb) {
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_pitchbend(&midi_device, channel, ((msb << 7) | lsb) - 8192);
            midi_send_pitchbend(&midi_serial_device, channel, ((msb << 7) | lsb) - 8192);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward non-clock messages thru to both outputs
            midi_send_pitchbend(&midi_device, channel, ((msb << 7) | lsb) - 8192);
            midi_send_pitchbend(&midi_serial_device, channel, ((msb << 7) | lsb) - 8192);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            if (channeloverride) {
                channel = channel_number & 0x0F;
            }
            midi_send_pitchbend_with_recording(channel, ((msb << 7) | lsb) - 8192);
            break;

        case MIDI_ROUTE_IGNORE:
            break;
    }
}

// Aftertouch (polyphonic key pressure) callback
void serial_midi_aftertouch_callback(MidiDevice* device, uint8_t channel, uint8_t note, uint8_t pressure) {
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_aftertouch(&midi_device, channel, note, pressure);
            midi_send_aftertouch(&midi_serial_device, channel, note, pressure);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward non-clock messages thru to both outputs
            midi_send_aftertouch(&midi_device, channel, note, pressure);
            midi_send_aftertouch(&midi_serial_device, channel, note, pressure);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            if (channeloverride) {
                channel = channel_number & 0x0F;
            }
            midi_send_aftertouch_with_recording(channel, note, pressure);
            break;

        case MIDI_ROUTE_IGNORE:
            break;
    }
}

// Program change callback
void serial_midi_progchange_callback(MidiDevice* device, uint8_t channel, uint8_t program) {
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_programchange(&midi_device, channel, program);
            midi_send_programchange(&midi_serial_device, channel, program);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward non-clock messages thru to both outputs
            midi_send_programchange(&midi_device, channel, program);
            midi_send_programchange(&midi_serial_device, channel, program);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            if (channeloverride) {
                channel = channel_number & 0x0F;
            }
            midi_send_program_with_recording(channel, program);
            break;

        case MIDI_ROUTE_IGNORE:
            break;
    }
}

// Channel pressure (monophonic aftertouch) callback
void serial_midi_chanpressure_callback(MidiDevice* device, uint8_t channel, uint8_t pressure) {
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_channelpressure(&midi_device, channel, pressure);
            midi_send_channelpressure(&midi_serial_device, channel, pressure);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward non-clock messages thru to both outputs
            midi_send_channelpressure(&midi_device, channel, pressure);
            midi_send_channelpressure(&midi_serial_device, channel, pressure);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            if (channeloverride) {
                channel = channel_number & 0x0F;
            }
            midi_send_channel_pressure_with_recording(channel, pressure);
            break;

        case MIDI_ROUTE_IGNORE:
            break;
    }
}

// Fallthrough callback - catches any messages not handled by specific callbacks
void serial_midi_fallthrough_callback(MidiDevice* device, uint16_t cnt, uint8_t byte0, uint8_t byte1, uint8_t byte2) {
    // Forward unhandled messages based on mode (SysEx, etc.)
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_data(&midi_device, cnt, byte0, byte1, byte2);
            midi_send_data(&midi_serial_device, cnt, byte0, byte1, byte2);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward non-clock messages thru to both outputs
            midi_send_data(&midi_device, cnt, byte0, byte1, byte2);
            midi_send_data(&midi_serial_device, cnt, byte0, byte1, byte2);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
        case MIDI_ROUTE_IGNORE:
            break;
    }
}

// =============================================================================
// MIDI SERIAL INITIALIZATION
// =============================================================================

// Initialize serial MIDI with callbacks
void setup_serial_midi(void) {
    // Initialize UART for MIDI (31250 baud)
    uart_init(MIDI_SERIAL_PORT, 31250);

    // Initialize the MIDI device
    midi_device_init(&midi_serial_device);
    midi_device_set_send_func(&midi_serial_device, serial_midi_send_func);
    midi_device_set_pre_input_process_func(&midi_serial_device, serial_midi_get_func);

    // Register callbacks for routing parsed messages
    // These are called by midi_device_process() after the state machine parser completes messages
    midi_register_noteon_callback(&midi_serial_device, serial_midi_noteon_callback);
    midi_register_noteoff_callback(&midi_serial_device, serial_midi_noteoff_callback);
    midi_register_cc_callback(&midi_serial_device, serial_midi_cc_callback);
    midi_register_pitchbend_callback(&midi_serial_device, serial_midi_pitchbend_callback);
    midi_register_aftertouch_callback(&midi_serial_device, serial_midi_aftertouch_callback);
    midi_register_progchange_callback(&midi_serial_device, serial_midi_progchange_callback);
    midi_register_chanpressure_callback(&midi_serial_device, serial_midi_chanpressure_callback);
    midi_register_fallthrough_callback(&midi_serial_device, serial_midi_fallthrough_callback);
}

// =============================================================================
// LEGACY ROUTE FUNCTION (kept for compatibility, now mostly handled by callbacks)
// =============================================================================

// Route MIDI data from hardware MIDI IN based on current mode
// Note: This is now primarily used for direct routing; most routing happens via callbacks
void route_midi_in_data(uint8_t byte1, uint8_t byte2, uint8_t byte3, uint8_t num_bytes) {
    switch (midi_in_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB and hardware MIDI out
            midi_send_data(&midi_device, num_bytes, byte1, byte2, byte3);
            midi_send_data(&midi_serial_device, num_bytes, byte1, byte2, byte3);
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Forward to both outputs (clock already processed)
            midi_send_data(&midi_device, num_bytes, byte1, byte2, byte3);
            midi_send_data(&midi_serial_device, num_bytes, byte1, byte2, byte3);
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            // Handled by callbacks now
            break;

        case MIDI_ROUTE_IGNORE:
            break;
    }
}
#endif // MIDI_SERIAL_ENABLE

// Route MIDI data from USB based on current mode
void route_usb_midi_data(uint8_t byte1, uint8_t byte2, uint8_t byte3, uint8_t num_bytes) {
    // Check if this is a clock-related message
    bool is_clock_msg = (byte1 == MIDI_CLOCK || byte1 == MIDI_START ||
                         byte1 == MIDI_STOP || byte1 == MIDI_CONTINUE);

    switch (usb_midi_mode) {
        case MIDI_ROUTE_THRU:
            // THRU mode: Send to BOTH USB out (echo back) and hardware MIDI out
            // Note: Echoing back to USB is usually not desired, so just send to hardware
#ifdef MIDI_SERIAL_ENABLE
            midi_send_data(&midi_serial_device, num_bytes, byte1, byte2, byte3);
#endif
            break;

        case MIDI_ROUTE_CLOCK_ONLY:
            // CLOCK_ONLY mode: Process clock through system, forward everything else thru
            if (is_clock_msg) {
                // Clock messages are processed by the system (handled elsewhere)
                // but also forward to hardware MIDI out
#ifdef MIDI_SERIAL_ENABLE
                midi_send_data(&midi_serial_device, num_bytes, byte1, byte2, byte3);
#endif
            } else {
                // Non-clock messages: forward to hardware MIDI out only
#ifdef MIDI_SERIAL_ENABLE
                midi_send_data(&midi_serial_device, num_bytes, byte1, byte2, byte3);
#endif
            }
            break;

        case MIDI_ROUTE_PROCESS_ALL:
            // Process through keyboard (default behavior)
            // This happens automatically via QMK's MIDI system
            break;

        case MIDI_ROUTE_IGNORE:
            // Ignore all USB MIDI data - do nothing
            break;
    }
}

// Toggle MIDI In routing mode
void toggle_midi_in_mode(void) {
    midi_in_mode = (midi_in_mode + 1) % 4;  // Cycle: PROCESS_ALL -> THRU -> CLOCK_ONLY -> IGNORE
}

// Toggle USB MIDI routing mode
void toggle_usb_midi_mode(void) {
    usb_midi_mode = (usb_midi_mode + 1) % 4;  // Cycle: PROCESS_ALL -> THRU -> CLOCK_ONLY -> IGNORE
}

// Toggle MIDI clock source
void toggle_midi_clock_source(void) {
    midi_clock_source = (midi_clock_source + 1) % 3;  // Cycle through 3 sources
}

bool is_external_clock_active(void) {
    return (clock_mode == CLOCK_MODE_EXTERNAL) && ext_clock.running && ext_clock.synced;
}

bool rgb_matrix_indicators_kb(void) {
    if (!rgb_matrix_indicators_user()) {
        return false;
    }
    
    // Only show indicators if smartchordlight != 2
    if (smartchordlight == 2) {
        return true;
    }
    
    // Get current user brightness and add 100, clamped to 255
    uint8_t user_brightness = rgb_matrix_get_val();
    uint8_t enhanced_brightness = (user_brightness > 155) ? 255 : user_brightness + 100;
    float brightness_factor = enhanced_brightness / 255.0f;
    
    // Light up caps lock if it's active
    if (host_keyboard_led_state().caps_lock) {
        uint8_t caps_led = get_special_key_led_index(29);  // Category 29 for caps lock
        if (caps_led != 99) {
            rgb_matrix_set_color(caps_led, 
                                (uint8_t)(200 * brightness_factor), 
                                0, 
                                0);
        }
    }
    
    // Flash tap tempo LED in pattern: green, red, red, red, repeat
    if (current_bpm != 0) {
        uint8_t tap_tempo_led = get_special_key_led_index(30);  // Category 30 for tap tempo
        if (tap_tempo_led != 99 && bpm_flash_state) {
            if (bpm_source_macro == 0) {
                // Manual BPM: green and red pattern
                if (bpm_beat_count == 1) {
                    rgb_matrix_set_color(tap_tempo_led, 
                                        0, 
                                        (uint8_t)(200 * brightness_factor), 
                                        0);  // Green on beat 1
                } else {
                    rgb_matrix_set_color(tap_tempo_led, 
                                        (uint8_t)(200 * brightness_factor), 
                                        0, 
                                        0);  // Red on beats 2, 3, 4
                }
            } else {
                // Automatic BPM: purple and pink pattern
                if (bpm_beat_count == 1) {
                    rgb_matrix_set_color(tap_tempo_led, 
                                        (uint8_t)(150 * brightness_factor), 
                                        0, 
                                        (uint8_t)(200 * brightness_factor));  // Purple on beat 1
                } else {
                    rgb_matrix_set_color(tap_tempo_led, 
                                        (uint8_t)(200 * brightness_factor), 
                                        (uint8_t)(100 * brightness_factor), 
                                        (uint8_t)(150 * brightness_factor));  // Pink on beats 2, 3, 4
                }
            }
        }
    }
    
    // Macro LEDs
    for (uint8_t i = 0; i < 4; i++) {
        uint8_t macro_led = get_special_key_led_index(31 + i);  // Categories 31-34 for macros 1-4
        if (macro_led != 99) {
            uint8_t r, g, b;
            get_macro_led_color(i, &r, &g, &b);
            // Apply enhanced brightness to macro colors
            rgb_matrix_set_color(macro_led, 
                                (uint8_t)(r * brightness_factor), 
                                (uint8_t)(g * brightness_factor), 
                                (uint8_t)(b * brightness_factor));
        }
    }
    
	if (smartchordlight != 3) {
    // SmartChord lighting functionality
    // Define the color mappings for each chord key index
    RGB chord_colors[42]; // Array to cover chordkey1-7 and their respective LED indices
    
    if (colorblindmode == 1) {
        // Set colors for colorblind mode (apply brightness factor)
        RGB color_blue = (RGB){(uint8_t)(255 * brightness_factor), (uint8_t)(176 * brightness_factor), 0};
        RGB color_red = (RGB){(uint8_t)(220 * brightness_factor), (uint8_t)(38 * brightness_factor), (uint8_t)(127 * brightness_factor)};
        RGB color_green = (RGB){(uint8_t)(254 * brightness_factor), (uint8_t)(97 * brightness_factor), 0};
        RGB color_purple = (RGB){(uint8_t)(200 * brightness_factor), (uint8_t)(50 * brightness_factor), (uint8_t)(200 * brightness_factor)};
        RGB color_yellow = (RGB){(uint8_t)(255 * brightness_factor), (uint8_t)(255 * brightness_factor), 0};
        RGB color_orange = (RGB){(uint8_t)(255 * brightness_factor), (uint8_t)(165 * brightness_factor), 0};
        RGB color_cyan = (RGB){0, (uint8_t)(255 * brightness_factor), (uint8_t)(255 * brightness_factor)};
        
        // Set specific colors for colorblind mode
        for (uint8_t i = 0; i < 6; i++) {
            chord_colors[i] = color_blue;           // Blue for chordkey1
            chord_colors[i + 6] = color_red;        // Red for chordkey2
            chord_colors[i + 12] = color_green;     // Green for chordkey3
            chord_colors[i + 18] = color_purple;    // Purple for chordkey4
            chord_colors[i + 24] = color_yellow;    // Yellow for chordkey5
            chord_colors[i + 30] = color_orange;    // Orange for chordkey6
            chord_colors[i + 36] = color_cyan;      // Cyan for chordkey7
        }
    } else {
        // Set colors for normal mode (apply brightness factor)
        RGB color_blue = (RGB){0, 0, (uint8_t)(255 * brightness_factor)};
        RGB color_red = (RGB){(uint8_t)(255 * brightness_factor), 0, 0};
        RGB color_green = (RGB){0, (uint8_t)(255 * brightness_factor), 0};
        RGB color_purple = (RGB){(uint8_t)(255 * brightness_factor), 0, (uint8_t)(255 * brightness_factor)};
        RGB color_yellow = (RGB){(uint8_t)(255 * brightness_factor), (uint8_t)(255 * brightness_factor), 0};
        RGB color_orange = (RGB){(uint8_t)(255 * brightness_factor), (uint8_t)(165 * brightness_factor), 0};
        RGB color_cyan = (RGB){0, (uint8_t)(255 * brightness_factor), (uint8_t)(255 * brightness_factor)};
        
        // Set specific colors for normal mode
        for (uint8_t i = 0; i < 6; i++) {
            chord_colors[i] = color_blue;           // Blue for chordkey1
            chord_colors[i + 6] = color_red;        // Red for chordkey2
            chord_colors[i + 12] = color_green;     // Green for chordkey3
            chord_colors[i + 18] = color_purple;    // Purple for chordkey4
            chord_colors[i + 24] = color_yellow;    // Yellow for chordkey5
            chord_colors[i + 30] = color_orange;    // Orange for chordkey6
            chord_colors[i + 36] = color_cyan;      // Cyan for chordkey7
        }
    }
    
    // Array of LED indices for chord keys
    uint8_t* chord_led_indices_ptr;
    uint8_t chord_led_indices_live[] = {
        chordkey1_led_index, chordkey1_led_index2, chordkey1_led_index3, chordkey1_led_index4, chordkey1_led_index5, chordkey1_led_index6,
        chordkey2_led_index, chordkey2_led_index2, chordkey2_led_index3, chordkey2_led_index4, chordkey2_led_index5, chordkey2_led_index6,
        chordkey3_led_index, chordkey3_led_index2, chordkey3_led_index3, chordkey3_led_index4, chordkey3_led_index5, chordkey3_led_index6,
        chordkey4_led_index, chordkey4_led_index2, chordkey4_led_index3, chordkey4_led_index4, chordkey4_led_index5, chordkey4_led_index6,
        chordkey5_led_index, chordkey5_led_index2, chordkey5_led_index3, chordkey5_led_index4, chordkey5_led_index5, chordkey5_led_index6,
        chordkey6_led_index, chordkey6_led_index2, chordkey6_led_index3, chordkey6_led_index4, chordkey6_led_index5, chordkey6_led_index6,
        chordkey7_led_index, chordkey7_led_index2, chordkey7_led_index3, chordkey7_led_index4, chordkey7_led_index5, chordkey7_led_index6
    };
    
    // Use frozen LEDs if progression is active, otherwise use live tracking
    if (leds_frozen && progression_active) {
        chord_led_indices_ptr = frozen_chord_leds;
    } else {
        chord_led_indices_ptr = chord_led_indices_live;
    }

    for (uint8_t i = 0; i < 42; i++) {
        uint8_t led_index = chord_led_indices_ptr[i];
        if (led_index >= 0 && led_index <= 70) {
            RGB base_color = chord_colors[i];
            rgb_matrix_set_color(led_index, base_color.r, base_color.g, base_color.b);
        }
    }
} 
    return true;
}

led_t led_usb_state;

/* advanced settings */
#define ANIM_FRAME_DURATION 120  // how long each frame lasts in ms
#define ANIM_SIZE           6    // number of bytes in standard patterns
#define WIDE_ANIM_SIZE      12   // number of bytes in wide patterns

/* timers */
uint32_t anim_timer = 0;

/* current frame */
uint8_t current_frame = 0;

/* logic */
static void render_luna(int LUNA_X, int LUNA_Y) {

// Optimized held key processing using bitmask
uint8_t oledheldkeys[11] = {
    (heldkey1 == 0) ? 99 : ((trueheldkey1 + oledkeyboard) % 24 + 1),
    (heldkey2 == 0) ? 99 : ((trueheldkey2 + oledkeyboard) % 24 + 1),
    (heldkey3 == 0) ? 99 : ((trueheldkey3 + oledkeyboard) % 24 + 1),
    (heldkey4 == 0) ? 99 : ((trueheldkey4 + oledkeyboard) % 24 + 1),
    (heldkey5 == 0) ? 99 : ((trueheldkey5 + oledkeyboard) % 24 + 1),
    (heldkey6 == 0) ? 99 : ((trueheldkey6 + oledkeyboard) % 24 + 1),
    (heldkey7 == 0) ? 99 : ((trueheldkey7 + oledkeyboard) % 24 + 1),
    (octaveheldkey1 == 0) ? 99 : ((trueoctaveheldkey1 + oledkeyboard) % 24 + 1),
    (octaveheldkey2 == 0) ? 99 : ((trueoctaveheldkey2 + oledkeyboard) % 24 + 1),
    (octaveheldkey3 == 0) ? 99 : ((trueoctaveheldkey3 + oledkeyboard) % 24 + 1),
    (octaveheldkey4 == 0) ? 99 : ((trueoctaveheldkey4 + oledkeyboard) % 24 + 1)
};

// Build bitmask for active notes (much faster than 264 comparisons)
uint32_t active_notes = 0;
for (uint8_t i = 0; i < 11; i++) {
    if (oledheldkeys[i] != 99 && oledheldkeys[i] >= 1 && oledheldkeys[i] <= 24) {
        active_notes |= (1UL << (oledheldkeys[i] - 1));
    }
}

// Extract note states from bitmask (O(1) instead of O(264))
bool C1_active = (active_notes & (1UL << 0)) != 0;
bool C1s_active = (active_notes & (1UL << 1)) != 0;
bool D1_active = (active_notes & (1UL << 2)) != 0;
bool D1s_active = (active_notes & (1UL << 3)) != 0;
bool E1_active = (active_notes & (1UL << 4)) != 0;
bool F1_active = (active_notes & (1UL << 5)) != 0;
bool F1s_active = (active_notes & (1UL << 6)) != 0;
bool G1_active = (active_notes & (1UL << 7)) != 0;
bool G1s_active = (active_notes & (1UL << 8)) != 0;
bool A1_active = (active_notes & (1UL << 9)) != 0;
bool A1s_active = (active_notes & (1UL << 10)) != 0;
bool B1_active = (active_notes & (1UL << 11)) != 0;
bool C2_active = (active_notes & (1UL << 12)) != 0;
bool C2s_active = (active_notes & (1UL << 13)) != 0;
bool D2_active = (active_notes & (1UL << 14)) != 0;
bool D2s_active = (active_notes & (1UL << 15)) != 0;
bool E2_active = (active_notes & (1UL << 16)) != 0;
bool F2_active = (active_notes & (1UL << 17)) != 0;
bool F2s_active = (active_notes & (1UL << 18)) != 0;
bool G2_active = (active_notes & (1UL << 19)) != 0;
bool G2s_active = (active_notes & (1UL << 20)) != 0;
bool A2_active = (active_notes & (1UL << 21)) != 0;
bool A2s_active = (active_notes & (1UL << 22)) != 0;
bool B2_active = (active_notes & (1UL << 23)) != 0;

// Basic empty patterns (6-byte)
static const char PROGMEM basic_empty_1[ANIM_SIZE] = {0x00, 0x00, 0xff, 0x00, 0x00, 0x00};  // Center dot
static const char PROGMEM basic_empty_2[ANIM_SIZE] = {0x00, 0x00, 0x00, 0xff, 0x00, 0x00};  // Dot position 4
static const char PROGMEM basic_empty_3[ANIM_SIZE] = {0xff, 0x00, 0x00, 0x00, 0x00, 0xff};  // Frame dots
static const char PROGMEM basic_empty_4[ANIM_SIZE] = {0x00, 0x00, 0x00, 0x00, 0xff, 0x00};  // Right dot
static const char PROGMEM basic_empty_5[ANIM_SIZE] = {0x00, 0x00, 0x00, 0x00, 0x00, 0xff};  // Far right dot
static const char PROGMEM basic_empty_6[ANIM_SIZE] = {0xff, 0x00, 0x00, 0x00, 0x00, 0x00};  // Left dot
static const char PROGMEM basic_empty_7[ANIM_SIZE] = {0x00, 0xff, 0x00, 0x00, 0x00, 0x00};  // Second position dot
static const char PROGMEM pattern_empty_special_1[ANIM_SIZE] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00};  // Completely empty

// Row 4 special patterns (with 0x80)
static const char PROGMEM row4_empty_1[ANIM_SIZE] = {0x80, 0x80, 0x80, 0xff, 0x00, 0x00};
static const char PROGMEM row4_empty_2[ANIM_SIZE] = {0x00, 0x00, 0xff, 0x80, 0x80, 0x80};
static const char PROGMEM row4_full_1[ANIM_SIZE] = {0xff, 0x00, 0xff, 0x80, 0x80, 0x80};

// Fill patterns
static const char PROGMEM fill_pattern_1[ANIM_SIZE] = {0xfe, 0x00, 0xff, 0x00, 0x00, 0x00};
static const char PROGMEM fill_pattern_2[ANIM_SIZE] = {0xff, 0xff, 0xff, 0xff, 0x00, 0x00};
static const char PROGMEM fill_pattern_3[ANIM_SIZE] = {0x00, 0x00, 0xff, 0xff, 0xff, 0xff};
static const char PROGMEM fill_pattern_4[ANIM_SIZE] = {0xff, 0x00, 0xff, 0xff, 0xff, 0xff};
static const char PROGMEM fill_pattern_5[ANIM_SIZE] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};  // Full solid

// Transition patterns
static const char PROGMEM transition_1[ANIM_SIZE] = {0x00, 0xff, 0x00, 0xfe, 0xfe, 0xfe};
static const char PROGMEM transition_2[ANIM_SIZE] = {0xff, 0x00, 0xfe, 0xfe, 0xfe, 0x00};
static const char PROGMEM transition_3[ANIM_SIZE] = {0xff, 0x00, 0xfe, 0xfe, 0xfe, 0xfe};

// Combined state patterns
static const char PROGMEM combined_1[ANIM_SIZE] = {0xfe, 0x00, 0xff, 0xff, 0xff, 0xff};
static const char PROGMEM combined_2[ANIM_SIZE] = {0xff, 0xff, 0xff, 0xff, 0x00, 0xfe};
static const char PROGMEM combined_3[ANIM_SIZE] = {0x00, 0x00, 0x00, 0xff, 0x00, 0xfe};
static const char PROGMEM combined_4[ANIM_SIZE] = {0xff, 0x00, 0xfe, 0xfe, 0x00, 0xff};
static const char PROGMEM combined_5[ANIM_SIZE] = {0xff, 0xff, 0xff, 0x00, 0xff, 0x00};
static const char PROGMEM combined_6[ANIM_SIZE] = {0x00, 0x00, 0x00, 0xff, 0x00, 0xff};
static const char PROGMEM combined_7[ANIM_SIZE] = {0x80, 0x80, 0x80, 0xff, 0x00, 0xff};

// Special fill patterns
static const char PROGMEM special_fill_1[ANIM_SIZE] = {0xff, 0xff, 0xff, 0xff, 0x00, 0xff};
static const char PROGMEM special_fill_2[ANIM_SIZE] = {0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe};
static const char PROGMEM special_fill_4[ANIM_SIZE] = {0xff, 0x00, 0xff, 0xff, 0x00, 0xff};
static const char PROGMEM special_fill_5[ANIM_SIZE] = {0xff, 0x00, 0xff, 0xff, 0xff, 0x00};
static const char PROGMEM special_fill_6[ANIM_SIZE] = {0xfe, 0xfe, 0xff, 0xff, 0xff, 0xff};
static const char PROGMEM special_fill_7[ANIM_SIZE] = {0xff, 0x00, 0xff, 0x00, 0x00, 0x00};
static const char PROGMEM special_fill_8[ANIM_SIZE] = {0x00, 0xff, 0x00, 0xff, 0xff, 0xff};
static const char PROGMEM special_fill_9[ANIM_SIZE] = {0xfe, 0xfe, 0xfe, 0x00, 0xff, 0x00};
static const char PROGMEM special_fill_10[ANIM_SIZE] = {0xfe, 0xfe, 0xfe, 0xfe, 0x00, 0xff};

// Wide patterns (12-byte)
static const char PROGMEM wide_empty[WIDE_ANIM_SIZE] = {0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00};
static const char PROGMEM wide_full_1[WIDE_ANIM_SIZE] = {0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0x00, 0xff, 0x00};
static const char PROGMEM wide_full_2[WIDE_ANIM_SIZE] = {0x00, 0xff, 0x00, 0xfe, 0xfe, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00};
static const char PROGMEM wide_full_3[ANIM_SIZE] = {0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe};
static const char PROGMEM wide_pattern_transition_2[WIDE_ANIM_SIZE] = {0x00, 0xff, 0x00, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe, 0x00, 0xff, 0x00};

// Frame elements
static const char PROGMEM endbar[2] = {0xff, 0x00};

static const char PROGMEM r5c14[2][ANIM_SIZE] = {
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, 
    {0xfe, 0xfe, 0xff, 0xff, 0xff, 0x00}
};

static const char PROGMEM r6c1[2][WIDE_ANIM_SIZE] = {
    {0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00}, 
    {0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00}
};

static const char PROGMEM Keyboardtop[128] = {
    0x00, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
    0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
    0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
    0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
    0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
    0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
    0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
    0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x00
};

static const char PROGMEM Keyboardbottom[128] = {
    0x00, 0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x03, 0x00
};

    /* animation */
void animate_luna(void) {
    static uint8_t yield_counter = 0;
    
    oled_set_cursor(0, 8);
    oled_write_raw_P(Keyboardtop, 128);
    
    // ROW 1
    oled_set_cursor(0, 9);
    oled_write_raw_P(C1_active ? transition_1 : basic_empty_7, ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(1, 9);
    if (C1_active && !C1s_active) {
        oled_write_raw_P(fill_pattern_1, ANIM_SIZE);
    } else if (!C1_active && C1s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (C1_active && C1s_active) {
        oled_write_raw_P(combined_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(2, 9);
    oled_write_raw_P(D1_active ? combined_4 : basic_empty_3, ANIM_SIZE);
    
    oled_set_cursor(3, 9);
    if (D1s_active && !E1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!D1s_active && E1_active) {
        oled_write_raw_P(combined_3, ANIM_SIZE);
    } else if (D1s_active && E1_active) {
        oled_write_raw_P(combined_2, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(4, 9);
    oled_write_raw_P(E1_active ? special_fill_9 : basic_empty_4, ANIM_SIZE);
    
    oled_set_cursor(5, 9);
    oled_write_raw_P(F1_active ? special_fill_10 : basic_empty_5, ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }
    
    oled_set_cursor(6, 9);
    if (F1s_active && !G1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!F1s_active && G1_active) {
        oled_write_raw_P(combined_3, ANIM_SIZE);
    } else if (F1s_active && G1_active) {
        oled_write_raw_P(combined_2, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(7, 9);
    if (G1_active && !G1s_active) {
        oled_write_raw_P(fill_pattern_1, ANIM_SIZE);
    } else if (!G1_active && G1s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (G1_active && G1s_active) {
        oled_write_raw_P(combined_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(8, 9);
    oled_write_raw_P(A1_active ? combined_4 : basic_empty_3, ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(9, 9);
    if (A1s_active && !B1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!A1s_active && B1_active) {
        oled_write_raw_P(combined_3, ANIM_SIZE);
    } else if (A1s_active && B1_active) {
        oled_write_raw_P(combined_2, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(10, 9);
    oled_write_raw_P(B1_active ? special_fill_9 : basic_empty_4, ANIM_SIZE);
    
    oled_set_cursor(11, 9);
    oled_write_raw_P(C2_active ? special_fill_10 : basic_empty_5, ANIM_SIZE);

    oled_set_cursor(12, 9);
    if (C2s_active && !D2_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!C2s_active && D2_active) {
        oled_write_raw_P(combined_3, ANIM_SIZE);
    } else if (C2s_active && D2_active) {
        oled_write_raw_P(combined_2, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }
    
    oled_set_cursor(13, 9);
    if (D2_active && !D2s_active) {
        oled_write_raw_P(fill_pattern_1, ANIM_SIZE);
    } else if (!D2_active && D2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (D2_active && D2s_active) {
        oled_write_raw_P(combined_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(14, 9);
    oled_write_raw_P(E2_active ? transition_3 : basic_empty_6, ANIM_SIZE);
    
    oled_set_cursor(15, 9);
    oled_write_raw_P(F2_active ? transition_1 : basic_empty_7, ANIM_SIZE);

    oled_set_cursor(16, 9);
    if (F2_active && !F2s_active) {
        oled_write_raw_P(fill_pattern_1, ANIM_SIZE);
    } else if (!F2_active && F2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (F2_active && F2s_active) {
        oled_write_raw_P(combined_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(17, 9);
    oled_write_raw_P(G2_active ? combined_4 : basic_empty_3, ANIM_SIZE);

    oled_set_cursor(18, 9);
    if (G2s_active && !A2_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!G2s_active && A2_active) {
        oled_write_raw_P(combined_3, ANIM_SIZE);
    } else if (G2s_active && A2_active) {
        oled_write_raw_P(combined_2, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(19, 9);
    if (A2_active && !A2s_active) {
        oled_write_raw_P(fill_pattern_1, ANIM_SIZE);
    } else if (!A2_active && A2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (A2_active && A2s_active) {
        oled_write_raw_P(combined_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(20, 9);
    oled_write_raw_P(B2_active ? transition_2 : basic_empty_6, ANIM_SIZE);

    oled_set_cursor(21, 9);
    oled_write_raw_P(endbar, 2);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    // ROW 2
    oled_set_cursor(0, 10);
    oled_write_raw_P(C1_active ? special_fill_8 : basic_empty_7, ANIM_SIZE);

    oled_set_cursor(1, 10);
    if (C1_active && !C1s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!C1_active && C1s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (C1_active && C1s_active) {
        oled_write_raw_P(special_fill_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(2, 10);
    oled_write_raw_P(D1_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);

    oled_set_cursor(3, 10);
    if (D1s_active && !E1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!D1s_active && E1_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (D1s_active && E1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(4, 10);
    oled_write_raw_P(E1_active ? combined_5 : basic_empty_4, ANIM_SIZE);

    oled_set_cursor(5, 10);
    oled_write_raw_P(F1_active ? special_fill_1 : basic_empty_5, ANIM_SIZE);

    oled_set_cursor(6, 10);
    if (F1s_active && !G1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!F1s_active && G1_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (F1s_active && G1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(7, 10);
    if (G1_active && !G1s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!G1_active && G1s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (G1_active && G1s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(8, 10);
    oled_write_raw_P(A1_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);

    oled_set_cursor(9, 10);
    if (A1s_active && !B1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!A1s_active && B1_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (A1s_active && B1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(10, 10);
    oled_write_raw_P(B1_active ? combined_5 : basic_empty_4, ANIM_SIZE);

    oled_set_cursor(11, 10);
    oled_write_raw_P(C2_active ? special_fill_1 : basic_empty_5, ANIM_SIZE);

    oled_set_cursor(12, 10);
    if (C2s_active && !D2_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!C2s_active && D2_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (C2s_active && D2_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(13, 10);
    if (D2_active && !D2s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!D2_active && D2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (D2_active && D2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(14, 10);
    oled_write_raw_P(E2_active ? fill_pattern_4 : basic_empty_6, ANIM_SIZE);

    oled_set_cursor(15, 10);
    oled_write_raw_P(F2_active ? special_fill_8 : basic_empty_7, ANIM_SIZE);

    oled_set_cursor(16, 10);
    if (F2_active && !F2s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!F2_active && F2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (F2_active && F2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(17, 10);
    oled_write_raw_P(G2_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(18, 10);
    if (G2s_active && !A2_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!G2s_active && A2_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (G2s_active && A2_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(19, 10);
    if (A2_active && !A2s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!A2_active && A2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (A2_active && A2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(20, 10);
    oled_write_raw_P(B2_active ? special_fill_5 : basic_empty_6, ANIM_SIZE);

    oled_set_cursor(21, 10);
    oled_write_raw_P(endbar, 2);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    // ROW 3 (continues with same pattern optimization...)
    oled_set_cursor(0, 11);
    oled_write_raw_P(C1_active ? special_fill_8 : basic_empty_7, ANIM_SIZE);

    oled_set_cursor(1, 11);
    if (C1_active && !C1s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!C1_active && C1s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (C1_active && C1s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(2, 11);
    oled_write_raw_P(D1_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);

    oled_set_cursor(3, 11);
    if (D1s_active && !E1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!D1s_active && E1_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (D1s_active && E1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(4, 11);
    oled_write_raw_P(E1_active ? combined_5 : basic_empty_4, ANIM_SIZE);

    oled_set_cursor(5, 11);
    oled_write_raw_P(F1_active ? special_fill_1 : basic_empty_5, ANIM_SIZE);

    oled_set_cursor(6, 11);
    if (F1s_active && !G1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!F1s_active && G1_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (F1s_active && G1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(7, 11);
    if (G1_active && !G1s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!G1_active && G1s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (G1_active && G1s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(8, 11);
    oled_write_raw_P(A1_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(9, 11);
    if (A1s_active && !B1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!A1s_active && B1_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (A1s_active && B1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(10, 11);
    oled_write_raw_P(B1_active ? combined_5 : basic_empty_4, ANIM_SIZE);

    oled_set_cursor(11, 11);
    oled_write_raw_P(C2_active ? special_fill_1 : basic_empty_5, ANIM_SIZE);

    oled_set_cursor(12, 11);
    if (C2s_active && !D2_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!C2s_active && D2_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (C2s_active && D2_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(13, 11);
    if (D2_active && !D2s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!D2_active && D2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (D2_active && D2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(14, 11);
    oled_write_raw_P(E2_active ? fill_pattern_4 : basic_empty_6, ANIM_SIZE);

    oled_set_cursor(15, 11);
    oled_write_raw_P(F2_active ? special_fill_8 : basic_empty_7, ANIM_SIZE);

    oled_set_cursor(16, 11);
    if (F2_active && !F2s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!F2_active && F2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (F2_active && F2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(17, 11);
    oled_write_raw_P(G2_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);

    oled_set_cursor(18, 11);
    if (G2s_active && !A2_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!G2s_active && A2_active) {
        oled_write_raw_P(combined_6, ANIM_SIZE);
    } else if (G2s_active && A2_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(19, 11);
    if (A2_active && !A2s_active) {
        oled_write_raw_P(special_fill_7, ANIM_SIZE);
    } else if (!A2_active && A2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (A2_active && A2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(basic_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(20, 11);
    oled_write_raw_P(B2_active ? special_fill_5 : basic_empty_6, ANIM_SIZE);

    oled_set_cursor(21, 11);
    oled_write_raw_P(endbar, 2);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    // ROW 4
    oled_set_cursor(0, 12);
    oled_write_raw_P(C1_active ? special_fill_8 : basic_empty_7, ANIM_SIZE);

    oled_set_cursor(1, 12);
    if (C1_active && !C1s_active) {
        oled_write_raw_P(row4_full_1, ANIM_SIZE);
    } else if (!C1_active && C1s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (C1_active && C1s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(2, 12);
    oled_write_raw_P(D1_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);

    oled_set_cursor(3, 12);
    if (D1s_active && !E1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!D1s_active && E1_active) {
        oled_write_raw_P(combined_7, ANIM_SIZE);
    } else if (D1s_active && E1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_1, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(4, 12);
    oled_write_raw_P(E1_active ? combined_5 : basic_empty_4, ANIM_SIZE);

    oled_set_cursor(5, 12);
    oled_write_raw_P(F1_active ? special_fill_1 : basic_empty_5, ANIM_SIZE);

    oled_set_cursor(6, 12);
    if (F1s_active && !G1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!F1s_active && G1_active) {
        oled_write_raw_P(combined_7, ANIM_SIZE);
    } else if (F1s_active && G1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(7, 12);
    if (G1_active && !G1s_active) {
        oled_write_raw_P(row4_full_1, ANIM_SIZE);
    } else if (!G1_active && G1s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (G1_active && G1s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(8, 12);
    oled_write_raw_P(A1_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(9, 12);
    if (A1s_active && !B1_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!A1s_active && B1_active) {
        oled_write_raw_P(combined_7, ANIM_SIZE);
    } else if (A1s_active && B1_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(10, 12);
    oled_write_raw_P(B1_active ? combined_5 : basic_empty_4, ANIM_SIZE);

    oled_set_cursor(11, 12);
    oled_write_raw_P(C2_active ? special_fill_1 : basic_empty_5, ANIM_SIZE);

    oled_set_cursor(12, 12);
    if (C2s_active && !D2_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!C2s_active && D2_active) {
        oled_write_raw_P(combined_7, ANIM_SIZE);
    } else if (C2s_active && D2_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(13, 12);
    if (D2_active && !D2s_active) {
        oled_write_raw_P(row4_full_1, ANIM_SIZE);
    } else if (!D2_active && D2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (D2_active && D2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_2, ANIM_SIZE);
    }
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(14, 12);
    oled_write_raw_P(E2_active ? fill_pattern_4 : basic_empty_6, ANIM_SIZE);

    oled_set_cursor(15, 12);
    oled_write_raw_P(F2_active ? special_fill_8 : basic_empty_7, ANIM_SIZE);

    oled_set_cursor(16, 12);
    if (F2_active && !F2s_active) {
        oled_write_raw_P(row4_full_1, ANIM_SIZE);
    } else if (!F2_active && F2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (F2_active && F2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(17, 12);
    oled_write_raw_P(G2_active ? special_fill_4 : basic_empty_3, ANIM_SIZE);

    oled_set_cursor(18, 12);
    if (G2s_active && !A2_active) {
        oled_write_raw_P(fill_pattern_2, ANIM_SIZE);
    } else if (!G2s_active && A2_active) {
        oled_write_raw_P(combined_7, ANIM_SIZE);
    } else if (G2s_active && A2_active) {
        oled_write_raw_P(special_fill_1, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_1, ANIM_SIZE);
    }

    oled_set_cursor(19, 12);
    if (A2_active && !A2s_active) {
        oled_write_raw_P(row4_full_1, ANIM_SIZE);
    } else if (!A2_active && A2s_active) {
        oled_write_raw_P(fill_pattern_3, ANIM_SIZE);
    } else if (A2_active && A2s_active) {
        oled_write_raw_P(fill_pattern_4, ANIM_SIZE);
    } else {
        oled_write_raw_P(row4_empty_2, ANIM_SIZE);
    }

    oled_set_cursor(20, 12);
    oled_write_raw_P(B2_active ? special_fill_5 : basic_empty_6, ANIM_SIZE);

    oled_set_cursor(21, 12);
    oled_write_raw_P(endbar, 2);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    // ROW 5
    oled_set_cursor(0, 13);
    oled_write_raw_P(C1_active ? wide_full_1 : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(2, 13);
    oled_write_raw_P(D1_active ? special_fill_2 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(3, 13);
    oled_write_raw_P(E1_active ? wide_full_2 : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(5, 13);
    oled_write_raw_P(F1_active ? wide_full_3 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(6, 13);
    oled_write_raw_P(G1_active ? wide_pattern_transition_2 : wide_empty, WIDE_ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(8, 13);
    oled_write_raw_P(A1_active ? special_fill_2 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(9, 13);
    oled_write_raw_P(B1_active ? wide_full_2 : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(11, 13);
    oled_write_raw_P(C2_active ? wide_full_3 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(12, 13);
    oled_write_raw_P(D2_active ? wide_pattern_transition_2 : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(14, 13);
    oled_write_raw_P(E2_active ? special_fill_6 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(15, 13);
    oled_write_raw_P(F2_active ? wide_full_1 : wide_empty, WIDE_ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(17, 13);
    oled_write_raw_P(G2_active ? special_fill_2 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(18, 13);
    oled_write_raw_P(A2_active ? wide_pattern_transition_2 : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(20, 13);
    oled_write_raw_P(B2_active ? r5c14[1] : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(21, 13);
    oled_write_raw_P(endbar, 2);

    // ROW 6
    oled_set_cursor(0, 14);
    oled_write_raw_P(C1_active ? r6c1[1] : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(2, 14);
    oled_write_raw_P(D1_active ? fill_pattern_5 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(3, 14);
    oled_write_raw_P(E1_active ? r6c1[1] : wide_empty, WIDE_ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(5, 14);
    oled_write_raw_P(F1_active ? fill_pattern_5 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(6, 14);
    oled_write_raw_P(G1_active ? r6c1[1] : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(8, 14);
    oled_write_raw_P(A1_active ? fill_pattern_5 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(9, 14);
    oled_write_raw_P(B1_active ? r6c1[1] : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(11, 14);
    oled_write_raw_P(C2_active ? fill_pattern_5 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(12, 14);
    oled_write_raw_P(D2_active ? r6c1[1] : wide_empty, WIDE_ANIM_SIZE);
    if (++yield_counter >= 8) { yield_counter = 0; __asm__ __volatile__ ("nop"); }

    oled_set_cursor(14, 14);
    oled_write_raw_P(E2_active ? fill_pattern_5 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(15, 14);
    oled_write_raw_P(F2_active ? r6c1[1] : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(17, 14);
    oled_write_raw_P(G2_active ? fill_pattern_5 : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(18, 14);
    oled_write_raw_P(A2_active ? r6c1[1] : wide_empty, WIDE_ANIM_SIZE);

    oled_set_cursor(20, 14);
    oled_write_raw_P(B2_active ? r5c14[1] : pattern_empty_special_1, ANIM_SIZE);

    oled_set_cursor(21, 14);
    oled_write_raw_P(endbar, 2);

    oled_set_cursor(0, 15);
    oled_write_raw_P(Keyboardbottom, 128);
}

#if OLED_TIMEOUT > 0
    /* the animation prevents the normal timeout from occuring */
    if (last_input_activity_elapsed() > OLED_TIMEOUT && last_led_activity_elapsed() > OLED_TIMEOUT) {
        oled_off();
        return;
    } else {
        oled_on();
    }
#endif

    /* animation timer */
    if (timer_elapsed32(anim_timer) > ANIM_FRAME_DURATION) {
        anim_timer = timer_read32();
        animate_luna();
    }
}

void ccondisplayupdates(uint8_t channel, uint8_t cc, uint8_t value) {
    dprintf("Ch %d CC:%d Value:%d\n", channel, cc, value);
}

void programdisplayupdates(uint8_t channel, uint8_t program) {
    dprintf("Ch %d Program:%d\n", channel, program);
}

void pitchbenddisplayupdates(uint8_t channel, int16_t bend_value) {
    dprintf("Ch %d PitchBend:%d\n", channel, bend_value);
}

void update_keylog_display(void) {
    char name[44];
    memset(name, ' ', sizeof(name) - 1);
    name[sizeof(name) - 1] = '\0';
    
    // Calculate note numbers within the musical note range
    int note_number1 = trueheldkey1;
    int note_number2 = trueheldkey2;
    int note_number3 = trueheldkey3;
    int note_number4 = trueheldkey4;
    int note_number5 = trueheldkey5;
    int note_number6 = trueheldkey6;
    int note_number7 = trueheldkey7;
    
    // Update the name string based on held keys
    if (heldkey7 != 0) {
        snprintf(name, sizeof(name), "%s,%s,%s,%s,%s,%s,%s",
                 chord_note_names[note_number1 % 12],
                 chord_note_names[note_number2 % 12],
                 chord_note_names[note_number3 % 12],
                 chord_note_names[note_number4 % 12],
                 chord_note_names[note_number5 % 12],
                 chord_note_names[note_number6 % 12],
                 chord_note_names[note_number7 % 12]);
    } else if (heldkey6 != 0) {
        snprintf(name, sizeof(name), "%s ,%s ,%s ,%s ,%s ,%s",
                 chord_note_names[note_number1 % 12],
                 chord_note_names[note_number2 % 12],
                 chord_note_names[note_number3 % 12],
                 chord_note_names[note_number4 % 12],
                 chord_note_names[note_number5 % 12],
                 chord_note_names[note_number6 % 12]);
    } else if (heldkey5 != 0) {
        snprintf(name, sizeof(name), "%s, %s, %s, %s, %s",
                 chord_note_names[note_number1 % 12],
                 chord_note_names[note_number2 % 12],
                 chord_note_names[note_number3 % 12],
                 chord_note_names[note_number4 % 12],
                 chord_note_names[note_number5 % 12]);
    } else if (heldkey4 != 0) {
        snprintf(name, sizeof(name), "%s, %s, %s, %s",
                 chord_note_names[note_number1 % 12],
                 chord_note_names[note_number2 % 12],
                 chord_note_names[note_number3 % 12],
                 chord_note_names[note_number4 % 12]);
    } else if (heldkey3 != 0) {
        snprintf(name, sizeof(name), "%s, %s, %s",
                 chord_note_names[note_number1 % 12],
                 chord_note_names[note_number2 % 12],
                 chord_note_names[note_number3 % 12]);
    } else if (heldkey2 != 0) {
        snprintf(name, sizeof(name), "%s, %s",
                 chord_note_names[note_number1 % 12],
                 chord_note_names[note_number2 % 12]);
    } else if (heldkey1 != 0) {
        snprintf(name, sizeof(name), "Note  %s", midi_note_names[note_number1]);
    } else if (heldkey1 == 0) {
        snprintf(name, sizeof(name), "   ");  // Three spaces
    }
    
    // Format the keylog string with proper padding
    int nlength = strlen(name);
    int tpadding = 21 - nlength;
    int lpadding = tpadding / 2;
    int rpadding = tpadding - lpadding;

    snprintf(keylog_str, sizeof(keylog_str), "%*s", lpadding, "");
    snprintf(keylog_str + strlen(keylog_str), sizeof(keylog_str) - strlen(keylog_str), "%s", name);
    snprintf(keylog_str + strlen(keylog_str), sizeof(keylog_str) - strlen(keylog_str), "%*s", rpadding, "");
}

static uint16_t last_modifier_press_time[4] = {0, 0, 0, 0};
static bool modifier_held[4] = {false, false, false, false}; 

void set_keylog(uint16_t keycode, keyrecord_t *record) {	

    char name[44];
    memset(name, ' ', sizeof(name) - 1);  // Fill with spaces
    name[sizeof(name) - 1] = '\0';        // Null-terminate the string	
    if ((keycode >= QK_MOD_TAP && keycode <= QK_MOD_TAP_MAX) ||
        (keycode >= QK_LAYER_TAP && keycode <= QK_LAYER_TAP_MAX)) {
        keycode = keycode & 0xFF;
    }

if (record->event.key.row == KEYLOC_ENCODER_CW && ccencoder != 130) { // Encoder turned clockwise
    if (CCValue[ccencoder] < 127) {
        CCValue[ccencoder] += cc_sensitivity;
        if (CCValue[ccencoder] > 127) {
            CCValue[ccencoder] = 127;
        }
        midi_send_cc_with_recording(channel_number, ccencoder, CCValue[ccencoder]);
        snprintf(name, sizeof(name), "CC%-3d  %d", ccencoder, CCValue[ccencoder]);
    }
} else if (record->event.key.row == KEYLOC_ENCODER_CCW && ccencoder != 130) { // Encoder turned counter-clockwise
    if (CCValue[ccencoder] > 0) {
        if (CCValue[ccencoder] >= cc_sensitivity) {
            CCValue[ccencoder] -= cc_sensitivity;
        } else {
            CCValue[ccencoder] = 0;
        }
        midi_send_cc_with_recording(channel_number, ccencoder, CCValue[ccencoder]);
        snprintf(name, sizeof(name), "CC%-3d  %d", ccencoder, CCValue[ccencoder]);
    }
}

// Transpose encoder handling (no limits)
if (record->event.key.row == KEYLOC_ENCODER_CW && transposeencoder != 130) {
    // Check if any sequencer modifier is held
    bool any_seq_mod_held = false;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_modifier_held[i]) {
            seq_state[i].locked_transpose++;
            snprintf(name, sizeof(name), "Seq %d Transpose: %d", i + 1, seq_state[i].locked_transpose);
            any_seq_mod_held = true;
        }
    }

    if (!any_seq_mod_held && !is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        transpose_number++;
        snprintf(name, sizeof(name), "Transpose: %d", transpose_number);
    } else if (!any_seq_mod_held && is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_transpose_target(i + 1);
                    set_overdub_transpose_target(i + 1, current_target + 1);
                    snprintf(name, sizeof(name), "Overdub %d Transpose: %d", i + 1, current_target + 1);
                }
            }
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_transpose_target(i + 1);
                    set_macro_transpose_target(i + 1, current_target + 1);
                    snprintf(name, sizeof(name), "Macro %d Transpose: %d", i + 1, current_target + 1);
                }
            }
        }
    } else if (!any_seq_mod_held && keysplitmodifierheld) {
        // Keysplit modifier is held - affect transpose_number2
        transpose_number2++;
        snprintf(name, sizeof(name), "Keysplit Transpose: %d", transpose_number2);
    } else if (!any_seq_mod_held && triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect transpose_number3
        transpose_number3++;
        snprintf(name, sizeof(name), "Triplesplit Transpose: %d", transpose_number3);
    }
} else if (record->event.key.row == KEYLOC_ENCODER_CCW && transposeencoder != 130) {
    // Check if any sequencer modifier is held
    bool any_seq_mod_held = false;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_modifier_held[i]) {
            seq_state[i].locked_transpose--;
            snprintf(name, sizeof(name), "Seq %d Transpose: %d", i + 1, seq_state[i].locked_transpose);
            any_seq_mod_held = true;
        }
    }

    if (!any_seq_mod_held && !is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        transpose_number--;
        snprintf(name, sizeof(name), "Transpose: %d", transpose_number);
    } else if (!any_seq_mod_held && is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_transpose_target(i + 1);
                    set_overdub_transpose_target(i + 1, current_target - 1);
                    snprintf(name, sizeof(name), "Overdub %d Transpose: %d", i + 1, current_target - 1);
                }
            }
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_transpose_target(i + 1);
                    set_macro_transpose_target(i + 1, current_target - 1);
                    snprintf(name, sizeof(name), "Macro %d Transpose: %d", i + 1, current_target - 1);
                }
            }
        }
    } else if (!any_seq_mod_held && keysplitmodifierheld) {
        // Keysplit modifier is held - affect transpose_number2
        transpose_number2--;
        snprintf(name, sizeof(name), "Keysplit Transpose: %d", transpose_number2);
    } else if (!any_seq_mod_held && triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect transpose_number3
        transpose_number3--;
        snprintf(name, sizeof(name), "Triplesplit Transpose: %d", transpose_number3);
    }
}

// Velocity encoder handling
if (record->event.key.row == KEYLOC_ENCODER_CW && velocityencoder != 130) { // Encoder turned clockwise
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        if (velocity_number < 127) {
            velocity_number += velocity_sensitivity;
            if (velocity_number > 127) {
                velocity_number = 127;
            }
            snprintf(name, sizeof(name), "Velocity: %d", velocity_number);
        }
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_velocity_offset_target(i + 1);
                    set_overdub_velocity_offset_target(i + 1, current_target + velocity_sensitivity);
                    snprintf(name, sizeof(name), "Overdub %d Velocity: %d", i + 1, current_target + velocity_sensitivity);
                }
            }
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_velocity_offset_target(i + 1);
                    set_macro_velocity_offset_target(i + 1, current_target + velocity_sensitivity);
                    snprintf(name, sizeof(name), "Macro %d Velocity: %d", i + 1, current_target + velocity_sensitivity);
                }
            }
        }
    }
} else if (record->event.key.row == KEYLOC_ENCODER_CCW && velocityencoder != 130) { // Encoder turned counter-clockwise
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        if (velocity_number > 0) {
            if (velocity_number >= velocity_sensitivity) {
                velocity_number -= velocity_sensitivity;
            } else {
                velocity_number = 0;
            }
            snprintf(name, sizeof(name), "Velocity: %d", velocity_number);
        }
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_velocity_offset_target(i + 1);
                    set_overdub_velocity_offset_target(i + 1, current_target - velocity_sensitivity);
                    snprintf(name, sizeof(name), "Overdub %d Velocity: %d", i + 1, current_target - velocity_sensitivity);
                }
            }
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_velocity_offset_target(i + 1);
                    set_macro_velocity_offset_target(i + 1, current_target - velocity_sensitivity);
                    snprintf(name, sizeof(name), "Macro %d Velocity: %d", i + 1, current_target - velocity_sensitivity);
                }
            }
        }
    }
}

// Channel encoder handling
if (record->event.key.row == KEYLOC_ENCODER_CW && channelencoder != 130) { // Encoder turned clockwise
    // Check if any sequencer modifier is held
    bool any_seq_mod_held = false;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_modifier_held[i]) {
            seq_state[i].locked_channel++;
            if (seq_state[i].locked_channel > 15) {
                seq_state[i].locked_channel = 0;
            }
            snprintf(name, sizeof(name), "Seq %d Channel: %d", i + 1, seq_state[i].locked_channel + 1);
            any_seq_mod_held = true;
        }
    }

    if (!any_seq_mod_held && !is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        channel_number++;
        if (channel_number > 15) {
            channel_number = 0;
        }
        snprintf(name, sizeof(name), "Channel: %d", channel_number);
    } else if (!any_seq_mod_held && is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_channel_offset_target(i + 1);
                    set_overdub_channel_offset_target(i + 1, current_target + 1);
                    snprintf(name, sizeof(name), "Overdub %d Channel: %d", i + 1, current_target + 1);
                }
            }
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_channel_offset_target(i + 1);
                    set_macro_channel_offset_target(i + 1, current_target + 1);
                    snprintf(name, sizeof(name), "Macro %d Channel: %d", i + 1, current_target + 1);
                }
            }
        }
    } else if (!any_seq_mod_held && keysplitmodifierheld) {
        // Keysplit modifier is held - affect keysplitchannel
        keysplitchannel++;
        if (keysplitchannel > 15) {
            keysplitchannel = 0;
        }
        snprintf(name, sizeof(name), "Keysplit Channel: %d", keysplitchannel);
    } else if (!any_seq_mod_held && triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect keysplit2channel
        keysplit2channel++;
        if (keysplit2channel > 15) {
            keysplit2channel = 0;
        }
        snprintf(name, sizeof(name), "Triplesplit Channel: %d", keysplit2channel);
    }
} else if (record->event.key.row == KEYLOC_ENCODER_CCW && channelencoder != 130) { // Encoder turned counter-clockwise
    // Check if any sequencer modifier is held
    bool any_seq_mod_held = false;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_modifier_held[i]) {
            if (seq_state[i].locked_channel == 0) {
                seq_state[i].locked_channel = 15;
            } else {
                seq_state[i].locked_channel--;
            }
            snprintf(name, sizeof(name), "Seq %d Channel: %d", i + 1, seq_state[i].locked_channel + 1);
            any_seq_mod_held = true;
        }
    }

    if (!any_seq_mod_held && !is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        if (channel_number == 0) {
            channel_number = 15;
        } else {
            channel_number--;
        }
        snprintf(name, sizeof(name), "Channel: %d", channel_number);
    } else if (!any_seq_mod_held && is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_channel_offset_target(i + 1);
                    set_overdub_channel_offset_target(i + 1, current_target - 1);
                    snprintf(name, sizeof(name), "Overdub %d Channel: %d", i + 1, current_target - 1);
                }
            }
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_channel_offset_target(i + 1);
                    set_macro_channel_offset_target(i + 1, current_target - 1);
                    snprintf(name, sizeof(name), "Macro %d Channel: %d", i + 1, current_target - 1);
                }
            }
        }
    } else if (!any_seq_mod_held && keysplitmodifierheld) {
        // Keysplit modifier is held - affect keysplitchannel
        if (keysplitchannel == 0) {
            keysplitchannel = 15;
        } else {
            keysplitchannel--;
        }
        snprintf(name, sizeof(name), "Keysplit Channel: %d", keysplitchannel);
    } else if (!any_seq_mod_held && triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect keysplit2channel
        if (keysplit2channel == 0) {
            keysplit2channel = 15;
        } else {
            keysplit2channel--;
        }
        snprintf(name, sizeof(name), "Triplesplit Channel: %d", keysplit2channel);
    }
}	

	if (keycode >= 0xc81e && keycode <= 0xc91d) {
		snprintf(name, sizeof(name), "Macro %d", keycode - 0xc81e);
	    // Handle macro modifier keys
    } else if (keycode >= 0xCC18 && keycode <= 0xCC1B) {
        uint8_t macro_idx = keycode - 0xCC18;  // 0-3 for macros 1-4
        uint8_t macro_num = macro_idx + 1;     // 1-4 for display
        
        if (record->event.pressed) {
            uint16_t current_time = timer_read();
            uint16_t time_since_last = timer_elapsed(last_modifier_press_time[macro_idx]);
            
            if (time_since_last < DOUBLE_TAP_THRESHOLD) {
                // Double tap detected
                reset_macro_transformations(macro_num);
                snprintf(name, sizeof(name), "L%d - CLEAR EDITS", macro_num);
            } else {
                // Single press
                snprintf(name, sizeof(name), "EDIT LOOP %d", macro_num);
            }
            
            modifier_held[macro_idx] = true;
            last_modifier_press_time[macro_idx] = current_time;
        } else {
            // Key released
            if (modifier_held[macro_idx]) {
                snprintf(name, sizeof(name), "   ");
                modifier_held[macro_idx] = false;
            }
        }
	} else if (keycode == 0xCC1C) {
		if (record->event.pressed) {
			global_edit_modifier_held = true;
			snprintf(name, sizeof(name), "EDIT MODIFIER");
		}

	// Handle macro keys when global modifier is active
	} else if (global_edit_modifier_held && keycode >= 0xCC08 && keycode <= 0xCC0B) {
		uint8_t macro_idx = keycode - 0xCC08;  // 0-3 for macros 1-4
		uint8_t macro_num = macro_idx + 1;     // 1-4 for display
		
        if (record->event.pressed) {
            uint16_t current_time = timer_read();
            uint16_t time_since_last = timer_elapsed(last_modifier_press_time[macro_idx]);
            
            if (time_since_last < DOUBLE_TAP_THRESHOLD) {
                // Double tap detected
                reset_macro_transformations(macro_num);
                snprintf(name, sizeof(name), "L%d - CLEAR EDITS", macro_num);
            } else {
                // Single press
                snprintf(name, sizeof(name), "EDIT LOOP %d", macro_num);
            }
            
            modifier_held[macro_idx] = true;
            last_modifier_press_time[macro_idx] = current_time;
        } else {
            // Key released
            if (modifier_held[macro_idx]) {
                snprintf(name, sizeof(name), "   ");
                modifier_held[macro_idx] = false;
            }
        }
		
} else if (global_edit_modifier_held && keycode >= 0xCC49 && keycode <= 0xCC4C) {
		uint8_t macro_idx = keycode - 0xCC49;  // 0-3 for macros 1-4
		uint8_t macro_num = macro_idx + 1;     // 1-4 for display
		
        if (record->event.pressed) {
            uint16_t current_time = timer_read();
            uint16_t time_since_last = timer_elapsed(last_modifier_press_time[macro_idx]);
            
            if (time_since_last < DOUBLE_TAP_THRESHOLD) {
                // Double tap detected
                reset_overdub_transformations(macro_num);
                snprintf(name, sizeof(name), "L%d - CLEAR EDITS", macro_num);
            } else {
                // Single press
                snprintf(name, sizeof(name), "EDIT LOOP %d", macro_num);
            }
            
            modifier_held[macro_idx] = true;
            last_modifier_press_time[macro_idx] = current_time;
        } else {
            // Key released
            if (modifier_held[macro_idx]) {
                snprintf(name, sizeof(name), "   ");
                modifier_held[macro_idx] = false;
            }
        }
		
}else if (keycode == 0xCC22) {
    // Copy button - independent display state
    if (record->event.pressed) {
        if (display_copy_active || display_paste_active) {
            // Cancel operation
            snprintf(name, sizeof(name), "LOOP COPY CANCELLED");
            display_copy_active = false;
            display_paste_active = false;
            display_source_macro = 0;
        } else {
            // Start copy operation
            snprintf(name, sizeof(name), "SELECT LOOP TO COPY");
            display_copy_active = true;
        }
    }

} else if (display_copy_active && keycode >= 0xCC08 && keycode <= 0xCC0B) {
    // Copy mode - selecting source macro
    uint8_t macro_num = keycode - 0xCC08 + 1;
    
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "L%d - COPIED", macro_num);
        display_copy_active = false;
        display_paste_active = true;
        display_source_macro = macro_num;
    }

} else if (display_paste_active && keycode >= 0xCC08 && keycode <= 0xCC0B) {
    // Paste mode - selecting target macro
    uint8_t macro_num = keycode - 0xCC08 + 1;
    
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "PASTED L%d - TO %d", display_source_macro, macro_num);
        display_paste_active = false;
        display_source_macro = 0;
    }
	
	
} else if (overdub_button_held && mute_button_held && keycode >= 0xCC08 && keycode <= 0xCC0B) {
    // Overdub + Mute buttons + macro key = Solo overdub
    uint8_t macro_idx = keycode - 0xCC08;
    uint8_t macro_num = macro_idx + 1;
    
    if (record->event.pressed) {
        char status_str[4];
        char overdub_str[4];
        get_macro_status_string(macro_idx, status_str);
        get_overdub_status_string(macro_idx, overdub_str);
        
        if (strcmp(status_str, "PLY") == 0) {
            snprintf(name, sizeof(name), "L%d - MUTE MAIN ONLY", macro_num);
        } else if (strcmp(overdub_str, "SOL") == 0) {
            snprintf(name, sizeof(name), "L%d - MUTE DUB", macro_num);
        } else if (strcmp(overdub_str, "PLY") == 0 || strcmp(overdub_str, "MUT") == 0) {
            snprintf(name, sizeof(name), "L%d - PLAY DUB ONLY", macro_num);
        } else {
            snprintf(name, sizeof(name), "L%d - START DUB ONLY", macro_num);
        }
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (overdub_button_held && keycode >= 0xCC08 && keycode <= 0xCC0B) {
    // Overdub button + macro key (without mute)
    uint8_t macro_idx = keycode - 0xCC08;
    uint8_t macro_num = macro_idx + 1;
    
    if (record->event.pressed) {
        char status_str[4];
        get_macro_status_string(macro_idx, status_str);
        
        if (strcmp(status_str, "PLY") == 0) {
            snprintf(name, sizeof(name), "L%d - END OVERDUB", macro_num);
        } else if (strcmp(status_str, "REC") == 0) {
            snprintf(name, sizeof(name), "L%d - REC+OVERDUB", macro_num);
        } else if (strcmp(status_str, "DUB") == 0) {
            snprintf(name, sizeof(name), "L%d - START OVERDUB", macro_num);
        } else if (strcmp(status_str, "MUT") == 0) {
            snprintf(name, sizeof(name), "L%d - PLAY+OVERDUB", macro_num);
        } else if (strcmp(status_str, " - ") == 0) {
            snprintf(name, sizeof(name), "L%d - EMPTY", macro_num);
        } else {
            snprintf(name, sizeof(name), "L%d - OVERDUB", macro_num);
        }
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (mute_button_held && keycode >= 0xCC08 && keycode <= 0xCC0B) {
    // Mute button + macro key (without overdub)
    uint8_t macro_idx = keycode - 0xCC08;
    uint8_t macro_num = macro_idx + 1;
    
    if (record->event.pressed) {
        char status_str[4];
        char overdub_str[4];
        get_macro_status_string(macro_idx, status_str);
        get_overdub_status_string(macro_idx, overdub_str);
        
        if (strcmp(overdub_str, "PLY") == 0) {
            snprintf(name, sizeof(name), "L%d - MUTE OVERDUB", macro_num);
        } else if (strcmp(overdub_str, "MUT") == 0) {
            snprintf(name, sizeof(name), "L%d - UNMUTE OVERDUB", macro_num);
        } else if (strcmp(overdub_str, "SOL") == 0) {
            snprintf(name, sizeof(name), "L%d - MUTE DUB", macro_num);
        } else {
            snprintf(name, sizeof(name), "L%d - OVERDUB TOGGLE", macro_num);
        }
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (octave_doubler_button_held && keycode >= 0xCC08 && keycode <= 0xCC0B) {
    // Octave doubler button + macro key
    uint8_t macro_idx = keycode - 0xCC08;
    uint8_t macro_num = macro_idx + 1;
    
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "L%d - OCTAVE TOGGLE", macro_num);
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (sample_mode_active && keycode >= 0xCC08 && keycode <= 0xCC0B) {
    // Sample mode + macro key
    uint8_t macro_idx = keycode - 0xCC08;
    uint8_t macro_num = macro_idx + 1;
    
    if (record->event.pressed) {
        char status_str[4];
        get_macro_status_string(macro_idx, status_str);
        
        if (strcmp(status_str, "PLY") == 0) {
            snprintf(name, sizeof(name), "L%d - RESTART", macro_num);
        } else if (strcmp(status_str, "REC") == 0) {
            snprintf(name, sizeof(name), "L%d - END+ONESHOT", macro_num);
        } else if (strcmp(status_str, "MUT") == 0) {
            snprintf(name, sizeof(name), "L%d - ONESHOT PLAY", macro_num);
        } else if (strcmp(status_str, " - ") == 0) {
            snprintf(name, sizeof(name), "L%d - ONESHOT REC", macro_num);
        } else {
            snprintf(name, sizeof(name), "L%d - ONESHOT", macro_num);
        }
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (!display_copy_active && !display_paste_active && !global_edit_modifier_held && 
           keycode >= 0xCC08 && keycode <= 0xCC0B) {
    // Normal macro key presses
    uint8_t macro_idx = keycode - 0xCC08;
    uint8_t macro_num = macro_idx + 1;
    
    if (record->event.pressed) {
        char status_str[4];
        char cmd_str[4];
        char overdub_str[4];
        bool should_flash = false;
        
        get_macro_status_string(macro_idx, status_str);
        get_queued_command_string(macro_idx, cmd_str, &should_flash);
        get_overdub_status_string(macro_idx, overdub_str);
        
       // Check for queued commands first
		if (should_flash) {
			if (strcmp(cmd_str, "PLY") == 0) {
				// Check if this is actually a record end + overdub start
				if (strcmp(status_str, "REC") == 0 && overdub_button_held) {
					snprintf(name, sizeof(name), "L%d - Q REC & DUB", macro_num);
				} else if (strcmp(overdub_str, "PLY") == 0) {
					snprintf(name, sizeof(name), "L%d - Q MAIN+OVR", macro_num);
				} else if (strcmp(overdub_str, "MUT") == 0) {
					snprintf(name, sizeof(name), "L%d - Q MAIN ONLY", macro_num);
				} else {
					snprintf(name, sizeof(name), "L%d - Q PLAY", macro_num);
				}
			} else if (strcmp(cmd_str, "MUT") == 0) {
				// Check if this is actually a record end + overdub start (double-tap case)
				if (strcmp(status_str, "REC") == 0 && overdub_button_held) {
					snprintf(name, sizeof(name), "L%d - Q REC & MUTE", macro_num);
				} else {
					snprintf(name, sizeof(name), "L%d - Q MUTE", macro_num);
				}
			} else if (strcmp(cmd_str, "END") == 0) {
				// This will now only be true for non-overdub cases
				if (strcmp(status_str, "REC") == 0) {
					snprintf(name, sizeof(name), "L%d - Q REC END", macro_num);
				} else if (strcmp(status_str, "DUB") == 0) {
					snprintf(name, sizeof(name), "L%d - Q OVR END", macro_num);
				} else {
					snprintf(name, sizeof(name), "L%d - Q MUTE", macro_num);
				}
			} else if (strcmp(cmd_str, "REC") == 0) {
				snprintf(name, sizeof(name), "L%d - Q RECORD", macro_num);
			} else if (strcmp(cmd_str, "SOL") == 0) {
				snprintf(name, sizeof(name), "L%d - Q DUB ONLY", macro_num);
			} else {
				snprintf(name, sizeof(name), "L%d - QUEUED", macro_num);
			}
		}
        // Check current status
        else if (strcmp(status_str, "REC") == 0) {
            snprintf(name, sizeof(name), "L%d - RECORDING", macro_num);
        } else if (strcmp(status_str, "DUB") == 0) {
            snprintf(name, sizeof(name), "L%d - OVERDUBBING", macro_num);
        } else if (strcmp(status_str, "PLY") == 0) {
            if (strcmp(overdub_str, "PLY") == 0) {
                snprintf(name, sizeof(name), "L%d - MAIN+OVERDUB", macro_num);
            } else if (strcmp(overdub_str, "MUT") == 0) {
                snprintf(name, sizeof(name), "L%d - MAIN ONLY", macro_num);
            } else {
                snprintf(name, sizeof(name), "L%d - PLAYING", macro_num);
            }
        } else if (strcmp(overdub_str, "SOL") == 0) {
            snprintf(name, sizeof(name), "L%d - DUB ONLY", macro_num);
        } else if (strcmp(status_str, "MUT") == 0) {
            if (strcmp(overdub_str, "PLY") == 0) {
                snprintf(name, sizeof(name), "L%d - DUB ONLY", macro_num);
            } else {
                snprintf(name, sizeof(name), "L%d - MUTED", macro_num);
            }
        } else if (strcmp(status_str, " - ") == 0) {
            snprintf(name, sizeof(name), "L%d - EMPTY", macro_num);
        } else {
            snprintf(name, sizeof(name), "L%d - READY", macro_num);
        }
        
    } else {
        snprintf(name, sizeof(name), "   ");
    }
	
	} else if (keycode == 0xCC51) {
    if (record->event.pressed) {
        // Only allow changes in internal clock mode
        if (clock_mode == CLOCK_MODE_INTERNAL) {
            // Increase by 1.00 BPM (100000 in internal format)
            uint32_t new_bpm = current_bpm + 100000;
            
            // Clamp to max 300 BPM
            if (new_bpm > 30000000) {
                new_bpm = 30000000;
            }
            
            current_bpm = new_bpm;
            bpm_source_macro = 0;  // Mark as manual BPM
            
            // Update internal clock if running
            internal_clock_tempo_changed();
            dynamic_macro_bpm_changed(current_bpm);
            
            // Display BPM
            uint16_t display_bpm = current_bpm / 100000;
            uint16_t decimal_part = (current_bpm % 100000) / 1000;
            snprintf(name, sizeof(name), "BPM+ %d.%02d", display_bpm, decimal_part);
    }
	}


// BPM DOWN button (0xCC52) - decrease by 1.00 BPM
} else if (keycode == 0xCC52) {
    if (record->event.pressed) {
        // Only allow changes in internal clock mode
        if (clock_mode == CLOCK_MODE_INTERNAL) {
            // Decrease by 1.00 BPM (100000 in internal format)
            int32_t new_bpm = (int32_t)current_bpm - 100000;
            
            // Clamp to min 30 BPM
            if (new_bpm < 3000000) {
                new_bpm = 3000000;
            }
            
            current_bpm = (uint32_t)new_bpm;
            bpm_source_macro = 0;  // Mark as manual BPM
            
            // Update internal clock if running
            internal_clock_tempo_changed();
            dynamic_macro_bpm_changed(current_bpm);
            
            // Display BPM
            uint16_t display_bpm = current_bpm / 100000;
            uint16_t decimal_part = (current_bpm % 100000) / 1000;
            snprintf(name, sizeof(name), "BPM- %d.%02d", display_bpm, decimal_part);
        }
    }

	
} else if (keycode >= 0xCC1D && keycode <= 0xCC20) {
    // Octave doubler toggle for macros 1-4
    uint8_t macro_num = keycode - 0xCC1D + 1;
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "L%d - OCTAVE TOGGLE", macro_num);
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (keycode == 0xCC21) {
    // Octave doubler modifier button
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "OCTAVE MODIFIER");
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (keycode == 0xCC10) {
    // Mute button
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "MUTE MODIFIER");
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (keycode == 0xCC15) {
    // Overdub button
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "OVERDUB MODIFIER");
    } else {
        snprintf(name, sizeof(name), "   ");
    }

} else if (keycode == 0xCC16) {
    // Unsynced mode toggle
    if (record->event.pressed) {
        if (unsynced_mode_active == 5) {
			unsynced_mode_active = 1;
            snprintf(name, sizeof(name), "Sync BPM - Bar");
        } else if (unsynced_mode_active == 4) {
			unsynced_mode_active = 2;
            snprintf(name, sizeof(name), "Unsynced - Prime");
        } else if (unsynced_mode_active == 3) {
			unsynced_mode_active = 0;
            snprintf(name, sizeof(name), "Sync to Loop - Prime");
		} else if (unsynced_mode_active == 1) {
			unsynced_mode_active = 3;
            snprintf(name, sizeof(name), "Sync BPM - Beat");
		} else if (unsynced_mode_active == 0) {
			unsynced_mode_active = 4;
            snprintf(name, sizeof(name), "Sync to Loop");
		} else if (unsynced_mode_active == 2) {
			unsynced_mode_active = 5;
            snprintf(name, sizeof(name), "Unsynced");
    }
	}

} else if (keycode == 0xCC17) {
    // Sample mode toggle
    if (record->event.pressed) {
        if (sample_mode_active) {
            snprintf(name, sizeof(name), "SAMPLE MODE ON");
        } else {
            snprintf(name, sizeof(name), "SAMPLE MODE OFF");
        }
    }

} else if (keycode >= 0xCC0C && keycode <= 0xCC0F) {
    // Dedicated mute keys
    uint8_t macro_idx = keycode - 0xCC0C;
    uint8_t macro_num = macro_idx + 1;
    if (record->event.pressed) {
        if (overdub_muted[macro_idx]) {
            snprintf(name, sizeof(name), "L%d - OVERDUB UNMUTED", macro_num);
        } else {
            snprintf(name, sizeof(name), "L%d - OVERDUB MUTED", macro_num);
        }
    }

} else if (keycode >= 0xCC23 && keycode <= 0xCC26) {
    // Save macro 1-4
    uint8_t macro_num = keycode - 0xCC23 + 1;
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "SAVE LOOP %d", macro_num);
    }

} else if (keycode == 0xCC27) {
    // Save All Loops button
    if (record->event.pressed) {
        snprintf(name, sizeof(name), "SAVE ALL LOOPS");
    }
	
} else if (keycode == 0xCC48) {
    if (record->event.pressed) {
        if (overdub_advanced_mode) {
            dprintf("dynamic macro: 8 Track mode ENABLED\n");
        } else {
            dprintf("dynamic macro: 8 Track mode DISABLED\n");
        }
    }

		
} else if (keycode >= 49925 && keycode <= 50052) {
    uint8_t target_velocity = (keycode - 49925); // 0-127
    
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        // Normal behavior - affect global velocity
        velocity_number = target_velocity;
        snprintf(name, sizeof(name), "DEFAULT VELOCITY %d", velocity_number);
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    set_overdub_velocity_absolute_target(i + 1, target_velocity);
                }
            }
            
            if (target_velocity == 0) {
                snprintf(name, sizeof(name), "Overdub: Default Velocity");
            } else {
                snprintf(name, sizeof(name), "Overdub: Velocity %d", target_velocity);
            }
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    set_macro_velocity_absolute_target(i + 1, target_velocity);
                }
            }
            
            if (target_velocity == 0) {
                snprintf(name, sizeof(name), "Loop: Default Velocity");
            } else {
                snprintf(name, sizeof(name), "Loop: Velocity %d", target_velocity);
            }
        }
    }
}else if (keycode >= 0xC6CA && keycode <= 0xC749) {
    // Deprecated: keysplit velocity (velocity_number2)
    snprintf(name, sizeof(name), "KS Velocity (deprecated)");
	//velocity3
    } else if (keycode >= 0xC77A && keycode <= 0xC7F9) {
    // Deprecated: triplesplit velocity (velocity_number3)
    snprintf(name, sizeof(name), "TS Velocity (deprecated)");
	//program change	
    } else if (keycode >= 49792 && keycode <= 49919) {
        snprintf(name, sizeof(name), "Program %d", keycode - 49792);

} else if (keycode >= 29043 && keycode <= 29058) { // Channel Absolute
    uint8_t target_channel = keycode - 29043; // 0-15
    
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        // Normal behavior - affect global channel
        channel_number = target_channel;
        snprintf(name, sizeof(name), "DEFAULT CHANNEL %d", (channel_number + 1));
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    set_overdub_channel_absolute_target(i + 1, target_channel + 1);
                }
            }
            snprintf(name, sizeof(name), "Overdub: Channel %d", target_channel + 1);
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    set_macro_channel_absolute_target(i + 1, target_channel + 1);
                }
            }
            snprintf(name, sizeof(name), "Loop: Channel %d", target_channel + 1);
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect keysplitchannel
        keysplitchannel = target_channel;
        snprintf(name, sizeof(name), "KEYSPLIT CH %d", (keysplitchannel + 1));
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect keysplit2channel
        keysplit2channel = target_channel;
        snprintf(name, sizeof(name), "TRIPLESPLIT CH %d", (keysplit2channel + 1));
    }
} else if (keycode >= 0xC652 && keycode <= 0xC661) {
	keysplitchannel = keycode - 0xC651;
    snprintf(name, sizeof(name), "KEYSPLIT CH  %d", keysplitchannel);
	
		} else if (keycode >= 0xC6BA && keycode <= 0xC6C9) {
	keysplit2channel = keycode - 0xC6B9;
    snprintf(name, sizeof(name), "TRIPLESPLIT CH %d", keysplit2channel);
	
	} else if (keycode == 0xCCA8) {
   if (record->event.pressed) {
       truesustain = !truesustain;
       if (truesustain) {
           snprintf(name, sizeof(name),"True Sustain ON");
       } else {
           snprintf(name, sizeof(name),"True Sustain OFF");
       }
       dprintf("True Sustain: %s\n", truesustain ? "ON" : "OFF");
   }

	} else if (keycode == 0xCCA9) {
	   if (record->event.pressed) {
		   cclooprecording = !cclooprecording;
		   if (cclooprecording) {
			   snprintf(name, sizeof(name),"CC Loop Rec ON");
		   } else {
			   snprintf(name, sizeof(name),"CC Loop Rec OFF");
		   }
		   dprintf("CC REC: %s\n", cclooprecording ? "ON" : "OFF");
	   }
	   
	} else if (keycode == 0xCCAA) {
	   if (record->event.pressed) {
		   channeloverride = !channeloverride;
		   if (channeloverride) {
			   snprintf(name, sizeof(name),"Channel Override ON");
		   } else {
			   snprintf(name, sizeof(name),"Channel Override OFF");
		   }
		   dprintf("Channel Override: %s\n", channeloverride ? "ON" : "OFF");
	   }
	   
	} else if (keycode == 0xCCAB) {
	   if (record->event.pressed) {
		   velocityoverride = !velocityoverride;
		   if (velocityoverride) {
			   snprintf(name, sizeof(name),"Velocity Override ON");
		   } else {
			   snprintf(name, sizeof(name),"Velocity Override OFF");
		   }
		   dprintf("Velocity Override: %s\n", velocityoverride ? "ON" : "OFF");
	   }

	} else if (keycode == 0xCCAC) {
	   if (record->event.pressed) {
		   transposeoverride = !transposeoverride;
		   if (transposeoverride) {
			   snprintf(name, sizeof(name),"Transpose Override ON");
		   } else {
			   snprintf(name, sizeof(name),"Transpose Override OFF");
		   }
		   dprintf("Transpose Override: %s\n", transposeoverride ? "ON" : "OFF");
	   }
	   
		} else if (keycode == 0xCCAD) { // keysplitmodifier
			if (record->event.pressed) {
				uint16_t current_time = timer_read();
				uint16_t time_since_last = timer_elapsed(last_keysplit_press_time);

				if (time_since_last < DOUBLE_TAP_THRESHOLD) {
					// Double tap detected - toggle keysplit bit (0↔1, 2↔3)
					if (keysplitstatus == 0) {
						keysplitstatus = 1;  // Turn on keysplit
					} else if (keysplitstatus == 1) {
						keysplitstatus = 0;  // Turn off keysplit
					} else if (keysplitstatus == 2) {
						keysplitstatus = 3;  // Add keysplit to triplesplit
					} else if (keysplitstatus == 3) {
						keysplitstatus = 2;  // Remove keysplit, keep triplesplit
					}
					snprintf(name, sizeof(name), "KEYSPLIT STATUS %d", keysplitstatus);
				} else {
					// Single press
					snprintf(name, sizeof(name), "KEYSPLIT MODIFIER");
				}

				keysplitmodifierheld = true;
				last_keysplit_press_time = current_time;
			} else {
				// Key released
				if (keysplitmodifierheld) {
					snprintf(name, sizeof(name), "   ");
					keysplitmodifierheld = false;
				}
			}

		} else if (keycode == 0xCCAE) { // triplesplitmodifier
			if (record->event.pressed) {
				uint16_t current_time = timer_read();
				uint16_t time_since_last = timer_elapsed(last_triplesplit_press_time);

				if (time_since_last < DOUBLE_TAP_THRESHOLD) {
					// Double tap detected - toggle triplesplit bit (0↔2, 1↔3)
					if (keysplitstatus == 0) {
						keysplitstatus = 2;  // Turn on triplesplit
					} else if (keysplitstatus == 1) {
						keysplitstatus = 3;  // Add triplesplit to keysplit
					} else if (keysplitstatus == 2) {
						keysplitstatus = 0;  // Turn off triplesplit
					} else if (keysplitstatus == 3) {
						keysplitstatus = 1;  // Remove triplesplit, keep keysplit
					}
					snprintf(name, sizeof(name), "KEYSPLIT STATUS %d", keysplitstatus);
				} else {
					// Single press
					snprintf(name, sizeof(name), "TRIPLESPLIT MODIFIER");
				}

				triplesplitmodifierheld = true;
				last_triplesplit_press_time = current_time;
			} else {
				// Key released
				if (triplesplitmodifierheld) {
					snprintf(name, sizeof(name), "   ");
					triplesplitmodifierheld = false;
				}
			}
	
	} else if (keycode == 0xC458) {
		if (oledkeyboard == 0) {
			oledkeyboard = 12;
			snprintf(name, sizeof(name),"Screenboard 2");
			
		} else if (oledkeyboard == 12) {
			oledkeyboard = 0;
			snprintf(name, sizeof(name),"Screenboard 1");
			}                                     
	
	} else if (keycode == 0xC459) {
		if (smartchordlightmode == 1) {
			smartchordlightmode = 3;
			smartchordlight = 0;
			populate_midi_data();
					//memcpy(keycode_to_led_index, temp_array_0, sizeof(temp_array_0));
			snprintf(name, sizeof(name),"Guide Lights EADGB");
			
		} else if (smartchordlightmode == 3) {
			smartchordlightmode = 4;
			smartchordlight = 0;
			populate_midi_data();
					//memcpy(keycode_to_led_index, temp_array_1, sizeof(temp_array_1));
			snprintf(name, sizeof(name),"Guide Lights ADGBE");

		} else if (smartchordlightmode == 4) {
			smartchordlightmode = 0;
			smartchordlight = 0;
			populate_midi_data();
					//memcpy(keycode_to_led_index, temp_array_0, sizeof(temp_array_0));
			snprintf(name, sizeof(name),"Guide Lights All");
			
		} else if (smartchordlightmode == 0) {
			smartchordlightmode = 2;
			smartchordlight = 3;
			populate_midi_data();
					//memcpy(keycode_to_led_index, temp_array_1, sizeof(temp_array_1));
			snprintf(name, sizeof(name),"Guide Lights Basic");
			
		
		} else if (smartchordlightmode == 2) {
			smartchordlightmode = 1;
			smartchordlight = 2;
			populate_midi_data();
					//memcpy(keycode_to_led_index, temp_array_1, sizeof(temp_array_1));
			snprintf(name, sizeof(name),"Guide Lights Off");
		}			
	
	} else if (keycode >= 0xC438 && keycode <= 0xC447) {
			if (record->event.pressed) {
				oneshotchannel = 1;
				channelplaceholder = channel_number;  // Store the current channel
				channel_number = (keycode - 0xC438);  // Set the MIDI channel temporarily
				snprintf(name, sizeof(name), "Temporary Channel %d", channel_number);
			}
			
	
	
	} else if (keycode >= 0xC448 && keycode <= 0xC457) {
    if (record->event.pressed) {
        channelplaceholder = channel_number;  // Store the current channel
        channel_number = (keycode - 0xC448);  // Set the MIDI channel based on the keycode    
		snprintf(name, sizeof(name), "Hold Channel %d", channel_number);
    } else {
            channel_number = channelplaceholder;  // Restore the previous channel
            channelplaceholder = 0;  // Reset the placeholder
        snprintf(name, sizeof(name), "Channel %d", channel_number);
    }
	
	} else if (keycode == 0xC662) {
		// Cycle: 0→1→2→3→0 (OFF → KS only → TS only → Both)
		if (keysplitstatus == 0) { keysplitstatus = 1;
		snprintf(name, sizeof(name),"KS CHANNEL ON");
		}else if (keysplitstatus == 1) { keysplitstatus = 2;
		snprintf(name, sizeof(name),"TS CHANNEL ON");
		}else if (keysplitstatus == 2) { keysplitstatus = 3;
		snprintf(name, sizeof(name),"KS+TS CHANNEL ON");
		}else if (keysplitstatus == 3) { keysplitstatus = 0;
		snprintf(name, sizeof(name),"SPLIT CHANNEL OFF");
		}
	} else if (keycode == 0xC800) {
		// Cycle: 0→1→2→3→0 (OFF → KS only → TS only → Both)
		if (keysplittransposestatus == 0) { keysplittransposestatus = 1;
		snprintf(name, sizeof(name),"KS TRANSPOSE ON");
		}else if (keysplittransposestatus == 1) { keysplittransposestatus = 2;
		snprintf(name, sizeof(name),"TS TRANSPOSE ON");
		}else if (keysplittransposestatus == 2) { keysplittransposestatus = 3;
		snprintf(name, sizeof(name),"KS+TS TRANSPOSE ON");
		}else if (keysplittransposestatus == 3) { keysplittransposestatus = 0;
		snprintf(name, sizeof(name),"SPLIT TRANSPOSE OFF");
		}
		
	} else if (keycode == 0xC801) {
		// Cycle: 0→1→2→3→0 (OFF → KS only → TS only → Both)
		if (keysplitvelocitystatus == 0) { keysplitvelocitystatus = 1;
		snprintf(name, sizeof(name),"KS VELOCITY ON");
		}else if (keysplitvelocitystatus == 1) { keysplitvelocitystatus = 2;
		snprintf(name, sizeof(name),"TS VELOCITY ON");
		}else if (keysplitvelocitystatus == 2) { keysplitvelocitystatus = 3;
		snprintf(name, sizeof(name),"KS+TS VELOCITY ON");
		}else if (keysplitvelocitystatus == 3) { keysplitvelocitystatus = 0;
		snprintf(name, sizeof(name),"SPLIT VELOCITY OFF");
		}

	} else if (keycode == 0xC650) {
		snprintf(name, sizeof(name), "KeySplit Chan Down");
		if (keysplitchannel == 0) {
            keysplitchannel = 15;
		}
        else {keysplitchannel--;}
		snprintf(name, sizeof(name),"KeySplit Channel Down");

	} else if (keycode == 0xC651) {
		snprintf(name, sizeof(name), "KeySplit Channel Up");
        keysplitchannel++;
		if (keysplitchannel > 15) {
        keysplitchannel = 0;
		}
		snprintf(name, sizeof(name),"KeySplit Channel Up");
		
	} else if (keycode == 0xC6B8) {
		snprintf(name, sizeof(name), "TripleSplit Ch Down");
		if (keysplit2channel == 0) {
            keysplit2channel = 15;
		}
        else {keysplit2channel--;}
		snprintf(name, sizeof(name),"TripleSplit Ch Down");

	} else if (keycode == 0xC6B9) {
		snprintf(name, sizeof(name), "TripleSplit Ch Up");
        keysplit2channel++;
		if (keysplit2channel > 15) {
        keysplit2channel = 0;
		}
		snprintf(name, sizeof(name),"TripleSplit Ch Up");
	
// Channel Down (29059)
} else if (keycode == 29059) { // Channel Down
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        // Normal behavior - affect global channel
        if (channel_number == 0) {
            channel_number = 15;
        } else {
            channel_number--;
        }
        snprintf(name, sizeof(name), "Channel Down");
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_channel_offset_target(i + 1);
                    set_overdub_channel_offset_target(i + 1, current_target - 1);
                }
            }
            snprintf(name, sizeof(name), "Overdub: Channel Down");
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_channel_offset_target(i + 1);
                    set_macro_channel_offset_target(i + 1, current_target - 1);
                }
            }
            snprintf(name, sizeof(name), "Loop: Channel Down");
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect keysplitchannel
        if (keysplitchannel == 0) {
            keysplitchannel = 15;
        } else {
            keysplitchannel--;
        }
        snprintf(name, sizeof(name), "KEYSPLIT CH DOWN");
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect keysplit2channel
        if (keysplit2channel == 0) {
            keysplit2channel = 15;
        } else {
            keysplit2channel--;
        }
        snprintf(name, sizeof(name), "TRIPLESPLIT CH DOWN");
    }
// Channel Up (29060)
} else if (keycode == 29060) { // Channel Up
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        // Normal behavior - affect global channel
        channel_number++;
        if (channel_number > 15) {
            channel_number = 0;
        }
        snprintf(name, sizeof(name), "Channel Up");
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_channel_offset_target(i + 1);
                    set_overdub_channel_offset_target(i + 1, current_target + 1);
                }
            }
            snprintf(name, sizeof(name), "Overdub: Channel Up");
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_channel_offset_target(i + 1);
                    set_macro_channel_offset_target(i + 1, current_target + 1);
                }
            }
            snprintf(name, sizeof(name), "Loop: Channel Up");
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect keysplitchannel
        keysplitchannel++;
        if (keysplitchannel > 15) {
            keysplitchannel = 0;
        }
        snprintf(name, sizeof(name), "KEYSPLIT CH UP");
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect keysplit2channel
        keysplit2channel++;
        if (keysplit2channel > 15) {
            keysplit2channel = 0;
        }
        snprintf(name, sizeof(name), "TRIPLESPLIT CH UP");
    }
		
	} else if (keycode == 0xC4A2) {
		if (colorblindmode == 0) {
            colorblindmode = 1;
			snprintf(name, sizeof(name), "Colorblind On");
        } else if (colorblindmode == 1) {
            colorblindmode = 0;
			snprintf(name, sizeof(name), "Colorblind Off");
		}
		
} else if (keycode >= 0xC420 && keycode <= 0xC425) {	
switch (keycode) {	
		case 0xC420:  snprintf(name, sizeof(name), "SC: Root Position");
		break;
		case 0xC421:  snprintf(name, sizeof(name), "SC: 1st Position");
		break;
		case 0xC422:  snprintf(name, sizeof(name), "SC: 2nd Position");
		break;
		case 0xC423:  snprintf(name, sizeof(name), "SC: 3rd Position");
		break;
		case 0xC424:  snprintf(name, sizeof(name), "SC: 4th Position");
		break;
		case 0xC425:  snprintf(name, sizeof(name), "SC: 5th Position");
		break;
	} 
	
	} else if (keycode >= 0xC38B && keycode <= 0xC416) {
		 switch (keycode) {
		case 0xC38B:    
			snprintf(name, sizeof(name), "Minor Second");
break;
		case 0xC38C:    
			snprintf(name, sizeof(name), "Major Second");
break;
		case 0xC38D:    
			snprintf(name, sizeof(name), "Minor Third");
break;
		case 0xC38E:    
			snprintf(name, sizeof(name), "Major Third");
break;
		case 0xC38F:    
			snprintf(name, sizeof(name), "Tritone");
break;
		case 0xC390:   
			snprintf(name, sizeof(name), "Perfect Fourth");
break;
		case 0xC391:    
			snprintf(name, sizeof(name), "Perfect Fifth");
break;
		case 0xC392:    
			snprintf(name, sizeof(name), "Minor Sixth");
break;
		case 0xC393:   
			snprintf(name, sizeof(name), "Major Sixth");
break;
		case 0xC394:    
			snprintf(name, sizeof(name), "Minor Seventh");
break;
		case 0xC395:    
			snprintf(name, sizeof(name), "Major Seventh");
case 0xC396:    // Major
   snprintf(name, sizeof(name), "Major");
break;

case 0xC397:    // Minor
   snprintf(name, sizeof(name), "Minor");
break;

case 0xC398:    // Diminished
   snprintf(name, sizeof(name), "Diminished");
break;

case 0xC399:    // Augmented
   snprintf(name, sizeof(name), "Augmented"); 
break;

case 0xC39A:    // b5
   snprintf(name, sizeof(name), "b5");
break;

case 0xC39B:    // Sus2
   snprintf(name, sizeof(name), "sus2");
break;

case 0xC39C:    // Sus4
   snprintf(name, sizeof(name), "sus4");
break;

case 0xC39D:    // 7 no 3
   snprintf(name, sizeof(name), "7no3");
break;

case 0xC39E:    // Major 7 no 3
   snprintf(name, sizeof(name), "maj7no3");
break;

case 0xC39F:    // 7 no 5
   snprintf(name, sizeof(name), "7no5");
break;

case 0xC3A0:    // Minor 7 no 5
   snprintf(name, sizeof(name), "m7no5");
break;

case 0xC3A1:    // Major 7 no 5
   snprintf(name, sizeof(name), "maj7no5");
break;

case 0xC3A2:    // Major 6
   snprintf(name, sizeof(name), "6");
break;

case 0xC3A3:    // Minor 6
   snprintf(name, sizeof(name), "m6");
break;

case 0xC3A4:    // Add2
   snprintf(name, sizeof(name), "add2");
break;

case 0xC3A5:    // Minor Add2
   snprintf(name, sizeof(name), "m(add2)");
break;

case 0xC3A6:    // Add4
   snprintf(name, sizeof(name), "add4");
break;

case 0xC3A7:    // Minor Add4
   snprintf(name, sizeof(name), "m(add4)");
break;

case 0xC3A8:    // 7
   snprintf(name, sizeof(name), "7");
break;

case 0xC3A9:    // Major 7
   snprintf(name, sizeof(name), "Maj7");
break;

case 0xC3AA:    // Minor 7
   snprintf(name, sizeof(name), "m7");
break;

case 0xC3AB:    // Minor 7 b5
   snprintf(name, sizeof(name), "m7b5");
break;

case 0xC3AC:    // Diminished 7
   snprintf(name, sizeof(name), "dim7");
break;

case 0xC3AD:    // Minor Major 7
   snprintf(name, sizeof(name), "minMaj7");
break;

case 0xC3AE:    // 7 Sus4
   snprintf(name, sizeof(name), "7sus4");
break;

case 0xC3AF:    // Add9
   snprintf(name, sizeof(name), "add9");
break;

case 0xC3B0:    // Minor Add9
   snprintf(name, sizeof(name), "m(add9)");
break;

case 0xC3B1:    // Add11
   snprintf(name, sizeof(name), "add11");
break;

case 0xC3B2:    // Minor Add11
   snprintf(name, sizeof(name), "m(add11)");
break;

case 0xC3B3:    // 9
   snprintf(name, sizeof(name), "9");
break;

case 0xC3B4:    // Minor 9
   snprintf(name, sizeof(name), "m9");
break;

case 0xC3B5:    // Major 9
   snprintf(name, sizeof(name), "Maj9");
break;

case 0xC3B6:    // 6/9
   snprintf(name, sizeof(name), "6/9");
break;

case 0xC3B7:    // Minor 6/9
   snprintf(name, sizeof(name), "m6/9");
break;

case 0xC3B8:    // 7 b9
   snprintf(name, sizeof(name), "7b9");
break;

case 0xC3B9:    // 7(11)
   snprintf(name, sizeof(name), "7(11)");
break;

case 0xC3BA:    // 7(#11)
   snprintf(name, sizeof(name), "7(#11)");
break;

case 0xC3BB:    // Minor 7(11)
   snprintf(name, sizeof(name), "m7(11)");
break;

case 0xC3BC:    // Major 7(11)
   snprintf(name, sizeof(name), "maj7(11)");
break;

case 0xC3BD:    // Major 7(#11)
   snprintf(name, sizeof(name), "Maj7(#11)");
break;

case 0xC3BE:    // 7(13)
   snprintf(name, sizeof(name), "7(13)");
break;

case 0xC3BF:    // Minor 7(13)
   snprintf(name, sizeof(name), "m7(13)");
break;

case 0xC3C0:    // Major 7(13)
   snprintf(name, sizeof(name), "Maj7(13)");
break;

case 0xC3C1:    // 11
   snprintf(name, sizeof(name), "11");
break;

case 0xC3C2:    // Minor 11
   snprintf(name, sizeof(name), "m11");
break;

case 0xC3C3:    // Major 11
   snprintf(name, sizeof(name), "Maj11");
break;

case 0xC3C4:    // 7(11)(13)
   snprintf(name, sizeof(name), "7(11)(13)");
break;

case 0xC3C5:    // Minor 7(11)(13)
   snprintf(name, sizeof(name), "m7(11)(13)");
break;

case 0xC3C6:    // Major 7(11)(13)
   snprintf(name, sizeof(name), "maj7(11)(13)");
break;

case 0xC3C7:    // 9(13)
   snprintf(name, sizeof(name), "9(13)");
break;

case 0xC3C8:    // Minor 9(13)
   snprintf(name, sizeof(name), "m9(13)");
break;

case 0xC3C9:    // Major 9(13)
   snprintf(name, sizeof(name), "maj9(13)");
break;

case 0xC3CA:    // 13
   snprintf(name, sizeof(name), "13");
break;

case 0xC3CB:    // Minor 13
   snprintf(name, sizeof(name), "m13");
break;

case 0xC3CC:    // Major 13
   snprintf(name, sizeof(name), "Maj13");
break;

case 0xC3CD:    // 7 b9(11)
   snprintf(name, sizeof(name), "7b9(11)");
break;

case 0xC3CE:    // 7 Sus2
   snprintf(name, sizeof(name), "7sus2");
break;

case 0xC3CF:    // 7 #5
   snprintf(name, sizeof(name), "7#5");
break;

case 0xC3D0:    // 7 b5
   snprintf(name, sizeof(name), "7b5");
break;

case 0xC3D1:    // 7 #9
   snprintf(name, sizeof(name), "7#9");
break;

case 0xC3D2:    // 7 b5 b9
   snprintf(name, sizeof(name), "7b5b9");
break;

case 0xC3D3:    // 7 b5 #9
   snprintf(name, sizeof(name), "7b5#9");
break;

case 0xC3D4:    // 7 b9(13)
   snprintf(name, sizeof(name), "7b9(13)");
break;

case 0xC3D5:    // 7 #9(13)
   snprintf(name, sizeof(name), "7#9(13)");
break;

case 0xC3D6:    // 7 #5 b9
   snprintf(name, sizeof(name), "7#5b9");
break;

case 0xC3D7:    // 7 #5 #9
   snprintf(name, sizeof(name), "7#5#9");
break;

case 0xC3D8:    // 7 b5(11)
   snprintf(name, sizeof(name), "7b5(11)");
break;

case 0xC3D9:    // Major 7 Sus4
   snprintf(name, sizeof(name), "maj7sus4");
break;

case 0xC3DA:    // Major 7 #5
   snprintf(name, sizeof(name), "maj7#5");
break;

case 0xC3DB:    // Major 7 b5
   snprintf(name, sizeof(name), "maj7b5");
break;

case 0xC3DC:    // Minor Major 7(11)
   snprintf(name, sizeof(name), "minMaj7(11)");
break;

case 0xC3DD:    // Add b5
   snprintf(name, sizeof(name), "(addb5)");
break;

case 0xC3DE:    // 9 #11
   snprintf(name, sizeof(name), "9#11");
break;

case 0xC3DF:    // 9 b5
   snprintf(name, sizeof(name), "9b5");
break;

case 0xC3E0:    // 9 #5
   snprintf(name, sizeof(name), "9#5");
break;

case 0xC3E1:    // Minor 9 b5
   snprintf(name, sizeof(name), "m9b5");
break;

case 0xC3E2:    // Minor 9 #11
   snprintf(name, sizeof(name), "m9#11");
break;

case 0xC3E3:    // 9 Sus4
   snprintf(name, sizeof(name), "9sus4");
break;

case 0xC3FB:    // Major(Ionian)
    snprintf(name, sizeof(name), "Major(Ionian)");
break;

case 0xC3FC:    // Dorian
    snprintf(name, sizeof(name), "Dorian");
break;

case 0xC3FD:    // Phrygian
    snprintf(name, sizeof(name), "Phrygian");
break;

case 0xC3FE:    // Lydian
    snprintf(name, sizeof(name), "Lydian");
break;

case 0xC3FF:    // Mixolydian
    snprintf(name, sizeof(name), "Mixolydian");
break;

case 0xC400:    // Minor(Aeolian)
    snprintf(name, sizeof(name), "Minor(Aeolian)");
break;

case 0xC401:    // Locrian
    snprintf(name, sizeof(name), "Locrian");
break;

case 0xC402:    // Melodic Minor
    snprintf(name, sizeof(name), "Melodic Minor");
break;

case 0xC403:    // Lydian Dominant
    snprintf(name, sizeof(name), "Lydian Dominant");
break;

case 0xC404:    // Altered Scale
    snprintf(name, sizeof(name), "Altered Scale");
break;

case 0xC405:    // Harmonic Minor
    snprintf(name, sizeof(name), "Harmonic Minor");
break;

case 0xC406:    // Major Pentatonic
    snprintf(name, sizeof(name), "Major Pentatonic");
break;

case 0xC407:    // Minor Pentatonic
    snprintf(name, sizeof(name), "Minor Pentatonic");
break;

case 0xC408:    // Whole Tone
    snprintf(name, sizeof(name), "Whole Tone");
break;

case 0xC409:    // Diminished
    snprintf(name, sizeof(name), "Diminished");
break;

case 0xC40A:    // Blues
    snprintf(name, sizeof(name), "Blues");
break;
		 }
			
} else if (keycode >= 0xC460 && keycode <= 0xC49F) {
    switch (keycode) {
        case 0xC460:    // RGB MATRIX NONE
            rgb_matrix_mode(RGB_MATRIX_NONE);
            snprintf(name, sizeof(name), "RGB None");
            break;

        case 0xC461:    // RGB MATRIX SOLID COLOR
            rgb_matrix_mode(RGB_MATRIX_SOLID_COLOR);
            snprintf(name, sizeof(name), "RGB Solid Color");
            break;

        case 0xC462:    // RGB MATRIX ALPHAS MODS
            rgb_matrix_mode(RGB_MATRIX_ALPHAS_MODS);
            snprintf(name, sizeof(name), "RGB Alphas Mods");
            break;

        case 0xC463:    // RGB MATRIX GRADIENT UP DOWN
            rgb_matrix_mode(RGB_MATRIX_GRADIENT_UP_DOWN);
            snprintf(name, sizeof(name), "RGB Gradient Up Down");
            break;

        case 0xC464:    // RGB MATRIX GRADIENT LEFT RIGHT
            rgb_matrix_mode(RGB_MATRIX_GRADIENT_LEFT_RIGHT);
            snprintf(name, sizeof(name), "RGB Gradient Left Right");
            break;

        case 0xC465:    // RGB MATRIX BREATHING
            rgb_matrix_mode(RGB_MATRIX_BREATHING);
            snprintf(name, sizeof(name), "RGB Breathing");
            break;

        case 0xC466:    // RGB MATRIX BAND SAT
            rgb_matrix_mode(RGB_MATRIX_BAND_SAT);
            snprintf(name, sizeof(name), "RGB Band Sat");
            break;

        case 0xC467:    // RGB MATRIX BAND VAL
            rgb_matrix_mode(RGB_MATRIX_BAND_VAL);
            snprintf(name, sizeof(name), "RGB Band Val");
            break;

        case 0xC468:    // RGB MATRIX BAND PINWHEEL SAT
            rgb_matrix_mode(RGB_MATRIX_BAND_PINWHEEL_SAT);
            snprintf(name, sizeof(name), "RGB Band Pinwheel Sat");
            break;

        case 0xC469:    // RGB MATRIX BAND PINWHEEL VAL
            rgb_matrix_mode(RGB_MATRIX_BAND_PINWHEEL_VAL);
            snprintf(name, sizeof(name), "RGB Band Pinwheel Val");
            break;

        case 0xC46A:    // RGB MATRIX BAND SPIRAL SAT
            rgb_matrix_mode(RGB_MATRIX_BAND_SPIRAL_SAT);
            snprintf(name, sizeof(name), "RGB Band Spiral Sat");
            break;

        case 0xC46B:    // RGB MATRIX BAND SPIRAL VAL
            rgb_matrix_mode(RGB_MATRIX_BAND_SPIRAL_VAL);
            snprintf(name, sizeof(name), "RGB Band Spiral Val");
            break;

        case 0xC46C:    // RGB MATRIX CYCLE ALL
            rgb_matrix_mode(RGB_MATRIX_CYCLE_ALL);
            snprintf(name, sizeof(name), "RGB Cycle All");
            break;

        case 0xC46D:    // RGB MATRIX CYCLE LEFT RIGHT
            rgb_matrix_mode(RGB_MATRIX_CYCLE_LEFT_RIGHT);
            snprintf(name, sizeof(name), "RGB Cycle Left Right");
            break;

        case 0xC46E:    // RGB MATRIX CYCLE UP DOWN
            rgb_matrix_mode(RGB_MATRIX_CYCLE_UP_DOWN);
            snprintf(name, sizeof(name), "RGB Cycle Up Down");
            break;

        case 0xC46F:    // RGB MATRIX CYCLE OUT IN
            rgb_matrix_mode(RGB_MATRIX_CYCLE_OUT_IN);
            snprintf(name, sizeof(name), "RGB Cycle Out In");
            break;

        case 0xC470:    // RGB MATRIX CYCLE OUT IN DUAL
            rgb_matrix_mode(RGB_MATRIX_CYCLE_OUT_IN_DUAL);
            snprintf(name, sizeof(name), "RGB Cycle Out In Dual");
            break;

        case 0xC471:    // RGB MATRIX RAINBOW MOVING CHEVRON
            rgb_matrix_mode(RGB_MATRIX_RAINBOW_MOVING_CHEVRON);
            snprintf(name, sizeof(name), "RGB Rainbow Chevron");
            break;

        case 0xC472:    // RGB MATRIX CYCLE PINWHEEL
            rgb_matrix_mode(RGB_MATRIX_CYCLE_PINWHEEL);
            snprintf(name, sizeof(name), "RGB Cycle Pinwheel");
            break;

        case 0xC473:    // RGB MATRIX CYCLE SPIRAL
            rgb_matrix_mode(RGB_MATRIX_CYCLE_SPIRAL);
            snprintf(name, sizeof(name), "RGB Cycle Spiral");
            break;

        case 0xC474:    // RGB MATRIX DUAL BEACON
            rgb_matrix_mode(RGB_MATRIX_DUAL_BEACON);
            snprintf(name, sizeof(name), "RGB Dual Beacon");
            break;

        case 0xC475:    // RGB MATRIX RAINBOW BEACON
            rgb_matrix_mode(RGB_MATRIX_RAINBOW_BEACON);
            snprintf(name, sizeof(name), "RGB Rainbow Beacon");
            break;

        case 0xC476:    // RGB MATRIX RAINBOW PINWHEELS
            rgb_matrix_mode(RGB_MATRIX_RAINBOW_PINWHEELS);
            snprintf(name, sizeof(name), "RGB Rainbow Pinwheels");
            break;

        case 0xC477:    // RGB MATRIX RAINDROPS
            rgb_matrix_mode(RGB_MATRIX_RAINDROPS);
            snprintf(name, sizeof(name), "RGB Raindrops");
            break;

        case 0xC478:    // RGB MATRIX JELLYBEAN RAINDROPS
            rgb_matrix_mode(RGB_MATRIX_JELLYBEAN_RAINDROPS);
            snprintf(name, sizeof(name), "RGB Jellybean Raindrops");
            break;

        case 0xC479:    // RGB MATRIX HUE BREATHING
            rgb_matrix_mode(RGB_MATRIX_HUE_BREATHING);
            snprintf(name, sizeof(name), "RGB Hue Breathing");
            break;

        case 0xC47A:    // RGB MATRIX HUE PENDULUM
            rgb_matrix_mode(RGB_MATRIX_HUE_PENDULUM);
            snprintf(name, sizeof(name), "RGB Hue Pendulum");
            break;

        case 0xC47B:    // RGB MATRIX HUE WAVE
            rgb_matrix_mode(RGB_MATRIX_HUE_WAVE);
            snprintf(name, sizeof(name), "RGB Hue Wave");
            break;

        case 0xC47C:    // RGB MATRIX PIXEL FRACTAL
            rgb_matrix_mode(RGB_MATRIX_PIXEL_FRACTAL);
            snprintf(name, sizeof(name), "RGB Pixel Fractal");
            break;

        case 0xC47D:    // RGB MATRIX PIXEL FLOW
            rgb_matrix_mode(RGB_MATRIX_PIXEL_FLOW);
            snprintf(name, sizeof(name), "RGB Pixel Flow");
            break;

        case 0xC47E:    // RGB MATRIX PIXEL RAIN
            rgb_matrix_mode(RGB_MATRIX_PIXEL_RAIN);
            snprintf(name, sizeof(name), "RGB Pixel Rain");
            break;
			
        case 0xC47F:    // RGB MATRIX TYPING HEATMAP
            rgb_matrix_mode(RGB_MATRIX_TYPING_HEATMAP);
            snprintf(name, sizeof(name), "RGB Typing Heatmap");
            break;

        case 0xC480:    // RGB MATRIX DIGITAL RAIN
            rgb_matrix_mode(RGB_MATRIX_DIGITAL_RAIN);
            snprintf(name, sizeof(name), "RGB Digital Rain");
            break;

        case 0xC481:    // RGB MATRIX SOLID REACTIVE SIMPLE
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_SIMPLE);
            snprintf(name, sizeof(name), "RGB Solid Reactive Simple");
            break;

        case 0xC482:    // RGB MATRIX SOLID REACTIVE
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE);
            snprintf(name, sizeof(name), "RGB Solid Reactive");
            break;

        case 0xC483:    // RGB MATRIX SOLID REACTIVE WIDE
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_WIDE);
            snprintf(name, sizeof(name), "RGB Solid Reactive Wide");
            break;

        case 0xC484:    // RGB MATRIX SOLID REACTIVE MULTIWIDE
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_MULTIWIDE);
            snprintf(name, sizeof(name), "RGB Solid Reactive Multiwide");
            break;

        case 0xC485:    // RGB MATRIX SOLID REACTIVE CROSS
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_CROSS);
            snprintf(name, sizeof(name), "RGB Solid Reactive Cross");
            break;

        case 0xC486:    // RGB MATRIX SOLID REACTIVE MULTICROSS
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_MULTICROSS);
            snprintf(name, sizeof(name), "RGB Solid Reactive Multicross");
            break;

        case 0xC487:    // RGB MATRIX SOLID REACTIVE NEXUS
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_NEXUS);
            snprintf(name, sizeof(name), "RGB Solid Reactive Nexus");
            break;

        case 0xC488:    // RGB MATRIX SOLID REACTIVE MULTINEXUS
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_MULTINEXUS);
            snprintf(name, sizeof(name), "RGB Solid Reactive Multinexus");
            break;

        case 0xC489:    // RGB MATRIX SPLASH
            rgb_matrix_mode(RGB_MATRIX_SPLASH);
            snprintf(name, sizeof(name), "RGB Splash");
            break;

        case 0xC48A:    // RGB MATRIX MULTISPLASH
            rgb_matrix_mode(RGB_MATRIX_MULTISPLASH);
            snprintf(name, sizeof(name), "RGB Multisplash");
            break;

        case 0xC48B:    // RGB MATRIX SOLID SPLASH
            rgb_matrix_mode(RGB_MATRIX_SOLID_SPLASH);
            snprintf(name, sizeof(name), "RGB Solid Splash");
            break;

        case 0xC48C:    // RGB MATRIX SOLID MULTISPLASH
            rgb_matrix_mode(RGB_MATRIX_SOLID_MULTISPLASH);
            snprintf(name, sizeof(name), "RGB Solid Multisplash");
            break;

        case 0xC48D:    // RGB AZURE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_AZURE);
            snprintf(name, sizeof(name), "RGB Azure");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC48E:    // RGB BLACK / RGB OFF
            rgb_matrix_set_color_all(RGB_OFF);
            rgb_matrix_sethsv(RGB_OFF);
            snprintf(name, sizeof(name), "RGB OFF");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC48F:    // RGB BLUE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_BLUE);
            snprintf(name, sizeof(name), "RGB Blue");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC490:    // RGB CHARTREUSE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_CHARTREUSE);
            snprintf(name, sizeof(name), "RGB Chartreuse");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC491:    // RGB CORAL
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_CORAL);
            snprintf(name, sizeof(name), "RGB Coral");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC492:    // RGB CYAN
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_CYAN);
            snprintf(name, sizeof(name), "RGB Cyan");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC493:    // RGB GOLD
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_GOLD);
            snprintf(name, sizeof(name), "RGB Gold");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC494:    // RGB GOLDENROD
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_GOLDENROD);
            snprintf(name, sizeof(name), "RGB Goldenrod");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC495:    // RGB GREEN
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_GREEN);
            snprintf(name, sizeof(name), "RGB Green");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC496:    // RGB MAGENTA
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_MAGENTA);
            snprintf(name, sizeof(name), "RGB Magenta");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC497:    // RGB ORANGE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_ORANGE);
            snprintf(name, sizeof(name), "RGB Orange");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC498:    // RGB PINK
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_PINK);
            snprintf(name, sizeof(name), "RGB Pink");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC499:    // RGB PURPLE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_PURPLE);
            snprintf(name, sizeof(name), "RGB Purple");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49A:    // RGB RED
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_RED);
            snprintf(name, sizeof(name), "RGB Red");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49B:    // RGB SPRINGGREEN
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_SPRINGGREEN);
            snprintf(name, sizeof(name), "RGB Springgreen");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49C:    // RGB TEAL
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_TEAL);
            snprintf(name, sizeof(name), "RGB Teal");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49D:    // RGB TURQUOISE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_TURQUOISE);
            snprintf(name, sizeof(name), "RGB Turquoise");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49E:    // RGB WHITE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_WHITE);
            snprintf(name, sizeof(name), "RGB White");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49F:    // RGB YELLOW
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_YELLOW);
            snprintf(name, sizeof(name), "RGB Yellow");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;
    }

	// MIDI Routing Toggle Keycodes
	if (keycode == MIDI_IN_MODE_TOG) {
		snprintf(name, sizeof(name), "MIDI IN: %s", midi_in_mode_names[midi_in_mode]);
	} else if (keycode == USB_MIDI_MODE_TOG) {
		snprintf(name, sizeof(name), "USB MIDI: %s", usb_midi_mode_names[usb_midi_mode]);
	} else if (keycode == MIDI_CLOCK_SRC_TOG) {
		snprintf(name, sizeof(name), "CLOCK: %s", clock_source_names[midi_clock_source]);
	}
	
	} else  if (keycode == 0x7185) {
        // Clear all trueheldkey variables
        trueheldkey1 = 0;
        trueheldkey2 = 0;
        trueheldkey3 = 0;
        trueheldkey4 = 0;
        trueheldkey5 = 0;
        trueheldkey6 = 0;
        trueheldkey7 = 0;
        
        // Clear all trueoctaveheldkey variables
        trueoctaveheldkey1 = 0;
        trueoctaveheldkey2 = 0;
        trueoctaveheldkey3 = 0;
        trueoctaveheldkey4 = 0;
        
        // Clear all corresponding heldkey variables
        heldkey1 = 0;
        heldkey2 = 0;
        heldkey3 = 0;
        heldkey4 = 0;
        heldkey5 = 0;
        heldkey6 = 0;
        heldkey7 = 0;
        
        // Clear all octaveheldkey variables
        octaveheldkey1 = 0;
        octaveheldkey2 = 0;
        octaveheldkey3 = 0;
        octaveheldkey4 = 0;
        
        // Clear all difference variables
        heldkey1difference = 0;
        heldkey2difference = 0;
        heldkey3difference = 0;
        heldkey4difference = 0;
        heldkey5difference = 0;
        heldkey6difference = 0;
        heldkey7difference = 0;
        
        octaveheldkey1difference = 0;
        octaveheldkey2difference = 0;
        octaveheldkey3difference = 0;
        octaveheldkey4difference = 0;
		
		noteoffdisplayupdates(1);
		snprintf(name, sizeof(name), "All notes cleared");
		
} else if (keycode >= 29003 && keycode <= 29012) {
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        octave_number = (keycode - 29005)*12;
        snprintf(name, sizeof(name), "OCTAVE %+d", keycode - 29005);
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            int8_t transpose_change = (keycode - 29005) * 12; // -6 to +6 octaves
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    set_overdub_transpose_target(i + 1, transpose_change);
                }
            }
            snprintf(name, sizeof(name), "Overdub Octave %+d", transpose_change / 12);
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            int8_t transpose_change = (keycode - 29005) * 12; // -6 to +6 octaves
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    set_macro_transpose_target(i + 1, transpose_change);
                }
            }
            snprintf(name, sizeof(name), "Loop Octave %+d", transpose_change / 12);
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect octave_number2
        octave_number2 = (keycode - 29005)*12;
        snprintf(name, sizeof(name), "KEYSPLIT OCTAVE %+d", keycode - 29005);
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect octave_number3
        octave_number3 = (keycode - 29005)*12;
        snprintf(name, sizeof(name), "TRIPLESPLIT OCTAVE %+d", keycode - 29005);
    } 
}else if (keycode >= 0xC750 && keycode <= 0xC759) {
		octave_number2 = (keycode - 0xC750 - 2)*12;  // Adjusting for the range -6 to +6
        snprintf(name, sizeof(name), "KS OCTAVE %+d", keycode - 0xC750 - 2);
		
	} else if (keycode >= 0xC802 && keycode <= 0xC80B) {
		octave_number3 = (keycode - 0xC802 - 2)*12;  // Adjusting for the range -6 to +6
        snprintf(name, sizeof(name), "TS OCTAVE %+d", keycode - 0xC802 - 2);
		
	} else if (keycode >= 0xC80C && keycode <= 0xC81B) {
        // Update cc_sensitivity value based on the key
        cc_sensitivity = keycode - 0xC80B;  // Assuming the keycodes are consecutive
	    snprintf(name, sizeof(name), "CC INTERVAL %d", keycode - 0xC80B);
		
	} else if (keycode >= 50220 && keycode <= 50229) {
        // Update cc_sensitivity value based on the key
        velocity_sensitivity = keycode - 50219;  // Assuming the keycodes are consecutive
	    snprintf(name, sizeof(name), "VELOCITY INTERVAL %d", keycode - 50219);	
	
} else if (keycode >= 29015 && keycode <= 29027) {
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        transpose_number = keycode - 29015 - 6;
        snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            int8_t transpose_change = keycode - 29015 - 6; // -6 to +6 semitones
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    set_overdub_transpose_target(i + 1, transpose_change);
                }
            }
            snprintf(name, sizeof(name), "Overdub Transpose %+d", transpose_change);
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            int8_t transpose_change = keycode - 29015 - 6; // -6 to +6 semitones
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    set_macro_transpose_target(i + 1, transpose_change);
                }
            }
            snprintf(name, sizeof(name), "Loop Transpose %+d", transpose_change);
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect transpose_number2
        transpose_number2 = keycode - 29015 - 6;
        snprintf(name, sizeof(name), "KEYSPLIT %s", majorminor_note_names[transpose_number2 + 29]);
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect transpose_number3
        transpose_number3 = keycode - 29015 - 6;
        snprintf(name, sizeof(name), "TRIPLESPLIT %s", majorminor_note_names[transpose_number3 + 29]);
		}
} else if (keycode >= 0xC75A && keycode <= 0xC765) {
        // Handle special keycodes within the range
        // Update the special number based on the keycode
        transpose_number2 = keycode - 0xC75A - 5;  // Adjusting for the range -6 to +6
	    snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);
		
	} else if (keycode >= 0xC766 && keycode <= 0xC771) {
        // Handle special keycodes within the range
        // Update the special number based on the keycode
        transpose_number3 = keycode - 0xC766 - 5;  // Adjusting for the range -6 to +6
	    snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number3 + 29]);
		
// Transpose Up (29028)
} else if (keycode == 29028) {
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        snprintf(name, sizeof(name), "TRANSPOSE UP");
        transpose_number--;
        snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current = get_overdub_transpose_target(i + 1);
                    set_overdub_transpose_target(i + 1, current - 1);
                }
            }
            snprintf(name, sizeof(name), "Overdub Transpose Down");
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current = get_macro_transpose_target(i + 1);
                    set_macro_transpose_target(i + 1, current - 1);
                }
            }
            snprintf(name, sizeof(name), "Loop Transpose Down");
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect transpose_number2
        transpose_number2--;
        snprintf(name, sizeof(name), "KEYSPLIT TRANSPOSE UP");
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect transpose_number3
        transpose_number3--;
        snprintf(name, sizeof(name), "TRIPLESPLIT TRANSPOSE UP");
    }

// Transpose Down (29029)
} else if (keycode == 29029) {
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        snprintf(name, sizeof(name), "TRANSPOSE DOWN");
        transpose_number++;
        snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current = get_overdub_transpose_target(i + 1);
                    set_overdub_transpose_target(i + 1, current + 1);
                }
            }
            snprintf(name, sizeof(name), "Overdub Transpose Up");
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current = get_macro_transpose_target(i + 1);
                    set_macro_transpose_target(i + 1, current + 1);
                }
            }
            snprintf(name, sizeof(name), "Loop Transpose Up");
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect transpose_number2
        transpose_number2++;
        snprintf(name, sizeof(name), "KEYSPLIT TRANSPOSE DOWN");
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect transpose_number3
        transpose_number3++;
        snprintf(name, sizeof(name), "TRIPLESPLIT TRANSPOSE DOWN");
    }
		
	} else if (keycode == 0xC74C) {
		snprintf(name, sizeof(name), "KS TRANSPOSE UP");
        // Decrease the special number by 1
        transpose_number2++;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);

    } else if (keycode == 0xC74D) {
	snprintf(name, sizeof(name), "KS TRANSPOSE DOWN");
        // Decrease the special number by 1
        transpose_number2--;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);
		
	} else if (keycode == 0xC7FC) {
		snprintf(name, sizeof(name), "TS TRANSPOSE UP");
        // Decrease the special number by 1
        transpose_number3++;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);

    } else if (keycode == 0xC7FD) {
	snprintf(name, sizeof(name), "TS TRANSPOSE DOWN");
        // Decrease the special number by 1
        transpose_number3--;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);
		
	} else if (keycode == 0xC4A3) {
		if (smartchordlight == 3) {
            smartchordlight = 0;
			snprintf(name, sizeof(name), "Smartchord Lights On");
        } else if ( smartchordlight != 3) {
            smartchordlight = 3;
			snprintf(name, sizeof(name), "Smartchord Lights Off");
			}
		

} else if (keycode == 0xC436){ // Velocity Up
    // Check if any sequencer modifier is held
    bool any_seq_mod_held = false;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_modifier_held[i]) {
            int16_t new_min = seq_state[i].locked_velocity_min + velocity_sensitivity;
            int16_t new_max = seq_state[i].locked_velocity_max + velocity_sensitivity;

            // Clamp to valid range
            if (new_min > 127) new_min = 127;
            if (new_max > 127) new_max = 127;

            // Check if we can move both without violating dynamic_range
            int16_t current_range = seq_state[i].locked_velocity_max - seq_state[i].locked_velocity_min;

            if (current_range >= dynamic_range) {
                // Current range meets or exceeds dynamic_range, move both
                seq_state[i].locked_velocity_min = (uint8_t)new_min;
                seq_state[i].locked_velocity_max = (uint8_t)new_max;
            } else {
                // Current range is less than dynamic_range, only move min
                seq_state[i].locked_velocity_min = (uint8_t)new_min;
                if (seq_state[i].locked_velocity_min > seq_state[i].locked_velocity_max) {
                    seq_state[i].locked_velocity_max = seq_state[i].locked_velocity_min;
                }
            }

            snprintf(name, sizeof(name), "Seq %d VEL %d-%d", i + 1, seq_state[i].locked_velocity_min, seq_state[i].locked_velocity_max);
            any_seq_mod_held = true;
        }
    }

    if (!any_seq_mod_held && !is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        // Normal behavior - affect HE velocity min/max ranges
        int16_t new_min = he_velocity_min + velocity_sensitivity;
        int16_t new_max = he_velocity_max + velocity_sensitivity;

        // Clamp to valid range
        if (new_min > 127) new_min = 127;
        if (new_max > 127) new_max = 127;

        // Check if we can move both without violating dynamic_range
        int16_t current_range = he_velocity_max - he_velocity_min;

        if (current_range >= dynamic_range) {
            // Current range meets or exceeds dynamic_range, move both
            he_velocity_min = (uint8_t)new_min;
            he_velocity_max = (uint8_t)new_max;
        } else {
            // Current range is less than dynamic_range, only move min
            he_velocity_min = (uint8_t)new_min;
            if (he_velocity_min > he_velocity_max) {
                he_velocity_max = he_velocity_min;
            }
        }

        snprintf(name, sizeof(name), "VEL %d-%d", he_velocity_min, he_velocity_max);
    } else if (!any_seq_mod_held && keysplitmodifierheld && !is_any_macro_modifier_active() && !triplesplitmodifierheld) {
        // Keysplit modifier held - affect keysplit velocity ranges
        int16_t new_min = keysplit_he_velocity_min + velocity_sensitivity;
        int16_t new_max = keysplit_he_velocity_max + velocity_sensitivity;

        // Clamp to valid range
        if (new_min > 127) new_min = 127;
        if (new_max > 127) new_max = 127;

        // Check if we can move both without violating dynamic_range
        int16_t current_range = keysplit_he_velocity_max - keysplit_he_velocity_min;

        if (current_range >= dynamic_range) {
            // Current range meets or exceeds dynamic_range, move both
            keysplit_he_velocity_min = (uint8_t)new_min;
            keysplit_he_velocity_max = (uint8_t)new_max;
        } else {
            // Current range is less than dynamic_range, only move min
            keysplit_he_velocity_min = (uint8_t)new_min;
            if (keysplit_he_velocity_min > keysplit_he_velocity_max) {
                keysplit_he_velocity_max = keysplit_he_velocity_min;
            }
        }

        snprintf(name, sizeof(name), "KS VEL %d-%d", keysplit_he_velocity_min, keysplit_he_velocity_max);
    } else if (!any_seq_mod_held && triplesplitmodifierheld && !is_any_macro_modifier_active() && !keysplitmodifierheld) {
        // Triplesplit modifier held - affect triplesplit velocity ranges
        int16_t new_min = triplesplit_he_velocity_min + velocity_sensitivity;
        int16_t new_max = triplesplit_he_velocity_max + velocity_sensitivity;

        // Clamp to valid range
        if (new_min > 127) new_min = 127;
        if (new_max > 127) new_max = 127;

        // Check if we can move both without violating dynamic_range
        int16_t current_range = triplesplit_he_velocity_max - triplesplit_he_velocity_min;

        if (current_range >= dynamic_range) {
            // Current range meets or exceeds dynamic_range, move both
            triplesplit_he_velocity_min = (uint8_t)new_min;
            triplesplit_he_velocity_max = (uint8_t)new_max;
        } else {
            // Current range is less than dynamic_range, only move min
            triplesplit_he_velocity_min = (uint8_t)new_min;
            if (triplesplit_he_velocity_min > triplesplit_he_velocity_max) {
                triplesplit_he_velocity_max = triplesplit_he_velocity_min;
            }
        }

        snprintf(name, sizeof(name), "TS VEL %d-%d", triplesplit_he_velocity_min, triplesplit_he_velocity_max);
    } else if (!any_seq_mod_held && is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_velocity_offset_target(i + 1);
                    set_overdub_velocity_offset_target(i + 1, current_target + velocity_sensitivity);
                }
            }
            snprintf(name, sizeof(name), "Overdub Velocity Up");
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_velocity_offset_target(i + 1);
                    set_macro_velocity_offset_target(i + 1, current_target + velocity_sensitivity);
                }
            }
            snprintf(name, sizeof(name), "Loop Velocity Up");
        }
    }

// Velocity Down (0xC437)
} else if (keycode == 0xC437){ // Velocity Down
    // Check if any sequencer modifier is held
    bool any_seq_mod_held = false;
    for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
        if (seq_modifier_held[i]) {
            int16_t new_min = seq_state[i].locked_velocity_min - velocity_sensitivity;
            int16_t new_max = seq_state[i].locked_velocity_max - velocity_sensitivity;

            // Clamp to valid range
            if (new_min < 0) new_min = 0;
            if (new_max < 0) new_max = 0;

            // Check if we can move both without violating dynamic_range
            int16_t current_range = seq_state[i].locked_velocity_max - seq_state[i].locked_velocity_min;

            if (current_range >= dynamic_range) {
                // Current range meets or exceeds dynamic_range, move both
                seq_state[i].locked_velocity_min = (uint8_t)new_min;
                seq_state[i].locked_velocity_max = (uint8_t)new_max;
            } else {
                // Current range is less than dynamic_range, only move max
                seq_state[i].locked_velocity_max = (uint8_t)new_max;
                if (seq_state[i].locked_velocity_max < seq_state[i].locked_velocity_min) {
                    seq_state[i].locked_velocity_min = seq_state[i].locked_velocity_max;
                }
            }

            snprintf(name, sizeof(name), "Seq %d VEL %d-%d", i + 1, seq_state[i].locked_velocity_min, seq_state[i].locked_velocity_max);
            any_seq_mod_held = true;
        }
    }

    if (!any_seq_mod_held && !is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        // Normal behavior - affect HE velocity min/max ranges
        int16_t new_min = he_velocity_min - velocity_sensitivity;
        int16_t new_max = he_velocity_max - velocity_sensitivity;

        // Clamp to valid range
        if (new_min < 0) new_min = 0;
        if (new_max < 0) new_max = 0;

        // Check if we can move both without violating dynamic_range
        int16_t current_range = he_velocity_max - he_velocity_min;

        if (current_range >= dynamic_range) {
            // Current range meets or exceeds dynamic_range, move both
            he_velocity_min = (uint8_t)new_min;
            he_velocity_max = (uint8_t)new_max;
        } else {
            // Current range is less than dynamic_range, only move max
            he_velocity_max = (uint8_t)new_max;
            if (he_velocity_max < he_velocity_min) {
                he_velocity_min = he_velocity_max;
            }
        }

        snprintf(name, sizeof(name), "VEL %d-%d", he_velocity_min, he_velocity_max);
    } else if (!any_seq_mod_held && keysplitmodifierheld && !is_any_macro_modifier_active() && !triplesplitmodifierheld) {
        // Keysplit modifier held - affect keysplit velocity ranges
        int16_t new_min = keysplit_he_velocity_min - velocity_sensitivity;
        int16_t new_max = keysplit_he_velocity_max - velocity_sensitivity;

        // Clamp to valid range
        if (new_min < 0) new_min = 0;
        if (new_max < 0) new_max = 0;

        // Check if we can move both without violating dynamic_range
        int16_t current_range = keysplit_he_velocity_max - keysplit_he_velocity_min;

        if (current_range >= dynamic_range) {
            // Current range meets or exceeds dynamic_range, move both
            keysplit_he_velocity_min = (uint8_t)new_min;
            keysplit_he_velocity_max = (uint8_t)new_max;
        } else {
            // Current range is less than dynamic_range, only move max
            keysplit_he_velocity_max = (uint8_t)new_max;
            if (keysplit_he_velocity_max < keysplit_he_velocity_min) {
                keysplit_he_velocity_min = keysplit_he_velocity_max;
            }
        }

        snprintf(name, sizeof(name), "KS VEL %d-%d", keysplit_he_velocity_min, keysplit_he_velocity_max);
    } else if (!any_seq_mod_held && triplesplitmodifierheld && !is_any_macro_modifier_active() && !keysplitmodifierheld) {
        // Triplesplit modifier held - affect triplesplit velocity ranges
        int16_t new_min = triplesplit_he_velocity_min - velocity_sensitivity;
        int16_t new_max = triplesplit_he_velocity_max - velocity_sensitivity;

        // Clamp to valid range
        if (new_min < 0) new_min = 0;
        if (new_max < 0) new_max = 0;

        // Check if we can move both without violating dynamic_range
        int16_t current_range = triplesplit_he_velocity_max - triplesplit_he_velocity_min;

        if (current_range >= dynamic_range) {
            // Current range meets or exceeds dynamic_range, move both
            triplesplit_he_velocity_min = (uint8_t)new_min;
            triplesplit_he_velocity_max = (uint8_t)new_max;
        } else {
            // Current range is less than dynamic_range, only move max
            triplesplit_he_velocity_max = (uint8_t)new_max;
            if (triplesplit_he_velocity_max < triplesplit_he_velocity_min) {
                triplesplit_he_velocity_min = triplesplit_he_velocity_max;
            }
        }

        snprintf(name, sizeof(name), "TS VEL %d-%d", triplesplit_he_velocity_min, triplesplit_he_velocity_max);
    } else if (!any_seq_mod_held && is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_velocity_offset_target(i + 1);
                    set_overdub_velocity_offset_target(i + 1, current_target - velocity_sensitivity);
                }
            }
            snprintf(name, sizeof(name), "Overdub Velocity Down");
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_velocity_offset_target(i + 1);
                    set_macro_velocity_offset_target(i + 1, current_target - velocity_sensitivity);
                }
            }
            snprintf(name, sizeof(name), "Loop Velocity Down");
        }
    }

	} else if (keycode == 0xC74A){
		 snprintf(name, sizeof(name), "KS VELOCITY UP (deprecated)");

    } else if (keycode == 0xC74B){
		 snprintf(name, sizeof(name), "KS VELOCITY DOWN (deprecated)");

	} else if (keycode == 0xC7FA){
		 snprintf(name, sizeof(name), "TS VELOCITY UP (deprecated)");

    } else if (keycode == 0xC7FB){
		 snprintf(name, sizeof(name), "TS VELOCITY DOWN (deprecated)");
	} else if (keycode == 0xC81D) {
        inversionposition--;
		if (inversionposition < 0) {
            inversionposition = 6;
        } else if (inversionposition > 6) {
            inversionposition = 0;
		}
		snprintf(name, sizeof(name), "%s", inversion_note_names[inversionposition]);

    } else if (keycode == 0xC81C) {
        inversionposition++;
		if (inversionposition < 0) {
            inversionposition = 6;
        } else if (inversionposition > 6) {
            inversionposition = 0;
		}
		snprintf(name, sizeof(name), "%s", inversion_note_names[inversionposition]);
		
	} else if (keycode >= 0xC81E && keycode <= 0xC91E) {
		if (record->event.pressed) {
			uint8_t id = keycode - 0xC81E;
			
			// Debug current position before sending macro
			char debug[32];
			snprintf(debug, sizeof(debug), "M%d id\n", id);
			
			dynamic_keymap_macro_send(id);
			//snprintf(name, sizeof(name), "Macro %d", id);
		}
		
	} else if (keycode >= 0xC961 && keycode <= 0xC9E0) {
			snprintf(name, sizeof(name), "Touch Dial CC %d", ccencoder);

		
	} else if (keycode == 0xC9F0) {
			snprintf(name, sizeof(name), "Touch Dial Tranposition");

		
	} else if (keycode == 0xC9F1) {
			snprintf(name, sizeof(name), "Touch Dial Velocity");

		
	} else if (keycode == 0xC9F2) {
			snprintf(name, sizeof(name), "Touch Dial MIDI Channel");
		
		
	} else if (keycode == 0xC9F3) {
		reset_keyboard_settings();
		snprintf(name, sizeof(name), "Reset Factory Settings");
		
	// SAVE_SETTINGS (Slot 0)
	} else if (keycode == 0xC9F4) {
		keyboard_settings.velocity_sensitivity = velocity_sensitivity;
		keyboard_settings.cc_sensitivity = cc_sensitivity;
		keyboard_settings.channel_number = channel_number;
		keyboard_settings.transpose_number = transpose_number;
		keyboard_settings.octave_number = octave_number;
		keyboard_settings.transpose_number2 = transpose_number2;
		keyboard_settings.octave_number2 = octave_number2;
		keyboard_settings.transpose_number3 = transpose_number3;
		keyboard_settings.octave_number3 = octave_number3;
		keyboard_settings.dynamic_range = dynamic_range;
		keyboard_settings.oledkeyboard = oledkeyboard;
		keyboard_settings.overdub_advanced_mode = overdub_advanced_mode;
		keyboard_settings.smartchordlightmode = smartchordlightmode;
		keyboard_settings.keysplitchannel = keysplitchannel;
		keyboard_settings.keysplit2channel = keysplit2channel;
		keyboard_settings.keysplitstatus = keysplitstatus;
		keyboard_settings.keysplittransposestatus = keysplittransposestatus;
		keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
		keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
			keyboard_settings.unsynced_mode_active = unsynced_mode_active;
    keyboard_settings.sample_mode_active = sample_mode_active;
	keyboard_settings.loop_messaging_enabled = loop_messaging_enabled;
    keyboard_settings.loop_messaging_channel = loop_messaging_channel;
    keyboard_settings.sync_midi_mode = sync_midi_mode;
    keyboard_settings.alternate_restart_mode = alternate_restart_mode;
		keyboard_settings.colorblindmode = colorblindmode;
	keyboard_settings.cclooprecording = cclooprecording;
	keyboard_settings.truesustain = truesustain;
		save_keyboard_settings_to_slot(0);
		snprintf(name, sizeof(name), "Saved as default settings");

	// SAVE_SETTINGS_2 (Slot 1)
	} else if (keycode == 0xC9F5) {
		keyboard_settings.velocity_sensitivity = velocity_sensitivity;
		keyboard_settings.cc_sensitivity = cc_sensitivity;
		keyboard_settings.channel_number = channel_number;
		keyboard_settings.transpose_number = transpose_number;
		keyboard_settings.octave_number = octave_number;
		keyboard_settings.transpose_number2 = transpose_number2;
		keyboard_settings.octave_number2 = octave_number2;
		keyboard_settings.transpose_number3 = transpose_number3;
		keyboard_settings.octave_number3 = octave_number3;
		keyboard_settings.dynamic_range = dynamic_range;
		keyboard_settings.oledkeyboard = oledkeyboard;
		keyboard_settings.overdub_advanced_mode = overdub_advanced_mode;
		keyboard_settings.smartchordlightmode = smartchordlightmode;
		keyboard_settings.keysplitchannel = keysplitchannel;
		keyboard_settings.keysplit2channel = keysplit2channel;
		keyboard_settings.keysplitstatus = keysplitstatus;
		keyboard_settings.keysplittransposestatus = keysplittransposestatus;
		keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
		keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
			keyboard_settings.unsynced_mode_active = unsynced_mode_active;
    keyboard_settings.sample_mode_active = sample_mode_active;
	keyboard_settings.loop_messaging_enabled = loop_messaging_enabled;
    keyboard_settings.loop_messaging_channel = loop_messaging_channel;
    keyboard_settings.sync_midi_mode = sync_midi_mode;
    keyboard_settings.alternate_restart_mode = alternate_restart_mode;
		keyboard_settings.colorblindmode = colorblindmode;
	keyboard_settings.cclooprecording = cclooprecording;
	keyboard_settings.truesustain = truesustain;
		save_keyboard_settings_to_slot(1);
		snprintf(name, sizeof(name), "Saved to Preset 1");

	// SAVE_SETTINGS_3 (Slot 2)
	} else if (keycode == 0xC9F6) {
		keyboard_settings.velocity_sensitivity = velocity_sensitivity;
		keyboard_settings.cc_sensitivity = cc_sensitivity;
		keyboard_settings.channel_number = channel_number;
		keyboard_settings.transpose_number = transpose_number;
		keyboard_settings.octave_number = octave_number;
		keyboard_settings.transpose_number2 = transpose_number2;
		keyboard_settings.octave_number2 = octave_number2;
		keyboard_settings.transpose_number3 = transpose_number3;
		keyboard_settings.octave_number3 = octave_number3;
		keyboard_settings.dynamic_range = dynamic_range;
		keyboard_settings.oledkeyboard = oledkeyboard;
		keyboard_settings.overdub_advanced_mode = overdub_advanced_mode;
		keyboard_settings.smartchordlightmode = smartchordlightmode;
		keyboard_settings.keysplitchannel = keysplitchannel;
		keyboard_settings.keysplit2channel = keysplit2channel;
		keyboard_settings.keysplitstatus = keysplitstatus;
		keyboard_settings.keysplittransposestatus = keysplittransposestatus;
		keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
		keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
			keyboard_settings.unsynced_mode_active = unsynced_mode_active;
    keyboard_settings.sample_mode_active = sample_mode_active;
	keyboard_settings.loop_messaging_enabled = loop_messaging_enabled;
    keyboard_settings.loop_messaging_channel = loop_messaging_channel;
    keyboard_settings.sync_midi_mode = sync_midi_mode;
    keyboard_settings.alternate_restart_mode = alternate_restart_mode;
		keyboard_settings.colorblindmode = colorblindmode;
	keyboard_settings.cclooprecording = cclooprecording;
	keyboard_settings.truesustain = truesustain;
		save_keyboard_settings_to_slot(2);
		snprintf(name, sizeof(name), "Saved to Preset 2");

	// SAVE_SETTINGS_4 (Slot 3)
	} else if (keycode == 0xC9F7) {
		keyboard_settings.velocity_sensitivity = velocity_sensitivity;
		keyboard_settings.cc_sensitivity = cc_sensitivity;
		keyboard_settings.channel_number = channel_number;
		keyboard_settings.transpose_number = transpose_number;
		keyboard_settings.octave_number = octave_number;
		keyboard_settings.transpose_number2 = transpose_number2;
		keyboard_settings.octave_number2 = octave_number2;
		keyboard_settings.transpose_number3 = transpose_number3;
		keyboard_settings.octave_number3 = octave_number3;
		keyboard_settings.dynamic_range = dynamic_range;
		keyboard_settings.oledkeyboard = oledkeyboard;
		keyboard_settings.overdub_advanced_mode = overdub_advanced_mode;
		keyboard_settings.smartchordlightmode = smartchordlightmode;
		keyboard_settings.keysplitchannel = keysplitchannel;
		keyboard_settings.keysplit2channel = keysplit2channel;
		keyboard_settings.keysplitstatus = keysplitstatus;
		keyboard_settings.keysplittransposestatus = keysplittransposestatus;
		keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
		keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
			keyboard_settings.unsynced_mode_active = unsynced_mode_active;
    keyboard_settings.sample_mode_active = sample_mode_active;
	keyboard_settings.loop_messaging_enabled = loop_messaging_enabled;
    keyboard_settings.loop_messaging_channel = loop_messaging_channel;
    keyboard_settings.sync_midi_mode = sync_midi_mode;
    keyboard_settings.alternate_restart_mode = alternate_restart_mode;
		save_keyboard_settings_to_slot(3);
		snprintf(name, sizeof(name), "Saved to Preset 3");

	// SAVE_SETTINGS_5 (Slot 4)
	} else if (keycode == 0xC9F8) {
		keyboard_settings.velocity_sensitivity = velocity_sensitivity;
		keyboard_settings.cc_sensitivity = cc_sensitivity;
		keyboard_settings.channel_number = channel_number;
		keyboard_settings.transpose_number = transpose_number;
		keyboard_settings.octave_number = octave_number;
		keyboard_settings.transpose_number2 = transpose_number2;
		keyboard_settings.octave_number2 = octave_number2;
		keyboard_settings.transpose_number3 = transpose_number3;
		keyboard_settings.octave_number3 = octave_number3;
		keyboard_settings.dynamic_range = dynamic_range;
		keyboard_settings.oledkeyboard = oledkeyboard;
		keyboard_settings.overdub_advanced_mode = overdub_advanced_mode;
		keyboard_settings.smartchordlightmode = smartchordlightmode;
		keyboard_settings.keysplitchannel = keysplitchannel;
		keyboard_settings.keysplit2channel = keysplit2channel;
		keyboard_settings.keysplitstatus = keysplitstatus;
		keyboard_settings.keysplittransposestatus = keysplittransposestatus;
		keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
		keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
			keyboard_settings.unsynced_mode_active = unsynced_mode_active;
    keyboard_settings.sample_mode_active = sample_mode_active;
	keyboard_settings.loop_messaging_enabled = loop_messaging_enabled;
    keyboard_settings.loop_messaging_channel = loop_messaging_channel;
    keyboard_settings.sync_midi_mode = sync_midi_mode;
    keyboard_settings.alternate_restart_mode = alternate_restart_mode;
		save_keyboard_settings_to_slot(4);
		snprintf(name, sizeof(name), "Saved to Preset 4");

	// LOAD_SETTINGS (Slot 0)
	} else if (keycode == 0xC9F9) {
		load_keyboard_settings_from_slot(0);
		snprintf(name, sizeof(name), "Loaded default settings");

	// LOAD_SETTINGS_2 (Slot 1)
	} else if (keycode == 0xC9FA) {
		load_keyboard_settings_from_slot(1);
		snprintf(name, sizeof(name), "Loaded Preset 1");

	// LOAD_SETTINGS_3 (Slot 2)
	} else if (keycode == 0xC9FB) {
		load_keyboard_settings_from_slot(2);
		snprintf(name, sizeof(name), "Loaded Preset 2");

	// LOAD_SETTINGS_4 (Slot 3)
	} else if (keycode == 0xC9FC) {
		load_keyboard_settings_from_slot(3);
		snprintf(name, sizeof(name), "Loaded Preset 3");

	// LOAD_SETTINGS_5 (Slot 4)
	} else if (keycode == 0xC9FD) {
		load_keyboard_settings_from_slot(4);
		snprintf(name, sizeof(name), "Loaded Preset 4");
		
	} else if (keycode == 0xCA0A) {  // Progression Voicing 1
            progressionvoicing = 1;
			randomprogression = 0;
			snprintf(name, sizeof(name), "Basic Voicing Style");
    
	} else if (keycode == 0xCA0B) {  // Progression Voicing 1
            progressionvoicing = 2;
			randomprogression = 0;
			snprintf(name, sizeof(name), "Advanced Voicing Style");
			
	} else if (keycode == 0xCA0C) {  // Progression Voicing 1
            progressionvoicing = 3;
			randomprogression = 0;
			previous_highest_note = 0;
			previous_lowest_note = 127;
			snprintf(name, sizeof(name), "Descending Voicing Style");
    
	} else if (keycode == 0xCA0D) {  // Progression Voicing 1
            progressionvoicing = 4;
			randomprogression = 0;
			previous_highest_note = 0;
			previous_lowest_note = 127;
			snprintf(name, sizeof(name), "Ascending Voicing Style");
	
	} else if (keycode == 0xCA0E) {  // Progression Voicing 1
			randomprogression = 1;
            progressionvoicing = 1;
			previous_highest_note = 0;
			previous_lowest_note = 127;
			snprintf(name, sizeof(name), "Random Voicing Style");
			
	} else if (keycode == 0xCA00) {  // Chord progression octave up
	if (record->event.pressed) {
        progression_octave_offset += 12;
		snprintf(name, sizeof(name), "Progression Octave Up");
        if (progression_octave_offset > 24) progression_octave_offset = 24;
	}

	} else if (keycode == 0xCA01) {  // Chord progression octave down
	if (record->event.pressed) {
        progression_octave_offset -= 12;
		snprintf(name, sizeof(name), "Progression Octave Down");
        if (progression_octave_offset < -24) progression_octave_offset = -24;
	}
		
    } else if (keycode == 0xC9FF) {  // Chord progression octave reset
			progression_octave_offset = 0;
			snprintf(name, sizeof(name), "Progression Octave Reset");
			
		
} else if (keycode == 0xC929) {// Tap tempo key
    if (record->event.pressed) {
		
        uint32_t current_time = timer_read32();
        
        // If too much time has passed, start fresh
        if (current_time - last_tap_time > TAP_TIMEOUT_MS) {
            active_taps = 0;  // Reset tap count
        }
        
        // Shift existing taps if we're at max
        if (active_taps >= MAX_TAPS_AVERAGE) {
            for (uint8_t i = 0; i < MAX_TAPS_AVERAGE - 1; i++) {
                tap_times[i] = tap_times[i + 1];
            }
            active_taps = MAX_TAPS_AVERAGE - 1;
        }
        
        // Add new tap
        tap_times[active_taps] = current_time;
        active_taps++;
        
        if (active_taps >= 2) {
            current_bpm = calculate_tap_bpm();
			internal_clock_start();
            //bpm_source_macro = 0;  // Mark as manual BPM
            tap_tempo_active = true;
			dynamic_macro_bpm_changed(current_bpm);
			internal_clock_tempo_changed();
			
        }
		
        last_tap_time = current_time;
        
        // Display BPM with 2 decimal places
        uint16_t display_bpm = current_bpm / 100000;           // Integer part
        uint16_t decimal_part = (current_bpm % 100000) / 1000; // 2 decimal places
        snprintf(name, sizeof(name), "%d.%02d BPM", display_bpm, decimal_part);
    }
	
	

	} else if (keycode == 0xEE2E) {  // MI_SCAN - moved from 0xC4B0 to avoid collision with RGB_KC_58
		if (record->event.pressed) {
			scan_current_layer_midi_leds();
			snprintf(name, sizeof(name), "Scanned Layer %d", get_highest_layer(layer_state | default_layer_state));
			smartchordlight = 0;  // Enable the LED visualization
		}
		
} else if (keycode == 29013) {
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        snprintf(name, sizeof(name), "OCTAVE DOWN");
        octave_number-=12;
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_transpose_target(i + 1);
                    set_overdub_transpose_target(i + 1, current_target - 12);
                }
            }
            snprintf(name, sizeof(name), "Overdub Octave Down");
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_transpose_target(i + 1);
                    set_macro_transpose_target(i + 1, current_target - 12);
                }
            }
            snprintf(name, sizeof(name), "Loop Octave Down");
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect octave_number2
        snprintf(name, sizeof(name), "KEYSPLIT OCTAVE DOWN");
        octave_number2-=12;
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect octave_number3
        snprintf(name, sizeof(name), "TRIPLESPLIT OCTAVE DOWN");
        octave_number3-=12;
    }

// Octave Up (29014)
} else if (keycode == 29014) {
    if (!is_any_macro_modifier_active() && !keysplitmodifierheld && !triplesplitmodifierheld) {
        snprintf(name, sizeof(name), "OCTAVE UP");
        octave_number+=12;
    } else if (is_any_macro_modifier_active()) {
        // Macro modifier is held - check if overdub button is also held
        if (overdub_button_held && overdub_advanced_mode) {
            // Macro modifier + overdub button held in advanced mode - apply to overdub
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_overdub_transpose_target(i + 1);
                    set_overdub_transpose_target(i + 1, current_target + 12);
                }
            }
            snprintf(name, sizeof(name), "Overdub Octave Up");
        } else {
            // Just macro modifier held - apply to macro (existing behavior)
            for (uint8_t i = 0; i < 4; i++) {
                if (macro_modifier_held[i]) {
                    int8_t current_target = get_macro_transpose_target(i + 1);
                    set_macro_transpose_target(i + 1, current_target + 12);
                }
            }
            snprintf(name, sizeof(name), "Loop Octave Up");
        }
    } else if (keysplitmodifierheld) {
        // Keysplit modifier is held - affect octave_number2
        snprintf(name, sizeof(name), "KEYSPLIT OCTAVE UP");
        octave_number2+=12;
    } else if (triplesplitmodifierheld) {
        // Triplesplit modifier is held - affect octave_number3
        snprintf(name, sizeof(name), "TRIPLESPLIT OCTAVE UP");
        octave_number3+=12;
    }
	
	} else if (keycode == 0xC74F) {
	snprintf(name, sizeof(name), "KS OCTAVE DOWN");
	octave_number2-=12;
	
	} else if (keycode == 0xC74E) {
	snprintf(name, sizeof(name), "KS OCTAVE UP");
	octave_number2+=12;
	
	} else if (keycode == 0xC7FF) {
	snprintf(name, sizeof(name), "TS OCTAVE DOWN");
	octave_number3-=12;
	
	} else if (keycode == 0xC7FE) {
	snprintf(name, sizeof(name), "TS OCTAVE UP");
	octave_number3+=12;
		
    } else if (keycode >= 33152 && keycode <= 49535) {
        // Calculate CC number and index within the CC
        int cc_number = (keycode - 33152) / 128;
        int cc_index = (keycode - 33152) % 128;

        // Update the name string with new line
        snprintf(name, sizeof(name), "CC%-3d  %d", cc_number, cc_index);
	}
    // Handle HE Velocity Curve keycodes
    else if (keycode >= HE_CURVE_SOFTEST && keycode <= HE_CURVE_HARDEST) {
        const char* curve_names[] = {"Softest", "Soft", "Medium", "Hard", "Hardest"};
        uint8_t curve_idx = keycode - HE_CURVE_SOFTEST;
        snprintf(name, sizeof(name), "HE Curve: %s", curve_names[curve_idx]);
    }
    // Handle HE Velocity Range keycodes (min ≤ max only, 8,128 keycodes)
    else if (keycode >= HE_VEL_RANGE_BASE && keycode < HE_VEL_RANGE_BASE + 8128) {
        uint16_t offset = keycode - HE_VEL_RANGE_BASE;
        // Calculate min/max from offset using matching generation order
        uint8_t min_value = 1;
        uint8_t max_value = 1;
        uint16_t count = 0;

        for (uint8_t m = 1; m <= 127; m++) {
            for (uint8_t x = m; x <= 127; x++) {
                if (count == offset) {
                    min_value = m;
                    max_value = x;
                    goto found_keylog;
                }
                count++;
            }
        }
        found_keylog:
        if (min_value == max_value) {
            snprintf(name, sizeof(name), "HE Vel: %d", min_value);
        } else {
            snprintf(name, sizeof(name), "HE Vel: %d-%d", min_value, max_value);
        }
    }

	else if (keycode > 0) {
        snprintf(name, sizeof(name), " ");
	}
    // Handle CC UP and CC SENSITIVITY keys
    if (keycode >= 32896 && keycode <= 33023) {
        int cc_number = (keycode - 32896);  // Calculate CC# based on keycode

        // Check if it's a CC# UP key
        if (keycode >= 32896 && keycode <= 33023) {
            cc_updown_value[cc_number] += cc_sensitivity;  // Increase CC UP (value 2) based on sensitivity
        }

        // Ensure CC UP (value 2) stays within the valid range (0-127)
        if (cc_updown_value[cc_number] < 0) {
            cc_updown_value[cc_number] = 0;
        } else if (cc_updown_value[cc_number] > 127) {
            cc_updown_value[cc_number] = 127;
        }

        // Update the name string
        snprintf(name, sizeof(name), "CC%-3d  %d", cc_number, cc_up_value1[cc_number] + cc_updown_value[cc_number]);
    }
	// Handle CC DOWN keys
	if (keycode >= 33024 && keycode <= 33151) {
    int cc_number = (keycode - 33024);  // Calculate CC# based on keycode

    // Check if it's a CC DOWN key
    if (keycode >= 33024 && keycode <= 33151) {
        cc_updown_value[cc_number] -= cc_sensitivity;  // Decrease CC DOWN (value 2) based on sensitivity
    }

    // Ensure CC DOWN (value 2) stays within the valid range (0-127)
    if (cc_updown_value[cc_number] < 0) {
        cc_updown_value[cc_number] = 0;
    } else if (cc_updown_value[cc_number] > 127) {
        cc_updown_value[cc_number] = 127;
    }
	

    // Update the name string
    snprintf(name, sizeof(name), "CC%-3d  %d", cc_number, cc_down_value1[cc_number] + cc_updown_value[cc_number]);
}

    // Update keylog
    //snprintf(keylog_str, sizeof(keylog_str), "%-21s", name);
	
	int nlength = strlen(name);
	int tpadding = 21 - nlength;
	int lpadding = tpadding / 2;
	int rpadding = tpadding - lpadding;  // To ensure it fits exactly in 21 characters

snprintf(keylog_str, sizeof(keylog_str), "%*s", lpadding, "");

snprintf(keylog_str + strlen(keylog_str), sizeof(keylog_str) - strlen(keylog_str), "%s", name);

snprintf(keylog_str + strlen(keylog_str), sizeof(keylog_str) - strlen(keylog_str), "%*s", rpadding, "");

}


void oled_render_keylog(void) {
	char name[124];
	int total_length = strlen(getRootName()) + strlen(getChordName()) + strlen(getBassName());
	int total_padding = 22 - total_length;
	int left_padding = total_padding / 2;
	int right_padding = total_padding - left_padding;


	if (keysplittransposestatus == 1) {snprintf(name, sizeof(name), "\n  TRA%+3d // TRA%+3d", transpose_number + octave_number, transpose_number2 + octave_number2);
	}else if (keysplittransposestatus == 2) {snprintf(name, sizeof(name), "\n T%+3d / T%+3d  /T%+3d", transpose_number + octave_number,transpose_number2 + octave_number2 ,transpose_number3 + octave_number3);
	}else if (keysplittransposestatus == 3) {snprintf(name, sizeof(name), "\nT%+3d/T%+3d/T%+3d", transpose_number + octave_number, transpose_number2 + octave_number2, transpose_number3 + octave_number3);
	}else { snprintf(name, sizeof(name), "\n  TRANSPOSITION %+3d", transpose_number + octave_number);
	}

	// Get HE velocity settings from global keyboard settings (no longer per-layer)
	uint8_t he_min = keyboard_settings.he_velocity_min;
	uint8_t he_max = keyboard_settings.he_velocity_max;

	// Show HE velocity range for current layer
	if (he_min == he_max) {
		snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n     VELOCITY %3d", he_min);
	} else {
		snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n   VELOCITY %3d-%3d", he_min, he_max);
	}

	if (keysplitstatus == 1) {snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n   CH %2d // CH %2d\n---------------------", (channel_number + 1), (keysplitchannel + 1));
	}else if (keysplitstatus == 2) {snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n CH %2d/ CH %2d /CH %2d\n---------------------", (channel_number + 1), (keysplitchannel + 1), (keysplit2channel + 1));
	}else if (keysplitstatus == 3) {snprintf(name + strlen(name), sizeof(name) - strlen(name), "\nC%2d/C%2d/C%2d\n---------------------", (channel_number + 1), (keysplitchannel + 1), (keysplit2channel + 1));
	}else { snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n   MIDI CHANNEL %2d\n---------------------", (channel_number + 1));
	}
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "%*s", left_padding, "");
	// Append the RootName, ChordName, and BassName
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "%s%s%s", getRootName(), getChordName(), getBassName());
	// Add right padding and the ending characters
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "%*s", right_padding, "");
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "- - - - - - - - - -\n");

    oled_write(name, false);
    oled_write(keylog_str, false);

}

// Function to clear all tracking arrays
void clear_sustain_tracking(void) {
    sustain_pressed_count = 0;
    sustain_released_count = 0;
    for (int i = 0; i < 20; i++) {
        sustain_pressed_keys[i] = 0;
        sustain_released_keys[i] = 0;
    }
}

// Function to check if a key is in the pressed list
bool is_key_in_pressed_list(uint16_t keycode) {
    for (int i = 0; i < sustain_pressed_count; i++) {
        if (sustain_pressed_keys[i] == keycode) {
            return true;
        }
    }
    return false;
}

// Function to check if a key is in the released list
bool is_key_in_released_list(uint16_t keycode) {
    for (int i = 0; i < sustain_released_count; i++) {
        if (sustain_released_keys[i] == keycode) {
            return true;
        }
    }
    return false;
}

// Function to remove key from released list
void remove_from_released_list(uint16_t keycode) {
    for (int i = 0; i < sustain_released_count; i++) {
        if (sustain_released_keys[i] == keycode) {
            // Shift all elements after this one back
            for (int j = i; j < sustain_released_count - 1; j++) {
                sustain_released_keys[j] = sustain_released_keys[j + 1];
            }
            sustain_released_count--;
            sustain_released_keys[sustain_released_count] = 0; // Clear the last element
            break; // Only remove the first occurrence
        }
    }
}

// Function to add key to pressed list
void add_to_pressed_list(uint16_t keycode) {
    // First check if this key was previously released while sustain was held
    if (is_key_in_released_list(keycode)) {
        // Remove it from the released list since it's being pressed again
        remove_from_released_list(keycode);
    }
    
    // Only add to pressed list if it's not already there
    if (!is_key_in_pressed_list(keycode) && sustain_pressed_count < 20) {
        sustain_pressed_keys[sustain_pressed_count++] = keycode;
    }
}

// Function to add key to released list
void add_to_released_list(uint16_t keycode) {
    // Only add to released list if it's not already there
    if (!is_key_in_released_list(keycode) && sustain_released_count < 20) {
        sustain_released_keys[sustain_released_count++] = keycode;
    }
}

// Function to backup current held keys state
void backup_held_keys_state(void) {
    sustain_backup.trueheldkey1 = trueheldkey1;
    sustain_backup.trueheldkey2 = trueheldkey2;
    sustain_backup.trueheldkey3 = trueheldkey3;
    sustain_backup.trueheldkey4 = trueheldkey4;
    sustain_backup.trueheldkey5 = trueheldkey5;
    sustain_backup.trueheldkey6 = trueheldkey6;
    sustain_backup.trueheldkey7 = trueheldkey7;
    
    sustain_backup.heldkey1 = heldkey1;
    sustain_backup.heldkey2 = heldkey2;
    sustain_backup.heldkey3 = heldkey3;
    sustain_backup.heldkey4 = heldkey4;
    sustain_backup.heldkey5 = heldkey5;
    sustain_backup.heldkey6 = heldkey6;
    sustain_backup.heldkey7 = heldkey7;
    
    sustain_backup.heldkey1difference = heldkey1difference;
    sustain_backup.heldkey2difference = heldkey2difference;
    sustain_backup.heldkey3difference = heldkey3difference;
    sustain_backup.heldkey4difference = heldkey4difference;
    sustain_backup.heldkey5difference = heldkey5difference;
    sustain_backup.heldkey6difference = heldkey6difference;
    sustain_backup.heldkey7difference = heldkey7difference;
    
    sustain_backup.trueoctaveheldkey1 = trueoctaveheldkey1;
    sustain_backup.trueoctaveheldkey2 = trueoctaveheldkey2;
    sustain_backup.trueoctaveheldkey3 = trueoctaveheldkey3;
    sustain_backup.trueoctaveheldkey4 = trueoctaveheldkey4;
    
    sustain_backup.octaveheldkey1 = octaveheldkey1;
    sustain_backup.octaveheldkey2 = octaveheldkey2;
    sustain_backup.octaveheldkey3 = octaveheldkey3;
    sustain_backup.octaveheldkey4 = octaveheldkey4;
    
    sustain_backup.octaveheldkey1difference = octaveheldkey1difference;
    sustain_backup.octaveheldkey2difference = octaveheldkey2difference;
    sustain_backup.octaveheldkey3difference = octaveheldkey3difference;
    sustain_backup.octaveheldkey4difference = octaveheldkey4difference;
}

// Function to clear all held keys
void clear_all_held_keys(void) {
    trueheldkey1 = trueheldkey2 = trueheldkey3 = trueheldkey4 = trueheldkey5 = trueheldkey6 = trueheldkey7 = 0;
    heldkey1 = heldkey2 = heldkey3 = heldkey4 = heldkey5 = heldkey6 = heldkey7 = 0;
    heldkey1difference = heldkey2difference = heldkey3difference = heldkey4difference = heldkey5difference = heldkey6difference = heldkey7difference = 0;
    
    trueoctaveheldkey1 = trueoctaveheldkey2 = trueoctaveheldkey3 = trueoctaveheldkey4 = 0;
    octaveheldkey1 = octaveheldkey2 = octaveheldkey3 = octaveheldkey4 = 0;
    octaveheldkey1difference = octaveheldkey2difference = octaveheldkey3difference = octaveheldkey4difference = 0;
    
    rootnote = 13;
    bassnote = 13;
}

// Function to rebuild held keys from current state
void rebuild_held_keys_from_sustain_state(void) {
    // Create a list of currently active keys (backup + pressed - released)
    uint16_t active_keys[20];
    uint8_t active_count = 0;
    
    // Add backed up keys that weren't released
    if (sustain_backup.trueheldkey1 != 0) {
        uint16_t keycode = sustain_backup.trueheldkey1 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueheldkey2 != 0) {
        uint16_t keycode = sustain_backup.trueheldkey2 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueheldkey3 != 0) {
        uint16_t keycode = sustain_backup.trueheldkey3 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueheldkey4 != 0) {
        uint16_t keycode = sustain_backup.trueheldkey4 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueheldkey5 != 0) {
        uint16_t keycode = sustain_backup.trueheldkey5 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueheldkey6 != 0) {
        uint16_t keycode = sustain_backup.trueheldkey6 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueheldkey7 != 0) {
        uint16_t keycode = sustain_backup.trueheldkey7 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    
    // Add octave keys that weren't released
    if (sustain_backup.trueoctaveheldkey1 != 0) {
        uint16_t keycode = sustain_backup.trueoctaveheldkey1 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueoctaveheldkey2 != 0) {
        uint16_t keycode = sustain_backup.trueoctaveheldkey2 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueoctaveheldkey3 != 0) {
        uint16_t keycode = sustain_backup.trueoctaveheldkey3 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    if (sustain_backup.trueoctaveheldkey4 != 0) {
        uint16_t keycode = sustain_backup.trueoctaveheldkey4 - 24 - transpositionplaceholder + keysplitnumber;
        if (!is_key_in_released_list(keycode)) {
            active_keys[active_count++] = keycode;
        }
    }
    
    // Add keys that were pressed while sustain was held and not released
    for (int i = 0; i < sustain_pressed_count; i++) {
        if (!is_key_in_released_list(sustain_pressed_keys[i])) {
            // Check if this key is not already in active_keys
            bool already_added = false;
            for (int j = 0; j < active_count; j++) {
                if (active_keys[j] == sustain_pressed_keys[i]) {
                    already_added = true;
                    break;
                }
            }
            if (!already_added && active_count < 20) {
                active_keys[active_count++] = sustain_pressed_keys[i];
            }
        }
    }
    
    // Now rebuild the held key system from the active keys list
    // This mimics the key press logic but rebuilds all at once
    for (int i = 0; i < active_count; i++) {
        uint16_t keycode = active_keys[i];
        
        // Calculate the held key values
        int calculated_trueheldkey = keycode - keysplitnumber + 24 + transpositionplaceholder;
        int calculated_heldkey = ((calculated_trueheldkey % 12) + 12) % 12 + 1;
        
        // Find the next available slot and assign
        if (heldkey1 == 0) {
            trueheldkey1 = calculated_trueheldkey;
            heldkey1 = calculated_heldkey;
            heldkey1difference = (heldkey1 - 1) % 12;
        } else if (heldkey2 == 0 && calculated_heldkey != heldkey1) {
            trueheldkey2 = calculated_trueheldkey;
            heldkey2 = calculated_heldkey;
            heldkey2difference = heldkey2 - heldkey1 + 1;
            if (heldkey2difference < 1) heldkey2difference += 12;
        } else if (heldkey3 == 0 && calculated_heldkey != heldkey1 && calculated_heldkey != heldkey2) {
            trueheldkey3 = calculated_trueheldkey;
            heldkey3 = calculated_heldkey;
            heldkey3difference = heldkey3 - heldkey1 + 1;
            if (heldkey3difference < 1) heldkey3difference += 12;
        } else if (heldkey4 == 0 && calculated_heldkey != heldkey1 && calculated_heldkey != heldkey2 && calculated_heldkey != heldkey3) {
            trueheldkey4 = calculated_trueheldkey;
            heldkey4 = calculated_heldkey;
            heldkey4difference = heldkey4 - heldkey1 + 1;
            if (heldkey4difference < 1) heldkey4difference += 12;
        } else if (heldkey5 == 0 && calculated_heldkey != heldkey1 && calculated_heldkey != heldkey2 && calculated_heldkey != heldkey3 && calculated_heldkey != heldkey4) {
            trueheldkey5 = calculated_trueheldkey;
            heldkey5 = calculated_heldkey;
            heldkey5difference = heldkey5 - heldkey1 + 1;
            if (heldkey5difference < 1) heldkey5difference += 12;
        } else if (heldkey6 == 0 && calculated_heldkey != heldkey1 && calculated_heldkey != heldkey2 && calculated_heldkey != heldkey3 && calculated_heldkey != heldkey4 && calculated_heldkey != heldkey5) {
            trueheldkey6 = calculated_trueheldkey;
            heldkey6 = calculated_heldkey;
            heldkey6difference = heldkey6 - heldkey1 + 1;
            if (heldkey6difference < 1) heldkey6difference += 12;
        } else if (heldkey7 == 0 && calculated_heldkey != heldkey1 && calculated_heldkey != heldkey2 && calculated_heldkey != heldkey3 && calculated_heldkey != heldkey4 && calculated_heldkey != heldkey5 && calculated_heldkey != heldkey6) {
            trueheldkey7 = calculated_trueheldkey;
            heldkey7 = calculated_heldkey;
            heldkey7difference = heldkey7 - heldkey1 + 1;
            if (heldkey7difference < 1) heldkey7difference += 12;
        } else {
            // This is an octave duplicate, put in octave slots
            if (octaveheldkey1 == 0) {
                trueoctaveheldkey1 = calculated_trueheldkey;
                octaveheldkey1 = calculated_heldkey;
                octaveheldkey1difference = calculated_heldkey - heldkey1 + 1;
                if (octaveheldkey1difference < 1) octaveheldkey1difference += 12;
            } else if (octaveheldkey2 == 0) {
                trueoctaveheldkey2 = calculated_trueheldkey;
                octaveheldkey2 = calculated_heldkey;
                octaveheldkey2difference = calculated_heldkey - heldkey1 + 1;
                if (octaveheldkey2difference < 1) octaveheldkey2difference += 12;
            } else if (octaveheldkey3 == 0) {
                trueoctaveheldkey3 = calculated_trueheldkey;
                octaveheldkey3 = calculated_heldkey;
                octaveheldkey3difference = calculated_heldkey - heldkey1 + 1;
                if (octaveheldkey3difference < 1) octaveheldkey3difference += 12;
            } else if (octaveheldkey4 == 0) {
                trueoctaveheldkey4 = calculated_trueheldkey;
                octaveheldkey4 = calculated_heldkey;
                octaveheldkey4difference = calculated_heldkey - heldkey1 + 1;
                if (octaveheldkey4difference < 1) octaveheldkey4difference += 12;
            }
        }
    }
}

static uint8_t active_smartchord_note = 0;  // 0 means no active smart chord

void smartchordaddnotes(uint8_t channel, uint8_t note, uint8_t velocity) {
    if (!progression_active) {
        // Calculate chord notes directly from the MIDI note
        uint8_t chordnote_2 = note + chordkey2;
        uint8_t chordnote_3 = note + chordkey3;
        uint8_t chordnote_4 = note + chordkey4;
        uint8_t chordnote_5 = note + chordkey5;
        uint8_t chordnote_6 = note + chordkey6;
        uint8_t chordnote_7 = note + chordkey7;

        // For tone status tracking, you might need these calculations
        uint8_t tone2 = note + chordkey2;
        uint8_t tone3 = note + chordkey3;
        uint8_t tone4 = note + chordkey4;
        uint8_t tone5 = note + chordkey5;
        uint8_t tone6 = note + chordkey6;
        uint8_t tone7 = note + chordkey7;

        // ALWAYS clean up existing smart chord keys before adding new ones
        if (smartchordkey2 != 0) {
            midi_send_noteoff_smartchord(channel, smartchordkey2, velocity);
            smartchordkey2 = 0;
        }
        if (smartchordkey3 != 0) {
            midi_send_noteoff_smartchord(channel, smartchordkey3, velocity);
            smartchordkey3 = 0;
        }
        if (smartchordkey4 != 0) {
            midi_send_noteoff_smartchord(channel, smartchordkey4, velocity);
            smartchordkey4 = 0;
        }
        if (smartchordkey5 != 0) {
            midi_send_noteoff_smartchord(channel, smartchordkey5, velocity);
            smartchordkey5 = 0;
        }
        if (smartchordkey6 != 0) {
            midi_send_noteoff_smartchord(channel, smartchordkey6, velocity);
            smartchordkey6 = 0;
        }
        if (smartchordkey7 != 0) {
            midi_send_noteoff_smartchord(channel, smartchordkey7, velocity);
            smartchordkey7 = 0;
        }

        // Set this note as the active smart chord controller
        active_smartchord_note = note;

        if (chordkey2 != 0) { // Handles up to 7-note smart chords
            // Send MIDI noteon for each chord key if present
            midi_send_noteon_smartchord(channel, chordnote_2, velocity);
            tone2_status[1][tone2] += 1;
            
            if (chordkey3 != 0) {
                midi_send_noteon_smartchord(channel, chordnote_3, velocity);
                tone3_status[1][tone3] += 1;
            }
            if (chordkey4 != 0) {
                midi_send_noteon_smartchord(channel, chordnote_4, velocity);
                tone4_status[1][tone4] += 1;
            }
            if (chordkey5 != 0) {
                midi_send_noteon_smartchord(channel, chordnote_5, velocity);
                tone5_status[1][tone5] += 1;
            }
            if (chordkey6 != 0) {
                midi_send_noteon_smartchord(channel, chordnote_6, velocity);
                tone6_status[1][tone6] += 1;
            }
            if (chordkey7 != 0) {
                midi_send_noteon_smartchord(channel, chordnote_7, velocity);
                tone7_status[1][tone7] += 1;
            }

            // Set smart chord keys for cleanup later (store the actual MIDI notes)
            smartchordkey2 = chordnote_2;
            if (chordkey3 != 0) smartchordkey3 = chordnote_3;
            if (chordkey4 != 0) smartchordkey4 = chordnote_4;
            if (chordkey5 != 0) smartchordkey5 = chordnote_5;
            if (chordkey6 != 0) smartchordkey6 = chordnote_6;
            if (chordkey7 != 0) smartchordkey7 = chordnote_7;
            
            // Calculate held key values for display
            trueheldkey1 = note + 24;
            heldkey1 = ((trueheldkey1 % 12) + 12) % 12 + 1;
            heldkey1difference = (heldkey1 - 1) % 12;
            trueheldkey2 = note + 24 + chordkey2;
            heldkey2 = ((trueheldkey2) % 12 + 12) % 12 + 1;
            heldkey2difference = heldkey2 - heldkey1 + 1;
            if (heldkey2difference < 1) {
                heldkey2difference += 12;
            }

            // Continue with trueheldkey3-7 calculations as needed...
            if (chordkey3 != 0) {
                trueheldkey3 = note + 24 + chordkey3;
                heldkey3 = ((trueheldkey3 % 12) + 12) % 12 + 1;
                heldkey3difference = heldkey3 - heldkey1 + 1;
                if (heldkey3difference < 1) {
                    heldkey3difference += 12;
                }
            }
            
            if (chordkey4 != 0) {
                trueheldkey4 = note + 24 + chordkey4;
                heldkey4 = ((trueheldkey4 % 12) + 12) % 12 + 1;
                heldkey4difference = heldkey4 - heldkey1 + 1;
                if (heldkey4difference < 1) {
                    heldkey4difference += 12;
                }
            }
            
            if (chordkey5 != 0) {
                trueheldkey5 = note + 24 + chordkey5;
                heldkey5 = ((trueheldkey5 % 12) + 12) % 12 + 1;
                heldkey5difference = heldkey5 - heldkey1 + 1;
                if (heldkey5difference < 1) {
                    heldkey5difference += 12;
                }
            }
            
            if (chordkey6 != 0) {
                trueheldkey6 = note + 24 + chordkey6;
                heldkey6 = ((trueheldkey6 % 12) + 12) % 12 + 1;
                heldkey6difference = heldkey6 - heldkey1 + 1;
                if (heldkey6difference < 1) {
                    heldkey6difference += 12;
                }
            }
            
            if (chordkey7 != 0) {
                trueheldkey7 = note + 24 + chordkey7;
                heldkey7 = ((trueheldkey7 % 12) + 12) % 12 + 1;
                heldkey7difference = heldkey7 - heldkey1 + 1;
                if (heldkey7difference < 1) {
                    heldkey7difference += 12;
                }
            }

            // Set initial tone status if necessary
            if (tone2_status[0][tone2] == MIDI_INVALID_NOTE) {
                tone2_status[0][tone2] = chordnote_2;
            }
        }
    }
}

void smartchordremovenotes(uint8_t channel, uint8_t note, uint8_t velocity) {
    if (!progression_active) {
        // Only clean up smart chord notes if THIS note is the one currently controlling them
        if (note == active_smartchord_note && smartchordkey2 != 0) {
            // Calculate tone values for status tracking
            uint8_t tone2 = note + chordkey2;
            uint8_t tone3 = note + chordkey3;
            uint8_t tone4 = note + chordkey4;
            uint8_t tone5 = note + chordkey5;
            uint8_t tone6 = note + chordkey6;
            uint8_t tone7 = note + chordkey7;

            // On key release
            if (smartchordlight != 3) {
                smartchordlight = 0;
            }
            
            // Send note offs using the stored smartchordkey values
            midi_send_noteoff_smartchord(channel, smartchordkey2, velocity);
            if (tone2_status[1][tone2] > 0) {
                tone2_status[1][tone2] -= 1;
            }
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;

            if (smartchordkey3 != 0) {
                midi_send_noteoff_smartchord(channel, smartchordkey3, velocity);
                if (tone3_status[1][tone3] > 0) {
                    tone3_status[1][tone3] -= 1;
                }
                tone3_status[0][tone3] = MIDI_INVALID_NOTE;
            }
            if (smartchordkey4 != 0) {
                midi_send_noteoff_smartchord(channel, smartchordkey4, velocity);
                if (tone4_status[1][tone4] > 0) {
                    tone4_status[1][tone4] -= 1;
                }
                tone4_status[0][tone4] = MIDI_INVALID_NOTE;
            }
            if (smartchordkey5 != 0) {
                midi_send_noteoff_smartchord(channel, smartchordkey5, velocity);
                if (tone5_status[1][tone5] > 0) {
                    tone5_status[1][tone5] -= 1;
                }
                tone5_status[0][tone5] = MIDI_INVALID_NOTE;
            }
            if (smartchordkey6 != 0) {
                midi_send_noteoff_smartchord(channel, smartchordkey6, velocity);
                if (tone6_status[1][tone6] > 0) {
                    tone6_status[1][tone6] -= 1;
                }
                tone6_status[0][tone6] = MIDI_INVALID_NOTE;
            }
            if (smartchordkey7 != 0) {
                midi_send_noteoff_smartchord(channel, smartchordkey7, velocity);
                if (tone7_status[1][tone7] > 0) {
                    tone7_status[1][tone7] -= 1;
                }
                tone7_status[0][tone7] = MIDI_INVALID_NOTE;
            }

            // Reset variables
            smartchordkey2 = 0;
            smartchordkey3 = 0;
            smartchordkey4 = 0;
            smartchordkey5 = 0;
            smartchordkey6 = 0;
            smartchordkey7 = 0;
            trueheldkey1 = 0;
            heldkey1 = 0;
            heldkey1difference = 0;
            trueheldkey2 = 0;
            heldkey2 = 0;
            heldkey2difference = 0;
            trueheldkey3 = 0;
            heldkey3 = 0;
            heldkey3difference = 0;
            trueheldkey4 = 0;
            heldkey4 = 0;
            heldkey4difference = 0;
            trueheldkey5 = 0;
            heldkey5 = 0;
            heldkey5difference = 0;
            trueheldkey6 = 0;
            heldkey6 = 0;
            heldkey6difference = 0;
            trueheldkey7 = 0;
            heldkey7 = 0;
            heldkey7difference = 0;

            // Clear the active note tracker
            active_smartchord_note = 0;
        }
        // If this note is NOT the active smart chord note, do nothing
        // (it was interrupted, so its smart chord notes were already cleaned up)
    }
}

void smartchorddisplayupdates(uint8_t note) {
    if (smartchordstatus != 0) {
        
        // Cache the layer lookup - this is the expensive part
        int8_t current_layer = get_highest_layer(layer_state | default_layer_state);	
        uint8_t positions[6];  // Reusable array for positions
        
        // Get base note positions (root note)
        uint8_t base_note_idx = note - 24 - transpose_number - octave_number;
        get_all_note_positions(current_layer, base_note_idx, positions);
        chordkey1_led_index = positions[0];
        chordkey1_led_index2 = positions[1];
        chordkey1_led_index3 = positions[2];
        chordkey1_led_index4 = positions[3];
        chordkey1_led_index5 = positions[4];
        chordkey1_led_index6 = positions[5];

        // Get chord note 2 positions
        if (chordkey2) {
            uint8_t note2_idx = note + chordkey2 - 24 - transpose_number - octave_number;
            get_all_note_positions(current_layer, note2_idx, positions);
            chordkey2_led_index = positions[0];
            chordkey2_led_index2 = positions[1];
            chordkey2_led_index3 = positions[2];
            chordkey2_led_index4 = positions[3];
            chordkey2_led_index5 = positions[4];
            chordkey2_led_index6 = positions[5];
        }

        // Get chord note 3 positions
        if (chordkey3) {
            uint8_t note3_idx = note + chordkey3 - 24 - transpose_number - octave_number;
            get_all_note_positions(current_layer, note3_idx, positions);
            chordkey3_led_index = positions[0];
            chordkey3_led_index2 = positions[1];
            chordkey3_led_index3 = positions[2];
            chordkey3_led_index4 = positions[3];
            chordkey3_led_index5 = positions[4];
            chordkey3_led_index6 = positions[5];
        }

        // Get chord note 4 positions
        if (chordkey4) {
            uint8_t note4_idx = note + chordkey4 - 24 - transpose_number - octave_number;
            get_all_note_positions(current_layer, note4_idx, positions);
            chordkey4_led_index = positions[0];
            chordkey4_led_index2 = positions[1];
            chordkey4_led_index3 = positions[2];
            chordkey4_led_index4 = positions[3];
            chordkey4_led_index5 = positions[4];
            chordkey4_led_index6 = positions[5];
        }

        // Get chord note 5 positions
        if (chordkey5) {
            uint8_t note5_idx = note + chordkey5 - 24 - transpose_number - octave_number;
            get_all_note_positions(current_layer, note5_idx, positions);
            chordkey5_led_index = positions[0];
            chordkey5_led_index2 = positions[1];
            chordkey5_led_index3 = positions[2];
            chordkey5_led_index4 = positions[3];
            chordkey5_led_index5 = positions[4];
            chordkey5_led_index6 = positions[5];
        }

        // Get chord note 6 positions
        if (chordkey6) {
            uint8_t note6_idx = note + chordkey6 - 24 - transpose_number - octave_number;
            get_all_note_positions(current_layer, note6_idx, positions);
            chordkey6_led_index = positions[0];
            chordkey6_led_index2 = positions[1];
            chordkey6_led_index3 = positions[2];
            chordkey6_led_index4 = positions[3];
            chordkey6_led_index5 = positions[4];
            chordkey6_led_index6 = positions[5];
        }

        // Get chord note 7 positions
        if (chordkey7) {
            uint8_t note7_idx = note + chordkey7 - 24 - transpose_number - octave_number;
            get_all_note_positions(current_layer, note7_idx, positions);
            chordkey7_led_index = positions[0];
            chordkey7_led_index2 = positions[1];
            chordkey7_led_index3 = positions[2];
            chordkey7_led_index4 = positions[3];
            chordkey7_led_index5 = positions[4];
            chordkey7_led_index6 = positions[5];
        }
    }
}

void noteondisplayupdates(uint8_t note) {
	
	uint16_t displaykeycode = note + 28931; // Convert MIDI note to your displaykeycode format
		    if (sustain_pedal_held) {
        add_to_pressed_list(displaykeycode);
    }
		
           if (heldkey1 == 0 && heldkey2 == 0 && heldkey3 == 0 && heldkey4 == 0 && heldkey5 == 0) {
    trueheldkey1 = displaykeycode - keysplitnumber + 24 + transpositionplaceholder;
    heldkey1 = ((trueheldkey1) % 12 + 12) % 12 + 1;
    heldkey1difference = (heldkey1 - 1) % 12;
    if (octaveheldkey1 == heldkey1 || octaveheldkey2 == heldkey1 || octaveheldkey3 == heldkey1 || octaveheldkey4 == heldkey1) {
        // Do nothing, continue as normal since we want heldkey1 to be filled
    }
} else if (heldkey1 != 0 && heldkey1 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey2 == 0 && heldkey3 == 0 && heldkey4 == 0 && heldkey5 == 0 && heldkey6 == 0) {
    trueheldkey2 = displaykeycode - keysplitnumber + 24 + transpositionplaceholder;
    heldkey2 = ((trueheldkey2) % 12 + 12) % 12 + 1;
    heldkey2difference = heldkey2 - heldkey1 + 1;
    if (heldkey2difference < 1) {
        heldkey2difference += 12;
    }
    else {}

    if (heldkey2 == heldkey1 || heldkey2 == heldkey3 || heldkey2 == heldkey4 || heldkey2 == heldkey5 || heldkey2 == heldkey6) {
        // Instead of setting heldkey2 to 0, we'll place it in octaveheldkey slots
        if (octaveheldkey1 == 0) {
            trueoctaveheldkey1 = trueheldkey2;
            octaveheldkey1 = heldkey2;
            octaveheldkey1difference = heldkey2difference;
        } else if (octaveheldkey2 == 0) {
            trueoctaveheldkey2 = trueheldkey2;
            octaveheldkey2 = heldkey2;
            octaveheldkey2difference = heldkey2difference;
        } else if (octaveheldkey3 == 0) {
            trueoctaveheldkey3 = trueheldkey2;
            octaveheldkey3 = heldkey2;
            octaveheldkey3difference = heldkey2difference;
        } else if (octaveheldkey4 == 0) {
            trueoctaveheldkey4 = trueheldkey2;
            octaveheldkey4 = heldkey2;
            octaveheldkey4difference = heldkey2difference;
        }
        heldkey2 = 0;
        trueheldkey2 = 0;
        heldkey2difference = 0;
    }
} else if (heldkey1 != 0 && heldkey1 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey2 != 0 && heldkey2 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey3 == 0 && heldkey4 == 0 && heldkey5 == 0 && heldkey6 == 0) {
    trueheldkey3 = displaykeycode - keysplitnumber + 24 + transpositionplaceholder;
    heldkey3 = ((trueheldkey3) % 12 + 12) % 12 + 1;
    heldkey3difference = heldkey3 - heldkey1 + 1;
    if (heldkey3difference < 1) {
        heldkey3difference += 12;
    }
    else {}

    if (heldkey3 == heldkey1 || heldkey3 == heldkey2 || heldkey3 == heldkey4 || heldkey3 == heldkey5 || heldkey3 == heldkey6) {
        if (octaveheldkey1 == 0) {
            trueoctaveheldkey1 = trueheldkey3;
            octaveheldkey1 = heldkey3;
            octaveheldkey1difference = heldkey3difference;
        } else if (octaveheldkey2 == 0) {
            trueoctaveheldkey2 = trueheldkey3;
            octaveheldkey2 = heldkey3;
            octaveheldkey2difference = heldkey3difference;
        } else if (octaveheldkey3 == 0) {
            trueoctaveheldkey3 = trueheldkey3;
            octaveheldkey3 = heldkey3;
            octaveheldkey3difference = heldkey3difference;
        } else if (octaveheldkey4 == 0) {
            trueoctaveheldkey4 = trueheldkey3;
            octaveheldkey4 = heldkey3;
            octaveheldkey4difference = heldkey3difference;
        }
        heldkey3 = 0;
        trueheldkey3 = 0;
        heldkey3difference = 0;
    }
} else if (heldkey1 != 0 && heldkey1 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey2 != 0 && heldkey2 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey3 != 0 && heldkey3 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey4 == 0 && heldkey5 == 0 && heldkey6 == 0) {
    trueheldkey4 = displaykeycode - keysplitnumber + 24 + transpositionplaceholder;
    heldkey4 = ((trueheldkey4) % 12 + 12) % 12 + 1;
    heldkey4difference = heldkey4 - heldkey1 + 1;
    if (heldkey4difference < 1) {
        heldkey4difference += 12;
    }
    else {}

    if (heldkey4 == heldkey1 || heldkey4 == heldkey2 || heldkey4 == heldkey3 || heldkey4 == heldkey5 || heldkey4 == heldkey6) {
        if (octaveheldkey1 == 0) {
            trueoctaveheldkey1 = trueheldkey4;
            octaveheldkey1 = heldkey4;
            octaveheldkey1difference = heldkey4difference;
        } else if (octaveheldkey2 == 0) {
            trueoctaveheldkey2 = trueheldkey4;
            octaveheldkey2 = heldkey4;
            octaveheldkey2difference = heldkey4difference;
        } else if (octaveheldkey3 == 0) {
            trueoctaveheldkey3 = trueheldkey4;
            octaveheldkey3 = heldkey4;
            octaveheldkey3difference = heldkey4difference;
        } else if (octaveheldkey4 == 0) {
            trueoctaveheldkey4 = trueheldkey4;
            octaveheldkey4 = heldkey4;
            octaveheldkey4difference = heldkey4difference;
        }
        heldkey4 = 0;
        trueheldkey4 = 0;
        heldkey4difference = 0;
    }
} else if (heldkey1 != 0 && heldkey1 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey2 != 0 && heldkey2 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey3 != 0 && heldkey3 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey4 != 0 && heldkey4 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey5 == 0 && heldkey6 == 0) {
    trueheldkey5 = displaykeycode - keysplitnumber + 24 + transpositionplaceholder;
    heldkey5 = ((trueheldkey5) % 12 + 12) % 12 + 1;
    heldkey5difference = heldkey5 - heldkey1 + 1;
    if (heldkey5difference < 1) {
        heldkey5difference += 12;
    }
    else {}

    if (heldkey5 == heldkey1 || heldkey5 == heldkey2 || heldkey5 == heldkey3 || heldkey5 == heldkey4 || heldkey5 == heldkey6) {
        if (octaveheldkey1 == 0) {
            trueoctaveheldkey1 = trueheldkey5;
            octaveheldkey1 = heldkey5;
            octaveheldkey1difference = heldkey5difference;
        } else if (octaveheldkey2 == 0) {
            trueoctaveheldkey2 = trueheldkey5;
            octaveheldkey2 = heldkey5;
            octaveheldkey2difference = heldkey5difference;
        } else if (octaveheldkey3 == 0) {
            trueoctaveheldkey3 = trueheldkey5;
            octaveheldkey3 = heldkey5;
            octaveheldkey3difference = heldkey5difference;
        } else if (octaveheldkey4 == 0) {
            trueoctaveheldkey4 = trueheldkey5;
            octaveheldkey4 = heldkey5;
            octaveheldkey4difference = heldkey5difference;
        }
        heldkey5 = 0;
        trueheldkey5 = 0;
        heldkey5difference = 0;
    }
} else if (heldkey1 != 0 && heldkey1 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey2 != 0 && heldkey2 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey3 != 0 && heldkey3 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey4 != 0 && heldkey4 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey5 != 0 && heldkey5 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey6 == 0) {
    trueheldkey6 = displaykeycode - keysplitnumber + 24 + transpositionplaceholder;
    heldkey6 = ((trueheldkey6) % 12 + 12) % 12 + 1;
    heldkey6difference = heldkey6 - heldkey1 + 1;
    if (heldkey6difference < 1) {
        heldkey6difference += 12;
    }
    else {}

    if (heldkey6 == heldkey1 || heldkey6 == heldkey2 || heldkey6 == heldkey3 || heldkey6 == heldkey4 || heldkey6 == heldkey5 || heldkey6 == heldkey7) {
        if (octaveheldkey1 == 0) {
            trueoctaveheldkey1 = trueheldkey6;
            octaveheldkey1 = heldkey6;
            octaveheldkey1difference = heldkey6difference;
        } else if (octaveheldkey2 == 0) {
            trueoctaveheldkey2 = trueheldkey6;
            octaveheldkey2 = heldkey6;
            octaveheldkey2difference = heldkey6difference;
        } else if (octaveheldkey3 == 0) {
            trueoctaveheldkey3 = trueheldkey6;
            octaveheldkey3 = heldkey6;
            octaveheldkey3difference = heldkey6difference;
        } else if (octaveheldkey4 == 0) {
            trueoctaveheldkey4 = trueheldkey6;
            octaveheldkey4 = heldkey6;
            octaveheldkey4difference = heldkey6difference;
        }
        heldkey6 = 0;
        trueheldkey6 = 0;
        heldkey6difference = 0;
    }
} else if (heldkey1 != 0 && heldkey1 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey2 != 0 && heldkey2 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey3 != 0 && heldkey3 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey4 != 0 && heldkey4 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey5 != 0 && heldkey5 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey6 != (displaykeycode - keysplitnumber + 24 + transpositionplaceholder) && heldkey7 == 0) {
    trueheldkey7 = displaykeycode - keysplitnumber + 24 + transpositionplaceholder;
    heldkey7 = ((trueheldkey7) % 12 + 12) % 12 + 1;
    heldkey7difference = heldkey7 - heldkey1 + 1;
    if (heldkey7difference < 1) {
        heldkey7difference += 12;
    }
    else {}

    if (heldkey7 == heldkey1 || heldkey7 == heldkey2 || heldkey7 == heldkey3 || heldkey7 == heldkey4 || heldkey7 == heldkey5 || heldkey7 == heldkey6) {
        if (octaveheldkey1 == 0) {
            trueoctaveheldkey1 = trueheldkey7;
            octaveheldkey1 = heldkey7;
            octaveheldkey1difference = heldkey7difference;
        } else if (octaveheldkey2 == 0) {
            trueoctaveheldkey2 = trueheldkey7;
            octaveheldkey2 = heldkey7;
            octaveheldkey2difference = heldkey7difference;
        } else if (octaveheldkey3 == 0) {
            trueoctaveheldkey3 = trueheldkey7;
            octaveheldkey3 = heldkey7;
            octaveheldkey3difference = heldkey7difference;
        } else if (octaveheldkey4 == 0) {
            trueoctaveheldkey4 = trueheldkey7;
            octaveheldkey4 = heldkey7;
            octaveheldkey4difference = heldkey7difference;
        }
        heldkey7 = 0;
        trueheldkey7 = 0;
        heldkey7difference = 0;
    }
}
update_keylog_display();
					
}
	
void noteoffdisplayupdates(uint8_t note) {
    uint16_t displaykeycode = note + 28931; // Convert MIDI note to your displaykeycode format
	    if (sustain_pedal_held) {
        add_to_released_list(displaykeycode);
    }
    
    // Only update visual held keys if sustain is not held
    if (!sustain_pedal_held) {
        // Your existing key release logic here...
        // All the existing held key management code
    chordkey1 = 0;
    chordkey1_led_index = 99;
    chordkey2_led_index = 99;
    chordkey3_led_index = 99;
    chordkey4_led_index = 99;
    chordkey5_led_index = 99;
    chordkey6_led_index = 99;
    chordkey7_led_index = 99;
    chordkey1_led_index2 = 99;
    chordkey2_led_index2 = 99;
    chordkey3_led_index2 = 99;
    chordkey4_led_index2 = 99;
    chordkey5_led_index2 = 99;
    chordkey6_led_index2 = 99;
    chordkey7_led_index2 = 99;
    chordkey1_led_index3 = 99;
    chordkey2_led_index3 = 99;
    chordkey3_led_index3 = 99;
    chordkey4_led_index3 = 99;
    chordkey5_led_index3 = 99;
    chordkey6_led_index3 = 99;
    chordkey7_led_index3 = 99;
    chordkey1_led_index4 = 99;
    chordkey2_led_index4 = 99;
    chordkey3_led_index4 = 99;
    chordkey4_led_index4 = 99;
    chordkey5_led_index4 = 99;
    chordkey6_led_index4 = 99;
    chordkey7_led_index4 = 99;
    chordkey1_led_index5 = 99;
    chordkey2_led_index5 = 99;
    chordkey3_led_index5 = 99;
    chordkey4_led_index5 = 99;
    chordkey5_led_index5 = 99;
    chordkey6_led_index5 = 99;
    chordkey7_led_index5 = 99;
    chordkey1_led_index6 = 99;
    chordkey2_led_index6 = 99;
    chordkey3_led_index6 = 99;
    chordkey4_led_index6 = 99;
    chordkey5_led_index6 = 99;
    chordkey6_led_index6 = 99;
    chordkey7_led_index6 = 99;
    
    // Handle octave key releases
	
		
 if (trueoctaveheldkey1 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    if (octaveheldkey2 != 0) {
        octaveheldkey1 = octaveheldkey2;
        octaveheldkey1difference = octaveheldkey2difference;
        trueoctaveheldkey1 = trueoctaveheldkey2;
        
        if (octaveheldkey3 != 0) {
            octaveheldkey2 = octaveheldkey3;
            octaveheldkey2difference = octaveheldkey3difference;
            trueoctaveheldkey2 = trueoctaveheldkey3;
            
            if (octaveheldkey4 != 0) {
                octaveheldkey3 = octaveheldkey4;
                octaveheldkey3difference = octaveheldkey4difference;
                trueoctaveheldkey3 = trueoctaveheldkey4;
                octaveheldkey4 = 0;
                octaveheldkey4difference = 0;
                trueoctaveheldkey4 = 0;
            } else {
                octaveheldkey3 = 0;
                octaveheldkey3difference = 0;
                trueoctaveheldkey3 = 0;
            }
        } else {
            octaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            trueoctaveheldkey2 = 0;
        }
    } else {
        octaveheldkey1 = 0;
        octaveheldkey1difference = 0;
        trueoctaveheldkey1 = 0;
    }
} 

if (trueoctaveheldkey2 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    if (octaveheldkey3 != 0) {
        octaveheldkey2 = octaveheldkey3;
        octaveheldkey2difference = octaveheldkey3difference;
        trueoctaveheldkey2 = trueoctaveheldkey3;
        
        if (octaveheldkey4 != 0) {
            octaveheldkey3 = octaveheldkey4;
            octaveheldkey3difference = octaveheldkey4difference;
            trueoctaveheldkey3 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            trueoctaveheldkey4 = 0;
        } else {
            octaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            trueoctaveheldkey3 = 0;
        }
    } else {
        octaveheldkey2 = 0;
        octaveheldkey2difference = 0;
        trueoctaveheldkey2 = 0;
    }
} 

if (trueoctaveheldkey3 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    if (octaveheldkey4 != 0) {
        octaveheldkey3 = octaveheldkey4;
        octaveheldkey3difference = octaveheldkey4difference;
        trueoctaveheldkey3 = trueoctaveheldkey4;
        octaveheldkey4 = 0;
        octaveheldkey4difference = 0;
        trueoctaveheldkey4 = 0;
    } else {
        octaveheldkey3 = 0;
        octaveheldkey3difference = 0;
        trueoctaveheldkey3 = 0;
    }
} 

if (trueoctaveheldkey4 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    octaveheldkey4 = 0;
    octaveheldkey4difference = 0;
    trueoctaveheldkey4 = 0;
} 

if (trueoctaveheldkey1 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    if (octaveheldkey2 != 0) {
        octaveheldkey1 = octaveheldkey2;
        octaveheldkey1difference = octaveheldkey2difference;
        trueoctaveheldkey1 = trueoctaveheldkey2;
        
        if (octaveheldkey3 != 0) {
            octaveheldkey2 = octaveheldkey3;
            octaveheldkey2difference = octaveheldkey3difference;
            trueoctaveheldkey2 = trueoctaveheldkey3;
            
            if (octaveheldkey4 != 0) {
                octaveheldkey3 = octaveheldkey4;
                octaveheldkey3difference = octaveheldkey4difference;
                trueoctaveheldkey3 = trueoctaveheldkey4;
                octaveheldkey4 = 0;
                octaveheldkey4difference = 0;
                trueoctaveheldkey4 = 0;
            } else {
                octaveheldkey3 = 0;
                octaveheldkey3difference = 0;
                trueoctaveheldkey3 = 0;
            }
        } else {
            octaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            trueoctaveheldkey2 = 0;
        }
    } else {
        octaveheldkey1 = 0;
        octaveheldkey1difference = 0;
        trueoctaveheldkey1 = 0;
    }
} 

if (trueoctaveheldkey2 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    if (octaveheldkey3 != 0) {
        octaveheldkey2 = octaveheldkey3;
        octaveheldkey2difference = octaveheldkey3difference;
        trueoctaveheldkey2 = trueoctaveheldkey3;
        
        if (octaveheldkey4 != 0) {
            octaveheldkey3 = octaveheldkey4;
            octaveheldkey3difference = octaveheldkey4difference;
            trueoctaveheldkey3 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            trueoctaveheldkey4 = 0;
        } else {
            octaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            trueoctaveheldkey3 = 0;
        }
    } else {
        octaveheldkey2 = 0;
        octaveheldkey2difference = 0;
        trueoctaveheldkey2 = 0;
    }
} 

if (trueoctaveheldkey3 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    if (octaveheldkey4 != 0) {
        octaveheldkey3 = octaveheldkey4;
        octaveheldkey3difference = octaveheldkey4difference;
        trueoctaveheldkey3 = trueoctaveheldkey4;
        octaveheldkey4 = 0;
        octaveheldkey4difference = 0;
        trueoctaveheldkey4 = 0;
    } else {
        octaveheldkey3 = 0;
        octaveheldkey3difference = 0;
        trueoctaveheldkey3 = 0;
    }
} 

if (trueoctaveheldkey4 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    octaveheldkey4 = 0;
    octaveheldkey4difference = 0;
    trueoctaveheldkey4 = 0;
} 

// Handle regular held keys
if (trueheldkey1 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    bool octaveMatch = false;
    
    // First check if this held key matches any octave key
    if (octaveheldkey1 != 0 || octaveheldkey2 != 0 || octaveheldkey3 != 0 || octaveheldkey4 != 0) {
        if (heldkey1 == octaveheldkey1) {
            heldkey1 = octaveheldkey1;
            trueheldkey1 = trueoctaveheldkey1;
            octaveheldkey1 = 0;
            trueoctaveheldkey1 = 0;
            octaveheldkey1difference = 0;
            octaveMatch = true;
        } else if (heldkey1 == octaveheldkey2) {
            heldkey1 = octaveheldkey2;
            trueheldkey1 = trueoctaveheldkey2;
            octaveheldkey2 = 0;
            trueoctaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            octaveMatch = true;
        } else if (heldkey1 == octaveheldkey3) {
            heldkey1 = octaveheldkey3;
            trueheldkey1 = trueoctaveheldkey3;
            octaveheldkey3 = 0;
            trueoctaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            octaveMatch = true;
        } else if (heldkey1 == octaveheldkey4) {
            heldkey1 = octaveheldkey4;
            trueheldkey1 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            trueoctaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            octaveMatch = true;
        }
    }
    
    // If no octave match was found, proceed with regular key shifting
    if (!octaveMatch) {
        if (heldkey2 != 0) {
            heldkey1 = heldkey2;
            trueheldkey1 = trueheldkey2;
            heldkey1difference = (heldkey1 - 1) % 12;
            
            if (heldkey3 != 0) {
                heldkey2 = heldkey3;
                heldkey2difference = heldkey2 - heldkey1 + 1; 
                if (heldkey2difference < 1) {heldkey2difference += 12;}
                trueheldkey2 = trueheldkey3;
            } else {  
                heldkey2 = 0;
                heldkey2difference = 0;        
                trueheldkey2 = 0; 
            }
                
            if (heldkey4 != 0) {
                heldkey3 = heldkey4;
                heldkey3difference = heldkey3 - heldkey1 + 1; 
                if (heldkey3difference < 1) {heldkey3difference += 12;}
                trueheldkey3 = trueheldkey4;
            } else {  
                heldkey3 = 0;
                heldkey3difference = 0;        
                trueheldkey3 = 0; 
            }
                
            if (heldkey5 != 0) {
                heldkey4 = heldkey5;
                heldkey4difference = heldkey4 - heldkey1 + 1;  
                if (heldkey4difference < 1) {heldkey4difference += 12;}         
                trueheldkey4 = trueheldkey5;
            } else {  
                heldkey4 = 0;
                heldkey4difference = 0;        
                trueheldkey4 = 0; 
            }
            
            if (heldkey6 != 0) {
                heldkey5 = heldkey6;
                heldkey5difference = heldkey5 - heldkey1 + 1;  
                if (heldkey5difference < 1) {heldkey5difference += 12;}        
                trueheldkey5 = trueheldkey6;
            } else {  
                heldkey5 = 0;
                heldkey5difference = 0;        
                trueheldkey5 = 0; 
            }
            
            if (heldkey7 != 0) {
                heldkey6 = heldkey7;
                heldkey6difference = heldkey6 - heldkey1 + 1;  
                if (heldkey6difference < 1) {heldkey6difference += 12;}          
                trueheldkey6 = trueheldkey7;
                heldkey7 = 0;
                heldkey7difference = 0;
                trueheldkey7 = 0;
            } else {  
                heldkey6 = 0;
                heldkey6difference = 0;        
                trueheldkey6 = 0; 
            }            
        } else {
            heldkey1 = 0;
            heldkey1difference = 0;
            trueheldkey1 = 0;
            rootnote = 13;
            bassnote = 13;
        }
    }
} 

else if (trueheldkey2 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    bool octaveMatch = false;
    
    // First check if this held key matches any octave key
    if (octaveheldkey1 != 0 || octaveheldkey2 != 0 || octaveheldkey3 != 0 || octaveheldkey4 != 0) {
        if (heldkey2 == octaveheldkey1) {
            heldkey2 = octaveheldkey1;
            trueheldkey2 = trueoctaveheldkey1;
            octaveheldkey1 = 0;
            trueoctaveheldkey1 = 0;
            octaveheldkey1difference = 0;
            octaveMatch = true;
        } else if (heldkey2 == octaveheldkey2) {
            heldkey2 = octaveheldkey2;
            trueheldkey2 = trueoctaveheldkey2;
            octaveheldkey2 = 0;
            trueoctaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            octaveMatch = true;
        } else if (heldkey2 == octaveheldkey3) {
            heldkey2 = octaveheldkey3;
            trueheldkey2 = trueoctaveheldkey3;
            octaveheldkey3 = 0;
            trueoctaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            octaveMatch = true;
        } else if (heldkey2 == octaveheldkey4) {
            heldkey2 = octaveheldkey4;
            trueheldkey2 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            trueoctaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            octaveMatch = true;
        }
    }
    
    // If no octave match was found, proceed with regular key shifting
    if (!octaveMatch) {
        if (heldkey3 != 0) {
            heldkey2 = heldkey3;
            heldkey2difference = heldkey3difference;
            trueheldkey2 = trueheldkey3;
            
            if (heldkey4 != 0) {
                heldkey3 = heldkey4;
                heldkey3difference = heldkey4difference;
                trueheldkey3 = trueheldkey4;
            } else {  
                heldkey3 = 0;
                heldkey3difference = 0;        
                trueheldkey3 = 0; 
            }
                
            if (heldkey5 != 0) {
                heldkey4 = heldkey5;
                heldkey4difference = heldkey5difference;           
                trueheldkey4 = trueheldkey5;
            } else {  
                heldkey4 = 0;
                heldkey4difference = 0;        
                trueheldkey4 = 0; 
            }
            
            if (heldkey6 != 0) {
                heldkey5 = heldkey6;
                heldkey5difference = heldkey6difference;           
                trueheldkey5 = trueheldkey6;
            } else {  
                heldkey5 = 0;
                heldkey5difference = 0;        
                trueheldkey5 = 0; 
            }
            
            if (heldkey7 != 0) {
                heldkey6 = heldkey7;
                heldkey6difference = heldkey7difference;           
                trueheldkey6 = trueheldkey7;
                heldkey7 = 0;
                heldkey7difference = 0;
                trueheldkey7 = 0;
            } else {  
                heldkey6 = 0;
                heldkey6difference = 0;        
                trueheldkey6 = 0; 
            }
        } else {
            heldkey2 = 0;
            heldkey2difference = 0;
            trueheldkey2 = 0;
        }
    }
} 

else if (trueheldkey3 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    bool octaveMatch = false;
    
    // First check if this held key matches any octave key
    if (octaveheldkey1 != 0 || octaveheldkey2 != 0 || octaveheldkey3 != 0 || octaveheldkey4 != 0) {
        if (heldkey3 == octaveheldkey1) {
            heldkey3 = octaveheldkey1;
            trueheldkey3 = trueoctaveheldkey1;
            octaveheldkey1 = 0;
            trueoctaveheldkey1 = 0;
            octaveheldkey1difference = 0;
            octaveMatch = true;
        } else if (heldkey3 == octaveheldkey2) {
            heldkey3 = octaveheldkey2;
            trueheldkey3 = trueoctaveheldkey2;
            octaveheldkey2 = 0;
            trueoctaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            octaveMatch = true;
        } else if (heldkey3 == octaveheldkey3) {
            heldkey3 = octaveheldkey3;
            trueheldkey3 = trueoctaveheldkey3;
            octaveheldkey3 = 0;
            trueoctaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            octaveMatch = true;
        } else if (heldkey3 == octaveheldkey4) {
            heldkey3 = octaveheldkey4;
            trueheldkey3 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            trueoctaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            octaveMatch = true;
        }
    }
    
    // If no octave match was found, proceed with regular key shifting
    if (!octaveMatch) {
        if (heldkey4 != 0) {
            heldkey3 = heldkey4;
            heldkey3difference = heldkey4difference;
            trueheldkey3 = trueheldkey4;
            
            if (heldkey5 != 0) {
                heldkey4 = heldkey5;
                heldkey4difference = heldkey5difference;           
                trueheldkey4 = trueheldkey5;
            } else {  
                heldkey4 = 0;
                heldkey4difference = 0;        
                trueheldkey4 = 0; 
            }
            
            if (heldkey6 != 0) {
                heldkey5 = heldkey6;
                heldkey5difference = heldkey6difference;           
                trueheldkey5 = trueheldkey6;
            } else {  
                heldkey5 = 0;
                heldkey5difference = 0;        
                trueheldkey5 = 0; 
            }
            
            if (heldkey7 != 0) {
                heldkey6 = heldkey7;
                heldkey6difference = heldkey7difference;           
                trueheldkey6 = trueheldkey7;
                heldkey7 = 0;
                heldkey7difference = 0;
                trueheldkey7 = 0;
            } else {  
                heldkey6 = 0;
                heldkey6difference = 0;        
                trueheldkey6 = 0; 
            }                        
        } else {
            heldkey3 = 0;
            heldkey3difference = 0;
            trueheldkey3 = 0;
        }
    }
}

else if (trueheldkey4 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    bool octaveMatch = false;
    
    // First check if this held key matches any octave key
    if (octaveheldkey1 != 0 || octaveheldkey2 != 0 || octaveheldkey3 != 0 || octaveheldkey4 != 0) {
        if (heldkey4 == octaveheldkey1) {
            heldkey4 = octaveheldkey1;
            trueheldkey4 = trueoctaveheldkey1;
            octaveheldkey1 = 0;
            trueoctaveheldkey1 = 0;
            octaveheldkey1difference = 0;
            octaveMatch = true;
        } else if (heldkey4 == octaveheldkey2) {
            heldkey4 = octaveheldkey2;
            trueheldkey4 = trueoctaveheldkey2;
            octaveheldkey2 = 0;
            trueoctaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            octaveMatch = true;
        } else if (heldkey4 == octaveheldkey3) {
            heldkey4 = octaveheldkey3;
            trueheldkey4 = trueoctaveheldkey3;
            octaveheldkey3 = 0;
            trueoctaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            octaveMatch = true;
        } else if (heldkey4 == octaveheldkey4) {
            heldkey4 = octaveheldkey4;
            trueheldkey4 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            trueoctaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            octaveMatch = true;
        }
    }
    
    // If no octave match was found, proceed with regular key shifting
    if (!octaveMatch) {
        if (heldkey5 != 0) {
            heldkey4 = heldkey5;
            heldkey4difference = heldkey5difference;           
            trueheldkey4 = trueheldkey5;
        
            if (heldkey6 != 0) {
                heldkey5 = heldkey6;
                heldkey5difference = heldkey6difference;           
                trueheldkey5 = trueheldkey6;
            } else {  
                heldkey5 = 0;
                heldkey5difference = 0;        
                trueheldkey5 = 0; 
            }
            
            if (heldkey7 != 0) {
                heldkey6 = heldkey7;
                heldkey6difference = heldkey7difference;           
                trueheldkey6 = trueheldkey7;
                heldkey7 = 0;
                heldkey7difference = 0;
                trueheldkey7 = 0;
            } else {  
                heldkey6 = 0;
                heldkey6difference = 0;        
                trueheldkey6 = 0; 
            }                
        } else {
            heldkey4 = 0;
            heldkey4difference = 0;
            trueheldkey4 = 0;
        }
    }
} 

else if (trueheldkey5 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    bool octaveMatch = false;
    
    // First check if this held key matches any octave key
    if (octaveheldkey1 != 0 || octaveheldkey2 != 0 || octaveheldkey3 != 0 || octaveheldkey4 != 0) {
        if (heldkey5 == octaveheldkey1) {
            heldkey5 = octaveheldkey1;
            trueheldkey5 = trueoctaveheldkey1;
            octaveheldkey1 = 0;
            trueoctaveheldkey1 = 0;
            octaveheldkey1difference = 0;
            octaveMatch = true;
        } else if (heldkey5 == octaveheldkey2) {
            heldkey5 = octaveheldkey2;
            trueheldkey5 = trueoctaveheldkey2;
            octaveheldkey2 = 0;
            trueoctaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            octaveMatch = true;
        } else if (heldkey5 == octaveheldkey3) {
            heldkey5 = octaveheldkey3;
            trueheldkey5 = trueoctaveheldkey3;
            octaveheldkey3 = 0;
            trueoctaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            octaveMatch = true;
        } else if (heldkey5 == octaveheldkey4) {
            heldkey5 = octaveheldkey4;
            trueheldkey5 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            trueoctaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            octaveMatch = true;
        }
    }
    
    // If no octave match was found, proceed with regular key shifting
    if (!octaveMatch) {
        if (heldkey6 != 0) {
            heldkey5 = heldkey6;
            heldkey5difference = heldkey6difference;           
            trueheldkey5 = trueheldkey6;

            if (heldkey7 != 0) {
                heldkey6 = heldkey7;
                heldkey6difference = heldkey7difference;           
                trueheldkey6 = trueheldkey7;
                heldkey7 = 0;
                heldkey7difference = 0;
                trueheldkey7 = 0;
            } else {
                heldkey6 = 0;
                heldkey6difference = 0;        
                trueheldkey6 = 0; 
            }
        } else {
            heldkey5 = 0;
            heldkey5difference = 0;
            trueheldkey5 = 0;
        }
    }
} 

else if (trueheldkey6 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    bool octaveMatch = false;
    
    // First check if this held key matches any octave key
    if (octaveheldkey1 != 0 || octaveheldkey2 != 0 || octaveheldkey3 != 0 || octaveheldkey4 != 0) {
        if (heldkey6 == octaveheldkey1) {
            heldkey6 = octaveheldkey1;
            trueheldkey6 = trueoctaveheldkey1;
            octaveheldkey1 = 0;
            trueoctaveheldkey1 = 0;
            octaveheldkey1difference = 0;
            octaveMatch = true;
        } else if (heldkey6 == octaveheldkey2) {
            heldkey6 = octaveheldkey2;
            trueheldkey6 = trueoctaveheldkey2;
            octaveheldkey2 = 0;
            trueoctaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            octaveMatch = true;
        } else if (heldkey6 == octaveheldkey3) {
            heldkey6 = octaveheldkey3;
            trueheldkey6 = trueoctaveheldkey3;
            octaveheldkey3 = 0;
            trueoctaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            octaveMatch = true;
        } else if (heldkey6 == octaveheldkey4) {
            heldkey6 = octaveheldkey4;
            trueheldkey6 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            trueoctaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            octaveMatch = true;
        }
    }
    
    // If no octave match was found, proceed with regular key shifting
    if (!octaveMatch) {
        if (heldkey7 != 0) {
            heldkey6 = heldkey7;
            heldkey6difference = heldkey7difference;           
            trueheldkey6 = trueheldkey7;
            heldkey7 = 0;
            heldkey7difference = 0;
            trueheldkey7 = 0;
        } else {
            heldkey6 = 0;
            heldkey6difference = 0;        
            trueheldkey6 = 0;
        }
    }
} 

else if (trueheldkey7 == (displaykeycode - keysplitnumber + 24 + transpositionplaceholder)) {
    bool octaveMatch = false;
    
    // First check if this held key matches any octave key
    if (octaveheldkey1 != 0 || octaveheldkey2 != 0 || octaveheldkey3 != 0 || octaveheldkey4 != 0) {
        if (heldkey7 == octaveheldkey1) {
            heldkey7 = octaveheldkey1;
            trueheldkey7 = trueoctaveheldkey1;
            octaveheldkey1 = 0;
            trueoctaveheldkey1 = 0;
            octaveheldkey1difference = 0;
            octaveMatch = true;
        } else if (heldkey7 == octaveheldkey2) {
            heldkey7 = octaveheldkey2;
            trueheldkey7 = trueoctaveheldkey2;
            octaveheldkey2 = 0;
            trueoctaveheldkey2 = 0;
            octaveheldkey2difference = 0;
            octaveMatch = true;
        } else if (heldkey7 == octaveheldkey3) {
            heldkey7 = octaveheldkey3;
            trueheldkey7 = trueoctaveheldkey3;
            octaveheldkey3 = 0;
            trueoctaveheldkey3 = 0;
            octaveheldkey3difference = 0;
            octaveMatch = true;
        } else if (heldkey7 == octaveheldkey4) {
            heldkey7 = octaveheldkey4;
            trueheldkey7 = trueoctaveheldkey4;
            octaveheldkey4 = 0;
            trueoctaveheldkey4 = 0;
            octaveheldkey4difference = 0;
            octaveMatch = true;
        }
    }
    
    // If no octave match was found, proceed with regular key shifting
    if (!octaveMatch) {
        heldkey7 = 0;
        heldkey7difference = 0;
        trueheldkey7 = 0;
    }

    }
}
update_keylog_display();			
}

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
    static uint8_t base_note = 0;
    static uint8_t interval_note = 0;

    // Exit EEPROM diagnostic display mode on any keypress
    if (eeprom_diag_display_mode && record->event.pressed) {
        eeprom_diag_display_mode = false;
        return true;  // Continue processing the keypress
    }

    // =============================================================================
    // TOGGLE KEYS (TGL_00 - TGL_99, keycodes 0xEE00-0xEE63)
    // =============================================================================
    if (is_toggle_keycode(keycode)) {
        toggle_process_key(keycode, record->event.pressed);
        set_keylog(keycode, record);
        return false;  // Skip further processing
    }

    // MIDI Routing Toggle Keycodes
    if (keycode == MIDI_IN_MODE_TOG) {
        if (record->event.pressed) {
            toggle_midi_in_mode();
            set_keylog(keycode, record);
        }
        return false;  // Skip further processing
    }

    if (keycode == USB_MIDI_MODE_TOG) {
        if (record->event.pressed) {
            toggle_usb_midi_mode();
            set_keylog(keycode, record);
        }
        return false;  // Skip further processing
    }

    if (keycode == MIDI_CLOCK_SRC_TOG) {
        if (record->event.pressed) {
            toggle_midi_clock_source();
            set_keylog(keycode, record);
        }
        return false;  // Skip further processing
    }

    // =============================================================================
    // ARPEGGIATOR & STEP SEQUENCER KEYCODES (0xCD00-0xCDFF)
    // =============================================================================

    // ARPEGGIATOR CONTROL KEYCODES (0xEE00-0xEE0F)
    if (keycode == ARP_PLAY) {
        if (record->event.pressed) {
            arp_handle_key_press(arp_state.current_preset_id);
        } else {
            arp_handle_key_release();
        }
        set_keylog(keycode, record);
        return false;
    }

    if (keycode == ARP_NEXT_PRESET) {
        if (record->event.pressed) {
            arp_next_preset();
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_PREV_PRESET) {
        if (record->event.pressed) {
            arp_prev_preset();
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_SYNC_TOGGLE) {
        if (record->event.pressed) {
            arp_toggle_sync_mode();
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_GATE_UP) {
        if (record->event.pressed) {
            uint8_t current_gate = (arp_state.master_gate_override > 0) ?
                                   arp_state.master_gate_override : 80;
            if (current_gate <= 90) current_gate += 10;
            arp_set_master_gate(current_gate);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_GATE_DOWN) {
        if (record->event.pressed) {
            uint8_t current_gate = (arp_state.master_gate_override > 0) ?
                                   arp_state.master_gate_override : 80;
            if (current_gate >= 10) current_gate -= 10;
            arp_set_master_gate(current_gate);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_GATE_RESET) {
        if (record->event.pressed) {
            arp_state.master_gate_override = 0;
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_RESET_TO_DEFAULT) {
        if (record->event.pressed) {
            arp_reset_overrides();
            set_keylog(keycode, record);
        }
        return false;
    }

    // ARPEGGIATOR RATE OVERRIDES (0xCD10-0xCD1B)
    if (keycode >= ARP_RATE_QUARTER && keycode <= ARP_RATE_SIXTEENTH_TRIP) {
        if (record->event.pressed) {
            uint8_t note_value, timing_mode;
            switch (keycode) {
                case ARP_RATE_QUARTER: note_value = NOTE_VALUE_QUARTER; timing_mode = TIMING_MODE_STRAIGHT; break;
                case ARP_RATE_QUARTER_DOT: note_value = NOTE_VALUE_QUARTER; timing_mode = TIMING_MODE_DOTTED; break;
                case ARP_RATE_QUARTER_TRIP: note_value = NOTE_VALUE_QUARTER; timing_mode = TIMING_MODE_TRIPLET; break;
                case ARP_RATE_EIGHTH: note_value = NOTE_VALUE_EIGHTH; timing_mode = TIMING_MODE_STRAIGHT; break;
                case ARP_RATE_EIGHTH_DOT: note_value = NOTE_VALUE_EIGHTH; timing_mode = TIMING_MODE_DOTTED; break;
                case ARP_RATE_EIGHTH_TRIP: note_value = NOTE_VALUE_EIGHTH; timing_mode = TIMING_MODE_TRIPLET; break;
                case ARP_RATE_SIXTEENTH: note_value = NOTE_VALUE_SIXTEENTH; timing_mode = TIMING_MODE_STRAIGHT; break;
                case ARP_RATE_SIXTEENTH_DOT: note_value = NOTE_VALUE_SIXTEENTH; timing_mode = TIMING_MODE_DOTTED; break;
                case ARP_RATE_SIXTEENTH_TRIP: note_value = NOTE_VALUE_SIXTEENTH; timing_mode = TIMING_MODE_TRIPLET; break;
                default: note_value = NOTE_VALUE_QUARTER; timing_mode = TIMING_MODE_STRAIGHT; break;
            }
            arp_set_rate_override(note_value, timing_mode);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_RATE_RESET) {
        if (record->event.pressed) {
            arp_state.rate_override = 0;
            set_keylog(keycode, record);
        }
        return false;
    }

    // NEW: Arpeggiator Rate Up/Down
    if (keycode == ARP_RATE_UP) {
        if (record->event.pressed) {
            arp_rate_up();
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_RATE_DOWN) {
        if (record->event.pressed) {
            arp_rate_down();
            set_keylog(keycode, record);
        }
        return false;
    }

    // NEW: Arpeggiator Static Gate Values (0xEEEB-0xEEF4)
    if (keycode >= ARP_SET_GATE_10 && keycode <= ARP_SET_GATE_100) {
        if (record->event.pressed) {
            uint8_t gate_value = 10 + ((keycode - ARP_SET_GATE_10) * 10);
            arp_set_gate_static(gate_value);
            set_keylog(keycode, record);
        }
        return false;
    }

    // ARPEGGIATOR MODES (0xEE24-0xEE28)
    if (keycode == ARP_MODE_SINGLE_SYNCED) {
        if (record->event.pressed) {
            arp_set_mode(ARPMODE_SINGLE_NOTE_SYNCED);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_MODE_SINGLE_UNSYNCED) {
        if (record->event.pressed) {
            arp_set_mode(ARPMODE_SINGLE_NOTE_UNSYNCED);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_MODE_CHORD_SYNCED) {
        if (record->event.pressed) {
            arp_set_mode(ARPMODE_CHORD_SYNCED);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_MODE_CHORD_UNSYNCED) {
        if (record->event.pressed) {
            arp_set_mode(ARPMODE_CHORD_UNSYNCED);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == ARP_MODE_CHORD_ADVANCED) {
        if (record->event.pressed) {
            arp_set_mode(ARPMODE_CHORD_ADVANCED);
            set_keylog(keycode, record);
        }
        return false;
    }

    // DIRECT ARPEGGIATOR PRESET SELECTION (0xEE30 + preset_id, 68 presets: 0-67)
    // Smart behavior: press to toggle/switch, checks BPM and initializes if needed
    if (keycode >= ARP_PRESET_BASE && keycode < ARP_PRESET_BASE + 68) {
        uint8_t preset_id = keycode - ARP_PRESET_BASE;
        if (preset_id < MAX_ARP_PRESETS) {
            if (record->event.pressed) {
                arp_handle_key_press(preset_id);
            } else {
                arp_handle_key_release();
            }
            set_keylog(keycode, record);
        }
        return false;
    }

    // STEP SEQUENCER CONTROL KEYCODES (0xEE80-0xEE8F)
    // SEQ_PLAY: Press to toggle, Hold to stop all
    if (keycode == SEQ_PLAY) {
        if (record->event.pressed) {
            seq_play_press_time = timer_read32();
            set_keylog(keycode, record);
        } else {
            // Release: check if held
            uint32_t hold_duration = timer_read32() - seq_play_press_time;
            if (hold_duration >= SEQ_HOLD_THRESHOLD) {
                // Held: stop and clear all sequences
                seq_stop_all();
                dprintf("seq: held - stopped all sequences\n");
            } else {
                // Quick press: toggle current preset
                uint8_t current = seq_state[0].current_preset_id;
                seq_select_preset(current);
            }
        }
        return false;
    }

    if (keycode == SEQ_STOP_ALL) {
        if (record->event.pressed) {
            seq_stop_all();
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_NEXT_PRESET) {
        if (record->event.pressed) {
            seq_next_preset();
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_PREV_PRESET) {
        if (record->event.pressed) {
            seq_prev_preset();
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_SYNC_TOGGLE) {
        if (record->event.pressed) {
            seq_toggle_sync_mode();
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_GATE_UP) {
        if (record->event.pressed) {
            // Get current gate from first active slot, or default to 80
            uint8_t current_gate = 80;
            for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
                if (seq_state[i].active && seq_state[i].master_gate_override > 0) {
                    current_gate = seq_state[i].master_gate_override;
                    break;
                }
            }
            if (current_gate <= 90) current_gate += 10;
            seq_set_master_gate(current_gate);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_GATE_DOWN) {
        if (record->event.pressed) {
            // Get current gate from first active slot, or default to 80
            uint8_t current_gate = 80;
            for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
                if (seq_state[i].active && seq_state[i].master_gate_override > 0) {
                    current_gate = seq_state[i].master_gate_override;
                    break;
                }
            }
            if (current_gate >= 20) current_gate -= 10;
            seq_set_master_gate(current_gate);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_GATE_RESET) {
        if (record->event.pressed) {
            for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
                seq_state[i].master_gate_override = 0;
            }
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_RESET_TO_DEFAULT) {
        if (record->event.pressed) {
            seq_reset_overrides();
            set_keylog(keycode, record);
        }
        return false;
    }

    // =============================================================================
    // QUICK BUILD BUTTONS (0xEF0D-0xEF15)
    // =============================================================================

    // ARPEGGIATOR QUICK BUILD
    if (keycode == ARP_QUICK_BUILD) {
        if (record->event.pressed) {
            // Record press time for 3-second hold detection
            quick_build_state.button_press_time = timer_read32();

            if (quick_build_state.has_saved_build && quick_build_state.mode == QUICK_BUILD_NONE) {
                // Has saved build and not currently building: toggle play
                arp_toggle();
            } else if (quick_build_state.mode == QUICK_BUILD_ARP) {
                // Currently building arp: finish and save
                quick_build_finish();
            } else {
                // Start new arp quick build
                quick_build_start_arp();
            }
        } else {
            // Button released: check for 3-second hold
            if (timer_elapsed32(quick_build_state.button_press_time) > 3000) {
                // Held for 3+ seconds: erase saved build
                quick_build_erase();
            }
        }
        set_keylog(keycode, record);
        return false;
    }

    // STEP SEQUENCER QUICK BUILD (8 buttons for 8 slots)
    if (keycode >= SEQ_QUICK_BUILD_1 && keycode <= SEQ_QUICK_BUILD_8) {
        uint8_t slot = keycode - SEQ_QUICK_BUILD_1;  // 0-7

        if (record->event.pressed) {
            // Record press time for 3-second hold detection
            quick_build_state.button_press_time = timer_read32();

            if (quick_build_state.has_saved_build &&
                quick_build_state.mode == QUICK_BUILD_NONE &&
                quick_build_state.seq_slot == slot) {
                // Has saved build for this slot and not currently building: toggle play
                seq_start(seq_state[slot].current_preset_id);
            } else if (quick_build_state.mode == QUICK_BUILD_SEQ &&
                       quick_build_state.seq_slot == slot) {
                // Currently building this seq slot: finish and save
                quick_build_finish();
            } else {
                // Start new seq quick build for this slot
                quick_build_start_seq(slot);
            }
        } else {
            // Button released: check for 3-second hold
            if (quick_build_state.seq_slot == slot &&
                timer_elapsed32(quick_build_state.button_press_time) > 3000) {
                // Held for 3+ seconds: erase saved build for this slot
                quick_build_erase();
            }
        }
        set_keylog(keycode, record);
        return false;
    }

    // STEP SEQUENCER RATE OVERRIDES (0xCD90-0xCD9B)
    if (keycode >= SEQ_RATE_QUARTER && keycode <= SEQ_RATE_SIXTEENTH_TRIP) {
        if (record->event.pressed) {
            uint8_t note_value, timing_mode;
            switch (keycode) {
                case SEQ_RATE_QUARTER: note_value = NOTE_VALUE_QUARTER; timing_mode = TIMING_MODE_STRAIGHT; break;
                case SEQ_RATE_QUARTER_DOT: note_value = NOTE_VALUE_QUARTER; timing_mode = TIMING_MODE_DOTTED; break;
                case SEQ_RATE_QUARTER_TRIP: note_value = NOTE_VALUE_QUARTER; timing_mode = TIMING_MODE_TRIPLET; break;
                case SEQ_RATE_EIGHTH: note_value = NOTE_VALUE_EIGHTH; timing_mode = TIMING_MODE_STRAIGHT; break;
                case SEQ_RATE_EIGHTH_DOT: note_value = NOTE_VALUE_EIGHTH; timing_mode = TIMING_MODE_DOTTED; break;
                case SEQ_RATE_EIGHTH_TRIP: note_value = NOTE_VALUE_EIGHTH; timing_mode = TIMING_MODE_TRIPLET; break;
                case SEQ_RATE_SIXTEENTH: note_value = NOTE_VALUE_SIXTEENTH; timing_mode = TIMING_MODE_STRAIGHT; break;
                case SEQ_RATE_SIXTEENTH_DOT: note_value = NOTE_VALUE_SIXTEENTH; timing_mode = TIMING_MODE_DOTTED; break;
                case SEQ_RATE_SIXTEENTH_TRIP: note_value = NOTE_VALUE_SIXTEENTH; timing_mode = TIMING_MODE_TRIPLET; break;
                default: note_value = NOTE_VALUE_QUARTER; timing_mode = TIMING_MODE_STRAIGHT; break;
            }
            seq_set_rate_override(note_value, timing_mode);
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_RATE_RESET) {
        if (record->event.pressed) {
            for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
                seq_state[i].rate_override = 0;
            }
            set_keylog(keycode, record);
        }
        return false;
    }

    // NEW: Step Sequencer Rate Up/Down
    if (keycode == SEQ_RATE_UP) {
        if (record->event.pressed) {
            // Check if any sequencer modifier is held
            bool modifier_held = false;
            for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
                if (seq_modifier_held[i]) {
                    seq_rate_up_for_slot(i);
                    modifier_held = true;
                }
            }
            // If no modifier held, affect all active slots
            if (!modifier_held) {
                seq_rate_up();
            }
            set_keylog(keycode, record);
        }
        return false;
    }

    if (keycode == SEQ_RATE_DOWN) {
        if (record->event.pressed) {
            // Check if any sequencer modifier is held
            bool modifier_held = false;
            for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
                if (seq_modifier_held[i]) {
                    seq_rate_down_for_slot(i);
                    modifier_held = true;
                }
            }
            // If no modifier held, affect all active slots
            if (!modifier_held) {
                seq_rate_down();
            }
            set_keylog(keycode, record);
        }
        return false;
    }

    // NEW: Step Sequencer Static Gate Values (0xEEF7-0xEF00)
    if (keycode >= STEP_SET_GATE_10 && keycode <= STEP_SET_GATE_100) {
        if (record->event.pressed) {
            uint8_t gate_value = 10 + ((keycode - STEP_SET_GATE_10) * 10);
            // Check if any sequencer modifier is held
            bool modifier_held = false;
            for (uint8_t i = 0; i < MAX_SEQ_SLOTS; i++) {
                if (seq_modifier_held[i]) {
                    seq_set_gate_for_slot(i, gate_value);
                    modifier_held = true;
                }
            }
            // If no modifier held, affect all active slots
            if (!modifier_held) {
                seq_set_gate_static(gate_value);
            }
            set_keylog(keycode, record);
        }
        return false;
    }

    // NEW: Step Sequencer Modifiers (0xEF01-0xEF08)
    if (keycode >= SEQ_MOD_1 && keycode <= SEQ_MOD_8) {
        uint8_t slot = keycode - SEQ_MOD_1;
        if (record->event.pressed) {
            seq_modifier_held[slot] = true;
        } else {
            seq_modifier_held[slot] = false;
        }
        set_keylog(keycode, record);
        return false;
    }

    // DIRECT STEP SEQUENCER PRESET SELECTION (0xEEA0 + offset, 68 presets map to firmware IDs 68-135)
    // Smart behavior: Press to toggle/add, Hold to stop all
    if (keycode >= SEQ_PRESET_BASE && keycode < SEQ_PRESET_BASE + 68) {
        uint8_t preset_id = 68 + (keycode - SEQ_PRESET_BASE);  // Map keycode offset to seq preset range (68-135)
        if (record->event.pressed) {
            seq_preset_press_time = timer_read32();
            seq_preset_held_keycode = keycode;
            set_keylog(keycode, record);
        } else {
            // Release: check if held
            if (seq_preset_held_keycode == keycode) {
                uint32_t hold_duration = timer_read32() - seq_preset_press_time;
                if (hold_duration >= SEQ_HOLD_THRESHOLD) {
                    // Held: stop and clear all sequences
                    seq_stop_all();
                    dprintf("seq: held preset button - stopped all sequences\n");
                } else {
                    // Quick press: smart toggle/add to slot
                    if (preset_id < MAX_SEQ_PRESETS) {
                        seq_select_preset(preset_id);
                    }
                }
                seq_preset_held_keycode = 0;
            }
        }
        return false;
    }

    // HE Velocity Curve Controls (global settings)
    if (keycode == HE_VEL_CURVE_UP) {
        if (record->event.pressed) {
            keyboard_settings.he_velocity_curve = (keyboard_settings.he_velocity_curve + 1) % 5;
            dprintf("Global HE Velocity Curve: %d\n", keyboard_settings.he_velocity_curve);
        }
        return false;
    }

    if (keycode == HE_VEL_CURVE_DOWN) {
        if (record->event.pressed) {
            if (keyboard_settings.he_velocity_curve == 0) {
                keyboard_settings.he_velocity_curve = 4;
            } else {
                keyboard_settings.he_velocity_curve--;
            }
            dprintf("Global HE Velocity Curve: %d\n", keyboard_settings.he_velocity_curve);
        }
        return false;
    }

    // Direct HE Curve Selection - affects ALL layers
    if (keycode >= HE_CURVE_SOFTEST && keycode <= HE_CURVE_HARDEST) {
        if (record->event.pressed) {
            uint8_t curve_value = keycode - HE_CURVE_SOFTEST;
            // Update ALL layers
            // Update global HE velocity curve
            keyboard_settings.he_velocity_curve = curve_value;
            dprintf("All layers HE Curve: %d\n", curve_value);
            set_keylog(keycode, record);
        }
        return false;
    }

    // Macro-aware HE Velocity Controls (0xEC90-0xEC95)
    // These modify the macro recording curve/min/max if a macro is recording,
    // otherwise they modify the global settings
    if (keycode >= HE_MACRO_CURVE_UP && keycode <= HE_MACRO_MAX_DOWN) {
        if (record->event.pressed) {
            if (current_macro_id > 0) {
                // A macro is recording - modify the macro's recording settings
                uint8_t curve = get_macro_recording_curve(current_macro_id);
                uint8_t min = get_macro_recording_min(current_macro_id);
                uint8_t max = get_macro_recording_max(current_macro_id);

                switch (keycode) {
                    case HE_MACRO_CURVE_UP:
                        curve = (curve + 1) % 5;  // 0-4: SOFTEST, SOFT, MEDIUM, HARD, HARDEST
                        set_macro_recording_curve_target(current_macro_id, curve);
                        dprintf("Macro %d recording curve: %d\n", current_macro_id, curve);
                        break;
                    case HE_MACRO_CURVE_DOWN:
                        curve = (curve == 0) ? 4 : (curve - 1);
                        set_macro_recording_curve_target(current_macro_id, curve);
                        dprintf("Macro %d recording curve: %d\n", current_macro_id, curve);
                        break;
                    case HE_MACRO_MIN_UP:
                        if (min < 127) min++;
                        set_macro_recording_min_target(current_macro_id, min);
                        dprintf("Macro %d recording min: %d\n", current_macro_id, min);
                        break;
                    case HE_MACRO_MIN_DOWN:
                        if (min > 1) min--;
                        set_macro_recording_min_target(current_macro_id, min);
                        dprintf("Macro %d recording min: %d\n", current_macro_id, min);
                        break;
                    case HE_MACRO_MAX_UP:
                        if (max < 127) max++;
                        set_macro_recording_max_target(current_macro_id, max);
                        dprintf("Macro %d recording max: %d\n", current_macro_id, max);
                        break;
                    case HE_MACRO_MAX_DOWN:
                        if (max > 1) max--;
                        set_macro_recording_max_target(current_macro_id, max);
                        dprintf("Macro %d recording max: %d\n", current_macro_id, max);
                        break;
                }
            } else if (keysplitmodifierheld) {
                // Keysplit modifier held - modify keysplit HE settings
                switch (keycode) {
                    case HE_MACRO_CURVE_UP:
                        keyboard_settings.keysplit_he_velocity_curve = (keyboard_settings.keysplit_he_velocity_curve + 1) % 5;
                        dprintf("Global Keysplit HE Curve: %d\n", keyboard_settings.keysplit_he_velocity_curve);
                        break;
                    case HE_MACRO_CURVE_DOWN:
                        if (keyboard_settings.keysplit_he_velocity_curve == 0) {
                            keyboard_settings.keysplit_he_velocity_curve = 4;
                        } else {
                            keyboard_settings.keysplit_he_velocity_curve--;
                        }
                        dprintf("Global Keysplit HE Curve: %d\n", keyboard_settings.keysplit_he_velocity_curve);
                        break;
                    case HE_MACRO_MIN_UP:
                        if (keyboard_settings.keysplit_he_velocity_min < 127) {
                            keyboard_settings.keysplit_he_velocity_min++;
                        }
                        dprintf("Global Keysplit HE Min: %d\n", keyboard_settings.keysplit_he_velocity_min);
                        break;
                    case HE_MACRO_MIN_DOWN:
                        if (keyboard_settings.keysplit_he_velocity_min > 1) {
                            keyboard_settings.keysplit_he_velocity_min--;
                        }
                        dprintf("Global Keysplit HE Min: %d\n", keyboard_settings.keysplit_he_velocity_min);
                        break;
                    case HE_MACRO_MAX_UP:
                        if (keyboard_settings.keysplit_he_velocity_max < 127) {
                            keyboard_settings.keysplit_he_velocity_max++;
                        }
                        dprintf("Global Keysplit HE Max: %d\n", keyboard_settings.keysplit_he_velocity_max);
                        break;
                    case HE_MACRO_MAX_DOWN:
                        if (keyboard_settings.keysplit_he_velocity_max > 1) {
                            keyboard_settings.keysplit_he_velocity_max--;
                        }
                        dprintf("Global Keysplit HE Max: %d\n", keyboard_settings.keysplit_he_velocity_max);
                        break;
                }
            } else if (triplesplitmodifierheld) {
                // Triplesplit modifier held - modify triplesplit HE settings
                switch (keycode) {
                    case HE_MACRO_CURVE_UP:
                        keyboard_settings.triplesplit_he_velocity_curve = (keyboard_settings.triplesplit_he_velocity_curve + 1) % 5;
                        dprintf("Global Triplesplit HE Curve: %d\n", keyboard_settings.triplesplit_he_velocity_curve);
                        break;
                    case HE_MACRO_CURVE_DOWN:
                        if (keyboard_settings.triplesplit_he_velocity_curve == 0) {
                            keyboard_settings.triplesplit_he_velocity_curve = 4;
                        } else {
                            keyboard_settings.triplesplit_he_velocity_curve--;
                        }
                        dprintf("Global Triplesplit HE Curve: %d\n", keyboard_settings.triplesplit_he_velocity_curve);
                        break;
                    case HE_MACRO_MIN_UP:
                        if (keyboard_settings.triplesplit_he_velocity_min < 127) {
                            keyboard_settings.triplesplit_he_velocity_min++;
                        }
                        dprintf("Global Triplesplit HE Min: %d\n", keyboard_settings.triplesplit_he_velocity_min);
                        break;
                    case HE_MACRO_MIN_DOWN:
                        if (keyboard_settings.triplesplit_he_velocity_min > 1) {
                            keyboard_settings.triplesplit_he_velocity_min--;
                        }
                        dprintf("Global Triplesplit HE Min: %d\n", keyboard_settings.triplesplit_he_velocity_min);
                        break;
                    case HE_MACRO_MAX_UP:
                        if (keyboard_settings.triplesplit_he_velocity_max < 127) {
                            keyboard_settings.triplesplit_he_velocity_max++;
                        }
                        dprintf("Global Triplesplit HE Max: %d\n", keyboard_settings.triplesplit_he_velocity_max);
                        break;
                    case HE_MACRO_MAX_DOWN:
                        if (keyboard_settings.triplesplit_he_velocity_max > 1) {
                            keyboard_settings.triplesplit_he_velocity_max--;
                        }
                        dprintf("Global Triplesplit HE Max: %d\n", keyboard_settings.triplesplit_he_velocity_max);
                        break;
                }
            } else {
                // No modifier held - modify main HE settings (global)
                switch (keycode) {
                    case HE_MACRO_CURVE_UP:
                        keyboard_settings.he_velocity_curve = (keyboard_settings.he_velocity_curve + 1) % 5;
                        dprintf("Global HE Velocity Curve: %d\n", keyboard_settings.he_velocity_curve);
                        break;
                    case HE_MACRO_CURVE_DOWN:
                        if (keyboard_settings.he_velocity_curve == 0) {
                            keyboard_settings.he_velocity_curve = 4;
                        } else {
                            keyboard_settings.he_velocity_curve--;
                        }
                        dprintf("Global HE Velocity Curve: %d\n", keyboard_settings.he_velocity_curve);
                        break;
                    case HE_MACRO_MIN_UP:
                        if (keyboard_settings.he_velocity_min < 127) {
                            keyboard_settings.he_velocity_min++;
                        }
                        dprintf("Global HE Velocity Min: %d\n", keyboard_settings.he_velocity_min);
                        break;
                    case HE_MACRO_MIN_DOWN:
                        if (keyboard_settings.he_velocity_min > 1) {
                            keyboard_settings.he_velocity_min--;
                        }
                        dprintf("Global HE Velocity Min: %d\n", keyboard_settings.he_velocity_min);
                        break;
                    case HE_MACRO_MAX_UP:
                        if (keyboard_settings.he_velocity_max < 127) {
                            keyboard_settings.he_velocity_max++;
                        }
                        dprintf("Global HE Velocity Max: %d\n", keyboard_settings.he_velocity_max);
                        break;
                    case HE_MACRO_MAX_DOWN:
                        if (keyboard_settings.he_velocity_max > 1) {
                            keyboard_settings.he_velocity_max--;
                        }
                        dprintf("Global HE Velocity Max: %d\n", keyboard_settings.he_velocity_max);
                        break;
                }
            }
            set_keylog(keycode, record);
        }
        return false;
    }

    // Direct HE Curve Selection (0xEC96-0xEC9A)
    // These set the curve to a specific value (0-4)
    // Macro-aware and modifier-aware
    if (keycode >= HE_MACRO_CURVE_0 && keycode <= HE_MACRO_CURVE_4) {
        if (record->event.pressed) {
            uint8_t curve_value = keycode - HE_MACRO_CURVE_0;  // 0-4

            if (current_macro_id > 0) {
                // A macro is recording - set the macro's recording curve
                set_macro_recording_curve_target(current_macro_id, curve_value);
                dprintf("Macro %d recording curve set to: %d\n", current_macro_id, curve_value);
            } else if (keysplitmodifierheld) {
                // Keysplit modifier held - set keysplit curve (global)
                keyboard_settings.keysplit_he_velocity_curve = curve_value;
                dprintf("Global Keysplit HE Curve set to: %d\n", curve_value);
            } else if (triplesplitmodifierheld) {
                // Triplesplit modifier held - set triplesplit curve (global)
                keyboard_settings.triplesplit_he_velocity_curve = curve_value;
                dprintf("Global Triplesplit HE Curve set to: %d\n", curve_value);
            } else {
                // No modifier held - set main HE curve (global)
                keyboard_settings.he_velocity_curve = curve_value;
                dprintf("Global HE Velocity Curve set to: %d\n", curve_value);
            }
            set_keylog(keycode, record);
        }
        return false;
    }

    // HE Velocity Range (min ≤ max only, 8,128 keycodes) - affects ALL layers
    if (keycode >= HE_VEL_RANGE_BASE && keycode < HE_VEL_RANGE_BASE + 8128) {
        if (record->event.pressed) {
            uint16_t offset = keycode - HE_VEL_RANGE_BASE;

            // Calculate min/max from offset using matching generation order
            uint8_t min_value = 1;
            uint8_t max_value = 1;
            uint16_t count = 0;

            for (uint8_t m = 1; m <= 127; m++) {
                for (uint8_t x = m; x <= 127; x++) {
                    if (count == offset) {
                        min_value = m;
                        max_value = x;
                        goto found;
                    }
                    count++;
                }
            }
            found:

            // Set both min and max simultaneously for ALL layers
            for (uint8_t i = 0; i < DYNAMIC_KEYMAP_LAYER_COUNT; i++) {
                keyboard_settings.he_velocity_min = min_value;
                keyboard_settings.he_velocity_max = max_value;
            }

            dprintf("All layers HE Vel Range: %d-%d\n", min_value, max_value);
            set_keylog(keycode, record);
        }
        return false;
    }

#ifdef JOYSTICK_ENABLE
    // Gaming Mode Toggle (0xCC60)
    if (keycode == 0xCC60) {
        if (record->event.pressed) {
            gaming_mode_active = !gaming_mode_active;
            gaming_settings.gaming_mode_enabled = gaming_mode_active;
            gaming_save_settings();
            dprintf("Gaming Mode: %s\n", gaming_mode_active ? "ON" : "OFF");
            set_keylog(keycode, record);
        }
        return false;
    }

    // Gaming button handlers (0xCC61-0xCC78)
    // These keycodes are handled by the gaming_update_joystick() in matrix_scan
    // But we still need to prevent them from triggering normal keyboard actions
    if (gaming_mode_active && keycode >= 0xCC61 && keycode <= 0xCC78) {
        // When gaming mode is active and these keys are mapped,
        // they should not send keyboard events
        // The actual joystick state is updated in gaming_update_joystick()
        set_keylog(keycode, record);
        return false;  // Suppress normal keyboard processing
    }
#endif

    if (keycode == 0xC929) {
        if (record->event.pressed) {
            // Key pressed - start timer
            tap_key_press_time = timer_read32();
            tap_key_held = true;
        } else {
            // Key released - clear timer
            tap_key_held = false;
            tap_key_press_time = 0;
        }
    }

    if (keycode >= 0xCC18 && keycode <= 0xCC1B) {
        uint8_t macro_idx = keycode - 0xCC18;
        
        if (record->event.pressed) {
            macro_modifier_held[macro_idx] = true;
        } else {
            macro_modifier_held[macro_idx] = false;
        }

    }
	
	    if (keycode >= 0xCC49 && keycode <= 0xCC4C) {    
		uint8_t macro_idx = keycode - 0xCC49;		
        if (record->event.pressed) {
			overdub_button_held = true;
			if (global_edit_modifier_held) { 
            macro_modifier_held[macro_idx] = true;
        } 			
        } else {
			macro_modifier_held[macro_idx] = false;
			overdub_button_held = false;
        }

    }
	
	    if (keycode >= 0xCC4D && keycode <= 0xCC50) {
        uint8_t macro_idx = keycode - 0xCC4D;
        
        if (record->event.pressed) {
			mute_button_held = true;
			overdub_button_held = true;
            macro_modifier_held[macro_idx] = true;
        } else {
			overdub_button_held = false;
			mute_button_held = false;
            macro_modifier_held[macro_idx] = false;
        }

    }
	
 if (keycode == 0xCC1C) {
		if (record->event.pressed) {
		} else {
			global_edit_modifier_held = false;
			
			// Clear all modifier states when releasing global modifier
			for (uint8_t i = 0; i < MAX_MACROS; i++) {
				if (modifier_held[i]) {
					modifier_held[i] = false;
				}
			}

		}
 }
	

 if (keycode >= 0xCC08 && keycode <= 0xCC0B) {
	     uint8_t macro_idx = keycode - 0xCC08;  // 0-3 for macros 1-4
		if (record->event.pressed) {
			if (global_edit_modifier_held) { 
            macro_modifier_held[macro_idx] = true;
        } 
	}	else {
            macro_modifier_held[macro_idx] = false;
        }
}
 

	
	if (keycode == 0x7186) { // Sustain pedal
    if (record->event.pressed) {
        // Sustain pedal pressed
        sustain_pedal_held = true;
        if (!sustain_keys_captured) {
            backup_held_keys_state();
            clear_sustain_tracking();
            sustain_keys_captured = true;
        }
    } else {
        // Sustain pedal released
        sustain_pedal_held = false;
        sustain_keys_captured = false;
        
        // Rebuild the held keys state
        clear_all_held_keys();
        rebuild_held_keys_from_sustain_state();
        
        // Clear tracking for next sustain session
        clear_sustain_tracking();
    }
}

	if (keycode == 0xcc57) { // aftertouch pedal
    if (record->event.pressed) {
        aftertouch_pedal_active = true;  // For matrix.c
        sustain_pedal_held = true;
		
        if (!sustain_keys_captured) {
            backup_held_keys_state();
            clear_sustain_tracking();
            sustain_keys_captured = true;
        }
    } else {
        // Sustain pedal released
        sustain_pedal_held = false;
        sustain_keys_captured = false;
        aftertouch_pedal_active = false;  // For matrix.c
    
        // Rebuild the held keys state
        clear_all_held_keys();
        rebuild_held_keys_from_sustain_state();
        
        // Clear tracking for next sustain session
        clear_sustain_tracking();
    }
}
	
	if (keycode >= 0xC961 && keycode <= 0xC9E0) {
		if (record->event.pressed) {
			ccencoder = keycode - 0xC961; // Set the CC number based on key pressed
		} else {
			ccencoder = 130; // Reset to invalid CC value when key is released
		}
		
	} else if (keycode == 0xC9F0) {
		if (record->event.pressed) {
			transposeencoder = 1; // Set the CC number based on key pressed
		} else {
			transposeencoder = 130; // Reset to invalid CC value when key is released
		}
		
	} else if (keycode == 0xC9F1) {
		if (record->event.pressed) {
			velocityencoder = 1; // Set the CC number based on key pressed
		} else {
			velocityencoder = 130; // Reset to invalid CC value when key is released
		}
		
	} else if (keycode == 0xC9F2) {
		if (record->event.pressed) {
			channelencoder = 1; // Set the CC number based on key pressed
		} else {
			channelencoder = 130; // Reset to invalid CC value when key is released
		}
	}
   
if (keycode >= 0xC92A && keycode <= 0xC93B) {
    uint8_t channel = channel_number;
    uint8_t velocity = he_velocity_min + ((he_velocity_max - he_velocity_min)/2);
    bool play_simultaneous = (keycode >= 0xC938);  // Changed to 0xC938 for the new 4 simultaneous modes
    uint16_t base_interval_code = play_simultaneous ? ((keycode * 3) - (0xC938 * 3) + 0xC92A) : keycode;   
    
    if (record->event.pressed) {
        smartchordstatus += 1;        
        // Cache the layer lookup once
        int8_t current_layer = get_highest_layer(layer_state | default_layer_state);	
        uint8_t positions[6];  // Reusable array for positions
        
        // Generate random base note between 24 and 36 semitones above 28931
        uint16_t base_keycode = 28931 + (rand() % 13) + 24;
        base_note = midi_compute_note(base_keycode);
        
        // Calculate held key values for base note
        trueheldkey1 = base_keycode - 28931;
        heldkey1 = ((trueheldkey1 % 12) + 12) % 12 + 1;
        
        // Set LED indices for base note - optimized
        get_all_note_positions(current_layer, trueheldkey1, positions);
        chordkey1_led_index = positions[0];
        chordkey1_led_index2 = positions[1];
        chordkey1_led_index3 = positions[2];
        chordkey1_led_index4 = positions[3];
        chordkey1_led_index5 = positions[4];
        chordkey1_led_index6 = positions[5];
        
        // Generate interval based on keycode
        int interval = 0;
        switch(base_interval_code) {
            case 0xC92A: interval = (rand() % 7) + 1; break;                   // Up to P5
            case 0xC92B: interval = -((rand() % 7) + 1); break;               // Down to P5
            case 0xC92C:                                                       // Both P5
                interval = (rand() % 14) - 7;
                if (interval >= 0) interval++; 
                break;
            case 0xC92D: interval = (rand() % 12) + 1; break;                 // Up to oct
            case 0xC92E: interval = -((rand() % 12) + 1); break;              // Down to oct
            case 0xC92F:                                                       // Both oct
                interval = (rand() % 24) - 12;
                if (interval >= 0) interval++; 
                break;
            case 0xC930: interval = (rand() % 13) + 12; break;                // Up 12-24
            case 0xC931: interval = -((rand() % 13) + 12); break;             // Down 12-24
            case 0xC932: interval = ((rand() % 13) + 12) * (rand() % 2 ? 1 : -1); break; // Both 12-24
            case 0xC933: interval = (rand() % 24) + 1; break;                 // Up 1-24
            case 0xC934: interval = -((rand() % 24) + 1); break;              // Down 1-24
            case 0xC935:                                                       // Both 1-24
                interval = (rand() % 48) - 24;
                if (interval >= 0) interval++; 
                break;
        }
        
        // Store interval for chord recognition
        chordkey1 = interval;
        
        // Calculate interval note
        uint16_t interval_keycode = base_keycode + interval;
        interval_note = midi_compute_note(interval_keycode);
        
        // Calculate held key values for interval note
        trueheldkey2 = base_keycode - 28931 + interval;
        heldkey2 = ((trueheldkey2 % 12) + 12) % 12 + 1;
        heldkey2difference = heldkey2 - heldkey1 + 1;
        if (heldkey2difference < 1) {
            heldkey2difference += 12;
        }
        
        // Set LED indices for interval note - optimized
        get_all_note_positions(current_layer, trueheldkey2, positions);
        chordkey2_led_index = positions[0];
        chordkey2_led_index2 = positions[1];
        chordkey2_led_index3 = positions[2];
        chordkey2_led_index4 = positions[3];
        chordkey2_led_index5 = positions[4];
        chordkey2_led_index6 = positions[5];

        if (play_simultaneous) {
            // Simultaneous playback modes (0xC938-0xC93B)
            // Note: base_interval_code will map these back to the corresponding base intervals
            midi_send_noteon_smartchord(channel, base_note, velocity);
            midi_send_noteon_smartchord(channel, interval_note, velocity);
        } else {
            // Sequential playback with simultaneous at end (0xC92A-0xC937)
            midi_send_noteon_trainer(channel, base_note, velocity);
            wait_ms(1000);
            midi_send_noteon_trainer(channel, interval_note, velocity);
            
            // Stop all notes
            wait_ms(1200);
            midi_send_noteoff_trainer(channel, base_note, velocity);
            midi_send_noteoff_trainer(channel, interval_note, velocity);
            
            // Play simultaneously
            wait_ms(100);
            midi_send_noteon_smartchord(channel, base_note, velocity);
            midi_send_noteon_smartchord(channel, interval_note, velocity);
        }
        
        return false;
    } else {
        // On key release, stop all notes
        if (base_note != 0) {
            midi_send_noteoff_smartchord(channel, base_note, velocity);
        }
        if (interval_note != 0) {
            midi_send_noteoff_smartchord(channel, interval_note, velocity);
        }

        smartchordstatus -= 1;
        if (smartchordlight != 3) {
            smartchordlight = 0;
        }
        
        // Clear all LED indices
        chordkey1_led_index = 99; chordkey1_led_index2 = 99; chordkey1_led_index3 = 99;
        chordkey1_led_index4 = 99; chordkey1_led_index5 = 99; chordkey1_led_index6 = 99;
        chordkey2_led_index = 99; chordkey2_led_index2 = 99; chordkey2_led_index3 = 99;
        chordkey2_led_index4 = 99; chordkey2_led_index5 = 99; chordkey2_led_index6 = 99;
        
        // Reset all variables
        trueheldkey1 = 0;
        heldkey1 = 0;
        trueheldkey2 = 0;
        heldkey2 = 0;
        
        return false;
    }
}

			
if (keycode >= 0xCA10 && keycode <= 0xCC13) {
    if (record->event.pressed) {
        if (progression_active) {
            // If any progression is active, stop it
			stop_chord_progression();
            progression_active = false;
            progression_key_held = false;

        } else {
            // Start the progression
            start_progression_from_keycode(keycode);
            progression_key_held = true; // Keep this true since we're not holding
        }
    }
}


	if (keycode >= 0xC961 && keycode <= 0xC9E0) {
		if (record->event.pressed) {
		} else {
			ccencoder = 130; // Reset to invalid CC value when key is released
			
		}
		
	} if (keycode == 0xC9F0) {
		if (record->event.pressed) {
		} else {
			transposeencoder = 130; // Reset to invalid CC value when key is released

		}
		
	} if (keycode == 0xC9F1) {
		if (record->event.pressed) {
		} else {
			velocityencoder = 130; // Reset to invalid CC value when key is released

		}
		
	} if (keycode == 0xC9F2) {
		if (record->event.pressed) {
		} else {
			channelencoder = 130; // Reset to invalid CC value when key is released

		}
}

	if (keycode == 0xC9FE) {
		if (record->event.pressed) {
			// Space key pressed
			if (spaceheld == 0) {
				// Space not being held, send space and set flag
				register_code(KC_SPC);
				spaceheld = 1;
			}
			// If spaceheld is already 1, do nothing (ignore the press)
		} else {
			// Space key released
			if (spaceheld == 1) {
				unregister_code(KC_SPC);
				spaceheld = 0;
			}
		}
	}



if (record->event.pressed) {
    if (keycode == 0xC9E1) {
        scan_keycode_categories();
        rgb_matrix_mode(RGB_MATRIX_CUSTOM_MIDIswitch1);
        return false;
    }

	if (keycode >= 0xC9E2 && keycode <= 0xC9ED) {
            uint8_t layer = keycode - 0xC9E2;
            save_current_rgb_settings(layer);
            return false;
        }
        
	if (keycode == 0xC9EE) {
		rgb_matrix_mode(RGB_MATRIX_CUSTOM_LAYERSETS);
		custom_layer_animations_enabled = true;
		
		// Save the setting
		keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
		update_layer_animations_setting_slot0_direct(true);
	}

	if (keycode == 0xC9EF) {
		custom_layer_animations_enabled = false;
		
		// Save the setting
		keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
		update_layer_animations_setting_slot0_direct(false);
	}
	}
	


	
    
if (keycode >= 0xC93C && keycode <= 0xC94F) {
    uint8_t channel = channel_number;
    uint8_t velocity = he_velocity_min + ((he_velocity_max - he_velocity_min)/2);
    bool play_simultaneous = (keycode >= 0xC941 && keycode <= 0xC945) || 
                           (keycode >= 0xC94B && keycode <= 0xC94F);
    bool random_octave_down = (keycode >= 0xC946);
    
    uint16_t base_chord_code;
    if (keycode >= 0xC93C && keycode <= 0xC940) {
        base_chord_code = keycode;
    } else if (keycode >= 0xC941 && keycode <= 0xC945) {
        base_chord_code = keycode - 0xC941 + 0xC93C;
    } else if (keycode >= 0xC946 && keycode <= 0xC94A) {
        base_chord_code = keycode - 0xC946 + 0xC93C;
    } else {
        base_chord_code = keycode - 0xC94B + 0xC93C;
    }
    
    if (record->event.pressed) {
        smartchordstatus += 1;
        
        // Cache the layer lookup once
        int8_t current_layer = get_highest_layer(layer_state | default_layer_state);	
        uint8_t positions[6];  // Reusable array for positions
        
        uint16_t base_keycode = 28931 + (rand() % 6) + 6 + 24 + octave_number + transpose_number;
        uint8_t base_note = midi_compute_note(base_keycode);
        
        trueheldkey1 = base_keycode - 28931;
        heldkey1 = ((trueheldkey1 % 12) + 12) % 12 + 1;
        heldkey1difference = (heldkey1 - 1) % 12;

        // Update LED indices for base note - optimized
        uint8_t base_note_idx = trueheldkey1 - octave_number - transpose_number;
        get_all_note_positions(current_layer, base_note_idx, positions);
        chordkey1_led_index = positions[0];
        chordkey1_led_index2 = positions[1];
        chordkey1_led_index3 = positions[2];
        chordkey1_led_index4 = positions[3];
        chordkey1_led_index5 = positions[4];
        chordkey1_led_index6 = positions[5];
        
        int interval1 = 0, interval2 = 0, interval3 = 0;
        
        switch(base_chord_code) {
            case 0xC93C:  // Basic Triads
                switch(rand() % 4) {
                    case 0: interval1 = 4; interval2 = 7; break;  // Major
                    case 1: interval1 = 3; interval2 = 7; break;  // Minor
                    case 2: interval1 = 3; interval2 = 6; break;  // Diminished
                    case 3: interval1 = 4; interval2 = 8; break;  // Augmented
                }
                break;
                
            case 0xC93D:  // Basic 7ths
                switch(rand() % 3) {
                    case 0: interval1 = 4; interval2 = 7; interval3 = 10; break;  // Dominant 7
                    case 1: interval1 = 4; interval2 = 7; interval3 = 11; break;  // Major 7
                    case 2: interval1 = 3; interval2 = 7; interval3 = 10; break;  // Minor 7
                }
                break;
                
            case 0xC93E:  // All 7ths
                switch(rand() % 5) {
                    case 0: interval1 = 4; interval2 = 7; interval3 = 10; break;  // Dominant 7
                    case 1: interval1 = 4; interval2 = 7; interval3 = 11; break;  // Major 7
                    case 2: interval1 = 3; interval2 = 7; interval3 = 10; break;  // Minor 7
                    case 3: interval1 = 3; interval2 = 6; interval3 = 10; break;  // Half Diminished
                    case 4: interval1 = 3; interval2 = 6; interval3 = 9;  break;  // Diminished 7
                }
                break;
                
            case 0xC93F:  // Triads and Basic 7ths
                switch(rand() % 7) {
                    case 0: interval1 = 4; interval2 = 7; break;                  // Major
                    case 1: interval1 = 3; interval2 = 7; break;                  // Minor
                    case 2: interval1 = 3; interval2 = 6; break;                  // Diminished
                    case 3: interval1 = 4; interval2 = 8; break;                  // Augmented
                    case 4: interval1 = 4; interval2 = 7; interval3 = 10; break;  // Dominant 7
                    case 5: interval1 = 4; interval2 = 7; interval3 = 11; break;  // Major 7
                    case 6: interval1 = 3; interval2 = 7; interval3 = 10; break;  // Minor 7
                }
                break;
                
            case 0xC940:  // Triads and All 7ths
                switch(rand() % 9) {
                    case 0: interval1 = 4; interval2 = 7; break;                  // Major
                    case 1: interval1 = 3; interval2 = 7; break;                  // Minor
                    case 2: interval1 = 3; interval2 = 6; break;                  // Diminished
                    case 3: interval1 = 4; interval2 = 8; break;                  // Augmented
                    case 4: interval1 = 4; interval2 = 7; interval3 = 10; break;  // Dominant 7
                    case 5: interval1 = 4; interval2 = 7; interval3 = 11; break;  // Major 7
                    case 6: interval1 = 3; interval2 = 7; interval3 = 10; break;  // Minor 7
                    case 7: interval1 = 3; interval2 = 6; interval3 = 10; break;  // Half Diminished
                    case 8: interval1 = 3; interval2 = 6; interval3 = 9;  break;  // Diminished 7
                }
                break;
        }

        int octave_adjust1 = (random_octave_down && (rand() % 2 == 0)) ? -12 : 0;
        int octave_adjust2 = (random_octave_down && (rand() % 2 == 0)) ? -12 : 0;
        int octave_adjust3 = (random_octave_down && (rand() % 2 == 0)) ? -12 : 0;

        if (interval1 > 0) {
            trueheldkey2 = trueheldkey1 + interval1 + octave_adjust1;
            heldkey2 = ((trueheldkey2 % 12) + 12) % 12 + 1;
            heldkey2difference = heldkey2 - heldkey1 + 1;
            if (heldkey2difference < 1) heldkey2difference += 12;
            
            // Update LED indices for interval1 - optimized
            uint8_t note2_idx = trueheldkey2 - octave_number - transpose_number;
            get_all_note_positions(current_layer, note2_idx, positions);
            chordkey2_led_index = positions[0];
            chordkey2_led_index2 = positions[1];
            chordkey2_led_index3 = positions[2];
            chordkey2_led_index4 = positions[3];
            chordkey2_led_index5 = positions[4];
            chordkey2_led_index6 = positions[5];
        }

        if (interval2 > 0) {
            trueheldkey3 = trueheldkey1 + interval2 + octave_adjust2;
            heldkey3 = ((trueheldkey3 % 12) + 12) % 12 + 1;
            heldkey3difference = heldkey3 - heldkey1 + 1;
            if (heldkey3difference < 1) heldkey3difference += 12;
            
            // Update LED indices for interval2 - optimized
            uint8_t note3_idx = trueheldkey3 - octave_number - transpose_number;
            get_all_note_positions(current_layer, note3_idx, positions);
            chordkey3_led_index = positions[0];
            chordkey3_led_index2 = positions[1];
            chordkey3_led_index3 = positions[2];
            chordkey3_led_index4 = positions[3];
            chordkey3_led_index5 = positions[4];
            chordkey3_led_index6 = positions[5];
        }

        if (interval3 > 0) {
            trueheldkey4 = trueheldkey1 + interval3 + octave_adjust3;
            heldkey4 = ((trueheldkey4 % 12) + 12) % 12 + 1;
            heldkey4difference = heldkey4 - heldkey1 + 1;
            if (heldkey4difference < 1) heldkey4difference += 12;
            
            // Update LED indices for interval3 - optimized
            uint8_t note4_idx = trueheldkey4 - octave_number - transpose_number;
            get_all_note_positions(current_layer, note4_idx, positions);
            chordkey4_led_index = positions[0];
            chordkey4_led_index2 = positions[1];
            chordkey4_led_index3 = positions[2];
            chordkey4_led_index4 = positions[3];
            chordkey4_led_index5 = positions[4];
            chordkey4_led_index6 = positions[5];
        }

        if (!(play_simultaneous)) {
            struct {
                int trueheldkey;
                uint8_t note;
            } sequence[4] = {
                {trueheldkey1, base_note},
                {trueheldkey2, midi_compute_note(trueheldkey2 + 28931)},
                {trueheldkey3, midi_compute_note(trueheldkey3 + 28931)},
                {trueheldkey4, midi_compute_note(trueheldkey4 + 28931)}
            };
			for(int i = 0; i < 3; i++) {
			   for(int j = 0; j < 3-i; j++) {
				   if(sequence[j].trueheldkey > sequence[j+1].trueheldkey) {
					   int temp_key = sequence[j].trueheldkey;
					   uint8_t temp_note = sequence[j].note;
					   sequence[j].trueheldkey = sequence[j+1].trueheldkey;
					   sequence[j].note = sequence[j+1].note;
					   sequence[j+1].trueheldkey = temp_key;
					   sequence[j+1].note = temp_note;
				   }
			   }
			}

			bool notes_played = false;
			for(int i = 0; i < 4; i++) {
			   if(sequence[i].trueheldkey != 0) {
				   notes_played = true;
				   midi_send_noteon_trainer(channel, sequence[i].note, velocity);
				   wait_ms(500);
			   }
			}

			if(notes_played) {
			   wait_ms(1200);
			   for(int i = 0; i < 4; i++) {
				   if(sequence[i].trueheldkey != 0) {
					   midi_send_noteoff_trainer(channel, sequence[i].note, velocity);
				   }
			   }
			   
			   wait_ms(100);
			   for(int i = 0; i < 4; i++) {
				   if(sequence[i].trueheldkey != 0) {
					   midi_send_noteon_smartchord(channel, sequence[i].note, velocity);
				   }
			   }
			}
        } else if (play_simultaneous) {
            midi_send_noteon_smartchord(channel, base_note, velocity);
            if (interval1 != 0) midi_send_noteon_smartchord(channel, base_note + interval1 + octave_adjust1, velocity);
            if (interval2 != 0) midi_send_noteon_smartchord(channel, base_note + interval2 + octave_adjust2, velocity);
            if (interval3 != 0) midi_send_noteon_smartchord(channel, base_note + interval3 + octave_adjust3, velocity);
        }
        
        return false;
    } else {
        uint8_t base_note = midi_compute_note(trueheldkey1 + 28931);
        midi_send_noteoff_smartchord(channel, base_note, velocity);
        if (trueheldkey2 != 0) midi_send_noteoff_smartchord(channel, midi_compute_note(trueheldkey2 + 28931), velocity);
        if (trueheldkey3 != 0) midi_send_noteoff_smartchord(channel, midi_compute_note(trueheldkey3 + 28931), velocity);
        if (trueheldkey4 != 0) midi_send_noteoff_smartchord(channel, midi_compute_note(trueheldkey4 + 28931), velocity);
        
        smartchordstatus -= 1;

        chordkey1_led_index = 99; chordkey1_led_index2 = 99; chordkey1_led_index3 = 99;
        chordkey1_led_index4 = 99; chordkey1_led_index5 = 99; chordkey1_led_index6 = 99;
        chordkey2_led_index = 99; chordkey2_led_index2 = 99; chordkey2_led_index3 = 99;
        chordkey2_led_index4 = 99; chordkey2_led_index5 = 99; chordkey2_led_index6 = 99;
        chordkey3_led_index = 99; chordkey3_led_index2 = 99; chordkey3_led_index3 = 99;
        chordkey3_led_index4 = 99; chordkey3_led_index5 = 99; chordkey3_led_index6 = 99;
        chordkey4_led_index = 99; chordkey4_led_index2 = 99; chordkey4_led_index3 = 99;
        chordkey4_led_index4 = 99; chordkey4_led_index5 = 99; chordkey4_led_index6 = 99;
        
        trueheldkey1 = 0; heldkey1 = 0; heldkey1difference = 0;
        trueheldkey2 = 0; heldkey2 = 0; heldkey2difference = 0;
        trueheldkey3 = 0; heldkey3 = 0; heldkey3difference = 0;
        trueheldkey4 = 0; heldkey4 = 0; heldkey4difference = 0;
        
        return false;
    }
}
    


	  /* KEYBOARD PET STATUS START */
 //switch (keycode) {
  //      case KC_LCTL:
  //      case KC_RCTL:
  //          if (record->event.pressed) {
  //              isSneaking = true;
  //          } else {
  //              isSneaking = false;
  //          }
  //          break;
//        case KC_SPC:
//            if (record->event.pressed) {
//                isJumping  = true;
//                showedJump = false;
//            } else {
 //               isJumping = false;
 //           }
 //           break;
 //}
            /* KEYBOARD PET STATUS END */





if (keycode >= 0xC420 && keycode <= 0xC428) {
	 if (record->event.pressed) {
        //smartchordstatus = 1;   trying without it to see if it is obselete
		 switch (keycode) {
		case 0xC420: inversionposition = 0;
		break;
		case 0xC421: inversionposition = 1;
		break;
		case 0xC422: inversionposition = 2;
		break;
		case 0xC423: inversionposition = 3;
		break;
		case 0xC424: inversionposition = 4;
		break;
		case 0xC425: inversionposition = 5;
		break;
		case 0xC426: positiveinversion = 0;
		break;
		case 0xC427: positiveinversion = 1;
		break;
		 }
	 }
}

if (keycode == 0xC4A0) {
	if (record->event.pressed) {
		smartchordchanger-=1;
		if (smartchordlight != 3) {smartchordlight = 1;}
	}
		if (smartchordchanger < 0) {
            smartchordchanger = 0;
        } else if (smartchordchanger > 79) {
            smartchordchanger = 79;
		}
		keycode = 0xC396 + smartchordchanger;
		//snprintf(name, sizeof(name),"Previous QuickChord");
}		
		
if (keycode == 0xC4A1) {
	if (record->event.pressed) {
		smartchordchanger+=1;
		if (smartchordlight != 3) {smartchordlight = 1;}
	}
		if (smartchordchanger < 0) {
            smartchordchanger = 0;
        } else if (smartchordchanger > 79) {
            smartchordchanger = 79;
		}
		keycode = 0xC396 + smartchordchanger;
		//snprintf(name, sizeof(name),"Next QuickChord");
}
	/////////////////////////////////////////// SMART CHORD///////////////////////////////////////////////////////////
if (keycode >= 0xC38B && keycode <= 0xC416) {
	 if (keycode == 0xC3F9) {
    // Calculate the new keycode based on the provided formula
	 keycode = 0xC396 + smartchordchanger;}
	 
	 if (record->event.pressed) {
        smartchordstatus += 1;
		
		 switch (keycode) {
		case 0xC38B:    
            chordkey2 = 1; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC38C:    
            chordkey2 = 2; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC38D:    
            chordkey2 = 3; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC38E:    
            chordkey2 = 4; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC38F:    
            chordkey2 = 5; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC390:   
            chordkey2 = 6; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC391:    
            chordkey2 = 7; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC392:    
            chordkey2 = 8; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC393:   
            chordkey2 = 9; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC394:    
            chordkey2 = 10; 
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC395:    
            chordkey2 = 11;  
			chordkey3 = 0;   
			chordkey4 = 0;
			chordkey5 = 0;
break;
case 0xC396:    // Major
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC397:    // Minor
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC398:    // Diminished
    chordkey2 = 3;   // Minor Third
    chordkey3 = 6;   // Diminished Fifth
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC399:    // Augmented
    chordkey2 = 4;   // Major Third
    chordkey3 = 8;   // Augmented Fifth
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC39A:    // b5
    chordkey2 = 4;   // Major Third
    chordkey3 = 6;   // Diminished Fifth
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC39B:    // sus2
    chordkey2 = 2;   // Major Second
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC39C:    // sus4
    chordkey2 = 5;   // Perfect Fourth
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC39D:    // 7 no 3
    chordkey2 = 7;   // Perfect Fifth
    chordkey3 = 10;  // Minor Seventh
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC39E:    // maj7no3
    chordkey2 = 7;   // Perfect Fifth
    chordkey3 = 11;  // Major Seventh
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC39F:    // 7no5
    chordkey2 = 4;   // Major Third
    chordkey3 = 10;  // Minor Seventh
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC3A0:    // m7no5
    chordkey2 = 3;   // Minor Third
    chordkey3 = 10;  // Minor Seventh
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC3A1:    // maj7no5
    chordkey2 = 4;   // Major Third
    chordkey3 = 11;  // Major Seventh
    chordkey4 = 0;
    chordkey5 = 0;
break;

case 0xC3A2:    // Major 6
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 9;   // Major Sixth
    chordkey5 = 0;
break;

case 0xC3A3:    // Minor 6
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 9;   // Major Sixth
    chordkey5 = 0;
break;

case 0xC3A4:    // Add2
    chordkey2 = 2;   // Major Second
    chordkey3 = 4;   // Major Third
    chordkey4 = 7;   // Perfect Fifth
    chordkey5 = 0;
break;

case 0xC3A5:    // Minor Add2
    chordkey2 = 2;   // Major Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 7;   // Perfect Fifth
    chordkey5 = 0;
break;

case 0xC3A6:    // Add4
    chordkey2 = 4;   // Major Third
    chordkey3 = 5;   // Perfect Fourth
    chordkey4 = 7;   // Perfect Fifth
    chordkey5 = 0;
break;

case 0xC3A7:    // Minor Add4
    chordkey2 = 3;   // Minor Third
    chordkey3 = 5;   // Perfect Fourth
    chordkey4 = 7;   // Perfect Fifth
    chordkey5 = 0;
break;

case 0xC3A8:    // 7
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 0;
break;

case 0xC3A9:    // Maj7
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 11;  // Major Seventh
    chordkey5 = 0;
break;

case 0xC3AA:    // m7
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 0;
break;

case 0xC3AB:    // m7b5
    chordkey2 = 3;   // Minor Third
    chordkey3 = 6;   // Diminished Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 0;
break;

case 0xC3AC:    // dim7
    chordkey2 = 3;   // Minor Third
    chordkey3 = 6;   // Diminished Fifth
    chordkey4 = 9;   // Diminished Seventh
    chordkey5 = 0;
break;

case 0xC3AD:    // minMaj7
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 11;  // Major Seventh
    chordkey5 = 0;
break;

case 0xC3AE:    // 7sus4
    chordkey2 = 5;   // Perfect Fourth
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 0;
break;

case 0xC3AF:    // Add9
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 14;  // Major Ninth
    chordkey5 = 0;
break;

case 0xC3B0:    // Minor Add9
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 14;  // Major Ninth
    chordkey5 = 0;
break;

case 0xC3B1:    // Add11
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 17;  // Perfect Eleventh
    chordkey5 = 0;
break;

case 0xC3B2:    // Minor Add11
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 17;  // Perfect Eleventh
    chordkey5 = 0;
break;

case 0xC3B3:    // 9
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 14;  // Major Ninth
break;

case 0xC3B4:    // m9
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 14;  // Major Ninth
break;

case 0xC3B5:    // Maj9
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 11;  // Major Seventh
    chordkey5 = 14;  // Major Ninth
break;

case 0xC3B6:    // 6/9
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 9;   // Major Sixth
    chordkey5 = 14;  // Major Ninth
break;

case 0xC3B7:    // m6/9
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 9;   // Major Sixth
    chordkey5 = 14;  // Major Ninth
break;

case 0xC3B8:    // 7b9
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 13;  // Minor Ninth
break;

case 0xC3B9:    // 7(11)
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 17;  // Perfect Eleventh
break;

case 0xC3BA:    // 7(#11)
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 18;  // Sharp Eleventh
break;

case 0xC3BB:    // m7(11)
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 17;  // Perfect Eleventh
break;

case 0xC3BC:    // maj7(11)
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 11;  // Major Seventh
    chordkey5 = 17;  // Perfect Eleventh
break;

case 0xC3BD:    // Maj7(#11)
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 11;  // Major Seventh
    chordkey5 = 18;  // Sharp Eleventh
break;

case 0xC3BE:    // 7(13)
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 21;  // Major Thirteenth
break;

case 0xC3BF:    // m7(13)
    chordkey2 = 3;   // Minor Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 10;  // Minor Seventh
    chordkey5 = 21;  // Major Thirteenth
break;

case 0xC3C0:    // Maj7(13)
    chordkey2 = 4;   // Major Third
    chordkey3 = 7;   // Perfect Fifth
    chordkey4 = 11;  // Major Seventh
    chordkey5 = 21;  // Major Thirteenth
break;

case 0xC3C1:    // 11
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 17;  // Perfect Eleventh
break;

case 0xC3C2:    // m11
   chordkey2 = 3;   // Minor Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 17;  // Perfect Eleventh
break;

case 0xC3C3:    // Maj11
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 11;  // Major Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 17;  // Perfect Eleventh
break;

case 0xC3C4:    // 7(11)(13)
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 17;  // Perfect Eleventh
   chordkey6 = 21;  // Major Thirteenth
break;

case 0xC3C5:    // m7(11)(13)
   chordkey2 = 3;   // Minor Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 17;  // Perfect Eleventh
   chordkey6 = 21;  // Major Thirteenth
break;

case 0xC3C6:    // maj7(11)(13)
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 11;  // Major Seventh
   chordkey5 = 17;  // Perfect Eleventh
   chordkey6 = 21;  // Major Thirteenth
break;

case 0xC3C7:    // 9(13)
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 21;  // Major Thirteenth
break;

case 0xC3C8:    // m9(13)
   chordkey2 = 3;   // Minor Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 21;  // Major Thirteenth
break;

case 0xC3C9:    // maj9(13)
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 11;  // Major Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 21;  // Major Thirteenth
break;

case 0xC3CA:    // 13
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 17;  // Perfect Eleventh
   chordkey7 = 21;  // Major Thirteenth
break;

case 0xC3CB:    // m13
   chordkey2 = 3;   // Minor Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 17;  // Perfect Eleventh
   chordkey7 = 21;  // Major Thirteenth
break;

case 0xC3CC:    // Maj13
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 11;  // Major Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 17;  // Perfect Eleventh
   chordkey7 = 21;  // Major Thirteenth
break;

case 0xC3CD:    // 7b9(11)
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 13;  // Minor Ninth
   chordkey6 = 17;  // Perfect Eleventh
break;

case 0xC3CE:    // 7sus2
   chordkey2 = 2;   // Major Second
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 0;
break;

case 0xC3CF:    // 7#5
   chordkey2 = 4;   // Major Third
   chordkey3 = 8;   // Augmented Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 0;
break;

case 0xC3D0:    // 7b5
   chordkey2 = 4;   // Major Third
   chordkey3 = 6;   // Diminished Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 0;
break;

case 0xC3D1:    // 7#9
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 15;  // Sharp Ninth
break;

case 0xC3D2:    // 7b5b9
   chordkey2 = 4;   // Major Third
   chordkey3 = 6;   // Diminished Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 13;  // Minor Ninth
break;

case 0xC3D3:    // 7b5#9
   chordkey2 = 4;   // Major Third
   chordkey3 = 6;   // Diminished Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 15;  // Sharp Ninth
break;

case 0xC3D4:    // 7b9(13)
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 13;  // Minor Ninth
   chordkey6 = 21;  // Major Thirteenth
break;

case 0xC3D5:    // 7#9(13)
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 15;  // Sharp Ninth
   chordkey6 = 21;  // Major Thirteenth
break;

case 0xC3D6:    // 7#5b9
   chordkey2 = 4;   // Major Third
   chordkey3 = 8;   // Augmented Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 13;  // Minor Ninth
break;

case 0xC3D7:    // 7#5#9
   chordkey2 = 4;   // Major Third
   chordkey3 = 8;   // Augmented Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 15;  // Sharp Ninth
break;

case 0xC3D8:    // 7b5(11)
   chordkey2 = 4;   // Major Third
   chordkey3 = 6;   // Diminished Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 17;  // Perfect Eleventh
break;

case 0xC3D9:    // maj7sus4
   chordkey2 = 5;   // Perfect Fourth
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 11;  // Major Seventh
   chordkey5 = 0;
break;

case 0xC3DA:    // maj7#5
   chordkey2 = 4;   // Major Third
   chordkey3 = 8;   // Augmented Fifth
   chordkey4 = 11;  // Major Seventh
   chordkey5 = 0;
break;

case 0xC3DB:    // maj7b5
   chordkey2 = 4;   // Major Third
   chordkey3 = 6;   // Diminished Fifth
   chordkey4 = 11;  // Major Seventh
   chordkey5 = 0;
break;

case 0xC3DC:    // minMaj7(11)
   chordkey2 = 3;   // Minor Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 11;  // Major Seventh
   chordkey5 = 17;  // Perfect Eleventh
break;

case 0xC3DD:    // (addb5)
   chordkey2 = 4;   // Major Third
   chordkey3 = 6;   // Diminished Fifth
   chordkey4 = 7;   // Perfect Fifth
   chordkey5 = 0;
break;

case 0xC3DE:    // 9#11
   chordkey2 = 4;   // Major Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 18;  // Sharp Eleventh
break;

case 0xC3DF:    // 9b5
   chordkey2 = 4;   // Major Third
   chordkey3 = 6;   // Diminished Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
break;

case 0xC3E0:    // 9#5
   chordkey2 = 4;   // Major Third
   chordkey3 = 8;   // Augmented Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
break;

case 0xC3E1:    // m9b5
   chordkey2 = 3;   // Minor Third
   chordkey3 = 6;   // Diminished Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
break;

case 0xC3E2:    // m9#11
   chordkey2 = 3;   // Minor Third
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
   chordkey6 = 18;  // Sharp Eleventh
break;

case 0xC3E3:    // 9sus4
   chordkey2 = 5;   // Perfect Fourth
   chordkey3 = 7;   // Perfect Fifth
   chordkey4 = 10;  // Minor Seventh
   chordkey5 = 14;  // Major Ninth
break;

case 0xC3FB:    // Major (Ionian)
    chordkey2 = 2;   // Major Second
    chordkey3 = 4;   // Major Third
    chordkey4 = 5;   // Perfect Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 9;   // Major Sixth
    chordkey7 = 11;  // Major Seventh
break;

case 0xC3FC:    // Dorian
    chordkey2 = 2;   // Major Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 5;   // Perfect Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 9;   // Major Sixth
    chordkey7 = 10;  // Minor Seventh
break;

case 0xC3FD:    // Phrygian
    chordkey2 = 1;   // Minor Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 5;   // Perfect Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 8;   // Minor Sixth
    chordkey7 = 10;  // Minor Seventh
break;

case 0xC3FE:    // Lydian
    chordkey2 = 2;   // Major Second
    chordkey3 = 4;   // Major Third
    chordkey4 = 6;   // Augmented Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 9;   // Major Sixth
    chordkey7 = 11;  // Major Seventh
break;

case 0xC3FF:    // Mixolydian
    chordkey2 = 2;   // Major Second
    chordkey3 = 4;   // Major Third
    chordkey4 = 5;   // Perfect Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 9;   // Major Sixth
    chordkey7 = 10;  // Minor Seventh
break;

case 0xC400:    // Minor (Aeolian)
    chordkey2 = 2;   // Major Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 5;   // Perfect Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 8;   // Minor Sixth
    chordkey7 = 10;  // Minor Seventh
break;

case 0xC401:    // Locrian
    chordkey2 = 1;   // Minor Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 5;   // Perfect Fourth
    chordkey5 = 6;   // Diminished Fifth
    chordkey6 = 8;   // Minor Sixth
    chordkey7 = 10;  // Minor Seventh
break;

case 0xC402:    // Melodic Minor
    chordkey2 = 2;   // Major Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 5;   // Perfect Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 9;   // Major Sixth
    chordkey7 = 11;  // Major Seventh
break;

case 0xC403:    // Lydian Dominant
    chordkey2 = 2;   // Major Second
    chordkey3 = 4;   // Major Third
    chordkey4 = 6;   // Augmented Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 9;   // Major Sixth
    chordkey7 = 10;  // Minor Seventh
break;

case 0xC404:    // Altered Scale
    chordkey2 = 1;   // Minor Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 4;   // Major Third
    chordkey5 = 6;   // Augmented Fourth
    chordkey6 = 8;   // Minor Sixth
    chordkey7 = 10;  // Minor Seventh
break;

case 0xC405:    // Harmonic Minor
    chordkey2 = 2;   // Major Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 5;   // Perfect Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 8;   // Minor Sixth
    chordkey7 = 11;  // Major Seventh
break;

case 0xC406:    // Major Pentatonic
    chordkey2 = 2;   // Major Second
    chordkey3 = 4;   // Major Third
    chordkey4 = 7;   // Perfect Fifth
    chordkey5 = 9;   // Major Sixth
    chordkey6 = 0;
    chordkey7 = 0;
break;

case 0xC407:    // Minor Pentatonic
    chordkey2 = 3;   // Minor Third
    chordkey3 = 5;   // Perfect Fourth
    chordkey4 = 7;   // Perfect Fifth
    chordkey5 = 10;  // Minor Seventh
    chordkey6 = 0;
    chordkey7 = 0;
break;

case 0xC408:    // Whole Tone
    chordkey2 = 2;   // Major Second
    chordkey3 = 4;   // Major Third
    chordkey4 = 6;   // Augmented Fourth
    chordkey5 = 8;   // Minor Sixth
    chordkey6 = 10;  // Minor Seventh
    chordkey7 = 0;
break;

case 0xC409:    // Diminished
    chordkey2 = 1;   // Minor Second
    chordkey3 = 3;   // Minor Third
    chordkey4 = 4;   // Major Third
    chordkey5 = 6;   // Augmented Fourth
    chordkey6 = 7;   // Perfect Fifth
    chordkey7 = 9;   // Major Sixth
break;

case 0xC40A:    // Blues
    chordkey2 = 3;   // Minor Third
    chordkey3 = 5;   // Perfect Fourth
    chordkey4 = 6;   // Augmented Fourth
    chordkey5 = 7;   // Perfect Fifth
    chordkey6 = 10;  // Minor Seventh
    chordkey7 = 0;
break;
		 }
		if (inversionposition == 1) {
			if (chordkey2 != 0) {
				chordkey2 -= 12;
				}
			if (chordkey3 != 0) {
				chordkey3 -= 12;
				}
			if (chordkey4 != 0) {
				chordkey4 -= 12;
				}
			if (chordkey5 != 0) {
				chordkey5 -= 12;
				}
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
			}
			
		else if (inversionposition == 2) {
			if (chordkey3 != 0) {
				chordkey3 -= 12;
				}
			if (chordkey4 != 0) {
				chordkey4 -= 12;
				}
			if (chordkey5 != 0) {
				chordkey5 -= 12;
				}
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
			}
			
		else if (inversionposition == 3) {
			if (chordkey4 != 0) {
				chordkey4 -= 12;
			}
			if (chordkey5 != 0) {
				chordkey5 -= 12;
				}
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
		}
				
		else if (inversionposition == 4) {
			if (chordkey5 != 0) {
				chordkey5 -= 12;
				}
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
		}		
		else if (inversionposition == 5) {
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
		}
		
		if (positiveinversion == 1) {
			if (chordkey2 != 0) {
				chordkey2 += 12;
				}
			if (chordkey3 != 0) {
				chordkey3 += 12;
				}
			if (chordkey4 != 0) {
				chordkey4 += 12;
				}
			if (chordkey5 != 0) {
				chordkey5 += 12;
				}
			if (chordkey6 != 0) {
				chordkey6 += 12;
				}
			}
		
    } else {
        smartchordstatus -= 1;
		if (smartchordlight != 3) {smartchordlight = 0;}
		if (smartchordstatus == 0) {
        chordkey2 = 0;
        chordkey3 = 0;
        chordkey4 = 0;
        chordkey5 = 0;
		chordkey6 = 0;
		chordkey7 = 0;
		trueheldkey2 = 0;
		heldkey2 = 0;
		heldkey2difference = 0;
		trueheldkey3 = 0;
		heldkey3 = 0;
		heldkey3difference = 0;
		trueheldkey4 = 0;
		heldkey4 = 0;
		heldkey4difference = 0;
		trueheldkey5 = 0;
		heldkey5 = 0;
		heldkey5difference = 0;
		trueheldkey6 = 0;
		heldkey6 = 0;
		heldkey6difference = 0;
		trueheldkey7 = 0;
		heldkey7 = 0;
		heldkey7difference = 0;
		rootnote = 13;
		bassnote = 13;
		}
    }
}

if (record->event.pressed) {
	 	if (keycode != 0x7186) {
		set_keylog(keycode, record);}
      } else if (!record->event.pressed && keycode >= 0xCC18 && keycode <= 0xCC1B) { 
		set_keylog(keycode, record);}
  
  if (!record->event.pressed) {
	 		if (oneshotchannel != 0 && !(keycode >= 0xC438 && keycode <= 0xC447)) {
			channel_number = channelplaceholder;  // Restore the previous channel
			channelplaceholder = 0;  // Reset the placeholder
			oneshotchannel = 0;
			} if ((keycode >= 28931 && keycode <= 29002) || (keycode >= 50688 && keycode <= 50759) || (keycode >= 50800 && keycode <= 50871) || (keycode == 0x7186)) {
			update_keylog_display();
		} else {
            return true;  // Exit early for key release events to prevent double triggering
        }

	}

if (keycode >= MI_CC_TOG_0 && keycode < (MI_CC_TOG_0 + 128)) { // CC TOGGLE
        uint8_t cc = keycode - MI_CC_TOG_0;

        if (CCValue[cc]) {
            CCValue[cc] = 0;
        } else {
            CCValue[cc] = 127;
        }
        midi_send_cc_with_recording(channel_number, cc, CCValue[cc]);

        //sprintf(status_str, "CC\nTog\n%d", cc);

    } else if (keycode >= MI_CC_UP_0 && keycode < (MI_CC_UP_0 + 128)) { // CC ++
    uint8_t cc = keycode - MI_CC_UP_0;

    if (CCValue[cc] < 127) {
        CCValue[cc] += cc_sensitivity; // Apply the encoder step directly
        if (CCValue[cc] > 127) {
            CCValue[cc] = 127;
        }
    }

    midi_send_cc_with_recording(channel_number, cc, CCValue[cc]);


        // sprintf(status_str, "CC\nUp\n%d", cc);
		


    } else if (keycode >= MI_CC_DWN_0 && keycode < (MI_CC_DWN_0 + 128)) { // CC --
    uint8_t cc = keycode - MI_CC_DWN_0;

    if (CCValue[cc] > 0) {
        if (CCValue[cc] >= cc_sensitivity) {
            CCValue[cc] -= cc_sensitivity; // Apply encoder step directly
        } else {
            CCValue[cc] = 0;
        }
    }

    midi_send_cc_with_recording(channel_number, cc, CCValue[cc]);




        //sprintf(status_str, "CC\nDown\n%d", cc);
    } else if (keycode == 0xC437){
			if (record->event.key.row == KEYLOC_ENCODER_CW && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) > 0) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (velocity_sensitivity)) < 0){
					midi_config.velocity = 0;
                }
			}else if (record->event.key.row == KEYLOC_ENCODER_CCW && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) > 0) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (velocity_sensitivity)) < 0){
					midi_config.velocity = 0;
                }
            }else if (record->event.pressed && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) > 0) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (velocity_sensitivity)) < 0){
					midi_config.velocity = 0;
                }

                dprintf("midi velocity %d\n", midi_config.velocity);
            }
    } else if (keycode == 0xC436){
			if (record->event.key.row == KEYLOC_ENCODER_CW && midi_config.velocity < 127) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) <127) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (velocity_sensitivity)) >127){
					midi_config.velocity = 127;
                }
			}else if (record->event.key.row == KEYLOC_ENCODER_CCW && midi_config.velocity < 127) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) <127) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (velocity_sensitivity)) >127){
					midi_config.velocity = 127;
                }
            }else if (record->event.pressed && midi_config.velocity < 127) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) <127) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (velocity_sensitivity)) >127){
					midi_config.velocity = 127;
                }

                dprintf("midi velocity %d\n", midi_config.velocity);
            }

    } else if (keycode >= MI_CC_0_0 && keycode < (MI_CC_0_0 + 128 * 128)) { // CC FIXED
        uint8_t cc  = (keycode - MI_CC_0_0) / 128;
        uint8_t val = (keycode - MI_CC_0_0) % 128;

        CCValue[cc] = val;
        midi_send_cc_with_recording(channel_number, cc, CCValue[cc]);

        //sprintf(status_str, "CC\n%d\n%d", cc, val);

    } else if (keycode >= MI_BANK_MSB_0 && keycode < (MI_BANK_MSB_0 + 128)) { // BANK MSB
        uint8_t val = keycode - MI_BANK_MSB_0;
        uint8_t cc  = BANK_SEL_MSB_CC;

        CCValue[cc] = val;
        midi_send_cc_with_recording(channel_number, cc, CCValue[cc]);

        MidiCurrentBank &= 0x00FF;
        MidiCurrentBank |= val << 8;

        //sprintf(status_str, "MSB\nbank\n%d", val);

    } else if (keycode >= MI_BANK_LSB_0 && keycode < (MI_BANK_LSB_0 + 128)) { // BANK LSB
        uint8_t val = keycode - MI_BANK_LSB_0;
        uint8_t cc  = BANK_SEL_LSB_CC;

        CCValue[cc] = val;
        midi_send_cc_with_recording(channel_number, cc, CCValue[cc]);

        MidiCurrentBank &= 0xFF00;
        MidiCurrentBank |= val;

        //sprintf(status_str, "LSB\nbank\n%d", val);

    } else if (keycode >= MI_PROG_0 && keycode < (MI_PROG_0 + 128)) { // PROG CHANGE
        uint8_t val = keycode - MI_PROG_0;

        midi_send_programchange(&midi_device, channel_number, val);
        MidiCurrentProg = val;

        //sprintf(status_str, "PC\n%d", val);

    } else if (keycode >= MI_VELOCITY_0 && keycode < (MI_VELOCITY_0 + 128)) {
        uint8_t val = keycode - MI_VELOCITY_0;
        if (val >= 0 && val < 128) midi_config.velocity = val;

    } else if (keycode >= ENCODER_STEP_1 && keycode < (ENCODER_STEP_1 + 16)) {
        uint8_t val = keycode - ENCODER_STEP_1 + 1;
        if (val >= 1 && val < 17) cc_sensitivity = val;
    
    } else {
        uint8_t lsb = 0;
        uint8_t msb = 0;

        switch (keycode) {
            case MI_BANK_UP:
                if (MidiCurrentBank < 0xFFFF) {
                    ++MidiCurrentBank;
                }
                //sprintf(status_str, "bank\n%d", MidiCurrentBank);
                lsb = MidiCurrentBank & 0xFF;
                msb = (MidiCurrentBank & 0xFF00) >> 8;
                midi_send_cc_with_recording(channel_number, BANK_SEL_LSB_CC, lsb);
                midi_send_cc_with_recording(channel_number, BANK_SEL_MSB_CC, msb);

                break;
            case MI_BANK_DWN:
                if (MidiCurrentBank > 0) {
                    --MidiCurrentBank;
                }
                //sprintf(status_str, "bank\n%d", MidiCurrentBank);
                uint8_t lsb = MidiCurrentBank & 0xFF;
                uint8_t msb = (MidiCurrentBank & 0xFF00) >> 8;
                midi_send_cc_with_recording(channel_number, BANK_SEL_LSB_CC, lsb);
                midi_send_cc_with_recording(channel_number, BANK_SEL_MSB_CC, msb);
                break;
            case MI_PROG_UP:
                if (MidiCurrentProg < 127) {
                    ++MidiCurrentProg;
                }
                //sprintf(status_str, "PC\n%d", MidiCurrentProg);
                midi_send_programchange(&midi_device, channel_number, MidiCurrentProg);
                break;
            case MI_PROG_DWN:
                if (MidiCurrentProg > 0) {
                    --MidiCurrentProg;
                }
                //sprintf(status_str, "PC\n%d", MidiCurrentProg);
                midi_send_programchange(&midi_device, channel_number, MidiCurrentProg);
                break;
            default:
                //sprintf(status_str, "%d", keycode);
                break; 

        }             
    }

    return true;
}

oled_rotation_t oled_init_kb(oled_rotation_t rotation) { return OLED_ROTATION_0; }

#include "usb_main.h"  // For USB_DRIVER access

// Render a big number on the OLED display for quick build step indication
void render_big_number(uint8_t number) {
    char buf[64];

    // Clear the display area
    oled_clear();

    // Line 1: Title
    oled_set_cursor(0, 0);
    if (quick_build_state.mode == QUICK_BUILD_ARP) {
        oled_write_P(PSTR("  ARP QUICK BUILD  "), false);
    } else if (quick_build_state.mode == QUICK_BUILD_SEQ) {
        snprintf(buf, sizeof(buf), " SEQ SLOT %d BUILD ", quick_build_state.seq_slot + 1);
        oled_write(buf, false);
    }

    // Line 2: Separator
    oled_set_cursor(0, 1);
    oled_write_P(PSTR("---------------------"), false);

    // Lines 3-5: Big number (centered)
    oled_set_cursor(0, 3);

    if (number < 10) {
        snprintf(buf, sizeof(buf), "      STEP %d      ", number);
    } else if (number < 100) {
        snprintf(buf, sizeof(buf), "     STEP %d      ", number);
    } else {
        snprintf(buf, sizeof(buf), "     STEP %d     ", number);
    }
    oled_write(buf, false);

    // Line 6: Note count
    oled_set_cursor(0, 5);
    snprintf(buf, sizeof(buf), "    %d NOTES TOTAL   ", quick_build_state.note_count);
    oled_write(buf, false);

    // Line 7: Instruction
    oled_set_cursor(0, 7);
    if (quick_build_state.mode == QUICK_BUILD_ARP) {
        oled_write_P(PSTR(" Press to finish     "), false);
    } else {
        oled_write_P(PSTR(" Press to finish     "), false);
    }
}

bool oled_task_user(void) {
    // Check if quick build is active - if so, show big number display
    if (quick_build_is_active()) {
        render_big_number(quick_build_get_current_step());
        return false;
    }

    // Normal display mode
    // Buffer to store the formatted string
    char str[22] = "";
    char name[124] = "";  // Define `name` buffer to be used later
    // Get the current layer and format it into `str`
    uint8_t layer = get_highest_layer(layer_state | default_layer_state);
    uint16_t display_bpm = current_bpm / 100000;  // Convert back to normal BPM

    if (current_bpm == 0) { snprintf(str, sizeof(str), "       LAYER %-3d", layer);}
	 else {snprintf(str, sizeof(str), "  LYR %-3d   BPM %3d", layer, (int)display_bpm);}
    // Write the layer information to the OLED
    oled_write(str, false);

    // Display temporary mode message if active
    if (mode_display_active) {
        if (timer_elapsed32(mode_display_timer) < MODE_DISPLAY_DURATION) {
            oled_write(mode_display_msg, false);
        } else {
            mode_display_active = false;
        }
    }

    // Render keylog information
    oled_render_keylog();
    // Add separator line to `name` and write to OLED
    //snprintf(name + strlen(name), sizeof(name) - strlen(name), "---------------------");
    // You only need to add the separator once, not three times.
    oled_write(name, false);

if (!dynamic_macro_has_activity()) {
    led_usb_state = host_keyboard_led_state();
        render_luna(0, 1);
} else {
    // Show Luna keyboard when no macros have data
    led_usb_state = host_keyboard_led_state();
	render_interface(0, 8);
};
return false;
}

void matrix_scan_user(void) {
    // Update chord progression timing
    update_chord_progression();
    matrix_scan_user_macro();

    // Update arpeggiator and sequencer timing and gate-offs
    arp_update();
    seq_update();

    // Update quick build sustain monitoring
    quick_build_update();

#ifdef JOYSTICK_ENABLE
    // Update joystick/gaming controller state
    gaming_update_joystick();
#endif

#ifdef MIDI_SERIAL_ENABLE
    // Process serial MIDI (hardware MIDI IN/OUT)
    midi_device_process(&midi_serial_device);
#endif

    // Check for tap tempo key hold (1.5 seconds = 1500ms)
    if (tap_key_held && (timer_read32() - tap_key_press_time >= 1500)) {
        current_bpm = 0;
        tap_key_held = false;  // Reset to prevent multiple triggers
		internal_clock_stop();
        tap_key_press_time = 0;
    }
	if (current_bpm > 0) {
	midi_clock_task();}

	// Virtual keys (encoder clicks + sustain pedal) use full QMK action processing
	// via action_exec() with MAKE_KEYEVENT to set the event type correctly.
	// The .type = KEY_EVENT field is REQUIRED - without it, the event defaults to
	// TICK_EVENT (value 0) and IS_EVENT() returns false, causing it to be ignored.

	// Handle footswitch / momentary switch (PA9) - active low
	static bool footswitch_prev_state = true;
	bool footswitch_state = readPin(A9);
	if (footswitch_state != footswitch_prev_state) {
		action_exec(MAKE_KEYEVENT(5, 2, !footswitch_state));
		footswitch_prev_state = footswitch_state;
	}

	// Handle encoder 0 click button (PB14) - matrix position (5, 0)
	static bool encoder0_click_prev_state = true;
	bool encoder0_click_state = readPin(B14);
	if (encoder0_click_state != encoder0_click_prev_state) {
		action_exec(MAKE_KEYEVENT(5, 0, !encoder0_click_state));
		encoder0_click_prev_state = encoder0_click_state;
	}

	// Handle encoder 1 click button (PB15) - matrix position (5, 1)
	static bool encoder1_click_prev_state = true;
	bool encoder1_click_state = readPin(B15);
	if (encoder1_click_state != encoder1_click_prev_state) {
		action_exec(MAKE_KEYEVENT(5, 1, !encoder1_click_state));
		encoder1_click_prev_state = encoder1_click_state;
	}
}
