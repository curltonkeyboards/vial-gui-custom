// Combined Zone Effects - Separated Live/Macro Architecture - Modular System
#include "process_midi.h"

// Define MAX_SUSTAIN_NOTES if not already defined
#ifndef MAX_SUSTAIN_NOTES
#define MAX_SUSTAIN_NOTES 16
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

// Forward declarations
static void apply_backlight(uint8_t brightness_pct, background_mode_t background_mode, uint8_t background_brightness_pct);
static bool is_static_background(background_mode_t background_mode);
static void render_autolight_background(background_mode_t background_mode, uint8_t background_brightness_pct);
static bool is_autolight_background(background_mode_t background_mode);

// =============================================================================
// UNIFIED NOTE STORAGE
// =============================================================================

#define MAX_UNIFIED_LIGHTING_NOTES 96
static uint8_t unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES][4]; // [channel, note, type, track_id]
static uint8_t unified_lighting_count = 0;
// type: 0=live/sustained, 1=macro

// =============================================================================
// LIVE SYSTEM DATA STRUCTURES
// =============================================================================

// Live effect arrays
static uint8_t live_led_heatmap[RGB_MATRIX_LED_COUNT];
static uint8_t live_led_color_id[RGB_MATRIX_LED_COUNT];
static uint8_t live_led_brightness[RGB_MATRIX_LED_COUNT];

// Live decay tracking
static uint8_t live_led_decay_brightness[RGB_MATRIX_LED_COUNT];
static uint8_t live_led_decay_color_id[RGB_MATRIX_LED_COUNT];
static bool live_led_currently_active[RGB_MATRIX_LED_COUNT];

// Live moving dots
#define MAX_MOVING_DOTS 32
typedef struct {
    uint8_t row;
    uint8_t col;
    int8_t direction;
    uint8_t color_id;
    uint8_t brightness;
    uint16_t spawn_time;
    bool is_row_movement;
    bool active;
} moving_dot_t;
static moving_dot_t live_moving_dots[MAX_MOVING_DOTS];

// Live held keys
#define MAX_HELD_KEYS 16
typedef struct {
    uint8_t channel;
    uint8_t note;
    uint8_t color_id;
    uint16_t start_time;
    bool active;
} held_key_t;
static held_key_t live_held_keys[MAX_HELD_KEYS];

// Live output buffer
typedef struct {
    uint8_t brightness;
    uint8_t hue;
    uint8_t sat;
    bool active;
} led_output_t;
static led_output_t live_output[RGB_MATRIX_LED_COUNT];

// =============================================================================
// MACRO SYSTEM DATA STRUCTURES
// =============================================================================

// Macro effect arrays
static uint8_t macro_led_heatmap[RGB_MATRIX_LED_COUNT];
static uint8_t macro_led_color_id[RGB_MATRIX_LED_COUNT];
static uint8_t macro_led_brightness[RGB_MATRIX_LED_COUNT];

// Macro decay tracking
static uint8_t macro_led_decay_brightness[RGB_MATRIX_LED_COUNT];
static uint8_t macro_led_decay_color_id[RGB_MATRIX_LED_COUNT];
static bool macro_led_currently_active[RGB_MATRIX_LED_COUNT];

// Macro moving dots
static moving_dot_t macro_moving_dots[MAX_MOVING_DOTS];

// Macro held keys
static held_key_t macro_held_keys[MAX_HELD_KEYS];

// Macro output buffer
static led_output_t macro_output[RGB_MATRIX_LED_COUNT];

// =============================================================================
// BPM BACKGROUND SYSTEM (only used by live system)
// =============================================================================

static bool last_bpm_flash_state = false;
static uint32_t bpm_pulse_start_time = 0;
static uint8_t bpm_pulse_intensity = 0;
static uint8_t bpm_all_beat_count = 0;
static uint8_t bpm_random_colors[5][14][3];
static bool bpm_colors_generated = false;

// Heatmap configuration constants
#define TRUEKEY_HEATMAP_INCREASE_STEP 32
#define TRUEKEY_HEATMAP_DECREASE_DELAY_MS 25

// Global flag to track if true key effects are active
bool truekey_effects_active = false;

// =============================================================================
// UNIFIED NOTE MANAGEMENT FUNCTIONS
// =============================================================================

void add_lighting_macro_note(uint8_t channel, uint8_t note, uint8_t track_id) {
    remove_lighting_macro_note(channel, note, track_id);
    
    if (unified_lighting_count < MAX_UNIFIED_LIGHTING_NOTES) {
        unified_lighting_notes[unified_lighting_count][0] = channel;
        unified_lighting_notes[unified_lighting_count][1] = note;
        unified_lighting_notes[unified_lighting_count][2] = 1; // type: macro
        unified_lighting_notes[unified_lighting_count][3] = track_id;
        unified_lighting_count++;
    } else {
        // Circular buffer - remove oldest
        for (uint8_t i = 0; i < MAX_UNIFIED_LIGHTING_NOTES - 1; i++) {
            unified_lighting_notes[i][0] = unified_lighting_notes[i + 1][0];
            unified_lighting_notes[i][1] = unified_lighting_notes[i + 1][1];
            unified_lighting_notes[i][2] = unified_lighting_notes[i + 1][2];
            unified_lighting_notes[i][3] = unified_lighting_notes[i + 1][3];
        }
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][0] = channel;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][1] = note;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][2] = 1; // type: macro
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][3] = track_id;
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

void add_lighting_live_note(uint8_t channel, uint8_t note) {
    remove_lighting_live_note(channel, note);
    
    if (unified_lighting_count < MAX_UNIFIED_LIGHTING_NOTES) {
        unified_lighting_notes[unified_lighting_count][0] = channel;
        unified_lighting_notes[unified_lighting_count][1] = note;
        unified_lighting_notes[unified_lighting_count][2] = 0; // type: live
        unified_lighting_notes[unified_lighting_count][3] = 0; // no track_id
        unified_lighting_count++;
    } else {
        // Circular buffer - remove oldest
        for (uint8_t i = 0; i < MAX_UNIFIED_LIGHTING_NOTES - 1; i++) {
            unified_lighting_notes[i][0] = unified_lighting_notes[i + 1][0];
            unified_lighting_notes[i][1] = unified_lighting_notes[i + 1][1];
            unified_lighting_notes[i][2] = unified_lighting_notes[i + 1][2];
            unified_lighting_notes[i][3] = unified_lighting_notes[i + 1][3];
        }
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][0] = channel;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][1] = note;
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][2] = 0; // type: live
        unified_lighting_notes[MAX_UNIFIED_LIGHTING_NOTES - 1][3] = 0; // no track_id
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
// BPM BACKGROUND SYSTEM FUNCTIONS (live system only)
// =============================================================================

static void generate_bpm_disco_colors(void) {
    if (!bpm_colors_generated && bpm_pulse_intensity > 0) {
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                bpm_random_colors[row][col][0] = rand() % 256; // Red
                bpm_random_colors[row][col][1] = rand() % 256; // Green
                bpm_random_colors[row][col][2] = rand() % 256; // Blue
            }
        }
        bpm_colors_generated = true;
    }
}

