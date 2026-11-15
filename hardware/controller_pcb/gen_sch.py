"""Generate the schematic (circuit diagram) for the fermenter controller board.

  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen_sch.py

WHAT THIS DOES
  The controller's circuit is defined once, in the NETS table of gen_pcb.py in this folder.
  This script draws a KiCad schematic from that table, so the drawing and the board can never
  disagree. It writes:
      fermenter_controller.kicad_sch   the schematic
      fermenter_controller.kicad_pro   the project file (open this in KiCad)
      phloat.kicad_sym                 the symbols for the XIAO and the pH module
      sym-lib-table, fp-lib-table      tell KiCad where the project's own libraries are

HOW
  All the drawing logic already exists for the sensor board, in
  ../phloat_sensor_pcb/gen_sch.py. Rather than copy it, this script loads that file, swaps in
  this board's details (which symbol to draw for each part, where to put it, the notes), and
  runs it. How the drawing itself is made is explained in that file.

  As there, every pin carries a name tag (a "global label") instead of a drawn wire. Pins with
  the same tag are connected. Electrically correct, just not pretty.

CHECK IT
  kicad-cli sch erc --severity-all fermenter_controller.kicad_sch
  kicad-cli sch export netlist --format kicadsexpr -o sch.net fermenter_controller.kicad_sch
  python ..\\phloat_sensor_pcb\\check_netlist.py sch.net .        (must print "netlist OK")
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SENSOR = os.path.join(HERE, "..", "phloat_sensor_pcb")

# ---------------------------------------------------------------------------------------------
# Load the sensor board's generator as a library.
#
# That file starts with "from gen_pcb import NETS, PARTS, HERE". Python looks for gen_pcb in the
# folders listed in sys.path, in order. Putting THIS folder first means it finds this board's
# gen_pcb.py, so the generator works on the controller's circuit without being changed.
# ---------------------------------------------------------------------------------------------
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("sensor_gen_sch", os.path.join(SENSOR, "gen_sch.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

KSYM = gen.KSYM          # KiCad's standard symbol library folder
PROJECT_SYMS = gen.XIAO_SRC   # this folder's phloat.kicad_sym, which the generator writes

# ---------------------------------------------------------------------------------------------
# This board's details.
# ---------------------------------------------------------------------------------------------
gen.PROJECT = "fermenter_controller"
gen.TITLE = "Fermenter controller"
gen.SEEED_SYM = os.path.join(SENSOR, "seeed_xiao.kicad_sym")             # the XIAO symbol's source
gen.FOOTPRINT_LIB_URI = "${KIPRJMOD}/../phloat_sensor_pcb/phloat.pretty"   # the XIAO footprint lives with the sensor board

# Which symbol to draw for each part: (library file, symbol name, library nickname).
# Looked up by the full reference first (C1, D4, J1...), then by its letter prefix (any R, any C).
# The pin numbers of each symbol must match the pad numbers of its footprint; the netlist
# check proves that they do.
TERMINAL_2 = (KSYM + "/Connector.kicad_sym", "Screw_Terminal_01x02", "Connector")
TERMINAL_3 = (KSYM + "/Connector.kicad_sym", "Screw_Terminal_01x03", "Connector")
gen.SYMBOLS = {
    "R": (KSYM + "/Device.kicad_sym", "R", "Device"),
    "C": (KSYM + "/Device.kicad_sym", "C", "Device"),
    "C1": (KSYM + "/Device.kicad_sym", "C_Polarized", "Device"),         # the electrolytic: pin 1 is +
    "D": (KSYM + "/Device.kicad_sym", "D_Schottky", "Device"),           # pin 1 = cathode (the striped end)
    "D4": (KSYM + "/Device.kicad_sym", "D_Zener", "Device"),             # the TVS, drawn as a zener: pin 1 = cathode
    "Q": (KSYM + "/Transistor_FET.kicad_sym", "AO3400A", "Transistor_FET"),
    "F": (KSYM + "/Device.kicad_sym", "Fuse", "Device"),
    "H": (KSYM + "/Mechanical.kicad_sym", "MountingHole", "Mechanical"),
    "U1": (PROJECT_SYMS, "XIAO-ESP32-S3-SMD", "phloat"),
    "U2": (KSYM + "/Converter_DCDC.kicad_sym", "TSR_1-2450", "Converter_DCDC"),
    "J1": TERMINAL_2, "J2": TERMINAL_2, "J3": TERMINAL_2,
    "J4": TERMINAL_3, "J5": TERMINAL_3, "J6": TERMINAL_3, "J7": TERMINAL_3,
}

# Where each part sits on the sheet, in grid squares of 1.27 mm (x to the right, y downward).
# Rows: power across the top, the two pump drivers in the middle, probes and holes below,
# the microcontroller on the right.
gen.PLACE = {
    "J1": (20, 40), "F1": (40, 36), "D4": (56, 44), "C1": (68, 44), "U2": (90, 40), "C3": (112, 44), "D3": (124, 36),
    "U1": (180, 60),
    "R1": (56, 80), "R3": (68, 90), "Q1": (82, 84), "D1": (98, 74), "J2": (116, 78),
    "R2": (56, 112), "R4": (68, 122), "Q2": (82, 116), "D2": (98, 106), "J3": (116, 110),
    "R5": (146, 112), "J4": (160, 108), "J5": (178, 108), "J6": (196, 108), "J7": (214, 108),
    "H1": (150, 136), "H2": (160, 136), "H3": (170, 136), "H4": (180, 136),
}

# Design notes printed on the drawing, so the rules travel with it.
gen.NOTES = """Fermenter controller rev A  -  netlist generated from gen_pcb.py (gen_sch.py)

1. 12 V supply and 12 V pumps ONLY. Q1/Q2 are 30 V parts and D4 is sized for 12 V. About 2 A per pump.
2. R3 and R4 hold the pump gates low: both pumps are OFF whenever the XIAO is booting, reset, dead or missing.
3. D1 and D2 are flyback diodes, cathode to +12 V. Fitted backwards they short the supply.
4. D4 clamps spikes; on a reversed supply it conducts and blows F1. D3 stops USB back-feeding the 5 V rail.
5. J4-J7 are four identical DS18B20 terminals on one 1-Wire bus (GPIO4), pulled up by R5. Pin order GND, DQ, 3V3.
6. COOL_PWM is GPIO5, WARM_PWM is GPIO6. The firmware's safety guard is the only code that drives them."""

if __name__ == "__main__":
    gen.main()
