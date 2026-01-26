#include "process_midi.h"
#include "process_dynamic_macro.h"
#include "matrix.h"

#ifdef MIDI_ENABLE
#    include <LUFA/Drivers/USB/USB.h>
#    include "midi.h"
#    include "qmk_midi.h"

// Define constants for live note tracking
#define MAX_LIVE_NOTES 32
#define MAX_SUSTAIN_NOTES 64


// Array to track live (non-macro) notes that are currently held
uint8_t live_notes[MAX_LIVE_NOTES][3]; // [channel, note, velocity]
uint8_t live_note_count = 0;
uint8_t analog_mode = 0;

// Array to track notes held by sustain pedal
uint8_t sustain_notes[MAX_SUSTAIN_NOTES][3]; // [channel, note, velocity]
uint8_t sustain_note_count = 0;

// Flag to track if sustain pedal is currently active
static bool sustain_active = false;

uint8_t  current_macro_id = 0;
static void    *current_macro_buffer1 = NULL;
static void    *current_macro_buffer2 = NULL;
static void   **current_macro_pointer = NULL;
static uint32_t *current_recording_start_time = NULL;

// External functions for arpeggiator press order tracking
extern void arp_track_note_pressed(uint8_t live_note_index);
extern void arp_track_note_moved(uint8_t from_index, uint8_t to_index);

// Function to add a note to the live notes array
static void add_live_note(uint8_t channel, uint8_t note, uint8_t velocity) {
    // First check if this note is in the sustain queue
    // If it is, remove it since we're playing it again
    for (uint8_t i = 0; i < sustain_note_count; i++) {
        if (sustain_notes[i][0] == channel && sustain_notes[i][1] == note) {
            // Remove this note from sustain queue by swapping with the last note
            if (i < sustain_note_count - 1) {
                sustain_notes[i][0] = sustain_notes[sustain_note_count-1][0];
                sustain_notes[i][1] = sustain_notes[sustain_note_count-1][1];
                sustain_notes[i][2] = sustain_notes[sustain_note_count-1][2];
            }
            sustain_note_count--;
            dprintf("midi: removed note from sustain queue ch:%d note:%d (playing again)\n",
                    channel, note);
            break;
        }
    }

    // Now add to live notes
    if (live_note_count < MAX_LIVE_NOTES) {
        uint8_t new_index = live_note_count;
        live_notes[new_index][0] = channel;
        live_notes[new_index][1] = note;
        live_notes[new_index][2] = velocity;
        live_note_count++;

        // Track press order for arpeggiator
        arp_track_note_pressed(new_index);

        dprintf("midi: added live note ch:%d note:%d vel:%d (total: %d)\n",
                channel, note, velocity, live_note_count);
    }
}

// Function to remove a note from the live notes array
static void remove_live_note(uint8_t channel, uint8_t note) {
    for (uint8_t i = 0; i < live_note_count; i++) {
        if (live_notes[i][0] == channel && live_notes[i][1] == note) {
            // Move the last note to this position
            if (i < live_note_count - 1) {
                uint8_t from_idx = live_note_count - 1;
                live_notes[i][0] = live_notes[from_idx][0];
                live_notes[i][1] = live_notes[from_idx][1];
                live_notes[i][2] = live_notes[from_idx][2];

                // Track the move for arpeggiator press order
                arp_track_note_moved(from_idx, i);
            }
            live_note_count--;
            dprintf("midi: removed live note ch:%d note:%d (remaining: %d)\n",
                    channel, note, live_note_count);
            break;
        }
    }
}

void force_clear_all_live_notes(void) {
    dprintf("midi: force clearing all live notes (count: %d)\n", live_note_count);
    
    // Simply reset the count to 0 to clear all live notes
    live_note_count = 0;
    
    dprintf("midi: cleared all live notes\n");
}


// Function to add a note to the sustain notes queue
static void add_sustain_note(uint8_t channel, uint8_t note, uint8_t velocity) {
    if (sustain_note_count < MAX_SUSTAIN_NOTES) {
        sustain_notes[sustain_note_count][0] = channel;
        sustain_notes[sustain_note_count][1] = note;
        sustain_notes[sustain_note_count][2] = velocity;
        sustain_note_count++;
        dprintf("midi: added sustain note ch:%d note:%d vel:%d (total: %d)\n", 
                channel, note, velocity, sustain_note_count);
    }
}

// Function to send all accumulated sustain note-offs
static void flush_sustain_notes(void) {
    dprintf("midi: flushing %d sustain notes\n", sustain_note_count);
    
    for (uint8_t i = 0; i < sustain_note_count; i++) {
        // Send the actual note-off
        midi_send_noteoff(&midi_device, 
                          sustain_notes[i][0], 
                          sustain_notes[i][1], 
                          sustain_notes[i][2]);
        remove_lighting_live_note(sustain_notes[i][0], sustain_notes[i][1]);
        // Also record this note-off in the macro if we're recording
        if (current_macro_id > 0) {
            dynamic_macro_intercept_noteoff(sustain_notes[i][0], 
                                          sustain_notes[i][1], 
                                          sustain_notes[i][2], 
                                          current_macro_id, 
                                          current_macro_buffer1, 
                                          current_macro_buffer2, 
                                          current_macro_pointer, 
                                          current_recording_start_time);
        }
        
        dprintf("midi: sent noteoff for sustained note ch:%d note:%d vel:%d\n",
                sustain_notes[i][0], sustain_notes[i][1], sustain_notes[i][2]);
    }
    
    sustain_note_count = 0;
}

// Track notes that are from macro playback
#define MAX_MACRO_NOTES 64
uint8_t macro_notes[MAX_MACRO_NOTES][3]; // [channel, note, macro_id]
uint8_t macro_note_count = 0;

