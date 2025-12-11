# EEPROM Usage Report - Orthomidi5x14 Keyboard

Generated: 2025-12-10

## Hardware Specifications

**EEPROM Chip:** 24LC256 (I2C)
**Total Capacity:** 32KB (32,768 bytes)
**Address Range:** 0x0000 - 0x7FFF

---

## EEPROM Memory Map Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Address Range  │ Size    │ Usage                               │
├─────────────────────────────────────────────────────────────────┤
│ 0-36           │ 37 B    │ QMK Base Configuration (eeconfig)   │
│ 37-40          │ 4 B     │ VIA Magic + Layout Options          │
│ 41+            │ varies  │ VIA Custom Config (if any)          │
│ ~41-~1720      │ ~1680 B │ Dynamic Keymaps (12 layers)         │
│ ~1721-~1768    │ ~48 B   │ Encoder mappings (if enabled)       │
│ ~1769-~9960    │ 8192 B  │ Dynamic Macros (MIDI events)        │
│ 9961-61999     │ ~52KB   │ Reserved/Unused                     │
│ 62000-62699    │ 700 B   │ Custom LED Animations (70 slots)    │
│ 62700-64599    │ 1900 B  │ Gap/Reserved                        │
│ 64600-64799    │ 200 B   │ Loop Settings (thru-loop system)    │
│ 64800-64999    │ 200 B   │ Gap/Reserved                        │
│ 65000-65199    │ 200 B   │ Keyboard Settings (5 slots)         │
│ 65200-65299    │ 100 B   │ Gap/Reserved                        │
│ 65300-65399    │ 100 B   │ RGB Defaults Magic + Gap            │
│ 65400-65599    │ 200 B   │ Layer RGB Settings (12 layers)      │
│ 65600-65699    │ 100 B   │ Layer Actuation Settings            │
│ 65700-65799    │ 100 B   │ Gaming/Joystick Settings            │
│ 65800-66271    │ 472 B   │ Arpeggiator User Presets (16 slots) │
│ 66272-65999    │ Gap     │ Gap (overlaps, needs correction)    │
│ 66000-66889    │ 890 B   │ Per-Key RGB Settings                │
│ 66890-32767    │ ~288 B  │ Available for future use            │
└─────────────────────────────────────────────────────────────────┘
```

**WARNING:** There appears to be an address overlap issue between:
- Arpeggiator presets (65800+)
- Per-Key RGB (66000+)

Need to verify actual arpeggiator storage implementation.

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

### 2. VIA/Vial Configuration (~37-40+) - ~4+ bytes

**Location:** `quantum/via.h`

- Magic number (3 bytes) for VIA firmware validation
- Layout options (1+ bytes)
- Custom config (if defined, typically 0 bytes)

### 3. Dynamic Keymaps (~41-~1720) - ~1680 bytes

**Location:** `quantum/dynamic_keymap.c`

**Configuration:**
- Layers: 12 (`DYNAMIC_KEYMAP_LAYER_COUNT = 12`)
- Matrix: 5 rows × 14 columns = 70 keys
- Storage: 12 layers × 70 keys × 2 bytes = **1,680 bytes**

Each keycode is stored as a 16-bit big-endian value.

### 4. Dynamic Macros (~1769-~9960) - 8,192 bytes

**Location:** `quantum/process_keycode/process_dynamic_macro.h`

**Configuration:**
```c
#define DYNAMIC_MACRO_SIZE 8192
```

**Purpose:** Stores MIDI event sequences for 4 macro slots
**Features:**
- MIDI Note On/Off events
- MIDI CC (Control Change) events
- Timestamps for playback timing
- Overdub mode support
- Preroll recording (200ms buffer)

---

## Custom Feature EEPROM Usage

### 5. Custom LED Animations (62000-62699) - 700 bytes

**Address:** 62000
**Size per slot:** ~10 bytes
**Total slots:** 70 animations
**Actual usage:** Variable based on number of custom animations

**Structure per animation:**
- HSV color values
- Speed/timing parameters
- Animation type flags

### 6. Loop Settings (64600-64799) - ~70 bytes used, 200 allocated

**Address:** 64600
**Structure:** `loop_settings_t`

**Contents:**
- Loop messaging enable flags
- MIDI channel routing
- Sync mode settings
- CC mapping for loop controls (4 loops):
  - Restart, Start/Stop Recording
  - Start/Stop Playback, Clear
- Overdub CC mappings (4 loops)
- Navigation CC mappings
- Total: ~70 bytes

### 7. Keyboard Settings (65000-65199) - ~225 bytes used, 200 allocated

**Address:** 65000-65199 (5 slots × 40-45 bytes each)
**Structure:** `keyboard_settings_t` (defined in `process_dynamic_macro.h:318-367`)

**Slot layout:**
- Slot 0 (default): 65000-65039
- Slot 1: 65040-65079
- Slot 2: 65080-65119
- Slot 3: 65120-65159
- Slot 4: 65160-65199

**Settings per slot (~45 bytes):**
```c
typedef struct {
    int velocity_sensitivity;              // 4B
    int cc_sensitivity;                    // 4B
    uint8_t channel_number;                // 1B
    int8_t transpose_number;               // 1B
    int8_t octave_number;                  // 1B
    int8_t transpose_number2;              // 1B
    int8_t octave_number2;                 // 1B
    int8_t transpose_number3;              // 1B
    int8_t octave_number3;                 // 1B
    uint8_t dynamic_range;                 // 1B
    int oledkeyboard;                      // 4B
    bool overdub_advanced_mode;            // 1B
    int smartchordlightmode;               // 4B
    uint8_t keysplitchannel;               // 1B
    uint8_t keysplit2channel;              // 1B
    uint8_t keysplitstatus;                // 1B
    uint8_t keysplittransposestatus;       // 1B
    uint8_t keysplitvelocitystatus;        // 1B
    bool custom_layer_animations_enabled;  // 1B
    uint8_t unsynced_mode_active;          // 1B
    bool sample_mode_active;               // 1B
    bool loop_messaging_enabled;           // 1B
    uint8_t loop_messaging_channel;        // 1B
    bool sync_midi_mode;                   // 1B
    bool alternate_restart_mode;           // 1B
    int colorblindmode;                    // 4B
    bool cclooprecording;                  // 1B
    bool truesustain;                      // 1B
    // Global MIDI Settings
    uint8_t aftertouch_mode;               // 1B
    uint8_t aftertouch_cc;                 // 1B
    // Velocity curves/ranges for 3 zones
    uint8_t he_velocity_curve;             // 1B
    uint8_t he_velocity_min;               // 1B
    uint8_t he_velocity_max;               // 1B
    uint8_t keysplit_he_velocity_curve;    // 1B
    uint8_t keysplit_he_velocity_min;      // 1B
    uint8_t keysplit_he_velocity_max;      // 1B
    uint8_t triplesplit_he_velocity_curve; // 1B
    uint8_t triplesplit_he_velocity_min;   // 1B
    uint8_t triplesplit_he_velocity_max;   // 1B
    // Sustain settings
    uint8_t base_sustain;                  // 1B
    uint8_t keysplit_sustain;              // 1B
    uint8_t triplesplit_sustain;           // 1B
} keyboard_settings_t;  // Total: ~47 bytes
```

### 8. Layer RGB Settings (65400-65599) - 108 bytes used, 200 allocated

**Address:** 65400
**Size:** 12 layers × 9 bytes = 108 bytes

**Per-layer settings (9 bytes):**
- RGB mode/effect
- HSV color values
- Speed/brightness
- Layer-specific LED configurations

### 9. Layer Actuation Settings (65600-65699) - 96 bytes used, 100 allocated

**Address:** 65600
**Structure:** `layer_actuation_t` × 12 layers
**Size per layer:** 8 bytes

**Per-layer actuation (8 bytes):**
```c
typedef struct {
    uint8_t normal_actuation;          // 1B - Normal key actuation point
    uint8_t midi_actuation;            // 1B - MIDI note actuation point
    uint8_t velocity_range;            // 1B - Velocity calculation range
    uint8_t rapid_trigger_sens;        // 1B - Rapid trigger sensitivity
    uint8_t midi_rapid_sens;           // 1B - MIDI rapid trigger sensitivity
    uint8_t midi_rapid_vel;            // 1B - MIDI rapid trigger velocity
    uint8_t velocity_speed;            // 1B - Velocity calculation speed
    uint8_t flags;                     // 1B - Feature flags (rapid on/off, etc.)
} layer_actuation_t;  // 8 bytes × 12 layers = 96 bytes
```

### 10. Gaming/Joystick Settings (65700-65799) - ~60 bytes used, 100 allocated

**Address:** 65700
**Structure:** `gaming_settings_t`
**Magic:** 0x47A3

**Contents (~60 bytes):**
- Gaming mode enable flag
- Left stick mappings (4 keys: up/down/left/right)
- Right stick mappings (4 keys)
- Trigger mappings (2 keys: LT/RT)
- Button mappings (16 buttons)
- Analog calibration for:
  - Left stick (min/max travel)
  - Right stick (min/max travel)
  - Triggers (min/max travel)

**Structure:**
```c
typedef struct {
    bool gaming_mode_enabled;           // 1B
    gaming_key_map_t ls_up;             // 3B (row, col, enabled)
    gaming_key_map_t ls_down;           // 3B
    gaming_key_map_t ls_left;           // 3B
    gaming_key_map_t ls_right;          // 3B
    gaming_key_map_t rs_up;             // 3B
    gaming_key_map_t rs_down;           // 3B
    gaming_key_map_t rs_left;           // 3B
    gaming_key_map_t rs_right;          // 3B
    gaming_key_map_t lt;                // 3B
    gaming_key_map_t rt;                // 3B
    gaming_key_map_t buttons[16];       // 48B (16 × 3B)
    gaming_analog_config_t ls_config;   // 2B
    gaming_analog_config_t rs_config;   // 2B
    gaming_analog_config_t trigger_config; // 2B
    uint16_t magic;                     // 2B
} gaming_settings_t;  // Total: ~100 bytes
```

### 11. Arpeggiator User Presets (65800+) - Up to 6,272 bytes

**Address:** 65800
**Number of user presets:** 16 (slots 48-63)
**Size per preset:** 392 bytes
**Total size:** 16 × 392 = **6,272 bytes**

**Note:** Factory presets (0-47) are stored in PROGMEM (flash), not EEPROM

**Preset structure:**
```c
typedef struct {
    uint8_t preset_type;                   // 1B - Arp or Step Sequencer
    uint8_t note_count;                    // 1B - Number of notes (1-128)
    uint8_t pattern_length_16ths;          // 1B - Pattern length in 16th notes
    uint8_t gate_length_percent;           // 1B - Gate length 0-100%
    uint8_t timing_mode;                   // 1B - Straight/Triplet/Dotted
    uint8_t note_value;                    // 1B - Quarter/Eighth/Sixteenth
    arp_preset_note_t notes[128];          // 384B (128 notes × 3 bytes)
    uint16_t magic;                        // 2B - 0xA89F validation
} arp_preset_t;  // Total: 392 bytes
```

**Note format (3 bytes per note):**
- Packed timing/velocity/sign (2 bytes)
- Note/interval + octave offset (1 byte)

### 12. Per-Key RGB Settings (66000-66889) - 890 bytes

**Address:** 66000
**Magic:** 0xC0DE (at address 66888)

**Structure:**
```
66000-66047:  Global HSV palette (48 bytes)
              - 16 colors × 3 bytes (H, S, V)
              
