#include <stdint.h>
#define N 32
/* .bss static in SRAM - mimics storage.c hardware_salt[32] */
volatile uint8_t fake_salt[N] __attribute__((used));
/* recognizable sentinel 0xA0..0xBF (no leftover SRAM looks like this) */
static const uint8_t pat[N] = {
  0xA0,0xA1,0xA2,0xA3,0xA4,0xA5,0xA6,0xA7,0xA8,0xA9,0xAA,0xAB,0xAC,0xAD,0xAE,0xAF,
  0xB0,0xB1,0xB2,0xB3,0xB4,0xB5,0xB6,0xB7,0xB8,0xB9,0xBA,0xBB,0xBC,0xBD,0xBE,0xBF
};
void Reset_Handler(void){
  for (int i=0;i<N;i++) fake_salt[i]=pat[i];   /* runtime write into .bss, like the real salt */
  for (;;){}                                   /* keep running, salt resident in SRAM */
}
extern uint32_t _estack;
__attribute__((section(".isr_vector"),used))
const uint32_t vtab[2] = { (uint32_t)&_estack, (uint32_t)Reset_Handler };
