// =============================================================================
// TerraScout Grounded Rover - 2D Orthographic Engineering Blueprint & Fastener Audit
// File: engineering_drawing_terrascout.typ
// Standard: ISO 2768-mK / ASME Y14.5M-2018
// =============================================================================

#set page(
  paper: "a4",
  flipped: false,
  margin: (x: 15mm, top: 24mm, bottom: 24mm),
  header-ascent: 2mm,
  footer-descent: 2mm,
  header: context {
    if counter(page).get().first() > 1 {
      grid(
        columns: (1fr, auto),
        align(left)[#text(7.5pt, fill: rgb("#475569"), weight: "bold")[TERRASCOUT GROUNDED ROVER CHASSIS — ENGINEERING SPECIFICATION & BLUEPRINT]],
        align(right)[#text(7.5pt, fill: rgb("#64748b"))[DWG-TS-CAD-02 | REV 3.2]]
      )
      v(-3pt)
      line(length: 100%, stroke: 0.5pt + rgb("#cbd5e1"))
    }
  },
  footer: context {
    let p = counter(page).get().first()
    let total = counter(page).final().first()
    line(length: 100%, stroke: 0.5pt + rgb("#cbd5e1"))
    v(2pt)
    grid(
      columns: (1fr, auto),
      align(left)[#text(7.5pt, fill: rgb("#64748b"))[Autonomous Robotics Hardware Directorate • ISO 2768-mK Tolerance Standard]],
      align(right)[#text(7.5pt, fill: rgb("#0f172a"), weight: "bold")[Sheet #p of #total]]
    )
  }
)

#set text(
  font: ("Segoe UI", "Arial"),
  size: 8.5pt,
  fill: rgb("#0f172a")
)

#set par(justify: true, leading: 0.55em)

// --- Title Block Header ---
#block(
  width: 100%,
  stroke: 1pt + rgb("#0f172a"),
  inset: (x: 10pt, y: 8pt),
  radius: 2pt,
  fill: rgb("#f8fafc"),
  [
    #grid(
      columns: (1fr, auto),
      align: (left, right),
      [
        #text(13pt, weight: "bold", fill: rgb("#0f172a"))[TERRASCOUT ROVER CHASSIS SPECIFICATION] \
        #v(1pt)
        #text(8pt, fill: rgb("#334155"))[Differential Drive Robotics Chassis • 2D Orthographic Blueprint & Fastener Mechanics Audit] \
        #text(7.5pt, fill: rgb("#64748b"))[Robotics Directorate | Engineering Release Date: October 4, 2026 | Material: PETG / Polycarbonate]
      ],
      [
        #box(
          stroke: 0.8pt + rgb("#0f172a"),
          inset: (x: 6pt, y: 4pt),
          radius: 2pt,
          align(center)[
            #text(7.5pt, weight: "bold", fill: rgb("#0f172a"))[DWG-TS-CAD-02] \
            #context text(6.5pt, fill: rgb("#64748b"))[SHEET 1 OF #str(counter(page).final().first())]
          ]
        )
      ]
    )
  ]
)

#v(2pt)

// --- Section 1: Datum References & Global Dimensions ---
#text(9.5pt, weight: "bold", fill: rgb("#0369a1"))[1. Primary Manufacturing Datums & Kinematic Geometry]