// Function to mark a note as coming from a specific macro
void mark_note_from_macro(uint8_t channel, uint8_t note, uint8_t macro_id) {
    if (macro_note_count < MAX_MACRO_NOTES) {
        macro_notes[macro_note_count][0] = channel;
        macro_notes[macro_note_count][1] = note;
        macro_notes[macro_note_count][2] = macro_id;
        macro_note_count++;
        dprintf("midi: marked note as from macro %d ch:%d note:%d\n", 
                macro_id, channel, note);
    }
}

// Function to unmark a note as coming from a specific macro
void unmark_note_from_macro(uint8_t channel, uint8_t note, uint8_t macro_id) {
    for (uint8_t i = 0; i < macro_note_count; i++) {
        if (macro_notes[i][0] == channel && 
            macro_notes[i][1] == note && 
            macro_notes[i][2] == macro_id) {
            // Remove by swapping with the last note
            if (i < macro_note_count - 1) {
                macro_notes[i][0] = macro_notes[macro_note_count-1][0];
                macro_notes[i][1] = macro_notes[macro_note_count-1][1];
                macro_notes[i][2] = macro_notes[macro_note_count-1][2];
            }
			remove_lighting_macro_note(channel, note, macro_id);
            macro_note_count--;
            dprintf("midi: unmarked note from macro %d ch:%d note:%d\n", 
                    macro_id, channel, note);
            break;
        }
    }
}

// Function to check if a specific note is currently being played live
bool is_live_note_active(uint8_t channel, uint8_t note) {
    // Check physically held notes
    for (uint8_t i = 0; i < live_note_count; i++) {
        if (live_notes[i][0] == channel && live_notes[i][1] == note) {
            return true; // This is an active live note
        }
    }
    
    // Also check sustain-held notes
    for (uint8_t i = 0; i < sustain_note_count; i++) {
        if (sustain_notes[i][0] == channel && sustain_notes[i][1] == note) {
            return true; // This is a sustained note (treat as live)
        }
    }
    
    return false; // Not an active live note
}

// Function to send note-offs for all notes from a specific macro
void cleanup_notes_from_macro(uint8_t macro_id) {
    dprintf("midi: cleaning up all notes from macro %d\n", macro_id);
    
    // First, find all notes from this macro
    uint8_t notes_to_stop[MAX_MACRO_NOTES][2]; // [channel, note]
    uint8_t notes_to_stop_count = 0;
    
    // Collect all notes from this macro
    for (uint8_t i = 0; i < macro_note_count; i++) {
        if (macro_notes[i][2] == macro_id) {
            if (notes_to_stop_count < MAX_MACRO_NOTES) {
                notes_to_stop[notes_to_stop_count][0] = macro_notes[i][0]; // channel
                notes_to_stop[notes_to_stop_count][1] = macro_notes[i][1]; // note
                notes_to_stop_count++;
            }
        }
    }
    
    // Now send note-offs for all collected notes
    for (uint8_t i = 0; i < notes_to_stop_count; i++) {
        // Skip note-offs for notes that are currently being played live
        if (!is_live_note_active(notes_to_stop[i][0], notes_to_stop[i][1])) {
            midi_send_noteoff(&midi_device, notes_to_stop[i][0], notes_to_stop[i][1], 0);
            dprintf("midi: sent note-off for macro %d ch:%d note:%d\n", 
                    macro_id, notes_to_stop[i][0], notes_to_stop[i][1]);
        } else {
            dprintf("midi: skipped note-off for macro %d ch:%d note:%d (active live note)\n", 
                    macro_id, notes_to_stop[i][0], notes_to_stop[i][1]);
        }
        
        // Always unmark this note from the macro tracking
        unmark_note_from_macro(notes_to_stop[i][0], notes_to_stop[i][1], macro_id);
    }
}

// Function to check if a note is from any macro playback
static bool is_note_from_macro(uint8_t channel, uint8_t note) {
    // Check if this note is in our macro_notes array
    for (uint8_t i = 0; i < macro_note_count; i++) {
        if (macro_notes[i][0] == channel && macro_notes[i][1] == note) {
            return true; // It's a macro note
        }
    }
    return false; // Not a macro note
}

bool get_live_sustain_state(void) {
    return sustain_active;
}

void setup_dynamic_macro_recording(uint8_t macro_id, void *macro_buffer1, void *macro_buffer2, 
                                  void **macro_pointer, uint32_t *recording_start_time) {
    current_macro_id = macro_id;
    current_macro_buffer1 = macro_buffer1;
    current_macro_buffer2 = macro_buffer2;
    current_macro_pointer = macro_pointer;
    current_recording_start_time = recording_start_time;
}

void stop_dynamic_macro_recording(void) {
    current_macro_id = 0;
}

#    ifdef MIDI_BASIC

// In process_midi_basic_noteon:
void process_midi_basic_noteon(uint8_t note) {
    // Send the note-on to MIDI device
    midi_send_noteon(&midi_device, 0, note, 127);
    
    // Add to live notes tracking
    add_live_note(0, note, 127);

    // Collect for preroll if it's active (only for slave recordings)
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_ON, 0, note, 127);
    }
    
    // Record to macro if we're recording
    if (current_macro_id > 0) {
        dynamic_macro_intercept_noteon(0, note, 127, current_macro_id, 
                                      current_macro_buffer1, current_macro_buffer2, 
                                      current_macro_pointer, current_recording_start_time);
    }
}

// In process_midi_basic_noteoff:  
void process_midi_basic_noteoff(uint8_t note) {
    // Remove from live notes tracking
    remove_live_note(0, note);

    
    // Collect for preroll if it's active (only for slave recordings)
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_OFF, 0, note, 0);
    }
    
    // Check if sustain is active and this is a live note (not from macro playback)
    if (sustain_active && !is_note_from_macro(0, note)) {
        // Add to sustain queue instead of sending immediately
        add_sustain_note(0, note, 0);
    } else {
        // Send noteoff immediately
        midi_send_noteoff(&midi_device, 0, note, 0);
    }
    
    // Record to macro if we're recording
    if (current_macro_id > 0) {
        dynamic_macro_intercept_noteoff(0, note, 0, current_macro_id, 
                                       current_macro_buffer1, current_macro_buffer2, 
                                       current_macro_pointer, current_recording_start_time);
    }
}

