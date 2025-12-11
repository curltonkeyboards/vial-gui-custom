// orthomidi5x14.h
#ifndef ORTHOMIDI5X14_H
#define ORTHOMIDI5X14_H

#include "quantum.h"

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
// ARPEGGIATOR & STEP SEQUENCER KEYCODES (0xEE00-0xEEFF)
// Moved from 0xCD00 to avoid overlap with HE Velocity Range (0xCCB5-0xEC74)
// =============================================================================

// ARPEGGIATOR SECTION (0xEE00-0xEE7F)

// Arpeggiator Control/Transport (0xEE00-0xEE0F)
#define ARP_PLAY            0xEE00  // Play current selected arp (hold/double-tap for latch)
#define ARP_NEXT_PRESET     0xEE01  // Navigate to next arp preset
#define ARP_PREV_PRESET     0xEE02  // Navigate to previous arp preset
#define ARP_SYNC_TOGGLE     0xEE03  // Toggle sync mode (BPM-locked vs free-running)
#define ARP_GATE_UP         0xEE04  // Increase master gate length (+10%)
#define ARP_GATE_DOWN       0xEE05  // Decrease master gate length (-10%)
#define ARP_GATE_RESET      0xEE06  // Reset gate to preset default
#define ARP_RESET_TO_DEFAULT 0xEE07 // Reset all overrides to preset defaults

// Arpeggiator Pattern Rate Overrides (0xEE10-0xEE1B)
#define ARP_RATE_QUARTER        0xEE10  // Quarter note straight
#define ARP_RATE_QUARTER_DOT    0xEE11  // Quarter note dotted
#define ARP_RATE_QUARTER_TRIP   0xEE12  // Quarter note triplet
#define ARP_RATE_EIGHTH         0xEE13  // Eighth note straight
#define ARP_RATE_EIGHTH_DOT     0xEE14  // Eighth note dotted
#define ARP_RATE_EIGHTH_TRIP    0xEE15  // Eighth note triplet
#define ARP_RATE_SIXTEENTH      0xEE16  // Sixteenth note straight
#define ARP_RATE_SIXTEENTH_DOT  0xEE17  // Sixteenth note dotted
#define ARP_RATE_SIXTEENTH_TRIP 0xEE18  // Sixteenth note triplet
#define ARP_RATE_RESET          0xEE19  // Reset to preset's default rate

// Arpeggiator Modes (0xEE20-0xEE2F)
#define ARP_MODE_SINGLE         0xEE20  // Single note mode (classic arp)
#define ARP_MODE_CHORD_BASIC    0xEE21  // Chord basic mode (all notes per step)
#define ARP_MODE_CHORD_ADVANCED 0xEE22  // Chord advanced mode (staggered notes)

// Direct Arpeggiator Preset Selection (0xEE30-0xEE73) - 68 presets (0-67)
#define ARP_PRESET_BASE         0xEE30  // Base address for arp presets (0xEE30 + preset_id)

// STEP SEQUENCER SECTION (0xEE80-0xEEFF)

// Step Sequencer Control/Transport (0xEE80-0xEE8F)
#define SEQ_PLAY            0xEE80  // Play current selected sequencer (toggle on/off)
#define SEQ_STOP_ALL        0xEE81  // Stop all playing sequencers
#define SEQ_NEXT_PRESET     0xEE82  // Navigate to next seq preset
#define SEQ_PREV_PRESET     0xEE83  // Navigate to previous seq preset
#define SEQ_SYNC_TOGGLE     0xEE84  // Toggle sync mode (BPM-locked vs free-running)
#define SEQ_GATE_UP         0xEE85  // Increase master gate length (+10%)
#define SEQ_GATE_DOWN       0xEE86  // Decrease master gate length (-10%)
#define SEQ_GATE_RESET      0xEE87  // Reset gate to preset default
#define SEQ_RESET_TO_DEFAULT 0xEE88 // Reset all overrides to preset defaults

// Step Sequencer Pattern Rate Overrides (0xEE90-0xEE9B)
#define SEQ_RATE_QUARTER        0xEE90  // Quarter note straight
#define SEQ_RATE_QUARTER_DOT    0xEE91  // Quarter note dotted
#define SEQ_RATE_QUARTER_TRIP   0xEE92  // Quarter note triplet
#define SEQ_RATE_EIGHTH         0xEE93  // Eighth note straight
#define SEQ_RATE_EIGHTH_DOT     0xEE94  // Eighth note dotted
#define SEQ_RATE_EIGHTH_TRIP    0xEE95  // Eighth note triplet
#define SEQ_RATE_SIXTEENTH      0xEE96  // Sixteenth note straight
#define SEQ_RATE_SIXTEENTH_DOT  0xEE97  // Sixteenth note dotted
#define SEQ_RATE_SIXTEENTH_TRIP 0xEE98  // Sixteenth note triplet
#define SEQ_RATE_RESET          0xEE99  // Reset to preset's default rate

