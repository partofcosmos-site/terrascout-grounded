# TerraScout Rover - Engineering Build Journal

**Project:** TerraScout Grounded (Autonomous Telemetry Rover)  
**Author / Lead Engineer:** TerraScout Hardware & Firmware Division  
**Repository:** `terrascout-grounded`  
**License:** CERN-OHL-P v2 (Hardware) / MIT (Software)  

---

## Executive Summary & Mission Scope

TerraScout is an open-source, dual-deck autonomous differential rover engineered for indoor and semi-rough surface telemetry gathering, environmental sensing, and obstacle avoidance. Designed from first principles to be reproducible on standard desktop FDM 3D printers, TerraScout combines parametric CAD, microsecond-accurate embedded MicroPython firmware, and a modular electronic sensor array.

```
                  +-----------------------------------+
                  |      TERRASCOUT SYSTEM STACK      |
                  +-----------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
  [PHYSICAL CHASSIS]                              [EMBEDDED FIRMWARE]
  - Dual-Deck OpenSCAD Platform                   - MicroPython / CircuitPython
  - 2x N20 Micro Metal Gearmotors                 - Dual PID Velocity Control Loops
  - 43mm Rubber Traction Wheels                   - HC-SR04 Median Filter Ultrasonic
  - 15mm Steel Ball Caster                        - SG90 Look-Ahead Panning Turret
  - M3 Hex Brass Standoff Core                    - BME280 Environmental Telemetry
  - 2S 18650 Li-ion Battery Sled                  - SSD1306 128x64 OLED Live HUD
                                                  - Streaming JSON Telemetry Bus
```

---

## Logged Engineering Time Summary

| Sprint / Milestone | Focus Area | Hours Logged | Status |
|---|---|:---:|:---:|
| **MS-01** | Mission Specs, Kinematic Sizing & Architecture | 6.5 hrs | **COMPLETED** |
| **MS-02** | Powertrain Selection, Driver H-Bridge & Power Budget | 8.0 hrs | **COMPLETED** |
| **MS-03** | Parametric Dual-Deck OpenSCAD Modeling & FDM Tolerancing | 10.5 hrs | **COMPLETED** |
| **MS-04** | Embedded MicroPython Firmware & Discrete PID Loops | 7.5 hrs | **COMPLETED** |
| **MS-05** | Obstacle Avoidance State Machine & HUD Telemetry | 6.0 hrs | **COMPLETED** |
| **TOTAL** | **Full System Orchestration** | **38.5 hrs** | **PHASE 1 COMPLETE** |

---

## Milestone 01: Concept Genesis & System Architecture
*Date: September 2026 | Logged: 6.5 Hours*

### Design Requirements & Constraints
1. **Physical Footprint:** Maximum length $\le 150\,\text{mm}$, width $\le 110\,\text{mm}$ to allow tight navigation through standard domestic door thresholds and cluttered test courses.
2. **Kinematic Configuration:** Differential drive (two driven wheels with zero-radius pivot capability) + omnidirectional trailing low-friction ball caster.
3. **Mass Distribution:** Heavy components (18650 Li-ion cells, steel motor gearboxes) concentrated on the lowest plane to drop the Center of Gravity (CoG) below the drive axle centerline ($Z_{\text{CoG}} \le 18\,\text{mm}$).
4. **Modularity:** Separation of powertrain/power storage (Bottom Deck) from control intelligence, communications, and sensing (Top Deck).

### Microcontroller Selection Matrix
We evaluated three low-cost embedded platforms:

| Platform | Core / Clock | RAM | Hardware Timers / PWM | Decision |
|---|---|---|---|---|
| **Raspberry Pi Pico (RP2040)** | Dual Cortex-M0+ @ 133MHz | 264 KB | 8 independent PWM slices (16 pins) | **SELECTED (Primary)** |
| **ESP32-WROOM-32** | Dual Xtensa LX6 @ 240MHz | 520 KB | 16 LEDC PWM channels | **SUPPORTED (Secondary)** |
| **ATmega328P (Uno/Nano)** | 8-bit AVR @ 16MHz | 2 KB | 6 PWM channels | **REJECTED** (Insufficient RAM for OLED framebuffer + telemetry stack) |

**Rationale:** The RP2040 provides dedicated hardware PWM slices per GPIO pin, generous 264KB SRAM (ideal for managing 128x64 OLED display buffers in MicroPython without GC pauses), dual 32-bit hardware timers, and 3.3V logic matching all chosen sensors directly.

---

## Milestone 02: Powertrain & Electrical Architecture
*Date: September 2026 | Logged: 8.0 Hours*

### Actuator Sizing & Kinematic Math
- **Motors:** 2x N20 Micro Metal Gearmotors (6V, 150 RPM rated, 1:100 reduction ratio).
- **Drive Wheels:** 43.0 mm outer diameter, high-friction silicone rubber tread.
- **Track Width ($L$):** 86.0 mm between wheel contact patches.

