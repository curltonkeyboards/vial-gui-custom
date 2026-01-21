// Copyright 2023 3yx3yx (@3yx3yx)
// SPDX-License-Identifier: GPL-2.0-or-later  test

#pragma once

/*
 * Feature disable options
 *  These options are also useful to firmware size reduction.
 */

/* disable debug print */
//#define NO_DEBUG

/* disable print */
//#define NO_PRINT

/* disable action features */
//#define NO_ACTION_LAYER
//#define NO_ACTION_TAPPING
//#define NO_ACTION_ONESHOT

#define RAW_USAGE_PAGE 0xFF60
#define RAW_USAGE_ID   0x61

#define MIDI_ADVANCED
#define BOOTMAGIC_LITE_ROW 0
#define BOOTMAGIC_LITE_COLUMN 0

#define WEAR_LEVELING_LOGICAL_SIZE 2048
#define WEAR_LEVELING_BACKING_SIZE (WEAR_LEVELING_LOGICAL_SIZE * 2)

//#define EECONFIG_USER_DATA_SIZE 77


//#define ENCODER_DEFAULT_POS 0x3

#define TAP_CODE_DELAY 10
#define MEDIA_KEY_DELAY 10

#define DYNAMIC_KEYMAP_LAYER_COUNT 12
#define DYNAMIC_MACRO_SIZE 8192


#define ENCODER_MAP_KEY_DELAY 0
#define ENCODERS_PAD_A { C14, C15 }
#define ENCODERS_PAD_B { C13, B4 }
//#define ENCODER_RESOLUTION 4

// Encoder click buttons (push functionality)
#define ENCODER_CLICK_PINS { B14, B15 }

// Sustain pedal / Footswitch pin
#define SUSTAIN_PEDAL_PIN A9

// MIDI Serial Configuration
// Hardware MIDI In/Out on USART1 using PA15/PB3
// PB3: USART1_RX (AF7) - MIDI IN
// PA15: USART1_TX (AF7) - MIDI OUT
// Note: PA15/PB3 are JTAG pins by default, remapped to USART1
#define MIDI_SERIAL_PORT SD1  // Use USART1 for MIDI serial
#define SD1_TX_PIN A15        // MIDI OUT - TX pin on PA15
#define SD1_RX_PIN B3         // MIDI IN - RX pin on PB3
#define SD1_TX_PAL_MODE 7     // Alternate function 7 for USART1
#define SD1_RX_PAL_MODE 7     // Alternate function 7 for USART1

// Updated for CAT24C512WI-GT3 (64KB EEPROM)
#define EEPROM_I2C_CAT24C512
// VIA macros use default range (no artificial limit)

// Joystick/Gaming Controller Configuration
#define JOYSTICK_BUTTON_COUNT 16        // Face buttons, shoulder, dpad, stick clicks
#define JOYSTICK_AXIS_COUNT 6           // Left stick (X,Y), Right stick (X,Y), Triggers (L,R)
#define JOYSTICK_AXIS_RESOLUTION 16     // 16-bit resolution for smooth analog control

#ifdef OLED_ENABLE
#    define OLED_DISPLAY_128X128
#define I2C1_SCL_PIN        B6
#define I2C1_SDA_PIN        B7
#define OLED_BRIGHTNESS 128
#define OLED_TIMEOUT 0
// Add this near your OLED config
#define OLED_USE_DMA  // Enable DMA mode for OLED

// The pin connected to the data pin of the LEDs
#define WS2812_DI_PIN B8
// The number of LEDs connected
#define RGB_MATRIX_LED_COUNT 70




