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
#include "process_keycode/process_dynamic_macro.h"  // For PER_KEY_ACTUATION_EEPROM_ADDR
#include "dynamic_keymap.h"
#include "distance_lut.h"
#include "eeprom.h"

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

// Velocity preset actuation override - BASE zone
extern bool preset_actuation_override;
extern uint8_t preset_actuation_point;  // 0-40 = 0.0-4.0mm
extern uint8_t preset_retrigger_distance;  // 0=off, 5-20 = 0.5-2.0mm

// Velocity preset actuation override - KEYSPLIT zone
extern bool keysplit_preset_actuation_override;
extern uint8_t keysplit_preset_actuation_point;
extern uint8_t keysplit_preset_retrigger_distance;

// Velocity preset actuation override - TRIPLESPLIT zone
extern bool triplesplit_preset_actuation_override;
extern uint8_t triplesplit_preset_actuation_point;
extern uint8_t triplesplit_preset_retrigger_distance;

// Keysplit velocity status (controls which zones have separate velocity)
// 0=disabled (all zones same), 1=keysplit only, 2=triplesplit only, 3=both
extern uint8_t keysplitvelocitystatus;

// EEPROM functions from orthomidi5x14.c
extern void load_per_key_actuations(void);
extern void initialize_per_key_actuations(void);

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
    uint16_t adc_raw;               // Raw ADC value (no filtering)
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
    uint16_t stable_start_adc;      // ADC value when stability was first detected (drift guard)
    uint32_t stable_time;           // When key became stable
    bool is_stable;                 // Key is at stable position
} key_state_t;

// ============================================================================
// MIDI KEY STATE (kept from orthomidi5x14)
// ============================================================================

// Zone type for keysplit/triplesplit velocity settings
#define ZONE_TYPE_BASE        0  // Base zone (MI_* keycodes)
#define ZONE_TYPE_KEYSPLIT    1  // Keysplit zone (MI_SPLIT_* keycodes, 0xC600-0xC647)
#define ZONE_TYPE_TRIPLESPLIT 2  // Triplesplit zone (MI_SPLIT2_* keycodes, 0xC670-0xC6B7)

