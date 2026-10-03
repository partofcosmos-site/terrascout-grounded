#!/usr/bin/env python3
"""
================================================================================
TerraScout Rover - Autonomous PCB Layout & Routing Engine
Project: TerraScout Grounded (Hack Club Grounded)
Author: Loop Agent 7 - TerraScout PCB Layout & Routing Engine
License: CERN-OHL-P v2 / MIT
================================================================================
"""

import os
import sys
import math
import zipfile
import subprocess
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# 1. BOARD SPECIFICATIONS & JLCPCB DESIGN RULES
# ==============================================================================
BOARD_WIDTH_MM = 100.0
BOARD_HEIGHT_MM = 80.0
BOARD_CORNER_RADIUS_MM = 3.0
BOARD_THICKNESS_MM = 1.6
COPPER_WEIGHT_OZ = 1.0  # 35 um

# DRC Design Rules (JLCPCB 2-Layer Standard)
MIN_TRACE_WIDTH_SIGNAL_MM = 0.254   # 10 mil
MIN_TRACE_WIDTH_POWER_MM  = 0.762   # 30 mil
MIN_CLEARANCE_MM          = 0.1524  # 6 mil
MIN_DRILL_MM              = 0.300   # 0.3 mm (12 mil)
VIA_PAD_DIA_MM            = 0.600   # 24 mil
VIA_DRILL_MM              = 0.300   # 12 mil
BOARD_EDGE_CLEARANCE_MM   = 0.500   # 20 mil

OUTPUT_DIR = Path(__file__).parent.resolve()

# M3 Mounting Hole Bolt Pattern (matching cad/chassis.scad 80mm x 60mm pattern)
MOUNT_HOLES = [
    {"name": "MH1", "x": 10.0, "y": 10.0, "drill": 3.2, "pad": 6.2},
    {"name": "MH2", "x": 90.0, "y": 10.0, "drill": 3.2, "pad": 6.2},
    {"name": "MH3", "x": 10.0, "y": 70.0, "drill": 3.2, "pad": 6.2},
    {"name": "MH4", "x": 90.0, "y": 70.0, "drill": 3.2, "pad": 6.2},
]

# ==============================================================================
# 2. DATA MODELS (PADS, TRACKS, VIAS, SILKSCREEN, ZONES)
# ==============================================================================
class Pad:
    def __init__(self, net, x, y, shape, w, h, drill=0.0, layer="All", pin_num="", component=""):
        self.net = net
        self.x = round(float(x), 4)
        self.y = round(float(y), 4)
        self.shape = shape  # "circle", "rect", "obround"
        self.w = round(float(w), 4)
        self.h = round(float(h), 4)
        self.drill = round(float(drill), 4)
        self.layer = layer  # "All", "F.Cu", "B.Cu"
        self.pin_num = str(pin_num)
        self.component = str(component)

class Track:
    def __init__(self, net, x1, y1, x2, y2, width, layer="F.Cu"):
        self.net = net
        self.x1 = round(float(x1), 4)
        self.y1 = round(float(y1), 4)
        self.x2 = round(float(x2), 4)
        self.y2 = round(float(y2), 4)
        self.width = round(float(width), 4)
        self.layer = layer  # "F.Cu" or "B.Cu"

class Via:
    def __init__(self, net, x, y, drill=VIA_DRILL_MM, pad=VIA_PAD_DIA_MM):
        self.net = net
        self.x = round(float(x), 4)
        self.y = round(float(y), 4)
        self.drill = round(float(drill), 4)
        self.pad = round(float(pad), 4)

class SilkLine:
    def __init__(self, x1, y1, x2, y2, width=0.15, layer="F.Silk"):
        self.x1 = round(float(x1), 4)
        self.y1 = round(float(y1), 4)
        self.x2 = round(float(x2), 4)
        self.y2 = round(float(y2), 4)
        self.width = round(float(width), 4)
        self.layer = layer

class SilkText:
    def __init__(self, text, x, y, size=1.2, layer="F.Silk", angle=0):
        self.text = text
        self.x = round(float(x), 4)
        self.y = round(float(y), 4)
        self.size = round(float(size), 4)
        self.layer = layer
        self.angle = angle

class Component:
    def __init__(self, ref, val, footprint, x, y, rot=0, desc="", lcsc=""):
        self.ref = ref
        self.val = val
        self.footprint = footprint
        self.x = round(float(x), 4)
        self.y = round(float(y), 4)
        self.rot = rot
        self.desc = desc
        self.lcsc = lcsc
        self.pads = []

