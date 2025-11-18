
#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(FIREPLACE)

static bool FIREPLACE_runner(effect_params_t* params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    
    uint8_t time = scale16by8(g_rgb_timer, rgb_matrix_config.speed / 4); // Slower: was /2, now /4
    
    for (uint8_t i = led_min; i < led_max; i++) {
        RGB_MATRIX_TEST_LED_FLAGS();
        
        uint8_t x = g_led_config.point[i].x;
        uint8_t y = g_led_config.point[i].y;
        
        // Flame height decreases from bottom to top
        uint8_t flame_intensity = (5 - y) * 51; // 0-255 range
        
        // Add flickering noise
        uint8_t noise = (sin8(x * 16 + time * 3) + sin8(y * 24 + time * 2)) / 2;
        flame_intensity = scale8(flame_intensity, noise);
        
        // Create flame colors based on current RGB hue
        HSV hsv = rgb_matrix_config.hsv;
        if (flame_intensity > 200) {
            hsv.h += 42; // Shift towards yellow equivalent
        } else if (flame_intensity > 100) {
            hsv.h += 21; // Shift towards orange equivalent
        }
        // else use base hue (red equivalent)
        
        hsv.s = rgb_matrix_config.hsv.s; // Use RGB saturation
        hsv.v = scale8(rgb_matrix_config.hsv.v, flame_intensity);
        
        RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    
    return rgb_matrix_check_finished_leds(led_max);
}

bool FIREPLACE(effect_params_t* params) {
    return FIREPLACE_runner(params);
}