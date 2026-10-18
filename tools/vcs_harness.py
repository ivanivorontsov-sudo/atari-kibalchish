import sys
from py65.devices.mpu6502 import MPU

TIA_W = {0x00:'VSYNC',0x01:'VBLANK',0x02:'WSYNC',0x10:'RESP0',0x11:'RESP1',0x12:'RESM0',0x13:'RESM1',0x14:'RESBL',
         0x20:'HMP0',0x21:'HMP1',0x22:'HMM0',0x23:'HMM1',0x24:'HMBL',0x2A:'HMOVE',0x2B:'HMCLR',
         0x15:'AUDC0',0x16:'AUDC1',0x17:'AUDF0',0x18:'AUDF1',0x19:'AUDV0',0x1A:'AUDV1',0x09:'COLUBK',0x08:'COLUPF',0x06:'COLUP0',0x07:'COLUP1'}

class Bus:
    def __init__(self, rom, h):
        self.rom = rom; self.h = h; self.ram = bytearray(128)
    def __getitem__(self, a):
        if isinstance(a, slice):
            return [self[i] for i in range(*a.indices(0x10000))]
        a &= 0x1FFF
        if a & 0x1000: return self.rom[a & 0xFFF]
        if not (a & 0x80):
            r = a & 0x0F
            if r == 0x0C: return 0x00 if self.h.fire else 0x80
            if r == 0x0D: return 0x80
            return 0
        if not (a & 0x200): return self.ram[a & 0x7F]
        r = a & 0x2FF
        if (r & 0x07) == 0: return self.h.swcha
        if (r & 0x07) == 2: return self.h.swchb
        if (r & 0x05) == 4:
            v = self.h.read_timer()
            if self.h.first_read:
                self.h.first_read = False
                self.h.cur.setdefault('timer_first', []).append(v)
            return v
        return 0
    def __setitem__(self, a, v):
        a &= 0x1FFF
        if a & 0x1000:
            self.h.err('write to ROM %04x' % a); return
        if not (a & 0x80):
            self.h.tia_write(a & 0x3F, v); return
        if not (a & 0x200):
            self.ram[a & 0x7F] = v; return
        r = a & 0x2FF
        if r & 0x14 == 0x14:
            self.h.set_timer([1,8,64,1024][r & 3], v)

class VCS:
    def __init__(self, binpath, sympath, ram_init=None):
        self.rom = open(binpath,'rb').read()
        assert len(self.rom) == 4096
        self.sym = {}
        for line in open(sympath):
            p = line.split()
            if len(p) >= 2 and not p[0].startswith('-'):
                try: self.sym[p[0]] = int(p[1],16)
                except: pass
        self.fire = False; self.swcha = 0xFF; self.swchb = 0x3F
        self.bus = Bus(self.rom, self)
        if ram_init is not None:
            for i in range(128): self.bus.ram[i] = ram_init[i]
        self.mpu = MPU(memory=self.bus, pc=None)
        self.mpu.sp = 0xFD
        self.now = 0; self.wsync = False
        self.timer_int = 1024; self.timer_val = 0; self.timer_start = 0
        self.errors = []; self.frames = []; self.cur = None
        self.vsync_on = False; self.vsync_start = None; self.last_hmove = -999
        self.frame_index = 0
        self.first_read = False
        self.min_sp = 0xFF
        self.new_frame_stats()
    def err(self, m):
        self.errors.append((self.frame_index, m))
    def new_frame_stats(self):
        self.cur = {'vsync_lines':None,'vblank_off':None,'vblank_on':None,'aud':{},'hmove_bad':0,'hm_after':0,'writes':0}
    def line_cycle(self):
        if self.vsync_start is None: return (None, self.now % 76)
        return (self.now // 76 - self.vsync_start, self.now % 76)
    def set_timer(self, interval, v):
        self.timer_int = interval; self.timer_val = v; self.timer_start = self.now; self.first_read = True
    def read_timer(self):
        e = self.mpu.processorCycles + 3 - self.timer_start
        if e <= 0: return self.timer_val
        I = self.timer_int
        if e <= self.timer_val * I:
            return self.timer_val - 1 - (e - 1) // I if self.timer_val > 0 else 0
        over = e - self.timer_val * I - 1
        return (0xFF - over) & 0xFF
    def tia_write(self, r, v):
        name = TIA_W.get(r)
        ln, cyc = self.line_cycle()
        if r == 0x00:
            on = bool(v & 2)
            if on and not self.vsync_on:
                if self.vsync_start is not None:
                    total = self.now // 76 - self.vsync_start
                    self.cur['total'] = total
                    self.frames.append(self.cur)
                    self.frame_index += 1
                    self.new_frame_stats()
                self.vsync_start = self.now // 76
            if (not on) and self.vsync_on and self.vsync_start is not None:
                self.cur['vsync_lines'] = self.now // 76 - self.vsync_start
            self.vsync_on = on
        elif r == 0x01:
            if v & 2:
                if self.cur['vblank_off'] is not None and self.cur['vblank_on'] is None: self.cur['vblank_on'] = ln
            else: self.cur['vblank_off'] = ln
        elif r == 0x02:
            self.wsync = True
        elif r == 0x2A:
            if cyc != 3: self.cur['hmove_bad'] += 1
            self.last_hmove = self.now
        elif r in (0x20,0x21,0x22,0x23,0x24,0x2B):
            if self.now - self.last_hmove < 24: self.cur['hm_after'] += 1
        elif r in (0x15,0x16,0x17,0x18,0x19,0x1A):
            self.cur['aud'][name] = v
    def step(self):
        m = self.mpu
        op = self.bus[m.pc]
        self.now = m.processorCycles + m.cycletime[op]
        m.step()
        if m.sp < self.min_sp: self.min_sp = m.sp
        if self.wsync:
            self.wsync = False
            c = m.processorCycles
            m.processorCycles = ((c + 75) // 76) * 76
        if op in (0x00,):
            self.err('BRK executed at %04x' % m.pc)
    def run_frames(self, n):
        target = self.frame_index + n
        guard = 0
        while self.frame_index < target:
            self.step(); guard += 1
            if guard > 200000 * n: raise RuntimeError('no vsync')
    def ram(self, name, off=0):
        return self.bus.ram[(self.sym[name] + off) & 0x7F]
    def setram(self, name, v, off=0):
        self.bus.ram[(self.sym[name] + off) & 0x7F] = v & 0xFF
    def joy(self, up=False, down=False, left=False, right=False):
        v = 0xFF
        if right: v &= ~0x80
        if left: v &= ~0x40
        if down: v &= ~0x20
        if up: v &= ~0x10
        self.swcha = v & 0xFF
