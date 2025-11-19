#pragma once
#include "quantum.h"
#include "eeconfig.h"

// Configuration constants
#ifndef MAX_MACROS
#    define MAX_MACROS 4  // Number of macro slots
#endif

#ifndef MACRO_BUFFER_SIZE
#    define MACRO_BUFFER_SIZE 20480  // 2KB per macro
#endif

// Time threshold for macro deletion (ms)
#ifndef MACRO_DELETE_THRESHOLD
#    define MACRO_DELETE_THRESHOLD 1000  // 2 seconds
#endif

// MIDI event types
#define MIDI_EVENT_NOTE_OFF 0
#define MIDI_EVENT_NOTE_ON 1
#define MIDI_EVENT_CC 2

// Add these after the existing #define statements
#define PREROLL_BUFFER_SIZE 32   // Max number of events in preroll
#define PREROLL_TIME_MS 200      // 200ms preroll time

// Preroll collection function and state variables - make these accessible
extern bool is_macro_primed;
extern bool collecting_preroll;
void collect_preroll_event(uint8_t type, uint8_t channel, uint8_t note, uint8_t velocity);

extern bool macro_in_overdub_mode[MAX_MACROS];
extern float macro_manual_speed[MAX_MACROS];
extern float macro_speed_factor[MAX_MACROS];
extern uint32_t loop_start_time;
extern uint32_t loop_length;

// Declare the overdub functions
void start_overdub_recording(uint8_t macro_num);
void end_overdub_recording(uint8_t macro_num);
void dynamic_macro_record_midi_event_overdub(uint8_t type, uint8_t channel, uint8_t note, uint8_t velocity);

// Add this to process_dynamic_macro.h to let midi.c know about the variable:
extern uint8_t macro_id;  // The currently recording macro ID

// And add this declaration so process_dynamic_macro.c can access current_macro_id:
extern uint8_t current_macro_id;

// Check if a macro is in overdub mode
bool is_macro_in_overdub(uint8_t macro_id);

// Record an event to the overdub buffer
void record_overdub_event(uint8_t type, uint8_t channel, uint8_t note, uint8_t velocity);

// Functions to mark/unmark notes from macros
void mark_note_from_macro(uint8_t channel, uint8_t note, uint8_t macro_id);
void unmark_note_from_macro(uint8_t channel, uint8_t note, uint8_t macro_id);
void cleanup_notes_from_macro(uint8_t macro_id);
bool is_live_note_active(uint8_t channel, uint8_t note);

// Main processing function
bool process_dynamic_macro(uint16_t keycode, keyrecord_t *record);

// Function to be called in matrix_scan_user
void matrix_scan_user_macro(void);

// MIDI event interception functions
void dynamic_macro_intercept_noteon(uint8_t channel, uint8_t note, uint8_t velocity, 
                                   uint8_t macro_id, void *macro_buffer1, 
                                   void *macro_buffer2, void **macro_pointer, 
                                   uint32_t *recording_start_time);
void dynamic_macro_intercept_noteoff(uint8_t channel, uint8_t note, uint8_t velocity, 
                                    uint8_t macro_id, void *macro_buffer1, 
                                    void *macro_buffer2, void **macro_pointer, 
                                    uint32_t *recording_start_time);
void dynamic_macro_intercept_cc(uint8_t channel, uint8_t cc_number, uint8_t value, 
                               uint8_t macro_id, void *macro_buffer1, 
                               void *macro_buffer2, void **macro_pointer, 
                               uint32_t *recording_start_time);

// Note cleanup function
void dynamic_macro_cleanup_notes(void);

// Setup and cleanup functions
void setup_dynamic_macro_recording(uint8_t macro_id, void *macro_buffer1, void *macro_buffer2, 
                                  void **macro_pointer, uint32_t *recording_start_time);
void stop_dynamic_macro_recording(void);

// Handle loop trigger from process_midi.c
void dynamic_macro_handle_loop_trigger(void);

