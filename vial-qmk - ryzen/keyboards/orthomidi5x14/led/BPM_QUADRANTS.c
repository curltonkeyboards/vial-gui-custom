#include "orthomidi5x14.h"

// BPM_QUADRANTS Effect
RGB_MATRIX_EFFECT(BPM_QUADRANTS)
static bool bpm_quadrants_runner(effect_params_t* params) {
    static bool last_flash_state = false;
    static uint32_t pulse_start_time = 0;
    static uint8_t pulse_intensity = 0;
    
    if (params->init) {
        last_flash_state = false;
        pulse_start_time = 0;
        pulse_intensity = 0;
    }
    
    // Update BPM flash state
    update_bpm_flash();
    
    // Detect new beat (flash state goes from false to true)
    if (bpm_flash_state && !last_flash_state) {
        pulse_start_time = timer_read32();
        pulse_intensity = 255; // Start at full intensity
    }
    last_flash_state = bpm_flash_state;
    
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
    
    // Calculate brightness based on pulse intensity
    uint8_t brightness = (rgb_matrix_config.hsv.v * pulse_intensity) / 255;
    
    // Determine which quadrant to light based on beat count
    // Beat pattern: 1=top-left, 2=top-right, 3=bottom-right, 0=bottom-left
    bool light_top = (bpm_beat_count == 1 || bpm_beat_count == 2);
    bool light_left = (bpm_beat_count == 1 || bpm_beat_count == 0);
    
    // Define quadrant boundaries for 5x14 matrix
    uint8_t row_start = light_top ? 0 : 2;
    uint8_t row_end = light_top ? 2 : 4;
    uint8_t col_start = light_left ? 0 : 7;
    uint8_t col_end = light_left ? 6 : 13;
    
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
                    // Use keyboard's current RGB color with calculated brightness
                    HSV hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, brightness};
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                } else {
                    // Turn off LED when not pulsing or not in active quadrant
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    return false;
}
bool BPM_QUADRANTS(effect_params_t* params) {
    return bpm_quadrants_runner(params);
}
