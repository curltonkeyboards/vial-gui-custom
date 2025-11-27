// Combined Zone Effects - Efficient Direct Calculation Architecture - FIXED
#include "process_midi.h"

// Define MAX_SUSTAIN_NOTES if not already defined
#ifndef MAX_SUSTAIN_NOTES
#define MAX_SUSTAIN_NOTES 16
#endif

#include <math.h>
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Function declarations for external use
void add_lighting_macro_note(uint8_t channel, uint8_t note, uint8_t track_id);
void remove_lighting_macro_note(uint8_t channel, uint8_t note, uint8_t track_id);
void add_lighting_live_note(uint8_t channel, uint8_t note);
void remove_lighting_live_note(uint8_t channel, uint8_t note);

// BPM system integration (only used by live system)
extern bool bpm_flash_state;
extern uint8_t bpm_beat_count;
extern void update_bpm_flash(void);

// =============================================================================
// POSITION SYSTEM STRUCTURES
// =============================================================================

#define MAX_POSITION_POINTS 16

typedef struct {
    uint8_t row;
    uint8_t col;
} position_point_t;

typedef struct {
    position_point_t points[MAX_POSITION_POINTS];
    uint8_t count;
} position_data_t;

// =============================================================================
// UNIFIED NOTE STORAGE
// =============================================================================

#define MAX_UNIFIED_LIGHTING_NOTES 96
static uint8_t unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES][5]; // Added 5th element for timestamp
static uint8_t unified_lighting_count = 0;
// type: 0=live/sustained, 1=macro

// =============================================================================
// EFFICIENT NOTE TRACKING SYSTEM
// =============================================================================

#define MAX_ACTIVE_NOTES 32

typedef struct {
    uint8_t row, col;           // Position where note was triggered
    uint16_t start_time;        // When it started
    uint8_t color_id;          // Color/channel
    uint8_t track_id;          // For macro notes
    uint8_t animation_type;    // Store the actual animation type
    bool is_live;              // Live vs macro
    bool active;
} active_note_t;

static active_note_t active_notes[MAX_ACTIVE_NOTES];
static uint8_t active_note_count = 0;

// Heat map arrays for heat and sustain effects
static uint8_t live_led_heatmap[RGB_MATRIX_LED_COUNT];
static uint8_t live_led_color_id[RGB_MATRIX_LED_COUNT];
static uint8_t macro_led_heatmap[RGB_MATRIX_LED_COUNT];
static uint8_t macro_led_color_id[RGB_MATRIX_LED_COUNT];

// Sustain key tracking
#define MAX_HELD_KEYS 16
typedef struct {
    uint8_t channel;
    uint8_t note;
    uint8_t track_id;
    uint8_t color_id;
    uint16_t start_time;
    uint8_t positioning_type;
    bool is_macro;
    bool active;
} held_key_t;
static held_key_t sustained_keys[MAX_HELD_KEYS];

// =============================================================================
// BPM BACKGROUND SYSTEM (only used by live system)
// =============================================================================

static bool last_bpm_flash_state = false;
static uint32_t bpm_pulse_start_time = 0;
static uint8_t bpm_pulse_intensity = 0;
static uint8_t bpm_all_beat_count = 0;
static uint8_t bpm_random_colors[5][14][2]; // Store only [hue, saturation] 
static bool bpm_colors_generated = false;
void on_note_pressed(void);
// Heatmap configuration constants
#define TRUEKEY_HEATMAP_INCREASE_STEP 128
#define TRUEKEY_HEATMAP_DECREASE_DELAY_MS 25

// Global flag to track if true key effects are active
bool truekey_effects_active = false;

// Forward declarations
static void apply_backlight(uint8_t brightness_pct, background_mode_t background_mode, uint8_t background_brightness_pct);
static void render_bpm_background(background_mode_t background_mode, uint8_t background_brightness_pct);
static bool is_static_background(background_mode_t background_mode);
static void render_autolight_background(background_mode_t background_mode, uint8_t background_brightness_pct);
static bool is_autolight_background(background_mode_t background_mode);
static void render_autolight_with_params(uint8_t brightness_pct, int16_t hue_shift, uint8_t sat_factor);

// =============================================================================
// UNIFIED NOTE MANAGEMENT FUNCTIONS
// =============================================================================

// Add cooldown constants
#define NOTE_COOLDOWN_MS 50  // Minimum time between processing the same note
#define NOTE_COOLDOWN_TICKS (NOTE_COOLDOWN_MS / 10)  // Convert to timer ticks (assuming 10ms timer resolution)

// =============================================================================
// FAST MATH OPTIMIZATIONS - NO CONFLICTS WITH QMK
// =============================================================================

// Pre-computed square root lookup table for values 0-255
static const uint8_t sqrt8_table[256] = {
    0, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8,
    8, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 10, 10, 10, 10, 10,
    10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11,
    11, 11, 11, 11, 11, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 13, 13, 13, 13,
    13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14,
    14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16
};

// Fast sqrt approximation using lookup table (for small values)
static uint8_t sqrt_fast_lookup(uint8_t val) {
    return sqrt8_table[val];
}

// Modified add functions to include timestamp
void add_lighting_macro_note(uint8_t channel, uint8_t note, uint8_t track_id) {
	on_note_pressed();
    remove_lighting_macro_note(channel, note, track_id);
    
    if (unified_lighting_count < MAX_UNIFIED_LIGHTING_NOTES) {
        unified_lighting_notes[unified_lighting_count][0] = channel;
        unified_lighting_notes[unified_lighting_count][1] = note;
        unified_lighting_notes[unified_lighting_count][2] = 1; // type: macro
        unified_lighting_notes[unified_lighting_count][3] = track_id;
        unified_lighting_notes[unified_lighting_count][4] = 0; // timestamp: 0 = needs processing
        unified_lighting_count++;
    } else {
        // Circular buffer - remove oldest
        for (uint8_t i = 0; i < MAX_UNIFIED_LIGHTING_NOTES - 1; i++) {
            unified_lighting_notes[i][0] = unified_lighting_notes[i + 1][0];
            unified_lighting_notes[i][1] = unified_lighting_notes[i + 1][1];
            unified_lighting_notes[i][2] = unified_lighting_notes[i + 1][2];
            unified_lighting_notes[i][3] = unified_lighting_notes[i + 1][3];
            unified_lighting_notes[i][4] = unified_lighting_notes[i + 1][4];
        }
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][0] = channel;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][1] = note;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][2] = 1; // type: macro
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][3] = track_id;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][4] = 0; // timestamp: 0 = needs processing
    }
}

void add_lighting_live_note(uint8_t channel, uint8_t note) {
	on_note_pressed();
    remove_lighting_live_note(channel, note);
    
    if (unified_lighting_count < MAX_UNIFIED_LIGHTING_NOTES) {
        unified_lighting_notes[unified_lighting_count][0] = channel;
        unified_lighting_notes[unified_lighting_count][1] = note;
        unified_lighting_notes[unified_lighting_count][2] = 0; // type: live
        unified_lighting_notes[unified_lighting_count][3] = 0; // no track_id
        unified_lighting_notes[unified_lighting_count][4] = 0; // timestamp: 0 = needs processing
        unified_lighting_count++;
    } else {
        // Circular buffer - remove oldest
        for (uint8_t i = 0; i < MAX_UNIFIED_LIGHTING_NOTES - 1; i++) {
            unified_lighting_notes[i][0] = unified_lighting_notes[i + 1][0];
            unified_lighting_notes[i][1] = unified_lighting_notes[i + 1][1];
            unified_lighting_notes[i][2] = unified_lighting_notes[i + 1][2];
            unified_lighting_notes[i][3] = unified_lighting_notes[i + 1][3];
            unified_lighting_notes[i][4] = unified_lighting_notes[i + 1][4];
        }
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][0] = channel;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][1] = note;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][2] = 0; // type: live
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][3] = 0; // no track_id
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][4] = 0; // timestamp: 0 = needs processing
    }
}


void remove_lighting_macro_note(uint8_t channel, uint8_t note, uint8_t track_id) {
    for (uint8_t i = 0; i < unified_lighting_count; i++) {
        if (unified_lighting_notes[i][0] == channel && 
            unified_lighting_notes[i][1] == note && 
            unified_lighting_notes[i][2] == 1 && // type: macro
            unified_lighting_notes[i][3] == track_id) {
            for (uint8_t j = i; j < unified_lighting_count - 1; j++) {
                unified_lighting_notes[j][0] = unified_lighting_notes[j + 1][0];
                unified_lighting_notes[j][1] = unified_lighting_notes[j + 1][1];
                unified_lighting_notes[j][2] = unified_lighting_notes[j + 1][2];
                unified_lighting_notes[j][3] = unified_lighting_notes[j + 1][3];
            }
            unified_lighting_count--;
            break;
        }
    }
}

