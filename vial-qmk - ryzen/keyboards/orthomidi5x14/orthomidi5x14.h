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
int16_t gaming_analog_to_axis(uint8_t row, uint8_t col, bool invert);
bool gaming_analog_to_trigger(uint8_t row, uint8_t col, int16_t* value);

#endif // ORTHOMIDI5X14_H

