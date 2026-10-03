"""
================================================================================
TerraScout Grounded Telemetry Rover - Asynchronous Web Telemetry Server
Project: TerraScout Grounded (Autonomous Telemetry Rover)
Target: Python 3.8+ / MicroPython LAN Gateway
License: MIT / CERN-OHL-P v2
================================================================================

Features:
  1. Real-time REST API:
     - `GET /api/telemetry` -> JSON sensor packet (battery, IMU, motors, radar, state).
     - `GET /api/grid` -> JSON 2D occupancy grid map cells and probability matrix.
     - `POST /api/command` -> Remote manual override and mission control commands.
     - `GET /api/stream` -> Server-Sent Events (SSE) live push stream at 10 Hz.
  2. Single-Page Glass Cockpit Telemetry HUD (`GET /`):
     - Fully self-contained (zero external CDN or internet connection required).
     - Real-time polar ultrasonic radar scope with sweep animation and danger rings.
     - 2D local occupancy grid canvas showing rover position and mapped obstacles.
     - Interactive artificial horizon and 360-degree compass heading dial.
     - Battery gauge (2S Li-ion pack voltage and state of charge %).
     - Dual motor PWM power gauges with directional indicators.
     - Environmental telemetry (temperature, barometric pressure, filtered altitude).
     - Remote mission control command panel.
  3. Integrated Standalone Simulation Daemon:
     - Runs out-of-the-box with a simulated rover loop if hardware is not connected.
================================================================================
"""

import json
import math
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# Import TerraScoutRover if available in path
try:
    from src.main import TerraScoutRover
except ImportError:
    try:
        from main import TerraScoutRover
    except ImportError:
        TerraScoutRover = None


# ==============================================================================
# Thread-Safe Telemetry Store
# ==============================================================================
class TelemetryStore:
    """Thread-safe state container storing the latest telemetry packet and grid map."""

    def __init__(self):
        self._lock = threading.Lock()
        self.packet = {
            "time_ms": int(time.time() * 1000),
            "state": "CRUISE",
            "battery": {"voltage_v": 7.64, "soc_pct": 78.5, "critical": False},
            "motors": {
                "target_l": 55.0,
                "target_r": 55.0,
                "actual_l": 54.2,
                "actual_r": 54.2,
                "pwm_l_pct": 54.2,
                "pwm_r_pct": 54.2,
            },
            "imu": {
                "heading_deg": 18.5,
                "pitch_deg": 1.2,
                "roll_deg": -0.8,
                "heading_rate_dps": 0.04,
                "kalman_active": True,
            },
            "ultrasonic": {
                "forward_cm": 86.4,
                "turret_angle_deg": 0.0,
                "scan_sectors": {
                    "-60": 115.0,
                    "-30": 92.0,
                    "0": 86.4,
                    "30": 78.0,
                    "60": 124.0,
                },
            },
            "environment": {
                "temp_c": 23.8,
                "press_hpa": 1013.1,
                "altitude_m": 44.6,
            },
            "navigation": {
                "speed_ramp_factor": 0.88,
                "best_heading_deg": 0.0,
                "target_heading_deg": 0.0,
                "obstacles_detected": 4,
            },
        }
        self.grid_cells = [
            {"fwd_cm": 45.0, "lat_cm": 0.0, "prob": 0.88},
            {"fwd_cm": 60.0, "lat_cm": 35.0, "prob": 0.92},
            {"fwd_cm": 75.0, "lat_cm": -40.0, "prob": 0.85},
            {"fwd_cm": 90.0, "lat_cm": 15.0, "prob": 0.79},
        ]
        self.pending_command = None
        self.subscribers = []

    def update_from_dict(self, data, grid_cells=None):
        with self._lock:
            self.packet = data
            if grid_cells is not None:
                self.grid_cells = grid_cells

    def update_from_rover(self, rover):
        data = rover.get_telemetry_dict()
        occupied = [
            {"fwd_cm": x, "lat_cm": y, "prob": p}
            for (x, y, p) in rover.grid_map.get_occupied_cells(threshold=0.65)
        ]
        self.update_from_dict(data, occupied)

    def get_telemetry(self):
        with self._lock:
            return dict(self.packet)

    def get_grid(self):
        with self._lock:
            return list(self.grid_cells)

    def set_command(self, cmd):
        with self._lock:
            self.pending_command = cmd

    def pop_command(self):
        with self._lock:
            cmd = self.pending_command
            self.pending_command = None
            return cmd


