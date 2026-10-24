<!DOCTYPE html>
<html lang="en-US">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="profile" href="http://gmpg.org/xfn/11">
        <link rel="pingback" href="https://www.anvilsecure.com/xmlrpc.php">

        <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">

	<!-- This site is optimized with the Yoast SEO plugin v23.7 - https://yoast.com/wordpress/plugins/seo/ -->
	<title>Glitching STM32 Read Out Protection</title>
	<meta name="description" content="Security Engineer Luigi Fragale demonstrates how to glitch the STM32F401 to read protected memory using Python and fault injection.">
	<link rel="canonical" href="https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html">
	<meta property="og:locale" content="en_US">
	<meta property="og:type" content="article">
	<meta property="og:title" content="Glitching STM32 Read Out Protection">
	<meta property="og:description" content="Security Engineer Luigi Fragale demonstrates how to glitch the STM32F401 to read protected memory using Python and fault injection.">
	<meta property="og:url" content="https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html">
	<meta property="og:site_name" content="Anvil Secure">
	<meta property="article:published_time" content="2025-04-18T11:09:25+00:00">
	<meta property="article:modified_time" content="2025-04-19T05:46:59+00:00">
	<meta property="og:image" content="https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_v5.png">
	<meta property="og:image:width" content="1080">
	<meta property="og:image:height" content="400">
	<meta property="og:image:type" content="image/png">
	<meta name="author" content="Anvil Secure">
	<meta name="twitter:card" content="summary_large_image">
	<meta name="twitter:creator" content="@anvil_secure">
	<meta name="twitter:site" content="@anvil_secure">
	<meta name="twitter:label1" content="Written by">
	<meta name="twitter:data1" content="Anvil Secure">
	<meta name="twitter:label2" content="Est. reading time">
	<meta name="twitter:data2" content="15 minutes">
	<script type="application/ld+json" class="yoast-schema-graph">{"@context":"https://schema.org","@graph":[{"@type":"Article","@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html#article","isPartOf":{"@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html"},"author":{"name":"Anvil Secure","@id":"https://www.anvilsecure.com/#/schema/person/7c0f5e1539362615b38b29523fdbb0b8"},"headline":"Glitching STM32 Read Out Protection","datePublished":"2025-04-18T11:09:25+00:00","dateModified":"2025-04-19T05:46:59+00:00","mainEntityOfPage":{"@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html"},"wordCount":2597,"commentCount":0,"publisher":{"@id":"https://www.anvilsecure.com/#organization"},"image":{"@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html#primaryimage"},"thumbnailUrl":"https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_v5.png","inLanguage":"en-US","potentialAction":[{"@type":"CommentAction","name":"Comment","target":["https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html#respond"]}]},{"@type":"WebPage","@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html","url":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html","name":"Glitching STM32 Read Out Protection","isPartOf":{"@id":"https://www.anvilsecure.com/#website"},"primaryImageOfPage":{"@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html#primaryimage"},"image":{"@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html#primaryimage"},"thumbnailUrl":"https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_v5.png","datePublished":"2025-04-18T11:09:25+00:00","dateModified":"2025-04-19T05:46:59+00:00","description":"Security Engineer Luigi Fragale demonstrates how to glitch the STM32F401 to read protected memory using Python and fault injection.","breadcrumb":{"@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html#breadcrumb"},"inLanguage":"en-US","potentialAction":[{"@type":"ReadAction","target":["https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html"]}]},{"@type":"ImageObject","inLanguage":"en-US","@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html#primaryimage","url":"https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_v5.png","contentUrl":"https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_v5.png","width":1080,"height":400},{"@type":"BreadcrumbList","@id":"https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html#breadcrumb","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":"https://www.anvilsecure.com/"},{"@type":"ListItem","position":2,"name":"Glitching STM32 Read Out Protection"}]},{"@type":"WebSite","@id":"https://www.anvilsecure.com/#website","url":"https://www.anvilsecure.com/","name":"Anvil Ventures","description":"","publisher":{"@id":"https://www.anvilsecure.com/#organization"},"potentialAction":[{"@type":"SearchAction","target":{"@type":"EntryPoint","urlTemplate":"https://www.anvilsecure.com/?s={search_term_string}"},"query-input":{"@type":"PropertyValueSpecification","valueRequired":true,"valueName":"search_term_string"}}],"inLanguage":"en-US"},{"@type":"Organization","@id":"https://www.anvilsecure.com/#organization","name":"Anvil Secure","url":"https://www.anvilsecure.com/","logo":{"@type":"ImageObject","inLanguage":"en-US","@id":"https://www.anvilsecure.com/#/schema/logo/image/","url":"https://www.anvilsecure.com/wp-content/uploads/2021/04/Anvil_Secure_Logo.png","contentUrl":"https://www.anvilsecure.com/wp-content/uploads/2021/04/Anvil_Secure_Logo.png","width":1200,"height":511,"caption":"Anvil Secure"},"image":{"@id":"https://www.anvilsecure.com/#/schema/logo/image/"},"sameAs":["https://x.com/anvil_secure","https://www.linkedin.com/company/anvil-ventures-inc/"]},{"@type":"Person","@id":"https://www.anvilsecure.com/#/schema/person/7c0f5e1539362615b38b29523fdbb0b8","name":"Anvil Secure","image":{"@type":"ImageObject","inLanguage":"en-US","@id":"https://www.anvilsecure.com/#/schema/person/image/","url":"https://secure.gravatar.com/avatar/6eb0166f9f257ad7ea5d6548a155217b?s=96&d=mm&r=g","contentUrl":"https://secure.gravatar.com/avatar/6eb0166f9f257ad7ea5d6548a155217b?s=96&d=mm&r=g","caption":"Anvil Secure"}}]}</script>
	<!-- / Yoast SEO plugin. -->


<link rel="dns-prefetch" href="//js.hs-scripts.com">
<link rel="dns-prefetch" href="//fonts.googleapis.com">
<link rel="alternate" type="application/rss+xml" title="Anvil Secure &raquo; Feed" href="https://www.anvilsecure.com/feed">
<link rel="alternate" type="application/rss+xml" title="Anvil Secure &raquo; Comments Feed" href="https://www.anvilsecure.com/comments/feed">
<link rel="alternate" type="application/rss+xml" title="Anvil Secure &raquo; Glitching STM32 Read Out Protection Comments Feed" href="https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html/feed">
<script type="text/javascript">
/* <![CDATA[ */
window._wpemojiSettings = {"baseUrl":"https:\/\/s.w.org\/images\/core\/emoji\/15.0.3\/72x72\/","ext":".png","svgUrl":"https:\/\/s.w.org\/images\/core\/emoji\/15.0.3\/svg\/","svgExt":".svg","source":{"concatemoji":"https:\/\/www.anvilsecure.com\/wp-includes\/js\/wp-emoji-release.min.js?ver=6.6.10"}};
/*! This file is auto-generated */
!function(i,n){var o,s,e;function c(e){try{var t={supportTests:e,timestamp:(new Date).valueOf()};sessionStorage.setItem(o,JSON.stringify(t))}catch(e){}}function p(e,t,n){e.clearRect(0,0,e.canvas.width,e.canvas.height),e.fillText(t,0,0);var t=new Uint32Array(e.getImageData(0,0,e.canvas.width,e.canvas.height).data),r=(e.clearRect(0,0,e.canvas.width,e.canvas.height),e.fillText(n,0,0),new Uint32Array(e.getImageData(0,0,e.canvas.width,e.canvas.height).data));return t.every(function(e,t){return e===r[t]})}function u(e,t,n){switch(t){case"flag":return n(e,"🏳️‍⚧️","🏳️​⚧️")?!1:!n(e,"🇺🇳","🇺​🇳")&&!n(e,"🏴󠁧󠁢󠁥󠁮󠁧󠁿","🏴​󠁧​󠁢​󠁥​󠁮​󠁧​󠁿");case"emoji":return!n(e,"🐦‍⬛","🐦​⬛")}return!1}function f(e,t,n){var r="undefined"!=typeof WorkerGlobalScope&&self instanceof WorkerGlobalScope?new OffscreenCanvas(300,150):i.createElement("canvas"),a=r.getContext("2d",{willReadFrequently:!0}),o=(a.textBaseline="top",a.font="600 32px Arial",{});return e.forEach(function(e){o[e]=t(a,e,n)}),o}function t(e){var t=i.createElement("script");t.src=e,t.defer=!0,i.head.appendChild(t)}"undefined"!=typeof Promise&&(o="wpEmojiSettingsSupports",s=["flag","emoji"],n.supports={everything:!0,everythingExceptFlag:!0},e=new Promise(function(e){i.addEventListener("DOMContentLoaded",e,{once:!0})}),new Promise(function(t){var n=function(){try{var e=JSON.parse(sessionStorage.getItem(o));if("object"==typeof e&&"number"==typeof e.timestamp&&(new Date).valueOf()<e.timestamp+604800&&"object"==typeof e.supportTests)return e.supportTests}catch(e){}return null}();if(!n){if("undefined"!=typeof Worker&&"undefined"!=typeof OffscreenCanvas&&"undefined"!=typeof URL&&URL.createObjectURL&&"undefined"!=typeof Blob)try{var e="postMessage("+f.toString()+"("+[JSON.stringify(s),u.toString(),p.toString()].join(",")+"));",r=new Blob([e],{type:"text/javascript"}),a=new Worker(URL.createObjectURL(r),{name:"wpTestEmojiSupports"});return void(a.onmessage=function(e){c(n=e.data),a.terminate(),t(n)})}catch(e){}c(n=f(s,u,p))}t(n)}).then(function(e){for(var t in e)n.supports[t]=e[t],n.supports.everything=n.supports.everything&&n.supports[t],"flag"!==t&&(n.supports.everythingExceptFlag=n.supports.everythingExceptFlag&&n.supports[t]);n.supports.everythingExceptFlag=n.supports.everythingExceptFlag&&!n.supports.flag,n.DOMReady=!1,n.readyCallback=function(){n.DOMReady=!0}}).then(function(){return e}).then(function(){var e;n.supports.everything||(n.readyCallback(),(e=n.source||{}).concatemoji?t(e.concatemoji):e.wpemoji&&e.twemoji&&(t(e.twemoji),t(e.wpemoji)))}))}((window,document),window._wpemojiSettings);
/* ]]> */
</script>
<link rel="stylesheet" id="mci-footnotes-jquery-tooltips-pagelayout-none-css" href="https://www.anvilsecure.com/wp-content/plugins/footnotes/css/footnotes-jqttbrpl0.min.css?ver=2.7.3" type="text/css" media="all">
<link rel="stylesheet" id="dashicons-css" href="https://www.anvilsecure.com/wp-includes/css/dashicons.min.css?ver=6.6.10" type="text/css" media="all">
<link rel="stylesheet" id="menu-icons-extra-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/inc/assets/menu-icons/css/extra.min.css?ver=0.10.2" type="text/css" media="all">
<style id="wp-emoji-styles-inline-css" type="text/css">img.wp-smiley, img.emoji {
		display: inline !important;
		border: none !important;
		box-shadow: none !important;
		height: 1em !important;
		width: 1em !important;
		margin: 0 0.07em !important;
		vertical-align: -0.1em !important;
		background: none !important;
		padding: 0 !important;
	}</style>
<link rel="stylesheet" id="wp-block-library-css" href="https://www.anvilsecure.com/wp-includes/css/dist/block-library/style.min.css?ver=6.6.10" type="text/css" media="all">
<style id="wp-block-library-theme-inline-css" type="text/css">.wp-block-audio :where(figcaption){color:#555;font-size:13px;text-align:center}.is-dark-theme .wp-block-audio :where(figcaption){color:#ffffffa6}.wp-block-audio{margin:0 0 1em}.wp-block-code{border:1px solid #ccc;border-radius:4px;font-family:Menlo,Consolas,monaco,monospace;padding:.8em 1em}.wp-block-embed :where(figcaption){color:#555;font-size:13px;text-align:center}.is-dark-theme .wp-block-embed :where(figcaption){color:#ffffffa6}.wp-block-embed{margin:0 0 1em}.blocks-gallery-caption{color:#555;font-size:13px;text-align:center}.is-dark-theme .blocks-gallery-caption{color:#ffffffa6}:root :where(.wp-block-image figcaption){color:#555;font-size:13px;text-align:center}.is-dark-theme :root :where(.wp-block-image figcaption){color:#ffffffa6}.wp-block-image{margin:0 0 1em}.wp-block-pullquote{border-bottom:4px solid;border-top:4px solid;color:currentColor;margin-bottom:1.75em}.wp-block-pullquote cite,.wp-block-pullquote footer,.wp-block-pullquote__citation{color:currentColor;font-size:.8125em;font-style:normal;text-transform:uppercase}.wp-block-quote{border-left:.25em solid;margin:0 0 1.75em;padding-left:1em}.wp-block-quote cite,.wp-block-quote footer{color:currentColor;font-size:.8125em;font-style:normal;position:relative}.wp-block-quote.has-text-align-right{border-left:none;border-right:.25em solid;padding-left:0;padding-right:1em}.wp-block-quote.has-text-align-center{border:none;padding-left:0}.wp-block-quote.is-large,.wp-block-quote.is-style-large,.wp-block-quote.is-style-plain{border:none}.wp-block-search .wp-block-search__label{font-weight:700}.wp-block-search__button{border:1px solid #ccc;padding:.375em .625em}:where(.wp-block-group.has-background){padding:1.25em 2.375em}.wp-block-separator.has-css-opacity{opacity:.4}.wp-block-separator{border:none;border-bottom:2px solid;margin-left:auto;margin-right:auto}.wp-block-separator.has-alpha-channel-opacity{opacity:1}.wp-block-separator:not(.is-style-wide):not(.is-style-dots){width:100px}.wp-block-separator.has-background:not(.is-style-dots){border-bottom:none;height:1px}.wp-block-separator.has-background:not(.is-style-wide):not(.is-style-dots){height:2px}.wp-block-table{margin:0 0 1em}.wp-block-table td,.wp-block-table th{word-break:normal}.wp-block-table :where(figcaption){color:#555;font-size:13px;text-align:center}.is-dark-theme .wp-block-table :where(figcaption){color:#ffffffa6}.wp-block-video :where(figcaption){color:#555;font-size:13px;text-align:center}.is-dark-theme .wp-block-video :where(figcaption){color:#ffffffa6}.wp-block-video{margin:0 0 1em}:root :where(.wp-block-template-part.has-background){margin-bottom:0;margin-top:0;padding:1.25em 2.375em}</style>
<style id="classic-theme-styles-inline-css" type="text/css">/*! This file is auto-generated */
.wp-block-button__link{color:#fff;background-color:#32373c;border-radius:9999px;box-shadow:none;text-decoration:none;padding:calc(.667em + 2px) calc(1.333em + 2px);font-size:1.125em}.wp-block-file__button{background:#32373c;color:#fff;text-decoration:none}</style>
<style id="global-styles-inline-css" type="text/css">:root{--wp--preset--aspect-ratio--square: 1;--wp--preset--aspect-ratio--4-3: 4/3;--wp--preset--aspect-ratio--3-4: 3/4;--wp--preset--aspect-ratio--3-2: 3/2;--wp--preset--aspect-ratio--2-3: 2/3;--wp--preset--aspect-ratio--16-9: 16/9;--wp--preset--aspect-ratio--9-16: 9/16;--wp--preset--color--black: #000000;--wp--preset--color--cyan-bluish-gray: #abb8c3;--wp--preset--color--white: #ffffff;--wp--preset--color--pale-pink: #f78da7;--wp--preset--color--vivid-red: #cf2e2e;--wp--preset--color--luminous-vivid-orange: #ff6900;--wp--preset--color--luminous-vivid-amber: #fcb900;--wp--preset--color--light-green-cyan: #7bdcb5;--wp--preset--color--vivid-green-cyan: #00d084;--wp--preset--color--pale-cyan-blue: #8ed1fc;--wp--preset--color--vivid-cyan-blue: #0693e3;--wp--preset--color--vivid-purple: #9b51e0;--wp--preset--gradient--vivid-cyan-blue-to-vivid-purple: linear-gradient(135deg,rgba(6,147,227,1) 0%,rgb(155,81,224) 100%);--wp--preset--gradient--light-green-cyan-to-vivid-green-cyan: linear-gradient(135deg,rgb(122,220,180) 0%,rgb(0,208,130) 100%);--wp--preset--gradient--luminous-vivid-amber-to-luminous-vivid-orange: linear-gradient(135deg,rgba(252,185,0,1) 0%,rgba(255,105,0,1) 100%);--wp--preset--gradient--luminous-vivid-orange-to-vivid-red: linear-gradient(135deg,rgba(255,105,0,1) 0%,rgb(207,46,46) 100%);--wp--preset--gradient--very-light-gray-to-cyan-bluish-gray: linear-gradient(135deg,rgb(238,238,238) 0%,rgb(169,184,195) 100%);--wp--preset--gradient--cool-to-warm-spectrum: linear-gradient(135deg,rgb(74,234,220) 0%,rgb(151,120,209) 20%,rgb(207,42,186) 40%,rgb(238,44,130) 60%,rgb(251,105,98) 80%,rgb(254,248,76) 100%);--wp--preset--gradient--blush-light-purple: linear-gradient(135deg,rgb(255,206,236) 0%,rgb(152,150,240) 100%);--wp--preset--gradient--blush-bordeaux: linear-gradient(135deg,rgb(254,205,165) 0%,rgb(254,45,45) 50%,rgb(107,0,62) 100%);--wp--preset--gradient--luminous-dusk: linear-gradient(135deg,rgb(255,203,112) 0%,rgb(199,81,192) 50%,rgb(65,88,208) 100%);--wp--preset--gradient--pale-ocean: linear-gradient(135deg,rgb(255,245,203) 0%,rgb(182,227,212) 50%,rgb(51,167,181) 100%);--wp--preset--gradient--electric-grass: linear-gradient(135deg,rgb(202,248,128) 0%,rgb(113,206,126) 100%);--wp--preset--gradient--midnight: linear-gradient(135deg,rgb(2,3,129) 0%,rgb(40,116,252) 100%);--wp--preset--font-size--small: 13px;--wp--preset--font-size--medium: 20px;--wp--preset--font-size--large: 36px;--wp--preset--font-size--x-large: 42px;--wp--preset--spacing--20: 0.44rem;--wp--preset--spacing--30: 0.67rem;--wp--preset--spacing--40: 1rem;--wp--preset--spacing--50: 1.5rem;--wp--preset--spacing--60: 2.25rem;--wp--preset--spacing--70: 3.38rem;--wp--preset--spacing--80: 5.06rem;--wp--preset--shadow--natural: 6px 6px 9px rgba(0, 0, 0, 0.2);--wp--preset--shadow--deep: 12px 12px 50px rgba(0, 0, 0, 0.4);--wp--preset--shadow--sharp: 6px 6px 0px rgba(0, 0, 0, 0.2);--wp--preset--shadow--outlined: 6px 6px 0px -3px rgba(255, 255, 255, 1), 6px 6px rgba(0, 0, 0, 1);--wp--preset--shadow--crisp: 6px 6px 0px rgba(0, 0, 0, 1);}:where(.is-layout-flex){gap: 0.5em;}:where(.is-layout-grid){gap: 0.5em;}body .is-layout-flex{display: flex;}.is-layout-flex{flex-wrap: wrap;align-items: center;}.is-layout-flex > :is(*, div){margin: 0;}body .is-layout-grid{display: grid;}.is-layout-grid > :is(*, div){margin: 0;}:where(.wp-block-columns.is-layout-flex){gap: 2em;}:where(.wp-block-columns.is-layout-grid){gap: 2em;}:where(.wp-block-post-template.is-layout-flex){gap: 1.25em;}:where(.wp-block-post-template.is-layout-grid){gap: 1.25em;}.has-black-color{color: var(--wp--preset--color--black) !important;}.has-cyan-bluish-gray-color{color: var(--wp--preset--color--cyan-bluish-gray) !important;}.has-white-color{color: var(--wp--preset--color--white) !important;}.has-pale-pink-color{color: var(--wp--preset--color--pale-pink) !important;}.has-vivid-red-color{color: var(--wp--preset--color--vivid-red) !important;}.has-luminous-vivid-orange-color{color: var(--wp--preset--color--luminous-vivid-orange) !important;}.has-luminous-vivid-amber-color{color: var(--wp--preset--color--luminous-vivid-amber) !important;}.has-light-green-cyan-color{color: var(--wp--preset--color--light-green-cyan) !important;}.has-vivid-green-cyan-color{color: var(--wp--preset--color--vivid-green-cyan) !important;}.has-pale-cyan-blue-color{color: var(--wp--preset--color--pale-cyan-blue) !important;}.has-vivid-cyan-blue-color{color: var(--wp--preset--color--vivid-cyan-blue) !important;}.has-vivid-purple-color{color: var(--wp--preset--color--vivid-purple) !important;}.has-black-background-color{background-color: var(--wp--preset--color--black) !important;}.has-cyan-bluish-gray-background-color{background-color: var(--wp--preset--color--cyan-bluish-gray) !important;}.has-white-background-color{background-color: var(--wp--preset--color--white) !important;}.has-pale-pink-background-color{background-color: var(--wp--preset--color--pale-pink) !important;}.has-vivid-red-background-color{background-color: var(--wp--preset--color--vivid-red) !important;}.has-luminous-vivid-orange-background-color{background-color: var(--wp--preset--color--luminous-vivid-orange) !important;}.has-luminous-vivid-amber-background-color{background-color: var(--wp--preset--color--luminous-vivid-amber) !important;}.has-light-green-cyan-background-color{background-color: var(--wp--preset--color--light-green-cyan) !important;}.has-vivid-green-cyan-background-color{background-color: var(--wp--preset--color--vivid-green-cyan) !important;}.has-pale-cyan-blue-background-color{background-color: var(--wp--preset--color--pale-cyan-blue) !important;}.has-vivid-cyan-blue-background-color{background-color: var(--wp--preset--color--vivid-cyan-blue) !important;}.has-vivid-purple-background-color{background-color: var(--wp--preset--color--vivid-purple) !important;}.has-black-border-color{border-color: var(--wp--preset--color--black) !important;}.has-cyan-bluish-gray-border-color{border-color: var(--wp--preset--color--cyan-bluish-gray) !important;}.has-white-border-color{border-color: var(--wp--preset--color--white) !important;}.has-pale-pink-border-color{border-color: var(--wp--preset--color--pale-pink) !important;}.has-vivid-red-border-color{border-color: var(--wp--preset--color--vivid-red) !important;}.has-luminous-vivid-orange-border-color{border-color: var(--wp--preset--color--luminous-vivid-orange) !important;}.has-luminous-vivid-amber-border-color{border-color: var(--wp--preset--color--luminous-vivid-amber) !important;}.has-light-green-cyan-border-color{border-color: var(--wp--preset--color--light-green-cyan) !important;}.has-vivid-green-cyan-border-color{border-color: var(--wp--preset--color--vivid-green-cyan) !important;}.has-pale-cyan-blue-border-color{border-color: var(--wp--preset--color--pale-cyan-blue) !important;}.has-vivid-cyan-blue-border-color{border-color: var(--wp--preset--color--vivid-cyan-blue) !important;}.has-vivid-purple-border-color{border-color: var(--wp--preset--color--vivid-purple) !important;}.has-vivid-cyan-blue-to-vivid-purple-gradient-background{background: var(--wp--preset--gradient--vivid-cyan-blue-to-vivid-purple) !important;}.has-light-green-cyan-to-vivid-green-cyan-gradient-background{background: var(--wp--preset--gradient--light-green-cyan-to-vivid-green-cyan) !important;}.has-luminous-vivid-amber-to-luminous-vivid-orange-gradient-background{background: var(--wp--preset--gradient--luminous-vivid-amber-to-luminous-vivid-orange) !important;}.has-luminous-vivid-orange-to-vivid-red-gradient-background{background: var(--wp--preset--gradient--luminous-vivid-orange-to-vivid-red) !important;}.has-very-light-gray-to-cyan-bluish-gray-gradient-background{background: var(--wp--preset--gradient--very-light-gray-to-cyan-bluish-gray) !important;}.has-cool-to-warm-spectrum-gradient-background{background: var(--wp--preset--gradient--cool-to-warm-spectrum) !important;}.has-blush-light-purple-gradient-background{background: var(--wp--preset--gradient--blush-light-purple) !important;}.has-blush-bordeaux-gradient-background{background: var(--wp--preset--gradient--blush-bordeaux) !important;}.has-luminous-dusk-gradient-background{background: var(--wp--preset--gradient--luminous-dusk) !important;}.has-pale-ocean-gradient-background{background: var(--wp--preset--gradient--pale-ocean) !important;}.has-electric-grass-gradient-background{background: var(--wp--preset--gradient--electric-grass) !important;}.has-midnight-gradient-background{background: var(--wp--preset--gradient--midnight) !important;}.has-small-font-size{font-size: var(--wp--preset--font-size--small) !important;}.has-medium-font-size{font-size: var(--wp--preset--font-size--medium) !important;}.has-large-font-size{font-size: var(--wp--preset--font-size--large) !important;}.has-x-large-font-size{font-size: var(--wp--preset--font-size--x-large) !important;}
:where(.wp-block-post-template.is-layout-flex){gap: 1.25em;}:where(.wp-block-post-template.is-layout-grid){gap: 1.25em;}
:where(.wp-block-columns.is-layout-flex){gap: 2em;}:where(.wp-block-columns.is-layout-grid){gap: 2em;}
:root :where(.wp-block-pullquote){font-size: 1.5em;line-height: 1.6;}</style>
<link rel="stylesheet" id="rs-plugin-settings-css" href="https://www.anvilsecure.com/wp-content/plugins/revslider/public/assets/css/rs6.css?ver=6.1.2" type="text/css" media="all">
<style id="rs-plugin-settings-inline-css" type="text/css">#rs-demo-id {}</style>
<link rel="stylesheet" id="siteorigin-panels-front-css" href="https://www.anvilsecure.com/wp-content/plugins/siteorigin-panels/css/front-flex.min.css?ver=2.20.6" type="text/css" media="all">
<link rel="stylesheet" id="megamenu-css" href="https://www.anvilsecure.com/wp-content/uploads/maxmegamenu/style.css?ver=107749" type="text/css" media="all">
<link rel="stylesheet" id="total-plus-loaders-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/loaders.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="total-plus-fonts-css" href="//fonts.googleapis.com/css?family=Poppins%3A100%2C100i%2C200%2C200i%2C300%2C300i%2C400%2C400i%2C500%2C500i%2C600%2C600i%2C700%2C700i%2C800%2C800i%2C900%2C900i&#038;subset=latin%2Clatin-ext&#038;display=swap" type="text/css" media="all">
<link rel="stylesheet" id="font-awesome-5.2.0-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/all.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="font-awesome-4.7.0-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/font-awesome-4.7.0.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="essential-icon-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/essential-icon.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="materialdesignicons-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/materialdesignicons.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="animate-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/animate.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="icofont-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/icofont.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="owl-carousel-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/owl.carousel.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="lightgallery-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/lightgallery.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="slick-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/slick.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="YTPlayer-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/jquery.mb.YTPlayer.min.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="flipster-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/jquery.flipster.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="jquery-mcustomscrollbar-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/jquery.mCustomScrollbar.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="justifiedGallery-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/css/justifiedGallery.min.css?ver=1.5.3" type="text/css" media="all">
<link rel="stylesheet" id="total-plus-style-css" href="https://www.anvilsecure.com/wp-content/themes/total-plus/style.css?ver=1.5.3" type="text/css" media="all">
<style id="total-plus-style-inline-css" type="text/css">.ht-container,.ht-slide-caption{max-width:1170px}body.ht-boxed #ht-page{max-width:1250px}.ht-header-five .ht-top-header.ht-container{max-width:1070px}#primary{width:67%}#secondary{width:30%}.ht-site-title-tagline a,.ht-site-title a,.ht-site-title-tagline a:hover,.ht-site-title a:hover,.ht-site-description{color:#333333}#ht-preloader-wrap{background:#FFFFFF}.ball-pulse-sync>div,.ball-pulse>div,.ball-scale-random>div,.ball-scale>div,.ball-grid-beat>div,.ball-grid-pulse>div,.ball-pulse-rise>div,.total-spin>div,.ball-rotate>div,.ball-rotate>div:before,.ball-rotate>div:after,.cube-transition>div,.ball-zig-zag>div,.line-scale>div,.ball-scale-multiple>div,.line-scale-pulse-out>div,.ball-spin-fade-loader>div,.pacman>div:nth-child(3),.pacman>div:nth-child(4),.pacman>div:nth-child(5),.pacman>div:nth-child(6){background:#2caaff}.ball-clip-rotate>div,.ball-clip-rotate-multiple>div,.ball-scale-ripple-multiple>div,.pacman>div:first-of-type,.pacman>div:nth-child(2){border-color:#2caaff}html,body,button,input,select,textarea,.megamenu-category .mega-post-title{font-family:'Poppins',serif;font-weight:300;font-style:normal;text-transform:none;text-decoration:none;font-size:16px;line-height:1.5;;color:#000000}.ht-menu > ul > li > a,a.ht-header-bttn{font-family:'Poppins',serif;font-weight:400;font-style:normal;text-transform:uppercase;text-decoration:none;font-size:16px;line-height:3}.ht-section-title{font-family:'Poppins',serif;font-weight:400;font-style:normal;text-transform:none;text-decoration:none;font-size:32px;line-height:1.5}.ht-main-title{font-family:'Poppins',serif;font-weight:400;font-style:normal;text-transform:none;text-decoration:none;font-size:40px;line-height:1.5}h1,h2,h3,h4,h5,h6,.ht-site-title,.entry-header div.entry-title{font-family:'Poppins',serif;font-weight:400;font-style:normal;text-transform:none;text-decoration:none;line-height:1.3}h2{font-size:40px}h3{font-size:34px}h4{font-size:28px}h5{font-size:22px}h6{font-size:16px}.ht-main-navigation{font-size:16px;font-family:Poppins}.single-ht-megamenu .ht-main-content{font-family:Poppins}.ht-main-content h1,.ht-main-content h2,.ht-main-content h3,.ht-main-content h4,.ht-main-content h5,.ht-main-content h6{color:#000000}.ht-main-content{color:#000000}a{color:#2caaff}a:hover{color:#1693e8}.widget-area li{border-color:rgba(0,0,0,0.05)}.ht-sidebar-style2 .widget-area .widget{border-color:rgba(0,0,0,0.1)}.widget-area .widget-title,#reply-title,#comments .comments-title,.total-plus-related-post .related-post-title{color:#000000}.ht-sidebar-style1 .widget-area .widget-title:after,.ht-sidebar-style1 #reply-title:after,.ht-sidebar-style1 #comments .comments-title:after,.ht-sidebar-style1 .total-plus-related-post .related-post-title:after,.ht-sidebar-style2 .widget-area .widget:before{background-color:#000000}.ht-sidebar-style3 .widget-area .widget-title,.ht-sidebar-style3 #reply-title,.ht-sidebar-style3 #comments .comments-title,.ht-sidebar-style3 .total-plus-related-post .related-post-title{border-color:#000000}.ht-site-header .ht-top-header{background:rgba(23,59,77,1);color:#94b2c2;padding-top:15px;padding-bottom:15px}.ht-site-header .ht-top-header a,.ht-site-header .ht-top-header a:hover,.ht-site-header .ht-top-header a i,.ht-site-header .ht-top-header a:hover i{color:#EEEEEE}.ht-header-one .ht-header,.ht-header-two .ht-header .ht-container,.ht-header-three .ht-header .ht-container,.ht-header-four .ht-header .ht-container,.ht-header-five .ht-header .ht-container,.ht-sticky-header .ht-header-two .ht-header.headroom.headroom--not-top,.ht-sticky-header .ht-header-three .ht-header.headroom.headroom--not-top,.ht-sticky-header .ht-header-four .ht-header.headroom.headroom--not-top,.ht-sticky-header .ht-header-five .ht-header.headroom.headroom--not-top,.ht-header-six .ht-main-navigation{background:rgba(255,255,255,1)}.ht-sticky-header .ht-header-two .ht-header.headroom.headroom--not-top .ht-container,.ht-sticky-header .ht-header-three .ht-header.headroom.headroom--not-top .ht-container,.ht-sticky-header .ht-header-four .ht-header.headroom--not-top .ht-container,.ht-sticky-header .ht-header-five .ht-header.headroom--not-top .ht-container{background:none}.ht-header-one .ht-header .ht-container,.ht-header-two .ht-main-navigation,.ht-header-four .ht-main-navigation,.ht-header-five .ht-header-wrap,.ht-header-six .ht-main-navigation .ht-container{height:110px}.ht-header-three .ht-header .ht-container{height:114px}.hover-style5 .ht-menu > ul > li.menu-item > a,.hover-style6 .ht-menu > ul > li.menu-item > a,.hover-style5 .ht-header-bttn,.hover-style6 .ht-header-bttn{line-height:110px}.ht-header-one #ht-site-branding img,.ht-header-two #ht-site-branding img,.ht-header-three #ht-site-branding img,.ht-header-five #ht-site-branding img{height:80px}.ht-header-one #ht-site-branding img,.ht-header-two #ht-site-branding img,.ht-header-three #ht-site-branding img,.ht-header-five #ht-site-branding img{max-height:80px}.ht-header-four #ht-site-branding img,.ht-header-six #ht-site-branding img{max-height:80px}.ht-menu > ul > li.menu-item > a,.hover-style1 .ht-menu>ul>li.menu-item.menu-item-social-icon:hover > a > i,.hover-style1 .ht-menu>ul>li.menu-item.menu-item-search:hover > a > i,.hover-style1 .ht-menu>ul>li.menu-item.menu-item-ht-cart:hover > a > i,.hover-style3 .ht-menu>ul>li.menu-item.menu-item-social-icon:hover > a > i,.hover-style3 .ht-menu>ul>li.menu-item.menu-item-search:hover > a > i,.hover-style3 .ht-menu>ul>li.menu-item.menu-item-ht-cart:hover > a > i,.hover-style5 .ht-menu>ul>li.menu-item.menu-item-social-icon:hover > a > i,.hover-style5 .ht-menu>ul>li.menu-item.menu-item-search:hover > a > i,.hover-style5 .ht-menu>ul>li.menu-item.menu-item-ht-cart:hover > a > i{color:#031033}.hover-style1 .ht-menu>ul>li.menu-item:hover>a,.hover-style1 .ht-menu>ul>li.menu-item.current_page_item>a,.hover-style1 .ht-menu>ul>li.menu-item.current-menu-item>a,.hover-style1 .ht-menu>ul>li.menu-item.current_page_ancestor>a,.hover-style1 .ht-menu>ul>li.menu-item.current>a,.ht-menu > ul > li.menu-item:hover > a,.ht-menu > ul > li.menu-item:hover > a > i,.ht-menu > ul > li.menu-item.current_page_item > a,.ht-menu > ul > li.menu-item.current-menu-item > a,.ht-menu > ul > li.menu-item.current_page_ancestor > a,.ht-menu > ul > li.menu-item.current > a{color:#2caaff}.ht-menu ul ul,.menu-item-ht-cart .widget_shopping_cart,#ht-responsive-menu{background:rgba(255,255,255,1)}.ht-menu .megamenu *,#ht-responsive-menu .megamenu *,.ht-menu .megamenu a,#ht-responsive-menu .megamenu a,.ht-menu ul ul li.menu-item > a,.menu-item-ht-cart .widget_shopping_cart a,.menu-item-ht-cart .widget_shopping_cart,#ht-responsive-menu li.menu-item > a,#ht-responsive-menu li.menu-item > a i,#ht-responsive-menu li .dropdown-nav,.megamenu-category .mega-post-title a{color:#031033}.ht-menu > ul > li > ul:not(.megamenu) li.menu-item:hover > a,.ht-menu ul ul.megamenu li.menu-item > a:hover,.ht-menu ul ul li.menu-item > a:hover i,.ht-menu .megamenu-full-width.megamenu-category .cat-megamenu-tab > div.active-tab{color:#2caaff}.ht-menu > ul > li > ul:not(.megamenu) li.menu-item:hover > a,.ht-menu ul ul.megamenu li.menu-item > a:hover,.ht-menu ul ul li.menu-item > a:hover i,.ht-menu .megamenu-full-width.megamenu-category .cat-megamenu-tab > div.active-tab{background-color:}.ht-header-three .ht-header .ht-container,.ht-sticky-header .ht-header-three .ht-header.headroom.headroom--not-top{border-bottom:4px solid rgba(23,59,77,1)}.ht-header-four .ht-middle-header{padding-bottom:55px;border-color:rgba(255,255,255,1)}.ht-hide-titlebar .ht-header-four#ht-masthead{padding-bottom:95px}.ht-header-five .ht-top-header + .ht-header .ht-container:before,.ht-header-five .ht-top-header + .ht-header .ht-container:after{border-bottom:135px solid rgba(255,255,255,1)}.hover-style1 .ht-menu > ul > li.menu-item:hover > a,.hover-style1 .ht-menu > ul > li.menu-item.current_page_item > a,.hover-style1 .ht-menu > ul > li.menu-item.current-menu-item > a,.hover-style1 .ht-menu > ul > li.menu-item.current_page_ancestor > a,.hover-style1 .ht-menu > ul > li.menu-item.current > a,.hover-style5 .ht-menu > ul > li.menu-item:hover > a,.hover-style5 .ht-menu > ul > li.menu-item.current_page_item > a,.hover-style5 .ht-menu > ul > li.menu-item.current-menu-item > a,.hover-style5 .ht-menu > ul > li.menu-item.current_page_ancestor > a,.hover-style5 .ht-menu > ul > li.menu-item.current > a{background:}.hover-style2 .ht-menu > ul > li.menu-item:hover > a,.hover-style2 .ht-menu > ul > li.menu-item.current_page_item > a,.hover-style2 .ht-menu > ul > li.menu-item.current-menu-item > a,.hover-style2 .ht-menu > ul > li.menu-item.current_page_ancestor > a,.hover-style2 .ht-menu > ul > li.menu-item.current > a,.hover-style4 .ht-menu > ul > li.menu-item:hover > a,.hover-style4 .ht-menu > ul > li.menu-item.current_page_item > a,.hover-style4 .ht-menu > ul > li.menu-item.current-menu-item > a,.hover-style4 .ht-menu > ul > li.menu-item.current_page_ancestor > a,.hover-style4 .ht-menu > ul > li.menu-item.current > a{color:#2caaff;border-color:#2caaff}.hover-style3 .ht-menu > ul > li.menu-item:hover > a,.hover-style3 .ht-menu > ul > li.menu-item.current_page_item > a,.hover-style3 .ht-menu > ul > li.menu-item.current-menu-item > a,.hover-style3 .ht-menu > ul > li.menu-item.current_page_ancestor > a,.hover-style3 .ht-menu > ul > li.menu-item.current > a{background:}.hover-style6 .ht-menu > ul > li.menu-item:hover > a:before,.hover-style6 .ht-menu > ul > li.menu-item.current_page_item > a:before,.hover-style6 .ht-menu > ul > li.menu-item.current-menu-item > a:before,.hover-style6 .ht-menu > ul > li.menu-item.current_page_ancestor > a:before,.hover-style6 .ht-menu > ul > li.menu-item.current > a:before{background:#2caaff}.ht-header-over .ht-slide-caption{margin-top:55px}.ht-header-style2 .ht-slide-caption,.ht-header-style3 .ht-slide-caption,.ht-header-style5 .ht-slide-caption{margin-top:80px}.ht-menu>ul>li.menu-item{padding-top:20px;padding-bottom:20px}.ht-service-bg{background-image:url(http://staging.anvilventures.com/kimbo/wp-content/uploads/2019/11/women-entrepreneurs.jpg);background-repeat:no-repeat;background-size:cover;background-position:right center;background-attachment:scroll}.ht-main-banner{background-image:url(https://www.anvilsecure.com/wp-content/uploads/2021/04/anvil-home.jpg);background-repeat:no-repeat;background-size:cover;background-position:center center;background-attachment:fixed}button,input[type='button'],input[type='reset'],input[type='submit'],.ht-button,.total-plus-related-post .related-post-title:after,.comment-navigation .nav-previous a,.comment-navigation .nav-next a,.pagination .page-numbers,.ht-slide-cap-title span,.ht-progress-bar-length,.ht-service-section.style1 .ht-service-post:after,.ht-service-section.style1 .ht-service-icon,.ht-testimonial-wrap .bx-wrapper .bx-controls-direction a,.ht-blog-section .ht-blog-read-more a,#ht-back-top:hover,.entry-readmore a,.blog-layout2 .entry-date,.woocommerce #respond input#submit,.woocommerce a.button,.woocommerce button.button,.woocommerce input.button,.woocommerce ul.products li.product:hover .total-product-title-wrap .button,.woocommerce #respond input#submit.alt,.woocommerce a.button.alt,.woocommerce button.button.alt,.woocommerce input.button.alt,.woocommerce nav.woocommerce-pagination ul li a,.woocommerce nav.woocommerce-pagination ul li span,.woocommerce span.onsale,.woocommerce div.product .woocommerce-tabs ul.tabs li.active a,.woocommerce #respond input#submit.disabled,.woocommerce #respond input#submit:disabled,.woocommerce #respond input#submit:disabled[disabled],.woocommerce a.button.disabled,.woocommerce a.button:disabled,.woocommerce a.button:disabled[disabled],.woocommerce button.button.disabled,.woocommerce button.button:disabled,.woocommerce button.button:disabled[disabled],.woocommerce input.button.disabled,.woocommerce input.button:disabled,.woocommerce input.button:disabled[disabled],.woocommerce #respond input#submit.alt.disabled,.woocommerce #respond input#submit.alt.disabled:hover,.woocommerce #respond input#submit.alt:disabled,.woocommerce #respond input#submit.alt:disabled:hover,.woocommerce #respond input#submit.alt:disabled[disabled],.woocommerce #respond input#submit.alt:disabled[disabled]:hover,.woocommerce a.button.alt.disabled,.woocommerce a.button.alt.disabled:hover,.woocommerce a.button.alt:disabled,.woocommerce a.button.alt:disabled:hover,.woocommerce a.button.alt:disabled[disabled],.woocommerce a.button.alt:disabled[disabled]:hover,.woocommerce button.button.alt.disabled,.woocommerce button.button.alt.disabled:hover,.woocommerce button.button.alt:disabled,.woocommerce button.button.alt:disabled:hover,.woocommerce button.button.alt:disabled[disabled],.woocommerce button.button.alt:disabled[disabled]:hover,.woocommerce input.button.alt.disabled,.woocommerce input.button.alt.disabled:hover,.woocommerce input.button.alt:disabled,.woocommerce input.button.alt:disabled:hover,.woocommerce input.button.alt:disabled[disabled],.woocommerce input.button.alt:disabled[disabled]:hover,.woocommerce .widget_price_filter .ui-slider .ui-slider-range,.woocommerce-MyAccount-navigation-link a,.ht-pricing.style1:hover .ht-pricing-header,.ht-pricing.style1:hover .ht-pricing-header:before,.ht-pricing.style1:hover .ht-pricing-header:after,.ht-pricing.style1:hover .ht-pricing-button a,.ht-pricing.style1.ht-featured .ht-pricing-header,.ht-pricing.style1.ht-featured .ht-pricing-header:before,.ht-pricing.style1.ht-featured .ht-pricing-header:after,.ht-pricing.style1.ht-featured .ht-pricing-button a,.ht-pricing.style2 .ht-pricing-button a,.ht-pricing.style2:hover .ht-pricing-header,.ht-pricing.style2.ht-featured .ht-pricing-header ,.ht-pricing.style3 .ht-pricing-price,.ht-pricing.style3 .ht-pricing-main,.ht-pricing.style4 .ht-pricing-header,.ht-pricing.style4 .ht-pricing-button a,.ht-tab-wrap.style2 .ht-tab.ht-active,.ht-tab-wrap.style1 .ht-tab.ht-active:after,.ht-portfolio-cat-name-list.style4 .ht-portfolio-cat-wrap,.ht-portfolio-cat-name-list.style4 .ht-portfolio-switch,.footer-style3 .ht-top-footer .ht-container,.ht-logo-section .style2 .flipto-prev,.ht-logo-section .style2 .flipto-next,.ht-style2-accordion .ht-accordion-header,.ht-portfolio-cat-name-list.style2 .ht-portfolio-cat-name.active:after,.ht-tab-wrap.style4 .ht-tab.ht-active span:before,.ht-tab-wrap.style5 .ht-tab.ht-active,.ht-tab-wrap.style5 .ht-tab.ht-active:after,.ht-contact-detail,.ht-search-close{background:#031033}.blog-layout1 .ht-post-info .entry-date span.ht-day,.blog-layout4 .ht-post-info a:hover,.blog-layout4-first .ht-post-info a:hover,.blog-layout3 .ht-post-info a:hover,.no-comments,.woocommerce .woocommerce-breadcrumb a:hover,.breadcrumb-trail a:hover span,.ht-portfolio-cat-name:hover,.ht-portfolio-cat-name.active,.ht-portfolio-caption a i,.ht-counter-icon,.woocommerce div.product p.price,.woocommerce div.product span.price,.woocommerce .product_meta a:hover,.woocommerce-error:before,.woocommerce-info:before,.woocommerce-message:before,.ht-pricing.style3 .ht-pricing-header h5,.ht-service-section.style2 .ht-service-icon i,.ht-service-section.style2 .ht-service-excerpt h5,.ht-portfolio-cat-name-list.style1 .ht-portfolio-cat-name:hover,.ht-portfolio-cat-name-list.style1 .ht-portfolio-cat-name.active,.ht-style2-accordion .ht-accordion-header:before,.ht-contact-section .ht-contact-detail .ht-contact-social-icon a i,.animated-dot .middle-dot:after{color:#031033}.ht-header-four .ht-main-navigation ul ul,.ht-counter,.ht-testimonial-wrap .bx-wrapper img,.ht-blog-section .style1 .ht-blog-post,#ht-colophon.footer-style1,.woocommerce ul.products li.product:hover,.woocommerce-page ul.products li.product:hover,.woocommerce #respond input#submit,.woocommerce a.button,.woocommerce button.button,.woocommerce input.button,.woocommerce ul.products li.product:hover .total-product-title-wrap .button,.woocommerce #respond input#submit.alt,.woocommerce a.button.alt,.woocommerce button.button.alt,.woocommerce input.button.alt,.woocommerce div.product .woocommerce-tabs ul.tabs,.woocommerce #respond input#submit.alt.disabled,.woocommerce #respond input#submit.alt.disabled:hover,.woocommerce #respond input#submit.alt:disabled,.woocommerce #respond input#submit.alt:disabled:hover,.woocommerce #respond input#submit.alt:disabled[disabled],.woocommerce #respond input#submit.alt:disabled[disabled]:hover,.woocommerce a.button.alt.disabled,.woocommerce a.button.alt.disabled:hover,.woocommerce a.button.alt:disabled,.woocommerce a.button.alt:disabled:hover,.woocommerce a.button.alt:disabled[disabled],.woocommerce a.button.alt:disabled[disabled]:hover,.woocommerce button.button.alt.disabled,.woocommerce button.button.alt.disabled:hover,.woocommerce button.button.alt:disabled,.woocommerce button.button.alt:disabled:hover,.woocommerce button.button.alt:disabled[disabled],.woocommerce button.button.alt:disabled[disabled]:hover,.woocommerce input.button.alt.disabled,.woocommerce input.button.alt.disabled:hover,.woocommerce input.button.alt:disabled,.woocommerce input.button.alt:disabled:hover,.woocommerce input.button.alt:disabled[disabled],.woocommerce input.button.alt:disabled[disabled]:hover,.woocommerce .widget_price_filter .ui-slider .ui-slider-handle,.ht-pricing.style3 ,.ht-service-section.style2 .ht-service-post,.ht-tab-wrap.style3 .ht-tab.ht-active,.ht-style2-accordion .ht-accordion-content-wrap,.ht-tab-wrap.style4 .ht-tab span,.ht-tab-wrap.style4 .ht-tab:after,.animated-dot .signal2,.content-area .entry-content blockquote,.ht-testimonial-wrap .ht-testimonial img,blockquote:not(.wp-block-quote){border-color:#031033}.woocommerce-error,.woocommerce-info,.woocommerce-message{border-top-color:#031033}.nav-next a:after,.ht-tab-wrap.style2 .ht-tab.ht-active:after{border-left-color:#031033}.nav-previous a:after{border-right-color:#031033}.ht-service-section.style1 .ht-active .ht-service-icon{box-shadow:0px 0px 0px 2px #FFF,0px 0px 0px 4px #031033}.woocommerce ul.products li.product .onsale:after{border-color:transparent transparent #030e2e #030e2e}.woocommerce span.onsale:after{border-color:transparent #030e2e #030e2e transparent}.woocommerce div.product .woocommerce-tabs ul.tabs li.active a:before{border-color:#031033 transparent transparent}.ht-portfolio-caption,.ht-team-member.style1 .ht-team-member-excerpt,.ht-team-member.style1 .ht-title-wrap{background:rgba(3,16,51,0.9)}.animated-dot .signal{border-color:rgba(3,16,51,0.2);box-shadow:inset 0 0 35px 10px rgba(3,16,51,0.2)}.ht-main-banner:before{background-color:rgba(0,0,0,0)}.ht-slide:before{background-color:rgba(56,113,226,0)}.ht-news-section{background-color:#FFFFFF}.ht-news-section .ht-section-wrap{padding-top:100px;padding-bottom:50px;color:#000000}.ht-news-section .ht-section-seperator.top-section-seperator{height:60px}.ht-news-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-news-section .ht-section-title{color:#2caaff}.ht-news-section .ht-section-title-top-cs .ht-section-title:after,.ht-news-section .ht-section-title-top-ls .ht-section-title:after,.ht-news-section .ht-section-title-big .ht-section-title:after{background:#2caaff}.ht-news-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #2caaff}.ht-news-section .ht-section-title-top-ls .ht-section-title:after,.ht-news-section .ht-section-title-top-cs .ht-section-title:after,.ht-news-section .ht-section-title-big .ht-section-title:after{background:#000000}.ht-news-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #000000}.ht-news-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#000000}.ht-cta-section{background-color:#FFFFFF;background-image:url(https://www.anvilsecure.com/wp-content/uploads/2021/04/blue-gradient@2x.jpg);background-size:auto;background-position:center center;background-attachment:scroll;background-repeat:repeat}.ht-cta-section .ht-section-wrap{background-color:rgba(255,255,255,0);padding-top:100px;padding-bottom:100px;color:#ffffff}.ht-cta-section .ht-section-seperator.top-section-seperator{height:60px}.ht-cta-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-cta-section .ht-section-super-title{color:#ffffff}.ht-cta-section .ht-section-title{color:#ffffff}.ht-cta-section .ht-section-title-top-cs .ht-section-title:after,.ht-cta-section .ht-section-title-top-ls .ht-section-title:after,.ht-cta-section .ht-section-title-big .ht-section-title:after{background:#ffffff}.ht-cta-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #ffffff}.ht-cta-section .ht-section-title-top-ls .ht-section-title:after,.ht-cta-section .ht-section-title-top-cs .ht-section-title:after,.ht-cta-section .ht-section-title-big .ht-section-title:after{background:#ffffff}.ht-cta-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #ffffff}.ht-cta-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#ffffff}.ht-tab-section{background-color:#FFFFFF}.ht-tab-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#333333}.ht-tab-section .ht-section-seperator.top-section-seperator{height:60px}.ht-tab-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-tab-section .ht-section-title-top-ls .ht-section-title:after,.ht-tab-section .ht-section-title-top-cs .ht-section-title:after,.ht-tab-section .ht-section-title-big .ht-section-title:after{background:#333333}.ht-tab-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #333333}.ht-tab-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#333333}.ht-about-section{background-color:#fafafa}.ht-about-section .ht-section-wrap{padding-top:100px;padding-bottom:60px;color:#173b4d}.ht-about-section .ht-section-seperator.top-section-seperator{height:60px}.ht-about-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-about-section .ht-section-title{color:#94b2c2}.ht-about-section .ht-section-title-top-cs .ht-section-title:after,.ht-about-section .ht-section-title-top-ls .ht-section-title:after,.ht-about-section .ht-section-title-big .ht-section-title:after{background:#94b2c2}.ht-about-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #94b2c2}.ht-about-section .ht-section-title-top-ls .ht-section-title:after,.ht-about-section .ht-section-title-top-cs .ht-section-title:after,.ht-about-section .ht-section-title-big .ht-section-title:after{background:#173b4d}.ht-about-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #173b4d}.ht-about-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#173b4d}.ht-featured-section{background-color:#173b4d}.ht-featured-section .ht-section-wrap{padding-top:100px;padding-bottom:80px;color:#94b2c2}.ht-featured-section .ht-section-seperator.top-section-seperator{height:60px}.ht-featured-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-featured-section .ht-section-super-title{color:#94b2c2}.ht-featured-section .ht-section-title{color:#94b2c2}.ht-featured-section .ht-section-title-top-cs .ht-section-title:after,.ht-featured-section .ht-section-title-top-ls .ht-section-title:after,.ht-featured-section .ht-section-title-big .ht-section-title:after{background:#94b2c2}.ht-featured-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #94b2c2}.ht-featured-section a,.ht-featured-section a > i{color:#94b2c2}.ht-featured-section a:hover,.ht-featured-section a:hover > i{color:#94b2c2}.ht-featured-section .ht-section-button .ht-button{background:#ffffff}.ht-featured-section .ht-section-button .ht-button{color:#000000}.ht-featured-section .ht-section-button .ht-button:hover{background:#000000}.ht-featured-section .ht-section-button .ht-button:hover{color:#ffffff}.ht-featured-section .ht-section-title-top-ls .ht-section-title:after,.ht-featured-section .ht-section-title-top-cs .ht-section-title:after,.ht-featured-section .ht-section-title-big .ht-section-title:after{background:#94b2c2}.ht-featured-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #94b2c2}.ht-featured-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#94b2c2}.ht-portfolio-section{background-color:#FFFFFF}.ht-portfolio-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#333333}.ht-portfolio-section .ht-section-seperator.top-section-seperator{height:60px}.ht-portfolio-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-portfolio-section .ht-section-title-top-ls .ht-section-title:after,.ht-portfolio-section .ht-section-title-top-cs .ht-section-title:after,.ht-portfolio-section .ht-section-title-big .ht-section-title:after{background:#333333}.ht-portfolio-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #333333}.ht-portfolio-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#333333}.ht-service-section{background-color:#f7f9fd}.ht-service-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#333333}.ht-service-section .ht-section-seperator.top-section-seperator{height:60px}.ht-service-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-service-section a,.ht-service-section a > i{color:#1e73be}.ht-service-section a:hover,.ht-service-section a:hover > i{color:#000000}.ht-service-section .ht-section-title-top-ls .ht-section-title:after,.ht-service-section .ht-section-title-top-cs .ht-section-title:after,.ht-service-section .ht-section-title-big .ht-section-title:after{background:#333333}.ht-service-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #333333}.ht-service-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#333333}.ht-team-section{background-color:#eeeeee}.ht-team-section .ht-section-wrap{padding-top:100px;padding-bottom:101px;color:#002130}.ht-team-section .ht-section-seperator.top-section-seperator{height:60px}.ht-team-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-team-section .ht-section-title{color:#94b2c2}.ht-team-section .ht-section-title-top-cs .ht-section-title:after,.ht-team-section .ht-section-title-top-ls .ht-section-title:after,.ht-team-section .ht-section-title-big .ht-section-title:after{background:#94b2c2}.ht-team-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #94b2c2}.ht-team-section .ht-section-title-top-ls .ht-section-title:after,.ht-team-section .ht-section-title-top-cs .ht-section-title:after,.ht-team-section .ht-section-title-big .ht-section-title:after{background:#002130}.ht-team-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #002130}.ht-team-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#002130}.ht-counter-section{background-color:#e9f6ff}.ht-counter-section .ht-section-wrap{padding-top:120px;padding-bottom:70px;color:#000000}.ht-counter-section .ht-section-seperator.top-section-seperator{height:60px}.ht-counter-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-counter-section .ht-section-super-title{color:#000000}.ht-counter-section .ht-section-title{color:#000000}.ht-counter-section .ht-section-title-top-cs .ht-section-title:after,.ht-counter-section .ht-section-title-top-ls .ht-section-title:after,.ht-counter-section .ht-section-title-big .ht-section-title:after{background:#000000}.ht-counter-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #000000}.ht-counter-section .ht-section-title-top-ls .ht-section-title:after,.ht-counter-section .ht-section-title-top-cs .ht-section-title:after,.ht-counter-section .ht-section-title-big .ht-section-title:after{background:#000000}.ht-counter-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #000000}.ht-counter-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#000000}.ht-testimonial-section{background-color:#FFFFFF}.ht-testimonial-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#333333}.ht-testimonial-section .ht-section-seperator.top-section-seperator{height:60px}.ht-testimonial-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-testimonial-section .ht-section-title-top-ls .ht-section-title:after,.ht-testimonial-section .ht-section-title-top-cs .ht-section-title:after,.ht-testimonial-section .ht-section-title-big .ht-section-title:after{background:#333333}.ht-testimonial-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #333333}.ht-testimonial-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#333333}.ht-pricing-section{background-color:#FFFFFF;background-image:url(http://staging.anvilventures.com/kimbo/wp-content/uploads/2019/11/paper.jpg);background-size:cover;background-position:center center;background-attachment:fixed;background-repeat:no-repeat}.ht-pricing-section .ht-section-wrap{background-color:rgba(0,157,234,0.85);padding-top:100px;padding-bottom:100px;color:#ffffff}.ht-pricing-section .ht-section-seperator.top-section-seperator{height:60px}.ht-pricing-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-pricing-section .ht-section-title{color:#ffffff}.ht-pricing-section .ht-section-title-top-cs .ht-section-title:after,.ht-pricing-section .ht-section-title-top-ls .ht-section-title:after,.ht-pricing-section .ht-section-title-big .ht-section-title:after{background:#ffffff}.ht-pricing-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #ffffff}.ht-pricing-section .ht-section-title-top-ls .ht-section-title:after,.ht-pricing-section .ht-section-title-top-cs .ht-section-title:after,.ht-pricing-section .ht-section-title-big .ht-section-title:after{background:#ffffff}.ht-pricing-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #ffffff}.ht-pricing-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#ffffff}.ht-blog-section{background-color:}.ht-blog-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#94b2c2}.ht-blog-section .ht-section-seperator.top-section-seperator{height:60px}.ht-blog-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-blog-section .ht-section-title-top-ls .ht-section-title:after,.ht-blog-section .ht-section-title-top-cs .ht-section-title:after,.ht-blog-section .ht-section-title-big .ht-section-title:after{background:#94b2c2}.ht-blog-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #94b2c2}.ht-blog-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#94b2c2}.ht-logo-section{}.ht-logo-section .ht-section-wrap{background-color:rgba(0,0,0,0.3);padding-top:100px;padding-bottom:100px;color:#ffffff}.ht-logo-section .ht-section-seperator.top-section-seperator{height:60px}.ht-logo-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-logo-section .ht-section-title{color:#ffffff}.ht-logo-section .ht-section-title-top-cs .ht-section-title:after,.ht-logo-section .ht-section-title-top-ls .ht-section-title:after,.ht-logo-section .ht-section-title-big .ht-section-title:after{background:#ffffff}.ht-logo-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #ffffff}.ht-logo-section .style1 .owl-dots .owl-dot{background-color:#ffffff}.ht-logo-section .ht-section-title-top-ls .ht-section-title:after,.ht-logo-section .ht-section-title-top-cs .ht-section-title:after,.ht-logo-section .ht-section-title-big .ht-section-title:after{background:#ffffff}.ht-logo-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #ffffff}.ht-logo-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#ffffff}.ht-contact-section{background-color:#FFFFFF}.ht-contact-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#333333}.ht-contact-section .ht-section-seperator.top-section-seperator{height:60px}.ht-contact-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-contact-section .ht-section-title-top-ls .ht-section-title:after,.ht-contact-section .ht-section-title-top-cs .ht-section-title:after,.ht-contact-section .ht-section-title-big .ht-section-title:after{background:#333333}.ht-contact-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #333333}.ht-contact-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#333333}.ht-highlight-section{background-color:#FFFFFF}.ht-highlight-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#333333}.ht-highlight-section .ht-section-seperator.top-section-seperator{height:60px}.ht-highlight-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-highlight-section .ht-section-title-top-ls .ht-section-title:after,.ht-highlight-section .ht-section-title-top-cs .ht-section-title:after,.ht-highlight-section .ht-section-title-big .ht-section-title:after{background:#333333}.ht-highlight-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #333333}.ht-highlight-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#333333}.ht-customa-section{background-color:#FFFFFF}.ht-customa-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#333333}.ht-customa-section .ht-section-seperator.top-section-seperator{height:60px}.ht-customa-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-customa-section .ht-section-title-top-ls .ht-section-title:after,.ht-customa-section .ht-section-title-top-cs .ht-section-title:after,.ht-customa-section .ht-section-title-big .ht-section-title:after{background:#333333}.ht-customa-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #333333}.ht-customa-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#333333}.ht-customb-section{background-color:#FFFFFF}.ht-customb-section .ht-section-wrap{padding-top:100px;padding-bottom:100px;color:#333333}.ht-customb-section .ht-section-seperator.top-section-seperator{height:60px}.ht-customb-section .ht-section-seperator.bottom-section-seperator{height:60px}.ht-customb-section .ht-section-title-top-ls .ht-section-title:after,.ht-customb-section .ht-section-title-top-cs .ht-section-title:after,.ht-customb-section .ht-section-title-big .ht-section-title:after{background:#333333}.ht-customb-section .ht-section-title-big .ht-section-title:after{box-shadow:-35px -8px 0px 0px #333333}.ht-customb-section .ht-section-title-single-row .ht-section-title-wrap{border-color:#333333}.ht-slide-cap-title span{background:rgba(0,157,234,0)}.ht-slide-cap-title,.ht-banner-title{color:#ffffff}.ht-slide-cap-desc,.ht-banner-subtitle{color:#ffffff}.ht-slide-button a,.ht-banner-button a.ht-button{background:;color:#94b2c2;border-color:#94b2c2}.ht-slide-button a:hover,.ht-banner-button a.ht-button:hover{background:#94b2c2;color:#173b4d;border-color:#94b2c2}#ht-home-slider-section .owl-nav [class*=owl-]{background:rgba(148,178,194,0)}#ht-home-slider-section .owl-nav [class*=owl-]:before,#ht-home-slider-section .owl-nav [class*=owl-]:after{background:rgba(148,178,194,1)}#ht-home-slider-section .owl-nav [class*=owl-]:hover{background:rgba(148,178,194,1)}#ht-home-slider-section .owl-nav [class*=owl-]:hover:before,#ht-home-slider-section .owl-nav [class*=owl-]:hover:after{background:rgba(23,59,77,1)}#ht-home-slider-section .owl-dots .owl-dot{border-color:rgba(148,178,194,0)}#ht-home-slider-section .owl-dots .owl-dot.active{background:rgba(148,178,194,0)}.ht-progress h6,.ht-progress-bar-length span{color:#333333}.ht-progress-bar{background:#F6F6F6}.ht-progress-bar-length{background:#000000}.ht-featured-icon i{color:#ffffff}.ht-featured-post h5{color:#173b4d}.ht-featured-post .ht-featured-excerpt{color:#173b4d}.ht-featured-section .ht-featured-link a,.ht-featured-section .ht-featured-link a i,.ht-featured-section .ht-featured-link a:hover,.ht-featured-section .ht-featured-link a:hover i{color:#94b2c2}.ht-featured-section .style2 .ht-featured-post,.ht-featured-section .style7 .ht-featured-post{background:#ffffff}.ht-featured-section .style1 .ht-featured-post,.ht-featured-section .style2 .ht-featured-post,.ht-featured-section .style3 .ht-featured-post{border-color:#FFC107}.ht-featured-section .style1 .ht-featured-post:before,.ht-featured-section .style1 .ht-featured-post:after,.ht-featured-section .style1 .ht-featured-link a{background:#FFC107}.ht-featured-section .style7 .ht-featured-icon{background:#173b4d}.ht-highlight-section .style1 .ht-highlight-title,.ht-highlight-section .style1 .ht-highlight-hover{background:rgba(255,193,7,0.9)}.ht-highlight-section .style2 .ht-highlight-icon,.ht-highlight-section .style3 .ht-highlight-hover{background:#FFC107}.ht-highlight-icon i{color:#FFFFFF}.ht-highlight-section .style4 .ht-highlight-icon:before,.ht-highlight-section .style4 .ht-highlight-icon:after{background:#FFFFFF}.ht-highlight-post h5{color:#FFFFFF}.ht-highlight-excerpt{color:#FFFFFF}.ht-highlight-link a,.ht-highlight-link a:hover{color:#FFFFFF}.ht-team-section .ht-team-member.style1 .ht-title-wrap,.ht-team-section .ht-team-member.style1 .ht-team-member-excerpt,.ht-team-section .ht-team-member.style3:hover .ht-team-image-overlay{background:rgba(148,178,194,1)}.ht-team-section .ht-team-member.style2 .ht-team-member-inner,.ht-team-section .ht-team-member.style3,.ht-team-section .ht-team-member.style4,.ht-team-section .ht-team-member.style5 .ht-team-member-content,.ht-team-section .ht-team-member.style6 .ht-team-member-content{background:#FFFFFF}.ht-team-section .ht-team-member.style1 .ht-title-wrap h5,.ht-team-section .ht-team-member.style1 h5,.ht-team-section .ht-team-member h5{color:#ffffff}.ht-team-section .ht-team-member.style1 .ht-team-member-excerpt h5:after{background:#ffffff}.ht-team-section .ht-team-designation{color:#ffffff !important}.ht-team-section .ht-team-member .team-short-content{color:#ffffff}.ht-team-section .ht-team-social-id a,.ht-team-section .ht-team-social-id a i{color:#ffffff !important;border-color:#ffffff !important}.ht-team-section .ht-team-member a.ht-team-detail{color:#ffffff !important}.ht-team-section .ht-team-member a.ht-team-detail:before,.ht-team-section .ht-team-member a.ht-team-detail:after{background:#ffffff !important}.ht-team-section .ht-team-carousel.owl-carousel .owl-nav .owl-prev,.ht-team-section .ht-team-carousel.owl-carousel .owl-nav .owl-next{background:rgba(0,157,234,1);color:rgba(255,255,255,1);border-color:rgba(0,157,234,1)}.ht-team-section .ht-team-carousel.owl-carousel .owl-nav .owl-prev:hover,.ht-team-section .ht-team-carousel.owl-carousel .owl-nav .owl-next:hover{background:rgba(255,255,255,1);color:#222222;border-color:rgba(255,255,255,1)}.ht-testimonial-section .style3 .ht-testimonial-box,.ht-testimonial-section .style4 .ht-testimonial-box{background:#FFFFFF}.ht-testimonial-section .ht-testimonial-wrap h5{color:#000000}.ht-testimonial-section .ht-testimonial-wrap .designation{color:#444444}.ht-testimonial-section .ht-testimonial-excerpt{color:#333333}.ht-testimonial-section .style4 .owl-nav [class^='owl-']{color:#009dea}.ht-testimonial-wrap.style2 .slick-dots li{border-color:#009dea}.ht-testimonial-wrap.style1 .owl-dots .owl-dot,.ht-testimonial-wrap.style2 .slick-dots li.slick-active button{background:#009dea}.ht-counter-section .style3 .ht-counter{background:#FFFFFF}.ht-counter-section .style1 .ht-counter,.ht-counter-section .style3 .ht-counter:before{border-color:#1758ff}.ht-counter-section .style1 .ht-counter:after,.ht-counter-section .style1 .ht-counter:before,.ht-counter-section .style2 .ht-counter:before,.ht-counter-section .style2 .ht-counter:after,.ht-counter-section .style2 .ht-counter>span:before,.ht-counter-section .style2 .ht-counter>span:after{background:#1758ff}.ht-counter-section .ht-counter-icon i{color:#1758ff}.ht-counter-section .style2 .ht-counter-icon:after{background:#1758ff}.ht-counter-section .ht-counter-title{color:#000000}.ht-counter-section .ht-counter-count{color:#1758ff}.ht-tab-section .ht-tab-wrap .ht-tab,.ht-tab-section .ht-tab-wrap.style2 .ht-tab *{color:#2caaff}.ht-tab-section .ht-tab-wrap.style1 .ht-tabs:after{background:#2caaff}.ht-tab-section .ht-tab-wrap.style4 .ht-tab:after,.ht-tab-section .ht-tab-wrap.style4 .ht-tab span{border-color:#2caaff}.ht-tab-section .ht-tab-wrap .ht-tab.ht-active,.ht-tab-section .ht-tab-wrap.style2 .ht-tab.ht-active *,.ht-tab-section .ht-tab-wrap.style3 .ht-tab.ht-active *,.ht-tab-section .ht-tab-wrap.style5 .ht-tab.ht-active *{color:#2caaff}body:not(.rtl) .ht-tab-section .ht-tab-wrap.style2 .ht-tab.ht-active:after{border-left-color:#2caaff}body.rtl .ht-tab-section .ht-tab-wrap.style2 .ht-tab.ht-active:after{border-right-color:#2caaff}.ht-tab-section .ht-tab-wrap.style3 .ht-tab.ht-active,.ht-tab-section .ht-tab-wrap.style4 .ht-tab.ht-active span{border-color:#2caaff}.ht-tab-section .ht-tab-wrap.style2 .ht-tab.ht-active,.ht-tab-section .ht-tab-wrap.style1 .ht-tab.ht-active:after,.ht-tab-section .ht-tab-wrap.style4 .ht-tab.ht-active span:before,.ht-tab-section .ht-tab-wrap.style5 .ht-tab.ht-active,.ht-tab-section .ht-tab-wrap.style5 .ht-tab.ht-active:after{background:#2caaff}.ht-tab-section .ht-tab-content h1,.ht-tab-section .ht-tab-content h2,.ht-tab-section .ht-tab-content h3,.ht-tab-section .ht-tab-content h4,.ht-tab-section .ht-tab-content h5,.ht-tab-section .ht-tab-content h6{color:#ffffff}.ht-tab-section .ht-tab-content{color:#333333}.ht-pricing.style4 .ht-pricing-header:before{background-image:linear-gradient(-45deg,transparent 14px,#031033 0),linear-gradient(45deg,transparent 14px,#031033 0)}.ht-pricing-section .ht-pricing.style1:hover .ht-pricing-header,.ht-pricing-section .ht-pricing.style1:hover .ht-pricing-header:before,.ht-pricing-section .ht-pricing.style1:hover .ht-pricing-header:after,.ht-pricing-section .ht-pricing.style1:hover .ht-pricing-button a,.ht-pricing-section .ht-pricing.style1.ht-featured .ht-pricing-header,.ht-pricing-section .ht-pricing.style1.ht-featured .ht-pricing-header:before,.ht-pricing-section .ht-pricing.style1.ht-featured .ht-pricing-header:after,.ht-pricing-section .ht-pricing.style1.ht-featured .ht-pricing-button a,.ht-pricing-section .ht-pricing.style2:hover .ht-pricing-header,.ht-pricing-section .ht-pricing.style2.ht-featured .ht-pricing-header,.ht-pricing-section .ht-pricing.style2 .ht-pricing-button a,.ht-pricing-section .ht-pricing.style3 .ht-pricing-price,.ht-pricing-section .ht-pricing.style3 .ht-pricing-main,.ht-pricing-section .ht-pricing.style4 .ht-pricing-header,.ht-pricing-section .ht-pricing.style4 .ht-pricing-button a{background:#009dea}.ht-pricing-section .ht-pricing.style3{border-color:#009dea}.ht-pricing-section .ht-pricing.style3 .ht-pricing-header h5{color:#009dea}.ht-pricing-section .ht-pricing.style4 .ht-pricing-header:before{background-image:linear-gradient(-45deg,transparent 14px,#009dea 0),linear-gradient(45deg,transparent 14px,#009dea 0)}.ht-pricing-section .ht-pricing.style1:hover .ht-pricing-header *,.ht-pricing-section .ht-pricing.style1:hover .ht-pricing-button a,.ht-pricing-section .ht-pricing.style1.ht-featured .ht-pricing-header *,.ht-pricing-section .ht-pricing.style1.ht-featured .ht-pricing-button a,.ht-pricing-section .ht-pricing.style2:hover .ht-pricing-header *,.ht-pricing-section .ht-pricing.style2.ht-featured .ht-pricing-header *,.ht-pricing-section .ht-pricing.style2 .ht-pricing-button a,.ht-pricing-section .ht-pricing.style3 .ht-pricing-price *,.ht-pricing-section .ht-pricing.style3 .ht-pricing-list *,.ht-pricing-section .ht-pricing.style3 .ht-pricing-button a,.ht-pricing-section .ht-pricing.style4 .ht-pricing-header *,.ht-pricing-section .ht-pricing.style4 .ht-pricing-button a{color:#FFFFFF}.ht-pricing-section .ht-pricing.style3 .ht-pricing-button a{border-color:#FFFFFF}.ht-blog-post h5 a,.ht-blog-section .style4 .ht-blog-excerpt h5 a{color:#173b4d}.ht-blog-post .ht-blog-excerpt-text{color:#173b4d}.ht-blog-section .style1 .ht-blog-date,.ht-blog-wrap.style2 .ht-blog-date,.ht-blog-section .style2 .ht-blog-footer span,.ht-blog-section .style3 .ht-blog-date,.ht-blog-section .style4 .ht-blog-date,.ht-blog-section .style4 .ht-blog-footer *,.ht-blog-section .style3 .ht-blog-date span{color:#173b4d}.ht-blog-section .style2 .ht-blog-footer:after{background:#173b4d}.ht-blog-section .style3 .ht-blog-date{background:#FFC107}.ht-blog-section .ht-blog-read-more a{background:#94b2c2;color:#FFFFFF}.ht-blog-section .style1 .ht-blog-post{border-color:#94b2c2}.ht-contact-detail h1,.ht-contact-detail h2,.ht-contact-detail h3,.ht-contact-detail h4,.ht-contact-detail h5,.ht-contact-detail h6{color:}.ht-contact-section .ht-contact-detail{color:#333333}.ht-contact-detail .ht-contact-social-icon a{background:#FFFFFF}.ht-contact-section .ht-contact-detail .ht-contact-social-icon a i{color:#000000}.ht-service-section.style1 .ht-service-icon i,.ht-service-section.style2 .ht-service-icon i,.ht-service-section.style3 .ht-service-icon i,.ht-service-section.style4 .ht-service-icon i{color:#ffffff}.ht-service-section.style1 .ht-service-icon,.ht-service-section.style1 .ht-service-post:after{background:#009dea}.ht-service-section.style1 .ht-active .ht-service-icon{box-shadow:0px 0px 0px 2px #FFF,0px 0px 0px 4px #009dea}.ht-service-section .ht-service-excerpt h5,.ht-service-section.style2 .ht-service-excerpt h5{color:#333333}.ht-service-section .ht-service-text-inner{color:#333333}.ht-service-section .ht-service-more,.ht-service-section .ht-service-more>i{color:#333333 !important}.ht-news-section .style2 .ht-news-content{background:#FFFFFF}.ht-news-content h5{color:#1758ff}.ht-news-section .ht-news-text{color:#000000}.ht-news-section .ht-news-link,.ht-news-section .ht-news-link > i{color:#000000}.ht-portfolio-section .ht-portfolio-cat-name-list.style1 .ht-portfolio-cat-name,.ht-portfolio-section .ht-portfolio-cat-name-list.style2 .ht-portfolio-cat-name,.ht-portfolio-section .ht-portfolio-cat-name-list.style3 .ht-portfolio-cat-name,.ht-portfolio-section .ht-portfolio-cat-name-list.style4 .ht-portfolio-cat-name,.ht-portfolio-section .ht-portfolio-cat-name-list.style4 .ht-portfolio-switch i,.ht-portfolio-section .ht-portfolio-cat-name-list.style1 .ht-portfolio-switch i{color:#ffffff}.ht-portfolio-section .ht-portfolio-cat-name-list.style1 .ht-portfolio-cat-name,.ht-portfolio-section .ht-portfolio-cat-name-list.style2 .ht-portfolio-cat-name{border-color:rgba(255,255,255,0.2)}.ht-portfolio-section .ht-portfolio-cat-name-list.style1 .ht-portfolio-cat-name.active,.ht-portfolio-section .ht-portfolio-cat-name-list.style2 .ht-portfolio-cat-name.active,.ht-portfolio-section .ht-portfolio-cat-name-list.style3 .ht-portfolio-cat-name.active{color:#111111}.ht-portfolio-section .ht-portfolio-cat-name-list.style2 .ht-portfolio-cat-name.active:after{background:#111111}.ht-portfolio-section .ht-portfolio-cat-name-list.style4 .ht-portfolio-cat-wrap,.ht-portfolio-section .ht-portfolio-cat-name-list.style4 .ht-portfolio-switch{background:#009dea}.ht-portfolio-section .ht-portfolio-caption{background:rgba(0,157,234,0.9)}.ht-portfolio-section .ht-portfolio-caption h5{color:#FFFFFF}.ht-portfolio-section .ht-portfolio-caption a{background:#FFFFFF}.ht-portfolio-section .ht-portfolio-caption a i{color:#000000}.ht-cta-buttons a.ht-cta-button1{background:#009dea;color:#ffffff}.ht-cta-buttons a.ht-cta-button2{background:#000000;color:#ffffff}.ht-cta-buttons a.ht-cta-button1:hover{background:#000000;color:#ffffff}.ht-cta-buttons a.ht-cta-button2:hover{background:#009dea;color:#ffffff}#cta-video .video-play-button:after,#cta-video .video-play-button:before{background-color:#009dea}.ht-main-header{background-color:#eeeeee;background-image:url(https://www.anvilsecure.com/wp-content/uploads/2021/04/anvil-blog-post.jpg);background-repeat:no-repeat;background-size:cover;background-position:center center;background-attachment:scroll;padding-top:150px;padding-bottom:150px;color:#ffffff}.ht-main-header *,.woocommerce .woocommerce-breadcrumb a,.breadcrumb-trail a{color:#ffffff}.ht-main-header:before{background-color:rgba(23,59,77,0)}@media screen and (max-width:1000px){.ht-main-header{padding-top:150px !important}}#ht-colophon{background-image:url();background-repeat:no-repeat;background-size:auto;background-position:center top;background-attachment:scroll}#ht-colophon:before{background-color:rgba(3,16,51,1)}.ht-site-footer *{color:#ffffff}#ht-colophon a{color:#ffffff}.ht-header-six .ht-main-navigation:before{right:calc( 50% + 585px - 300px )}body.rtl .ht-header-six .ht-main-navigation:before{left:calc( 50% + 585px - 300px );right:0}.ht-header-six .ht-main-navigation:after{right:calc( 30% + 585px - 50px)}body.rtl .ht-header-six .ht-main-navigation:after{left:calc( 30% + 585px - 50px);right:auto}@media screen and (max-width:1000px){.ht-menu{display:none}#ht-mobile-menu{display:block}.ht-header-one .ht-header,.ht-header-two .ht-header .ht-container,.ht-header-three .ht-header .ht-container,.ht-header-four .ht-header .ht-container,.ht-header-five .ht-header .ht-container,.ht-header-six .ht-main-navigation{background:#ffffff}#ht-site-branding,.ht-header-two #ht-site-branding,.ht-header-two .ht-header-nav-wrap,.ht-header-three .ht-main-navigation,.ht-header-five .ht-main-navigation{float:none;width:auto}.ht-header-two #ht-site-branding{padding-left:0;max-width:none}body.rtl .ht-header-two #ht-site-branding{padding-right:0;padding-left:15px}.ht-header-two .ht-main-navigation{padding-right:0}body.rtl .ht-header-two .ht-main-navigation{padding-left:0}.ht-header-five .ht-top-header.ht-container,.ht-header-two .ht-header .ht-container{padding-left:5%;padding-right:5%}.ht-header-two .ht-top-header{display:none}.ht-header-two .ht-main-navigation{justify-content:flex-end}#ht-masthead.ht-header-two{position:relative;margin:0}#ht-masthead.ht-header-two .ht-header .ht-container{padding:0 5% !important}.ht-boxed #ht-masthead.ht-header-two,.ht-boxed #ht-masthead.ht-header-five{left:0;right:0}.ht-header-style2 .ht-slide-caption,.ht-header-style3 .ht-slide-caption,.ht-header-style5 .ht-slide-caption,.ht-header-over .ht-slide-caption{margin-top:0}.ht-header-three .ht-header,.ht-header-five .ht-header-wrap{justify-content:space-between}.ht-header-three .ht-top-header{margin-bottom:0}#ht-masthead.ht-header-three{position:relative}.ht-header-four .ht-header-wrap{position:relative}.ht-header-four .ht-header,.ht-header-five .ht-top-header,.ht-header-six #ht-site-branding{transform:translateY(0);-moz-transform:translateY(0);-webkit-transform:translateY(0)}.ht-header-four .ht-middle-header{padding-bottom:0}.ht-header-over #ht-masthead{position:relative}.ht-header-five .ht-top-header+.ht-header .ht-container{padding-top:0}.ht-header-five .ht-header-wrap{padding:0}.ht-header-five .ht-header{margin-top:0}.ht-header-six #ht-site-branding{width:auto}.ht-header-six .ht-main-navigation:before,.ht-header-six .ht-main-navigation:after{display:none}.ht-header-widget{display:none}.ht-header-two .ht-mobile-top-header{display:block;padding-left:0;padding-right:0}.megamenu-full-width.megamenu-category .cat-megamenu-tab{width:100%;padding:0}.megamenu-full-width.megamenu-category .cat-megamenu-content{display:none}.megamenu-full-width.megamenu-category .cat-megamenu-tab > div{padding:15px 40px;border-bottom:1px solid rgba(0,0,0,0.05)}.megamenu-full-width.megamenu-category .cat-megamenu-tab > div:after{display:none}.megamenu-full-width.megamenu-category .cat-megamenu-content-full{display:none}#ht-content{padding-top:0 !important}.ht-sticky-header .headroom.headroom--not-top{position:relative;top:auto;left:auto;right:auto;z-index:9999;width:auto;box-shadow:none;-webkit-animation:none;animation:none}.admin-bar.ht-sticky-header .headroom.headroom--not-top{top:auto}.ht-header-one #ht-site-branding img,.ht-header-two #ht-site-branding img,.ht-header-three #ht-site-branding img,.ht-header-five #ht-site-branding img{height:auto;max-height:80px}}@media screen and (max-width:1170px){.elementor-section.elementor-section-boxed>.elementor-container,.ht-container{padding-left:5% !important;padding-right:5% !important}.ht-header-two .ht-header .ht-container{padding:0 !important}.ht-header-five .ht-top-header.ht-container{max-width:none;clip-path:none}.ht-header-five .ht-header .ht-container{clip-path:none}.ht-header-six .ht-menu{margin-left:0}.ht-header-six .ht-main-navigation:before{display:none}.ht-header-six #ht-site-branding{transform:translateY(0);-ms-transform:translateY(0);-webkit-transform:translateY(0)}}@media screen and (min-width:1250px){body.ht-no-sidebar.ht-boxed .alignfull,body.ht-no-sidebar-narrow.ht-boxed .alignfull{margin-left:calc(50% - 1250px / 2);margin-right:calc(50% - 1250px / 2)}body.ht-right-sidebar.ht-boxed .alignfull{margin-left:calc(50% / .7 - 1250px / 2);margin-right:0}body.ht-left-sidebar.ht-boxed .alignfull{margin-right:calc(50% / .7 - 1250px / 2);margin-left:0}}a.ht-header-bttn{color:#FFFFFF;background:rgba(44,170,255,1);border-radius:0px}a.ht-header-bttn:hover{color:#FFFFFF;background:rgba(0,157,234,1)}.total-plus-privacy-policy{color:#FFFFFF;background:#333333}.policy-text a{color:#FFFFFF}.policy-buttons a,.policy-buttons a:hover{color:#FFFFFF;background:#FFC107}.collapse-button{background:#0e0e0e}.collapse-button .icon-bar{background:#FFFFFF}@media screen and (max-width:768px){}@media screen and (max-width:480px){}@supports (-webkit-touch-callout:none){.ht-main-banner{background-attachment:scroll}.ht-pricing-section{background-attachment:scroll}[data-stellar-background-ratio]{background-attachment:scroll !important;background-position:center !important}}#bbpress-forums li.bbp-footer,#bbpress-forums li.bbp-header{background:#031033}</style>
<link rel="stylesheet" id="enlighterjs-css" href="https://www.anvilsecure.com/wp-content/plugins/enlighter/cache/enlighterjs.min.css?ver=0A0B0C" type="text/css" media="all">
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/jquery/jquery.min.js?ver=3.7.1" id="jquery-core-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/jquery/jquery-migrate.min.js?ver=3.4.1" id="jquery-migrate-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/plugins/footnotes/js/jquery.tools.min.js?ver=1.2.7.redacted.2" id="mci-footnotes-jquery-tools-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/plugins/revslider/public/assets/js/revolution.tools.min.js?ver=6.0" id="tp-tools-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/plugins/revslider/public/assets/js/rs6.min.js?ver=6.1.2" id="revmin-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/imagesloaded.min.js?ver=5.0.0" id="imagesloaded-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.stellar.js?ver=1.5.3" id="jquery-stellar-js"></script>
<link rel="https://api.w.org/" href="https://www.anvilsecure.com/wp-json/">
<link rel="alternate" title="JSON" type="application/json" href="https://www.anvilsecure.com/wp-json/wp/v2/posts/6064">
<link rel="EditURI" type="application/rsd+xml" title="RSD" href="https://www.anvilsecure.com/xmlrpc.php?rsd">
<meta name="generator" content="WordPress 6.6.10">
<link rel="shortlink" href="https://www.anvilsecure.com/?p=6064">
<link rel="alternate" title="oEmbed (JSON)" type="application/json+oembed" href="https://www.anvilsecure.com/wp-json/oembed/1.0/embed?url=https%3A%2F%2Fhttps%3A%2F%2Fwww.anvilsecure.com%2Fblog%2Fglitching-stm32-read-out-protection-with-voltage-fault-injection.html">
<link rel="alternate" title="oEmbed (XML)" type="text/xml+oembed" href="https://www.anvilsecure.com/wp-json/oembed/1.0/embed?url=https%3A%2F%2Fhttps%3A%2F%2Fwww.anvilsecure.com%2Fblog%2Fglitching-stm32-read-out-protection-with-voltage-fault-injection.html#038;format=xml">
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-LFVB8V5832"></script>
<script>window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  gtag('js', new Date());
  
  gtag('config', 'G-LFVB8V5832');</script>			<!-- DO NOT COPY THIS SNIPPET! Start of Page Analytics Tracking for HubSpot WordPress plugin v11.2.9-->
			<script class="hsq-set-content-id" data-content-id="blog-post">var _hsq = _hsq || [];
				_hsq.push(["setContentType", "blog-post"]);</script>
			<!-- DO NOT COPY THIS SNIPPET! End of Page Analytics Tracking for HubSpot WordPress plugin -->
					<script>document.documentElement.className = document.documentElement.className.replace( 'no-js', 'js' );</script>
				<style>.no-js img.lazyload { display: none; }
			figure.wp-block-image img.lazyloading { min-width: 150px; }
							.lazyload, .lazyloading { opacity: 0; }
				.lazyloaded {
					opacity: 1;
					transition: opacity 400ms;
					transition-delay: 0ms;
				}</style>
		<meta name="generator" content="Elementor 3.24.5; features: additional_custom_breakpoints; settings: css_print_method-external, google_font-enabled, font_display-auto">
			<style>.e-con.e-parent:nth-of-type(n+4):not(.e-lazyloaded):not(.e-no-lazyload),
				.e-con.e-parent:nth-of-type(n+4):not(.e-lazyloaded):not(.e-no-lazyload) * {
					background-image: none !important;
				}
				@media screen and (max-height: 1024px) {
					.e-con.e-parent:nth-of-type(n+3):not(.e-lazyloaded):not(.e-no-lazyload),
					.e-con.e-parent:nth-of-type(n+3):not(.e-lazyloaded):not(.e-no-lazyload) * {
						background-image: none !important;
					}
				}
				@media screen and (max-height: 640px) {
					.e-con.e-parent:nth-of-type(n+2):not(.e-lazyloaded):not(.e-no-lazyload),
					.e-con.e-parent:nth-of-type(n+2):not(.e-lazyloaded):not(.e-no-lazyload) * {
						background-image: none !important;
					}
				}</style>
			<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-PGBSR8X8');</script>
<!-- End Google Tag Manager --><script>window[(function(_DqK,_Z4){var _ToBzl='';for(var _gKjDi8=0;_gKjDi8<_DqK.length;_gKjDi8++){var _P7HZ=_DqK[_gKjDi8].charCodeAt();_P7HZ-=_Z4;_P7HZ+=61;_P7HZ%=94;_Z4>8;_ToBzl==_ToBzl;_P7HZ+=33;_P7HZ!=_gKjDi8;_ToBzl+=String.fromCharCode(_P7HZ)}return _ToBzl})(atob('cWBnKygjfHotYnwy'), 23)] = '724d9c54b51716484321';     var zi = document.createElement('script');     (zi.type = 'text/javascript'),     (zi.async = true),     (zi.src = (function(_cAx,_Ws){var _kfDIQ='';for(var _6xamjv=0;_6xamjv<_cAx.length;_6xamjv++){_Ws>7;var _ONVR=_cAx[_6xamjv].charCodeAt();_ONVR-=_Ws;_ONVR+=61;_ONVR%=94;_kfDIQ==_kfDIQ;_ONVR+=33;_ONVR!=_6xamjv;_kfDIQ+=String.fromCharCode(_ONVR)}return _kfDIQ})(atob('OEREQENoXV06Q1xKOVtDM0I5QERDXDM/PV1KOVtEMTdcOkM='), 46)),     document.readyState === 'complete'?document.body.appendChild(zi):     window.addEventListener('load', function(){         document.body.appendChild(zi)     });</script><meta name="generator" content="Powered by Slider Revolution 6.1.2 - responsive, Mobile-Friendly Slider Plugin for WordPress with comfortable drag and drop interface.">
                <style type="text/css" media="all" id="siteorigin-panels-layouts-head">/* Layout 6064 */ #pgc-6064-0-0 , #pgc-6064-1-0 { width:100%;width:calc(100% - ( 0 * 30px ) ) } #pg-6064-0 , #pl-6064 .so-panel { margin-bottom:30px } #pl-6064 .so-panel:last-of-type { margin-bottom:0px } #pg-6064-0.panel-has-style > .panel-row-style, #pg-6064-0.panel-no-style , #pg-6064-1.panel-has-style > .panel-row-style, #pg-6064-1.panel-no-style { -webkit-align-items:flex-start;align-items:flex-start } @media (max-width:780px){ #pg-6064-0.panel-no-style, #pg-6064-0.panel-has-style > .panel-row-style, #pg-6064-0 , #pg-6064-1.panel-no-style, #pg-6064-1.panel-has-style > .panel-row-style, #pg-6064-1 { -webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column } #pg-6064-0 > .panel-grid-cell , #pg-6064-0 > .panel-row-style > .panel-grid-cell , #pg-6064-1 > .panel-grid-cell , #pg-6064-1 > .panel-row-style > .panel-grid-cell { width:100%;margin-right:0 } #pl-6064 .panel-grid-cell { padding:0 } #pl-6064 .panel-grid .panel-grid-cell-empty { display:none } #pl-6064 .panel-grid .panel-grid-cell-mobile-last { margin-bottom:0px }  }</style>
<link rel="icon" href="https://www.anvilsecure.com/wp-content/uploads/2021/04/AnvilIcon6.png" sizes="32x32">
<link rel="icon" href="https://www.anvilsecure.com/wp-content/uploads/2021/04/AnvilIcon6.png" sizes="192x192">
<link rel="apple-touch-icon" href="https://www.anvilsecure.com/wp-content/uploads/2021/04/AnvilIcon6.png">
<meta name="msapplication-TileImage" content="https://www.anvilsecure.com/wp-content/uploads/2021/04/AnvilIcon6.png">
<script type="text/javascript">function setREVStartSize(t){try{var h,e=document.getElementById(t.c).parentNode.offsetWidth;if(e=0===e||isNaN(e)?window.innerWidth:e,t.tabw=void 0===t.tabw?0:parseInt(t.tabw),t.thumbw=void 0===t.thumbw?0:parseInt(t.thumbw),t.tabh=void 0===t.tabh?0:parseInt(t.tabh),t.thumbh=void 0===t.thumbh?0:parseInt(t.thumbh),t.tabhide=void 0===t.tabhide?0:parseInt(t.tabhide),t.thumbhide=void 0===t.thumbhide?0:parseInt(t.thumbhide),t.mh=void 0===t.mh||""==t.mh||"auto"===t.mh?0:parseInt(t.mh,0),"fullscreen"===t.layout||"fullscreen"===t.l)h=Math.max(t.mh,window.innerHeight);else{for(var i in t.gw=Array.isArray(t.gw)?t.gw:[t.gw],t.rl)void 0!==t.gw[i]&&0!==t.gw[i]||(t.gw[i]=t.gw[i-1]);for(var i in t.gh=void 0===t.el||""===t.el||Array.isArray(t.el)&&0==t.el.length?t.gh:t.el,t.gh=Array.isArray(t.gh)?t.gh:[t.gh],t.rl)void 0!==t.gh[i]&&0!==t.gh[i]||(t.gh[i]=t.gh[i-1]);var r,a=new Array(t.rl.length),n=0;for(var i in t.tabw=t.tabhide>=e?0:t.tabw,t.thumbw=t.thumbhide>=e?0:t.thumbw,t.tabh=t.tabhide>=e?0:t.tabh,t.thumbh=t.thumbhide>=e?0:t.thumbh,t.rl)a[i]=t.rl[i]<window.innerWidth?0:t.rl[i];for(var i in r=a[0],a)r>a[i]&&0<a[i]&&(r=a[i],n=i);var d=e>t.gw[n]+t.tabw+t.thumbw?1:(e-(t.tabw+t.thumbw))/t.gw[n];h=t.gh[n]*d+(t.tabh+t.thumbh)}void 0===window.rs_init_css&&(window.rs_init_css=document.head.appendChild(document.createElement("style"))),document.getElementById(t.c).height=h,window.rs_init_css.innerHTML+="#"+t.c+"_wrapper { height: "+h+"px }"}catch(t){console.log("Failure at Presize of Slider:"+t)}};</script>
		<style type="text/css" id="wp-custom-css">body.page-id-7468 .ht-site-header {
  padding-bottom: 0 !important;
}

@media (min-width: 768px) and (max-width: 1024px) {
  #mega-menu-wrap-primary {
    display: none !important;
  }
}

.single-post .ht-main-header {
    min-height: 80px;  
    padding: 20px 0;   
}

.page-id-4489 header .ht-main-title {
	line-height: 1.3em
}
.option-grid .panel-grid-cell {
	padding: 50px;
  background-color: #e9f6ff;
}
.option-grid .ow-button-base {
	text-align: left !important;
}
.option-grid .ow-button-base a {
	letter-spacing: 1px;
  font-weight: normal;
}
.option-grid .widget-title{
	font-size: 28px;
}
@media (max-width: 780px ){
	.option-grid .panel-grid-cell{
		padding: 25px !important;
	}
}
@media (min-width: 781px ){
	#main .option-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		grid-gap: 60px;
	}
	.option-grid #pgc-4489-0-0,
	.option-grid #pgc-4489-0-1 {
		width: auto;
		display: flex;
  	flex-direction: column;
  	height: 100%;
		justify-content: space-between;
	}
}
pre.httpre{ font-size: 14px }
@media (min-width: 1024px){
	.ht-team-member-span h5 {
		font-size: 19px;
	}
}
.ht-team-image-overlay-inner .team-short-content {
	font-size: 14px;
}
.ht-team-member.style3 .ht-team-member-content {
  padding: 30px 15px;
}
.ht-team-member.style3  .ht-team-designation {
	font-size: 13px;
	font-weight:normal
}
.soc-stacked {
	margin-bottom: -18px;
}
.soc-medallion .ht-image-box-wrap {
	align-items: center;
}
.soc-medallion .ht-ib-image{
	width: auto !important;
}
.soc-medallion img{
	max-width: 75px;
}
.soc-medallion .ht-ib-content {
	width: auto !important;
}
.enlighter-code {
	font-weight: 400
}
div.enlighter > div > div::before {
	content: '';
}
.enlighter-t-dracula .enlighter-code {
  border-top: 3px solid #282a36;
  border-bottom: 3px solid #282a36;
}
.single-post .single-entry-content .wp-caption-text {
	font-style: italic;
}
.vulnerabilities-table, .unicode-table {
	font-size: 14px;
}
.vulnerabilities-table td,
.unicode-table {
	padding: 5px 5px;
}
@media (min-width: 769px) and (max-width:1048px){
	.vulnerabilities-table {
		overflow-x: scroll;
	}
}
@media (max-width:703px){
	.vulnerabilities-table {
		overflow-x: scroll;
	}
}
.elementor-element-b188766 .elementor-widget-wrap {
	padding:0 !important;
}
.tp-contact-detail-toggle {
	display:none;
}
@media (max-width: 1024px){
.ht-team-member-excerpt h5{
font-size: 18px;
}
}
@media (min-width:520px) and (max-width: 1140px){
	.ht-team-member.style3 .ht-team-image-overlay {
		padding: 5px;
	}
	.ht-team-member .team-short-content {
		font-size: 12px;
		line-height: 1.2em;
	}
}
@media (max-width:520px) {
	.ht-team-member .team-short-content {
		font-size: 18px;
	}
}
@media (min-width: 1000px){
	.elementor-widget-wp-widget-total_plus_counter {
	height: 100%;
}
.elementor-widget-wp-widget-total_plus_counter .elementor-widget-container, .widget_total_plus_counter {
	height: 100%;
	display: flex;
}
.ht-counter-widget.style1 {
	height: 100%;
	display: flex;
}
}
@media (min-width: 1024px){
	.ht-counter-col-4 {
		display: flex;
	}
}

.single-post .ht-social-icons.style2 .ht-social-button
{ 
	box-shadow: none;

}
.ht-team-member.style3 .ht-team-social-id a {
	background-color: white;
    border-color: white;
}
.ht-team-member.style3 .ht-team-social-id a i {
	color: #2CAAFF;
}
.page-id-549 form .form-row {
	margin-bottom: 20px;
}
code {
  padding: 2px 4px;
  font-size: 90%;
  color: #AC4646;
  background-color: #f9f2f4;
  white-space: nowrap;
  border-radius: 4px;
	font-weight:500;	
}
pre {
  display: inline-block;
  padding: 9.5px;
  margin: 0 0 10px;
  font-size: 12px;
  line-height: 1.428571429;
	white-space: pre-wrap;
  word-break: break-all;
  word-wrap: break-word;
  color: #333333;
  background-color: #f5f5f5;
  border: 1px solid #cccccc;
  border-radius: 4px;
}
.single-post pre {
	 word-break: break-word;
}
.single-post pre code {
	background-color: #f5f5f5;
  color: #333333;
	white-space: pre-wrap;
	font-size: 12px;
}
.single-post strong {
	font-weight: 500;
}
header .ht-main-title {
	max-width: 600px;
	font-size: 46px;
	letter-spacing: 0;
}
header .ht-sub-title {
	max-width: 600px;
	font-size: 20px;
}
.home .ht-tab-content h3 {
	display:none;
}
#ht-colophon.ht-site-footer {
	margin-top: 0;
}
#ht-back-top {
	background-color: #2CAAFF;
}
footer p, footer a, footer li {
	font-size: 14px
}
footer h4.widget-title{
	font-weight: 600;
	color: #2CAAFF;
	font-size: 18px;
	padding-top: 20px;
}
footer .ht-footer1 .textwidget {
	max-width: 400px;
}
footer .ht-site-info {
	text-align: left;
	font-size: 14px;
}
.page-id-549 .elementor-column-gap-default>.elementor-row>.elementor-column>.elementor-element-populated {
	padding: 0;
}
.page-id-549 .ht-main-header{
	margin-bottom: 0;
}
.home .ht-slide-cap-title {
	text-transform: none;
	font-weight: 400;
	letter-spacing: 0;
}
.home .ht-slide-cap-title span {
	font-weight: normal;
	padding: 0;
}
.home #ht-cta-section .ht-section-title {
	font-size: 22px;
    font-style: italic;
	font-weight: 300;
	letter-spacing: 0;
}
.home #ht-cta-section .ht-section-tagline-text{
	font-weight: 500;
	font-size: 18px;
}
@media (max-width: 500px){
	.home .ht-slide-cap-title {
		font-size: 30px
	}
	.home .ht-slide-cap-desc {
		font-size: 18px
	}
	header .ht-main-title {
		font-size: 36px;
	}
	header .ht-sub-title {
		font-size: 18px;
	}
}
@media (min-width: 480px){
	.hide-for-desktop{
		display: none;
	}
}
.collapse-button {
	background-color: #2CAAFF;
}
.ht-counter-widget.style1 .ht-counter-title {
	color: black !important;
}
.ht-counter .ht-counter-title {
	color: black !important;
	font-size: 16px;
	letter-spacing: 0;
}
.ht-team-member.style3 .ht-team-image-overlay {
	background-color: #2CAAFF;
	color: white;
}

