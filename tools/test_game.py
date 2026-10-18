import random, sys
from vcs_harness import VCS
VAR=sys.argv[1] if len(sys.argv)>1 else 'NTSC'
BIN=f'../build/kibalchish_{VAR}.bin'; SYM=f'../build/kibalchish_{VAR}.sym'
_s=VCS(BIN,SYM).sym
HZ50=_s['HZ50']; NOPAUSE=_s['NOPAUSE']; SHOTSPD=_s['SHOTSPD']; LREP=_s['LREP']; DIFFADD=_s['DIFFADD']; FPSN=_s['FPSN']
TOTAL=312 if HZ50 else 262; VBOFF=48 if HZ50 else 40; VBON=VBOFF+(228 if HZ50 else 192)
print(f'variant {VAR}: TV={_s["TV"]} HZ50={HZ50} NOPAUSE={NOPAUSE} lines={TOTAL}')
def xok(got,base,n): return base+n <= got <= base+n+(n+4)//5 if HZ50 else got==base+n
def xokn(got,base,n): return base-n-(n+4)//5 <= got <= base-n if HZ50 else got==base-n
results=[]
ALL=[]
def check(name, cond, info=''):
    results.append((name, bool(cond), info))
    return cond

def new(seed=None, swchb=0x3F):
    ram=None
    if seed is not None:
        r=random.Random(seed); ram=[r.randrange(256) for _ in range(128)]
    v=VCS(BIN,SYM,ram); v.swchb=swchb; ALL.append(v)
    v.run_frames(5)
    return v

def frames_ok(v, start=1):
    bad=[(i,f) for i,f in enumerate(v.frames) if i>=start and (f.get('total')!=TOTAL or f['vsync_lines']!=3 or f['vblank_off']!=VBOFF or f['vblank_on']!=VBON or f['hmove_bad'] or f['hm_after'])]
    return bad

def timer_ok(v):
    t=[x for f in v.frames for x in f.get('timer_first',[])]
    return min(t) if t else None

def press_fire(v, hold=2, after=2):
    v.fire=True; v.run_frames(hold); v.fire=False; v.run_frames(after)

def start_game(v):
    v.fire=False; v.run_frames(2); press_fire(v)

def pulse_sw(v, bit, frames=3, after=3):
    v.swchb &= ~bit; v.run_frames(frames); v.swchb |= bit; v.run_frames(after)

def lanes_clear(v):
    v.setram('houses',31)
    for i in range(5):
        v.setram('dX',0,i); v.setram('dE',0,i); v.setram('dT',250,i)
    v.setram('plState',0); v.setram('plTimer',250)

S=lambda v,n,o=0:v.ram(n,o)

for seed in range(8):
    v=new(seed)
    check(f'power-on seed {seed}: title state', S(v,'state')==0 and S(v,'startLevel')==1)
v=new(1)
check('power-on: sound silent on title', all(f['aud'].get('AUDV0',0)==0 and f['aud'].get('AUDV1',0)==0 for f in v.frames[1:]))
vh=VCS(BIN,SYM); vh.fire=True; vh.run_frames(60)
check('fire held from power-on does not start until released', vh.ram('state')==0)
vh.fire=False; vh.run_frames(2); vh.fire=True; vh.run_frames(2)
check('...then release+press starts', vh.ram('state')==1)
v.fire=False; v.run_frames(2); press_fire(v)
check('fire press starts game', S(v,'state')==1 and S(v,'houses')==31 and S(v,'scoreH')==0 and S(v,'scoreL')==0 and S(v,'level')==1)
check('start: no shot fired by the start press', S(v,'shotDir')==0)

v=new(2)
lv=[]
for i in range(5):
    pulse_sw(v,0x02); lv.append(S(v,'startLevel'))
check('Game Select on title cycles start level 2,3,4,1,2', lv==[2,3,4,1,2], str(lv))
pulse_sw(v,0x02); pulse_sw(v,0x02)
start_game(v)
check('game starts at selected level 4', S(v,'level')==4, str(S(v,'level')))
spd4=S(v,'speed')

v=new(3); start_game(v); lanes_clear(v)
def hold(v,n,**k):
    lanes_clear(v)
    v.joy(**k); v.run_frames(n); v.joy()
