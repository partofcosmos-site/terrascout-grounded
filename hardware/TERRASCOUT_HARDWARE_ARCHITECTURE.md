# TerraScout: Complete Hardware & Electronics Architecture
**Hack Club Grounded — Tier 1 ($150 Grant Budget) Autonomous Planetary Scout Rover**

---

## 1. Executive Summary & System Overview

**TerraScout** is a high-reliability, low-cost autonomous planetary exploration rover engineered for the **Hack Club Grounded Tier 1 Grant Program ($150 budget limit)**. Designed to operate both autonomously and via telemetry-linked teleoperation, TerraScout combines real-time atmospheric sensing, forward radar sweeping, surface boundary/line navigation, and dual closed-loop micro-traction motors.

### System Specifications at a Glance:
* **Core Compute:** Espressif ESP32-S3 Dual-Core Xtensa LX7 @ 240 MHz (with 8MB Flash / 8MB PSRAM, Wi-Fi 4 802.11 b/g/n, BLE 5.0) — *Alternative: Raspberry Pi Pico RP2040 Dual ARM Cortex-M0+ @ 133 MHz*.
* **Motor Drive:** Dual N20 Micro Metal Gearmotors (6V, 300 RPM, all-metal gear train) paired with Texas Instruments DRV8833 Dual H-Bridge MOSFET driver (up to 1.5A per channel, ultra-low $R_{\text{DS(on)}}$, zero heatsink required).
* **Sweeping Obstacle Radar:** HC-SR04P 3.3V-5V wide-voltage ultrasonic sonar mounted atop a TowerPro SG90 9g micro-servo delivering 180° pan-sweep obstacle depth mapping.
* **Surface Boundary & Line Detection:** 3-Channel TCRT5000 infrared reflective sensor array with onboard LM393 comparators for edge detection, drop-off avoidance, and line tracking.
* **Atmospheric & Telemetry Package:** Bosch Sensortec BME280 digital environmental sensor (Temperature, Barometric Pressure, Relative Humidity) via I2C for elevation tracking and microclimate monitoring.
* **Onboard HUD:** 0.96-inch monochrome SSD1306 128×64 OLED display providing live battery gauge, heading, ping distance, and system states.
* **Power Subsystem:** 2S 7.4V nominal (8.4V peak) 18650 Li-ion battery pack with integrated 2S 10A BMS protection, USB-C 2S balance charging (TP5100/IP2326), MP1584EN 3A high-frequency buck regulator stepping down to 5.0V, and high-impedance resistor divider for battery telemetry.
* **Total Project BOM Cost:** **$64.78 USD (₹5,571 INR)** — leaving a massive **$85.22 buffer (56.8% under budget)** beneath the $150 Hack Club Grounded Tier 1 limit.

---

## 2. Microcontroller Selection: ESP32-S3 vs. RP2040

### 2.1 The Flagship Choice: ESP32-S3 (ESP32-S3-DevKitC-1)
* **Processor Architecture:** Dual-core 32-bit Xtensa LX7 running at 240 MHz, delivering 600 DMIPS.
* **Memory Architecture:** 512 KB internal SRAM, 8 MB external Flash, 8 MB Octal PSRAM.
* **Wireless Telemetry & Control:** On-chip 2.4 GHz Wi-Fi 4 and Bluetooth 5 (LE) enable TerraScout to broadcast a local Web dashboard, stream WebSockets sensor telemetry (live radar sweep graph, BME280 metrics, battery percentage) to any phone or laptop browser, and receive joystick control commands without extra hardware.
* **Peripherals:** 45 programmable GPIOs, 14-channel 12-bit SAR ADC, 8 independent LEDC PWM channels (motor and servo control), 2 hardware I2C buses.
* **Development Ecosystem:** Fully supported in Arduino IDE, ESP-IDF, and MicroPython/CircuitPython.