static bool calculate_bpm_all_active_area(uint8_t row, uint8_t col) {
    uint8_t pattern_type = bpm_all_beat_count / 4;
    uint8_t beat_in_pattern = bpm_all_beat_count % 4;
    
    if (pattern_type == 0) {
        // Quadrants pattern
        uint8_t quad_beat = (beat_in_pattern + 1) % 4;
        if (quad_beat == 0) quad_beat = 4;
        
        bool light_top = (quad_beat == 1 || quad_beat == 2);
        bool light_left = (quad_beat == 1 || quad_beat == 4);
        
        uint8_t row_start = light_top ? 0 : 2;
        uint8_t row_end = light_top ? 2 : 4;
        uint8_t col_start = light_left ? 0 : 7;
        uint8_t col_end = light_left ? 6 : 13;
        
        return (row >= row_start && row <= row_end && col >= col_start && col <= col_end);
        
    } else if (pattern_type == 1) {
        // Rows pattern
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
        // Columns pattern - 4,3,3,4 distribution
        uint8_t col_beat = (beat_in_pattern + 1) % 4;
        if (col_beat == 0) col_beat = 4;
        
        uint8_t col_start, col_end;
        switch (col_beat) {
            case 1: col_start = 0; col_end = 3; break;   // 4 columns
            case 2: col_start = 4; col_end = 6; break;   // 3 columns
            case 3: col_start = 7; col_end = 9; break;   // 3 columns
            case 4: col_start = 10; col_end = 13; break; // 4 columns
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
        case 1: col_start = 0; col_end = 3; break;   // 4 columns
        case 2: col_start = 4; col_end = 6; break;   // 3 columns  
        case 3: col_start = 7; col_end = 9; break;   // 3 columns
        case 0: col_start = 10; col_end = 13; break; // 4 columns
        default: col_start = 0; col_end = 3; break;
    }
    return (col >= col_start && col <= col_end);
}

static void update_bpm_background(background_mode_t background_mode) {
    if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_ALL_DISCO) {
        update_bpm_flash();
        
        if (bpm_flash_state && !last_bpm_flash_state) {
            bpm_pulse_start_time = timer_read32();
            bpm_pulse_intensity = 255;
            bpm_colors_generated = false;
            
            if (background_mode >= BACKGROUND_BPM_ALL && background_mode <= BACKGROUND_BPM_ALL_DISCO) {
                bpm_all_beat_count = (bpm_all_beat_count + 1) % 12;
            } else {
                bpm_beat_count = (bpm_beat_count + 1) % 4;
            }
        }
        last_bpm_flash_state = bpm_flash_state;
        
        bool is_disco_mode = (background_mode == BACKGROUND_BPM_PULSE_FADE_DISCO) ||
                            (background_mode == BACKGROUND_BPM_QUADRANTS_DISCO) ||
                            (background_mode == BACKGROUND_BPM_ROW_DISCO) ||
                            (background_mode == BACKGROUND_BPM_COLUMN_DISCO) ||
                            (background_mode == BACKGROUND_BPM_ALL_DISCO);
        
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

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

static uint8_t calculate_distance(uint8_t led1, uint8_t led2) {
    if (led1 >= RGB_MATRIX_LED_COUNT || led2 >= RGB_MATRIX_LED_COUNT) return 255;
    int16_t dx = g_led_config.point[led1].x - g_led_config.point[led2].x;
    int16_t dy = g_led_config.point[led1].y - g_led_config.point[led2].y;
    return sqrt16(dx * dx + dy * dy);
}

static uint8_t cap_brightness(uint16_t value) {
    return value > 255 ? 255 : (uint8_t)value;
}

static uint8_t get_effect_color(uint8_t base_hue, uint8_t effect_type, uint8_t color_id) {
    static const int16_t channel_hue_offsets[16] = {
        0, 85, 170, 43, 213, 128, 28, 248, 60, 192, 11, 126, 36, 147, 241, 6
    };
    
    static const int16_t macro_hue_offsets[5] = {
        0, 85, 170, 43, 213
    };
    
    switch (effect_type) {
        case 0: return base_hue;
        case 1: return (base_hue + channel_hue_offsets[color_id % 16]) % 256;
        case 2: return (base_hue + macro_hue_offsets[color_id % 5]) % 256;
        case 3: return (base_hue + 85) % 256;
        default: return base_hue;
    }
}

static uint8_t get_quadrant_for_macro(uint8_t macro_id) {
    return ((macro_id - 1) % 4) + 1;
}

// =============================================================================
// POSITION SYSTEM FUNCTIONS
// =============================================================================

static void get_truekey_leds(uint8_t note, uint8_t* led_positions, uint8_t* led_count) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    *led_count = 0;
    int16_t note_index = note - 24 - transpose_number - octave_number;
    
    if (note_index >= 0 && note_index < 72) {
        for (uint8_t j = 0; j < 6; j++) {
            uint8_t led_index = get_midi_led_position(current_layer, note_index, j);
            if (led_index < RGB_MATRIX_LED_COUNT && led_index != 99) {
                led_positions[*led_count] = led_index;
                (*led_count)++;
            }
        }
    }
}

static void get_zone_position(uint8_t note, uint8_t* row, uint8_t* col) {
    uint8_t shifted_note = (note + 36) % 60;
    static const uint8_t octave_to_row[5] = {4, 3, 1, 2, 0};
    static const uint8_t note_to_col[12] = {
        0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12
    };
    
    uint8_t octave = (shifted_note / 12) % 5;
    uint8_t note_in_octave = shifted_note % 12;
    
    *row = octave_to_row[octave];
    *col = note_to_col[note_in_octave];
    
    if (*col >= 14) *col = 13;
}

static void get_zone_centers(uint8_t quadrant, uint8_t centers[][2], uint8_t* center_count) {
    *center_count = 5;
    
    switch (quadrant) {
        case 1:
            centers[0][0] = 1; centers[0][1] = 1;
            centers[1][0] = 1; centers[1][1] = 2;
            centers[2][0] = 1; centers[2][1] = 3;
            centers[3][0] = 1; centers[3][1] = 4;
            centers[4][0] = 1; centers[4][1] = 5;
            break;
        case 2:
            centers[0][0] = 1; centers[0][1] = 8;
            centers[1][0] = 1; centers[1][1] = 9;
            centers[2][0] = 1; centers[2][1] = 10;
            centers[3][0] = 1; centers[3][1] = 11;
            centers[4][0] = 1; centers[4][1] = 12;
            break;
        case 3:
            centers[0][0] = 4; centers[0][1] = 1;
            centers[1][0] = 4; centers[1][1] = 2;
            centers[2][0] = 4; centers[2][1] = 3;
            centers[3][0] = 4; centers[3][1] = 4;
            centers[4][0] = 4; centers[4][1] = 5;
            break;
        case 4:
            centers[0][0] = 4; centers[0][1] = 8;
            centers[1][0] = 4; centers[1][1] = 9;
            centers[2][0] = 4; centers[2][1] = 10;
            centers[3][0] = 4; centers[3][1] = 11;
            centers[4][0] = 4; centers[4][1] = 12;
            break;
        default:
            *center_count = 0;
            break;
    }
}

static void get_live_notes_centers(uint8_t centers[][2], uint8_t* center_count) {
    *center_count = 6;
    
    centers[0][0] = 2; centers[0][1] = 4;
    centers[1][0] = 2; centers[1][1] = 5;
    centers[2][0] = 2; centers[2][1] = 6;
    centers[3][0] = 2; centers[3][1] = 7;
    centers[4][0] = 2; centers[4][1] = 8;
    centers[5][0] = 2; centers[5][1] = 9;
}

static uint8_t get_note_row(uint8_t note) {
    uint8_t note_in_octave = note % 12;
    
    switch (note_in_octave) {
        case 0: case 1: return 0;
        case 2: case 3: return 1;
        case 4: case 5: return 2;
        case 6: case 7: return 3;
        case 8: case 9: return 4;
        case 10: return 0;
        case 11: return 2;
        default: return 0;
    }
}

static void get_note_columns(uint8_t note, uint8_t* columns, uint8_t* column_count) {
    uint8_t note_in_octave = note % 12;
    *column_count = 1;
    
    switch (note_in_octave) {
        case 0:
            columns[0] = 0; columns[1] = 1;
            *column_count = 2;
            break;
        case 1: columns[0] = 2; break;
        case 2: columns[0] = 3; break;
        case 3: columns[0] = 4; break;
        case 4: columns[0] = 5; break;
        case 5: columns[0] = 6; break;
        case 6: columns[0] = 7; break;
        case 7: columns[0] = 8; break;
        case 8: columns[0] = 9; break;
        case 9: columns[0] = 10; break;
        case 10: columns[0] = 11; break;
        case 11:
            columns[0] = 12; columns[1] = 13;
            *column_count = 2;
            break;
        default: columns[0] = 0; break;
    }
}

static uint8_t get_mixed_row_column(uint8_t note) {
    uint8_t note_in_octave = note % 12;
    return (note_in_octave % 2 == 0) ? 0 : 13;
}

static uint8_t get_mixed_column_row(uint8_t note) {
    uint8_t note_in_octave = note % 12;
    return (note_in_octave % 2 == 0) ? 0 : 4;
}

static uint8_t get_loop_row(uint8_t track_id) {
    return ((track_id - 1) % 4);
}

static uint8_t get_loop_alt_column(uint8_t track_id) {
    return ((track_id - 1) % 2 == 0) ? 0 : 13;
}

static void get_loop_columns(uint8_t track_id, uint8_t* columns, uint8_t* column_count) {
    switch (track_id) {
        case 1:
            columns[0] = 6; columns[1] = 7;
            *column_count = 2;
            break;
        case 2:
            columns[0] = 4; columns[1] = 5; columns[2] = 8; columns[3] = 9;
            *column_count = 4;
            break;
        case 3:
            columns[0] = 2; columns[1] = 3; columns[2] = 10; columns[3] = 11;
            *column_count = 4;
            break;
        case 4:
            columns[0] = 0; columns[1] = 1; columns[2] = 12; columns[3] = 13;
            *column_count = 4;
            break;
        default:
            columns[0] = 0;
            *column_count = 1;
            break;
    }
}

// =============================================================================
// LIVE SYSTEM FUNCTIONS
// =============================================================================

static int8_t find_live_held_key(uint8_t channel, uint8_t note) {
    for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
        if (live_held_keys[i].active && 
            live_held_keys[i].channel == channel && 
            live_held_keys[i].note == note) {
            return i;
        }
    }
    return -1;
}

static bool add_live_held_key(uint8_t channel, uint8_t note, uint8_t color_id) {
    for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
        if (!live_held_keys[i].active) {
            live_held_keys[i].channel = channel;
            live_held_keys[i].note = note;
            live_held_keys[i].color_id = color_id;
            live_held_keys[i].start_time = timer_read();
            live_held_keys[i].active = true;
            return true;
        }
    }
    return false;
}

static void spawn_live_moving_dots(uint8_t row, uint8_t col, uint8_t color_id, bool is_row_movement) {
    uint8_t dots_spawned = 0;
    for (uint8_t i = 0; i < MAX_MOVING_DOTS && dots_spawned < 2; i++) {
        if (!live_moving_dots[i].active) {
            live_moving_dots[i].row = row;
            live_moving_dots[i].col = col;
            live_moving_dots[i].direction = (dots_spawned == 0) ? -1 : 1;
            live_moving_dots[i].color_id = color_id;
            live_moving_dots[i].brightness = 255;
            live_moving_dots[i].spawn_time = timer_read();
            live_moving_dots[i].is_row_movement = is_row_movement;
            live_moving_dots[i].active = true;
            dots_spawned++;
        }
    }
}

static void update_live_moving_dots(uint8_t speed) {
    static uint16_t movement_timer = 0;
    uint16_t movement_interval = 100 - ((speed * 80) / 255);
    
    if (timer_elapsed(movement_timer) >= movement_interval) {
        for (uint8_t i = 0; i < MAX_MOVING_DOTS; i++) {
            if (live_moving_dots[i].active) {
                if (live_moving_dots[i].is_row_movement) {
                    live_moving_dots[i].col += live_moving_dots[i].direction;
                    if (live_moving_dots[i].col >= 14) {
                        live_moving_dots[i].active = false;
                        continue;
                    }
                } else {
                    live_moving_dots[i].row += live_moving_dots[i].direction;
                    if (live_moving_dots[i].row >= 5) {
                        live_moving_dots[i].active = false;
                        continue;
                    }
                }
                
                uint16_t age = timer_elapsed(live_moving_dots[i].spawn_time);
                if (age >= 5000) {
                    live_moving_dots[i].active = false;
                }
            }
        }
        movement_timer = timer_read();
    }
}

