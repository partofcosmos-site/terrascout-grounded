# TerraScout: Complete Pinout Matrix & Electrical Specifications
**Hack Club Grounded — Tier 1 Project**

This document defines the complete microcontroller pin assignment, electrical interface types, signal protocols, and hardware peripherals for both the primary **ESP32-S3** architecture and the **Raspberry Pi Pico (RP2040)** alternative.

---

## 1. Primary Architecture: ESP32-S3-DevKitC-1 Pinout Matrix

| Pin # | Microcontroller Pin | Physical Function / Net Name | Signal Type | Logic Level | Connected Peripheral & Pin | Internal / External Configuration | Description & Operating Notes |
|:---:|:---:|:---|:---:|:---:|:---|:---:|:---|
| 1 | **3V3** | `+3.3V` | Power Output | 3.3V DC | BME280 VCC, SSD1306 VCC, HC-SR04P VCC, TCRT5000 VCC | Regulated by onboard AP2112K LDO | Powers all digital logic & I2C sensors (max 600mA). |
| 2 | **GND** | `GND` | Ground Reference | 0V | System Common Star Ground | System Ground Plane | Zero-potential reference plane for all analog & digital circuits. |
| 3 | **GPIO1** | `MOTOR_L_IN1` | Digital Output | 3.3V (5V tol) | DRV8833 `IN1` (Left Motor Phase A) | LEDC PWM Channel 0 (20 kHz, 8-bit) | Controls Left Motor forward drive & speed. |
| 4 | **GPIO2** | `MOTOR_L_IN2` | Digital Output | 3.3V (5V tol) | DRV8833 `IN2` (Left Motor Phase B) | LEDC PWM Channel 1 (20 kHz, 8-bit) | Controls Left Motor reverse drive & braking. |
| 5 | **GPIO4** | `MOTOR_R_IN1` | Digital Output | 3.3V (5V tol) | DRV8833 `IN3` (Right Motor Phase A) | LEDC PWM Channel 2 (20 kHz, 8-bit) | Controls Right Motor forward drive & speed. |
| 6 | **GPIO5** | `MOTOR_R_IN2` | Digital Output | 3.3V (5V tol) | DRV8833 `IN4` (Right Motor Phase B) | LEDC PWM Channel 3 (20 kHz, 8-bit) | Controls Right Motor reverse drive & braking. |
| 7 | **GPIO6** | `US_TRIG` | Digital Output | 3.3V | HC-SR04P `TRIG` | Push-Pull, Software Pulsed | Emits 10 µs HIGH trigger pulse to initiate ultrasonic burst. |
| 8 | **GPIO7** | `US_ECHO` | Digital Input | 3.3V | HC-SR04P `ECHO` | High-Z Input / GPIO Interrupt | Measures pulse width ($t_{\text{echo}}$). Distance $= t \times 0.0343 / 2$ cm. |
| 9 | **GPIO8** | `I2C_SDA` | Bidirectional Open-Drain | 3.3V | SSD1306 OLED `SDA` & BME280 `SDA` | External 4.7 kΩ Pull-Up to 3.3V | Hardware I2C0 Serial Data bus (400 kHz Fast-Mode). |
| 10 | **GPIO9** | `I2C_SCL` | Digital Output Open-Drain | 3.3V | SSD1306 OLED `SCL` & BME280 `SCL` | External 4.7 kΩ Pull-Up to 3.3V | Hardware I2C0 Serial Clock bus (400 kHz Fast-Mode). |
| 11 | **GPIO10** | `SERVO_PWM` | Digital Output | 3.3V | SG90 Servo `PWM` (Orange Wire) | LEDC PWM Channel 4 (50 Hz, 14-bit) | 1.0ms (0°) to 2.0ms (180°) radar pan control. |
| 12 | **GPIO11** | `LINE_L_OUT` | Digital Input | 3.3V | 3-Ch TCRT5000 `OUT1` (Left Sensor) | High-Z Input / Pull-Up enabled | LOW on reflective surface, HIGH on dark/drop-off. |
| 13 | **GPIO12** | `LINE_C_OUT` | Digital Input | 3.3V | 3-Ch TCRT5000 `OUT2` (Center Sensor) | High-Z Input / Pull-Up enabled | LOW on reflective surface, HIGH on dark/drop-off. |
| 14 | **GPIO13** | `LINE_R_OUT` | Digital Input | 3.3V | 3-Ch TCRT5000 `OUT3` (Right Sensor) | High-Z Input / Pull-Up enabled | LOW on reflective surface, HIGH on dark/drop-off. |
| 15 | **GPIO14** | `BATT_ADC` | Analog Input | 0V – 2.7V | Voltage Divider ($R_1=100\text{k}\Omega / R_2=47\text{k}\Omega$) | ADC1 Channel 3, 11 dB Attenuation | $V_{\text{BAT}} = V_{\text{ADC}} \times 3.1278$. Filtered with 100nF capacitor. |
| 16 | **GPIO15** | `MOTOR_NSLEEP`| Digital Output | 3.3V | DRV8833 `nSLEEP` (Sleep / Enable) | Pull-Down (Default Sleep on reset) | Active HIGH. Set LOW during standby to enter 1.6µA sleep. |
| 17 | **GPIO38** | `WS2812_STATUS`| Digital Output | 3.3V | Onboard RGB WS2812B NeoPixel | RMT Peripheral / FastLED | Visual diagnostic beacon (Green=OK, Blue=WiFi, Red=LowBatt). |
| 18 | **5V / VIN** | `+5V_BUCK` | Power Input | 5.0V DC (±2%) | MP1584EN Buck Converter `OUT+` | Bulk Decoupled (100µF + 100nF) | Powers ESP32-S3 board through low-dropout 3.3V regulator. |

