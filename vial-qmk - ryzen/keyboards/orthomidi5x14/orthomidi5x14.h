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
extern velocity_curve_t keysplit_he_velocity_curve;
extern uint8_t keysplit_he_velocity_min;  // 1-127
extern uint8_t keysplit_he_velocity_max;  // 1-127
extern velocity_curve_t triplesplit_he_velocity_curve;
extern uint8_t triplesplit_he_velocity_min;  // 1-127
extern uint8_t triplesplit_he_velocity_max;  // 1-127

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
#define ARP_GATE_RESET      0xEE04  // Reset gate to preset default
#define ARP_RESET_TO_DEFAULT 0xEE05 // Reset all overrides to preset defaults

// Arpeggiator Gate Up keycodes (0xEE06-0xEE0F) - Increase gate by 1-10%
#define ARP_GATE_1_UP       0xEE06  // Increase master gate length (+1%)
#define ARP_GATE_2_UP       0xEE07  // Increase master gate length (+2%)
#define ARP_GATE_3_UP       0xEE08  // Increase master gate length (+3%)
#define ARP_GATE_4_UP       0xEE09  // Increase master gate length (+4%)
#define ARP_GATE_5_UP       0xEE0A  // Increase master gate length (+5%)
#define ARP_GATE_6_UP       0xEE0B  // Increase master gate length (+6%)
#define ARP_GATE_7_UP       0xEE0C  // Increase master gate length (+7%)
#define ARP_GATE_8_UP       0xEE0D  // Increase master gate length (+8%)
#define ARP_GATE_9_UP       0xEE0E  // Increase master gate length (+9%)
#define ARP_GATE_10_UP      0xEE0F  // Increase master gate length (+10%)

// Arpeggiator Gate Down keycodes (0xEE10-0xEE19) - Decrease gate by 1-10%
#define ARP_GATE_1_DOWN     0xEE10  // Decrease master gate length (-1%)
#define ARP_GATE_2_DOWN     0xEE11  // Decrease master gate length (-2%)
#define ARP_GATE_3_DOWN     0xEE12  // Decrease master gate length (-3%)
#define ARP_GATE_4_DOWN     0xEE13  // Decrease master gate length (-4%)
#define ARP_GATE_5_DOWN     0xEE14  // Decrease master gate length (-5%)
#define ARP_GATE_6_DOWN     0xEE15  // Decrease master gate length (-6%)
#define ARP_GATE_7_DOWN     0xEE16  // Decrease master gate length (-7%)
#define ARP_GATE_8_DOWN     0xEE17  // Decrease master gate length (-8%)
#define ARP_GATE_9_DOWN     0xEE18  // Decrease master gate length (-9%)
#define ARP_GATE_10_DOWN    0xEE19  // Decrease master gate length (-10%)

// Arpeggiator Pattern Rate Overrides (0xEE1A-0xEE23)
#define ARP_RATE_QUARTER        0xEE1A  // Quarter note straight
#define ARP_RATE_QUARTER_DOT    0xEE1B  // Quarter note dotted
#define ARP_RATE_QUARTER_TRIP   0xEE1C  // Quarter note triplet
#define ARP_RATE_EIGHTH         0xEE1D  // Eighth note straight
#define ARP_RATE_EIGHTH_DOT     0xEE1E  // Eighth note dotted
#define ARP_RATE_EIGHTH_TRIP    0xEE1F  // Eighth note triplet
#define ARP_RATE_SIXTEENTH      0xEE20  // Sixteenth note straight
#define ARP_RATE_SIXTEENTH_DOT  0xEE21  // Sixteenth note dotted
#define ARP_RATE_SIXTEENTH_TRIP 0xEE22  // Sixteenth note triplet
#define ARP_RATE_RESET          0xEE23  // Reset to preset's default rate

// Arpeggiator Modes (0xEE24-0xEE26)
#define ARP_MODE_SINGLE         0xEE24  // Single note mode (classic arp)
#define ARP_MODE_CHORD_BASIC    0xEE25  // Chord basic mode (all notes per step)
#define ARP_MODE_CHORD_ADVANCED 0xEE26  // Chord advanced mode (staggered notes)

