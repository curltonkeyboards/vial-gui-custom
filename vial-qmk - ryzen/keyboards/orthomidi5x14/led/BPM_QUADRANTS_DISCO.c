
// BPM_QUADRANTS_DISCO Effect
#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(BPM_QUADRANTS_DISCO)
static bool bpm_quadrants_disco_runner(effect_params_t* params) {
    static bool last_flash_state = false;
    static uint32_t pulse_start_time = 0;
    static uint8_t pulse_intensity = 0;
    static uint8_t random_colors[5][14][3]; // Store RGB values for each position
    static bool colors_generated = false;
    
    if (params->init) {
        last_flash_state = false;
        pulse_start_time = 0;
        pulse_intensity = 0;
        colors_generated = false;
    }
    
    // Update BPM flash state
    update_bpm_flash();
    
    // Detect new beat (flash state goes from false to true)
    if (bpm_flash_state && !last_flash_state) {
        pulse_start_time = timer_read32();
        pulse_intensity = 255; // Start at full intensity
        colors_generated = false; // Generate new colors for new beat
    }
    last_flash_state = bpm_flash_state;
    
    // Generate random colors for this beat if not already done
    if (!colors_generated && pulse_intensity > 0) {
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                // Generate random RGB values
                random_colors[row][col][0] = rand() % 256; // Red
                random_colors[row][col][1] = rand() % 256; // Green
                random_colors[row][col][2] = rand() % 256; // Blue
            }
        }
        colors_generated = true;
    }
    
    // Calculate fade progression
    if (pulse_intensity > 0) {
        uint32_t current_time = timer_read32();
        uint32_t elapsed = current_time - pulse_start_time;
        
        // Pulse duration: use same calculation method as main BPM code
        uint32_t pulse_duration = current_bpm > 0 ? (3000000000ULL / current_bpm) : 250; // ms
        
        if (elapsed < pulse_duration) {
            // Fade out using exponential decay for natural feel
            float progress = (float)elapsed / pulse_duration;
            pulse_intensity = (uint8_t)(255 * (1.0f - progress) * (1.0f - progress));
        } else {
            pulse_intensity = 0;
        }
    }
    
    // Determine which quadrant to light based on beat count
    // Beat pattern: 1=top-left, 2=top-right, 3=bottom-right, 0=bottom-left
    bool light_top = (bpm_beat_count == 1 || bpm_beat_count == 2);
    bool light_left = (bpm_beat_count == 1 || bpm_beat_count == 0);
    
    // Define quadrant boundaries for 5x14 matrix
    uint8_t row_start = light_top ? 0 : 2;
    uint8_t row_end = light_top ? 2 : 4;
    uint8_t col_start = light_left ? 0 : 7;
    uint8_t col_end = light_left ? 6 : 13;
    
    // Calculate brightness factor based on device brightness and pulse intensity
    uint8_t brightness_factor = (rgb_matrix_config.hsv.v * pulse_intensity) / 255;
    
    // Render the pulse across entire matrix, but only light the active quadrant
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                // Check if this LED is in the active quadrant
                bool in_active_quadrant = (row >= row_start && row <= row_end && 
                                         col >= col_start && col <= col_end);
                
                if (pulse_intensity > 0 && in_active_quadrant) {
                    // Use random colors with device brightness
                    uint8_t r = (random_colors[row][col][0] * brightness_factor) / 255;
                    uint8_t g = (random_colors[row][col][1] * brightness_factor) / 255;
                    uint8_t b = (random_colors[row][col][2] * brightness_factor) / 255;
                    rgb_matrix_set_color(led[0], r, g, b);
                } else {
                    // Turn off LED when not pulsing or not in active quadrant
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    return false;
}
bool BPM_QUADRANTS_DISCO(effect_params_t* params) {
    return bpm_quadrants_disco_runner(params);
}
