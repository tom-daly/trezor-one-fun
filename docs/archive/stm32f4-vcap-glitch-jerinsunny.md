<!DOCTYPE html>
<html lang=" en-US">

<head>
  <meta charset='utf-8'>
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="/stm32_vglitch/assets/css/style.css?v=76803afb658efe7288531be03d0c76e477ef8fd2">
  <title>Voltage glitching on STM32F4 MCUs</title>
  <!-- start custom head snippets, customize with your own _includes/head-custom.html file -->

<!-- Setup theme-color -->
<!-- start theme color meta headers -->
<meta name="theme-color" content="#151515">
<meta name="msapplication-navbutton-color" content="#151515">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="image" property="og:image" content="https://jerinsunny.github.io/stm32_vglitch/assets/images/banner.jpg"/>
<!-- end theme color meta headers -->


<!-- Setup Google Analytics -->

  <script>
    (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
    (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
            m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
        })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
    ga('create', 'G-DW62RVHCXG', 'auto');
    ga('send', 'pageview');
  </script>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-DW62RVHCXG"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-DW62RVHCXG');
</script>



<!-- You can set your favicon here -->
<!-- link rel="shortcut icon" type="image/x-icon" href="/stm32_vglitch/favicon.ico" -->

<!-- end custom head snippets -->


  <!-- Begin Jekyll SEO tag v2.8.0 -->
<title>Overview | Voltage glitching on STM32F4 MCUs</title>
<meta name="generator" content="Jekyll v3.10.0" />
<meta property="og:title" content="Overview" />
<meta name="author" content="Jerin Sunny" />
<meta property="og:locale" content="en_US" />
<meta name="description" content="Bypassing Read Protection to extract firmware from STM32 Microcontrollers." />
<meta property="og:description" content="Bypassing Read Protection to extract firmware from STM32 Microcontrollers." />
<link rel="canonical" href="https://jerinsunny.github.io/stm32_vglitch/" />
<meta property="og:url" content="https://jerinsunny.github.io/stm32_vglitch/" />
<meta property="og:site_name" content="Voltage glitching on STM32F4 MCUs" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary" />
<meta property="twitter:title" content="Overview" />
<meta name="twitter:site" content="@" />
<meta name="twitter:creator" content="@Jerin Sunny" />
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebSite","author":{"@type":"Person","name":"Jerin Sunny"},"description":"Bypassing Read Protection to extract firmware from STM32 Microcontrollers.","headline":"Overview","name":"Voltage glitching on STM32F4 MCUs","url":"https://jerinsunny.github.io/stm32_vglitch/"}</script>
<!-- End Jekyll SEO tag -->

</head>

<body>

  <header>
    <div class="container">
      <a id="a-title" href="/stm32_vglitch/">
        <h1>Voltage glitching on STM32F4 MCUs</h1>
      </a>
      <small>10 April 2024</small>
      <h2>Bypassing Read Protection to extract firmware from STM32 Microcontrollers.</h2>
      <!-- <p class="view"> 10 April 2024 </p> -->
      <div style="display: flex; gap: 2rem;">
        <div style="display: flex; flex-direction: row; flex-grow: inherit;  align-items: center;">
          <a href="https://www.linkedin.com/in/jerin-sunny/" target="_blank">
          <img src="https://avatars.githubusercontent.com/u/166545686" height="50px" width="50px" style="border-radius: 50%; margin: 0.25rem;"> </a>
          <p class="view">Jerin Sunny </p>

        </div>
        <div style="display: flex; flex-direction: row; flex-grow: inherit;  align-items: center;">
          <a href="https://www.linkedin.com/in/shakir-zari/" target="_blank">
          <img src="https://avatars.githubusercontent.com/u/166615503" height="50px" width="50px" style="border-radius: 50%; margin: 0.25rem;"> </a>
          <p class="view">Shakir Zari </p>

        </div>
      </div>
      
      <section id="downloads">
        
      </section>
    </div>
  </header>

  <div class="container">
    <section id="main_content">
      <h2 id="overview">Overview</h2>