$$\text{Circumference} = \pi \times D = \pi \times 0.043\,\text{m} \approx 0.1351\,\text{m}$$
$$\text{Max Linear Speed} = 150\,\text{RPM} \times \frac{0.1351\,\text{m}}{60\,\text{s}} \approx 0.338\,\text{m/s} \; (33.8\,\text{cm/s})$$

Stall torque on the 1:100 gearbox is approximately $0.8\,\text{kg}\cdot\text{cm} = 0.078\,\text{N}\cdot\text{m}$. With a wheel radius of $21.5\,\text{mm}$, total forward tractive thrust across both wheels:
$$F_{\text{thrust}} = 2 \times \frac{0.078\,\text{N}\cdot\text{m}}{0.0215\,\text{m}} \approx 7.25\,\text{N}$$
Given our estimated all-up rover weight of $340\,\text{g} \; (3.33\,\text{N})$, the available thrust-to-weight ratio exceeds 2.1:1, easily conquering 25° incline ramps and thick carpet transitions without stall.

### Power & Driver Topology
- **Battery Pack:** 2S 18650 Li-ion cells (Nominal 7.4V, 2600 mAh, 19.2 Wh).
- **Buck Converter:** Ultra-compact MP1584EN synchronous step-down module delivering clean, regulated 5.0V @ 2A for the Raspberry Pi Pico VSYS, SG90 servo, and HC-SR04.
- **Motor Driver:** DRV8833 Dual MOSFET H-Bridge:
  - Ultra-low $R_{\text{DS(on)}} \approx 360\,\text{m}\Omega$ per H-bridge.
  - Continuous current: 1.2A per channel (N20 stall is ~700mA at 6V).
  - High-frequency ultrasonic PWM drive (20 kHz) selected in firmware to eradicate audible human motor whining.

---

## Milestone 03: Parametric Dual-Deck CAD Engineering
*Date: October 2026 | Logged: 10.5 Hours*

### CAD Stack & Design Rules
Authoring was performed 100% parametrically in OpenSCAD (`cad/chassis.scad`). All dimensions are expressed as scalar variables, allowing rapid retuning for different wheel sizes, battery cell formats (18650 vs LiPo pouch), or microcontroller footprints.

### Mechanical Features Engineered
1. **Bottom Deck:**
   - Dual N20 motor alignment saddles with 0.2mm press clearances and anti-twist sidewalls.
   - 2S 18650 battery cradle with slotted zip-tie tie-downs.
   - Wheel clearance cutouts matching 43mm tires with 2mm peripheral radial clearance.
   - Central $22 \times 14\,\text{mm}$ cable passthrough tunnel for motor leads and power bus.
   - Rear drop socket and M3 mounting points for a 15mm steel ball caster.
2. **Top Deck:**
   - Forward cantilever prow pocket with M2 screw tabs for SG90 servo flange mount.
   - Precision mounting hole pattern for Raspberry Pi Pico ($47.0 \times 11.4\,\text{mm}$).
   - 4-hole mounting pattern for SSD1306 0.96" OLED ($23.5 \times 23.5\,\text{mm}$).
   - BME280 sensor breakout bay with $6.0\,\text{mm}$ atmospheric sampling vent.
   - Honeycomb / hexagonal weight-relief matrix reducing top-deck print time by 32% and shifting mass downward.
3. **Turret & Brackets:**
   - `ultrasonic_bracket.scad`: Dual 16.3mm cylindrical retention sleeves for HC-SR04 transducer barrels with integrated underside servo horn receiver socket.
   - `n20_motor_bracket.scad`: Heavy-duty U-clamp brackets with M2 through-holes and recessed bolt heads.
   - `caster_mount.scad`: 10mm riser standoff with captive M3 hex nut traps for leveling the rover horizontal to the ground.

---

## Milestone 04: Embedded Firmware & PID Velocity Control
*Date: October 2026 | Logged: 7.5 Hours*

### Firmware Architecture (`src/main.py`)
MicroPython was selected for its high prototyping speed and transparent introspection. To avoid dependency bottlenecks, all core controllers, HAL mocks, and math routines were authored without external C extensions.

### Control Loops & Math
1. **Discrete PID Implementation:**
   - Equation:
     $$u(t) = K_p e(t) + K_i \int_0^t e(\tau)d\tau + K_d \frac{de(t)}{dt}$$
   - Integral Anti-Windup: Output accumulation clamped strictly to $\pm 40\%$ to prevent saturation overshoot when the rover encounters carpet friction or transient stalls.
   - Slew Rate Limiter: Motor commanded duty cycle limited to $180\%\,\text{s}^{-1}$ acceleration gradient, protecting N20 brass spur gears against stripping during instantaneous reverse commands.
