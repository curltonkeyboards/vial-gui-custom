// Combined Wave Effects - Shared variables and functions
#include "process_midi.h"

#define MAX_WAVES 16
#define MAX_TRACKED_NOTES_WAVES 64

typedef struct {
    uint8_t center_row;
    uint8_t center_col;
    uint8_t channel;
    uint8_t macro_id;    // Store macro_id for macro-colored waves
    uint8_t velocity;
    uint32_t start_time;
    bool active;
    bool is_macro;       // Track if this wave came from a macro note
} wave_t;

typedef struct {
    uint8_t channel;
    uint8_t note;
    bool is_macro;
    bool active;
} tracked_note_waves_t;

// Shared variables between all wave effects
static wave_t waves[MAX_WAVES];
static uint8_t wave_index = 0;
static tracked_note_waves_t tracked_notes_waves[MAX_TRACKED_NOTES_WAVES];
static uint8_t tracked_count_waves = 0;

// Shared helper functions
static int8_t find_tracked_note_waves(uint8_t channel, uint8_t note, bool is_macro) {
    for (uint8_t i = 0; i < MAX_TRACKED_NOTES_WAVES; i++) {
        if (tracked_notes_waves[i].active && 
            tracked_notes_waves[i].channel == channel && 
            tracked_notes_waves[i].note == note && 
            tracked_notes_waves[i].is_macro == is_macro) {
            return i;
        }
    }
    return -1;
}

static bool add_tracked_note_waves(uint8_t channel, uint8_t note, bool is_macro) {
    for (uint8_t i = 0; i < MAX_TRACKED_NOTES_WAVES; i++) {
        if (!tracked_notes_waves[i].active) {
            tracked_notes_waves[i].channel = channel;
            tracked_notes_waves[i].note = note;
            tracked_notes_waves[i].is_macro = is_macro;
            tracked_notes_waves[i].active = true;
            if (i >= tracked_count_waves) tracked_count_waves = i + 1;
            return true;
        }
    }
    return false;
}

