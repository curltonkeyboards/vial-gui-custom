// Copyright 2023 QMK
// SPDX-License-Identifier: GPL-2.0-or-later

#include "midi_function_types.h"
#include "process_midi.h"
#include "process_rgb.h"
#include <printf/printf.h>
#include QMK_KEYBOARD_H
#include "orthomidi5x14.h"
extern MidiDevice midi_device;

#define BANK_SEL_MSB_CC 0
#define BANK_SEL_LSB_CC 32

// new midi keycodes
#define MI_CC_TOG_0 0x8000
#define MI_CC_UP_0 (0x8000 + 128)
#define MI_CC_DWN_0 (0x8000 + 128 * 2)
#define MI_CC_0_0 (0x8000 + 128 * 3)
#define MI_BANK_MSB_0 ((0x8000 + 128 * 3) + 128 * 128)
#define MI_BANK_LSB_0 ((0x8000 + 128 * 4) + 128 * 128)
#define MI_PROG_0 ((0x8000 + 128 * 5) + 128 * 128)
#define MI_BANK_UP ((0x8000 + 128 * 6) + 128 * 128 + 1)
#define MI_BANK_DWN ((0x8000 + 128 * 6) + 128 * 128 + 2)
#define MI_PROG_UP ((0x8000 + 128 * 6) + 128 * 128 + 3)
#define MI_PROG_DWN ((0x8000 + 128 * 6) + 128 * 128 + 4)
#define KC_CUSTOM ((0x8000 + 128 * 6) + 128 * 128 + 5)
#define MI_VELOCITY_0 ((0x8000 + 128 * 6) + 128 * 128 + 5)
#define ENCODER_STEP_1 ( (0x8000 + 128 * 7) + 128 * 128 + 5)
#undef KC_CUSTOM
#define KC_CUSTOM (0x8000 + 128 * 7) + 128 * 128 + 5 + 17


// enum custom_keycodes { MY_CUSTOM_KC = KC_CUSTOM, CUSTOM_KC_2, CUSTOM_KC_3 };

static uint8_t  CCValue[128]    = {};
static uint16_t MidiCurrentBank = 0;
static uint8_t  MidiCurrentProg = 0;
static uint8_t  encoder_step = 1;
//static uint8_t tone_status[2][MIDI_TONE_COUNT];
static uint8_t tone2_status[2][MIDI_TONE_COUNT];
static uint8_t tone3_status[2][MIDI_TONE_COUNT];
static uint8_t tone4_status[2][MIDI_TONE_COUNT];
static uint8_t tone5_status[2][MIDI_TONE_COUNT];
static uint8_t tone6_status[2][MIDI_TONE_COUNT];
static uint8_t tone7_status[2][MIDI_TONE_COUNT];

uint8_t modified_note;
uint8_t original_note;

//char status_str[32] = "";


/* KEYLOGREND */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>

char keylog_str[44] = {};
int8_t transpose_number = 0;  // Variable to store the special number
int8_t octave_number = 0;
int8_t transpose_number2 = 0;  // Variable to store the special number
int8_t octave_number2 = 0;
int8_t transpose_number3 = 0;  // Variable to store the special number
int8_t octave_number3 = 0;
uint8_t velocity_number = 127;
uint8_t velocity_number2 = 127;
uint8_t velocity_number3 = 127;
uint8_t velocityplaceholder = 127;
int cc_up_value1[128] = {0};   // (value 1) for CC UP for each CC#
int cc_updown_value[128] = {0};   // (value 2) for CC UP for each CC#[128] = {0};   // (value 2) for CC UP for each CC#
int cc_down_value1[128] = {0};   // (value 1) for CC UP for each CC#
int velocity_sensitivity = 1;     
int cc_sensitivity = 1;   // Initial sensitivity value
uint8_t channel_number = 0;
int channelplaceholder = 0;
int hsvplaceholder = 0;
int oneshotchannel = 0;
int hk1 = 0;
int hk2 = 0;
int hk3 = 0;
int hk4 = 0;
int hk5 = 0;
int hk6 = 0;
int hk7 = 0;
int hk1d = 0; 
int hk2d = 0; 
int hk3d = 0; 
int hk4d = 0; 
int hk5d = 0; 
int hk6d = 0; 
int hk7d = 0; 
int hk1 = 0;
int hk2 = 0;
int hk3 = 0;
int hk4 = 0;
int hk5 = 0;
int hk6 = 0;
int hk7 = 0;
int ck1 = 0;
int ck2 = 0;
int ck3 = 0;
int ck4 = 0;
int ck5 = 0;
int ck6 = 0;
int ck7 = 0;
int smartck2 = 0;
int smartck3 = 0;
int smartck4 = 0;
int smartck5 = 0;
int smartck6 = 0;
int smartck7 = 0;
int scstatus = 0;
int inversionposition = 0;
int rootnote = 13;
int bassnote = 13;
int trueheldkey[7];
uint8_t ck1_led_index = 99;
uint8_t ck2_led_index = 99;
uint8_t ck3_led_index = 99;
uint8_t ck4_led_index = 99;
uint8_t ck5_led_index = 99;
uint8_t ck6_led_index = 99;
uint8_t ck7_led_index = 99;
uint8_t ck1_led_index2 = 99;
uint8_t ck2_led_index2 = 99;
uint8_t ck3_led_index2 = 99;
uint8_t ck4_led_index2 = 99;
uint8_t ck5_led_index2 = 99;
uint8_t ck6_led_index2 = 99;
uint8_t ck7_led_index2 = 99;
uint8_t ck1_led_index3 = 99;
uint8_t ck2_led_index3 = 99;
uint8_t ck3_led_index3 = 99;
uint8_t ck4_led_index3 = 99;
uint8_t ck5_led_index3 = 99;
uint8_t ck6_led_index3 = 99;
uint8_t ck7_led_index3 = 99;
uint8_t ck1_led_index4 = 99;
uint8_t ck2_led_index4 = 99;
uint8_t ck3_led_index4 = 99;
uint8_t ck4_led_index4 = 99;
uint8_t ck5_led_index4 = 99;
uint8_t ck6_led_index4 = 99;
uint8_t ck7_led_index4 = 99;
uint8_t ck1_led_index5 = 99;
uint8_t ck2_led_index5 = 99;
uint8_t ck3_led_index5 = 99;
uint8_t ck4_led_index5 = 99;
uint8_t ck5_led_index5 = 99;
uint8_t ck6_led_index5 = 99;
uint8_t ck7_led_index5 = 99;
uint8_t ck1_led_index6 = 99;
uint8_t ck2_led_index6 = 99;
uint8_t ck3_led_index6 = 99;
uint8_t ck4_led_index6 = 99;
uint8_t ck5_led_index6 = 99;
uint8_t ck6_led_index6 = 99;
uint8_t ck7_led_index6 = 99;
int oledkeyboard = 0;
int scchanger = 1;
int colorblindmode = 0;
int sclight = 0;
int sclightmode = 0;
int keysplitnumber = 28931;
uint8_t keysplitchannel = 0;
uint8_t keysplit2channel = 0;
uint8_t keysplitstatus = 0;
uint8_t keysplittransposestatus = 0;
uint8_t keysplitvelocitystatus = 0;
int8_t transpositionplaceholder = 0;


uint8_t keycode_to_led_index[72] = {
	99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
	42, 28, 43, 29, 44, 45, 31, 46, 32, 47, 33, 48, 
	14, 0, 15, 1, 16, 17, 3, 18, 4, 19, 5, 20,
	21, 7, 22, 8, 23, 24, 10, 25, 11, 26, 12, 27,
	99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
	99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99
   };
   
led_config_t g_led_config = {
  // Key Matrix to LED Index
  {
    // Row 0
    { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 },
    // Row 1
    { 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27 },
    // Row 2
    { 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41 },
    // Row 3
    { 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 },
    // Row 4
    { 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69 }
  },
  // LED Index to Physical Position
  {
    // LED positions, equally spaced
    // Row 0
    { 0, 0 }, { 16, 0 }, { 32, 0 }, { 48, 0 }, { 64, 0 }, { 80, 0 }, { 96, 0 }, { 112, 0 }, { 128, 0 }, { 144, 0 }, { 160, 0 }, { 176, 0 }, { 192, 0 }, { 208, 0 },
    // Row 1
    { 0, 16 }, { 16, 16 }, { 32, 16 }, { 48, 16 }, { 64, 16 }, { 80, 16 }, { 96, 16 }, { 112, 16 }, { 128, 16 }, { 144, 16 }, { 160, 16 }, { 176, 16 }, { 192, 16 }, { 208, 16 },
    // Row 2
    { 0, 32 }, { 16, 32 }, { 32, 32 }, { 48, 32 }, { 64, 32 }, { 80, 32 }, { 96, 32 }, { 112, 32 }, { 128, 32 }, { 144, 32 }, { 160, 32 }, { 176, 32 }, { 192, 32 }, { 208, 32 },
    // Row 3
    { 0, 48 }, { 16, 48 }, { 32, 48 }, { 48, 48 }, { 64, 48 }, { 80, 48 }, { 96, 48 }, { 112, 48 }, { 128, 48 }, { 144, 48 }, { 160, 48 }, { 176, 48 }, { 192, 48 }, { 208, 48 },
    // Row 4
    { 0, 64 }, { 16, 64 }, { 32, 64 }, { 48, 64 }, { 64, 64 }, { 80, 64 }, { 96, 64 }, { 112, 64 }, { 128, 64 }, { 144, 64 }, { 160, 64 }, { 176, 64 }, { 192, 64 }, { 208, 64 }
  },
  // LED Index to Flag
  {
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4
  }
};


const char* getRootName(void) {
	if (rootnote == 0) {
		return "B";  // Return NULL to indicate individual note calculation
	}
		else if (rootnote == 1) {
	return "C";  
	}
		else if (rootnote == 2) {
	return "C#";  
	}
		else if (rootnote == 3) {
	return "D";  
	}
		else if (rootnote == 4) {
	return "D#";  
	}
		else if (rootnote == 5) {
	return "E";  
	}
		else if (rootnote == 6) {
	return "F";  
	}
		else if (rootnote == 7) {
	return "F#";  
	}
		else if (rootnote == 8) {
	return "G";  
	}
		else if (rootnote == 9) {
	return "G#";  
	}
		else if (rootnote == 10) {
	return "A";  
	}
		else if (rootnote == 11) {
	return "A#";  
	}
		else if (rootnote == 12) {
	return "B";  
	}
		else { 
	return "";
		}
}

const char* getBassName(void) {
	if (bassnote == 0) {
		return "/B";  // Return NULL to indicate individual note calculation
	}
		else if (bassnote == 1) {
	return "/C";  
	}
		else if (bassnote == 2) {
	return "/C#";  
	}
		else if (bassnote == 3) {
	return "/D";  
	}
		else if (bassnote == 4) {
	return "/D#";  
	}
		else if (bassnote == 5) {
	return "/E";  
	}
		else if (bassnote == 6) {
	return "/F";  
	}
		else if (bassnote == 7) {
	return "/F#";  
	}
		else if (bassnote == 8) {
	return "/G";  
	}
		else if (bassnote == 9) {
	return "/G#";  
	}
		else if (bassnote == 10) {
	return "/A";  
	}
		else if (bassnote == 11) {
	return "/A#";  
	}
		else if (bassnote == 12) {
	return "/B";  
	}
		else { 
	return "";
		}
}

const char* getChordName(void) {
		   	////////////////////////////////////////////////////////////////////////////////
	//				ALL intervals
	///////////////////////////////////////////////////////////////////////////////
	// Check for Minor 2nd
	if (hk2d == 0 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
        return "     ";  // Return NULL to indicate individual note calculation
	}
	else if (hk2d == 2 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Minor 2nd";
	}
	
	// Check for Major 2nd
	else if(hk2d == 3 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Major 2nd";
	}
	
	// Check for Minor 3rd
	else if(hk2d == 4 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Minor 3rd";
	}
	
	// Check for Major 3rd
	else if(hk2d == 5 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Major 3rd";
	}

	// Check for Perfect 4th
	else if(hk2d == 6 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Pfect 4th";
	}

	// Check for Tritone
	else if(hk2d == 7 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Tritone";
	}

	// Check for Perfect 5th
	else if(hk2d == 8 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Pfect 5th";
	}

	// Check for Minor 6th
	else if(hk2d == 9 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Minor 6th";
	}

	// Check for Major 6th
	else if(hk2d == 10 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Major 6th";
	}

	// Check for Minor 7th
	else if(hk2d == 11 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Minor 7th";
	}

	// Check for Major 7th
	else if(hk2d == 12 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
		rootnote = 13;
		bassnote = 13;
    return "Major 7th";
	}
	
		   	////////////////////////////////////////////////////////////////////////////////
	//				ALL 3 note CHORDS
	///////////////////////////////////////////////////////////////////////////////
	   	////////////////////////////////////////////////////////////////////////////////
	//				ALL MAJOR MINOR CHORDS
	///////////////////////////////////////////////////////////////////////////////
// Major key - hk1 is root
else if ((hk2d == 5 || hk2d == 8) &&
         (hk3d == 5 || hk3d == 8) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 5 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 5 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;
			return "";
			
			} else if 
			((hk2d == 8 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 8 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;
			return "";
				} else {
					rootnote = hk1;
					return "Major";
    }
}
// Major key - hk1 is Fifth
else if ((hk2d == 6 || hk2d == 10) &&
         (hk3d == 6 || hk3d == 10) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 6 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 6 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;
			return "Major";
			
			} else if 
			((hk2d == 10 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 10 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 9) % 12;
			return "";
				} else {
				rootnote = (hk1 + 5) % 12;
				bassnote = hk1;
					return "";
    }
}

// Major key - hk1 is Third
else if ((hk2d == 9 || hk2d == 4) &&
         (hk3d == 9 || hk3d == 4) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 9 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 9 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = 13;
			return "Major";
			
			} else if 
			((hk2d == 4 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 4 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 3) % 12;
			return "";
				} else {
				rootnote = (hk1 + 8) % 12;
				bassnote = hk1;
					return "";
    }
}

// Minor key - hk1 is root
else if ((hk2d == 4 || hk2d == 8) &&
         (hk3d == 4 || hk3d == 8) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 4 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 4 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;
			return "m";
			
			} else if 
			((hk2d == 8 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 8 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;
			return "m";
				} else {
					rootnote = hk1;
					return "Minor";
    }
}
// Minor key - hk1 is Fifth
else if ((hk2d == 6 || hk2d == 9) &&
         (hk3d == 6 || hk3d == 9) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 6 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 6 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;
			return "Minor";
			
			} else if 
			((hk2d == 9 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 9 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 8) % 12;
			return "m";
				} else {
				rootnote = (hk1 + 5) % 12;
				bassnote = hk1;
					return "m";
    }
}

// Minor key - hk1 is Third
else if ((hk2d == 10 || hk2d == 5) &&
         (hk3d == 10 || hk3d == 5) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 10 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 10 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 9) % 12;
				bassnote = 13;
			return "Minor";
			
			} else if 
			((hk2d == 5 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 5 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 4) % 12;
			return "m";
				} else {
				rootnote = (hk1 + 9) % 12;
				bassnote = hk1;
					return "m";
    }
}

// b5 key - hk1 is root
else if ((hk2d == 5 || hk2d == 7) &&
         (hk3d == 5 || hk3d == 7) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 5 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 5 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;
			return "b5";
			
			} else if 
			((hk2d == 7 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 7 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 6) % 12;
			return "b5";
				} else {
					rootnote = hk1;
					return "b5";
    }
}
// b5 key - hk1 is Fifth
else if ((hk2d == 5 || hk2d == 9) &&
         (hk3d == 5 || hk3d == 9) &&
         (hk4d == 5 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 5 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 5 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 4) % 12;
				bassnote = 13;
			return "b5";
			
			} else if 
			((hk2d == 9 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 9 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 4) % 12;
				bassnote = (hk1 + 8) % 12;
			return "b5";
				} else {
				rootnote = (hk1 + 4) % 12;
				bassnote = hk1;
					return "b5";
    }
}

// b5 key - hk1 is Third
else if ((hk2d == 9 || hk2d == 3) &&
         (hk3d == 9 || hk3d == 3) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 9 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 9 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = 13;
			return "b5";
			
			} else if 
			((hk2d == 3 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 3 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 2) % 12;
			return "b5";
				} else {
				rootnote = (hk1 + 8) % 12;
				bassnote = hk1;
					return "b5";
    }
}

	    // Check for sus2 root is first
else if ((hk2d == 3 || hk2d == 8) &&
         (hk3d == 3 || hk3d == 8) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 3 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 3 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 2) % 12;
				bassnote = 13;
			return "7sus4";
			
			} else if 
			((hk2d == 8 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 8 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 7) % 12;
				bassnote = 13;
			return "sus4";
				} else {
				rootnote = hk1;
				bassnote = 13;
					return "sus2";
    }
}

	    // Check for sus2 root is 5th
else if ((hk2d == 6 || hk2d == 8) &&
         (hk3d == 6 || hk3d == 8) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 6 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 6 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;
			return "sus2";
			
			} else if 
			((hk2d == 8 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 8 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 7) % 12;
				bassnote = 13;
			return "7sus4";
				} else {
				rootnote = hk1;
				bassnote = 13;
					return "sus4";
    }
}

	    // Check for sus2 root is 2nd
else if ((hk2d == 6 || hk2d == 11) &&
         (hk3d == 6 || hk3d == 11) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 6 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 6 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;
			return "sus4";
			
			} else if 
			((hk2d == 11 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 11 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 10) % 12;
				bassnote = 13;
			return "sus2";
				} else {
				rootnote = hk1;
				bassnote = 13;
					return "7sus4";
    }
}

	
// dim key - hk1 is root
else if ((hk2d == 4 || hk2d == 7) &&
         (hk3d == 4 || hk3d == 7) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 4 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 4 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;
			return "dim";
			
			} else if 
			((hk2d == 7 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 7 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 6) % 12;
			return "dim";
				} else {
					rootnote = hk1;
					return "dim";
    }
}
// dim key - hk1 is Fifth
else if ((hk2d == 7 || hk2d == 10) &&
         (hk3d == 7 || hk3d == 10) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 7 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 7 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 6) % 12;
				bassnote = 13;
			return "dim";
			
			} else if 
			((hk2d == 10 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 10 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 6) % 12;
				bassnote = (hk1 + 9) % 12;
			return "dim";
				} else {
				rootnote = (hk1 + 6) % 12;
				bassnote = hk1;
					return "dim";
    }
}

// dim key - hk1 is Third
else if ((hk2d == 10 || hk2d == 4) &&
         (hk3d == 10 || hk3d == 4) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 10 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 10 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 9) % 12;
				bassnote = 13;
			return "dim";
			
			} else if 
			((hk2d == 4 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 4 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 3) % 12;
			return "dim";
				} else {
				rootnote = (hk1 + 9) % 12;
				bassnote = hk1;
					return "dim";
    }
}
	
		// Check for aug
	else if ((hk2d == 5 || hk2d == 9) &&
         (hk3d == 5 || hk3d == 9) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {	 
		if 
			((hk2d == 5 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 5 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 4) % 12;
				bassnote = 13;
			return "aug";
			
			} else if 
			((hk2d == 9 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 9 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = 13;
			return "aug";
				} else {
				rootnote = hk1;
				bassnote = 13;
					return "aug";
    }
 }
	
// Check for min7no5
else if ((hk2d == 11 || hk2d == 4) &&
         (hk3d == 11 || hk3d == 4) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 11 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 11 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;
			return "min7no5";
			
			} else if 
			((hk2d == 4 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 4 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;
			return "min7no5";
				} else {
					rootnote = hk1;
					return "min7no5";
    }
}
// min7no5 key - hk1 is Seventh
else if ((hk2d == 3 || hk2d == 6) &&
         (hk3d == 3 || hk3d == 6) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 3 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 3 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 2) % 12;
				bassnote = 13;
			return "min7no5";
			
			} else if 
			((hk2d == 6 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 6 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 5) % 12;
			return "min7no5";
				} else {
				rootnote = (hk1 + 2) % 12;
				bassnote = hk1;
					return "min7no5";
    }
}

// min7no5 key - hk1 is third
else if ((hk2d == 8 || hk2d == 10) &&
         (hk3d == 8 || hk3d == 10) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 8 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 8  && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 7) % 12;
			return "min7no5";
			
			} else if 
			((hk2d == 10 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 10 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 9) % 12;
				bassnote = 13;
			return "min7no5";
				} else {
				rootnote = (hk1 + 9) % 12;
				bassnote = hk1;
					return "min7no5";
    }
}
	
	// Check for 7no5
else if ((hk2d == 11 || hk2d == 5) &&
         (hk3d == 11 || hk3d == 5) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 11 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 11 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;
			return "7no5";
			
			} else if 
			((hk2d == 5 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 5 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;
			return "7no5";
				} else {
					rootnote = hk1;
					return "7no5";
    }
}
// 7no5 key - hk1 is Seventh
else if ((hk2d == 3 || hk2d == 7) &&
         (hk3d == 3 || hk3d == 7) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 3 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 3 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 2) % 12;
				bassnote = 13;
			return "7no5";
			
			} else if 
			((hk2d == 7 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 7 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 6) % 12;
			return "7no5";
				} else {
				rootnote = (hk1 + 2) % 12;
				bassnote = hk1;
					return "7no5";
    }
}

// 7no5 key - hk1 is fifth
else if ((hk2d == 7 || hk2d == 9) &&
         (hk3d == 7 || hk3d == 9) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 7 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 7 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 6) % 12;
			return "7no5";
			
			} else if 
			((hk2d == 9 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 9 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = 13;
			return "7no5";
				} else {
				rootnote = (hk1 + 8) % 12;
				bassnote = hk1;
					return "7no5";
    }
}
	

// Check for maj7no5
else if ((hk2d == 12 || hk2d == 5) &&
         (hk3d == 12 || hk3d == 5) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 12 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 12 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;
			return "maj7no5";
			
			} else if 
			((hk2d == 5 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 5 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;
			return "maj7no5";
				} else {
					rootnote = hk1;
					return "maj7no5";
    }
}
// maj7no5 key - hk1 is Seventh
else if ((hk2d == 2 || hk2d == 6) &&
         (hk3d == 2 || hk3d == 6) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 2 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 2 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 1) % 12;
				bassnote = 13;
			return "maj7no5";
			
			} else if 
			((hk2d == 6 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 6 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 1) % 12;
				bassnote = (hk1 + 5) % 12;
			return "maj7no5";
				} else {
				rootnote = (hk1 + 1) % 12;
				bassnote = hk1;
					return "maj7no5";
    }
}

// maj7no5 key - hk1 is fifth
else if ((hk2d == 8 || hk2d == 9) &&
         (hk3d == 8 || hk3d == 9) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 8 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 8 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 7) % 12;
			return "maj7no5";
			
			} else if 
			((hk2d == 9 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 9 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 8) % 12;
				bassnote = 13;
			return "maj7no5";
				} else {
				rootnote = (hk1 + 8) % 12;
				bassnote = hk1;
					return "maj7no5";
    }
}
	
		// Check for min7no5
	else if ((hk2d == 4 || hk2d == 11) &&
         (hk3d == 4 || hk3d == 11) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
		rootnote = hk1;
		bassnote = 13;
        return "min7no5";
    }
	
			// Check for 7no5
	else if ((hk2d == 5 || hk2d == 11) &&
         (hk3d == 5 || hk3d == 11) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
		rootnote = hk1;
		bassnote = 13;
        return "7no5";
    }
		

// maj7no3 key - 
else if ((hk2d == 12 || hk2d == 8) &&
         (hk3d == 12 || hk3d == 8) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 12 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 12 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;
			return "maj7no3";
			
			} else if 
			((hk2d == 8 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 8 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;
			return "maj7no3";
				} else {
					rootnote = hk1;
					return "maj7no3";
    }
}
// maj7no3 key - hk1 is Seventh
else if ((hk2d == 2 || hk2d == 9) &&
         (hk3d == 2 || hk3d == 9) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 2 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 2 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 1) % 12;
				bassnote = 13;
			return "maj7no3";
			
			} else if 
			((hk2d == 9 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 9 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 1) % 12;
				bassnote = (hk1 + 8) % 12;
			return "maj7no3";
				} else {
				rootnote = (hk1 + 1) % 12;
				bassnote = hk1;
					return "maj7no3";
    }
}

// maj7no3 key - hk1 is fifth
else if ((hk2d == 5 || hk2d == 6) &&
         (hk3d == 5 || hk3d == 6) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 5 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 5 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 4) % 12;
			return "maj7no3";
			
			} else if 
			((hk2d == 6 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 6 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;
			return "maj7no3";
				} else {
				rootnote = (hk1 + 5) % 12;
				bassnote = hk1;
					return "maj7no3";
    }
}


//7 no 3 - hk1 is root
else if ((hk2d == 11 || hk2d == 8) &&
         (hk3d == 11 || hk3d == 8) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 11 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 11 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;
			return "7no3";
			
			} else if 
			((hk2d == 8 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 8 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;
			return "7no3";
				} else {
					rootnote = hk1;
					return "7no3";
    }
}
// 7no3 - hk1 is Seventh
else if ((hk2d == 3 || hk2d == 10) &&
         (hk3d == 3 || hk3d == 10) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 3 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 3 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 2) % 12;
				bassnote = 13;
			return "7no3";
			
			} else if 
			((hk2d == 10 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 10 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 9) % 12;
			return "7no3";
				} else {
				rootnote = (hk1 + 2) % 12;
				bassnote = hk1;
					return "7no3";
    }
}

