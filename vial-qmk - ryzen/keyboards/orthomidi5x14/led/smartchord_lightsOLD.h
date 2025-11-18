#pragma once

typedef HSV (*smartchord_f)(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint16_t tick);

bool effect_runner_smartchord(uint8_t start, effect_params_t* params, smartchord_f effect_func) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);

    uint8_t count = g_last_hit_tracker.count;
    for (uint8_t i = led_min; i < led_max; i++) {
        RGB_MATRIX_TEST_LED_FLAGS();
        HSV hsv = rgb_matrix_config.hsv;
        hsv.v = 0;

        // Light up the current key
        for (uint8_t j = start; j < count; j++) {
            if (g_last_hit_tracker.index[j] == i) {
                int16_t dx = g_led_config.point[i].x - g_last_hit_tracker.x[j];
                int16_t dy = g_led_config.point[i].y - g_last_hit_tracker.y[j];
                uint8_t dist = sqrt16(dx * dx + dy * dy);
                uint16_t tick = scale16by8(g_last_hit_tracker.tick[j], qadd8(rgb_matrix_config.speed, 1));
                hsv = effect_func(hsv, dx, dy, dist, tick);
                hsv.v = scale8(hsv.v, rgb_matrix_config.hsv.v);
                RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
            }
        }

        // Light up the key two positions to the right
        if (i < led_max - 2) {
            uint8_t right_key = i + 2;
            for (uint8_t j = start; j < count; j++) {
                if (g_last_hit_tracker.index[j] == i) {
                    int16_t dx = g_led_config.point[right_key].x - g_last_hit_tracker.x[j];
                    int16_t dy = g_led_config.point[right_key].y - g_last_hit_tracker.y[j];
                    uint8_t dist = sqrt16(dx * dx + dy * dy);
                    uint16_t tick = scale16by8(g_last_hit_tracker.tick[j], qadd8(rgb_matrix_config.speed, 1));
                    hsv = effect_func(hsv, dx, dy, dist, tick);
                    hsv.v = scale8(hsv.v, rgb_matrix_config.hsv.v);
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(right_key, rgb.r, rgb.g, rgb.b);
                }
            }
        }

        // Light up the key four positions to the right
        if (i < led_max - 4) {
            uint8_t right_key_4 = i + 4;
            for (uint8_t j = start; j < count; j++) {
                if (g_last_hit_tracker.index[j] == i) {
                    int16_t dx = g_led_config.point[right_key_4].x - g_last_hit_tracker.x[j];
                    int16_t dy = g_led_config.point[right_key_4].y - g_last_hit_tracker.y[j];
                    uint8_t dist = sqrt16(dx * dx + dy * dy);
                    uint16_t tick = scale16by8(g_last_hit_tracker.tick[j], qadd8(rgb_matrix_config.speed, 1));
                    hsv = effect_func(hsv, dx, dy, dist, tick);
                    hsv.v = scale8(hsv.v, rgb_matrix_config.hsv.v);
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(right_key_4, rgb.r, rgb.g, rgb.b);
                }
            }
        }
    }
    return rgb_matrix_check_finished_leds(led_max);
}
