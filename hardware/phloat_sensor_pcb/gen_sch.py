"""Generate phloat_sensor.kicad_sch (+ project files) from the NETS/PARTS tables in gen_pcb.py.

  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen_sch.py

Every pin gets a global label instead of a drawn wire: the netlist is what matters and
it stays identical to the board by construction.
ponytail: labels, not wires. Redraw with wires in eeschema if the drawing needs to look pretty.
"""
# WHAT THIS SCRIPT DOES
#   It draws the schematic (the circuit diagram) for the sensor board from the same NETS table
#   the board itself is built from, so the diagram and the board can never disagree.
#
#   A KiCad schematic is a text file made of nested brackets, e.g. (symbol (at 10 20) ...).
#   This script writes that text directly.
#
#   Shortcut taken: connections are not drawn as wires. Every pin gets a small name tag
#   (a "global label") carrying its net name; KiCad treats all pins with the same label as
#   connected. Electrically identical to drawn wires, just less pretty.
#
# WORDS
#   symbol   the drawing of a part on a schematic (a box with pins), as opposed to its footprint.
#   pin      a connection point on a symbol; its number matches the footprint's pad number.
#   UUID     a long unique ID that KiCad requires on every item in the file.
import json
import os
import re
import uuid

from gen_pcb import NETS, PARTS, HERE

