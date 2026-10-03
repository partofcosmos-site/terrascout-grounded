# TerraScout Rover - PCB Hardware Division

Welcome to the **TerraScout Rover Printed Circuit Board (PCB) Directory** (`hardware/pcb/`).

This directory contains the production-ready 2-layer FR-4 PCB design ($100\,\text{mm} \times 80\,\text{mm}$) for the TerraScout Rover, tailored to match the dual-deck 3D printed chassis bolt pattern ($80\,\text{mm} \times 60\,\text{mm}$ M3 standoffs) from `cad/chassis.scad`.

---

## ⚡ Quick Links & Production Deliverables

- **Fabrication Ready Zip:** [`gerbers.zip`](gerbers.zip) (Ready for direct upload to JLCPCB / PCBWay)
- **Detailed Engineering Report:** [`PCB_DESIGN_REPORT.md`](PCB_DESIGN_REPORT.md)
- **KiCad Native Board File:** [`terrascout.kicad_pcb`](terrascout.kicad_pcb)
- **Bill of Materials:** [`bom.csv`](bom.csv) (with LCSC part numbers)
- **Centroid Placement File:** [`cpl.csv`](cpl.csv)
- **DRC Verification Report:** [`drc_report.json`](drc_report.json)
- **Automated PCB Layout Engine:** [`generate_pcb.py`](generate_pcb.py)
- **Standalone DRC Check Gate:** [`pcb_drc_check.py`](pcb_drc_check.py)

---

## 📸 Render Previews

| View | File | Description |
|---|---|---|
| **3D Top Isometric** | `render_3d_top_isometric.png` | Fully assembled rover PCB with components |
| **3D Bottom Isometric** | `render_3d_bottom_isometric.png` | Bottom ground plane with through-hole solder pins |
| **2D Top Composite** | `render_2d_top_composite.png` | Top copper, solder mask, gold pads, white silkscreen |
| **2D Bottom Composite** | `render_2d_bottom_composite.png` | Bottom copper and thermal relief ground flood |
| **PyGerber Top Copper** | `render_2d_top_copper.png` | PyGerber rasterized Top Copper (`F.Cu`) |
| **PyGerber Bottom Copper** | `render_2d_bottom_copper.png` | PyGerber rasterized Bottom Copper (`B.Cu`) |

---

## 🛠️ Automated Regeneration & Verification

To re-run the layout generator, regenerate all Gerbers, renders, and execute the DRC:

```bash
python hardware/pcb/generate_pcb.py
```

To run the standalone Design Rule Check gate:

```bash
python hardware/pcb/pcb_drc_check.py
```
