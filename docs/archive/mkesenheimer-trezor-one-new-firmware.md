<!DOCTYPE html>
<html lang="en">

<head>
    <base href="/mkesenheimer.github.io/" />
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#002241" />
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
    <link rel="manifest" href="/site.webmanifest" />
    <link rel="mask-icon" href="/safari-pinned-tab.svg" color="#002241" />
    <meta name="msapplication-TileColor" content="#ffffff" />
    <meta name="theme-color" content="#ffffff" />
    <link rel="stylesheet" media="all" href="/Resources/Static/Packages/matthias.kesenheimer/Styles/prism.css" />
    <link rel="stylesheet" media="all" href="/Resources/Static/Packages/matthias.kesenheimer/Styles/Main.min.css" />

    <script src="/Resources/Static/Packages/matthias.kesenheimer/JavaScript/jQuery.js"></script>
    <script src="/Resources/Static/Packages/matthias.kesenheimer/JavaScript/Plugins/anime.min.js" defer></script>
    <script src="/Resources/Static/Packages/matthias.kesenheimer/JavaScript/Plugins/prism.js" defer></script>
    <script src="/Resources/Static/Packages/matthias.kesenheimer/JavaScript/Plugins/chart.js" defer></script>
    <script src="/Resources/Static/Packages/matthias.kesenheimer/JavaScript/Main.js" defer></script>
    <title>Physik, Elektronik und mehr... | Blog</title>
    <meta name="robots" content="index,follow" />
</head>