// Direct Arpeggiator Preset Selection (0xEE30-0xEE73) - 68 presets (0-67)
#define ARP_PRESET_BASE         0xEE30  // Base address for arp presets (0xEE30 + preset_id)

// STEP SEQUENCER SECTION (0xEE80-0xEEFF)

// Step Sequencer Control/Transport (0xEE80-0xEE8F)
#define SEQ_PLAY            0xEE80  // Play current selected sequencer (toggle on/off)
#define SEQ_STOP_ALL        0xEE81  // Stop all playing sequencers
#define SEQ_NEXT_PRESET     0xEE82  // Navigate to next seq preset
#define SEQ_PREV_PRESET     0xEE83  // Navigate to previous seq preset
#define SEQ_SYNC_TOGGLE     0xEE84  // Toggle sync mode (BPM-locked vs free-running)
#define SEQ_GATE_RESET      0xEE85  // Reset gate to preset default
#define SEQ_RESET_TO_DEFAULT 0xEE86 // Reset all overrides to preset defaults

// Step Sequencer Gate Up keycodes (0xEE87-0xEE90) - Increase gate by 1-10%
#define SEQ_GATE_1_UP       0xEE87  // Increase master gate length (+1%)
#define SEQ_GATE_2_UP       0xEE88  // Increase master gate length (+2%)
#define SEQ_GATE_3_UP       0xEE89  // Increase master gate length (+3%)
#define SEQ_GATE_4_UP       0xEE8A  // Increase master gate length (+4%)
#define SEQ_GATE_5_UP       0xEE8B  // Increase master gate length (+5%)
#define SEQ_GATE_6_UP       0xEE8C  // Increase master gate length (+6%)
#define SEQ_GATE_7_UP       0xEE8D  // Increase master gate length (+7%)
#define SEQ_GATE_8_UP       0xEE8E  // Increase master gate length (+8%)
#define SEQ_GATE_9_UP       0xEE8F  // Increase master gate length (+9%)
#define SEQ_GATE_10_UP      0xEE90  // Increase master gate length (+10%)

// Step Sequencer Gate Down keycodes (0xEE91-0xEE9A) - Decrease gate by 1-10%
#define SEQ_GATE_1_DOWN     0xEE91  // Decrease master gate length (-1%)
#define SEQ_GATE_2_DOWN     0xEE92  // Decrease master gate length (-2%)
#define SEQ_GATE_3_DOWN     0xEE93  // Decrease master gate length (-3%)
#define SEQ_GATE_4_DOWN     0xEE94  // Decrease master gate length (-4%)
#define SEQ_GATE_5_DOWN     0xEE95  // Decrease master gate length (-5%)
#define SEQ_GATE_6_DOWN     0xEE96  // Decrease master gate length (-6%)
#define SEQ_GATE_7_DOWN     0xEE97  // Decrease master gate length (-7%)
#define SEQ_GATE_8_DOWN     0xEE98  // Decrease master gate length (-8%)
#define SEQ_GATE_9_DOWN     0xEE99  // Decrease master gate length (-9%)
#define SEQ_GATE_10_DOWN    0xEE9A  // Decrease master gate length (-10%)

// Step Sequencer Pattern Rate Overrides (0xEE9B-0xEEA4)
#define SEQ_RATE_QUARTER        0xEE9B  // Quarter note straight
#define SEQ_RATE_QUARTER_DOT    0xEE9C  // Quarter note dotted
#define SEQ_RATE_QUARTER_TRIP   0xEE9D  // Quarter note triplet
#define SEQ_RATE_EIGHTH         0xEE9E  // Eighth note straight
#define SEQ_RATE_EIGHTH_DOT     0xEE9F  // Eighth note dotted
#define SEQ_RATE_EIGHTH_TRIP    0xEEA0  // Eighth note triplet
#define SEQ_RATE_SIXTEENTH      0xEEA1  // Sixteenth note straight
#define SEQ_RATE_SIXTEENTH_DOT  0xEEA2  // Sixteenth note dotted
#define SEQ_RATE_SIXTEENTH_TRIP 0xEEA3  // Sixteenth note triplet
#define SEQ_RATE_RESET          0xEEA4  // Reset to preset's default rate

