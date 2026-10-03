// ==============================================================================
// TerraScout Rover - Parametric Dual-Deck Chassis System
// Project: TerraScout Grounded Telemetry Rover
// Author: TerraScout Engineering Team
// License: CERN-OHL-P v2 / MIT
// ==============================================================================
// Parametric, 3D-printable modular chassis for a dual-motor differential rover.
// Features:
//   - Bottom Deck: N20 gearmotor saddles, 2S 18650 battery cradle, caster mount.
//   - Top Deck: Microcontroller mounts (Pico/ESP32), OLED HUD, BME280 slot,
//               forward SG90 servo panning deck.
//   - Ultrasonic Sensor Turret: HC-SR04/RCWL-1601 dual-barrel press-fit bracket.
//   - N20 Clamping Brackets: Heavy-duty M2 bolt retainers.
//   - Caster Mount: 15mm low-friction steel ball caster riser block.
// ==============================================================================

/* [Render Mode Selection] */
// Select what to display or export (supports either string or integer part_id)
// 0: assembly, 1: exploded, 2: bottom_deck, 3: top_deck, 4: motor_bracket, 5: ultrasonic_bracket, 6: caster_mount, 7: print_bed
part_id     = 0;
render_mode = "assembly";

/* [Global Chassis Dimensions] */
deck_length       = 136.0;   // Overall length of chassis plate (mm)
deck_width        = 94.0;    // Overall width of chassis plate (mm)
deck_thickness    = 3.2;     // Plate rigidity thickness (mm)
corner_radius     = 8.0;     // Filleted corner radius (mm)
deck_spacing      = 28.0;    // Standoff spacing between bottom and top deck (mm)

/* [Standoff Hole Pattern] */
standoff_x_span   = 96.0;    // Center-to-center distance in X (mm)
standoff_y_span   = 76.0;    // Center-to-center distance in Y (mm)
hole_m3_dia       = 3.3;     // Clearance hole for M3 screw/standoff (mm)
hole_m2_dia       = 2.2;     // Clearance hole for M2 screws (mm)

/* [Fastener Tolerances & Nut Pockets] */
m3_nut_flat_nominal = 5.5;    // Nominal M3 hex nut width across flats (ISO 4032 / DIN 934) (mm)
m3_nut_friction_tol = 0.2;    // Friction-fit clearance tolerance (mm)
m3_nut_flat         = m3_nut_flat_nominal + m3_nut_friction_tol; // 5.7 mm flat-to-flat
m3_nut_corner_dia   = m3_nut_flat / cos(30);                     // 6.582 mm corner-to-corner for OpenSCAD $fn=6
m3_nut_depth        = 2.4;                                       // Standard M3 hex nut thickness (mm)

/* [N20 Gear Motor Specifications] */
n20_body_w        = 12.2;    // Motor cross-section width (mm)
n20_body_h        = 10.2;    // Motor cross-section height (mm)
n20_gearbox_l     = 9.2;     // Metal gearbox length (mm)
n20_total_l       = 25.0;    // Total motor body length (mm)
n20_shaft_dia     = 3.0;     // D-shaft diameter (mm)
n20_shaft_len     = 10.0;    // Shaft extension length (mm)
wheel_diameter    = 43.0;    // N20 rubber wheel diameter (mm)
wheel_width       = 18.0;    // Wheel tire tread width (mm)
motor_offset_x    = -8.0;    // X position of drive axle relative to chassis center
motor_mount_spread= 56.0;    // Spacing between inner motor faces (mm)

/* [SG90 Pan Servo Specifications] */
servo_body_w      = 12.4;    // Micro servo width (mm)
servo_body_l      = 23.0;    // Micro servo body length (mm)
servo_flange_l    = 32.5;    // Flange length across mounting ears (mm)
servo_height      = 22.8;    // Servo body depth (mm)
servo_offset_x    = 52.0;    // Forward position of scanning servo (mm)

/* [Ultrasonic HC-SR04 Bracket Parameters] */
hc_barrel_dia     = 16.3;    // Diameter of transmitter/receiver eye cylinders (mm)
hc_barrel_spacing = 26.0;    // Center-to-center distance of transducer barrels (mm)
hc_barrel_depth   = 8.0;     // Depth of retention barrel sleeves (mm)
hc_plate_w        = 46.0;    // Sensor faceplate width (mm)
hc_plate_h        = 22.0;    // Sensor faceplate height (mm)