<p>This blog describes voltage glitching attack on <strong>STM32F4</strong> series MCU. This post aims to provide a practical example of executing a voltage glitching attack, while also discussing the challenges and limitations one might encounter during the process.</p>

<h2 id="introduction-to-voltage-glitching">Introduction to Voltage Glitching</h2>

<p>Fault Injection attack involves the process of deliberately introducing controlled/targeted faults into a system, such that the system misbehaves, but not enough to cause a hard fault.
<code class="language-plaintext highlighter-rouge">Voltage glitching</code> involves targeting the power supply of the system. The goal here is to manipulate the power to a target system precisely at a specific moment for specific period of time, such that the target system misbehaves such as skipping instructions, breaking memory and register contents etc.</p>

<div class="language-plaintext highlighter-rouge"><div class="highlight"><pre class="highlight"><code>From a security perspective this can be exploited to bypass security mechanisms such as secure debug access, 
access to protected memory, extracting secret keys, authentication bypass.
</code></pre></div></div>

<h2 id="target-description">Target Description</h2>

<h3 id="stm32f4-series">STM32F4 series</h3>
<p>The <a href="https://www.st.com/en/microcontrollers-microprocessors/stm32f4-series.html">STM32F4</a> series microcontrollers (MCUs) are a popular family of embedded systems processors developed by STMicroelectronics. Renowned for their high performance, low power consumption, and rich peripheral integration, STM32F4 MCUs are widely used in a diverse range of applications, including industrial automation, consumer electronics, automotive systems, and IoT devices.</p>

<p>The target device used for this research was an <a href="https://robu.in/product/stm32f401ccu6-minimum-system-board-microcomputer-stm32-arm-core-board/">STM32F401CCU6 Minimum System STM32 ARM Core Board</a>, which contains an STM32F4 series MCU. The target details are mentioned below:</p>
<blockquote>

  <p>Model: STM32F401CCU6.<br />
Core: ARM 32 Cortex-M4 CPU.<br />
Debug mode: SWD.<br />
84MHz work frequency.<br />
256K flash memory, 64K SRAM.</p>
</blockquote>

<h2 id="technical-details-stm32">Technical Details STM32</h2>
<h3 id="boot-process-and-boot-rom">Boot Process and Boot ROM</h3>
<p>Boot ROMs are the initial piece of code within microcontrollers that are executed during the boot process. These ROMs contain firmware code responsible for initializing essential hardware parameters and settings, such as memory configuration, security configuration (Option bytes) and boot modes, upon powering up the microcontroller.</p>

<p>BOOT ROMs play a crucial role in the initial bootstrapping process of the microcontroller, ensuring proper initialization before handing control over to the main application code. They are integral to the startup sequence of the microcontroller and help establish a stable and functional operating environment for the device.</p>

<p>The bootloader is stored in the internal boot ROM (system memory) of STM32 devices, and is programmed by STM during production. Its main task is to reprogram the Flash memory through one of the available serial peripherals. More details on the STM32 Bootloader can be found in <a href="https://www.st.com/resource/en/application_note/cd00167594-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf">AN2606:Application Note</a></p>

<h3 id="enabling-bootloader">Enabling Bootloader</h3>

<p>STM32F4 has a set of dedicated I/0 pins knowns as Boot Pins, these pins are used to determine the boot options. The BootROM present in STM32 Microcontrollers checks for a predefined logic level in the Boot Pins and then enables the bootloader. In STM32F4 the bootloader can be activated by setting a specific pattern on the Boot Pins, as mentioned in this <a href="https://www.st.com/resource/en/application_note/cd00167594-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf">document</a>  .</p>

<h3 id="stm32-bootloader-features">STM32 Bootloader Features</h3>
<p>The STM32 Bootloader supports USART protocol and provides a lot of features. This bootloader supports a wide set of commands as described in the <a href="https://www.st.com/resource/en/application_note/cd00264342-usart-protocol-used-in-the-stm32-bootloader-stmicroelectronics.pdf">application note</a>.</p>
<figure style="text-align:center;">
<img src="./assets/images/bootloader_cmnds.webp" width="60%" />
<figcaption>STM32 Bootloader commands </figcaption>
</figure>

