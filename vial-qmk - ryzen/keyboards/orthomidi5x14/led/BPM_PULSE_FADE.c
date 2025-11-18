#include "orthomidi5x14.h"

// BPM_PULSE_FADE Effect
RGB_MATRIX_EFFECT(BPM_PULSE_FADE)
static bool bpm_pulse_fade_runner(effect_params_t* params) {
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
        // For half-beat duration: (6000000000ULL / current_bpm) / 2 = 3000000000ULL / current_bpm
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
    
    // Render the pulse across entire matrix
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                if (pulse_intensity > 0) {
                    // Use keyboard's current RGB color with calculated brightness
                    HSV hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, brightness};
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                } else {
                    // Turn off LED when not pulsing
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    return false;
}
bool BPM_PULSE_FADE(effect_params_t* params) {
    return bpm_pulse_fade_runner(params);
}