static void update_live_non_heat_decay(uint8_t speed) {
    static uint16_t decay_timer = 0;
    uint16_t decay_interval = 50 - ((speed * 40) / 255);
    
    if (timer_elapsed(decay_timer) >= decay_interval) {
        uint8_t decay_amount = 1 + (speed / 32);
        
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            if (!live_led_currently_active[i] && live_led_decay_brightness[i] > 0) {
                if (live_led_decay_brightness[i] > decay_amount) {
                    live_led_decay_brightness[i] -= decay_amount;
                } else {
                    live_led_decay_brightness[i] = 0;
                }
            }
            live_led_currently_active[i] = false;
        }
        
        decay_timer = timer_read();
    }
}

static uint8_t calculate_live_heat_for_time(uint16_t hold_time, uint8_t speed) {
    uint16_t buildup_time = 8000 - ((speed * 7000) / 255);
    uint8_t target_heat = 255;
    
    if (hold_time >= buildup_time) {
        return target_heat;
    } else {
        return (hold_time * target_heat) / buildup_time;
    }
}

static void apply_live_basic_light(uint8_t* led_positions, uint8_t led_count, uint8_t color_type, uint8_t color_id, uint8_t brightness) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t effect_hue = get_effect_color(base_hue, color_type, color_id);
    
    for (uint8_t i = 0; i < led_count; i++) {
        uint8_t led = led_positions[i];
        if (led < RGB_MATRIX_LED_COUNT) {
            live_led_currently_active[led] = true;
            live_led_decay_brightness[led] = brightness;
            live_led_decay_color_id[led] = color_id;
            
            live_output[led].brightness = brightness;
            live_output[led].hue = effect_hue;
            live_output[led].sat = base_sat;
            live_output[led].active = true;
        }
    }
}

static void apply_live_influence_light(uint8_t* led_positions, uint8_t led_count, uint8_t color_type, uint8_t color_id, uint8_t brightness, uint8_t radius) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t influence_brightness = (brightness * 50) / 100;
    
    apply_live_basic_light(led_positions, led_count, color_type, color_id, brightness);
    
    for (uint8_t i = 0; i < led_count; i++) {
        uint8_t main_led = led_positions[i];
        
        for (uint8_t k = 0; k < RGB_MATRIX_LED_COUNT; k++) {
            if (k != main_led && calculate_distance(main_led, k) < radius) {
                live_led_currently_active[k] = true;
                if (live_led_decay_brightness[k] < influence_brightness) {
                    live_led_decay_brightness[k] = influence_brightness;
                    live_led_decay_color_id[k] = color_id % 16;
                    
                    uint8_t effect_hue = get_effect_color(base_hue, color_type, color_id);
                    live_output[k].brightness = influence_brightness;
                    live_output[k].hue = effect_hue;
                    live_output[k].sat = base_sat;
                    live_output[k].active = true;
                }
            }
        }
    }
}

static void apply_live_zone_with_influence(uint8_t row, uint8_t col, uint8_t color_type, uint8_t color_id, uint8_t brightness) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t effect_hue = get_effect_color(base_hue, color_type, color_id);
    uint8_t capped_brightness = brightness > 255 ? 255 : brightness;
    
    // Light main position
    uint8_t led[LED_HITS_TO_REMEMBER];
    uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
    if (led_count > 0) {
        live_led_currently_active[led[0]] = true;
        live_led_decay_brightness[led[0]] = capped_brightness;
        live_led_decay_color_id[led[0]] = color_id;
        
        live_output[led[0]].brightness = capped_brightness;
        live_output[led[0]].hue = effect_hue;
        live_output[led[0]].sat = base_sat;
        live_output[led[0]].active = true;
    }
    
    // Create zone influence
    uint8_t influence_brightness = (capped_brightness * 50) / 100;
    for (int8_t dr = -1; dr <= 1; dr++) {
        for (int8_t dc = -1; dc <= 1; dc++) {
            int8_t new_row = row + dr;
            int8_t new_col = col + dc;
            if (new_row >= 0 && new_row < 5 && new_col >= 0 && new_col < 14) {
                if (dr == 0 && dc == 0) continue;
                
                uint8_t influence_led[LED_HITS_TO_REMEMBER];
                uint8_t influence_led_count = rgb_matrix_map_row_column_to_led(new_row, new_col, influence_led);
                if (influence_led_count > 0) {
                    live_led_currently_active[influence_led[0]] = true;
                    if (live_led_decay_brightness[influence_led[0]] < influence_brightness) {
                        live_led_decay_brightness[influence_led[0]] = influence_brightness;
                        live_led_decay_color_id[influence_led[0]] = color_id;
                        
                        live_output[influence_led[0]].brightness = influence_brightness;
                        live_output[influence_led[0]].hue = effect_hue;
                        live_output[influence_led[0]].sat = base_sat;
                        live_output[influence_led[0]].active = true;
                    }
                }
            }
        }
    }
}

static void process_live_note(uint8_t channel, uint8_t note, 
                             live_note_positioning_t positioning, 
                             live_animation_t animation,
                             bool use_influence, uint8_t color_type) {
    
    // Handle moving dots animations first
    if (animation == LIVE_ANIM_MOVING_DOTS_ROW || animation == LIVE_ANIM_MOVING_DOTS_COL) {
        uint8_t row, col;
        
        switch (positioning) {
            case LIVE_POS_ZONE:
                get_zone_position(note, &row, &col);
                spawn_live_moving_dots(row, col, channel, animation == LIVE_ANIM_MOVING_DOTS_ROW);
                break;
            case LIVE_POS_QUADRANT: {
                uint8_t centers[6][2];
                uint8_t center_count;
                get_live_notes_centers(centers, &center_count);
                for (uint8_t c = 0; c < center_count; c++) {
                    spawn_live_moving_dots(centers[c][0], centers[c][1], channel, animation == LIVE_ANIM_MOVING_DOTS_ROW);
                }
                break;
            }
            case LIVE_POS_NOTE_ROW_COL0:
                row = get_note_row(note);
                spawn_live_moving_dots(row, 0, channel, animation == LIVE_ANIM_MOVING_DOTS_ROW);
                break;
            case LIVE_POS_NOTE_ROW_COL13:
                row = get_note_row(note);
                spawn_live_moving_dots(row, 13, channel, animation == LIVE_ANIM_MOVING_DOTS_ROW);
                break;
            case LIVE_POS_NOTE_COL_ROW0: {
                uint8_t columns[2];
                uint8_t column_count;
                get_note_columns(note, columns, &column_count);
                for (uint8_t c = 0; c < column_count; c++) {
                    spawn_live_moving_dots(0, columns[c], channel, animation == LIVE_ANIM_MOVING_DOTS_ROW);
                }
                break;
            }
            case LIVE_POS_NOTE_COL_ROW4: {
                uint8_t columns[2];
                uint8_t column_count;
                get_note_columns(note, columns, &column_count);
                for (uint8_t c = 0; c < column_count; c++) {
                    spawn_live_moving_dots(4, columns[c], channel, animation == LIVE_ANIM_MOVING_DOTS_ROW);
                }
                break;
            }
            case LIVE_POS_NOTE_ROW_MIXED: {
                uint8_t row = get_note_row(note);
                uint8_t col = get_mixed_row_column(note);
                spawn_live_moving_dots(row, col, channel, animation == LIVE_ANIM_MOVING_DOTS_ROW);
                break;
            }
            case LIVE_POS_NOTE_COL_MIXED: {
                uint8_t columns[2];
                uint8_t column_count;
                get_note_columns(note, columns, &column_count);
                uint8_t row = get_mixed_column_row(note);
                for (uint8_t c = 0; c < column_count; c++) {
                    spawn_live_moving_dots(row, columns[c], channel, animation == LIVE_ANIM_MOVING_DOTS_ROW);
                }
                break;
			case LIVE_POS_TRUEKEY: {}
			break;
            }
        }
        return;
    }
    
    // Handle other positioning
    switch (positioning) {
        case LIVE_POS_TRUEKEY: {
            uint8_t led_positions[6];
            uint8_t led_count;
            get_truekey_leds(note, led_positions, &led_count);
            
            if (animation == LIVE_ANIM_HEAT || animation == LIVE_ANIM_SUSTAIN) {
                if (animation == LIVE_ANIM_SUSTAIN) {
                    if (find_live_held_key(channel, note) == -1) {
                        add_live_held_key(channel, note, channel);
                    }
                } else {
                    for (uint8_t j = 0; j < led_count; j++) {
                        live_led_heatmap[led_positions[j]] = qadd8(live_led_heatmap[led_positions[j]], TRUEKEY_HEATMAP_INCREASE_STEP);
                        live_led_color_id[led_positions[j]] = channel % 16;
                    }
                }
            } else {
                if (use_influence) {
                    apply_live_influence_light(led_positions, led_count, color_type, channel, 255, 20);
                } else {
                    apply_live_basic_light(led_positions, led_count, color_type, channel, 255);
                }
            }
            break;
        }
        
        case LIVE_POS_ZONE: {
            uint8_t row, col;
            get_zone_position(note, &row, &col);
            apply_live_zone_with_influence(row, col, color_type, channel, 255);
            break;
        }
        
        case LIVE_POS_QUADRANT: {
            uint8_t centers[6][2];
            uint8_t center_count;
            get_live_notes_centers(centers, &center_count);
            
            for (uint8_t c = 0; c < center_count; c++) {
                apply_live_zone_with_influence(centers[c][0], centers[c][1], 0, 0, 255);
            }
            break;
        }
        
        case LIVE_POS_NOTE_ROW_COL0: {
            uint8_t row = get_note_row(note);
            apply_live_zone_with_influence(row, 0, color_type, channel, 255);
            break;
        }
        
        case LIVE_POS_NOTE_ROW_COL13: {
            uint8_t row = get_note_row(note);
            apply_live_zone_with_influence(row, 13, color_type, channel, 255);
            break;
        }
        
        case LIVE_POS_NOTE_COL_ROW0: {
            uint8_t columns[2];
            uint8_t column_count;
            get_note_columns(note, columns, &column_count);
            
            for (uint8_t c = 0; c < column_count; c++) {
                apply_live_zone_with_influence(0, columns[c], color_type, channel, 255);
            }
            break;
        }
        
        case LIVE_POS_NOTE_COL_ROW4: {
            uint8_t columns[2];
            uint8_t column_count;
            get_note_columns(note, columns, &column_count);
            
            for (uint8_t c = 0; c < column_count; c++) {
                apply_live_zone_with_influence(4, columns[c], color_type, channel, 255);
            }
            break;
        }
        
        case LIVE_POS_NOTE_ROW_MIXED: {
            uint8_t row = get_note_row(note);
            uint8_t col = get_mixed_row_column(note);
            apply_live_zone_with_influence(row, col, color_type, channel, 255);
            break;
        }
        
        case LIVE_POS_NOTE_COL_MIXED: {
            uint8_t columns[2];
            uint8_t column_count;
            get_note_columns(note, columns, &column_count);
            uint8_t row = get_mixed_column_row(note);
            
            for (uint8_t c = 0; c < column_count; c++) {
                apply_live_zone_with_influence(row, columns[c], color_type, channel, 255);
            }
            break;
        }
    }
}