p0=(S(v,'pX'),S(v,'pLane'))
hold(v,1,up=True); a=S(v,'pLane')
check('joy UP moves one lane up immediately', a==p0[1]-1, f'{p0}->{a}')
hold(v,1,down=True); v.run_frames(1); hold(v,1,down=True); b=S(v,'pLane')
check('joy DOWN moves lanes down', b==p0[1]+1, str(b))
x0=S(v,'pX'); hold(v,10,right=True)
check('joy RIGHT moves right & faces right', xok(S(v,'pX'),x0,10) and S(v,'facing')==0)
x0=S(v,'pX'); hold(v,10,left=True)
check('joy LEFT moves left & turns around (facing left)', xokn(S(v,'pX'),x0,10) and S(v,'facing')==8)
v.setram('pLane',2); v.setram('pX',40)
hold(v,1,up=True,right=True)
check('diagonal UP+RIGHT', S(v,'pLane')==1 and xok(S(v,'pX'),40,1) and S(v,'facing')==0)
v.run_frames(1); hold(v,1,up=True,left=True)
v.setram('pX',41); check('diagonal UP+LEFT', S(v,'pLane')==0 and True and S(v,'facing')==8)
v.run_frames(1); hold(v,1,down=True,right=True)
check('diagonal DOWN+RIGHT', S(v,'pLane')==1 and S(v,'pX')>=41 and S(v,'facing')==0)
v.run_frames(1); xb=S(v,'pX'); hold(v,1,down=True,left=True)
check('diagonal DOWN+LEFT', S(v,'pLane')==2 and S(v,'pX')<xb and S(v,'facing')==8)
hold(v,200,left=True); check('left limit x=20', S(v,'pX')==20)
hold(v,200,right=True); check('right limit x=60', S(v,'pX')==60)
hold(v,200,up=True); check('top lane limit 0', S(v,'pLane')==0)
hold(v,200,down=True); check('bottom lane limit 4', S(v,'pLane')==4)
v.run_frames(1); v.setram('pLane',0); v.joy(down=True); seq=[]
for i in range(25): lanes_clear(v); v.run_frames(1); seq.append(S(v,'pLane'))
v.joy()
R=LREP+1
check(f'held DOWN auto-repeats every {R} frames', seq[0]==1 and seq[R-1]==1 and seq[R]==2 and seq[2*R]==3, str(seq))
v.run_frames(1); v.setram('pLane',2); hold(v,1,up=True); hold(v,1,down=True)
check('direct UP->DOWN reversal without center responds instantly', S(v,'pLane')==2)
v.setram('pLane',2); hold(v,1,up=True); v.run_frames(1); hold(v,1,up=True)
check('tap-tap UP moves twice', S(v,'pLane')==0)

v.setram('pLane',2); v.setram('pX',30); hold(v,1,right=True); lanes_clear(v)
check('still playing before fire tests', S(v,'state')==1)
press_fire(v,1,0)
check('fire facing right launches shot right', S(v,'shotDir')==0x02 and S(v,'shotLane')==2)
x1=S(v,'shotX'); v.run_frames(1); x2=S(v,'shotX')
check(f'shot travels right {SHOTSPD}px/frame', x2==x1+SHOTSPD, f'{x1}->{x2}')
v.fire=True
for i in range(40): lanes_clear(v); v.run_frames(1)
check('holding fire = no autofire; shot leaves screen', S(v,'shotDir')==0 and S(v,'shotX')==0)
v.fire=False; v.run_frames(1)
hold(v,1,left=True)
press_fire(v,1,0)
check('fire facing left launches shot left', S(v,'shotDir')==0x82)
x1=S(v,'shotX'); v.run_frames(1)
check('shot travels left', S(v,'shotX')==x1-SHOTSPD)
lanes_clear(v); v.run_frames(15)
check('left shot disappears at left edge', S(v,'shotDir')==0 and S(v,'shotX')==0)
press_fire(v,1,0); x=S(v,'shotX'); press_fire(v,1,0)
check('second press while shot active does not restart shot', S(v,'shotX')==x-8 or S(v,'shotX')<x)

v=new(4); start_game(v); lanes_clear(v)
v.setram('pLane',1); v.setram('pX',30); hold(v,1,right=True)
v.setram('dX',100,1); v.setram('dE',0,1)
press_fire(v,1,0); v.run_frames(20)
check('shot kills dollar: explosion + score 1 + kills 1', S(v,'scoreL')==1 and S(v,'kills')==1 and (S(v,'dE',1)>0 or S(v,'dX',1)==0))
ex=[f['aud'].get('AUDC0') for f in v.frames[-20:]]
check('explosion sound (noise AUDC0=8)', 8 in ex)
v.run_frames(20)
check('dollar respawn timer set after explosion', S(v,'dX',1)==0 and S(v,'dT',1)>0)

