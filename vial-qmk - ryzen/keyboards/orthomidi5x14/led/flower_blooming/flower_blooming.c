#include "led/smartchord_lights.h"

static HSV SMARTCHORD_LIGHTS_math(HSV hsv, uint8_t i, uint8_t time) {
    if (g_led_config.point[i].y > k_rgb_matrix_center.y)
        hsv.h = g_led_config.point[i].x * 3 - g_led_config.point[i].y * 3 + time;
    else
        hsv.h = g_led_config.point[i].x * 3 - g_led_config.point[i].y * 3 - time;
    return hsv;
}

bool FLOWER_BLOOMING(effect_params_t* params) { return effect_runner_smartchord(params, &SMARTCHORD_LIGHTS_math); }