/* [Ball Caster Parameters] */
caster_ball_dia   = 15.0;    // Steel ball diameter (mm)
caster_flange_dia = 28.0;    // Mounting flange diameter (mm)
caster_hole_dist  = 20.0;    // Flange bolt spacing (mm)
caster_x_pos      = -50.0;   // Rearward position of caster (mm)

/* [Quality / Resolution] */
$fn = 48;

// ==============================================================================
// Helper Modules
// ==============================================================================

// Rounded rectangle with centered origin
module rounded_rect_2d(length, width, r) {
    hull() {
        translate([ length/2 - r,  width/2 - r]) circle(r=r);
        translate([-length/2 + r,  width/2 - r]) circle(r=r);
        translate([ length/2 - r, -width/2 + r]) circle(r=r);
        translate([-length/2 + r, -width/2 + r]) circle(r=r);
    }
}

// 4-corner M3 standoff pattern with M3 hex nut pockets
module standoff_holes(x_span, y_span, dia, depth=30, with_nut_pockets=false, nut_z=0, nut_h=2.0) {
    for (sx = [-1, 1]) {
        for (sy = [-1, 1]) {
            translate([sx * x_span/2, sy * y_span/2, 0]) {
                cylinder(d=dia, h=depth, center=true);
                if (with_nut_pockets) {
                    translate([0, 0, nut_z])
                        rotate([0, 0, 30])
                        cylinder(d=m3_nut_corner_dia, h=nut_h, $fn=6);
                }
            }
        }
    }
}

// Hexagonal weight relief lattice
module hex_weight_relief_cutout(rows=3, cols=3, radius=6.0, spacing=16.0) {
    for (ix = [-(cols-1)/2 : 1 : (cols-1)/2]) {
        for (iy = [-(rows-1)/2 : 1 : (rows-1)/2]) {
            translate([ix * spacing, iy * spacing, 0])
                rotate([0, 0, 30])
                cylinder(r=radius, h=20, center=true, $fn=6);
        }
    }
}

// Zip tie slot
module zip_tie_slot(length=12, width=3.5, thickness=10) {
    cube([length, width, thickness], center=true);
}

// ==============================================================================
// Component 1: Bottom Deck Plate
// ==============================================================================
module bottom_deck() {
    difference() {
        union() {
            // Main chassis plate
            linear_extrude(height=deck_thickness)
                rounded_rect_2d(deck_length, deck_width, corner_radius);

            // N20 Motor alignment cradles (Left & Right)
            for (side = [-1, 1]) {
                translate([motor_offset_x, side * (motor_mount_spread/2 + n20_body_w/2), deck_thickness])
                    difference() {
                        cube([n20_total_l + 2, n20_body_w + 3.0, 2.5], center=true);
                        // Recess channel for motor body
                        cube([n20_total_l + 4, n20_body_w, 3.0], center=true);
                    }
            }
        }

        // 1. M3 Standoff mounting holes with underside hex nut pockets (5.5mm + 0.2mm friction fit)
        standoff_holes(standoff_x_span, standoff_y_span, hole_m3_dia, depth=deck_thickness*4, with_nut_pockets=true, nut_z=-0.1, nut_h=1.8);

        // 2. Drive wheel clearance cutouts
        for (side = [-1, 1]) {
            translate([motor_offset_x, side * (deck_width/2 - 2), -1])
                cube([wheel_diameter + 4, wheel_width + 8, deck_thickness + 2], center=true);
        }

        // 3. N20 Motor bracket M2 mounting holes
        for (side = [-1, 1]) {
            for (bx = [-8, 8]) {
                translate([motor_offset_x + bx, side * (motor_mount_spread/2 - 3.5), -1])
                    cylinder(d=hole_m2_dia, h=deck_thickness + 2);
                translate([motor_offset_x + bx, side * (motor_mount_spread/2 + n20_body_w + 3.5), -1])
                    cylinder(d=hole_m2_dia, h=deck_thickness + 2);
            }
        }

        // 4. Rear Ball Caster mount holes
        translate([caster_x_pos, -caster_hole_dist/2, -1])
            cylinder(d=hole_m3_dia, h=deck_thickness + 2);
        translate([caster_x_pos,  caster_hole_dist/2, -1])
            cylinder(d=hole_m3_dia, h=deck_thickness + 2);
        // Center drop recess for ball housing
        translate([caster_x_pos, 0, -1])
            cylinder(d=caster_ball_dia + 2, h=deck_thickness + 2);

        // 5. Battery Cradle retention zip-tie slots (2S 18650 battery pack)
        translate([15, -18, deck_thickness/2]) zip_tie_slot(14, 3.5);
        translate([15,  18, deck_thickness/2]) zip_tie_slot(14, 3.5);
        translate([-25, -18, deck_thickness/2]) zip_tie_slot(14, 3.5);
        translate([-25,  18, deck_thickness/2]) zip_tie_slot(14, 3.5);

        // 6. Central cable routing passthrough
        translate([0, 0, -1])
            linear_extrude(height=deck_thickness + 2)
                rounded_rect_2d(22, 14, 3);
        
        // 7. Weight relief & ventilation pattern
        translate([18, 0, 0])
            hex_weight_relief_cutout(rows=2, cols=2, radius=5.0, spacing=14.0);
    }
}