---

## 2. Drop-in Alternative Architecture: Raspberry Pi Pico (RP2040) Pinout Matrix

| Pin # | RP2040 Pin | Physical Function / Net Name | Signal Type | Logic Level | Connected Peripheral & Pin | Notes / Hardware Resource |
|:---:|:---:|:---|:---:|:---:|:---|:---:|
| 1 | **GP0** | `I2C0_SDA` | Bidirectional Open-Drain | 3.3V | SSD1306 `SDA` & BME280 `SDA` | I2C0 Controller SDA (400 kHz) |
| 2 | **GP1** | `I2C0_SCL` | Digital Output Open-Drain | 3.3V | SSD1306 `SCL` & BME280 `SCL` | I2C0 Controller SCL (400 kHz) |
| 4 | **GP2** | `MOTOR_L_IN1` | Digital Output | 3.3V | DRV8833 `IN1` | PWM Slice 1 Channel A |
| 5 | **GP3** | `MOTOR_L_IN2` | Digital Output | 3.3V | DRV8833 `IN2` | PWM Slice 1 Channel B |
| 6 | **GP4** | `MOTOR_R_IN1` | Digital Output | 3.3V | DRV8833 `IN3` | PWM Slice 2 Channel A |
| 7 | **GP5** | `MOTOR_R_IN2` | Digital Output | 3.3V | DRV8833 `IN4` | PWM Slice 2 Channel B |
| 9 | **GP6** | `US_TRIG` | Digital Output | 3.3V | HC-SR04P `TRIG` | GPIO Output / PIO State Machine 0 |
| 10 | **GP7** | `US_ECHO` | Digital Input | 3.3V | HC-SR04P `ECHO` | GPIO Input / PIO State Machine 0 |
| 11 | **GP8** | `SERVO_PWM` | Digital Output | 3.3V | SG90 Servo `PWM` | PWM Slice 4 Channel A (50 Hz) |
| 12 | **GP9** | `LINE_L_OUT` | Digital Input | 3.3V | TCRT5000 `OUT1` | GPIO Input (Left Line Tracker) |
| 14 | **GP10** | `LINE_C_OUT` | Digital Input | 3.3V | TCRT5000 `OUT2` | GPIO Input (Center Line Tracker) |
| 15 | **GP11** | `LINE_R_OUT` | Digital Input | 3.3V | TCRT5000 `OUT3` | GPIO Input (Right Line Tracker) |
| 19 | **GP14** | `MOTOR_NSLEEP`| Digital Output | 3.3V | DRV8833 `nSLEEP` | GPIO Output (Active HIGH Driver Enable) |
| 31 | **GP26 (ADC0)**| `BATT_ADC` | Analog Input | 0V – 2.7V | Resistor Divider Tap | RP2040 12-bit SAR ADC Channel 0 |
| 36 | **3V3(OUT)** | `+3.3V` | Power Output | 3.3V DC | Sensors & Displays | Onboard RT6150 Buck-Boost Regulator |
| 39 | **VSYS** | `+5V_BUCK` | Power Input | 5.0V DC | MP1584EN Buck Converter `OUT+` | Powers RP2040 via internal Schottky diode |
| 38 | **GND** | `GND` | Ground Reference | 0V | System Common Ground | Reference ground plane |