void remove_lighting_live_note(uint8_t channel, uint8_t note) {
    for (uint8_t i = 0; i < unified_lighting_count; i++) {
        if (unified_lighting_notes[i][0] == channel && 
            unified_lighting_notes[i][1] == note && 
            unified_lighting_notes[i][2] == 0) { // type: live
            for (uint8_t j = i; j < unified_lighting_count - 1; j++) {
                unified_lighting_notes[j][0] = unified_lighting_notes[j + 1][0];
                unified_lighting_notes[j][1] = unified_lighting_notes[j + 1][1];
                unified_lighting_notes[j][2] = unified_lighting_notes[j + 1][2];
                unified_lighting_notes[j][3] = unified_lighting_notes[j + 1][3];
            }
            unified_lighting_count--;
            break;
        }
    }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

static uint8_t cap_brightness(uint16_t value) {
    return value > 255 ? 255 : (uint8_t)value;
}

static uint8_t distance_lookup[5][14][5][14];
static bool distance_table_initialized = false;

static uint8_t calculate_distance(uint8_t row1, uint8_t col1, uint8_t row2, uint8_t col2) {
    int8_t dx = col2 - col1;
    int8_t dy = row2 - row1;
    
    // Use integer sqrt approximation for better accuracy than Manhattan distance
    uint16_t dx_sq = dx * dx;
    uint16_t dy_sq = dy * dy;
    uint16_t dist_sq = dx_sq + dy_sq;
    
    if (dist_sq < 256) {
        return sqrt_fast_lookup(dist_sq);
    } else {
        // For distances > 15, use approximation
        return 15;
    }
}

// Initialize distance lookup table
static void init_distance_table(void) {
    if (distance_table_initialized) return;
    
    for (uint8_t r1 = 0; r1 < 5; r1++) {
        for (uint8_t c1 = 0; c1 < 14; c1++) {
            for (uint8_t r2 = 0; r2 < 5; r2++) {
                for (uint8_t c2 = 0; c2 < 14; c2++) {
                    distance_lookup[r1][c1][r2][c2] = calculate_distance(r1, c1, r2, c2);
                }
            }
        }
    }
    distance_table_initialized = true;
}

// Fast distance lookup (use this for ripple/burst effects)
static uint8_t get_distance_fast(uint8_t row1, uint8_t col1, uint8_t row2, uint8_t col2) {
    if (!distance_table_initialized) {
        init_distance_table();
    }
    return distance_lookup[row1][col1][row2][col2];
}

static const uint8_t gradient_themes[21][4] = {
    // 37: Temperature Gradient (original)
    {0, 43, 85, 170},        // Red → Orange → Yellow → Blue
    
    // Atmospheric/Natural (65-72)
    {170, 213, 255, 43},     // 65: Synthwave - Purple → Pink → Cyan → Yellow  
    {85, 128, 170, 200},     // 66: Ocean Depth - Turquoise → Blue → Navy → Deep
    {43, 21, 0, 213},        // 67: Sunset Horizon - Yellow → Orange → Red → Purple
    {106, 128, 213, 170},    // 68: Aurora Borealis - Green → Green → Purple → Blue
    {64, 85, 106, 21},       // 69: Forest Canopy - Lime → Green → Pine → Brown
    {43, 21, 0, 21},         // 70: Desert Mirage - Yellow → Orange → Red → Brown
    {0, 43, 21, 0},          // 71: Volcanic Flow - White(Red) → Yellow → Orange → Black(Red)
    {170, 180, 190, 200},    // 72: Ice Crystal - White(Cyan) → Cyan → Blue → Deep Blue
    
    // Fantasy/Mystical (73-76)
    {64, 85, 106, 128},      // 73: Toxic Waste - Yellow → Lime → Green → Dark Green
    {213, 170, 180, 0},      // 74: Deep Space - White(Magenta) → Purple → Blue → Black
    {213, 170, 128, 106},    // 75: Crystal Cave - White(Magenta) → Purple → Amethyst → Violet
    {43, 85, 213, 0},        // 76: Enchanted Forest - Gold → Emerald → Purple → Black
    
    // Floral/Garden (77-80)
    {255, 213, 0, 85},       // 77: Rose Garden - Pink → Hot Pink → Red → Green
    {43, 21, 213, 85},       // 78: Tropical Paradise - Yellow → Coral → Pink → Green
    {255, 234, 213, 21},     // 79: Cherry Blossom - White(Pink) → Pale Pink → Pink → Brown
    {43, 21, 0, 21},         // 80: Autumn Leaves - Yellow → Orange → Red → Brown
    
    // Urban/Tech (81-84)
    {255, 213, 170, 128},    // 81: Neon City - White(Magenta) → Pink → Blue → Dark
    {85, 170, 213, 128},     // 82: Cyberpunk Alley - Green → Blue → Pink → Purple
    {85, 96, 106, 0},        // 83: Matrix Code - Bright Green → Green → Dark Green → Black
    {43, 21, 0, 0}           // 84: Retro Arcade - Yellow → Orange → Red → Deep Red
};

// Saturation adjustments for specific themes (255 = max, 220 = med, 170 = low)
static const uint8_t gradient_sat_override[21] = {
    220, // 37: Temperature (med sat)
    255, // 65: Synthwave (max sat)
    200, // 66: Ocean Depth (med-high sat)
    255, // 67: Sunset Horizon (max sat)
    220, // 68: Aurora Borealis (med sat)
    190, // 69: Forest Canopy (med-low sat)
    220, // 70: Desert Mirage (med sat)
    220, // 71: Volcanic Flow (med sat)
    170, // 72: Ice Crystal (low sat)
    255, // 73: Toxic Waste (max sat)
    220, // 74: Deep Space (med sat)
    220, // 75: Crystal Cave (med sat)
    220, // 76: Enchanted Forest (med sat)
    200, // 77: Rose Garden (med-high sat)
    255, // 78: Tropical Paradise (max sat)
    170, // 79: Cherry Blossom (low sat)
    220, // 80: Autumn Leaves (med sat)
    255, // 81: Neon City (max sat)
    255, // 82: Cyberpunk Alley (max sat)
    255, // 83: Matrix Code (max sat)
    255  // 84: Retro Arcade (max sat)
};

static HSV get_effect_color_hsv(uint8_t base_hue, uint8_t base_sat, uint8_t base_val, 
                               uint8_t effect_type, uint8_t color_id, 
                               uint8_t note_row, uint8_t note_col, 
                               uint8_t led_row, uint8_t led_col, 
                               uint16_t elapsed_time, bool is_live) {
    
    HSV result = {base_hue, base_sat, base_val};
    
    // Early exit for most common cases (60% of calls)
    if (effect_type == 0) return result; // Base - no change
    
    if (effect_type == 6) { // Base Max Sat
        result.s = 255;
        return result;
    }
    
    if (effect_type == 12) { // Base Desat
        result.s = (base_sat > 80) ? (base_sat - 80) : 0;
        return result;
    }
    
    // Pre-compute common values once
    static const int16_t channel_hue_offsets[16] = {
        0, 85, 170, 43, 213, 128, 28, 248, 60, 192, 11, 126, 36, 147, 241, 6
    };
    
    static const int16_t macro_hue_offsets[5] = {
        0, 85, 170, 43, 213
    };
    
    // Group related effects to reduce branching
    if (effect_type >= 1 && effect_type <= 5) {
        // Fundamental color effects (1-5)
        switch (effect_type) {
            case 1: // Channel
                result.h = (base_hue + channel_hue_offsets[color_id % 16]) % 256;
                break;
            case 2: // Macro
                result.h = (base_hue + macro_hue_offsets[color_id % 5]) % 256;
                break;
            case 3: // Rainbow
                result.h = rand() % 256;
                break;
            case 4: // Pitch Colors Up
            {
                uint8_t note_pitch = color_id > 96 ? 96 : color_id;
                result.h = (base_hue + ((note_pitch * 256) / 96)) % 256;
                break;
            }
            case 5: // Pitch Colors Down
            {
                uint8_t note_pitch = color_id > 96 ? 96 : color_id;
                result.h = (base_hue + (((96 - note_pitch) * 256) / 96)) % 256;
                break;
            }
        }
        return result;
    }
    
    if (effect_type >= 7 && effect_type <= 11) {
        // Fundamental + Max Sat effects (7-11)
        result.s = 255;
        switch (effect_type) {
            case 7: // Channel Max Sat
                result.h = (base_hue + channel_hue_offsets[color_id % 16]) % 256;
                break;
            case 8: // Macro Max Sat
                result.h = (base_hue + macro_hue_offsets[color_id % 5]) % 256;
                break;
            case 9: // Rainbow Max Sat
                result.h = rand() % 256;
                break;
            case 10: // Pitch Colors Up Max Sat
            {
                uint8_t note_pitch = color_id > 96 ? 96 : color_id;
                result.h = (base_hue + ((note_pitch * 256) / 96)) % 256;
                break;
            }
            case 11: // Pitch Colors Down Max Sat
            {
                uint8_t note_pitch = color_id > 96 ? 96 : color_id;
                result.h = (base_hue + (((96 - note_pitch) * 256) / 96)) % 256;
                break;
            }
        }
        return result;
    }
    
    if (effect_type >= 13 && effect_type <= 17) {
        // Fundamental + Desat effects (13-17)
        result.s = (base_sat > 80) ? (base_sat - 80) : 0;
        switch (effect_type) {
            case 13: // Channel Desat
                result.h = (base_hue + channel_hue_offsets[color_id % 16]) % 256;
                break;
            case 14: // Macro Desat
                result.h = (base_hue + macro_hue_offsets[color_id % 5]) % 256;
                break;
            case 15: // Rainbow Desat
                result.h = rand() % 256;
                break;
            case 16: // Pitch Colors Up Desat
            {
                uint8_t note_pitch = color_id > 96 ? 96 : color_id;
                result.h = (base_hue + ((note_pitch * 256) / 96)) % 256;
                break;
            }
            case 17: // Pitch Colors Down Desat
            {
                uint8_t note_pitch = color_id > 96 ? 96 : color_id;
                result.h = (base_hue + (((96 - note_pitch) * 256) / 96)) % 256;
                break;
            }
        }
        return result;
    }
    
    // Pre-calculate distance for distance-based effects (18-35)
    float distance = 0;
    if (effect_type >= 18 && effect_type <= 35) {
        distance = calculate_distance(note_row, note_col, led_row, led_col);
    }
    
    if (effect_type >= 18 && effect_type <= 23) {
        // Fundamental + Distance effects (18-23)
        uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
        switch (effect_type) {
            case 18: // Base Distance
                result.h = (base_hue + distance_hue_shift) % 256;
                break;
            case 19: // Channel Distance
                result.h = (base_hue + channel_hue_offsets[color_id % 16] + distance_hue_shift) % 256;
                break;
            case 20: // Macro Distance
                result.h = (base_hue + macro_hue_offsets[color_id % 5] + distance_hue_shift) % 256;
                break;
            case 21: // Rainbow Distance
                result.h = (rand() % 256 + ((uint8_t)(distance * 30) % 256)) % 256;
                break;
            case 22: // Pitch Colors Up Distance
            {
                uint8_t note_pitch = color_id > 96 ? 96 : color_id;
                result.h = (base_hue + ((note_pitch * 256) / 96) + distance_hue_shift) % 256;
                break;
            }
            case 23: // Pitch Colors Down Distance
            {
                uint8_t note_pitch = color_id > 96 ? 96 : color_id;
                result.h = (base_hue + (((96 - note_pitch) * 256) / 96) + distance_hue_shift) % 256;
                break;
            }
        }
        return result;
    }
    
    // Continue with remaining effects using similar grouping...
    // For brevity, falling back to original switch for remaining cases
    switch (effect_type) {
        case 24: // Base Distance Max Sat
        {
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + distance_hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 25: // Channel Distance Max Sat
        {
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + channel_hue_offsets[color_id % 16] + distance_hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 26: // Macro Distance Max Sat
        {
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + macro_hue_offsets[color_id % 5] + distance_hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 27: // Rainbow Distance Max Sat
        {
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 30) % 256;
            result.h = (rand() % 256 + distance_hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 28: // Pitch Colors Up Distance Max Sat
        {
            uint8_t note_pitch = color_id > 96 ? 96 : color_id;
            uint16_t pitch_hue_shift = (note_pitch * 256) / 96;
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + pitch_hue_shift + distance_hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 29: // Pitch Colors Down Distance Max Sat
        {
            uint8_t note_pitch = color_id > 96 ? 96 : color_id;
            uint16_t pitch_hue_shift = ((96 - note_pitch) * 256) / 96;
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + pitch_hue_shift + distance_hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 30: // Base Distance Desat
        {
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + distance_hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 31: // Channel Distance Desat
        {
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + channel_hue_offsets[color_id % 16] + distance_hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 32: // Macro Distance Desat
        {
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + macro_hue_offsets[color_id % 5] + distance_hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 33: // Rainbow Distance Desat
        {
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 30) % 256;
            result.h = (rand() % 256 + distance_hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 34: // Pitch Colors Up Distance Desat
        {
            uint8_t note_pitch = color_id > 96 ? 96 : color_id;
            uint16_t pitch_hue_shift = (note_pitch * 256) / 96;
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + pitch_hue_shift + distance_hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 35: // Pitch Colors Down Distance Desat
        {
            uint8_t note_pitch = color_id > 96 ? 96 : color_id;
            uint16_t pitch_hue_shift = ((96 - note_pitch) * 256) / 96;
            float distance = calculate_distance(note_row, note_col, led_row, led_col);
            uint8_t distance_hue_shift = (uint8_t)(distance * 8.1f) % 64;
            result.h = (base_hue + pitch_hue_shift + distance_hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 36: // Beat Sync
        {
            uint8_t bpm_offset = (bpm_beat_count * 64) % 256;
            result.h = (base_hue + bpm_offset) % 256;
            break;
        }
		// Add this to your switch statement:
		case 37: // Temperature Gradient
		case 65: case 66: case 67: case 68: case 69: case 70: case 71: case 72: case 73:
		case 74: case 75: case 76: case 77: case 78: case 79: case 80: case 81: case 82:
		case 83: case 84: // All other gradient themes
		{
			float distance = calculate_distance(note_row, note_col, led_row, led_col);
			
			uint8_t theme_index;
			if (effect_type == 37) {
				theme_index = 0; // Temperature gradient
			} else {
				theme_index = effect_type - 64; // Maps 65->1, 66->2, etc.
			}
			
			uint8_t hue_index;
			if (distance < 1.0f) {
				hue_index = 0;      // Close
			} else if (distance < 3.0f) {
				hue_index = 1;      // Medium
			} else if (distance < 5.0f) {
				hue_index = 2;      // Far
			} else {
				hue_index = 3;      // Distant
			}
			
			result.h = gradient_themes[theme_index][hue_index];
			result.s = gradient_sat_override[theme_index];
			
			break;
		}
        
        // Location effects - Horizontal (38-46)
        case 38: // Horizontal Soft
        {
            uint8_t hue_shift = (led_col * 64) / 15;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 39: // Horizontal Soft Max Sat
        {
            uint8_t hue_shift = (led_col * 64) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 40: // Horizontal Soft Desat
        {
            uint8_t hue_shift = (led_col * 64) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 41: // Horizontal Medium
        {
            uint8_t hue_shift = (led_col * 128) / 15;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 42: // Horizontal Medium Max Sat
        {
            uint8_t hue_shift = (led_col * 128) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 43: // Horizontal Medium Desat
        {
            uint8_t hue_shift = (led_col * 128) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 44: // Horizontal Strong
        {
            uint8_t hue_shift = (led_col * 192) / 15;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 45: // Horizontal Strong Max Sat
        {
            uint8_t hue_shift = (led_col * 192) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 46: // Horizontal Strong Desat
        {
            uint8_t hue_shift = (led_col * 192) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        
        // Location effects - Diagonal (47-55)
        case 47: // Diagonal Soft
        {
            uint8_t hue_shift = ((led_row + led_col) * 64) / 30;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 48: // Diagonal Soft Max Sat
        {
            uint8_t hue_shift = ((led_row + led_col) * 64) / 30;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 49: // Diagonal Soft Desat
        {
            uint8_t hue_shift = ((led_row + led_col) * 64) / 30;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 50: // Diagonal Medium
        {
            uint8_t hue_shift = ((led_row + led_col) * 128) / 30;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 51: // Diagonal Medium Max Sat
        {
            uint8_t hue_shift = ((led_row + led_col) * 128) / 30;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 52: // Diagonal Medium Desat
        {
            uint8_t hue_shift = ((led_row + led_col) * 128) / 30;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 53: // Diagonal Strong
        {
            uint8_t hue_shift = ((led_row + led_col) * 192) / 30;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 54: // Diagonal Strong Max Sat
        {
            uint8_t hue_shift = ((led_row + led_col) * 192) / 30;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 55: // Diagonal Strong Desat
        {
            uint8_t hue_shift = ((led_row + led_col) * 192) / 30;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        
        // Location effects - Vertical (56-64)
        case 56: // Vertical Soft
        {
            uint8_t hue_shift = (led_row * 64) / 15;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 57: // Vertical Soft Max Sat
        {
            uint8_t hue_shift = (led_row * 64) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 58: // Vertical Soft Desat
        {
            uint8_t hue_shift = (led_row * 64) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 59: // Vertical Medium
        {
            uint8_t hue_shift = (led_row * 128) / 15;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 60: // Vertical Medium Max Sat
        {
            uint8_t hue_shift = (led_row * 128) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 61: // Vertical Medium Desat
        {
            uint8_t hue_shift = (led_row * 128) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        case 62: // Vertical Strong
        {
            uint8_t hue_shift = (led_row * 192) / 15;
            result.h = (base_hue + hue_shift) % 256;
            break;
        }
        case 63: // Vertical Strong Max Sat
        {
            uint8_t hue_shift = (led_row * 192) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = 255;
            break;
        }
        case 64: // Vertical Strong Desat
        {
            uint8_t hue_shift = (led_row * 192) / 15;
            result.h = (base_hue + hue_shift) % 256;
            result.s = (base_sat > 80) ? (base_sat - 80) : 0;
            break;
        }
        
        default:
            break;
    }
    
    return result;
}

// =============================================================================
// POSITION SYSTEM FUNCTIONS (UNCHANGED)
// =============================================================================
static void get_truekey_positions(uint8_t note, position_data_t* positions) {
    positions->count = 0;
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    int16_t note_index = note - 24 - transpose_number - octave_number;
    
    if (note_index >= 0 && note_index < 72) {
        for (uint8_t j = 0; j < 6 && positions->count < MAX_POSITION_POINTS; j++) {
            uint8_t led_index = get_midi_led_position(current_layer, note_index, j);
            if (led_index < RGB_MATRIX_LED_COUNT && led_index != 99) {
                // Convert LED index back to row/col using proper mapping
                for (uint8_t row = 0; row < 5; row++) {
                    for (uint8_t col = 0; col < 14; col++) {
                        uint8_t led[LED_HITS_TO_REMEMBER];
                        uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
                        if (led_count > 0 && led[0] == led_index) {
                            positions->points[positions->count].row = row;
                            positions->points[positions->count].col = col;
                            positions->count++;
                            goto next_position; // Break out of both loops
                        }
                    }
                }
                next_position:;
            }
        }
    }
}

static void get_zone_positions(uint8_t note, position_data_t* positions) {
    uint8_t shifted_note = (note + 36) % 60;
    static const uint8_t octave_to_row[5] = {4, 3, 1, 2, 0};
    static const uint8_t note_to_col[12] = {
        0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12
    };
    
    uint8_t octave = (shifted_note / 12) % 5;
    uint8_t note_in_octave = shifted_note % 12;
    
    positions->count = 1;
    positions->points[0].row = octave_to_row[octave];
    positions->points[0].col = note_to_col[note_in_octave];
    
    if (positions->points[0].col >= 14) positions->points[0].col = 13;
}

static void get_quadrant_positions(uint8_t quadrant, position_data_t* positions) {
    positions->count = 0;
    
    // Define the 5 positions for each quadrant
    uint8_t quadrant_positions[4][5][2] = {
        // Quadrant 1: row 1, cols 1-5
        {{1, 1}, {1, 2}, {1, 3}, {1, 4}, {1, 5}},
        // Quadrant 2: row 1, cols 8-12  
        {{1, 8}, {1, 9}, {1, 10}, {1, 11}, {1, 12}},
        // Quadrant 3: row 3, cols 1-5
        {{3, 1}, {3, 2}, {3, 3}, {3, 4}, {3, 5}},
        // Quadrant 4: row 3, cols 8-12
        {{3, 8}, {3, 9}, {3, 10}, {3, 11}, {3, 12}}
    };
    
    if (quadrant < 1 || quadrant > 4) {
        return;
    }
    
    // Pick one LED from the quadrant based on note processing order
    static uint8_t quadrant_note_counter = 0;
    quadrant_note_counter = (quadrant_note_counter + 1) % 5; // Cycle through 0-4
    
    uint8_t quad_index = quadrant - 1; // Convert to 0-based index
    positions->points[0].row = quadrant_positions[quad_index][quadrant_note_counter][0];
    positions->points[0].col = quadrant_positions[quad_index][quadrant_note_counter][1];
    positions->count = 1;
}

static void get_live_notes_centers_positions(position_data_t* positions) {
    positions->count = 6;
    
    for (uint8_t i = 0; i < 6; i++) {
        positions->points[i].row = 2;
        positions->points[i].col = 4 + i;
    }
}

static void get_note_row_positions(uint8_t note, uint8_t fixed_col, position_data_t* positions) {
    uint8_t note_in_octave = note % 12;
    uint8_t row;
    
    switch (note_in_octave) {
        case 0: case 1: row = 0; break;
        case 2: case 3: row = 1; break;
        case 4: case 5: row = 2; break;
        case 6: case 7: row = 3; break;
        case 8: case 9: row = 4; break;
        case 10: row = 0; break;
        case 11: row = 2; break;
        default: row = 0; break;
    }
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = fixed_col;
}

static void get_note_col_positions(uint8_t note, uint8_t fixed_row, position_data_t* positions) {
    uint8_t note_in_octave = note % 12;
    positions->count = 1;
    
    switch (note_in_octave) {
        case 0:
            positions->count = 2;
            positions->points[0].row = 4;
            positions->points[0].col = 0;
            positions->points[1].row = 4;
            positions->points[1].col = 1;
            break;
        case 1: 
            positions->points[0].row = 4;
            positions->points[0].col = 2; 
            break;
        case 2: 
            positions->points[0].row = 4;
            positions->points[0].col = 3; 
            break;
        case 3: 
            positions->points[0].row = 4;
            positions->points[0].col = 4; 
            break;
        case 4: 
            positions->points[0].row = 4;
            positions->points[0].col = 5; 
            break;
        case 5: 
            positions->points[0].row = 4;
            positions->points[0].col = 6; 
            break;
        case 6: 
            positions->points[0].row = 4;
            positions->points[0].col = 7; 
            break;
        case 7: 
            positions->points[0].row = 4;
            positions->points[0].col = 8; 
            break;
        case 8: 
            positions->points[0].row = 4;
            positions->points[0].col = 9; 
            break;
        case 9: 
            positions->points[0].row = 4;
            positions->points[0].col = 10; 
            break;
        case 10: 
            positions->points[0].row = 4;
            positions->points[0].col = 11; 
            break;
        case 11:
            positions->count = 2;
            positions->points[0].row = 4;
            positions->points[0].col = 12;
            positions->points[1].row = 4;
            positions->points[1].col = 13;
            break;
        default: 
            positions->points[0].row = 4;
            positions->points[0].col = 0; 
            break;
    }
}

static void get_note_row_mixed_positions(uint8_t note, position_data_t* positions) {
    uint8_t note_in_octave = note % 12;
    uint8_t row;
    
    switch (note_in_octave) {
        case 0: case 1: row = 0; break;
        case 2: case 3: row = 1; break;
        case 4: case 5: row = 2; break;
        case 6: case 7: row = 3; break;
        case 8: case 9: row = 4; break;
        case 10: row = 0; break;
        case 11: row = 2; break;
        default: row = 0; break;
    }
    
    uint8_t col = (note_in_octave % 2 == 0) ? 0 : 13;
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = col;
}

static void get_note_col_mixed_positions(uint8_t note, position_data_t* positions) {
    uint8_t note_in_octave = note % 12;
    uint8_t row = (note_in_octave % 2 == 0) ? 0 : 4;
    
    get_note_col_positions(note, row, positions);
}

static void get_loop_row_positions(uint8_t track_id, uint8_t fixed_col, position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = (track_id - 1) % 5; // Use all 5 rows
    positions->points[0].col = fixed_col;
}

static void get_loop_row_alt_positions(uint8_t track_id, position_data_t* positions) {
    uint8_t col = ((track_id - 1) % 2 == 0) ? 0 : 13;
    get_loop_row_positions(track_id, col, positions);
}

static void get_loop_col_positions(uint8_t track_id, uint8_t fixed_row, position_data_t* positions) {
    switch (track_id) {
        case 1:
            positions->count = 2;
            positions->points[0].row = 4;
            positions->points[0].col = 6;
            positions->points[1].row = 4;
            positions->points[1].col = 7;
            break;
        case 2:
            positions->count = 4;
            positions->points[0].row = 4;
            positions->points[0].col = 8;
            positions->points[1].row = 4;
            positions->points[1].col = 9;
            positions->points[2].row = 4;
            positions->points[2].col = 4;
            positions->points[3].row = 4;
            positions->points[3].col = 5;
            break;
        case 3:
            positions->count = 4;
            positions->points[0].row = 4;
            positions->points[0].col = 10;
            positions->points[1].row = 4;
            positions->points[1].col = 11;
            positions->points[2].row = 4;
            positions->points[2].col = 2;
            positions->points[3].row = 4;
            positions->points[3].col = 3;
            break;
        case 4:
            positions->count = 4;
            positions->points[0].row = 4;
            positions->points[0].col = 0;
            positions->points[1].row = 4;
            positions->points[1].col = 1;
            positions->points[2].row = 4;
            positions->points[2].col = 12;
            positions->points[3].row = 4;
            positions->points[3].col = 13;
            break;
        default:
            // Fallback for other track IDs
            positions->count = 1;
            positions->points[0].row = 4;
            positions->points[0].col = 0;
            break;
    }
}

// Dot positioning functions (single dots only)
static void get_top_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 0;
    positions->points[0].col = 6; // Changed from 7 to 6
}

static void get_left_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 2;
    positions->points[0].col = 0;
}

static void get_right_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 2;
    positions->points[0].col = 13;
}

static void get_bottom_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 4;
    positions->points[0].col = 6; // Changed from 7 to 6
}

static void get_center_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 2;
    positions->points[0].col = 6; // Changed from 7 to 6
}

static void get_top_left_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 0;
    positions->points[0].col = 0;
}

static void get_top_right_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 0;
    positions->points[0].col = 13;
}

static void get_bottom_left_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 4;
    positions->points[0].col = 0;
}

static void get_bottom_right_dot_positions(position_data_t* positions) {
    positions->count = 1;
    positions->points[0].row = 4;
    positions->points[0].col = 13;
}

// Note-based positioning functions (deterministic based on note)
static void get_note_corner_dot_positions(uint8_t note, position_data_t* positions) {
    uint8_t corner = note % 4;
    
    switch (corner) {
        case 0: get_top_left_dot_positions(positions); break;
        case 1: get_top_right_dot_positions(positions); break;
        case 2: get_bottom_left_dot_positions(positions); break;
        case 3: get_bottom_right_dot_positions(positions); break;
    }
}

static void get_note_edge_dot_positions(uint8_t note, position_data_t* positions) {
    uint8_t edge = note % 4;
    
    switch (edge) {
        case 0: get_top_dot_positions(positions); break;
        case 1: get_left_dot_positions(positions); break;
        case 2: get_right_dot_positions(positions); break;
        case 3: get_bottom_dot_positions(positions); break;
    }
}

static void get_note_all_dot_positions(uint8_t note, position_data_t* positions) {
    uint8_t dot = note % 9;
    
    switch (dot) {
        case 0: get_top_dot_positions(positions); break;
        case 1: get_left_dot_positions(positions); break;
        case 2: get_right_dot_positions(positions); break;
        case 3: get_bottom_dot_positions(positions); break;
        case 4: get_center_dot_positions(positions); break;
        case 5: get_top_left_dot_positions(positions); break;
        case 6: get_top_right_dot_positions(positions); break;
        case 7: get_bottom_left_dot_positions(positions); break;
        case 8: get_bottom_right_dot_positions(positions); break;
    }
}

// Loop-dependent positioning functions
static void get_loop_block_3x3_positions(uint8_t track_id, position_data_t* positions) {
    positions->count = 0;
    
    uint8_t block = (track_id - 1) % 4;
    uint8_t start_row = 1;
    uint8_t start_col;
    
    switch (block) {
        case 0: start_col = 1; break;  // cols 1-3
        case 1: start_col = 4; break;  // cols 4-6
        case 2: start_col = 7; break;  // cols 7-9
        case 3: start_col = 10; break; // cols 10-12
        default: start_col = 1; break;
    }
    
    // Instead of lighting all 9 LEDs, pick one based on note processing order
    // This creates a pseudo-random but deterministic selection within the 3x3 block
    static uint8_t note_counter = 0;
    note_counter = (note_counter + 1) % 9; // Cycle through 0-8
    
    uint8_t selected_row = start_row + (note_counter / 3);  // 0,0,0,1,1,1,2,2,2
    uint8_t selected_col = start_col + (note_counter % 3);  // 0,1,2,0,1,2,0,1,2
    
    if (selected_row < 5 && selected_col < 14) {
        positions->points[0].row = selected_row;
        positions->points[0].col = selected_col;
        positions->count = 1;
    }
}

static void get_loop_block_center_positions(uint8_t track_id, position_data_t* positions) {
    positions->count = 1;
    
    uint8_t block = (track_id - 1) % 4;
    uint8_t center_row = 2; // Center of the 3x3 block
    uint8_t center_col;
    
    switch (block) {
        case 0: center_col = 2; break;  // Center of cols 1-3
        case 1: center_col = 5; break;  // Center of cols 4-6
        case 2: center_col = 8; break;  // Center of cols 7-9
        case 3: center_col = 11; break; // Center of cols 10-12
        default: center_col = 2; break;
    }
    
    positions->points[0].row = center_row;
    positions->points[0].col = center_col;
}

// Loop-dependent dot positioning functions (assigns loops to corners or edges)
static void get_loop_corner_dot_positions(uint8_t track_id, position_data_t* positions) {
    uint8_t corner = (track_id - 1) % 4;
    
    switch (corner) {
        case 0: get_top_left_dot_positions(positions); break;
        case 1: get_top_right_dot_positions(positions); break;
        case 2: get_bottom_left_dot_positions(positions); break;
        case 3: get_bottom_right_dot_positions(positions); break;
    }
}

static void get_loop_edge_dot_positions(uint8_t track_id, position_data_t* positions) {
    uint8_t edge = (track_id - 1) % 4;
    
    switch (edge) {
        case 0: get_top_dot_positions(positions); break;
        case 1: get_left_dot_positions(positions); break;
        case 2: get_right_dot_positions(positions); break;
        case 3: get_bottom_dot_positions(positions); break;
    }
}

// Two additional zone positioning functions
static void get_zone2_positions(uint8_t note, position_data_t* positions) {
    // Alternative zone mapping - horizontal layout
    uint8_t shifted_note = (note + 12) % 84; // Different shift for variety
    
    uint8_t row = (shifted_note / 14) % 5;    // Distribute across rows by 14s
    uint8_t col = shifted_note % 14;          // Columns 0-13
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = col;
}

static void get_zone3_positions(uint8_t note, position_data_t* positions) {
    // Spiral zone mapping
    uint8_t note_mod = note % 70; // Map to 70 positions
    static const uint8_t spiral_positions[70][2] = {
        // Spiral from outside to inside
        {0,0}, {0,1}, {0,2}, {0,3}, {0,4}, {0,5}, {0,6}, {0,7}, {0,8}, {0,9}, {0,10}, {0,11}, {0,12}, {0,13},
        {1,13}, {2,13}, {3,13}, {4,13}, {4,12}, {4,11}, {4,10}, {4,9}, {4,8}, {4,7}, {4,6}, {4,5}, {4,4}, {4,3}, {4,2}, {4,1}, {4,0},
        {3,0}, {2,0}, {1,0}, {1,1}, {1,2}, {1,3}, {1,4}, {1,5}, {1,6}, {1,7}, {1,8}, {1,9}, {1,10}, {1,11}, {1,12},
        {2,12}, {3,12}, {3,11}, {3,10}, {3,9}, {3,8}, {3,7}, {3,6}, {3,5}, {3,4}, {3,3}, {3,2}, {3,1},
        {2,1}, {2,2}, {2,3}, {2,4}, {2,5}, {2,6}, {2,7}, {2,8}, {2,9}, {2,10}, {2,11}
    };
    
    positions->count = 1;
    positions->points[0].row = spiral_positions[note_mod][0];
    positions->points[0].col = spiral_positions[note_mod][1];
}

static void get_count_to_8_track_positions(position_data_t* positions) {
    static uint8_t count_counter = 0;
    count_counter = (count_counter + 1) % 8;
    
    positions->count = 1;
    positions->points[0].row = 0;
    positions->points[0].col = 1 + count_counter; // cols 1-8
}

// Loop count to 8 positioning - each track gets its own row and moves horizontally
static uint8_t loop_position_counters[8] = {0}; // Support up to 8 tracks

static void get_loop_count_to_8_positions(uint8_t track_id, position_data_t* positions) {
    // Ensure we have a valid track_id (1-based, convert to 0-based for array access)
    uint8_t track_index = (track_id > 0) ? (track_id - 1) % 8 : 0;
    
    // Advance the position counter for this specific track
    loop_position_counters[track_index] = (loop_position_counters[track_index] + 1) % 14; // 14 columns (0-13)
    
    positions->count = 1;
    positions->points[0].row = (track_id - 1) % 5; // Each track gets its own row (0-4)
    positions->points[0].col = loop_position_counters[track_index]; // Move horizontally across the row
}

// Pitch Mapping 1: Snake down first (r0c0 -> r1c0 -> r2c0...)
static void get_pitch_mapping_1_positions(uint8_t note, position_data_t* positions) {
    uint8_t position_index = note % 70; // Map to 70 positions
    uint8_t col = position_index / 5;    // Which column (0-13)
    uint8_t row = position_index % 5;    // Which row in that column (0-4)
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = col;
}

// Pitch Mapping 2: Snake up from bottom right (r4c13 -> r3c13 -> r2c13...)
static void get_pitch_mapping_2_positions(uint8_t note, position_data_t* positions) {
    uint8_t position_index = note % 70;
    uint8_t col = 13 - (position_index / 5); // Start from rightmost column
    uint8_t row = 4 - (position_index % 5);  // Start from bottom row
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = col;
}

// Pitch Mapping 3: Snake left from top right (r0c13 -> r0c12 -> r0c11...)
static void get_pitch_mapping_3_positions(uint8_t note, position_data_t* positions) {
    uint8_t position_index = note % 70;
    uint8_t row = position_index / 14;       // Which row (0-4, but only goes to 4)
    uint8_t col = 13 - (position_index % 14); // Start from right, go left
    
    if (row >= 5) { // Handle overflow for 70 positions
        row = 4;
        col = 13 - ((position_index - 56) % 14);
    }
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = col;
}

// Pitch Mapping 4: Snake right from bottom left (r4c0 -> r4c1 -> r4c2...)
static void get_pitch_mapping_4_positions(uint8_t note, position_data_t* positions) {
    uint8_t position_index = note % 70;
    uint8_t row = 4 - (position_index / 14);  // Start from bottom row, go up
    uint8_t col = position_index % 14;        // Go left to right
    
    if (row < 0) { // Handle overflow 
        row = 0;
        col = (position_index - 56) % 14;
    }
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = col;
}

// Quadrant dots - singular dots at specified positions
static void get_quadrant_dots_positions(uint8_t track_id, position_data_t* positions) {
    uint8_t dot = (track_id - 1) % 4;
    
    positions->count = 1;
    switch (dot) {
        case 0: // Top left quadrant
            positions->points[0].row = 1;
            positions->points[0].col = 2;
            break;
        case 1: // Top right quadrant
            positions->points[0].row = 1;
            positions->points[0].col = 11;
            break;
        case 2: // Bottom left quadrant
            positions->points[0].row = 3;
            positions->points[0].col = 2;
            break;
        case 3: // Bottom right quadrant
            positions->points[0].row = 3;
            positions->points[0].col = 11;
            break;
    }
}

// Snake positions - tracks that move when keys are pressed
typedef struct {
    uint8_t row;
    uint8_t col;
    bool active;
} snake_position_t;

// Snake positions - follows a predictable zigzag path across the matrix
static uint8_t snake_position_counters[5] = {0}; // Up to 5 snakes (4 tracks + 1 live)

static void get_snake_positions(uint8_t snake_id, uint8_t note, position_data_t* positions) {
    // Advance the snake position counter for this snake
    snake_position_counters[snake_id] = (snake_position_counters[snake_id] + 1) % 70; // 5 rows * 14 cols = 70 positions
    
    uint8_t position_index = snake_position_counters[snake_id];
    uint8_t row = position_index / 14;  // Which row (0-4)
    uint8_t col_in_row = position_index % 14;  // Position within row (0-13)
    
    // Create zigzag pattern: odd rows go right-to-left, even rows go left-to-right
    uint8_t col;
    if (row % 2 == 0) {
        // Even rows (0, 2, 4): left to right
        col = col_in_row;
    } else {
        // Odd rows (1, 3): right to left  
        col = 13 - col_in_row;
    }
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = col;
}

// Center block - random assignment from r1c3 to r3c9
static void get_center_block_positions(uint8_t note, position_data_t* positions) {
    // Center block is rows 1-3, cols 3-9 (3x7 = 21 positions)
    uint8_t position_index = note % 21;
    uint8_t row = 1 + (position_index / 7);  // rows 1-3
    uint8_t col = 3 + (position_index % 7);  // cols 3-9
    
    positions->count = 1;
    positions->points[0].row = row;
    positions->points[0].col = col;
}

// Note close dots 1: r2c3, r2c9, r1c6, r3c6
static void get_note_close_dots_1_positions(uint8_t note, position_data_t* positions) {
    uint8_t dot = note % 4;
    
    positions->count = 1;
    switch (dot) {
        case 0:
            positions->points[0].row = 2;
            positions->points[0].col = 3;
            break;
        case 1:
            positions->points[0].row = 2;
            positions->points[0].col = 9;
            break;
        case 2:
            positions->points[0].row = 1;
            positions->points[0].col = 6;
            break;
        case 3:
            positions->points[0].row = 3;
            positions->points[0].col = 6;
            break;
    }
}

// Note close dots 2: r1c4, r1c8, r3c4, r3c8  
static void get_note_close_dots_2_positions(uint8_t note, position_data_t* positions) {
    uint8_t dot = note % 4;
    
    positions->count = 1;
    switch (dot) {
        case 0:
            positions->points[0].row = 1;
            positions->points[0].col = 4;
            break;
        case 1:
            positions->points[0].row = 1;
            positions->points[0].col = 8;
            break;
        case 2:
            positions->points[0].row = 3;
            positions->points[0].col = 4;
            break;
        case 3:
            positions->points[0].row = 3;
            positions->points[0].col = 8;
            break;
    }
}

static void get_live_positions(uint8_t channel, uint8_t note, live_note_positioning_t positioning, position_data_t* positions) {
    switch (positioning) {
        case LIVE_POS_TRUEKEY:
            get_truekey_positions(note, positions);
            break;
        case LIVE_POS_ZONE:
            get_zone_positions(note, positions);
            break;
        case LIVE_POS_QUADRANT:
            get_live_notes_centers_positions(positions);
            break;
        case LIVE_POS_NOTE_ROW_COL0:
            get_note_row_positions(note, 0, positions);
            break;
        case LIVE_POS_NOTE_ROW_COL13:
            get_note_row_positions(note, 13, positions);
            break;
        case LIVE_POS_NOTE_ROW_COL6:
            get_note_row_positions(note, 6, positions);
            break;
        case LIVE_POS_NOTE_COL_ROW0:
            get_note_col_positions(note, 0, positions);
            break;
        case LIVE_POS_NOTE_COL_ROW4:
            get_note_col_positions(note, 4, positions);
            break;
        case LIVE_POS_NOTE_COL_ROW2:
            get_note_col_positions(note, 2, positions);
            break;
        case LIVE_POS_NOTE_ROW_MIXED:
            get_note_row_mixed_positions(note, positions);
            break;
        case LIVE_POS_NOTE_COL_MIXED:
            get_note_col_mixed_positions(note, positions);
            break;
        
        // Dot positions (single dots only)
        case LIVE_POS_TOP_DOT:
            get_top_dot_positions(positions);
            break;
        case LIVE_POS_LEFT_DOT:
            get_left_dot_positions(positions);
            break;
        case LIVE_POS_RIGHT_DOT:
            get_right_dot_positions(positions);
            break;
        case LIVE_POS_BOTTOM_DOT:
            get_bottom_dot_positions(positions);
            break;
        case LIVE_POS_CENTER_DOT:
            get_center_dot_positions(positions);
            break;
        case LIVE_POS_TOP_LEFT_DOT:
            get_top_left_dot_positions(positions);
            break;
        case LIVE_POS_TOP_RIGHT_DOT:
            get_top_right_dot_positions(positions);
            break;
        case LIVE_POS_BOTTOM_LEFT_DOT:
            get_bottom_left_dot_positions(positions);
            break;
        case LIVE_POS_BOTTOM_RIGHT_DOT:
            get_bottom_right_dot_positions(positions);
            break;
        
        // Note-based dot positions
        case LIVE_POS_NOTE_CORNER_DOTS:
            get_note_corner_dot_positions(note, positions);
            break;
        case LIVE_POS_NOTE_EDGE_DOTS:
            get_note_edge_dot_positions(note, positions);
            break;
        case LIVE_POS_NOTE_ALL_DOTS:
            get_note_all_dot_positions(note, positions);
            break;
                case LIVE_POS_ZONE2:
            get_zone2_positions(note, positions);
            break;
        case LIVE_POS_ZONE3:
            get_zone3_positions(note, positions);
            break;
        case LIVE_POS_COUNT_TO_8:
            get_count_to_8_track_positions(positions);
            break;
        case LIVE_POS_PITCH_MAPPING_1:
            get_pitch_mapping_1_positions(note, positions);
            break;
        case LIVE_POS_PITCH_MAPPING_2:
            get_pitch_mapping_2_positions(note, positions);
            break;
        case LIVE_POS_PITCH_MAPPING_3:
            get_pitch_mapping_3_positions(note, positions);
            break;
        case LIVE_POS_PITCH_MAPPING_4:
            get_pitch_mapping_4_positions(note, positions);
            break;
        case LIVE_POS_SNAKE:
            get_snake_positions(0, note, positions); // Use snake_id 0 for live notes
            break;
        case LIVE_POS_CENTER_BLOCK:
            get_center_block_positions(note, positions);
            break;
        case LIVE_POS_NOTE_CLOSE_DOTS_1:
            get_note_close_dots_1_positions(note, positions);
            break;
        case LIVE_POS_NOTE_CLOSE_DOTS_2:
            get_note_close_dots_2_positions(note, positions);
            break;
			
        default:
            positions->count = 0;
            break;
    }
}

static void get_macro_positions(uint8_t channel, uint8_t note, uint8_t track_id, macro_note_positioning_t positioning, position_data_t* positions) {
    switch (positioning) {
        case MACRO_POS_TRUEKEY:
            get_truekey_positions(note, positions);
            break;
        case MACRO_POS_ZONE:
            get_zone_positions(note, positions);
            break;
        case MACRO_POS_QUADRANT: {
            uint8_t quadrant = ((track_id - 1) % 4) + 1;
            get_quadrant_positions(quadrant, positions);
            break;
        }
        case MACRO_POS_NOTE_ROW_COL0:
            get_note_row_positions(note, 0, positions);
            break;
        case MACRO_POS_NOTE_ROW_COL13:
            get_note_row_positions(note, 13, positions);
            break;
        case MACRO_POS_NOTE_ROW_COL6:
            get_note_row_positions(note, 6, positions);
            break;
        case MACRO_POS_NOTE_COL_ROW0:
            get_note_col_positions(note, 0, positions);
            break;
        case MACRO_POS_NOTE_COL_ROW4:
            get_note_col_positions(note, 4, positions);
            break;
        case MACRO_POS_NOTE_COL_ROW2:
            get_note_col_positions(note, 2, positions);
            break;
        case MACRO_POS_NOTE_ROW_MIXED:
            get_note_row_mixed_positions(note, positions);
            break;
        case MACRO_POS_NOTE_COL_MIXED:
            get_note_col_mixed_positions(note, positions);
            break;
        case MACRO_POS_LOOP_ROW_COL0:
            get_loop_row_positions(track_id, 0, positions);
            break;
        case MACRO_POS_LOOP_ROW_COL13:
            get_loop_row_positions(track_id, 13, positions);
            break;
        case MACRO_POS_LOOP_ROW_COL6:
            get_loop_row_positions(track_id, 6, positions);
            break;
        case MACRO_POS_LOOP_ROW_ALT:
            get_loop_row_alt_positions(track_id, positions);
            break;
        case MACRO_POS_LOOP_COL_ROW0:
            get_loop_col_positions(track_id, 0, positions);
            break;
        case MACRO_POS_LOOP_COL_ROW4:
            get_loop_col_positions(track_id, 4, positions);
            break;
        case MACRO_POS_LOOP_COL_ROW2:
            get_loop_col_positions(track_id, 2, positions);
            break;
        case MACRO_POS_LOOP_BLOCK_3X3:
            get_loop_block_3x3_positions(track_id, positions);
            break;
        case MACRO_POS_LOOP_BLOCK_CENTER:
            get_loop_block_center_positions(track_id, positions);
            break;
        
        // Dot positions (single dots only)
        case MACRO_POS_TOP_DOT:
            get_top_dot_positions(positions);
            break;
        case MACRO_POS_LEFT_DOT:
            get_left_dot_positions(positions);
            break;
        case MACRO_POS_RIGHT_DOT:
            get_right_dot_positions(positions);
            break;
        case MACRO_POS_BOTTOM_DOT:
            get_bottom_dot_positions(positions);
            break;
        case MACRO_POS_CENTER_DOT:
            get_center_dot_positions(positions);
            break;
        case MACRO_POS_TOP_LEFT_DOT:
            get_top_left_dot_positions(positions);
            break;
        case MACRO_POS_TOP_RIGHT_DOT:
            get_top_right_dot_positions(positions);
            break;
        case MACRO_POS_BOTTOM_LEFT_DOT:
            get_bottom_left_dot_positions(positions);
            break;
        case MACRO_POS_BOTTOM_RIGHT_DOT:
            get_bottom_right_dot_positions(positions);
            break;
        
        // Note-based dot positions
        case MACRO_POS_NOTE_CORNER_DOTS:
            get_note_corner_dot_positions(note, positions);
            break;
        case MACRO_POS_NOTE_EDGE_DOTS:
            get_note_edge_dot_positions(note, positions);
            break;
        case MACRO_POS_NOTE_ALL_DOTS:
            get_note_all_dot_positions(note, positions);
            break;        
        case MACRO_POS_LOOP_CORNER_DOTS:
            get_loop_corner_dot_positions(track_id, positions);
            break;
        case MACRO_POS_LOOP_EDGE_DOTS:
            get_loop_edge_dot_positions(track_id, positions);
            break;
                case MACRO_POS_ZONE2:
            get_zone2_positions(note, positions);
            break;
        case MACRO_POS_ZONE3:
            get_zone3_positions(note, positions);
            break;
        case MACRO_POS_COUNT_TO_8:
            get_loop_count_to_8_positions(track_id, positions);
            break;
        case MACRO_POS_LOOP_COUNT_TO_8:
            get_loop_count_to_8_positions(track_id, positions);
            break;
        case MACRO_POS_PITCH_MAPPING_1:
            get_pitch_mapping_1_positions(note, positions);
            break;
        case MACRO_POS_PITCH_MAPPING_2:
            get_pitch_mapping_2_positions(note, positions);
            break;
        case MACRO_POS_PITCH_MAPPING_3:
            get_pitch_mapping_3_positions(note, positions);
            break;
        case MACRO_POS_PITCH_MAPPING_4:
            get_pitch_mapping_4_positions(note, positions);
            break;
        case MACRO_POS_QUADRANT_DOTS:
            get_quadrant_dots_positions(track_id, positions);
            break;
        case MACRO_POS_SNAKE:
            get_snake_positions(track_id, note, positions); // Use track_id as snake_id
            break;
        case MACRO_POS_CENTER_BLOCK:
            get_center_block_positions(note, positions);
            break;
        case MACRO_POS_NOTE_CLOSE_DOTS_1:
            get_note_close_dots_1_positions(note, positions);
            break;
        case MACRO_POS_NOTE_CLOSE_DOTS_2:
            get_note_close_dots_2_positions(note, positions);
            break;
        default:
            positions->count = 0;
            break;
    }
}
// =============================================================================
// BPM BACKGROUND SYSTEM FUNCTIONS (UNCHANGED)
// =============================================================================

static void generate_bpm_disco_colors(void) {
    if (!bpm_colors_generated && bpm_pulse_intensity > 0) {
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                bpm_random_colors[row][col][0] = rand() % 256; // Random hue
                bpm_random_colors[row][col][1] = 200 + (rand() % 56); // Saturation 200-255 for vibrant colors
            }
        }
        bpm_colors_generated = true;
    }
}

static bool calculate_bpm_all_active_area(uint8_t row, uint8_t col) {
    uint8_t pattern_type = bpm_all_beat_count / 4;
    uint8_t beat_in_pattern = bpm_all_beat_count % 4;
    
    if (pattern_type == 0) {
        bool light_top = (beat_in_pattern == 1 || beat_in_pattern == 2);
        bool light_left = (beat_in_pattern == 1 || beat_in_pattern == 0);
        
        uint8_t row_start = light_top ? 0 : 2;
        uint8_t row_end = light_top ? 2 : 4;
        uint8_t col_start = light_left ? 0 : 7;
        uint8_t col_end = light_left ? 6 : 13;
        
        return (row >= row_start && row <= row_end && col >= col_start && col <= col_end);
    } else if (pattern_type == 1) {
        uint8_t row_beat = (beat_in_pattern + 1) % 4;
        if (row_beat == 0) row_beat = 4;
        
        uint8_t row_start, row_end;
        switch (row_beat) {
            case 1: row_start = 0; row_end = 1; break;
            case 2: row_start = 1; row_end = 2; break;
            case 3: row_start = 2; row_end = 3; break;
            case 4: row_start = 3; row_end = 4; break;
            default: row_start = 0; row_end = 1; break;
        }
        
        return (row >= row_start && row <= row_end);
    } else if (pattern_type == 2) {
        uint8_t col_beat = (beat_in_pattern + 1) % 4;
        if (col_beat == 0) col_beat = 4;
        
        uint8_t col_start, col_end;
        switch (col_beat) {
            case 1: col_start = 0; col_end = 3; break;
            case 2: col_start = 4; col_end = 6; break;
            case 3: col_start = 7; col_end = 9; break;
            case 4: col_start = 10; col_end = 13; break;
            default: col_start = 0; col_end = 3; break;
        }
        
        return (col >= col_start && col <= col_end);
    }
    return false;
}

static bool calculate_bpm_quadrants_active_area(uint8_t row, uint8_t col) {
    bool light_top = (bpm_beat_count == 1 || bpm_beat_count == 2);
    bool light_left = (bpm_beat_count == 1 || bpm_beat_count == 0);
    
    uint8_t row_start = light_top ? 0 : 2;
    uint8_t row_end = light_top ? 2 : 4;
    uint8_t col_start = light_left ? 0 : 7;
    uint8_t col_end = light_left ? 6 : 13;
    
    return (row >= row_start && row <= row_end && col >= col_start && col <= col_end);
}

static bool calculate_bpm_row_active_area(uint8_t row, uint8_t col) {
    uint8_t row_start, row_end;
    switch (bpm_beat_count) {
        case 1: row_start = 0; row_end = 1; break;
        case 2: row_start = 1; row_end = 2; break;
        case 3: row_start = 2; row_end = 3; break;
        case 0: row_start = 3; row_end = 4; break;
        default: row_start = 0; row_end = 1; break;
    }
    return (row >= row_start && row <= row_end);
}

static bool calculate_bpm_column_active_area(uint8_t row, uint8_t col) {
    uint8_t col_start, col_end;
    switch (bpm_beat_count) {
        case 1: col_start = 0; col_end = 3; break;
        case 2: col_start = 4; col_end = 6; break;
        case 3: col_start = 7; col_end = 9; break;
        case 0: col_start = 10; col_end = 13; break;
        default: col_start = 0; col_end = 3; break;
    }
    return (col >= col_start && col <= col_end);
}

static void update_bpm_background(background_mode_t background_mode) {
    if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_ALL_9) {
        update_bpm_flash();
        
        if (bpm_flash_state && !last_bpm_flash_state) {
            bpm_pulse_start_time = timer_read32();
            bpm_pulse_intensity = 255;
            bpm_colors_generated = false;
            bpm_all_beat_count = (bpm_all_beat_count + 1) % 12;
        }
        last_bpm_flash_state = bpm_flash_state;
        
        uint8_t pattern_base = 0;
        if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_PULSE_FADE_9) {
            pattern_base = BACKGROUND_BPM_PULSE_FADE;
        } else if (background_mode >= BACKGROUND_BPM_QUADRANTS && background_mode <= BACKGROUND_BPM_QUADRANTS_9) {
            pattern_base = BACKGROUND_BPM_QUADRANTS;
        } else if (background_mode >= BACKGROUND_BPM_ROW && background_mode <= BACKGROUND_BPM_ROW_9) {
            pattern_base = BACKGROUND_BPM_ROW;
        } else if (background_mode >= BACKGROUND_BPM_COLUMN && background_mode <= BACKGROUND_BPM_COLUMN_9) {
            pattern_base = BACKGROUND_BPM_COLUMN;
        } else if (background_mode >= BACKGROUND_BPM_ALL && background_mode <= BACKGROUND_BPM_ALL_9) {
            pattern_base = BACKGROUND_BPM_ALL;
        }
        
        uint8_t variant = background_mode - pattern_base;
        bool is_disco_mode = (variant == 3 || variant == 6 || variant == 9);
        
        if (is_disco_mode) {
            generate_bpm_disco_colors();
        }
        
        if (bpm_pulse_intensity > 0) {
            uint32_t current_time = timer_read32();
            uint32_t elapsed = current_time - bpm_pulse_start_time;
            
            uint32_t pulse_duration = current_bpm > 0 ? (3000000000ULL / current_bpm) : 250;
            
            if (elapsed < pulse_duration) {
                float progress = (float)elapsed / pulse_duration;
                bpm_pulse_intensity = (uint8_t)(255 * (1.0f - progress) * (1.0f - progress));
            } else {
                bpm_pulse_intensity = 0;
            }
        }
    }
}

// Helper function to render autolight with custom parameters
static void render_autolight_with_params(uint8_t brightness_pct, int16_t hue_shift, uint8_t sat_factor) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    uint8_t base_val = rgb_matrix_get_val();
    uint8_t autolight_brightness = (base_val * brightness_pct) / 100;
    
    uint8_t user_hue = rgb_matrix_get_hue();
    uint8_t user_sat = rgb_matrix_get_sat();
    
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        HSV hsv = {(user_hue + hue_shift) % 256, (user_sat * sat_factor) / 255, autolight_brightness};
        RGB rgb = hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    
    for (uint8_t i = 0; i < led_categories[current_layer].count; i++) {
        uint8_t led_index = led_categories[current_layer].leds[i].led_index;
        uint8_t category = led_categories[current_layer].leds[i].category;
        
        if (category < 29 && led_index < RGB_MATRIX_LED_COUNT) {
            uint8_t category_hue_offset = (category * 255) / 29;
            
            uint8_t final_hue = (user_hue + hue_shift + category_hue_offset) % 256;
            uint8_t final_sat = (user_sat * sat_factor) / 255;
            uint8_t final_brightness = autolight_brightness;
            
            if ((keysplitstatus != 0) || (keysplittransposestatus != 0) || (keysplitvelocitystatus != 0)) {
                if (category == 2) {
                    final_hue = 170;
                    final_sat = 255;
                }
            }
            
            if ((keysplitstatus == 2) || (keysplitstatus == 3) || (keysplittransposestatus == 2) || (keysplittransposestatus == 3) || (keysplitvelocitystatus == 2) || (keysplitvelocitystatus == 3)) {
                if (category == 1) {
                    final_hue = 85;
                    final_sat = 255;
                }
            }
            
            HSV color_hsv = {final_hue, final_sat, final_brightness};
            RGB final_color = hsv_to_rgb(color_hsv);
            rgb_matrix_set_color(led_index, final_color.r, final_color.g, final_color.b);
        }
    }
}

static void render_bpm_background(background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    
    if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_ALL_9) {
        uint8_t pattern_base = 0;
        bool (*active_area_func)(uint8_t, uint8_t) = NULL;
        
        if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_PULSE_FADE_9) {
            pattern_base = BACKGROUND_BPM_PULSE_FADE;
            active_area_func = NULL;
        } else if (background_mode >= BACKGROUND_BPM_QUADRANTS && background_mode <= BACKGROUND_BPM_QUADRANTS_9) {
            pattern_base = BACKGROUND_BPM_QUADRANTS;
            active_area_func = calculate_bpm_quadrants_active_area;
        } else if (background_mode >= BACKGROUND_BPM_ROW && background_mode <= BACKGROUND_BPM_ROW_9) {
            pattern_base = BACKGROUND_BPM_ROW;
            active_area_func = calculate_bpm_row_active_area;
        } else if (background_mode >= BACKGROUND_BPM_COLUMN && background_mode <= BACKGROUND_BPM_COLUMN_9) {
            pattern_base = BACKGROUND_BPM_COLUMN;
            active_area_func = calculate_bpm_column_active_area;
        } else if (background_mode >= BACKGROUND_BPM_ALL && background_mode <= BACKGROUND_BPM_ALL_9) {
            pattern_base = BACKGROUND_BPM_ALL;
            active_area_func = calculate_bpm_all_active_area;
        }
        
        uint8_t variant = background_mode - pattern_base;
        
        if (variant >= 4 && variant <= 6) {
            uint8_t static_hue = base_hue;
            if (variant == 5) {
                static_hue = (base_hue + 128) % 256;
            }
            
            uint8_t static_brightness = (base_val * background_brightness_pct) / 200;
            
            for (uint8_t row = 0; row < 5; row++) {
                for (uint8_t col = 0; col < 14; col++) {
                    uint8_t led[LED_HITS_TO_REMEMBER];
                    uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
                    if (led_count > 0) {
                        HSV hsv = {static_hue, base_sat, static_brightness};
                        RGB rgb = hsv_to_rgb(hsv);
                        rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                    }
                }
            }
        } else if (variant >= 7 && variant <= 9) {
            int16_t autolight_hue_shift = 0;
            if (variant == 8) {
                autolight_hue_shift = 128;
            } else if (variant == 9) {
                autolight_hue_shift = 64;
            }
            
            render_autolight_with_params(background_brightness_pct / 2, autolight_hue_shift, 255);
        }
        
        uint8_t pulse_hue = base_hue;
        uint8_t pulse_sat = base_sat;
        bool is_disco = false;
        
        switch (variant) {
            case 0: break;
            case 1: pulse_hue = (base_hue + 128) % 256; break;
            case 2: pulse_sat = base_sat / 2; break;
            case 3: is_disco = true; break;
            case 4: pulse_hue = (base_hue + 128) % 256; break;
            case 5: break;
            case 6: is_disco = true; break;
            case 7: pulse_hue = (base_hue + 128) % 256; break;
            case 8: break;
            case 9: is_disco = true; break;
        }
        
        if (bpm_pulse_intensity > 0) {
            uint8_t max_pulse_brightness = (base_val * background_brightness_pct) / 100;
            uint8_t min_pulse_brightness = max_pulse_brightness / 2;
            
            uint8_t brightness_factor;
            if (variant >= 4) {
                brightness_factor = min_pulse_brightness + ((max_pulse_brightness - min_pulse_brightness) * bpm_pulse_intensity) / 255;
            } else {
                brightness_factor = (max_pulse_brightness * bpm_pulse_intensity) / 255;
            }
            
            for (uint8_t row = 0; row < 5; row++) {
                for (uint8_t col = 0; col < 14; col++) {
                    uint8_t led[LED_HITS_TO_REMEMBER];
                    uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
                    if (led_count > 0) {
                        bool in_active_area = true;
                        
                        if (active_area_func != NULL) {
                            in_active_area = active_area_func(row, col);
                        }
                        
                        if (in_active_area && bpm_pulse_intensity > 0) {
                            if (is_disco) {
                                uint8_t disco_hue = bpm_random_colors[row][col][0];
                                uint8_t disco_sat = bpm_random_colors[row][col][1];
                                HSV hsv = {disco_hue, disco_sat, brightness_factor};
                                RGB rgb = hsv_to_rgb(hsv);
                                rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                            } else {
                                HSV hsv = {pulse_hue, pulse_sat, brightness_factor};
                                RGB rgb = hsv_to_rgb(hsv);
                                rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                            }
                        } else if (variant < 4) {
                            rgb_matrix_set_color(led[0], 0, 0, 0);
                        }
                    }
                }
            }
        } else {
            if (variant < 4) {
                for (uint8_t row = 0; row < 5; row++) {
                    for (uint8_t col = 0; col < 14; col++) {
                        uint8_t led[LED_HITS_TO_REMEMBER];
                        uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
                        if (led_count > 0) {
                            rgb_matrix_set_color(led[0], 0, 0, 0);
                        }
                    }
                }
            }
        }
    }
}

static void apply_backlight(uint8_t brightness_pct, background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    uint8_t backlight_val = (base_val * background_brightness_pct) / 100;
    
    uint8_t static_hue = base_hue;
    uint8_t static_sat = base_sat;
    
    // Handle original static backgrounds
    if (background_mode >= BACKGROUND_STATIC && background_mode <= BACKGROUND_STATIC_HUE3) {
        uint8_t variant = background_mode - BACKGROUND_STATIC;
        
        switch (variant) {
            case 1: static_hue = (base_hue + 64) % 256; break;
            case 2: static_hue = (base_hue + 128) % 256; break;
            case 3: static_hue = (base_hue + 192) % 256; break;
        }
    }
    // Handle desaturated static backgrounds
    else if (background_mode >= BACKGROUND_STATIC_DESAT && background_mode <= BACKGROUND_STATIC_HUE3_DESAT) {
        uint8_t variant = background_mode - BACKGROUND_STATIC_DESAT;
        
        switch (variant) {
            case 0: break; // basic desat
            case 1: static_hue = (base_hue + 64) % 256; break;
            case 2: static_hue = (base_hue + 128) % 256; break;
            case 3: static_hue = (base_hue + 192) % 256; break;
        }
        // Apply desaturation
        static_sat = static_sat > 80 ? static_sat - 80 : 0;
    }
    
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                HSV hsv = {static_hue, static_sat, backlight_val};
                RGB rgb = hsv_to_rgb(hsv);
                rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
            }
        }
    }
}

static void render_autolight_background(background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    uint8_t base_val = rgb_matrix_get_val();
    uint8_t autolight_brightness = (base_val * background_brightness_pct) / 100;
    
    uint8_t user_hue = rgb_matrix_get_hue();
    uint8_t user_sat = rgb_matrix_get_sat();
    
    int16_t hue_shift = 0;
    bool is_desaturated = false;
    bool is_hue_cycle = false;
    bool is_breathing = false;
    
    // Handle original autolight backgrounds
    if (background_mode >= BACKGROUND_AUTOLIGHT && background_mode <= BACKGROUND_AUTOLIGHT_HUE1) {
        uint8_t variant = background_mode - BACKGROUND_AUTOLIGHT;
        
        switch (variant) {
            case 1: hue_shift = 64; break;  // HUE1
        }
    }
    // Handle new hue cycle and breathing backgrounds (replacing HUE2 and HUE3)
    else if (background_mode == BACKGROUND_AUTOLIGHT_HUE2) {
        is_hue_cycle = true;
    }
    else if (background_mode == BACKGROUND_AUTOLIGHT_HUE3) {
        is_breathing = true;
    }
    // Handle desaturated autolight backgrounds
    else if (background_mode >= BACKGROUND_AUTOLIGHT_DESAT && background_mode <= BACKGROUND_AUTOLIGHT_HUE1_DESAT) {
        uint8_t variant = background_mode - BACKGROUND_AUTOLIGHT_DESAT;
        is_desaturated = true;
        
        switch (variant) {
            case 0: break; // basic desat
            case 1: hue_shift = 64; break;  // HUE1_DESAT
        }
    }
    // Handle new desaturated hue cycle and breathing backgrounds
    else if (background_mode == BACKGROUND_AUTOLIGHT_HUE2_DESAT) {
        is_hue_cycle = true;
        is_desaturated = true;
    }
    else if (background_mode == BACKGROUND_AUTOLIGHT_HUE3_DESAT) {
        is_breathing = true;
        is_desaturated = true;
    }
    
    // Calculate time-based effects
    uint16_t time = scale16by8(g_rgb_timer, rgb_matrix_config.speed / 4);
    uint8_t time_hue_offset = 0;
    uint8_t breathing_brightness_factor = 255;
    
    if (is_hue_cycle) {
        time_hue_offset = time;  // Cycle through all hues over time
    }
    
    if (is_breathing) {
        breathing_brightness_factor = scale8(abs8(sin8(time) - 128) * 2, 255);
    }
    
    // Set base color for all LEDs
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        uint8_t final_sat = user_sat;
        if (is_desaturated) {
            final_sat = final_sat > 80 ? final_sat - 80 : 0;
        }
        
        uint8_t final_brightness = autolight_brightness;
        if (is_breathing) {
            final_brightness = scale8(final_brightness, breathing_brightness_factor);
        }
        
        HSV hsv = {(user_hue + hue_shift + time_hue_offset) % 256, final_sat, final_brightness};
        RGB rgb = hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    
    // Apply category-specific colors
    for (uint8_t i = 0; i < led_categories[current_layer].count; i++) {
        uint8_t led_index = led_categories[current_layer].leds[i].led_index;
        uint8_t category = led_categories[current_layer].leds[i].category;
        
        if (category < 29 && led_index < RGB_MATRIX_LED_COUNT) {
            uint8_t category_hue_offset = (category * 255) / 29;
            
            uint8_t final_hue = (user_hue + hue_shift + time_hue_offset + category_hue_offset) % 256;
            uint8_t final_sat = user_sat;
            if (is_desaturated) {
                final_sat = final_sat > 80 ? final_sat - 80 : 0;
            }
            
            uint8_t final_brightness = autolight_brightness;
            if (is_breathing) {
                final_brightness = scale8(final_brightness, breathing_brightness_factor);
            }
            
            // Handle key split special cases
            if ((keysplitstatus != 0) || (keysplittransposestatus != 0) || (keysplitvelocitystatus != 0)) {
                if (category == 2) {
                    final_hue = (170 + time_hue_offset) % 256;  // Apply time offset to split colors too
                    final_sat = 255;
                    if (is_desaturated) {
                        final_sat = 175;
                    }
                }
            }
            
            if ((keysplitstatus == 2) || (keysplitstatus == 3) || (keysplittransposestatus == 2) || (keysplittransposestatus == 3) || (keysplitvelocitystatus == 2) || (keysplitvelocitystatus == 3)) {
                if (category == 1) {
                    final_hue = (85 + time_hue_offset) % 256;   // Apply time offset to split colors too
                    final_sat = 255;
                    if (is_desaturated) {
                        final_sat = 175;
                    }
                }
            }
            
            HSV color_hsv = {final_hue, final_sat, final_brightness};
            RGB final_color = hsv_to_rgb(color_hsv);
            rgb_matrix_set_color(led_index, final_color.r, final_color.g, final_color.b);
        }
    }
}
static bool is_static_background(background_mode_t background_mode) {
    return ((background_mode >= BACKGROUND_STATIC && background_mode <= BACKGROUND_STATIC_HUE3) ||
            (background_mode >= BACKGROUND_STATIC_DESAT && background_mode <= BACKGROUND_STATIC_HUE3_DESAT));
}

static bool is_autolight_background(background_mode_t background_mode) {
    return ((background_mode >= BACKGROUND_AUTOLIGHT && background_mode <= BACKGROUND_AUTOLIGHT_HUE3) ||
            (background_mode >= BACKGROUND_AUTOLIGHT_DESAT && background_mode <= BACKGROUND_AUTOLIGHT_HUE3_DESAT));
}

// Math function implementations - add these right after the registry struct
static HSV cycle_all_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h = time;
    return hsv;
}

static HSV cycle_left_right_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h = g_led_config.point[i].x - time;
    return hsv;
}

static HSV cycle_up_down_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h = g_led_config.point[i].y - time;
    return hsv;
}

static HSV cycle_out_in_math_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    uint8_t dist = sqrt16(dx * dx + dy * dy);
    hsv.h = 3 * dist + time;
    return hsv;
}

static HSV cycle_out_in_math_desat_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    uint8_t dist = sqrt16(dx * dx + dy * dy);
    hsv.h = 3 * dist + time;
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV cycle_out_in_dual_math_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    dx = (k_rgb_matrix_center.x / 2) - abs8(dx);
    uint8_t dist = sqrt16(dx * dx + dy * dy);
    hsv.h = 3 * dist + time;
    return hsv;
}

static HSV rainbow_pinwheel_math_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    hsv.h = atan2_8(dy, dx) + time;
    return hsv;
}

static HSV breathing_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.v = scale8(abs8(sin8(time) - 128) * 2, hsv.v);
    return hsv;
}

static HSV wave_left_right_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.v = scale8(abs8(sin8(g_led_config.point[i].x + time) - 128) * 2, hsv.v);
    return hsv;
}

static HSV diagonal_wave_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + g_led_config.point[i].y;
    hsv.v = scale8(abs8(sin8(pos + time) - 128) * 2, hsv.v);
    return hsv;
}

// Additional math function implementations - add after existing ones
static HSV gradient_up_down_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    // FIXED: Direct hue setting for smooth cycling
    hsv.h = (g_led_config.point[i].y * 4) + time;  // Smooth position-based hue + time cycling
    return hsv;
}

static HSV gradient_left_right_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    // FIXED: Direct hue setting for smooth cycling
    hsv.h = (g_led_config.point[i].x * 2) + time;  // Smooth position-based hue + time cycling
    return hsv;
}

static HSV hue_breathing_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t huedelta = 12;
    hsv.h = hsv.h + scale8(abs8(sin8(time) - 128) * 2, huedelta);
    return hsv;
}

static HSV hue_pendulum_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t huedelta = 12;
    hsv.h = hsv.h + scale8(abs8(sin8(time) + (g_led_config.point[i].x) - 128) * 2, huedelta);
    return hsv;
}

static HSV hue_wave_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t huedelta = 24;
    hsv.h = hsv.h + scale8(abs8(g_led_config.point[i].x - time), huedelta);
    return hsv;
}

static HSV rainbow_moving_chevron_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h += abs8(g_led_config.point[i].y - k_rgb_matrix_center.y) + (g_led_config.point[i].x - time);
    return hsv;
}

static HSV band_pinwheel_sat_math_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    hsv.s = scale8(hsv.s - time - atan2_8(dy, dx) * 3, hsv.s);
    return hsv;
}

static HSV band_pinwheel_val_math_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    hsv.v = scale8(hsv.v - time - atan2_8(dy, dx) * 3, hsv.v);
    return hsv;
}

static HSV band_spiral_sat_math_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint8_t time) {
    hsv.s = scale8(hsv.s + dist - time - atan2_8(dy, dx), hsv.s);
    return hsv;
}

static HSV band_spiral_val_math_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint8_t time) {
    hsv.v = scale8(hsv.v + dist - time - atan2_8(dy, dx), hsv.v);
    return hsv;
}

static HSV gradient_diagonal_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t diagonal_pos = (g_led_config.point[i].x + g_led_config.point[i].y) / 2;
    // FIXED: Direct hue setting for smooth cycling
    hsv.h = (diagonal_pos * 4) + time;  // Smooth diagonal position-based hue + time cycling
    return hsv;
}

