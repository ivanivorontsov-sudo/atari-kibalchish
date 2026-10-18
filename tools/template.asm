	processor 6502
	include "vcs.h"
NO_ILLEGAL_OPCODES = 1
	include "macro.h"

	IFNCONST TV
TV = 0
	ENDIF
	IFNCONST NOPAUSE
NOPAUSE = 0
	ENDIF
	IF TV = 1 || TV = 3
HZ50 = 1
FPSN = 5
VBT = 57
OST = 43
PADL = 18
SHOTSPD = 5
LREP = 8
PLWALK = 77
DIFFADD = 24
	ELSE
HZ50 = 0
FPSN = 6
VBT = 44
OST = 36
PADL = 0
SHOTSPD = 4
LREP = 10
PLWALK = 64
DIFFADD = 40
	ENDIF
	IF TV = 0
C_STAR = $44
C_STAR2 = $46
C_JAR = $58
C_JARF = $5E
C_DOL = $1E
C_BOOM = $36
C_HOUSE = $F6
C_FIELD = $C4
C_GOF = $42
C_WHITE = $0E
C_TBG = $82
	ENDIF
	IF TV = 1 || TV = 2
C_STAR = $64
C_STAR2 = $66
C_JAR = $86
C_JARF = $8A
C_DOL = $2C
C_BOOM = $46
C_HOUSE = $28
C_FIELD = $54
C_GOF = $62
C_WHITE = $0E
C_TBG = $D2
	ENDIF
	IF TV = 3
C_STAR = $04
C_STAR2 = $04
C_JAR = $06
C_JARF = $0E
C_DOL = $0C
C_BOOM = $0E
C_HOUSE = $0A
C_FIELD = $08
C_GOF = $04
C_WHITE = $0E
C_TBG = $02
	ENDIF

ST_TITLE = 0
ST_PLAY  = 1
ST_OVER  = 2

	SEG.U VARS
	ORG $80
frame      ds 1
rand       ds 1
state      ds 1
paused     ds 1
prevSW     ds 1
prevFire   ds 1
scoreH     ds 1
scoreL     ds 1
hiH        ds 1
hiL        ds 1
level      ds 1
startLevel ds 1
kills      ds 1
speed      ds 1
acc        ds 1
pX         ds 1
pLane      ds 1
facing     ds 1
laneRep    ds 1
shotX      ds 1
shotLane   ds 1
shotDir    ds 1
dX         ds 5
dE         ds 5
dT         ds 5
houses     ds 1
plState    ds 1
plLane     ds 1
plX        ds 1
plTimer    ds 1
s0T        ds 1
s0K        ds 1
s1T        ds 1
s1K        ds 1
goTimer    ds 1
sg0        ds 5
sg1        ds 5
lP0x       ds 5
lP1x       ds 5
lP0g       ds 5
lP1g       ds 5
lC0        ds 5
lC1        ds 5
lR0        ds 5
ptr0       ds 2
ptr1       ds 2
pfptr      ds 2
shotEn     ds 1
colBK      ds 1
colPF      ds 1
colSc      ds 1
colMask    ds 1
temp       ds 1
temp2      ds 1
overrun    ds 1
prevV      ds 1
plAcc      ds 1
f5         ds 1
RAMEND
	echo "RAM used:", [RAMEND - $80]d, "bytes"

	MAC POSOBJ
	sec
.div	sbc #15
	bcs .div
	if >.div != >*
	echo "POSOBJ PAGE CROSS"
	err
	endif
	eor #7
	asl
	asl
	asl
	asl
	sta {1}
	sta {2}
	ENDM

	SEG CODE
	ORG $F000

Reset
	SUBROUTINE
	CLEAN_START
	lda #0
	sta SWACNT
	sta SWBCNT
	lda #$FF
	sta prevSW
	sta colMask
	lda #1
	sta startLevel
	lda #$A5
	sta rand
	jsr GoTitle

MainLoop
	SUBROUTINE
	lda #2
	sta WSYNC
	sta VBLANK
	sta VSYNC
	IF HZ50 = 1
	lda #VBT
	sta TIM64T
	ENDIF
	sta WSYNC
	sta WSYNC
	sta WSYNC
	lda #0
	sta VSYNC
	IF HZ50 = 0
	lda #VBT
	sta TIM64T
	ENDIF
	jsr Precompute
	lda #0
	sta COLUBK
	lda INTIM
	bne VbWait
	inc overrun