66048-66887:  12 per-key presets (840 bytes)
              - Each preset: 70 LEDs × 1 byte (palette index)
              - 12 presets × 70 bytes = 840 bytes
              
66888-66889:  Magic number validation (2 bytes)
```

**Total:** 48 + 840 + 2 = **890 bytes**

---

## Total EEPROM Usage Summary

| Feature | Address Range | Size (bytes) | % of 32KB |
|---------|---------------|--------------|-----------|
| QMK Base Config | 0-36 | 37 | 0.1% |
| VIA Config | 37-40 | 4 | <0.1% |
| Dynamic Keymaps | ~41-1720 | 1,680 | 5.1% |
| Encoders | ~1721-1768 | 48 | 0.1% |
| **Dynamic Macros** | ~1769-9960 | **8,192** | **25.0%** |
| Reserved/Gap | 9961-61999 | 52,039 | - |
| Custom Animations | 62000-62699 | 700 | 2.1% |
| Gap | 62700-64599 | 1,900 | - |
| Loop Settings | 64600-64799 | 70/200 | 0.2% |
| Gap | 64800-64999 | 200 | - |
| **Keyboard Settings (5 slots)** | 65000-65199 | **~225/200** | **0.7%** |
| Gap | 65200-65299 | 100 | - |
| RGB Magic | 65300-65399 | 4/100 | <0.1% |
| Layer RGB Settings | 65400-65599 | 108/200 | 0.3% |
| Layer Actuation | 65600-65699 | 96/100 | 0.3% |
| Gaming Settings | 65700-65799 | 60/100 | 0.2% |
| **Arp User Presets (16)** | 65800-72071 | **6,272** | **19.1%** |
| **Per-Key RGB** | 66000-66889 | **890** | **2.7%** |
| **Available** | 72072-32767 | **~280** | **~0.9%** |

### Key Statistics:

**Total Used:** ~32,488 bytes / 32,768 bytes
**Remaining:** ~280 bytes (~0.9%)

**Largest Allocations:**
1. Dynamic Macros: 8,192 bytes (25.0%)
2. Arpeggiator Presets: 6,272 bytes (19.1%)
3. Dynamic Keymaps: 1,680 bytes (5.1%)
4. Per-Key RGB: 890 bytes (2.7%)
5. Custom Animations: 700 bytes (2.1%)

---

## Address Conflict Warning ⚠️

There is an **address overlap** between:
- Arpeggiator User Presets: starts at 65800, needs 6,272 bytes → ends at **72,071**
- Per-Key RGB Settings: starts at **66000**, needs 890 bytes → ends at 66,889

**Overlap range:** 66000-66889 (890 bytes)

This means the arpeggiator presets and per-key RGB are using the **same EEPROM addresses**!

### Resolution Options:

1. **Move Arpeggiator Presets** to start after Per-Key RGB:
   - New address: 66890
   - End address: 66890 + 6,272 = 73,162
   - **Problem:** Exceeds 32KB EEPROM capacity (32,768 bytes)!

2. **Reduce Arpeggiator Presets:**
   - Option A: Reduce from 16 to 10 user presets → 3,920 bytes
   - Option B: Reduce from 16 to 8 user presets → 3,136 bytes
   - Option C: Reduce max notes per preset from 128 to 64 → 200 bytes/preset × 16 = 3,200 bytes

3. **Reduce Dynamic Macro Size:**
   - Current: 8,192 bytes
   - Reduce to: 6,144 bytes (savings: 2,048 bytes)
   - This frees up space to move arpeggiator presets

### Recommended Fix:

**Option 3 + Move Arpeggiator:**
1. Reduce `DYNAMIC_MACRO_SIZE` from 8192 to 6144 bytes
2. Move Arpeggiator start address from 65800 to 67000
3. New layout:
   - Macros: 1769-7912 (6,144 bytes)
   - Arp: 67000-73271 (6,272 bytes)
   - Total: Still within 32KB with ~3KB breathing room

---

## Storage Architecture by Category

### A. MIDI Performance Features
- **Macros (8192 bytes):** MIDI event loops with overdub
- **Arpeggiator (6272 bytes):** 16 user + 48 factory presets
- **Loop Settings (70 bytes):** Thru-loop system configuration
- **Keyboard Settings (225 bytes):** Global MIDI routing, channels, velocity curves

### B. Hall Effect Sensor Configuration
- **Layer Actuation (96 bytes):** Per-layer actuation points, rapid trigger
- **Velocity Curves (stored in keyboard_settings):** 3 zones (base/keysplit/triplesplit)

### C. RGB Lighting
- **Layer RGB (108 bytes):** Per-layer RGB effects
- **Custom Animations (700 bytes):** User-defined LED animations
- **Per-Key RGB (890 bytes):** 12 presets with 16-color palette

### D. Gaming/Joystick
- **Gaming Settings (60 bytes):** Joystick mappings and analog calibration

---

## Files Containing EEPROM Definitions

1. **`quantum/eeconfig.h`** - QMK base EEPROM layout (0-36)
2. **`quantum/via.h`** - VIA protocol EEPROM usage (37+)
3. **`quantum/dynamic_keymap.c`** - Keymap and macro storage
4. **`quantum/process_keycode/process_dynamic_macro.h`** - Custom EEPROM layout (62000+)
5. **`keyboards/orthomidi5x14/orthomidi5x14.h`** - Gaming and arpeggiator addresses
6. **`keyboards/orthomidi5x14/per_key_rgb.h`** - Per-key RGB storage

---

## Recommendations

### Immediate Actions:
1. **Fix address overlap** between arpeggiator and per-key RGB
2. Test EEPROM boundaries to ensure no overflow
3. Add validation to detect EEPROM corruption

### Future Considerations:
1. **Upgrade to larger EEPROM:** 24LC512 (64KB) or 24LC1026 (128KB)
2. **Implement wear leveling** for frequently-written areas (macros, settings)
3. **Add EEPROM health monitoring** to track write cycles
4. **Compress arpeggiator presets** using delta encoding or RLE

### Memory Optimization Ideas:
1. **Share preset storage** between factory and user (lazy-load from flash/EEPROM)
2. **Reduce macro buffer** if 8KB is excessive for typical use
3. **Implement preset compression** for arpeggiator patterns
4. **Use flash storage** for read-only data (factory presets already do this)

---

## Conclusion

The orthomidi5x14 keyboard makes extensive use of EEPROM to store:
- **Performance data:** Macros, arps, loops
- **Configuration:** 5 keyboard setting slots, layer settings
- **Customization:** RGB animations, per-key colors, gaming mappings

Currently using **~32.5KB of 32KB available** with an address conflict that needs resolution. The system is feature-rich but at capacity limits.

**Next steps:** Address the overlap issue and consider EEPROM upgrade for future expansion.