v=new(5); start_game(v); lanes_clear(v)
v.setram('dX',20,3)
for i in range(30):
    v.setram('plState',0); v.setram('plTimer',250); v.run_frames(1)
check('dollar reaching house destroys it (bit3 cleared)', S(v,'houses')==31-8, bin(S(v,'houses')))
check('house destruction sound', any(f['aud'].get('AUDC0')==8 and f['aud'].get('AUDF0')==31 for f in v.frames[-30:]))
v.run_frames(300)
check('no dollar spawns in a lane without a house', S(v,'dX',3)==0)

v=new(6); start_game(v); lanes_clear(v)
v.setram('plState',1); v.setram('plLane',0); v.setram('plX',30); v.setram('pLane',4)
v.run_frames(80)
check('Plokhish walks to house and starts sabotage', S(v,'plState')==2)
aud=[f['aud'].get('AUDV1',0) for f in v.frames[-40:]]
v.run_frames(40)
aud+= [f['aud'].get('AUDV1',0) for f in v.frames[-40:]]
check('warning beep while Plokhish sabotages', max(aud)>0 and min(aud)==0)
v.run_frames(300)
check('Plokhish blows up house 0 after timer', S(v,'houses')&1==0, bin(S(v,'houses')))

v=new(7); start_game(v); lanes_clear(v)
v.setram('plState',1); v.setram('plLane',2); v.setram('plX',24); v.setram('pLane',2); v.setram('pX',50)
v.joy(left=True); v.run_frames(1); v.joy(); press_fire(v,1,0); v.run_frames(10)
check('turn around + shoot kills Plokhish (+5)', S(v,'plState')==0 and S(v,'scoreL')==5)
check('Plokhish respawn timer set', S(v,'plTimer')>=50)

