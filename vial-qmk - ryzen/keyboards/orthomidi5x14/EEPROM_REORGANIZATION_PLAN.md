# EEPROM Reorganization - COMPLETED

## Status: ✅ COMPLETE (2026-01-08)

The EEPROM layout has been fully reorganized for the 64KB CAT24C512WI-GT3 chip with 20KB dedicated for VIA text macros.

## Summary of Changes

### 1. EEPROM Chip Configuration
- **File:** `config.h`
- **Change:** `EEPROM_I2C_24LC256` → `EEPROM_I2C_CAT24C512`
- **Effect:** Enables full 64KB (65,536 bytes) capacity

### 2. VIA Macro Space Allocation
- **File:** `config.h`
- **Added:** `DYNAMIC_KEYMAP_EEPROM_MAX_ADDR 21999`
- **Effect:** Allocates ~20KB (addresses 1817-21999) for VIA text macros

### 3. Address Reorganization

All EEPROM addresses have been reorganized to:
- Fit within 64KB limit (0-65,535)
- Allocate 20KB for VIA text macros
- Eliminate all overlaps
- Leave ~20KB available for future expansion

#### New Memory Layout

```
Address Range        Size        Feature
─────────────────────────────────────────────────────────────
0-1,816              ~1.8 KB     QMK/VIA base (keymaps, encoders)
1,817-21,999         ~20 KB      VIA Text Macros
22,000-25,999        4,000 B     Arp User Presets (20 × 200)
26,000-33,839        7,840 B     Seq User Presets (20 × 392)
34,000-34,699        700 B       Custom Animations
35,000-35,199        200 B       Loop Settings
35,200-35,449        250 B       Keyboard Settings (5 slots)
35,500-35,607        108 B       Layer RGB Settings
35,700-35,759        60 B        Layer Actuation Settings
36,000-36,241        242 B       User Curves
36,500-36,599        100 B       Gaming Settings
37,000-37,889        890 B       Per-Key RGB
38,000-44,721        6,722 B     Per-Key Actuation
44,722-65,535        ~20 KB      Available for future use
```

### 4. Files Updated

| File | Changes |
|------|---------|
| `config.h` | EEPROM chip define + macro buffer limit |
| `orthomidi5x14.h` | ARP, SEQ, USER_CURVES, GAMING addresses |
| `per_key_rgb.h` | PER_KEY_RGB_EEPROM_ADDR |
| `process_dynamic_macro.h` | All other EEPROM addresses |
| `EEPROM_USAGE_REPORT.md` | Complete documentation update |

### 5. Old vs New Addresses

| Feature | Old Address | New Address |
|---------|-------------|-------------|
| VIA Macros | 1817-9999 | 1817-21999 |
| Arp Presets | 10000 | 22000 |
| Seq Presets | 14000 | 26000 |
| Custom Animations | 22000 | 34000 |
| Loop Settings | 23000 | 35000 |
| Keyboard Settings | 23200 | 35200 |
| RGB Magic | 23450 | 35450 |
| Layer RGB | 23500 | 35500 |
| Layer Actuation | 23700 | 35700 |
| User Curves | 24000 | 36000 |
| Gaming Settings | 24500 | 36500 |
| Per-Key RGB | 25000 | 37000 |
| Per-Key Actuation | 26000 | 38000 |

## Important Note

**Existing EEPROM data will need to be reset** after flashing firmware with these changes, as all addresses have moved. Users should save any custom presets/settings before updating.

## Testing Checklist

- [ ] Verify EEPROM is recognized as 64KB
- [ ] Test VIA macro save/load
- [ ] Test all arp preset save/load operations
- [ ] Test all seq preset save/load operations
- [ ] Test custom animation save/load
- [ ] Test keyboard settings save/load (all 5 slots)
- [ ] Test layer RGB settings
- [ ] Test layer actuation settings
- [ ] Test user curves save/load
- [ ] Test gaming settings save/load
- [ ] Test per-key RGB save/load
- [ ] Test per-key actuation save/load
- [ ] Power cycle test to ensure persistence
