#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include "quantum.h"
#include "process_dynamic_macro.h"

// Display constants
#define DISPLAY_WIDTH 21
#define DISPLAY_ROWS 4
#define MACRO_COLUMNS 4
#define COLUMN_WIDTH 5
#define FLASH_INTERVAL 500  // milliseconds

// Status abbreviations
typedef enum {
    STATUS_EMPTY = 0,
    STATUS_PLAYING,
    STATUS_MUTED,
    STATUS_RECORDING,
    STATUS_OVERDUBBING,
    STATUS_SOLO
} macro_status_t;

// Display state structure
typedef struct {
    macro_status_t current_status[MAX_MACROS];
    macro_status_t queued_status[MAX_MACROS];
    macro_status_t overdub_status[MAX_MACROS];
    macro_status_t overdub_queued[MAX_MACROS];
    bool flash_state;
    uint32_t last_flash_time;
    bool display_needs_update;
    bool any_macro_has_data;
} display_state_t;

// Global display state
static display_state_t display_state = {0};

// Status text lookup
static const char* status_text[] = {
    "   ",  // EMPTY
    "PLY",  // PLAYING
    "MUT",  // MUTED
    "REC",  // RECORDING
    "DUB",  // OVERDUBBING
    "SOL"   // SOLO
};

// External function declaration for Luna rendering
extern void render_luna(int LUNA_X, int LUNA_Y);

// Function declarations
void oled_display_init(void);
void oled_display_update(void);
void oled_display_force_update(void);
bool check_any_macro_has_data(void);
macro_status_t get_macro_current_status(uint8_t macro_idx);
macro_status_t get_macro_queued_status(uint8_t macro_idx);
macro_status_t get_overdub_current_status(uint8_t macro_idx);
macro_status_t get_overdub_queued_status(uint8_t macro_idx);
void render_display_line(char* buffer, macro_status_t statuses[MAX_MACROS], bool flash_queued, macro_status_t queued[MAX_MACROS]);
void render_macro_display(void);

// Initialize the display system
void oled_display_init(void) {
    display_state.flash_state = false;
    display_state.last_flash_time = timer_read32();
    display_state.display_needs_update = true;
    display_state.any_macro_has_data = false;
    
    // Initialize all statuses to empty
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        display_state.current_status[i] = STATUS_EMPTY;
        display_state.queued_status[i] = STATUS_EMPTY;
        display_state.overdub_status[i] = STATUS_EMPTY;
        display_state.overdub_queued[i] = STATUS_EMPTY;
    }
}

// Check if any macro or overdub has data
bool check_any_macro_has_data(void) {
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        // Check if main macro has content
        midi_event_t *macro_start = get_macro_buffer(i + 1);
        midi_event_t **macro_end_ptr = get_macro_end_ptr(i + 1);
        if (macro_start && macro_end_ptr && *macro_end_ptr && macro_start != *macro_end_ptr) {
            return true;
        }
        
        // Check if overdub has content
        if (overdub_buffers[i] != NULL && 
            overdub_buffer_ends[i] != overdub_buffers[i]) {
            return true;
        }
        
        // Check if currently recording
        if (macro_id == (i + 1)) {
            return true;
        }
    }
    return false;
}

// Get current status for a macro
macro_status_t get_macro_current_status(uint8_t macro_idx) {
    if (macro_idx >= MAX_MACROS) return STATUS_EMPTY;
    
    // Check if currently recording this macro
    if (macro_id == (macro_idx + 1)) {
        if (macro_in_overdub_mode[macro_idx]) {
            return STATUS_OVERDUBBING;
        } else {
            return STATUS_RECORDING;
        }
    }
    
    // Check if macro is playing
    if (macro_playback[macro_idx].is_playing) {
        return STATUS_PLAYING;
    }
    
    // Check if macro has content but is not playing (muted)
    midi_event_t *macro_start = get_macro_buffer(macro_idx + 1);
    midi_event_t **macro_end_ptr = get_macro_end_ptr(macro_idx + 1);
    if (macro_start && macro_end_ptr && *macro_end_ptr && macro_start != *macro_end_ptr) {
        return STATUS_MUTED;
    }
    
    // Macro is empty
    return STATUS_EMPTY;
}

// Get queued status for a macro
macro_status_t get_macro_queued_status(uint8_t macro_idx) {
    if (macro_idx >= MAX_MACROS) return STATUS_EMPTY;
    
    uint8_t macro_num = macro_idx + 1;
    
    // Check command batch for queued operations
    for (uint8_t i = 0; i < command_batch_count; i++) {
        if (command_batch[i].macro_id == macro_num && !command_batch[i].processed) {
            switch (command_batch[i].command_type) {
                case CMD_PLAY:
                    return STATUS_PLAYING;
                case CMD_STOP:
                    return STATUS_MUTED;
                case CMD_RECORD:
                    return STATUS_RECORDING;
                case CMD_PLAY_OVERDUB_ONLY:
                    return STATUS_SOLO;
                default:
                    break;
            }
        }
    }
    
    return STATUS_EMPTY;
}

