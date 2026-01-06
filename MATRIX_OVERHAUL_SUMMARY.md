# Matrix Overhaul Summary
## libhmk Architecture Integration for orthomidi5x14

---

## Quick Links
- **[Implementation Comparison](libhmk_implementation_comparison.md)** - Detailed comparison of libhmk vs orthomidi implementations
- **[Overhaul Plan](MATRIX_OVERHAUL_PLAN.md)** - Complete 7-phase migration plan
- **[Actuation Flowchart Analysis](actuation_flowchart_analysis.md)** - Current orthomidi system documentation
- **[DKS Complete Flowchart](DKS_complete_flowchart.md)** - Current DKS implementation

---

## Executive Summary

This project aims to **completely overhaul the orthomidi5x14 matrix scanning system** to adopt libhmk's superior architecture, addressing the primary concerns of **CPU efficiency** and **noise/delay elimination** while maintaining orthomidi's expressive features.

---

## Why Overhaul?

### Current Pain Points:
1. **No noise filtering** - Raw ADC values cause false triggers
2. **Manual calibration** - Users must manually calibrate, no drift compensation
3. **Fragmented rapid trigger** - Part of per-key system, not always available
4. **High memory cost** - 6,720 bytes for per-key actuation across 12 layers

### libhmk Advantages:
1. **Built-in EMA filtering** - Automatic noise immunity (~20 cycles overhead)
2. **Auto-calibration** - Learns rest/bottom-out values, tracks temperature drift
3. **Integrated rapid trigger** - Always available, built into matrix state machine
4. **Efficient memory** - 700 bytes total, no layer duplication

---

## Performance Comparison

| Metric | Current (simple) | Current (per-key+DKS) | Target (libhmk) |
|--------|------------------|------------------------|-----------------|
| **CPU per key** | ~20 cycles | ~35-115 cycles | ~70 cycles |
| **Memory** | ~100 bytes | 6,720 bytes | 700 bytes |
| **Filtering** | ❌ None | ❌ None | ✅ EMA |
| **Calibration** | ❌ Manual | ❌ Manual | ✅ Automatic |
| **Rapid Trigger** | ❌ No | ⚠️ Per-key only | ✅ Built-in |
| **Noise immunity** | ❌ Poor | ❌ Poor | ✅ Excellent |

**Conclusion:** libhmk provides consistent ~70 cycle overhead with superior robustness, better than current per-key mode (35-115 cycles) and much more reliable than simple mode (20 cycles but no features).

---

## What We're Keeping vs Changing

### ✅ KEEPING (orthomidi advantages):

1. **8-threshold DKS** - More expressive than libhmk's 2-zone DKS
   - Current: 4 press + 4 release actions with custom thresholds
   - libhmk: 4 keycode slots × 2 fixed zones (actuation + bottom-out)
   - **Decision:** Keep orthomidi DKS as "advanced key type"

2. **MIDI system** - Full velocity sensitivity, multiple modes
   - libhmk doesn't have MIDI
   - **Decision:** Keep entire MIDI pipeline, update to use filtered values

3. **QMK layer integration** - Standard QMK layers
   - libhmk uses "profiles" instead
   - **Decision:** Keep QMK layers, adapt libhmk features to work with layers

### 🔄 CHANGING (adopting libhmk):

1. **Matrix scanning algorithm**
   - Replace: Raw ADC comparison
   - With: EMA filtering → calibration → distance normalization → RT state machine

2. **Rapid trigger implementation**
   - Replace: Per-key rapidfire (part of per-key actuation)
   - With: Built-in RT state machine (always available, extremum tracking)

3. **Advanced key system**
   - Add: 4 new advanced key types from libhmk
     - Null Bind (monitor 2 keys, register both)
     - Dynamic Keystroke (4 slots, 4 events, simpler than current DKS)
     - Tap-Hold (time-based tap vs hold)
     - Toggle (toggle key state)
   - Keep: Existing 8-threshold DKS as 5th advanced key type

4. **Data structures**
   - Replace: `per_key_actuation_t` (8 bytes × 70 × 12 = 6,720 bytes)
   - With: `key_state_t` (10 bytes × 70 = 700 bytes)

5. **Calibration**
   - Replace: Manual, static values
   - With: Automatic learning during idle periods

---

## Key Features After Overhaul

