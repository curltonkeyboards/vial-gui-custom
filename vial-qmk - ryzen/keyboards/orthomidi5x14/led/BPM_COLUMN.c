#include "orthomidi5x14.h"

// BPM_COLUMN Effect
RGB_MATRIX_EFFECT(BPM_COLUMN)
static bool bpm_column_runner(effect_params_t* params) {
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
    
    // Determine which columns to light based on beat count
    // Beat pattern: 1=cols 0-3, 2=cols 4-7, 3=cols 8-11, 0=cols 12-13
    uint8_t col_start, col_end;
    switch (bpm_beat_count) {
        case 1: col_start = 0; col_end = 3; break;
        case 2: col_start = 4; col_end = 7; break;
        case 3: col_start = 8; col_end = 11; break;
        case 0: col_start = 12; col_end = 13; break;
        default: col_start = 0; col_end = 3; break;
    }
    
    // Render the pulse across entire matrix, but only light the active columns
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                // Check if this LED is in the active columns
                bool in_active_columns = (col >= col_start && col <= col_end);
                
                if (pulse_intensity > 0 && in_active_columns) {
                    // Use keyboard's current RGB color with calculated brightness
                    HSV hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, brightness};
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                } else {
                    // Turn off LED when not pulsing or not in active columns
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    return false;
}
bool BPM_COLUMN(effect_params_t* params) {
    return bpm_column_runner(params);
}




