# EEPROM Usage Report - Orthomidi5x14 Keyboard

Updated: 2026-01-08

## Hardware Specifications

**EEPROM Chip:** CAT24C512WI-GT3 (I2C)
**Total Capacity:** 64KB (65,536 bytes)
**Address Range:** 0x0000 - 0xFFFF

---

## EEPROM Memory Map Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Address Range   │ Size      │ Usage                             │
├─────────────────────────────────────────────────────────────────┤
│ 0-36            │ 37 B      │ QMK Base Configuration (eeconfig) │
│ 37-40           │ 4 B       │ VIA Magic + Layout Options        │
│ 41-1,720        │ 1,680 B   │ Dynamic Keymaps (12 layers)       │
│ 1,721-1,768     │ 48 B      │ Encoder mappings                  │
│ 1,769-9,960     │ 8,192 B   │ Dynamic Macros (MIDI events)      │
│ 9,961-9,999     │ 39 B      │ Reserved                          │
│ 10,000-13,999   │ 4,000 B   │ Arp User Presets (20 slots)       │
│ 14,000-21,839   │ 7,840 B   │ Seq User Presets (20 slots)       │
│ 21,840-21,999   │ 160 B     │ Gap                               │
│ 22,000-22,699   │ 700 B     │ Custom LED Animations (70 slots)  │
│ 22,700-22,999   │ 300 B     │ Gap                               │
│ 23,000-23,199   │ 200 B     │ Loop Settings                     │
│ 23,200-23,449   │ 250 B     │ Keyboard Settings (5 slots)       │
│ 23,450-23,499   │ 50 B      │ RGB Defaults Magic                │
│ 23,500-23,607   │ 108 B     │ Layer RGB Settings (12 layers)    │
│ 23,608-23,699   │ 92 B      │ Gap                               │
│ 23,700-23,759   │ 60 B      │ Layer Actuation Settings          │
│ 23,760-23,999   │ 240 B     │ Gap                               │
│ 24,000-24,241   │ 242 B     │ User Curves (10 slots)            │
│ 24,242-24,499   │ 258 B     │ Gap                               │
│ 24,500-24,599   │ 100 B     │ Gaming/Joystick Settings          │
│ 24,600-24,999   │ 400 B     │ Gap                               │
│ 25,000-25,889   │ 890 B     │ Per-Key RGB Settings              │
│ 25,890-25,999   │ 110 B     │ Gap                               │
│ 26,000-32,721   │ 6,722 B   │ Per-Key Actuation Settings        │
│ 32,722-65,535   │ 32,814 B  │ Available for future use          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Breakdown by Feature

### 1. QMK Base Configuration (0-36) - 37 bytes

**Location:** `quantum/eeconfig.h`

```
Address  Size  Field
-------------------------------
0-1      2B    Magic Number (0xFEE6)
2        1B    Debug flags
3        1B    Default layer
4-5      2B    Keymap config
6        1B    Backlight config
7        1B    Audio config
8-11     4B    RGB Light config
12       1B    Unicode mode
13       1B    Steno mode
14       1B    Handedness
15-18    4B    Keyboard-specific
19-22    4B    User-specific
23       1B    Velocikey
24-31    8B    RGB Matrix config
32-35    4B    Haptic config
36       1B    RGB Light extended
```

### 2. VIA/Vial Configuration (37-40+) - ~4+ bytes

**Location:** `quantum/via.h`

- Magic number (3 bytes) for VIA firmware validation
- Layout options (1+ bytes)

### 3. Dynamic Keymaps (41-1,720) - 1,680 bytes

**Location:** `quantum/dynamic_keymap.c`

**Configuration:**
- Layers: 12 (`DYNAMIC_KEYMAP_LAYER_COUNT = 12`)
- Matrix: 5 rows × 14 columns = 70 keys
- Storage: 12 layers × 70 keys × 2 bytes = **1,680 bytes**

### 4. Dynamic Macros (1,769-9,960) - 8,192 bytes

**Location:** `quantum/process_keycode/process_dynamic_macro.h`

**Configuration:**
```c
#define DYNAMIC_MACRO_SIZE 8192
```

### 5. Arp User Presets (10,000-13,999) - 4,000 bytes

**Location:** `orthomidi5x14.h` - `ARP_EEPROM_ADDR`

**Configuration:**
- 20 user presets × 200 bytes each = 4,000 bytes
- Each preset: 64 notes × 3 bytes + 8 byte header

### 6. Seq User Presets (14,000-21,839) - 7,840 bytes

**Location:** `orthomidi5x14.h` - `SEQ_EEPROM_ADDR`

**Configuration:**
- 20 user presets × 392 bytes each = 7,840 bytes
- Each preset: 128 notes × 3 bytes + 8 byte header

### 7. Custom LED Animations (22,000-22,699) - 700 bytes

**Location:** `process_dynamic_macro.h` - `EECONFIG_CUSTOM_ANIMATIONS`

**Size per slot:** ~10 bytes
**Total slots:** 70 animations

### 8. Loop Settings (23,000-23,199) - 200 bytes

**Location:** `process_dynamic_macro.h` - `LOOP_SETTINGS_EEPROM_ADDR`

**Structure:** `loop_settings_t`

