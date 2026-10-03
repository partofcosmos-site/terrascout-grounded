# 🚜 TerraScout Grounded: Autonomous Telemetry Rover

> **An open-source, dual-deck differential micro-rover built for autonomous exploration, environmental telemetry gathering, and obstacle avoidance.**

[![Platform](https://img.shields.io/badge/Platform-MicroPython%20%7C%20CircuitPython-blue.svg)](https://micropython.org)
[![MCU](https://img.shields.io/badge/Brain-Raspberry%20Pi%20Pico%20(RP2040)-green.svg)](https://www.raspberrypi.com/products/raspberry-pi-pico/)
[![CAD](https://img.shields.io/badge/CAD-OpenSCAD%20Parametric-orange.svg)](https://openscad.org)
[![License](https://img.shields.io/badge/License-CERN--OHL--P%20%2F%20MIT-brightgreen.svg)](LICENSE)

---

## 🧭 Why We Built TerraScout

There's something magical about placing a small rover onto the floor, flipping the master power switch, and watching it spring to life: eyes panning left and right, ultrasonic pings reflecting off table legs, motors humming smoothly at 20 kHz without the irritating high-pitch whine of cheap toys, and a glowing 128x64 OLED screen reporting real-time telemetry like a tiny Mars rover on a kitchen-floor expedition.

**TerraScout Grounded** was designed from scratch as a grounded telemetry rover that anyone with a basic desktop 3D printer, a soldering iron, and a Raspberry Pi Pico can build over a weekend for under $40 in off-the-shelf parts. 

Everything here is engineered to be **reproducible, parametric, and hackable**:
- **Parametric OpenSCAD Chassis:** No static meshes you can't adapt. Tweak wheel diameters, battery bays, or standoff heights with simple scalar variables.
- **MicroPython Firmware:** Clean, readable, and battle-tested embedded Python with a discrete-time PID velocity controller, anti-windup protection, and slew rate acceleration limiting to protect delicate brass gear teeth.
- **Sweeping Radar Head:** An SG90 micro-servo pans the HC-SR04 ultrasonic rangefinder from $-60^\circ$ to $+60^\circ$, executing multi-point sector clearance analysis before choosing traversal paths.
- **Environmental Telemetry HUD:** Live temperature, barometric pressure, estimated altitude, and radar clearance bars rendered directly to a 0.96" SSD1306 OLED display, while broadcasting streaming JSON telemetry over serial.

---

## ⚙️ System Specifications

```
                     +---------------------------------------+
                     |         TERRASCOUT ARCHITECTURE       |
                     +---------------------------------------+
                                         |
     +-----------------------------------+-----------------------------------+
     |                                                                       |
[TOP DECK: BRAIN & SENSORS]                             [BOTTOM DECK: DRIVE & POWER]
* Raspberry Pi Pico (RP2040) @ 133MHz                   * 2x N20 Micro Metal Gearmotors (6V 150RPM)
* SG90 Panning Micro-Servo (-60°..+60°)                 * 43mm Silicone Rubber Traction Wheels
* HC-SR04 Ultrasonic "Eye" Transducers                  * 15mm Steel Omnidirectional Ball Caster
* BME280 I2C Barometric / Temp Sensor                   * DRV8833 Dual H-Bridge Motor Driver
* SSD1306 0.96" 128x64 I2C OLED HUD                     * 2S 18650 Li-ion Battery Sled (7.4V 2600mAh)
* M3 Hex Brass Standoff Core (28mm)                     * MP1584EN 5V 2A Regulated Buck Converter
```

| Parameter | Specification | Details |
|---|---|---|
| **Chassis Dimensions** | $136\,\text{mm} \times 94\,\text{mm} \times 65\,\text{mm}$ | Fits within standard desk/bookshelf test courses |
| **All-Up Weight (AUW)** | $\approx 340\,\text{g}$ | Low CoG ($\le 18\,\text{mm}$ from ground level) |
| **Drive Configuration** | Differential 2WD + Trailing Ball Caster | Zero-radius counter-rotation turning capability |
| **Cruising Speed** | $22 - 34\,\text{cm/s}$ | PWM controlled via dual PID velocity loops |
| **Battery Life** | $4.5 - 6.0\,\text{hours}$ | Continuous autonomous navigation on 2S 18650 |
| **Scanning Resolution** | 5 discrete sectors ($-60^\circ, -30^\circ, 0^\circ, +30^\circ, +60^\circ$) | $180\,\text{ms}$ settle time per sector |
| **Operating Voltage** | 7.4V nominal (Battery) / 5.0V regulated (Logic) | Regulated via high-efficiency MP1584EN buck converter |

---

## 🖨️ 3D Printing & Mechanical Assembly

The complete chassis is parametrically modeled in OpenSCAD (`cad/chassis.scad`). You don't need proprietary CAD tools; open the `.scad` file in OpenSCAD and export individual plates or compile them headlessly via our build script.

### Printable Components Overview

| Component | File | Recommended Print Settings |
|---|---|---|
| **Bottom Deck Plate** | `cad/bottom_deck.stl` | PETG / PLA+, 0.2mm layer, 30% gyroid infill, 3 perimeters |
| **Top Deck Plate** | `cad/top_deck.stl` | PETG / PLA+, 0.2mm layer, 25% infill, 3 perimeters |
| **N20 Motor Brackets (x2)** | `cad/motor_bracket.stl` | PETG, 0.16mm layer, 50% infill for rigidity |
| **Ultrasonic Turret Eye Bracket** | `cad/ultrasonic_bracket.stl` | PLA / PETG, 0.2mm layer, 20% infill, press-fit transducer collars |
| **Ball Caster Riser Mount** | `cad/caster_mount.stl` | PETG / PLA+, 0.2mm layer, 40% infill, captive M3 nut traps |
| **All-in-One Print Bed** | `cad/print_bed_plate.stl` | Arranged flat for single-run 200x200mm print beds! |

### Mechanical Build Instructions

1. **Bottom Deck Assembly:**
   - Drop the two N20 gearmotors into their molded alignment saddles on the bottom plate.
   - Secure each motor using the `motor_bracket.stl` clamps with four M2 screws.
   - Press the 43mm rubber wheels onto the motor D-shafts.
   - Mount the 15mm steel ball caster to the rear drop socket using two M3 screws and the `caster_mount.stl` riser block.
   - Strap the 2S 18650 battery holder to the center of the bottom deck using zip ties through the integrated retention slots.
   - Install four $28\,\text{mm}$ M3 female brass hex standoffs at the corners.

2. **Top Deck Assembly:**
   - Press the SG90 micro-servo into the forward prow pocket and fasten with two M2 self-tapping screws.
   - Press the HC-SR04 ultrasonic sensor into the dual 16.3mm eye sleeves of `ultrasonic_bracket.stl`. Screw the small single-arm servo horn into the bracket's underside boss and press it onto the SG90 output spline.
   - Mount the Raspberry Pi Pico, SSD1306 OLED display, and BME280 breakout using M2 screws into the pre-spaced deck bosses.
   - Route motor leads and power cables through the deck passthrough slots.
   - Fasten the top deck onto the four M3 standoffs.

---

## ⚡ Electronics & Wiring Pinout

All logic operates at **3.3V** (Raspberry Pi Pico native). The high-current motor stage and SG90 servo are isolated and powered through the 5V buck converter.

| Subsystem | Component Pin | Pico GPIO Pin | Notes |
|---|---|:---:|---|
| **Left Motor (DRV8833)** | IN1 (Forward) | **GP18** | PWM Channel 1A (20 kHz) |
| | IN2 (Reverse) | **GP19** | PWM Channel 1B (20 kHz) |
| **Right Motor (DRV8833)** | IN1 (Forward) | **GP20** | PWM Channel 2A (20 kHz) |
| | IN2 (Reverse) | **GP21** | PWM Channel 2B (20 kHz) |
| **Panning Turret** | SG90 Signal (Orange) | **GP15** | PWM Channel 7B (50 Hz, 600-2400 µs) |
| **Ultrasonic Sensor** | HC-SR04 Trigger | **GP16** | 10 µs trigger pulse |
| | HC-SR04 Echo | **GP17** | Echo return pulse timing |
| **I2C Bus (OLED + BME280)** | I2C0 SDA | **GP4** | 400 kHz Fast I2C bus |
| | I2C0 SCL | **GP5** | 400 kHz Fast I2C bus |
| **Power Delivery** | VSYS | 5.0V Output | Regulated from MP1584EN buck converter |
| | GND | Common GND | Star ground connection |

---

## 🧠 Firmware Architecture (`src/main.py`)

TerraScout runs a cooperative multi-rate firmware loop without blocking `time.sleep()` calls, ensuring sensor readings and PID loops execute deterministically.

```
       [40 Hz Loop]               [5 Hz Loop]                [2 Hz Loop]
+-------------------------+  +--------------------+  +-------------------------+
| Differential Drive PID  |  | SSD1306 OLED HUD   |  | JSON Serial Telemetry   |
| Obstacle Avoidance FSM  |  | - Radar Arc Bars   |  | - {"dist_cm": 84.5,     |
| Slew Rate Acceleration  |  | - State Indicator  |  |    "temp_c": 23.4, ...} |
+-------------------------+  +--------------------+  +-------------------------+
```

### Finite State Machine (FSM) States

1. **`STATE_BOOT`:** Initial 1.2-second hardware self-test, centering the panning turret and zeroing motor PWM registers.
2. **`STATE_CRUISE`:** Drives forward smoothly ($65\%$ cruising speed). Continuous 40Hz rangefinder pings monitor forward clearance.
3. **`STATE_SLOW_APPROACH`:** Triggered when an obstacle is detected within $38\,\text{cm}$. Decelerates to $30\%$ to minimize vehicle momentum.
4. **`STATE_PANORAMIC_SCAN`:** When an obstacle breaches $20\,\text{cm}$, the rover brakes to a dead stop. The SG90 servo sweeps across $[-60^\circ, -30^\circ, 0^\circ, +30^\circ, +60^\circ]$, collecting median-filtered distance readings.
5. **`STATE_PATHFINDING`:** Evaluates sector clearance using a directional cost function:
   $$\text{Score}(\theta) = d_{\text{measured}}(\theta) \times \left(1.0 - \frac{|\theta|}{120^\circ} \times 0.25\right)$$
   This encourages the rover to favor straight or gentle veerings over drastic direction flips unless necessary.
6. **`STATE_PIVOT_AVOID`:** Executes a zero-radius differential pivot towards the selected heading with calibrated rotational timing ($\sim 14\,\text{ms}/\text{degree}$).
7. **`STATE_EMERGENCY_REVERSE`:** If trapped in a box canyon or cul-de-sac ($d < 14\,\text{cm}$ in all sectors), the rover backs up straight for $1.1\,\text{seconds}$ before rescanning.

### Desktop Simulation & Self-Test Mode

You can verify the firmware directly on your workstation without flashing a microcontroller! The built-in Hardware Abstraction Layer (HAL) automatically detects desktop Python:

```bash
# Run the automated diagnostic test suite
python src/main.py --diag
```

---

## 📊 Live OLED HUD & Telemetry Streaming

### SSD1306 OLED Screen Layout
```
+--------------------------------+
| TSCOUT: CRUISE          120cm  |  <- Mode & Forward Distance
|--------------------------------|
|        |||    |||||     ||     |  <- Real-time 5-Sector Radar Bars
|       [-60]   [ 0 ]    [+60]   |     (Left, Center, Right)
|--------------------------------|
| 23.4C  1013hPa      L55 R55    |  <- Temp, Pressure, Motor Power
+--------------------------------+
```

### Streaming JSON Telemetry
Every 500ms, the rover streams telemetry over the USB serial interface:
```json
{
  "time_ms": 18450,
  "state": "CRUISE",
  "dist_cm": 114.2,
  "best_hdg": 0,
  "temp_c": 23.42,
  "press_hpa": 1013.2,
  "alt_m": 45.2,
  "motor_l": 65.0,
  "motor_r": 65.0
}
```

---

## 🚀 Quickstart Guide

### 1. Compile the 3D Printable Models
OpenSCAD can compile all parts in one automated pass:
```bash
python cad/compile_models.py
```
This generates all `.stl` files and high-resolution `.png` renders inside the `cad/` directory.

### 2. Flash MicroPython to the Pico
1. Hold down the **BOOTSEL** button on your Raspberry Pi Pico and plug it into your computer via USB.
2. Drag and drop the latest MicroPython `.uf2` firmware onto the mounted `RPI-RP2` drive.
3. Copy `src/main.py` onto the Pico's root flash memory using `mpremote`, `ampy`, or Thonny IDE:
   ```bash
   # Using mpremote (optional)
   mpremote cp src/main.py :main.py
   ```
4. Reset the Pico. TerraScout will initialize, display the HUD banner, and begin autonomous navigation!

---

## 📁 Repository Structure

```
terrascout-grounded/
├── .gitignore               # Git exclusions for CAD caches and bytecode
├── README.md                # Comprehensive documentation and build guide
├── JOURNAL.md               # Detailed engineering log, math & BOM
├── src/
│   └── main.py              # MicroPython autonomous rover firmware
└── cad/
    ├── chassis.scad         # Parametric OpenSCAD dual-deck master model
    ├── compile_models.py    # Headless CAD compiler and PNG renderer
    ├── bottom_deck.stl      # 3D printable bottom plate (N20 + battery)
    ├── top_deck.stl         # 3D printable top plate (MCU + HUD + sensors)
    ├── motor_bracket.stl    # 3D printable N20 gearmotor clamp
    ├── ultrasonic_bracket.stl # 3D printable HC-SR04 servo turret
    ├── caster_mount.stl     # 3D printable 15mm ball caster riser
    ├── print_bed_plate.stl  # Full 200x200mm single-run print bed layout
    ├── assembly.png         # 3D perspective assembly render
    └── exploded.png         # Exploded architecture render
```

---

## 📜 License & Credits

- **Hardware & Mechanics:** [CERN Open Hardware Licence Version 2 - Strongly Reciprocal (CERN-OHL-S)](https://ohwr.org/cernohl)
- **Firmware & Software:** [MIT License](https://opensource.org/licenses/MIT)

*Engineered with precision for autonomous explorers everywhere.* 🚀