// Direct Step Sequencer Preset Selection (0xEEA0-0xEEE3) - 68 presets (maps to firmware IDs 68-135)
#define SEQ_PRESET_BASE         0xEEA0  // Base address for seq presets (0xEEA0 + offset, maps to firmware ID 68+offset)

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
#define GAMING_SETTINGS_EEPROM_ADDR 67840
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
#define MAX_ARP_NOTES 32           // Maximum simultaneous arp notes being gated (for gate timing)
#define MAX_ARP_PRESET_NOTES 64    // Maximum notes in an arpeggiator preset
#define MAX_SEQ_PRESET_NOTES 128   // Maximum notes in a step sequencer preset
#define NUM_FACTORY_ARP_PRESETS 48 // Factory arpeggiator presets (0-47) in PROGMEM
#define NUM_FACTORY_SEQ_PRESETS 48 // Factory sequencer presets (0-47) in PROGMEM
#define NUM_USER_ARP_PRESETS 20    // User arpeggiator presets (0-19) in EEPROM
#define NUM_USER_SEQ_PRESETS 20    // User sequencer presets (0-19) in EEPROM

// Preset ID ranges
#define USER_ARP_PRESET_START 48   // First user arpeggiator preset ID (48-67)
#define MAX_ARP_PRESETS (USER_ARP_PRESET_START + NUM_USER_ARP_PRESETS)  // 48 + 20 = 68
#define USER_SEQ_PRESET_START 116  // First user sequencer preset ID (116-135)
#define MAX_SEQ_PRESETS (USER_SEQ_PRESET_START + NUM_USER_SEQ_PRESETS)  // 116 + 20 = 136

// Preset type enumeration
typedef enum {
    PRESET_TYPE_ARPEGGIATOR = 0,  // Arpeggiator: intervals relative to master note
    PRESET_TYPE_STEP_SEQUENCER,   // Step Sequencer: absolute MIDI notes
    PRESET_TYPE_COUNT
} preset_type_t;

// Timing mode flags (for triplet/dotted note support)
#define TIMING_MODE_STRAIGHT 0x00  // Normal timing
#define TIMING_MODE_TRIPLET  0x01  // Triplet timing (×2/3)
#define TIMING_MODE_DOTTED   0x02  // Dotted timing (×3/2)
#define TIMING_MODE_MASK     0x03  // Mask for timing mode bits

// Note value for timing modes (sets base subdivision)
typedef enum {
    NOTE_VALUE_QUARTER = 0,        // Quarter notes (4 16ths)
    NOTE_VALUE_EIGHTH,             // Eighth notes (2 16ths)
    NOTE_VALUE_SIXTEENTH,          // Sixteenth notes (1 16th)
    NOTE_VALUE_COUNT
} note_value_t;

// Arpeggiator mode types (internal enum values)
typedef enum {
    ARPMODE_SINGLE_NOTE = 0,      // One note at a time (classic arp)
    ARPMODE_CHORD_BASIC,          // All notes at once per step
    ARPMODE_CHORD_ADVANCED,       // Staggers notes evenly across step time
    ARPMODE_COUNT
} arp_mode_t;

// Arpeggiator note in the tracking array (for gate timing)
typedef struct {
    uint8_t channel;
    uint8_t note;
    uint8_t velocity;
    uint32_t note_off_time;  // When to send note-off based on gate length
    bool active;
} arp_note_t;

// Individual note definition within a preset (OPTIMIZED: 3 bytes per note, was 5)
typedef struct {
    // Byte 0-1: Packed timing and velocity
    uint16_t packed_timing_vel;
      // bits 0-6:   timing_16ths (0-127 = max 8 bars)
      // bits 7-13:  velocity (0-127)
      // bit 14:     interval_sign (arpeggiator only: 0=positive, 1=negative)
      // bit 15:     reserved

    // Byte 2: Packed note/interval and octave
    uint8_t note_octave;
      // bits 0-3:   note_index (0-11) or interval magnitude (0-11 for arp)
      // bits 4-7:   octave_offset (signed -8 to +7)
} arp_preset_note_t;  // 3 bytes total (was 5 bytes)

