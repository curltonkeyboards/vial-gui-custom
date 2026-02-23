#include "loop_timer.h"
#include <hal.h>
#include "stm32_tim.h"

// ---------------------------------------------------------------------------
// Dedicated free-running hardware timer for loop / BPM timing (TIM5).
//
// TIM5 on the STM32F412 is a 32-bit general-purpose timer sitting on APB1.
// We configure it as a simple up-counter with a prescaler that yields a
// 1 MHz tick (1 µs resolution).  The counter free-runs from 0 to 0xFFFFFFFF
// (~4295 seconds / 71 minutes) before wrapping.
//
// Reading the counter is a single volatile 32-bit load from the CNT register
// — no locks, no ISR interaction, no ChibiOS scheduler dependency.  This
// makes it immune to jitter caused by EEPROM writes, HID transfers, RGB
// matrix updates, OLED refreshes, or any other heavy work in the main loop.
// ---------------------------------------------------------------------------

#define LOOP_TIMER  STM32_TIM5

void loop_timer_init(void) {
    // Enable TIM5 peripheral clock (APB1)
    rccEnableTIM5(true);
    rccResetTIM5();

    // Stop the timer while configuring
    LOOP_TIMER->CR1 = 0;

    // Prescaler: divide the timer input clock down to 1 MHz.
    // STM32_TIMCLK1 is the APB1 timer clock (48 MHz for this board).
    // PSC register value = (clock / desired_freq) - 1
    LOOP_TIMER->PSC = (uint32_t)((STM32_TIMCLK1 / 1000000U) - 1U);

    // Auto-reload at maximum (free-running 32-bit counter)
    LOOP_TIMER->ARR = 0xFFFFFFFFU;

    // No interrupts, no DMA, no capture/compare — pure counter
    LOOP_TIMER->DIER = 0;
    LOOP_TIMER->SR   = 0;

    // Force an update event to latch the prescaler value, then clear the
    // update flag so it doesn't trigger anything later.
    LOOP_TIMER->EGR = STM32_TIM_EGR_UG;
    LOOP_TIMER->SR  = 0;

    // Start counting (up-direction, no one-pulse, no clock division)
    LOOP_TIMER->CR1 = STM32_TIM_CR1_CEN;
}

uint32_t loop_timer_read_us(void) {
    return LOOP_TIMER->CNT;
}

uint32_t loop_timer_read_ms(void) {
    return LOOP_TIMER->CNT / 1000U;
}

uint32_t loop_timer_elapsed_ms(uint32_t last) {
    uint32_t now = loop_timer_read_ms();
    // Handles 32-bit wrap-around correctly (ms counter wraps at ~4295 s)
    return now - last;
}

uint32_t loop_timer_elapsed_us(uint32_t last) {
    uint32_t now = loop_timer_read_us();
    return now - last;
}