// Desaturated versions of all math functions - add after existing math functions
static HSV cycle_all_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h = time;
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV cycle_left_right_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h = g_led_config.point[i].x - time;
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV cycle_up_down_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h = g_led_config.point[i].y - time;
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV cycle_out_in_dual_math_desat_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    dx = (k_rgb_matrix_center.x / 2) - abs8(dx);
    uint8_t dist = sqrt16(dx * dx + dy * dy);
    hsv.h = 3 * dist + time;
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV rainbow_pinwheel_math_desat_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    hsv.h = atan2_8(dy, dx) + time;
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV breathing_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.v = scale8(abs8(sin8(time) - 128) * 2, hsv.v);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV wave_left_right_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.v = scale8(abs8(sin8(g_led_config.point[i].x + time) - 128) * 2, hsv.v);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV diagonal_wave_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + g_led_config.point[i].y;
    hsv.v = scale8(abs8(sin8(pos + time) - 128) * 2, hsv.v);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV gradient_up_down_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h = (g_led_config.point[i].y * 4) + time;  // FIXED: Smooth cycling
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV gradient_left_right_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h = (g_led_config.point[i].x * 2) + time;  // FIXED: Smooth cycling
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV gradient_diagonal_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t diagonal_pos = (g_led_config.point[i].x + g_led_config.point[i].y) / 2;
    hsv.h = (diagonal_pos * 4) + time;  // FIXED: Smooth cycling
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV hue_breathing_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t huedelta = 12;
    hsv.h = hsv.h + scale8(abs8(sin8(time) - 128) * 2, huedelta);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV hue_pendulum_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t huedelta = 12;
    hsv.h = hsv.h + scale8(abs8(sin8(time) + (g_led_config.point[i].x) - 128) * 2, huedelta);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV hue_wave_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t huedelta = 24;
    hsv.h = hsv.h + scale8(abs8(g_led_config.point[i].x - time), huedelta);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV rainbow_moving_chevron_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    hsv.h += abs8(g_led_config.point[i].y - k_rgb_matrix_center.y) + (g_led_config.point[i].x - time);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV band_pinwheel_sat_math_desat_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    hsv.s = scale8(hsv.s - time - atan2_8(dy, dx) * 3, hsv.s);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV band_pinwheel_val_math_desat_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t time) {
    hsv.v = scale8(hsv.v - time - atan2_8(dy, dx) * 3, hsv.v);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV band_spiral_sat_math_desat_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint8_t time) {
    hsv.s = scale8(hsv.s + dist - time - atan2_8(dy, dx), hsv.s);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV band_spiral_val_math_desat_impl(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint8_t time) {
    hsv.v = scale8(hsv.v + dist - time - atan2_8(dy, dx), hsv.v);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

// Add these math implementation functions after the existing diagonal_wave_math_impl function

// NEW DIAGONAL WAVE VARIATIONS - Regular versions
static HSV diagonal_wave_hue_cycle_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + g_led_config.point[i].y;
    hsv.v = scale8(abs8(sin8(pos + time) - 128) * 2, hsv.v);
    // FIXED: Direct hue setting like cycle_out_in, smooth continuous cycling
    hsv.h = pos * 2 + time;  // Smooth cycling independent of base hue
    return hsv;
}

static HSV diagonal_wave_dual_color_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + g_led_config.point[i].y;
    hsv.v = scale8(abs8(sin8(pos + time) - 128) * 2, hsv.v);
    // Use dual colors - original hue or +64 shift based on wave position
    if (sin8(pos + time) > 128) {
        hsv.h = hsv.h + 64;  // +64 hue shift for second color
    }
    return hsv;
}

static HSV diagonal_wave_dual_color_hue_cycle_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + g_led_config.point[i].y;
    hsv.v = scale8(abs8(sin8(pos + time) - 128) * 2, hsv.v);
    // FIXED: Smooth base hue cycling with dual color offset
    uint8_t base_hue = pos + time;  // Smooth base cycling
    if (sin8(pos + time) > 128) {
        hsv.h = base_hue + 64;  // +64 hue shift for second color
    } else {
        hsv.h = base_hue;
    }
    return hsv;
}

// REVERSE DIAGONAL WAVE VARIATIONS
static HSV diagonal_wave_reverse_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + (255 - g_led_config.point[i].y);
    hsv.v = scale8(abs8(sin8(pos - time) - 128) * 2, hsv.v);  // Note: pos - time for reverse
    return hsv;
}

static HSV diagonal_wave_reverse_hue_cycle_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + (255 - g_led_config.point[i].y);
    hsv.v = scale8(abs8(sin8(pos - time) - 128) * 2, hsv.v);
    // FIXED: Smooth reverse cycling
    hsv.h = pos * 2 - time;  // Reverse direction, smooth cycling
    return hsv;
}

static HSV diagonal_wave_reverse_dual_color_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + (255 - g_led_config.point[i].y);
    hsv.v = scale8(abs8(sin8(pos - time) - 128) * 2, hsv.v);
    // Use dual colors - original hue or +64 shift based on wave position (reverse)
    if (sin8(pos - time) > 128) {
        hsv.h = hsv.h + 64;  // +64 hue shift for second color
    }
    return hsv;
}

static HSV diagonal_wave_reverse_dual_color_hue_cycle_math_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + (255 - g_led_config.point[i].y);
    hsv.v = scale8(abs8(sin8(pos - time) - 128) * 2, hsv.v);
    // FIXED: Smooth reverse base hue cycling with dual colors
    uint8_t base_hue = pos - time;  // Smooth reverse cycling
    if (sin8(pos - time) > 128) {
        hsv.h = base_hue + 64;  // +64 hue shift for second color
    } else {
        hsv.h = base_hue;
    }
    return hsv;
}

// DESATURATED VERSIONS OF ALL DIAGONAL WAVES
static HSV diagonal_wave_hue_cycle_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + g_led_config.point[i].y;
    hsv.v = scale8(abs8(sin8(pos + time) - 128) * 2, hsv.v);
    hsv.h = pos * 2 + time;  // FIXED: Smooth cycling
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV diagonal_wave_dual_color_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + g_led_config.point[i].y;
    hsv.v = scale8(abs8(sin8(pos + time) - 128) * 2, hsv.v);
    if (sin8(pos + time) > 128) {
        hsv.h = hsv.h + 64;
    }
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV diagonal_wave_dual_color_hue_cycle_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + g_led_config.point[i].y;
    hsv.v = scale8(abs8(sin8(pos + time) - 128) * 2, hsv.v);
    uint8_t base_hue = pos + time;  // FIXED: Smooth base cycling
    if (sin8(pos + time) > 128) {
        hsv.h = base_hue + 64;
    } else {
        hsv.h = base_hue;
    }
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV diagonal_wave_reverse_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + (255 - g_led_config.point[i].y);
    hsv.v = scale8(abs8(sin8(pos - time) - 128) * 2, hsv.v);
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV diagonal_wave_reverse_hue_cycle_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + (255 - g_led_config.point[i].y);
    hsv.v = scale8(abs8(sin8(pos - time) - 128) * 2, hsv.v);
    hsv.h = pos * 2 - time;  // FIXED: Smooth reverse cycling
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV diagonal_wave_reverse_dual_color_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + (255 - g_led_config.point[i].y);
    hsv.v = scale8(abs8(sin8(pos - time) - 128) * 2, hsv.v);
    if (sin8(pos - time) > 128) {
        hsv.h = hsv.h + 64;
    }
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

static HSV diagonal_wave_reverse_dual_color_hue_cycle_math_desat_impl(HSV hsv, uint8_t i, uint8_t time) {
    uint8_t pos = g_led_config.point[i].x + (255 - g_led_config.point[i].y);
    hsv.v = scale8(abs8(sin8(pos - time) - 128) * 2, hsv.v);
    uint8_t base_hue = pos - time;  // FIXED: Smooth reverse cycling
    if (sin8(pos - time) > 128) {
        hsv.h = base_hue + 64;
    } else {
        hsv.h = base_hue;
    }
    hsv.s = hsv.s > 80 ? hsv.s - 80 : 0;
    return hsv;
}

// Add these entries to your math_backgrounds array after the existing 20 entries
// Update num_math_backgrounds from 20 to 27

static math_background_t math_backgrounds[MAX_MATH_BACKGROUNDS] = {
    // ... existing 20 entries ...
    {"Cycle All", BG_TYPE_SIMPLE, .simple_func = cycle_all_math_impl, 1, true},
    {"Cycle Left Right", BG_TYPE_SIMPLE, .simple_func = cycle_left_right_math_impl, 1, true},
    {"Cycle Up Down", BG_TYPE_SIMPLE, .simple_func = cycle_up_down_math_impl, 1, true},
    {"Cycle Out In", BG_TYPE_DX_DY, .dx_dy_func = cycle_out_in_math_impl, 1, true},
    {"Cycle Out In Dual", BG_TYPE_DX_DY, .dx_dy_func = cycle_out_in_dual_math_impl, 1, true},
    {"Rainbow Pinwheel", BG_TYPE_DX_DY, .dx_dy_func = rainbow_pinwheel_math_impl, 1, true},
    {"Breathing", BG_TYPE_SIMPLE, .simple_func = breathing_math_impl, 1, true},
    {"Wave Left Right", BG_TYPE_SIMPLE, .simple_func = wave_left_right_math_impl, 1, true},
    {"Diagonal Wave", BG_TYPE_SIMPLE, .simple_func = diagonal_wave_math_impl, 1, true},
    {"Gradient Up Down", BG_TYPE_SIMPLE, .simple_func = gradient_up_down_math_impl, 1, true},
    {"Gradient Left Right", BG_TYPE_SIMPLE, .simple_func = gradient_left_right_math_impl, 1, true},
    {"Gradient Diagonal", BG_TYPE_SIMPLE, .simple_func = gradient_diagonal_math_impl, 1, true},
    {"Hue Breathing", BG_TYPE_SIMPLE, .simple_func = hue_breathing_math_impl, 1, true},
    {"Hue Pendulum", BG_TYPE_SIMPLE, .simple_func = hue_pendulum_math_impl, 1, true},
    {"Hue Wave", BG_TYPE_SIMPLE, .simple_func = hue_wave_math_impl, 1, true},
    {"Rainbow Moving Chevron", BG_TYPE_SIMPLE, .simple_func = rainbow_moving_chevron_math_impl, 1, true},
    {"Band Pinwheel Sat", BG_TYPE_DX_DY, .dx_dy_func = band_pinwheel_sat_math_impl, 1, true},
    {"Band Pinwheel Val", BG_TYPE_DX_DY, .dx_dy_func = band_pinwheel_val_math_impl, 1, true},
    {"Band Spiral Sat", BG_TYPE_DIST, .dist_func = band_spiral_sat_math_impl, 1, true},
    {"Band Spiral Val", BG_TYPE_DIST, .dist_func = band_spiral_val_math_impl, 1, true},
    {"Diagonal Wave Hue Cycle", BG_TYPE_SIMPLE, .simple_func = diagonal_wave_hue_cycle_math_impl, 1, true},
    {"Diagonal Wave Dual Color", BG_TYPE_SIMPLE, .simple_func = diagonal_wave_dual_color_math_impl, 1, true},
    {"Diagonal Wave Dual Hue Cycle", BG_TYPE_SIMPLE, .simple_func = diagonal_wave_dual_color_hue_cycle_math_impl, 1, true},
    {"Diagonal Wave Reverse", BG_TYPE_SIMPLE, .simple_func = diagonal_wave_reverse_math_impl, 1, true},
    {"Diagonal Wave Reverse Hue Cycle", BG_TYPE_SIMPLE, .simple_func = diagonal_wave_reverse_hue_cycle_math_impl, 1, true},
    {"Diagonal Wave Reverse Dual Color", BG_TYPE_SIMPLE, .simple_func = diagonal_wave_reverse_dual_color_math_impl, 1, true},
    {"Diagonal Wave Reverse Dual Hue Cycle", BG_TYPE_SIMPLE, .simple_func = diagonal_wave_reverse_dual_color_hue_cycle_math_impl, 1, true},
};

// Update this line:
static uint8_t num_math_backgrounds = 27;  // Changed from 20 to 27

static void run_background_math_i(background_math_func_t math_func, uint8_t time, uint8_t brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    uint8_t background_val = (base_val * brightness_pct) / 100;
    
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        HSV hsv = {base_hue, base_sat, background_val};
        hsv = math_func(hsv, i, time);
        RGB rgb = hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
}

static void run_background_math_dx_dy(background_math_dx_dy_func_t math_func, uint8_t time, uint8_t brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    uint8_t background_val = (base_val * brightness_pct) / 100;
    
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        HSV hsv = {base_hue, base_sat, background_val};
        int16_t dx = g_led_config.point[i].x - k_rgb_matrix_center.x;
        int16_t dy = g_led_config.point[i].y - k_rgb_matrix_center.y;
        hsv = math_func(hsv, dx, dy, time);
        RGB rgb = hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
}

static void run_background_math_dist(background_math_dist_func_t math_func, uint8_t time, uint8_t brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    uint8_t background_val = (base_val * brightness_pct) / 100;
    
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        HSV hsv = {base_hue, base_sat, background_val};
        int16_t dx = g_led_config.point[i].x - k_rgb_matrix_center.x;
        int16_t dy = g_led_config.point[i].y - k_rgb_matrix_center.y;
        uint8_t dist = sqrt16(dx * dx + dy * dy);
        hsv = math_func(hsv, dx, dy, dist, time);
        RGB rgb = hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
}

// Update your render_math_background_by_index function or add this mapping logic
// This handles the new diagonal wave background indices (107-113) that need to map 
// to math_backgrounds array indices (20-26)

