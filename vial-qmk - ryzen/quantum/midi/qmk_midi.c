#include <LUFA/Drivers/USB/USB.h>
#include "qmk_midi.h"
#include "sysex_tools.h"
#include "midi.h"
#include "usb_descriptor.h"
#include "process_midi.h"
#include "process_dynamic_macro.h"


#include "rgb_matrix.h"
#include "process_rgb.h"

// Include keyboard-specific routing for orthomidi5x14
#ifdef KEYBOARD_orthomidi5x14
#    include "keyboards/orthomidi5x14/orthomidi5x14.h"
#endif

/*******************************************************************************
 * MIDI
 ******************************************************************************/

MidiDevice midi_device;

#define SYSEX_START_OR_CONT 0x40
#define SYSEX_ENDS_IN_1 0x50
#define SYSEX_ENDS_IN_2 0x60
#define SYSEX_ENDS_IN_3 0x70

#define SYS_COMMON_1 0x50
#define SYS_COMMON_2 0x20
#define SYS_COMMON_3 0x30

static uint8_t sysex_buffer[1024];     // Buffer to accumulate SysEx data
static uint16_t sysex_buffer_pos = 0;  // Current position in buffer
static bool sysex_receiving = false;   // Are we currently receiving a SysEx message?

void usb_send_func(MidiDevice* device, uint16_t cnt, uint8_t byte0, uint8_t byte1, uint8_t byte2) {
    MIDI_EventPacket_t event;
    event.Data1 = byte0;
    event.Data2 = byte1;
    event.Data3 = byte2;

    uint8_t cable = 0;

    // if the length is undefined we assume it is a SYSEX message
    if (midi_packet_length(byte0) == UNDEFINED) {
        switch (cnt) {
            case 3:
                if (byte2 == SYSEX_END)
                    event.Event = MIDI_EVENT(cable, SYSEX_ENDS_IN_3);
                else
                    event.Event = MIDI_EVENT(cable, SYSEX_START_OR_CONT);
                break;
            case 2:
                if (byte1 == SYSEX_END)
                    event.Event = MIDI_EVENT(cable, SYSEX_ENDS_IN_2);
                else
                    event.Event = MIDI_EVENT(cable, SYSEX_START_OR_CONT);
                break;
            case 1:
                if (byte0 == SYSEX_END)
                    event.Event = MIDI_EVENT(cable, SYSEX_ENDS_IN_1);
                else
                    event.Event = MIDI_EVENT(cable, SYSEX_START_OR_CONT);
                break;
            default:
                return; // invalid cnt
        }
    } else {
        // deal with 'system common' messages
        // TODO are there any more?
        switch (byte0 & 0xF0) {
            case MIDI_SONGPOSITION:
                event.Event = MIDI_EVENT(cable, SYS_COMMON_3);
                break;
            case MIDI_SONGSELECT:
            case MIDI_TC_QUARTERFRAME:
                event.Event = MIDI_EVENT(cable, SYS_COMMON_2);
                break;
            default:
                event.Event = MIDI_EVENT(cable, byte0);
                break;
        }
    }

    send_midi_packet(&event);
}

// Function to find LED indices for a specific MIDI note using the compatibility wrapper
static void find_midi_note_leds(uint8_t midi_note, uint8_t led_indices[6], uint8_t *led_count) {
    *led_count = 0;
    uint8_t current_layer = get_highest_layer(layer_state | default_layer_state);
    
    // Convert MIDI note to note index (0-71)
    uint8_t note_index = (midi_note - 24) % 72;
    
    // Use the compatibility wrapper function
    for (uint8_t i = 0; i < 6; i++) {
        uint8_t led_index = get_midi_led_position(current_layer, note_index, i);
        if (led_index != 99 && *led_count < 6) {
            led_indices[*led_count] = led_index;
            (*led_count)++;
        }
    }
}

// Function to trigger RGB effects for a specific MIDI note
static void trigger_rgb_for_midi_note(uint8_t note, uint8_t velocity) {
    // Find all LED positions for this MIDI note
    uint8_t led_indices[6];
    uint8_t led_count;
    find_midi_note_leds(note, led_indices, &led_count);
    
    if (led_count > 0) {
        // For each LED that corresponds to this MIDI note, simulate a keypress
        for (uint8_t i = 0; i < led_count; i++) {
            uint8_t led_index = led_indices[i];
            if (led_index < RGB_MATRIX_LED_COUNT) {
                // Find row/col for this LED index by searching the matrix
                for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
                    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
                        if (g_led_config.matrix_co[row][col] == led_index) {
                            // Simulate keypress - this will trigger reactive effects
                            process_rgb_matrix(row, col, true);
                            break; // Found the row/col for this LED, move to next LED
                        }
                    }
                }
            }
        }
    }
}

