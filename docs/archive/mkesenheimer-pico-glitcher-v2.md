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
                                    <h1 style="text-align: center">Pico Glitcher v2</h1>
                                </div>
                            </div>
                            <div class="paddingTop0 paddingBottom0 kesenheimer-text">
                                <div>
                                    <p style="text-align:center">A device to perform fault-injection attacks</p>
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
                                                <p>If you have feature requests or issues, please contact me:</p>
                                                <ul>
                                                    <li>twitter: <a href="https://x.com/BartimaeusvUruk">@BartimaeusvUruk</a></li>
                                                    <li>mastodon: <a href="https://mastodon.social/@mkesenheimer">@mkesenheimer@mastodon.social</a></li>
                                                    <li>discord: <a href="https://discord.gg/8mqEVPG6k7">https://discord.gg/8mqEVPG6k7</a></li>
                                                </ul>
                                            </div>
                                        </div>

                                        <p>Compared to hardware <a href="https://fault-injection-library.readthedocs.io/en/latest/overview/#what-is-the-pico-glitcher-v1">revision 1</a>, several new features have been added in revision 2. However, the basic usage is the same and the scripts for version 1 will also (likely) work for version 2.</p>
                                        
                                        <!-- front image -->
                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/01/front.jpg" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>The hardware is based on the Raspberry Pi Pico, two high-power MOSFETs for crowbar glitch generation, and two level shifters to ensure compatibility over a wide voltage range. A newly designed input stage (EXT1 and EXT2) can be used to filter out noise and other disturbances via adjustable Schmitt Triggers. The multiplexing output can be used to quickly switch between up to four different voltage levels and to supply the target board with power.</p>

                                        <p>The second revision of the Pico Glitcher can also be modified to suit your needs. The Pico Glitcher v2 is built from the following components:</p>

                                        <!-- components -->
                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/01/pico-glitcher-v2.1-components.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>If you want to write code for additional communication protocols, such as a UART-to-USB adapter, or an SPI-to-USB adapter, then the unused GPIO pins are perfect for that. Pins GPIO16 - GPIO19 are connected to the Raspberry Pi Pico without a level shifter and can be used bi-directionally. The output pins with level-shifting are GPIO4 - GPIO9. For inputs with level shifter the pins GPIO15, GPIO20 and GPIO21 can be used.</p>

                                        <!-- section multiplexing -->
                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Multiplexing</h2>
                                            </div>
                                        </div>

                                        <p>Multiplexing is a technique to quickly switch between different supply voltage levels of the microcontroller. Similar to glitching with the <a href="https://fault-injection-library.readthedocs.io/en/latest/glitches/">crowbar technique</a>, this can cause a fault in the microcontroller. A fundamental difference is that with the multiplexing-fault-injection method, the supply voltage of the microcontroller is not pulled to GND, but intermediate voltages can also be used, for example 1.8V or user-defined voltages. It is also possible to go through a sequence of different supply voltages, so called voltage profiles.</p>

                                        <p>With the second hardware revision of the Pico Glitcher, it is possible to create different voltage profiles and apply them to the supply voltage of the target. This is made possible by the introduction of the multiplexing stage. The multiplexing stage also allows the target to be supplied with power. It is therefore not necessary to additionally supply the target with voltage via the 'VTARGET' output.</p>

                                        <p>The following setup can be used to test the multiplexing stage of the Pico Glitcher v2:</p>

                                        <!-- Multiplexing test setup -->
                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/01/multiplexing-test-setup.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>Note that the power supply is optional and can be used to generate a third, intermediate voltage. Without the additional power supply, the multiplexing stage of the Pico Glitcher can switch between 3.3V, 1.8V and 0V. See <a href="https://github.com/MKesenheimer/fault-injection-library/blob/master/example/pico-glitcher.py">fault-injection-library/example/pico-glitcher.py</a> for a complete test script and <a href="https://fault-injection-library.readthedocs.io/en/latest/multiplexing/#using-the-multiplexing-stage">fault-injection-library.readthedocs.io</a> for a detailed overview on how to setup and use the multiplexing stage.</p>

                                        <p>The software for controlling the multiplexing stage is extremely flexible and a vast number of voltage profiles with countless parameterizations can be generated. Up to four different voltage steps can be parametrized and utilized with the general multiplexing configuration similar to</p>

                                        <div class="paddingTop0 paddingBottom0 kesenheimer-code">
                                            <pre class="line-numbers-rows">
                                                <code class="language-php">mul_config = {"t1": t1, "v1": "GND", "t2": t2, "v2": "1.8", "t3": t3, "v3": "VCC", "t4": t4, "v4": "3.3"}</code>
                                            </pre>
                                        </div>

                                        <p>where VCC is a user-supplied voltage level by the VIN input. Below are some examples of voltage traces that can be applied to the target.</p>

                                        <p><ul>
                                            <li>1.8V voltage step, custom voltage of 0.95V, followed by a pull to GND:</li>
                                        </ul></p>

                                        <!-- Multiplexing annotated voltage trace -->
                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/01/ps_1000ns_annotated.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p><ul>
                                            <li>The same pulse, but a factor 10 shorter:</li>
                                        </ul></p>

                                        <!-- Multiplexing 100ns pulse -->
                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/01/ps.bmp" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p><ul>
                                            <li>Double glitch (both to GND), separated by 400ns:</li>
                                        </ul></p>

                                        <!-- Multiplexing double glitch -->
                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/01/double-crowbar-glitch.bmp" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>In order to switch quickly between different voltage levels, the chip 'TS3A4751' from Texas Instruments is used. This chip is a 4-channel analog switch in SPST (single-pull-single-through) configuration. To make the analog switch easier to control and to reduce the signal lines from the Raspberry Pi Pico to the analog switch, a digital demultiplexer is used ('SN74LVC1G139DCUT'). Since the voltage levels are reversed after the demultiplexer, a 4-channel not-gate is used to reverse the voltage levels.</p>

                                        <!-- Multiplexing schematics -->
                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/01/multiplexing-schematics.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>This setup seems rather complicated to switch between four different voltage levels. However, the choice of analogue switches is not exactly extensive or does not match the requirements of a fast-switching fault-injection device. The required properties of the analogue switch are as follows:</p>

                                        <p><ul>
                                            <li>Fast switching: less than 5ns switching time.</li>
                                            <li>Number of channels: four channels for flexible switching between as many voltage levels as possible.</li>
                                            <li>Low resistance: to avoid switching losses, a low resistance of 1Ω or less is required.</li>
                                            <li>High output current: a high continuous current of at least 100mA is needed to keep the device powered even for a long time. This maximum current should be suitable for most microcontrollers.</li>
                                        </ul></p>

                                        <p>All these requirements are met by the 'TS3A4751', even if the choice of this chip has made controlling it a little more complicated.</p>

                                        <!-- Section Schmitt Trigger inputs-->
                                        <div class="paddingTop15 paddingBottom15 kesenheimer-headline">
                                            <div>
                                                <h2>Schmitt Trigger inputs</h2>
                                            </div>
                                        </div>

                                        <p>The trigger inputs EXT1 and EXT2 are particularly useful for noisy logic signals, as the noise can be easily suppressed by the adjustable Schmitt Trigger. If, for example, the signal oscillates or is disturbed in any other way, this disturbances can be cut off by selecting a suitable threshold.</p>

                                        <!-- Schmitt Trigger schematic -->
                                        <div class="paddingTop0 paddingBottom30 kesenheimer-image">
                                            <figure>
                                                <img title="" alt="" src="/Resources/Persistent/2025/01/schmitt-trigger-input-test.png" width="3264" height="2448" />
                                            </figure>
                                        </div>

                                        <p>Use the potentiometer labeled THR to adjust the threshold of the Schmitt Trigger. The threshold is lowered by turning the potentiometer to the left.</p>

                                        <p>The potentiometer ATN can be used for an additionally signal reduction, if necessary. Turning the potentiometer all the way to the right disables attenuation and uses the full signal range.</p>

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
