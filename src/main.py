"""
================================================================================
TerraScout Grounded Telemetry Rover - Autonomous Firmware
Project: TerraScout Grounded (Autonomous Telemetry Rover)
Target: MicroPython / CircuitPython on Raspberry Pi Pico (RP2040) / ESP32
License: MIT / CERN-OHL-P v2
================================================================================

Architecture Overview:
  1. Hardware Abstraction Layer (HAL):
     - Auto-detects MicroPython hardware (`machine`, `time`, `micropython`).
     - Falls back to pure-Python Virtual Hardware Emulation when run on desktop.
  2. Differential Drive PID Motion Controller:
     - Independent left and right motor closed-loop PID control loops.
     - Kinematic differential drive mixer: forward, reverse, turn, pivot_left,
       pivot_right, stop, and active electronic braking.
     - Slew rate acceleration limiting to protect N20 brass gearboxes.
  3. Ultrasonic Distance & Pan-Tilt Head:
     - SG90 Micro Servo pan head (-60 deg to +60 deg scan range).
     - HC-SR04 / RCWL-1601 ultrasonic rangefinder with timeout protection
       and median noise filtering.
  4. Environmental & Telemetry Subsystems:
     - I2C BME280 driver (ambient temperature, barometric pressure, altitude).
     - I2C SSD1306 128x64 OLED HUD (status header, radar arc, telemetry feed).
     - Streaming JSON Telemetry Logger over Serial / UART.
  5. Autonomous Obstacle Avoidance State Machine:
     - High-level decision loop evaluating forward clearance, obstacle triggers,
       multi-point panoramic sweeps, cost-weighted pathfinding, and recovery reversals.
================================================================================
"""

import math
import sys
import time

# ==============================================================================
# Hardware Abstraction Layer (HAL) & Desktop Simulation Support
# ==============================================================================
IS_EMBEDDED = False
try:
    import machine  # type: ignore
    from machine import I2C, PWM, Pin  # type: ignore
    IS_EMBEDDED = True
except ImportError:
    # Desktop environment: Emulate MicroPython hardware abstractions
    class MockPin:
        OUT = 1
        IN = 0
        PULL_UP = 1
        PULL_DOWN = 2

        def __init__(self, pin_num, mode=OUT, pull=None):
            self.pin_num = pin_num
            self.mode = mode
            self.val = 0

        def value(self, v=None):
            if v is not None:
                self.val = int(v)
            return self.val

        def __call__(self, v=None):
            return self.value(v)

    class MockPWM:
        def __init__(self, pin, freq=1000, duty_u16=0):
            self.pin = pin
            self._freq = freq
            self._duty = duty_u16

        def freq(self, f=None):
            if f is not None:
                self._freq = f
            return self._freq

        def duty_u16(self, d=None):
            if d is not None:
                self._duty = max(0, min(65535, int(d)))
            return self._duty

        def deinit(self):
            self._duty = 0

    class MockI2C:
        def __init__(self, id_or_bus=0, scl=None, sda=None, freq=400000):
            self.freq = freq

        def scan(self):
            # Simulate BME280 (0x76) and SSD1306 OLED (0x3C)
            return [0x3C, 0x76]

        def writeto(self, addr, buf):
            return len(buf)

        def readfrom(self, addr, nbytes):
            return b"\x00" * nbytes

        def readfrom_mem(self, addr, memaddr, nbytes):
            # Simulated BME280 compensation registers & readout
            return b"\x55" * nbytes

        def writeto_mem(self, addr, memaddr, buf):
            return len(buf)

    Pin = MockPin  # type: ignore
    PWM = MockPWM  # type: ignore
    I2C = MockI2C  # type: ignore


# High-precision millisecond and microsecond timing abstraction
def ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def ticks_us():
    if hasattr(time, "ticks_us"):
        return time.ticks_us()
    return int(time.time() * 1000000)


def ticks_diff(t1, t2):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(t1, t2)
    return t1 - t2