static void render_math_background_by_index(uint8_t bg_index, uint8_t background_brightness_pct) {
    uint8_t math_array_index;
    
    // Map background_mode_t indices to math_backgrounds array indices
    if (bg_index >= BACKGROUND_CYCLE_ALL && bg_index <= BACKGROUND_BAND_SPIRAL_VAL) {
        // Original math backgrounds (59-78 -> array indices 0-19)
        math_array_index = bg_index - BACKGROUND_CYCLE_ALL;
    } else if (bg_index >= BACKGROUND_DIAGONAL_WAVE_HUE_CYCLE && bg_index <= BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR_HUE_CYCLE) {
        // New diagonal wave backgrounds (107-113 -> array indices 20-26)
        math_array_index = bg_index - BACKGROUND_DIAGONAL_WAVE_HUE_CYCLE + 20;
    } else {
        return; // Invalid index
    }
    
    if (math_array_index >= num_math_backgrounds || !math_backgrounds[math_array_index].enabled) {
        return;
    }
    
    // Use RGB matrix speed scaling like the original effects
    uint16_t time = scale16by8(g_rgb_timer, rgb_matrix_config.speed / 4);
    
    math_background_t* bg = &math_backgrounds[math_array_index];
    uint8_t effective_time = time;
    
    if (bg->speed_multiplier == 0) {
        effective_time /= 2;
    } else {
        effective_time *= bg->speed_multiplier;
    }
    
    switch (bg->type) {
        case BG_TYPE_SIMPLE:
            run_background_math_i(bg->simple_func, effective_time, background_brightness_pct);
            break;
        case BG_TYPE_DX_DY:
            run_background_math_dx_dy(bg->dx_dy_func, effective_time, background_brightness_pct);
            break;
        case BG_TYPE_DIST:
            run_background_math_dist(bg->dist_func, effective_time, background_brightness_pct);
            break;
    }
}

static void render_math_background_desaturated(background_mode_t background_mode, uint8_t background_brightness_pct) {
    // Use RGB matrix speed scaling like the original effects
    uint16_t time = scale16by8(g_rgb_timer, rgb_matrix_config.speed / 4);
    uint8_t effective_time = time;
    
    // Map the desaturated background to its corresponding function
// Map the desaturated background to its corresponding function
    switch (background_mode) {
        case BACKGROUND_CYCLE_ALL_DESAT:
            run_background_math_i(cycle_all_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_CYCLE_LEFT_RIGHT_DESAT:
            run_background_math_i(cycle_left_right_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_CYCLE_UP_DOWN_DESAT:
            run_background_math_i(cycle_up_down_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_CYCLE_OUT_IN_DESAT:
			run_background_math_dx_dy(cycle_out_in_math_desat_impl, effective_time, background_brightness_pct);
        case BACKGROUND_CYCLE_OUT_IN_DUAL_DESAT:
            run_background_math_dx_dy(cycle_out_in_dual_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_RAINBOW_PINWHEEL_DESAT:
            run_background_math_dx_dy(rainbow_pinwheel_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_BREATHING_DESAT:
            run_background_math_i(breathing_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_WAVE_LEFT_RIGHT_DESAT:
            run_background_math_i(wave_left_right_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_DIAGONAL_WAVE_DESAT:
            run_background_math_i(diagonal_wave_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_GRADIENT_UP_DOWN_DESAT:
            run_background_math_i(gradient_up_down_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_GRADIENT_LEFT_RIGHT_DESAT:
            run_background_math_i(gradient_left_right_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_GRADIENT_DIAGONAL_DESAT:
            run_background_math_i(gradient_diagonal_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_HUE_BREATHING_DESAT:
            run_background_math_i(hue_breathing_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_HUE_PENDULUM_DESAT:
            run_background_math_i(hue_pendulum_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_HUE_WAVE_DESAT:
            run_background_math_i(hue_wave_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_RAINBOW_MOVING_CHEVRON_DESAT:
            run_background_math_i(rainbow_moving_chevron_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_BAND_PINWHEEL_SAT_DESAT:
            run_background_math_dx_dy(band_pinwheel_sat_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_BAND_PINWHEEL_VAL_DESAT:
            run_background_math_dx_dy(band_pinwheel_val_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_BAND_SPIRAL_SAT_DESAT:
            run_background_math_dist(band_spiral_sat_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_BAND_SPIRAL_VAL_DESAT:
            run_background_math_dist(band_spiral_val_math_desat_impl, effective_time, background_brightness_pct);
            break;
		case BACKGROUND_DIAGONAL_WAVE_HUE_CYCLE_DESAT:
            run_background_math_i(diagonal_wave_hue_cycle_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_DIAGONAL_WAVE_DUAL_COLOR_DESAT:
            run_background_math_i(diagonal_wave_dual_color_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_DIAGONAL_WAVE_DUAL_COLOR_HUE_CYCLE_DESAT:
            run_background_math_i(diagonal_wave_dual_color_hue_cycle_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_DIAGONAL_WAVE_REVERSE_DESAT:
            run_background_math_i(diagonal_wave_reverse_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_DIAGONAL_WAVE_REVERSE_HUE_CYCLE_DESAT:
            run_background_math_i(diagonal_wave_reverse_hue_cycle_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR_DESAT:
            run_background_math_i(diagonal_wave_reverse_dual_color_math_desat_impl, effective_time, background_brightness_pct);
            break;
        case BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR_HUE_CYCLE_DESAT:
            run_background_math_i(diagonal_wave_reverse_dual_color_hue_cycle_math_desat_impl, effective_time, background_brightness_pct);
            break;
        default:
            // Do nothing for non-desaturated backgrounds - they're handled elsewhere
            break;
    }
}// =============================================================================

// EFFICIENT ANIMATION MATH FUNCTIONS - COMPLETE SET WITH NORMALIZED TIMING
// =============================================================================

// =============================================================================
// TIMING STANDARDS:
// - DOT/LINE EFFECTS: /80.0f base (fast, sharp movements)
// - RIPPLE EFFECTS: /120.0f base (medium-fast, expanding rings) 
// - BURST EFFECTS: /150.0f base (medium speed, area fills)
// - VOLUME EFFECTS: /200.0f base (slow, smooth bars)
// - FADE EFFECTS: fade_time approach (static fades)
// =============================================================================

// Speed formula explanation:
// (min_multiplier + (speed / 255.0f) * range)
// - To increase MAX speed: increase 'range' value
// - To increase SLOWEST speed: increase 'min_multiplier' value  
// - To increase DISPARITY: increase 'range' and/or decrease 'min_multiplier'

// Fade time formula explanation:
// base_time - ((speed * reduction_amount) / 255)
// - To increase MAX speed: increase 'reduction_amount'
// - To increase SLOWEST speed: decrease 'base_time'
// - To increase DISPARITY: increase 'reduction_amount' and/or increase 'base_time'

// =============================================================================
// BASIC FADE ANIMATIONS
// =============================================================================

static uint8_t none_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Only light the exact triggered position
    if (led_row != note_row || led_col != note_col) return 0;
    
    // Speed: 2000ms to 200ms (10x difference)
    uint16_t fade_time = 2000 - ((speed * 1800) / 255);
    if (elapsed_time >= fade_time) return 0;
    
    return 255 - ((elapsed_time * 255) / fade_time);
}

static uint8_t none_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return none_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t wide1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early rejection - only check LEDs within 1 step
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 1 || col_diff > 1) return 0;
    
    // Speed calculation
    uint16_t fade_time = 2400 - ((speed * 2100) / 255);
    if (elapsed_time >= fade_time) return 0;
    
    uint8_t base_brightness = 255 - ((elapsed_time * 255) / fade_time);
    
    // Center LED - full brightness
    if (row_diff == 0 && col_diff == 0) {
        return base_brightness;
    }
    
    // Adjacent LEDs - 60% brightness
    return (base_brightness * 60) / 100;
}

static uint8_t wide1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return wide1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t wide2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early rejection - only check LEDs within 2 steps
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 2 || col_diff > 2) return 0;
    
    // Speed calculation
    uint16_t fade_time = 2400 - ((speed * 2100) / 255);
    if (elapsed_time >= fade_time) return 0;
    
    uint8_t base_brightness = 255 - ((elapsed_time * 255) / fade_time);
    
    // Center LED - full brightness
    if (row_diff == 0 && col_diff == 0) {
        return base_brightness;
    }
    
    // First ring - 60% brightness
    if (row_diff <= 1 && col_diff <= 1) {
        return (base_brightness * 60) / 100;
    }
    
    // Second ring - 30% brightness  
    return (base_brightness * 30) / 100;
}

static uint8_t wide2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return wide2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}


static uint8_t column_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0; // Same column only
    
    int8_t distance = abs(led_row - note_row);
    if (distance > 2) return 0; // 2 LEDs above and below
    
    // Speed: 4000ms to 500ms (8x difference)
    uint16_t fade_time = 4000 - ((speed * 3500) / 255);
    if (elapsed_time >= fade_time) return 0;
    
    uint8_t brightness_reduction = distance * 60; // Fade based on distance
    uint8_t base_brightness = 255 - ((elapsed_time * 255) / fade_time);
    return base_brightness > brightness_reduction ? base_brightness - brightness_reduction : 0;
}

static uint8_t column_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return column_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t row_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    int8_t distance = abs(led_col - note_col);
    if (distance > 2) return 0; // 2 LEDs left and right
    
    // Speed: 4000ms to 500ms (8x difference)
    uint16_t fade_time = 4000 - ((speed * 3500) / 255);
    if (elapsed_time >= fade_time) return 0;
    
    uint8_t brightness_reduction = distance * 60; // Fade based on distance
    uint8_t base_brightness = 255 - ((elapsed_time * 255) / fade_time);
    return base_brightness > brightness_reduction ? base_brightness - brightness_reduction : 0;
}

static uint8_t row_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return row_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t cross_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    int8_t row_distance = abs(led_row - note_row);
    int8_t col_distance = abs(led_col - note_col);
    
    // Only orthogonal directions (cross shape)
    if (!((row_distance <= 2 && col_distance == 0) || (col_distance <= 2 && row_distance == 0))) return 0;
    
    // Speed: 4000ms to 500ms (8x difference)
    uint16_t fade_time = 4000 - ((speed * 3500) / 255);
    if (elapsed_time >= fade_time) return 0;
    
    uint8_t distance = (row_distance > col_distance) ? row_distance : col_distance;
    uint8_t brightness_reduction = distance * 60;
    uint8_t base_brightness = 255 - ((elapsed_time * 255) / fade_time);
    return base_brightness > brightness_reduction ? base_brightness - brightness_reduction : 0;
}

static uint8_t cross_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return cross_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t cross_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    int8_t row_diff = led_row - note_row;
    int8_t col_diff = led_col - note_col;
    
    // Only diagonal directions (X shape)
    if (!(abs(row_diff) == abs(col_diff) && abs(row_diff) <= 2)) return 0;
    
    // Speed: 4000ms to 500ms (8x difference)
    uint16_t fade_time = 4000 - ((speed * 3500) / 255);
    if (elapsed_time >= fade_time) return 0;
    
    uint8_t distance = abs(row_diff);
    uint8_t brightness_reduction = distance * 60;
    uint8_t base_brightness = 255 - ((elapsed_time * 255) / fade_time);
    return base_brightness > brightness_reduction ? base_brightness - brightness_reduction : 0;
}

static uint8_t cross_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return cross_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// DOT/LINE MOVEMENT ANIMATIONS (Standardized to /80.0f base)
// =============================================================================

static uint8_t moving_dots_row_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Horizontal line expanding left and right like ripple
    if (led_row != note_row) return 0;
    
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 7.0f) return 0;
    
    float horizontal_distance = fabs((float)(led_col - note_col));
    float line_thickness = 0.8f;
    
    if (horizontal_distance >= radius - line_thickness && horizontal_distance <= radius + line_thickness) {
        float brightness_factor = 1.0f - (radius / 7.0f);
        return (uint8_t)(255 * brightness_factor);
    }
    
    return 0;
}

static uint8_t moving_dots_row_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_row_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_col_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Vertical line expanding up and down like ripple
    if (led_col != note_col) return 0;
    
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 3.0f) return 0;
    
    float vertical_distance = fabs((float)(led_row - note_row));
    float line_thickness = 0.8f;
    
    if (vertical_distance >= radius - line_thickness && vertical_distance <= radius + line_thickness) {
        float brightness_factor = 1.0f - (radius / 3.0f);
        return (uint8_t)(255 * brightness_factor);
    }
    
    return 0;
}

static uint8_t moving_dots_col_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_col_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_row_no_fade_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0;
    
    // DOT STANDARD: /80.0f base timing (this was the reference speed)
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 15.0f) return 0;
    
    float horizontal_distance = fabs((float)(led_col - note_col));
    float line_thickness = 0.8f;
    
    if (horizontal_distance >= radius - line_thickness && horizontal_distance <= radius + line_thickness) {
        return 255; // No brightness fadeout - always full brightness
    }
    
    return 0;
}

static uint8_t moving_dots_row_no_fade_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_row_no_fade_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_col_no_fade_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0;
    
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 5.0f) return 0;
    
    float vertical_distance = fabs((float)(led_row - note_row));
    float line_thickness = 0.8f;
    
    if (vertical_distance >= radius - line_thickness && vertical_distance <= radius + line_thickness) {
        return 255; // No brightness fadeout - always full brightness
    }
    
    return 0;
}

static uint8_t moving_dots_col_no_fade_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_col_no_fade_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// DIAGONAL DOTS
static uint8_t moving_dots_diag_tl_br_no_fade_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 6.0f) return 0;
    
    int8_t row_diff = led_row - note_row;
    int8_t col_diff = led_col - note_col;
    
    if (row_diff != col_diff) return 0;
    
    float diagonal_distance = fabs((float)row_diff);
    float line_thickness = 0.8f;
    
    if (diagonal_distance >= radius - line_thickness && diagonal_distance <= radius + line_thickness) {
        return 255; // No fade
    }
    return 0;
}

static uint8_t moving_dots_diag_tl_br_no_fade_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_diag_tl_br_no_fade_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_diag_tr_bl_no_fade_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 6.0f) return 0;
    
    int8_t row_diff = led_row - note_row;
    int8_t col_diff = led_col - note_col;
    
    if (row_diff != -col_diff) return 0;
    
    float diagonal_distance = fabs((float)row_diff);
    float line_thickness = 0.8f;
    
    if (diagonal_distance >= radius - line_thickness && diagonal_distance <= radius + line_thickness) {
        return 255; // No fade
    }
    return 0;
}

static uint8_t moving_dots_diag_tr_bl_no_fade_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_diag_tr_bl_no_fade_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// ALL ORTHOGONAL (combines horizontal and vertical)
static uint8_t moving_dots_all_orthogonal_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 7.0f) return 0;
    
    float line_thickness = 0.8f;
    float brightness_factor = 1.0f - (radius / 7.0f);
    
    // Check horizontal line (left/right)
    if (led_row == note_row) {
        float horizontal_distance = fabs((float)(led_col - note_col));
        if (horizontal_distance >= radius - line_thickness && horizontal_distance <= radius + line_thickness) {
            return (uint8_t)(255 * brightness_factor);
        }
    }
    
    // Check vertical line (up/down)
    if (led_col == note_col) {
        float vertical_distance = fabs((float)(led_row - note_row));
        if (vertical_distance >= radius - line_thickness && vertical_distance <= radius + line_thickness) {
            return (uint8_t)(255 * brightness_factor);
        }
    }
    
    return 0;
}

static uint8_t moving_dots_all_orthogonal_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_all_orthogonal_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_all_orthogonal_no_fade_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 15.0f) return 0;
    
    float line_thickness = 0.8f;
    
    // Check horizontal line (left/right)
    if (led_row == note_row) {
        float horizontal_distance = fabs((float)(led_col - note_col));
        if (horizontal_distance >= radius - line_thickness && horizontal_distance <= radius + line_thickness) {
            return 255; // No fade
        }
    }
    
    // Check vertical line (up/down)
    if (led_col == note_col) {
        float vertical_distance = fabs((float)(led_row - note_row));
        if (vertical_distance >= radius - line_thickness && vertical_distance <= radius + line_thickness) {
            return 255; // No fade
        }
    }
    
    return 0;
}

static uint8_t moving_dots_all_orthogonal_no_fade_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_all_orthogonal_no_fade_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// ALL DIAGONAL
static uint8_t moving_dots_all_diagonal_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 6.0f) return 0;
    
    int8_t row_diff = led_row - note_row;
    int8_t col_diff = led_col - note_col;
    float line_thickness = 0.8f;
    float brightness_factor = 1.0f - (radius / 6.0f);
    
    // Check TL-BR diagonal (row_diff == col_diff)
    if (abs(row_diff - col_diff) <= 1) {
        float diagonal_distance = fabs((float)row_diff);
        if (diagonal_distance >= radius - line_thickness && diagonal_distance <= radius + line_thickness) {
            return (uint8_t)(255 * brightness_factor);
        }
    }
    
    // Check TR-BL diagonal (row_diff == -col_diff)
    if (abs(row_diff + col_diff) <= 1) {
        float diagonal_distance = fabs((float)row_diff);
        if (diagonal_distance >= radius - line_thickness && diagonal_distance <= radius + line_thickness) {
            return (uint8_t)(255 * brightness_factor);
        }
    }
    
    return 0;
}

static uint8_t moving_dots_all_diagonal_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_all_diagonal_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_all_diagonal_no_fade_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // DOT STANDARD: /80.0f base timing
    float radius = (elapsed_time / 80.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    if (radius > 6.0f) return 0;
    
    int8_t row_diff = led_row - note_row;
    int8_t col_diff = led_col - note_col;
    float line_thickness = 0.8f;
    
    // Check TL-BR diagonal (row_diff == col_diff)
    if (row_diff == col_diff) {
        float diagonal_distance = fabs((float)row_diff);
        if (diagonal_distance >= radius - line_thickness && diagonal_distance <= radius + line_thickness) {
            return 255; // No fade
        }
    }
    
    // Check TR-BL diagonal (row_diff == -col_diff)
    if (row_diff == -col_diff) {
        float diagonal_distance = fabs((float)row_diff);
        if (diagonal_distance >= radius - line_thickness && diagonal_distance <= radius + line_thickness) {
            return 255; // No fade
        }
    }
    
    return 0;
}

static uint8_t moving_dots_all_diagonal_no_fade_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_all_diagonal_no_fade_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// REVERSE DOT ANIMATIONS (Current 25% speed is now max speed)
// =============================================================================

static uint8_t moving_dots_row_1_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0;
    
    // 3.33x slower: multiply denominator by ~3.33 (267/80 ≈ 3.33) + remove delay (use full speed range)
    float time_factor = (elapsed_time / 267.0f) * (0.25f + (speed / 255.0f) * 1.75f); // Full speed range, no delay
    if (time_factor > 1.0f) return 0;
    
    float max_radius = 4.0f;
    float radius = max_radius - (time_factor * max_radius);
    if (radius < 0) return 0;
    
    float horizontal_distance = fabs((float)(led_col - note_col));
    float line_thickness = 0.8f;
    float brightness_factor = 1.0f - (radius / 3.0f);
    if (horizontal_distance >= radius - line_thickness && horizontal_distance <= radius + line_thickness) {
        return (uint8_t)(255 * brightness_factor);
    }
    
    return 0;
}

static uint8_t moving_dots_row_1_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_row_1_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_row_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0;
    
    // REVERSE DOT STANDARD: Much slower - current 25% speed is now max speed
    float time_factor = (elapsed_time / 80.0f) * (0.1f + (speed / 255.0f) * 0.6f);
    if (time_factor > 1.0f) return 0;
    
    float max_radius = 7.0f;
    float radius = max_radius - (time_factor * max_radius);
    if (radius < 0) return 0;
    
    float horizontal_distance = fabs((float)(led_col - note_col));
    float line_thickness = 0.8f;
    
    if (horizontal_distance >= radius - line_thickness && horizontal_distance <= radius + line_thickness) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_dots_row_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_row_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_col_1_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0;
    
    // REVERSE DOT STANDARD: Much slower - current 25% speed is now max speed
    float time_factor = (elapsed_time / 80.0f) * (0.1f + (speed / 255.0f) * 0.6f);
    if (time_factor > 1.0f) return 0;
    
    float max_radius = 3.0f;
    float radius = max_radius - (time_factor * max_radius);
    if (radius < 0) return 0;
    
    float vertical_distance = fabs((float)(led_row - note_row));
    float line_thickness = 0.8f;
    
    if (vertical_distance >= radius - line_thickness && vertical_distance <= radius + line_thickness) {
        float brightness_factor = 1.0f - (radius / 3.0f);
        return (uint8_t)(255 * brightness_factor);
    }
    
    return 0;
}

static uint8_t moving_dots_col_1_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_col_1_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_col_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0;
    
    // REVERSE DOT STANDARD: Much slower - current 25% speed is now max speed
    float time_factor = (elapsed_time / 80.0f) * (0.1f + (speed / 255.0f) * 0.6f);
    if (time_factor > 1.0f) return 0;
    
    float max_radius = 3.0f;
    float radius = max_radius - (time_factor * max_radius);
    if (radius < 0) return 0;
    
    float vertical_distance = fabs((float)(led_row - note_row));
    float line_thickness = 0.8f;
    
    if (vertical_distance >= radius - line_thickness && vertical_distance <= radius + line_thickness) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_dots_col_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_col_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_all_orthogonal_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // 2x faster: divide denominator by 2 (160/320 = 0.5)
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 160;
    if (time_factor > 256) return 0;
    
    // Brightness fades over time (30% fade like other reverse functions)
    uint8_t brightness_factor = 255 - ((time_factor * 77) / 256);
    
    // Check horizontal line (contracting)
    if (led_row == note_row) {
        uint8_t max_radius = 7;
        uint8_t radius = (max_radius * (256 - time_factor)) / 256; // Contract from max to 0
        
        uint8_t horizontal_distance = abs(led_col - note_col);
        // Line thickness of ~0.8 converted to integer: allow exact match or +/-1
        if (horizontal_distance == radius) {
            return brightness_factor;
        }
    }
    
    // Check vertical line (contracting)
    if (led_col == note_col) {
        uint8_t max_radius = 3;
        uint8_t radius = (max_radius * (256 - time_factor)) / 256; // Contract from max to 0
        
        uint8_t vertical_distance = abs(led_row - note_row);
        // Line thickness of ~0.8 converted to integer: allow exact match or +/-1
        if (vertical_distance == radius) {
            return brightness_factor;
        }
    }
    
    return 0;
}

static uint8_t moving_dots_all_orthogonal_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_all_orthogonal_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_dots_all_orthogonal_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // REVERSE DOT STANDARD: Much slower - current 25% speed is now max speed
    float time_factor = (elapsed_time / 80.0f) * (0.1f + (speed / 255.0f) * 0.6f);
    if (time_factor > 1.0f) return 0;
    
    float line_thickness = 0.8f;
    
    // Check horizontal line (contracting)
    if (led_row == note_row) {
        float max_radius = 7.0f;
        float radius = max_radius - (time_factor * max_radius);
        if (radius >= 0) {
            float horizontal_distance = fabs((float)(led_col - note_col));
            if (horizontal_distance >= radius - line_thickness && horizontal_distance <= radius + line_thickness) {
                return 255;
            }
        }
    }
    
    // Check vertical line (contracting)
    if (led_col == note_col) {
        float max_radius = 3.0f;
        float radius = max_radius - (time_factor * max_radius);
        if (radius >= 0) {
            float vertical_distance = fabs((float)(led_row - note_row));
            if (vertical_distance >= radius - line_thickness && vertical_distance <= radius + line_thickness) {
                return 255;
            }
        }
    }
    
    return 0;
}

static uint8_t moving_dots_all_orthogonal_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_dots_all_orthogonal_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// OPTIMIZED 3-PIXEL ORTHOGONAL ANIMATIONS
// =============================================================================

static uint8_t moving_all_orthogonal_3_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // 6.67x slower: multiply denominator by ~6.67 (533/80 ≈ 6.67)
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 533;
    uint8_t radius_h = (radius_factor * 7) / 256;
    uint8_t radius_v = (radius_factor * 3) / 256;
    
    if (radius_h > 7 && radius_v > 3) return 0;
    
    uint8_t brightness_factor = 255 - ((radius_h * 255) / 7);
    
    // Check horizontal (3-pixel columns) - early culling
    uint8_t row_diff = abs(led_row - note_row);
    if (row_diff <= 1) {
        uint8_t horizontal_distance = abs(led_col - note_col);
        if (horizontal_distance == radius_h) {
            return brightness_factor;
        }
    }
    
    // Check vertical (3-pixel rows) - early culling
    uint8_t col_diff = abs(led_col - note_col);
    if (col_diff <= 1) {
        uint8_t vertical_distance = abs(led_row - note_row);
        if (vertical_distance == radius_v) {
            return brightness_factor;
        }
    }
    
    return 0;
}

static uint8_t moving_all_orthogonal_3_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_all_orthogonal_3_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_all_orthogonal_3_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Convert to integer math - max radius is 15 for horizontal, 5 for vertical
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 533;
    uint8_t radius_h = (radius_factor * 15) / 256;
    uint8_t radius_v = (radius_factor * 5) / 256;
    
    if (radius_h > 15 && radius_v > 5) return 0;
    
    // Check horizontal (3-pixel columns) - early culling
    uint8_t row_diff = abs(led_row - note_row);
    if (row_diff <= 1) {
        uint8_t horizontal_distance = abs(led_col - note_col);
        if (horizontal_distance == radius_h) {
            return 255;
        }
    }
    
    // Check vertical (3-pixel rows) - early culling
    uint8_t col_diff = abs(led_col - note_col);
    if (col_diff <= 1) {
        uint8_t vertical_distance = abs(led_row - note_row);
        if (vertical_distance == radius_v) {
            return 255;
        }
    }
    
    return 0;
}

static uint8_t moving_all_orthogonal_3_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_all_orthogonal_3_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// OPTIMIZED 3-PIXEL REVERSE ORTHOGONAL ANIMATIONS
// =============================================================================

static uint8_t moving_all_orthogonal_3_1_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Convert to integer math - reverse timing
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 80;
    if (time_factor > 256) return 0;
    
    // Check horizontal (3-pixel columns contracting)
    uint8_t row_diff = abs(led_row - note_row);
    if (row_diff <= 1) {
        uint8_t max_radius = 7;
        uint8_t radius = (max_radius * (256 - time_factor)) / 256;
        if (radius > 0) {
            uint8_t horizontal_distance = abs(led_col - note_col);
            if (horizontal_distance == radius) {
                uint8_t brightness_factor = 255 - ((time_factor * 77) / 256); // 30% fade
                return brightness_factor;
            }
        }
    }
    
    // Check vertical (3-pixel rows contracting)
    uint8_t col_diff = abs(led_col - note_col);
    if (col_diff <= 1) {
        uint8_t max_radius = 3;
        uint8_t radius = (max_radius * (256 - time_factor)) / 256;
        if (radius > 0) {
            uint8_t vertical_distance = abs(led_row - note_row);
            if (vertical_distance == radius) {
                uint8_t brightness_factor = 255 - ((time_factor * 77) / 256); // 30% fade
                return brightness_factor;
            }
        }
    }
    
    return 0;
}

static uint8_t moving_all_orthogonal_3_1_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_all_orthogonal_3_1_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_all_orthogonal_3_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Convert to integer math - reverse timing
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 80;
    if (time_factor > 256) return 0;
    
    // Check horizontal (3-pixel columns contracting)
    uint8_t row_diff = abs(led_row - note_row);
    if (row_diff <= 1) {
        uint8_t max_radius = 7;
        uint8_t radius = (max_radius * (256 - time_factor)) / 256;
        if (radius > 0) {
            uint8_t horizontal_distance = abs(led_col - note_col);
            if (horizontal_distance == radius) {
                return 255;
            }
        }
    }
    
    // Check vertical (3-pixel rows contracting)
    uint8_t col_diff = abs(led_col - note_col);
    if (col_diff <= 1) {
        uint8_t max_radius = 3;
        uint8_t radius = (max_radius * (256 - time_factor)) / 256;
        if (radius > 0) {
            uint8_t vertical_distance = abs(led_row - note_row);
            if (vertical_distance == radius) {
                return 255;
            }
        }
    }
    
    return 0;
}

static uint8_t moving_all_orthogonal_3_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_all_orthogonal_3_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// OPTIMIZED 8-PIXEL ORTHOGONAL ANIMATIONS
// =============================================================================

static uint8_t moving_all_orthogonal_8_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // 6.67x slower: multiply denominator by ~6.67 (533/80 ≈ 6.67)
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 533;
    uint8_t radius_h = (radius_factor * 7) / 256;
    uint8_t radius_v = (radius_factor * 3) / 256;
    
    if (radius_h > 7 && radius_v > 3) return 0;
    
    uint8_t brightness_factor = 255 - ((radius_h * 255) / 7);
    
    // Check horizontal (full-height columns) - no row restriction
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius_h) {
        return brightness_factor;
    }
    
    // Check vertical (full-width rows) - no column restriction  
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius_v) {
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_all_orthogonal_8_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_all_orthogonal_8_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_all_orthogonal_8_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Convert to integer math - max radius is 15 for horizontal, 5 for vertical
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 533;
    uint8_t radius_h = (radius_factor * 15) / 256;
    uint8_t radius_v = (radius_factor * 5) / 256;
    
    if (radius_h > 15 && radius_v > 5) return 0;
    
    // Check horizontal (full-height columns) - no row restriction
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius_h) {
        return 255;
    }
    
    // Check vertical (full-width rows) - no column restriction
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius_v) {
        return 255;
    }
    
    return 0;
}

static uint8_t moving_all_orthogonal_8_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_all_orthogonal_8_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// OPTIMIZED 8-PIXEL REVERSE ORTHOGONAL ANIMATIONS
// =============================================================================

static uint8_t moving_all_orthogonal_8_1_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Convert to integer math - reverse timing
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 80;
    if (time_factor > 256) return 0;
    
    // Check horizontal (full-height columns contracting)
    uint8_t max_radius_h = 7;
    uint8_t radius_h = (max_radius_h * (256 - time_factor)) / 256;
    if (radius_h > 0) {
        uint8_t horizontal_distance = abs(led_col - note_col);
        if (horizontal_distance == radius_h) {
            uint8_t brightness_factor = 255 - ((time_factor * 77) / 256); // 30% fade
            return brightness_factor;
        }
    }
    
    // Check vertical (full-width rows contracting)
    uint8_t max_radius_v = 3;
    uint8_t radius_v = (max_radius_v * (256 - time_factor)) / 256;
    if (radius_v > 0) {
        uint8_t vertical_distance = abs(led_row - note_row);
        if (vertical_distance == radius_v) {
            uint8_t brightness_factor = 255 - ((time_factor * 77) / 256); // 30% fade
            return brightness_factor;
        }
    }
    
    return 0;
}

static uint8_t moving_all_orthogonal_8_1_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_all_orthogonal_8_1_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_all_orthogonal_8_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Convert to integer math - reverse timing
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 80;
    if (time_factor > 256) return 0;
    
    // Check horizontal (full-height columns contracting)
    uint8_t max_radius_h = 7;
    uint8_t radius_h = (max_radius_h * (256 - time_factor)) / 256;
    if (radius_h > 0) {
        uint8_t horizontal_distance = abs(led_col - note_col);
        if (horizontal_distance == radius_h) {
            return 255;
        }
    }
    
    // Check vertical (full-width rows contracting)
    uint8_t max_radius_v = 3;
    uint8_t radius_v = (max_radius_v * (256 - time_factor)) / 256;
    if (radius_v > 0) {
        uint8_t vertical_distance = abs(led_row - note_row);
        if (vertical_distance == radius_v) {
            return 255;
        }
    }
    
    return 0;
}

static uint8_t moving_all_orthogonal_8_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_all_orthogonal_8_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// OPTIMIZED 3-PIXEL COLUMN ANIMATIONS
// =============================================================================

