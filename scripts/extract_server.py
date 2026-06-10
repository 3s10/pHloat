import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
installer = root / "install-phloat-tiltpi.sh"
text = installer.read_text(encoding="utf-8")
match = re.search(
    r"cat > \"\$PHLOAT_DIR/phloat_server.py\" << 'EOFPYTHON'\n(.*?)\nEOFPYTHON",
    text,
    re.S,
)
if not match:
    raise SystemExit("Could not find phloat_server.py heredoc")

out_dir = root / "tiltpi"
out_dir.mkdir(exist_ok=True)
(out_dir / "phloat_server.py").write_text(match.group(1), encoding="utf-8")
print(f"Wrote {out_dir / 'phloat_server.py'} ({len(match.group(1))} bytes)")
