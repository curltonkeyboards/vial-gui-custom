/* Copyright 2021 @ Grayson Carr
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "rgb_matrix.h"
#include "rgb_matrix_types.h"
#include "keymap.h"

// Define key groups and their colors
#define NUM_GROUPS 12
const uint16_t group_start_keycode = 28931;
const uint16_t group_end_keycode = 29002;

const HSV colors[NUM_GROUPS] = {
    {HSV_RED}, {HSV_ORANGE}, {HSV_YELLOW}, {HSV_GREEN}, {HSV_CYAN}, {HSV_BLUE},
    {HSV_PURPLE}, {HSV_PINK}, {HSV_WHITE}, {HSV_TEAL}, {HSV_MAGENTA}, {HSV_GOLD}
};

uint8_t get_group(uint16_t keycode) {
    if (keycode < group_start_keycode || keycode > group_end_keycode) {
        return 0xFF; // Invalid group
    }
    return (keycode - group_start_keycode) % NUM_GROUPS;
}

bool is_key_in_group(uint16_t keycode, uint8_t group) {
    return get_group(keycode) == group;
}