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
// ARPEGGIATOR & STEP SEQUENCER KEYCODES (0xCD00-0xCDFF)
// =============================================================================

// ARPEGGIATOR SECTION (0xCD00-0xCD7F)

// Arpeggiator Control/Transport (0xCD00-0xCD0F)
#define ARP_PLAY            0xCD00  // Play current selected arp (hold/double-tap for latch)
#define ARP_NEXT_PRESET     0xCD01  // Navigate to next arp preset
#define ARP_PREV_PRESET     0xCD02  // Navigate to previous arp preset
#define ARP_SYNC_TOGGLE     0xCD03  // Toggle sync mode (BPM-locked vs free-running)
#define ARP_GATE_UP         0xCD04  // Increase master gate length (+10%)
#define ARP_GATE_DOWN       0xCD05  // Decrease master gate length (-10%)
#define ARP_GATE_RESET      0xCD06  // Reset gate to preset default
#define ARP_RESET_TO_DEFAULT 0xCD07 // Reset all overrides to preset defaults

// Arpeggiator Fixed Gate Percentages (0xCD08-0xCD0F, 0xCD1A-0xCD1B)
#define ARP_SET_GATE_100    0xCD08  // Set gate to 100%
#define ARP_SET_GATE_90     0xCD09  // Set gate to 90%
#define ARP_SET_GATE_80     0xCD0A  // Set gate to 80%
#define ARP_SET_GATE_70     0xCD0B  // Set gate to 70%
#define ARP_SET_GATE_60     0xCD0C  // Set gate to 60%
#define ARP_SET_GATE_50     0xCD0D  // Set gate to 50%
#define ARP_SET_GATE_40     0xCD0E  // Set gate to 40%
#define ARP_SET_GATE_30     0xCD0F  // Set gate to 30%
#define ARP_SET_GATE_20     0xCD1A  // Set gate to 20%
#define ARP_SET_GATE_10     0xCD1B  // Set gate to 10%

// Arpeggiator Pattern Rate Overrides (0xCD10-0xCD19)
#define ARP_RATE_QUARTER        0xCD10  // Quarter note straight
#define ARP_RATE_QUARTER_DOT    0xCD11  // Quarter note dotted
#define ARP_RATE_QUARTER_TRIP   0xCD12  // Quarter note triplet
#define ARP_RATE_EIGHTH         0xCD13  // Eighth note straight
#define ARP_RATE_EIGHTH_DOT     0xCD14  // Eighth note dotted
#define ARP_RATE_EIGHTH_TRIP    0xCD15  // Eighth note triplet
#define ARP_RATE_SIXTEENTH      0xCD16  // Sixteenth note straight
#define ARP_RATE_SIXTEENTH_DOT  0xCD17  // Sixteenth note dotted
#define ARP_RATE_SIXTEENTH_TRIP 0xCD18  // Sixteenth note triplet
#define ARP_RATE_RESET          0xCD19  // Reset to preset's default rate

// Arpeggiator Modes (0xCD20-0xCD2F)
#define ARP_MODE_SINGLE         0xCD20  // Single note mode (classic arp)
#define ARP_MODE_CHORD_BASIC    0xCD21  // Chord basic mode (all notes per step)
#define ARP_MODE_CHORD_ADVANCED 0xCD22  // Chord advanced mode (staggered notes)

// Arpeggiator Gate Up/Down Variants (0xCD23-0xCD2C, 0xCD70-0xCD79)
#define ARP_GATE_UP_1       0xCD23  // Increase gate by 1%
#define ARP_GATE_UP_2       0xCD24  // Increase gate by 2%
#define ARP_GATE_UP_3       0xCD25  // Increase gate by 3%
#define ARP_GATE_UP_4       0xCD26  // Increase gate by 4%
#define ARP_GATE_UP_5       0xCD27  // Increase gate by 5%
#define ARP_GATE_UP_6       0xCD28  // Increase gate by 6%
#define ARP_GATE_UP_7       0xCD29  // Increase gate by 7%
#define ARP_GATE_UP_8       0xCD2A  // Increase gate by 8%
#define ARP_GATE_UP_9       0xCD2B  // Increase gate by 9%
#define ARP_GATE_UP_10      0xCD2C  // Increase gate by 10%

