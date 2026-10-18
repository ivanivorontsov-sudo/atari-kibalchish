H=28
def spr(rows, top=6):
    lines=[0]*H
    for r,v in enumerate(rows):
        for k in range(2):
            t=top+2*r+k
            lines[t]=v
    return list(reversed(lines))
def raw(top_to_bottom):
    assert len(top_to_bottom)==H
    return list(reversed(top_to_bottom))
tabs={}
tabs['GBlank']=[0]*H
tabs['GStar']=spr([0x10,0x38,0x38,0xFE,0x7F,0x38,0x6C,0xC6])
tabs['GJar']=spr([0x7E,0x7E,0x3C,0x7E,0xFF,0xBD,0xFF,0x7E])
tabs['GDol1']=spr([0x10,0x7E,0xD0,0x7C,0x16,0xFC,0x10,0x44])
tabs['GDol2']=spr([0x10,0x7E,0xD0,0x7C,0x16,0xFC,0x10,0x28])
tabs['GBoom']=spr([0x92,0x54,0x38,0xFE,0x38,0x54,0x92,0x00])
house=[0]*3+[0x60]*3+[0xF0]*3+[0xF0]*3+[0xD0]*4+[0xF0]*4+[0xB0]*6+[0]*2
tabs['GHouse']=raw(house)
mis=[0]*H
mis[14]=2; mis[15]=2
tabs['GMis']=raw(mis)
for t in tabs.values(): assert t[0]==0
out=[]
for n,v in tabs.items():
    out.append(n)
    for i in range(0,H,14):
        out.append("\t.byte "+",".join("$%02X"%b for b in v[i:i+14]))
font=["111101101101111","010110010010111","111001111100111","111001111001111","101101111001001",
      "111100111001111","111100111101111","111001001001001","111101111101111","111101111001111"]
hi=[];lo=[]
for f in font:
    for r in range(5):
        bits=int(f[r*3:r*3+3]+"0",2)
        hi.append(bits<<4); lo.append(bits)
def emit(name,arr):
    out.append(name)
    for i in range(0,len(arr),10):
        out.append("\t.byte "+",".join("$%02X"%b for b in arr[i:i+10]))
emit("DigHi",hi); emit("DigLo",lo)
L="100100100100111"
emit("LGlyph",[int(L[r*3:r*3+3]+"0",2)<<4 for r in range(5)])
open("gfx.inc.txt","w").write("\n".join(out)+"\n")