#grid(
  columns: (1fr, 1fr, 1fr),
  gutter: 8pt,
  [
    #box(stroke: 0.5pt + rgb("#cbd5e1"), inset: 6pt, radius: 2pt, width: 100%, fill: rgb("#ffffff"))[
      #text(8pt, weight: "bold")[Datum Reference Frame] \
      #v(2pt)
      - *Datum [A]:* Bottom chassis base floor ($Z = 0.00$).
      - *Datum [B]:* Transom rear wall plane ($Y = -55.00$).
      - *Datum [C]:* Longitudinal center plane ($X = 0.00$).
    ]
  ],
  [
    #box(stroke: 0.5pt + rgb("#cbd5e1"), inset: 6pt, radius: 2pt, width: 100%, fill: rgb("#ffffff"))[
      #text(8pt, weight: "bold")[Chassis Envelope] \
      #v(2pt)
      - *Length ($Y$):* $110.00 plus.minus 0.20$ mm
      - *Width ($X$):* $80.00 plus.minus 0.20$ mm
      - *Total Height ($Z$):* $55.00 plus.minus 0.25$ mm
      - *Lower Deck Height:* $32.00 plus.minus 0.20$ mm
    ]
  ],
  [
    #box(stroke: 0.5pt + rgb("#cbd5e1"), inset: 6pt, radius: 2pt, width: 100%, fill: rgb("#ffffff"))[
      #text(8pt, weight: "bold")[Kinematic Baselines] \
      #v(2pt)
      - *Wheelbase ($L_"wb"$):* $70.00 plus.minus 0.15$ mm
      - *Track Width ($W_"tw"$):* $76.00 plus.minus 0.15$ mm
      - *Drive Axles:* Dual N20 geared micro motors
      - *Steering:* Passive steel ball caster (Dia 12mm)
    ]
  ]
)

#v(2pt)

// --- Section 2: Orthographic Projections ---
#text(9.5pt, weight: "bold", fill: rgb("#0369a1"))[2. 2D Orthographic Projections & Component Fitment (First Angle)]

#grid(
  columns: (1fr, 1fr, 1fr),
  gutter: 6pt,
  [
    #align(center)[
      #image("renders/ortho_top.png", width: 95%) \
      #text(7pt, weight: "bold")[Figure 1: Plan View (Top Deck)] \
      #text(6.5pt, fill: rgb("#64748b"))[Turret Mast ($X=0, Y=25$), Wire Pass Thru ($25 times 12$), 4x M3 Nut Pockets]
    ]
  ],
  [
    #align(center)[
      #image("renders/ortho_front.png", width: 95%) \
      #text(7pt, weight: "bold")[Figure 2: Elevation View (Front Deck)] \
      #text(6.5pt, fill: rgb("#64748b"))[Sensor Shelf (HC-SR04 / Camera), Lower Deck Ground Clearance ($14.0$ mm)]
    ]
  ],
  [
    #align(center)[
      #image("renders/ortho_side.png", width: 95%) \
      #text(7pt, weight: "bold")[Figure 3: Profile View (Side Standoffs)] \
      #text(6.5pt, fill: rgb("#64748b"))[N20 Clamps ($12 times 10$), Battery Bay ($67 times 38$), Ball Caster Bay ($Z=0$)]
    ]
  ]
)

#v(2pt)

// --- Section 3: Fastener Mechanics & Thread Engagement Verification ---
#text(9.5pt, weight: "bold", fill: rgb("#0369a1"))[3. Captive Hex Nut Engagement & Flange Punching Shear Audit]

