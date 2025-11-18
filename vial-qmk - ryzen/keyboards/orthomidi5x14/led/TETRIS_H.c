#include "orthomidi5x14.h"
RGB_MATRIX_EFFECT(TETRIS_H)

static bool TETRIS_H_runner(effect_params_t* params) {
    static uint8_t grid[5][14] = {0}; // 5 rows, 14 cols
    static uint8_t drop_timer = 0;
    static uint8_t current_x = 0;
    static uint8_t current_y = 2;
    static uint8_t current_hue = 0;
    
    if (params->init) {
        memset(grid, 0, sizeof(grid));
        current_x = 0;
        current_y = 2;
        current_hue = rand() % 255;
    }
    
    if (++drop_timer > (60 - (rgb_matrix_config.speed / 4))) { // Scale with RGB speed
        drop_timer = 0;
        
        // Try to move current block right
        if (current_x < 13 && grid[current_y][current_x + 1] == 0) {
            grid[current_y][current_x] = 0;
            current_x++;
            grid[current_y][current_x] = current_hue;
        } else {
            // Block landed, spawn new one
            current_y = rand() % 5;
            current_x = 0;
            current_hue = rand() % 255;
            if (grid[current_y][0] == 0) {
                grid[current_y][current_x] = current_hue;
            } else {
                // Left column is full, reset the game
                memset(grid, 0, sizeof(grid));
                current_x = 0;
                current_y = 2;
                current_hue = rand() % 255;
                grid[current_y][current_x] = current_hue;
            }
        }
    }
    
    // Render grid
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                if (grid[row][col] > 0) {
                    HSV hsv = {grid[row][col], 255, rgb_matrix_config.hsv.v};
                    RGB rgb = rgb_matrix_hsv_to_rgb(hsv);
                    rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                } else {
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
            }
        }
    }
    
    return false;
}

bool TETRIS_H(effect_params_t* params) {
    return TETRIS_H_runner(params);
}