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

#define DOUBLE_TAP_THRESHOLD 200  // 300ms threshold for double-tap detection

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
void collect_preroll_event(uint8_t type, uint8_t channel, uint8_t note, uint8_t raw_travel);

extern bool macro_in_overdub_mode[MAX_MACROS];
extern float macro_manual_speed[MAX_MACROS];
extern float macro_speed_factor[MAX_MACROS];
extern uint32_t loop_start_time;
extern uint32_t loop_length;

// Declare the overdub functions
void start_overdub_recording(uint8_t macro_num);
void end_overdub_recording(uint8_t macro_num);
void dynamic_macro_record_midi_event_overdub(uint8_t type, uint8_t channel, uint8_t note, uint8_t raw_travel);

// Add this to process_dynamic_macro.h to let midi.c know about the variable:
extern uint8_t macro_id;  // The currently recording macro ID

// And add this declaration so process_dynamic_macro.c can access current_macro_id:
extern uint8_t current_macro_id;

// Check if a macro is in overdub mode
bool is_macro_in_overdub(uint8_t macro_id);

// Record an event to the overdub buffer
void record_overdub_event(uint8_t type, uint8_t channel, uint8_t note, uint8_t raw_travel);

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
void dynamic_macro_intercept_noteon(uint8_t channel, uint8_t note, uint8_t raw_travel,
                                   uint8_t macro_id, void *macro_buffer1,
                                   void *macro_buffer2, void **macro_pointer,
                                   uint32_t *recording_start_time);