typedef struct {
    bool is_midi_key;
    uint8_t note_index;
    uint8_t zone_type;           // Zone type: ZONE_TYPE_BASE, ZONE_TYPE_KEYSPLIT, or ZONE_TYPE_TRIPLESPLIT
    bool pressed;
    bool was_pressed;

    // Mode 1: Peak travel at apex
    uint8_t peak_travel;
    bool send_on_release;
    bool velocity_captured;      // True when velocity has been captured for this press

    // MIDI Retrigger state (velocity preset feature, separate from per-key rapidfire)
    // Retrigger allows new note-on after releasing by retrigger_distance from peak
    bool retrigger_eligible;     // True when key has risen by retrigger_distance from peak
    uint8_t retrigger_peak;      // Peak travel during current retrigger cycle
    uint8_t retrigger_eligible_point; // Travel value where key became eligible (for speed measurement)
    uint32_t retrigger_move_start;    // ChibiOS ticks when key started moving down from eligible point

    // Mode 2 & 3: Speed-based
    uint8_t last_travel;
    uint16_t last_time;
    uint8_t peak_velocity;
    uint16_t peak_speed;         // Peak speed (uint16_t to avoid overflow)
    uint8_t travel_at_actuation; // Travel when actuation point was crossed (for Mode 2)
    uint8_t release_travel;      // Travel position when key was released (for partial re-press scaling)

    // Mode 1 & 3: Apex detection + timing
    uint32_t move_start_time;    // ChibiOS system ticks when key started moving (10µs resolution)
    uint32_t stall_start_time;   // ChibiOS ticks when key stopped increasing (for stall detection)

    // Raw velocity for curve application (0-255)
    uint8_t raw_velocity;        // Raw velocity value before curve/scaling

    // Travel time and final velocity for GUI display
    uint16_t travel_time_ms;     // Last measured travel time in milliseconds
    uint8_t final_velocity;      // Final velocity (0-127) after curve application

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

// EQ-style sensitivity curve tuning (adjustable via HID for real-time tuning)
// Range boundaries: determines which curve set to use based on rest ADC
uint16_t eq_range_low = 1745;   // Below this = low rest range
uint16_t eq_range_high = 2082;  // At or above this = high rest range

// EQ bands: 3 ranges × 5 bands
// Value stored as half-percentage: actual_percent = value * 2
// Default = 50 (100% = no change)
// Range: 12 (25%) to 200 (400%)
uint8_t eq_bands[3][5] = {
    // Range 0 (Low rest < 1745): [low, low-mid, mid, high-mid, high]
    // 98%, 98%, 100%, 100%, 100%
    {49, 49, 50, 50, 50},
    // Range 1 (Mid rest 1745-2082): [low, low-mid, mid, high-mid, high]
    // 100%, 100%, 100%, 100%, 100% (neutral baseline)
    {50, 50, 50, 50, 50},
    // Range 2 (High rest >= 2082): [low, low-mid, mid, high-mid, high]
    // 130%, 118%, 100%, 100%, 100%
    {65, 59, 50, 50, 50},
};

// Range scale: overall distance multiplier for each rest range
// Value stored as half-percentage: actual_percent = value * 2
// 110%, 100%, 106%
uint8_t eq_range_scale[3] = {55, 50, 53};

// ============================================================================
// GLOBAL VELOCITY TIME SETTINGS
// ============================================================================
// Min/max travel time for velocity scaling - now uses global min_press_time/max_press_time
// from keyboard_settings_t (set via HID commands)
// min_press_time: Time in ms for slowest press = minimum velocity (default 200ms)
// max_press_time: Time in ms for fastest press = maximum velocity (default 20ms)
// Linear interpolation between these two points:
//   elapsed_ms <= max_press_time → velocity = 127 (max)
//   elapsed_ms >= min_press_time → velocity = 1 (min)
//   otherwise → linear interpolation
// NOTE: Local variables removed - using global min_press_time/max_press_time from process_dynamic_macro.h

// ============================================================================
// EQ CURVE EEPROM PERSISTENCE
// ============================================================================

// EEPROM address for EQ curve settings (must match keyboard header)
#ifndef EQ_CURVE_EEPROM_ADDR
#define EQ_CURVE_EEPROM_ADDR 41300
#endif
#ifndef EQ_CURVE_MAGIC
#define EQ_CURVE_MAGIC 0xEA01
#endif

void eq_curve_save_to_eeprom(void) {
    // Write magic number first
    eeprom_update_word((uint16_t*)EQ_CURVE_EEPROM_ADDR, EQ_CURVE_MAGIC);

    // Write range boundaries (4 bytes)
    eeprom_update_word((uint16_t*)(EQ_CURVE_EEPROM_ADDR + 2), eq_range_low);
    eeprom_update_word((uint16_t*)(EQ_CURVE_EEPROM_ADDR + 4), eq_range_high);

    // Write all 15 band values (15 bytes)
    for (uint8_t range = 0; range < 3; range++) {
        for (uint8_t band = 0; band < 5; band++) {
            eeprom_update_byte((uint8_t*)(EQ_CURVE_EEPROM_ADDR + 6 + range * 5 + band),
                              eq_bands[range][band]);
        }
    }

    // Write 3 range scale values (3 bytes)
    for (uint8_t range = 0; range < 3; range++) {
        eeprom_update_byte((uint8_t*)(EQ_CURVE_EEPROM_ADDR + 21 + range),
                          eq_range_scale[range]);
    }

    dprintf("EQ Curve saved to EEPROM\n");
}

void eq_curve_load_from_eeprom(void) {
    // Check magic number
    uint16_t magic = eeprom_read_word((uint16_t*)EQ_CURVE_EEPROM_ADDR);
    if (magic != EQ_CURVE_MAGIC) {
        dprintf("EQ Curve EEPROM not initialized, using defaults\n");
        return;
    }

    // Read range boundaries
    eq_range_low = eeprom_read_word((uint16_t*)(EQ_CURVE_EEPROM_ADDR + 2));
    eq_range_high = eeprom_read_word((uint16_t*)(EQ_CURVE_EEPROM_ADDR + 4));

    // Read all 15 band values
    for (uint8_t range = 0; range < 3; range++) {
        for (uint8_t band = 0; band < 5; band++) {
            eq_bands[range][band] = eeprom_read_byte((uint8_t*)(EQ_CURVE_EEPROM_ADDR + 6 + range * 5 + band));
        }
    }

    // Read 3 range scale values
    for (uint8_t range = 0; range < 3; range++) {
        eq_range_scale[range] = eeprom_read_byte((uint8_t*)(EQ_CURVE_EEPROM_ADDR + 21 + range));
    }

    dprintf("EQ Curve loaded from EEPROM: low=%d, high=%d\n", eq_range_low, eq_range_high);
}

// ============================================================================
// VELOCITY TIME SETTINGS EEPROM PERSISTENCE
// ============================================================================

// EEPROM functions for velocity time settings - DEPRECATED
// Velocity time (min_press_time/max_press_time) is now saved via keyboard_settings_t
// These stub functions are kept for compatibility but do nothing
void velocity_time_save_to_eeprom(void) {
    // Velocity time is now saved with keyboard_settings - this function is deprecated
    dprintf("velocity_time_save_to_eeprom() deprecated - use keyboard settings\n");
}

void velocity_time_load_from_eeprom(void) {
    // Velocity time is now loaded with keyboard_settings - this function is deprecated
    dprintf("velocity_time_load_from_eeprom() deprecated - use keyboard settings\n");
}

// Layer caching (libhmk style optimization)
static uint8_t cached_layer = 0xFF;
static uint8_t cached_layer_settings_layer = 0xFF;

// Cached layer settings for hot path
// NOTE: normal_actuation and midi_actuation removed - per-key only now
static struct {
    uint8_t velocity_mode;
    uint8_t velocity_speed_scale;
    // Per-layer aftertouch settings
    uint8_t aftertouch_mode;
    uint8_t aftertouch_cc;
    uint8_t vibrato_sensitivity;
    uint16_t vibrato_decay_time;
} active_settings;

// ============================================================================
// KEY TYPE CACHE (eliminates EEPROM reads in scan loop)
// ============================================================================

// Key types for the cache
typedef enum {
    KEY_TYPE_NORMAL = 0,
    KEY_TYPE_DKS = 1,
    KEY_TYPE_MIDI = 2
} key_type_t;

// Cache: stores key type for each key (refreshed on layer change)
static uint8_t key_type_cache[NUM_KEYS];
static uint16_t dks_keycode_cache[NUM_KEYS];  // Cache DKS keycodes for processing
static uint8_t key_type_cache_layer = 0xFF;   // Layer the cache was built for

// Forward declaration
static void refresh_key_type_cache(uint8_t layer);

// ============================================================================
// PER-KEY ACTUATION CACHE (280 bytes - fits in L1 cache)
// ============================================================================
// This cache holds the essential per-key settings for the active layer only.
// It's refreshed on layer change and used during the matrix scan hot path.
// The full per_key_actuations[12][70] array is still used for EEPROM/HID.

per_key_config_lite_t active_per_key_cache[70];
uint8_t active_per_key_cache_layer = 0xFF;  // Layer the cache was built for

// Deferred EEPROM loading - load on first keypress instead of at init
static bool per_key_eeprom_loaded = false;

// Chunked EEPROM loading state
// Reads 1 row (14 keys = 112 bytes) per scan cycle to avoid blocking
static bool chunked_load_active = false;
static uint8_t chunked_load_row = 0;
static uint8_t chunked_load_layer = 0;  // Which layer we're currently loading
static uint16_t layers_eeprom_loaded = 0;  // Bitmask: bit N = layer N loaded from EEPROM
#define KEYS_PER_ROW 14
#define BYTES_PER_ROW (KEYS_PER_ROW * sizeof(per_key_actuation_t))  // 112 bytes

// NOTE: Diagnostic test modes (0-25) have been removed after root cause was found.
// See PER_KEY_ACTUATION_USB_DISCONNECT_DIAGNOSIS.md for full analysis.
// Root cause: refresh_per_key_cache called 71x per scan cycle, must return early.

// ============================================================================
// PER-KEY CACHE LOADING
// ============================================================================
// Strategy:
//   1. At startup (keyboard_post_init), load layer 0 fully - USB not active yet
//   2. On layer change during operation, only fill defaults (no array reads)
//
// NOTE: Reading from per_key_actuations during scan causes USB disconnect.
// Even 1 struct read per scan accumulates to USB starvation.
// See PER_KEY_ACTUATION_USB_DISCONNECT_DIAGNOSIS.md for full analysis.

static uint8_t incremental_load_index = 70;  // 70 = done loading
static uint8_t incremental_load_layer = 0xFF;

// Force load all 70 keys for a layer - ONLY SAFE DURING INIT (before USB active)
// This function reads from per_key_actuations which causes USB disconnect if
// called during normal operation. Only call from keyboard_post_init_user.
void force_load_per_key_cache_at_init(uint8_t layer) {
    if (layer >= 12) layer = 0;

    // Load all 70 keys from the array
    for (uint8_t i = 0; i < 70; i++) {
        per_key_actuation_t *full = &per_key_actuations[layer].keys[i];
        active_per_key_cache[i].actuation = full->actuation;
        active_per_key_cache[i].rt_down = full->rapidfire_press_sens;
        active_per_key_cache[i].rt_up = full->rapidfire_release_sens;
        active_per_key_cache[i].flags = full->flags;
    }

    // Mark cache as valid for this layer
    active_per_key_cache_layer = layer;
}

// Start chunked EEPROM loading for all layers
// This initiates loading 1 row (112 bytes) per scan cycle, starting from layer 0
void start_chunked_eeprom_load_all(void) {
    if (chunked_load_active) return;  // Already loading something
    if (layers_eeprom_loaded == 0x0FFF) return;  // All layers already loaded

    chunked_load_active = true;
    chunked_load_row = 0;
    chunked_load_layer = 0;  // Start with layer 0
}

// Process one chunk of EEPROM loading (called once per scan cycle)
// Reads 1 row (14 keys = 112 bytes) from EEPROM into per_key_actuations
// then updates the active cache for those keys
// Automatically continues to next layer until all are loaded
void process_chunked_eeprom_load(void) {
    if (!chunked_load_active) return;

    uint8_t layer = chunked_load_layer;

    if (chunked_load_row >= 5) {
        // Done loading all 5 rows for this layer
        layers_eeprom_loaded |= (1 << layer);  // Mark this layer as loaded

        // Check if EEPROM was uninitialized (0xFF = never saved) - only check on layer 0
        if (layer == 0 && per_key_actuations[0].keys[0].actuation == 0xFF) {
            initialize_per_key_actuations();
            // Mark all layers as "loaded" (they now have defaults)
            layers_eeprom_loaded = 0x0FFF;  // All 12 layers
            chunked_load_active = false;
            per_key_eeprom_loaded = true;

            // Refresh cache with defaults
            for (uint8_t i = 0; i < 70; i++) {
                active_per_key_cache[i].actuation = DEFAULT_ACTUATION_VALUE;
                active_per_key_cache[i].rt_down = 0;
                active_per_key_cache[i].rt_up = 0;
                active_per_key_cache[i].flags = 0;
            }
            return;
        }

        // Refresh cache if we just loaded the currently active layer
        if (active_per_key_cache_layer == layer) {
            for (uint8_t i = 0; i < 70; i++) {
                per_key_actuation_t *full = &per_key_actuations[layer].keys[i];
                active_per_key_cache[i].actuation = full->actuation;
                active_per_key_cache[i].rt_down = full->rapidfire_press_sens;
                active_per_key_cache[i].rt_up = full->rapidfire_release_sens;
                active_per_key_cache[i].flags = full->flags;
            }
        }

        // Move to next layer
        chunked_load_layer++;
        chunked_load_row = 0;

        // Check if all layers are loaded
        if (chunked_load_layer >= 12) {
            chunked_load_active = false;
            per_key_eeprom_loaded = true;
        }
        return;
    }

    // Calculate EEPROM offset for this row and layer
    // Layout: per_key_actuations[layer][key] = base + (layer * 70 * 8) + (key * 8)
    uint8_t start_key = chunked_load_row * KEYS_PER_ROW;
    uint32_t eeprom_offset = PER_KEY_ACTUATION_EEPROM_ADDR +
                             (layer * 70 * sizeof(per_key_actuation_t)) +
                             (start_key * sizeof(per_key_actuation_t));

    // Read 14 keys (112 bytes) from EEPROM directly into per_key_actuations array
    eeprom_read_block(&per_key_actuations[layer].keys[start_key],
                      (void*)eeprom_offset,
                      BYTES_PER_ROW);

    // Update active cache for these 14 keys (if we're loading the active layer)
    if (active_per_key_cache_layer == layer) {
        for (uint8_t i = 0; i < KEYS_PER_ROW; i++) {
            uint8_t key_idx = start_key + i;
            if (key_idx < 70) {
                per_key_actuation_t *full = &per_key_actuations[layer].keys[key_idx];
                active_per_key_cache[key_idx].actuation = full->actuation;
                active_per_key_cache[key_idx].rt_down = full->rapidfire_press_sens;
                active_per_key_cache[key_idx].rt_up = full->rapidfire_release_sens;
                active_per_key_cache[key_idx].flags = full->flags;
            }
        }
    }

    chunked_load_row++;
}

// Check if EEPROM has been loaded (for external use)
bool is_per_key_eeprom_loaded(void) {
    return per_key_eeprom_loaded;
}

// DISABLED: This function causes USB disconnect even at 1 key per scan.
// The struct field access pattern from per_key_actuations array is problematic.
// Keeping the code for future reference - need alternative loading approach.
void incremental_load_per_key_cache(void) {
    if (incremental_load_index >= 70) return;  // Done loading

    // Load 1 key from the array
    uint8_t i = incremental_load_index;
    uint8_t layer = incremental_load_layer;

    if (layer < 12) {
        per_key_actuation_t *full = &per_key_actuations[layer].keys[i];
        active_per_key_cache[i].actuation = full->actuation;
        active_per_key_cache[i].rt_down = full->rapidfire_press_sens;
        active_per_key_cache[i].rt_up = full->rapidfire_release_sens;
        active_per_key_cache[i].flags = full->flags;
    }

    incremental_load_index++;
}

// Refresh the per-key cache on layer change
// If all layers loaded from EEPROM, copies from per_key_actuations array
// Otherwise uses defaults (before first keypress triggers EEPROM load)
void refresh_per_key_cache(uint8_t layer) {
    if (layer == active_per_key_cache_layer) return;  // Already cached
    if (layer >= 12) layer = 0;

    // Check if this layer has been loaded from EEPROM
    bool layer_loaded = (layers_eeprom_loaded & (1 << layer)) != 0;

    if (layer_loaded) {
        // Layer loaded from EEPROM - copy from per_key_actuations array
        for (uint8_t i = 0; i < 70; i++) {
            per_key_actuation_t *full = &per_key_actuations[layer].keys[i];
            active_per_key_cache[i].actuation = full->actuation;
            active_per_key_cache[i].rt_down = full->rapidfire_press_sens;
            active_per_key_cache[i].rt_up = full->rapidfire_release_sens;
            active_per_key_cache[i].flags = full->flags;
        }
    } else {
        // Layer not loaded yet (before first keypress) - use defaults
        for (uint8_t i = 0; i < 70; i++) {
            active_per_key_cache[i].actuation = DEFAULT_ACTUATION_VALUE;
            active_per_key_cache[i].rt_down = 0;
            active_per_key_cache[i].rt_up = 0;
            active_per_key_cache[i].flags = 0;
        }
    }

    // Set cache layer IMMEDIATELY so next 70 calls return early
    active_per_key_cache_layer = layer;
}

// Old diagnostic modes (0-25) removed - see PER_KEY_ACTUATION_USB_DISCONNECT_DIAGNOSIS.md

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

    // Invert column addressing to match physical PCB wiring
    // Physical columns are wired in reverse order on the mux
    // cols 0-7: invert to 7-0, cols 8-13: invert to 13-8
    uint8_t mux_addr;
    if (col < 8) {
        mux_addr = 7 - col;      // 0→7, 1→6, ..., 7→0
    } else {
        mux_addr = 21 - col;     // 8→13, 9→12, ..., 13→8
    }

    writePin(ADG706_A0, mux_addr & 0x01);
    writePin(ADG706_A1, mux_addr & 0x02);
    writePin(ADG706_A2, mux_addr & 0x04);
    writePin(ADG706_A3, mux_addr & 0x08);

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

// Convert actuation point from 0-255 scale to 0-255 distance (now 1:1 mapping)
static inline uint8_t actuation_to_distance(uint8_t actuation) {
    return actuation;  // Direct mapping since both use 0-255 scale
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
    cached_layer_settings_layer = 0xFF;  // Force refresh layer settings
    active_per_key_cache_layer = 0xFF;   // Force refresh per-key cache
}

static inline void update_active_settings(uint8_t current_layer) {
    if (current_layer >= 12) current_layer = 0;

    // Global MIDI settings (not per-layer anymore)
    // These are updated immediately when HID commands are received
    active_settings.velocity_mode = velocity_mode;
    active_settings.velocity_speed_scale = 10;  // Deprecated, using min/max_press_time now
    active_settings.aftertouch_mode = aftertouch_mode;
    active_settings.aftertouch_cc = aftertouch_cc;
    active_settings.vibrato_sensitivity = vibrato_sensitivity;
    active_settings.vibrato_decay_time = vibrato_decay_time;
    cached_layer_settings_layer = current_layer;
}

// ============================================================================
// KEY TYPE CACHE REFRESH (eliminates 140 EEPROM reads per scan)
// ============================================================================

// Refresh key type cache when layer changes
// This reads keycodes from EEPROM once per layer change instead of 140x per scan
static void refresh_key_type_cache(uint8_t layer) {
    if (layer >= 12) layer = 0;

    // Skip if cache is already valid for this layer
    if (key_type_cache_layer == layer) return;

    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            uint32_t key_idx = KEY_INDEX(row, col);
            uint16_t keycode = dynamic_keymap_get_keycode(layer, row, col);

            // Check if DKS key
            if (is_dks_keycode(keycode)) {
                key_type_cache[key_idx] = KEY_TYPE_DKS;
                dks_keycode_cache[key_idx] = keycode;
            }
            // Check if MIDI key by keycode on current layer (not permanent is_midi_key flag)
            // Covers all MIDI ranges: base notes, keysplit, and triplesplit
            else if ((keycode >= 0x7103 && keycode <= 0x71FF) ||
                     (keycode >= 0xC600 && keycode <= 0xC647) ||
                     (keycode >= 0xC670 && keycode <= 0xC6B7)) {
                key_type_cache[key_idx] = KEY_TYPE_MIDI;
                dks_keycode_cache[key_idx] = 0;
            }
            // Normal key
            else {
                key_type_cache[key_idx] = KEY_TYPE_NORMAL;
                dks_keycode_cache[key_idx] = 0;
            }
        }
    }

    key_type_cache_layer = layer;
}

