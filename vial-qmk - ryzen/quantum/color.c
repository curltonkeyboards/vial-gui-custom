/* Copyright 2017 Jason Williams
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
#include "color.h"
#include "led_tables.h"
#include "progmem.h"
#include "util.h"

// Helper function to apply brightness scaling to any RGB values
static RGB apply_brightness_scaling(RGB rgb) {
    // Calculate cumulative RGB values
    uint16_t rgb_sum = (uint16_t)rgb.r + (uint16_t)rgb.g + (uint16_t)rgb.b;
    
    uint16_t scale_factor = 100; // Default 100% (no scaling)
    
    if (rgb_sum >= 250) {
        if (rgb_sum <= 550) {
            // Stronger scaling from 250 to 550: 100% down to 50%
            scale_factor = 100 - ((rgb_sum - 250) * 60) / (550 - 250);
        } else {
            // Weaker scaling from 550 to 765: 50% down to 35%
            scale_factor = 50 - ((rgb_sum - 550) * 30) / (765 - 550);
        }
        
        // Apply scaling to all RGB components
        rgb.r = ((uint16_t)rgb.r * scale_factor) / 100;
        rgb.g = ((uint16_t)rgb.g * scale_factor) / 100;
        rgb.b = ((uint16_t)rgb.b * scale_factor) / 100;
    }
    
    return rgb;
}

RGB hsv_to_rgb_impl(HSV hsv, bool use_cie) {
    RGB      rgb;
    uint8_t  region, remainder, p, q, t;
    uint16_t h, s, v;
    if (hsv.s == 0) {
#ifdef USE_CIE1931_CURVE
        if (use_cie) {
            rgb.r = rgb.g = rgb.b = pgm_read_byte(&CIE1931_CURVE[hsv.v]);
        } else {
            rgb.r = hsv.v;
            rgb.g = hsv.v;
            rgb.b = hsv.v;
        }
#else
        rgb.r = hsv.v;
        rgb.g = hsv.v;
        rgb.b = hsv.v;
#endif
        // Apply brightness scaling for grayscale colors too
        return apply_brightness_scaling(rgb);
    }
    h = hsv.h;
    s = hsv.s;
#ifdef USE_CIE1931_CURVE
    if (use_cie) {
        v = pgm_read_byte(&CIE1931_CURVE[hsv.v]);
    } else {
        v = hsv.v;
    }
#else
    v = hsv.v;
#endif
    region    = h * 6 / 255;
    remainder = (h * 2 - region * 85) * 3;
    p = (v * (255 - s)) >> 8;
    q = (v * (255 - ((s * remainder) >> 8))) >> 8;
    t = (v * (255 - ((s * (255 - remainder)) >> 8))) >> 8;
    switch (region) {
        case 6:
        case 0:
            rgb.r = v;
            rgb.g = t;
            rgb.b = p;
            break;
        case 1:
            rgb.r = q;
            rgb.g = v;
            rgb.b = p;
            break;
        case 2:
            rgb.r = p;
            rgb.g = v;
            rgb.b = t;
            break;
        case 3:
            rgb.r = p;
            rgb.g = q;
            rgb.b = v;
            break;
        case 4:
            rgb.r = t;
            rgb.g = p;
            rgb.b = v;
            break;
        default:
            rgb.r = v;
            rgb.g = p;
            rgb.b = q;
            break;
    }

    // Apply brightness scaling to all colors
    return apply_brightness_scaling(rgb);
}

RGB hsv_to_rgb(HSV hsv) {
#ifdef USE_CIE1931_CURVE
    return hsv_to_rgb_impl(hsv, true);
#else
    return hsv_to_rgb_impl(hsv, false);
#endif
}

RGB hsv_to_rgb_nocie(HSV hsv) {
    return hsv_to_rgb_impl(hsv, false);
}

#ifdef RGBW
void convert_rgb_to_rgbw(LED_TYPE *led) {
    // Determine lowest value in all three colors, put that into
    // the white channel and then shift all colors by that amount
    led->w = MIN(led->r, MIN(led->g, led->b));
    led->r -= led->w;
    led->g -= led->w;
    led->b -= led->w;
}
#endif