// Get current overdub status
macro_status_t get_overdub_current_status(uint8_t macro_idx) {
    if (macro_idx >= MAX_MACROS) return STATUS_EMPTY;
    
    // Check if overdub buffer exists and has content
    if (overdub_buffers[macro_idx] == NULL || 
        overdub_buffer_ends[macro_idx] == overdub_buffers[macro_idx]) {
        return STATUS_EMPTY;
    }
    
    // Check if overdub is playing solo (main macro muted, overdub playing)
    if (overdub_playback[macro_idx].is_playing && !macro_playback[macro_idx].is_playing) {
        return STATUS_SOLO;
    }
    
    // Check if overdub is playing with main macro
    if (overdub_playback[macro_idx].is_playing) {
        return STATUS_PLAYING;
    }
    
    // Check if overdub is muted
    if (overdub_muted[macro_idx]) {
        return STATUS_MUTED;
    }
    
    // Overdub exists but is not playing (unmuted but main macro not playing)
    return STATUS_MUTED;
}

// Get queued overdub status
macro_status_t get_overdub_queued_status(uint8_t macro_idx) {
    if (macro_idx >= MAX_MACROS) return STATUS_EMPTY;
    
    // Check for pending mute/unmute operations
    if (overdub_mute_pending[macro_idx]) {
        return STATUS_MUTED;
    }
    
    if (overdub_unmute_pending[macro_idx]) {
        return STATUS_PLAYING;
    }
    
    return STATUS_EMPTY;
}

// Render a display line with optional flashing for queued items
void render_display_line(char* buffer, macro_status_t statuses[MAX_MACROS], bool flash_queued, macro_status_t queued[MAX_MACROS]) {
    buffer[0] = '\0';  // Clear buffer
    
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        char column[6];  // 5 chars + null terminator
        
        // Determine what to display and if it should flash
        macro_status_t display_status = statuses[i];
        bool should_flash = false;
        
        if (flash_queued && queued[i] != STATUS_EMPTY) {
            display_status = queued[i];
            should_flash = true;
        }
        
        // Apply flashing effect
        if (should_flash && !display_state.flash_state) {
            // Flash off - show spaces
            snprintf(column, sizeof(column), "    ");
        } else {
            // Show the status
            snprintf(column, sizeof(column), " %s ", status_text[display_status]);
        }
        
        // Add to buffer with column separator
        strcat(buffer, column);
        if (i < MAX_MACROS - 1) {
            strcat(buffer, "|");
        }
    }
}

// Render the macro status display
void render_macro_display(void) {
    char line_buffer[DISPLAY_WIDTH + 1];
    
    // Clear the area where we'll draw (starting from row 1)
    oled_set_cursor(0, 1);
    oled_write_P(PSTR("                     "), false); // Clear line
    oled_set_cursor(0, 2);
    oled_write_P(PSTR("                     "), false); // Clear line
    oled_set_cursor(0, 3);
    oled_write_P(PSTR("                     "), false); // Clear line
    
    // Row 1: Current status
    render_display_line(line_buffer, display_state.current_status, false, NULL);
    oled_set_cursor(0, 1);
    oled_write(line_buffer, false);
    
    // Row 2: Queued status (flashing)
    render_display_line(line_buffer, display_state.current_status, true, display_state.queued_status);
    oled_set_cursor(0, 2);
    oled_write(line_buffer, false);
    
    // Row 3: Overdub status with queued flashing
    macro_status_t overdub_display[MAX_MACROS];
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        if (display_state.overdub_queued[i] != STATUS_EMPTY) {
            // Use queued status as base, will flash automatically
            overdub_display[i] = display_state.overdub_status[i]; // Show current when flash is off
        } else {
            // Show current overdub status
            overdub_display[i] = display_state.overdub_status[i];
        }
    }
    
    render_display_line(line_buffer, overdub_display, true, display_state.overdub_queued);
    oled_set_cursor(0, 3);
    oled_write(line_buffer, false);
}

// Main display update function
void oled_display_update(void) {
    uint32_t current_time = timer_read32();
    bool status_changed = false;
    
    // Check if any macro has data
    bool has_data = check_any_macro_has_data();
    if (display_state.any_macro_has_data != has_data) {
        display_state.any_macro_has_data = has_data;
        display_state.display_needs_update = true;
    }
    
    // If no macros have data, we don't need to update macro display
    if (!display_state.any_macro_has_data) {
        return; // Let Luna render instead
    }
    
    // Update flash state
    if (timer_elapsed32(display_state.last_flash_time) >= FLASH_INTERVAL) {
        display_state.flash_state = !display_state.flash_state;
        display_state.last_flash_time = current_time;
        display_state.display_needs_update = true;
    }
    
    // Check for status changes
    for (uint8_t i = 0; i < MAX_MACROS; i++) {
        macro_status_t new_current = get_macro_current_status(i);
        macro_status_t new_queued = get_macro_queued_status(i);
        macro_status_t new_overdub = get_overdub_current_status(i);
        macro_status_t new_overdub_queued = get_overdub_queued_status(i);
        
        if (display_state.current_status[i] != new_current ||
            display_state.queued_status[i] != new_queued ||
            display_state.overdub_status[i] != new_overdub ||
            display_state.overdub_queued[i] != new_overdub_queued) {
            
            display_state.current_status[i] = new_current;
            display_state.queued_status[i] = new_queued;
            display_state.overdub_status[i] = new_overdub;
            display_state.overdub_queued[i] = new_overdub_queued;
            status_changed = true;
        }
    }
    
    if (status_changed) {
        display_state.display_needs_update = true;
    }
    
    // Render display if update needed
    if (display_state.display_needs_update) {
        render_macro_display();
        display_state.display_needs_update = false;
    }
}

// Force immediate display update
void oled_display_force_update(void) {
    display_state.display_needs_update = true;
    oled_display_update();
}

// Check if we should show Luna or macro display
bool should_show_luna(void) {
    return !display_state.any_macro_has_data;
}

#endif // OLED_DISPLAY_H