<body class>
    <div id="wrapper">
        <div id="header">
            <div class="menu">
                <nav class="paddingTop30 paddingBottom15 kesenheimer-menu">
                    <menu-ul>
                        <li class=""><a href="/about-me.html">Über mich</a></li>
                        <li class="current"><a href="/">Blog</a></li>
                        <li class=""><a href="/blog/pico-glitcher-v3.html">Pico Glitcher</a></li>
                        <li class=""><a href="/contact.html">Kontakt</a></li>
                    </menu-ul>
                </nav>
            </div>
        </div>

        <section id="content">
            <div class="neos-contentcollection">
                <div class="paddingTop0 paddingBottom30 kesenheimer-container">
                    <div class="inner container-fluid">
                        <div class="neos-contentcollection">
                            <div class="paddingTop0 paddingBottom0 kesenheimer-headline">
                                <div>
                                    <h1 style="text-align: center">Attacking the Trezor One Crypto Wallet (new firmware)</h1>
                                </div>
                            </div>
                            <div class="paddingTop0 paddingBottom0 kesenheimer-text">
                                <div>
                                    <p style="text-align:center">Glitching firmware versions v1.6.1 and newer</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Block -->
                <div class="color-white paddingTop0 paddingBottom0 kesenheimer-container">
                    <div class="inner container-fluid">
                        <div class="neos-contentcollection">
                            <!-- Text -->
                            <div class="neos-nodetypes-html">
                                <div class="paddingTop30 paddingBottom15 kesenheimer-text">
                                    <div>
                                        <div class="paddingTop0 paddingBottom15 kesenheimer-warning">
                                            <div>
                                                <p>I am selling the PicoGlitcher on <a href="https://shop.faultyhardware.de">faultyhardware.de</a>.</p>
                                                
                                                <p>More links:</p>
                                                <ul>
                                                    <li>The Pico Glitcher and findus (the software to control the Pico Glitcher) are open source: <a href="https://github.com/MKesenheimer/fault-injection-library">fault-injection-library</a></li>
                                                    <li>Documentation of the Pico Glitcher and findus: <a href="https://fault-injection-library.readthedocs.io/en/latest/">fault-injection-library.readthedocs.io</a></li>
                                                    <li>hackaday.io project page: <a href="https://hackaday.io/project/196357-picoglitcher">hackaday.io/project/196357-picoglitcher</a></li>
                                                    <li>The Pico Glitcher was featured on Hackaday: <a href="https://hackaday.com/2024/10/30/use-picoglitcher-for-voltage-glitching-attacks/">hackaday.com/2024/10/30/use-picoglitcher-for-voltage-glitching-attacks/</a></li>
                                                </ul>
                                            </div>
                                        </div>

                                        <p>The Trezor One crypto wallet is one of the earliest and most popular hardware wallets for securely storing cryptocurrencies. It isolates private keys from internet-connected devices, providing strong protection against malware and remote attacks.</p>

                                        <p>Voltage glitching, which involves briefly tampering with the device's power supply to induce faults, can be necessary if the owner of the device has forgotten their PIN for unlocking the crypto wallet. By precisely timing these glitches, we can bypass security checks and extract sensitive data, such as the wallets passphrase.</p>

                                        <p>This article will explain how to attack the Trezor One crypto wallet with firmware versions v1.6.1 and newer, and how to get from read-out protection level 2 (RDP-2) to complete flash access. While <a href="https://blog.kraken.com/product/security/kraken-identifies-critical-flaw-in-trezor-hardware-wallets">a previous research from Kraken</a> showed that it is possible to get complete flash access to the device, the flash layout is different for devices with legacy firmware version v1.6.1.</p>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Prerequisites</h2>
                                            </div>
                                        </div>

                                        <p>The following tools and materials are needed for the attack:</p>

                                        <ul>
                                            <li>Pico Glitcher v2.1 or later</li>
                                            <li>ST-Link-V2 debug adapter</li>
                                            <li>An adjustable power supply (for example RD6006)</li>
                                            <li>Logic Analyzer (for example Dreamwave Logic Pro)</li>
                                            <li><a href="https://www.waveshare.com/stm32-qfp64.htm">QFP-64 STM32 adapter</a></li>
                                            <li>4.7kΩ resistors</li>
                                            <li>SMA cables and connectors</li>
                                            <li>Jumper cables</li>
                                            <li>Optional: a breadboard</li>
                                        </ul>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>STM32-QFP64 adapter</h2>
                                            </div>
                                        </div>

                                        <p>For this attack, the STM32-QFP64 adapter from Waveshare proved to be very helpful. This adapter can be used to quickly swap out different targets and to easily access different pins of the chip. It also supplies power to the chip and enables different boot configurations to be selected via the jumpers.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/01-stm32-qfp64-adapter.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>An SMA connector is soldered to the bottom of the board as shown below. This helps injecting the voltage glitches precisely and without much distortion. The SMA connector is held in place with a bit of glue.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/02-stm32-qfp64-adapter-back1.jpeg" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Schematics</h2>
                                            </div>
                                        </div>

                                        <p>The complete setup for this attack is shown in the following figure.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/04-stm32f205-glitching_bb.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>Additionally, the 'EXT TRIGGER' input of an oscilloscope is connected to the 'GLITCH_EN' output of the Pico Glitcher. We measure the voltage of the 'V_CAP' line ('MUX' output) on channel 1. The second channel of the oscilloscope can be used to measure either the 'RX' or 'TX' line.</p>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Images of the setup</h2>
                                            </div>
                                        </div>

                                        <p>The complete setup:</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/05-setup.jpg" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>ST-LINK v3 with 'SWD' and 'UART' connected:</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/06-setup.jpg" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>The '4.7kΩ' pull-up resistors on the 'TX' and 'RX' line:</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/07-setup.jpg" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>Connections to the STM23-QFP64 adapter:</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/08-setup.jpg" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>Pico Glitcher and external power supply connected to 'VIN1' (be sure to not exceed '1.2V'):</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/09-setup.jpg" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/10-setup.jpg" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Voltage traces</h2>
                                            </div>
                                        </div>

                                        <p>We can now verify the startup sequence of the STM32F205 by measuring the voltage traces during startup:</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/20-startup.bmp" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/21-vcap-power-trace.bmp" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>The level of the voltage supply should slowly rise in comparison to the voltage on the 'V_CAP' line. Furthermore, the voltage output on the 'VCAP' line is delayed approximately '150ms' after the device is powered on. Powering the device and measuring the voltage traces can be done with the command:</p>

                                        <div class="paddingTop0 paddingBottom15 kesenheimer-code">
                                            <pre class="line-numbers-rows">
                                                <code class="language-php">power-on --rpico /dev/pico-tty-device</code>
                                            </pre>
                                        </div>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Trigger condition</h2>
                                            </div>
                                        </div>

                                        <p>The trigger condition for stage 1 glitching (getting bootloader access) is measured on the 'EXT1' input. This input uses a configurable Schmitt trigger to generate a logical signal at a certain threshold. This threshold condition must be configured once and left untouched for the rest of the glitching campaign since changing it would also likely shift the 'delay' and 'length' parameters.</p>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Glitching</h2>
                                            </div>
                                        </div>

                                        <p>Now everything is set up, we can start glitching the device. For this, the script 'stm32f2-bootloader-memread-mux.py' has been prepared. This script powers up the device, waits for the trigger signal on input 'EXT1', waits a given delay and emits a glitch of a certain length. Afterwards, it is tested if the bootloader responds properly via UART. If yes, the first stage has been successfully glitched and a downgrade from RDP-2 to RDP-1 was performed. The script continues with glitching the second stage.</p>

                                        <p>In the second stage, the 'memread' command ('0x11ee') is sent to the device. The device checks if read-out protection is active. This check is glitched during the second stage of the script.</p>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Stage 2 glitching (RDP-1 to RDP-0)</h2>
                                            </div>
                                        </div>

                                        <p>The glitch to downgrade from RDP-1 to RDP-0 is positioned approximetely '105µs' after the read memory command ('readmem = 0x11ee') and before the device acknowledges the command. This is verified with an oscilloscope.</p>

                                        <p>The following figure shows the USB-UART transmit line (TX) and the voltage on 'V_CAP'. The glitch is emitted after the 'readmem' command ('0x11ee').</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/22-bootcom-readmemory-glitch.bmp" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>Next, the USB-UART receive line (RX) is shown. In this case, the device responds with two NACKs. The glitch is positioned before the device responds.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/23-bootcom-readmemory-glitch.bmp" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>In order to get an overview of the parameterspace, a scan over the full range was performed. Positive events were found around '105µs' after the 'readmem' command.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/30-stage-2-parameterspace.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>To optimize glitching and to be less invasive, the scan over the parameterspace was restricted in the next attempts. Good results were obtained with a delay in the range of '105.45µs' to '105.8µs' and a glitch length between '10ns' to '30ns'. A shorter glitch length proved to be better in this case as it seems to be less invasive. These parameters can be dependent on the Schmitt Trigger configuration, on the temperature or on the microcontroller itself. For best results, the parameters have to be tweaked for each target.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/31-stage-2-parameterspace.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/32-stage-2-parameterspace.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>The following command was used to glitch the 'readmem' command. The parameters '--delay' and '--length' are not necessary at this stage and are ignored.</p>

                                        <div class="paddingTop0 paddingBottom15 kesenheimer-code">
                                            <pre class="line-numbers-rows">
                                                <code class="language-php">python stm32f2-bootloader-memread-mux.py --rpico /dev/pico-tty-device --length 0 0 --delay 0 0 --target /dev/stm32-tty-device --delay2 105_450 105_800 --length2 10 30 --stage-2</code>
                                            </pre>
                                        </div>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Stage 1 glitching (RDP-2 to RDP-1)</h2>
                                            </div>
                                        </div>

                                        <p>Glitching to obtain bootloader access is similar to <a href="/blog/trezor-wallet-hack.html">Attacking the Trezor One Crypto Wallet (old firmware)</a>. However this time, the glitch is positioned '10µs' later, approximately '180µs' after the 'V_CAP' line rises.</p>

                                        <p>The following command is used to search a bigger portion of the parameterspace for successful glitches. The parameters should be optimized in a later step to optimize success rate. The parameters '--delay2' and '--length2' are not necessary at this stage and are ignored.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/24-stage-1-parameterspace.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Combining both attacks</h2>
                                            </div>
                                        </div>

                                        <p>The combined attack on a fully locked down target can be executed with the following command:</p>

                                        <div class="paddingTop0 paddingBottom15 kesenheimer-code">
                                            <pre class="line-numbers-rows">
                                                <code class="language-php">python stm32f2-bootloader-memread-mux.py --rpico /dev/pico-tty-device --length 110 130 --delay 188_900 189_500 --target /dev/stm32-tty-device --delay2 104_900 105_300 --length2 20 40</code>
                                            </pre>
                                        </div>

                                        <p>After a few attempts, the contents of the device's flash are displayed as the script's output.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/50-combined-success.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>We can analyze the parameterspace for successful events and optimize accordingly.</p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/10/images-flash-dump/51-combined-parameterspace.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Determining the address to read from</h2>
                                            </div>
                                        </div>

                                        <p>In most cases, it is unnecessary to download the entire contents of the device's flash memory, since we are only interested in the mnemonic passphrase or the PIN.</p>

                                        <p>By analyzing the <a href="https://github.com/trezor/trezor-firmware/tree/legacy/v1.6.1">firmware of the device</a>, the following memory offsets were found:</p>

                                        <div class="paddingTop0 paddingBottom15 kesenheimer-code">
                                            <pre class="line-numbers-rows">
                                                <code class="language-php">
