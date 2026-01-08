# Velocity Calculation Methods

This document describes the velocity calculation modes available for Hall effect keyboards in the orthomidi5x14 firmware.

## Overview

Velocity determines how hard/fast a key was pressed and maps to MIDI velocity (1-127). The firmware supports 4 velocity modes that measure different aspects of keystroke dynamics.

## Data Flow

```
Raw ADC → EMA Filter → LUT Linearization → key->distance (0-255)
                                                  │
                              ┌───────────────────┼───────────────────┐
                              ▼                   ▼                   ▼
                         Mode 0-3            Aftertouch          Key State
                         (matrix.c)          (matrix.c)          Detection
                              │
                              ▼
                       raw_velocity (0-255)
                              │
                              ▼
                   get_he_velocity_from_position()
                              │
                       ┌──────┴──────┐
                       ▼             ▼
                  apply_curve()   Scale to
                  (piecewise)     [min, max]
                       │             │
                       └──────┬──────┘
                              ▼
                    Final MIDI Velocity (1-127)
```

---

## Mode 0: Fixed Velocity

**Description:** Returns a fixed velocity value regardless of how the key is pressed.

**Use Case:** When consistent velocity is desired (organ-style playing).

**Behavior:**
- All keypresses produce the same velocity
- Velocity curves still apply
- Useful for non-expressive playing

```
Input: Any keypress
Output: Fixed value (configured via settings)
```

---

## Mode 1: Peak Travel at Apex

**Description:** Measures the maximum travel distance reached before the key starts returning (apex detection).

**How It Works:**
1. Key starts moving (crosses deadzone threshold)
2. Track peak travel distance continuously
3. Monitor instantaneous speed
4. When speed drops drastically (apex detected), capture peak travel as velocity
5. Scale peak travel (0-240) to raw velocity (0-255)

**Formula:**
```
raw_velocity = (peak_travel * 255) / 240
```

**Diagram:**
```
Travel
  │          ●───●───●  ← Peak travel captured here
  │         ╱         ╲
  │        ╱   Apex    ╲
  │       ╱   detected  ╲
  │      ╱               ╲
  └─────●─────────────────●──────► Time
        │                 │
   Start moving      Speed drops
   (deadzone)        (apex trigger)
```

**Behavior:**
- Press 30% depth → ~30% velocity
- Press 80% depth → ~80% velocity
- Speed doesn't matter, only depth
- Actuation point is ignored (only deadzone used)

**Best For:** Players who want velocity based purely on how far they press the key.

---

## Mode 2: Speed-Based (Deadzone to Actuation)

**Description:** Measures the average speed from when the key starts moving until it crosses the actuation point.

**How It Works:**
1. Record timestamp when key crosses deadzone (t_start)
2. Record timestamp when key crosses actuation point (t_end)
3. Calculate time delta: `time_delta = t_end - t_start`
4. Calculate average speed based on travel distance and time
5. Scale speed to velocity using configurable scale factor

**Formula:**
```
avg_speed = (actuation_travel * 1000) / time_delta_ms
raw_velocity = (avg_speed * velocity_speed_scale) / 100
```

**Diagram:**
```
Travel
  │                 Actuation Point
  │                       │
  │       ●───────────────●──────●
  │      ╱                │       ╲
  │     ╱                 │        ╲
  │    ╱                  │         ╲
  │   ╱                   │          ╲
  └──●────────────────────│───────────●──► Time
     │                    │
  t_start             t_end
  (deadzone)       (actuation)

     ◄─── time_delta ────►
```

**Behavior:**
- Fast press → high velocity
- Slow press → low velocity
- Travel depth beyond actuation doesn't matter
- Deeper actuation point = more reliable measurement (longer travel distance)

**Best For:** Players who want velocity based on keystroke speed, similar to traditional piano action.

**Tip:** Set a deeper actuation point for more consistent speed measurements.

---

