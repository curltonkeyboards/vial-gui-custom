// orthomidi5x14.h
#ifndef ORTHOMIDI5X14_H
#define ORTHOMIDI5X14_H
extern int smartchordstatus;
extern int chordkey2;
extern int chordkey3;
extern int chordkey4;
extern int chordkey5;
extern int chordkey6;
extern int heldkey1;
extern int colorblindmode;
extern uint8_t chordkey1_led_index;
extern uint8_t chordkey2_led_index;
extern uint8_t chordkey3_led_index;
extern uint8_t chordkey4_led_index;
extern uint8_t chordkey5_led_index;
extern uint8_t chordkey6_led_index;
extern uint8_t chordkey7_led_index;
extern uint8_t chordkey1_led_index2;
extern uint8_t chordkey2_led_index2;
extern uint8_t chordkey3_led_index2;
extern uint8_t chordkey4_led_index2;
extern uint8_t chordkey5_led_index2;
extern uint8_t chordkey6_led_index2;
extern uint8_t chordkey7_led_index2;
extern uint8_t chordkey1_led_index3;
extern uint8_t chordkey2_led_index3;
extern uint8_t chordkey3_led_index3;
extern uint8_t chordkey4_led_index3;
extern uint8_t chordkey5_led_index3;
extern uint8_t chordkey6_led_index3;
extern uint8_t chordkey7_led_index3;
extern uint8_t chordkey1_led_index4;
extern uint8_t chordkey2_led_index4; 
extern uint8_t chordkey3_led_index4;
extern uint8_t chordkey4_led_index4;
extern uint8_t chordkey5_led_index4;
extern uint8_t chordkey6_led_index4;
extern uint8_t chordkey7_led_index4;
extern uint8_t chordkey1_led_index5;
extern uint8_t chordkey2_led_index5;
extern uint8_t chordkey3_led_index5;
extern uint8_t chordkey4_led_index5;
extern uint8_t chordkey5_led_index5;
extern uint8_t chordkey6_led_index5;
extern uint8_t chordkey7_led_index5;
extern uint8_t chordkey1_led_index6;
extern uint8_t chordkey2_led_index6;
extern uint8_t chordkey3_led_index6;
extern uint8_t chordkey4_led_index6;
extern uint8_t chordkey5_led_index6;
extern uint8_t chordkey6_led_index6;
extern uint8_t chordkey7_led_index6;

extern bool bpm_flash_state;
extern uint8_t bpm_beat_count;
extern uint32_t current_bpm;
extern void update_bpm_flash(void);

extern uint8_t keysplitstatus;
extern uint8_t keysplittransposestatus;
extern uint8_t keysplitvelocitystatus;

// In orthomidi5x14.h
#define NUM_LAYERS 12  
#define MAX_CATEGORIZED_LEDS 70  // Maximum possible, but we'll only use what we need
typedef struct {
    uint8_t led_index;
    uint8_t category;
} categorized_led_t;
typedef struct {
    categorized_led_t leds[MAX_CATEGORIZED_LEDS];
    uint8_t count;  // How many LEDs actually have categories on this layer
} layer_categories_t;
extern layer_categories_t led_categories[NUM_LAYERS];
#include "eeconfig.h"

void load_keyboard_settings(void);
void reset_keyboard_settings(void);
void load_keyboard_settings_from_slot(uint8_t slot);
void scan_current_layer_midi_leds(void);
void scan_keycode_categories(void);
void update_layer_animations_setting_slot0_direct(bool new_value);
extern bool truekey_effects_active;

// MIDI Routing Mode Enums and Functions
typedef enum {
    MIDI_IN_TO_USB,        // Send MIDI In directly to USB only
    MIDI_IN_TO_OUT,        // Send MIDI In directly to MIDI Out only
    MIDI_IN_PROCESS,       // Send MIDI In through keyboard processing
    MIDI_IN_CLOCK_ONLY,    // Only forward clock messages from MIDI In
    MIDI_IN_IGNORE         // Ignore all MIDI In data
} midi_in_mode_t;

typedef enum {
    USB_MIDI_TO_OUT,       // Send USB MIDI directly to MIDI Out
    USB_MIDI_PROCESS,      // Send USB MIDI through keyboard processing
    USB_MIDI_IGNORE        // Ignore all USB MIDI data
} usb_midi_mode_t;

typedef enum {
    CLOCK_SOURCE_LOCAL,    // Use local/internal clock generation
    CLOCK_SOURCE_USB,      // Use clock from USB MIDI
    CLOCK_SOURCE_MIDI_IN   // Use clock from hardware MIDI IN
} midi_clock_source_t;

extern midi_in_mode_t midi_in_mode;
extern usb_midi_mode_t usb_midi_mode;
extern midi_clock_source_t midi_clock_source;

