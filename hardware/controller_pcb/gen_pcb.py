"""Generate fermenter_controller.kicad_pcb. Run with KiCad's bundled Python:

  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen_pcb.py [--pads]

Source of truth for the board: netlist (NETS), placement (PARTS) and routing (route()).
NETS is the master copy of the circuit; gen_sch.py draws the schematic from it.
12 V pumps only: the AO3400A FETs are 30 V parts and the TVS is sized for a 12 V supply.
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
LOCAL = os.path.join(HERE, "..", "phloat_sensor_pcb", "phloat.pretty")   # Seeed XIAO footprint (CC-BY-SA-4.0)
OUT = os.path.join(HERE, "fermenter_controller.kicad_pcb")

OX, OY = 40.0, 40.0          # board origin on the KiCad sheet
L, W = 92.0, 62.0            # board size, mm


# Convert a position in millimetres on OUR board into the form KiCad wants: a point on its
# drawing sheet, in its internal units (nanometres). Every coordinate below goes through this.
def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))


R0805 = (KLIB + "/Resistor_SMD.pretty", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C0805 = (KLIB + "/Capacitor_SMD.pretty", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")
SOT23 = (KLIB + "/Package_TO_SOT_SMD.pretty", "SOT-23")
SMA = (KLIB + "/Diode_SMD.pretty", "D_SMA")
TB2 = (KLIB + "/TerminalBlock_Phoenix.pretty", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal")
TB3 = (KLIB + "/TerminalBlock_Phoenix.pretty", "TerminalBlock_Phoenix_PT-1,5-3-3.5-H_1x03_P3.50mm_Horizontal")
HOLE = (KLIB + "/MountingHole.pretty", "MountingHole_3.2mm_M3")

# ref: (library dir, footprint, value, x, y, rotation deg)
# PLACEMENT: one line per part.
# The reference (R1, U2, ...) is the part's name on the board and in the parts list.
# Rotation is in degrees, anticlockwise.
PARTS = {
    "U1": (LOCAL, "XIAO-ESP32-S3-SMD", "XIAO ESP32-S3", 70.6, 22.0, -90),           # USB-C at the right edge
    "U2": (KLIB + "/Converter_DCDC.pretty", "Converter_DCDC_TRACO_TSR-1_THT", "TSR 1-2450 (5 V, 1 A)", 30.0, 33.0, 0),
    "J1": TB2 + ("12V IN", 6.0, 30.0, 270),                                           # left edge
    "F1": (KLIB + "/Fuse.pretty", "Fuseholder_Clip-5x20mm_Littelfuse_111_Inline_P20.00x5.00mm_D1.05mm_Horizontal",
           "5x20 fuse", 14.0, 46.0, 0),
    "D4": (KLIB + "/Diode_SMD.pretty", "D_SMB", "SMBJ15A", 20.0, 28.0, 90),          # TVS; also blows F1 on a reversed supply
    "C1": (KLIB + "/Capacitor_THT.pretty", "CP_Radial_D8.0mm_P3.50mm", "220u 25V", 42.0, 44.0, 0),
    "C3": C0805 + ("22u 10V", 38.5, 37.0, 0),
    "D3": (KLIB + "/Diode_SMD.pretty", "D_SOD-123", "B5819W", 47.0, 34.0, 180),      # 5 V -> XIAO, stops USB back-feed
    "Q1": SOT23 + ("AO3400A", 56.0, 48.0, 0),                                         # cooling pump
    "Q2": SOT23 + ("AO3400A", 74.0, 48.0, 0),                                         # warming pump
    "R1": R0805 + ("100R", 52.0, 44.0, 0),
    "R2": R0805 + ("100R", 70.0, 44.0, 0),
    "R3": R0805 + ("10k", 52.0, 47.0, 0),                                             # gate pull-downs: pumps off while the ESP is dead
    "R4": R0805 + ("10k", 70.0, 47.0, 0),
    "D1": SMA + ("SS34", 61.0, 46.5, 270),                                            # flyback
    "D2": SMA + ("SS34", 79.0, 46.5, 270),
    "J2": TB2 + ("COOL PUMP", 56.0, 56.0, 0),                                         # bottom edge
    "J3": TB2 + ("WARM PUMP", 74.0, 56.0, 0),
    "R5": R0805 + ("4.7k", 56.0, 14.0, 0),                                            # 1-Wire pull-up
    "J4": TB3 + ("COOLANT", 11.0, 6.0, 180),                                          # top edge: 3V3, DQ, GND
    "J5": TB3 + ("WARM FLUID", 24.0, 6.0, 180),
    "J6": TB3 + ("AMBIENT", 37.0, 6.0, 180),
    "J7": TB3 + ("THERMOWELL", 50.0, 6.0, 180),
    "H1": HOLE + ("M3", 4.0, 58.0, 0),
    "H2": HOLE + ("M3", 88.0, 58.0, 0),
    "H3": HOLE + ("M3", 88.0, 4.0, 0),
    "H4": HOLE + ("M3", 4.0, 18.0, 0),
}

# The schematic. net: [(ref, pad number), ...]
# XIAO pads: 4=D3/GPIO4  5=D4/GPIO5  6=D5/GPIO6  12=3V3  13,24=GND  14=5V
# THE CIRCUIT. Each line is one net: a name, then every (part, pad number) joined to it.
# This table is the schematic. To change the circuit, change it here, then fix route() until
# the design-rule check reports nothing unconnected.
NETS = {
    "GND": [("U1", "13"), ("U1", "24"), ("U2", "2"), ("J1", "2"), ("D4", "2"), ("C1", "2"), ("C3", "1"),
            ("Q1", "2"), ("Q2", "2"), ("R3", "1"), ("R4", "1"), ("J4", "3"), ("J5", "3"), ("J6", "3"), ("J7", "3")],
    "VIN_RAW": [("J1", "1"), ("F1", "1")],                                 # supply +, before the fuse
    "VIN": [("F1", "2"), ("D4", "1"), ("C1", "1"), ("U2", "1"),
            ("J2", "1"), ("J3", "1"), ("D1", "1"), ("D2", "1")],          # fused supply: pumps + and regulator in
    "5V": [("U2", "3"), ("C3", "2"), ("D3", "2")],
    "5V_XIAO": [("D3", "1"), ("U1", "14")],
    "3V3": [("U1", "12"), ("R5", "1"), ("J4", "1"), ("J5", "1"), ("J6", "1"), ("J7", "1")],
    "DQ": [("U1", "4"), ("R5", "2"), ("J4", "2"), ("J5", "2"), ("J6", "2"), ("J7", "2")],   # GPIO4, 1-Wire
    "COOL_PWM": [("U1", "5"), ("R1", "1")],                                # GPIO5
    "COOL_GATE": [("R1", "2"), ("R3", "2"), ("Q1", "1")],
    "COOL_SW": [("Q1", "3"), ("D1", "2"), ("J2", "2")],                    # pump -, switched to GND
    "WARM_PWM": [("U1", "6"), ("R2", "1")],                                # GPIO6
    "WARM_GATE": [("R2", "2"), ("R4", "2"), ("Q2", "1")],
    "WARM_SW": [("Q2", "3"), ("D2", "2"), ("J3", "2")],
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
    for ref, (lib, name, value, x, y, rot) in PARTS.items():
        fp = pcbnew.FootprintLoad(lib, name)
        assert fp is not None, (lib, name)
        fp.SetFPID(pcbnew.LIB_ID(os.path.basename(lib).replace(".pretty", ""), name))
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(P(x, y))
        board.Add(fp)
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
            print("   %-3s (%7.2f,%6.2f) %s" % (p.GetNumber() or "-", pcbnew.ToMM(p.GetPosition().x) - OX,
                                               pcbnew.ToMM(p.GetPosition().y) - OY, p.GetNetname() or "."))


SIG, PWR5, VINW, SWW = 0.25, 0.5, 2.0, 1.5   # track widths, mm


# Draw the copper. Three small helpers do the work (track, via, zone); the rest of the function
# is a list of calls to them, grouped by which part of the circuit they connect.
def route(board, nets):
    F, B = pcbnew.F_Cu, pcbnew.B_Cu

    # track: draw a line of copper for `net` through a list of points, `w` millimetres wide.
    def track(net, pts, w=SIG, layer=F):
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(*a))
            t.SetEnd(P(*b))
            t.SetWidth(pcbnew.FromMM(w))
            t.SetLayer(layer)
            t.SetNet(nets[net])
            board.Add(t)

    # via: a plated hole joining the front and back copper at one point.
    def via(net, x, y, big=False):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(P(x, y))
        v.SetDrill(pcbnew.FromMM(0.8 if big else 0.4))
        v.SetWidth(F, pcbnew.FromMM(1.6 if big else 0.8))
        v.SetNet(nets[net])
        board.Add(v)

    # zone: a filled copper area with the given outline. Copper of other nets is kept clear of it
    # automatically; pads of the same net are connected to it.
    def zone(net, layer, pts):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets[net])
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.25))
        o = z.Outline()
        o.NewOutline()
        for x, y in pts:
            o.Append(P(x, y))
        board.Add(z)

    # --- supply in: J1 -> fuse (back, wide)
    track("VIN_RAW", [(6, 30), (9, 30), (14, 35), (14, 46), (19, 46)], w=VINW, layer=B)
    # --- fused supply bus on the back: fuse -> bulk cap, regulator, both pump terminals, both flyback diodes
    track("VIN", [(29, 46), (34, 46), (34, 59.5), (83.5, 59.5), (83.5, 44.5)], w=VINW, layer=B)
    track("VIN", [(34, 46), (42, 46), (42, 44)], w=VINW, layer=B)
    track("VIN", [(56, 59.5), (56, 56)], w=VINW, layer=B)
    track("VIN", [(74, 59.5), (74, 56)], w=VINW, layer=B)
    track("VIN", [(65.5, 59.5), (65.5, 44.5)], w=SWW, layer=B)
    track("VIN", [(29, 46), (29, 36.5), (30, 35.5), (30, 33)], w=1.0, layer=B)        # regulator in
    track("VIN", [(30, 33), (22, 33), (20, 31), (20, 30.15)], w=1.0)                  # TVS
    via("VIN", 65.5, 44.5, big=True)
    track("VIN", [(65.5, 44.5), (61, 44.5)], w=SWW)                                   # D1 cathode
    via("VIN", 83.5, 44.5, big=True)
    track("VIN", [(83.5, 44.5), (79, 44.5)], w=SWW)                                   # D2 cathode
    # --- pump low side: FET drain -> flyback anode -> terminal pin 2
    for dx, net in ((0, "COOL"), (18, "WARM")):
        track(net + "_SW", [(56.94 + dx, 48), (57.44 + dx, 48.5), (61.08 + dx, 48.5), (61.08 + dx, 56)], w=SWW)
        track(net + "_GATE", [(53 + dx, 44), (53 + dx, 47.05), (55.06 + dx, 47.05)])
        track("GND", [(55.06 + dx, 48.95), (54.5 + dx, 49.1), (51 + dx, 49.1), (51 + dx, 47)], w=0.8)   # source + pull-down
        via("GND", 52.9 + dx, 49.1, big=True)
        via("GND", 51 + dx, 49.1, big=True)
    # --- PWM: XIAO -> via -> back -> via -> gate resistor
    track("COOL_PWM", [(78.56, 22.84), (78.56, 19.5)])
    via("COOL_PWM", 78.56, 19.5)
    track("COOL_PWM", [(78.56, 19.5), (62, 19.5), (49.3, 32.2), (49.3, 44)], layer=B)
    via("COOL_PWM", 49.3, 44)
    track("COOL_PWM", [(49.3, 44), (51, 44)])
    track("WARM_PWM", [(76.02, 22.84), (76.02, 20.6)])
    via("WARM_PWM", 76.02, 20.6)
    track("WARM_PWM", [(76.02, 20.6), (72, 20.6), (67.3, 25.3), (67.3, 44)], layer=B)
    via("WARM_PWM", 67.3, 44)
    track("WARM_PWM", [(67.3, 44), (69, 44)])
    # --- 5 V: regulator -> C3 -> D3 -> XIAO 5V pin
    track("5V", [(35.08, 33), (38.5, 33), (39.5, 34), (45.35, 34)], w=PWR5)
    track("5V", [(39.54, 34), (39.54, 37)], w=PWR5)
    track("5V_XIAO", [(48.65, 34), (48.65, 42.4), (88.72, 42.4), (88.72, 39)], w=PWR5)
    # --- 1-Wire: XIAO GPIO4 -> pull-up -> back bus under the probe terminals
    track("DQ", [(81.10, 22.84), (81.10, 17), (58.5, 17)])
    track("DQ", [(57, 14), (58.5, 15.5), (58.5, 17)])
    via("DQ", 58.5, 17)
    track("DQ", [(58.5, 17), (58.5, 11), (7.5, 11)], layer=B)
    for x in (7.5, 20.5, 33.5, 46.5):
        track("DQ", [(x, 11), (x, 6)], layer=B)
    # --- 3V3: XIAO -> back (under the module) -> front bus to the probe terminals
    track("3V3", [(83.64, 39), (83.64, 41.15)], w=0.4)
    via("3V3", 83.64, 41.15)
    track("3V3", [(83.64, 41.15), (83.64, 14.5), (60.5, 14.5)], w=0.4, layer=B)
    via("3V3", 60.5, 14.5)
    track("3V3", [(60.5, 14.5), (60.5, 12), (11, 12)], w=0.4)
    track("3V3", [(55, 14), (55, 12)], w=0.4)
    for x in (11, 24, 37, 50):
        track("3V3", [(x, 12), (x, 6)], w=0.4)
    # --- grounds for SMD pads: tie each to the back pour
    track("GND", [(86.18, 39), (86.18, 41.15)], w=0.4)
    via("GND", 86.18, 41.15)
    track("GND", [(83.39, 26.44), (85.3, 26.44)], w=0.4)
    via("GND", 85.3, 26.44)                          # under the XIAO: order tented vias
    track("GND", [(20, 25.85), (20, 23.8)], w=0.8)
    via("GND", 20, 23.8, big=True)
    track("GND", [(37.46, 37), (37.46, 38.7)], w=0.4)
    via("GND", 37.46, 38.7)
    for x, y in [(12, 20), (30, 20), (45, 24), (62, 30), (25, 54), (45, 54), (60, 6), (75, 10)]:
        via("GND", x, y)                             # stitch the two pours

    outline = [(0.4, 0.4), (L - 0.4, 0.4), (L - 0.4, W - 0.4), (0.4, W - 0.4)]
    zone("GND", F, outline)
    zone("GND", B, outline)

    # The board outline: a rectangle on the Edge.Cuts layer tells the factory where to cut.
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_RECT)
    edge.SetStart(P(0, 0))
    edge.SetEnd(P(L, W))
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetWidth(pcbnew.FromMM(0.1))
    board.Add(edge)

    labels = [("Fermenter controller rev A", 30, 24.5), ("12V", 13.5, 27.5), ("+", 12.5, 30), ("-", 12.5, 35),
              ("COOL + -", 58.5, 41.2), ("WARM + -", 76.5, 41.2),
              ("GND DQ 3V3", 12.5, 14.2), ("COOLANT", 12.5, 16), ("WARM", 24, 14.2), ("AMBIENT", 37, 14.2), ("WELL", 50, 14.2),
              ("FUSE", 24, 51)]
    for txt, x, y in labels:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(P(x, y))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1), pcbnew.FromMM(1)))
        t.SetTextThickness(pcbnew.FromMM(0.15))
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