VbWait
	lda INTIM
	bne VbWait
	sta WSYNC
	sta VBLANK
	IF PADL > 0
	ldy #PADL
.pt
	sta WSYNC
	dey
	bne .pt
	ENDIF
	lda state
	bne .gk
	jsr TitleKernel
	jmp .os
.gk
	jsr GameKernel
.os
	sta WSYNC
	IF PADL > 0
	lda #0
	sta COLUBK
	sta PF0
	sta PF1
	sta PF2
	sta GRP0
	sta GRP1
	sta ENAM0
	ldy #PADL
.pb
	sta WSYNC
	dey
	bne .pb
	ENDIF
	lda #2
	sta VBLANK
	lda #OST
	sta TIM64T
	jsr Switches
	jsr Update
	jsr Sound
	lda INTIM
	bne OsWait
	inc overrun
OsWait
	lda INTIM
	bne OsWait
	jmp MainLoop

GoTitle
	SUBROUTINE
	lda #ST_TITLE
	sta state
	lda #0
	sta paused
	sta s0T
	sta s1T
	sta AUDV0
	sta AUDV1
	rts

NewGame
	SUBROUTINE
	lda #ST_PLAY
	sta state
	lda #0
	sta paused
	sta scoreH
	sta scoreL
	sta kills
	sta shotDir
	sta shotX
	sta plState
	sta facing
	sta laneRep
	sta acc
	sta s0T
	sta s1T
	sta goTimer
	lda #%11111
	sta houses
	lda startLevel
	sta level
	lda #24
	sta pX
	lda #2
	sta pLane
	ldx #4
.n1
	lda #0
	sta dX,x
	sta dE,x
	jsr SpawnDelay
	txa
	asl
	asl
	asl
	IF HZ50 = 0
	asl
	ENDIF
	clc
	adc dT,x
	sta dT,x
	dex
	bpl .n1
	jsr PlRespawn
	jsr SetSpeed
	rts

Rand
	SUBROUTINE
	lda rand
	lsr
	bcc .r1
	eor #$B8
.r1
	sta rand
	rts

SpawnDelay
	SUBROUTINE
	jsr Rand
	and #63
	ldy level
	clc
	adc SpawnBase,y
	sta dT,x
	rts

PlRespawn
	SUBROUTINE
	jsr Rand
	and #127
	ldy level
	clc
	adc PlBase,y
	sta plTimer
	rts

SetSpeed
	SUBROUTINE
	ldx level
	lda SpeedTab,x
	bit SWCHB
	bvc .ss
	clc
	adc #DIFFADD
	bcc .ss
	lda #255
.ss
	sta speed
	rts

SabTime
	SUBROUTINE
	ldy level
	lda SabTab,y
	bit SWCHB
	bpl .sb
	sec
	sbc #[60*FPSN/6]
.sb
	sta plTimer
	rts

AddScore
	SUBROUTINE
	sed
	clc
	adc scoreL
	sta scoreL
	lda scoreH
	adc #0
	sta scoreH
	cld
	bcc .as
	lda #$99
	sta scoreH
	sta scoreL
.as
	rts

Switches
	SUBROUTINE
	lda SWCHB
	sta temp
	eor #$FF
	and prevSW
	sta temp2
	lda temp
	eor prevSW
	and #$08
	beq .nobw
	IF NOPAUSE = 1
	jmp .nobw
	ENDIF
	lda state
	cmp #ST_PLAY
	bne .nobw
	lda paused
	eor #1
	sta paused
.nobw
	lda temp
	sta prevSW
	lda temp2
	lsr
	bcc .noreset
	jmp NewGame
.noreset
	lsr
	bcc .nosel
	lda state
	bne .totitle
	ldx startLevel
	inx
	cpx #5
	bcc .sl1
	ldx #1
.sl1
	stx startLevel
	rts
.totitle
	jmp GoTitle
.nosel
	rts

Update
	SUBROUTINE
	jsr Rand
	inc frame
	IF HZ50 = 1
	dec f5
	bpl .f5ok
	lda #4
	sta f5
.f5ok
	ENDIF
	lda INPT4
	and #$80
	sta temp
	lda prevFire
	eor temp
	and prevFire
	sta temp2
	lda temp
	sta prevFire
	lda state
	beq .utitle
	cmp #ST_OVER
	beq .uover
	lda paused
	beq Play
	rts