#define ARP_GATE_DOWN_1     0xCD70  // Decrease gate by 1%
#define ARP_GATE_DOWN_2     0xCD71  // Decrease gate by 2%
#define ARP_GATE_DOWN_3     0xCD72  // Decrease gate by 3%
#define ARP_GATE_DOWN_4     0xCD73  // Decrease gate by 4%
#define ARP_GATE_DOWN_5     0xCD74  // Decrease gate by 5%
#define ARP_GATE_DOWN_6     0xCD75  // Decrease gate by 6%
#define ARP_GATE_DOWN_7     0xCD76  // Decrease gate by 7%
#define ARP_GATE_DOWN_8     0xCD77  // Decrease gate by 8%
#define ARP_GATE_DOWN_9     0xCD78  // Decrease gate by 9%
#define ARP_GATE_DOWN_10    0xCD79  // Decrease gate by 10%

// Direct Arpeggiator Preset Selection (0xCD30-0xCD6F) - 64 presets
#define ARP_PRESET_BASE         0xCD30  // Base address for arp presets (0xCD30 + preset_id)

// STEP SEQUENCER SECTION (0xCD80-0xCDFF)

// Step Sequencer Control/Transport (0xCD80-0xCD8F)
#define SEQ_PLAY            0xCD80  // Play current selected sequencer (toggle on/off)
#define SEQ_STOP_ALL        0xCD81  // Stop all playing sequencers
#define SEQ_NEXT_PRESET     0xCD82  // Navigate to next seq preset
#define SEQ_PREV_PRESET     0xCD83  // Navigate to previous seq preset
#define SEQ_SYNC_TOGGLE     0xCD84  // Toggle sync mode (BPM-locked vs free-running)
#define SEQ_GATE_UP         0xCD85  // Increase master gate length (+10%)
#define SEQ_GATE_DOWN       0xCD86  // Decrease master gate length (-10%)
#define SEQ_GATE_RESET      0xCD87  // Reset gate to preset default
#define SEQ_RESET_TO_DEFAULT 0xCD88 // Reset all overrides to preset defaults

// Step Sequencer Fixed Gate Percentages (0xCD89-0xCD8F, 0xCDE0-0xCDE2)
#define SEQ_SET_GATE_100    0xCD89  // Set gate to 100%
#define SEQ_SET_GATE_90     0xCD8A  // Set gate to 90%
#define SEQ_SET_GATE_80     0xCD8B  // Set gate to 80%
#define SEQ_SET_GATE_70     0xCD8C  // Set gate to 70%
#define SEQ_SET_GATE_60     0xCD8D  // Set gate to 60%
#define SEQ_SET_GATE_50     0xCD8E  // Set gate to 50%
#define SEQ_SET_GATE_40     0xCD8F  // Set gate to 40%
#define SEQ_SET_GATE_30     0xCDE0  // Set gate to 30%
#define SEQ_SET_GATE_20     0xCDE1  // Set gate to 20%
#define SEQ_SET_GATE_10     0xCDE2  // Set gate to 10%

// Step Sequencer Pattern Rate Overrides (0xCD90-0xCD99)
#define SEQ_RATE_QUARTER        0xCD90  // Quarter note straight
#define SEQ_RATE_QUARTER_DOT    0xCD91  // Quarter note dotted
#define SEQ_RATE_QUARTER_TRIP   0xCD92  // Quarter note triplet
#define SEQ_RATE_EIGHTH         0xCD93  // Eighth note straight
#define SEQ_RATE_EIGHTH_DOT     0xCD94  // Eighth note dotted
#define SEQ_RATE_EIGHTH_TRIP    0xCD95  // Eighth note triplet
#define SEQ_RATE_SIXTEENTH      0xCD96  // Sixteenth note straight
#define SEQ_RATE_SIXTEENTH_DOT  0xCD97  // Sixteenth note dotted
#define SEQ_RATE_SIXTEENTH_TRIP 0xCD98  // Sixteenth note triplet
#define SEQ_RATE_RESET          0xCD99  // Reset to preset's default rate

// Direct Step Sequencer Preset Selection (0xCDA0-0xCDDF) - 64 presets
#define SEQ_PRESET_BASE         0xCDA0  // Base address for seq presets (0xCDA0 + preset_id)

