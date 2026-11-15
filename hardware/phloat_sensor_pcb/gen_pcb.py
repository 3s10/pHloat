"""Generate phloat_sensor.kicad_pcb. Run with KiCad's bundled Python:

  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen_pcb.py [--pads]

This script is the source of truth for the board: netlist, placement and routing.
ponytail: no .kicad_sch -- the NETS table below is the schematic. Draw one in
eeschema when the design needs GUI edits or a formal review.
ponytail: no DS18B20 footprint -- beer temperature comes from the Tilt over BLE.
"""
# WORDS USED IN THIS FILE
#   footprint  the copper pattern one part is soldered onto (its pads), plus its outline.
#   pad        one solder point of a footprint. Pads are numbered to match the part's pins.
#   net        a set of pads that must be electrically connected (one "wire" of the circuit).
#   track      a copper line on the board joining pads of the same net.
#   via        a small plated hole that takes a track from one side of the board to the other.
#   zone       a large filled copper area (a "pour"), here used for ground on both sides.
#   layer      F.Cu = copper on the front (top), B.Cu = copper on the back (bottom).
#   DRC        design-rule check: KiCad's test that nothing is shorted, too close, or left
#              unconnected. Run it after every change (the command is in the README).
#
# HOW THE SCRIPT WORKS
#   1. PARTS says which footprint goes where.
#   2. NETS says which pads belong together.
#   3. build() places the footprints and labels every pad with its net.
#   4. route() draws the tracks, vias and ground zones by hand-written coordinates.
#   5. The board is saved as a .kicad_pcb file that opens in KiCad.
#   All coordinates are in millimetres from the board's top-left corner; x grows to the right
#   and y grows DOWNWARD (KiCad's convention).
import os
import sys
import pcbnew

# Where things are on disk: this script's folder, KiCad's standard footprint library, the
# project's own footprint folder, and the board file to write.
HERE = os.path.dirname(os.path.abspath(__file__))
KLIB = os.environ.get("KICAD10_FOOTPRINT_DIR", r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
LOCAL = os.path.join(HERE, "phloat.pretty")
OUT = os.path.join(HERE, "phloat_sensor.kicad_pcb")

OX, OY = 40.0, 40.0          # board origin on the KiCad sheet
L, W = 118.0, 32.0           # board size, mm
CY = W / 2


# Convert a position in millimetres on OUR board into the form KiCad wants: a point on its
# drawing sheet, in its internal units (nanometres). Every coordinate below goes through this.
def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))