// RGB Matrix Animation modes. Explicitly enabled
// For full list of effects, see:
// https://docs.qmk.fm/#/feature_rgb_matrix?id=rgb-matrix-effects
#define ENABLE_RGB_MATRIX_ALPHAS_MODS
#define ENABLE_RGB_MATRIX_GRADIENT_UP_DOWN
#define ENABLE_RGB_MATRIX_GRADIENT_LEFT_RIGHT
#define ENABLE_RGB_MATRIX_BREATHING
#define ENABLE_RGB_MATRIX_BAND_SAT
#define ENABLE_RGB_MATRIX_BAND_VAL
#define ENABLE_RGB_MATRIX_BAND_PINWHEEL_SAT
#define ENABLE_RGB_MATRIX_BAND_PINWHEEL_VAL
#define ENABLE_RGB_MATRIX_BAND_SPIRAL_SAT
#define ENABLE_RGB_MATRIX_BAND_SPIRAL_VAL
#define ENABLE_RGB_MATRIX_CYCLE_ALL
#define ENABLE_RGB_MATRIX_CYCLE_LEFT_RIGHT
#define ENABLE_RGB_MATRIX_CYCLE_UP_DOWN
#define ENABLE_RGB_MATRIX_RAINBOW_MOVING_CHEVRON
#define ENABLE_RGB_MATRIX_CYCLE_OUT_IN
#define ENABLE_RGB_MATRIX_CYCLE_OUT_IN_DUAL
#define ENABLE_RGB_MATRIX_CYCLE_PINWHEEL
#define ENABLE_RGB_MATRIX_CYCLE_SPIRAL
#define ENABLE_RGB_MATRIX_DUAL_BEACON
#define ENABLE_RGB_MATRIX_RAINBOW_BEACON
#define ENABLE_RGB_MATRIX_RAINBOW_PINWHEELS
#define ENABLE_RGB_MATRIX_RAINDROPS
#define ENABLE_RGB_MATRIX_JELLYBEAN_RAINDROPS
#define ENABLE_RGB_MATRIX_HUE_BREATHING
#define ENABLE_RGB_MATRIX_HUE_PENDULUM
#define ENABLE_RGB_MATRIX_HUE_WAVE
#define ENABLE_RGB_MATRIX_PIXEL_RAIN
#define ENABLE_RGB_MATRIX_PIXEL_FLOW
#define ENABLE_RGB_MATRIX_PIXEL_FRACTAL
//enabled only if RGB_MATRIX_FRAMEBUFFER_EFFECTS is defined
#define ENABLE_RGB_MATRIX_TYPING_HEATMAP
#define ENABLE_RGB_MATRIX_DIGITAL_RAIN
//enabled only of RGB_MATRIX_KEYPRESSES or RGB_MATRIX_KEYRELEASES is defined
#define ENABLE_RGB_MATRIX_SOLID_REACTIVE_SIMPLE
#define ENABLE_RGB_MATRIX_SOLID_REACTIVE
#define ENABLE_RGB_MATRIX_SOLID_REACTIVE_WIDE
#define ENABLE_RGB_MATRIX_SOLID_REACTIVE_MULTIWIDE
#define ENABLE_RGB_MATRIX_SOLID_REACTIVE_CROSS
#define ENABLE_RGB_MATRIX_SOLID_REACTIVE_MULTICROSS
#define ENABLE_RGB_MATRIX_SOLID_REACTIVE_NEXUS
#define ENABLE_RGB_MATRIX_SOLID_REACTIVE_MULTINEXUS
#define ENABLE_RGB_MATRIX_SPLASH
#define ENABLE_RGB_MATRIX_MULTISPLASH
#define ENABLE_RGB_MATRIX_SOLID_SPLASH
#define ENABLE_RGB_MATRIX_SOLID_MULTISPLASH

#define RGB_MATRIX_KEYPRESSES
#define RGB_MATRIX_FRAMEBUFFER_EFFECTS








#define OLED_TIMEOUT 0

#define MATRIX_ROWS 6   // 5 physical rows (ADC1-ADC5) + 1 virtual row for encoders/sustain
#define MATRIX_COLS 14  // 14 columns (mux channels 0-13)

