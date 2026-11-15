// pHloat sensor enclosure, rev A. Units: mm.
//   openscad -D "part=\"body\"" -o phloat_body.stl phloat_enclosure.scad
//   openscad -D "part=\"lid\""  -o phloat_lid.stl  phloat_enclosure.scad
// The PCB mounts component-side DOWN on four posts; the 18650 faces the lid, so
// removing the lid is all it takes to swap the cell. One penetration: the probe cable gland.
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

// --- PCB (from gen_pcb.py)
pcb_l = 118; pcb_w = 32; pcb_t = 1.6;
hole_inset = 3.2;             // M2.5 mounting holes from each corner

// --- fit knobs: measure the real parts and adjust
bay       = 45;    // space past the SMA jack for the mated plug and cable bend
post_h    = 12;    // floor to PCB: clears SMA plug, XIAO and the gland nut
batt_h    = 22;    // PCB to lid: Keystone 1042 holder + 18650. MEASURE before printing.
side_gap  = 1;     // PCB edge to wall
gland_d   = 16.2;  // clearance hole for an M16x1.5 gland (SMA plug must pass through it)
pilot_d   = 2.1;   // M2.5 self-tapping pilot in the posts
insert_d  = 4.0;   // M3 heat-set insert hole in the flange
oring_cs  = 2.0;   // O-ring cord diameter
groove_w  = 2.6;   // FDM-friendly groove for 2.0 cord
groove_d  = 1.5;   // about 25% squeeze

// --- mounting ears: flat tabs at the base of the two end walls, for screws or zip ties
mount_ears = true; // false = a plain box with no ears
ear_w    = 14;     // width of each tab
ear_l    = 18;     // how far a tab sticks out from the wall
ear_t    = 4;      // tab thickness
ear_hole = 4.5;    // hole for an M4 screw or a zip tie

wall = 3; floor_t = 3; lid_t = 4;
flange = 7;        // extra width at the rim for groove + screws
flange_h = 8;
r = 4;             // inside corner radius
$fn = 48;

// Derived sizes: the inside of the box, worked out from the knobs above.
in_l = bay + pcb_l + side_gap;
in_w = pcb_w + 2 * side_gap;
in_h = post_h + pcb_t + batt_h;
out_h = floor_t + in_h;

groove_off = wall + 0.2 + groove_w / 2;      // groove centreline, measured out from the cavity wall
screw_off  = wall + flange - 3.2;            // screw centreline, outside the O-ring

// A box with rounded vertical corners: four cylinders at the corners, wrapped in a hull.
module rrect(l, w, h, rad) {                 // rounded box grown outward from an l x w footprint at the origin
    hull() for (x = [rad, l - rad], y = [rad, w - rad]) translate([x, y, 0]) cylinder(r = rad, h = h);
}
// The cavity's outline pushed outward by `off` on every side, `h` tall, starting at height z.
// grown(0) is the cavity itself, grown(wall) is the outside of the walls, and so on.
module grown(off, h, z = 0) {                // cavity footprint offset outward by `off`
    translate([-off, -off, z]) rrect(in_l + 2 * off, in_w + 2 * off, h, r + off);
}
// The positions of the eight lid screws: four along each long side, outside the O-ring.
function screw_xy() = let (o = screw_off, xs = [-o, in_l * 0.33, in_l * 0.67, in_l + o])
    concat([for (x = xs) [x, -o]], [for (x = xs) [x, in_w + o]]);

// The body. Start with the solid outer shape plus the thicker rim flange, then cut away:
// the cavity, the O-ring groove, the screw-insert holes and the cable gland hole.
// Finally add the four posts the circuit board screws onto.
module body() {
    difference() {
        union() {
            grown(wall, out_h, -floor_t);
            grown(wall + flange, flange_h, in_h - flange_h);
        }
        grown(0, in_h + 1);                                         // cavity
        translate([0, 0, in_h - groove_d]) difference() {           // O-ring groove
            grown(groove_off + groove_w / 2, groove_d + 1);
            grown(groove_off - groove_w / 2, groove_d + 2, -0.5);
        }
        for (p = screw_xy()) translate([p[0], p[1], in_h - 6.5]) cylinder(d = insert_d, h = 7);
        translate([-wall - flange - 1, in_w / 2, post_h + pcb_t / 2])   // gland, on the SMA axis
            rotate([0, 90, 0]) cylinder(d = gland_d, h = wall + flange + 2);
    }
    for (x = [hole_inset, pcb_l - hole_inset], y = [hole_inset, pcb_w - hole_inset])
        translate([bay + x, side_gap + y, 0]) difference() {
            cylinder(d = 7, h = post_h);
            translate([0, 0, post_h - 8]) cylinder(d = pilot_d, h = 8.1);
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

// Produce the requested part. "assembly" shows the body, a see-through board and battery, and
// the lid floating above, for checking the fit by eye.
if (part == "body") body();
else if (part == "lid") lid();
else {
    body();
    %translate([bay, side_gap, post_h]) cube([pcb_l, pcb_w, pcb_t]);            // PCB
    %translate([bay + 22, side_gap + 6.7, post_h + pcb_t]) cube([88, 18.6, 18.6]); // 18650 envelope
    translate([0, 0, in_h + 12]) lid();
}

// O-ring cord length (groove centreline):
echo(oring_length_mm = 2 * (in_l + in_w) - 8 * r + 2 * PI * (r + groove_off));
echo(outside_mm = [in_l + 2 * (wall + flange), in_w + 2 * (wall + flange), out_h + lid_t]);
echo(length_over_ears_mm = in_l + 2 * (wall + (mount_ears ? ear_l : 0)));
