#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(COMET_TRAIL)

bool effect_runner_comet_trail(effect_params_t* params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    
    for (uint8_t i = led_min; i < led_max; i++) {
        RGB_MATRIX_TEST_LED_FLAGS();
        HSV hsv = rgb_matrix_config.hsv;
        
        // Get LED position
        uint8_t x = g_led_config.point[i].x;
        uint8_t y = g_led_config.point[i].y;
        
        // Comet position moves diagonally across keyboard
        uint16_t time = scale16by8(g_rgb_timer, rgb_matrix_config.speed);
        uint8_t comet_x = (time * 2) % 224;
        uint8_t comet_y = (time) % 64;
        
        // Calculate distance from comet head
        uint8_t dx = abs(x - comet_x);
        uint8_t dy = abs(y - comet_y);
        uint8_t dist = sqrt16(dx * dx + dy * dy);
        
        uint8_t intensity = 0;
        
        // Comet head (brightest point)
        if (dist < 8) {
            intensity = 255 - (dist * 30);
        }
        // Comet tail (fades behind the head)
        else if (x < comet_x && dist < 20) {
            intensity = 150 - (dist * 7);
        }
        
        hsv.v = intensity;
        // Slowly shifting hue based on base hue
        hsv.h = qadd8(rgb_matrix_config.hsv.h, time >> 3);
        
        hsv.v = scale8(hsv.v, rgb_matrix_config.hsv.v);
        RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    return rgb_matrix_check_finished_leds(led_max);
}

bool COMET_TRAIL(effect_params_t* params) {
    return effect_runner_comet_trail(params);
}