// Optional user hooks
void dynamic_macro_record_start_user(int8_t direction);
void dynamic_macro_play_user(int8_t direction);
void dynamic_macro_record_key_user(int8_t direction, keyrecord_t *record);
void dynamic_macro_record_end_user(int8_t direction);
bool dynamic_macro_valid_key_user(uint16_t keycode, keyrecord_t *record);

// Function to get the live sustain state
bool get_live_sustain_state(void);
extern bool copy_modifier_active;
extern bool paste_modifier_active;
extern uint8_t source_macro_id;
// Macro state checking functions
bool dynamic_macro_is_playing(void);
bool dynamic_macro_is_playing_slot(uint8_t slot);
void dynamic_macro_bpm_changed(uint32_t new_bpm);

extern bool sample_mode_active;
extern bool overdub_muted[4];  // Assuming MAX_MACROS is 4
extern uint32_t current_bpm;
void render_interface(uint8_t x, uint8_t y);
void get_macro_status_string(uint8_t macro_idx, char* status_str);
void get_queued_command_string(uint8_t macro_idx, char* cmd_str, bool* should_flash);
void get_overdub_status_string(uint8_t macro_idx, char* overdub_str);
void get_loop_timer_string(uint8_t macro_idx, char* timer_str);
bool dynamic_macro_has_activity(void);
void force_clear_all_live_notes(void);
void dynamic_macro_init(void);

void noteoffdisplayupdates(uint8_t note);
void noteondisplayupdates(uint8_t note);
void smartchorddisplayupdates(uint8_t note);


void smartchordaddnotes(uint8_t channel, uint8_t note, uint8_t velocity);
void smartchordremovenotes(uint8_t channel, uint8_t note, uint8_t velocity);
void ccondisplayupdates(uint8_t channel, uint8_t cc, uint8_t value);
void programdisplayupdates(uint8_t channel, uint8_t program);
void pitchbenddisplayupdates(uint8_t channel, int16_t bend_value);

void dynamic_macro_process_sysex(uint8_t* data, uint16_t length);
void send_macro_via_hid(uint8_t macro_num);
void usb_send_func(MidiDevice* device, uint16_t cnt, uint8_t byte0, uint8_t byte1, uint8_t byte2);

void save_loop_settings(void);
void load_loop_settings(void);
void reset_loop_settings(void);
// Loop settings structure (add this after the keyboard_settings_t definition)
typedef struct {
    bool loop_messaging_enabled;
    uint8_t loop_messaging_channel;
    bool sync_midi_mode;
    bool alternate_restart_mode;
    bool loop_navigate_use_master_cc;
    
    // Main Loop CC arrays [4 loops each]
    uint8_t loop_restart_cc[4];
    uint8_t loop_start_recording_cc[4];
    uint8_t loop_stop_recording_cc[4];
    uint8_t loop_start_playing_cc[4];
    uint8_t loop_stop_playing_cc[4];
    uint8_t loop_clear_cc[4];
    
    // Overdub CC arrays [4 loops each]
    uint8_t overdub_start_recording_cc[4];
    uint8_t overdub_stop_recording_cc[4];
    uint8_t overdub_start_playing_cc[4];
    uint8_t overdub_stop_playing_cc[4];
    uint8_t overdub_clear_cc[4];
    
    // Navigation CCs
    uint8_t loop_navigate_master_cc;
    uint8_t loop_navigate_0_8_cc;
    uint8_t loop_navigate_1_8_cc;
    uint8_t loop_navigate_2_8_cc;
    uint8_t loop_navigate_3_8_cc;
    uint8_t loop_navigate_4_8_cc;
    uint8_t loop_navigate_5_8_cc;
    uint8_t loop_navigate_6_8_cc;
    uint8_t loop_navigate_7_8_cc;
	bool cclooprecording;
} loop_settings_t;

void dynamic_macro_hid_receive(uint8_t *data, uint8_t length);
// Add these function declarations to your header
bool is_custom_animations_eeprom_initialized(void);
void set_custom_animations_eeprom_initialized(void);

#include "eeconfig.h"

// Layer settings definitions
#define LAYER_BLOCK_SIZE 9
#define NUM_LAYERS 12
#define TOTAL_STORAGE_SIZE (LAYER_BLOCK_SIZE * NUM_LAYERS)

