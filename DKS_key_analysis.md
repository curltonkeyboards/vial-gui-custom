# DKS (Dynamic Keystroke) Key Analysis
## orthomidi5x14 Firmware

## Current Status: **DEFINED BUT NOT IMPLEMENTED**

### What are DKS Keys?

DKS (Dynamic Keystroke) keys are defined as **"multi-action analog keys"** with 50 available slots.

**Keycode Range:** `0xED00` to `0xED31` (50 slots: DKS_00 through DKS_49)

**Location of Definition:** `orthomidi5x14.h` lines 136-190

```c
// =============================================================================
// DKS (DYNAMIC KEYSTROKE) KEYCODES (0xED00-0xED31)
// 50 DKS slots for multi-action analog keys
// =============================================================================

#define DKS_00  0xED00
#define DKS_01  0xED01
#define DKS_02  0xED02
...
#define DKS_49  0xED31
```

---

## Investigation Results

### Files Searched:
- `orthomidi5x14.c` (543KB - main firmware file)
- `orthomidi5x14.h` (35KB - header file)
- `arpeggiator.c`, `arpeggiator_hid.c`
- All keymap files
- process_record_user() function

### Findings:

**✗ NO IMPLEMENTATION FOUND**

1. **No Processing Code**: There is no code in `process_record_user()` or any other function that handles keycodes in the range `0xED00-0xED31`

2. **No Data Structures**: No arrays, structs, or configuration data for storing DKS settings

3. **No HID Handlers**: No HID commands for configuring DKS keys (unlike per-key actuation which has HID commands 0xE0-0xE3)

4. **No Matrix Processing**: No special handling in matrix scanning or analog processing for DKS keys

---

## What DKS Keys WOULD Do (If Implemented)

Based on the name **"multi-action analog keys"**, DKS keys would likely:

### Concept: Analog-Triggered Multi-Action System

A DKS key would allow **multiple different actions** based on **analog travel depth**:

```
Example DKS_00 Configuration:
┌─────────────────────────────────────────────┐
│  Travel: 0.0mm - 0.5mm → No action          │
│  Travel: 0.5mm - 1.0mm → Send MIDI note 60  │
│  Travel: 1.0mm - 1.5mm → Send MIDI note 64  │
│  Travel: 1.5mm - 2.0mm → Send MIDI note 67  │
│  Travel: 2.0mm - 2.5mm → Send CC #1         │
└─────────────────────────────────────────────┘
```

### Potential Use Cases:
1. **Progressive MIDI Layers**: Different notes/CCs at different travel depths
2. **Velocity Zones**: Different velocity curves per zone
3. **Multi-Instrument Keys**: Piano at shallow press, strings at deep press
4. **Dynamic Expression**: Gradually change parameters as key travels
5. **Gaming Analog Actions**: Light press = walk, deep press = run

---

## How DKS Keys WOULD Fit Into Actuation System (Hypothetical)

If DKS were implemented, here's how they would integrate:

### Modified Matrix Scanning Flow:

```
┌─────────────────────────────────────────────────────────────┐
│                 MATRIX SCAN (Every Cycle)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
          ┌──────────────────────────────┐
          │  For each key (row, col)     │
          └──────────┬───────────────────┘
                     │
                     ↓
          ┌──────────────────────────────┐
          │  Read analog travel value    │
          │  (0-100 range, 0-2.5mm)      │
          └──────────┬───────────────────┘
                     │
                     ↓
          ┌──────────────────────────────┐
          │  Get keycode at position     │
          │  keycode = get_keycode()     │
          └──────────┬───────────────────┘
                     │
                     ↓
          ┌──────────────────────────────┐
          │  Check keycode type          │
          └────┬─────────┬───────────────┘
               │         │
               │         └──→ Regular MIDI Key
               │             (Normal processing)
               │
               ↓
    ┌──────────────────────────────┐
    │  Is keycode in DKS range?    │
    │  (0xED00 - 0xED31)           │
    └────┬──────────────┬──────────┘
         │ NO           │ YES
         │              │
         ↓              ↓
    [Normal Path]  ┌────────────────────────────────┐
                   │  DKS Processing (HYPOTHETICAL) │
                   ├────────────────────────────────┤
                   │                                │
                   │  1. Get DKS slot number        │
                   │     slot = keycode - 0xED00    │
                   │                                │
                   │  2. Load DKS configuration     │
                   │     dks_config[slot]           │
                   │                                │
                   │  3. Check travel zones:        │
                   │     for each zone:             │
                   │       if (travel >= zone_start │
                   │           && travel < zone_end)│
                   │         Execute zone action    │
                   │                                │
                   │  4. Zone actions might be:     │
                   │     - Send MIDI note           │
                   │     - Send MIDI CC             │
                   │     - Send keycode             │
                   │     - Trigger macro            │
                   │     - Change layer             │
                   │                                │
                   └────────────────────────────────┘
```

### Hypothetical Data Structure:

```c
// NOT IN ACTUAL CODE - CONCEPTUAL ONLY
#define MAX_DKS_ZONES 8  // Up to 8 action zones per key

typedef enum {
    DKS_ACTION_NONE,
    DKS_ACTION_MIDI_NOTE,
    DKS_ACTION_MIDI_CC,
    DKS_ACTION_KEYCODE,
    DKS_ACTION_MACRO,
    DKS_ACTION_LAYER
} dks_action_type_t;

typedef struct {
    uint8_t travel_start;      // 0-100 (travel threshold to activate)
    uint8_t travel_end;        // 0-100 (travel threshold to deactivate)
    dks_action_type_t action;  // What to do in this zone
    uint16_t parameter1;       // Note, CC#, keycode, macro ID, etc.
    uint16_t parameter2;       // Velocity, CC value, etc.
    uint8_t flags;             // Momentary, toggle, etc.
} dks_zone_t;

typedef struct {
    bool enabled;
    uint8_t zone_count;        // Number of active zones (1-8)
    dks_zone_t zones[MAX_DKS_ZONES];
} dks_config_t;

// Would need 50 slots (one per DKS key)
dks_config_t dks_configs[50];  // Not actually in code
```

