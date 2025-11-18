#include "orthomidi5x14.h"

typedef HSV (*smartchord_f)(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint16_t tick);

bool effect_runner_smartchord(uint8_t start, effect_params_t* params, smartchord_f effect_func) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);

    // Define the color mappings for each chord key index
    RGB colors[] = {
        {255, 176, 0},  // Color for chordkey1 and chordkey1_led_index2
        {255, 176, 0},  // Color for chordkey1_led_index2
        {220, 38, 127}, // Color for chordkey2 and chordkey2_led_index2
        {220, 38, 127}, // Color for chordkey2_led_index2
        {254, 97, 0},   // Color for chordkey3 and chordkey3_led_index2
        {254, 97, 0},   // Color for chordkey3_led_index2
        {120, 94, 240}, // Color for chordkey4 and chordkey4_led_index2
        {120, 94, 240}, // Color for chordkey4_led_index2
        {0, 60, 178},   // Color for chordkey5 and chordkey5_led_index2
        {0, 60, 178},   // Color for chordkey5_led_index2
        {100, 143, 255},// Color for chordkey6 and chordkey6_led_index2
        {100, 143, 255},// Color for chordkey6_led_index2
        {0, 158, 115}   // Color for chordkey7 and chordkey7_led_index2
    };

    // Map each chord key index to its color
    uint8_t led_indices[] = {
        chordkey1_led_index, chordkey1_led_index2,
        chordkey2_led_index, chordkey2_led_index2,
        chordkey3_led_index, chordkey3_led_index2,
        chordkey4_led_index, chordkey4_led_index2,
        chordkey5_led_index, chordkey5_led_index2,
        chordkey6_led_index, chordkey6_led_index2,
        chordkey7_led_index, chordkey7_led_index2
    };

    // Reset all LEDs to off or default state
    for (uint8_t i = led_min; i < led_max; i++) {
        rgb_matrix_set_color(i, 1, 1, 1); // Turn off all LEDs
    }

    uint8_t count = g_last_hit_tracker.count;

    if (smartchordstatus != 0) {
        for (uint8_t j = start; j < count; j++) {       
            int16_t hit_x = g_last_hit_tracker.x[j];
            int16_t hit_y = g_last_hit_tracker.y[j];

            for (uint8_t k = 0; k < sizeof(led_indices)/sizeof(led_indices[0]); k++) {
                uint8_t addkey = led_indices[k];
                if (addkey < led_max) {
                    int16_t dx = g_led_config.point[addkey].x - hit_x;
                    int16_t dy = g_led_config.point[addkey].y - hit_y;
                    uint8_t dist = sqrt16(dx * dx + dy * dy);
                    HSV hsv = rgb_matrix_config.hsv;
                    hsv.v = rgb_matrix_config.hsv.v; // Use the configured brightness
                    hsv = effect_func(hsv, dx, dy, dist, 1); // Pass 1 as tick
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(addkey, rgb.r, rgb.g, rgb.b);
                }
            }
        }
    } else {
        uint16_t tick = 65535 / qadd8(rgb_matrix_config.speed, 1);
        for (uint8_t i = led_min; i < led_max; i++) {
            for (uint8_t j = start; j < count; j++) {
                if (g_last_hit_tracker.index[j] == i) {
                    int16_t dx = g_led_config.point[i].x - g_last_hit_tracker.x[j];
                    int16_t dy = g_led_config.point[i].y - g_last_hit_tracker.y[j];
                    uint8_t dist = sqrt16(dx * dx + dy * dy);
                    HSV hsv = rgb_matrix_config.hsv;
                    hsv.v = rgb_matrix_config.hsv.v; // Use the configured brightness
                    hsv = effect_func(hsv, dx, dy, dist, tick);
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
                } else {
                    rgb_matrix_set_color(i, 2, 2, 2); // Ensure the LED is off if no key is matched
                }
            }
        }
    }

    // Apply specific colors to defined chord keys
    for (uint8_t i = 0; i < sizeof(led_indices) / sizeof(led_indices[0]); i++) {
        uint8_t led_index = led_indices[i];
        if (led_index < led_max) {
            rgb_matrix_set_color(led_index, colors[i].r, colors[i].g, colors[i].b);
        }
    }

    return rgb_matrix_check_finished_leds(led_max);
}




RGB_MATRIX_EFFECT(SMARTCHORD_LIGHTS)

static HSV SMARTCHORD_LIGHTS_math(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint16_t tick) {
    uint16_t effect = dist * 1 / 8;
    if (effect > 255) effect = 255;
    hsv.h = scale16by8(g_rgb_timer, 8); // Use a fixed value instead of speed
    hsv.v = qadd8(hsv.v, 255 - effect);
    return hsv;
}


bool SMARTCHORD_LIGHTS(effect_params_t* params) {
    return effect_runner_smartchord(0, params, &SMARTCHORD_LIGHTS_math);
}
