"""Check that the schematic and the board describe the same circuit.

The board is built from the NETS table in gen_pcb.py. The schematic is generated from the same
table, but could be edited by hand in KiCad afterwards. This script exports nothing itself;
it reads a netlist that KiCad exported from the schematic and compares it with NETS.
It stops with an error (listing the differences) if they disagree.

How to run:
  kicad-cli sch export netlist --format kicadsexpr -o sch.net phloat_sensor.kicad_sch
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" check_netlist.py sch.net [folder holding gen_pcb.py]

A "netlist" is simply a list of nets, each with the pins connected to it.
"""
import re
import sys

# By default the board description (gen_pcb.py) is the one in this folder. A second argument
# names a different folder, so the same check works for the controller board:
#   check_netlist.py sch.net ..\controller_pcb
if len(sys.argv) > 2:
    sys.path.insert(0, sys.argv[2])
from gen_pcb import NETS

# Read the netlist file KiCad wrote (its path is the first word after the script name).
t = open(sys.argv[1], encoding="utf-8").read()

# Pull each net out of the file: its name, and the set of (part, pin) pairs on it.
# The file is bracketed text; each net starts with "(net" on its own line.
got = {}
for chunk in re.split(r"\(net\s*\n", t[t.index("(nets"):])[1:]:
    name = re.search(r'\(name "([^"]*)"\)', chunk).group(1).lstrip("/")
    got[name] = set(re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', chunk))

# What the board expects, in the same shape.
want = {k: set(v) for k, v in NETS.items()}
# KiCad invents "unconnected-..." nets for pins deliberately left unused. Ignore those.
named = {k: v for k, v in got.items() if not k.startswith("unconnected-")}

# For every net that differs, list the pins that are in one but not the other
# (`^` on two sets means "in exactly one of them").
diff = {k: sorted(named.get(k, set()) ^ want.get(k, set())) for k in set(named) | set(want) if named.get(k) != want.get(k)}
assert not diff, diff
print("netlist OK: %d nets, %d pins match gen_pcb.NETS" % (len(want), sum(map(len, want.values()))))