### Hypothetical Processing Function:

```c
// NOT IN ACTUAL CODE - CONCEPTUAL ONLY
void process_dks_key(uint8_t slot, uint8_t row, uint8_t col, uint8_t travel) {
    if (slot >= 50 || !dks_configs[slot].enabled) return;

    dks_config_t *config = &dks_configs[slot];

    // Check each zone to see if travel is within range
    for (uint8_t i = 0; i < config->zone_count; i++) {
        dks_zone_t *zone = &config->zones[i];

        if (travel >= zone->travel_start && travel < zone->travel_end) {
            // Execute the action for this zone
            switch (zone->action) {
                case DKS_ACTION_MIDI_NOTE:
                    // Send MIDI note with velocity based on travel
                    uint8_t velocity = calculate_velocity(travel, zone);
                    midi_send_noteon(channel, zone->parameter1, velocity);
                    break;

                case DKS_ACTION_MIDI_CC:
                    // Send MIDI CC
                    midi_send_cc(channel, zone->parameter1, zone->parameter2);
                    break;

                case DKS_ACTION_KEYCODE:
                    // Send regular keycode
                    register_code16(zone->parameter1);
                    break;

                // ... other actions
            }
        }
    }
}
```

---

## Why DKS Keys Would Be Powerful

### Comparison to Regular Keys:

| Feature | Regular MIDI Key | DKS Key (Hypothetical) |
|---------|------------------|------------------------|
| **Actions per key** | 1 (single note/CC) | Up to 8 zones with different actions |
| **Analog response** | Single actuation point | Multiple zones responding to depth |
| **Configurability** | Note + velocity | Zone-based multi-action sequences |
| **Use case** | Simple MIDI notes | Complex expression, layered sounds |

### Example: DKS_00 as "Expression Pad"

```
┌─────────────────────────────────────────────────────────────┐
│  Zone 1: 0-20% travel   → MIDI Note 60 (C4) Piano Sound    │
│  Zone 2: 20-40% travel  → MIDI Note 64 (E4) Strings        │
│  Zone 3: 40-60% travel  → MIDI Note 67 (G4) Brass          │
│  Zone 4: 60-80% travel  → MIDI CC #1 (Modulation)          │
│  Zone 5: 80-100% travel → MIDI CC #7 (Volume Swell)        │
└─────────────────────────────────────────────────────────────┘

Result: Single key creates chord progression + expression
```

---

## Integration with Per-Key Actuation

DKS keys would **complement** per-key actuation:

### Per-Key Actuation
- **Purpose**: Fine-tune actuation point, deadzone, velocity curve
- **Scope**: Single binary state (pressed/released) with analog velocity
- **Use case**: Precise feel and responsiveness

### DKS Keys
- **Purpose**: Multiple actions based on analog depth
- **Scope**: Multiple states/zones within single keypress
- **Use case**: Complex expression and layered functionality

### Combined Example:

```
Key assigned to DKS_00 with per-key actuation enabled:

┌─────────────────────────────────────────────────────────────┐
│  Per-Key Settings:                                          │
│  - Actuation: 1.0mm (triggers first DKS zone)              │
│  - Deadzone Top: 0.1mm                                      │
│  - Velocity Curve: Aggro (for zones that use velocity)     │
│                                                             │
│  DKS Zones:                                                 │
│  - Zone 1 (1.0-1.5mm): Piano note (uses velocity curve)    │
│  - Zone 2 (1.5-2.0mm): String note                         │
│  - Zone 3 (2.0-2.5mm): CC modulation                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Current Status Summary

### What EXISTS:
✓ Keycode definitions (0xED00-0xED31)
✓ 50 available slots
✓ Comment describing purpose: "multi-action analog keys"

### What DOES NOT EXIST:
✗ Processing logic in `process_record_user()`
✗ Data structures for DKS configuration
✗ HID commands for configuring DKS keys
✗ Matrix scanning integration
✗ EEPROM storage for DKS settings
✗ GUI support in Vial

---

## To Implement DKS Keys Would Require:

1. **Data Structure** (~5KB): Zone definitions for 50 slots
2. **HID Protocol**: Commands to configure zones from GUI
3. **Processing Logic**: Check travel depth and execute zone actions
4. **EEPROM Storage**: Save/load configurations
5. **GUI Integration**: Vial UI for configuring zones
6. **Matrix Integration**: Call DKS processing during scan

**Estimated Implementation Effort**: Medium-Large (comparable to implementing per-key actuation system)

---

## Conclusion

**DKS keys are currently a PLACEHOLDER for future functionality.**

The keycodes are reserved but not yet implemented. When a DKS key is pressed today:
- It would be treated like any undefined keycode
- No special processing occurs
- No actions are triggered

To actually use DKS functionality, significant firmware development would be needed to implement the zone-based action system described above.

---

## Recommendation

If you want to use analog multi-action keys TODAY, you would need to:

1. Implement the DKS processing system (or request it as a feature)
2. Add HID commands for configuration
3. Update Vial GUI to support DKS configuration
4. Define your zone configurations and actions

Alternatively, you can achieve similar functionality using:
- **Multiple keys** with different actuation points
- **Layer switching** based on analog values
- **MIDI velocity layering** on the DAW side