void process_midi_all_notes_off(void) {
    // Turn off all live notes
    for (uint8_t i = 0; i < live_note_count; i++) {
        midi_send_noteoff(&midi_device, live_notes[i][0], live_notes[i][1], live_notes[i][2]);
    }
    live_note_count = 0;
    
    // Clear the sustain queue
    sustain_note_count = 0;
    
    // Reset standard MIDI note tracking arrays
    for (uint8_t i = 0; i < MIDI_TONE_COUNT; i++) {
        tone_status[0][i] = MIDI_INVALID_NOTE;
        tone_status[1][i] = 0;
        toneb_status[0][i] = MIDI_INVALID_NOTE;
        toneb_status[1][i] = 0;
        tonec_status[0][i] = MIDI_INVALID_NOTE;
        tonec_status[1][i] = 0;
    }

    // Send all notes off CC to all channels
    for (uint8_t channel = 0; channel < 16; channel++) {
        midi_send_cc(&midi_device, channel, 0x7B, 0);
    }
}

#    endif // MIDI_BASIC

#    ifdef MIDI_ADVANCED

#        include "timer.h"

static uint8_t tone_status[2][MIDI_TONE_COUNT];
static uint8_t toneb_status[2][MIDI_TONE_COUNT];
static uint8_t tonec_status[2][MIDI_TONE_COUNT];

static uint8_t  midi_modulation;
static int8_t   midi_modulation_step;
static uint16_t midi_modulation_timer;
midi_config_t   midi_config;

inline uint8_t compute_velocity(uint8_t setting) {
    return setting * (128 / (MIDI_VELOCITY_MAX - MIDI_VELOCITY_MIN));
}

void midi_init(void) {
    midi_config.octave              = QK_MIDI_OCTAVE_0 - MIDI_OCTAVE_MIN;
    midi_config.transpose           = 0;
    midi_config.velocity            = 127;
    midi_config.channel             = 0;
    midi_config.modulation_interval = 8;

    for (uint8_t i = 0; i < MIDI_TONE_COUNT; i++) {
        tone_status[0][i] = MIDI_INVALID_NOTE;
        tone_status[1][i] = 0;
        toneb_status[0][i] = MIDI_INVALID_NOTE;
        toneb_status[1][i] = 0;
        tonec_status[0][i] = MIDI_INVALID_NOTE;
        tonec_status[1][i] = 0;
    }
    
    live_note_count = 0;
    sustain_note_count = 0;
    sustain_active = false;

    midi_modulation       = 0;
    midi_modulation_step  = 0;
    midi_modulation_timer = 0;
}

uint8_t midi_compute_note(uint16_t keycode) {
    return (keycode - MIDI_TONE_MIN) + (transpose_number + octave_number + 24);
}

uint8_t midi_compute_note2(uint16_t keycode) {
    // keysplittransposestatus: 0=disabled, 1=keysplit only, 2=triplesplit only, 3=both
    int transpose_value2 = (keysplittransposestatus == 1 || keysplittransposestatus == 3) ?
                           (transpose_number2 + octave_number2) : (transpose_number + octave_number);

    return (keycode - 50688) + transpose_value2 + 24;
}

uint8_t midi_compute_note3(uint16_t keycode) {
    // keysplittransposestatus: 0=disabled, 1=keysplit only, 2=triplesplit only, 3=both
    int transpose_value3 = (keysplittransposestatus == 2 || keysplittransposestatus == 3) ?
                           (transpose_number3 + octave_number3) : (transpose_number + octave_number);

    return (keycode - 50800) + transpose_value3 + 24;
}

// Add this helper function at the top of process_midi.c
uint8_t apply_velocity_mode(uint8_t base_velocity, uint8_t layer, uint8_t note_index) {
    uint8_t final_velocity;

    if (analog_mode == 0) {
        // Mode 0: Fixed velocity (no random modifier)
        final_velocity = base_velocity;
    } else {
        // Modes 1, 2, 3: Use pre-calculated analog velocity from matrix.c
        final_velocity = get_midi_velocity(layer, note_index);

        // If velocity is default and we have a base velocity, use that
        if (final_velocity == 64 && base_velocity != 64) {
            final_velocity = base_velocity;
        }
    }

    if (final_velocity < 1) final_velocity = 1;
    if (final_velocity > 127) final_velocity = 127;

    return final_velocity;
}

// Weak default implementation - keyboards can override this
__attribute__((weak)) uint8_t get_he_velocity_from_position(uint8_t row, uint8_t col) {
    // Default implementation returns 0, indicating no HE velocity available
    return 0;
}

// Helper function for applying HE velocity with row/col from keyrecord
uint8_t apply_he_velocity_from_record(uint8_t base_velocity, keyrecord_t *record) {
    if (analog_mode > 0 && record != NULL) {
        // Get HE velocity from the key's row/col position
        uint8_t he_vel = get_he_velocity_from_position(record->event.key.row, record->event.key.col);
        if (he_vel > 0) {
            return he_vel;
        }
    }
    {
        // Fallback to base velocity (no random modifier)
        uint8_t final_velocity = base_velocity;
        if (final_velocity < 1) final_velocity = 1;
        if (final_velocity > 127) final_velocity = 127;
        return final_velocity;
    }
}

// Helper function to get raw travel from keyrecord
// Returns 0-255 raw travel value, or 0 if not available (non-analog)
uint8_t get_raw_travel_from_record(keyrecord_t *record) {
    if (analog_mode > 0 && record != NULL) {
        return analog_matrix_get_travel_normalized(record->event.key.row, record->event.key.col);
    }
    return 0; // No analog data available
}