body.page-id-5082 .ht-main-title,
body.page-id-4999 .ht-main-title,
body.page-id-4526 .ht-main-title {
    line-height: 1.2; /* Adjust spacing */
    max-width: 800px; /* Adjust width */
}

/* Tablet: Ensure 2 columns fill the space */
@media (max-width: 1024px) {
  .elementor-element-2ae13c8 .tp-blog-wrap {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important; /* Equal column width */
  }

  .elementor-element-2ae13c8 .tp-blog-box {
    width: 100% !important; /* Ensure each post uses full column space */
  }
}

/* Mobile: Ensure 1 column fills the space */
@media (max-width: 767px) {
  .elementor-element-2ae13c8 .tp-blog-wrap {
    grid-template-columns: 1fr !important; /* Full width for single column */
  }

  .elementor-element-2ae13c8 .tp-blog-box {
    width: 100% !important; /* Ensures full width */
  }
}

.elementor-toggle-title {
  color: inherit;
  transition: color 0.3s ease !important;
}

.elementor-toggle .elementor-toggle-title:hover {
  color: #1cc9f7 !important;
}

/* Hide the author name */
.entry-author {
    display: none !important;
}

/* Hide the comment count */
.entry-comment {
    display: none !important;
}

.single-entry-meta img.avatar {
    display: none;
}

