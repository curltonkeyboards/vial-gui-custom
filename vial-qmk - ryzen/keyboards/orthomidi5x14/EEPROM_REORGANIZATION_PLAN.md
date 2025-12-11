# EEPROM Reorganization - Implementation Status

## Overview

Reorganizing EEPROM for 64KB capacity with separate arpeggiator and step sequencer presets.

## Memory Layout (64KB EEPROM)

```
Address Range        Size        Feature
─────────────────────────────────────────────────────────────
0-36                 37 B        QMK Base Config
37-40                4 B         VIA Config
41-1,720             1,680 B     Dynamic Keymaps (12 layers)
1,721-1,768          48 B        Encoders
1,769-55,999         ~54 KB      VIA Text Macros

56,000-59,999        4,000 B     ✅ Arp Presets (20 × 200B)
60,000-67,839        7,840 B     ✅ Seq Presets (20 × 392B)
67,840-67,939        100 B       ✅ Gaming Settings (MOVED)
67,940-68,829        890 B       ✅ Per-Key RGB (MOVED)
68,830-68,929        100 B       ✅ Layer Actuation (MOVED)

62,000-62,699        700 B       Custom Animations (UNCHANGED)
64,600-64,799        200 B       Loop Settings (UNCHANGED)
65,000-65,199        200 B       Keyboard Settings (UNCHANGED)
65,400-65,599        200 B       Layer RGB Settings (UNCHANGED)

65,600-65,535        Available   ~64 bytes
```

---

## ✅ COMPLETED

### 1. Header File Updates

**File: `orthomidi5x14.h`**
- ✅ Updated `GAMING_SETTINGS_EEPROM_ADDR` from 65700 → 67840
- ✅ Separated `MAX_ARP_PRESET_NOTES` (64) and `MAX_SEQ_PRESET_NOTES` (128)
- ✅ Changed from 16 shared presets to:
  - `NUM_USER_ARP_PRESETS 20` (slots 0-19)
  - `NUM_USER_SEQ_PRESETS 20` (slots 0-19)
  - `NUM_FACTORY_ARP_PRESETS 48` (slots 0-47 in PROGMEM)
  - `NUM_FACTORY_SEQ_PRESETS 48` (slots 0-47 in PROGMEM)
- ✅ Created separate structures:
  - `arp_preset_t` - 200 bytes (64 notes × 3 + 8 header)
  - `seq_preset_t` - 392 bytes (128 notes × 3 + 8 header)
- ✅ Added new EEPROM addresses:
  - `ARP_EEPROM_ADDR 56000`
  - `SEQ_EEPROM_ADDR 60000`
  - `ARP_PRESET_SIZE 200`
  - `SEQ_PRESET_SIZE 392`
- ✅ Updated RAM storage declarations:
  - `arp_active_preset` → `arp_preset_t` (200 bytes)
  - `seq_active_presets[4]` → `seq_preset_t[]` (4 × 392 bytes)
- ✅ Added separate function declarations for sequencer:
  - `seq_validate_preset()`
  - `seq_save_preset_to_eeprom()`
  - `seq_load_preset_from_eeprom()`
  - `seq_load_factory_preset()`
  - `seq_clear_preset()`
  - `seq_copy_preset()`
  - `seq_reset_all_user_presets()`

**File: `per_key_rgb.h`**
- ✅ Updated `PER_KEY_RGB_EEPROM_ADDR` from 66000 → 67940

**File: `process_dynamic_macro.h`**
- ✅ Updated `LAYER_ACTUATION_EEPROM_ADDR` from 65600 → 68830
- ✅ Added comments noting unchanged addresses (62000, 64600, 65000, 65400)

**File: `arpeggiator.c`**
- ✅ Updated RAM storage declarations to use `seq_preset_t` for sequencers

---

## 🔧 TODO - Arpeggiator.c Implementation

### 2. EEPROM Address Calculation Functions

