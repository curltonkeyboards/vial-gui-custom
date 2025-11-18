// Combined BPM Effects - Shared variables and functions
#include "orthomidi5x14.h"

typedef enum {
    BPM_PATTERN_QUADRANTS,
    BPM_PATTERN_ROW, 
    BPM_PATTERN_COLUMN,
    BPM_PATTERN_ALL,
    BPM_PATTERN_PULSE_FADE
} bpm_pattern_t;

typedef enum {
    BPM_COLOR_NORMAL,
    BPM_COLOR_DISCO,
    BPM_COLOR_BACKLIGHT,  
    BPM_COLOR_DISCO_BACKLIGHT
} bpm_color_mode_t;

// Shared variables between all BPM effects
static bool last_flash_state = false;
static uint32_t pulse_start_time = 0;
static uint8_t pulse_intensity = 0;
static uint8_t all_beat_count = 0; // 0-11 counter for ALL pattern
static uint8_t random_colors[5][14][3]; // Store RGB values for each position
static bool colors_generated = false;

// Generate random disco colors for the entire matrix
static void generate_disco_colors(void) {
    if (!colors_generated && pulse_intensity > 0) {
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                random_colors[row][col][0] = rand() % 256; // Red
                random_colors[row][col][1] = rand() % 256; // Green
                random_colors[row][col][2] = rand() % 256; // Blue
            }
        }
        colors_generated = true;
    }
}

