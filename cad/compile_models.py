"""
================================================================================
TerraScout OpenSCAD CAD Compilation & Render Automation
Exports all STL 3D printable meshes and PNG preview renders.
================================================================================
"""

import os
import subprocess
import sys
import time

OPENSCAD_BIN = r"C:\Program Files\OpenSCAD\openscad.com"
SCAD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chassis.scad")
CAD_DIR = os.path.dirname(os.path.abspath(__file__))

PARTS = [
    # (part_id, output_filename, description, is_stl)
    (0, "assembly.png", "Assembled Rover 3D Perspective Preview", False),
    (1, "exploded.png", "Exploded Rover Architecture Preview", False),
    (2, "bottom_deck.stl", "Bottom Deck Chassis Plate (N20 + 18650 Cradles)", True),
    (3, "top_deck.stl", "Top Deck Electronics Plate (Pico + OLED + Turret)", True),
    (4, "motor_bracket.stl", "N20 Metal Gearmotor Clamping Bracket", True),
    (5, "ultrasonic_bracket.stl", "HC-SR04 / RCWL-1601 Ultrasonic Servo Turret", True),
    (6, "caster_mount.stl", "15mm Ball Caster Standoff Riser Block", True),
    (7, "print_bed_plate.stl", "Complete 200x200mm Print Bed Plate (All Parts)", True),
]

def compile_cad():
    print("=" * 70)
    print("TERRASCOUT OPENSCAD CAD BUILD SYSTEM")
    print(f"OpenSCAD Binary: {OPENSCAD_BIN}")
    print(f"Target SCAD:    {SCAD_FILE}")
    print("=" * 70)

    if not os.path.exists(OPENSCAD_BIN):
        print(f"ERROR: OpenSCAD binary not found at {OPENSCAD_BIN}")
        sys.exit(1)

    start_all = time.time()
    results = []

    for part_id, out_name, desc, is_stl in PARTS:
        out_path = os.path.join(CAD_DIR, out_name)
        print(f"\n[BUILD] Part {part_id}: {desc}")
        print(f"        Output -> {out_name}")

        t0 = time.time()
        if is_stl:
            cmd = [
                OPENSCAD_BIN,
                "-D", f"part_id={part_id}",
                "-o", out_path,
                SCAD_FILE,
            ]
        else:
            # PNG preview rendering
            cmd = [
                OPENSCAD_BIN,
                "-D", f"part_id={part_id}",
                "--autocenter",
                "--viewall",
                "--imgsize", "1280,720",
                "--colorscheme", "Sunset",
                "-o", out_path,
                SCAD_FILE,
            ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - t0

        if res.returncode == 0 and os.path.exists(out_path):
            size_kb = os.path.getsize(out_path) / 1024.0
            print(f"        STATUS: SUCCESS ({elapsed:.2f}s, {size_kb:.1f} KB)")
            results.append((out_name, "PASS", f"{size_kb:.1f} KB", f"{elapsed:.2f}s"))
        else:
            print(f"        STATUS: FAILED (Code {res.returncode})")
            if res.stderr:
                print(f"        STDERR: {res.stderr.strip()}")
            results.append((out_name, "FAIL", "0 KB", f"{elapsed:.2f}s"))

    print("\n" + "=" * 70)
    print("CAD BUILD SUMMARY")
    print("=" * 70)
    print(f"{'Filename':<24} {'Status':<8} {'Size':<12} {'Time':<8}")
    print("-" * 70)
    for name, stat, sz, tm in results:
        print(f"{name:<24} {stat:<8} {sz:<12} {tm:<8}")
    print("=" * 70)
    print(f"Total Compilation Time: {time.time() - start_all:.2f}s\n")

if __name__ == "__main__":
    compile_cad()