// ==============================================================================
// Component 2: Top Deck Plate
// ==============================================================================
module top_deck() {
    difference() {
        union() {
            // Main deck plate
            linear_extrude(height=deck_thickness)
                rounded_rect_2d(deck_length, deck_width, corner_radius);

            // Servo mounting deck reinforced boss on forward prow
            translate([servo_offset_x, 0, deck_thickness])
                difference() {
                    cube([servo_body_l + 8, servo_body_w + 6, 2.5], center=true);
                    cube([servo_body_l, servo_body_w, 4], center=true);
                }
        }

        // 1. M3 Standoff holes matching bottom deck with top-face hex nut pockets
        standoff_holes(standoff_x_span, standoff_y_span, hole_m3_dia, depth=deck_thickness*4, with_nut_pockets=true, nut_z=deck_thickness - 1.7, nut_h=1.8);

        // 2. Forward SG90 Servo cutout & mounting ear screw holes
        translate([servo_offset_x, 0, 0]) {
            // Center body pocket
            cube([servo_body_l, servo_body_w, 30], center=true);
            // Flange screw holes (M2)
            translate([-servo_flange_l/2 + 2.5, 0, 0])
                cylinder(d=hole_m2_dia, h=30, center=true);
            translate([ servo_flange_l/2 - 2.5, 0, 0])
                cylinder(d=hole_m2_dia, h=30, center=true);
        }

        // 3. Raspberry Pi Pico / MCU mounting holes (51mm x 21mm, holes at 47mm x 11.4mm)
        translate([-12, 0, 0]) {
            for (mx = [-23.5, 23.5]) {
                for (my = [-5.7, 5.7]) {
                    translate([mx, my, 0])
                        cylinder(d=hole_m2_dia, h=30, center=true);
                }
            }
        }

        // 4. SSD1306 0.96" OLED HUD mounting holes (23.5mm x 23.5mm square pattern)
        translate([28, -22, 0]) {
            for (ox = [-11.75, 11.75]) {
                for (oy = [-11.75, 11.75]) {
                    translate([ox, oy, 0])
                        cylinder(d=hole_m2_dia, h=30, center=true);
                }
            }
            // Screen view/cable clearance slot
            cube([18, 12, 30], center=true);
        }

        // 5. BME280 Environmental Sensor mounting pattern (15mm spacing)
        translate([28, 22, 0]) {
            translate([-7.5, 0, 0]) cylinder(d=hole_m2_dia, h=30, center=true);
            translate([ 7.5, 0, 0]) cylinder(d=hole_m2_dia, h=30, center=true);
            // Sensing vent hole
            cylinder(d=6.0, h=30, center=true);
        }

        // 6. Center wire harness passthrough
        translate([-12, -26, 0])
            cube([16, 8, 30], center=true);
        translate([-12,  26, 0])
            cube([16, 8, 30], center=true);

        // 7. Rear deck hexagonal ventilation array
        translate([-42, 0, 0])
            hex_weight_relief_cutout(rows=3, cols=2, radius=4.5, spacing=12.0);
    }
}

// ==============================================================================
// Component 3: N20 Heavy-Duty Motor Mounting Bracket (x2 needed)
// ==============================================================================
module n20_motor_bracket() {
    bracket_l = 18.0;
    bracket_w = n20_body_w + 11.0;
    bracket_h = n20_body_h + 3.0;

