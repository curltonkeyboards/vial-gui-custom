#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(REACTIVE_LIGHTNING)

bool effect_runner_reactive_lightning(effect_params_t* params) {
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
            
            // Lightning effect logic
            uint8_t lightning_path = (dx ^ dy ^ tick) & 0xFF;
            uint8_t intensity = 0;
            
            // Main lightning bolt - vertical and horizontal lines
            if (lightning_path < 40) {
                if (abs(dx) < 3 || abs(dy) < 3) {
                    intensity = 255 - (dist * 8);
                }
            }
            // Lightning branches - diagonal lines
            else if (lightning_path < 80) {
                if ((abs(dx - dy) < 2) || (abs(dx + dy) < 2)) {
                    intensity = 200 - (dist * 10);
                }
            }
            
            // Flash effect - quick bright flash that fades rapidly
            if (tick < 30) {
                intensity = qadd8(intensity, 255 - (tick * 8));
            }
            
            if (intensity > hsv.v) {
                hsv.v = intensity > 255 ? 255 : intensity;
                // Apply electric color shift while respecting base hue
                hsv.h = qadd8(rgb_matrix_config.hsv.h, tick >> 2);
            }
        }
        
        hsv.v = scale8(hsv.v, rgb_matrix_config.hsv.v);
        RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    return rgb_matrix_check_finished_leds(led_max);
}

bool REACTIVE_LIGHTNING(effect_params_t* params) {
    return effect_runner_reactive_lightning(params);
}