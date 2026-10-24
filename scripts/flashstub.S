@ SRAM stub v6: fault-tolerant flash copy.
@ - NO cpsid: faults must VECTOR (PRIMASK makes BusFault pend forever)
@ - full vector table: all faults+IRQs -> recover (privileged handler):
@   records fault count, disables MPU, clears CFSR sticky, bx lr (retry insn)
@ - probes: BootROM / TrezBL / firmware / storage, then the full copy
    .syntax unified
    .cpu cortex-m3
    .thumb
    .org 0
    .word 0x20020000          @ 0x00 MSP
    .word start+1             @ 0x04 Reset
    .rept 78                  @ 0x08.. : NMI..SysTick + IRQ0..63 -> recover
    .word recover+1
    .endr
start:
    ldr  r0, =0xE000ED08      @ VTOR -> our table
    ldr  r1, =0x20000000
    str  r1, [r0]
    ldr  r0, =0xE000ED24      @ SHCSR: MemManage/BusFault/UsageFault vectors on
    ldr  r1, =0x00070000
    str  r1, [r0]
    movs r0, #1
    ldr  r1, =0x20001010
    str  r0, [r1]             @ step 1: setup done
    ldr  r0, =0x1FFF0004      @ probe A: BootROM
    ldr  r3, [r0]
    str  r3, [r1, #-252]      @ 0x20001014
    movs r0, #2
    str  r0, [r1]
    ldr  r0, =0x08000004      @ probe B: Trezor bootloader
    ldr  r3, [r0]
    str  r3, [r1, #-248]      @ 0x20001018
    movs r0, #3
    str  r0, [r1]
    ldr  r0, =0x08010004      @ probe C: firmware
    ldr  r3, [r0]
    str  r3, [r1, #-244]      @ 0x2000101C
    movs r0, #4
    str  r0, [r1]
    ldr  r0, =0x08008000      @ probe D: storage
    ldr  r3, [r0]
    str  r3, [r1, #-8]        @ 0x20001008
    movs r0, #5
    str  r0, [r1]
    ldr  r0, =0x08008000      @ copy storage 32K
    ldr  r1, =0x20010000
    ldr  r2, =0x08010000
1:  ldr  r3, [r0], #4
    str  r3, [r1], #4
    cmp  r0, r2
    bne  1b
    movs r0, #6
    ldr  r1, =0x20001010
    str  r0, [r1]
    ldr  r0, =0x08010000      @ copy firmware header 64B
    ldr  r1, =0x20018000
    ldr  r2, =0x08010040
2:  ldr  r3, [r0], #4
    str  r3, [r1], #4
    cmp  r0, r2
    bne  2b
    movs r0, #7
    ldr  r1, =0x20001010
    str  r0, [r1]
    ldr  r0, =0xCAFEBABE
    ldr  r1, =0x20001000
    str  r0, [r1]
3:  wfi
    b    3b
@ ---- fault / IRQ recovery handler (privileged) ----
recover:
    ldr  r0, =0x20001024      @ fault counter++
    ldr  r3, [r0]
    adds r3, #1
    str  r3, [r0]
    ldr  r0, =0xE000ED38      @ capture BFAR once
    ldr  r3, [r0]
    ldr  r1, =0x2000100C
    str  r3, [r1]
    ldr  r0, =0xE000ED28      @ capture CFSR once
    ldr  r3, [r0]
    ldr  r1, =0x20001020
    str  r3, [r1]
    ldr  r0, =0xE000ED94      @ MPU_CTRL = 0 (privileged: disable MPU)
    movs r1, #0
    str  r1, [r0]
    ldr  r0, =0xE000ED28      @ clear CFSR sticky bits
    ldr  r1, =0xFFFFFFFF
    str  r1, [r0]
    bx   lr                   @ return: faulting insn retries, MPU now off