.utitle
	lda temp2
	beq .ur
	jmp NewGame
.uover
	lda goTimer
	beq .uo1
	dec goTimer
	rts
.uo1
	lda temp2
	beq .ur
	jmp NewGame
.ur
	rts

Play
	SUBROUTINE
	jsr SetSpeed
	lda SWCHA
	sta temp
	bmi .noR
	lda pX
	cmp #60
	bcs .rf
	inc pX
	IF HZ50 = 1
	lda f5
	bne .rf
	lda pX
	cmp #60
	bcs .rf
	inc pX
	ENDIF
.rf
	lda #0
	sta facing
.noR
	lda temp
	and #$40
	bne .noL
	lda pX
	cmp #21
	bcc .lf
	dec pX
	IF HZ50 = 1
	lda f5
	bne .lf
	lda pX
	cmp #21
	bcc .lf
	dec pX
	ENDIF
.lf
	lda #8
	sta facing
.noL
	lda temp
	and #$30
	cmp prevV
	sta prevV
	beq .same
	lda #0
	sta laneRep
.same
	lda prevV
	cmp #$30
	beq .vdone
	lda laneRep
	beq .vmove
	dec laneRep
	jmp .vdone
.vmove
	lda #LREP
	sta laneRep
	lda temp
	and #$10
	bne .notUp
	lda pLane
	beq .vdone
	dec pLane
	jmp .vdone
.notUp
	lda pLane
	cmp #4
	bcs .vdone
	inc pLane
.vdone
	lda temp2
	beq .nofire
	lda shotDir
	bne .nofire
	lda pLane
	sta shotLane
	lda facing
	bne .fl
	lda pX
	clc
	adc #8
	sta shotX
	lda #$02
	sta shotDir
	bne .fs
.fl
	lda pX
	sec
	sbc #4
	sta shotX
	lda #$82
	sta shotDir
.fs
	lda #0
	sta s0K
	lda #8
	sta s0T
.nofire
	lda shotDir
	beq .noshot
	bmi .sleft
	lda shotX
	clc
	adc #SHOTSPD
	sta shotX
	cmp #146
	bcc .noshot
	bcs .shotoff
.sleft
	lda shotX
	sec
	sbc #SHOTSPD
	bcc .shotoff
	sta shotX
	cmp #4
	bcs .noshot
.shotoff
	lda #0
	sta shotDir
	sta shotX
.noshot
	lda #0
	sta temp
	lda acc
	clc
	adc speed
	IF HZ50 = 1
	bcc .ac1
	inc temp
	clc
.ac1
	adc speed
	ENDIF
	sta acc
	bcc .ac2
	inc temp
.ac2
	ldx #4
.dl
	lda dE,x
	beq .dnoexp
	dec dE,x
	bne .dnext
	lda #0
	sta dX,x
	jsr SpawnDelay
	jmp .dnext
.dnoexp
	lda dX,x
	bne .dact
	lda dT,x
	beq .dspawn
	dec dT,x
	jmp .dnext
.dspawn
	lda houses
	and LaneBit,x
	beq .dnext
	lda #148
	sta dX,x
	jmp .dnext
.dact
	lda temp
	beq .dnext
	lsr
	beq .dmv1
	dec dX,x
.dmv1
	dec dX,x
	lda dX,x
	cmp #17
	bcs .dnext
	lda #16
	sta dE,x
	lda houses
	and LaneBit,x
	beq .dnext
	lda LaneBit,x
	eor #$FF
	and houses
	sta houses
	lda #2
	sta s0K
	lda #31
	sta s0T
.dnext
	dex
	bpl .dl
	lda shotDir
	beq .nsc
	ldx shotLane
	lda dX,x
	beq .npc
	lda dE,x
	bne .npc
	lda shotX
	clc
	adc #4
	cmp dX,x
	bcc .npc
	lda dX,x
	clc
	adc #8
	cmp shotX
	bcc .npc
	lda #16
	sta dE,x
	lda #0
	sta shotDir
	sta shotX
	lda #1
	jsr AddScore
	lda #1
	sta s0K
	lda #15
	sta s0T
	inc kills
	lda kills
	cmp #8
	bcc .nsc
	lda #0
	sta kills
	lda level
	cmp #9
	bcs .nsc
	inc level
	jmp .nsc
