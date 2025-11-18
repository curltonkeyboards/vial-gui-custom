#include "orthomidi5x14.h"

typedef HSV (*smartchord_f)(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint16_t tick);

bool effect_runner_smartchord(uint8_t start, effect_params_t* params, smartchord_f effect_func) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);

    // Define the color mappings for each chord key index
    RGB colors[42]; // Declare the colors array to cover chordkey1-7 and their respective LED indices

    if (colorblindmode == 1) {
        // Set colors for colorblind mode
        RGB color_blue = (RGB){255, 176, 0};   // Example for colorblind mode
        RGB color_red = (RGB){220, 38, 127};
        RGB color_green = (RGB){254, 97, 0};
        RGB color_purple = (RGB){200, 50, 200};
        RGB color_yellow = (RGB){255, 255, 0};
        RGB color_orange = (RGB){255, 165, 0};
        RGB color_cyan = (RGB){0, 255, 255};   // Example cyan for chordkey7
        
        // Set specific colors for colorblind mode
        for (uint8_t i = 0; i < 6; i++) {
            // Blue for chordkey1
            colors[i] = color_blue;
            // Red for chordkey2
            colors[i + 6] = color_red;
            // Green for chordkey3
            colors[i + 12] = color_green;
            // Purple for chordkey4
            colors[i + 18] = color_purple;
            // Yellow for chordkey5
            colors[i + 24] = color_yellow;
            // Orange for chordkey6
            colors[i + 30] = color_orange;
            // Cyan for chordkey7
            colors[i + 36] = color_cyan;
        }
    } else {
        // Set colors for normal mode
        RGB color_blue = (RGB){0, 0, 255};     // Blue
        RGB color_red = (RGB){255, 0, 0};      // Red
        RGB color_green = (RGB){0, 255, 0};    // Green
        RGB color_purple = (RGB){255, 0, 255}; // Purple
        RGB color_yellow = (RGB){255, 255, 0}; // Yellow
        RGB color_orange = (RGB){255, 165, 0}; // Orange
        RGB color_cyan = (RGB){0, 255, 255};   // Cyan for chordkey7
        
        // Set specific colors for normal mode
        for (uint8_t i = 0; i < 6; i++) {
            // Blue for chordkey1
            colors[i] = color_blue;
            // Red for chordkey2
            colors[i + 6] = color_red;
            // Green for chordkey3
            colors[i + 12] = color_green;
            // Purple for chordkey4
            colors[i + 18] = color_purple;
            // Yellow for chordkey5
            colors[i + 24] = color_yellow;
            // Orange for chordkey6
            colors[i + 30] = color_orange;
            // Cyan for chordkey7
            colors[i + 36] = color_cyan;
        }
    }

    // Array of LED indices for chord keys
    uint8_t led_indices[] = {
        chordkey1_led_index, chordkey1_led_index2, chordkey1_led_index3, chordkey1_led_index4, chordkey1_led_index5, chordkey1_led_index6,
        chordkey2_led_index, chordkey2_led_index2, chordkey2_led_index3, chordkey2_led_index4, chordkey2_led_index5, chordkey2_led_index6,
        chordkey3_led_index, chordkey3_led_index2, chordkey3_led_index3, chordkey3_led_index4, chordkey3_led_index5, chordkey3_led_index6,
        chordkey4_led_index, chordkey4_led_index2, chordkey4_led_index3, chordkey4_led_index4, chordkey4_led_index5, chordkey4_led_index6,
        chordkey5_led_index, chordkey5_led_index2, chordkey5_led_index3, chordkey5_led_index4, chordkey5_led_index5, chordkey5_led_index6,
        chordkey6_led_index, chordkey6_led_index2, chordkey6_led_index3, chordkey6_led_index4, chordkey6_led_index5, chordkey6_led_index6,
        chordkey7_led_index, chordkey7_led_index2, chordkey7_led_index3, chordkey7_led_index4, chordkey7_led_index5, chordkey7_led_index6
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

            for (uint8_t k = 0; k < sizeof(led_indices) / sizeof(led_indices[0]); k++) {
                uint8_t addkey = led_indices[k];
                if (addkey < led_max) {
                    int16_t dx = g_led_config.point[addkey].x - hit_x;
                    int16_t dy = g_led_config.point[addkey].y - hit_y;
                    uint8_t dist = sqrt16(dx * dx + dy * dy);
                    HSV hsv = rgb_matrix_config.hsv;
                    // Here we use the configured brightness
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
                    // Here we use the configured brightness
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
            // Get the base color
            RGB base_color = colors[i];
            
            // Scale the RGB values based on the brightness setting
            // This ensures the chord key colors respect the global brightness setting
            float brightness_factor = (float)rgb_matrix_config.hsv.v / 255.0f;
            RGB adjusted_color = {
                (uint8_t)(base_color.r * brightness_factor),
                (uint8_t)(base_color.g * brightness_factor),
                (uint8_t)(base_color.b * brightness_factor)
            };
            
            rgb_matrix_set_color(led_index, adjusted_color.r, adjusted_color.g, adjusted_color.b);
        }
    }

    return rgb_matrix_check_finished_leds(led_max);
}


RGB_MATRIX_EFFECT(SMARTCHORD_LIGHTS)
static HSV SMARTCHORD_LIGHTS_math(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint16_t tick) {
    uint16_t effect = dist * 1 / 8;
    if (effect > 255) effect = 255;
    hsv.h = scale16by8(g_rgb_timer, 8); // Use a fixed value instead of speed
    
    // Calculate adjustment based on distance, but respect the original brightness
    uint8_t distance_adjustment = 255 - effect;
    
    // Scale the adjustment based on the current brightness
    float scale_factor = (float)hsv.v / 255.0f;
    uint8_t adjusted_value = hsv.v + (uint8_t)(distance_adjustment * scale_factor);
    
    // Ensure we don't exceed the original brightness
    hsv.v = (adjusted_value > hsv.v) ? hsv.v : adjusted_value;
    
    return hsv;
}


bool SMARTCHORD_LIGHTS(effect_params_t* params) {
    return effect_runner_smartchord(0, params, &SMARTCHORD_LIGHTS_math);
}