// Modified noteon functions
void midi_send_noteon_smartchord(uint8_t channel, uint8_t note, uint8_t velocity) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    uint8_t final_velocity = apply_velocity_mode(velocity, current_layer, note);

    midi_send_noteon(&midi_device, channel, note, final_velocity);
    noteondisplayupdates(note);
    add_live_note(channel, note, final_velocity);
    add_lighting_live_note(channel, note);

    // Smartchord doesn't have raw_travel, use final_velocity as fallback
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_ON, channel, note, final_velocity);
    }

    if (current_macro_id > 0) {
        dynamic_macro_intercept_noteon(channel, note, final_velocity, current_macro_id,
                                     current_macro_buffer1, current_macro_buffer2,
                                     current_macro_pointer, current_recording_start_time);
    }
}


void midi_send_noteoff_smartchord(uint8_t channel, uint8_t note, uint8_t velocity) {
    // Remove from live notes tracking
    if (is_note_from_macro(channel, note) && !is_live_note_active(channel, note)) {
        return; // Don't let live note-offs stop macro notes unless the note is actually live
    }

    remove_live_note(channel, note);
	noteoffdisplayupdates(note);


    // Collect for preroll if it's active (only for slave recordings)
    // Smartchord doesn't have raw_travel, use velocity as fallback
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_OFF, channel, note, velocity);
    }

    // Check if sustain is active and this is NOT a note from macro playback
    if (sustain_active) {
        // Add to sustain queue instead of sending immediately
        add_sustain_note(channel, note, velocity);

        // Don't record the note-off in the macro yet!
        // We'll record it when the sustain pedal is released
    } else {
        // Send noteoff immediately (for macro playback notes or when sustain is not active)
        midi_send_noteoff(&midi_device, channel, note, velocity);
        remove_lighting_live_note(channel, note);
        // Record to macro if we're recording (and it's not a sustained note)
        if (current_macro_id > 0 && (!sustain_active || is_note_from_macro(channel, note))) {
            dynamic_macro_intercept_noteoff(channel, note, velocity, current_macro_id,
                                          current_macro_buffer1, current_macro_buffer2,
                                          current_macro_pointer, current_recording_start_time);
        }
    }
}

void midi_send_noteon_trainer(uint8_t channel, uint8_t note, uint8_t velocity) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);

    uint8_t final_velocity = apply_velocity_mode(velocity, current_layer, note);

    midi_send_noteon(&midi_device, channel, note, final_velocity);
    noteondisplayupdates(note);
    add_live_note(channel, note, final_velocity);
    add_lighting_live_note(channel, note);

    // Trainer doesn't have raw_travel, use final_velocity as fallback
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_ON, channel, note, final_velocity);
    }

    if (current_macro_id > 0) {
        dynamic_macro_intercept_noteon(channel, note, final_velocity, current_macro_id,
                                     current_macro_buffer1, current_macro_buffer2,
                                     current_macro_pointer, current_recording_start_time);
    }
}

void midi_send_noteoff_trainer(uint8_t channel, uint8_t note, uint8_t velocity) {
    // Remove from live notes tracking
    if (is_note_from_macro(channel, note) && !is_live_note_active(channel, note)) {
        return; // Don't let live note-offs stop macro notes unless the note is actually live
    }
    // Collect for preroll if it's active (only for slave recordings)
    // Trainer doesn't have raw_travel, use velocity as fallback
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_OFF, channel, note, velocity);
    }

    // Check if sustain is active and this is NOT a note from macro playback
    if (sustain_active) {
        // Add to sustain queue instead of sending immediately
        add_sustain_note(channel, note, velocity);

        // Don't record the note-off in the macro yet!
        // We'll record it when the sustain pedal is released
    } else {
        // Send noteoff immediately (for macro playback notes or when sustain is not active)
        midi_send_noteoff(&midi_device, channel, note, velocity);
        remove_lighting_live_note(channel, note);
        // Record to macro if we're recording (and it's not a sustained note)
        if (current_macro_id > 0 && (!sustain_active || is_note_from_macro(channel, note))) {
            dynamic_macro_intercept_noteoff(channel, note, velocity, current_macro_id,
                                          current_macro_buffer1, current_macro_buffer2,
                                          current_macro_pointer, current_recording_start_time);
        }
    }
}

static void simulate_sustain_keycode(bool pressed) {
    keyrecord_t record;
    record.event.key.row = 0;
    record.event.key.col = 0;
    record.event.pressed = pressed;
    record.event.time = timer_read();
    
    // Call the existing process_midi function with QK_MIDI_SUSTAIN
    process_midi(0x7186, &record);  // 0x7186 is QK_MIDI_SUSTAIN
}

// Modified midi_send_external_cc_with_recording function
void midi_send_external_cc_with_recording(uint8_t channel, uint8_t cc, uint8_t value) {
    // Special handling for sustain pedal (only if truesustain is false)
    if (cc == 0x40 && !truesustain) {
        bool new_sustain_state = (value >= 64);
        
        // Simulate keycode press/release instead of handling internally
        if (new_sustain_state != sustain_active) {
            simulate_sustain_keycode(new_sustain_state);
        }
        
        // Record to macro if we're recording and cclooprecording is enabled
        if (current_macro_id > 0 && cclooprecording) {
            dynamic_macro_intercept_cc(channel, cc, value, current_macro_id, 
                                     current_macro_buffer1, current_macro_buffer2, 
                                     current_macro_pointer, current_recording_start_time);
        }
    } else {
        // For all other CC messages (or CC40 when truesustain is enabled), send them normally
        midi_send_cc(&midi_device, channel, cc, value);
        
        // Record to macro if we're recording and cclooprecording is enabled
        if (current_macro_id > 0 && cclooprecording) {
            dynamic_macro_intercept_cc(channel, cc, value, current_macro_id, 
                                     current_macro_buffer1, current_macro_buffer2, 
                                     current_macro_pointer, current_recording_start_time);
        }
    }
    
    // Update display to show CC information
    ccondisplayupdates(channel, cc, value);
    
    dprintf("midi: sent CC ch:%d cc:%d val:%d (ccloop:%d truesustain:%d)\n", 
            channel, cc, value, cclooprecording, truesustain);
}

