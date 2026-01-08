# EEPROM Reorganization - COMPLETED

## Status: ✅ COMPLETE (2026-01-08)

The EEPROM layout has been fully reorganized for the 64KB CAT24C512WI-GT3 chip.

## Summary of Changes

### 1. EEPROM Chip Configuration
- **File:** `config.h`
- **Change:** `EEPROM_I2C_24LC256` → `EEPROM_I2C_CAT24C512`
- **Effect:** Enables full 64KB (65,536 bytes) capacity

### 2. Address Reorganization

All EEPROM addresses have been reorganized to:
- Fit within 64KB limit (0-65,535)
- Eliminate all overlaps
- Leave ~32KB available for future expansion

#### New Memory Layout

```
Address Range        Size        Feature
─────────────────────────────────────────────────────────────
0-9,999              ~10 KB      Reserved for QMK/VIA base
10,000-13,999        4,000 B     Arp User Presets (20 × 200)
14,000-21,839        7,840 B     Seq User Presets (20 × 392)
22,000-22,699        700 B       Custom Animations
23,000-23,199        200 B       Loop Settings
23,200-23,449        250 B       Keyboard Settings (5 slots)
23,500-23,607        108 B       Layer RGB Settings
23,700-23,759        60 B        Layer Actuation Settings
24,000-24,241        242 B       User Curves
24,500-24,599        100 B       Gaming Settings
25,000-25,889        890 B       Per-Key RGB
26,000-32,721        6,722 B     Per-Key Actuation
32,722-65,535        ~32 KB      Available for future use
```

### 3. Files Updated

| File | Changes |
|------|---------|
| `config.h` | Changed EEPROM chip define to CAT24C512 |
| `orthomidi5x14.h` | Updated ARP_EEPROM_ADDR, SEQ_EEPROM_ADDR, USER_CURVES_EEPROM_ADDR, GAMING_SETTINGS_EEPROM_ADDR |
| `per_key_rgb.h` | Updated PER_KEY_RGB_EEPROM_ADDR |
| `process_dynamic_macro.h` | Updated all EEPROM addresses, added comprehensive memory map |
| `EEPROM_USAGE_REPORT.md` | Complete documentation update |

### 4. Old vs New Addresses

| Feature | Old Address | New Address | Status |
|---------|-------------|-------------|--------|
| Arp Presets | 56000 | 10000 | ✅ Fixed |
| Seq Presets | 60000 | 14000 | ✅ Fixed |
| Custom Animations | 62000 | 22000 | ✅ Fixed |
| Loop Settings | 64600 | 23000 | ✅ Fixed |
| Keyboard Settings | 65000 | 23200 | ✅ Fixed |
| RGB Magic | 65300 | 23450 | ✅ Fixed |
| Layer RGB | 65400 | 23500 | ✅ Fixed |
| Layer Actuation | 74000 | 23700 | ✅ Fixed (was beyond 64KB!) |
| User Curves | 68100 | 24000 | ✅ Fixed |
| Gaming Settings | 74100 | 24500 | ✅ Fixed (was beyond 64KB!) |
| Per-Key RGB | 67940 | 25000 | ✅ Fixed |
| Per-Key Actuation | 67000 | 26000 | ✅ Fixed |

### 5. Issues Resolved

1. **Addresses exceeding 64KB:** Layer Actuation (74000) and Gaming Settings (74100) were beyond the 64KB limit
2. **Overlapping regions:** Seq presets (60000-67839) overlapped with Custom Animations (62000), Per-Key Actuation (67000), and Per-Key RGB (67940)
3. **Chip configuration:** config.h was configured for 32KB chip instead of 64KB

## Important Note

**Existing EEPROM data will need to be reset** after flashing firmware with these changes, as the addresses have moved. Users should save any custom presets/settings before updating.

## Testing Checklist

- [ ] Verify EEPROM is recognized as 64KB
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
