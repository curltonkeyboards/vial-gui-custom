#pragma once

#ifdef MIDI_ENABLE
#    include "midi.h"
#    include <LUFA/Drivers/USB/USB.h>
extern MidiDevice midi_device;
void              setup_midi(void);
void              send_midi_packet(MIDI_EventPacket_t* event);
bool              recv_midi_packet(MIDI_EventPacket_t* const event);

// Keyboard-specific USB MIDI routing function (can be implemented by keyboards)
#ifdef KEYBOARD_orthomidi5x14
void route_usb_midi_data(uint8_t byte1, uint8_t byte2, uint8_t byte3, uint8_t num_bytes);
#endif

#endif