void midi_send_cc_with_recording(uint8_t channel, uint8_t cc, uint8_t value) {
    // Special handling for sustain pedal
    if (cc == 0x40) {
        bool new_sustain_state = (value >= 64);
        
        // Only handle state changes
        if (new_sustain_state != sustain_active) {
            sustain_active = new_sustain_state;
            
            // If sustain was just released, send all queued note-offs
            if (!sustain_active && sustain_note_count > 0) {
                flush_sustain_notes();
            }
            
            dprintf("midi: sustain state changed to %d\n", sustain_active);
        }
        
        // Don't send actual sustain CC if we're handling it internally
        // But still record to macro if we're recording
        if (current_macro_id > 0) {
            dynamic_macro_intercept_cc(channel, cc, value, current_macro_id, 
                                     current_macro_buffer1, current_macro_buffer2, 
                                     current_macro_pointer, current_recording_start_time);
        }
    } else {
        // For all other CC messages, send them normally
        midi_send_cc(&midi_device, channel, cc, value);
        
        // Record to macro if we're recording
        if (current_macro_id > 0) {
            dynamic_macro_intercept_cc(channel, cc, value, current_macro_id, 
                                     current_macro_buffer1, current_macro_buffer2, 
                                     current_macro_pointer, current_recording_start_time);
        }
    }
}

void midi_send_program_with_recording(uint8_t channel, uint8_t program) {
    // Send program change
    midi_send_programchange(&midi_device, channel, program);

    programdisplayupdates(channel, program);
    
    dprintf("midi: sent Program ch:%d prog:%d\n", channel, program);
}

void midi_send_aftertouch_with_recording(uint8_t channel, uint8_t note, uint8_t pressure) {
    // Send aftertouch
    midi_send_aftertouch(&midi_device, channel, note, pressure);

    dprintf("midi: sent Aftertouch ch:%d note:%d pressure:%d\n", channel, note, pressure);
}

void midi_send_channel_pressure_with_recording(uint8_t channel, uint8_t pressure) {
    // Send channel pressure
    midi_send_channelpressure(&midi_device, channel, pressure);
}

void midi_send_pitchbend_with_recording(uint8_t channel, int16_t bend_value) {
    // Send pitchbend
    midi_send_pitchbend(&midi_device, channel, bend_value);

    // Update display to show pitchbend information
    pitchbenddisplayupdates(channel, bend_value);
    
    dprintf("midi: sent Pitchbend ch:%d value:%d\n", channel, bend_value);
}

void midi_send_noteon_with_recording(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);

    uint8_t final_velocity = apply_velocity_mode(velocity, current_layer, note);

    // Check if arpeggiator is active - suppress direct MIDI output
    // The arp engine will generate its own notes from the live_notes[] array
    extern bool arp_is_active(void);
    bool arp_suppressed = arp_is_active();

    if (!arp_suppressed) {
        midi_send_noteon(&midi_device, channel, note, final_velocity);
        smartchordaddnotes(channel, note, final_velocity);
        smartchorddisplayupdates(note);
    }

    // Always update display and live note tracking (arp reads live_notes[])
    noteondisplayupdates(note);
    add_live_note(channel, note, final_velocity);
    add_lighting_live_note(channel, note);

    // Use raw_travel if available, otherwise use final_velocity as fallback
    uint8_t travel_for_recording = (raw_travel > 0) ? raw_travel : final_velocity;

    // QUICK BUILD HOOK: Intercept notes for arpeggiator/sequencer building
    extern bool quick_build_is_active(void);
    extern void quick_build_handle_note(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel);
    if (quick_build_is_active()) {
        quick_build_handle_note(channel, note, final_velocity, raw_travel);
    }

    // Skip preroll and macro recording when arp is active (arp records its own output)
    if (!arp_suppressed) {
        if (collecting_preroll) {
            collect_preroll_event(MIDI_EVENT_NOTE_ON, channel, note, travel_for_recording);
        }

        if (current_macro_id > 0) {
            dynamic_macro_intercept_noteon(channel, note, travel_for_recording, current_macro_id,
                                         current_macro_buffer1, current_macro_buffer2,
                                         current_macro_pointer, current_recording_start_time);
        }
    }
}