// =============================================================================
// MACRO SYSTEM FUNCTIONS  
// =============================================================================

static int8_t find_macro_held_key(uint8_t channel, uint8_t note) {
    for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
        if (macro_held_keys[i].active && 
            macro_held_keys[i].channel == channel && 
            macro_held_keys[i].note == note) {
            return i;
        }
    }
    return -1;
}

static bool add_macro_held_key(uint8_t channel, uint8_t note, uint8_t color_id) {
    for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
        if (!macro_held_keys[i].active) {
            macro_held_keys[i].channel = channel;
            macro_held_keys[i].note = note;
            macro_held_keys[i].color_id = color_id;
            macro_held_keys[i].start_time = timer_read();
            macro_held_keys[i].active = true;
            return true;
        }
    }
    return false;
}

static void spawn_macro_moving_dots(uint8_t row, uint8_t col, uint8_t color_id, bool is_row_movement) {
    uint8_t dots_spawned = 0;
    for (uint8_t i = 0; i < MAX_MOVING_DOTS && dots_spawned < 2; i++) {
        if (!macro_moving_dots[i].active) {
            macro_moving_dots[i].row = row;
            macro_moving_dots[i].col = col;
            macro_moving_dots[i].direction = (dots_spawned == 0) ? -1 : 1;
            macro_moving_dots[i].color_id = color_id;
            macro_moving_dots[i].brightness = 255;
            macro_moving_dots[i].spawn_time = timer_read();
            macro_moving_dots[i].is_row_movement = is_row_movement;
            macro_moving_dots[i].active = true;
            dots_spawned++;
        }
    }
}

static void update_macro_moving_dots(uint8_t speed) {
    static uint16_t movement_timer = 0;
    uint16_t movement_interval = 100 - ((speed * 80) / 255);
    
    if (timer_elapsed(movement_timer) >= movement_interval) {
        for (uint8_t i = 0; i < MAX_MOVING_DOTS; i++) {
            if (macro_moving_dots[i].active) {
                if (macro_moving_dots[i].is_row_movement) {
                    macro_moving_dots[i].col += macro_moving_dots[i].direction;
                    if (macro_moving_dots[i].col >= 14) {
                        macro_moving_dots[i].active = false;
                        continue;
                    }
                } else {
                    macro_moving_dots[i].row += macro_moving_dots[i].direction;
                    if (macro_moving_dots[i].row >= 5) {
                        macro_moving_dots[i].active = false;
                        continue;
                    }
                }
                
                uint16_t age = timer_elapsed(macro_moving_dots[i].spawn_time);
                if (age >= 5000) {
                    macro_moving_dots[i].active = false;
                }
            }
        }
        movement_timer = timer_read();
    }
}

static void update_macro_non_heat_decay(uint8_t speed) {
    static uint16_t decay_timer = 0;
    uint16_t decay_interval = 50 - ((speed * 40) / 255);
    
    if (timer_elapsed(decay_timer) >= decay_interval) {
        uint8_t decay_amount = 1 + (speed / 32);
        
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            if (!macro_led_currently_active[i] && macro_led_decay_brightness[i] > 0) {
                if (macro_led_decay_brightness[i] > decay_amount) {
                    macro_led_decay_brightness[i] -= decay_amount;
                } else {
                    macro_led_decay_brightness[i] = 0;
                }
            }
            macro_led_currently_active[i] = false;
        }
        
        decay_timer = timer_read();
    }
}

static uint8_t calculate_macro_heat_for_time(uint16_t hold_time, uint8_t speed) {
    uint16_t buildup_time = 8000 - ((speed * 7000) / 255);
    uint8_t target_heat = 255;
    
    if (hold_time >= buildup_time) {
        return target_heat;
    } else {
        return (hold_time * target_heat) / buildup_time;
    }
}

static void apply_macro_basic_light(uint8_t* led_positions, uint8_t led_count, uint8_t color_type, uint8_t color_id, uint8_t brightness) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t effect_hue = get_effect_color(base_hue, color_type, color_id);
    
    for (uint8_t i = 0; i < led_count; i++) {
        uint8_t led = led_positions[i];
        if (led < RGB_MATRIX_LED_COUNT) {
            macro_led_currently_active[led] = true;
            macro_led_decay_brightness[led] = brightness;
            macro_led_decay_color_id[led] = color_id;
            
            macro_output[led].brightness = brightness;
            macro_output[led].hue = effect_hue;
            macro_output[led].sat = base_sat;
            macro_output[led].active = true;
        }
    }
}

static void apply_macro_influence_light(uint8_t* led_positions, uint8_t led_count, uint8_t color_type, uint8_t color_id, uint8_t brightness, uint8_t radius) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t influence_brightness = (brightness * 50) / 100;
    
    apply_macro_basic_light(led_positions, led_count, color_type, color_id, brightness);
    
    for (uint8_t i = 0; i < led_count; i++) {
        uint8_t main_led = led_positions[i];
        
        for (uint8_t k = 0; k < RGB_MATRIX_LED_COUNT; k++) {
            if (k != main_led && calculate_distance(main_led, k) < radius) {
                macro_led_currently_active[k] = true;
                if (macro_led_decay_brightness[k] < influence_brightness) {
                    macro_led_decay_brightness[k] = influence_brightness;
                    macro_led_decay_color_id[k] = color_id % 16;
                    
                    uint8_t effect_hue = get_effect_color(base_hue, color_type, color_id);
                    macro_output[k].brightness = influence_brightness;
                    macro_output[k].hue = effect_hue;
                    macro_output[k].sat = base_sat;
                    macro_output[k].active = true;
                }
            }
        }
    }
}

static void apply_macro_zone_with_influence(uint8_t row, uint8_t col, uint8_t color_type, uint8_t color_id, uint8_t brightness) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t effect_hue = get_effect_color(base_hue, color_type, color_id);
    uint8_t capped_brightness = brightness > 255 ? 255 : brightness;
    
    // Light main position
    uint8_t led[LED_HITS_TO_REMEMBER];
    uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
    if (led_count > 0) {
        macro_led_currently_active[led[0]] = true;
        macro_led_decay_brightness[led[0]] = capped_brightness;
        macro_led_decay_color_id[led[0]] = color_id;
        
        macro_output[led[0]].brightness = capped_brightness;
        macro_output[led[0]].hue = effect_hue;
        macro_output[led[0]].sat = base_sat;
        macro_output[led[0]].active = true;
    }
    
    // Create zone influence
    uint8_t influence_brightness = (capped_brightness * 50) / 100;
    for (int8_t dr = -1; dr <= 1; dr++) {
        for (int8_t dc = -1; dc <= 1; dc++) {
            int8_t new_row = row + dr;
            int8_t new_col = col + dc;
            if (new_row >= 0 && new_row < 5 && new_col >= 0 && new_col < 14) {
                if (dr == 0 && dc == 0) continue;
                
                uint8_t influence_led[LED_HITS_TO_REMEMBER];
                uint8_t influence_led_count = rgb_matrix_map_row_column_to_led(new_row, new_col, influence_led);
                if (influence_led_count > 0) {
                    macro_led_currently_active[influence_led[0]] = true;
                    if (macro_led_decay_brightness[influence_led[0]] < influence_brightness) {
                        macro_led_decay_brightness[influence_led[0]] = influence_brightness;
                        macro_led_decay_color_id[influence_led[0]] = color_id;
                        
                        macro_output[influence_led[0]].brightness = influence_brightness;
                        macro_output[influence_led[0]].hue = effect_hue;
                        macro_output[influence_led[0]].sat = base_sat;
                        macro_output[influence_led[0]].active = true;
                    }
                }
            }
        }
    }
}