// Arpeggiator preset definition (200 bytes for 64 notes)
typedef struct {
    uint8_t preset_type;                // Always PRESET_TYPE_ARPEGGIATOR
    uint8_t note_count;                 // Number of notes in this preset (1-64)
    uint8_t pattern_length_16ths;       // Total pattern length in 16th notes (1-127 = max 8 bars)
    uint8_t gate_length_percent;        // Gate length 0-100% (can be overridden by master)
    uint8_t timing_mode;                // Timing mode flags (TIMING_MODE_STRAIGHT/TRIPLET/DOTTED)
    uint8_t note_value;                 // Base note value (NOTE_VALUE_QUARTER/EIGHTH/SIXTEENTH)
    arp_preset_note_t notes[MAX_ARP_PRESET_NOTES];  // Note definitions (3 bytes each × 64)
    uint16_t magic;                     // 0xA89F for validation
} arp_preset_t;  // Total: 8 + (64 × 3) = 200 bytes

// Step Sequencer preset definition (392 bytes for 128 notes)
typedef struct {
    uint8_t preset_type;                // Always PRESET_TYPE_STEP_SEQUENCER
    uint8_t note_count;                 // Number of notes in this preset (1-128)
    uint8_t pattern_length_16ths;       // Total pattern length in 16th notes (1-127 = max 8 bars)
    uint8_t gate_length_percent;        // Gate length 0-100% (can be overridden by master)
    uint8_t timing_mode;                // Timing mode flags (TIMING_MODE_STRAIGHT/TRIPLET/DOTTED)
    uint8_t note_value;                 // Base note value (NOTE_VALUE_QUARTER/EIGHTH/SIXTEENTH)
    arp_preset_note_t notes[MAX_SEQ_PRESET_NOTES];  // Note definitions (3 bytes each × 128)
    uint16_t magic;                     // 0xA89F for validation
} seq_preset_t;  // Total: 8 + (128 × 3) = 392 bytes

// Arpeggiator runtime state
typedef struct {
    bool active;                        // Is arp currently running
    bool sync_mode;                     // Sync to BPM beat boundaries
    bool latch_mode;                    // Continue after keys released (double-tap)
    arp_mode_t mode;                    // Single note / Chord basic / Chord advanced
    uint8_t current_preset_id;          // Which preset is selected (for NEXT/PREV)
    uint8_t loaded_preset_id;           // Which preset is currently loaded in RAM
    uint32_t next_note_time;            // When to play next note
    uint16_t current_position_16ths;    // Current position in pattern (0-pattern_length)
    uint8_t current_note_in_chord;      // For chord advanced mode: which note of chord
    uint8_t rate_override;              // 0=use preset, else override (NOTE_VALUE_* | TIMING_MODE_*)
    uint8_t master_gate_override;       // 0=use preset gate, else override (1-100%)
    uint32_t pattern_start_time;        // When current pattern loop started
    uint32_t last_tap_time;             // For double-tap detection
    bool key_held;                      // Is arp button physically held
} arp_state_t;

// Step Sequencer runtime state (per slot)
#define MAX_SEQ_SLOTS 4
typedef struct {
    bool active;                        // Is this seq slot currently running
    bool sync_mode;                     // Sync to BPM beat boundaries
    uint8_t current_preset_id;          // Which preset is selected (for NEXT/PREV)
    uint8_t loaded_preset_id;           // Which preset is currently loaded in RAM
    uint32_t next_note_time;            // When to play next note
    uint16_t current_position_16ths;    // Current position in pattern (0-pattern_length)
    uint8_t rate_override;              // 0=use preset, else override (NOTE_VALUE_* | TIMING_MODE_*)
    uint8_t master_gate_override;       // 0=use preset gate, else override (1-100%)
    uint32_t pattern_start_time;        // When current pattern loop started
} seq_state_t;

// EEPROM storage structure (for user presets only)
#define ARP_EEPROM_ADDR 56000       // Starting address for user arp presets in EEPROM (20 slots)
#define SEQ_EEPROM_ADDR 60000       // Starting address for user seq presets in EEPROM (20 slots)
#define ARP_PRESET_MAGIC 0xA89F     // Magic number for preset validation
#define ARP_PRESET_HEADER_SIZE 8    // Header size (type, count, length, gate, timing_mode, note_value, magic)
#define ARP_PRESET_SIZE (ARP_PRESET_HEADER_SIZE + (MAX_ARP_PRESET_NOTES * 3))  // 8 + 192 = 200 bytes
#define SEQ_PRESET_SIZE (ARP_PRESET_HEADER_SIZE + (MAX_SEQ_PRESET_NOTES * 3))  // 8 + 384 = 392 bytes

