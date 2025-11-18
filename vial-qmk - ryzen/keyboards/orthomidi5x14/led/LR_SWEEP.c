#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(LR_SWEEP)

static bool LR_SWEEP_runner(effect_params_t* params) {
    static uint8_t current_col = 0;
    static int8_t direction = 1; // 1 for right, -1 for left
    static uint8_t move_timer = 0;
    static uint8_t current_hue = 0;
    static uint8_t hue_timer = 0;
    
    if (params->init) {
        current_col = 0;
        direction = 1;
        current_hue = 0;
    }
    
    // Update hue for color cycling
    if (++hue_timer > 10) {
        hue_timer = 0;
        current_hue += 2;
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
    
    // Render the bouncing column
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                if (col == current_col) {
                    // Light up the current column
                    HSV hsv = {current_hue, 255, rgb_matrix_config.hsv.v};
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
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

bool LR_SWEEP(effect_params_t* params) {
    return LR_SWEEP_runner(params);
}