void midi_send_noteoff_with_recording(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel, uint8_t note_type) {
    if (is_note_from_macro(channel, note) && !is_live_note_active(channel, note)) {
        return; // Don't let live note-offs stop macro notes unless the note is actually live
    }

    bool was_live_note = false;
    for (uint8_t i = 0; i < live_note_count; i++) {
        if (live_notes[i][0] == channel && live_notes[i][1] == note) {
            was_live_note = true;
            break;
        }
    }

    // Always remove from live notes tracking (arp reads live_notes[])
    remove_live_note(channel, note);
    noteoffdisplayupdates(note);

    // Check if arpeggiator is active - suppress direct MIDI output
    // Note-on was never sent, so no note-off needed either
    extern bool arp_is_active(void);
    if (arp_is_active()) {
        remove_lighting_live_note(channel, note);
        return;
    }

    smartchordremovenotes(channel, note, velocity);

    // Use raw_travel if available, otherwise use velocity as fallback
    uint8_t travel_for_recording = (raw_travel > 0) ? raw_travel : velocity;

    // Collect for preroll if it's active (only for slave recordings)
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_OFF, channel, note, travel_for_recording);
    }

    // Check if this note type should ignore sustain
    // note_type: 0=base, 1=keysplit, 2=triplesplit
    // sustain value: 0=allow (add to sustain queue), 1=ignore (send immediately)
    bool ignore_sustain = false;
    if (note_type == 0 && base_sustain == 1) {
        ignore_sustain = true;  // Base notes ignore sustain
    } else if (note_type == 1 && keysplit_sustain == 1) {
        ignore_sustain = true;  // Keysplit notes ignore sustain
    } else if (note_type == 2 && triplesplit_sustain == 1) {
        ignore_sustain = true;  // Triplesplit notes ignore sustain
    }

    // Handle sustain logic
    if (sustain_active && !ignore_sustain) {
        // Add to sustain queue instead of sending immediately
        add_sustain_note(channel, note, velocity);

        // Don't record the note-off in the macro yet!
        // We'll record it when the sustain pedal is released
    } else {
        // Send noteoff immediately (for macro playback notes or when sustain is not active)
        midi_send_noteoff(&midi_device, channel, note, velocity);
        remove_lighting_live_note(channel, note);
        // Record to macro if we're recording (and it's not a sustained note)
        if (current_macro_id > 0 && (!sustain_active || !was_live_note || ignore_sustain)) {
            dynamic_macro_intercept_noteoff(channel, note, travel_for_recording, current_macro_id,
                                          current_macro_buffer1, current_macro_buffer2,
                                          current_macro_pointer, current_recording_start_time);
        }
    }
}

// =============================================================================
// ARPEGGIATOR MIDI FUNCTIONS
// =============================================================================
// These functions are similar to midi_send_noteon/off_with_recording, but:
// - Do NOT add to live_notes[] (would pollute master note tracking)
// - Instead add to arp_notes[] for gate timing management
// - Still record to macros
// - Still trigger LED lighting

void midi_send_noteon_arp(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);

    // Apply velocity mode conversion (reuses existing velocity curve logic)
    uint8_t final_velocity = apply_velocity_mode(velocity, current_layer, note);

    // Send MIDI note-on
    midi_send_noteon(&midi_device, channel, note, final_velocity);

    // Display updates
    noteondisplayupdates(note);

    // Add to arp_notes[] for gate tracking (not live_notes[]!)
    // This is handled by add_arp_note() in orthomidi5x14.c

    // Add LED lighting (existing code handles the rest)
    add_lighting_live_note(channel, note);

    // Use raw_travel if available, otherwise use final_velocity as fallback
    uint8_t travel_for_recording = (raw_travel > 0) ? raw_travel : final_velocity;

    // Collect for preroll if active (for slave recordings)
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_ON, channel, note, travel_for_recording);
    }

    // Record to macro if we're recording
    if (current_macro_id > 0) {
        dynamic_macro_intercept_noteon(channel, note, travel_for_recording, current_macro_id,
                                     current_macro_buffer1, current_macro_buffer2,
                                     current_macro_pointer, current_recording_start_time);
    }

    dprintf("arp: note-on ch:%d note:%d vel:%d raw:%d\n", channel, note, final_velocity, raw_travel);
}

void midi_send_noteoff_arp(uint8_t channel, uint8_t note, uint8_t velocity) {
    // Send MIDI note-off
    midi_send_noteoff(&midi_device, channel, note, velocity);

    // Display updates
    noteoffdisplayupdates(note);

    // Remove LED lighting
    remove_lighting_live_note(channel, note);

    // Collect for preroll if active (for slave recordings)
    if (collecting_preroll) {
        collect_preroll_event(MIDI_EVENT_NOTE_OFF, channel, note, velocity);
    }

    // Record to macro if we're recording
    if (current_macro_id > 0) {
        dynamic_macro_intercept_noteoff(channel, note, velocity, current_macro_id,
                                       current_macro_buffer1, current_macro_buffer2,
                                       current_macro_pointer, current_recording_start_time);
    }

    dprintf("arp: note-off ch:%d note:%d vel:%d\n", channel, note, velocity);
}