    difference() {
        // Outer housing block with rounded top
        hull() {
            translate([-bracket_l/2, -bracket_w/2, 0])
                cube([bracket_l, bracket_w, 3.0]);
            translate([-bracket_l/2, -n20_body_w/2 - 1.5, bracket_h - 2])
                cube([bracket_l, n20_body_w + 3.0, 2.0]);
        }

        // Motor gearbox inner cavity
        translate([-bracket_l/2 - 1, -n20_body_w/2, -0.1])
            cube([bracket_l + 2, n20_body_w, n20_body_h + 0.3]);

        // M2 clamp screw holes
        for (side = [-1, 1]) {
            translate([0, side * (n20_body_w/2 + 3.5), -1])
                cylinder(d=hole_m2_dia, h=bracket_h + 5);
            // Counterbore for screw head
            translate([0, side * (n20_body_w/2 + 3.5), 3.0])
                cylinder(d=4.2, h=bracket_h + 5);
        }
    }
}

// ==============================================================================
// Component 4: Ultrasonic HC-SR04 Turret Eye Bracket
// ==============================================================================
module ultrasonic_bracket() {
    turret_w = hc_plate_w + 4.0;
    turret_h = hc_plate_h + 4.0;
    wall_t   = 2.8;

    difference() {
        union() {
            // Front sensor faceplate
            translate([0, 0, turret_h/2])
                cube([wall_t, turret_w, turret_h], center=true);

            // Transmitter / Receiver cylindrical retention sleeves
            for (sy = [-1, 1]) {
                translate([hc_barrel_depth/2, sy * hc_barrel_spacing/2, turret_h/2])
                    rotate([0, 90, 0])
                    cylinder(d=hc_barrel_dia + 2.8, h=hc_barrel_depth, center=true);
            }

            // Lower horn receiver mounting stem for SG90 servo horn attachment
            translate([-4.0, 0, -3.0])
                difference() {
                    cube([12.0, 16.0, 6.0], center=true);
                    // Central horn screw pivot hole
                    translate([0, 0, -4]) cylinder(d=2.4, h=10);
                    // Horn flange recess slot
                    translate([0, 0, 1.2]) cube([8.5, 15.0, 2.5], center=true);
                }
        }

        // Dual 16.3mm eye barrel through-holes for HC-SR04 ultrasonic transducers
        for (sy = [-1, 1]) {
            translate([-2, sy * hc_barrel_spacing/2, turret_h/2])
                rotate([0, 90, 0])
                cylinder(d=hc_barrel_dia, h=hc_barrel_depth + 6);
        }

        // Crystal oscillator clearance slot on PCB rear
        translate([-wall_t, 0, turret_h/2 - 4])
            cube([4, 12, 6], center=true);
    }
}

// ==============================================================================
// Component 5: Caster Ball Standoff Riser Mount
// ==============================================================================
module caster_mount() {
    mount_h = 10.0;
    flange_l = 32.0;
    flange_w = 18.0;

    difference() {
        union() {
            // Main standoff block
            translate([0, 0, mount_h/2])
                hull() {
                    cube([flange_l - 6, flange_w, mount_h], center=true);
                    cylinder(d=flange_w, h=mount_h, center=true);
                }
        }

        // Central ball caster housing socket (15mm steel ball)
        translate([0, 0, -1])
            cylinder(d=caster_ball_dia + 0.8, h=mount_h + 2);

        // Mounting holes (M3 clearance)
        translate([-caster_hole_dist/2, 0, -1])
            cylinder(d=hole_m3_dia, h=mount_h + 4);
        translate([ caster_hole_dist/2, 0, -1])
            cylinder(d=hole_m3_dia, h=mount_h + 4);

        // Nut traps on top face (5.5mm flat-to-flat with 0.2mm friction fit = 5.7mm flat-to-flat)
        translate([-caster_hole_dist/2, 0, mount_h - 2.8])
            cylinder(d=m3_nut_corner_dia, h=4, $fn=6);
        translate([ caster_hole_dist/2, 0, mount_h - 2.8])
            cylinder(d=m3_nut_corner_dia, h=4, $fn=6);
    }
}