void route_midi_in_data(uint8_t byte1, uint8_t byte2, uint8_t byte3, uint8_t num_bytes);
void route_usb_midi_data(uint8_t byte1, uint8_t byte2, uint8_t byte3, uint8_t num_bytes);
void toggle_midi_clock_source(void);

// HE Velocity Curve and Range System
typedef enum {
    VELOCITY_CURVE_SOFTEST = 0,
    VELOCITY_CURVE_SOFT,
    VELOCITY_CURVE_MEDIUM,
    VELOCITY_CURVE_HARD,
    VELOCITY_CURVE_HARDEST,
    VELOCITY_CURVE_COUNT
} velocity_curve_t;

extern velocity_curve_t he_velocity_curve;
extern uint8_t he_velocity_min;  // 1-127
extern uint8_t he_velocity_max;  // 1-127

uint8_t apply_he_velocity_curve(uint8_t travel_value);
void cycle_he_velocity_curve(bool forward);
void set_he_velocity_range(uint8_t min, uint8_t max);
uint8_t get_he_velocity_from_position(uint8_t row, uint8_t col);

// =============================================================================
// GAMING / JOYSTICK SYSTEM
// =============================================================================

// Gaming key mapping structure - maps a matrix position to a joystick control
typedef struct {
    uint8_t row;     // Matrix row (0-4)
    uint8_t col;     // Matrix column (0-13)
    uint8_t enabled; // 1 = enabled, 0 = disabled
} gaming_key_map_t;

// Analog calibration for joystick axes and triggers (separate for LS/RS/Triggers)
typedef struct {
    uint8_t min_travel_mm_x10;  // Minimum travel in 0.1mm units (e.g., 10 = 1.0mm)
    uint8_t max_travel_mm_x10;  // Maximum travel in 0.1mm units (e.g., 20 = 2.0mm)
} gaming_analog_config_t;

// Complete gaming settings structure for EEPROM
typedef struct {
    bool gaming_mode_enabled;              // Master enable/disable

    // Left stick mappings (Up, Down, Left, Right)
    gaming_key_map_t ls_up;
    gaming_key_map_t ls_down;
    gaming_key_map_t ls_left;
    gaming_key_map_t ls_right;

    // Right stick mappings (Up, Down, Left, Right)
    gaming_key_map_t rs_up;
    gaming_key_map_t rs_down;
    gaming_key_map_t rs_left;
    gaming_key_map_t rs_right;

    // Trigger mappings
    gaming_key_map_t lt;  // Left trigger
    gaming_key_map_t rt;  // Right trigger

    // Button mappings (16 buttons: Face, Shoulder, DPad, etc.)
    gaming_key_map_t buttons[16];

    // Analog calibration - separate for LS, RS, and Triggers
    gaming_analog_config_t ls_config;      // Left stick calibration
    gaming_analog_config_t rs_config;      // Right stick calibration
    gaming_analog_config_t trigger_config; // Trigger calibration

    uint16_t magic;  // 0x47A3 (GAME) for validation
} gaming_settings_t;

// EEPROM address for gaming settings (100 bytes allocated)
#define GAMING_SETTINGS_EEPROM_ADDR 65700
#define GAMING_SETTINGS_MAGIC 0x47A3

// Gaming mode global state
extern bool gaming_mode_active;
extern gaming_settings_t gaming_settings;

// Gaming system functions
void gaming_init(void);
void gaming_save_settings(void);
void gaming_load_settings(void);
void gaming_reset_settings(void);
void gaming_update_joystick(void);
//int16_t gaming_analog_to_axis(uint8_t row, uint8_t col, bool invert);
bool gaming_analog_to_trigger(uint8_t row, uint8_t col, int16_t* value);

// =============================================================================
// ARPEGGIATOR SYSTEM
// =============================================================================

// Maximum limits
#define MAX_ARP_NOTES 32           // Maximum simultaneous arp notes being gated
#define MAX_PRESET_NOTES 128       // Maximum notes per preset (smart EEPROM)
#define MAX_ARP_PRESETS 64         // Maximum presets (0-31: Arpeggiator, 32-63: Step Sequencer)
#define ARP_PRESET_NAME_LENGTH 16  // Max length for preset names

// Preset type enumeration
typedef enum {
    PRESET_TYPE_ARPEGGIATOR = 0,  // Arpeggiator: intervals relative to master note
    PRESET_TYPE_STEP_SEQUENCER,   // Step Sequencer: absolute MIDI notes
    PRESET_TYPE_COUNT
} preset_type_t;

// Arpeggiator mode types
typedef enum {
    ARP_MODE_SINGLE_NOTE = 0,     // One note at a time (classic arp)
    ARP_MODE_CHORD_BASIC,         // All notes at once per step
    ARP_MODE_CHORD_ADVANCED,      // Staggers notes evenly across step time
    ARP_MODE_COUNT
} arp_mode_t;

