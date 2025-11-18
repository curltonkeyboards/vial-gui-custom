#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(LR_SWEEP_RANDOM)

static bool LR_SWEEP_RANDOM_runner(effect_params_t* params) {
    static uint8_t current_col = 0;
    static int8_t direction = 1; // 1 for right, -1 for left
    static uint8_t move_timer = 0;
    
    if (params->init) {
        current_col = 0;
        direction = 1;
    }
    
    // Move the column
    if (++move_timer > (80 - (rgb_matrix_config.speed / 3))) { // Scale with RGB speed
        move_timer = 0;
        
        // Move in current direction
        current_col += direction;
        
        // Check for bouncing
        if (current_col >= 13) {
            current_col = 13;
            direction = -1;
        } else if (current_col <= 0) {
            current_col = 0;
            direction = 1;
        }
    }
    
    // Render the bouncing column using keyboard's RGB color
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                if (col == current_col) {
                    // Light up the current column with keyboard's current RGB color
                    RGB rgb = rgb_matrix_hsv_to_rgb(rgb_matrix_config.hsv);
                    rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                } else {
                    // Turn off other LEDs
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    return false;
}

bool LR_SWEEP_RANDOM(effect_params_t* params) {
    return LR_SWEEP_RANDOM_runner(params);
}