R0805 = (KLIB + "/Resistor_SMD.pretty", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C0805 = (KLIB + "/Capacitor_SMD.pretty", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
HOLE = (KLIB + "/MountingHole.pretty", "MountingHole_2.7mm_M2.5")

# ref: (library dir, footprint, value, x, y, rotation deg, back side?)
# PLACEMENT: one line per part.
# The reference (R1, U2, ...) is the part's name on the board and in the parts list.
# Rotation is in degrees, anticlockwise.
PARTS = {
    "J1": (KLIB + "/Connector_Coaxial.pretty", "SMA_Amphenol_132289_EdgeMount", "SMA jack (probe)", 2.54, CY, 180, False),
    "U2": (LOCAL, "Atlas_pH_OEM", "Atlas pH OEM", 16.0, CY - 2.25, 0, False),   # pin 4 (PRB) in line with J1
    "U1": (LOCAL, "XIAO-ESP32-S3-SMD", "XIAO ESP32-S3", 96.6, CY - 8.89, -90, False),  # USB-C at the right edge
    "BT1": (KLIB + "/Battery.pretty", "BatteryHolder_Keystone_1042_1x18650", "18650 holder", 66.0, CY, 0, True),
    "Q1": (KLIB + "/Package_TO_SOT_SMD.pretty", "SOT-23", "AO3401A", 34.0, 16.0, 180, False),
    "R1": R0805 + ("4.7k", 28.5, 4.0, 90, False),     # SDA pull-up
    "R2": R0805 + ("4.7k", 31.0, 5.6, 90, False),     # SCL pull-up
    "R5": R0805 + ("100k", 23.0, 5.6, 90, False),     # PH_PWR pull-down: OEM stays off while GPIO5 floats in deep sleep
    "C1": C0805 + ("100n", 15.0, 5.64, 90, False),
    "C2": C0805 + ("1u", 19.0, 5.64, 90, False),
    "R3": R0805 + ("470k", 41.0, 12.55, 90, False),   # battery divider top
    "R4": R0805 + ("470k", 41.0, 16.4, 90, False),    # battery divider bottom
    "C3": C0805 + ("100n", 43.5, 16.44, 90, False),
    "H1": HOLE + ("M2.5", 3.2, 3.2, 0, False),
    "H2": HOLE + ("M2.5", 3.2, W - 3.2, 0, False),
    "H3": HOLE + ("M2.5", L - 3.2, 3.2, 0, False),
    "H4": HOLE + ("M2.5", L - 3.2, W - 3.2, 0, False),
}

# The schematic. net: [(ref, pad number), ...]
# XIAO pads used: 4=D3/GPIO4  5=D4/GPIO5  6=D5/GPIO6  9=D8/GPIO7  13,24=GND  23=VBAT (underside pad)
# OEM pads:       1=SDA 3=VCC 4=PRB 5=PRB GND 6=GND 8=SCL   (2,9,10=NC and 7=INT must float)
# THE CIRCUIT. Each line is one net: a name, then every (part, pad number) joined to it.
# This table is the schematic. To change the circuit, change it here, then fix route() until
# the design-rule check reports nothing unconnected.
NETS = {
    "GND": [("U1", "13"), ("U1", "24"), ("U2", "6"), ("BT1", "2"), ("Q1", "1"),
            ("R5", "1"), ("C1", "1"), ("C2", "1"), ("R4", "1"), ("C3", "1")],
    "BAT_RAW": [("BT1", "1"), ("Q1", "3")],                    # cell +, before the reverse-polarity FET
    "VBAT": [("Q1", "2"), ("U1", "23"), ("R3", "2")],
    "BAT_SENSE": [("R3", "1"), ("R4", "2"), ("C3", "2"), ("U1", "9")],   # VBAT/2 -> GPIO7 (ADC1)
    "PH_PWR": [("U1", "5"), ("U2", "3"), ("R1", "1"), ("R2", "2"), ("R5", "2"), ("C1", "2"), ("C2", "2")],  # GPIO5 powers OEM + pull-ups
    "SDA": [("U1", "4"), ("U2", "1"), ("R1", "2")],            # GPIO4
    "SCL": [("U1", "6"), ("U2", "8"), ("R2", "1")],            # GPIO6
    "PRB": [("U2", "4"), ("J1", "1")],
    "PRBG": [("U2", "5"), ("J1", "2")],                        # probe reference / analog ground: NEVER tie to GND
}


# Create an empty board, declare every net, load and place every footprint, then go through
# NETS and stamp each pad with the net it belongs to. Nothing is wired yet after this step.
def build():
    board = pcbnew.CreateEmptyBoard()
    nets = {}
    for name in NETS:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    fps = {}
    for ref, (lib, name, value, x, y, rot, back) in PARTS.items():
        fp = pcbnew.FootprintLoad(lib, name)
        assert fp is not None, (lib, name)
        fp.SetFPID(pcbnew.LIB_ID(os.path.basename(lib).replace(".pretty", ""), name))  # matches the schematic's Footprint field
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(P(x, y))
        board.Add(fp)
        if back:  # Flip() segfaults on a footprint that is not on a board yet
            fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        fp.SetOrientationDegrees(rot)
        fps[ref] = fp
    for name, pins in NETS.items():
        for ref, num in pins:
            hit = [p for p in fps[ref].Pads() if p.GetNumber() == num]
            assert hit, (ref, num)
            for p in hit:
                p.SetNet(nets[name])
    return board, nets, fps


# Print where every pad ended up (run the script with --pads). Rotating a footprint moves its
# pads, so this listing is how the coordinates used in route() were found.
def dump_pads(fps):
    for ref, fp in fps.items():
        bb = fp.GetBoundingBox(False)
        print("%s bbox x[%.2f,%.2f] y[%.2f,%.2f]" % (ref, pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetRight()) - OX,
                                                      pcbnew.ToMM(bb.GetTop()) - OY, pcbnew.ToMM(bb.GetBottom()) - OY))
        for p in fp.Pads():
            print("   %-3s (%7.2f,%6.2f) %s %s" % (p.GetNumber() or "-", pcbnew.ToMM(p.GetPosition().x) - OX,
                                                  pcbnew.ToMM(p.GetPosition().y) - OY, p.GetNetname() or ".",
                                                  "B" if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) else ""))


SIG, PWR, PROBE = 0.25, 0.5, 0.4   # track widths, mm (PRB 0.4 per OEM datasheet p34)