<p>We are interested in the Read Memory Command as it helps us to dump the flash memory contents of the MCU. The key takeaway is that the Read command has a limit—it only fetches 256 bytes of memory, starting from a specific memory address location.</p>

<h2 id="stm32-security-overview">STM32 Security Overview</h2>

<p>STM32 MCUs provide a host of security features which has been described <a href="https://www.st.com/resource/en/application_note/an5156-introduction-to-security-for-stm32-mcus-stmicroelectronics.pdf">here</a>. STM32 MCUs also provide a security mechanism called <code class="language-plaintext highlighter-rouge">Read Out Protection (RDP)</code> to prevent unauthenticated access to flash memory contents. STM32 provides a specific set of Option Bytes to configure the security setting of the MCU. Option Bytes are mostly used to pre-configure the system on chip before starting the Cortex®-M and user code. They are basically meant to allow the user a way to customize the general settings of the microcontroller.</p>

<p>STM32F4 basically provides three levels of <a href="https://www.st.com/resource/en/application_note/dm00186528-proprietary-code-readout-protection-on-microcontrollers-of-the-stm32f4-series-stmicroelectronics.pdf">Read Out Protection</a> :</p>

<figure style="text-align:center;">
<img src="./assets/images/rdp_levels.webp" width="60%" />
<figcaption>STM32 RDP Levels </figcaption>
</figure>

<p>RDP0</p>
<blockquote>
  <p>This is the Default level. In this mode there is no protection.</p>
</blockquote>

<p>RDP1</p>
<blockquote>
  <p>In RDP Level 1 there is no access to Flash Memory. Reading, programming and erasing the flash memory, even through SWD or JTAG is also disabled. Any read request to the protected Flash memory generates a bus error. In this level booting from SRAM and system bootloader is allowed.</p>
</blockquote>

<p>RPD2</p>
<blockquote>
  <p>In this level, the chip is fully protected. All the option bytes are frozen and cannot be modified. The JTAG, SWV (single-wire viewer), ETM, and boundary scan are disabled. Booting from SRAM or from system memory bootloader is not allowed.</p>
</blockquote>

<p>RDP Levels can always be levelled up. Downgrading from RDP1 to RDP0 can be done by reprogramming the option bytes, but this would lead to a mass erase of flash memory, SRAM and backup registers.  RDP2 level is irreversible and cannot be downgraded.</p>

<h2 id="stm32-power-managementregulation">STM32 Power Management/Regulation</h2>

<p>For <code class="language-plaintext highlighter-rouge">Voltage Glitching</code> attack, we need to target the power supply of the MCU. Every MCU has a specifically designed power management/ regulation system, which is used for powering the internal circuitry, peripherals etc. The power supply scheme of STM32 is shown in the below figure.</p>
<figure style="text-align:center;">
<img src="./assets/images/stm32_power.webp" width="60%" />
<figcaption>STM32F4  Power Supply Scheme </figcaption>
</figure>

<p>From the power supply scheme it is clear that we need to target the voltage regulator to inject faults into the power rails. VCAP_1 and VCAP_2 pins gives us direct access to internal power rails.</p>

<h2 id="glitch-setup">Glitch Setup</h2>

<p>As mentioned earlier, we have used <a href="https://robu.in/product/stm32f401ccu6-minimum-system-board-microcomputer-stm32-arm-core-board/">STM32F401CCU6 Minimum System STM32 ARM Core Board</a> for this research.</p>

<h3 id="hardware-setup">Hardware Setup</h3>

<p>Every system has components designed to specifically maintain the its operating voltage at the appropriate levels, such as decoupling capacitors. One of the challenges/requirement with this method is to modify/tamper  the hardware circuitry in order to overcome the protection offered by these components. This includes removal of some components, replacing with custom components, as well as selecting the glitch injection point.</p>

