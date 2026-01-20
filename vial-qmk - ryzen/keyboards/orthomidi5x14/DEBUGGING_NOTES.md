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

### Issue 4: Keys Permanently Pressed on Startup (Inverted HE Sensors)
**Problem:** All keys were registering as pressed immediately on power-on.

**Root Cause:** The distance calculation in `distance_lut.h` had an early return that didn't handle Hall Effect sensors with inverted ADC behavior (higher ADC = unpressed, lower ADC = pressed).

**Original (Wrong):**
```c
// In adc_to_distance_corrected()
if (rest >= bottom_out) return 0;  // Invalid calibration
```
This condition was ALWAYS true for our HE sensors where rest (~2000) > bottom_out (~1100), causing all keys to return distance=0, which was then misinterpreted.

**Fixed:**
```c
if (rest == bottom_out) return 0;  // Invalid calibration (no range)

// Handle inverted sensors (rest > bottom_out) - Hall Effect sensors
if (rest > bottom_out) {
    if (adc >= rest) return 0;        // At or above rest = no travel
    if (adc <= bottom_out) return 255; // At or below bottom = full travel
    uint8_t linear_distance = (uint8_t)(((uint32_t)(rest - adc) * 255) / (rest - bottom_out));
    // ... LUT blending code
}
```

**File:** `quantum/distance_lut.h`

---

### Issue 5: ADC Validity Range Incorrect
**Problem:** Empty key sockets were causing ghost keypresses.

**Original (Wrong):**
```c
if (key->adc_filtered < 1800 || key->adc_filtered > 3300) {
    // Treat as invalid
}
```

**Fixed (matches actual hardware measurements):**
```c
if (key->adc_filtered < 1000 || key->adc_filtered > 2500) {
    // Treat as invalid
}
```

Also updated constants:
```c
#define VALID_ANALOG_RAW_VALUE_MIN 1000
#define VALID_ANALOG_RAW_VALUE_MAX 2500
```

**Files:** `quantum/matrix.c`, `quantum/matrix.h`

---

### Issue 6: Actuation Threshold Too High (95%)
**Problem:** Keys still not registering after fixing distance calculation.

**Root Cause:** Default actuation was set to 95%, requiring distance >= 242 (out of 255). Physical keys only reached ~240 when fully bottomed out.

**Fixed:** Lowered default actuation to 30% for troubleshooting:
```c
void initialize_layer_actuations(void) {
    for (uint8_t i = 0; i < 12; i++) {
        layer_actuations[i].normal_actuation = 30;  // Was 95
        layer_actuations[i].midi_actuation = 30;    // Was 95
        // ...
    }
}
```

**File:** `keyboards/orthomidi5x14/orthomidi5x14.c`

---

### Issue 7: 2-Second Input Delay (EMA Filter)
**Problem:** Key presses had ~2 second delay before registering, and same delay on release.

**Root Cause:** EMA (Exponential Moving Average) filter with alpha = 1/16 was causing heavy smoothing:
```c
#define MATRIX_EMA_ALPHA_EXPONENT 4  // alpha = 1/16 = 0.0625
#define EMA(x, y) (((uint32_t)(x) + ((uint32_t)(y) * 15)) >> 4)
```

With alpha = 0.0625, it takes ~16 samples to reach 63% of a step change, causing significant lag.

**Fixed (Bypass):**
```c
// In analog_matrix_task_internal():
// TROUBLESHOOTING: Bypass EMA filter, use raw ADC directly
// Original: key->adc_filtered = EMA(raw_value, key->adc_filtered);
key->adc_filtered = raw_value;
```

**File:** `quantum/matrix.c` (line ~1046)

---

### Issue 8: Remaining Input Delay (QMK Debounce)
**Problem:** Still some delay after bypassing EMA filter.

**Root Cause:** QMK's debounce system was set to 5ms (`DEBOUNCE=5`), using `sym_defer_g` algorithm which defers all state changes.

**Fixed:**
```c
#define DEBOUNCE 0
```

**File:** `keyboards/orthomidi5x14/config.h`

---

### Issue 9: EEPROM Read Bottleneck (140 reads/scan)
**Problem:** Performance bottleneck identified - 140 EEPROM reads per matrix scan cycle.

**Root Cause:** Two loops in `matrix_scan_custom()` were calling `dynamic_keymap_get_keycode()`:
1. DKS key detection loop: 70 calls
2. Matrix building loop: 70 calls

Each I2C EEPROM read takes ~100-500µs, totaling ~14-70ms per scan cycle.

**Fixed:** Implemented key type caching system:

