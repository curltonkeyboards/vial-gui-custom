#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(REACTIVE_FIREWORKS)

bool effect_runner_reactive_fireworks(effect_params_t* params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    uint8_t count = g_last_hit_tracker.count;
    
    for (uint8_t i = led_min; i < led_max; i++) {
        RGB_MATRIX_TEST_LED_FLAGS();
        HSV hsv = rgb_matrix_config.hsv;
        hsv.v = 0; // Start with everything off
        
        for (uint8_t j = 0; j < count; j++) {
            int16_t dx = g_led_config.point[i].x - g_last_hit_tracker.x[j];
            int16_t dy = g_led_config.point[i].y - g_last_hit_tracker.y[j];
            uint8_t dist = sqrt16(dx * dx + dy * dy);
            uint16_t tick = scale16by8(g_last_hit_tracker.tick[j], qadd8(rgb_matrix_config.speed, 1));
            
            // Effect lasts for 255 ticks
            if (tick < 255) {
                uint8_t intensity = 0;
                
                // Calculate angle from center to this LED (0-255 range)
                uint8_t led_angle = 0;
                if (dx != 0 || dy != 0) {
                    // Simple angle calculation using atan2-like approach
                    if (abs(dx) >= abs(dy)) {
                        // Horizontal dominant
                        led_angle = 64 + (dy * 32) / (abs(dx) + 1);
                        if (dx < 0) led_angle = 128 - led_angle;
                    } else {
                        // Vertical dominant  
                        led_angle = 32 - (dx * 32) / (abs(dy) + 1);
                        if (dy < 0) led_angle = 128 + led_angle;
                    }
                    led_angle = led_angle & 0xFF; // Keep in 0-255 range
                }
                
                // Rotating base angle based on time and speed
                uint8_t base_angle = (tick * 2) & 0xFF; // Rotation speed
                
                // Create 3 lines spaced 120 degrees apart (85 units in 0-255 scale)
                uint8_t line1_angle = base_angle;
                uint8_t line2_angle = (base_angle + 85) & 0xFF;   // 120 degrees
                uint8_t line3_angle = (base_angle + 170) & 0xFF;  // 240 degrees
                
                // Check if LED is close to any of the 3 lines
                uint8_t line_width = 8; // How wide each line is
                
                // Distance to line 1
                uint8_t dist1 = abs(led_angle - line1_angle);
                if (dist1 > 128) dist1 = 256 - dist1; // Handle wraparound
                
                // Distance to line 2
                uint8_t dist2 = abs(led_angle - line2_angle);
                if (dist2 > 128) dist2 = 256 - dist2;
                
                // Distance to line 3
                uint8_t dist3 = abs(led_angle - line3_angle);
                if (dist3 > 128) dist3 = 256 - dist3;
                
                // Light up if close to any line and within distance range
                if (dist > 2 && dist < 40) { // Exclude center, extend to edges
                    if (dist1 < line_width) {
                        intensity = qadd8(intensity, 255 - (dist * 6) - (tick >> 1));
                        hsv.h = qadd8(rgb_matrix_config.hsv.h, tick >> 2);
                    }
                    if (dist2 < line_width) {
                        intensity = qadd8(intensity, 255 - (dist * 6) - (tick >> 1));
                        hsv.h = qadd8(rgb_matrix_config.hsv.h, 85 + (tick >> 2));
                    }
                    if (dist3 < line_width) {
                        intensity = qadd8(intensity, 255 - (dist * 6) - (tick >> 1));
                        hsv.h = qadd8(rgb_matrix_config.hsv.h, 170 + (tick >> 2));
                    }
                }
                
                // Add center glow
                if (dist < 5) {
                    intensity = qadd8(intensity, 255 - (dist * 30) - (tick >> 2));
                    hsv.h = qadd8(rgb_matrix_config.hsv.h, tick);
                }
                
                if (intensity > hsv.v) {
                    hsv.v = intensity > 255 ? 255 : intensity;
                    hsv.s = rgb_matrix_config.hsv.s;
                }
            }
        }
        
        hsv.v = scale8(hsv.v, rgb_matrix_config.hsv.v);
        RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    return rgb_matrix_check_finished_leds(led_max);
}

bool REACTIVE_FIREWORKS(effect_params_t* params) {
    return effect_runner_reactive_fireworks(params);
}