// ADC-capable pins for reading row analog values
// Each ADC pin reads one row of Hall effect sensors
// PCB wiring: ADC1=PA4 (row 0), ADC2=PA3 (row 1), ADC3=PA2 (row 2), ADC4=PA1 (row 3), ADC5=PA0 (row 4)
// Reversed order so firmware row 0 = physical row 0
// Row 5 is virtual (encoder clicks + sustain pedal via GPIO polling, not ADC)
#define MATRIX_ROW_PINS { A4, A3, A2, A1, A0, NO_PIN }
//                        PA4  PA3  PA2  PA1  PA0  (virtual)

// ============================================================================
// ADG706 MULTIPLEXER PINS (from your PCB)
// ============================================================================

// Address pins - PCB wiring:
// MUXA (A0) = PA5
// MUXB (A1) = PA6
// MUXC (A2) = PA7
// MUXD (A3) = PB0
#define ADG706_A0 A5      // PA5 = MUXA - Address bit 0 (LSB)
#define ADG706_A1 A6      // PA6 = MUXB - Address bit 1
#define ADG706_A2 A7      // PA7 = MUXC - Address bit 2
#define ADG706_A3 B0      // PB0 = MUXD - Address bit 3 (MSB)

// Enable pin (active LOW)
// NOTE: If your ADG706 EN pin is hardwired to GND (always enabled),
// you can set this to NO_PIN. Otherwise, define the actual pin.
#define ADG706_EN NO_PIN  // ← Change if you have EN connected to a GPIO

// If EN is connected to a GPIO, uncomment and set the correct pin:
// #define ADG706_EN B0  // Example: PB0

// ============================================================================
// STM32F412 SPECIFIC NOTES
// ============================================================================

// Your STM32F412 ADC pins:
// - ADC1: PA0 (ADC12_IN0)
// - ADC2: PA1 (ADC12_IN1)
// - ADC3: PA2 (ADC12_IN2)
// - ADC4: PA3 (ADC12_IN3)
// - ADC5: PA4 (ADC12_IN4)
//
// All on ADC1 peripheral, channels 0-4
// STM32F412 has ADC1 only (single ADC)

// ============================================================================
// OPTIONAL: ANALOG SETTINGS (override defaults from matrix.h)
// ============================================================================

// Only uncomment these if your sensors behave differently than defaults

// Actuation point (default: 20 = 2.0mm)
// #define DEFAULT_ACTUATION_POINT 20

// Rapid trigger sensitivity (default: 4 = 0.4mm)
// #define DEFAULT_RAPID_TRIGGER_SENSITIVITY 4

// ADC calibration values (measured from actual hardware)
// Your Hall effect sensors read:
// - Rest: ~1650-2250 ADC (average ~2000)
// - Full press: ~1100-1350 ADC (bottom ~1100)
// - Travel range: ~900 counts
#define DEFAULT_ZERO_TRAVEL_VALUE 2000
#define DEFAULT_FULL_RANGE 900

// ============================================================================
// DEBOUNCE
// ============================================================================

// TROUBLESHOOTING: Disabled debounce - HE sensors don't need it
#define DEBOUNCE 0

// ============================================================================
// HARDWARE NOTES FOR YOUR PCB
// ============================================================================
//
// Pin Mapping Summary:
// --------------------
// PA0 (pin 10) → ADC1 → Row 0
// PA1 (pin 11) → ADC2 → Row 1
// PA2 (pin 12) → ADC3 → Row 2
// PA3 (pin 13) → ADC4 → Row 3
// PA4 (pin 14) → ADC5 → Row 4
//
// PA5 (pin 15) → MUX1_A → ADG706 A0 (address bit 0)
// PA6 (pin 16) → MUX1_B → ADG706 A1 (address bit 1)
// PA7 (pin 17) → MUX1_C → ADG706 A2 (address bit 2)
// PA8 (pin 18) → MUX1_D → ADG706 A3 (address bit 3)
//
// ADG706 Channel Usage:
// ---------------------
// Channels S0-S13 → Your 14 columns
// Channels S14-S15 → Unused
//
// Matrix Layout:
// --------------
// 5 rows × 14 columns = 70 keys total
//
// ============================================================================

#endif
