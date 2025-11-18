#ifdef LED_MATRIX_KEYREACTIVE_ENABLED
#    if defined(ENABLE_LED_MATRIX_SOLID_REACTIVE_CROSS) || defined(ENABLE_LED_MATRIX_SOLID_REACTIVE_MULTICROSS)

#        ifdef ENABLE_LED_MATRIX_SOLID_REACTIVE_CROSS
LED_MATRIX_EFFECT(SOLID_REACTIVE_CROSS)
#        endif

#        ifdef ENABLE_LED_MATRIX_SOLID_REACTIVE_MULTICROSS
LED_MATRIX_EFFECT(SOLID_REACTIVE_MULTICROSS)
#        endif

#        ifdef LED_MATRIX_CUSTOM_EFFECT_IMPLS

static uint8_t SOLID_REACTIVE_CROSS_math(uint8_t val, int16_t dx, int16_t dy, uint8_t dist, uint16_t tick) {
    uint16_t effect = tick + dist;
    dx              = dx < 0 ? dx * -1 : dx;
    dy              = dy < 0 ? dy * -1 : dy;
    if (dx == 2 && dy == 0) { // Light up only the LED that is 2 spaces to the right
        effect = 0; // Make sure this LED is lit up fully
    } else if (dx == 0 && dy == 0) { // Light up the pressed key itself
        effect = 0; // Make sure this LED is lit up fully
    } else {
        effect = 255; // Make sure other LEDs are not lit
    }
    return qadd8(val, 255 - effect);
}


#            ifdef ENABLE_LED_MATRIX_SOLID_REACTIVE_CROSS
bool SOLID_REACTIVE_CROSS(effect_params_t* params) {
    return effect_runner_reactive_splash(qsub8(g_last_hit_tracker.count, 1), params, &SOLID_REACTIVE_CROSS_math);
}
#            endif

#            ifdef ENABLE_LED_MATRIX_SOLID_REACTIVE_MULTICROSS
bool SOLID_REACTIVE_MULTICROSS(effect_params_t* params) {
    return effect_runner_reactive_splash(0, params, &SOLID_REACTIVE_CROSS_math);
}
#            endif

#        endif // LED_MATRIX_CUSTOM_EFFECT_IMPLS
#    endif     // defined(ENABLE_LED_MATRIX_SOLID_REACTIVE_CROSS) || defined(ENABLE_LED_MATRIX_SOLID_REACTIVE_MULTICROSS)
#endif         // LED_MATRIX_KEYREACTIVE_ENABLED
