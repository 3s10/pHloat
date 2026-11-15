// Fermenter controller enclosure, rev A. Units: mm.
//   openscad -D "part=\"body\"" -o controller_body.stl controller_enclosure.scad
//   openscad -D "part=\"lid\""  -o controller_lid.stl  controller_enclosure.scad
// PCB sits component-side up on four M3 posts. Seven cable glands: four probes on one long
// wall, power + two pumps on the other. Wiring bays on three sides give the wires room to bend
// into the terminals. USB-C is reached by taking the lid off.
// Mounting ears on both ends take screws or zip ties (set mount_ears = false for a plain box).

// HOW TO READ AN OPENSCAD FILE
//   OpenSCAD builds a 3D shape from a description, not by drawing. You combine simple solids:
//     cube(), cylinder()        basic shapes
//     translate([x, y, z])      move the shape that follows
//     rotate([x, y, z])         turn the shape that follows (degrees about each axis)
//     union() { ... }           add shapes together
//     difference() { A; B; C }  start with A and cut B, C, ... out of it
//     hull() { ... }            the tight skin stretched around several shapes
//     module name() { ... }     a reusable recipe, like a function that makes a shape
//   A `%` in front of a shape draws it see-through and leaves it out of the exported part.
//   All sizes are millimetres. The numbers at the top are the knobs; everything below is
//   calculated from them, so changing one number resizes the whole box consistently.
//
// HOW THE BOX IS BUILT
//   Everything is measured from the inside: the cavity is in_l x in_w x in_h, starting at the
//   origin. Walls, the rim flange and the lid are made by growing that cavity shape outward.
//
// Which part to produce. The export commands at the top of the file override this.
part = "assembly";            // "body" | "lid" | "assembly"

// --- PCB (from gen_pcb.py; y runs the other way there: scad_y = pcb_w - board_y)
pcb_l = 92; pcb_w = 62; pcb_t = 1.6;
holes = [[4, 4], [88, 4], [88, 58], [4, 44]];   // M3 mounting holes

// --- fit knobs: measure the real parts and adjust
bay_probe = 28;    // space past the probe terminals (board top edge)
bay_pump  = 26;    // space past the pump terminals (board bottom edge)
bay_power = 16;    // space left of the power terminal
gap_usb   = 4;     // XIAO USB end overhangs the board by about 1.2 mm
post_h    = 6;     // floor to PCB underside: clears through-hole leads
comp_h    = 20;    // PCB top to lid: tallest part is the 220 uF capacitor. MEASURE yours.
gland_d   = 12.3;  // clearance hole for M12x1.5 glands (3-6.5 mm cable). PG7 needs 12.7.
gland_nut = 18;    // across the corners of the gland's nut. MEASURE yours.
gland_z   = 10;    // gland centre above the inside floor
gland_pitch_probe = 22;
gland_pitch_pump  = 30;
pilot_d   = 2.5;   // M3 self-tapping pilot in the posts
insert_d  = 4.0;   // M3 heat-set insert hole in the flange
groove_w  = 2.6;   // for 2.0 mm O-ring cord
groove_d  = 1.5;

// --- mounting ears: flat tabs at the base of the two end walls, for screws or zip ties
mount_ears = true; // false = a plain box with no ears
ear_w    = 14;     // width of each tab
ear_l    = 18;     // how far a tab sticks out from the wall
ear_t    = 4;      // tab thickness
ear_hole = 4.5;    // hole for an M4 screw or a zip tie

wall = 3; floor_t = 3; lid_t = 4;
flange = 7; flange_h = 8;
r = 4;
$fn = 48;

// Derived sizes: the inside of the box and where the board sits in it, from the knobs above.
in_l = bay_power + pcb_l + gap_usb;
in_w = bay_pump + pcb_w + bay_probe;
in_h = post_h + pcb_t + comp_h;
out_h = floor_t + in_h;
pcb_x = bay_power; pcb_y = bay_pump;

groove_off = wall + 0.2 + groove_w / 2;
screw_off  = wall + flange - 3.2;

// A box with rounded vertical corners: four cylinders at the corners, wrapped in a hull.
module rrect(l, w, h, rad) {
    hull() for (x = [rad, l - rad], y = [rad, w - rad]) translate([x, y, 0]) cylinder(r = rad, h = h);
}
// The cavity's outline pushed outward by `off` on every side, `h` tall, starting at height z.
// grown(0) is the cavity itself, grown(wall) is the outside of the walls, and so on.
module grown(off, h, z = 0) {
    translate([-off, -off, z]) rrect(in_l + 2 * off, in_w + 2 * off, h, r + off);
}
// The positions of the eight lid screws: a 3 x 3 grid around the rim with the centre left out.
function screw_xy() = let (o = screw_off, xs = [-o, in_l / 2, in_l + o], ys = [-o, in_w / 2, in_w + o])
    [for (x = xs, y = ys) if (!(x == in_l / 2 && y == in_w / 2)) [x, y]];