// Modified process_midi main switch cases
bool process_midi(uint16_t keycode, keyrecord_t *record) {
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);

    switch (keycode) {
        case MIDI_TONE_MIN ... MIDI_TONE_MAX: {
            uint8_t channel  = channel_number;
            uint8_t tone     = keycode - MIDI_TONE_MIN;
            uint8_t velocity = velocity_number;

            // Get raw travel from analog matrix (0-255) for macro recording
            uint8_t raw_travel = get_raw_travel_from_record(record);

            // Use HE velocity curve if analog_mode is enabled
            if (analog_mode > 0) {
                velocity = apply_he_velocity_from_record(velocity, record);
            } else {
                velocity = apply_velocity_mode(velocity, current_layer, tone);
            }

            if (record->event.pressed) {
                uint8_t note = midi_compute_note(keycode);
                midi_send_noteon_with_recording(channel, note, velocity, raw_travel);
                dprintf("midi noteon channel:%d note:%d velocity:%d\n", channel, note, velocity);
                tone_status[1][tone] += 1;
                if (tone_status[0][tone] == MIDI_INVALID_NOTE) {
                    tone_status[0][tone] = note;
                }
            } else {
                uint8_t note = tone_status[0][tone];
                tone_status[1][tone] -= 1;
                if (tone_status[1][tone] == 0) {
                    midi_send_noteoff_with_recording(channel, note, velocity, raw_travel, 0);  // note_type=0 (base)
                    dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, note, velocity);
                    tone_status[0][tone] = MIDI_INVALID_NOTE;
                }
            }
            return false;
        }
    
        case 0xC600 ... 0xC647: {
            uint8_t channel = 0;
            // keysplitstatus: 0=disabled, 1=keysplit only, 2=triplesplit only, 3=both
            if (keysplitstatus == 1 || keysplitstatus == 3) {
                channel = keysplitchannel;
            } else {
                channel = channel_number;
            }
            uint8_t toneb     = keycode - 50684;
            uint8_t velocity = 0;

            // Get raw travel from analog matrix (0-255) for macro recording
            uint8_t raw_travel = get_raw_travel_from_record(record);

            // keysplitvelocitystatus: 0=disabled, 1=keysplit only, 2=triplesplit only, 3=both
            if (keysplitvelocitystatus == 1 || keysplitvelocitystatus == 3) {
                // Use Keysplit HE velocity curve from layer settings
                velocity = get_keysplit_he_velocity_from_position(record->event.key.row, record->event.key.col);
            } else {
                // Use base velocity method (same as MIDI_TONE_MIN...MIDI_TONE_MAX)
                velocity = velocity_number;
                if (analog_mode > 0) {
                    velocity = apply_he_velocity_from_record(velocity, record);
                } else {
                    velocity = apply_velocity_mode(velocity, current_layer, toneb);
                }
            }

            if (record->event.pressed) {
                uint8_t noteb = midi_compute_note2(keycode);
                midi_send_noteon_with_recording(channel, noteb, velocity, raw_travel);
                dprintf("midi noteon channel:%d note:%d velocity:%d\n", channel, noteb, velocity);
                toneb_status[1][toneb] += 1;
                if (toneb_status[0][toneb] == MIDI_INVALID_NOTE) {
                    toneb_status[0][toneb] = noteb;
                }
            } else {
                uint8_t noteb = toneb_status[0][toneb];
                toneb_status[1][toneb] -= 1;
                if (toneb_status[1][toneb] == 0) {
                    midi_send_noteoff_with_recording(channel, noteb, velocity, raw_travel, 1);  // note_type=1 (keysplit)
                    dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, noteb, velocity);
                    toneb_status[0][toneb] = MIDI_INVALID_NOTE;
                }
            }
            return false;
        }    
        case 0xC670 ... 0xC6B7: {
            uint8_t channel = 0;
            // keysplitstatus: 0=disabled, 1=keysplit only, 2=triplesplit only, 3=both
            if (keysplitstatus == 2 || keysplitstatus == 3) {
                channel = keysplit2channel;
            } else {
                channel = channel_number;
            }
            uint8_t tonec     = keycode - 50796;
            uint8_t velocity = 0;

            // Get raw travel from analog matrix (0-255) for macro recording
            uint8_t raw_travel = get_raw_travel_from_record(record);

            // keysplitvelocitystatus: 0=disabled, 1=keysplit only, 2=triplesplit only, 3=both
            if (keysplitvelocitystatus == 2 || keysplitvelocitystatus == 3) {
                // Use Triplesplit HE velocity curve from layer settings
                velocity = get_triplesplit_he_velocity_from_position(record->event.key.row, record->event.key.col);
            } else {
                // Use base velocity method (same as MIDI_TONE_MIN...MIDI_TONE_MAX)
                velocity = velocity_number;
                if (analog_mode > 0) {
                    velocity = apply_he_velocity_from_record(velocity, record);
                } else {
                    velocity = apply_velocity_mode(velocity, current_layer, tonec);
                }
            }

            if (record->event.pressed) {
                uint8_t notec = midi_compute_note3(keycode);
                midi_send_noteon_with_recording(channel, notec, velocity, raw_travel);
                dprintf("midi noteon channel:%d note:%d velocity:%d\n", channel, notec, velocity);
                tonec_status[1][tonec] += 1;
                if (tonec_status[0][tonec] == MIDI_INVALID_NOTE) {
                    tonec_status[0][tonec] = notec;
                }
            } else {
                uint8_t notec = tonec_status[0][tonec];
                tonec_status[1][tonec] -= 1;
                if (tonec_status[1][tonec] == 0) {
                    midi_send_noteoff_with_recording(channel, notec, velocity, raw_travel, 2);  // note_type=2 (triplesplit)
                    dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, notec, velocity);
                    tonec_status[0][tonec] = MIDI_INVALID_NOTE;
                }
            }
            return false;
        }    
        case MIDI_OCTAVE_MIN ... MIDI_OCTAVE_MAX:
            if (record->event.pressed) {
                midi_config.octave = keycode - MIDI_OCTAVE_MIN;
                dprintf("midi octave %d\n", midi_config.octave);
            }
            return false;
        case QK_MIDI_OCTAVE_DOWN:
            if (record->event.pressed && midi_config.octave > 0) {
                midi_config.octave--;
                dprintf("midi octave %d\n", midi_config.octave);
            }
            return false;
        case QK_MIDI_OCTAVE_UP:
            if (record->event.pressed && midi_config.octave < (MIDI_OCTAVE_MAX - MIDI_OCTAVE_MIN)) {
                midi_config.octave++;
                dprintf("midi octave %d\n", midi_config.octave);
            }
            return false;
        case MIDI_TRANSPOSE_MIN ... MIDI_TRANSPOSE_MAX:
            if (record->event.pressed) {
                midi_config.transpose = keycode - QK_MIDI_TRANSPOSE_0;
                dprintf("midi transpose %d\n", midi_config.transpose);
            }
            return false;
        case QK_MIDI_TRANSPOSE_DOWN:
            if (record->event.pressed && midi_config.transpose > (MIDI_TRANSPOSE_MIN - QK_MIDI_TRANSPOSE_0)) {
                midi_config.transpose--;
                dprintf("midi transpose %d\n", midi_config.transpose);
            }
            return false;
        case QK_MIDI_TRANSPOSE_UP:
            if (record->event.pressed && midi_config.transpose < (MIDI_TRANSPOSE_MAX - QK_MIDI_TRANSPOSE_0)) {
                const bool positive = midi_config.transpose > 0;
                midi_config.transpose++;
                if (positive && midi_config.transpose < 0) midi_config.transpose--;
                dprintf("midi transpose %d\n", midi_config.transpose);
            }
            return false;
        case MIDI_VELOCITY_MIN ... MIDI_VELOCITY_MAX:
            if (record->event.pressed) {
                midi_config.velocity = compute_velocity(keycode - MIDI_VELOCITY_MIN);
                dprintf("midi velocity %d\n", midi_config.velocity);
            }
            return false;
        case QK_MIDI_VELOCITY_DOWN:
            if (record->event.pressed && midi_config.velocity > 0) {
                if (midi_config.velocity == 127) {
                    midi_config.velocity -= 10;
                } else if (midi_config.velocity > 12) {
                    midi_config.velocity -= 13;
                } else {
                    midi_config.velocity = 0;
                }

                dprintf("midi velocity %d\n", midi_config.velocity);
            }
            return false;
        case QK_MIDI_VELOCITY_UP:
            if (record->event.pressed && midi_config.velocity < 127) {
                if (midi_config.velocity < 115) {
                    midi_config.velocity += 13;
                } else {
                    midi_config.velocity = 127;
                }
                dprintf("midi velocity %d\n", midi_config.velocity);
            }
            return false;
        case MIDI_CHANNEL_MIN ... MIDI_CHANNEL_MAX:
            if (record->event.pressed) {
                midi_config.channel = keycode - MIDI_CHANNEL_MIN;
                dprintf("midi channel %d\n", midi_config.channel);
            }
            return false;
        case QK_MIDI_CHANNEL_DOWN:
            if (record->event.pressed) {
                midi_config.channel--;
                dprintf("midi channel %d\n", midi_config.channel);
            }
            return false;
        case QK_MIDI_CHANNEL_UP:
            if (record->event.pressed) {
                midi_config.channel++;
                dprintf("midi channel %d\n", midi_config.channel);
            }
            return false;
        case QK_MIDI_ALL_NOTES_OFF:
            if (record->event.pressed) {
                // Clear all live notes and the sustain queue
                live_note_count = 0;
                sustain_note_count = 0;
                
                midi_send_cc(&midi_device, channel_number, 0x7B, 0);
                dprintf("midi all notes off\n");
            }
            return false;
        case QK_MIDI_SUSTAIN:
            if (record->event.pressed) {
                // Sustain pedal pressed
                sustain_active = true;
                dprintf("midi sustain pedal pressed\n");
            } else {
                // Sustain pedal released
                sustain_active = false;
                
                // Flush any queued note-offs
                if (sustain_note_count > 0) {
                    flush_sustain_notes();					
                }
                dprintf("midi sustain pedal released\n");
            }
            
            // Don't send actual sustain CC to MIDI device
            
            return false;
        case QK_MIDI_PORTAMENTO:
            midi_send_cc_with_recording(channel_number, 0x41, record->event.pressed ? 127 : 0);
            dprintf("midi portamento %d\n", record->event.pressed);
            return false;
        case QK_MIDI_SOSTENUTO:
            midi_send_cc_with_recording(channel_number, 0x42, record->event.pressed ? 127 : 0);
            dprintf("midi sostenuto %d\n", record->event.pressed);
            return false;
        case QK_MIDI_SOFT:
            midi_send_cc_with_recording(channel_number, 0x43, record->event.pressed ? 127 : 0);
            dprintf("midi soft %d\n", record->event.pressed);
            return false;
        case QK_MIDI_LEGATO:
            midi_send_cc_with_recording(channel_number, 0x44, record->event.pressed ? 127 : 0);
            dprintf("midi legato %d\n", record->event.pressed);
            return false;
        case QK_MIDI_MODULATION:
            midi_modulation_step = record->event.pressed ? 1 : -1;
            return false;
        case QK_MIDI_MODULATION_SPEED_DOWN:
            if (record->event.pressed) {
                midi_config.modulation_interval++;
                if (midi_config.modulation_interval == 0) midi_config.modulation_interval--;
                dprintf("midi modulation interval %d\n", midi_config.modulation_interval);
            }
            return false;
        case QK_MIDI_MODULATION_SPEED_UP:
            if (record->event.pressed && midi_config.modulation_interval > 0) {
                midi_config.modulation_interval--;
                dprintf("midi modulation interval %d\n", midi_config.modulation_interval);
            }
            return false;
        case QK_MIDI_PITCH_BEND_DOWN:
            if (record->event.pressed) {
                midi_send_pitchbend(&midi_device, channel_number, -0x2000);
                dprintf("midi pitchbend channel:%d amount:%d\n", channel_number, -0x2000);
            } else {
                midi_send_pitchbend(&midi_device, channel_number, 0);
                dprintf("midi pitchbend channel:%d amount:%d\n", channel_number, 0);
            }
            return false;
        case QK_MIDI_PITCH_BEND_UP:
            if (record->event.pressed) {
                midi_send_pitchbend(&midi_device, channel_number, 0x1fff);
                dprintf("midi pitchbend channel:%d amount:%d\n", channel_number, 0x1fff);
            } else {
                midi_send_pitchbend(&midi_device, channel_number, 0);
                dprintf("midi pitchbend channel:%d amount:%d\n", channel_number, 0);
            }
            return false;
    };

    return true;
}

void midi_task(void) {
    midi_device_process(&midi_device);
#    ifdef MIDI_ADVANCED
    if (timer_elapsed(midi_modulation_timer) < midi_config.modulation_interval) return;
    midi_modulation_timer = timer_read();

    if (midi_modulation_step != 0) {
        dprintf("midi modulation %d\n", midi_modulation);
        midi_send_cc_with_recording(channel_number, 0x1, midi_modulation);

        if (midi_modulation_step < 0 && midi_modulation < -midi_modulation_step) {
            midi_modulation      = 0;
            midi_modulation_step = 0;
            return;
        }

        midi_modulation += midi_modulation_step;

        if (midi_modulation > 127) midi_modulation = 127;
    }
#    endif
}

#    endif // MIDI_ADVANCED

#endif // MIDI_ENABLE