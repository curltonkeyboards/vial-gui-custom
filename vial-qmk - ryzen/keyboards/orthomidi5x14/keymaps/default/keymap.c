// Copyright 2023 QMK
// SPDX-License-Identifier: GPL-2.0-or-later

#include QMK_KEYBOARD_H



#if defined(ENCODER_MAP_ENABLE)
const uint16_t PROGMEM encoder_map[][NUM_ENCODERS][2] = {
    [0] =   { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU)  },
    [1] =   { ENCODER_CCW_CW(MI_CC_40_DWN, MI_CC_40_UP),            ENCODER_CCW_CW(MI_CC_47_DWN, MI_CC_47_UP)  },
    [2] =   { ENCODER_CCW_CW(MI_CC_42_DWN, MI_CC_42_UP),            ENCODER_CCW_CW(RGB_VAD, RGB_VAI)  },
    [3] =   { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU) },
    [4] =   { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU)  },
    [5] =   { ENCODER_CCW_CW(MI_VELD, MI_VELU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU)  },
    [6] =   { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU)  },
    [7] =   { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU) },
    [8] =   { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU)  },
    [9] =   { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU)  },
    [10] =  { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(KC_VOLD, KC_VOLU)  },
    [11] =  { ENCODER_CCW_CW(KC_VOLD, KC_VOLU),                     ENCODER_CCW_CW(MI_CHORD_14, MI_CHORD_14) },
    //                  Encoder 1                                     Encoder 2
};
#endif

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    // Layer 0: Default QWERTY layer
    [0] = LAYOUT_ortho_6x14(
        KC_ESC,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,    KC_6,    KC_7,    KC_8,    KC_9,    KC_0,    KC_MINS, KC_EQL,  KC_BSPC,
        KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,    KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_LBRC, KC_RBRC, KC_BSLS,
        KC_CAPS, KC_A,    KC_S,    KC_D,    KC_F,    KC_G,    KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_QUOT, CMB_ON,  KC_ENT,
        KC_LSFT, KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,    KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_UP,   KC_RSFT,
        KC_LCTL, KC_LGUI, KC_LALT, KC_SPC,  KC_SPC,  KC_SPC,  MO(2),   KC_SPC,  KC_SPC,  KC_SPC,  KC_RCTL, KC_LEFT, KC_DOWN, KC_RIGHT,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 1: Function layer - MIDI control layer 1
    [1] = LAYOUT_ortho_6x14(
        MI_Cs_2, MI_Ds_2, KC_NO,   MI_Fs_2, MI_Gs_2, MI_As_2, KC_NO,   MI_Cs_3, MI_Ds_3, KC_NO,   MI_Fs_3, MI_Gs_3, MI_As_3, MI_ALLOFF,
        MI_C_2,  MI_D_2,  MI_E_2,  MI_F_2,  MI_G_2,  MI_A_2,  MI_B_2,  MI_C_3,  MI_D_3,  MI_E_3,  MI_F_3,  MI_G_3,  MI_A_3,  MI_B_3,
        MI_Cs_1, MI_Ds_1, KC_NO,   MI_Fs_1, MI_Gs_1, MI_As_1, MI_B_1,  MI_Cs_2, MI_Ds_2, KC_NO,   MI_Fs_2, MI_Gs_2, MI_As_2, KC_NO,
        MI_C_1,  MI_D_1,  MI_E_1,  MI_F_1,  MI_G_1,  MI_A_1,  MI_B_1,  MI_C_2,  MI_D_2,  MI_E_2,  MI_F_2,  MI_G_2,  MI_A_2,  MI_B_2,
        MI_CC_100_127, MI_CC_101_127, MI_CC_102_127, MI_CC_103_127, MI_SUS, MI_SUS, MO(2), DF(3), MI_CC_106_127, MI_CC_107_127, MI_CC_108_127, MI_CC_109_127, MI_CC_110_127, MI_CC_111_127,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 2: MIDI control layer 2
    [2] = LAYOUT_ortho_6x14(
        M0,      MI_TRNS_1, MI_TRNS_2, MI_TRNS_3, MI_TRNS_4, MI_TRNS_5, MI_TRNS_6, MI_TRNS_N5, MI_TRNS_N4, MI_TRNS_N3, MI_TRNS_N2, MI_TRNS_N1, KC_NO,  DF(0),
        KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   M0,      MI_OCTD,  MI_OCTU,  MI_TRNSD, MI_TRNSU, KC_NO,   DF(5),
        KC_NO,   MI_VELOCITY_25, MI_VELOCITY_38, MI_VELOCITY_50, MI_VELOCITY_63, MI_VELOCITY_76, MI_VELOCITY_88, MI_VELOCITY_101, MI_VELOCITY_114, MI_VELOCITY_123, MI_VELOCITY_125, KC_NO,   KC_NO,   DF(11),
        KC_NO,   MI_VELOCITY_31, MI_VELOCITY_44, MI_VELOCITY_57, MI_VELOCITY_69, MI_VELOCITY_82, MI_VELOCITY_95, MI_VELOCITY_107, MI_VELOCITY_120, MI_VELOCITY_124, MI_VELOCITY_127, KC_NO,   KC_NO,   RGB_MOD,
        MI_CC_100_127, MI_CC_101_127, MI_CC_102_127, MI_CC_103_127, KC_NO,   KC_NO,   KC_NO,   DF(1), MI_CC_112_127, MI_CC_113_127, MI_CC_114_127, MI_CC_115_127, MI_CC_116_127, MI_CC_117_127,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 3: Macro layer
    [3] = LAYOUT_ortho_6x14(
        KC_NO,   M1,      M2,      M3,      M4,      M5,      M20,     M21,     M22,     M23,     M24,     M25,     M26,     M27,
        KC_NO,   M6,      M7,      M8,      M9,      M10,     M30,     M31,     M32,     M33,     M34,     M35,     M36,     M37,
        KC_NO,   M11,     M12,     M13,     M14,     M15,     M40,     M41,     M42,     M43,     M44,     M45,     M46,     M47,
        KC_NO,   M16,     KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   RGB_TOG,
        MI_CC_100_TOG, MI_CC_101_TOG, MI_CC_102_TOG, MI_CC_103_TOG, ENCODER_SENSITIVITY_12, ENCODER_SENSITIVITY_15, KC_NO, M18, KC_NO, KC_NO, KC_NO, KC_NO, KC_NO, DF(4),
        KC_B,    KC_C,    KC_A
    ),

    // Layer 4: Macro set 2
    [4] = LAYOUT_ortho_6x14(
        M100,    M101,    M102,    M103,    M104,    M105,    M106,    M107,    M108,    M109,    KC_NO,   KC_NO,   KC_NO,   KC_NO,
        M110,    M111,    M112,    M113,    M114,    M115,    M116,    M117,    M118,    M119,    KC_NO,   KC_NO,   KC_NO,   KC_NO,
        M120,    M121,    M122,    M123,    M124,    M125,    M126,    M127,    M128,    M129,    KC_NO,   KC_NO,   KC_NO,   KC_NO,
        M130,    M131,    M132,    M133,    M134,    M135,    M136,    M137,    M138,    M139,    KC_NO,   KC_NO,   KC_NO,   KC_NO,
        DF(1),   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   M18,     KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 5: MIDI velocity control
    [5] = LAYOUT_ortho_6x14(
        MI_C_4,  MI_D_4,  MI_E_4,  MI_F_4,  MI_G_4,  MI_A_4,  MI_B_4,  MI_C_5,  MI_D_5,  MI_E_5,  MI_F_5,  MI_G_5,  MI_A_5,  MI_B_5,
        MI_C_3,  MI_D_3,  MI_E_3,  MI_F_3,  MI_G_3,  MI_A_3,  MI_B_3,  MI_C_4,  MI_D_4,  MI_E_4,  MI_F_4,  MI_G_4,  MI_A_4,  MI_B_4,
        MI_C_2,  MI_D_2,  MI_E_2,  MI_F_2,  MI_G_2,  MI_A_2,  MI_B_2,  MI_C_3,  MI_D_3,  MI_E_3,  MI_F_3,  MI_G_3,  MI_A_3,  MI_B_3,
        MI_C_1,  MI_D_1,  MI_E_1,  MI_F_1,  MI_G_1,  MI_A_1,  MI_B_1,  MI_C_2,  MI_D_2,  MI_E_2,  MI_F_2,  MI_G_2,  MI_A_2,  MI_B_2,
        MI_TRNSD, MI_TRNSU, KC_NO, KC_NO,  MO(2),   MO(2),   DF(2),   DF(2),   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,   KC_NO,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 6: MIDI octave control
    [6] = LAYOUT_ortho_6x14(
        KC_ESC,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,    KC_6,    KC_7,    KC_8,    KC_9,    KC_0,    KC_MINS, KC_EQL,  KC_BSPC,
        KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,    KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_LBRC, KC_RBRC, KC_BSLS,
        KC_CAPS, KC_A,    KC_S,    KC_D,    KC_F,    KC_G,    KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_QUOT, KC_ENT,  KC_ENT,
        KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,    KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_END,  KC_UP,   KC_RSFT,
        KC_LCTL, KC_LGUI, KC_LALT, MO(1),   KC_SPC,  KC_SPC,  KC_SPC,  KC_SPC,  KC_RALT, MO(1),   KC_RCTL, KC_LEFT, KC_DOWN, KC_RIGHT,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 7: Normal keyboard layer
    [7] = LAYOUT_ortho_6x14(
        KC_ESC,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,    KC_6,    KC_7,    KC_8,    KC_9,    KC_0,    KC_MINS, KC_EQL,  KC_BSPC,
        KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,    KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_LBRC, KC_RBRC, KC_BSLS,
        KC_CAPS, KC_A,    KC_S,    KC_D,    KC_F,    KC_G,    KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_QUOT, KC_ENT,  KC_ENT,
        KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,    KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_END,  KC_UP,   KC_RSFT,
        KC_LCTL, KC_LGUI, KC_LALT, MO(1),   KC_SPC,  KC_SPC,  KC_SPC,  KC_SPC,  KC_RALT, MO(1),   KC_RCTL, KC_LEFT, KC_DOWN, KC_RIGHT,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 8: Additional layer with default layout
    [8] = LAYOUT_ortho_6x14(
        KC_ESC,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,    KC_6,    KC_7,    KC_8,    KC_9,    KC_0,    KC_MINS, KC_EQL,  KC_BSPC,
        KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,    KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_LBRC, KC_RBRC, KC_BSLS,
        KC_CAPS, KC_A,    KC_S,    KC_D,    KC_F,    KC_G,    KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_QUOT, KC_ENT,  KC_ENT,
        KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,    KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_END,  KC_UP,   KC_RSFT,
        KC_LCTL, KC_LGUI, KC_LALT, MO(1),   KC_SPC,  KC_SPC,  KC_SPC,  KC_SPC,  KC_RALT, MO(1),   KC_RCTL, KC_LEFT, KC_DOWN, KC_RIGHT,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 9: Additional layer with default layout
    [9] = LAYOUT_ortho_6x14(
        KC_ESC,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,    KC_6,    KC_7,    KC_8,    KC_9,    KC_0,    KC_MINS, KC_EQL,  KC_BSPC,
        KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,    KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_LBRC, KC_RBRC, KC_BSLS,
        KC_CAPS, KC_A,    KC_S,    KC_D,    KC_F,    KC_G,    KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_QUOT, KC_ENT,  KC_ENT,
        KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,    KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_END,  KC_UP,   KC_RSFT,
        KC_LCTL, KC_LGUI, KC_LALT, MO(1),   KC_SPC,  KC_SPC,  KC_SPC,  KC_SPC,  KC_RALT, MO(1),   KC_RCTL, KC_LEFT, KC_DOWN, KC_RIGHT,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 10: Additional layer with default layout
    [10] = LAYOUT_ortho_6x14(
        KC_ESC,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,    KC_6,    KC_7,    KC_8,    KC_9,    KC_0,    KC_MINS, KC_EQL,  KC_BSPC,
        KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,    KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_LBRC, KC_RBRC, KC_BSLS,
        KC_CAPS, KC_A,    KC_S,    KC_D,    KC_F,    KC_G,    KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_QUOT, KC_ENT,  KC_ENT,
        KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,    KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_END,  KC_UP,   KC_RSFT,
        KC_LCTL, KC_LGUI, KC_LALT, MO(1),   KC_SPC,  KC_SPC,  KC_SPC,  KC_SPC,  KC_RALT, MO(1),   KC_RCTL, KC_LEFT, KC_DOWN, KC_RIGHT,
        KC_B,    KC_C,    KC_A
    ),

    // Layer 11: MIDI chord layer
    [11] = LAYOUT_ortho_6x14(
        MI_Cs_2, MI_Ds_2, KC_2,    MI_Fs_2, MI_Gs_2, MI_As_2, KC_6,    MI_Cs_3, MI_Ds_3, KC_9,    MI_Fs_3, MI_Gs_3, MI_As_3, DF(1),
        MI_C_2,  MI_D_2,  MI_E_2,  MI_F_2,  MI_G_2,  MI_A_2,  MI_B_2,  MI_C_3,  MI_D_3,  MI_E_3,  MI_F_3,  MI_G_3,  MI_A_3,  MI_B_3,
        MI_CHORD_0, MI_CHORD_1, MI_CHORD_2, MI_CHORD_3, MI_CHORD_4, MI_CHORD_5, MI_CHORD_6, MI_CHORD_7, MI_CHORD_8, MI_CHORD_9, MI_CHORD_10, MI_CHORD_11, MI_CHORD_12, MI_CHORD_13,
        MI_CHORD_14, MI_CHORD_15, MI_CHORD_16, MI_CHORD_17, MI_CHORD_18, MI_CHORD_19, MI_CHORD_20, MI_CHORD_21, MI_CHORD_22, MI_CHORD_23, MI_CHORD_24, MI_CHORD_25, MI_CHORD_26, MI_CHORD_27,
        MI_CHORD_28, MI_CHORD_29, MI_CHORD_30, MI_CHORD_31, MI_CHORD_32, MI_CHORD_33, MI_CHORD_34, MI_CHORD_35, MI_CHORD_36, MI_CHORD_37, MI_CHORD_38, MI_CHORD_39, MI_CHORD_40, MI_CHORD_41,
        KC_B,    KC_C,    KC_A
    )
};
