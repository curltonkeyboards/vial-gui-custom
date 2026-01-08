#include "process_dynamic_macro.h"
#include "quantum.h"
#include "midi.h"
#include "process_midi.h"
#include <stdio.h>
#include "qmk_midi.h"
#include "raw_hid.h"
#include <math.h>
#include "keyboards/orthomidi5x14/orthomidi5x14.h"
#include "process_dks.h"

// External functions to mark/unmark notes from macros
extern void mark_note_from_macro(uint8_t channel, uint8_t note, uint8_t macro_id);
extern void unmark_note_from_macro(uint8_t channel, uint8_t note, uint8_t macro_id);
extern void cleanup_notes_from_macro(uint8_t macro_id);
extern bool is_live_note_active(uint8_t channel, uint8_t note);
static int8_t macro_transpose_target[MAX_MACROS] = {0, 0, 0, 0};

// Define constants
#define MAX_ACTIVE_NOTES 16
#define MAX_PENDING_RELEASES 16
#define MAX_MACROS 4
#define MACRO_BUFFER_SIZE 20480  // 2KB per macro
#define TOTAL_BUFFER_SIZE (MAX_MACROS * MACRO_BUFFER_SIZE)
#define MACRO_DELETE_THRESHOLD 1000  // 2 seconds in milliseconds
#define OVERDUB_BUFFER_SIZE 5120  // Size of temporary buffer for overdub recording
#define RESTART_PROXIMITY_THRESHOLD 200  // 200ms threshold for restart eligibility
#define LOOP_SNAP_TO_START_THRESHOLD 100  // 100ms threshold for snapping to loop start
#define MIDI_EVENT_DUMMY 0xFF

// Command types for the batching system
#define CMD_NONE 0
#define CMD_PLAY 1
#define CMD_STOP 2
#define CMD_RECORD 3
#define CMD_PLAY_OVERDUB_ONLY 4
#define CMD_PLAY_MUTED 6
#define CMD_GHOST_MUTE 7
#define CMD_OVERDUB_AFTER_MUTE 8
#define CMD_ADVANCED_OVERDUB_REC 9
#define CMD_ADVANCED_OVERDUB_END 10
// Advanced overdub mode variables - complete independence system
bool overdub_advanced_mode = false;
uint32_t overdub_independent_loop_length[MAX_MACROS] = {0, 0, 0, 0};
uint32_t overdub_independent_timer[MAX_MACROS] = {0, 0, 0, 0};
uint32_t overdub_independent_gap_time[MAX_MACROS] = {0, 0, 0, 0};
uint32_t overdub_independent_start_time[MAX_MACROS] = {0, 0, 0, 0};
bool overdub_independent_waiting_for_gap[MAX_MACROS] = {false, false, false, false};

static bool macro_main_muted[MAX_MACROS] = {false, false, false, false};

#define HID_MANUFACTURER_ID     0x7D
#define HID_DEVICE_ID          0x4D
#define HID_SUB_ID             0x00

// Save/Load Operations (0xA0-0xA7)
#define HID_CMD_SAVE_START              0xA0  // was 0x01
#define HID_CMD_SAVE_CHUNK              0xA1  // was 0x02
#define HID_CMD_SAVE_END                0xA2  // was 0x03
#define HID_CMD_LOAD_START              0xA3  // was 0x04
#define HID_CMD_LOAD_CHUNK              0xA4  // was 0x05
#define HID_CMD_LOAD_END                0xA5  // was 0x06
#define HID_CMD_LOAD_OVERDUB_START      0xA6  // was 0x07
// Reserved for future save/load operations: 0xA7

// Request/Trigger Operations (0xA8-0xAF)
#define HID_CMD_REQUEST_SAVE            0xA8  // was 0x10
#define HID_CMD_TRIGGER_SAVE_ALL        0xA9  // was 0x30
// Reserved for future request/trigger operations: 0xAA-0xAF

// Loop Configuration (0xB0-0xB5)
#define HID_CMD_SET_LOOP_CONFIG         0xB0  // was 0x40
#define HID_CMD_SET_MAIN_LOOP_CCS       0xB1  // was 0x41
#define HID_CMD_SET_OVERDUB_CCS         0xB2  // was 0x42
#define HID_CMD_SET_NAVIGATION_CONFIG   0xB3  // was 0x43
#define HID_CMD_GET_ALL_CONFIG          0xB4  // was 0x44
#define HID_CMD_RESET_LOOP_CONFIG       0xB5  // was 0x45

// Additional Loop Commands (0xCE+)
#define HID_CMD_CLEAR_ALL_LOOPS         0xCE  // Clear all loop content

// DKS (Dynamic Keystroke) Commands (0xE5-0xEA)
#define HID_CMD_DKS_GET_SLOT            0xE5  // Get DKS slot configuration
#define HID_CMD_DKS_SET_ACTION          0xE6  // Set a single DKS action
#define HID_CMD_DKS_SAVE_EEPROM         0xE7  // Save all DKS configs to EEPROM
#define HID_CMD_DKS_LOAD_EEPROM         0xE8  // Load all DKS configs from EEPROM
#define HID_CMD_DKS_RESET_SLOT          0xE9  // Reset a slot to defaults
#define HID_CMD_DKS_RESET_ALL           0xEA  // Reset all slots to defaults

// Keyboard Configuration (0xB6-0xBF)
#define HID_CMD_SET_KEYBOARD_CONFIG         0xB6  // was 0x50
#define HID_CMD_GET_KEYBOARD_CONFIG         0xB7  // was 0x51
#define HID_CMD_RESET_KEYBOARD_CONFIG       0xB8  // was 0x52
#define HID_CMD_SAVE_KEYBOARD_SLOT          0xB9  // was 0x53
#define HID_CMD_LOAD_KEYBOARD_SLOT          0xBA  // was 0x54
#define HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED 0xBB  // was 0x55
#define HID_CMD_SET_KEYBOARD_PARAM_SINGLE    0xBD  // NEW: Set individual keyboard parameter

// Parameter IDs for HID_CMD_SET_KEYBOARD_PARAM_SINGLE (1-byte parameters)
#define PARAM_CHANNEL_NUMBER                 0
#define PARAM_TRANSPOSE_NUMBER               1
#define PARAM_TRANSPOSE_NUMBER2              2
#define PARAM_TRANSPOSE_NUMBER3              3
#define PARAM_HE_VELOCITY_CURVE              4
#define PARAM_HE_VELOCITY_MIN                5
#define PARAM_HE_VELOCITY_MAX                6
#define PARAM_KEYSPLIT_HE_VELOCITY_CURVE     7
#define PARAM_KEYSPLIT_HE_VELOCITY_MIN       8
#define PARAM_KEYSPLIT_HE_VELOCITY_MAX       9
#define PARAM_TRIPLESPLIT_HE_VELOCITY_CURVE  10
#define PARAM_TRIPLESPLIT_HE_VELOCITY_MIN    11
#define PARAM_TRIPLESPLIT_HE_VELOCITY_MAX    12
// PARAM_AFTERTOUCH_MODE (13) and PARAM_AFTERTOUCH_CC (14) are now per-layer
// Use set_layer_actuation() / get_layer_actuation() instead (0xCA/0xCB commands)
#define PARAM_BASE_SUSTAIN                   15
#define PARAM_KEYSPLIT_SUSTAIN               16
#define PARAM_TRIPLESPLIT_SUSTAIN            17
#define PARAM_KEYSPLITCHANNEL                18
#define PARAM_KEYSPLIT2CHANNEL               19
#define PARAM_KEYSPLITSTATUS                 20
#define PARAM_KEYSPLITTRANSPOSESTATUS        21
#define PARAM_KEYSPLITVELOCITYSTATUS         22
// 4-byte parameters
#define PARAM_VELOCITY_SENSITIVITY           30
#define PARAM_CC_SENSITIVITY                 31
// Hall Effect Sensor Linearization
#define PARAM_LUT_CORRECTION_STRENGTH        32

// HID packet structure (32 bytes max)
#define HID_PACKET_SIZE        32
#define HID_HEADER_SIZE        6
#define HID_DATA_SIZE          (HID_PACKET_SIZE - HID_HEADER_SIZE)
#define HID_CHUNK_SIZE         (HID_DATA_SIZE - 4)  // Reserve 4 bytes for chunk info

static void handle_set_keyboard_config(const uint8_t* data);
static void handle_set_keyboard_config_advanced(const uint8_t* data);
static void handle_set_keyboard_param_single(const uint8_t* data);
static void handle_get_keyboard_config(void);
static void handle_reset_keyboard_config(void);
static void handle_save_keyboard_slot(const uint8_t* data);
static void handle_load_keyboard_slot(const uint8_t* data);

// DKS handler functions
static void handle_dks_get_slot(const uint8_t* data);
static void handle_dks_set_action(const uint8_t* data);
static void handle_dks_reset_slot(const uint8_t* data);

typedef struct {
    uint8_t type;
    uint8_t channel;
    uint8_t note;
    uint8_t raw_travel;  // 0-255 raw analog travel value (was velocity)
    uint32_t timestamp;
} midi_event_t;

// Command structure for batch processing
typedef struct {
    uint8_t command_type;  // CMD_PLAY, CMD_STOP, CMD_RECORD
    uint8_t macro_id;      // Which macro (1-4)
    bool processed;        // Has this command been processed
} macro_command_t;

// Batch queue for loop transition
#define MAX_BATCH_COMMANDS 16
static macro_command_t command_batch[MAX_BATCH_COMMANDS];
static uint8_t command_batch_count = 0;

// Simplified playback state structure for each macro
typedef struct {
    midi_event_t *current;
    midi_event_t *end;
    midi_event_t *buffer_start;
    uint32_t timer;
    int8_t direction;  // Always +1 now
    bool is_playing;
    bool waiting_for_loop_gap;
    uint32_t next_event_time;
    uint32_t loop_gap_time;
    uint32_t loop_length;  // ADD THIS FIELD
} macro_playback_state_t;

// Loop Messaging Variables
bool loop_messaging_enabled = false;
uint8_t loop_messaging_channel = 16;  // MIDI channel 1-16
bool sync_midi_mode = false;  // Send stop/start on loop restarts
bool alternate_restart_mode = false;       // true = send stop+start, false = send restart CC
static uint8_t loop_restart_cc[MAX_MACROS] = {128, 128, 128, 128};  // Single restart CC per loop

// Main Loop CC numbers [4 loops]
static uint8_t loop_start_recording_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t loop_stop_recording_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t loop_start_playing_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t loop_stop_playing_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t loop_clear_cc[MAX_MACROS] = {128, 128, 128, 128};

// Overdub CC numbers [4 loops]
static uint8_t overdub_start_recording_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t overdub_stop_recording_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t overdub_start_playing_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t overdub_stop_playing_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t overdub_clear_cc[MAX_MACROS] = {128, 128, 128, 128};
static uint8_t overdub_restart_cc[MAX_MACROS] = {128, 128, 128, 128};  // Overdub restart CC per loop

// Navigation CC (global) - 8 positions
static bool loop_navigate_use_master_cc = false;  // true = use master CC, false = use individual CCs
static uint8_t loop_navigate_master_cc = 128;       // Single CC with values 0-127
static uint8_t loop_navigate_0_8_cc = 128;
static uint8_t loop_navigate_1_8_cc = 128;
static uint8_t loop_navigate_2_8_cc = 128;
static uint8_t loop_navigate_3_8_cc = 128;
static uint8_t loop_navigate_4_8_cc = 128;
static uint8_t loop_navigate_5_8_cc = 128;
static uint8_t loop_navigate_6_8_cc = 128;
static uint8_t loop_navigate_7_8_cc = 128;

// Array of playback states for all macros
static macro_playback_state_t macro_playback[MAX_MACROS] = {0};
static macro_playback_state_t overdub_playback[MAX_MACROS] = {0};
static bool is_macro_empty = true;
static bool first_note_recorded = false;
static uint16_t key_timers[MAX_MACROS] = {0};  // Separate timer for each macro key
static bool macro_key_held[MAX_MACROS] = {false};  // Track which keys are being held
static bool macro_deleted[MAX_MACROS] = {false};  // Track which macros have been deleted during current hold
static bool recording_sustain_active = false;
static uint16_t last_macro_press_time[MAX_MACROS] = {0};  // Track last press time
static uint16_t last_overdub_press_time[MAX_MACROS] = {0};  // Track last overdub press time separately
static bool skip_autoplay_for_macro[MAX_MACROS] = {false};  // Track which macros should skip autoplay
static bool ignore_second_press[MAX_MACROS] = {false};  // Ignore the second press of a double-tap for recording
uint8_t unsynced_mode_active = 0;  // Track whether unsynced mode button is being held
bool overdub_button_held = false;  // Track whether overdub button is being held
bool macro_in_overdub_mode[MAX_MACROS] = {false};  // Track which macros are in overdub mode
static uint8_t overdub_target_macro = 0;
bool mute_button_held = false;  // For the 0xCC10 button
static bool overdub_mute_pending[MAX_MACROS] = {false, false, false, false};  // Pending mute changes
static bool overdub_unmute_pending[MAX_MACROS] = {false, false, false, false};  // Pending unmute changes

static bool handle_macro_key(uint16_t keycode, keyrecord_t *record);
static bool handle_macro_key_press(uint8_t macro_num, uint8_t macro_idx);
static bool handle_mute_button_combinations(uint8_t macro_num, uint8_t macro_idx, 
                                           midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                                           bool this_macro_playing, bool this_macro_empty,
                                           bool this_macro_in_overdub, bool this_overdub_muted, 
                                           bool has_overdub_content);
static bool handle_unsynced_mode(uint8_t macro_num, uint8_t macro_idx, 
                                midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                                bool this_macro_playing, bool this_macro_empty);
static bool handle_sample_mode(uint8_t macro_num, uint8_t macro_idx,
                              midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                              bool this_macro_playing, bool this_macro_empty);
static bool handle_regular_mode(uint8_t macro_num, uint8_t macro_idx,
                               midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                               bool this_macro_playing, bool this_macro_empty);

// Unified macro buffer - 8KB total
static midi_event_t macro_buffer[TOTAL_BUFFER_SIZE / sizeof(midi_event_t)];

// Macro recording state variables
static midi_event_t *macro_ends[MAX_MACROS] = {NULL};
static midi_event_t *macro_pointer = NULL;
uint8_t macro_id = 0;
static uint32_t recording_start_time = 0;
static bool macros_initialized = false;

// Forward declarations
static void dynamic_macro_cleanup_notes_for_state(macro_playback_state_t *state);
static bool dynamic_macro_play_task_for_state(macro_playback_state_t *state);
static bool merge_overdub_buffer(uint8_t macro_idx);  // <-- ADD THIS LINE
static void clear_overdub_only(uint8_t macro_num);
static bool deserialize_overdub_data(uint8_t* buffer, uint16_t buffer_size, uint8_t expected_macro);
static void handle_hid_load_overdub_data(uint8_t macro_num, const uint8_t* data, uint16_t data_len);
static void check_loop_trigger(void);
static void execute_command_batch(void);
static void clear_command_batch(void);
static bool add_command_to_batch(uint8_t command_type, uint8_t macro_id);
bool sample_mode_active = false;  // Track whether sample mode is active
void dynamic_macro_play(midi_event_t *macro_buffer, midi_event_t *macro_end, int8_t direction);
void dynamic_macro_record_end(midi_event_t *macro_buffer, midi_event_t *macro_pointer, int8_t direction, midi_event_t **macro_end, uint32_t *start_time);
void dynamic_macro_actual_start(uint32_t *start_time);

static uint32_t overdub_start_time = 0;
uint32_t loop_start_time = 0;
uint32_t loop_length = 0;
static bool macro_transpose_pending[MAX_MACROS] = {false, false, false, false};
static int8_t macro_transpose_pending_value[MAX_MACROS] = {0, 0, 0, 0};

// Dynamic overdub buffers for each macro
static midi_event_t *overdub_buffers[MAX_MACROS] = {NULL, NULL, NULL, NULL};
static midi_event_t *overdub_buffer_ends[MAX_MACROS] = {NULL, NULL, NULL, NULL};
static uint32_t overdub_buffer_sizes[MAX_MACROS] = {0, 0, 0, 0};
static uint32_t pause_timestamps[MAX_MACROS] = {0, 0, 0, 0};
static uint32_t overdub_pause_timestamps[MAX_MACROS] = {0, 0, 0, 0};
bool overdub_muted[MAX_MACROS] = {false, false, false, false};

// Add these variables to store preroll events
static midi_event_t preroll_buffer[PREROLL_BUFFER_SIZE];
static uint8_t preroll_buffer_count = 0;
static uint8_t preroll_buffer_index = 0;
static uint32_t preroll_start_time = 0;
bool collecting_preroll = false;  // Not static - needs to be accessible from process_midi.c
bool is_macro_primed = false;     // Change this from static to global

// Add these new variables after the existing channel override variables
static int8_t macro_channel_offset[MAX_MACROS] = {0, 0, 0, 0};
static int8_t macro_channel_offset_target[MAX_MACROS] = {0, 0, 0, 0};
static bool macro_channel_offset_pending[MAX_MACROS] = {false, false, false, false};
static int8_t macro_channel_offset_pending_value[MAX_MACROS] = {0, 0, 0, 0};
static bool suppress_next_loop_start_playing[MAX_MACROS] = {false, false, false, false};
static bool suppress_next_overdub_start_playing[MAX_MACROS] = {false, false, false, false};
// Rename existing channel override to channel absolute for clarity
// Change macro_channel_override to macro_channel_absolute
static uint8_t macro_channel_absolute[MAX_MACROS] = {0, 0, 0, 0}; // 0 = ignore, 1-16 = force to channel
static uint8_t macro_channel_absolute_target[MAX_MACROS] = {0, 0, 0, 0};
static bool macro_channel_absolute_pending[MAX_MACROS] = {false, false, false, false};
static uint8_t macro_channel_absolute_pending_value[MAX_MACROS] = {0, 0, 0, 0};

static uint8_t macro_velocity_absolute[MAX_MACROS] = {0, 0, 0, 0}; // 0 = ignore, 1-127 = force to velocity
static uint8_t macro_velocity_absolute_target[MAX_MACROS] = {0, 0, 0, 0};
static bool macro_velocity_absolute_pending[MAX_MACROS] = {false, false, false, false};
static uint8_t macro_velocity_absolute_pending_value[MAX_MACROS] = {0, 0, 0, 0};

static int8_t macro_velocity_offset_target[MAX_MACROS] = {0, 0, 0, 0};
static bool macro_velocity_offset_pending[MAX_MACROS] = {false, false, false, false};
static int8_t macro_velocity_offset_pending_value[MAX_MACROS] = {0, 0, 0, 0};

// Velocity range and curve settings for macro recording/playback
static uint8_t macro_recording_curve[MAX_MACROS] = {2, 2, 2, 2};  // Default: MEDIUM (2)
static uint8_t macro_recording_min[MAX_MACROS] = {1, 1, 1, 1};    // Default: 1
static uint8_t macro_recording_max[MAX_MACROS] = {127, 127, 127, 127};  // Default: 127
static uint8_t macro_recording_curve_target[MAX_MACROS] = {2, 2, 2, 2};
static uint8_t macro_recording_min_target[MAX_MACROS] = {1, 1, 1, 1};
static uint8_t macro_recording_max_target[MAX_MACROS] = {127, 127, 127, 127};
static bool macro_recording_curve_pending[MAX_MACROS] = {false, false, false, false};
static bool macro_recording_min_pending[MAX_MACROS] = {false, false, false, false};
static bool macro_recording_max_pending[MAX_MACROS] = {false, false, false, false};
static uint8_t macro_recording_curve_pending_value[MAX_MACROS] = {2, 2, 2, 2};
static uint8_t macro_recording_min_pending_value[MAX_MACROS] = {1, 1, 1, 1};
static uint8_t macro_recording_max_pending_value[MAX_MACROS] = {127, 127, 127, 127};

// Overdub velocity range and curve settings (separate from main macro)
static uint8_t overdub_recording_curve[MAX_MACROS] = {2, 2, 2, 2};
static uint8_t overdub_recording_min[MAX_MACROS] = {1, 1, 1, 1};
static uint8_t overdub_recording_max[MAX_MACROS] = {127, 127, 127, 127};
static bool overdub_recording_set[MAX_MACROS] = {false, false, false, false};  // Track if overdub range has been set

static int8_t macro_octave_doubler[MAX_MACROS] = {0, 0, 0, 0};
static int8_t macro_octave_doubler_target[MAX_MACROS] = {0, 0, 0, 0};
static bool macro_octave_doubler_pending[MAX_MACROS] = {false, false, false, false};
static int8_t macro_octave_doubler_pending_value[MAX_MACROS] = {0, 0, 0, 0};
bool octave_doubler_button_held = false;

// Overdub-specific transformations (used only in advanced mode)
static int8_t overdub_transpose[MAX_MACROS] = {0, 0, 0, 0};
static int8_t overdub_transpose_target[MAX_MACROS] = {0, 0, 0, 0};
static bool overdub_transpose_pending[MAX_MACROS] = {false, false, false, false};
static int8_t overdub_transpose_pending_value[MAX_MACROS] = {0, 0, 0, 0};

static int8_t overdub_channel_offset[MAX_MACROS] = {0, 0, 0, 0};
static int8_t overdub_channel_offset_target[MAX_MACROS] = {0, 0, 0, 0};
static bool overdub_channel_offset_pending[MAX_MACROS] = {false, false, false, false};
static int8_t overdub_channel_offset_pending_value[MAX_MACROS] = {0, 0, 0, 0};
static uint8_t overdub_channel_absolute[MAX_MACROS] = {0, 0, 0, 0};
static uint8_t overdub_channel_absolute_target[MAX_MACROS] = {0, 0, 0, 0};
static bool overdub_channel_absolute_pending[MAX_MACROS] = {false, false, false, false};
static uint8_t overdub_channel_absolute_pending_value[MAX_MACROS] = {0, 0, 0, 0};
static int8_t overdub_velocity_offset[MAX_MACROS] = {0, 0, 0, 0};
static int8_t overdub_velocity_offset_target[MAX_MACROS] = {0, 0, 0, 0};
static bool overdub_velocity_offset_pending[MAX_MACROS] = {false, false, false, false};
static int8_t overdub_velocity_offset_pending_value[MAX_MACROS] = {0, 0, 0, 0};
static uint8_t overdub_velocity_absolute[MAX_MACROS] = {0, 0, 0, 0};
static uint8_t overdub_velocity_absolute_target[MAX_MACROS] = {0, 0, 0, 0};
static bool overdub_velocity_absolute_pending[MAX_MACROS] = {false, false, false, false};
static uint8_t overdub_velocity_absolute_pending_value[MAX_MACROS] = {0, 0, 0, 0};
static int8_t overdub_octave_doubler[MAX_MACROS] = {0, 0, 0, 0};
static int8_t overdub_octave_doubler_target[MAX_MACROS] = {0, 0, 0, 0};
static bool overdub_octave_doubler_pending[MAX_MACROS] = {false, false, false, false};
static int8_t overdub_octave_doubler_pending_value[MAX_MACROS] = {0, 0, 0, 0};

static bool overdub_merge_pending[MAX_MACROS] = {false, false, false, false};

bool copy_modifier_active = false;
bool paste_modifier_active = false;
uint8_t source_macro_id = 0;

uint16_t serialize_macro_data(uint8_t macro_num, uint8_t* buffer);
bool deserialize_macro_data(uint8_t* buffer, uint16_t buffer_size, uint8_t expected_macro);

static uint8_t hid_rx_buffer[MACRO_BUFFER_SIZE * 2];
static uint16_t hid_rx_buffer_pos = 0;
static bool hid_receiving_multi_packet = false;
static uint16_t hid_expected_total_packets = 0;
static uint16_t hid_received_packets = 0;

static bool recording_suspended[MAX_MACROS] = {false, false, false, false};  // Flag to stop recording new events while preserving timing
static void navigate_all_macros(int32_t time_offset_ms);
static void navigate_macro_playback_state(macro_playback_state_t *state, int32_t time_offset_ms, uint32_t current_time, uint8_t macro_idx);
static midi_event_t* find_event_at_position(macro_playback_state_t *state, uint32_t position_ms);
uint8_t bpm_source_macro = 0;

static bool overdub_independent_suspended[MAX_MACROS] = {false, false, false, false};
static uint32_t overdub_independent_suspension_time[MAX_MACROS] = {0, 0, 0, 0};

float macro_speed_factor[MAX_MACROS] = {1.0f, 1.0f, 1.0f, 1.0f};  // Individual speed for each macro
static bool speed_modifier_held = false;  // Track whether speed modifier button is held
static bool slow_modifier_held = false;  // Track whether speed modifier button is held
static float macro_speed_before_pause[MAX_MACROS] = {1.0f, 1.0f, 1.0f, 1.0f};
static bool global_playback_paused = false;
static uint32_t original_system_bpm = 0;  // Locked when first macro recorded
float macro_manual_speed[MAX_MACROS] = {1.0f, 1.0f, 1.0f, 1.0f};  // Individual manual speed adjustments

static uint32_t macro_recording_bpm[MAX_MACROS] = {0, 0, 0, 0};  // BPM when each macro was recorded
static bool macro_has_content[MAX_MACROS] = {false, false, false, false};  // Whether each macro has content

static bool capture_early_overdub_events[MAX_MACROS] = {false, false, false, false};
static midi_event_t early_overdub_buffer[MAX_MACROS][32]; // 32 events per macro should be plenty
static uint8_t early_overdub_count[MAX_MACROS] = {0, 0, 0, 0};

// Forward declarations for new functions
static void recalculate_all_macro_speeds_for_bpm(void);
static void recalculate_single_macro_speed(uint8_t macro_idx);
static void update_bpm_from_source_macro_speed(uint8_t macro_num, float new_speed);
static uint32_t calculate_base_bpm_excluding_source(void);
void dynamic_macro_bpm_changed(uint32_t new_bpm);
static void navigate_all_macros_to_fraction(uint8_t numerator, uint8_t denominator);
static void navigate_macro_to_absolute_time(macro_playback_state_t *state, uint32_t target_time_ms, uint32_t current_time, uint8_t macro_idx);
static uint32_t last_flash_time = 0;
static bool flash_state = false;
#define FLASH_INTERVAL_MS 50
static uint16_t overdub_temp_count[MAX_MACROS] = {0, 0, 0, 0};

loop_settings_t loop_settings;

void save_loop_settings(void) {
    // Copy current global variables to the structure
    loop_settings.loop_messaging_enabled = loop_messaging_enabled;
    loop_settings.loop_messaging_channel = loop_messaging_channel;
    loop_settings.sync_midi_mode = sync_midi_mode;
    loop_settings.alternate_restart_mode = alternate_restart_mode;
    loop_settings.loop_navigate_use_master_cc = loop_navigate_use_master_cc;
    
    // Copy main loop CC arrays
    for (uint8_t i = 0; i < 4; i++) {
        loop_settings.loop_restart_cc[i] = loop_restart_cc[i];
        loop_settings.loop_start_recording_cc[i] = loop_start_recording_cc[i];
        loop_settings.loop_stop_recording_cc[i] = loop_stop_recording_cc[i];
        loop_settings.loop_start_playing_cc[i] = loop_start_playing_cc[i];
        loop_settings.loop_stop_playing_cc[i] = loop_stop_playing_cc[i];
        loop_settings.loop_clear_cc[i] = loop_clear_cc[i];
    }
    
    // Copy overdub CC arrays
    for (uint8_t i = 0; i < 4; i++) {
        loop_settings.overdub_start_recording_cc[i] = overdub_start_recording_cc[i];
        loop_settings.overdub_stop_recording_cc[i] = overdub_stop_recording_cc[i];
        loop_settings.overdub_start_playing_cc[i] = overdub_start_playing_cc[i];
        loop_settings.overdub_stop_playing_cc[i] = overdub_stop_playing_cc[i];
        loop_settings.overdub_clear_cc[i] = overdub_clear_cc[i];
    }
    
    // Copy navigation CCs
    loop_settings.loop_navigate_master_cc = loop_navigate_master_cc;
    loop_settings.loop_navigate_0_8_cc = loop_navigate_0_8_cc;
    loop_settings.loop_navigate_1_8_cc = loop_navigate_1_8_cc;
    loop_settings.loop_navigate_2_8_cc = loop_navigate_2_8_cc;
    loop_settings.loop_navigate_3_8_cc = loop_navigate_3_8_cc;
    loop_settings.loop_navigate_4_8_cc = loop_navigate_4_8_cc;
    loop_settings.loop_navigate_5_8_cc = loop_navigate_5_8_cc;
    loop_settings.loop_navigate_6_8_cc = loop_navigate_6_8_cc;
    loop_settings.loop_navigate_7_8_cc = loop_navigate_7_8_cc;
    
    // Save to EEPROM
    eeprom_update_block(&loop_settings, (uint8_t*)LOOP_SETTINGS_EEPROM_ADDR, LOOP_SETTINGS_SIZE);
}

void load_loop_settings(void) {
    // Load from EEPROM
    eeprom_read_block(&loop_settings, (uint8_t*)LOOP_SETTINGS_EEPROM_ADDR, LOOP_SETTINGS_SIZE);
    
    // Update global variables with loaded settings
    loop_messaging_enabled = loop_settings.loop_messaging_enabled;
    loop_messaging_channel = loop_settings.loop_messaging_channel;
    sync_midi_mode = loop_settings.sync_midi_mode;
    alternate_restart_mode = loop_settings.alternate_restart_mode;
    loop_navigate_use_master_cc = loop_settings.loop_navigate_use_master_cc;
    
    // Update main loop CC arrays
    for (uint8_t i = 0; i < 4; i++) {
        loop_restart_cc[i] = loop_settings.loop_restart_cc[i];
        loop_start_recording_cc[i] = loop_settings.loop_start_recording_cc[i];
        loop_stop_recording_cc[i] = loop_settings.loop_stop_recording_cc[i];
        loop_start_playing_cc[i] = loop_settings.loop_start_playing_cc[i];
        loop_stop_playing_cc[i] = loop_settings.loop_stop_playing_cc[i];
        loop_clear_cc[i] = loop_settings.loop_clear_cc[i];
    }
    
    // Update overdub CC arrays
    for (uint8_t i = 0; i < 4; i++) {
        overdub_start_recording_cc[i] = loop_settings.overdub_start_recording_cc[i];
        overdub_stop_recording_cc[i] = loop_settings.overdub_stop_recording_cc[i];
        overdub_start_playing_cc[i] = loop_settings.overdub_start_playing_cc[i];
        overdub_stop_playing_cc[i] = loop_settings.overdub_stop_playing_cc[i];
        overdub_clear_cc[i] = loop_settings.overdub_clear_cc[i];
    }
    
    // Update navigation CCs
    loop_navigate_master_cc = loop_settings.loop_navigate_master_cc;
    loop_navigate_0_8_cc = loop_settings.loop_navigate_0_8_cc;
    loop_navigate_1_8_cc = loop_settings.loop_navigate_1_8_cc;
    loop_navigate_2_8_cc = loop_settings.loop_navigate_2_8_cc;
    loop_navigate_3_8_cc = loop_settings.loop_navigate_3_8_cc;
    loop_navigate_4_8_cc = loop_settings.loop_navigate_4_8_cc;
    loop_navigate_5_8_cc = loop_settings.loop_navigate_5_8_cc;
    loop_navigate_6_8_cc = loop_settings.loop_navigate_6_8_cc;
    loop_navigate_7_8_cc = loop_settings.loop_navigate_7_8_cc;
}

void reset_loop_settings(void) {
    // Reset all global variables to defaults
    loop_messaging_enabled = false;
    loop_messaging_channel = 1;
    sync_midi_mode = false;
    alternate_restart_mode = false;
    loop_navigate_use_master_cc = false;
    
    // Reset all CC arrays to 128 (disabled)
    for (uint8_t i = 0; i < 4; i++) {
        loop_restart_cc[i] = 128;
        loop_start_recording_cc[i] = 128;
        loop_stop_recording_cc[i] = 128;
        loop_start_playing_cc[i] = 128;
        loop_stop_playing_cc[i] = 128;
        loop_clear_cc[i] = 128;
        overdub_start_recording_cc[i] = 128;
        overdub_stop_recording_cc[i] = 128;
        overdub_start_playing_cc[i] = 128;
        overdub_stop_playing_cc[i] = 128;
        overdub_clear_cc[i] = 128;
        overdub_restart_cc[i] = 128;  // ADD THIS LINE
    }
    
    // Reset navigation CCs
    loop_navigate_master_cc = 128;
    loop_navigate_0_8_cc = 128;
    loop_navigate_1_8_cc = 128;
    loop_navigate_2_8_cc = 128;
    loop_navigate_3_8_cc = 128;
    loop_navigate_4_8_cc = 128;
    loop_navigate_5_8_cc = 128;
    loop_navigate_6_8_cc = 128;
    loop_navigate_7_8_cc = 128;
    
    // Save the reset values to EEPROM
    save_loop_settings();
}

bool is_macro_effectively_playing(uint8_t i) {
    return macro_playback[i].is_playing || (current_bpm > 0 && bpm_source_macro == 0) || overdub_playback[i].is_playing;
}

// Transpose variables for each macro (-127 to +127 semitones)
static int8_t macro_transpose[MAX_MACROS] = {0, 0, 0, 0};

// Velocity offset variables for each macro (-127 to +127)
static int8_t macro_velocity_offset[MAX_MACROS] = {0, 0, 0, 0};


// Helper function to apply transpose and clamp to valid MIDI range
static uint8_t apply_transpose(uint8_t original_note, int8_t transpose_amount) {
    int16_t transposed = (int16_t)original_note + transpose_amount;
    
    // Clamp to valid MIDI note range (0-127)
    if (transposed < 0) {
        return 0;
    } else if (transposed > 127) {
        return 127;
    } else {
        return (uint8_t)transposed;
    }
}

// Replace the existing apply_channel_transformations function
static uint8_t apply_channel_transformations(uint8_t original_channel, int8_t channel_offset, uint8_t channel_absolute) {
    uint8_t base_channel;
    
    // Check if absolute channel is set (not 0)
    if (channel_absolute != 0) {
        // Use absolute channel as the base (convert 1-16 to 0-15)
        base_channel = (channel_absolute - 1) & 0x0F;
    } else {
        // Use original channel as the base
        base_channel = original_channel;
    }
    
    // Apply offset to the base channel
    int16_t final_channel = (int16_t)base_channel + channel_offset;
    
    // Wrap around MIDI channel range (0-15)
    while (final_channel < 0) {
        final_channel += 16;
    }
    while (final_channel > 15) {
        final_channel -= 16;
    }
    
    return (uint8_t)final_channel;
}

static uint32_t calculate_restart_proximity_threshold(uint8_t macro_idx) {
    // If unsynced mode is active, return 0 (immediate restart)
    if ((unsynced_mode_active == 2 || unsynced_mode_active == 5)) {
        dprintf("dynamic macro: unsynced mode active - using 0ms threshold\n");
        return 0;
    }
    
    // If BPM is set (from any source), use quarter note duration
    if (current_bpm > 0 && (unsynced_mode_active == 1)) {
        // Calculate quarter note duration from BPM
        // current_bpm is in format where 120 BPM = 12000000 (BPM * 100000)
        // Quarter note time = 60000ms / (current_bpm / 100000)
        // = 6000000000 / current_bpm
        uint32_t quarter_note_ms = 6000000000ULL / current_bpm;
        
        return quarter_note_ms;
    }
	
	if (current_bpm > 0 && (unsynced_mode_active == 3)) {
        // Calculate quarter note duration from BPM
        // current_bpm is in format where 120 BPM = 12000000 (BPM * 100000)
        // Quarter note time = 60000ms / (current_bpm / 100000)
        // = 6000000000 / current_bpm
        uint32_t quarter_note_ms = (6000000000ULL / current_bpm) / 3;
        
        return quarter_note_ms;
    }
    
    // No BPM set - fall back to loop-based timing (25% of shortest loop)
    uint32_t shortest_real_loop = 0;
    
    // Find the shortest REAL-WORLD loop among all macros that have content
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_has_content[i] && macro_playback[i].loop_length > 0) {
            // Calculate real-world loop duration accounting for speed
            float speed_factor = macro_speed_factor[i];
            uint32_t real_loop_duration;
            
            if (speed_factor > 0.0f) {
                real_loop_duration = (uint32_t)(macro_playback[i].loop_length / speed_factor);
            } else {
                continue; // Skip paused macros
            }
            
            if (shortest_real_loop == 0 || real_loop_duration < shortest_real_loop) {
                shortest_real_loop = real_loop_duration;
            }
        }
    }
    
    if (shortest_real_loop > 0) {
        uint32_t threshold = shortest_real_loop / 4;  // 25% of shortest real-world loop time
        
        dprintf("dynamic macro: threshold = %lu ms (25%% of shortest real-world loop %lu ms)\n", 
                threshold, shortest_real_loop);
        
        return threshold;
    }
    
    // Final fallback if nothing else works
    dprintf("dynamic macro: using fallback threshold %d ms\n", RESTART_PROXIMITY_THRESHOLD);
    return RESTART_PROXIMITY_THRESHOLD;
}

static void send_loop_message(uint8_t cc_number, uint8_t value) {
    if (loop_messaging_enabled && cc_number < 128) {  // CHANGED: < 128 instead of > 0
        midi_send_cc(&midi_device, loop_messaging_channel - 1, cc_number, value);
        dprintf("loop messaging: sent CC %d value %d on channel %d\n", cc_number, value, loop_messaging_channel);
    }
}

// New getter functions for channel offset
int8_t get_macro_channel_offset(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_channel_offset[macro_num - 1];
    }
    return 0;
}

// New target getter for channel offset
int8_t get_macro_channel_offset_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_channel_offset_target[macro_num - 1];
    }
    return 0;
}

// New setter function for channel offset
void set_macro_channel_offset(uint8_t macro_num, int8_t channel_offset) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        // Clamp channel offset to reasonable range (-127 to +127)
        if (channel_offset < -127) {
            channel_offset = -127;
        } else if (channel_offset > 127) {
            channel_offset = 127;
        }
        
        macro_channel_offset[macro_num - 1] = channel_offset;
        dprintf("dynamic macro: set channel offset for macro %d to %+d\n", 
                macro_num, channel_offset);
    }
}

// New target setter for channel offset
void set_macro_channel_offset_target(uint8_t macro_num, int8_t channel_offset) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        // Clamp channel offset to reasonable range
        if (channel_offset < -127) {
            channel_offset = -127;
        } else if (channel_offset > 127) {
            channel_offset = 127;
        }
        
        uint8_t macro_idx = macro_num - 1;
        
        // Set the target immediately
        macro_channel_offset_target[macro_idx] = channel_offset;
        
        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            // Macros are playing - queue the change for next loop trigger
            macro_channel_offset_pending[macro_idx] = true;
            macro_channel_offset_pending_value[macro_idx] = channel_offset;
            
            dprintf("dynamic macro: set channel offset target for macro %d to %+d (queued for loop trigger)\n", 
                    macro_num, channel_offset);
        } else {
            // No macros playing - apply immediately
            macro_channel_offset[macro_idx] = channel_offset;
            dprintf("dynamic macro: immediately applied channel offset for macro %d to %+d\n", 
                    macro_num, channel_offset);
        }
    }
}

// Helper function to apply velocity curve/range, then offset/absolute transformations
static uint8_t apply_velocity_transformations(uint8_t raw_travel, int8_t velocity_offset, uint8_t velocity_absolute, uint8_t macro_num) {
    uint8_t base_velocity;

    // STEP 1: Apply velocity curve and range to raw_travel (0-255) to get MIDI velocity (1-127)
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;
        uint8_t curve = macro_recording_curve[macro_idx];
        uint8_t min_vel = macro_recording_min[macro_idx];
        uint8_t max_vel = macro_recording_max[macro_idx];

        // Apply Bezier curve to raw_travel (0-255 input -> 0-255 output)
        uint8_t curved_travel = apply_curve(raw_travel, curve);

        // Map curved travel to velocity range (min_vel to max_vel)
        uint8_t range = max_vel - min_vel;
        int16_t velocity_from_curve = min_vel + ((int16_t)curved_travel * range) / 255;

        // Clamp to valid MIDI velocity range (1-127)
        if (velocity_from_curve < 1) velocity_from_curve = 1;
        if (velocity_from_curve > 127) velocity_from_curve = 127;

        base_velocity = (uint8_t)velocity_from_curve;
    } else {
        // Fallback: use raw_travel as-is (shouldn't happen)
        base_velocity = (raw_travel > 127) ? 127 : raw_travel;
        if (base_velocity < 1) base_velocity = 1;
    }

    // STEP 2: Apply absolute velocity override if set
    if (velocity_absolute != 0) {
        base_velocity = velocity_absolute;
    }

    // STEP 3: Apply velocity offset
    int16_t final_velocity = (int16_t)base_velocity + velocity_offset;

    // STEP 4: Clamp to valid MIDI velocity range (0-127)
    if (final_velocity < 0) {
        final_velocity = 0;
    } else if (final_velocity > 127) {
        final_velocity = 127;
    }

    return (uint8_t)final_velocity;
}

// Helper function to apply overdub velocity curve/range, then offset/absolute transformations
static uint8_t apply_overdub_velocity_transformations(uint8_t raw_travel, int8_t velocity_offset, uint8_t velocity_absolute, uint8_t macro_num) {
    uint8_t base_velocity;

    // STEP 1: Apply velocity curve and range to raw_travel (0-255) to get MIDI velocity (1-127)
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;
        uint8_t curve = overdub_recording_curve[macro_idx];
        uint8_t min_vel = overdub_recording_min[macro_idx];
        uint8_t max_vel = overdub_recording_max[macro_idx];

        // Apply Bezier curve to raw_travel (0-255 input -> 0-255 output)
        uint8_t curved_travel = apply_curve(raw_travel, curve);

        // Map curved travel to velocity range (min_vel to max_vel)
        uint8_t range = max_vel - min_vel;
        int16_t velocity_from_curve = min_vel + ((int16_t)curved_travel * range) / 255;

        // Clamp to valid MIDI velocity range (1-127)
        if (velocity_from_curve < 1) velocity_from_curve = 1;
        if (velocity_from_curve > 127) velocity_from_curve = 127;

        base_velocity = (uint8_t)velocity_from_curve;
    } else {
        // Fallback: use raw_travel as-is (shouldn't happen)
        base_velocity = (raw_travel > 127) ? 127 : raw_travel;
        if (base_velocity < 1) base_velocity = 1;
    }

    // STEP 2: Apply absolute velocity override if set
    if (velocity_absolute != 0) {
        base_velocity = velocity_absolute;
    }

    // STEP 3: Apply velocity offset
    int16_t final_velocity = (int16_t)base_velocity + velocity_offset;

    // STEP 4: Clamp to valid MIDI velocity range (0-127)
    if (final_velocity < 0) {
        final_velocity = 0;
    } else if (final_velocity > 127) {
        final_velocity = 127;
    }

    return (uint8_t)final_velocity;
}


// Helper function to get macro buffer for a given macro number
static midi_event_t* get_macro_buffer(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return NULL;
    return &macro_buffer[(macro_num - 1) * (MACRO_BUFFER_SIZE / sizeof(midi_event_t))];
}

// Helper function to get macro end pointer
static midi_event_t** get_macro_end_ptr(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return NULL;
    return &macro_ends[macro_num - 1];
}

void dynamic_macro_init(void) {
    dprintf("dynamic macro: initializing system to fresh startup state\n");
    load_loop_settings();
	load_layer_actuations();
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        uint8_t macro_num = i + 1;
        
        // ZERO OUT THE MAIN MACRO MEMORY CONTENT (same as your reset)
        midi_event_t *macro_start = get_macro_buffer(macro_num);
        midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
        
        if (macro_start && macro_end_ptr) {
            // Calculate how much memory to clear (entire macro buffer)
            uint32_t macro_buffer_events = MACRO_BUFFER_SIZE / sizeof(midi_event_t);
            memset(macro_start, 0, macro_buffer_events * sizeof(midi_event_t));
            
            // Set macro end pointer to start (making it empty)
            *macro_end_ptr = macro_start;
        }
        
        // Clear overdub buffer references (permanent overdub area)
        overdub_buffers[i] = NULL;
        overdub_buffer_ends[i] = NULL;
        overdub_buffer_sizes[i] = 0;
        overdub_muted[i] = false;
        
        // COMPLETE PLAYBACK STATE RESET (matching device startup)
        macro_playback[i].current = NULL;
        macro_playback[i].end = NULL;
        macro_playback[i].buffer_start = NULL;
        macro_playback[i].timer = 0;
        macro_playback[i].direction = +1;
        macro_playback[i].is_playing = false;
        macro_playback[i].waiting_for_loop_gap = false;
        macro_playback[i].next_event_time = 0;
        macro_playback[i].loop_gap_time = 0;
        macro_playback[i].loop_length = 0;
        macro_main_muted[i] = false;
        
        // COMPLETE OVERDUB PLAYBACK STATE RESET
        overdub_playback[i].current = NULL;
        overdub_playback[i].end = NULL;
        overdub_playback[i].buffer_start = NULL;
        overdub_playback[i].timer = 0;
        overdub_playback[i].direction = +1;
        overdub_playback[i].is_playing = false;
        overdub_playback[i].waiting_for_loop_gap = false;
        overdub_playback[i].next_event_time = 0;
        overdub_playback[i].loop_gap_time = 0;
        overdub_playback[i].loop_length = 0;
		
		capture_early_overdub_events[i] = false;
		early_overdub_count[i] = 0;
		memset(early_overdub_buffer[i], 0, sizeof(early_overdub_buffer[i]));
        
        // Reset speed and BPM variables
        macro_manual_speed[i] = 1.0f;      
        macro_speed_factor[i] = 1.0f;
        macro_recording_bpm[i] = 0;
        macro_has_content[i] = false;
        
        // Reset transformation values to startup state
        macro_transpose[i] = 0;
        macro_transpose_target[i] = 0;
        macro_transpose_pending[i] = false;
        macro_transpose_pending_value[i] = 0;
        
        macro_channel_offset[i] = 0;
        macro_channel_offset_target[i] = 0;
        macro_channel_offset_pending[i] = false;
        macro_channel_offset_pending_value[i] = 0;
        
        macro_channel_absolute[i] = 0;
        macro_channel_absolute_target[i] = 0;
        macro_channel_absolute_pending[i] = false;
        macro_channel_absolute_pending_value[i] = 0;
        
        macro_velocity_offset[i] = 0;
        macro_velocity_offset_target[i] = 0;
        macro_velocity_offset_pending[i] = false;
        macro_velocity_offset_pending_value[i] = 0;
        
        macro_velocity_absolute[i] = 0;
        macro_velocity_absolute_target[i] = 0;
        macro_velocity_absolute_pending[i] = false;
        macro_velocity_absolute_pending_value[i] = 0;
        
        macro_octave_doubler[i] = 0;
        macro_octave_doubler_target[i] = 0;
        macro_octave_doubler_pending[i] = false;
        macro_octave_doubler_pending_value[i] = 0;
		
		        overdub_transpose[i] = 0;
        overdub_transpose_target[i] = 0;
        overdub_transpose_pending[i] = false;
        overdub_transpose_pending_value[i] = 0;
        
        overdub_channel_offset[i] = 0;
        overdub_channel_offset_target[i] = 0;
        overdub_channel_offset_pending[i] = false;
        overdub_channel_offset_pending_value[i] = 0;
        
        overdub_channel_absolute[i] = 0;
        overdub_channel_absolute_target[i] = 0;
        overdub_channel_absolute_pending[i] = false;
        overdub_channel_absolute_pending_value[i] = 0;
        
        overdub_velocity_offset[i] = 0;
        overdub_velocity_offset_target[i] = 0;
        overdub_velocity_offset_pending[i] = false;
        overdub_velocity_offset_pending_value[i] = 0;
        
        overdub_velocity_absolute[i] = 0;
        overdub_velocity_absolute_target[i] = 0;
        overdub_velocity_absolute_pending[i] = false;
        overdub_velocity_absolute_pending_value[i] = 0;
        
        overdub_octave_doubler[i] = 0;
        overdub_octave_doubler_target[i] = 0;
        overdub_octave_doubler_pending[i] = false;
        overdub_octave_doubler_pending_value[i] = 0;
        
        // Reset additional macro-specific flags (matching device startup)
        skip_autoplay_for_macro[i] = false;
        ignore_second_press[i] = false; 
        last_macro_press_time[i] = 0;
        macro_deleted[i] = false;
        
        // Clear overdub mode flags
        macro_in_overdub_mode[i] = false;
        
        // Clear any pending overdub operations  
        overdub_mute_pending[i] = false;
        overdub_unmute_pending[i] = false;
        overdub_merge_pending[i] = false;
        overdub_temp_count[i] = 0;
		overdub_independent_suspended[i] = false;
        overdub_independent_suspension_time[i] = 0;
		
        // Reset key press tracking
        key_timers[i] = 0;
        macro_key_held[i] = false;
        
        // Reset pause tracking
        pause_timestamps[i] = 0;
        overdub_pause_timestamps[i] = 0;
        macro_speed_before_pause[i] = 1.0f;
    }
    
    // Reset global state variables
    macro_id = 0;
    overdub_target_macro = 0;
    current_macro_id = 0;
    macro_pointer = NULL;
    is_macro_primed = false;
    first_note_recorded = false;
    recording_start_time = 0;
    recording_sustain_active = false;
    collecting_preroll = false;
    preroll_buffer_count = 0;
    preroll_buffer_index = 0;
    preroll_start_time = 0;
    
    // Reset BPM system
    bpm_source_macro = 0;
    current_bpm = 0;
    original_system_bpm = 0;
    
    // Reset modifier states
    unsynced_mode_active = 0;
    overdub_button_held = false;
    mute_button_held = false;
    sample_mode_active = false;
    octave_doubler_button_held = false;
    copy_modifier_active = false;
    paste_modifier_active = false;
    source_macro_id = 0;
    speed_modifier_held = false;
    slow_modifier_held = false;
    global_playback_paused = false;
    
    // Clear command batch
    clear_command_batch();
    
    // Reset HID state
    hid_rx_buffer_pos = 0;
    hid_receiving_multi_packet = false;
    hid_expected_total_packets = 0;
    hid_received_packets = 0;
    
    // Initialize macros flag
    macros_initialized = true;
    
    dprintf("dynamic macro: system initialized with complete fresh state\n");
}

static void initialize_macros(void) {
    if (!macros_initialized) {
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            macro_ends[i] = get_macro_buffer(i + 1);
        }
        macros_initialized = true;
    }
}

static void clear_command_batch(void) {
    for (uint8_t i = 0; i < MAX_BATCH_COMMANDS; i++) {
        command_batch[i].command_type = CMD_NONE;
        command_batch[i].macro_id = 0;
        command_batch[i].processed = false;
    }
    command_batch_count = 0;
}

static bool add_command_to_batch(uint8_t command_type, uint8_t macro_id_target) {
    if (command_batch_count >= MAX_BATCH_COMMANDS) {
        return false; // Batch is full
    }
    
    // Check for duplicate commands (don't add if already in batch)
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == command_type &&
            command_batch[i].macro_id == macro_id_target) {
            return true; // Already in batch
        }
    }
    
    // AUTOMATIC RECORDING SUSPENSION: If we're adding a command that would stop recording,
    // suspend recording immediately to prevent new events from being recorded
    if ((command_type == CMD_STOP || command_type == CMD_PLAY) && 
        macro_id > 0 && macro_id == macro_id_target && macro_id <= MAX_MACROS) {
        recording_suspended[macro_id - 1] = true;
        dprintf("dynamic macro: auto-suspended recording for macro %d (batched %s command)\n", 
                macro_id, command_type == CMD_STOP ? "STOP" : "PLAY");
    }
    
    // EARLY OVERDUB CAPTURE: If we're adding a command that will start overdub recording,
    // start capturing early events
	if ((command_type == CMD_OVERDUB_AFTER_MUTE || command_type == CMD_PLAY_MUTED || command_type == CMD_PLAY_OVERDUB_ONLY) && 
		macro_id_target <= MAX_MACROS) {
		uint8_t target_idx = macro_id_target - 1;
		
		// Check if overdub has no content
		bool overdub_is_empty = (overdub_buffers[target_idx] == NULL || 
								overdub_buffer_ends[target_idx] == overdub_buffers[target_idx]);
		
		if (overdub_is_empty) {
			capture_early_overdub_events[target_idx] = true;
			early_overdub_count[target_idx] = 0; // Reset count
			dprintf("dynamic macro: started early overdub capture for macro %d (empty overdub)\n", macro_id_target);
		}
	}
    
    // Add new command
    command_batch[command_batch_count].command_type = command_type;
    command_batch[command_batch_count].macro_id = macro_id_target;
    command_batch[command_batch_count].processed = false;
    command_batch_count++;
    
    // Start preroll collection if this is a recording command (slave recording)
    if (command_type == CMD_RECORD) {
        preroll_buffer_count = 0;
        preroll_buffer_index = 0;
        preroll_start_time = timer_read32();
        collecting_preroll = true;
        dprintf("dynamic macro: started preroll collection for slave recording of macro %d\n", macro_id_target);
    }
	
		if (command_type == CMD_ADVANCED_OVERDUB_REC) {
		preroll_buffer_count = 0;
		preroll_buffer_index = 0;
		preroll_start_time = timer_read32();
		collecting_preroll = true;
		dprintf("dynamic macro: started preroll collection for advanced overdub of macro %d\n", macro_id_target);
	}
	
	    if (command_type == CMD_ADVANCED_OVERDUB_END && macro_id_target <= MAX_MACROS) {
        uint8_t target_idx = macro_id_target - 1;
        
        // Suspend recording immediately and store the time
        overdub_independent_suspended[target_idx] = true;
        overdub_independent_suspension_time[target_idx] = timer_read32();
        
        dprintf("dynamic macro: suspended independent overdub recording for macro %d at time %lu\n", 
                macro_id_target, overdub_independent_suspension_time[target_idx]);
    }
    
    dprintf("dynamic macro: Added command %d for macro %d to batch (total: %d)\n", 
            command_type, macro_id_target, command_batch_count);
    
    return true;
}

// Function to check if a specific command exists in the batch for a given macro
static bool command_exists_in_batch(uint8_t command_type, uint8_t macro_id) {
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == command_type &&
            command_batch[i].macro_id == macro_id &&
            !command_batch[i].processed) {
            return true;
        }
    }
    return false;
}

// Function to remove a specific command from the batch for a given macro
static void remove_command_from_batch(uint8_t command_type, uint8_t macro_id) {
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == command_type &&
            command_batch[i].macro_id == macro_id &&
            !command_batch[i].processed) {
            // Remove this command by shifting all subsequent commands
            for (uint8_t j = i; j < command_batch_count - 1; j++) {
                command_batch[j] = command_batch[j + 1];
            }
            command_batch_count--;
            i--; // Check the same index again
            dprintf("dynamic macro: removed command %d for macro %d from batch\n", 
                    command_type, macro_id);
        }
    }
}

bool is_macro_in_overdub(uint8_t macro_id) {
    if (macro_id > 0 && macro_id <= MAX_MACROS) {
        return macro_in_overdub_mode[macro_id - 1];
    }
    return false;
}

// Function for midi.c to record an event to the overdub buffer
void record_overdub_event(uint8_t type, uint8_t channel, uint8_t note, uint8_t velocity) {
    dynamic_macro_record_midi_event_overdub(type, channel, note, velocity);
}


void dynamic_macro_led_blink(void) {
#ifdef BACKLIGHT_ENABLE
    backlight_toggle();
#endif
}

__attribute__((weak)) void dynamic_macro_record_start_user(int8_t direction) {
     
}

__attribute__((weak)) void dynamic_macro_play_user(int8_t direction) {
     
}

__attribute__((weak)) void dynamic_macro_record_key_user(int8_t direction, keyrecord_t *record) {
     
}

__attribute__((weak)) void dynamic_macro_record_end_user(int8_t direction) {
     
}

__attribute__((weak)) bool dynamic_macro_valid_key_user(uint16_t keycode, keyrecord_t *record) {
    return true;
}

static void dynamic_macro_cleanup_notes_for_state(macro_playback_state_t *state) {
    // Figure out which macro this is
    uint8_t macro_num = 0;
    bool is_overdub = false;
    
    // First check if this is a main macro playback state
    for (uint8_t i = 1; i <= MAX_MACROS; i++) {
        if (state->buffer_start == get_macro_buffer(i)) {
            macro_num = i;
            break;
        }
    }
    
    // If not found in main macros, check if it's an overdub playback state
    if (macro_num == 0) {
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (state->buffer_start == overdub_buffers[i]) {
                macro_num = i + 1;
                is_overdub = true;
                break;
            }
        }
    }
    
    // Clean up notes for this specific macro or overdub
    if (macro_num > 0) {
        if (is_overdub) {
            // For overdub notes, use the offset macro ID (macro_num + MAX_MACROS)
            cleanup_notes_from_macro(macro_num + MAX_MACROS);
            dprintf("dynamic macro: cleaned up overdub notes for macro %d (track ID %d)\n", 
                    macro_num, macro_num + MAX_MACROS);
					//if overdub_advanced_mode {
					//send_loop_message(overdub_stop_playing_cc[macro_num - 1], 127);}
        } else {
            // For main macro notes, use the regular macro ID
            cleanup_notes_from_macro(macro_num);
            dprintf("dynamic macro: cleaned up main macro notes for macro %d\n", macro_num);
			//if overdub_advanced_mode {
			//send_loop_message(loop_stop_playing_cc[macro_num - 1], 127);
        }
    }
    
    // Reset playback state
    state->current = NULL;
    state->is_playing = false;
}


void dynamic_macro_cleanup_notes(void) {
    // Cleanup notes for all macros - just stop playback now
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_playback[i].is_playing) {
            macro_playback[i].is_playing = false;
            macro_playback[i].current = NULL;
        }
        
        // Also stop overdub playback
        if (overdub_playback[i].is_playing) {
            overdub_playback[i].is_playing = false;
            overdub_playback[i].current = NULL;
        }
    }
    
    // Also clear overdub state if stopping everything
    if (overdub_target_macro) {
        macro_in_overdub_mode[overdub_target_macro - 1] = false;
        overdub_target_macro = 0;
        macro_id = 0;
        current_macro_id = 0;
        stop_dynamic_macro_recording();
        dprintf("dynamic macro: cleared continuous overdub state\n");
    }
    
    // Note: Live notes are now handled in process_midi.c
}

bool dynamic_macro_is_paused(void) {
    return global_playback_paused;
}

static bool has_overdub_space(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return false;
    
    uint8_t macro_idx = macro_num - 1;
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
    
    if (!macro_start || !macro_end_ptr) return false;
    
    // Calculate ALL space usage
    uint32_t main_bytes = (*macro_end_ptr - macro_start) * sizeof(midi_event_t);
    uint32_t temp_bytes = overdub_temp_count[macro_idx] * sizeof(midi_event_t);
    
    // Check if adding one more temp event would cause collision
    uint32_t new_temp_bytes = temp_bytes + sizeof(midi_event_t);
    
    return (main_bytes + new_temp_bytes) < MACRO_BUFFER_SIZE;
}

// Helper function to get the backward write position for overdub
static midi_event_t* get_overdub_write_position(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return NULL;
    
    uint8_t macro_idx = macro_num - 1;
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    
    // Calculate position: start at end of 2KB buffer, go backwards by current count
    // End of buffer = macro_start + (MACRO_BUFFER_SIZE / sizeof(midi_event_t))
    uint32_t buffer_end_offset = MACRO_BUFFER_SIZE / sizeof(midi_event_t);
    
    // Write position = end of buffer - current overdub count - 1 (for next event)
    return macro_start + buffer_end_offset - overdub_temp_count[macro_idx] - 1;
}

// Helper function to get the start of temp overdub events for reading
static midi_event_t* get_overdub_read_start(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return NULL;
    
    uint8_t macro_idx = macro_num - 1;
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    
    if (overdub_temp_count[macro_idx] == 0) return NULL;
    
    // Start reading from: end_of_buffer - temp_count
    uint32_t buffer_end_offset = MACRO_BUFFER_SIZE / sizeof(midi_event_t);
    return macro_start + buffer_end_offset - overdub_temp_count[macro_idx];
}



// Helper function to snapshot velocity curve/range settings when recording starts
static void snapshot_recording_settings(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;

        // Snapshot curve and range from global settings
        macro_recording_curve[macro_idx] = he_velocity_curve;
        macro_recording_min[macro_idx] = he_velocity_min;
        macro_recording_max[macro_idx] = he_velocity_max;

        dprintf("dynamic macro: snapshotted recording settings for macro %d - curve:%d min:%d max:%d\n",
                macro_num, macro_recording_curve[macro_idx],
                macro_recording_min[macro_idx], macro_recording_max[macro_idx]);
    }
}

// Helper function to snapshot overdub recording settings (only if not already set)
static void snapshot_overdub_recording_settings(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;

        // Only snapshot if not already set (for continuous overdubs)
        if (!overdub_recording_set[macro_idx]) {
            // Snapshot curve and range from global settings
            overdub_recording_curve[macro_idx] = he_velocity_curve;
            overdub_recording_min[macro_idx] = he_velocity_min;
            overdub_recording_max[macro_idx] = he_velocity_max;
            overdub_recording_set[macro_idx] = true;

            dprintf("dynamic macro: snapshotted overdub recording settings for macro %d - curve:%d min:%d max:%d\n",
                    macro_num, overdub_recording_curve[macro_idx],
                    overdub_recording_min[macro_idx], overdub_recording_max[macro_idx]);
        }
    }
}

void dynamic_macro_record_start(midi_event_t **macro_pointer, midi_event_t *macro_buffer, int8_t direction, uint32_t *start_time) {
    *macro_pointer = macro_buffer;

    if (unsynced_mode_active == 4 || unsynced_mode_active == 5) {
        // Skip priming - start recording immediately for modes 4 and 5
        is_macro_primed = false;
        first_note_recorded = true;
        is_macro_empty = false;  // Set to false since we're recording dummy event NOW
        
        // Set the start time immediately
        *start_time = timer_read32();
        recording_start_time = *start_time;
        
        // Record dummy event immediately so loop isn't considered empty
        (*macro_pointer)->type = MIDI_EVENT_DUMMY;
        (*macro_pointer)->channel = 0;
        (*macro_pointer)->note = 0;
        (*macro_pointer)->raw_travel = 0;
        (*macro_pointer)->timestamp = 0;
        
        (*macro_pointer)++;  // Advance the pointer past the dummy event
        
        // Check and store current sustain state
        recording_sustain_active = get_live_sustain_state();
        
        dprintln("dynamic macro: immediate recording (no priming) with dummy event");
         
    } else {
        // Normal priming behavior for all other modes
        is_macro_primed = true;
        first_note_recorded = false;
        is_macro_empty = true;
        
        dprintln("dynamic macro primed: waiting for first note");
        
        // Signal that the macro is primed (blink once)
         
    }
}

void collect_preroll_event(uint8_t type, uint8_t channel, uint8_t note, uint8_t raw_travel) {
    if (!collecting_preroll) return;

    // Store the event in the circular buffer
    preroll_buffer[preroll_buffer_index].type = type;
    preroll_buffer[preroll_buffer_index].channel = channel;
    preroll_buffer[preroll_buffer_index].note = note;
    preroll_buffer[preroll_buffer_index].raw_travel = raw_travel;

    // Calculate time relative to preroll start
    uint32_t now = timer_read32();
    preroll_buffer[preroll_buffer_index].timestamp = now - preroll_start_time;

    // Update buffer index and count
    preroll_buffer_index = (preroll_buffer_index + 1) % PREROLL_BUFFER_SIZE;
    if (preroll_buffer_count < PREROLL_BUFFER_SIZE) {
        preroll_buffer_count++;
    }

    dprintf("preroll: stored event type:%d ch:%d note/cc:%d raw:%d at time %lu ms\n",
            type, channel, note, raw_travel, now - preroll_start_time);
}

// Add this new helper function (place it near other static helper functions)
static void clear_temp_overdub_buffer(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return;
    
    uint8_t macro_idx = macro_num - 1;
    
    // If there are temp events, zero out the memory before clearing count
    if (overdub_temp_count[macro_idx] > 0) {
        midi_event_t *temp_start = get_overdub_read_start(macro_num);
        if (temp_start != NULL) {
            // Zero out the temp event memory to prevent ghost reads
            memset(temp_start, 0, overdub_temp_count[macro_idx] * sizeof(midi_event_t));
            dprintf("dynamic macro: cleared %d temp overdub events from memory for macro %d\n", 
                    overdub_temp_count[macro_idx], macro_num);
        }
    }
    
    // Clear the count and pending flag
    overdub_temp_count[macro_idx] = 0;
    overdub_merge_pending[macro_idx] = false;
}

// REPLACE the existing merge_overdub_buffer function with this:
static bool merge_overdub_buffer(uint8_t macro_idx) {
    uint8_t macro_num = macro_idx + 1;
    
    dprintf("dynamic macro: merge_overdub_buffer() called for macro %d (mode: %s)\n", 
            macro_num, overdub_advanced_mode ? "INDEPENDENT" : "SYNCED");
    
    uint16_t temp_event_count = overdub_temp_count[macro_idx];
    if (temp_event_count == 0) {
        clear_temp_overdub_buffer(macro_num);
        dprintf("dynamic macro: no overdub temp events to merge for macro %d\n", macro_num);
        return true;
    }
    
    midi_event_t *overdub_start = overdub_buffers[macro_idx];
    midi_event_t **overdub_end_ptr = &overdub_buffer_ends[macro_idx];
    uint32_t max_overdub_events = overdub_buffer_sizes[macro_idx];
    
    if (!overdub_start) {
        clear_temp_overdub_buffer(macro_num);
        dprintf("dynamic macro: no permanent overdub buffer allocated for macro %d\n", macro_num);
        return false;
    }
    
    midi_event_t *temp_read_start = get_overdub_read_start(macro_num);
    if (!temp_read_start) {
        clear_temp_overdub_buffer(macro_num);
        dprintf("dynamic macro: could not get temp read start for macro %d\n", macro_num);
        return false;
    }
    
    midi_event_t *temp_events = (midi_event_t*)malloc(temp_event_count * sizeof(midi_event_t));
    if (!temp_events) {
        clear_temp_overdub_buffer(macro_num);
        dprintf("dynamic macro: malloc failed for temp events array for macro %d\n", macro_num);
        return false;
    }
    
    // Read events in correct chronological order (reverse the backwards storage)
    for (uint16_t i = 0; i < temp_event_count; i++) {
        temp_events[i] = temp_read_start[temp_event_count - 1 - i];
    }
    
    if (overdub_advanced_mode) {
        // ADVANCED MODE: Simple chronological append - no timestamp sorting needed
        dprintf("dynamic macro: processing INDEPENDENT overdub merge for %d events\n", temp_event_count);
        
        if (overdub_buffer_ends[macro_idx] == overdub_buffers[macro_idx]) {
            // FIRST INDEPENDENT OVERDUB - Simple copy with independent loop length
            uint32_t copy_count = (temp_event_count > max_overdub_events) ? max_overdub_events : temp_event_count;
            
            memcpy(overdub_start, temp_events, copy_count * sizeof(midi_event_t));
            *overdub_end_ptr = overdub_start + copy_count;
            
            // Set up INDEPENDENT overdub playback state
            overdub_playback[macro_idx].loop_gap_time = overdub_independent_gap_time[macro_idx];
            overdub_playback[macro_idx].loop_length = overdub_independent_loop_length[macro_idx];
            
            // CRITICAL: Force overdub to use independent timing if currently playing
            if (overdub_playback[macro_idx].is_playing) {
                overdub_playback[macro_idx].timer = overdub_independent_timer[macro_idx];
                dprintf("dynamic macro: updated playing overdub to use independent timer\n");
            }
            
            dprintf("dynamic macro: merged first INDEPENDENT overdub for macro %d (%d events, %lu ms independent loop)\n", 
                    macro_num, copy_count, overdub_independent_loop_length[macro_idx]);
        } else {
            // SUBSEQUENT INDEPENDENT OVERDUB - Simple append (events are already chronologically ordered)
            uint32_t current_event_count = *overdub_end_ptr - overdub_start;
            uint32_t total_events = current_event_count + temp_event_count;
            
            if (total_events <= max_overdub_events) {
                // Simple append - no timestamp sorting because independent events are chronological
                memcpy(*overdub_end_ptr, temp_events, temp_event_count * sizeof(midi_event_t));
                *overdub_end_ptr += temp_event_count;
                
                dprintf("dynamic macro: appended %d events to INDEPENDENT overdub for macro %d (%lu total events)\n", 
                        temp_event_count, macro_num, total_events);
            } else {
                // Buffer overflow - append what we can
                uint32_t available_space = max_overdub_events - current_event_count;
                uint32_t events_to_add = (temp_event_count > available_space) ? available_space : temp_event_count;
                
                if (events_to_add > 0) {
                    memcpy(*overdub_end_ptr, temp_events, events_to_add * sizeof(midi_event_t));
                    *overdub_end_ptr += events_to_add;
                }
                dprintf("dynamic macro: appended %lu events to INDEPENDENT overdub (buffer full) for macro %d\n", 
                        events_to_add, macro_num);
            }
        }
    } else {
        // ORIGINAL MODE: Complex merge with timestamp sorting for loop boundaries
        dprintf("dynamic macro: processing SYNCED overdub merge for %d events\n", temp_event_count);
        
        if (overdub_buffer_ends[macro_idx] == overdub_buffers[macro_idx]) {
            // FIRST SYNCED OVERDUB
            uint32_t copy_count = (temp_event_count > max_overdub_events) ? max_overdub_events : temp_event_count;
            
            memcpy(overdub_start, temp_events, copy_count * sizeof(midi_event_t));
            *overdub_end_ptr = overdub_start + copy_count;
            
            // Set up SYNCED overdub playback state (use parent timing)
            macro_playback_state_t *original_state = &macro_playback[macro_idx];
            overdub_playback[macro_idx].loop_gap_time = original_state->loop_gap_time;
            overdub_playback[macro_idx].loop_length = original_state->loop_length;
            
            dprintf("dynamic macro: merged first SYNCED overdub for macro %d (%d events, synced to parent)\n", 
                    macro_num, copy_count);
        } else {
            // SUBSEQUENT SYNCED OVERDUB - Merge with timestamp sorting
            uint32_t current_event_count = *overdub_end_ptr - overdub_start;
            uint32_t total_events = current_event_count + temp_event_count;
            
            if (total_events <= max_overdub_events) {
                midi_event_t *merge_buffer = (midi_event_t*)malloc(total_events * sizeof(midi_event_t));
                
                if (merge_buffer != NULL) {
                    // Copy existing + new events
                    memcpy(merge_buffer, overdub_start, current_event_count * sizeof(midi_event_t));
                    memcpy(merge_buffer + current_event_count, temp_events, temp_event_count * sizeof(midi_event_t));
                    
                    // Sort all events by timestamp using insertion sort
                    for (uint32_t j = 1; j < total_events; j++) {
                        midi_event_t key = merge_buffer[j];
                        int32_t k = j - 1;
                        
                        while (k >= 0 && merge_buffer[k].timestamp > key.timestamp) {
                            merge_buffer[k + 1] = merge_buffer[k];
                            k = k - 1;
                        }
                        merge_buffer[k + 1] = key;
                    }
                    
                    memcpy(overdub_start, merge_buffer, total_events * sizeof(midi_event_t));
                    *overdub_end_ptr = overdub_start + total_events;
                    
                    free(merge_buffer);
                    dprintf("dynamic macro: merged SYNCED overdub for macro %d (%lu total sorted events)\n", macro_num, total_events);
                } else {
                    free(temp_events);
                    clear_temp_overdub_buffer(macro_num);
                    return false;
                }
            } else {
                // Buffer overflow
                uint32_t available_space = max_overdub_events - current_event_count;
                uint32_t events_to_add = (temp_event_count > available_space) ? available_space : temp_event_count;
                
                if (events_to_add > 0) {
                    memcpy(*overdub_end_ptr, temp_events, events_to_add * sizeof(midi_event_t));
                    *overdub_end_ptr += events_to_add;
                }
                dprintf("dynamic macro: appended %lu events to SYNCED overdub (buffer full) for macro %d\n", 
                        events_to_add, macro_num);
            }
        }
    }
    
    free(temp_events);
    
    // Check if overdub is still active and should continue
    bool overdub_still_active = (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num);
    
    clear_temp_overdub_buffer(macro_num);
    
    if (overdub_still_active) {
        uint32_t current_time = timer_read32();
        if (overdub_advanced_mode) {
            // INDEPENDENT MODE: Reset independent timing for next segment
            overdub_independent_start_time[macro_idx] = current_time;
            dprintf("dynamic macro: reset independent timing for continuing overdub on macro %d\n", macro_num);
        } else {
            // SYNCED MODE: Reset synced timing for next segment
            loop_start_time = current_time;
            dprintf("dynamic macro: reset synced timing for continuing overdub on macro %d\n", macro_num);
        }
        overdub_start_time = current_time;
    }
    
    dprintf("dynamic macro: completed %s overdub merge for macro %d\n", 
            overdub_advanced_mode ? "INDEPENDENT" : "SYNCED", macro_num);
    return true;
}

static void auto_segment_overdub_if_needed(uint8_t macro_idx) {
    uint8_t macro_num = macro_idx + 1;
    
    if (overdub_advanced_mode) {
        // ADVANCED MODE: Do NOT auto-segment based on parent macro restarts
        // Independent overdubs segment only when they naturally complete their own loops
        dprintf("dynamic macro: skipped auto-segment for INDEPENDENT overdub %d (parent macro restart ignored)\n", macro_num);
        return;
    } else {
        // ORIGINAL MODE: Auto-segment when parent macro restarts
        if (macro_in_overdub_mode[macro_idx] && 
            overdub_target_macro == macro_num && 
            overdub_temp_count[macro_idx] > 0) {
            
            overdub_merge_pending[macro_idx] = true;
            
            uint32_t current_time = timer_read32();
            loop_start_time = current_time;
            overdub_start_time = current_time;
            
            dprintf("dynamic macro: segmented SYNCED overdub for macro %d (temp_count=%d, continuous recording)\n", 
                    macro_num, overdub_temp_count[macro_idx]);
        }
    }
}

void get_overdub_space_info(uint8_t macro_num, uint32_t *main_bytes, uint32_t *temp_bytes, uint32_t *available_bytes) {
    if (macro_num < 1 || macro_num > MAX_MACROS) {
        *main_bytes = 0;
        *temp_bytes = 0;
        *available_bytes = 0;
        return;
    }
    
    uint8_t macro_idx = macro_num - 1;
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
    
    if (macro_start && macro_end_ptr) {
        *main_bytes = (*macro_end_ptr - macro_start) * sizeof(midi_event_t);
        *temp_bytes = overdub_temp_count[macro_idx] * sizeof(midi_event_t);
        *available_bytes = MACRO_BUFFER_SIZE - *main_bytes - *temp_bytes;
    } else {
        *main_bytes = 0;
        *temp_bytes = 0;
        *available_bytes = 0;
    }
}

static void process_pending_overdub_merge(uint8_t macro_idx) {
    if (!overdub_merge_pending[macro_idx]) {
        return; // No pending merge for this macro
    }
    
    uint8_t macro_num = macro_idx + 1;
    
    // Check if overdub is still active BEFORE merging
    bool overdub_still_active = (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num);
    
    dprintf("dynamic macro: processing pending merge for macro %d (overdub_still_active=%s)\n", 
            macro_num, overdub_still_active ? "true" : "false");
    
    // Perform the merge
    bool merge_success = merge_overdub_buffer(macro_idx);
    
    if (merge_success) {
        dprintf("dynamic macro: successfully merged overdub for macro %d\n", macro_num);
        
        // If overdub is still active after merge, we need to prepare for the next segment
        if (overdub_still_active) {
            // The merge function already reset timing, but we should verify recording is still active
            if (overdub_target_macro == macro_num && macro_in_overdub_mode[macro_idx]) {
                dprintf("dynamic macro: continuous overdub confirmed active for macro %d - ready for next segment\n", macro_num);
            } else {
                dprintf("dynamic macro: overdub state changed during merge for macro %d\n", macro_num);
            }
        }
    } else {
        dprintf("dynamic macro: failed to merge overdub for macro %d\n", macro_num);
    }
}

void record_early_overdub_event(uint8_t type, uint8_t channel, uint8_t note, uint8_t velocity) {
    // Find which macro should capture this event
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (capture_early_overdub_events[i] && early_overdub_count[i] < 32) {
            early_overdub_buffer[i][early_overdub_count[i]].type = type;
            early_overdub_buffer[i][early_overdub_count[i]].channel = channel;
            early_overdub_buffer[i][early_overdub_count[i]].note = note;
            early_overdub_buffer[i][early_overdub_count[i]].raw_travel = velocity;
            early_overdub_buffer[i][early_overdub_count[i]].timestamp = 0; // Will be placed at loop start
            early_overdub_count[i]++;

            dprintf("early overdub: recorded event type:%d ch:%d note:%d vel:%d for macro %d\n",
                    type, channel, note, velocity, i + 1);
            return; // Only capture in one macro
        }
    }
}


void dynamic_macro_play_overdub(uint8_t macro_num);

static void start_overdub_recording_advanced(uint8_t macro_num) {
    uint8_t macro_idx = macro_num - 1;

    // Snapshot overdub recording settings (only if not already set)
    snapshot_overdub_recording_settings(macro_num);

    // FIRST: Check if any OTHER macros have pending merges and force them
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (i != macro_idx && (overdub_merge_pending[i] || overdub_temp_count[i] > 0)) {
            if (overdub_merge_pending[i]) {
                bool merge_success = merge_overdub_buffer(i);
                if (merge_success) {
                    dprintf("dynamic macro: force-merged overdub for macro %d due to macro switch\n", i + 1);
                } else {
                    dprintf("dynamic macro: force-merge FAILED for macro %d due to macro switch - temp data cleared\n", i + 1);
                }
            } else if (overdub_temp_count[i] > 0) {
                clear_temp_overdub_buffer(i + 1);
                dprintf("dynamic macro: cleared orphaned temp events for macro %d due to macro switch\n", i + 1);
            }
        }
    }
	
		// Handle preroll transfer if we were collecting
	if (collecting_preroll && preroll_buffer_count > 0) {
		uint32_t current_time = timer_read32();
		uint32_t cutoff_time = current_time - PREROLL_TIME_MS;
		
		// Transfer recent preroll events to temp overdub buffer
		uint8_t oldest_idx = (preroll_buffer_index + PREROLL_BUFFER_SIZE - preroll_buffer_count) % PREROLL_BUFFER_SIZE;
		
		for (uint8_t j = 0; j < preroll_buffer_count; j++) {
			uint8_t idx = (oldest_idx + j) % PREROLL_BUFFER_SIZE;
			uint32_t event_time = preroll_start_time + preroll_buffer[idx].timestamp;
			
			if (event_time >= cutoff_time && has_overdub_space(macro_num)) {
				midi_event_t *write_pos = get_overdub_write_position(macro_num);
				if (write_pos) {
					*write_pos = preroll_buffer[idx];
					write_pos->timestamp = 0; // Place at independent loop start
					overdub_temp_count[macro_idx]++;
				}
			}
		}
		
		collecting_preroll = false;
		dprintf("dynamic macro: transferred %d preroll events to advanced overdub for macro %d\n", 
				overdub_temp_count[macro_idx], macro_num);
	}
    
    if (overdub_muted[macro_idx]) {
        overdub_muted[macro_idx] = false;
        overdub_mute_pending[macro_idx] = false;
        overdub_unmute_pending[macro_idx] = false;
        dprintf("dynamic macro: auto-unmuted overdub when starting ADVANCED recording for macro %d\n", macro_num);
        
        if (overdub_buffers[macro_idx] != NULL && 
            overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx] &&
            macro_playback[macro_idx].is_playing &&
            !overdub_playback[macro_idx].is_playing) {
            dynamic_macro_play_overdub(macro_num);
            dprintf("dynamic macro: started playing existing overdub content while ADVANCED recording for macro %d\n", macro_num);
        }
    }
    
    // Handle early overdub transfer
    if (capture_early_overdub_events[macro_idx] && early_overdub_count[macro_idx] > 0) {
        dprintf("dynamic macro: transferring %d early overdub events to temp overdub for macro %d\n", 
                early_overdub_count[macro_idx], macro_num);
        
        for (uint8_t i = 0; i < early_overdub_count[macro_idx]; i++) {
            if (has_overdub_space(macro_num)) {
                midi_event_t *write_pos = get_overdub_write_position(macro_num);
                if (write_pos) {
                    *write_pos = early_overdub_buffer[macro_idx][i];
                    overdub_temp_count[macro_idx]++;
                }
            }
        }
        
        capture_early_overdub_events[macro_idx] = false;
        early_overdub_count[macro_idx] = 0;
        memset(early_overdub_buffer[macro_idx], 0, sizeof(early_overdub_buffer[macro_idx]));
    }
    
    uint32_t current_time = timer_read32();
    
    // ADVANCED MODE: Set up completely independent timing
    overdub_independent_timer[macro_idx] = current_time;
    overdub_independent_start_time[macro_idx] = current_time;
    overdub_independent_waiting_for_gap[macro_idx] = false;
    overdub_independent_loop_length[macro_idx] = 0; // Will be set when recording ends
    
    // Common setup
    overdub_start_time = current_time;
    macro_in_overdub_mode[macro_idx] = true;
    current_macro_id = macro_num;
    macro_id = macro_num;
    recording_start_time = overdub_start_time;
    first_note_recorded = true;
    overdub_target_macro = macro_num;
    
    send_loop_message(overdub_start_recording_cc[macro_num - 1], 127);
    
    dprintf("dynamic macro: started INDEPENDENT overdub recording for macro %d (quantized)\n", macro_num);
}


void start_overdub_recording(uint8_t macro_num) {
    if (overdub_advanced_mode) {
        // ADVANCED MODE: Just add command to batch for quantized execution
        uint8_t playing_count = 0;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                playing_count++;
            }
        }
        
        if (playing_count > 0) {
            // Add command for quantized execution
            add_command_to_batch(CMD_ADVANCED_OVERDUB_REC, macro_num);
            dprintf("dynamic macro: queued ADVANCED overdub recording for macro %d\n", macro_num);
        } else {
            // No other macros playing - execute immediately
            start_overdub_recording_advanced(macro_num);
        }
        return;
    }
    
    // ORIGINAL MODE: Continue with existing logic
    // FIRST: Check if any OTHER macros have pending merges and force them
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (i != (macro_num - 1) && (overdub_merge_pending[i] || overdub_temp_count[i] > 0)) {
            if (overdub_merge_pending[i]) {
                bool merge_success = merge_overdub_buffer(i);
                if (merge_success) {
                    dprintf("dynamic macro: force-merged overdub for macro %d due to macro switch\n", i + 1);
                } else {
                    dprintf("dynamic macro: force-merge FAILED for macro %d due to macro switch - temp data cleared\n", i + 1);
                }
            } else if (overdub_temp_count[i] > 0) {
                clear_temp_overdub_buffer(i + 1);
                dprintf("dynamic macro: cleared orphaned temp events for macro %d due to macro switch\n", i + 1);
            }
        }
    }

    uint8_t macro_idx = macro_num - 1;

    // Snapshot overdub recording settings (only if not already set)
    snapshot_overdub_recording_settings(macro_num);

    if (overdub_muted[macro_idx]) {
        overdub_muted[macro_idx] = false;
        overdub_mute_pending[macro_idx] = false;
        overdub_unmute_pending[macro_idx] = false;
        dprintf("dynamic macro: auto-unmuted overdub when starting recording for macro %d\n", macro_num);
        
        if (overdub_buffers[macro_idx] != NULL && 
            overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx] &&
            macro_playback[macro_idx].is_playing &&
            !overdub_playback[macro_idx].is_playing) {
            dynamic_macro_play_overdub(macro_num);
            dprintf("dynamic macro: started playing existing overdub content while recording for macro %d\n", macro_num);
        }
    }
    
    // Handle early overdub transfer
    if (capture_early_overdub_events[macro_idx] && early_overdub_count[macro_idx] > 0) {
        dprintf("dynamic macro: transferring %d early overdub events to temp overdub for macro %d\n", 
                early_overdub_count[macro_idx], macro_num);
        
        for (uint8_t i = 0; i < early_overdub_count[macro_idx]; i++) {
            if (has_overdub_space(macro_num)) {
                midi_event_t *write_pos = get_overdub_write_position(macro_num);
                if (write_pos) {
                    *write_pos = early_overdub_buffer[macro_idx][i];
                    overdub_temp_count[macro_idx]++;
                }
            }
        }
        
        capture_early_overdub_events[macro_idx] = false;
        early_overdub_count[macro_idx] = 0;
        memset(early_overdub_buffer[macro_idx], 0, sizeof(early_overdub_buffer[macro_idx]));
    }
    
    uint32_t current_time = timer_read32();
    
    // ORIGINAL MODE: Use parent macro timing
    macro_playback_state_t *state = &macro_playback[macro_num - 1];
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    midi_event_t *macro_end = *get_macro_end_ptr(macro_num);
    
    float speed_factor = macro_speed_factor[macro_idx];
    uint32_t real_elapsed_since_playback_start = current_time - state->timer;
    
    uint32_t speed_adjusted_elapsed;
    if (speed_factor > 0.0f) {
        speed_adjusted_elapsed = (uint32_t)(real_elapsed_since_playback_start * speed_factor);
    } else {
        speed_adjusted_elapsed = real_elapsed_since_playback_start;
    }
    
    if (state->loop_length > 0) {
        loop_length = state->loop_length;
    } else {
        uint32_t max_timestamp = 0;
        if (macro_end > macro_start) {
            for (midi_event_t *event = macro_start; event < macro_end; event++) {
                if (event->timestamp > max_timestamp) {
                    max_timestamp = event->timestamp;
                }
            }
        }
        loop_length = max_timestamp + state->loop_gap_time;
        if (loop_length == 0 || loop_length > 60000) {
            loop_length = 2000;
        }
        state->loop_length = loop_length;
    }
    
    uint32_t position_in_loop = speed_adjusted_elapsed % loop_length;
    uint32_t real_time_offset_to_loop_start;
    if (speed_factor > 0.0f) {
        real_time_offset_to_loop_start = (uint32_t)(position_in_loop / speed_factor);
    } else {
        real_time_offset_to_loop_start = position_in_loop;
    }
    
    loop_start_time = current_time - real_time_offset_to_loop_start;
    
    dprintf("dynamic macro: started SYNCED overdub recording for macro %d\n", macro_num);
    
    // Common setup
    overdub_start_time = current_time;
    macro_in_overdub_mode[macro_num - 1] = true;
    current_macro_id = macro_num;
    macro_id = macro_num;
    recording_start_time = overdub_start_time;
    first_note_recorded = true;
    overdub_target_macro = macro_num;
    
    send_loop_message(overdub_start_recording_cc[macro_num - 1], 127);
}


void dynamic_macro_play_overdub(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) {
        return;
    }
    
    uint8_t macro_idx = macro_num - 1;
    
    // Only play if overdub exists and not muted
    if (overdub_buffers[macro_idx] != NULL && 
        overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx] &&
        !overdub_muted[macro_idx]) {
        
        macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
        overdub_state->current = overdub_buffers[macro_idx];
        overdub_state->end = overdub_buffer_ends[macro_idx];
        overdub_state->direction = +1;
        overdub_state->buffer_start = overdub_buffers[macro_idx];
        overdub_state->is_playing = true;
        overdub_state->waiting_for_loop_gap = false;
        overdub_state->next_event_time = 0;
        
        if (overdub_advanced_mode) {
            // ADVANCED MODE: Use independent timer and loop length
            overdub_independent_timer[macro_idx] = timer_read32();
            overdub_state->timer = overdub_independent_timer[macro_idx];
            overdub_state->loop_length = overdub_independent_loop_length[macro_idx];
            overdub_state->loop_gap_time = overdub_independent_gap_time[macro_idx];
            
            dprintf("dynamic macro: started INDEPENDENT overdub playback for macro %d (%lu ms loop)\n", 
                    macro_num, overdub_independent_loop_length[macro_idx]);
        } else {
            // ORIGINAL MODE: Sync with parent macro
            overdub_state->timer = timer_read32();
            // Keep existing loop_length and loop_gap_time from merge
            
            dprintf("dynamic macro: started SYNCED overdub playback for macro %d\n", macro_num);
        }
        
        if (!suppress_next_overdub_start_playing[macro_idx]) {
            send_loop_message(overdub_start_playing_cc[macro_num - 1], 127);
        } else {
            suppress_next_overdub_start_playing[macro_idx] = false;
        }
    }
}

void dynamic_macro_stop_overdub(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) {
        return;
    }
    
    uint8_t macro_idx = macro_num - 1;
    
    // Stop overdub playback
    if (overdub_playback[macro_idx].is_playing) {
        dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
        overdub_playback[macro_idx].is_playing = false;
        overdub_playback[macro_idx].current = NULL;
		send_loop_message(overdub_stop_playing_cc[macro_num - 1], 127);
        dprintf("dynamic macro: stopped overdub for macro %d\n", macro_num);
    }
}

void dynamic_macro_record_midi_event_overdub(uint8_t type, uint8_t channel, uint8_t note, uint8_t raw_travel) {
    if (overdub_target_macro == 0 || overdub_target_macro > MAX_MACROS) {
        return; // No valid target macro
    }
    
    // Check if we have space using byte-based collision detection
    if (!has_overdub_space(overdub_target_macro)) {
        dprintf("dynamic macro: overdub buffer full for macro %d (collision with main macro)\n", overdub_target_macro);
        return;
    }
    
    uint8_t macro_idx = overdub_target_macro - 1;
    
    // Check for independent overdub suspension (matching slave recording methodology)
    if (overdub_advanced_mode && overdub_independent_suspended[macro_idx]) {
        dprintf("dynamic macro: skipping overdub event - independent recording suspended for macro %d\n", 
                overdub_target_macro);
        return;
    }
    uint32_t now = timer_read32();
    uint32_t record_timestamp;
    
    if (overdub_advanced_mode) {
        // ADVANCED MODE: Use completely independent timing - no loop boundaries
        if (overdub_independent_start_time[macro_idx] == 0) {
            dprintf("ERROR: Independent start time not set for macro %d\n", overdub_target_macro);
            return;
        }
        
        uint32_t real_elapsed = now - overdub_independent_start_time[macro_idx];
        record_timestamp = real_elapsed;
        
        dprintf("dynamic macro: INDEPENDENT overdub recording at time %lu ms (raw elapsed, no boundaries)\n", record_timestamp);
    } else {
        // ORIGINAL MODE: Use parent macro timing with loop boundaries
        if (loop_length == 0) {
            dprintf("ERROR: Loop length is zero, cannot record overdub\n");
            return;
        }
        
        float speed_factor = macro_speed_factor[macro_idx];
        uint32_t real_elapsed = now - loop_start_time;
        
        // Apply speed factor: if macro plays at 2x speed, 1 second real time = 2 seconds loop time
        uint32_t speed_adjusted_elapsed;
        if (speed_factor > 0.0f) {
            speed_adjusted_elapsed = (uint32_t)(real_elapsed * speed_factor);
        } else {
            speed_adjusted_elapsed = real_elapsed; // Fallback to real time
        }
        
        uint32_t position_in_loop = speed_adjusted_elapsed % loop_length;
        
        // AUTO-PREROLL CHECK: If temp buffer is empty and first note is within 100ms of loop end
        bool temp_overdub_is_empty = (overdub_temp_count[macro_idx] == 0);
        bool is_first_overdub_note = temp_overdub_is_empty;
        
        uint32_t time_to_loop_end = loop_length - position_in_loop;
        bool near_loop_end = (time_to_loop_end <= 100); // 100ms threshold
        
        if (is_first_overdub_note && near_loop_end) {
            // Auto-preroll: place at loop start (timestamp 0)
            record_timestamp = 0;
            dprintf("dynamic macro: auto-preroll activated for SYNCED macro %d (first note %lu ms before loop end, placing at loop start)\n", 
                    overdub_target_macro, time_to_loop_end);
        } else {
            // Normal recording: use actual position
            record_timestamp = position_in_loop;
        }
        
        dprintf("dynamic macro: SYNCED overdub recording at loop position %lu ms (speed: %.2fx, real elapsed: %lu ms)\n", 
                position_in_loop, speed_factor, real_elapsed);
    }
    
    // Get the backward write position
    midi_event_t *write_pos = get_overdub_write_position(overdub_target_macro);
    if (!write_pos) {
        dprintf("ERROR: Could not get overdub write position for macro %d\n", overdub_target_macro);
        return;
    }
    
    // Write the event with determined timestamp
    write_pos->type = type;
    write_pos->channel = channel;
    write_pos->note = note;
    write_pos->raw_travel = raw_travel;
    write_pos->timestamp = record_timestamp;

    // Increment the count for this macro
    overdub_temp_count[macro_idx]++;

    dprintf("dynamic macro: recorded %s overdub event type:%d ch:%d note:%d raw:%d at timestamp %lu ms (temp_count now %d)\n",
            overdub_advanced_mode ? "INDEPENDENT" : "SYNCED", type, channel, note, raw_travel, record_timestamp, overdub_temp_count[macro_idx]);
}


// Helper function to find the next event timestamp after current position
static uint32_t find_next_event_timestamp_in_loop(uint8_t macro_num, uint32_t current_position) {
    uint8_t macro_idx = macro_num - 1;
    uint32_t next_timestamp = UINT32_MAX;
    
    // Check main macro events
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
    
    if (macro_start && macro_end_ptr) {
        for (midi_event_t *event = macro_start; event < *macro_end_ptr; event++) {
            if (event->timestamp > current_position && event->timestamp < next_timestamp) {
                next_timestamp = event->timestamp;
            }
        }
    }
    
    // Check existing overdub events (permanent overdub buffer)
    if (overdub_buffers[macro_idx] != NULL && overdub_buffer_ends[macro_idx] != NULL) {
        for (midi_event_t *event = overdub_buffers[macro_idx]; event < overdub_buffer_ends[macro_idx]; event++) {
            if (event->timestamp > current_position && event->timestamp < next_timestamp) {
                next_timestamp = event->timestamp;
            }
        }
    }
    
    // Check temp overdub events (currently being recorded)
    if (overdub_temp_count[macro_idx] > 0) {
        midi_event_t *temp_start = get_overdub_read_start(macro_num);
        if (temp_start != NULL) {
            for (uint16_t i = 0; i < overdub_temp_count[macro_idx]; i++) {
                if (temp_start[i].timestamp > current_position && temp_start[i].timestamp < next_timestamp) {
                    next_timestamp = temp_start[i].timestamp;
                }
            }
        }
    }
    
    // If no events found after current position, use the beginning of next loop cycle
    if (next_timestamp == UINT32_MAX) {
        // Find the first event in the next loop cycle
        uint32_t loop_length = macro_playback[macro_idx].loop_length;
        if (loop_length > 0) {
            uint32_t next_loop_start = ((current_position / loop_length) + 1) * loop_length;
            
            // Look for the first event in the main macro
            for (midi_event_t *event = macro_start; event < *macro_end_ptr; event++) {
                uint32_t next_cycle_timestamp = next_loop_start + event->timestamp;
                if (next_cycle_timestamp < next_timestamp) {
                    next_timestamp = next_cycle_timestamp;
                }
            }
            
            // Look for the first event in existing overdub
            if (overdub_buffers[macro_idx] != NULL && overdub_buffer_ends[macro_idx] != NULL) {
                for (midi_event_t *event = overdub_buffers[macro_idx]; event < overdub_buffer_ends[macro_idx]; event++) {
                    uint32_t next_cycle_timestamp = next_loop_start + event->timestamp;
                    if (next_cycle_timestamp < next_timestamp) {
                        next_timestamp = next_cycle_timestamp;
                    }
                }
            }
            
            // If still no events found, just use the start of next loop
            if (next_timestamp == UINT32_MAX) {
                next_timestamp = next_loop_start;
            }
        } else {
            // No loop length available, just use current position + small offset
            next_timestamp = current_position + 100; // 100ms later
        }
    }
    
    return next_timestamp;
}

// REPLACE the entire end_overdub_recording_deferred_advanced function with this:
static void end_overdub_recording_deferred_advanced(uint8_t macro_num) {
    if (!overdub_advanced_mode || macro_num < 1 || macro_num > MAX_MACROS) {
        return;
    }
    uint8_t macro_idx = macro_num - 1;
    uint32_t current_time = timer_read32();
    
    if (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num) {
        // Use suspension time if available (matching slave recording methodology)
        uint32_t effective_end_time;
        if (overdub_independent_suspended[macro_idx]) {
            effective_end_time = overdub_independent_suspension_time[macro_idx];
            dprintf("dynamic macro: using suspension time %lu for independent overdub length calculation\n", 
                    effective_end_time);
        } else {
            effective_end_time = current_time;
            dprintf("dynamic macro: using execution time %lu for independent overdub length calculation\n", 
                    effective_end_time);
        }
        
        // Calculate independent loop length using effective end time
        uint32_t total_recording_duration = effective_end_time - overdub_independent_start_time[macro_idx];
            // Unsynced mode - use original duration
            overdub_independent_loop_length[macro_idx] = total_recording_duration;
            dprintf("dynamic macro: unsynced mode - using original duration %lu ms for independent overdub %d\n", 
                    total_recording_duration, macro_num);
        
        
        // Calculate gap time based on last event in temp buffer
        uint32_t last_event_time = 0;
        if (overdub_temp_count[macro_idx] > 0) {
            midi_event_t *temp_start = get_overdub_read_start(macro_num);
            if (temp_start != NULL) {
                // Find latest timestamp in temp events (they're stored backwards)
                for (uint16_t i = 0; i < overdub_temp_count[macro_idx]; i++) {
                    if (temp_start[i].timestamp > last_event_time) {
                        last_event_time = temp_start[i].timestamp;
                    }
                }
            }
        }
        
        // Adjust gap time to achieve the quantized length
        if (overdub_independent_loop_length[macro_idx] > last_event_time) {
            overdub_independent_gap_time[macro_idx] = overdub_independent_loop_length[macro_idx] - last_event_time;
        } else {
            overdub_independent_gap_time[macro_idx] = 100; // Minimum gap
        }
        
        dprintf("dynamic macro: independent overdub final loop length %lu ms, gap %lu ms\n", 
                overdub_independent_loop_length[macro_idx], overdub_independent_gap_time[macro_idx]);
				
		        
        overdub_target_macro = 0;
        macro_in_overdub_mode[macro_num - 1] = false;
        current_macro_id = 0;
        macro_id = 0;
        stop_dynamic_macro_recording();
        
        // SET FLAG FOR DEFERRED MERGE
        if (overdub_temp_count[macro_idx] > 0) {
            overdub_merge_pending[macro_idx] = true;
        }
        
        send_loop_message(overdub_stop_recording_cc[macro_num - 1], 127);
        suppress_next_overdub_start_playing[macro_num - 1] = true;
        
        dprintf("dynamic macro: ended %s overdub recording for macro %d\n", 
                overdub_advanced_mode ? "independent" : "synced", macro_num);
        
        // Add this after the merge in end_overdub_recording_deferred_advanced:
        if (overdub_temp_count[macro_idx] > 0) {
            merge_overdub_buffer(macro_idx);
            
            // Auto-start playback of the newly recorded content
            if (overdub_buffers[macro_idx] != NULL && 
                overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx]) {
                
                overdub_muted[macro_idx] = false; // Ensure it's unmuted
                
                if (!overdub_playback[macro_idx].is_playing) {
                    dynamic_macro_play_overdub(macro_num);
                    dprintf("dynamic macro: auto-started independent overdub playback after recording for macro %d\n", macro_num);
                }
            }
        }
    } else if (overdub_merge_pending[macro_idx]) {
        // Just merge pending events
        merge_overdub_buffer(macro_idx);
        dprintf("dynamic macro: manually merged pending independent overdub for macro %d\n", macro_num);
    }
}

void end_overdub_recording_deferred(uint8_t macro_num) {
    if (overdub_advanced_mode) {
        // ADVANCED MODE: Just add command to batch for quantized execution
        uint8_t playing_count = 0;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                playing_count++;
            }
        }
        
        if (playing_count > 0) {
            // Add command for quantized execution
            add_command_to_batch(CMD_ADVANCED_OVERDUB_END, macro_num);
            dprintf("dynamic macro: queued ADVANCED overdub end for macro %d\n", macro_num);
        } else {
            // No other macros playing - execute immediately
            end_overdub_recording_deferred_advanced(macro_num);
        }
        return;
    }
    
    // ORIGINAL MODE: Continue with existing logic
    uint8_t macro_idx = macro_num - 1;
    uint32_t current_time = timer_read32();
    uint32_t current_position_in_loop = 0;
    
    // ORIGINAL MODE: Use parent macro timing for note-off placement
    if (loop_length > 0 && loop_start_time > 0) {
        float speed_factor = macro_speed_factor[macro_idx];
        uint32_t real_elapsed = current_time - loop_start_time;
        
        if (speed_factor > 0.0f) {
            uint32_t speed_adjusted_elapsed = (uint32_t)(real_elapsed * speed_factor);
            current_position_in_loop = speed_adjusted_elapsed % loop_length;
        } else {
            current_position_in_loop = real_elapsed % loop_length;
        }
    }
    
    // Record note-offs for currently held live notes
    for (uint8_t note = 0; note < 128; note++) {
        for (uint8_t channel = 0; channel < 16; channel++) {
            if (is_live_note_active(channel, note)) {
                if (has_overdub_space(macro_num)) {
                    midi_event_t *write_pos = get_overdub_write_position(macro_num);
                    if (write_pos) {
                        // Original mode: use next event timestamp with wrapping
                        uint32_t next_event_timestamp = find_next_event_timestamp_in_loop(macro_num, current_position_in_loop);
                        uint32_t noteoff_timestamp = next_event_timestamp % loop_length;

                        write_pos->type = MIDI_EVENT_NOTE_OFF;
                        write_pos->channel = channel;
                        write_pos->note = note;
                        write_pos->raw_travel = 64;
                        write_pos->timestamp = noteoff_timestamp;

                        overdub_temp_count[macro_idx]++;
                    }
                }
            }
        }
    }
    
    // STOP RECORDING IMMEDIATELY
    overdub_target_macro = 0;
    macro_in_overdub_mode[macro_num - 1] = false;
    current_macro_id = 0;
    macro_id = 0;
    stop_dynamic_macro_recording();
    
    // SET FLAG FOR DEFERRED MERGE
    if (overdub_temp_count[macro_idx] > 0) {
        overdub_merge_pending[macro_idx] = true;
    }
    
    send_loop_message(overdub_stop_recording_cc[macro_num - 1], 127);
    suppress_next_overdub_start_playing[macro_num - 1] = true;
    
    dprintf("dynamic macro: ended SYNCED overdub recording for macro %d\n", macro_num);
}

static void execute_command_batch(void) {
    dprintf("dynamic macro: Executing command batch with %d commands\n", command_batch_count);
    
// First, process all STOP commands
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == CMD_STOP && !command_batch[i].processed) {
            uint8_t target = command_batch[i].macro_id;
            uint8_t target_idx = target - 1;
            macro_main_muted[target_idx] = false;
            
            // Check if this macro is in overdub mode
            if (target <= MAX_MACROS && macro_in_overdub_mode[target_idx] && overdub_target_macro == target) {
                // End overdub recording - route to appropriate function based on mode
                if (overdub_advanced_mode) {
                    end_overdub_recording_deferred_advanced(target);
                    dprintf("dynamic macro: batch ended ADVANCED overdub recording for macro %d\n", target);
                } else {
                    end_overdub_recording_deferred(target);
                    dprintf("dynamic macro: batch ended overdub recording for macro %d\n", target);
                }
            } else if (macro_id > 0 && macro_id == target) {
                // Currently recording this macro - stop recording
                midi_event_t *macro_start = get_macro_buffer(macro_id);
                midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_id);
                force_clear_all_live_notes();
                dynamic_macro_record_end(macro_start, macro_pointer, +1, macro_end_ptr, &recording_start_time);
                
                // Clear the suspended recording flag for this macro
                recording_suspended[target - 1] = false;
                
                if (target <= MAX_MACROS) {
                    uint8_t target_idx = target - 1;
                    macro_playback_state_t *state = &macro_playback[target_idx];
                    
                    if (*macro_end_ptr > macro_start) {
                        // Find max timestamp in the recorded events
                        uint32_t max_timestamp = 0;
                        for (midi_event_t *event = macro_start; event < *macro_end_ptr; event++) {
                            if (event->timestamp > max_timestamp) {
                                max_timestamp = event->timestamp;
                            }
                        }
                        
                        // Store loop timing
                        state->loop_length = max_timestamp + state->loop_gap_time;
                        
                        // Pre-initialize global loop timing variables
                        uint32_t current_time = timer_read32();
                        
                        // If we immediately start playback, the position will be at the beginning
                        loop_start_time = current_time;
                        loop_length = state->loop_length;
                        
                        dprintf("dynamic macro: immediately calculated loop_length %lu ms for slave macro %d\n", 
                                state->loop_length, target);
                    }
                }
                
                // Check if we already have a play command for this macro
                bool play_cmd_exists = false;
                for (uint8_t j = 0; j < command_batch_count; j++) {
                    if (j != i && command_batch[j].command_type == CMD_PLAY && 
                        command_batch[j].macro_id == target) {
                        play_cmd_exists = true;
                        break;
                    }
                }
                
                // Add play command if it doesn't exist and the macro isn't empty
                if (!is_macro_empty && !play_cmd_exists) {
                    add_command_to_batch(CMD_PLAY, target);
                }
                
                // Reset the recording state
                macro_id = 0;
                stop_dynamic_macro_recording();
                dprintf("dynamic macro: batch stopped recording of macro %d\n", target);
            } else if (target <= MAX_MACROS && macro_playback[target_idx].is_playing) {
                // Stop playback of this macro
                dynamic_macro_cleanup_notes_for_state(&macro_playback[target_idx]);
                macro_playback[target_idx].is_playing = false;
                randomize_order();
                macro_playback[target_idx].current = NULL;
                
                if (overdub_advanced_mode) {
                    // In advanced mode: NEVER touch the overdub when stopping main macro
                    dprintf("dynamic macro: advanced mode stopped main macro %d only (overdub untouched)\n", target);
                } else {
                    // Original behavior for non-advanced mode: check if we should keep overdub
                    bool keep_overdub = false;
                    
                    // Check for CMD_PLAY_OVERDUB_ONLY commands for this macro (processed or unprocessed)
                    for (uint8_t j = 0; j < command_batch_count; j++) {
                        if (command_batch[j].command_type == CMD_PLAY_OVERDUB_ONLY && 
                            command_batch[j].macro_id == target) {
                            keep_overdub = true;
                            dprintf("dynamic macro: found CMD_PLAY_OVERDUB_ONLY for macro %d - keeping overdub\n", target);
                            break;
                        }
                    }
                    
                    // Also check pending unmute flags as another indicator to keep overdub
                    if (overdub_unmute_pending[target_idx]) {
                        keep_overdub = true;
                        dprintf("dynamic macro: overdub_unmute_pending for macro %d - keeping overdub\n", target);
                    }
                    
                    if (!keep_overdub && overdub_playback[target_idx].is_playing) {
                        dynamic_macro_cleanup_notes_for_state(&overdub_playback[target_idx]);
                        overdub_playback[target_idx].is_playing = false;
                        overdub_playback[target_idx].current = NULL;
                        dprintf("dynamic macro: also stopped overdub for macro %d (linked stop)\n", target);
                    } else if (keep_overdub) {
                        dprintf("dynamic macro: kept overdub playing for macro %d (solo function)\n", target);
                    }
                }
                
                dprintf("dynamic macro: batch stopped playback of macro %d\n", target);
            }
            
            command_batch[i].processed = true;
        }
    }
    // Next, process all RECORD commands
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == CMD_RECORD && !command_batch[i].processed) {
            uint8_t target = command_batch[i].macro_id;            
            if (macro_id == 0) { // Only start if not already recording
                // End any overdub recording on all macros before starting new recording
                for (uint8_t j = 0; j < MAX_MACROS; j++) {
                    if (macro_in_overdub_mode[j]) {
                        // End overdub recording for this macro - route based on mode
                        if (overdub_advanced_mode) {
                            end_overdub_recording_deferred_advanced(j + 1);
                        } else {
                            end_overdub_recording_deferred(j + 1);
                        }
                        
                        // Reset overdub state
                        macro_in_overdub_mode[j] = false;
                        dprintf("dynamic macro: ended overdub recording for macro %d (new recording starting)\n", j + 1);
                    }
                }
                
                // Reset global overdub state
                overdub_target_macro = 0;
                
                // Start new recording
                macro_id = target;
                midi_event_t *macro_start = get_macro_buffer(macro_id);
                macro_pointer = macro_start;
                recording_start_time = timer_read32();
                first_note_recorded = true;
                
                // Use collected preroll events if we were collecting them
                if (collecting_preroll) {
                    dynamic_macro_actual_start(&recording_start_time);
                }
                
                setup_dynamic_macro_recording(macro_id, macro_buffer, NULL, (void**)&macro_pointer, &recording_start_time);
                dprintf("dynamic macro: batch started recording of macro %d\n", target);
                 
            }
            
            command_batch[i].processed = true;
            randomize_order();
        }
    }
    
    // Next, process all PLAY commands
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == CMD_PLAY && !command_batch[i].processed) {
            uint8_t target = command_batch[i].macro_id;
            uint8_t target_idx = target - 1;
            
            // Check if macro was previously muted (ghost muted)
            bool was_muted = macro_main_muted[target_idx];
            macro_main_muted[target_idx] = false;
            
            // Check if we should skip autoplay for this macro due to double-tap
            if (skip_autoplay_for_macro[target_idx]) {
                dprintf("dynamic macro: skipping play command for macro %d due to double-tap\n", target);
                skip_autoplay_for_macro[target_idx] = false; // Reset the flag
                command_batch[i].processed = true;
                continue; // Skip to next command
            }
            
            // Start playback for this macro
            midi_event_t *macro_start = get_macro_buffer(target);
            midi_event_t **macro_end_ptr = get_macro_end_ptr(target);
            
            if (macro_start && macro_end_ptr && *macro_end_ptr && macro_start != *macro_end_ptr) {
                // Only play if the macro has content
                if (!macro_playback[target_idx].is_playing || was_muted) {
                    // If it was muted and still playing, reset position to 0
                    if (was_muted && macro_playback[target_idx].is_playing) {
                        macro_playback[target_idx].current = macro_playback[target_idx].buffer_start;
                        macro_playback[target_idx].timer = timer_read32();
                        macro_playback[target_idx].next_event_time = macro_playback[target_idx].timer + 
                                                                   macro_playback[target_idx].current->timestamp;
                        macro_playback[target_idx].waiting_for_loop_gap = false;
                        
                        // Clean up any hanging notes before restart
                        cleanup_notes_from_macro(target);
                        
                        dprintf("dynamic macro: reset muted macro %d to position 0\n", target);
                    } else {
                        // Normal start from stopped state
                        dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                    }
                    
                    dprintf("dynamic macro: batch started playback of macro %d\n", target);
                    
                    // Check if we should enter overdub mode for this macro
                    if (macro_in_overdub_mode[target_idx]) {
                        // Route to appropriate function based on mode
                        if (overdub_advanced_mode) {
                            start_overdub_recording_advanced(target);
                        } else {
                            start_overdub_recording(target);
                        }
                        dprintf("dynamic macro: batch started overdub for macro %d\n", target);
                    }
                }
            }
			
			// Add this after the main macro restart logic in CMD_PLAY section
			if (overdub_advanced_mode && target <= MAX_MACROS) {
				uint8_t macro_idx = target - 1;
				
				// If restarting this macro, also reset its independent overdub timer if it exists
				if (overdub_buffers[macro_idx] != NULL && 
					overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx]) {
					
					// Reset the independent timer for this macro's overdub
					overdub_independent_timer[macro_idx] = timer_read32();
					
					// If the overdub is currently playing, update its timer too
					if (overdub_playback[macro_idx].is_playing) {
						overdub_playback[macro_idx].timer = overdub_independent_timer[macro_idx];
						overdub_playback[macro_idx].next_event_time = 0; // Force recalculation
					}
					
					dprintf("dynamic macro: reset independent timer for macro %d during parent restart\n", target);
				}
			}
            
            command_batch[i].processed = true;
        }
    }
    
// Replace the CMD_PLAY_MUTED section with this:
for (uint8_t i = 0; i < command_batch_count; i++) {
    if (command_batch[i].command_type == CMD_PLAY_MUTED && !command_batch[i].processed) {
        uint8_t target = command_batch[i].macro_id;
        uint8_t target_idx = target - 1;
        
        if (overdub_advanced_mode) {
            // In advanced mode: just mute the main macro, no playback
            macro_main_muted[target_idx] = true;
            cleanup_notes_from_macro(target);
            dprintf("dynamic macro: batch applied advanced mute to macro %d\n", target);
        } else {
            // Original behavior for non-advanced mode
            // First, end recording if this macro is currently being recorded
            if (macro_id == target) {
                midi_event_t *rec_start = get_macro_buffer(target);
                midi_event_t **rec_end_ptr = get_macro_end_ptr(target);
                
                dynamic_macro_record_end(rec_start, macro_pointer, +1, rec_end_ptr, &recording_start_time);
                macro_id = 0;
                stop_dynamic_macro_recording();
                
                dprintf("dynamic macro: batch ended recording for macro %d\n", target);
            }
            
            // Start muted playback for this macro
            midi_event_t *macro_start = get_macro_buffer(target);
            midi_event_t **macro_end_ptr = get_macro_end_ptr(target);
            
            if (macro_start && macro_end_ptr && *macro_end_ptr && macro_start != *macro_end_ptr) {
                // Only play if the macro has content
                if (!macro_playback[target_idx].is_playing) {
                    dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                    
                    // IMMEDIATELY set mute flag - this is the key difference from CMD_PLAY
                    macro_main_muted[target_idx] = true;
                    
                    // Start overdub recording - route based on mode
                    if (overdub_advanced_mode) {
                        start_overdub_recording_advanced(target);
                    } else {
                        start_overdub_recording(target);
                    }
                    
                    dprintf("dynamic macro: batch started muted playback with overdub for macro %d\n", target);
                }
            }
        }
        
        command_batch[i].processed = true;
    }
}

// Replace the CMD_PLAY_OVERDUB_ONLY section with this:
for (uint8_t i = 0; i < command_batch_count; i++) {
    if (command_batch[i].command_type == CMD_PLAY_OVERDUB_ONLY && !command_batch[i].processed) {
        uint8_t target = command_batch[i].macro_id;
        uint8_t target_idx = target - 1;
        
        if (overdub_advanced_mode) {
            // In advanced mode: stop the main macro like CMD_STOP and play overdub
            if (target <= MAX_MACROS && macro_playback[target_idx].is_playing) {
                // Stop playback of main macro
                dynamic_macro_cleanup_notes_for_state(&macro_playback[target_idx]);
                macro_playback[target_idx].is_playing = false;
                randomize_order();
                macro_playback[target_idx].current = NULL;
                dprintf("dynamic macro: advanced mode stopped main macro %d for overdub-only\n", target);
            }
            
            // Start overdub playback
            if (overdub_buffers[target_idx] != NULL && overdub_buffer_ends[target_idx] != overdub_buffers[target_idx]) {
                // Make sure the overdub is unmuted
                overdub_muted[target_idx] = false;
                
                // Set up overdub playback
                macro_playback_state_t *overdub_state = &overdub_playback[target_idx];
                overdub_state->current = overdub_buffers[target_idx];
                overdub_state->end = overdub_buffer_ends[target_idx];
                overdub_state->direction = +1;
                overdub_state->timer = timer_read32();
                overdub_state->buffer_start = overdub_buffers[target_idx];
                overdub_state->is_playing = true;
                overdub_state->waiting_for_loop_gap = false;
                overdub_state->next_event_time = 0;
                send_loop_message(overdub_start_playing_cc[target - 1], 127);
                dprintf("dynamic macro: advanced mode started overdub-only playback for macro %d\n", target);
            }
        } else {
            // Original behavior for non-advanced mode
            // Start playback for just the overdub
            if (overdub_buffers[target_idx] != NULL && overdub_buffer_ends[target_idx] != overdub_buffers[target_idx]) {
                // Make sure the overdub is unmuted
                overdub_muted[target_idx] = false;
                
                // Set up overdub playback
                macro_playback_state_t *overdub_state = &overdub_playback[target_idx];
                overdub_state->current = overdub_buffers[target_idx];
                overdub_state->end = overdub_buffer_ends[target_idx];
                overdub_state->direction = +1;
                overdub_state->timer = timer_read32();
                overdub_state->buffer_start = overdub_buffers[target_idx];
                overdub_state->is_playing = true;
                overdub_state->waiting_for_loop_gap = false;
                overdub_state->next_event_time = 0;
                send_loop_message(overdub_start_playing_cc[target - 1], 127);
                dprintf("dynamic macro: started overdub-only playback for macro %d\n", target);
            }
        }
        
        command_batch[i].processed = true;
        randomize_order();
    }
}

// CMD_GHOST_MUTE section stays the same (already just sets mute)
for (uint8_t i = 0; i < command_batch_count; i++) {
    if (command_batch[i].command_type == CMD_GHOST_MUTE && !command_batch[i].processed) {
        uint8_t target = command_batch[i].macro_id;
        uint8_t target_idx = target - 1;
        
        // Set the main macro to muted (this happens at loop trigger)
        macro_main_muted[target_idx] = true;
        cleanup_notes_from_macro(target);
        
        dprintf("dynamic macro: batch applied ghost mute to macro %d\n", target);
        
        command_batch[i].processed = true;
    }
}

// Replace the CMD_OVERDUB_AFTER_MUTE section with this:
for (uint8_t i = 0; i < command_batch_count; i++) {
    if (command_batch[i].command_type == CMD_OVERDUB_AFTER_MUTE && !command_batch[i].processed) {
        uint8_t target = command_batch[i].macro_id;
        uint8_t target_idx = target - 1;
        
        if (overdub_advanced_mode) {
            // In advanced mode: just mute the main macro
            macro_main_muted[target_idx] = true;
            cleanup_notes_from_macro(target);
            dprintf("dynamic macro: advanced mode applied mute instead of overdub after mute for macro %d\n", target);
        } else {
            // Original behavior for non-advanced mode
            // Start overdub recording (this happens after the macro is ghost muted)
            if (macro_playback[target_idx].is_playing && macro_main_muted[target_idx]) {
                // Route to appropriate function based on mode
                if (overdub_advanced_mode) {
                    start_overdub_recording_advanced(target);
                } else {
                    start_overdub_recording(target);
                }
                dprintf("dynamic macro: batch started overdub recording for ghost muted macro %d\n", target);
            }
        }
        
        command_batch[i].processed = true;
    }
}
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == CMD_OVERDUB_AFTER_MUTE && !command_batch[i].processed) {
            uint8_t target = command_batch[i].macro_id;
            uint8_t target_idx = target - 1;
            
            // Start overdub recording (this happens after the macro is ghost muted)
            if (macro_playback[target_idx].is_playing && macro_main_muted[target_idx]) {
                // Route to appropriate function based on mode
                if (overdub_advanced_mode) {
                    start_overdub_recording_advanced(target);
                } else {
                    start_overdub_recording(target);
                }
                dprintf("dynamic macro: batch started overdub recording for ghost muted macro %d\n", target);
            }
            
            command_batch[i].processed = true;
        }
    }

// Process ADVANCED_OVERDUB_REC commands (only in advanced mode)
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == CMD_ADVANCED_OVERDUB_REC && !command_batch[i].processed) {
            uint8_t target = command_batch[i].macro_id;
            start_overdub_recording_advanced(target);
            command_batch[i].processed = true;
            dprintf("dynamic macro: batch executed ADVANCED overdub recording for macro %d\n", target);
        }
    }

    // Process ADVANCED_OVERDUB_END commands (only in advanced mode)
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].command_type == CMD_ADVANCED_OVERDUB_END && !command_batch[i].processed) {
            uint8_t target = command_batch[i].macro_id;
            end_overdub_recording_deferred_advanced(target);
            command_batch[i].processed = true;
            dprintf("dynamic macro: batch executed ADVANCED overdub end for macro %d\n", target);
        }
    }
    
    // Clear the batch after processing all commands
    clear_command_batch();
}


static void check_loop_trigger(void) {
    uint32_t current_time = timer_read32();
    
    if (overdub_advanced_mode) {
        // ===================================================================
        // ADVANCED MODE: Independent overdubs with synchronized restarts
        // ===================================================================
        dprintf("dynamic macro: Loop trigger in ADVANCED mode\n");
        
        // PHASE 1: CHECK ALL RESTART CONDITIONS
        bool main_macro_should_restart[MAX_MACROS] = {false, false, false, false};
        bool overdub_should_restart[MAX_MACROS] = {false, false, false, false};
        
        // Check main macros for restart conditions
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing) {
                uint32_t threshold = calculate_restart_proximity_threshold(i);
                float speed_factor = macro_speed_factor[i];
                
                if (speed_factor <= 0.0f) continue;
                
                uint32_t real_loop_duration = (uint32_t)(macro_playback[i].loop_length / speed_factor);
                
                if (macro_playback[i].waiting_for_loop_gap) {
                    uint32_t time_to_restart = 0;
                    if (macro_playback[i].next_event_time > current_time) {
                        time_to_restart = macro_playback[i].next_event_time - current_time;
                    }
                    if (time_to_restart <= threshold) {
                        main_macro_should_restart[i] = true;
                    }
                } else {
                    uint32_t elapsed_since_start = current_time - macro_playback[i].timer;
                    uint32_t position_in_real_loop = elapsed_since_start % real_loop_duration;
                    uint32_t time_to_real_end = real_loop_duration - position_in_real_loop;
                    
                    if (time_to_real_end <= threshold) {
                        main_macro_should_restart[i] = true;
                    }
                }
            }
        }
        
        // Check independent overdubs for restart conditions
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (overdub_playback[i].is_playing && 
                overdub_buffers[i] != NULL && 
                overdub_independent_loop_length[i] > 0) {
                
                uint32_t threshold = calculate_restart_proximity_threshold(i);
                uint32_t overdub_real_loop_duration = overdub_independent_loop_length[i];
                
                if (overdub_playback[i].waiting_for_loop_gap) {
                    uint32_t time_to_restart = 0;
                    if (overdub_playback[i].next_event_time > current_time) {
                        time_to_restart = overdub_playback[i].next_event_time - current_time;
                    }
                    if (time_to_restart <= threshold) {
                        overdub_should_restart[i] = true;
                    }
                } else {
                    uint32_t elapsed_since_overdub_start = current_time - overdub_independent_timer[i];
                    uint32_t position_in_overdub_loop = elapsed_since_overdub_start % overdub_real_loop_duration;
                    uint32_t time_to_overdub_end = overdub_real_loop_duration - position_in_overdub_loop;
                    
                    if (time_to_overdub_end <= threshold) {
                        overdub_should_restart[i] = true;
                    }
                }
            }
        }
        
        // PHASE 2: EXECUTE RESTARTS SIMULTANEOUSLY
        uint32_t restart_time = timer_read32();
        
        // Restart main macros
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (main_macro_should_restart[i]) {
                float speed_factor = macro_speed_factor[i];
                
                macro_playback[i].current = macro_playback[i].buffer_start;
                macro_playback[i].timer = restart_time;
                
                if (speed_factor > 0.0f) {
                    uint32_t adjusted_timestamp = (uint32_t)(macro_playback[i].current->timestamp / speed_factor);
                    macro_playback[i].next_event_time = restart_time + adjusted_timestamp;
                } else {
                    macro_playback[i].next_event_time = UINT32_MAX;
                }
                
                macro_playback[i].waiting_for_loop_gap = false;
                cleanup_notes_from_macro(i + 1);
                
                if (sync_midi_mode) {
                    if (alternate_restart_mode) {
                        send_loop_message(loop_stop_playing_cc[i], 127);
                        send_loop_message(loop_start_playing_cc[i], 127);
                    } else {
                        send_loop_message(loop_restart_cc[i], 127);
                    }
                }
                dprintf("dynamic macro: restarted main macro %d at synchronized time\n", i + 1);
            }
        }
        
        // Restart independent overdubs
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (overdub_should_restart[i]) {
                cleanup_notes_from_macro(i + 1 + MAX_MACROS);
                
                if (sample_mode_active) {
                    overdub_playback[i].is_playing = false;
                    overdub_playback[i].current = NULL;
                    overdub_playback[i].waiting_for_loop_gap = false;
                    dprintf("dynamic macro: one-shot end for independent overdub %d\n", i + 1);
                    continue;
                }
				
			if (sync_midi_mode && overdub_advanced_mode) {
				if (alternate_restart_mode) {
					send_loop_message(overdub_stop_playing_cc[i], 127);
					send_loop_message(overdub_start_playing_cc[i], 127);
				} else {
					send_loop_message(overdub_restart_cc[i], 127);
				}
			}
                
                overdub_playback[i].current = overdub_buffers[i];
                overdub_independent_timer[i] = restart_time;
                overdub_playback[i].timer = restart_time;
                overdub_playback[i].next_event_time = restart_time + overdub_playback[i].current->timestamp;
                overdub_playback[i].waiting_for_loop_gap = false;
                
                dprintf("dynamic macro: restarted independent overdub %d at synchronized time\n", i + 1);
            }
        }
        
    } else {
        // ===================================================================
        // ORIGINAL MODE: Synced overdubs with merge processing
        // ===================================================================
        dprintf("dynamic macro: Loop trigger in ORIGINAL mode\n");
        
        // Check all playing macros for proximity to their loop end and restart if within threshold
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing) {
                bool should_restart = false;
                uint32_t threshold = calculate_restart_proximity_threshold(i);
                float speed_factor = macro_speed_factor[i];
                
                if (speed_factor <= 0.0f) continue;
                
                uint32_t real_loop_duration = (uint32_t)(macro_playback[i].loop_length / speed_factor);
                
                if (macro_playback[i].waiting_for_loop_gap) {
                    uint32_t time_to_restart = 0;
                    if (macro_playback[i].next_event_time > current_time) {
                        time_to_restart = macro_playback[i].next_event_time - current_time;
                    }
                    if (time_to_restart <= threshold) {
                        should_restart = true;
                    }
                } else {
                    uint32_t elapsed_since_start = current_time - macro_playback[i].timer;
                    uint32_t position_in_real_loop = elapsed_since_start % real_loop_duration;
                    uint32_t time_to_real_end = real_loop_duration - position_in_real_loop;
                    
                    if (time_to_real_end <= threshold) {
                        should_restart = true;
                    }
                }
                
                if (should_restart) {
                    // Process overdub merging and preroll for synced mode
                    if (overdub_merge_pending[i] || 
                        (macro_in_overdub_mode[i] && overdub_target_macro == i + 1)) {
                        auto_segment_overdub_if_needed(i);
                        process_pending_overdub_merge(i);
                        dprintf("dynamic macro: force-completed overdub for macro %d at forced restart\n", i + 1);
                    }
                    
                    // Handle preroll transfer for synced overdubs
                    if (macro_in_overdub_mode[i] && overdub_target_macro == i + 1 && 
                        collecting_preroll && preroll_buffer_count > 0) {
                        // [preroll transfer logic - same as original]
                        uint32_t current_time = timer_read32();
                        uint32_t cutoff_time = current_time - PREROLL_TIME_MS;
                        uint8_t oldest_idx = (preroll_buffer_index + PREROLL_BUFFER_SIZE - preroll_buffer_count) % PREROLL_BUFFER_SIZE;
                        
                        for (uint8_t j = 0; j < preroll_buffer_count && early_overdub_count[i] < 32; j++) {
                            uint8_t idx = (oldest_idx + j) % PREROLL_BUFFER_SIZE;
                            uint32_t event_time = preroll_start_time + preroll_buffer[idx].timestamp;
                            
                            if (event_time >= cutoff_time) {
                                early_overdub_buffer[i][early_overdub_count[i]] = preroll_buffer[idx];
                                early_overdub_buffer[i][early_overdub_count[i]].timestamp = 0;
                                early_overdub_count[i]++;
                            }
                        }
                    }
                    
                    if (overdub_temp_count[i] > 0) {
                        merge_overdub_buffer(i);
                        dprintf("dynamic macro: auto-merged temp overdub for macro %d at forced restart\n", i + 1);
                    }
                    
                    // Restart main macro
                    macro_playback[i].current = macro_playback[i].buffer_start;
                    macro_playback[i].timer = timer_read32();
                    
                    if (speed_factor > 0.0f) {
                        uint32_t adjusted_timestamp = (uint32_t)(macro_playback[i].current->timestamp / speed_factor);
                        macro_playback[i].next_event_time = macro_playback[i].timer + adjusted_timestamp;
                    } else {
                        macro_playback[i].next_event_time = UINT32_MAX;
                    }
                    
                    macro_playback[i].waiting_for_loop_gap = false;
                    cleanup_notes_from_macro(i + 1);
                    
                    // Start linked overdub playback in synced mode
                    if (overdub_buffers[i] != NULL && 
                        overdub_buffer_ends[i] != overdub_buffers[i] &&
                        !overdub_muted[i]) {
                        
                        macro_playback_state_t *overdub_state = &overdub_playback[i];
                        overdub_state->current = overdub_buffers[i];
                        overdub_state->end = overdub_buffer_ends[i];
                        overdub_state->direction = +1;
                        overdub_state->timer = macro_playback[i].timer;
                        overdub_state->buffer_start = overdub_buffers[i];
                        overdub_state->is_playing = true;
                        overdub_state->waiting_for_loop_gap = false;
                        overdub_state->next_event_time = 0;
                        send_loop_message(overdub_start_playing_cc[i], 127);
                    }
                    
                    if (sync_midi_mode) {
                        if (alternate_restart_mode) {
                            send_loop_message(loop_stop_playing_cc[i], 127);
                            send_loop_message(loop_start_playing_cc[i], 127);
                        } else {
                            send_loop_message(loop_restart_cc[i], 127);
                        }
                    }
                }
            }
        }
        
        // Check synced overdubs for restart (same logic as main macros)
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (overdub_playback[i].is_playing) {
                bool should_restart = false;
                uint32_t threshold = calculate_restart_proximity_threshold(i);
                float speed_factor = macro_speed_factor[i];
                
                if (speed_factor <= 0.0f) continue;
                
                uint32_t real_loop_duration = (uint32_t)(overdub_playback[i].loop_length / speed_factor);
                
                if (overdub_playback[i].waiting_for_loop_gap) {
                    uint32_t time_to_restart = 0;
                    if (overdub_playback[i].next_event_time > current_time) {
                        time_to_restart = overdub_playback[i].next_event_time - current_time;
                    }
                    if (time_to_restart <= threshold) {
                        should_restart = true;
                    }
                } else {
                    uint32_t elapsed_since_start = current_time - overdub_playback[i].timer;
                    uint32_t position_in_real_loop = elapsed_since_start % real_loop_duration;
                    uint32_t time_to_real_end = real_loop_duration - position_in_real_loop;
                    
                    if (time_to_real_end <= threshold) {
                        should_restart = true;
                    }
                }
                
                if (should_restart) {
                    overdub_playback[i].current = overdub_playback[i].buffer_start;
                    overdub_playback[i].timer = timer_read32();
                    
                    if (speed_factor > 0.0f) {
                        uint32_t adjusted_timestamp = (uint32_t)(overdub_playback[i].current->timestamp / speed_factor);
                        overdub_playback[i].next_event_time = overdub_playback[i].timer + adjusted_timestamp;
                    } else {
                        overdub_playback[i].next_event_time = UINT32_MAX;
                    }
                    
                    overdub_playback[i].waiting_for_loop_gap = false;
                }
            }
        }
    }
    
    // ===================================================================
    // SHARED LOGIC: Transformations, mute/unmute, commands
    // ===================================================================
    
    // Execute any batched commands first
    if (command_batch_count > 0) {
        execute_command_batch();
    }
    
    // Process pending transformation changes
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        // Main macro transformations (shared by both modes)
        if (macro_transpose_pending[i]) {
            cleanup_notes_from_macro(i + 1);
            if (overdub_playback[i].is_playing) {
                cleanup_notes_from_macro(i + 1 + MAX_MACROS);
            }
            macro_transpose[i] = macro_transpose_pending_value[i];
            macro_transpose_pending[i] = false;
            dprintf("dynamic macro: applied pending transpose change for macro %d to %d semitones\n", 
                    i + 1, macro_transpose[i]);
        }

        if (macro_channel_offset_pending[i]) {
            cleanup_notes_from_macro(i + 1);
            if (overdub_playback[i].is_playing) {
                cleanup_notes_from_macro(i + 1 + MAX_MACROS);
            }
            macro_channel_offset[i] = macro_channel_offset_pending_value[i];
            macro_channel_offset_pending[i] = false;
            dprintf("dynamic macro: applied pending channel offset change for macro %d to %+d\n", 
                    i + 1, macro_channel_offset[i]);
        }

        if (macro_channel_absolute_pending[i]) {
            cleanup_notes_from_macro(i + 1);
            if (overdub_playback[i].is_playing) {
                cleanup_notes_from_macro(i + 1 + MAX_MACROS);
            }
            macro_channel_absolute[i] = macro_channel_absolute_pending_value[i];
            macro_channel_absolute_pending[i] = false;
            if (macro_channel_absolute[i] == 0) {
                dprintf("dynamic macro: applied pending channel absolute change for macro %d to ORIGINAL\n", i + 1);
            } else {
                dprintf("dynamic macro: applied pending channel absolute change for macro %d to %d\n", 
                        i + 1, macro_channel_absolute[i]);
            }
        }
        
        if (macro_velocity_offset_pending[i]) {
            macro_velocity_offset[i] = macro_velocity_offset_pending_value[i];
            macro_velocity_offset_pending[i] = false;
            dprintf("dynamic macro: applied pending velocity offset change for macro %d to %+d\n", 
                    i + 1, macro_velocity_offset[i]);
        }

        if (macro_velocity_absolute_pending[i]) {
            macro_velocity_absolute[i] = macro_velocity_absolute_pending_value[i];
            macro_velocity_absolute_pending[i] = false;
            if (macro_velocity_absolute[i] == 0) {
                dprintf("dynamic macro: applied pending velocity absolute change for macro %d to ORIGINAL\n", i + 1);
            } else {
                dprintf("dynamic macro: applied pending velocity absolute change for macro %d to %d\n", 
                        i + 1, macro_velocity_absolute[i]);
            }
        }
        
        if (macro_octave_doubler_pending[i]) {
            macro_octave_doubler[i] = macro_octave_doubler_pending_value[i];
            macro_octave_doubler_pending[i] = false;
        }
        
        // Overdub transformations (only processed in advanced mode)
        if (overdub_advanced_mode) {
            if (overdub_transpose_pending[i]) {
                cleanup_notes_from_macro(i + 1 + MAX_MACROS);
                overdub_transpose[i] = overdub_transpose_pending_value[i];
                overdub_transpose_pending[i] = false;
                dprintf("dynamic macro: applied pending overdub transpose change for macro %d to %d semitones\n", 
                        i + 1, overdub_transpose[i]);
            }

            if (overdub_channel_offset_pending[i]) {
                cleanup_notes_from_macro(i + 1 + MAX_MACROS);
                overdub_channel_offset[i] = overdub_channel_offset_pending_value[i];
                overdub_channel_offset_pending[i] = false;
                dprintf("dynamic macro: applied pending overdub channel offset change for macro %d to %+d\n", 
                        i + 1, overdub_channel_offset[i]);
            }

            if (overdub_channel_absolute_pending[i]) {
                cleanup_notes_from_macro(i + 1 + MAX_MACROS);
                overdub_channel_absolute[i] = overdub_channel_absolute_pending_value[i];
                overdub_channel_absolute_pending[i] = false;
                if (overdub_channel_absolute[i] == 0) {
                    dprintf("dynamic macro: applied pending overdub channel absolute change for macro %d to ORIGINAL\n", i + 1);
                } else {
                    dprintf("dynamic macro: applied pending overdub channel absolute change for macro %d to %d\n", 
                            i + 1, overdub_channel_absolute[i]);
                }
            }
            
            if (overdub_velocity_offset_pending[i]) {
                overdub_velocity_offset[i] = overdub_velocity_offset_pending_value[i];
                overdub_velocity_offset_pending[i] = false;
                dprintf("dynamic macro: applied pending overdub velocity offset change for macro %d to %+d\n", 
                        i + 1, overdub_velocity_offset[i]);
            }

            if (overdub_velocity_absolute_pending[i]) {
                overdub_velocity_absolute[i] = overdub_velocity_absolute_pending_value[i];
                overdub_velocity_absolute_pending[i] = false;
                if (overdub_velocity_absolute[i] == 0) {
                    dprintf("dynamic macro: applied pending overdub velocity absolute change for macro %d to ORIGINAL\n", i + 1);
                } else {
                    dprintf("dynamic macro: applied pending overdub velocity absolute change for macro %d to %d\n", 
                            i + 1, overdub_velocity_absolute[i]);
                }
            }
            
            if (overdub_octave_doubler_pending[i]) {
                overdub_octave_doubler[i] = overdub_octave_doubler_pending_value[i];
                overdub_octave_doubler_pending[i] = false;
                dprintf("dynamic macro: applied pending overdub octave doubler change for macro %d\n", i + 1);
            }
        }
        
        // Process overdub mute/unmute (different logic per mode)
        if (overdub_mute_pending[i]) {
            overdub_muted[i] = true;
            
            if (overdub_playback[i].is_playing) {
                dynamic_macro_cleanup_notes_for_state(&overdub_playback[i]);
                overdub_playback[i].is_playing = false;
                overdub_playback[i].current = NULL;
                send_loop_message(overdub_stop_playing_cc[i], 127);
                dprintf("dynamic macro: muted overdub for macro %d at loop trigger\n", i + 1);
            }
            
            overdub_mute_pending[i] = false;
        }
        
        if (overdub_unmute_pending[i]) {
            overdub_muted[i] = false;
            
            if (overdub_buffers[i] != NULL &&
                overdub_buffer_ends[i] != overdub_buffers[i]) {
                
                if (overdub_advanced_mode) {
                    // Advanced mode: Independent overdub playback
                    macro_playback_state_t *overdub_state = &overdub_playback[i];
                    overdub_state->current = overdub_buffers[i];
                    overdub_state->end = overdub_buffer_ends[i];
                    overdub_state->direction = +1;
                    overdub_state->buffer_start = overdub_buffers[i];
                    overdub_state->is_playing = true;
                    overdub_state->waiting_for_loop_gap = false;
                    overdub_state->next_event_time = 0;
                    
                    overdub_independent_timer[i] = timer_read32();
                    overdub_state->timer = overdub_independent_timer[i];
                    overdub_state->loop_length = overdub_independent_loop_length[i];
                    overdub_state->loop_gap_time = overdub_independent_gap_time[i];
                    
                    dprintf("dynamic macro: unmuted and started independent overdub for macro %d\n", i + 1);
                } else {
                    // Original mode: Synced overdub playback (complex positioning logic from original)
                    if (macro_playback[i].is_playing) {
                        // [Complex sync positioning logic - same as original]
                        macro_playback_state_t *main_state = &macro_playback[i];
                        uint32_t current_time = timer_read32();
                        uint32_t elapsed = current_time - main_state->timer;
                        float speed_factor = macro_speed_factor[i];
                        uint32_t real_loop_duration = (speed_factor > 0.0f) ? 
                            (uint32_t)(main_state->loop_length / speed_factor) : main_state->loop_length;
                        
                        uint32_t position_in_real_loop = (real_loop_duration > 0) ? (elapsed % real_loop_duration) : 0;
                        uint32_t position_in_internal_loop = (speed_factor > 0.0f) ? 
                            (uint32_t)(position_in_real_loop * speed_factor) : position_in_real_loop;
                        
                        macro_playback_state_t *overdub_state = &overdub_playback[i];
                        overdub_state->end = overdub_buffer_ends[i];
                        overdub_state->direction = +1;
                        overdub_state->timer = main_state->timer;
                        overdub_state->buffer_start = overdub_buffers[i];
                        overdub_state->is_playing = true;
                        
                        // Find event positioning logic
                        bool all_events_before_current_position = true;
                        midi_event_t *first_event_after_position = NULL;
                        
                        for (midi_event_t *event = overdub_buffers[i]; event < overdub_buffer_ends[i]; event++) {
                            if (event->timestamp >= position_in_internal_loop) {
                                all_events_before_current_position = false;
                                first_event_after_position = event;
                                break;
                            }
                        }
                        
                        if (all_events_before_current_position) {
                            overdub_state->current = overdub_buffers[i];
                            overdub_state->waiting_for_loop_gap = true;
                            uint32_t time_to_next_loop = real_loop_duration - position_in_real_loop;
                            overdub_state->next_event_time = current_time + time_to_next_loop;
                        } else {
                            overdub_state->current = first_event_after_position;
                            overdub_state->waiting_for_loop_gap = false;
                            uint32_t time_to_next_event_internal = first_event_after_position->timestamp - position_in_internal_loop;
                            uint32_t time_to_next_event_real = (speed_factor > 0.0f) ? 
                                (uint32_t)(time_to_next_event_internal / speed_factor) : time_to_next_event_internal;
                            overdub_state->next_event_time = current_time + time_to_next_event_real;
                        }
                        
                        dprintf("dynamic macro: unmuted synced overdub for macro %d at position %lu ms\n", 
                                i + 1, position_in_real_loop);
                    }
                }
                
                send_loop_message(overdub_start_playing_cc[i], 127);
            }
            
            overdub_unmute_pending[i] = false;
        }
    }
    
    // Clear general macro primed state
    is_macro_primed = false;
}

static bool dynamic_macro_play_task_for_state(macro_playback_state_t *state) {
    if (!state->is_playing || state->current == NULL) {
        state->is_playing = false;
        return false;
    }
    
    if (global_playback_paused) {
        return true; // Continue task but don't progress
    }
    
    uint32_t current_time = timer_read32();
    
    // Determine which macro this is and if it's an independent overdub
    uint8_t macro_num = 0;
    bool is_independent_overdub = false;
    
    // Check if this is an overdub playback state in advanced mode
    if (overdub_advanced_mode) {
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (state->buffer_start == overdub_buffers[i]) {
                macro_num = i + 1;
                is_independent_overdub = true;
                break;
            }
        }
    }
    
    // If not found as independent overdub, check main macros
    if (macro_num == 0) {
        for (uint8_t i = 1; i <= MAX_MACROS; i++) {
            if (state->buffer_start == get_macro_buffer(i)) {
                macro_num = i;
                break;
            }
        }
    }
    
    // If still not found and not advanced mode, check overdub buffers (synced overdubs)
    if (macro_num == 0 && !overdub_advanced_mode) {
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (state->buffer_start == overdub_buffers[i]) {
                macro_num = i + 1;
                break;
            }
        }
    }
    
// =============================================================================
// INDEPENDENT OVERDUB LOGIC (COMPLETELY SEPARATE)
// =============================================================================
// =============================================================================
// INDEPENDENT OVERDUB LOGIC (COMPLETELY SEPARATE)
// =============================================================================
if (is_independent_overdub && macro_num > 0) {
    uint8_t macro_idx = macro_num - 1;
    uint32_t independent_gap_time = overdub_independent_gap_time[macro_idx];
    float speed_factor = macro_speed_factor[macro_idx]; // GET SPEED FACTOR
    
    // Handle initial event timing setup
    if (state->next_event_time == 0) {
        uint32_t base_delay = state->current->timestamp;
        if (speed_factor > 0.0f) {
            uint32_t adjusted_delay = (uint32_t)(base_delay / speed_factor);
            state->next_event_time = overdub_independent_timer[macro_idx] + adjusted_delay;
        } else {
            state->next_event_time = UINT32_MAX; // Paused
        }
        dprintf("independent overdub: set first event time for macro %d at adjusted timestamp %lu (raw: %lu, speed: %.2fx)\n", 
                macro_num, state->next_event_time - overdub_independent_timer[macro_idx], 
                state->current->timestamp, speed_factor);
    }
    
    // If we're at the end of the overdub and waiting for the gap
    if (state->waiting_for_loop_gap) {
        if (current_time >= state->next_event_time) {
            // Clean up notes before restart
            cleanup_notes_from_macro(macro_num + MAX_MACROS);
            dprintf("independent overdub: cleaned up notes for macro %d before restart\n", macro_num);
            
            // Check if we're in sample mode (one-shot)
            if (sample_mode_active) {
                state->is_playing = false;
                state->current = NULL;
                state->waiting_for_loop_gap = false;
                dprintf("independent overdub: one-shot end for macro %d in sample mode\n", macro_num);
                return false;
            }
            
            // Restart from beginning with fresh independent timing
            state->current = state->buffer_start;
            overdub_independent_timer[macro_idx] = timer_read32();
            state->timer = overdub_independent_timer[macro_idx];
            
            // Apply speed to first event
            if (speed_factor > 0.0f) {
                uint32_t adjusted_delay = (uint32_t)(state->current->timestamp / speed_factor);
                state->next_event_time = overdub_independent_timer[macro_idx] + adjusted_delay;
            } else {
                state->next_event_time = UINT32_MAX;
            }
            
            state->waiting_for_loop_gap = false;
            check_loop_trigger();
            
			if (sync_midi_mode && overdub_advanced_mode) {
				if (alternate_restart_mode) {
					send_loop_message(overdub_stop_playing_cc[macro_idx], 127);
					send_loop_message(overdub_start_playing_cc[macro_idx], 127);
				} else {
					send_loop_message(overdub_restart_cc[macro_idx], 127);
				}
			}
			
            dprintf("independent overdub: restarted macro %d with fresh independent timing (speed: %.2fx)\n", 
                    macro_num, speed_factor);
        }
        return true;
    }
    
    // Process events when it's time
    if (current_time >= state->next_event_time) {
        // Process the current event
        switch (state->current->type) {
            case MIDI_EVENT_DUMMY:
                // Dummy event - do nothing, just skip to next event
                dprintf("midi macro: skipped dummy event\n");
                break;

            case MIDI_EVENT_NOTE_ON:
            {
                uint8_t transposed_note, override_channel, offset_velocity;
                
                // Apply appropriate transformations based on mode
                if (overdub_advanced_mode) {
                    // ADVANCED MODE: Use overdub-specific transformations
                    transposed_note = apply_transpose(state->current->note, overdub_transpose[macro_idx]);
                    override_channel = apply_channel_transformations(state->current->channel,
                                                          overdub_channel_offset[macro_idx],
                                                          overdub_channel_absolute[macro_idx]);
                    offset_velocity = apply_overdub_velocity_transformations(state->current->raw_travel,
                                                          overdub_velocity_offset[macro_idx],
                                                          overdub_velocity_absolute[macro_idx], macro_num);
                } else {
                    // NORMAL MODE: Use macro transformations (existing behavior)
                    transposed_note = apply_transpose(state->current->note, macro_transpose[macro_idx]);
                    override_channel = apply_channel_transformations(state->current->channel,
                                                          macro_channel_offset[macro_idx],
                                                          macro_channel_absolute[macro_idx]);
                    offset_velocity = apply_velocity_transformations(state->current->raw_travel,
                                                          macro_velocity_offset[macro_idx],
                                                          macro_velocity_absolute[macro_idx], macro_num);
                }
                
                uint8_t track_id = macro_num + MAX_MACROS;
                
                if (!is_live_note_active(override_channel, transposed_note)) {
                    midi_send_noteon(&midi_device, override_channel, transposed_note, offset_velocity);
                    add_lighting_macro_note(override_channel, transposed_note, track_id);
                    
                    dprintf("independent overdub: played note ch:%d->%d note:%d->%d raw:%d->vel:%d for macro %d\n",
                            state->current->channel, override_channel, state->current->note, transposed_note,
                            state->current->raw_travel, offset_velocity, macro_num);
                } else {
                    dprintf("independent overdub: skipped note on ch:%d->%d note:%d->%d (active live note)\n", 
                            state->current->channel, override_channel, state->current->note, transposed_note);
                }
                
                mark_note_from_macro(override_channel, transposed_note, track_id);
                
                // Handle octave doubler (use appropriate setting based on mode)
                int8_t octave_doubler_value = overdub_advanced_mode ? 
                                             overdub_octave_doubler[macro_idx] : 
                                             macro_octave_doubler[macro_idx];
                
                if (octave_doubler_value != 0) {
                    uint8_t octave_note = apply_transpose(transposed_note, octave_doubler_value);
                    if (!is_live_note_active(override_channel, octave_note)) {
                        midi_send_noteon(&midi_device, override_channel, octave_note, offset_velocity);
                        add_lighting_macro_note(override_channel, octave_note, track_id);
                    }
                    mark_note_from_macro(override_channel, octave_note, track_id);
                }
                break;
            }

            case MIDI_EVENT_NOTE_OFF:
            {
                uint8_t transposed_note, override_channel, offset_velocity;
                
                // Apply appropriate transformations based on mode
                if (overdub_advanced_mode) {
                    // ADVANCED MODE: Use overdub-specific transformations
                    transposed_note = apply_transpose(state->current->note, overdub_transpose[macro_idx]);
                    override_channel = apply_channel_transformations(state->current->channel,
                                                          overdub_channel_offset[macro_idx],
                                                          overdub_channel_absolute[macro_idx]);
                    offset_velocity = apply_overdub_velocity_transformations(state->current->raw_travel,
                                                          overdub_velocity_offset[macro_idx],
                                                          overdub_velocity_absolute[macro_idx], macro_num);
                } else {
                    // NORMAL MODE: Use macro transformations (existing behavior)
                    transposed_note = apply_transpose(state->current->note, macro_transpose[macro_idx]);
                    override_channel = apply_channel_transformations(state->current->channel,
                                                          macro_channel_offset[macro_idx],
                                                          macro_channel_absolute[macro_idx]);
                    offset_velocity = apply_velocity_transformations(state->current->raw_travel,
                                                          macro_velocity_offset[macro_idx],
                                                          macro_velocity_absolute[macro_idx], macro_num);
                }
                
                uint8_t track_id = macro_num + MAX_MACROS;
                
                if (!is_live_note_active(override_channel, transposed_note)) {
                    midi_send_noteoff(&midi_device, override_channel, transposed_note, offset_velocity);
                    remove_lighting_macro_note(override_channel, transposed_note, track_id);
                    
                    dprintf("independent overdub: played note off ch:%d->%d note:%d->%d raw:%d->vel:%d for macro %d\n",
                            state->current->channel, override_channel, state->current->note, transposed_note,
                            state->current->raw_travel, offset_velocity, macro_num);
                } else {
                    dprintf("independent overdub: skipped note off ch:%d->%d note:%d->%d (active live note)\n", 
                            state->current->channel, override_channel, state->current->note, transposed_note);
                }
                
                unmark_note_from_macro(override_channel, transposed_note, track_id);
                
                // Handle octave doubler note-off (use appropriate setting based on mode)
                int8_t octave_doubler_value = overdub_advanced_mode ? 
                                             overdub_octave_doubler[macro_idx] : 
                                             macro_octave_doubler[macro_idx];
                                             
                if (octave_doubler_value != 0) {
                    uint8_t octave_note = apply_transpose(transposed_note, octave_doubler_value);
                    if (!is_live_note_active(override_channel, octave_note)) {
                        midi_send_noteoff(&midi_device, override_channel, octave_note, offset_velocity);
                        remove_lighting_macro_note(override_channel, octave_note, track_id);
                    }
                    unmark_note_from_macro(override_channel, octave_note, track_id);
                }
                break;
            }
            
            case MIDI_EVENT_CC:
                midi_send_cc(&midi_device, state->current->channel, state->current->note, state->current->raw_travel);
                dprintf("independent overdub: played CC ch:%d cc:%d val:%d\n",
                        state->current->channel, state->current->note, state->current->raw_travel);
                break;
        }
        
        // Move to next event
        state->current++;
        
        // Check if we've reached the end
        if (state->current == state->end) {
            dprintf("independent overdub: reached end of macro %d\n", macro_num);
            
            if (sample_mode_active) {
                cleanup_notes_from_macro(macro_num + MAX_MACROS);
                state->is_playing = false;
                state->current = NULL;
                dprintf("independent overdub: one-shot end for macro %d in sample mode\n", macro_num);
                return false;
            }
            
            // Calculate when to restart using independent gap time WITH SPEED
            state->waiting_for_loop_gap = true;
            if (speed_factor > 0.0f) {
                uint32_t adjusted_gap = (uint32_t)(independent_gap_time / speed_factor);
                state->next_event_time = current_time + adjusted_gap;
            } else {
                state->next_event_time = UINT32_MAX;
            }
            
            dprintf("independent overdub: reached end, waiting %lu ms before restarting (raw gap: %lu, speed: %.2fx)\n", 
                    state->next_event_time - current_time, independent_gap_time, speed_factor);
        } else {
            // Calculate time for next event using independent timing WITH SPEED
            if (speed_factor > 0.0f) {
                uint32_t adjusted_timestamp = (uint32_t)(state->current->timestamp / speed_factor);
                state->next_event_time = overdub_independent_timer[macro_idx] + adjusted_timestamp;
            } else {
                state->next_event_time = UINT32_MAX;
            }
        }
    }
    
    return true;
}

  // =============================================================================
    // ORIGINAL LOGIC FOR MAIN MACROS AND SYNCED OVERDUBS
    // =============================================================================
    
    // Determine which macro this is and if it's an overdub to get its speed factor
    bool is_overdub_state = false;
    float speed_factor = 1.0f;
    
    if (macro_num > 0) {
        // Check if this macro_num corresponds to an overdub buffer (synced overdub)
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (state->buffer_start == overdub_buffers[i]) {
                is_overdub_state = true;
                break;
            }
        }
        speed_factor = macro_speed_factor[macro_num - 1];
    }
    
    // Handle initial event timing setup
    if (state->next_event_time == 0) {
        uint32_t base_delay = state->current->timestamp;
        if (speed_factor > 0.0f) {
            uint32_t adjusted_delay = (uint32_t)(base_delay / speed_factor);
            state->next_event_time = state->timer + adjusted_delay;
        } else {
            state->next_event_time = UINT32_MAX;
            return true;
        }
    }
    
    // If we're at the end of the macro and waiting for the loop gap
    if (state->waiting_for_loop_gap) {
        if (current_time >= state->next_event_time) {
            // Clean up notes before restart (only for main macros, NOT synced overdubs)
            if (macro_num > 0 && !is_overdub_state) {
                cleanup_notes_from_macro(macro_num);
                dprintf("dynamic macro: cleaned up hanging notes for macro %d before loop restart\n", macro_num);
            }
            
            // Handle preroll transfer if needed
            if (!is_overdub_state && macro_num > 0 && 
                macro_in_overdub_mode[macro_num - 1] && overdub_target_macro == macro_num && 
                collecting_preroll && preroll_buffer_count > 0) {
                
                uint8_t macro_idx = macro_num - 1;
                uint32_t cutoff_time = current_time - PREROLL_TIME_MS;
                uint8_t oldest_idx = (preroll_buffer_index + PREROLL_BUFFER_SIZE - preroll_buffer_count) % PREROLL_BUFFER_SIZE;
                
                for (uint8_t j = 0; j < preroll_buffer_count && early_overdub_count[macro_idx] < 32; j++) {
                    uint8_t idx = (oldest_idx + j) % PREROLL_BUFFER_SIZE;
                    uint32_t event_time = preroll_start_time + preroll_buffer[idx].timestamp;
                    
                    if (event_time >= cutoff_time) {
                        early_overdub_buffer[macro_idx][early_overdub_count[macro_idx]] = preroll_buffer[idx];
                        early_overdub_buffer[macro_idx][early_overdub_count[macro_idx]].timestamp = 0;
                        early_overdub_count[macro_idx]++;
                        
                        dprintf("overdub preroll: transferred event type:%d ch:%d note:%d vel:%d at natural loop end\n",
                                preroll_buffer[idx].type, preroll_buffer[idx].channel,
                                preroll_buffer[idx].note, preroll_buffer[idx].raw_travel);
                    }
                }
                
                dprintf("overdub preroll: transferred %d preroll events to early overdub for macro %d at natural loop end\n", 
                        early_overdub_count[macro_idx], macro_num);
            }
            
            // Process overdub merging if needed (only for synced overdubs, not advanced mode)
            if (!is_overdub_state && macro_num > 0 && !overdub_advanced_mode) {
                if (overdub_merge_pending[macro_num - 1] || 
                    (macro_in_overdub_mode[macro_num - 1] && overdub_target_macro == macro_num)) {
                    auto_segment_overdub_if_needed(macro_num - 1);
                    process_pending_overdub_merge(macro_num - 1);
                    dprintf("dynamic macro: auto-completed SYNCED overdub for macro %d at natural loop boundary\n", macro_num);
                }
            }
            
            // Check if we're in sample mode
            if (sample_mode_active) {
                state->is_playing = false;
                state->current = NULL;
                state->waiting_for_loop_gap = false;
				send_loop_message(loop_stop_playing_cc[macro_num - 1], 127);
                dprintf("midi macro: one-shot end for macro %d in sample mode\n", macro_num);
                return false;
            }
            
            // Merge temp overdub if needed (only for synced mode)
            if (!is_overdub_state && macro_num > 0 && !overdub_advanced_mode && overdub_temp_count[macro_num - 1] > 0) {
                merge_overdub_buffer(macro_num - 1);
                dprintf("dynamic macro: auto-merged temp SYNCED overdub for macro %d at natural loop restart\n", macro_num);
            }
            
            // Restart from beginning
            state->current = state->buffer_start;
            state->timer = timer_read32();
            
			if (sync_midi_mode && macro_num > 0) {
				if (!is_overdub_state) {
					// Main macro restart
					if (alternate_restart_mode) {
						send_loop_message(loop_stop_playing_cc[macro_num - 1], 127);
						send_loop_message(loop_start_playing_cc[macro_num - 1], 127);
					} else {
						send_loop_message(loop_restart_cc[macro_num - 1], 127);
					}
				} if (is_overdub_state && overdub_advanced_mode) {
					// Overdub restart (synced mode)
					if (alternate_restart_mode) {
						send_loop_message(overdub_stop_playing_cc[macro_num - 1], 127);
						send_loop_message(overdub_start_playing_cc[macro_num - 1], 127);
					} else {
						send_loop_message(overdub_restart_cc[macro_num - 1], 127);
					}
				}
				
				else {}
			}
            
            if (speed_factor > 0.0f) {
                uint32_t base_delay = state->current->timestamp;
                uint32_t adjusted_delay = (uint32_t)(base_delay / speed_factor);
                state->next_event_time = state->timer + adjusted_delay;
            } else {
                state->next_event_time = UINT32_MAX;
                return true;
            }
            
            state->waiting_for_loop_gap = false;
            
            uint8_t macro_idx = macro_num - 1;
            
            // SYNCED OVERDUB HANDLING (not advanced mode)
            if (!is_overdub_state && !overdub_advanced_mode && overdub_buffers[macro_idx] != NULL && 
                overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx] &&
                !overdub_muted[macro_idx]) {
                
                macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
                overdub_state->current = overdub_buffers[macro_idx];
                overdub_state->end = overdub_buffer_ends[macro_idx];
                overdub_state->direction = +1;
                overdub_state->timer = timer_read32();
                overdub_state->buffer_start = overdub_buffers[macro_idx];
                overdub_state->is_playing = true;
                overdub_state->waiting_for_loop_gap = false;
                overdub_state->next_event_time = 0;
                send_loop_message(overdub_start_playing_cc[macro_idx], 127);
                dprintf("dynamic macro: restarted SYNCED overdub playback for macro %d\n", macro_num);
            }
            
            // Send loop trigger when appropriate
            if (is_overdub_state) {
                if ((current_bpm == 0 || bpm_source_macro != 0) && macro_num > 0 && !macro_playback[macro_num - 1].is_playing) {
                    check_loop_trigger();
                } else if (current_bpm > 0 && bpm_source_macro == 0) {
                    dprintf("midi macro: overdub %d skipped loop trigger (manual bpm sync active)\n", macro_num);
                } else {
                    dprintf("midi macro: overdub %d completed cycle but parent macro is playing - no loop trigger\n", macro_num);
                }
            } else {
                if (current_bpm == 0 || bpm_source_macro != 0) {
                    check_loop_trigger();
                } else {
                    dprintf("midi macro: skipped loop trigger (manual bpm sync active) from macro %d\n", macro_num);
                }
            }
        }
        return true;
    }
    
    if (current_time >= state->next_event_time) {
        // Process the current event (note on/off/CC)
                switch (state->current->type) {
            case MIDI_EVENT_DUMMY:
                // Dummy event - do nothing, just skip to next event
                dprintf("midi macro: skipped dummy event\n");
                break;

            case MIDI_EVENT_NOTE_ON:
            {
                uint8_t transposed_note = state->current->note;
                uint8_t override_channel = state->current->channel;
                uint8_t offset_velocity = state->current->raw_travel;  // Will be transformed below

                if (macro_num > 0) {
                    uint8_t macro_idx = macro_num - 1;

                    if (is_overdub_state && overdub_advanced_mode) {
                        // Advanced mode overdub: use overdub transformations
                        transposed_note = apply_transpose(state->current->note, overdub_transpose[macro_idx]);
                        override_channel = apply_channel_transformations(state->current->channel,
                                                          overdub_channel_offset[macro_idx],
                                                          overdub_channel_absolute[macro_idx]);
                        offset_velocity = apply_overdub_velocity_transformations(state->current->raw_travel,
                                                        overdub_velocity_offset[macro_idx],
                                                        overdub_velocity_absolute[macro_idx], macro_num);
                    } else {
                        // Normal mode or main macro: use macro transformations
                        transposed_note = apply_transpose(state->current->note, macro_transpose[macro_idx]);
                        override_channel = apply_channel_transformations(state->current->channel,
                                                          macro_channel_offset[macro_idx],
                                                          macro_channel_absolute[macro_idx]);
                        offset_velocity = apply_velocity_transformations(state->current->raw_travel,
                                                        macro_velocity_offset[macro_idx],
                                                        macro_velocity_absolute[macro_idx], macro_num);
                    }
                }
                
                uint8_t track_id = is_overdub_state ? (macro_num + MAX_MACROS) : macro_num;
                
                if (!is_live_note_active(override_channel, transposed_note)) {
                    if (macro_num > 0 && (!macro_main_muted[macro_num - 1] || is_overdub_state)) {
                        midi_send_noteon(&midi_device, override_channel, transposed_note, offset_velocity);
                        add_lighting_macro_note(override_channel, transposed_note, track_id);
                    }
                    if (macro_num > 0) {
                        mark_note_from_macro(override_channel, transposed_note, track_id);
                        
                        // Determine which octave doubler to use based on mode and state
                        int8_t octave_doubler_value;
                        if (is_overdub_state && overdub_advanced_mode) {
                            octave_doubler_value = overdub_octave_doubler[macro_num - 1];
                        } else {
                            octave_doubler_value = macro_octave_doubler[macro_num - 1];
                        }
                        
                        if (octave_doubler_value != 0) {
                            uint8_t octave_note = apply_transpose(transposed_note, octave_doubler_value);
                            mark_note_from_macro(override_channel, octave_note, track_id);
                        }
                        
                        if (is_overdub_state) {
                            dprintf("midi macro: played overdub note ch:%d->%d note:%d->%d raw:%d->vel:%d for macro %d\n",
                                    state->current->channel, override_channel, state->current->note, transposed_note,
                                    state->current->raw_travel, offset_velocity, macro_num);
                        } else {
                            dprintf("midi macro: played note ch:%d->%d note:%d->%d raw:%d->vel:%d\n",
                                    state->current->channel, override_channel, state->current->note, transposed_note,
                                    state->current->raw_travel, offset_velocity);
                        }
                    }
                } else {
                    dprintf("midi macro: skipped note on ch:%d->%d note:%d->%d (active live note)\n", 
                            state->current->channel, override_channel, state->current->note, transposed_note);
                    
                    if (macro_num > 0) {
                        uint8_t track_id = is_overdub_state ? (macro_num + MAX_MACROS) : macro_num;
                        mark_note_from_macro(override_channel, transposed_note, track_id);
                        
                        // Determine which octave doubler to use based on mode and state
                        int8_t octave_doubler_value;
                        if (is_overdub_state && overdub_advanced_mode) {
                            octave_doubler_value = overdub_octave_doubler[macro_num - 1];
                        } else {
                            octave_doubler_value = macro_octave_doubler[macro_num - 1];
                        }
                        
                        if (octave_doubler_value != 0) {
                            uint8_t octave_note = apply_transpose(transposed_note, octave_doubler_value);
                            mark_note_from_macro(override_channel, octave_note, track_id);
                        }
                        
                        if (is_overdub_state) {
                            dprintf("midi macro: tracked (but skipped playing) overdub note ch:%d->%d note:%d->%d for macro %d\n", 
                                    state->current->channel, override_channel, state->current->note, transposed_note, macro_num);
                        } else {
                            dprintf("midi macro: tracked (but skipped playing) note ch:%d->%d note:%d->%d for macro %d\n", 
                                    state->current->channel, override_channel, state->current->note, transposed_note, macro_num);
                        }
                    }
                }
                
                if (macro_num > 0) {
                    // Determine which octave doubler to use based on mode and state
                    int8_t octave_doubler_value;
                    if (is_overdub_state && overdub_advanced_mode) {
                        octave_doubler_value = overdub_octave_doubler[macro_num - 1];
                    } else {
                        octave_doubler_value = macro_octave_doubler[macro_num - 1];
                    }
                    
                    if (octave_doubler_value != 0) {
                        uint8_t octave_note = apply_transpose(transposed_note, octave_doubler_value);
                        if (!is_live_note_active(override_channel, octave_note)) {
                            if (macro_num > 0 && (!macro_main_muted[macro_num - 1] || is_overdub_state)) {
                                midi_send_noteon(&midi_device, override_channel, octave_note, offset_velocity);
                                add_lighting_macro_note(override_channel, octave_note, track_id);
                            }
                            if (is_overdub_state) {
                                dprintf("midi macro: played overdub octave note ch:%d->%d note:%d->%d raw:%d->vel:%d for macro %d\n",
                                        state->current->channel, override_channel, octave_note, octave_note,
                                        state->current->raw_travel, offset_velocity, macro_num);
                            } else {
                                dprintf("midi macro: played octave note ch:%d->%d note:%d->%d raw:%d->vel:%d\n",
                                        state->current->channel, override_channel, octave_note, octave_note,
                                        state->current->raw_travel, offset_velocity);
                            }
                        } else {
                            dprintf("midi macro: skipped octave note ch:%d->%d note:%d->%d (active live note)\n", 
                                    state->current->channel, override_channel, octave_note, octave_note);
                        }
                    }
                }
                break;
            }

            case MIDI_EVENT_NOTE_OFF:
          {
                uint8_t transposed_note_off = state->current->note;
                uint8_t override_channel_off = state->current->channel;
                uint8_t offset_velocity_off = state->current->raw_travel;  // Will be transformed below

                if (macro_num > 0) {
                    uint8_t macro_idx = macro_num - 1;

                    if (is_overdub_state && overdub_advanced_mode) {
                        // Advanced mode overdub: use overdub transformations
                        transposed_note_off = apply_transpose(state->current->note, overdub_transpose[macro_idx]);
                        override_channel_off = apply_channel_transformations(state->current->channel,
                                                          overdub_channel_offset[macro_idx],
                                                          overdub_channel_absolute[macro_idx]);
                        offset_velocity_off = apply_overdub_velocity_transformations(state->current->raw_travel,
                                                            overdub_velocity_offset[macro_idx],
                                                            overdub_velocity_absolute[macro_idx], macro_num);
                    } else {
                        // Normal mode or main macro: use macro transformations
                        transposed_note_off = apply_transpose(state->current->note, macro_transpose[macro_idx]);
                        override_channel_off = apply_channel_transformations(state->current->channel,
                                                          macro_channel_offset[macro_idx],
                                                          macro_channel_absolute[macro_idx]);
                        offset_velocity_off = apply_velocity_transformations(state->current->raw_travel,
                                                            macro_velocity_offset[macro_idx],
                                                            macro_velocity_absolute[macro_idx], macro_num);
                    }
                }
                
                uint8_t track_id = is_overdub_state ? (macro_num + MAX_MACROS) : macro_num;
                
                if (!is_live_note_active(override_channel_off, transposed_note_off)) {
                    if (macro_num > 0 && (!macro_main_muted[macro_num - 1] || is_overdub_state)) {
                        midi_send_noteoff(&midi_device, override_channel_off, transposed_note_off, offset_velocity_off);
                        remove_lighting_macro_note(override_channel_off, transposed_note_off, track_id);
                    }
                    
                    if (is_overdub_state) {
                        dprintf("midi macro: played overdub note off ch:%d->%d note:%d->%d raw:%d->vel:%d for macro %d\n",
                                state->current->channel, override_channel_off, state->current->note, transposed_note_off,
                                state->current->raw_travel, offset_velocity_off, macro_num);
                    } else {
                        dprintf("midi macro: played note off ch:%d->%d note:%d->%d raw:%d->vel:%d\n",
                                state->current->channel, override_channel_off, state->current->note, transposed_note_off,
                                state->current->raw_travel, offset_velocity_off);
                    }
                } else {
                    dprintf("midi macro: skipped note off ch:%d->%d note:%d->%d (active live note)\n", 
                            state->current->channel, override_channel_off, state->current->note, transposed_note_off);
                }
                
                if (macro_num > 0) {
                    uint8_t track_id = is_overdub_state ? (macro_num + MAX_MACROS) : macro_num;
                    unmark_note_from_macro(override_channel_off, transposed_note_off, track_id);
                    
                    // Determine which octave doubler to use based on mode and state
                    int8_t octave_doubler_value;
                    if (is_overdub_state && overdub_advanced_mode) {
                        octave_doubler_value = overdub_octave_doubler[macro_num - 1];
                    } else {
                        octave_doubler_value = macro_octave_doubler[macro_num - 1];
                    }
                    
                    if (octave_doubler_value != 0) {
                        uint8_t octave_note = apply_transpose(transposed_note_off, octave_doubler_value);
                        unmark_note_from_macro(override_channel_off, octave_note, track_id);
                    }
                }
                
                if (macro_num > 0) {
                    // Determine which octave doubler to use based on mode and state
                    int8_t octave_doubler_value;
                    if (is_overdub_state && overdub_advanced_mode) {
                        octave_doubler_value = overdub_octave_doubler[macro_num - 1];
                    } else {
                        octave_doubler_value = macro_octave_doubler[macro_num - 1];
                    }
                    
                    if (octave_doubler_value != 0) {
                        uint8_t octave_note = apply_transpose(transposed_note_off, octave_doubler_value);
                        if (!is_live_note_active(override_channel_off, octave_note)) {
                            if (macro_num > 0 && (!macro_main_muted[macro_num - 1] || is_overdub_state)) {
                                midi_send_noteoff(&midi_device, override_channel_off, octave_note, offset_velocity_off);
                                remove_lighting_macro_note(override_channel_off, octave_note, track_id);
                            }
                            if (is_overdub_state) {
                                dprintf("midi macro: played overdub octave note off ch:%d->%d note:%d->%d raw:%d->vel:%d for macro %d\n",
                                        state->current->channel, override_channel_off, octave_note, octave_note,
                                        state->current->raw_travel, offset_velocity_off, macro_num);
                            } else {
                                dprintf("midi macro: played octave note off ch:%d->%d note:%d->%d raw:%d->vel:%d\n",
                                        state->current->channel, override_channel_off, octave_note, octave_note,
                                        state->current->raw_travel, offset_velocity_off);
                            }
                        } else {
                            dprintf("midi macro: skipped octave note off ch:%d->%d note:%d->%d (active live note)\n", 
                                    state->current->channel, override_channel_off, octave_note, octave_note);
                        }
                    }
                }
                break;
            }           
            case MIDI_EVENT_CC:
                midi_send_cc(&midi_device, state->current->channel, state->current->note, state->current->raw_travel);
                dprintf("midi macro: played CC ch:%d cc:%d val:%d\n",
                        state->current->channel, state->current->note, state->current->raw_travel);
                break;
        }
        
        state->current += state->direction;
        
        // Determine effective loop length
        uint32_t effective_loop_length = 0;
        if (state->loop_length > 0) {
            effective_loop_length = state->loop_length;
        } else {
            effective_loop_length = 2000;
        }
        
        // Check if we've reached the end of the macro
        if (state->current == state->end) {
            if (macro_num > 0) {
                dprintf("midi macro: reached end of %s %d\n", 
                        is_overdub_state ? "overdub" : "macro", macro_num);
            }
            
            if (sample_mode_active) {
                if (macro_num > 0) {
                    uint8_t track_id = is_overdub_state ? (macro_num + MAX_MACROS) : macro_num;
                    cleanup_notes_from_macro(track_id);
					send_loop_message(loop_stop_playing_cc[macro_num - 1], 127);
                }
                state->is_playing = false;
                state->current = NULL;
                dprintf("midi macro: one-shot end for %s %d in sample mode\n", 
                        is_overdub_state ? "overdub" : "macro", macro_num);
                return false;
            }
            
            // Calculate gap time
            uint32_t gap_time;
            if (effective_loop_length > 0) {
                midi_event_t *last_event = state->end - 1;
                if (last_event >= state->buffer_start) {
                    gap_time = effective_loop_length - last_event->timestamp;
                    if (gap_time > effective_loop_length) {
                        gap_time = state->loop_gap_time;
                    }
                } else {
                    gap_time = state->loop_gap_time;
                }
                dprintf("midi macro: using effective loop_length %lu ms, calculated gap %lu ms\n", 
                        effective_loop_length, gap_time);
            } else {
                gap_time = state->loop_gap_time;
                dprintf("midi macro: using fallback loop_gap_time %lu ms\n", gap_time);
            }
            
            uint32_t adjusted_gap_time;
            if (speed_factor > 0.0f) {
                adjusted_gap_time = (uint32_t)(gap_time / speed_factor);
            } else {
                adjusted_gap_time = UINT32_MAX;
            }
            
            state->waiting_for_loop_gap = true;
            state->next_event_time = current_time + adjusted_gap_time;
            dprintf("midi macro: reached end, waiting %lu ms before looping (speed factor: %.2f)\n", 
                    adjusted_gap_time, speed_factor);
        } else {
            // Calculate time for next event
            if (speed_factor > 0.0f) {
                uint32_t base_timestamp = state->current->timestamp;
                uint32_t adjusted_timestamp = (uint32_t)(base_timestamp / speed_factor);
                state->next_event_time = state->timer + adjusted_timestamp;
            } else {
                state->next_event_time = UINT32_MAX;
            }
        }
    }
    
    return true;
}

void apply_macro_transformation(void (*setter_func)(uint8_t, int8_t), int8_t value) {
    if (is_any_macro_modifier_active()) {
        for (uint8_t i = 0; i < 4; i++) {
            if (macro_modifier_held[i]) {
                setter_func(i + 1, value);
            }
        }
    }
}

// Add new function to get the target transpose value
int8_t get_macro_transpose_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_transpose_target[macro_num - 1];
    }
    return 0;
}

// Add new function to set target directly (for MIDI controllers)
void set_macro_transpose_target(uint8_t macro_num, int8_t transpose_value) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        // Clamp transpose value to reasonable range
        if (transpose_value < -127) {
            transpose_value = -127;
        } else if (transpose_value > 127) {
            transpose_value = 127;
        }
        
        uint8_t macro_idx = macro_num - 1;
        
        // Set the target immediately
        macro_transpose_target[macro_idx] = transpose_value;
        
        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            // Macros are playing - queue the change for next loop trigger
            macro_transpose_pending[macro_idx] = true;
            macro_transpose_pending_value[macro_idx] = transpose_value;
            
            dprintf("dynamic macro: set transpose target for macro %d to %d semitones (queued for loop trigger)\n", 
                    macro_num, transpose_value);
        } else {
            // No macros playing - apply immediately
            macro_transpose[macro_idx] = transpose_value;
            dprintf("dynamic macro: immediately applied transpose target for macro %d to %d semitones\n", 
                    macro_num, transpose_value);
        }
    }
}

// Add function to reset all transpose targets
void reset_all_macro_transpose_targets(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_transpose_target[i] = 0;
        macro_transpose_pending[i] = false;
        macro_transpose_pending_value[i] = 0;
        macro_transpose[i] = 0;
    }
    dprintf("dynamic macro: reset all transpose targets and values to 0\n");
}

// Update existing channel absolute functions (renamed from channel override)
uint8_t get_macro_channel_absolute(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_channel_absolute[macro_num - 1];
    }
    return 0;
}

void set_macro_channel_absolute(uint8_t macro_num, uint8_t channel_absolute) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        // Clamp channel absolute to valid range (0-16)
        if (channel_absolute > 16) {
            channel_absolute = 16;
        }
        
        macro_channel_absolute[macro_num - 1] = channel_absolute;
        
        if (channel_absolute == 0) {
            dprintf("dynamic macro: set macro %d to use original channel\n", macro_num);
        } else {
            dprintf("dynamic macro: set macro %d to force channel %d\n", 
                    macro_num, channel_absolute);
        }
    }
}

// New target getter for channel absolute
uint8_t get_macro_channel_absolute_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_channel_absolute_target[macro_num - 1];
    }
    return 0;
}

// New target setter for channel absolute
void set_macro_channel_absolute_target(uint8_t macro_num, uint8_t channel_absolute) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        // Clamp channel absolute to valid range (0-16)
        if (channel_absolute > 16) {
            channel_absolute = 16;
        }
        
        uint8_t macro_idx = macro_num - 1;
        
        // Set the target immediately
        macro_channel_absolute_target[macro_idx] = channel_absolute;
        
        // RESET OFFSET TO 0 when setting absolute
        macro_channel_offset_target[macro_idx] = 0;
        
        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            // Macros are playing - queue both changes for next loop trigger
            macro_channel_absolute_pending[macro_idx] = true;
            macro_channel_absolute_pending_value[macro_idx] = channel_absolute;
            macro_channel_offset_pending[macro_idx] = true;
            macro_channel_offset_pending_value[macro_idx] = 0;
            
            if (channel_absolute == 0) {
                dprintf("dynamic macro: set channel absolute target for macro %d to ORIGINAL, reset offset to 0 (queued for loop trigger)\n", macro_num);
            } else {
                dprintf("dynamic macro: set channel absolute target for macro %d to %d, reset offset to 0 (queued for loop trigger)\n", 
                        macro_num, channel_absolute);
            }
        } else {
            // No macros playing - apply immediately
            macro_channel_absolute[macro_idx] = channel_absolute;
            macro_channel_offset[macro_idx] = 0;
            if (channel_absolute == 0) {
                dprintf("dynamic macro: immediately set channel absolute for macro %d to ORIGINAL, reset offset to 0\n", macro_num);
            } else {
                dprintf("dynamic macro: immediately set channel absolute for macro %d to %d, reset offset to 0\n", 
                        macro_num, channel_absolute);
            }
        }
    }
}

// New reset functions for channel offset
void reset_all_macro_channel_offset(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_channel_offset[i] = 0;
    }
    dprintf("dynamic macro: reset all channel offsets to 0\n");
}

void reset_all_macro_channel_offset_targets(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_channel_offset_target[i] = 0;
        macro_channel_offset_pending[i] = false;
        macro_channel_offset_pending_value[i] = 0;
        macro_channel_offset[i] = 0;
    }
    dprintf("dynamic macro: reset all channel offset targets and values to 0\n");
}

// New getter functions for velocity offset target
int8_t get_macro_velocity_offset_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_velocity_offset_target[macro_num - 1];
    }
    return 0;
}

// New setter function for velocity offset target
void set_macro_velocity_offset_target(uint8_t macro_num, int8_t velocity_offset) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        // Clamp velocity offset to reasonable range
        if (velocity_offset < -127) {
            velocity_offset = -127;
        } else if (velocity_offset > 127) {
            velocity_offset = 127;
        }
        
        uint8_t macro_idx = macro_num - 1;
        
        // Set the target immediately
        macro_velocity_offset_target[macro_idx] = velocity_offset;
        
        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            // Macros are playing - queue the change for next loop trigger
            macro_velocity_offset_pending[macro_idx] = true;
            macro_velocity_offset_pending_value[macro_idx] = velocity_offset;
            
            dprintf("dynamic macro: set velocity offset target for macro %d to %+d (queued for loop trigger)\n", 
                    macro_num, velocity_offset);
        } else {
            // No macros playing - apply immediately
            macro_velocity_offset[macro_idx] = velocity_offset;
            dprintf("dynamic macro: immediately applied velocity offset for macro %d to %+d\n", 
                    macro_num, velocity_offset);
        }
    }
}

// Velocity absolute functions (copied from channel absolute pattern)
uint8_t get_macro_velocity_absolute(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_velocity_absolute[macro_num - 1];
    }
    return 0;
}

void set_macro_velocity_absolute(uint8_t macro_num, uint8_t velocity_absolute) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        // Clamp velocity absolute to valid range (0-127)
        if (velocity_absolute > 127) {
            velocity_absolute = 127;
        }
        
        macro_velocity_absolute[macro_num - 1] = velocity_absolute;
        
        if (velocity_absolute == 0) {
            dprintf("dynamic macro: set macro %d to use original velocity\n", macro_num);
        } else {
            dprintf("dynamic macro: set macro %d to force velocity %d\n", 
                    macro_num, velocity_absolute);
        }
    }
}

// New target getter for velocity absolute
uint8_t get_macro_velocity_absolute_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_velocity_absolute_target[macro_num - 1];
    }
    return 0;
}

// New target setter for velocity absolute
void set_macro_velocity_absolute_target(uint8_t macro_num, uint8_t velocity_absolute) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        // Clamp velocity absolute to valid range (0-127)
        if (velocity_absolute > 127) {
            velocity_absolute = 127;
        }
        
        uint8_t macro_idx = macro_num - 1;
        
        // Set the target immediately
        macro_velocity_absolute_target[macro_idx] = velocity_absolute;
        
        // RESET OFFSET TO 0 when setting absolute
        macro_velocity_offset_target[macro_idx] = 0;
        
        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            // Macros are playing - queue both changes for next loop trigger
            macro_velocity_absolute_pending[macro_idx] = true;
            macro_velocity_absolute_pending_value[macro_idx] = velocity_absolute;
            macro_velocity_offset_pending[macro_idx] = true;
            macro_velocity_offset_pending_value[macro_idx] = 0;
            
            if (velocity_absolute == 0) {
                dprintf("dynamic macro: set velocity absolute target for macro %d to ORIGINAL, reset offset to 0 (queued for loop trigger)\n", macro_num);
            } else {
                dprintf("dynamic macro: set velocity absolute target for macro %d to %d, reset offset to 0 (queued for loop trigger)\n", 
                        macro_num, velocity_absolute);
            }
        } else {
            // No macros playing - apply immediately
            macro_velocity_absolute[macro_idx] = velocity_absolute;
            macro_velocity_offset[macro_idx] = 0;
            if (velocity_absolute == 0) {
                dprintf("dynamic macro: immediately set velocity absolute for macro %d to ORIGINAL, reset offset to 0\n", macro_num);
            } else {
                dprintf("dynamic macro: immediately set velocity absolute for macro %d to %d, reset offset to 0\n", 
                        macro_num, velocity_absolute);
            }
        }
    }
}

// Octave doubler getter/setter functions
uint8_t get_macro_octave_doubler(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_octave_doubler[macro_num - 1];
    }
    return 0;
}

int8_t get_macro_octave_doubler_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_octave_doubler_target[macro_num - 1];
    }
    return 0;
}

void set_macro_octave_doubler_target(uint8_t macro_num, int8_t octave_offset) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;
        
        // Set the target immediately
        macro_octave_doubler_target[macro_idx] = octave_offset;
        
        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            // Macros are playing - queue the change for next loop trigger
            macro_octave_doubler_pending[macro_idx] = true;
            macro_octave_doubler_pending_value[macro_idx] = octave_offset;
            
            dprintf("dynamic macro: set octave doubler target for macro %d (queued for loop trigger)\n", macro_num);
        } else {
            // No macros playing - apply immediately
            macro_octave_doubler[macro_idx] = octave_offset;
            dprintf("dynamic macro: immediately applied octave doubler for macro %d\n", macro_num);
        }
    }
}

void reset_all_macro_octave_doubler_targets(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_octave_doubler_target[i] = 0;
        macro_octave_doubler_pending[i] = false;
        macro_octave_doubler_pending_value[i] = 0;
        macro_octave_doubler[i] = 0;
    }
    dprintf("dynamic macro: reset all octave doubler targets and values to OFF\n");
}

// New reset functions for velocity offset
void reset_all_macro_velocity_offset_targets(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_velocity_offset_target[i] = 0;
        macro_velocity_offset_pending[i] = false;
        macro_velocity_offset_pending_value[i] = 0;
        macro_velocity_offset[i] = 0;
    }
    dprintf("dynamic macro: reset all velocity offset targets and values to 0\n");
}

// New reset functions for velocity absolute
void reset_all_macro_velocity_absolute(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_velocity_absolute[i] = 0;
    }
    dprintf("dynamic macro: reset all velocity absolute values to 0 (use original velocities)\n");
}

void reset_all_macro_velocity_absolute_targets(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_velocity_absolute_target[i] = 0;
        macro_velocity_absolute_pending[i] = false;
        macro_velocity_absolute_pending_value[i] = 0;
        macro_velocity_absolute[i] = 0;
    }
    dprintf("dynamic macro: reset all velocity absolute targets and values to 0\n");
}

// =============================================================================
// VELOCITY RANGE AND CURVE GETTER/SETTER FUNCTIONS
// =============================================================================

// Macro recording curve
uint8_t get_macro_recording_curve(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_recording_curve[macro_num - 1];
    }
    return 2;  // Default MEDIUM
}

void set_macro_recording_curve_target(uint8_t macro_num, uint8_t curve) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;

        // Clamp to valid range (0-4)
        if (curve > 4) curve = 4;

        macro_recording_curve_target[macro_idx] = curve;

        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }

        if (any_macros_playing) {
            macro_recording_curve_pending[macro_idx] = true;
            macro_recording_curve_pending_value[macro_idx] = curve;
            dprintf("dynamic macro: set recording curve target for macro %d to %d (queued for loop trigger)\n", macro_num, curve);
        } else {
            macro_recording_curve[macro_idx] = curve;
            dprintf("dynamic macro: immediately applied recording curve %d for macro %d\n", curve, macro_num);
        }
    }
}

// Macro recording min
uint8_t get_macro_recording_min(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_recording_min[macro_num - 1];
    }
    return 1;
}

void set_macro_recording_min_target(uint8_t macro_num, uint8_t min) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;

        // Clamp to valid range (1-127)
        if (min < 1) min = 1;
        if (min > 127) min = 127;

        macro_recording_min_target[macro_idx] = min;

        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }

        if (any_macros_playing) {
            macro_recording_min_pending[macro_idx] = true;
            macro_recording_min_pending_value[macro_idx] = min;
            dprintf("dynamic macro: set recording min target for macro %d to %d (queued for loop trigger)\n", macro_num, min);
        } else {
            macro_recording_min[macro_idx] = min;
            dprintf("dynamic macro: immediately applied recording min %d for macro %d\n", min, macro_num);
        }
    }
}

// Macro recording max
uint8_t get_macro_recording_max(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return macro_recording_max[macro_num - 1];
    }
    return 127;
}

void set_macro_recording_max_target(uint8_t macro_num, uint8_t max) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;

        // Clamp to valid range (1-127)
        if (max < 1) max = 1;
        if (max > 127) max = 127;

        macro_recording_max_target[macro_idx] = max;

        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }

        if (any_macros_playing) {
            macro_recording_max_pending[macro_idx] = true;
            macro_recording_max_pending_value[macro_idx] = max;
            dprintf("dynamic macro: set recording max target for macro %d to %d (queued for loop trigger)\n", macro_num, max);
        } else {
            macro_recording_max[macro_idx] = max;
            dprintf("dynamic macro: immediately applied recording max %d for macro %d\n", max, macro_num);
        }
    }
}

// Reset all transpose values to 0
void reset_all_macro_transpose(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_transpose[i] = 0;
    }
    dprintf("dynamic macro: reset all transpose values to 0\n");
}

// Reset all channel overrides to 0 (use original channels)
void reset_all_macro_channel_absolute(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_channel_absolute[i] = 0;
    }
    dprintf("dynamic macro: reset all channel absolute values to 0 (use original channels)\n");
}

// Reset all velocity offsets to 0
void reset_all_macro_velocity_offset(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_velocity_offset[i] = 0;
    }
    dprintf("dynamic macro: reset all velocity offsets to 0\n");
}

void reset_all_macro_channel_absolute_targets(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_channel_absolute_target[i] = 0;
        macro_channel_absolute_pending[i] = false;
        macro_channel_absolute_pending_value[i] = 0;
        macro_channel_absolute[i] = 0;
    }
    dprintf("dynamic macro: reset all channel absolute targets and values to 0 (use original channels)\n");
}



void reset_macro_transformations(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t idx = macro_num - 1;  // Convert to 0-based index
        
        // Reset transpose
        set_macro_transpose_target(macro_num, 0);
        macro_transpose_pending[idx] = false;
        macro_transpose_pending_value[idx] = 0;
        
        // Reset channel offset
        set_macro_channel_offset_target(macro_num, 0);
        macro_channel_offset_pending[idx] = false;
        macro_channel_offset_pending_value[idx] = 0;
        
        // Reset channel absolute
        set_macro_channel_absolute_target(macro_num, 0);
        macro_channel_absolute_pending[idx] = false;
        macro_channel_absolute_pending_value[idx] = 0;
        
        // Reset velocity offset
        set_macro_velocity_offset_target(macro_num, 0);
        macro_velocity_offset_pending[idx] = false;
        macro_velocity_offset_pending_value[idx] = 0;
        
        // Reset velocity absolute
        set_macro_velocity_absolute_target(macro_num, 0);
        macro_velocity_absolute_pending[idx] = false;
        macro_velocity_absolute_pending_value[idx] = 0;
        
        // Reset octave doubler
        set_macro_octave_doubler_target(macro_num, 0);
        macro_octave_doubler_pending[idx] = false;
        macro_octave_doubler_pending_value[idx] = 0;
        
        // Reset overdub merge pending
        overdub_merge_pending[idx] = false;
        
        dprintf("dynamic macro: reset all transformations and pending flags for macro %d\n", macro_num);
    }
}

// ADD THESE FUNCTIONS after the existing transformation functions (around line 1950)
// Find the function: void reset_all_macro_octave_doubler_targets(void)
// ADD THESE FUNCTIONS AFTER IT:

// Overdub transformation getter/setter functions
int8_t get_overdub_transpose_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return overdub_transpose_target[macro_num - 1];
    }
    return 0;
}

void set_overdub_transpose_target(uint8_t macro_num, int8_t transpose_value) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        if (transpose_value < -127) transpose_value = -127;
        else if (transpose_value > 127) transpose_value = 127;
        
        uint8_t macro_idx = macro_num - 1;
        overdub_transpose_target[macro_idx] = transpose_value;
        
        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            overdub_transpose_pending[macro_idx] = true;
            overdub_transpose_pending_value[macro_idx] = transpose_value;
            dprintf("dynamic macro: set overdub transpose target for macro %d to %d semitones (queued)\n", 
                    macro_num, transpose_value);
        } else {
            overdub_transpose[macro_idx] = transpose_value;
            dprintf("dynamic macro: immediately applied overdub transpose for macro %d to %d semitones\n", 
                    macro_num, transpose_value);
        }
    }
}

int8_t get_overdub_channel_offset_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return overdub_channel_offset_target[macro_num - 1];
    }
    return 0;
}

void set_overdub_channel_offset_target(uint8_t macro_num, int8_t channel_offset) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        if (channel_offset < -127) channel_offset = -127;
        else if (channel_offset > 127) channel_offset = 127;
        
        uint8_t macro_idx = macro_num - 1;
        overdub_channel_offset_target[macro_idx] = channel_offset;
        
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            overdub_channel_offset_pending[macro_idx] = true;
            overdub_channel_offset_pending_value[macro_idx] = channel_offset;
            dprintf("dynamic macro: set overdub channel offset target for macro %d to %+d (queued)\n", 
                    macro_num, channel_offset);
        } else {
            overdub_channel_offset[macro_idx] = channel_offset;
            dprintf("dynamic macro: immediately applied overdub channel offset for macro %d to %+d\n", 
                    macro_num, channel_offset);
        }
    }
}

uint8_t get_overdub_channel_absolute_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return overdub_channel_absolute_target[macro_num - 1];
    }
    return 0;
}

void set_overdub_channel_absolute_target(uint8_t macro_num, uint8_t channel_absolute) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        if (channel_absolute > 16) channel_absolute = 16;
        
        uint8_t macro_idx = macro_num - 1;
        overdub_channel_absolute_target[macro_idx] = channel_absolute;
        overdub_channel_offset_target[macro_idx] = 0; // Reset offset when setting absolute
        
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            overdub_channel_absolute_pending[macro_idx] = true;
            overdub_channel_absolute_pending_value[macro_idx] = channel_absolute;
            overdub_channel_offset_pending[macro_idx] = true;
            overdub_channel_offset_pending_value[macro_idx] = 0;
            
            if (channel_absolute == 0) {
                dprintf("dynamic macro: set overdub channel absolute target for macro %d to ORIGINAL (queued)\n", macro_num);
            } else {
                dprintf("dynamic macro: set overdub channel absolute target for macro %d to %d (queued)\n", 
                        macro_num, channel_absolute);
            }
        } else {
            overdub_channel_absolute[macro_idx] = channel_absolute;
            overdub_channel_offset[macro_idx] = 0;
            if (channel_absolute == 0) {
                dprintf("dynamic macro: immediately set overdub channel absolute for macro %d to ORIGINAL\n", macro_num);
            } else {
                dprintf("dynamic macro: immediately set overdub channel absolute for macro %d to %d\n", 
                        macro_num, channel_absolute);
            }
        }
    }
}

int8_t get_overdub_velocity_offset_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return overdub_velocity_offset_target[macro_num - 1];
    }
    return 0;
}

void set_overdub_velocity_offset_target(uint8_t macro_num, int8_t velocity_offset) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        if (velocity_offset < -127) velocity_offset = -127;
        else if (velocity_offset > 127) velocity_offset = 127;
        
        uint8_t macro_idx = macro_num - 1;
        overdub_velocity_offset_target[macro_idx] = velocity_offset;
        
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            overdub_velocity_offset_pending[macro_idx] = true;
            overdub_velocity_offset_pending_value[macro_idx] = velocity_offset;
            dprintf("dynamic macro: set overdub velocity offset target for macro %d to %+d (queued)\n", 
                    macro_num, velocity_offset);
        } else {
            overdub_velocity_offset[macro_idx] = velocity_offset;
            dprintf("dynamic macro: immediately applied overdub velocity offset for macro %d to %+d\n", 
                    macro_num, velocity_offset);
        }
    }
}

uint8_t get_overdub_velocity_absolute_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return overdub_velocity_absolute_target[macro_num - 1];
    }
    return 0;
}

void set_overdub_velocity_absolute_target(uint8_t macro_num, uint8_t velocity_absolute) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        if (velocity_absolute > 127) velocity_absolute = 127;
        
        uint8_t macro_idx = macro_num - 1;
        overdub_velocity_absolute_target[macro_idx] = velocity_absolute;
        overdub_velocity_offset_target[macro_idx] = 0; // Reset offset when setting absolute
        
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            overdub_velocity_absolute_pending[macro_idx] = true;
            overdub_velocity_absolute_pending_value[macro_idx] = velocity_absolute;
            overdub_velocity_offset_pending[macro_idx] = true;
            overdub_velocity_offset_pending_value[macro_idx] = 0;
            
            if (velocity_absolute == 0) {
                dprintf("dynamic macro: set overdub velocity absolute target for macro %d to ORIGINAL (queued)\n", macro_num);
            } else {
                dprintf("dynamic macro: set overdub velocity absolute target for macro %d to %d (queued)\n", 
                        macro_num, velocity_absolute);
            }
        } else {
            overdub_velocity_absolute[macro_idx] = velocity_absolute;
            overdub_velocity_offset[macro_idx] = 0;
            if (velocity_absolute == 0) {
                dprintf("dynamic macro: immediately set overdub velocity absolute for macro %d to ORIGINAL\n", macro_num);
            } else {
                dprintf("dynamic macro: immediately set overdub velocity absolute for macro %d to %d\n", 
                        macro_num, velocity_absolute);
            }
        }
    }
}

int8_t get_overdub_octave_doubler_target(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        return overdub_octave_doubler_target[macro_num - 1];
    }
    return 0;
}

void set_overdub_octave_doubler_target(uint8_t macro_num, int8_t octave_offset) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t macro_idx = macro_num - 1;
        overdub_octave_doubler_target[macro_idx] = octave_offset;
        
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        if (any_macros_playing) {
            overdub_octave_doubler_pending[macro_idx] = true;
            overdub_octave_doubler_pending_value[macro_idx] = octave_offset;
            dprintf("dynamic macro: set overdub octave doubler target for macro %d (queued)\n", macro_num);
        } else {
            overdub_octave_doubler[macro_idx] = octave_offset;
            dprintf("dynamic macro: immediately applied overdub octave doubler for macro %d\n", macro_num);
        }
    }
}

// Reset functions for overdub transformations
void reset_all_overdub_transformations(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        overdub_transpose[i] = 0;
        overdub_transpose_target[i] = 0;
        overdub_transpose_pending[i] = false;
        overdub_transpose_pending_value[i] = 0;
        
        overdub_channel_offset[i] = 0;
        overdub_channel_offset_target[i] = 0;
        overdub_channel_offset_pending[i] = false;
        overdub_channel_offset_pending_value[i] = 0;
        
        overdub_channel_absolute[i] = 0;
        overdub_channel_absolute_target[i] = 0;
        overdub_channel_absolute_pending[i] = false;
        overdub_channel_absolute_pending_value[i] = 0;
        
        overdub_velocity_offset[i] = 0;
        overdub_velocity_offset_target[i] = 0;
        overdub_velocity_offset_pending[i] = false;
        overdub_velocity_offset_pending_value[i] = 0;
        
        overdub_velocity_absolute[i] = 0;
        overdub_velocity_absolute_target[i] = 0;
        overdub_velocity_absolute_pending[i] = false;
        overdub_velocity_absolute_pending_value[i] = 0;
        
        overdub_octave_doubler[i] = 0;
        overdub_octave_doubler_target[i] = 0;
        overdub_octave_doubler_pending[i] = false;
        overdub_octave_doubler_pending_value[i] = 0;
    }
    dprintf("dynamic macro: reset all overdub transformations\n");
}

void reset_overdub_transformations(uint8_t macro_num) {
    if (macro_num >= 1 && macro_num <= MAX_MACROS) {
        uint8_t idx = macro_num - 1;
        
        set_overdub_transpose_target(macro_num, 0);
        overdub_transpose_pending[idx] = false;
        overdub_transpose_pending_value[idx] = 0;
        
        set_overdub_channel_offset_target(macro_num, 0);
        overdub_channel_offset_pending[idx] = false;
        overdub_channel_offset_pending_value[idx] = 0;
        
        set_overdub_channel_absolute_target(macro_num, 0);
        overdub_channel_absolute_pending[idx] = false;
        overdub_channel_absolute_pending_value[idx] = 0;
        
        set_overdub_velocity_offset_target(macro_num, 0);
        overdub_velocity_offset_pending[idx] = false;
        overdub_velocity_offset_pending_value[idx] = 0;
        
        set_overdub_velocity_absolute_target(macro_num, 0);
        overdub_velocity_absolute_pending[idx] = false;
        overdub_velocity_absolute_pending_value[idx] = 0;
        
        set_overdub_octave_doubler_target(macro_num, 0);
        overdub_octave_doubler_pending[idx] = false;
        overdub_octave_doubler_pending_value[idx] = 0;
        
        dprintf("dynamic macro: reset all overdub transformations for macro %d\n", macro_num);
    }
}

// Expose modifier state to other files
bool is_any_macro_modifier_active(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_modifier_held[i]) {
            return true;
        }
    }
    return false;
}

// Get which macro modifier is currently active (returns 0 if none, 1-4 if active)
uint8_t get_active_macro_modifier(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_modifier_held[i]) {
            return i + 1; // Return macro number (1-4)
        }
    }
    return 0; // No modifier active
}

static void process_pending_states_for_macro(uint8_t macro_idx) {
    uint8_t macro_num = macro_idx + 1;
    
    dprintf("dynamic macro: processing pending states immediately for macro %d (no other macros playing)\n", macro_num);
    
    // Process pending transformations that affect note tracking (need cleanup)
    if (macro_transpose_pending[macro_idx]) {
        // Clear notes before applying transpose change
        cleanup_notes_from_macro(macro_num);
        if (overdub_playback[macro_idx].is_playing) {
            cleanup_notes_from_macro(macro_num + MAX_MACROS);
        }
        
        macro_transpose[macro_idx] = macro_transpose_pending_value[macro_idx];
        macro_transpose_pending[macro_idx] = false;
        dprintf("dynamic macro: applied pending transpose change for macro %d to %d semitones\n", 
                macro_num, macro_transpose[macro_idx]);
    }
    
    if (macro_channel_offset_pending[macro_idx]) {
        // Clear notes before applying channel offset change
        cleanup_notes_from_macro(macro_num);
        if (overdub_playback[macro_idx].is_playing) {
            cleanup_notes_from_macro(macro_num + MAX_MACROS);
        }
        
        macro_channel_offset[macro_idx] = macro_channel_offset_pending_value[macro_idx];
        macro_channel_offset_pending[macro_idx] = false;
        dprintf("dynamic macro: applied pending channel offset change for macro %d to %+d\n", 
                macro_num, macro_channel_offset[macro_idx]);
    }
    
    if (macro_channel_absolute_pending[macro_idx]) {
        // Clear notes before applying channel absolute change
        cleanup_notes_from_macro(macro_num);
        if (overdub_playback[macro_idx].is_playing) {
            cleanup_notes_from_macro(macro_num + MAX_MACROS);
        }
        
        macro_channel_absolute[macro_idx] = macro_channel_absolute_pending_value[macro_idx];
        macro_channel_absolute_pending[macro_idx] = false;
        if (macro_channel_absolute[macro_idx] == 0) {
            dprintf("dynamic macro: applied pending channel absolute change for macro %d to ORIGINAL\n", macro_num);
        } else {
            dprintf("dynamic macro: applied pending channel absolute change for macro %d to %d\n", 
                    macro_num, macro_channel_absolute[macro_idx]);
        }
    }
    
    // Velocity changes don't need note cleanup (don't affect note tracking)
    if (macro_velocity_offset_pending[macro_idx]) {
        macro_velocity_offset[macro_idx] = macro_velocity_offset_pending_value[macro_idx];
        macro_velocity_offset_pending[macro_idx] = false;
        dprintf("dynamic macro: applied pending velocity offset change for macro %d to %+d\n", 
                macro_num, macro_velocity_offset[macro_idx]);
    }
    
    if (macro_velocity_absolute_pending[macro_idx]) {
        macro_velocity_absolute[macro_idx] = macro_velocity_absolute_pending_value[macro_idx];
        macro_velocity_absolute_pending[macro_idx] = false;
        if (macro_velocity_absolute[macro_idx] == 0) {
            dprintf("dynamic macro: applied pending velocity absolute change for macro %d to ORIGINAL\n", macro_num);
        } else {
            dprintf("dynamic macro: applied pending velocity absolute change for macro %d to %d\n", 
                    macro_num, macro_velocity_absolute[macro_idx]);
        }
    }
    
    if (macro_octave_doubler_pending[macro_idx]) {
        macro_octave_doubler[macro_idx] = macro_octave_doubler_pending_value[macro_idx];
        macro_octave_doubler_pending[macro_idx] = false;
        dprintf("dynamic macro: applied pending octave doubler change for macro %d\n", macro_num);
    }
    
    // Process pending overdub mute/unmute states
    if (overdub_mute_pending[macro_idx]) {
        // Mute the overdub
        overdub_muted[macro_idx] = true;
        
        // Stop overdub playback if playing
        if (overdub_playback[macro_idx].is_playing) {
            dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
            overdub_playback[macro_idx].is_playing = false;
            overdub_playback[macro_idx].current = NULL;
            dprintf("dynamic macro: muted overdub for macro %d immediately\n", macro_num);
        }
        
        // Clear the pending flag
        overdub_mute_pending[macro_idx] = false;
    }
    
    if (overdub_unmute_pending[macro_idx]) {
        // Unmute the overdub
        overdub_muted[macro_idx] = false;
        
        // Since we're starting fresh playback, we can start overdub from beginning
        // (no need for the complex loop position calculation from check_loop_trigger)
        if (overdub_buffers[macro_idx] != NULL &&
            overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx]) {
            
            // Set up overdub playback from beginning (simpler than loop trigger version)
            macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
            overdub_state->current = overdub_buffers[macro_idx];
            overdub_state->end = overdub_buffer_ends[macro_idx];
            overdub_state->direction = +1;
            overdub_state->timer = timer_read32();
            overdub_state->buffer_start = overdub_buffers[macro_idx];
            overdub_state->is_playing = true;
            overdub_state->waiting_for_loop_gap = false;
            overdub_state->next_event_time = 0;
            
            dprintf("dynamic macro: unmuted overdub for macro %d (starting from beginning)\n", macro_num);
        }
        
        // Clear the pending flag
        overdub_unmute_pending[macro_idx] = false;
    }
}

// Modified dynamic_macro_play function to link playback
void dynamic_macro_play(midi_event_t *macro_buffer, midi_event_t *macro_end, int8_t direction) {
    // Find which macro this is
    uint8_t macro_num = 0;
    for (uint8_t i = 1; i <= MAX_MACROS; i++) {
        if (macro_buffer == get_macro_buffer(i)) {
            macro_num = i;
            break;
        }
    }
    
    if (macro_num == 0) {
        dprintf("dynamic macro: error - invalid macro buffer\n");
        return;
    }
    
    uint8_t macro_idx = macro_num - 1;
    dprintf("dynamic macro: slot %d playback\n", macro_num);
    
    // Get the appropriate playback state
    macro_playback_state_t *state = &macro_playback[macro_idx];
    
    if (state->is_playing) {
        // If already playing, stop playback of both macro and overdub
        dynamic_macro_cleanup_notes_for_state(state);
        state->is_playing = false;
        state->current = NULL;
        
        // LINKED PLAYBACK: Also stop overdub playback
        if (overdub_playback[macro_idx].is_playing && !overdub_advanced_mode) {
            dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
            overdub_playback[macro_idx].is_playing = false;
            overdub_playback[macro_idx].current = NULL;
			send_loop_message(overdub_stop_playing_cc[macro_num - 1], 127);
            dprintf("dynamic macro: stopped overdub for macro %d (linked stop)\n", macro_num);
        }
        
        return;
    }
    
    // Check if macro is empty
    if (macro_buffer == macro_end) {
        dprintf("dynamic macro: empty, nothing to play\n");
        return;
    }
    
    // Start main macro playback
    state->current = macro_buffer;
    state->end = macro_end;
    state->direction = direction;
    state->timer = timer_read32();
    state->buffer_start = macro_buffer;
    state->is_playing = true;
    state->waiting_for_loop_gap = false;
    state->next_event_time = 0;
	reset_bpm_timing_for_loop_start();
	process_pending_states_for_macro(macro_idx);
    
if (overdub_advanced_mode) {
        // ADVANCED MODE: Do NOT auto-start overdub when parent macro starts
        // Independent overdubs are controlled separately
        dprintf("dynamic macro: skipped auto-start of independent overdub for macro %d\n", macro_num);
    } else {
        // ORIGINAL MODE: LINKED PLAYBACK - start overdub with parent macro
        if (overdub_buffers[macro_idx] != NULL && 
            overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx] &&
            !overdub_muted[macro_idx]) {
            
            // Start overdub playback synchronously with main macro
            macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
            overdub_state->current = overdub_buffers[macro_idx];
            overdub_state->end = overdub_buffer_ends[macro_idx];
            overdub_state->direction = direction;
            overdub_state->timer = state->timer;  // Use the same timer as main macro for sync
            overdub_state->buffer_start = overdub_buffers[macro_idx];
            overdub_state->is_playing = true;
            overdub_state->waiting_for_loop_gap = false;
            overdub_state->next_event_time = 0;
            send_loop_message(overdub_start_playing_cc[macro_num - 1], 127);
            dprintf("dynamic macro: also started overdub playback for macro %d (linked)\n", macro_num);
        }
    }
    // Check suppression flag before sending start playing message
    if (!suppress_next_loop_start_playing[macro_num - 1]) {
        send_loop_message(loop_start_playing_cc[macro_num - 1], 127);
    } else {
        // Clear the suppression flag after using it
        suppress_next_loop_start_playing[macro_num - 1] = false;
        dprintf("dynamic macro: suppressed loop start playing message for macro %d (just finished recording)\n", macro_num);
    }
    
    dynamic_macro_play_user(direction);
    randomize_order();
}

void dynamic_macro_actual_start(uint32_t *start_time) {
    // This is called when we receive the first MIDI note after priming
    uint32_t original_start_time = timer_read32();
    is_macro_primed = false;
    first_note_recorded = true;
    
	    // ADD THIS SECTION - Record a dummy event so the macro isn't considered empty
    if (macro_id > 0 && macro_pointer != NULL) {
        midi_event_t *macro_start = get_macro_buffer(macro_id);
        midi_event_t *macro_end = macro_start + (MACRO_BUFFER_SIZE / sizeof(midi_event_t));
        
        // Only add dummy if buffer has space and we're at the start
        if (macro_pointer < macro_end) {
            macro_pointer->type = MIDI_EVENT_DUMMY;
            macro_pointer->channel = 0;
            macro_pointer->note = 0;
            macro_pointer->raw_travel = 0;
            macro_pointer->timestamp = 0;  // Place at the very start

            macro_pointer++;
            is_macro_empty = false;

            dprintf("dynamic macro: recorded dummy event to mark recording start\n");
        }
    }
	
    // If this was a slave recording with preroll collection active
    if (collecting_preroll) {
        dprintf("dynamic macro: processing preroll for slave recording\n");
        
        // Calculate the cutoff time - only include events within PREROLL_TIME_MS
        uint32_t cutoff_time = original_start_time - PREROLL_TIME_MS;
        
        // Insert preroll events at the beginning of the macro
        if (preroll_buffer_count > 0 && macro_pointer != NULL) {
            dprintf("dynamic macro: adding %d preroll events\n", preroll_buffer_count);
            
            // Find the earliest preroll event that will be included
            uint32_t earliest_event_time = UINT32_MAX;
            uint8_t oldest_idx = (preroll_buffer_index + PREROLL_BUFFER_SIZE - preroll_buffer_count) % PREROLL_BUFFER_SIZE;
            
            for (uint8_t i = 0; i < preroll_buffer_count; i++) {
                uint8_t idx = (oldest_idx + i) % PREROLL_BUFFER_SIZE;
                uint32_t event_time = preroll_start_time + preroll_buffer[idx].timestamp;
                
                if (event_time >= cutoff_time && event_time < earliest_event_time) {
                    earliest_event_time = event_time;
                }
            }
            
            // Calculate the time offset between the earliest preroll event and the original start
            uint32_t preroll_offset = 0;
            if (earliest_event_time != UINT32_MAX && earliest_event_time < original_start_time) {
                preroll_offset = original_start_time - earliest_event_time;
                dprintf("dynamic macro: preroll offset is %lu ms\n", preroll_offset);
            }
            
            // Keep the original start time for main recording - DON'T adjust it
            *start_time = original_start_time;
            
            // Get the oldest event index in our circular buffer
            midi_event_t *original_start = macro_pointer;
            macro_pointer += preroll_buffer_count;
            
            // Move the preroll events to the beginning with timestamps relative to original start
            uint8_t event_count = 0;
            for (uint8_t i = 0; i < preroll_buffer_count; i++) {
                uint8_t idx = (oldest_idx + i) % PREROLL_BUFFER_SIZE;
                
                // Only include events within our preroll time window
                uint32_t event_time = preroll_start_time + preroll_buffer[idx].timestamp;
                if (event_time >= cutoff_time) {
                    // Calculate how far before the original start this event was
                    uint32_t time_before_start = original_start_time - event_time;
                    
                    // Place it at the beginning, offset by how early it was
                    // The earliest event gets timestamp 0, others are offset from that
                    uint32_t adjusted_timestamp = preroll_offset - time_before_start;
                    
                    // Copy event to the macro buffer with adjusted timestamp
                    original_start[event_count].type = preroll_buffer[idx].type;
                    original_start[event_count].channel = preroll_buffer[idx].channel;
                    original_start[event_count].note = preroll_buffer[idx].note;
                    original_start[event_count].raw_travel = preroll_buffer[idx].raw_travel;
                    original_start[event_count].timestamp = adjusted_timestamp;

                    dprintf("preroll: added event type:%d ch:%d note:%d vel:%d at time %lu ms (was %lu ms before start)\n",
                            original_start[event_count].type, original_start[event_count].channel,
                            original_start[event_count].note, original_start[event_count].raw_travel,
                            adjusted_timestamp, time_before_start);
                    
                    event_count++;
                }
            }
            
            // Adjust macro_pointer to reflect actual events added
            macro_pointer = original_start + event_count;
        } else {
            *start_time = original_start_time;
        }
        
        // Stop collecting preroll
        collecting_preroll = false;
    } else {
        *start_time = original_start_time;
    }
    
    // Check current sustain state
    recording_sustain_active = get_live_sustain_state();
    
    // Signal that actual recording has started (blink once more)
     
	    send_loop_message(loop_start_recording_cc[macro_id - 1], 127);  // ADD THIS LINE
    
    dprintln("dynamic macro recording: started from first MIDI note");
}

void dynamic_macro_record_midi_event(midi_event_t *macro_buffer, midi_event_t **macro_pointer,
                                    midi_event_t *macro_end, int8_t direction,
                                    uint8_t type, uint8_t channel, uint8_t note, uint8_t raw_travel,
                                    uint32_t *start_time, uint8_t macro_id) {
    // If we're primed but haven't started recording yet, and this is a note-on event
    if (is_macro_primed && !first_note_recorded && type == MIDI_EVENT_NOTE_ON) {
        dynamic_macro_actual_start(start_time);
    }
    
    // Don't record if we're only primed and waiting for the first note-on
    if (is_macro_primed && !first_note_recorded) {
        return;
    }
    
    // NEVER record sustain CC events - macros should only contain note events
    if (type == MIDI_EVENT_CC && note == 0x40) {
        return;
    }
    
    if (*macro_pointer < macro_end) {
        (*macro_pointer)->type = type;
        (*macro_pointer)->channel = channel;
        (*macro_pointer)->note = note;
        (*macro_pointer)->raw_travel = raw_travel;

        uint32_t now = timer_read32();
        (*macro_pointer)->timestamp = now - *start_time;

        dprintf("dynamic macro: recorded MIDI event type:%d ch:%d note/cc:%d raw:%d at time %lu ms\n",
                type, channel, note, raw_travel, (*macro_pointer)->timestamp);

        *macro_pointer += direction;
        is_macro_empty = false;
    } else {
         
    }

    dprintf("dynamic macro: slot %d length: %d/%d\n", 
            macro_id, 
            (int)(*macro_pointer - macro_buffer), 
            (int)(macro_end - macro_buffer));
}

void dynamic_macro_record_end(midi_event_t *macro_buffer, midi_event_t *macro_pointer, int8_t direction, midi_event_t **macro_end, uint32_t *start_time) {
    dynamic_macro_record_end_user(direction);

    // If the macro was never actually started (no MIDI notes), reset it
    //if (is_macro_primed && !first_note_recorded) {
   //     is_macro_primed = false;
    //    *macro_end = macro_buffer; // Set the end pointer to start (empty macro)
    //    is_macro_empty = true;
    //    return;
   // } << AUTO DELETES LOOP IF NO NOTES RECORDED
	
    // SEND NOTE-OFFS FOR ALL LIVE NOTES when recording ends
    force_clear_all_live_notes();
    dprintf("dynamic macro: cleared all live notes at end of recording\n");
    
    // If sustain was active, send a sustain off event
    if (recording_sustain_active) {
        recording_sustain_active = false;
    }
    
	int32_t min_timestamp = 0;  // Start with 0
	uint32_t event_count = macro_pointer - macro_buffer;
	bool needs_normalization = false;

	if (event_count > 0) {
		// Find the most negative timestamp (if any)
		for (midi_event_t *event = macro_buffer; event < macro_pointer; event++) {
			int32_t signed_timestamp = (int32_t)event->timestamp;
			if (signed_timestamp < min_timestamp) {
				min_timestamp = signed_timestamp;
				needs_normalization = true;
			}
		}
		
		// Only shift if we found negative timestamps
		// (This handles old-style preroll or other edge cases, but should be rare now)
		if (needs_normalization && min_timestamp < 0) {
			uint32_t shift_amount = (uint32_t)(-min_timestamp);  // Convert to positive shift
			
			dprintf("dynamic macro: found negative timestamps with minimum %d ms, shifting all events forward by %lu ms\n", 
					min_timestamp, shift_amount);
			
			// Shift all event timestamps forward
			for (midi_event_t *event = macro_buffer; event < macro_pointer; event++) {
				int32_t signed_timestamp = (int32_t)event->timestamp;
				signed_timestamp += shift_amount;  // Add the shift to make it positive
				event->timestamp = (uint32_t)signed_timestamp;
			}
			
			dprintf("dynamic macro: completed timestamp normalization\n");
		} else if (min_timestamp >= 0) {
			dprintf("dynamic macro: all timestamps are already positive, no normalization needed\n");
		}
	}
    
    // Calculate the gap time (time between last event and stopping recording)
    uint32_t stop_time = timer_read32();
    uint32_t last_event_time = 0;
    
    // Find the latest timestamp (now all are positive)
    if (macro_pointer != macro_buffer) {
        for (midi_event_t *event = macro_buffer; event < macro_pointer; event++) {
            if (event->timestamp > last_event_time) {
                last_event_time = event->timestamp;
            }
        }
    }
    
    // Calculate the time between the last event and stopping the recording
    // Adjust for any preroll shift that was applied
    uint32_t recording_duration = stop_time - *start_time;
    uint32_t expected_stop_time = last_event_time;
    
    uint32_t loop_gap_time;
    if (recording_duration > expected_stop_time) {
        loop_gap_time = recording_duration - expected_stop_time;
    } else {
        // Fallback if timing calculation seems off
        loop_gap_time = 1;  // Minimum gap
    }
    
    // If we shifted events due to preroll, adjust the gap time
    if (min_timestamp < 0) {
        uint32_t shift_amount = (uint32_t)(-min_timestamp);
        loop_gap_time += shift_amount;  // Extend gap to account for the shifted start
        
        dprintf("dynamic macro: adjusted loop gap by %lu ms to account for preroll shift\n", shift_amount);
    }
    
    // Find which macro this is
    uint8_t macro_num = 0;
    for (uint8_t i = 1; i <= MAX_MACROS; i++) {
        if (macro_buffer == get_macro_buffer(i)) {
            macro_num = i;
            break;
        }
    }
    
// Store the loop gap time AND calculate/store total loop length
if (macro_num > 0) {
    macro_playback_state_t *state = &macro_playback[macro_num - 1];
    state->loop_gap_time = loop_gap_time;
    
    // Calculate total loop length using the corrected last_event_time
    state->loop_length = last_event_time + loop_gap_time;
    
		// NEW: Auto-quantize to bpm master loop if in synced mode
	// AUTO-QUANTIZE: Different behavior based on unsynced mode
	if ((unsynced_mode_active == 2 || unsynced_mode_active == 5)) {
		// MODE 2 (Fully Unsynced): NEVER quantize
		dprintf("dynamic macro: unsynced mode 2 - no quantization\n");
		
	} else if (unsynced_mode_active == 1 || unsynced_mode_active == 3) {
		// MODE 1 or 3: ALWAYS quantize to nearest quarter note (if BPM exists)
		if (current_bpm > 0) {
			// Calculate quarter note length in milliseconds
			uint32_t quarter_note_ms = (6000000000ULL) / current_bpm;
			
			// Calculate how many quarter notes this loop is
			uint32_t calculated_length = state->loop_length;
			float num_quarter_notes = (float)calculated_length / (float)quarter_note_ms;
			
			// Round to nearest quarter note (minimum 1 quarter note)
			uint32_t rounded_quarter_notes = (uint32_t)(num_quarter_notes + 0.5f);
			if (rounded_quarter_notes < 1) {
				rounded_quarter_notes = 1;
			}
			
			// Cap at reasonable maximum (64 quarter notes = 16 bars)
			if (rounded_quarter_notes > 64) {
				rounded_quarter_notes = 64;
				dprintf("dynamic macro: capped quantization to 64 quarter notes\n");
			}
			
			uint32_t quantized_length = rounded_quarter_notes * quarter_note_ms;
			
			// Adjust loop_gap_time to achieve the quantized length
			if (quantized_length > last_event_time) {
				loop_gap_time = quantized_length - last_event_time;
				state->loop_length = quantized_length;
				
				dprintf("dynamic macro: mode %d - quantized loop %d to %lu quarter notes (%lu ms, was %lu ms)\n", 
						unsynced_mode_active, macro_num, rounded_quarter_notes, quantized_length, calculated_length);
			}
		}
		
	} else if (unsynced_mode_active == 0 || unsynced_mode_active == 4) {
		// MODE 0 (Normal Synced): Behavior depends on whether something is playing
		
		// Check if any other macros or overdubs are playing
		uint8_t playing_count = 0;
		for (uint8_t i = 0; i < MAX_MACROS; i++) {
			if (macro_playback[i].is_playing || overdub_playback[i].is_playing) {
				playing_count++;
			}
		}
		
		if (playing_count > 0) {
			// Something is playing: Use ORIGINAL quantization to master loop multiples
			if (bpm_source_macro != 0 && bpm_source_macro != macro_num) {
				uint8_t master_idx = bpm_source_macro - 1;
				
				// Only quantize if the master loop is actually playing
				if (macro_playback[master_idx].is_playing && !macro_main_muted[master_idx]) {
					uint32_t master_loop_length = macro_playback[master_idx].loop_length;
					
					if (master_loop_length > 0 && master_loop_length < 60000) {
						// Find the closest multiple of master loop length
						uint32_t calculated_length = state->loop_length;
						float multiple = (float)calculated_length / (float)master_loop_length;
						
						// Round to nearest multiple
						uint32_t quantized_length;
						if (multiple < 1.25f) {
							quantized_length = master_loop_length; // 1x
						} else if (multiple < 1.75f) {
							quantized_length = master_loop_length + (master_loop_length / 2); // 1.5x
						} else {
							// Round to nearest integer multiple (cap at 8x)
							uint32_t rounded_multiple = (uint32_t)(multiple + 0.5f);
							if (rounded_multiple > 8) {
								rounded_multiple = 8;
							}
							quantized_length = rounded_multiple * master_loop_length;
						}
						
						// Adjust loop_gap_time to achieve the quantized length
						if (quantized_length > last_event_time) {
							loop_gap_time = quantized_length - last_event_time;
							state->loop_length = quantized_length;
							
							dprintf("dynamic macro: mode 0 - quantized to master loop multiple (%lu ms)\n", 
									quantized_length);
						}
					}
				} else {
					dprintf("dynamic macro: mode 0 - master loop not playing, no quantization\n");
				}
			}
		} else {
			// Nothing is playing: NO quantization
			dprintf("dynamic macro: mode 0 - nothing playing, no quantization\n");
		}
	}
    // ========================================================================
    // BPM CALCULATION WITH MIDI CLOCK INTEGRATION
    // ========================================================================
    
    bool bpm_was_zero = (current_bpm == 0);
    bool bpm_changed = false;
    
    if (current_bpm == 0 && state->loop_length > 1000) {
        // Start with 4-beat assumption
        uint32_t calculated_bpm = (24000000000ULL) / state->loop_length;
        
        // Keep halving if too high (maybe it's 8 beats, 16 beats, etc.)
        while (calculated_bpm > 20000000) {  // While > 200 BPM
            calculated_bpm = calculated_bpm / 2;
        }
        
        // Keep doubling if too low (maybe it's 2 beats, 1 beat, etc.)
        while (calculated_bpm < 8000000) {   // While < 80 BPM
            calculated_bpm = calculated_bpm * 2;
        }
        
        // Check if we got it in range
        if (calculated_bpm >= 6000000 && calculated_bpm <= 20000000) {
            current_bpm = calculated_bpm;
            bpm_source_macro = macro_num;  // Track which macro set the BPM
            bpm_changed = true;
            
            // Store this macro's recording BPM
            macro_recording_bpm[macro_num - 1] = current_bpm;
            macro_has_content[macro_num - 1] = true;
            
            dprintf("dynamic macro: recorded macro %d at BPM %lu.%05lu\n", 
                    macro_num, current_bpm / 100000, current_bpm % 100000);
        } else {
            dprintf("dynamic macro: could not find reasonable BPM for loop length\n");
        }
    } else {
        // Macro recorded while BPM already exists - store current BPM as this macro's base
        macro_recording_bpm[macro_num - 1] = current_bpm;
        macro_has_content[macro_num - 1] = true;
        
        dprintf("dynamic macro: recorded macro %d at current BPM %lu.%05lu\n", 
                macro_num, current_bpm / 100000, current_bpm % 100000);
    }
    
    // ========================================================================
    // MIDI CLOCK INTEGRATION
    // ========================================================================
    
    // If BPM was just set from loop AND we're not receiving external clock
    if (bpm_changed && bpm_was_zero && !is_external_clock_active()) {
        // Start internal MIDI clock automatically
        internal_clock_start();
        dprintf("MIDI clock: Auto-started from loop recording\n");
    }
    // If BPM changed and internal clock is already running
    else if (bpm_changed && is_internal_clock_active()) {
        // Update the running clock's tempo
        internal_clock_tempo_changed();
        dprintf("MIDI clock: Tempo updated from loop\n");
    }

        
        // ALLOCATE OVERDUB BUFFER - use remaining space in this macro's allocation
        uint32_t macro_size_used = (macro_pointer - macro_buffer) * sizeof(midi_event_t);
        uint32_t remaining_space = MACRO_BUFFER_SIZE - macro_size_used;
        uint32_t overdub_events = remaining_space / sizeof(midi_event_t);
        
        if (overdub_events > 0) {
            // Set up overdub buffer right after the main macro content
            overdub_buffers[macro_num - 1] = macro_pointer;
            overdub_buffer_ends[macro_num - 1] = macro_pointer;  // Start empty
            overdub_buffer_sizes[macro_num - 1] = overdub_events;
            overdub_muted[macro_num - 1] = false;  // Start unmuted
            
            // Initialize overdub playback state
            overdub_playback[macro_num - 1].buffer_start = overdub_buffers[macro_num - 1];
            overdub_playback[macro_num - 1].loop_length = state->loop_length;
            overdub_playback[macro_num - 1].loop_gap_time = state->loop_gap_time;
            
            dprintf("dynamic macro: allocated %lu events for macro %d overdub buffer\n", 
                    overdub_events, macro_num);
        }
        
        dprintf("dynamic macro: stored loop_length %lu ms for macro %d (preroll normalized)\n", 
                state->loop_length, macro_num);
    }
    
    dprintf("dynamic macro: loop gap time set to %lu ms\n", loop_gap_time);
    dprintf("dynamic macro: slot %d saved, length: %d\n", 
            macro_num, 
            (int)(macro_pointer - macro_buffer));

    *macro_end = macro_pointer;
    if (macro_num > 0) {
        send_loop_message(loop_stop_recording_cc[macro_num - 1], 127);
        // Set flag to suppress next start playing message for this macro
        suppress_next_loop_start_playing[macro_num - 1] = true;
    }
    is_macro_primed = false;
    first_note_recorded = false;
}

// Modify the existing cycle_macro_speed function to handle BPM source macro
static void cycle_macro_speed(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return;
    
    uint8_t macro_idx = macro_num - 1;
    
    // Only allow speed changes if macro has content
    if (!macro_has_content[macro_idx]) {
        dprintf("dynamic macro: cannot change speed of empty macro %d\n", macro_num);
        return;
    }
    
    // If globally paused, modify the stored speed instead of current speed
    float *target_speed = global_playback_paused ? 
                         &macro_speed_before_pause[macro_idx] : 
                         &macro_manual_speed[macro_idx];
    
    // Cycle through: 1.0 -> 1.5 -> 2.0 -> 1.0
    if (*target_speed == 1.0f) {
        *target_speed = 1.5f;
    } else if (*target_speed == 1.5f) {
        *target_speed = 2.0f;
    } else {
        *target_speed = 1.0f;
    }
    
    // Check if this is the BPM source macro
    if (bpm_source_macro == macro_num && !global_playback_paused) {
        // This macro controls BPM - update global BPM but factor out its contribution
        update_bpm_from_source_macro_speed(macro_num, *target_speed);
        
        // Recalculate ALL macro speeds to account for the factored BPM change
        recalculate_all_macro_speeds_for_bpm();
        
        dprintf("dynamic macro: BPM source macro %d speed set to %.1fx (BPM updated, all macros recalculated)\n", 
                macro_num, *target_speed);
    } else {
        // Regular macro - just update its speed normally
        if (!global_playback_paused) {
            recalculate_single_macro_speed(macro_idx);
        }
        
        dprintf("dynamic macro: speed for macro %d set to %.1fx%s\n", 
                macro_num, *target_speed, global_playback_paused ? " (will apply on resume)" : "");
    }
    
     
}


// Modify the existing cycle_macro_slow function similarly
static void cycle_macro_slow(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return;
    
    uint8_t macro_idx = macro_num - 1;
    
    // Only allow speed changes if macro has content
    if (!macro_has_content[macro_idx]) {
        dprintf("dynamic macro: cannot change speed of empty macro %d\n", macro_num);
        return;
    }
    
    // If globally paused, modify the stored speed instead of current speed
    float *target_speed = global_playback_paused ? 
                         &macro_speed_before_pause[macro_idx] : 
                         &macro_manual_speed[macro_idx];
    
    // Cycle through: 1.0 -> 0.5 -> 0.25 -> 1.0
    if (*target_speed == 1.0f) {
        *target_speed = 0.5f;
    } else if (*target_speed == 0.5f) {
        *target_speed = 0.25f;
    } else {
        *target_speed = 1.0f;
    }
    
    // Check if this is the BPM source macro
    if (bpm_source_macro == macro_num && !global_playback_paused) {
        // This macro controls BPM - update global BPM but factor out its contribution
        update_bpm_from_source_macro_speed(macro_num, *target_speed);
        
        // Recalculate ALL macro speeds to account for the factored BPM change
        recalculate_all_macro_speeds_for_bpm();
        
        dprintf("dynamic macro: BPM source macro %d speed set to %.1fx (BPM updated, all macros recalculated)\n", 
                macro_num, *target_speed);
    } else {
        // Regular macro - just update its speed normally
        if (!global_playback_paused) {
            recalculate_single_macro_speed(macro_idx);
        }
        
        dprintf("dynamic macro: speed for macro %d set to %.1fx%s\n", 
                macro_num, *target_speed, global_playback_paused ? " (will apply on resume)" : "");
    }
    
     
}

static void cycle_all_macros_speed(void) {
    dprintf("dynamic macro: cycling ALL macros to faster speed\n");
    
    // Determine the new speed based on the first macro with content
    float new_speed = 1.5f;
    bool found_reference = false;
    
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_has_content[i]) {
            float *current_speed = global_playback_paused ? 
                                  &macro_speed_before_pause[i] : 
                                  &macro_manual_speed[i];
            
            // Cycle: 1.0 -> 1.5 -> 2.0 -> 1.0
            if (*current_speed == 1.0f) {
                new_speed = 1.5f;
            } else if (*current_speed == 1.5f) {
                new_speed = 2.0f;
            } else {
                new_speed = 1.0f;
            }
            
            found_reference = true;
            break;
        }
    }
    
    if (!found_reference) {
        dprintf("dynamic macro: no macros with content to cycle\n");
        return;
    }
    
    // Apply to all macros
    uint8_t macros_changed = 0;
    bool bpm_source_affected = false;
    
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_has_content[i]) {
            float *target_speed = global_playback_paused ? 
                                 &macro_speed_before_pause[i] : 
                                 &macro_manual_speed[i];
            
            *target_speed = new_speed;
            macros_changed++;
            
            if (bpm_source_macro == (i + 1)) {
                bpm_source_affected = true;
            }
        }
    }
    
    // Recalculate speeds
    if (!global_playback_paused) {
        if (bpm_source_affected && bpm_source_macro > 0) {
            update_bpm_from_source_macro_speed(bpm_source_macro, new_speed);
            recalculate_all_macro_speeds_for_bpm();
        } else {
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                if (macro_has_content[i]) {
                    recalculate_single_macro_speed(i);
                }
            }
        }
    }
    
    dprintf("dynamic macro: cycled %d macros to %.1fx%s\n", 
            macros_changed, new_speed, 
            global_playback_paused ? " (will apply on resume)" : "");
    
     
}

static void cycle_all_macros_slow(void) {
    dprintf("dynamic macro: cycling ALL macros to slower speed\n");
    
    // Determine the new speed based on the first macro with content
    float new_speed = 0.5f;
    bool found_reference = false;
    
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_has_content[i]) {
            float *current_speed = global_playback_paused ? 
                                  &macro_speed_before_pause[i] : 
                                  &macro_manual_speed[i];
            
            // Cycle: 1.0 -> 0.5 -> 0.25 -> 1.0
            if (*current_speed == 1.0f) {
                new_speed = 0.5f;
            } else if (*current_speed == 0.5f) {
                new_speed = 0.25f;
            } else {
                new_speed = 1.0f;
            }
            
            found_reference = true;
            break;
        }
    }
    
    if (!found_reference) {
        dprintf("dynamic macro: no macros with content to cycle\n");
        return;
    }
    
    // Apply to all macros
    uint8_t macros_changed = 0;
    bool bpm_source_affected = false;
    
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_has_content[i]) {
            float *target_speed = global_playback_paused ? 
                                 &macro_speed_before_pause[i] : 
                                 &macro_manual_speed[i];
            
            *target_speed = new_speed;
            macros_changed++;
            
            if (bpm_source_macro == (i + 1)) {
                bpm_source_affected = true;
            }
        }
    }
    
    // Recalculate speeds
    if (!global_playback_paused) {
        if (bpm_source_affected && bpm_source_macro > 0) {
            update_bpm_from_source_macro_speed(bpm_source_macro, new_speed);
            recalculate_all_macro_speeds_for_bpm();
        } else {
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                if (macro_has_content[i]) {
                    recalculate_single_macro_speed(i);
                }
            }
        }
    }
    
    dprintf("dynamic macro: cycled %d macros to %.2fx%s\n", 
            macros_changed, new_speed, 
            global_playback_paused ? " (will apply on resume)" : "");
    
     
}


void dynamic_macro_bpm_changed(uint32_t new_bpm) {
    current_bpm = new_bpm;

    // For each macro with content, calculate its effective BPM and update accordingly
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_has_content[i] && macro_recording_bpm[i] > 0) {
            uint8_t macro_num = i + 1;
            uint32_t original_recording_bpm = macro_recording_bpm[i];
            float original_manual_speed = macro_manual_speed[i];
            uint32_t effective_bpm;
            
            if (bpm_source_macro == macro_num) {
                // BPM SOURCE MACRO: Speed modifier affects global BPM, so ignore it for effective BPM calculation
                // The effective BPM is just the original recording BPM (speed modifier is "expressed" in global BPM)
                effective_bpm = original_recording_bpm;
                
                dprintf("dynamic macro: BPM source macro %d - ignoring speed modifier %.1fx, effective BPM = %lu\n", 
                        macro_num, original_manual_speed, effective_bpm / 100000);
            } else {
                // OTHER MACROS: Speed modifier is actual playback speed change, so include it in effective BPM
                effective_bpm = (uint32_t)((float)original_recording_bpm * original_manual_speed);
                
                dprintf("dynamic macro: non-source macro %d - including speed modifier %.1fx, effective BPM = %lu * %.1fx = %lu\n", 
                        macro_num, original_manual_speed, original_recording_bpm / 100000, 
                        original_manual_speed, effective_bpm / 100000);
            }
            
            // Update this macro's recording BPM to the effective BPM
            macro_recording_bpm[i] = effective_bpm;
            
            // Reset manual speed to 1.0x (speed modification is now "baked in")
            macro_manual_speed[i] = 1.0f;
        }
    }
    
    // Now recalculate all macro speeds with the new BPM and updated recording BPMs
    recalculate_all_macro_speeds_for_bpm();
    
    dprintf("dynamic macro: completed external BPM change with speed bake-in\n");
}

// Calculate what the "base BPM" would be without the source macro's speed contribution
static uint32_t calculate_base_bpm_excluding_source(void) {
    if (bpm_source_macro == 0 || bpm_source_macro > MAX_MACROS) {
        return current_bpm; // No source macro
    }
    
    uint8_t source_idx = bpm_source_macro - 1;
    uint32_t source_recording_bpm = macro_recording_bpm[source_idx];
    float source_manual_speed = macro_manual_speed[source_idx];
    
    if (source_recording_bpm == 0 || source_manual_speed == 0) {
        return current_bpm; // Invalid source data
    }
    
    // The "base BPM" is what the BPM would be if the source macro was at 1.0x speed
    // current_bpm = base_bpm * source_manual_speed
    // Therefore: base_bpm = current_bpm / source_manual_speed
    uint32_t base_bpm = (uint32_t)((float)current_bpm / source_manual_speed);
    
    return base_bpm;
}

// Recalculate all macro speeds based on current BPM vs each macro's recording BPM
static void recalculate_all_macro_speeds_for_bpm(void) {
    // Calculate the base BPM (excluding source macro's speed contribution)
    uint32_t base_bpm = calculate_base_bpm_excluding_source();
    
    // Update all macro speeds based on their individual recording BPMs
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_has_content[i] && macro_recording_bpm[i] > 0) {
            // Calculate BPM multiplier for this specific macro
            float bpm_multiplier = (float)base_bpm / (float)macro_recording_bpm[i];
            
            // Final speed = BPM effect × manual speed adjustment
            macro_speed_factor[i] = bpm_multiplier * macro_manual_speed[i];
            
            dprintf("dynamic macro: updated macro %d speed to %.2fx (base BPM %.0f / recording BPM %lu = %.2fx, × manual %.2fx)\n", 
                    i + 1, macro_speed_factor[i], (float)base_bpm / 100000.0f, 
                    macro_recording_bpm[i] / 100000, bpm_multiplier, macro_manual_speed[i]);
        } else {
            // No content or no recording BPM - keep at manual speed only
            macro_speed_factor[i] = macro_manual_speed[i];
        }
    }
}

// Recalculate speed for a single macro
static void recalculate_single_macro_speed(uint8_t macro_idx) {
    if (macro_idx >= MAX_MACROS) return;
    
    if (macro_has_content[macro_idx] && macro_recording_bpm[macro_idx] > 0) {
        // Calculate the base BPM (excluding source macro's speed contribution)
        uint32_t base_bpm = calculate_base_bpm_excluding_source();
        
        // Calculate BPM multiplier for this specific macro
        float bpm_multiplier = (float)base_bpm / (float)macro_recording_bpm[macro_idx];
        
        // Final speed = BPM effect × manual speed adjustment
        macro_speed_factor[macro_idx] = bpm_multiplier * macro_manual_speed[macro_idx];
        
        dprintf("dynamic macro: updated macro %d speed to %.2fx\n", macro_idx + 1, macro_speed_factor[macro_idx]);
    } else {
        // No content - keep at manual speed only
        macro_speed_factor[macro_idx] = macro_manual_speed[macro_idx];
    }
}

// Update global BPM when source macro speed changes
static void update_bpm_from_source_macro_speed(uint8_t macro_num, float new_speed) {
    if (bpm_source_macro != macro_num || macro_num < 1 || macro_num > MAX_MACROS) {
        return;
    }
    
    uint8_t source_idx = macro_num - 1;
    uint32_t source_recording_bpm = macro_recording_bpm[source_idx];
    
    if (source_recording_bpm == 0) {
        return; // No recording BPM stored
    }
    
    // Calculate new global BPM: source_recording_bpm × new_speed
    uint32_t new_bpm = (uint32_t)((float)source_recording_bpm * new_speed);
    
    // Update global BPM
    current_bpm = new_bpm;
    
    dprintf("dynamic macro: BPM source macro %d speed %.1fx → global BPM %lu\n", 
            macro_num, new_speed, current_bpm / 100000);
}

// Navigate all currently playing macros based on the longest loop's timeline
// Navigate all currently playing macros based on the longest loop's timeline
static void navigate_all_macros_to_fraction(uint8_t numerator, uint8_t denominator) {
    dprintf("dynamic macro: navigating all macros to %d/%d based on longest loop\n", numerator, denominator);
    
    // First, execute any pending command batch
    if (command_batch_count > 0) {
        execute_command_batch();
        dprintf("dynamic macro: executed command batch before fractional navigation\n");
    }
    
    // Find the longest loop time among all playing macros
    uint32_t longest_loop_time = 0;
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_playback[i].is_playing && macro_playback[i].loop_length > longest_loop_time) {
            longest_loop_time = macro_playback[i].loop_length;
        }
        if (overdub_playback[i].is_playing && overdub_playback[i].loop_length > longest_loop_time) {
            longest_loop_time = overdub_playback[i].loop_length;
        }
    }
    
    if (longest_loop_time == 0) {
        dprintf("dynamic macro: no playing macros found for navigation\n");
        return;
    }
    
    // Calculate target time for main macros based on longest loop
    uint32_t main_target_time_ms = (longest_loop_time * numerator) / denominator;
    
    dprintf("dynamic macro: longest loop is %lu ms, main target time is %lu ms (%d/%d)\n", 
            longest_loop_time, main_target_time_ms, numerator, denominator);
    
    // Clean up all hanging notes before navigation
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_playback[i].is_playing) {
            cleanup_notes_from_macro(i + 1);
        }
        if (overdub_playback[i].is_playing) {
            cleanup_notes_from_macro(i + 1 + MAX_MACROS);
        }
    }
    
    uint32_t current_time = timer_read32();
    
    // Navigate main macros to the main target time (with wrapping)
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_playback[i].is_playing) {
            navigate_macro_to_absolute_time(&macro_playback[i], main_target_time_ms, current_time, i);
            dprintf("dynamic macro: navigated main macro %d to absolute time %lu ms\n", i + 1, main_target_time_ms);
        }
    }
    
    // Navigate overdubs - behavior depends on mode
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (overdub_playback[i].is_playing) {
            uint32_t overdub_target_time_ms;
            
            if (overdub_advanced_mode && overdub_independent_loop_length[i] > 0) {
                // ADVANCED MODE: Navigate to fraction of THIS overdub's independent loop length
                overdub_target_time_ms = (overdub_independent_loop_length[i] * numerator) / denominator;
                dprintf("dynamic macro: advanced mode - navigating overdub %d to %lu ms (fraction of its %lu ms loop)\n", 
                        i + 1, overdub_target_time_ms, overdub_independent_loop_length[i]);
            } else {
                // SYNCED MODE: Navigate to same time as main macros
                overdub_target_time_ms = main_target_time_ms;
                dprintf("dynamic macro: synced mode - navigating overdub %d to %lu ms (same as main)\n", 
                        i + 1, overdub_target_time_ms);
            }
            
            navigate_macro_to_absolute_time(&overdub_playback[i], overdub_target_time_ms, current_time, i);
        }
    }
    
    // Update pause timestamps if currently paused (so pause state stays consistent)
    if (global_playback_paused) {
        const uint32_t SNAP_TO_START_THRESHOLD = 100; // Same 100ms threshold
        
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing && macro_playback[i].loop_length > 0) {
                // Calculate wrapped position for this macro's loop
                uint32_t wrapped_position = main_target_time_ms % macro_playback[i].loop_length;
                
                // Apply snap-to-start logic for pause timestamps too
                if (wrapped_position <= SNAP_TO_START_THRESHOLD) {
                    wrapped_position = 0;
                    dprintf("dynamic macro: snapped pause position to start for macro %d\n", i + 1);
                }
                
                pause_timestamps[i] = wrapped_position;
                
                // Update overdub pause position - depends on mode
                if (overdub_playback[i].is_playing && overdub_playback[i].loop_length > 0) {
                    uint32_t overdub_target_for_pause;
                    
                    if (overdub_advanced_mode && overdub_independent_loop_length[i] > 0) {
                        // ADVANCED MODE: Use fraction of independent loop length
                        overdub_target_for_pause = (overdub_independent_loop_length[i] * numerator) / denominator;
                    } else {
                        // SYNCED MODE: Use same as main
                        overdub_target_for_pause = main_target_time_ms;
                    }
                    
                    uint32_t overdub_wrapped_position = overdub_target_for_pause % overdub_playback[i].loop_length;
                    
                    // Apply snap-to-start for overdub too
                    if (overdub_wrapped_position <= SNAP_TO_START_THRESHOLD) {
                        overdub_wrapped_position = 0;
                    }
                    
                    overdub_pause_timestamps[i] = overdub_wrapped_position;
                }
                
                dprintf("dynamic macro: updated pause position for macro %d to %lu ms (from target %lu ms)\n", 
                        i + 1, wrapped_position, main_target_time_ms);
            }
        }
    }
}
static void navigate_macro_to_absolute_time(macro_playback_state_t *state, uint32_t target_time_ms, uint32_t current_time, uint8_t macro_idx) {
    if (!state->is_playing || state->loop_length == 0) {
        return;
    }
    
    // Check if this is an independent overdub in advanced mode
    bool is_independent_overdub = false;
    if (overdub_advanced_mode) {
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (state->buffer_start == overdub_buffers[i]) {
                is_independent_overdub = true;
                break;
            }
        }
    }
    
    // Get the speed factor for this macro
    float speed_factor = macro_speed_factor[macro_idx];
    
    if (speed_factor <= 0.0f) {
        dprintf("dynamic macro: skipping absolute time navigation for macro %d (paused or invalid speed)\n", macro_idx + 1);
        return; // Can't navigate paused macros
    }
    
    // Wrap target time to this macro's loop length
    uint32_t wrapped_loop_position = target_time_ms % state->loop_length;
    bool snapped_to_start = false;
    
    // SNAP TO START: If within 100ms of loop start, snap to the beginning
    if (wrapped_loop_position <= LOOP_SNAP_TO_START_THRESHOLD) {
        wrapped_loop_position = 0;
        snapped_to_start = true;
        dprintf("dynamic macro: macro %d - snapped to start (was %lu ms, within %lu ms threshold)\n", 
                macro_idx + 1, wrapped_loop_position, LOOP_SNAP_TO_START_THRESHOLD);
    } else {
        dprintf("dynamic macro: macro %d - target %lu ms wraps to %lu ms (loop length %lu ms)\n", 
                macro_idx + 1, target_time_ms, wrapped_loop_position, state->loop_length);
    }
    
    // CATCHUP EVENTS: If we didn't snap to start, play recent events immediately
    // This ensures musical continuity by playing events that happened in the 100ms
    // window before our navigation target, so we don't miss chord hits or sustained notes
    if (!snapped_to_start) {
        uint32_t catchup_start_time = (wrapped_loop_position >= LOOP_SNAP_TO_START_THRESHOLD) ? 
                                     (wrapped_loop_position - LOOP_SNAP_TO_START_THRESHOLD) : 0;
        uint32_t catchup_end_time = wrapped_loop_position;
        
        dprintf("dynamic macro: macro %d - scanning for catchup events from %lu ms to %lu ms\n", 
                macro_idx + 1, catchup_start_time, catchup_end_time);
        
        // Scan for events in the catchup window and play them immediately
        for (midi_event_t *event = state->buffer_start; event < state->end; event++) {
            if (event->timestamp >= catchup_start_time && event->timestamp < catchup_end_time) {
                // Determine which transformations to use based on mode and overdub status
                uint8_t macro_num = macro_idx + 1;
                uint8_t transposed_note, override_channel, offset_velocity;
                
                if (is_independent_overdub) {
                    // Independent overdub: use overdub transformations
                    transposed_note = apply_transpose(event->note, overdub_transpose[macro_idx]);
                    override_channel = apply_channel_transformations(event->channel,
                                                      overdub_channel_offset[macro_idx],
                                                      overdub_channel_absolute[macro_idx]);
                    offset_velocity = apply_overdub_velocity_transformations(event->raw_travel,
                                                    overdub_velocity_offset[macro_idx],
                                                    overdub_velocity_absolute[macro_idx], macro_num);
                } else {
                    // Main macro or synced overdub: use macro transformations
                    transposed_note = apply_transpose(event->note, macro_transpose[macro_idx]);
                    override_channel = apply_channel_transformations(event->channel,
                                                      macro_channel_offset[macro_idx],
                                                      macro_channel_absolute[macro_idx]);
                    offset_velocity = apply_velocity_transformations(event->raw_travel,
                                                    macro_velocity_offset[macro_idx],
                                                    macro_velocity_absolute[macro_idx], macro_num);
                }
                
                // Determine track ID based on whether this is an overdub
                bool is_overdub = false;
                for (uint8_t i = 0; i < MAX_MACROS; i++) {
                    if (state->buffer_start == overdub_buffers[i]) {
                        is_overdub = true;
                        break;
                    }
                }
                
                uint8_t track_id = is_overdub ? (macro_num + MAX_MACROS) : macro_num;
                
                switch (event->type) {
                    case MIDI_EVENT_NOTE_ON:
                        // Check if the transposed note is currently being played live
                        if (!is_live_note_active(override_channel, transposed_note)) {
                            // Only send if not muted and not a live note
                            if (!macro_main_muted[macro_idx] || is_overdub) {
                                midi_send_noteon(&midi_device, override_channel, transposed_note, offset_velocity);
                                add_lighting_macro_note(override_channel, transposed_note, track_id);
                            }
                            
                            mark_note_from_macro(override_channel, transposed_note, track_id);
                            
                            // Handle octave doubler (use appropriate setting based on mode)
                            int8_t octave_doubler_value = (is_independent_overdub) ? 
                                                         overdub_octave_doubler[macro_idx] : 
                                                         macro_octave_doubler[macro_idx];
                            
                            if (octave_doubler_value != 0) {
                                uint8_t octave_note = apply_transpose(transposed_note, octave_doubler_value);
                                if (!is_live_note_active(override_channel, octave_note)) {
                                    if (!macro_main_muted[macro_idx] || is_overdub) {
                                        midi_send_noteon(&midi_device, override_channel, octave_note, offset_velocity);
                                        add_lighting_macro_note(override_channel, octave_note, track_id);
                                    }
                                }
                                mark_note_from_macro(override_channel, octave_note, track_id);
                            }
                            
                            dprintf("dynamic macro: catchup note-on ch:%d note:%d->%d vel:%d for macro %d\n", 
                                    event->channel, event->note, transposed_note, offset_velocity, macro_num);
                        }
                        break;
                        
                    case MIDI_EVENT_NOTE_OFF:
                        // For note-offs, we should send them regardless to ensure clean state
                        if (!is_live_note_active(override_channel, transposed_note)) {
                            if (!macro_main_muted[macro_idx] || is_overdub) {
                                midi_send_noteoff(&midi_device, override_channel, transposed_note, offset_velocity);
                                remove_lighting_macro_note(override_channel, transposed_note, track_id);
                            }
                            
                            unmark_note_from_macro(override_channel, transposed_note, track_id);
                            
                            // Handle octave doubler note-off
                            int8_t octave_doubler_value = (is_independent_overdub) ? 
                                                         overdub_octave_doubler[macro_idx] : 
                                                         macro_octave_doubler[macro_idx];
                            
                            if (octave_doubler_value != 0) {
                                uint8_t octave_note = apply_transpose(transposed_note, octave_doubler_value);
                                if (!is_live_note_active(override_channel, octave_note)) {
                                    if (!macro_main_muted[macro_idx] || is_overdub) {
                                        midi_send_noteoff(&midi_device, override_channel, octave_note, offset_velocity);
                                        remove_lighting_macro_note(override_channel, octave_note, track_id);
                                    }
                                }
                                unmark_note_from_macro(override_channel, octave_note, track_id);
                            }
                            
                            dprintf("dynamic macro: catchup note-off ch:%d note:%d->%d for macro %d\n", 
                                    event->channel, event->note, transposed_note, macro_num);
                        }
                        break;
                        
                    case MIDI_EVENT_CC:
                        // Send CC events immediately (they don't conflict with live notes)
                        if (!macro_main_muted[macro_idx] || is_overdub) {
                            midi_send_cc(&midi_device, override_channel, event->note, offset_velocity);
                        }
                        dprintf("dynamic macro: catchup CC ch:%d cc:%d val:%d for macro %d\n", 
                                override_channel, event->note, offset_velocity, macro_num);
                        break;
                }
            }
        }
    }
    
    // Calculate real-time equivalent of this loop position
    uint32_t target_real_time_position = (uint32_t)(wrapped_loop_position / speed_factor);
    
    // Find the appropriate event to start from at the wrapped position
    midi_event_t *target_event = find_event_at_position(state, wrapped_loop_position);
    
    if (target_event) {
        // Update playback state to new position
        state->current = target_event;
        state->timer = current_time - target_real_time_position;
        
        // CRITICAL: Also update independent timer for advanced mode overdubs
        if (is_independent_overdub) {
            overdub_independent_timer[macro_idx] = state->timer;
            dprintf("dynamic macro: updated independent timer for overdub %d\n", macro_idx + 1);
        }
        
        state->waiting_for_loop_gap = false;
        
        // Calculate next event time accounting for speed
        uint32_t time_to_event_in_loop = target_event->timestamp - wrapped_loop_position;
        uint32_t real_time_to_event = (uint32_t)(time_to_event_in_loop / speed_factor);
        state->next_event_time = current_time + real_time_to_event;
        
        dprintf("dynamic macro: positioned at %lu ms loop position, target event at %lu ms\n", 
                wrapped_loop_position, target_event->timestamp);
    } else {
        // No events at this position - we're in a gap, wait for next cycle
        state->waiting_for_loop_gap = true;
        state->timer = current_time - target_real_time_position;
        
        // CRITICAL: Also update independent timer for advanced mode overdubs
        if (is_independent_overdub) {
            overdub_independent_timer[macro_idx] = state->timer;
            dprintf("dynamic macro: updated independent timer for overdub %d (gap wait)\n", macro_idx + 1);
        }
        
        // Calculate real-world loop duration
        uint32_t real_loop_duration = (uint32_t)(state->loop_length / speed_factor);
        uint32_t real_time_to_loop_end = real_loop_duration - target_real_time_position;
        state->next_event_time = current_time + real_time_to_loop_end;
        
        dprintf("dynamic macro: positioned in gap at %lu ms loop position, waiting %lu ms for loop restart\n", 
                wrapped_loop_position, real_time_to_loop_end);
    }
}
bool process_dynamic_macro(uint16_t keycode, keyrecord_t *record) {
    // Handle special control keys first
    switch (keycode) {
		case 0xCC48: // Advanced overdub mode toggle (choose your preferred keycode)
    if (record->event.pressed) {
        overdub_advanced_mode = !overdub_advanced_mode;
        dprintf("dynamic macro: advanced overdub mode %s\n", 
                overdub_advanced_mode ? "ENABLED" : "DISABLED");
         
    }
    return true;
	
	// Add this case statement where your other custom keycodes are handled
// (around line 6560 near the BPM reset code)

case 0xcc56: // BPM doubler/halver - adjusts BPM display without changing speed
    if (record->event.pressed) {
        if (current_bpm > 0) {
            uint32_t old_bpm = current_bpm;
            
            // Determine whether to double or halve based on current value
            // If BPM >= 100, halve it (to avoid going over 200)
            // If BPM < 100, double it (to avoid going under 60)
            if (current_bpm >= 10000000) {  // >= 100 BPM
                current_bpm = current_bpm / 2;
                dprintf("dynamic macro: halved BPM from %lu.%05lu to %lu.%05lu\n", 
                        old_bpm / 100000, old_bpm % 100000,
                        current_bpm / 100000, current_bpm % 100000);
            } else {  // < 100 BPM
                current_bpm = current_bpm * 2;
                dprintf("dynamic macro: doubled BPM from %lu.%05lu to %lu.%05lu\n", 
                        old_bpm / 100000, old_bpm % 100000,
                        current_bpm / 100000, current_bpm % 100000);
            }
            
            // Update original_system_bpm to match the new value
            // This ensures the new BPM is treated as the "base" BPM
            if (original_system_bpm > 0) {
                if (old_bpm >= 10000000) {
                    original_system_bpm = original_system_bpm / 2;
                } else {
                    original_system_bpm = original_system_bpm * 2;
                }
            } else {
                // If original_system_bpm wasn't set, set it to the new current_bpm
                original_system_bpm = current_bpm;
            }
            
            // Update macro_recording_bpm for all macros that have content
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                if (macro_has_content[i] && macro_recording_bpm[i] > 0) {
                    if (old_bpm >= 10000000) {
                        macro_recording_bpm[i] = macro_recording_bpm[i] / 2;
                    } else {
                        macro_recording_bpm[i] = macro_recording_bpm[i] * 2;
                    }
                }
            }
            
            // Recalculate all macro speeds to maintain the same playback speed
            // This is crucial - the speed factors will be recalculated so that
            // the actual playback tempo remains unchanged
            recalculate_all_macro_speeds_for_bpm();
            
            // Update MIDI clock if it's running
            if (is_internal_clock_active()) {
                internal_clock_tempo_changed();
                dprintf("MIDI clock: Updated tempo for BPM adjustment\n");
            }
            
             
        } else {
            dprintf("dynamic macro: BPM doubler/halver - no BPM set yet\n");
        }
    }
    return true;
	
	case 0xCC49: // Complete independent overdub for macro 1
	case 0xCC4A: // Complete independent overdub for macro 2  
	case 0xCC4B: // Complete independent overdub for macro 3
	case 0xCC4C: // Complete independent overdub for macro 4
    if (record->event.pressed){
	overdub_button_held = true;
    }
		handle_macro_key((keycode - 0xCC49)+ 0xCC08, record);
    return true;
	
	
	case 0xCC4D: // Complete independent overdub for macro 1
	case 0xCC4E: // Complete independent overdub for macro 2  
	case 0xCC4F: // Complete independent overdub for macro 3
	case 0xCC50: // Complete independent overdub for macro 4
    if (record->event.pressed){
	mute_button_held = true;
	overdub_button_held = true;
    }
		handle_macro_key((keycode - 0xCC49)+ 0xCC08, record);
    return true;
		
		case 0xCC1D: // Octave doubler toggle for macro 1
        case 0xCC1E: // Octave doubler toggle for macro 2  
        case 0xCC1F: // Octave doubler toggle for macro 3
        case 0xCC20: // Octave doubler toggle for macro 4
            if (record->event.pressed) {
                uint8_t macro_num = keycode - 0xCC1D + 1; // Calculate macro number (1-4)
                
                // Cycle through octave doubler modes for this macro: 0 -> 12 -> 24 -> -12 -> 0
                int8_t current_mode = get_macro_octave_doubler_target(macro_num);
                int8_t next_mode;
                if (current_mode == 0) next_mode = 12;
                else if (current_mode == 12) next_mode = 24;
                else if (current_mode == 24) next_mode = -12;
                else next_mode = 0;
                
                set_macro_octave_doubler_target(macro_num, next_mode);
                
                dprintf("dynamic macro: cycled octave doubler for macro %d\n", macro_num);
                 
            }
            return true;
			
		case 0xCC21: // Octave doubler modifier button
            if (record->event.pressed) {
                octave_doubler_button_held = true;
                dprintf("dynamic macro: octave doubler modifier button PRESSED\n");
            } else {
                octave_doubler_button_held = false;
                dprintf("dynamic macro: octave doubler modifier button RELEASED\n");
            }
            return true;
		
        case 0xCC10: // Mute button
            if (record->event.pressed) {
                mute_button_held = true;
                dprintf("dynamic macro: mute button PRESSED\n");
            } else {
                mute_button_held = false;
                dprintf("dynamic macro: mute button RELEASED\n");
            }
            return true;
            
        case 0xCC15: // Overdub button
            if (record->event.pressed) {
                overdub_button_held = true;
                dprintf("dynamic macro: overdub button PRESSED\n");
            } else {
                overdub_button_held = false;
                dprintf("dynamic macro: overdub button RELEASED\n");
            }
            return true;
            
        case 0xCC17: // Sample mode toggle
            if (record->event.pressed) {
                sample_mode_active = !sample_mode_active;
                dprintf("dynamic macro: sample mode %s\n", sample_mode_active ? "ENABLED" : "DISABLED");
                 
                
                // If enabling sample mode and multiple macros are playing, stop all except the first one
                if (sample_mode_active) {
                    bool found_first = false;
                    for (uint8_t i = 0; i < MAX_MACROS; i++) {
                        if (macro_playback[i].is_playing) {
                            if (!found_first) {
                                found_first = true;  // Keep the first one playing
                            } else {
                                // Stop additional macros
                                dynamic_macro_cleanup_notes_for_state(&macro_playback[i]);
                                macro_playback[i].is_playing = false;
                                macro_playback[i].current = NULL;
                                
                                // Also stop overdubs
                                if (overdub_playback[i].is_playing) {
                                    dynamic_macro_cleanup_notes_for_state(&overdub_playback[i]);
                                    overdub_playback[i].is_playing = false;
                                    overdub_playback[i].current = NULL;
                                }
                                
                                dprintf("dynamic macro: stopped macro %d due to sample mode activation\n", i + 1);
                            }
                        }
                    }
                    
                    // Also cancel any play commands in the batch
                    for (uint8_t i = 0; i < command_batch_count; i++) {
                        if (command_batch[i].command_type == CMD_PLAY && !command_batch[i].processed) {
                            command_batch[i].processed = true;
                            dprintf("dynamic macro: removed queued play command for macro %d due to sample mode\n", 
                                    command_batch[i].macro_id);
                        }
                    }
                }
            }
            return true;	
		
		case 0xCC1C: // Global edit modifier button
		if (record->event.pressed) {
			global_edit_modifier_held = true;
			dprintf("dynamic macro: global edit modifier PRESSED\n");
		} else {
			global_edit_modifier_held = false;
			dprintf("dynamic macro: global edit modifier RELEASED\n");
		}
		return true;
            
        case 0xCC0C:
        case 0xCC0D:
        case 0xCC0E:
        case 0xCC0F: // Dedicated mute keys
            if (record->event.pressed) {
                uint8_t macro_idx = keycode - 0xCC0C;
                
                // Toggle mute state with quantization
                if (overdub_muted[macro_idx]) {
                    // Currently muted - schedule unmute at loop trigger
                    overdub_unmute_pending[macro_idx] = true;
                    dprintf("dynamic macro: scheduled to unmute overdub for macro %d at loop trigger\n", macro_idx + 1);
                } else {
                    // Currently unmuted - schedule mute at loop trigger
                    overdub_mute_pending[macro_idx] = true;
                    dprintf("dynamic macro: scheduled to mute overdub for macro %d at loop trigger\n", macro_idx + 1);
                }
                
                 
            }
            return true;
			
		case 0xCC22: // Copy button
			if (record->event.pressed) {
				if (copy_modifier_active || paste_modifier_active) {
					// Cancel operation
					copy_modifier_active = false;
					paste_modifier_active = false;
					source_macro_id = 0;
					hid_rx_buffer_pos = 0;  // ADD THIS LINE
					dprintf("dynamic macro: copy operation cancelled\n");
				} else {
					// Start copy operation
					copy_modifier_active = true;
					hid_rx_buffer_pos = 0;  // ADD THIS LINE
					dprintf("dynamic macro: Select Loop to Copy\n");
				}
				 
			}
			return true;
			
		case 0xCC23: // Save macro 1
        case 0xCC24: // Save macro 2  
        case 0xCC25: // Save macro 3
        case 0xCC26: // Save macro 4
            if (record->event.pressed) {
                uint8_t save_macro_num = keycode - 0xCC23 + 1;  // DECLARE THE VARIABLE HERE
                
                midi_event_t *check_start = get_macro_buffer(save_macro_num);
                midi_event_t **check_end = get_macro_end_ptr(save_macro_num);
                
                if (check_start != *check_end) {
                    send_macro_via_hid(save_macro_num);  // NEW HID FUNCTION
                    dprintf("dynamic macro: initiated save for macro %d\n", save_macro_num);
                } else {
                    dprintf("dynamic macro: macro %d is empty - nothing to save\n", save_macro_num);
                }
                 
            }
            return true;
		case 0xCC27: // Save All Loops button (choose whatever keycode you want)
			if (record->event.pressed) {
				// Send signal to web app to trigger save all modal
				uint8_t packet[HID_PACKET_SIZE] = {0};
				
				packet[0] = HID_MANUFACTURER_ID;
				packet[1] = HID_SUB_ID; 
				packet[2] = HID_DEVICE_ID;
				packet[3] = HID_CMD_TRIGGER_SAVE_ALL;
				packet[4] = 0; // No specific macro
				packet[5] = 0; // No status
				
				raw_hid_send(packet, HID_PACKET_SIZE);
				
				dprintf("dynamic macro: sent save all trigger to web app\n");
				 
			}
			return true;
			
        case 0xCC28: // Speed modifier button (hold + macro to change speed)
            if (record->event.pressed) {
                speed_modifier_held = true;
                dprintf("dynamic macro: speed modifier PRESSED\n");
            } else {
                speed_modifier_held = false;
                dprintf("dynamic macro: speed modifier RELEASED\n");
            }
            return true;

        case 0xCC29: // slow modifier button (hold + macro to change speed)
            if (record->event.pressed) {
                slow_modifier_held = true;
                dprintf("dynamic macro: speed modifier PRESSED\n");
            } else {
                slow_modifier_held = false;
                dprintf("dynamic macro: speed modifier RELEASED\n");
            }
            return true;			
			
		case 0xCC2A: // Individual speed toggle for macro 1
            if (record->event.pressed) {
                cycle_macro_speed(1);
            }
            return true;
            
        case 0xCC2B: // Individual speed toggle for macro 2
            if (record->event.pressed) {
                cycle_macro_speed(2);
            }
            return true;
            
        case 0xCC2C: // Individual speed toggle for macro 3
            if (record->event.pressed) {
                cycle_macro_speed(3);
            }
            return true;
            
        case 0xCC2D: // Individual speed toggle for macro 4
            if (record->event.pressed) {
                cycle_macro_speed(4);
            }
            return true;
			
		case 0xCC2E: // Individual speed toggle for macro 1
            if (record->event.pressed) {
                cycle_macro_slow(1);
            }
            return true;
            
        case 0xCC2F: // Individual speed toggle for macro 2
            if (record->event.pressed) {
                cycle_macro_slow(2);
            }
            return true;
            
        case 0xCC30: // Individual speed toggle for macro 3
            if (record->event.pressed) {
                cycle_macro_slow(3);
            }
            return true;
            
        case 0xCC31: // Individual speed toggle for macro 4
            if (record->event.pressed) {
                cycle_macro_slow(4);
            }
            return true;
			
		case 0xCC53: // Cycle ALL macros to faster speeds
            if (record->event.pressed) {
                cycle_all_macros_speed();
            }
            return true;
        
        case 0xCC54: // Cycle ALL macros to slower speeds
            if (record->event.pressed) {
                cycle_all_macros_slow();
            }
            return true;	
		
		case 0xCC3A: // Navigate backward 1 second
            if (record->event.pressed) {
                navigate_all_macros(-1000); // -1000ms = -1 second
                 
            }
            return true;
            
        case 0xCC3B: // Navigate forward 1 second  
            if (record->event.pressed) {
                navigate_all_macros(1000); // +1000ms = +1 second
                 
            }
            return true;
			
		case 0xCC3C: // Navigate backward 1 second
            if (record->event.pressed) {
                navigate_all_macros(-5000); // -1000ms = -1 second
                 
            }
            return true;
            
        case 0xCC3D: // Navigate forward 1 second  
            if (record->event.pressed) {
                navigate_all_macros(5000); // +1000ms = +1 second
                 
            }
            return true;
        
		case 0xCC3E: // Global play/pause toggle button
			if (record->event.pressed) {
				if (!global_playback_paused) {
					// ===================================================================
					// PAUSE: Store current loop positions for all playing macros
					// ===================================================================
					uint32_t current_time = timer_read32();
					
					for (uint8_t i = 0; i < MAX_MACROS; i++) {
						// PAUSE MAIN MACROS
						if (macro_playback[i].is_playing) {
							// Calculate current speed-adjusted position in loop
							float speed_factor = macro_speed_factor[i];
							uint32_t real_elapsed = current_time - macro_playback[i].timer;
							
							if (speed_factor > 0.0f) {
								uint32_t speed_adjusted_elapsed = (uint32_t)(real_elapsed * speed_factor);
								pause_timestamps[i] = speed_adjusted_elapsed % macro_playback[i].loop_length;
							} else {
								pause_timestamps[i] = real_elapsed % macro_playback[i].loop_length;
							}
							
							dprintf("dynamic macro: paused main macro %d at loop position %lu ms\n", 
									i + 1, pause_timestamps[i]);
						}
						
						// PAUSE OVERDUBS (with advanced mode support)
						if (overdub_playback[i].is_playing) {
							float speed_factor = macro_speed_factor[i];
							uint32_t real_elapsed;
							
							// CRITICAL: Use appropriate timer based on mode
							if (overdub_advanced_mode && overdub_independent_loop_length[i] > 0) {
								// ADVANCED MODE: Use independent timer
								real_elapsed = current_time - overdub_independent_timer[i];
								dprintf("dynamic macro: using independent timer for pause (overdub %d)\n", i + 1);
							} else {
								// SYNCED MODE: Use regular timer
								real_elapsed = current_time - overdub_playback[i].timer;
							}
							
							if (speed_factor > 0.0f) {
								uint32_t speed_adjusted_elapsed = (uint32_t)(real_elapsed * speed_factor);
								overdub_pause_timestamps[i] = speed_adjusted_elapsed % overdub_playback[i].loop_length;
							} else {
								overdub_pause_timestamps[i] = real_elapsed % overdub_playback[i].loop_length;
							}
							
							dprintf("dynamic macro: paused overdub %d at loop position %lu ms (%s mode)\n", 
									i + 1, overdub_pause_timestamps[i],
									(overdub_advanced_mode && overdub_independent_loop_length[i] > 0) ? "independent" : "synced");
						}
					}
					
					global_playback_paused = true;
					dprintf("dynamic macro: paused all macro playback\n");
					
				} else {
					// ===================================================================
					// PLAY: Restore all macros from stored positions
					// ===================================================================
					uint32_t current_time = timer_read32();
					
					for (uint8_t i = 0; i < MAX_MACROS; i++) {
						// RESUME MAIN MACROS
						if (macro_playback[i].is_playing) {
							float speed_factor = macro_speed_factor[i];
							uint32_t loop_position = pause_timestamps[i];
							
							// Find the event at or after this position
							midi_event_t *target_event = find_event_at_position(&macro_playback[i], loop_position);
							
							if (target_event) {
								macro_playback[i].current = target_event;
								macro_playback[i].waiting_for_loop_gap = false;
								
								// Calculate real time offset for this loop position
								uint32_t real_time_offset;
								if (speed_factor > 0.0f) {
									real_time_offset = (uint32_t)(loop_position / speed_factor);
								} else {
									real_time_offset = loop_position;
								}
								
								macro_playback[i].timer = current_time - real_time_offset;
								
								// Calculate next event time
								uint32_t time_to_event = target_event->timestamp - loop_position;
								uint32_t adjusted_time_to_event = (speed_factor > 0.0f) ? 
																 (uint32_t)(time_to_event / speed_factor) : time_to_event;
								macro_playback[i].next_event_time = current_time + adjusted_time_to_event;
							} else {
								// In gap, wait for next loop
								macro_playback[i].waiting_for_loop_gap = true;
								macro_playback[i].current = macro_playback[i].buffer_start;
								
								uint32_t real_time_offset;
								if (speed_factor > 0.0f) {
									real_time_offset = (uint32_t)(loop_position / speed_factor);
								} else {
									real_time_offset = loop_position;
								}
								macro_playback[i].timer = current_time - real_time_offset;
								
								uint32_t time_to_loop_end = macro_playback[i].loop_length - loop_position;
								uint32_t adjusted_time_to_end = (speed_factor > 0.0f) ? 
															   (uint32_t)(time_to_loop_end / speed_factor) : time_to_loop_end;
								macro_playback[i].next_event_time = current_time + adjusted_time_to_end;
							}
							
							dprintf("dynamic macro: resumed main macro %d from loop position %lu ms\n", 
									i + 1, loop_position);
						}
						
						// RESUME OVERDUBS (with advanced mode support)
						if (overdub_playback[i].is_playing) {
							float speed_factor = macro_speed_factor[i];
							uint32_t loop_position = overdub_pause_timestamps[i];
							bool is_independent = (overdub_advanced_mode && overdub_independent_loop_length[i] > 0);
							
							// Find the event at or after this position in overdub
							midi_event_t *target_event = NULL;
							for (midi_event_t *event = overdub_playback[i].buffer_start; 
								 event < overdub_playback[i].end; event++) {
								if (event->timestamp >= loop_position) {
									target_event = event;
									break;
								}
							}
							
							if (target_event) {
								overdub_playback[i].current = target_event;
								overdub_playback[i].waiting_for_loop_gap = false;
								
								uint32_t real_time_offset;
								if (speed_factor > 0.0f) {
									real_time_offset = (uint32_t)(loop_position / speed_factor);
								} else {
									real_time_offset = loop_position;
								}
								
								// Update BOTH timers for independent overdubs
								overdub_playback[i].timer = current_time - real_time_offset;
								
								// CRITICAL: Also update independent timer if in advanced mode
								if (is_independent) {
									overdub_independent_timer[i] = current_time - real_time_offset;
									dprintf("dynamic macro: updated independent timer for overdub %d on resume\n", i + 1);
								}
								
								uint32_t time_to_event = target_event->timestamp - loop_position;
								uint32_t adjusted_time_to_event = (speed_factor > 0.0f) ? 
																 (uint32_t)(time_to_event / speed_factor) : time_to_event;
								overdub_playback[i].next_event_time = current_time + adjusted_time_to_event;
							} else {
								// In gap, wait for next loop
								overdub_playback[i].waiting_for_loop_gap = true;
								overdub_playback[i].current = overdub_playback[i].buffer_start;
								
								uint32_t real_time_offset;
								if (speed_factor > 0.0f) {
									real_time_offset = (uint32_t)(loop_position / speed_factor);
								} else {
									real_time_offset = loop_position;
								}
								
								// Update BOTH timers for independent overdubs
								overdub_playback[i].timer = current_time - real_time_offset;
								
								// CRITICAL: Also update independent timer if in advanced mode
								if (is_independent) {
									overdub_independent_timer[i] = current_time - real_time_offset;
									dprintf("dynamic macro: updated independent timer for overdub %d on resume (gap)\n", i + 1);
								}
								
								uint32_t time_to_loop_end = overdub_playback[i].loop_length - loop_position;
								uint32_t adjusted_time_to_end = (speed_factor > 0.0f) ? 
															   (uint32_t)(time_to_loop_end / speed_factor) : time_to_loop_end;
								overdub_playback[i].next_event_time = current_time + adjusted_time_to_end;
							}
							
							dprintf("dynamic macro: resumed overdub %d from loop position %lu ms (%s mode)\n", 
									i + 1, loop_position, is_independent ? "independent" : "synced");
						}
					}
					
					global_playback_paused = false;
					dprintf("dynamic macro: resumed all macro playback\n");
				}
				 
			}
			return true;
			
		case 0xCC3F: // Reset all speeds and BPM to original
		if (record->event.pressed) {
			// Reset all manual speeds to 1.0x
			for (uint8_t i = 0; i < MAX_MACROS; i++) {
				macro_manual_speed[i] = 1.0f;
			}
			
			// Reset BPM to original
			if (original_system_bpm > 0) {
				current_bpm = original_system_bpm;
				dprintf("dynamic macro: reset BPM to original %lu\n", current_bpm / 100000);
			}
			
			// Recalculate all macro speeds (should all be 1.0x now)
			recalculate_all_macro_speeds_for_bpm();
			
			dprintf("dynamic macro: reset all speeds to 1.0x and BPM to original\n");
			 
		}
		return true;
		
		case 0xCC40: // Skip to 0/8 (start)
		case 0xCC41: // Skip to 1/8 
		case 0xCC42: // Skip to 2/8
		case 0xCC43: // Skip to 3/8
		case 0xCC44: // Skip to 4/8 (middle)
		case 0xCC45: // Skip to 5/8
		case 0xCC46: // Skip to 6/8
		case 0xCC47: // Skip to 7/8
			if (record->event.pressed) {
				uint8_t fraction_numerator = keycode - 0xCC40; // 0-7
				navigate_all_macros_to_fraction(fraction_numerator, 8);
			if (!loop_navigate_use_master_cc) {
				switch(fraction_numerator) {
					case 0: send_loop_message(loop_navigate_0_8_cc, 127); break;
					case 1: send_loop_message(loop_navigate_1_8_cc, 127); break;
					case 2: send_loop_message(loop_navigate_2_8_cc, 127); break;
					case 3: send_loop_message(loop_navigate_3_8_cc, 127); break;
					case 4: send_loop_message(loop_navigate_4_8_cc, 127); break;
					case 5: send_loop_message(loop_navigate_5_8_cc, 127); break;
					case 6: send_loop_message(loop_navigate_6_8_cc, 127); break;
					case 7: send_loop_message(loop_navigate_7_8_cc, 127); break;
				}
			} else {
				// Option 2: Master CC with increments of 16
				uint8_t nav_values[8] = {0, 16, 32, 48, 64, 80, 96, 112};
				send_loop_message(loop_navigate_master_cc, nav_values[fraction_numerator]);
			}
				 
			}
			return true;

				  
        case 0xCC08:
        case 0xCC09:
        case 0xCC0A:
        case 0xCC0B: // Macro keys
            handle_macro_key(keycode, record);
			return true;
            
        case QK_DYNAMIC_MACRO_RECORD_STOP:
        case QK_DYNAMIC_MACRO_PLAY_1:
        case QK_DYNAMIC_MACRO_PLAY_2:
            // Ignore these keys - functionality handled by macro keys above
            return false;
            
        default:
            // Handle other keys during recording
            if (macro_id > 0 || is_macro_primed) {
                if (dynamic_macro_valid_key_user(keycode, record)) {
                    return true; // Let key be processed normally
                }
            }
            return true;
    }
}

// Helper function to end overdub recording in a mode-aware way
static void end_overdub_recording_mode_aware(uint8_t macro_num, bool force_immediate, bool auto_mute) {
    if (!overdub_advanced_mode) {
        // ORIGINAL MODE: Use original behavior
        if (auto_mute) {
            uint8_t macro_idx = macro_num - 1;
            overdub_unmute_pending[macro_idx] = true;
        }
        end_overdub_recording_deferred(macro_num);
        
        // Do immediate cleanup for original mode
        uint8_t macro_idx = macro_num - 1;
        macro_in_overdub_mode[macro_idx] = false;
        overdub_target_macro = 0;
        macro_id = 0;
        current_macro_id = 0;
        stop_dynamic_macro_recording();
        return;
    }
    
    // ADVANCED MODE: Check if we need to batch or execute immediately
    if (force_immediate) {
        // Force immediate execution (for unsynced/sample modes)
        end_overdub_recording_deferred_advanced(macro_num);
        return;
    }
    
    // Check if other macros are playing
    uint8_t playing_count = 0;
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
            playing_count++;
        }
    }
    
    if (playing_count > 0) {
        // Add command for quantized execution - DON'T do immediate cleanup
        add_command_to_batch(CMD_ADVANCED_OVERDUB_END, macro_num);
        dprintf("dynamic macro: queued ADVANCED overdub end for macro %d\n", macro_num);
    } else {
        // No other macros playing - execute immediately
        end_overdub_recording_deferred_advanced(macro_num);
    }
}

// Main macro key handler
static bool handle_macro_key(uint16_t keycode, keyrecord_t *record) {
    // Initialize macro system if needed
    initialize_macros();
    
    uint8_t macro_num = keycode - 0xCC08 + 1;
    uint8_t macro_idx = macro_num - 1;
    
    if (record->event.pressed) {
        if (global_edit_modifier_held) {
            // DON'T process here - let other file handle it
            return true;  // Continue processing (let other handlers see it)
        }
        // Normal processing when global modifier NOT held
        handle_macro_key_press(macro_num, macro_idx);
        return false;  // We handled it, stop processing
    } else {
        // Key released
        macro_key_held[macro_idx] = false;
        return true;  // We handled the release, stop processing
    }
}

// Handle advanced overdub mode - complete independence between macros and overdubs
static bool handle_overdub_advanced_mode(uint8_t macro_num, uint8_t macro_idx,
                                        midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                                        bool this_macro_playing, bool this_macro_empty) {
    
    // Count playing items to determine if we need batching
    uint8_t playing_count = 0;
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
            playing_count++;
        }
    }
    
    bool use_batching = (unsynced_mode_active != 2 && unsynced_mode_active != 5) && !sample_mode_active && playing_count > 0;
    
    // Determine if this is an overdub operation or main macro operation
    bool is_overdub_operation = overdub_button_held || mute_button_held;
    
    if (is_overdub_operation) {
        // ============================================================================
        // OVERDUB-ONLY OPERATIONS (overdub + macro OR mute + macro)
        // ============================================================================
        
        bool overdub_has_content = (overdub_buffers[macro_idx] != NULL && 
                                   overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx]);
        bool overdub_is_playing = overdub_playback[macro_idx].is_playing;
        bool overdub_is_recording = (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num);
        
		// Case 1: Currently recording overdub - stop recording
		if (overdub_is_recording) {
			// Use the SAME logic as the working macro-only case
			if (use_batching) {
				// Suspend recording and batch the stop (matches working behavior)
				recording_suspended[macro_idx] = true;
				add_command_to_batch(CMD_STOP, macro_num);
				
				// Add play command if not skipped by double-tap
				midi_event_t *macro_start = get_macro_buffer(macro_num);
				midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
				bool is_macro_empty = (macro_start == *macro_end_ptr);
				
				if (!is_macro_empty && !skip_autoplay_for_macro[macro_idx]) {
					add_command_to_batch(CMD_PLAY, macro_num);
				}
				
				dprintf("dynamic macro: [ADVANCED] batched stop overdub recording for macro %d\n", macro_num);
			} else {
				// Immediate execution - same as working case
				end_overdub_recording_deferred_advanced(macro_num);
				dprintf("dynamic macro: [ADVANCED] immediately stopped overdub recording for macro %d\n", macro_num);
			}
			 
			return false;
		}
        
        // Case 2: Overdub is playing - stop it (independent from main macro)
        if (overdub_is_playing) {
            if (use_batching) {
                // Set pending mute for loop trigger processing
                overdub_mute_pending[macro_idx] = true;
                dprintf("dynamic macro: [ADVANCED] batched stop overdub playback for macro %d\n", macro_num);
            } else {
                // Stop overdub immediately
                dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
                overdub_playback[macro_idx].is_playing = false;
                overdub_playback[macro_idx].current = NULL;
                overdub_muted[macro_idx] = true;				
                send_loop_message(overdub_stop_playing_cc[macro_num - 1], 127);
                dprintf("dynamic macro: [ADVANCED] immediately stopped overdub playback for macro %d\n", macro_num);
            }
             
            return false;
        }
        
        // Case 3: Overdub has content but not playing - play it independently
        if (overdub_has_content && !overdub_is_playing) {
            if (use_batching) {
                // Set pending unmute for loop trigger processing
                overdub_unmute_pending[macro_idx] = true;
                dprintf("dynamic macro: [ADVANCED] batched independent overdub playback for macro %d\n", macro_num);
            } else {
                // Start overdub playback immediately (independent)
                overdub_muted[macro_idx] = false;
                
                macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
                overdub_state->current = overdub_buffers[macro_idx];
                overdub_state->end = overdub_buffer_ends[macro_idx];
                overdub_state->direction = +1;
                overdub_state->buffer_start = overdub_buffers[macro_idx];
                overdub_state->is_playing = true;
                overdub_state->waiting_for_loop_gap = false;
                overdub_state->next_event_time = 0;
                
                // Use independent timer and loop length for advanced mode
                overdub_independent_timer[macro_idx] = timer_read32();
                overdub_state->timer = overdub_independent_timer[macro_idx];
                overdub_state->loop_length = overdub_independent_loop_length[macro_idx];
                overdub_state->loop_gap_time = overdub_independent_gap_time[macro_idx];
                
                reset_bpm_timing_for_loop_start();
                send_loop_message(overdub_start_playing_cc[macro_num - 1], 127);
                dprintf("dynamic macro: [ADVANCED] immediately started independent overdub playback for macro %d\n", macro_num);
            }
             
            return false;
        }
        
        // Case 4: Overdub is empty - start recording
        if (!overdub_has_content && !overdub_is_recording) {
            if (use_batching) {
                add_command_to_batch(CMD_ADVANCED_OVERDUB_REC, macro_num);
				
                dprintf("dynamic macro: [ADVANCED] batched start overdub recording for macro %d\n", macro_num);
            } else {
                start_overdub_recording_advanced(macro_num);
                dprintf("dynamic macro: [ADVANCED] immediately started overdub recording for macro %d\n", macro_num);
            }
             
            return false;
        }
        
    } else {
        // ============================================================================
        // MAIN MACRO OPERATIONS (just macro press)
        // ============================================================================
        
        // Case 1: Currently recording this macro - stop recording
        if (macro_id == macro_num) {
            if (use_batching) {
                // Suspend recording and batch the stop
                recording_suspended[macro_idx] = true;
                add_command_to_batch(CMD_STOP, macro_num);
                
                // Add play command if not skipped by double-tap
                if (!is_macro_empty && !skip_autoplay_for_macro[macro_idx]) {
                    add_command_to_batch(CMD_PLAY, macro_num);
                }
                
                dprintf("dynamic macro: [ADVANCED] batched stop recording for macro %d\n", macro_num);
            } else {
                // Stop recording immediately
                dynamic_macro_record_end(macro_start, macro_pointer, +1, macro_end_ptr, &recording_start_time);
                macro_id = 0;
                stop_dynamic_macro_recording();
                
                // Start playback if not skipped
                if (!is_macro_empty && !skip_autoplay_for_macro[macro_idx]) {
                    process_pending_states_for_macro(macro_idx);
                    dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                    dprintf("dynamic macro: [ADVANCED] immediately stopped recording and started playback for macro %d\n", macro_num);
                } else {
                    dprintf("dynamic macro: [ADVANCED] immediately stopped recording for macro %d (no autoplay)\n", macro_num);
                }
            }
             
            return false;
        }
        
        // Case 2: Currently recording another macro - batch a stop for this and record for the new one
        if (macro_id > 0 && macro_id != macro_num) {
            if (this_macro_empty) {
                // New macro is empty - record handoff
                if (use_batching) {
                    add_command_to_batch(CMD_STOP, macro_id);
                    if (!is_macro_empty) {
                        add_command_to_batch(CMD_PLAY, macro_id);
                    }
                    add_command_to_batch(CMD_RECORD, macro_num);
                    dprintf("dynamic macro: [ADVANCED] batched record handoff from macro %d to %d\n", macro_id, macro_num);
                } else {
                    // Immediate handoff
                    midi_event_t *rec_start = get_macro_buffer(macro_id);
                    midi_event_t **rec_end_ptr = get_macro_end_ptr(macro_id);
                    
                    dynamic_macro_record_end(rec_start, macro_pointer, +1, rec_end_ptr, &recording_start_time);
                    
                    // Start new recording
                    macro_id = macro_num;
                    macro_pointer = macro_start;
                    recording_start_time = timer_read32();
                    first_note_recorded = true;
					send_loop_message(loop_start_recording_cc[macro_id - 1], 127);  // ADD THIS LINE
                    setup_dynamic_macro_recording(macro_id, macro_buffer, NULL, (void**)&macro_pointer, &recording_start_time);
                    
                    dprintf("dynamic macro: [ADVANCED] immediate record handoff from previous to macro %d\n", macro_num);
                }
            } else {
                // New macro has content - just affect this macro
                if (use_batching) {
                    if (this_macro_playing) {
                        add_command_to_batch(CMD_STOP, macro_num);
                    } else {
                        add_command_to_batch(CMD_PLAY, macro_num);
                    }
                    dprintf("dynamic macro: [ADVANCED] batched %s for macro %d (while recording other)\n", 
                            this_macro_playing ? "stop" : "play", macro_num);
                } else {
                    if (this_macro_playing) {
                        dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
                        macro_playback[macro_idx].is_playing = false;
                        macro_playback[macro_idx].current = NULL;
                        dprintf("dynamic macro: [ADVANCED] immediately stopped macro %d\n", macro_num);
                    } else {
                        process_pending_states_for_macro(macro_idx);
                        dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                        dprintf("dynamic macro: [ADVANCED] immediately started macro %d\n", macro_num);
                    }
                }
            }
             
            return false;
        }
        
        // Case 3: Macro is playing - stop it (independent from overdub)
        if (this_macro_playing) {
            if (use_batching) {
                add_command_to_batch(CMD_STOP, macro_num);
                dprintf("dynamic macro: [ADVANCED] batched stop for playing macro %d\n", macro_num);
            } else {
                dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
                macro_playback[macro_idx].is_playing = false;
                macro_playback[macro_idx].current = NULL;
                send_loop_message(loop_stop_playing_cc[macro_num - 1], 127);
                dprintf("dynamic macro: [ADVANCED] immediately stopped macro %d\n", macro_num);
            }
             
            return false;
        }
        
        // Case 4: Macro has content but not playing - play it (independent from overdub)
        if (!this_macro_empty && !this_macro_playing) {
            if (use_batching) {
                add_command_to_batch(CMD_PLAY, macro_num);
                dprintf("dynamic macro: [ADVANCED] batched play for stopped macro %d\n", macro_num);
            } else {
                process_pending_states_for_macro(macro_idx);
                dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                dprintf("dynamic macro: [ADVANCED] immediately started macro %d\n", macro_num);
            }
             
            return false;
        }
        
        // Case 5: Macro is empty - start recording
        if (this_macro_empty && macro_id == 0) {
            if (use_batching) {
                add_command_to_batch(CMD_RECORD, macro_num);
                dprintf("dynamic macro: [ADVANCED] batched record for empty macro %d\n", macro_num);
            } else {
                dynamic_macro_record_start(&macro_pointer, macro_start, +1, &recording_start_time);
                macro_id = macro_num;
                snapshot_recording_settings(macro_num);  // Snapshot curve/min/max when recording starts
                setup_dynamic_macro_recording(macro_id, macro_buffer, NULL, (void**)&macro_pointer, &recording_start_time);
                dprintf("dynamic macro: [ADVANCED] immediately started recording macro %d\n", macro_num);
            }
             
            return false;
        }
    }
    
    // If we get here, some case wasn't handled
    dprintf("dynamic macro: [ADVANCED] unhandled case for macro %d\n", macro_num);
    return false;
}
// Handle macro key press with all original logic
static bool handle_macro_key_press(uint8_t macro_num, uint8_t macro_idx) {
    
    // Continue with normal processing
    key_timers[macro_idx] = timer_read();
    macro_key_held[macro_idx] = true;
    macro_deleted[macro_idx] = false;  // Reset delete state
    
    // Handle copy modifier
    if (copy_modifier_active) {
        // Check if currently recording/overdubbing
        if (macro_id > 0) {
            copy_modifier_active = false;
            dprintf("dynamic macro: Cannot Copy While Recording\n");
             
            return false;
        }
        
        // Check if source macro is empty
        midi_event_t *check_macro_start = get_macro_buffer(macro_num);
        midi_event_t **check_macro_end_ptr = get_macro_end_ptr(macro_num);
        if (check_macro_start == *check_macro_end_ptr) {
            copy_modifier_active = false;
            dprintf("dynamic macro: No Macro Found\n");
             
            return false;
        }
        
        // Serialize the source macro data to HID buffer
        hid_rx_buffer_pos = serialize_macro_data(macro_num, hid_rx_buffer);
        if (hid_rx_buffer_pos > 0) {
            copy_modifier_active = false;
            paste_modifier_active = true;
            source_macro_id = macro_num; // Store for display purposes
            dprintf("dynamic macro: serialized %d bytes from macro %d, Select Loop to Overwrite\n", 
                    hid_rx_buffer_pos, macro_num);
             
        } else {
            copy_modifier_active = false;
            dprintf("dynamic macro: Failed to serialize macro %d\n", macro_num);
             
        }
        return false;
    }

    // Handle paste modifier
    if (paste_modifier_active) {
        // Check if we have valid copy data
        if (hid_rx_buffer_pos == 0) {
            paste_modifier_active = false;
            source_macro_id = 0;
            dprintf("dynamic macro: No valid copy data\n");
             
            return false;
        }
        
        // Deserialize the HID buffer to the target macro
        if (deserialize_macro_data(hid_rx_buffer, hid_rx_buffer_pos, macro_num)) {
            paste_modifier_active = false;
            source_macro_id = 0;
            hid_rx_buffer_pos = 0; // Clear the buffer
             
        } else {
            paste_modifier_active = false;
            source_macro_id = 0;
            hid_rx_buffer_pos = 0;
            dprintf("dynamic macro: Failed to paste to macro %d\n", macro_num);
             
        }
        return false;
    }

    if (speed_modifier_held) {
        cycle_macro_speed(macro_num);
        return false;  // Speed change handled, don't continue with normal macro logic
    }

    if (slow_modifier_held) {
        cycle_macro_slow(macro_num);
        return false;  // Speed change handled, don't continue with normal macro logic
    }

    if (octave_doubler_button_held) {
        if (overdub_button_held && overdub_advanced_mode) {
            // ADVANCED MODE + OVERDUB BUTTON: Apply to overdub octave doubler
            int8_t current_mode = get_overdub_octave_doubler_target(macro_num);
            int8_t next_mode;
            if (current_mode == 0) next_mode = 12;
            else if (current_mode == 12) next_mode = 24;
            else if (current_mode == 24) next_mode = -12;
            else next_mode = 0;
            
            set_overdub_octave_doubler_target(macro_num, next_mode);
            
            dprintf("dynamic macro: cycled OVERDUB octave doubler for macro %d\n", macro_num);
        } else {
            // NORMAL MODE or MACRO: Apply to macro octave doubler (existing behavior)
            int8_t current_mode = get_macro_octave_doubler_target(macro_num);
            int8_t next_mode;
            if (current_mode == 0) next_mode = 12;
            else if (current_mode == 12) next_mode = 24;
            else if (current_mode == 24) next_mode = -12;
            else next_mode = 0;
            
            set_macro_octave_doubler_target(macro_num, next_mode);
            
            dprintf("dynamic macro: cycled MACRO octave doubler for macro %d\n", macro_num);
            
            // If macro has content but is not playing, queue it to play so user can hear the octave doubler effect
            if (!macro_playback[macro_num - 1].is_playing) {
                // Check current state - count how many things are playing
                uint8_t playing_count = 0;
                for (uint8_t i = 0; i < MAX_MACROS; i++) {
                    if (macro_playback[i].is_playing) {
                        playing_count++;
                    }
                    else if (overdub_playback[i].is_playing) {
                        playing_count++;
                    }
                }
                
                if (playing_count > 0) {
                    // Other things are playing - queue play command for loop trigger
                    add_command_to_batch(CMD_PLAY, macro_num);
                    dprintf("dynamic macro: queued play command for macro %d to hear octave doubler effect\n", macro_num);
                } else {
                    // Nothing else playing - do nothing
                }
            }
        }
        
         
        return false;  // Exit early, don't proceed with normal macro key logic
    }
    
    dprintln("Macro key pressed");
    
    // Get macro buffer and end pointer for this macro
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
    
    // OVERDUB HANDLING
    bool this_macro_playing = macro_playback[macro_idx].is_playing;
    bool this_macro_empty = (macro_start == *macro_end_ptr);
    bool this_macro_in_overdub = macro_in_overdub_mode[macro_idx];
    bool this_overdub_muted = overdub_muted[macro_idx];
    bool has_overdub_content = (overdub_buffers[macro_idx] != NULL && 
                               overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx]);
    
    // Handle mute button + macro key combination (alternative mute control)
    if (mute_button_held) {
        return handle_mute_button_combinations(macro_num, macro_idx, macro_start, macro_end_ptr,
                                              this_macro_playing, this_macro_empty, 
                                              this_macro_in_overdub, this_overdub_muted, has_overdub_content);
    }
    
    // NEW DOUBLE-TAP DETECTION LOGIC
    uint16_t current_time = timer_read();
    
    // ADVANCED MODE: Separate double-tap detection for macro vs overdub operations
    if (overdub_advanced_mode) {
        bool is_overdub_operation = overdub_button_held || mute_button_held;
        
        if (is_overdub_operation) {
            // OVERDUB OPERATION - check overdub timing
            uint16_t time_since_last_overdub_press = timer_elapsed(last_overdub_press_time[macro_idx]);
            
            if (time_since_last_overdub_press < DOUBLE_TAP_THRESHOLD && !sample_mode_active && (unsynced_mode_active != 2 && unsynced_mode_active != 5) && !octave_doubler_button_held && !global_edit_modifier_held) {
                dprintf("dynamic macro: OVERDUB double-tap detected for macro %d - stopping overdub only\n", macro_num);
                
                // Process pending overdub merge immediately
                if (overdub_merge_pending[macro_idx]) {
                    process_pending_overdub_merge(macro_idx);
                    dprintf("dynamic macro: processed pending overdub merge for macro %d on overdub double-tap\n", macro_num);
                }
                
                // Stop overdub recording if active
                if (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num) {
                    end_overdub_recording_mode_aware(macro_num, false, false);
                    dprintf("dynamic macro: stopped overdub recording %d on overdub double-tap\n", macro_num);
                }
                
                // Stop overdub playback
                if (overdub_playback[macro_idx].is_playing) {
                    dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
                    overdub_playback[macro_idx].is_playing = false;
                    overdub_playback[macro_idx].current = NULL;
                    dprintf("dynamic macro: stopped overdub %d on overdub double-tap\n", macro_num);
                }
                
                // Clear any pending overdub commands for this macro
                for (uint8_t i = 0; i < command_batch_count; i++) {
                    if (command_batch[i].macro_id == macro_num && !command_batch[i].processed && 
                        (command_batch[i].command_type == CMD_ADVANCED_OVERDUB_REC || 
                         command_batch[i].command_type == CMD_ADVANCED_OVERDUB_END)) {
                        // Remove this command by shifting all subsequent commands
                        for (uint8_t j = i; j < command_batch_count - 1; j++) {
                            command_batch[j] = command_batch[j + 1];
                        }
                        command_batch_count--;
                        i--; // Check the same index again
                        dprintf("dynamic macro: cleared pending overdub command for macro %d on overdub double-tap\n", macro_num);
                    }
                }
                
                // Set overdub state only
                overdub_muted[macro_idx] = true;
                overdub_mute_pending[macro_idx] = false;
                overdub_unmute_pending[macro_idx] = false;
                overdub_merge_pending[macro_idx] = false;
                capture_early_overdub_events[macro_idx] = false;
                early_overdub_count[macro_idx] = 0;
                memset(early_overdub_buffer[macro_idx], 0, sizeof(early_overdub_buffer[macro_idx]));
                
                last_overdub_press_time[macro_idx] = current_time;
                 
                return false;  // Completely handled
            }
            
            // Update overdub press time for next comparison
            last_overdub_press_time[macro_idx] = current_time;
            
        } else {
            // MAIN MACRO OPERATION - check macro timing
            uint16_t time_since_last_macro_press = timer_elapsed(last_macro_press_time[macro_idx]);
            
            if (time_since_last_macro_press < DOUBLE_TAP_THRESHOLD && !sample_mode_active && (unsynced_mode_active != 2 && unsynced_mode_active != 5) && !octave_doubler_button_held && !global_edit_modifier_held) {
                dprintf("dynamic macro: MACRO double-tap detected for macro %d - stopping main macro only\n", macro_num);
                
                // If this macro is currently recording a main macro, handle special logic
                if (macro_id == macro_num && !macro_in_overdub_mode[macro_idx]) {
                    dprintf("dynamic macro: ignoring second press for macro %d - main macro recording will continue until loop trigger\n", macro_num);
                    last_macro_press_time[macro_idx] = current_time;
                    skip_autoplay_for_macro[macro_idx] = true;
                    ignore_second_press[macro_idx] = true;
                    return false;
                }
                
                // Stop main macro playback only
                if (macro_playback[macro_idx].is_playing) {
                    dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
                    macro_playback[macro_idx].is_playing = false;
                    macro_playback[macro_idx].current = NULL;
                    dprintf("dynamic macro: stopped main macro %d on macro double-tap\n", macro_num);
                }
                
                // Clear any pending main macro commands for this macro
                for (uint8_t i = 0; i < command_batch_count; i++) {
                    if (command_batch[i].macro_id == macro_num && !command_batch[i].processed && 
                        (command_batch[i].command_type == CMD_PLAY || 
                         command_batch[i].command_type == CMD_STOP || 
                         command_batch[i].command_type == CMD_RECORD)) {
                        // Remove this command by shifting all subsequent commands
                        for (uint8_t j = i; j < command_batch_count - 1; j++) {
                            command_batch[j] = command_batch[j + 1];
                        }
                        command_batch_count--;
                        i--; // Check the same index again
                        dprintf("dynamic macro: cleared pending main macro command for macro %d on macro double-tap\n", macro_num);
                    }
                }
                
                // Set main macro state only
                macro_main_muted[macro_idx] = false;
                skip_autoplay_for_macro[macro_idx] = false;
                ignore_second_press[macro_idx] = false;
                
                last_macro_press_time[macro_idx] = current_time;
                 
                return false;  // Completely handled
            }
            
            // Update macro press time for next comparison
            last_macro_press_time[macro_idx] = current_time;
        }
        
    } else {
        // ORIGINAL MODE: Keep existing unified double-tap behavior (affects everything)
        uint16_t time_since_last_press = timer_elapsed(last_macro_press_time[macro_idx]);
        
        if (time_since_last_press < DOUBLE_TAP_THRESHOLD && !sample_mode_active && (unsynced_mode_active != 2 && unsynced_mode_active != 5) && !overdub_button_held && !mute_button_held && !octave_doubler_button_held && !global_edit_modifier_held) {
            dprintf("dynamic macro: double-tap detected for macro %d - immediate stop and mute (original mode)\n", macro_num);
            
            // Process pending overdub merge immediately (before stopping anything)
            if (overdub_merge_pending[macro_idx]) {
                process_pending_overdub_merge(macro_idx);
                dprintf("dynamic macro: processed pending overdub merge for macro %d on double-tap\n", macro_num);
            }
            
            // If this macro is currently recording a main macro, don't end it yet
            if (macro_id == macro_num && !macro_in_overdub_mode[macro_idx]) {
                dprintf("dynamic macro: ignoring second press for macro %d - main macro recording will continue until loop trigger\n", macro_num);
                last_macro_press_time[macro_idx] = current_time;
                skip_autoplay_for_macro[macro_idx] = true;
                ignore_second_press[macro_idx] = true;
                return false;
            }
            
            // Stop overdub recording if active
            if (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num) {
                end_overdub_recording_mode_aware(macro_num, false, false);
                dprintf("dynamic macro: stopped overdub recording %d on double-tap\n", macro_num);
            }
            
            // Stop main macro playback
            if (macro_playback[macro_idx].is_playing) {
                dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
                macro_playback[macro_idx].is_playing = false;
                macro_playback[macro_idx].current = NULL;
                dprintf("dynamic macro: stopped main macro %d on double-tap\n", macro_num);
            }
            
            // Stop overdub playback (linked stop like CMD_STOP)
            if (overdub_playback[macro_idx].is_playing) {
                dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
                overdub_playback[macro_idx].is_playing = false;
                overdub_playback[macro_idx].current = NULL;
                dprintf("dynamic macro: stopped overdub %d on double-tap (linked stop)\n", macro_num);
            }
            
            // Clear any pending commands for this macro
            for (uint8_t i = 0; i < command_batch_count; i++) {
                if (command_batch[i].macro_id == macro_num && !command_batch[i].processed) {
                    // Remove this command by shifting all subsequent commands
                    for (uint8_t j = i; j < command_batch_count - 1; j++) {
                        command_batch[j] = command_batch[j + 1];
                    }
                    command_batch_count--;
                    i--;
                    dprintf("dynamic macro: cleared pending command for macro %d on double-tap\n", macro_num);
                }
            }
            
            // Set final state to match CMD_STOP result
            macro_main_muted[macro_idx] = false;
            overdub_muted[macro_idx] = true;
            overdub_mute_pending[macro_idx] = false;
            overdub_unmute_pending[macro_idx] = false;
            overdub_merge_pending[macro_idx] = false;
            skip_autoplay_for_macro[macro_idx] = false;
            ignore_second_press[macro_idx] = false;
            capture_early_overdub_events[macro_idx] = false;
            early_overdub_count[macro_idx] = 0;
            memset(early_overdub_buffer[macro_idx], 0, sizeof(early_overdub_buffer[macro_idx]));
            
            last_macro_press_time[macro_idx] = current_time;
             
            return false;
        }
        
        // Always update macro press time in original mode (unified timing)
        last_macro_press_time[macro_idx] = current_time;
    }

    // Reset the skip flags if we get past double-tap detection
    skip_autoplay_for_macro[macro_idx] = false;
    ignore_second_press[macro_idx] = false;

    // Handle advanced overdub mode
    if (overdub_advanced_mode) {
        return handle_overdub_advanced_mode(macro_num, macro_idx, macro_start, macro_end_ptr,
                                           this_macro_playing, this_macro_empty);
    }    
    
    // Handle macro button while overdub recording and main macro ghost muted
    if (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num && macro_main_muted[macro_idx] && macro_playback[macro_idx].is_playing) {
        end_overdub_recording_mode_aware(macro_num, false, true);
        
        uint8_t playing_count = 0;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                playing_count++;
            }
        }
        
        if (playing_count > 0) {
            // Use batching - unmute overdub at loop trigger
            overdub_unmute_pending[macro_idx] = true;
            dprintf("dynamic macro: stopped overdub recording, scheduled overdub unmute for macro %d (main stays muted)\n", macro_num);
        } else {
            // Execute immediately - unmute overdub
            overdub_muted[macro_idx] = false;
            dprintf("dynamic macro: stopped overdub recording, immediately unmuted overdub for macro %d (main stays muted)\n", macro_num);
        }
        
        // Main macro stays in ghost muted state
         
        return false;
    }
    
    if (macro_main_muted[macro_idx] && macro_playback[macro_idx].is_playing) {
        // Macro is muted but still playing - unmute it
        uint8_t playing_count = 0;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                playing_count++;
            }
        }
        
        if (playing_count > 0) {
            // Other things are playing - use batching to unmute
            add_command_to_batch(CMD_PLAY, macro_num);
            dprintf("dynamic macro: queued unmute for muted macro %d\n", macro_num);
        } else {
            // Nothing else playing - unmute immediately and reset to position 0
            macro_main_muted[macro_idx] = false;
            
            // Reset to position 0
            macro_playback[macro_idx].current = macro_playback[macro_idx].buffer_start;
            macro_playback[macro_idx].timer = timer_read32();
            macro_playback[macro_idx].next_event_time = macro_playback[macro_idx].timer + 
                                                       macro_playback[macro_idx].current->timestamp;
            macro_playback[macro_idx].waiting_for_loop_gap = false;
            
            // Clean up any hanging notes before restart
            cleanup_notes_from_macro(macro_num);
            
            dprintf("dynamic macro: immediately unmuted and reset macro %d to position 0\n", macro_num);
        }
        
         
        return false;
    }

    // FEATURE #1: If overdub is active for this macro, end the overdub
    if (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num) {
        // End overdub recording for this macro (auto-mute only in original mode)
        end_overdub_recording_mode_aware(macro_num, false, true);
        
        dprintf("dynamic macro: ended overdub recording for macro %d (same button press)\n", macro_num);
         
        return false;
    }
    
    if (this_macro_in_overdub) {
        // Case 1: Macro is in overdub mode and we press without overdub button
        // Schedule to exit overdub mode at next loop trigger
        dprintf("dynamic macro: scheduling to exit overdub mode for macro %d at next loop trigger\n", macro_num);
        
        if ((unsynced_mode_active == 2 || unsynced_mode_active == 5)) {
            // In unsynced mode, exit overdub immediately
            end_overdub_recording_deferred(macro_num);
            macro_in_overdub_mode[macro_idx] = false;
            overdub_target_macro = 0;
            macro_id = 0;
            current_macro_id = 0;
            stop_dynamic_macro_recording();
            dprintf("dynamic macro: immediately exited overdub mode for macro %d\n", macro_num);
        } else {
            // In normal mode, add a command to exit overdub at loop trigger
            //add_command_to_batch(CMD_STOP, macro_num);
            //add_command_to_batch(CMD_PLAY, macro_num);
             
            dprintf("dynamic macro: batched commands to exit overdub for macro %d\n", macro_num);
        }
        return false;
    }
    
    if (overdub_button_held && this_macro_playing && !this_macro_in_overdub) {
        // Case 2: Macro is playing, we hold overdub and press the macro
        // Enter overdub mode immediately
        start_overdub_recording(macro_num);
        dprintf("dynamic macro: entered overdub mode for playing macro %d\n", macro_num);
        return false;
    }
    
    if (overdub_button_held && !this_macro_playing && !this_macro_empty) {
        // Case 3: Macro is not playing, has content, we hold overdub and press the macro
        // Play it muted and enter overdub mode (same as overdub+mute on playing macro)
        
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (is_macro_effectively_playing(i)) {
                any_macros_playing = true;
                break;
            }
        }
        
        if ((unsynced_mode_active == 2 || unsynced_mode_active == 5) || sample_mode_active || !any_macros_playing) {
            // In unsynced or sample mode, play immediately muted and enter overdub
            dynamic_macro_play(macro_start, *macro_end_ptr, +1);
            macro_main_muted[macro_idx] = true;  // Mute it immediately
            
            // Start overdub recording
            start_overdub_recording(macro_num);
            dprintf("dynamic macro: started muted playback with overdub for macro %d\n", macro_num);
        } else {
            // In normal mode, batch the commands like overdub+mute does
            if (!command_exists_in_batch(CMD_PLAY, macro_num)) {
                add_command_to_batch(CMD_PLAY, macro_num);
                add_command_to_batch(CMD_OVERDUB_AFTER_MUTE, macro_num);  // This triggers early overdub capture!
                macro_in_overdub_mode[macro_idx] = true;
                start_overdub_recording(macro_num);
                 
                dprintf("dynamic macro: batched play with overdub-after-mute for macro %d\n", macro_num);
            } else {
                // Remove the commands
                remove_command_from_batch(CMD_PLAY, macro_num);
                remove_command_from_batch(CMD_OVERDUB_AFTER_MUTE, macro_num);
                macro_in_overdub_mode[macro_idx] = false;
                 
                dprintf("dynamic macro: removed play and overdub commands for macro %d\n", macro_num);
            }
        }
        
        return false;
    }
    
    // Handle overdub button + recording macro
    if (overdub_button_held && macro_id == macro_num) {
        // Check current state - count how many things are playing
        uint8_t playing_count = 0;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing) {
                playing_count++;
            }
            else if (overdub_playback[i].is_playing) {
                playing_count++;
            }
        }
        
        if (playing_count == 0) {
            // No other macros playing - finish recording and enter overdub immediately
            dynamic_macro_record_end(macro_start, macro_pointer, +1, macro_end_ptr, &recording_start_time);
            macro_id = 0;
            stop_dynamic_macro_recording();
            
            // Start playback immediately
            if (!is_macro_empty) {
                dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                dprintf("dynamic macro: finished recording and started playback of macro %d\n", macro_num);
                
                // Enter overdub mode immediately
                start_overdub_recording(macro_num);
                dprintf("dynamic macro: entered overdub mode for macro %d after recording\n", macro_num);
            }
            
            return false;
        } else {
            // Other macros are playing - queue commands to stop recording and start overdub at loop trigger
            add_command_to_batch(CMD_STOP, macro_num);   // Stop the current recording
            add_command_to_batch(CMD_PLAY, macro_num);   // Start playback of the recorded macro
            macro_in_overdub_mode[macro_idx] = true;     // Flag to enter overdub when PLAY executes
            
            dprintf("dynamic macro: queued stop recording and start overdub for macro %d at loop trigger\n", macro_num);
             
            return false;
        }
    }
    
    // Handle overdub button + empty macro (do nothing)
    if (overdub_button_held && this_macro_empty && macro_id == 0) {
        // Empty macro with overdub button - do nothing
        dprintf("dynamic macro: overdub button held on empty macro %d - ignoring\n", macro_num);
        return false;  // Exit early, don't proceed with any recording
    }
    
    if (overdub_button_held && macro_id > 0 && macro_id != macro_num) {
        // Check if target macro is empty - if so, do nothing
        midi_event_t *target_macro_start = get_macro_buffer(macro_num);
        midi_event_t **target_macro_end_ptr = get_macro_end_ptr(macro_num);
        if (target_macro_start == *target_macro_end_ptr) {
            // Target macro is empty - do nothing
            dprintf("dynamic macro: overdub button held on empty macro %d - ignoring\n", macro_num);
            return false;
        }
        
        // Target macro has content - set flag to enter overdub mode after recording stops
        macro_in_overdub_mode[macro_idx] = true;
        dprintf("dynamic macro: will enter overdub mode after recording stops for macro %d\n", macro_num);
        // Continue with normal processing to handle recording stop
    }
    
    // UNSYNCED MODE HANDLING
    if ((unsynced_mode_active == 2 || unsynced_mode_active == 5)) {
        return handle_unsynced_mode(macro_num, macro_idx, macro_start, macro_end_ptr, 
                                   this_macro_playing, this_macro_empty);
    }
    
    // SAMPLE MODE HANDLING
    if (sample_mode_active) {
        return handle_sample_mode(macro_num, macro_idx, macro_start, macro_end_ptr,
                                 this_macro_playing, this_macro_empty);
    }
    
    // REGULAR MODE HANDLING
    return handle_regular_mode(macro_num, macro_idx, macro_start, macro_end_ptr,
                              this_macro_playing, this_macro_empty);
}

static bool handle_mute_button_combinations(uint8_t macro_num, uint8_t macro_idx, 
                                           midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                                           bool this_macro_playing, bool this_macro_empty,
                                           bool this_macro_in_overdub, bool this_overdub_muted, 
                                           bool has_overdub_content) {
    
// Case: Overdub recording with main macro ghost muted + just mute + macro
if (!overdub_button_held && macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num && macro_main_muted[macro_idx] && macro_playback[macro_idx].is_playing) {
end_overdub_recording_mode_aware(macro_num, false, true);
    
    uint8_t playing_count = 0;
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
            playing_count++;
        }
    }
    
    if (playing_count > 0) {
        // Use batching - mute overdub and queue stop for main
        overdub_mute_pending[macro_idx] = true;
        add_command_to_batch(CMD_STOP, macro_num);
        dprintf("dynamic macro: stopped overdub recording, scheduled overdub mute and main stop for macro %d\n", macro_num);
    } else {
        // Execute immediately - mute overdub and stop main
        overdub_muted[macro_idx] = true;
        
        // Stop main macro
        if (macro_playback[macro_idx].is_playing) {
            dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
            macro_playback[macro_idx].is_playing = false;
            macro_playback[macro_idx].current = NULL;
        }
        macro_main_muted[macro_idx] = false; // Reset mute flag
        
        dprintf("dynamic macro: stopped overdub recording, immediately muted overdub and stopped main for macro %d\n", macro_num);
    }
    
     
    return false;
}
	
    if (!has_overdub_content && !overdub_button_held && !this_macro_in_overdub && !overdub_merge_pending[macro_idx] && !overdub_button_held && macro_id != macro_num) {
        dprintf("dynamic macro: no overdub content for macro %d - ignoring mute button\n", macro_num);
        return false;
    }

    if (overdub_button_held) {
        // CASE 1: Both overdub and mute held + macro recording - mute macro and start overdub record
        if (macro_id == macro_num && !this_macro_in_overdub) {
            uint8_t playing_count = 0;
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                    playing_count++;
                }
            }
            
            if (playing_count > 0) {
                // Use batched command for synchronized execution
                add_command_to_batch(CMD_PLAY_MUTED, macro_num);
                dprintf("dynamic macro: queued muted play with overdub for macro %d\n", macro_num);
            } else {
                // Execute immediately
                dynamic_macro_record_end(macro_start, macro_pointer, +1, macro_end_ptr, &recording_start_time);
                macro_id = 0;
                stop_dynamic_macro_recording();
                
                if (!is_macro_empty) {
                    dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                    macro_main_muted[macro_idx] = true;
                    start_overdub_recording(macro_num);
                    dprintf("dynamic macro: ended recording, started muted playback with overdub for macro %d\n", macro_num);
                }
            }
            
             
            return false;
        }
		
		// Case: Overdub recording with main macro ghost muted + mute + overdub + macro
		if (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num && macro_main_muted[macro_idx] && macro_playback[macro_idx].is_playing) {
end_overdub_recording_mode_aware(macro_num, false, true);
			
			uint8_t playing_count = 0;
			for (uint8_t i = 0; i < MAX_MACROS; i++) {
				if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
					playing_count++;
				}
			}
			
			if (playing_count > 0) {
				// Use batching - mute overdub and queue play for main
				overdub_mute_pending[macro_idx] = true;
				add_command_to_batch(CMD_PLAY, macro_num);
				dprintf("dynamic macro: stopped overdub recording, scheduled overdub mute and main play for macro %d\n", macro_num);
			} else {
				// Execute immediately - mute overdub and unmute main
				overdub_muted[macro_idx] = true;
				macro_main_muted[macro_idx] = false; // Unmute main
				dprintf("dynamic macro: stopped overdub recording, immediately muted overdub and unmuted main for macro %d\n", macro_num);
			}
			
			 
			return false;
		}
        
        // CASE 2: Currently overdub recording - end overdub and solo the overdub (mute main + play overdub)
        if (this_macro_in_overdub && overdub_target_macro == macro_num) {
            end_overdub_recording_deferred(macro_num);
            macro_in_overdub_mode[macro_idx] = false;
            overdub_target_macro = 0;
            macro_id = 0;
            current_macro_id = 0;
            stop_dynamic_macro_recording();
            
            uint8_t playing_count = 0;
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                    playing_count++;
                }
            }
            
            if (playing_count > 0) {
                // Use batching - mute main and play overdub solo
                if (!macro_main_muted[macro_idx]) {
                    add_command_to_batch(CMD_GHOST_MUTE, macro_num);
                }
                add_command_to_batch(CMD_PLAY_OVERDUB_ONLY, macro_num);
                overdub_unmute_pending[macro_idx] = true;
                dprintf("dynamic macro: ended overdub recording, queued muted main + solo overdub for macro %d\n", macro_num);
            } else {
                // Execute immediately - mute main (keep playing) and start overdub solo
                if (this_macro_playing) {
                    macro_main_muted[macro_idx] = true; // Mute instead of stopping
                }
                
                if (has_overdub_content) {
                    overdub_muted[macro_idx] = false;
                    
                    macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
                    overdub_state->current = overdub_buffers[macro_idx];
                    overdub_state->end = overdub_buffer_ends[macro_idx];
                    overdub_state->direction = +1;
                    overdub_state->timer = timer_read32();
                    overdub_state->buffer_start = overdub_buffers[macro_idx];
                    overdub_state->is_playing = true;
                    overdub_state->waiting_for_loop_gap = false;
                    overdub_state->next_event_time = 0;
                    reset_bpm_timing_for_loop_start();
                    
                    dprintf("dynamic macro: ended overdub recording, immediately started muted main + solo overdub for macro %d\n", macro_num);
                }
            }
            
             
            return false;
        }
		
				if (this_macro_playing && !has_overdub_content && !this_macro_in_overdub) {
			uint8_t playing_count = 0;
			for (uint8_t i = 0; i < MAX_MACROS; i++) {
				if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
					playing_count++;
				}
			}
			
			if (playing_count > 0) {
				// Use batching - ghost mute first, then start overdub
				add_command_to_batch(CMD_GHOST_MUTE, macro_num);
				add_command_to_batch(CMD_OVERDUB_AFTER_MUTE, macro_num);
				dprintf("dynamic macro: queued ghost mute and delayed overdub for macro %d\n", macro_num);
			} else {
				// Execute immediately - mute and start overdub
				macro_main_muted[macro_idx] = true;
				start_overdub_recording(macro_num);
				dprintf("dynamic macro: immediately muted and started overdub for macro %d\n", macro_num);
			}
			
			 
			return false;
		}

		// NEW CASE: Macro already muted without overdub data + overdub + mute held  
		if (macro_main_muted[macro_idx] && macro_playback[macro_idx].is_playing && !has_overdub_content && !this_macro_in_overdub) {
			uint8_t playing_count = 0;
			for (uint8_t i = 0; i < MAX_MACROS; i++) {
				if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
					playing_count++;
				}
			}
			
			if (playing_count > 0) {
				// Use batching - ensure ghost mute and start overdub
				add_command_to_batch(CMD_GHOST_MUTE, macro_num); // Ensure it stays muted
				add_command_to_batch(CMD_OVERDUB_AFTER_MUTE, macro_num);
				dprintf("dynamic macro: queued ghost mute maintenance and delayed overdub for muted macro %d\n", macro_num);
			} else {
				// Execute immediately - already muted, just start overdub
				start_overdub_recording(macro_num);
				dprintf("dynamic macro: immediately started overdub for already muted macro %d\n", macro_num);
			}
			
			 
			return false;
		}
        
        // CASE 3: Overdub is playing solo - unmute main and mute overdub
        if (overdub_playback[macro_idx].is_playing && macro_main_muted[macro_idx]) {
            uint8_t playing_count = 0;
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                    playing_count++;
                }
            }
            
            if (playing_count > 0) {
                // Use batching - queue CMD_PLAY to unmute main, and schedule overdub mute
                overdub_mute_pending[macro_idx] = true; // Schedule mute overdub
                add_command_to_batch(CMD_PLAY, macro_num); // This will unmute main
                dprintf("dynamic macro: scheduled unmute main and mute overdub for macro %d\n", macro_num);
		} else {
				// Execute immediately - unmute main and mute overdub
				bool was_muted = macro_main_muted[macro_idx];
				macro_main_muted[macro_idx] = false; // Unmute main
				
				// If it was muted and still playing, reset to position 0
				if (was_muted && macro_playback[macro_idx].is_playing) {
					macro_playback[macro_idx].current = macro_playback[macro_idx].buffer_start;
					macro_playback[macro_idx].timer = timer_read32();
					macro_playback[macro_idx].next_event_time = macro_playback[macro_idx].timer + 
															   macro_playback[macro_idx].current->timestamp;
					macro_playback[macro_idx].waiting_for_loop_gap = false;
					
					// Clean up any hanging notes before restart
					cleanup_notes_from_macro(macro_num);
					
					dprintf("dynamic macro: immediately reset muted macro %d to position 0\n", macro_num);
				}
				
				// Stop and mute overdub
				overdub_muted[macro_idx] = true;
				dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
				overdub_playback[macro_idx].is_playing = false;
				overdub_playback[macro_idx].current = NULL;
				
				dprintf("dynamic macro: immediately unmuted main and muted overdub for macro %d\n", macro_num);
			}
            
             
            return false;
        }
        
		// CASE 4: Main macro playing - check if overdub is muted to determine behavior
				if (this_macro_playing) {
					uint8_t playing_count = 0;
					for (uint8_t i = 0; i < MAX_MACROS; i++) {
						if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
							playing_count++;
						}
					}
					
					// Check if overdub is currently muted - if so, restart main and unmute overdub
					if (has_overdub_content && this_overdub_muted) {
						if (playing_count > 0) {
							// Use batching - restart main (but keep it muted) and unmute overdub
							add_command_to_batch(CMD_STOP, macro_num);
							add_command_to_batch(CMD_GHOST_MUTE, macro_num);  // This will start muted
							add_command_to_batch(CMD_PLAY, macro_num);        // This will start playback
							overdub_unmute_pending[macro_idx] = true;
							if (!overdub_playback[macro_idx].is_playing) {
								add_command_to_batch(CMD_PLAY_OVERDUB_ONLY, macro_num);
							}
							
							dprintf("dynamic macro: scheduled to restart main macro %d (muted) and unmute overdub\n", macro_num);
						} else {
							// Execute immediately - restart main from position 0, ghost mute it, and unmute overdub
							// Clean up any hanging notes before restart
							cleanup_notes_from_macro(macro_num);
							
							// Reset main macro to position 0
							macro_playback[macro_idx].current = macro_playback[macro_idx].buffer_start;
							macro_playback[macro_idx].timer = timer_read32();
							macro_playback[macro_idx].next_event_time = macro_playback[macro_idx].timer + 
																	   macro_playback[macro_idx].current->timestamp;
							macro_playback[macro_idx].waiting_for_loop_gap = false;
							
							// Ghost mute the main macro (it plays but is muted)
							macro_main_muted[macro_idx] = true;
							
							// Unmute and start overdub
							overdub_muted[macro_idx] = false;
							
							macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
							overdub_state->current = overdub_buffers[macro_idx];
							overdub_state->end = overdub_buffer_ends[macro_idx];
							overdub_state->direction = +1;
							overdub_state->timer = macro_playback[macro_idx].timer; // Sync with restarted main macro
							overdub_state->buffer_start = overdub_buffers[macro_idx];
							overdub_state->is_playing = true;
							overdub_state->waiting_for_loop_gap = false;
							overdub_state->next_event_time = 0;
							
							reset_bpm_timing_for_loop_start();
							
							dprintf("dynamic macro: immediately restarted main macro %d from position 0 (ghost muted) and unmuted overdub\n", macro_num);
						}
					} else {
						// Original behavior - mute main and solo overdub
						if (playing_count > 0) {
							// Use batching - mute main and start overdub solo
							add_command_to_batch(CMD_GHOST_MUTE, macro_num);
							
							if (has_overdub_content) {
								overdub_unmute_pending[macro_idx] = true;
								if (!overdub_playback[macro_idx].is_playing) {
									add_command_to_batch(CMD_PLAY_OVERDUB_ONLY, macro_num);
								}
							}
							
							dprintf("dynamic macro: scheduled to mute main macro %d and start overdub solo\n", macro_num);
						} else {
							// Execute immediately - mute main and start overdub
							macro_main_muted[macro_idx] = true; // Mute instead of stopping
							
							if (has_overdub_content) {
								overdub_muted[macro_idx] = false;
								
								macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
								overdub_state->current = overdub_buffers[macro_idx];
								overdub_state->end = overdub_buffer_ends[macro_idx];
								overdub_state->direction = +1;
								overdub_state->timer = macro_playback[macro_idx].timer; // Sync with main macro
								overdub_state->buffer_start = overdub_buffers[macro_idx];
								overdub_state->is_playing = true;
								overdub_state->waiting_for_loop_gap = false;
								overdub_state->next_event_time = 0;
								
								dprintf("dynamic macro: immediately muted main and started overdub solo for macro %d\n", macro_num);
							}
						}
					}
					
					 
					return false;
				}
        
        // CASE 5: Overdub is playing with other things - mute overdub and unmute main
        else if (overdub_playback[macro_idx].is_playing) {
            uint8_t playing_count = 0;
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                    playing_count++;
                }
            }
            
            if (playing_count > 1) {
                // Use batching - queue CMD_PLAY to unmute main, and schedule overdub mute
                overdub_mute_pending[macro_idx] = true; // Schedule mute overdub
                add_command_to_batch(CMD_PLAY, macro_num); // This will unmute main
                dprintf("dynamic macro: scheduled unmute main and mute overdub for macro %d\n", macro_num);
            } else {
                // Execute immediately
                macro_main_muted[macro_idx] = false; // Unmute main
                
                dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
                overdub_playback[macro_idx].is_playing = false;
                overdub_playback[macro_idx].current = NULL;
                overdub_muted[macro_idx] = true;
                
                dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                dprintf("dynamic macro: immediately unmuted main and muted overdub for macro %d\n", macro_num);
            }
            
             
            return false;
        }
        
        // CASE 6: Main macro not playing - start main muted and solo overdub
        else {
            if (has_overdub_content) {
                uint8_t playing_count = 0;
                for (uint8_t i = 0; i < MAX_MACROS; i++) {
                    if (macro_playback[i].is_playing) {
                        playing_count++;
                    }
                    else if (overdub_playback[i].is_playing) {
                        playing_count++;
                    }
                }
                
                if (playing_count > 0) {
                    // Use batching - start main muted and overdub solo
                    add_command_to_batch(CMD_GHOST_MUTE, macro_num);
                    overdub_unmute_pending[macro_idx] = true;
                    add_command_to_batch(CMD_PLAY, macro_num); // Start main (will be muted)
                    add_command_to_batch(CMD_PLAY_OVERDUB_ONLY, macro_num); // Start overdub
                    dprintf("dynamic macro: scheduled muted main + overdub solo for macro %d\n", macro_num);
                } else {
                    // Execute immediately - start main muted and overdub solo
                    dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                    macro_main_muted[macro_idx] = true; // Mute the main
                    
                    overdub_muted[macro_idx] = false;
                    
                    macro_playback_state_t *overdub_state = &overdub_playback[macro_idx];
                    overdub_state->current = overdub_buffers[macro_idx];
                    overdub_state->end = overdub_buffer_ends[macro_idx];
                    overdub_state->direction = +1;
                    overdub_state->timer = macro_playback[macro_idx].timer; // Sync with main
                    overdub_state->buffer_start = overdub_buffers[macro_idx];
                    overdub_state->is_playing = true;
                    overdub_state->waiting_for_loop_gap = false;
                    overdub_state->next_event_time = 0;
                    
                    if (macro_playback[macro_idx].loop_length > 0) {
                        overdub_state->loop_gap_time = macro_playback[macro_idx].loop_gap_time;
                        overdub_state->loop_length = macro_playback[macro_idx].loop_length;
                    }
                    
                    reset_bpm_timing_for_loop_start();
                    dprintf("dynamic macro: immediately started muted main + overdub solo for macro %d\n", macro_num);
                }
            }
            
             
            return false;
        }
    }

    // Handle just mute button held (not overdub) - overdub solo case
    if (overdub_playback[macro_idx].is_playing && macro_main_muted[macro_idx]) {
        // Overdub is playing solo - stop main and mute overdub
        uint8_t playing_count = 0;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (is_macro_effectively_playing(i) || overdub_playback[i].is_playing) {
                playing_count++;
            }
        }
        
        if (playing_count > 0) {
            // Use batching - queue CMD_STOP to unmute and stop main, and schedule overdub mute
            overdub_mute_pending[macro_idx] = true; // Schedule mute overdub
            add_command_to_batch(CMD_STOP, macro_num); // This will unmute and stop main
            dprintf("dynamic macro: scheduled mute overdub and stop main for macro %d\n", macro_num);
        } else {
            // Execute immediately - stop main and mute overdub
            if (macro_playback[macro_idx].is_playing) {
                dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
                macro_playback[macro_idx].is_playing = false;
                macro_playback[macro_idx].current = NULL;
            }
            macro_main_muted[macro_idx] = false; // Reset mute flag
            
            // Stop and mute overdub
            overdub_muted[macro_idx] = true;
            dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
            overdub_playback[macro_idx].is_playing = false;
            overdub_playback[macro_idx].current = NULL;
            
            dprintf("dynamic macro: immediately stopped main and muted overdub for macro %d\n", macro_num);
        }
        
         
        return false;
    }
	
	if (overdub_mute_pending[macro_idx]) {
    // Currently pending mute - switch to pending unmute
    overdub_mute_pending[macro_idx] = false;
    overdub_unmute_pending[macro_idx] = true;
    dprintf("dynamic macro: switched from pending mute to pending unmute for macro %d\n", macro_num);
     
    return false;
	} else if (overdub_unmute_pending[macro_idx]) {
    // Currently pending unmute - switch to pending mute
    overdub_unmute_pending[macro_idx] = false;
    overdub_mute_pending[macro_idx] = true;
    dprintf("dynamic macro: switched from pending unmute to pending mute for macro %d\n", macro_num);
     
    return false;
	}
    
    // Check current state - count how many things are playing (macros + solo overdubs)
    uint8_t playing_count = 0;
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (is_macro_effectively_playing(i)) {
            playing_count++;
        }
        // Also count overdubs that are playing solo (without their main macro)
        else if (overdub_playback[i].is_playing) {
            playing_count++;
        }
    }
    
    // SCENARIO 1: Stopped macro with data - Mute overdub and play macro
    if (!this_macro_playing && !this_macro_empty) {
        if (playing_count > 0) {
            // Other things are playing - use batching to wait for loop trigger
            overdub_mute_pending[macro_idx] = true;  // Schedule mute
            add_command_to_batch(CMD_PLAY, macro_num);  // Schedule play
            dprintf("dynamic macro: scheduled to mute overdub and play macro %d at loop trigger\n", macro_num);
             
            return false;
        } else {
            // Nothing else playing - execute immediately
            // 1. Immediately mute the overdub
            overdub_muted[macro_idx] = true;
            
            // 2. Start playing the macro (overdub will stay muted)
            dynamic_macro_play(macro_start, *macro_end_ptr, +1);
            
            dprintf("dynamic macro: immediately muted overdub and started macro %d playback\n", macro_num);
             
            return false;
        }
    }
    
    // SCENARIO 2: Overdub recording active - Finish overdub but leave it muted
else if (this_macro_in_overdub && overdub_target_macro == macro_num) {
    dprintf("dynamic macro: ending overdub with mute - before recording end\n");
    
    if (!overdub_advanced_mode) {
        overdub_mute_pending[macro_idx] = true;
    }
    
    end_overdub_recording_mode_aware(macro_num, false, true);
    
    if (!overdub_advanced_mode) {
        // Clear any conflicting unmute flags (only for original mode)
        overdub_unmute_pending[macro_idx] = false;
    }
    
    // 3. Also make sure overdub playback is really stopped
    // This is a backup to ensure the overdub doesn't play
    if (overdub_playback[macro_idx].is_playing) {
        dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
        overdub_playback[macro_idx].is_playing = false;
        overdub_playback[macro_idx].current = NULL;
        dprintf("dynamic macro: stopped overdub playback after muting\n");
    }
    
    // Clear any pending unmute flags for this macro (only if not advanced mode)
    if (!overdub_advanced_mode) {
        overdub_unmute_pending[macro_idx] = false;
    }
    
    dprintf("dynamic macro: ended overdub recording and forced mute for macro %d\n", macro_num);
     
    return false;
}
    
    // SCENARIO 3: Macro playing with overdub - Toggle mute state synchronously
    else if (this_macro_playing && has_overdub_content) {
        if (!this_overdub_muted) {
            // Currently unmuted - schedule mute at loop trigger
            overdub_mute_pending[macro_idx] = true;
            dprintf("dynamic macro: scheduled to mute overdub for macro %d at loop trigger\n", macro_num);
        } else {
            // Currently muted - schedule unmute at loop trigger
            overdub_unmute_pending[macro_idx] = true;
            dprintf("dynamic macro: scheduled to unmute overdub for macro %d at loop trigger\n", macro_num);
        }
        
         
        return false;
    }
    
    // SCENARIO 4: Overdub is playing solo (macro stopped) - Mute the overdub
    else if (!this_macro_playing && overdub_playback[macro_idx].is_playing && !overdub_button_held) {
        // Overdub is playing solo - schedule to mute it
        overdub_mute_pending[macro_idx] = true;
        dprintf("dynamic macro: scheduled to mute solo overdub for macro %d at loop trigger\n", macro_num);
         
        return false;
    }
    
    // Only perform mute/unmute operations if overdub content exists
    if (!overdub_button_held && has_overdub_content) {
        if (overdub_muted[macro_idx]) {
            // Currently muted - schedule unmute at loop trigger
            overdub_unmute_pending[macro_idx] = true;
            dprintf("dynamic macro: scheduled to unmute overdub for macro %d at loop trigger\n", macro_num);
        } else {
            // Currently unmuted - schedule mute at loop trigger
            overdub_mute_pending[macro_idx] = true;
            dprintf("dynamic macro: scheduled to mute overdub for macro %d at loop trigger\n", macro_num);
        }
        
         
        return false;
    }
    
    // If we get here, some button combination didn't match any criteria - do nothing
    dprintf("dynamic macro: unhandled mute/overdub button combination for macro %d - ignoring\n", macro_num);
    return false;
}

// Handle unsynced mode
static bool handle_unsynced_mode(uint8_t macro_num, uint8_t macro_idx, 
                                midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                                bool this_macro_playing, bool this_macro_empty) {
    
    // First, clear any commands for this macro from the batch
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].macro_id == macro_num && !command_batch[i].processed) {
            command_batch[i].processed = true; // Mark as processed (effectively removing it)
        }
    }
    
    // If we're currently recording this macro, stop recording immediately
    if (macro_id == macro_num) {
        // End recording immediately
		force_clear_all_live_notes();
        dynamic_macro_record_end(macro_start, macro_pointer, +1, macro_end_ptr, &recording_start_time);
        
        // Check if we need to enter overdub mode
        bool should_enter_overdub = macro_in_overdub_mode[macro_idx];
        
        // Reset recording state
        macro_id = 0;
        stop_dynamic_macro_recording();
        dprintf("dynamic macro: unsynced mode - immediately stopped recording of macro %d\n", macro_num);
        
        // Maybe play it back (if not skipped)
        if (!is_macro_empty && !skip_autoplay_for_macro[macro_idx]) {
			process_pending_states_for_macro(macro_idx);
            dynamic_macro_play(macro_start, *macro_end_ptr, +1);
			
            dprintf("dynamic macro: unsynced mode - started playback after recording macro %d\n", macro_num);
            
            // If flag was set to enter overdub, set it up now
            if (should_enter_overdub) {
                // Start overdub recording
                start_overdub_recording(macro_num);
                dprintf("dynamic macro: entered overdub mode for macro %d after recording\n", macro_num);
            }
        }
        
        return false;
    }
    
    // If macro is already playing, stop it immediately
    if (this_macro_playing) {
        // If in overdub mode, also stop recording
        if (macro_in_overdub_mode[macro_idx] && macro_id == macro_num) {
            end_overdub_recording_deferred(macro_num);
            dprintf("dynamic macro: unsynced mode - stopped overdub recording for macro %d\n", macro_num);
        } else {
            // Stop playback
            dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
            macro_playback[macro_idx].is_playing = false;
            macro_playback[macro_idx].current = NULL;
            macro_in_overdub_mode[macro_idx] = false;  // Clear overdub flag
            dprintf("dynamic macro: unsynced mode - immediately stopped playback of macro %d\n", macro_num);
        }
        return false;
    }
    
    // If macro has content and is not playing, play it immediately
    if (!this_macro_empty && !this_macro_playing) {
        // In sample mode, we stop all other macros
        if (sample_mode_active) {
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                if (macro_playback[i].is_playing) {
                    // If in overdub mode, also stop recording
                    if (macro_in_overdub_mode[i] && macro_id == i + 1) {
                        end_overdub_recording_deferred(i + 1);
                        dprintf("dynamic macro: stopped overdub recording for macro %d\n", i + 1);
                    } else {
                        dynamic_macro_cleanup_notes_for_state(&macro_playback[i]);
                        macro_playback[i].is_playing = false;
                        macro_playback[i].current = NULL;
                        macro_in_overdub_mode[i] = false;  // Clear overdub flag
                    }
                }
            }
        }
        
        // Play this macro
		process_pending_states_for_macro(macro_idx);
        dynamic_macro_play(macro_start, *macro_end_ptr, +1);
        dprintf("dynamic macro: unsynced mode - immediately started playback of macro %d\n", macro_num);
        
        // If overdub button is held, enter overdub mode
        if (overdub_button_held) {
            start_overdub_recording(macro_num);
            dprintf("dynamic macro: entered overdub mode for macro %d\n", macro_num);
        }
        
        return false;
    }
    
    // If macro is empty and we're not recording it, start recording
    if (this_macro_empty && macro_id == 0) {
        dynamic_macro_record_start(&macro_pointer, macro_start, +1, &recording_start_time);
        macro_id = macro_num;
        snapshot_recording_settings(macro_num);  // Snapshot curve/min/max when recording starts
        setup_dynamic_macro_recording(macro_id, macro_buffer, NULL, (void**)&macro_pointer, &recording_start_time);
        dprintf("dynamic macro: unsynced mode - started recording macro %d\n", macro_num);
        return false;
    }
    
    // If we're recording a different macro, let's keep the recording going
    // and don't handle this press any further
    if (macro_id > 0 && macro_id != macro_num) {
        dprintf("dynamic macro: unsynced mode - ignoring press while recording macro %d\n", macro_id);
        return false;
    }
    
    // If we got here, we've already handled all unsynced mode cases
    return false;
}

// Handle sample mode
static bool handle_sample_mode(uint8_t macro_num, uint8_t macro_idx,
                              midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                              bool this_macro_playing, bool this_macro_empty) {
    
    // Case 1: The macro is already playing - restart it from position 0
    if (this_macro_playing) {
        // First, check if in overdub mode and exit if needed
if (macro_in_overdub_mode[macro_idx] && macro_id == macro_num) {
    end_overdub_recording_mode_aware(macro_num, true, false); // Force immediate in sample mode
    dprintf("dynamic macro: sample mode - stopped overdub for macro %d\n", macro_num);
}
        
        // Clean up notes from this macro
        cleanup_notes_from_macro(macro_num);
		process_pending_states_for_macro(macro_idx);
        
        // Then restart the playback from position 0
        macro_playback[macro_idx].current = macro_playback[macro_idx].buffer_start;
        macro_playback[macro_idx].timer = timer_read32();
        macro_playback[macro_idx].next_event_time = macro_playback[macro_idx].timer + 
                                                   macro_playback[macro_idx].current->timestamp;
        macro_playback[macro_idx].waiting_for_loop_gap = false;
        
        // If overdub button is held, enter overdub mode
        if (overdub_button_held) {
            start_overdub_recording(macro_num);
            dprintf("dynamic macro: entered overdub mode for macro %d\n", macro_num);
        }
        
        dprintf("dynamic macro: sample mode - restarted macro %d from position 0\n", macro_num);
        return false;
    }
    
    // Case 2: We're already recording this macro
    if (macro_id == macro_num) {
        // End the recording immediately and play it back
        dynamic_macro_record_end(macro_start, macro_pointer, +1, macro_end_ptr, &recording_start_time);
        
        // Check if we need to enter overdub mode
        bool should_enter_overdub = macro_in_overdub_mode[macro_idx];
        
        // Reset recording state
        macro_id = 0;
        stop_dynamic_macro_recording();
        
        // Start playback (if not skipped by double-tap)
        if (!is_macro_empty && !skip_autoplay_for_macro[macro_idx]) {
			process_pending_states_for_macro(macro_idx);
            dynamic_macro_play(macro_start, *macro_end_ptr, +1);
            dprintf("dynamic macro: sample mode - ended recording and started playback of macro %d\n", macro_num);
            
            // If flag was set to enter overdub, set it up now
            if (should_enter_overdub) {
                start_overdub_recording(macro_num);
                dprintf("dynamic macro: entered overdub mode for macro %d after recording\n", macro_num);
            }
        }
        
        return false;
    }
    
    // Case 3: We're recording another macro - stop that recording first
    if (macro_id > 0 && macro_id != macro_num) {
        // End the current recording
        midi_event_t *rec_start = get_macro_buffer(macro_id);
        midi_event_t **rec_end_ptr = get_macro_end_ptr(macro_id);
        
        // Check if current recording macro is in overdub mode
        bool was_in_overdub = macro_in_overdub_mode[macro_id - 1];
        
        // End recording
if (was_in_overdub) {
    end_overdub_recording_mode_aware(macro_id, true, false); // Force immediate in sample mode
} else {
            dynamic_macro_record_end(rec_start, macro_pointer, +1, rec_end_ptr, &recording_start_time);
            
            // Reset recording state
            macro_id = 0;
            stop_dynamic_macro_recording();
        }
        
        // Maybe play it back (if not skipped)
        if (!is_macro_empty && !skip_autoplay_for_macro[macro_id - 1]) {
            dynamic_macro_play(rec_start, *rec_end_ptr, +1);
            dprintf("dynamic macro: sample mode - ended recording and started playback of macro %d\n", macro_id);
        }
    }
    
    // Case 4: Macro has content - play it and stop all others
    if (!this_macro_empty) {
        // Stop all playing macros
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing) {
                // If in overdub mode, also stop recording
                if (macro_in_overdub_mode[i] && macro_id == i + 1) {
                    end_overdub_recording_deferred(i + 1);
                    dprintf("dynamic macro: stopped overdub recording for macro %d\n", i + 1);
                } else {
                    dynamic_macro_cleanup_notes_for_state(&macro_playback[i]);
                    macro_playback[i].is_playing = false;
                    macro_playback[i].current = NULL;
                    macro_in_overdub_mode[i] = false;  // Clear overdub flag
                }
            }
        }
        
        // Clear command batch
        clear_command_batch();
        
		process_pending_states_for_macro(macro_idx);
        dynamic_macro_play(macro_start, *macro_end_ptr, +1);
        dprintf("dynamic macro: sample mode playing macro %d\n", macro_num);
        
        // If overdub button is held, enter overdub mode
        if (overdub_button_held) {
            start_overdub_recording(macro_num);
            dprintf("dynamic macro: entered overdub mode for macro %d\n", macro_num);
        }
        
        return false;
    }
    
    // Case 5: Macro is empty - start recording it
    if (this_macro_empty) {
        // Stop all playing macros
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing) {
                // If in overdub mode, also stop recording
                if (macro_in_overdub_mode[i] && macro_id == i + 1) {
                    end_overdub_recording_deferred(i + 1);
                    dprintf("dynamic macro: stopped overdub recording for macro %d\n", i + 1);
                } else {
                    dynamic_macro_cleanup_notes_for_state(&macro_playback[i]);
                    macro_playback[i].is_playing = false;
                    macro_playback[i].current = NULL;
                    macro_in_overdub_mode[i] = false;  // Clear overdub flag
                }
            }
        }
        
        // Clear command batch
        clear_command_batch();
        
        // Start recording this macro
        dynamic_macro_record_start(&macro_pointer, macro_start, +1, &recording_start_time);
        macro_id = macro_num;
        snapshot_recording_settings(macro_num);  // Snapshot curve/min/max when recording starts
        setup_dynamic_macro_recording(macro_id, macro_buffer, NULL, (void**)&macro_pointer, &recording_start_time);
        dprintf("dynamic macro: sample mode started recording macro %d\n", macro_num);
        return false;
    }
    
    // If we got here, we've already handled all sample mode cases
    return false;
}

// Handle regular mode
// Handle regular mode
static bool handle_regular_mode(uint8_t macro_num, uint8_t macro_idx,
                               midi_event_t *macro_start, midi_event_t **macro_end_ptr,
                               bool this_macro_playing, bool this_macro_empty) {
    
    // FEATURE 1: Check if a stop command is queued for this macro
    if (command_exists_in_batch(CMD_STOP, macro_num)) {
        // Stop command exists - implement immediately
        if (macro_playback[macro_idx].is_playing) {
            // If in overdub mode, also stop recording
            if (macro_in_overdub_mode[macro_idx] && macro_id == macro_num) {
                end_overdub_recording_deferred(macro_num);
                dprintf("dynamic macro: immediately stopped overdub recording for macro %d\n", macro_num);
            }
            
            // Stop playback
            dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
            macro_playback[macro_idx].is_playing = false;
            macro_playback[macro_idx].current = NULL;
            if (overdub_playback[macro_idx].is_playing) {
                dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
                overdub_playback[macro_idx].is_playing = false;
                overdub_playback[macro_idx].current = NULL;
            }
            dprintf("dynamic macro: immediately stopped playback of macro %d\n", macro_num);
        } else if (macro_id == macro_num) {
            // Stop recording immediately
            midi_event_t *rec_start = get_macro_buffer(macro_id);
            midi_event_t **rec_end_ptr = get_macro_end_ptr(macro_id);
            dynamic_macro_record_end(rec_start, macro_pointer, +1, rec_end_ptr, &recording_start_time);
            macro_id = 0;
            stop_dynamic_macro_recording();
            dprintf("dynamic macro: immediately stopped recording of macro %d\n", macro_num);
        }
        
        // Remove the stop command from the batch
        remove_command_from_batch(CMD_STOP, macro_num);
        
        return false; // Command processed
    }
    
    // Check current state - count how many things are playing (macros + solo overdubs)
    uint8_t playing_count = 0;
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (is_macro_effectively_playing(i)) {
            playing_count++;
        }
        // Also count overdubs that are playing solo (without their main macro)
        else if (overdub_playback[i].is_playing) {
            playing_count++;
        }
    }

    // Special case: If we're currently recording another macro
    if (macro_id > 0 && macro_id != macro_num) {
        // We're recording another macro, and this is a different macro button
        
        // If macro_start == *macro_end_ptr, this macro is empty
        bool this_macro_empty = (macro_start == *macro_end_ptr);
        
        // Check if any macros are currently playing
        bool any_macros_playing = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing) {
                any_macros_playing = true;
                break;
            }
        }
        
        // Different behavior based on whether M2 is empty and if macros are playing
        if (this_macro_empty) {
            // M2 is empty - quick record handoff behavior
            if (any_macros_playing) {
                // Check if current recording is in overdub mode
                bool current_is_overdub = macro_in_overdub_mode[macro_id - 1];
                
                // Macros are playing - batch commands for the loop transition
                // 1. Add command to stop current recording
                add_command_to_batch(CMD_STOP, macro_id);
                
                // 2. Add command to play just recorded macro (always add it)
                if (!is_macro_empty) {
                    add_command_to_batch(CMD_PLAY, macro_id);
                    
                    // If current recording is in overdub mode, keep it that way
                    if (current_is_overdub) {
                        macro_in_overdub_mode[macro_id - 1] = true;
                    }
                }
                
                // 3. Add command to start recording the new macro
                add_command_to_batch(CMD_RECORD, macro_num);
                 
                dprintf("dynamic macro: batched commands for loop transition - stop rec %d, play %d, start rec %d\n", 
                        macro_id, macro_id, macro_num);
            } else {
                // No macros playing - do a quick record handoff immediately
                // 1. Stop current recording
                midi_event_t *rec_start = get_macro_buffer(macro_id);
                midi_event_t **rec_end_ptr = get_macro_end_ptr(macro_id);
                
                // Check if current recording is in overdub mode
                bool current_is_overdub = macro_in_overdub_mode[macro_id - 1];
                
			if (current_is_overdub) {
				end_overdub_recording_mode_aware(macro_id, true, false); // Force immediate for handoff
			} else {
				dynamic_macro_record_end(rec_start, macro_pointer, +1, rec_end_ptr, &recording_start_time);
				
				// Reset recording state
				macro_id = 0;
				stop_dynamic_macro_recording();
			}
                
                // 2. Start playback of just recorded macro (if not skipped)
                if (!is_macro_empty && !skip_autoplay_for_macro[macro_id - 1]) {
                    dynamic_macro_play(rec_start, *rec_end_ptr, +1);
                    dprintf("dynamic macro: started playback after recording macro %d\n", macro_id);
                    
                    // If current recording is in overdub mode, restart overdub
                    if (current_is_overdub) {
                        start_overdub_recording(macro_id);
                        dprintf("dynamic macro: restarted overdub mode for macro %d\n", macro_id);
                    }
                } else if (!is_macro_empty && skip_autoplay_for_macro[macro_id - 1]) {
                    dprintf("dynamic macro: skipped playback due to double-tap for macro %d\n", macro_id);
                    skip_autoplay_for_macro[macro_id - 1] = false; // Reset flag after using it
                }
                
                // 3. Immediately start recording the new macro
                macro_id = macro_num;
                macro_pointer = macro_start;
                recording_start_time = timer_read32();
                first_note_recorded = true;
				send_loop_message(loop_start_recording_cc[macro_id - 1], 127);  // ADD THIS LINE
                setup_dynamic_macro_recording(macro_id, macro_buffer, NULL, (void**)&macro_pointer, &recording_start_time);
                 
                dprintf("dynamic macro: quick record handoff to macro %d\n", macro_num);
            }
        } else {
            // M2 already has content
            if (any_macros_playing) {
                // Macros are playing - only affect M2, leave M1 recording unchanged
                bool m2_is_playing = macro_playback[macro_num - 1].is_playing;
                
                if (m2_is_playing) {
                    // M2 is playing - add command to stop it
                    add_command_to_batch(CMD_STOP, macro_num);
                    
                    // If in overdub mode, clear the flag
                    if (macro_in_overdub_mode[macro_idx]) {
                        macro_in_overdub_mode[macro_idx] = false;
                    }
                    
                     
                    dprintf("dynamic macro: batched command to stop M2 (macro %d) at loop transition\n", macro_num);
                } else {
                    // M2 is not playing - add command to play it
                    add_command_to_batch(CMD_PLAY, macro_num);
                    
                    // If overdub button is held, set flag to enter overdub
                    if (overdub_button_held) {
                        macro_in_overdub_mode[macro_idx] = true;
                        dprintf("dynamic macro: will enter overdub mode for macro %d at loop trigger\n", macro_num);
                    }
                    
                     
                    dprintf("dynamic macro: batched command to play M2 (macro %d) at loop transition\n", macro_num);
                }
            } else {
                // No macros playing - immediate handoff
                // 1. Stop current recording
                midi_event_t *rec_start = get_macro_buffer(macro_id);
                midi_event_t **rec_end_ptr = get_macro_end_ptr(macro_id);
                
                // Check if current recording is in overdub mode
                bool current_is_overdub = macro_in_overdub_mode[macro_id - 1];
                
                if (current_is_overdub) {
                    end_overdub_recording_deferred(macro_id);
                } else {
                    dynamic_macro_record_end(rec_start, macro_pointer, +1, rec_end_ptr, &recording_start_time);
                    
                    // Reset recording state
                    macro_id = 0;
                    stop_dynamic_macro_recording();
                }
                
                // 2. Start playback of just recorded macro (if not skipped)
                if (!is_macro_empty && !skip_autoplay_for_macro[macro_id - 1]) {
                    dynamic_macro_play(rec_start, *rec_end_ptr, +1);
                    dprintf("dynamic macro: started playback after recording macro %d\n", macro_id);
                    
                    // If current recording is in overdub mode, restart overdub
                    if (current_is_overdub) {
                        start_overdub_recording(macro_id);
                        dprintf("dynamic macro: restarted overdub mode for macro %d\n", macro_id);
                    }
                } else if (!is_macro_empty && skip_autoplay_for_macro[macro_id - 1]) {
                    dprintf("dynamic macro: skipped playback due to double-tap for macro %d\n", macro_id);
                    skip_autoplay_for_macro[macro_id - 1] = false; // Reset flag after using it
                }
                
                // 3. Play the existing macro M2
                dynamic_macro_play(macro_start, *macro_end_ptr, +1);
                
                // If overdub button is held, enter overdub mode
                if (overdub_button_held) {
                    start_overdub_recording(macro_num);
                    dprintf("dynamic macro: entered overdub mode for macro %d\n", macro_num);
                } else {
                    // 4. Reset recording state
                    macro_id = 0;
                    stop_dynamic_macro_recording();
                }
                
                dprintf("dynamic macro: stopped recording on M1 and started playback of M2 (macro %d)\n", macro_num);
            }
        }
        return false;
    }      

    if (!this_macro_playing && playing_count == 0) {
        // NORMAL RECORD MODE
        if (macro_id == 0 && !is_macro_primed) {
            // Check if macro already exists
            if (macro_start != *macro_end_ptr) {
                // Macro exists - play it
                overdub_mute_pending[macro_idx] = false;
                overdub_unmute_pending[macro_idx] = false;
                overdub_muted[macro_idx] = false;
                dynamic_macro_play(macro_start, *macro_end_ptr, +1);
				
			if (((unsynced_mode_active == 0 || unsynced_mode_active == 4)) && is_internal_clock_active()) {
                internal_clock_tempo_changed();
                dprintf("MIDI clock: Tempo updated when starting first loop\n");
            }    
                // If overdub button is held, enter overdub mode
                if (overdub_button_held) {
                    start_overdub_recording(macro_num);
                    dprintf("dynamic macro: entered overdub mode for macro %d\n", macro_num);
                }
            } else {
                // No macro exists - prime for recording
                dynamic_macro_record_start(&macro_pointer, macro_start, +1, &recording_start_time);
                macro_id = macro_num;
                snapshot_recording_settings(macro_num);  // Snapshot curve/min/max when recording starts
                setup_dynamic_macro_recording(macro_id, macro_buffer, NULL, (void**)&macro_pointer, &recording_start_time);

                // If overdub button is held, set flag for after recording
                if (overdub_button_held) {
                    macro_in_overdub_mode[macro_idx] = true;
                    dprintf("dynamic macro: will enter overdub mode after recording macro %d\n", macro_num);
                }
            }
        } else if (macro_id > 0 || is_macro_primed) {
            // CRUCIAL PART - don't stop recording on double-tap
            if (macro_id == macro_num && ignore_second_press[macro_idx]) {
                // This is the second press of a double-tap for the macro we're recording
                // Don't end recording, just set flag to skip autoplay at loop trigger
                dprintf("dynamic macro: ignoring second press for recording macro %d\n", macro_num);
                return false;
            }
            
            // Check if we're in overdub mode
            bool is_overdub = macro_in_overdub_mode[macro_idx] && macro_id == macro_num;
            
            if (is_overdub) {
                // End overdub recording
                end_overdub_recording_mode_aware(macro_num, false, false);
                dprintf("dynamic macro: ended overdub recording for macro %d\n", macro_num);
            } else {
                // Normal recording - stop and start playback immediately (for non-double-tap case)
                midi_event_t *rec_start = get_macro_buffer(macro_id);
                midi_event_t **rec_end_ptr = get_macro_end_ptr(macro_id);
                
                // Check if we need to enter overdub mode
                bool should_enter_overdub = macro_in_overdub_mode[macro_idx] || 
                                           (overdub_button_held && macro_id == macro_num);
                
                // End recording
                dynamic_macro_record_end(rec_start, macro_pointer, +1, rec_end_ptr, &recording_start_time);
                
                // Reset recording state
                macro_id = 0;
                stop_dynamic_macro_recording();
                
                // Start playback (if not skipped)
                if (!is_macro_empty && !skip_autoplay_for_macro[macro_id - 1]) {
                    dynamic_macro_play(rec_start, *rec_end_ptr, +1);
                    dprintf("dynamic macro: started playback after recording macro %d\n", macro_id);
                    
                    // If flag was set to enter overdub, set it up now
                    if (should_enter_overdub) {
                        start_overdub_recording(macro_num);
                        dprintf("dynamic macro: entered overdub mode for macro %d after recording\n", macro_num);
                    }
                } else if (!is_macro_empty && skip_autoplay_for_macro[macro_id - 1]) {
                    dprintf("dynamic macro: skipped playback due to double-tap for macro %d\n", macro_id);
                    skip_autoplay_for_macro[macro_id - 1] = false; // Reset flag after using it
                }
            }
        }
    } else if (!this_macro_playing && playing_count > 0) {
        overdub_muted[macro_idx] = false;
        // MULTIPLE MACROS PLAYING MODE - This is where we want batching to happen
        if (macro_id == 0 && !is_macro_primed) {
            // Check if macro already exists
            if (macro_start != *macro_end_ptr) {
                // Macro exists - add play command to batch
                overdub_mute_pending[macro_idx] = false;
                overdub_unmute_pending[macro_idx] = false;
                overdub_muted[macro_idx] = false;
                
                // FEATURE 3: First check if this command already exists
                if (!command_exists_in_batch(CMD_PLAY, macro_num)) {
                    add_command_to_batch(CMD_PLAY, macro_num);
                    
                    // If overdub button is held, set flag to enter overdub
                    if (overdub_button_held) {
                        macro_in_overdub_mode[macro_idx] = true;
                        dprintf("dynamic macro: will enter overdub mode for macro %d at loop trigger\n", macro_num);
                    }
                    
                     
                    dprintf("dynamic macro: batched play command for macro %d\n", macro_num);
                } else {
                    // Remove the play command instead of adding it
                    remove_command_from_batch(CMD_PLAY, macro_num);
                    
                    // Clear overdub flag
                    macro_in_overdub_mode[macro_idx] = false;
                    
                     
                    dprintf("dynamic macro: removed play command for macro %d\n", macro_num);
                }
            } else {
                // No macro exists - add record command to batch
                add_command_to_batch(CMD_RECORD, macro_num);
                
                // If overdub button is held, set flag for after recording
                if (overdub_button_held) {
                    macro_in_overdub_mode[macro_idx] = true;
                    dprintf("dynamic macro: will enter overdub mode after recording macro %d\n", macro_num);
                }
                
                 
                dprintf("dynamic macro: batched record command for macro %d\n", macro_num);
            }
        } else if (macro_id > 0) {
            // Another critical section - check if this is the macro we're recording
            if (macro_id == macro_num && ignore_second_press[macro_idx]) {
                // This is the second press of a double-tap for the macro we're recording
                // Don't add stop command, just set flag to skip autoplay at loop trigger
                dprintf("dynamic macro: ignoring second press for recording macro %d - will skip autoplay at loop trigger\n", macro_num);
                return false;
            }
            
            // Check if we're in overdub mode
            bool is_overdub = macro_in_overdub_mode[macro_idx] && macro_id == macro_num;
            
            if (is_overdub) {
                // We're in overdub mode - add commands to exit overdub mode
                add_command_to_batch(CMD_STOP, macro_num);
                add_command_to_batch(CMD_PLAY, macro_num);
                 
                dprintf("dynamic macro: batched commands to exit overdub for macro %d\n", macro_num);
            } else {
                // Currently recording - stop accepting new events immediately but batch the proper end
                recording_suspended[macro_id - 1] = true;
                
                // Add stop command to batch for proper end processing with correct timing
                add_command_to_batch(CMD_STOP, macro_id);
                
                // Always add play command to batch - the flag will be checked during execution
                if (!is_macro_empty) {
                    add_command_to_batch(CMD_PLAY, macro_id);
                    
                    // If overdub button is held, set flag to enter overdub
                    if (overdub_button_held && macro_id == macro_num) {
                        macro_in_overdub_mode[macro_idx] = true;
                        dprintf("dynamic macro: will enter overdub mode for macro %d at loop trigger\n", macro_num);
                    }
                }
                
                 
                dprintf("dynamic macro: suspended recording, batched stop for macro %d\n", macro_id);
            }
        }
    } else if (this_macro_playing && playing_count >= 1) {
        // Macro is already playing
        if (macro_in_overdub_mode[macro_idx]) {
            // If it's in overdub mode, schedule to exit at loop trigger
            add_command_to_batch(CMD_STOP, macro_num);
            add_command_to_batch(CMD_PLAY, macro_num);
             
            dprintf("dynamic macro: batched commands to exit overdub for macro %d\n", macro_num);
        } else if (overdub_button_held) {
            // If overdub button is held and macro isn't already in overdub, enter overdub
            start_overdub_recording(macro_num);
            dprintf("dynamic macro: entered overdub mode for macro %d\n", macro_num);
        } else {
            // THIS MACRO IS ALREADY PLAYING - add stop command to batch
            add_command_to_batch(CMD_STOP, macro_num);
             
            dprintf("dynamic macro: batched stop command for macro %d\n", macro_num);
        }
    }
    
    return false;
}

void dynamic_macro_intercept_noteon(uint8_t channel, uint8_t note, uint8_t raw_travel, uint8_t macro_id,
                                   void *macro_buffer1, void *macro_buffer2,
                                   void **macro_pointer, uint32_t *recording_start_time) {
    
    // FIRST: Always check for early overdub capture (independent of regular recording)
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (capture_early_overdub_events[i] && early_overdub_count[i] < 32) {
            early_overdub_buffer[i][early_overdub_count[i]].type = MIDI_EVENT_NOTE_ON;
            early_overdub_buffer[i][early_overdub_count[i]].channel = channel;
            early_overdub_buffer[i][early_overdub_count[i]].note = note;
            early_overdub_buffer[i][early_overdub_count[i]].raw_travel = raw_travel;
            early_overdub_buffer[i][early_overdub_count[i]].timestamp = 0; // Will be placed at loop start
            early_overdub_count[i]++;

            dprintf("early overdub: captured note-on ch:%d note:%d vel:%d for macro %d\n",
                    channel, note, raw_travel, i + 1);
            return; // Early captured, don't process as normal recording
        }
    }

    // SECOND: Check if regular recording is active and not suspended
    if (macro_id == 0 || recording_suspended[macro_id - 1]) {
        return; // No regular recording active or recording suspended
    }

    // THIRD: Route to appropriate recording system
    if (macro_in_overdub_mode[macro_id - 1]) {
        // Regular overdub recording (to temp buffer)
        dynamic_macro_record_midi_event_overdub(MIDI_EVENT_NOTE_ON, channel, note, raw_travel);
    } else {
        // Normal macro recording
        midi_event_t *macro_start = get_macro_buffer(macro_id);
        midi_event_t *macro_end = macro_start + (MACRO_BUFFER_SIZE / sizeof(midi_event_t));

        dynamic_macro_record_midi_event(macro_start, (midi_event_t**)macro_pointer,
                                       macro_end, +1,
                                       MIDI_EVENT_NOTE_ON, channel, note, raw_travel,
                                       recording_start_time, macro_id);
    }
}

void dynamic_macro_intercept_noteoff(uint8_t channel, uint8_t note, uint8_t raw_travel, uint8_t macro_id,
                                    void *macro_buffer1, void *macro_buffer2,
                                    void **macro_pointer, uint32_t *recording_start_time) {
    
    // FIRST: Always check for early overdub capture (independent of regular recording)
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (capture_early_overdub_events[i] && early_overdub_count[i] < 32) {
            early_overdub_buffer[i][early_overdub_count[i]].type = MIDI_EVENT_NOTE_OFF;
            early_overdub_buffer[i][early_overdub_count[i]].channel = channel;
            early_overdub_buffer[i][early_overdub_count[i]].note = note;
            early_overdub_buffer[i][early_overdub_count[i]].raw_travel = raw_travel;
            early_overdub_buffer[i][early_overdub_count[i]].timestamp = 0; // Will be placed at loop start
            early_overdub_count[i]++;

            dprintf("early overdub: captured note-off ch:%d note:%d vel:%d for macro %d\n",
                    channel, note, raw_travel, i + 1);
            return; // Early captured, don't process as normal recording
        }
    }

    // SECOND: Check if regular recording is active and not suspended
    if (macro_id == 0 || recording_suspended[macro_id - 1]) {
        return; // No regular recording active or recording suspended
    }

    // THIRD: Route to appropriate recording system
    if (macro_in_overdub_mode[macro_id - 1]) {
        // Regular overdub recording (to temp buffer)
        dynamic_macro_record_midi_event_overdub(MIDI_EVENT_NOTE_OFF, channel, note, raw_travel);
    } else {
        // Normal macro recording
        midi_event_t *macro_start = get_macro_buffer(macro_id);
        midi_event_t *macro_end = macro_start + (MACRO_BUFFER_SIZE / sizeof(midi_event_t));

        dynamic_macro_record_midi_event(macro_start, (midi_event_t**)macro_pointer,
                                       macro_end, +1,
                                       MIDI_EVENT_NOTE_OFF, channel, note, raw_travel,
                                       recording_start_time, macro_id);
    }
}

void dynamic_macro_intercept_cc(uint8_t channel, uint8_t cc_number, uint8_t value, uint8_t macro_id, 
                               void *macro_buffer1, void *macro_buffer2, 
                               void **macro_pointer, uint32_t *recording_start_time) {
    
    // FIRST: Always check for early overdub capture (independent of regular recording)
    // Only capture non-sustain CCs in early overdub
    if (cc_number != 0x40) { // Don't capture sustain in early overdub
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (capture_early_overdub_events[i] && early_overdub_count[i] < 32) {
                early_overdub_buffer[i][early_overdub_count[i]].type = MIDI_EVENT_CC;
                early_overdub_buffer[i][early_overdub_count[i]].channel = channel;
                early_overdub_buffer[i][early_overdub_count[i]].note = cc_number;
                early_overdub_buffer[i][early_overdub_count[i]].raw_travel = value;
                early_overdub_buffer[i][early_overdub_count[i]].timestamp = 0; // Will be placed at loop start
                early_overdub_count[i]++;
                
                dprintf("early overdub: captured CC ch:%d cc:%d val:%d for macro %d\n", 
                        channel, cc_number, value, i + 1);
                return; // Early captured, don't process as normal recording
            }
        }
    }
    
    // SECOND: Check if regular recording is active and not suspended
    if (macro_id == 0 || recording_suspended[macro_id - 1]) {
        return; // No regular recording active or recording suspended
    }
    
    // THIRD: Handle sustain pedal specially (update state but don't record)
    if (cc_number == 0x40) {
        // Just update internal state but don't record the event
        recording_sustain_active = (value >= 64);
        return;
    }
    
    // FOURTH: Route to appropriate recording system (non-sustain CCs only)
    if (macro_in_overdub_mode[macro_id - 1]) {
        // Regular overdub recording (to temp buffer)
        dynamic_macro_record_midi_event_overdub(MIDI_EVENT_CC, channel, cc_number, value);
    } else {
        // Normal macro recording
        midi_event_t *macro_start = get_macro_buffer(macro_id);
        midi_event_t *macro_end = macro_start + (MACRO_BUFFER_SIZE / sizeof(midi_event_t));
        
        dynamic_macro_record_midi_event(macro_start, (midi_event_t**)macro_pointer, 
                                       macro_end, +1, 
                                       MIDI_EVENT_CC, channel, cc_number, value, 
                                       recording_start_time, macro_id);
    }
}

// Modified matrix_scan_user_macro to handle both main and overdub playback
void matrix_scan_user_macro(void) {
    // Process all main macros
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_playback[i].is_playing) {
            dynamic_macro_play_task_for_state(&macro_playback[i]);
        }
        
        // Process overdub playback
        if (overdub_playback[i].is_playing) {
            dynamic_macro_play_task_for_state(&overdub_playback[i]);
        }
        
        // Check for long press to delete a macro
if (macro_key_held[i] && !macro_deleted[i]) {
    if (timer_elapsed(key_timers[i]) > MACRO_DELETE_THRESHOLD) {
        // Long press detected - conditional deletion based on modifier keys
        uint8_t macro_num = i + 1;
        
        if (overdub_button_held) {
            // Delete only overdubs - RESET TO FRESH MACRO STATE (no overdubs)
            if (overdub_playback[i].is_playing) {
                // Send note-offs for all overdub notes before stopping
                cleanup_notes_from_macro(macro_num + MAX_MACROS);
                
                // Now stop the playback state
                overdub_playback[i].is_playing = false;
                overdub_playback[i].current = NULL;
                overdub_playback[i].waiting_for_loop_gap = false;
            }
            
            // Clear temp overdub data AND zero the memory
            if (overdub_temp_count[i] > 0) {
                midi_event_t *temp_start = get_overdub_read_start(macro_num);
                if (temp_start != NULL) {
                    memset(temp_start, 0, overdub_temp_count[i] * sizeof(midi_event_t));
                }
            }
            overdub_temp_count[i] = 0;
            overdub_merge_pending[i] = false;
            
            // Clear overdub mode state completely
            macro_in_overdub_mode[i] = false;
            
            // Reset overdub target if this was the target
            if (overdub_target_macro == macro_num) {
                overdub_target_macro = 0;
                current_macro_id = 0;
                // Only clear macro_id if it matches this macro
                if (macro_id == macro_num) {
                    macro_id = 0;
                    macro_pointer = NULL;
                    is_macro_primed = false;
                    first_note_recorded = false;
                    is_macro_empty = true;
                    recording_start_time = 0;
                    recording_sustain_active = false;
                }
                stop_dynamic_macro_recording();
            }
            
            // Clear any pending overdub operations
            overdub_mute_pending[i] = false;
            overdub_unmute_pending[i] = false;
            
            // === NEW: MACRO-SPECIFIC RESET FOR OVERDUB-ONLY DELETION ===
            recording_suspended[i] = false;  // Clear recording suspension flag
            overdub_pause_timestamps[i] = 0; // Clear overdub pause position
            
            // Clear preroll if this macro was collecting it
            if (collecting_preroll && macro_id == macro_num) {
                collecting_preroll = false;
                preroll_buffer_count = 0;
                preroll_buffer_index = 0;
                preroll_start_time = 0;
                memset(preroll_buffer, 0, sizeof(preroll_buffer));
                dprintf("dynamic macro: cleared preroll system for overdub deletion of macro %d\n", macro_num);
            }
            
            if (overdub_buffers[i] != NULL) {
                // ZERO OUT THE OVERDUB MEMORY CONTENT
                uint32_t overdub_events_allocated = overdub_buffer_sizes[i];
                memset(overdub_buffers[i], 0, overdub_events_allocated * sizeof(midi_event_t));
                
                // Reset end pointer to start pointer (making it empty but keeping allocation)
                overdub_buffer_ends[i] = overdub_buffers[i];
                
                // Keep overdub_buffers[i] and overdub_buffer_sizes[i] unchanged (match fresh macro allocation)
                // Reset muted state to initial (unmuted)
                overdub_muted[i] = false;
                
                // COMPLETE overdub playback state reset to match fresh macro state
                overdub_playback[i].buffer_start = overdub_buffers[i];
                overdub_playback[i].loop_length = macro_playback[i].loop_length;
                overdub_playback[i].loop_gap_time = macro_playback[i].loop_gap_time;
                overdub_playback[i].current = NULL;
                overdub_playback[i].end = overdub_buffer_ends[i];
                overdub_playback[i].is_playing = false;
                overdub_playback[i].waiting_for_loop_gap = false;
                overdub_playback[i].direction = +1;
                overdub_playback[i].timer = 0;
                overdub_playback[i].next_event_time = 0;
                macro_main_muted[i] = false;
				capture_early_overdub_events[i] = false;
				early_overdub_count[i] = 0;
				memset(early_overdub_buffer[i], 0, sizeof(early_overdub_buffer[i]));	
				overdub_independent_loop_length[i] = 0;
				overdub_independent_timer[i] = 0;
				overdub_independent_gap_time[i] = 0;
				overdub_independent_start_time[i] = 0;
				overdub_independent_waiting_for_gap[i] = false;
				overdub_independent_suspended[i] = false;
				overdub_independent_suspension_time[i] = 0;
				
            } else {
                // No overdub buffer was allocated - this shouldn't happen for a recorded macro
                dprintf("WARNING: No overdub buffer found for macro %d during overdub deletion\n", macro_num);
            }
            
            force_clear_all_live_notes();
            // Single blink to confirm overdub deletion
             
                        send_loop_message(overdub_clear_cc[macro_num - 1], 127);  // ADD THIS LINE

            dprintf("dynamic macro: RESET OVERDUBS - macro %d restored to fresh macro state (memory cleared)\n", macro_num);
        } else {
            // Delete everything - COMPLETE RESET TO DEVICE STARTUP STATE
            
            // Stop main macro
            if (macro_playback[i].is_playing) {
                dynamic_macro_cleanup_notes_for_state(&macro_playback[i]);
                macro_playback[i].is_playing = false;
                macro_playback[i].current = NULL;
            }
            
            // Stop overdub
            if (overdub_playback[i].is_playing) {
                dynamic_macro_cleanup_notes_for_state(&overdub_playback[i]);
                overdub_playback[i].is_playing = false;
                overdub_playback[i].current = NULL;
            }
            
            // Clear temp overdub data AND zero the memory
            if (overdub_temp_count[i] > 0) {
                midi_event_t *temp_start = get_overdub_read_start(macro_num);
                if (temp_start != NULL) {
                    memset(temp_start, 0, overdub_temp_count[i] * sizeof(midi_event_t));
                }
            }
            overdub_temp_count[i] = 0;
            overdub_merge_pending[i] = false;
            
            // ZERO OUT THE MAIN MACRO MEMORY CONTENT
            midi_event_t *macro_start = get_macro_buffer(macro_num);
            midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
            
            // Calculate how much memory to clear (entire macro buffer)
            uint32_t macro_buffer_events = MACRO_BUFFER_SIZE / sizeof(midi_event_t);
            memset(macro_start, 0, macro_buffer_events * sizeof(midi_event_t));
            
            // Set macro end pointer to start (making it empty)
            *macro_end_ptr = macro_start;
            
            // Clear overdub buffer references (permanent overdub area)
            overdub_buffers[i] = NULL;
            overdub_buffer_ends[i] = NULL;
            overdub_buffer_sizes[i] = 0;
            overdub_muted[i] = false;
            
            // COMPLETE PLAYBACK STATE RESET (matching device startup)
            macro_playback[i].current = NULL;
            macro_playback[i].end = NULL;
            macro_playback[i].buffer_start = NULL;
            macro_playback[i].timer = 0;
            macro_playback[i].direction = +1;
            macro_playback[i].is_playing = false;
            macro_playback[i].waiting_for_loop_gap = false;
            macro_playback[i].next_event_time = 0;
            macro_playback[i].loop_gap_time = 0;
            macro_playback[i].loop_length = 0;
            macro_main_muted[i] = false;
            
            // COMPLETE OVERDUB PLAYBACK STATE RESET
            overdub_playback[i].current = NULL;
            overdub_playback[i].end = NULL;
            overdub_playback[i].buffer_start = NULL;
            overdub_playback[i].timer = 0;
            overdub_playback[i].direction = +1;
            overdub_playback[i].is_playing = false;
            overdub_playback[i].waiting_for_loop_gap = false;
            overdub_playback[i].next_event_time = 0;
            overdub_playback[i].loop_gap_time = 0;
            overdub_playback[i].loop_length = 0;
            macro_manual_speed[i] = 1.0f;      
            macro_speed_factor[i] = 1.0f;      
			capture_early_overdub_events[i] = false;
			early_overdub_count[i] = 0;
			memset(early_overdub_buffer[i], 0, sizeof(early_overdub_buffer[i]));	
			overdub_independent_loop_length[i] = 0;
			overdub_independent_timer[i] = 0;
			overdub_independent_gap_time[i] = 0;
			overdub_independent_start_time[i] = 0;
			overdub_independent_waiting_for_gap[i] = false;
			overdub_independent_suspended[i] = false;
			overdub_independent_suspension_time[i] = 0;
            
            // === NEW: COMPLETE MACRO-SPECIFIC RESET ===
            recording_suspended[i] = false;     // Clear recording suspension flag
            pause_timestamps[i] = 0;            // Clear pause position
            overdub_pause_timestamps[i] = 0;    // Clear overdub pause position  
            macro_speed_before_pause[i] = 1.0f; // Reset speed before pause
            
            // Clear preroll if this macro was collecting it
            if (collecting_preroll && macro_id == macro_num) {
                collecting_preroll = false;
                preroll_buffer_count = 0;
                preroll_buffer_index = 0;
                preroll_start_time = 0;
                memset(preroll_buffer, 0, sizeof(preroll_buffer));
                dprintf("dynamic macro: cleared preroll system for deleted macro %d\n", macro_num);
            }
            
            // Reset global recording state if this was the recording macro
            if (macro_id == macro_num) {
                macro_id = 0;
                current_macro_id = 0;
                macro_pointer = NULL;
                is_macro_primed = false;
                first_note_recorded = false;
                is_macro_empty = true;
                recording_start_time = 0;
                recording_sustain_active = false;
                stop_dynamic_macro_recording();
                dprintf("dynamic macro: cleared global recording state for deleted macro %d\n", macro_num);
            }
            
            // Reset overdub target if this was the target
            if (overdub_target_macro == macro_num) {
                overdub_target_macro = 0;
                current_macro_id = 0;
                // Note: macro_id might still be valid for a different macro, so don't clear it here
                // unless it matches this macro (handled above)
                if (macro_id == macro_num) {
                    macro_id = 0;
                    stop_dynamic_macro_recording();
                }
                dprintf("dynamic macro: cleared overdub target for deleted macro %d\n", macro_num);
            }
            
            // If this was the BPM source macro, clear the source and reset BPM
            if (bpm_source_macro == macro_num) {
                bpm_source_macro = 0;
                current_bpm = 0;
                original_system_bpm = 0;
                dprintf("dynamic macro: cleared BPM source, reset BPM to 0 for deleted macro %d\n", macro_num);
            }
            
            macro_recording_bpm[i] = 0;
            macro_has_content[i] = false;
            macro_manual_speed[i] = 1.0f;
            
            // Reset ALL transformation values to device startup state
            reset_macro_transformations(macro_num);
            
            // RESET ADDITIONAL MACRO-SPECIFIC FLAGS (matching device startup)
            skip_autoplay_for_macro[i] = false;
            ignore_second_press[i] = false; 
            last_macro_press_time[i] = 0;
            macro_deleted[i] = false;  // Reset this too (will be set true at end of function)
            
            // Clear overdub mode flag
            macro_in_overdub_mode[i] = false;
            
            // Clear any pending overdub operations  
            overdub_mute_pending[i] = false;
            overdub_unmute_pending[i] = false;
            
            // Reset key press tracking
            key_timers[i] = 0;
            macro_key_held[i] = false;  // This will be overridden but ensure consistency
            
            force_clear_all_live_notes();
            
            // Clear any queued commands for this macro
            for (uint8_t j = 0; j < command_batch_count; j++) {
                if (command_batch[j].macro_id == macro_num) {
                    for (uint8_t k = j; k < command_batch_count - 1; k++) {
                        command_batch[k] = command_batch[k + 1];
                    }
                    command_batch_count--;
                    j--;
                }
            }
            
            dprintf("dynamic macro: COMPLETE RESET - macro %d restored to device startup state (memory cleared)\n", macro_num);
			send_loop_message(loop_clear_cc[macro_num - 1], 127);  // ADD THIS LINE
            send_loop_message(overdub_clear_cc[macro_num - 1], 127);  // ALSO SEND OVERDUB CLEAR
        }
        
        macro_deleted[i] = true;
			}
		}
	}
}

// Returns true if any macro is currently playing
bool dynamic_macro_is_playing(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_playback[i].is_playing) {
            return true;
        }
    }
    return false;
}

// Additional helper function to check if a specific macro is playing
bool dynamic_macro_is_playing_slot(uint8_t slot) {
    if (slot >= 1 && slot <= MAX_MACROS) {
        return macro_playback[slot - 1].is_playing;
    }
    return false;
}

void dynamic_macro_handle_loop_trigger(void) {
    // If we were collecting preroll and a loop trigger starts recording a macro,
    // make sure to include the preroll events
    if (is_macro_primed && collecting_preroll) {
        for (uint8_t i = 0; i < command_batch_count; i++) {
            if (command_batch[i].command_type == CMD_RECORD && !command_batch[i].processed) {
                // This will include the preroll events
                dynamic_macro_actual_start(&recording_start_time);
                break;
            }
        }
    }
    
    // Original loop trigger handling
    check_loop_trigger();
}

// Helper function to check if any modulations are active for a macro
bool has_any_modulation(uint8_t macro_idx) {
    return (macro_transpose[macro_idx] != 0 ||
            macro_channel_absolute[macro_idx] != 0 ||
            macro_channel_offset[macro_idx] != 0 ||
            macro_velocity_absolute[macro_idx] != 0 ||
            macro_velocity_offset[macro_idx] != 0); 
}

// Helper function to generate header with octave doubler asterisks (21 chars exactly)
// Helper function to generate header with octave doubler asterisks (21 chars exactly)
void get_macro_header_with_octave_indicators(char* header_str, bool flash_state) {
    strcpy(header_str, ""); // Initialize empty
    
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        char macro_str[6]; // Buffer for each macro column
        uint8_t macro_num = i + 1;
        
        // Get current and target octave doubler states
        int8_t current_value = macro_octave_doubler[i];
        int8_t target_value = macro_octave_doubler_target[i];
        bool is_pending = macro_octave_doubler_pending[i];
        
        // Determine which value to display based on flash state
        int8_t display_value;
        bool show_spaces = false;
        
        if (is_pending) {
            if (flash_state) {
                // Flash ON: show target state
                display_value = target_value;
            } else {
                // Flash OFF: show plain number, EXCEPT when going to 0 (show spaces)
                if (target_value == 0) {
                    show_spaces = true;
                } else {
                    display_value = 0; // Force plain number display
                }
            }
        } else {
            // Not pending: show current state
            display_value = current_value;
        }
        
        // Generate the macro column string to match original spacing
        if (macro_num == 1) {
            // Macro 1: " 1  " format (4 characters)
            if (show_spaces) {
                strcpy(macro_str, "    ");
            } else if (display_value == 0) {
                strcpy(macro_str, " 1  ");
            } else if (display_value == -12) {
                strcpy(macro_str, "*1  ");
            } else if (display_value == 12) {
                strcpy(macro_str, " 1* ");
            } else if (display_value == 24) {
                strcpy(macro_str, " 1**");
            }
        } else if (macro_num == 4) {
            // Macro 4: "  4 " format (4 characters)
            if (show_spaces) {
                strcpy(macro_str, "    ");
            } else if (display_value == 0) {
                strcpy(macro_str, "  4 ");
            } else if (display_value == -12) {
                strcpy(macro_str, " *4 ");
            } else if (display_value == 12) {
                strcpy(macro_str, "  4*");
            } else if (display_value == 24) {
                strcpy(macro_str, " 4**");
            }
        } else {
            // Macros 2 and 3: "  2  " format (5 characters)
            if (show_spaces) {
                strcpy(macro_str, "     ");
            } else if (display_value == 0) {
                strcpy(macro_str, (macro_num == 2) ? "  2  " : "  3  ");
            } else if (display_value == -12) {
                strcpy(macro_str, (macro_num == 2) ? " *2  " : " *3  ");
            } else if (display_value == 12) {
                strcpy(macro_str, (macro_num == 2) ? "  2* " : "  3* ");
            } else if (display_value == 24) {
                strcpy(macro_str, (macro_num == 2) ? "  2**" : "  3**");
            }
        }
        
        // Add to header string with single "|" separator to fit 21-char limit
        if (i == 0) {
            strcpy(header_str, macro_str);
        } else {
            strcat(header_str, "|");  // Single "|" separator
            strcat(header_str, macro_str);
        }
    }
}

void get_combined_channel_string(uint8_t macro_idx, char* channel_str) {
    uint8_t absolute = macro_channel_absolute[macro_idx];
    int8_t offset = macro_channel_offset[macro_idx];
    
    if (absolute != 0) {
        // Calculate final channel: (absolute - 1) + offset, then wrap and convert back to 1-16 display
        int16_t final_channel = (int16_t)(absolute - 1) + offset;
        
        // Wrap around MIDI channel range (0-15)
        while (final_channel < 0) {
            final_channel += 16;
        }
        while (final_channel > 15) {
            final_channel -= 16;
        }
        
        // Convert back to 1-16 for display - absolute values can show full number
        int display_channel = final_channel + 1;
        channel_str[0] = 'C';
        if (display_channel < 10) {
            channel_str[1] = ' ';
            channel_str[2] = ' ';
            channel_str[3] = '0' + display_channel;
        } else {
            channel_str[1] = ' ';
            channel_str[2] = '1';
            channel_str[3] = '0' + (display_channel - 10);
        }
    } else if (offset != 0) {
        // Only offset is active - show proper +/- format up to ±99
        channel_str[0] = 'C';
        
        // Clamp display to ±99
        int display_offset = offset;
        if (display_offset > 99) display_offset = 99;
        if (display_offset < -99) display_offset = -99;
        
        if (display_offset > 0) {
            if (display_offset < 10) {
                channel_str[1] = ' ';
                channel_str[2] = '+';
                channel_str[3] = '0' + display_offset;
            } else {
                channel_str[1] = '+';
                channel_str[2] = '0' + (display_offset / 10);
                channel_str[3] = '0' + (display_offset % 10);
            }
        } else {
            if (display_offset > -10) {
                channel_str[1] = ' ';
                channel_str[2] = '-';
                channel_str[3] = '0' + (-display_offset);
            } else {
                channel_str[1] = '-';
                channel_str[2] = '0' + ((-display_offset) / 10);
                channel_str[3] = '0' + ((-display_offset) % 10);
            }
        }
    } else {
        // No modulation - show spaces
        strcpy(channel_str, "    ");
    }
    channel_str[4] = '\0';
}

// UPDATED: Helper function to calculate combined velocity effect (4 characters)
void get_combined_velocity_string(uint8_t macro_idx, char* velocity_str) {
    uint8_t absolute = macro_velocity_absolute[macro_idx];
    int8_t offset = macro_velocity_offset[macro_idx];
    
    if (absolute != 0) {
        // Calculate final velocity: absolute + offset, clamped 0-127
        int16_t final_velocity = (int16_t)absolute + offset;
        
        // Clamp to valid MIDI velocity range
        if (final_velocity < 0) {
            final_velocity = 0;
        } else if (final_velocity > 127) {
            final_velocity = 127;
        }
        
        // Show absolute values up to 127
        velocity_str[0] = 'V';
        if (final_velocity < 10) {
            velocity_str[1] = ' ';
            velocity_str[2] = ' ';
            velocity_str[3] = '0' + final_velocity;
        } else if (final_velocity < 100) {
            velocity_str[1] = ' ';
            velocity_str[2] = '0' + (final_velocity / 10);
            velocity_str[3] = '0' + (final_velocity % 10);
        } else {
            velocity_str[1] = '1';
            velocity_str[2] = '0' + ((final_velocity - 100) / 10);
            velocity_str[3] = '0' + (final_velocity % 10);
        }
    } else if (offset != 0) {
        // Only offset is active - show proper +/- format up to ±99
        velocity_str[0] = 'V';
        
        // Clamp display to ±99
        int display_offset = offset;
        if (display_offset > 99) display_offset = 99;
        if (display_offset < -99) display_offset = -99;
        
        if (display_offset > 0) {
            if (display_offset < 10) {
                velocity_str[1] = ' ';
                velocity_str[2] = '+';
                velocity_str[3] = '0' + display_offset;
            } else {
                velocity_str[1] = '+';
                velocity_str[2] = '0' + (display_offset / 10);
                velocity_str[3] = '0' + (display_offset % 10);
            }
        } else {
            if (display_offset > -10) {
                velocity_str[1] = ' ';
                velocity_str[2] = '-';
                velocity_str[3] = '0' + (-display_offset);
            } else {
                velocity_str[1] = '-';
                velocity_str[2] = '0' + ((-display_offset) / 10);
                velocity_str[3] = '0' + ((-display_offset) % 10);
            }
        }
    } else {
        // No modulation - show spaces
        strcpy(velocity_str, "    ");
    }
    velocity_str[4] = '\0';
}

// Add new function to get overdub timer countdown (add near other timer functions)
void get_overdub_timer_string(uint8_t macro_idx, char* timer_str) {
    // Only show timer if in advanced mode and overdub is playing with independent timing
    if (!overdub_advanced_mode || !overdub_playback[macro_idx].is_playing || 
        overdub_independent_loop_length[macro_idx] == 0) {
        strcpy(timer_str, "   ");
        return;
    }
    
    uint32_t overdub_loop_length = overdub_independent_loop_length[macro_idx];
    uint32_t overdub_position;
    
    // Get speed factor for this macro
    float speed_factor = macro_speed_factor[macro_idx];
    
    if (global_playback_paused) {
        // When paused, use the stored pause position (already in loop timeline)
        overdub_position = overdub_pause_timestamps[macro_idx];
        dprintf("dynamic macro: using stored overdub pause position %lu ms for timer calculation\n", overdub_position);
    } else {
        // Normal operation - calculate current position using independent timer
        uint32_t current_time = timer_read32();
        uint32_t elapsed = current_time - overdub_independent_timer[macro_idx];
        
        // Calculate speed-adjusted position in overdub loop timeline
        uint32_t speed_adjusted_elapsed = (uint32_t)(elapsed * speed_factor);
        overdub_position = speed_adjusted_elapsed % overdub_loop_length;
    }
    
    // Calculate time remaining in overdub loop timeline
    uint32_t overdub_time_remaining = overdub_loop_length - overdub_position;
    
    // Convert to real-world time using speed factor
    uint32_t real_time_remaining;
    if (speed_factor > 0.0f) {
        real_time_remaining = (uint32_t)(overdub_time_remaining / speed_factor);
    } else {
        real_time_remaining = overdub_time_remaining; // Fallback for invalid speed
    }
    
    // Convert to seconds (timer_read32 returns milliseconds)
    uint32_t seconds_remaining = real_time_remaining / 1000;
    uint32_t tenths_remaining = (real_time_remaining % 1000) / 100;
    
    // Clamp values to prevent format overflow
    if (seconds_remaining >= 99) {
        strcpy(timer_str, "99+");
    } else if (seconds_remaining < 10) {
        // Show X.Y format for less than 10 seconds
        timer_str[0] = '0' + (char)(seconds_remaining % 10);
        timer_str[1] = '.';
        timer_str[2] = '0' + (char)(tenths_remaining % 10);
        timer_str[3] = '\0';
    } else {
        // Show XX format for 10-99 seconds  
        timer_str[0] = '0' + (char)(seconds_remaining / 10);
        timer_str[1] = '0' + (char)(seconds_remaining % 10);
        timer_str[2] = ' '; // Pad with space
        timer_str[3] = '\0';
    }
}

// MODIFIED: render_interface function
void render_interface(uint8_t x, uint8_t y) {
    // Update flash state for queued commands and octave doubler pending changes
    uint32_t current_time = timer_read32();
    if (current_time - last_flash_time > FLASH_INTERVAL_MS) {
        flash_state = !flash_state;
        last_flash_time = current_time;
    }
    
    char display_line[32]; // Buffer for display lines
    
    // Row 1: UNCHANGED - Dynamic Header with octave doubler indicators (19 chars max)
    oled_set_cursor(x, y);
    get_macro_header_with_octave_indicators(display_line, flash_state);
    oled_write(display_line, false);
    
    // Row 2: UNCHANGED - Current status (21 chars exactly)
    oled_set_cursor(x, y + 1);
    strcpy(display_line, "");
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        char status[4];  // Keep exactly 3 chars + null
        get_macro_status_string(i, status);
        
        if (i == 0) {
            strcpy(display_line, status);
        } else {
            strcat(display_line, " | ");
            strcat(display_line, status);
        }
    }
    oled_write(display_line, false);
    
    // Row 3: UNCHANGED - Queued commands (21 chars exactly)
    oled_set_cursor(x, y + 2);
    strcpy(display_line, "");
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        char cmd[4];  // Keep exactly 3 chars + null
        bool should_flash;
        get_queued_command_string(i, cmd, &should_flash);
        
        if (should_flash && !flash_state) {
            strcpy(cmd, "   ");
        }
        
        if (i == 0) {
            strcpy(display_line, cmd);
        } else {
            strcat(display_line, " | ");
            strcat(display_line, cmd);
        }
    }
    oled_write(display_line, false);
    
    if (overdub_advanced_mode) {
        // ADVANCED MODE: Swap rows 4 and 5, add overdub timers, remove modulations
        
        // Row 4: Loop countdown timers (swapped from row 5)
        oled_set_cursor(x, y + 3);
        strcpy(display_line, "");
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            char timer[4];  // Keep exactly 3 chars + null
            get_loop_timer_string(i, timer);
            
            if (i == 0) {
                strcpy(display_line, timer);
            } else {
                strcat(display_line, " | ");
                strcat(display_line, timer);
            }
        }
        oled_write(display_line, false);
        
        // Row 5: Overdub status (swapped from row 4)
        oled_set_cursor(x, y + 4);
        strcpy(display_line, "");
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            char overdub[4];  // Keep exactly 3 chars + null
            
            // Check if we're queuing overdub start (from ending recording)
            bool queuing_overdub_start = false;
            if (macro_in_overdub_mode[i]) {
                // Check if there's a CMD_STOP queued for this macro
                for (uint8_t j = 0; j < command_batch_count; j++) {
                    if (command_batch[j].macro_id == (i + 1) && 
                        command_batch[j].command_type == CMD_STOP && 
                        !command_batch[j].processed) {
                        queuing_overdub_start = true;
                        break;
                    }
                }
            }
            
            if (queuing_overdub_start) {
                strcpy(overdub, "DUB");
                if (!flash_state) {
                    strcpy(overdub, "   ");
                }
            } else if (overdub_mute_pending[i]) {
                strcpy(overdub, "MUT");
                if (!flash_state) {
                    strcpy(overdub, "   ");
                }
            } else if (overdub_unmute_pending[i]) {
                strcpy(overdub, "PLY");
                // Only flash if overdub is currently muted (meaningful state change)
                if (!flash_state && overdub_muted[i]) {
                    strcpy(overdub, "   ");
                }
            } else {
                get_overdub_status_string(i, overdub);
            }
            
            if (i == 0) {
                strcpy(display_line, overdub);
            } else {
                strcat(display_line, " | ");
                strcat(display_line, overdub);
            }
        }
        oled_write(display_line, false);
        
        // Row 6: NEW - Overdub countdown timers (21 chars exactly)
        oled_set_cursor(x, y + 5);
        strcpy(display_line, "");
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            char overdub_timer[4];  // Keep exactly 3 chars + null
            get_overdub_timer_string(i, overdub_timer);
            
            if (i == 0) {
                strcpy(display_line, overdub_timer);
            } else {
                strcat(display_line, " | ");
                strcat(display_line, overdub_timer);
            }
        }
        oled_write(display_line, false);
        
        // Rows 7-8: Clear (no modulations in advanced mode)
        oled_set_cursor(x, y + 6);
        oled_write("                     ", false);
        
        oled_set_cursor(x, y + 7);
        oled_write("                     ", false);
        
    } else {
        // ORIGINAL MODE: Keep existing layout
        
        // Row 4: Overdub status (original position)
        oled_set_cursor(x, y + 3);
        strcpy(display_line, "");
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            char overdub[4];  // Keep exactly 3 chars + null
            
            // Check if we're queuing overdub start (from ending recording)
            bool queuing_overdub_start = false;
            if (macro_in_overdub_mode[i]) {
                // Check if there's a CMD_STOP queued for this macro
                for (uint8_t j = 0; j < command_batch_count; j++) {
                    if (command_batch[j].macro_id == (i + 1) && 
                        command_batch[j].command_type == CMD_STOP && 
                        !command_batch[j].processed) {
                        queuing_overdub_start = true;
                        break;
                    }
                }
            }
            
            if (queuing_overdub_start) {
                strcpy(overdub, "DUB");
                if (!flash_state) {
                    strcpy(overdub, "   ");
                }
            } else if (overdub_mute_pending[i]) {
                strcpy(overdub, "MUT");
                if (!flash_state) {
                    strcpy(overdub, "   ");
                }
            } else if (overdub_unmute_pending[i]) {
                strcpy(overdub, "PLY");
                // Only flash if overdub is currently muted (meaningful state change)
                if (!flash_state && overdub_muted[i]) {
                    strcpy(overdub, "   ");
                }
            } else {
                get_overdub_status_string(i, overdub);
            }
            
            if (i == 0) {
                strcpy(display_line, overdub);
            } else {
                strcat(display_line, " | ");
                strcat(display_line, overdub);
            }
        }
        oled_write(display_line, false);
        
        // Row 5: Loop countdown timers (original position)
        oled_set_cursor(x, y + 4);
        strcpy(display_line, "");
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            char timer[4];  // Keep exactly 3 chars + null
            get_loop_timer_string(i, timer);
            
            if (i == 0) {
                strcpy(display_line, timer);
            } else {
                strcat(display_line, " | ");
                strcat(display_line, timer);
            }
        }
        oled_write(display_line, false);
        
        // Rows 6-8: Modulation rows (original behavior)
        bool any_modulations = false;
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (has_any_modulation(i)) {
                any_modulations = true;
                break;
            }
        }
        
        if (any_modulations) {
            // Row 6: Transpose values (19 chars: "T +5|T+12|T -3|    ")
            oled_set_cursor(x, y + 5);
            strcpy(display_line, "");
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                char transpose[5]; // 4 chars + null
                int8_t t_val = macro_transpose[i];
                
                if (t_val == 0) {
                    strcpy(transpose, "    ");
                } else {
                    transpose[0] = 'T';
                    
                    int display_val = t_val;
                    if (display_val > 99) display_val = 99;
                    if (display_val < -99) display_val = -99;
                    
                    if (display_val > 0) {
                        if (display_val < 10) {
                            transpose[1] = ' ';
                            transpose[2] = '+';
                            transpose[3] = '0' + display_val;
                        } else {
                            transpose[1] = '+';
                            transpose[2] = '0' + (display_val / 10);
                            transpose[3] = '0' + (display_val % 10);
                        }
                    } else {
                        if (display_val > -10) {
                            transpose[1] = ' ';
                            transpose[2] = '-';
                            transpose[3] = '0' + (-display_val);
                        } else {
                            transpose[1] = '-';
                            transpose[2] = '0' + ((-display_val) / 10);
                            transpose[3] = '0' + ((-display_val) % 10);
                        }
                    }
                }
                transpose[4] = '\0';
                
                if (i == 0) {
                    strcpy(display_line, transpose);
                } else if (i == 1) {
                    strcat(display_line, "|");   // No space after column 1
                    strcat(display_line, transpose);
                } else {
                    strcat(display_line, " |");  // Space + pipe for columns 2 & 3
                    strcat(display_line, transpose);
                }
            }
            oled_write(display_line, false);
            
            // Row 7: Channel values (19 chars: "C +8|C+16|C -2|C  14")
            oled_set_cursor(x, y + 6);
            strcpy(display_line, "");
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                char channel[5]; // 4 chars + null
                get_combined_channel_string(i, channel);
                
                if (i == 0) {
                    strcpy(display_line, channel);
                } else if (i == 1) {
                    strcat(display_line, "|");   // No space after column 1
                    strcat(display_line, channel);
                } else {
                    strcat(display_line, " |");  // Space + pipe for columns 2 & 3
                    strcat(display_line, channel);
                }
            }
            oled_write(display_line, false);
            
            // Row 8: Velocity values (19 chars: "V +4|V+25|V -8|V127")
            oled_set_cursor(x, y + 7);
            strcpy(display_line, "");
            for (uint8_t i = 0; i < MAX_MACROS; i++) {
                char velocity[5]; // 4 chars + null
                get_combined_velocity_string(i, velocity);
                
                if (i == 0) {
                    strcpy(display_line, velocity);
                } else if (i == 1) {
                    strcat(display_line, "|");   // No space after column 1
                    strcat(display_line, velocity);
                } else {
                    strcat(display_line, " |");  // Space + pipe for columns 2 & 3
                    strcat(display_line, velocity);
                }
            }
            oled_write(display_line, false);
        } else {
            // Clear modulation rows when no modulations are active
            oled_set_cursor(x, y + 5);
            oled_write("                     ", false);
            
            oled_set_cursor(x, y + 6);
            oled_write("                     ", false);
            
            oled_set_cursor(x, y + 7);
            oled_write("                     ", false);
        }
    }
    
    static const char PROGMEM black_endbar[2] = {0x00, 0x00};

    // Clear Luna's rightmost graphics on rows 8-15
    for (uint8_t row = 8; row <= 15; row++) {
        oled_set_cursor(21, row);
        oled_write_raw_P(black_endbar, 2);   // Clear the endbar area
    }
}

void get_macro_status_string(uint8_t macro_idx, char* status_str) {
    uint8_t macro_num = macro_idx + 1;
    
    // Check if this macro is currently being recorded
    if (macro_id == macro_num && !macro_in_overdub_mode[macro_idx]) {
        strcpy(status_str, "REC");
        return;
    }
	
    // Check if macro is playing but muted (new mute mode)
    if (macro_playback[macro_idx].is_playing && macro_main_muted[macro_idx]) {
        strcpy(status_str, "MUT");
        return;
    }
    
    // Check if macro is playing (and not muted)
    if (macro_playback[macro_idx].is_playing) {
        // Show speed factor if not at normal speed, otherwise show PLY
        if (macro_speed_factor[macro_idx] != 1.0f) {
            if (macro_speed_factor[macro_idx] == 0.5f) {
                strcpy(status_str, ".50");
            } else if (macro_speed_factor[macro_idx] == 0.25f) {
                strcpy(status_str, ".25");
            } else if (macro_speed_factor[macro_idx] == 2.0f) {
                strcpy(status_str, "2.0");
            } else if (macro_speed_factor[macro_idx] == 1.5f) {
                strcpy(status_str, "1.5");
            } else if (macro_speed_factor[macro_idx] == 0.75f) {
                strcpy(status_str, ".75");
            } else {
                // Fallback for any other speed - just show PLY
                strcpy(status_str, "PLY");
            }
        } else {
            strcpy(status_str, "PLY");
        }
        return;
    }
    
    // Check if macro exists but is not playing
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
    if (macro_start != NULL && macro_end_ptr != NULL && macro_start != *macro_end_ptr) {
        strcpy(status_str, "MUT"); // Macro exists but is stopped
        return;
    }
    
    // No activity and no macro exists
    strcpy(status_str, " - ");
}

// Get queued command string (PLY/REC/END/MUT)
void get_queued_command_string(uint8_t macro_idx, char* cmd_str, bool* should_flash) {
    uint8_t macro_num = macro_idx + 1;
    *should_flash = false;
    
    // Check command batch for this macro (original logic)
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].macro_id == macro_num && !command_batch[i].processed) {
            *should_flash = true;
            
            switch (command_batch[i].command_type) {
				case CMD_STOP:
					// Check if we're entering overdub mode (special case)
					if (macro_in_overdub_mode[macro_idx]) {
						// Ending recording and entering overdub - show what main will do
						if (skip_autoplay_for_macro[macro_idx]) {
							strcpy(cmd_str, "MUT");  // Will be muted due to double-tap
						} else {
							strcpy(cmd_str, "PLY");  // Will play normally
						}
					} else if (macro_playback[macro_idx].is_playing) {
						strcpy(cmd_str, "MUT");
					} else {
						strcpy(cmd_str, "END");
					}
					return;
                case CMD_PLAY:
                    strcpy(cmd_str, "PLY");
                    return;
                case CMD_RECORD:
                    strcpy(cmd_str, "REC");
                    return;
                case CMD_PLAY_OVERDUB_ONLY:
                    strcpy(cmd_str, "SOL"); // Solo overdub
                    return;
                default:
                    break;
            }
        }
    }
    
    // No queued commands
    strcpy(cmd_str, "   ");
}

// Get overdub status (DUB/PLY/SOL/MUT or blank)
void get_overdub_status_string(uint8_t macro_idx, char* overdub_str) {
    uint8_t macro_num = macro_idx + 1;
    
    // NEW: Check if actively recording overdub (show DUB on fourth row)
    if (macro_in_overdub_mode[macro_idx] && overdub_target_macro == macro_num) {
        strcpy(overdub_str, "DUB");
        return;
    }
    
    // First check if there's a pending overdub merge
    if (overdub_merge_pending[macro_idx]) {
        // Show what the status will be after merge completes
        if (overdub_muted[macro_idx]) {
            strcpy(overdub_str, "MUT"); // Will be muted when merge completes
        } else {
            strcpy(overdub_str, "PLY"); // Will play when merge completes
        }
        return;
    }
    
    // Check if overdub exists for this macro
    if (overdub_buffers[macro_idx] == NULL || 
        overdub_buffer_ends[macro_idx] == overdub_buffers[macro_idx]) {
        strcpy(overdub_str, "   "); // No overdub content
        return;
    }
    
    // Check if overdub is playing
    if (overdub_playback[macro_idx].is_playing) {
        // Check if main macro is also playing
        if (macro_playback[macro_idx].is_playing) {
            strcpy(overdub_str, "PLY"); // Playing with main macro
        } else {
            strcpy(overdub_str, "PLY"); // Playing solo
        }
        return;
    }
    
    // Check if overdub is muted
    if (overdub_muted[macro_idx]) {
        strcpy(overdub_str, "MUT");
        return;
    }
    
    // Overdub exists but not playing (ready to play)
    strcpy(overdub_str, "MUT");
}

void get_loop_timer_string(uint8_t macro_idx, char* timer_str) {
    // Only show timer if macro is playing and has loop timing
    if (!macro_playback[macro_idx].is_playing || 
        macro_playback[macro_idx].loop_length == 0) {
        strcpy(timer_str, "   ");
        return;
    }
    
    uint32_t loop_length = macro_playback[macro_idx].loop_length;
    uint32_t loop_position;
    
    // Get speed factor for this macro
    float speed_factor = macro_speed_factor[macro_idx];
    
    if (global_playback_paused) {
        // When paused, use the stored pause position (already in loop timeline)
        loop_position = pause_timestamps[macro_idx];
        dprintf("dynamic macro: using stored pause position %lu ms for timer calculation\n", loop_position);
    } else {
        // Normal operation - calculate current position
        uint32_t current_time = timer_read32();
        uint32_t elapsed = current_time - macro_playback[macro_idx].timer;
        
        // Calculate speed-adjusted position in loop timeline
        uint32_t speed_adjusted_elapsed = (uint32_t)(elapsed * speed_factor);
        loop_position = speed_adjusted_elapsed % loop_length;
    }
    
    // Calculate time remaining in loop timeline
    uint32_t loop_time_remaining = loop_length - loop_position;
    
    // Convert to real-world time using speed factor
    uint32_t real_time_remaining;
    if (speed_factor > 0.0f) {
        real_time_remaining = (uint32_t)(loop_time_remaining / speed_factor);
    } else {
        real_time_remaining = loop_time_remaining; // Fallback for invalid speed
    }
    
    // Convert to seconds (timer_read32 returns milliseconds)
    uint32_t seconds_remaining = real_time_remaining / 1000;
    uint32_t tenths_remaining = (real_time_remaining % 1000) / 100;
    
    // Clamp values to prevent format overflow
    if (seconds_remaining >= 99) {
        strcpy(timer_str, "99+");
    } else if (seconds_remaining < 10) {
        // Show X.Y format for less than 10 seconds
        timer_str[0] = '0' + (char)(seconds_remaining % 10);
        timer_str[1] = '.';
        timer_str[2] = '0' + (char)(tenths_remaining % 10);
        timer_str[3] = '\0';
    } else {
        // Show XX format for 10-99 seconds  
        timer_str[0] = '0' + (char)(seconds_remaining / 10);
        timer_str[1] = '0' + (char)(seconds_remaining % 10);
        timer_str[2] = ' '; // Pad with space
        timer_str[3] = '\0';
    }
}

bool dynamic_macro_has_activity(void) {
    // Check if currently recording any macro
    if (macro_id > 0) {
        return true;
    }
    
    // Check if any macro has recorded data
    for (uint8_t i = 1; i <= MAX_MACROS; i++) {
        midi_event_t *macro_start = get_macro_buffer(i);
        midi_event_t **macro_end_ptr = get_macro_end_ptr(i);
        
        if (macro_start != NULL && macro_end_ptr != NULL && macro_start != *macro_end_ptr) {
            return true; // This macro has data
        }
    }
    
    // Check if any overdub buffers have data
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (overdub_buffers[i] != NULL && overdub_buffer_ends[i] != overdub_buffers[i]) {
            return true; // This overdub has data
        }
    }
    
    // NEW: Check if any macro has modulations active
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
		if (has_any_modulation(i) || macro_octave_doubler[i] != 0) {
			return true; // This macro has modulations
		}
    }
    
    return false; // No activity found
}

uint32_t get_total_loop_duration(uint8_t macro_idx) {
    if (macro_idx < MAX_MACROS) {
        return macro_playback[macro_idx].loop_length;
    }
    return 0;  // Return 0 if invalid macro index
}

// Helper function to check if overdub status is flashing
bool is_overdub_status_flashing(uint8_t macro_idx) {
    uint8_t macro_num = macro_idx + 1;
    
    // Check if we're queuing overdub start (from ending recording)
    if (macro_in_overdub_mode[macro_idx]) {
        for (uint8_t j = 0; j < command_batch_count; j++) {
            if (command_batch[j].macro_id == macro_num && 
                command_batch[j].command_type == CMD_STOP && 
                !command_batch[j].processed) {
                return true; // "DUB" is flashing
            }
        }
    }
    
    // Check for overdub mute pending
    if (overdub_mute_pending[macro_idx]) {
        return true; // "MUT" is flashing
    }
    
    // Check for overdub unmute pending (only flash if meaningful change)
    if (overdub_unmute_pending[macro_idx] && overdub_muted[macro_idx]) {
        return true; // "PLY" is flashing
    }
    
    return false;
}

// Helper function to get bpm-synced flash timing
uint32_t get_flash_period_ms(bool is_pending_command) {
    if (current_bpm > 0) {
        if (is_pending_command) {
            // 2x BPM flash rate for pending commands
            return 3000000000ULL / current_bpm;
        } else {
            // 1x BPM flash rate for running states  
            return 6000000000ULL / current_bpm;
        }
    } else {
        // Fallback when no BPM is set
        if (is_pending_command) {
            return 150; // Default fast flash for pending commands
        } else {
            return 400; // Default slow flash for running states
        }
    }
}

// Determine what the future state will be after pending commands execute
void get_future_state(uint8_t macro_idx, char* future_status, char* future_overdub) {
    uint8_t macro_num = macro_idx + 1;
    
    // Start with current state
    get_macro_status_string(macro_idx, future_status);
    get_overdub_status_string(macro_idx, future_overdub);
    
    // Apply queued command changes
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].macro_id == macro_num && !command_batch[i].processed) {
            switch (command_batch[i].command_type) {
                case CMD_PLAY:
                    strcpy(future_status, "PLY");
                    // If overdub exists and not muted, it will play too
                    if (overdub_buffers[macro_idx] != NULL && 
                        overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx] &&
                        !overdub_muted[macro_idx]) {
                        strcpy(future_overdub, "PLY");
                    }
                    break;
                case CMD_STOP:
                    strcpy(future_status, "MUT");
                    
                    // Check if overdub should be kept playing (same logic as execute_command_batch)
                    bool keep_overdub = false;
                    
                    // Check for CMD_PLAY_OVERDUB_ONLY commands for this macro
                    for (uint8_t j = 0; j < command_batch_count; j++) {
                        if (command_batch[j].command_type == CMD_PLAY_OVERDUB_ONLY && 
                            command_batch[j].macro_id == macro_num) {
                            keep_overdub = true;
                            break;
                        }
                    }
                    
                    // Also check pending unmute flags as another indicator to keep overdub
                    if (overdub_unmute_pending[macro_idx]) {
                        keep_overdub = true;
                    }
                    
                    // If not keeping overdub, it will also be stopped (linked stop)
                    if (!keep_overdub) {
                        strcpy(future_overdub, "MUT");
                    }
                    break;
                case CMD_RECORD:
                    strcpy(future_status, "REC");
                    strcpy(future_overdub, "   ");
                    break;
                case CMD_PLAY_OVERDUB_ONLY:
                    strcpy(future_status, "MUT");
                    strcpy(future_overdub, "PLY");
                    break;
                case CMD_GHOST_MUTE:
                    // Macro will be muted but still playing
                    strcpy(future_status, "MUT");
                    break;
            }
        }
    }
    
    // Apply pending overdub state changes
    if (overdub_mute_pending[macro_idx]) {
        strcpy(future_overdub, "MUT");
    }
    if (overdub_unmute_pending[macro_idx]) {
        strcpy(future_overdub, "PLY");
    }
    
    // Check for overdub recording starting
    if (macro_in_overdub_mode[macro_idx]) {
        // Check if there's a CMD_STOP queued (ending recording to start overdub)
        for (uint8_t j = 0; j < command_batch_count; j++) {
            if (command_batch[j].macro_id == macro_num && 
                command_batch[j].command_type == CMD_STOP && 
                !command_batch[j].processed) {
                strcpy(future_overdub, "DUB");
                break;
            }
        }
    }
    
    // If currently overdub recording
    if (overdub_target_macro == macro_num) {
        strcpy(future_overdub, "DUB");
    }
}

// Helper function to interpolate between two colors
static void interpolate_colors(uint8_t r1, uint8_t g1, uint8_t b1,
                              uint8_t r2, uint8_t g2, uint8_t b2,
                              float factor, uint8_t* r_out, uint8_t* g_out, uint8_t* b_out) {
    // Clamp factor to 0.0-1.0 range
    if (factor < 0.0f) factor = 0.0f;
    if (factor > 1.0f) factor = 1.0f;
    
    // Linear interpolation: result = color1 + factor * (color2 - color1)
    *r_out = (uint8_t)(r1 + factor * (float)(r2 - r1));
    *g_out = (uint8_t)(g1 + factor * (float)(g2 - g1));
    *b_out = (uint8_t)(b1 + factor * (float)(b2 - b1));
}

// OLED-Based LED Color System with Future State Logic (Fixed Priority Order)
void get_macro_led_color(uint8_t macro_idx, uint8_t* r, uint8_t* g, uint8_t* b) {
    uint32_t current_time = timer_read32();
    uint8_t macro_num = macro_idx + 1;
    
    // Calculate brightness scaling factor
    uint8_t device_brightness = rgb_matrix_get_val();
    uint16_t brightness_factor = device_brightness + 30;
    if (brightness_factor > 255) brightness_factor = 255;
    
    // Get current OLED display strings
    char current_status[4];
    char current_cmd[4]; 
    char current_overdub[4];
    bool cmd_flashing = false;
    
    get_macro_status_string(macro_idx, current_status);
    get_queued_command_string(macro_idx, current_cmd, &cmd_flashing);
    get_overdub_status_string(macro_idx, current_overdub);
    
    // Check for pending states
    bool has_pending_commands = cmd_flashing || 
                               overdub_mute_pending[macro_idx] || 
                               overdub_unmute_pending[macro_idx] ||
                               (macro_in_overdub_mode[macro_idx] && 
                                command_exists_in_batch(CMD_STOP, macro_num));
    
    // Get future state for transition logic
    char future_status[4];
    char future_overdub[4];
    if (has_pending_commands) {
        get_future_state(macro_idx, future_status, future_overdub);
    } else {
        strcpy(future_status, current_status);
        strcpy(future_overdub, current_overdub);
    }
    
    uint32_t flash_period = get_flash_period_ms(has_pending_commands);
    
    // PRIORITY 1: Macro Primed for Recording (Flash Orange)
    if (is_macro_primed && macro_id == macro_num) {
        uint32_t flash_period = get_flash_period_ms(true);
        bool flash_on = (current_time / (flash_period / 2)) % 2;
        if (flash_on) {
            *r = (200 * brightness_factor) / 255;
            *g = (100 * brightness_factor) / 255;
            *b = 0;
        } else {
            *r = 0; *g = 0; *b = 0;
        }
        return;
    }
    
    // PRIORITY 2: Recording End ("END" command) - Flash Green (must come before recording states)
    if (has_pending_commands && strcmp(current_cmd, "END") == 0) {
        bool flash_on = (current_time / (flash_period / 2)) % 2;
        if (flash_on) {
            uint8_t green_value = (200 * brightness_factor) / 255;
            *r = 0;
            *g = green_value;
            *b = 0;
        } else {
            *r = 0;
            *g = 0;
            *b = 0;
        }
        return;
    }
    
    // PRIORITY 3: Recording states (REC/DUB) - Solid Orange
    if (strcmp(current_status, "REC") == 0 || strcmp(current_overdub, "DUB") == 0 ||
        strcmp(future_status, "REC") == 0 || strcmp(future_overdub, "DUB") == 0) {
        *r = (200 * brightness_factor) / 255;
        *g = (100 * brightness_factor) / 255;
        *b = 0;
        return;
    }
    
    // PRIORITY 4: Transition States (pending commands showing current ↔ future)
    if (has_pending_commands && 
        (strcmp(current_status, future_status) != 0 || strcmp(current_overdub, future_overdub) != 0)) {
        
        bool flash_on = (current_time / (flash_period / 2)) % 2;
        
        // 4a: Muted to Playing transition (Red ↔ Green)
        if (strcmp(current_status, "MUT") == 0 && 
            (strcmp(future_status, "PLY") == 0 || strcmp(future_status, "2.0") == 0 || 
             strcmp(future_status, "1.5") == 0 || strcmp(future_status, ".75") == 0 ||
             strcmp(future_status, ".50") == 0 || strcmp(future_status, ".25") == 0)) {
            
            if (flash_on) {
                // Show current state (red for muted)
                *r = (200 * brightness_factor) / 255;
                *g = 0;
                *b = 0;
            } else {
                // Show future state (green for playing)
                *r = 0;
                *g = (200 * brightness_factor) / 255;
                *b = 0;
            }
            return;
        }
        
        // 4b: Playing to Muted transition (Green ↔ Red)
        if ((strcmp(current_status, "PLY") == 0 || strcmp(current_status, "2.0") == 0 || 
             strcmp(current_status, "1.5") == 0 || strcmp(current_status, ".75") == 0 ||
             strcmp(current_status, ".50") == 0 || strcmp(current_status, ".25") == 0) &&
            strcmp(future_status, "MUT") == 0) {
            
            if (flash_on) {
                // Show current state (green for playing)
                *r = 0;
                *g = (200 * brightness_factor) / 255;
                *b = 0;
            } else {
                // Show future state (red for muted)
                *r = (200 * brightness_factor) / 255;
                *g = 0;
                *b = 0;
            }
            return;
        }
        
        // 4c: Empty to Recording transition (Gray ↔ Orange)
        if (strcmp(current_status, " - ") == 0 && strcmp(future_status, "REC") == 0) {
            if (flash_on) {
                // Show current state (gray for empty)
                *r = (30 * brightness_factor) / 255;
                *g = (30 * brightness_factor) / 255;
                *b = (30 * brightness_factor) / 255;
            } else {
                // Show future state (orange for recording)
                *r = (200 * brightness_factor) / 255;
                *g = (100 * brightness_factor) / 255;
                *b = 0;
            }
            return;
        }
        
        // 4d: Overdub state transitions
        if (strcmp(current_overdub, future_overdub) != 0) {
            // Handle overdub-only transitions by showing the future state with fast flash
            // Fall through to show future state with appropriate flashing
        }
    }
    
    // PRIORITY 5: Playing combinations (use future state if pending, current if not)
    char display_status[4];
    char display_overdub[4];
    strcpy(display_status, has_pending_commands ? future_status : current_status);
    strcpy(display_overdub, has_pending_commands ? future_overdub : current_overdub);
    
    bool is_playing = (strcmp(display_status, "PLY") == 0 || strcmp(display_status, "2.0") == 0 || 
                      strcmp(display_status, "1.5") == 0 || strcmp(display_status, ".75") == 0 ||
                      strcmp(display_status, ".50") == 0 || strcmp(display_status, ".25") == 0);
    
    if (is_playing) {
        uint8_t green_value = (200 * brightness_factor) / 255;
        
        // Loop fade effect (only for current state, not future state)
        if (!has_pending_commands && macro_playback[macro_idx].is_playing) {
            uint32_t elapsed = current_time - macro_playback[macro_idx].timer;
            if (elapsed <= 1000) {
                float fade_factor = 1.0f - ((float)elapsed / 1000.0f);
                float brightness_multiplier = 1.0f + fade_factor;
                green_value = (uint16_t)(green_value * brightness_multiplier);
                if (green_value > 255) green_value = 255;
            }
        }
        
        if (strcmp(display_overdub, "PLY") == 0) {
            // Macro + overdub playing - Transition Green ↔ Purple
            if (has_pending_commands) {
                // Fast flash: hard transitions (pending state)
                bool flash_on = (current_time / (flash_period / 2)) % 2;
                if (flash_on) {
                    *r = 0;
                    *g = green_value;
                    *b = 0;
                } else {
                    *r = (150 * brightness_factor) / 255;
                    *g = 0;
                    *b = (200 * brightness_factor) / 255;
                }
            } else {
                // bpm-synced transitions: 16-beat cycle
                uint32_t bpm_cycle_period = flash_period * 1;
                uint32_t time_in_cycle = current_time % bpm_cycle_period;
                float cycle_factor = (float)time_in_cycle / (float)bpm_cycle_period;
                
                uint8_t final_r, final_g, final_b;
                
                if (cycle_factor < 0.4f) {
                    final_r = 0;
                    final_g = green_value;
                    final_b = 0;
                } else if (cycle_factor < 0.5f) {
                    float transition_progress = (cycle_factor - 0.4f) / 0.1f;
                    uint8_t green_r = 0, green_g = green_value, green_b = 0;
                    uint8_t purple_r = (150 * brightness_factor) / 255;
                    uint8_t purple_g = 0, purple_b = (200 * brightness_factor) / 255;
                    interpolate_colors(green_r, green_g, green_b, purple_r, purple_g, purple_b, 
                                     transition_progress, &final_r, &final_g, &final_b);
                } else if (cycle_factor < 0.9f) {
                    final_r = (150 * brightness_factor) / 255;
                    final_g = 0;
                    final_b = (200 * brightness_factor) / 255;
                } else {
                    float transition_progress = (cycle_factor - 0.9f) / 0.1f;
                    uint8_t purple_r = (150 * brightness_factor) / 255;
                    uint8_t purple_g = 0, purple_b = (200 * brightness_factor) / 255;
                    uint8_t green_r = 0, green_g = green_value, green_b = 0;
                    interpolate_colors(purple_r, purple_g, purple_b, green_r, green_g, green_b, 
                                     transition_progress, &final_r, &final_g, &final_b);
                }
                
                *r = final_r;
                *g = final_g;
                *b = final_b;
            }
            return;
        }
        else if (strcmp(display_overdub, "MUT") == 0) {
            // Check if overdub actually has content
            bool overdub_has_content = (overdub_buffers[macro_idx] != NULL && 
                                       overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx]);
            
            if (overdub_has_content) {
                // Macro playing, overdub muted (but exists) - Transition Green ↔ Blue
                if (has_pending_commands) {
                    bool flash_on = (current_time / (flash_period / 2)) % 2;
                    if (flash_on) {
                        *r = 0; *g = green_value; *b = 0;
                    } else {
                        *r = 0; *g = 0; *b = (200 * brightness_factor) / 255;
                    }
                } else {
                    // BPM-synced transitions
                    uint32_t bpm_cycle_period = flash_period * 1;
                    uint32_t time_in_cycle = current_time % bpm_cycle_period;
                    float cycle_factor = (float)time_in_cycle / (float)bpm_cycle_period;
                    
                    uint8_t final_r, final_g, final_b;
                    
                    if (cycle_factor < 0.375f) {
                        final_r = 0; final_g = green_value; final_b = 0;
                    } else if (cycle_factor < 0.5f) {
                        float transition_progress = (cycle_factor - 0.375f) / 0.125f;
                        uint8_t green_r = 0, green_g = green_value, green_b = 0;
                        uint8_t blue_r = 0, blue_g = 0, blue_b = (200 * brightness_factor) / 255;
                        interpolate_colors(green_r, green_g, green_b, blue_r, blue_g, blue_b, 
                                         transition_progress, &final_r, &final_g, &final_b);
                    } else if (cycle_factor < 0.875f) {
                        final_r = 0; final_g = 0; final_b = (200 * brightness_factor) / 255;
                    } else {
                        float transition_progress = (cycle_factor - 0.875f) / 0.125f;
                        uint8_t blue_r = 0, blue_g = 0, blue_b = (200 * brightness_factor) / 255;
                        uint8_t green_r = 0, green_g = green_value, green_b = 0;
                        interpolate_colors(blue_r, blue_g, blue_b, green_r, green_g, green_b, 
                                         transition_progress, &final_r, &final_g, &final_b);
                    }
                    
                    *r = final_r; *g = final_g; *b = final_b;
                }
            } else {
                // Macro playing, no overdub content - Just solid green
                *r = 0; *g = green_value; *b = 0;
            }
            return;
        }
        else if (strcmp(display_overdub, "DUB") == 0) {
            // Macro playing + overdub recording - Green with orange flashes
            if (has_pending_commands) {
                bool flash_on = (current_time / (flash_period / 2)) % 2;
                if (flash_on) {
                    *r = 0; *g = green_value; *b = 0; // Green
                } else {
                    *r = (200 * brightness_factor) / 255; // Orange
                    *g = (100 * brightness_factor) / 255;
                    *b = 0;
                }
            } else {
                // BPM-synced green-orange transitions (similar pattern to other transitions)
                uint32_t bpm_cycle_period = flash_period * 1;
                uint32_t time_in_cycle = current_time % bpm_cycle_period;
                float cycle_factor = (float)time_in_cycle / (float)bpm_cycle_period;
                
                uint8_t final_r, final_g, final_b;
                
                if (cycle_factor < 0.4f) {
                    final_r = 0; final_g = green_value; final_b = 0;
                } else if (cycle_factor < 0.5f) {
                    float transition_progress = (cycle_factor - 0.4f) / 0.1f;
                    uint8_t green_r = 0, green_g = green_value, green_b = 0;
                    uint8_t orange_r = (200 * brightness_factor) / 255;
                    uint8_t orange_g = (100 * brightness_factor) / 255, orange_b = 0;
                    interpolate_colors(green_r, green_g, green_b, orange_r, orange_g, orange_b, 
                                     transition_progress, &final_r, &final_g, &final_b);
                } else if (cycle_factor < 0.9f) {
                    final_r = (200 * brightness_factor) / 255;
                    final_g = (100 * brightness_factor) / 255;
                    final_b = 0;
                } else {
                    float transition_progress = (cycle_factor - 0.9f) / 0.1f;
                    uint8_t orange_r = (200 * brightness_factor) / 255;
                    uint8_t orange_g = (100 * brightness_factor) / 255, orange_b = 0;
                    uint8_t green_r = 0, green_g = green_value, green_b = 0;
                    interpolate_colors(orange_r, orange_g, orange_b, green_r, green_g, green_b, 
                                     transition_progress, &final_r, &final_g, &final_b);
                }
                
                *r = final_r; *g = final_g; *b = final_b;
            }
            return;
        }
        else {
            // Just macro playing - Solid Green
            *r = 0; *g = green_value; *b = 0;
            return;
        }
    }
    
    // PRIORITY 6: Muted combinations
    if (strcmp(display_status, "MUT") == 0) {
        if (strcmp(display_overdub, "PLY") == 0) {
            // Macro stopped, overdub playing - Transition Red ↔ Purple
            if (has_pending_commands) {
                bool flash_on = (current_time / (flash_period / 2)) % 2;
                if (flash_on) {
                    *r = (200 * brightness_factor) / 255; *g = 0; *b = 0;
                } else {
                    *r = (150 * brightness_factor) / 255;
                    *g = 0; *b = (200 * brightness_factor) / 255;
                }
            } else {
                // BPM-synced transitions
                uint32_t bpm_cycle_period = flash_period * 1;
                uint32_t time_in_cycle = current_time % bpm_cycle_period;
                float cycle_factor = (float)time_in_cycle / (float)bpm_cycle_period;
                
                uint8_t final_r, final_g, final_b;
                
                if (cycle_factor < 0.375f) {
                    final_r = (200 * brightness_factor) / 255; final_g = 0; final_b = 0;
                } else if (cycle_factor < 0.5f) {
                    float transition_progress = (cycle_factor - 0.375f) / 0.125f;
                    uint8_t red_r = (200 * brightness_factor) / 255, red_g = 0, red_b = 0;
                    uint8_t purple_r = (150 * brightness_factor) / 255;
                    uint8_t purple_g = 0, purple_b = (200 * brightness_factor) / 255;
                    interpolate_colors(red_r, red_g, red_b, purple_r, purple_g, purple_b, 
                                     transition_progress, &final_r, &final_g, &final_b);
                } else if (cycle_factor < 0.875f) {
                    final_r = (150 * brightness_factor) / 255; final_g = 0;
                    final_b = (200 * brightness_factor) / 255;
                } else {
                    float transition_progress = (cycle_factor - 0.875f) / 0.125f;
                    uint8_t purple_r = (150 * brightness_factor) / 255;
                    uint8_t purple_g = 0, purple_b = (200 * brightness_factor) / 255;
                    uint8_t red_r = (200 * brightness_factor) / 255, red_g = 0, red_b = 0;
                    interpolate_colors(purple_r, purple_g, purple_b, red_r, red_g, red_b, 
                                     transition_progress, &final_r, &final_g, &final_b);
                }
                
                *r = final_r; *g = final_g; *b = final_b;
            }
            return;
        }
        else {
            // Macro stopped - Red (with flashing if pending)
            if (has_pending_commands && strcmp(current_status, future_status) == 0) {
                // Fast flash for pending stop: Flash Red ↔ Off
                bool flash_on = (current_time / (flash_period / 2)) % 2;
                if (flash_on) {
                    *r = (200 * brightness_factor) / 255; *g = 0; *b = 0;
                } else {
                    *r = 0; *g = 0; *b = 0;
                }
            } else {
                // Solid Red
                *r = (200 * brightness_factor) / 255; *g = 0; *b = 0;
            }
            return;
        }
    }
    
    // PRIORITY 7: Empty slot (only if no pending commands)
    if (!has_pending_commands && strcmp(current_status, " - ") == 0 && strcmp(current_overdub, "   ") == 0) {
        *r = (30 * brightness_factor) / 255;
        *g = (30 * brightness_factor) / 255;
        *b = (30 * brightness_factor) / 255;
        return;
    }
    
    // Default fallback
    *r = 0; *g = 0; *b = 0;
}// Forward declaration
void dynamic_macro_hid_receive(uint8_t *data, uint8_t length);


// Function to send HID response
static void send_hid_response(uint8_t command, uint8_t macro_num, uint8_t status, 
                             const uint8_t* data, uint16_t data_len) {
    uint8_t packet[HID_PACKET_SIZE] = {0};
    
    // Header
    packet[0] = HID_MANUFACTURER_ID;
    packet[1] = HID_SUB_ID;
    packet[2] = HID_DEVICE_ID;
    packet[3] = command;
    packet[4] = macro_num;
    packet[5] = status;
    
    // Data (up to 26 bytes)
    if (data && data_len > 0) {
        uint16_t copy_len = data_len > (HID_PACKET_SIZE - HID_HEADER_SIZE) ? 
                           (HID_PACKET_SIZE - HID_HEADER_SIZE) : data_len;
        memcpy(&packet[HID_HEADER_SIZE], data, copy_len);
    }
    
    raw_hid_send(packet, HID_PACKET_SIZE);
}

// Function to send multi-packet data
static void send_hid_multi_packet_data(uint8_t command, uint8_t macro_num, 
                                      const uint8_t* data, uint16_t total_len) {
    // Calculate total packets needed
    uint16_t total_packets = (total_len + HID_CHUNK_SIZE - 1) / HID_CHUNK_SIZE;
    
    dprintf("Sending %d bytes in %d HID packets\n", total_len, total_packets);
    
    // Send start packet
    uint8_t start_data[4] = {
        total_packets & 0xFF,
        (total_packets >> 8) & 0xFF,
        total_len & 0xFF,
        (total_len >> 8) & 0xFF
    };
    send_hid_response(command, macro_num, 0, start_data, 4);
    
    // Send data packets
    for (uint16_t packet = 0; packet < total_packets; packet++) {
        uint16_t offset = packet * HID_CHUNK_SIZE;
        uint16_t chunk_len = (offset + HID_CHUNK_SIZE > total_len) ? 
                            (total_len - offset) : HID_CHUNK_SIZE;
        
        uint8_t chunk_packet[HID_DATA_SIZE];
        chunk_packet[0] = packet & 0xFF;
        chunk_packet[1] = (packet >> 8) & 0xFF;
        chunk_packet[2] = chunk_len & 0xFF;
        chunk_packet[3] = (chunk_len >> 8) & 0xFF;
        
        memcpy(&chunk_packet[4], &data[offset], chunk_len);
        
        send_hid_response(HID_CMD_SAVE_CHUNK, macro_num, 0, chunk_packet, chunk_len + 4);
        
        // Small delay between packets for stability
        wait_ms(5);
    }
    
    // Send end packet
    send_hid_response(HID_CMD_SAVE_END, macro_num, 0, NULL, 0);
}

// Handle save request from web app
static void handle_hid_save_request(uint8_t macro_num) {
    dprintf("HID save request for macro %d\n", macro_num);
    
    // Check if macro has data
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
    
    if (macro_start == *macro_end_ptr) {
        // Empty macro
        send_hid_response(HID_CMD_SAVE_START, macro_num, 1, NULL, 0); // Status 1 = error
        return;
    }
    
    // Serialize macro data
    static uint8_t serialize_buffer[MACRO_BUFFER_SIZE * 2];
    uint16_t data_size = serialize_macro_data(macro_num, serialize_buffer);
    
    if (data_size == 0) {
        send_hid_response(HID_CMD_SAVE_START, macro_num, 1, NULL, 0);
        return;
    }
    
    // Send data via HID (no 7-bit encoding needed!)
    send_hid_multi_packet_data(HID_CMD_SAVE_START, macro_num, serialize_buffer, data_size);
}

// Handle load data from web app
static void handle_hid_load_data(uint8_t macro_num, const uint8_t* data, uint16_t data_len) {
    dprintf("Loading %d bytes to macro %d\n", data_len, macro_num);
    
    // Deserialize and load
    if (deserialize_macro_data((uint8_t*)data, data_len, macro_num)) {
        send_hid_response(HID_CMD_LOAD_END, macro_num, 0, NULL, 0); // Success
        dprintf("Successfully loaded macro %d\n", macro_num);
    } else {
        send_hid_response(HID_CMD_LOAD_END, macro_num, 1, NULL, 0); // Error
        dprintf("Failed to load macro %d\n", macro_num);
    }
}

// Function to trigger HID save from button press (replaces send_macro_via_sysex)
void send_macro_via_hid(uint8_t macro_num) {
    handle_hid_save_request(macro_num);
}


// Set loop messaging basic configuration
static void handle_set_loop_config(const uint8_t* data) {
    loop_messaging_enabled = (data[0] != 0);
    
    // Validate and set channel (1-16)
    uint8_t channel = data[1];
    if (channel >= 1 && channel <= 16) {
        loop_messaging_channel = channel;
    }
    
    sync_midi_mode = (data[2] != 0);
    alternate_restart_mode = (data[3] != 0);
    
    // Set loop restart CCs (4 bytes)
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        loop_restart_cc[i] = data[4 + i];
    }
	cclooprecording = (data[8] != 0);  // 9th byte for cclooprecording
    
    // SAVE TO EEPROM
    save_loop_settings();
    
    dprintf("HID: Updated loop config - enabled:%d, channel:%d, sync:%d, alt_restart:%d\n", 
            loop_messaging_enabled, loop_messaging_channel, sync_midi_mode, alternate_restart_mode);
}

// Set main loop CC arrays
static void handle_set_main_loop_ccs(const uint8_t* data) {
    // Each array is 4 bytes (MAX_MACROS)
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        loop_start_recording_cc[i] = data[0 + i];
        loop_stop_recording_cc[i] = data[4 + i];
        loop_start_playing_cc[i] = data[8 + i];
        loop_stop_playing_cc[i] = data[12 + i];
        loop_clear_cc[i] = data[16 + i];
    }
    
    // SAVE TO EEPROM
    save_loop_settings();
    
    dprintf("HID: Updated main loop CCs\n");
}

// Set overdub CC arrays
// Set overdub CC arrays
static void handle_set_overdub_ccs(const uint8_t* data) {
    // Each array is 4 bytes (MAX_MACROS)
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        overdub_start_recording_cc[i] = data[0 + i];
        overdub_stop_recording_cc[i] = data[4 + i];
        overdub_start_playing_cc[i] = data[8 + i];
        overdub_stop_playing_cc[i] = data[12 + i];
        overdub_clear_cc[i] = data[16 + i];
        overdub_restart_cc[i] = data[20 + i];  // ADD THIS LINE
    }
    
    // SAVE TO EEPROM
    save_loop_settings();
    
    dprintf("HID: Updated overdub CCs\n");
}
// Set navigation configuration
static void handle_set_navigation_config(const uint8_t* data) {
    loop_navigate_use_master_cc = (data[0] != 0);
    loop_navigate_master_cc = data[1];
    
    // Set individual navigation CCs (8 bytes)
    loop_navigate_0_8_cc = data[2];
    loop_navigate_1_8_cc = data[3];
    loop_navigate_2_8_cc = data[4];
    loop_navigate_3_8_cc = data[5];
    loop_navigate_4_8_cc = data[6];
    loop_navigate_5_8_cc = data[7];
    loop_navigate_6_8_cc = data[8];
    loop_navigate_7_8_cc = data[9];
    
    // SAVE TO EEPROM
    save_loop_settings();
    
    dprintf("HID: Updated navigation config - use_master:%d, master_cc:%d\n", 
            loop_navigate_use_master_cc, loop_navigate_master_cc);
}

// Send all configuration back to the web app
// Send all configuration back to the web app
static void handle_get_all_config(uint8_t macro_num) {
    // We need to send multiple packets since all config won't fit in one packet
    load_loop_settings();
    
    // Packet 1: Loop messaging basic config
    uint8_t config_packet1[9];
    config_packet1[0] = loop_messaging_enabled ? 1 : 0;
    config_packet1[1] = loop_messaging_channel;
    config_packet1[2] = sync_midi_mode ? 1 : 0;
    config_packet1[3] = alternate_restart_mode ? 1 : 0;
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        config_packet1[4 + i] = loop_restart_cc[i];
    }
    config_packet1[8] = cclooprecording ? 1 : 0;
    send_hid_response(HID_CMD_SET_LOOP_CONFIG, macro_num, 0, config_packet1, 9);
    wait_ms(5);
    
    // Packet 2: Main loop CCs
    uint8_t config_packet2[20];
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        config_packet2[0 + i] = loop_start_recording_cc[i];
        config_packet2[4 + i] = loop_stop_recording_cc[i];
        config_packet2[8 + i] = loop_start_playing_cc[i];
        config_packet2[12 + i] = loop_stop_playing_cc[i];
        config_packet2[16 + i] = loop_clear_cc[i];
    }
    send_hid_response(HID_CMD_SET_MAIN_LOOP_CCS, macro_num, 0, config_packet2, 20);
    wait_ms(5);
    
    // Packet 3: Overdub CCs - UPDATED TO 24 BYTES
    uint8_t config_packet3[24];  // CHANGED FROM 20 TO 24
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        config_packet3[0 + i] = overdub_start_recording_cc[i];
        config_packet3[4 + i] = overdub_stop_recording_cc[i];
        config_packet3[8 + i] = overdub_start_playing_cc[i];
        config_packet3[12 + i] = overdub_stop_playing_cc[i];
        config_packet3[16 + i] = overdub_clear_cc[i];
        config_packet3[20 + i] = overdub_restart_cc[i];  // ADD THIS LINE
    }
    send_hid_response(HID_CMD_SET_OVERDUB_CCS, macro_num, 0, config_packet3, 24);  // CHANGED FROM 20 TO 24
    wait_ms(5);
    
    // Packet 4: Navigation config
    uint8_t config_packet4[10];
    config_packet4[0] = loop_navigate_use_master_cc ? 1 : 0;
    config_packet4[1] = loop_navigate_master_cc;
    config_packet4[2] = loop_navigate_0_8_cc;
    config_packet4[3] = loop_navigate_1_8_cc;
    config_packet4[4] = loop_navigate_2_8_cc;
    config_packet4[5] = loop_navigate_3_8_cc;
    config_packet4[6] = loop_navigate_4_8_cc;
    config_packet4[7] = loop_navigate_5_8_cc;
    config_packet4[8] = loop_navigate_6_8_cc;
    config_packet4[9] = loop_navigate_7_8_cc;
    send_hid_response(HID_CMD_SET_NAVIGATION_CONFIG, macro_num, 0, config_packet4, 10);
    
    dprintf("HID: Sent all configuration to web app\n");
}
// Reset all loop messaging configuration to defaults
static void handle_reset_loop_config(void) {
    // Reset to your default values
    loop_messaging_enabled = false;
    loop_messaging_channel = 16;  // Changed to match initialization
    sync_midi_mode = false;
    alternate_restart_mode = false;
    
    // Reset all CC arrays to 128 (disabled)
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        loop_restart_cc[i] = 128;
        loop_start_recording_cc[i] = 128;
        loop_stop_recording_cc[i] = 128;
        loop_start_playing_cc[i] = 128;
        loop_stop_playing_cc[i] = 128;
        loop_clear_cc[i] = 128;
        overdub_start_recording_cc[i] = 128;
        overdub_stop_recording_cc[i] = 128;
        overdub_start_playing_cc[i] = 128;
        overdub_stop_playing_cc[i] = 128;
        overdub_clear_cc[i] = 128;
    }
    
    // Reset navigation
    loop_navigate_use_master_cc = false;
    loop_navigate_master_cc = 128;
    loop_navigate_0_8_cc = 128;
    loop_navigate_1_8_cc = 128;
    loop_navigate_2_8_cc = 128;
    loop_navigate_3_8_cc = 128;
    loop_navigate_4_8_cc = 128;
    loop_navigate_5_8_cc = 128;
    loop_navigate_6_8_cc = 128;
    loop_navigate_7_8_cc = 128;
	cclooprecording = false;
    
    // SAVE TO EEPROM
    save_loop_settings();
    
    dprintf("HID: Reset all loop messaging configuration to defaults\n");
}

// Clear all loop content (same as holding all macro buttons)
static void handle_clear_all_loops(void) {
    dprintf("HID: Clearing all loop content\n");

    // Loop through all macros and clear each one
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        uint8_t macro_num = i + 1;

        // Stop main macro
        if (macro_playback[i].is_playing) {
            dynamic_macro_cleanup_notes_for_state(&macro_playback[i]);
            macro_playback[i].is_playing = false;
            macro_playback[i].current = NULL;
        }

        // Stop overdub
        if (overdub_playback[i].is_playing) {
            dynamic_macro_cleanup_notes_for_state(&overdub_playback[i]);
            overdub_playback[i].is_playing = false;
            overdub_playback[i].current = NULL;
        }

        // Clear temp overdub data AND zero the memory
        if (overdub_temp_count[i] > 0) {
            midi_event_t *temp_start = get_overdub_read_start(macro_num);
            if (temp_start != NULL) {
                memset(temp_start, 0, overdub_temp_count[i] * sizeof(midi_event_t));
            }
        }
        overdub_temp_count[i] = 0;
        overdub_merge_pending[i] = false;

        // ZERO OUT THE MAIN MACRO MEMORY CONTENT
        midi_event_t *macro_start = get_macro_buffer(macro_num);
        midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);

        if (macro_start && macro_end_ptr) {
            // Calculate how much memory to clear (entire macro buffer)
            uint32_t macro_buffer_events = MACRO_BUFFER_SIZE / sizeof(midi_event_t);
            memset(macro_start, 0, macro_buffer_events * sizeof(midi_event_t));

            // Set macro end pointer to start (making it empty)
            *macro_end_ptr = macro_start;
        }

        // Clear overdub buffer references (permanent overdub area)
        overdub_buffers[i] = NULL;
        overdub_buffer_ends[i] = NULL;
        overdub_buffer_sizes[i] = 0;
        overdub_muted[i] = false;

        // COMPLETE PLAYBACK STATE RESET (matching device startup)
        macro_playback[i].current = NULL;
        macro_playback[i].end = NULL;
        macro_playback[i].buffer_start = NULL;
        macro_playback[i].timer = 0;
        macro_playback[i].direction = +1;
        macro_playback[i].is_playing = false;
        macro_playback[i].waiting_for_loop_gap = false;
        macro_playback[i].next_event_time = 0;
        macro_playback[i].loop_gap_time = 0;
        macro_playback[i].loop_length = 0;
        macro_main_muted[i] = false;

        // COMPLETE OVERDUB PLAYBACK STATE RESET
        overdub_playback[i].current = NULL;
        overdub_playback[i].end = NULL;
        overdub_playback[i].buffer_start = NULL;
        overdub_playback[i].timer = 0;
        overdub_playback[i].direction = +1;
        overdub_playback[i].is_playing = false;
        overdub_playback[i].waiting_for_loop_gap = false;
        overdub_playback[i].next_event_time = 0;
        overdub_playback[i].loop_gap_time = 0;
        overdub_playback[i].loop_length = 0;
        macro_manual_speed[i] = 1.0f;
        macro_speed_factor[i] = 1.0f;
        capture_early_overdub_events[i] = false;
        early_overdub_count[i] = 0;
        memset(early_overdub_buffer[i], 0, sizeof(early_overdub_buffer[i]));
        overdub_independent_loop_length[i] = 0;
        overdub_independent_timer[i] = 0;
        overdub_independent_gap_time[i] = 0;
        overdub_independent_start_time[i] = 0;
        overdub_independent_waiting_for_gap[i] = false;
        overdub_independent_suspended[i] = false;
        overdub_independent_suspension_time[i] = 0;

        // Clear recording suspension and pause states
        recording_suspended[i] = false;
        pause_timestamps[i] = 0;
        overdub_pause_timestamps[i] = 0;
        macro_speed_before_pause[i] = 1.0f;

        // Clear preroll if this macro was collecting it
        if (collecting_preroll && macro_id == macro_num) {
            collecting_preroll = false;
            preroll_buffer_count = 0;
            preroll_buffer_index = 0;
            preroll_start_time = 0;
            memset(preroll_buffer, 0, sizeof(preroll_buffer));
        }

        // Reset global recording state if this was the recording macro
        if (macro_id == macro_num) {
            macro_id = 0;
            current_macro_id = 0;
            macro_pointer = NULL;
            is_macro_primed = false;
            first_note_recorded = false;
            is_macro_empty = true;
            recording_start_time = 0;
            recording_sustain_active = false;
            stop_dynamic_macro_recording();
        }

        // Reset overdub target if this was the target
        if (overdub_target_macro == macro_num) {
            overdub_target_macro = 0;
            current_macro_id = 0;
            if (macro_id == macro_num) {
                macro_id = 0;
                stop_dynamic_macro_recording();
            }
        }

        // If this was the BPM source macro, clear the source and reset BPM
        if (bpm_source_macro == macro_num) {
            bpm_source_macro = 0;
            current_bpm = 0;
            original_system_bpm = 0;
        }

        macro_recording_bpm[i] = 0;
        macro_has_content[i] = false;
        macro_manual_speed[i] = 1.0f;

        // Reset ALL transformation values to device startup state
        reset_macro_transformations(macro_num);

        // RESET ADDITIONAL MACRO-SPECIFIC FLAGS (matching device startup)
        skip_autoplay_for_macro[i] = false;
        ignore_second_press[i] = false;
        last_macro_press_time[i] = 0;
        macro_deleted[i] = false;

        // Clear overdub mode flag
        macro_in_overdub_mode[i] = false;

        // Clear any pending overdub operations
        overdub_mute_pending[i] = false;
        overdub_unmute_pending[i] = false;

        // Reset key press tracking
        key_timers[i] = 0;
        macro_key_held[i] = false;

        // Clear any queued commands for this macro
        for (uint8_t j = 0; j < command_batch_count; j++) {
            if (command_batch[j].macro_id == macro_num) {
                for (uint8_t k = j; k < command_batch_count - 1; k++) {
                    command_batch[k] = command_batch[k + 1];
                }
                command_batch_count--;
                j--;
            }
        }

        // Send loop clear messages
        send_loop_message(loop_clear_cc[i], 127);
        send_loop_message(overdub_clear_cc[i], 127);

        dprintf("dynamic macro: cleared loop %d\n", macro_num);
    }

    // Clear all live notes
    force_clear_all_live_notes();

    dprintf("HID: All loops cleared successfully\n");
}

// ============================================================================
// DKS HID HANDLER FUNCTIONS
// ============================================================================

/**
 * Get DKS slot configuration and send it back via HID
 * Packet format: [slot_num]
 */
static void handle_dks_get_slot(const uint8_t* data) {
    uint8_t slot_num = data[0];

    if (slot_num >= DKS_NUM_SLOTS) {
        send_hid_response(HID_CMD_DKS_GET_SLOT, 0, 1, NULL, 0); // Error: invalid slot
        return;
    }

    const dks_slot_t* slot = dks_get_slot(slot_num);
    if (!slot) {
        send_hid_response(HID_CMD_DKS_GET_SLOT, 0, 1, NULL, 0); // Error
        return;
    }

    // Send back the 32-byte slot configuration
    send_hid_response(HID_CMD_DKS_GET_SLOT, 0, 0, (const uint8_t*)slot, sizeof(dks_slot_t));
}

/**
 * Set a single DKS action
 * Packet format: [slot_num] [is_press] [action_index] [keycode_low] [keycode_high] [actuation] [behavior]
 */
static void handle_dks_set_action(const uint8_t* data) {
    uint8_t slot_num = data[0];
    uint8_t is_press = data[1];           // 0=release, 1=press
    uint8_t action_index = data[2];       // 0-3
    uint16_t keycode = data[3] | (data[4] << 8);
    uint8_t actuation = data[5];
    uint8_t behavior = data[6];

    if (slot_num >= DKS_NUM_SLOTS || action_index >= DKS_ACTIONS_PER_STAGE) {
        return; // Invalid parameters
    }

    // Get slot (we need to modify it, so cast away const)
    dks_slot_t* slot = (dks_slot_t*)dks_get_slot(slot_num);
    if (!slot) {
        return;
    }

    // Set the action
    if (is_press) {
        slot->press_keycode[action_index] = keycode;
        slot->press_actuation[action_index] = actuation;
        dks_set_behavior(slot, action_index, (dks_behavior_t)behavior);
    } else {
        slot->release_keycode[action_index] = keycode;
        slot->release_actuation[action_index] = actuation;
        dks_set_behavior(slot, action_index + 4, (dks_behavior_t)behavior);
    }
}

/**
 * Reset a single DKS slot to defaults
 * Packet format: [slot_num]
 */
static void handle_dks_reset_slot(const uint8_t* data) {
    uint8_t slot_num = data[0];

    if (slot_num >= DKS_NUM_SLOTS) {
        send_hid_response(HID_CMD_DKS_RESET_SLOT, 0, 1, NULL, 0); // Error
        return;
    }

    // Get slot and reset it
    dks_slot_t* slot = (dks_slot_t*)dks_get_slot(slot_num);
    if (!slot) {
        send_hid_response(HID_CMD_DKS_RESET_SLOT, 0, 1, NULL, 0); // Error
        return;
    }

    // Reset this slot
    memset(slot->press_keycode, 0, sizeof(slot->press_keycode));
    memset(slot->release_keycode, 0, sizeof(slot->release_keycode));

    // Set default actuation points
    slot->press_actuation[0] = 24;  // 0.6mm
    slot->press_actuation[1] = 48;  // 1.2mm
    slot->press_actuation[2] = 72;  // 1.8mm
    slot->press_actuation[3] = 96;  // 2.4mm

    slot->release_actuation[0] = 96;  // 2.4mm
    slot->release_actuation[1] = 72;  // 1.8mm
    slot->release_actuation[2] = 48;  // 1.2mm
    slot->release_actuation[3] = 24;  // 0.6mm

    slot->behaviors = 0x0000;  // All TAP

    send_hid_response(HID_CMD_DKS_RESET_SLOT, 0, 0, NULL, 0); // Success
}

// Our HID receive handler (called from VIA's raw_hid_receive)
void dynamic_macro_hid_receive(uint8_t *data, uint8_t length) {
    // Add static variable to track the type of loading in progress
    static uint8_t hid_load_type = 0; // 0 = regular, HID_CMD_LOAD_OVERDUB_START = overdub
    
    dprintf("MACRO HID: Received %d bytes: [%02X %02X %02X %02X %02X %02X]\n", 
            length, data[0], data[1], data[2], data[3], data[4], data[5]);
    
    // Validate packet
    if (length != HID_PACKET_SIZE || 
        data[0] != HID_MANUFACTURER_ID || 
        data[1] != HID_SUB_ID || 
        data[2] != HID_DEVICE_ID) {
        dprintf("MACRO HID: Invalid packet header or length\n");
        return;
    }
    
    uint8_t command = data[3];
    uint8_t macro_num = data[4];
    
    dprintf("HID command: %d, macro: %d\n", command, macro_num);
    
    switch (command) {
        case HID_CMD_REQUEST_SAVE:
            handle_hid_save_request(macro_num);
            break;
            
        case HID_CMD_LOAD_START:
            if (length >= 10) {
                hid_expected_total_packets = data[6] | (data[7] << 8);
                
                hid_receiving_multi_packet = true;
                hid_received_packets = 0;
                hid_rx_buffer_pos = 0;
                hid_load_type = HID_CMD_LOAD_START; // Track regular load
                
                // Acknowledge
                send_hid_response(HID_CMD_LOAD_START, macro_num, 0, NULL, 0);
            }
            break;
            
        case HID_CMD_LOAD_OVERDUB_START:
            if (length >= 10) {
                hid_expected_total_packets = data[6] | (data[7] << 8);
                
                hid_receiving_multi_packet = true;
                hid_received_packets = 0;
                hid_rx_buffer_pos = 0;
                hid_load_type = HID_CMD_LOAD_OVERDUB_START; // Track overdub-only load
                
                // Acknowledge
                send_hid_response(HID_CMD_LOAD_OVERDUB_START, macro_num, 0, NULL, 0);
                dprintf("HID: Started overdub-only load for macro %d\n", macro_num);
            }
            break;
            
        case HID_CMD_LOAD_CHUNK:
            if (hid_receiving_multi_packet && length >= 10) {               
                uint16_t chunk_len = data[8] | (data[9] << 8);
                
                if (chunk_len > 0 && chunk_len <= HID_CHUNK_SIZE && 
                    hid_rx_buffer_pos + chunk_len <= sizeof(hid_rx_buffer)) {
                    
                    memcpy(&hid_rx_buffer[hid_rx_buffer_pos], &data[10], chunk_len);
                    hid_rx_buffer_pos += chunk_len;
                    hid_received_packets++;
                }
            }
            break;
            
        case HID_CMD_LOAD_END:
            if (hid_receiving_multi_packet && 
                hid_received_packets == hid_expected_total_packets) {
                
                // Determine which type of loading to perform
                if (hid_load_type == HID_CMD_LOAD_OVERDUB_START) {
                    handle_hid_load_overdub_data(macro_num, hid_rx_buffer, hid_rx_buffer_pos);
                } else {
                    handle_hid_load_data(macro_num, hid_rx_buffer, hid_rx_buffer_pos);
                }
                
                hid_receiving_multi_packet = false;
                hid_load_type = 0; // Reset
            }
            break;

		case HID_CMD_SET_LOOP_CONFIG: // 0x40
			if (length >= 12) { // Header + 8 data bytes minimum
				handle_set_loop_config(&data[6]); // Skip header bytes
				send_hid_response(HID_CMD_SET_LOOP_CONFIG, macro_num, 0, NULL, 0); // Success
			} else {
				send_hid_response(HID_CMD_SET_LOOP_CONFIG, macro_num, 1, NULL, 0); // Error
			}
			break;

		case HID_CMD_SET_MAIN_LOOP_CCS: // 0x41
			if (length >= 26) { // Header + 20 data bytes
				handle_set_main_loop_ccs(&data[6]);
				send_hid_response(HID_CMD_SET_MAIN_LOOP_CCS, macro_num, 0, NULL, 0);
			} else {
				send_hid_response(HID_CMD_SET_MAIN_LOOP_CCS, macro_num, 1, NULL, 0);
			}
			break;

		case HID_CMD_SET_OVERDUB_CCS: // 0x42
			if (length >= 30) { // Header + 24 data bytes (CHANGED FROM 26)
				handle_set_overdub_ccs(&data[6]);
				send_hid_response(HID_CMD_SET_OVERDUB_CCS, macro_num, 0, NULL, 0);
			} else {
				send_hid_response(HID_CMD_SET_OVERDUB_CCS, macro_num, 1, NULL, 0);
			}
			break;

		case HID_CMD_SET_NAVIGATION_CONFIG: // 0x43
			if (length >= 16) { // Header + 10 data bytes
				handle_set_navigation_config(&data[6]);
				send_hid_response(HID_CMD_SET_NAVIGATION_CONFIG, macro_num, 0, NULL, 0);
			} else {
				send_hid_response(HID_CMD_SET_NAVIGATION_CONFIG, macro_num, 1, NULL, 0);
			}
			break;

		case HID_CMD_GET_ALL_CONFIG: // 0x44
			handle_get_all_config(macro_num);
			break;

		case HID_CMD_RESET_LOOP_CONFIG: // 0x45
			handle_reset_loop_config();
			send_hid_response(HID_CMD_RESET_LOOP_CONFIG, macro_num, 0, NULL, 0);
			break;

		case HID_CMD_CLEAR_ALL_LOOPS: // 0xCE
			handle_clear_all_loops();
			send_hid_response(HID_CMD_CLEAR_ALL_LOOPS, 0, 0, NULL, 0);
			break;

		case HID_CMD_SET_KEYBOARD_CONFIG: // 0x50
            if (length >= 41) { // Header + 35 data bytes minimum (expanded for velocity curve/min/max)
                handle_set_keyboard_config(&data[6]); // Skip header bytes
                send_hid_response(HID_CMD_SET_KEYBOARD_CONFIG, 0, 0, NULL, 0); // Success
            } else {
                send_hid_response(HID_CMD_SET_KEYBOARD_CONFIG, 0, 1, NULL, 0); // Error
            }
            break;
			
				// Add case to your HID handler:
		case HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED: // 0x55
			if (length >= 21) { // Header + 15 data bytes
				handle_set_keyboard_config_advanced(&data[6]);
				send_hid_response(HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED, 0, 0, NULL, 0);
			} else {
				send_hid_response(HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED, 0, 1, NULL, 0);
			}
			break;

        case HID_CMD_GET_KEYBOARD_CONFIG: // 0x51
            handle_get_keyboard_config();
            break;

        case HID_CMD_RESET_KEYBOARD_CONFIG: // 0x52
            handle_reset_keyboard_config();
            send_hid_response(HID_CMD_RESET_KEYBOARD_CONFIG, 0, 0, NULL, 0);
            break;

        case HID_CMD_SAVE_KEYBOARD_SLOT: // 0x53
            if (length >= 41) { // Header + slot + 35 data bytes minimum (expanded for velocity curve/min/max)
                handle_save_keyboard_slot(&data[6]); // Skip header bytes
                send_hid_response(HID_CMD_SAVE_KEYBOARD_SLOT, 0, 0, NULL, 0); // Success
            } else {
                send_hid_response(HID_CMD_SAVE_KEYBOARD_SLOT, 0, 1, NULL, 0); // Error
            }
            break;

        case HID_CMD_LOAD_KEYBOARD_SLOT: // 0x54
            if (length >= 7) { // Header + slot byte minimum
                handle_load_keyboard_slot(&data[6]); // Skip header bytes
                send_hid_response(HID_CMD_LOAD_KEYBOARD_SLOT, 0, 0, NULL, 0); // Success
            } else {
                send_hid_response(HID_CMD_LOAD_KEYBOARD_SLOT, 0, 1, NULL, 0); // Error
            }
            break;

        case HID_CMD_SET_KEYBOARD_PARAM_SINGLE: // 0xBD - NEW: Set individual parameter
            if (length >= 7) { // Header + param_id + at least 1 byte value
                handle_set_keyboard_param_single(&data[6]); // Skip header bytes
                send_hid_response(HID_CMD_SET_KEYBOARD_PARAM_SINGLE, 0, 0, NULL, 0); // Success
            } else {
                send_hid_response(HID_CMD_SET_KEYBOARD_PARAM_SINGLE, 0, 1, NULL, 0); // Error
            }
            break;

        // DKS Commands
        case HID_CMD_DKS_GET_SLOT: // 0xE5 - Get DKS slot configuration
            if (length >= 7) { // Header + slot number
                handle_dks_get_slot(&data[6]);
            } else {
                send_hid_response(HID_CMD_DKS_GET_SLOT, 0, 1, NULL, 0); // Error
            }
            break;

        case HID_CMD_DKS_SET_ACTION: // 0xE6 - Set a single DKS action
            if (length >= 14) { // Header + slot + action data
                handle_dks_set_action(&data[6]);
                send_hid_response(HID_CMD_DKS_SET_ACTION, 0, 0, NULL, 0); // Success
            } else {
                send_hid_response(HID_CMD_DKS_SET_ACTION, 0, 1, NULL, 0); // Error
            }
            break;

        case HID_CMD_DKS_SAVE_EEPROM: // 0xE7 - Save all DKS configs to EEPROM
            dks_save_to_eeprom();
            send_hid_response(HID_CMD_DKS_SAVE_EEPROM, 0, 0, NULL, 0); // Success
            break;

        case HID_CMD_DKS_LOAD_EEPROM: // 0xE8 - Load all DKS configs from EEPROM
            {
                bool success = dks_load_from_eeprom();
                send_hid_response(HID_CMD_DKS_LOAD_EEPROM, 0, success ? 0 : 1, NULL, 0);
            }
            break;

        case HID_CMD_DKS_RESET_SLOT: // 0xE9 - Reset a slot to defaults
            if (length >= 7) { // Header + slot number
                handle_dks_reset_slot(&data[6]);
            } else {
                send_hid_response(HID_CMD_DKS_RESET_SLOT, 0, 1, NULL, 0); // Error
            }
            break;

        case HID_CMD_DKS_RESET_ALL: // 0xEA - Reset all slots to defaults
            dks_reset_all_slots();
            send_hid_response(HID_CMD_DKS_RESET_ALL, 0, 0, NULL, 0); // Success
            break;
    }
}

uint16_t serialize_macro_data(uint8_t macro_num, uint8_t* buffer) {
    uint16_t offset = 0;
    uint8_t macro_idx = macro_num - 1;
    
    // Get macro pointers
    midi_event_t *macro_start = get_macro_buffer(macro_num);
    midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_num);
    
    if (!macro_start || !macro_end_ptr) {
        return 0;
    }
    
    // Calculate current speed factor for this macro
    float current_speed = macro_speed_factor[macro_idx];
    
    // === HEADER ===
    buffer[offset++] = 0xAA; // Magic byte 1
    buffer[offset++] = 0x55; // Magic byte 2
    buffer[offset++] = 0x01; // Version
    buffer[offset++] = macro_num; // Macro number
    
    // === MAIN MACRO DATA (with adjusted timestamps) ===
    uint32_t main_event_count = (*macro_end_ptr - macro_start);
    uint32_t main_size = main_event_count * sizeof(midi_event_t);
    buffer[offset++] = (main_size >> 8) & 0xFF; // Size high byte
    buffer[offset++] = main_size & 0xFF;        // Size low byte
    
    if (main_size > 0) {
        // Copy events with adjusted timestamps to reflect current speed
        for (uint32_t i = 0; i < main_event_count; i++) {
            midi_event_t adjusted_event = macro_start[i];
            
            // Adjust timestamp: if playing at 2x speed, timestamps should be halved
            if (current_speed > 0.0f) {
                adjusted_event.timestamp = (uint32_t)(adjusted_event.timestamp / current_speed);
            }
            
            memcpy(&buffer[offset], &adjusted_event, sizeof(midi_event_t));
            offset += sizeof(midi_event_t);
        }
    }
    
    // === OVERDUB DATA (with adjusted timestamps) ===
    uint32_t overdub_event_count = 0;
    if (overdub_buffers[macro_idx] != NULL && overdub_buffer_ends[macro_idx] != overdub_buffers[macro_idx]) {
        overdub_event_count = (overdub_buffer_ends[macro_idx] - overdub_buffers[macro_idx]);
    }
    uint32_t overdub_size = overdub_event_count * sizeof(midi_event_t);
    
    buffer[offset++] = (overdub_size >> 8) & 0xFF; // Size high byte
    buffer[offset++] = overdub_size & 0xFF;        // Size low byte
    
    if (overdub_size > 0) {
        // Copy overdub events with adjusted timestamps
        for (uint32_t i = 0; i < overdub_event_count; i++) {
            midi_event_t adjusted_event = overdub_buffers[macro_idx][i];
            
            // Adjust timestamp: if playing at 2x speed, timestamps should be halved
            if (current_speed > 0.0f) {
                adjusted_event.timestamp = (uint32_t)(adjusted_event.timestamp / current_speed);
            }
            
            memcpy(&buffer[offset], &adjusted_event, sizeof(midi_event_t));
            offset += sizeof(midi_event_t);
        }
    }
    
    // === TRANSFORMATION SETTINGS (using current recording BPM as base) ===
    buffer[offset++] = (uint8_t)macro_transpose[macro_idx];
    buffer[offset++] = (uint8_t)macro_channel_offset[macro_idx]; 
    buffer[offset++] = macro_channel_absolute[macro_idx];
    buffer[offset++] = (uint8_t)macro_velocity_offset[macro_idx];
    buffer[offset++] = macro_velocity_absolute[macro_idx];
    buffer[offset++] = (uint8_t)macro_octave_doubler[macro_idx];
    buffer[offset++] = overdub_muted[macro_idx] ? 1 : 0;
    
    // === TIMING INFO (adjusted for current speed) ===
    uint32_t adjusted_loop_length = macro_playback[macro_idx].loop_length;
    uint32_t adjusted_loop_gap = macro_playback[macro_idx].loop_gap_time;
    
    // Adjust timing to reflect current speed
    if (current_speed > 0.0f) {
        adjusted_loop_length = (uint32_t)(adjusted_loop_length / current_speed);
        adjusted_loop_gap = (uint32_t)(adjusted_loop_gap / current_speed);
    }
    
    buffer[offset++] = (adjusted_loop_length >> 24) & 0xFF;
    buffer[offset++] = (adjusted_loop_length >> 16) & 0xFF;
    buffer[offset++] = (adjusted_loop_length >> 8) & 0xFF;
    buffer[offset++] = adjusted_loop_length & 0xFF;
    
    buffer[offset++] = (adjusted_loop_gap >> 24) & 0xFF;
    buffer[offset++] = (adjusted_loop_gap >> 16) & 0xFF;
    buffer[offset++] = (adjusted_loop_gap >> 8) & 0xFF;
    buffer[offset++] = adjusted_loop_gap & 0xFF;
    
    // === BPM INFO (store current BPM as the "recording" BPM) ===
    uint8_t is_bpm_source = (bpm_source_macro == macro_num) ? 1 : 0;
    buffer[offset++] = is_bpm_source;
    
    // Store current BPM as the new "recording BPM"
    buffer[offset++] = (current_bpm >> 24) & 0xFF;
    buffer[offset++] = (current_bpm >> 16) & 0xFF;
    buffer[offset++] = (current_bpm >> 8) & 0xFF;
    buffer[offset++] = current_bpm & 0xFF;
    
    dprintf("dynamic macro: serialized macro %d data with adjusted timing (speed %.2fx): %d bytes\n", 
            macro_num, current_speed, offset);
    return offset;
}

// ============================================================================
// REPLACE THE EXISTING deserialize_macro_data FUNCTION WITH THIS:
// ============================================================================
bool deserialize_macro_data(uint8_t* buffer, uint16_t buffer_size, uint8_t expected_macro) {
    uint16_t offset = 0;
    
    // Check header
    if (buffer_size < 4 || buffer[0] != 0xAA || buffer[1] != 0x55) {
        dprintf("dynamic macro: invalid header in received data\n");
        return false;
    }
    
    uint8_t version = buffer[2];
    offset = 4;
    
    if (version != 0x01) {
        dprintf("dynamic macro: version mismatch\n");
        return false;
    }
    
    uint8_t macro_idx = expected_macro - 1;
    
    // First, completely reset target macro
    midi_event_t *target_start = get_macro_buffer(expected_macro);
    midi_event_t **target_end_ptr = get_macro_end_ptr(expected_macro);
    
    // Stop playback if active
    if (macro_playback[macro_idx].is_playing) {
        dynamic_macro_cleanup_notes_for_state(&macro_playback[macro_idx]);
        macro_playback[macro_idx].is_playing = false;
        macro_playback[macro_idx].current = NULL;
    }
    
    if (overdub_playback[macro_idx].is_playing) {
        dynamic_macro_cleanup_notes_for_state(&overdub_playback[macro_idx]);
        overdub_playback[macro_idx].is_playing = false;
        overdub_playback[macro_idx].current = NULL;
    }
    
    // Clear temp overdub data
    if (overdub_temp_count[macro_idx] > 0) {
        midi_event_t *temp_start = get_overdub_read_start(expected_macro);
        if (temp_start != NULL) {
            memset(temp_start, 0, overdub_temp_count[macro_idx] * sizeof(midi_event_t));
        }
    }
    overdub_temp_count[macro_idx] = 0;
    overdub_merge_pending[macro_idx] = false;
    
    // Reset to empty state first
    *target_end_ptr = target_start;
    overdub_buffers[macro_idx] = NULL;
    overdub_buffer_ends[macro_idx] = NULL;
    overdub_buffer_sizes[macro_idx] = 0;
    
    // Read and copy main macro data
    if (offset + 2 > buffer_size) return false;
    uint16_t main_size = (buffer[offset] << 8) | buffer[offset + 1];
    offset += 2;
    
    if (main_size > 0) {
        if (offset + main_size > buffer_size) return false;
        memcpy(target_start, &buffer[offset], main_size);
        *target_end_ptr = target_start + (main_size / sizeof(midi_event_t));
        offset += main_size;
    }
    
    // Read and copy overdub data
    if (offset + 2 > buffer_size) return false;
    uint16_t overdub_size = (buffer[offset] << 8) | buffer[offset + 1];
    offset += 2;
    
    if (overdub_size > 0) {
        uint32_t main_bytes_used = (*target_end_ptr - target_start) * sizeof(midi_event_t);
        uint32_t remaining_space = MACRO_BUFFER_SIZE - main_bytes_used;
        uint32_t overdub_events = remaining_space / sizeof(midi_event_t);
        
        if (overdub_events > 0 && overdub_size <= remaining_space) {
            overdub_buffers[macro_idx] = *target_end_ptr;
            overdub_buffer_sizes[macro_idx] = overdub_events;
            
            if (offset + overdub_size > buffer_size) return false;
            memcpy(overdub_buffers[macro_idx], &buffer[offset], overdub_size);
            overdub_buffer_ends[macro_idx] = overdub_buffers[macro_idx] + (overdub_size / sizeof(midi_event_t));
            offset += overdub_size;
        } else {
            offset += overdub_size; // Skip if no space
        }
    } else {
        // Set up empty overdub buffer
        uint32_t main_bytes_used = (*target_end_ptr - target_start) * sizeof(midi_event_t);
        uint32_t remaining_space = MACRO_BUFFER_SIZE - main_bytes_used;
        uint32_t overdub_events = remaining_space / sizeof(midi_event_t);
        
        if (overdub_events > 0) {
            overdub_buffers[macro_idx] = *target_end_ptr;
            overdub_buffer_ends[macro_idx] = *target_end_ptr;
            overdub_buffer_sizes[macro_idx] = overdub_events;
        }
    }
    
    // Read transformation settings
    if (offset + 7 > buffer_size) return false;
    macro_transpose[macro_idx] = (int8_t)buffer[offset++];
    macro_channel_offset[macro_idx] = (int8_t)buffer[offset++];
    macro_channel_absolute[macro_idx] = buffer[offset++];
    macro_velocity_offset[macro_idx] = (int8_t)buffer[offset++];
    macro_velocity_absolute[macro_idx] = buffer[offset++];
    macro_octave_doubler[macro_idx] = (int8_t)buffer[offset++];
    overdub_muted[macro_idx] = buffer[offset++] != 0;
    
    // Read timing info
    if (offset + 8 > buffer_size) return false;
    uint32_t loop_length = (buffer[offset] << 24) | (buffer[offset+1] << 16) | 
                          (buffer[offset+2] << 8) | buffer[offset+3];
    offset += 4;
    
    uint32_t loop_gap = (buffer[offset] << 24) | (buffer[offset+1] << 16) | 
                       (buffer[offset+2] << 8) | buffer[offset+3];
    offset += 4;
    
    macro_playback[macro_idx].loop_length = loop_length;
    macro_playback[macro_idx].loop_gap_time = loop_gap;
    
    // Read BPM info
    if (offset + 5 > buffer_size) return false;
    uint8_t is_bpm_source = buffer[offset++];
    uint32_t stored_bpm = (buffer[offset] << 24) | (buffer[offset+1] << 16) | 
                         (buffer[offset+2] << 8) | buffer[offset+3];
    offset += 4;
    
    // Set up BPM system for this macro
    macro_recording_bpm[macro_idx] = stored_bpm; // Use stored BPM as recording BPM
    macro_has_content[macro_idx] = true;
    macro_manual_speed[macro_idx] = 1.0f; // Reset to 1.0x speed
    
    if (is_bpm_source && stored_bpm > 0) {
        current_bpm = stored_bpm;
        bpm_source_macro = expected_macro;
        dprintf("dynamic macro: restored BPM %lu from macro %d\n", current_bpm / 100000, expected_macro);
    }
    
    // Initialize overdub playback timing if overdub exists
    if (overdub_buffers[macro_idx] != NULL) {
        overdub_playback[macro_idx].buffer_start = overdub_buffers[macro_idx];
        overdub_playback[macro_idx].loop_length = loop_length;
        overdub_playback[macro_idx].loop_gap_time = loop_gap;
    }
    
    // Reset targets to match current values
    macro_transpose_target[macro_idx] = macro_transpose[macro_idx];
    macro_channel_offset_target[macro_idx] = macro_channel_offset[macro_idx];
    macro_channel_absolute_target[macro_idx] = macro_channel_absolute[macro_idx];
    macro_velocity_offset_target[macro_idx] = macro_velocity_offset[macro_idx];
    macro_velocity_absolute_target[macro_idx] = macro_velocity_absolute[macro_idx];
    macro_octave_doubler_target[macro_idx] = macro_octave_doubler[macro_idx];
    
    dprintf("dynamic macro: successfully loaded data into macro %d with recording BPM %lu\n", 
            expected_macro, stored_bpm / 100000);
    return true;
}

// Function to clear only the overdub section (extracted from matrix_scan logic)
static void clear_overdub_only(uint8_t macro_num) {
    if (macro_num < 1 || macro_num > MAX_MACROS) return;
    
    uint8_t macro_idx = macro_num - 1;
    
    // Stop overdub playback AND send note-offs
    if (overdub_playback[macro_idx].is_playing) {
        // Send note-offs for all overdub notes before stopping
        cleanup_notes_from_macro(macro_num + MAX_MACROS);
        
        // Now stop the playback state
        overdub_playback[macro_idx].is_playing = false;
        overdub_playback[macro_idx].current = NULL;
        overdub_playback[macro_idx].waiting_for_loop_gap = false;
    }
    
    // Clear temp overdub data
    if (overdub_temp_count[macro_idx] > 0) {
        midi_event_t *temp_start = get_overdub_read_start(macro_num);
        if (temp_start != NULL) {
            memset(temp_start, 0, overdub_temp_count[macro_idx] * sizeof(midi_event_t));
        }
    }
    overdub_temp_count[macro_idx] = 0;
    overdub_merge_pending[macro_idx] = false;
    
    // Clear overdub mode state completely
    macro_in_overdub_mode[macro_idx] = false;
    
    // Reset overdub target if this was the target
    if (overdub_target_macro == macro_num) {
        overdub_target_macro = 0;
        current_macro_id = 0;
        macro_id = 0;
        stop_dynamic_macro_recording();
    }
    
    // Clear any pending overdub operations
    overdub_mute_pending[macro_idx] = false;
    overdub_unmute_pending[macro_idx] = false;
    
    if (overdub_buffers[macro_idx] != NULL) {
        // Reset end pointer to start pointer (making it empty but keeping allocation)
        overdub_buffer_ends[macro_idx] = overdub_buffers[macro_idx];
        
        // Keep overdub_buffers[macro_idx] and overdub_buffer_sizes[macro_idx] unchanged (match fresh macro allocation)
        // Reset muted state to initial (unmuted)
        overdub_muted[macro_idx] = false;
        
        // COMPLETE overdub playback state reset to match fresh macro state
        overdub_playback[macro_idx].buffer_start = overdub_buffers[macro_idx];
        overdub_playback[macro_idx].loop_length = macro_playback[macro_idx].loop_length;
        overdub_playback[macro_idx].loop_gap_time = macro_playback[macro_idx].loop_gap_time;
        overdub_playback[macro_idx].current = NULL;
        overdub_playback[macro_idx].end = overdub_buffer_ends[macro_idx];
        overdub_playback[macro_idx].is_playing = false;
        overdub_playback[macro_idx].waiting_for_loop_gap = false;
        overdub_playback[macro_idx].direction = +1;
        overdub_playback[macro_idx].timer = 0;
        overdub_playback[macro_idx].next_event_time = 0;
    } else {
        // No overdub buffer was allocated - this shouldn't happen for a recorded macro
        dprintf("WARNING: No overdub buffer found for macro %d during overdub deletion\n", macro_num);
    }
    
    force_clear_all_live_notes();
    
    dprintf("dynamic macro: RESET OVERDUBS ONLY - macro %d overdub section cleared\n", macro_num);
}

// Deserialize overdub-only data (modified version of deserialize_macro_data)
bool deserialize_overdub_data(uint8_t* buffer, uint16_t buffer_size, uint8_t expected_macro) {
    uint16_t offset = 0;
    
    // Check header
    if (buffer_size < 4 || buffer[0] != 0xAA || buffer[1] != 0x55) {
        dprintf("dynamic macro: invalid header in received overdub data\n");
        return false;
    }
    
    uint8_t version = buffer[2];
    uint8_t macro_num = buffer[3];
    offset = 4;
    
	if (version != 0x01) {
		dprintf("dynamic macro: version mismatch\n");
		return false;
	}
    
    uint8_t macro_idx = macro_num - 1;
    
    // Clear only the overdub section
    clear_overdub_only(macro_num);
    
    // Skip main macro size (we don't need it for overdub-only loading)
    if (offset + 2 > buffer_size) return false;
    uint16_t main_size = (buffer[offset] << 8) | buffer[offset + 1];
    offset += 2;
    offset += main_size; // Skip main macro data
    
    // Read overdub size
    if (offset + 2 > buffer_size) return false;
    uint16_t overdub_size = (buffer[offset] << 8) | buffer[offset + 1];
    offset += 2;
    
    // Set up overdub buffer if we have data to load
    if (overdub_size > 0) {
        // Check if we have an existing main macro to determine remaining space
        midi_event_t *target_start = get_macro_buffer(macro_num);
        midi_event_t **target_end_ptr = get_macro_end_ptr(macro_num);
        
        uint32_t main_bytes_used = (*target_end_ptr - target_start) * sizeof(midi_event_t);
        uint32_t remaining_space = MACRO_BUFFER_SIZE - main_bytes_used;
        uint32_t overdub_events = remaining_space / sizeof(midi_event_t);
        
        if (overdub_events > 0 && overdub_size <= remaining_space) {
            overdub_buffers[macro_idx] = *target_end_ptr;
            overdub_buffer_sizes[macro_idx] = overdub_events;
            
            if (offset + overdub_size > buffer_size) return false;
            memcpy(overdub_buffers[macro_idx], &buffer[offset], overdub_size);
            overdub_buffer_ends[macro_idx] = overdub_buffers[macro_idx] + (overdub_size / sizeof(midi_event_t));
            offset += overdub_size;
            
            dprintf("dynamic macro: loaded overdub data (%d bytes) for macro %d\n", overdub_size, macro_num);
        } else {
            dprintf("dynamic macro: insufficient space for overdub data in macro %d\n", macro_num);
            offset += overdub_size; // Skip if no space
            return false;
        }
    } else {
        // No overdub content - ensure we have an empty overdub buffer set up
        midi_event_t *target_start = get_macro_buffer(macro_num);
        midi_event_t **target_end_ptr = get_macro_end_ptr(macro_num);
        
        uint32_t main_bytes_used = (*target_end_ptr - target_start) * sizeof(midi_event_t);
        uint32_t remaining_space = MACRO_BUFFER_SIZE - main_bytes_used;
        uint32_t overdub_events = remaining_space / sizeof(midi_event_t);
        
        if (overdub_events > 0) {
            overdub_buffers[macro_idx] = *target_end_ptr;
            overdub_buffer_ends[macro_idx] = *target_end_ptr; // Empty
            overdub_buffer_sizes[macro_idx] = overdub_events;
        }
        
        dprintf("dynamic macro: set up empty overdub buffer for macro %d\n", macro_num);
    }
    
    // Skip transformation settings (we don't change main macro settings for overdub-only load)
    if (offset + 7 > buffer_size) return false;
    offset += 6; // Skip transpose, channel_offset, channel_absolute, velocity_offset, velocity_absolute, octave_doubler
    overdub_muted[macro_idx] = buffer[offset++] != 0; // Only apply the muted state
    
    // Skip timing info (don't change main macro timing)
    if (offset + 8 > buffer_size) return false;
    offset += 8; // Skip loop_length and loop_gap
    
    // Skip BPM info (don't change BPM settings)
    if (offset + 5 > buffer_size) return false;
    offset += 5; // Skip BPM data
    
    // Initialize overdub playback timing if overdub exists (use existing main macro timing)
    if (overdub_buffers[macro_idx] != NULL) {
        overdub_playback[macro_idx].buffer_start = overdub_buffers[macro_idx];
        overdub_playback[macro_idx].loop_length = macro_playback[macro_idx].loop_length;
        overdub_playback[macro_idx].loop_gap_time = macro_playback[macro_idx].loop_gap_time;
    }
    
    dprintf("dynamic macro: successfully loaded overdub-only data into macro %d\n", macro_num);
    return true;
}

// Handle overdub load data from web app
static void handle_hid_load_overdub_data(uint8_t macro_num, const uint8_t* data, uint16_t data_len) {
    dprintf("Loading overdub %d bytes to macro %d\n", data_len, macro_num);
    
    // Deserialize and load overdub only
    if (deserialize_overdub_data((uint8_t*)data, data_len, macro_num)) {
        send_hid_response(HID_CMD_LOAD_END, macro_num, 0, NULL, 0); // Success
        dprintf("Successfully loaded overdub for macro %d\n", macro_num);
    } else {
        send_hid_response(HID_CMD_LOAD_END, macro_num, 1, NULL, 0); // Error
        dprintf("Failed to load overdub for macro %d\n", macro_num);
    }
}

static midi_event_t* find_event_at_position(macro_playback_state_t *state, uint32_t position_ms) {
    if (!state->buffer_start || !state->end || state->buffer_start >= state->end) {
        return NULL;
    }
    
    // Look for the first event at or after the target position in loop timeline
    for (midi_event_t *event = state->buffer_start; event < state->end; event++) {
        if (event->timestamp >= position_ms) {
            return event;
        }
    }
    
    // No events found at or after this position
    // This means we're in the gap at the end of the loop
    return NULL;
}

// Navigate a single macro's playback state by a relative time offset
static void navigate_macro_playback_state(macro_playback_state_t *state, int32_t time_offset_ms, uint32_t current_time, uint8_t macro_idx) {
    if (!state->is_playing || state->loop_length == 0) {
        return;
    }
    
    // Check if this is an independent overdub in advanced mode
    bool is_independent_overdub = false;
    uint8_t overdub_idx = 0;
    if (overdub_advanced_mode) {
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (state->buffer_start == overdub_buffers[i] && overdub_independent_loop_length[i] > 0) {
                is_independent_overdub = true;
                overdub_idx = i;
                break;
            }
        }
    }
    
    // Get the speed factor for this macro
    float speed_factor = macro_speed_factor[macro_idx];
    
    if (speed_factor <= 0.0f) {
        dprintf("dynamic macro: skipping navigation for macro %d (paused or invalid speed)\n", macro_idx + 1);
        return; // Can't navigate paused macros
    }
    
    // Calculate current real-time position relative to playback start
    uint32_t current_real_elapsed;
    
    if (is_independent_overdub) {
        // Use independent timer for advanced mode overdubs
        current_real_elapsed = current_time - overdub_independent_timer[overdub_idx];
        dprintf("dynamic macro: using independent timer for overdub %d (elapsed: %lu ms)\n", 
                macro_idx + 1, current_real_elapsed);
    } else {
        // Use regular timer for main macros and synced overdubs
        current_real_elapsed = current_time - state->timer;
    }
    
    // Apply navigation offset in real-time
    int64_t new_real_elapsed = (int64_t)current_real_elapsed + time_offset_ms;
    
    // Calculate real-world loop duration (how long the loop takes in real time)
    uint32_t real_loop_duration = (uint32_t)(state->loop_length / speed_factor);
    
    // Handle wrapping for real-time navigation
    while (new_real_elapsed < 0) {
        new_real_elapsed += real_loop_duration;
    }
    while (new_real_elapsed >= (int64_t)real_loop_duration) {
        new_real_elapsed -= real_loop_duration;
    }
    
    uint32_t new_real_elapsed_final = (uint32_t)new_real_elapsed;
    
    // Convert real-time position back to loop timeline position
    uint32_t new_loop_position = (uint32_t)(new_real_elapsed_final * speed_factor);
    
    // Ensure loop position stays within bounds
    if (new_loop_position >= state->loop_length) {
        new_loop_position = new_loop_position % state->loop_length;
    }
    
    // Find the appropriate event to start from at the new loop position
    midi_event_t *target_event = find_event_at_position(state, new_loop_position);
    
    if (target_event) {
        // Update playback state to new position
        state->current = target_event;
        state->timer = current_time - new_real_elapsed_final;
        
        // CRITICAL: Also update independent timer for advanced mode overdubs
        if (is_independent_overdub) {
            overdub_independent_timer[overdub_idx] = current_time - new_real_elapsed_final;
            dprintf("dynamic macro: updated independent timer for overdub %d to match new position\n", 
                    macro_idx + 1);
        }
        
        state->waiting_for_loop_gap = false;
        
        // Calculate next event time accounting for speed
        uint32_t time_to_event_in_loop = target_event->timestamp - new_loop_position;
        uint32_t real_time_to_event = (uint32_t)(time_to_event_in_loop / speed_factor);
        state->next_event_time = current_time + real_time_to_event;
        
        dprintf("dynamic macro: positioned at %lu ms real-time (%lu ms loop position, target event at %lu ms)\n", 
                new_real_elapsed_final, new_loop_position, target_event->timestamp);
    } else {
        // No events at this position - we're in a gap, wait for next cycle
        state->waiting_for_loop_gap = true;
        state->timer = current_time - new_real_elapsed_final;
        
        // CRITICAL: Also update independent timer for advanced mode overdubs
        if (is_independent_overdub) {
            overdub_independent_timer[overdub_idx] = current_time - new_real_elapsed_final;
            dprintf("dynamic macro: updated independent timer for overdub %d (gap wait)\n", 
                    macro_idx + 1);
        }
        
        uint32_t real_time_to_loop_end = real_loop_duration - new_real_elapsed_final;
        state->next_event_time = current_time + real_time_to_loop_end;
        
        dprintf("dynamic macro: positioned in gap at %lu ms real-time (%lu ms loop position), waiting %lu ms for loop restart\n", 
                new_real_elapsed_final, new_loop_position, real_time_to_loop_end);
    }
}

// Navigate all currently playing macros by a time offset (in milliseconds)
// This function now supports advanced overdub mode with independent loop timings
static void navigate_all_macros(int32_t time_offset_ms) {
    dprintf("dynamic macro: navigating all macros by %ld ms\n", time_offset_ms);
    
    // Clean up all hanging notes before navigation
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_playback[i].is_playing) {
            cleanup_notes_from_macro(i + 1);
        }
        if (overdub_playback[i].is_playing) {
            cleanup_notes_from_macro(i + 1 + MAX_MACROS);
        }
    }
    
    uint32_t current_time = timer_read32();
    
    // Navigate main macros
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (macro_playback[i].is_playing) {
            navigate_macro_playback_state(&macro_playback[i], time_offset_ms, current_time, i);
            dprintf("dynamic macro: navigated main macro %d\n", i + 1);
        }
    }
    
    // Navigate overdubs - behavior depends on mode
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (overdub_playback[i].is_playing) {
            // In advanced mode with independent loop timing, navigate the overdub
            // by the same offset - the navigate_macro_playback_state function
            // will handle the independent timer and loop length automatically
            navigate_macro_playback_state(&overdub_playback[i], time_offset_ms, current_time, i);
            
            if (overdub_advanced_mode && overdub_independent_loop_length[i] > 0) {
                dprintf("dynamic macro: navigated overdub %d (advanced mode - independent timing)\n", i + 1);
            } else {
                dprintf("dynamic macro: navigated overdub %d (synced mode)\n", i + 1);
            }
        }
    }
    
    // Update pause timestamps if currently paused (so pause state stays consistent)
    if (global_playback_paused) {
        for (uint8_t i = 0; i < MAX_MACROS; i++) {
            if (macro_playback[i].is_playing && macro_playback[i].loop_length > 0) {
                float speed_factor = macro_speed_factor[i];
                if (speed_factor <= 0.0f) continue;
                
                // Calculate new pause position for main macro
                uint32_t real_loop_duration = (uint32_t)(macro_playback[i].loop_length / speed_factor);
                uint32_t current_real_position = pause_timestamps[i] / speed_factor;
                
                int64_t new_real_position = (int64_t)current_real_position + time_offset_ms;
                
                // Handle wrapping
                while (new_real_position < 0) {
                    new_real_position += real_loop_duration;
                }
                while (new_real_position >= (int64_t)real_loop_duration) {
                    new_real_position -= real_loop_duration;
                }
                
                uint32_t new_loop_position = (uint32_t)((uint32_t)new_real_position * speed_factor);
                if (new_loop_position >= macro_playback[i].loop_length) {
                    new_loop_position = new_loop_position % macro_playback[i].loop_length;
                }
                
                pause_timestamps[i] = new_loop_position;
                
                // Update overdub pause position - depends on mode
                if (overdub_playback[i].is_playing && overdub_playback[i].loop_length > 0) {
                    uint32_t overdub_real_loop_duration = (uint32_t)(overdub_playback[i].loop_length / speed_factor);
                    uint32_t overdub_current_real_position = overdub_pause_timestamps[i] / speed_factor;
                    
                    int64_t overdub_new_real_position = (int64_t)overdub_current_real_position + time_offset_ms;
                    
                    // Handle wrapping
                    while (overdub_new_real_position < 0) {
                        overdub_new_real_position += overdub_real_loop_duration;
                    }
                    while (overdub_new_real_position >= (int64_t)overdub_real_loop_duration) {
                        overdub_new_real_position -= overdub_real_loop_duration;
                    }
                    
                    uint32_t overdub_new_loop_position = (uint32_t)((uint32_t)overdub_new_real_position * speed_factor);
                    if (overdub_new_loop_position >= overdub_playback[i].loop_length) {
                        overdub_new_loop_position = overdub_new_loop_position % overdub_playback[i].loop_length;
                    }
                    
                    overdub_pause_timestamps[i] = overdub_new_loop_position;
                }
                
                dprintf("dynamic macro: updated pause position for macro %d to %lu ms (offset: %ld ms)\n", 
                        i + 1, new_loop_position, time_offset_ms);
            }
        }
    }
}

// Update handle_set_keyboard_config to only handle basic settings (packet 1)
static void handle_set_keyboard_config(const uint8_t* data) {
    const uint8_t* ptr = data;
    
    // Read 32-bit integers (little endian)
    velocity_sensitivity = *(int32_t*)ptr; ptr += 4;
    cc_sensitivity = *(int32_t*)ptr; ptr += 4;
    
    // Read single bytes
    channel_number = *ptr++;
    transpose_number = *(int8_t*)ptr++;
    octave_number = *(int8_t*)ptr++;
    transpose_number2 = *(int8_t*)ptr++;
    octave_number2 = *(int8_t*)ptr++;
    transpose_number3 = *(int8_t*)ptr++;
    octave_number3 = *(int8_t*)ptr++;
    dynamic_range = *ptr++;

    // Read 32-bit integer for oledkeyboard
    oledkeyboard = *(int32_t*)ptr; ptr += 4;
    
    // Read remaining single bytes
    overdub_advanced_mode = *ptr++;
    smartchordlightmode = *ptr++;
    
    // Update basic keyboard settings structure
    keyboard_settings.velocity_sensitivity = velocity_sensitivity;
    keyboard_settings.cc_sensitivity = cc_sensitivity;
    keyboard_settings.channel_number = channel_number;
    keyboard_settings.transpose_number = transpose_number;
    keyboard_settings.octave_number = octave_number;
    keyboard_settings.transpose_number2 = transpose_number2;
    keyboard_settings.octave_number2 = octave_number2;
    keyboard_settings.transpose_number3 = transpose_number3;
    keyboard_settings.octave_number3 = octave_number3;
    keyboard_settings.dynamic_range = dynamic_range;
    keyboard_settings.oledkeyboard = oledkeyboard;
    keyboard_settings.overdub_advanced_mode = overdub_advanced_mode;
    keyboard_settings.smartchordlightmode = smartchordlightmode;
    
    dprintf("HID: Updated basic keyboard config\n");
}


// Add a static variable to track pending slot saves
static uint8_t pending_slot_save = 255; // 255 = no pending save

// New function for advanced settings (packet 2)
static void handle_set_keyboard_config_advanced(const uint8_t* data) {
    const uint8_t* ptr = data;
    
    // Read keysplit settings
    keysplitchannel = *ptr++;
    keysplit2channel = *ptr++;
    keysplitstatus = *ptr++;
    keysplittransposestatus = *ptr++;
    keysplitvelocitystatus = *ptr++;
    
    // Read boolean settings
    custom_layer_animations_enabled = (*ptr++ != 0);
    unsynced_mode_active = *ptr++;
    sample_mode_active = (*ptr++ != 0);
    
    // Read loop messaging features
    loop_messaging_enabled = (*ptr++ != 0);
    loop_messaging_channel = *ptr++;
    sync_midi_mode = (*ptr++ != 0);
    alternate_restart_mode = (*ptr++ != 0);
    colorblindmode = *ptr++;
    cclooprecording = (*ptr++ != 0);
    truesustain = (*ptr++ != 0);
    
    // Update advanced keyboard settings structure
    keyboard_settings.keysplitchannel = keysplitchannel;
    keyboard_settings.keysplit2channel = keysplit2channel;
    keyboard_settings.keysplitstatus = keysplitstatus;
    keyboard_settings.keysplittransposestatus = keysplittransposestatus;
    keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
    keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
    keyboard_settings.unsynced_mode_active = unsynced_mode_active;
    keyboard_settings.sample_mode_active = sample_mode_active;
    keyboard_settings.loop_messaging_enabled = loop_messaging_enabled;
    keyboard_settings.loop_messaging_channel = loop_messaging_channel;
    keyboard_settings.sync_midi_mode = sync_midi_mode;
    keyboard_settings.alternate_restart_mode = alternate_restart_mode;
    keyboard_settings.colorblindmode = colorblindmode;
    keyboard_settings.cclooprecording = cclooprecording;
    keyboard_settings.truesustain = truesustain;
    
    if (pending_slot_save != 255) {
        save_keyboard_settings_to_slot(pending_slot_save);
        dprintf("HID: Completed save to slot %d with both basic and advanced settings\n", pending_slot_save);
        pending_slot_save = 255; // Clear pending save
    } else {
        // Regular advanced settings update (not part of slot save)
        save_keyboard_settings(); // Save to current active settings
    }
    
    dprintf("HID: Updated advanced keyboard config\n");
}

// NEW: Handle individual parameter updates (real-time updates without full batch)
static void handle_set_keyboard_param_single(const uint8_t* data) {
    uint8_t param_id = data[0];
    const uint8_t* value_ptr = &data[1];

    switch (param_id) {
        // 1-byte parameters
        case PARAM_CHANNEL_NUMBER:
            channel_number = *value_ptr;
            keyboard_settings.channel_number = channel_number;
            break;
        case PARAM_TRANSPOSE_NUMBER:
            transpose_number = (int8_t)(*value_ptr);
            keyboard_settings.transpose_number = transpose_number;
            break;
        case PARAM_TRANSPOSE_NUMBER2:
            transpose_number2 = (int8_t)(*value_ptr);
            keyboard_settings.transpose_number2 = transpose_number2;
            break;
        case PARAM_TRANSPOSE_NUMBER3:
            transpose_number3 = (int8_t)(*value_ptr);
            keyboard_settings.transpose_number3 = transpose_number3;
            break;
        case PARAM_HE_VELOCITY_CURVE:
            keyboard_settings.he_velocity_curve = *value_ptr;
            break;
        case PARAM_HE_VELOCITY_MIN:
            keyboard_settings.he_velocity_min = *value_ptr;
            break;
        case PARAM_HE_VELOCITY_MAX:
            keyboard_settings.he_velocity_max = *value_ptr;
            break;
        case PARAM_KEYSPLIT_HE_VELOCITY_CURVE:
            keyboard_settings.keysplit_he_velocity_curve = *value_ptr;
            break;
        case PARAM_KEYSPLIT_HE_VELOCITY_MIN:
            keyboard_settings.keysplit_he_velocity_min = *value_ptr;
            break;
        case PARAM_KEYSPLIT_HE_VELOCITY_MAX:
            keyboard_settings.keysplit_he_velocity_max = *value_ptr;
            break;
        case PARAM_TRIPLESPLIT_HE_VELOCITY_CURVE:
            keyboard_settings.triplesplit_he_velocity_curve = *value_ptr;
            break;
        case PARAM_TRIPLESPLIT_HE_VELOCITY_MIN:
            keyboard_settings.triplesplit_he_velocity_min = *value_ptr;
            break;
        case PARAM_TRIPLESPLIT_HE_VELOCITY_MAX:
            keyboard_settings.triplesplit_he_velocity_max = *value_ptr;
            break;
        // PARAM_AFTERTOUCH_MODE and PARAM_AFTERTOUCH_CC are now per-layer
        // Use layer actuation protocol (0xCA/0xCB) instead
        case PARAM_BASE_SUSTAIN:
            base_sustain = *value_ptr;
            keyboard_settings.base_sustain = base_sustain;
            break;
        case PARAM_KEYSPLIT_SUSTAIN:
            keysplit_sustain = *value_ptr;
            keyboard_settings.keysplit_sustain = keysplit_sustain;
            break;
        case PARAM_TRIPLESPLIT_SUSTAIN:
            triplesplit_sustain = *value_ptr;
            keyboard_settings.triplesplit_sustain = triplesplit_sustain;
            break;
        case PARAM_KEYSPLITCHANNEL:
            keysplitchannel = *value_ptr;
            keyboard_settings.keysplitchannel = keysplitchannel;
            break;
        case PARAM_KEYSPLIT2CHANNEL:
            keysplit2channel = *value_ptr;
            keyboard_settings.keysplit2channel = keysplit2channel;
            break;
        case PARAM_KEYSPLITSTATUS:
            keysplitstatus = *value_ptr;
            keyboard_settings.keysplitstatus = keysplitstatus;
            break;
        case PARAM_KEYSPLITTRANSPOSESTATUS:
            keysplittransposestatus = *value_ptr;
            keyboard_settings.keysplittransposestatus = keysplittransposestatus;
            break;
        case PARAM_KEYSPLITVELOCITYSTATUS:
            keysplitvelocitystatus = *value_ptr;
            keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
            break;

        // 4-byte parameters
        case PARAM_VELOCITY_SENSITIVITY:
            velocity_sensitivity = *(int32_t*)value_ptr;
            keyboard_settings.velocity_sensitivity = velocity_sensitivity;
            break;
        case PARAM_CC_SENSITIVITY:
            cc_sensitivity = *(int32_t*)value_ptr;
            keyboard_settings.cc_sensitivity = cc_sensitivity;
            break;

        // Hall Effect Sensor Linearization
        case PARAM_LUT_CORRECTION_STRENGTH:
            lut_correction_strength = *value_ptr;
            if (lut_correction_strength > 100) lut_correction_strength = 100;
            keyboard_settings.lut_correction_strength = lut_correction_strength;
            break;

        default:
            dprintf("HID: Unknown param_id: %d\n", param_id);
            return;
    }

    dprintf("HID: Updated single parameter %d\n", param_id);
}


static void handle_get_keyboard_config(void) {
    load_keyboard_settings();
    
    // Packet 1: Basic settings (35 bytes - expanded for velocity curve/min/max)
    uint8_t config_packet1[35];
    uint8_t* ptr = config_packet1;

    *(int32_t*)ptr = keyboard_settings.velocity_sensitivity; ptr += 4;
    *(int32_t*)ptr = keyboard_settings.cc_sensitivity; ptr += 4;
    *ptr++ = keyboard_settings.channel_number;
    *(int8_t*)ptr++ = keyboard_settings.transpose_number;
    *(int8_t*)ptr++ = keyboard_settings.octave_number;
    *(int8_t*)ptr++ = keyboard_settings.transpose_number2;
    *(int8_t*)ptr++ = keyboard_settings.octave_number2;
    *(int8_t*)ptr++ = keyboard_settings.transpose_number3;
    *(int8_t*)ptr++ = keyboard_settings.octave_number3;
    *ptr++ = keyboard_settings.dynamic_range;
    *(int32_t*)ptr = keyboard_settings.oledkeyboard; ptr += 4;
    *ptr++ = keyboard_settings.overdub_advanced_mode;
    *ptr++ = keyboard_settings.smartchordlightmode;

    send_hid_response(HID_CMD_GET_KEYBOARD_CONFIG, 0, 0, config_packet1, 22);
    wait_ms(5);
    
    // Packet 2: Advanced settings (15 bytes)
    uint8_t config_packet2[15];
    ptr = config_packet2;
    
    *ptr++ = keyboard_settings.keysplitchannel;
    *ptr++ = keyboard_settings.keysplit2channel;
    *ptr++ = keyboard_settings.keysplitstatus;
    *ptr++ = keyboard_settings.keysplittransposestatus;
    *ptr++ = keyboard_settings.keysplitvelocitystatus;
    *ptr++ = keyboard_settings.custom_layer_animations_enabled ? 1 : 0;
    *ptr++ = keyboard_settings.unsynced_mode_active;
    *ptr++ = keyboard_settings.sample_mode_active ? 1 : 0;
    *ptr++ = keyboard_settings.loop_messaging_enabled ? 1 : 0;
    *ptr++ = keyboard_settings.loop_messaging_channel;
    *ptr++ = keyboard_settings.sync_midi_mode ? 1 : 0;
    *ptr++ = keyboard_settings.alternate_restart_mode ? 1 : 0;
    *ptr++ = keyboard_settings.colorblindmode;
    *ptr++ = keyboard_settings.cclooprecording ? 1 : 0;
    *ptr++ = keyboard_settings.truesustain ? 1 : 0;
    
    send_hid_response(HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED, 0, 0, config_packet2, 15);
    
    dprintf("HID: Sent keyboard configuration to web app (2 packets)\n");
}

// Reset keyboard configuration to defaults
static void handle_reset_keyboard_config(void) {
    // Reset to default values
    velocity_sensitivity = 1;
    cc_sensitivity = 1;
    channel_number = 0;
    transpose_number = 0;
    octave_number = 0;
    transpose_number2 = 0;
    octave_number2 = 0;
    transpose_number3 = 0;
    octave_number3 = 0;
    dynamic_range = 127;  // Default: maximum range allowed
    oledkeyboard = 0;
    overdub_advanced_mode = false;
    smartchordlightmode = 0;
    keysplitchannel = 0;
    keysplit2channel = 0;
    keysplitstatus = 0;
    keysplittransposestatus = 0;
    keysplitvelocitystatus = 0;
    custom_layer_animations_enabled = false;
    sample_mode_active = false;
    unsynced_mode_active = 0;
    colorblindmode = 0;
	cclooprecording = false;
	truesustain = false;
    // Reset new loop messaging features to defaults
    loop_messaging_enabled = false;
    loop_messaging_channel = 16;  // Default to MIDI channel 16
    sync_midi_mode = false;
    alternate_restart_mode = false;
    
    // Update keyboard settings structure
    keyboard_settings.velocity_sensitivity = velocity_sensitivity;
    keyboard_settings.cc_sensitivity = cc_sensitivity;
    keyboard_settings.channel_number = channel_number;
    keyboard_settings.transpose_number = transpose_number;
    keyboard_settings.octave_number = octave_number;
    keyboard_settings.transpose_number2 = transpose_number2;
    keyboard_settings.octave_number2 = octave_number2;
    keyboard_settings.transpose_number3 = transpose_number3;
    keyboard_settings.octave_number3 = octave_number3;
    keyboard_settings.dynamic_range = dynamic_range;
    keyboard_settings.oledkeyboard = oledkeyboard;
    keyboard_settings.overdub_advanced_mode = overdub_advanced_mode;
    keyboard_settings.smartchordlightmode = smartchordlightmode;
    keyboard_settings.keysplitchannel = keysplitchannel;
    keyboard_settings.keysplit2channel = keysplit2channel;
    keyboard_settings.keysplitstatus = keysplitstatus;
    keyboard_settings.keysplittransposestatus = keysplittransposestatus;
    keyboard_settings.keysplitvelocitystatus = keysplitvelocitystatus;
    keyboard_settings.custom_layer_animations_enabled = custom_layer_animations_enabled;
    keyboard_settings.unsynced_mode_active = unsynced_mode_active;
    keyboard_settings.sample_mode_active = sample_mode_active;
    
    // Update new loop messaging features
    keyboard_settings.loop_messaging_enabled = loop_messaging_enabled;
    keyboard_settings.loop_messaging_channel = loop_messaging_channel;
    keyboard_settings.sync_midi_mode = sync_midi_mode;
    keyboard_settings.alternate_restart_mode = alternate_restart_mode;
	keyboard_settings.colorblindmode = colorblindmode;
	keyboard_settings.cclooprecording = cclooprecording;
	keyboard_settings.truesustain = truesustain;
    
    // Save to EEPROM
    save_keyboard_settings();
    
    dprintf("HID: Reset keyboard configuration to defaults\n");
}

static void handle_save_keyboard_slot(const uint8_t* data) {
    uint8_t slot = data[0];
    
    if (slot > 4) {
        dprintf("HID: Invalid keyboard slot %d\n", slot);
        return;
    }
    
    // Update current settings from the remaining data
    handle_set_keyboard_config(&data[1]);
    
    // DON'T save yet - wait for the advanced packet
    pending_slot_save = slot;
    
    dprintf("HID: Prepared basic settings for slot %d, waiting for advanced settings\n", slot);
}

// Load keyboard configuration from specific slot
static void handle_load_keyboard_slot(const uint8_t* data) {
    uint8_t slot = data[0];  // First byte is the slot number (0-4)
    
    // Validate slot number
    if (slot > 4) {
        dprintf("HID: Invalid keyboard slot %d\n", slot);
        return;
    }
    
    // Load from the specific slot
    load_keyboard_settings_from_slot(slot);
    
    dprintf("HID: Loaded keyboard config from slot %d\n", slot);
    
    // Send the loaded configuration back to the webapp using two packets
    // Packet 1: Basic settings (35 bytes - expanded for velocity curve/min/max)
    uint8_t config_packet1[35];
    uint8_t* ptr = config_packet1;

    *(int32_t*)ptr = keyboard_settings.velocity_sensitivity; ptr += 4;
    *(int32_t*)ptr = keyboard_settings.cc_sensitivity; ptr += 4;
    *ptr++ = keyboard_settings.channel_number;
    *(int8_t*)ptr++ = keyboard_settings.transpose_number;
    *(int8_t*)ptr++ = keyboard_settings.octave_number;
    *(int8_t*)ptr++ = keyboard_settings.transpose_number2;
    *(int8_t*)ptr++ = keyboard_settings.octave_number2;
    *(int8_t*)ptr++ = keyboard_settings.transpose_number3;
    *(int8_t*)ptr++ = keyboard_settings.octave_number3;
    *ptr++ = keyboard_settings.dynamic_range;
    *(int32_t*)ptr = keyboard_settings.oledkeyboard; ptr += 4;
    *ptr++ = keyboard_settings.overdub_advanced_mode;
    *ptr++ = keyboard_settings.smartchordlightmode;

    send_hid_response(HID_CMD_GET_KEYBOARD_CONFIG, 0, 0, config_packet1, 22);
    wait_ms(5);
    
    // Packet 2: Advanced settings (15 bytes) - FIXED: Actually fill and send the packet
    uint8_t config_packet2[15];
    ptr = config_packet2;
    
    *ptr++ = keyboard_settings.keysplitchannel;
    *ptr++ = keyboard_settings.keysplit2channel;
    *ptr++ = keyboard_settings.keysplitstatus;
    *ptr++ = keyboard_settings.keysplittransposestatus;
    *ptr++ = keyboard_settings.keysplitvelocitystatus;
    *ptr++ = keyboard_settings.custom_layer_animations_enabled ? 1 : 0;
    *ptr++ = keyboard_settings.unsynced_mode_active;
    *ptr++ = keyboard_settings.sample_mode_active ? 1 : 0;
    *ptr++ = keyboard_settings.loop_messaging_enabled ? 1 : 0;
    *ptr++ = keyboard_settings.loop_messaging_channel;
    *ptr++ = keyboard_settings.sync_midi_mode ? 1 : 0;
    *ptr++ = keyboard_settings.alternate_restart_mode ? 1 : 0;
    *ptr++ = keyboard_settings.colorblindmode;
    *ptr++ = keyboard_settings.cclooprecording ? 1 : 0;
    *ptr++ = keyboard_settings.truesustain ? 1 : 0;
    
    send_hid_response(HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED, 0, 0, config_packet2, 15);
    
    // FIXED: Now update global variables AFTER sending both packets
    velocity_sensitivity = keyboard_settings.velocity_sensitivity;
    cc_sensitivity = keyboard_settings.cc_sensitivity;
    channel_number = keyboard_settings.channel_number;
    transpose_number = keyboard_settings.transpose_number;
    octave_number = keyboard_settings.octave_number;
    transpose_number2 = keyboard_settings.transpose_number2;
    octave_number2 = keyboard_settings.octave_number2;
    transpose_number3 = keyboard_settings.transpose_number3;
    octave_number3 = keyboard_settings.octave_number3;
    dynamic_range = keyboard_settings.dynamic_range;
    oledkeyboard = keyboard_settings.oledkeyboard;
    overdub_advanced_mode = keyboard_settings.overdub_advanced_mode;
    smartchordlightmode = keyboard_settings.smartchordlightmode;
    keysplitchannel = keyboard_settings.keysplitchannel;
    keysplit2channel = keyboard_settings.keysplit2channel;
    keysplitstatus = keyboard_settings.keysplitstatus;
    keysplittransposestatus = keyboard_settings.keysplittransposestatus;
    keysplitvelocitystatus = keyboard_settings.keysplitvelocitystatus;
    custom_layer_animations_enabled = keyboard_settings.custom_layer_animations_enabled;
    unsynced_mode_active = keyboard_settings.unsynced_mode_active;
    sample_mode_active = keyboard_settings.sample_mode_active;
    loop_messaging_enabled = keyboard_settings.loop_messaging_enabled;
    loop_messaging_channel = keyboard_settings.loop_messaging_channel;
    sync_midi_mode = keyboard_settings.sync_midi_mode;
    alternate_restart_mode = keyboard_settings.alternate_restart_mode;
    colorblindmode = keyboard_settings.colorblindmode;
    cclooprecording = keyboard_settings.cclooprecording;
    truesustain = keyboard_settings.truesustain;
    
    dprintf("HID: Applied loaded settings from slot %d to active configuration\n", slot);
}
// ============================================================================
// LAYER ACTUATION SETTINGS - EEPROM MANAGEMENT
// ============================================================================
// ============================================================================
// LAYER ACTUATION SETTINGS - EEPROM MANAGEMENT
// ============================================================================

// Save all layer actuations to EEPROM
__attribute__((weak)) void save_layer_actuations(void) {
    // Save entire array at once - now 10 bytes per layer = 120 bytes total
    eeprom_update_block(&layer_actuations, (void*)LAYER_ACTUATION_EEPROM_ADDR, sizeof(layer_actuations));
    dprintf("Saved all layer actuations to EEPROM\n");
}

// Load all layer actuations from EEPROM
__attribute__((weak)) void load_layer_actuations(void) {
    // Load entire array at once
    eeprom_read_block(&layer_actuations, (void*)LAYER_ACTUATION_EEPROM_ADDR, sizeof(layer_actuations));
    
    // Validate loaded values
    for (uint8_t layer = 0; layer < 12; layer++) {
        if (layer_actuations[layer].normal_actuation > 100) {
            layer_actuations[layer].normal_actuation = 80;
        }
        if (layer_actuations[layer].midi_actuation > 100) {
            layer_actuations[layer].midi_actuation = 80;
        }
        if (layer_actuations[layer].velocity_mode > 3) {
            layer_actuations[layer].velocity_mode = 2;
        }
        // Note: rapidfire settings moved to per-key actuations
        if (layer_actuations[layer].velocity_speed_scale < 1 || layer_actuations[layer].velocity_speed_scale > 20) {
            layer_actuations[layer].velocity_speed_scale = 10;
        }
    }
    
    dprintf("Loaded all layer actuations from EEPROM\n");
}

// Reset all layer actuations to defaults
__attribute__((weak)) void reset_layer_actuations(void) {
    for (uint8_t layer = 0; layer < 12; layer++) {
        layer_actuations[layer].normal_actuation = 80;
        layer_actuations[layer].midi_actuation = 80;
        layer_actuations[layer].velocity_mode = 2;
        // Note: rapidfire settings moved to per-key actuations
        layer_actuations[layer].velocity_speed_scale = 10;
        layer_actuations[layer].flags = 0;
        // Per-layer aftertouch settings
        layer_actuations[layer].aftertouch_mode = 0;       // Off
        layer_actuations[layer].aftertouch_cc = 255;       // Off (no CC)
        layer_actuations[layer].vibrato_sensitivity = 100; // Normal (100%)
        layer_actuations[layer].vibrato_decay_time = 200;  // 200ms decay
    }
    save_layer_actuations();
    dprintf("Reset all layer actuations to defaults\n");
}

// Set actuation for a specific layer (extended with aftertouch settings)
__attribute__((weak)) void set_layer_actuation(uint8_t layer, uint8_t normal, uint8_t midi, uint8_t velocity,
                         uint8_t vel_speed, uint8_t flags,
                         uint8_t aftertouch_mode, uint8_t aftertouch_cc,
                         uint8_t vibrato_sensitivity, uint16_t vibrato_decay_time) {
    if (layer >= 12) return;

    // Clamp values to valid ranges
    if (normal > 100) normal = 100;
    if (midi > 100) midi = 100;
    if (velocity > 3) velocity = 3;
    if (vel_speed < 1) vel_speed = 1;
    if (vel_speed > 20) vel_speed = 20;
    if (aftertouch_mode > 4) aftertouch_mode = 0;
    if (vibrato_sensitivity < 50) vibrato_sensitivity = 50;
    if (vibrato_sensitivity > 200) vibrato_sensitivity = 200;
    if (vibrato_decay_time > 2000) vibrato_decay_time = 2000;

    layer_actuations[layer].normal_actuation = normal;
    layer_actuations[layer].midi_actuation = midi;
    layer_actuations[layer].velocity_mode = velocity;
    layer_actuations[layer].velocity_speed_scale = vel_speed;
    layer_actuations[layer].flags = flags;
    layer_actuations[layer].aftertouch_mode = aftertouch_mode;
    layer_actuations[layer].aftertouch_cc = aftertouch_cc;
    layer_actuations[layer].vibrato_sensitivity = vibrato_sensitivity;
    layer_actuations[layer].vibrato_decay_time = vibrato_decay_time;

    dprintf("Set layer %d: n=%d m=%d vel=%d vs=%d flags=%d at_mode=%d at_cc=%d vib_sens=%d vib_decay=%d\n",
            layer, normal, midi, velocity, vel_speed, flags,
            aftertouch_mode, aftertouch_cc, vibrato_sensitivity, vibrato_decay_time);
}

// Get actuation for a specific layer (extended with aftertouch settings)
__attribute__((weak)) void get_layer_actuation(uint8_t layer, uint8_t *normal, uint8_t *midi, uint8_t *velocity,
                         uint8_t *vel_speed, uint8_t *flags,
                         uint8_t *aftertouch_mode, uint8_t *aftertouch_cc,
                         uint8_t *vibrato_sensitivity, uint16_t *vibrato_decay_time) {
    if (layer >= 12) {
        *normal = 80;
        *midi = 80;
        *velocity = 2;
        *vel_speed = 10;
        *flags = 0;
        *aftertouch_mode = 0;
        *aftertouch_cc = 255;
        *vibrato_sensitivity = 100;
        *vibrato_decay_time = 200;
        return;
    }

    *normal = layer_actuations[layer].normal_actuation;
    *midi = layer_actuations[layer].midi_actuation;
    *velocity = layer_actuations[layer].velocity_mode;
    *vel_speed = layer_actuations[layer].velocity_speed_scale;
    *flags = layer_actuations[layer].flags;
    *aftertouch_mode = layer_actuations[layer].aftertouch_mode;
    *aftertouch_cc = layer_actuations[layer].aftertouch_cc;
    *vibrato_sensitivity = layer_actuations[layer].vibrato_sensitivity;
    *vibrato_decay_time = layer_actuations[layer].vibrato_decay_time;
}

// Helper functions to check flags
// Note: Rapidfire is now per-key, not layer-based - these functions always return false
__attribute__((weak)) bool layer_rapidfire_enabled(uint8_t layer) {
    (void)layer;  // Unused
    return false;  // Rapidfire moved to per-key actuations
}

__attribute__((weak)) bool layer_midi_rapidfire_enabled(uint8_t layer) {
    (void)layer;  // Unused
    return false;  // MIDI rapidfire moved to per-key actuations
}

// ============================================================================
// HID COMMAND HANDLERS FOR LAYER ACTUATION
// ============================================================================

__attribute__((weak)) void handle_set_layer_actuation(const uint8_t* data) {
    // New protocol: 11 bytes per layer
    // [0]=layer, [1]=normal, [2]=midi, [3]=velocity_mode, [4]=vel_speed, [5]=flags,
    // [6]=aftertouch_mode, [7]=aftertouch_cc, [8]=vibrato_sensitivity,
    // [9]=vibrato_decay_time_low, [10]=vibrato_decay_time_high
    uint8_t layer = data[0];
    uint8_t normal = data[1];
    uint8_t midi = data[2];
    uint8_t velocity = data[3];
    uint8_t vel_speed = data[4];
    uint8_t flags = data[5];
    uint8_t aftertouch_mode = data[6];
    uint8_t aftertouch_cc = data[7];
    uint8_t vibrato_sensitivity = data[8];
    uint16_t vibrato_decay_time = data[9] | ((uint16_t)data[10] << 8);

    if (layer >= 12) {
        dprintf("HID: Invalid layer %d for actuation\n", layer);
        return;
    }

    set_layer_actuation(layer, normal, midi, velocity, vel_speed, flags,
                        aftertouch_mode, aftertouch_cc, vibrato_sensitivity, vibrato_decay_time);
    save_layer_actuations();

    dprintf("HID: Set layer %d actuation with aftertouch settings\n", layer);
}

__attribute__((weak)) void handle_get_layer_actuation(uint8_t layer, uint8_t* response) {
    if (layer >= 12) {
        dprintf("HID: Invalid layer %d for actuation get\n", layer);
        response[0] = 0;  // Error
        return;
    }

    // Get 10 layer parameters (5 original + 5 aftertouch)
    uint8_t normal, midi, velocity, vel_speed, flags;
    uint8_t aftertouch_mode, aftertouch_cc, vibrato_sensitivity;
    uint16_t vibrato_decay_time;

    get_layer_actuation(layer, &normal, &midi, &velocity, &vel_speed, &flags,
                        &aftertouch_mode, &aftertouch_cc, &vibrato_sensitivity, &vibrato_decay_time);

    response[0] = 0x01;  // Success
    response[1] = normal;
    response[2] = midi;
    response[3] = velocity;
    response[4] = vel_speed;
    response[5] = flags;
    response[6] = aftertouch_mode;
    response[7] = aftertouch_cc;
    response[8] = vibrato_sensitivity;
    response[9] = vibrato_decay_time & 0xFF;         // Low byte
    response[10] = (vibrato_decay_time >> 8) & 0xFF; // High byte

    dprintf("HID: Sent layer %d actuation (11 bytes including aftertouch settings)\n", layer);
}

__attribute__((weak)) void handle_get_all_layer_actuations(void) {
    load_layer_actuations();

    // Send data in chunks (12 layers × 10 bytes = 120 bytes, 6 packets of 20 bytes each)
    // Each layer: normal, midi, velocity_mode, vel_speed, flags,
    //             aftertouch_mode, aftertouch_cc, vibrato_sensitivity, vibrato_decay_time(2)

    for (uint8_t packet = 0; packet < 6; packet++) {
        uint8_t response[20];
        uint8_t idx = 0;
        uint8_t start_layer = packet * 2;

        for (uint8_t i = 0; i < 2; i++) {
            uint8_t layer = start_layer + i;
            if (layer >= 12) break;

            response[idx++] = layer_actuations[layer].normal_actuation;
            response[idx++] = layer_actuations[layer].midi_actuation;
            response[idx++] = layer_actuations[layer].velocity_mode;
            response[idx++] = layer_actuations[layer].velocity_speed_scale;
            response[idx++] = layer_actuations[layer].flags;
            response[idx++] = layer_actuations[layer].aftertouch_mode;
            response[idx++] = layer_actuations[layer].aftertouch_cc;
            response[idx++] = layer_actuations[layer].vibrato_sensitivity;
            response[idx++] = layer_actuations[layer].vibrato_decay_time & 0xFF;         // Low byte
            response[idx++] = (layer_actuations[layer].vibrato_decay_time >> 8) & 0xFF;  // High byte
        }

        send_hid_response(HID_CMD_GET_ALL_LAYER_ACTUATIONS, packet, 0, response, idx);
        if (packet < 5) wait_ms(10);
    }

    dprintf("HID: Sent all layer actuations (6 packets, 10 bytes/layer)\n");
}
__attribute__((weak)) void handle_reset_layer_actuations(void) {
    reset_layer_actuations();
    dprintf("HID: Reset all layer actuations to defaults\n");
}