### 2.2 The Low-Cost Minimalist Choice: Raspberry Pi Pico (RP2040)
* **Processor Architecture:** Dual-core ARM Cortex-M0+ running at 133 MHz.
* **Memory Architecture:** 264 KB on-chip SRAM, 2 MB external QSPI Flash.
* **Unique Strength:** Programmable I/O (PIO) state machines can drive the ultrasonic echo timing and servo PWM with cycle-accurate precision with zero CPU overhead.
* **Limitation:** Lacks native Wi-Fi/Bluetooth (unless using Pico W, which uses CYW43439).

*Decision:* The reference architecture is built around the **ESP32-S3-DevKitC-1** to leverage high-speed telemetry web-serving, while complete, pin-for-pin drop-in compatibility is mapped for the **Raspberry Pi Pico RP2040**.

---

## 3. Power Architecture & Power Tree

```
  [2x 18650 Li-ion Cells (7.4V - 8.4V, 2600mAh)]
                        |
            [2S 8.4V 10A BMS Protection]
                        |
            [SPST Rocker Power Switch]
                        |
       +----------------+----------------+
       |                                 |
 [Raw VBAT: 7.4V-8.4V]          [Battery Sense Divider]
       |                         (100k + 47k + 100nF)
       |                                 |
       |                        ESP32-S3 GPIO14 (ADC)
       |
       +---> [DRV8833 Motor Driver VM Pin]
       |     (Decoupled by 470uF 16V Low-ESR + 100nF Ceramic)
       |     *Powers 2x N20 6V Gearmotors via PWM duty scaling
       |
       +---> [MP1584EN High-Freq Buck Converter (1.5MHz, 3A)]
                        |
             [Regulated +5.00V Rail]
                        |
       +----------------+----------------+
       |                                 |
 [SG90 Pan Servo]                [ESP32-S3 5V/VIN Pin]
  (VCC: 5.0V)                            |
                                [Onboard Low-Noise LDO]
                                         |
                              [Regulated +3.30V Rail]
                                         |
                 +-----------------------+-----------------------+
                 |                       |                       |
          [ESP32-S3 Core]        [HC-SR04P Sonar]        [BME280 Sensor]
                 |                       |                       |
        [SSD1306 OLED HUD]       [TCRT5000 Array]        [Status Neopixel]
```

### 3.1 Power Rail Analysis & Budgeting
1. **$V_{\text{BAT}}$ Raw Rail (7.0V min to 8.4V max):**
   - Directly feeds the Texas Instruments DRV8833 `VM` pins.
   - Operating N20 6V motors from an 8.4V source via PWM limit (clamped in software to $\le 80\%$ duty cycle, i.e., $8.4\text{ V} \times 0.75 \approx 6.3\text{ V}$) ensures full torque response while preventing motor coil over-saturation.
   - High transient motor currents are isolated by a $470\,\mu\text{F}$ 16V electrolytic bulk capacitor placed directly across the DRV8833 supply pins.
2. **$+5.0\text{V}$ Regulated Rail:**
   - Generated by the ultra-compact MP1584EN DC-DC buck converter (1.5 MHz switching frequency, 3A max capability, >92% efficiency).
   - Feeds the TowerPro SG90 servo motor (which stalls at ~500mA @ 5V during rapid sweeps) and powers the ESP32-S3 DevKit 5V input.
   - Prevents servo inductive spikes from causing MCU brownouts through isolated buck filtering.
3. **$+3.3\text{V}$ Logic & Sensor Rail:**
   - Provided by the ESP32-S3 DevKit's onboard high-current low-dropout linear regulator (AP2112K / SGM2211, rated 600mA).
   - Supplies the ESP32-S3 SoC, HC-SR04P ultrasonic module, 3-channel TCRT5000 comparator logic, BME280 sensor, and SSD1306 OLED display.
   - Total 3.3V quiescent draw: ESP32-S3 (120mA peak with Wi-Fi) + OLED (20mA) + BME280 (<1mA) + HC-SR04P (3mA) + TCRT5000 (15mA) $\approx 160\,\text{mA}$, well within the 600mA LDO limit.