static void process_macro_note(uint8_t channel, uint8_t note, uint8_t track_id,
                              macro_note_positioning_t positioning, 
                              macro_animation_t animation,
                              bool use_influence, uint8_t color_type) {
    
    // Handle moving dots animations first
    if (animation == MACRO_ANIM_MOVING_DOTS_ROW || animation == MACRO_ANIM_MOVING_DOTS_COL) {
        uint8_t row, col;
        
        switch (positioning) {
            case MACRO_POS_ZONE:
                get_zone_position(note, &row, &col);
                spawn_macro_moving_dots(row, col, channel, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                break;
            case MACRO_POS_QUADRANT: {
                uint8_t quadrant = get_quadrant_for_macro(track_id);
                uint8_t centers[5][2];
                uint8_t center_count;
                get_zone_centers(quadrant, centers, &center_count);
                for (uint8_t c = 0; c < center_count; c++) {
                    spawn_macro_moving_dots(centers[c][0], centers[c][1], quadrant, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                }
                break;
            }
            case MACRO_POS_NOTE_ROW_COL0:
                row = get_note_row(note);
                spawn_macro_moving_dots(row, 0, channel, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                break;
            case MACRO_POS_NOTE_ROW_COL13:
                row = get_note_row(note);
                spawn_macro_moving_dots(row, 13, channel, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                break;
            case MACRO_POS_NOTE_COL_ROW0: {
                uint8_t columns[2];
                uint8_t column_count;
                get_note_columns(note, columns, &column_count);
                for (uint8_t c = 0; c < column_count; c++) {
                    spawn_macro_moving_dots(0, columns[c], channel, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                }
                break;
            }
            case MACRO_POS_NOTE_COL_ROW4: {
                uint8_t columns[2];
                uint8_t column_count;
                get_note_columns(note, columns, &column_count);
                for (uint8_t c = 0; c < column_count; c++) {
                    spawn_macro_moving_dots(4, columns[c], channel, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                }
                break;
            }
            case MACRO_POS_LOOP_ROW_COL0: {
                uint8_t row = get_loop_row(track_id);
                spawn_macro_moving_dots(row, 0, channel, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                break;
            }
            case MACRO_POS_LOOP_ROW_COL13: {
                uint8_t row = get_loop_row(track_id);
                spawn_macro_moving_dots(row, 13, channel, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                break;
            }
            case MACRO_POS_LOOP_ROW_ALT: {
                uint8_t row = get_loop_row(track_id);
                uint8_t col = get_loop_alt_column(track_id);
                spawn_macro_moving_dots(row, col, channel, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                break;
            }
            case MACRO_POS_LOOP_COL: {
                uint8_t columns[4];
                uint8_t column_count;
                get_loop_columns(track_id, columns, &column_count);
                for (uint8_t c = 0; c < column_count; c++) {
                    spawn_macro_moving_dots(0, columns[c], track_id, animation == MACRO_ANIM_MOVING_DOTS_ROW);
                }
                break;
				
			case MACRO_POS_TRUEKEY: {}
			break;	
            }
        }
        return;
    }
    
    // Handle other positioning
    switch (positioning) {
        case MACRO_POS_TRUEKEY: {
            uint8_t led_positions[6];
            uint8_t led_count;
            get_truekey_leds(note, led_positions, &led_count);
            
            if (animation == MACRO_ANIM_HEAT || animation == MACRO_ANIM_SUSTAIN) {
                if (animation == MACRO_ANIM_SUSTAIN) {
                    if (find_macro_held_key(channel, note) == -1) {
                        add_macro_held_key(channel, note, channel);
                    }
                } else {
                    for (uint8_t j = 0; j < led_count; j++) {
                        macro_led_heatmap[led_positions[j]] = qadd8(macro_led_heatmap[led_positions[j]], TRUEKEY_HEATMAP_INCREASE_STEP);
                        macro_led_color_id[led_positions[j]] = channel % 16;
                    }
                }
            } else {
                if (use_influence) {
                    apply_macro_influence_light(led_positions, led_count, color_type, channel, 255, 20);
                } else {
                    apply_macro_basic_light(led_positions, led_count, color_type, channel, 255);
                }
            }
            break;
        }
        
        case MACRO_POS_ZONE: {
            uint8_t row, col;
            get_zone_position(note, &row, &col);
            apply_macro_zone_with_influence(row, col, color_type, channel, 255);
            break;
        }
        
        case MACRO_POS_QUADRANT: {
            uint8_t quadrant = get_quadrant_for_macro(track_id);
            uint8_t centers[5][2];
            uint8_t center_count;
            get_zone_centers(quadrant, centers, &center_count);
            
            for (uint8_t c = 0; c < center_count; c++) {
                apply_macro_zone_with_influence(centers[c][0], centers[c][1], color_type, quadrant, 255);
            }
            break;
        }
        
        case MACRO_POS_NOTE_ROW_COL0: {
            uint8_t row = get_note_row(note);
            apply_macro_zone_with_influence(row, 0, color_type, channel, 255);
            break;
        }
        
        case MACRO_POS_NOTE_ROW_COL13: {
            uint8_t row = get_note_row(note);
            apply_macro_zone_with_influence(row, 13, color_type, channel, 255);
            break;
        }
        
        case MACRO_POS_NOTE_COL_ROW0: {
            uint8_t columns[2];
            uint8_t column_count;
            get_note_columns(note, columns, &column_count);
            
            for (uint8_t c = 0; c < column_count; c++) {
                apply_macro_zone_with_influence(0, columns[c], color_type, channel, 255);
            }
            break;
        }
        
        case MACRO_POS_NOTE_COL_ROW4: {
            uint8_t columns[2];
            uint8_t column_count;
            get_note_columns(note, columns, &column_count);
            
            for (uint8_t c = 0; c < column_count; c++) {
                apply_macro_zone_with_influence(4, columns[c], color_type, channel, 255);
            }
            break;
        }
        
        case MACRO_POS_LOOP_ROW_COL0: {
            uint8_t row = get_loop_row(track_id);
            apply_macro_zone_with_influence(row, 0, color_type, channel, 255);
            break;
        }
        
        case MACRO_POS_LOOP_ROW_COL13: {
            uint8_t row = get_loop_row(track_id);
            apply_macro_zone_with_influence(row, 13, color_type, channel, 255);
            break;
        }
        
        case MACRO_POS_LOOP_ROW_ALT: {
            uint8_t row = get_loop_row(track_id);
            uint8_t col = get_loop_alt_column(track_id);
            apply_macro_zone_with_influence(row, col, color_type, channel, 255);
            break;
        }
        
        case MACRO_POS_LOOP_COL: {
            uint8_t columns[4];
            uint8_t column_count;
            get_loop_columns(track_id, columns, &column_count);
            
            for (uint8_t c = 0; c < column_count; c++) {
                apply_macro_zone_with_influence(0, columns[c], color_type, track_id, 255);
            }
            break;
        }
    }
}

// =============================================================================
// BACKGROUND RENDERING FUNCTIONS  
// =============================================================================

// Simplified render_bpm_background function
static void render_bpm_background(background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    
    // Check if this is any BPM mode
    if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_ALL_DISCO) {
        
        // Determine pattern type
        uint8_t pattern_base = 0;
        bool (*active_area_func)(uint8_t, uint8_t) = NULL;
        
        if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_PULSE_FADE_DISCO) {
            pattern_base = BACKGROUND_BPM_PULSE_FADE;
            active_area_func = NULL; // Pulse fade uses full matrix
        } else if (background_mode >= BACKGROUND_BPM_QUADRANTS && background_mode <= BACKGROUND_BPM_QUADRANTS_DISCO) {
            pattern_base = BACKGROUND_BPM_QUADRANTS;
            active_area_func = calculate_bpm_quadrants_active_area;
        } else if (background_mode >= BACKGROUND_BPM_ROW && background_mode <= BACKGROUND_BPM_ROW_DISCO) {
            pattern_base = BACKGROUND_BPM_ROW;
            active_area_func = calculate_bpm_row_active_area;
        } else if (background_mode >= BACKGROUND_BPM_COLUMN && background_mode <= BACKGROUND_BPM_COLUMN_DISCO) {
            pattern_base = BACKGROUND_BPM_COLUMN;
            active_area_func = calculate_bpm_column_active_area;
        } else if (background_mode >= BACKGROUND_BPM_ALL && background_mode <= BACKGROUND_BPM_ALL_DISCO) {
            pattern_base = BACKGROUND_BPM_ALL;
            active_area_func = calculate_bpm_all_active_area;
        }
        
        // Calculate variant within pattern (0-6)
        uint8_t variant = background_mode - pattern_base;
        bool is_disco = (variant == 6); // Disco is always the 7th variant (index 6)
        
        // Determine hue and saturation modifications based on variant
        uint8_t pulse_hue = base_hue;
        uint8_t pulse_sat = base_sat;
        
        if (!is_disco) {
            switch (variant) {
                case 1: // HUE1
                    pulse_hue = (base_hue + 64) % 256;   // Your original working values
                    break;
                case 2: // HUE2
                    pulse_hue = (base_hue + 128) % 256;
                    break;
                case 3: // HUE3
                    pulse_hue = (base_hue + 192) % 256;
                    break;
                case 4: // DESAT
                    pulse_sat = base_sat / 2;
                    break;
                case 5: // HUE_DESAT
                    pulse_hue = (base_hue + 128) % 256;
                    pulse_sat = base_sat / 2;
                    break;
                default: // Base variant (0) - keep original values
                    break;
            }
        }
        
        if (bpm_pulse_intensity > 0) {
            // Calculate max pulse brightness using configurable background brightness
            uint8_t max_pulse_brightness = (base_val * background_brightness_pct) / 100;
            uint8_t brightness_factor = (max_pulse_brightness * bpm_pulse_intensity) / 255;
            
            // Render based on pattern
            for (uint8_t row = 0; row < 5; row++) {
                for (uint8_t col = 0; col < 14; col++) {
                    uint8_t led[LED_HITS_TO_REMEMBER];
                    uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
                    if (led_count > 0) {
                        bool in_active_area = true;
                        
                        // Check if position is in active area for patterned modes
                        if (active_area_func != NULL) {
                            in_active_area = active_area_func(row, col);
                        }
                        
                        if (in_active_area) {
                            if (is_disco) {
                                // Use random disco colors (like your old BPM_ALL_DISCO)
                                uint8_t r = (bpm_random_colors[row][col][0] * brightness_factor) / 255;
                                uint8_t g = (bpm_random_colors[row][col][1] * brightness_factor) / 255;
                                uint8_t b = (bpm_random_colors[row][col][2] * brightness_factor) / 255;
                                rgb_matrix_set_color(led[0], r, g, b);
                            } else {
                                // Use device colors with hue/saturation modifications
                                HSV hsv = {pulse_hue, pulse_sat, brightness_factor};
                                RGB rgb = hsv_to_rgb(hsv);
                                rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                            }
                        } else {
                            rgb_matrix_set_color(led[0], 0, 0, 0);
                        }
                    }
                }
            }
        } else {
            // No pulse - turn off all LEDs (0 backlight)
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
static void apply_backlight(uint8_t brightness_pct, background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    uint8_t backlight_val = (base_val * background_brightness_pct) / 100;
    
    uint8_t static_hue = base_hue;
    uint8_t static_sat = base_sat;
    
    if (background_mode >= BACKGROUND_STATIC && background_mode <= BACKGROUND_STATIC_HUE_DESAT) {
        uint8_t variant = background_mode - BACKGROUND_STATIC;
        
        switch (variant) {
            case 1: static_hue = (base_hue + 64) % 256; break;
            case 2: static_hue = (base_hue + 128) % 256; break;
            case 3: static_hue = (base_hue + 192) % 256; break;
            case 4: static_sat = base_sat / 2; break;
            case 5:
                static_hue = (base_hue + 128) % 256;
                static_sat = base_sat / 2;
                break;
        }
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
    uint8_t sat_factor = 255;
    
    if (background_mode >= BACKGROUND_AUTOLIGHT && background_mode <= BACKGROUND_AUTOLIGHT_HUE_DESAT) {
        uint8_t variant = background_mode - BACKGROUND_AUTOLIGHT;
        
        switch (variant) {
            case 1: hue_shift = 64; break;
            case 2: hue_shift = 128; break;
            case 3: hue_shift = 192; break;
            case 4: sat_factor = 128; break;
            case 5:
                hue_shift = 128;
                sat_factor = 128;
                break;
        }
    }
    
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

static bool is_static_background(background_mode_t background_mode) {
    return (background_mode >= BACKGROUND_STATIC && background_mode <= BACKGROUND_STATIC_HUE_DESAT);
}

static bool is_autolight_background(background_mode_t background_mode) {
    return (background_mode >= BACKGROUND_AUTOLIGHT && background_mode <= BACKGROUND_AUTOLIGHT_HUE_DESAT);
}

// =============================================================================
// COMPOSITOR SYSTEM
// =============================================================================

static void composite_and_render(background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t base_val = rgb_matrix_get_val();
    
    // Background is already rendered by live rendering functions
    // Just composite live and macro effects on top
    
    // Composite and render to actual LEDs with live priority
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        if (live_output[i].active) {
            // Live effect takes priority
            uint8_t final_brightness = cap_brightness((live_output[i].brightness * base_val) / 255);
            HSV hsv = {live_output[i].hue, live_output[i].sat, final_brightness};
            RGB rgb = hsv_to_rgb(hsv);
            rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
        } else if (macro_output[i].active) {
            // Macro effect if no live effect
            uint8_t final_brightness = cap_brightness((macro_output[i].brightness * base_val) / 255);
            HSV hsv = {macro_output[i].hue, macro_output[i].sat, final_brightness};
            RGB rgb = hsv_to_rgb(hsv);
            rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
        }
        // Note: for backgrounds, they are already rendered directly to LEDs by live functions
        // Only turn off LEDs if background is NONE and no effects are active
        else if (background_mode == BACKGROUND_NONE) {
            rgb_matrix_set_color(i, 0, 0, 0);
        }
    }
}

static void render_live_moving_dots(background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    
    // Render background first (live system handles this)
    if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_ALL_DISCO) {
        render_bpm_background(background_mode, background_brightness_pct);
    } else if (is_static_background(background_mode)) {
        apply_backlight(30, background_mode, background_brightness_pct);
    } else if (is_autolight_background(background_mode)) {
        render_autolight_background(background_mode, background_brightness_pct);
    } else if (background_mode == BACKGROUND_NONE) {
        // Clear all LEDs for BACKGROUND_NONE
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
    
    // Clear live output buffer
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        live_output[i].active = false;
    }
    
    // Render moving dots into live output
    for (uint8_t i = 0; i < MAX_MOVING_DOTS; i++) {
        if (live_moving_dots[i].active) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(live_moving_dots[i].row, live_moving_dots[i].col, led);
            if (led_count > 0) {
                uint8_t effect_hue = get_effect_color(base_hue, 1, live_moving_dots[i].color_id);
                
                live_output[led[0]].brightness = live_moving_dots[i].brightness;
                live_output[led[0]].hue = effect_hue;
                live_output[led[0]].sat = base_sat;
                live_output[led[0]].active = true;
            }
        }
    }
}

static void render_macro_moving_dots(void) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    
    // Clear macro output buffer  
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        macro_output[i].active = false;
    }
    
    // Render moving dots into macro output
    for (uint8_t i = 0; i < MAX_MOVING_DOTS; i++) {
        if (macro_moving_dots[i].active) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(macro_moving_dots[i].row, macro_moving_dots[i].col, led);
            if (led_count > 0) {
                uint8_t effect_hue = get_effect_color(base_hue, 1, macro_moving_dots[i].color_id);
                
                macro_output[led[0]].brightness = macro_moving_dots[i].brightness;
                macro_output[led[0]].hue = effect_hue;
                macro_output[led[0]].sat = base_sat;
                macro_output[led[0]].active = true;
            }
        }
    }
}

static void render_live_decay_effects(background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    
    // Render background first (live system handles this)
    if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_ALL_DISCO) {
        render_bpm_background(background_mode, background_brightness_pct);
    } else if (is_static_background(background_mode)) {
        apply_backlight(30, background_mode, background_brightness_pct);
    } else if (is_autolight_background(background_mode)) {
        render_autolight_background(background_mode, background_brightness_pct);
    } else if (background_mode == BACKGROUND_NONE) {
        // Clear all LEDs for BACKGROUND_NONE
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            rgb_matrix_set_color(i, 0, 0, 0);
        }
    }
    
    // Clear live output buffer
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        live_output[i].active = false;
    }
    
    // Render decay effects into live output
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        if (live_led_decay_brightness[i] > 0) {
            uint8_t color_id = live_led_decay_color_id[i];
            if (color_id < 16) {
                uint8_t effect_hue = get_effect_color(base_hue, 1, color_id);
                
                live_output[i].brightness = live_led_decay_brightness[i];
                live_output[i].hue = effect_hue;
                live_output[i].sat = base_sat;
                live_output[i].active = true;
            }
        }
    }
}

static void render_macro_decay_effects(void) {
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    
    // Clear macro output buffer
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        macro_output[i].active = false;
    }
    
    // Render decay effects into macro output
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        if (macro_led_decay_brightness[i] > 0) {
            uint8_t color_id = macro_led_decay_color_id[i];
            if (color_id < 16) {
                uint8_t effect_hue = get_effect_color(base_hue, 1, color_id);
                
                macro_output[i].brightness = macro_led_decay_brightness[i];
                macro_output[i].hue = effect_hue;
                macro_output[i].sat = base_sat;
                macro_output[i].active = true;
            }
        }
    }
}