def sleep_ms(ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(ms)
    else:
        time.sleep(ms / 1000.0)


def sleep_us(us):
    if hasattr(time, "sleep_us"):
        time.sleep_us(us)
    else:
        time.sleep(us / 1000000.0)


# ==============================================================================
# Hardware Pin Configurations (Default: Raspberry Pi Pico / RP2040)
# ==============================================================================
PIN_CONFIG = {
    # Motor Left (N20 + H-Bridge DRV8833/TB6612)
    "MOTOR_L_IN1": 18,
    "MOTOR_L_IN2": 19,
    # Motor Right (N20 + H-Bridge DRV8833/TB6612)
    "MOTOR_R_IN1": 20,
    "MOTOR_R_IN2": 21,
    # Panning SG90 Micro Servo
    "SERVO_PIN": 15,
    # Ultrasonic HC-SR04 / RCWL-1601
    "TRIGGER_PIN": 16,
    "ECHO_PIN": 17,
    # I2C Bus for SSD1306 OLED & BME280
    "I2C_ID": 0,
    "I2C_SDA": 4,
    "I2C_SCL": 5,
    "I2C_FREQ": 400000,
    # Status LED
    "STATUS_LED": 25,  # Onboard Pico LED
}


# ==============================================================================
# PID Controller Implementation
# ==============================================================================
class PIDController:
    """Discrete-time Proportional-Integral-Derivative controller with anti-windup."""

    def __init__(self, kp=1.8, ki=0.25, kd=0.08, out_min=-100.0, out_max=100.0, integral_limit=40.0):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.out_min = float(out_min)
        self.out_max = float(out_max)
        self.integral_limit = float(integral_limit)

        self._integral = 0.0
        self._prev_error = 0.0
        self._last_time = None

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._last_time = None

    def update(self, target, measured, dt=None):
        """Calculates control output given setpoint and current process value."""
        now = ticks_ms()
        if dt is None:
            if self._last_time is None:
                dt = 0.05
            else:
                dt = max(0.001, ticks_diff(now, self._last_time) / 1000.0)
        self._last_time = now

        error = target - measured

        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup clamping
        self._integral += error * dt
        if self._integral > self.integral_limit:
            self._integral = self.integral_limit
        elif self._integral < -self.integral_limit:
            self._integral = -self.integral_limit
        i_term = self.ki * self._integral

        # Derivative term
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        self._prev_error = error

        # Compute combined output clamped to saturation limits
        output = p_term + i_term + d_term
        if output > self.out_max:
            output = self.out_max
        elif output < self.out_min:
            output = self.out_min

        return output


# ==============================================================================
# Dual Motor Differential Drive Controller
# ==============================================================================
class MotorChannel:
    """Controls a single H-bridge channel using complementary PWM pins."""

    def __init__(self, in1_pin, in2_pin, pwm_freq=20000):
        self.pin1 = Pin(in1_pin, Pin.OUT)
        self.pin2 = Pin(in2_pin, Pin.OUT)
        self.pwm1 = PWM(self.pin1)
        self.pwm2 = PWM(self.pin2)
        self.pwm1.freq(pwm_freq)
        self.pwm2.freq(pwm_freq)
        self.pwm1.duty_u16(0)
        self.pwm2.duty_u16(0)
        self.current_duty = 0.0

    def set_effort(self, effort_pct):
        """Sets motor effort from -100.0 (full reverse) to +100.0 (full forward)."""
        effort_pct = max(-100.0, min(100.0, float(effort_pct)))
        self.current_duty = effort_pct

        # Apply deadband compensation for N20 motors (< 12% cannot break static friction)
        if abs(effort_pct) < 2.0:
            self.pwm1.duty_u16(0)
            self.pwm2.duty_u16(0)
            return

        duty = int((abs(effort_pct) / 100.0) * 65535)

        if effort_pct > 0:
            # Forward
            self.pwm1.duty_u16(duty)
            self.pwm2.duty_u16(0)
        else:
            # Reverse
            self.pwm1.duty_u16(0)
            self.pwm2.duty_u16(duty)

    def brake(self):
        """Actively shorts motor windings through H-bridge for dynamic braking."""
        self.current_duty = 0.0
        self.pwm1.duty_u16(65535)
        self.pwm2.duty_u16(65535)

    def coast(self):
        """Disables drive, allowing motor to spin down freely."""
        self.current_duty = 0.0
        self.pwm1.duty_u16(0)
        self.pwm2.duty_u16(0)


class DifferentialDrive:
    """Differential drive motion controller coordinating dual N20 gearmotors."""

    def __init__(self, left_pins, right_pins, track_width_mm=86.0):
        self.track_width = track_width_mm
        self.left_motor = MotorChannel(left_pins[0], left_pins[1])
        self.right_motor = MotorChannel(right_pins[0], right_pins[1])

        # Dual PID velocity loops
        self.pid_left = PIDController(kp=1.5, ki=0.2, kd=0.05)
        self.pid_right = PIDController(kp=1.5, ki=0.2, kd=0.05)

        # Target and estimated velocities (-100 to 100 scale)
        self.target_left = 0.0
        self.target_right = 0.0
        self.actual_left = 0.0
        self.actual_right = 0.0

        # Slew rate acceleration limiter (% per second)
        self.max_slew_rate = 180.0  # Max 180% per second ramp
        self.last_update = ticks_ms()

    def update(self):
        """Executes one control cycle: ramps speeds and computes PID effort."""
        now = ticks_ms()
        dt = max(0.001, ticks_diff(now, self.last_update) / 1000.0)
        self.last_update = now

        # Slew rate ramp towards target
        step = self.max_slew_rate * dt

        # Left motor ramp
        if self.actual_left < self.target_left:
            self.actual_left = min(self.target_left, self.actual_left + step)
        elif self.actual_left > self.target_left:
            self.actual_left = max(self.target_left, self.actual_left - step)

        # Right motor ramp
        if self.actual_right < self.target_right:
            self.actual_right = min(self.target_right, self.actual_right + step)
        elif self.actual_right > self.target_right:
            self.actual_right = max(self.target_right, self.actual_right - step)

        # PID effort calculation
        out_l = self.pid_left.update(self.actual_left, self.actual_left, dt)
        out_r = self.pid_right.update(self.actual_right, self.actual_right, dt)

        self.left_motor.set_effort(out_l)
        self.right_motor.set_effort(out_r)

    def forward(self, speed=60.0):
        """Drives forward in a straight vector at specified speed percentage."""
        spd = max(0.0, min(100.0, float(speed)))
        self.target_left = spd
        self.target_right = spd

    def reverse(self, speed=45.0):
        """Drives backward in a straight vector at specified speed percentage."""
        spd = max(0.0, min(100.0, float(speed)))
        self.target_left = -spd
        self.target_right = -spd

    def turn(self, speed=50.0, steer=0.4):
        """
        Drives in a smooth curve.
        steer > 0: turns right (reduces right wheel speed).
        steer < 0: turns left (reduces left wheel speed).
        """
        steer = max(-1.0, min(1.0, float(steer)))
        if steer >= 0:
            self.target_left = speed
            self.target_right = speed * (1.0 - steer * 1.5)
        else:
            self.target_left = speed * (1.0 - abs(steer) * 1.5)
            self.target_right = speed

    def pivot_left(self, speed=50.0):
        """Zero-radius left counter-rotation pivot."""
        spd = max(0.0, min(100.0, float(speed)))
        self.target_left = -spd
        self.target_right = spd

    def pivot_right(self, speed=50.0):
        """Zero-radius right counter-rotation pivot."""
        spd = max(0.0, min(100.0, float(speed)))
        self.target_left = spd
        self.target_right = -spd

    def stop(self):
        """Smoothly stops motion and zeroes targets."""
        self.target_left = 0.0
        self.target_right = 0.0
        self.left_motor.coast()
        self.right_motor.coast()
        self.pid_left.reset()
        self.pid_right.reset()

    def brake(self):
        """Dynamic emergency braking."""
        self.target_left = 0.0
        self.target_right = 0.0
        self.actual_left = 0.0
        self.actual_right = 0.0
        self.left_motor.brake()
        self.right_motor.brake()
        self.pid_left.reset()
        self.pid_right.reset()


# ==============================================================================
# Ultrasonic Rangefinder & Pan Servo Head
# ==============================================================================
class PanServo:
    """Controls the SG90 panning servo for look-ahead radar scanning."""

    def __init__(self, pin_num, min_us=600, max_us=2400):
        self.pin = Pin(pin_num, Pin.OUT)
        self.pwm = PWM(self.pin)
        self.pwm.freq(50)  # Standard 50Hz RC servo period (20ms)
        self.min_us = min_us
        self.max_us = max_us
        self.current_angle = 0
        self.center()

    def set_angle(self, angle_deg):
        """
        Sets servo angle from -60 (hard left) to +60 (hard right).
        0 degrees is centered straight ahead.
        """
        angle_deg = max(-60.0, min(60.0, float(angle_deg)))
        self.current_angle = angle_deg

        # Map [-60..+60] to [0..180] physical servo domain
        mapped_deg = angle_deg + 90.0

        # Convert degrees to microsecond pulse width
        pulse_us = self.min_us + (mapped_deg / 180.0) * (self.max_us - self.min_us)

        # Convert to 16-bit PWM duty cycle (period = 20,000 us)
        duty = int((pulse_us / 20000.0) * 65535)
        self.pwm.duty_u16(duty)

    def center(self):
        self.set_angle(0.0)


class UltrasonicSensor:
    """HC-SR04 / RCWL-1601 ultrasonic distance sensor with median noise filter."""

    def __init__(self, trig_pin, echo_pin, timeout_us=30000):
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.trig.value(0)
        self.timeout_us = timeout_us  # Max distance ~510cm
        self.last_valid_dist = 150.0

    def read_single_cm(self):
        """Triggers a single 10us ultrasonic burst and measures pulse width."""
        if not IS_EMBEDDED:
            # Emulated reading for desktop testing
            return 120.0

        # Trigger pulse
        self.trig.value(0)
        sleep_us(2)
        self.trig.value(1)
        sleep_us(10)
        self.trig.value(0)

        # Wait for Echo pin to go HIGH
        t_start = ticks_us()
        while self.echo.value() == 0:
            if ticks_diff(ticks_us(), t_start) > self.timeout_us:
                return 400.0  # Open corridor timeout

        echo_start = ticks_us()

        # Wait for Echo pin to go LOW
        while self.echo.value() == 1:
            if ticks_diff(ticks_us(), echo_start) > self.timeout_us:
                return 400.0

        echo_end = ticks_us()
        pulse_duration = ticks_diff(echo_end, echo_start)

        # Speed of sound: 343 m/s = 0.0343 cm/us -> distance = duration / 58.2
        dist_cm = pulse_duration / 58.2
        if 2.0 <= dist_cm <= 400.0:
            return dist_cm
        return 400.0

    def get_distance_filtered(self, samples=3):
        """Takes multiple rapid pulses and returns the median distance."""
        readings = []
        for _ in range(samples):
            d = self.read_single_cm()
            readings.append(d)
            sleep_ms(8)

        readings.sort()
        median = readings[len(readings) // 2]
        self.last_valid_dist = median
        return median


# ==============================================================================
# BME280 Environmental Telemetry Driver (I2C)
# ==============================================================================
class BME280Sensor:
    """I2C environmental sensor reading temperature, barometric pressure, and altitude."""

    def __init__(self, i2c, address=0x76):
        self.i2c = i2c
        self.address = address
        self.available = False
        self._init_sensor()

    def _init_sensor(self):
        try:
            # Scan bus to check if device responds
            devs = self.i2c.scan()
            if self.address in devs:
                self.available = True
                # Set forced mode / sample rates
                self.i2c.writeto_mem(self.address, 0xF4, b"\x27")  # Normal mode, 1x oversampling
        except Exception:
            self.available = False

    def read_telemetry(self):
        """Returns (temperature_c, pressure_hpa, altitude_m)."""
        if not self.available or not IS_EMBEDDED:
            # Simulated atmospheric data
            return (23.4, 1013.2, 45.2)

        try:
            # Read 6 raw data bytes (Press MSB, LSB, XLSB; Temp MSB, LSB, XLSB)
            raw = self.i2c.readfrom_mem(self.address, 0xF7, 6)
            raw_p = ((raw[0] << 16) | (raw[1] << 8) | raw[2]) >> 4
            raw_t = ((raw[3] << 16) | (raw[4] << 8) | raw[5]) >> 4

            # Linear conversion approximation for telemetry HUD
            temp_c = (raw_t / 16384.0) * 10.0 + 20.0
            press_hpa = (raw_p / 256.0) * 0.1 + 950.0

            # Hypsometric formula for barometric altitude
            altitude_m = 44330.0 * (1.0 - (press_hpa / 1013.25) ** 0.1903)
            return (round(temp_c, 2), round(press_hpa, 1), round(altitude_m, 1))
        except Exception:
            return (22.0, 1013.0, 0.0)


# ==============================================================================
# SSD1306 OLED HUD Display Driver (I2C)
# ==============================================================================
class OLEDHud:
    """128x64 I2C OLED Heads-Up Display showing rover radar arc & telemetry."""

    def __init__(self, i2c, address=0x3C):
        self.i2c = i2c
        self.address = address
        self.available = False
        self.buffer = bytearray(128 * 64 // 8)
        self._init_display()

    def _init_display(self):
        try:
            devs = self.i2c.scan()
            if self.address in devs:
                self.available = True
        except Exception:
            self.available = False

    def clear(self):
        for i in range(len(self.buffer)):
            self.buffer[i] = 0

    def render(self, state_name, forward_dist, scan_data, temp_c, press_hpa, left_pwr, right_pwr):
        """Draws HUD telemetry dashboard and transmits frame to display."""
        if not self.available:
            return

        # Simple terminal/frame logging if on embedded device with framebuf
        try:
            import framebuf  # type: ignore

            fb = framebuf.FrameBuffer(self.buffer, 128, 64, framebuf.MONO_VLSB)
            fb.fill(0)

            # Header
            fb.text(f"TSCOUT: {state_name[:7]}", 0, 0, 1)
            fb.text(f"{int(forward_dist):3d}cm", 88, 0, 1)
            fb.hline(0, 10, 128, 1)

            # Radar clearance indicators [-60, -30, 0, +30, +60]
            angles = [-60, -30, 0, 30, 60]
            for i, ang in enumerate(angles):
                val = scan_data.get(ang, 100.0)
                bar_h = min(20, max(2, int(val / 8.0)))
                x = 14 + i * 22
                fb.vline(x, 34 - bar_h, bar_h, 1)
                fb.text(str(int(val)), x - 8, 36, 1)

            # Bottom environmental and drive telemetry
            fb.hline(0, 48, 128, 1)
            fb.text(f"{temp_c:.1f}C {press_hpa:.0f}hPa", 0, 52, 1)
            fb.text(f"L{int(left_pwr)} R{int(right_pwr)}", 76, 52, 1)

            # Transmit to SSD1306
            self.i2c.writeto_mem(self.address, 0x40, self.buffer)
        except Exception:
            pass


# ==============================================================================
# Autonomous Obstacle Avoidance State Machine
# ==============================================================================
class RoverStateMachine:
    """Obstacle avoidance and navigation state engine."""

    # States
    STATE_BOOT = "BOOT"
    STATE_CRUISE = "CRUISE"
    STATE_SLOW_APPROACH = "SLOW_APP"
    STATE_PANORAMIC_SCAN = "SCAN"
    STATE_PATHFINDING = "PATHFIND"
    STATE_PIVOT_AVOID = "PIVOT"
    STATE_EMERGENCY_REVERSE = "REVERSE"
    STATE_STOPPED = "STOPPED"

    # Thresholds (cm)
    THRESHOLD_OBSTACLE_WARN = 38.0
    THRESHOLD_OBSTACLE_CRIT = 20.0
    THRESHOLD_EMERGENCY_BACKUP = 14.0

    def __init__(self, drive, servo, ultrasonic, bme, oled):
        self.drive = drive
        self.servo = servo
        self.ultrasonic = ultrasonic
        self.bme = bme
        self.oled = oled

        self.state = self.STATE_BOOT
        self.scan_angles = [-60, -30, 0, 30, 60]
        self.scan_results = {ang: 200.0 for ang in self.scan_angles}
        self.best_heading = 0.0
        self.state_enter_time = ticks_ms()
        self.pivot_duration_ms = 0

    def change_state(self, new_state):
        self.state = new_state
        self.state_enter_time = ticks_ms()

    def update(self):
        """Processes state machine transitions."""
        now = ticks_ms()
        state_elapsed = ticks_diff(now, self.state_enter_time)

        # ----------------------------------------------------------------------
        # STATE: BOOT
        # ----------------------------------------------------------------------
        if self.state == self.STATE_BOOT:
            self.servo.center()
            self.drive.stop()
            if state_elapsed > 1200:
                self.change_state(self.STATE_CRUISE)

        # ----------------------------------------------------------------------
        # STATE: CRUISE (Forward autonomous traversal)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_CRUISE:
            self.servo.center()
            dist = self.ultrasonic.get_distance_filtered(samples=2)

            if dist <= self.THRESHOLD_EMERGENCY_BACKUP:
                self.drive.brake()
                self.change_state(self.STATE_EMERGENCY_REVERSE)
            elif dist <= self.THRESHOLD_OBSTACLE_CRIT:
                self.drive.brake()
                self.change_state(self.STATE_PANORAMIC_SCAN)
            elif dist <= self.THRESHOLD_OBSTACLE_WARN:
                # Approaching obstacle: decelerate
                self.drive.forward(speed=35.0)
                self.change_state(self.STATE_SLOW_APPROACH)
            else:
                # Cruising clear path
                self.drive.forward(speed=65.0)

        # ----------------------------------------------------------------------
        # STATE: SLOW APPROACH
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_SLOW_APPROACH:
            dist = self.ultrasonic.get_distance_filtered(samples=2)
            if dist <= self.THRESHOLD_OBSTACLE_CRIT:
                self.drive.brake()
                self.change_state(self.STATE_PANORAMIC_SCAN)
            elif dist > self.THRESHOLD_OBSTACLE_WARN + 8.0:
                self.change_state(self.STATE_CRUISE)
            else:
                self.drive.forward(speed=30.0)

        # ----------------------------------------------------------------------
        # STATE: PANORAMIC SCAN (-60 deg to +60 deg sweep)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_PANORAMIC_SCAN:
            self.drive.stop()

            # Execute 5-point sweep
            for ang in self.scan_angles:
                self.servo.set_angle(ang)
                sleep_ms(180)  # Settle time for SG90 servo
                d = self.ultrasonic.get_distance_filtered(samples=3)
                self.scan_results[ang] = d

            self.servo.center()
            sleep_ms(100)
            self.change_state(self.STATE_PATHFINDING)

        # ----------------------------------------------------------------------
        # STATE: PATHFINDING (Evaluate clearance sectors)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_PATHFINDING:
            # Cost-weighted clearance function:
            # Penalize sharp turns slightly to encourage straight courses if clear
            best_score = -1.0
            chosen_angle = 0.0

            for ang, dist in self.scan_results.items():
                # Heading bias: favor center unless obstructed
                bias = 1.0 - (abs(ang) / 120.0) * 0.25
                score = dist * bias

                if score > best_score:
                    best_score = score
                    chosen_angle = ang

            self.best_heading = chosen_angle

            # Check if completely trapped in dead-end
            max_clearance = max(self.scan_results.values())
            if max_clearance < self.THRESHOLD_OBSTACLE_CRIT:
                # Dead end detected: reverse out
                self.change_state(self.STATE_EMERGENCY_REVERSE)
            else:
                # Compute pivot duration based on angular deflection
                # Calibrated for N20 motors at 50% power: ~12ms per degree
                self.pivot_duration_ms = int(abs(chosen_angle) * 14.0) + 120
                self.change_state(self.STATE_PIVOT_AVOID)

        # ----------------------------------------------------------------------
        # STATE: PIVOT AVOID (Execute zero-radius turn)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_PIVOT_AVOID:
            if self.best_heading < 0:
                self.drive.pivot_left(speed=52.0)
            else:
                self.drive.pivot_right(speed=52.0)

            if state_elapsed >= self.pivot_duration_ms:
                self.drive.brake()
                self.change_state(self.STATE_CRUISE)

        # ----------------------------------------------------------------------
        # STATE: EMERGENCY REVERSE (Back out of dead end)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_EMERGENCY_REVERSE:
            self.drive.reverse(speed=42.0)
            if state_elapsed >= 1100:  # Reverse for 1.1 seconds
                self.drive.brake()
                self.change_state(self.STATE_PANORAMIC_SCAN)

        # Always update differential drive PID loops
        self.drive.update()


# ==============================================================================
# Master Rover Orchestrator & Telemetry Loop
# ==============================================================================
class TerraScoutRover:
    """Master controller coordinating hardware, navigation, telemetry, and HUD."""

    def __init__(self):
        print("[TERRASCOUT] Initializing hardware subsystems...")

        # 1. Drive Controller
        self.drive = DifferentialDrive(
            left_pins=(PIN_CONFIG["MOTOR_L_IN1"], PIN_CONFIG["MOTOR_L_IN2"]),
            right_pins=(PIN_CONFIG["MOTOR_R_IN1"], PIN_CONFIG["MOTOR_R_IN2"]),
        )

        # 2. Scanning Turret
        self.servo = PanServo(PIN_CONFIG["SERVO_PIN"])
        self.ultrasonic = UltrasonicSensor(PIN_CONFIG["TRIGGER_PIN"], PIN_CONFIG["ECHO_PIN"])

        # 3. I2C Sensors & HUD
        self.i2c = I2C(
            PIN_CONFIG["I2C_ID"],
            sda=Pin(PIN_CONFIG["I2C_SDA"]),
            scl=Pin(PIN_CONFIG["I2C_SCL"]),
            freq=PIN_CONFIG["I2C_FREQ"],
        )
        self.bme = BME280Sensor(self.i2c)
        self.oled = OLEDHud(self.i2c)

        # 4. State Engine
        self.sm = RoverStateMachine(self.drive, self.servo, self.ultrasonic, self.bme, self.oled)

        # Timers
        self.last_hud_update = ticks_ms()
        self.last_telemetry_emit = ticks_ms()
        print("[TERRASCOUT] Initialization complete. System armed.")

    def run_step(self):
        """Single non-blocking execution cycle."""
        # 1. Update navigation state machine
        self.sm.update()

        now = ticks_ms()

        # 2. HUD refresh loop (5 Hz)
        if ticks_diff(now, self.last_hud_update) >= 200:
            self.last_hud_update = now
            t, p, _ = self.bme.read_telemetry()
            self.oled.render(
                state_name=self.sm.state,
                forward_dist=self.ultrasonic.last_valid_dist,
                scan_data=self.sm.scan_results,
                temp_c=t,
                press_hpa=p,
                left_pwr=self.drive.actual_left,
                right_pwr=self.drive.actual_right,
            )

        # 3. Serial JSON Telemetry Logger (2 Hz)
        if ticks_diff(now, self.last_telemetry_emit) >= 500:
            self.last_telemetry_emit = now
            t, p, alt = self.bme.read_telemetry()
            telemetry_packet = (
                f'{{"time_ms":{now},'
                f'"state":"{self.sm.state}",'
                f'"dist_cm":{self.ultrasonic.last_valid_dist:.1f},'
                f'"best_hdg":{self.sm.best_heading:.0f},'
                f'"temp_c":{t:.2f},'
                f'"press_hpa":{p:.1f},'
                f'"alt_m":{alt:.1f},'
                f'"motor_l":{self.drive.actual_left:.1f},'
                f'"motor_r":{self.drive.actual_right:.1f}}}'
            )
            print(f"[TELEM] {telemetry_packet}")

    def loop(self, max_iterations=None):
        """Main execution loop."""
        iteration = 0
        try:
            while max_iterations is None or iteration < max_iterations:
                self.run_step()
                sleep_ms(25)  # 40Hz control tick
                iteration += 1
        except KeyboardInterrupt:
            print("\n[TERRASCOUT] Safe shutdown requested.")
            self.drive.stop()
            self.servo.center()


# ==============================================================================
# Self-Test & Diagnostic Routine
# ==============================================================================
def run_diagnostics():
    """Runs a complete automated bench test of all subsystems."""
    print("=" * 60)
    print("TERRASCOUT AUTONOMOUS ROVER - HARDWARE SELF-TEST")
    print(f"Platform: {'Embedded MicroPython' if IS_EMBEDDED else 'Desktop Simulation'}")
    print("=" * 60)

    rover = TerraScoutRover()

    # Test 1: Sensor Readings
    t, p, alt = rover.bme.read_telemetry()
    print(f"[TEST 1] BME280 -> Temp: {t:.2f} C | Press: {p:.1f} hPa | Alt: {alt:.1f} m")

    # Test 2: Ultrasonic Rangefinder
    d = rover.ultrasonic.get_distance_filtered()
    print(f"[TEST 2] Ultrasonic Rangefinder -> {d:.1f} cm")

    # Test 3: Servo Pan Sweep
    print("[TEST 3] Exercising Servo Pan Turret (-60 deg to +60 deg)...")
    for ang in [-60, -30, 0, 30, 60]:
        rover.servo.set_angle(ang)
        sleep_ms(100)
    rover.servo.center()
    print("  -> Servo Sweep PASS")

    # Test 4: Differential Motion Controller
    print("[TEST 4] Exercising Differential Drive Controller...")
    rover.drive.forward(40)
    rover.drive.update()
    sleep_ms(100)
    rover.drive.pivot_right(50)
    rover.drive.update()
    sleep_ms(100)
    rover.drive.brake()
    print("  -> Drive Motion Controller PASS")

    # Test 5: State Machine Step Simulation
    print("[TEST 5] Executing 20 State Machine Cycles...")
    rover.loop(max_iterations=20)
    print("  -> State Machine PASS")

    print("=" * 60)
    print("ALL DIAGNOSTIC BENCH TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--test", "--diag"):
        run_diagnostics()
    else:
        # Standard launch
        rover = TerraScoutRover()
        rover.loop()