### 3.2 Battery Monitoring Voltage Divider
To prevent Li-ion over-discharge and provide live telemetry:
$$V_{\text{ADC}} = V_{\text{BAT}} \times \frac{R_2}{R_1 + R_2}$$
* Selected values: $R_1 = 100\text{ k}\Omega$ (1%), $R_2 = 47\text{ k}\Omega$ (1%).
* Division ratio: $k = \frac{47}{147} \approx 0.31972$.
* When battery is fully charged ($8.40\text{ V}$): $V_{\text{ADC}} = 8.40 \times 0.31972 = 2.686\text{ V}$.
* When battery reaches nominal discharge ($6.60\text{ V}$ / 3.3V per cell): $V_{\text{ADC}} = 2.110\text{ V}$.
* Safe boundary: $2.686\text{ V}$ is comfortably below the ESP32-S3 ADC full-scale threshold ($3.10\text{ V}$ at 11 dB attenuation).
* Decoupling: A $100\,\text{nF}$ ceramic capacitor in parallel with $R_2$ suppresses switching noise and stabilizes SAR ADC conversions.

---

## 4. Motor Drive & Actuation Subsystem

### 4.1 N20 Micro Metal Gearmotors
* **Operating Voltage:** 3.0V – 6.0V DC.
* **No-load Speed:** 300 RPM @ 6V.
* **Gearbox:** All-metal spur gearbox with 1:50 gear reduction.
* **Torque:** Rated $0.35\,\text{kg}\cdot\text{cm}$, Stall $0.98\,\text{kg}\cdot\text{cm}$.
* **Current Draw:** No-load ~60mA, Full-load ~180mA, Stall ~670mA.
* **Mechanical Interface:** 3mm D-shaft, mounted with stamped aluminum N20 brackets to the chassis, fitted with 43mm rubber high-traction tires.

### 4.2 DRV8833 Dual H-Bridge Motor Driver
* **Input Voltage:** 2.7V to 10.8V.
* **Current Capability:** 1.2A RMS, 2.0A peak per H-bridge channel.
* **$R_{\text{DS(on)}}$:** ~300 m$\Omega$ per FET — produces negligible heat compared to legacy L298N drivers (which drop 2V-3V internally in Darlington transistors).
* **Control Truth Table (Fast Decay / PWM):**
  * Forward: `IN1 = PWM`, `IN2 = LOW`
  * Reverse: `IN1 = LOW`, `IN2 = PWM`
  * Brake: `IN1 = HIGH`, `IN2 = HIGH`
  * Coast (Freewheel): `IN1 = LOW`, `IN2 = LOW`
* **Sleep Pin (`nSLEEP`):** Tied to ESP32-S3 GPIO15 (active HIGH). Driven LOW during low-power standby.

---

## 5. Sensor Suite & Sweep Radar Architecture

### 5.1 Sweeping Obstacle Detection: HC-SR04P on SG90 Servo
* **Ultrasonic Module:** HC-SR04P wide-voltage model (compatible with 3.0V to 5.5V).
  * Direct 3.3V GPIO compatibility allows `TRIG` and `ECHO` to connect directly to ESP32-S3 GPIO6 and GPIO7 without external resistor dividers or level-shifting transistors.
  * Range: 2 cm to 400 cm with 3mm precision.
  * Sound pulse: 8 pulses of 40 kHz ultrasonic burst triggered by a $10\,\mu\text{s}$ HIGH pulse on `TRIG`.
* **Pan Servo:** TowerPro SG90 9g Micro Servo.
  * Sweep range: 0° (Far Left) to 180° (Far Right), centering at 90° (Direct Forward).
  * Control signal: 50 Hz PWM (20ms period), pulse width $1.0\,\text{ms}$ (0°) to $2.0\,\text{ms}$ (180°).
  * Mounting: Custom 3D-printed swivel mount affixing the HC-SR04P transducer eyes directly over the servo horn.
  * Sweeping Algorithm: Continuous scanning across 5 discrete sectors (30°, 60°, 90°, 120°, 150°) to construct a forward polar depth map for real-time path planning.