// Function to handle note-off events (dim or turn off LEDs)
static void clear_rgb_for_midi_note(uint8_t note) {
    // Find all LED positions for this MIDI note
    uint8_t led_indices[6];
    uint8_t led_count;
    find_midi_note_leds(note, led_indices, &led_count);
    
    if (led_count > 0) {
        // For each LED that corresponds to this MIDI note, simulate a key release
        for (uint8_t i = 0; i < led_count; i++) {
            uint8_t led_index = led_indices[i];
            if (led_index < RGB_MATRIX_LED_COUNT) {
                // Find row/col for this LED index by searching the matrix
                for (uint8_t row = 0; row < MATRIX_ROWS; row++) {
                    for (uint8_t col = 0; col < MATRIX_COLS; col++) {
                        if (g_led_config.matrix_co[row][col] == led_index) {
                            // Simulate key release - this will trigger reactive effects
                            process_rgb_matrix(row, col, false);
                            break; // Found the row/col for this LED, move to next LED
                        }
                    }
                }
            }
        }
    }
}

static void usb_get_midi(MidiDevice* device) {
    MIDI_EventPacket_t event;
    while (recv_midi_packet(&event)) {
        midi_packet_length_t length = midi_packet_length(event.Data1);
        uint8_t              input[3];
        input[0] = event.Data1;
        input[1] = event.Data2;
        input[2] = event.Data3;

#ifdef KEYBOARD_orthomidi5x14
        // Route USB MIDI based on current mode
        if (usb_midi_mode == USB_MIDI_TO_OUT) {
            // Send directly to hardware MIDI OUT without processing
            route_usb_midi_data(input[0], input[1], input[2], length);
            // Skip all keyboard processing below
            continue;
        }
        // If USB_MIDI_PROCESS mode, continue with normal processing below
#endif

        // Convert MIDI messages to direct function calls
        if (length == 3) {
            uint8_t channel = input[0] & 0x0F;
            uint8_t status = input[0] & 0xF0;
            uint8_t data1 = input[1] & 0x7F;
            uint8_t data2 = input[2] & 0x7F;
            
            // Apply channel override if enabled
            if (channeloverride) {
                channel = channel_number & 0x0F; // Ensure valid channel range (0-15)
            }
            
            switch (status) {
                case MIDI_NOTEON:
                    {
                        uint8_t note = data1;
                        uint8_t velocity = data2;
                        
                        // Apply transpose override if enabled
                        if (transposeoverride) {
                            int16_t transposed_note = note + transpose_number + octave_number;
                            // Clamp to valid MIDI note range (0-127)
                            if (transposed_note < 0) transposed_note = 0;
                            if (transposed_note > 127) transposed_note = 127;
                            note = (uint8_t)transposed_note;
                        }
                        
                        // Apply velocity override if enabled
                        if (velocityoverride) {
                            velocity = velocity_number & 0x7F; // Ensure valid velocity range (0-127)
                        }
                        
                        midi_send_noteon_with_recording(channel, note, velocity);
                        
                        // NEW: Trigger RGB lighting effects
                        if (velocity > 0) { // Velocity > 0 means note on
                            trigger_rgb_for_midi_note(note, velocity);
                        } else { // Velocity 0 is actually note off
                            clear_rgb_for_midi_note(note);
                        }
                    }
                    break;
                    
                case MIDI_NOTEOFF:
                    {
                        uint8_t note = data1;
                        uint8_t velocity = data2;
                        
                        // Apply transpose override if enabled
                        if (transposeoverride) {
                            int16_t transposed_note = note + transpose_number + octave_number;
                            // Clamp to valid MIDI note range (0-127)
                            if (transposed_note < 0) transposed_note = 0;
                            if (transposed_note > 127) transposed_note = 127;
                            note = (uint8_t)transposed_note;
                        }
                        
                        // Apply velocity override if enabled (some devices use note-off velocity)
                        if (velocityoverride) {
                            velocity = velocity_number & 0x7F; // Ensure valid velocity range (0-127)
                        }
                        
                        midi_send_noteoff_with_recording(channel, note, velocity);
                        
                        // NEW: Clear RGB lighting effects
                        clear_rgb_for_midi_note(note);
                    }
                    break;
                    
                case MIDI_CC:
                    // Direct CC processing
                    midi_send_external_cc_with_recording(channel, data1, data2);
                    break;
                    
                case MIDI_AFTERTOUCH:
                    // Send aftertouch with recording
                    midi_send_aftertouch_with_recording(channel, data1, data2);
                    break;
                    
                case MIDI_PITCHBEND:
                    {
                        // Pitch bend is 14-bit, reconstruct the full value
                        int16_t bend_value = ((data2 & 0x7F) << 7) | (data1 & 0x7F);
                        bend_value -= 8192; // Convert to signed range (-8192 to +8191)
                        
                        // Send pitchbend with recording
                        midi_send_pitchbend_with_recording(channel, bend_value);
                    }
                    break;
            }
        } else if (length == 2) {
            uint8_t channel = input[0] & 0x0F;
            uint8_t status = input[0] & 0xF0;
            uint8_t data1 = input[1] & 0x7F;
            
            // Apply channel override if enabled
            if (channeloverride) {
                channel = channel_number & 0x0F; // Ensure valid channel range (0-15)
            }
            
            switch (status) {
                case MIDI_PROGCHANGE:
                    // Send program change with recording
                    midi_send_program_with_recording(channel, data1);
                    break;
                    
                case MIDI_CHANPRESSURE:
                    // Send channel pressure with recording
                    midi_send_channel_pressure_with_recording(channel, data1);
                    break;
            }
		} else if (length == 1) {
					// System realtime messages (no channel or note data to override)
					switch (input[0]) {
						case MIDI_CLOCK:  // 0xF8
							handle_external_clock_pulse();
							break;
						case MIDI_START:  // 0xFA
							handle_external_clock_start();
							break;
						case MIDI_STOP:   // 0xFC
							handle_external_clock_stop();
							break;
						case MIDI_CONTINUE:  // 0xFB
							handle_external_clock_continue();
							break;
					}
				}
        
        // *** NEW SYSEX HANDLING SECTION ***
        if (length == UNDEFINED) {
            // SysEx message handling
            uint8_t sysex_length = 0;
            uint8_t sysex_data[3];
            
            if (event.Event == MIDI_EVENT(0, SYSEX_START_OR_CONT) || event.Event == MIDI_EVENT(0, SYSEX_ENDS_IN_3)) {
                sysex_length = 3;
                sysex_data[0] = input[0];
                sysex_data[1] = input[1];
                sysex_data[2] = input[2];
            } else if (event.Event == MIDI_EVENT(0, SYSEX_ENDS_IN_2)) {
                sysex_length = 2;
                sysex_data[0] = input[0];
                sysex_data[1] = input[1];
            } else if (event.Event == MIDI_EVENT(0, SYSEX_ENDS_IN_1)) {
                sysex_length = 1;
                sysex_data[0] = input[0];
            }
            
            if (sysex_length > 0) {
                // Process SysEx data
                for (uint8_t i = 0; i < sysex_length; i++) {
                    uint8_t byte = sysex_data[i];
                    
                    if (byte == 0xF0) {
                        // SysEx start - reset buffer
                        sysex_receiving = true;
                        sysex_buffer_pos = 0;
                        if (sysex_buffer_pos < sizeof(sysex_buffer)) {
                            sysex_buffer[sysex_buffer_pos++] = byte;
                        }
                    } else if (byte == 0xF7) {
                        // SysEx end - process complete message
                        if (sysex_receiving && sysex_buffer_pos < sizeof(sysex_buffer)) {
                            sysex_buffer[sysex_buffer_pos++] = byte;

                            // Reset for next message
                            sysex_receiving = false;
                            sysex_buffer_pos = 0;
                        }
                    } else if (sysex_receiving) {
                        // SysEx continuation - add to buffer
                        if (sysex_buffer_pos < sizeof(sysex_buffer)) {
                            sysex_buffer[sysex_buffer_pos++] = byte;
                        } else {
                            // Buffer overflow - reset
                            sysex_receiving = false;
                            sysex_buffer_pos = 0;
                        }
                    }
                }
            }
            
            // Set length for the original processing
            if (event.Event == MIDI_EVENT(0, SYSEX_START_OR_CONT) || event.Event == MIDI_EVENT(0, SYSEX_ENDS_IN_3)) {
                length = 3;
            } else if (event.Event == MIDI_EVENT(0, SYSEX_ENDS_IN_2)) {
                length = 2;
            } else if (event.Event == MIDI_EVENT(0, SYSEX_ENDS_IN_1)) {
                length = 1;
            }
        }

        // Still pass the data to the device input function for any other processing
        if (length != UNDEFINED) {
            midi_device_input(device, length, input);
        }
    }
}