// Direct Step Sequencer Preset Selection (0xEEA5-0xEEE8) - 68 presets (maps to firmware IDs 68-135)
#define SEQ_PRESET_BASE         0xEEA5  // Base address for seq presets (0xEEA5 + offset, maps to firmware ID 68+offset)

// NEW: Arpeggiator Rate Up/Down (0xEEE9-0xEEEA)
#define ARP_RATE_UP             0xEEE9  // Cycle to next rate (1/4 → 1/4 dot → 1/4 trip → 1/8...)
#define ARP_RATE_DOWN           0xEEEA  // Cycle to previous rate

// NEW: Arpeggiator Static Gate Values (0xEEEB-0xEEF4)
#define ARP_SET_GATE_10         0xEEEB  // Set gate to 10%
#define ARP_SET_GATE_20         0xEEEC  // Set gate to 20%
#define ARP_SET_GATE_30         0xEEED  // Set gate to 30%
#define ARP_SET_GATE_40         0xEEEE  // Set gate to 40%
#define ARP_SET_GATE_50         0xEEEF  // Set gate to 50%
#define ARP_SET_GATE_60         0xEEF0  // Set gate to 60%
#define ARP_SET_GATE_70         0xEEF1  // Set gate to 70%
#define ARP_SET_GATE_80         0xEEF2  // Set gate to 80%
#define ARP_SET_GATE_90         0xEEF3  // Set gate to 90%
#define ARP_SET_GATE_100        0xEEF4  // Set gate to 100%

// NEW: Step Sequencer Rate Up/Down (0xEEF5-0xEEF6)
#define SEQ_RATE_UP             0xEEF5  // Cycle to next rate (1/4 → 1/4 dot → 1/4 trip → 1/8...)
#define SEQ_RATE_DOWN           0xEEF6  // Cycle to previous rate

// NEW: Step Sequencer Static Gate Values (0xEEF7-0xEF00)
#define STEP_SET_GATE_10        0xEEF7  // Set gate to 10%
#define STEP_SET_GATE_20        0xEEF8  // Set gate to 20%
#define STEP_SET_GATE_30        0xEEF9  // Set gate to 30%
#define STEP_SET_GATE_40        0xEEFA  // Set gate to 40%
#define STEP_SET_GATE_50        0xEEFB  // Set gate to 50%
#define STEP_SET_GATE_60        0xEEFC  // Set gate to 60%
#define STEP_SET_GATE_70        0xEEFD  // Set gate to 70%
#define STEP_SET_GATE_80        0xEEFE  // Set gate to 80%
#define STEP_SET_GATE_90        0xEEFF  // Set gate to 90%
#define STEP_SET_GATE_100       0xEF00  // Set gate to 100%

// NEW: Step Sequencer Modifiers (0xEF01-0xEF08)
#define SEQ_MOD_1               0xEF01  // Step Sequencer 1 Modifier (affects slot 1)
#define SEQ_MOD_2               0xEF02  // Step Sequencer 2 Modifier (affects slot 2)
#define SEQ_MOD_3               0xEF03  // Step Sequencer 3 Modifier (affects slot 3)
#define SEQ_MOD_4               0xEF04  // Step Sequencer 4 Modifier (affects slot 4)
#define SEQ_MOD_5               0xEF05  // Step Sequencer 5 Modifier (affects slot 5)
#define SEQ_MOD_6               0xEF06  // Step Sequencer 6 Modifier (affects slot 6)
#define SEQ_MOD_7               0xEF07  // Step Sequencer 7 Modifier (affects slot 7)
#define SEQ_MOD_8               0xEF08  // Step Sequencer 8 Modifier (affects slot 8)