// Helper macros for unpacking note data
#define NOTE_GET_TIMING(packed)      ((packed) & 0x7F)                        // bits 0-6
#define NOTE_GET_VELOCITY(packed)    (((packed) >> 7) & 0x7F)                 // bits 7-13
#define NOTE_GET_SIGN(packed)        (((packed) >> 14) & 0x01)                // bit 14 (arp only)
#define NOTE_GET_NOTE(octave_byte)   ((octave_byte) & 0x0F)                   // bits 0-3
#define NOTE_GET_OCTAVE(octave_byte) ((int8_t)((octave_byte) << 4) >> 4)      // bits 4-7 (signed)

// Helper macros for packing note data
#define NOTE_PACK_TIMING_VEL(timing, vel, sign) (((timing) & 0x7F) | (((vel) & 0x7F) << 7) | (((sign) & 0x01) << 14))
#define NOTE_PACK_NOTE_OCTAVE(note, octave)     (((note) & 0x0F) | (((octave) & 0x0F) << 4))

// Global arpeggiator state
extern arp_note_t arp_notes[MAX_ARP_NOTES];
extern uint8_t arp_note_count;
extern arp_state_t arp_state;
extern seq_state_t seq_state[MAX_SEQ_SLOTS];

// Efficient RAM storage: Only active presets loaded
extern arp_preset_t arp_active_preset;           // 1 slot for arpeggiator (200 bytes)
extern seq_preset_t seq_active_presets[MAX_SEQ_SLOTS];  // 4 slots for sequencers (4 × 392 = 1568 bytes)

// Arpeggiator functions
void arp_init(void);
void arp_update(void);
void seq_update(void);  // Update all active sequencer slots
void arp_start(uint8_t preset_id);
void arp_stop(void);
void seq_start(uint8_t preset_id);  // Start sequencer in available slot
void seq_stop(uint8_t slot);        // Stop specific sequencer slot
void seq_stop_all(void);            // Stop all sequencers
void arp_toggle_sync_mode(void);
void seq_toggle_sync_mode(void);
void arp_next_preset(void);
void arp_prev_preset(void);
void seq_next_preset(void);
void seq_prev_preset(void);
void arp_handle_button_press(void);
void arp_handle_button_release(void);
void arp_set_master_gate(uint8_t gate_percent);
void seq_set_master_gate(uint8_t gate_percent);
void arp_set_mode(arp_mode_t mode);
void arp_set_rate_override(uint8_t note_value, uint8_t timing_mode);
void seq_set_rate_override(uint8_t note_value, uint8_t timing_mode);
void arp_reset_overrides(void);
void seq_reset_overrides(void);

// Lazy-loading preset management
bool arp_load_preset_into_slot(uint8_t preset_id);  // Load preset into arp RAM slot
bool seq_load_preset_into_slot(uint8_t preset_id, uint8_t slot);  // Load preset into seq RAM slot
int8_t seq_find_available_slot(void);  // Find available seq slot (-1 if none)

// EEPROM and preset management functions - ARPEGGIATOR
bool arp_validate_preset(const arp_preset_t *preset);
bool arp_save_preset_to_eeprom(uint8_t preset_id, const arp_preset_t *source);
bool arp_load_preset_from_eeprom(uint8_t preset_id, arp_preset_t *dest);
void arp_load_factory_preset(uint8_t preset_id, arp_preset_t *dest);
bool arp_clear_preset(uint8_t preset_id);
bool arp_copy_preset(uint8_t source_id, uint8_t dest_id);
void arp_reset_all_user_presets(void);

// EEPROM and preset management functions - STEP SEQUENCER
bool seq_validate_preset(const seq_preset_t *preset);
bool seq_save_preset_to_eeprom(uint8_t preset_id, const seq_preset_t *source);
bool seq_load_preset_from_eeprom(uint8_t preset_id, seq_preset_t *dest);
void seq_load_factory_preset(uint8_t preset_id, seq_preset_t *dest);
bool seq_clear_preset(uint8_t preset_id);
bool seq_copy_preset(uint8_t source_id, uint8_t dest_id);
void seq_reset_all_user_presets(void);

// Internal helper functions
void add_arp_note(uint8_t channel, uint8_t note, uint8_t velocity, uint32_t note_off_time);
void remove_arp_note(uint8_t channel, uint8_t note);
void process_arp_note_offs(void);
void midi_send_noteon_arp(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel);
void midi_send_noteoff_arp(uint8_t channel, uint8_t note, uint8_t velocity);

#endif // ORTHOMIDI5X14_H