#define EECONFIG_CUSTOM_ANIMATIONS 62000
#define EECONFIG_CUSTOM_ANIMATIONS_SIZE (sizeof(custom_animation_config_t) * NUM_CUSTOM_SLOTS)


#define LOOP_SETTINGS_SIZE sizeof(loop_settings_t)
#define LOOP_SETTINGS_EEPROM_ADDR 64600  // Single address, no slots needed

#define RGB_DEFAULTS_MAGIC_ADDR 65300  // EEPROM address for magic number for the rgb custom layers
#define RGB_DEFAULTS_MAGIC_NUMBER 0xC0DE 

#define LAYER_SETTINGS_EEPROM_ADDR 65400

// Settings storage definitions
#define SETTINGS_SIZE sizeof(keyboard_settings_t)
#define SETTINGS_BASE_ADDR 65000
#define SETTINGS_EEPROM_ADDR(slot) (SETTINGS_BASE_ADDR + ((slot) * SETTINGS_SIZE))
#define SETTINGS_EEPROM_ADDR_DEFAULT SETTINGS_EEPROM_ADDR(0)


#define LAYER_ACTUATION_EEPROM_ADDR 65600
#define LAYER_ACTUATION_SIZE (sizeof(layer_actuation_t) * 12)  // 120 bytes for 12 layers

// Function declarations
void save_layer_actuations(void);
void load_layer_actuations(void);
void reset_layer_actuations(void);
void set_layer_actuation(uint8_t layer, uint8_t normal, uint8_t midi, uint8_t aftertouch,
                         uint8_t velocity, uint8_t rapid, uint8_t midi_rapid_sens,
                         uint8_t midi_rapid_vel, uint8_t vel_speed,
                         uint8_t aftertouch_cc, uint8_t flags,
                         uint8_t he_curve, uint8_t he_min, uint8_t he_max);
                         
void get_layer_actuation(uint8_t layer, uint8_t *normal, uint8_t *midi, uint8_t *aftertouch,
                         uint8_t *velocity, uint8_t *rapid, uint8_t *midi_rapid_sens,
                         uint8_t *midi_rapid_vel, uint8_t *vel_speed,
                         uint8_t *aftertouch_cc, uint8_t *flags,
                         uint8_t *he_curve, uint8_t *he_min, uint8_t *he_max);

bool layer_rapidfire_enabled(uint8_t layer);
bool layer_midi_rapidfire_enabled(uint8_t layer);
// Add these HID command definitions to vial.c (around line with other HID_CMD defines)
#define HID_CMD_SET_LAYER_ACTUATION 0xCA
#define HID_CMD_GET_LAYER_ACTUATION 0xCB
#define HID_CMD_GET_ALL_LAYER_ACTUATIONS 0xCC
#define HID_CMD_RESET_LAYER_ACTUATIONS 0xCD

// =============================================================================
// EEPROM MEMORY LAYOUT (64KB Total - 65536 bytes)
// =============================================================================
//
// 0-64199:     Available for macros, eeconfig, other data (64200 bytes)
//
// 63700-64399: Custom Animations - each animation is 10 bytes - have 500bytes of space - so room for 50 custom animations - including gap will be around 70
//
// 64400-64599: Gap (200 bytes safety buffer)
//
// 64600-64799: Loop Settings (200 bytes allocated, ~70 used) 
//              - loop_settings_t structure
//              - 130 bytes wiggle room for expansion
//
// 64800-64999: Gap (200 bytes safety buffer)
//
// 65000-65199: Keyboard Settings (200 bytes allocated, ~150 used)
//              - 5 slots × 40 bytes each = 200 bytes total
//              - keyboard_settings_t per slot (~30 bytes)
//              - 10 bytes wiggle room per slot
//              - Slot 0: 65000-65039
//              - Slot 1: 65040-65079  
//              - Slot 2: 65080-65119
//              - Slot 3: 65120-65159
//              - Slot 4: 65160-65199
//
// 65200-65399: Gap (200 bytes safety buffer)
//
// 65400-65535: Layer RGB Settings (136 bytes allocated, 108 used)
//              - 12 layers × 9 bytes each = 108 bytes used
//              - 28 bytes wiggle room for expansion
//
// =============================================================================
// EEPROM ADDRESSES SUMMARY:
// Custom Animations:   CUSTOM_ANIMATIONS_EEPROM_ADDR = 64200
// Loop Settings:       LOOP_SETTINGS_EEPROM_ADDR     = 64600  
// Keyboard Settings:   SETTINGS_BASE_ADDR            = 65000
// Layer RGB:           LAYER_SETTINGS_EEPROM_ADDR    = 65400
// =============================================================================