# Settings: KiCad's symbol library folder, the project name, the drawing grid (1.27 mm), and a
# fixed starting value for generating IDs.
KSYM = os.environ.get("KICAD10_SYMBOL_DIR", r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
PROJECT = "phloat_sensor"
# The next three are plain variables (not written into main() below) so that another board can
# reuse this file: hardware/controller_pcb/gen_sch.py loads it, changes them, and calls main().
TITLE = "pHloat sensor"                                  # printed in the drawing's title block
SEEED_SYM = os.path.join(HERE, "seeed_xiao.kicad_sym")   # Seeed's symbol library, the source of the XIAO symbol
FOOTPRINT_LIB_URI = "${KIPRJMOD}/phloat.pretty"          # where the project's own footprints are, relative to the project
G = 1.27
NS = uuid.UUID("7d0c2f0e-5b1a-4c57-9d2e-70686c6f6174")
ROOT = str(uuid.uuid5(NS, "root"))


# Make an ID from a description of the item (for example "R1", "pin", "2"). The same description
# always gives the same ID, so regenerating the schematic doesn't change every ID in the file.
def uid(*key):
    return str(uuid.uuid5(NS, "/".join(map(str, key))))


# Helper for reading KiCad's bracketed text: given the position of an opening bracket, return
# everything up to its matching closing bracket. It counts brackets, ignoring any inside quotes.
def block(text, start):
    """Return the balanced s-expression starting at text[start] == '('."""
    depth, i, in_str = 0, start, False
    while True:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1


# Copy one symbol's definition out of a KiCad symbol library file. A schematic file must contain
# its own copy of every symbol it uses.
def lib_symbol(path, name):
    text = open(path, encoding="utf-8").read()
    i = text.index('(symbol "%s"' % name)
    b = block(text, i)
    m = re.search(r'\(extends "([^"]+)"\)', b)
    if m:  # schematic files embed flattened symbols: take the parent's graphics under the child's name
        parent = m.group(1)
        b = block(text, text.index('(symbol "%s"' % parent)).replace(parent, name)
    return b


# The pH module has no symbol in KiCad's libraries, so it is defined here by hand: a rectangle
# with ten numbered pins. Pin numbers match the module's datasheet.
OEM_SYMBOL = '''(symbol "Atlas_pH_OEM"
		(exclude_from_sim no) (in_bom yes) (on_board yes)
		(property "Reference" "U" (at -10.16 13.97 0) (effects (font (size 1.27 1.27)) (justify left)))
		(property "Value" "Atlas_pH_OEM" (at -10.16 -13.97 0) (effects (font (size 1.27 1.27)) (justify left)))
		(property "Footprint" "phloat:Atlas_pH_OEM" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Datasheet" "https://files.atlas-scientific.com/oem_pH_datasheet.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Description" "Atlas Scientific pH OEM embedded circuit, I2C 0x65" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(symbol "Atlas_pH_OEM_0_1"
			(rectangle (start -10.16 12.7) (end 10.16 -12.7) (stroke (width 0.254) (type default)) (fill (type background)))
		)
		(symbol "Atlas_pH_OEM_1_1"
			(pin passive line (at -12.7 10.16 0) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
			(pin bidirectional line (at -12.7 5.08 0) (length 2.54) (name "SDA" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
			(pin input line (at -12.7 2.54 0) (length 2.54) (name "SCL" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
			(pin output line (at -12.7 -2.54 0) (length 2.54) (name "INT" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
			(pin passive line (at -12.7 -10.16 0) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 12.7 5.08 180) (length 2.54) (name "PRB" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
			(pin passive line (at 12.7 2.54 180) (length 2.54) (name "PRB_GND" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
			(pin no_connect line (at 12.7 -5.08 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
			(pin no_connect line (at 12.7 -7.62 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "9" (effects (font (size 1.27 1.27)))))
			(pin no_connect line (at 12.7 -10.16 180) (length 2.54) (name "NC" (effects (font (size 1.27 1.27)))) (number "10" (effects (font (size 1.27 1.27)))))
		)
	)'''

XIAO_SRC = os.path.join(HERE, "phloat.kicad_sym")   # written below from Seeed's library symbol + ours

# ref prefix -> (symbol library file, symbol name, lib nickname)
# Which symbol to draw for each part. Looked up by the full reference first (U1, U2), then by
# its letter prefix (R for any resistor, C for any capacitor, ...).
SYMBOLS = {
    "R": (KSYM + "/Device.kicad_sym", "R", "Device"),
    "C": (KSYM + "/Device.kicad_sym", "C", "Device"),
    "BT": (KSYM + "/Device.kicad_sym", "Battery_Cell", "Device"),
    "J": (KSYM + "/Connector.kicad_sym", "Conn_Coaxial", "Connector"),
    "Q": (KSYM + "/Transistor_FET.kicad_sym", "AO3401A", "Transistor_FET"),
    "H": (KSYM + "/Mechanical.kicad_sym", "MountingHole", "Mechanical"),
    "U1": (XIAO_SRC, "XIAO-ESP32-S3-SMD", "phloat"),
    "U2": (XIAO_SRC, "Atlas_pH_OEM", "phloat"),
}

# ref -> sheet position in grid units (1.27 mm)
# Where each part sits on the drawing sheet.
PLACE = {
    "J1": (40, 66), "U2": (80, 70), "U1": (160, 70),
    "R1": (72, 34), "R2": (84, 34), "R5": (96, 34), "C1": (108, 34), "C2": (120, 34),
    "BT1": (40, 112), "Q1": (72, 108), "R3": (100, 104), "R4": (100, 120), "C3": (112, 120),
    "H1": (150, 124), "H2": (160, 124), "H3": (170, 124), "H4": (180, 124),
}

# Design notes printed on the schematic itself, so the rules travel with the drawing.
NOTES = """pHloat sensor rev A  -  netlist generated from gen_pcb.py (gen_sch.py)

1. PRBG is the probe reference (OEM pin 5 + SMA shell). It is NOT ground. Never tie PRBG to GND.
2. PH_PWR (GPIO5) powers the OEM and both I2C pull-ups. Drive HIGH to measure, release for deep sleep. R5 keeps it low.
3. OEM pins 2, 9, 10 (NC) and 7 (INT) must float. No vias under U2. Remove all flux after soldering U2.
4. Q1 blocks a reversed 18650. No under-voltage cut-off in hardware: firmware stops below about 3.2 V.
5. BAT_SENSE = VBAT / 2 on GPIO7. I2C: SDA GPIO4, SCL GPIO6, OEM address 0x65.
6. Beer temperature comes from the Tilt over BLE; there is no temperature sensor on this board."""


# "R12" -> "R": find which SYMBOLS entry applies to a reference.
def sym_key(ref):
    return ref if ref in SYMBOLS else re.match(r"[A-Z]+", ref).group(0)


# List a symbol's pins: (number, electrical type, x, y, direction). Found by searching the
# symbol's text for "(pin ..." entries.
def pins_of(sym_text):
    out = []
    for m in re.finditer(r"\(pin\s+(\w+)\s+\w+", sym_text):
        b = block(sym_text, m.start())
        at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", b)
        num = re.search(r'\(number\s+"([^"]*)"', b).group(1)
        out.append((num, m.group(1), float(at.group(1)), float(at.group(2)), int(float(at.group(3) or 0))))
    return out


# Write the symbol library, then the schematic, then the small project files KiCad expects.
def main():
    # project symbol library: Seeed's XIAO symbol + our OEM symbol
    xiao = lib_symbol(SEEED_SYM, "XIAO-ESP32-S3-SMD")
    assert "(extends" not in xiao
    with open(XIAO_SRC, "w", encoding="utf-8", newline="\n") as f:
        f.write('(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "phloat_gen")\n\t(generator_version "9.0")\n\t%s\n\t%s\n)\n'
                % (xiao, OEM_SYMBOL))

    # Turn NETS inside out: from "net -> its pins" to "pin -> its net", for quick lookup below.
    pin_net = {(ref, num): net for net, pins in NETS.items() for ref, num in pins}
    lib_syms, body = {}, []
    # For every part: place its symbol, then tag each of its pins.
    for ref, part in PARTS.items():
        path, name, nick = SYMBOLS[sym_key(ref)]
        lib_id = "%s:%s" % (nick, name)
        if lib_id not in lib_syms:
            lib_syms[lib_id] = lib_symbol(path, name)
        sym = lib_syms[lib_id]
        fp_nick = os.path.basename(part[0]).replace(".pretty", "")
        footprint = "%s:%s" % (fp_nick, part[1])
        x, y = PLACE[ref][0] * G, PLACE[ref][1] * G
        pins = pins_of(sym)
        top = max(p[3] for p in pins) if pins else 2.54
        small = len(pins) <= 3
        rx, ry = (x + 3.81, y - 1.27) if small else (x - 10.16, y - top - 5.08)
        vx, vy = (x + 3.81, y + 1.27) if small else (x - 10.16, y - top - 2.54)
        pin_lines = "".join('\n\t\t(pin "%s" (uuid "%s"))' % (p[0], uid(ref, "pin", p[0], i)) for i, p in enumerate(pins))
        body.append('''	(symbol (lib_id "%s") (at %.2f %.2f 0) (unit 1)
		(exclude_from_sim no) (in_bom %s) (on_board yes) (dnp no)
		(uuid "%s")
		(property "Reference" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left)))
		(property "Value" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (justify left)))
		(property "Footprint" "%s" (at %.2f %.2f 0) (effects (font (size 1.27 1.27)) (hide yes)))%s
		(instances (project "%s" (path "/%s" (reference "%s") (unit 1))))
	)''' % (lib_id, x, y, "no" if ref[0] == "H" else "yes", uid(ref), ref, rx, ry, part[2], vx, vy,
            footprint, x, y, pin_lines, PROJECT, ROOT, ref))
        seen = set()
        # A pin that is in NETS gets a label with its net name. A pin that is not, and is not
        # already marked "no connect" in the symbol, gets an X so KiCad knows it is unused on purpose.
        for num, etype, px, py, ang in pins:
            ex, ey = round(x + px, 2), round(y - py, 2)
            if (ex, ey) in seen:      # stacked pins (e.g. several GND numbers on one point)
                continue
            seen.add((ex, ey))
            net = pin_net.get((ref, num))
            if net:
                la = (ang + 180) % 360
                just = "right" if la in (180, 270) else "left"
                body.append('''	(global_label "%s" (shape passive) (at %.2f %.2f %d)
		(effects (font (size 1.27 1.27)) (justify %s))
		(uuid "%s")
		(property "Intersheetrefs" "${INTERSHEET_REFS}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
	)''' % (net, ex, ey, la, just, uid(ref, "lbl", num)))
            elif etype != "no_connect":
                body.append('\t(no_connect (at %.2f %.2f) (uuid "%s"))' % (ex, ey, uid(ref, "nc", num)))

    libs = "\n".join("\t\t" + s.replace('(symbol "%s"' % k.split(":")[1], '(symbol "%s"' % k, 1) for k, s in lib_syms.items())
    notes = '\t(text "%s" (exclude_from_sim no) (at %.2f %.2f 0) (effects (font (size 1.5 1.5)) (justify left top)) (uuid "%s"))' % (
        NOTES.replace("\n", "\\n"), 30 * G, 136 * G, uid("notes"))
    sch = '''(kicad_sch
	(version 20250114)
	(generator "phloat_gen")
	(generator_version "9.0")
	(uuid "%s")
	(paper "A4")
	(title_block (title "%s") (date "2026-11-15") (rev "A") (comment 1 "Generated by gen_sch.py - edit gen_pcb.py, not this file"))
	(lib_symbols
%s
	)
%s
%s
	(sheet_instances (path "/" (page "1")))
	(embedded_fonts no)
)
''' % (ROOT, TITLE, libs, notes, "\n".join(body))
    with open(os.path.join(HERE, PROJECT + ".kicad_sch"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sch)

    # Two small files that tell KiCad where this project's own symbols and footprints live.
    with open(os.path.join(HERE, "sym-lib-table"), "w", newline="\n") as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "phloat")(type "KiCad")(uri "${KIPRJMOD}/phloat.kicad_sym")(options "")(descr "pHloat project symbols"))\n)\n')
    with open(os.path.join(HERE, "fp-lib-table"), "w", newline="\n") as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "phloat")(type "KiCad")(uri "%s")(options "")(descr "pHloat project footprints"))\n)\n' % FOOTPRINT_LIB_URI)
    pro = os.path.join(HERE, PROJECT + ".kicad_pro")
    if not os.path.exists(pro):   # KiCad fills in every other setting on first open; never overwrite a project the user has opened
        with open(pro, "w", newline="\n") as f:
            json.dump({"meta": {"filename": PROJECT + ".kicad_pro", "version": 3}}, f, indent=2)
    print("wrote", PROJECT + ".kicad_sch")


if __name__ == "__main__":
    main()