// A round hole for one cable gland through one of the two long walls, at position x along it.
module gland_hole_y(x, far) {               // through a long wall: far = true is the probe side
    translate([x, far ? in_w - 1 : -wall - flange - 1, gland_z])
        rotate([-90, 0, 0]) cylinder(d = gland_d, h = wall + flange + 2);
}

// The body. Start with the solid outer shape plus the thicker rim flange, then cut away:
// the cavity, the O-ring groove, the screw-insert holes and the seven gland holes.
// Finally add the four posts the circuit board screws onto.
module body() {
    difference() {
        union() {
            grown(wall, out_h, -floor_t);
            grown(wall + flange, flange_h, in_h - flange_h);
        }
        grown(0, in_h + 1);
        translate([0, 0, in_h - groove_d]) difference() {
            grown(groove_off + groove_w / 2, groove_d + 1);
            grown(groove_off - groove_w / 2, groove_d + 2, -0.5);
        }
        for (p = screw_xy()) translate([p[0], p[1], in_h - 6.5]) cylinder(d = insert_d, h = 7);
        for (i = [-1.5 : 1.5]) gland_hole_y(in_l / 2 + i * gland_pitch_probe, true);    // 4 probes
        for (i = [-1 : 1])     gland_hole_y(in_l / 2 + i * gland_pitch_pump, false);    // power, cool pump, warm pump
    }
    for (h = holes) translate([pcb_x + h[0], pcb_y + h[1], 0]) difference() {
        cylinder(d = 8, h = post_h);
        translate([0, 0, post_h - 5.5]) cylinder(d = pilot_d, h = 5.6);
    }
    ears();
}

// Mounting ears: two tabs on each end wall, flush with the bottom of the box so it sits flat
// against a wall or bracket. Each hole is 12 mm out from the wall, which puts it clear of the
// rim flange overhanging above, so a screwdriver can reach it from the lid side.
module ears() {
    if (mount_ears) for (end = [0, 1], y = [0, in_w - ear_w]) {
        x0 = end == 0 ? -wall - ear_l : in_l + wall - 1;         // the tab overlaps the wall by 1 mm so they fuse
        hole_x = end == 0 ? ear_l - 12 : 1 + 12;                 // measured from the tab's own corner
        translate([x0, y, -floor_t]) difference() {
            cube([ear_l + 1, ear_w, ear_t]);
            translate([hole_x, ear_w / 2, -1]) cylinder(d = ear_hole, h = ear_t + 2);
        }
    }
}

// The lid: a flat plate the size of the flange, with a clearance hole for each screw.
module lid() {
    difference() {
        grown(wall + flange, lid_t);
        for (p = screw_xy()) translate([p[0], p[1], -1]) cylinder(d = 3.4, h = lid_t + 2);
    }
}

// Produce the requested part. "assembly" shows the body, a see-through board, and the lid
// floating above, for checking the fit by eye.
if (part == "body") body();
else if (part == "lid") lid();
else {
    body();
    %translate([pcb_x, pcb_y, post_h]) cube([pcb_l, pcb_w, pcb_t]);
    translate([0, 0, in_h + 14]) lid();
}

echo(oring_length_mm = 2 * (in_l + in_w) - 8 * r + 2 * PI * (r + groove_off));
echo(outside_mm = [in_l + 2 * (wall + flange), in_w + 2 * (wall + flange), out_h + lid_t]);
echo(length_over_ears_mm = in_l + 2 * (wall + (mount_ears ? ear_l : 0)));
// The gland nut must sit on flat wall: above the base and below the rim flange.
nut_clear = [gland_z + floor_t - gland_nut / 2, (in_h - flange_h) - (gland_z + gland_nut / 2)];
echo(gland_nut_clearance_mm = nut_clear);
assert(nut_clear[0] >= 0 && nut_clear[1] >= 0, "gland nut hits the base or the rim flange: raise comp_h or move gland_z");
assert(gland_pitch_probe >= gland_nut + 2 && gland_pitch_pump >= gland_nut + 2, "glands too close together");