# Draw the copper. Three small helpers do the work (track, via, zone); the rest of the function
# is a list of calls to them, grouped by which part of the circuit they connect.
def route(board, nets):
    # track: draw a line of copper for `net` through a list of points, `w` millimetres wide.
    def track(net, pts, w=SIG, layer=pcbnew.F_Cu):
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(*a))
            t.SetEnd(P(*b))
            t.SetWidth(pcbnew.FromMM(w))
            t.SetLayer(layer)
            t.SetNet(nets[net])
            board.Add(t)

    # via: a plated hole joining the front and back copper at one point.
    def via(net, x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(P(x, y))
        v.SetDrill(pcbnew.FromMM(0.4))
        v.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(0.8))
        v.SetNet(nets[net])
        board.Add(v)

    # zone: a filled copper area with the given outline. Copper of other nets is kept clear of it
    # automatically; pads of the same net are connected to it.
    def zone(net, layer, pts, solid=False):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets[net])
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.25))
        if solid:
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        o = z.Outline()
        o.NewOutline()
        for x, y in pts:
            o.Append(P(x, y))
        board.Add(z)

    B = pcbnew.B_Cu
    # --- I2C + switched OEM power: three lanes along the top edge, XIAO -> OEM
    track("SCL", [(102.02, 7.95), (102.02, 5.6), (33.5, 5.6), (33.5, 6.6), (26.0, 6.6), (26.0, 13.75), (22.0, 13.75)])
    track("PH_PWR", [(104.56, 7.95), (104.56, 4.6), (13.0, 4.6)])
    via("PH_PWR", 13.0, 4.6)                       # hop under SDA on the back
    track("PH_PWR", [(13.0, 4.6), (7.7, 4.6)], layer=B)
    via("PH_PWR", 7.7, 4.6)
    track("PH_PWR", [(7.7, 4.6), (7.7, 13.75), (10.0, 13.75)])
    track("SDA", [(107.10, 7.95), (107.10, 3.4), (9.7, 3.4), (9.7, 9.25)])
    # --- decoupling / pull-down grounds
    track("GND", [(15.0, 6.68), (23.0, 6.68)], w=0.4)
    via("GND", 17.0, 6.68)
    track("GND", [(22.0, 18.25), (22.0, 21.2), (20.5, 21.2)], w=0.4)   # OEM pin 6
    via("GND", 20.5, 21.2)
    # --- probe: short, straight, wrapped in PRBG on both layers
    track("PRB", [(2.54, 16.0), (10.0, 16.0)], w=PROBE)
    via("PRBG", 6.0, 20.9)
    via("PRBG", 6.0, 11.1)
    # --- battery: holder(+) on the back -> via -> Q1 -> VBAT lane -> XIAO underside pad
    track("BAT_RAW", [(26.31, 16.0), (31.3, 16.0)], w=PWR, layer=B)
    via("BAT_RAW", 31.3, 16.0)
    track("BAT_RAW", [(31.3, 16.0), (33.06, 16.0)], w=PWR)
    track("GND", [(34.94, 16.95), (36.6, 16.95)], w=0.4)                # Q1 gate
    via("GND", 36.6, 16.95)
    track("VBAT", [(34.94, 15.05), (34.94, 11.55), (107.48, 11.55)], w=PWR)
    # --- battery sense divider
    track("BAT_SENSE", [(41.0, 13.55), (41.0, 15.4), (45.5, 15.4), (45.5, 26.6), (102.02, 26.6), (102.02, 24.11)])
    track("GND", [(41.0, 17.4), (43.5, 17.4)], w=0.4)
    via("GND", 42.25, 17.4)
    # --- XIAO grounds
    track("GND", [(112.18, 24.11), (112.18, 26.6)], w=0.4)
    via("GND", 112.18, 26.6)
    track("GND", [(109.39, 11.55), (111.3, 11.55)], w=0.4)
    via("GND", 111.3, 11.55)
    # --- stitch front and back ground pours together
    for x, y in [(60, 8.5), (85, 8.5), (60, 19), (85, 19), (60, 29.5), (90, 29.5), (60, 1.8), (90, 1.8), (16, 27)]:
        via("GND", x, y)

    analog_f = [(0.4, 10.4), (6.6, 10.4), (6.6, 14.9), (11.7, 14.9), (11.7, 21.6), (0.4, 21.6)]
    analog_b = [(0.4, 10.4), (11.7, 10.4), (11.7, 21.6), (0.4, 21.6)]
    digital = [(12.6, 0.4), (L - 0.4, 0.4), (L - 0.4, W - 0.4), (0.4, W - 0.4), (0.4, 22.5), (12.6, 22.5)]
    zone("PRBG", pcbnew.F_Cu, analog_f, solid=True)
    zone("PRBG", B, analog_b, solid=True)
    zone("GND", pcbnew.F_Cu, digital)
    zone("GND", B, digital)

    # The board outline: a rectangle on the Edge.Cuts layer tells the factory where to cut.
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_RECT)
    edge.SetStart(P(0, 0))
    edge.SetEnd(P(L, W))
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetWidth(pcbnew.FromMM(0.1))
    board.Add(edge)

    for txt, x, y, layer in [("pHloat sensor rev A", 66, 30.3, pcbnew.F_SilkS), ("PROBE", 5.5, 8.6, pcbnew.F_SilkS),
                             ("18650  + this end", 40, 29.6, pcbnew.B_SilkS)]:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1), pcbnew.FromMM(1)))
        t.SetTextThickness(pcbnew.FromMM(0.15))
        if layer == pcbnew.B_SilkS:
            t.SetMirrored(True)
        board.Add(t)

    # Work out the actual copper shape of each zone (flowing around the tracks and pads).
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


# Run when the script is started directly: build, optionally list the pads and stop, otherwise
# route and save.
if __name__ == "__main__":
    board, nets, fps = build()
    if "--pads" in sys.argv:
        dump_pads(fps)
        sys.exit(0)
    route(board, nets)
    pcbnew.SaveBoard(OUT, board)
    print("wrote", OUT)
