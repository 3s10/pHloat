from pathlib import Path

root = Path(__file__).resolve().parents[1]
installer = root / "install-phloat-tiltpi.sh"
text = installer.read_text(encoding="utf-8")
start = text.index('cat > "$PHLOAT_DIR/phloat_server.py" << \'EOFPYTHON\'')
end = text.index("EOFPYTHON\n\nchmod +x", start)
replacement = '''SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/tiltpi/phloat_server.py" "$PHLOAT_DIR/phloat_server.py"
cp "$SCRIPT_DIR/tiltpi/phloat_helpers.py" "$PHLOAT_DIR/phloat_helpers.py"
'''
installer.write_text(text[:start] + replacement + text[end + len("EOFPYTHON\n\n"):], encoding="utf-8")
print("Updated installer to copy tiltpi/*.py")
