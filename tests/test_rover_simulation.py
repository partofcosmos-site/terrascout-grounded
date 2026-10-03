"""
================================================================================
TerraScout Grounded Telemetry Rover - Simulation & Unit Test Suite
Project: TerraScout Grounded (Autonomous Telemetry Rover)
Target: Comprehensive Closed-Loop Rover Physics, State Machine & Telemetry Tests
License: MIT / CERN-OHL-P v2
================================================================================

Test Suite Coverage:
  1. IMU Active Kalman Filtering & Complementary Fusion:
     - Noise rejection and drift elimination against ground truth kinematics.
  2. PID Speed & Heading Step Response Curves:
     - Velocity step response, rise time, overshoot, and steady-state error.
     - Closed-loop heading hold and pivot convergence.
  3. Adaptive Speed Ramping:
     - Distance-proportional deceleration profile and jerk limiting.
  4. 2D Local Occupancy Grid Map:
     - Raycasting Bayesian cell probability updates and clearance query accuracy.
  5. Virtual Obstacle Arena Closed-Loop Navigation:
     - Continuous physics simulation with collision detection.
     - Traversal across multi-obstacle arena with zero collisions.
  6. Web Telemetry Server REST & SSE Endpoints:
     - Validates HTTP response status, JSON schemas, and command dispatch.
  7. Telemetry Benchmark Asset Generator:
     - Renders multi-panel telemetry and physics performance graphs to assets/telemetry_benchmark.png.
================================================================================
"""

import math
import json
import os
import random
import sys
import time
import unittest
from urllib.request import Request, urlopen

# Set up project import paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.main import (
    BME280KalmanFilter,
    BatteryMonitor,
    ComplementaryFilter,
    DifferentialDrive,
    IMUOrientationEstimator,
    KalmanFilter1D,
    OccupancyGridMap,
    PIDController,
    SpeedRampController,
    TerraScoutRover,
    set_simulated_time_ms,
)
from src.telemetry_server import TelemetryServer, STORE


