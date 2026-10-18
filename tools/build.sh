#!/bin/sh
set -e
cd "$(dirname "$0")/.."
python3 tools/gfx.py
python3 - <<'P'
t=open("tools/template.asm").read()
g=open("gfx.inc.txt").read().rstrip("\n")
open("kibalchish.asm","w").write(t.replace("@@GFX@@",g))
P
rm -f gfx.inc.txt
dasm kibalchish.asm -f3 -okibalchish.bin -lkibalchish.lst -skibalchish.sym
ls -l kibalchish.bin