**Current (NEEDS UPDATE):**
```c
static uint32_t arp_get_preset_eeprom_addr(uint8_t preset_id) {
    // Currently handles both arp and seq presets combined
    // Uses USER_PRESET_START (48) and MAX_ARP_PRESETS (64)
    return ARP_EEPROM_ADDR + (eeprom_slot * ARP_MAX_PRESET_EEPROM_SIZE);
}
```

**REPLACE WITH TWO SEPARATE FUNCTIONS:**
```c
// Arpeggiator presets: user slots 0-19
static uint32_t arp_get_preset_eeprom_addr(uint8_t preset_id) {
    if (preset_id >= NUM_USER_ARP_PRESETS) {
        return 0;  // Invalid or factory preset
    }
    return ARP_EEPROM_ADDR + (preset_id * ARP_PRESET_SIZE);
}

// Step sequencer presets: user slots 0-19
static uint32_t seq_get_preset_eeprom_addr(uint8_t preset_id) {
    if (preset_id >= NUM_USER_SEQ_PRESETS) {
        return 0;  // Invalid or factory preset
    }
    return SEQ_EEPROM_ADDR + (preset_id * SEQ_PRESET_SIZE);
}
```

### 3. Validation Functions

**Current:**
- `bool arp_validate_preset(const arp_preset_t *preset)` - checks `MAX_PRESET_NOTES`

**UPDATE NEEDED:**
- Update to check `MAX_ARP_PRESET_NOTES` (64) instead of `MAX_PRESET_NOTES` (128)

**ADD NEW:**
```c
bool seq_validate_preset(const seq_preset_t *preset) {
    // Same logic as arp version but checks MAX_SEQ_PRESET_NOTES (128)
    if (preset == NULL) return false;
    if (preset->magic != ARP_PRESET_MAGIC) return false;
    if (preset->note_count > MAX_SEQ_PRESET_NOTES) return false;
    // ... rest of validation
}
```

### 4. Save/Load Functions

**Current Arp Functions (NEED UPDATE):**
- `arp_save_preset_to_eeprom()` - update to use new address function
- `arp_load_preset_from_eeprom()` - update to use new address function

**NEW Sequencer Functions NEEDED:**
```c
bool seq_save_preset_to_eeprom(uint8_t preset_id, const seq_preset_t *source) {
    if (preset_id >= NUM_USER_SEQ_PRESETS) return false;
    if (!seq_validate_preset(source)) return false;

    uint32_t addr = seq_get_preset_eeprom_addr(preset_id);
    eeprom_update_block(source, (void*)addr, SEQ_PRESET_SIZE);
    return true;
}

bool seq_load_preset_from_eeprom(uint8_t preset_id, seq_preset_t *dest) {
    if (preset_id >= NUM_USER_SEQ_PRESETS) return false;

    uint32_t addr = seq_get_preset_eeprom_addr(preset_id);
    eeprom_read_block(dest, (void*)addr, SEQ_PRESET_SIZE);
    return seq_validate_preset(dest);
}
```

### 5. Clear/Copy/Reset Functions

**ADD NEW Sequencer Functions:**
```c
bool seq_clear_preset(uint8_t preset_id);
bool seq_copy_preset(uint8_t source_id, uint8_t dest_id);
void seq_reset_all_user_presets(void);
```

---

## 🔧 TODO - Factory Presets

### 6. Factory Preset Organization

**File: `arp_factory_presets.c`**

**Current Organization:**
- Array of 48 total factory presets (mixed arp and seq)

**NEW Organization NEEDED:**
```c
// First 48 presets: Arpeggiators (stored as arp_preset_t)
const arp_preset_t PROGMEM factory_arp_presets[NUM_FACTORY_ARP_PRESETS] = {
    // 48 arpeggiator patterns
};

// Next 48 presets: Step Sequencers (stored as seq_preset_t)
const seq_preset_t PROGMEM factory_seq_presets[NUM_FACTORY_SEQ_PRESETS] = {
    // 48 step sequencer patterns
};
```

