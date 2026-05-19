# pHloat Integration Options Comparison

## Quick Decision Guide

**Already have a Tilt Hydrometer and Raspberry Pi?**
→ **Use Tilt Pi Integration** (Option 1)

**Don't have a Raspberry Pi or Tilt?**
→ **Use Standalone System** (Option 2)

**Want the absolute simplest setup?**
→ **Use Standalone System** (Option 2)

**Want the best data integration and lowest cost?**
→ **Use Tilt Pi Integration** (Option 1)

---

## Option 1: Tilt Pi Integration

### System Architecture

```
pH Sensors → WiFi → Raspberry Pi (Tilt Pi) → Google Sheets
Tilt Hydrometer → Bluetooth → Raspberry Pi (Tilt Pi) → Google Sheets
```

### Hardware Needed

**Per pH Sensor:**
- ESP32-S3 + Atlas pH OEM (~$155-200)
- **Option A:** pHloat Relay as WiFi bridge (~$25)
- **Option B:** Modify sensor to use WiFi directly (no relay needed)

**Central Hub:**
- Raspberry Pi (already have for Tilt Pi) - $0 additional
- No extra relays needed beyond first one

### Total Cost (3 sensors)

| Component | Cost |
|-----------|------|
| Raspberry Pi | $0 (already have) |
| 3x pH Sensors | $155-200 each = $465-600 |
| 1x Relay (WiFi bridge) | $25 |
| Calibration supplies | $50 |
| **Total** | **$540-675** |

**vs. Standalone:** Save $50-75 (no relay per sensor)

### Pros ✅

- ✅ **Best integration** - Direct database access for precise matching
- ✅ **Unified dashboard** - One interface for Tilt + pHloat
- ✅ **Lower cost** - One relay for all sensors (or none if using WiFi)
- ✅ **Better matching** - ±1 second accuracy vs ±60 seconds
- ✅ **Single Google Sheets setup** - Configure once for everything
- ✅ **Local data backup** - Everything stored on Pi
- ✅ **Easier troubleshooting** - All logs in one place
- ✅ **Scalable** - Add unlimited sensors without more relays

### Cons ❌

- ❌ Requires Raspberry Pi (but you already have one for Tilt)
- ❌ Slightly more complex initial setup (10 minutes)
- ❌ Pi must stay powered on (but it already is for Tilt)
- ❌ Requires SSH access to Pi for initial install

### Setup Time

- **Initial install on Pi:** 10 minutes (automated script)
- **Per sensor configuration:** 5 minutes
- **Total for 3 sensors:** 25 minutes

### Technical Details

**Communication:**
- Sensors → Relay: ESP-NOW (wireless)
- Relay → Pi: HTTP/WiFi
- OR Sensors → Pi: HTTP/WiFi directly (no relay)

**Data Matching:**
- Direct SQLite database queries
- Matches within ±1 second (vs ±60 seconds)
- No API delays or rate limits

**Storage:**
- Pi's SD card (GB available)
- Can store years of data
- Easy to backup entire system

### Best For

- ✅ Existing Tilt Pi users
- ✅ Brewers with multiple fermenters
- ✅ Those wanting unified data
- ✅ Home network environments
- ✅ Budget-conscious setups

---

## Option 2: Standalone System

### System Architecture

```
pH Sensors → ESP-NOW → pHloat Relay → WiFi → Google Sheets
Tilt Hydrometer → Tilt App → Google Sheets
```

### Hardware Needed

**Per pH Sensor:**
- ESP32-S3 + Atlas pH OEM (~$155-200)

**Per Relay:** (one relay can handle ~6 sensors)
- ESP32 + USB power (~$25)

### Total Cost (3 sensors)

| Component | Cost |
|-----------|------|
| 3x pH Sensors | $155-200 each = $465-600 |
| 1x Relay | $25 |
| Calibration supplies | $50 |
| **Total** | **$540-675** |

**Same as Tilt Pi option** for small setups

### Pros ✅

- ✅ **Simpler hardware** - No Raspberry Pi needed
- ✅ **Portable** - Works anywhere with WiFi
- ✅ **Independent** - Doesn't rely on Pi staying on
- ✅ **Faster to deploy** - Upload code and go
- ✅ **No SSH needed** - All config via web interface
- ✅ **Lower power** - Only relay draws continuous power

### Cons ❌

- ❌ **More relays needed** - One per ~6 sensors at scale
- ❌ **Separate configuration** - Each relay configured individually
- ❌ **Timestamp matching** - Less precise (±60 seconds)
- ❌ **Limited storage** - ESP32 flash (MB not GB)
- ❌ **Multiple dashboards** - One per relay
- ❌ **More Google Sheets setup** - Configure each relay