// Step Sequencer Gate Up/Down Variants (0xCDE3-0xCDF6)
#define SEQ_GATE_UP_1       0xCDE3  // Increase gate by 1%
#define SEQ_GATE_UP_2       0xCDE4  // Increase gate by 2%
#define SEQ_GATE_UP_3       0xCDE5  // Increase gate by 3%
#define SEQ_GATE_UP_4       0xCDE6  // Increase gate by 4%
#define SEQ_GATE_UP_5       0xCDE7  // Increase gate by 5%
#define SEQ_GATE_UP_6       0xCDE8  // Increase gate by 6%
#define SEQ_GATE_UP_7       0xCDE9  // Increase gate by 7%
#define SEQ_GATE_UP_8       0xCDEA  // Increase gate by 8%
#define SEQ_GATE_UP_9       0xCDEB  // Increase gate by 9%
#define SEQ_GATE_UP_10      0xCDEC  // Increase gate by 10%

#define SEQ_GATE_DOWN_1     0xCDED  // Decrease gate by 1%
#define SEQ_GATE_DOWN_2     0xCDEE  // Decrease gate by 2%
#define SEQ_GATE_DOWN_3     0xCDEF  // Decrease gate by 3%
#define SEQ_GATE_DOWN_4     0xCDF0  // Decrease gate by 4%
#define SEQ_GATE_DOWN_5     0xCDF1  // Decrease gate by 5%
#define SEQ_GATE_DOWN_6     0xCDF2  // Decrease gate by 6%
#define SEQ_GATE_DOWN_7     0xCDF3  // Decrease gate by 7%
#define SEQ_GATE_DOWN_8     0xCDF4  // Decrease gate by 8%
#define SEQ_GATE_DOWN_9     0xCDF5  // Decrease gate by 9%
#define SEQ_GATE_DOWN_10    0xCDF6  // Decrease gate by 10%

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
#define MAX_PRESET_NOTES 128       // Maximum notes per preset in RAM
#define MAX_ARP_PRESETS 64         // Total preset slots (0-47: Factory PROGMEM, 48-63: User EEPROM)
#define NUM_FACTORY_PRESETS 48     // Factory presets (0-47) stored in PROGMEM
#define NUM_USER_PRESETS 16        // User presets (48-63) stored in EEPROM
#define USER_PRESET_START 48       // First user preset slot

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

// Complete arpeggiator preset definition (OPTIMIZED: 392 bytes, was 663)
typedef struct {
    uint8_t preset_type;                // PRESET_TYPE_ARPEGGIATOR or PRESET_TYPE_STEP_SEQUENCER
    uint8_t note_count;                 // Number of notes in this preset (1-128)
    uint8_t pattern_length_16ths;       // Total pattern length in 16th notes (1-127 = max 8 bars)
    uint8_t gate_length_percent;        // Gate length 0-100% (can be overridden by master)
    uint8_t timing_mode;                // Timing mode flags (TIMING_MODE_STRAIGHT/TRIPLET/DOTTED)
    uint8_t note_value;                 // Base note value (NOTE_VALUE_QUARTER/EIGHTH/SIXTEENTH)
    arp_preset_note_t notes[MAX_PRESET_NOTES];  // Note definitions (3 bytes each)
    uint16_t magic;                     // 0xA89F for validation
} arp_preset_t;  // Total: 8 + (128 × 3) = 392 bytes (was 663 bytes)

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
#define ARP_EEPROM_ADDR 65800       // Starting address for user presets in EEPROM
#define ARP_PRESET_MAGIC 0xA89F     // Magic number for preset validation
#define ARP_PRESET_HEADER_SIZE 8    // Header size (type, count, length, gate, timing_mode, note_value, magic)
#define ARP_MAX_PRESET_EEPROM_SIZE (ARP_PRESET_HEADER_SIZE + (MAX_PRESET_NOTES * 3))  // 8 + 384 = 392 bytes

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

// Efficient RAM storage: Only active presets loaded (was 64 × 392 = 25KB, now ~2KB)
extern arp_preset_t arp_active_preset;           // 1 slot for arpeggiator (~392 bytes)
extern arp_preset_t seq_active_presets[MAX_SEQ_SLOTS];  // 4 slots for sequencers (~1.5KB)
extern uint8_t arp_preset_count;  // Still track total count for NEXT/PREV navigation

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

// EEPROM and preset management functions
bool arp_validate_preset(const arp_preset_t *preset);
bool arp_save_preset_to_eeprom(uint8_t preset_id, const arp_preset_t *source);
bool arp_load_preset_from_eeprom(uint8_t preset_id, arp_preset_t *dest);
void arp_load_factory_preset(uint8_t preset_id, arp_preset_t *dest);
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