// Function declarations for layer settings
void save_layer_block(uint8_t layer, uint8_t data[LAYER_BLOCK_SIZE]);
void load_layer_block(uint8_t layer, uint8_t data[LAYER_BLOCK_SIZE]);
void apply_layer_block(uint8_t data[LAYER_BLOCK_SIZE]);
void rgb_layer_init(void);

typedef struct {
    int velocity_sensitivity;
    int cc_sensitivity;
    uint8_t channel_number;
    int8_t transpose_number;
    int8_t octave_number;
    int8_t transpose_number2;
    int8_t octave_number2;
    int8_t transpose_number3;
    int8_t octave_number3;
    uint8_t velocity_number;
    uint8_t velocity_number2;
    uint8_t velocity_number3;
    uint8_t randomvelocitymodifier;
    int oledkeyboard;
    bool overdub_advanced_mode;
    int smartchordlightmode;
    uint8_t keysplitchannel;
    uint8_t keysplit2channel;
    uint8_t keysplitstatus;
    uint8_t keysplittransposestatus;
    uint8_t keysplitvelocitystatus;
    bool custom_layer_animations_enabled;
    uint8_t unsynced_mode_active;
    bool sample_mode_active;
    // New loop messaging features
    bool loop_messaging_enabled;
    uint8_t loop_messaging_channel;
    bool sync_midi_mode;
    bool alternate_restart_mode;
	int colorblindmode;
	bool cclooprecording;
	bool truesustain;
} keyboard_settings_t;

extern int velocity_sensitivity;
extern int cc_sensitivity;
extern uint8_t channel_number;
extern int8_t transpose_number;
extern int8_t octave_number;
extern int8_t transpose_number2;
extern int8_t octave_number2;
extern int8_t transpose_number3;
extern int8_t octave_number3;
extern uint8_t velocity_number;
extern uint8_t velocity_number2;
extern uint8_t velocity_number3;
extern uint8_t randomvelocitymodifier;
extern int oledkeyboard;
extern int smartchordlight;
extern int smartchordlightmode;
extern uint8_t keysplitchannel;
extern uint8_t keysplit2channel;
extern uint8_t keysplitstatus;
extern uint8_t keysplittransposestatus;
extern uint8_t keysplitvelocitystatus;
extern bool custom_layer_animations_enabled;
extern uint8_t unsynced_mode_active;
extern bool sample_mode_active;
extern bool loop_messaging_enabled;
extern uint8_t loop_messaging_channel;
extern bool sync_midi_mode;
extern bool alternate_restart_mode;
extern int colorblindmode;
extern bool cclooprecording;
extern bool truesustain;

// Keyboard settings instance
extern keyboard_settings_t keyboard_settings;

// Keyboard settings function declarations
void save_keyboard_settings(void);
void load_keyboard_settings(void);
void save_keyboard_settings_to_slot(uint8_t slot);
void load_keyboard_settings_from_slot(uint8_t slot);
void reset_keyboard_settings(void);
void save_current_rgb_settings(uint8_t layer);
void apply_layer_rgb_settings(uint8_t layer);
void scan_current_layer_midi_leds(void);
void scan_keycode_categories(void);

void handle_external_clock_pulse(void);
void handle_external_clock_beat(void);
void handle_external_clock_start(void);
void handle_external_clock_stop(void);
void handle_external_clock_continue(void);
void check_external_clock_timeout(void);

void internal_clock_tempo_changed(void);
extern bool is_internal_clock_active(void);
void internal_clock_start(void);
extern bool is_external_clock_active(void);