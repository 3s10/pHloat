# pHloat Wiring Diagrams

## pH Sensor Wiring Diagram

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          pHloat pH SENSOR ASSEMBLY                        ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   ┌─────────────────┐                 ┌──────────────────────┐         │
│   │   ESP32-S3      │                 │  Atlas Scientific     │         │
│   │  Development    │                 │  pH OEM Circuit      │         │
│   │     Board       │                 │                      │         │
│   │                 │                 │                      │         │
│   │                 │    I2C Wires    │                      │         │
│   │  GPIO 8 (SDA)───┼─────Blue────────┤ SDA                 │         │
│   │  GPIO 9 (SCL)───┼────Yellow───────┤ SCL                 │         │
│   │  3.3V       ────┼─────Red─────────┤ VCC                 │         │
│   │  GND        ────┼────Black────────┤ GND                 │         │
│   │                 │                 │                      │         │
│   │                 │                 │     BNC              │         │
│   │                 │                 │   Connector          │         │
│   └────────┬────────┘                 └──────┬───────────────┘         │
│            │                                 │                         │
│            │ JST                             │                         │
│            │ Connector                       │                         │
│            │                                 │                         │
│   ┌────────▼────────┐                        │                         │
│   │  LiPo Battery   │                        │                         │
│   │  3.7V 2000mAh   │                        │                         │
│   │  (underneath    │                        │                         │
│   │   boards)       │                        │                         │
│   └─────────────────┘                        │                         │
│                                              │                         │
│                                              │                         │
│   ╔══════════════════════════════════════════▼═══════════════════╗     │
│   ║                     Enclosure Wall                            ║     │
│   ║                                                               ║     │
│   ║   ┌────────────────────────────────────────────────┐          ║     │
│   ║   │  BNC Panel Mount Connector (waterproofed)      │          ║     │
│   ║   └──────────────────────┬─────────────────────────┘          ║     │
│   ║                          │                                    ║     │
│   ╚══════════════════════════▼════════════════════════════════════╝     │
│                              │                                          │
│                              │ pH Probe Cable                           │
│                              │                                          │
│                         ┌────▼─────┐                                    │
│                         │ pH Probe │                                    │
│                         │  (BNC)   │                                    │
│                         └──────────┘                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

WIRE COLOR CODE (Suggested):
═══════════════════════════
  Red    = 3.3V Power
  Black  = Ground
  Blue   = SDA (I2C Data)
  Yellow = SCL (I2C Clock)

IMPORTANT NOTES:
═══════════════
⚠  Atlas pH OEM operates at 3.3V ONLY (not 5V!)
⚠  Keep I2C wires short (< 15cm recommended)
⚠  Waterproof BNC connection with silicone sealant
⚠  Never let pH probe dry out - keep in storage solution
⚠  Battery polarity: Red = Positive, Black = Negative
```

---

## Relay Wiring Diagram

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          pHloat RELAY ASSEMBLY                            ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                        ┌─────────────────┐                              │
│                        │     ESP32       │                              │
│                        │  Development    │                              │
│                        │     Board       │                              │
│                        │                 │                              │
│                        │                 │                              │
│                        │    USB Port     │                              │
│                        └────────┬────────┘                              │
│                                 │                                       │
│                                 │ USB Cable                             │
│                                 │                                       │
│                        ┌────────▼────────┐                              │
│                        │  USB Power      │                              │
│                        │   Adapter       │                              │
│                        │   (5V 1A+)      │                              │
│                        └────────┬────────┘                              │
│                                 │                                       │
│                                 │                                       │
│                        ┌────────▼────────┐                              │
│                        │  Wall Outlet    │                              │
│                        │  (110-240V AC)  │                              │
│                        └─────────────────┘                              │
│                                                                         │
│  Optional: Mount in enclosure for protection                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

RELAY CONNECTIONS:
═════════════════
  WiFi:      Built-in (connects to your network)
  ESP-NOW:   Built-in (receives from sensors)
  Power:     USB (always on)
  Web UI:    Access via IP address on your network

IMPORTANT NOTES:
═══════════════
✓  Relay must be powered 24/7 for continuous operation
✓  Place near WiFi router for good signal
✓  Keep away from moisture
✓  Note the MAC address for sensor configuration
```

