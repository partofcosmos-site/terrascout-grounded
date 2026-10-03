#!/usr/bin/env python3
"""
================================================================================
TerraScout Rover - Autonomous PCB Design Rule Check (DRC) Verification Gate
Project: TerraScout Grounded (Hack Club Grounded)
Author: Loop Agent 7 - TerraScout PCB Layout & Routing Engine
License: CERN-OHL-P v2 / MIT
================================================================================
"""

import sys
import json
from pathlib import Path
from generate_pcb import TerraScoutPCB, DRCEngine, OUTPUT_DIR, BOARD_WIDTH_MM, BOARD_HEIGHT_MM, MOUNT_HOLES

def run_drc():
    print("=" * 80)
    print("  TERRASCOUT ROVER - STANDALONE PCB DESIGN RULE CHECK (DRC) GATE")
    print("=" * 80)
    
    pcb = TerraScoutPCB()
    drc_results = DRCEngine.run_checks(pcb)
    
    report_file = OUTPUT_DIR / "drc_report.json"
    with open(report_file, "w") as f:
        json.dump(drc_results, f, indent=2)
        
    print(f"[*] Board Dimensions:          {drc_results['board_dimensions_mm']}")
    print(f"[*] Mounting Hole Bolt Pattern: {drc_results['m3_bolt_pattern_span_mm']} (M3 Clearance 3.2mm)")
    print(f"[*] Copper Layers:             {drc_results['copper_layers']} (Top F.Cu, Bottom B.Cu)")
    print(f"[*] Min Trace Width (Signal):  {drc_results['min_trace_width_signal_mm']} mm (10 mil)")
    print(f"[*] Min Trace Width (Power):   {drc_results['min_trace_width_power_mm']} mm (30 mil)")
    print(f"[*] Min Drill Diameter:        {drc_results['min_drill_dia_mm']} mm (12 mil)")
    print(f"[*] Min Copper Clearance:      {drc_results['min_clearance_mm']} mm (6 mil)")
    print(f"[*] Checks Evaluated:          {drc_results['checks_evaluated']}")
    print(f"[*] Total Defects Found:       {drc_results['defects_found']}")
    print(f"[*] Total Warnings Found:      {drc_results['warnings_found']}")
    print(f"[*] Gate Verification Status:  {drc_results['drc_status']}")
    print("=" * 80)
    
    if drc_results["defects_found"] > 0:
        print("\n[!] DRC DEFECTS DETECTED:")
        for idx, defect in enumerate(drc_results["defects_list"], 1):
            print(f"  {idx}. {defect}")
        sys.exit(1)
    else:
        print("\n[+] SUCCESS: All JLCPCB 2-Layer manufacturing constraints verified with 0 defects.")
        sys.exit(0)

if __name__ == "__main__":
    run_drc()
