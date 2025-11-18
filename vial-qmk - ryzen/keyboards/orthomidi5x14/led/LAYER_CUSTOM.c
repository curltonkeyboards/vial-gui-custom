#include "orthomidi5x14.h"

RGB_MATRIX_EFFECT(MIDIswitch1)

typedef HSV (*keycode_category_f)(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint16_t tick);

bool effect_runner_keycode_category(effect_params_t* params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    
    // Get current layer
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    
    // First set all LEDs to dim
    for (uint8_t i = led_min; i < led_max; i++) {
        rgb_matrix_set_color(i, 1, 1, 1);
    }
    
    // Define base colors for each category
    RGB colors[9] = {
        {1, 1, 1},       // Category 0 (no category/off)
        {255, 0, 0},     // Category 1 (Red)
        {0, 0, 255},     // Category 2 (Blue)
        {0, 255, 0},     // Category 3 (Green)
        {255, 0, 255},   // Category 4 (Purple)
        {255, 255, 0},   // Category 5 (Yellow)
        {255, 165, 0},   // Category 6 (Orange)
        {0, 255, 255},   // Category 7 (Cyan)
        {255, 255, 255}  // Category 8 (White)
    };
    
    // Only process the LEDs that have categories assigned
    for (uint8_t i = 0; i < led_categories[current_layer].count; i++) {
        uint8_t led_index = led_categories[current_layer].leds[i].led_index;
        uint8_t category = led_categories[current_layer].leds[i].category;
        
        if (category < 9) {
            rgb_matrix_set_color(led_index, 
                colors[category].r,
                colors[category].g,
                colors[category].b);
        }
    }

    return rgb_matrix_check_finished_leds(led_max);
}

bool MIDIswitch1(effect_params_t* params) {
    return effect_runner_keycode_category(params);
}