.npc
	lda plState
	beq .nsc
	lda shotLane
	cmp plLane
	bne .nsc
	lda shotX
	clc
	adc #4
	cmp plX
	bcc .nsc
	lda plX
	clc
	adc #8
	cmp shotX
	bcc .nsc
	lda #0
	sta shotDir
	sta shotX
	sta plState
	jsr PlRespawn
	lda #5
	jsr AddScore
	lda #0
	sta s1K
	lda #23
	sta s1T
.nsc
	lda plState
	bne .pa
	dec plTimer
	beq .pspawn
	jmp .pdone
.pspawn
	jsr Rand
	and #7
	cmp #5
	bcc .p1
	sbc #5
.p1
	tax
	ldy #5
.p2
	lda houses
	and LaneBit,x
	bne .p3
	inx
	cpx #5
	bcc .p4
	ldx #0
.p4
	dey
	bne .p2
	lda #[30*FPSN/6]
	sta plTimer
	bne .pdone
.p3
	stx plLane
	lda #60
	sta plX
	lda #1
	sta plState
	bne .pdone
.pa
	ldx plLane
	lda houses
	and LaneBit,x
	bne .pb
	lda #0
	sta plState
	lda #[40*FPSN/6]
	sta plTimer
	bne .pdone
.pb
	lda plState
	cmp #1
	bne .ps
	lda plAcc
	clc
	adc #PLWALK
	sta plAcc
	bcc .pdone
	dec plX
	lda plX
	cmp #18
	bcs .pdone
	lda #2
	sta plState
	jsr SabTime
	jmp .pdone
.ps
	dec plTimer
	bne .pdone
	lda LaneBit,x
	eor #$FF
	and houses
	sta houses
	lda #2
	sta s0K
	lda #31
	sta s0T
	lda #0
	sta plState
	jsr PlRespawn
.pdone
	lda houses
	bne .alive
	lda #ST_OVER
	sta state
	lda #[120*FPSN/6]
	sta goTimer
	lda #0
	sta shotDir
	sta shotX
	sta plState
	ldx #4
.go1
	sta dX,x
	sta dE,x
	dex
	bpl .go1
	lda #1
	sta s1K
	lda #63
	sta s1T
	lda scoreH
	cmp hiH
	bcc .alive
	bne .sethi
	lda scoreL
	cmp hiL
	bcc .alive
.sethi
	lda scoreH
	sta hiH
	lda scoreL
	sta hiL
.alive
	rts

Sound
	SUBROUTINE
	lda paused
	beq .s0
	lda #0
	sta AUDV0
	sta AUDV1
	rts
.s0
	lda s0T
	beq .s0off
	dec s0T
	lda s0K
	bne .s0b
	lda #4
	sta AUDC0
	lda s0T
	clc
	adc #2
	sta AUDF0
	lda s0T
	sta AUDV0
	jmp .ch1
.s0b
	lda #8
	sta AUDC0
	lda s0K
	cmp #1
	bne .s0h
	lda #31
	sec
	sbc s0T
	sta AUDF0
	lda s0T
	lsr
	sta AUDV0
	jmp .ch1
.s0h
	lda #31
	sta AUDF0
	lda s0T
	lsr
	sta AUDV0
	jmp .ch1
.s0off
	lda #0
	sta AUDV0
.ch1
	lda s1T
	beq .s1idle
	dec s1T
	lda s1K
	bne .s1go
	lda #4
	sta AUDC1
	lda s1T
	sta AUDF1
	lda #10
	sta AUDV1
	rts
.s1go
	lda #12
	sta AUDC1
	lda s1T
	lsr
	eor #$1F
	sta AUDF1
	lda #8
	sta AUDV1
	rts
.s1idle
	lda state
	cmp #ST_PLAY
	bne .s1off
	lda plState
	beq .s1off
	cmp #2
	beq .warn
	lda frame
	and #31
	cmp #3
	bcs .s1off
	lda #1
	sta AUDC1
	lda #20
	sta AUDF1
	lda #4
	sta AUDV1
	rts
.warn
	lda frame
	and #8
	beq .s1off
	lda #12
	sta AUDC1
	lda #8
	sta AUDF1
	lda #8
	sta AUDV1
	rts
.s1off
	lda #0
	sta AUDV1
	rts