# ==============================================================================
# 2D Virtual Obstacle Arena Geometry & Raycaster
# ==============================================================================
class VirtualArena:
    """
    Continuous 2D Obstacle Arena with geometric boundaries, rectangular obstacles,
    cylindrical pillars, and high-performance raycasting for sonar emulation.
    """

    def __init__(self, width_cm=350.0, height_cm=350.0):
        self.width = float(width_cm)
        self.height = float(height_cm)

        # Boundary perimeter line segments: ((x1, y1), (x2, y2))
        self.walls = [
            ((0.0, 0.0), (self.width, 0.0)),
            ((self.width, 0.0), (self.width, self.height)),
            ((self.width, self.height), (0.0, self.height)),
            ((0.0, self.height), (0.0, 0.0)),
        ]

        # Rectangular obstacles: (min_x, min_y, max_x, max_y)
        self.boxes = [
            (80.0, 75.0, 140.0, 135.0),    # Obstacle A: South-West box
            (210.0, 210.0, 275.0, 275.0),  # Obstacle B: North-East box
            (70.0, 230.0, 130.0, 280.0),   # Obstacle C: North-West box
        ]

        # Cylindrical obstacles: (center_x, center_y, radius)
        self.cylinders = [
            (175.0, 175.0, 26.0),  # Central Pillar
        ]

        # Decompose boxes into boundary line segments for raycasting
        self.segments = list(self.walls)
        for (bx1, by1, bx2, by2) in self.boxes:
            self.segments.append(((bx1, by1), (bx2, by1)))
            self.segments.append(((bx2, by1), (bx2, by2)))
            self.segments.append(((bx2, by2), (bx1, by2)))
            self.segments.append(((bx1, by2), (bx1, by1)))

    def cast_ray(self, origin_x, origin_y, angle_rad, max_range_cm=200.0):
        """
        Calculates exact Euclidean distance to closest obstacle or wall along ray.
        """
        dx = math.cos(angle_rad)
        dy = math.sin(angle_rad)
        min_dist = max_range_cm

        # 1. Test line segments
        for (p1, p2) in self.segments:
            x1, y1 = p1
            x2, y2 = p2
            v1_x = origin_x - x1
            v1_y = origin_y - y1
            v2_x = x2 - x1
            v2_y = y2 - y1
            cross = v2_x * dy - v2_y * dx
            if abs(cross) < 1e-6:
                continue

            t1 = (v1_x * v2_y - v1_y * v2_x) / cross
            t2 = (dy * v1_x - dx * v1_y) / cross
            if t1 >= 0.0 and 0.0 <= t2 <= 1.0:
                if t1 < min_dist:
                    min_dist = t1

        # 2. Test cylinders (ray-circle intersection)
        for (cx, cy, r) in self.cylinders:
            fx = origin_x - cx
            fy = origin_y - cy
            a = dx * dx + dy * dy
            b = 2.0 * (fx * dx + fy * dy)
            c = fx * fx + fy * fy - r * r
            disc = b * b - 4 * a * c
            if disc >= 0:
                sqrt_disc = math.sqrt(disc)
                t_hit = (-b - sqrt_disc) / (2 * a)
                if t_hit > 0 and t_hit < min_dist:
                    min_dist = t_hit

        # Add small simulated ultrasonic Gaussian measurement jitter (+-0.5cm)
        jitter = random.gauss(0.0, 0.4)
        return max(2.0, min(max_range_cm, min_dist + jitter))

    def check_collision(self, x, y, rover_radius_cm=8.5):
        """
        Returns (is_collision, min_clearance_cm) for a circular rover footprint.
        """
        # Check boundary walls
        if (x - rover_radius_cm <= 0.0 or x + rover_radius_cm >= self.width or
            y - rover_radius_cm <= 0.0 or y + rover_radius_cm >= self.height):
            return True, 0.0

        min_clearance = min(x, self.width - x, y, self.height - y) - rover_radius_cm

        # Check rectangular boxes
        for (bx1, by1, bx2, by2) in self.boxes:
            closest_x = max(bx1, min(x, bx2))
            closest_y = max(by1, min(y, by2))
            dist = math.hypot(x - closest_x, y - closest_y)
            clearance = dist - rover_radius_cm
            if clearance < min_clearance:
                min_clearance = clearance
            if dist <= rover_radius_cm:
                return True, clearance

        # Check cylindrical pillars
        for (cx, cy, r) in self.cylinders:
            dist = math.hypot(x - cx, y - cy)
            clearance = dist - r - rover_radius_cm
            if clearance < min_clearance:
                min_clearance = clearance
            if dist <= (r + rover_radius_cm):
                return True, clearance

        return False, min_clearance


