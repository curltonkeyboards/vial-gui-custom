// LOOP_ACTIVITY_PULSE Effect - Speed Responsive - Similar to typing heatmap but for MIDI notes
#include "process_midi.h"
RGB_MATRIX_EFFECT(LOOP_ACTIVITY_PULSE)

#define LOOP_ACTIVITY_INCREASE_STEP 32
#define LOOP_ACTIVITY_SPREAD 40
#define LOOP_ACTIVITY_AREA_LIMIT 16
#define MAX_TRACKED_NOTES_PULSE 64

typedef struct {
    uint8_t channel;
    uint8_t note;
    bool is_macro;
    bool active;
} tracked_note_pulse_t;

static tracked_note_pulse_t tracked_notes_pulse[MAX_TRACKED_NOTES_PULSE];
static uint8_t tracked_count_pulse = 0;

static int8_t find_tracked_note_pulse(uint8_t channel, uint8_t note, bool is_macro) {
    for (uint8_t i = 0; i < MAX_TRACKED_NOTES_PULSE; i++) {
        if (tracked_notes_pulse[i].active && 
            tracked_notes_pulse[i].channel == channel && 
            tracked_notes_pulse[i].note == note && 
            tracked_notes_pulse[i].is_macro == is_macro) {
            return i;
        }
    }
    return -1;
}

static bool add_tracked_note_pulse(uint8_t channel, uint8_t note, bool is_macro) {
    for (uint8_t i = 0; i < MAX_TRACKED_NOTES_PULSE; i++) {
        if (!tracked_notes_pulse[i].active) {
            tracked_notes_pulse[i].channel = channel;
            tracked_notes_pulse[i].note = note;
            tracked_notes_pulse[i].is_macro = is_macro;
            tracked_notes_pulse[i].active = true;
            if (i >= tracked_count_pulse) tracked_count_pulse = i + 1;
            return true;
        }
    }
    return false;
}

// Process MIDI note hits similar to process_rgb_matrix_typing_heatmap
static void process_midi_note_heatmap_pulse(uint8_t row, uint8_t col, uint8_t velocity, uint8_t channel, 
                                           uint8_t midi_frame_buffer[5][14], uint8_t channel_buffer[5][14]) {
    if (row >= 5 || col >= 14) return; // Bounds check
    
    // Add heat based on velocity
    uint8_t heat_increase = (velocity * LOOP_ACTIVITY_INCREASE_STEP) / 127;
    if (heat_increase < LOOP_ACTIVITY_INCREASE_STEP / 2) {
        heat_increase = LOOP_ACTIVITY_INCREASE_STEP / 2; // Minimum heat
    }
    
    // Set the directly hit key (explicitly cap at 255 to prevent overflow issues)
    uint16_t new_heat = midi_frame_buffer[row][col] + heat_increase;
    midi_frame_buffer[row][col] = new_heat > 255 ? 255 : new_heat;
    channel_buffer[row][col] = channel;
    
    // Spread effect to nearby keys
    for (int8_t i_row = 0; i_row < 5; i_row++) {
        for (int8_t i_col = 0; i_col < 14; i_col++) {
            if (i_row == row && i_col == col) continue; // Skip center key (already handled)
            
            // Calculate distance (simplified Manhattan distance for performance)
            uint8_t distance = abs(i_row - row) + abs(i_col - col);
            distance *= 20; // Scale for comparison with SPREAD value
            
            if (distance <= LOOP_ACTIVITY_SPREAD) {
                uint8_t amount = qsub8(LOOP_ACTIVITY_SPREAD, distance);
                if (amount > LOOP_ACTIVITY_AREA_LIMIT) {
                    amount = LOOP_ACTIVITY_AREA_LIMIT;
                }
                
                // Only update if we're adding more heat than current (explicitly cap at 255)
                if (amount > 5) { // Minimum threshold for spread
                    uint16_t new_spread_heat = midi_frame_buffer[i_row][i_col] + amount;
                    midi_frame_buffer[i_row][i_col] = new_spread_heat > 255 ? 255 : new_spread_heat;
                    // Use same channel for spread effect
                    if (midi_frame_buffer[i_row][i_col] > channel_buffer[i_row][i_col]) {
                        channel_buffer[i_row][i_col] = channel;
                    }
                }
            }
        }
    }
}