static void render_live_heat_effects(background_mode_t background_mode, uint8_t background_brightness_pct) {
    uint8_t base_sat = rgb_matrix_get_sat();
    
    // Render background first (live system handles this)
    if (background_mode >= BACKGROUND_BPM_PULSE_FADE && background_mode <= BACKGROUND_BPM_ALL_DISCO) {
        render_bpm_background(background_mode, background_brightness_pct);
    } else if (is_static_background(background_mode)) {
        apply_backlight(30, background_mode, background_brightness_pct);
    } else if (is_autolight_background(background_mode)) {
        render_autolight_background(background_mode, background_brightness_pct);
    } else if (background_mode == BACKGROUND_NONE) {
        // Clear all LEDs for BACKGROUND_NONE
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            rgb_matrix_set_color(i, 0, 0, 0);
        }
    }
    
    // Clear live output buffer
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        live_output[i].active = false;
    }
    
    // Render heat effects into live output
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        uint8_t heat = live_led_heatmap[i];
        uint8_t color_id = live_led_color_id[i];
        
        if (heat > 0 && color_id < 16) {
            uint8_t effect_hue;
            uint8_t final_brightness;
            
            // Heat-based hue cycling (blue to red)
            uint16_t hue_shift = (170 * (255 - heat)) / 255;
            effect_hue = hue_shift;
            final_brightness = heat;
            
            live_output[i].brightness = final_brightness;
            live_output[i].hue = effect_hue;
            live_output[i].sat = base_sat;
            live_output[i].active = true;
        }
    }
}

static void render_macro_heat_effects(void) {
    uint8_t base_sat = rgb_matrix_get_sat();
    
    // Clear macro output buffer
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        macro_output[i].active = false;
    }
    
    // Render heat effects into macro output
    for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
        uint8_t heat = macro_led_heatmap[i];
        uint8_t color_id = macro_led_color_id[i];
        
        if (heat > 0 && color_id < 16) {
            uint8_t effect_hue;
            uint8_t final_brightness;
            
            // Heat-based hue cycling (blue to red)
            uint16_t hue_shift = (170 * (255 - heat)) / 255;
            effect_hue = hue_shift;
            final_brightness = heat;
            
            macro_output[i].brightness = final_brightness;
            macro_output[i].hue = effect_hue;
            macro_output[i].sat = base_sat;
            macro_output[i].active = true;
        }
    }
}

// =============================================================================
// MAIN SEPARATED EFFECT RUNNER
// =============================================================================