// 7no3 - hk1 is fifth
else if ((hk2d == 4 || hk2d == 6) &&
         (hk3d == 4 || hk3d == 6) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
			if 
			((hk2d == 4 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 4 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 3) % 12;
			return "7no3";
			
			} else if 
			((hk2d == 6 && hk2 < hk1 && hk2 < hk3) ||
			(hk3d == 6 && hk3 < hk1 && hk3 < hk2)) {
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;
			return "7no3";
				} else {
				rootnote = (hk1 + 5) % 12;
				bassnote = hk1;
					return "7no3";
    }
}
				
		// Check for 7b5no3
	else if ((hk2d == 7 || hk2d == 11) &&
         (hk3d == 7 || hk3d == 11) &&
         (hk4d == 0 && hk5 == 0 && hk6 == 0)) {
		rootnote = hk1;
		bassnote = 13;
        return "7b5no3";
    }

		////////////////////////////////////////////////////////////////////////////////
	//				4 note chords
	//////////////////////////////////////////////////////////////////////////////
	
	////////////////////////////////////////////////////////////////////////////////
	//				ALL MAJOR 7TH CHORDS
	//////////////////////////////////////////////////////////////////////////////

    // Check Major 7: 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 12) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 12) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 12) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;		
        return "Maj7";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "Maj7";
    } else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;	
        return "Maj7";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "Maj7";
    }
}

    // Check Major 7: 1 is 7th
    else if ((hk2d == 2 || hk2d == 6 || hk2d == 9) && 
			 (hk3d == 2 || hk3d == 6 || hk3d == 9) && 
			 (hk4d == 2 || hk4d == 6 || hk4d == 9) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 1) % 12;	
				bassnote = 13;		
        return "Maj7";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "Maj7";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 8) % 12;	
        return "Maj7";
    } else {		
		rootnote = (hk1 + 1) % 12;	
		bassnote = hk1;
        return "Maj7";
    }
}

    // Check Major 7: 1 is 5th
    else if ((hk2d == 6 || hk2d == 10 || hk2d == 5) && 
			 (hk3d == 6 || hk3d == 10 || hk3d == 5) && 
			 (hk4d == 6 || hk4d == 10 || hk4d == 5) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 5) % 12;	
				bassnote = 13;		
        return "Maj7";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 9) % 12;	
        return "Maj7";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "Maj7";
    } else {		
		rootnote = (hk1 + 5) % 12;	
		bassnote = hk1;
        return "Maj7";
    }
}

    // Check Major 7: 1 is 3rd
    else if ((hk2d == 9 || hk2d == 4 || hk2d == 8) && 
			 (hk3d == 9 || hk3d == 4 || hk3d == 8) && 
			 (hk4d == 9 || hk4d == 4 || hk4d == 8) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 8) % 12;	
				bassnote = 13;		
        return "Maj7";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 3) % 12;	
        return "Maj7";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "Maj7";
    } else {		
		rootnote = (hk1 + 8) % 12;	
		bassnote = hk1;
        return "Maj7";
    }
}

    // Check 7: 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 11) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 11) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;		
        return "7";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "7";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "7";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "7";
    }
}

    // Check 7: 1 is 7th
    else if ((hk2d == 3 || hk2d == 7 || hk2d == 10) && 
			 (hk3d == 3 || hk3d == 7 || hk3d == 10) && 
			 (hk4d == 3 || hk4d == 7 || hk4d == 10) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 2) % 12;	
				bassnote = 13;		
        return "7";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 6) % 12;	
        return "7";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 9) % 12;	
        return "7";
    } else {		
		rootnote = (hk1 + 2) % 12;	
		bassnote = hk1;
        return "7";
    }
}

    // Check 7: 1 is 5th
    else if ((hk2d == 6 || hk2d == 10 || hk2d == 4) && 
			 (hk3d == 6 || hk3d == 10 || hk3d == 4) && 
			 (hk4d == 6 || hk4d == 10 || hk4d == 4) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 5) % 12;	
				bassnote = 13;		
        return "7";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 9) % 12;	
        return "7";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 3) % 12;	
        return "7";
    } else {		
		rootnote = (hk1 + 5) % 12;	
		bassnote = hk1;
        return "7";
    }
}

    // Check 7: 1 is 3rd
    else if ((hk2d == 9 || hk2d == 4 || hk2d == 7) && 
			 (hk3d == 9 || hk3d == 4 || hk3d == 7) && 
			 (hk4d == 9 || hk4d == 4 || hk4d == 7) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 8) % 12;	
				bassnote = 13;		
        return "7";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 3) % 12;	
        return "7";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 6) % 12;	
        return "7";
    } else {		
		rootnote = (hk1 + 8) % 12;	
		bassnote = hk1;
        return "7";
    }
}

    // Check min7: 1 is root
    else if ((hk2d == 4 || hk2d == 8 || hk2d == 11) && 
			 (hk3d == 4 || hk3d == 8 || hk3d == 11) && 
			 (hk4d == 4 || hk4d == 8 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;		
        return "min7";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "min7";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "min7";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "min7";
    }
}

    // Check min7: 1 is 7th
    else if ((hk2d == 3 || hk2d == 6 || hk2d == 10) && 
			 (hk3d == 3 || hk3d == 6 || hk3d == 10) && 
			 (hk4d == 3 || hk4d == 6 || hk4d == 10) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 2) % 12;	
				bassnote = 13;		
        return "min7";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = 13;	
        return "Maj6";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 9) % 12;	
        return "min7";
    } else {		
		rootnote = (hk1 + 2) % 12;	
		bassnote = hk1;
        return "min7";
    }
}

    // Check min7: 1 is 5th
    else if ((hk2d == 6 || hk2d == 9 || hk2d == 4) && 
			 (hk3d == 6 || hk3d == 9 || hk3d == 4) && 
			 (hk4d == 6 || hk4d == 9 || hk4d == 4) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 5) % 12;	
				bassnote = 13;		
        return "min7";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = 13;	
        return "Maj6";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 3) % 12;	
        return "min7";
    } else {		
		rootnote = (hk1 + 5) % 12;	
		bassnote = hk1;
        return "min7";
    }
}

    // Check min7: 1 is 3rd
    else if ((hk2d == 10 || hk2d == 5 || hk2d == 8) && 
			 (hk3d == 10 || hk3d == 5 || hk3d == 8) && 
			 (hk4d == 10 || hk4d == 5 || hk4d == 8) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 9) % 12;	
				bassnote = 13;		
        return "min7";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "min7";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "min7";
    } else {		
		rootnote = hk1;	
		bassnote = 13;
        return "maj6";
    }
}


			// Check for add9 or add2
	else if ((hk2d == 4 ||hk2d == 8 || hk2d == 3) &&
         (hk3d == 4 ||hk3d == 8 || hk3d == 3) &&
         (hk4d == 4 ||hk4d == 8 || hk4d == 3) && 
		 (hk5d == 0 && hk6 == 0)) {
		 	rootnote = hk1;
			bassnote = 13;
		if (abs(hk1 - hk2) == 2 ||
			abs(hk1 - hk3) == 2 ||
			abs(hk1 - hk4) == 2 ||
			abs(hk1 - hk5) == 2 ||
			abs(hk1 - hk6) == 2 ||
			abs(hk2 - hk3) == 2 ||
			abs(hk2 - hk4) == 2 ||
			abs(hk2 - hk5) == 2 ||
			abs(hk2 - hk6) == 2 ||
			abs(hk3 - hk4) == 2 ||
			abs(hk3 - hk5) == 2 ||
			abs(hk3 - hk6) == 2 ||
			abs(hk4 - hk5) == 2 ||
			abs(hk4 - hk6) == 2 ||
			abs(hk5 - hk6) == 2) {
			return "m(add2)";}
		else {return "m(add9)";}
	}	
	
			// Check for add9 or add2
	else if ((hk2d == 5 ||hk2d == 8 || hk2d == 3) &&
         (hk3d == 5 ||hk3d == 8 || hk3d == 3) &&
         (hk4d == 5 ||hk4d == 8 || hk4d == 3) && 
		 (hk5d == 0 && hk6 == 0)) {
		 	rootnote = hk1;
			bassnote = 13;
		if (abs(hk1 - hk2) == 2 ||
			abs(hk1 - hk3) == 2 ||
			abs(hk1 - hk4) == 2 ||
			abs(hk1 - hk5) == 2 ||
			abs(hk1 - hk6) == 2 ||
			abs(hk2 - hk3) == 2 ||
			abs(hk2 - hk4) == 2 ||
			abs(hk2 - hk5) == 2 ||
			abs(hk2 - hk6) == 2 ||
			abs(hk3 - hk4) == 2 ||
			abs(hk3 - hk5) == 2 ||
			abs(hk3 - hk6) == 2 ||
			abs(hk4 - hk5) == 2 ||
			abs(hk4 - hk6) == 2 ||
			abs(hk5 - hk6) == 2) {
			return "(add2)";}
		else {return "(add9)";}
	}		

			// Check for add11 or add4
	else if ((hk2d == 5 ||hk2d == 8 || hk2d == 6) &&
         (hk3d == 5 ||hk3d == 8 || hk3d == 6) &&
         (hk4d == 5 ||hk4d == 8 || hk4d == 6) && 
		 (hk5d == 0 && hk6 == 0)) {
		 	rootnote = hk1;
			bassnote = 13;
		if (abs(hk1 - hk2) == 17 ||
			abs(hk1 - hk3) == 17 ||
			abs(hk1 - hk4) == 17 ||
			abs(hk1 - hk5) == 17 ||
			abs(hk1 - hk6) == 17 ||
			abs(hk2 - hk3) == 17 ||
			abs(hk2 - hk4) == 17 ||
			abs(hk2 - hk5) == 17 ||
			abs(hk2 - hk6) == 17 ||
			abs(hk3 - hk4) == 17 ||
			abs(hk3 - hk5) == 17 ||
			abs(hk3 - hk6) == 17 ||
			abs(hk4 - hk5) == 17 ||
			abs(hk4 - hk6) == 17 ||
			abs(hk5 - hk6) == 17) {
			return "(add11)";}
		else {return "(add4)";}
	}		
			// Check for m(add11) or m(add4)
	else if ((hk2d == 4 ||hk2d == 8 || hk2d == 6) &&
         (hk3d == 4 ||hk3d == 8 || hk3d == 6) &&
         (hk4d == 4 ||hk4d == 8 || hk4d == 6) && 
		 (hk5d == 0 && hk6 == 0)) {
		 	rootnote = hk1;
			bassnote = 13;
		if (abs(hk1 - hk2) == 17 ||
			abs(hk1 - hk3) == 17 ||
			abs(hk1 - hk4) == 17 ||
			abs(hk1 - hk5) == 17 ||
			abs(hk1 - hk6) == 17 ||
			abs(hk2 - hk3) == 17 ||
			abs(hk2 - hk4) == 17 ||
			abs(hk2 - hk5) == 17 ||
			abs(hk2 - hk6) == 17 ||
			abs(hk3 - hk4) == 17 ||
			abs(hk3 - hk5) == 17 ||
			abs(hk3 - hk6) == 17 ||
			abs(hk4 - hk5) == 17 ||
			abs(hk4 - hk6) == 17 ||
			abs(hk5 - hk6) == 17) {
			return "m(add11)";}
		else {return "m(add4)";}
	}		


    // Check dim7
    else if ((hk2d == 4 || hk2d == 7 || hk2d == 10) && 
			 (hk3d == 4 || hk3d == 7 || hk3d == 10) && 
			 (hk4d == 4 || hk4d == 7 || hk4d == 10) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 3) % 12;	
				bassnote = 13;	
        return "dim7";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 6) % 12;	
				bassnote = 13;
        return "dim7";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = 13;	
        return "dim7";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "dim7";
    }
}

   // Check 7#5: 1 is root
    else if ((hk2d == 5 || hk2d == 9 || hk2d == 11) && 
			 (hk3d == 5 || hk3d == 9 || hk3d == 11) && 
			 (hk4d == 5 || hk4d == 9 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;		
        return "7#5";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 8) % 12;	
        return "7#5";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "7#5";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "7#5";
    }
}

    // Check 7#5: 1 is 7th
    else if ((hk2d == 3 || hk2d == 7 || hk2d == 11) && 
			 (hk3d == 3 || hk3d == 7 || hk3d == 11) && 
			 (hk4d == 3 || hk4d == 7 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 2) % 12;	
				bassnote = 13;		
        return "7#5";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 6) % 12;	
        return "7#5";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 10) % 12;	
        return "7#5";
    } else {		
		rootnote = (hk1 + 2) % 12;	
		bassnote = hk1;
        return "7#5";
    }
}

    // Check 7#5: 1 is 5th
    else if ((hk2d == 5 || hk2d == 9 || hk2d == 3) && 
			 (hk3d == 5 || hk3d == 9 || hk3d == 3) && 
			 (hk4d == 5 || hk4d == 9 || hk4d == 3) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 4) % 12;	
				bassnote = 13;		
        return "7#5";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 4) % 12;	
				bassnote = (hk1 + 8) % 12;	
        return "7#5";
    } else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 4) % 12;	
				bassnote = (hk1 + 2) % 12;	
        return "7#5";
    } else {		
		rootnote = (hk1 + 4) % 12;	
		bassnote = hk1;
        return "7#5";
    }
}

    // Check 7#5: 1 is 3rd
    else if ((hk2d == 9 || hk2d == 5 || hk2d == 7) && 
			 (hk3d == 9 || hk3d == 5 || hk3d == 7) && 
			 (hk4d == 9 || hk4d == 5 || hk4d == 7) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 8) % 12;	
				bassnote = 13;		
        return "7#5";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "7#5";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 6) % 12;	
        return "7#5";
    } else {		
		rootnote = (hk1 + 8) % 12;	
		bassnote = hk1;
        return "7#5";
    }
}
   // Check min7#5: 1 is root
    else if ((hk2d == 4 || hk2d == 9 || hk2d == 11) && 
			 (hk3d == 4 || hk3d == 9 || hk3d == 11) && 
			 (hk4d == 4 || hk4d == 9 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;		
        return "min7#5";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 8) % 12;	
        return "min7#5";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "min7#5";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "min7#5";
    }
}

    // Check min7#5: 1 is 7th
    else if ((hk2d == 3 || hk2d == 6 || hk2d == 11) && 
			 (hk3d == 3 || hk3d == 6 || hk3d == 11) && 
			 (hk4d == 3 || hk4d == 6 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 2) % 12;	
				bassnote = 13;		
        return "min7#5";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "min7#5";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 10) % 12;	
        return "min7#5";
    } else {		
		rootnote = (hk1 + 2) % 12;	
		bassnote = hk1;
        return "min7#5";
    }
}

    // Check min7#5: 1 is 5th
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 3) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 3) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 3) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 4) % 12;	
				bassnote = 13;		
        return "min7#5";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 4) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "min7#5";
    } else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 4) % 12;	
				bassnote = (hk1 + 2) % 12;	
        return "min7#5";
    } else {		
		rootnote = (hk1 + 4) % 12;	
		bassnote = hk1;
        return "min7#5";
    }
}

    // Check min7#5: 1 is 3rd
    else if ((hk2d == 10 || hk2d == 6 || hk2d == 8) && 
			 (hk3d == 10 || hk3d == 6 || hk3d == 8) && 
			 (hk4d == 10 || hk4d == 6 || hk4d == 8) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 9) % 12;	
				bassnote = 13;		
        return "min7#5";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "min7#5";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "min7#5";
    } else {		
		rootnote = (hk1 + 9) % 12;	
		bassnote = hk1;
        return "min7#5";
    }
}

   // Check Maj7#5: 1 is root
    else if ((hk2d == 5 || hk2d == 9 || hk2d == 12) && 
			 (hk3d == 5 || hk3d == 9 || hk3d == 12) && 
			 (hk4d == 5 || hk4d == 9 || hk4d == 12) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;		
        return "Maj7#5";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 8) % 12;	
        return "Maj7#5";
    } else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;	
        return "Maj7#5";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "Maj7#5";
    }
}

    // Check Maj7#5: 1 is 7th
    else if ((hk2d == 2 || hk2d == 6 || hk2d == 10) && 
			 (hk3d == 2 || hk3d == 6 || hk3d == 10) && 
			 (hk4d == 2 || hk4d == 6 || hk4d == 10) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 1) % 12;	
				bassnote = 13;		
        return "Maj7#5";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "Maj7#5";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 9) % 12;	
        return "Maj7#5";
    } else {		
		rootnote = (hk1 + 1) % 12;	
		bassnote = hk1;
        return "Maj7#5";
    }
}

    // Check Maj7#5: 1 is 5th
    else if ((hk2d == 5 || hk2d == 9 || hk2d == 4) && 
			 (hk3d == 5 || hk3d == 9 || hk3d == 4) && 
			 (hk4d == 5 || hk4d == 9 || hk4d == 4) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 4) % 12;	
				bassnote = 13;		
        return "Maj7#5";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 4) % 12;	
				bassnote = (hk1 + 8) % 12;	
        return "Maj7#5";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 4) % 12;	
				bassnote = (hk1 + 3) % 12;	
        return "Maj7#5";
    } else {		
		rootnote = (hk1 + 4) % 12;	
		bassnote = hk1;
        return "Maj7#5";
    }
}

    // Check Maj7#5: 1 is 3rd
    else if ((hk2d == 9 || hk2d == 5 || hk2d == 8) && 
			 (hk3d == 9 || hk3d == 5 || hk3d == 8) && 
			 (hk4d == 9 || hk4d == 5 || hk4d == 8) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 8) % 12;	
				bassnote = 13;		
        return "Maj7#5";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "Maj7#5";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "Maj7#5";
    } else {		
		rootnote = (hk1 + 8) % 12;	
		bassnote = hk1;
        return "Maj7#5";
    }
}

    // Check Major 7b5: 1 is root
    else if ((hk2d == 5 || hk2d == 7 || hk2d == 12) && 
			 (hk3d == 5 || hk3d == 7 || hk3d == 12) && 
			 (hk4d == 5 || hk4d == 7 || hk4d == 12) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;		
        return "Maj7b5";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 6) % 12;	
        return "Maj7b5";
    } else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;	
        return "Maj7b5";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "Maj7b5";
    }
}

    // Check Major 7b5: 1 is 7th
    else if ((hk2d == 2 || hk2d == 6 || hk2d == 8) && 
			 (hk3d == 2 || hk3d == 6 || hk3d == 8) && 
			 (hk4d == 2 || hk4d == 6 || hk4d == 8) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 1) % 12;	
				bassnote = 13;		
        return "Maj7b5";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "Maj7b5";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "Maj7b5";
    } else {		
		rootnote = (hk1 + 1) % 12;	
		bassnote = hk1;
        return "Maj7b5";
    }
}

    // Check Major 7b5: 1 is 5th
    else if ((hk2d == 7 || hk2d == 11 || hk2d == 6) && 
			 (hk3d == 7 || hk3d == 11 || hk3d == 6) && 
			 (hk4d == 7 || hk4d == 11 || hk4d == 6) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 6) % 12;	
				bassnote = 13;		
        return "Maj7b5";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 6) % 12;	
				bassnote = (hk1 + 10) % 12;	
        return "Maj7b5";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 6) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "Maj7b5";
    } else {		
		rootnote = (hk1 + 6) % 12;	
		bassnote = hk1;
        return "Maj7b5";
    }
}

    // Check Major 7b5: 1 is 3rd
    else if ((hk2d == 9 || hk2d == 3 || hk2d == 8) && 
			 (hk3d == 9 || hk3d == 3 || hk3d == 8) && 
			 (hk4d == 9 || hk4d == 3 || hk4d == 8) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 8) % 12;	
				bassnote = 13;		
        return "Maj7b5";
    } else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 2) % 12;	
        return "Maj7b5";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "Maj7b5";
    } else {		
		rootnote = (hk1 + 8) % 12;	
		bassnote = hk1;
        return "Maj7b5";
    }
}

    // Check 7b5: 1 is root
    else if ((hk2d == 5 || hk2d == 7 || hk2d == 11) && 
			 (hk3d == 5 || hk3d == 7 || hk3d == 11) && 
			 (hk4d == 5 || hk4d == 7 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 6) % 12;	
				bassnote = (hk1 + 4) % 12;		
        return "7b5";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 6) % 12;
				bassnote = 13;
        return "7b5";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "7b5";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "7b5";
    }
}

    // Check 7b5: 1 is 7th
    else if ((hk2d == 3 || hk2d == 7 || hk2d == 9) && 
			 (hk3d == 3 || hk3d == 7 || hk3d == 9) && 
			 (hk4d == 3 || hk4d == 7 || hk4d == 9) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 2) % 12;	
				bassnote = 13;		
        return "7b5";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = (hk1 + 6) % 12;	
        return "7b5";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = 13;	
        return "7b5";
    } else {		
		rootnote = (hk1 + 2) % 12;	
		bassnote = 13;
        return "7b5";
    }
}


    // Check m7b5: 1 is root
    else if ((hk2d == 4 || hk2d == 7 || hk2d == 11) && 
			 (hk3d == 4 || hk3d == 7 || hk3d == 11) && 
			 (hk4d == 4 || hk4d == 7 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;		
        return "m7b5";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 6) % 12;	
        return "m7b5";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 10) % 12;	
				bassnote = 13;
        return "min6";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "m7b5";
    }
}

    // Check m7b5: 1 is 7th
    else if ((hk2d == 3 || hk2d == 6 || hk2d == 9) && 
			 (hk3d == 3 || hk3d == 6 || hk3d == 9) && 
			 (hk4d == 3 || hk4d == 6 || hk4d == 9) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 2) % 12;	
				bassnote = 13;		
        return "m7b5";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 5) % 12;		
				bassnote = 13;	
        return "min6";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 8) % 12;	
        return "m7b5";
    } else {		
		rootnote = (hk1 + 2) % 12;	
		bassnote = hk1;
        return "m7b5";
    }
}

    // Check m7b5: 1 is 5th
    else if ((hk2d == 7 || hk2d == 10 || hk2d == 5) && 
			 (hk3d == 7 || hk3d == 10 || hk3d == 5) && 
			 (hk4d == 7 || hk4d == 10 || hk4d == 5) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 6) % 12;	
				bassnote = 13;		
        return "m7b5";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 9) % 12;		
				bassnote = 13;	
        return "min6";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 6) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "m7b5";
    } else {		
		rootnote = (hk1 + 6) % 12;	
		bassnote = hk1;
        return "m7b5";
    }
}

    // Check m7b5: 1 is 3rd
    else if ((hk2d == 10 || hk2d == 4 || hk2d == 8) && 
			 (hk3d == 10 || hk3d == 4 || hk3d == 8) && 
			 (hk4d == 10 || hk4d == 4 || hk4d == 8) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 9) % 12;	
				bassnote = 13;		
        return "m7b5";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = (hk1 + 3) % 12;	
        return "m7b5";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "m7b5";
    } else {		
		rootnote = hk1;	
		bassnote = 13;
        return "min6";
    }
}

   // Check MinMaj7: 1 is root
    else if ((hk2d == 4 || hk2d == 8 || hk2d == 12) && 
			 (hk3d == 4 || hk3d == 8 || hk3d == 12) && 
			 (hk4d == 4 || hk4d == 8 || hk4d == 12) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;		
        return "minMaj7";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "minMaj7";
    } else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;	
        return "minMaj7";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "minMaj7";
    }
}

    // Check MinMaj7: 1 is 7th
    else if ((hk2d == 2 || hk2d == 5 || hk2d == 9) && 
			 (hk3d == 2 || hk3d == 5 || hk3d == 9) && 
			 (hk4d == 2 || hk4d == 5 || hk4d == 9) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 1) % 12;	
				bassnote = 13;		
        return "minMaj7";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "minMaj7";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 8) % 12;	
        return "minMaj7";
    } else {		
		rootnote = (hk1 + 1) % 12;	
		bassnote = hk1;
        return "minMaj7";
    }
}

    // Check MinMaj7: 1 is 5th
    else if ((hk2d == 6 || hk2d == 9 || hk2d == 5) && 
			 (hk3d == 6 || hk3d == 9 || hk3d == 5) && 
			 (hk4d == 6 || hk4d == 9 || hk4d == 5) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 5) % 12;	
				bassnote = 13;		
        return "minMaj7";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 8) % 12;	
        return "minMaj7";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "minMaj7";
    } else {		
		rootnote = (hk1 + 5) % 12;	
		bassnote = hk1;
        return "minMaj7";
    }
}

    // Check MinMaj7: 1 is 3rd
    else if ((hk2d == 10 || hk2d == 5 || hk2d == 9) && 
			 (hk3d == 10 || hk3d == 5 || hk3d == 9) && 
			 (hk4d == 10 || hk4d == 5 || hk4d == 9) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 9) % 12;	
				bassnote = 13;		
        return "minMaj7";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "minMaj7";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 9) % 12;	
				bassnote = (hk1 + 8) % 12;	
        return "minMaj7";
    } else {		
		rootnote = (hk1 + 9) % 12;	
		bassnote = hk1;
        return "minMaj7";
    }
}

   // Check Maj7sus2: 1 is root
    else if ((hk2d == 3 || hk2d == 8 || hk2d == 12) && 
			 (hk3d == 3 || hk3d == 8 || hk3d == 12) && 
			 (hk4d == 3 || hk4d == 8 || hk4d == 12) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;	
				bassnote = (hk1 + 2) % 12;
        return "Maj7sus2";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "Maj7sus2";
    } else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;	
        return "Maj7sus2";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "Maj7sus2";
    }
}

    // Check Maj7sus2: 1 is 7th
    else if ((hk2d == 2 || hk2d == 4 || hk2d == 9) && 
			 (hk3d == 2 || hk3d == 4 || hk3d == 9) && 
			 (hk4d == 2 || hk4d == 4 || hk4d == 9) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 1) % 12;	
				bassnote = 13;		
        return "Maj7sus2";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 3) % 12;
        return "Maj7sus2";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 8) % 12;	
        return "Maj7sus2";
    } else {		
		rootnote = (hk1 + 1) % 12;	
		bassnote = hk1;
        return "Maj7sus2";
    }
}

    // Check Maj7sus2: 1 is 5th
    else if ((hk2d == 6 || hk2d == 8 || hk2d == 5) && 
			 (hk3d == 6 || hk3d == 8 || hk3d == 5) && 
			 (hk4d == 6 || hk4d == 8 || hk4d == 5) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 5) % 12;	
				bassnote = 13;		
        return "Maj7sus2";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "Maj7sus2";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "Maj7sus2";
    } else {		
		rootnote = (hk1 + 5) % 12;	
		bassnote = hk1;
        return "Maj7sus2";
    }
}

    // Check Maj7sus2: 1 is 3rd
    else if ((hk2d == 11 || hk2d == 6 || hk2d == 10) && 
			 (hk3d == 11 || hk3d == 6 || hk3d == 10) && 
			 (hk4d == 11 || hk4d == 6 || hk4d == 10) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 10) % 12;	
				bassnote = 13;		
        return "Maj7sus2";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 10) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "Maj7sus2";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 10) % 12;	
				bassnote = (hk1 + 9) % 12;	
        return "Maj7sus2";
    } else {		
		rootnote = (hk1 + 10) % 12;	
		bassnote = hk1;
        return "Maj7sus2";
    }
}
   // Check 7sus4: 1 is root
    else if ((hk2d == 6 || hk2d == 8 || hk2d == 11) && 
			 (hk3d == 6 || hk3d == 8 || hk3d == 11) && 
			 (hk4d == 6 || hk4d == 8 || hk4d == 11) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 5) % 12;		
        return "7sus4";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "7sus4";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "7sus4";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "7sus4";
    }
}

    // Check 7sus4: 1 is 7th
    else if ((hk2d == 3 || hk2d == 8 || hk2d == 10) && 
			 (hk3d == 3 || hk3d == 8 || hk3d == 10) && 
			 (hk4d == 3 || hk4d == 8 || hk4d == 10) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 2) % 12;	
				bassnote = 13;		
        return "7sus4";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 7) % 12;	
        return "7sus4";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = (hk1 + 9) % 12;	
        return "7sus4";
    } else {		
		rootnote = (hk1 + 2) % 12;	
		bassnote = hk1;
        return "7sus4";
    }
}

    // Check 7sus4: 1 is 5th
    else if ((hk2d == 6 || hk2d == 11 || hk2d == 4) && 
			 (hk3d == 6 || hk3d == 11 || hk3d == 4) && 
			 (hk4d == 6 || hk4d == 11 || hk4d == 4) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 5) % 12;	
				bassnote = 13;		
        return "7sus4";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 10) % 12;	
        return "7sus4";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 3) % 12;	
        return "7sus4";
    } else {		
		rootnote = (hk1 + 5) % 12;		
		bassnote = hk1;
        return "7add4";
    }
}

    // Check 7sus4: 1 is 3rd
    else if ((hk2d == 8 || hk2d == 2 || hk2d == 6) && 
			 (hk3d == 8 || hk3d == 2 || hk3d == 6) && 
			 (hk4d == 8 || hk4d == 2 || hk4d == 6) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 7) % 12;	
				bassnote = 13;		
        return "7sus4";
    } else if ((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 7) % 12;	
				bassnote = (hk1 + 1) % 12;	
        return "7add4";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 7) % 12;	
				bassnote = (hk1 + 5) % 12;	
        return "7sus4";
    } else {		
		rootnote = (hk1 + 7) % 12;	
		bassnote = hk1;
        return "7sus4";
    }
}
   // Check Maj7Sus4: 1 is root
    else if ((hk2d == 6 || hk2d == 8 || hk2d == 12) && 
			 (hk3d == 6 || hk3d == 8 || hk3d == 12) && 
			 (hk4d == 6 || hk4d == 8 || hk4d == 12) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = hk1;
				bassnote = (hk1 + 5) % 12;		
        return "Maj7Sus4";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 7) % 12;
				bassnote = 13;	
        return "7add4";
    } else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;	
        return "Maj7Sus4";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "Maj7Sus4";
    }
}

    // Check Maj7Sus4: 1 is 7th
    else if ((hk2d == 2 || hk2d == 7 || hk2d == 9) && 
			 (hk3d == 2 || hk3d == 7 || hk3d == 9) && 
			 (hk4d == 2 || hk4d == 7 || hk4d == 9) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 1) % 12;	
				bassnote = 13;		
        return "Maj7Sus4";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 1) % 12;	
				bassnote = (hk1 + 6) % 12;	
        return "Maj7Sus4";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 8) % 12;	
				bassnote = 13;	
        return "7add4";
    } else {		
		rootnote = (hk1 + 1) % 12;	
		bassnote = hk1;
        return "Maj7Sus4";
    }
}

    // Check Maj7Sus4: 1 is 5th
    else if ((hk2d == 6 || hk2d == 11 || hk2d == 5) && 
			 (hk3d == 6 || hk3d == 11 || hk3d == 5) && 
			 (hk4d == 6 || hk4d == 11 || hk4d == 5) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 5) % 12;	
				bassnote = 13;		
        return "Maj7Sus4";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 10) % 12;	
        return "Maj7Sus4";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 5) % 12;	
				bassnote = (hk1 + 4) % 12;	
        return "Maj7Sus4";
    } else {		
		rootnote = hk1;	
		bassnote = 13;
        return "7add4";
    }
}

    // Check Maj7Sus4: 1 is 3rd
    else if ((hk2d == 8 || hk2d == 3 || hk2d == 7) && 
			 (hk3d == 8 || hk3d == 3 || hk3d == 7) && 
			 (hk4d == 8 || hk4d == 3 || hk4d == 7) &&
			hk5 == 0 && hk6 == 0) {
    if 	((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))	{	
				rootnote = (hk1 + 7) % 12;	
				bassnote = 13;		
        return "Maj7Sus4";
    } else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3)) 			{
				rootnote = (hk1 + 2) % 12;	
				bassnote = 13;	
        return "7add4";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3))			{
				rootnote = (hk1 + 7) % 12;	
				bassnote = (hk1 + 6) % 12;	
        return "Maj7Sus4";
    } else {		
		rootnote = (hk1 + 7) % 12;	
		bassnote = hk1;
        return "Maj7Sus4";
    }
}
			// Check for 7sus2
	else if ((hk2d == 3 ||hk2d == 8 || hk2d == 11) &&
         (hk3d == 3 ||hk3d == 8 || hk3d == 11) &&
         (hk4d == 3 ||hk4d == 8 || hk4d == 11) && 
		 (hk5d == 0 && hk6 == 0)) {
		rootnote = hk1;
		bassnote = 13;
        return "7sus2";
    }


	////////////////////////////////////////////////////////////////////////////////
	//				ALL 5 note chords
	//////////////////////////////////////////////////////////////////////////////
	
			// Check for maj7(add11) or maj7(add4)
	else if ((hk2d == 5 ||hk2d == 8 || hk2d == 6 || hk2d == 12) &&
         (hk3d == 5 ||hk3d == 8 || hk3d == 6 || hk3d == 12) &&
         (hk4d == 5 ||hk4d == 8 || hk4d == 6 || hk4d == 12) && 
		 (hk5d == 5 ||hk5d == 8 || hk5d == 6 || hk5d == 12) &&
		 (hk6d == 0)) {
		 	rootnote = hk1;
			bassnote = 13;
		
		if (abs(hk1 - hk2) == 17 ||
			abs(hk1 - hk3) == 17 ||
			abs(hk1 - hk4) == 17 ||
			abs(hk1 - hk5) == 17 ||
			abs(hk1 - hk6) == 17 ||
			abs(hk2 - hk3) == 17 ||
			abs(hk2 - hk4) == 17 ||
			abs(hk2 - hk5) == 17 ||
			abs(hk2 - hk6) == 17 ||
			abs(hk3 - hk4) == 17 ||
			abs(hk3 - hk5) == 17 ||
			abs(hk3 - hk6) == 17 ||
			abs(hk4 - hk5) == 17 ||
			abs(hk4 - hk6) == 17 ||
			abs(hk5 - hk6) == 17) {
			return "maj7(add11)";}
		else {return "maj7(add4)";}
	}
	
			// Check for 7(add11) or 7(add4)
	else if ((hk2d == 5 ||hk2d == 8 || hk2d == 6 || hk2d == 11) &&
         (hk3d == 5 ||hk3d == 8 || hk3d == 6 || hk3d == 11) &&
         (hk4d == 5 ||hk4d == 8 || hk4d == 6 || hk4d == 11) && 
		 (hk5d == 5 ||hk5d == 8 || hk5d == 6 || hk5d == 11) &&
		 (hk6d == 0)) {
		 	rootnote = hk1;
			bassnote = 13;
		if (abs(hk1 - hk2) == 17 ||
			abs(hk1 - hk3) == 17 ||
			abs(hk1 - hk4) == 17 ||
			abs(hk1 - hk5) == 17 ||
			abs(hk1 - hk6) == 17 ||
			abs(hk2 - hk3) == 17 ||
			abs(hk2 - hk4) == 17 ||
			abs(hk2 - hk5) == 17 ||
			abs(hk2 - hk6) == 17 ||
			abs(hk3 - hk4) == 17 ||
			abs(hk3 - hk5) == 17 ||
			abs(hk3 - hk6) == 17 ||
			abs(hk4 - hk5) == 17 ||
			abs(hk4 - hk6) == 17 ||
			abs(hk5 - hk6) == 17) {
			return "7(add11)";}
		else {return "7(add4)";}
	}
	
			// Check for min7(add11) or min7(add4)
	else if ((hk2d == 4 ||hk2d == 8 || hk2d == 6 || hk2d == 11) &&
         (hk3d == 4 ||hk3d == 8 || hk3d == 6 || hk3d == 11) &&
         (hk4d == 4 ||hk4d == 8 || hk4d == 6 || hk4d == 11) && 
		 (hk5d == 4 ||hk5d == 8 || hk5d == 6 || hk5d == 11) &&
		 (hk6d == 0) && (hk7d == 0)) {
		 	rootnote = hk1;
			bassnote = 13;
			if (hk1 <= hk2 && hk1 <= hk3 && hk1 <= hk4 && hk1 <= hk5) {return "m Pentatonic";}
		else if (abs(hk1 - hk2) == 17 ||
			abs(hk1 - hk3) == 17 ||
			abs(hk1 - hk4) == 17 ||
			abs(hk1 - hk5) == 17 ||
			abs(hk1 - hk6) == 17 ||
			abs(hk2 - hk3) == 17 ||
			abs(hk2 - hk4) == 17 ||
			abs(hk2 - hk5) == 17 ||
			abs(hk2 - hk6) == 17 ||
			abs(hk3 - hk4) == 17 ||
			abs(hk3 - hk5) == 17 ||
			abs(hk3 - hk6) == 17 ||
			abs(hk4 - hk5) == 17 ||
			abs(hk4 - hk6) == 17 ||
			abs(hk5 - hk6) == 17) {
			return "min7(add11)";}
		else {return "min7(add4)";}
	}

   // Check Major 9: 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 12 || hk2d == 3) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 12 || hk3d == 3) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 12 || hk4d == 3) &&
			(hk5d == 5 || hk5d == 8 || hk5d == 12 || hk5d == 3)
			&& hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;		
        return "Maj9";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "Maj9";
    } else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 12 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 11) % 12;	
        return "Maj9";
	} else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 2) % 12;	
        return "Maj9";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "Maj9";
    }
}

   // Check Major 9: 1 is 7th
    else if ((hk2d == 2 || hk2d == 6 || hk2d == 9 || hk2d == 4) && 
			 (hk3d == 2 || hk3d == 6 || hk3d == 9 || hk3d == 4) && 
			 (hk4d == 2 || hk4d == 6 || hk4d == 9 || hk4d == 4) &&
			(hk5d == 2 || hk5d == 6 || hk5d == 9 || hk5d == 4)
			&& hk6 == 0) {
    if 	((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 2 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 1) % 12;
				bassnote = 13;		
        return "Maj9";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 1) % 12;
				bassnote = (hk1 + 5) % 12;	
        return "Maj9";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 1) % 12;
				bassnote = (hk1 + 8) % 12;	
        return "Maj9";
	} else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 4 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 1) % 12;
				bassnote = (hk1 + 3) % 12;	
        return "Maj9";
    } else {		
		rootnote = (hk1 + 1) % 12;
		bassnote = hk1;
        return "Maj9";
    }
}

   // Check Major 9: 1 is 5th
    else if ((hk2d == 6 || hk2d == 10 || hk2d == 5 || hk2d == 8) && 
			 (hk3d == 6 || hk3d == 10 || hk3d == 5 || hk3d == 8) && 
			 (hk4d == 6 || hk4d == 10 || hk4d == 5 || hk4d == 8) &&
			(hk5d == 6 || hk5d == 10 || hk5d == 5 || hk5d == 8)
			&& hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;		
        return "Maj9";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 10 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 9) % 12;	
        return "Maj9";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 4) % 12;	
        return "Maj9";
	} else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 7) % 12;	
        return "Maj9";
    } else {		
		rootnote = (hk1 + 5) % 12;
		bassnote = hk1;
        return "Maj9";
    }
}

   // Check Major 9: 1 is 3rd
    else if ((hk2d == 9 || hk2d == 4 || hk2d == 8 || hk2d == 11) && 
			 (hk3d == 9 || hk3d == 4 || hk3d == 8 || hk3d == 11) && 
			 (hk4d == 9 || hk4d == 4 || hk4d == 8 || hk4d == 11) &&
			(hk5d == 9 || hk5d == 4 || hk5d == 8 || hk5d == 11)
			&& hk6 == 0) {
    if 	((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 8) % 12;
				bassnote = 13;		
        return "Maj9";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 4 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 3) % 12;	
        return "Maj9";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 7) % 12;	
        return "Maj9";
	} else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 10) % 12;	
        return "Maj9";
    } else {		
		rootnote = (hk1 + 8) % 12;
		bassnote = hk1;
        return "Maj9";
    }
}

   // Check Major 9: 1 is 9th
    else if ((hk2d == 11 || hk2d == 3 || hk2d == 6 || hk2d == 10) && 
			 (hk3d == 11 || hk3d == 3 || hk3d == 6 || hk3d == 10) && 
			 (hk4d == 11 || hk4d == 3 || hk4d == 6 || hk4d == 10) &&
			(hk5d == 11 || hk5d == 3 || hk5d == 6 || hk5d == 10)
			&& hk6 == 0) {
    if 	((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = 13;		
        return "Maj9";
    } else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 2) % 12;	
        return "Maj9";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 5) % 12;	
        return "Maj9";
	} else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 10 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 9) % 12;	
        return "Maj9";
    } else {		
		rootnote = (hk1 + 10) % 12;
		bassnote = hk1;
        return "Maj9";
    }
}

   // Check 9: 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 11 || hk2d == 3) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 11 || hk3d == 3) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 11 || hk4d == 3) &&
			(hk5d == 5 || hk5d == 8 || hk5d == 11 || hk5d == 3)
			&& hk6 == 0) {
    if 	((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 4) % 12;		
        return "9";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "9";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "9";
	} else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 2) % 12;	
        return "9";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "9";
    }
}

   // Check 9: 1 is 7th
    else if ((hk2d == 3 || hk2d == 7 || hk2d == 10 || hk2d == 5) && 
			 (hk3d == 3 || hk3d == 7 || hk3d == 10 || hk3d == 5) && 
			 (hk4d == 3 || hk4d == 7 || hk4d == 10 || hk4d == 5) &&
			(hk5d == 3 || hk5d == 7 || hk5d == 10 || hk5d == 5)
			&& hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = 13;		
        return "9";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 7 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 6) % 12;	
        return "9";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 10 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 9) % 12;	
        return "9";
	} else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 4) % 12;	
        return "9";
    } else {		
		rootnote = (hk1 + 2) % 12;
		bassnote = hk1;
        return "9";
    }
}

   // Check 9: 1 is 5th
    else if ((hk2d == 6 || hk2d == 10 || hk2d == 4 || hk2d == 8) && 
			 (hk3d == 6 || hk3d == 10 || hk3d == 4 || hk3d == 8) && 
			 (hk4d == 6 || hk4d == 10 || hk4d == 4 || hk4d == 8) &&
			(hk5d == 6 || hk5d == 10 || hk5d == 4 || hk5d == 8)
			&& hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;		
        return "9";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 10 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 9) % 12;	
        return "9";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 4 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 3) % 12;	
        return "9";
	} else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 7) % 12;	
        return "9";
    } else {		
		rootnote = (hk1 + 5) % 12;
		bassnote = hk1;
        return "9";
    }
}

   // Check 9: 1 is 3rd
    else if ((hk2d == 9 || hk2d == 4 || hk2d == 7 || hk2d == 11) && 
			 (hk3d == 9 || hk3d == 4 || hk3d == 7 || hk3d == 11) && 
			 (hk4d == 9 || hk4d == 4 || hk4d == 7 || hk4d == 11) &&
			(hk5d == 9 || hk5d == 4 || hk5d == 7 || hk5d == 11)
			&& hk6 == 0) {
    if 	((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 8) % 12;
				bassnote = 13;		
        return "9";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 4 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 3) % 12;	
        return "9";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 7 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 6) % 12;	
        return "9";
	} else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 8) % 12;
				bassnote = (hk1 + 10) % 12;	
        return "9";
    } else {		
		rootnote = (hk1 + 8) % 12;
		bassnote = hk1;
        return "9";
    }
}

   // Check 9: 1 is 9th
    else if ((hk2d == 11 || hk2d == 3 || hk2d == 6 || hk2d == 9) && 
			 (hk3d == 11 || hk3d == 3 || hk3d == 6 || hk3d == 9) && 
			 (hk4d == 11 || hk4d == 3 || hk4d == 6 || hk4d == 9) &&
			(hk5d == 11 || hk5d == 3 || hk5d == 6 || hk5d == 9)
			&& hk6 == 0) {
    if 	((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = 13;		
        return "9";
    } else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 2) % 12;	
        return "9";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 5) % 12;	
        return "9";
	} else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 8) % 12;	
        return "9";
    } else {		
		rootnote = (hk1 + 10) % 12;
		bassnote = hk1;
        return "9";
    }
}

   // Check min9: 1 is root
    else if ((hk2d == 4 || hk2d == 8 || hk2d == 11 || hk2d == 3) && 
			 (hk3d == 4 || hk3d == 8 || hk3d == 11 || hk3d == 3) && 
			 (hk4d == 4 || hk4d == 8 || hk4d == 11 || hk4d == 3) &&
			(hk5d == 4 || hk5d == 8 || hk5d == 11 || hk5d == 3)
			&& hk6 == 0) {
    if 	((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 4 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;		
        return "min9";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 7) % 12;	
        return "min9";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "min9";
	} else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 2) % 12;	
        return "min9";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "min9";
    }
}

   // Check min9: 1 is 7th
    else if ((hk2d == 3 || hk2d == 6 || hk2d == 10 || hk2d == 5) && 
			 (hk3d == 3 || hk3d == 6 || hk3d == 10 || hk3d == 5) && 
			 (hk4d == 3 || hk4d == 6 || hk4d == 10 || hk4d == 5) &&
			(hk5d == 3 || hk5d == 6 || hk5d == 10 || hk5d == 5)
			&& hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = 13;		
        return "min9";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 5) % 12;	
        return "min9";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 10 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 9) % 12;	
        return "min9";
	} else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 4) % 12;	
        return "min9";
    } else {		
		rootnote = (hk1 + 2) % 12;
		bassnote = hk1;
        return "min9";
    }
}

   // Check min9: 1 is 5th
    else if ((hk2d == 6 || hk2d == 9 || hk2d == 4 || hk2d == 8) && 
			 (hk3d == 6 || hk3d == 9 || hk3d == 4 || hk3d == 8) && 
			 (hk4d == 6 || hk4d == 9 || hk4d == 4 || hk4d == 8) &&
			(hk5d == 6 || hk5d == 9 || hk5d == 4 || hk5d == 8)
			&& hk6 == 0) {
    if 	((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = 13;		
        return "min9";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 8) % 12;	
        return "min9";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 4 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 3) % 12;	
        return "min9";
	} else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 5) % 12;
				bassnote = (hk1 + 7) % 12;	
        return "min9";
    } else {		
		rootnote = (hk1 + 5) % 12;
		bassnote = hk1;
        return "min9";
    }
}

   // Check min9: 1 is 3rd
    else if ((hk2d == 10 || hk2d == 5 || hk2d == 8 || hk2d == 12) && 
			 (hk3d == 10 || hk3d == 5 || hk3d == 8 || hk3d == 12) && 
			 (hk4d == 10 || hk4d == 5 || hk4d == 8 || hk4d == 12) &&
			(hk5d == 10 || hk5d == 5 || hk5d == 8 || hk5d == 12)
			&& hk6 == 0) {
    if 	((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 10 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 9) % 12;
				bassnote = 13;		
        return "min9";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 4) % 12;	
        return "min9";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 7) % 12;	
        return "min9";
	} else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 12 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 11) % 12;	
        return "min9";
    } else {		
		rootnote = (hk1 + 9) % 12;
		bassnote = hk1;
        return "min9";
    }
}

   // Check min9: 1 is 9th
    else if ((hk2d == 11 || hk2d == 2 || hk2d == 6 || hk2d == 9) && 
			 (hk3d == 11 || hk3d == 2 || hk3d == 6 || hk3d == 9) && 
			 (hk4d == 11 || hk4d == 2 || hk4d == 6 || hk4d == 9) &&
			(hk5d == 11 || hk5d == 2 || hk5d == 6 || hk5d == 9)
			&& hk6 == 0) {
    if 	((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = 13;		
        return "min9";
    } else if ((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 2 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 1) % 12;	
        return "min9";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 5) % 12;	
        return "min9";
	} else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 8) % 12;	
        return "min9";
    } else {		
		rootnote = (hk1 + 10) % 12;
		bassnote = hk1;
        return "min9";
    }
}

   // Check m9b5: 1 is root
    else if ((hk2d == 4 || hk2d == 7 || hk2d == 11 || hk2d == 3) && 
			 (hk3d == 4 || hk3d == 7 || hk3d == 11 || hk3d == 3) && 
			 (hk4d == 4 || hk4d == 7 || hk4d == 11 || hk4d == 3) &&
			(hk5d == 4 || hk5d == 7 || hk5d == 11 || hk5d == 3)
			&& hk6 == 0) {
    if 	((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 4 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 3) % 12;		
        return "m9b5";
    } else if ((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 7 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 6) % 12;	
        return "m9b5";
    } else if ((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 10) % 12;	
        return "m9b5";
	} else if ((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = hk1;
				bassnote = (hk1 + 2) % 12;	
        return "m9b5";
    } else {		
		rootnote = hk1;
		bassnote = 13;
        return "m9b5";
    }
}

   // Check m9b5: 1 is 7th
    else if ((hk2d == 3 || hk2d == 6 || hk2d == 9 || hk2d == 5) && 
			 (hk3d == 3 || hk3d == 6 || hk3d == 9 || hk3d == 5) && 
			 (hk4d == 3 || hk4d == 6 || hk4d == 9 || hk4d == 5) &&
			(hk5d == 3 || hk5d == 6 || hk5d == 9 || hk5d == 5)
			&& hk6 == 0) {
    if 	((hk2d == 3 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 3 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 3 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 3 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = 13;		
        return "m9b5";
    } else if ((hk2d == 6 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 6 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 6 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 6 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 5) % 12;	
        return "m9b5";
    } else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 8) % 12;	
        return "m9b5";
	} else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 2) % 12;
				bassnote = (hk1 + 4) % 12;	
        return "m9b5";
    } else {		
		rootnote = (hk1 + 2) % 12;
		bassnote = hk1;
        return "m9b5";
    }
}

   // Check m9b5: 1 is 5th
    else if ((hk2d == 7 || hk2d == 10 || hk2d == 5 || hk2d == 9) && 
			 (hk3d == 7 || hk3d == 10 || hk3d == 5 || hk3d == 9) && 
			 (hk4d == 7 || hk4d == 10 || hk4d == 5 || hk4d == 9) &&
			(hk5d == 7 || hk5d == 10 || hk5d == 5 || hk5d == 9)
			&& hk6 == 0) {
    if 	((hk2d == 7 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 7 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 7 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 7 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 6) % 12;
				bassnote = 13;		
        return "m9b5";
    } else if ((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 10 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 6) % 12;
				bassnote = (hk1 + 9) % 12;	
        return "m9b5";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 6) % 12;
				bassnote = (hk1 + 4) % 12;	
        return "m9b5";
	} else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 6) % 12;
				bassnote = (hk1 + 8) % 12;	
        return "m9b5";
    } else {		
		rootnote = (hk1 + 6) % 12;
		bassnote = hk1;
        return "m9b5";
    }
}

   // Check m9b5: 1 is 3rd
    else if ((hk2d == 10 || hk2d == 4 || hk2d == 8 || hk2d == 12) && 
			 (hk3d == 10 || hk3d == 4 || hk3d == 8 || hk3d == 12) && 
			 (hk4d == 10 || hk4d == 4 || hk4d == 8 || hk4d == 12) &&
			(hk5d == 10 || hk5d == 4 || hk5d == 8 || hk5d == 12)
			&& hk6 == 0) {
    if 	((hk2d == 10 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 10 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 10 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 10 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 9) % 12;
				bassnote = 13;		
        return "m9b5";
    } else if ((hk2d == 4 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 4 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 4 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 4 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 3) % 12;	
        return "m9b5";
    } else if ((hk2d == 8 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 8 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 8 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 8 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 7) % 12;	
        return "m9b5";
	} else if ((hk2d == 12 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 12 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 12 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 12 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 9) % 12;
				bassnote = (hk1 + 11) % 12;	
        return "m9b5";
    } else {		
		rootnote = (hk1 + 9) % 12;
		bassnote = hk1;
        return "m9b5";
    }
}

   // Check m9b5: 1 is 9th
    else if ((hk2d == 11 || hk2d == 2 || hk2d == 5 || hk2d == 9) && 
			 (hk3d == 11 || hk3d == 2 || hk3d == 5 || hk3d == 9) && 
			 (hk4d == 11 || hk4d == 2 || hk4d == 5 || hk4d == 9) &&
			(hk5d == 11 || hk5d == 2 || hk5d == 5 || hk5d == 9)
			&& hk6 == 0) {
    if 	((hk2d == 11 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 11 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 11 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 11 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = 13;		
        return "m9b5";
    } else if ((hk2d == 2 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 2 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 2 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 2 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 1) % 12;	
        return "m9b5";
    } else if ((hk2d == 5 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 5 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 5 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 5 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 4) % 12;	
        return "m9b5";
	} else if ((hk2d == 9 && hk2 < hk1 && hk2 < hk3 && hk2 < hk4 && hk2 < hk5) ||
        (hk3d == 9 && hk3 < hk1 && hk3 < hk2 && hk3 < hk4 && hk3 < hk5) ||
		(hk4d == 9 && hk4 < hk1 && hk4 < hk2 && hk4 < hk3 && hk4 < hk5) ||
		(hk5d == 9 && hk5 < hk1 && hk5 < hk2 && hk5 < hk3 && hk5 < hk4))	{	
				rootnote = (hk1 + 10) % 12;
				bassnote = (hk1 + 8) % 12;	
        return "m9b5";
    } else {		
		rootnote = (hk1 + 10) % 12;
		bassnote = hk1;
        return "m9b5";
    }
}

   // Check dim7(9): 1 is root
    else if ((hk2d == 4 || hk2d == 7 || hk2d == 10 || hk2d == 3) && 
			 (hk3d == 4 || hk3d == 7 || hk3d == 10 || hk3d == 3) && 
			 (hk4d == 4 || hk4d == 7 || hk4d == 10 || hk4d == 3) &&
			(hk5d == 4 || hk5d == 7 || hk5d == 10 || hk5d == 3)
			&& hk6 == 0) {	
		rootnote = hk1;
		bassnote = 13;
        return "dim7(9)";
    }
	
	
	
	   // Check 9#5: 1 is root
    else if ((hk2d == 5 || hk2d == 9 || hk2d == 11 || hk2d == 3) && 
			 (hk3d == 5 || hk3d == 9 || hk3d == 11 || hk3d == 3) && 
			 (hk4d == 5 || hk4d == 9 || hk4d == 11 || hk4d == 3) &&
			(hk5d == 5 || hk5d == 9 || hk5d == 11 || hk5d == 3)
			&& hk6 == 0) {	
		rootnote = hk1;
		bassnote = 13;
        return "9#5";
    }
	
		   // Check #9#5: 1 is root
    else if ((hk2d == 5 || hk2d == 9 || hk2d == 11 || hk2d == 4) && 
			 (hk3d == 5 || hk3d == 9 || hk3d == 11 || hk3d == 4) && 
			 (hk4d == 5 || hk4d == 9 || hk4d == 11 || hk4d == 4) &&
			(hk5d == 5 || hk5d == 9 || hk5d == 11 || hk5d == 4)
			&& hk6 == 0) {	
		rootnote = hk1;
		bassnote = 13;
        return "#9#5";
    }
	
   // Check (6/9): 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 10 || hk2d == 3) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 10 || hk3d == 3) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 10 || hk4d == 3) &&
			(hk5d == 5 || hk5d == 8 || hk5d == 10 || hk5d == 3)
			&& hk6 == 0) {	
		rootnote = hk1;
		bassnote = 13;
		if (hk2d == 3 && hk3d == 5 && hk4d == 8 && hk5d == 10 && scstatus != 0) {
		return "Pentatonic";}
		else {return "(6/9)";}
 
    }
   // Check m(6/9): 1 is root
    else if ((hk2d == 4 || hk2d == 8 || hk2d == 10 || hk2d == 3) && 
			 (hk3d == 4 || hk3d == 8 || hk3d == 10 || hk3d == 3) && 
			 (hk4d == 4 || hk4d == 8 || hk4d == 10 || hk4d == 3) &&
			(hk5d == 4 || hk5d == 8 || hk5d == 10 || hk5d == 3)
			&& hk6 == 0) {	
		rootnote = hk1;
		bassnote = 13;
		if (hk2d == 3 && hk3d == 4 && hk4d == 8 && hk5d == 10 && scstatus != 0) {
		return "m Pentatonic";}
		else return "m(6/9)";}
    
	
   // Check 11: 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 11 || hk2d == 3 || hk2d == 6) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 11 || hk3d == 3 || hk3d == 6) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 11 || hk4d == 3 || hk4d == 6) &&
			 (hk5d == 5 || hk5d == 8 || hk5d == 11 || hk5d == 3 || hk5d == 6) && 
			 (hk6d == 5 || hk6d == 8 || hk6d == 11 || hk6d == 3 || hk6d == 6) &&
			 hk7d == 0) { 	
		rootnote = hk1;
		bassnote = 13;
        return "11";
    }
	
	   // Check min11: 1 is root
    else if ((hk2d == 4 || hk2d == 8 || hk2d == 11 || hk2d == 3 || hk2d == 6) && 
			 (hk3d == 4 || hk3d == 8 || hk3d == 11 || hk3d == 3 || hk3d == 6) && 
			 (hk4d == 4 || hk4d == 8 || hk4d == 11 || hk4d == 3 || hk4d == 6) &&
			 (hk5d == 4 || hk5d == 8 || hk5d == 11 || hk5d == 3 || hk5d == 6) && 
			 (hk6d == 4 || hk6d == 8 || hk6d == 11 || hk6d == 3 || hk6d == 6) &&
			 hk7d == 0){
		rootnote = hk1;
		bassnote = 13;
        return "min11";
    }
	
	   // Check Maj11: 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 12 || hk2d == 3 || hk2d == 6) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 12 || hk3d == 3 || hk3d == 6) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 12 || hk4d == 3 || hk4d == 6) &&
			 (hk5d == 5 || hk5d == 8 || hk5d == 12 || hk5d == 3 || hk5d == 6) && 
			 (hk6d == 5 || hk6d == 8 || hk6d == 12 || hk6d == 3 || hk6d == 6) &&
			 hk7d == 0){
		rootnote = hk1;
		bassnote = 13;
        return "Maj11";
    }
	
		   // Check Half diminished 11: 1 is root
    else if ((hk2d == 4 || hk2d == 7 || hk2d == 11 || hk2d == 3 || hk2d == 6) && 
			 (hk3d == 4 || hk3d == 7 || hk3d == 11 || hk3d == 3 || hk3d == 6) && 
			 (hk4d == 4 || hk4d == 7 || hk4d == 11 || hk4d == 3 || hk4d == 6) &&
			 (hk5d == 4 || hk5d == 7 || hk5d == 11 || hk5d == 3 || hk5d == 6) && 
			 (hk6d == 4 || hk6d == 7 || hk6d == 11 || hk6d == 3 || hk6d == 6) &&
			 hk7d == 0){
		rootnote = hk1;
		bassnote = 13;
        return "min7b5(9/11)";
    }
	
			   // Check diminished 11: 1 is root
    else if ((hk2d == 4 || hk2d == 7 || hk2d == 10 || hk2d == 3 || hk2d == 6) && 
			 (hk3d == 4 || hk3d == 7 || hk3d == 10 || hk3d == 3 || hk3d == 6) && 
			 (hk4d == 4 || hk4d == 7 || hk4d == 10 || hk4d == 3 || hk4d == 6) &&
			 (hk5d == 4 || hk5d == 7 || hk5d == 10 || hk5d == 3 || hk5d == 6) && 
			 (hk6d == 4 || hk6d == 7 || hk6d == 10 || hk6d == 3 || hk6d == 6) &&
			 hk7d == 0){
		rootnote = hk1;
		bassnote = 13;
        return "dim7(9/11)";
    }
	
			// Check min7#11: 1 is root
    else if ((hk2d == 4 || hk2d == 8 || hk2d == 11 || hk2d == 7) && 
			 (hk3d == 4 || hk3d == 8 || hk3d == 11 || hk3d == 7) && 
			 (hk4d == 4 || hk4d == 8 || hk4d == 11 || hk4d == 7) &&
			(hk5d == 4 || hk5d == 8 || hk5d == 11 || hk5d == 7)
			&& hk6 == 0) {
		rootnote = hk1;
		bassnote = 13;
        return "min7(#11)";
			}
			   // Check 7#11: 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 11 || hk2d == 7) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 11 || hk3d == 7) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 11 || hk4d == 7) &&
			(hk5d == 5 || hk5d == 8 || hk5d == 11 || hk5d == 7)
			&& hk6 == 0) {
		rootnote = hk1;
		bassnote = 13;
        return "7(#11)";
			}
				// Check maj7#11: 1 is root
    else if ((hk2d == 5 || hk2d == 8 || hk2d == 12 || hk2d == 7) && 
			 (hk3d == 5 || hk3d == 8 || hk3d == 12 || hk3d == 7) && 
			 (hk4d == 5 || hk4d == 8 || hk4d == 12 || hk4d == 7) &&
			(hk5d == 5 || hk5d == 8 || hk5d == 12 || hk5d == 7)
			&& hk6 == 0) {
		rootnote = hk1;
		bassnote = 13;
        return "maj7(#11)";
			}
			
				// Ionian
	 else if ((hk2d == 3 || hk2d == 5 || hk2d == 6 || hk2d == 8 || hk2d == 10 || hk2d == 12) && 
			 (hk3d == 3 || hk3d == 5 || hk3d == 6 || hk3d == 8 || hk3d == 10 || hk3d == 12) && 
			 (hk4d == 3 || hk4d == 5 || hk4d == 6 || hk4d == 8 || hk4d == 10 || hk4d == 12) &&
			 (hk5d == 3 || hk5d == 5 || hk5d == 6 || hk5d == 8 || hk5d == 10 || hk5d == 12) && 
			 (hk6d == 3 || hk6d == 5 || hk6d == 6 || hk6d == 8 || hk6d == 10 || hk6d == 12) &&
			 (hk7d == 3 || hk7d == 5 || hk7d == 6 || hk7d == 8 || hk7d == 10 || hk7d == 12)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Major Scale (Ionian)";
    }
	
					// Dorian
	 else if ((hk2d == 3 || hk2d == 4 || hk2d == 6 || hk2d == 8 || hk2d == 10 || hk2d == 11) && 
			 (hk3d == 3 || hk3d == 4 || hk3d == 6 || hk3d == 8 || hk3d == 10 || hk3d == 11) && 
			 (hk4d == 3 || hk4d == 4 || hk4d == 6 || hk4d == 8 || hk4d == 10 || hk4d == 11) &&
			 (hk5d == 3 || hk5d == 4 || hk5d == 6 || hk5d == 8 || hk5d == 10 || hk5d == 11) && 
			 (hk6d == 3 || hk6d == 4 || hk6d == 6 || hk6d == 8 || hk6d == 10 || hk6d == 11) &&
			 (hk7d == 3 || hk7d == 4 || hk7d == 6 || hk7d == 8 || hk7d == 10 || hk7d == 11)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Dorian";
    }
	
						// Phrygian
	 else if ((hk2d == 2 || hk2d == 4 || hk2d == 6 || hk2d == 8 || hk2d == 9 || hk2d == 11) && 
			 (hk3d == 2 || hk3d == 4 || hk3d == 6 || hk3d == 8 || hk3d == 9 || hk3d == 11) && 
			 (hk4d == 2 || hk4d == 4 || hk4d == 6 || hk4d == 8 || hk4d == 9 || hk4d == 11) &&
			 (hk5d == 2 || hk5d == 4 || hk5d == 6 || hk5d == 8 || hk5d == 9 || hk5d == 11) && 
			 (hk6d == 2 || hk6d == 4 || hk6d == 6 || hk6d == 8 || hk6d == 9 || hk6d == 11) &&
			 (hk7d == 2 || hk7d == 4 || hk7d == 6 || hk7d == 8 || hk7d == 9 || hk7d == 11)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Phrygian";
    }
	
						// Lydian
	 else if ((hk2d == 3 || hk2d == 5 || hk2d == 7 || hk2d == 8 || hk2d == 10 || hk2d == 12) && 
			 (hk3d == 3 || hk3d == 5 || hk3d == 7 || hk3d == 8 || hk3d == 10 || hk3d == 12) && 
			 (hk4d == 3 || hk4d == 5 || hk4d == 7 || hk4d == 8 || hk4d == 10 || hk4d == 12) &&
			 (hk5d == 3 || hk5d == 5 || hk5d == 7 || hk5d == 8 || hk5d == 10 || hk5d == 12) && 
			 (hk6d == 3 || hk6d == 5 || hk6d == 7 || hk6d == 8 || hk6d == 10 || hk6d == 12) &&
			 (hk7d == 3 || hk7d == 5 || hk7d == 7 || hk7d == 8 || hk7d == 10 || hk7d == 12)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Lydian";
    }
	
						// Mixolydian
	 else if ((hk2d == 3 || hk2d == 5 || hk2d == 6 || hk2d == 8 || hk2d == 10 || hk2d == 11) && 
			 (hk3d == 3 || hk3d == 5 || hk3d == 6 || hk3d == 8 || hk3d == 10 || hk3d == 11) && 
			 (hk4d == 3 || hk4d == 5 || hk4d == 6 || hk4d == 8 || hk4d == 10 || hk4d == 11) &&
			 (hk5d == 3 || hk5d == 5 || hk5d == 6 || hk5d == 8 || hk5d == 10 || hk5d == 11) && 
			 (hk6d == 3 || hk6d == 5 || hk6d == 6 || hk6d == 8 || hk6d == 10 || hk6d == 11) &&
			 (hk7d == 3 || hk7d == 5 || hk7d == 6 || hk7d == 8 || hk7d == 10 || hk7d == 11)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Mixolydian";
    }
	
						// Aeolian
	 else if ((hk2d == 3 || hk2d == 4 || hk2d == 6 || hk2d == 8 || hk2d == 9 || hk2d == 11) && 
			 (hk3d == 3 || hk3d == 4 || hk3d == 6 || hk3d == 8 || hk3d == 9 || hk3d == 11) && 
			 (hk4d == 3 || hk4d == 4 || hk4d == 6 || hk4d == 8 || hk4d == 9 || hk4d == 11) &&
			 (hk5d == 3 || hk5d == 4 || hk5d == 6 || hk5d == 8 || hk5d == 9 || hk5d == 11) && 
			 (hk6d == 3 || hk6d == 4 || hk6d == 6 || hk6d == 8 || hk6d == 9 || hk6d == 11) &&
			 (hk7d == 3 || hk7d == 4 || hk7d == 6 || hk7d == 8 || hk7d == 9 || hk7d == 11)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Minor Scale (Aeolian)";
    }
	
						// Locrian
	 else if ((hk2d == 2 || hk2d == 4 || hk2d == 6 || hk2d == 7 || hk2d == 9 || hk2d == 11) && 
			 (hk3d == 2 || hk3d == 4 || hk3d == 6 || hk3d == 7 || hk3d == 9 || hk3d == 11) && 
			 (hk4d == 2 || hk4d == 4 || hk4d == 6 || hk4d == 7 || hk4d == 9 || hk4d == 11) &&
			 (hk5d == 2 || hk5d == 4 || hk5d == 6 || hk5d == 7 || hk5d == 9 || hk5d == 11) && 
			 (hk6d == 2 || hk6d == 4 || hk6d == 6 || hk6d == 7 || hk6d == 9 || hk6d == 11) &&
			 (hk7d == 2 || hk7d == 4 || hk7d == 6 || hk7d == 7 || hk7d == 9 || hk7d == 11)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Locrian";
    }
	
						// Harmonic Minor
	 else if ((hk2d == 3 || hk2d == 4 || hk2d == 6 || hk2d == 8 || hk2d == 9 || hk2d == 12) && 
			 (hk3d == 3 || hk3d == 4 || hk3d == 6 || hk3d == 8 || hk3d == 9 || hk3d == 12) && 
			 (hk4d == 3 || hk4d == 4 || hk4d == 6 || hk4d == 8 || hk4d == 9 || hk4d == 12) &&
			 (hk5d == 3 || hk5d == 4 || hk5d == 6 || hk5d == 8 || hk5d == 9 || hk5d == 12) && 
			 (hk6d == 3 || hk6d == 4 || hk6d == 6 || hk6d == 8 || hk6d == 9 || hk6d == 12) &&
			 (hk7d == 3 || hk7d == 4 || hk7d == 6 || hk7d == 8 || hk7d == 9 || hk7d == 12)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Harmonic Minor";
    }
	
						// Melodic Minor
	 else if ((hk2d == 3 || hk2d == 4 || hk2d == 6 || hk2d == 8 || hk2d == 10 || hk2d == 12) && 
			 (hk3d == 3 || hk3d == 4 || hk3d == 6 || hk3d == 8 || hk3d == 10 || hk3d == 12) && 
			 (hk4d == 3 || hk4d == 4 || hk4d == 6 || hk4d == 8 || hk4d == 10 || hk4d == 12) &&
			 (hk5d == 3 || hk5d == 4 || hk5d == 6 || hk5d == 8 || hk5d == 10 || hk5d == 12) && 
			 (hk6d == 3 || hk6d == 4 || hk6d == 6 || hk6d == 8 || hk6d == 10 || hk6d == 12) &&
			 (hk7d == 3 || hk7d == 4 || hk7d == 6 || hk7d == 8 || hk7d == 10 || hk7d == 12)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Melodic Minor";
    }
	
						// Whole Step
	 else if ((hk2d == 3 || hk2d == 5 || hk2d == 7 || hk2d == 9 || hk2d == 11) && 
			 (hk3d == 3 || hk3d == 5 || hk3d == 7 || hk3d == 9 || hk3d == 11) && 
			 (hk4d == 3 || hk4d == 5 || hk4d == 7 || hk4d == 9 || hk4d == 11) &&
			 (hk5d == 3 || hk5d == 5 || hk5d == 7 || hk5d == 9 || hk5d == 11) && 
			 (hk6d == 3 || hk6d == 5 || hk6d == 7 || hk6d == 9 || hk6d == 11)) { 	
		rootnote = hk1;
		bassnote = 13;
        return "Whole Step Scale";
    }
		
    // If no specific chord is matched, return a generic chord name
    else {
        return "     ";
    }
}