### 5.2 3-Channel TCRT5000 Infrared Reflective Sensor Array
* **Principle:** Infrared emitter diode + phototransistor detecting ground surface reflectance.
* **Comparator Circuit:** Onboard LM393 dual comparator with multiturn trimpot for threshold tuning.
* **Digital Outputs (`OUT1`, `OUT2`, `OUT3`):**
  * Black surface / Table edge drop-off: High impedance / Logic HIGH.
  * White surface / Reflective terrain: Collector pulled down / Logic LOW.
* **Role in Rover Architecture:**
  * Primary: High-speed line following along white/black course lines.
  * Secondary: Cliff detection / table-edge fail-safe cutoff.

### 5.3 Atmospheric Telemetry: Bosch BME280 Sensor
* **Bus:** I2C (Address `0x76` or `0x77`).
* **Sensing Parameters:**
  * **Barometric Pressure:** 300 – 1100 hPa (resolution 0.18 Pa, accuracy ±1 hPa). Enables hypsometric altitude calculation:
    $$h = 44330 \times \left(1 - \left(\frac{P}{P_0}\right)^{\frac{1}{5.255}}\right)$$
  * **Temperature:** -40°C to +85°C (resolution 0.01°C, accuracy ±0.5°C).
  * **Relative Humidity:** 0% – 100% RH (response time 1s, accuracy ±3% RH).
* **Telemetry Application:** Enables TerraScout to record ambient atmospheric profiles as it navigates varying altitudes and terrain.

### 5.4 Onboard Telemetry HUD: 0.96" SSD1306 OLED
* **Resolution:** 128×64 pixels monochrome.
* **Interface:** I2C (Address `0x3C`) sharing `SDA` (GPIO8) and `SCL` (GPIO9) with BME280.
* **Display Layout:**
  * Line 1: `[BATT: 8.2V 94%] [MD:AUTO]`
  * Line 2: `[SWEEP: 90°] [PING: 42cm]`
  * Line 3: `[T:24.6°C] [P:1013.2hPa]`
  * Line 4: `[LINE: L:0 C:1 R:0] [WIFI:OK]`

---

## 6. Complete System Schematic Netlist & Connections

### 6.1 Power Subsystem Netlist
| Signal Name | Source | Destination | Specifications |
|---|---|---|---|
| `BAT+` | 18650 Battery (+) | BMS `B+` | 7.4V - 8.4V raw Li-ion |
| `BAT-` | 18650 Battery (-) | BMS `B-` | Cell return |
| `BAT_MID` | Battery Inter-cell tap | BMS `BM` | 3.7V - 4.2V balancing tap |
| `P+` (Switched) | BMS `P+` via Rocker SW | MP1584 `IN+`, DRV8833 `VM`, Divider $R_1$ | Main 8.4V switched power rail |
| `P-` / `GND` | BMS `P-` | Common Star Ground | System reference ground |
| `+5V_BUCK` | MP1584 `OUT+` | SG90 `VCC`, ESP32-S3 `5V` (VBUS/VIN) | Clean 5.00V, 3A peak rail |
| `+3.3V` | ESP32-S3 `3V3` Pin | BME280 `VCC`, OLED `VCC`, HC-SR04P `VCC`, TCRT5000 `VCC` | Clean 3.30V sensor rail |
| `BATT_SENSE` | Divider $R_1$/$R_2$ junction | ESP32-S3 `GPIO14` (ADC1_CH13) | Analog 0 - 2.7V proportional voltage |

