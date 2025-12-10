/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Per-Key RGB Feature - Header File */

#pragma once

#include "quantum.h"
#include "rgb_matrix.h"

// Per-Key RGB Configuration
#define PER_KEY_PALETTE_SIZE 16        // 16 colors in palette
#define PER_KEY_NUM_PRESETS 12         // 12 per-key presets
#define PER_KEY_NUM_LEDS 70            // 70 LEDs (5x14 matrix)

// EEPROM Layout
#define PER_KEY_RGB_EEPROM_ADDR 67940
#define PER_KEY_PALETTE_SIZE_BYTES (PER_KEY_PALETTE_SIZE * 3)  // 16 colors × 3 bytes (HSV) = 48 bytes
#define PER_KEY_PRESET_SIZE_BYTES PER_KEY_NUM_LEDS             // 70 bytes per preset (palette indices)
#define PER_KEY_TOTAL_PRESETS_SIZE (PER_KEY_NUM_PRESETS * PER_KEY_PRESET_SIZE_BYTES) // 840 bytes
#define PER_KEY_MAGIC_ADDR (PER_KEY_RGB_EEPROM_ADDR + PER_KEY_PALETTE_SIZE_BYTES + PER_KEY_TOTAL_PRESETS_SIZE)
#define PER_KEY_MAGIC_NUMBER 0xC0DE

// Total: 48 (palette) + 840 (presets) + 2 (magic) = 890 bytes

// Data Structures
typedef struct {
    HSV palette[PER_KEY_PALETTE_SIZE];           // Global 16-color palette (48 bytes)
    uint8_t presets[PER_KEY_NUM_PRESETS][PER_KEY_NUM_LEDS]; // 12 presets × 70 LEDs (840 bytes)
} per_key_rgb_config_t;

// Global instance (in RAM)
extern per_key_rgb_config_t per_key_rgb_config;
extern bool per_key_rgb_initialized;

// Function declarations
void per_key_rgb_init(void);
void per_key_rgb_load_from_eeprom(void);
void per_key_rgb_save_to_eeprom(void);
void per_key_rgb_reset_to_defaults(void);

// Get color for a specific LED in a specific preset
HSV per_key_get_color(uint8_t preset, uint8_t led_index);

// Set per-key palette color
void per_key_set_palette_color(uint8_t palette_index, uint8_t h, uint8_t s, uint8_t v);

// Set per-key LED color (by palette index)
void per_key_set_led_color(uint8_t preset, uint8_t led_index, uint8_t palette_index);

// Get per-key data for protocol
void per_key_get_palette(uint8_t *data);
void per_key_get_preset_data(uint8_t preset, uint8_t offset, uint8_t count, uint8_t *data);