// NEW: Arpeggiator Gate Up/Down (0xEF09-0xEF0A)
#define ARP_GATE_UP             0xEF09  // Increase arpeggiator gate by 10%
#define ARP_GATE_DOWN           0xEF0A  // Decrease arpeggiator gate by 10%

// NEW: Step Sequencer Gate Up/Down (0xEF0B-0xEF0C)
#define SEQ_GATE_UP             0xEF0B  // Increase sequencer gate by 10%
#define SEQ_GATE_DOWN           0xEF0C  // Decrease sequencer gate by 10%

// NEW: Quick Build Buttons (0xEF0D-0xEF15)
#define ARP_QUICK_BUILD         0xEF0D  // Quick build arpeggiator preset
#define SEQ_QUICK_BUILD_1       0xEF0E  // Quick build step sequencer slot 1
#define SEQ_QUICK_BUILD_2       0xEF0F  // Quick build step sequencer slot 2
#define SEQ_QUICK_BUILD_3       0xEF10  // Quick build step sequencer slot 3
#define SEQ_QUICK_BUILD_4       0xEF11  // Quick build step sequencer slot 4
#define SEQ_QUICK_BUILD_5       0xEF12  // Quick build step sequencer slot 5
#define SEQ_QUICK_BUILD_6       0xEF13  // Quick build step sequencer slot 6
#define SEQ_QUICK_BUILD_7       0xEF14  // Quick build step sequencer slot 7
#define SEQ_QUICK_BUILD_8       0xEF15  // Quick build step sequencer slot 8

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

    // NEW: Analog Curve and Gamepad Response Settings
    uint8_t analog_curve_index;        // 0-6=Factory presets, 7-16=User curves 1-10
    bool angle_adjustment_enabled;     // Enable diagonal angle adjustment
    uint8_t diagonal_angle;            // 0-90 degrees for diagonal adjustment
    bool use_square_output;            // Square vs circular joystick output
    bool snappy_joystick_enabled;      // Use max instead of combining opposite inputs

    uint16_t magic;  // 0x47A3 (GAME) for validation
} gaming_settings_t;

// EEPROM address for gaming settings (100 bytes allocated) - MOVED to avoid overlap with expanded per-key actuation
#define GAMING_SETTINGS_EEPROM_ADDR 74100
#define GAMING_SETTINGS_MAGIC 0x47A3

// =============================================================================
// CURVE SYSTEM (For Gaming Analog & Velocity Curves)
// =============================================================================

// User-defined curve (24 bytes each)
// Used for both gaming analog curves and per-key velocity curves
typedef struct {
    uint8_t points[4][2];  // 4 control points: (x, y) each 0-255
    char name[16];         // User-friendly name (e.g., "My FPS Curve")
} user_curve_t;

// Global user curves array (10 slots × 24 bytes = 240 bytes + 2 magic = 242 bytes)
typedef struct {
    user_curve_t curves[10];
    uint16_t magic;  // 0xCF01 (CurVe1) for validation
} user_curves_t;

// EEPROM address for user curves
#define USER_CURVES_EEPROM_ADDR 68100
#define USER_CURVES_MAGIC 0xCF01

extern user_curves_t user_curves;

// Curve system functions
void user_curves_init(void);
void user_curves_save(void);
void user_curves_load(void);
void user_curves_reset(void);
uint8_t apply_curve(uint8_t input, uint8_t curve_index);

// Curve indices:
// 0-6:   Factory presets (Linear, Aggro, Slow, Smooth, Steep, Instant, Turbo)
// 7-16:  User curves 1-10
#define CURVE_FACTORY_LINEAR    0
#define CURVE_FACTORY_AGGRO     1
#define CURVE_FACTORY_SLOW      2
#define CURVE_FACTORY_SMOOTH    3
#define CURVE_FACTORY_STEEP     4
#define CURVE_FACTORY_INSTANT   5
#define CURVE_FACTORY_TURBO     6
#define CURVE_USER_START        7
#define CURVE_USER_END          16

// Gaming mode global state
extern bool gaming_mode_active;
extern gaming_settings_t gaming_settings;