// Shared wave runner - takes a parameter to determine coloring mode
static bool wave_runner(effect_params_t* params, bool color_by_macro) {
    static uint16_t color_buffer[5][14][3]; // RGB accumulation buffer for blending
    
    // Channel hue offsets (for channel-colored waves)
    static const int16_t channel_hue_offsets[16] = {
        0, 85, 170, 43, 213, 128, 28, 248, 60, 192, 11, 126, 36, 147, 241, 6
    };
    
    // Macro hue offsets (for macro-colored waves)
    static const int16_t macro_hue_offsets[16] = {
        0, 85, 170, 43, 213, 128, 28, 248, 60, 192, 11, 126, 36, 147, 241, 6
    };
    
    if (params->init) {
        // Initialize all waves as inactive
        for (uint8_t i = 0; i < MAX_WAVES; i++) {
            waves[i].active = false;
        }
        // Initialize color buffer
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                color_buffer[row][col][0] = 0; // R
                color_buffer[row][col][1] = 0; // G  
                color_buffer[row][col][2] = 0; // B
            }
        }
        // Initialize tracking
        for (uint8_t i = 0; i < MAX_TRACKED_NOTES_WAVES; i++) {
            tracked_notes_waves[i].active = false;
        }
        wave_index = 0;
        tracked_count_waves = 0;
    }
    
    uint32_t current_time = timer_read32();
    uint8_t speed = rgb_matrix_get_speed();
    
    // Check for new live notes (note-on events)
    for (uint8_t i = 0; i < live_note_count; i++) {
        uint8_t channel = live_notes[i][0];
        uint8_t note = live_notes[i][1];
        uint8_t velocity = live_notes[i][2];
        
        // Check if this note is already tracked
        if (find_tracked_note_waves(channel, note, false) == -1) {
            // New note detected - create wave and track it
            uint8_t row = (note / 12) % 5;
            uint8_t col = (note % 12) + 1;
            if (col >= 14) col = 13;
            
            waves[wave_index].center_row = row;
            waves[wave_index].center_col = col;
            waves[wave_index].channel = channel;
            waves[wave_index].macro_id = 0; // Default macro_id for live notes
            waves[wave_index].velocity = velocity;
            waves[wave_index].start_time = current_time;
            waves[wave_index].active = true;
            waves[wave_index].is_macro = false;
            wave_index = (wave_index + 1) % MAX_WAVES;
            
            // Track this note
            add_tracked_note_waves(channel, note, false);
        }
    }
    
    // Check for new macro notes (note-on events)
    for (uint8_t i = 0; i < macro_note_count; i++) {
        uint8_t channel = macro_notes[i][0];
        uint8_t note = macro_notes[i][1];
        uint8_t macro_id = macro_notes[i][2];
        
        // Check if this note is already tracked
        if (find_tracked_note_waves(channel, note, true) == -1) {
            // New note detected - create wave and track it
            uint8_t row = (note / 12) % 5;
            uint8_t col = (note % 12) + 1;
            if (col >= 14) col = 13;
            
            waves[wave_index].center_row = row;
            waves[wave_index].center_col = col;
            waves[wave_index].channel = channel;
            waves[wave_index].macro_id = macro_id; // Use actual macro_id
            waves[wave_index].velocity = 100; // Fixed velocity for macro notes
            waves[wave_index].start_time = current_time;
            waves[wave_index].active = true;
            waves[wave_index].is_macro = true;
            wave_index = (wave_index + 1) % MAX_WAVES;
            
            // Track this note
            add_tracked_note_waves(channel, note, true);
        }
    }
    
    // Check for removed notes (note-off events) and untrack them
    for (uint8_t t = 0; t < tracked_count_waves; t++) {
        if (!tracked_notes_waves[t].active) continue;
        
        bool found = false;
        
        if (tracked_notes_waves[t].is_macro) {
            // Check if macro note still exists
            for (uint8_t i = 0; i < macro_note_count; i++) {
                if (macro_notes[i][0] == tracked_notes_waves[t].channel && 
                    macro_notes[i][1] == tracked_notes_waves[t].note) {
                    found = true;
                    break;
                }
            }
        } else {
            // Check if live note still exists
            for (uint8_t i = 0; i < live_note_count; i++) {
                if (live_notes[i][0] == tracked_notes_waves[t].channel && 
                    live_notes[i][1] == tracked_notes_waves[t].note) {
                    found = true;
                    break;
                }
            }
        }
        
        if (!found) {
            // Note was removed - untrack it (wave continues independently)
            tracked_notes_waves[t].active = false;
        }
    }
    
    // Clear the color buffer
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            color_buffer[row][col][0] = 0; // R
            color_buffer[row][col][1] = 0; // G
            color_buffer[row][col][2] = 0; // B
        }
    }
    
    // Get base color settings
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    
    // Render active waves with speed-responsive duration
    for (uint8_t w = 0; w < MAX_WAVES; w++) {
        if (!waves[w].active) continue;
        
        uint32_t elapsed = current_time - waves[w].start_time;
        // Speed-responsive wave duration: 500ms to 2500ms based on speed
        uint32_t wave_duration = 2500 - (speed * 2000) / 255;
        if (wave_duration < 500) wave_duration = 500; // Minimum duration
        
        if (elapsed > wave_duration) {
            waves[w].active = false;
            continue;
        }
        
        // Calculate wave properties
        float progress = (float)elapsed / wave_duration;
        float wave_radius = progress * 3.0f; // Max radius of 3 keys
        uint8_t intensity = (uint8_t)(255 * (1.0f - progress) * (waves[w].velocity / 127.0f));
        
        if (intensity < 10) {
            waves[w].active = false;
            continue;
        }
        
        // Draw wave circle
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                // Calculate distance from wave center
                float dx = (float)col - waves[w].center_col;
                float dy = (float)row - waves[w].center_row;
                float distance = sqrtf(dx * dx + dy * dy);
                
                // Check if this position is on the wave ring
                float ring_thickness = 0.8f;
                if (distance >= (wave_radius - ring_thickness) && distance <= (wave_radius + ring_thickness)) {
                    HSV hsv;
                    
                    if (color_by_macro) {
                        // MACRO_WAVES: Color by macro ID
                        uint8_t macro_idx = waves[w].macro_id % 16;
                        hsv.h = (base_hue + macro_hue_offsets[macro_idx]) % 256;
                    } else {
                        // LOOP_CHANNEL_WAVES: Color by channel
                        uint8_t channel_idx = waves[w].channel % 16;
                        hsv.h = (base_hue + channel_hue_offsets[channel_idx]) % 256;
                    }
                    
                    hsv.s = base_sat;
                    hsv.v = base_val;
                    
                    RGB wave_rgb = hsv_to_rgb(hsv);
                    
                    // Apply wave intensity and distance falloff
                    float falloff = 1.0f - fabsf(distance - wave_radius) / ring_thickness;
                    uint8_t final_intensity = (uint8_t)(intensity * falloff);
                    
                    uint16_t r = (wave_rgb.r * final_intensity) / 255;
                    uint16_t g = (wave_rgb.g * final_intensity) / 255;
                    uint16_t b = (wave_rgb.b * final_intensity) / 255;
                    
                    // Additive blending in color buffer
                    color_buffer[row][col][0] += r;
                    color_buffer[row][col][1] += g;
                    color_buffer[row][col][2] += b;
                    
                    // Clamp to prevent overflow
                    if (color_buffer[row][col][0] > 255) color_buffer[row][col][0] = 255;
                    if (color_buffer[row][col][1] > 255) color_buffer[row][col][1] = 255;
                    if (color_buffer[row][col][2] > 255) color_buffer[row][col][2] = 255;
                }
            }
        }
    }
    
    // Apply color buffer to LED matrix
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                rgb_matrix_set_color(led[0], 
                    (uint8_t)color_buffer[row][col][0],
                    (uint8_t)color_buffer[row][col][1], 
                    (uint8_t)color_buffer[row][col][2]);
            }
        }
    }
    
    return false;
}

bool LOOP_CHANNEL_WAVES(effect_params_t* params) {
    return wave_runner(params, false); // Color by channel
}

bool LOOP_MACRO_WAVES(effect_params_t* params) {
    return wave_runner(params, true); // Color by macro
}