// ==============================================================================
// Hardware Mocks (For Assembly Visualization Mode)
// ==============================================================================
module mock_n20_motor() {
    color([0.7, 0.7, 0.2]) { // Brass gearbox
        translate([0, 0, 0])
            cube([n20_gearbox_l, n20_body_w, n20_body_h], center=true);
    }
    color([0.75, 0.75, 0.75]) { // Silver motor can
        translate([-n20_total_l/2 + 2, 0, 0])
            rotate([0, 90, 0])
            cylinder(d=10.0, h=n20_total_l - n20_gearbox_l, center=true);
        // Output shaft
        translate([n20_gearbox_l/2 + n20_shaft_len/2, 0, 0])
            rotate([0, 90, 0])
            cylinder(d=n20_shaft_dia, h=n20_shaft_len, center=true);
    }
}

module mock_wheel() {
    color([0.9, 0.9, 0.9]) // White rim
        rotate([90, 0, 0])
        cylinder(d=wheel_diameter - 6, h=wheel_width - 2, center=true);
    color([0.15, 0.15, 0.15]) // Black rubber tire
        rotate([90, 0, 0])
        difference() {
            cylinder(d=wheel_diameter, h=wheel_width, center=true);
            cylinder(d=wheel_diameter - 6.5, h=wheel_width + 1, center=true);
        }
}

module mock_sg90_servo() {
    color([0.1, 0.4, 0.8, 0.85]) { // Blue translucent case
        cube([servo_body_l, servo_body_w, servo_height], center=true);
        // Flange ears
        translate([0, 0, 2])
            cube([servo_flange_l, servo_body_w, 2.5], center=true);
        // Output spline boss
        translate([servo_body_l/2 - 6, 0, servo_height/2 + 2])
            cylinder(d=5.0, h=4);
    }
}

module mock_hc_sr04() {
    color([0.1, 0.4, 0.8]) // Blue PCB
        translate([-1.5, 0, hc_plate_h/2])
        cube([1.6, hc_plate_w, hc_plate_h], center=true);
    color([0.8, 0.8, 0.85]) { // Metallic eye transducers
        for (sy = [-1, 1]) {
            translate([hc_barrel_depth/2, sy * hc_barrel_spacing/2, hc_plate_h/2])
                rotate([0, 90, 0])
                cylinder(d=16.0, h=hc_barrel_depth, center=true);
        }
    }
}

module mock_oled_display() {
    color([0.1, 0.1, 0.8]) // Blue PCB
        cube([27, 27, 1.6], center=true);
    color([0.05, 0.05, 0.05]) // Black OLED glass
        translate([0, 0, 1.2])
        cube([24, 15, 1.2], center=true);
}

module mock_mcu_pico() {
    color([0.1, 0.6, 0.2]) // Green PCB
        cube([51, 21, 1.6], center=true);
    color([0.8, 0.8, 0.8]) // Metal RF shield / RP2040 package
        translate([-5, 0, 1.5])
        cube([12, 12, 1.8], center=true);
}

module mock_18650_battery_sled() {
    sled_l = 75.0;
    sled_w = 40.0;
    sled_h = 19.5;

    // Black ABS plastic battery tray sled
    color([0.15, 0.15, 0.18]) {
        difference() {
            translate([0, 0, sled_h/2])
                cube([sled_l, sled_w, sled_h], center=true);
            // Cell bay hollows
            for (cy = [-9.5, 9.5]) {
                translate([0, cy, sled_h/2 + 2])
                    rotate([0, 90, 0])
                    cylinder(d=18.6, h=67, center=true);
            }
        }
    }

    // 2x 18650 Li-ion Cells (Cyan/Green jacket)
    for (cy = [-9.5, 9.5]) {
        color([0.1, 0.75, 0.45]) // Samsung/Panasonic 18650 green jacket
            translate([0, cy, 18.4/2 + 1.2])
            rotate([0, 90, 0])
            cylinder(d=18.4, h=65.0, center=true);
        // Nickel plated terminals (+ / -)
        color([0.85, 0.85, 0.9])
            translate([33.0, cy, 18.4/2 + 1.2])
            rotate([0, 90, 0])
            cylinder(d=7.0, h=1.5, center=true);
    }
}

module mock_standoff(height=28) {
    color([0.85, 0.75, 0.2]) // Brass hex standoffs
        rotate([0, 0, 30])
        cylinder(d=5.5, h=height, center=true, $fn=6);
}