v=new(8); start_game(v)
lv=S(v,'level'); sp=S(v,'speed')
v.setram('kills',7); lanes_clear(v)
v.setram('pLane',0); v.setram('pX',30); hold(v,1,right=True); v.setram('dX',90,0)
press_fire(v,1,0); v.run_frames(15)
check('8 kills -> level up', S(v,'level')==lv+1 and S(v,'kills')==0)
check('dollar speed increases with level', S(v,'speed')>sp, f'{sp}->{S(v,"speed")}')
v.setram('level',9); v.setram('kills',7); v.setram('dX',90,0); lanes_clear(v); v.setram('dX',90,0)
v.setram('shotDir',0); press_fire(v,1,0); v.run_frames(15)
check('level caps at 9', S(v,'level')==9)
sp9=S(v,'speed')
v.swchb |= 0x40; v.run_frames(2)
check('Left difficulty A: dollars faster', S(v,'speed')==min(255,sp9+DIFFADD), f'{sp9}->{S(v,"speed")}')
v.swchb &= ~0x40; v.run_frames(2)
check('Left difficulty back to B: normal speed', S(v,'speed')==sp9)
lanes_clear(v); v.setram('plState',1); v.setram('plLane',1); v.setram('plX',18); v.setram('plAcc',255)
v.run_frames(2); tB=S(v,'plTimer')
lanes_clear(v); v.swchb |= 0x80; v.setram('plState',1); v.setram('plLane',1); v.setram('plX',18); v.setram('plAcc',255)
v.run_frames(2); tA=S(v,'plTimer'); v.swchb &= ~0x80
check(f'Right difficulty A: sabotage {60*FPSN//6} frames faster (=1 s)', tB-tA==60*FPSN//6, f'B={tB} A={tA}')

v=new(9); start_game(v); lanes_clear(v)
v.setram('scoreH',0x99); v.setram('scoreL',0x98)
v.setram('pLane',0); v.setram('pX',30); hold(v,1,right=True); v.setram('dX',90,0)
press_fire(v,1,0); v.run_frames(15)
check('BCD score 9998+1 = 9999', S(v,'scoreH')==0x99 and S(v,'scoreL')==0x99)
v.setram('dX',90,0); v.setram('dE',0,0); press_fire(v,1,0); v.run_frames(15)
check('score caps at 9999', S(v,'scoreH')==0x99 and S(v,'scoreL')==0x99)

v=new(10); start_game(v); lanes_clear(v)
v.setram('scoreL',0x42); v.setram('houses',4); v.setram('dX',18,2)
v.run_frames(10)
check('last house destroyed -> GAME OVER state', S(v,'state')==2)
check('hi score saved', S(v,'hiL')==0x42 and S(v,'hiH')==0)
check('game over sound on channel 1', any(f['aud'].get('AUDC1')==12 for f in v.frames[-10:]))
press_fire(v,1,1)
check('fire ignored during 2s game-over delay', S(v,'state')==2)
v.run_frames(130)
check('game-over sound ends (silence)', v.frames[-1]['aud'].get('AUDV1',0)==0 and v.frames[-1]['aud'].get('AUDV0',0)==0)
press_fire(v)
check('fire after delay restarts game', S(v,'state')==1 and S(v,'houses')==31 and S(v,'scoreL')==0)
v.setram('houses',0); v.run_frames(3)
pulse_sw(v,0x02)
check('Game Select on game over -> title', S(v,'state')==0)
check('title shows hi score (sg digits nonzero)', any(S(v,'sg0',i) or S(v,'sg1',i) for i in range(5)))

v=new(11); pulse_sw(v,0x01)
check('Game Reset on title starts game', S(v,'state')==1)
v.setram('scoreL',0x33); v.setram('houses',7)
v.swchb &= ~1; v.run_frames(30)
check('Game Reset during play restarts once (held reset no repeat loop)', S(v,'state')==1 and S(v,'houses')==31 and S(v,'scoreL')==0)
v.setram('scoreL',0x11); v.run_frames(20)
check('held reset does not keep restarting', S(v,'scoreL')==0x11)
v.swchb |= 1; v.run_frames(2)
v.setram('houses',0); v.run_frames(3)
check('game over reached', S(v,'state')==2)
pulse_sw(v,0x01)
check('Game Reset on game over restarts', S(v,'state')==1 and S(v,'houses')==31)
pulse_sw(v,0x02)
check('Game Select during play -> title', S(v,'state')==0)

if NOPAUSE:
    v=new(12); start_game(v); lanes_clear(v); v.setram('dX',100,0)
    x=S(v,'dX',0)
    v.swchb &= ~0x08; v.run_frames(30)
    check('NOPAUSE: Color->B/W does not pause', S(v,'paused')==0 and S(v,'state')==1)
    hold(v,5,right=True); v.setram('dX',100,0); v.run_frames(30)
    check('NOPAUSE: game keeps running with switch on B/W', S(v,'dX',0)<100 and S(v,'colMask')==0xFF)
    v.swchb |= 0x08; v.run_frames(30)
    check('NOPAUSE: B/W->Color does not pause', S(v,'paused')==0)
    for i in range(20):
        v.swchb ^= 0x08; v.run_frames(2)
    check('NOPAUSE: rapid switch toggling never pauses', S(v,'paused')==0 and S(v,'state')==1)
v=new(12); start_game(v); lanes_clear(v)
v.setram('dX',100,0); v.setram('speed',200)
if not NOPAUSE:
    v.swchb &= ~0x08; v.run_frames(3)
    check('Color->B/W switch pauses game', S(v,'paused')==1)
    snap=(S(v,'pX'),S(v,'pLane'),S(v,'dX',0),S(v,'frame'))
    v.joy(right=True,down=True); v.fire=True; v.run_frames(30); v.joy(); v.fire=False; v.run_frames(2)
    check('paused: joystick/fire/dollars frozen', (S(v,'pX'),S(v,'pLane'),S(v,'dX',0))==snap[:3] and S(v,'shotDir')==0)
    check('paused: sound muted', all(f['aud'].get('AUDV0',0)==0 and f['aud'].get('AUDV1',0)==0 for f in v.frames[-30:]))
    check('paused: grayscale palette', S(v,'colMask')==0x0F and (S(v,'colBK')&0xF0)==0)
    v.swchb |= 0x08; v.run_frames(3)
    check('B/W->Color resumes', S(v,'paused')==0 and S(v,'colMask')==0xFF)
    v.run_frames(5)
    check('resumed: dollars move again', S(v,'dX',0)<snap[2])
    v=new(13, swchb=0x37)
    check('B/W switch at power-on: title fine, not paused', S(v,'state')==0 and S(v,'paused')==0)
    start_game(v); v.run_frames(5)
    check('B/W switch at power-on: game runs (no pause)', S(v,'paused')==0 and S(v,'state')==1)
    v.swchb |= 0x08; v.run_frames(2)
    check('then flipping switch pauses (edge-triggered, 7800 pause compatible)', S(v,'paused')==1)
    pulse_sw(v,0x01)
    check('Reset clears pause', S(v,'paused')==0 and S(v,'state')==1)
    v=new(14); v.swchb&=~0x08; v.run_frames(3)
    check('B/W on title: no effect', S(v,'paused')==0 and S(v,'state')==0)

v=new(15); start_game(v); lanes_clear(v)
v.setram('pLane',3); v.setram('pX',30); hold(v,1,right=True)
press_fire(v,1,0)
check('shot sound (AUDC0=4 pure tone)', any(f['aud'].get('AUDC0')==4 and f['aud'].get('AUDV0',0)>0 for f in v.frames[-2:]))
v.run_frames(20)
check('sound off when no events', v.frames[-1]['aud'].get('AUDV0',0)==0 and v.frames[-1]['aud'].get('AUDV1',0)==0)
v.setram('plState',1); v.setram('plLane',0); v.setram('plX',50)
v.run_frames(64)
check('Plokhish walking tick sound', any(f['aud'].get('AUDV1',0)>0 for f in v.frames[-64:]))

v=new(16); start_game(v); v.min_sp=0xFF
v.run_frames(60*60*3)
check('idle game: stack depth ok (SP>=$F8)', v.min_sp>=0xF8, hex(v.min_sp))
check('3-minute idle game ends in GAME OVER by itself (dollars+Plokhish win)', S(v,'state')==2, f"houses={S(v,'houses')}")
bad=frames_ok(v)
check('idle game: every frame 262 lines', not bad, str(bad[:2]))

rng=random.Random(99)
fz=new(17); allbad=[]; fz.min_sp=0xFF
cnt=0
for blk in range(3000):
    d=rng.randrange(16)
    fz.joy(up=bool(d&1),down=bool(d&2) and not d&1,left=bool(d&4),right=bool(d&8) and not d&4)
    fz.fire=rng.random()<0.4
    sw=0x3F
    if rng.random()<0.01: sw&=~1
    if rng.random()<0.01: sw&=~2
    if rng.random()<0.5: sw&=~8
    if rng.random()<0.5: sw|=0x40
    if rng.random()<0.5: sw|=0x80
    if rng.random()<0.3: sw=fz.swchb
    fz.swchb=sw
    fz.run_frames(rng.randrange(1,12))
    for i in range(5):
        if fz.ram('dX',i)>149 or fz.ram('lP0x',i)>149 or fz.ram('lP1x',i)>149: allbad.append(('pos',i))
    if fz.ram('shotX')>149: allbad.append('shotX')
    if not (20<=fz.ram('pX')<=60) and fz.ram('state')!=0: allbad.append(('pX',fz.ram('pX')))
    if fz.ram('pLane')>4: allbad.append('lane')
    if fz.ram('state')>2: allbad.append('state')
bad=frames_ok(fz)
check(f'fuzz {len(fz.frames)} frames random input/switches: always 262 lines, 3 VSYNC, 37 VBLANK, 192 visible, 30 overscan', not bad, str(bad[:2]))
check('fuzz: object X always 0..149, lane/state valid', not allbad, str(allbad[:5]))
check('fuzz: no timer overrun (vblank/overscan logic fits)', fz.ram('overrun')==0 and timer_ok(fz)>0, f'min timer left={timer_ok(fz)}')
check('fuzz: stack never reaches variables (min SP vs last var $%02X)' % (0x80+0x6B), fz.min_sp>=0xF0, hex(fz.min_sp))
check('fuzz: no CPU errors', not fz.errors, str(fz.errors[:3]))

tot=sum(len(x.frames) for x in ALL); badall=[b for x in ALL for b in frames_ok(x)]
check(f'ALL scenarios ({tot} frames incl. every transition): 262 lines / 3+37+192+30, HMOVE at cycle 3, no HMxx write <24 cycles after HMOVE', not badall, str(badall[:2]))
check('ALL scenarios: no timer overrun flag', all(x.ram('overrun')==0 for x in ALL))
fails=[r for r in results if not r[1]]
for n,ok,info in results:
    print(('PASS ' if ok else 'FAIL ')+n+((' ['+info+']') if info and not ok else ''))
print(f'\n{len(results)-len(fails)}/{len(results)} passed')
sys.exit(1 if fails else 0)