```c
// Key types for the cache
typedef enum {
    KEY_TYPE_NORMAL = 0,
    KEY_TYPE_DKS = 1,
    KEY_TYPE_MIDI = 2
} key_type_t;

// Cache arrays (refreshed on layer change only)
static uint8_t key_type_cache[NUM_KEYS];      // 70 bytes
static uint16_t dks_keycode_cache[NUM_KEYS];  // 140 bytes
static uint8_t key_type_cache_layer = 0xFF;   // Current cached layer

// Refresh function - reads EEPROM once per layer change
static void refresh_key_type_cache(uint8_t layer) {
    if (key_type_cache_layer == layer) return;  // Already cached

    for (each key) {
        uint16_t keycode = dynamic_keymap_get_keycode(layer, row, col);
        if (is_dks_keycode(keycode)) {
            key_type_cache[key_idx] = KEY_TYPE_DKS;
            dks_keycode_cache[key_idx] = keycode;
        } else if (midi_key_states[key_idx].is_midi_key) {
            key_type_cache[key_idx] = KEY_TYPE_MIDI;
        } else {
            key_type_cache[key_idx] = KEY_TYPE_NORMAL;
        }
    }
    key_type_cache_layer = layer;
}
```

**Performance Impact:**
- Before: ~140 EEPROM reads per scan (~14-70ms overhead)
- After: 70 reads only on layer change, 0 reads during normal scanning

**File:** `quantum/matrix.c` (lines 183-200, 352-387, 1195-1270)

---

### Issue 10: EEPROM Bypass for Troubleshooting
**Problem:** EEPROM-stored actuation values may have been corrupt or invalid.

**Fixed (Temporary Bypass):**
```c
void load_layer_actuations(void) {
    // TROUBLESHOOTING: Bypass EEPROM and use hardcoded defaults
    initialize_layer_actuations();
}
```

**File:** `keyboards/orthomidi5x14/orthomidi5x14.c`

---

## Current Troubleshooting State

### Bypassed/Disabled Features
| Feature | Status | Reason |
|---------|--------|--------|
| EMA Filter | Bypassed | Was causing 2-second delay |
| QMK Debounce | DEBOUNCE=0 | Was adding additional delay |
| EEPROM Actuation Loading | Bypassed | Using hardcoded 30% actuation |
| Per-key Actuations | Disabled | 6.7KB array access was problematic |

### Active Optimizations
| Optimization | Description |
|--------------|-------------|
| Key Type Cache | Eliminates EEPROM reads in scan loop |
| Layer Settings Cache | Caches actuation settings per layer |
| Nullbind in RAM | All nullbind operations use RAM arrays |

---

## Commits Made

1. `FIX: Correct MUX pins - A2=PA7, A3=PB0`
2. `FIX: Invert row and column addressing to match PCB wiring`
3. `FIX: Remove preprocessor conditionals that can't evaluate PAL_LINE`
4. `FIX: Resolve permanently pressed keys on HE keyboard startup`
5. `FIX: Lower default actuation threshold from 95% to 50%`
6. `TROUBLESHOOT: Bypass EEPROM, use hardcoded 30% actuation`
7. `TROUBLESHOOT: Bypass EMA filter for immediate key response`
8. `TROUBLESHOOT: Disable QMK debounce (DEBOUNCE=0)`
9. `PERF: Add key type cache to eliminate EEPROM reads per scan`

---

## Next Steps

1. **Test current configuration** - Verify keys respond with minimal delay
2. **Re-enable EMA with faster alpha** - Try alpha = 1/4 or 1/2 for light filtering
3. **Re-enable debounce** - Set DEBOUNCE=2 or similar for minimal filtering
4. **Restore EEPROM loading** - Once actuation values are confirmed working
5. **Calibration testing** - Ensure per-key calibration handles ADC variation

---

## Notes for Future Reference

- The PCB has columns wired in reverse order on the MUX (0-7 reversed, 8-13 reversed)
- Row ADC pins are labeled ADC1-ADC5 on PCB but correspond to PA4-PA0
- Hall effect sensor variation of ~600 counts in rest values is normal
- All sensors bottom out to similar values (~1100-1350), which is good for consistency
- **HE sensors have inverted ADC**: Higher ADC = unpressed, Lower ADC = pressed
- **Valid ADC range**: 1000-2500 (not the original 1800-3300)
- **EEPROM reads are slow**: ~100-500µs each via I2C, avoid in hot loops
- **EMA alpha = 1/16 is too slow**: Causes ~2 second delay, use faster alpha or bypass