---

## 3. Peripheral Electrical Interfaces & Protocols

### 3.1 I2C Bus Topology (Address & Timing Specifications)
* **Bus Speed:** 400 kHz (Fast Mode).
* **Pull-Up Resistors:** Dual external $4.7\text{ k}\Omega$ metal-film resistors pulling `SDA` and `SCL` to `+3.3V`.
* **Devices on Bus:**
  1. **SSD1306 OLED HUD:** 7-bit I2C address `0x3C` (selectable to `0x3D` via onboard solder jumper).
  2. **BME280 Sensor:** 7-bit I2C address `0x76` (SDO tied to GND; selectable to `0x77` if SDO pulled to VCC).
* **Collision Check:** Addresses are hardware unique (`0x3C` vs `0x76`), guaranteeing collision-free simultaneous operation on the single bus pair.

### 3.2 Ultrasonic Ranging Protocol (HC-SR04P)
* **Triggering:** Apply minimum $10\,\mu\text{s}$ HIGH pulse on `GPIO6`.
* **Sonic Emission:** Sensor automatically generates eight $40\,\text{kHz}$ acoustic pulses and raises `ECHO` (`GPIO7`) HIGH.
* **Return Capture:** `ECHO` stays HIGH until reflected ultrasound returns to receiver. Pulse width $T$ (in $\mu\text{s}$) is measured via hardware input capture timer or interrupt.
* **Distance Calculation:**
  $$D = \frac{T \times 0.03432\,\text{cm}/\mu\text{s}}{2} \quad (\text{at } 20^\circ\text{C})$$
* **Temperature Compensation:** Since TerraScout carries an onboard BME280 sensor, speed of sound $c$ is dynamically compensated in firmware:
  $$c = 331.3 \times \sqrt{1 + \frac{T_{\text{ambient}}}{273.15}}\ \text{m/s}$$
  Yielding millimeter-accurate ranging across varying ambient field temperatures.

### 3.3 Servo Pan Radar Protocol (SG90)
* **PWM Frequency:** $50\,\text{Hz}$ ($20\,\text{ms}$ period).
* **Duty Cycle Resolution:** 14-bit timer ($16384$ ticks).
* **Angle Mapping:**
  * $0^\circ$ (Full Left): $1.0\,\text{ms}$ pulse width (5.0% duty cycle).
  * $90^\circ$ (Dead Ahead): $1.5\,\text{ms}$ pulse width (7.5% duty cycle).
  * $180^\circ$ (Full Right): $2.0\,\text{ms}$ pulse width (10.0% duty cycle).
* **Current Isolation:** Powered strictly from the $+5.0\text{V}$ buck regulator with local $100\,\mu\text{F}$ capacitor to absorb servo motor commutation stalls without glitching the MCU logic rail.