static bool run_separated_effect(effect_params_t* params,
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
    
    // Determine which effects are active
    truekey_effects_active = (live_positioning == LIVE_POS_TRUEKEY) || 
                            (macro_positioning == MACRO_POS_TRUEKEY);
    
    bool live_heat_mode = (live_animation == LIVE_ANIM_HEAT) || (live_animation == LIVE_ANIM_SUSTAIN);
    bool macro_heat_mode = (macro_animation == MACRO_ANIM_HEAT) || (macro_animation == MACRO_ANIM_SUSTAIN);
    
    bool live_moving_dots_mode = (live_animation == LIVE_ANIM_MOVING_DOTS_ROW) || 
                                (live_animation == LIVE_ANIM_MOVING_DOTS_COL);
    bool macro_moving_dots_mode = (macro_animation == MACRO_ANIM_MOVING_DOTS_ROW) || 
                                 (macro_animation == MACRO_ANIM_MOVING_DOTS_COL);
    
    if (params->init) {
        // Initialize live arrays
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            live_led_brightness[i] = 0;
            live_led_color_id[i] = 255;
            live_led_heatmap[i] = 0;
            live_led_decay_brightness[i] = 0;
            live_led_decay_color_id[i] = 255;
            live_led_currently_active[i] = false;
            live_output[i].active = false;
        }
        for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
            live_held_keys[i].active = false;
        }
        for (uint8_t i = 0; i < MAX_MOVING_DOTS; i++) {
            live_moving_dots[i].active = false;
        }
        
        // Initialize macro arrays
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            macro_led_brightness[i] = 0;
            macro_led_color_id[i] = 255;
            macro_led_heatmap[i] = 0;
            macro_led_decay_brightness[i] = 0;
            macro_led_decay_color_id[i] = 255;
            macro_led_currently_active[i] = false;
            macro_output[i].active = false;
        }
        for (uint8_t i = 0; i < MAX_HELD_KEYS; i++) {
            macro_held_keys[i].active = false;
        }
        for (uint8_t i = 0; i < MAX_MOVING_DOTS; i++) {
            macro_moving_dots[i].active = false;
        }

        // Initialize BPM background system (live system only)
        last_bpm_flash_state = false;
        bpm_pulse_start_time = 0;
        bpm_pulse_intensity = 0;
        bpm_all_beat_count = 0;
		bpm_beat_count = 0;
        bpm_colors_generated = false;

        live_heat_timer = timer_read();
        macro_heat_timer = timer_read();
    }
    
    // Update BPM background system (live system only)
    update_bpm_background(background_mode);
    
    // Handle live heat decay
    if (live_heat_mode) {
        bool decrease_heat = timer_elapsed(live_heat_timer) >= 10;
        if (decrease_heat) {
            bool sustain_mode = (live_animation == LIVE_ANIM_SUSTAIN);
            uint8_t decay_amount = sustain_mode ? 13 : (1 + (live_speed / 64));
            
            for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
                if (sustain_mode) {
                    bool has_active_key = false;
                    for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
                        if (live_held_keys[h].active) {
                            uint8_t led_positions[6];
                            uint8_t led_count;
                            get_truekey_leds(live_held_keys[h].note, led_positions, &led_count);
                            for (uint8_t l = 0; l < led_count; l++) {
                                if (led_positions[l] == i) {
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
            live_heat_timer = timer_read();
        }
    }
    
    // Handle macro heat decay
    if (macro_heat_mode) {
        bool decrease_heat = timer_elapsed(macro_heat_timer) >= 10;
        if (decrease_heat) {
            bool sustain_mode = (macro_animation == MACRO_ANIM_SUSTAIN);
            uint8_t decay_amount = sustain_mode ? 13 : (1 + (macro_speed / 64));
            
            for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
                if (sustain_mode) {
                    bool has_active_key = false;
                    for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
                        if (macro_held_keys[h].active) {
                            uint8_t led_positions[6];
                            uint8_t led_count;
                            get_truekey_leds(macro_held_keys[h].note, led_positions, &led_count);
                            for (uint8_t l = 0; l < led_count; l++) {
                                if (led_positions[l] == i) {
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
            macro_heat_timer = timer_read();
        }
    }
    
    // Update moving dots
    if (live_moving_dots_mode) {
        update_live_moving_dots(live_speed);
    }
    if (macro_moving_dots_mode) {
        update_macro_moving_dots(macro_speed);
    }
    
    // SEPARATED NOTE PROCESSING
    for (int16_t i = unified_lighting_count - 1; i >= 0; i--) {
        uint8_t channel = unified_lighting_notes[i][0];
        uint8_t note = unified_lighting_notes[i][1];
        uint8_t type = unified_lighting_notes[i][2]; // 0=live, 1=macro
        uint8_t track_id = unified_lighting_notes[i][3];
        
        bool is_macro = (type == 1);
        bool is_live = (type == 0);
        
        // Route to appropriate system
        if (is_live) {
            process_live_note(channel, note, live_positioning, live_animation, 
                            use_influence, color_type);
        } else {
            process_macro_note(channel, note, track_id, macro_positioning, macro_animation,
                             use_influence, color_type);
        }
        
        // Handle pulse mode
        bool should_pulse = false;
        if (pulse_mode == 1 && is_live) should_pulse = true;
        if (pulse_mode == 2 && is_macro) should_pulse = true;
        if (pulse_mode == 3) should_pulse = true;
        
        if (should_pulse) {
            for (uint8_t j = i; j < unified_lighting_count - 1; j++) {
                unified_lighting_notes[j][0] = unified_lighting_notes[j + 1][0];
                unified_lighting_notes[j][1] = unified_lighting_notes[j + 1][1];
                unified_lighting_notes[j][2] = unified_lighting_notes[j + 1][2];
                unified_lighting_notes[j][3] = unified_lighting_notes[j + 1][3];
            }
            unified_lighting_count--;
        }
    }
    
    // Update held keys for sustain effects
    if (live_heat_mode && (live_animation == LIVE_ANIM_SUSTAIN)) {
        for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
            if (live_held_keys[h].active) {
                uint16_t hold_time = timer_elapsed(live_held_keys[h].start_time);
                uint8_t heat_value = calculate_live_heat_for_time(hold_time, live_speed);
                
                uint8_t led_positions[6];
                uint8_t led_count;
                get_truekey_leds(live_held_keys[h].note, led_positions, &led_count);
                
                for (uint8_t j = 0; j < led_count; j++) {
                    live_led_heatmap[led_positions[j]] = heat_value;
                    live_led_color_id[led_positions[j]] = live_held_keys[h].color_id % 16;
                }
            }
        }
        
        // Remove inactive live held keys
        for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
            if (live_held_keys[h].active) {
                bool still_active = false;
                for (uint8_t i = 0; i < unified_lighting_count; i++) {
                    if (unified_lighting_notes[i][0] == live_held_keys[h].channel && 
                        unified_lighting_notes[i][1] == live_held_keys[h].note &&
                        unified_lighting_notes[i][2] == 0) { // live type
                        still_active = true;
                        break;
                    }
                }
                if (!still_active) {
                    live_held_keys[h].active = false;
                }
            }
        }
    }
    
    if (macro_heat_mode && (macro_animation == MACRO_ANIM_SUSTAIN)) {
        for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
            if (macro_held_keys[h].active) {
                uint16_t hold_time = timer_elapsed(macro_held_keys[h].start_time);
                uint8_t heat_value = calculate_macro_heat_for_time(hold_time, macro_speed);
                
                uint8_t led_positions[6];
                uint8_t led_count;
                get_truekey_leds(macro_held_keys[h].note, led_positions, &led_count);
                
                for (uint8_t j = 0; j < led_count; j++) {
                    macro_led_heatmap[led_positions[j]] = heat_value;
                    macro_led_color_id[led_positions[j]] = macro_held_keys[h].color_id % 16;
                }
            }
        }
        
        // Remove inactive macro held keys
        for (uint8_t h = 0; h < MAX_HELD_KEYS; h++) {
            if (macro_held_keys[h].active) {
                bool still_active = false;
                for (uint8_t i = 0; i < unified_lighting_count; i++) {
                    if (unified_lighting_notes[i][0] == macro_held_keys[h].channel && 
                        unified_lighting_notes[i][1] == macro_held_keys[h].note &&
                        unified_lighting_notes[i][2] == 1) { // macro type
                        still_active = true;
                        break;
                    }
                }
                if (!still_active) {
                    macro_held_keys[h].active = false;
                }
            }
        }
    }
    
    // Update non-heat decay
    if (!live_heat_mode && !live_moving_dots_mode) {
        update_live_non_heat_decay(live_speed);
    }
    if (!macro_heat_mode && !macro_moving_dots_mode) {
        update_macro_non_heat_decay(macro_speed);
    }
    
    // Render both systems into their output buffers
    if (live_moving_dots_mode) {
        render_live_moving_dots(background_mode, background_brightness_pct);
    } else if (!live_heat_mode) {
        render_live_decay_effects(background_mode, background_brightness_pct);
    } else {
        render_live_heat_effects(background_mode, background_brightness_pct);
    }
    
    if (macro_moving_dots_mode) {
        render_macro_moving_dots();
    } else if (!macro_heat_mode) {
        render_macro_decay_effects();
    } else {
        render_macro_heat_effects();
    }
    
    // Final composite and render
    composite_and_render(background_mode, background_brightness_pct);
    
    return false;
}

// =============================================================================
// CUSTOM ANIMATION CONFIGURATION SYSTEM
// =============================================================================

custom_animation_config_t custom_slots[NUM_CUSTOM_SLOTS] = {
    // Slots 0-9 with basic defaults
    {LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_HEAT, MACRO_ANIM_HEAT, false, BACKGROUND_STATIC, 3, 1, true, 30, 255, 255},
    {LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_ROW, MACRO_ANIM_MOVING_DOTS_ROW, false, BACKGROUND_BPM_PULSE_FADE, 3, 1, true, 30, 255, 255},
    {LIVE_POS_QUADRANT, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, true, BACKGROUND_BPM_ALL_DISCO, 0, 2, true, 30, 255, 255},
    {LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, true, BACKGROUND_NONE, 0, 1, true, 30, 255, 255},
    {LIVE_POS_NOTE_COL_MIXED, MACRO_POS_LOOP_COL, LIVE_ANIM_MOVING_DOTS_COL, MACRO_ANIM_MOVING_DOTS_COL, false, BACKGROUND_BPM_ALL_DISCO, 3, 1, true, 30, 255, 255},
    {LIVE_POS_NOTE_ROW_MIXED, MACRO_POS_LOOP_ROW_ALT, LIVE_ANIM_MOVING_DOTS_ROW, MACRO_ANIM_MOVING_DOTS_ROW, false, BACKGROUND_BPM_PULSE_FADE, 3, 1, true, 30, 255, 255},
    {LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_NONE, 3, 1, false, 30, 255, 255},
    {LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_HEAT, MACRO_ANIM_HEAT, true, BACKGROUND_STATIC, 0, 3, false, 30, 255, 255},
    {LIVE_POS_QUADRANT, MACRO_POS_QUADRANT, LIVE_ANIM_MOVING_DOTS_ROW, MACRO_ANIM_MOVING_DOTS_COL, false, BACKGROUND_BPM_PULSE_FADE, 1, 2, false, 30, 255, 255},
    {LIVE_POS_NOTE_COL_ROW0, MACRO_POS_LOOP_COL, LIVE_ANIM_SUSTAIN, MACRO_ANIM_NONE, true, BACKGROUND_BPM_ALL_DISCO, 2, 1, false, 30, 255, 255}
};

uint8_t current_custom_slot = 0;

// =============================================================================
// PARAMETER SETTING FUNCTIONS
// =============================================================================

void set_custom_slot_background_brightness(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value <= 100) {
        custom_slots[slot].background_brightness = value;
    }
}

void set_custom_slot_live_positioning(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 9) {
        custom_slots[slot].live_positioning = (live_note_positioning_t)value;
    }
}

void set_custom_slot_macro_positioning(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 11) {
        custom_slots[slot].macro_positioning = (macro_note_positioning_t)value;
    }
}

void set_custom_slot_live_animation(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 5) {
        custom_slots[slot].live_animation = (live_animation_t)value;
    }
}