# Global telemetry store singleton
STORE = TelemetryStore()


# ==============================================================================
# Glass Cockpit Telemetry HUD - Embedded Single Page Dashboard
# ==============================================================================
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TerraScout Grounded | Autonomous Telemetry HUD</title>
<style>
  :root {
    --bg-dark: #080d1a;
    --card-bg: #11192e;
    --card-border: #1f2d4d;
    --accent-cyan: #00f2fe;
    --accent-teal: #4facfe;
    --accent-amber: #f59e0b;
    --accent-emerald: #10b981;
    --accent-crimson: #ef4444;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-dim: #64748b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background-color: var(--bg-dark);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace, sans-serif;
    padding: 18px;
    font-size: 14px;
    line-height: 1.4;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 18px;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    margin-bottom: 18px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  }
  .header-title { display: flex; align-items: center; gap: 12px; }
  .logo-badge {
    background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
    color: #050b14;
    font-weight: 900;
    font-size: 16px;
    padding: 6px 12px;
    border-radius: 6px;
    letter-spacing: 1px;
  }
  h1 { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }
  .header-status { display: flex; align-items: center; gap: 16px; }
  .state-badge {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid var(--accent-emerald);
    color: var(--accent-emerald);
    padding: 5px 14px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .live-dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--accent-emerald);
    box-shadow: 0 0 10px var(--accent-emerald);
    display: inline-block;
    animation: pulse 1.5s infinite;
  }
  @keyframes pulse {
    0% { transform: scale(0.95); opacity: 0.7; }
    50% { transform: scale(1.15); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.7; }
  }

  /* Grid Layout */
  .grid-container {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 18px;
  }
  .card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.25);
  }
  .card-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: var(--text-dim);
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .metric-large {
    font-size: 30px;
    font-weight: 800;
    color: var(--accent-cyan);
    font-family: monospace;
    display: flex;
    align-items: baseline;
    gap: 4px;
  }
  .metric-unit { font-size: 14px; color: var(--text-secondary); font-weight: 400; }
  .metric-sub {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 6px;
  }

  /* Progress bars */
  .bar-bg {
    width: 100%;
    height: 8px;
    background: #1a2642;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 8px;
  }
  .bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #00f2fe, #4facfe);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  /* Main Visualization Area */
  .viz-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 18px;
  }
  .canvas-wrapper {
    position: relative;
    width: 100%;
    height: 320px;
    background: #091024;
    border-radius: 8px;
    border: 1px solid #1a284c;
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
  }
  canvas { width: 100%; height: 100%; display: block; }

  /* Remote Control Bar */
  .control-bar {
    display: flex;
    gap: 12px;
    padding: 14px 18px;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    margin-bottom: 18px;
    align-items: center;
  }
  .btn {
    padding: 9px 18px;
    border-radius: 6px;
    border: none;
    font-weight: 700;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s ease;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .btn-danger { background: var(--accent-crimson); color: white; }
  .btn-danger:hover { background: #dc2626; box-shadow: 0 0 12px rgba(239, 68, 68, 0.4); }
  .btn-success { background: var(--accent-emerald); color: #050b14; }
  .btn-success:hover { background: #059669; color: white; box-shadow: 0 0 12px rgba(16, 185, 129, 0.4); }
  .btn-secondary { background: #1e293b; color: var(--text-primary); border: 1px solid #334155; }
  .btn-secondary:hover { background: #334155; }

  /* Log Ticker */
  .log-console {
    background: #050811;
    border: 1px solid #16203a;
    border-radius: 8px;
    padding: 12px;
    font-family: monospace;
    font-size: 12px;
    height: 120px;
    overflow-y: auto;
    color: #38bdf8;
  }
  .log-line { margin-bottom: 4px; }
  .log-time { color: var(--text-dim); margin-right: 8px; }

  @media (max-width: 1024px) {
    .grid-container { grid-template-columns: repeat(2, 1fr); }
    .viz-row { grid-template-columns: 1fr; }
  }
  @media (max-width: 600px) {
    .grid-container { grid-template-columns: 1fr; }
    .control-bar { flex-direction: column; align-items: stretch; }
  }
</style>
</head>
<body>

<header>
  <div class="header-title">
    <div class="logo-badge">TSCOUT</div>
    <div>
      <h1>TERRASCOUT AUTONOMOUS GROUND ROVER</h1>
      <div style="font-size: 11px; color: var(--text-dim);">FIRMWARE TELEMETRY & OCCUPANCY RADAR FLIGHT HUD</div>
    </div>
  </div>
  <div class="header-status">
    <div style="display: flex; align-items: center; gap: 8px; font-size: 12px;">
      <span class="live-dot"></span> LIVE TELEMETRY
    </div>
    <div id="stateBadge" class="state-badge">CRUISE</div>
  </div>
</header>

<!-- Telemetry Summary Cards -->
<div class="grid-container">
  <!-- Card 1: Battery -->
  <div class="card">
    <div class="card-title">2S Li-ion Battery Pack <span id="batIcon">⚡</span></div>
    <div class="metric-large"><span id="batVolt">7.62</span> <span class="metric-unit">V</span></div>
    <div class="metric-sub">State of Charge: <b id="batPct">78</b>%</div>
    <div class="bar-bg">
      <div id="batBar" class="bar-fill" style="width: 78%;"></div>
    </div>
  </div>

  <!-- Card 2: Ultrasonic Range -->
  <div class="card">
    <div class="card-title">Look-Ahead Sonar <span id="sonarIcon">📡</span></div>
    <div class="metric-large"><span id="distCm">86.4</span> <span class="metric-unit">cm</span></div>
    <div class="metric-sub">Turret Angle: <b id="turretAngle">0.0</b>° | Safe Corridor</div>
    <div class="bar-bg">
      <div id="distBar" class="bar-fill" style="width: 43%; background: linear-gradient(90deg, #10b981, #00f2fe);"></div>
    </div>
  </div>

  <!-- Card 3: IMU Heading & Attitude -->
  <div class="card">
    <div class="card-title">MPU6050 Kalman Attitude <span>🧭</span></div>
    <div class="metric-large"><span id="headingDeg">18.5</span> <span class="metric-unit">°</span></div>
    <div class="metric-sub">Pitch: <b id="pitchDeg">+1.2</b>° | Roll: <b id="rollDeg">-0.8</b>°</div>
    <div class="metric-sub" style="color: var(--accent-emerald);">Active Kalman Fusion (Q_cov: 0.001)</div>
  </div>

  <!-- Card 4: Differential Motor Effort -->
  <div class="card">
    <div class="card-title">Dual N20 Motor PWM <span>⚙️</span></div>
    <div class="metric-large"><span id="motorAvg">54</span> <span class="metric-unit">%</span></div>
    <div class="metric-sub">Left: <b id="motorL">54.2</b>% | Right: <b id="motorR">54.2</b>%</div>
    <div class="metric-sub">Adaptive Speed Factor: <b id="speedFactor">0.88</b>x</div>
  </div>
</div>

<!-- Main Visualization Row -->
<div class="viz-row">
  <!-- Polar Ultrasonic Radar Scope -->
  <div class="card">
    <div class="card-title">
      <span>Polar Ultrasonic Radar Arc (-60° to +60°)</span>
      <span style="color: var(--accent-cyan); font-family: monospace;">RANGE: 200 CM</span>
    </div>
    <div class="canvas-wrapper">
      <canvas id="radarCanvas" width="480" height="320"></canvas>
    </div>
  </div>

  <!-- 2D Local Occupancy Grid Map -->
  <div class="card">
    <div class="card-title">
      <span>2D Local Occupancy Grid Map (41x41 Cells, 5cm Res)</span>
      <span id="obstacleCount" style="color: var(--accent-amber); font-family: monospace;">4 HAZARDS</span>
    </div>
    <div class="canvas-wrapper">
      <canvas id="gridCanvas" width="480" height="320"></canvas>
    </div>
  </div>
</div>

<!-- Mission Control Command Bar -->
<div class="control-bar">
  <span style="font-weight: 700; font-size: 12px; letter-spacing: 1px; color: var(--text-dim);">MISSION OVERRIDE:</span>
  <button class="btn btn-danger" onclick="sendCommand('emergency_stop')">🛑 Emergency Brake</button>
  <button class="btn btn-success" onclick="sendCommand('resume')">▶ Resume Cruise</button>
  <button class="btn btn-secondary" onclick="sendCommand('panoramic_scan')">🔄 Trigger Sweep Scan</button>
  <button class="btn btn-secondary" onclick="sendCommand('pivot_left')">↺ Pivot Left 45°</button>
  <button class="btn btn-secondary" onclick="sendCommand('pivot_right')">↻ Pivot Right 45°</button>
</div>

<!-- Real-Time Telemetry Event Log -->
<div class="card">
  <div class="card-title">Telemetry Stream Logger</div>
  <div id="logConsole" class="log-console">
    <div class="log-line"><span class="log-time">[BOOT]</span> TerraScout Telemetry HUD initialized. Connecting stream...</div>
  </div>
</div>

<script>
  let telemetryData = {};
  let gridData = [];
  let sweepAngle = -60;
  let sweepDir = 1;

  function appendLog(msg) {
    const consoleEl = document.getElementById("logConsole");
    const now = new Date().toTimeString().split(' ')[0];
    const line = document.createElement("div");
    line.className = "log-line";
    line.innerHTML = `<span class="log-time">[${now}]</span> ${msg}`;
    consoleEl.appendChild(line);
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function sendCommand(action) {
    fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action })
    })
    .then(r => r.json())
    .then(res => {
      appendLog(`Dispatched command: <b>${action}</b> -> ${res.status}`);
    })
    .catch(err => appendLog(`Command error: ${err}`));
  }

  // Update UI Elements
  function updateUI(t) {
    telemetryData = t;
    document.getElementById("stateBadge").innerText = t.state || "CRUISE";
    
    // Battery
    const batV = t.battery ? t.battery.voltage_v : 7.6;
    const soc = t.battery ? t.battery.soc_pct : 75;
    document.getElementById("batVolt").innerText = batV.toFixed(2);
    document.getElementById("batPct").innerText = Math.round(soc);
    document.getElementById("batBar").style.width = soc + "%";
    if (soc < 20) {
      document.getElementById("batBar").style.background = "var(--accent-crimson)";
    } else {
      document.getElementById("batBar").style.background = "linear-gradient(90deg, #00f2fe, #4facfe)";
    }

    // Ultrasonic
    const dist = t.ultrasonic ? t.ultrasonic.forward_cm : 100;
    const turret = t.ultrasonic ? t.ultrasonic.turret_angle_deg : 0;
    document.getElementById("distCm").innerText = dist.toFixed(1);
    document.getElementById("turretAngle").innerText = turret.toFixed(1);
    const distPct = Math.min(100, (dist / 200) * 100);
    document.getElementById("distBar").style.width = distPct + "%";

    // IMU
    if (t.imu) {
      document.getElementById("headingDeg").innerText = t.imu.heading_deg.toFixed(1);
      document.getElementById("pitchDeg").innerText = (t.imu.pitch_deg >= 0 ? "+" : "") + t.imu.pitch_deg.toFixed(1);
      document.getElementById("rollDeg").innerText = (t.imu.roll_deg >= 0 ? "+" : "") + t.imu.roll_deg.toFixed(1);
    }

    // Motors
    if (t.motors) {
      document.getElementById("motorL").innerText = t.motors.pwm_l_pct.toFixed(1);
      document.getElementById("motorR").innerText = t.motors.pwm_r_pct.toFixed(1);
      const avg = ((t.motors.pwm_l_pct + t.motors.pwm_r_pct) / 2).toFixed(0);
      document.getElementById("motorAvg").innerText = avg;
    }
    if (t.navigation) {
      document.getElementById("speedFactor").innerText = t.navigation.speed_ramp_factor.toFixed(2);
      document.getElementById("obstacleCount").innerText = `${t.navigation.obstacles_detected} HAZARDS`;
    }
  }

  // Draw Polar Radar Scope
  function drawRadar() {
    const canvas = document.getElementById("radarCanvas");
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h - 30;
    const maxR = h - 60;

    // Draw range rings
    const rings = [0.25, 0.5, 0.75, 1.0];
    rings.forEach((ratio, idx) => {
      const r = maxR * ratio;
      ctx.beginPath();
      ctx.arc(cx, cy, r, Math.PI, 2 * Math.PI);
      ctx.strokeStyle = "rgba(0, 242, 254, 0.18)";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Range text (cm)
      ctx.fillStyle = "rgba(148, 163, 184, 0.5)";
      ctx.font = "10px monospace";
      ctx.fillText(`${idx * 50 + 50}cm`, cx + 6, cy - r + 10);
    });

    // Draw radial sector lines (-60, -30, 0, 30, 60 deg)
    const angles = [-60, -30, 0, 30, 60];
    angles.forEach(ang => {
      const rad = (ang - 90) * (Math.PI / 180);
      const ex = cx + maxR * Math.cos(rad);
      const ey = cy + maxR * Math.sin(rad);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(ex, ey);
      ctx.strokeStyle = "rgba(79, 172, 254, 0.2)";
      ctx.stroke();

      ctx.fillStyle = "rgba(148, 163, 184, 0.7)";
      ctx.font = "10px monospace";
      ctx.fillText(`${ang}°`, ex - 8, ey - 4);
    });

    // Draw obstacle blips from scan_sectors
    if (telemetryData.ultrasonic && telemetryData.ultrasonic.scan_sectors) {
      const sectors = telemetryData.ultrasonic.scan_sectors;
      for (const [angStr, dist] of Object.entries(sectors)) {
        const ang = parseFloat(angStr);
        if (dist > 0 && dist <= 200) {
          const ratio = dist / 200.0;
          const r = maxR * ratio;
          const rad = (ang - 90) * (Math.PI / 180);
          const bx = cx + r * Math.cos(rad);
          const by = cy + r * Math.sin(rad);

          ctx.beginPath();
          ctx.arc(bx, by, 7, 0, 2 * Math.PI);
          ctx.fillStyle = dist < 30 ? "rgba(239, 68, 68, 0.9)" : "rgba(245, 158, 11, 0.85)";
          ctx.fill();
          ctx.shadowBlur = 10;
          ctx.shadowColor = dist < 30 ? "#ef4444" : "#f59e0b";
          ctx.stroke();
          ctx.shadowBlur = 0;
        }
      }
    }

    // Animated radar sweep line
    sweepAngle += sweepDir * 2.2;
    if (sweepAngle > 60) sweepDir = -1;
    if (sweepAngle < -60) sweepDir = 1;
    const sweepRad = (sweepAngle - 90) * (Math.PI / 180);
    const sx = cx + maxR * Math.cos(sweepRad);
    const sy = cy + maxR * Math.sin(sweepRad);

    const grad = ctx.createLinearGradient(cx, cy, sx, sy);
    grad.addColorStop(0, "rgba(0, 242, 254, 0.1)");
    grad.addColorStop(1, "rgba(0, 242, 254, 0.85)");
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(sx, sy);
    ctx.strokeStyle = grad;
    ctx.lineWidth = 2.5;
    ctx.stroke();
  }

  // Draw 2D Local Occupancy Grid Map
  function drawGrid() {
    const canvas = document.getElementById("gridCanvas");
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const scale = 1.35; // px per cm

    // Background crosshair
    ctx.strokeStyle = "rgba(31, 45, 77, 0.6)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, cy); ctx.lineTo(w, cy);
    ctx.moveTo(cx, 0); ctx.lineTo(cx, h);
    ctx.stroke();

    // Concentric grid circles (50cm, 100cm)
    [50, 100].forEach(rCm => {
      ctx.beginPath();
      ctx.arc(cx, cy, rCm * scale, 0, 2 * Math.PI);
      ctx.strokeStyle = "rgba(79, 172, 254, 0.15)";
      ctx.stroke();
    });

    // Render registered obstacle cells from gridData
    gridData.forEach(cell => {
      // world coords: forward is -Y in screen, lateral is +X in screen
      const px = cx + (cell.lat_cm * scale);
      const py = cy - (cell.fwd_cm * scale);
      ctx.beginPath();
      ctx.rect(px - 4, py - 4, 8, 8);
      ctx.fillStyle = `rgba(239, 68, 68, ${Math.min(1.0, cell.prob)})`;
      ctx.fill();
    });

    // Render rover body icon at center
    ctx.save();
    ctx.translate(cx, cy);
    const hdg = telemetryData.imu ? (telemetryData.imu.heading_deg * Math.PI / 180) : 0;
    ctx.rotate(hdg);

    // Rover chassis rectangle
    ctx.fillStyle = "#00f2fe";
    ctx.shadowBlur = 12;
    ctx.shadowColor = "#00f2fe";
    ctx.fillRect(-12, -18, 24, 36);
    ctx.shadowBlur = 0;

    // Heading nose pointer
    ctx.beginPath();
    ctx.moveTo(0, -25);
    ctx.lineTo(-8, -18);
    ctx.lineTo(8, -18);
    ctx.closePath();
    ctx.fillStyle = "#ffffff";
    ctx.fill();

    ctx.restore();
  }

  // Animation Loop
  function animLoop() {
    drawRadar();
    drawGrid();
    requestAnimationFrame(animLoop);
  }
  requestAnimationFrame(animLoop);

  // SSE or Polling Loop
  function pollData() {
    fetch('/api/telemetry')
      .then(r => r.json())
      .then(t => updateUI(t))
      .catch(() => {});

    fetch('/api/grid')
      .then(r => r.json())
      .then(g => { gridData = g; })
      .catch(() => {});
  }
  setInterval(pollData, 100);
</script>

</body>
</html>
"""


# ==============================================================================
# HTTP Request Handler
# ==============================================================================
class TelemetryHTTPHandler(BaseHTTPRequestHandler):
    """Handles REST and dashboard HTTP requests."""

    def log_message(self, format, *args):
        # Suppress routine request logging to prevent console spam
        pass

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = STORE.get_telemetry()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif path == "/api/grid":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            grid = STORE.get_grid()
            self.wfile.write(json.dumps(grid).encode("utf-8"))

        elif path == "/api/stream":
            # Server-Sent Events (SSE) live push stream
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            try:
                for _ in range(50):  # Stream 50 ticks before reconnecting
                    telem = STORE.get_telemetry()
                    payload = f"data: {json.dumps(telem)}\\n\\n"
                    self.wfile.write(payload.encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(0.1)
            except (ConnectionResetError, BrokenPipeError):
                pass

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path

        if path == "/api/command":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                action = data.get("action", "unknown")
                STORE.set_command(action)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "acknowledged", "action": action}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


# ==============================================================================
# Telemetry Web Server Engine
# ==============================================================================
class TelemetryServer:
    """Asynchronous HTTP Web Telemetry Server."""

    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = port
        self.server = None
        self._thread = None
        self._running = False

    def start(self, block=False):
        """Starts the HTTP telemetry server on configured host and port."""
        self.server = ThreadingHTTPServer((self.host, self.port), TelemetryHTTPHandler)
        self._running = True

        if block:
            print(f"[TELEM-SRV] Server listening at http://{self.host}:{self.port}/")
            self.server.serve_forever()
        else:
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._thread.start()
            print(f"[TELEM-SRV] Server running in background at http://{self.host}:{self.port}/")

    def stop(self):
        """Stops the telemetry server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self._running = False
            print("[TELEM-SRV] Server shut down cleanly.")


# ==============================================================================
# Standalone Simulation Runner
# ==============================================================================
def run_standalone_simulation(port=8080):
    """Spins a mock rover simulation thread and hosts the live telemetry server."""
    print("=" * 60)
    print("TERRASCOUT WEB TELEMETRY SERVER & SIMULATOR")
    print(f"Hosting live aerospace HUD at: http://localhost:{port}/")
    print("=" * 60)

    server = TelemetryServer(host="0.0.0.0", port=port)
    server.start(block=False)

    # Initialize simulation rover if available
    rover = TerraScoutRover() if TerraScoutRover is not None else None

    # Virtual obstacle simulation state
    sim_t = 0.0
    heading_sim = 0.0
    dist_sim = 100.0

    try:
        while True:
            sim_t += 0.05
            if rover is not None:
                # Run step and update store
                rover.run_step()
                STORE.update_from_rover(rover)
            else:
                # Pure mathematical simulation if main not importable
                heading_sim = 25.0 * math.sin(sim_t * 0.5)
                dist_sim = 75.0 + 35.0 * math.cos(sim_t * 0.8)
                packet = {
                    "time_ms": int(time.time() * 1000),
                    "state": "CRUISE",
                    "battery": {"voltage_v": 7.60 - (sim_t * 0.001), "soc_pct": 76.0, "critical": False},
                    "motors": {
                        "target_l": 55.0, "target_r": 55.0,
                        "actual_l": 54.0, "actual_r": 54.0,
                        "pwm_l_pct": 54.0, "pwm_r_pct": 54.0
                    },
                    "imu": {
                        "heading_deg": round(heading_sim, 1),
                        "pitch_deg": round(1.2 * math.sin(sim_t), 1),
                        "roll_deg": round(0.8 * math.cos(sim_t), 1),
                        "heading_rate_dps": round(12.5 * math.cos(sim_t * 0.5), 2),
                        "kalman_active": True,
                    },
                    "ultrasonic": {
                        "forward_cm": round(dist_sim, 1),
                        "turret_angle_deg": round(30.0 * math.sin(sim_t * 2.0), 1),
                        "scan_sectors": {
                            "-60": round(90 + 20 * math.sin(sim_t), 1),
                            "-30": round(80 + 15 * math.cos(sim_t), 1),
                            "0": round(dist_sim, 1),
                            "30": round(85 - 10 * math.sin(sim_t), 1),
                            "60": round(110 + 25 * math.cos(sim_t), 1),
                        },
                    },
                    "environment": {
                        "temp_c": 23.8,
                        "press_hpa": 1013.2,
                        "altitude_m": 44.5,
                    },
                    "navigation": {
                        "speed_ramp_factor": round(max(0.2, min(1.0, dist_sim / 100.0)), 2),
                        "best_heading_deg": 0.0,
                        "target_heading_deg": 0.0,
                        "obstacles_detected": 4,
                    },
                }
                STORE.update_from_dict(packet)

            # Check if any manual command was received
            cmd = STORE.pop_command()
            if cmd:
                print(f"[REMOTE-CMD] Received command: {cmd}")
                if cmd == "emergency_stop" and rover is not None:
                    rover.drive.brake()
                    rover.sm.change_state("STOPPED")
                elif cmd == "resume" and rover is not None:
                    rover.sm.change_state("CRUISE")

            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[TELEM-SRV] Shutting down simulation server...")
        server.stop()


if __name__ == "__main__":
    port_arg = 8080
    if len(sys.argv) > 1:
        try:
            port_arg = int(sys.argv[1])
        except ValueError:
            pass
    run_standalone_simulation(port=port_arg)