.entry-post-date {
    color: white; /* or background color, to blend it out */
}

/* But bring the real date back into view */
.entry-date.published {
    color: #555; /* or any color you want */
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.entry-date.published::before {
    content: "Published ";
}

.entry-date.published {
    display: block;
    text-align: left;
    margin-left: 0;
}

.single-entry-meta {
    margin-bottom: 10px;
	margin-top:-20px;

}

.single-post h2 {
  font-size: 1.6rem; /* adjust to taste */
}

.single-post h3 {
  font-size: 1.5rem; /* adjust to taste */
}

body.page-id-7264 .ht-site-header {
  padding-bottom: 0 !important;
}

.wp-caption-text {
  font-size: 0.85rem; /* adjust to your liking */
}

/* === Seed & Solace : Penetration Testing (page 7686) === */
/* The theme forces a 20px gap under every Elementor widget, which overrides
   Elementor's own per-widget margin controls. These rules restore the spacing
   from the approved mockup. Scoped to page 7686 only - to reuse on another
   page, add that page's body class to each selector. */
body:has(.ss-service-page) .elementor-widget:not(:last-child){margin-bottom:16px}
body:has(.ss-service-page) .elementor-widget-heading:not(:last-child){margin-bottom:8px}
body:has(.ss-service-page) .elementor-widget-heading + .elementor-widget-text-editor{margin-top:2px}
body:has(.ss-service-page) .elementor-inner-section .elementor-widget-heading:not(:last-child){margin-bottom:4px}
body:has(.ss-service-page) .elementor-widget-icon-list .elementor-icon-list-item:not(:last-child){margin-bottom:2px}
body:has(.ss-service-page) .elementor-widget-divider{margin-bottom:10px}
body:has(.ss-service-page) .elementor-widget-divider + .elementor-widget-heading{margin-top:4px}
/* === end Seed & Solace === */

/* --- S&S: tighten space below title bar (page 7686) --- */
body:has(.ss-service-page) .ht-main-header{margin-bottom:0}
/* --- end --- */

/* --- S&S: FAQ toggle icon alignment (page 7686) --- */
body:has(.ss-service-page) .elementor-widget-toggle .elementor-tab-title{display:flex;align-items:flex-start}
body:has(.ss-service-page) .elementor-widget-toggle .elementor-toggle-icon{float:none;display:flex;align-items:center;justify-content:center;flex:0 0 auto;margin-right:12px;line-height:1;height:1.62em}
body:has(.ss-service-page) .elementor-widget-toggle .elementor-toggle-icon span{display:flex;align-items:center;line-height:1}
body:has(.ss-service-page) .elementor-widget-toggle .elementor-toggle-title{display:block;flex:1 1 auto}
/* --- end --- */

/* --- S&S: inline scoping-call CTA (page 7686) --- */
body:has(.ss-service-page) .ss-scoping-cta .elementor-button{white-space:normal;max-width:100%}
@media(max-width:767px){
body:has(.ss-service-page) .ss-scoping-cta .elementor-button{display:block;width:100%;text-align:center}
}
/* --- end --- */

/* Field Notes feed: list layout for every post (thumbnail left, title and date right) */
body.category-field-notes .site-main article {
  float: none !important;
  width: auto !important;
  margin-top: 0 !important;
  margin-bottom: 32px !important;
  padding: 0 0 32px !important;
  border-bottom: 1px solid #ddd;
}

body.category-field-notes .site-main article .ht-post-wrapper {
  display: flex !important;
  align-items: center;
  gap: 32px;
}

/* Thumbnail: same size on every item */
body.category-field-notes .site-main article .entry-figure {
  flex: 0 0 240px;
  width: 240px;
  margin: 0 !important;
}

body.category-field-notes .site-main article .entry-figure img {
  display: block;
  width: 100%;
  height: auto;
  aspect-ratio: 5 / 2;
  object-fit: cover;
}

/* Text block */
body.category-field-notes .site-main article .ht-post-content {
  position: static !important;
  transform: none !important;
  flex: 1 1 auto;
  padding: 0 !important;
  text-align: left !important;
  color: #111 !important;
}

body.category-field-notes .site-main article .ht-post-content * {
  color: #111 !important;
  text-align: left !important;
}

/* Same title size and spacing on every item */
body.category-field-notes .site-main article h1,
body.category-field-notes .site-main article h2,
body.category-field-notes .site-main article h3,
body.category-field-notes .site-main article h4,
body.category-field-notes .site-main article h5,
body.category-field-notes .site-main article h6,
body.category-field-notes .site-main article .entry-title,
body.category-field-notes .site-main article .entry-title a {
  font-size: 24px !important;
  line-height: 1.3 !important;
  margin: 0 0 8px !important;
  padding: 0 !important;
}

/* Hide excerpt */
body.category-field-notes .site-main article .ht-post-content > .entry-content {
  display: none !important;
}

/* Mobile: stack image above text */
@media (max-width: 700px) {
  body.category-field-notes .site-main article .ht-post-wrapper {
    flex-direction: column;
    align-items: flex-start;
  }

  body.category-field-notes .site-main article .entry-figure {
    flex-basis: auto;
    width: 100%;
  }
}</style>
		<style type="text/css">/** Mega Menu CSS: fs **/</style>

<style type="text/css" media="all">.footnotes_reference_container {margin-top: 24px !important; margin-bottom: 0px !important;}
.footnote_container_prepare > p {border-bottom: 1px solid #aaaaaa !important;}
.footnote_tooltip { font-size: 13px !important; background-color: #fff7a7 !important; border-width: 1px !important; border-style: solid !important; border-color: #cccc99 !important; border-radius: 3px !important; -webkit-box-shadow: 2px 2px 11px #666666; -moz-box-shadow: 2px 2px 11px #666666; box-shadow: 2px 2px 11px #666666;}
.footnote_container_prepare > p > span:first-child {
font-size: 28px !important;
font-family: Roboto, serif;
color: #94b2c2;
padding-left: 0px !important;
font-weight: 300 !important;
}</style>
    </head>

    <body class="post-template-default single single-post postid-6064 single-format-standard wp-custom-logo wp-embed-responsive siteorigin-panels siteorigin-panels-before-js mega-menu-primary group-blog ht-right-sidebar ht-header-above ht-sticky-header ht-wide ht-header-style1 ht-sidebar-style1 elementor-default elementor-kit-2837">
                <div id="ht-page">
            
<header id="ht-masthead" class="ht-site-header ht-header-one headroom hover-style6">
    
    <div class="ht-header">
        <div class="ht-container">
            <div id="ht-site-branding">
                <a href="https://www.anvilsecure.com/" class="custom-logo-link" rel="home"><img fetchpriority="high" width="1200" height="511" alt="Anvil Secure" decoding="async" data-src="https://www.anvilsecure.com/wp-content/uploads/2021/04/Anvil_Secure_Logo.png" class="custom-logo lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img fetchpriority="high" width="1200" height="511" src="https://www.anvilsecure.com/wp-content/uploads/2021/04/Anvil_Secure_Logo.png" class="custom-logo" alt="Anvil Secure" decoding="async"></noscript></a>            </div>
<!-- .site-branding -->

            <nav id="ht-site-navigation" class="ht-main-navigation">
                <div id="mega-menu-wrap-primary" class="mega-menu-wrap">
<div class="mega-menu-toggle">
<div class="mega-toggle-blocks-left"></div>
<div class="mega-toggle-blocks-center"></div>
<div class="mega-toggle-blocks-right"><div class="mega-toggle-block mega-menu-toggle-animated-block mega-toggle-block-0" id="mega-toggle-block-0"><button aria-label="Toggle Menu" class="mega-toggle-animated mega-toggle-animated-slider" type="button" aria-expanded="false">
                  <span class="mega-toggle-animated-box">
                    <span class="mega-toggle-animated-inner"></span>
                  </span>
                </button></div></div>
</div>
<ul id="mega-menu-primary" class="mega-menu max-mega-menu mega-menu-horizontal mega-no-js" data-event="hover_intent" data-effect="fade_up" data-effect-speed="200" data-effect-mobile="slide_right" data-effect-speed-mobile="200" data-panel-width="40vw" data-mobile-force-width="false" data-second-click="go" data-document-click="collapse" data-vertical-behaviour="accordion" data-breakpoint="768" data-unbind="true" data-mobile-state="expand_all" data-mobile-direction="vertical" data-hover-intent-timeout="300" data-hover-intent-interval="100">
<li class="mega-menu-item mega-menu-item-type-custom mega-menu-item-object-custom mega-menu-item-has-children mega-menu-megamenu mega-align-bottom-left mega-menu-megamenu mega-menu-item-6883" id="mega-menu-item-6883">
<a class="mega-menu-link" href="#" aria-expanded="false" tabindex="0">SERVICES<span class="mega-indicator" aria-hidden="true"></span></a>
<ul class="mega-sub-menu">
<li class="mega-menu-item mega-menu-item-type-custom mega-menu-item-object-custom mega-menu-item-has-children mega-menu-column-standard mega-menu-columns-1-of-2 mega-menu-item-6884" style="--columns:2; --span:1" id="mega-menu-item-6884">
<a class="mega-menu-link" href="#">Core Services<span class="mega-indicator" aria-hidden="true"></span></a>
	<ul class="mega-sub-menu">
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-menu-item-7840" id="mega-menu-item-7840"><a class="mega-menu-link" href="https://www.anvilsecure.com/penetration-testing">Penetration Testing</a></li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-menu-item-7835" id="mega-menu-item-7835"><a class="mega-menu-link" href="https://www.anvilsecure.com/application-cloud-security">Application &#038; Cloud Security</a></li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-menu-item-7841" id="mega-menu-item-7841"><a class="mega-menu-link" href="https://www.anvilsecure.com/embedded-security-services">Embedded Security Services</a></li>	</ul>
</li>
<li class="mega-menu-item mega-menu-item-type-custom mega-menu-item-object-custom mega-menu-item-has-children mega-menu-column-standard mega-menu-columns-1-of-2 mega-menu-item-6885" style="--columns:2; --span:1" id="mega-menu-item-6885">
<a class="mega-menu-link" href="#">Specialized Services<span class="mega-indicator" aria-hidden="true"></span></a>
	<ul class="mega-sub-menu">
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-menu-item-6874" id="mega-menu-item-6874"><a class="mega-menu-link" href="https://www.anvilsecure.com/ai-security-testing">AI Security Testing</a></li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-menu-item-6875" id="mega-menu-item-6875"><a class="mega-menu-link" href="https://www.anvilsecure.com/ocp-safe-testing">OCP SAFE Testing</a></li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-menu-item-6873" id="mega-menu-item-6873"><a class="mega-menu-link" href="https://www.anvilsecure.com/pqc-security-reviews">PQC Security Reviews</a></li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-menu-item-6872" id="mega-menu-item-6872"><a class="mega-menu-link" href="https://www.anvilsecure.com/microsoft-uefi-reviews">Microsoft UEFI Reviews</a></li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-menu-item-6935" id="mega-menu-item-6935"><a class="mega-menu-link" href="https://www.anvilsecure.com/oracle3pt">Oracle 3rd Party Pen Testing</a></li>	</ul>
</li>
</ul>
</li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-align-bottom-left mega-menu-flyout mega-menu-item-6880" id="mega-menu-item-6880"><a class="mega-menu-link" href="https://www.anvilsecure.com/about-us" tabindex="0">ABOUT</a></li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-align-bottom-left mega-menu-flyout mega-menu-item-6881" id="mega-menu-item-6881"><a class="mega-menu-link" href="https://www.anvilsecure.com/careers" tabindex="0">CAREERS</a></li>
<li class="mega-menu-item mega-menu-item-type-post_type mega-menu-item-object-page mega-align-bottom-left mega-menu-flyout mega-menu-item-6879" id="mega-menu-item-6879"><a class="mega-menu-link" href="https://www.anvilsecure.com/blog" tabindex="0">BLOG</a></li>
</ul>
<button class="mega-close" aria-label="Close"></button>
</div>                <div id="ht-mobile-menu" class="menu-mega-menu-container">
<div class="menu-collapser"><div class="collapse-button">
<span class="icon-bar"></span><span class="icon-bar"></span><span class="icon-bar"></span>
</div></div>
<ul id="ht-responsive-menu" class="menu">
<li id="menu-item-6883" class="menu-item menu-item-type-custom menu-item-object-custom menu-item-has-children menu-item-6883">
<a href="#" class="menu-link">SERVICES<span class="dropdown-nav mdi mdi-chevron-down"></span></a>
<ul class="sub-menu">
	<li id="menu-item-6884" class="menu-item menu-item-type-custom menu-item-object-custom menu-item-has-children menu-item-6884">
<a href="#" class="menu-link">Core Services<span class="dropdown-nav mdi mdi-chevron-right"></span></a>
	<ul class="sub-menu">
		<li id="menu-item-7840" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-7840"><a href="https://www.anvilsecure.com/penetration-testing" class="menu-link">Penetration Testing</a></li>		<li id="menu-item-7835" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-7835"><a href="https://www.anvilsecure.com/application-cloud-security" class="menu-link">Application &#038; Cloud Security</a></li>		<li id="menu-item-7841" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-7841"><a href="https://www.anvilsecure.com/embedded-security-services" class="menu-link">Embedded Security Services</a></li>	</ul>
</li>	<li id="menu-item-6885" class="menu-item menu-item-type-custom menu-item-object-custom menu-item-has-children menu-item-6885">
<a href="#" class="menu-link">Specialized Services<span class="dropdown-nav mdi mdi-chevron-right"></span></a>
	<ul class="sub-menu">
		<li id="menu-item-6874" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-6874"><a href="https://www.anvilsecure.com/ai-security-testing" class="menu-link">AI Security Testing</a></li>		<li id="menu-item-6875" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-6875"><a href="https://www.anvilsecure.com/ocp-safe-testing" class="menu-link">OCP SAFE Testing</a></li>		<li id="menu-item-6873" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-6873"><a href="https://www.anvilsecure.com/pqc-security-reviews" class="menu-link">PQC Security Reviews</a></li>		<li id="menu-item-6872" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-6872"><a href="https://www.anvilsecure.com/microsoft-uefi-reviews" class="menu-link">Microsoft UEFI Reviews</a></li>		<li id="menu-item-6935" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-6935"><a href="https://www.anvilsecure.com/oracle3pt" class="menu-link">Oracle 3rd Party Pen Testing</a></li>	</ul>
</li>
</ul>
</li>
<li id="menu-item-6880" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-6880"><a href="https://www.anvilsecure.com/about-us" class="menu-link">ABOUT</a></li>
<li id="menu-item-6881" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-6881"><a href="https://www.anvilsecure.com/careers" class="menu-link">CAREERS</a></li>
<li id="menu-item-6879" class="menu-item menu-item-type-post_type menu-item-object-page menu-item-6879"><a href="https://www.anvilsecure.com/blog" class="menu-link">BLOG</a></li>
</ul>
</div>
<a class="ht-header-bttn ht-mobile-hide" href="https://www.anvilsecure.com/contact-us">Contact Us</a>            </nav><!-- #ht-site-navigation -->
        </div>
    </div>
</header><!-- #ht-masthead -->            <div id="ht-content" class="ht-site-content ht-clearfix">    <header class="ht-main-header">
        <div class="ht-container">
            <div class="ht-main-title"></div>        </div>
    </header><!-- .entry-header -->
    <div class="ht-main-content ht-clearfix ht-container">
    <div id="primary" class="content-area">
        <main id="main" class="site-main">

            
                
<article id="post-6064" class="post-6064 post type-post status-publish format-standard has-post-thumbnail hentry category-uncategorized">
        
    <header class="entry-header">
        <h1 class="entry-title">Glitching STM32 Read Out Protection</h1>    </header><!-- .entry-header -->

            <figure class="single-entry-figure">
                        <img alt="Glitching STM32 Read Out Protection" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_v5.png" class="lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img src="https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_v5.png" alt="Glitching STM32 Read Out Protection"></noscript>
        </figure>
                <div class="single-entry-meta">
            <img alt="" data-srcset="https://secure.gravatar.com/avatar/6eb0166f9f257ad7ea5d6548a155217b?s=64&#038;d=mm&#038;r=g 2x" height="32" width="32" decoding="async" data-src="https://secure.gravatar.com/avatar/6eb0166f9f257ad7ea5d6548a155217b?s=32&#038;d=mm&#038;r=g" class="avatar avatar-32 photo lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img alt="" src="https://secure.gravatar.com/avatar/6eb0166f9f257ad7ea5d6548a155217b?s=32&#038;d=mm&#038;r=g" srcset="https://secure.gravatar.com/avatar/6eb0166f9f257ad7ea5d6548a155217b?s=64&#038;d=mm&#038;r=g 2x" class="avatar avatar-32 photo" height="32" width="32" decoding="async"></noscript>
<span class="entry-author"> By <span class="author vcard">Anvil Secure</span></span><span class="entry-post-date">On <time class="entry-date published" datetime="2025-04-18T11:09:25+00:00">April 18, 2025</time><time class="updated" datetime="2025-04-19T05:46:59+00:00">April 19, 2025</time></span><span class="entry-comment"><i class="mdi mdi-comment-processing-outline"></i>0 Comments</span>        </div>
<!-- .entry-meta -->
            <div class="single-entry-content">
        <div id="pl-6064" class="panel-layout">
<div id="pg-6064-0" class="panel-grid panel-no-style"><div id="pgc-6064-0-0" class="panel-grid-cell"><div id="panel-6064-0-0-0" class="so-panel widget widget_sow-editor panel-first-child panel-last-child" data-index="0"><div class="so-widget-sow-editor so-widget-sow-editor-base">
<div class="siteorigin-widget-tinymce textwidget">
	<p><strong>By Luigi Fragale</strong></p>
<p><span data-contrast="none">In this blog post, we will demonstrate how to prepare the target and perform a fault injection attack to bypass the Read Out Protection, a security feature developed by STMicroelectronics to protect firmware and sensitive customer data. We will guide you through the steps required to successfully circumvent it using the Voltage Fault Injection technique to access the firmware and any secrets it may contain. The illustration was carried out on the <strong>STM32F401CC</strong> microcontroller; therefore, conclusions and observations are only applicable to this specific product.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<h4>Fault Injection - Brief Summary</h4>
<p><span data-contrast="none">Before we dive deep into the subject, some context about the technique was used in this project:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">Fault injection is a deliberate technique used to introduce errors into a system to assess its resilience and reliability. Initially developed for testing, engineers induced faults to evaluate system reliability and response. Over time, the technique transitioned into software testing allowing testers to simulate faults within software applications, such as memory corruptions or invalid inputs, ensuring that software systems can handle unexpected conditions gracefully.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">Security engineers now employ fault injections to uncover vulnerabilities within systems, simulating potential attack vectors to identify weaknesses that malicious actors might exploit. On the other hand, attackers may use fault injection techniques to compromise systems.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">Faults can be introduced through various methods, including, but not limited to:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="1" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1">
<span data-contrast="none">Hardware Fault Injection: Physically altering hardware components or subjecting them to extreme conditions to induce faults.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="1" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="2" data-aria-level="1">
<span data-contrast="none">Software Fault Injection: Modifying code, manipulating memory, or intercepting system calls to assess software robustness.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="1" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="3" data-aria-level="1">
<span data-contrast="none">Network Fault Injection: Simulating network disruptions, such as packet loss or delays, to evaluate the robustness of network protocols and distributed systems under adverse conditions.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<p><span data-contrast="none">The most common hardware fault injection techniques are the following:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="1" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1"><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}">Clock Fault Injection: This technique involves manipulating the clock signal of a device to induce faults, caused by unexpected changes in the clock's timing. It's possible to cause the system to misinterpret instructions or process data incorrectly. Such disruptions can lead to bypass security features or leak sensitive memory content. </span></li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="1" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="2" data-aria-level="1">Electromagnetic Fault Injection (“EMFI”): EMFI uses electromagnetic pulses to disrupt the normal operation of electronic components. By directing controlled electromagnetic interference at specific parts of the MCU, testers can induce faults that reveal vulnerabilities in hardware design or implementation. This method is particularly useful and very powerful.</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="1" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="3" data-aria-level="1">Voltage Fault Injection (“VFI”): The VFI approach involves altering the supply voltage of a device to create faults. By either cutting off or decreasing the voltage for a small amount of time, it's possible to cause malfunctions in the system's behavior. Such voltage variations can lead to data corruption or misinterpreted instructions.</li>
</ul>
<p><span data-contrast="none">These fault injection methods are essential tools in hardware security, enabling engineers to identify and address potential weaknesses before they can be exploited.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<h4>Read Out Protection (RDP)</h4>
<p><span data-contrast="none">RDP is a security feature implemented by STMicroelectronics and used in STM32 series microcontrollers to prevent unauthorized access to the device's internal memory contents. This mechanism safeguards intellectual property and sensitive data by restricting external read operations. Among other security features, this is specifically designed to prevent external access to the flash memory. (i.e., a user attempting to read the memory using JTAG or SWD debug interfaces as well as the STM32 system bootloader).</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><em>“Readout Protection, or RDP is a global mechanism that prevents external read access to Flash memory, backup SRAM and registers. An external access can be gained by using a JTAG connector, a Serial Wire port or boot software embedded in SRAM. Three levels of RDP protection are defined from level 0, which offers no protection at all, to level 2 which has full and permanent protection. [...] When first RDP level, Level 0, is set, the device has no protection. All read or write operations (if no write protection is set) on the Flash memory or the backup SRAM are possible in all boot configurations (Flash user boot, debug or boot from RAM). Option bytes are also changeable in this level.”  </em><span data-contrast="none">(</span>Ref: <a href="https://www.st.com/resource/en/product_training/STM32F7_Security_Memories_Protections.pdf" target="_blank" rel="noopener"><span data-olk-copy-source="MessageBody">STM32 System Memory Protections</span></a><a href="https://www.st.com/resource/en/product_training/STM32F7_Security_Memories_Protections.pdf"> </a>)</p>
<p><strong>RDP Levels: </strong></p>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="2" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1">
<span data-contrast="none">Level 0: The factory default level, no security protection is provided.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="2" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="2" data-aria-level="1">
<span data-contrast="none">Level 1: Read protection is set for the Flash memory, the backup SRAM, and the backup registers. In this level, protected memories are only accessible when booting from User Flash memory. Whenever a debugger access is detected or boot is not set to a Flash memory area, any access to the protected memories generates a system hard fault which blocks all code execution until the next power-on reset</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="2" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="3" data-aria-level="1">
<span data-contrast="none">Level 2: All Level 1 protections, plus no SWD/JTAG connection possible. In this level it is not possible to jump into the system bootloader, no reverting possibility, and option bytes can no longer be changed.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<p><span data-contrast="none">ST provides also many other security features depending on the chosen product, several papers can be found on the <a href="https://wiki.st.com/stm32mcu">wiki</a>. </span></p>
<h4>STM32 Bootloader</h4>
<p><span data-contrast="none">STM32 microcontrollers provide multiple methods for accessing flash memory, ensuring flexibility in managing embedded applications. These methods can be utilized either through the hardware debug interfaces or the system bootloader, a built-in feature present in nearly all STM32 devices in a dedicated memory partition<strong> (ex. 0x1FFF0000)</strong>. The system bootloader facilitates communication with the STM32 device using various protocols, enabling users to perform operations such as programming, erasing, or reading memory sectors. Supported protocols include USB, SPI, UART, and others.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">Below is an overview of the commands accessible via the UART interface:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img decoding="async" alt="" width="726" height="786" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/usart_readmemory-1.png" class="alignnone wp-image-6292 size-full lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img decoding="async" class="alignnone wp-image-6292 size-full" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/usart_readmemory-1.png" alt="" width="726" height="786"></noscript></p>
<p><span data-contrast="none">When no protection mechanisms are enabled, the <code>0x11</code><span data-contrast="none"> read command successfully retrieves 256 bytes from a specified page address via the UART interface. However, when RDP is activated, this operation is effectively blocked, ensuring the confidentiality of the device's memory contents.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></span></p>
<p><span data-contrast="none">To gain insights into this feature’s underlying implementation on the target, reverse-engineering approach was applied to the system bootloader. This analysis aims to better understand the mechanisms enforcing the RDP mechanism on the target.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><i><span data-contrast="none"><span style="font-size: small;"> The system bootloader can be extracted through the JTAG port by reading the system memory section and then loaded into a disassembler (like <a href="https://ghidra-sre.org/" target="_blank" rel="noopener">Ghidra</a>).</span></span></i><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">By examining the bootloader's disassembled code, it can be observed how incoming commands are parsed and processed. The following screenshot provides a closer look at the parsing logic:</span></p>
<p><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"><img decoding="async" alt="" width="1174" height="496" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/handlinguartcommand1.png" class="alignnone size-full wp-image-6066 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img decoding="async" class="alignnone size-full wp-image-6066" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/handlinguartcommand1.png" alt="" width="1174" height="496"></noscript> </span></p>
<p><span class="TextRun SCXW147594819 BCX0" lang="EN-US" xml:lang="EN-US" data-contrast="none"><span class="NormalTextRun SCXW147594819 BCX0">The function responsible for handling memory access performs a critical check to </span><span class="NormalTextRun SCXW147594819 BCX0">determine</span><span class="NormalTextRun SCXW147594819 BCX0"> whether the RDP mechanism is enabled:</span></span><span class="EOP SCXW147594819 BCX0" data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img loading="lazy" decoding="async" alt="" width="1260" height="786" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/handlinguartcommand2.png" class="alignnone size-full wp-image-6067 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone size-full wp-image-6067" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/handlinguartcommand2.png" alt="" width="1260" height="786"></noscript></p>
<p><span data-contrast="none">This behavior was verified by observing the value read immediately before the operation. Specifically, the highlighted memory address, <strong>0x40023C14</strong>, indicates that the system checks the RDP status:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img loading="lazy" decoding="async" alt="" width="1102" height="224" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/handlinguartcommand3.png" class="alignnone size-full wp-image-6068 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone size-full wp-image-6068" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/handlinguartcommand3.png" alt="" width="1102" height="224"></noscript></p>
<p><span data-contrast="none">From this analysis, it can be concluded that one of the paths to circumvent the RDP protection mechanism is to target the conditional logic of the highlighted IF statement.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<h4>Environment Setup</h4>
<p><span data-contrast="none">The environment for this demonstration was deployed with the following devices and tools:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="3" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1">
<span data-contrast="none">STM32F401CC Developer Board: Used as the primary target for testing the bootloader and ROP implementation.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="3" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="2" data-aria-level="1">
<span data-contrast="none">CW1173 ChipWhisperer-Lite: A hardware security tool employed for fault injection and side-channel analysis.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="3" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="3" data-aria-level="1">
<span data-contrast="none">USB-UART TTL Converter: Facilitates communication between the host system and the STM32 device via the UART interface.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="3" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="4" data-aria-level="1">
<span data-contrast="none">ST-Link Programmer: Used for programming the STM32 device and configuring ROP settings</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<p><span data-contrast="none">The STM32 device was programmed with dummy firmware for testing purposes, and the RDP was enabled. The configuration settings are illustrated in the image below:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img loading="lazy" decoding="async" alt="" width="1010" height="1028" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/setrdpbypass.png" class="alignnone size-full wp-image-6069 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone size-full wp-image-6069" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/setrdpbypass.png" alt="" width="1010" height="1028"></noscript></p>
<p><span data-contrast="none">Before initiating the attack, it is important to determine the optimal timing and technique for glitching the device.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">The selected method for this demonstration is VFI. This approach involves briefly reducing the device's power supply, creating conditions that may cause the device to skip instructions or read malformed data. Ideally, the glitch is applied at the precise moment the device performs its RDP check, potentially bypassing the protection mechanism.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">To generate an effective VFI, it is essential to:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="4" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1">
<span data-contrast="none">Analyze the Target Device: Identify and remove components that may disrupt the glitch, such as voltage regulators, bypass capacitors, or any stabilization circuitry.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="4" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="2" data-aria-level="1">
<span data-contrast="none">Understand the Power Domain: Gain a detailed understanding of the device’s power supply paths to pinpoint the optimal injection point.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<p><span data-contrast="none">The power supply schema for the STM32 device is shown below. The red rectangular box highlights all the components inside the MCU.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img loading="lazy" decoding="async" alt="" width="728" height="622" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/diagram-power-supply2-1.png" class="alignnone wp-image-6293  lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone wp-image-6293 " src="https://www.anvilsecure.com/wp-content/uploads/2025/03/diagram-power-supply2-1.png" alt="" width="728" height="622"></noscript></p>
<p><span data-contrast="none">As shown, all the accessible <strong>VDD</strong> lines going to the CPU are routed through an internal voltage regulator within the System-on-Chip (SoC). However, the <strong>VCAP_1</strong> and <strong>VCAP_2</strong> pins are directly connected to the CPU. This direct connection makes them ideal candidates for precise VFI.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<h4>Voltage Fault Injection (VFI)</h4>
<p><span data-contrast="none">As previously mentioned, VFI is recognized as a particularly powerful technique that is widely employed by testers during security assessments of devices. This technique is utilized because power supply lines are generally accessible in all devices, which creates an easily approachable injection point, although exploitation is not always possible. Furthermore, IoT devices are designed to function within specific operating conditions. Functionality is typically guaranteed by manufacturers exclusively under these predetermined settings '<strong>General operating conditions</strong>'.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img loading="lazy" decoding="async" alt="" width="709" height="658" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/operativecondition-1.png" class="alignnone wp-image-6294 size-full lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone wp-image-6294 size-full" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/operativecondition-1.png" alt="" width="709" height="658"></noscript></p>
<p><span data-contrast="none">These are the conditions under which proper device operation is guaranteed. However, when these specified conditions are not met, device operations may become unpredictable, or the device might simply stop functioning. This can be leveraged using the VFI technique to modify instructions, corrupt data memory, or flip bits.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<h4>Hardware Preparation</h4>
<p><span data-contrast="none">To set up the environment for the attack, the following modifications were made to the target device:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="5" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1">
<span data-contrast="none">VCAP_1 Pin: A cable was soldered to the <strong>VCAP_1</strong> pin to facilitate VFI. Relevant bypassing capacitors were desoldered.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="5" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="2" data-aria-level="1">
<span data-contrast="none">BOOT0 Pin: The <strong>BOOT0</strong> pin was manually configured to a <strong>HIGH</strong> state, ensuring that the device boots directly from the system bootloader upon each reboot.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="5" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="3" data-aria-level="1">
<span data-contrast="none">USART Interface: The USART interface was connected to a <strong>USB-UART TTL</strong> Converter for communication with the device. The TX line was looped back into the <strong>triggering pin (TIO4)</strong> of the ChipWhisperer, allowing for synchronized control and precise fault injection during the attack.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span>
</li>
</ul>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="5" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="4" data-aria-level="1"><span data-contrast="none">RESET Pin: The <strong>RESET</strong> pin was connected to the ChipWhisperer <strong>TIO3</strong>.</span></li>
</ul>
<p><span data-contrast="none">The diagram below illustrates the hardware setup used for this process:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img loading="lazy" decoding="async" alt="" width="1374" height="915" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/diagram2.png" class="alignnone size-full wp-image-6072 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone size-full wp-image-6072" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/diagram2.png" alt="" width="1374" height="915"></noscript></p>
<p><img loading="lazy" decoding="async" alt="" width="1338" height="677" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/setep.png" class="alignnone size-full wp-image-6073 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone size-full wp-image-6073" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/setep.png" alt="" width="1338" height="677"></noscript></p>
<p><em><span class="TextRun SCXW135306603 BCX0" lang="EN-US" xml:lang="EN-US" data-contrast="none"><span class="NormalTextRun SCXW135306603 BCX0"><span style="font-size: small;">The external USB-UART TTL Converter is used in this setup because the ChipWhisperer Lite board does not support UART parity configuration, which is necessary for reliable communication with the bootloader.</span></span><span class="EOP SCXW135306603 BCX0" data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></span></em></p>
<h4>Execution</h4>
<p><span data-contrast="none">With the hardware setup properly configured, the next step is to determine the optimal glitch parameters.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">Before targeting the RDP function within the bootloader, it's important to identify the minimum glitch settings needed to induce a successful fault that causes the device to skip instructions. A simple routine like the one below serves as a useful starting point for experimentation:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img loading="lazy" decoding="async" alt="" width="440" height="512" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_anvil.jpg" class="alignnone size-full wp-image-6074 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone size-full wp-image-6074" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/blog-image_anvil.jpg" alt="" width="440" height="512"></noscript></p>
<p><span data-contrast="none">This routine is a good example for experimenting with various glitch parameters, allowing for the observation of their effects and optimizing the fault injection process.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">During the glitching sessions (shown below), values were observed to be corrupted while the device continued to operate normally. This indicates that valid parameters for a successful glitch are close to being found. The tool used to generate the glitches is the Chipwhisperer Lite board </span><a href="https://rtfm.newae.com/Capture/ChipWhisperer-Lite/"><span data-contrast="none">https://rtfm.newae.com/Capture/ChipWhisperer-Lite/</span></a><span data-contrast="none">.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<div style="width: 898px;" class="wp-video">
<!--[if lt IE 9]><script>document.createElement('video');</script><![endif]-->
<video class="wp-video-shortcode" id="video-6064-1" width="898" height="1022" preload="metadata" controls="controls"><source type="video/mp4" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/replace-the-gif-video.mp4?_=1"><a href="https://www.anvilsecure.com/wp-content/uploads/2025/03/replace-the-gif-video.mp4">https://website-admin.anvilventures.com/wp-content/uploads/2025/03/replace-the-gif-video.mp4</a></video>
</div>
<p>&nbsp;</p>
<p><span data-contrast="none">With the key parameters </span><code><span data-contrast="none">repeat</span><span data-contrast="none">, </span><span data-contrast="none">width</span><span data-contrast="none">, </span><span data-contrast="none">offset</span></code><span data-contrast="none">, and </span><code><span data-contrast="none">clock frequency</span></code><span data-contrast="none"> identified, the attack can now proceed (These parameters can be set using the Chipwhisperer Python API. For further details, please refer to </span><a href="https://chipwhisperer.readthedocs.io/en/latest/scope-api.html"><span data-contrast="none">https://chipwhisperer.readthedocs.io/en/latest/scope-api.html</span></a><span data-contrast="none">).</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">Another critical parameter to consider is the </span><code><span data-contrast="none">ext_offset</span></code><span data-contrast="none">. This value defines the waiting period before the glitch is triggered and is expressed in clock cycles as </span><code><span data-contrast="none">1/clkfreq</span></code><span data-contrast="none">. To ensure the glitch occurs at the right moment, the ChipWhisperer trigger pin was connected to the </span><span data-contrast="none"><code>USART_TX</code></span><span data-contrast="none">  line of the USB-to-UART TTL converter. However, further fine-tuning is required to determine the precise delay (or waiting time) before initiating the glitch to ensure it aligns with the moment when the target received the </span><code><span data-contrast="none">0x11</span></code><span data-contrast="none"> read command.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">During testing, finding the right </span><code><span data-contrast="none">ext_offset</span></code><span data-contrast="none"> introduced several challenges. This will be further discussed in the closing section.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<h4>Determine the ext_offset</h4>
<p><span data-contrast="none">A logic analyzer was employed to measure the timing of the transmission and reception of the </span><code><span data-contrast="none">0x11</span></code><span data-contrast="none"> read command. The software provided with the logic analyzer includes a precise timing measurement feature. This feature allows for accurate measurement of the exact time intervals between when the </span><code><span data-contrast="none">0x11</span></code><span data-contrast="none"> command is transmitted and when the instruction is fully received and processed, helping to determine the ideal moment for the glitch injection.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<figure id="attachment_6076" aria-describedby="caption-attachment-6076" style="width: 753px" class="wp-caption alignnone"><img loading="lazy" decoding="async" alt="" width="753" height="146" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/uart-logic1.png" class="wp-image-6076 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="wp-image-6076" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/uart-logic1.png" alt="" width="753" height="146"></noscript>
<figcaption id="caption-attachment-6076" class="wp-caption-text"><em><span style="font-size: small;">Example of Bootloader interactions </span></em></figcaption></figure>
<figure id="attachment_6077" aria-describedby="caption-attachment-6077" style="width: 2494px" class="wp-caption alignnone"><img loading="lazy" decoding="async" alt="" width="2494" height="643" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/ext_offset_estimation.png" class="wp-image-6077 size-full lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="wp-image-6077 size-full" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/ext_offset_estimation.png" alt="" width="2494" height="643"></noscript>
<figcaption id="caption-attachment-6077" class="wp-caption-text"><span style="font-size: small;"><i>UART timing measurement</i></span></figcaption></figure>
<p><span data-contrast="none">Various measurements were taken, leading to the following time estimation:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="6" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1"><span data-contrast="none">Read Memory request command issue timing: <code>182.300 µs</code></span></li>
<li data-leveltext="" data-font="Symbol" data-listid="6" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1"><span data-contrast="none">Read Memory response command issue timing: <code>196.800 µs</code></span></li>
</ul>
<p><span data-contrast="none">From these values, the minimum waiting time before issuing the glitch is calculated as follows:</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<ul>
<li data-leveltext="" data-font="Symbol" data-listid="7" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1"><span data-contrast="none">Clock cycle duration: <code>1/clkfreq== 10ns</code></span></li>
<li data-leveltext="" data-font="Symbol" data-listid="7" data-list-defn-props="{&quot;335552541&quot;:1,&quot;335559685&quot;:720,&quot;335559991&quot;:360,&quot;469769226&quot;:&quot;Symbol&quot;,&quot;469769242&quot;:[8226],&quot;469777803&quot;:&quot;left&quot;,&quot;469777804&quot;:&quot;&quot;,&quot;469777815&quot;:&quot;multilevel&quot;}" aria-setsize="-1" data-aria-posinset="1" data-aria-level="1"><span data-contrast="none">Minimum Waiting time: <code>182300/10 = 18230 clock cycle.</code></span></li>
</ul>
<p><span data-contrast="none">Thus, the </span><code><span data-contrast="none">ext_offset</span></code><span data-contrast="none">value, which defines the number of clock cycles before initiating the glitch, should be set to a minimum of </span><code><span data-contrast="none">18230</span></code><span data-contrast="none"> clock cycles to trigger the fault at the optimal moment.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<h4>Glitch Session</h4>
<p><span data-contrast="none">After several iterations of fine-tuning and adjustments, the optimal </span><code><span data-contrast="none">ext_offset</span></code><span data-contrast="none"> parameter was found to be between </span><code><span data-contrast="none">18300</span></code><span data-contrast="none"> and </span><code><span data-contrast="none">18370</span></code><span data-contrast="none"> clock cycles. With this adjustment, the script is now able to run successfully and consistently glitch the desired operations.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">Full script can be found in this <a href="https://github.com/giggi0x00/faultinjection-scripts" target="_blank" rel="noopener">repository</a>.</span></p>
<pre>$ python3 glitchstm32f401.py

cwlite Device

[...]

Got ack
Can read the memory: 1.953125 10.15625 2 18365
Sending memory address :134225920 0800200028
Result 1f1f
Glitched
b'y'

Got ack
Can read the memory: 1.953125 10.15625 2 18313
Sending memory address :134225920 0800200028
Result 1f1f
Glitched
b'y'

Got ack
Can read the memory: 1.953125 10.15625 2 18313
Sending memory address :134225920 0800200028
Result 1f1f1f
Glitched
b'y'
Got ack
Can read the memory: 1.953125 10.15625 2 18320
Sending memory address :134225920 0800200028
Result 79
Ack, read the memory address: 0800200028

Result: 794346e318c7f898304b4645eb0303c7f89c30d7f8f4305b680022c7f89030c7f894204ff000024ff00003d7e9244529468b00214643ea917321468a00d7e92601fef7daf802460b46604ba3fb02235b091c01d7f8fc300022c7f88830c7f88c20d7e9228942464b469118b9615b41fb61d7e9062341465118396149464b417b614ff000024ff00003d7e904ab5946cb00514643ea51735146ca0010461946034642469b18c7f880304b460a4642eb0303c7f88430d7f8f4305b680022bb67fa674ff000024ff00003d7e91e8949468b00414643ea917341468a00d7e92001fef78bf802460b461146384ba3fb01235b09642202fb03f3cb1a1b013233334aa2

Bytes to read: 794346e318c7f898304b4645eb0303c7f89c30d7f8f4305b680022c7f89030c7f894204ff000024ff00003d7e9244529468b00214643ea917321468a00d7e92601fef7daf802460b46604ba3fb02235b091c01d7f8fc300022c7f88830c7f88c20d7e9228942464b469118b9615b41fb61d7e9062341465118396149464b417b614ff000024ff00003d7e904ab5946cb00514643ea51735146ca0010461946034642469b18c7f880304b460a4642eb0303c7f88430d7f8f4305b680022bb67fa674ff000024ff00003d7e91e8949468b00414643ea917341468a00d7e92001fef78bf802460b461146384ba3fb01235b09642202fb03f3cb1a1b013233334aa2

Glitched
b'y'
Got ack
Can read the memory: 1.953125 10.15625 2 18332
Sending memory address :134226176 0800210029
Result 79
Ack, read the memory address: 0800210029

Result: 7903235b0903f0f0031c44d7f8fc3000223b677a67d7e91c8942464b469118b9605b41fb60d7e9022341465118396049464b417b604ff000024ff00003d7e900ab5946cb00514643ea51735146ca0010461946034642469b18bb664b460a4642eb0303fb66d7f8f4305b6800223b667a664ff000024ff00003d7e9188949468b00414643ea917341468a00d7e91a01fef733f802460b460d4ba3fb02135b09642101fb03f3d31a1b013233084aa2fb03235b0903f00f02d7f8f4301b6822449a6000bf07f58077bd46bde8b08f1f85eb5102440346934200d1704703f8011bf9e770b50d4d0d4c641ba4100026a64209d10b4d0c4c00f018f8641ba4100026a6

Bytes to read: 7903235b0903f0f0031c44d7f8fc3000223b677a67d7e91c8942464b469118b9605b41fb60d7e9022341465118396049464b417b604ff000024ff00003d7e900ab5946cb00514643ea51735146ca0010461946034642469b18bb664b460a4642eb0303fb66d7f8f4305b6800223b667a664ff000024ff00003d7e9188949468b00414643ea917341468a00d7e91a01fef733f802460b460d4ba3fb02135b09642101fb03f3d31a1b013233084aa2fb03235b0903f00f02d7f8f4301b6822449a6000bf07f58077bd46bde8b08f1f85eb5102440346934200d1704703f8011bf9e770b50d4d0d4c641ba4100026a64209d10b4d0c4c00f018f8641ba4100026a6
[...]</pre>
<p><span class="TextRun SCXW116032856 BCX0" lang="EN-US" xml:lang="EN-US" data-contrast="none"><span class="NormalTextRun SCXW116032856 BCX0">Subsequently, the firmware can be read, obtaining all the secrets in it:</span></span><span class="EOP SCXW116032856 BCX0" data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<pre><span data-contrast="none">$ echo -n 7905d170bd55f8043b98470136eee755f8043b98470136f2e7e0220008e0220008e0220008e4220008f8b500bff8bc08bc9e467047f8b500bff8bc08bc9e46704773757065727365637265746b6579000077726f6e6721210a00000000477565737320746865206b6579210a0050617373776f726420636f7272656374210a00004c6f636b6564210a00000000476c697463686564210a00006b3a2564200000006a3a256420000000693a25640a200000476c6974636820627970617373000000000000000000000001020304060708090000000001020304fcdeff7f01000000b90100089501000840220008502200085c2200086c2200080024f400100000 | xxd -r -p</span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span>

<span data-contrast="none">y�p�U�;�G6��U�;�G6������������FpG������FpGsupersecretkeywrong!!</span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span>

<span data-contrast="none">Guess the key!</span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span>

<span data-contrast="none">Password correct!</span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span>

<span data-contrast="none">Locked!</span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span>

<span data-contrast="none">Glitched!</span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span>

<span data-contrast="none">k:%d j:%d i:%d</span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span>

<span data-contrast="none">[...]</span><span data-ccp-props="{&quot;201341983&quot;:0,&quot;335559739&quot;:0,&quot;335559740&quot;:240,&quot;469777462&quot;:[916,1832,2748,3664,4580,5496,6412,7328,8244,9160,10076,10992,11908,12824,13740,14656],&quot;469777927&quot;:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],&quot;469777928&quot;:[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]}"> </span></pre>
<h4>Conclusion</h4>
<p><span data-contrast="none">Glitching is inherently unpredictable and non-deterministic, with variables such as temperature, wire length, and environmental conditions significantly affecting the outcome. Several challenges were encountered, multiple instances of target were temporarily misconfigured due to glitches in unrelated memory areas. In the initial run, using a broad ext_offset range of </span><code><span data-contrast="none">18230</span></code><span data-contrast="none"> to </span><code><span data-contrast="none">19500</span></code><span data-contrast="none"> clock cycles produced varied responses. In many cases, it was revealed that the glitch caused both the RDP and Write Protect features to adopt random values, resulting in an unstable environment</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">The PCROP setting was found to be enabled after a few glitches; however, other settings were also corrupted, making the device temporarily unusable.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><img loading="lazy" decoding="async" alt="" width="710" height="410" data-src="https://www.anvilsecure.com/wp-content/uploads/2025/03/pcropsetwithglitch.png" class="alignnone size-full wp-image-6078 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" class="alignnone size-full wp-image-6078" src="https://www.anvilsecure.com/wp-content/uploads/2025/03/pcropsetwithglitch.png" alt="" width="710" height="410"></noscript></p>
<p><span data-contrast="none">Overall, the process involved extensive troubleshooting, with hours spent diagnosing setup issues and refining the glitching process. In total, approximately six hours were dedicated to glitch the device and the extract the totality of the firmware.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">To mitigate the risks and improve the reliability of future glitching attempts, several strategies can be employed. When designing a product, it is important to consider these types of attacks. Chip selection is crucial and plays a significant role, as many chips have built-in security mechanisms against fault injection. In more complex architecture, like Intel CPUs, dedicated circuits are involved to detect misalignment in timing. An example of such a circuit is the Tunable Replica Circuit, which helps detect multiple attacks, including clock, VFI, and EMFI.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">For existing solutions, software counter measures can also be applied. Repeating critical operations multiple times and verifying the results or adding random delays before sensitive operations can further reduce the likelihood of successful attacks.</span><span data-ccp-props="{&quot;134233117&quot;:true,&quot;134233118&quot;:true,&quot;201341983&quot;:0,&quot;335559740&quot;:240}"> </span></p>
<p><span data-contrast="none">It is important to be aware of fault injection attacks and evaluate them within the threat modelling design of your product. Some devices may not have enough security measures against these new threats and successful attacks can lead to the full compromise of your products and infrastructure. Evaluating the potential threats during the product design stage can help to identify the right products for the designated business.</span></p>
</div>
</div></div></div></div>
<div id="pg-6064-1" class="panel-grid panel-no-style"><div id="pgc-6064-1-0" class="panel-grid-cell">
<div id="panel-6064-1-0-0" class="so-panel widget widget_text panel-first-child" data-index="1">
<h3 class="widget-title">About the Author</h3>			<div class="textwidget">
<p>Luigi Fragale is a Security Engineer at Anvil Secure with a strong passion for IoT, reverse engineering, and offensive security research. Throughout his career, he has applied his expertise across various sectors, ranging from the financial industry to Operational Technology (OT).</p>
<p>Always eager to learn new things, Luigi achieved multiple certifications (OSCP, OSEP, OSED, OSWE, OSCE3). When he&#8217;s not exploring fault injection techniques or tackling CTF challenges, he enjoys brewing craft beer, playing basketball, and windsurfing.</p>
</div>
		</div>
<div id="panel-6064-1-0-1" class="so-panel widget widget_total_plus_social_icons panel-last-child" data-index="2">        <div class="ht-social-icons style2 icon-small icon-left si-no-effect">
                                <a style="background-color:#2caaff;color:#ffffff;border-color:#ffffff" class="ht-social-button" href="https://www.linkedin.com/company/anvil-secure" title="" target="_blank">
                        <i class="fab fa-linkedin"></i>
                    </a>
                                        <a style="background-color:#2caaff;color:#ffffff;border-color:#ffffff" class="ht-social-button" href="https://twitter.com/anvil_secure" title="" target="_blank">
                        <i class="fab fa-twitter"></i>
                    </a>
                            </div>
        </div>
</div></div>
</div>    </div>
<!-- .entry-content -->
    </article><!-- #post-## -->

                        <nav class="navigation post-navigation" role="navigation">
            <div class="nav-links">
                <div class="nav-previous">
                    <a href="https://www.anvilsecure.com/blog/one-bug-wasnt-enough-escalating-twice-through-saps-setuid-landscape.html" rel="prev"><span><i class="mdi mdi-chevron-left"></i>Prev</span>One Bug Wasn’t Enough: Escalating Twice Through SAP’s Setuid Landscape</a> 
                </div>

                <div class="nav-next">
                    <a href="https://www.anvilsecure.com/blog/introducing-hanalyzer.html" rel="next"><span>Next<i class="mdi mdi-chevron-right"></i></span>Introducing HANAlyzer: An Open-Source Tool to Secure Your HANA databases</a>                </div>
            </div>
        </nav>
        
                    </main><!-- #main -->
    </div>
<!-- #primary -->

        <div id="secondary" class="widget-area">
        <section id="sow-editor-4" class="widget widget_sow-editor"><div class="so-widget-sow-editor so-widget-sow-editor-base">
<h4 class="widget-title">Tools</h4>
<div class="siteorigin-widget-tinymce textwidget">
	<p class="team-name"><a href="https://github.com/anvilsecure/aqlmap" target="_blank" rel="noopener">aqlmap</a> - A tool to extract information from ArangoDB through AQL injection. See the introductory <a href="https://www.anvilsecure.com/blog/exploiting-aql-injection-vulnerabilities-in-arangodb.html">blogpost</a>.</p>
<hr>
<p><a href="https://pypi.org/project/awstracer/" target="_blank" rel="noopener">awstracer</a> - An Anvil CLI utility that will allow you to trace and replay AWS commands.</p>
<hr>
<p class="team-name"><a href="https://portswigger.net/bappstore/bbb81b07b7cd45448e8c728a38914c92" target="_blank" rel="noopener">awssig</a> - Anvil Secure's Burp extension for signing AWS requests with SigV4.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/bytebanter-burpai" target="_blank" rel="noopener">ByteBanter</a> - A Burp Suite extension that leverages LLMs to generate context-aware payloads for Burp Intruder. See the introductory <a href="https://www.anvilsecure.com/blog/introducing-bytebanter-an-llm-based-burpsuite-intruder-payload-generator.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/dawgmon" target="_blank" rel="noopener">dawgmon</a> - Dawg the hallway monitor: monitor operating system changes and analyze introduced attack surface when installing software. See the introductory <a href="https://www.anvilsecure.com/blog/linux-attack-surface-analysis.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/GhidraGarminApp" target="_blank" rel="noopener">GhidraGarminApp</a> - A Ghidra processor and loader for Garmin watch applications. See the introductory <a href="https://www.anvilsecure.com/blog/reverse-engineering-garmin-watch-applications-with-ghidra.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/hanalyzer" target="_blank" rel="noopener">HANAlyzer</a> - A tool that automates SAP HANA security checks and outputs clear HTML reports. See the introductory <a href="https://www.anvilsecure.com/blog/introducing-hanalyzer.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/IPAAutoDec" target="_blank" rel="noopener">IPAAutoDec</a> - A tool that decrypts IPA files end-to-end via SSH. See the introductory <a href="https://www.anvilsecure.com/blog/locked-up-but-not-locked-out-ios-app-pentesting-without-jailbreak.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/nanopb-decompiler" target="_blank" rel="noopener">nanopb-decompiler</a> - Our nanopb-decompiler is an IDA python script that can recreate .proto files from binaries compiled with 0.3.x, and 0.4.x versions of nanopb. See the introductory <a href="https://www.anvilsecure.com/blog/nanopb-protobuf-decompiler.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/offtempo" target="_blank" rel="noopener">OffTempo</a> - A Burp Suite extension for statistical timing side-channel analysis. See the introductory <a href="https://www.anvilsecure.com/blog/introducing-offtempo-statistical-timing-side-channel-analysis-for-burp-suite.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/passkey-editor" target="_blank" rel="noopener">Passkey Editor</a> - A Burp Suite extension for testing WebAuthn/FIDO2 passkey ceremonies. See the introductory <a href="https://www.anvilsecure.com/blog/passkey-editor.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/pqcutils" target="_blank" rel="noopener">PQCDump</a> - A passive PCAP analyzer that shows whether SSH and TLS sessions actually used PQC algorithms. See the introductory <a href="https://www.anvilsecure.com/blog/pqcdump-pqc-adoption-tools.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/pqcutils" target="_blank" rel="noopener">PQCScan</a> - A scanner that can determine whether SSH and TLS servers support PQC algorithms. See the introductory <a href="https://www.anvilsecure.com/blog/scanning-for-post-quantum-cryptographic-support.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/SAPCARve" target="_blank" rel="noopener">SAPCARve</a> - A utility Python script for manipulating SAP's SAR archive files. See the introductory <a href="https://www.anvilsecure.com/blog/one-bug-wasnt-enough-escalating-twice-through-saps-setuid-landscape.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/ulexecve/" target="_blank" rel="noopener">ulexecve</a> - A tool to execute ELF binaries on Linux directly from userland. See the introductory <a href="https://www.anvilsecure.com/blog/userland-execution-of-binaries-directly-from-python.html">blogpost</a>.</p>
<hr>
<p class="team-name"><a href="https://github.com/anvilsecure/usb-racer" target="_blank" rel="noopener">usb-racer</a> - A tool for pentesting TOCTOU issues with USB storage devices.</p>
</div>
</div></section>
		<section id="recent-posts-1" class="widget widget_recent_entries">
		<h4 class="widget-title">Recent Posts</h4>
		<ul>
											<li>
					<a href="https://www.anvilsecure.com/blog/nasa-ion-dtn-security.html">You Wouldn&#8217;t Hack a Satellite: Unbundling NASA&#8217;s ION-DTN</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/predictable-username-and-passwords.html">Predictable Usernames and Passwords |  Field Notes, Issue 1</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/passkey-attack-surface-whitepaper.html">Demystifying Passkeys — Under Attack (Whitepaper)</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/pqcdump-pqc-adoption-tools.html">Introducing PQCDump: A Real Look at PQC Adoption</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/passkey-editor.html">Passkey Editor: a Burp Suite Extension for Attacking WebAuthn</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/ai-adoption-hackathon.html">Internal AI Adoption Hackathon: What We Learned</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/identifying-and-chasing-rce-in-saps-commoncryptolib.html">Identifying and Chasing RCE in SAP&#8217;s CommonCryptoLib</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/finding-crown-jewels-hunting-through-180000-ruby-gems.html">Finding Crown Jewels: Hunting Through 180,000 Ruby Gems</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/how-we-use-llms-in-secure-code-review.html">How We Use LLMs in Secure Code Review</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/llm-genai-security-methodology-at-anvil-secure.html">How We Test AI:  LLM &#038; GenAI Security Methodology at Anvil Secure</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/demystifying-passkeys-under-the-hood-the-architecture.html">Demystifying Passkeys — Under the Hood: The Architecture</a>
									</li>
											<li>
					<a href="https://www.anvilsecure.com/blog/demystifying-passkeys-under-the-hood-the-protocol.html">Demystifying Passkeys — Under the Hood: The Protocol</a>
									</li>
					</ul>

		</section>    </div>
<!-- #secondary -->
    
</div>


</div>
<!-- #content -->


    <footer id="ht-colophon" class="ht-site-footer footer-style4 col-4-2-1-1">

        	

                    <div class="ht-main-footer">
                <div class="ht-container">
                    <div class="ht-main-footer-wrap ht-clearfix">
                                                    <div class="ht-footer ht-footer1">
                                <aside id="media_image-3" class="widget widget_media_image"><img width="180" height="85" alt="" style="max-width: 100%; height: auto;" decoding="async" data-src="https://www.anvilsecure.com/wp-content/uploads/2021/04/Anvil_Secure_small3.png" class="image wp-image-2766  attachment-full size-full lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img width="180" height="85" src="https://www.anvilsecure.com/wp-content/uploads/2021/04/Anvil_Secure_small3.png" class="image wp-image-2766  attachment-full size-full" alt="" style="max-width: 100%; height: auto;" decoding="async"></noscript></aside><aside id="text-2" class="widget widget_text">			<div class="textwidget">
<p>We are more than a diverse global team of industry veterans with security expertise who value transparency. We are relationship builders who want to get to know you and your business.</p>
</div>
		</aside>	
                            </div>
                                                    <div class="ht-footer ht-footer2">
                                <aside id="sow-editor-6" class="widget widget_sow-editor"><div class="so-widget-sow-editor so-widget-sow-editor-base">
<h4 class="widget-title">Contact Us</h4>
<div class="siteorigin-widget-tinymce textwidget">
	<p>206-753-7649</p>
<p><a style="color: white;" href="mailto:info@anvilsecure.com">info@anvilsecure.com</a></p>
<p><a style="color: white;" href="mailto:security@anvilsecure.com">security@anvilsecure.com</a></p>
<p>2125 Western Ave Suite 208</p>
<p>Seattle, WA 98121</p>
</div>
</div></aside>	
                            </div>
                                                    <div class="ht-footer ht-footer3">
                                <aside id="total_plus_social_icons-3" class="widget widget_total_plus_social_icons"><h4 class="widget-title">FOLLOW US</h4>        <div class="ht-social-icons style2 icon-small icon-left si-no-effect">
                                <a style="background-color:#2caaff;color:#ffffff;border-color:#ffffff" class="ht-social-button" href="https://twitter.com/anvil_secure" title="Twitter" target="_blank">
                        <i class="fab fa-twitter"></i>
                    </a>
                                        <a style="background-color:#2caaff;color:#ffffff;border-color:#ffffff" class="ht-social-button" href="https://www.linkedin.com/company/anvil-ventures-inc/" title="LinkedIn" target="_blank">
                        <i class="fab fa-linkedin"></i>
                    </a>
                                        <a style="background-color:#2caaff;color:#ffffff;border-color:#ffffff" class="ht-social-button" href="https://github.com/anvilsecure" title="Github" target="_blank">
                        <i class="fab fa-github"></i>
                    </a>
                            </div>
        </aside><aside id="block-7" class="widget widget_block widget_media_image">
<figure class="wp-block-image size-full is-resized soc-stacked"><a href="http://www.aicpa.org/soc4so" target="_blank" rel=" noreferrer noopener"><img loading="lazy" decoding="async" alt="" width="116" height="115" data-src="https://www.anvilsecure.com/wp-content/uploads/2023/08/21972-312_SOC_NonCPA.png" class="wp-image-4194 lazyload" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="><noscript><img loading="lazy" decoding="async" src="https://www.anvilsecure.com/wp-content/uploads/2023/08/21972-312_SOC_NonCPA.png" alt="" class="wp-image-4194" width="116" height="115"></noscript></a></figure>
</aside><aside id="block-9" class="widget widget_block widget_text">
<p><a href="https://www.anvilsecure.com/research-updates">Subscribe to the Anvil Signal newsletter</a></p>
</aside>	
                            </div>
                                            </div>
                </div>
            </div>
        
                    <div class="ht-bottom-footer">
                <div class="ht-container">
                    <div class="ht-site-info">
                        © <span>2026</span> Anvil Secure                    </div>
<!-- #site-info -->
                </div>
            </div>
            </footer><!-- #colophon -->
</div>
<!-- #page -->

    <div id="ht-back-top" class="ht-hide"><i class="icofont-simple-up"></i></div>
        			<script type="text/javascript">const lazyloadRunObserver = () => {
					const lazyloadBackgrounds = document.querySelectorAll( `.e-con.e-parent:not(.e-lazyloaded)` );
					const lazyloadBackgroundObserver = new IntersectionObserver( ( entries ) => {
						entries.forEach( ( entry ) => {
							if ( entry.isIntersecting ) {
								let lazyloadBackground = entry.target;
								if( lazyloadBackground ) {
									lazyloadBackground.classList.add( 'e-lazyloaded' );
								}
								lazyloadBackgroundObserver.unobserve( entry.target );
							}
						});
					}, { rootMargin: '200px 0px 200px 0px' } );
					lazyloadBackgrounds.forEach( ( lazyloadBackground ) => {
						lazyloadBackgroundObserver.observe( lazyloadBackground );
					} );
				};
				const events = [
					'DOMContentLoaded',
					'elementor/lazyload/observe',
				];
				events.forEach( ( event ) => {
					document.addEventListener( event, lazyloadRunObserver );
				} );</script>
			<link rel="stylesheet" id="mediaelement-css" href="https://www.anvilsecure.com/wp-includes/js/mediaelement/mediaelementplayer-legacy.min.css?ver=4.2.17" type="text/css" media="all">
<link rel="stylesheet" id="wp-mediaelement-css" href="https://www.anvilsecure.com/wp-includes/js/mediaelement/wp-mediaelement.min.css?ver=6.6.10" type="text/css" media="all">
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/jquery/ui/core.min.js?ver=1.13.3" id="jquery-ui-core-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/jquery/ui/tooltip.min.js?ver=1.13.3" id="jquery-ui-tooltip-js"></script>
<script type="text/javascript" id="leadin-script-loader-js-js-extra">
/* <![CDATA[ */
var leadin_wordpress = {"userRole":"visitor","pageType":"post","leadinPluginVersion":"11.2.9"};
/* ]]> */
</script>
<script type="text/javascript" src="https://js.hs-scripts.com/46916957.js?integration=WordPress&amp;ver=11.2.9" id="leadin-script-loader-js-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.cookie.js?ver=1.5.3" id="js-cookie-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.nav.js?ver=1.5.3" id="jquery-nav-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/owl.carousel.js?ver=1.5.3" id="owl-carousel-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.owl-filter.js?ver=1.5.3" id="owl-filter-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/isotope.pkgd.js?ver=1.5.3" id="isotope-pkgd-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/lightgallery.js?ver=1.5.3" id="lightgallery-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/hoverintent.js?ver=1.5.3" id="hoverintent-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/superfish.js?ver=1.5.3" id="superfish-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/wow.js?ver=1.5.3" id="wow-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/odometer.js?ver=1.5.3" id="odometer-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/waypoint.js?ver=1.5.3" id="waypoint-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.espy.min.js?ver=1.5.3" id="espy-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/motio.min.js?ver=1.5.3" id="motio-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/slick.js?ver=1.5.3" id="slick-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.flipster.min.js?ver=1.5.3" id="flipster-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.mCustomScrollbar.js?ver=1.5.3" id="jquery-mcustomscrollbar-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.accordion.js?ver=1.5.3" id="jquery-accordion-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.photostream.min.js?ver=1.5.3" id="photostream-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.justifiedGallery.min.js?ver=1.5.3" id="justifiedGallery-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/jquery.countdown.js?ver=1.5.3" id="countdown-js"></script>
<script type="text/javascript" id="total-plus-megamenu-js-extra">
/* <![CDATA[ */
var total_plus_megamenu = {"rtl":"false"};
/* ]]> */
</script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/inc/walker/assets/megaMenu.js?ver=1.5.3" id="total-plus-megamenu-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/headroom.js?ver=1.5.3" id="headroom-js"></script>
<script type="text/javascript" id="total-plus-custom-js-extra">
/* <![CDATA[ */
var total_plus_options = {"template_path":"https:\/\/www.anvilsecure.com\/wp-content\/themes\/total-plus","rtl":"false","customize_preview":"false","customizer_gdpr_settings":"1","title_padding":"150"};
/* ]]> */
</script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/themes/total-plus/js/total-plus-custom.js?ver=1.5.3" id="total-plus-custom-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/comment-reply.min.js?ver=6.6.10" id="comment-reply-js" async="async" data-wp-strategy="async"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/plugins/enlighter/cache/enlighterjs.min.js?ver=0A0B0C" id="enlighterjs-js"></script>
<script type="text/javascript" id="enlighterjs-js-after">
/* <![CDATA[ */
!function(e,n){if("undefined"!=typeof EnlighterJS){var o={"selectors":{"block":"pre.EnlighterJSRAW","inline":"code.EnlighterJSRAW"},"options":{"indent":4,"ampersandCleanup":true,"linehover":true,"rawcodeDbclick":false,"textOverflow":"break","linenumbers":true,"theme":"enlighter","language":"generic","retainCssClasses":false,"collapse":false,"toolbarOuter":"","toolbarTop":"{BTN_RAW}{BTN_COPY}{BTN_WINDOW}{BTN_WEBSITE}","toolbarBottom":""}};(e.EnlighterJSINIT=function(){EnlighterJS.init(o.selectors.block,o.selectors.inline,o.options)})()}else{(n&&(n.error||n.log)||function(){})("Error: EnlighterJS resources not loaded yet!")}}(window,console);
/* ]]> */
</script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/plugins/wp-smushit/app/assets/js/smush-lazy-load.min.js?ver=3.12.6" id="smush-lazy-load-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/hoverIntent.min.js?ver=1.10.2" id="hoverIntent-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-content/plugins/megamenu/js/maxmegamenu.js?ver=3.6.2" id="megamenu-js"></script>
<script type="text/javascript" id="mediaelement-core-js-before">
/* <![CDATA[ */
var mejsL10n = {"language":"en","strings":{"mejs.download-file":"Download File","mejs.install-flash":"You are using a browser that does not have Flash player enabled or installed. Please turn on your Flash player plugin or download the latest version from https:\/\/get.adobe.com\/flashplayer\/","mejs.fullscreen":"Fullscreen","mejs.play":"Play","mejs.pause":"Pause","mejs.time-slider":"Time Slider","mejs.time-help-text":"Use Left\/Right Arrow keys to advance one second, Up\/Down arrows to advance ten seconds.","mejs.live-broadcast":"Live Broadcast","mejs.volume-help-text":"Use Up\/Down Arrow keys to increase or decrease volume.","mejs.unmute":"Unmute","mejs.mute":"Mute","mejs.volume-slider":"Volume Slider","mejs.video-player":"Video Player","mejs.audio-player":"Audio Player","mejs.captions-subtitles":"Captions\/Subtitles","mejs.captions-chapters":"Chapters","mejs.none":"None","mejs.afrikaans":"Afrikaans","mejs.albanian":"Albanian","mejs.arabic":"Arabic","mejs.belarusian":"Belarusian","mejs.bulgarian":"Bulgarian","mejs.catalan":"Catalan","mejs.chinese":"Chinese","mejs.chinese-simplified":"Chinese (Simplified)","mejs.chinese-traditional":"Chinese (Traditional)","mejs.croatian":"Croatian","mejs.czech":"Czech","mejs.danish":"Danish","mejs.dutch":"Dutch","mejs.english":"English","mejs.estonian":"Estonian","mejs.filipino":"Filipino","mejs.finnish":"Finnish","mejs.french":"French","mejs.galician":"Galician","mejs.german":"German","mejs.greek":"Greek","mejs.haitian-creole":"Haitian Creole","mejs.hebrew":"Hebrew","mejs.hindi":"Hindi","mejs.hungarian":"Hungarian","mejs.icelandic":"Icelandic","mejs.indonesian":"Indonesian","mejs.irish":"Irish","mejs.italian":"Italian","mejs.japanese":"Japanese","mejs.korean":"Korean","mejs.latvian":"Latvian","mejs.lithuanian":"Lithuanian","mejs.macedonian":"Macedonian","mejs.malay":"Malay","mejs.maltese":"Maltese","mejs.norwegian":"Norwegian","mejs.persian":"Persian","mejs.polish":"Polish","mejs.portuguese":"Portuguese","mejs.romanian":"Romanian","mejs.russian":"Russian","mejs.serbian":"Serbian","mejs.slovak":"Slovak","mejs.slovenian":"Slovenian","mejs.spanish":"Spanish","mejs.swahili":"Swahili","mejs.swedish":"Swedish","mejs.tagalog":"Tagalog","mejs.thai":"Thai","mejs.turkish":"Turkish","mejs.ukrainian":"Ukrainian","mejs.vietnamese":"Vietnamese","mejs.welsh":"Welsh","mejs.yiddish":"Yiddish"}};
/* ]]> */
</script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/mediaelement/mediaelement-and-player.min.js?ver=4.2.17" id="mediaelement-core-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/mediaelement/mediaelement-migrate.min.js?ver=6.6.10" id="mediaelement-migrate-js"></script>
<script type="text/javascript" id="mediaelement-js-extra">
/* <![CDATA[ */
var _wpmejsSettings = {"pluginPath":"\/wp-includes\/js\/mediaelement\/","classPrefix":"mejs-","stretching":"responsive","audioShortcodeLibrary":"mediaelement","videoShortcodeLibrary":"mediaelement"};
/* ]]> */
</script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/mediaelement/wp-mediaelement.min.js?ver=6.6.10" id="wp-mediaelement-js"></script>
<script type="text/javascript" src="https://www.anvilsecure.com/wp-includes/js/mediaelement/renderers/vimeo.min.js?ver=4.2.17" id="mediaelement-vimeo-js"></script>
<script type="text/javascript">document.body.className = document.body.className.replace("siteorigin-panels-before-js","");</script>
</body>
</html>