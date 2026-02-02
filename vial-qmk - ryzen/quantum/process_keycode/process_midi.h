/* Copyright 2016 Jack Humbert
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

#pragma once

#include "quantum.h"

extern uint8_t keysplitchannel;
extern uint8_t keysplit2channel;
extern uint8_t keysplitstatus;
extern uint8_t channel_number;
extern int8_t transpose_number;
extern int8_t octave_number;
extern int8_t transpose_number2;
extern int8_t octave_number2;
extern int8_t transpose_number3;
extern int8_t octave_number3;
extern uint8_t velocity_number;
extern uint8_t keysplittransposestatus;
extern uint8_t keysplitvelocitystatus;
extern bool global_edit_modifier_held;

bool cclooprecording;
bool truesustain;
bool channeloverride;
bool velocityoverride;
bool transposeoverride;

void midi_send_noteon_with_recording(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel);
void midi_send_noteoff_with_recording(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel, uint8_t note_type);
void midi_send_cc_with_recording(uint8_t channel, uint8_t cc, uint8_t value);
void midi_send_program_with_recording(uint8_t channel, uint8_t program);
void midi_send_aftertouch_with_recording(uint8_t channel, uint8_t note, uint8_t pressure);
void midi_send_channel_pressure_with_recording(uint8_t channel, uint8_t pressure);

// HE (Hall Effect) velocity functions - can be overridden by keyboard implementation
uint8_t get_he_velocity_from_position(uint8_t row, uint8_t col);
uint8_t get_keysplit_he_velocity_from_position(uint8_t row, uint8_t col);
uint8_t get_triplesplit_he_velocity_from_position(uint8_t row, uint8_t col);
void midi_send_pitchbend_with_recording(uint8_t channel, int16_t bend_value);
void midi_send_external_cc_with_recording(uint8_t channel, uint8_t cc, uint8_t value);
void midi_send_noteon_smartchord(uint8_t channel, uint8_t note, uint8_t velocity);
void midi_send_noteoff_smartchord(uint8_t channel, uint8_t note, uint8_t velocity);
void midi_send_noteon_trainer(uint8_t channel, uint8_t note, uint8_t velocity);
void midi_send_noteoff_trainer(uint8_t channel, uint8_t note, uint8_t velocity);

extern void scan_current_layer_midi_leds(void);
// Add this declaration to your header file
uint8_t get_midi_led_position(uint8_t layer, uint8_t note_index, uint8_t position_index);
void process_midi_basic_noteon(uint8_t note);
void process_midi_basic_noteoff(uint8_t note);
void process_midi_all_notes_off(void);


void midi_task(void);

typedef union {
    uint32_t raw;
    struct {
        uint8_t octave : 4;
        int8_t  transpose : 4;
        uint8_t velocity : 7;
        uint8_t channel : 4;
        uint8_t modulation_interval : 4;
    };
} midi_config_t;

extern midi_config_t midi_config;

void midi_init(void);
bool process_midi(uint16_t keycode, keyrecord_t *record);

#        define MIDI_INVALID_NOTE 0xFF
#        define MIDI_TONE_COUNT (MIDI_TONE_MAX - MIDI_TONE_MIN + 1)

uint8_t midi_compute_note(uint16_t keycode);
bool is_any_macro_modifier_active(void);  // Function declaration
extern bool overdub_advanced_mode;
void reset_all_macro_transpose(void);

// Channel override functions  
uint8_t get_macro_channel_override(uint8_t macro_num);
void set_macro_channel_override(uint8_t macro_num, uint8_t channel_override);
void reset_all_macro_channel_override(void);

// Velocity offset functions
int8_t get_macro_velocity_offset(uint8_t macro_num);
void set_macro_velocity_offset(uint8_t macro_num, int8_t velocity_offset);
void reset_all_macro_velocity_offset(void);

void reset_macro_transformations(uint8_t macro_num);
void reset_overdub_transformations(uint8_t macro_num);
void apply_macro_transformation(void (*setter_func)(uint8_t, int8_t), int8_t value);

bool is_any_macro_modifier_active(void);
uint8_t get_active_macro_modifier(void);
uint8_t bpm_source_macro;

// Pending change functions
bool has_pending_transpose_change(uint8_t macro_num);
int8_t get_pending_transpose_value(uint8_t macro_num);
extern bool macro_modifier_held[4];  // Just the declaration

// Get target transpose value for a specific macro (1-4)
int8_t get_macro_transpose_target(uint8_t macro_num);

// Set target transpose value for a specific macro (1-4) - direct target setting
void set_macro_transpose_target(uint8_t macro_num, int8_t transpose_value);

// Reset all transpose targets to 0
void reset_all_macro_transpose_targets(void);

int8_t get_macro_channel_offset_target(uint8_t macro_num);
void set_macro_channel_offset_target(uint8_t macro_num, int8_t channel_offset);

// Channel absolute functions  
uint8_t get_macro_channel_absolute_target(uint8_t macro_num);
void set_macro_channel_absolute_target(uint8_t macro_num, uint8_t channel_absolute);

int8_t get_macro_velocity_offset_target(uint8_t macro_num);
void set_macro_velocity_offset_target(uint8_t macro_num, int8_t velocity_offset);

bool is_macro_effectively_playing(uint8_t i);
void reset_bpm_timing_for_loop_start(void);
uint8_t get_macro_velocity_absolute_target(uint8_t macro_num);
void set_macro_velocity_absolute_target(uint8_t macro_num, uint8_t velocity_absolute);
void get_macro_led_color(uint8_t macro_idx, uint8_t* r, uint8_t* g, uint8_t* b);

// Overdub transpose functions
int8_t get_overdub_transpose_target(uint8_t macro_num);
void set_overdub_transpose_target(uint8_t macro_num, int8_t transpose_value);

// Overdub channel offset functions  
int8_t get_overdub_channel_offset_target(uint8_t macro_num);
void set_overdub_channel_offset_target(uint8_t macro_num, int8_t channel_offset);

// Overdub channel absolute functions
uint8_t get_overdub_channel_absolute_target(uint8_t macro_num);
void set_overdub_channel_absolute_target(uint8_t macro_num, uint8_t channel_absolute);

// Overdub velocity offset functions
int8_t get_overdub_velocity_offset_target(uint8_t macro_num);
void set_overdub_velocity_offset_target(uint8_t macro_num, int8_t velocity_offset);

// Overdub velocity absolute functions
uint8_t get_overdub_velocity_absolute_target(uint8_t macro_num);
void set_overdub_velocity_absolute_target(uint8_t macro_num, uint8_t velocity_absolute);

// Overdub octave doubler functions (if needed)
int8_t get_overdub_octave_doubler_target(uint8_t macro_num);
void set_overdub_octave_doubler_target(uint8_t macro_num, int8_t octave_offset);

void dynamic_macro_handle_loop_trigger(void);
extern uint32_t current_bpm;

#define MAX_MACRO_NOTES 64
#define MAX_LIVE_NOTES 32

// Add these lines
void add_lighting_live_note(uint8_t channel, uint8_t note);
void remove_lighting_live_note(uint8_t channel, uint8_t note);
void add_lighting_macro_note(uint8_t channel, uint8_t note, uint8_t track_id);
void remove_lighting_macro_note(uint8_t channel, uint8_t note, uint8_t track_id);

extern uint8_t live_notes[MAX_LIVE_NOTES][3];   // [channel, note, velocity]
extern uint8_t live_note_count;

#define MAX_SUSTAIN_NOTES 64

// Sustain notes array and count - extern declarations for other files to use
extern uint8_t sustain_notes[MAX_SUSTAIN_NOTES][3]; // [channel, note, velocity]
extern uint8_t sustain_note_count;

#define NUM_CUSTOM_SLOTS 50
#define NUM_CUSTOM_PARAMETERS 12
// =============================================================================
// NEW MODULAR SYSTEM ENUMS
// =============================================================================

typedef enum {
    LIVE_POS_TRUEKEY,
    LIVE_POS_ZONE,
    LIVE_POS_QUADRANT,
    LIVE_POS_NOTE_ROW_COL0,
    LIVE_POS_NOTE_ROW_COL13,
    LIVE_POS_NOTE_ROW_COL6,
    LIVE_POS_NOTE_COL_ROW0,
    LIVE_POS_NOTE_COL_ROW4,
    LIVE_POS_NOTE_COL_ROW2,
    LIVE_POS_NOTE_ROW_MIXED,
    LIVE_POS_NOTE_COL_MIXED,
    LIVE_POS_TOP_DOT,
    LIVE_POS_LEFT_DOT,
    LIVE_POS_RIGHT_DOT,
    LIVE_POS_BOTTOM_DOT,
    LIVE_POS_CENTER_DOT,
    LIVE_POS_TOP_LEFT_DOT,
    LIVE_POS_TOP_RIGHT_DOT,
    LIVE_POS_BOTTOM_LEFT_DOT,
    LIVE_POS_BOTTOM_RIGHT_DOT,
    LIVE_POS_NOTE_CORNER_DOTS,
    LIVE_POS_NOTE_EDGE_DOTS,
    LIVE_POS_NOTE_ALL_DOTS,
	LIVE_POS_ZONE2,
    LIVE_POS_ZONE3,
    LIVE_POS_COUNT_TO_8,
    LIVE_POS_PITCH_MAPPING_1,
    LIVE_POS_PITCH_MAPPING_2, 
    LIVE_POS_PITCH_MAPPING_3,
    LIVE_POS_PITCH_MAPPING_4,
    LIVE_POS_SNAKE,
    LIVE_POS_CENTER_BLOCK,
    LIVE_POS_NOTE_CLOSE_DOTS_1,
    LIVE_POS_NOTE_CLOSE_DOTS_2,
} live_note_positioning_t;

typedef enum {
    MACRO_POS_TRUEKEY,
    MACRO_POS_ZONE,
    MACRO_POS_QUADRANT,
    MACRO_POS_NOTE_ROW_COL0,
    MACRO_POS_NOTE_ROW_COL13,
    MACRO_POS_NOTE_ROW_COL6,
    MACRO_POS_NOTE_COL_ROW0,
    MACRO_POS_NOTE_COL_ROW4,
    MACRO_POS_NOTE_COL_ROW2,
    MACRO_POS_NOTE_ROW_MIXED,
    MACRO_POS_NOTE_COL_MIXED,
    MACRO_POS_LOOP_ROW_COL0,
    MACRO_POS_LOOP_ROW_COL13,
    MACRO_POS_LOOP_ROW_COL6,
    MACRO_POS_LOOP_ROW_ALT,
    MACRO_POS_LOOP_COL_ROW0,
    MACRO_POS_LOOP_COL_ROW4,
    MACRO_POS_LOOP_COL_ROW2,
    MACRO_POS_LOOP_BLOCK_3X3,
    MACRO_POS_LOOP_BLOCK_CENTER,
    MACRO_POS_TOP_DOT,
    MACRO_POS_LEFT_DOT,
    MACRO_POS_RIGHT_DOT,
    MACRO_POS_BOTTOM_DOT,
    MACRO_POS_CENTER_DOT,
    MACRO_POS_TOP_LEFT_DOT,
    MACRO_POS_TOP_RIGHT_DOT,
    MACRO_POS_BOTTOM_LEFT_DOT,
    MACRO_POS_BOTTOM_RIGHT_DOT,
    MACRO_POS_NOTE_CORNER_DOTS,
    MACRO_POS_NOTE_EDGE_DOTS,
    MACRO_POS_NOTE_ALL_DOTS,
    MACRO_POS_LOOP_CORNER_DOTS,
    MACRO_POS_LOOP_EDGE_DOTS,
	MACRO_POS_ZONE2,
    MACRO_POS_ZONE3,
    MACRO_POS_COUNT_TO_8,
	MACRO_POS_LOOP_COUNT_TO_8,
    MACRO_POS_PITCH_MAPPING_1,
    MACRO_POS_PITCH_MAPPING_2,
    MACRO_POS_PITCH_MAPPING_3,
    MACRO_POS_PITCH_MAPPING_4,
    MACRO_POS_QUADRANT_DOTS,
    MACRO_POS_SNAKE,
    MACRO_POS_CENTER_BLOCK,
    MACRO_POS_NOTE_CLOSE_DOTS_1,
    MACRO_POS_NOTE_CLOSE_DOTS_2,
} macro_note_positioning_t;
typedef enum {
    LIVE_ANIM_NONE,
    LIVE_ANIM_NONE_SOLO,
    LIVE_ANIM_WIDE1,
    LIVE_ANIM_WIDE1_SOLO,
    LIVE_ANIM_WIDE2,
    LIVE_ANIM_WIDE2_SOLO,
    LIVE_ANIM_HEAT,
    LIVE_ANIM_SUSTAIN,
    LIVE_ANIM_COLUMN,
    LIVE_ANIM_COLUMN_SOLO,
    LIVE_ANIM_ROW,
    LIVE_ANIM_ROW_SOLO,
    LIVE_ANIM_CROSS,
    LIVE_ANIM_CROSS_SOLO,
    LIVE_ANIM_CROSS_2,
    LIVE_ANIM_CROSS_2_SOLO,
    LIVE_ANIM_MOVING_DOTS1_ROW,   
    LIVE_ANIM_MOVING_DOTS1_ROW_SOLO,
    LIVE_ANIM_MOVING_DOTS2_ROW,
    LIVE_ANIM_MOVING_DOTS2_ROW_SOLO,
    LIVE_ANIM_MOVING_DOTS1_COL, 
    LIVE_ANIM_MOVING_DOTS1_COL_SOLO,
    LIVE_ANIM_MOVING_DOTS2_COL,  
    LIVE_ANIM_MOVING_DOTS2_COL_SOLO,
    LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE,
    LIVE_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE_SOLO,
    LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE,
    LIVE_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE_SOLO,
    LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL, 
    LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_SOLO, 
    LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE, 
    LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE_SOLO,
    LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL, 
    LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_SOLO, 
    LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE,
    LIVE_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE_SOLO,
    LIVE_ANIM_RIPPLE_SMALL_1,
    LIVE_ANIM_RIPPLE_SMALL_1_SOLO,
    LIVE_ANIM_RIPPLE_MED_1,
    LIVE_ANIM_RIPPLE_MED_1_SOLO,
    LIVE_ANIM_RIPPLE_LARGE_1,
    LIVE_ANIM_RIPPLE_LARGE_1_SOLO,
    LIVE_ANIM_RIPPLE_MASSIVE_1,
    LIVE_ANIM_RIPPLE_MASSIVE_1_SOLO,
    LIVE_ANIM_RIPPLE_SMALL_2,
    LIVE_ANIM_RIPPLE_MED_2,
    LIVE_ANIM_RIPPLE_LARGE_2,
    LIVE_ANIM_RIPPLE_MASSIVE_2,
	LIVE_ANIM_RIPPLE_SMALL_2_SOLO,
    LIVE_ANIM_RIPPLE_MED_2_SOLO, 
    LIVE_ANIM_RIPPLE_LARGE_2_SOLO,
    LIVE_ANIM_RIPPLE_MASSIVE_2_SOLO,
    LIVE_ANIM_ROW_BURST_1,
    LIVE_ANIM_ROW_BURST_1_SOLO,
    LIVE_ANIM_ROW_BURST_2,
    LIVE_ANIM_ROW_BURST_2_SOLO,
    LIVE_ANIM_COLUMN_BURST_1,
    LIVE_ANIM_COLUMN_BURST_1_SOLO,
    LIVE_ANIM_COLUMN_BURST_2,
    LIVE_ANIM_COLUMN_BURST_2_SOLO,
    LIVE_ANIM_OUTWARD_BURST_SMALL_1,
    LIVE_ANIM_OUTWARD_BURST_SMALL_2,
    LIVE_ANIM_OUTWARD_BURST_1,	
    LIVE_ANIM_OUTWARD_BURST_2,
    LIVE_ANIM_OUTWARD_BURST_LARGE_1,
    LIVE_ANIM_OUTWARD_BURST_LARGE_2,
    LIVE_ANIM_VOLUME_UP_DOWN_1,
    LIVE_ANIM_VOLUME_UP_DOWN_1_SOLO,
    LIVE_ANIM_VOLUME_UP_DOWN_1_WIDE,
    LIVE_ANIM_VOLUME_UP_DOWN_1_WIDE_SOLO,
    LIVE_ANIM_VOLUME_UP_DOWN_2,
    LIVE_ANIM_VOLUME_UP_DOWN_2_SOLO,
    LIVE_ANIM_VOLUME_UP_DOWN_2_WIDE,
    LIVE_ANIM_VOLUME_UP_DOWN_2_WIDE_SOLO,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_1,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_1_SOLO,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_1_WIDE,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_1_WIDE_SOLO,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_2,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_2_SOLO,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_2_WIDE,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_2_WIDE_SOLO,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_3,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_3_SOLO,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_3_WIDE,
    LIVE_ANIM_VOLUME_LEFT_RIGHT_3_WIDE_SOLO,
    LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1,
    LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_SOLO,
    LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE,
    LIVE_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE_SOLO,
    LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2,
    LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_SOLO,
    LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE,
    LIVE_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE_SOLO,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_SOLO,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE_SOLO,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_SOLO,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE_SOLO,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_SOLO,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE,
    LIVE_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE_SOLO,
	    // NEW REVERSE DOT ANIMATIONS
    LIVE_ANIM_MOVING_DOTS_ROW_1_REVERSE,
    LIVE_ANIM_MOVING_DOTS_ROW_1_REVERSE_SOLO,
    LIVE_ANIM_MOVING_DOTS_ROW_2_REVERSE,
    LIVE_ANIM_MOVING_DOTS_ROW_2_REVERSE_SOLO,
    LIVE_ANIM_MOVING_DOTS_COL_1_REVERSE,
    LIVE_ANIM_MOVING_DOTS_COL_1_REVERSE_SOLO,
    LIVE_ANIM_MOVING_DOTS_COL_2_REVERSE,
    LIVE_ANIM_MOVING_DOTS_COL_2_REVERSE_SOLO,
    
    // 3-PIXEL COLUMN ANIMATIONS
    LIVE_ANIM_MOVING_COLUMNS_3_1,
    LIVE_ANIM_MOVING_COLUMNS_3_1_SOLO,
    LIVE_ANIM_MOVING_COLUMNS_3_2,
    LIVE_ANIM_MOVING_COLUMNS_3_2_SOLO,
    LIVE_ANIM_MOVING_COLUMNS_3_1_REVERSE,
    LIVE_ANIM_MOVING_COLUMNS_3_1_REVERSE_SOLO,
    LIVE_ANIM_MOVING_COLUMNS_3_2_REVERSE,
    LIVE_ANIM_MOVING_COLUMNS_3_2_REVERSE_SOLO,
    
    // 3-PIXEL ROW ANIMATIONS
    LIVE_ANIM_MOVING_ROWS_3_1,
    LIVE_ANIM_MOVING_ROWS_3_1_SOLO,
    LIVE_ANIM_MOVING_ROWS_3_2,
    LIVE_ANIM_MOVING_ROWS_3_2_SOLO,
    LIVE_ANIM_MOVING_ROWS_3_1_REVERSE,
    LIVE_ANIM_MOVING_ROWS_3_1_REVERSE_SOLO,
    LIVE_ANIM_MOVING_ROWS_3_2_REVERSE,
    LIVE_ANIM_MOVING_ROWS_3_2_REVERSE_SOLO,
    
    // 8-PIXEL COLUMN ANIMATIONS
    LIVE_ANIM_MOVING_COLUMNS_8_1,
    LIVE_ANIM_MOVING_COLUMNS_8_1_SOLO,
    LIVE_ANIM_MOVING_COLUMNS_8_2,
    LIVE_ANIM_MOVING_COLUMNS_8_2_SOLO,
    LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE,
    LIVE_ANIM_MOVING_COLUMNS_8_1_REVERSE_SOLO,
    LIVE_ANIM_MOVING_COLUMNS_8_2_REVERSE,
    LIVE_ANIM_MOVING_COLUMNS_8_2_REVERSE_SOLO,
    
    // 8-PIXEL ROW ANIMATIONS  
    LIVE_ANIM_MOVING_ROWS_8_1,
    LIVE_ANIM_MOVING_ROWS_8_1_SOLO,
    LIVE_ANIM_MOVING_ROWS_8_2,
    LIVE_ANIM_MOVING_ROWS_8_2_SOLO,
    LIVE_ANIM_MOVING_ROWS_8_1_REVERSE,
    LIVE_ANIM_MOVING_ROWS_8_1_REVERSE_SOLO,
    LIVE_ANIM_MOVING_ROWS_8_2_REVERSE,
    LIVE_ANIM_MOVING_ROWS_8_2_REVERSE_SOLO,
    
    // ALL ORTHOGONAL VERSIONS
    LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE,
    LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE_SOLO,
    LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE,
    LIVE_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE_SOLO,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_SOLO,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_SOLO,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE_SOLO,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE_SOLO,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_SOLO,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_SOLO,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE_SOLO,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE,
    LIVE_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE_SOLO,
	LIVE_COLLAPSING_BURST_SMALL,
	LIVE_COLLAPSING_BURST_SMALL_SOLO,
	LIVE_COLLAPSING_BURST_MED,
	LIVE_COLLAPSING_BURST_MED_SOLO,
	LIVE_COLLAPSING_BURST_LARGE,
	LIVE_COLLAPSING_BURST_LARGE_SOLO,
	LIVE_COLLAPSING_BURST_MASSIVE,
	LIVE_COLLAPSING_BURST_MASSIVE_SOLO,
} live_animation_t;

typedef enum {
    MACRO_ANIM_NONE,
    MACRO_ANIM_NONE_SOLO,
    MACRO_ANIM_WIDE1,
    MACRO_ANIM_WIDE1_SOLO,
    MACRO_ANIM_WIDE2,
    MACRO_ANIM_WIDE2_SOLO,
    MACRO_ANIM_HEAT,
    MACRO_ANIM_SUSTAIN,
    MACRO_ANIM_COLUMN,
    MACRO_ANIM_COLUMN_SOLO,
    MACRO_ANIM_ROW,
    MACRO_ANIM_ROW_SOLO,
    MACRO_ANIM_CROSS,
    MACRO_ANIM_CROSS_SOLO,
    MACRO_ANIM_CROSS_2,
    MACRO_ANIM_CROSS_2_SOLO,
    MACRO_ANIM_MOVING_DOTS1_ROW,   
    MACRO_ANIM_MOVING_DOTS1_ROW_SOLO,
    MACRO_ANIM_MOVING_DOTS2_ROW,
    MACRO_ANIM_MOVING_DOTS2_ROW_SOLO,
    MACRO_ANIM_MOVING_DOTS1_COL, 
    MACRO_ANIM_MOVING_DOTS1_COL_SOLO,
    MACRO_ANIM_MOVING_DOTS2_COL,  
    MACRO_ANIM_MOVING_DOTS2_COL_SOLO,
    MACRO_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE,
    MACRO_ANIM_MOVING_DOTS_DIAG_TL_BR_NO_FADE_SOLO,
    MACRO_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE,
    MACRO_ANIM_MOVING_DOTS_DIAG_TR_BL_NO_FADE_SOLO,
    MACRO_ANIM_MOVING_DOTS_ALL_ORTHOGONAL, 
    MACRO_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_SOLO, 
    MACRO_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE, 
    MACRO_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_NO_FADE_SOLO,
    MACRO_ANIM_MOVING_DOTS_ALL_DIAGONAL, 
    MACRO_ANIM_MOVING_DOTS_ALL_DIAGONAL_SOLO, 
    MACRO_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE,
    MACRO_ANIM_MOVING_DOTS_ALL_DIAGONAL_NO_FADE_SOLO,
    MACRO_ANIM_RIPPLE_SMALL_1,
    MACRO_ANIM_RIPPLE_SMALL_1_SOLO,
    MACRO_ANIM_RIPPLE_MED_1,
    MACRO_ANIM_RIPPLE_MED_1_SOLO,
    MACRO_ANIM_RIPPLE_LARGE_1,
    MACRO_ANIM_RIPPLE_LARGE_1_SOLO,
    MACRO_ANIM_RIPPLE_MASSIVE_1,
    MACRO_ANIM_RIPPLE_MASSIVE_1_SOLO,
    MACRO_ANIM_RIPPLE_SMALL_2,
    MACRO_ANIM_RIPPLE_MED_2,
    MACRO_ANIM_RIPPLE_LARGE_2,
    MACRO_ANIM_RIPPLE_MASSIVE_2,
	MACRO_ANIM_RIPPLE_SMALL_2_SOLO,
    MACRO_ANIM_RIPPLE_MED_2_SOLO,
    MACRO_ANIM_RIPPLE_LARGE_2_SOLO,
    MACRO_ANIM_RIPPLE_MASSIVE_2_SOLO,
    MACRO_ANIM_ROW_BURST_1,
    MACRO_ANIM_ROW_BURST_1_SOLO,
    MACRO_ANIM_ROW_BURST_2,
    MACRO_ANIM_ROW_BURST_2_SOLO,
    MACRO_ANIM_COLUMN_BURST_1,
    MACRO_ANIM_COLUMN_BURST_1_SOLO,
    MACRO_ANIM_COLUMN_BURST_2,
    MACRO_ANIM_COLUMN_BURST_2_SOLO,
    MACRO_ANIM_OUTWARD_BURST_SMALL_1,
    MACRO_ANIM_OUTWARD_BURST_SMALL_2,
    MACRO_ANIM_OUTWARD_BURST_1,	
    MACRO_ANIM_OUTWARD_BURST_2,
    MACRO_ANIM_OUTWARD_BURST_LARGE_1,
    MACRO_ANIM_OUTWARD_BURST_LARGE_2,
    MACRO_ANIM_VOLUME_UP_DOWN_1,
    MACRO_ANIM_VOLUME_UP_DOWN_1_SOLO,
    MACRO_ANIM_VOLUME_UP_DOWN_1_WIDE,
    MACRO_ANIM_VOLUME_UP_DOWN_1_WIDE_SOLO,
    MACRO_ANIM_VOLUME_UP_DOWN_2,
    MACRO_ANIM_VOLUME_UP_DOWN_2_SOLO,
    MACRO_ANIM_VOLUME_UP_DOWN_2_WIDE,
    MACRO_ANIM_VOLUME_UP_DOWN_2_WIDE_SOLO,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_1,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_1_SOLO,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_1_WIDE,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_1_WIDE_SOLO,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_2,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_2_SOLO,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_2_WIDE,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_2_WIDE_SOLO,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_3,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_3_SOLO,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_3_WIDE,
    MACRO_ANIM_VOLUME_LEFT_RIGHT_3_WIDE_SOLO,
    MACRO_ANIM_PEAK_VOLUME_UP_DOWN_1,
    MACRO_ANIM_PEAK_VOLUME_UP_DOWN_1_SOLO,
    MACRO_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE,
    MACRO_ANIM_PEAK_VOLUME_UP_DOWN_1_WIDE_SOLO,
    MACRO_ANIM_PEAK_VOLUME_UP_DOWN_2,
    MACRO_ANIM_PEAK_VOLUME_UP_DOWN_2_SOLO,
    MACRO_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE,
    MACRO_ANIM_PEAK_VOLUME_UP_DOWN_2_WIDE_SOLO,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_1,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_SOLO,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_1_WIDE_SOLO,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_2,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_SOLO,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_2_WIDE_SOLO,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_3,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_SOLO,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE,
    MACRO_ANIM_PEAK_VOLUME_LEFT_RIGHT_3_WIDE_SOLO,
	    // NEW REVERSE DOT ANIMATIONS
    MACRO_ANIM_MOVING_DOTS_ROW_1_REVERSE,
    MACRO_ANIM_MOVING_DOTS_ROW_1_REVERSE_SOLO,
    MACRO_ANIM_MOVING_DOTS_ROW_2_REVERSE,
    MACRO_ANIM_MOVING_DOTS_ROW_2_REVERSE_SOLO,
    MACRO_ANIM_MOVING_DOTS_COL_1_REVERSE,
    MACRO_ANIM_MOVING_DOTS_COL_1_REVERSE_SOLO,
    MACRO_ANIM_MOVING_DOTS_COL_2_REVERSE,
    MACRO_ANIM_MOVING_DOTS_COL_2_REVERSE_SOLO,
    
    // 3-PIXEL COLUMN ANIMATIONS
    MACRO_ANIM_MOVING_COLUMNS_3_1,
    MACRO_ANIM_MOVING_COLUMNS_3_1_SOLO,
    MACRO_ANIM_MOVING_COLUMNS_3_2,
    MACRO_ANIM_MOVING_COLUMNS_3_2_SOLO,
    MACRO_ANIM_MOVING_COLUMNS_3_1_REVERSE,
    MACRO_ANIM_MOVING_COLUMNS_3_1_REVERSE_SOLO,
    MACRO_ANIM_MOVING_COLUMNS_3_2_REVERSE,
    MACRO_ANIM_MOVING_COLUMNS_3_2_REVERSE_SOLO,
    
    // 3-PIXEL ROW ANIMATIONS
    MACRO_ANIM_MOVING_ROWS_3_1,
    MACRO_ANIM_MOVING_ROWS_3_1_SOLO,
    MACRO_ANIM_MOVING_ROWS_3_2,
    MACRO_ANIM_MOVING_ROWS_3_2_SOLO,
    MACRO_ANIM_MOVING_ROWS_3_1_REVERSE,
    MACRO_ANIM_MOVING_ROWS_3_1_REVERSE_SOLO,
    MACRO_ANIM_MOVING_ROWS_3_2_REVERSE,
    MACRO_ANIM_MOVING_ROWS_3_2_REVERSE_SOLO,
    
    // 8-PIXEL COLUMN ANIMATIONS
    MACRO_ANIM_MOVING_COLUMNS_8_1,
    MACRO_ANIM_MOVING_COLUMNS_8_1_SOLO,
    MACRO_ANIM_MOVING_COLUMNS_8_2,
    MACRO_ANIM_MOVING_COLUMNS_8_2_SOLO,
    MACRO_ANIM_MOVING_COLUMNS_8_1_REVERSE,
    MACRO_ANIM_MOVING_COLUMNS_8_1_REVERSE_SOLO,
    MACRO_ANIM_MOVING_COLUMNS_8_2_REVERSE,
    MACRO_ANIM_MOVING_COLUMNS_8_2_REVERSE_SOLO,
    
    // 8-PIXEL ROW ANIMATIONS  
    MACRO_ANIM_MOVING_ROWS_8_1,
    MACRO_ANIM_MOVING_ROWS_8_1_SOLO,
    MACRO_ANIM_MOVING_ROWS_8_2,
    MACRO_ANIM_MOVING_ROWS_8_2_SOLO,
    MACRO_ANIM_MOVING_ROWS_8_1_REVERSE,
    MACRO_ANIM_MOVING_ROWS_8_1_REVERSE_SOLO,
    MACRO_ANIM_MOVING_ROWS_8_2_REVERSE,
    MACRO_ANIM_MOVING_ROWS_8_2_REVERSE_SOLO,
    
    // ALL ORTHOGONAL VERSIONS
    MACRO_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE,
    MACRO_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_REVERSE_SOLO,
    MACRO_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE,
    MACRO_ANIM_MOVING_DOTS_ALL_ORTHOGONAL_2_REVERSE_SOLO,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_3_1,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_3_1_SOLO,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_3_2,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_3_2_SOLO,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_3_1_REVERSE_SOLO,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_3_2_REVERSE_SOLO,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_8_1,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_8_1_SOLO,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_8_2,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_8_2_SOLO,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_8_1_REVERSE_SOLO,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE,
    MACRO_ANIM_MOVING_ALL_ORTHOGONAL_8_2_REVERSE_SOLO,
	MACRO_COLLAPSING_BURST_SMALL,
	MACRO_COLLAPSING_BURST_SMALL_SOLO,
	MACRO_COLLAPSING_BURST_MED,
	MACRO_COLLAPSING_BURST_MED_SOLO,
	MACRO_COLLAPSING_BURST_LARGE,
	MACRO_COLLAPSING_BURST_LARGE_SOLO,
	MACRO_COLLAPSING_BURST_MASSIVE,
	MACRO_COLLAPSING_BURST_MASSIVE_SOLO,
} macro_animation_t;

        // All 8 directions

typedef enum {
    BACKGROUND_NONE = 0,
    
    // STATIC background (4 variants)
    BACKGROUND_STATIC = 1,
    BACKGROUND_STATIC_HUE1 = 2,      // +64 degree hue shift
    BACKGROUND_STATIC_HUE2 = 3,      // +128 degree hue shift  
    BACKGROUND_STATIC_HUE3 = 4,      // +192 degree hue shift
    
    // AUTOLIGHT background (4 variants)
    BACKGROUND_AUTOLIGHT = 5,
    BACKGROUND_AUTOLIGHT_HUE1 = 6,      // +64 degree hue shift
    BACKGROUND_AUTOLIGHT_HUE2 = 7,      // +128 degree hue shift  
    BACKGROUND_AUTOLIGHT_HUE3 = 8,     // +192 degree hue shift
    
    // PULSE FADE pattern (10 variants: 0-9)
    BACKGROUND_BPM_PULSE_FADE = 9,
    BACKGROUND_BPM_PULSE_FADE_1 = 10,    // +128 hue pulse
    BACKGROUND_BPM_PULSE_FADE_2 = 11,    // -64 saturation
    BACKGROUND_BPM_PULSE_FADE_3 = 12,    // disco pulse
    BACKGROUND_BPM_PULSE_FADE_4 = 13,    // non hue shifted static background and +128 pulse
    BACKGROUND_BPM_PULSE_FADE_5 = 14,    // +128 hue static background and non shifted hue pulse
    BACKGROUND_BPM_PULSE_FADE_6 = 15,    // static background and disco pulse
    BACKGROUND_BPM_PULSE_FADE_7 = 16,    // non hue shifted autolight and +128 shifted hue pulse
    BACKGROUND_BPM_PULSE_FADE_8 = 17,    // +128 hue shifted autolight and non shifted hue pulse
    BACKGROUND_BPM_PULSE_FADE_9 = 18,    // +64 hue shifted autolight and disco pulse
    
    // QUADRANTS pattern (10 variants: 0-9)
    BACKGROUND_BPM_QUADRANTS = 19,
    BACKGROUND_BPM_QUADRANTS_1 = 20,     // +128 hue pulse
    BACKGROUND_BPM_QUADRANTS_2 = 21,     // -64 saturation
    BACKGROUND_BPM_QUADRANTS_3 = 22,     // disco pulse
    BACKGROUND_BPM_QUADRANTS_4 = 23,     // non hue shifted static background and +128 pulse
    BACKGROUND_BPM_QUADRANTS_5 = 24,     // +128 hue static background and non shifted hue pulse
    BACKGROUND_BPM_QUADRANTS_6 = 25,     // static background and disco pulse
    BACKGROUND_BPM_QUADRANTS_7 = 26,     // non hue shifted autolight and +128 shifted hue pulse
    BACKGROUND_BPM_QUADRANTS_8 = 27,     // +128 hue shifted autolight and non shifted hue pulse
    BACKGROUND_BPM_QUADRANTS_9 = 28,     // +64 hue shifted autolight and disco pulse
    
    // ROW pattern (10 variants: 0-9)
    BACKGROUND_BPM_ROW = 29,
    BACKGROUND_BPM_ROW_1 = 30,           // +128 hue pulse
    BACKGROUND_BPM_ROW_2 = 31,           // -64 saturation
    BACKGROUND_BPM_ROW_3 = 32,           // disco pulse
    BACKGROUND_BPM_ROW_4 = 33,           // non hue shifted static background and +128 pulse
    BACKGROUND_BPM_ROW_5 = 34,           // +128 hue static background and non shifted hue pulse
    BACKGROUND_BPM_ROW_6 = 35,           // static background and disco pulse
    BACKGROUND_BPM_ROW_7 = 36,           // non hue shifted autolight and +128 shifted hue pulse
    BACKGROUND_BPM_ROW_8 = 37,           // +128 hue shifted autolight and non shifted hue pulse
    BACKGROUND_BPM_ROW_9 = 38,           // +64 hue shifted autolight and disco pulse
    
    // COLUMN pattern (10 variants: 0-9)
    BACKGROUND_BPM_COLUMN = 39,
    BACKGROUND_BPM_COLUMN_1 = 40,        // +128 hue pulse
    BACKGROUND_BPM_COLUMN_2 = 41,        // -64 saturation
    BACKGROUND_BPM_COLUMN_3 = 42,        // disco pulse
    BACKGROUND_BPM_COLUMN_4 = 43,        // non hue shifted static background and +128 pulse
    BACKGROUND_BPM_COLUMN_5 = 44,        // +128 hue static background and non shifted hue pulse
    BACKGROUND_BPM_COLUMN_6 = 45,        // static background and disco pulse
    BACKGROUND_BPM_COLUMN_7 = 46,        // non hue shifted autolight and +128 shifted hue pulse
    BACKGROUND_BPM_COLUMN_8 = 47,        // +128 hue shifted autolight and non shifted hue pulse
    BACKGROUND_BPM_COLUMN_9 = 48,        // +64 hue shifted autolight and disco pulse
    
    // ALL pattern (10 variants: 0-9)
    BACKGROUND_BPM_ALL = 49,
    BACKGROUND_BPM_ALL_1 = 50,           // +128 hue pulse
    BACKGROUND_BPM_ALL_2 = 51,           // -64 saturation
    BACKGROUND_BPM_ALL_3 = 52,           // disco pulse
    BACKGROUND_BPM_ALL_4 = 53,           // non hue shifted static background and +128 pulse
    BACKGROUND_BPM_ALL_5 = 54,           // +128 hue static background and non shifted hue pulse
    BACKGROUND_BPM_ALL_6 = 55,           // static background and disco pulse
    BACKGROUND_BPM_ALL_7 = 56,           // non hue shifted autolight and +128 shifted hue pulse
    BACKGROUND_BPM_ALL_8 = 57,           // +128 hue shifted autolight and non shifted hue pulse
    BACKGROUND_BPM_ALL_9 = 58,            // +64 hue shifted autolight and disco pulse
	BACKGROUND_CYCLE_ALL = 59,
    BACKGROUND_CYCLE_LEFT_RIGHT = 60,
    BACKGROUND_CYCLE_UP_DOWN = 61,
    BACKGROUND_CYCLE_OUT_IN = 62,
    BACKGROUND_CYCLE_OUT_IN_DUAL = 63,
    BACKGROUND_RAINBOW_PINWHEEL = 64,
    BACKGROUND_BREATHING = 65,
    BACKGROUND_WAVE_LEFT_RIGHT = 66,
    BACKGROUND_DIAGONAL_WAVE = 67,
    BACKGROUND_GRADIENT_UP_DOWN = 68,
    BACKGROUND_GRADIENT_LEFT_RIGHT = 69,
    BACKGROUND_GRADIENT_DIAGONAL = 70,
    BACKGROUND_HUE_BREATHING = 71,
    BACKGROUND_HUE_PENDULUM = 72,
    BACKGROUND_HUE_WAVE = 73,
    BACKGROUND_RAINBOW_MOVING_CHEVRON = 74,
    BACKGROUND_BAND_PINWHEEL_SAT = 75,
    BACKGROUND_BAND_PINWHEEL_VAL = 76,
    BACKGROUND_BAND_SPIRAL_SAT = 77,
    BACKGROUND_BAND_SPIRAL_VAL = 78,
    BACKGROUND_STATIC_DESAT = 79,
    BACKGROUND_STATIC_HUE1_DESAT = 80,
    BACKGROUND_STATIC_HUE2_DESAT = 81,
    BACKGROUND_STATIC_HUE3_DESAT = 82,
    BACKGROUND_AUTOLIGHT_DESAT = 83,
    BACKGROUND_AUTOLIGHT_HUE1_DESAT = 84,
    BACKGROUND_AUTOLIGHT_HUE2_DESAT = 85,
    BACKGROUND_AUTOLIGHT_HUE3_DESAT = 86,
    BACKGROUND_CYCLE_ALL_DESAT = 87,
    BACKGROUND_CYCLE_LEFT_RIGHT_DESAT = 88,
    BACKGROUND_CYCLE_UP_DOWN_DESAT = 89,
    BACKGROUND_CYCLE_OUT_IN_DESAT = 90,
    BACKGROUND_CYCLE_OUT_IN_DUAL_DESAT = 91,
    BACKGROUND_RAINBOW_PINWHEEL_DESAT = 92,
    BACKGROUND_BREATHING_DESAT = 93,
    BACKGROUND_WAVE_LEFT_RIGHT_DESAT = 94,
    BACKGROUND_DIAGONAL_WAVE_DESAT = 95,
    BACKGROUND_GRADIENT_UP_DOWN_DESAT = 96,
    BACKGROUND_GRADIENT_LEFT_RIGHT_DESAT = 97,
    BACKGROUND_GRADIENT_DIAGONAL_DESAT = 98,
    BACKGROUND_HUE_BREATHING_DESAT = 99,
    BACKGROUND_HUE_PENDULUM_DESAT = 100,
    BACKGROUND_HUE_WAVE_DESAT = 101,
    BACKGROUND_RAINBOW_MOVING_CHEVRON_DESAT = 102,
    BACKGROUND_BAND_PINWHEEL_SAT_DESAT = 103,
    BACKGROUND_BAND_PINWHEEL_VAL_DESAT = 104,
    BACKGROUND_BAND_SPIRAL_SAT_DESAT = 105,
    BACKGROUND_BAND_SPIRAL_VAL_DESAT = 106,
    BACKGROUND_DIAGONAL_WAVE_HUE_CYCLE = 107,
    BACKGROUND_DIAGONAL_WAVE_DUAL_COLOR = 108,
    BACKGROUND_DIAGONAL_WAVE_DUAL_COLOR_HUE_CYCLE = 109,
    BACKGROUND_DIAGONAL_WAVE_REVERSE = 110,
    BACKGROUND_DIAGONAL_WAVE_REVERSE_HUE_CYCLE = 111,
    BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR = 112,
    BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR_HUE_CYCLE = 113,
    BACKGROUND_DIAGONAL_WAVE_HUE_CYCLE_DESAT = 114,
    BACKGROUND_DIAGONAL_WAVE_DUAL_COLOR_DESAT = 115,
    BACKGROUND_DIAGONAL_WAVE_DUAL_COLOR_HUE_CYCLE_DESAT = 116,
    BACKGROUND_DIAGONAL_WAVE_REVERSE_DESAT = 117,
    BACKGROUND_DIAGONAL_WAVE_REVERSE_HUE_CYCLE_DESAT = 118,
    BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR_DESAT = 119,
    BACKGROUND_DIAGONAL_WAVE_REVERSE_DUAL_COLOR_HUE_CYCLE_DESAT = 120,
} background_mode_t;

#define MAX_MATH_BACKGROUNDS 27
#define BACKGROUND_MATH_START 59

typedef enum {
    BG_TYPE_SIMPLE,      // Uses (HSV, i, time)
    BG_TYPE_DX_DY,       // Uses (HSV, dx, dy, time)
    BG_TYPE_DIST,        // Uses (HSV, dx, dy, dist, time)
} background_type_t;

typedef HSV (*background_math_func_t)(HSV hsv, uint8_t i, uint8_t time);
typedef HSV (*background_math_dx_dy_func_t)(HSV hsv, int16_t dx, int16_t dy, uint8_t time);
typedef HSV (*background_math_dist_func_t)(HSV hsv, int16_t dx, int16_t dy, uint8_t dist, uint8_t time);

typedef struct {
    const char* name;
    background_type_t type;
    union {
        background_math_func_t simple_func;
        background_math_dx_dy_func_t dx_dy_func;
        background_math_dist_func_t dist_func;
    };
    uint8_t speed_multiplier;
    bool enabled;
} math_background_t;

typedef struct {
    live_note_positioning_t live_positioning;
    macro_note_positioning_t macro_positioning;
    live_animation_t live_animation;
    macro_animation_t macro_animation;
    bool use_influence;
    background_mode_t background_mode;
    uint8_t pulse_mode;
    uint8_t color_type;
    bool enabled;
    uint8_t background_brightness;  // 0-100 percentage relative to user brightness
    uint8_t live_speed;            // NEW: 0-255 live animation speed
    uint8_t macro_speed;           // NEW: 0-255 macro animation speed
} custom_animation_config_t;

// =============================================================================
// GLOBAL VARIABLES (extern declarations)
// =============================================================================

extern custom_animation_config_t custom_slots[NUM_CUSTOM_SLOTS];
extern uint8_t current_custom_slot;

// =============================================================================
// FUNCTION DECLARATIONS - Lighting Functions
// =============================================================================

// Parameter setting functions (lighting file)
void set_custom_slot_live_positioning(uint8_t slot, uint8_t value);
void set_custom_slot_macro_positioning(uint8_t slot, uint8_t value);
void set_custom_slot_background_brightness(uint8_t slot, uint8_t value);
void set_custom_slot_live_animation(uint8_t slot, uint8_t value);
void set_custom_slot_macro_animation(uint8_t slot, uint8_t value);
void set_custom_slot_use_influence(uint8_t slot, bool value);
void set_custom_slot_background_mode(uint8_t slot, uint8_t value);
void set_custom_slot_pulse_mode(uint8_t slot, uint8_t value);
void set_custom_slot_color_type(uint8_t slot, uint8_t value);
void set_custom_slot_enabled(uint8_t slot, bool value);

// EEPROM functions
void save_custom_animations_to_eeprom(void);
void load_custom_animations_from_eeprom(void);
void save_custom_slot_to_eeprom(uint8_t slot);
void load_custom_slot_from_eeprom(uint8_t slot);
void get_custom_slot_ram_stuff(uint8_t slot, uint8_t* data);
void get_custom_slot_parameters_from_eeprom(uint8_t slot, uint8_t* data);
// Parameter setting with EEPROM save
void set_and_save_custom_slot_live_positioning(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_macro_positioning(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_live_animation(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_macro_animation(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_use_influence(uint8_t slot, bool value);
void set_and_save_custom_slot_background_mode(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_pulse_mode(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_color_type(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_enabled(uint8_t slot, bool value);
void set_and_save_custom_slot_background_brightness(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_live_speed(uint8_t slot, uint8_t value);
void set_and_save_custom_slot_macro_speed(uint8_t slot, uint8_t value);

// Batch parameter functions
void set_custom_slot_parameters_from_bytes(uint8_t slot, uint8_t* data);
void get_custom_slot_parameters_as_bytes(uint8_t slot, uint8_t* data);

// Initialization
void init_custom_animations(void);

void randomize_order(void);

uint8_t get_midi_velocity(uint8_t layer, uint8_t note_index);

uint8_t apply_velocity_mode(uint8_t base_velocity, uint8_t layer, uint8_t note_index);

// ============================================================================
// LAYER-SPECIFIC ACTUATION SETTINGS
// ============================================================================

// Layer actuation structure (DEPRECATED - kept for backward compatibility)
// Global MIDI settings (velocity_mode, aftertouch, etc) now in keyboard_settings_t
//
// NOTE: This structure is DEPRECATED. Firmware now uses:
// - Per-key actuation via active_per_key_cache (for actuation points)
// - Global settings via keyboard_settings_t (for velocity_mode, aftertouch, etc)
// The HID protocol still accepts this format but values are applied globally.
typedef struct {
    uint8_t normal_actuation;              // DEPRECATED - per-key only now
    uint8_t midi_actuation;                // DEPRECATED - per-key only now
    uint8_t velocity_mode;                 // DEPRECATED - use global velocity_mode instead
    uint8_t velocity_speed_scale;          // DEPRECATED - replaced with min/max_press_time
    uint8_t flags;                         // DEPRECATED
    uint8_t aftertouch_mode;               // DEPRECATED - use global aftertouch_mode instead
    uint8_t aftertouch_cc;                 // DEPRECATED - use global aftertouch_cc instead
    uint8_t vibrato_sensitivity;           // DEPRECATED - use global vibrato_sensitivity instead
    uint16_t vibrato_decay_time;           // DEPRECATED - use global vibrato_decay_time instead
} layer_actuation_t;


// Flag bit definitions
#define LAYER_ACTUATION_FLAG_USE_FIXED_VELOCITY         (1 << 2)

// ============================================================================
// PER-KEY ACTUATION SYSTEM
// ============================================================================

// Per-key actuation settings (8 bytes per key) - FULL structure for EEPROM/HID
typedef struct {
    uint8_t actuation;              // 0-100 (0-2.5mm) - Default: 60 (1.5mm)
    uint8_t deadzone_top;           // 0-100 (0-2.5mm) - Default: 4 (0.1mm), max ~20 (0.5mm)
    uint8_t deadzone_bottom;        // 0-100 (0-2.5mm) - Default: 4 (0.1mm), max ~20 (0.5mm)
    uint8_t velocity_curve;         // 0-16 (0-6: Factory curves, 7-16: User curves) - Default: 0 (Linear)
    uint8_t flags;                  // Bit 0: rapidfire_enabled, Bit 1: use_per_key_velocity_curve - Default: 0
    uint8_t rapidfire_press_sens;   // 0-100 (0-2.5mm) - Default: 4 (0.1mm)
    uint8_t rapidfire_release_sens; // 0-100 (0-2.5mm) - Default: 4 (0.1mm)
    int8_t  rapidfire_velocity_mod; // -64 to +64 (velocity offset per RT) - Default: 0
} per_key_actuation_t;

// ============================================================================
// OPTIMIZED PER-KEY CACHE (4 bytes per key) - For fast matrix scan access
// ============================================================================
// This lightweight structure is cached in RAM for the active layer only.
// Total cache size: 70 keys × 4 bytes = 280 bytes (fits in L1 cache)
// The full per_key_actuation_t is still used for EEPROM and HID communication.

typedef struct __attribute__((packed)) {
    uint8_t actuation;      // 0-100 (0-2.5mm) actuation point
    uint8_t rt_down;        // Rapid trigger press sensitivity (0 = RT disabled)
    uint8_t rt_up;          // Rapid trigger release sensitivity
    uint8_t flags;          // Bit 0: RT enabled, Bit 1: per-key velocity, Bit 2: continuous RT
} per_key_config_lite_t;

// Compile-time size check
_Static_assert(sizeof(per_key_config_lite_t) == 4, "per_key_config_lite_t must be exactly 4 bytes");

// Per-key flag bit definitions
#define PER_KEY_FLAG_RAPIDFIRE_ENABLED          (1 << 0)
#define PER_KEY_FLAG_USE_PER_KEY_VELOCITY_CURVE (1 << 1)
#define PER_KEY_FLAG_CONTINUOUS_RT              (1 << 2)  // Continuous rapid trigger (reset at 0 instead of actuation point)

// Per-key actuation storage (70 keys × 8 bytes = 560 bytes per layer)
typedef struct {
    per_key_actuation_t keys[70];
} layer_key_actuations_t;

// Default values (0-255 scale for actuation, 0-51 scale for deadzones = 20% of travel)
#define DEFAULT_ACTUATION_VALUE 127             // 2.0mm (50% of 4mm = 127/255)
#define DEFAULT_DEADZONE_TOP 6                  // ~0.1mm (6/51 * 0.8mm)
#define DEFAULT_DEADZONE_BOTTOM 6               // ~0.1mm (6/51 * 0.8mm)
#define DEFAULT_VELOCITY_CURVE 2                // MEDIUM (linear)
#define DEFAULT_PER_KEY_FLAGS 0                 // All flags off (rapidfire off, use global velocity curve)
#define DEFAULT_RAPIDFIRE_PRESS_SENS 6          // ~0.1mm
#define DEFAULT_RAPIDFIRE_RELEASE_SENS 6        // ~0.1mm
#define DEFAULT_RAPIDFIRE_VELOCITY_MOD 0        // No offset

// External declarations
extern layer_actuation_t layer_actuations[12];  // DEPRECATED - use global settings instead
// Global MIDI settings are in keyboard_settings_t (velocity_mode, aftertouch_mode, etc.)
extern bool aftertouch_pedal_active;
extern uint8_t analog_mode;  // Global analog mode

// Per-key actuation arrays (firmware always uses per-key per-layer)
extern layer_key_actuations_t per_key_actuations[12];  // 6720 bytes total (560 bytes × 12 layers)
// NOTE: per_key_mode_enabled and per_key_per_layer_enabled have been REMOVED
// Firmware now ALWAYS uses per-key per-layer settings.

// Optimized per-key cache for active layer (280 bytes - fits in L1 cache)
// This cache is refreshed on layer change and used during matrix scan.
extern per_key_config_lite_t active_per_key_cache[70];
extern uint8_t active_per_key_cache_layer;

// Refresh the per-key cache for a given layer
void refresh_per_key_cache(uint8_t layer);

void save_layer_actuations(void);
void load_layer_actuations(void);
void reset_layer_actuations(void);
void set_layer_actuation(uint8_t layer, uint8_t normal, uint8_t midi, uint8_t velocity,
                         uint8_t vel_speed, uint8_t flags, uint8_t aftertouch_mode,
                         uint8_t aftertouch_cc, uint8_t vibrato_sensitivity,
                         uint16_t vibrato_decay_time);

void get_layer_actuation(uint8_t layer, uint8_t *normal, uint8_t *midi, uint8_t *velocity,
                         uint8_t *vel_speed, uint8_t *flags, uint8_t *aftertouch_mode,
                         uint8_t *aftertouch_cc, uint8_t *vibrato_sensitivity,
                         uint16_t *vibrato_decay_time);

bool layer_use_fixed_velocity(uint8_t layer);
bool layer_use_per_key_velocity_curve(uint8_t layer);

// HID handlers
void handle_set_layer_actuation(const uint8_t* data);
void handle_get_layer_actuation(uint8_t layer, uint8_t* response);
void handle_get_all_layer_actuations(void);
void handle_reset_layer_actuations(void);

// ============================================================================
// PER-KEY ACTUATION FUNCTIONS
// ============================================================================

// Initialization and EEPROM functions
void initialize_per_key_actuations(void);
void save_per_key_actuations(void);
void load_per_key_actuations(void);
void reset_per_key_actuations(void);

// Per-key lookup functions
uint8_t get_key_actuation_point(uint8_t layer, uint8_t row, uint8_t col);
per_key_actuation_t* get_key_settings(uint8_t layer, uint8_t row, uint8_t col);
uint8_t get_key_velocity_curve(uint8_t layer, uint8_t row, uint8_t col, uint8_t split_type);

// HID handlers for per-key actuation
void handle_set_per_key_actuation(const uint8_t* data);
void handle_get_per_key_actuation(const uint8_t* data, uint8_t* response);
void handle_set_per_key_mode(const uint8_t* data);
void handle_get_per_key_mode(uint8_t* response);
void handle_reset_per_key_actuations_hid(void);
void handle_copy_layer_actuations(const uint8_t* data);

// ============================================================================
// NULL BIND (SOCD HANDLING) SYSTEM
// ============================================================================
// Null bind groups allow multiple keys to be assigned together with a
// behavior that resolves simultaneous key presses (SOCD - Simultaneous
// Opposing Cardinal Directions).
//
// Behaviors:
//   NEUTRAL (0):      All keys nulled when 2+ pressed simultaneously
//   LAST_INPUT (1):   Last pressed key wins, others nulled
//   DISTANCE (2):     Key with most travel (pressed furthest) wins
//   PRIORITY_X (3+):  Absolute priority for key at index X in group
//                     (3 = key 0 priority, 4 = key 1 priority, etc.)
// ============================================================================

// Constants
#define NULLBIND_NUM_GROUPS         20      // Number of null bind groups
#define NULLBIND_MAX_KEYS_PER_GROUP 8       // Maximum keys per group
#define NULLBIND_GROUP_SIZE         18      // Bytes per group in EEPROM/RAM
#define NULLBIND_EEPROM_SIZE        (NULLBIND_NUM_GROUPS * NULLBIND_GROUP_SIZE)  // 360 bytes total

// Behavior enumeration
typedef enum {
    NULLBIND_BEHAVIOR_NEUTRAL = 0,      // All keys nulled when 2+ pressed
    NULLBIND_BEHAVIOR_LAST_INPUT = 1,   // Last pressed key wins
    NULLBIND_BEHAVIOR_DISTANCE = 2,     // Key with most travel wins
    NULLBIND_BEHAVIOR_PRIORITY_BASE = 3 // Priority behaviors start here (3 + key_index)
} nullbind_behavior_t;

// Null bind group structure (18 bytes per group)
// NOTE: Each group is now layer-specific. Groups only activate on their assigned layer.
typedef struct {
    uint8_t behavior;                               // nullbind_behavior_t
    uint8_t key_count;                              // Number of keys in this group (0-8)
    uint8_t keys[NULLBIND_MAX_KEYS_PER_GROUP];      // Key indices (row * 14 + col), 0xFF = unused
    uint8_t layer;                                  // Layer this group is active on (0-11), 0xFF = all layers (legacy)
    uint8_t reserved[7];                            // Reserved for future use (e.g., per-key priority order)
} nullbind_group_t;

// Runtime state for null bind processing
typedef struct {
    bool keys_pressed[NULLBIND_MAX_KEYS_PER_GROUP]; // Which keys in group are currently pressed
    uint8_t last_pressed_key;                       // Index of last pressed key in group (for LAST_INPUT)
    uint8_t active_key;                             // Currently active (non-nulled) key index, 0xFF = none
    uint32_t press_times[NULLBIND_MAX_KEYS_PER_GROUP]; // Press timestamps for LAST_INPUT
} nullbind_runtime_t;

// External declarations
extern nullbind_group_t nullbind_groups[NULLBIND_NUM_GROUPS];
extern nullbind_runtime_t nullbind_runtime[NULLBIND_NUM_GROUPS];
extern bool nullbind_enabled;  // Global enable flag

// HID Command IDs (0xF0-0xF4)
#define HID_CMD_NULLBIND_GET_GROUP      0xF0    // Get null bind group configuration
#define HID_CMD_NULLBIND_SET_GROUP      0xF1    // Set null bind group configuration
#define HID_CMD_NULLBIND_SAVE_EEPROM    0xF2    // Save all groups to EEPROM
#define HID_CMD_NULLBIND_LOAD_EEPROM    0xF3    // Load all groups from EEPROM
#define HID_CMD_NULLBIND_RESET_ALL      0xF4    // Reset all groups to defaults

// Initialization and EEPROM functions
void nullbind_init(void);
void nullbind_save_to_eeprom(void);
void nullbind_load_from_eeprom(void);
void nullbind_reset_all(void);

// Group management functions
bool nullbind_add_key_to_group(uint8_t group_num, uint8_t key_index);
bool nullbind_remove_key_from_group(uint8_t group_num, uint8_t key_index);
void nullbind_clear_group(uint8_t group_num);
bool nullbind_key_in_group(uint8_t group_num, uint8_t key_index);
int8_t nullbind_find_key_group(uint8_t key_index);  // Returns group num or -1 (ignores layer)
int8_t nullbind_find_key_group_for_layer(uint8_t key_index, uint8_t layer);  // Returns group num or -1 (layer-specific)

// Key processing functions (called from matrix scanning)
// NOTE: These are now layer-aware - groups only activate on their assigned layer
bool nullbind_should_null_key(uint8_t row, uint8_t col, uint8_t layer);
void nullbind_key_pressed(uint8_t row, uint8_t col, uint8_t travel, uint8_t layer);
void nullbind_key_released(uint8_t row, uint8_t col, uint8_t layer);
void nullbind_update_group_state(uint8_t group_num);

// HID handlers
void handle_nullbind_get_group(uint8_t group_num, uint8_t* response);
void handle_nullbind_set_group(const uint8_t* data);
void handle_nullbind_save_eeprom(void);
void handle_nullbind_load_eeprom(void);
void handle_nullbind_reset_all(void);

// ============================================================================
// TOGGLE KEYS SYSTEM
// ============================================================================
//
// Toggle keys allow a keypress to toggle between holding and releasing a
// target keycode. This is implemented as keybinds (TGL_00 - TGL_99) that
// can be assigned to any physical key in the keymap.
//
// When a toggle key is pressed:
// - If the target keycode is released, it becomes held
// - If the target keycode is held, it becomes released
//
// This is useful for gaming scenarios where you want to toggle a key state
// without continuously holding the physical key.
// ============================================================================

// Constants
#define TOGGLE_NUM_SLOTS            100     // Number of toggle slots (TGL_00 - TGL_99)
#define TOGGLE_SLOT_SIZE            4       // Bytes per slot in EEPROM/RAM
#define TOGGLE_EEPROM_SIZE          (TOGGLE_NUM_SLOTS * TOGGLE_SLOT_SIZE)  // 400 bytes total

// Toggle keycode range (100 keycodes: TGL_00 through TGL_99)
// NOTE: Moved from 0xEE00-0xEE63 to avoid conflict with Arpeggiator keycodes
#define TOGGLE_KEY_BASE             0xEF10
#define TOGGLE_KEY_MAX              (TOGGLE_KEY_BASE + TOGGLE_NUM_SLOTS - 1)  // 0xEF73

// Toggle slot structure (4 bytes per slot)
typedef struct {
    uint16_t target_keycode;            // Keycode to toggle (0 = disabled)
    uint8_t  reserved[2];               // Reserved for future use (e.g., options/flags)
} toggle_slot_t;

// Runtime state for toggle key processing
typedef struct {
    bool is_held;                       // Current state: true = target is held, false = released
} toggle_runtime_t;

// External declarations
extern toggle_slot_t toggle_slots[TOGGLE_NUM_SLOTS];
extern toggle_runtime_t toggle_runtime[TOGGLE_NUM_SLOTS];
extern bool toggle_enabled;  // Global enable flag

// HID Command IDs (0xF5-0xF9)
#define HID_CMD_TOGGLE_GET_SLOT         0xF5    // Get toggle slot configuration
#define HID_CMD_TOGGLE_SET_SLOT         0xF6    // Set toggle slot configuration
#define HID_CMD_TOGGLE_SAVE_EEPROM      0xF7    // Save all slots to EEPROM
#define HID_CMD_TOGGLE_LOAD_EEPROM      0xF8    // Load all slots from EEPROM
#define HID_CMD_TOGGLE_RESET_ALL        0xF9    // Reset all slots to defaults

// Initialization and EEPROM functions
void toggle_init(void);
void toggle_save_to_eeprom(void);
void toggle_load_from_eeprom(void);
void toggle_reset_all(void);

// Helper functions
static inline bool is_toggle_keycode(uint16_t keycode) {
    return (keycode >= TOGGLE_KEY_BASE && keycode <= TOGGLE_KEY_MAX);
}

static inline uint8_t toggle_keycode_to_slot(uint16_t keycode) {
    return (uint8_t)(keycode - TOGGLE_KEY_BASE);
}

// Key processing functions (called when TGL_XX key is pressed)
void toggle_process_key(uint16_t keycode, bool pressed);
void toggle_release_all(void);  // Release all held toggles

// HID handlers
void handle_toggle_get_slot(uint8_t slot_num, uint8_t* response);
void handle_toggle_set_slot(const uint8_t* data);
void handle_toggle_save_eeprom(void);
void handle_toggle_load_eeprom(void);
void handle_toggle_reset_all(void);