FLASH_BOOT_START = 0x08000000
FLASH_BOOT_LEN = 0x8000
FLASH_META_DESC_LEN = 0x100
FLASH_META_START = FLASH_BOOT_START + FLASH_BOOT_LEN = 0x08008000
FLASH_STORAGE_START	= FLASH_META_START + FLASH_META_DESC_LEN = 0x08008100
STORAGE_ROM = FLASH_STORAGE_START + sizeof(storage_magic) + sizeof(storage_uuid) = 0x08008100 + 4 + 12 = 0x08008110
                                                </code>
                                            </pre>
                                        </div>

                                        <p>Therefore, the mnemonic passphrase should be around memory offset '0x08008190', and the PIN around '0x08008290'. Hence, we need to perform two memory reads with 256 Bytes each starting from '0x08008190' to extract all secrets. This can be achieved by the following command:</p>

                                        <div class="paddingTop0 paddingBottom15 kesenheimer-code">
                                            <pre class="line-numbers-rows">
                                                <code class="language-php">python stm32f2-bootloader-memread-mux.py --rpico /dev/pico-tty-device --length 100 150 --delay 195_000 198_000 --target /dev/stm32-tty-device --delay2 105_000 106_000 --length2 10 50 --address 0x08008190 --size 0x1fe
                                                </code>
                                            </pre>
                                        </div>

                                        <!--more links to other projects-->
                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Continue reading</h2>
                                            </div>
                                        </div>

                                        <p>Continue reading about the Pico Glitcher and its capabilities, or how to attack various microcontrollers, here:</p>

                                        <p><ul>
                                            <li><a href="https://mkesenheimer.github.io/blog/raspberry-pico-voltage-glitcher.html">The beginning of the Pico Glitcher</a></li>
                                            <li><a href="https://mkesenheimer.github.io/blog/pico-glitcher-v2.html">The Pico Glitcher v2</a></li>
                                            <li><a href="https://mkesenheimer.github.io/blog/pico-glitcher-v3.html">The Pico Glitcher v3</a></li>
                                            <li><a href="https://mkesenheimer.github.io/blog/esp32-glitching.html">Voltage multiplexing and parameter optimization</a></li>
                                            <li><a href="https://mkesenheimer.github.io/blog/glitching-the-stm32f4.html">Attacking the STM32F4 with the PicoGlitcher</a></li>
                                            <li><a href="https://mkesenheimer.github.io/blog/trezor-wallet-hack-v161.html">Attacking the Trezor One Crypto Wallet (new firmware)</a></li>
                                            <li><a href="https://mkesenheimer.github.io/blog/glitching-the-rp2350.html">Glitching the Raspberry Pico with a Raspberry Pico</a></li>
                                            <li><a href="https://blog.syss.com/posts/voltage-glitching-the-stm32l05-microcontroller/">Attacking the SMT32L051 with the Pico Glitcher</a></li>
                                            <li><a href="https://blog.syss.com/posts/nrf54-emfi/">Attacking the nRF54L15 with an Electromagnetic Fault Injection (EMFI) attack and the Pico Glitcher</a></li>
                                            <li><a href="https://blog.syss.com/posts/voltage-glitching-with-picoglitcher-and-findus/">Voltage Glitching with the Pico Glitcher and Findus</a></li>
                                            <li><a href="https://www.youtube.com/watch?v=3To4tyzmRsg">The Pico Glitcher on Youtube</a></li>
                                        </ul></p>
                                    </div>
                                </div>
                            </div>
                            <div class="row paddingTop0 paddingBottom30 neos-nodetypes-twocolumn">
                                <div class="col-lg-9 col-md-9 col-sm-9 col-xs-12 is-page neos-contentcollection"></div>
                                <div class="col-lg-3 col-md-3 col-sm-3 col-xs-12 is-page neos-contentcollection"></div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </section>

        <section id="footer">
            <div class="copy">
                <div class="inner">
                    <div class="neos-contentcollection">
                        <div class="paddingTop15 paddingBottom15 kesenheimer-text">
                            <div>
                                <p style="text-align:center">
                                    <a href="/impressum.html">Impressum</a>
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </div>
</body>
</html>
