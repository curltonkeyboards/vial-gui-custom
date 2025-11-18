// LOOP_MACRO_ZONES Effect - Enhanced to support both macro and live notes
#include "process_midi.h"
RGB_MATRIX_EFFECT(LOOP_MACRO_ZONES)

#define MAX_TRACKED_NOTES_ZONES 64

typedef struct {
    uint8_t channel;
    uint8_t note;
    uint8_t color_id;  // macro_id for macro notes, channel for live notes
    bool is_macro;     // true for macro notes, false for live notes
    bool active;
} tracked_macro_note_zones_t;

static tracked_macro_note_zones_t tracked_notes_zones[MAX_TRACKED_NOTES_ZONES];
static uint8_t tracked_count_zones = 0;

static int8_t find_tracked_note_zones(uint8_t channel, uint8_t note, uint8_t color_id, bool is_macro) {
    for (uint8_t i = 0; i < MAX_TRACKED_NOTES_ZONES; i++) {
        if (tracked_notes_zones[i].active && 
            tracked_notes_zones[i].channel == channel && 
            tracked_notes_zones[i].note == note && 
            tracked_notes_zones[i].color_id == color_id &&
            tracked_notes_zones[i].is_macro == is_macro) {
            return i;
        }
    }
    return -1;
}

static bool add_tracked_note_zones(uint8_t channel, uint8_t note, uint8_t color_id, bool is_macro) {
    for (uint8_t i = 0; i < MAX_TRACKED_NOTES_ZONES; i++) {
        if (!tracked_notes_zones[i].active) {
            tracked_notes_zones[i].channel = channel;
            tracked_notes_zones[i].note = note;
            tracked_notes_zones[i].color_id = color_id;
            tracked_notes_zones[i].is_macro = is_macro;
            tracked_notes_zones[i].active = true;
            if (i >= tracked_count_zones) tracked_count_zones = i + 1;
            return true;
        }
    }
    return false; // No space
}

