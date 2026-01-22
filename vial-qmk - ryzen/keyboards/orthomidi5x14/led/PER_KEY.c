/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Per-Key RGB Feature - Implementation */

#include "../per_key_rgb.h"
#include "eeconfig.h"

// Global per-key RGB configuration (in RAM)
per_key_rgb_config_t per_key_rgb_config = {0};
bool per_key_rgb_initialized = false;

// Initialize per-key RGB system
void per_key_rgb_init(void) {
    if (per_key_rgb_initialized) return;

    // Check if EEPROM has valid data
    uint16_t magic = eeprom_read_word((uint16_t*)PER_KEY_MAGIC_ADDR);

    if (magic == PER_KEY_MAGIC_NUMBER) {
        // Load from EEPROM
        per_key_rgb_load_from_eeprom();
    } else {
        // First time - initialize with defaults
        per_key_rgb_reset_to_defaults();
        per_key_rgb_save_to_eeprom();
    }

    per_key_rgb_initialized = true;
}

// Reset to default values
void per_key_rgb_reset_to_defaults(void) {
    // Default palette: Common colors
    // Palette index 0: Black (off)
    per_key_rgb_config.palette[0] = (HSV){0, 0, 0};
    // Palette index 1: Red
    per_key_rgb_config.palette[1] = (HSV){0, 255, 255};
    // Palette index 2: Orange
    per_key_rgb_config.palette[2] = (HSV){28, 255, 255};
    // Palette index 3: Yellow
    per_key_rgb_config.palette[3] = (HSV){43, 255, 255};
    // Palette index 4: Green
    per_key_rgb_config.palette[4] = (HSV){85, 255, 255};
    // Palette index 5: Cyan
    per_key_rgb_config.palette[5] = (HSV){128, 255, 255};
    // Palette index 6: Blue
    per_key_rgb_config.palette[6] = (HSV){170, 255, 255};
    // Palette index 7: Purple
    per_key_rgb_config.palette[7] = (HSV){191, 255, 255};
    // Palette index 8: Magenta
    per_key_rgb_config.palette[8] = (HSV){213, 255, 255};
    // Palette index 9: Pink
    per_key_rgb_config.palette[9] = (HSV){234, 255, 255};
    // Palette index 10: White
    per_key_rgb_config.palette[10] = (HSV){0, 0, 255};
    // Palette index 11: Warm White
    per_key_rgb_config.palette[11] = (HSV){28, 50, 255};
    // Palette index 12: Spring Green
    per_key_rgb_config.palette[12] = (HSV){106, 255, 255};
    // Palette index 13: Coral
    per_key_rgb_config.palette[13] = (HSV){11, 176, 255};
    // Palette index 14: Gold
    per_key_rgb_config.palette[14] = (HSV){36, 255, 218};
    // Palette index 15: Azure
    per_key_rgb_config.palette[15] = (HSV){132, 102, 255};

    // Initialize all presets to black (palette index 0)
    for (uint8_t preset = 0; preset < PER_KEY_NUM_PRESETS; preset++) {
        for (uint8_t led = 0; led < PER_KEY_NUM_LEDS; led++) {
            per_key_rgb_config.presets[preset][led] = 0; // Index 0 = black
        }
    }
}

// Load from EEPROM
void per_key_rgb_load_from_eeprom(void) {
    // Load entire structure in one block read (888 bytes)
    eeprom_read_block(&per_key_rgb_config, (void*)PER_KEY_RGB_EEPROM_ADDR, sizeof(per_key_rgb_config));
}

// Save to EEPROM
void per_key_rgb_save_to_eeprom(void) {
    // Save entire structure in one block write (888 bytes)
    eeprom_update_block(&per_key_rgb_config, (void*)PER_KEY_RGB_EEPROM_ADDR, sizeof(per_key_rgb_config));

    // Write magic number
    eeprom_update_word((uint16_t*)PER_KEY_MAGIC_ADDR, PER_KEY_MAGIC_NUMBER);
}

// Get color for a specific LED in a specific preset
HSV per_key_get_color(uint8_t preset, uint8_t led_index) {
    if (preset >= PER_KEY_NUM_PRESETS || led_index >= PER_KEY_NUM_LEDS) {
        return (HSV){0, 0, 0}; // Return black for invalid indices
    }

    uint8_t palette_index = per_key_rgb_config.presets[preset][led_index];
    if (palette_index >= PER_KEY_PALETTE_SIZE) {
        return (HSV){0, 0, 0}; // Return black for invalid palette index
    }

    return per_key_rgb_config.palette[palette_index];
}