# ==============================================================================
# Virtual Differential Drive Kinematics & Physics Engine
# ==============================================================================
class VirtualRoverPhysics:
    """Simulates real-time differential drive dynamics, wheel slip, inertia and sensors."""

    def __init__(self, init_x=175.0, init_y=55.0, init_heading_deg=90.0):
        self.x = float(init_x)
        self.y = float(init_y)
        self.heading_rad = math.radians(init_heading_deg)

        self.track_width = 8.6   # cm
        self.wheel_radius = 2.15 # cm
        self.max_wheel_speed = 32.0 # cm/s at 100% duty

        self.v_left = 0.0
        self.v_right = 0.0
        self.actual_speed = 0.0
        self.yaw_rate_dps = 0.0

        # Virtual battery pack
        self.battery_voltage = 7.65
        self.battery_capacity_ah = 2.6
        self.internal_resistance = 0.12 # Ohms

    def step(self, duty_left, duty_right, dt=0.025):
        """Simulates motor response with inertia and differential kinematics."""
        target_vl = (duty_left / 100.0) * self.max_wheel_speed
        target_vr = (duty_right / 100.0) * self.max_wheel_speed

        # Inertial lag (tau = 0.08s)
        alpha = min(1.0, dt / 0.08)
        self.v_left += (target_vl - self.v_left) * alpha
        self.v_right += (target_vr - self.v_right) * alpha

        # Kinematic differential velocity
        linear_v = (self.v_left + self.v_right) / 2.0
        angular_w = (self.v_right - self.v_left) / self.track_width  # rad/s

        self.actual_speed = linear_v
        self.yaw_rate_dps = math.degrees(angular_w)

        # Coordinate integration
        self.heading_rad += angular_w * dt
        # Normalize to [-pi, pi]
        self.heading_rad = (self.heading_rad + math.pi) % (2 * math.pi) - math.pi

        self.x += linear_v * math.cos(self.heading_rad) * dt
        self.y += linear_v * math.sin(self.heading_rad) * dt

        # Battery discharge simulation under load
        motor_current = (abs(duty_left) + abs(duty_right)) / 100.0 * 0.42 + 0.08 # Amps
        # Voltage sag
        self.battery_voltage -= (motor_current * dt / (self.battery_capacity_ah * 3600.0)) * 1.8
        sagged_v = self.battery_voltage - (motor_current * self.internal_resistance)
        return sagged_v


# ==============================================================================
# Unit Test Cases
# ==============================================================================
class TestIMUFiltering(unittest.TestCase):
    """Unit tests verifying Kalman and Complementary IMU attitude filtering."""

    def test_kalman_filter_noise_rejection(self):
        kf = KalmanFilter1D(q_angle=0.001, q_bias=0.003, r_measure=0.04)
        true_angle = 15.0
        kf.reset(initial_angle=true_angle)
        raw_noise_errors = []
        filtered_errors = []

        # Run 250 simulation steps with noisy accelerometer and gyro bias
        gyro_bias = 1.2  # deg/s offset
        dt = 0.02
        for _ in range(250):
            measured_gyro = 0.0 + gyro_bias + random.gauss(0.0, 0.05)
            noise = random.gauss(0.0, 1.8)
            measured_accel = true_angle + noise
            est = kf.update(measured_accel, measured_gyro, dt)

            raw_noise_errors.append(abs(noise))
            filtered_errors.append(abs(est - true_angle))

        # Check that after settling, Kalman error is much smaller than raw sensor noise
        avg_raw_err = sum(raw_noise_errors[60:]) / len(raw_noise_errors[60:])
        avg_filt_err = sum(filtered_errors[60:]) / len(filtered_errors[60:])

        self.assertLess(avg_filt_err, avg_raw_err * 0.5,
                        "Kalman filter must reduce angle error by at least 50% compared to raw noise")
        self.assertAlmostEqual(kf.bias, gyro_bias, delta=0.5,
                               msg="Kalman filter must estimate gyro bias")

    def test_complementary_filter_response(self):
        comp = ComplementaryFilter(alpha=0.95)
        # Verify dynamic response
        angle = comp.update(accel_angle=20.0, gyro_rate=0.0, dt=0.02)
        self.assertGreater(angle, 0.0)
        self.assertLess(angle, 20.0)

    def test_bme280_kalman_smoothing(self):
        bme_kf = BME280KalmanFilter(q_alt=0.02, q_vel=0.01, r_measure=1.2)
        raw_alts = [45.0 + random.gauss(0.0, 1.2) for _ in range(60)]
        filtered = [bme_kf.update(a, dt=0.1)[0] for a in raw_alts]

        raw_var = sum((a - 45.0)**2 for a in raw_alts[15:]) / len(raw_alts[15:])
        filt_var = sum((f - 45.0)**2 for f in filtered[15:]) / len(filtered[15:])

        self.assertLess(filt_var, raw_var * 0.45,
                        "BME280 Kalman filter must suppress altitude variance by > 55%")


