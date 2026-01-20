# OrthMIDI 5x14 Hall Effect Keyboard - Debugging Notes

## Date: January 2025

---

## Hardware Configuration

### MCU: STM32F412

### ADC Pins (Row Sensing)
| ADC Label | MCU Pin | Firmware Row |
|-----------|---------|--------------|
| ADC1 | PA4 | Row 0 |
| ADC2 | PA3 | Row 1 |
| ADC3 | PA2 | Row 2 |
| ADC4 | PA1 | Row 3 |
| ADC5 | PA0 | Row 4 |

### MUX Address Pins (Column Selection - ADG706)
| MUX Pin | MCU Pin | Function |
|---------|---------|----------|
| MUXA | PA5 | A0 (LSB) |
| MUXB | PA6 | A1 |
| MUXC | PA7 | A2 |
| MUXD | PB0 | A3 (MSB) |

### Other Peripherals
| Function | Pins |
|----------|------|
| Encoder 1 A/B | PC14 / PC13 |
| Encoder 1 Click | PB14 |
| Encoder 2 A/B | PC15 / PB4 |
| Encoder 2 Click | PB15 |
| I2C SCL (OLED) | PB6 |
| I2C SDA (OLED) | PB7 |
| WS2812 RGB Data | PB8 |

---

## Issues Discovered & Fixes Applied

### Issue 1: Incorrect MUX Pin Assignments
**Problem:** Original firmware had wrong pin mappings for MUX address lines.

**Original (Wrong):**
```c
#define ADG706_A0 A5  // PA5
#define ADG706_A1 A6  // PA6
#define ADG706_A2 B0  // PB0 - WRONG
#define ADG706_A3 B1  // PB1 - WRONG
```

**Fixed:**
```c
#define ADG706_A0 A5  // PA5 = MUXA
#define ADG706_A1 A6  // PA6 = MUXB
#define ADG706_A2 A7  // PA7 = MUXC
#define ADG706_A3 B0  // PB0 = MUXD
```

**File:** `keyboards/orthomidi5x14/config.h`

---

### Issue 2: Row Pin Order Inverted
**Problem:** Firmware row 0 was reading physical row 4, and vice versa.

**Original (Wrong):**
```c
#define MATRIX_ROW_PINS { A0, A1, A2, A3, A4 }
// PA0 (ADC5) was firmware row 0, but ADC5 is physical row 4
```

**Fixed:**
```c
#define MATRIX_ROW_PINS { A4, A3, A2, A1, A0 }
// PA4 (ADC1) is now firmware row 0 = physical row 0
```

**File:** `keyboards/orthomidi5x14/config.h`

---

### Issue 3: Column Addressing Inverted
**Problem:** Physical columns were wired in reverse order on the MUX.
- Physical r0c0 was triggering firmware col 7
- Physical r0c7 was triggering firmware col 0

**Original (Wrong):**
```c
static void select_column(uint8_t col) {
    writePin(ADG706_A0, col & 0x01);
    writePin(ADG706_A1, col & 0x02);
    writePin(ADG706_A2, col & 0x04);
    writePin(ADG706_A3, col & 0x08);
}
```

**Fixed:**
```c
static void select_column(uint8_t col) {
    if (col >= 16) return;

    // Invert column addressing to match physical PCB wiring
    uint8_t mux_addr;
    if (col < 8) {
        mux_addr = 7 - col;      // 0→7, 1→6, ..., 7→0
    } else {
        mux_addr = 21 - col;     // 8→13, 9→12, ..., 13→8
    }

    writePin(ADG706_A0, mux_addr & 0x01);
    writePin(ADG706_A1, mux_addr & 0x02);
    writePin(ADG706_A2, mux_addr & 0x04);
    writePin(ADG706_A3, mux_addr & 0x08);

    if (ADG706_EN != NO_PIN) {
        writePinLow(ADG706_EN);
    }
}
```

**File:** `quantum/matrix.c`

---

## ADC Value Characterization

### Resting (Unpressed) Values
- Range: **1650 - 2250** (approximately 600 count variation)
- This variation is normal for Hall effect sensors due to:
  - Sensor manufacturing tolerances
  - Magnet positioning variations
  - PCB trace differences

### Pressed (Bottom Out) Values
- Range: **1100 - 1350**
- Consistent floor across all keys
- No values go below ~1100

### Travel Range by Key Type
| Rest Value | Pressed Value | Travel Range |
|------------|---------------|--------------|
| 2000-2200 | 1150-1350 | ~850-1050 counts |
| 1600-1800 | 1110-1250 | ~490-690 counts |

### Implications for Calibration
- Per-key calibration is essential due to rest value variation
- Each key needs individual `rest_adc` and `bottom_adc` values
- Actuation should be calculated as percentage of each key's range
- Minimum travel range (~500 counts) is sufficient for reliable detection

---

## Matrix Mapping Summary

### Final Correct Mapping
After all fixes, the matrix should map as:
- **Firmware Row 0** = Physical Row 0 (ADC1/PA4)
- **Firmware Row 4** = Physical Row 4 (ADC5/PA0)
- **Firmware Col 0** = Physical Col 0 (MUX channel 7)
- **Firmware Col 13** = Physical Col 13 (MUX channel 8)

### Column Address Translation Table
| Firmware Col | MUX Address |
|--------------|-------------|
| 0 | 7 |
| 1 | 6 |
| 2 | 5 |
| 3 | 4 |
| 4 | 3 |
| 5 | 2 |
| 6 | 1 |
| 7 | 0 |
| 8 | 13 |
| 9 | 12 |
| 10 | 11 |
| 11 | 10 |
| 12 | 9 |
| 13 | 8 |

---

## Files Modified

1. **`keyboards/orthomidi5x14/config.h`**
   - Fixed MUX pin assignments (A2=PA7, A3=PB0)
   - Reversed MATRIX_ROW_PINS order

2. **`quantum/matrix.c`**
   - Added column address inversion in `select_column()`
   - Removed preprocessor conditionals that couldn't evaluate PAL_LINE macros

3. **`keyboards/orthomidi5x14/orthomidi5x14.c`**
   - OLED debug display (temporary, for testing)

---

## Commits Made

1. `FIX: Correct MUX pins - A2=PA7, A3=PB0`
2. `FIX: Invert row and column addressing to match PCB wiring`
3. `FIX: Remove preprocessor conditionals that can't evaluate PAL_LINE`
4. Various debug commits for OLED display testing

---

## Next Steps

1. **Re-enable keypress processing** - Currently disabled for debugging
2. **Test actual key output** - Verify keys produce correct keycodes
3. **Calibration testing** - Ensure per-key calibration handles the ADC variation
4. **Remove debug OLED code** - Restore normal OLED display functionality

---

## Notes for Future Reference

- The PCB has columns wired in reverse order on the MUX (0-7 reversed, 8-13 reversed)
- Row ADC pins are labeled ADC1-ADC5 on PCB but correspond to PA4-PA0
- Hall effect sensor variation of ~600 counts in rest values is normal
- All sensors bottom out to similar values (~1100-1350), which is good for consistency