// Arpeggiator note in the tracking array (for gate timing)
typedef struct {
    uint8_t channel;
    uint8_t note;
    uint8_t velocity;
    uint32_t note_off_time;  // When to send note-off based on gate length
    bool active;
} arp_note_t;

// Individual note definition within a preset
typedef struct {
    uint16_t timing_64ths;     // When to trigger this note (0-255+ for multi-bar patterns)
    int8_t note_index;         // Semitone offset for arpeggiator (-11 to +11), or note index for step seq (0-11)
    int8_t octave_offset;      // Octave shift: can be negative for down octaves
    uint8_t raw_travel;        // Velocity as raw travel (0-255)
} arp_preset_note_t;

// Complete arpeggiator preset definition
typedef struct {
    char name[ARP_PRESET_NAME_LENGTH];  // Preset name for display
    uint8_t preset_type;                // PRESET_TYPE_ARPEGGIATOR or PRESET_TYPE_STEP_SEQUENCER
    uint8_t note_count;                 // Number of notes in this preset
    uint16_t pattern_length_64ths;      // Total pattern length in 64th notes (16=1 beat, 64=1 bar)
    uint8_t gate_length_percent;        // Gate length 0-100% (can be overridden by master)
    arp_preset_note_t notes[MAX_PRESET_NOTES];  // Note definitions
    uint16_t magic;                     // 0xA89F for validation
} arp_preset_t;

// Arpeggiator runtime state
typedef struct {
    bool active;                        // Is arp currently running
    bool sync_mode;                     // Sync to BPM beat boundaries
    bool latch_mode;                    // Continue after keys released (double-tap)
    arp_mode_t mode;                    // Single note / Chord basic / Chord advanced
    uint8_t current_preset_id;          // Which preset is active
    uint32_t next_note_time;            // When to play next note
    uint16_t current_position_64ths;    // Current position in pattern (0-pattern_length)
    uint8_t current_note_in_chord;      // For chord advanced mode: which note of chord
    uint8_t subdivision_override;       // 0=use preset timing, else override subdivision
    uint8_t master_gate_override;       // 0=use preset gate, else override (1-100%)
    uint32_t pattern_start_time;        // When current pattern loop started
    uint32_t last_tap_time;             // For double-tap detection
    bool key_held;                      // Is arp button physically held
} arp_state_t;

// EEPROM storage structure (for user presets)
#define ARP_EEPROM_ADDR 65800  // Starting address for arpeggiator/sequencer presets
#define ARP_PRESET_MAGIC 0xA89F

// Preset slot definitions
#define ARP_FACTORY_START 0         // Factory arpeggiator presets: 0-7
#define ARP_FACTORY_END 7
#define ARP_USER_START 8            // User arpeggiator presets: 8-31
#define ARP_USER_END 31
#define SEQ_FACTORY_START 32        // Factory step sequencer presets: 32-39
#define SEQ_FACTORY_END 39
#define SEQ_USER_START 40           // User step sequencer presets: 40-63
#define SEQ_USER_END 63

// Global arpeggiator state
extern arp_note_t arp_notes[MAX_ARP_NOTES];
extern uint8_t arp_note_count;
extern arp_state_t arp_state;
extern arp_preset_t arp_presets[MAX_ARP_PRESETS];
extern uint8_t arp_preset_count;

// Arpeggiator functions
void arp_init(void);
void arp_update(void);
void arp_start(uint8_t preset_id);
void arp_stop(void);
void arp_toggle_sync_mode(void);
void arp_next_preset(void);
void arp_prev_preset(void);
void arp_handle_button_press(void);
void arp_handle_button_release(void);
void arp_set_master_gate(uint8_t gate_percent);
void arp_set_mode(arp_mode_t mode);

// Phase 3: EEPROM and preset management functions
bool arp_validate_preset(const arp_preset_t *preset);
bool arp_save_preset_to_eeprom(uint8_t preset_id);
bool arp_load_preset_from_eeprom(uint8_t preset_id);
void arp_load_all_user_presets(void);
bool arp_clear_preset(uint8_t preset_id);
bool arp_copy_preset(uint8_t source_id, uint8_t dest_id);
void arp_reset_all_user_presets(void);

// Internal helper functions
void add_arp_note(uint8_t channel, uint8_t note, uint8_t velocity, uint32_t note_off_time);
void remove_arp_note(uint8_t channel, uint8_t note);
void process_arp_note_offs(void);
void midi_send_noteon_arp(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel);
void midi_send_noteoff_arp(uint8_t channel, uint8_t note, uint8_t velocity);

#endif // ORTHOMIDI5X14_H