// ==============================================================================
// Full Assembly View
// ==============================================================================
module full_assembly(explode_dist=0) {
    // 1. Bottom Deck Plate
    color([0.2, 0.25, 0.3])
        bottom_deck();

    // 1b. 2S 18650 Battery Sled & Power Subsystem
    translate([-5, 0, deck_thickness + explode_dist * 0.2])
        mock_18650_battery_sled();

    // 2. Brass Standoffs (4x)
    for (sx = [-1, 1]) {
        for (sy = [-1, 1]) {
            translate([sx * standoff_x_span/2, sy * standoff_y_span/2, deck_thickness + deck_spacing/2 + explode_dist * 0.4])
                mock_standoff(deck_spacing);
        }
    }

    // 3. Motors & Brackets (Left & Right)
    for (side = [-1, 1]) {
        translate([motor_offset_x, side * (motor_mount_spread/2 + n20_body_w/2), deck_thickness + n20_body_h/2]) {
            // N20 Motor
            rotate([0, 0, side > 0 ? 90 : -90])
                mock_n20_motor();

            // Motor Mounting Bracket
            color([1.0, 0.5, 0.1])
                translate([0, 0, -n20_body_h/2])
                n20_motor_bracket();

            // Drive Wheel
            translate([0, side * (n20_total_l/2 + wheel_width/2 + 2), 0])
                mock_wheel();
        }
    }

    // 4. Rear Ball Caster Mount & Ball
    translate([caster_x_pos, 0, -10 - explode_dist * 0.3]) {
        color([1.0, 0.5, 0.1])
            rotate([0, 180, 90])
            caster_mount();
        // Steel ball
        color([0.9, 0.9, 0.95])
            translate([0, 0, -2])
            sphere(d=caster_ball_dia);
    }

    // 5. Top Deck Plate
    translate([0, 0, deck_thickness + deck_spacing + explode_dist]) {
        color([0.2, 0.35, 0.45])
            top_deck();

        // Raspberry Pi Pico MCU
        translate([-12, 0, deck_thickness + 1.5])
            mock_mcu_pico();

        // OLED HUD Display
        translate([28, -22, deck_thickness + 2.0])
            mock_oled_display();

        // SG90 Panning Servo
        translate([servo_offset_x, 0, -servo_height/2 + deck_thickness]) {
            mock_sg90_servo();

            // Ultrasonic Panning Turret Assembly
            translate([servo_body_l/2 - 6, 0, servo_height/2 + 6]) {
                color([1.0, 0.5, 0.1])
                    ultrasonic_bracket();
                mock_hc_sr04();
            }
        }
    }
}

// ==============================================================================
// 3D Print Bed Multi-Part Layout (Ready for single-print batch export)
// ==============================================================================
module print_bed_layout() {
    // Bottom Deck (Left side)
    translate([-30, -50, 0])
        bottom_deck();

    // Top Deck (Right side)
    translate([-30, 50, 0])
        top_deck();

    // 2x N20 Motor Brackets
    translate([60, -35, 0])
        rotate([0, 0, 90])
        n20_motor_bracket();
    translate([60, -10, 0])
        rotate([0, 0, 90])
        n20_motor_bracket();

    // Caster Riser Mount
    translate([60, 20, 0])
        caster_mount();

    // Ultrasonic Turret Eye Bracket (Flat on rear face)
    translate([60, 48, 0])
        rotate([90, 0, 0])
        ultrasonic_bracket();
}

// ==============================================================================
// Execution Switch
// ==============================================================================
if (part_id == 1 || render_mode == "exploded") {
    full_assembly(explode_dist=48);
} else if (part_id == 2 || render_mode == "bottom_deck") {
    bottom_deck();
} else if (part_id == 3 || render_mode == "top_deck") {
    top_deck();
} else if (part_id == 4 || render_mode == "motor_bracket") {
    n20_motor_bracket();
} else if (part_id == 5 || render_mode == "ultrasonic_bracket") {
    ultrasonic_bracket();
} else if (part_id == 6 || render_mode == "caster_mount") {
    caster_mount();
} else if (part_id == 7 || render_mode == "print_bed") {
    print_bed_layout();
} else {
    // Default assembly
    full_assembly(explode_dist=0);
}