### Setup Time

- **Per relay:** 10 minutes
- **Per sensor:** 5 minutes
- **Google Apps Script:** 5 minutes
- **Total for 3 sensors:** 30 minutes

### Technical Details

**Communication:**
- Sensors → Relay: ESP-NOW (wireless)
- Relay → Google Sheets: HTTPS/WiFi

**Data Matching:**
- Via Google Sheets timestamp comparison
- Matches within ±60 seconds
- Dependent on network reliability

**Storage:**
- SPIFFS (~1-3 MB available)
- Stores ~100+ days of data
- Manual download required for backup

### Best For

- ✅ Those without Raspberry Pi
- ✅ Simple 1-3 sensor setups
- ✅ Remote locations without Pi
- ✅ Mobile/temporary installations
- ✅ Those wanting simplest hardware

---

## Feature Comparison

| Feature | Tilt Pi Integration | Standalone |
|---------|-------------------|-----------|
| **Requires Raspberry Pi** | Yes | No |
| **Requires pHloat Relay** | 1 for all (or 0 with WiFi) | 1 per ~6 sensors |
| **Setup Complexity** | Medium | Simple |
| **Data Matching Accuracy** | ±1 second | ±60 seconds |
| **Storage Capacity** | GB (years) | MB (months) |
| **Unified Dashboard** | Yes | No (one per relay) |
| **Google Sheets Config** | Once | Per relay |
| **Scalability** | Excellent | Good |
| **Power Consumption** | Pi + 1 relay | 1+ relays |
| **Cost (1 sensor)** | $230-275 | $230-275 |
| **Cost (10 sensors)** | $1,575-2,025 | $1,625-2,075 |
| **Local Data Access** | Excellent | Good |
| **Backup Difficulty** | Easy | Medium |
| **Troubleshooting** | Easy (one place) | Medium (multiple) |

---

## Hybrid Approach

**Can I use both?**

Yes! You can mix and match:

- **Some sensors → Tilt Pi** (home brewery)
- **Some sensors → Standalone relay** (remote location)
- **All data → Same Google Sheet**

This gives you flexibility for different environments.

---

## Migration Path

### From Standalone to Tilt Pi

1. Install pHloat server on Tilt Pi
2. Change relay Google Sheets URL to point to Pi
3. Keep relays running (they become WiFi bridges)
4. Done! No sensor changes needed

**Time:** 15 minutes

### From Tilt Pi to Standalone

1. Set up Google Apps Script
2. Update relay configuration to point to Google Sheets
3. Done! No sensor changes needed

**Time:** 10 minutes

---

## Recommendations by Use Case

### Homebrewer (1-3 fermenters)
**Recommendation:** Either option works great!
- Have Tilt Pi? → **Tilt Pi Integration**
- Don't have Pi? → **Standalone**

### Nano Brewery (3-6 fermenters)
**Recommendation:** **Tilt Pi Integration**
- Better data management
- Lower cost at scale
- Unified monitoring

### Small Brewery (6-10+ fermenters)
**Recommendation:** **Tilt Pi Integration**
- Significant cost savings
- Much easier to manage
- Professional data integration

### Mobile/Remote Setups
**Recommendation:** **Standalone**
- No dependency on Pi
- Works anywhere with WiFi
- Self-contained

### Teaching/Research
**Recommendation:** **Tilt Pi Integration**
- Better data access
- Easier to export/analyze
- Centralized logging

---

## Decision Tree

```
Do you have a Raspberry Pi running Tilt Pi?
├─ YES → Do you want the best integration?
│  ├─ YES → Use Tilt Pi Integration ✅
│  └─ NO → Want simplest setup?
│     ├─ YES → Use Standalone
│     └─ NO → Use Tilt Pi Integration ✅
│
└─ NO → Want to buy a Raspberry Pi ($35-75)?
   ├─ YES → Use Tilt Pi Integration ✅
   └─ NO → Use Standalone ✅
```

---

## Bottom Line

### Choose **Tilt Pi Integration** if:
- You already have Tilt Pi (strongly recommended)
- You want unified pH + gravity monitoring
- You're monitoring 3+ fermenters
- You want the best data matching
- You want lowest long-term cost

### Choose **Standalone** if:
- You don't have a Raspberry Pi
- You want simplest hardware
- You need portable monitoring
- You're only monitoring 1-2 fermenters
- You want fastest initial setup

---

**Both options are fully functional and production-ready!**

The "best" choice depends on your existing equipment and preferences. You can't go wrong with either.

**Questions?** See the respective documentation:
- Tilt Pi: `TILT_PI_INTEGRATION.md`
- Standalone: `README.md` and `QUICK_START.md`
