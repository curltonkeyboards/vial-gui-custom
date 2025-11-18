#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(REACTIVE_RIPPLE)

bool effect_runner_reactive_ripple(effect_params_t* params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    uint8_t count = g_last_hit_tracker.count;
    
    for (uint8_t i = led_min; i < led_max; i++) {
        RGB_MATRIX_TEST_LED_FLAGS();
        HSV hsv = rgb_matrix_config.hsv;
        hsv.v = 0;
        
        for (uint8_t j = 0; j < count; j++) {
            int16_t dx = g_led_config.point[i].x - g_last_hit_tracker.x[j];
            int16_t dy = g_led_config.point[i].y - g_last_hit_tracker.y[j];
            uint8_t dist = sqrt16(dx * dx + dy * dy);
            uint16_t tick = scale16by8(g_last_hit_tracker.tick[j], qadd8(rgb_matrix_config.speed, 1));
            
            // Ripple effect logic - create multiple concentric rings
            uint16_t ripple_time = tick >> 1;
            
            // Create three ripple rings with different speeds and intensities
            uint8_t ring1 = abs(dist - ripple_time) < 8 ? 255 - abs(dist - ripple_time) * 32 : 0;
            uint8_t ring2 = abs(dist - (ripple_time >> 1)) < 4 ? 128 - abs(dist - (ripple_time >> 1)) * 32 : 0;
            uint8_t ring3 = abs(dist - (ripple_time >> 2)) < 2 ? 64 - abs(dist - (ripple_time >> 2)) * 32 : 0;
            
            uint8_t intensity = qadd8(ring1, qadd8(ring2, ring3));
            
            // Fade out over time
            if (tick > 100) {
                intensity = scale8(intensity, 255 - ((tick - 100) * 2));
            }
            
            if (intensity > hsv.v) {
                hsv.v = intensity;
                // Color varies with distance while respecting base hue
                hsv.h = qadd8(rgb_matrix_config.hsv.h, dist >> 2);
            }
        }
        
        hsv.v = scale8(hsv.v, rgb_matrix_config.hsv.v);
        RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    return rgb_matrix_check_finished_leds(led_max);
}

bool REACTIVE_RIPPLE(effect_params_t* params) {
    return effect_runner_reactive_ripple(params);
}