MakeScore
	SUBROUTINE
	lda temp
	lsr
	lsr
	lsr
	lsr
	tay
	lda Mul5,y
	sta ptr0
	lda temp
	and #$0F
	tay
	lda Mul5,y
	sta ptr1
	lda temp2
	lsr
	lsr
	lsr
	lsr
	tay
	lda Mul5,y
	sta pfptr
	lda temp2
	and #$0F
	tay
	lda Mul5,y
	sta pfptr+1
	ldy #0
.ms
	ldx ptr0
	lda DigHi,x
	ldx ptr1
	ora DigLo,x
	sta sg0,y
	ldx pfptr
	lda DigHi,x
	ldx pfptr+1
	ora DigLo,x
	sta sg1,y
	inc ptr0
	inc ptr1
	inc pfptr
	inc pfptr+1
	iny
	cpy #5
	bne .ms
	rts

Precompute
	SUBROUTINE
	lda #$FF
	ldx paused
	beq .pc0
	lda #$0F
.pc0
	sta colMask
	lda state
	bne .pcs
	lda hiH
	sta temp
	lda hiL
	sta temp2
	jmp .pcm
.pcs
	lda scoreH
	sta temp
	lda scoreL
	sta temp2
.pcm
	jsr MakeScore
	lda #>GfxPage
	sta ptr0+1
	sta ptr1+1
	sta pfptr+1
	lda #C_WHITE
	and colMask
	sta colSc
	lda #C_HOUSE
	and colMask
	sta colPF
	lda #C_FIELD
	ldx state
	cpx #ST_OVER
	bne .pc1
	ldx goTimer
	beq .pc1
	lda frame
	and #8
	beq .pc2
	lda #C_GOF
	bne .pc1
.pc2
	lda #C_FIELD
.pc1
	and colMask
	IF TV = 3
	ldx paused
	beq .pc3
	lda #0
.pc3
	ENDIF
	sta colBK
	lda state
	bne .lanes
	ldy startLevel
	lda Mul5,y
	sta temp
	rts
.lanes
	ldx #4
.lp
	lda #<GBlank
	sta lP0g,x
	lda #0
	sta lP0x,x
	sta lR0,x
	lda #C_STAR
	and colMask
	sta lC0,x
	cpx pLane
	bne .np
	lda plState
	beq .star
	cpx plLane
	bne .star
	lda frame
	lsr
	bcs .jar
.star
	lda #<GStar
	sta lP0g,x
	lda pX
	sta lP0x,x
	lda facing
	sta lR0,x
	jmp .p1
.np
	lda plState
	beq .p1
	cpx plLane
	bne .p1
.jar
	lda #<GJar
	sta lP0g,x
	lda plX
	sta lP0x,x
	lda #0
	sta lR0,x
	lda #C_JAR
	ldy plState
	cpy #2
	bne .jc
	lda frame
	and #4
	beq .jc0
	lda #C_JARF
	bne .jc
.jc0
	lda #C_JAR
.jc
	and colMask
	sta lC0,x
.p1
	lda dX,x
	bne .dol
	lda #<GBlank
	sta lP1g,x
	lda #0
	sta lP1x,x
	sta lC1,x
	jmp .ln
.dol
	sta lP1x,x
	lda dE,x
	beq .dd
	lda #<GBoom
	sta lP1g,x
	lda #C_BOOM
	bne .dc
.dd
	lda frame
	and #16
	beq .d2
	lda #<GDol1
	bne .d3
.d2
	lda #<GDol2
.d3
	sta lP1g,x
	lda #C_DOL
.dc
	and colMask
	sta lC1,x
.ln
	dex
	bmi .lpend
	jmp .lp
.lpend
	rts

	ALIGN 256
ScoreArea
	SUBROUTINE
	sta WSYNC
	lda #0
	sta COLUBK
	sta CTRLPF
	sta PF0
	sta PF1
	sta PF2
	sta GRP0
	sta GRP1
	sta REFP0
	sta REFP1
	sta ENAM0
	lda #5
	sta NUSIZ0
	sta NUSIZ1
	lda colSc
	sta COLUP0
	sta COLUP1
	sta WSYNC
	lda #56
	POSOBJ HMP0, RESP0
	sta WSYNC
	lda #72
	POSOBJ HMP1, RESP1
	sta WSYNC
	sta HMOVE
	ldy #0
