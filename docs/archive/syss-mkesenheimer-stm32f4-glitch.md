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
                                    <h1 style="text-align: center">Attacking the STM32F4 with the PicoGlitcher</h1>
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

                                        <p>
                                            STMicroelectronics offers a wide range of STM32 microcontrollers, based on ARM Cortex-M cores, catering to various performance and power requirements. These microcontrollers are integral in applications across industrial automation, consumer electronics, automotive systems, and IoT devices, providing efficient processing, connectivity, and real-time control. Since they are widely used, these microcontrollers are a interesting target for hardware attacks.
                                        </p>

                                        <p>
                                            A processor from the ST32F4 series was chosen as the target, specifically the STM Black Pill board with the STM32F401 microcontroller which is based on the Arm® Cortex®-M4 architecture. The Black Pill board contains all necessary components for operation.
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/Black_pill_pinout.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>
                                            STM32 processors utilize a readout protection (RDP) that is divided into three stages. RDP level 1 (RDP-1) is the first level that restricts access to the microcontroller. With RDP-0 selected, no protection is active, i.e. the flash content of the microcontroller can be read out and the debug functions can be accessed. With RDP-1, the readout protection is active for the program flash, but the RAM of the microcontroller can still be accessed for debugging purposes. With RDP-2 selected, the microcontroller is completely closed. It is possible to switch from RDP-1 to RDP-0, but the program flash will be deleted. Switching from RDP-2 to RDP-1 is not supported by the microcontroller. The level of the readout protection can, for example, be set or read via the <a href="https://www.st.com/en/development-tools/stm32cubeprog.html">STM32CubeProgrammer</a>.
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/rdp1.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>
                                            Due to the special values of the option bytes and the fact that the register values are redundant, a glitching attack is correspondingly unlikely. Switching from RDP-2 to RDP-1 is more likely, as only one bit (and the complementary bit in the redundant register) needs to be changed to activate RDP-1. The change from RDP-1 to RDP-0 is very unlikely since exactly the value 0xAA and the value 0x55 in the complementary register must be hit.
                                        </p>

                                        <p>
                                            The glitch is inserted at one of the voltage regulator capacitors ('VCAP' pin). In order to achieve good results, the capacitor have to be removed from the board.
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/power_supply_scheme.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>
                                            The following setup was selected to glitch the microcontroller.
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/stm32f40-glitching_bb.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>
                                            The colors of the connections encode these signals:
                                        </p>
                                        <ul>
                                            <li>red: Voltage supply of the Black Pill board (5V)</li>
                                            <li>purple: 1.8V voltage supply to the 'VCAP' pin decoupled with a 10 Ohms resistor and glitch input. The 1.8V voltage supply via the resistor is needed to get a stable voltage on the 'VCAP' pin.</li>
                                            <li>yellow: TX line to the STM32 microcontroller.</li>
                                            <li>orange. RX line to the STM32 microcontroller.</li>
                                            <li>also yellow: Trigger line, connected to the TX line to the STM32 microcontroller. If 0x11 (memory read command) is transmitted, the trigger is set.</li>
                                            <li>geen: Reset line to reset the microcontroller.</li>
                                        </ul>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/setup.JPG" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>
                                            Additionally, an oscilloscope is connected to the TX line and the 'VCAP' pin (glitch line).
                                        </p>

                                        <p>
                                            A simple test program was flashed onto the microcontroller. The sole purpose of this programme was to demonstrate a successful glitch.
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/programmed_flash.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>
                                            The bootloader of the STM32 processors offers a specific option for reading out the program flash. The bootloader mode is activated when the 'BOOT0' pin is connected to VCC. This can be done by pressing the 'BOOT0' switch on the Black Pill board, or by shorting the 'BOOT0' pin to VCC.
                                        </p>

                                        <p>
                                            To read the program memory, a series of commands must be sent to the processor in bootloader mode via UART, which instruct the processor to return parts of the flash memory (see <a href="https://www.st.com/resource/en/application_note/an3155-usart-protocol-used-in-the-stm32-bootloader-stmicroelectronics.pdf">STMicroelectronics: USART protocol used in the STM32 bootloader</a>). Among other things, the 'read memory' command is sent to the processor via UART, i.e. the byte 0x11. The glitcher is configured in such a way that it triggers as soon as byte 0x11 is recognized on the TX line. As the transmission of a  second checksum byte requires additional 80µs, the interesting range begins at a 'delay' of 80,000ns and ends as soon as the bootloader sends the acknowledgement approximately 20-40µs later. In practice, it turns out that a range from 95,000ns to 125,000ns must be scanned. The duration of the glitch is selected just short enough so that the microcontroller is not reset ('brown-out') and long enough so that the glitch also has an effect. A 'length' of 25 to 35ns turns out to be good.
                                        </p>

                                        <p>
                                            The script to perform the glitch can be found in the <a href="https://github.com/MKesenheimer/fault-injection-library/blob/master/projects/stm32f40x/stm32f4-glitching.py">fault-injection-library</a> and is typically run with the command:
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-code">
                                            <pre class="line-numbers-rows">
                                                <code class="language-php">python stm32f4-glitching.py --target /dev/tty.usbserial-A50285BI --rpico /dev/tty.usbmodem11101 --power /dev/tty.usbserial-10 --delay 95_000 125_000 --length 25 35</code>
                                            </pre>
                                        </div>

                                        <p>
                                            In the following figure, the glitch is barely visible after the bytes 0x11 and 0xee are sent via UART.
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/osci.bmp" width="1500" height="1125" />
                                            </figure>
                                        </div>

                                        <p>
                                            A successful glitching campaign can be seen in the following figure. Successful glitches were found around the parameter point (104,000ns, 33ns), for example.
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/parameterspace-attempt-2.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>
                                            A status message is printed with the memory content if a successful glitch was found.
                                        </p>

                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2024/12/successful-dump.png" width="3264" height="2448" />
                                            </figure>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="row paddingTop0 paddingBottom0 neos-nodetypes-twocolumn">
                                <div class="col-lg-9 col-md-9 col-sm-9 col-xs-12 is-page neos-contentcollection"></div>
                                <div class="col-lg-3 col-md-3 col-sm-3 col-xs-12 is-page neos-contentcollection"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Block -->
                <div class="color-white paddingTop30 paddingBottom0 kesenheimer-container">
                    <div class="inner container-fluid">
                        <div class="neos-contentcollection">
                            <!-- Text -->
                            <div class="neos-nodetypes-html">
                                <div class="paddingTop0 paddingBottom15 kesenheimer-text">
                                    <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                        <div>
                                            <h2>Things that can and will go wrong</h2>
                                        </div>
                                    </div>

                                    <p>
                                        <em>Problem 1: Flash is sometimes completely erased</em>
                                    </p>

                                    <p>
                                        In addition to the memory read command, the bootloader also offers the memory erase command. If this function is accidentally triggered by a glitch, the entire flash content of the microcontroller is erased. This can happen up to once every 100,000 attempts. Interesting data (such as the firmware) is of course lost in that case.
                                    </p>

                                    <p>
                                        <em>Problem 2: PCROP protection</em>
                                    </p>

                                    <p>
                                        It can also happen that the SPRMOD bit is set in the event of a glitch. This bit causes the bytes returned by the bootloader when reading the flash contents to be masked with 0x00. This means that the bootloader is in the correct path of the read memory routine due to the glitch, but any response from the bootloader will be replaced with a zero by a downstream instance in the microcontroller.
                                    </p>

                                    <p>
                                        If the PCROP bit is set by mistake, the glitching process must be aborted and the entire flash reprogrammed. Interesting data (e.g. firmware) will be lost.
                                    </p>

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