**UPDATE Loading Functions:**
```c
void arp_load_factory_preset(uint8_t preset_id, arp_preset_t *dest) {
    if (preset_id >= NUM_FACTORY_ARP_PRESETS) return;
    memcpy_P(dest, &factory_arp_presets[preset_id], sizeof(arp_preset_t));
}

void seq_load_factory_preset(uint8_t preset_id, seq_preset_t *dest) {
    if (preset_id >= NUM_FACTORY_SEQ_PRESETS) return;
    memcpy_P(dest, &factory_seq_presets[preset_id], sizeof(seq_preset_t));
}
```

---

## 🔧 TODO - HID Communication

### 7. Update HID Protocol

**File: `arpeggiator_hid.c`**

**Current Commands:**
- `ARP_CMD_SAVE_PRESET` - saves to combined pool
- `ARP_CMD_LOAD_PRESET` - loads from combined pool

**UPDATE NEEDED:**

**Option A: Use preset type field to route**
```c
case ARP_CMD_SAVE_PRESET:
    // Check preset_type field in received data
    if (preset->preset_type == PRESET_TYPE_ARPEGGIATOR) {
        arp_save_preset_to_eeprom(preset_id, (arp_preset_t*)preset);
    } else {
        seq_save_preset_to_eeprom(preset_id, (seq_preset_t*)preset);
    }
    break;
```

**Option B: Separate command IDs (RECOMMENDED)**
```c
#define ARP_CMD_SAVE_ARP_PRESET  0x30  // Save arpeggiator preset
#define ARP_CMD_SAVE_SEQ_PRESET  0x31  // Save sequencer preset
#define ARP_CMD_LOAD_ARP_PRESET  0x32  // Load arpeggiator preset
#define ARP_CMD_LOAD_SEQ_PRESET  0x33  // Load sequencer preset
```

**Validation Changes:**
- Update buffer size checks to verify correct preset size (200 vs 392 bytes)
- Update note count checks (64 vs 128)

---

## 🔧 TODO - Runtime Updates

### 8. Preset Loading into RAM

**UPDATE Functions:**
```c
// Current:
bool arp_load_preset_into_slot(uint8_t preset_id) {
    // Loads either factory (0-47) or user (48-63) into arp_active_preset
}

bool seq_load_preset_into_slot(uint8_t preset_id, uint8_t slot) {
    // Loads either factory (0-47) or user (48-63) into seq_active_presets[slot]
}
```

**CHANGES NEEDED:**
- Update to handle new slot numbering (0-19 for user, 0-47 for factory)
- Route to correct save/load functions based on preset type

### 9. Preset Navigation

**UPDATE NEXT/PREV Functions:**
```c
// Current wraps around 0-63
// Need to update to:
// - Arpeggiator: wrap 0-19 for user, 0-47 for factory
// - Sequencer: wrap 0-19 for user, 0-47 for factory
```

---

## Testing Checklist

Once implementation is complete:

- [ ] Verify all 20 arp user slots can save/load from EEPROM (56000-59999)
- [ ] Verify all 20 seq user slots can save/load from EEPROM (60000-67839)
- [ ] Verify no overlap between arp and seq storage
- [ ] Verify gaming settings at 67840 work correctly
- [ ] Verify per-key RGB at 67940 works correctly
- [ ] Verify layer actuation at 68830 works correctly
- [ ] Test that arp presets enforce 64 note limit
- [ ] Test that seq presets allow full 128 notes
- [ ] Test factory preset loading for both types
- [ ] Test HID communication for save/load operations
- [ ] Verify all addresses are within 0-65,535 bounds
- [ ] Power cycle test to ensure EEPROM persistence

---

## Summary

**Completed:**
- All header file address updates
- Structure definitions separated
- Function declarations added
- Memory layout finalized

**Remaining Work:**
1. Arpeggiator.c: Implement separate EEPROM functions for arp/seq
2. Factory presets: Split into two arrays (arp + seq)
3. HID communication: Update to handle both types
4. Runtime: Update preset loading and navigation
5. Testing: Comprehensive validation of all features

**Estimated Complexity:**
- Medium-High: Requires careful handling of different structure sizes
- Main risk: Ensuring correct routing between arp and seq functions
- Testing critical: Must verify no data corruption between preset types
