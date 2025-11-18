#include "orthomidi5x14.h"

// BPM_ALL Effect
RGB_MATRIX_EFFECT(BPM_ALL)
static bool bpm_all_runner(effect_params_t* params) {
    static bool last_flash_state = false;
    static uint32_t pulse_start_time = 0;
    static uint8_t pulse_intensity = 0;
    static uint8_t all_beat_count = 0; // 0-11 counter for full cycle
    
    if (params->init) {
        last_flash_state = false;
        pulse_start_time = 0;
        pulse_intensity = 0;
        all_beat_count = 0;
    }
    
    // Update BPM flash state
    update_bpm_flash();
    
    // Detect new beat (flash state goes from false to true)
    if (bpm_flash_state && !last_flash_state) {
        pulse_start_time = timer_read32();
        pulse_intensity = 255; // Start at full intensity
        all_beat_count = (all_beat_count + 1) % 12; // Cycle through 0-11
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
    
    // Determine pattern and active area based on all_beat_count
    uint8_t pattern = all_beat_count / 4; // 0=quadrants, 1=rows, 2=columns
    uint8_t beat_in_pattern = all_beat_count % 4; // 0-3 within each pattern
    
    // Render the pulse across entire matrix
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                bool in_active_area = false;
                
                if (pattern == 0) {
                    // Quadrants pattern (beats 0-3 in all_beat_count, which is beats 1-4 visually)
                    // Convert beat_in_pattern to match quadrant logic: 0->1, 1->2, 2->3, 3->0
                    uint8_t quad_beat = (beat_in_pattern + 1) % 4;
                    if (quad_beat == 0) quad_beat = 4; // Make it 1,2,3,4 instead of 1,2,3,0
                    
                    bool light_top = (quad_beat == 1 || quad_beat == 2);
                    bool light_left = (quad_beat == 1 || quad_beat == 4);
                    
                    uint8_t row_start = light_top ? 0 : 2;
                    uint8_t row_end = light_top ? 2 : 4;
                    uint8_t col_start = light_left ? 0 : 7;
                    uint8_t col_end = light_left ? 6 : 13;
                    
                    in_active_area = (row >= row_start && row <= row_end && 
                                    col >= col_start && col <= col_end);
                    
                } else if (pattern == 1) {
                    // Rows pattern (beats 4-7 in all_beat_count, which is beats 1-4 visually)
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
                    
                    in_active_area = (row >= row_start && row <= row_end);
                    
                } else if (pattern == 2) {
                    // Columns pattern (beats 8-11 in all_beat_count, which is beats 1-4 visually)
                    uint8_t col_beat = (beat_in_pattern + 1) % 4;
                    if (col_beat == 0) col_beat = 4;
                    
                    uint8_t col_start, col_end;
                    switch (col_beat) {
                        case 1: col_start = 0; col_end = 3; break;
                        case 2: col_start = 4; col_end = 7; break;
                        case 3: col_start = 8; col_end = 11; break;
                        case 4: col_start = 12; col_end = 13; break;
                        default: col_start = 0; col_end = 3; break;
                    }
                    
                    in_active_area = (col >= col_start && col <= col_end);
                }
                
                if (pulse_intensity > 0 && in_active_area) {
                    // Use keyboard's current RGB color with calculated brightness
                    HSV hsv = {rgb_matrix_config.hsv.h, rgb_matrix_config.hsv.s, brightness};
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                } else {
                    // Turn off LED when not pulsing or not in active area
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    return false;
}
bool BPM_ALL(effect_params_t* params) {
    return bpm_all_runner(params);
}