<p>We have used VCAP_1 as glitch injection point. The decoupling capacitors were replaced, which would increase the impact  of our glitch on the target. A custom glitch injection circuit consisting of capacitors, resistors and MOSFETs was created to ensure precise glitch injection. Each component was carefully chosen following comprehensive research to ensure the circuit delivers the desired glitch reliably.</p>

<p>We used <code class="language-plaintext highlighter-rouge">Teensy</code> board to develop our glitcher software, which would help us to control the glitch and precisely inject the required glitch. <br />
We tested out other glitching tools such as <code class="language-plaintext highlighter-rouge">Chipwhisperer Lite</code>, but hit a snag with the STM32 bootloader’s UART protocol, which demands an even parity bit. It was a tough nut to crack because Chipwhisperer Lite’s didn’t offer a straightforward way to tweak the UART parity bit.</p>

<p>We came across a fix for this issue in a recent <a href="https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/">article</a>, but we were already underway with our research when it was released, and had already started a different approach at that time.</p>

<p>The hardware setup used for the research is shown in the figure below.</p>
<figure style="text-align:center;">
<img src="./assets/images/hardware_setup.jpg" width="70%" />
<figcaption>Hardware Setup </figcaption>
</figure>

<p>Teensy board is communicating serially to the targets UART port. It also controls the glitch injection circuit, to inject the glitch precisely. We soldered the output of glitch injection circuit to VCAP_1 pin, ensuring minimal losses to the glitch. The specified logic levels are applied on the Boot Pins so that the target boots into the bootloader mode as mentioned in the section <a href="#enabling-bootloader">Enabling Bootloader</a>.</p>

<h3 id="software-setup">Software Setup</h3>

<p>ST-Link V2 Programmer was used to connect to the target via the SWD interface. We used STM32Cube IDE to write a sample program and flashed it to the target. A dump of the flash memory was taken to verify our results later on, a snapshot of the dump is shown below.</p>
<figure style="text-align:center;">
<img src="./assets/images/org_firmware.webp" width="45%" id="dump" />
<figcaption>Firmware dump before enabling RDP1</figcaption>
</figure>

<p>Next, STM32CubeProgrammer was used to enable RDP1 on the target. STM32CubeProgrammer enables us to program the Option Bytes in STM32 MCUs. RDP1 can be enabled by setting any value other than 0xAA and 0xCC.</p>

<figure style="text-align:center;">
<img src="./assets/images/rdp_1.webp" width="70%" />
<figcaption>RDP1 enabled on target </figcaption>
</figure>

<h3 id="glitcher-software">Glitcher Software</h3>
<p>As our aim is to dump the firmware, as mentioned <a href="#stm32-bootloader-features">earlier</a> we will be targeting the Read Memory command(0x11). As described <a href="https://www.st.com/resource/en/application_note/cd00264342-usart-protocol-used-in-the-stm32-bootloader-stmicroelectronics.pdf">here</a>, on receiving the Read Memory command, the device checks if any RDP levels is set or not and based on that access to flash memory is provided. If RDP is active the device returns NACK byte for the Read Memory command else the device returns ACK byte.</p>

<p>The glitcher software performs the following operation</p>
<div class="language-python highlighter-rouge"><div class="highlight"><pre class="highlight"><code><span class="n">send_read_memory_command</span><span class="p">()</span>
<span class="n">inject_glitch</span><span class="p">(</span><span class="n">glitch_parameters</span><span class="p">)</span>
<span class="n">result</span><span class="o">=</span> <span class="n">read_response</span><span class="p">()</span>
<span class="k">if</span> <span class="n">result</span> <span class="o">==</span> <span class="n">ack</span><span class="p">:</span>
  <span class="c1"># RDP1 Bypassed
</span>  <span class="n">data</span> <span class="o">=</span> <span class="n">read_265K_from</span><span class="p">(</span><span class="n">address</span><span class="p">)</span>
  <span class="c1"># memory read successful
</span>  <span class="k">print</span><span class="p">(</span><span class="n">data</span><span class="p">)</span>
<span class="k">elif</span> <span class="n">result</span> <span class="o">==</span> <span class="n">nack</span><span class="p">:</span>
  <span class="c1">#Print RDP1 active