### 1. EMA Filtering
```c
#define MATRIX_EMA_ALPHA_EXPONENT 4  // Configurable smoothing
filtered = (current + (previous * 15)) >> 4  // Efficient bitshift math
```
- **Benefit:** Eliminates noise-induced false triggers
- **Cost:** ~20 cycles per key

### 2. Automatic Calibration
```c
// During 500ms idle periods:
- Learn rest value (minimum ADC)
- Calculate bottom-out (rest + threshold)
- Track temperature drift automatically
```
- **Benefit:** No user calibration needed, handles drift
- **Cost:** ~5-15 cycles per key (only when idle)

### 3. Rapid Trigger State Machine
```c
State: INACTIVE → DOWN → UP → DOWN (continuous)
       ↑_________↓
Extremum tracking: Release on upward motion, re-press on downward
```
- **Benefit:** Always available, continuous mode, more responsive
- **Cost:** ~25 cycles per key

### 4. Advanced Keys
- **Null Bind:** Simultaneous key registration (e.g., Shift+A)
- **Dynamic Keystroke:** 4 slots, 4 events (simpler config than current DKS)
- **Tap-Hold:** Different actions for tap vs hold
- **Toggle:** Toggle key state on tap, normal on hold
- **orthomidi DKS:** Keep existing 8-threshold system
- **Benefit:** More expressive key behaviors
- **Cost:** ~10-40 cycles per advanced key (only if mapped)

### 5. Unified Configuration
- Per-key actuation points (0-255)
- Global rapid trigger settings + per-key disable bitmap
- Advanced key mappings
- All stored in EEPROM with versioning

---

## Implementation Phases

### Phase 1: Core Matrix (Weeks 1-2)
- Implement data structures
- Implement EMA filtering
- Implement auto-calibration
- Implement distance normalization
- Implement rapid trigger state machine
- **Milestone:** Matrix scanning works with new system

### Phase 2: Advanced Keys (Weeks 3-4)
- Implement 4 advanced key types
- Implement deferred action queue
- Integrate with matrix scan
- **Milestone:** All advanced key types functional

### Phase 3: Integration (Weeks 5-6)
- Refactor matrix scan loop
- Update MIDI integration
- Test compatibility
- **Milestone:** MIDI + layers + advanced keys all work together

### Phase 4: Configuration (Weeks 7-8)
- Design EEPROM layout
- Implement HID commands
- Implement save/load
- **Milestone:** Configuration persists across reboots

### Phase 5: GUI (Weeks 9-10)
- Implement Vial-GUI tabs
- Implement migration wizard
- Test GUI ↔ firmware
- **Milestone:** Users can configure via Vial-GUI

### Phase 6: Testing (Weeks 11-12)
- Unit tests
- Integration tests
- User acceptance testing
- **Milestone:** All tests pass, users approve

### Phase 7: Documentation (Weeks 13-14)
- Write developer docs
- Write user docs
- Create tutorials
- **Milestone:** Release ready

---

## Success Criteria

### Performance:
- ✅ **CPU:** ≤ 100 cycles per key per scan (target: ~70)
- ✅ **Latency:** ≤ 1ms from actuation to HID report
- ✅ **Noise immunity:** No false triggers with ±10 ADC units noise
- ✅ **Calibration:** Converge within 500ms, track ±50 ADC drift

### Functionality:
- ✅ **Rapid trigger:** Re-actuation within 0.1mm (configurable)
- ✅ **Advanced keys:** All 5 types working reliably
- ✅ **MIDI:** Velocity accuracy ±5% vs old system
- ✅ **Compatibility:** Migrate existing configs automatically

### Quality:
- ✅ **Code coverage:** ≥ 80%
- ✅ **Documentation:** Complete API docs + user guide
- ✅ **User testing:** 10+ users approve before release

---

## Migration Path for Existing Users

### Step 1: Backup
- Vial-GUI exports current configuration to file
- Includes all per-key actuation, rapidfire, DKS, MIDI settings

### Step 2: Auto-Migration
- Wizard analyzes current settings
- Converts per-key actuation (0-100 → 0-255)
- Converts rapidfire to rapid trigger settings
- Converts velocity curves to advanced key configs

### Step 3: Manual Adjustments
- User reviews migrated settings
- Tweaks actuation points if needed
- Tests keys in real-time

### Step 4: Flash
- Write new config to firmware
- Keyboard reboots with new system