## Mode 3: Combined Speed + Travel (70/30 Blend)

**Description:** Combines both peak speed and peak travel measurements, weighted 70% speed and 30% travel.

**How It Works:**
1. Track both peak instantaneous speed AND peak travel
2. When apex is detected (speed drops drastically):
   - Calculate speed component: `speed_raw = (peak_speed * scale) / 10`
   - Calculate travel component: `travel_raw = (peak_travel * 255) / 240`
   - Blend: `raw_velocity = (speed_raw * 70 + travel_raw * 30) / 100`

**Formula:**
```
speed_component = (peak_speed * velocity_speed_scale) / 10
travel_component = (peak_travel * 255) / 240
raw_velocity = (speed_component * 70 + travel_component * 30) / 100
```

**Diagram:**
```
Travel
  │          ●───●───●  ← Both peak_speed and peak_travel captured
  │         ╱│        ╲
  │        ╱ │ peak    ╲
  │       ╱  │ speed    ╲
  │      ╱   ▼           ╲
  └─────●─────────────────●──────► Time
                          │
                    Apex detected
                    (speed drops)

        Final = 70% speed + 30% travel
```

**Behavior:**
- Fast + deep press → highest velocity
- Fast + shallow press → medium-high velocity (mostly speed)
- Slow + deep press → medium velocity (30% from travel)
- Slow + shallow press → lowest velocity

**Best For:** Players who want a balanced response considering both attack speed and key depth.

---

## Velocity Curves

After raw velocity (0-255) is calculated, it passes through a velocity curve before final scaling.

**Available Curves:**
- Linear
- Soft (logarithmic-like)
- Hard (exponential-like)
- Custom (user-defined points)

**Curve Application:**
```
raw_velocity (0-255) → apply_curve() → curved_value (0-255) → scale to [min_vel, max_vel]
```

The curve shapes how the raw measurement maps to final velocity:
- **Soft curve:** Easier to get high velocities, harder to play quietly
- **Hard curve:** Easier to play quietly, requires more force for loud
- **Linear:** Direct 1:1 mapping

---

## Configuration Parameters

| Parameter | Description | Range |
|-----------|-------------|-------|
| `velocity_mode` | Selects mode 0-3 | 0-3 |
| `velocity_speed_scale` | Scaling factor for speed modes | 1-255 |
| `he_velocity_min` | Minimum output velocity | 1-127 |
| `he_velocity_max` | Maximum output velocity | 1-127 |
| `midi_actuation` | Actuation point (% of travel) | 1-100 |

---

## Mode Comparison

| Aspect | Mode 0 | Mode 1 | Mode 2 | Mode 3 |
|--------|--------|--------|--------|--------|
| **Measures** | Nothing | Peak depth | Speed | Speed + Depth |
| **Responds to** | N/A | How far | How fast | Both |
| **Actuation point** | N/A | Ignored | Critical | Ignored |
| **Apex detection** | No | Yes | No | Yes |
| **Best for** | Consistent play | Depth control | Speed control | Balanced feel |

---

## Implementation Details

### Key State Tracking

Each key maintains:
```c
typedef struct {
    bool velocity_captured;      // Has velocity been captured this press?
    uint8_t peak_speed;          // Peak instantaneous speed observed
    uint8_t peak_travel;         // Peak travel distance observed
    uint8_t travel_at_actuation; // Travel when actuation crossed
    uint8_t raw_velocity;        // Final raw velocity (0-255)
    uint16_t last_time;          // Timestamp for delta calculations
} midi_key_state_t;
```

### Apex Detection

Apex is detected when:
1. Key was previously moving fast (speed > threshold)
2. Current speed drops significantly below previous peak
3. This indicates the key has stopped accelerating and is at maximum travel

### Speed Calculation

Instantaneous speed is calculated each scan cycle:
```c
speed = abs(current_travel - previous_travel) / time_delta_ms
```

Peak speed is the maximum observed during the keystroke.