class TestPIDControllers(unittest.TestCase):
    """Unit tests verifying PID Speed and Heading step response performance."""

    def test_pid_speed_step_response(self):
        pid = PIDController(kp=1.6, ki=1.5, kd=0.06, out_min=-100, out_max=100, integral_limit=100.0)
        target_speed = 60.0
        current_speed = 0.0
        dt = 0.02
        overshoot_max = 0.0

        for _ in range(180):  # 3.6 seconds
            effort = pid.update(target_speed, current_speed, dt=dt)
            # Motor velocity response (gain = 1.0)
            current_speed += (effort - current_speed) * 0.2
            if current_speed > target_speed:
                overshoot = (current_speed - target_speed) / target_speed
                if overshoot > overshoot_max:
                    overshoot_max = overshoot

        self.assertLess(overshoot_max, 0.12, "PID speed overshoot must be < 12%")
        self.assertAlmostEqual(current_speed, target_speed, delta=3.0,
                               msg="PID speed controller must settle close to target speed")

    def test_pid_heading_step_response(self):
        pid = PIDController(kp=1.6, ki=0.1, kd=0.12, out_min=-50, out_max=50)
        target_heading = 45.0
        current_heading = 0.0
        dt = 0.025

        for _ in range(100):
            err = target_heading - current_heading
            effort = pid.update(target_heading, current_heading, dt=dt)
            # Simulated angular acceleration and pivot dynamics
            current_heading += effort * 0.08

        self.assertAlmostEqual(current_heading, target_heading, delta=2.5,
                               msg="Heading PID must converge to setpoint within 2.5 degrees")


class TestAdaptiveSpeedRamping(unittest.TestCase):
    """Unit tests verifying distance-proportional speed governor."""

    def test_speed_ramp_distance_profile(self):
        gov = SpeedRampController(v_max=70.0, v_min=22.0, d_crit=20.0, d_slow=65.0)

        # Clear distance: max speed
        v_open = gov.calculate_target_speed(150.0)
        self.assertEqual(v_open, 70.0)

        # Midway approach: throttled speed
        v_mid = gov.calculate_target_speed(42.5)
        self.assertGreater(v_mid, 22.0)
        self.assertLess(v_mid, 70.0)

        # Critical proximity: zero speed
        v_crit = gov.calculate_target_speed(18.0)
        self.assertEqual(v_crit, 0.0)

    def test_slew_rate_acceleration_limits(self):
        gov = SpeedRampController(v_max=70.0, accel_rate=100.0, decel_rate=200.0)
        # Rapid jump to clear distance
        s1 = gov.update(100.0)
        time.sleep(0.02)
        s2 = gov.update(100.0)
        self.assertLessEqual(s2 - s1, 15.0, "Acceleration jerk must be strictly slew-limited")


class TestOccupancyGridMapping(unittest.TestCase):
    """Unit tests verifying 2D local occupancy grid raycasting."""

    def test_raycast_obstacle_registration(self):
        grid = OccupancyGridMap(size=41, resolution_cm=5.0)
        # Raycast directly ahead at 50cm
        grid.update_ray(angle_deg=0.0, distance_cm=50.0)

        occupied = grid.get_occupied_cells(threshold=0.65)
        self.assertGreaterEqual(len(occupied), 1, "Obstacle at 50cm must be registered")

        # Verify free cells along ray
        free_gx, free_gy = grid.world_to_grid(25.0, 0.0)
        free_prob = grid.grid[grid._get_index(free_gx, free_gy)]
        self.assertLess(free_prob, 0.45, "Cells between rover and obstacle must be marked free")

    def test_sector_clearance_queries(self):
        grid = OccupancyGridMap(size=41, resolution_cm=5.0)
        # Register obstacle at +30 degrees at 35cm
        grid.update_ray(angle_deg=30.0, distance_cm=35.0)
        clearance = grid.get_sector_clearance(sectors=[-30, 0, 30])
        self.assertLess(clearance[30], 45.0, "Sector at 30 deg must report restricted clearance")