void dynamic_macro_intercept_noteoff(uint8_t channel, uint8_t note, uint8_t raw_travel,
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

// Macro recording velocity curve/range functions (Part 2: velocity transform system)
uint8_t get_macro_recording_curve(uint8_t macro_num);
void set_macro_recording_curve_target(uint8_t macro_num, uint8_t curve);

uint8_t get_macro_recording_min(uint8_t macro_num);
void set_macro_recording_min_target(uint8_t macro_num, uint8_t min);

uint8_t get_macro_recording_max(uint8_t macro_num);
void set_macro_recording_max_target(uint8_t macro_num, uint8_t max);
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


void smartchordaddnotes(uint8_t channel, uint8_t note, uint8_t raw_travel);
void smartchordremovenotes(uint8_t channel, uint8_t note, uint8_t raw_travel);
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

// =============================================================================
// EEPROM ADDRESS DEFINITIONS - REORGANIZED FOR 64KB EEPROM
// =============================================================================
// Layout for 64KB EEPROM (CAT24C512WI-GT3)
// All addresses verified to fit within 65535 bytes with spacing between features
//
// Memory Map (reorganized 2026-01-21):
//   0-4,508:       QMK/VIA base (keymaps, encoders, tap dance, combos, key overrides)
//   4,509-20,000:  VIA Text Macros (~15KB)
//   21,000-21,359: Null Bind (SOCD) Settings (see orthomidi5x14.h)
//   22,000-22,399: Toggle Keys (see orthomidi5x14.h)
//   23,000-26,999: Arp User Presets (see orthomidi5x14.h)
//   27,500-35,339: Seq User Presets (see orthomidi5x14.h)
//   36,000-36,699: Custom Animations (700 bytes)
//   37,000-37,199: Loop Settings (200 bytes)
//   38,000-38,249: Keyboard Settings (250 bytes, 5 slots)
//   38,500:        RGB Defaults Magic
//   39,000-39,107: Layer RGB Settings (108 bytes)
//   40,000-40,059: Layer Actuation Settings (60 bytes)
//   41,000-41,241: User Curves (see orthomidi5x14.h)
//   42,000-42,099: Gaming Settings (see orthomidi5x14.h)
//   43,000-43,889: Per-Key RGB (890 bytes)
//   45,000-51,719: Per-Key Actuation (6720 bytes)
//   52,000-65,535: Available for future use (~13KB)
// =============================================================================

#define EECONFIG_CUSTOM_ANIMATIONS 36000  // Custom animations (700 bytes)
#define EECONFIG_CUSTOM_ANIMATIONS_SIZE (sizeof(custom_animation_config_t) * NUM_CUSTOM_SLOTS)

#define LOOP_SETTINGS_SIZE sizeof(loop_settings_t)
#define LOOP_SETTINGS_EEPROM_ADDR 37000  // Loop settings (200 bytes)

#define RGB_DEFAULTS_MAGIC_ADDR 38500  // EEPROM address for magic number for the rgb custom layers
#define RGB_DEFAULTS_MAGIC_NUMBER 0xC0DE

#define LAYER_SETTINGS_EEPROM_ADDR 39000  // Layer RGB settings (108 bytes)

// Settings storage definitions
#define SETTINGS_SIZE sizeof(keyboard_settings_t)
#define SETTINGS_BASE_ADDR 38000  // Keyboard settings (250 bytes for 5 slots)
#define SETTINGS_EEPROM_ADDR(slot) (SETTINGS_BASE_ADDR + ((slot) * SETTINGS_SIZE))
#define SETTINGS_EEPROM_ADDR_DEFAULT SETTINGS_EEPROM_ADDR(0)

// Per-Key Actuation EEPROM addresses
#define PER_KEY_ACTUATION_EEPROM_ADDR 45000  // Per-key actuation (6720 bytes)
#define PER_KEY_ACTUATION_SIZE (sizeof(per_key_actuation_t) * 70 * 12)  // 6720 bytes (8 bytes × 70 keys × 12 layers)
#define PER_KEY_ACTUATION_FLAGS_ADDR (PER_KEY_ACTUATION_EEPROM_ADDR + PER_KEY_ACTUATION_SIZE)
// NOTE: Mode flags (per_key_mode_enabled, per_key_per_layer_enabled) have been REMOVED.
// Firmware now ALWAYS uses per-key per-layer settings. The flags EEPROM area is now unused.

// Layer Actuation EEPROM addresses
#define LAYER_ACTUATION_EEPROM_ADDR 40000  // Layer actuation (60 bytes)
#define LAYER_ACTUATION_SIZE (sizeof(layer_actuation_t) * 12)  // 60 bytes for 12 layers (5 bytes per layer)

// Function declarations (updated signatures - removed rapidfire params)
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
// Add these HID command definitions to vial.c (around line with other HID_CMD defines)
#define HID_CMD_SET_LAYER_ACTUATION 0xCA
#define HID_CMD_GET_LAYER_ACTUATION 0xCB
#define HID_CMD_GET_ALL_LAYER_ACTUATIONS 0xCC
#define HID_CMD_RESET_LAYER_ACTUATIONS 0xCD

// Gaming/Joystick HID Commands
#define HID_CMD_GAMING_SET_MODE 0xCE           // Set gaming mode on/off
#define HID_CMD_GAMING_SET_KEY_MAP 0xCF        // Map key to joystick control
#define HID_CMD_GAMING_SET_ANALOG_CONFIG 0xD0  // Set min/max travel and deadzone
#define HID_CMD_GAMING_GET_SETTINGS 0xD1       // Get current gaming settings
#define HID_CMD_GAMING_RESET 0xD2              // Reset gaming settings to defaults

// =============================================================================
// EEPROM ADDRESSES SUMMARY (REORGANIZED 2026-01-21 - ALL WITHIN 64KB):
// VIA Text Macros:     4509-20000                    (DYNAMIC_KEYMAP_EEPROM_MAX_ADDR)
// Null Bind:           NULLBIND_EEPROM_ADDR          = 21000 (orthomidi5x14.h)
// Toggle Keys:         TOGGLE_EEPROM_ADDR            = 22000 (orthomidi5x14.h)
// Arp Presets:         ARP_EEPROM_ADDR               = 23000 (orthomidi5x14.h)
// Seq Presets:         SEQ_EEPROM_ADDR               = 27500 (orthomidi5x14.h)
// Custom Animations:   EECONFIG_CUSTOM_ANIMATIONS    = 36000
// Loop Settings:       LOOP_SETTINGS_EEPROM_ADDR     = 37000
// Keyboard Settings:   SETTINGS_BASE_ADDR            = 38000
// RGB Magic:           RGB_DEFAULTS_MAGIC_ADDR       = 38500
// Layer RGB:           LAYER_SETTINGS_EEPROM_ADDR    = 39000
// Layer Actuation:     LAYER_ACTUATION_EEPROM_ADDR   = 40000
// User Curves:         USER_CURVES_EEPROM_ADDR       = 41000 (orthomidi5x14.h)
// Gaming Settings:     GAMING_SETTINGS_EEPROM_ADDR   = 42000 (orthomidi5x14.h)
// Per-Key RGB:         PER_KEY_RGB_EEPROM_ADDR       = 43000 (per_key_rgb.h)
// Per-Key Actuation:   PER_KEY_ACTUATION_EEPROM_ADDR = 45000
// Available:           52000-65535                   (~13KB for future use)
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
    uint8_t dynamic_range;  // Maximum allowed differential between velocity min and max (0-127)
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
    // Global MIDI Velocity/Aftertouch Settings (not per-layer)
    uint8_t velocity_mode;                // 0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak
    uint8_t aftertouch_mode;              // 0=Off, 1=Bottom-out, 2=Reverse, 3=Post-actuation, 4=Bottom-out(no sus), 5=Reverse(no sus), 6=Vibrato
    uint8_t aftertouch_cc;                // 0-127=CC number, 255=off (poly AT only)
    uint8_t vibrato_sensitivity;          // 50-200 (percentage, 100=normal)
    uint16_t vibrato_decay_time;          // 0-2000 (milliseconds)
    uint16_t min_press_time;              // 50-500ms (slow press threshold for min velocity)
    uint16_t max_press_time;              // 1-100ms (fast press threshold for max velocity)
    // Base/Main MIDI HE Velocity curve and range
    uint8_t he_velocity_curve;            // 0-4 (SOFTEST, SOFT, MEDIUM, HARD, HARDEST) - global fallback
    uint8_t he_velocity_min;              // 1-127 (minimum velocity)
    uint8_t he_velocity_max;              // 1-127 (maximum velocity)
    // Keysplit HE Velocity curve and range
    uint8_t keysplit_he_velocity_curve;   // 0-4 (SOFTEST, SOFT, MEDIUM, HARD, HARDEST)
    uint8_t keysplit_he_velocity_min;     // 1-127 (minimum velocity)
    uint8_t keysplit_he_velocity_max;     // 1-127 (maximum velocity)
    // Triplesplit HE Velocity curve and range
    uint8_t triplesplit_he_velocity_curve; // 0-4 (SOFTEST, SOFT, MEDIUM, HARD, HARDEST)
    uint8_t triplesplit_he_velocity_min;   // 1-127 (minimum velocity)
    uint8_t triplesplit_he_velocity_max;   // 1-127 (maximum velocity)
    // Sustain settings (0=Ignore, 1=ON)
    uint8_t base_sustain;                 // Base/main MIDI sustain
    uint8_t keysplit_sustain;             // Keysplit MIDI sustain
    uint8_t triplesplit_sustain;          // Triplesplit MIDI sustain
    // Hall Effect Sensor Linearization
    uint8_t lut_correction_strength;      // 0-100: 0=linear (no correction), 100=full logarithmic LUT
    // MIDI Routing Override Settings (startup defaults)
    bool channeloverride;                 // Override channel with fixed channel_number
    bool velocityoverride;                // Override velocity calculation
    bool transposeoverride;               // Override transpose
    uint8_t midi_in_mode;                 // MIDI IN routing mode (0=Process All, 1=Thru, 2=Clock Only, 3=Ignore)
    uint8_t usb_midi_mode;                // USB MIDI routing mode (0=Process All, 1=Thru, 2=Clock Only, 3=Ignore)
    uint8_t midi_clock_source;            // Clock source (0=Local, 1=USB, 2=MIDI IN)
    bool macro_override_live_notes;       // When true, macro notes play even if same note is live (skip live note check)
    uint8_t smartchord_mode;              // 0=Hold, 1=Toggle
    uint8_t base_smartchord_ignore;       // 0=Allow smartchord, 1=Ignore smartchord for base zone
    uint8_t keysplit_smartchord_ignore;    // 0=Allow smartchord, 1=Ignore smartchord for keysplit zone
    uint8_t triplesplit_smartchord_ignore; // 0=Allow smartchord, 1=Ignore smartchord for triplesplit zone
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
extern uint8_t dynamic_range;
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
// Global MIDI Velocity/Aftertouch Settings
extern uint8_t velocity_mode;
extern uint8_t aftertouch_mode;
extern uint8_t aftertouch_cc;
extern uint8_t vibrato_sensitivity;
extern uint16_t vibrato_decay_time;
extern uint16_t min_press_time;
extern uint16_t max_press_time;
extern uint8_t preset_speed_peak_ratio;
extern uint8_t he_velocity_curve;
extern uint8_t he_velocity_min;
extern uint8_t he_velocity_max;
extern uint8_t keysplit_he_velocity_min;
extern uint8_t keysplit_he_velocity_max;
extern uint8_t triplesplit_he_velocity_min;
extern uint8_t triplesplit_he_velocity_max;
extern uint8_t base_sustain;
extern uint8_t keysplit_sustain;
extern uint8_t triplesplit_sustain;
// Hall Effect Sensor Linearization
extern uint8_t lut_correction_strength;
// MIDI Routing Override Settings
extern bool channeloverride;
extern bool velocityoverride;
extern bool transposeoverride;

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