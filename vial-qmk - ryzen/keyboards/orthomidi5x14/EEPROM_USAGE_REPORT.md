# EEPROM Usage Report - Orthomidi5x14 Keyboard

Updated: 2026-03-05

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
│ 1,721-1,816     │ 96 B      │ Encoder mappings                  │
│ 1,817-20,999    │ 19,183 B  │ VIA Text Macros (~19KB)           │
│ 21,000-21,359   │ 360 B     │ Null Bind (SOCD) Settings         │
│ 22,000-22,399   │ 400 B     │ Toggle Keys                       │
│ 23,000-26,999   │ 4,000 B   │ Arp User Presets (20 × 200)       │
│ 27,500-35,339   │ 7,840 B   │ Seq User Presets (20 × 392)       │
│ 36,000-36,749   │ 750 B     │ Custom LED Animations (50 × 15)   │
│ 37,000-37,199   │ 200 B     │ Loop Settings                     │
│ 38,000-38,249   │ 250 B     │ Keyboard Settings (5 slots)       │
│ 38,500-38,501   │ 2 B       │ RGB Defaults Magic                │
│ 39,000-39,107   │ 108 B     │ Layer RGB Settings (12 layers)    │
│ 40,000-40,059   │ 60 B      │ Layer Actuation Settings          │
│ 41,000-41,901   │ 902 B     │ User Curves (10 × 90 + 2 magic)  │
│ 42,000-42,099   │ 100 B     │ Gaming/Joystick Settings          │
│ 42,200-42,225   │ 26 B      │ EQ Curve Settings                 │
│ 43,000-43,887   │ 888 B     │ Per-Key RGB Settings              │
│ 45,000-51,719   │ 6,720 B   │ Per-Key Actuation Settings        │
│ 52,000-53,603   │ 1,604 B   │ DKS Configurations (50 slots)     │
│ 53,604-65,535   │ 11,932 B  │ Available for future use           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration Requirements

In `config.h`:
```c
// Updated for CAT24C512WI-GT3 (64KB EEPROM)
#define EEPROM_I2C_CAT24C512

// Allocate ~19KB for VIA text macros (addresses 1817-20999)
#define DYNAMIC_KEYMAP_EEPROM_MAX_ADDR 20999
```

In `rules.mk`:
```makefile
EEPROM_DRIVER = i2c
```

---

## Total EEPROM Usage Summary

| Feature | Address Range | Size (bytes) | % of 64KB |
|---------|---------------|--------------|-----------|
| QMK Base Config | 0-36 | 37 | 0.1% |
| VIA Config | 37-40 | 4 | <0.1% |
| Dynamic Keymaps | 41-1,720 | 1,680 | 2.6% |
| Encoders | 1,721-1,816 | 96 | 0.1% |
| **VIA Text Macros** | 1,817-20,999 | **19,183** | **29.3%** |
| Null Bind (SOCD) | 21,000-21,359 | 360 | 0.5% |
| Toggle Keys | 22,000-22,399 | 400 | 0.6% |
| **Arp User Presets** | 23,000-26,999 | **4,000** | **6.1%** |
| **Seq User Presets** | 27,500-35,339 | **7,840** | **12.0%** |
| Custom Animations | 36,000-36,749 | 750 | 1.1% |
| Loop Settings | 37,000-37,199 | 200 | 0.3% |
| Keyboard Settings | 38,000-38,249 | 250 | 0.4% |
| Layer RGB Settings | 39,000-39,107 | 108 | 0.2% |
| Layer Actuation | 40,000-40,059 | 60 | 0.1% |
| User Curves | 41,000-41,901 | 902 | 1.4% |
| Gaming Settings | 42,000-42,099 | 100 | 0.2% |
| EQ Curve Settings | 42,200-42,225 | 26 | <0.1% |
| Per-Key RGB | 43,000-43,887 | 888 | 1.4% |
| **Per-Key Actuation** | 45,000-51,719 | **6,720** | **10.3%** |
| **DKS Configurations** | 52,000-53,603 | **1,604** | **2.4%** |
| **Available** | 53,604-65,535 | **11,932** | **18.2%** |

### Key Statistics:

**Total Used:** ~45,208 bytes / 65,536 bytes (~69%)
**Remaining:** ~11,932 bytes (~18%) contiguous at end + gaps between features

**Largest Allocations:**
1. VIA Text Macros: 19,183 bytes (29.3%)
2. Seq User Presets: 7,840 bytes (12.0%)
3. Per-Key Actuation: 6,720 bytes (10.3%)
4. Arp User Presets: 4,000 bytes (6.1%)
5. Dynamic Keymaps: 1,680 bytes (2.6%)

---

## VIA Macro Capacity

With ~19KB allocated for macros:
- **Buffer size:** ~19,183 bytes
- **Default macro count:** 16 (can be increased via `DYNAMIC_KEYMAP_MACRO_COUNT`)
- **Estimated capacity:**
  - Simple text: ~19,000 characters
  - Basic keycodes (3 bytes each): ~6,400 actions
  - Mixed typical use: ~7,500-9,500 total actions

---

## Files Containing EEPROM Definitions

1. **`config.h`** - EEPROM chip config, macro buffer limit
2. **`rules.mk`** - EEPROM driver selection
3. **`quantum/process_keycode/process_dynamic_macro.h`** - Custom feature addresses (animations, loop, settings, RGB, layer, per-key actuation)
4. **`keyboards/orthomidi5x14/orthomidi5x14.h`** - Null bind, toggle, arp, seq, gaming, user curves, EQ curve addresses
5. **`keyboards/orthomidi5x14/per_key_rgb.h`** - Per-key RGB address
6. **`quantum/process_keycode/process_dks.h`** - DKS EEPROM address (52,000)

---

## Recent Changes (2026-03-05)

- **Fixed EEPROM overlap:** EQ Curve (was 42,000) moved to 42,200 to avoid collision with Gaming Settings (42,000)
- **Fixed EEPROM overlap:** DKS (was 45,000) moved to 52,000 to avoid collision with Per-Key Actuation (45,000-51,719)
- **Updated all addresses** to match actual `#define` values in source code
- **Corrected Custom Animations:** 50 slots × 15 bytes = 750 bytes (was listed as 70 slots × 10 = 700 bytes)
- **Corrected User Curves:** 10 × 90 + 2 = 902 bytes (was listed as 242 bytes)