class TestArenaSimulationAndCollisionAvoidance(unittest.TestCase):
    """Autonomous traversal simulation in multi-obstacle virtual arena."""

    def test_autonomous_navigation_zero_collisions(self):
        arena = VirtualArena()
        physics = VirtualRoverPhysics(init_x=175.0, init_y=55.0, init_heading_deg=90.0)
        rover = TerraScoutRover()
        # Immediately arm into autonomous cruise state
        rover.sm.change_state(rover.sm.STATE_CRUISE)
        rover.sm.state_enter_time = -10000

        # Bind dynamic raycasting callback to rover ultrasonic sensor
        rover.ultrasonic._sim_distance = lambda: arena.cast_ray(
            physics.x, physics.y, physics.heading_rad + math.radians(rover.servo.current_angle)
        )

        set_simulated_time_ms(0)
        dt = 0.025
        steps = 800  # 20.0 seconds of autonomous exploration
        collisions_detected = 0
        min_clearance_recorded = 999.0
        distance_traversed = 0.0
        last_x, last_y = physics.x, physics.y

        try:
            for step in range(steps):
                set_simulated_time_ms(step * 25)

                # 1. Update IMU gyro rate
                rover.mpu.sim_yaw_rate = physics.yaw_rate_dps

                # 3. Advance rover firmware state machine
                rover.run_step()

                # 4. Advance physics with commanded motor duties
                duty_l = rover.drive.actual_left
                duty_r = rover.drive.actual_right
                physics.step(duty_l, duty_r, dt=dt)

                # Check collision
                hit, clearance = arena.check_collision(physics.x, physics.y)
                if hit:
                    collisions_detected += 1
                if clearance < min_clearance_recorded:
                    min_clearance_recorded = clearance

                distance_traversed += math.hypot(physics.x - last_x, physics.y - last_y)
                last_x, last_y = physics.x, physics.y
        finally:
            set_simulated_time_ms(None)

        self.assertEqual(collisions_detected, 0,
                         f"Zero collisions allowed! Detected {collisions_detected} collisions.")
        self.assertGreater(distance_traversed, 60.0,
                           "Rover must actively traverse the arena during autonomous cruise")
        self.assertGreater(min_clearance_recorded, -0.1,
                           "Rover footprint must never violate obstacle margins")