</span>  <span class="n">send_read_memory_command</span><span class="p">()</span>
</code></pre></div></div>

<h2 id="glitching-the-target">Glitching the target</h2>

<p>Once the hardware and software is setup, we ran the setup for obtaining initial characterization. Obtain the glitch parameters from the characterization tests done. The key parameters for voltage glitching are - Glitch Offset and Glitch  Width. Glitch Offset dictates when to inject the glitch. Glitch Width determines the duration of the glitch to be applied. Observe the glitch on an oscilloscope to corelate the software glitch parameters with the actual glitch impact. Narrow down the glitch parameters after each run based on the characterization results obtained.</p>

<figure style="text-align:center;">
<img src="./assets/images/oscilloscope.webp" width="75%" />
<figcaption>Observing Trigger and Glitch Parameters  </figcaption>
</figure>

<h4 id="note">Note</h4>
<p>During the process of narrowing down the glitch parameters, we observed that positive ack response for Read Memory command is obtained, but on comparing the data, we only got zeros as data as shown below. This meant that RDP1 level was successfully bypassed but we were not able to read the data.</p>

<video class="center" width="80%" autoplay="" loop="" muted="">
  <source src="./assets/gifs/Pcrop.webm" type="video/webm" />
</video>

<p>Upon further analysis, it became apparent that the Option Byte for PCROP (SPRMOD) was inadvertently getting set during the voltage glitching process. This suggests the need to fine-tune the glitch to prevent unintended setting of PCROP during glitching.</p>
<figure style="text-align:center;">
<img src="./assets/images/pcrop.webp" width="95%" />
<figcaption>PCROP Bit getting set during glitching </figcaption>
</figure>

<p>We manually unset the PCROP bit , regressed the RDP level to RDP0 , then followed the whole software setup and restarted the whole process.</p>

<h2 id="glitched-successfully">Glitched Successfully</h2>

<p>After fine tuning the glitch, finally the glitch was successful and we obtained some data as shown <a href="#mem">below</a>. To verify our results, we compared the data output with the original dump taken before enabling RDP1 as shown in <a href="#dump">figure</a>.</p>

<figure style="text-align:center;">
<img src="./assets/images/logic1.png" width="95%" id="mem" />
<figcaption>Successful Data Read</figcaption>
</figure>

<p>As explained in the above <a href="#stm32-bootloader-features">section</a>, a single Read Memory Command can only read 256 bytes of data before reading the next block of data. Since the targets flash size is of 256KB, a total of 1024 successful glitches were required to extract the whole flash memory. The glitch setup was kept running till the whole firmware was extracted.</p>

<video class="center" width="80%" autoplay="" loop="" muted="">
  <source src="./assets/gifs/memory_read_1.webm" type="video/webm" />
</video>

<p>After around <strong><code class="language-plaintext highlighter-rouge">22hrs</code></strong> and 1024 successful glitches out of 621594 glitches, the whole firmware was extracted as shown in <a href="#full_mem">figure</a> below.</p>
<figure style="text-align:center;">
<img src="./assets/images/1024.webp" width="50%" id="full_mem" />
<figcaption>Extracted 256KB Flash Memory</figcaption>
</figure>

<hr />
<!-- ### Authors -->
<h3 id="this-research-was-carried-out-by-jerin-sunny-and-shakir-zari-and-published-on-behalf-of-the-fev-secure-lab">This research was carried out by <a href="https://www.linkedin.com/in/jerin-sunny/"><code class="language-plaintext highlighter-rouge">Jerin Sunny</code></a> and <a href="https://www.linkedin.com/in/shakir-zari/" target="_blank"><code class="language-plaintext highlighter-rouge">Shakir Zari</code></a> and published on behalf of the <a href="https://in.linkedin.com/company/fev-india" target="_blank"><code class="language-plaintext highlighter-rouge">FEV Secure Lab</code></a>.</h3>

<hr />

    </section>
  </div>
</body>

</html>