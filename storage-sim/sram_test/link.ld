MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
}
_estack = 0x20010000;
SECTIONS
{
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
  .text       : { *(.text*) *(.rodata*) } > FLASH
  .bss        : { *(.bss*) *(COMMON) } > RAM
  /DISCARD/   : { *(.ARM.*) *(.comment) }
}