// ============================================================================
// PER-KEY ACTUATION LOOKUP (using optimized 280-byte cache)
// ============================================================================

static inline void get_key_actuation_config(uint32_t key_idx, uint8_t layer,
                                            uint8_t *actuation_point,
                                            uint8_t *rt_down,
                                            uint8_t *rt_up,
                                            uint8_t *flags) {
    // FIXED: Using optimized per-key cache (280 bytes, fits in L1 cache)
    // The cache is refreshed on layer change, so we just read from it here.
    // This replaces the old 6.7KB per_key_actuations[] array access that
    // was causing USB disconnection.

    if (layer >= 12) layer = 0;
    if (key_idx >= 70) {
        // Fallback for invalid key index
        *actuation_point = actuation_to_distance(DEFAULT_ACTUATION_VALUE);
        *rt_down = 0;
        *rt_up = 0;
        *flags = 0;
        return;
    }

    // Ensure cache is valid for current layer
    refresh_per_key_cache(layer);

    // Read from lightweight cache (4 bytes per key, all in L1 cache)
    per_key_config_lite_t *config = &active_per_key_cache[key_idx];

    *actuation_point = actuation_to_distance(config->actuation);
    *rt_down = config->rt_down;
    *rt_up = config->rt_up;
    *flags = config->flags;
}

