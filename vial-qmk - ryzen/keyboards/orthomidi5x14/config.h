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
#define ENCODERS_PAD_A { C14, B5}
#define ENCODERS_PAD_B { C13, B4}
//#define ENCODER_RESOLUTION 4

// Encoder click buttons (push functionality)
#define ENCODER_CLICK_PINS { B12, B13 }

// Sustain pedal pin
#define SUSTAIN_PEDAL_PIN B10

// MIDI Serial Configuration
// Hardware MIDI In/Out on USART3 using pins 45/46 (PB8/PB9)
// PB8: USART3_RX (AF7) - MIDI IN (pin 45)
// PB9: USART3_TX (AF7) - MIDI OUT (pin 46)
#define MIDI_SERIAL_PORT SD3  // Use USART3 for MIDI serial
#define SD3_TX_PIN B9         // MIDI OUT - TX pin on PB9 (pin 46)
#define SD3_RX_PIN B8         // MIDI IN - RX pin on PB8 (pin 45)

// Updated for CAT24C512WI-GT3 (64KB EEPROM)
#define EEPROM_I2C_CAT24C512

// Allocate 20KB for VIA text macros (addresses 1817-21999)
// This prevents macros from overwriting custom features starting at 22000
#define DYNAMIC_KEYMAP_EEPROM_MAX_ADDR 21999

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
#define WS2812_DI_PIN B3
#define WS2812_EXTERNAL_PULLUP 
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

#define MATRIX_ROWS 5   // 5 physical rows (ADC1-ADC5) + 1 virtual row for encoder clicks and sustain pedal
#define MATRIX_COLS 14  // 14 columns

// ADC-capable pins for reading row analog values
// Each ADC pin reads one row of Hall effect sensors
#define MATRIX_ROW_PINS { A0, A1, A2, A3, A4 }
//                        ADC1 ADC2 ADC3 ADC4 ADC5 (PA0-PA4, pins 10-14)

// ============================================================================
// ADG706 MULTIPLEXER PINS (from your PCB)
// ============================================================================

// Address pins (4-bit binary for selecting 1 of 16 channels)
// Your PCB uses channels 0-13 for 14 columns
#define ADG706_A0 A5  // MUX1_A (PA5, pin 15) - Address bit 0 (LSB)
#define ADG706_A1 A6  // MUX1_B (PA6, pin 16) - Address bit 1
#define ADG706_A2 A7  // MUX1_C (PA7, pin 17) - Address bit 2
#define ADG706_A3 A8  // MUX1_D (PA8, pin 18) - Address bit 3 (MSB)

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

// ADC calibration values (measure and adjust if needed!)
// Defaults assume typical Hall effect sensor behavior:
// - Rest: ~3000 ADC value
// - Full press: ~2100 ADC value
// #define DEFAULT_ZERO_TRAVEL_VALUE 3000
// #define DEFAULT_FULL_RANGE 900

// ============================================================================
// DEBOUNCE
// ============================================================================

#define DEBOUNCE 5

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