---

## Complete System Diagram

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                        COMPLETE pHloat SYSTEM                             ║
╚═══════════════════════════════════════════════════════════════════════════╝


    FERMENTER #1              FERMENTER #2              FERMENTER #3
   ┌────────────┐            ┌────────────┐            ┌────────────┐
   │            │            │            │            │            │
   │   ┌────┐   │            │   ┌────┐   │            │   ┌────┐   │
   │   │Tilt│   │            │   │Tilt│   │            │   │Tilt│   │
   │   └────┘   │            │   └────┘   │            │   └────┘   │
   │            │            │            │            │            │
   │   ┌────┐   │            │   ┌────┐   │            │   ┌────┐   │
   │   │ pH │   │            │   │ pH │   │            │   │ pH │   │
   │   │Probe   │            │   │Probe   │            │   │Probe   │
   │   └──┬─┘   │            │   └──┬─┘   │            │   └──┬─┘   │
   └──────┼─────┘            └──────┼─────┘            └──────┼─────┘
          │                         │                         │
          │                         │                         │
    ┌─────▼──────┐           ┌─────▼──────┐           ┌─────▼──────┐
    │  pHloat    │           │  pHloat    │           │  pHloat    │
    │  Sensor #1 │           │  Sensor #2 │           │  Sensor #3 │
    │ (ESP32-S3) │           │ (ESP32-S3) │           │ (ESP32-S3) │
    │  Battery   │           │  Battery   │           │  Battery   │
    └─────┬──────┘           └─────┬──────┘           └─────┬──────┘
          │                        │                         │
          │ ESP-NOW                │ ESP-NOW                 │ ESP-NOW
          │ (Wireless)             │ (Wireless)              │ (Wireless)
          │                        │                         │
          └────────────────────────┼─────────────────────────┘
                                   │
                                   │
                            ┌──────▼───────┐
                            │   pHloat     │
                            │    Relay     │
                            │   (ESP32)    │
                            │              │
                            │ WiFi Enabled │
                            └──────┬───────┘
                                   │
                                   │ WiFi
                                   │ (Internet)
                                   │
                            ┌──────▼────────────┐
                            │  Google Sheets    │
                            │                   │
                            │ ┌───────────────┐ │
                            │ │ Fermenter #1  │ │
                            │ │ pH + Tilt SG  │ │
                            │ ├───────────────┤ │
                            │ │ Fermenter #2  │ │
                            │ │ pH + Tilt SG  │ │
                            │ ├───────────────┤ │
                            │ │ Fermenter #3  │ │
                            │ │ pH + Tilt SG  │ │
                            │ └───────────────┘ │
                            └───────────────────┘

DATA FLOW:
═════════
1. pH Sensors take readings every 60 seconds
2. Sensors send data to Relay via ESP-NOW (wireless, no WiFi needed)
3. Relay applies calibration corrections
4. Relay saves data locally (SPIFFS storage)
5. Relay uploads to Google Sheets (if WiFi enabled)
6. Google Sheets matches pH data with Tilt gravity readings by timestamp
7. Access data via:
   - Relay web interface (download CSV)
   - Google Sheets (automatic charts)
   - Tilt app (can view combined data)
```

---

## Pin Connections Detail

### ESP32-S3 to Atlas pH OEM

```
ESP32-S3                 Atlas pH OEM
─────────                ─────────────
         ┌─────────────┐
GPIO 8   │──────SDA────│ Pin 1 (SDA)
         │             │
GPIO 9   │──────SCL────│ Pin 2 (SCL)
         │             │
3.3V     │──────VCC────│ Pin 3 (VCC)
         │             │
GND      │──────GND────│ Pin 4 (GND)
         └─────────────┘

