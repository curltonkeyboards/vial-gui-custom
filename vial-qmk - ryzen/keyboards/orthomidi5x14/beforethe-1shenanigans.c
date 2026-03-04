// Copyright 2023 QMK
// SPDX-License-Identifier: GPL-2.0-or-later

#include "midi_function_types.h"
#include "process_midi.h"
#include <printf/printf.h>
#include QMK_KEYBOARD_H
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
static uint8_t tone2_status[2][MIDI_TONE_COUNT];
static uint8_t tone3_status[2][MIDI_TONE_COUNT];
static uint8_t tone4_status[2][MIDI_TONE_COUNT];
static uint8_t tone5_status[2][MIDI_TONE_COUNT];
static uint8_t tone6_status[2][MIDI_TONE_COUNT];

uint8_t modified_note;
uint8_t original_note;

//char status_str[32] = "";


/* KEYLOGREND */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>

char keylog_str[24] = {};
int transpose_number = 0;  // Variable to store the special number
int octave_number = 0;
int velocity_number = 0;
int cc_up_value1[128] = {0};   // (value 1) for CC UP for each CC#
int cc_updown_value[128] = {0};   // (value 2) for CC UP for each CC#[128] = {0};   // (value 2) for CC UP for each CC#
int cc_down_value1[128] = {0};   // (value 1) for CC UP for each CC#
int sensitivity = 1;           // Initial sensitivity value
int channel_number = 0;
int heldkey1 = 0;
int heldkey2 = 0;
int heldkey3 = 0;
int heldkey4 = 0;
int heldkey5 = 0;
int heldkey6 = 0;
int heldkey1difference = 0; 
int heldkey2difference = 0; 
int heldkey3difference = 0; 
int heldkey4difference = 0; 
int heldkey5difference = 0; 
int heldkey6difference = 0; 
int trueheldkey1 = 0;
int trueheldkey2 = 0;
int trueheldkey3 = 0;
int trueheldkey4 = 0;
int trueheldkey5 = 0;
int trueheldkey6 = 0;
int chordkey1 = 0;
int chordkey2 = 0;
int chordkey3 = 0;
int chordkey4 = 0;
int chordkey5 = 0;
int chordkey6 = 0;
int smartchordkey2 = 0;
int smartchordkey3 = 0;
int smartchordkey4 = 0;
int smartchordkey5 = 0;
int smartchordkey6 = 0;
int smartchordstatus = 0;
int inversionposition = 0;
int rootnote = 13;
int bassnote = 13;
int trueheldkey[7];

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

#include <vector>
#include <string>

struct ChordPattern {
    const char* name;
    int numNotes;
    std::vector<std::vector<int>> possibleIntervals;
    bool checkInversion;
    int inversionType;
};

const char* getChordName() {
    struct HeldNotes {
        std::vector<int> differences = {
            heldkey2difference,
            heldkey3difference,
            heldkey4difference,
            heldkey5difference,
            heldkey6difference,
            heldkey7difference
        };
        std::vector<int> trueKeys = {
            trueheldkey2,
            trueheldkey3,
            trueheldkey4,
            trueheldkey5,
            trueheldkey6,
            trueheldkey7
        };
    } held;

    const std::vector<ChordPattern> PATTERNS = {
        // Basic Intervals
        {"     ", 1, {{0}}, false, 0},  // Single note
        {"Minor 2nd", 1, {{2}}, false, 0},
        {"Major 2nd", 1, {{3}}, false, 0},
        {"Minor 3rd", 1, {{4}}, false, 0},
        {"Major 3rd", 1, {{5}}, false, 0},
        {"Perfect 4th", 1, {{6}}, false, 0},
        {"Tritone", 1, {{7}}, false, 0},
        {"Perfect 5th", 1, {{8}}, false, 0},
        {"Minor 6th", 1, {{9}}, false, 0},
        {"Major 6th", 1, {{10}}, false, 0},
        {"Minor 7th", 1, {{11}}, false, 0},
        {"Major 7th", 1, {{12}}, false, 0},

        // Major Triads and Inversions
        {"Major", 2, {{5, 8}}, true, 1},     // Root position
        {"", 2, {{6, 10}}, true, 2},         // First inversion
        {"", 2, {{9, 4}}, true, 3},          // Second inversion

        // Minor Triads and Inversions
        {"Minor", 2, {{4, 8}}, true, 4},     // Root position
        {"m", 2, {{6, 9}}, true, 5},         // First inversion
        {"m", 2, {{10, 5}}, true, 6},        // Second inversion

        // Diminished Triads and Inversions
        {"dim", 2, {{4, 7}}, true, 7},       // Root position
        {"dim", 2, {{7, 10}}, true, 8},      // First inversion
        {"dim", 2, {{10, 4}}, true, 9},      // Second inversion

        // b5 Triads and Inversions
        {"b5", 2, {{5, 7}}, true, 10},       // Root position
        {"b5", 2, {{5, 9}}, true, 11},       // First inversion
        {"b5", 2, {{9, 3}}, true, 12},       // Second inversion

        // sus2 and sus4 Inversions
        {"sus2", 2, {{3, 8}}, true, 13},     // Root position
        {"7sus4", 2, {{6, 8}}, true, 14},    // First inversion
        {"sus4", 2, {{6, 11}}, true, 15},    // Second inversion

        // Augmented Triads
        {"aug", 2, {{5, 9}}, true, 16},

        // Major 7 and Inversions
        {"Maj7", 3, {{5, 8, 12}}, true, 17},     // Root position
        {"Maj7", 3, {{2, 6, 9}}, true, 18},      // First inversion
        {"Maj7", 3, {{6, 10, 5}}, true, 19},     // Second inversion
        {"Maj7", 3, {{9, 4, 8}}, true, 20},      // Third inversion

        // Dominant 7 and Inversions
        {"7", 3, {{5, 8, 11}}, true, 21},        // Root position
        {"7", 3, {{3, 7, 10}}, true, 22},        // First inversion
        {"7", 3, {{6, 10, 4}}, true, 23},        // Second inversion
        {"7", 3, {{9, 4, 7}}, true, 24},         // Third inversion

        // Minor 7 and Inversions
        {"min7", 3, {{4, 8, 11}}, true, 25},     // Root position
        {"min7", 3, {{3, 6, 10}}, true, 26},     // First inversion
        {"min7", 3, {{6, 9, 4}}, true, 27},      // Second inversion
        {"min7", 3, {{10, 5, 8}}, true, 28},     // Third inversion

        // min7#5 and Inversions
        {"min7#5", 3, {{4, 9, 11}}, true, 29},  // Root position
        {"min7#5", 3, {{3, 6, 9}}, true, 30},   // First inversion
        {"min7#5", 3, {{6, 8, 4}}, true, 31},   // Second inversion
        {"min7#5", 3, {{10, 6, 8}}, true, 32},  // Third inversion

        // 7#5 and Inversions
        {"7#5", 3, {{5, 9, 11}}, true, 33},     // Root position
        {"7#5", 3, {{3, 7, 11}}, true, 34},     // First inversion
        {"7#5", 3, {{6, 11, 4}}, true, 35},     // Second inversion
        {"7#5", 3, {{9, 4, 8}}, true, 36},      // Third inversion

		// Maj7#5 and Inversions
		{"Maj7#5", 3, {{5, 9, 12}}, true, 37},       // Root position
		{"Maj7#5", 3, {{2, 6, 10}}, true, 38},       // First inversion
		{"Maj7#5", 3, {{6, 10, 5}}, true, 39},       // Second inversion
		{"Maj7#5", 3, {{9, 4, 8}}, true, 40},        // Third inversion

		// min7#5 and Inversions
		{"min7#5", 3, {{4, 9, 11}}, true, 41},       // Root position
		{"min7#5", 3, {{3, 6, 9}}, true, 42},        // First inversion
		{"min7#5", 3, {{6, 8, 4}}, true, 43},        // Second inversion
		{"min7#5", 3, {{10, 6, 8}}, true, 44},       // Third inversion

		// m7b5 and Inversions
		{"m7b5", 3, {{4, 7, 11}}, true, 45},         // Root position
		{"m7b5", 3, {{3, 6, 9}}, true, 46},          // First inversion
		{"m7b5", 3, {{6, 8, 4}}, true, 47},          // Second inversion
		{"m7b5", 3, {{9, 4, 7}}, true, 48},          // Third inversion

		// 7b5 and Inversions
		{"7b5", 3, {{5, 7, 11}}, true, 49},          // Root position
		{"7b5", 3, {{3, 7, 10}}, true, 50},          // First inversion
		{"7b5", 3, {{6, 9, 4}}, true, 51},           // Second inversion
		{"7b5", 3, {{9, 3, 7}}, true, 52},           // Third inversion

		// Maj7b5 and Inversions
		{"Maj7b5", 3, {{5, 7, 12}}, true, 53},       // Root position
		{"Maj7b5", 3, {{2, 7, 9}}, true, 54},        // First inversion
		{"Maj7b5", 3, {{7, 11, 5}}, true, 55},       // Second inversion
		{"Maj7b5", 3, {{9, 3, 8}}, true, 56},        // Third inversion

		// minMaj7 and Inversions
		{"minMaj7", 3, {{4, 8, 12}}, true, 57},      // Root position
		{"minMaj7", 3, {{2, 5, 9}}, true, 58},       // First inversion
		{"minMaj7", 3, {{6, 9, 5}}, true, 59},       // Second inversion
		{"minMaj7", 3, {{10, 5, 8}}, true, 60},      // Third inversion

		// Maj7sus2 and Inversions
		{"Maj7sus2", 3, {{3, 8, 12}}, true, 61},     // Root position
		{"Maj7sus2", 3, {{2, 4, 6}}, true, 62},      // First inversion
		{"Maj7sus2", 3, {{5, 6, 11}}, true, 63},     // Second inversion
		{"Maj7sus2", 3, {{8, 11, 2}}, true, 64},     // Third inversion

		// 7sus4 and Inversions
		{"7sus4", 3, {{6, 8, 11}}, true, 65},        // Root position
		{"7sus4", 3, {{3, 8, 10}}, true, 66},        // First inversion
		{"7sus4", 3, {{6, 11, 4}}, true, 67},        // Second inversion
		{"7sus4", 3, {{8, 3, 7}}, true, 68},         // Third inversion

		// Maj7sus4 and Inversions
		{"Maj7sus4", 3, {{6, 8, 12}}, true, 69},     // Root position
		{"Maj7sus4", 3, {{2, 8, 10}}, true, 70},     // First inversion
		{"Maj7sus4", 3, {{7, 11, 5}}, true, 71},     // Second inversion
		{"Maj7sus4", 3, {{8, 2, 7}}, true, 72},      // Third inversion

		{"min7no5", 2, {{4, 11}}, true, 73},         // Root position
		{"min7no5", 2, {{3, 6}}, true, 74},          // First inversion
		{"min7no5", 2, {{6, 8}}, true, 75},          // Second inversion
		{"min7no5", 2, {{10, 6}}, true, 76},         // Third inversion

		// 7no5 and inversions
		{"7no5", 2, {{5, 11}}, true, 77},            // Root position
		{"7no5", 2, {{3, 7}}, true, 78},             // First inversion
		{"7no5", 2, {{6, 9}}, true, 79},             // Second inversion
		{"7no5", 2, {{9, 3}}, true, 80},             // Third inversion

		// maj7no5 and inversions
		{"maj7no5", 2, {{5, 12}}, true, 81},         // Root position
		{"maj7no5", 2, {{2, 7}}, true, 82},          // First inversion
		{"maj7no5", 2, {{7, 11}}, true, 83},         // Second inversion
		{"maj7no5", 2, {{9, 2}}, true, 84},          // Third inversion

		// No3 variants with inversions
		// maj7no3 and inversions
		{"maj7no3", 2, {{8, 12}}, true, 85},         // Root position
		{"maj7no3", 2, {{2, 8}}, true, 86},          // First inversion
		{"maj7no3", 2, {{5, 6}}, true, 87},          // Second inversion
		{"maj7no3", 2, {{8, 2}}, true, 88},          // Third inversion

		// 7no3 and inversions
		{"7no3", 2, {{8, 11}}, true, 89},            // Root position
		{"7no3", 2, {{3, 10}}, true, 90},            // First inversion
		{"7no3", 2, {{4, 6}}, true, 91},             // Second inversion
		{"7no3", 2, {{8, 3}}, true, 92},             // Third inversion

		// 7b5no3 and inversions
		{"7b5no3", 2, {{7, 11}}, true, 93},          // Root position
		{"7b5no3", 2, {{3, 8}}, true, 94},           // First inversion
		{"7b5no3", 2, {{4, 5}}, true, 95},           // Second inversion
		{"7b5no3", 2, {{7, 3}}, true, 96},           // Third inversion

		// Ninth Chords and Inversions
		{"9", 4, {{5, 8, 11, 3}}, true, 79},         // Root position
		{"9", 4, {{3, 7, 10, 2}}, true, 80},         // First inversion
		{"9", 4, {{6, 10, 4, 8}}, true, 81},         // Second inversion
		{"9", 4, {{9, 4, 7, 11}}, true, 82},         // Third inversion

		{"min9", 4, {{4, 8, 11, 3}}, true, 83},      // Root position
		{"min9", 4, {{3, 6, 10, 2}}, true, 84},      // First inversion
		{"min9", 4, {{6, 9, 4, 8}}, true, 85},       // Second inversion
		{"min9", 4, {{10, 5, 8, 11}}, true, 86},     // Third inversion

		{"Maj9", 4, {{5, 8, 12, 3}}, true, 87},      // Root position
		{"Maj9", 4, {{2, 6, 9, 1}}, true, 88},       // First inversion
		{"Maj9", 4, {{6, 10, 5, 8}}, true, 89},      // Second inversion
		{"Maj9", 4, {{9, 4, 8, 11}}, true, 90},      // Third inversion

		{"m9b5", 4, {{4, 7, 11, 3}}, true, 97},      // Root position
		{"m9b5", 4, {{3, 6, 9, 2}}, true, 98},       // First inversion
		{"m9b5", 4, {{6, 8, 4, 7}}, true, 99},       // Second inversion
		{"m9b5", 4, {{9, 4, 7, 11}}, true, 100},     // Third inversion
		{"m9b5", 4, {{10, 2, 5, 8}}, true, 101},     // Fourth inversion
		{"9#5", 4, {{5, 9, 11, 3}}, true, 92},
		{"#9#5", 4, {{5, 9, 11, 4}}, true, 93},

		// 6/9 Chords
		{"(6/9)", 4, {{5, 8, 10, 3}}, true, 94},
		{"m(6/9)", 4, {{4, 8, 10, 3}}, true, 95},

		// 11th Chords
		{"11", 5, {{5, 8, 11, 3, 6}}, true, 96},
		{"min11", 5, {{4, 8, 11, 3, 6}}, true, 97},
		{"Maj11", 5, {{5, 8, 12, 3, 6}}, true, 98},
		{"min7b5(9/11)", 5, {{4, 7, 11, 3, 6}}, true, 99},
		{"dim7(9/11)", 5, {{4, 7, 10, 3, 6}}, true, 100},

		// Add11 variants
		{"min7(#11)", 4, {{4, 8, 11, 7}}, true, 101},
		{"7(#11)", 4, {{5, 8, 11, 7}}, true, 102},
		{"maj7(#11)", 4, {{5, 8, 12, 7}}, true, 103},

		// Scales (no inversions)
		{"Major Scale (Ionian)", 6, {{3, 5, 6, 8, 10, 12}}, false, 104},
		{"Dorian", 6, {{3, 4, 6, 8, 10, 11}}, false, 105},
		{"Phrygian", 6, {{2, 4, 6, 8, 9, 11}}, false, 106},
		{"Lydian", 6, {{3, 5, 7, 8, 10, 12}}, false, 107},
		{"Mixolydian", 6, {{3, 5, 6, 8, 10, 11}}, false, 108},
		{"Minor Scale (Aeolian)", 6, {{3, 4, 6, 8, 9, 11}}, false, 109},
		{"Locrian", 6, {{2, 4, 6, 7, 9, 11}}, false, 110},
		{"Harmonic Minor", 6, {{3, 4, 6, 8, 9, 12}}, false, 111},
		{"Melodic Minor", 6, {{3, 4, 6, 8, 10, 12}}, false, 112},
		{"Whole Step Scale", 5, {{3, 5, 7, 9, 11}}, false, 113}

    };

    // Check for single note
    if (held.differences[0] == 0 && held.differences[1] == 0 && 
        held.differences[2] == 0 && held.differences[3] == 0 && 
        held.differences[4] == 0) {
        rootnote = 13;
        bassnote = 13;
        return "     ";
    }

    // Helper function for pattern matching
    auto matchesPattern = [](const HeldNotes& held, const std::vector<std::vector<int>>& pattern, int numNotes) {
        for (int i = 0; i < numNotes; i++) {
            bool noteMatched = false;
            for (int interval : pattern[i]) {
                if (held.differences[i] == interval) {
                    noteMatched = true;
                    break;
                }
            }
            if (!noteMatched) return false;
        }
        // Check no extra notes
        for (size_t i = numNotes; i < held.differences.size(); i++) {
            if (held.differences[i] != 0) return false;
        }
        return true;
    };

    // Check each pattern
    for (const auto& pattern : PATTERNS) {
        if (matchesPattern(held, pattern.possibleIntervals, pattern.numNotes)) {
            if (pattern.checkInversion) {
                setRootAndBass(rootnote, bassnote, heldkey1, pattern.inversionType, held);
            } else {
                rootnote = heldkey1;
                bassnote = 13;
            }
            return pattern.name;
        }
    }

    return "     ";
}