### 6.2 Control & Signal Netlist
| Signal Name | ESP32-S3 Pin | Peripheral Pin | Function |
|---|---|---|---|
| `MOTOR_L_IN1` | GPIO1 | DRV8833 `IN1` | Motor Left Direction A (LEDC PWM) |
| `MOTOR_L_IN2` | GPIO2 | DRV8833 `IN2` | Motor Left Direction B (LEDC PWM) |
| `MOTOR_R_IN1` | GPIO4 | DRV8833 `IN3` | Motor Right Direction A (LEDC PWM) |
| `MOTOR_R_IN2` | GPIO5 | DRV8833 `IN4` | Motor Right Direction B (LEDC PWM) |
| `MOTOR_NSLEEP`| GPIO15 | DRV8833 `nSLEEP` | Motor Driver Enable (Active HIGH) |
| `US_TRIG` | GPIO6 | HC-SR04P `TRIG` | Sonar Trigger ($10\,\mu\text{s}$ pulse) |
| `US_ECHO` | GPIO7 | HC-SR04P `ECHO` | Sonar Echo Input (3.3V logic) |
| `I2C_SDA` | GPIO8 | SSD1306 `SDA`, BME280 `SDA` | Shared I2C Data bus |
| `I2C_SCL` | GPIO9 | SSD1306 `SCL`, BME280 `SCL` | Shared I2C Clock bus |
| `SERVO_PWM` | GPIO10 | SG90 `PWM` (Orange wire) | Pan Radar Sweep PWM (50 Hz) |
| `LINE_L` | GPIO11 | TCRT5000 Channel 1 `DO` | Left Line Sensor Digital Input |
| `LINE_C` | GPIO12 | TCRT5000 Channel 2 `DO` | Center Line Sensor Digital Input |
| `LINE_R` | GPIO13 | TCRT5000 Channel 3 `DO` | Right Line Sensor Digital Input |
| `BATT_ADC` | GPIO14 | Resistor Divider Tap | Battery Telemetry Voltage ADC |
| `RGB_LED` | GPIO38 / GPIO48 | Onboard WS2812B NeoPixel | Status Indicator RGB LED |

---

## 7. Complete RP2040 (Raspberry Pi Pico) Alternative Mapping

For builders choosing the Raspberry Pi Pico / Pico W, the pinout maps directly as follows:
* **`GP2`:** DRV8833 `IN1` (Motor Left PWM A)
* **`GP3`:** DRV8833 `IN2` (Motor Left PWM B)
* **`GP4`:** DRV8833 `IN3` (Motor Right PWM A)
* **`GP5`:** DRV8833 `IN4` (Motor Right PWM B)
* **`GP14`:** DRV8833 `nSLEEP` (Motor Sleep/Enable)
* **`GP6`:** HC-SR04P `TRIG`
* **`GP7`:** HC-SR04P `ECHO`
* **`GP8`:** SG90 Servo PWM
* **`GP9`:** TCRT5000 Left Line Sensor `DO`
* **`GP10`:** TCRT5000 Center Line Sensor `DO`
* **`GP11`:** TCRT5000 Right Line Sensor `DO`
* **`GP0 (I2C0 SDA)`:** SSD1306 & BME280 `SDA`
* **`GP1 (I2C0 SCL)`:** SSD1306 & BME280 `SCL`
* **`GP26 (ADC0)`:** Battery Voltage Divider Tap
* **`VSYS / VBUS`:** Buck converter +5.0V input (diode isolated)

---

## 8. Mechanical Integration & Chassis Packaging

1. **Chassis Baseplate:** Dual-layer acrylic / FR4 / 3D-printed PETG chassis (dimensions: 140 mm × 100 mm × 3 mm).
2. **Drive Configuration:** Differential drive with dual rear N20 motors and front nylon/stainless-steel omnidirectional ball caster wheel (15 mm).
3. **Weight Distribution:**
   - The heavy 2S 18650 battery pack (approx. 95 g) is seated low along the centerline between the two drive wheels to maximize rear wheel traction.
   - The electronics carrier PCB sits on 10 mm brass standoffs directly above the battery holder.
   - The SG90 servo and HC-SR04P sonar mount is positioned forward over the front caster, granting unobstructed 180° field-of-view scanning.
   - The 3-channel TCRT5000 line sensor array is mounted underneath the front chassis lip, positioned 5 mm to 8 mm above the ground plane for optimal optical reflection.
4. **Thermal Dissipation:**
   - DRV8833 MOSFET driver has an exposed bottom copper pad with stitching vias to the ground plane on the carrier PCB.
   - MP1584EN buck converter inductor and IC are exposed to ambient airflow.
