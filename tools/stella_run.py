import subprocess, os, glob, shutil, time, sys, re
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
VAR=os.environ.get('VAR','NTSC')
BINN=f'kibalchish_{VAR}.bin'
sym={}
for l in open(os.path.join(ROOT,'build',f'kibalchish_{VAR}.sym')):
    p=l.split()
    if len(p)>=2:
        try: sym[p[0]]=int(p[1],16)
        except: pass
ML='%x'%sym['MainLoop']
def a(n,o=0): return '%x'%(sym[n]+o)
W='/tmp/stella_run_'+VAR; shutil.rmtree(W,ignore_errors=True); os.makedirs(W)
shutil.copy(os.path.join(ROOT,'build',BINN),W)
NOP=sym['NOPAUSE']; TOT=312 if sym['HZ50'] else 262
cmds=[]
header=[]
header.append(f'breakIf {{pc=={ML} && _scanEnd!=#{TOT} && _fCount>#2}}')
asserts=[]
def assert_at(desc, cond):
    asserts.append(desc)
    k=len(asserts)
    header.append(f'breakIf {{pc=={ML} && *f0==#{k} && !({cond})}}')
    cmds.append(f'ram f0 {k:02x}'); fr(2); cmds.append('ram f0 00')
fc=[0]
snaps=[]
def fr(n):
    cmds.append(f'frame {n}'); fc[0]+=n
def snap(name):
    cmds.append('saveSnap'); snaps.append(name)
def joy(d,v): cmds.append(f'joy0{d} {v}')
def sw(v): cmds.append(f'swchb {v}')
def ram(n,val,o=0): cmds.append(f'ram {a(n,o)} {val:02x}')
def calm():
    ram('houses',31); ram('plState',0); ram('plTimer',255)
    for i in range(5): ram('dT',255,i)
fr(60); snap('01_title')
sw('3d'); fr(3); sw('3f'); fr(3); sw('3d'); fr(3); sw('3f'); fr(30)
assert_at('select -> level 3', f'*{a("startLevel")}==#3')
snap('02_title_level3')
sw('3d'); fr(3); sw('3f'); fr(3); sw('3d'); fr(3); sw('3f'); fr(3)
joy('Fire',0); fr(3); joy('Fire',1); fr(3)
assert_at('fire starts game', f'*{a("state")}==#1')
fr(240); calm(); ram('dX',120,0); ram('dX',70,1); ram('dX',140,3); ram('dX',95,4); ram('plState',1); ram('plLane',4); ram('plX',40); fr(1); snap('03_gameplay')
calm(); joy('Up',0); fr(1); joy('Up',1); fr(2)
assert_at('up -> lane 1', f'*{a("pLane")}==#1')
joy('Right',0); fr(20); joy('Right',1); fr(1)
assert_at('right -> moved right, facing right', f'*{a("pX")}>#40 && *{a("facing")}==#0')
joy('Fire',0); fr(4); snap('04_shot_right'); joy('Fire',1); fr(40)
calm(); joy('Left',0); fr(3); joy('Left',1); fr(1)
assert_at('left -> facing left', f'*{a("facing")}==#8')
joy('Fire',0); fr(3); snap('05_turned_left_shot'); joy('Fire',1); fr(30)
calm(); ram('pLane',1); ram('plState',1); ram('plLane',1); ram('plX',30); fr(1)
joy('Fire',0); fr(1); joy('Fire',1); fr(10)
assert_at('plokhish shot', f'*{a("plState")}==#0')
ram('houses',31); ram('plState',2); ram('plLane',2); ram('plX',17); ram('plTimer',200); ram('pLane',3); ram('pX',40); fr(2); snap('06_plokhish_sabotage')
ram('pLane',2); fr(1); snap('06b_star_and_plokhish_same_lane_a'); fr(1); snap('06c_star_and_plokhish_same_lane_b')
assert_at('NEGATIVE CONTROL (must be logged)', f'*{a("state")}==#7')
calm(); ram('dX',90,0); ram('dE',0,0); ram('pLane',0); ram('pX',40); joy('Right',0); fr(1); joy('Right',1)
joy('Fire',0); fr(12); snap('07_dollar_explosion'); joy('Fire',1); fr(30)
calm(); ram('plState',1); ram('plLane',3); ram('plX',45); ram('dX',100,1); sw('37'); fr(5); snap('08_paused_bw')
assert_at('paused' if not NOP else 'NOPAUSE: B/W switch does not pause', f'*{a("paused")}==#{0 if NOP else 1}')
fr(30); sw('3f'); fr(5); calm()
assert_at('unpaused', f'*{a("paused")}==#0')
ram('houses',1); ram('dX',20,0); ram('dE',0,0); ram('plState',0); fr(120)
assert_at('game over', f'*{a("state")}==#2')
snap('09_game_over')
fr(150); joy('Fire',0); fr(3); joy('Fire',1); fr(3)
assert_at('restart after game over', f'*{a("state")}==#1')
sw('3e'); fr(3); sw('3f'); fr(10)
assert_at('reset restarts', f'*{a("state")}==#1 && *{a("houses")}==#31')
calm(); sw('7f'); fr(60); sw('bf'); fr(60); sw('ff'); fr(60); sw('3f'); fr(10)
assert_at('difficulty switches ok, still playing', f'*{a("state")}==#1')
assert_at('B/W at power-on style: switch left in B/W then reset -> not paused', f'*{a("paused")}==#0')
sw('3d'); fr(3); sw('3f'); fr(10)
assert_at('select -> title', f'*{a("state")}==#0')
fr(30); snap('10_title_hiscore')
total=fc[0]
open(os.path.expanduser('~/.config/stella/autoexec.script'),'w').write('\n'.join(header+cmds)+'\n')
env=dict(os.environ)
p=subprocess.Popen(['timeout',str(int(sys.argv[1]) if len(sys.argv)>1 else 25),'xvfb-run','-a','stella','-debug','-dbg.logbreaks','1','-loglevel','2','-logtoconsole','1','-snapsavedir',W,'-dev.settings',os.environ.get('DEVSET','0'),os.path.join(W,BINN)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,cwd=W)
out=p.communicate()[0]
subprocess.run(['pkill','-f','stella -debug'])
cbp=[l for l in out.splitlines() if l.startswith('CBP')]
frames=[l for l in out.splitlines() if 'frame' in l.lower() and 'CBP' not in l][:0]
pngs=sorted(glob.glob(W+'/*.png'),key=os.path.getmtime)
print('frames scripted:',total,'snaps:',len(pngs),'expected',len(snaps))
print('assert/scanline violations logged:',len(cbp))
for l in cbp[:20]: print(l)
idx=[int(l[4:6],16) for l in cbp]
negi=1+asserts.index('NEGATIVE CONTROL (must be logged)')
print('negative-control logged:', negi in idx)
real=[l for l,i in zip(cbp,idx) if i!=negi]
print('REAL violations:', len(real))
for l in real[:20]: print(l)
SD=os.path.join(ROOT,'screenshots',VAR); os.makedirs(SD,exist_ok=True)
for f,n in zip(pngs,snaps):
    shutil.copy(f,os.path.join(SD,n+'.png'))
for l in out.splitlines():
    if 'Display Format' in l or 'Bankswitch Type' in l: print('STELLA:',l.strip())
print('asserts:',asserts)
