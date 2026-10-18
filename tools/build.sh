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
mkdir -p build
for v in NTSC:0 PAL:1 PAL60:2 SECAM:3; do
  name=${v%%:*}; tv=${v##*:}
  for np in 0 1; do
    suf=""; [ $np = 1 ] && suf="_nopause"
    out=build/kibalchish_${name}${suf}
    dasm kibalchish.asm -f3 -DTV=$tv -DNOPAUSE=$np -o$out.bin -l$out.lst -s$out.sym > $out.log
    cp $out.bin $out.a26
    sz=$(stat -c %s $out.bin)
    [ "$sz" = 4096 ] || { echo "BAD SIZE $out $sz"; exit 1; }
    echo "$out.bin $sz $(grep -h 'RAM used\|ROM free' $out.log | tr -s ' ' | tr '\n' ' ')"
  done
done