.sa
	sta WSYNC
	lda sg0,y
	sta GRP0
	lda sg1,y
	sta GRP1
	sta WSYNC
	iny
	cpy #5
	bne .sa
	sta WSYNC
	lda #0
	sta GRP0
	sta GRP1
	ldy #15
.sb
	sta WSYNC
	dey
	bne .sb
	rts

GameKernel
	SUBROUTINE
	jsr ScoreArea
	sta WSYNC
	lda colBK
	sta COLUBK
	lda colPF
	sta COLUPF
	lda #$20
	sta NUSIZ0
	lda #0
	sta NUSIZ1
	ldx #0
.lane
	sta WSYNC
	lda lP0x,x
	POSOBJ HMP0, RESP0
	sta WSYNC
	lda lP1x,x
	POSOBJ HMP1, RESP1
	sta WSYNC
	lda shotX
	POSOBJ HMM0, RESM0
	sta WSYNC
	sta HMOVE
	lda lC0,x
	sta COLUP0
	lda lC1,x
	sta COLUP1
	lda lR0,x
	sta REFP0
	lda lP0g,x
	sta ptr0
	lda lP1g,x
	sta ptr1
	lda #0
	cpx shotLane
	bne .se
	lda shotDir
.se
	sta shotEn
	lda houses
	and LaneBit,x
	beq .nh
	lda #<GHouse
	bne .sh
.nh
	lda #<GBlank
.sh
	sta pfptr
	ldy #27
.dl
	sta WSYNC
	lda (pfptr),y
	sta PF0
	lda (ptr0),y
	sta GRP0
	lda (ptr1),y
	sta GRP1
	lda GMis,y
	and shotEn
	sta ENAM0
	lda #0
	sta PF0
	dey
	bpl .dl
	inx
	cpx #5
	beq .kend
	jmp .lane
.kend
	rts

TitleKernel
	SUBROUTINE
	jsr ScoreArea
	sta WSYNC
	lda #C_TBG
	sta COLUBK
	lda #1
	sta CTRLPF
	lda frame
	and #32
	beq .tc0
	lda #C_STAR2
	bne .tc
.tc0
	lda #C_STAR
.tc
	sta COLUPF
	ldy #16
.t1
	sta WSYNC
	dey
	bne .t1
	ldx #0
.tr
	ldy #7
.tl
	sta WSYNC
	lda StarPF,x
	sta PF2
	dey
	bne .tl
	inx
	cpx #14
	bne .tr
	sta WSYNC
	lda #0
	sta PF2
	ldy #13
.t2
	sta WSYNC
	dey
	bne .t2
	ldy #0
	ldx temp
.lv
	sta WSYNC
	lda LGlyph,y
	ora DigLo,x
	sta GRP0
	sta WSYNC
	inx
	iny
	cpy #5
	bne .lv
	sta WSYNC
	lda #0
	sta GRP0
	ldy #21
.t3
	sta WSYNC
	dey
	bne .t3
	rts

LaneBit
	.byte 1,2,4,8,16
Mul5
	.byte 0,5,10,15,20,25,30,35,40,45
SpeedTab
	IF HZ50 = 1
	.byte 36,36,49,62,76,89,102,115,128,142
	ELSE
	.byte 60,60,82,104,126,148,170,192,214,236
	ENDIF
SpawnBase
	.byte [100*FPSN/6],[100*FPSN/6],[90*FPSN/6],[80*FPSN/6],[70*FPSN/6],[60*FPSN/6],[50*FPSN/6],[40*FPSN/6],[30*FPSN/6],[20*FPSN/6]
PlBase
	.byte [128*FPSN/6],[128*FPSN/6],[120*FPSN/6],[110*FPSN/6],[100*FPSN/6],[90*FPSN/6],[80*FPSN/6],[70*FPSN/6],[60*FPSN/6],[50*FPSN/6]
SabTab
	.byte [200*FPSN/6],[200*FPSN/6],[192*FPSN/6],[184*FPSN/6],[176*FPSN/6],[168*FPSN/6],[160*FPSN/6],[152*FPSN/6],[144*FPSN/6],[136*FPSN/6]
StarPF
	.byte $80,$80,$C0,$C0,$FF,$FE,$F8,$F0,$F0,$78,$38,$1C,$0C,$02

	ALIGN 256
GfxPage
@@GFX@@
	echo "ROM free:", [$FFFC - *]d, "bytes"

	ORG $FFFC
	.word Reset
	.word Reset