static bool loop_macro_zones_runner(effect_params_t* params) {
    static uint8_t zone_map[5][14]; // Store color_id for each key position
    static uint8_t zone_brightness[5][14]; // Brightness for each zone
    static uint32_t last_update_time = 0;
    
    // Hue offsets from base color for different color IDs (macro IDs or channels)
    static const int16_t color_hue_offsets[16] = {
        0,    // ID 0: Base hue (red-ish)
        85,   // ID 1: Green offset
        170,  // ID 2: Blue offset
        43,   // ID 3: Yellow offset
        213,  // ID 4: Purple offset
        128,  // ID 5: Cyan offset
        28,   // ID 6: Orange offset
        248,  // ID 7: Pink offset
        60,   // ID 8: Yellow-green offset
        192,  // ID 9: Blue-violet offset
        11,   // ID 10: Dark salmon offset
        126,  // ID 11: Light sea green offset
        36,   // ID 12: Gold offset
        147,  // ID 13: Steel blue offset
        241,  // ID 14: Pale violet red offset
        6     // ID 15: Tomato offset
    };
    
    if (params->init) {
        // Initialize zone map
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                zone_map[row][col] = 255; // 255 = no color assigned
                zone_brightness[row][col] = 0;
            }
        }
        // Initialize tracking
        for (uint8_t i = 0; i < MAX_TRACKED_NOTES_ZONES; i++) {
            tracked_notes_zones[i].active = false;
        }
        tracked_count_zones = 0;
        last_update_time = timer_read32();
    }
    
    uint32_t current_time = timer_read32();
    uint32_t elapsed = current_time - last_update_time;
    
    // Fade brightness over time (speed-responsive)
    uint8_t speed = rgb_matrix_get_speed();
    uint32_t fade_delay = 50 - (speed * 40) / 255; // 10ms to 50ms based on speed
    if (fade_delay < 10) fade_delay = 10; // Minimum delay
    
    if (elapsed > fade_delay) {
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                if (zone_brightness[row][col] > 0) {
                    zone_brightness[row][col] = (zone_brightness[row][col] * 92) / 100;
                    if (zone_brightness[row][col] < 5) {
                        zone_brightness[row][col] = 0;
                        zone_map[row][col] = 255; // Clear color assignment
                    }
                }
            }
        }
        last_update_time = current_time;
    }
    
    // Check for new macro notes (note-on events)
    for (uint8_t i = 0; i < macro_note_count; i++) {
        uint8_t channel = macro_notes[i][0];
        uint8_t note = macro_notes[i][1];
        uint8_t macro_id = macro_notes[i][2];
        
        // Check if this macro note is already tracked
        if (find_tracked_note_zones(channel, note, macro_id, true) == -1) {
            // New macro note detected - trigger animation and track it
            uint8_t row = (note / 12) % 5;
            uint8_t col = (note % 12) + 1;
            if (col >= 14) col = 13;
            
            // Assign zone and set brightness
            zone_map[row][col] = macro_id % 16; // Limit to available colors
            zone_brightness[row][col] = 255; // Full brightness for active zones
            
            // Create zone influence - nearby keys get partial assignment
            for (int8_t dr = -1; dr <= 1; dr++) {
                for (int8_t dc = -1; dc <= 1; dc++) {
                    int8_t new_row = row + dr;
                    int8_t new_col = col + dc;
                    if (new_row >= 0 && new_row < 5 && new_col >= 0 && new_col < 14) {
                        if (zone_brightness[new_row][new_col] < 128) {
                            zone_map[new_row][new_col] = macro_id % 16;
                            zone_brightness[new_row][new_col] = 128; // Half brightness for influence
                        }
                    }
                }
            }
            
            // Track this macro note
            add_tracked_note_zones(channel, note, macro_id, true);
        }
    }
    
    // Check for new live notes (note-on events)
    for (uint8_t i = 0; i < live_note_count; i++) {
        uint8_t channel = live_notes[i][0];
        uint8_t note = live_notes[i][1];
        uint8_t velocity = live_notes[i][2];
        
        // Check if this live note is already tracked
        if (find_tracked_note_zones(channel, note, channel, false) == -1) {
            // New live note detected - trigger animation and track it
            uint8_t row = (note / 12) % 5;
            uint8_t col = (note % 12) + 1;
            if (col >= 14) col = 13;
            
            // Use channel as color_id for live notes
            uint8_t color_id = channel % 16; // Limit to available colors
            
            // Assign zone and set brightness based on velocity
            zone_map[row][col] = color_id;
            zone_brightness[row][col] = (velocity * 2) > 255 ? 255 : (velocity * 2); // Scale velocity to brightness
            
            // Create zone influence - nearby keys get partial assignment
            uint8_t influence_brightness = zone_brightness[row][col] / 2; // Half brightness for influence
            for (int8_t dr = -1; dr <= 1; dr++) {
                for (int8_t dc = -1; dc <= 1; dc++) {
                    int8_t new_row = row + dr;
                    int8_t new_col = col + dc;
                    if (new_row >= 0 && new_row < 5 && new_col >= 0 && new_col < 14) {
                        if (zone_brightness[new_row][new_col] < influence_brightness) {
                            zone_map[new_row][new_col] = color_id;
                            zone_brightness[new_row][new_col] = influence_brightness;
                        }
                    }
                }
            }
            
            // Track this live note (using channel as color_id)
            add_tracked_note_zones(channel, note, channel, false);
        }
    }
    
    // Check for removed notes (note-off events) and untrack them
    for (uint8_t t = 0; t < tracked_count_zones; t++) {
        if (!tracked_notes_zones[t].active) continue;
        
        bool found = false;
        
        if (tracked_notes_zones[t].is_macro) {
            // Check if macro note still exists
            for (uint8_t i = 0; i < macro_note_count; i++) {
                if (macro_notes[i][0] == tracked_notes_zones[t].channel && 
                    macro_notes[i][1] == tracked_notes_zones[t].note &&
                    macro_notes[i][2] == tracked_notes_zones[t].color_id) {
                    found = true;
                    break;
                }
            }
        } else {
            // Check if live note still exists
            for (uint8_t i = 0; i < live_note_count; i++) {
                if (live_notes[i][0] == tracked_notes_zones[t].channel && 
                    live_notes[i][1] == tracked_notes_zones[t].note) {
                    found = true;
                    break;
                }
            }
        }
        
        if (!found) {
            // Note was removed - untrack it
            tracked_notes_zones[t].active = false;
        }
    }
    
    // Get base color settings
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    
    // Render zones
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                uint8_t color_id = zone_map[row][col];
                uint8_t brightness = zone_brightness[row][col];
                
                if (color_id < 16 && brightness > 0) {
                    // Calculate HSV based on base color and color offset
                    HSV hsv;
                    hsv.h = (base_hue + color_hue_offsets[color_id]) % 256;
                    hsv.s = base_sat;
                    hsv.v = (brightness * base_val) / 128;
                    
                    RGB rgb = hsv_to_rgb(hsv);
                    rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                } else {
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    return false;
}

bool LOOP_MACRO_ZONES(effect_params_t* params) {
    return loop_macro_zones_runner(params);
}