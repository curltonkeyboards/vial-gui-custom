#pragma once

#include <stdint.h>
#include <stdbool.h>

// Dedicated hardware timer for loop/BPM timing using TIM5.
//
// TIM5 is a 32-bit general purpose timer on the STM32F412 that runs
// completely in hardware, independent of the ChibiOS system tick and
// the main task loop.  Reading it is a single register load — no locks,
// no ISR interaction, no scheduler dependency.
//
// This means EEPROM writes, HID processing, RGB matrix updates, OLED
// refreshes, and any other heavy work in the main loop cannot delay or
// skew the timestamps used by the loop/BPM engine.
//
// Resolution: 1 microsecond (prescaler = sysclk/1MHz)
// Range:      ~4295 seconds (~71 minutes) before 32-bit overflow
//
// Call loop_timer_init() once at startup (before any macro playback).
// Then use loop_timer_read_ms() everywhere you previously used
// timer_read32() for loop timing.

void     loop_timer_init(void);
uint32_t loop_timer_read_ms(void);
uint32_t loop_timer_read_us(void);
uint32_t loop_timer_elapsed_ms(uint32_t last);
uint32_t loop_timer_elapsed_us(uint32_t last);