// ============================================================================
// CALIBRATION FUNCTIONS (libhmk style continuous calibration)
// ============================================================================

static void update_calibration(uint32_t key_idx) {
    key_state_t *key = &key_matrix[key_idx];
    uint32_t now = timer_read32();

    // Stability detection with percentage-based tolerance
    // Must stay within X% of the stable reference value for the entire duration
    uint16_t stability_threshold = (key->adc_rest_value * AUTO_CALIB_STABILITY_PERCENT) / 100;
    if (stability_threshold < AUTO_CALIB_ZERO_TRAVEL_JITTER) {
        stability_threshold = AUTO_CALIB_ZERO_TRAVEL_JITTER;  // Minimum threshold
    }

    // Check if current ADC is close to the last stable reading (scan-to-scan)
    if (abs((int)key->adc_filtered - (int)key->last_adc_value) < stability_threshold) {
        if (!key->is_stable) {
            key->is_stable = true;
            key->stable_time = now;
            key->stable_start_adc = key->adc_filtered;  // Record where stability started
        }
        // Drift guard: if reading has drifted too far from where stability started,
        // reset stability. This prevents gradual drift during a slow key release
        // from keeping is_stable=true across a wide ADC range.
        if (abs((int)key->adc_filtered - (int)key->stable_start_adc) >= stability_threshold) {
            key->is_stable = false;
        }
        // Micro-drift guard: if ADC has moved meaningfully (> CALIBRATION_EPSILON)
        // from where stability started, the key is still considered "stable" for
        // general purposes, but restart the 10-second timer and update the reference.
        // This prevents slow presses from accumulating enough stable time to
        // incorrectly recalibrate the rest value (the old timer from when the key
        // was truly at rest would carry over into the slow press). Temperature drift
        // is slow enough that 10 seconds of post-drift stability is easily achieved.
        else if (abs((int)key->adc_filtered - (int)key->stable_start_adc) > CALIBRATION_EPSILON) {
            key->stable_time = now;
            key->stable_start_adc = key->adc_filtered;
        }
    } else {
        key->is_stable = false;
    }

    // Auto-calibrate rest position when stable, not pressed, AND near rest position
    // Requires stability for full AUTO_CALIB_VALID_RELEASE_TIME (10 seconds)
    // The distance check (< 5% of travel) prevents recalibration during slow presses
    if (key->is_stable && !key->is_pressed &&
        key->distance < AUTO_CALIB_MAX_DISTANCE &&
        timer_elapsed32(key->stable_time) > AUTO_CALIB_VALID_RELEASE_TIME) {
        // Use a small threshold for the rest value update decision.
        // The stability detection (above) already confirmed the reading is stable,
        // so we just need enough hysteresis to avoid chasing 1-2 unit ADC noise.
        // Using CALIBRATION_EPSILON (5) prevents constant micro-updates while
        // still catching real drift (e.g. 27 ADC units over time).
        if (key->adc_filtered > key->adc_rest_value + CALIBRATION_EPSILON ||
            key->adc_filtered < key->adc_rest_value - CALIBRATION_EPSILON) {
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
    bool was_pressed = key->is_pressed;  // Track previous state for null bind

    // FIX: ADC validity check to prevent ghost presses from empty sockets
    // Empty sockets often read very low values (0-500) or very high values (>3500)
    // Actual measured HE sensor values for this keyboard:
    // - Resting (unpressed): 1650-2250 ADC
    // - Pressed (bottom out): 1100-1350 ADC
    // Valid range: 1000-2500 to encompass all valid readings with margin
    if (key->adc_filtered < 1000 || key->adc_filtered > 2500) {
        key->is_pressed = false;
        key->key_dir = KEY_DIR_INACTIVE;
        key->distance = 0;
        return;
    }

    // Get per-key actuation config
    uint8_t actuation_point, rt_down, rt_up, flags;
    get_key_actuation_config(key_idx, current_layer,
                            &actuation_point, &rt_down, &rt_up, &flags);

    // Apply velocity preset actuation override if enabled (MIDI keys only)
    // Check zone type and keysplitvelocitystatus to determine which actuation to use
    // keysplitvelocitystatus: 0=all same, 1=keysplit only, 2=triplesplit only, 3=both
    if (key_type_cache[key_idx] == KEY_TYPE_MIDI) {
        uint8_t zone = midi_key_states[key_idx].zone_type;
        bool use_zone_actuation = false;
        bool zone_actuation_override = false;
        uint8_t zone_actuation_point = 0;

        if (zone == ZONE_TYPE_KEYSPLIT && (keysplitvelocitystatus == 1 || keysplitvelocitystatus == 3)) {
            // Use keysplit zone actuation
            use_zone_actuation = true;
            zone_actuation_override = keysplit_preset_actuation_override;
            zone_actuation_point = keysplit_preset_actuation_point;
        } else if (zone == ZONE_TYPE_TRIPLESPLIT && (keysplitvelocitystatus == 2 || keysplitvelocitystatus == 3)) {
            // Use triplesplit zone actuation
            use_zone_actuation = true;
            zone_actuation_override = triplesplit_preset_actuation_override;
            zone_actuation_point = triplesplit_preset_actuation_point;
        } else {
            // Use base zone actuation
            zone_actuation_override = preset_actuation_override;
            zone_actuation_point = preset_actuation_point;
        }

        // Apply the actuation override if enabled for this zone
        // actuation_point values are 0-40 (0.0-4.0mm), convert to 0-255 distance scale
        if (use_zone_actuation ? zone_actuation_override : preset_actuation_override) {
            actuation_point = ((use_zone_actuation ? zone_actuation_point : preset_actuation_point) * 255) / 40;
        }
    }

    // Determine reset point based on continuous mode flag
    // Continuous mode: reset only when key fully released (distance = 0)
    // Normal mode: reset when key goes above actuation point
    uint8_t reset_point = (flags & PER_KEY_FLAG_CONTINUOUS_RT) ? 0 : actuation_point;

    // Check if rapid trigger is enabled via the flag (not just rt_down != 0)
    // MIDI keys never use per-key RT - they use velocity preset retrigger instead
    bool rt_enabled = (flags & PER_KEY_FLAG_RAPIDFIRE_ENABLED) && (rt_down > 0);
    if (key_type_cache[key_idx] == KEY_TYPE_MIDI) {
        rt_enabled = false;
    }

    if (!rt_enabled) {
        // RT disabled - simple threshold mode
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

    // Null bind integration: notify on key state transitions
    // NOTE: Null bind is now layer-aware - groups only activate on their assigned layer
    uint8_t row = KEY_ROW(key_idx);
    uint8_t col = KEY_COL(key_idx);

    if (key->is_pressed && !was_pressed) {
        // Key just pressed - notify null bind with current travel distance and layer
        nullbind_key_pressed(row, col, key->distance, current_layer);
    } else if (!key->is_pressed && was_pressed) {
        // Key just released - notify null bind
        nullbind_key_released(row, col, current_layer);
    } else if (key->is_pressed) {
        // Key still pressed - update travel for distance-based null bind
        // This is needed for DISTANCE mode to track which key is pressed further
        uint8_t key_index = row * 14 + col;
        if (key_index < 70) {
            // Update the internal travel tracking (done inside nullbind_key_pressed normally,
            // but we need to update it continuously for distance mode)
            extern uint8_t nullbind_key_travel[70];  // Access from orthomidi5x14.c
            nullbind_key_travel[key_index] = key->distance;

            // Re-evaluate which key should be active if distance changed (layer-aware)
            int8_t group_num = nullbind_find_key_group_for_layer(key_index, current_layer);
            if (group_num >= 0) {
                nullbind_update_group_state(group_num);
            }
        }
    }
}

// ============================================================================
// MIDI KEY DETECTION
// ============================================================================

// Get zone type from keycode
// Returns ZONE_TYPE_BASE, ZONE_TYPE_KEYSPLIT, or ZONE_TYPE_TRIPLESPLIT
static uint8_t get_zone_type_from_keycode(uint16_t keycode) {
    // Keysplit keycodes: 0xC600-0xC647
    if (keycode >= 0xC600 && keycode <= 0xC647) {
        return ZONE_TYPE_KEYSPLIT;
    }
    // Triplesplit keycodes: 0xC670-0xC6B7
    if (keycode >= 0xC670 && keycode <= 0xC6B7) {
        return ZONE_TYPE_TRIPLESPLIT;
    }
    // Everything else (including MI_* 0x7103-0x714A) is base zone
    return ZONE_TYPE_BASE;
}

static bool check_is_midi_key(uint8_t row, uint8_t col, uint8_t *note_index_out, uint8_t *zone_type_out) {
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
                // Get the actual keycode to determine zone type
                uint16_t keycode = dynamic_keymap_get_keycode(current_layer, row, col);
                *zone_type_out = get_zone_type_from_keycode(keycode);
                return true;
            }
        }
    }

    return false;
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

    // Use per-key actuation from cache (280 bytes, fits in L1 cache)
    // Cache is refreshed on layer change before this function is called
    uint8_t per_key_actuation = (key_idx < 70) ? active_per_key_cache[key_idx].actuation : DEFAULT_ACTUATION_VALUE;

    // ========================================================================
    // ZONE-SPECIFIC ACTUATION OVERRIDE AND RETRIGGER
    // Check zone type and apply zone-specific settings if enabled
    // keysplitvelocitystatus: 0=all same, 1=keysplit only, 2=triplesplit only, 3=both
    // ========================================================================
    uint8_t zone_type = state->zone_type;
    bool zone_actuation_override = false;
    uint8_t zone_actuation_point = 0;
    uint8_t zone_retrigger_distance = 0;

    if (zone_type == ZONE_TYPE_KEYSPLIT && (keysplitvelocitystatus == 1 || keysplitvelocitystatus == 3)) {
        // Use keysplit zone settings
        zone_actuation_override = keysplit_preset_actuation_override;
        zone_actuation_point = keysplit_preset_actuation_point;
        zone_retrigger_distance = keysplit_preset_retrigger_distance;
    } else if (zone_type == ZONE_TYPE_TRIPLESPLIT && (keysplitvelocitystatus == 2 || keysplitvelocitystatus == 3)) {
        // Use triplesplit zone settings
        zone_actuation_override = triplesplit_preset_actuation_override;
        zone_actuation_point = triplesplit_preset_actuation_point;
        zone_retrigger_distance = triplesplit_preset_retrigger_distance;
    } else {
        // Use base zone settings
        zone_actuation_override = preset_actuation_override;
        zone_actuation_point = preset_actuation_point;
        zone_retrigger_distance = preset_retrigger_distance;
    }

    // Apply actuation override if enabled for this zone
    // zone_actuation_point is 0-40 (0.0-4.0mm), convert to 0-255 distance scale
    if (zone_actuation_override) {
        per_key_actuation = (zone_actuation_point * 255) / 40;
    }

    uint8_t midi_threshold = (per_key_actuation * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 255;
    uint8_t analog_mode = active_settings.velocity_mode;

    // Convert retrigger_distance (0-20 = 0-2.0mm in 0.1mm steps) to travel units
    // Travel units: 240 = full travel (~4mm), so 1mm ≈ 60 units
    // retrigger_distance / 10.0 = mm, mm * 60 = travel units
    // Simplified: retrigger_travel = retrigger_distance * 6
    uint8_t retrigger_travel = zone_retrigger_distance * 6;

    state->was_pressed = state->pressed;
    state->pressed = pressed;

    // Save previous last_travel for retrigger direction detection
    // (last_travel gets updated in velocity mode switch below)
    uint8_t prev_last_travel = state->last_travel;

    // RT velocity modifier - disabled for now to avoid accessing large array in hot path
    // TODO: Add to per_key_config_lite_t cache if needed
    int8_t rapidfire_velocity_mod = 0;

    // ========================================================================
    // VELOCITY MODE PROCESSING
    // All modes store raw_velocity (0-255) for curve application later
    // ========================================================================

    switch (analog_mode) {
        case 0:  // Fixed velocity
            // raw_velocity stays at default (will be handled by get_he_velocity_from_position)
            state->raw_velocity = 255;  // Max raw value, curve will determine actual velocity
            break;

        case 1:  // Peak Travel - Direction Reversal
            // Triggers immediately when key starts moving back up (direction change)
            // OR when key reaches actuation point (instant max velocity)
            // Velocity = how deep you pressed (peak travel)
            {
                const uint8_t MIN_PEAK = 12;              // ~0.2mm minimum depth to trigger
                const uint8_t REVERSAL_THRESHOLD = 3;    // Must decrease by 3 units to count as reversal
                const uint8_t NOTE_OFF_TRAVEL = 6;       // ~0.1mm - note off when below this

                // Track peak travel during press
                if (travel > state->peak_travel) {
                    state->peak_travel = travel;
                }

                // Actuation point reached: trigger immediately at max velocity
                if (!state->velocity_captured && travel >= midi_threshold) {
                    state->raw_velocity = 255;  // Max velocity for full actuation
                    state->velocity_captured = true;
                    state->send_on_release = true;  // Note ON

                    key->base_velocity = MAX_VELOCITY;
                }
                // Direction reversal detection: trigger when key starts coming back up
                else if (!state->velocity_captured &&
                    state->peak_travel >= MIN_PEAK &&
                    travel < state->peak_travel - REVERSAL_THRESHOLD) {

                    // Trigger! Velocity based on peak travel reached
                    uint16_t raw = ((uint16_t)state->peak_travel * 255) / 240;
                    if (raw > 255) raw = 255;
                    if (raw < 1) raw = 1;
                    state->raw_velocity = (uint8_t)raw;
                    state->velocity_captured = true;
                    state->send_on_release = true;  // Note ON

                    // Update base_velocity for RT
                    key->base_velocity = (state->raw_velocity * 127) / 255;
                    if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
                }

                // Note OFF when key returns close to rest
                if (state->send_on_release && travel < NOTE_OFF_TRAVEL) {
                    state->send_on_release = false;
                    state->peak_travel = 0;
                    state->velocity_captured = false;
                    // Reset retrigger state so next press starts clean
                    state->retrigger_peak = 0;
                    state->retrigger_eligible = false;
                    state->retrigger_eligible_point = 0;
                    state->retrigger_move_start = 0;
                }

                state->last_travel = travel;
            }
            break;

        case 2:  // Speed-based (rest to actuation)
            // Measures time from key starting to move to actuation point
            // User can adjust min/max press time to tune velocity curve
            {
                // Start timer when key starts moving from rest
                // Use ChibiOS system ticks (100kHz = 10µs resolution) for precise timing
                if (state->last_travel == 0 && travel > 0) {
                    state->move_start_time = (uint32_t)chVTGetSystemTimeX();
                    state->travel_at_actuation = 0;
                    state->velocity_captured = false;
                    state->release_travel = 0;  // Full press from rest
                }

                // Capture velocity when actuation point is crossed
                if (!state->velocity_captured && travel >= midi_threshold && state->last_travel < midi_threshold) {
                    // Calculate elapsed time in microseconds (10µs resolution from ChibiOS)
                    uint32_t elapsed_ticks = (uint32_t)chVTGetSystemTimeX() - state->move_start_time;
                    uint32_t elapsed_us = TIME_I2US(elapsed_ticks);
                    uint32_t elapsed_ms = elapsed_us / 1000;

                    // Store travel time for GUI display
                    state->travel_time_ms = (elapsed_ms > 65535) ? 65535 : (uint16_t)elapsed_ms;

                    if (elapsed_ms > 0) {
                        // New min/max time-based velocity calculation:
                        // elapsed_ms <= max_time → raw = 255 (max velocity)
                        // elapsed_ms >= min_time → raw = 1 (min velocity, NOT 0 - see below)
                        // Otherwise → linear interpolation
                        // NOTE: We use 1 instead of 0 for minimum because raw_velocity=0
                        // is reserved as "not yet captured" sentinel in get_he_velocity_from_position()
                        uint32_t raw;
                        if (elapsed_ms <= max_press_time) {
                            raw = 255;  // Fastest press = max velocity
                        } else if (elapsed_ms >= min_press_time) {
                            raw = 1;    // Slowest press = min velocity (use 1, not 0!)
                        } else {
                            // Linear interpolation between max_time and min_time
                            // raw = 255 * (min_time - elapsed_ms) / (min_time - max_time)
                            raw = (255 * (min_press_time - elapsed_ms)) / (min_press_time - max_press_time);
                            if (raw < 1) raw = 1;  // Ensure minimum of 1
                        }

                        // Scale velocity by fraction of distance traveled (for partial re-presses)
                        // Full press from 0 to actuation = full velocity
                        // Partial press (e.g., release at 1mm, actuation at 2mm) = scaled velocity
                        if (state->release_travel > 0 && state->release_travel < midi_threshold) {
                            uint16_t distance_traveled = midi_threshold - state->release_travel;
                            raw = (raw * distance_traveled) / midi_threshold;
                            if (raw < 1) raw = 1;  // Ensure minimum of 1
                        }

                        state->raw_velocity = (uint8_t)raw;
                        state->velocity_captured = true;

                        // Update base_velocity for RT
                        key->base_velocity = (state->raw_velocity * 127) / 255;
                        if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
                    } else {
                        // Instant press (sub-1ms) - max velocity
                        uint32_t raw = 255;

                        // Scale velocity for partial re-presses
                        if (state->release_travel > 0 && state->release_travel < midi_threshold) {
                            uint16_t distance_traveled = midi_threshold - state->release_travel;
                            raw = (raw * distance_traveled) / midi_threshold;
                            if (raw < 1) raw = 1;
                        }

                        state->raw_velocity = (uint8_t)raw;
                        state->velocity_captured = true;
                        key->base_velocity = (state->raw_velocity * 127) / 255;
                        if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
                        state->travel_time_ms = 0;
                    }
                }

                // On release, reset and prepare timer for next press
                if (state->was_pressed && !pressed) {
                    state->velocity_captured = false;
                    state->travel_at_actuation = 0;
                    state->release_travel = travel;  // Store release position for scaling
                    // Start timer now so partial release + re-press gets fresh timing
                    state->move_start_time = (uint32_t)chVTGetSystemTimeX();
                    // Reset retrigger state so next press starts clean
                    state->retrigger_peak = 0;
                    state->retrigger_eligible = false;
                    state->retrigger_eligible_point = 0;
                    state->retrigger_move_start = 0;
                }

                state->last_travel = travel;
                state->last_time = now;
            }
            break;

        case 3:  // Speed + Peak Combined - Direction Reversal
            // Triggers on direction reversal like Mode 1
            // OR when key reaches actuation point (uses ONLY speed, ignores peak)
            // Velocity = 50% speed + 50% peak travel (on reversal)
            // Velocity = 100% speed only (on actuation)
            {
                const uint8_t MIN_PEAK3 = 12;             // ~0.2mm minimum depth to trigger
                const uint8_t REVERSAL_THRESHOLD3 = 3;   // Must decrease by 3 units to count as reversal
                const uint8_t NOTE_OFF_TRAVEL3 = 6;      // ~0.1mm - note off when below this

                // Track when key starts moving from rest (for speed calculation)
                if (state->last_travel == 0 && travel > 0) {
                    state->move_start_time = (uint32_t)chVTGetSystemTimeX();
                }

                // Track peak travel during press
                if (travel > state->peak_travel) {
                    state->peak_travel = travel;
                }

                // Actuation point reached: trigger using ONLY speed (ignore peak since it's maxed)
                if (!state->velocity_captured && travel >= midi_threshold) {
                    // Calculate elapsed time from start to actuation
                    uint32_t elapsed_ticks = (uint32_t)chVTGetSystemTimeX() - state->move_start_time;
                    uint32_t elapsed_us = TIME_I2US(elapsed_ticks);
                    uint32_t elapsed_ms = elapsed_us / 1000;

                    // Store travel time for GUI display
                    state->travel_time_ms = (elapsed_ms > 65535) ? 65535 : (uint16_t)elapsed_ms;

                    // Use ONLY speed component (peak is maxed, so ignore it)
                    uint32_t speed_raw;
                    if (elapsed_ms > 0) {
                        if (elapsed_ms <= max_press_time) {
                            speed_raw = 255;
                        } else if (elapsed_ms >= min_press_time) {
                            speed_raw = 1;
                        } else {
                            speed_raw = (255 * (min_press_time - elapsed_ms)) / (min_press_time - max_press_time);
                            if (speed_raw < 1) speed_raw = 1;
                        }
                    } else {
                        speed_raw = 255;
                        state->travel_time_ms = 0;
                    }

                    state->raw_velocity = (uint8_t)speed_raw;
                    state->velocity_captured = true;
                    state->send_on_release = true;  // Note ON

                    key->base_velocity = (state->raw_velocity * 127) / 255;
                    if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
                }
                // Direction reversal detection: trigger when key starts coming back up
                else if (!state->velocity_captured &&
                    state->peak_travel >= MIN_PEAK3 &&
                    travel < state->peak_travel - REVERSAL_THRESHOLD3) {

                    // Calculate elapsed time from start to peak
                    uint32_t elapsed_ticks = (uint32_t)chVTGetSystemTimeX() - state->move_start_time;
                    uint32_t elapsed_us = TIME_I2US(elapsed_ticks);
                    uint32_t elapsed_ms = elapsed_us / 1000;

                    // Store travel time for GUI display
                    state->travel_time_ms = (elapsed_ms > 65535) ? 65535 : (uint16_t)elapsed_ms;

                    // Calculate speed component using min/max time settings
                    uint32_t speed_raw;
                    if (elapsed_ms > 0) {
                        if (elapsed_ms <= max_press_time) {
                            speed_raw = 255;  // Fastest press = max velocity
                        } else if (elapsed_ms >= min_press_time) {
                            speed_raw = 1;    // Slowest press = min velocity
                        } else {
                            speed_raw = (255 * (min_press_time - elapsed_ms)) / (min_press_time - max_press_time);
                            if (speed_raw < 1) speed_raw = 1;
                        }
                    } else {
                        speed_raw = 255;  // Sub-1ms press = max speed
                        state->travel_time_ms = 0;
                    }

                    // Calculate travel component (0-255)
                    uint16_t travel_raw = ((uint16_t)state->peak_travel * 255) / 240;
                    if (travel_raw > 255) travel_raw = 255;

                    // Blend: 50% speed + 50% travel
                    uint8_t blended = (uint8_t)(((uint16_t)speed_raw * 50 + travel_raw * 50) / 100);
                    state->raw_velocity = (blended < 1) ? 1 : blended;
                    state->velocity_captured = true;
                    state->send_on_release = true;  // Note ON

                    // Update base_velocity for RT
                    key->base_velocity = (state->raw_velocity * 127) / 255;
                    if (key->base_velocity < MIN_VELOCITY) key->base_velocity = MIN_VELOCITY;
                }

                // Note OFF when key returns close to rest
                if (state->send_on_release && travel < NOTE_OFF_TRAVEL3) {
                    state->send_on_release = false;
                    state->peak_travel = 0;
                    state->velocity_captured = false;
                    // Reset retrigger state so next press starts clean
                    state->retrigger_peak = 0;
                    state->retrigger_eligible = false;
                    state->retrigger_eligible_point = 0;
                    state->retrigger_move_start = 0;
                }

                state->last_travel = travel;
            }
            break;
    }

    // ========================================================================
    // MIDI RETRIGGER PROCESSING (velocity preset feature)
    // Re-triggers note-on by sending note-off + note-on directly (bypasses QMK matrix)
    // Eligibility: key rises by retrigger_distance from peak (distance-based, any position)
    // 10% hysteresis: must press 10% of actuation distance past eligible point to fire
    // Speed-based velocity with distance cap based on available travel
    // ========================================================================
    if (retrigger_travel > 0 && state->velocity_captured) {
        // Track peak travel for retrigger eligibility
        if (travel > state->retrigger_peak) {
            state->retrigger_peak = travel;
            state->retrigger_eligible = false;  // Going deeper, reset eligibility
            state->retrigger_move_start = 0;    // Reset speed timer
        }

        // Check for retrigger eligibility: key has risen by retrigger_travel from peak
        // Purely distance-based - no requirement to be above actuation point
        if (!state->retrigger_eligible &&
            state->retrigger_peak > 0 &&
            state->retrigger_peak > retrigger_travel &&
            travel <= state->retrigger_peak - retrigger_travel) {
            state->retrigger_eligible = true;
            state->retrigger_eligible_point = travel;  // Record position for speed + cap
            state->retrigger_move_start = 0;           // Speed timer starts on downward movement
        }

        if (state->retrigger_eligible) {
            if (travel > prev_last_travel) {
                // Key moving down - start speed timer on first downward movement
                if (state->retrigger_move_start == 0) {
                    state->retrigger_move_start = (uint32_t)chVTGetSystemTimeX();
                }

                // 10% hysteresis: must press 10% of actuation distance past eligible point
                uint8_t hysteresis = midi_threshold / 10;
                if (hysteresis < 1) hysteresis = 1;

                uint8_t repress_distance = travel - state->retrigger_eligible_point;

                if (repress_distance >= hysteresis) {
                    // --- Speed-based velocity ---
                    // Measure from eligible point to current (where hysteresis threshold crossed)
                    uint32_t elapsed_ticks = (uint32_t)chVTGetSystemTimeX() - state->retrigger_move_start;
                    uint32_t elapsed_us = TIME_I2US(elapsed_ticks);
                    uint32_t elapsed_ms = elapsed_us / 1000;

                    uint32_t speed_raw;
                    if (elapsed_ms == 0 || elapsed_ms <= max_press_time) {
                        speed_raw = 255;
                    } else if (elapsed_ms >= min_press_time) {
                        speed_raw = 1;
                    } else {
                        speed_raw = (255 * (min_press_time - elapsed_ms)) / (min_press_time - max_press_time);
                        if (speed_raw < 1) speed_raw = 1;
                    }

                    // --- Velocity cap based on available travel ---
                    // Cap = (actuation - release_point) / actuation
                    // release_point = retrigger_eligible_point (where key became eligible)
                    uint16_t velocity_cap;
                    if (midi_threshold > state->retrigger_eligible_point) {
                        velocity_cap = ((uint16_t)(midi_threshold - state->retrigger_eligible_point) * 255) / midi_threshold;
                    } else {
                        velocity_cap = 0;
                    }
                    if (velocity_cap > 255) velocity_cap = 255;

                    // Apply cap to speed velocity
                    uint16_t capped_raw = (speed_raw * velocity_cap) / 255;
                    if (capped_raw < 1) capped_raw = 1;
                    if (capped_raw > 255) capped_raw = 255;

                    state->raw_velocity = (uint8_t)capped_raw;

                    // Get final velocity through zone-appropriate curve/min/max mapping
                    uint8_t row = KEY_ROW(key_idx);
                    uint8_t col = KEY_COL(key_idx);
                    uint8_t velocity;

                    if (state->zone_type == ZONE_TYPE_KEYSPLIT &&
                        (keysplitvelocitystatus == 1 || keysplitvelocitystatus == 3)) {
                        velocity = get_keysplit_he_velocity_from_position(row, col);
                    } else if (state->zone_type == ZONE_TYPE_TRIPLESPLIT &&
                               (keysplitvelocitystatus == 2 || keysplitvelocitystatus == 3)) {
                        velocity = get_triplesplit_he_velocity_from_position(row, col);
                    } else {
                        velocity = get_he_velocity_from_position(row, col);
                    }

                    // Send note-off (respects sustain/queue) then note-on directly
                    uint8_t raw_travel = (travel * 255) / 240;
                    midi_send_noteoff_with_recording(state->note_channel, state->midi_note, 127, 0, state->zone_type);
                    midi_send_noteon_with_recording(state->note_channel, state->midi_note, velocity, raw_travel);

                    // Store for GUI display
                    analog_matrix_store_final_velocity(row, col, velocity);

                    // Reset for next retrigger cycle
                    state->retrigger_eligible = false;
                    state->retrigger_peak = travel;     // New peak starts here
                    state->retrigger_move_start = 0;
                }
            } else if (travel < prev_last_travel) {
                // Key still moving up while eligible - update eligible point if higher
                if (travel < state->retrigger_eligible_point) {
                    state->retrigger_eligible_point = travel;
                }
                state->retrigger_move_start = 0;  // Reset speed timer for next downward move
            }
        }
    }

    // ========================================================================
    // RT VELOCITY ACCUMULATION
    // Applies velocity modifier on rapid trigger re-presses
    // ========================================================================
    if (key->key_dir != KEY_DIR_INACTIVE && pressed && !state->was_pressed && state->velocity_captured) {
        // RT re-trigger with existing velocity - accumulate modifier
        int16_t new_raw = state->raw_velocity + (rapidfire_velocity_mod * 2);  // Scale modifier to 0-255 range
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
    // Uses per-key actuation from cache for threshold
    if (active_settings.aftertouch_mode > 0 && pressed) {
        uint8_t aftertouch_value = 0;
        bool send_aftertouch = false;

        // Use per-key actuation from cache for aftertouch threshold
        uint8_t per_key_act = (key_idx < 70) ? active_per_key_cache[key_idx].actuation : DEFAULT_ACTUATION_VALUE;
        uint8_t normal_threshold = (per_key_act * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 255;

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

static void initialize_midi_states(void) {
    if (midi_states_initialized) return;

    memset(midi_key_states, 0, sizeof(midi_key_states));

    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            uint32_t key_idx = KEY_INDEX(row, col);
            uint8_t note_index;
            uint8_t zone_type;
            if (check_is_midi_key(row, col, &note_index, &zone_type)) {
                midi_key_states[key_idx].is_midi_key = true;
                midi_key_states[key_idx].note_index = note_index;
                midi_key_states[key_idx].zone_type = zone_type;
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

            // Store raw value for debugging
            key->adc_raw = raw_value;

            // TROUBLESHOOTING: Bypass EMA filter, use raw ADC directly
            // Original: key->adc_filtered = EMA(raw_value, key->adc_filtered);
            key->adc_filtered = raw_value;

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

    // Initialize mux address pins
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

            // Initialize EMA with first readings and estimate per-key calibration
            for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
                uint32_t key_idx = KEY_INDEX(row, col);
                uint16_t rest_value = samples[row];

                key_matrix[key_idx].adc_filtered = rest_value;
                key_matrix[key_idx].adc_rest_value = rest_value;

                // Smart estimation of bottom-out value using linear formula
                // bottom = rest * 0.52 + 200 (best fit for measured Hall sensors)
                // This accounts for sensors with higher rest values needing more range
                uint16_t estimated_bottom = ((uint32_t)rest_value * WARM_UP_BOTTOM_SLOPE / 1000) + WARM_UP_BOTTOM_OFFSET;
                key_matrix[key_idx].adc_bottom_out_value = estimated_bottom;
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

    // Chunked EEPROM loading: triggered on first keypress, loads ALL 12 layers
    // Reads 1 row (112 bytes) per scan cycle: 12 layers × 5 rows = 60 scan cycles total
    if (!per_key_eeprom_loaded && !chunked_load_active) {
        // Check if any key is pressed to trigger loading all layers
        for (uint32_t i = 0; i < NUM_KEYS; i++) {
            if (key_matrix[i].distance > 20) {
                start_chunked_eeprom_load_all();  // Load all 12 layers
                break;
            }
        }
    }

    // Process one chunk per scan cycle (if any loading is active)
    process_chunked_eeprom_load();

    // Get current layer
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    if (current_layer >= 12) current_layer = 0;

    // Refresh key type cache on layer change (eliminates 140 EEPROM reads per scan)
    refresh_key_type_cache(current_layer);

    // Refresh per-key actuation cache on layer change (fills defaults, marks cache valid)
    refresh_per_key_cache(current_layer);

    // DISABLED: Incremental loading causes USB disconnect even at 1 key per scan
    // The struct field access pattern from per_key_actuations array is problematic
    // See PER_KEY_ACTUATION_USB_DISCONNECT_DIAGNOSIS.md
    // incremental_load_per_key_cache();

    // Process MIDI keys (uses cached is_midi_key flag and per-key actuation - no EEPROM reads)
    if (midi_states_initialized && active_settings.velocity_mode > 0) {
        for (uint32_t i = 0; i < NUM_KEYS; i++) {
            if (key_type_cache[i] == KEY_TYPE_MIDI) {
                process_midi_key_analog(i, current_layer);
            }
        }
    }

    // Process DKS keys (uses cached key types and keycodes - no EEPROM reads)
    for (uint32_t i = 0; i < NUM_KEYS; i++) {
        if (key_type_cache[i] == KEY_TYPE_DKS) {
            uint8_t row = KEY_ROW(i);
            uint8_t col = KEY_COL(i);
            // Convert distance to travel for DKS (backward compatibility)
            uint8_t travel = distance_to_travel_compat(key_matrix[i].distance);
            dks_process_key(row, col, travel, dks_keycode_cache[i]);
        }
    }

    // Build matrix from key states (uses cached key types and per-key actuation - no EEPROM reads)
    uint8_t analog_mode = active_settings.velocity_mode;

    for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
        matrix_row_t current_row_value = 0;

        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            uint32_t key_idx = KEY_INDEX(row, col);
            key_state_t *key = &key_matrix[key_idx];
            bool pressed = false;

            // Use cached key type instead of EEPROM read
            uint8_t key_type = key_type_cache[key_idx];

            if (key_type == KEY_TYPE_DKS) {
                // DKS keys handle their own keycodes internally
                pressed = false;
            } else if (key_type == KEY_TYPE_MIDI) {
                midi_key_state_t *state = &midi_key_states[key_idx];
                uint8_t travel = distance_to_travel_compat(key->distance);

                // Use per-key actuation from cache (fast, in L1 cache)
                uint8_t per_key_act = (key_idx < 70) ? active_per_key_cache[key_idx].actuation : DEFAULT_ACTUATION_VALUE;
                uint8_t midi_threshold = (per_key_act * FULL_TRAVEL_UNIT * TRAVEL_SCALE) / 255;

                switch (analog_mode) {
                    case 0:  // Fixed
                        pressed = key->is_pressed && (travel >= midi_threshold);
                        break;
                    case 1:  // Peak
                        pressed = state->send_on_release;
                        break;
                    case 2:  // Speed
                        pressed = (travel >= midi_threshold) && state->velocity_captured;
                        break;
                    case 3:  // Speed+Peak
                        pressed = state->send_on_release;
                        break;
                }

                if ((active_settings.aftertouch_mode == 1 || active_settings.aftertouch_mode == 2) &&
                    aftertouch_pedal_active && state->was_pressed) {
                    pressed = true;
                }
            } else {
                // Normal key (KEY_TYPE_NORMAL) - use RT state
                pressed = key->is_pressed;
            }

            if (pressed) {
                // Check if null bind wants to block this key (SOCD handling)
                // NOTE: Null bind is layer-aware - only checks groups on current layer
                if (!nullbind_should_null_key(row, col, current_layer)) {
                    current_row_value |= (MATRIX_ROW_SHIFTER << col);
                }
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

// Get last measured travel time in milliseconds for a key
uint16_t analog_matrix_get_travel_time_ms(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return midi_key_states[key_idx].travel_time_ms;
}

// Get final velocity (0-127, after curve application) for a key
// This returns the LAST SENT velocity from when the key triggered a MIDI note
uint8_t analog_matrix_get_final_velocity(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return midi_key_states[key_idx].final_velocity;
}

// Store the final velocity when a MIDI note is sent
// This should be called from process_midi when sending note-on
void analog_matrix_store_final_velocity(uint8_t row, uint8_t col, uint8_t velocity) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;
    uint32_t key_idx = KEY_INDEX(row, col);
    midi_key_states[key_idx].final_velocity = velocity;
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

// Get actual raw ADC value (no filtering)
uint16_t analog_matrix_get_raw_adc(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].adc_raw;
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

    // Always update current layer - firmware is always per-key per-layer
    per_key_actuations[cached_layer].keys[key_idx].actuation = point;
}

void analog_matrix_set_rapid_trigger(uint8_t row, uint8_t col, uint8_t sensitivity) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return;

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

// Get calibration rest ADC value
uint16_t analog_matrix_get_rest_adc(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].adc_rest_value;
}

// Get calibration bottom-out ADC value
uint16_t analog_matrix_get_bottom_adc(uint8_t row, uint8_t col) {
    if (row >= MATRIX_ROWS || col >= MATRIX_COLS) return 0;
    uint32_t key_idx = KEY_INDEX(row, col);
    return key_matrix[key_idx].adc_bottom_out_value;
}