### Step 5: Verify
- Test all keys
- Compare behavior to old system
- Rollback option available if issues

---

## Risks & Mitigation

### Risk 1: Performance Regression
- **Mitigation:** Benchmark at each phase
- **Fallback:** Keep old code as compile-time option

### Risk 2: Configuration Migration Failure
- **Mitigation:** Extensive testing, backup/restore
- **Fallback:** Manual migration guide

### Risk 3: Advanced Key Complexity
- **Mitigation:** Implement one type at a time
- **Fallback:** Ship with subset, add later

### Risk 4: User Adoption
- **Mitigation:** Clear docs, migration wizard, video tutorials
- **Fallback:** Support old system in parallel during transition

---

## Expected Outcomes

### For Users:
- ✅ **No false triggers** - EMA filtering eliminates noise
- ✅ **No manual calibration** - Automatic learning and drift tracking
- ✅ **Faster rapid trigger** - Built-in, always available, more responsive
- ✅ **More expressive keys** - 5 advanced key types
- ✅ **Easier configuration** - Unified system, better GUI

### For Developers:
- ✅ **Cleaner code** - Unified architecture, less fragmentation
- ✅ **Better performance** - Consistent overhead, optimized hot paths
- ✅ **Easier maintenance** - Single matrix system, comprehensive tests
- ✅ **Easier porting** - Well-documented, follows libhmk patterns

### For the Project:
- ✅ **More competitive** - Matches/exceeds commercial analog keyboards
- ✅ **Better reputation** - Rock-solid reliability, no quirks
- ✅ **Easier to recommend** - "Just works" out of box
- ✅ **Foundation for future** - Advanced features build on solid base

---

## Next Steps

1. **Review this plan** - Team/stakeholders approve approach
2. **Prioritize phases** - Decide if any phases can be parallelized
3. **Set up dev environment** - Testing framework, benchmarks
4. **Begin Phase 1** - Core matrix implementation
5. **Iterate** - Test at each milestone, adjust plan as needed

---

## Questions for Decision

### 1. Layer-based actuation overrides?
- **Option A:** Per-key only (simpler, follows libhmk)
- **Option B:** Add per-layer overrides (more complex, more flexible)
- **Recommendation:** Start with Option A, add B only if users request

### 2. Keep old DKS alongside new dynamic keystroke?
- **Option A:** Yes, keep both (more options, but complexity)
- **Option B:** Merge into one system (simpler, but might lose expressiveness)
- **Recommendation:** Option A - orthomidi DKS is unique advantage

### 3. Migration support timeline?
- **Option A:** 1 release cycle (force migration, simpler)
- **Option B:** 3 release cycles (gradual, more user-friendly)
- **Recommendation:** Option B - don't rush users, provide support period

### 4. GUI redesign scope?
- **Option A:** Minimal - just new features (faster)
- **Option B:** Complete redesign (better UX, more work)
- **Recommendation:** Option A for first release, B in future if needed

---

## Conclusion

This overhaul transforms orthomidi5x14 from a powerful but fragmented analog keyboard firmware into a **unified, efficient, and robust system** that combines the best of both worlds:

- **libhmk's engineering excellence** (EMA, auto-cal, RT state machine)
- **orthomidi's expressive features** (8-threshold DKS, MIDI, layers)

The result will be a firmware that is:
- **Faster** - Consistent ~70 cycle overhead vs current 35-115
- **More reliable** - Built-in filtering and calibration
- **More expressive** - 5 advanced key types
- **Easier to use** - Auto-calibration, unified config
- **Better documented** - Comprehensive docs and migration support

**Expected timeline:** 14 weeks from start to release

**Expected outcome:** The most advanced, reliable, and user-friendly analog keyboard firmware available

**Let's build it!** 🚀

---

## Appendix: File Reference

| File | Purpose |
|------|---------|
| `libhmk_implementation_comparison.md` | Detailed technical comparison of implementations |
| `MATRIX_OVERHAUL_PLAN.md` | Complete 7-phase implementation plan |
| `actuation_flowchart_analysis.md` | Current orthomidi actuation system documentation |
| `DKS_complete_flowchart.md` | Current orthomidi DKS system documentation |
| `MATRIX_OVERHAUL_SUMMARY.md` | This file - high-level overview |

---

**Last Updated:** 2026-01-06
**Status:** Planning Phase
**Next Milestone:** Begin Phase 1 implementation
