(() => {
  const GA4_ID = "G-0QQR0MNHJR";
  const CLARITY_ID = "yrcbz82zju";

  if (/^G-[A-Z0-9]+$/i.test(GA4_ID)) {
    const s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(GA4_ID);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function(){ dataLayer.push(arguments); };
    gtag("js", new Date());
    gtag("config", GA4_ID, { anonymize_ip: true });
  }

  if (/^[a-z0-9]+$/i.test(CLARITY_ID) && CLARITY_ID.length >= 6) {
    (function(c,l,a,r,i,t,y){
      c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
      t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
      y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    })(window, document, "clarity", "script", CLARITY_ID);
  }
})();