const char code_to_name[60][25] = {
    "  ", "  ", "  ", "  ", "A", "B", "C", "D", "E", "F",
    "G", "H", "I", "J", "K", "L", "M", "N", "O", "P",
    "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "Enter", "Delete", "Back space", "Tab", "Space", "-", "=", "[", "]", "\\",
    "#", ";", "'", "`", ",", ".", "/", "  ", "  ", "  "};
	
const char* noteNames[] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
	
const char midi_note_names[144][5] = {
	"C-2", "C#-2", "D-2", "D#-2", "E-2", "F-2", "F#-2", "G-2", "G#-2", "A-2", "A#-2", "B-2",
	"C-1", "C#-1", "D-1", "D#-1", "E-1", "F-1", "F#-1", "G-1", "G#-1", "A-1", "A#-1", "B-1",
    "C0", "C#0", "D0", "D#0", "E0", "F0", "F#0", "G0", "G#0", "A0", "A#0", "B0",
    "C1", "C#1", "D1", "D#1", "E1", "F1", "F#1", "G1", "G#1", "A1", "A#1", "B1",
    "C2", "C#2", "D2", "D#2", "E2", "F2", "F#2", "G2", "G#2", "A2", "A#2", "B2",
    "C3", "C#3", "D3", "D#3", "E3", "F3", "F#3", "G3", "G#3", "A3", "A#3", "B3",
    "C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4",
    "C5", "C#5", "D5", "D#5", "E5", "F5", "F#5", "G5", "G#5", "A5", "A#5", "B5",
	"C6", "C#6", "D6", "D#6", "E6", "F6", "F#6", "G6", "G#6", "A6", "A#6", "B6",
	"C7", "C#7", "D7", "D#7", "E7", "F7", "F#7", "G7", "G#7", "A7", "A#7", "B7",
	"C8", "C#8", "D8", "D#8", "E8", "F8", "F#8", "G8", "G#8", "A8", "A#8", "B8",
	"C9", "C#9", "D8", "D#9", "E9", "F9", "F#9", "G9", "G#9", "A9", "A#9", "B9"
};

const char chord_note_names[12][5] = {
	"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"

};

const char majorminor_note_names[96][11] = {
	"G MAJE MIN", "G#MAJFMIN", "A MAJF#MIN", "A#MAJG MIN", "B MAJG#MIN", "C MAJA MIN", "C#MAJA#MIN", "D MAJB MIN", "D#MAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJD#MIN",
	"G MAJE MIN", "G#MAJFMIN", "A MAJF#MIN", "A#MAJG MIN", "B MAJG#MIN", "C MAJA MIN", "C#MAJA#MIN", "D MAJB MIN", "D#MAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJD#MIN",
	"G MAJE MIN", "G#MAJFMIN", "A MAJF#MIN", "A#MAJG MIN", "B MAJG#MIN", "C MAJA MIN", "C#MAJA#MIN", "D MAJB MIN", "D#MAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJD#MIN",
	"G MAJE MIN", "G#MAJFMIN", "A MAJF#MIN", "A#MAJG MIN", "B MAJG#MIN", "C MAJA MIN", "C#MAJA#MIN", "D MAJB MIN", "D#MAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJD#MIN",
	"G MAJE MIN", "G#MAJFMIN", "A MAJF#MIN", "A#MAJG MIN", "B MAJG#MIN", "C MAJA MIN", "C#MAJA#MIN", "D MAJB MIN", "D#MAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJD#MIN",
	"G MAJE MIN", "G#MAJFMIN", "A MAJF#MIN", "A#MAJG MIN", "B MAJG#MIN", "C MAJA MIN", "C#MAJA#MIN", "D MAJB MIN", "D#MAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJD#MIN",
	"G MAJE MIN", "G#MAJFMIN", "A MAJF#MIN", "A#MAJG MIN", "B MAJG#MIN", "C MAJA MIN", "C#MAJA#MIN", "D MAJB MIN", "D#MAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJD#MIN",
	"G MAJE MIN", "G#MAJFMIN", "A MAJF#MIN", "A#MAJG MIN", "B MAJG#MIN", "C MAJA MIN", "C#MAJA#MIN", "D MAJB MIN", "D#MAJC MIN", "E MAJC#MIN", "F MAJD MIN", "F#MAJD#MIN",
};