2. **HC-SR04 Signal Conditioning:**
   - HC-SR04 raw pulse returns often suffer from multi-path reflections and stray echo loss. We implemented a 3-point median filter with microsecond timeout protection:
     $$d_{\text{cm}} = \frac{t_{\text{echo\_us}}}{58.2}$$
   - If an echo pulse fails to return within $30,000\,\mu\text{s}$, the driver safely returns $400.0\,\text{cm}$ (clear open corridor) rather than blocking the real-time event loop.

---

## Milestone 05: Obstacle Avoidance State Engine & Live Telemetry
*Date: October 2026 | Logged: 6.0 Hours*

### Finite State Machine (FSM) Flowchart

```
                 +-------------+
                 |  STATE_BOOT |
                 +-------------+
                        | (Self-test complete)
                        v
                 +---------------+
       +-------->|  STATE_CRUISE |<---------+
       |         +---------------+          |
       |                | (Dist < 38cm)     |
       |                v                   |
       |         +---------------+          |
       |         |   SLOW_APP    |          |
       |         +---------------+          |
       |                | (Dist < 20cm)     |
       |                v                   |
       |         +---------------+          |
       |         |   STATE_SCAN  |          |
       |         +---------------+          |
       |                | (Sweep -60..+60)  |
       |                v                   |
       |         +---------------+          |
       |         |   PATHFIND    |          |
       |         +---------------+          |
       |           /           \            |
       |   (Clear sector)   (All blocked)   |
       |         /               \          |
       |        v                 v         |
       |  +------------+   +-------------+  |
       |  | STATE_PIVOT|   | STATE_REVERS|--+
       |  +------------+   +-------------+
       +--------+
```

### Pathfinding Cost Function
During `STATE_SCAN`, the SG90 servo sweeps through five discrete headings: $[-60^\circ, -30^\circ, 0^\circ, +30^\circ, +60^\circ]$. The cost engine selects the traversal path using:
$$\text{Score}(\theta) = d_{\text{measured}}(\theta) \times \left(1.0 - \frac{|\theta|}{120^\circ} \times 0.25\right)$$
This gives an intentional directional bias toward continuing straight forward unless an obstacle is genuinely encroaching, preventing erratic zigzagging.

### Live Telemetry Format
Telemetry is transmitted over Serial UART at 2 Hz in high-speed JSON:
```json
{
  "time_ms": 14250,
  "state": "CRUISE",
  "dist_cm": 84.5,
  "best_hdg": 0,
  "temp_c": 23.42,
  "press_hpa": 1013.2,
  "alt_m": 45.2,
  "motor_l": 65.0,
  "motor_r": 65.0
}
```

Simultaneously, the SSD1306 OLED HUD renders a live radar arc with 5 clearance bars, current flight mode, ambient temperature, atmospheric pressure, and motor duty cycles.

---

## Bill of Materials (BOM) & Sourcing

| Item | Component Description | Qty | Est. Unit Cost | Purpose |
|:---:|---|:---:|:---:|---|
| 1 | Raspberry Pi Pico (RP2040) | 1 | $4.00 | Master Flight Controller |
| 2 | N20 Micro Metal Gearmotor (6V, 150 RPM) | 2 | $3.50 | Differential Powertrain |
| 3 | 43mm D-shaft Rubber Wheels | 2 | $1.50 | Traction Drive Wheels |
| 4 | DRV8833 Dual H-Bridge Driver | 1 | $1.80 | Motor PWM Amplification |
| 5 | SG90 9g Micro Servo Motor | 1 | $2.20 | Panning Sensor Turret |
| 6 | HC-SR04 / RCWL-1601 Ultrasonic Module | 1 | $1.50 | Look-Ahead Obstacle Rangefinder |
| 7 | BME280 I2C Barometric & Temp Sensor | 1 | $4.50 | Atmospheric Telemetry |
| 8 | SSD1306 0.96" 128x64 OLED Display (I2C) | 1 | $3.00 | Heads-Up Display (HUD) |
| 9 | 15mm Steel Ball Caster | 1 | $1.20 | Low-Friction Rear Support |
| 10 | 18650 Li-ion Cells (2S Pack) + Holder | 1 | $8.00 | Main Energy Storage |
| 11 | MP1584EN DC-DC Buck Converter (5V 2A) | 1 | $1.20 | Regulated Logic Power |
| 12 | M3 x 28mm Brass Hex Standoffs + Screws | 4 | $0.40 | Chassis Deck Structural Core |
| 13 | M2 x 10mm / M2 x 6mm Machine Screws | 12 | $0.15 | Motor & Sensor Mountings |
| 14 | 3D Printed PETG / PLA Chassis Components | 1 set | ~$3.00 | Structural Frames & Mounts |
| -- | **TOTAL ESTIMATED BUILD COST** | -- | **~$39.50** | **Complete Autonomous Rover** |

---

## Conclusion & Next Horizons
Phase 1 milestones have established a fully verified physical CAD system, compiled 3D mesh assets, and a tested MicroPython firmware stack. Future milestones will explore 9-DOF IMU Kalman filter heading integration, SLAM corridor mapping, and Long-Range (LoRa) telemetry relay downlinks.