⚠ CRITICAL: Use 3.3V, NOT 5V!
Atlas pH OEM will be damaged by 5V
```

### Battery Connection

```
LiPo Battery             ESP32-S3
────────────             ─────────
                ┌──────────────┐
Red Wire (+)    │───── VCC ────│
                │              │
Black Wire (-)  │───── GND ────│
                └──────────────┘

⚠ VERIFY POLARITY BEFORE CONNECTING!
Wrong polarity can destroy board
```

### Probe Connection

```
pH Probe                 Atlas pH OEM
────────                 ────────────
            ┌──────────────────┐
BNC Male    │──── BNC Female ──│
Connector   │                  │
            └──────────────────┘

Then connect Atlas BNC to panel-mount BNC on enclosure
```

---

## Power Budget

### pH Sensor (ESP32-S3 + Atlas pH OEM)

```
MODE            CURRENT    DURATION       ENERGY
────────────────────────────────────────────────
Deep Sleep      10 µA      59.9 sec       0.17 mAh
Wake Up         50 mA      0.1 sec        0.001 mAh
Take Reading    50 mA      1.0 sec        0.014 mAh
Transmit Data   80 mA      0.1 sec        0.002 mAh
────────────────────────────────────────────────
Per Minute:                               0.187 mAh
Per Hour:                                 11.2 mAh
Per Day:                                  269 mAh
────────────────────────────────────────────────

Battery Life Calculation:
─────────────────────────
2000 mAh battery ÷ 269 mAh/day = 7.4 days (theoretical max)
With real-world deep-sleep overhead:   ~5-7 days
With a 3500 mAh 18650 cell:            ~10-14 days

Actual battery life varies with ambient temperature, battery age,
WiFi signal strength, and transmit retry count. For extended runtime
see 18650_BATTERY_GUIDE.md.
```

### Relay (ESP32)

```
MODE            CURRENT
───────────────────────
Normal          150 mA
Peak (WiFi TX)  240 mA

Always powered by USB wall adapter
```

---

## Troubleshooting Wiring Issues

### No Communication Between Sensor and Relay

```
Check:
  □ Relay is powered on
  □ Sensor MAC address matches relay's actual MAC
  □ Distance < 100 meters
  □ No metal walls between sensor and relay
  □ Both devices are powered
```

### pH Readings Always 0.00 or 14.00

```
Check:
  □ I2C connections (SDA/SCL not swapped?)
  □ Power is 3.3V, not 5V
  □ Probe is connected to Atlas circuit
  □ Probe is not dried out
  □ Atlas circuit LED is on
```

### Sensor Not Taking Readings

```
Check:
  □ Battery is charged (> 3.5V)
  □ Battery polarity correct
  □ Firmware uploaded successfully
  □ Serial monitor shows activity
  □ Check for error messages in serial
```

### Web Interface Not Accessible

```
Relay:
  □ Connected to WiFi (check serial monitor)
  □ Note IP address from serial monitor
  □ Try relay's AP mode (pHloat-Relay)
  □ Firewall not blocking access

Sensor:
  □ Hold BOOT button during power-on
  □ Wait 30 seconds for AP to start
  □ Look for "pHloat-XXXXXXXX" network
```

---

## Best Practices

### Wire Management

```
✓ Use different colored wires for easy tracing
✓ Keep I2C wires twisted together to reduce interference
✓ Strain relief at all connections
✓ Label wires with tape or heat shrink
✓ Take photos before closing enclosure
```

### Waterproofing

```
✓ Silicone sealant on all enclosure penetrations
✓ Let sealant cure 24 hours before use
✓ Test waterproofing with spray bottle before deploying
✓ Use cable glands for professional installations
✓ Keep electronics above liquid level
```

### Safety

```
⚠ Never apply 5V to Atlas pH OEM (3.3V only!)
⚠ Check battery polarity before connecting
⚠ Use correct LiPo charging circuit
⚠ Don't over-discharge batteries (< 3.0V)
⚠ Use waterproof enclosures near fermenters
```

---

**For assembly instructions, see ASSEMBLY.md**
**For troubleshooting, see README.md**