// Set palette color
void per_key_set_palette_color(uint8_t palette_index, uint8_t h, uint8_t s, uint8_t v) {
    if (palette_index >= PER_KEY_PALETTE_SIZE) return;

    per_key_rgb_config.palette[palette_index].h = h;
    per_key_rgb_config.palette[palette_index].s = s;
    per_key_rgb_config.palette[palette_index].v = v;
}

// Set LED color by palette index
void per_key_set_led_color(uint8_t preset, uint8_t led_index, uint8_t palette_index) {
    if (preset >= PER_KEY_NUM_PRESETS || led_index >= PER_KEY_NUM_LEDS) return;
    if (palette_index >= PER_KEY_PALETTE_SIZE) return;

    per_key_rgb_config.presets[preset][led_index] = palette_index;
}

// Get palette data for protocol
void per_key_get_palette(uint8_t *data) {
    for (uint8_t i = 0; i < PER_KEY_PALETTE_SIZE; i++) {
        data[i * 3] = per_key_rgb_config.palette[i].h;
        data[i * 3 + 1] = per_key_rgb_config.palette[i].s;
        data[i * 3 + 2] = per_key_rgb_config.palette[i].v;
    }
}

// Get preset data (paginated) for protocol
void per_key_get_preset_data(uint8_t preset, uint8_t offset, uint8_t count, uint8_t *data) {
    if (preset >= PER_KEY_NUM_PRESETS) return;
    if (offset + count > PER_KEY_NUM_LEDS) {
        count = PER_KEY_NUM_LEDS - offset;
    }

    for (uint8_t i = 0; i < count; i++) {
        data[i] = per_key_rgb_config.presets[preset][offset + i];
    }
}

// =============================================================================
// RGB Matrix Effect Implementations (12 Presets)
// =============================================================================

// Helper function to render a per-key preset
static bool per_key_effect_runner(effect_params_t* params, uint8_t preset) {
    // Ensure per-key RGB is initialized (loads from EEPROM if valid)
    if (!per_key_rgb_initialized) {
        per_key_rgb_init();
    }

    RGB_MATRIX_USE_LIMITS(led_min, led_max);

    // Get global brightness setting
    uint8_t base_val = rgb_matrix_get_val();

    for (uint8_t i = led_min; i < led_max; i++) {
        HSV hsv = per_key_get_color(preset, i);
        // Scale the color's value by global brightness
        hsv.v = (uint8_t)((uint16_t)hsv.v * base_val / 255);
        RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
        rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
    }

    return rgb_matrix_check_finished_leds(led_max);
}

// Preset 1
bool PER_KEY_1(effect_params_t* params) {
    return per_key_effect_runner(params, 0);
}

// Preset 2
bool PER_KEY_2(effect_params_t* params) {
    return per_key_effect_runner(params, 1);
}

// Preset 3
bool PER_KEY_3(effect_params_t* params) {
    return per_key_effect_runner(params, 2);
}

// Preset 4
bool PER_KEY_4(effect_params_t* params) {
    return per_key_effect_runner(params, 3);
}

// Preset 5
bool PER_KEY_5(effect_params_t* params) {
    return per_key_effect_runner(params, 4);
}

// Preset 6
bool PER_KEY_6(effect_params_t* params) {
    return per_key_effect_runner(params, 5);
}

// Preset 7
bool PER_KEY_7(effect_params_t* params) {
    return per_key_effect_runner(params, 6);
}

// Preset 8
bool PER_KEY_8(effect_params_t* params) {
    return per_key_effect_runner(params, 7);
}

// Preset 9
bool PER_KEY_9(effect_params_t* params) {
    return per_key_effect_runner(params, 8);
}

// Preset 10
bool PER_KEY_10(effect_params_t* params) {
    return per_key_effect_runner(params, 9);
}

// Preset 11
bool PER_KEY_11(effect_params_t* params) {
    return per_key_effect_runner(params, 10);
}

// Preset 12
bool PER_KEY_12(effect_params_t* params) {
    return per_key_effect_runner(params, 11);
}