#ifdef RGB_MATRIX_ENABLE
bool rgb_matrix_indicators_kb(void) {
    if (!rgb_matrix_indicators_user()) {
        return false;
    }

//    if (host_keyboard_led_state().caps_lock) { // Capslock = RED
//        rgb_matrix_set_color(44, 200, 0, 0);
//    }
    return true;
}
#endif

/* KEYBOARD PET START */

/* settings */
//#    define MIN_WALK_SPEED      1000
//#    define MIN_RUN_SPEED       4000

/* advanced settings */
#    define ANIM_FRAME_DURATION 120  // how long each frame lasts in ms
#    define ANIM_SIZE           48   // number of bytes in array. If you change sprites, minimize for adequate firmware size. max is 1024

/* timers */
uint32_t anim_timer = 0;

/* current frame */
uint8_t current_frame = 0;

/* status variables */
//int   current_wpm = 0;
led_t led_usb_state;

/* logic */
static void render_luna(int LUNA_X, int LUNA_Y) {
	
	

int oledhk1 = (hk1 == 0) ? 99 : ((hk1 + oledkeyboard) % 24 + 1);
int oledhk2 = (hk2 == 0) ? 99 : ((hk2 + oledkeyboard) % 24 + 1);
int oledhk3 = (hk3 == 0) ? 99 : ((hk3 + oledkeyboard) % 24 + 1);
int oledhk4 = (hk4 == 0) ? 99 : ((hk4 + oledkeyboard) % 24 + 1);
int oledhk5 = (hk5 == 0) ? 99 : ((hk5 + oledkeyboard) % 24 + 1);
int oledhk6 = (hk6 == 0) ? 99 : ((hk6 + oledkeyboard) % 24 + 1);
int oledhk7 = (hk7 == 0) ? 99 : ((hk7 + oledkeyboard) % 24 + 1);


int C1_active = 0;
if (oledhk1 == 1 || oledhk2 == 1 || oledhk3 == 1 || oledhk4 == 1 || oledhk5 == 1 || oledhk6 == 1 || oledhk7 == 1) {
    C1_active = 1;
} else {
    C1_active = 0;
}

int C1s_active = 0;
if (oledhk1 == 2 || oledhk2 == 2 || oledhk3 == 2 || oledhk4 == 2 || oledhk5 == 2 || oledhk6 == 2 || oledhk7 == 2) {
    C1s_active = 1;
} else {
    C1s_active = 0;
}

int D1_active = 0;
if (oledhk1 == 3 || oledhk2 == 3 || oledhk3 == 3 || oledhk4 == 3 || oledhk5 == 3 || oledhk6 == 3 || oledhk7 == 3) {
    D1_active = 1;
} else {
    D1_active = 0;
}

int D1s_active = 0;
if (oledhk1 == 4 || oledhk2 == 4 || oledhk3 == 4 || oledhk4 == 4 || oledhk5 == 4 || oledhk6 == 4 || oledhk7 == 4) {
    D1s_active = 1;
} else {
    D1s_active = 0;
}

int E1_active = 0;
if (oledhk1 == 5 || oledhk2 == 5 || oledhk3 == 5 || oledhk4 == 5 || oledhk5 == 5 || oledhk6 == 5 || oledhk7 == 5) {
    E1_active = 1;
} else {
    E1_active = 0;
}

int F1_active = 0;
if (oledhk1 == 6 || oledhk2 == 6 || oledhk3 == 6 || oledhk4 == 6 || oledhk5 == 6 || oledhk6 == 6 || oledhk7 == 6) {
    F1_active = 1;
} else {
    F1_active = 0;
}

int F1s_active = 0;
if (oledhk1 == 7 || oledhk2 == 7 || oledhk3 == 7 || oledhk4 == 7 || oledhk5 == 7 || oledhk6 == 7 || oledhk7 == 7) {
    F1s_active = 1;
} else {
    F1s_active = 0;
}

int G1_active = 0;
if (oledhk1 == 8 || oledhk2 == 8 || oledhk3 == 8 || oledhk4 == 8 || oledhk5 == 8 || oledhk6 == 8 || oledhk7 == 8) {
    G1_active = 1;
} else {
    G1_active = 0;
}

int G1s_active = 0;
if (oledhk1 == 9 || oledhk2 == 9 || oledhk3 == 9 || oledhk4 == 9 || oledhk5 == 9 || oledhk6 == 9 || oledhk7 == 9) {
    G1s_active = 1;
} else {
    G1s_active = 0;
}

int A1_active = 0;
if (oledhk1 == 10 || oledhk2 == 10 || oledhk3 == 10 || oledhk4 == 10 || oledhk5 == 10 || oledhk6 == 10 || oledhk7 == 10) {
    A1_active = 1;
} else {
    A1_active = 0;
}

int A1s_active = 0;
if (oledhk1 == 11 || oledhk2 == 11 || oledhk3 == 11 || oledhk4 == 11 || oledhk5 == 11 || oledhk6 == 11 || oledhk7 == 11) {
    A1s_active = 1;
} else {
    A1s_active = 0;
}

int B1_active = 0;
if (oledhk1 == 12 || oledhk2 == 12 || oledhk3 == 12 || oledhk4 == 12 || oledhk5 == 12 || oledhk6 == 12 || oledhk7 == 12) {
    B1_active = 1;
} else {
    B1_active = 0;
}

int C2_active = 0;
if (oledhk1 == 13 || oledhk2 == 13 || oledhk3 == 13 || oledhk4 == 13 || oledhk5 == 13 || oledhk6 == 13 || oledhk7 == 13) {
    C2_active = 1;
} else {
    C2_active = 0;
}

int C2s_active = 0;
if (oledhk1 == 14 || oledhk2 == 14 || oledhk3 == 14 || oledhk4 == 14 || oledhk5 == 14 || oledhk6 == 14 || oledhk7 == 14) {
    C2s_active = 1;
} else {
    C2s_active = 0;
}

int D2_active = 0;
if (oledhk1 == 15 || oledhk2 == 15 || oledhk3 == 15 || oledhk4 == 15 || oledhk5 == 15 || oledhk6 == 15 || oledhk7 == 15) {
    D2_active = 1;
} else {
    D2_active = 0;
}

int D2s_active = 0;
if (oledhk1 == 16 || oledhk2 == 16 || oledhk3 == 16 || oledhk4 == 16 || oledhk5 == 16 || oledhk6 == 16 || oledhk7 == 16) {
    D2s_active = 1;
} else {
    D2s_active = 0;
}

int E2_active = 0;
if (oledhk1 == 17 || oledhk2 == 17 || oledhk3 == 17 || oledhk4 == 17 || oledhk5 == 17 || oledhk6 == 17 || oledhk7 == 17) {
    E2_active = 1;
} else {
    E2_active = 0;
}

int F2_active = 0;
if (oledhk1 == 18 || oledhk2 == 18 || oledhk3 == 18 || oledhk4 == 18 || oledhk5 == 18 || oledhk6 == 18 || oledhk7 == 18) {
    F2_active = 1;
} else {
    F2_active = 0;
}

int F2s_active = 0;
if (oledhk1 == 19 || oledhk2 == 19 || oledhk3 == 19 || oledhk4 == 19 || oledhk5 == 19 || oledhk6 == 19 || oledhk7 == 19) {
    F2s_active = 1;
} else {
    F2s_active = 0;
}

int G2_active = 0;
if (oledhk1 == 20 || oledhk2 == 20 || oledhk3 == 20 || oledhk4 == 20 || oledhk5 == 20 || oledhk6 == 20 || oledhk7 == 20) {
    G2_active = 1;
} else {
    G2_active = 0;
}

int G2s_active = 0;
if (oledhk1 == 21 || oledhk2 == 21 || oledhk3 == 21 || oledhk4 == 21 || oledhk5 == 21 || oledhk6 == 21 || oledhk7 == 21) {
    G2s_active = 1;
} else {
    G2s_active = 0;
}

int A2_active = 0;
if (oledhk1 == 22 || oledhk2 == 22 || oledhk3 == 22 || oledhk4 == 22 || oledhk5 == 22 || oledhk6 == 22 || oledhk7 == 22) {
    A2_active = 1;
} else {
    A2_active = 0;
}

int A2s_active = 0;
if (oledhk1 == 23 || oledhk2 == 23 || oledhk3 == 23 || oledhk4 == 23 || oledhk5 == 23 || oledhk6 == 23 || oledhk7 == 23) {
    A2s_active = 1;
} else {
    A2s_active = 0;
}

int B2_active = 0;
if (oledhk1 == 24 || oledhk2 == 24 || oledhk3 == 24 || oledhk4 == 24 || oledhk5 == 24 || oledhk6 == 24 || oledhk7 == 24) {
    B2_active = 1;
} else {
    B2_active = 0;
}

    static const char PROGMEM r1c1[2][ANIM_SIZE] = {
                                                   {
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
0x00, 0xff, 0x00, 0xfe, 0xfe, 0xfe
   }, 
};

    static const char PROGMEM r1c2[4][ANIM_SIZE] = {
                                                   {
// 'Toprow2Empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow2Full1', 6x8px
0xfe, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow2Full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'Toprow2Fullboth', 6x8px
0xfe, 0x00, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r1c3[2][ANIM_SIZE] = {
                                                   {
// '2row3Empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// '2row3full', 6x8px
0xff, 0x00, 0xfe, 0xfe, 0x00, 0xff
   }, 
};

    static const char PROGMEM r1c4[4][ANIM_SIZE] = {
                                                   {
// '2row4empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow4full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow4full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xfe
   }, 
{
// 'Toprow4fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xfe, 
   }, 
};

    static const char PROGMEM r1c5[2][ANIM_SIZE] = {
                                                   {
// 'Toprow5empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'Toprow5full', 6x8px
0xfe, 0xfe, 0xfe, 0x00, 0xff, 0x00,
   }, 
};

    static const char PROGMEM r1c6[2][ANIM_SIZE] = {
                                                   {
// 'Toprow6empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'Toprow6full', 6x8px
0xfe, 0xfe, 0xfe, 0xfe, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r1c7[4][ANIM_SIZE] = {
                                                   {
// 'Toprow7empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow7full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow7full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xfe,
   }, 
{
// 'Toprow7fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xfe, 
   }, 
};

    static const char PROGMEM r1c8[4][ANIM_SIZE] = {
                                                   {
// 'Toprow8empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow8realfull1', 6x8px
0xfe, 0x00, 0xff, 0x00, 0x00, 0x00
   }, 
{
// 'Toprow8realfull2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'Toprow8realfullboth', 6x8px
0xfe, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
};

    static const char PROGMEM r1c9[2][ANIM_SIZE] = {
                                                   {
// 'Toprow9empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'Toprow9full', 6x8px
0xff, 0x00, 0xfe, 0xfe, 0x00, 0xff
   }, 
};

    static const char PROGMEM r1c10[4][ANIM_SIZE] = {
                                                   {
// 'Toprow10empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow10full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00
   }, 
{
// 'Toprow10full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xfe, 
   }, 
{
// 'Toprow10fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xfe, 
   }, 
};

    static const char PROGMEM r1c11[2][ANIM_SIZE] = {
                                                   {
// 'Toprow11empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'Toprow11full', 6x8px
0xfe, 0xfe, 0xfe, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r1c12[2][ANIM_SIZE] = {
                                                   {
// 'Toprow12empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'Toprow12full', 6x8px
0xfe, 0xfe, 0xfe, 0xfe, 0x00, 0xff
   }, 
};

    static const char PROGMEM r1c13[4][ANIM_SIZE] = {
                                                   {
// 'Toprow13empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow13full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00
   }, 
{
// 'Toprow13full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xfe, 
   }, 
{
// 'Toprow13fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xfe, 
   }, 
};

    static const char PROGMEM r1c14[4][ANIM_SIZE] = {
                                                   {
// 'Toprow14empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow14full1', 6x8px
0xfe, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow14full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff
   }, 
{
// 'Toprow14fullboth', 6x8px
0xfe, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
};

    static const char PROGMEM r1c15[2][ANIM_SIZE] = {
                                                   {
// 'Toprow15empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow15full', 6x8px
0xff, 0x00, 0xfe, 0xfe, 0xfe, 0xfe
   }, 
};

    static const char PROGMEM r1c16[2][ANIM_SIZE] = {
                                                   {
// 'Toprow16empty', 6x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow16full', 6x8px
0x00, 0xff, 0x00, 0xfe, 0xfe, 0xfe
   }, 
};

    static const char PROGMEM r1c17[4][ANIM_SIZE] = {
                                                   {
// 'Toprow17empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow17full1', 6x8px
0xfe, 0x00, 0xff, 0x00, 0x00, 0x00
   }, 
{
// 'Toprow17full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'Toprow17fullboth', 6x8px
0xfe, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
};

    static const char PROGMEM r1c18[2][ANIM_SIZE] = {
                                                   {
// 'Toprow18empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'Toprow18full', 6x8px
0xff, 0x00, 0xfe, 0xfe, 0x00, 0xff
   }, 
};

    static const char PROGMEM r1c19[4][ANIM_SIZE] = {
                                                   {
// 'Toprow19empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow19full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow19full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xfe
   }, 
{
// 'Toprow19fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xfe, 
   }, 
};

    static const char PROGMEM r1c20[4][ANIM_SIZE] = {
                                                   {
// 'Toprow20empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow20realfull1', 6x8px
0xfe, 0x00, 0xff, 0x00, 0x00, 0x00
   }, 
{
// 'Toprow20realfull2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'Toprow20realfullboth', 6x8px
0xfe, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
};

    static const char PROGMEM r1c21[2][ANIM_SIZE] = {
                                                   {
// 'Toprow21empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow21full', 6x8px
0xff, 0x00, 0xfe, 0xfe, 0xfe, 0x00
   }, 
};

    static const char PROGMEM r2c1[2][ANIM_SIZE] = {
                                                   {
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'ToprowC1Full', 6x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r2c2[4][ANIM_SIZE] = {
                                                   {
// 'Toprow2Empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// '2row2Full1', 6x8px
0xff, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// '2row2Full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// '2row2Fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff,
   }, 
};

    static const char PROGMEM r2c3[2][ANIM_SIZE] = {
                                                   {
// '2row3Empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// '2row3full', 6x8px
0xff, 0x00, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c4[4][ANIM_SIZE] = {
                                                   {
// '2row4empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// '2row4full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// '2row4full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xff, 
   }, 
{
// '2row4fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c5[2][ANIM_SIZE] = {
                                                   {
// 'Toprow5empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'Toprow5full', 6x8px
0xff, 0xff, 0xff, 0x00, 0xff, 0x00,
   }, 
};

    static const char PROGMEM r2c6[2][ANIM_SIZE] = {
                                                   {
// 'Toprow6empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'Toprow6full', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c7[4][ANIM_SIZE] = {
                                                   {
// 'Toprow7empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow7full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow7full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xff, 
   }, 
{
// 'Toprow7fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c8[4][ANIM_SIZE] = {
                                                   {
// 'Toprow8empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow8full1', 6x8px
0xff, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow8full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'Toprow8fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff ,
   }, 
};

    static const char PROGMEM r2c9[2][ANIM_SIZE] = {
                                                   {
// 'Toprow9empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'Toprow9full', 6x8px
0xff, 0x00, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c10[4][ANIM_SIZE] = {
                                                   {
// 'Toprow10empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow10full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow10full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xff, 
   }, 
{
// 'Toprow10fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c11[2][ANIM_SIZE] = {
                                                   {
// 'Toprow11empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'Toprow11full', 6x8px
0xff, 0xff, 0xff, 0x00, 0xff, 0x00,
   }, 
};

    static const char PROGMEM r2c12[2][ANIM_SIZE] = {
                                                   {
// 'Toprow12empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'Toprow12full', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c13[4][ANIM_SIZE] = {
                                                   {
// 'Toprow13empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow13full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow13full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xff,
   }, 
{
// 'Toprow13fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 
   }, 
};

    static const char PROGMEM r2c14[4][ANIM_SIZE] = {
                                                   {
// 'Toprow14empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow14full1', 6x8px
0xff, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow14full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'Toprow14fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff,
   }, 
};

    static const char PROGMEM r2c15[2][ANIM_SIZE] = {
                                                   {
// 'Toprow15empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow15full', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff,
   }, 
};

    static const char PROGMEM r2c16[2][ANIM_SIZE] = {
                                                   {
// 'Toprow16empty', 6x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow16full', 6x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff,
   }, 
};

    static const char PROGMEM r2c17[4][ANIM_SIZE] = {
                                                   {
// 'Toprow17empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow17Full1', 6x8px
0xff, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow17full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'Toprow17fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff,
   }, 
};

    static const char PROGMEM r2c18[2][ANIM_SIZE] = {
                                                   {
// 'Toprow18empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'Toprow18full', 6x8px
0xff, 0x00, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c19[4][ANIM_SIZE] = {
                                                   {
// 'Toprow19empty', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow19full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'Toprow19full2', 6x8px
0x00, 0x00, 0x00, 0xff, 0x00, 0xff, 
   }, 
{
// 'Toprow19fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff,
   }, 
};

    static const char PROGMEM r2c20[4][ANIM_SIZE] = {
                                                   {
// 'Toprow20empty', 6x8px
0x00, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow20full1', 6x8px
0xff, 0x00, 0xff, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow20full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff,
   }, 
{
// 'Toprow20fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
};

    static const char PROGMEM r2c21[2][ANIM_SIZE] = {
                                                   {
// 'Toprow21empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'Toprow21full', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0x00,
   }, 
};

    static const char PROGMEM r4c1[2][ANIM_SIZE] = {
                                                   {
// 'c1empty', 6x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00,  
   }, 
{
// 'c1full', 6x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r4c2[4][ANIM_SIZE] = {
                                                   {
// 'c2empty', 6x8px
0x00, 0x00, 0xff, 0x80, 0x80, 0x80, 
   }, 
{
// 'c2full1', 6x8px
0xff, 0x00, 0xff, 0x80, 0x80, 0x80, 
   }, 
{
// 'c2full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff,
   }, 
{
// 'c2fullall', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r4c3[2][ANIM_SIZE] = {
                                                   {
// 'c3empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'c3full', 6x8px
0xff, 0x00, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c4[4][ANIM_SIZE] = {
                                                   {
// 'c4empty', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0x00, 
   }, 
{
// 'c4full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00,  
   }, 
{
// 'c4full2', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0xff, 
   }, 
{
// 'c4fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c5[2][ANIM_SIZE] = {
                                                   {
// 'c5empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'c5full', 6x8px
0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r4c6[2][ANIM_SIZE] = {
                                                   {
// 'C6empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'C6full', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c7[4][ANIM_SIZE] = {
                                                   {
// 'C7empty', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0x00, 
   }, 
{
// 'c7full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'c7full2', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0xff,
   }, 
{
// 'c7fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c8[4][ANIM_SIZE] = {
                                                   {
// 'c8empty', 6x8px
0x00, 0x00, 0xff, 0x80, 0x80, 0x80, 
   }, 
{
// 'c8full1', 6x8px
0xff, 0x00, 0xff, 0x80, 0x80, 0x80,  
   }, 
{
// 'c8full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'c8fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r4c9[2][ANIM_SIZE] = {
                                                   {
// 'c9empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'c9full', 6x8px
0xff, 0x00, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c10[4][ANIM_SIZE] = {
                                                   {
// 'c10empty', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0x00, 
   }, 
{
// 'c10full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'c10full2', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0xff,
   }, 
{
// 'c10fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c11[2][ANIM_SIZE] = {
                                                   {
// 'c11empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0xff, 0x00,  
   }, 
{
// 'c11full', 6x8px
0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r4c12[2][ANIM_SIZE] = {
                                                   {
// 'c12empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'c12full', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c13[4][ANIM_SIZE] = {
                                                   {
// 'c13empty', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0x00, 
   }, 
{
// 'c13full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'c13full2', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0xff, 
   }, 
{
// 'c13fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c14[4][ANIM_SIZE] = {
                                                   {
// 'c14empty', 6x8px
0x00, 0x00, 0xff, 0x80, 0x80, 0x80, 
   }, 
{
// 'c14full1', 6x8px
0xff, 0x00, 0xff, 0x80, 0x80, 0x80,  
   }, 
{
// 'c14full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'c14fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r4c15[2][ANIM_SIZE] = {
                                                   {
// 'c15empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'c15full', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r4c16[2][ANIM_SIZE] = {
                                                   {
// 'c16empty', 6x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'c16full', 6x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r4c17[4][ANIM_SIZE] = {
                                                   {
// 'c17empty', 6x8px
0x00, 0x00, 0xff, 0x80, 0x80, 0x80,  
   }, 
{
// 'c17full1', 6x8px
0xff, 0x00, 0xff, 0x80, 0x80, 0x80, 
   }, 
{
// 'c17full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'c17fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r4c18[2][ANIM_SIZE] = {
                                                   {
// 'c18empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 
   }, 
{
// 'c18full', 6x8px
0xff, 0x00, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c19[4][ANIM_SIZE] = {
                                                   {
// 'c19empty', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0x00, 
   }, 
{
// 'c19full1', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 
   }, 
{
// 'c19full2', 6x8px
0x80, 0x80, 0x80, 0xff, 0x00, 0xff, 
   }, 
{
// 'c19fullboth', 6x8px
0xff, 0xff, 0xff, 0xff, 0x00, 0xff
   }, 
};

    static const char PROGMEM r4c20[4][ANIM_SIZE] = {
                                                   {
// 'c20empty', 6x8px
0x00, 0x00, 0xff, 0x80, 0x80, 0x80, 
   }, 
{
// 'c20full1', 6x8px
0xff, 0x00, 0xff, 0x80, 0x80, 0x80,  
   }, 
{
// 'c20full2', 6x8px
0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 
   }, 
{
// 'c20fullboth', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0xff
   }, 
};


    static const char PROGMEM r5c1[2][ANIM_SIZE] = {
                                                   {
// 'C1_2empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'image_2024-09-25_043136924', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r5c2[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'image_2024-09-25_043230864', 6x8px
0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe
   }, 
};

    static const char PROGMEM r5c3[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'image_2024-09-25_043335485', 12x8px
0x00, 0xff, 0x00, 0xfe, 0xfe, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r5c4[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'image_2024-09-25_043420697', 6x8px
0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe
   }, 
};

    static const char PROGMEM r5c5[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'image_2024-09-25_043501525', 12x8px
0x00, 0xff, 0x00, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r5c6[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'image_2024-09-25_043604220', 6x8px
0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe
   }, 
};

    static const char PROGMEM r5c7[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'image_2024-09-25_043631883', 12x8px
0x00, 0xff, 0x00, 0xfe, 0xfe, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r5c8[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'image_2024-09-25_043657944', 6x8px
0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe
   }, 
};

    static const char PROGMEM r5c9[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'image_2024-09-25_043754590', 12x8px
0x00, 0xff, 0x00, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r5c10[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'image_2024-09-25_043818031', 6x8px
0xfe, 0xfe, 0xff, 0xff, 0xff, 0xff
   }, 
};
    static const char PROGMEM r5c11[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'image_2024-09-25_043831004', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xfe, 0xfe, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r5c12[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'image_2024-09-25_043901507', 6x8px
0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe
   }, 
};

    static const char PROGMEM r5c13[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'image_2024-09-25_043938804', 12x8px
0x00, 0xff, 0x00, 0xfe, 0xfe, 0xff, 0xff, 0xfe, 0xfe, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r5c14[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'image_2024-09-25_044032590', 6x8px
0xfe, 0xfe, 0xff, 0xff, 0xff, 0x00
   }, 
};

    static const char PROGMEM r6c1[2][ANIM_SIZE] = {
                                                   {
// 'C1_2empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'C1_2full', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r6c2[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'full', 6x8px
0xff, 0xff, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r6c3[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'C4_5full', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r6c4[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'full', 6x8px
0xff, 0xff, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r6c5[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'C4_5full', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r6c6[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'full', 6x8px
0xff, 0xff, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r6c7[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'C4_5full', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r6c8[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'full', 6x8px
0xff, 0xff, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r6c9[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'C4_5full', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r6c10[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'full', 6x8px
0xff, 0xff, 0xff, 0xff, 0xff, 0xff
   }, 
};
    static const char PROGMEM r6c11[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'C4_5full', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r6c12[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'full', 6x8px
0xff, 0xff, 0xff, 0xff, 0xff, 0xff
   }, 
};

    static const char PROGMEM r6c13[2][ANIM_SIZE] = {
                                                   {
// 'C4_5empty', 12x8px
0x00, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 
   }, 
{
// 'C4_5full', 12x8px
0x00, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0xff, 0x00
   }, 
};

    static const char PROGMEM r6c14[2][ANIM_SIZE] = {
                                                   {
// 'Empty', 6x8px
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'image_2024-09-25_183423648', 6x8px
0xff, 0xff, 0xff, 0xff, 0xff, 0x00
   }, 
};

    static const char PROGMEM r4c21[2][ANIM_SIZE] = {
                                                   {
// 'c21empty', 6x8px
0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 
   }, 
{
// 'c21full', 6x8px
0xff, 0x00, 0xff, 0xff, 0xff, 0x00
   }, 
};

    static const char PROGMEM endbar[1][128] = {
                                                   {
 //End
0xff, 0x00
   }, 
};
    static const char PROGMEM Keyboardtop[1][128] = {
                                                   {
// 'TOPROW', 128x8px
0x00, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 
0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x00
   }, 
};

    static const char PROGMEM Keyboardbottom[1][128] = {
                                                   {
// 'image_2024-09-25_183648124', 128x8px
0x00, 0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 
0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x03, 0x00
   }, 
};

    /* animation */
void animate_luna(void) {
	
	oled_set_cursor(0, 8);  // Adjust the x position as needed
    oled_write_raw_P(Keyboardtop[0], 128);
	
	
	// ROW 1
    oled_set_cursor(0, 9);  // Adjust the x position as needed
	if (C1_active == 1) {oled_write_raw_P(r1c1[1], ANIM_SIZE);} else {oled_write_raw_P(r1c1[0], ANIM_SIZE);}
	oled_set_cursor(1, 9);  // Adjust the x position as needed
	if (C1_active == 1 && C1s_active == 0) {oled_write_raw_P(r1c2[1], ANIM_SIZE); } else if (C1_active == 0 && C1s_active == 1) {oled_write_raw_P(r1c2[2], ANIM_SIZE); } else if (C1_active == 1 && C1s_active == 1) {oled_write_raw_P(r1c2[3], ANIM_SIZE); } else {oled_write_raw_P(r1c2[0], ANIM_SIZE); }
	oled_set_cursor(2, 9);  // Adjust the x position as needed
    if (D1_active == 1) {oled_write_raw_P(r1c3[1], ANIM_SIZE); } else {oled_write_raw_P(r1c3[0], ANIM_SIZE); }
	oled_set_cursor(3, 9);  // Adjust the x position as needed
    if (D1s_active == 1 && E1_active == 0) {oled_write_raw_P(r1c4[1], ANIM_SIZE); } else if (D1s_active == 0 && E1_active == 1) {oled_write_raw_P(r1c4[2], ANIM_SIZE); } else if (D1s_active == 1 && E1_active == 1) {oled_write_raw_P(r1c4[3], ANIM_SIZE); } else {oled_write_raw_P(r1c4[0], ANIM_SIZE); }
	oled_set_cursor(4, 9);  // Adjust the x position as needed
    if (E1_active == 1) {oled_write_raw_P(r1c5[1], ANIM_SIZE);} else {oled_write_raw_P(r1c5[0], ANIM_SIZE);}
	oled_set_cursor(5, 9);  // Adjust the x position as needed
    if (F1_active == 1) {oled_write_raw_P(r1c6[1], ANIM_SIZE); } else {oled_write_raw_P(r1c6[0], ANIM_SIZE); }
	oled_set_cursor(6, 9);  // Adjust the x position as needed
    if (F1s_active == 1 && G1_active == 0) {oled_write_raw_P(r1c7[1], ANIM_SIZE); } else if (F1s_active == 0 && G1_active == 1) {oled_write_raw_P(r1c7[2], ANIM_SIZE); } else if (F1s_active == 1 && G1_active == 1) {oled_write_raw_P(r1c7[3], ANIM_SIZE); } else {oled_write_raw_P(r1c7[0], ANIM_SIZE); }
	oled_set_cursor(7, 9);  // Adjust the x position as needed
	if (G1_active == 1 && G1s_active == 0) {oled_write_raw_P(r1c8[1], ANIM_SIZE); } else if (G1_active == 0 && G1s_active == 1) {oled_write_raw_P(r1c8[2], ANIM_SIZE); } else if (G1_active == 1 && G1s_active == 1) {oled_write_raw_P(r1c8[3], ANIM_SIZE); } else {oled_write_raw_P(r1c8[0], ANIM_SIZE); }
	oled_set_cursor(8, 9);  // Adjust the x position as needed
	if (A1_active == 1) {oled_write_raw_P(r1c9[1], ANIM_SIZE); } else {oled_write_raw_P(r1c9[0], ANIM_SIZE); }
	oled_set_cursor(9, 9);  // Adjust the x position as needed
	if (A1s_active == 1 && B1_active == 0) {oled_write_raw_P(r1c10[1], ANIM_SIZE); } else if (A1s_active == 0 && B1_active == 1) {oled_write_raw_P(r1c10[2], ANIM_SIZE); } else if (A1s_active == 1 && B1_active == 1) {oled_write_raw_P(r1c10[3], ANIM_SIZE); } else {oled_write_raw_P(r1c10[0], ANIM_SIZE); }
	oled_set_cursor(10, 9);  // Adjust the x position as needed
	if (B1_active == 1) {oled_write_raw_P(r1c11[1], ANIM_SIZE);} else {oled_write_raw_P(r1c11[0], ANIM_SIZE);}
	oled_set_cursor(11, 9);  // Adjust the x position as needed
	if (C2_active == 1) {oled_write_raw_P(r1c12[1], ANIM_SIZE); } else {oled_write_raw_P(r1c12[0], ANIM_SIZE); }
	oled_set_cursor(12, 9);  // Adjust the x position as needed
    if (C2s_active == 1 && D2_active == 0) {oled_write_raw_P(r1c13[1], ANIM_SIZE); } else if (C2s_active == 0 && D2_active == 1) {oled_write_raw_P(r1c13[2], ANIM_SIZE); } else if (C2s_active == 1 && D2_active == 1) {oled_write_raw_P(r1c13[3], ANIM_SIZE); } else {oled_write_raw_P(r1c13[0], ANIM_SIZE); }
	oled_set_cursor(13, 9);  // Adjust the x position as needed
    if (D2_active == 1 && D2s_active == 0) {oled_write_raw_P(r1c14[1], ANIM_SIZE); } else if (D2_active == 0 && D2s_active == 1) {oled_write_raw_P(r1c14[2], ANIM_SIZE); } else if (D2_active == 1 && D2s_active == 1) {oled_write_raw_P(r1c14[3], ANIM_SIZE); } else {oled_write_raw_P(r1c14[0], ANIM_SIZE); }
	oled_set_cursor(14, 9);  // Adjust the x position as needed
    if (E2_active == 1) {oled_write_raw_P(r1c15[1], ANIM_SIZE);} else {oled_write_raw_P(r1c15[0], ANIM_SIZE);}
	oled_set_cursor(15, 9);  // Adjust the x position as needed
    if (F2_active == 1) {oled_write_raw_P(r1c16[1], ANIM_SIZE); } else {oled_write_raw_P(r1c16[0], ANIM_SIZE); }
	oled_set_cursor(16, 9);  // Adjust the x position as needed
    if (F2_active == 1 && F2s_active == 0) {oled_write_raw_P(r1c17[1], ANIM_SIZE); } else if (F2_active == 0 && F2s_active == 1) {oled_write_raw_P(r1c17[2], ANIM_SIZE); } else if (F2_active == 1 && F2s_active == 1) {oled_write_raw_P(r1c17[3], ANIM_SIZE); } else {oled_write_raw_P(r1c17[0], ANIM_SIZE); }
	oled_set_cursor(17, 9);  // Adjust the x position as needed
	if (G2_active == 1) {oled_write_raw_P(r1c18[1], ANIM_SIZE); } else {oled_write_raw_P(r1c18[0], ANIM_SIZE); }
	oled_set_cursor(18, 9);  // Adjust the x position as needed
	if (G2s_active == 1 && A2_active == 0) {oled_write_raw_P(r1c19[1], ANIM_SIZE); } else if (G2s_active == 0 && A2_active == 1) {oled_write_raw_P(r1c19[2], ANIM_SIZE); } else if (G2s_active == 1 && A2_active == 1) {oled_write_raw_P(r1c19[3], ANIM_SIZE); } else {oled_write_raw_P(r1c19[0], ANIM_SIZE); }
	oled_set_cursor(19, 9);  // Adjust the x position as needed
	if (A2_active == 1 && A2s_active == 0) {oled_write_raw_P(r1c20[1], ANIM_SIZE); } else if (A2_active == 0 && A2s_active == 1) {oled_write_raw_P(r1c20[2], ANIM_SIZE); } else if (A2_active == 1 && A2s_active == 1) {oled_write_raw_P(r1c20[3], ANIM_SIZE); } else {oled_write_raw_P(r1c20[0], ANIM_SIZE); }
	oled_set_cursor(20, 9);  // Adjust the x position as needed
	if (B2_active == 1) {oled_write_raw_P(r1c21[1], ANIM_SIZE); } else {oled_write_raw_P(r1c21[0], ANIM_SIZE); }
	oled_set_cursor(21, 9);  // Adjust the x position as needed
	oled_write_raw_P(endbar[0], ANIM_SIZE);
	
		// ROW 2
    oled_set_cursor(0, 10);  // Adjust the x position as needed
	if (C1_active == 1) {oled_write_raw_P(r2c1[1], ANIM_SIZE);} else {oled_write_raw_P(r2c1[0], ANIM_SIZE);}
	oled_set_cursor(1, 10);  // Adjust the x position as needed
	if (C1_active == 1 && C1s_active == 0) {oled_write_raw_P(r2c2[1], ANIM_SIZE); } else if (C1_active == 0 && C1s_active == 1) {oled_write_raw_P(r2c2[2], ANIM_SIZE); } else if (C1_active == 1 && C1s_active == 1) {oled_write_raw_P(r2c2[3], ANIM_SIZE); } else {oled_write_raw_P(r2c2[0], ANIM_SIZE); }
	oled_set_cursor(2, 10);  // Adjust the x position as needed
    if (D1_active == 1) {oled_write_raw_P(r2c3[1], ANIM_SIZE); } else {oled_write_raw_P(r2c3[0], ANIM_SIZE); }
	oled_set_cursor(3, 10);  // Adjust the x position as needed
    if (D1s_active == 1 && E1_active == 0) {oled_write_raw_P(r2c4[1], ANIM_SIZE); } else if (D1s_active == 0 && E1_active == 1) {oled_write_raw_P(r2c4[2], ANIM_SIZE); } else if (D1s_active == 1 && E1_active == 1) {oled_write_raw_P(r2c4[3], ANIM_SIZE); } else {oled_write_raw_P(r2c4[0], ANIM_SIZE); }
	oled_set_cursor(4, 10);  // Adjust the x position as needed
    if (E1_active == 1) {oled_write_raw_P(r2c5[1], ANIM_SIZE);} else {oled_write_raw_P(r2c5[0], ANIM_SIZE);}
	oled_set_cursor(5, 10);  // Adjust the x position as needed
    if (F1_active == 1) {oled_write_raw_P(r2c6[1], ANIM_SIZE); } else {oled_write_raw_P(r2c6[0], ANIM_SIZE); }
	oled_set_cursor(6, 10);  // Adjust the x position as needed
    if (F1s_active == 1 && G1_active == 0) {oled_write_raw_P(r2c7[1], ANIM_SIZE); } else if (F1s_active == 0 && G1_active == 1) {oled_write_raw_P(r2c7[2], ANIM_SIZE); } else if (F1s_active == 1 && G1_active == 1) {oled_write_raw_P(r2c7[3], ANIM_SIZE); } else {oled_write_raw_P(r2c7[0], ANIM_SIZE); }
	oled_set_cursor(7, 10);  // Adjust the x position as needed
	if (G1_active == 1 && G1s_active == 0) {oled_write_raw_P(r2c8[1], ANIM_SIZE); } else if (G1_active == 0 && G1s_active == 1) {oled_write_raw_P(r2c8[2], ANIM_SIZE); } else if (G1_active == 1 && G1s_active == 1) {oled_write_raw_P(r2c8[3], ANIM_SIZE); } else {oled_write_raw_P(r2c8[0], ANIM_SIZE); }
	oled_set_cursor(8, 10);  // Adjust the x position as needed
	if (A1_active == 1) {oled_write_raw_P(r2c9[1], ANIM_SIZE); } else {oled_write_raw_P(r2c9[0], ANIM_SIZE); }
	oled_set_cursor(9, 10);  // Adjust the x position as needed
	if (A1s_active == 1 && B1_active == 0) {oled_write_raw_P(r2c10[1], ANIM_SIZE); } else if (A1s_active == 0 && B1_active == 1) {oled_write_raw_P(r2c10[2], ANIM_SIZE); } else if (A1s_active == 1 && B1_active == 1) {oled_write_raw_P(r2c10[3], ANIM_SIZE); } else {oled_write_raw_P(r2c10[0], ANIM_SIZE); }
	oled_set_cursor(10, 10);  // Adjust the x position as needed
	if (B1_active == 1) {oled_write_raw_P(r2c11[1], ANIM_SIZE);} else {oled_write_raw_P(r2c11[0], ANIM_SIZE);}
	oled_set_cursor(11, 10);  // Adjust the x position as needed
	if (C2_active == 1) {oled_write_raw_P(r2c12[1], ANIM_SIZE); } else {oled_write_raw_P(r2c12[0], ANIM_SIZE); }
	oled_set_cursor(12, 10);  // Adjust the x position as needed
    if (C2s_active == 1 && D2_active == 0) {oled_write_raw_P(r2c13[1], ANIM_SIZE); } else if (C2s_active == 0 && D2_active == 1) {oled_write_raw_P(r2c13[2], ANIM_SIZE); } else if (C2s_active == 1 && D2_active == 1) {oled_write_raw_P(r2c13[3], ANIM_SIZE); } else {oled_write_raw_P(r2c13[0], ANIM_SIZE); }
	oled_set_cursor(13, 10);  // Adjust the x position as needed
    if (D2_active == 1 && D2s_active == 0) {oled_write_raw_P(r2c14[1], ANIM_SIZE); } else if (D2_active == 0 && D2s_active == 1) {oled_write_raw_P(r2c14[2], ANIM_SIZE); } else if (D2_active == 1 && D2s_active == 1) {oled_write_raw_P(r2c14[3], ANIM_SIZE); } else {oled_write_raw_P(r2c14[0], ANIM_SIZE); }
	oled_set_cursor(14, 10);  // Adjust the x position as needed
    if (E2_active == 1) {oled_write_raw_P(r2c15[1], ANIM_SIZE);} else {oled_write_raw_P(r2c15[0], ANIM_SIZE);}
	oled_set_cursor(15, 10);  // Adjust the x position as needed
    if (F2_active == 1) {oled_write_raw_P(r2c16[1], ANIM_SIZE); } else {oled_write_raw_P(r2c16[0], ANIM_SIZE); }
	oled_set_cursor(16, 10);  // Adjust the x position as needed
    if (F2_active == 1 && F2s_active == 0) {oled_write_raw_P(r2c17[1], ANIM_SIZE); } else if (F2_active == 0 && F2s_active == 1) {oled_write_raw_P(r2c17[2], ANIM_SIZE); } else if (F2_active == 1 && F2s_active == 1) {oled_write_raw_P(r2c17[3], ANIM_SIZE); } else {oled_write_raw_P(r2c17[0], ANIM_SIZE); }
	oled_set_cursor(17, 10);  // Adjust the x position as needed
	if (G2_active == 1) {oled_write_raw_P(r2c18[1], ANIM_SIZE); } else {oled_write_raw_P(r2c18[0], ANIM_SIZE); }
	oled_set_cursor(18, 10);  // Adjust the x position as needed
	if (G2s_active == 1 && A2_active == 0) {oled_write_raw_P(r2c19[1], ANIM_SIZE); } else if (G2s_active == 0 && A2_active == 1) {oled_write_raw_P(r2c19[2], ANIM_SIZE); } else if (G2s_active == 1 && A2_active == 1) {oled_write_raw_P(r2c19[3], ANIM_SIZE); } else {oled_write_raw_P(r2c19[0], ANIM_SIZE); }
	oled_set_cursor(19, 10);  // Adjust the x position as needed
	if (A2_active == 1 && A2s_active == 0) {oled_write_raw_P(r2c20[1], ANIM_SIZE); } else if (A2_active == 0 && A2s_active == 1) {oled_write_raw_P(r2c20[2], ANIM_SIZE); } else if (A2_active == 1 && A2s_active == 1) {oled_write_raw_P(r2c20[3], ANIM_SIZE); } else {oled_write_raw_P(r2c20[0], ANIM_SIZE); }
	oled_set_cursor(20, 10);  // Adjust the x position as needed
	if (B2_active == 1) {oled_write_raw_P(r2c21[1], ANIM_SIZE); } else {oled_write_raw_P(r2c21[0], ANIM_SIZE); }
	oled_set_cursor(21, 10);  // Adjust the x position as needed
	oled_write_raw_P(endbar[0], ANIM_SIZE);
	
		// ROW 3
    oled_set_cursor(0, 11);  // Adjust the x position as needed
	if (C1_active == 1) {oled_write_raw_P(r2c1[1], ANIM_SIZE);} else {oled_write_raw_P(r2c1[0], ANIM_SIZE);}
	oled_set_cursor(1, 11);  // Adjust the x position as needed
	if (C1_active == 1 && C1s_active == 0) {oled_write_raw_P(r2c2[1], ANIM_SIZE); } else if (C1_active == 0 && C1s_active == 1) {oled_write_raw_P(r2c2[2], ANIM_SIZE); } else if (C1_active == 1 && C1s_active == 1) {oled_write_raw_P(r2c2[3], ANIM_SIZE); } else {oled_write_raw_P(r2c2[0], ANIM_SIZE); }
	oled_set_cursor(2, 11);  // Adjust the x position as needed
    if (D1_active == 1) {oled_write_raw_P(r2c3[1], ANIM_SIZE); } else {oled_write_raw_P(r2c3[0], ANIM_SIZE); }
	oled_set_cursor(3, 11);  // Adjust the x position as needed
    if (D1s_active == 1 && E1_active == 0) {oled_write_raw_P(r2c4[1], ANIM_SIZE); } else if (D1s_active == 0 && E1_active == 1) {oled_write_raw_P(r2c4[2], ANIM_SIZE); } else if (D1s_active == 1 && E1_active == 1) {oled_write_raw_P(r2c4[3], ANIM_SIZE); } else {oled_write_raw_P(r2c4[0], ANIM_SIZE); }
	oled_set_cursor(4, 11);  // Adjust the x position as needed
    if (E1_active == 1) {oled_write_raw_P(r2c5[1], ANIM_SIZE);} else {oled_write_raw_P(r2c5[0], ANIM_SIZE);}
	oled_set_cursor(5, 11);  // Adjust the x position as needed
    if (F1_active == 1) {oled_write_raw_P(r2c6[1], ANIM_SIZE); } else {oled_write_raw_P(r2c6[0], ANIM_SIZE); }
	oled_set_cursor(6, 11);  // Adjust the x position as needed
    if (F1s_active == 1 && G1_active == 0) {oled_write_raw_P(r2c7[1], ANIM_SIZE); } else if (F1s_active == 0 && G1_active == 1) {oled_write_raw_P(r2c7[2], ANIM_SIZE); } else if (F1s_active == 1 && G1_active == 1) {oled_write_raw_P(r2c7[3], ANIM_SIZE); } else {oled_write_raw_P(r2c7[0], ANIM_SIZE); }
	oled_set_cursor(7, 11);  // Adjust the x position as needed
	if (G1_active == 1 && G1s_active == 0) {oled_write_raw_P(r2c8[1], ANIM_SIZE); } else if (G1_active == 0 && G1s_active == 1) {oled_write_raw_P(r2c8[2], ANIM_SIZE); } else if (G1_active == 1 && G1s_active == 1) {oled_write_raw_P(r2c8[3], ANIM_SIZE); } else {oled_write_raw_P(r2c8[0], ANIM_SIZE); }
	oled_set_cursor(8, 11);  // Adjust the x position as needed
	if (A1_active == 1) {oled_write_raw_P(r2c9[1], ANIM_SIZE); } else {oled_write_raw_P(r2c9[0], ANIM_SIZE); }
	oled_set_cursor(9, 11);  // Adjust the x position as needed
	if (A1s_active == 1 && B1_active == 0) {oled_write_raw_P(r2c10[1], ANIM_SIZE); } else if (A1s_active == 0 && B1_active == 1) {oled_write_raw_P(r2c10[2], ANIM_SIZE); } else if (A1s_active == 1 && B1_active == 1) {oled_write_raw_P(r2c10[3], ANIM_SIZE); } else {oled_write_raw_P(r2c10[0], ANIM_SIZE); }
	oled_set_cursor(10, 11);  // Adjust the x position as needed
	if (B1_active == 1) {oled_write_raw_P(r2c11[1], ANIM_SIZE);} else {oled_write_raw_P(r2c11[0], ANIM_SIZE);}
	oled_set_cursor(11, 11);  // Adjust the x position as needed
	if (C2_active == 1) {oled_write_raw_P(r2c12[1], ANIM_SIZE); } else {oled_write_raw_P(r2c12[0], ANIM_SIZE); }
	oled_set_cursor(12, 11);  // Adjust the x position as needed
    if (C2s_active == 1 && D2_active == 0) {oled_write_raw_P(r2c13[1], ANIM_SIZE); } else if (C2s_active == 0 && D2_active == 1) {oled_write_raw_P(r2c13[2], ANIM_SIZE); } else if (C2s_active == 1 && D2_active == 1) {oled_write_raw_P(r2c13[3], ANIM_SIZE); } else {oled_write_raw_P(r2c13[0], ANIM_SIZE); }
	oled_set_cursor(13, 11);  // Adjust the x position as needed
    if (D2_active == 1 && D2s_active == 0) {oled_write_raw_P(r2c14[1], ANIM_SIZE); } else if (D2_active == 0 && D2s_active == 1) {oled_write_raw_P(r2c14[2], ANIM_SIZE); } else if (D2_active == 1 && D2s_active == 1) {oled_write_raw_P(r2c14[3], ANIM_SIZE); } else {oled_write_raw_P(r2c14[0], ANIM_SIZE); }
	oled_set_cursor(14, 11);  // Adjust the x position as needed
    if (E2_active == 1) {oled_write_raw_P(r2c15[1], ANIM_SIZE);} else {oled_write_raw_P(r2c15[0], ANIM_SIZE);}
	oled_set_cursor(15, 11);  // Adjust the x position as needed
    if (F2_active == 1) {oled_write_raw_P(r2c16[1], ANIM_SIZE); } else {oled_write_raw_P(r2c16[0], ANIM_SIZE); }
	oled_set_cursor(16, 11);  // Adjust the x position as needed
    if (F2_active == 1 && F2s_active == 0) {oled_write_raw_P(r2c17[1], ANIM_SIZE); } else if (F2_active == 0 && F2s_active == 1) {oled_write_raw_P(r2c17[2], ANIM_SIZE); } else if (F2_active == 1 && F2s_active == 1) {oled_write_raw_P(r2c17[3], ANIM_SIZE); } else {oled_write_raw_P(r2c17[0], ANIM_SIZE); }
	oled_set_cursor(17, 11);  // Adjust the x position as needed
	if (G2_active == 1) {oled_write_raw_P(r2c18[1], ANIM_SIZE); } else {oled_write_raw_P(r2c18[0], ANIM_SIZE); }
	oled_set_cursor(18, 11);  // Adjust the x position as needed
	if (G2s_active == 1 && A2_active == 0) {oled_write_raw_P(r2c19[1], ANIM_SIZE); } else if (G2s_active == 0 && A2_active == 1) {oled_write_raw_P(r2c19[2], ANIM_SIZE); } else if (G2s_active == 1 && A2_active == 1) {oled_write_raw_P(r2c19[3], ANIM_SIZE); } else {oled_write_raw_P(r2c19[0], ANIM_SIZE); }
	oled_set_cursor(19, 11);  // Adjust the x position as needed
	if (A2_active == 1 && A2s_active == 0) {oled_write_raw_P(r2c20[1], ANIM_SIZE); } else if (A2_active == 0 && A2s_active == 1) {oled_write_raw_P(r2c20[2], ANIM_SIZE); } else if (A2_active == 1 && A2s_active == 1) {oled_write_raw_P(r2c20[3], ANIM_SIZE); } else {oled_write_raw_P(r2c20[0], ANIM_SIZE); }
	oled_set_cursor(20, 11);  // Adjust the x position as needed
	if (B2_active == 1) {oled_write_raw_P(r2c21[1], ANIM_SIZE); } else {oled_write_raw_P(r2c21[0], ANIM_SIZE); }
	oled_set_cursor(21, 11);  // Adjust the x position as needed
	oled_write_raw_P(endbar[0], ANIM_SIZE);
	
			// ROW 4
    oled_set_cursor(0, 12);  // Adjust the x position as needed
	if (C1_active == 1) {oled_write_raw_P(r4c1[1], ANIM_SIZE);} else {oled_write_raw_P(r4c1[0], ANIM_SIZE);}
	oled_set_cursor(1, 12);  // Adjust the x position as needed
	if (C1_active == 1 && C1s_active == 0) {oled_write_raw_P(r4c2[1], ANIM_SIZE); } else if (C1_active == 0 && C1s_active == 1) {oled_write_raw_P(r4c2[2], ANIM_SIZE); } else if (C1_active == 1 && C1s_active == 1) {oled_write_raw_P(r4c2[3], ANIM_SIZE); } else {oled_write_raw_P(r4c2[0], ANIM_SIZE); }
	oled_set_cursor(2, 12);  // Adjust the x position as needed
    if (D1_active == 1) {oled_write_raw_P(r4c3[1], ANIM_SIZE); } else {oled_write_raw_P(r4c3[0], ANIM_SIZE); }
	oled_set_cursor(3, 12);  // Adjust the x position as needed
    if (D1s_active == 1 && E1_active == 0) {oled_write_raw_P(r4c4[1], ANIM_SIZE); } else if (D1s_active == 0 && E1_active == 1) {oled_write_raw_P(r4c4[2], ANIM_SIZE); } else if (D1s_active == 1 && E1_active == 1) {oled_write_raw_P(r4c4[3], ANIM_SIZE); } else {oled_write_raw_P(r4c4[0], ANIM_SIZE); }
	oled_set_cursor(4, 12);  // Adjust the x position as needed
    if (E1_active == 1) {oled_write_raw_P(r4c5[1], ANIM_SIZE);} else {oled_write_raw_P(r4c5[0], ANIM_SIZE);}
	oled_set_cursor(5, 12);  // Adjust the x position as needed
    if (F1_active == 1) {oled_write_raw_P(r4c6[1], ANIM_SIZE); } else {oled_write_raw_P(r4c6[0], ANIM_SIZE); }
	oled_set_cursor(6, 12);  // Adjust the x position as needed
    if (F1s_active == 1 && G1_active == 0) {oled_write_raw_P(r4c7[1], ANIM_SIZE); } else if (F1s_active == 0 && G1_active == 1) {oled_write_raw_P(r4c7[2], ANIM_SIZE); } else if (F1s_active == 1 && G1_active == 1) {oled_write_raw_P(r4c7[3], ANIM_SIZE); } else {oled_write_raw_P(r4c7[0], ANIM_SIZE); }
	oled_set_cursor(7, 12);  // Adjust the x position as needed
	if (G1_active == 1 && G1s_active == 0) {oled_write_raw_P(r4c8[1], ANIM_SIZE); } else if (G1_active == 0 && G1s_active == 1) {oled_write_raw_P(r4c8[2], ANIM_SIZE); } else if (G1_active == 1 && G1s_active == 1) {oled_write_raw_P(r4c8[3], ANIM_SIZE); } else {oled_write_raw_P(r4c8[0], ANIM_SIZE); }
	oled_set_cursor(8, 12);  // Adjust the x position as needed
	if (A1_active == 1) {oled_write_raw_P(r4c9[1], ANIM_SIZE); } else {oled_write_raw_P(r4c9[0], ANIM_SIZE); }
	oled_set_cursor(9, 12);  // Adjust the x position as needed
	if (A1s_active == 1 && B1_active == 0) {oled_write_raw_P(r4c10[1], ANIM_SIZE); } else if (A1s_active == 0 && B1_active == 1) {oled_write_raw_P(r4c10[2], ANIM_SIZE); } else if (A1s_active == 1 && B1_active == 1) {oled_write_raw_P(r4c10[3], ANIM_SIZE); } else {oled_write_raw_P(r4c10[0], ANIM_SIZE); }
	oled_set_cursor(10, 12);  // Adjust the x position as needed
	if (B1_active == 1) {oled_write_raw_P(r4c11[1], ANIM_SIZE);} else {oled_write_raw_P(r4c11[0], ANIM_SIZE);}
	oled_set_cursor(11, 12);  // Adjust the x position as needed
	if (C2_active == 1) {oled_write_raw_P(r4c12[1], ANIM_SIZE); } else {oled_write_raw_P(r4c12[0], ANIM_SIZE); }
	oled_set_cursor(12, 12);  // Adjust the x position as needed
    if (C2s_active == 1 && D2_active == 0) {oled_write_raw_P(r4c13[1], ANIM_SIZE); } else if (C2s_active == 0 && D2_active == 1) {oled_write_raw_P(r4c13[2], ANIM_SIZE); } else if (C2s_active == 1 && D2_active == 1) {oled_write_raw_P(r4c13[3], ANIM_SIZE); } else {oled_write_raw_P(r4c13[0], ANIM_SIZE); }
	oled_set_cursor(13, 12);  // Adjust the x position as needed
    if (D2_active == 1 && D2s_active == 0) {oled_write_raw_P(r4c14[1], ANIM_SIZE); } else if (D2_active == 0 && D2s_active == 1) {oled_write_raw_P(r4c14[2], ANIM_SIZE); } else if (D2_active == 1 && D2s_active == 1) {oled_write_raw_P(r4c14[3], ANIM_SIZE); } else {oled_write_raw_P(r4c14[0], ANIM_SIZE); }
	oled_set_cursor(14, 12);  // Adjust the x position as needed
    if (E2_active == 1) {oled_write_raw_P(r4c15[1], ANIM_SIZE);} else {oled_write_raw_P(r4c15[0], ANIM_SIZE);}
	oled_set_cursor(15, 12);  // Adjust the x position as needed
    if (F2_active == 1) {oled_write_raw_P(r4c16[1], ANIM_SIZE); } else {oled_write_raw_P(r4c16[0], ANIM_SIZE); }
	oled_set_cursor(16, 12);  // Adjust the x position as needed
    if (F2_active == 1 && F2s_active == 0) {oled_write_raw_P(r4c17[1], ANIM_SIZE); } else if (F2_active == 0 && F2s_active == 1) {oled_write_raw_P(r4c17[2], ANIM_SIZE); } else if (F2_active == 1 && F2s_active == 1) {oled_write_raw_P(r4c17[3], ANIM_SIZE); } else {oled_write_raw_P(r4c17[0], ANIM_SIZE); }
	oled_set_cursor(17, 12);  // Adjust the x position as needed
	if (G2_active == 1) {oled_write_raw_P(r4c18[1], ANIM_SIZE); } else {oled_write_raw_P(r4c18[0], ANIM_SIZE); }
	oled_set_cursor(18, 12);  // Adjust the x position as needed
	if (G2s_active == 1 && A2_active == 0) {oled_write_raw_P(r4c19[1], ANIM_SIZE); } else if (G2s_active == 0 && A2_active == 1) {oled_write_raw_P(r4c19[2], ANIM_SIZE); } else if (G2s_active == 1 && A2_active == 1) {oled_write_raw_P(r4c19[3], ANIM_SIZE); } else {oled_write_raw_P(r4c19[0], ANIM_SIZE); }
	oled_set_cursor(19, 12);  // Adjust the x position as needed
	if (A2_active == 1 && A2s_active == 0) {oled_write_raw_P(r4c20[1], ANIM_SIZE); } else if (A2_active == 0 && A2s_active == 1) {oled_write_raw_P(r4c20[2], ANIM_SIZE); } else if (A2_active == 1 && A2s_active == 1) {oled_write_raw_P(r4c20[3], ANIM_SIZE); } else {oled_write_raw_P(r4c20[0], ANIM_SIZE); }
	oled_set_cursor(20, 12);  // Adjust the x position as needed
	if (B2_active == 1) {oled_write_raw_P(r4c21[1], ANIM_SIZE); } else {oled_write_raw_P(r4c21[0], ANIM_SIZE); }
	oled_set_cursor(21, 12);  // Adjust the x position as needed
	oled_write_raw_P(endbar[0], ANIM_SIZE);
	
	oled_set_cursor(0, 13);  // Adjust the x position as needed
	if (C1_active == 1) {oled_write_raw_P(r5c1[1], ANIM_SIZE);} else {oled_write_raw_P(r5c1[0], ANIM_SIZE);}
	oled_set_cursor(2, 13);  // Adjust the x position as needed
	if (D1_active == 1) {oled_write_raw_P(r5c2[1], ANIM_SIZE);} else {oled_write_raw_P(r5c2[0], ANIM_SIZE);}
	oled_set_cursor(3, 13);  // Adjust the x position as needed
	if (E1_active == 1) {oled_write_raw_P(r5c3[1], ANIM_SIZE);} else {oled_write_raw_P(r5c3[0], ANIM_SIZE);}
	oled_set_cursor(5, 13);  // Adjust the x position as needed
	if (F1_active == 1) {oled_write_raw_P(r5c4[1], ANIM_SIZE);} else {oled_write_raw_P(r5c4[0], ANIM_SIZE);}
	oled_set_cursor(6, 13);  // Adjust the x position as needed
	if (G1_active == 1) {oled_write_raw_P(r5c5[1], ANIM_SIZE);} else {oled_write_raw_P(r5c5[0], ANIM_SIZE);}
	oled_set_cursor(8, 13);  // Adjust the x position as needed
	if (A1_active == 1) {oled_write_raw_P(r5c6[1], ANIM_SIZE);} else {oled_write_raw_P(r5c6[0], ANIM_SIZE);}
	oled_set_cursor(9, 13);  // Adjust the x position as needed
	if (B1_active == 1) {oled_write_raw_P(r5c7[1], ANIM_SIZE);} else {oled_write_raw_P(r5c7[0], ANIM_SIZE);}
	oled_set_cursor(11, 13);  // Adjust the x position as needed
	if (C2_active == 1) {oled_write_raw_P(r5c8[1], ANIM_SIZE);} else {oled_write_raw_P(r5c8[0], ANIM_SIZE);}
	oled_set_cursor(12, 13);  // Adjust the x position as needed
	if (D2_active == 1) {oled_write_raw_P(r5c9[1], ANIM_SIZE);} else {oled_write_raw_P(r5c9[0], ANIM_SIZE);}
	oled_set_cursor(14, 13);  // Adjust the x position as needed
	if (E2_active == 1) {oled_write_raw_P(r5c10[1], ANIM_SIZE);} else {oled_write_raw_P(r5c10[0], ANIM_SIZE);}
	oled_set_cursor(15, 13);  // Adjust the x position as needed
	if (F2_active == 1) {oled_write_raw_P(r5c11[1], ANIM_SIZE);} else {oled_write_raw_P(r5c11[0], ANIM_SIZE);}
	oled_set_cursor(17, 13);  // Adjust the x position as needed
	if (G2_active == 1) {oled_write_raw_P(r5c12[1], ANIM_SIZE);} else {oled_write_raw_P(r5c12[0], ANIM_SIZE);}
	oled_set_cursor(18, 13);  // Adjust the x position as needed
	if (A2_active == 1) {oled_write_raw_P(r5c13[1], ANIM_SIZE);} else {oled_write_raw_P(r5c13[0], ANIM_SIZE);}
	oled_set_cursor(20, 13);  // Adjust the x position as needed
	if (B2_active == 1) {oled_write_raw_P(r5c14[1], ANIM_SIZE);} else {oled_write_raw_P(r5c14[0], ANIM_SIZE);}
	oled_set_cursor(21, 13);  // Adjust the x position as needed
	oled_write_raw_P(endbar[0], ANIM_SIZE);
	
	oled_set_cursor(0, 14);  // Adjust the x position as needed
	if (C1_active == 1) {oled_write_raw_P(r6c1[1], ANIM_SIZE);} else {oled_write_raw_P(r6c1[0], ANIM_SIZE);}
	oled_set_cursor(2, 14);  // Adjust the x position as needed
	if (D1_active == 1) {oled_write_raw_P(r6c2[1], ANIM_SIZE);} else {oled_write_raw_P(r6c2[0], ANIM_SIZE);}
	oled_set_cursor(3, 14);  // Adjust the x position as needed
	if (E1_active == 1) {oled_write_raw_P(r6c3[1], ANIM_SIZE);} else {oled_write_raw_P(r6c3[0], ANIM_SIZE);}
	oled_set_cursor(5, 14);  // Adjust the x position as needed
	if (F1_active == 1) {oled_write_raw_P(r6c4[1], ANIM_SIZE);} else {oled_write_raw_P(r6c4[0], ANIM_SIZE);}
	oled_set_cursor(6, 14);  // Adjust the x position as needed
	if (G1_active == 1) {oled_write_raw_P(r6c5[1], ANIM_SIZE);} else {oled_write_raw_P(r6c5[0], ANIM_SIZE);}
	oled_set_cursor(8, 14);  // Adjust the x position as needed
	if (A1_active == 1) {oled_write_raw_P(r6c6[1], ANIM_SIZE);} else {oled_write_raw_P(r6c6[0], ANIM_SIZE);}
	oled_set_cursor(9, 14);  // Adjust the x position as needed
	if (B1_active == 1) {oled_write_raw_P(r6c7[1], ANIM_SIZE);} else {oled_write_raw_P(r6c7[0], ANIM_SIZE);}
	oled_set_cursor(11, 14);  // Adjust the x position as needed
	if (C2_active == 1) {oled_write_raw_P(r6c8[1], ANIM_SIZE);} else {oled_write_raw_P(r6c8[0], ANIM_SIZE);}
	oled_set_cursor(12, 14);  // Adjust the x position as needed
	if (D2_active == 1) {oled_write_raw_P(r6c9[1], ANIM_SIZE);} else {oled_write_raw_P(r6c9[0], ANIM_SIZE);}
	oled_set_cursor(14, 14);  // Adjust the x position as needed
	if (E2_active == 1) {oled_write_raw_P(r6c10[1], ANIM_SIZE);} else {oled_write_raw_P(r6c10[0], ANIM_SIZE);}
	oled_set_cursor(15, 14);  // Adjust the x position as needed
	if (F2_active == 1) {oled_write_raw_P(r6c11[1], ANIM_SIZE);} else {oled_write_raw_P(r6c11[0], ANIM_SIZE);}
	oled_set_cursor(17, 14);  // Adjust the x position as needed
	if (G2_active == 1) {oled_write_raw_P(r6c12[1], ANIM_SIZE);} else {oled_write_raw_P(r6c12[0], ANIM_SIZE);}
	oled_set_cursor(18, 14);  // Adjust the x position as needed
	if (A2_active == 1) {oled_write_raw_P(r6c13[1], ANIM_SIZE);} else {oled_write_raw_P(r6c13[0], ANIM_SIZE);}
	oled_set_cursor(20, 14);  // Adjust the x position as needed
	if (B2_active == 1) {oled_write_raw_P(r6c14[1], ANIM_SIZE);} else {oled_write_raw_P(r6c14[0], ANIM_SIZE);}
	oled_set_cursor(21, 14);  // Adjust the x position as needed
	oled_write_raw_P(endbar[0], ANIM_SIZE);
	
	oled_set_cursor(0, 15);  // Adjust the x position as needed
    oled_write_raw_P(Keyboardbottom[0], 128);

}

#    if OLED_TIMEOUT > 0
/* the animation prevents the normal timeout from occuring */
if (last_input_activity_elapsed() > OLED_TIMEOUT && last_led_activity_elapsed() > OLED_TIMEOUT) {
	
    oled_off();
    return;
} else {
    oled_on();
}
#    endif

    /* animation timer */
    if (timer_elapsed32(anim_timer) > ANIM_FRAME_DURATION) {
        anim_timer = timer_read32();
        animate_luna();
    }
}

void set_keylog(uint16_t keycode, keyrecord_t *record) {
    char name[44];
    memset(name, ' ', sizeof(name) - 1);  // Fill with spaces
    name[sizeof(name) - 1] = '\0';        // Null-terminate the string

    if ((keycode >= QK_MOD_TAP && keycode <= QK_MOD_TAP_MAX) ||
        (keycode >= QK_LAYER_TAP && keycode <= QK_LAYER_TAP_MAX)) {
        keycode = keycode & 0xFF;
    }
	
	if ((keycode >= 28931 && keycode <= 29002) || (keycode >= 50688 && keycode <= 50759) || (keycode >= 50800 && keycode <= 50871)) {
		
     // Calculate note number within the musical note range
    //int note_number = keycode - 28931 + 24 + transpose_number + octave_number;
	int note_number1 = hk1;
	int note_number2 = hk2;
	int note_number3 = hk3;
	int note_number4 = hk4;
	int note_number5 = hk5;
	int note_number6 = hk6;
	int note_number7 = hk7;
	
		
    // Update the name string with new line

if (hk7 != 0){
    snprintf(name, sizeof(name), "%s,%s,%s,%s,%s,%s,%s",
             chord_note_names[note_number1 % 12],
             chord_note_names[note_number2 % 12],
             chord_note_names[note_number3 % 12],
             chord_note_names[note_number4 % 12],
             chord_note_names[note_number5 % 12],
             chord_note_names[note_number6 % 12],
             chord_note_names[note_number7 % 12]);
} else if (hk6 != 0) {
    snprintf(name, sizeof(name), "%s ,%s ,%s ,%s ,%s ,%s",
             chord_note_names[note_number1 % 12],
             chord_note_names[note_number2 % 12],
             chord_note_names[note_number3 % 12],
             chord_note_names[note_number4 % 12],
             chord_note_names[note_number5 % 12],
             chord_note_names[note_number6 % 12]);
} else if (hk5 != 0) {
    snprintf(name, sizeof(name), "%s, %s, %s, %s, %s",
             chord_note_names[note_number1 % 12],
             chord_note_names[note_number2 % 12],
             chord_note_names[note_number3 % 12],
             chord_note_names[note_number4 % 12],
             chord_note_names[note_number5 % 12]);
} else if (hk4 != 0) {
    snprintf(name, sizeof(name), "%s, %s, %s, %s",
             chord_note_names[note_number1 % 12],
             chord_note_names[note_number2 % 12],
             chord_note_names[note_number3 % 12],
             chord_note_names[note_number4 % 12]);
} else if (hk3 != 0) {
    snprintf(name, sizeof(name), "%s, %s, %s",
             chord_note_names[note_number1 % 12],
             chord_note_names[note_number2 % 12],
             chord_note_names[note_number3 % 12]);
} else if (hk2 != 0) {
    snprintf(name, sizeof(name), "%s, %s",
             chord_note_names[note_number1 % 12],
             chord_note_names[note_number2 % 12]);
} else if (hk1 != 0) {
    snprintf(name, sizeof(name), "Note  %s", midi_note_names[note_number1]);
	
} else if (hk1 == 0) {
    snprintf(name, sizeof(name), "   ");  // Three spaces
}




	//velocity
    } else if (keycode >= 49925 && keycode <= 50052) {
	velocity_number = (keycode - 49925);
    snprintf(name, sizeof(name), "Velocity %d", keycode - 49925);
	//velocity2
    } else if (keycode >= 0xC6CA && keycode <= 0xC749) {
	velocity_number2 = (keycode - 0xC6CA);
    snprintf(name, sizeof(name), "KS Velocity %d", keycode - 0xC6CA);
	//velocity3
    } else if (keycode >= 0xC77A && keycode <= 0xC7F9) {
	velocity_number3 = (keycode - 0xC77A);
    snprintf(name, sizeof(name), "TS Velocity %d", keycode - 0xC77A);
	//program change	
    } else if (keycode >= 49792 && keycode <= 49919) {
        snprintf(name, sizeof(name), "Program %d", keycode - 49792);
		
	// MIDI Channel
	} else if (keycode >= 29043 && keycode <= 29058) {
	channel_number = keycode - 29043;
    snprintf(name, sizeof(name), "DEFAULT CHANNEL  %d", channel_number);
	
	} else if (keycode >= 0xC652 && keycode <= 0xC661) {
	keysplitchannel = keycode - 0xC652;
    snprintf(name, sizeof(name), "KEYSPLIT CH  %d", keysplitchannel);
	
		} else if (keycode >= 0xC6BA && keycode <= 0xC6C9) {
	keysplit2channel = keycode - 0xC6BA;
    snprintf(name, sizeof(name), "TRIPLESPLIT CH %d", keysplit2channel);
	

	} else if (keycode == 0xC458) {
		if (oledkeyboard == 0) {
			oledkeyboard = 12;
			snprintf(name, sizeof(name),"Screenboard 2");
			
		} else if (oledkeyboard == 12) {
			oledkeyboard = 0;
			snprintf(name, sizeof(name),"Screenboard 1");
			}                                     
	
	} else if (keycode == 0xC459) {
		if (sclightmode != 3) {
			sclightmode = 3;
			static const uint8_t temp_array_0[72] = {
   						//99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
						//99, 99, 99, 99, 56, 57, 58, 59, 60, 42, 43, 44, 
						//45, 46, 28, 29, 30, 31, 32, 14, 15, 16, 17, 0,
						//1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
						//13, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
						//99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0
					};
					memcpy(keycode_to_led_index, temp_array_0, sizeof(temp_array_0));
			snprintf(name, sizeof(name),"SC Light Mode Guitar 1");
			
		} else if (sclightmode == 3) {
			sclightmode = 4;
							    static const uint8_t temp_array_1[72] = {
   						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0,
						1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0
					};
					memcpy(keycode_to_led_index, temp_array_1, sizeof(temp_array_1));
			snprintf(name, sizeof(name),"SC Light Mode Guitar 2");
			}
	
			
	} else if (keycode == 0xC45A) {
		if (sclightmode != 0) {
			sclightmode = 0;
			static const uint8_t temp_array_0[72] = {
						99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
						42, 28, 43, 29, 44, 45, 31, 46, 32, 47, 33, 48, 
						14, 0, 15, 1, 16, 17, 3, 18, 4, 19, 5, 20,
						21, 7, 22, 8, 23, 24, 10, 25, 11, 26, 12, 27,
						99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
						99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99
					};
					memcpy(keycode_to_led_index, temp_array_0, sizeof(temp_array_0));
			snprintf(name, sizeof(name),"SC Light Mode Piano 1");
			
		} else if (sclightmode == 0) {
			sclightmode = 1;
							    static const uint8_t temp_array_1[72] = {
						99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
						42, 29, 43, 30, 44, 45, 32, 46, 33, 47, 34, 48, 
						14, 1, 15, 2, 16, 17, 4, 18, 5, 19, 6, 20,
						21, 8, 22, 9, 23, 24, 11, 25, 12, 26, 13, 27,
						99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
						99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99
					};
					memcpy(keycode_to_led_index, temp_array_1, sizeof(temp_array_1));
			snprintf(name, sizeof(name),"SC Light Mode Piano 2");
			}
	
	} else if (keycode >= 0xC438 && keycode <= 0xC447) {
			if (record->event.pressed) {
				oneshotchannel = 1;
				channelplaceholder = channel_number;  // Store the current channel
				channel_number = (keycode - 0xC438);  // Set the MIDI channel temporarily
				snprintf(name, sizeof(name), "Temporary Channel %d", channel_number);
			}
			
	
	
	} else if (keycode >= 0xC448 && keycode <= 0xC457) {
    if (record->event.pressed) {
        channelplaceholder = channel_number;  // Store the current channel
        channel_number = (keycode - 0xC448);  // Set the MIDI channel based on the keycode    
		snprintf(name, sizeof(name), "Hold Channel %d", channel_number);
    } else {
            channel_number = channelplaceholder;  // Restore the previous channel
            channelplaceholder = 0;  // Reset the placeholder
        snprintf(name, sizeof(name), "Channel %d", channel_number);
    }
	
	} else if (keycode == 0xC662) {
		if (keysplitstatus == 0) { keysplitstatus = 1;
		snprintf(name, sizeof(name),"KeySplit On");
		}else if (keysplitstatus == 1) { keysplitstatus = 2;
		snprintf(name, sizeof(name),"TripleSplit On");
		}else if (keysplitstatus == 2) { keysplitstatus = 0;
		snprintf(name, sizeof(name),"KeySplit Off");
		}
	} else if (keycode == 0xC800) {
		if (keysplittransposestatus == 0) { keysplittransposestatus = 1;
		snprintf(name, sizeof(name),"KS TRANSPOSE ON");
		}else if (keysplittransposestatus == 1) { keysplittransposestatus = 2;
		snprintf(name, sizeof(name),"TS TRANSPOSE ON");
		}else if (keysplittransposestatus == 2) { keysplittransposestatus = 0;
		snprintf(name, sizeof(name),"KS TRANSPOSE OFF");
		}
		
	} else if (keycode == 0xC801) {
		if (keysplitvelocitystatus == 0) { keysplitvelocitystatus = 1;
		snprintf(name, sizeof(name),"KS VELOCITY ON");
		}else if (keysplitvelocitystatus == 1) { keysplitvelocitystatus = 2;
		snprintf(name, sizeof(name),"TS VELOCITY ON");
		}else if (keysplitvelocitystatus == 2) { keysplitvelocitystatus = 0;
		snprintf(name, sizeof(name),"KS VELOCITY OFF");
		}

	} else if (keycode == 0xC650) {
		snprintf(name, sizeof(name), "KeySplit Chan Down");
		if (keysplitchannel == 0) {
            keysplitchannel = 15;
		}
        else {keysplitchannel--;}
		snprintf(name, sizeof(name),"KeySplit Channel Down");

	} else if (keycode == 0xC651) {
		snprintf(name, sizeof(name), "KeySplit Channel Up");
        keysplitchannel++;
		if (keysplitchannel > 15) {
        keysplitchannel = 0;
		}
		snprintf(name, sizeof(name),"KeySplit Channel Up");
		
	} else if (keycode == 0xC6B8) {
		snprintf(name, sizeof(name), "TripleSplit Ch Down");
		if (keysplit2channel == 0) {
            keysplit2channel = 15;
		}
        else {keysplit2channel--;}
		snprintf(name, sizeof(name),"TripleSplit Ch Down");

	} else if (keycode == 0xC6B9) {
		snprintf(name, sizeof(name), "TripleSplit Ch Up");
        keysplit2channel++;
		if (keysplit2channel > 15) {
        keysplit2channel = 0;
		}
		snprintf(name, sizeof(name),"TripleSplit Ch Up");
	
	} else if (keycode == 29059) {
		snprintf(name, sizeof(name), "Chan Down");
		if (channel_number == 0) {
            channel_number = 15;
		}
        else {channel_number--;}
		snprintf(name, sizeof(name),"Channel Down");

	} else if (keycode == 29060) {
		snprintf(name, sizeof(name), "Channel Up");
        channel_number++;
		if (channel_number > 15) {
        channel_number = 0;
		}
		snprintf(name, sizeof(name),"Channel Up");
		
		

		
	} else if (keycode == 0xC4A2) {
		if (colorblindmode == 0) {
            colorblindmode = 1;
			snprintf(name, sizeof(name), "Colorblind On");
        } else if (colorblindmode == 1) {
            colorblindmode = 0;
			snprintf(name, sizeof(name), "Colorblind Off");
		}
		
} else if (keycode >= 0xC420 && keycode <= 0xC425) {	
switch (keycode) {	
		case 0xC420:  snprintf(name, sizeof(name), "SC: Root Position");
		break;
		case 0xC421:  snprintf(name, sizeof(name), "SC: 1st Position");
		break;
		case 0xC422:  snprintf(name, sizeof(name), "SC: 2nd Position");
		break;
		case 0xC423:  snprintf(name, sizeof(name), "SC: 3rd Position");
		break;
		case 0xC424:  snprintf(name, sizeof(name), "SC: 4th Position");
		break;
		case 0xC425:  snprintf(name, sizeof(name), "SC: 5th Position");
		break;
	
	} 
	
	} else if (keycode >= 0xC396 && keycode <= 0xC416) {
		 switch (keycode) {
		case 0xC396:    // Major Chord
			snprintf(name, sizeof(name), "Chord Major");
break;
		case 0xC397:   // Minor Chord		
			snprintf(name, sizeof(name), "Chord Minor");
 break;
		case 0xC398:   // Diminished
			snprintf(name, sizeof(name), "Chord Dim");
 break;
		case 0xC399:   // Augmented
			snprintf(name, sizeof(name), "Chord Aug");			
break;
		case 0xC39A:   // b5
			snprintf(name, sizeof(name), "Chord b5");
 break;
		case 0xC39B:   // Sus2
			snprintf(name, sizeof(name), "Chord Sus2");
 break;
		case 0xC39C:    // Sus4
			snprintf(name, sizeof(name), "Chord Sus4");
 break;
		case 0xC39D:    // Maj6
			snprintf(name, sizeof(name), "Chord Maj6");
 break;
		 case 0xC39E:    // Min6
			snprintf(name, sizeof(name), "Chord Min6");
 break;
		case 0xC39F:    // Maj7	
			snprintf(name, sizeof(name), "Chord Maj7");
 break;
		case 0xC3A0:    // Min7
			snprintf(name, sizeof(name), "Chord Min7");
 break;
		case 0xC3A1:    // Dom7
			snprintf(name, sizeof(name), "Chord 7");
break;
		case 0xC3A2:    // Diminished 7th (dim7)
			snprintf(name, sizeof(name), "Chord dim7");
break;
		case 0xC3A3:    // Half-Diminished 7th (ø7) (m7b5)
			snprintf(name, sizeof(name), "Chord Halfdim7");
break;
		case 0xC3A4:    // Augmented 7th (7#5)
			snprintf(name, sizeof(name), "Chord Aug7");
break;
		case 0xC3A5:    // Major9 (maj9)
			snprintf(name, sizeof(name), "Chord Maj9");
break;
		case 0xC3A6:    // Minor 9 (min9)
			snprintf(name, sizeof(name), "Chord Min9");
break;
		case 0xC3A7:    // Dominant 9 (dom9)
			snprintf(name, sizeof(name), "Chord 9");
break;			
		case 0xC3A8:    // Major add2 (majadd2)
			snprintf(name, sizeof(name), "Chord Add2");
break;
		case 0xC3A9:    // Minor add2 (madd2)
			snprintf(name, sizeof(name), "Chord mAdd2");
break;
		case 0xC3AA:    // Major add4 (majadd4)
			snprintf(name, sizeof(name), "Chord add4");
break;
		case 0xC3AB:    // Minor add4 (madd4)
			snprintf(name, sizeof(name), "Chord mAdd4");
break;		
		case 0xC3AC:    // Major 6/9
			snprintf(name, sizeof(name), "Chord 6/9");
break;
		case 0xC3AD:    // Minor 6/9
			snprintf(name, sizeof(name), "Chord Minor 6/9");
break;				
		case 0xC3AE:    // Minor Major 7th (m(maj7))
			snprintf(name, sizeof(name), "Chord MinMaj7");
break;
		case 0xC3AF:    // Major 7sus4 (maj7sus4)
			snprintf(name, sizeof(name), "Chord Maj7sus4");
break;
		case 0xC3B0:    // Dominant 7sus4 (7sus4)
			snprintf(name, sizeof(name), "Chord 7sus4");
break;
		case 0xC3B1:    // Major 7sus2 (maj7sus2)
			snprintf(name, sizeof(name), "Chord Maj7sus2");
break;
		case 0xC3B2:    // Dominant 7sus2 (7sus2)
			snprintf(name, sizeof(name), "Chord 7sus2");
break;
		case 0xC3B3:    // Major 7th with Raised 5 (Maj7#5)
			snprintf(name, sizeof(name), "Chord Maj7#5");
break;
		case 0xC3B4:    // Minor 7th with Raised 5 (m7#5)
			snprintf(name, sizeof(name), "Chord m7#5");
break;
		case 0xC3B5:    // Major 7th with Lowered 5 (maj7b5)
			snprintf(name, sizeof(name), "Chord Maj7b5");
break;
		case 0xC3B6:    // Dominant 7th with Lowered 5 (7b5)
			snprintf(name, sizeof(name), "Chord 7b5");
break;
		case 0xC3B7:    // Major 7th with no 5 (Maj7no5)
			snprintf(name, sizeof(name), "Chord Maj7no5");
break;			
		case 0xC3B8:    // Minor 7th with no 5 (min7no5)
			snprintf(name, sizeof(name), "Chord Min7no5");
break;			
		case 0xC3B9:    // Dominant 7th with no 5 (7no5)
			snprintf(name, sizeof(name), "Chord 7no5");
break;	
		case 0xC3BA:    // Major add9 (add9)
			snprintf(name, sizeof(name), "Chord Add9");
break;
		case 0xC3BB:    // Minor add9 (madd9)
			snprintf(name, sizeof(name), "Chord mAdd9");
break;
		case 0xC3BC:    // Diminished 9 (dim9)
			snprintf(name, sizeof(name), "Chord Dim9");
break;
		case 0xC3BD:    // Half-Diminished 9 (ø9)
			snprintf(name, sizeof(name), "Chord HalfDim9");
break;
		case 0xC3BE:    // Augmented 9th (9#5)
			snprintf(name, sizeof(name), "Chord Aug9");
break;
		case 0xC3BF:    // Major 11 (maj11)
			snprintf(name, sizeof(name), "Chord Maj11");
break;
		case 0xC3C0:    // Minor 11 (min11)
			snprintf(name, sizeof(name), "Chord Min11");
break;
		case 0xC3C1:    // Dominant 11 (dom11)
			snprintf(name, sizeof(name), "Chord 11");
break;
		case 0xC3C2:    // Major add11 (add11))
			snprintf(name, sizeof(name), "Chord Add11");
break;
		case 0xC3C3:    // Minor add11 (madd11))
			snprintf(name, sizeof(name), "Chord mAdd11");
break;
		case 0xC3C4:    // Major 7th add11 (maj7(add11))
			snprintf(name, sizeof(name), "Chord Maj7Add11");
break;
		case 0xC3C5:    // Minor 7th add11 (m7(add11))
			snprintf(name, sizeof(name), "Chord min7Add11");
break;
		case 0xC3C6:    // Dominant 7th add11 (7(add11))
			snprintf(name, sizeof(name), "Chord 7Add11");
break;
		case 0xC3C7:    // Diminished 11 (dim11)
			snprintf(name, sizeof(name), "Chord Dim11");
break;
		case 0xC3C8:    // Half-Diminished 11 (ø11)
			snprintf(name, sizeof(name), "Chord HalfDim11");
			
break;
		case 0xC3C9:    // Maj7#11 (Maj7#11)
			snprintf(name, sizeof(name), "Chord Maj7#11");
			
break;
		case 0xC3CA:    // Min7#11 (min7#11)
			snprintf(name, sizeof(name), "Chord min7#11");
			
break;
		case 0xC3CB:    // 7#11 (7#11)
			snprintf(name, sizeof(name), "Chord 7#11");
			
			
break;
		case 0xC3FB:    // Major Scale (Ionian)
			snprintf(name, sizeof(name), "Major (Ionian)");
			
break;
		case 0xC3FC:    // Dorian
			snprintf(name, sizeof(name), "Dorian");
			
break;
		case 0xC3FD:    // Phrygian
			snprintf(name, sizeof(name), "Phrygian");
			
break;
		case 0xC3FE:    // Lydian
			snprintf(name, sizeof(name), "Lydian");
			
break;
		case 0xC3FF:    // Mixolydian 
			snprintf(name, sizeof(name), "Mixolydian");
			
break;
		case 0xC400:    // Minor Scale (Aeolian)
			snprintf(name, sizeof(name), "Minor (Aeolian)");
			
break;
		case 0xC401:    // Locrian
			snprintf(name, sizeof(name), "Locrian");
			
break;
		case 0xC402:    // Harmonic Minor
			snprintf(name, sizeof(name), "Harmonic Minor");
			
break;
		case 0xC403:    // Melodic Minor
			snprintf(name, sizeof(name), "Melodic Minor");
			
break;
		case 0xC404:    // Whole Step
			snprintf(name, sizeof(name), "Whole Step Scale");
			
break;
		case 0xC405:    // Major Pentatonic
			snprintf(name, sizeof(name), "Major Pentatonic");
			
break;
		case 0xC406:    // Minor Pentatonic
			snprintf(name, sizeof(name), "Minor Pentatonic");
			}
			
} else if (keycode >= 0xC460 && keycode <= 0xC49F) {
    switch (keycode) {
        case 0xC460:    // RGB MATRIX NONE
            rgb_matrix_mode(RGB_MATRIX_NONE);
            snprintf(name, sizeof(name), "RGB None");
            break;

        case 0xC461:    // RGB MATRIX SOLID COLOR
            rgb_matrix_mode(RGB_MATRIX_SOLID_COLOR);
            snprintf(name, sizeof(name), "RGB Solid Color");
            break;

        case 0xC462:    // RGB MATRIX ALPHAS MODS
            rgb_matrix_mode(RGB_MATRIX_ALPHAS_MODS);
            snprintf(name, sizeof(name), "RGB Alphas Mods");
            break;

        case 0xC463:    // RGB MATRIX GRADIENT UP DOWN
            rgb_matrix_mode(RGB_MATRIX_GRADIENT_UP_DOWN);
            snprintf(name, sizeof(name), "RGB Gradient Up Down");
            break;

        case 0xC464:    // RGB MATRIX GRADIENT LEFT RIGHT
            rgb_matrix_mode(RGB_MATRIX_GRADIENT_LEFT_RIGHT);
            snprintf(name, sizeof(name), "RGB Gradient Left Right");
            break;

        case 0xC465:    // RGB MATRIX BREATHING
            rgb_matrix_mode(RGB_MATRIX_BREATHING);
            snprintf(name, sizeof(name), "RGB Breathing");
            break;

        case 0xC466:    // RGB MATRIX BAND SAT
            rgb_matrix_mode(RGB_MATRIX_BAND_SAT);
            snprintf(name, sizeof(name), "RGB Band Sat");
            break;

        case 0xC467:    // RGB MATRIX BAND VAL
            rgb_matrix_mode(RGB_MATRIX_BAND_VAL);
            snprintf(name, sizeof(name), "RGB Band Val");
            break;

        case 0xC468:    // RGB MATRIX BAND PINWHEEL SAT
            rgb_matrix_mode(RGB_MATRIX_BAND_PINWHEEL_SAT);
            snprintf(name, sizeof(name), "RGB Band Pinwheel Sat");
            break;

        case 0xC469:    // RGB MATRIX BAND PINWHEEL VAL
            rgb_matrix_mode(RGB_MATRIX_BAND_PINWHEEL_VAL);
            snprintf(name, sizeof(name), "RGB Band Pinwheel Val");
            break;

        case 0xC46A:    // RGB MATRIX BAND SPIRAL SAT
            rgb_matrix_mode(RGB_MATRIX_BAND_SPIRAL_SAT);
            snprintf(name, sizeof(name), "RGB Band Spiral Sat");
            break;

        case 0xC46B:    // RGB MATRIX BAND SPIRAL VAL
            rgb_matrix_mode(RGB_MATRIX_BAND_SPIRAL_VAL);
            snprintf(name, sizeof(name), "RGB Band Spiral Val");
            break;

        case 0xC46C:    // RGB MATRIX CYCLE ALL
            rgb_matrix_mode(RGB_MATRIX_CYCLE_ALL);
            snprintf(name, sizeof(name), "RGB Cycle All");
            break;

        case 0xC46D:    // RGB MATRIX CYCLE LEFT RIGHT
            rgb_matrix_mode(RGB_MATRIX_CYCLE_LEFT_RIGHT);
            snprintf(name, sizeof(name), "RGB Cycle Left Right");
            break;

        case 0xC46E:    // RGB MATRIX CYCLE UP DOWN
            rgb_matrix_mode(RGB_MATRIX_CYCLE_UP_DOWN);
            snprintf(name, sizeof(name), "RGB Cycle Up Down");
            break;

        case 0xC46F:    // RGB MATRIX CYCLE OUT IN
            rgb_matrix_mode(RGB_MATRIX_CYCLE_OUT_IN);
            snprintf(name, sizeof(name), "RGB Cycle Out In");
            break;

        case 0xC470:    // RGB MATRIX CYCLE OUT IN DUAL
            rgb_matrix_mode(RGB_MATRIX_CYCLE_OUT_IN_DUAL);
            snprintf(name, sizeof(name), "RGB Cycle Out In Dual");
            break;

        case 0xC471:    // RGB MATRIX RAINBOW MOVING CHEVRON
            rgb_matrix_mode(RGB_MATRIX_RAINBOW_MOVING_CHEVRON);
            snprintf(name, sizeof(name), "RGB Rainbow Chevron");
            break;

        case 0xC472:    // RGB MATRIX CYCLE PINWHEEL
            rgb_matrix_mode(RGB_MATRIX_CYCLE_PINWHEEL);
            snprintf(name, sizeof(name), "RGB Cycle Pinwheel");
            break;

        case 0xC473:    // RGB MATRIX CYCLE SPIRAL
            rgb_matrix_mode(RGB_MATRIX_CYCLE_SPIRAL);
            snprintf(name, sizeof(name), "RGB Cycle Spiral");
            break;

        case 0xC474:    // RGB MATRIX DUAL BEACON
            rgb_matrix_mode(RGB_MATRIX_DUAL_BEACON);
            snprintf(name, sizeof(name), "RGB Dual Beacon");
            break;

        case 0xC475:    // RGB MATRIX RAINBOW BEACON
            rgb_matrix_mode(RGB_MATRIX_RAINBOW_BEACON);
            snprintf(name, sizeof(name), "RGB Rainbow Beacon");
            break;

        case 0xC476:    // RGB MATRIX RAINBOW PINWHEELS
            rgb_matrix_mode(RGB_MATRIX_RAINBOW_PINWHEELS);
            snprintf(name, sizeof(name), "RGB Rainbow Pinwheels");
            break;

        case 0xC477:    // RGB MATRIX RAINDROPS
            rgb_matrix_mode(RGB_MATRIX_RAINDROPS);
            snprintf(name, sizeof(name), "RGB Raindrops");
            break;

        case 0xC478:    // RGB MATRIX JELLYBEAN RAINDROPS
            rgb_matrix_mode(RGB_MATRIX_JELLYBEAN_RAINDROPS);
            snprintf(name, sizeof(name), "RGB Jellybean Raindrops");
            break;

        case 0xC479:    // RGB MATRIX HUE BREATHING
            rgb_matrix_mode(RGB_MATRIX_HUE_BREATHING);
            snprintf(name, sizeof(name), "RGB Hue Breathing");
            break;

        case 0xC47A:    // RGB MATRIX HUE PENDULUM
            rgb_matrix_mode(RGB_MATRIX_HUE_PENDULUM);
            snprintf(name, sizeof(name), "RGB Hue Pendulum");
            break;

        case 0xC47B:    // RGB MATRIX HUE WAVE
            rgb_matrix_mode(RGB_MATRIX_HUE_WAVE);
            snprintf(name, sizeof(name), "RGB Hue Wave");
            break;

        case 0xC47C:    // RGB MATRIX PIXEL FRACTAL
            rgb_matrix_mode(RGB_MATRIX_PIXEL_FRACTAL);
            snprintf(name, sizeof(name), "RGB Pixel Fractal");
            break;

        case 0xC47D:    // RGB MATRIX PIXEL FLOW
            rgb_matrix_mode(RGB_MATRIX_PIXEL_FLOW);
            snprintf(name, sizeof(name), "RGB Pixel Flow");
            break;

        case 0xC47E:    // RGB MATRIX PIXEL RAIN
            rgb_matrix_mode(RGB_MATRIX_PIXEL_RAIN);
            snprintf(name, sizeof(name), "RGB Pixel Rain");
            break;
			
        case 0xC47F:    // RGB MATRIX TYPING HEATMAP
            rgb_matrix_mode(RGB_MATRIX_TYPING_HEATMAP);
            snprintf(name, sizeof(name), "RGB Typing Heatmap");
            break;

        case 0xC480:    // RGB MATRIX DIGITAL RAIN
            rgb_matrix_mode(RGB_MATRIX_DIGITAL_RAIN);
            snprintf(name, sizeof(name), "RGB Digital Rain");
            break;

        case 0xC481:    // RGB MATRIX SOLID REACTIVE SIMPLE
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_SIMPLE);
            snprintf(name, sizeof(name), "RGB Solid Reactive Simple");
            break;

        case 0xC482:    // RGB MATRIX SOLID REACTIVE
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE);
            snprintf(name, sizeof(name), "RGB Solid Reactive");
            break;

        case 0xC483:    // RGB MATRIX SOLID REACTIVE WIDE
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_WIDE);
            snprintf(name, sizeof(name), "RGB Solid Reactive Wide");
            break;

        case 0xC484:    // RGB MATRIX SOLID REACTIVE MULTIWIDE
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_MULTIWIDE);
            snprintf(name, sizeof(name), "RGB Solid Reactive Multiwide");
            break;

        case 0xC485:    // RGB MATRIX SOLID REACTIVE CROSS
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_CROSS);
            snprintf(name, sizeof(name), "RGB Solid Reactive Cross");
            break;

        case 0xC486:    // RGB MATRIX SOLID REACTIVE MULTICROSS
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_MULTICROSS);
            snprintf(name, sizeof(name), "RGB Solid Reactive Multicross");
            break;

        case 0xC487:    // RGB MATRIX SOLID REACTIVE NEXUS
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_NEXUS);
            snprintf(name, sizeof(name), "RGB Solid Reactive Nexus");
            break;

        case 0xC488:    // RGB MATRIX SOLID REACTIVE MULTINEXUS
            rgb_matrix_mode(RGB_MATRIX_SOLID_REACTIVE_MULTINEXUS);
            snprintf(name, sizeof(name), "RGB Solid Reactive Multinexus");
            break;

        case 0xC489:    // RGB MATRIX SPLASH
            rgb_matrix_mode(RGB_MATRIX_SPLASH);
            snprintf(name, sizeof(name), "RGB Splash");
            break;

        case 0xC48A:    // RGB MATRIX MULTISPLASH
            rgb_matrix_mode(RGB_MATRIX_MULTISPLASH);
            snprintf(name, sizeof(name), "RGB Multisplash");
            break;

        case 0xC48B:    // RGB MATRIX SOLID SPLASH
            rgb_matrix_mode(RGB_MATRIX_SOLID_SPLASH);
            snprintf(name, sizeof(name), "RGB Solid Splash");
            break;

        case 0xC48C:    // RGB MATRIX SOLID MULTISPLASH
            rgb_matrix_mode(RGB_MATRIX_SOLID_MULTISPLASH);
            snprintf(name, sizeof(name), "RGB Solid Multisplash");
            break;

        case 0xC48D:    // RGB AZURE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_AZURE);
            snprintf(name, sizeof(name), "RGB Azure");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC48E:    // RGB BLACK / RGB OFF
            rgb_matrix_set_color_all(RGB_OFF);
            rgb_matrix_sethsv(RGB_OFF);
            snprintf(name, sizeof(name), "RGB OFF");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC48F:    // RGB BLUE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_BLUE);
            snprintf(name, sizeof(name), "RGB Blue");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC490:    // RGB CHARTREUSE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_CHARTREUSE);
            snprintf(name, sizeof(name), "RGB Chartreuse");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC491:    // RGB CORAL
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_CORAL);
            snprintf(name, sizeof(name), "RGB Coral");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC492:    // RGB CYAN
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_CYAN);
            snprintf(name, sizeof(name), "RGB Cyan");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC493:    // RGB GOLD
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_GOLD);
            snprintf(name, sizeof(name), "RGB Gold");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC494:    // RGB GOLDENROD
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_GOLDENROD);
            snprintf(name, sizeof(name), "RGB Goldenrod");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC495:    // RGB GREEN
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_GREEN);
            snprintf(name, sizeof(name), "RGB Green");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC496:    // RGB MAGENTA
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_MAGENTA);
            snprintf(name, sizeof(name), "RGB Magenta");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC497:    // RGB ORANGE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_ORANGE);
            snprintf(name, sizeof(name), "RGB Orange");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC498:    // RGB PINK
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_PINK);
            snprintf(name, sizeof(name), "RGB Pink");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC499:    // RGB PURPLE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_PURPLE);
            snprintf(name, sizeof(name), "RGB Purple");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49A:    // RGB RED
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_RED);
            snprintf(name, sizeof(name), "RGB Red");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49B:    // RGB SPRINGGREEN
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_SPRINGGREEN);
            snprintf(name, sizeof(name), "RGB Springgreen");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49C:    // RGB TEAL
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_TEAL);
            snprintf(name, sizeof(name), "RGB Teal");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49D:    // RGB TURQUOISE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_TURQUOISE);
            snprintf(name, sizeof(name), "RGB Turquoise");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49E:    // RGB WHITE
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_WHITE);
            snprintf(name, sizeof(name), "RGB White");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;

        case 0xC49F:    // RGB YELLOW
			hsvplaceholder = rgb_matrix_config.hsv.v;
            rgb_matrix_sethsv(HSV_YELLOW);
            snprintf(name, sizeof(name), "RGB Yellow");
			rgb_matrix_config.hsv.v = hsvplaceholder;
            break;
    }
		
	//octave value	
	} else if (keycode >= 29003 && keycode <= 29012) {
		octave_number = (keycode - 29005)*12;  // Adjusting for the range -6 to +6
        snprintf(name, sizeof(name), "OCTAVE %+d", keycode - 29005);
		
	} else if (keycode >= 0xC750 && keycode <= 0xC759) {
		octave_number2 = (keycode - 0xC750 - 2)*12;  // Adjusting for the range -6 to +6
        snprintf(name, sizeof(name), "KS OCTAVE %+d", keycode - 0xC750 - 2);
		
	} else if (keycode >= 0xC802 && keycode <= 0xC80B) {
		octave_number3 = (keycode - 0xC802 - 2)*12;  // Adjusting for the range -6 to +6
        snprintf(name, sizeof(name), "TS OCTAVE %+d", keycode - 0xC802 - 2);
		
	} else if (keycode >= 50053 && keycode <= 50068) {
        // Update cc_sensitivity value based on the key
        cc_sensitivity = keycode - 50052;  // Assuming the keycodes are consecutive
	    snprintf(name, sizeof(name), "CC INTERVAL %d", keycode - 50052);
		
	} else if (keycode >= 50220 && keycode <= 50229) {
        // Update cc_sensitivity value based on the key
        velocity_sensitivity = keycode - 50219;  // Assuming the keycodes are consecutive
	    snprintf(name, sizeof(name), "VELOCITY INTERVAL %d", keycode - 50219);	
	
	} else if (keycode >= 29015 && keycode <= 29027) {
        // Handle special keycodes within the range
        // Update the special number based on the keycode
        transpose_number = keycode - 29015 - 6;  // Adjusting for the range -6 to +6
	    snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);
		
	} else if (keycode >= 0xC75A && keycode <= 0xC765) {
        // Handle special keycodes within the range
        // Update the special number based on the keycode
        transpose_number2 = keycode - 0xC75A - 6;  // Adjusting for the range -6 to +6
	    snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);
		
	} else if (keycode >= 0xC766 && keycode <= 0xC771) {
        // Handle special keycodes within the range
        // Update the special number based on the keycode
        transpose_number3 = keycode - 0xC766 - 6;  // Adjusting for the range -6 to +6
	    snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number3 + 29]);
		
	 } else if (keycode == 29028) {
		snprintf(name, sizeof(name), "TRANSPOSE UP");
        // Decrease the special number by 1
        transpose_number--;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);

    } else if (keycode == 29029) {
	snprintf(name, sizeof(name), "TRANSPOSE DOWN");
        // Decrease the special number by 1
        transpose_number++;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);
		
	} else if (keycode == 0xC74C) {
		snprintf(name, sizeof(name), "KS TRANSPOSE UP");
        // Decrease the special number by 1
        transpose_number2--;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);

    } else if (keycode == 0xC74D) {
	snprintf(name, sizeof(name), "KS TRANSPOSE DOWN");
        // Decrease the special number by 1
        transpose_number2++;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);
		
	} else if (keycode == 0xC7FC) {
		snprintf(name, sizeof(name), "TS TRANSPOSE UP");
        // Decrease the special number by 1
        transpose_number3--;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);

    } else if (keycode == 0xC7FD) {
	snprintf(name, sizeof(name), "TS TRANSPOSE DOWN");
        // Decrease the special number by 1
        transpose_number3++;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number2 + 29]);
		
	} else if (keycode == 0xC4A3) {
		if (sclight == 3) {
            sclight = 0;
			snprintf(name, sizeof(name), "sc Lights On");
        } else if ( sclight != 3) {
            sclight = 3;
			snprintf(name, sizeof(name), "sc Lights Off");
			}
		
	} else if (keycode == 0xC436){
		 snprintf(name, sizeof(name), "VELOCITY UP");
			if (velocity_number == 0) {
                    velocity_number += (velocity_sensitivity);
               } else if ((velocity_number + (velocity_sensitivity)) <127) {
                    velocity_number += (velocity_sensitivity);
               } else if ((velocity_number + (velocity_sensitivity)) == 127) {
					velocity_number = 127;
               } else if ((velocity_number + (velocity_sensitivity)) >127){
					velocity_number = 127;
               }
		
    } else if (keycode == 0xC437){
		 snprintf(name, sizeof(name), "VELOCITY DOWN");
			if (velocity_number == 127) {
                    velocity_number -= (velocity_sensitivity);
                } else if ((velocity_number - (velocity_sensitivity)) > 0) {
                    velocity_number -= (velocity_sensitivity);
                } else if ((velocity_number - (velocity_sensitivity)) == 0) {
					velocity_number = 0;
                } else if ((velocity_number - (velocity_sensitivity)) < 0){
					velocity_number = 0;
                }
				
	} else if (keycode == 0xC74A){
		 snprintf(name, sizeof(name), "KS VELOCITY UP");
			if (velocity_number2 == 0) {
                    velocity_number2 += (velocity_sensitivity);
               } else if ((velocity_number2 + (velocity_sensitivity)) <127) {
                    velocity_number2 += (velocity_sensitivity);
               } else if ((velocity_number2 + (velocity_sensitivity)) == 127) {
					velocity_number2 = 127;
               } else if ((velocity_number2 + (velocity_sensitivity)) >127){
					velocity_number2 = 127;
               }
		
    } else if (keycode == 0xC74B){
		 snprintf(name, sizeof(name), "KS VELOCITY DOWN");
			if (velocity_number2 == 127) {
                    velocity_number2 -= (velocity_sensitivity);
                } else if ((velocity_number2 - (velocity_sensitivity)) > 0) {
                    velocity_number2 -= (velocity_sensitivity);
                } else if ((velocity_number2 - (velocity_sensitivity)) == 0) {
					velocity_number2 = 0;
                } else if ((velocity_number2 - (velocity_sensitivity)) < 0){
					velocity_number2 = 0;
                }
				
	} else if (keycode == 0xC7FA){
		 snprintf(name, sizeof(name), "TS VELOCITY UP");
			if (velocity_number3 == 0) {
                    velocity_number3 += (velocity_sensitivity);
               } else if ((velocity_number3 + (velocity_sensitivity)) <127) {
                    velocity_number3 += (velocity_sensitivity);
               } else if ((velocity_number3 + (velocity_sensitivity)) == 127) {
					velocity_number3 = 127;
               } else if ((velocity_number3 + (velocity_sensitivity)) >127){
					velocity_number3 = 127;
               }
		
    } else if (keycode == 0xC7FB){
		 snprintf(name, sizeof(name), "TS VELOCITY DOWN");
			if (velocity_number3 == 127) {
                    velocity_number3 -= (velocity_sensitivity);
                } else if ((velocity_number3 - (velocity_sensitivity)) > 0) {
                    velocity_number3 -= (velocity_sensitivity);
                } else if ((velocity_number3 - (velocity_sensitivity)) == 0) {
					velocity_number3 = 0;
                } else if ((velocity_number3 - (velocity_sensitivity)) < 0){
					velocity_number3 = 0;
                }

		
    } else if (keycode == 29013) {
	snprintf(name, sizeof(name), "OCTAVE DOWN");
	octave_number-=12;
	
	} else if (keycode == 29014) {
	snprintf(name, sizeof(name), "OCTAVE UP");
	octave_number+=12;
	
	} else if (keycode == 0xC74F) {
	snprintf(name, sizeof(name), "KS OCTAVE DOWN");
	octave_number2-=12;
	
	} else if (keycode == 0xC74E) {
	snprintf(name, sizeof(name), "KS OCTAVE UP");
	octave_number2+=12;
	
	} else if (keycode == 0xC7FF) {
	snprintf(name, sizeof(name), "TS OCTAVE DOWN");
	octave_number3-=12;
	
	} else if (keycode == 0xC7FE) {
	snprintf(name, sizeof(name), "TS OCTAVE UP");
	octave_number3+=12;
		
    } else if (keycode >= 33152 && keycode <= 49535) {
        // Calculate CC number and index within the CC
        int cc_number = (keycode - 33152) / 128;
        int cc_index = (keycode - 33152) % 128;

        // Update the name string with new line
        snprintf(name, sizeof(name), "CC%-3d  %d", cc_number, cc_index);
	}
	
	else if (keycode > 0) {
        snprintf(name, sizeof(name), " ");
	}
    // Handle CC UP and CC SENSITIVITY keys
    if (keycode >= 32896 && keycode <= 33023) {
        int cc_number = (keycode - 32896);  // Calculate CC# based on keycode

        // Check if it's a CC# UP key
        if (keycode >= 32896 && keycode <= 33023) {
            cc_updown_value[cc_number] += cc_sensitivity;  // Increase CC UP (value 2) based on sensitivity
        }

        // Ensure CC UP (value 2) stays within the valid range (0-127)
        if (cc_updown_value[cc_number] < 0) {
            cc_updown_value[cc_number] = 0;
        } else if (cc_updown_value[cc_number] > 127) {
            cc_updown_value[cc_number] = 127;
        }

        // Update the name string
        snprintf(name, sizeof(name), "CC%-3d  %d", cc_number, cc_up_value1[cc_number] + cc_updown_value[cc_number]);
    }
	// Handle CC DOWN keys
	if (keycode >= 33024 && keycode <= 33151) {
    int cc_number = (keycode - 33024);  // Calculate CC# based on keycode

    // Check if it's a CC DOWN key
    if (keycode >= 33024 && keycode <= 33151) {
        cc_updown_value[cc_number] -= cc_sensitivity;  // Decrease CC DOWN (value 2) based on sensitivity
    }

    // Ensure CC DOWN (value 2) stays within the valid range (0-127)
    if (cc_updown_value[cc_number] < 0) {
        cc_updown_value[cc_number] = 0;
    } else if (cc_updown_value[cc_number] > 127) {
        cc_updown_value[cc_number] = 127;
    }
	

    // Update the name string
    snprintf(name, sizeof(name), "CC%-3d  %d", cc_number, cc_down_value1[cc_number] + cc_updown_value[cc_number]);
}

    // Update keylog
    //snprintf(keylog_str, sizeof(keylog_str), "%-21s", name);
	
	int nlength = strlen(name);
	int tpadding = 21 - nlength;
	int lpadding = tpadding / 2;
	int rpadding = tpadding - lpadding;  // To ensure it fits exactly in 21 characters

snprintf(keylog_str, sizeof(keylog_str), "%*s", lpadding, "");

snprintf(keylog_str + strlen(keylog_str), sizeof(keylog_str) - strlen(keylog_str), "%s", name);

snprintf(keylog_str + strlen(keylog_str), sizeof(keylog_str) - strlen(keylog_str), "%*s", rpadding, "");

}


void oled_render_keylog(void) {
	char name[124];
	int total_length = strlen(getRootName()) + strlen(getChordName()) + strlen(getBassName());
	int total_padding = 22 - total_length;
	int left_padding = total_padding / 2;
	int right_padding = total_padding - left_padding;
	snprintf(name, sizeof(name), "\n  TRANSPOSITION %+3d", transpose_number + octave_number);
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n     VELOCITY %3d", velocity_number);
	if (keysplitstatus == 1) {snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n CH %2d // CH %2d\n---------------------", (channel_number + 1), (keysplitchannel + 1));
	}else if (keysplitstatus == 2) {snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n   CH %2d//CH %2d//CH %2d\n---------------------", (channel_number + 1), (keysplitchannel + 1), (keysplit2channel + 1));
	}else { snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n   MIDI CHANNEL %2d\n---------------------", (channel_number + 1)); //
	}
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "%*s", left_padding, "");
	// Append the RootName, ChordName, and BassName
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "%s%s%s", getRootName(), getChordName(), getBassName());
	// Add right padding and the ending characters
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "%*s", right_padding, "");
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "- - - - - - - - - -\n");
	
	//snprintf(name + strlen(name), sizeof(name) - strlen(name), "     %s%s%s\n---------------------\n     ", getRootName(), getChordName(), getBassName());
    oled_write(name, false);
    oled_write(keylog_str, false);

}


bool process_record_user(uint16_t keycode, keyrecord_t *record) {
	  /* KEYBOARD PET STATUS START */
 //switch (keycode) {
  //      case KC_LCTL:
  //      case KC_RCTL:
  //          if (record->event.pressed) {
  //              isSneaking = true;
  //          } else {
  //              isSneaking = false;
  //          }
  //          break;
//        case KC_SPC:
//            if (record->event.pressed) {
//                isJumping  = true;
//                showedJump = false;
//            } else {
 //               isJumping = false;
 //           }
 //           break;
 //}
            /* KEYBOARD PET STATUS END */
			
int led_indices[][6] = {
    {0, 63, 44, 37, 18, 12},  // ck index 0
    {1, 64, 45, 38, 19, 13},  // ck index 1
    {2, 65, 46, 39, 20, 99},  // ck index 2
    {3, 66, 47, 28, 40, 21},  // ck index 3
    {4, 67, 48, 29, 41, 22},  // ck index 4
    {5, 56, 68, 49, 30, 23},  // ck index 5
    {6, 57, 69, 50, 31, 24},  // ck index 6
    {7, 58, 51, 32, 25, 99},  // ck index 7
    {8, 59, 52, 33, 26, 14},  // ck index 8
    {9, 60, 53, 34, 27, 15},  // ck index 9
    {10, 61, 42, 54, 35, 16},  // ck index 10
    {11, 62, 43, 55, 36, 17}   // ck index 11
};




if ((keycode >= 28931 && keycode <= 29002) || (keycode >= 50688 && keycode <= 50759) || (keycode >= 50800 && keycode <= 50871)) {
		ck1 = keycode + transpositionplaceholder;
		uint8_t channel  = channel_number;
        uint8_t tone2     = keycode - keysplitnumber + ck2 + transpositionplaceholder;
		uint8_t tone3     = keycode - keysplitnumber + ck3 + transpositionplaceholder;
		uint8_t tone4     = keycode - keysplitnumber + ck4 + transpositionplaceholder;
		uint8_t tone5     = keycode - keysplitnumber + ck5 + transpositionplaceholder;
		uint8_t tone6     = keycode - keysplitnumber + ck6 + transpositionplaceholder;
		uint8_t tone7     = keycode - keysplitnumber + ck7 + transpositionplaceholder;
        uint8_t velocity = velocityplaceholder;
        uint16_t combined_keycode2 = keycode + ck2;
        uint16_t combined_keycode3 = keycode + ck3;
		uint16_t combined_keycode4 = keycode + ck4;
		uint16_t combined_keycode5 = keycode + ck5;
		uint16_t combined_keycode6 = keycode + ck6;
		uint16_t combined_keycode7 = keycode + ck7;
		uint8_t chordnote_2 = midi_compute_note(combined_keycode2);
		uint8_t chordnote_3 = midi_compute_note(combined_keycode3);
		uint8_t chordnote_4 = midi_compute_note(combined_keycode4);
		uint8_t chordnote_5 = midi_compute_note(combined_keycode5);
		uint8_t chordnote_6 = midi_compute_note(combined_keycode6);
		uint8_t chordnote_7 = midi_compute_note(combined_keycode7);

    if (record->event.pressed) {
		if (keycode >= 28931 && keycode <= 29002) { keysplitnumber = 28931; velocityplaceholder = velocity_number; transpositionplaceholder = (transpose_number + octave_number);}
			else if (keycode >= 50688 && keycode <= 50759) {keysplitnumber = 50688; if (keysplitvelocitystatus != 0) {velocityplaceholder = velocity_number2;} else {velocityplaceholder = velocity_number;
					}if (keysplittransposestatus != 0) {transpositionplaceholder = (transpose_number2 + octave_number2);} else {transpositionplaceholder = (transpose_number + octave_number);}}
			else if (keycode >= 50800 && keycode <= 50871) {keysplitnumber = 50800; if (keysplitvelocitystatus != 2) {velocityplaceholder = velocity_number;} else {velocityplaceholder = velocity_number3;
					}if (keysplittransposestatus != 2) {transpositionplaceholder = (transpose_number + octave_number);} else {transpositionplaceholder = (transpose_number3 + octave_number3);}}
	} else {
		if (keycode >= 28931 && keycode <= 29002) { keysplitnumber = 28931; velocityplaceholder = velocity_number; transpositionplaceholder = (transpose_number + octave_number);}
			else if (keycode >= 50688 && keycode <= 50759) {keysplitnumber = 50688; if (keysplitvelocitystatus != 0) {velocityplaceholder = velocity_number2;} else {velocityplaceholder = velocity_number;
					}if (keysplittransposestatus != 0) {transpositionplaceholder = (transpose_number2 + octave_number2);} else {transpositionplaceholder = (transpose_number + octave_number);}}
			else if (keycode >= 50800 && keycode <= 50871) {keysplitnumber = 50800; if (keysplitvelocitystatus != 2) {velocityplaceholder = velocity_number;} else {velocityplaceholder = velocity_number3;
					}if (keysplittransposestatus != 2) {transpositionplaceholder = (transpose_number + octave_number);} else {transpositionplaceholder = (transpose_number3 + octave_number3);}}
		if (scstatus == 0) {
		if (smartck2 != 0) {
        midi_send_noteoff(&midi_device, channel, smartck2, velocity);
        smartck2 = 0;
		}
		if (smartck3 != 0) {
        midi_send_noteoff(&midi_device, channel, smartck3, velocity);
        smartck3 = 0;
		}
		if (smartck4 != 0) {
        midi_send_noteoff(&midi_device, channel, smartck4, velocity);
        smartck4 = 0;
		}
		if (smartck5 != 0) {
        midi_send_noteoff(&midi_device, channel, smartck5, velocity);
        smartck5 = 0;
		}
		if (smartck6 != 0) {
        midi_send_noteoff(&midi_device, channel, smartck6, velocity);
        smartck6 = 0;
		}
		if (smartck7 != 0) {
        midi_send_noteoff(&midi_device, channel, smartck7, velocity);
        smartck7 = 0;
		}
	}
}
	if (ck2 != 0) { // Handles up to 7-note smart chords
    if (record->event.pressed) {
        // Send MIDI noteon for each chord key if present
        midi_send_noteon(&midi_device, channel, chordnote_2, velocity);
        tone2_status[1][tone2] += 1;

        if (ck3 != 0) {
            midi_send_noteon(&midi_device, channel, chordnote_3, velocity);
            tone3_status[1][tone3] += 1;
        }
        if (ck4 != 0) {
            midi_send_noteon(&midi_device, channel, chordnote_4, velocity);
            tone4_status[1][tone4] += 1;
        }
        if (ck5 != 0) {
            midi_send_noteon(&midi_device, channel, chordnote_5, velocity);
            tone5_status[1][tone5] += 1;
        }
        if (ck6 != 0) {
            midi_send_noteon(&midi_device, channel, chordnote_6, velocity);
            tone6_status[1][tone6] += 1;
        }
        if (ck7 != 0) {
            midi_send_noteon(&midi_device, channel, chordnote_7, velocity);
            tone7_status[1][tone7] += 1;
        }

        // Set smart chord keys and calculate held key values
        smartck2 = combined_keycode2 + transpositionplaceholder + 21;
        hk1 = keycode - keysplitnumber + 24 + transpositionplaceholder;
        hk1 = ((hk1 % 12) + 12) % 12 + 1;
        hk1d = (hk1 - 1) % 12;
				hk2 = keycode - keysplitnumber + 24 + transpositionplaceholder + ck2;
		hk2 = ((hk2) % 12 + 12) % 12 + 1;
		hk2d = hk2 - hk1 + 1;
		if (hk2d < 1) {
                    hk2d += 12;
                }

        for (int i = 2; i <= 7; i++) {
            if (i == 3 && ck3 != 0) {
                smartck3 = combined_keycode3 + transpositionplaceholder + 21;
                hk3 = keycode - keysplitnumber + 24 + transpositionplaceholder + ck3;
                hk3 = ((hk3 % 12) + 12) % 12 + 1;
                hk3d = hk3 - hk1 + 1;
                if (hk3d < 1) {
                    hk3d += 12;
                }
            }
            if (i == 4 && ck4 != 0) {
                smartck4 = combined_keycode4 + transpositionplaceholder + 21;
                hk4 = keycode - keysplitnumber + 24 + transpositionplaceholder + ck4;
                hk4 = ((hk4 % 12) + 12) % 12 + 1;
                hk4d = hk4 - hk1 + 1;
                if (hk4d < 1) {
                    hk4d += 12;
                }
            }
            if (i == 5 && ck5 != 0) {
                smartck5 = combined_keycode5 + transpositionplaceholder + 21;
                hk5 = keycode - keysplitnumber + 24 + transpositionplaceholder + ck5;
                hk5 = ((hk5 % 12) + 12) % 12 + 1;
                hk5d = hk5 - hk1 + 1;
                if (hk5d < 1) {
                    hk5d += 12;
                }
            }
            if (i == 6 && ck6 != 0) {
                smartck6 = combined_keycode6 + transpositionplaceholder + 21;
                hk6 = keycode - keysplitnumber + 24 + transpositionplaceholder + ck6;
                hk6 = ((hk6 % 12) + 12) % 12 + 1;
                hk6d = hk6 - hk1 + 1;
                if (hk6d < 1) {
                    hk6d += 12;
                }
            }
            if (i == 7 && ck7 != 0) {
                smartck7 = combined_keycode7 + transpositionplaceholder + 21;
                hk7 = keycode - keysplitnumber + 24 + transpositionplaceholder + ck7;
                hk7 = ((hk7 % 12) + 12) % 12 + 1;
                hk7d = hk7 - hk1 + 1;
                if (hk7d < 1) {
                    hk7d += 12;
                }
            }
        }

        // Set initial tone status if necessary
        if (tone2_status[0][tone2] == MIDI_INVALID_NOTE) {
            tone2_status[0][tone2] = chordnote_2;
        }

    } else { // On key release
        midi_send_noteoff(&midi_device, channel, combined_keycode2 + transpositionplaceholder + 21, velocity);
        tone2_status[1][tone2] -= 1;
        tone2_status[0][tone2] = MIDI_INVALID_NOTE;

        for (int i = 3; i <= 7; i++) {
            if (i == 3 && ck3 != 0) {
                midi_send_noteoff(&midi_device, channel, combined_keycode3 + transpositionplaceholder + 21, velocity);
                tone3_status[1][tone3] -= 1;
                tone3_status[0][tone3] = MIDI_INVALID_NOTE;
            }
            if (i == 4 && ck4 != 0) {
                midi_send_noteoff(&midi_device, channel, combined_keycode4 + transpositionplaceholder + 21, velocity);
                tone4_status[1][tone4] -= 1;
                tone4_status[0][tone4] = MIDI_INVALID_NOTE;
            }
            if (i == 5 && ck5 != 0) {
                midi_send_noteoff(&midi_device, channel, combined_keycode5 + transpositionplaceholder + 21, velocity);
                tone5_status[1][tone5] -= 1;
                tone5_status[0][tone5] = MIDI_INVALID_NOTE;
            }
            if (i == 6 && ck6 != 0) {
                midi_send_noteoff(&midi_device, channel, combined_keycode6 + transpositionplaceholder + 21, velocity);
                tone6_status[1][tone6] -= 1;
                tone6_status[0][tone6] = MIDI_INVALID_NOTE;
            }
            if (i == 7 && ck7 != 0) {
                midi_send_noteoff(&midi_device, channel, combined_keycode7 + transpositionplaceholder + 21, velocity);
                tone7_status[1][tone7] -= 1;
                tone7_status[0][tone7] = MIDI_INVALID_NOTE;
            }
        }

        // Reset variables
        smartck2 = 0;
        smartck3 = 0;
        smartck4 = 0;
        smartck5 = 0;
        smartck6 = 0;
        smartck7 = 0;
        hk1 = 0;
        hk1 = 0;
        hk1d = 0;
        hk2 = 0;
        hk2 = 0;
        hk2d = 0;
        hk3 = 0;
        hk3 = 0;
        hk3d = 0;
        hk4 = 0;
        hk4 = 0;
        hk4d = 0;
        hk5 = 0;
        hk5 = 0;
        hk5d = 0;
        hk6 = 0;
        hk6 = 0;
        hk6d = 0;
        hk7 = 0;
        hk7 = 0;
        hk7d = 0;
    }
}
}




if (keycode >= 0xC420 && keycode <= 0xC428) {
	 if (record->event.pressed) {
        //scstatus = 1;   trying without it to see if it is obselete
		 switch (keycode) {
		case 0xC420: inversionposition = 0;
		break;
		case 0xC421: inversionposition = 1;
		break;
		case 0xC422: inversionposition = 2;
		break;
		case 0xC423: inversionposition = 3;
		break;
		case 0xC424: inversionposition = 4;
		break;
		case 0xC425: inversionposition = 5;
		break;
		 }
	 }
}

	
if ((keycode >= 28931 && keycode <= 29002) || (keycode >= 50688 && keycode <= 50759) || (keycode >= 50800 && keycode <= 50871)) {

        if (record->event.pressed) {

            // Ensure the ck2 keycode is within range
            if (scstatus != 0) { 
				if (sclightmode <=2) {
				 ck1_led_index = keycode_to_led_index[keycode - keysplitnumber]; 
				 if ((ck1_led_index <= 5) || (ck1_led_index >= 14 && ck1_led_index <= 20)) {ck1_led_index2 = ck1_led_index + 35;}	  
				 ck2_led_index = keycode_to_led_index[keycode + ck2 - keysplitnumber];
				 if ((ck2_led_index <= 5) || (ck2_led_index >= 14 && ck2_led_index <= 20)) {ck2_led_index2 = ck2_led_index + 35;}	 	 
				 ck3_led_index = keycode_to_led_index[keycode + ck3 - keysplitnumber]; 
				 if ((ck3_led_index <= 5) || (ck3_led_index >= 14 && ck3_led_index <= 20)) {ck3_led_index2 = ck3_led_index + 35;}	           
				if (ck4 != 0) {
				 ck4_led_index = keycode_to_led_index[keycode + ck4 - keysplitnumber]; 
                if ((ck4_led_index <= 5) || (ck4_led_index >= 14 && ck4_led_index <= 20)) {ck4_led_index2 = ck4_led_index + 35;}	  
				}
				if (ck5 != 0) {
				ck5_led_index = keycode_to_led_index[keycode + ck5 - keysplitnumber]; 
                if ((ck5_led_index <= 5) || (ck5_led_index >= 14 && ck5_led_index <= 20)) {ck5_led_index2 = ck5_led_index + 35;}	 
				}
				if (ck6 != 0) {
				ck6_led_index = keycode_to_led_index[keycode + ck6 - keysplitnumber]; 
                if ((ck6_led_index <= 5) || (ck6_led_index >= 14 && ck6_led_index <= 20)) {ck6_led_index2 = ck6_led_index + 35;}	 
				}
				if (ck7 != 0) {
				ck7_led_index = keycode_to_led_index[keycode + ck7 - keysplitnumber]; 
                if ((ck7_led_index <= 5) || (ck7_led_index >= 14 && ck7_led_index <= 20)) {ck7_led_index2 = ck7_led_index + 35;}	 
				}
				}	

else if (sclightmode >= 2) {
	int cks[7] = {0, ck2, ck3, ck4, ck5, ck6, ck7};
    int ck_led_indices[7][6];  // Declare the array at the beginning of the function

    // Your existing logic for populating the array
    for (int i = 1; i <= 7; i++) {
        int ck_led_index = keycode_to_led_index[keycode + cks[i - 1] - keysplitnumber];
        if (ck_led_index >= 0 && ck_led_index < 12) {
            for (int j = 0; j < 6; j++) {
                // Assign LED indices from `led_indices` to `ck_led_indices`
                ck_led_indices[i - 1][j] = led_indices[ck_led_index][j];
            }
        }
    }

    // Assign the values from the 2D array to the ck LED index variables
    ck1_led_index = ck_led_indices[0][0];
    ck1_led_index2 = ck_led_indices[0][1];
    ck1_led_index3 = ck_led_indices[0][2];
    ck1_led_index4 = ck_led_indices[0][3];
    ck1_led_index5 = ck_led_indices[0][4];
	ck1_led_index6 = ck_led_indices[0][5];
	

    ck2_led_index = ck_led_indices[1][0];
    ck2_led_index2 = ck_led_indices[1][1];
    ck2_led_index3 = ck_led_indices[1][2];
    ck2_led_index4 = ck_led_indices[1][3];
    ck2_led_index5 = ck_led_indices[1][4];
	ck2_led_index6 = ck_led_indices[1][5];

    ck3_led_index = ck_led_indices[2][0];
    ck3_led_index2 = ck_led_indices[2][1];
    ck3_led_index3 = ck_led_indices[2][2];
    ck3_led_index4 = ck_led_indices[2][3];
    ck3_led_index5 = ck_led_indices[2][4];
	ck3_led_index6 = ck_led_indices[2][5];

    ck4_led_index = ck_led_indices[3][0];
    ck4_led_index2 = ck_led_indices[3][1];
    ck4_led_index3 = ck_led_indices[3][2];
    ck4_led_index4 = ck_led_indices[3][3];
    ck4_led_index5 = ck_led_indices[3][4];
	ck4_led_index6 = ck_led_indices[3][5];

    ck5_led_index = ck_led_indices[4][0];
    ck5_led_index2 = ck_led_indices[4][1];
    ck5_led_index3 = ck_led_indices[4][2];
    ck5_led_index4 = ck_led_indices[4][3];
    ck5_led_index5 = ck_led_indices[4][4];
	ck5_led_index6 = ck_led_indices[4][5];

    ck6_led_index = ck_led_indices[5][0];
    ck6_led_index2 = ck_led_indices[5][1];
    ck6_led_index3 = ck_led_indices[5][2];
    ck6_led_index4 = ck_led_indices[5][3];
    ck6_led_index5 = ck_led_indices[5][4];
	ck6_led_index6 = ck_led_indices[5][5];
	
    ck7_led_index = ck_led_indices[6][0];
    ck7_led_index2 = ck_led_indices[6][1];
    ck7_led_index3 = ck_led_indices[6][2];
    ck7_led_index4 = ck_led_indices[6][3];
    ck7_led_index5 = ck_led_indices[6][4];
	ck7_led_index6 = ck_led_indices[6][5];
}



            }
        
			
            if (hk1 == 0 && hk2 == 0 && hk3 == 0 && hk4 == 0 && hk5 == 0) {
                hk1 = keycode - keysplitnumber + 24 + transpositionplaceholder;
				hk1 = ((hk1) % 12 + 12) % 12 + 1;
				hk1d = (hk1 - 1) % 12;
				if (hk1 == hk2 || hk1 == hk3 || hk1 == hk4 || hk1 == hk5 || hk1 == hk6) {
				hk2 = 0;
				hk2 = 0;
				hk2d = 0;
				}
            } else if (hk1 != 0 && hk1 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk2 == 0 && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
                hk2 = keycode - keysplitnumber + 24 + transpositionplaceholder;
				hk2 = ((hk2) % 12 + 12) % 12 + 1;
				    hk2d = hk2 - hk1 + 1;
    if (hk2d < 1) {
        hk2d += 12;
    }
    else {}

				if (hk2 == hk1 || hk2 == hk3 || hk2 == hk4 || hk2 == hk5 || hk2 == hk6) {
				hk2 = 0;
				hk2 = 0;
				hk2d = 0;
				}
            } else if (hk1 != 0 && hk1 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk2 != 0 && hk2 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk3 == 0 && hk4 == 0 && hk5 == 0 && hk6 == 0) {
                hk3 = keycode - keysplitnumber + 24 + transpositionplaceholder;
				hk3 = ((hk3) % 12 + 12) % 12 + 1;
				    hk3d = hk3 - hk1 + 1;
    if (hk3d < 1) {
        hk3d += 12;
    }
    else {}

				if (hk3 == hk1 || hk3 == hk2 || hk3 == hk4 || hk3 == hk5 || hk3 == hk6) {
				hk3 = 0;
				hk3 = 0;
				hk3d = 0;
				}
            } else if (hk1 != 0 && hk1 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk2 != 0 && hk2 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk3 != 0 && hk3 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk4 == 0 && hk5 == 0 && hk6 == 0) {
                hk4 = keycode - keysplitnumber + 24 + transpositionplaceholder;
				hk4 = ((hk4) % 12 + 12) % 12 + 1;
				    hk4d = hk4 - hk1 + 1;
    if (hk4d < 1) {
        hk4d += 12;
    }
    else {}

				if (hk4 == hk1 || hk4 == hk2 || hk4 == hk3 || hk4 == hk5 || hk4 == hk6) {
				hk4 = 0;
				hk4 = 0;
				hk4d = 0;
				}
            } else if (hk1 != 0 && hk1 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk2 != 0 && hk2 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk3 != 0 && hk3 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk4 != 0 && hk4 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk5 == 0 && hk6 == 0) {
                hk5 = keycode - keysplitnumber + 24 + transpositionplaceholder;
				hk5 = ((hk5) % 12 + 12) % 12 + 1;
				    hk5d = hk5 - hk1 + 1;
    if (hk5d < 1) {
        hk5d += 12;
    }
    else {}

				if (hk5 == hk1 || hk5 == hk2 || hk5 == hk3 || hk5 == hk4 || hk5 == hk6) {
				hk5 = 0;
				hk5 = 0;
				hk5d = 0;
				}
            } else if (hk1 != 0 && hk1 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk2 != 0 && hk2 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk3 != 0 && hk3 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk4 != 0 && hk4 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk5 != 0 && hk5 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk6 == 0) {
                hk6 = keycode - keysplitnumber + 24 + transpositionplaceholder;
				hk6 = ((hk6) % 12 + 12) % 12 + 1;
				    hk6d = hk6 - hk1 + 1;
    if (hk6d < 1) {
        hk6d += 12;
    }
	else {}

				if (hk6 == hk1 || hk6 == hk2 || hk6 == hk3 || hk6 == hk4 || hk6 == hk5 || hk6 == hk7) {
				hk6 = 0;
				hk6 = 0;
				hk6d = 0;
				}
            } else if (hk1 != 0 && hk1 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk2 != 0 && hk2 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk3 != 0 && hk3 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk4 != 0 && hk4 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk5 != 0 && hk5 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk6 != (keycode - keysplitnumber + 24 + transpositionplaceholder) && hk7 == 0) {
                hk7 = keycode - keysplitnumber + 24 + transpositionplaceholder;
				hk7 = ((hk7) % 12 + 12) % 12 + 1;
				    hk7d = hk7 - hk1 + 1;
    if (hk7d < 1) {
        hk7d += 12;
    }
	
    else {}

				if (hk7 == hk1 || hk7 == hk2 || hk7 == hk3 || hk7 == hk4 || hk7 == hk5 || hk7 == hk6) {
				hk7 = 0;
				hk7 = 0;
				hk7d = 0;
				}
            }
			
				
} else {
    ck1 = 0;
	ck1_led_index = 99;
	ck2_led_index = 99;
	ck3_led_index = 99;
	ck4_led_index = 99;
	ck5_led_index = 99;
	ck6_led_index = 99;
	ck7_led_index = 99;
	ck1_led_index2 = 99;
	ck2_led_index2 = 99;
	ck3_led_index2 = 99;
	ck4_led_index2 = 99;
	ck5_led_index2 = 99;
	ck6_led_index2 = 99;
	ck7_led_index2 = 99;
	ck1_led_index3 = 99;
	ck2_led_index3 = 99;
	ck3_led_index3 = 99;
	ck4_led_index3 = 99;
	ck5_led_index3 = 99;
	ck6_led_index3 = 99;
	ck7_led_index3 = 99;
    ck1_led_index4 = 99;
   ck2_led_index4 = 99;
   ck3_led_index4 = 99;
   ck4_led_index4 = 99;
   ck5_led_index4 = 99;
   ck6_led_index4 = 99;
   ck7_led_index4 = 99;
   ck1_led_index5 = 99;
   ck2_led_index5 = 99;
   ck3_led_index5 = 99;
   ck4_led_index5 = 99;
   ck5_led_index5 = 99;
   ck6_led_index5 = 99;
   ck7_led_index5 = 99;
   ck1_led_index6 = 99;
   ck2_led_index6 = 99;
   ck3_led_index6 = 99;
   ck4_led_index6 = 99;
   ck5_led_index6 = 99;
   ck6_led_index6 = 99;
   ck7_led_index6 = 99;


    if (hk1 == (keycode - keysplitnumber + 24 + transpositionplaceholder)) {
        if (hk2 != 0) {
            hk1 = hk2;
			hk1 = hk2;
			hk1d = (hk1 - 1) % 12;
            
		
        if (hk3 != 0) {
            hk2 = hk3;
			hk2d =  hk2 - hk1 + 1; if (hk2d < 1) {hk2d += 12;}
			hk2 = hk3;
				}	else {  hk2 = 0;
							hk2d = 0;		
							hk2 = 0; }
			
		if (hk4 != 0) {
            hk3 = hk4;
			hk3d = hk3 - hk1 + 1; if (hk3d < 1) {hk3d += 12;}
			hk3 = hk4;
				}	else {  hk3 = 0;
							hk3d = 0;		
							hk3 = 0; }
			
		if (hk5 != 0) {
            hk4 = hk5;
			hk4d = hk4 - hk1 + 1;  if (hk4d < 1) {hk4d += 12;}         
			hk4 = hk5;
				}	else {  hk4 = 0;
							hk4d = 0;		
							hk4 = 0; }
		
		if (hk6 != 0) {
            hk5 = hk6;
			hk5d = hk5 - hk1 + 1;  if (hk5d < 1) {hk5d += 12;}        
			hk5 = hk6;
				}	else {  hk5 = 0;
							hk5d = 0;		
							hk5 = 0; }
		if (hk7 != 0) {
            hk6 = hk7;
			hk6d = hk6 - hk1 + 1;  if (hk6d < 1) {hk6d += 12;}          
			hk6 = hk7;
			hk7 = 0;
			hk7d = 0;
			hk7 = 0;
				}	else {  hk6 = 0;
							hk6d = 0;		
							hk6 = 0; }			
		}
        
				
		
		else {
            hk1 = 0;
			hk1d = 0;
			hk1 = 0;
			rootnote = 13;
			bassnote = 13;
        }
    } else if (hk2 == (keycode - keysplitnumber + 24 + transpositionplaceholder)) {
        if (hk3 != 0) {
            hk2 = hk3;
			hk2d = hk3d;
			hk2 = hk3;
			
		if (hk4 != 0) {
            hk3 = hk4;
			hk3d = hk4d;
			hk3 = hk4;
			}		else {  hk3 = 0;
							hk3d = 0;		
							hk3 = 0; }
			
		if (hk5 != 0) {
            hk4 = hk5;
			hk4d = hk5d;           
			hk4 = hk5;
			}		else {  hk4 = 0;
							hk4d = 0;		
							hk4 = 0; }
		
		if (hk6 != 0) {
            hk5 = hk6;
			hk5d = hk6d;           
			hk5 = hk6;
			}		else {  hk5 = 0;
							hk5d = 0;		
							hk5 = 0; }
		if (hk7 != 0) {
            hk6 = hk7;
			hk6d = hk7d;           
			hk6 = hk7;
			hk7 = 0;
			hk7d = 0;
			hk7 = 0;
			}		else {  hk6 = 0;
							hk6d = 0;		
							hk6 = 0; }
		}								
		 else {
            hk2 = 0;
			hk2d = 0;
			hk2 = 0;
        }
    } else if (hk3 == (keycode - keysplitnumber + 24 + transpositionplaceholder)) {
        if (hk4 != 0) {
            hk3 = hk4;
			hk3d = hk4d;
			hk3 = hk4;
			
		if (hk5 != 0) {
            hk4 = hk5;
			hk4d = hk5d;           
			hk4 = hk5;
		}		else {  hk4 = 0;
							hk4d = 0;		
							hk4 = 0; }
		
		if (hk6 != 0) {
            hk5 = hk6;
			hk5d = hk6d;           
			hk5 = hk6;
		}		else {  hk5 = 0;
							hk5d = 0;		
							hk5 = 0; }
		if (hk7 != 0) {
            hk6 = hk7;
			hk6d = hk7d;           
			hk6 = hk7;
			hk7 = 0;
			hk7d = 0;
			hk7 = 0;
		}		else {  hk6 = 0;
							hk6d = 0;		
							hk6 = 0; }						
		}		
        else {
            hk3 = 0;
			hk3d = 0;
			hk3 = 0;
        }
    } else if (hk4 == (keycode - keysplitnumber + 24 + transpositionplaceholder)) {
        if (hk5 != 0) {
            hk4 = hk5;
			hk4d = hk5d;           
			hk4 = hk5;
		
		if (hk6 != 0) {
            hk5 = hk6;
			hk5d = hk6d;           
			hk5 = hk6;
		}		else {  hk5 = 0;
							hk5d = 0;		
							hk5 = 0; }
		if (hk7 != 0) {
            hk6 = hk7;
			hk6d = hk7d;           
			hk6 = hk7;
			hk7 = 0;
			hk7d = 0;
			hk7 = 0;
		}		else {  hk6 = 0;
							hk6d = 0;		
							hk6 = 0; }				
		}
         else {
            hk4 = 0;
			hk4d = 0;
			hk4 = 0;
        }
    } else if (hk5 == (keycode - keysplitnumber + 24 + transpositionplaceholder)) {
        if (hk6 != 0) {
            hk5 = hk6;
			hk5d = hk6d;           
			hk5 = hk6;

		if (hk7 != 0) {
            hk6 = hk7;
			hk6d = hk7d;           
			hk6 = hk7;
			hk7 = 0;
			hk7d = 0;
			hk7 = 0;
		}		else {hk6 = 0;
						hk6d = 0;		
						hk6 = 0; }
		
		}
         else {
            hk5 = 0;
			hk5d = 0;
			hk5 = 0;
        }
		
	} else if (hk6 == (keycode - keysplitnumber + 24 + transpositionplaceholder)) {
    if (hk7 != 0) {
        hk6 = hk7;
        hk6d = hk7d;           
        hk6 = hk7;
		hk7 = 0;
		hk7d = 0;
		hk7 = 0;
		} else {
			hk6 = 0;
			hk6d = 0;		
			hk6 = 0;
		}
	} else if (hk7 == (keycode - keysplitnumber + 24 + transpositionplaceholder)) {
        hk7 = 0;
		hk7d = 0;
		hk7 = 0;
    }
}
}

if (keycode == 0xC4A0) {
	if (record->event.pressed) {
		scchanger-=1;
		if (sclight != 3) {sclight = 1;}
	}
		if (scchanger < 0) {
            scchanger = 0;
        } else if (scchanger > 53) {
            scchanger = 53;
		}
		keycode = 0xC3FA - 100 + scchanger;
		//snprintf(name, sizeof(name),"Previous QuickChord");
}		
		
if (keycode == 0xC4A1) {
	if (record->event.pressed) {
		scchanger+=1;
		if (sclight != 3) {sclight = 1;}
	}
		if (scchanger < 0) {
            scchanger = 0;
        } else if (scchanger > 53) {
            scchanger = 53;
		}
		keycode = 0xC3FA - 100 + scchanger;
		//snprintf(name, sizeof(name),"Next QuickChord");
}
	/////////////////////////////////////////// SMART CHORD///////////////////////////////////////////////////////////
if (keycode >= 0xC396 && keycode <= 0xC416) {
	 static uint8_t previous_rgb_mode = RGB_MATRIX_NONE;
	 if (keycode == 0xC3FA) {
    // Calculate the new keycode based on the provided formula
	 keycode = 0xC3FA - 100 + scchanger;}
	 
	 if (record->event.pressed) {
        scstatus = 1;
		if (sclight == 0) {
		previous_rgb_mode = rgb_matrix_get_mode();  // Store the current RGB mode
        rgb_matrix_mode(RGB_MATRIX_CUSTOM_sc_LIGHTS);}
		
		 switch (keycode) {
		case 0xC396:    // Major Chord
            ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 0;
			ck5 = 0;
break;
		case 0xC397:   // Minor Chord		
            ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 0;
			ck5 = 0;
 break;
		case 0xC398:   // Diminished
            ck2 = 3;   // Minor Third
			ck3 = 6;   // Diminished fifth
			ck4 = 0;
			ck5 = 0;
 break;
		case 0xC399:   // Augmented
            ck2 = 4;   // Major Third
			ck3 = 8;	// Augmented fifth
			ck4 = 0;
			ck5 = 0;
			
 break;
		case 0xC39A:   // Major b5
            ck2 = 4;   // Major Third
			ck3 = 6;	// Diminished fifth
			ck4 = 0;
			ck5 = 0;
			
 break;
		case 0xC39B:   // Sus2
            ck2 = 2;	 // Major Second
			ck3 = 7;   // Perfect Fifth
			ck4 = 0;
			ck5 = 0;
 break;
		case 0xC39C:    // Sus4
            ck2 = 5;   // Perfect fourth
			ck3 = 7;   // Perfect Fifth
			ck4 = 0;
			ck5 = 0;
 break;
		case 0xC39D:    // Maj6								
            ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 9;   // Major 6th
			ck5 = 0;
 break;
		 case 0xC39E:    // Min6
            ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 9;   // Major 6th
			ck5 = 0;
 break;
		case 0xC39F:    // Maj7											/////// INTERMEDIATE CHORDS ////////
            ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 11;
			ck5 = 0;
 break;
		case 0xC3A0:    // Min7
            ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;   // Minor Seventh
			ck5 = 0;
 break;
		case 0xC3A1:    // Dom7
            ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;   // Minor Seventh
			ck5 = 0;
break;
		case 0xC3A2:    // Diminished 7th (dim7)					
			ck2 = 3;   // Minor Third
			ck3 = 6;   // Diminished Fifth
			ck4 = 9;   // Diminished Seventh
			ck5 = 0;			
			
break;
		case 0xC3A3:    // Half-Diminished 7th (ø7) (m7b5)
			ck2 = 3;   // Minor Third
			ck3 = 6;   // Diminished Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 0;  
break;
		case 0xC3A4:    // Augmented 7th (7#5)
			ck2 = 4;   // Major Third
			ck3 = 8;   // Augmented Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 0;
break;
		case 0xC3A5:    // Major9 (maj9)
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 14;  // Major Ninth
break;
		case 0xC3A6:    // Minor 9 (min9)
			ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 14;  // Major Ninth 
break;
		case 0xC3A7:    // Dominant 9 (dom9)
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 14;  // Major Ninth 
break;			
		case 0xC3A8:    // Major add2 (majadd2)								//ADVANCED CHORDS
			ck2 = 2;   // Major Second
			ck3 = 4;   // Major Third
			ck4 = 7;   // Perfect Fifth
			ck5 = 0;   // No additional note
break;
		case 0xC3A9:    // Minor add2 (madd2)
			ck2 = 2;   // Major Second
			ck3 = 3;   // Minor Third
			ck4 = 7;   // Perfect Fifth
			ck5 = 0;   // No additional note
break;
		case 0xC3AA:    // Major add4 (majadd4)
			ck2 = 4;   // Major Third
			ck3 = 5;   // Perfect Fourth
			ck4 = 7;   // Perfect Fifth
			ck5 = 0;   // No additional note
break;
		case 0xC3AB:    // Minor add4 (madd4)
			ck2 = 3;   // Minor Third
			ck3 = 5;   // Perfect Fourth
			ck4 = 7;   // Perfect Fifth
			ck5 = 0;   // No additional note
break;		
		case 0xC3AC:    // Major 6/9
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 9;   // Major Sixth
			ck5 = 14;  // Major Ninth
			ck6 = 0;   // No additional note
break;
		case 0xC3AD:    // Minor 6/9
			ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 9;   // Major Sixth
			ck5 = 14;  // Major Ninth
			ck6 = 0;   // No additional note
break;				
		case 0xC3AE:    // Minor Major 7th (m(maj7))
			ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 0;   // No additional note
break;
		case 0xC3AF:    // Major 7sus4 (maj7sus4)
			ck2 = 5;   // Perfect fourth
			ck3 = 7;   // Perfect Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 0;   // No additional note
break;
		case 0xC3B0:    // Dominant 7sus4 (7sus4)
			ck2 = 5;   // Perfect fourth
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 0;   // No additional note
break;
		case 0xC3B1:    // Major 7sus2 (maj7sus2)
			ck2 = 2;   // Major Second
			ck3 = 7;   // Perfect Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 0;   // No additional note
break;
		case 0xC3B2:    // Dominant 7sus2 (7sus2)
			ck2 = 2;   // Major Second
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 0;   // No additional note
break;
		case 0xC3B3:    // Major 7th with Raised 5 (maj7#5)
			ck2 = 4;   // Major Third
			ck3 = 8;   // Augmented Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 0;   // No additional note
break;

		case 0xC3B4:    // Minor 7th with Raised 5 (m7#5)
			ck2 = 3;   // Minor Third
			ck3 = 8;   // Augmented Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 0;   // No additional note
break;

		case 0xC3B5:    // Major 7th with Lowered 5 (maj7b5)
			ck2 = 4;   // Major Third
			ck3 = 6;   // Diminished Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 0;   // No additional note
break;

		case 0xC3B6:    // Dominant 7th with Lowered 5 (7b5)
			ck2 = 4;   // Major Third
			ck3 = 6;   // Diminished Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 0;   // No additional note
break;
		case 0xC3B7:    // Major 7th with no 5 (7no5)
			ck2 = 4;   // Major Third
			ck3 = 11;  // Major Seventh
			ck4 = 0;   // No additional note
			ck5 = 0;   // No additional note
break;			
		case 0xC3B8:    // Minor 7th with no 5 (7no5)
			ck2 = 3;   // Minor Third
			ck3 = 10;  // Minor Seventh
			ck4 = 0;   // No additional note
			ck5 = 0;   // No additional note
break;			
		case 0xC3B9:    // Dominant 7th with no 5 (7no5)
			ck2 = 4;   // Minor Third
			ck3 = 10;  // Minor Seventh
			ck4 = 0;   // No additional note
			ck5 = 0;   // No additional note
break;	
		case 0xC3BA:    // Major add9 (add9)
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 14;  // Major Ninth
			ck5 = 0;   // No eleventh
			ck6 = 0;   // No thirteenth
break;
		case 0xC3BB:    // Minor add9 (madd9)
			ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 14;  // Major Ninth
			ck5 = 0;   // No eleventh
			ck6 = 0;   // No thirteenth
break;
		case 0xC3BC:    // Diminished 9 (dim9)
			ck2 = 3;   // Minor Third
			ck3 = 6;   // Diminished Fifth
			ck4 = 9;  // Diminished Seventh
			ck5 = 14;  // Major Ninth 
break;
		case 0xC3BD:    // Half-Diminished 9 (ø9)
			ck2 = 3;   // Minor Third
			ck3 = 6;   // Diminished Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 14;  // Major Ninth 
break;
		case 0xC3BE:    // Augmented 9th (9#5)
			ck2 = 4;   // Major Third
			ck3 = 8;   // Augmented Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 14;  // Major Ninth
break;
		case 0xC3BF:    // Major 11 (maj11)
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 14;  // Major Ninth 
			ck6 = 17;  // Perfect Eleventh
break;
		case 0xC3C0:    // Minor 11 (min11)
			ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 14;  // Major Ninth 
			ck6 = 17;  // Perfect Eleventh
break;
		case 0xC3C1:    // Dominant 11 (dom11)
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 14;  // Major Ninth 
			ck6 = 17;  // Perfect Eleventh
break;
		case 0xC3C2:    // Major add11 (add11))
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 17;  // Perfect Eleventh
			ck5 = 0;
			ck6 = 0;
break;
		case 0xC3C3:    // Minor add11 (madd11))
			ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 17;  // Perfect Eleventh
			ck5 = 0;
			ck6 = 0;
break;
		case 0xC3C4:    // Major 7th add11 (maj7(add11))
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 17;  // Perfect Eleventh
			ck6 = 0;
break;
		case 0xC3C5:    // Minor 7th add11 (m7(add11))
			ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 17;  // Perfect Eleventh
			ck6 = 0;
break;
		case 0xC3C6:    // Dominant 7th add11 (7(add11))
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 17;  // Perfect Eleventh
			ck6 = 0;
break;
		case 0xC3C7:    // Diminished 11 (dim11)
 		   ck2 = 3;   // Minor Third
			ck3 = 6;   // Diminished Fifth
			ck4 = 9;   // Diminished Seventh
			ck5 = 14;  // Major Ninth 
			ck6 = 17;  // Perfect Eleventh

break;
		case 0xC3C8:    // Half-Diminished 11 (ø11)
			ck2 = 3;   // Minor Third
			ck3 = 6;   // Diminished Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 14;  // Major Ninth 
			ck6 = 17;  // Perfect Eleventh
			
break;
		case 0xC3C9:    // Maj7#11 (Maj7#11)
			ck2 = 4;   // Major Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 11;  // Major Seventh
			ck5 = 18;  // Sharp Eleventh 
			
break;
		case 0xC3CA:    // Min7#11 (min7#11)
			ck2 = 3;   // Minor Third
			ck3 = 7;   // Perfect Fifth
			ck4 = 10;  // Minor Seventh
			ck5 = 18;  // Sharp Eleventh 
			
break;
		case 0xC3CB:    // 7#11 (7#11)
			ck2 = 4;   // Major Third			// 7#11 (7#11)
			ck3 = 7;   // Diminished Fifth		// 7#11 (7#11)
			ck4 = 10;  // Minor Seventh			// 7#11 (7#11)
			ck5 = 18;  // Sharp Eleventh 		// 7#11 (7#11)
			
break;																	//MODES AND SCALES
		case 0xC3FB:    // IONIAN (Major)		
			ck2 = 2;  // Major Second
			ck3 = 4;  // Major 3rd
			ck4 = 5;  // 4th
			ck5 = 7;  // Perfect 5th 
			ck6 = 9;  // Major 6th
			ck7 = 11; // Major Seventh

break;
		case 0xC3FC:    // DORIAN			
			ck2 = 2;  // Major Second
			ck3 = 3;  // Major 3rd
			ck4 = 5;  // 4th
			ck5 = 7;  // Perfect 5th 
			ck6 = 9;  // Major 6th
			ck7 = 10; // Major Seventh
			
break;
		case 0xC3FD:    // PHRYGIAN			
			ck2 = 1;  // Major Second
			ck3 = 3;  // Major 3rd
			ck4 = 5;  // 4th
			ck5 = 7;  // Perfect 5th 
			ck6 = 8;  // Major 6th
			ck7 = 10; // Major Seventh
			
break;
		case 0xC3FE:    // LYDIAN			
			ck2 = 2;  // Major Second
			ck3 = 4;  // Major 3rd
			ck4 = 6;  // 4th
			ck5 = 7;  // Perfect 5th 
			ck6 = 9;  // Major 6th
			ck7 = 11; // Major Seventh
			
break;
		case 0xC3FF:    // MIXOLYDIAN			
			ck2 = 2;  // Major Second
			ck3 = 4;  // Major 3rd
			ck4 = 5;  // 4th
			ck5 = 7;  // Perfect 5th 
			ck6 = 9;  // Major 6th
			ck7 = 10; // Major Seventh
			
break;
		case 0xC400:    // AEOLIAN (Minor)			
			ck2 = 2;  // Major Second
			ck3 = 3;  // Major 3rd
			ck4 = 5;  // 4th
			ck5 = 7;  // Perfect 5th 
			ck6 = 8;  // Major 6th
			ck7 = 10; // Major Seventh
			
break;
		case 0xC401:    // LOCRIAN			
			ck2 = 1;  // Major Second
			ck3 = 3;  // Major 3rd
			ck4 = 5;  // 4th
			ck5 = 6;  // Perfect 5th 
			ck6 = 8;  // Major 6th
			ck7 = 10; // Major Seventh
			
break;
		case 0xC402:    // Harmonic Minor		
			ck2 = 2;  // Major Second
			ck3 = 3;  // Major 3rd
			ck4 = 5;  // 4th
			ck5 = 7;  // Perfect 5th 
			ck6 = 8;  // Major 6th
			ck7 = 11; // Major Seventh

break;																	
		case 0xC403:    // Melodic Minor		
			ck2 = 2;  // Major Second
			ck3 = 3;  // Major 3rd
			ck4 = 5;  // 4th
			ck5 = 7;  // Perfect 5th 
			ck6 = 9;  // Major 6th
			ck7 = 11; // Major Seventh
			
break;																	
		case 0xC404:    // Whole Step		
			ck2 = 2;  // Major Second
			ck3 = 4;  // Major 3rd
			ck4 = 6;  // 4th
			ck5 = 8;  // Perfect 5th 
			ck6 = 10;  // Major 6th
			ck7 = 0; // Major Seventh
			
break;																	
		case 0xC405:    // Major Pentatonic		
			ck2 = 2;  // Major Second
			ck3 = 4;  // Major 3rd
			ck4 = 7;  // 4th
			ck5 = 9;  // Perfect 5th 
			ck6 = 0;  // Major 6th
			ck7 = 0; // Major Seventh
			
break;																	
		case 0xC406:    // Minor Pentatonic		
			ck2 = 3;  // Major Second
			ck3 = 5;  // Major 3rd
			ck4 = 7;  // 4th
			ck5 = 10;  // Perfect 5th 
			ck6 = 0;  // Major 6th
			ck7 = 0; // Major Seventh

		 }
		if (inversionposition == 1) {
			if (ck2 != 0) {
				ck2 -= 12;
				}
			if (ck3 != 0) {
				ck3 -= 12;
				}
			if (ck4 != 0) {
				ck4 -= 12;
				}
			if (ck5 != 0) {
				ck5 -= 12;
				}
			if (ck6 != 0) {
				ck6 -= 12;
				}
			}
			
		else if (inversionposition == 2) {
			if (ck3 != 0) {
				ck3 -= 12;
				}
			if (ck4 != 0) {
				ck4 -= 12;
				}
			if (ck5 != 0) {
				ck5 -= 12;
				}
			if (ck6 != 0) {
				ck6 -= 12;
				}
			}
			
		else if (inversionposition == 3) {
			if (ck4 != 0) {
				ck4 -= 12;
			}
			if (ck5 != 0) {
				ck5 -= 12;
				}
			if (ck6 != 0) {
				ck6 -= 12;
				}
		}
				
		else if (inversionposition == 4) {
			if (ck5 != 0) {
				ck5 -= 12;
				}
			if (ck6 != 0) {
				ck6 -= 12;
				}
		}		
		else if (inversionposition == 5) {
			if (ck6 != 0) {
				ck6 -= 12;
				}
		}
		
    } else {
        scstatus = 0;
		if (sclight != 3) {sclight = 0;}
        ck2 = 0;
        ck3 = 0;
        ck4 = 0;
        ck5 = 0;
		ck6 = 0;
		ck7 = 0;
		hk2 = 0;
		hk2 = 0;
		hk2d = 0;
		hk3 = 0;
		hk3 = 0;
		hk3d = 0;
		hk4 = 0;
		hk4 = 0;
		hk4d = 0;
		hk5 = 0;
		hk5 = 0;
		hk5d = 0;
		hk6 = 0;
		hk6 = 0;
		hk6d = 0;
		hk7 = 0;
		hk7 = 0;
		hk7d = 0;
		rootnote = 13;
		bassnote = 13;
		rgb_matrix_mode(previous_rgb_mode);  // Restore the previous RGB mode
    }
}

	
 if (record->event.pressed) {
    set_keylog(keycode, record);
  
 } if (!record->event.pressed) {
	 		if (oneshotchannel != 0 && !(keycode >= 0xC438 && keycode <= 0xC447)) {
			channel_number = channelplaceholder;  // Restore the previous channel
			channelplaceholder = 0;  // Reset the placeholder
			oneshotchannel = 0;
			} if ((keycode >= 28931 && keycode <= 29002) || (keycode >= 50688 && keycode <= 50759) || (keycode >= 50800 && keycode <= 50871)) {
			if (hk1 != 0) {set_keylog(keycode, record);}
			else if (hk1 == 0) {snprintf(keylog_str, sizeof(keylog_str), " \n");}
		}else {return true;}

	}

	
	

if (keycode >= MI_CC_TOG_0 && keycode < (MI_CC_TOG_0 + 128)) { // CC TOGGLE
        uint8_t cc = keycode - MI_CC_TOG_0;

        if (CCValue[cc]) {
            CCValue[cc] = 0;
        } else {
            CCValue[cc] = 127;
        }
        midi_send_cc(&midi_device, channel_number, cc, CCValue[cc]);

        //sprintf(status_str, "CC\nTog\n%d", cc);

    } else if (keycode >= MI_CC_UP_0 && keycode < (MI_CC_UP_0 + 128)) { // CC ++
    uint8_t cc = keycode - MI_CC_UP_0;

    if (CCValue[cc] < 127) {
        CCValue[cc] += encoder_step; // Apply the encoder step directly
        if (CCValue[cc] > 127) {
            CCValue[cc] = 127;
        }
    }

    midi_send_cc(&midi_device, channel_number, cc, CCValue[cc]);


        // sprintf(status_str, "CC\nUp\n%d", cc);
		


    } else if (keycode >= MI_CC_DWN_0 && keycode < (MI_CC_DWN_0 + 128)) { // CC --
    uint8_t cc = keycode - MI_CC_DWN_0;

    if (CCValue[cc] > 0) {
        if (CCValue[cc] >= encoder_step) {
            CCValue[cc] -= encoder_step; // Apply encoder step directly
        } else {
            CCValue[cc] = 0;
        }
    }

    midi_send_cc(&midi_device, channel_number, cc, CCValue[cc]);




        //sprintf(status_str, "CC\nDown\n%d", cc);
    } else if (keycode == 0xC437){
			if (record->event.key.row == KEYLOC_ENCODER_CW && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) > 0) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (velocity_sensitivity)) < 0){
					midi_config.velocity = 0;
                }
			}else if (record->event.key.row == KEYLOC_ENCODER_CCW && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) > 0) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (velocity_sensitivity)) < 0){
					midi_config.velocity = 0;
                }
            }else if (record->event.pressed && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) > 0) {
                    midi_config.velocity -= (velocity_sensitivity);
                } else if ((midi_config.velocity - (velocity_sensitivity)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (velocity_sensitivity)) < 0){
					midi_config.velocity = 0;
                }

                dprintf("midi velocity %d\n", midi_config.velocity);
            }
    } else if (keycode == 0xC436){
			if (record->event.key.row == KEYLOC_ENCODER_CW && midi_config.velocity < 127) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) <127) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (velocity_sensitivity)) >127){
					midi_config.velocity = 127;
                }
			}else if (record->event.key.row == KEYLOC_ENCODER_CCW && midi_config.velocity < 127) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) <127) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (velocity_sensitivity)) >127){
					midi_config.velocity = 127;
                }
            }else if (record->event.pressed && midi_config.velocity < 127) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) <127) {
                    midi_config.velocity += (velocity_sensitivity);
                } else if ((midi_config.velocity + (velocity_sensitivity)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (velocity_sensitivity)) >127){
					midi_config.velocity = 127;
                }

                dprintf("midi velocity %d\n", midi_config.velocity);
            }

    } else if (keycode >= MI_CC_0_0 && keycode < (MI_CC_0_0 + 128 * 128)) { // CC FIXED
        uint8_t cc  = (keycode - MI_CC_0_0) / 128;
        uint8_t val = (keycode - MI_CC_0_0) % 128;

        CCValue[cc] = val;
        midi_send_cc(&midi_device, channel_number, cc, CCValue[cc]);

        //sprintf(status_str, "CC\n%d\n%d", cc, val);

    } else if (keycode >= MI_BANK_MSB_0 && keycode < (MI_BANK_MSB_0 + 128)) { // BANK MSB
        uint8_t val = keycode - MI_BANK_MSB_0;
        uint8_t cc  = BANK_SEL_MSB_CC;

        CCValue[cc] = val;
        midi_send_cc(&midi_device, channel_number, cc, CCValue[cc]);

        MidiCurrentBank &= 0x00FF;
        MidiCurrentBank |= val << 8;

        //sprintf(status_str, "MSB\nbank\n%d", val);

    } else if (keycode >= MI_BANK_LSB_0 && keycode < (MI_BANK_LSB_0 + 128)) { // BANK LSB
        uint8_t val = keycode - MI_BANK_LSB_0;
        uint8_t cc  = BANK_SEL_LSB_CC;

        CCValue[cc] = val;
        midi_send_cc(&midi_device, channel_number, cc, CCValue[cc]);

        MidiCurrentBank &= 0xFF00;
        MidiCurrentBank |= val;

        //sprintf(status_str, "LSB\nbank\n%d", val);

    } else if (keycode >= MI_PROG_0 && keycode < (MI_PROG_0 + 128)) { // PROG CHANGE
        uint8_t val = keycode - MI_PROG_0;

        midi_send_programchange(&midi_device, channel_number, val);
        MidiCurrentProg = val;

        //sprintf(status_str, "PC\n%d", val);

    } else if (keycode >= MI_VELOCITY_0 && keycode < (MI_VELOCITY_0 + 128)) {
        uint8_t val = keycode - MI_VELOCITY_0;
        if (val >= 0 && val < 128) midi_config.velocity = val;

    } else if (keycode >= ENCODER_STEP_1 && keycode < (ENCODER_STEP_1 + 16)) {
        uint8_t val = keycode - ENCODER_STEP_1 + 1;
        if (val >= 1 && val < 17) encoder_step = val;
    
    } else {
        uint8_t lsb = 0;
        uint8_t msb = 0;

        switch (keycode) {
            case MI_BANK_UP:
                if (MidiCurrentBank < 0xFFFF) {
                    ++MidiCurrentBank;
                }
                //sprintf(status_str, "bank\n%d", MidiCurrentBank);
                lsb = MidiCurrentBank & 0xFF;
                msb = (MidiCurrentBank & 0xFF00) >> 8;
                midi_send_cc(&midi_device, channel_number, BANK_SEL_LSB_CC, lsb);
                midi_send_cc(&midi_device, channel_number, BANK_SEL_MSB_CC, msb);

                break;
            case MI_BANK_DWN:
                if (MidiCurrentBank > 0) {
                    --MidiCurrentBank;
                }
                //sprintf(status_str, "bank\n%d", MidiCurrentBank);
                uint8_t lsb = MidiCurrentBank & 0xFF;
                uint8_t msb = (MidiCurrentBank & 0xFF00) >> 8;
                midi_send_cc(&midi_device, channel_number, BANK_SEL_LSB_CC, lsb);
                midi_send_cc(&midi_device, channel_number, BANK_SEL_MSB_CC, msb);
                break;
            case MI_PROG_UP:
                if (MidiCurrentProg < 127) {
                    ++MidiCurrentProg;
                }
                //sprintf(status_str, "PC\n%d", MidiCurrentProg);
                midi_send_programchange(&midi_device, channel_number, MidiCurrentProg);
                break;
            case MI_PROG_DWN:
                if (MidiCurrentProg > 0) {
                    --MidiCurrentProg;
                }
                //sprintf(status_str, "PC\n%d", MidiCurrentProg);
                midi_send_programchange(&midi_device, channel_number, MidiCurrentProg);
                break;
            default:
                //sprintf(status_str, "%d", keycode);
                break; 

        }             
    }

    return true;
}

oled_rotation_t oled_init_kb(oled_rotation_t rotation) { return OLED_ROTATION_0; }

bool oled_task_user(void) {
    // Buffer to store the formatted string
    char str[22] = "";
    char name[124] = "";  // Define `name` buffer to be used later

    // Get the current layer and format it into `str`
    uint8_t layer = get_highest_layer(layer_state | default_layer_state);
    snprintf(str, sizeof(str), "       LAYER %-3d", layer);

    // Write the layer information to the OLED
    oled_write_P(str, false);

    // Render keylog information
    oled_render_keylog();

    // Add separator line to `name` and write to OLED
    //snprintf(name + strlen(name), sizeof(name) - strlen(name), "---------------------");

    // You only need to add the separator once, not three times.
    oled_write(name, false);

    /* KEYBOARD PET VARIABLES START */
   // current_wpm = get_current_wpm();
    led_usb_state = host_keyboard_led_state();
    render_luna(0, 0);

    return false;
}