
#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(PONG)

static bool PONG_runner(effect_params_t* params) {
    static uint8_t ball_x = 7;   // Center X for 5x14 keyboard
    static uint8_t ball_y = 2;   // Center Y
    static int8_t dir_x = 1;     // 1 for right, -1 for left
    static int8_t dir_y = 1;     // 1 for down, -1 for up
    static uint8_t move_timer = 0;
    static uint8_t trail_decay = 0;
    
    if (params->init) {
        rgb_matrix_set_color_all(0, 0, 0);
        ball_x = 7;
        ball_y = 2;
        dir_x = (rand() % 2) ? 1 : -1;
        dir_y = (rand() % 2) ? 1 : -1;
        move_timer = 0;
    }
    
    // Scale movement with RGB speed
    uint8_t speed_threshold = 255 - rgb_matrix_config.speed;
    
    // Move ball diagonally
    if (++move_timer > (speed_threshold / 32 + 1)) {
        move_timer = 0;
        
        // Move diagonally
        ball_x += dir_x;
        ball_y += dir_y;
        
        // Bounce off edges - always maintain diagonal movement
        if (ball_x == 0 || ball_x == 13) {
            dir_x = -dir_x;
        }
        if (ball_y == 0 || ball_y == 4) {
            dir_y = -dir_y;
        }
        
        // Keep ball in bounds
        ball_x = ball_x > 13 ? 13 : ball_x;
        ball_y = ball_y > 4 ? 4 : ball_y;
    }
    
    // Fade trail
    if (++trail_decay > 8) {
        for (uint8_t i = 0; i < RGB_MATRIX_LED_COUNT; i++) {
            rgb_matrix_set_color(i, 0, 0, 0);
        }
        trail_decay = 0;
    }
    
    // Draw ball
    uint8_t led[LED_HITS_TO_REMEMBER];
    uint8_t led_count = rgb_matrix_map_row_column_to_led(ball_y, ball_x, led);
    if (led_count > 0) {
        HSV hsv = rgb_matrix_config.hsv;
        hsv.h += scale16by8(g_rgb_timer, rgb_matrix_config.speed / 4);
        hsv.s = rgb_matrix_config.hsv.s; // Use RGB saturation
        RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
        rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
    }
    
    return false;
}

bool PONG(effect_params_t* params) {
    return PONG_runner(params);
}