void setRootAndBass(int& rootNote, int& bassNote, int heldKey1, int inversionType, const HeldNotes& held) {
    switch (inversionType) {
        // Major Triad Inversions
        case 1:  // Root position Major
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 2:  // First inversion Major
            rootNote = (heldKey1 + 8) % 12;
            bassNote = heldKey1;
            break;
        case 3:  // Second inversion Major
            rootNote = (heldKey1 + 5) % 12;
            bassNote = heldKey1;
            break;

        // Minor Triad Inversions
        case 4:  // Root position Minor
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 5:  // First inversion Minor
            rootNote = (heldKey1 + 9) % 12;
            bassNote = heldKey1;
            break;
        case 6:  // Second inversion Minor
            rootNote = (heldKey1 + 5) % 12;
            bassNote = heldKey1;
            break;

        // Diminished Triad Inversions
        case 7:  // Root position dim
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 8:  // First inversion dim
            rootNote = (heldKey1 + 9) % 12;
            bassNote = heldKey1;
            break;
        case 9:  // Second inversion dim
            rootNote = (heldKey1 + 6) % 12;
            bassNote = heldKey1;
            break;

        // b5 Triad Inversions
        case 10:  // Root position b5
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 11:  // First inversion b5
            rootNote = (heldKey1 + 4) % 12;
            bassNote = (heldKey1 + 3) % 12;
            break;
        case 12:  // Second inversion b5
            rootNote = (heldKey1 + 6) % 12;
            bassNote = heldKey1;
            break;

        // Sus2 and Sus4 Inversions
        case 13:  // Root position sus2
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 14:  // First inversion sus2/sus4
            rootNote = (heldKey1 + 5) % 12;
            bassNote = 13;
            break;
        case 15:  // Second inversion sus2/sus4
            rootNote = heldKey1;
            bassNote = 13;
            break;

        // Augmented
        case 16:  // aug
            rootNote = heldKey1;
            bassNote = 13;
            break;

        // Major 7 Inversions
        case 17:  // Maj7 root position
            rootNote = heldKey1;
            bassNote = (heldKey1 + 4) % 12;
            break;
        case 18:  // Maj7 first inversion
            rootNote = (heldKey1 + 1) % 12;
            bassNote = 13;
            break;
        case 19:  // Maj7 second inversion
            rootNote = (heldKey1 + 5) % 12;
            bassNote = heldKey1;
            break;
        case 20:  // Maj7 third inversion
            rootNote = (heldKey1 + 8) % 12;
            bassNote = heldKey1;
            break;

        // Dominant 7 Inversions
        case 21:  // 7 root position
            rootNote = heldKey1;
            bassNote = (heldKey1 + 4) % 12;
            break;
        case 22:  // 7 first inversion
            rootNote = (heldKey1 + 2) % 12;
            bassNote = 13;
            break;
        case 23:  // 7 second inversion
            rootNote = (heldKey1 + 5) % 12;
            bassNote = heldKey1;
            break;
        case 24:  // 7 third inversion
            rootNote = (heldKey1 + 8) % 12;
            bassNote = heldKey1;
            break;

        // Minor 7 Inversions
        case 25:  // min7 root position
            rootNote = heldKey1;
            bassNote = (heldKey1 + 3) % 12;
            break;
        case 26:  // min7 first inversion
            rootNote = (heldKey1 + 2) % 12;
            bassNote = 13;
            break;
        case 27:  // min7 second inversion
            rootNote = (heldKey1 + 5) % 12;
            bassNote = heldKey1;
            break;
        case 28:  // min7 third inversion
            rootNote = (heldKey1 + 9) % 12;
            bassNote = heldKey1;
            break;

        // min7#5 Inversions
        case 29:  // min7#5 root position
            rootNote = heldKey1;
            bassNote = (heldKey1 + 3) % 12;
            break;
        case 30:  // min7#5 first inversion
            rootNote = (heldKey1 + 2) % 12;
            bassNote = 13;
            break;
        case 31:  // min7#5 second inversion
            rootNote = (heldKey1 + 6) % 12;
            bassNote = heldKey1;
            break;
        case 32:  // min7#5 third inversion
            rootNote = (heldKey1 + 9) % 12;
            bassNote = heldKey1;
            break;

        // 7#5 Inversions
        case 33:  // 7#5 root position
            rootNote = heldKey1;
            bassNote = (heldKey1 + 4) % 12;
            break;
        case 34:  // 7#5 first inversion
            rootNote = (heldKey1 + 2) % 12;
            bassNote = 13;
            break;
        case 35:  // 7#5 second inversion
            rootNote = (heldKey1 + 6) % 12;
            bassNote = heldKey1;
            break;
        case 36:  // 7#5 third inversion
            rootNote = (heldKey1 + 9) % 12;
            bassNote = heldKey1;
            break;

        // Maj7#5 Inversions
        case 37:  // Maj7#5 root position
            rootNote = heldKey1;
            bassNote = (heldKey1 + 4) % 12;
            break;
        case 38:  // Maj7#5 first inversion
            rootNote = (heldKey1 + 1) % 12;
            bassNote = 13;
            break;
        case 39:  // Maj7#5 second inversion
            rootNote = (heldKey1 + 6) % 12;
            bassNote = heldKey1;
            break;
        case 40:  // Maj7#5 third inversion
            rootNote = (heldKey1 + 9) % 12;
            bassNote = heldKey1;
            break;

        // m7b5 Inversions
        case 41:  // m7b5 root position
            rootNote = heldKey1;
            bassNote = (heldKey1 + 3) % 12;
            break;
        case 42:  // m7b5 first inversion
            rootNote = (heldKey1 + 2) % 12;
            bassNote = 13;
            break;
        case 43:  // m7b5 second inversion
            rootNote = (heldKey1 + 6) % 12;
            bassNote = heldKey1;
            break;
        case 44:  // m7b5 third inversion
            rootNote = (heldKey1 + 9) % 12;
            bassNote = heldKey1;
            break;

        // minMaj7 Inversions
        case 45:  // minMaj7 root position
            rootNote = heldKey1;
            bassNote = (heldKey1 + 3) % 12;
            break;
        case 46:  // minMaj7 first inversion
            rootNote = (heldKey1 + 1) % 12;
            bassNote = 13;
            break;
        case 47:  // minMaj7 second inversion
            rootNote = (heldKey1 + 5) % 12;
            bassNote = heldKey1;
            break;
        case 48:  // minMaj7 third inversion
            rootNote = (heldKey1 + 9) % 12;
            bassNote = heldKey1;
            break;

        // Ninth Chords
        case 49:  // 9
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 50:  // Maj9
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 51:  // min9
            rootNote = heldKey1;
            bassNote = 13;
            break;

        // Extended and Altered Chords
        case 52:  // 11
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 53:  // min11
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 54:  // Maj11
            rootNote = heldKey1;
            bassNote = 13;
            break;

        // Add9 and Add11 variants
        case 55:  // add9
            rootNote = heldKey1;
            bassNote = 13;
            break;
        case 56:  // add11
            rootNote = heldKey1;
            bassNote = 13;
            break;

        // Default case
        default:
            rootNote = heldKey1;
            bassNote = 13;
            break;
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


//led_config_t g_led_config = { {
  // Key Matrix to LED Index
//  {   0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13 },
//  {  14,  15,  16,  17,  18,  19,  20,  21,  22,  23,  24,  25,  26,  27 },
 // {  28,  29,  30,  31,  32,  33,  34,  35,  36,  37,  38,  39,  40,  41 },
//  {  42,  43,  44,  45,  46,  47,  48,  49,  50,  51,  52,  53,  54,  55 },
 // {  56,  57,  58,  59,  60,  61,  62,  63,  64,  65,  66,  67,  68,  69 }
//}, {
  // LED Index to Physical Position
//  {   0,   0 }, {  16,   0 }, {  32,   0 }, {  48,   0 }, {  64,   0 }, {  80,   0 }, {  96,   0 }, { 112,   0 }, { 128,   0 }, { 144,   0 }, { 160,   0 }, { 176,   0 }, { 192,   0 }, { 208,   0 },
 // {   0,  15 }, {  16,  15 }, {  32,  15 }, {  48,  15 }, {  64,  15 }, {  80,  15 }, {  96,  15 }, { 112,  15 }, { 128,  15 }, { 144,  15 }, { 160,  15 }, { 176,  15 }, { 192,  15 }, { 208,  15 },
 // {   0,  30 }, {  16,  30 }, {  32,  30 }, {  48,  30 }, {  64,  30 }, {  80,  30 }, {  96,  30 }, { 112,  30 }, { 128,  30 }, { 144,  30 }, { 160,  30 }, { 176,  30 }, { 192,  30 }, { 208,  30 },
 // {   0,  45 }, {  16,  45 }, {  32,  45 }, {  48,  45 }, {  64,  45 }, {  80,  45 }, {  96,  45 }, { 112,  45 }, { 128,  45 }, { 144,  45 }, { 160,  45 }, { 176,  45 }, { 192,  45 }, { 208,  45 },
//  {   0,  60 }, {  16,  60 }, {  32,  60 }, {  48,  60 }, {  64,  60 }, {  80,  60 }, {  96,  60 }, { 112,  60 }, { 128,  60 }, { 144,  60 }, { 160,  60 }, { 176,  60 }, { 192,  60 }, { 208,  60 }
//}, {
  // LED Index to Flag
  // Adjust these flags as needed for your LED types
 // 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
 // 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
 // 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
 // 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
//  4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4
//}};

#ifdef RGB_MATRIX_ENABLE
bool rgb_matrix_indicators_kb(void) {
    if (!rgb_matrix_indicators_user()) {
        return false;
    }

    if (host_keyboard_led_state().caps_lock) { // Capslock = RED
        rgb_matrix_set_color(44, 200, 0, 0);
    }
    return true;
}
#endif

/* KEYBOARD PET START */

/* settings */
#    define MIN_WALK_SPEED      10
#    define MIN_RUN_SPEED       40

/* advanced settings */
#    define ANIM_FRAME_DURATION 200  // how long each frame lasts in ms
#    define ANIM_SIZE           96   // number of bytes in array. If you change sprites, minimize for adequate firmware size. max is 1024

/* timers */
uint32_t anim_timer = 0;

/* current frame */
uint8_t current_frame = 0;

/* status variables */
int   current_wpm = 0;
led_t led_usb_state;

bool isSneaking = false;
bool isJumping  = false;
bool showedJump = true;

/* logic */
static void render_luna(int LUNA_X, int LUNA_Y) {
    /* Sit */
    static const char PROGMEM sit[2][ANIM_SIZE] = {/* 'sit1', 32x22px */
                                                   {
                                                       0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xe0, 0x1c, 0x02, 0x05, 0x02, 0x24, 0x04, 0x04, 0x02, 0xa9, 0x1e, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xe0, 0x10, 0x08, 0x68, 0x10, 0x08, 0x04, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x06, 0x82, 0x7c, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x04, 0x0c, 0x10, 0x10, 0x20, 0x20, 0x20, 0x28, 0x3e, 0x1c, 0x20, 0x20, 0x3e, 0x0f, 0x11, 0x1f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                                   },

                                                   /* 'sit2', 32x22px */
                                                   {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xe0, 0x1c, 0x02, 0x05, 0x02, 0x24, 0x04, 0x04, 0x02, 0xa9, 0x1e, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xe0, 0x90, 0x08, 0x18, 0x60, 0x10, 0x08, 0x04, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x0e, 0x82, 0x7c, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x04, 0x0c, 0x10, 0x10, 0x20, 0x20, 0x20, 0x28, 0x3e, 0x1c, 0x20, 0x20, 0x3e, 0x0f, 0x11, 0x1f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}};

    /* Walk */
    static const char PROGMEM walk[2][ANIM_SIZE] = {/* 'walk1', 32x22px */
                                                    {
                                                        0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x40, 0x20, 0x10, 0x90, 0x90, 0x90, 0xa0, 0xc0, 0x80, 0x80, 0x80, 0x70, 0x08, 0x14, 0x08, 0x90, 0x10, 0x10, 0x08, 0xa4, 0x78, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x08, 0xfc, 0x01, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x18, 0xea, 0x10, 0x0f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x1c, 0x20, 0x20, 0x3c, 0x0f, 0x11, 0x1f, 0x03, 0x06, 0x18, 0x20, 0x20, 0x3c, 0x0c, 0x12, 0x1e, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                                    },

                                                    /* 'walk2', 32x22px */
                                                    {
                                                        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x40, 0x20, 0x20, 0x20, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0xe0, 0x10, 0x28, 0x10, 0x20, 0x20, 0x20, 0x10, 0x48, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1f, 0x20, 0xf8, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x30, 0xd5, 0x20, 0x1f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3f, 0x20, 0x30, 0x0c, 0x02, 0x05, 0x09, 0x12, 0x1e, 0x02, 0x1c, 0x14, 0x08, 0x10, 0x20, 0x2c, 0x32, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                                    }};

    /* Run */
    static const char PROGMEM run[2][ANIM_SIZE] = {/* 'run1', 32x22px */
                                                   {
                                                       0x00, 0x00, 0x00, 0x00, 0xe0, 0x10, 0x08, 0x08, 0xc8, 0xb0, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x40, 0x40, 0x3c, 0x14, 0x04, 0x08, 0x90, 0x18, 0x04, 0x08, 0xb0, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0xc4, 0xa4, 0xfc, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xc8, 0x58, 0x28, 0x2a, 0x10, 0x0f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0e, 0x09, 0x04, 0x04, 0x04, 0x04, 0x02, 0x03, 0x02, 0x01, 0x01, 0x02, 0x02, 0x04, 0x08, 0x10, 0x26, 0x2b, 0x32, 0x04, 0x05, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00,
                                                   },

                                                   /* 'run2', 32x22px */
                                                   {
                                                       0x00, 0x00, 0x00, 0xe0, 0x10, 0x10, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x80, 0x80, 0x78, 0x28, 0x08, 0x10, 0x20, 0x30, 0x08, 0x10, 0x20, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x04, 0x08, 0x10, 0x11, 0xf9, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x10, 0xb0, 0x50, 0x55, 0x20, 0x1f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x0c, 0x10, 0x20, 0x28, 0x37, 0x02, 0x1e, 0x20, 0x20, 0x18, 0x0c, 0x14, 0x1e, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                                   }};

    /* Bark */
    static const char PROGMEM bark[2][ANIM_SIZE] = {/* 'bark1', 32x22px */
                                                    {
                                                        0x00, 0xc0, 0x20, 0x10, 0xd0, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x80, 0x40, 0x3c, 0x14, 0x04, 0x08, 0x90, 0x18, 0x04, 0x08, 0xb0, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x04, 0x08, 0x10, 0x11, 0xf9, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xc8, 0x48, 0x28, 0x2a, 0x10, 0x0f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x0c, 0x10, 0x20, 0x28, 0x37, 0x02, 0x02, 0x04, 0x08, 0x10, 0x26, 0x2b, 0x32, 0x04, 0x05, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                                    },

                                                    /* 'bark2', 32x22px */
                                                    {
                                                        0x00, 0xe0, 0x10, 0x10, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x80, 0x40, 0x40, 0x2c, 0x14, 0x04, 0x08, 0x90, 0x18, 0x04, 0x08, 0xb0, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x04, 0x08, 0x10, 0x11, 0xf9, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xc0, 0x48, 0x28, 0x2a, 0x10, 0x0f, 0x20, 0x4a, 0x09, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x0c, 0x10, 0x20, 0x28, 0x37, 0x02, 0x02, 0x04, 0x08, 0x10, 0x26, 0x2b, 0x32, 0x04, 0x05, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                                    }};

    /* Sneak */
    static const char PROGMEM sneak[2][ANIM_SIZE] = {/* 'sneak1', 32x22px */
                                                     {
                                                         0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x40, 0x40, 0x40, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc0, 0x40, 0x40, 0x80, 0x00, 0x80, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1e, 0x21, 0xf0, 0x04, 0x02, 0x02, 0x02, 0x02, 0x03, 0x02, 0x02, 0x04, 0x04, 0x04, 0x03, 0x01, 0x00, 0x00, 0x09, 0x01, 0x80, 0x80, 0xab, 0x04, 0xf8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x1c, 0x20, 0x20, 0x3c, 0x0f, 0x11, 0x1f, 0x02, 0x06, 0x18, 0x20, 0x20, 0x38, 0x08, 0x10, 0x18, 0x04, 0x04, 0x02, 0x02, 0x01, 0x00, 0x00, 0x00, 0x00,
                                                     },

                                                     /* 'sneak2', 32x22px */
                                                     {
                                                         0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x40, 0x40, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xe0, 0xa0, 0x20, 0x40, 0x80, 0xc0, 0x20, 0x40, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3e, 0x41, 0xf0, 0x04, 0x02, 0x02, 0x02, 0x03, 0x02, 0x02, 0x02, 0x04, 0x04, 0x02, 0x01, 0x00, 0x00, 0x00, 0x04, 0x00, 0x40, 0x40, 0x55, 0x82, 0x7c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3f, 0x20, 0x30, 0x0c, 0x02, 0x05, 0x09, 0x12, 0x1e, 0x04, 0x18, 0x10, 0x08, 0x10, 0x20, 0x28, 0x34, 0x06, 0x02, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
                                                     }};

    /* animation */
    void animate_luna(void) {
        /* jump */
        if (isJumping || !showedJump) {
            /* clear */
            oled_set_cursor(LUNA_X, LUNA_Y + 2);
            oled_write("     ", false);

            oled_set_cursor(LUNA_X, LUNA_Y - 1);

            showedJump = true;
        } else {
            /* clear */
            oled_set_cursor(LUNA_X, LUNA_Y - 1);
            oled_write("     ", false);

            oled_set_cursor(LUNA_X, LUNA_Y);
        }

        /* switch frame */
        current_frame = (current_frame + 1) % 2;

        /* current status */
        if (led_usb_state.caps_lock) {
            oled_write_raw_P(bark[current_frame], ANIM_SIZE);

        } else if (isSneaking) {
            oled_write_raw_P(sneak[current_frame], ANIM_SIZE);

        } else if (current_wpm <= MIN_WALK_SPEED) {
            oled_write_raw_P(sit[current_frame], ANIM_SIZE);

        } else if (current_wpm <= MIN_RUN_SPEED) {
            oled_write_raw_P(walk[current_frame], ANIM_SIZE);

        } else {
            oled_write_raw_P(run[current_frame], ANIM_SIZE);
        }
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

/* KEYBOARD PET END */

void set_keylog(uint16_t keycode, keyrecord_t *record) {
    char name[18];
    memset(name, ' ', sizeof(name) - 1);
    name[sizeof(name) - 1] = '\0';

    if ((keycode >= QK_MOD_TAP && keycode <= QK_MOD_TAP_MAX) ||
        (keycode >= QK_LAYER_TAP && keycode <= QK_LAYER_TAP_MAX)) {
        keycode = keycode & 0xFF;
    }

    // Handle standard keycodes less than 60
    if (keycode < 60) {
        strncpy(name, code_to_name[keycode], sizeof(name) - 1);  
		
    } else if (keycode >= 28931 && keycode <= 29002) {
		
     // Calculate note number within the musical note range
    int note_number = keycode - 28931 + 24 + transpose_number + octave_number;
		
    // Update the name string with new line
     snprintf(name, sizeof(name), "NOTE  %s", midi_note_names[note_number]);

	//velocity
    } else if (keycode >= 49925 && keycode <= 50052) {
	velocity_number = (keycode - 49925);
    snprintf(name, sizeof(name), "VELOC %d", keycode - 49925);
	//program change	
    } else if (keycode >= 49792 && keycode <= 49919) {
        snprintf(name, sizeof(name), "PROGM %d", keycode - 49792);
		
	// MIDI Channel
	} else if (keycode >= 29043 && keycode <= 29058) {
	channel_number = keycode - 29042;
    snprintf(name, sizeof(name), "CHAN  %d", channel_number);

	
	} else if (keycode == 29060) {
		snprintf(name, sizeof(name), "CHAN  UP");
        // Decrease the channel number by 1
		channel_number++;
		if (channel_number < 0) {
            channel_number = 0;
        } else if (channel_number > 16) {
            channel_number = 16;
		}
		snprintf(name, sizeof(name),"CHAN UP");
		
	} else if (keycode == 29059) {
		snprintf(name, sizeof(name), "CHAN DOWN");
        // increase the channel number by 1
		channel_number--;
		if (channel_number < 0) {
            channel_number = 0;
        } else if (channel_number > 16) {
            channel_number = 16;
		}
		snprintf(name, sizeof(name),"CHAN DOWN");
		
	//octave value	
	} else if (keycode >= 29003 && keycode <= 29012) {
		octave_number = (keycode - 29005)*12;  // Adjusting for the range -6 to +6
        snprintf(name, sizeof(name), "OCTAV %+d", keycode - 29005);
		
	} else if (keycode >= 50053 && keycode <= 50068) {
        // Update sensitivity value based on the key
        sensitivity = keycode - 50052;  // Assuming the keycodes are consecutive
	    snprintf(name, sizeof(name), "STEP\n %d", keycode - 50053);
		
	} else if (keycode >= 29015 && keycode <= 29027) {
        // Handle special keycodes within the range
        // Update the special number based on the keycode
        transpose_number = keycode - 29015 - 6;  // Adjusting for the range -6 to +6
	    snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);
	
	 } else if (keycode == 29028) {
		snprintf(name, sizeof(name), "TRANSUP");
        // Decrease the special number by 1
        transpose_number--;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);

    } else if (keycode == 29029) {
	snprintf(name, sizeof(name), "TRANSDOWN");
        // Decrease the special number by 1
        transpose_number++;
		snprintf(name, sizeof(name), "%s", majorminor_note_names[transpose_number + 29]);
		
	} else if (keycode == QK_MIDI_VELOCITY_UP){
		 snprintf(name, sizeof(name), "VEL  UP");
			if (velocity_number == 0) {
                    velocity_number += (sensitivity);
               } else if ((velocity_number + (sensitivity)) <127) {
                    velocity_number += (sensitivity);
               } else if ((velocity_number + (sensitivity)) == 127) {
					velocity_number = 127;
               } else if ((velocity_number + (sensitivity)) >127){
					velocity_number = 127;
               }
		
    } else if (keycode == QK_MIDI_VELOCITY_DOWN){
		 snprintf(name, sizeof(name), "VEL  DOWN");
			if (velocity_number == 127) {
                    velocity_number -= (sensitivity);
                } else if ((velocity_number - (sensitivity)) > 0) {
                    velocity_number -= (sensitivity);
                } else if ((velocity_number - (sensitivity)) == 0) {
					velocity_number = 0;
                } else if ((velocity_number - (sensitivity)) < 0){
					velocity_number = 0;
                }

		
    } else if (keycode == 29013) {
	snprintf(name, sizeof(name), " OCT DOWN");
	octave_number-=12;
	
	} else if (keycode == 29014) {
	snprintf(name, sizeof(name), " OCT  UP");
	octave_number+=12;
		
    } else if (keycode >= 33152 && keycode <= 49535) {
        // Calculate CC number and index within the CC
        int cc_number = (keycode - 33152) / 128;
        int cc_index = (keycode - 33152) % 128;

        // Update the name string with new line
        snprintf(name, sizeof(name), "CC%-3d  %d", cc_number, cc_index);
	}
    // Handle CC UP and CC SENSITIVITY keys
    if (keycode >= 32896 && keycode <= 33023) {
        int cc_number = (keycode - 32896);  // Calculate CC# based on keycode

        // Check if it's a CC# UP key
        if (keycode >= 32896 && keycode <= 33023) {
            cc_updown_value[cc_number] += sensitivity;  // Increase CC UP (value 2) based on sensitivity
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
        cc_updown_value[cc_number] -= sensitivity;  // Decrease CC DOWN (value 2) based on sensitivity
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
    snprintf(keylog_str, sizeof(keylog_str), "%-18s", name);
}


void oled_render_keylog(void) {
	char name[100];
	snprintf(name, sizeof(name), "\n  TRANSPOSITION %+3d", transpose_number + octave_number);
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n     VELOCITY %3d", velocity_number);
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "\n   MIDI CHANNEL %2d\n\n", channel_number);
	snprintf(name + strlen(name), sizeof(name) - strlen(name), "     %s%s%s\n\n", getRootName(), getChordName(), getBassName());
    oled_write(name, false);
    oled_write(keylog_str, false);

}


bool process_record_user(uint16_t keycode, keyrecord_t *record) {
	  /* KEYBOARD PET STATUS START */
 switch (keycode) {
        case KC_LCTL:
        case KC_RCTL:
            if (record->event.pressed) {
                isSneaking = true;
            } else {
                isSneaking = false;
            }
            break;
        case KC_SPC:
            if (record->event.pressed) {
                isJumping  = true;
                showedJump = false;
            } else {
                isJumping = false;
            }
            break;
 }
            /* KEYBOARD PET STATUS END */

if (keycode >= 28931 && keycode <= 29002) {
		chordkey1 = keycode + transpose_number + octave_number;
		uint8_t channel  = midi_config.channel;
        uint8_t tone2     = keycode - MIDI_TONE_MIN + chordkey2 + transpose_number + octave_number;
		uint8_t tone3     = keycode - MIDI_TONE_MIN + chordkey3 + transpose_number + octave_number;
		uint8_t tone4     = keycode - MIDI_TONE_MIN + chordkey4 + transpose_number + octave_number;
		uint8_t tone5     = keycode - MIDI_TONE_MIN + chordkey5 + transpose_number + octave_number;
		uint8_t tone6     = keycode - MIDI_TONE_MIN + chordkey6 + transpose_number + octave_number;
        uint8_t velocity = midi_config.velocity;
        uint16_t combined_keycode2 = keycode + chordkey2;
        uint16_t combined_keycode3 = keycode + chordkey3;
		uint16_t combined_keycode4 = keycode + chordkey4;
		uint16_t combined_keycode5 = keycode + chordkey5;
		uint16_t combined_keycode6 = keycode + chordkey6;
		uint8_t chordnote_2 = midi_compute_note(combined_keycode2);
		uint8_t chordnote_3 = midi_compute_note(combined_keycode3);
		uint8_t chordnote_4 = midi_compute_note(combined_keycode4);
		uint8_t chordnote_5 = midi_compute_note(combined_keycode5);
		uint8_t chordnote_6 = midi_compute_note(combined_keycode6);

		if (chordkey2 != 0 && chordkey4 == 0 && chordkey5 == 0 && chordkey6 == 0) { 								// for 3 note smartchords on key press
            if (record->event.pressed) {
				midi_send_noteon(&midi_device, channel, chordnote_2, velocity);
                midi_send_noteon(&midi_device, channel, chordnote_3, velocity);
        dprintf("midi noteon channel:%d note:%d velocity:%d\n", channel, chordnote_3, velocity);

        tone2_status[1][tone2] += 1;
		tone3_status[1][tone3] += 1;
		smartchordkey2 = combined_keycode2 + octave_number + transpose_number + 21;
		smartchordkey3 = combined_keycode3 + octave_number + transpose_number + 21;
		trueheldkey1 = keycode - 28931 + 24 + transpose_number + octave_number;
		heldkey1 = ((trueheldkey1) % 12 + 12) % 12 + 1;
		heldkey1difference = (heldkey1 - 1) % 12;
		trueheldkey2 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey2;
		heldkey2 = ((trueheldkey2) % 12 + 12) % 12 + 1;
		    heldkey2difference = heldkey2 - heldkey1 + 1;
    if (heldkey2difference < 1) {
        heldkey2difference += 12;
    }
    else {}

		heldkey2difference = heldkey2 - heldkey1 + 1;
		trueheldkey3 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey3;
		heldkey3 = ((trueheldkey3) % 12 + 12) % 12 + 1;
		    heldkey3difference = heldkey3 - heldkey1 + 1;
    if (heldkey3difference < 1) {
        heldkey3difference += 12;
    }
    else {}


        if (tone2_status[0][tone2] == MIDI_INVALID_NOTE) {
            tone2_status[0][tone2] = chordnote_2;
        }
		} else { 																		//on key release
        tone2_status[1][tone2] -= 1;
		tone3_status[1][tone3] -= 1;{
				midi_send_noteoff(&midi_device, channel, combined_keycode2 + octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode2, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
				midi_send_noteoff(&midi_device, channel, combined_keycode3+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
		smartchordkey2 = 0;
		smartchordkey3 = 0;
		trueheldkey1 = 0;
		heldkey1 = 0;
		heldkey1difference = 0;
		trueheldkey2 = 0;
		heldkey2 = 0;
		heldkey2difference = 0;
		trueheldkey3 = 0;
		heldkey3 = 0;
		heldkey3difference = 0;
				}
			}
		}
		else if (chordkey2 != 0 && chordkey4 != 0 && chordkey5 == 0 && chordkey6 == 0) {					// for 4 note smartchords on key press
            if (record->event.pressed) {
				midi_send_noteon(&midi_device, channel, chordnote_2, velocity);
                midi_send_noteon(&midi_device, channel, chordnote_3, velocity);
				midi_send_noteon(&midi_device, channel, chordnote_4, velocity);
        dprintf("midi noteon channel:%d note:%d velocity:%d\n", channel, chordnote_3, velocity);

        tone2_status[1][tone2] += 1;
		tone3_status[1][tone3] += 1;
		tone4_status[1][tone4] += 1;
		smartchordkey2 = combined_keycode2 + octave_number + transpose_number + 21;
		smartchordkey3 = combined_keycode3 + octave_number + transpose_number + 21;
		smartchordkey4 = combined_keycode4 + octave_number + transpose_number + 21;
		trueheldkey1 = keycode - 28931 + 24 + transpose_number + octave_number;
		heldkey1 = ((trueheldkey1) % 12 + 12) % 12 + 1;
		heldkey1difference = (heldkey1 - 1) % 12;
		trueheldkey2 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey2;
		heldkey2 = ((trueheldkey2) % 12 + 12) % 12 + 1;
		heldkey2difference = heldkey2 - heldkey1 + 1;
    if (heldkey2difference < 1) {
        heldkey2difference += 12;
    }
    else {}

		trueheldkey3 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey3;
		heldkey3 = ((trueheldkey3) % 12 + 12) % 12 + 1;
		    heldkey3difference = heldkey3 - heldkey1 + 1;
    if (heldkey3difference < 1) {
        heldkey3difference += 12;
    }
    else {}

		trueheldkey4 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey4;
		heldkey4 = ((trueheldkey4) % 12 + 12) % 12 + 1;
		    heldkey4difference = heldkey4 - heldkey1 + 1;
    if (heldkey4difference < 1) {
        heldkey4difference += 12;
    }
    else {}


        if (tone2_status[0][tone2] == MIDI_INVALID_NOTE) {
            tone2_status[0][tone2] = chordnote_2;
        }
		}	else {

        tone2_status[1][tone2] -= 1;
		tone3_status[1][tone3] -= 1;
		tone4_status[1][tone4] -= 1; {
				midi_send_noteoff(&midi_device, channel, combined_keycode2 + octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode2, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
				midi_send_noteoff(&midi_device, channel, combined_keycode3+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
				midi_send_noteoff(&midi_device, channel, combined_keycode4+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
		smartchordkey2 = 0;
		smartchordkey3 = 0;
		smartchordkey4 = 0;
		trueheldkey1 = 0;
		heldkey1 = 0;
		heldkey1difference = 0;
		trueheldkey2 = 0;
		heldkey2 = 0;
		heldkey2difference = 0;
		trueheldkey3 = 0;
		heldkey3 = 0;
		heldkey3difference = 0;
		trueheldkey4 = 0;
		heldkey4 = 0;
		heldkey4difference = 0;
				}
			}
		}
		else if (chordkey2 != 0 && chordkey4 != 0 && chordkey5 != 0 && chordkey6 == 0) {						// for 5 note smartchords on key press
            if (record->event.pressed) {
				midi_send_noteon(&midi_device, channel, chordnote_2, velocity);
                midi_send_noteon(&midi_device, channel, chordnote_3, velocity);
				midi_send_noteon(&midi_device, channel, chordnote_4, velocity);
				midi_send_noteon(&midi_device, channel, chordnote_5, velocity);
        dprintf("midi noteon channel:%d note:%d velocity:%d\n", channel, chordnote_3, velocity);

        tone2_status[1][tone2] += 1;
		tone3_status[1][tone3] += 1;
		tone4_status[1][tone4] += 1;
		tone4_status[1][tone5] += 1;
		smartchordkey2 = combined_keycode2 + octave_number + transpose_number + 21;
		smartchordkey3 = combined_keycode3 + octave_number + transpose_number + 21;
		smartchordkey4 = combined_keycode4 + octave_number + transpose_number + 21;
		smartchordkey5 = combined_keycode5 + octave_number + transpose_number + 21;
		trueheldkey1 = keycode - 28931 + 24 + transpose_number + octave_number;
		heldkey1 = ((trueheldkey1) % 12 + 12) % 12 + 1;
		heldkey1difference = (heldkey1 - 1) % 12;
		trueheldkey2 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey2;
		heldkey2 = ((trueheldkey2) % 12 + 12) % 12 + 1;
		    heldkey2difference = heldkey2 - heldkey1 + 1;
    if (heldkey2difference < 1) {
        heldkey2difference += 12;
    }
    else {}

		trueheldkey3 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey3;
		heldkey3 = ((trueheldkey3) % 12 + 12) % 12 + 1;
		    heldkey3difference = heldkey3 - heldkey1 + 1;
    if (heldkey3difference < 1) {
        heldkey3difference += 12;
    }
    else {}

		trueheldkey4 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey4;
		heldkey4 = ((trueheldkey4) % 12 + 12) % 12 + 1;
		    heldkey4difference = heldkey4 - heldkey1 + 1;
    if (heldkey4difference < 1) {
        heldkey4difference += 12;
    }
    else {}

		trueheldkey5 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey5;
		heldkey5 = ((trueheldkey5) % 12 + 12) % 12 + 1;
		    heldkey5difference = heldkey5 - heldkey1 + 1;
    if (heldkey5difference < 1) {
        heldkey5difference += 12;
    }
    else {}


        if (tone2_status[0][tone2] == MIDI_INVALID_NOTE) {
            tone2_status[0][tone2] = chordnote_2;
        }
		}	else {

        tone2_status[1][tone2] -= 1;
		tone3_status[1][tone3] -= 1;
		tone4_status[1][tone4] -= 1;
		tone5_status[1][tone5] -= 1;	{
				midi_send_noteoff(&midi_device, channel, combined_keycode2 + octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode2, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
				midi_send_noteoff(&midi_device, channel, combined_keycode3+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
				midi_send_noteoff(&midi_device, channel, combined_keycode4+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
				midi_send_noteoff(&midi_device, channel, combined_keycode5+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
		smartchordkey2 = 0;
		smartchordkey3 = 0;
		smartchordkey4 = 0;
		smartchordkey5 = 0;
		trueheldkey1 = 0;
		heldkey1 = 0;
		heldkey1difference = (heldkey1 - 1) % 12;
		trueheldkey2 = 0;
		heldkey2 = 0;
		heldkey2difference = 0;
		trueheldkey3 = 0;
		heldkey3 = 0;
		heldkey3difference = 0;
		trueheldkey4 = 0;
		heldkey4 = 0;
		heldkey4difference = 0;
		trueheldkey5 = 0;
		heldkey5 = 0;
		heldkey5difference = 0;
				}
			}
		}
	else if (chordkey2 != 0 && chordkey4 != 0 && chordkey5 != 0 && chordkey6 != 0) {						// for 6 note smartchords on key press
            if (record->event.pressed) {
				midi_send_noteon(&midi_device, channel, chordnote_2, velocity);
                midi_send_noteon(&midi_device, channel, chordnote_3, velocity);
				midi_send_noteon(&midi_device, channel, chordnote_4, velocity);
				midi_send_noteon(&midi_device, channel, chordnote_5, velocity);
				midi_send_noteon(&midi_device, channel, chordnote_6, velocity);
        dprintf("midi noteon channel:%d note:%d velocity:%d\n", channel, chordnote_3, velocity);

        tone2_status[1][tone2] += 1;
		tone3_status[1][tone3] += 1;
		tone4_status[1][tone4] += 1;
		tone5_status[1][tone5] += 1;
		tone6_status[1][tone6] += 1;
		smartchordkey2 = combined_keycode2 + octave_number + transpose_number + 21;
		smartchordkey3 = combined_keycode3 + octave_number + transpose_number + 21;
		smartchordkey4 = combined_keycode4 + octave_number + transpose_number + 21;
		smartchordkey5 = combined_keycode5 + octave_number + transpose_number + 21;
		smartchordkey6 = combined_keycode6 + octave_number + transpose_number + 21;
		trueheldkey1 = keycode - 28931 + 24 + transpose_number + octave_number;
		heldkey1 = ((trueheldkey1) % 12 + 12) % 12 + 1;
		heldkey1difference = (heldkey1 - 1) % 12;
		trueheldkey2 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey2;
		heldkey2 = ((trueheldkey2) % 12 + 12) % 12 + 1;
		    heldkey2difference = heldkey2 - heldkey1 + 1;
    if (heldkey2difference < 1) {
        heldkey2difference += 12;
    }
    else {}

		trueheldkey3 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey3;
		heldkey3 = ((trueheldkey3) % 12 + 12) % 12 + 1;
		    heldkey3difference = heldkey3 - heldkey1 + 1;
    if (heldkey3difference < 1) {
        heldkey3difference += 12;
    }
    else {}

		trueheldkey4 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey4;
		heldkey4 = ((trueheldkey4) % 12 + 12) % 12 + 1;
		    heldkey4difference = heldkey4 - heldkey1 + 1;
    if (heldkey4difference < 1) {
        heldkey4difference += 12;
    }
    else {}

		trueheldkey5 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey5;
		heldkey5 = ((trueheldkey5) % 12 + 12) % 12 + 1;
		    heldkey5difference = heldkey5 - heldkey1 + 1;
    if (heldkey5difference < 1) {
        heldkey5difference += 12;
    }
    else {}

		trueheldkey6 = keycode - 28931 + 24 + transpose_number + octave_number + chordkey6;
		heldkey6 = ((trueheldkey6) % 12 + 12) % 12 + 1;
		    heldkey5difference = heldkey5 - heldkey1 + 1;
    if (heldkey5difference < 1) {
        heldkey5difference += 12;
    }
    else {}


        if (tone2_status[0][tone2] == MIDI_INVALID_NOTE) {
            tone2_status[0][tone2] = chordnote_2;
        }
		}	else {

        tone2_status[1][tone2] -= 1;
		tone3_status[1][tone3] -= 1;
		tone4_status[1][tone4] -= 1;
		tone5_status[1][tone5] -= 1;
		tone6_status[1][tone6] -= 1;		{
				midi_send_noteoff(&midi_device, channel, combined_keycode2 + octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode2, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
				midi_send_noteoff(&midi_device, channel, combined_keycode3+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
				midi_send_noteoff(&midi_device, channel, combined_keycode4+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
				midi_send_noteoff(&midi_device, channel, combined_keycode5+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
				midi_send_noteoff(&midi_device, channel, combined_keycode6+ octave_number + transpose_number + 21, velocity);
            dprintf("midi noteoff channel:%d note:%d velocity:%d\n", channel, combined_keycode3, velocity);
            tone2_status[0][tone2] = MIDI_INVALID_NOTE;
		smartchordkey2 = 0;
		smartchordkey3 = 0;
		smartchordkey4 = 0;
		smartchordkey5 = 0;
		smartchordkey6 = 0;
		trueheldkey1 = 0;
		heldkey1 = 0;
		heldkey1difference = (heldkey1 - 1) % 12;
		trueheldkey2 = 0;
		heldkey2 = 0;
		heldkey2difference = 0;
		trueheldkey3 = 0;
		heldkey3 = 0;
		heldkey3difference = 0;
		trueheldkey4 = 0;
		heldkey4 = 0;
		heldkey4difference = 0;
		trueheldkey5 = 0;
		heldkey5 = 0;
		heldkey5difference = 0;
		trueheldkey6 = 0;
		heldkey6 = 0;
		heldkey6difference = 0;
				}
			}
		}
	
    if (record->event.pressed) {
	} else {
		if (smartchordstatus == 0) {
		if (smartchordkey2 != 0) {
        midi_send_noteoff(&midi_device, channel, smartchordkey2, velocity);
        smartchordkey2 = 0;
		}
		if (smartchordkey3 != 0) {
        midi_send_noteoff(&midi_device, channel, smartchordkey3, velocity);
        smartchordkey3 = 0;
		}
		if (smartchordkey4 != 0) {
        midi_send_noteoff(&midi_device, channel, smartchordkey4, velocity);
        smartchordkey4 = 0;
		}
		if (smartchordkey5 != 0) {
        midi_send_noteoff(&midi_device, channel, smartchordkey5, velocity);
        smartchordkey4 = 0;
		}
	}
}
}

if (keycode >= 0xC420 && keycode <= 0xC428) {
	 if (record->event.pressed) {
        smartchordstatus = 1;
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

	
if (keycode >= 28931 && keycode <= 29002) {

        if (record->event.pressed) {
            if (heldkey1 == 0 && heldkey2 == 0 && heldkey3 == 0 && heldkey4 == 0 && heldkey5 == 0) {
                trueheldkey1 = keycode - 28931 + 24 + transpose_number + octave_number;
				heldkey1 = ((trueheldkey1) % 12 + 12) % 12 + 1;
				heldkey1difference = (heldkey1 - 1) % 12;
				if (heldkey1 == heldkey2 || heldkey1 == heldkey3 || heldkey1 == heldkey4 || heldkey1 == heldkey5 || heldkey1 == heldkey6) {
				heldkey2 = 0;
				trueheldkey2 = 0;
				heldkey2difference = 0;
				}
            } else if (heldkey1 != 0 && heldkey1 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey2 == 0 && heldkey3 == 0 && heldkey4 == 0 && heldkey5 == 0 && heldkey6 == 0) {
                trueheldkey2 = keycode - 28931 + 24 + transpose_number + octave_number;
				heldkey2 = ((trueheldkey2) % 12 + 12) % 12 + 1;
				    heldkey2difference = heldkey2 - heldkey1 + 1;
    if (heldkey2difference < 1) {
        heldkey2difference += 12;
    }
    else {}

				if (heldkey2 == heldkey1 || heldkey2 == heldkey3 || heldkey2 == heldkey4 || heldkey2 == heldkey5 || heldkey2 == heldkey6) {
				heldkey2 = 0;
				trueheldkey2 = 0;
				heldkey2difference = 0;
				}
            } else if (heldkey1 != 0 && heldkey1 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey2 != 0 && heldkey2 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey3 == 0 && heldkey4 == 0 && heldkey5 == 0 && heldkey6 == 0) {
                trueheldkey3 = keycode - 28931 + 24 + transpose_number + octave_number;
				heldkey3 = ((trueheldkey3) % 12 + 12) % 12 + 1;
				    heldkey3difference = heldkey3 - heldkey1 + 1;
    if (heldkey3difference < 1) {
        heldkey3difference += 12;
    }
    else {}

				if (heldkey3 == heldkey1 || heldkey3 == heldkey2 || heldkey3 == heldkey4 || heldkey3 == heldkey5 || heldkey3 == heldkey6) {
				heldkey3 = 0;
				trueheldkey3 = 0;
				heldkey2difference = 0;
				}
            } else if (heldkey1 != 0 && heldkey1 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey2 != 0 && heldkey2 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey3 != 0 && heldkey3 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey4 == 0 && heldkey5 == 0 && heldkey6 == 0) {
                trueheldkey4 = keycode - 28931 + 24 + transpose_number + octave_number;
				heldkey4 = ((trueheldkey4) % 12 + 12) % 12 + 1;
				    heldkey4difference = heldkey4 - heldkey1 + 1;
    if (heldkey4difference < 1) {
        heldkey4difference += 12;
    }
    else {}

				if (heldkey4 == heldkey1 || heldkey4 == heldkey2 || heldkey4 == heldkey3 || heldkey4 == heldkey5 || heldkey4 == heldkey6) {
				heldkey4 = 0;
				trueheldkey4 = 0;
				heldkey4difference = 0;
				}
            } else if (heldkey1 != 0 && heldkey1 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey2 != 0 && heldkey2 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey3 != 0 && heldkey3 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey4 != 0 && heldkey4 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey5 == 0 && heldkey6 == 0) {
                trueheldkey5 = keycode - 28931 + 24 + transpose_number + octave_number;
				heldkey5 = ((trueheldkey5) % 12 + 12) % 12 + 1;
				    heldkey5difference = heldkey5 - heldkey1 + 1;
    if (heldkey5difference < 1) {
        heldkey5difference += 12;
    }
    else {}

				if (heldkey5 == heldkey1 || heldkey5 == heldkey2 || heldkey5 == heldkey3 || heldkey5 == heldkey4 || heldkey5 == heldkey6) {
				heldkey5 = 0;
				trueheldkey5 = 0;
				heldkey5difference = 0;
				}
            } else if (heldkey1 != 0 && heldkey1 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey2 != 0 && heldkey2 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey3 != 0 && heldkey3 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey4 != 0 && heldkey4 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey5 != 0 && heldkey5 != (keycode - 28931 + 24 + transpose_number + octave_number) && heldkey6 == 0) {
                trueheldkey6 = keycode - 28931 + 24 + transpose_number + octave_number;
				heldkey6 = ((trueheldkey6) % 12 + 12) % 12 + 1;
				    heldkey6difference = heldkey6 - heldkey1 + 1;
    if (heldkey6difference < 1) {
        heldkey6difference += 12;
    }
    else {}

				if (heldkey6 == heldkey1 || heldkey6 == heldkey2 || heldkey6 == heldkey3 || heldkey6 == heldkey4 || heldkey6 == heldkey5) {
				heldkey6 = 0;
				trueheldkey6 = 0;
				heldkey6difference = 0;
				}
            }
			
				
} else {
    chordkey1 = 0;

    if (heldkey1 == ((keycode - 28931 + 24 + transpose_number + octave_number) % 12 + 12) % 12 + 1) {
        if (heldkey2 != 0) {
            heldkey1 = heldkey2;
			heldkey1difference = 1;
            heldkey2 = 0;
			heldkey2difference = 0;
			trueheldkey1 = trueheldkey2;
            trueheldkey2 = 0;
        } else {
            heldkey1 = 0;
			heldkey1difference = 0;
			trueheldkey1 = 0;
			rootnote = 13;
			bassnote = 13;
        }
    } else if (heldkey2 == ((keycode - 28931 + 24 + transpose_number + octave_number) % 12 + 12) % 12 + 1) {
        if (heldkey3 != 0) {
            heldkey2 = heldkey3;
			heldkey2difference = heldkey3difference;
            heldkey3 = 0;
			heldkey3difference = 0;
			trueheldkey2 = trueheldkey3;
            trueheldkey3 = 0;
        } else {
            heldkey2 = 0;
			heldkey2difference = 0;
			trueheldkey2 = 0;
        }
    } else if (heldkey3 == ((keycode - 28931 + 24 + transpose_number + octave_number) % 12 + 12) % 12 + 1) {
        if (heldkey4 != 0) {
            heldkey3 = heldkey4;
			heldkey3difference = heldkey4difference;
            heldkey4 = 0;
			heldkey4difference = 0;
			trueheldkey3 = trueheldkey4;
            trueheldkey4 = 0;
        } else {
            heldkey3 = 0;
			heldkey3difference = 0;
			trueheldkey3 = 0;
        }
    } else if (heldkey4 == ((keycode - 28931 + 24 + transpose_number + octave_number) % 12 + 12) % 12 + 1) {
        if (heldkey5 != 0) {
            heldkey4 = heldkey5;
			heldkey4difference = heldkey5difference;
            heldkey5 = 0;
			heldkey5difference = 0;
			trueheldkey4 = trueheldkey5;
            trueheldkey5 = 0;
        } else {
            heldkey4 = 0;
			heldkey4difference = 0;
			trueheldkey4 = 0;
        }
    } else if (heldkey5 == ((keycode - 28931 + 24 + transpose_number + octave_number) % 12 + 12) % 12 + 1) {
        if (heldkey6 != 0) {
            heldkey5 = heldkey6;
			heldkey5difference = heldkey6difference;
            heldkey6 = 0;
			heldkey6difference = 0;
			trueheldkey5 = trueheldkey6;
            trueheldkey6 = 0;
        } else {
            heldkey5 = 0;
			heldkey5difference = 0;
			trueheldkey5 = 0;
        }
    } else if (heldkey6 == ((keycode - 28931 + 24 + transpose_number + octave_number) % 12 + 12) % 12 + 1) {
        heldkey6 = 0;
		heldkey6difference = 0;
		trueheldkey6 = 0;
    }
}
}

	/////////////////////////////////////////// SMART CHORD///////////////////////////////////////////////////////////
if (keycode >= 0xC396 && keycode <= 0xC416) {
	 if (record->event.pressed) {
        smartchordstatus = 1;
		 switch (keycode) {
		case 0xC396:    // Major Chord
            chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 0;
			chordkey5 = 0;
break;
		case 0xC397:   // Minor Chord		
            chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 0;
			chordkey5 = 0;
 break;
		case 0xC398:   // Diminished
            chordkey2 = 3;   // Minor Third
			chordkey3 = 6;   // Diminished fifth
			chordkey4 = 0;
			chordkey5 = 0;
 break;
		case 0xC39A:   // Augmented
            chordkey2 = 4;   // Major Third
			chordkey3 = 8;	// Augmented fifth
			chordkey4 = 0;
			chordkey5 = 0;
 break;
		case 0xC39B:   // Sus2
            chordkey2 = 2;	 // Major Second
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 0;
			chordkey5 = 0;
 break;
		case 0xC39C:    // Sus4
            chordkey2 = 5;   // Perfect fourth
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 0;
			chordkey5 = 0;
 break;
		case 0xC39D:    // Maj6								
            chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 9;   // Major 6th
			chordkey5 = 0;
 break;
		 case 0xC39E:    // Min6
            chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 9;   // Major 6th
			chordkey5 = 0;
 break;
		case 0xC39F:    // Maj7											/////// INTERMEDIATE CHORDS ////////
            chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 11;
			chordkey5 = 0;
 break;
		case 0xC3A0:    // Min7
            chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;   // Minor Seventh
			chordkey5 = 0;
 break;
		case 0xC3A1:    // Dom7
            chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;   // Minor Seventh
			chordkey5 = 0;
break;
		case 0xC3A2:    // Diminished 7th (dim7)					
			chordkey2 = 3;   // Minor Third
			chordkey3 = 6;   // Diminished Fifth
			chordkey4 = 9;   // Diminished Seventh
			chordkey5 = 0;  
break;
		case 0xC3A3:    // Half-Diminished 7th (ø7) (m7b5)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 6;   // Diminished Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 0;  
break;
		case 0xC3A4:    // Augmented 7th (7#5)
			chordkey2 = 4;   // Major Third
			chordkey3 = 8;   // Augmented Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 0;
break;
		case 0xC3A5:    // Major9 (maj9)
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 11;  // Major Seventh
			chordkey5 = 14;  // Major Ninth
break;
		case 0xC3A6:    // Minor 9 (min9)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 14;  // Major Ninth 
break;
		case 0xC3A7:    // Dominant 9 (dom9)
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 14;  // Major Ninth 
break;			
		case 0xC3A8:    // Major add2 (majadd2)								//ADVANCED CHORDS
			chordkey2 = 2;   // Major Second
			chordkey3 = 4;   // Major Third
			chordkey4 = 7;   // Perfect Fifth
			chordkey5 = 0;   // No additional note
break;
		case 0xC3A9:    // Minor add2 (madd2)
			chordkey2 = 2;   // Major Second
			chordkey3 = 3;   // Minor Third
			chordkey4 = 7;   // Perfect Fifth
			chordkey5 = 0;   // No additional note
break;
		case 0xC3AA:    // Major add4 (majadd4)
			chordkey2 = 4;   // Major Third
			chordkey3 = 5;   // Perfect Fourth
			chordkey4 = 7;   // Perfect Fifth
			chordkey5 = 0;   // No additional note
break;
		case 0xC3AB:    // Minor add4 (madd4)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 5;   // Perfect Fourth
			chordkey4 = 7;   // Perfect Fifth
			chordkey5 = 0;   // No additional note
break;		
		case 0xC3AC:    // Major 6/9
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 9;   // Major Sixth
			chordkey5 = 14;  // Major Ninth
			chordkey6 = 0;   // No additional note
break;
		case 0xC3AD:    // Minor 6/9
			chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 9;   // Major Sixth
			chordkey5 = 14;  // Major Ninth
			chordkey6 = 0;   // No additional note
break;				
		case 0xC3AE:    // Minor Major 7th (m(maj7))
			chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 11;  // Major Seventh
			chordkey5 = 0;   // No additional note
break;
		case 0xC3AF:    // Major 7sus4 (maj7sus4)
			chordkey2 = 5;   // Perfect fourth
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 11;  // Major Seventh
			chordkey5 = 0;   // No additional note
break;
		case 0xC3B0:    // Dominant 7sus4 (7sus4)
			chordkey2 = 5;   // Perfect fourth
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 0;   // No additional note
break;
		case 0xC3B1:    // Major 7sus2 (maj7sus2)
			chordkey2 = 2;   // Major Second
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 11;  // Major Seventh
			chordkey5 = 0;   // No additional note
break;
		case 0xC3B2:    // Dominant 7sus2 (7sus2)
			chordkey2 = 2;   // Major Second
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 0;   // No additional note
break;
		case 0xC3B3:    // Major 7th with Raised 5 (maj7#5)
			chordkey2 = 4;   // Major Third
			chordkey3 = 8;   // Augmented Fifth
			chordkey4 = 11;  // Major Seventh
			chordkey5 = 0;   // No additional note
break;

		case 0xC3B4:    // Minor 7th with Raised 5 (m7#5)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 8;   // Augmented Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 0;   // No additional note
break;

		case 0xC3B5:    // Major 7th with Lowered 5 (maj7b5)
			chordkey2 = 4;   // Major Third
			chordkey3 = 6;   // Diminished Fifth
			chordkey4 = 11;  // Major Seventh
			chordkey5 = 0;   // No additional note
break;

		case 0xC3B6:    // Dominant 7th with Lowered 5 (7b5)
			chordkey2 = 4;   // Major Third
			chordkey3 = 6;   // Diminished Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 0;   // No additional note
break;
		case 0xC3B7:    // Major 7th with no 5 (7no5)
			chordkey2 = 4;   // Major Third
			chordkey3 = 11;  // Major Seventh
			chordkey4 = 0;   // No additional note
			chordkey5 = 0;   // No additional note
break;			
		case 0xC3B8:    // Minor 7th with no 5 (7no5)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 10;  // Minor Seventh
			chordkey4 = 0;   // No additional note
			chordkey5 = 0;   // No additional note
break;			
		case 0xC3B9:    // Dominant 7th with no 5 (7no5)
			chordkey2 = 4;   // Minor Third
			chordkey3 = 10;  // Minor Seventh
			chordkey4 = 0;   // No additional note
			chordkey5 = 0;   // No additional note
break;	
		case 0xC3BA:    // Major add9 (add9)
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 14;  // Major Ninth
			chordkey5 = 0;   // No eleventh
			chordkey6 = 0;   // No thirteenth
break;
		case 0xC3BB:    // Minor add9 (madd9)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 14;  // Major Ninth
			chordkey5 = 0;   // No eleventh
			chordkey6 = 0;   // No thirteenth
break;
		case 0xC3BC:    // Diminished 9 (dim9)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 6;   // Diminished Fifth
			chordkey4 = 9;  // Diminished Seventh
			chordkey5 = 14;  // Major Ninth 
break;
		case 0xC3BD:    // Half-Diminished 9 (ø9)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 6;   // Diminished Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 14;  // Major Ninth 
break;
		case 0xC3BE:    // Augmented 9th (9#5)
			chordkey2 = 4;   // Major Third
			chordkey3 = 8;   // Augmented Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 14;  // Major Ninth
break;
		case 0xC3C9:    // Dominant7#9#5 (7#9#5)
			chordkey2 = 4;   // Major Third
			chordkey3 = 8;   // Augmented Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 15;  // Sharp Ninth 
break;
		case 0xC3BF:    // Major 11 (maj11)
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 11;  // Major Seventh
			chordkey5 = 14;  // Major Ninth 
			chordkey6 = 17;  // Perfect Eleventh
break;
		case 0xC3C0:    // Minor 11 (min11)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 14;  // Major Ninth 
			chordkey6 = 17;  // Perfect Eleventh
break;
		case 0xC3C1:    // Dominant 11 (dom11)
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 14;  // Major Ninth 
			chordkey6 = 17;  // Perfect Eleventh
break;
		case 0xC3C2:    // Major add11 (add11))
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 17;  // Perfect Eleventh
			chordkey5 = 0;
			chordkey6 = 0;
break;
		case 0xC3C3:    // Minor add11 (madd11))
			chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 17;  // Perfect Eleventh
			chordkey5 = 0;
			chordkey6 = 0;
break;
		case 0xC3C4:    // Major 7th add11 (maj7(add11))
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 11;  // Major Seventh
			chordkey5 = 17;  // Perfect Eleventh
			chordkey6 = 0;
break;
		case 0xC3C5:    // Minor 7th add11 (m7(add11))
			chordkey2 = 3;   // Minor Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 17;  // Perfect Eleventh
			chordkey6 = 0;
break;
		case 0xC3C6:    // Dominant 7th add11 (7(add11))
			chordkey2 = 4;   // Major Third
			chordkey3 = 7;   // Perfect Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 17;  // Perfect Eleventh
			chordkey6 = 0;
break;
		case 0xC3C7:    // Diminished 11 (dim11)
 		   chordkey2 = 3;   // Minor Third
			chordkey3 = 6;   // Diminished Fifth
			chordkey4 = 9;   // Diminished Seventh
			chordkey5 = 14;  // Major Ninth 
			chordkey6 = 17;  // Perfect Eleventh
break;
		case 0xC3C8:    // Half-Diminished 11 (ø11)
			chordkey2 = 3;   // Minor Third
			chordkey3 = 6;   // Diminished Fifth
			chordkey4 = 10;  // Minor Seventh
			chordkey5 = 14;  // Major Ninth 
			chordkey6 = 17;  // Perfect Eleventh


		 }
		if (inversionposition == 1) {
			if (chordkey2 != 0) {
				chordkey2 -= 12;
				}
			if (chordkey3 != 0) {
				chordkey3 -= 12;
				}
			if (chordkey4 != 0) {
				chordkey4 -= 12;
				}
			if (chordkey5 != 0) {
				chordkey5 -= 12;
				}
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
			}
			
		else if (inversionposition == 2) {
			if (chordkey3 != 0) {
				chordkey3 -= 12;
				}
			if (chordkey4 != 0) {
				chordkey4 -= 12;
				}
			if (chordkey5 != 0) {
				chordkey5 -= 12;
				}
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
			}
			
		else if (inversionposition == 3) {
			if (chordkey4 != 0) {
				chordkey4 -= 12;
			}
			if (chordkey5 != 0) {
				chordkey5 -= 12;
				}
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
		}
				
		else if (inversionposition == 4) {
			if (chordkey5 != 0) {
				chordkey5 -= 12;
				}
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
		}		
		else if (inversionposition == 5) {
			if (chordkey6 != 0) {
				chordkey6 -= 12;
				}
		}
		
    } else {
        smartchordstatus = 0;
        chordkey2 = 0;
        chordkey3 = 0;
        chordkey4 = 0;
        chordkey5 = 0;
		chordkey6 = 0;
		trueheldkey2 = 0;
		heldkey2 = 0;
		heldkey2difference = 0;
		trueheldkey3 = 0;
		heldkey3 = 0;
		heldkey3difference = 0;
		trueheldkey4 = 0;
		heldkey4 = 0;
		heldkey4difference = 0;
		trueheldkey5 = 0;
		heldkey5 = 0;
		heldkey5difference = 0;
		trueheldkey6 = 0;
		heldkey6 = 0;
		heldkey6difference = 0;
		rootnote = 13;
		bassnote = 13;
    }
}

	
 if (record->event.pressed) {
    set_keylog(keycode, record);
  
    } else if (!record->event.pressed) {

        return true;
    }
	

if (keycode >= MI_CC_TOG_0 && keycode < (MI_CC_TOG_0 + 128)) { // CC TOGGLE
        uint8_t cc = keycode - MI_CC_TOG_0;

        if (CCValue[cc]) {
            CCValue[cc] = 0;
        } else {
            CCValue[cc] = 127;
        }
        midi_send_cc(&midi_device, midi_config.channel, cc, CCValue[cc]);

        //sprintf(status_str, "CC\nTog\n%d", cc);

    } else if (keycode >= MI_CC_UP_0 && keycode < (MI_CC_UP_0 + 128)) { // CC ++
        uint8_t cc = keycode - MI_CC_UP_0;

        if (CCValue[cc] < 127) {
            if (record->event.key.row == KEYLOC_ENCODER_CW) {
                CCValue[cc] += encoder_step;
                if (CCValue[cc] > 127) {
                    CCValue[cc] = 127;
                }
            } else {
                ++CCValue[cc];
            }
        }
		

        midi_send_cc(&midi_device, midi_config.channel, cc, CCValue[cc]);

        // sprintf(status_str, "CC\nUp\n%d", cc);
		


    } else if (keycode >= MI_CC_DWN_0 && keycode < (MI_CC_DWN_0 + 128)) { // CC --
        uint8_t cc = keycode - MI_CC_DWN_0;

        if (CCValue[cc] > 0) {
            if (record->event.key.row == KEYLOC_ENCODER_CCW) {
                if (CCValue[cc] >= encoder_step) {
                    CCValue[cc] -= encoder_step;
                } else {
                    CCValue[cc] = 0;
                }

            } else {
                --CCValue[cc];
            }
        }
        midi_send_cc(&midi_device, midi_config.channel, cc, CCValue[cc]);

        //sprintf(status_str, "CC\nDown\n%d", cc);
    } else if (keycode == QK_MIDI_VELOCITY_DOWN){
			if (record->event.key.row == KEYLOC_ENCODER_CW && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (sensitivity - 1);
                } else if ((midi_config.velocity - (sensitivity - 1)) > 0) {
                    midi_config.velocity -= (sensitivity - 1);
                } else if ((midi_config.velocity - (sensitivity - 1)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (sensitivity - 1)) < 0){
					midi_config.velocity = 0;
                }
			}else if (record->event.key.row == KEYLOC_ENCODER_CCW && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (sensitivity - 1);
                } else if ((midi_config.velocity - (sensitivity - 1)) > 0) {
                    midi_config.velocity -= (sensitivity - 1);
                } else if ((midi_config.velocity - (sensitivity - 1)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (sensitivity - 1)) < 0){
					midi_config.velocity = 0;
                }
            }else if (record->event.pressed && midi_config.velocity > 0) {
				if (midi_config.velocity == 127) {
                    midi_config.velocity -= (sensitivity - 1);
                } else if ((midi_config.velocity - (sensitivity - 1)) > 0) {
                    midi_config.velocity -= (sensitivity - 1);
                } else if ((midi_config.velocity - (sensitivity - 1)) == 0) {
					midi_config.velocity = 0;
                } else if ((midi_config.velocity - (sensitivity - 1)) < 0){
					midi_config.velocity = 0;
                }

                dprintf("midi velocity %d\n", midi_config.velocity);
            }
    } else if (keycode == QK_MIDI_VELOCITY_UP){
			if (record->event.key.row == KEYLOC_ENCODER_CW && midi_config.velocity > 0) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (sensitivity + 1);
                } else if ((midi_config.velocity + (sensitivity + 1)) <127) {
                    midi_config.velocity += (sensitivity + 1);
                } else if ((midi_config.velocity + (sensitivity + 1)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (sensitivity + 1)) >127){
					midi_config.velocity = 127;
                }
			}else if (record->event.key.row == KEYLOC_ENCODER_CCW && midi_config.velocity > 0) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (sensitivity + 1);
                } else if ((midi_config.velocity + (sensitivity + 1)) <127) {
                    midi_config.velocity += (sensitivity + 1);
                } else if ((midi_config.velocity + (sensitivity + 1)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (sensitivity + 1)) >127){
					midi_config.velocity = 127;
                }
            }else if (record->event.pressed && midi_config.velocity > 0) {
				if (midi_config.velocity == 0) {
                    midi_config.velocity += (sensitivity + 1);
                } else if ((midi_config.velocity + (sensitivity + 1)) <127) {
                    midi_config.velocity += (sensitivity + 1);
                } else if ((midi_config.velocity + (sensitivity + 1)) == 127) {
					midi_config.velocity = 127;
                } else if ((midi_config.velocity + (sensitivity + 1)) >127){
					midi_config.velocity = 127;
                }

                dprintf("midi velocity %d\n", midi_config.velocity);
            }

    } else if (keycode >= MI_CC_0_0 && keycode < (MI_CC_0_0 + 128 * 128)) { // CC FIXED
        uint8_t cc  = (keycode - MI_CC_0_0) / 128;
        uint8_t val = (keycode - MI_CC_0_0) % 128;

        CCValue[cc] = val;
        midi_send_cc(&midi_device, midi_config.channel, cc, CCValue[cc]);

        //sprintf(status_str, "CC\n%d\n%d", cc, val);

    } else if (keycode >= MI_BANK_MSB_0 && keycode < (MI_BANK_MSB_0 + 128)) { // BANK MSB
        uint8_t val = keycode - MI_BANK_MSB_0;
        uint8_t cc  = BANK_SEL_MSB_CC;

        CCValue[cc] = val;
        midi_send_cc(&midi_device, midi_config.channel, cc, CCValue[cc]);

        MidiCurrentBank &= 0x00FF;
        MidiCurrentBank |= val << 8;

        //sprintf(status_str, "MSB\nbank\n%d", val);

    } else if (keycode >= MI_BANK_LSB_0 && keycode < (MI_BANK_LSB_0 + 128)) { // BANK LSB
        uint8_t val = keycode - MI_BANK_LSB_0;
        uint8_t cc  = BANK_SEL_LSB_CC;

        CCValue[cc] = val;
        midi_send_cc(&midi_device, midi_config.channel, cc, CCValue[cc]);

        MidiCurrentBank &= 0xFF00;
        MidiCurrentBank |= val;

        //sprintf(status_str, "LSB\nbank\n%d", val);

    } else if (keycode >= MI_PROG_0 && keycode < (MI_PROG_0 + 128)) { // PROG CHANGE
        uint8_t val = keycode - MI_PROG_0;

        midi_send_programchange(&midi_device, midi_config.channel, val);
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
                midi_send_cc(&midi_device, midi_config.channel, BANK_SEL_LSB_CC, lsb);
                midi_send_cc(&midi_device, midi_config.channel, BANK_SEL_MSB_CC, msb);

                break;
            case MI_BANK_DWN:
                if (MidiCurrentBank > 0) {
                    --MidiCurrentBank;
                }
                //sprintf(status_str, "bank\n%d", MidiCurrentBank);
                uint8_t lsb = MidiCurrentBank & 0xFF;
                uint8_t msb = (MidiCurrentBank & 0xFF00) >> 8;
                midi_send_cc(&midi_device, midi_config.channel, BANK_SEL_LSB_CC, lsb);
                midi_send_cc(&midi_device, midi_config.channel, BANK_SEL_MSB_CC, msb);
                break;
            case MI_PROG_UP:
                if (MidiCurrentProg < 127) {
                    ++MidiCurrentProg;
                }
                //sprintf(status_str, "PC\n%d", MidiCurrentProg);
                midi_send_programchange(&midi_device, midi_config.channel, MidiCurrentProg);
                break;
            case MI_PROG_DWN:
                if (MidiCurrentProg > 0) {
                    --MidiCurrentProg;
                }
                //sprintf(status_str, "PC\n%d", MidiCurrentProg);
                midi_send_programchange(&midi_device, midi_config.channel, MidiCurrentProg);
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

    uint8_t layer   = get_highest_layer(layer_state|default_layer_state);
    char    str[79] = "";
    sprintf(str, "      LAYER %-3d", layer);

    oled_write_P(str, false);
	
	// render keylog
    oled_render_keylog();

 /* KEYBOARD PET VARIABLES START */

    current_wpm   = get_current_wpm();
    led_usb_state = host_keyboard_led_state();

    /* KEYBOARD PET VARIABLES END */

    // Host Keyboard LED Status
    //led_t led_state = host_keyboard_led_state();
    //oled_write_P(led_state.num_lock ? PSTR(" NUM \n") : PSTR("\n"), false);
    //oled_write_P(led_state.caps_lock ? PSTR(" CAP \n") : PSTR("\n"), false);
    //oled_write_P(led_state.scroll_lock ? PSTR(" SCR \n") : PSTR("\n"), false);
	

	    /* KEYBOARD PET RENDER START */

    render_luna(0, 13);




    /* KEYBOARD PET RENDER END */
	


    return false;
}