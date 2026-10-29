# Trezor One v1.6.1 and later glitching (flash dump attack)

This summary will explain how to attack the Trezor One with firmware 1.6.1 and later. It will go into detail how to get from RDP level 2 to RDP level 0 and dump the content of the flash.
For this attack the from Waveshare proved to be very helpful.

![](images-flash-dump/01-stm32-qfp64-adapter.png)

## Prerequisites

- Pico Glitcher v2.1 or later
- ST-Link-V2 debug adapter
- adjustable power supply (for example RD6006)
- Logic Analyzer (for example Dreamwave Logic Pro)
- [QFP-64 STM32 adapter](https://www.waveshare.com/stm32-qfp64.htm)
- 4.7kΩ resistors
- SMA cables and connectors
- jumper cables
- optional: breadboard

## Setup

### Preparation of the STM32-QFP64 adapter

Solder a SMA connector to the bottom of the board as shown below. This helps injecting the voltage glitches precisely and without much distortion.

![](images-flash-dump/02-stm32-qfp64-adapter-back1.jpeg)

Secure the SMA connector with a bit of glue.

### Schematics

The complete setup is shown in the following figure.

![](images-flash-dump/04-stm32f205-glitching_bb.png)

Additionally, connect the `EXT TRIGGER` input of an oscilloscope to the `GLITCH_EN` output of the Pico Glitcher. Measure the voltage of the `V_CAP` line (`MUX` output) on channel 1. The second channel of the oscilloscope can be used to measure either the `RX` or `TX` line.

### Images of the setup

Complete setup:

![](images-flash-dump/05-setup.jpg)

ST-LINK v3 with `SWD` and `UART` connected:

![](images-flash-dump/06-setup.jpg)

The `4.7kΩ` pull-up resistors on the `TX` and `RX` line:

![](images-flash-dump/07-setup.jpg)

Connections to the STM23-QFP64 adapter:

![](images-flash-dump/08-setup.jpg)

Pico Glitcher and external power supply connected to `VIN1` (be sure to not exceed `1.2V`; double-check polarity):

![](images-flash-dump/09-setup.jpg)
![](images-flash-dump/10-setup.jpg)

## Voltage traces

Verify the startup sequence of the STM32F205 by measuring the voltage traces during startup:

![](images-flash-dump/20-startup.bmp)

The level of the voltage supply should slowly rise in comparison to the voltage on the `V_CAP` line. Furthermore, the voltage output on the `VCAP` line is delayed approximately `150ms` after the device is powered on. Powering the device and measuring the voltage traces can be done with the command:

```bash
power-on --rpico /dev/<tty-device>
```

## Trigger condition

The trigger condition for stage 1 glitching (getting bootloader access) is measured on the `EXT1` input. This input uses a configurable Schmitt trigger to generate a logical signal at a certain threshold. This threshold condition must be configured once and left untouched for the rest of the glitching campaign since changing it would also likely shift the `delay` and `length` parameters.

Start by turning the third and fourth potentiometers from the left (`THR` and `ATN`) fully clockwise.

Then execute the following command to periodically generate a trigger condition:

```bash
python stm32f2-bootloader-memread-mux.py --rpico /dev/tty.usbmodem1401 --length 0 0 --delay 0 0 --target /dev/tty.usbmodem1103 --delay2 0 0 --length2 0 0 --stage-1 --no-store
```

Turn back the potentiometer lebeled `THR` (turn in counter-clockwise) until the output of the script changes from `b'warning: timout'` to  `b'error: bootloader error'`.

The threshold levels are now configured correctly. Do not change the configuration for the rest of the experiments.


## Glitching

Now everything is set up, we can start glitching our device. For this, the script `stm32f2-bootloader-memread-mux.py` has been prepared. This script powers up the device, waits for the trigger signal on input `EXT1`, waits a given delay and emits a glitch of a certain length. Afterwards, it is tested if the bootloader responds properly via UART. If yes, the first stage has been successfully glitched and a downgrade from RDP-2 to RDP-1 was performed. The script continues with glitching the second stage.

In the second stage, the `memread` command (`0x11ee`) is sent to the device. The device checks if read-out protection is active. This check is glitched during the second stage of the script.

To test the setup and to tune the parameters of each attack, first execute glitching on each stage separately on a test device. Start with the second stage as this requires a device with RDP level 1 activated. If stage 2 glitching works, continue with stage 1 glitching. In this stage, a test device with RDP level 2 is necessary, which can not be deactivated anymore.

If everything works and if you have collected enough experience, only then continue with the combined attack on the real target.

### Stage 2 glitching (RDP-1 to RDP-0)

Prepare a test microcontroller with a sample program. It does not matter which program is flashed as this program will not be executed. However, it is necessary to not have a blank target to check if the attack works. Do not activate RDP yet. Execute the following command and check, if the device responds to bootloader commands via UART:

```bash
stm32-power-cycle-and-read --rpico /dev/tty.usbmodem1401 --target /dev/tty.usbmodem1103
```

If this command yields the memory content of the device, activate RDP level 1 and continue. With this configuration the device should respond to bootloader commands but not respond to the read memory command.

The glitch to downgrade from RDP-1 to RDP-0 is positioned approximetely `105µs` after the read memory command (`readmem = 0x11ee`) and before the device acknowledges the command. This should be verified with an oscilloscope.

The following figure shows the USB-UART transmit line (TX) and the voltage on `V_CAP`. The glitch is emitted after the `readmem` command (`0x11ee`).
![](images-flash-dump/22-bootcom-readmemory-glitch.bmp)

Next, the USB-UART receive line (RX) is shown. In this case, the device responds with two NACKs. The glitch is positioned before the device responds.
![](images-flash-dump/23-bootcom-readmemory-glitch.bmp)

In order to get an overview of the parameterspace, a scan over the full range was performed. Positive events were found around `105µs` after the `readmem` command.
![](images-flash-dump/30-stage-2-parameterspace.png)

To optimize glitching and to be less invasive, the scan over the parameterspace was restricted in the next attempts. Good results were obtained with a delay in the range of `105.45µs` to `105.8µs` and a glitch length between `10ns` to `30ns`. A shorter glitch length proved to be better in this case as it seems to be less invasive. These parameters can be dependent on the Schmitt Trigger configuration (see [Trigger condition](#trigger-condition)), on the temperature or on the microcontroller itself. For best results, the parameters have to be tweaked for each target.

![](images-flash-dump/31-stage-2-parameterspace.png)
![](images-flash-dump/32-stage-2-parameterspace.png)

Use the following command to glitch the `readmem` command. The parameters `--delay` and `--length` are not necessary at this stage and are ignored.

```bash
python stm32f2-bootloader-memread-mux.py --rpico /dev/tty.usbmodem1401 --length 0 0 --delay 0 0 --target /dev/tty.usbmodem1103 --delay2 105_450 105_800 --length2 10 30 --stage-2
```

Use the flags `--resume` to continue a previous glitching campaign, or `--no-store` to not store the current experiments to the database. This could be used for testing purposes, for example.

The following figure shows a successful glitch of a `readmem` command with the target returning valid data:

![](images-flash-dump/40-stage-2-success.png)

### Stage 1 glitching (RDP-2 to RDP-1)

If stage 2 glitching was successful, increase the RDP level once more to level 2. In this configuration, the device should not respond to bootloader commands anymore and it should be completely locked down. RDP level 2 can not be downgraded, so be sure you checked everything before you continue.

Glitching to obtain bootloader access is similar to [Trezor One v1.6.0 glitching](README.md). However this time, the glitch is positioned `10µs` later, approximately `180µs` after the `V_CAP` line rises.

The following command is used to search a bigger portion of the parameterspace for successful glitches. The parameters should be optimized in a later step to optimize success rate. The parameters `--delay2` and `--length2` are not necessary at this stage and are ignored.

```bash
python stm32f2-bootloader-memread-mux.py --rpico /dev/tty.usbmodem1401 --length 110 130 --delay 188_900 189_500 --target /dev/tty.usbmodem1103 --delay2 105_450 105_800 --length2 10 30 --stage-1
```

![](images-flash-dump/24-stage-1-parameterspace.png)

### Combined attack

The combined attack on a fully locked down target can be executed with the following command:

```bash
python stm32f2-bootloader-memread-mux.py --rpico /dev/tty.usbmodem1401 --length 110 130 --delay 188_900 189_500 --target /dev/tty.usbmodem1103 --delay2 104_900 105_300 --length2 20 40
```

![](images-flash-dump/50-combined-success.png)
![](images-flash-dump/51-combined-parameterspace.png)

### Found parameters

| target | delay / length range          | delay2 / length2 range      |
|--------|-------------------------------|-----------------------------|
| t1     | 192.140 - 192.300 / 100 - 150 |                             |
| t2     | 191.750 - 192.080 / 100 - 150 | 105.000 - 106.000 / 10 - 50 |
| t3     | 193.040 - 193.740 / 100 - 150 |                             |
| t4     | 196.570 - 197.160 / 100 - 150 |                             |

## Recover the mnemonic passphrase and pin from Trezor with firmware version 1.61

According to the calculation from `storage/Notes.org`, the mnemonic passphrase starts around address 0x08008190 and pin at address 0x08008290.
Hence, we need to perform two memory reads with 256 Bytes each starting from 0x08008190 to extract all secrets.