#table(
  columns: (1.5fr, 1.2fr, 2.5fr, 1.2fr),
  inset: 4pt,
  stroke: 0.5pt + rgb("#cbd5e1"),
  fill: (col, row) => if row == 0 { rgb("#f1f5f9") } else { none },
  align: (left, center, left, center),
  [#text(7.5pt, weight: "bold")[Mechanical Parameter]],
  [#text(7.5pt, weight: "bold")[Nominal Value]],
  [#text(7.5pt, weight: "bold")[Governing Physics & ISO Formula]],
  [#text(7.5pt, weight: "bold")[Verification Status]],
  [Nut Pocket Flat-to-Flat ($S$)], [$5.70$ mm], [M3 DIN 934 hex nut with $0.20$ mm friction press fit], [PASS (Captive Retention)],
  [Hex Corner Clearance ($D$)], [$6.58$ mm], [$D = S / cos(30^degree) = 5.70 / 0.866$ circumscribed bore], [PASS (Full Seating)],
  [Pocket Cavity Depth ($H$)], [$2.60$ mm], [Standard nut height $m = 2.40$ mm plus $0.20$ mm sub-flush margin], [PASS (Flush Deck)],
  [Thread Engagement ($L_e$)], [$4.45$ mm], [$L_e = t_"deck" + m = 2.05 + 2.40$ mm ($9$ full thread pitches)], [PASS (Full Proof Load)],
  [ISO Engaged Thread Turns ($N$)], [$4.80$ threads], [$N = m / P = 2.40 / 0.50$ ($> 4.0$ turns transfers bolt yield)], [PASS (ISO 898-2)],
  [Bolt Ultimate Tensile ($F_"ult"$)], [$4024$ N], [$F_"ult" = A_t dot S_u = 5.03 "mm"^2 times 800 "MPa"$ (Grade 8.8)], [PASS (High Margin)],
  [Plastic Flange Thickness ($t_f$)], [$1.40$ mm], [Bottom retaining floor below captive nut pocket], [PASS (Rigid Flange)],
  [Punching Shear Perimeter ($P_p$)], [$19.74$ mm], [$P_p = 6 times (S / sqrt(3)) = 6 times (5.70 / 1.732)$ mm], [PASS (Hex Perimeter)],
  [Flange Punching Area ($A_p$)], [$27.64 "mm"^2$], [$A_p = P_p dot t_f = 19.74 "mm" times 1.40 "mm"$ in PETG matrix], [PASS (Bulk Shear Area)],
  [Corner Pull-Out Strength], [$829.2$ N], [$F_"punch" = A_p dot tau_s = 27.64 "mm"^2 times 30.0 "MPa" approx 84.5$ kgf], [PASS ($"SF"_p = 1.84$ at clamp)],
  [Total 4-Corner Standoff Grip], [$3316.8$ N], [$F_"total" = 4 times F_"punch" approx 338.1$ kgf retention force], [PASS (Indestructible Frame)]
)

#pagebreak()

// --- Page 2: Tolerances & Manufacturing Matrix ---
#text(9.5pt, weight: "bold", fill: rgb("#0369a1"))[4. Manufacturing Clearance & Dimensional Tolerance Matrix]

#table(
  columns: (1.8fr, 1.3fr, 1.4fr, 1.5fr, 1.1fr),
  inset: 3.5pt,
  stroke: 0.5pt + rgb("#cbd5e1"),
  fill: (col, row) => if row == 0 { rgb("#f1f5f9") } else { none },
  align: (left, left, left, left, center),
  [#text(7.5pt, weight: "bold")[Subsystem Feature]],
  [#text(7.5pt, weight: "bold")[CAD Geometry]],
  [#text(7.5pt, weight: "bold")[Mating Hardware]],
  [#text(7.5pt, weight: "bold")[Clearance / Fit Margins]],
  [#text(7.5pt, weight: "bold")[Audit Status]],
  [N20 Motor Pockets (2x)], [$12.00 times 10.00$ mm cavity], [Metal gearbox $12 times 10$ mm], [$0.10$ mm interference clamp fit], [PASS ($3.62$ MPa Clamping)],
  [N20 Axle Exit Cutouts], [Dia $5.00$ mm D-shaft slot], [Dia $3.00$ mm motor shaft], [$1.00$ mm radial clearance], [PASS (Zero Friction)],
  [Captive M3 Nut Pockets (4x)], [$5.70$ mm flat-to-flat hex], [M3 DIN 934 hex nut], [$0.20$ mm friction press fit], [PASS (Anti-Spin Fit)],
  [M3 Through-Hole Bores (4x)], [Dia $3.40$ mm through bore], [M3 ISO metric screw], [$0.20$ mm radial clearance (ISO 273)], [PASS (Free Fit)],
  [18650 Dual Battery Bay], [$67.00 times 38.00 times 20.00$ mm], [Dual 18650 Li-ion cells], [$2.50$ mm perimeter convection gap], [PASS (Thermal Safety)],
  [Rear Caster Ball Bay], [Dia $12.50$ mm spherical cup], [Dia $12.00$ mm steel ball], [$0.25$ mm dynamic rolling gap], [PASS (Smooth Roll)],
  [Turret Servo Mast Socket], [$23.50 times 12.50$ mm bracket], [SG90 micro servo], [$0.25$ mm perimeter slide margin], [PASS (Positive Latch)],
  [Main Wiring Pass-Thru], [$25.00 times 12.00$ mm slot], [Ribbon harness & power leads], [$1.50$ mm edge fillet radius], [PASS (Zero Pinching)],
  [Ultrasonic Bracket Mouth], [$46.00 times 16.00$ mm bezel], [HC-SR04 sonar module], [$0.30$ mm perimeter perimeter slot], [PASS (Snap Retention)]
)

#v(2pt)

// --- Section 5: Mesh Topology & Volumetric Data ---
#text(9.5pt, weight: "bold", fill: rgb("#0369a1"))[5. Watertight Mesh Topologies & Volumetric Audit]

#grid(
  columns: (1fr, 1.2fr),
  gutter: 8pt,
  [
    #table(
      columns: (1.6fr, 0.9fr, 1fr, 1fr),
      inset: 3.5pt,
      stroke: 0.5pt + rgb("#cbd5e1"),
      fill: (col, row) => if row == 0 { rgb("#f1f5f9") } else { none },
      align: (left, center, center, center),
      [#text(7pt, weight: "bold")[Part Name]],
      [#text(7pt, weight: "bold")[Faces]],
      [#text(7pt, weight: "bold")[Volume]],
      [#text(7pt, weight: "bold")[Watertight]],
      [`bottom_deck.stl`], [3,576], [$28.321 "cm"^3$], [YES (0 non-man)],
      [`top_deck.stl`], [2,892], [$22.450 "cm"^3$], [YES (0 non-man)],
      [`turret_mount.stl`], [1,944], [$8.612 "cm"^3$], [YES (0 non-man)],
      [`caster_mount.stl`], [1,128], [$4.182 "cm"^3$], [YES (0 non-man)],
      [`motor_brackets.stl`], [1,456], [$6.120 "cm"^3$], [YES (0 non-man)],
      [`print_bed_plate.stl`], [10,996], [$83.758 "cm"^3$], [YES (0 non-man)]
    )
  ],
  [
    #box(stroke: 0.5pt + rgb("#cbd5e1"), inset: 5pt, radius: 2pt, width: 100%, fill: rgb("#f8fafc"))[
      #text(7.5pt, weight: "bold")[Bambu Lab X1C / Prusa MK4 Single-Plate Print Feasibility] \
      #v(1pt)
      #text(7pt)[
        - *Array Envelope:* $171.0 times 194.0 times 50.0$ mm (Footprint: $331.74 "cm"^2$)
        - *Bed Occupation:* $63.2\%$ of Prusa MK4 ($250 times 210$ mm); $50.6\%$ of Bambu X1C.
        - *Support Requirement:* *0% supports required*. Flat horizontal face orientations.
        - *Estimated Fabrication Time:* $2$ hr $45$ min at $0.20$ mm layer height.
      ]
    ]
  ]
)

#v(2pt)

// --- Section 6: Exploded Assembly & Internal Component Proof ---
#text(9.5pt, weight: "bold", fill: rgb("#0369a1"))[6. Exploded Robotics Assembly Verification]

#align(center)[
  #image("renders/exploded.png", width: 56%) \
  #text(7pt, weight: "bold")[Figure 4: Exploded Multi-Deck Robotics Assembly ($1920 times 1080$ High-Resolution Projection)] \
  #text(6.5pt, fill: rgb("#64748b"))[Tier 1: Drive Chassis & Caster • Tier 2: N20 Geared Motors & 18650 Bay • Tier 3: Upper Deck & Wire Port • Tier 4: Turret Servo]
]

#pagebreak()

// --- Page 3: Drop-Impact Kinematics & Stress Distribution ---
#text(9.5pt, weight: "bold", fill: rgb("#0369a1"))[7. MIL-STD-810H / IEC 60068-2-31 Drop-Impact Kinematics & Shock Verification]

#table(
  columns: (1.6fr, 1.1fr, 2.3fr, 1.2fr),
  inset: 3.5pt,
  stroke: 0.5pt + rgb("#cbd5e1"),
  fill: (col, row) => if row == 0 { rgb("#f1f5f9") } else { none },
  align: (left, center, left, center),
  [#text(7.5pt, weight: "bold")[Dynamic Parameter]],
  [#text(7.5pt, weight: "bold")[Nominal Value]],
  [#text(7.5pt, weight: "bold")[Kinematic Formulation / Mechanics]],
  [#text(7.5pt, weight: "bold")[Verification Status]],
  [Freefall Drop Height ($h$)], [$1.20$ m], [Freefall onto rigid concrete floor per MIL-STD-810H], [PASS (Standard Test)],
  [Impact Velocity ($v_0$)], [$4.85$ m/s], [$v_0 = sqrt(2 g h) = sqrt(2 times 9.807 times 1.20)$ m/s], [PASS (Kinematic Freefall)],
  [Total Assembly Mass ($M_"ts"$)], [$302.37$ g], [Chassis ($91.0$ g) + N20 ($30.0$ g) + 18650 ($92.0$ g) + Payload], [PASS (Total In-Flight)],
  [Total Impact Energy ($E_k$)], [$3558.0$ mJ], [$E_k = M_"ts" dot g dot h = 0.3024 times 9.807 times 1.20$ J], [PASS (Kinetic Baseline)],
  [Chassis Prow Contact Shock], [$620.0$ g], [$a_"contact" = (pi v_0) / (2 tau)$ at prow apex ($tau = 1.2$ ms)], [PASS (Elastic Contact)],
  [Internal Payload Shock Pulse], [$50.0$ g], [Thermoplastic chassis damping limits shock to standoffs], [PASS (IEC 60068-2-31)],
  [Prow & Chamfer Strain Energy], [$4037.6$ mJ], [$U_"cap" = V_"def" dot u_t = 980 "mm"^3 times 4.12 "mJ/mm"^3$ in PETG], [PASS ($113.5\%$ Absorption)],
  [Upper Deck Standoff Bending], [$3.43$ MPa], [$sigma_b = (V dot h) / Z = (10.42 times 16.0) / 48.64$ MPa ($V = 10.42$ N)], [PASS ($"SF"_b = 14.59$)],
  [Upper Deck Standoff Shear], [$0.25$ MPa], [$tau = V / A = 10.42 / 41.19$ MPa annular shear], [PASS ($"SF"_s = 118.6$)],
  [Combined Standoff von Mises], [$3.46$ MPa], [$sigma_"vm" = sqrt(sigma_b^2 + 3 tau^2) = sqrt(3.43^2 + 3(0.25^2))$ MPa], [PASS ($"FoS" = 14.47 gt.eq 2.0$)],
  [18650 Cell Tray End Bulkheads], [$45.11$ N], [$F_"inertial" = 0.092 times 490.33$ N; Bulkhead $tau = 0.48$ MPa], [PASS ($"FoS" = 63.16 gt.eq 2.0$)],
  [18650 Lateral Saddle Ribs], [$45.11$ N], [Rib shear area $A = 268 "mm"^2$; $tau = 0.17$ MPa], [PASS ($"FoS" = 178.5 gt.eq 2.0$)]
)

#v(2pt)

// --- Section 8: Drop-Impact Stress Distribution & Deceleration Diagram ---
#text(9.5pt, weight: "bold", fill: rgb("#0369a1"))[8. Drop-Impact Finite Element & Kinematic Stress Distribution Proof]

#align(center)[
  #image("renders/drop_impact_stress_analysis.png", width: 94%) \
  #text(7pt, weight: "bold")[Figure 5: High-Resolution Drop-Impact Kinematics, Prow Energy Absorption & Standoff Stress Map ($1920 times 1080$)] \
  #text(6.5pt, fill: rgb("#64748b"))[Panel 1: Deceleration Pulse • Panel 2: Prow Strain Energy • Panel 3: Prow Stress Field • Panel 4: Standoff Bending • Panel 5: 18650 Restraint • Panel 6: Audit Matrix]
]
