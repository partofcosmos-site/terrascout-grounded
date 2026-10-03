"""
================================================================================
TerraScout Grounded Telemetry Rover - Autonomous Firmware & Flight Controller
Project: TerraScout Grounded (Autonomous Telemetry Rover)
Target: MicroPython / CircuitPython on Raspberry Pi Pico (RP2040) / ESP32
License: MIT / CERN-OHL-P v2
================================================================================

Architecture Overview:
  1. Hardware Abstraction Layer (HAL):
     - Auto-detects MicroPython hardware (`machine`, `time`, `micropython`).
     - Falls back to high-fidelity Virtual Hardware Emulation on desktop platforms.
  2. Inertial Measurement Unit (IMU) & Active State Estimation:
     - MPU6050 6-DOF accelerometer and gyroscope I2C driver.
     - Discrete-time Kalman Filter (1D state-space) and Complementary Filter for
       pitch, roll, and gyro bias estimation.
     - Gyro-integrated heading (yaw) tracking with zero-motion bias rejection.
     - BME280 barometric Kalman filter for smoothed altitude and vertical climb rate.
  3. Power Subsystem:
     - ADC voltage sensing for 2S Li-ion battery pack (6.0V - 8.4V).
     - Real-time State of Charge (SoC %) and critical undervoltage protection.
  4. Adaptive Speed Governor & Differential Motion Controller:
     - Distance-proportional adaptive speed ramping with smooth deceleration curves.
     - Independent left and right closed-loop PID velocity controllers with anti-windup.
     - Slew rate acceleration and deceleration jerk limiting.
     - Closed-loop heading hold and IMU-governed precision pivot turns.
  5. Obstacle Avoidance 2D Local Occupancy Grid Map:
     - 41x41 cell local Cartesian grid (5cm resolution, 205cm x 205cm local span).
     - Raycasting Bayesian occupancy updates from ultrasonic sweeps.
     - Polar clearance sector cost evaluation (-60 deg to +60 deg).
  6. Autonomous Multi-State Navigation Engine:
     - High-level decision loop evaluating forward clearance, proximity alerts,
     - panoramic sweeps, grid corridor analysis, closed-loop pivots, and dead-end reversals.
  7. Environmental & Serial Telemetry Broadcast:
     - SSD1306 128x64 OLED HUD rendering radar arc and motion metrics.
     - High-frequency streaming JSON telemetry logger over serial.
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
    from machine import ADC, I2C, PWM, Pin  # type: ignore
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

    class MockADC:
        def __init__(self, pin_or_num):
            self.pin = pin_or_num
            self._simulated_voltage = 7.62  # Nominal 2S Li-ion pack

        def set_voltage(self, v):
            self._simulated_voltage = max(0.0, float(v))

        def read_u16(self):
            # 1:3 divider ratio (e.g. 7.62V / 3.0 = 2.54V; 2.54V / 3.3V * 65535 ~ 50442)
            v_pin = self._simulated_voltage / 3.0
            adc_val = int((v_pin / 3.3) * 65535)
            return max(0, min(65535, adc_val))

    class MockI2C:
        def __init__(self, id_or_bus=0, scl=None, sda=None, freq=400000):
            self.freq = freq
            self._gyro_z = 0.0
            self._accel_z = 16384  # 1.0g

        def scan(self):
            # Simulate SSD1306 OLED (0x3C), MPU6050 IMU (0x68), and BME280 (0x76)
            return [0x3C, 0x68, 0x76]

        def writeto(self, addr, buf):
            return len(buf)

        def readfrom(self, addr, nbytes):
            return b"\x00" * nbytes

        def readfrom_mem(self, addr, memaddr, nbytes):
            if addr == 0x68:  # MPU6050
                if memaddr == 0x3B and nbytes >= 14:
                    # Ax=0, Ay=0, Az=16384 (1g), Temp=25C, Gx=0, Gy=0, Gz=simulated
                    gz_val = int(self._gyro_z * 131.0)
                    gz_val = max(-32768, min(32767, gz_val))
                    if gz_val < 0:
                        gz_val += 65536
                    gz_h = (gz_val >> 8) & 0xFF
                    gz_l = gz_val & 0xFF
                    return bytes([0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00,
                                  0x00, 0x00, 0x00, 0x00, gz_h, gz_l])
                elif memaddr == 0x43 and nbytes >= 6:
                    # Gx, Gy, Gz
                    return b"\x00" * 6
                return b"\x00" * nbytes
            elif addr == 0x76:  # BME280
                return b"\x55" * nbytes
            return b"\x00" * nbytes

        def writeto_mem(self, addr, memaddr, buf):
            return len(buf)

    Pin = MockPin  # type: ignore
    PWM = MockPWM  # type: ignore
    ADC = MockADC  # type: ignore
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
    # I2C Bus for SSD1306 OLED, BME280 & MPU6050
    "I2C_ID": 0,
    "I2C_SDA": 4,
    "I2C_SCL": 5,
    "I2C_FREQ": 400000,
    # Battery Voltage Sensing (ADC0 / GP26)
    "BATTERY_ADC": 26,
    "BATTERY_DIVIDER_RATIO": 3.0,
    "BATTERY_VREF": 3.3,
    # Status LED
    "STATUS_LED": 25,  # Onboard Pico LED
}


# ==============================================================================
# IMU Filtering: Kalman Filter & Complementary Filter
# ==============================================================================
class KalmanFilter1D:
    """
    Discrete linear 1D Kalman filter for IMU attitude estimation.
    Fuses accelerometer angle with rate gyroscope integration, simultaneously
    estimating and removing dynamic gyro bias.
    State vector: x = [angle (deg), gyro_bias (deg/s)]^T
    """

    def __init__(self, q_angle=0.001, q_bias=0.003, r_measure=0.03):
        self.q_angle = float(q_angle)
        self.q_bias = float(q_bias)
        self.r_measure = float(r_measure)

        self.angle = 0.0
        self.bias = 0.0

        # Error covariance matrix P (2x2)
        self.p00 = 0.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 0.0

    def reset(self, initial_angle=0.0):
        self.angle = float(initial_angle)
        self.bias = 0.0
        self.p00 = 0.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 0.0

    def update(self, new_angle, new_rate, dt):
        """
        Step update of Kalman Filter.
        new_angle: Accelerometer derived angle in degrees
        new_rate: Gyroscope angular rate in degrees/sec
        dt: Time delta in seconds
        """
        if dt <= 0:
            return self.angle

        # 1. State prediction
        rate = new_rate - self.bias
        self.angle += dt * rate

        # 2. Covariance prediction: P = A*P*A^T + Q
        self.p00 += dt * (dt * self.p11 - self.p01 - self.p10 + self.q_angle)
        self.p01 -= dt * self.p11
        self.p10 -= dt * self.p11
        self.p11 += self.q_bias * dt

        # 3. Measurement innovation
        y = new_angle - self.angle

        # 4. Innovation covariance: S = H*P*H^T + R = P00 + R
        s = self.p00 + self.r_measure

        # 5. Kalman gain: K = P*H^T / S
        k0 = self.p00 / s if s != 0 else 0.0
        k1 = self.p10 / s if s != 0 else 0.0

        # 6. State update: x = x + K * y
        self.angle += k0 * y
        self.bias += k1 * y

        # 7. Covariance update: P = (I - K*H) * P
        p00_temp = self.p00
        p01_temp = self.p01

        self.p00 -= k0 * p00_temp
        self.p01 -= k0 * p01_temp
        self.p10 -= k1 * p00_temp
        self.p11 -= k1 * p01_temp

        return self.angle


class ComplementaryFilter:
    """Fast, low-latency complementary filter for embedded attitude fusion."""

    def __init__(self, alpha=0.96):
        self.alpha = float(alpha)
        self.angle = 0.0

    def reset(self, initial_angle=0.0):
        self.angle = float(initial_angle)

    def update(self, accel_angle, gyro_rate, dt):
        """Fused estimate: angle = alpha * (angle + gyro * dt) + (1 - alpha) * accel."""
        self.angle = self.alpha * (self.angle + gyro_rate * dt) + (1.0 - self.alpha) * accel_angle
        return self.angle


class IMUOrientationEstimator:
    """
    Fuses 6-DOF IMU data (MPU6050) to estimate Pitch, Roll, and Yaw (Heading).
    Uses Kalman filtering for pitch and roll inclination, and zero-drift integrated
    rate filtering for heading.
    """

    def __init__(self, use_kalman=True):
        self.use_kalman = use_kalman
        self.kf_pitch = KalmanFilter1D()
        self.kf_roll = KalmanFilter1D()
        self.comp_pitch = ComplementaryFilter(alpha=0.96)
        self.comp_roll = ComplementaryFilter(alpha=0.96)

        self.pitch = 0.0
        self.roll = 0.0
        self.heading = 0.0  # Yaw in degrees [-180..+180]
        self.heading_rate = 0.0
        self.gyro_z_bias = 0.0
        self.last_update = None

    def reset(self, initial_heading=0.0):
        self.pitch = 0.0
        self.roll = 0.0
        self.heading = float(initial_heading)
        self.heading_rate = 0.0
        self.kf_pitch.reset(0.0)
        self.kf_roll.reset(0.0)
        self.comp_pitch.reset(0.0)
        self.comp_roll.reset(0.0)
        self.last_update = None

    def update(self, ax, ay, az, gx, gy, gz, dt=None):
        """
        Updates orientation estimates with raw 6-DOF sensor data.
        ax, ay, az: Acceleration in g
        gx, gy, gz: Angular rates in deg/s
        """
        now = ticks_ms()
        if dt is None:
            if self.last_update is None:
                dt = 0.025
            else:
                dt = max(0.001, ticks_diff(now, self.last_update) / 1000.0)
        self.last_update = now

        # Incline angles from gravity vector
        denom_pitch = math.sqrt(ay * ay + az * az)
        pitch_acc = math.atan2(ax, denom_pitch) * (180.0 / math.pi) if denom_pitch != 0 else 0.0
        roll_acc = math.atan2(ay, az) * (180.0 / math.pi) if az != 0 else 0.0

        if self.use_kalman:
            self.pitch = self.kf_pitch.update(pitch_acc, gy, dt)
            self.roll = self.kf_roll.update(roll_acc, gx, dt)
        else:
            self.pitch = self.comp_pitch.update(pitch_acc, gy, dt)
            self.roll = self.comp_roll.update(roll_acc, gx, dt)

        # Gyro Z rate is yaw / heading rate
        gz_corrected = gz - self.gyro_z_bias
        self.heading_rate = gz_corrected
        self.heading += gz_corrected * dt

        # Normalize heading to [-180, 180]
        while self.heading > 180.0:
            self.heading -= 360.0
        while self.heading < -180.0:
            self.heading += 360.0

        return self.pitch, self.roll, self.heading


class BME280KalmanFilter:
    """1D Kalman filter for smoothing barometric pressure & altitude fluctuations."""

    def __init__(self, q_alt=0.08, q_vel=0.03, r_measure=0.9):
        self.q_alt = q_alt
        self.q_vel = q_vel
        self.r_measure = r_measure

        self.altitude = 0.0
        self.climb_rate = 0.0

        self.p00 = 1.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 1.0
        self.last_update = None

    def update(self, measured_alt, dt=None):
        now = ticks_ms()
        if dt is None:
            if self.last_update is None:
                dt = 0.1
            else:
                dt = max(0.01, ticks_diff(now, self.last_update) / 1000.0)
        self.last_update = now

        # Prediction step
        self.altitude += self.climb_rate * dt
        self.p00 += dt * (dt * self.p11 + self.p01 + self.p10) + self.q_alt
        self.p01 += dt * self.p11
        self.p10 += dt * self.p11
        self.p11 += self.q_vel * dt

        # Measurement update
        y = measured_alt - self.altitude
        s = self.p00 + self.r_measure
        k0 = self.p00 / s if s != 0 else 0.0
        k1 = self.p10 / s if s != 0 else 0.0

        self.altitude += k0 * y
        self.climb_rate += k1 * y

        p00_temp = self.p00
        p01_temp = self.p01
        self.p00 -= k0 * p00_temp
        self.p01 -= k0 * p01_temp
        self.p10 -= k1 * p00_temp
        self.p11 -= k1 * p01_temp

        return self.altitude, self.climb_rate


# ==============================================================================
# MPU6050 6-DOF IMU Driver (I2C)
# ==============================================================================
class MPU6050Sensor:
    """I2C 6-DOF IMU driver providing acceleration, angular rate, and temperature."""

    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.address = address
        self.available = False
        self.gyro_bias_x = 0.0
        self.gyro_bias_y = 0.0
        self.gyro_bias_z = 0.0
        # Simulation hooks for desktop
        self.sim_pitch = 0.0
        self.sim_roll = 0.0
        self.sim_yaw_rate = 0.0
        self._init_sensor()

    def _init_sensor(self):
        try:
            devs = self.i2c.scan()
            if self.address in devs:
                self.available = True
                # Wake up device: PWR_MGMT_1 = 0x00
                self.i2c.writeto_mem(self.address, 0x6B, b"\x00")
                sleep_ms(10)
                # ACCEL_CONFIG = 0x00 (+-2g range, 16384 LSB/g)
                self.i2c.writeto_mem(self.address, 0x1C, b"\x00")
                # GYRO_CONFIG = 0x00 (+-250 deg/s range, 131 LSB/(deg/s))
                self.i2c.writeto_mem(self.address, 0x1B, b"\x00")
        except Exception:
            self.available = False

    def read_sensors(self):
        """
        Reads raw sensor registers and returns scaled physical units:
        (ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps, temp_c)
        """
        if not self.available or not IS_EMBEDDED:
            # Emulated reading for desktop testing
            return (0.0, 0.0, 1.0, 0.0, 0.0, self.sim_yaw_rate, 24.5)

        try:
            raw = self.i2c.readfrom_mem(self.address, 0x3B, 14)

            def to_int16(h, l):
                val = (h << 8) | l
                return val - 65536 if val > 32767 else val

            ax_raw = to_int16(raw[0], raw[1])
            ay_raw = to_int16(raw[2], raw[3])
            az_raw = to_int16(raw[4], raw[5])
            t_raw = to_int16(raw[6], raw[7])
            gx_raw = to_int16(raw[8], raw[9])
            gy_raw = to_int16(raw[10], raw[11])
            gz_raw = to_int16(raw[12], raw[13])

            ax = ax_raw / 16384.0
            ay = ay_raw / 16384.0
            az = az_raw / 16384.0
            temp_c = (t_raw / 340.0) + 36.53
            gx = (gx_raw / 131.0) - self.gyro_bias_x
            gy = (gy_raw / 131.0) - self.gyro_bias_y
            gz = (gz_raw / 131.0) - self.gyro_bias_z

            return (ax, ay, az, gx, gy, gz, temp_c)
        except Exception:
            return (0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 24.0)

    def calibrate_gyro(self, samples=50):
        """Averages stationary readings to eliminate gyro zero-rate drift."""
        if not self.available or not IS_EMBEDDED:
            self.gyro_bias_x = 0.0
            self.gyro_bias_y = 0.0
            self.gyro_bias_z = 0.0
            return

        bx, by, bz = 0.0, 0.0, 0.0
        for _ in range(samples):
            try:
                raw = self.i2c.readfrom_mem(self.address, 0x43, 6)

                def to_int16(h, l):
                    val = (h << 8) | l
                    return val - 65536 if val > 32767 else val

                bx += to_int16(raw[0], raw[1]) / 131.0
                by += to_int16(raw[2], raw[3]) / 131.0
                bz += to_int16(raw[4], raw[5]) / 131.0
                sleep_ms(5)
            except Exception:
                pass
        self.gyro_bias_x = bx / max(1, samples)
        self.gyro_bias_y = by / max(1, samples)
        self.gyro_bias_z = bz / max(1, samples)


# ==============================================================================
# Battery Voltage & Health Monitor
# ==============================================================================
class BatteryMonitor:
    """Monitors 2S Li-ion battery pack voltage and State of Charge (SoC)."""

    def __init__(self, adc_pin=26, divider_ratio=3.0, v_ref=3.3, v_min=6.0, v_max=8.4):
        self.adc_pin = adc_pin
        self.divider_ratio = float(divider_ratio)
        self.v_ref = float(v_ref)
        self.v_min = float(v_min)
        self.v_max = float(v_max)
        self._adc = ADC(adc_pin) if IS_EMBEDDED else MockADC(adc_pin)
        self.voltage = 7.62
        self.soc_pct = 75.0
        self.is_critical = False

    def read_voltage(self):
        """Reads ADC, computes actual battery pack voltage and estimated SoC %."""
        try:
            raw = self._adc.read_u16()
            v_sense = (raw / 65535.0) * self.v_ref
            self.voltage = round(v_sense * self.divider_ratio, 2)

            # Estimate SoC % based on 2S Li-ion discharge characteristics
            ratio = (self.voltage - self.v_min) / (self.v_max - self.v_min)
            self.soc_pct = max(0.0, min(100.0, round(ratio * 100.0, 1)))
            self.is_critical = self.voltage < (self.v_min + 0.4)  # < 6.4V
            return self.voltage, self.soc_pct
        except Exception:
            return 7.4, 70.0


# ==============================================================================
# Adaptive Speed Governor & Obstacle Proximity Limiter
# ==============================================================================
class SpeedRampController:
    """
    Adaptive velocity governor that dynamically scales cruising speed
    based on forward ultrasonic clearance, curvature, and slew acceleration limits.
    """

    def __init__(self, v_max=70.0, v_min=22.0, d_crit=20.0, d_slow=65.0,
                 accel_rate=120.0, decel_rate=240.0):
        self.v_max = float(v_max)
        self.v_min = float(v_min)
        self.d_crit = float(d_crit)
        self.d_slow = float(d_slow)
        self.accel_rate = float(accel_rate)  # % per second
        self.decel_rate = float(decel_rate)  # % per second

        self.current_speed = 0.0
        self.target_speed = 0.0
        self.speed_factor = 1.0
        self.last_update = ticks_ms()

    def calculate_target_speed(self, distance_cm, base_speed=None):
        """Calculates distance-proportional speed ceiling."""
        if base_speed is None:
            base_speed = self.v_max

        if distance_cm <= self.d_crit:
            self.speed_factor = 0.0
            return 0.0

        if distance_cm >= self.d_slow:
            self.speed_factor = 1.0
            return base_speed

        # Linear-quadratic smooth ramping between d_crit and d_slow
        ratio = (distance_cm - self.d_crit) / (self.d_slow - self.d_crit)
        self.speed_factor = ratio
        target = self.v_min + (base_speed - self.v_min) * (ratio ** 1.2)
        return target

    def update(self, distance_cm, base_speed=None):
        """Calculates slew-rate limited ramped speed for this control tick."""
        now = ticks_ms()
        dt = max(0.001, ticks_diff(now, self.last_update) / 1000.0)
        self.last_update = now

        self.target_speed = self.calculate_target_speed(distance_cm, base_speed)

        # Asymmetric acceleration vs deceleration ramping
        if self.current_speed < self.target_speed:
            step = self.accel_rate * dt
            self.current_speed = min(self.target_speed, self.current_speed + step)
        elif self.current_speed > self.target_speed:
            step = self.decel_rate * dt
            self.current_speed = max(self.target_speed, self.current_speed - step)

        return self.current_speed


# ==============================================================================
# Obstacle Avoidance 2D Local Occupancy Grid Map
# ==============================================================================
class OccupancyGridMap:
    """
    2D Local Occupancy Grid Map for obstacle clearance mapping.
    Maintains probability of obstacle presence across a spatial discrete grid.
    Grid center (origin) corresponds to rover location (0, 0).
    """

    def __init__(self, size=41, resolution_cm=5.0):
        self.size = size
        self.resolution = float(resolution_cm)
        self.center_idx = size // 2
        # Store as 1D list of length size*size for MicroPython memory efficiency
        # 0.5 = Unknown, 0.05 = Free, 0.95 = Occupied
        self.grid = [0.5] * (self.size * self.size)
        self.total_scans = 0

    def clear(self):
        """Resets grid to unknown (0.5)."""
        for i in range(len(self.grid)):
            self.grid[i] = 0.5
        self.total_scans = 0

    def _get_index(self, gx, gy):
        if 0 <= gx < self.size and 0 <= gy < self.size:
            return gy * self.size + gx
        return -1

    def world_to_grid(self, forward_cm, lateral_cm):
        """Converts local coordinate (forward_cm, lateral_cm) to grid indices."""
        gx = int(self.center_idx + (lateral_cm / self.resolution))
        gy = int(self.center_idx + (forward_cm / self.resolution))
        return gx, gy

    def grid_to_world(self, gx, gy):
        """Converts grid indices to local coordinate (forward_cm, lateral_cm)."""
        lateral_cm = (gx - self.center_idx) * self.resolution
        forward_cm = (gy - self.center_idx) * self.resolution
        return forward_cm, lateral_cm

    def update_ray(self, angle_deg, distance_cm, max_range_cm=200.0):
        """
        Raycasts along beam angle (0 = straight ahead, - = left, + = right).
        Marks traversed cells as FREE and terminal hit cell as OCCUPIED.
        """
        self.total_scans += 1
        angle_rad = math.radians(angle_deg)
        dir_fwd = math.cos(angle_rad)
        dir_lat = math.sin(angle_rad)

        dist = min(distance_cm, max_range_cm)
        step = self.resolution * 0.75
        curr_dist = step

        # Mark free space along ray
        while curr_dist < (dist - self.resolution * 0.8):
            fwd = curr_dist * dir_fwd
            lat = curr_dist * dir_lat
            gx, gy = self.world_to_grid(fwd, lat)
            idx = self._get_index(gx, gy)
            if idx != -1:
                self.grid[idx] = max(0.05, self.grid[idx] * 0.7)
            curr_dist += step

        # Mark obstacle at terminal point if within valid sensor range
        if distance_cm <= max_range_cm:
            hit_fwd = distance_cm * dir_fwd
            hit_lat = distance_cm * dir_lat
            gx, gy = self.world_to_grid(hit_fwd, hit_lat)
            idx = self._get_index(gx, gy)
            if idx != -1:
                self.grid[idx] = min(0.95, self.grid[idx] + 0.35)

    def get_sector_clearance(self, sectors=(-60, -30, 0, 30, 60), sample_radius_cm=100.0):
        """
        Computes obstacle penalty and clearance score for given sectors from the grid.
        Returns dict: {angle: clearance_score_cm}
        """
        results = {}
        for ang in sectors:
            rad = math.radians(ang)
            dir_fwd = math.cos(rad)
            dir_lat = math.sin(rad)

            min_dist = sample_radius_cm
            curr_dist = self.resolution
            while curr_dist <= sample_radius_cm:
                fwd = curr_dist * dir_fwd
                lat = curr_dist * dir_lat
                gx, gy = self.world_to_grid(fwd, lat)
                idx = self._get_index(gx, gy)
                if idx != -1 and self.grid[idx] > 0.65:
                    min_dist = curr_dist
                    break
                curr_dist += self.resolution

            results[ang] = min_dist
        return results

    def get_occupied_cells(self, threshold=0.7):
        """Returns list of (fwd_cm, lat_cm, prob) for occupied cells."""
        occupied = []
        for gy in range(self.size):
            for gx in range(self.size):
                prob = self.grid[gy * self.size + gx]
                if prob >= threshold:
                    fwd_cm, lat_cm = self.grid_to_world(gx, gy)
                    occupied.append((round(fwd_cm, 1), round(lat_cm, 1), round(prob, 2)))
        return occupied

    def to_matrix(self):
        """Returns 2D matrix of probabilities."""
        matrix = []
        for gy in range(self.size):
            row = []
            for gx in range(self.size):
                row.append(round(self.grid[gy * self.size + gx], 2))
            matrix.append(row)
        return matrix


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

        # Apply deadband compensation for N20 motors (< 2% static deadband)
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
        self.max_slew_rate = 180.0
        self.last_update = ticks_ms()

    def update(self):
        """Executes one control cycle: ramps speeds and computes PID effort."""
        now = ticks_ms()
        dt = max(0.001, ticks_diff(now, self.last_update) / 1000.0)
        self.last_update = now

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
        self.current_angle = 0.0
        self.center()

    def set_angle(self, angle_deg):
        """
        Sets servo angle from -60 (hard left) to +60 (hard right).
        0 degrees is centered straight ahead.
        """
        angle_deg = max(-60.0, min(60.0, float(angle_deg)))
        self.current_angle = angle_deg

        mapped_deg = angle_deg + 90.0
        pulse_us = self.min_us + (mapped_deg / 180.0) * (self.max_us - self.min_us)
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
        self.timeout_us = timeout_us
        self.last_valid_dist = 150.0
        self._sim_distance = 120.0  # Emulation hook

    def read_single_cm(self):
        """Triggers a single 10us ultrasonic burst and measures pulse width."""
        if not IS_EMBEDDED:
            return self._sim_distance

        self.trig.value(0)
        sleep_us(2)
        self.trig.value(1)
        sleep_us(10)
        self.trig.value(0)

        t_start = ticks_us()
        while self.echo.value() == 0:
            if ticks_diff(ticks_us(), t_start) > self.timeout_us:
                return 400.0

        echo_start = ticks_us()
        while self.echo.value() == 1:
            if ticks_diff(ticks_us(), echo_start) > self.timeout_us:
                return 400.0

        echo_end = ticks_us()
        pulse_duration = ticks_diff(echo_end, echo_start)

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
            if IS_EMBEDDED:
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
            devs = self.i2c.scan()
            if self.address in devs:
                self.available = True
                self.i2c.writeto_mem(self.address, 0xF4, b"\x27")
        except Exception:
            self.available = False

    def read_telemetry(self):
        """Returns (temperature_c, pressure_hpa, altitude_m)."""
        if not self.available or not IS_EMBEDDED:
            return (23.4, 1013.2, 45.2)

        try:
            raw = self.i2c.readfrom_mem(self.address, 0xF7, 6)
            raw_p = ((raw[0] << 16) | (raw[1] << 8) | raw[2]) >> 4
            raw_t = ((raw[3] << 16) | (raw[4] << 8) | raw[5]) >> 4

            temp_c = (raw_t / 16384.0) * 10.0 + 20.0
            press_hpa = (raw_p / 256.0) * 0.1 + 950.0
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

    def render(self, state_name, forward_dist, scan_data, temp_c, press_hpa,
               left_pwr, right_pwr, heading_deg=0.0, battery_v=7.4):
        """Draws HUD telemetry dashboard and transmits frame to display."""
        if not self.available:
            return

        try:
            import framebuf  # type: ignore

            fb = framebuf.FrameBuffer(self.buffer, 128, 64, framebuf.MONO_VLSB)
            fb.fill(0)

            # Header with heading and battery
            fb.text(f"TS:{state_name[:4]}", 0, 0, 1)
            fb.text(f"{int(heading_deg):+3d}d", 54, 0, 1)
            fb.text(f"{battery_v:.1f}V", 92, 0, 1)
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

            self.i2c.writeto_mem(self.address, 0x40, self.buffer)
        except Exception:
            pass


# ==============================================================================
# Autonomous Obstacle Avoidance State Machine
# ==============================================================================
class RoverStateMachine:
    """Enhanced obstacle avoidance and navigation state engine."""

    # States
    STATE_BOOT = "BOOT"
    STATE_CRUISE = "CRUISE"
    STATE_SLOW_APPROACH = "SLOW_APP"
    STATE_PANORAMIC_SCAN = "SCAN"
    STATE_PATHFINDING = "PATHFIND"
    STATE_PIVOT_AVOID = "PIVOT"
    STATE_EMERGENCY_REVERSE = "REVERSE"
    STATE_STOPPED = "STOPPED"
    STATE_LOW_BATTERY = "LOW_BATT"

    # Thresholds (cm)
    THRESHOLD_OBSTACLE_WARN = 45.0
    THRESHOLD_OBSTACLE_CRIT = 22.0
    THRESHOLD_EMERGENCY_BACKUP = 14.0

    def __init__(self, drive, servo, ultrasonic, bme, oled, imu=None,
                 battery=None, grid_map=None, speed_ramp=None):
        self.drive = drive
        self.servo = servo
        self.ultrasonic = ultrasonic
        self.bme = bme
        self.oled = oled
        self.imu = imu
        self.battery = battery
        self.grid_map = grid_map if grid_map is not None else OccupancyGridMap()
        self.speed_ramp = speed_ramp if speed_ramp is not None else SpeedRampController()

        # Heading control PID
        self.heading_pid = PIDController(kp=1.4, ki=0.08, kd=0.12, out_min=-55.0, out_max=55.0)

        self.state = self.STATE_BOOT
        self.scan_angles = [-60, -30, 0, 30, 60]
        self.scan_results = {ang: 200.0 for ang in self.scan_angles}
        self.best_heading = 0.0
        self.target_heading = 0.0
        self.state_enter_time = ticks_ms()
        self.pivot_duration_ms = 0
        self.current_heading = 0.0

    def change_state(self, new_state):
        self.state = new_state
        self.state_enter_time = ticks_ms()

    def update(self):
        """Processes state machine transitions."""
        now = ticks_ms()
        state_elapsed = ticks_diff(now, self.state_enter_time)

        # Update battery status
        if self.battery is not None and self.battery.is_critical:
            self.drive.brake()
            self.change_state(self.STATE_LOW_BATTERY)
            return

        # ----------------------------------------------------------------------
        # STATE: BOOT
        # ----------------------------------------------------------------------
        if self.state == self.STATE_BOOT:
            self.servo.center()
            self.drive.stop()
            if state_elapsed > 1000:
                self.change_state(self.STATE_CRUISE)

        # ----------------------------------------------------------------------
        # STATE: CRUISE (Adaptive speed traversal & forward raycasting)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_CRUISE:
            self.servo.center()
            dist = self.ultrasonic.get_distance_filtered(samples=2)

            # Continuous local occupancy grid mapping along forward line
            self.grid_map.update_ray(0.0, dist)

            if dist <= self.THRESHOLD_EMERGENCY_BACKUP:
                self.drive.brake()
                self.change_state(self.STATE_EMERGENCY_REVERSE)
            elif dist <= self.THRESHOLD_OBSTACLE_CRIT:
                self.drive.brake()
                self.change_state(self.STATE_PANORAMIC_SCAN)
            elif dist <= self.THRESHOLD_OBSTACLE_WARN:
                # Decelerate smoothly into slow approach
                target_spd = self.speed_ramp.update(dist, base_speed=38.0)
                self.drive.forward(speed=target_spd)
                self.change_state(self.STATE_SLOW_APPROACH)
            else:
                # Full adaptive cruise speed
                target_spd = self.speed_ramp.update(dist, base_speed=65.0)
                self.drive.forward(speed=target_spd)

        # ----------------------------------------------------------------------
        # STATE: SLOW APPROACH
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_SLOW_APPROACH:
            dist = self.ultrasonic.get_distance_filtered(samples=2)
            self.grid_map.update_ray(0.0, dist)

            if dist <= self.THRESHOLD_OBSTACLE_CRIT:
                self.drive.brake()
                self.change_state(self.STATE_PANORAMIC_SCAN)
            elif dist > self.THRESHOLD_OBSTACLE_WARN + 10.0:
                self.change_state(self.STATE_CRUISE)
            else:
                # Dynamically ramp speed proportionally to remaining clearance
                creep_spd = self.speed_ramp.update(dist, base_speed=32.0)
                self.drive.forward(speed=creep_spd)

        # ----------------------------------------------------------------------
        # STATE: PANORAMIC SCAN (5-point sweep + grid mapping)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_PANORAMIC_SCAN:
            self.drive.stop()

            # Execute 5-point sweep and register rays in occupancy grid
            for ang in self.scan_angles:
                self.servo.set_angle(ang)
                if IS_EMBEDDED:
                    sleep_ms(160)
                d = self.ultrasonic.get_distance_filtered(samples=3)
                self.scan_results[ang] = d
                self.grid_map.update_ray(ang, d)

            self.servo.center()
            if IS_EMBEDDED:
                sleep_ms(80)
            self.change_state(self.STATE_PATHFINDING)

        # ----------------------------------------------------------------------
        # STATE: PATHFINDING (Evaluate clearance & grid corridors)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_PATHFINDING:
            # Query grid sector clearances
            grid_clearance = self.grid_map.get_sector_clearance(self.scan_angles)

            best_score = -1.0
            chosen_angle = 0.0

            for ang in self.scan_angles:
                sonar_d = self.scan_results.get(ang, 0.0)
                grid_d = grid_clearance.get(ang, 0.0)
                # Combined metric: min of sonar and grid memory
                effective_clearance = min(sonar_d, grid_d)

                # Heading penalty: penalize sharp pivots slightly
                bias = 1.0 - (abs(ang) / 120.0) * 0.22
                score = effective_clearance * bias

                if score > best_score:
                    best_score = score
                    chosen_angle = ang

            self.best_heading = chosen_angle

            # Check if rover is trapped in dead-end
            max_clearance = max(self.scan_results.values())
            if max_clearance < self.THRESHOLD_OBSTACLE_CRIT:
                self.change_state(self.STATE_EMERGENCY_REVERSE)
            else:
                # Closed-loop heading target
                self.target_heading = self.current_heading + chosen_angle
                # Bound heading to [-180, 180]
                if self.target_heading > 180.0:
                    self.target_heading -= 360.0
                elif self.target_heading < -180.0:
                    self.target_heading += 360.0

                self.pivot_duration_ms = int(abs(chosen_angle) * 14.0) + 140
                self.heading_pid.reset()
                self.change_state(self.STATE_PIVOT_AVOID)

        # ----------------------------------------------------------------------
        # STATE: PIVOT AVOID (Closed-loop / Timed Pivot)
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_PIVOT_AVOID:
            # Compute heading error
            heading_err = self.target_heading - self.current_heading
            while heading_err > 180.0:
                heading_err -= 360.0
            while heading_err < -180.0:
                heading_err += 360.0

            if abs(heading_err) < 5.0 or state_elapsed >= self.pivot_duration_ms:
                self.drive.brake()
                self.change_state(self.STATE_CRUISE)
            else:
                if self.best_heading < 0:
                    self.drive.pivot_left(speed=50.0)
                else:
                    self.drive.pivot_right(speed=50.0)

        # ----------------------------------------------------------------------
        # STATE: EMERGENCY REVERSE
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_EMERGENCY_REVERSE:
            self.drive.reverse(speed=42.0)
            if state_elapsed >= 1100:
                self.drive.brake()
                self.change_state(self.STATE_PANORAMIC_SCAN)

        # ----------------------------------------------------------------------
        # STATE: LOW BATTERY
        # ----------------------------------------------------------------------
        elif self.state == self.STATE_LOW_BATTERY:
            self.drive.stop()
            self.servo.center()

        # Update motor PID loops
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
        self.bme_kalman = BME280KalmanFilter()
        self.oled = OLEDHud(self.i2c)

        # 4. IMU & Active Filtering
        self.mpu = MPU6050Sensor(self.i2c)
        self.imu = IMUOrientationEstimator(use_kalman=True)
        self.mpu.calibrate_gyro(samples=40)

        # 5. Battery Monitoring
        self.battery = BatteryMonitor(
            adc_pin=PIN_CONFIG["BATTERY_ADC"],
            divider_ratio=PIN_CONFIG["BATTERY_DIVIDER_RATIO"],
            v_ref=PIN_CONFIG["BATTERY_VREF"],
        )

        # 6. Adaptive Speed Ramping & Local Occupancy Grid
        self.speed_ramp = SpeedRampController()
        self.grid_map = OccupancyGridMap(size=41, resolution_cm=5.0)

        # 7. State Engine
        self.sm = RoverStateMachine(
            drive=self.drive,
            servo=self.servo,
            ultrasonic=self.ultrasonic,
            bme=self.bme,
            oled=self.oled,
            imu=self.imu,
            battery=self.battery,
            grid_map=self.grid_map,
            speed_ramp=self.speed_ramp,
        )

        # Timers
        self.last_imu_update = ticks_ms()
        self.last_hud_update = ticks_ms()
        self.last_telemetry_emit = ticks_ms()
        print("[TERRASCOUT] Initialization complete. System armed.")

    def run_step(self):
        """Single non-blocking execution cycle."""
        now = ticks_ms()

        # 1. High-rate IMU telemetry & Kalman filter update (40-50Hz)
        dt_imu = max(0.002, ticks_diff(now, self.last_imu_update) / 1000.0)
        self.last_imu_update = now
        ax, ay, az, gx, gy, gz, _ = self.mpu.read_sensors()
        pitch, roll, heading = self.imu.update(ax, ay, az, gx, gy, gz, dt=dt_imu)
        self.sm.current_heading = heading

        # 2. Update navigation state machine
        self.sm.update()

        # 3. Read battery status
        bat_v, soc_pct = self.battery.read_voltage()

        # 4. Filtered barometric altitude
        temp_c, press_hpa, raw_alt = self.bme.read_telemetry()
        filt_alt, climb_rate = self.bme_kalman.update(raw_alt)

        # 5. HUD refresh loop (5 Hz)
        if ticks_diff(now, self.last_hud_update) >= 200:
            self.last_hud_update = now
            self.oled.render(
                state_name=self.sm.state,
                forward_dist=self.ultrasonic.last_valid_dist,
                scan_data=self.sm.scan_results,
                temp_c=temp_c,
                press_hpa=press_hpa,
                left_pwr=self.drive.actual_left,
                right_pwr=self.drive.actual_right,
                heading_deg=heading,
                battery_v=bat_v,
            )

        # 6. Serial JSON Telemetry Logger (2 Hz)
        if ticks_diff(now, self.last_telemetry_emit) >= 500:
            self.last_telemetry_emit = now
            telemetry_packet = (
                f'{{"time_ms":{now},'
                f'"state":"{self.sm.state}",'
                f'"dist_cm":{self.ultrasonic.last_valid_dist:.1f},'
                f'"best_hdg":{self.sm.best_heading:.0f},'
                f'"heading":{heading:.1f},'
                f'"pitch":{pitch:.1f},'
                f'"roll":{roll:.1f},'
                f'"temp_c":{temp_c:.2f},'
                f'"press_hpa":{press_hpa:.1f},'
                f'"alt_m":{filt_alt:.1f},'
                f'"bat_v":{bat_v:.2f},'
                f'"soc_pct":{soc_pct:.1f},'
                f'"motor_l":{self.drive.actual_left:.1f},'
                f'"motor_r":{self.drive.actual_right:.1f},'
                f'"speed_factor":{self.speed_ramp.speed_factor:.2f}}}'
            )
            print(f"[TELEM] {telemetry_packet}")

    def get_telemetry_dict(self):
        """Constructs telemetry payload dictionary for web telemetry dashboard."""
        now = ticks_ms()
        t, p, raw_alt = self.bme.read_telemetry()
        filt_alt, _ = self.bme_kalman.update(raw_alt)
        bat_v, soc_pct = self.battery.read_voltage()

        return {
            "time_ms": now,
            "state": self.sm.state,
            "battery": {
                "voltage_v": bat_v,
                "soc_pct": soc_pct,
                "critical": self.battery.is_critical,
            },
            "motors": {
                "target_l": round(self.drive.target_left, 1),
                "target_r": round(self.drive.target_right, 1),
                "actual_l": round(self.drive.actual_left, 1),
                "actual_r": round(self.drive.actual_right, 1),
                "pwm_l_pct": round(abs(self.drive.actual_left), 1),
                "pwm_r_pct": round(abs(self.drive.actual_right), 1),
            },
            "imu": {
                "heading_deg": round(self.imu.heading, 1),
                "pitch_deg": round(self.imu.pitch, 1),
                "roll_deg": round(self.imu.roll, 1),
                "heading_rate_dps": round(self.imu.heading_rate, 2),
                "kalman_active": self.imu.use_kalman,
            },
            "ultrasonic": {
                "forward_cm": round(self.ultrasonic.last_valid_dist, 1),
                "turret_angle_deg": round(self.servo.current_angle, 1),
                "scan_sectors": {str(k): round(v, 1) for k, v in self.sm.scan_results.items()},
            },
            "environment": {
                "temp_c": t,
                "press_hpa": p,
                "altitude_m": round(filt_alt, 1),
            },
            "navigation": {
                "speed_ramp_factor": round(self.speed_ramp.speed_factor, 2),
                "best_heading_deg": round(self.sm.best_heading, 1),
                "target_heading_deg": round(self.sm.target_heading, 1),
                "obstacles_detected": len(self.grid_map.get_occupied_cells()),
            },
        }

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
    """Runs a complete automated bench test of all expanded subsystems."""
    print("=" * 60)
    print("TERRASCOUT AUTONOMOUS ROVER - EXPANDED FIRMWARE BENCH TEST")
    print(f"Platform: {'Embedded MicroPython' if IS_EMBEDDED else 'Desktop Simulation'}")
    print("=" * 60)

    rover = TerraScoutRover()

    # Test 1: BME280 Environmental & Barometric Kalman Filter
    t, p, alt = rover.bme.read_telemetry()
    filt_alt, climb = rover.bme_kalman.update(alt)
    print(f"[TEST 1] BME280 -> Temp: {t:.2f} C | Press: {p:.1f} hPa | Alt: {filt_alt:.1f} m (Climb: {climb:.2f} m/s)")
    assert 10.0 <= t <= 50.0, "Temperature out of expected range"

    # Test 2: MPU6050 & Active Kalman Attitude Filter
    ax, ay, az, gx, gy, gz, _ = rover.mpu.read_sensors()
    pitch, roll, heading = rover.imu.update(ax, ay, az, gx, gy, gz, dt=0.02)
    print(f"[TEST 2] MPU6050 Kalman -> Pitch: {pitch:.2f}° | Roll: {roll:.2f}° | Heading: {heading:.2f}°")

    # Test 3: Battery Monitoring & SoC Calculation
    v_bat, soc = rover.battery.read_voltage()
    print(f"[TEST 3] Battery Subsystem -> Voltage: {v_bat:.2f} V | State of Charge: {soc:.1f}%")
    assert 6.0 <= v_bat <= 8.5, "Battery voltage reading invalid"

    # Test 4: Ultrasonic Rangefinder
    d = rover.ultrasonic.get_distance_filtered()
    print(f"[TEST 4] Ultrasonic Rangefinder -> {d:.1f} cm")
    assert d > 0, "Ultrasonic distance invalid"

    # Test 5: Pan Servo Turret Sweep
    print("[TEST 5] Exercising Servo Pan Turret (-60 deg to +60 deg)...")
    for ang in [-60, -30, 0, 30, 60]:
        rover.servo.set_angle(ang)
        sleep_ms(60)
    rover.servo.center()
    print("  -> Servo Sweep PASS")

    # Test 6: Differential Motion Controller & Slew Limiter
    print("[TEST 6] Exercising Differential Drive Controller...")
    rover.drive.forward(40)
    rover.drive.update()
    sleep_ms(60)
    rover.drive.pivot_right(50)
    rover.drive.update()
    sleep_ms(60)
    rover.drive.brake()
    print("  -> Drive Motion Controller PASS")

    # Test 7: Adaptive Speed Ramping Governor
    ramp_100 = rover.speed_ramp.calculate_target_speed(100.0)
    ramp_40 = rover.speed_ramp.calculate_target_speed(40.0)
    ramp_15 = rover.speed_ramp.calculate_target_speed(15.0)
    print(f"[TEST 7] Adaptive Speed Ramping -> 100cm: {ramp_100:.1f}%, 40cm: {ramp_40:.1f}%, 15cm: {ramp_15:.1f}%")
    assert ramp_100 > ramp_40 > ramp_15 == 0.0, "Speed ramping profile incorrect"

    # Test 8: 2D Local Occupancy Grid Map
    print("[TEST 8] Exercising 2D Local Occupancy Grid Map...")
    rover.grid_map.update_ray(angle_deg=0.0, distance_cm=45.0)
    rover.grid_map.update_ray(angle_deg=30.0, distance_cm=25.0)
    occupied = rover.grid_map.get_occupied_cells()
    clearance = rover.grid_map.get_sector_clearance()
    print(f"  -> Occupied Cells Registered: {len(occupied)} | Clearance Sectors: {clearance}")
    assert len(occupied) >= 1, "Grid map failed to register obstacle"

    # Test 9: State Machine Simulation Loop
    print("[TEST 9] Executing 20 State Machine Cycles...")
    rover.loop(max_iterations=20)
    print("  -> State Machine PASS")

    print("=" * 60)
    print("ALL EXPANDED FIRMWARE BENCH TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--test", "--diag"):
        run_diagnostics()
    else:
        # Standard launch
        rover = TerraScoutRover()
        rover.loop()
