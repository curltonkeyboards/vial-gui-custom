#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(MIDIswitch1)
RGB_MATRIX_EFFECT(LAYERSETS)
typedef HSV (*keycode_category_f)(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint16_t tick);

bool effect_runner_keycode_category(effect_params_t* params) {
    RGB_MATRIX_USE_LIMITS(led_min, led_max);
    
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    
    // Get current RGB matrix settings as the base
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    
    // Set all LEDs to dim base color first
    for (uint8_t i = led_min; i < led_max; i++) {
        HSV hsv = {base_hue, base_sat / 10, base_val / 10}; // Very dim base color
        RGB rgb = hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }
    
    // Hue offsets from base color for each category (in 0-255 range)
    int16_t hue_offsets[29] = {
        0,    // 0 (off - same as base)
        0,    // 1 (Red - same as base)
        0,    // 2 (Default Red - same as base) 
        0,    // 3 (Default Red - same as base)
        213,  // 4 (Purple - add 213 to base hue)
        43,   // 5 (Yellow - add 43 to base hue)
        28,   // 6 (Orange - add 28 to base hue)
        128,  // 7 (Cyan - add 128 to base hue)
        0,    // 8 (White - special case)
        0,    // 9 (Dark Red - same hue as base)
        85,   // 10 (Dark Green - add 85 to base hue)
        170,  // 11 (Dark Blue - add 170 to base hue)
        43,   // 12 (Olive - add 43 to base hue)
        213,  // 13 (Dark Purple - add 213 to base hue)
        128,  // 14 (Teal - add 128 to base hue)
        0,    // 15 (Silver - special case)
        38,   // 16 (Khaki - add 38 to base hue)
        248,  // 17 (Pink - add 248 to base hue)
        23,   // 18 (Dark Orange - add 23 to base hue)
        60,   // 19 (Yellow Green - add 60 to base hue)
        192,  // 20 (Blue Violet - add 192 to base hue)
        11,   // 21 (Dark Salmon - add 11 to base hue)
        126,  // 22 (Light Sea Green - add 126 to base hue)
        36,   // 23 (Gold - add 36 to base hue)
        38,   // 24 (Khaki - add 38 to base hue)
        213,  // 25 (Thistle - add 213 to base hue)
        6,    // 26 (Tomato - add 6 to base hue)
        147,  // 27 (Steel Blue - add 147 to base hue)
        241   // 28 (Pale Violet Red - add 241 to base hue)
    };
    
    // Create modified arrays for split status
    int16_t modified_hue_offsets[29];
    
    for (int i = 0; i < 29; i++) {
        modified_hue_offsets[i] = hue_offsets[i];
    }
    
    if ((keysplitstatus != 0) || (keysplittransposestatus != 0) || (keysplitvelocitystatus != 0)) {
        modified_hue_offsets[2] = 170;    // Blue offset (keysplit enabled)
    }

    if ((keysplitstatus == 2) || (keysplitstatus == 3) || (keysplittransposestatus == 2) || (keysplittransposestatus == 3) || (keysplitvelocitystatus == 2) || (keysplitvelocitystatus == 3)) {
        modified_hue_offsets[1] = 85;     // Green offset (triplesplit enabled)
    }
    
    for (uint8_t i = 0; i < led_categories[current_layer].count; i++) {
        uint8_t led_index = led_categories[current_layer].leds[i].led_index;
        uint8_t category = led_categories[current_layer].leds[i].category;
        
        if (category < 29) {
            HSV hsv;
            
            // Calculate hue by adding offset to base hue
            hsv.h = (base_hue + modified_hue_offsets[category]) % 256;
            
            // Use base saturation for all categories except category 0
            if (category == 0) {
                hsv.s = 0;  // Keep "off" category as grayscale
            } else {
                hsv.s = base_sat;  // All other categories use base saturation
            }
            
            // Use base brightness for all categories, except category 0 which stays dim
            if (category == 0) {
                hsv.v = 1;  // Keep "off" category very dim
            } else {
                hsv.v = base_val;  // All other categories use base brightness
            }
            
            RGB rgb = hsv_to_rgb(hsv);
            rgb_matrix_set_color(led_index, rgb.r, rgb.g, rgb.b);
        }
    }
    return rgb_matrix_check_finished_leds(led_max);
}

bool MIDIswitch1(effect_params_t* params) {
    return effect_runner_keycode_category(params);
}

bool LAYERSETS(effect_params_t* params) {
    return false;
}