class TestTelemetryServerAPI(unittest.TestCase):
    """Unit tests validating web telemetry server endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.port = 8899
        cls.server = TelemetryServer(host="127.0.0.1", port=cls.port)
        cls.server.start(block=False)
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_dashboard_index_html(self):
        url = f"http://127.0.0.1:{self.port}/"
        req = Request(url)
        with urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("TERRASCOUT AUTONOMOUS GROUND ROVER", html)
            self.assertIn("radarCanvas", html)
            self.assertIn("gridCanvas", html)

    def test_telemetry_json_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/telemetry"
        req = Request(url)
        with urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("battery", data)
            self.assertIn("imu", data)
            self.assertIn("ultrasonic", data)
            self.assertIn("motors", data)
            self.assertGreater(data["battery"]["voltage_v"], 6.0)

    def test_grid_json_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/grid"
        req = Request(url)
        with urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            grid = json.loads(resp.read().decode("utf-8"))
            self.assertIsInstance(grid, list)

    def test_post_command_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/command"
        payload = json.dumps({"action": "emergency_stop"}).encode("utf-8")
        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            res = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res["status"], "acknowledged")
            self.assertEqual(res["action"], "emergency_stop")


# ==============================================================================
# Telemetry Benchmark Visualizer & Asset Generator
# ==============================================================================
def generate_telemetry_benchmark_asset(output_path="assets/telemetry_benchmark.png"):
    """
    Executes a high-resolution 1000-tick closed-loop simulation, records all telemetry
    timeseries, and renders a publication-grade benchmark visualization plot.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    print(f"[BENCHMARK] Generating telemetry benchmark asset -> {output_path}...")

    arena = VirtualArena()
    physics = VirtualRoverPhysics(init_x=175.0, init_y=60.0, init_heading_deg=90.0)
    rover = TerraScoutRover()

    dt = 0.025
    total_steps = 1000

    # Timeseries recording buffers
    time_series = []
    target_speeds = []
    actual_speeds = []
    distances = []
    true_headings = []
    kalman_headings = []
    raw_headings = []
    battery_volts = []
    motor_pwms_l = []
    motor_pwms_r = []
    states = []
    traj_x = []
    traj_y = []
    radar_pings_x = []
    radar_pings_y = []

    cum_raw_heading = 90.0
    gyro_drift_rate = 0.08 # deg/s

    try:
        for step in range(total_steps):
            set_simulated_time_ms(step * 25)
            t_sec = step * dt
            time_series.append(t_sec)

            # Ultrasonic raycast
            sonar_angle_rad = physics.heading_rad + math.radians(rover.servo.current_angle)
            ray_dist = arena.cast_ray(physics.x, physics.y, sonar_angle_rad)
            rover.ultrasonic._sim_distance = ray_dist

            # Record radar hits when obstacle within 150cm
            if ray_dist < 150.0 and step % 4 == 0:
                hit_x = physics.x + ray_dist * math.cos(sonar_angle_rad)
                hit_y = physics.y + ray_dist * math.sin(sonar_angle_rad)
                radar_pings_x.append(hit_x)
                radar_pings_y.append(hit_y)

            # IMU simulation
            physics_dps = physics.yaw_rate_dps
            rover.mpu.sim_yaw_rate = physics_dps

            # Raw gyro integration with drift
            cum_raw_heading += (physics_dps + gyro_drift_rate + random.gauss(0.0, 0.4)) * dt

            # Advance rover
            rover.run_step()

            # Step physics
            sagged_v = physics.step(rover.drive.actual_left, rover.drive.actual_right, dt=dt)
            rover.battery._adc.set_voltage(sagged_v)

            # Record metrics
            target_speeds.append(rover.speed_ramp.target_speed)
            actual_speeds.append(physics.actual_speed)
            distances.append(ray_dist)
            true_headings.append(math.degrees(physics.heading_rad))
            kalman_headings.append(rover.imu.heading)
            raw_headings.append(cum_raw_heading)
            battery_volts.append(sagged_v)
            motor_pwms_l.append(rover.drive.actual_left)
            motor_pwms_r.append(rover.drive.actual_right)
            states.append(rover.sm.state)
            traj_x.append(physics.x)
            traj_y.append(physics.y)
    finally:
        set_simulated_time_ms(None)

    # Setup publication-grade styling
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(18, 12), dpi=150)
    fig.patch.set_facecolor("#080d1a")

    gs = fig.add_gridspec(2, 2, hspace=0.28, wspace=0.24)

    # --------------------------------------------------------------------------
    # Subplot 1: PID Velocity & Adaptive Speed Ramping Response
    # --------------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor("#0e1526")
    ax1.grid(True, linestyle="--", alpha=0.3, color="#1f2d4d")

    line1 = ax1.plot(time_series, target_speeds, label="Adaptive Speed Target (cm/s)",
                     color="#00f2fe", linewidth=1.8, linestyle="--")
    line2 = ax1.plot(time_series, actual_speeds, label="Actual Rover Speed (cm/s)",
                     color="#10b981", linewidth=2.2)
    ax1.set_xlabel("Simulation Time (s)", fontsize=11, color="#cbd5e1")
    ax1.set_ylabel("Linear Velocity (cm/s)", fontsize=11, color="#cbd5e1")
    ax1.set_title("1. PID Velocity & Adaptive Speed Ramping Response", fontsize=13, fontweight="bold", pad=12, color="#00f2fe")

    ax1_twin = ax1.twinx()
    line3 = ax1_twin.plot(time_series, distances, label="Sonar Distance (cm)",
                          color="#f59e0b", linewidth=1.2, alpha=0.75)
    ax1_twin.axhline(22.0, color="#ef4444", linestyle=":", label="Critical Threshold (22cm)")
    ax1_twin.set_ylabel("Clearance Distance (cm)", fontsize=11, color="#f59e0b")

    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper right", framealpha=0.6, fontsize=9)

    # --------------------------------------------------------------------------
    # Subplot 2: IMU Orientation & Kalman Filter vs Raw Gyro Drift
    # --------------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor("#0e1526")
    ax2.grid(True, linestyle="--", alpha=0.3, color="#1f2d4d")

    # Wrap true headings to match Kalman
    wrapped_true = [(h + 180) % 360 - 180 for h in true_headings]
    ax2.plot(time_series, wrapped_true, label="Ground Truth Heading (deg)",
             color="#ffffff", linewidth=2.0, alpha=0.9)
    ax2.plot(time_series, kalman_headings, label="Kalman Active Estimate (deg)",
             color="#00f2fe", linewidth=1.8, linestyle="-")
    ax2.plot(time_series, [(h + 180) % 360 - 180 for h in raw_headings],
             label="Raw Gyro Integration (Unfiltered Drift)", color="#ef4444",
             linewidth=1.2, linestyle=":", alpha=0.7)

    ax2.set_xlabel("Simulation Time (s)", fontsize=11, color="#cbd5e1")
    ax2.set_ylabel("Heading / Yaw (deg)", fontsize=11, color="#cbd5e1")
    ax2.set_title("2. IMU Heading: Active Kalman Filter vs Sensor Drift", fontsize=13, fontweight="bold", pad=12, color="#00f2fe")
    ax2.legend(loc="lower left", framealpha=0.6, fontsize=9)

    # --------------------------------------------------------------------------
    # Subplot 3: 2D Virtual Arena Trajectory & Occupancy Radar Pings
    # --------------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor("#0e1526")
    ax3.set_aspect("equal")
    ax3.set_xlim(-10, arena.width + 10)
    ax3.set_ylim(-10, arena.height + 10)
    ax3.grid(True, linestyle="--", alpha=0.3, color="#1f2d4d")

    # Draw boundary walls
    for (p1, p2) in arena.walls:
        ax3.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#64748b", linewidth=2.5)

    # Draw boxes
    for (bx1, by1, bx2, by2) in arena.boxes:
        rect = plt.Rectangle((bx1, by1), bx2 - bx1, by2 - by1,
                             facecolor="#1e293b", edgecolor="#38bdf8", linewidth=1.8, alpha=0.85)
        ax3.add_patch(rect)

    # Draw cylinder
    for (cx, cy, r) in arena.cylinders:
        circle = plt.Circle((cx, cy), r, facecolor="#1e293b", edgecolor="#f59e0b", linewidth=1.8, alpha=0.85)
        ax3.add_patch(circle)

    # Draw radar hits
    if radar_pings_x:
        ax3.scatter(radar_pings_x, radar_pings_y, s=4, color="#ef4444", alpha=0.45, label="Sonar Radar Pings")

    # Draw traversed trajectory colored by speed
    points = np.array([traj_x, traj_y]).T.reshape(-1, 1, 2)
    from matplotlib.collections import LineCollection
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    norm = plt.Normalize(0, 35)
    lc = LineCollection(segments, cmap="plasma", norm=norm, linewidth=2.2, label="Rover Trajectory")
    lc.set_array(np.array(actual_speeds))
    ax3.add_collection(lc)

    # Start and End points
    ax3.plot(traj_x[0], traj_y[0], "o", color="#10b981", markersize=9, label="Start Position")
    ax3.plot(traj_x[-1], traj_y[-1], "*", color="#00f2fe", markersize=12, label="Current Position")

    ax3.set_title("3. 2D Obstacle Arena Trajectory & Occupancy Radar", fontsize=13, fontweight="bold", pad=12, color="#00f2fe")
    ax3.set_xlabel("Arena X Coordinate (cm)", fontsize=11, color="#cbd5e1")
    ax3.set_ylabel("Arena Y Coordinate (cm)", fontsize=11, color="#cbd5e1")
    cbar = fig.colorbar(lc, ax=ax3, fraction=0.046, pad=0.04)
    cbar.set_label("Speed (cm/s)", color="#cbd5e1")
    ax3.legend(loc="upper left", framealpha=0.6, fontsize=8)

    # --------------------------------------------------------------------------
    # Subplot 4: Telemetry Power & State Transitions
    # --------------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor("#0e1526")
    ax4.grid(True, linestyle="--", alpha=0.3, color="#1f2d4d")

    ax4.plot(time_series, battery_volts, label="2S Pack Voltage (V)", color="#38bdf8", linewidth=2.0)
    ax4.axhline(6.4, color="#ef4444", linestyle=":", label="Low Battery Threshold (6.4V)")
    ax4.set_xlabel("Simulation Time (s)", fontsize=11, color="#cbd5e1")
    ax4.set_ylabel("Battery Pack Voltage (V)", fontsize=11, color="#38bdf8")
    ax4.set_title("4. Power Subsystem & Motor PWM Metrics", fontsize=13, fontweight="bold", pad=12, color="#00f2fe")

    ax4_twin = ax4.twinx()
    ax4_twin.plot(time_series, motor_pwms_l, label="Left Motor PWM (%)", color="#a855f7", linewidth=1.2, alpha=0.7)
    ax4_twin.plot(time_series, motor_pwms_r, label="Right Motor PWM (%)", color="#ec4899", linewidth=1.2, alpha=0.7)
    ax4_twin.set_ylabel("Motor PWM Effort (%)", fontsize=11, color="#ec4899")

    # Combine legends
    lines4 = ax4.get_lines() + ax4_twin.get_lines()
    labels4 = [l.get_label() for l in lines4]
    ax4.legend(lines4, labels4, loc="upper right", framealpha=0.6, fontsize=9)

    plt.suptitle("TERRASCOUT GROUNDED — AUTONOMOUS FIRMWARE & TELEMETRY BENCHMARK AUDIT",
                 fontsize=16, fontweight="heavy", color="#f8fafc", y=0.98)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight")
    svg_path = os.path.splitext(output_path)[0] + ".svg"
    plt.savefig(svg_path, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight")
    plt.close()
    print(f"[BENCHMARK] Telemetry benchmark saved successfully to {output_path} ({os.path.getsize(output_path):,} bytes) and {svg_path} ({os.path.getsize(svg_path):,} bytes).")


# ==============================================================================
# Master Test Runner Entrypoint
# ==============================================================================
def run_all_tests():
    """Runs test suite and generates benchmark telemetry graph."""
    print("=" * 70)
    print("TERRASCOUT AUTONOMOUS FIRMWARE - COMPREHENSIVE SIMULATION SUITE")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestIMUFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestPIDControllers))
    suite.addTests(loader.loadTestsFromTestCase(TestAdaptiveSpeedRamping))
    suite.addTests(loader.loadTestsFromTestCase(TestOccupancyGridMapping))
    suite.addTests(loader.loadTestsFromTestCase(TestArenaSimulationAndCollisionAvoidance))
    suite.addTests(loader.loadTestsFromTestCase(TestTelemetryServerAPI))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    if result.wasSuccessful():
        print(f"100% TEST PASS RATE CONFIRMED: {result.testsRun} TESTS EXECUTED CLEANLY.")
        # Generate benchmark visual artifact
        benchmark_file = os.path.join(PROJECT_ROOT, "assets", "telemetry_benchmark.png")
        generate_telemetry_benchmark_asset(benchmark_file)
        return True
    else:
        print(f"TEST FAILURES DETECTED: {len(result.failures)} Failures, {len(result.errors)} Errors.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