static void fallthrough_callback(MidiDevice* device, uint16_t cnt, uint8_t byte0, uint8_t byte1, uint8_t byte2) {
#ifdef AUDIO_ENABLE
    if (cnt == 3) {
        switch (byte0 & 0xF0) {
            case MIDI_NOTEON:
                play_note(((double)261.6) * pow(2.0, -4.0) * pow(2.0, (byte1 & 0x7F) / 12.0), (byte2 & 0x7F) / 8);
                break;
            case MIDI_NOTEOFF:
                stop_note(((double)261.6) * pow(2.0, -4.0) * pow(2.0, (byte1 & 0x7F) / 12.0));
                break;
        }
    }
    if (byte0 == MIDI_STOP) {
        stop_all_notes();
    }
#endif
}

static void cc_callback(MidiDevice* device, uint8_t chan, uint8_t num, uint8_t val) {
    // sending it back on the next channel
    // midi_send_cc(device, (chan + 1) % 16, num, val);
}

void midi_init(void);

void setup_midi(void) {
#ifdef MIDI_ADVANCED
    midi_init();
#endif
    midi_device_init(&midi_device);
    midi_device_set_send_func(&midi_device, usb_send_func);
    midi_device_set_pre_input_process_func(&midi_device, usb_get_midi);
    midi_register_fallthrough_callback(&midi_device, fallthrough_callback);
    midi_register_cc_callback(&midi_device, cc_callback);
}