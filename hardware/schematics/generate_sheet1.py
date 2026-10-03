import os
import sys

sys.path.append('C:/Users/white/terrascout-grounded/hardware/schematics')
from schematic_builder import SchematicSheet

def build_refined_sheet1():
    s = SchematicSheet("Sheet 1: Power Management & Battery Subsystem", "11111111-1111-1111-1111-111111111111", "00000000-0000-0000-0000-000000000000", "terrascout")

    # Title Banner
    s.add_text("TERRASCOUT POWER MANAGEMENT & BATTERY SUBSYSTEM", 25.4, 15.24, size=2.54, bold=True)
    s.add_text("2S 7.4V Li-ion (18650) | TP5100 2A Balance Charger | MP1584EN 5V 3A Buck | AMS1117-3.3 LDO | P-MOSFET Reverse Protection", 25.4, 21.59, size=1.52, bold=False)

    # =========================================================================
    # 1. 2S 18650 Battery Connector & Balance Tap
    # =========================================================================
    s.add_text("1. 2S 18650 BATTERY INPUT & BALANCE TAP", 25.4, 33.02, size=1.52, bold=True)
    
    # J1: 2-pin screw terminal at (40.64, 45.72)
    # Pin 1 at (35.56, 45.72), Pin 2 at (35.56, 48.26)
    j1 = s.add_symbol("Connector_Generic:Conn_01x02", "J1", "2S_18650_7.4V_IN", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", 40.64, 45.72)
    j1.add_pin("1")
    j1.add_pin("2")
    s.add_wire(35.56, 45.72, 27.94, 45.72)
    s.add_global_label("+BATT", 27.94, 45.72, angle=180)
    s.add_wire(35.56, 48.26, 27.94, 48.26)
    s.add_symbol("power:GND", "#PWR101", "GND", "", 27.94, 48.26)

    # J2: 3-pin Balance Connector at (40.64, 60.96)
    # Pin 1 at (35.56, 58.42), Pin 2 at (35.56, 60.96), Pin 3 at (35.56, 63.50)
    j2 = s.add_symbol("Connector_Generic:Conn_01x03", "J2", "JST_XH_2S_BAL", "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical", 40.64, 60.96)
    j2.add_pin("1")
    j2.add_pin("2")
    j2.add_pin("3")
    s.add_wire(35.56, 58.42, 27.94, 58.42)
    s.add_symbol("power:GND", "#PWR102", "GND", "", 27.94, 58.42)
    s.add_wire(35.56, 60.96, 27.94, 60.96)
    s.add_global_label("CELL_MID", 27.94, 60.96, angle=180)
    s.add_wire(35.56, 63.50, 27.94, 63.50)
    s.add_global_label("+BATT", 27.94, 63.50, angle=180)

    # =========================================================================
    # 2. TP5100 2S 2A Switching Li-ion Charger
    # =========================================================================
    s.add_text("2. TP5100 2S 8.4V 2A SWITCHING CHARGER", 68.58, 33.02, size=1.52, bold=True)
    
    # DC Barrel Jack J3 at (76.2, 45.72)
    j3 = s.add_symbol("Connector_Generic:Conn_01x02", "J3", "DC_IN_9-15V", "Connector_BarrelJack:BarrelJack_Horizontal", 76.2, 45.72)
    j3.add_pin("1")
    j3.add_pin("2")
    s.add_wire(71.12, 45.72, 63.5, 45.72)
    s.add_global_label("VIN_CHG", 63.5, 45.72, angle=180)
    # Power flag for VIN_CHG to satisfy ERC
    s.add_symbol("power:PWR_FLAG", "#FLG100", "PWR_FLAG", "", 63.5, 45.72)
    s.add_wire(71.12, 48.26, 63.5, 48.26)
    s.add_symbol("power:GND", "#PWR103", "GND", "", 63.5, 48.26)

    # TP5100 U1 at (114.3, 60.96)
    u1 = s.add_symbol("terrascout_custom:TP5100", "U1", "TP5100_2S_2A", "Package_DFN_QFN:QFN-16-1EP_4x4mm_P0.65mm_EP2.5x2.5mm", 114.3, 60.96)
    for p in range(1, 18):
        u1.add_pin(str(p))

    # VIN bus at X=93.98, from Y=50.8 to Y=60.96
    s.add_wire(99.06, 50.8, 93.98, 50.8)   # Pin 1 PWR_ON
    s.add_wire(99.06, 58.42, 93.98, 58.42) # Pin 5 VIN
    s.add_wire(99.06, 60.96, 93.98, 60.96) # Pin 6 VIN
    s.add_wire(93.98, 50.8, 93.98, 60.96)
    s.add_junction(93.98, 50.8)
    s.add_junction(93.98, 58.42)
    s.add_wire(93.98, 50.8, 86.36, 50.8)
    s.add_global_label("VIN_CHG", 86.36, 50.8, angle=180)

    # Input Decoupling C1 (10µF) at (88.9, 60.96)
    c1 = s.add_symbol("Device:C", "C1", "10uF_25V", "Capacitor_SMD:C_1206_3216Metric", 88.9, 60.96)
    c1.add_pin("1")
    c1.add_pin("2")
    s.add_wire(88.9, 50.8, 88.9, 57.15)
    s.add_junction(88.9, 50.8)
    s.add_wire(88.9, 64.77, 88.9, 68.58)
    s.add_symbol("power:GND", "#PWR104", "GND", "", 88.9, 68.58)

    # CS_SET Pin 2 (99.06, 53.34) tied to VREG Pin 13 (99.06, 66.04) for 2S mode
    s.add_wire(99.06, 53.34, 96.52, 53.34)
    s.add_wire(96.52, 53.34, 96.52, 66.04)
    s.add_wire(96.52, 66.04, 99.06, 66.04)
    s.add_junction(96.52, 66.04)

    # VREG C3 (100nF) at (96.52, 73.66)
    c3 = s.add_symbol("Device:C", "C3", "100nF", "Capacitor_SMD:C_0805_2012Metric", 96.52, 73.66)
    c3.add_pin("1")
    c3.add_pin("2")
    s.add_wire(96.52, 66.04, 96.52, 69.85)
    s.add_wire(96.52, 77.47, 96.52, 80.01)
    s.add_symbol("power:GND", "#PWR105", "GND", "", 96.52, 80.01)

    # Indicator LEDs:
    # Pin 14 (~CHRG): (99.06, 71.12) -> Red LED D2 + R1 (1k) to VIN_CHG
    d2 = s.add_symbol("Device:LED", "D2", "LED_CHG_RED", "LED_SMD:LED_0805_2012Metric", 83.82, 71.12)
    d2.add_pin("1") # K at 83.82 - 3.81 = 80.01
    d2.add_pin("2") # A at 83.82 + 3.81 = 87.63
    s.add_wire(99.06, 71.12, 80.01, 71.12)
    r1 = s.add_symbol("Device:R", "R1", "1k", "Resistor_SMD:R_0805_2012Metric", 71.12, 71.12, angle=90)
    r1.add_pin("1") # at 71.12 - 3.81 = 67.31
    r1.add_pin("2") # at 71.12 + 3.81 = 74.93
    s.add_wire(87.63, 71.12, 74.93, 71.12)
    s.add_wire(67.31, 71.12, 60.96, 71.12)
    s.add_global_label("VIN_CHG", 60.96, 71.12, angle=180)

    # Pin 15 (~STDBY): (99.06, 73.66) -> Blue/Green LED D3 + R2 (1k) to VIN_CHG
    d3 = s.add_symbol("Device:LED", "D3", "LED_DONE_BLUE", "LED_SMD:LED_0805_2012Metric", 83.82, 78.74)
    d3.add_pin("1") # K at 80.01
    d3.add_pin("2") # A at 87.63
    s.add_wire(99.06, 73.66, 80.01, 73.66)
    s.add_wire(80.01, 73.66, 80.01, 78.74)
    r2 = s.add_symbol("Device:R", "R2", "1k", "Resistor_SMD:R_0805_2012Metric", 71.12, 78.74, angle=90)
    r2.add_pin("1") # at 67.31
    r2.add_pin("2") # at 74.93
    s.add_wire(87.63, 78.74, 74.93, 78.74)
    s.add_wire(67.31, 78.74, 60.96, 78.74)
    s.add_global_label("VIN_CHG", 60.96, 78.74, angle=180)

    # Temperature Sense TS Pin 16 (129.54, 73.66) tied to GND via R3 (10k)
    r3 = s.add_symbol("Device:R", "R3", "10k", "Resistor_SMD:R_0805_2012Metric", 137.16, 73.66, angle=90)
    r3.add_pin("1") # at 133.35
    r3.add_pin("2") # at 140.97
    s.add_wire(129.54, 73.66, 133.35, 73.66)
    s.add_wire(140.97, 73.66, 147.32, 73.66)
    s.add_symbol("power:GND", "#PWR106", "GND", "", 147.32, 73.66)

    # TP5100 GND pins: Pin 3, 4, 17
    s.add_wire(114.3, 80.01, 114.3, 83.82)
    s.add_wire(116.84, 80.01, 116.84, 83.82)
    s.add_wire(111.76, 80.01, 111.76, 83.82)
    s.add_wire(111.76, 83.82, 116.84, 83.82)
    s.add_junction(114.3, 83.82)
    s.add_symbol("power:GND", "#PWR107", "GND", "", 114.3, 83.82)

    # Output SW node: Pin 7, 8 (129.54, 50.8 and 53.34)
    s.add_wire(129.54, 50.8, 134.62, 50.8)
    s.add_wire(129.54, 53.34, 134.62, 53.34)
    s.add_wire(134.62, 50.8, 134.62, 53.34)
    s.add_junction(134.62, 50.8)

    # Catch Diode D1 (SS34) at (134.62, 60.96) angle 270:
    # Pin 1 (K) at (134.62, 57.15), Pin 2 (A) at (134.62, 64.77)
    d1 = s.add_symbol("Device:D_Schottky", "D1", "SS34_3A", "Diode_SMD:D_SMA", 134.62, 60.96, angle=270)
    d1.add_pin("1")
    d1.add_pin("2")
    s.add_wire(134.62, 50.8, 134.62, 57.15)
    s.add_wire(134.62, 64.77, 134.62, 68.58)
    s.add_symbol("power:GND", "#PWR108", "GND", "", 134.62, 68.58)

    # Inductor L1 (10µH 3A) at (144.78, 50.8) angle 90:
    # Pin 1 at 140.97, Pin 2 at 148.59
    l1 = s.add_symbol("Device:L", "L1", "10uH_3A", "Inductor_SMD:L_12x12mm_H6mm", 144.78, 50.8, angle=90)
    l1.add_pin("1")
    l1.add_pin("2")
    s.add_wire(134.62, 50.8, 140.97, 50.8)

    # Sense Resistor R4 (0.05Ω 1W) at (157.48, 50.8) angle 90:
    # Pin 1 at 153.67, Pin 2 at 161.29
    r4 = s.add_symbol("Device:R", "R4", "0.05R_1W_1%", "Resistor_SMD:R_1206_3216Metric", 157.48, 50.8, angle=90)
    r4.add_pin("1")
    r4.add_pin("2")
    s.add_wire(148.59, 50.8, 153.67, 50.8)

    # BAT Pin 9, 10 (129.54, 58.42 and 60.96) connect between L1 and R4 at X=151.13
    s.add_wire(129.54, 58.42, 151.13, 58.42)
    s.add_wire(129.54, 60.96, 151.13, 60.96)
    s.add_wire(151.13, 58.42, 151.13, 60.96)
    s.add_wire(151.13, 50.8, 151.13, 58.42)
    s.add_junction(151.13, 50.8)
    s.add_junction(151.13, 58.42)

    # CS Pin 11, 12 (129.54, 66.04 and 68.58) connect after R4 at X=162.56
    s.add_wire(129.54, 66.04, 162.56, 66.04)
    s.add_wire(129.54, 68.58, 162.56, 68.58)
    s.add_wire(162.56, 66.04, 162.56, 68.58)
    s.add_wire(161.29, 50.8, 162.56, 50.8)
    s.add_wire(162.56, 50.8, 162.56, 66.04)
    s.add_junction(162.56, 50.8)
    s.add_junction(162.56, 66.04)

    # Output Filter C4 (10µF) at (167.64, 60.96)
    c4 = s.add_symbol("Device:C", "C4", "10uF_16V", "Capacitor_SMD:C_1206_3216Metric", 167.64, 60.96)
    c4.add_pin("1")
    c4.add_pin("2")
    s.add_wire(162.56, 50.8, 167.64, 50.8)
    s.add_junction(167.64, 50.8)
    s.add_wire(167.64, 50.8, 167.64, 57.15)
    s.add_wire(167.64, 64.77, 167.64, 68.58)
    s.add_symbol("power:GND", "#PWR109", "GND", "", 167.64, 68.58)

    # Output to +BATT
    s.add_wire(167.64, 50.8, 175.26, 50.8)
    s.add_global_label("+BATT", 175.26, 50.8, angle=0)

    # =========================================================================
    # 3. Reverse Polarity Protection Circuit (AO3401A P-MOSFET)
    # =========================================================================
    s.add_text("3. REVERSE POLARITY P-MOSFET ISOLATION", 193.04, 33.02, size=1.52, bold=True)
    
    # Q1: AO3401A at (213.36, 50.8)
    # Pin 1 (G) at (208.28, 50.8)
    # Pin 2 (S) at (215.9, 54.61)
    # Pin 3 (D) at (215.9, 46.99)
    q1 = s.add_symbol("terrascout_custom:AO3401A", "Q1", "AO3401A_PMOS", "Package_TO_SOT_SMD:SOT-23", 213.36, 50.8)
    q1.add_pin("1")
    q1.add_pin("2")
    q1.add_pin("3")

    # +BATT input to Source (215.9, 54.61)
    s.add_wire(198.12, 54.61, 215.9, 54.61)
    s.add_global_label("+BATT", 198.12, 54.61, angle=180)

    # Drain (215.9, 46.99) to +V_BATT_PROT
    s.add_wire(215.9, 46.99, 228.6, 46.99)
    s.add_global_label("+V_BATT_PROT", 228.6, 46.99, angle=0)

    # Gate (208.28, 50.8) pull-down R5 (100k) to GND at (203.2, 60.96)
    r5 = s.add_symbol("Device:R", "R5", "100k", "Resistor_SMD:R_0805_2012Metric", 203.2, 60.96)
    r5.add_pin("1") # at 57.15
    r5.add_pin("2") # at 64.77
    s.add_wire(208.28, 50.8, 203.2, 50.8)
    s.add_junction(208.28, 50.8)
    s.add_wire(203.2, 50.8, 203.2, 57.15)
    s.add_wire(203.2, 64.77, 203.2, 68.58)
    s.add_symbol("power:GND", "#PWR110", "GND", "", 203.2, 68.58)

    # 12V Zener D4 at (208.28, 60.96) angle 90:
    # In Device:D_Zener, pin 1 is K at (-3.81, 0), pin 2 is A at (3.81, 0).
    # When angle=90: Pin 1 (K) is at (Sx - Py, Sy - Px) = (208.28, 60.96 - (-3.81)) = (208.28, 64.77)!
    # Pin 2 (A) is at (208.28, 57.15)!
    # Gate is at 50.8, so Gate connects to Anode (57.15).
    # Source is at 54.61 (connected to Cathode at 64.77 via wire).
    d4 = s.add_symbol("Device:D_Zener", "D4", "BZX84C12_12V", "Diode_SMD:D_SOD-323", 208.28, 60.96, angle=90)
    d4.add_pin("1")
    d4.add_pin("2")
    s.add_wire(208.28, 50.8, 208.28, 57.15) # Gate to Anode
    s.add_wire(208.28, 64.77, 208.28, 68.58) # Cathode to Source line
    s.add_wire(208.28, 68.58, 215.9, 68.58)
    s.add_wire(215.9, 68.58, 215.9, 54.61)
    s.add_junction(215.9, 54.61)

    # =========================================================================
    # 4. Master Power Switch & Power Rail
    # =========================================================================
    s.add_text("4. MASTER POWER SWITCH & POWER BUS", 243.84, 33.02, size=1.52, bold=True)
    
    # SW1 at (261.62, 45.72)
    # Common is pin 2 at 256.54, ON is pin 1 at (266.7, 43.18), OFF is pin 3 at (266.7, 48.26)
    sw1 = s.add_symbol("Switch:SW_SPDT", "SW1", "MASTER_SWITCH", "Button_Switch_THT:SW_DIP_SPSTx01_Slide_6.7x4.1mm_W7.62mm_P2.54mm_LowPro", 261.62, 45.72)
    sw1.add_pin("1")
    sw1.add_pin("2")
    sw1.add_pin("3")
    s.add_wire(248.92, 45.72, 256.54, 45.72)
    s.add_global_label("+V_BATT_PROT", 248.92, 45.72, angle=180)
    s.add_wire(266.7, 43.18, 274.32, 43.18)
    s.add_global_label("+VBAT_SW", 274.32, 43.18, angle=0)
    s.add_symbol("power:PWR_FLAG", "#FLG101", "PWR_FLAG", "", 274.32, 43.18)
    s.add_no_connect(266.7, 48.26)

    # Master Power LED D5 + R6 (4.7k)
    r6 = s.add_symbol("Device:R", "R6", "4.7k", "Resistor_SMD:R_0805_2012Metric", 261.62, 53.34)
    r6.add_pin("1") # at 49.53
    r6.add_pin("2") # at 57.15
    s.add_wire(274.32, 43.18, 261.62, 43.18)
    s.add_junction(274.32, 43.18)
    s.add_wire(261.62, 43.18, 261.62, 49.53)
    
    # D5 at (261.62, 60.96) angle 270:
    # Pin 1 (K) at (261.62, 60.96 - (-3.81)) = (261.62, 64.77)
    # Pin 2 (A) at (261.62, 57.15)
    d5 = s.add_symbol("Device:LED", "D5", "LED_PWR_GREEN", "LED_SMD:LED_0805_2012Metric", 261.62, 60.96, angle=270)
    d5.add_pin("1")
    d5.add_pin("2")
    s.add_wire(261.62, 64.77, 261.62, 68.58)
    s.add_symbol("power:GND", "#PWR111", "GND", "", 261.62, 68.58)

    # =========================================================================
    # 5. MP1584EN 3A Buck Converter (to +5V)
    # =========================================================================
    s.add_text("5. MP1584EN 3A SYNCHRONOUS STEP-DOWN CONVERTER (TO +5V)", 25.4, 96.52, size=1.52, bold=True)
    
    # U2 at (60.96, 119.38)
    u2 = s.add_symbol("terrascout_custom:MP1584EN", "U2", "MP1584EN_3A", "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm", 60.96, 119.38)
    for p in range(1, 10):
        u2.add_pin(str(p))

    # VIN Pin 2 at (48.26, 116.84)
    s.add_wire(48.26, 116.84, 38.1, 116.84)
    s.add_global_label("+VBAT_SW", 38.1, 116.84, angle=180)

    # Pull-up R7 (100k) on EN Pin 1 (48.26, 111.76) to VIN
    # Place R7 at (43.18, 111.76) angle 90:
    # Pin 1 at (39.37, 111.76), Pin 2 at (46.99, 111.76)
    r7 = s.add_symbol("Device:R", "R7", "100k", "Resistor_SMD:R_0805_2012Metric", 43.18, 111.76, angle=90)
    r7.add_pin("1")
    r7.add_pin("2")
    s.add_wire(48.26, 111.76, 46.99, 111.76) # Pin 1 EN to R7 pin 2
    s.add_wire(39.37, 111.76, 38.1, 111.76)
    s.add_wire(38.1, 111.76, 38.1, 116.84)   # to VIN
    s.add_junction(38.1, 116.84)

    # Input caps C5 (10µF) at (33.02, 124.46)
    c5 = s.add_symbol("Device:C", "C5", "10uF_25V", "Capacitor_SMD:C_1206_3216Metric", 33.02, 124.46)
    c5.add_pin("1") # at 120.65
    c5.add_pin("2") # at 128.27
    s.add_wire(38.1, 116.84, 33.02, 116.84)
    s.add_junction(38.1, 116.84)
    s.add_wire(33.02, 116.84, 33.02, 120.65)
    s.add_wire(33.02, 128.27, 33.02, 132.08)
    s.add_symbol("power:GND", "#PWR112", "GND", "", 33.02, 132.08)

    # FREQ Pin 7 at (48.26, 124.46) with R11 (100k) to GND
    r11 = s.add_symbol("Device:R", "R11", "100k", "Resistor_SMD:R_0805_2012Metric", 43.18, 124.46, angle=90)
    r11.add_pin("1") # at 39.37
    r11.add_pin("2") # at 46.99
    s.add_wire(48.26, 124.46, 46.99, 124.46)
    s.add_wire(39.37, 124.46, 35.56, 124.46)
    s.add_symbol("power:GND", "#PWR113", "GND", "", 35.56, 124.46)

    # GND pins 8, 9 of MP1584EN
    s.add_wire(60.96, 135.89, 60.96, 139.7)
    s.add_wire(63.5, 135.89, 63.5, 139.7)
    s.add_wire(60.96, 139.7, 63.5, 139.7)
    s.add_junction(60.96, 139.7)
    s.add_symbol("power:GND", "#PWR114", "GND", "", 60.96, 139.7)

    # SW node (73.66, 111.76)
    # BST Pin 4 at (73.66, 116.84) connected via C7 (100nF) at (81.28, 114.3)
    c7 = s.add_symbol("Device:C", "C7", "100nF", "Capacitor_SMD:C_0805_2012Metric", 81.28, 114.3)
    c7.add_pin("1") # at 110.49
    c7.add_pin("2") # at 118.11
    s.add_wire(73.66, 111.76, 81.28, 111.76)
    s.add_junction(81.28, 111.76)
    s.add_wire(81.28, 111.76, 81.28, 110.49)
    s.add_wire(73.66, 116.84, 81.28, 116.84)
    s.add_wire(81.28, 116.84, 81.28, 118.11)

    # Catch diode D6 (SS34) at (88.9, 124.46) angle 270:
    # Pin 1 (K) at (88.9, 120.65), Pin 2 (A) at (88.9, 128.27)
    d6 = s.add_symbol("Device:D_Schottky", "D6", "SS34_3A", "Diode_SMD:D_SMA", 88.9, 124.46, angle=270)
    d6.add_pin("1")
    d6.add_pin("2")
    s.add_wire(81.28, 111.76, 88.9, 111.76)
    s.add_junction(88.9, 111.76)
    s.add_wire(88.9, 111.76, 88.9, 120.65)
    s.add_wire(88.9, 128.27, 88.9, 132.08)
    s.add_symbol("power:GND", "#PWR115", "GND", "", 88.9, 132.08)

    # Inductor L2 (10µH 3A) at (99.06, 111.76) angle 90:
    # Pin 1 at 95.25, Pin 2 at 102.87
    l2 = s.add_symbol("Device:L", "L2", "10uH_3A", "Inductor_SMD:L_12x12mm_H6mm", 99.06, 111.76, angle=90)
    l2.add_pin("1")
    l2.add_pin("2")
    s.add_wire(88.9, 111.76, 95.25, 111.76)
    s.add_wire(102.87, 111.76, 109.22, 111.76)

    # FB Pin 5 at (73.66, 124.46)
    # Voltage divider R8 (42.2k) and R9 (8.06k)
    s.add_wire(109.22, 111.76, 109.22, 124.46)
    s.add_junction(109.22, 111.76)
    r8 = s.add_symbol("Device:R", "R8", "42.2k_1%", "Resistor_SMD:R_0805_2012Metric", 99.06, 124.46, angle=90)
    r8.add_pin("1") # at 95.25
    r8.add_pin("2") # at 102.87
    s.add_wire(109.22, 124.46, 102.87, 124.46)
    s.add_wire(95.25, 124.46, 88.9, 124.46)
    s.add_junction(88.9, 124.46)
    s.add_wire(88.9, 124.46, 73.66, 124.46) # to FB pin

    r9 = s.add_symbol("Device:R", "R9", "8.06k_1%", "Resistor_SMD:R_0805_2012Metric", 88.9, 132.08)
    r9.add_pin("1") # at 128.27
    r9.add_pin("2") # at 135.89
    s.add_wire(88.9, 124.46, 88.9, 128.27)
    s.add_wire(88.9, 135.89, 88.9, 139.7)
    s.add_symbol("power:GND", "#PWR116", "GND", "", 88.9, 139.7)

    # COMP Pin 6 at (73.66, 129.54) with R10 (33k) + C8 (1.8nF)
    s.add_wire(73.66, 129.54, 78.74, 129.54)
    r10 = s.add_symbol("Device:R", "R10", "33k", "Resistor_SMD:R_0805_2012Metric", 78.74, 134.62)
    r10.add_pin("1") # at 130.81
    r10.add_pin("2") # at 138.43
    s.add_wire(78.74, 129.54, 78.74, 130.81)
    c8 = s.add_symbol("Device:C", "C8", "1.8nF", "Capacitor_SMD:C_0805_2012Metric", 78.74, 142.24)
    c8.add_pin("1") # at 138.43
    c8.add_pin("2") # at 146.05
    s.add_wire(78.74, 146.05, 78.74, 148.59)
    s.add_symbol("power:GND", "#PWR117", "GND", "", 78.74, 148.59)

    # Output caps C10 (22µF) and C11 (22µF)
    c10 = s.add_symbol("Device:C", "C10", "22uF_10V", "Capacitor_SMD:C_1206_3216Metric", 114.3, 120.65)
    c10.add_pin("1") # at 116.84
    c10.add_pin("2") # at 124.46
    s.add_wire(109.22, 111.76, 114.3, 111.76)
    s.add_junction(114.3, 111.76)
    s.add_wire(114.3, 111.76, 114.3, 116.84)
    s.add_wire(114.3, 124.46, 114.3, 128.27)
    s.add_symbol("power:GND", "#PWR118", "GND", "", 114.3, 128.27)

    c11 = s.add_symbol("Device:C", "C11", "22uF_10V", "Capacitor_SMD:C_1206_3216Metric", 121.92, 120.65)
    c11.add_pin("1") # at 116.84
    c11.add_pin("2") # at 124.46
    s.add_wire(114.3, 111.76, 121.92, 111.76)
    s.add_junction(121.92, 111.76)
    s.add_wire(121.92, 111.76, 121.92, 116.84)
    s.add_wire(121.92, 124.46, 121.92, 128.27)
    s.add_symbol("power:GND", "#PWR119", "GND", "", 121.92, 128.27)

    # +5V Rail Label & Flag
    s.add_wire(121.92, 111.76, 129.54, 111.76)
    s.add_global_label("+5V", 129.54, 111.76, angle=0)
    s.add_symbol("power:PWR_FLAG", "#FLG102", "PWR_FLAG", "", 129.54, 111.76)

    # =========================================================================
    # 6. AMS1117-3.3 Linear Regulator (to +3V3)
    # =========================================================================
    s.add_text("6. AMS1117-3.3 LOW-DROPOUT REGULATOR (TO +3V3)", 147.32, 96.52, size=1.52, bold=True)
    
    # U3 at (172.72, 116.84)
    # Pin 3 (VIN) at (162.56, 116.84)
    # Pin 2 (VOUT) at (182.88, 116.84) - already power_out!
    # Pin 1 (GND) at (172.72, 128.27)
    u3 = s.add_symbol("terrascout_custom:AMS1117-3.3", "U3", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 172.72, 116.84)
    u3.add_pin("1")
    u3.add_pin("2")
    u3.add_pin("3")

    s.add_wire(154.94, 116.84, 162.56, 116.84)
    s.add_global_label("+5V", 154.94, 116.84, angle=180)

    # Input C13 (10µF) at (158.75, 124.46)
    c13 = s.add_symbol("Device:C", "C13", "10uF_10V", "Capacitor_SMD:C_0805_2012Metric", 158.75, 124.46)
    c13.add_pin("1") # at 120.65
    c13.add_pin("2") # at 128.27
    s.add_wire(158.75, 116.84, 158.75, 120.65)
    s.add_junction(158.75, 116.84)
    s.add_wire(158.75, 128.27, 158.75, 132.08)
    s.add_symbol("power:GND", "#PWR120", "GND", "", 158.75, 132.08)

    # Pin 1 GND
    s.add_wire(172.72, 128.27, 172.72, 132.08)
    s.add_symbol("power:GND", "#PWR121", "GND", "", 172.72, 132.08)

    # Output Pin 2 (182.88, 116.84) to +3V3 rail (NO PWR_FLAG here because U3 pin 2 is power_out!)
    s.add_wire(182.88, 116.84, 203.2, 116.84)
    s.add_global_label("+3V3", 203.2, 116.84, angle=0)

    # Output C15 (22µF) at (187.96, 124.46)
    c15 = s.add_symbol("Device:C", "C15", "22uF_10V", "Capacitor_SMD:C_1206_3216Metric", 187.96, 124.46)
    c15.add_pin("1") # at 120.65
    c15.add_pin("2") # at 128.27
    s.add_wire(187.96, 116.84, 187.96, 120.65)
    s.add_junction(187.96, 116.84)
    s.add_wire(187.96, 128.27, 187.96, 132.08)
    s.add_symbol("power:GND", "#PWR122", "GND", "", 187.96, 132.08)

    # 3.3V Power LED D7 (Blue) + R12 (1.5k)
    r12 = s.add_symbol("Device:R", "R12", "1.5k", "Resistor_SMD:R_0805_2012Metric", 195.58, 123.19)
    r12.add_pin("1") # at 119.38
    r12.add_pin("2") # at 127.0
    s.add_wire(195.58, 116.84, 195.58, 119.38)
    s.add_junction(195.58, 116.84)

    # D7 at (195.58, 130.81) angle 270:
    # Pin 1 (K) at (195.58, 134.62)
    # Pin 2 (A) at (195.58, 127.0)
    d7 = s.add_symbol("Device:LED", "D7", "LED_3V3_BLUE", "LED_SMD:LED_0805_2012Metric", 195.58, 130.81, angle=270)
    d7.add_pin("1")
    d7.add_pin("2")
    s.add_wire(195.58, 134.62, 195.58, 138.43)
    s.add_symbol("power:GND", "#PWR123", "GND", "", 195.58, 138.43)

    # =========================================================================
    # 7. Battery Voltage Telemetry Divider & ADC Protection
    # =========================================================================
    s.add_text("7. BATTERY TELEMETRY DIVIDER & ADC CLAMP", 215.9, 96.52, size=1.52, bold=True)
    
    s.add_wire(220.98, 106.68, 226.06, 106.68)
    s.add_global_label("+VBAT_SW", 220.98, 106.68, angle=180)
    r13 = s.add_symbol("Device:R", "R13", "100k_1%", "Resistor_SMD:R_0805_2012Metric", 226.06, 114.3)
    r13.add_pin("1") # at 110.49
    r13.add_pin("2") # at 118.11
    s.add_wire(226.06, 106.68, 226.06, 110.49)

    s.add_wire(226.06, 118.11, 226.06, 121.92)
    s.add_junction(226.06, 121.92)

    r14 = s.add_symbol("Device:R", "R14", "33k_1%", "Resistor_SMD:R_0805_2012Metric", 226.06, 129.54)
    r14.add_pin("1") # at 125.73
    r14.add_pin("2") # at 133.35
    s.add_wire(226.06, 121.92, 226.06, 125.73)
    s.add_wire(226.06, 133.35, 226.06, 137.16)
    s.add_symbol("power:GND", "#PWR124", "GND", "", 226.06, 137.16)

    # Noise filter cap C17 (100nF)
    c17 = s.add_symbol("Device:C", "C17", "100nF", "Capacitor_SMD:C_0805_2012Metric", 233.68, 129.54)
    c17.add_pin("1") # at 125.73
    c17.add_pin("2") # at 133.35
    s.add_wire(226.06, 121.92, 233.68, 121.92)
    s.add_junction(233.68, 121.92)
    s.add_wire(233.68, 121.92, 233.68, 125.73)
    s.add_wire(233.68, 133.35, 233.68, 137.16)
    s.add_symbol("power:GND", "#PWR125", "GND", "", 233.68, 137.16)

    # Output to BATT_SENSE
    s.add_wire(233.68, 121.92, 246.38, 121.92)
    s.add_global_label("BATT_SENSE", 246.38, 121.92, angle=0)

    # Global power flags
    s.add_symbol("power:PWR_FLAG", "#FLG104", "PWR_FLAG", "", 27.94, 48.26)

    return s

s1 = build_refined_sheet1()
with open("C:/Users/white/terrascout-grounded/hardware/schematics/sheet1_power.kicad_sch", "w", encoding="utf-8") as f:
    f.write(s1.render())
print("Saved refined sheet1_power.kicad_sch")