void set_custom_slot_macro_animation(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 5) {
        custom_slots[slot].macro_animation = (macro_animation_t)value;
    }
}

void set_custom_slot_use_influence(uint8_t slot, bool value) {
    if (slot < NUM_CUSTOM_SLOTS) {
        custom_slots[slot].use_influence = value;
    }
}

void set_custom_slot_background_mode(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 50) {
        custom_slots[slot].background_mode = (background_mode_t)value;
    }
}

void set_custom_slot_pulse_mode(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 4) {
        custom_slots[slot].pulse_mode = value;
    }
}

void set_custom_slot_color_type(uint8_t slot, uint8_t value) {
    if (slot < NUM_CUSTOM_SLOTS && value < 4) {
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

// =============================================================================
// CUSTOM ANIMATION EFFECT FUNCTIONS  
// =============================================================================

static bool run_custom_animation(effect_params_t* params, uint8_t slot_number) {
    if (slot_number >= NUM_CUSTOM_SLOTS) return false;
    
    custom_animation_config_t* config = &custom_slots[slot_number];
    
    if (!config->enabled) {
        return false;
    }
    
    current_custom_slot = slot_number;
    
    return run_separated_effect(params,
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

// =============================================================================
// EFFECT DEFINITIONS - UPDATED FOR SEPARATED SYSTEM
// =============================================================================

// Zone effect functions
bool LOOP_CHANNEL_COLORS(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_NONE, 3, 1, 30, 255, 245);
}

bool LOOP_CHANNEL_COLORS_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_STATIC, 3, 1, 30, 255, 245);
}

bool LOOP_CHANNEL_COLORS_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_BPM_PULSE_FADE, 3, 1, 30, 255, 245);
}

bool LOOP_CHANNEL_COLORS_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_BPM_ALL_DISCO, 3, 1, 30, 255, 245);
}

bool LOOP_ZONES(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_NONE, 3, 2, 30, 255, 245);
}

bool LOOP_ZONES_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_STATIC, 3, 2, 30, 255, 255);
}

bool LOOP_ZONES_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_BPM_PULSE_FADE, 3, 2, 30, 255, 255);
}

bool LOOP_ZONES_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_BPM_ALL_DISCO, 3, 2, 30, 255, 255);
}

bool LOOP_TRUEKEY_BASIC(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_NONE, 0, 1, 30, 255, 255);
}

bool LOOP_TRUEKEY_BASIC_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_STATIC, 0, 1, 30, 255, 255);
}

bool LOOP_TRUEKEY_BASIC_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_BPM_PULSE_FADE, 0, 1, 30, 255, 255);
}

bool LOOP_TRUEKEY_BASIC_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_BPM_ALL_DISCO, 0, 1, 30, 255, 255);
}

bool LOOP_TRUEKEY_WIDE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_NONE, MACRO_ANIM_NONE, true, BACKGROUND_NONE, 3, 1, 30, 255, 255);
}

bool LOOP_TRUEKEY_WIDE_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_NONE, MACRO_ANIM_NONE, true, BACKGROUND_STATIC, 3, 1, 30, 255, 255);
}

bool LOOP_TRUEKEY_WIDE_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_NONE, MACRO_ANIM_NONE, true, BACKGROUND_BPM_PULSE_FADE, 3, 1, 30, 255, 255);
}

bool LOOP_TRUEKEY_WIDE_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_NONE, MACRO_ANIM_NONE, true, BACKGROUND_BPM_ALL_DISCO, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP1_NARROW(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_HEAT, MACRO_ANIM_HEAT, false, BACKGROUND_NONE, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP1_NARROW_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_HEAT, MACRO_ANIM_HEAT, false, BACKGROUND_STATIC, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP1_NARROW_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_HEAT, MACRO_ANIM_HEAT, false, BACKGROUND_BPM_PULSE_FADE, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP1_NARROW_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_HEAT, MACRO_ANIM_HEAT, false, BACKGROUND_BPM_ALL_DISCO, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP1_WIDE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, false, BACKGROUND_NONE, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP1_WIDE_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, false, BACKGROUND_STATIC, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP1_WIDE_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, false, BACKGROUND_BPM_PULSE_FADE, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP1_WIDE_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, false, BACKGROUND_BPM_ALL_DISCO, 3, 1, 30, 255, 255);
}

bool LOOP_HEATMAP2_NARROW(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, false, BACKGROUND_NONE, 0, 0, 30, 255, 255);
}

bool LOOP_HEATMAP2_NARROW_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, false, BACKGROUND_STATIC, 0, 3, 30, 255, 255);
}

bool LOOP_HEATMAP2_NARROW_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, false, BACKGROUND_BPM_PULSE_FADE, 0, 3, 30, 255, 255);
}

bool LOOP_HEATMAP2_NARROW_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_TRUEKEY, MACRO_POS_TRUEKEY, LIVE_ANIM_SUSTAIN, MACRO_ANIM_SUSTAIN, false, BACKGROUND_BPM_ALL_DISCO, 0, 3, 30, 255, 255);
}

// Moving dots effect functions
bool LOOP_MOVING_DOTS_ROW(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_ROW, MACRO_ANIM_MOVING_DOTS_ROW, false, BACKGROUND_NONE, 3, 1, 30, 255, 255);
}

bool LOOP_MOVING_DOTS_ROW_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_ROW, MACRO_ANIM_MOVING_DOTS_ROW, false, BACKGROUND_STATIC, 3, 1, 30, 255, 255);
}

bool LOOP_MOVING_DOTS_ROW_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_ROW, MACRO_ANIM_MOVING_DOTS_ROW, false, BACKGROUND_BPM_PULSE_FADE, 3, 1, 30, 255, 255);
}

bool LOOP_MOVING_DOTS_ROW_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_ROW, MACRO_ANIM_MOVING_DOTS_ROW, false, BACKGROUND_BPM_ALL_DISCO, 3, 1, 30, 255, 255);
}

bool LOOP_MOVING_DOTS_COL(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_COL, MACRO_ANIM_MOVING_DOTS_COL, false, BACKGROUND_NONE, 3, 1, 30, 255, 255);
}

bool LOOP_MOVING_DOTS_COL_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_COL, MACRO_ANIM_MOVING_DOTS_COL, false, BACKGROUND_STATIC, 3, 1, 30, 255, 255);
}

bool LOOP_MOVING_DOTS_COL_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_COL, MACRO_ANIM_MOVING_DOTS_COL, false, BACKGROUND_BPM_PULSE_FADE, 3, 1, 30, 255, 255);
}

bool LOOP_MOVING_DOTS_COL_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_ZONE, MACRO_POS_ZONE, LIVE_ANIM_MOVING_DOTS_COL, MACRO_ANIM_MOVING_DOTS_COL, false, BACKGROUND_BPM_ALL_DISCO, 3, 1, 30, 255, 255);
}

// Basic quadrant effects
bool LOOP_QUADRANTS_SUSTAIN(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_QUADRANT, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_NONE, 0, 0, 30, 255, 255);
}

bool LOOP_QUADRANTS_SUSTAIN_BACKLIGHT(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_QUADRANT, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_STATIC, 0, 0, 30, 255, 255);
}

bool LOOP_QUADRANTS_SUSTAIN_BPM_PULSE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_QUADRANT, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_BPM_PULSE_FADE, 0, 0, 30, 255, 255);
}

bool LOOP_QUADRANTS_SUSTAIN_BPM_DISCO(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_QUADRANT, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_BPM_ALL_DISCO, 0, 0, 30, 255, 255);
}

// Basic truekey effects
bool LOOP_TRUEKEY_SUBWOOF(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_QUADRANT, MACRO_POS_QUADRANT, LIVE_ANIM_NONE, MACRO_ANIM_NONE, false, BACKGROUND_NONE, 0, 0, 30, 255, 255);
}

bool LOOP_TRUEKEY_LINE(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_NOTE_ROW_MIXED, MACRO_POS_LOOP_ROW_ALT, LIVE_ANIM_MOVING_DOTS_ROW , MACRO_ANIM_MOVING_DOTS_ROW , false, BACKGROUND_BPM_PULSE_FADE, 3, 1, 30, 255, 255);
}

bool LOOP_TRUEKEY_ALL(effect_params_t* params) {
    return run_separated_effect(params, LIVE_POS_NOTE_COL_MIXED, MACRO_POS_LOOP_COL, LIVE_ANIM_MOVING_DOTS_COL , MACRO_ANIM_MOVING_DOTS_COL , false, BACKGROUND_BPM_ALL_DISCO, 3, 1, 30, 255, 255);
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