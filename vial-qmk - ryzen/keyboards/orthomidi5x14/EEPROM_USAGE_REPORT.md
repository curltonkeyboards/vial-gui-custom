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
│ 1,721-1,816     │ 96 B      │ Encoder mappings                  │
│ 1,817-21,999    │ 20,183 B  │ VIA Text Macros (~20KB)           │
│ 22,000-25,999   │ 4,000 B   │ Arp User Presets (20 slots)       │
│ 26,000-33,839   │ 7,840 B   │ Seq User Presets (20 slots)       │
│ 33,840-33,999   │ 160 B     │ Gap                               │
│ 34,000-34,699   │ 700 B     │ Custom LED Animations (70 slots)  │
│ 34,700-34,999   │ 300 B     │ Gap                               │
│ 35,000-35,199   │ 200 B     │ Loop Settings                     │
│ 35,200-35,449   │ 250 B     │ Keyboard Settings (5 slots)       │
│ 35,450-35,499   │ 50 B      │ RGB Defaults Magic                │
│ 35,500-35,607   │ 108 B     │ Layer RGB Settings (12 layers)    │
│ 35,608-35,699   │ 92 B      │ Gap                               │
│ 35,700-35,759   │ 60 B      │ Layer Actuation Settings          │
│ 35,760-35,999   │ 240 B     │ Gap                               │
│ 36,000-36,241   │ 242 B     │ User Curves (10 slots)            │
│ 36,242-36,499   │ 258 B     │ Gap                               │
│ 36,500-36,599   │ 100 B     │ Gaming/Joystick Settings          │
│ 36,600-36,999   │ 400 B     │ Gap                               │
│ 37,000-37,889   │ 890 B     │ Per-Key RGB Settings              │
│ 37,890-37,999   │ 110 B     │ Gap                               │
│ 38,000-44,721   │ 6,722 B   │ Per-Key Actuation Settings        │
│ 44,722-65,535   │ 20,814 B  │ Available for future use          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration Requirements

In `config.h`:
```c
// Updated for CAT24C512WI-GT3 (64KB EEPROM)
#define EEPROM_I2C_CAT24C512

// Allocate 20KB for VIA text macros (addresses 1817-21999)
#define DYNAMIC_KEYMAP_EEPROM_MAX_ADDR 21999
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
| **VIA Text Macros** | 1,817-21,999 | **20,183** | **30.8%** |
| **Arp User Presets** | 22,000-25,999 | **4,000** | **6.1%** |
| **Seq User Presets** | 26,000-33,839 | **7,840** | **12.0%** |
| Custom Animations | 34,000-34,699 | 700 | 1.1% |
| Loop Settings | 35,000-35,199 | 200 | 0.3% |
| Keyboard Settings | 35,200-35,449 | 250 | 0.4% |
| Layer RGB Settings | 35,500-35,607 | 108 | 0.2% |
| Layer Actuation | 35,700-35,759 | 60 | 0.1% |
| User Curves | 36,000-36,241 | 242 | 0.4% |
| Gaming Settings | 36,500-36,599 | 100 | 0.2% |
| Per-Key RGB | 37,000-37,889 | 890 | 1.4% |
| **Per-Key Actuation** | 38,000-44,721 | **6,722** | **10.3%** |
| **Available** | 44,722-65,535 | **20,814** | **31.8%** |

### Key Statistics:

**Total Used:** ~44,722 bytes / 65,536 bytes (~68%)
**Remaining:** ~20,814 bytes (~32%)

**Largest Allocations:**
1. VIA Text Macros: 20,183 bytes (30.8%)
2. Seq User Presets: 7,840 bytes (12.0%)
3. Per-Key Actuation: 6,722 bytes (10.3%)
4. Arp User Presets: 4,000 bytes (6.1%)
5. Dynamic Keymaps: 1,680 bytes (2.6%)

---

## VIA Macro Capacity

With 20KB allocated for macros:
- **Buffer size:** ~20,183 bytes
- **Default macro count:** 16 (can be increased via `DYNAMIC_KEYMAP_MACRO_COUNT`)
- **Estimated capacity:**
  - Simple text: ~20,000 characters
  - Basic keycodes (3 bytes each): ~6,700 actions
  - Mixed typical use: ~8,000-10,000 total actions

---

## Files Containing EEPROM Definitions

1. **`config.h`** - EEPROM chip config, macro buffer limit
2. **`rules.mk`** - EEPROM driver selection
3. **`quantum/process_keycode/process_dynamic_macro.h`** - Custom feature addresses
4. **`keyboards/orthomidi5x14/orthomidi5x14.h`** - Arp, Seq, Gaming, Curves addresses
5. **`keyboards/orthomidi5x14/per_key_rgb.h`** - Per-key RGB address

---

## Recent Changes (2026-01-08)

- **Upgraded EEPROM:** CAT24C256WI-GT3 (32KB) → CAT24C512WI-GT3 (64KB)
- **Config:** Changed `EEPROM_I2C_24LC256` → `EEPROM_I2C_CAT24C512`
- **Macro allocation:** 20KB dedicated for VIA text macros
- **Custom features:** Moved to addresses 22000+ to avoid macro overlap
- **Available space:** ~20KB remaining for future expansion