static uint8_t moving_columns_3_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early culling - only 3 pixels tall (note_row ± 1)
    if (abs(led_row - note_row) > 1) return 0;
    
    // 6.67x slower: multiply denominator by ~6.67 (533/80 ≈ 6.67)
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 533;
    uint8_t radius = (radius_factor * 7) / 256;
    if (radius > 7) return 0;
    
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 7);
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_columns_3_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_columns_3_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_columns_3_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early culling - only 3 pixels tall (note_row ± 1)
    if (abs(led_row - note_row) > 1) return 0;
    
    // Convert to integer math - max radius is 15
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 533;
    uint8_t radius = (radius_factor * 15) / 256;
    if (radius > 15) return 0;
    
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_columns_3_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_columns_3_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_columns_3_1_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early culling - only 3 pixels tall (note_row ± 1)
    if (abs(led_row - note_row) > 1) return 0;
    
    // COLLAPSING COLUMNS: Half speed - convert to integer math
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 160;
    if (time_factor > 256) return 0;
    
    uint8_t max_radius = 7;
    uint8_t radius = (max_radius * (256 - time_factor)) / 256;
    if (radius == 0) return 0;
    
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 7);
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_columns_3_1_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_columns_3_1_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_columns_3_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early culling - only 3 pixels tall (note_row ± 1)
    if (abs(led_row - note_row) > 1) return 0;
    
    // COLLAPSING COLUMNS: Half speed - convert to integer math
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 160;
    if (time_factor > 256) return 0;
    
    uint8_t max_radius = 7;
    uint8_t radius = (max_radius * (256 - time_factor)) / 256;
    if (radius == 0) return 0;
    
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_columns_3_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_columns_3_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// OPTIMIZED 3-PIXEL ROW ANIMATIONS  
// =============================================================================

static uint8_t moving_rows_3_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early culling - only 3 pixels wide (note_col ± 1)
    if (abs(led_col - note_col) > 1) return 0;
    
    // 4x slower: multiply denominator by 4 (320/80 = 4)
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 320;
    uint8_t radius = (radius_factor * 3) / 256;
    if (radius > 3) return 0;
    
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 3);
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_rows_3_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_rows_3_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_rows_3_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early culling - only 3 pixels wide (note_col ± 1)
    if (abs(led_col - note_col) > 1) return 0;
    
    // Convert to integer math - max radius is 5
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 320;
    uint8_t radius = (radius_factor * 5) / 256;
    if (radius > 5) return 0;
    
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_rows_3_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_rows_3_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_rows_3_1_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early culling - only 3 pixels wide (note_col ± 1)
    if (abs(led_col - note_col) > 1) return 0;
    
    // 2x slower: multiply denominator by 2 (160/80 = 2)
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 160;
    if (time_factor > 256) return 0;
    
    uint8_t max_radius = 3;
    uint8_t radius = (max_radius * (256 - time_factor)) / 256;
    if (radius == 0) return 0;
    
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 3);
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_rows_3_1_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_rows_3_1_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_rows_3_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early culling - only 3 pixels wide (note_col ± 1)
    if (abs(led_col - note_col) > 1) return 0;
    
    // COLLAPSING ROWS MEDIUM: Convert to integer math
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 80;
    if (time_factor > 256) return 0;
    
    uint8_t max_radius = 3;
    uint8_t radius = (max_radius * (256 - time_factor)) / 256;
    if (radius == 0) return 0;
    
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_rows_3_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_rows_3_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// OPTIMIZED 8-PIXEL COLUMN ANIMATIONS
// =============================================================================

// MOVING_COLUMNS_8_1 - 15% speed → 100% speed (6.67x faster)
static uint8_t moving_columns_8_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // 6.67x slower: multiply denominator by ~6.67 (533/80 ≈ 6.67)
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 533;
    uint8_t radius = (radius_factor * 7) / 256;
    if (radius > 7) return 0;
    
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 7);
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_columns_8_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_columns_8_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_columns_8_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Convert to integer math - max radius is 15 (full height columns)
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 533;
    uint8_t radius = (radius_factor * 15) / 256;
    if (radius > 15) return 0;
    
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_columns_8_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_columns_8_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_columns_8_1_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // COLLAPSING COLUMNS: Half speed - convert to integer math
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 160;
    if (time_factor > 256) return 0;
    
    uint8_t max_radius = 7;
    uint8_t radius = (max_radius * (256 - time_factor)) / 256;
    if (radius == 0) return 0;
    
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 7);
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_columns_8_1_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_columns_8_1_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_columns_8_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // COLLAPSING COLUMNS: Half speed - convert to integer math
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 160;
    if (time_factor > 256) return 0;
    
    uint8_t max_radius = 7;
    uint8_t radius = (max_radius * (256 - time_factor)) / 256;
    if (radius == 0) return 0;
    
    uint8_t horizontal_distance = abs(led_col - note_col);
    if (horizontal_distance == radius) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_columns_8_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_columns_8_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// OPTIMIZED 8-PIXEL ROW ANIMATIONS
// =============================================================================

static uint8_t moving_rows_8_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // 2x slower: multiply denominator by 2 (160/80 = 2)
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 160;
    uint8_t radius = (radius_factor * 3) / 256;
    if (radius > 3) return 0;
    
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 3);
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_rows_8_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_rows_8_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_rows_8_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Convert to integer math - max radius is 5 (full width rows)
    uint16_t radius_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 160;
    uint8_t radius = (radius_factor * 5) / 256;
    if (radius > 5) return 0;
    
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_rows_8_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_rows_8_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_rows_8_1_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // 2x slower: multiply denominator by 2 (160/80 = 2)
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 160;
    if (time_factor > 256) return 0;
    
    uint8_t max_radius = 3;
    uint8_t radius = (max_radius * (256 - time_factor)) / 256;
    if (radius == 0) return 0;
    
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 3);
        return brightness_factor;
    }
    
    return 0;
}

static uint8_t moving_rows_8_1_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_rows_8_1_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t moving_rows_8_2_reverse_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // COLLAPSING ROWS: Same speed as medium - convert to integer math
    uint16_t time_factor = (elapsed_time * (26 + (speed * 154) / 255)) / 80;
    if (time_factor > 256) return 0;
    
    uint8_t max_radius = 3;
    uint8_t radius = (max_radius * (256 - time_factor)) / 256;
    if (radius == 0) return 0;
    
    uint8_t vertical_distance = abs(led_row - note_row);
    if (vertical_distance == radius) {
        return 255; // No fade
    }
    
    return 0;
}

static uint8_t moving_rows_8_2_reverse_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return moving_rows_8_2_reverse_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}
// =============================================================================
// RIPPLE ANIMATIONS (Standardized to /120.0f base)
// =============================================================================

static uint8_t ripple_small_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 3
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 3 || col_diff > 3) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    // RIPPLE STANDARD: /120.0f base timing converted to integer
    uint16_t time_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 120;
    uint8_t radius = time_factor / 256; // Convert back to radius scale
    if (radius > 3) return 0; // Small radius limit
    
    // Ring thickness check (converted to integer)
    if (distance >= radius && distance <= radius + 1) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 3);
        return brightness_factor;
    }
    return 0;
}

static uint8_t ripple_small_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return ripple_small_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t ripple_med_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 5
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 5 || col_diff > 5) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 120;
    uint8_t radius = time_factor / 256;
    if (radius > 5) return 0; // Medium radius limit
    
    if (distance >= radius && distance <= radius + 1) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 5);
        return brightness_factor;
    }
    return 0;
}

static uint8_t ripple_med_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return ripple_med_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t ripple_large_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 10
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 10 || col_diff > 10) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 120;
    uint8_t radius = time_factor / 256;
    if (radius > 10) return 0; // Large radius limit
    
    if (distance >= radius && distance <= radius + 1) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 8);
        return brightness_factor;
    }
    return 0;
}

static uint8_t ripple_large_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return ripple_large_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t ripple_massive_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 15
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 15 || col_diff > 15) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (64 + (speed * 448) / 255)) / 120;
    uint8_t radius = time_factor / 256;
    if (radius > 15) return 0; // Massive radius limit
    
    if (distance >= radius && distance <= radius + 2) { // Thicker ring
        uint8_t brightness_factor = 255 - ((radius * 255) / 12);
        return brightness_factor;
    }
    return 0;
}

static uint8_t ripple_massive_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return ripple_massive_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// RIPPLE_2 ANIMATIONS - Contracting/Reverse
static uint8_t outward_burst_reverse_small_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 2
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 2 || col_diff > 2) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    // Convert to integer math - only contracting phase
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 120;
    if (time_factor > 256) return 0; // Stop after contraction complete
    
    // Start at max radius and shrink: radius goes from 2 to 0
    uint8_t radius = ((256 - time_factor) * 2) / 256;
    
    if (distance <= radius && radius > 0) {
        // Add intensity falloff like outward_burst
        uint8_t intensity = 255 - ((distance * 255) / (radius + 1));
        return (intensity * intensity) / 255; // Square for falloff
    }
    return 0;
}

static uint8_t outward_burst_reverse_small_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return outward_burst_reverse_small_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t outward_burst_reverse_med_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 4
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 4 || col_diff > 4) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 120;
    if (time_factor > 256) return 0;
    
    // Start at radius 4 and shrink to 0
    uint8_t radius = ((256 - time_factor) * 4) / 256;
    
    if (distance <= radius && radius > 0) {
        // Add intensity falloff like outward_burst
        uint8_t intensity = 255 - ((distance * 255) / (radius + 1));
        return (intensity * intensity) / 255; // Square for falloff
    }
    return 0;
}

static uint8_t outward_burst_reverse_med_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return outward_burst_reverse_med_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t outward_burst_reverse_large_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 6
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 6 || col_diff > 6) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 120;
    if (time_factor > 256) return 0;
    
    // Start at radius 6 and shrink to 0
    uint8_t radius = ((256 - time_factor) * 6) / 256;
    
    if (distance <= radius && radius > 0) {
        // Add intensity falloff like outward_burst
        uint8_t intensity = 255 - ((distance * 255) / (radius + 1));
        return (intensity * intensity) / 255; // Square for falloff
    }
    return 0;
}

static uint8_t outward_burst_reverse_large_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return outward_burst_reverse_large_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t outward_burst_reverse_massive_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 10
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 10 || col_diff > 10) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 120;
    if (time_factor > 256) return 0;
    
    // Start at radius 10 and shrink to 0
    uint8_t radius = ((256 - time_factor) * 10) / 256;
    
    if (distance <= radius && radius > 0) {
        // Add intensity falloff like outward_burst
        uint8_t intensity = 255 - ((distance * 255) / (radius + 1));
        return (intensity * intensity) / 255; // Square for falloff
    }
    return 0;
}

static uint8_t outward_burst_reverse_massive_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return outward_burst_reverse_massive_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t ripple_small_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 3
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 3 || col_diff > 3) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 120;
    if (time_factor > 256) return 0;
    
    // Reverse: radius goes from 3 to 0 (inward ripple)
    uint8_t radius = (3 * (256 - time_factor)) / 256;
    
    // Thinner ring: exact match only (was +1)
    if (distance == radius && radius > 0) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 3);
        return brightness_factor;
    }
    return 0;
}

static uint8_t ripple_small_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return ripple_small_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t ripple_med_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 5
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 5 || col_diff > 5) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 120;
    if (time_factor > 256) return 0;
    
    // Reverse: radius goes from 5 to 0 (inward ripple)
    uint8_t radius = (5 * (256 - time_factor)) / 256;
    
    // Thinner ring: exact match only (was +1)
    if (distance == radius && radius > 0) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 5);
        return brightness_factor;
    }
    return 0;
}

static uint8_t ripple_med_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return ripple_med_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t ripple_large_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 10
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 10 || col_diff > 10) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 120;
    if (time_factor > 256) return 0;
    
    // Reverse: radius goes from 10 to 0 (inward ripple)
    uint8_t radius = (10 * (256 - time_factor)) / 256;
    
    // Much thinner ring: exact match only (was +2)
    if (distance == radius && radius > 0) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 9);
        return brightness_factor;
    }
    return 0;
}

static uint8_t ripple_large_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return ripple_large_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t ripple_massive_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 15
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 15 || col_diff > 15) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    // 2x slower: multiply denominator by 2 (240/120 = 2)
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 240;
    if (time_factor > 256) return 0;
    
    // Reverse: radius goes from 15 to 0 (inward ripple)
    uint8_t radius = (15 * (256 - time_factor)) / 256;
    
    // Thinner ring: reduce thickness from +2 to +1
    if (distance >= radius && distance <= radius + 1 && radius > 0) {
        uint8_t brightness_factor = 255 - ((radius * 255) / 12);
        return brightness_factor;
    }
    return 0;
}

static uint8_t ripple_massive_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return ripple_massive_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// BURST ANIMATIONS (Standardized to /150.0f base)
// =============================================================================

static uint8_t row_burst_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    float distance = fabs((float)(led_col - note_col));
    // BURST STANDARD: /150.0f base timing
    float radius = (elapsed_time / 150.0f) * (0.3f + (speed / 200.0f) * 4.1f);
    
    if (distance > radius || radius > 5.0f) return 0;
    
    float intensity = 1.0f - (distance / radius);
    return (uint8_t)(255 * intensity * intensity);
}

static uint8_t row_burst_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return row_burst_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t column_burst_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0; // Same column only
    
    float distance = fabs((float)(led_row - note_row));
    // BURST STANDARD: /150.0f base timing
    float radius = (elapsed_time / 150.0f) * (0.3f + (speed / 200.0f) * 4.1f);
    
    if (distance > radius || radius > 4.0f) return 0;
    
    float intensity = 1.0f - (distance / radius);
    return (uint8_t)(255 * intensity * intensity);
}

static uint8_t column_burst_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return column_burst_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t row_burst_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    // BURST STANDARD: /150.0f base timing
    float time_factor = (elapsed_time / 150.0f) * (0.5f + (speed / 128.0f) * 6.5f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float radius;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): radius goes from 0 to 14
        radius = time_factor * 14.0f;
    } else {
        // Shrinking phase (1 to 2): radius goes from 14 back to 0
        radius = (2.0f - time_factor) * 14.0f;
    }
    
    float distance = fabs((float)(led_col - note_col));
    if (distance <= radius) {
        float intensity = 1.0f - (distance / radius);
        return (uint8_t)(255 * intensity * intensity);
    }
    return 0;
}

static uint8_t row_burst_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return row_burst_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t column_burst_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0; // Same column only
    
    // BURST STANDARD: /150.0f base timing
    float time_factor = (elapsed_time / 150.0f) * (0.5f + (speed / 128.0f) * 6.5f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float radius;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): radius goes from 0 to 3
        radius = time_factor * 15.0f;
    } else {
        // Shrinking phase (1 to 2): radius goes from 3 back to 0
        radius = (10.0f - time_factor) * 15.0f;
    }
    
    float distance = fabs((float)(led_row - note_row));
    if (distance <= radius) {
        float intensity = 1.0f - (distance / radius);
        return (uint8_t)(255 * intensity * intensity);
    }
    return 0;
}

static uint8_t column_burst_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return column_burst_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t outward_burst_small_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 4
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 4 || col_diff > 4) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    // Convert to integer math
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 150;
    if (time_factor > 512) return 0; // Stop after one cycle (512 = 2.0 * 256)
    
    uint8_t radius;
    if (time_factor <= 256) {
        // Growing phase: radius goes from 0 to 4
        radius = (time_factor * 4) / 256;
    } else {
        // Shrinking phase: radius goes from 4 back to 0
        radius = ((512 - time_factor) * 4) / 256;
    }
    
    if (distance <= radius && radius > 0) {
        uint8_t intensity = 255 - ((distance * 255) / (radius + 1));
        return (intensity * intensity) / 255; // Square for falloff
    }
    return 0;
}

static uint8_t outward_burst_small_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return outward_burst_small_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t outward_burst_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 6
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 6 || col_diff > 6) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 150;
    if (time_factor > 512) return 0;
    
    uint8_t radius;
    if (time_factor <= 256) {
        radius = (time_factor * 6) / 256;
    } else {
        radius = ((512 - time_factor) * 6) / 256;
    }
    
    if (distance <= radius && radius > 0) {
        uint8_t intensity = 255 - ((distance * 255) / (radius + 1));
        return (intensity * intensity) / 255;
    }
    return 0;
}

static uint8_t outward_burst_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return outward_burst_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t outward_burst_large_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // Early radius culling - max radius is 10
    uint8_t row_diff = abs(led_row - note_row);
    uint8_t col_diff = abs(led_col - note_col);
    if (row_diff > 10 || col_diff > 10) return 0;
    
    uint8_t distance = get_distance_fast(note_row, note_col, led_row, led_col);
    
    uint16_t time_factor = (elapsed_time * (38 + (speed * 224) / 255)) / 150;
    if (time_factor > 512) return 0;
    
    uint8_t radius;
    if (time_factor <= 256) {
        radius = (time_factor * 10) / 256;
    } else {
        radius = ((512 - time_factor) * 10) / 256;
    }
    
    if (distance <= radius && radius > 0) {
        uint8_t intensity = 255 - ((distance * 255) / (radius + 1));
        return (intensity * intensity) / 255;
    }
    return 0;
}

static uint8_t outward_burst_large_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return outward_burst_large_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// VOLUME ANIMATIONS (Standardized to /200.0f base)
// =============================================================================

static uint8_t volume_up_down_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0; // Same column only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float height;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): height goes from 0 to 2 LEDs each side
        height = time_factor * 2.0f;
    } else {
        // Shrinking phase (1 to 2): height goes from 2 back to 0
        height = (2.0f - time_factor) * 2.0f;
    }
    
    float distance = fabs((float)(led_row - note_row));
    if (distance <= height) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t volume_up_down_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_up_down_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_up_down_1_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float height;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): height goes from 0 to 2 LEDs each side
        height = time_factor * 2.0f;
    } else {
        // Shrinking phase (1 to 2): height goes from 2 back to 0
        height = (2.0f - time_factor) * 2.0f;
    }
    
    // Main column - full brightness
    if (led_col == note_col) {
        float distance = fabs((float)(led_row - note_row));
        if (distance <= height) {
            return 255;
        }
    }
    
    // Adjacent columns - half brightness and half height
    if (abs(led_col - note_col) == 1) {
        float distance = fabs((float)(led_row - note_row));
        if (distance <= height / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t volume_up_down_1_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_up_down_1_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_up_down_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0; // Same column only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float height;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): height goes from 0 to 4 LEDs each side (full height)
        height = time_factor * 4.0f;
    } else {
        // Shrinking phase (1 to 2): height goes from 4 back to 0
        height = (2.0f - time_factor) * 4.0f;
    }
    
    float distance = fabs((float)(led_row - note_row));
    if (distance <= height) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t volume_up_down_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_up_down_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_up_down_2_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float height;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): height goes from 0 to 4 LEDs each side (full height)
        height = time_factor * 4.0f;
    } else {
        // Shrinking phase (1 to 2): height goes from 4 back to 0
        height = (2.0f - time_factor) * 4.0f;
    }
    
    // Main column - full brightness
    if (led_col == note_col) {
        float distance = fabs((float)(led_row - note_row));
        if (distance <= height) {
            return 255;
        }
    }
    
    // Adjacent columns - half brightness and half height
    if (abs(led_col - note_col) == 1) {
        float distance = fabs((float)(led_row - note_row));
        if (distance <= height / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t volume_up_down_2_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_up_down_2_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_left_right_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float width;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): width goes from 0 to 3 LEDs each side
        width = time_factor * 3.0f;
    } else {
        // Shrinking phase (1 to 2): width goes from 3 back to 0
        width = (2.0f - time_factor) * 3.0f;
    }
    
    float distance = fabs((float)(led_col - note_col));
    if (distance <= width) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t volume_left_right_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_left_right_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_left_right_1_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float width;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): width goes from 0 to 3 LEDs each side
        width = time_factor * 3.0f;
    } else {
        // Shrinking phase (1 to 2): width goes from 3 back to 0
        width = (2.0f - time_factor) * 3.0f;
    }
    
    // Main row - full brightness
    if (led_row == note_row) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width) {
            return 255;
        }
    }
    
    // Adjacent rows - half brightness and half width
    if (abs(led_row - note_row) == 1) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t volume_left_right_1_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_left_right_1_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_left_right_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float width;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): width goes from 0 to 7 LEDs each side
        width = time_factor * 7.0f;
    } else {
        // Shrinking phase (1 to 2): width goes from 7 back to 0
        width = (2.0f - time_factor) * 7.0f;
    }
    
    float distance = fabs((float)(led_col - note_col));
    if (distance <= width) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t volume_left_right_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_left_right_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_left_right_2_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float width;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): width goes from 0 to 7 LEDs each side
        width = time_factor * 7.0f;
    } else {
        // Shrinking phase (1 to 2): width goes from 7 back to 0
        width = (2.0f - time_factor) * 7.0f;
    }
    
    // Main row - full brightness
    if (led_row == note_row) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width) {
            return 255;
        }
    }
    
    // Adjacent rows - half brightness and half width
    if (abs(led_row - note_row) == 1) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t volume_left_right_2_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_left_right_2_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_left_right_3_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float width;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): width goes from 0 to 13 LEDs each side (full width)
        width = time_factor * 13.0f;
    } else {
        // Shrinking phase (1 to 2): width goes from 13 back to 0
        width = (2.0f - time_factor) * 13.0f;
    }
    
    float distance = fabs((float)(led_col - note_col));
    if (distance <= width) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t volume_left_right_3_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_left_right_3_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t volume_left_right_3_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 2.0f) return 0; // Stop after one cycle
    
    float width;
    if (time_factor <= 1.0f) {
        // Growing phase (0 to 1): width goes from 0 to 13 LEDs each side (full width)
        width = time_factor * 13.0f;
    } else {
        // Shrinking phase (1 to 2): width goes from 13 back to 0
        width = (2.0f - time_factor) * 13.0f;
    }
    
    // Main row - full brightness
    if (led_row == note_row) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width) {
            return 255;
        }
    }
    
    // Adjacent rows - half brightness and half width
    if (abs(led_row - note_row) == 1) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t volume_left_right_3_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return volume_left_right_3_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// PEAK VOLUME ANIMATIONS (Half duration, same timing base)
// =============================================================================

static uint8_t peak_volume_up_down_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0; // Same column only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle (half the time of regular volume)
    
    // Start at max height and shrink: height goes from 2 to 0
    float height = 2.0f * (1.0f - time_factor);
    
    float distance = fabs((float)(led_row - note_row));
    if (distance <= height) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t peak_volume_up_down_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_up_down_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_up_down_1_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max height and shrink: height goes from 2 to 0
    float height = 2.0f * (1.0f - time_factor);
    
    // Main column - full brightness
    if (led_col == note_col) {
        float distance = fabs((float)(led_row - note_row));
        if (distance <= height) {
            return 255;
        }
    }
    
    // Adjacent columns - half brightness and half height
    if (abs(led_col - note_col) == 1) {
        float distance = fabs((float)(led_row - note_row));
        if (distance <= height / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t peak_volume_up_down_1_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_up_down_1_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_up_down_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_col != note_col) return 0; // Same column only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max height and shrink: height goes from 4 to 0 (full height)
    float height = 4.0f * (1.0f - time_factor);
    
    float distance = fabs((float)(led_row - note_row));
    if (distance <= height) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t peak_volume_up_down_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_up_down_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_up_down_2_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max height and shrink: height goes from 4 to 0 (full height)
    float height = 4.0f * (1.0f - time_factor);
    
    // Main column - full brightness
    if (led_col == note_col) {
        float distance = fabs((float)(led_row - note_row));
        if (distance <= height) {
            return 255;
        }
    }
    
    // Adjacent columns - half brightness and half height
    if (abs(led_col - note_col) == 1) {
        float distance = fabs((float)(led_row - note_row));
        if (distance <= height / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t peak_volume_up_down_2_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_up_down_2_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_left_right_1_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max width and shrink: width goes from 3 to 0
    float width = 3.0f * (1.0f - time_factor);
    
    float distance = fabs((float)(led_col - note_col));
    if (distance <= width) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t peak_volume_left_right_1_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_left_right_1_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_left_right_1_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max width and shrink: width goes from 3 to 0
    float width = 3.0f * (1.0f - time_factor);
    
    // Main row - full brightness
    if (led_row == note_row) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width) {
            return 255;
        }
    }
    
    // Adjacent rows - half brightness and half width
    if (abs(led_row - note_row) == 1) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t peak_volume_left_right_1_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_left_right_1_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_left_right_2_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max width and shrink: width goes from 7 to 0
    float width = 7.0f * (1.0f - time_factor);
    
    float distance = fabs((float)(led_col - note_col));
    if (distance <= width) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t peak_volume_left_right_2_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_left_right_2_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_left_right_2_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max width and shrink: width goes from 7 to 0
    float width = 7.0f * (1.0f - time_factor);
    
    // Main row - full brightness
    if (led_row == note_row) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width) {
            return 255;
        }
    }
    
    // Adjacent rows - half brightness and half width
    if (abs(led_row - note_row) == 1) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t peak_volume_left_right_2_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_left_right_2_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_left_right_3_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    if (led_row != note_row) return 0; // Same row only
    
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max width and shrink: width goes from 13 to 0 (full width)
    float width = 13.0f * (1.0f - time_factor);
    
    float distance = fabs((float)(led_col - note_col));
    if (distance <= width) {
        return 255; // Full brightness throughout
    }
    return 0;
}

static uint8_t peak_volume_left_right_3_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_left_right_3_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

static uint8_t peak_volume_left_right_3_wide_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    // VOLUME STANDARD: /200.0f base timing
    float time_factor = (elapsed_time / 200.0f) * (0.25f + (speed / 255.0f) * 1.75f);
    
    if (time_factor > 1.0f) return 0; // Stop after one cycle
    
    // Start at max width and shrink: width goes from 13 to 0 (full width)
    float width = 13.0f * (1.0f - time_factor);
    
    // Main row - full brightness
    if (led_row == note_row) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width) {
            return 255;
        }
    }
    
    // Adjacent rows - half brightness and half width
    if (abs(led_row - note_row) == 1) {
        float distance = fabs((float)(led_col - note_col));
        if (distance <= width / 2.0f) {
            return 128;
        }
    }
    
    return 0;
}

static uint8_t peak_volume_left_right_3_wide_solo_math(uint8_t note_row, uint8_t note_col, uint8_t led_row, uint8_t led_col, uint16_t elapsed_time, uint8_t speed) {
    return peak_volume_left_right_3_wide_math(note_row, note_col, led_row, led_col, elapsed_time, speed);
}

// =============================================================================
// ACTIVE NOTE MANAGEMENT
// =============================================================================

static void add_active_note(uint8_t row, uint8_t col, uint8_t color_id, uint8_t track_id, uint8_t animation_type, bool is_live) {
    // Find available slot
    for (uint8_t i = 0; i < MAX_ACTIVE_NOTES; i++) {
        if (!active_notes[i].active) {
            active_notes[i].row = row;
            active_notes[i].col = col;
            active_notes[i].start_time = timer_read();
            active_notes[i].color_id = color_id;
            active_notes[i].track_id = track_id;
            active_notes[i].animation_type = animation_type;
            active_notes[i].is_live = is_live;
            active_notes[i].active = true;
            active_note_count++;
            return;
        }
    }
    
    // If no slot available, replace oldest
    uint8_t oldest = 0;
    uint16_t oldest_time = active_notes[0].start_time;
    for (uint8_t i = 1; i < MAX_ACTIVE_NOTES; i++) {
        if (active_notes[i].start_time < oldest_time) {
            oldest = i;
            oldest_time = active_notes[i].start_time;
        }
    }
    
    active_notes[oldest].row = row;
    active_notes[oldest].col = col;
    active_notes[oldest].start_time = timer_read();
    active_notes[oldest].color_id = color_id;
    active_notes[oldest].track_id = track_id;
    active_notes[oldest].animation_type = animation_type;
    active_notes[oldest].is_live = is_live;
    active_notes[oldest].active = true;
}

static void cleanup_active_notes(uint8_t live_speed, uint8_t macro_speed) {
    uint16_t current_time = timer_read();
    uint8_t write_index = 0;
    
    // Instead of removing items one by one (expensive), compact the array in one pass
    for (uint8_t read_index = 0; read_index < MAX_ACTIVE_NOTES; read_index++) {
        if (active_notes[read_index].active) {
            uint16_t elapsed = current_time - active_notes[read_index].start_time;
            uint8_t speed = active_notes[read_index].is_live ? live_speed : macro_speed;
            uint16_t max_duration = 2000 - ((speed * 1500) / 255);
            
            if (elapsed < max_duration) {
                // Keep this note - copy to write position if different
                if (write_index != read_index) {
                    active_notes[write_index] = active_notes[read_index];
                }
                write_index++;
            }
            // If elapsed >= max_duration, we skip copying (effectively removing it)
        }
    }
    
    // Clear any remaining slots and update count
    for (uint8_t i = write_index; i < MAX_ACTIVE_NOTES; i++) {
        active_notes[i].active = false;
    }
    active_note_count = write_index;
}

// =============================================================================
// HEAT SYSTEM FUNCTIONS
// =============================================================================

static void apply_heat_effect(position_data_t* positions, uint8_t color_id, bool is_live) {
    for (uint8_t pos = 0; pos < positions->count; pos++) {
        uint8_t row = positions->points[pos].row;
        uint8_t col = positions->points[pos].col;
        
        uint8_t led[LED_HITS_TO_REMEMBER];
        uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
        if (led_count > 0) {
            if (is_live) {
                live_led_heatmap[led[0]] = qadd8(live_led_heatmap[led[0]], TRUEKEY_HEATMAP_INCREASE_STEP);
                live_led_color_id[led[0]] = color_id % 16;
            } else {
                macro_led_heatmap[led[0]] = qadd8(macro_led_heatmap[led[0]], TRUEKEY_HEATMAP_INCREASE_STEP);
                macro_led_color_id[led[0]] = color_id % 16;
            }
        }
    }
}

static int8_t find_sustained_key(uint8_t channel, uint8_t note, uint8_t track_id, bool is_live) {
    for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
        if (sustained_keys[i].active && 
            sustained_keys[i].channel == channel && 
            sustained_keys[i].note == note &&
            sustained_keys[i].track_id == track_id &&
            sustained_keys[i].is_macro == !is_live) {
            return i;
        }
    }
    return -1;
}

static bool add_sustained_key(uint8_t channel, uint8_t note, uint8_t track_id, uint8_t color_id, uint8_t positioning_type, bool is_live) {
    for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
        if (!sustained_keys[i].active) {
            sustained_keys[i].channel = channel;
            sustained_keys[i].note = note;
            sustained_keys[i].track_id = track_id;
            sustained_keys[i].color_id = color_id;
            sustained_keys[i].start_time = timer_read();
            sustained_keys[i].positioning_type = positioning_type;
            sustained_keys[i].is_macro = !is_live;
            sustained_keys[i].active = true;
            return true;
        }
    }
    return false;
}