static bool loop_activity_pulse_runner(effect_params_t* params) {
    static uint8_t midi_frame_buffer[5][14]; // Heat values for each key position
    static uint8_t channel_buffer[5][14];    // Channel assignment for each key
    static uint16_t heatmap_decrease_timer;
    static bool decrease_heatmap_values;
    
    // Channel hue offsets from base color
    static const int16_t channel_hue_offsets[16] = {
        0,    // Ch 1: Base hue
        85,   // Ch 2: Green offset
        170,  // Ch 3: Blue offset
        43,   // Ch 4: Yellow offset
        213,  // Ch 5: Purple offset
        128,  // Ch 6: Cyan offset
        28,   // Ch 7: Orange offset
        248,  // Ch 8: Pink offset
        60,   // Ch 9: Yellow-green offset
        192,  // Ch 10: Blue-violet offset
        11,   // Ch 11: Dark salmon offset
        126,  // Ch 12: Light sea green offset
        36,   // Ch 13: Gold offset
        147,  // Ch 14: Steel blue offset
        241,  // Ch 15: Pale violet red offset
        6     // Ch 16: Tomato offset
    };
    
    if (params->init) {
        // Initialize buffers
        for (uint8_t row = 0; row < 5; row++) {
            for (uint8_t col = 0; col < 14; col++) {
                midi_frame_buffer[row][col] = 0;
                channel_buffer[row][col] = 0;
            }
        }
        // Initialize tracking
        for (uint8_t i = 0; i < MAX_TRACKED_NOTES_PULSE; i++) {
            tracked_notes_pulse[i].active = false;
        }
        heatmap_decrease_timer = timer_read();
        decrease_heatmap_values = false;
        tracked_count_pulse = 0;
    }
    
    // Check for new live notes (note-on events)
    for (uint8_t i = 0; i < live_note_count; i++) {
        uint8_t channel = live_notes[i][0];
        uint8_t note = live_notes[i][1];
        uint8_t velocity = live_notes[i][2];
        
        // Check if this note is already tracked
        if (find_tracked_note_pulse(channel, note, false) == -1) {
            // New note detected - trigger heatmap and track it
            uint8_t row = (note / 12) % 5;
            uint8_t col = (note % 12) + 1;
            if (col >= 14) col = 13;
            
            process_midi_note_heatmap_pulse(row, col, velocity, channel, midi_frame_buffer, channel_buffer);
            
            // Track this note
            add_tracked_note_pulse(channel, note, false);
        }
    }
    
    // Check for new macro notes (note-on events)
    for (uint8_t i = 0; i < macro_note_count; i++) {
        uint8_t channel = macro_notes[i][0];
        uint8_t note = macro_notes[i][1];
        
        // Check if this note is already tracked
        if (find_tracked_note_pulse(channel, note, true) == -1) {
            // New note detected - trigger heatmap and track it
            uint8_t row = (note / 12) % 5;
            uint8_t col = (note % 12) + 1;
            if (col >= 14) col = 13;
            
            process_midi_note_heatmap_pulse(row, col, 100, channel, midi_frame_buffer, channel_buffer); // Fixed velocity for macros
            
            // Track this note
            add_tracked_note_pulse(channel, note, true);
        }
    }
    
    // Check for removed notes (note-off events) and untrack them
    for (uint8_t t = 0; t < tracked_count_pulse; t++) {
        if (!tracked_notes_pulse[t].active) continue;
        
        bool found = false;
        
        if (tracked_notes_pulse[t].is_macro) {
            // Check if macro note still exists
            for (uint8_t i = 0; i < macro_note_count; i++) {
                if (macro_notes[i][0] == tracked_notes_pulse[t].channel && 
                    macro_notes[i][1] == tracked_notes_pulse[t].note) {
                    found = true;
                    break;
                }
            }
        } else {
            // Check if live note still exists
            for (uint8_t i = 0; i < live_note_count; i++) {
                if (live_notes[i][0] == tracked_notes_pulse[t].channel && 
                    live_notes[i][1] == tracked_notes_pulse[t].note) {
                    found = true;
                    break;
                }
            }
        }
        
        if (!found) {
            // Note was removed - untrack it (heatmap continues to fade independently)
            tracked_notes_pulse[t].active = false;
        }
    }
    
    // Speed-responsive decrease timer (similar to typing heatmap)
    uint8_t speed = rgb_matrix_get_speed();
    uint16_t decrease_delay_ms = 50 - (speed * 40) / 255; // 10ms to 50ms based on speed
    if (decrease_delay_ms < 10) decrease_delay_ms = 10; // Minimum delay
    
    if (params->iter == 0) {
        decrease_heatmap_values = timer_elapsed(heatmap_decrease_timer) >= decrease_delay_ms;
        
        if (decrease_heatmap_values) {
            heatmap_decrease_timer = timer_read();
        }
    }
    
    // Get base color settings
    uint8_t base_hue = rgb_matrix_get_hue();
    uint8_t base_sat = rgb_matrix_get_sat();
    uint8_t base_val = rgb_matrix_get_val();
    
    // Render heatmap & decrease (similar to typing heatmap logic)
    for (uint8_t row = 0; row < 5; row++) {
        for (uint8_t col = 0; col < 14; col++) {
            uint8_t led[LED_HITS_TO_REMEMBER];
            uint8_t led_count = rgb_matrix_map_row_column_to_led(row, col, led);
            if (led_count > 0) {
                uint8_t val = midi_frame_buffer[row][col];
                uint8_t channel = channel_buffer[row][col];
                
                if (val > 0) {
                    // Calculate color based on heat value and channel
                    HSV hsv;
                    
                    // Use channel-based hue offset from base hue
                    uint8_t channel_idx = channel % 16;
                    hsv.h = (base_hue + channel_hue_offsets[channel_idx]) % 256;
                    
                    // Saturation: full saturation for higher heat values
                    hsv.s = base_sat;
                    
                    // FIXED: Value calculation to prevent overflow
                    uint16_t brightness_calc;
                    if (val > 170) {
                        // For high heat values, use maximum brightness
                        brightness_calc = 255;
                    } else {
                        // For lower heat values, calculate safely using uint16_t
                        brightness_calc = val + 85;
                        if (brightness_calc > 85) {
                            brightness_calc = (brightness_calc - 85) * 4;
                            if (brightness_calc > 255) brightness_calc = 255;
                        } else {
                            brightness_calc = 0;
                        }
                    }
                    hsv.v = scale8(brightness_calc, base_val);
                    
                    RGB rgb = hsv_to_rgb(hsv);
                    rgb_matrix_set_color(led[0], rgb.r, rgb.g, rgb.b);
                } else {
                    rgb_matrix_set_color(led[0], 0, 0, 0);
                }
                
                // Decrease heat value over time (speed-responsive)
                if (decrease_heatmap_values && val > 0) {
                    // Speed-responsive decay rate: 1 to 5 based on speed
                    uint8_t decay_rate = 1 + (speed * 4) / 255;
                    if (decay_rate < 1) decay_rate = 1;
                    if (decay_rate > 5) decay_rate = 5;
                    
                    midi_frame_buffer[row][col] = qsub8(val, decay_rate);
                    if (midi_frame_buffer[row][col] == 0) {
                        channel_buffer[row][col] = 0; // Clear channel when heat reaches zero
                    }
                }
            }
        }
    }
    
    return false;
}

bool LOOP_ACTIVITY_PULSE(effect_params_t* params) {
    return loop_activity_pulse_runner(params);
}