// Calculate if a position is in the active area based on pattern and beat count
static bool calculate_active_area(bpm_pattern_t pattern, uint8_t row, uint8_t col) {
    switch (pattern) {
        case BPM_PATTERN_QUADRANTS: {
            // Beat pattern: 1=top-left, 2=top-right, 3=bottom-right, 0=bottom-left
            bool light_top = (bpm_beat_count == 1 || bpm_beat_count == 2);
            bool light_left = (bpm_beat_count == 1 || bpm_beat_count == 0);
            
            uint8_t row_start = light_top ? 0 : 2;
            uint8_t row_end = light_top ? 2 : 4;
            uint8_t col_start = light_left ? 0 : 7;
            uint8_t col_end = light_left ? 6 : 13;
            
            return (row >= row_start && row <= row_end && col >= col_start && col <= col_end);
        }
        
        case BPM_PATTERN_ROW: {
            // Beat pattern: 1=rows 0-1, 2=rows 1-2, 3=rows 2-3, 0=rows 3-4
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
        
        case BPM_PATTERN_COLUMN: {
            // Beat pattern: 1=cols 0-3 (4), 2=cols 4-6 (3), 3=cols 7-9 (3), 0=cols 10-13 (4)
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
        
        case BPM_PATTERN_ALL: {
            // Determine pattern and active area based on all_beat_count
            uint8_t pattern_type = all_beat_count / 4; // 0=quadrants, 1=rows, 2=columns
            uint8_t beat_in_pattern = all_beat_count % 4; // 0-3 within each pattern
            
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
                // Columns pattern - Updated to 4,3,3,4 distribution
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
        
        case BPM_PATTERN_PULSE_FADE:
            // Full matrix is always active
            return true;
            
        default:
            return false;
    }
}

// Get color for a position based on color mode and beat state
static void get_color_for_position(bpm_color_mode_t color_mode, uint8_t row, uint8_t col, 
                                   bool in_active_area, uint8_t beat_intensity, 
                                   uint8_t *r, uint8_t *g, uint8_t *b) {
    switch (color_mode) {
        case BPM_COLOR_NORMAL:
            if (pulse_intensity > 0 && in_active_area) {
                // Use keyboard's current RGB color with calculated brightness
                uint8_t brightness = (rgb_matrix_config.hsv.v * pulse_intensity) / 255;
                HSV hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, brightness};
                RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                *r = rgb.r; *g = rgb.g; *b = rgb.b;
            } else {
                // Turn off LED when not pulsing or not in active area
                *r = 0; *g = 0; *b = 0;
            }
            break;
            
        case BPM_COLOR_DISCO:
            if (pulse_intensity > 0 && in_active_area) {
                // Use random colors with device brightness
                uint8_t brightness_factor = (rgb_matrix_config.hsv.v * pulse_intensity) / 255;
                *r = (random_colors[row][col][0] * brightness_factor) / 255;
                *g = (random_colors[row][col][1] * brightness_factor) / 255;
                *b = (random_colors[row][col][2] * brightness_factor) / 255;
            } else {
                // Turn off LED when not pulsing or not in active area
                *r = 0; *g = 0; *b = 0;
            }
            break;
            
        case BPM_COLOR_BACKLIGHT:
            if (beat_intensity > 0 && in_active_area) {
                // Beat effect: Start with hue offset +60 degrees at user's brightness, fade to backlight
                uint32_t current_time = timer_read32();
                uint32_t elapsed = current_time - pulse_start_time;
                uint32_t pulse_duration = current_bpm > 0 ? (3000000000ULL / current_bpm) : 250;
                
                if (elapsed < pulse_duration) {
                    float progress = (float)elapsed / pulse_duration;
                    
                    // Interpolate hue from offset back to original
                    uint8_t start_hue = (rgb_matrix_config.hsv.h + 85) % 256;  // +60 degrees
                    uint8_t end_hue = rgb_matrix_config.hsv.h;
                    uint8_t current_hue = start_hue + (uint8_t)((float)(end_hue - start_hue) * progress);
                    
                    // Interpolate brightness from user's brightness to backlight level (50% of user brightness)
                    uint8_t user_brightness = rgb_matrix_config.hsv.v;  // User's current brightness setting
                    uint8_t backlight_brightness = user_brightness / 2;  // 50% of user brightness
                    uint8_t current_brightness = user_brightness - (uint8_t)((user_brightness - backlight_brightness) * progress);
                    
                    HSV beat_hsv = {current_hue, rgb_matrix_config.hsv.s, current_brightness};
                    RGB beat_rgb = rgb_matrix_hsv_to_rgb(beat_hsv);
                    *r = beat_rgb.r; *g = beat_rgb.g; *b = beat_rgb.b;
                } else {
                    // Fallback to backlight
                    HSV bg_hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, rgb_matrix_config.hsv.v / 2};
                    RGB bg_rgb = rgb_matrix_hsv_to_rgb(bg_hsv);
                    *r = bg_rgb.r; *g = bg_rgb.g; *b = bg_rgb.b;
                }
            } else {
                // Background: use current RGB color at 50% of user brightness
                HSV bg_hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, rgb_matrix_config.hsv.v / 2};
                RGB bg_rgb = rgb_matrix_hsv_to_rgb(bg_hsv);
                *r = bg_rgb.r; *g = bg_rgb.g; *b = bg_rgb.b;
            }
            break;
            
        case BPM_COLOR_DISCO_BACKLIGHT:
            if (beat_intensity > 0 && in_active_area) {
                // Beat effect: Start with random disco colors at user's brightness, fade to backlight
                uint32_t current_time = timer_read32();
                uint32_t elapsed = current_time - pulse_start_time;
                uint32_t pulse_duration = current_bpm > 0 ? (3000000000ULL / current_bpm) : 250;
                
                if (elapsed < pulse_duration) {
                    float progress = (float)elapsed / pulse_duration;
                    
                    // Start with disco colors at user brightness, fade to backlight
                    uint8_t user_brightness = rgb_matrix_config.hsv.v;  // User's current brightness setting
                    uint8_t backlight_brightness = user_brightness / 2;  // 50% of user brightness
                    uint8_t disco_brightness = user_brightness;          // User's brightness for disco
                    uint8_t current_brightness = disco_brightness - (uint8_t)((disco_brightness - backlight_brightness) * progress);
                    
                    // Interpolate from disco colors to backlight color
                    HSV bg_hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, current_brightness};
                    RGB bg_rgb = rgb_matrix_hsv_to_rgb(bg_hsv);
                    
                    // Mix disco and backlight colors based on progress
                    uint8_t disco_r = (random_colors[row][col][0] * current_brightness) / 255;
                    uint8_t disco_g = (random_colors[row][col][1] * current_brightness) / 255;  
                    uint8_t disco_b = (random_colors[row][col][2] * current_brightness) / 255;
                    
                    *r = disco_r * (1.0f - progress) + bg_rgb.r * progress;
                    *g = disco_g * (1.0f - progress) + bg_rgb.g * progress;
                    *b = disco_b * (1.0f - progress) + bg_rgb.b * progress;
                } else {
                    // Fallback to backlight
                    HSV bg_hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, rgb_matrix_config.hsv.v / 2};
                    RGB bg_rgb = rgb_matrix_hsv_to_rgb(bg_hsv);
                    *r = bg_rgb.r; *g = bg_rgb.g; *b = bg_rgb.b;
                }
            } else {
                // Background: use current RGB color at 50% of user brightness
                HSV bg_hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, rgb_matrix_config.hsv.v / 2};
                RGB bg_rgb = rgb_matrix_hsv_to_rgb(bg_hsv);
                *r = bg_rgb.r; *g = bg_rgb.g; *b = bg_rgb.b;
            }
            break;
    }
}