# ==============================================================================
# 3. PCB GEOMETRY BUILDER
# ==============================================================================
class TerraScoutPCB:
    def __init__(self):
        self.components = []
        self.pads = []
        self.tracks = []
        self.vias = []
        self.silk_lines = []
        self.silk_texts = []
        self.edge_cuts = []
        
        self._build_board_outline()
        self._build_mounting_holes()
        self._build_components()
        self._route_tracks()
        self._build_ground_stitching()
        self._build_silkscreen_legends()

    def _build_board_outline(self):
        w, h, r = BOARD_WIDTH_MM, BOARD_HEIGHT_MM, BOARD_CORNER_RADIUS_MM
        # Rounded rectangle segments (Edge Cuts)
        # 4 straight edges + 4 corner arcs
        self.edge_cuts = [
            # Bottom straight line
            (r, 0, w - r, 0),
            # Right bottom arc approx lines
            (w - r, 0, w, r),
            # Right straight line
            (w, r, w, h - r),
            # Right top arc
            (w, h - r, w - r, h),
            # Top straight line
            (w - r, h, r, h),
            # Left top arc
            (r, h, 0, h - r),
            # Left straight line
            (0, h - r, 0, r),
            # Left bottom arc
            (0, r, r, 0)
        ]

    def _build_mounting_holes(self):
        for mh in MOUNT_HOLES:
            pad = Pad(
                net="GND",
                x=mh["x"],
                y=mh["y"],
                shape="circle",
                w=mh["pad"],
                h=mh["pad"],
                drill=mh["drill"],
                layer="All",
                pin_num="1",
                component=mh["name"]
            )
            self.pads.append(pad)
            
            # Silkscreen circle around mounting hole
            r = mh["pad"] / 2.0 + 0.5
            cx, cy = mh["x"], mh["y"]
            n_pts = 16
            for i in range(n_pts):
                a1 = 2 * math.pi * i / n_pts
                a2 = 2 * math.pi * (i + 1) / n_pts
                self.silk_lines.append(SilkLine(
                    cx + r * math.cos(a1), cy + r * math.sin(a1),
                    cx + r * math.cos(a2), cy + r * math.sin(a2),
                    width=0.15
                ))

    def _build_components(self):
        # ----------------------------------------------------------------------
        # U1: ESP32-S3 DevKitC-1 (2x22 Pin Headers, 2.54mm pitch, 25.4mm span)
        # ----------------------------------------------------------------------
        c_esp = Component("U1", "ESP32-S3-DevKitC-1", "DIP-44_W25.4mm", 38.7, 46.67, 0,
                          "ESP32-S3 Dual-Core Xtensa LX7 @ 240MHz, 8MB Flash", "C2913200")
        self.components.append(c_esp)
        
        # Left header: X = 26.0, Y from 20.0 to 73.34 (22 pins)
        left_nets = [
            ("3V3", "1"), ("EN", "2"), ("I2C_SDA", "3"), ("I2C_SCL", "4"),
            ("GPIO6", "5"), ("GPIO7", "6"), ("SERVO_PWM", "7"), ("HC_TRIG", "8"),
            ("HC_ECHO", "9"), ("MOTOR_L_IN1", "10"), ("GPIO8", "11"), ("GPIO3", "12"),
            ("GPIO46", "13"), ("GPIO9", "14"), ("GPIO10", "15"), ("GPIO11", "16"),
            ("GPIO12", "17"), ("GPIO13", "18"), ("GPIO14", "19"), ("+5V", "20"),
            ("GND", "21"), ("GND", "22")
        ]
        y_start = 20.0
        pitch = 2.54
        for idx, (net, pnum) in enumerate(left_nets):
            py = y_start + idx * pitch
            shape = "rect" if pnum == "1" else "circle"
            p = Pad(net=net, x=26.0, y=py, shape=shape, w=1.6, h=1.6, drill=0.9,
                    layer="All", pin_num=pnum, component="U1")
            self.pads.append(p)
            c_esp.pads.append(p)
            
        # Right header: X = 51.4, Y from 20.0 to 73.34 (22 pins)
        right_nets = [
            ("GND", "23"), ("TX", "24"), ("RX", "25"), ("VBAT_SENSE", "26"),
            ("STATUS_LED", "27"), ("GPIO42", "28"), ("GPIO41", "29"), ("GPIO40", "30"),
            ("GPIO39", "31"), ("GPIO38", "32"), ("GPIO37", "33"), ("GPIO36", "34"),
            ("GPIO35", "35"), ("GPIO0", "36"), ("GPIO45", "37"), ("GPIO48", "38"),
            ("GPIO47", "39"), ("MOTOR_R_IN2", "40"), ("MOTOR_R_IN1", "41"),
            ("MOTOR_L_IN2", "42"), ("GND", "43"), ("+5V", "44")
        ]
        for idx, (net, pnum) in enumerate(right_nets):
            py = y_start + idx * pitch
            shape = "circle"
            p = Pad(net=net, x=51.4, y=py, shape=shape, w=1.6, h=1.6, drill=0.9,
                    layer="All", pin_num=pnum, component="U1")
            self.pads.append(p)
            c_esp.pads.append(p)

        # U1 Silkscreen outline & antenna zone
        self._add_box_silk(23.5, 17.5, 53.9, 75.8)
        self.silk_texts.append(SilkText("ESP32-S3", 38.7, 72.0, size=1.8))
        self.silk_texts.append(SilkText("ANTENNA KEEP-OUT", 38.7, 74.0, size=1.0))
        # Draw antenna cross-hatch
        self.silk_lines.append(SilkLine(30.0, 73.5, 47.4, 73.5, width=0.15))

        # ----------------------------------------------------------------------
        # U2: TI DRV8833 Dual H-Bridge Motor Driver (SSOP-16 with Thermal Pad)
        # ----------------------------------------------------------------------
        c_drv = Component("U2", "DRV8833PWP", "HTSSOP-16_EP", 74.0, 42.0, 0,
                          "Dual H-Bridge Motor Driver 1.2A RMS / 2A Peak", "C50810")
        self.components.append(c_drv)
        
        # Left pins: X = 71.3, Y = 42.0 + (3.5 - i)*0.65 for i=0..7
        # Pins: 1:nSLEEP, 2:AOUT1, 3:AISEN, 4:AOUT2, 5:BOUT2, 6:BISEN, 7:BOUT1, 8:nFAULT
        drv_left = [
            ("3V3", "1"), ("MOTOR_L1", "2"), ("GND", "3"), ("MOTOR_L2", "4"),
            ("MOTOR_R2", "5"), ("GND", "6"), ("MOTOR_R1", "7"), ("3V3", "8")
        ]
        for i, (net, pnum) in enumerate(drv_left):
            py = 42.0 + (3.5 - i) * 0.65
            p = Pad(net=net, x=71.3, y=py, shape="rect", w=1.35, h=0.42, drill=0.0,
                    layer="F.Cu", pin_num=pnum, component="U2")
            self.pads.append(p)
            c_drv.pads.append(p)

        # Right pins: X = 76.7, Y = 42.0 + (i - 3.5)*0.65 for i=0..7
        # Pins: 9:BIN1, 10:BIN2, 11:VINT, 12:GND, 13:AIN2, 14:AIN1, 15:VCP, 16:VM
        drv_right = [
            ("MOTOR_R_IN1", "9"), ("MOTOR_R_IN2", "10"), ("VINT", "11"), ("GND", "12"),
            ("MOTOR_L_IN2", "13"), ("MOTOR_L_IN1", "14"), ("GND", "15"), ("VBAT_SW", "16")
        ]
        for i, (net, pnum) in enumerate(drv_right):
            py = 42.0 - (3.5 - i) * 0.65
            p = Pad(net=net, x=76.7, y=py, shape="rect", w=1.35, h=0.42, drill=0.0,
                    layer="F.Cu", pin_num=pnum, component="U2")
            self.pads.append(p)
            c_drv.pads.append(p)

        # DRV8833 Thermal Pad (3.4mm x 2.8mm) at (74.0, 42.0)
        p_ep = Pad(net="GND", x=74.0, y=42.0, shape="rect", w=3.4, h=2.8, drill=0.0,
                   layer="F.Cu", pin_num="EP", component="U2")
        self.pads.append(p_ep)
        c_drv.pads.append(p_ep)
        
        # 6 Thermal Vias connecting PowerPAD directly to bottom ground plane
        for vx in [-0.9, 0.9]:
            for vy in [-0.8, 0.0, 0.8]:
                self.vias.append(Via("GND", 74.0 + vx, 42.0 + vy, drill=0.3, pad=0.6))

        # Silkscreen box for U2
        self._add_box_silk(70.0, 39.0, 78.0, 45.0)
        self.silk_texts.append(SilkText("DRV8833", 74.0, 45.8, size=1.3))
        # Pin 1 dot
        self.silk_lines.append(SilkLine(70.4, 44.5, 70.4, 44.5, width=0.4))

        # ----------------------------------------------------------------------
        # U3: MP1584EN 3A DC-DC Buck Converter Module Footprint
        # ----------------------------------------------------------------------
        c_buck = Component("U3", "MP1584EN_3A", "MODULE_22x17mm", 15.0, 36.0, 0,
                           "High-Efficiency 3A DC-DC Step-Down Converter", "C14256")
        self.components.append(c_buck)
        buck_pads = [
            ("VBAT_SW", 11.5, 27.5, "IN+"),
            ("GND",     18.5, 27.5, "IN-"),
            ("+5V",     11.5, 44.5, "OUT+"),
            ("GND",     18.5, 44.5, "OUT-")
        ]
        for net, px, py, pnum in buck_pads:
            p = Pad(net=net, x=px, y=py, shape="rect", w=2.4, h=2.0, drill=1.2,
                    layer="All", pin_num=pnum, component="U3")
            self.pads.append(p)
            c_buck.pads.append(p)
        self._add_box_silk(9.0, 25.5, 21.0, 46.5)
        self.silk_texts.append(SilkText("MP1584EN", 15.0, 36.0, size=1.4))
        self.silk_texts.append(SilkText("5V BUCK", 15.0, 34.0, size=1.1))

        # ----------------------------------------------------------------------
        # U4: TP5100 2S Li-ion Battery Charger Module Footprint
        # ----------------------------------------------------------------------
        c_chg = Component("U4", "TP5100_2S", "MODULE_25x17mm", 15.0, 60.0, 0,
                          "2S 8.4V 2A Switching Li-ion Charger Subsystem", "C99321")
        self.components.append(c_chg)
        chg_pads = [
            ("VIN_CHG", 11.5, 52.5, "VIN+"),
            ("GND",     18.5, 52.5, "VIN-"),
            ("VBAT_RAW",11.5, 67.5, "BAT+"),
            ("GND",     18.5, 67.5, "BAT-")
        ]
        for net, px, py, pnum in chg_pads:
            p = Pad(net=net, x=px, y=py, shape="rect", w=2.4, h=2.0, drill=1.2,
                    layer="All", pin_num=pnum, component="U4")
            self.pads.append(p)
            c_chg.pads.append(p)
        self._add_box_silk(9.0, 50.5, 21.0, 69.5)
        self.silk_texts.append(SilkText("TP5100 2S", 15.0, 60.0, size=1.4))
        self.silk_texts.append(SilkText("CHARGER", 15.0, 58.0, size=1.1))

        # ----------------------------------------------------------------------
        # CONNECTORS: J1 to J8
        # ----------------------------------------------------------------------
        # J1: Left Motor (JST-XH 2-pin 2.50mm pitch)
        c_j1 = Component("J1", "JST-XH-2P", "JST_XH_B2B-XH-A_1x02_P2.50mm", 63.0, 15.0, 0,
                         "Motor Left N20 Output", "C157924")
        self.components.append(c_j1)
        p1 = Pad("MOTOR_L1", 61.75, 15.0, "rect", 1.8, 1.8, 1.0, "All", "1", "J1")
        p2 = Pad("MOTOR_L2", 64.25, 15.0, "circle", 1.8, 1.8, 1.0, "All", "2", "J1")
        self.pads.extend([p1, p2])
        c_j1.pads.extend([p1, p2])
        self._add_box_silk(59.5, 12.0, 66.5, 18.0)
        self.silk_texts.append(SilkText("MOTOR_L", 63.0, 9.5, size=1.2))

        # J2: Right Motor (JST-XH 2-pin 2.50mm pitch)
        c_j2 = Component("J2", "JST-XH-2P", "JST_XH_B2B-XH-A_1x02_P2.50mm", 83.0, 15.0, 0,
                         "Motor Right N20 Output", "C157924")
        self.components.append(c_j2)
        p1 = Pad("MOTOR_R1", 81.75, 15.0, "rect", 1.8, 1.8, 1.0, "All", "1", "J2")
        p2 = Pad("MOTOR_R2", 84.25, 15.0, "circle", 1.8, 1.8, 1.0, "All", "2", "J2")
        self.pads.extend([p1, p2])
        c_j2.pads.extend([p1, p2])
        self._add_box_silk(79.5, 12.0, 86.5, 18.0)
        self.silk_texts.append(SilkText("MOTOR_R", 83.0, 9.5, size=1.2))

        # J3: HC-SR04 Ultrasonic Sensor (JST-XH 4-pin 2.50mm pitch)
        c_j3 = Component("J3", "JST-XH-4P", "JST_XH_B4B-XH-A_1x04_P2.50mm", 65.0, 73.0, 0,
                         "HC-SR04 Ultrasonic Ranging Transceiver", "C157926")
        self.components.append(c_j3)
        hc_nets = [("+5V", "1"), ("HC_TRIG", "2"), ("HC_ECHO", "3"), ("GND", "4")]
        for idx, (net, pnum) in enumerate(hc_nets):
            px = 61.25 + idx * 2.5
            shape = "rect" if pnum == "1" else "circle"
            p = Pad(net, px, 73.0, shape, 1.8, 1.8, 1.0, "All", pnum, "J3")
            self.pads.append(p)
            c_j3.pads.append(p)
        self._add_box_silk(59.0, 70.0, 71.0, 76.0)
        self.silk_texts.append(SilkText("HC-SR04", 65.0, 77.5, size=1.2))

        # J4: SSD1306 OLED HUD (JST-XH 4-pin 2.50mm pitch)
        c_j4 = Component("J4", "JST-XH-4P", "JST_XH_B4B-XH-A_1x04_P2.50mm", 80.0, 73.0, 0,
                         "0.96 inch 128x64 I2C OLED HUD Display", "C157926")
        self.components.append(c_j4)
        oled_nets = [("GND", "1"), ("3V3", "2"), ("I2C_SCL", "3"), ("I2C_SDA", "4")]
        for idx, (net, pnum) in enumerate(oled_nets):
            px = 76.25 + idx * 2.5
            shape = "rect" if pnum == "1" else "circle"
            p = Pad(net, px, 73.0, shape, 1.8, 1.8, 1.0, "All", pnum, "J4")
            self.pads.append(p)
            c_j4.pads.append(p)
        self._add_box_silk(74.0, 70.0, 86.0, 76.0)
        self.silk_texts.append(SilkText("OLED HUD", 80.0, 77.5, size=1.2))

        # J5: SG90 Micro Servo Look-Ahead Turret (1x3 Pin Header 2.54mm pitch)
        c_j5 = Component("J5", "PINHD-1x3", "PinHeader_1x03_P2.54mm_Vertical", 48.0, 13.0, 0,
                         "SG90 Micro Servo Look-Ahead Scanner", "C22550")
        self.components.append(c_j5)
        servo_nets = [("GND", "1"), ("+5V", "2"), ("SERVO_PWM", "3")]
        for idx, (net, pnum) in enumerate(servo_nets):
            px = 45.46 + idx * 2.54
            shape = "rect" if pnum == "1" else "circle"
            p = Pad(net, px, 13.0, shape, 1.6, 1.6, 0.9, "All", pnum, "J5")
            self.pads.append(p)
            c_j5.pads.append(p)
        self._add_box_silk(43.5, 11.0, 52.5, 15.0)
        self.silk_texts.append(SilkText("SERVO", 48.0, 8.5, size=1.1))

        # J6: BME280 Environmental Sensor Header (1x4 Pin Header 2.54mm pitch)
        c_j6 = Component("J6", "PINHD-1x4", "PinHeader_1x04_P2.54mm_Vertical", 88.0, 56.0, 90,
                         "BME280 Temp/Pressure/Altitude Sensor", "C22551")
        self.components.append(c_j6)
        bme_nets = [("3V3", "1"), ("GND", "2"), ("I2C_SCL", "3"), ("I2C_SDA", "4")]
        for idx, (net, pnum) in enumerate(bme_nets):
            py = 52.19 + idx * 2.54
            shape = "rect" if pnum == "1" else "circle"
            p = Pad(net, 88.0, py, shape, 1.6, 1.6, 0.9, "All", pnum, "J6")
            self.pads.append(p)
            c_j6.pads.append(p)
        self._add_box_silk(86.0, 50.5, 90.0, 61.5)
        self.silk_texts.append(SilkText("BME280", 94.0, 56.0, size=1.1, angle=90))

        # J7: 2S Li-ion Battery Sled Terminal (JST-XH 2-pin 2.50mm pitch)
        c_j7 = Component("J7", "JST-XH-2P", "JST_XH_B2B-XH-A_1x02_P2.50mm", 34.0, 13.0, 0,
                         "2S 7.4V 18650 Battery Connector", "C157924")
        self.components.append(c_j7)
        p1 = Pad("VBAT_RAW", 32.75, 13.0, "rect", 1.8, 1.8, 1.0, "All", "1", "J7")
        p2 = Pad("GND",      35.25, 13.0, "circle", 1.8, 1.8, 1.0, "All", "2", "J7")
        self.pads.extend([p1, p2])
        c_j7.pads.extend([p1, p2])
        self._add_box_silk(30.5, 10.5, 37.5, 15.5)
        self.silk_texts.append(SilkText("2S_BAT", 34.0, 8.5, size=1.1))

        # J8: DC Charger Input (2-pin 2.54mm pitch)
        c_j8 = Component("J8", "PINHD-1x2", "PinHeader_1x02_P2.54mm_Vertical", 15.0, 13.0, 0,
                         "DC 9V-15V Charger Input Terminal", "C22549")
        self.components.append(c_j8)
        p1 = Pad("VIN_CHG", 13.73, 13.0, "rect", 1.8, 1.8, 1.0, "All", "1", "J8")
        p2 = Pad("GND",     16.27, 13.0, "circle", 1.8, 1.8, 1.0, "All", "2", "J8")
        self.pads.extend([p1, p2])
        c_j8.pads.extend([p1, p2])
        self._add_box_silk(11.5, 10.5, 18.5, 15.5)
        self.silk_texts.append(SilkText("DC_IN", 15.0, 8.5, size=1.1))

        # SW1: Master Power SPDT Slide Switch
        c_sw = Component("SW1", "SPDT_SWITCH", "Switch_Slide_1P2T_P2.54mm", 41.0, 13.0, 0,
                         "Master Power Toggle Switch", "C319024")
        self.components.append(c_sw)
        sw_nets = [("VBAT_RAW", "1"), ("VBAT_SW", "2"), ("NC", "3")]
        for idx, (net, pnum) in enumerate(sw_nets):
            px = 39.73 + idx * 2.54
            shape = "rect" if pnum == "1" else "circle"
            p = Pad(net, px, 13.0, shape, 1.6, 1.6, 0.9, "All", pnum, "SW1")
            self.pads.append(p)
            c_sw.pads.append(p)
        self._add_box_silk(38.0, 10.5, 46.0, 15.5)
        self.silk_texts.append(SilkText("PWR_SW", 42.0, 17.0, size=1.1))

        # ----------------------------------------------------------------------
        # PASSIVES: C1..C6, R1..R6, D1..D2
        # ----------------------------------------------------------------------
        # C1: 100uF 16V Electrolytic Bulk Cap for DRV8833
        c_c1 = Component("C1", "100uF_16V", "CP_Radial_D6.3mm_P2.50mm", 74.0, 26.0, 0,
                         "Electrolytic Bulk Decoupling Capacitor", "C3288")
        self.components.append(c_c1)
        p1 = Pad("VBAT_SW", 72.75, 26.0, "rect", 1.8, 1.8, 0.9, "All", "1", "C1")
        p2 = Pad("GND",     75.25, 26.0, "circle", 1.8, 1.8, 0.9, "All", "2", "C1")
        self.pads.extend([p1, p2])
        c_c1.pads.extend([p1, p2])
        self.silk_texts.append(SilkText("C1 100uF", 74.0, 29.0, size=1.0))

        # C2: 10uF 1206 Ceramic Cap for VM
        self._add_smd_passive("C2", "10uF", "1206", 74.0, 32.0, "VBAT_SW", "GND", "C15850")
        # C3: 10uF 1206 Ceramic Cap for 5V Rail
        self._add_smd_passive("C3", "10uF", "1206", 11.5, 48.0, "+5V", "GND", "C15850")
        # C4: 0.1uF 0805 Decoupling Cap for VINT
        self._add_smd_passive("C4", "0.1uF", "0805", 79.5, 42.0, "VINT", "GND", "C49678")
        # C5: 0.1uF 0805 Decoupling Cap for 3.3V
        self._add_smd_passive("C5", "0.1uF", "0805", 26.0, 16.0, "3V3", "GND", "C49678")

        # R1, R2: 4.7k 0805 I2C Pullups
        self._add_smd_passive("R1", "4.7k", "0805", 84.0, 67.0, "3V3", "I2C_SCL", "C25900")
        self._add_smd_passive("R2", "4.7k", "0805", 84.0, 64.0, "3V3", "I2C_SDA", "C25900")

        # R3, R4: 100k 0805 Battery Voltage Divider
        self._add_smd_passive("R3", "100k", "0805", 48.0, 28.0, "VBAT_RAW", "VBAT_SENSE", "C25803")
        self._add_smd_passive("R4", "100k", "0805", 48.0, 25.0, "VBAT_SENSE", "GND", "C25803")

        # D1: Power LED (Green) + R5 (1k)
        self._add_smd_passive("R5", "1k", "0805", 22.0, 16.0, "+5V", "NET_LED_PWR", "C17513")
        self._add_smd_passive("D1", "LED_GRN", "0805", 22.0, 13.0, "NET_LED_PWR", "GND", "C84256")
        self.silk_texts.append(SilkText("PWR", 22.0, 10.5, size=0.9))

        # D2: Status LED (Blue) + R6 (1k)
        self._add_smd_passive("R6", "1k", "0805", 26.0, 13.0, "STATUS_LED", "NET_LED_STAT", "C17513")
        self._add_smd_passive("D2", "LED_BLU", "0805", 26.0, 10.5, "NET_LED_STAT", "GND", "C84267")
        self.silk_texts.append(SilkText("STAT", 26.0, 8.5, size=0.9))

    def _add_smd_passive(self, ref, val, pkg, cx, cy, net1, net2, lcsc=""):
        c = Component(ref, val, f"R_{pkg}_2012Metric", cx, cy, 0, f"{ref} {val}", lcsc)
        self.components.append(c)
        # 0805 / 1206 pad spacing
        dx = 0.95 if pkg == "0805" else 1.45
        pw = 1.0 if pkg == "0805" else 1.2
        ph = 1.25 if pkg == "0805" else 1.6
        p1 = Pad(net1, cx - dx, cy, "rect", pw, ph, 0.0, "F.Cu", "1", ref)
        p2 = Pad(net2, cx + dx, cy, "rect", pw, ph, 0.0, "F.Cu", "2", ref)
        self.pads.extend([p1, p2])
        c.pads.extend([p1, p2])
        # Silk outline
        self._add_box_silk(cx - dx - pw/2 - 0.2, cy - ph/2 - 0.2,
                           cx + dx + pw/2 + 0.2, cy + ph/2 + 0.2)
        self.silk_texts.append(SilkText(ref, cx, cy + ph/2 + 0.8, size=0.9))

    def _add_box_silk(self, x1, y1, x2, y2):
        self.silk_lines.extend([
            SilkLine(x1, y1, x2, y1),
            SilkLine(x2, y1, x2, y2),
            SilkLine(x2, y2, x1, y2),
            SilkLine(x1, y2, x1, y1)
        ])

    def _route_tracks(self):
        """
        High-precision multi-segment track routing with wide power traces (>= 30 mil).
        Signal traces: 12 mil (0.305 mm).
        Power traces: 35 mil (0.889 mm) to 45 mil (1.143 mm).
        """
        # ======================================================================
        # POWER ROUTING (>= 30 mil / 0.762 mm)
        # ======================================================================
        w_vbat = 1.143   # 45 mil (High-current battery rail)
        w_5v   = 0.889   # 35 mil (+5V regulated rail)
        w_3v3  = 0.635   # 25 mil (+3.3V logic rail)
        w_mot  = 0.889   # 35 mil (Motor drive H-bridge outputs)
        w_sig  = 0.305   # 12 mil (High-speed digital signals)

        # 1. VBAT_RAW: J7 (Battery) -> SW1 (Switch Pin 1) -> TP5100 BAT+
        self._add_wire("VBAT_RAW", [(32.75, 13.0), (32.75, 18.0), (39.73, 18.0), (39.73, 13.0)], w_vbat)
        self._add_wire("VBAT_RAW", [(32.75, 18.0), (22.0, 18.0), (22.0, 67.5), (11.5, 67.5)], w_vbat, layer="B.Cu")
        # Vias for battery layer transition
        self.vias.append(Via("VBAT_RAW", 32.75, 18.0))
        self.vias.append(Via("VBAT_RAW", 11.5, 67.5))

        # 2. VIN_CHG: J8 (DC In) -> TP5100 VIN+
        self._add_wire("VIN_CHG", [(13.73, 13.0), (8.5, 13.0), (8.5, 52.5), (11.5, 52.5)], w_vbat)

        # 3. VBAT_SW: SW1 Pin 2 -> MP1584 Buck IN+ (11.5, 27.5) & DRV8833 VM (76.7, 39.72) & C1 (72.75, 26.0)
        self._add_wire("VBAT_SW", [(42.27, 13.0), (42.27, 22.0), (11.5, 22.0), (11.5, 27.5)], w_vbat)
        self._add_wire("VBAT_SW", [(42.27, 22.0), (72.75, 22.0), (72.75, 26.0)], w_vbat)
        self._add_wire("VBAT_SW", [(72.75, 26.0), (74.0, 32.0 - 1.45), (76.7, 32.0), (76.7, 39.72)], w_vbat)

        # 4. +5V: MP1584 Buck OUT+ (11.5, 44.5) -> ESP32 5V (26.0, 68.26) & Servo J5 (48.0, 13.0) & HC-SR04 J3 (61.25, 73.0)
        self._add_wire("+5V", [(11.5, 44.5), (11.5, 48.0), (22.0, 48.0), (22.0, 68.26), (26.0, 68.26)], w_5v)
        self._add_wire("+5V", [(22.0, 68.26), (22.0, 78.0), (61.25, 78.0), (61.25, 73.0)], w_5v)
        self._add_wire("+5V", [(22.0, 48.0), (22.0, 18.0), (48.0, 18.0), (48.0, 13.0)], w_5v, layer="B.Cu")
        self.vias.append(Via("+5V", 22.0, 48.0))
        self.vias.append(Via("+5V", 48.0, 18.0))

        # 5. +3V3: ESP32 Pin 1 (26.0, 20.0) -> OLED J4 (78.75, 73.0) & BME280 J6 (88.0, 52.19) & I2C Pullups
        self._add_wire("3V3", [(26.0, 20.0), (26.0, 16.0)], w_3v3)
        self._add_wire("3V3", [(26.0, 20.0), (23.5, 20.0), (23.5, 8.0), (78.75, 8.0), (78.75, 65.0), (78.75, 73.0)], w_3v3, layer="B.Cu")
        self.vias.append(Via("3V3", 26.0, 20.0))
        self.vias.append(Via("3V3", 78.75, 73.0))
        self._add_wire("3V3", [(78.75, 52.19), (88.0, 52.19)], w_3v3)
        self._add_wire("3V3", [(78.75, 65.0), (84.0 - 0.95, 65.0)], w_3v3)
        self._add_wire("3V3", [(84.0 - 0.95, 65.0), (84.0 - 0.95, 67.0)], w_3v3)
        # 3.3V to DRV8833 nSLEEP (Pin 1: 71.3, 44.27) & nFAULT pullup (Pin 8: 71.3, 39.72)
        self._add_wire("3V3", [(71.3, 44.27), (69.0, 44.27), (69.0, 39.72), (71.3, 39.72)], w_3v3)
        self._add_wire("3V3", [(69.0, 44.27), (69.0, 52.19), (78.75, 52.19)], w_3v3)

        # ======================================================================
        # MOTOR DRIVE H-BRIDGE HIGH CURRENT OUTPUTS (35 mil / 0.889 mm)
        # ======================================================================
        # Left Motor: DRV8833 AOUT1 (71.3, 43.62) -> J1 Pin 1 (61.75, 15.0)
        self._add_wire("MOTOR_L1", [(71.3, 43.62), (65.0, 43.62), (65.0, 20.0), (61.75, 20.0), (61.75, 15.0)], w_mot)
        # Left Motor: DRV8833 AOUT2 (71.3, 42.32) -> J1 Pin 2 (64.25, 15.0)
        self._add_wire("MOTOR_L2", [(71.3, 42.32), (66.5, 42.32), (66.5, 21.0), (64.25, 21.0), (64.25, 15.0)], w_mot)

        # Right Motor: DRV8833 BOUT1 (71.3, 40.37) -> J2 Pin 1 (81.75, 15.0)
        self._add_wire("MOTOR_R1", [(71.3, 40.37), (70.0, 40.37), (70.0, 20.0), (81.75, 20.0), (81.75, 15.0)], w_mot, layer="B.Cu")
        self.vias.append(Via("MOTOR_R1", 71.3, 40.37))
        self.vias.append(Via("MOTOR_R1", 81.75, 15.0))
        # Right Motor: DRV8833 BOUT2 (71.3, 41.67) -> J2 Pin 2 (84.25, 15.0)
        self._add_wire("MOTOR_R2", [(71.3, 41.67), (68.5, 41.67), (68.5, 19.0), (84.25, 19.0), (84.25, 15.0)], w_mot, layer="B.Cu")
        self.vias.append(Via("MOTOR_R2", 71.3, 41.67))
        self.vias.append(Via("MOTOR_R2", 84.25, 15.0))

        # ======================================================================
        # SIGNAL ROUTING (12 mil / 0.305 mm)
        # ======================================================================
        # Motor Control Inputs from ESP32:
        # MOTOR_L_IN1: ESP32 IO18 (26.0, 42.86) -> DRV8833 AIN1 (76.7, 41.02)
        self._add_wire("MOTOR_L_IN1", [(26.0, 42.86), (30.0, 42.86), (30.0, 36.0), (82.0, 36.0), (82.0, 41.02), (76.7, 41.02)], w_sig, layer="B.Cu")
        self.vias.append(Via("MOTOR_L_IN1", 26.0, 42.86))
        self.vias.append(Via("MOTOR_L_IN1", 76.7, 41.02))

        # MOTOR_L_IN2: ESP32 IO19 (51.4, 68.26) -> DRV8833 AIN2 (76.7, 41.67)
        self._add_wire("MOTOR_L_IN2", [(51.4, 68.26), (58.0, 68.26), (58.0, 45.0), (79.0, 45.0), (79.0, 41.67), (76.7, 41.67)], w_sig)

        # MOTOR_R_IN1: ESP32 IO20 (51.4, 65.72) -> DRV8833 BIN1 (76.7, 39.07)
        self._add_wire("MOTOR_R_IN1", [(51.4, 65.72), (60.0, 65.72), (60.0, 39.07), (76.7, 39.07)], w_sig)

        # MOTOR_R_IN2: ESP32 IO21 (51.4, 63.18) -> DRV8833 BIN2 (76.7, 39.72)
        self._add_wire("MOTOR_R_IN2", [(51.4, 63.18), (62.0, 63.18), (62.0, 39.72), (76.7, 39.72)], w_sig)

        # SERVO_PWM: ESP32 IO15 (26.0, 35.24) -> Servo J5 Pin 3 (50.54, 13.0)
        self._add_wire("SERVO_PWM", [(26.0, 35.24), (28.0, 35.24), (28.0, 10.0), (50.54, 10.0), (50.54, 13.0)], w_sig)

        # HC_TRIG: ESP32 IO16 (26.0, 37.78) -> HC-SR04 J3 Pin 2 (63.75, 73.0)
        self._add_wire("HC_TRIG", [(26.0, 37.78), (24.0, 37.78), (24.0, 62.0), (63.75, 62.0), (63.75, 73.0)], w_sig, layer="B.Cu")
        self.vias.append(Via("HC_TRIG", 26.0, 37.78))
        self.vias.append(Via("HC_TRIG", 63.75, 73.0))

        # HC_ECHO: ESP32 IO17 (26.0, 40.32) -> HC-SR04 J3 Pin 3 (66.25, 73.0)
        self._add_wire("HC_ECHO", [(26.0, 40.32), (23.0, 40.32), (23.0, 64.0), (66.25, 64.0), (66.25, 73.0)], w_sig, layer="B.Cu")
        self.vias.append(Via("HC_ECHO", 26.0, 40.32))
        self.vias.append(Via("HC_ECHO", 66.25, 73.0))

        # I2C_SCL: ESP32 IO5 (26.0, 27.62) -> OLED J4 Pin 3 (81.25, 73.0) & BME280 J6 Pin 3 (88.0, 57.27)
        self._add_wire("I2C_SCL", [(26.0, 27.62), (24.0, 27.62), (24.0, 50.0), (81.25, 50.0), (81.25, 73.0)], w_sig, layer="B.Cu")
        self.vias.append(Via("I2C_SCL", 26.0, 27.62))
        self.vias.append(Via("I2C_SCL", 81.25, 73.0))
        self._add_wire("I2C_SCL", [(81.25, 57.27), (88.0, 57.27)], w_sig)

        # I2C_SDA: ESP32 IO4 (26.0, 25.08) -> OLED J4 Pin 4 (83.75, 73.0) & BME280 J6 Pin 4 (88.0, 59.81)
        self._add_wire("I2C_SDA", [(26.0, 25.08), (23.0, 25.08), (23.0, 49.0), (83.75, 49.0), (83.75, 73.0)], w_sig, layer="B.Cu")
        self.vias.append(Via("I2C_SDA", 26.0, 25.08))
        self.vias.append(Via("I2C_SDA", 83.75, 73.0))
        self._add_wire("I2C_SDA", [(83.75, 59.81), (88.0, 59.81)], w_sig)

        # STATUS_LED: ESP32 IO2 (51.4, 30.16) -> R6 (26.0, 13.0)
        self._add_wire("STATUS_LED", [(51.4, 30.16), (51.4, 25.0), (28.0, 25.0), (28.0, 13.0), (26.95, 13.0)], w_sig)

        # VBAT_SENSE: Divider tap (48.0, 26.5) -> ESP32 IO1 (51.4, 27.62)
        self._add_wire("VBAT_SENSE", [(48.0, 26.5), (50.0, 26.5), (50.0, 27.62), (51.4, 27.62)], w_sig)

        # VINT DRV8833 bypass cap C4: Pin 11 (76.7, 40.37) -> C4 (79.5 - 0.95, 42.0)
        self._add_wire("VINT", [(76.7, 40.37), (78.55, 40.37), (78.55, 42.0)], w_sig)

    def _add_wire(self, net, pts, width, layer="F.Cu"):
        for i in range(len(pts) - 1):
            p_start = pts[i]
            p_end = pts[i + 1]
            self.tracks.append(Track(net, p_start[0], p_start[1], p_end[0], p_end[1], width, layer))

    def _build_ground_stitching(self):
        """
        Distributes ground stitching vias across board perimeter and central areas
        to stitch Top and Bottom Ground Planes into a unified low-inductance cage.
        """
        # Outer grid perimeter vias
        x_steps = [15.0, 30.0, 45.0, 60.0, 75.0, 85.0]
        y_steps = [6.0, 74.0]
        for y in y_steps:
            for x in x_steps:
                self.vias.append(Via("GND", x, y))
                
        # Lateral perimeter vias
        for y in [20.0, 35.0, 50.0, 65.0]:
            self.vias.append(Via("GND", 5.0, y))
            self.vias.append(Via("GND", 95.0, y))
            
        # Interior stitching near MCU, Buck, and Drivers
        interior_vias = [
            (21.0, 22.0), (38.0, 21.0), (38.0, 70.0), (55.0, 22.0),
            (55.0, 50.0), (55.0, 70.0), (68.0, 55.0), (82.0, 27.0),
            (88.0, 45.0), (88.0, 68.0)
        ]
        for ix, iy in interior_vias:
            self.vias.append(Via("GND", ix, iy))

    def _build_silkscreen_legends(self):
        # Board Title & Hack Club Grounded Attribution
        self.silk_texts.append(SilkText("TERRASCOUT GROUNDED", 50.0, 3.5, size=2.0))
        self.silk_texts.append(SilkText("AUTONOMOUS TELEMETRY ROVER - PCB REV 1.0", 50.0, 1.8, size=1.0))
        self.silk_texts.append(SilkText("HACK CLUB GROUNDED", 8.0, 3.5, size=1.1, angle=90))
        self.silk_texts.append(SilkText("CERN-OHL-P v2 / MIT", 92.0, 3.5, size=1.1, angle=90))
        
        # M3 Bolt Pattern Legend
        self.silk_texts.append(SilkText("80x60 M3 MOUNT", 50.0, 77.5, size=1.0))
        
        # Decorative rover logo / icon in silk
        self._add_rover_silk_icon(5.0, 70.0)

    def _add_rover_silk_icon(self, cx, cy):
        # Tiny stylized rover glyph
        self.silk_lines.append(SilkLine(cx - 2, cy - 1, cx + 2, cy - 1, width=0.25))
        self.silk_lines.append(SilkLine(cx - 2, cy + 1, cx + 2, cy + 1, width=0.25))
        self.silk_lines.append(SilkLine(cx - 1.5, cy - 2, cx - 1.5, cy + 2, width=0.3))
        self.silk_lines.append(SilkLine(cx + 1.5, cy - 2, cx + 1.5, cy + 2, width=0.3))

print("[*] TerraScout PCB Model configured.")