// Function to determine if an animation is a solo type
static bool is_solo_animation(uint8_t animation_type) {
    switch (animation_type) {
        case LIVE_ANIM_NONE_SOLO:
        case LIVE_ANIM_WIDE1_SOLO:
        case LIVE_ANIM_WIDE2_SOLO:
        case LIVE_ANIM_COLUMN_SOLO:
        case LIVE_ANIM_ROW_SOLO:
        case LIVE_ANIM_CROSS_SOLO:
        case LIVE_ANIM_CROSS_2_SOLO:  // NEW
        case LIVE_ANIM_MOVING_DOTS1_ROW_SOLO:
        case LIVE_ANIM_MOVING_DOTS2_ROW_SOLO:
        case LIVE_ANIM_MOVING_DOTS1_COL_SOLO:
        case LIVE_ANIM_MOVING_DOTS2_COL_SOLO:
        case LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE_SOLO:  // NEW
        case LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE_SOLO:  // NEW
        case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_SOLO:
        case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE_SOLO:
        case LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_SOLO:
        case LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE_SOLO:  // NEW
        case LIVE_ANIM_RIPPLE_SMALL_1_SOLO:
        case LIVE_ANIM_RIPPLE_MED_1_SOLO:
        case LIVE_ANIM_RIPPLE_LARGE_1_SOLO:
        case LIVE_ANIM_RIPPLE_MASSIVE_1_SOLO:
		case LIVE_ANIM_RIPPLE_SMALL_2_SOLO:
        case LIVE_ANIM_RIPPLE_MED_2_SOLO:
        case LIVE_ANIM_RIPPLE_LARGE_2_SOLO:
        case LIVE_ANIM_RIPPLE_MASSIVE_2_SOLO:
        case LIVE_ANIM_ROW_BURST_1_SOLO:
        case LIVE_ANIM_ROW_BURST_2_SOLO:
        case LIVE_ANIM_COLUMN_BURST_1_SOLO:
        case LIVE_ANIM_COLUMN_BURST_2_SOLO:
		case LIVE_ANIM_OUTWARD_BURST_SMALL_2:  // Now a solo
        case LIVE_ANIM_OUTWARD_BURST_2:        // Now a solo
        case LIVE_ANIM_OUTWARD_BURST_LARGE_2:  // Now a solo
        case LIVE_ANIM_VOLUME_UP_DOWN_1_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_UP_DOWN_1_WIDE_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_UP_DOWN_2_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_UP_DOWN_2_WIDE_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_1_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_1_WIDE_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_2_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_2_WIDE_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_3_SOLO:  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_3_WIDE_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_SOLO:  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE_SOLO:  // NEW
        case LIVE_ANIM_MOVING_DOTS_ROW_1_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_DOTS_ROW_2_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_DOTS_COL_1_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_DOTS_COL_2_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_COLUMNS_3_1_SOLO:
        case LIVE_ANIM_MOVING_COLUMNS_3_2_SOLO:
        case LIVE_ANIM_MOVING_COLUMNS_3_1_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_COLUMNS_3_2_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_ROWS_3_1_SOLO:
        case LIVE_ANIM_MOVING_ROWS_3_2_SOLO:
        case LIVE_ANIM_MOVING_ROWS_3_1_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_ROWS_3_2_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_COLUMNS_8_1_SOLO:
        case LIVE_ANIM_MOVING_COLUMNS_8_2_SOLO:
        case LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_COLUMNS_8_2_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_ROWS_8_1_SOLO:
        case LIVE_ANIM_MOVING_ROWS_8_2_SOLO:
        case LIVE_ANIM_MOVING_ROWS_8_1_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_ROWS_8_2_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_SOLO:
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_SOLO:
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_SOLO:
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_SOLO:
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE_SOLO:
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE_SOLO:
		case LIVE_COLLAPSING_BURST_SMALL_SOLO:
		case LIVE_COLLAPSING_BURST_MED_SOLO:
		case LIVE_COLLAPSING_BURST_LARGE_SOLO:
		case LIVE_COLLAPSING_BURST_MASSIVE_SOLO:
            return true;
        default:
            return false;
    }
}

// Updated get_base_animation_type function - add these cases to your existing switch statement:
static uint8_t get_base_animation_type(uint8_t animation_type) {
    switch (animation_type) {
        case LIVE_ANIM_NONE_SOLO: return LIVE_ANIM_NONE;
        case LIVE_ANIM_WIDE1_SOLO: return LIVE_ANIM_WIDE1;
        case LIVE_ANIM_WIDE2_SOLO: return LIVE_ANIM_WIDE2;
        case LIVE_ANIM_COLUMN_SOLO: return LIVE_ANIM_COLUMN;
        case LIVE_ANIM_ROW_SOLO: return LIVE_ANIM_ROW;
        case LIVE_ANIM_CROSS_SOLO: return LIVE_ANIM_CROSS;
        case LIVE_ANIM_CROSS_2_SOLO: return LIVE_ANIM_CROSS_2;  // NEW
        case LIVE_ANIM_MOVING_DOTS1_ROW_SOLO: return LIVE_ANIM_MOVING_DOTS1_ROW;
        case LIVE_ANIM_MOVING_DOTS2_ROW_SOLO: return LIVE_ANIM_MOVING_DOTS2_ROW;
        case LIVE_ANIM_MOVING_DOTS1_COL_SOLO: return LIVE_ANIM_MOVING_DOTS1_COL;
        case LIVE_ANIM_MOVING_DOTS2_COL_SOLO: return LIVE_ANIM_MOVING_DOTS2_COL;
        case LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE_SOLO: return LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE;  // NEW
        case LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE_SOLO: return LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE;  // NEW
        case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_SOLO: return LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL;
        case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE_SOLO: return LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE;
        case LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_SOLO: return LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL;
        case LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE_SOLO: return LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE;  // NEW
        case LIVE_ANIM_RIPPLE_SMALL_1_SOLO: return LIVE_ANIM_RIPPLE_SMALL_1;
        case LIVE_ANIM_RIPPLE_MED_1_SOLO: return LIVE_ANIM_RIPPLE_MED_1;
        case LIVE_ANIM_RIPPLE_LARGE_1_SOLO: return LIVE_ANIM_RIPPLE_LARGE_1;
        case LIVE_ANIM_RIPPLE_MASSIVE_1_SOLO: return LIVE_ANIM_RIPPLE_MASSIVE_1;
        case LIVE_ANIM_ROW_BURST_1_SOLO: return LIVE_ANIM_ROW_BURST_1;
        case LIVE_ANIM_ROW_BURST_2_SOLO: return LIVE_ANIM_ROW_BURST_2;
        case LIVE_ANIM_COLUMN_BURST_1_SOLO: return LIVE_ANIM_COLUMN_BURST_1;
        case LIVE_ANIM_COLUMN_BURST_2_SOLO: return LIVE_ANIM_COLUMN_BURST_2;
        case LIVE_ANIM_VOLUME_UP_DOWN_1_SOLO: return LIVE_ANIM_VOLUME_UP_DOWN_1;  // NEW
        case LIVE_ANIM_VOLUME_UP_DOWN_1_WIDE_SOLO: return LIVE_ANIM_VOLUME_UP_DOWN_1_WIDE;  // NEW
        case LIVE_ANIM_VOLUME_UP_DOWN_2_SOLO: return LIVE_ANIM_VOLUME_UP_DOWN_2;  // NEW
        case LIVE_ANIM_VOLUME_UP_DOWN_2_WIDE_SOLO: return LIVE_ANIM_VOLUME_UP_DOWN_2_WIDE;  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_1_SOLO: return LIVE_ANIM_VOLUME_LEFT_RIGHT_1;  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_1_WIDE_SOLO: return LIVE_ANIM_VOLUME_LEFT_RIGHT_1_WIDE;  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_2_SOLO: return LIVE_ANIM_VOLUME_LEFT_RIGHT_2;  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_2_WIDE_SOLO: return LIVE_ANIM_VOLUME_LEFT_RIGHT_2_WIDE;  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_3_SOLO: return LIVE_ANIM_VOLUME_LEFT_RIGHT_3;  // NEW
        case LIVE_ANIM_VOLUME_LEFT_RIGHT_3_WIDE_SOLO: return LIVE_ANIM_VOLUME_LEFT_RIGHT_3_WIDE;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_SOLO: return LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE_SOLO: return LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_SOLO: return LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE_SOLO: return LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_SOLO: return LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE_SOLO: return LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_SOLO: return LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE_SOLO: return LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_SOLO: return LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3;  // NEW
        case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE_SOLO: return LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE;  // NEW
		case LIVE_ANIM_RIPPLE_SMALL_2_SOLO: return LIVE_ANIM_RIPPLE_SMALL_2;
        case LIVE_ANIM_RIPPLE_MED_2_SOLO: return LIVE_ANIM_RIPPLE_MED_2;
        case LIVE_ANIM_RIPPLE_LARGE_2_SOLO: return LIVE_ANIM_RIPPLE_LARGE_2;
        case LIVE_ANIM_RIPPLE_MASSIVE_2_SOLO: return LIVE_ANIM_RIPPLE_MASSIVE_2;
		case LIVE_ANIM_MOVING_DOTS_ROW_1_REVERSE_SOLO: return LIVE_ANIM_MOVING_DOTS_ROW_1_REVERSE;
        case LIVE_ANIM_MOVING_DOTS_ROW_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_DOTS_ROW_2_REVERSE;
        case LIVE_ANIM_MOVING_DOTS_COL_1_REVERSE_SOLO: return LIVE_ANIM_MOVING_DOTS_COL_1_REVERSE;
        case LIVE_ANIM_MOVING_DOTS_COL_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_DOTS_COL_2_REVERSE;
        case LIVE_ANIM_MOVING_COLUMNS_3_1_SOLO: return LIVE_ANIM_MOVING_COLUMNS_3_1;
        case LIVE_ANIM_MOVING_COLUMNS_3_2_SOLO: return LIVE_ANIM_MOVING_COLUMNS_3_2;
        case LIVE_ANIM_MOVING_COLUMNS_3_1_REVERSE_SOLO: return LIVE_ANIM_MOVING_COLUMNS_3_1_REVERSE;
        case LIVE_ANIM_MOVING_COLUMNS_3_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_COLUMNS_3_2_REVERSE;
        case LIVE_ANIM_MOVING_ROWS_3_1_SOLO: return LIVE_ANIM_MOVING_ROWS_3_1;
        case LIVE_ANIM_MOVING_ROWS_3_2_SOLO: return LIVE_ANIM_MOVING_ROWS_3_2;
        case LIVE_ANIM_MOVING_ROWS_3_1_REVERSE_SOLO: return LIVE_ANIM_MOVING_ROWS_3_1_REVERSE;
        case LIVE_ANIM_MOVING_ROWS_3_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_ROWS_3_2_REVERSE;
        case LIVE_ANIM_MOVING_COLUMNS_8_1_SOLO: return LIVE_ANIM_MOVING_COLUMNS_8_1;
        case LIVE_ANIM_MOVING_COLUMNS_8_2_SOLO: return LIVE_ANIM_MOVING_COLUMNS_8_2;
        case LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE_SOLO: return LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE;
        case LIVE_ANIM_MOVING_COLUMNS_8_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_COLUMNS_8_2_REVERSE;
        case LIVE_ANIM_MOVING_ROWS_8_1_SOLO: return LIVE_ANIM_MOVING_ROWS_8_1;
        case LIVE_ANIM_MOVING_ROWS_8_2_SOLO: return LIVE_ANIM_MOVING_ROWS_8_2;
        case LIVE_ANIM_MOVING_ROWS_8_1_REVERSE_SOLO: return LIVE_ANIM_MOVING_ROWS_8_1_REVERSE;
        case LIVE_ANIM_MOVING_ROWS_8_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_ROWS_8_2_REVERSE;
        case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE_SOLO: return LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE;
        case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE;
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_SOLO: return LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1;
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_SOLO: return LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2;
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE_SOLO: return LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE;
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE;
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_SOLO: return LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1;
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_SOLO: return LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2;
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE_SOLO: return LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE;
        case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE_SOLO: return LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE;
		case LIVE_COLLAPSING_BURST_SMALL_SOLO: return LIVE_COLLAPSING_BURST_SMALL;
		case LIVE_COLLAPSING_BURST_MED_SOLO: return LIVE_COLLAPSING_BURST_MED;
		case LIVE_COLLAPSING_BURST_LARGE_SOLO: return LIVE_COLLAPSING_BURST_LARGE;
		case LIVE_COLLAPSING_BURST_MASSIVE_SOLO: return LIVE_COLLAPSING_BURST_MASSIVE;
        default: return animation_type; // Return as-is if not a solo type
    }
}

// Function to clear all active notes of a specific animation type (with track consideration for macros)
static void clear_active_notes_of_type(uint8_t animation_type, bool is_live, uint8_t track_id) {
    uint8_t base_type = get_base_animation_type(animation_type);
    
    for (uint8_t i = 0; i < MAX_ACTIVE_NOTES; i++) {
        if (active_notes[i].active && active_notes[i].is_live == is_live) {
            uint8_t note_base_type = get_base_animation_type(active_notes[i].animation_type);
            
            // Clear if it matches the base animation type
            if (note_base_type == base_type) {
                // For live notes, clear all matching animations
                // For macro notes, only clear if it's the same track
                if (is_live || active_notes[i].track_id == track_id) {
                    active_notes[i].active = false;
                    active_note_count--;
                }
            }
        }
    }
}

// Modified add_active_note function to handle solo animations with track consideration
static void add_active_note_with_solo_check(uint8_t row, uint8_t col, uint8_t color_id, uint8_t track_id, uint8_t animation_type, bool is_live) {
    // If this is a solo animation, clear existing animations of the same type first
    if (is_solo_animation(animation_type)) {
        clear_active_notes_of_type(animation_type, is_live, track_id);
    }
    
    // Now add the new active note
    add_active_note(row, col, color_id, track_id, animation_type, is_live);
}


// =============================================================================
// NOTE PROCESSING FUNCTIONS
// =============================================================================

// Updated process_note function to fix pitch-based color issues
static void process_note(uint8_t channel, uint8_t note, uint8_t track_id, bool is_live,
                        live_note_positioning_t live_positioning, macro_note_positioning_t macro_positioning,
                        live_animation_t live_animation, macro_animation_t macro_animation,
                        bool use_influence, uint8_t color_type) {
    
    position_data_t positions;
    
    // Get positions based on live or macro
    if (is_live) {
        get_live_positions(channel, note, live_positioning, &positions);
    } else {
        get_macro_positions(channel, note, track_id, macro_positioning, &positions);
    }
    
    if (positions.count == 0) return;
    
    // Get animation type
    uint8_t animation = is_live ? live_animation : macro_animation;
    
    // Handle heat and sustain effects
    if (animation == LIVE_ANIM_HEAT || animation == MACRO_ANIM_HEAT) {
        apply_heat_effect(&positions, channel, is_live);
        return;
    }
    
    if (animation == LIVE_ANIM_SUSTAIN || animation == MACRO_ANIM_SUSTAIN) {
        uint8_t positioning = is_live ? live_positioning : macro_positioning;
        if (find_sustained_key(channel, note, track_id, is_live) == -1) {
            add_sustained_key(channel, note, track_id, channel, positioning, is_live);
        }
        apply_heat_effect(&positions, channel, is_live);
        return;
    }
    
    // FIXED: Set color_id based on color_type
    uint8_t color_id;
    
    // Check if this is a pitch-based color type
    if (color_type == 4 || color_type == 5 ||      // Pitch Colors Up/Down
        color_type == 10 || color_type == 11 ||    // Pitch Colors Up/Down Max Sat
        color_type == 16 || color_type == 17 ||    // Pitch Colors Up/Down Desat
        color_type == 22 || color_type == 23 ||    // Pitch Colors Up/Down Distance
        color_type == 28 || color_type == 29 ||    // Pitch Colors Up/Down Distance Max Sat
        color_type == 34 || color_type == 35) {    // Pitch Colors Up/Down Distance Desat
        color_id = note; // Use actual MIDI note number for pitch-based colors
    } else {
        color_id = is_live ? channel : track_id; // Use channel/track for other color types
    }
    
    // For other animations, add to active notes with solo check
    for (uint8_t pos = 0; pos < positions.count; pos++) {
        add_active_note_with_solo_check(positions.points[pos].row, positions.points[pos].col, color_id, track_id, animation, is_live);
    }
}

// =============================================================================
// MAIN EFFICIENT EFFECT RUNNER - FIXED TO USE ROW/COL ITERATION + NEW ANIMATIONS
// =============================================================================

static bool run_efficient_effect(effect_params_t* params,
                                live_note_positioning_t live_positioning,
                                macro_note_positioning_t macro_positioning,
                                live_animation_t live_animation,
                                macro_animation_t macro_animation,
                                bool use_influence,
                                background_mode_t background_mode,
                                uint8_t pulse_mode,
                                uint8_t color_type,
                                uint8_t background_brightness_pct,
                                uint8_t live_speed,
                                uint8_t macro_speed) {

    static uint16_t live_heat_timer = 0;
    static uint16_t macro_heat_timer = 0;
    static uint16_t cached_current_time = 0;
    static uint16_t cache_update_timer = 0;
    
    // Update cached timers only every 5ms to reduce timer_read() calls
    if (params->init || timer_elapsed(cache_update_timer) >= 5) {
        cached_current_time = timer_read();
        cache_update_timer = cached_current_time;
    }
    
    // Determine which effects are active
    truekey_effects_active = (live_positioning == LIVE_POS_TRUEKEY) || 
                            (macro_positioning == MACRO_POS_TRUEKEY);
    
    bool live_heat_mode = (live_animation == LIVE_ANIM_HEAT) || (live_animation == LIVE_ANIM_SUSTAIN);
    bool macro_heat_mode = (macro_animation == MACRO_ANIM_HEAT) || (macro_animation == MACRO_ANIM_SUSTAIN);
    
    if (params->init) {
        // Initialize arrays
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            live_led_heatmap[i] = 0;
            live_led_color_id[i] = 255;
            macro_led_heatmap[i] = 0;
            macro_led_color_id[i] = 255;
        }
        for (uint8_t i = 0; i < MAX_ACTIVE_NOTES; i++) {
            active_notes[i].active = false;
        }
        for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
            sustained_keys[i].active = false;
        }
        active_note_count = 0;

        // Initialize BPM background system
        last_bpm_flash_state = false;
        bpm_pulse_start_time = 0;
        bpm_pulse_intensity = 0;
        bpm_all_beat_count = 0;
        bpm_beat_count = 0;
        bpm_colors_generated = false;

        live_heat_timer = cached_current_time;
        macro_heat_timer = cached_current_time;
        
        // Initialize distance table
        init_distance_table();
    }
    
    // Update BPM background system
    update_bpm_background(background_mode);
    
    // Handle heat decay using cached timer
    if (live_heat_mode && timer_elapsed(live_heat_timer) >= 10) {
        bool sustain_mode = (live_animation == LIVE_ANIM_SUSTAIN);
        uint8_t decay_amount = sustain_mode ? 13 : (1 + (live_speed / 64));
        
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            if (sustain_mode) {
                // Check if LED has active sustained key
                bool has_active_key = false;
                for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
                    if (sustained_keys[h].active && !sustained_keys[h].is_macro) {
                        position_data_t positions;
                        get_live_positions(sustained_keys[h].channel, sustained_keys[h].note, 
                                         (live_note_positioning_t)sustained_keys[h].positioning_type, &positions);
                        for (uint8_t p = 0; p < positions.count; p++) {
                            uint8_t led[LED_HITS_TO_REMEMBER];
                            uint8_t led_count = rgb_matrix_map_row_column_to_led(positions.points[p].row, positions.points[p].col, led);
                            if (led_count > 0 && led[0] == i) {
                                has_active_key = true;
                                break;
                            }
                        }
                        if (has_active_key) break;
                    }
                }
                if (!has_active_key) {
                    live_led_heatmap[i] = qsub8(live_led_heatmap[i], decay_amount);
                }
            } else {
                live_led_heatmap[i] = qsub8(live_led_heatmap[i], decay_amount);
            }
        }
        live_heat_timer = cached_current_time;
    }
    
    if (macro_heat_mode && timer_elapsed(macro_heat_timer) >= 10) {
        bool sustain_mode = (macro_animation == MACRO_ANIM_SUSTAIN);
        uint8_t decay_amount = sustain_mode ? 13 : (1 + (macro_speed / 64));
        
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            if (sustain_mode) {
                bool has_active_key = false;
                for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
                    if (sustained_keys[h].active && sustained_keys[h].is_macro) {
                        position_data_t positions;
                        get_macro_positions(sustained_keys[h].channel, sustained_keys[h].note, sustained_keys[h].track_id,
                                          (macro_note_positioning_t)sustained_keys[h].positioning_type, &positions);
                        for (uint8_t p = 0; p < positions.count; p++) {
                            uint8_t led[LED_HITS_TO_REMEMBER];
                            uint8_t led_count = rgb_matrix_map_row_column_to_led(positions.points[p].row, positions.points[p].col, led);
                            if (led_count > 0 && led[0] == i) {
                                has_active_key = true;
                                break;
                            }
                        }
                        if (has_active_key) break;
                    }
                }
                if (!has_active_key) {
                    macro_led_heatmap[i] = qsub8(macro_led_heatmap[i], decay_amount);
                }
            } else {
                macro_led_heatmap[i] = qsub8(macro_led_heatmap[i], decay_amount);
            }
        }
        macro_heat_timer = cached_current_time;
    }
    
    // Process unified notes using optimized batch method
    for (uint8_t i = 0; i < unified_lighting_count; i++) {
        uint8_t channel = unified_lighting_notes[i][0];
        uint8_t note = unified_lighting_notes[i][1];
        uint8_t type = unified_lighting_notes[i][2];
        uint8_t track_id = unified_lighting_notes[i][3];
        bool is_live = (type == 0);
        
        process_note(channel, note, track_id, is_live, live_positioning, macro_positioning,
                    live_animation, macro_animation, use_influence, color_type);
    }
    unified_lighting_count = 0;
    
    // Clean up old active notes using cached timer
    cleanup_active_notes(live_speed, macro_speed);
    
    // Clean up sustained keys
    for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
        if (sustained_keys[h].active) {
            bool still_active = false;
            for (uint8_t i = 0; i < unified_lighting_count; i++) {
                if (unified_lighting_notes[i][0] == sustained_keys[h].channel && 
                    unified_lighting_notes[i][1] == sustained_keys[h].note &&
                    unified_lighting_notes[i][2] == (sustained_keys[h].is_macro ? 1 : 0) &&
                    (sustained_keys[h].is_macro ? unified_lighting_notes[i][3] == sustained_keys[h].track_id : true)) {
                    still_active = true;
                    break;
                }
            }
            if (!still_active) {
                sustained_keys[h].active = false;
            }
        }
    }
    
    // Render background
    if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_ALL_9) {
        render_bpm_background(background_mode, background_brightness_pct);
    } else if (is_static_background(background_mode)) {
        apply_backlight(30, background_mode, background_brightness_pct);
    } else if (is_autolight_background(background_mode)) {
        render_autolight_background(background_mode, background_brightness_pct);
    } else if (background_mode >= BACKGROUND_MATH_START && background_mode < BACKGROUND_MATH_START + num_math_backgrounds) {
        render_math_background_by_index(background_mode, background_brightness_pct);
    } else if (background_mode >= BACKGROUND_CYCLE_ALL_DESAT && background_mode <= BACKGROUND_BAND_SPIRAL_VAL_DESAT) {
        render_math_background_desaturated(background_mode, background_brightness_pct);
    } else if (background_mode >= BACKGROUND_DIAGONAL_WAVE_HUE_CYCLE && background_mode <= BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR_HUE_CYCLE) {
        render_math_background_by_index(background_mode, background_brightness_pct);
    } else if (background_mode >= BACKGROUND_DIAGONAL_WAVE_HUE_CYCLE_DESAT && background_mode <= BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR_HUE_CYCLE_DESAT) {
        render_math_background_desaturated(background_mode, background_brightness_pct);
    } else if (background_mode == BACKGROUND_NONE) {
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                uint8_t led[LED_HITS_TO_REMEMBER];
                uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
                if (led_count > 0) {
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    // Direct calculation for each ROW/COL with ALL ANIMATIONS
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                uint8_t led_index = led[0];
                
                uint8_t final_brightness = 0;
                uint8_t final_hue = base_hue;
                uint8_t final_sat = base_sat;
                
                // Check heat effects first
                if (live_heat_mode && live_led_heatmap[led_index] > 0) {
                    uint8_t heat = live_led_heatmap[led_index];
                    uint16_t hue_shift = (170 * (255 - heat)) / 255;
                    final_hue = hue_shift;
                    final_brightness = heat;
                } else if (macro_heat_mode && macro_led_heatmap[led_index] > 0) {
                    uint8_t heat = macro_led_heatmap[led_index];
                    uint16_t hue_shift = (170 * (255 - heat)) / 255;
                    final_hue = hue_shift;
                    final_brightness = heat;
                } else {
                    // Check active notes for other animations
                    for (uint8_t note = 0; note < MAX_ACTIVE_NOTES; note++) {
                        if (active_notes[note].active) {
                            uint16_t elapsed = cached_current_time - active_notes[note].start_time;
                            uint8_t speed = active_notes[note].is_live ? live_speed : macro_speed;
                            uint8_t animation = active_notes[note].animation_type;
                            
                            uint8_t brightness = 0;
                            
                            // Calculate brightness based on animation type
switch (animation) {
    case LIVE_ANIM_NONE:
        brightness = none_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_NONE_SOLO:
        brightness = none_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_WIDE1:
        brightness = wide1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_WIDE1_SOLO:
        brightness = wide1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_WIDE2:
        brightness = wide2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_WIDE2_SOLO:
        brightness = wide2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_COLUMN:
        brightness = column_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_COLUMN_SOLO:
        brightness = column_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_ROW:
        brightness = row_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_ROW_SOLO:
        brightness = row_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_CROSS:
        brightness = cross_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_CROSS_SOLO:
        brightness = cross_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_CROSS_2:
        brightness = cross_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS1_ROW:
        brightness = moving_dots_row_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS1_ROW_SOLO:
        brightness = moving_dots_row_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS2_ROW:
        brightness = moving_dots_row_no_fade_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS2_ROW_SOLO:
        brightness = moving_dots_row_no_fade_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS1_COL:
        brightness = moving_dots_col_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS1_COL_SOLO:
        brightness = moving_dots_col_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS2_COL:
        brightness = moving_dots_col_no_fade_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS2_COL_SOLO:
        brightness = moving_dots_col_no_fade_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE:
        brightness = moving_dots_diag_tl_br_no_fade_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE:
        brightness = moving_dots_diag_tr_bl_no_fade_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL:
        brightness = moving_dots_all_orthogonal_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_SOLO:
        brightness = moving_dots_all_orthogonal_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE:
        brightness = moving_dots_all_orthogonal_no_fade_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE_SOLO:
        brightness = moving_dots_all_orthogonal_no_fade_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL:
        brightness = moving_dots_all_diagonal_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_SOLO:
        brightness = moving_dots_all_diagonal_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE:
        brightness = moving_dots_all_diagonal_no_fade_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_SMALL_1:
        brightness = ripple_small_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_SMALL_1_SOLO:
        brightness = ripple_small_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_MED_1:
        brightness = ripple_med_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_MED_1_SOLO:
        brightness = ripple_med_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_LARGE_1:
        brightness = ripple_large_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_LARGE_1_SOLO:
        brightness = ripple_large_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_MASSIVE_1:
        brightness = ripple_massive_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_MASSIVE_1_SOLO:
        brightness = ripple_massive_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_SMALL_2:
        brightness = ripple_small_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_MED_2:
        brightness = ripple_med_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_LARGE_2:
        brightness = ripple_large_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_MASSIVE_2:
        brightness = ripple_massive_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
	case LIVE_ANIM_RIPPLE_SMALL_2_SOLO:
        brightness = ripple_small_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_MED_2_SOLO:
        brightness = ripple_med_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_LARGE_2_SOLO:
        brightness = ripple_large_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_RIPPLE_MASSIVE_2_SOLO:
        brightness = ripple_massive_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_ROW_BURST_1:
        brightness = row_burst_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_ROW_BURST_1_SOLO:
        brightness = row_burst_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_ROW_BURST_2:
        brightness = row_burst_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_ROW_BURST_2_SOLO:
        brightness = row_burst_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_COLUMN_BURST_1:
        brightness = column_burst_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_COLUMN_BURST_1_SOLO:
        brightness = column_burst_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_COLUMN_BURST_2:
        brightness = column_burst_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_COLUMN_BURST_2_SOLO:
        brightness = column_burst_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_OUTWARD_BURST_SMALL_1:
        brightness = outward_burst_small_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_OUTWARD_BURST_1:
        brightness = outward_burst_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_OUTWARD_BURST_LARGE_1:
        brightness = outward_burst_large_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_OUTWARD_BURST_SMALL_2:
        brightness = outward_burst_small_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_OUTWARD_BURST_2:
        brightness = outward_burst_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_OUTWARD_BURST_LARGE_2:
        brightness = outward_burst_large_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_UP_DOWN_1:
        brightness = volume_up_down_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_UP_DOWN_1_WIDE:
        brightness = volume_up_down_1_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_UP_DOWN_2:
        brightness = volume_up_down_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_UP_DOWN_2_WIDE:
        brightness = volume_up_down_2_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_1:
        brightness = volume_left_right_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_1_WIDE:
        brightness = volume_left_right_1_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_2:
        brightness = volume_left_right_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_2_WIDE:
        brightness = volume_left_right_2_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_3:
        brightness = volume_left_right_3_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_3_WIDE:
        brightness = volume_left_right_3_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
	case LIVE_ANIM_CROSS_2_SOLO:
        brightness = cross_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE_SOLO:
        brightness = moving_dots_diag_tl_br_no_fade_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE_SOLO:
        brightness = moving_dots_diag_tr_bl_no_fade_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE_SOLO:
        brightness = moving_dots_all_diagonal_no_fade_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_UP_DOWN_1_SOLO:
        brightness = volume_up_down_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_UP_DOWN_1_WIDE_SOLO:
        brightness = volume_up_down_1_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_UP_DOWN_2_SOLO:
        brightness = volume_up_down_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_UP_DOWN_2_WIDE_SOLO:
        brightness = volume_up_down_2_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_1_SOLO:
        brightness = volume_left_right_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_1_WIDE_SOLO:
        brightness = volume_left_right_1_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_2_SOLO:
        brightness = volume_left_right_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_2_WIDE_SOLO:
        brightness = volume_left_right_2_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_3_SOLO:
        brightness = volume_left_right_3_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_VOLUME_LEFT_RIGHT_3_WIDE_SOLO:
        brightness = volume_left_right_3_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1:
        brightness = peak_volume_up_down_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE:
        brightness = peak_volume_up_down_1_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2:
        brightness = peak_volume_up_down_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE:
        brightness = peak_volume_up_down_2_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1:
        brightness = peak_volume_left_right_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE:
        brightness = peak_volume_left_right_1_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2:
        brightness = peak_volume_left_right_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE:
        brightness = peak_volume_left_right_2_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3:
        brightness = peak_volume_left_right_3_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE:
        brightness = peak_volume_left_right_3_wide_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_SOLO:
        brightness = peak_volume_up_down_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE_SOLO:
        brightness = peak_volume_up_down_1_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_SOLO:
        brightness = peak_volume_up_down_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE_SOLO:
        brightness = peak_volume_up_down_2_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_SOLO:
        brightness = peak_volume_left_right_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE_SOLO:
        brightness = peak_volume_left_right_1_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_SOLO:
        brightness = peak_volume_left_right_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE_SOLO:
        brightness = peak_volume_left_right_2_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_SOLO:
        brightness = peak_volume_left_right_3_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE_SOLO:
        brightness = peak_volume_left_right_3_wide_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;	
	    // REVERSE DOT ANIMATIONS
    case LIVE_ANIM_MOVING_DOTS_ROW_1_REVERSE:
        brightness = moving_dots_row_1_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ROW_1_REVERSE_SOLO:
        brightness = moving_dots_row_1_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ROW_2_REVERSE:
        brightness = moving_dots_row_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ROW_2_REVERSE_SOLO:
        brightness = moving_dots_row_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_COL_1_REVERSE:
        brightness = moving_dots_col_1_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_COL_1_REVERSE_SOLO:
        brightness = moving_dots_col_1_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_COL_2_REVERSE:
        brightness = moving_dots_col_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_COL_2_REVERSE_SOLO:
        brightness = moving_dots_col_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
        
    // 3-PIXEL COLUMN ANIMATIONS
    case LIVE_ANIM_MOVING_COLUMNS_3_1:
        brightness = moving_columns_3_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_3_1_SOLO:
        brightness = moving_columns_3_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_3_2:
        brightness = moving_columns_3_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_3_2_SOLO:
        brightness = moving_columns_3_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_3_1_REVERSE:
        brightness = moving_columns_3_1_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_3_1_REVERSE_SOLO:
        brightness = moving_columns_3_1_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_3_2_REVERSE:
        brightness = moving_columns_3_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_3_2_REVERSE_SOLO:
        brightness = moving_columns_3_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
        
    // 3-PIXEL ROW ANIMATIONS
    case LIVE_ANIM_MOVING_ROWS_3_1:
        brightness = moving_rows_3_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_3_1_SOLO:
        brightness = moving_rows_3_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_3_2:
        brightness = moving_rows_3_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_3_2_SOLO:
        brightness = moving_rows_3_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_3_1_REVERSE:
        brightness = moving_rows_3_1_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_3_1_REVERSE_SOLO:
        brightness = moving_rows_3_1_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_3_2_REVERSE:
        brightness = moving_rows_3_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_3_2_REVERSE_SOLO:
        brightness = moving_rows_3_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
        
    // 8-PIXEL COLUMN ANIMATIONS
    case LIVE_ANIM_MOVING_COLUMNS_8_1:
        brightness = moving_columns_8_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_8_1_SOLO:
        brightness = moving_columns_8_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_8_2:
        brightness = moving_columns_8_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_8_2_SOLO:
        brightness = moving_columns_8_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE:
        brightness = moving_columns_8_1_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE_SOLO:
        brightness = moving_columns_8_1_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_8_2_REVERSE:
        brightness = moving_columns_8_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_COLUMNS_8_2_REVERSE_SOLO:
        brightness = moving_columns_8_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
        
    // 8-PIXEL ROW ANIMATIONS
    case LIVE_ANIM_MOVING_ROWS_8_1:
        brightness = moving_rows_8_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_8_1_SOLO:
        brightness = moving_rows_8_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_8_2:
        brightness = moving_rows_8_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_8_2_SOLO:
        brightness = moving_rows_8_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_8_1_REVERSE:
        brightness = moving_rows_8_1_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_8_1_REVERSE_SOLO:
        brightness = moving_rows_8_1_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_8_2_REVERSE:
        brightness = moving_rows_8_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ROWS_8_2_REVERSE_SOLO:
        brightness = moving_rows_8_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
        
    // ALL ORTHOGONAL ANIMATIONS
    case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE:
        brightness = moving_dots_all_orthogonal_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE_SOLO:
        brightness = moving_dots_all_orthogonal_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE:
        brightness = moving_dots_all_orthogonal_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE_SOLO:
        brightness = moving_dots_all_orthogonal_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1:
        brightness = moving_all_orthogonal_3_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
    case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_SOLO:
        brightness = moving_all_orthogonal_3_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
        break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2:
    brightness = moving_all_orthogonal_3_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_SOLO:
		brightness = moving_all_orthogonal_3_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE:
		brightness = moving_all_orthogonal_3_1_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE_SOLO:
		brightness = moving_all_orthogonal_3_1_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE:
		brightness = moving_all_orthogonal_3_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE_SOLO:
		brightness = moving_all_orthogonal_3_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1:
		brightness = moving_all_orthogonal_8_1_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_SOLO:
		brightness = moving_all_orthogonal_8_1_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2:
		brightness = moving_all_orthogonal_8_2_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_SOLO:
		brightness = moving_all_orthogonal_8_2_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE:
		brightness = moving_all_orthogonal_8_1_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE_SOLO:
		brightness = moving_all_orthogonal_8_1_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE:
		brightness = moving_all_orthogonal_8_2_reverse_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE_SOLO:
		brightness = moving_all_orthogonal_8_2_reverse_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_COLLAPSING_BURST_SMALL:
		brightness = outward_burst_reverse_small_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_COLLAPSING_BURST_MED:
		brightness = outward_burst_reverse_med_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_COLLAPSING_BURST_LARGE:
		brightness = outward_burst_reverse_large_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_COLLAPSING_BURST_MASSIVE:
		brightness = outward_burst_reverse_massive_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_COLLAPSING_BURST_SMALL_SOLO:
		brightness = outward_burst_reverse_small_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_COLLAPSING_BURST_MED_SOLO:
		brightness = outward_burst_reverse_med_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_COLLAPSING_BURST_LARGE_SOLO:
		brightness = outward_burst_reverse_large_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
	case LIVE_COLLAPSING_BURST_MASSIVE_SOLO:
		brightness = outward_burst_reverse_massive_solo_math(active_notes[note].row, active_notes[note].col, row, col, elapsed, speed);
		break;
		                                // Add other animation cases as needed...
                                default:
                                    brightness = 0;
                                    break;
}                            
                            if (brightness > final_brightness) {
                                final_brightness = brightness;
                                HSV effect_hsv = get_effect_color_hsv(base_hue, base_sat, base_val, color_type, 
                                                                     active_notes[note].color_id,
                                                                     active_notes[note].row, active_notes[note].col,
                                                                     row, col, elapsed, active_notes[note].is_live);
                                final_hue = effect_hsv.h;
                                final_sat = effect_hsv.s;
                            }
                        }
                    }
                }
                
                if (final_brightness > 0) {
                    uint8_t scaled_brightness = cap_brightness((final_brightness * base_val) / 255);
                    HSV hsv = {final_hue, final_sat, scaled_brightness};
                    RGB rgb = hsv_to_rgb(hsv);
                    rgb_matrix_set_color(led_index, rgb.r, rgb.g, rgb.b);
                }
            }
        }
    }
    
    return false;
}
// =============================================================================
// CUSTOM ANIMATION CONFIGURATION SYSTEM (UNCHANGED)
// =============================================================================

