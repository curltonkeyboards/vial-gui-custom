# Keycode Audit: Missing from tabbed_keycodes.py

Generated: 2026-03-04

## Overview

| File | Keycodes Defined |
|------|-----------------|
| `keycodes_v5.py` | 2,634 (firmware resolution dict) |
| `keycodes_v6.py` | 2,634 (identical to v5) |
| `keycodes.py` | 2,624 (GUI `K()` definitions) |
| `tabbed_keycodes.py` | ~2,559 reachable via 171 `KEYCODES_*` lists |

**Note:** v5 and v6 dictionaries are identical — no differences between versions.

---

## Part 1: KEYCODES_* Lists Defined in keycodes.py But Never Used in Any Tab

These are entire groups of keycodes defined via `K()` but never wired to `tabbed_keycodes.py`.

### KEYCODES_HE_MACRO_CURVE (25 keycodes)
- `HE_MACRO_CURVE_0` through `HE_MACRO_CURVE_16` (17 curve selection)
- `HE_MACRO_CURVE_DOWN`, `HE_MACRO_CURVE_UP`
- `HE_MACRO_MAX_DOWN`, `HE_MACRO_MAX_UP`
- `HE_MACRO_MIN_DOWN`, `HE_MACRO_MIN_UP`
- `HE_VEL_CURVE_DOWN`, `HE_VEL_CURVE_UP`

### KEYCODES_MIDI_BASIC (76 keycodes)
- `MI_C` through `MI_Gs_5` (72 base MIDI notes across octaves)
- `MI_ALLOFF`, `MI_SUS`, `MI_CHORD_99`, `KC_NO`

### KEYCODES_OCTAVE_DOUBLER (8 keycodes)
- `OCT_DBL_MINUS1`, `OCT_DBL_OFF`, `OCT_DBL_PLUS1`, `OCT_DBL_PLUS2`, `OCT_DBL_TOGGLE`
- `TEMP_TRANS_MINUS12`, `TEMP_TRANS_PLUS12`, `TEMP_TRANS_PLUS24`

### KEYCODES_KC (35 modifier-wrap keycodes)
- `ALL_T(kc)`, `C_S(kc)`, `C_S_T(kc)`, `HYPR(kc)`, `LALT(kc)`, `LALT_T(kc)`
- `LCA(kc)`, `LCAG(kc)`, `LCAG_T(kc)`, `LCA_T(kc)`, `LCG(kc)`, `LCG_T(kc)`
- `LCTL(kc)`, `LCTL_T(kc)`, `LGUI(kc)`, `LGUI_T(kc)`, `LSA(kc)`, `LSA_T(kc)`
- `LSFT(kc)`, `LSFT_T(kc)`, `MEH(kc)`, `MEH_T(kc)`, `RALT(kc)`, `RALT_T(kc)`
- `RCAG_T(kc)`, `RCG(kc)`, `RCG_T(kc)`, `RCTL(kc)`, `RCTL_T(kc)`
- `RGUI(kc)`, `RGUI_T(kc)`, `RSFT(kc)`, `RSFT_T(kc)`, `SGUI(kc)`, `SGUI_T(kc)`

### KEYCODES_HIDDEN (1 keycode)
- `TD({})` (tap dance template)

**Subtotal: 145 keycodes defined in keycodes.py but unreachable from tabs**

---

## Part 2: Keycodes in v5/v6 Firmware Dicts With NO K() Definition in keycodes.py

These exist for firmware resolution but have zero GUI representation.

### MIDI (328 keycodes — biggest gap)
- `MI_VELOCITY2_0` through `MI_VELOCITY2_127` (128 keysplit velocity values)
- `MI_VELOCITY3_0` through `MI_VELOCITY3_127` (128 triplesplit velocity values)
- `MI_CHORD_78`–`MI_CHORD_98`, `MI_CHORD_116`–`MI_CHORD_128` (34 chord indices)
- `MI_BANK_LSB_0`, `MI_BANK_MSB_0`, `MI_CC_0_0`, `MI_CC_0_DWN`, `MI_CC_0_TOG`, `MI_CC_0_UP`
- `MI_ET_3`, `MI_ET_6`, `MI_ET_9`, `MI_ET_12` (ear trainer intervals)
- `MI_INVERSION_DEF`, `MI_INVERSION_1`–`MI_INVERSION_8`
- `MI_PROG_0`, `MI_SCAN`, `MI_VELOCITY_0`
- `MI_SMARTCHORD_DOWN`, `MI_SMARTCHORD_PRESS`, `MI_SMARTCHORD_UP`
- `MI_TRNS_N6`, `MI_VELD`, `MI_VELU`
- `MI_VEL_1` through `MI_VEL_10`

### RGB Mode (9 keycodes)
- `RGB_M_B`, `RGB_M_G`, `RGB_M_K`, `RGB_M_P`, `RGB_M_R`, `RGB_M_SN`, `RGB_M_SW`, `RGB_M_T`, `RGB_M_X`

### Backlight (7 keycodes)
- `BL_BRTG`, `BL_DEC`, `BL_INC`, `BL_OFF`, `BL_ON`, `BL_STEP`, `BL_TOGG`

### OLED (3 keycodes)
- `OLED_4`, `OLED_5`, `OLED_6`

### CC Step Size (6 keycodes)
- `CC_STEPSIZE_11` through `CC_STEPSIZE_16`

### Other (8 keycodes)
- `ARP_PRESET_BASE`, `CHORD_PROG_STOP`, `DKS_00`, `FN_MO13`, `FN_MO23`
- `HE_VEL_RANGE_1_1`, `SEQ_PRESET_BASE`, `TGL_00`

**Subtotal: ~361 keycodes in firmware dicts with no GUI definition at all**

---

## Summary of Most Significant Gaps

| Gap | Count | Impact |
|-----|-------|--------|
| MI_VELOCITY2/3 (keysplit/triplesplit velocity) | 256 | Firmware-only, invisible to GUI |
| KEYCODES_HE_MACRO_CURVE (Hall Effect macro curves) | 25 | Defined in keycodes.py, never added to tabs |
| KEYCODES_MIDI_BASIC (base MIDI notes) | 76 | Defined but not in tabs (split versions used instead) |
| KEYCODES_KC (modifier wraps) | 35 | Defined but not in tabs |
| BL_* + RGB_M_* (backlight/RGB modes) | 16 | Standard QMK keycodes, missing entirely |
| KEYCODES_OCTAVE_DOUBLER | 8 | Defined but not in tabs |
| MI_CHORD high indices | 34 | In firmware dicts, no GUI definition |
| MI_INVERSION keycodes | 10 | In firmware dicts, no GUI definition |
| CC_STEPSIZE 11-16 | 6 | In firmware dicts, no GUI definition |
| OLED_4/5/6 | 3 | In firmware dicts, no GUI definition |