// Main shared BPM runner function
static bool bpm_runner(effect_params_t* params, bpm_pattern_t pattern, bpm_color_mode_t color_mode) {
    if (params->init) {
        last_flash_state = false;
        pulse_start_time = 0;
        pulse_intensity = 0;
        all_beat_count = 0;
        colors_generated = false;
    }
    
    // Update BPM flash state
    update_bpm_flash();
    
    // Detect new beat (flash state goes from false to true)
    if (bpm_flash_state && !last_flash_state) {
        pulse_start_time = timer_read32();
        pulse_intensity = 255; // Start at full intensity
        colors_generated = false; // Generate new colors for new beat
        
        // Update counters
        if (pattern == BPM_PATTERN_ALL) {
            all_beat_count = (all_beat_count + 1) % 12; // Cycle through 0-11
        }
    }
    last_flash_state = bpm_flash_state;
    
    // Generate disco colors if needed
    if (color_mode == BPM_COLOR_DISCO || color_mode == BPM_COLOR_DISCO_BACKLIGHT) {
        generate_disco_colors();
    }
    
    // Calculate fade progression
    uint8_t beat_intensity = 0;
    if (pulse_intensity > 0) {
        uint32_t current_time = timer_read32();
        uint32_t elapsed = current_time - pulse_start_time;
        
        // Pulse duration: use same calculation method as main BPM code
        uint32_t pulse_duration = current_bpm > 0 ? (3000000000ULL / current_bpm) : 250; // ms
        
        if (elapsed < pulse_duration) {
            // Fade out using exponential decay for natural feel
            float progress = (float)elapsed / pulse_duration;
            
            if (color_mode == BPM_COLOR_BACKLIGHT || color_mode == BPM_COLOR_DISCO_BACKLIGHT) {
                // Backlight modes use beat_intensity
                beat_intensity = (uint8_t)(255 * (1.0f - progress) * (1.0f - progress));
                pulse_intensity = beat_intensity;
            } else {
                // Normal and disco modes use pulse_intensity
                pulse_intensity = (uint8_t)(255 * (1.0f - progress) * (1.0f - progress));
            }
        } else {
            pulse_intensity = 0;
            beat_intensity = 0;
        }
    }
    
    // Render the effect across entire matrix
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                // Check if this position is in the active area
                bool in_active_area = calculate_active_area(pattern, row, col);
                
                // Get color for this position
                uint8_t r, g, b;
                get_color_for_position(color_mode, row, col, in_active_area, beat_intensity, &r, &g, &b);
                
                // Set the LED color
                rgb_matrix_set_color(led[0], r, g, b);
            }
        }
    }
    
    return false;
}

// Individual effect functions
bool BPM_QUADRANTS(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_QUADRANTS, BPM_COLOR_NORMAL);
}

bool BPM_QUADRANTS_DISCO(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_QUADRANTS, BPM_COLOR_DISCO);
}

bool BPM_QUADRANTS_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_QUADRANTS, BPM_COLOR_BACKLIGHT);
}

bool BPM_QUADRANTS_DISCO_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_QUADRANTS, BPM_COLOR_DISCO_BACKLIGHT);
}

bool BPM_ROW(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_ROW, BPM_COLOR_NORMAL);
}

bool BPM_ROW_DISCO(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_ROW, BPM_COLOR_DISCO);
}

bool BPM_ROW_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_ROW, BPM_COLOR_BACKLIGHT);
}

bool BPM_ROW_DISCO_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_ROW, BPM_COLOR_DISCO_BACKLIGHT);
}

bool BPM_COLUMN(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_COLUMN, BPM_COLOR_NORMAL);
}

bool BPM_COLUMN_DISCO(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_COLUMN, BPM_COLOR_DISCO);
}

bool BPM_COLUMN_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_COLUMN, BPM_COLOR_BACKLIGHT);
}

bool BPM_COLUMN_DISCO_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_COLUMN, BPM_COLOR_DISCO_BACKLIGHT);
}

bool BPM_ALL(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_ALL, BPM_COLOR_NORMAL);
}

bool BPM_ALL_DISCO(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_ALL, BPM_COLOR_DISCO);
}

bool BPM_ALL_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_ALL, BPM_COLOR_BACKLIGHT);
}

bool BPM_ALL_DISCO_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_ALL, BPM_COLOR_DISCO_BACKLIGHT);
}

bool BPM_PULSE_FADE(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_PULSE_FADE, BPM_COLOR_NORMAL);
}

bool BPM_PULSE_FADE_DISCO(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_PULSE_FADE, BPM_COLOR_DISCO);
}

bool BPM_PULSE_FADE_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_PULSE_FADE, BPM_COLOR_BACKLIGHT);
}

bool BPM_PULSE_FADE_DISCO_BACKLIGHT(effect_params_t* params) {
    return bpm_runner(params, BPM_PATTERN_PULSE_FADE, BPM_COLOR_DISCO_BACKLIGHT);
}