// Gaming system functions
void gaming_init(void);
void gaming_save_settings(void);
void gaming_load_settings(void);
void gaming_reset_settings(void);
void gaming_update_joystick(void);

// Gamepad response transformation functions
void apply_angle_adjustment(int16_t* x, int16_t* y, uint8_t angle_deg);
void apply_square_output(int16_t* x, int16_t* y);
void apply_snappy_joystick(int16_t* axis_val, int16_t pos, int16_t neg);
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
#define MAX_SEQ_SLOTS 8
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

    // Locked-in values (captured when sequencer starts playing)
    uint8_t locked_channel;             // Locked MIDI channel
    uint8_t locked_velocity_min;        // Locked velocity minimum
    uint8_t locked_velocity_max;        // Locked velocity maximum
    int8_t locked_transpose;            // Locked transposition value
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
extern seq_preset_t seq_active_presets[MAX_SEQ_SLOTS];  // 8 slots for sequencers (8 × 392 = 3136 bytes)

// Step Sequencer modifier tracking
extern bool seq_modifier_held[MAX_SEQ_SLOTS];  // Track which seq modifiers are held

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
int8_t seq_find_slot_with_preset(uint8_t preset_id);  // Find slot playing specific preset (-1 if none)

// Smart toggle/selection functions
void arp_toggle(void);  // Toggle arpeggiator on/off
void arp_select_preset(uint8_t preset_id);  // Smart preset selection with toggle
void seq_select_preset(uint8_t preset_id);  // Smart seq preset selection with slot management

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

// NEW: Rate cycling functions
void arp_rate_up(void);
void arp_rate_down(void);
void seq_rate_up(void);
void seq_rate_down(void);
void seq_rate_up_for_slot(uint8_t slot);
void seq_rate_down_for_slot(uint8_t slot);

// NEW: Static gate setting functions
void arp_set_gate_static(uint8_t gate_percent);
void seq_set_gate_static(uint8_t gate_percent);
void seq_set_gate_for_slot(uint8_t slot, uint8_t gate_percent);

// NEW: Quick Build System Types
typedef enum {
    QUICK_BUILD_NONE = 0,
    QUICK_BUILD_ARP,
    QUICK_BUILD_SEQ
} quick_build_mode_t;

typedef struct {
    quick_build_mode_t mode;           // Current build mode (NONE, ARP, or SEQ)
    uint8_t seq_slot;                  // Which seq slot we're building (0-7)
    uint8_t current_step;              // Current step (0-based internal)
    uint8_t note_count;                // Total notes recorded so far
    uint8_t root_note;                 // First note played (arp only, for interval calculation)
    bool has_root;                     // Have we recorded the root yet? (arp only)
    bool sustain_held_last_check;      // Track sustain state for release detection
    uint32_t button_press_time;        // For 3-second hold detection
    bool has_saved_build;              // Has user completed a build?
} quick_build_state_t;

extern quick_build_state_t quick_build_state;

// NEW: Quick Build functions
void quick_build_start_arp(void);
void quick_build_start_seq(uint8_t slot);
void quick_build_cancel(void);
void quick_build_finish(void);
void quick_build_erase(void);
void quick_build_handle_note(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel);
void quick_build_handle_sustain_release(void);
void quick_build_update(void);
bool quick_build_is_active(void);
uint8_t quick_build_get_current_step(void);
void render_big_number(uint8_t number);

// Internal helper functions
void add_arp_note(uint8_t channel, uint8_t note, uint8_t velocity, uint32_t note_off_time);
void remove_arp_note(uint8_t channel, uint8_t note);
void process_arp_note_offs(void);
void midi_send_noteon_arp(uint8_t channel, uint8_t note, uint8_t velocity, uint8_t raw_travel);
void midi_send_noteon_seq(uint8_t slot, uint8_t note, uint8_t velocity_0_127);
void midi_send_noteoff_arp(uint8_t channel, uint8_t note, uint8_t velocity);

#endif // ORTHOMIDI5X14_H