custom_animation_config_t custom_slots[NUM_CUSTOM_SLOTS] = {
    
    // NEW: Heat effects with TRUEKEY
    {LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_HEAT, LIVE_ANIM_SUSTAIN, false, BACKGROUND_AUTOLIGHT, 3, 68, true, 40, 180, 170},
    
    // NEW: Wide + simple with TRUEKEY (max speed)
    {LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_WIDE1, LIVE_ANIM_NONE, false, BACKGROUND_BPM_ALL_2, 3, 72, true, 75, 255, 255},
    // Keep 1: Full coverage with moving dots
    {LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS2_ROW, LIVE_ANIM_MOVING_DOTS2_COL, false, BACKGROUND_HUE_PENDULUM, 3, 28, true, 35, 200, 190},
    
    // Keep 3: Full + horizontal macro
    {LIVE_POS_TRUEKEY, MACRO_POS_NOTE_ROW_COL0, LIVE_ANIM_OUTWARD_BURST_1, LIVE_ANIM_VOLUME_LEFT_RIGHT_2, false, BACKGROUND_DIAGONAL_WAVE, 3, 42, true, 50, 220, 200},
    
    // Keep 9: Dot positions with moving effects
    {LIVE_POS_NOTE_CORNER_DOTS, MACRO_POS_LOOP_EDGE_DOTS, LIVE_ANIM_MOVING_COLUMNS_3_2, LIVE_ANIM_MOVING_ROWS_3_2, false, BACKGROUND_CYCLE_ALL, 3, 48, true, 20, 170, 150},
    
    // Keep 10: Modified - macro effect to volume row medium and note row left
    {LIVE_POS_NOTE_ROW_COL13, MACRO_POS_NOTE_ROW_COL0, LIVE_ANIM_VOLUME_LEFT_RIGHT_3, LIVE_ANIM_VOLUME_LEFT_RIGHT_2, false, BACKGROUND_DIAGONAL_WAVE_DUAL_COLOR_DESAT, 3, 36, true, 50, 160, 190},
    
    // Keep 11: Changed background to autolight
    {LIVE_POS_ZONE, MACRO_POS_LOOP_BLOCK_3X3, LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL, LIVE_ANIM_MOVING_DOTS1_ROW_SOLO, false, BACKGROUND_AUTOLIGHT, 3, 2, true, 50, 200, 180},
    
    // Keep 12: Changed live to solo version, macro to horizontal dots long
    {LIVE_POS_NOTE_ALL_DOTS, MACRO_POS_NOTE_CORNER_DOTS, LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_SOLO, LIVE_ANIM_MOVING_DOTS2_ROW, false, BACKGROUND_WAVE_LEFT_RIGHT, 3, 29, true, 15, 130, 160},
    
    // Keep 14: Vertical live, horizontal macro
    {LIVE_POS_NOTE_COL_ROW0, MACRO_POS_NOTE_ROW_MIXED, LIVE_ANIM_VOLUME_UP_DOWN_1_WIDE, LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE, false, BACKGROUND_BAND_SPIRAL_VAL_DESAT, 3, 52, true, 35, 180, 200},
    
    // Keep 15: Full coverage with diagonal effects
    {LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE, LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE, false, BACKGROUND_BAND_PINWHEEL_VAL, 3, 41, true, 50, 220, 210},
    
    // Keep 17: Dot + block
    {LIVE_POS_CENTER_DOT, MACRO_POS_LOOP_BLOCK_CENTER, LIVE_ANIM_RIPPLE_MED_1_SOLO, LIVE_ANIM_CROSS, false, BACKGROUND_RAINBOW_PINWHEEL_DESAT, 3, 38, true, 25, 200, 180},
    
    // Keep 19: Changed live effect to ripple massive 1
    {LIVE_POS_NOTE_EDGE_DOTS, MACRO_POS_LOOP_CORNER_DOTS, LIVE_ANIM_RIPPLE_MASSIVE_1, LIVE_ANIM_RIPPLE_LARGE_1_SOLO, false, BACKGROUND_DIAGONAL_WAVE_DUAL_COLOR, 3, 25, true, 30, 190, 170},
    
    // Keep 20: Changed macro to 3 pixel rows and loop col bottom
    {LIVE_POS_NOTE_COL_MIXED, MACRO_POS_LOOP_COL_ROW4, LIVE_ANIM_MOVING_COLUMNS_3_1, LIVE_ANIM_MOVING_ROWS_3_1, false, BACKGROUND_HUE_BREATHING, 3, 59, true, 40, 150, 190},
    
    // Keep 21: Changed live speed to 30%
    {LIVE_POS_ZONE, MACRO_POS_TRUEKEY, LIVE_ANIM_RIPPLE_LARGE_2_SOLO, LIVE_COLLAPSING_BURST_LARGE_SOLO, false, BACKGROUND_STATIC_HUE2_DESAT, 3, 31, true, 50, 77, 200},
    
    // Keep 22: Horizontal live, vertical macro
    {LIVE_POS_NOTE_ROW_COL6, MACRO_POS_LOOP_COL_ROW4, LIVE_ANIM_MOVING_ROWS_8_2, LIVE_ANIM_VOLUME_UP_DOWN_2, false, BACKGROUND_BAND_SPIRAL_SAT_DESAT, 3, 17, true, 45, 170, 160},
    
    // Keep 24: Changed macro pos to loop row center
    {LIVE_POS_NOTE_COL_ROW4, MACRO_POS_LOOP_ROW_COL6, LIVE_ANIM_MOVING_ROWS_3_2, LIVE_ANIM_MOVING_ROWS_3_1_REVERSE, false, BACKGROUND_BAND_PINWHEEL_SAT, 3, 9, true, 50, 180, 170},
    
    // Keep 25: Dot pair
    {LIVE_POS_CENTER_DOT, MACRO_POS_NOTE_ALL_DOTS, LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_SOLO, LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE, false, BACKGROUND_HUE_PENDULUM_DESAT, 3, 53, true, 20, 160, 180},
    
    // Keep 26: Full + horizontal macro
    {LIVE_POS_ZONE, MACRO_POS_LOOP_ROW_COL6, LIVE_ANIM_MOVING_DOTS_ROW_2_REVERSE, LIVE_ANIM_VOLUME_LEFT_RIGHT_2_SOLO, false, BACKGROUND_CYCLE_ALL_DESAT, 3, 22, true, 50, 200, 190},
    
    // Keep 27: Horizontal live, vertical macro
    {LIVE_POS_NOTE_ROW_COL0, MACRO_POS_LOOP_COL_ROW0, LIVE_ANIM_VOLUME_LEFT_RIGHT_3_SOLO, LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE_SOLO, false, BACKGROUND_DIAGONAL_WAVE_REVERSE, 3, 46, true, 50, 140, 160},
    
    // Keep 28: Dot effects
    {LIVE_POS_NOTE_CORNER_DOTS, MACRO_POS_CENTER_DOT, LIVE_ANIM_MOVING_ROWS_8_1_REVERSE, LIVE_ANIM_RIPPLE_MED_1_SOLO, false, BACKGROUND_BAND_SPIRAL_VAL, 3, 35, true, 25, 190, 170},
    
    // Keep 29: Changed macro to collapsing column large and note col bottom
    {LIVE_POS_TRUEKEY, MACRO_POS_NOTE_COL_ROW4, LIVE_ANIM_WIDE1, LIVE_COLLAPSING_BURST_LARGE, false, BACKGROUND_BREATHING_DESAT, 3, 58, true, 40, 220, 200},
    
    // Keep 30: Changed to vertical dots long
    {LIVE_POS_NOTE_COL_ROW2, MACRO_POS_LOOP_ROW_ALT, LIVE_ANIM_MOVING_DOTS2_COL, LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE_SOLO, false, BACKGROUND_GRADIENT_UP_DOWN, 3, 11, true, 50, 150, 180},
    
    // Keep 31: Full + block
    {LIVE_POS_ZONE, MACRO_POS_LOOP_BLOCK_3X3, LIVE_ANIM_MOVING_DOTS1_COL, LIVE_ANIM_CROSS_2, false, BACKGROUND_HUE_WAVE_DESAT, 3, 40, true, 45, 210, 190},
    
    // Keep 32: Changed live anim to horizontal dots no fade
    {LIVE_POS_NOTE_ALL_DOTS, MACRO_POS_LOOP_EDGE_DOTS, LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE, LIVE_ANIM_MOVING_COLUMNS_3_1_REVERSE, false, BACKGROUND_AUTOLIGHT_HUE1_DESAT, 3, 27, true, 15, 170, 160},
    
    // Keep 34: Full coverage with orthogonal effects
    {LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2, LIVE_ANIM_MOVING_ROWS_8_2, false, BACKGROUND_BAND_SPIRAL_SAT, 3, 4, true, 50, 190, 180},
    
    // Keep 35: Dot + horizontal macro
    {LIVE_POS_CENTER_DOT, MACRO_POS_LOOP_ROW_COL0, LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE_SOLO, LIVE_ANIM_MOVING_ROWS_8_1, false, BACKGROUND_BAND_SPIRAL_VAL_DESAT, 3, 37, true, 30, 180, 160},
    
    // Keep 36: Vertical live, horizontal macro
    {LIVE_POS_NOTE_COL_ROW0, MACRO_POS_NOTE_ROW_MIXED, LIVE_ANIM_VOLUME_UP_DOWN_2_SOLO, LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE_SOLO, false, BACKGROUND_HUE_WAVE, 3, 20, true, 50, 140, 190},
    
    // Keep 38: Dot pair
    {LIVE_POS_NOTE_EDGE_DOTS, MACRO_POS_NOTE_CORNER_DOTS, LIVE_ANIM_RIPPLE_MASSIVE_1_SOLO, LIVE_ANIM_RIPPLE_MED_2_SOLO, false, BACKGROUND_BAND_SPIRAL_SAT_DESAT, 3, 13, true, 25, 160, 150},
    
    // Keep 40: Full + block
    {LIVE_POS_TRUEKEY, MACRO_POS_LOOP_BLOCK_CENTER, LIVE_ANIM_MOVING_DOTS1_ROW, LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE, false, BACKGROUND_GRADIENT_DIAGONAL_DESAT, 3, 32, true, 45, 230, 210},
    
    // Keep 43: Horizontal live, vertical macro
    {LIVE_POS_NOTE_ROW_COL6, MACRO_POS_NOTE_COL_ROW2, LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1, LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE, false, BACKGROUND_AUTOLIGHT_HUE2_DESAT, 3, 42, true, 40, 180, 190},
    
    // Keep 46: Vertical live, horizontal macro
    {LIVE_POS_NOTE_COL_ROW4, MACRO_POS_LOOP_ROW_COL6, LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE_SOLO, LIVE_ANIM_MOVING_ROWS_3_2_REVERSE, false, BACKGROUND_RAINBOW_MOVING_CHEVRON_DESAT, 3, 16, true, 50, 160, 180},
    
    // Keep 47: Dot + full
    {LIVE_POS_CENTER_DOT, MACRO_POS_ZONE, LIVE_ANIM_OUTWARD_BURST_1, LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE_SOLO, false, BACKGROUND_GRADIENT_LEFT_RIGHT_DESAT, 3, 39, true, 30, 200, 170},

    // NEW ENTRIES (with new positioning and updated color styles)
    
    // NEW: Collapsing burst effects with ZONE (half speed)
    {LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_COLLAPSING_BURST_LARGE, LIVE_COLLAPSING_BURST_SMALL_SOLO, false, BACKGROUND_AUTOLIGHT_HUE1, 3, 76, true, 30, 127, 127},
    
    // NEW: Horizontal dots short + long with center dot and loop row alt
    {LIVE_POS_CENTER_DOT, MACRO_POS_LOOP_ROW_ALT, LIVE_ANIM_MOVING_DOTS1_ROW, LIVE_ANIM_MOVING_DOTS2_ROW, false, BACKGROUND_BPM_ROW_2, 3, 80, true, 65, 160, 180},
    
    // NEW: Vertical dots long + short with column positions
    {LIVE_POS_NOTE_COL_ROW4, MACRO_POS_NOTE_COL_ROW0, LIVE_ANIM_MOVING_DOTS2_COL, LIVE_ANIM_MOVING_DOTS1_COL, false, BACKGROUND_AUTOLIGHT_HUE2, 3, 84, true, 50, 170, 150},
    
    // NEW: Horizontal dots from left to right
    {LIVE_POS_NOTE_ROW_COL0, MACRO_POS_NOTE_ROW_COL13, LIVE_ANIM_MOVING_DOTS1_ROW, LIVE_ANIM_MOVING_DOTS1_ROW, false, BACKGROUND_BPM_COLUMN_2, 3, 67, true, 60, 190, 170},
    
    // NEW: Vertical dots from bottom to top
    {LIVE_POS_NOTE_COL_ROW4, MACRO_POS_NOTE_COL_ROW0, LIVE_ANIM_MOVING_DOTS1_COL, LIVE_ANIM_MOVING_DOTS1_COL, false, BACKGROUND_AUTOLIGHT_HUE3, 3, 71, true, 40, 180, 160},
    
    // NEW: Mixed autolight BPM effects
    {LIVE_POS_ZONE, MACRO_POS_QUADRANT, LIVE_ANIM_RIPPLE_LARGE_1, LIVE_ANIM_VOLUME_LEFT_RIGHT_1, false, BACKGROUND_BPM_QUADRANTS_2, 3, 75, true, 80, 200, 190},
    
    // NEW: More autolight variations
    {LIVE_POS_TRUEKEY, MACRO_POS_CENTER_DOT, LIVE_ANIM_CROSS_2, LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL, false, BACKGROUND_AUTOLIGHT, 3, 79, true, 25, 210, 180},
    
    // NEW: BPM pulse fade variations
    {LIVE_POS_NOTE_ROW_COL6, MACRO_POS_LOOP_COL_ROW2, LIVE_ANIM_MOVING_ROWS_3_1, LIVE_ANIM_MOVING_COLUMNS_3_2, false, BACKGROUND_BPM_PULSE_FADE_2, 3, 83, true, 70, 150, 170},
    
    // NEW: More mixed positioning with autolight
    {LIVE_POS_NOTE_EDGE_DOTS, MACRO_POS_LOOP_BLOCK_3X3, LIVE_ANIM_OUTWARD_BURST_2, LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE_SOLO, false, BACKGROUND_AUTOLIGHT_HUE1, 3, 66, true, 35, 160, 140},
    
    // NEW: Column/row mixed with BMP
    {LIVE_POS_NOTE_COL_MIXED, MACRO_POS_LOOP_ROW_COL0, LIVE_ANIM_MOVING_COLUMNS_8_2, LIVE_ANIM_MOVING_ROWS_8_1, false, BACKGROUND_BPM_ALL_2, 3, 70, true, 85, 180, 200},
    
    // NEW: Final autolight entry
    {LIVE_POS_CENTER_DOT, MACRO_POS_TRUEKEY, LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE, LIVE_ANIM_RIPPLE_MED_1, false, BACKGROUND_AUTOLIGHT_HUE2, 3, 74, true, 30, 170, 160},

    // NEW ENTRIES WITH NEW POSITIONING OPTIONS
    
    // NEW: Zone2 with Snake positioning
    {LIVE_POS_ZONE2, MACRO_POS_SNAKE, LIVE_ANIM_RIPPLE_LARGE_1_SOLO, LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_SOLO, false, BACKGROUND_AUTOLIGHT, 3, 78, true, 45, 180, 170},
    
    // NEW: Zone3 with Center Block
    {LIVE_POS_ZONE3, MACRO_POS_CENTER_BLOCK, LIVE_ANIM_MOVING_DOTS2_ROW_SOLO, LIVE_ANIM_CROSS_2_SOLO, false, BACKGROUND_BPM_QUADRANTS_2, 3, 82, true, 75, 200, 190},
    
    // NEW: Count to 8 positioning
    {LIVE_POS_COUNT_TO_8, MACRO_POS_COUNT_TO_8, LIVE_ANIM_NONE_SOLO, LIVE_ANIM_NONE_SOLO, false, BACKGROUND_AUTOLIGHT_HUE3, 3, 65, true, 50, 160, 180},
    
    // NEW: Close dots positioning
    {LIVE_POS_NOTE_CLOSE_DOTS_1, MACRO_POS_NOTE_CLOSE_DOTS_2, LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL, LIVE_ANIM_OUTWARD_BURST_1, false, BACKGROUND_BPM_PULSE_FADE_2, 3, 69, true, 60, 170, 150},
    
    // NEW: Pitch mapping with Quadrant Dots
    {LIVE_POS_PITCH_MAPPING_1, MACRO_POS_QUADRANT_DOTS, LIVE_ANIM_OUTWARD_BURST_LARGE_2, LIVE_ANIM_RIPPLE_MED_2, false, BACKGROUND_AUTOLIGHT_HUE1, 3, 73, true, 40, 190, 160},
    
    // NEW: Snake with Loop Count to 8
    {LIVE_POS_SNAKE, MACRO_POS_COUNT_TO_8, LIVE_ANIM_MOVING_COLUMNS_8_1, LIVE_ANIM_MOVING_ROWS_8_2, false, BACKGROUND_BPM_ROW_2, 3, 77, true, 70, 150, 180},
    
    // NEW: Center Block with Zone2
    {LIVE_POS_CENTER_BLOCK, MACRO_POS_ZONE2, LIVE_ANIM_CROSS, LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL, false, BACKGROUND_AUTOLIGHT_HUE2, 3, 81, true, 35, 210, 170}
};

uint8_t current_custom_slot = 0;

// Parameter setting functions (unchanged)
void set_custom_slot_background_brightness(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value <= 100) {
        custom_slots[slot].background_brightness = value;
    }
}

void set_custom_slot_live_positioning(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 34) {  // Updated from 9 to 45 for new enum count
        custom_slots[slot].live_positioning = (live_note_positioning_t)value;
    }
}

void set_custom_slot_macro_positioning(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 46) {
        custom_slots[slot].macro_positioning = (macro_note_positioning_t)value;
    }
}

void set_custom_slot_live_animation(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 171) {
        custom_slots[slot].live_animation = (live_animation_t)value;
    }
}

void set_custom_slot_macro_animation(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 171) {
        custom_slots[slot].macro_animation = (macro_animation_t)value;
    }
}

void set_custom_slot_use_influence(uint8_t slot, bool value) {
    if (slot < NUM_CUSTOM_SLOTS) {
        custom_slots[slot].use_influence = value;
    }
}

void set_custom_slot_background_mode(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 121) {
        custom_slots[slot].background_mode = (background_mode_t)value;
    }
}

void set_custom_slot_pulse_mode(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 4) {
        custom_slots[slot].pulse_mode = value;
    }
}

void set_custom_slot_color_type(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 84) {
        custom_slots[slot].color_type = value;
    }
}

void set_custom_slot_enabled(uint8_t slot, bool value) {
    if (slot < NUM_CUSTOM_SLOTS) {
        custom_slots[slot].enabled = value;
    }
}

void set_custom_slot_live_speed_temp(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS) {
        custom_slots[slot].live_speed = value;
    }
}

void set_custom_slot_macro_speed_temp(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS) {
        custom_slots[slot].macro_speed = value;
    }
}

// Custom slot effect functions
static bool run_custom_animation(effect_params_t* params, uint8_t slot_number) {
    if (slot_number >= NUM_CUSTOM_SLOTS) return false;
    
    custom_animation_config_t* config = &custom_slots[slot_number];
    
    if (!config->enabled) {
        return false;
    }
    
    current_custom_slot = slot_number;
    
    return run_efficient_effect(params,
                               config->live_positioning,
                               config->macro_positioning,
                               config->live_animation,
                               config->macro_animation,
                               config->use_influence,
                               config->background_mode,
                               config->pulse_mode,
                               config->color_type,
                               config->background_brightness,
                               config->live_speed,
                               config->macro_speed);
}
typedef enum {
    CUSTOM_RANDOMIZE_OFF = 0,
    CUSTOM_RANDOMIZE_LOOP_1,    // Sequential patterns 1-50
    CUSTOM_RANDOMIZE_LOOP_2,    // Inclusion criteria system
    CUSTOM_RANDOMIZE_LOOP_3,    // No restrictions
    CUSTOM_RANDOMIZE_BPM_1,     // BPM version of Loop 1
    CUSTOM_RANDOMIZE_BPM_2,     // BPM version of Loop 2  
    CUSTOM_RANDOMIZE_BPM_3,     // BPM version of Loop 3
    CUSTOM_RANDOMIZE_NOTE_1,    // Note-driven version of Loop 1
    CUSTOM_RANDOMIZE_NOTE_2,    // Note-driven version of Loop 2
    CUSTOM_RANDOMIZE_NOTE_3,    // Note-driven version of Loop 3
} custom_randomize_mode_t;

// Global randomize state
static custom_randomize_mode_t current_randomize_mode = CUSTOM_RANDOMIZE_OFF;
static uint8_t randomize_bpm_beat_counter = 0;
static uint8_t randomize_note_counter = 0;  // Counter for note-driven randomization
static uint8_t sequential_pattern_index = 0; // For Loop 1 sequential patterns
static uint32_t randomize_seed = 0;

#define NOTE_RANDOMIZE_THRESHOLD 40  // Change randomization every 40 notes

// =============================================================================
// RANDOM SEED INITIALIZATION
// =============================================================================

void init_randomize_seed(void) {
    // Use timer or other hardware source for better entropy
    // This is a placeholder - replace with actual timer/hardware source
    randomize_seed = timer_read32() ^ (timer_read32() << 16);
    srand(randomize_seed);
}

// =============================================================================
// WEIGHTED POSITIONING GROUPS
// =============================================================================

// LIVE Position Groups
static const uint8_t live_full_coverage[] = {
    LIVE_POS_TRUEKEY, LIVE_POS_ZONE
};
static const uint8_t live_full_coverage_count = sizeof(live_full_coverage) / sizeof(live_full_coverage[0]);

static const uint8_t live_row_positions[] = {
    LIVE_POS_NOTE_ROW_COL0, LIVE_POS_NOTE_ROW_COL13, LIVE_POS_NOTE_ROW_COL6, LIVE_POS_NOTE_ROW_MIXED
};
static const uint8_t live_row_positions_count = sizeof(live_row_positions) / sizeof(live_row_positions[0]);

static const uint8_t live_column_positions[] = {
    LIVE_POS_NOTE_COL_ROW0, LIVE_POS_NOTE_COL_ROW4, LIVE_POS_NOTE_COL_ROW2, LIVE_POS_NOTE_COL_MIXED
};
static const uint8_t live_column_positions_count = sizeof(live_column_positions) / sizeof(live_column_positions[0]);

static const uint8_t live_dot_positions[] = {
    LIVE_POS_CENTER_DOT, LIVE_POS_NOTE_CORNER_DOTS, LIVE_POS_NOTE_EDGE_DOTS, LIVE_POS_NOTE_ALL_DOTS
};
static const uint8_t live_dot_positions_count = sizeof(live_dot_positions) / sizeof(live_dot_positions[0]);

// MACRO Position Groups
static const uint8_t macro_full_coverage[] = {
    MACRO_POS_TRUEKEY, MACRO_POS_ZONE, MACRO_POS_QUADRANT
};
static const uint8_t macro_full_coverage_count = sizeof(macro_full_coverage) / sizeof(macro_full_coverage[0]);

static const uint8_t macro_row_positions[] = {
    MACRO_POS_NOTE_ROW_COL0, MACRO_POS_NOTE_ROW_COL13, MACRO_POS_NOTE_ROW_COL6, MACRO_POS_NOTE_ROW_MIXED,
    MACRO_POS_LOOP_ROW_COL0, MACRO_POS_LOOP_ROW_COL13, MACRO_POS_LOOP_ROW_COL6, MACRO_POS_LOOP_ROW_ALT
};
static const uint8_t macro_row_positions_count = sizeof(macro_row_positions) / sizeof(macro_row_positions[0]);

static const uint8_t macro_column_positions[] = {
    MACRO_POS_NOTE_COL_ROW0, MACRO_POS_NOTE_COL_ROW4, MACRO_POS_NOTE_COL_ROW2, MACRO_POS_NOTE_COL_MIXED,
    MACRO_POS_LOOP_COL_ROW0, MACRO_POS_LOOP_COL_ROW4, MACRO_POS_LOOP_COL_ROW2
};
static const uint8_t macro_column_positions_count = sizeof(macro_column_positions) / sizeof(macro_column_positions[0]);

static const uint8_t macro_block_positions[] = {
    MACRO_POS_LOOP_BLOCK_3X3, MACRO_POS_LOOP_BLOCK_CENTER
};
static const uint8_t macro_block_positions_count = sizeof(macro_block_positions) / sizeof(macro_block_positions[0]);

static const uint8_t macro_dot_positions[] = {
    MACRO_POS_CENTER_DOT, MACRO_POS_NOTE_CORNER_DOTS, MACRO_POS_NOTE_EDGE_DOTS, MACRO_POS_NOTE_ALL_DOTS,
    MACRO_POS_LOOP_CORNER_DOTS, MACRO_POS_LOOP_EDGE_DOTS
};
static const uint8_t macro_dot_positions_count = sizeof(macro_dot_positions) / sizeof(macro_dot_positions[0]);

// =============================================================================
// INCLUSION CRITERIA ARRAYS - EFFECTS ALLOWED FOR EACH POSITION
// =============================================================================

// All effects allowed (for TRUEKEY and ZONE) - UNCHANGED
static const uint8_t all_effects[] = {
    0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 39, 41, 43, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 61, 63, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171
};
static const uint8_t all_effects_count = sizeof(all_effects) / sizeof(all_effects[0]);

// Effects for NOTE_ROW_COL0 and COL13 - UPDATED
// REMOVED: wide(2,3), wider(4,5), heatmap(6,7), cross short(12,13), criss cross(14,15), ripple med(38,39), outward burst(62,63,64,65)
static const uint8_t row_col0_col13_effects[] = {
    // Horizontal dots long (moving dots 2)
    18, 19,
    // Cross dots long  
    30, 31,
    // Ripple Large+ (40-43 in hierarchy = LARGE through MASSIVE)
    41, 43,
    // Reverse Ripple Med+ (45, 46, 47, 49, 50, 51 in hierarchy)
    49, 50, 51,
    // Expanding Row Long
    54, 55,
    // Volume Row Med+ (78-85 in hierarchy)
    78, 79, 80, 81, 82, 83, 84, 85,
    // Collapsing Row Med+ (98-105 in hierarchy)
    98, 99, 100, 101, 102, 103, 104, 105,
	
	146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
	
	130, 131, 132, 133, 134, 135, 136, 137, 114, 115, 116, 117, 118, 119, 120, 121, 110, 111, 112, 113 //coulumns
};
static const uint8_t row_col0_col13_effects_count = sizeof(row_col0_col13_effects) / sizeof(row_col0_col13_effects[0]);