### 9. Keyboard Settings (23,200-23,449) - 250 bytes

**Location:** `process_dynamic_macro.h` - `SETTINGS_BASE_ADDR`

**Configuration:**
- 5 slots × ~50 bytes each
- `keyboard_settings_t` structure per slot

### 10. Layer RGB Settings (23,500-23,607) - 108 bytes

**Location:** `process_dynamic_macro.h` - `LAYER_SETTINGS_EEPROM_ADDR`

**Configuration:**
- 12 layers × 9 bytes = 108 bytes

### 11. Layer Actuation Settings (23,700-23,759) - 60 bytes

**Location:** `process_dynamic_macro.h` - `LAYER_ACTUATION_EEPROM_ADDR`

**Configuration:**
- 12 layers × 5 bytes = 60 bytes

### 12. User Curves (24,000-24,241) - 242 bytes

**Location:** `orthomidi5x14.h` - `USER_CURVES_EEPROM_ADDR`

**Configuration:**
- 10 user curves × 24 bytes + 2 byte magic = 242 bytes

### 13. Gaming/Joystick Settings (24,500-24,599) - 100 bytes

**Location:** `orthomidi5x14.h` - `GAMING_SETTINGS_EEPROM_ADDR`

**Structure:** `gaming_settings_t`

### 14. Per-Key RGB Settings (25,000-25,889) - 890 bytes

**Location:** `per_key_rgb.h` - `PER_KEY_RGB_EEPROM_ADDR`

**Structure:**
```
25,000-25,047:  Global HSV palette (48 bytes)
                - 16 colors × 3 bytes (H, S, V)

25,048-25,887:  12 per-key presets (840 bytes)
                - Each preset: 70 LEDs × 1 byte (palette index)

25,888-25,889:  Magic number validation (2 bytes)
```

### 15. Per-Key Actuation Settings (26,000-32,721) - 6,722 bytes

**Location:** `process_dynamic_macro.h` - `PER_KEY_ACTUATION_EEPROM_ADDR`

**Configuration:**
- 70 keys × 12 layers × 8 bytes = 6,720 bytes
- 2 bytes for flags (mode_enabled, per_layer_enabled)
- Total: 6,722 bytes

---

## Total EEPROM Usage Summary

| Feature | Address Range | Size (bytes) | % of 64KB |
|---------|---------------|--------------|-----------|
| QMK Base Config | 0-36 | 37 | 0.1% |
| VIA Config | 37-40 | 4 | <0.1% |
| Dynamic Keymaps | 41-1,720 | 1,680 | 2.6% |
| Encoders | 1,721-1,768 | 48 | 0.1% |
| Dynamic Macros | 1,769-9,960 | 8,192 | 12.5% |
| **Arp User Presets** | 10,000-13,999 | **4,000** | **6.1%** |
| **Seq User Presets** | 14,000-21,839 | **7,840** | **12.0%** |
| Custom Animations | 22,000-22,699 | 700 | 1.1% |
| Loop Settings | 23,000-23,199 | 200 | 0.3% |
| Keyboard Settings | 23,200-23,449 | 250 | 0.4% |
| Layer RGB Settings | 23,500-23,607 | 108 | 0.2% |
| Layer Actuation | 23,700-23,759 | 60 | 0.1% |
| User Curves | 24,000-24,241 | 242 | 0.4% |
| Gaming Settings | 24,500-24,599 | 100 | 0.2% |
| Per-Key RGB | 25,000-25,889 | 890 | 1.4% |
| **Per-Key Actuation** | 26,000-32,721 | **6,722** | **10.3%** |
| **Available** | 32,722-65,535 | **32,814** | **50.1%** |

### Key Statistics:

**Total Used:** ~32,722 bytes / 65,536 bytes
**Remaining:** ~32,814 bytes (~50%)

**Largest Allocations:**
1. Dynamic Macros: 8,192 bytes (12.5%)
2. Seq User Presets: 7,840 bytes (12.0%)
3. Per-Key Actuation: 6,722 bytes (10.3%)
4. Arp User Presets: 4,000 bytes (6.1%)
5. Dynamic Keymaps: 1,680 bytes (2.6%)

---

## Files Containing EEPROM Definitions

1. **`quantum/eeconfig.h`** - QMK base EEPROM layout (0-36)
2. **`quantum/via.h`** - VIA protocol EEPROM usage (37+)
3. **`quantum/dynamic_keymap.c`** - Keymap and macro storage
4. **`quantum/process_keycode/process_dynamic_macro.h`** - Custom EEPROM layout
5. **`keyboards/orthomidi5x14/orthomidi5x14.h`** - Gaming, arpeggiator, curve addresses
6. **`keyboards/orthomidi5x14/per_key_rgb.h`** - Per-key RGB storage
7. **`keyboards/orthomidi5x14/config.h`** - EEPROM chip configuration

---

## Recent Changes (2026-01-08)

- **Upgraded EEPROM:** Changed from CAT24C256WI-GT3 (32KB) to CAT24C512WI-GT3 (64KB)
- **Fixed config.h:** Changed `EEPROM_I2C_24LC256` to `EEPROM_I2C_CAT24C512`
- **Reorganized addresses:** All features now fit within 64KB with no overlaps
- **Available space:** ~32KB remaining for future expansion
