#include "orthomidi5x14.h"

// BPM_ROW_BACKLIGHT Effect
RGB_MATRIX_EFFECT(BPM_ROW_BACKLIGHT)
static bool bpm_row_backlight_runner(effect_params_t* params) {
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
    
    // Calculate fade progression for beat effect
    uint8_t beat_intensity = 0;
    if (pulse_intensity > 0) {
        uint32_t current_time = timer_read32();
        uint32_t elapsed = current_time - pulse_start_time;
        
        // Pulse duration: use same calculation method as main BPM code
        uint32_t pulse_duration = current_bpm > 0 ? (3000000000ULL / current_bpm) : 250; // ms
        
        if (elapsed < pulse_duration) {
            // Fade out using exponential decay for natural feel
            float progress = (float)elapsed / pulse_duration;
            beat_intensity = (uint8_t)(255 * (1.0f - progress) * (1.0f - progress));
            pulse_intensity = beat_intensity;
        } else {
            pulse_intensity = 0;
            beat_intensity = 0;
        }
    }
    
    // Determine which rows to light based on beat count
    // Beat pattern: 1=rows 0-1, 2=rows 1-2, 3=rows 2-3, 0=rows 3-4
    uint8_t row_start, row_end;
    switch (bpm_beat_count) {
        case 1: row_start = 0; row_end = 1; break;
        case 2: row_start = 1; row_end = 2; break;
        case 3: row_start = 2; row_end = 3; break;
        case 0: row_start = 3; row_end = 4; break;
        default: row_start = 0; row_end = 1; break;
    }
    
    // Render the effect across entire matrix
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                // Check if this LED is in the active rows
                bool in_active_rows = (row >= row_start && row <= row_end);
                
                if (beat_intensity > 0 && in_active_rows) {
                    // Beat effect: hue offset +60 degrees (85 units in HSV)
                    uint8_t beat_brightness = (rgb_matrix_config.hsv.v * beat_intensity) / 255;
                    HSV beat_hsv = {(rgb_matrix_config.hsv.h + 85) % 256, rgb_matrix_config.hsv.s, beat_brightness};
                    RGB beat_rgb = rgb_matrix_hsv_to_rgb(beat_hsv);
                    rgb_matrix_set_color(led[0], beat_rgb.r, beat_rgb.g, beat_rgb.b);
                } else {
                    // Background: use current RGB color at device brightness
                    HSV bg_hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, rgb_matrix_config.hsv.v};
                    RGB bg_rgb = rgb_matrix_hsv_to_rgb(bg_hsv);
                    rgb_matrix_set_color(led[0], bg_rgb.r, bg_rgb.g, bg_rgb.b);
                }
            }
        }
    }
    
    return false;
}
bool BPM_ROW_BACKLIGHT(effect_params_t* params) {
    return bpm_row_backlight_runner(params);
}