// Effects for NOTE_ROW_COL6 - UPDATED
// REMOVED: wide(2,3), wider(4,5), heatmap(6,7)
static const uint8_t row_col6_effects[] = {
    // Horizontal dots (both short and long)
    16, 17, 18, 19,
    // Diagonal dots
    24, 25, 26, 27,
    // Cross dots (both short and long)
    28, 29, 30, 31,
    // Ripple (all sizes - short versions now allowed)
    37, 39, 41, 43,
    // Reverse Ripple (all sizes)
    48, 49, 50, 51,
    // Expanding Row (both short and long)
    52, 53, 54, 55,
    // Outward Burst (all sizes)
    61, 63, 65,
    // Volume Row (all sizes)
    74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85,
    // Collapsing Row (all sizes)
    86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105,
	
	146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
	
	130, 131, 132, 133, 134, 135, 136, 137, 114, 115, 116, 117, 118, 119, 120, 121, 110, 111, 112, 113 //coulumns
};
static const uint8_t row_col6_effects_count = sizeof(row_col6_effects) / sizeof(row_col6_effects[0]);

// Effects for NOTE_COL_ROW0 and ROW4 - UPDATED
// REMOVED: wide(2,3), wider(4,5), heatmap(6,7), cross short(12,13), criss cross(14,15), ripple med(38,39), outward burst(62,63,64,65)
static const uint8_t col_row0_row4_effects[] = {
    // Vertical dots long (moving dots 2)
    22, 23,
    // Cross dots long
    30, 31,
    // Ripple Large+ (40-43 in hierarchy = LARGE through MASSIVE)
    41, 43,
    // Reverse Ripple Med+ (45, 46, 47, 49, 50, 51)
    49, 50, 51,
    // Expanding Column Long
    58, 59,
    // Volume Column Large+ (70-73 in hierarchy)
    70, 71, 72, 73,
    // Collapsing Column Large+ (90-93 in hierarchy)
    90, 91, 92, 93,
	
	146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
	
	138, 139, 140, 141, 142, 143, 144, 145, 122, 123, 124, 125, 126, 127, 128, 129, 106, 107, 108, 109, // rows
};
static const uint8_t col_row0_row4_effects_count = sizeof(col_row0_row4_effects) / sizeof(col_row0_row4_effects[0]);

// Effects for NOTE_COL_ROW2 - UPDATED  
// REMOVED: wide(2,3), wider(4,5), heatmap(6,7)
static const uint8_t col_row2_effects[] = {
    // Cross effects
    12, 13, 14, 15,
    // Vertical dots (both short and long)
    20, 21, 22, 23,
    // Diagonal dots
    24, 25, 26, 27,
    // Cross dots (both short and long)
    28, 29, 30, 31,
    // Diagonal burst
    32, 33,
    // Criss cross dots
    34, 35,
    // Ripple (all sizes)
    37, 39, 41, 43,
    // Reverse Ripple (all sizes)
    48, 49, 50, 51,
    // Expanding Column (both short and long)
    56, 57, 58, 59,
    // Outward Burst (all sizes)
    61, 63, 65,
    // Volume Column (all sizes)
    66, 67, 68, 69, 70, 71, 72, 73,
    // Collapsing Column (all sizes)
    86, 87, 88, 89, 90, 91, 92, 93,
	
	146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
	
	138, 139, 140, 141, 142, 143, 144, 145, 122, 123, 124, 125, 126, 127, 128, 129, 106, 107, 108, 109, // rows
};
static const uint8_t col_row2_effects_count = sizeof(col_row2_effects) / sizeof(col_row2_effects[0]);

// Effects for CENTER_DOT, NOTE_CORNER_DOTS, NOTE_EDGE_DOTS, NOTE_ALL_DOTS - UPDATED
// REMOVED: wide(2,3), wider(4,5), cross short(12,13), criss cross(14,15)
static const uint8_t dot_effects[] = {
    // Moving dots (all - no short/small restriction mentioned for dots)
    16, 17, 18, 19, 20, 21, 22, 23,
    // Diagonal dots
    24, 25, 26, 27,
    // Cross dots (long versions only - no short/small)
    30, 31,
    // Diagonal burst
    32, 33,
    // Criss cross dots
    34, 35,
    // Ripple (med+ only - no small)
    39, 41, 43,
    // Reverse Ripple (med+ only - no small)
    49, 50, 51,
    // Expanding (long versions only)
    54, 55, 58, 59,
    // Outward Burst (med+ only - no small)
    63, 65,
    // Volume (med+ only - no small)
    70, 71, 72, 73, 78, 79, 80, 81, 82, 83, 84, 85,
    // Collapsing (med+ only - no small)
    90, 91, 92, 93, 98, 99, 100, 101, 102, 103, 104, 105,
	
	146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
	
	138, 139, 140, 141, 142, 143, 144, 145, 122, 123, 124, 125, 126, 127, 128, 129, 106, 107, 108, 109, // rows
	
	130, 131, 132, 133, 134, 135, 136, 137, 114, 115, 116, 117, 118, 119, 120, 121, 110, 111, 112, 113 //coulumns
};
static const uint8_t dot_effects_count = sizeof(dot_effects) / sizeof(dot_effects[0]);

// Position exclusions (positions that are completely excluded)
static const uint8_t excluded_live_positions[] = {
    LIVE_POS_QUADRANT, LIVE_POS_TOP_DOT, LIVE_POS_LEFT_DOT, LIVE_POS_RIGHT_DOT,
    LIVE_POS_BOTTOM_DOT, LIVE_POS_TOP_LEFT_DOT, LIVE_POS_TOP_RIGHT_DOT,
    LIVE_POS_BOTTOM_LEFT_DOT, LIVE_POS_BOTTOM_RIGHT_DOT
};
static const uint8_t excluded_live_positions_count = sizeof(excluded_live_positions) / sizeof(excluded_live_positions[0]);

static const uint8_t excluded_macro_positions[] = {
    MACRO_POS_TOP_DOT, MACRO_POS_LEFT_DOT, MACRO_POS_RIGHT_DOT,
    MACRO_POS_BOTTOM_DOT, MACRO_POS_TOP_LEFT_DOT, MACRO_POS_TOP_RIGHT_DOT,
    MACRO_POS_BOTTOM_LEFT_DOT, MACRO_POS_BOTTOM_RIGHT_DOT
};
static const uint8_t excluded_macro_positions_count = sizeof(excluded_macro_positions) / sizeof(excluded_macro_positions[0]);

// BPM background exclusions (only basic BPM, no _1+ variants)
static const uint8_t excluded_bpm_backgrounds[] = {
    BACKGROUND_BPM_PULSE_FADE_1, BACKGROUND_BPM_PULSE_FADE_2, BACKGROUND_BPM_PULSE_FADE_3,
    BACKGROUND_BPM_PULSE_FADE_4, BACKGROUND_BPM_PULSE_FADE_5,
    BACKGROUND_BPM_QUADRANTS_1, BACKGROUND_BPM_QUADRANTS_2, BACKGROUND_BPM_QUADRANTS_3,
    BACKGROUND_BPM_QUADRANTS_4, BACKGROUND_BPM_QUADRANTS_5, 
    BACKGROUND_BPM_ROW_1, BACKGROUND_BPM_ROW_2, BACKGROUND_BPM_ROW_3, BACKGROUND_BPM_ROW_4,
    BACKGROUND_BPM_ROW_5, BACKGROUND_BPM_COLUMN_1, BACKGROUND_BPM_COLUMN_2, BACKGROUND_BPM_COLUMN_3,
    BACKGROUND_BPM_COLUMN_4, BACKGROUND_BPM_COLUMN_5, BACKGROUND_BPM_ALL_1, BACKGROUND_BPM_ALL_2,
    BACKGROUND_BPM_ALL_3, BACKGROUND_BPM_ALL_4, BACKGROUND_BPM_ALL_5
};
static const uint8_t excluded_bpm_backgrounds_count = sizeof(excluded_bpm_backgrounds) / sizeof(excluded_bpm_backgrounds[0]);

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

static bool is_value_excluded(uint8_t value, const uint8_t* exclusion_array, uint8_t exclusion_count) {
    for (uint8_t i = 0; i < exclusion_count; i++) {
        if (value == exclusion_array[i]) {
            return true;
        }
    }
    return false;
}

static uint8_t get_random_value_with_exclusions(uint8_t max_value, const uint8_t* exclusion_array, uint8_t exclusion_count) {
    uint8_t attempts = 0;
    uint8_t random_value;
    
    do {
        random_value = rand() % max_value;
        attempts++;
    } while (is_value_excluded(random_value, exclusion_array, exclusion_count) && attempts < 100);
    
    return random_value;
}

static uint8_t get_random_from_array(const uint8_t* array, uint8_t array_count) {
    if (array_count == 0) return 0;
    uint8_t index = rand() % array_count;
    return array[index];
}

static uint8_t get_random_value(uint8_t max_value) {
    return rand() % max_value;
}

// =============================================================================
// WEIGHTED POSITION SELECTION FUNCTIONS
// =============================================================================

static uint8_t get_weighted_live_position(void) {
    uint8_t random_percent = rand() % 100;
    
    if (random_percent < 25) {
        // Full Coverage - 25%
        return get_random_from_array(live_full_coverage, live_full_coverage_count);
    } else if (random_percent < 50) {
        // Row Positions - 25%
        return get_random_from_array(live_row_positions, live_row_positions_count);
    } else if (random_percent < 75) {
        // Column Positions - 25%
        return get_random_from_array(live_column_positions, live_column_positions_count);
    } else {
        // Dot Positions - 25%
        return get_random_from_array(live_dot_positions, live_dot_positions_count);
    }
}

static uint8_t get_weighted_macro_position(void) {
    uint8_t random_percent = rand() % 100;
    
    if (random_percent < 20) {
        // Full Coverage - 20%
        return get_random_from_array(macro_full_coverage, macro_full_coverage_count);
    } else if (random_percent < 50) {
        // Row Positions - 30%
        return get_random_from_array(macro_row_positions, macro_row_positions_count);
    } else if (random_percent < 75) {
        // Column Positions - 25%
        return get_random_from_array(macro_column_positions, macro_column_positions_count);
    } else if (random_percent < 85) {
        // Block Positions - 10%
        return get_random_from_array(macro_block_positions, macro_block_positions_count);
    } else {
        // Dot Positions - 15%
        return get_random_from_array(macro_dot_positions, macro_dot_positions_count);
    }
}

// Get allowed effects for a given position
static const uint8_t* get_allowed_effects_for_position(uint8_t position, uint8_t* count, bool is_live) {
    if (is_live) {
        switch (position) {
            case LIVE_POS_TRUEKEY:
            case LIVE_POS_ZONE:
                *count = all_effects_count;
                return all_effects;
                
            case LIVE_POS_NOTE_ROW_COL0:
            case LIVE_POS_NOTE_ROW_COL13:
                *count = row_col0_col13_effects_count;
                return row_col0_col13_effects;
                
            case LIVE_POS_NOTE_ROW_COL6:
            case LIVE_POS_NOTE_ROW_MIXED:
                *count = row_col6_effects_count;
                return row_col6_effects;
                
            case LIVE_POS_NOTE_COL_ROW0:
            case LIVE_POS_NOTE_COL_ROW4:
                *count = col_row0_row4_effects_count;
                return col_row0_row4_effects;
                
            case LIVE_POS_NOTE_COL_ROW2:
            case LIVE_POS_NOTE_COL_MIXED:
                *count = col_row2_effects_count;
                return col_row2_effects;
                
            case LIVE_POS_CENTER_DOT:
            case LIVE_POS_NOTE_CORNER_DOTS:
            case LIVE_POS_NOTE_EDGE_DOTS:
            case LIVE_POS_NOTE_ALL_DOTS:
                *count = dot_effects_count;
                return dot_effects;
                
            default:
                *count = 0;
                return NULL;
        }
    } else {
        // Macro positions - now with updated LOOP restrictions
        switch (position) {
            case MACRO_POS_TRUEKEY:
            case MACRO_POS_ZONE:
            case MACRO_POS_QUADRANT: // Macro quadrant not excluded
                *count = all_effects_count;
                return all_effects;
                
            case MACRO_POS_NOTE_ROW_COL0:
            case MACRO_POS_NOTE_ROW_COL13:
                *count = row_col0_col13_effects_count;
                return row_col0_col13_effects;
                
            case MACRO_POS_NOTE_ROW_COL6:
            case MACRO_POS_NOTE_ROW_MIXED:
            case MACRO_POS_LOOP_ROW_ALT: // Same as row_col6
                *count = row_col6_effects_count;
                return row_col6_effects;
                
            case MACRO_POS_NOTE_COL_ROW0:
            case MACRO_POS_NOTE_COL_ROW4:
            case MACRO_POS_LOOP_COL_ROW0:
            case MACRO_POS_LOOP_COL_ROW4:
                *count = col_row0_row4_effects_count;
                return col_row0_row4_effects;
                
            case MACRO_POS_NOTE_COL_ROW2:
            case MACRO_POS_NOTE_COL_MIXED:
            case MACRO_POS_LOOP_COL_ROW2:
                *count = col_row2_effects_count;
                return col_row2_effects;
                
            case MACRO_POS_CENTER_DOT:
            case MACRO_POS_NOTE_CORNER_DOTS:
            case MACRO_POS_NOTE_EDGE_DOTS:
            case MACRO_POS_NOTE_ALL_DOTS:
            case MACRO_POS_LOOP_CORNER_DOTS: // Same as note counterpart
            case MACRO_POS_LOOP_EDGE_DOTS:   // Same as note counterpart
                *count = dot_effects_count;
                return dot_effects;
                
            // LOOP ROW positions - now follow same restrictions as NOTE counterparts
            case MACRO_POS_LOOP_ROW_COL0:
            case MACRO_POS_LOOP_ROW_COL13:
                *count = row_col0_col13_effects_count;
                return row_col0_col13_effects;
                
            case MACRO_POS_LOOP_ROW_COL6:
                *count = row_col6_effects_count;
                return row_col6_effects;
            
            // Other macro positions get all effects
            case MACRO_POS_LOOP_BLOCK_3X3:
            case MACRO_POS_LOOP_BLOCK_CENTER:
                *count = all_effects_count;
                return all_effects;
                
            default:
                *count = 0;
                return NULL;
        }
    }
}

// =============================================================================
// RANDOMIZATION FUNCTIONS FOR EACH MODE
// =============================================================================

// Random pattern selection for Note 1 (randomly picks from slots 1-50 and randomizes color)
static void randomize_pattern_with_color(uint8_t current_slot) {
    // Randomly pick from slots 1-50 (0-indexed: slots 0-49)
    uint8_t random_pattern_slot = rand() % 49;  // 0-49
    
    // Copy configuration from the random pattern slot to current slot
    custom_slots[current_slot] = custom_slots[random_pattern_slot];
    
    // Randomize RGB color (hue)
    uint8_t new_hue = rand() & 0xFF;
    rgb_matrix_sethsv_noeeprom(new_hue, rgb_matrix_get_sat(), rgb_matrix_get_val());
}

// Inclusion criteria system for Loop 2 - NOW WITH WEIGHTED POSITIONING
static void randomize_with_criteria(uint8_t slot) {
    // Use weighted position selection instead of uniform random
    uint8_t live_pos = get_weighted_live_position();
    uint8_t macro_pos = get_weighted_macro_position();
    
    // Get allowed effects for selected positions
    uint8_t live_effects_count;
    const uint8_t* live_effects = get_allowed_effects_for_position(live_pos, &live_effects_count, true);
    
    uint8_t macro_effects_count;
    const uint8_t* macro_effects = get_allowed_effects_for_position(macro_pos, &macro_effects_count, false);
    
    // Select random effects from allowed arrays
    uint8_t live_anim = (live_effects_count > 0) ? get_random_from_array(live_effects, live_effects_count) : 0;
    uint8_t macro_anim = (macro_effects_count > 0) ? get_random_from_array(macro_effects, macro_effects_count) : 0;
    
    // Apply randomization
    set_custom_slot_live_positioning(slot, live_pos);
    set_custom_slot_macro_positioning(slot, macro_pos);
    set_custom_slot_live_animation(slot, live_anim);
    set_custom_slot_macro_animation(slot, macro_anim);
    
    // Randomize other parameters
    uint8_t color_type = get_random_value(84);
    set_custom_slot_color_type(slot, color_type);
    
    uint8_t new_hue = rand() & 0xFF;
    rgb_matrix_sethsv_noeeprom(new_hue, rgb_matrix_get_sat(), rgb_matrix_get_val());
    
    uint8_t background = get_random_value_with_exclusions(121, excluded_bpm_backgrounds, excluded_bpm_backgrounds_count);
    set_custom_slot_background_mode(slot, background);
    
    uint8_t live_speed = rand() & 0xFF;
    set_custom_slot_live_speed_temp(slot, live_speed);
    
    uint8_t macro_speed = rand() & 0xFF;
    set_custom_slot_macro_speed_temp(slot, macro_speed);
}

// No restrictions for Loop 3
static void randomize_no_restrictions(uint8_t slot) {
    // Randomize everything without restrictions (except exclude HEAT/SUSTAIN)
    uint8_t live_anim;
        live_anim = get_random_value(170);

    
    uint8_t macro_anim;

        macro_anim = get_random_value(170);

    
    set_custom_slot_live_animation(slot, live_anim);
    set_custom_slot_macro_animation(slot, macro_anim);
    
    uint8_t live_pos = get_random_value(33);
    set_custom_slot_live_positioning(slot, live_pos);
    
    uint8_t macro_pos = get_random_value(46);
    set_custom_slot_macro_positioning(slot, macro_pos);
    
    uint8_t color_type = get_random_value(84);
    set_custom_slot_color_type(slot, color_type);
    
    uint8_t new_hue = rand() & 0xFF;
    rgb_matrix_sethsv_noeeprom(new_hue, rgb_matrix_get_sat(), rgb_matrix_get_val());
    
    uint8_t background = get_random_value(121);
    set_custom_slot_background_mode(slot, background);
    
    uint8_t live_speed = rand() & 0xFF;
    set_custom_slot_live_speed_temp(slot, live_speed);
    
    uint8_t macro_speed = rand() & 0xFF;
    set_custom_slot_macro_speed_temp(slot, macro_speed);
}

// =============================================================================
// MAIN RANDOMIZE FUNCTION
// =============================================================================

#define RANDOMIZE_SLOT 49  // Slot 12 (0-indexed)

// Modify internal_randomize to always work on the randomize slot
static void internal_randomize(void) {
    uint8_t slot = RANDOMIZE_SLOT;  // Always use slot 12
    
    switch (current_randomize_mode) {
        case CUSTOM_RANDOMIZE_LOOP_1:
        case CUSTOM_RANDOMIZE_BPM_1:
		case CUSTOM_RANDOMIZE_NOTE_1:
            randomize_pattern_with_color(slot);
            break;
            
        case CUSTOM_RANDOMIZE_LOOP_2:
        case CUSTOM_RANDOMIZE_BPM_2:
        case CUSTOM_RANDOMIZE_NOTE_2:
            randomize_with_criteria(slot);
            break;
            
        case CUSTOM_RANDOMIZE_LOOP_3:
        case CUSTOM_RANDOMIZE_BPM_3:
        case CUSTOM_RANDOMIZE_NOTE_3:
            randomize_no_restrictions(slot);
            break;
            
        default:
            break;
    }
}

// External randomize function (called from loop system) - ONLY works for LOOP modes
void randomize_order(void) {
    // Check if current RGB effect is one of the LOOP randomize effects
    uint8_t current_effect = rgb_matrix_get_mode();
    if (current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_1 && 
        current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_2 && 
        current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_3) {
        return;  // Only work if currently running a LOOP randomize effect
    }
    internal_randomize();
}

// =============================================================================
// BPM RANDOMIZE UPDATE FUNCTION
// =============================================================================

static void update_bpm_randomize(void) {
    // Check if current RGB effect is one of the BPM randomize effects
    uint8_t current_effect = rgb_matrix_get_mode();
    if (current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_1 && 
        current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_2 && 
        current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_3) {
        return;  // Only work if currently running a BPM randomize effect
    }
    
    // Check if BPM system is active and we have a beat
    if (bpm_flash_state && !last_bpm_flash_state) {
        randomize_bpm_beat_counter++;
        
        // Trigger randomization every 16 beats
        if (randomize_bpm_beat_counter >= 8) {
            randomize_bpm_beat_counter = 0;
            internal_randomize();
        }
    }
    
    // UPDATE: Add this line to prevent multiple detections of the same beat
    //last_bpm_flash_state = bpm_flash_state;
}

// =============================================================================
// NOTE-DRIVEN RANDOMIZE FUNCTIONS
// =============================================================================

// Function to be called whenever a note is pressed (call this from your note handling code)
void on_note_pressed(void) {
    // Check if current RGB effect is one of the NOTE randomize effects
    uint8_t current_effect = rgb_matrix_get_mode();
    if (current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_1 && 
        current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_2 && 
        current_effect != RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_3) {
        return;  // Only work if currently running a NOTE randomize effect
    }
    
    randomize_note_counter++;
    
    // Trigger randomization every 40 notes
    if (randomize_note_counter >= NOTE_RANDOMIZE_THRESHOLD) {
        randomize_note_counter = 0;
        internal_randomize();
    }
}

// Function to reset note counter (useful when switching modes)
void reset_note_randomize_counter(void) {
    randomize_note_counter = 0;
}

// Function to get current note count (for debugging/display)
uint8_t get_note_randomize_counter(void) {
    return randomize_note_counter;
}

// =============================================================================
// UTILITY FUNCTIONS FOR EXTERNAL USE
// =============================================================================

// Get current randomize mode (based on RGB effect mode)
custom_randomize_mode_t get_current_randomize_mode(void) {
    uint8_t current_effect = rgb_matrix_get_mode();
    
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_1) return CUSTOM_RANDOMIZE_LOOP_1;
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_2) return CUSTOM_RANDOMIZE_LOOP_2;
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_3) return CUSTOM_RANDOMIZE_LOOP_3;
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_1) return CUSTOM_RANDOMIZE_BPM_1;
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_2) return CUSTOM_RANDOMIZE_BPM_2;
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_3) return CUSTOM_RANDOMIZE_BPM_3;
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_1) return CUSTOM_RANDOMIZE_NOTE_1;
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_2) return CUSTOM_RANDOMIZE_NOTE_2;
    if (current_effect == RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_3) return CUSTOM_RANDOMIZE_NOTE_3;
    
    return CUSTOM_RANDOMIZE_OFF;
}

// Check if randomize mode is active (based on RGB effect mode)
bool is_randomize_mode_active(void) {
    return get_current_randomize_mode() != CUSTOM_RANDOMIZE_OFF;
}

// Set randomize mode (for debugging/testing) - This just switches RGB effect
void set_randomize_mode(custom_randomize_mode_t mode) {
    switch (mode) {
        case CUSTOM_RANDOMIZE_LOOP_1:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_1);
            break;
        case CUSTOM_RANDOMIZE_LOOP_2:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_2);
            break;
        case CUSTOM_RANDOMIZE_LOOP_3:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_LOOP_3);
            break;
        case CUSTOM_RANDOMIZE_BPM_1:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_1);
            break;
        case CUSTOM_RANDOMIZE_BPM_2:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_2);
            break;
        case CUSTOM_RANDOMIZE_BPM_3:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_BPM_3);
            break;
        case CUSTOM_RANDOMIZE_NOTE_1:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_1);
            break;
        case CUSTOM_RANDOMIZE_NOTE_2:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_2);
            break;
        case CUSTOM_RANDOMIZE_NOTE_3:
            rgb_matrix_mode_noeeprom(RGB_MATRIX_CUSTOM_LOOP_CUSTOM_RANDOMIZE_MANUAL_3);
            break;
        default:
            // Turn off randomize by switching to a regular effect
            break;
    }
}

// Modify run_randomize_effect to use randomize slot and initialize seed
static bool run_randomize_effect(effect_params_t* params, custom_randomize_mode_t mode) {
    current_randomize_mode = mode;
    
    if (params->init) {
        // Initialize random seed for better randomness
        init_randomize_seed();
        
        randomize_bpm_beat_counter = 0;
        randomize_note_counter = 0; // Reset note counter
        sequential_pattern_index = 0;
        last_bpm_flash_state = false; // Reset BPM state tracking
        
        // Trigger initial randomization (note-driven modes start immediately)
        if (mode != CUSTOM_RANDOMIZE_OFF) {
            internal_randomize();
        }
    }
    
    update_bpm_randomize();
    
    // Always run slot 12 for randomize effects
    return run_custom_animation(params, RANDOMIZE_SLOT);
}

// Loop randomize effects
bool LOOP_CUSTOM_RANDOMIZE_LOOP_1(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_LOOP_1);
}

bool LOOP_CUSTOM_RANDOMIZE_LOOP_2(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_LOOP_2);
}

bool LOOP_CUSTOM_RANDOMIZE_LOOP_3(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_LOOP_3);
}

// BPM randomize effects
bool LOOP_CUSTOM_RANDOMIZE_BPM_1(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_BPM_1);
}

bool LOOP_CUSTOM_RANDOMIZE_BPM_2(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_BPM_2);
}

bool LOOP_CUSTOM_RANDOMIZE_BPM_3(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_BPM_3);
}

// Note-driven randomize effects
bool LOOP_CUSTOM_RANDOMIZE_MANUAL_1(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_NOTE_1);
}

bool LOOP_CUSTOM_RANDOMIZE_MANUAL_2(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_NOTE_2);
}

bool LOOP_CUSTOM_RANDOMIZE_MANUAL_3(effect_params_t* params) {
    return run_randomize_effect(params, CUSTOM_RANDOMIZE_NOTE_3);
}
// =============================================================================
// UTILITY FUNCTIONS FOR EXTERNAL USE
// =============================================================================

// Manual trigger for testing (works for all modes)
void trigger_manual_randomize(void) {
    if (current_randomize_mode != CUSTOM_RANDOMIZE_OFF) {
        internal_randomize();
    }
}

// Individual slot effect functions
bool LOOP_CUSTOM_SLOT_0(effect_params_t* params) {
    return run_custom_animation(params, 0);
}

bool LOOP_CUSTOM_SLOT_1(effect_params_t* params) {
    return run_custom_animation(params, 1);
}

bool LOOP_CUSTOM_SLOT_2(effect_params_t* params) {
    return run_custom_animation(params, 2);
}

bool LOOP_CUSTOM_SLOT_3(effect_params_t* params) {
    return run_custom_animation(params, 3);
}

bool LOOP_CUSTOM_SLOT_4(effect_params_t* params) {
    return run_custom_animation(params, 4);
}

bool LOOP_CUSTOM_SLOT_5(effect_params_t* params) {
    return run_custom_animation(params, 5);
}

bool LOOP_CUSTOM_SLOT_6(effect_params_t* params) {
    return run_custom_animation(params, 6);
}

bool LOOP_CUSTOM_SLOT_7(effect_params_t* params) {
    return run_custom_animation(params, 7);
}

bool LOOP_CUSTOM_SLOT_8(effect_params_t* params) {
    return run_custom_animation(params, 8);
}

bool LOOP_CUSTOM_SLOT_9(effect_params_t* params) {
    return run_custom_animation(params, 9);
}

bool LOOP_CUSTOM_SLOT_10(effect_params_t* params) {
    return run_custom_animation(params, 10);
}

bool LOOP_CUSTOM_SLOT_11(effect_params_t* params) {
    return run_custom_animation(params, 11);
}

bool LOOP_CUSTOM_SLOT_12(effect_params_t* params) {
    return run_custom_animation(params, 12);
}

bool LOOP_CUSTOM_SLOT_13(effect_params_t* params) {
    return run_custom_animation(params, 13);
}

bool LOOP_CUSTOM_SLOT_14(effect_params_t* params) {
    return run_custom_animation(params, 14);
}

bool LOOP_CUSTOM_SLOT_15(effect_params_t* params) {
    return run_custom_animation(params, 15);
}

bool LOOP_CUSTOM_SLOT_16(effect_params_t* params) {
    return run_custom_animation(params, 16);
}

bool LOOP_CUSTOM_SLOT_17(effect_params_t* params) {
    return run_custom_animation(params, 17);
}

bool LOOP_CUSTOM_SLOT_18(effect_params_t* params) {
    return run_custom_animation(params, 18);
}

bool LOOP_CUSTOM_SLOT_19(effect_params_t* params) {
    return run_custom_animation(params, 19);
}

bool LOOP_CUSTOM_SLOT_20(effect_params_t* params) {
    return run_custom_animation(params, 20);
}

bool LOOP_CUSTOM_SLOT_21(effect_params_t* params) {
    return run_custom_animation(params, 21);
}

bool LOOP_CUSTOM_SLOT_22(effect_params_t* params) {
    return run_custom_animation(params, 22);
}

bool LOOP_CUSTOM_SLOT_23(effect_params_t* params) {
    return run_custom_animation(params, 23);
}

bool LOOP_CUSTOM_SLOT_24(effect_params_t* params) {
    return run_custom_animation(params, 24);
}
bool LOOP_CUSTOM_SLOT_25(effect_params_t* params) {
    return run_custom_animation(params, 25);
}
bool LOOP_CUSTOM_SLOT_26(effect_params_t* params) {
    return run_custom_animation(params, 26);
}
bool LOOP_CUSTOM_SLOT_27(effect_params_t* params) {
    return run_custom_animation(params, 27);
}
bool LOOP_CUSTOM_SLOT_28(effect_params_t* params) {
    return run_custom_animation(params, 28);
}
bool LOOP_CUSTOM_SLOT_29(effect_params_t* params) {
    return run_custom_animation(params, 29);
}
bool LOOP_CUSTOM_SLOT_30(effect_params_t* params) {
    return run_custom_animation(params, 30);
}
bool LOOP_CUSTOM_SLOT_31(effect_params_t* params) {
    return run_custom_animation(params, 31);
}
bool LOOP_CUSTOM_SLOT_32(effect_params_t* params) {
    return run_custom_animation(params, 32);
}
bool LOOP_CUSTOM_SLOT_33(effect_params_t* params) {
    return run_custom_animation(params, 33);
}
bool LOOP_CUSTOM_SLOT_34(effect_params_t* params) {
    return run_custom_animation(params, 34);
}
bool LOOP_CUSTOM_SLOT_35(effect_params_t* params) {
    return run_custom_animation(params, 35);
}
bool LOOP_CUSTOM_SLOT_36(effect_params_t* params) {
    return run_custom_animation(params, 36);
}
bool LOOP_CUSTOM_SLOT_37(effect_params_t* params) {
    return run_custom_animation(params, 37);
}
bool LOOP_CUSTOM_SLOT_38(effect_params_t* params) {
    return run_custom_animation(params, 38);
}
bool LOOP_CUSTOM_SLOT_39(effect_params_t* params) {
    return run_custom_animation(params, 39);
}
bool LOOP_CUSTOM_SLOT_40(effect_params_t* params) {
    return run_custom_animation(params, 40);
}

bool LOOP_CUSTOM_SLOT_41(effect_params_t* params) {
    return run_custom_animation(params, 41);
}
bool LOOP_CUSTOM_SLOT_42(effect_params_t* params) {
    return run_custom_animation(params, 42);
}
bool LOOP_CUSTOM_SLOT_43(effect_params_t* params) {
    return run_custom_animation(params, 43);
}
bool LOOP_CUSTOM_SLOT_44(effect_params_t* params) {
    return run_custom_animation(params, 44);
}
bool LOOP_CUSTOM_SLOT_45(effect_params_t* params) {
    return run_custom_animation(params, 45);
}
bool LOOP_CUSTOM_SLOT_46(effect_params_t* params) {
    return run_custom_animation(params, 46);
}
bool LOOP_CUSTOM_SLOT_47(effect_params_t* params) {
    return run_custom_animation(params, 47);
}
bool LOOP_CUSTOM_SLOT_48(effect_params_t* params) {
    return run_custom_animation(params, 48);
}


// =============================================================================
// UTILITY FUNCTIONS FOR EXTERNAL USE
// ======================================