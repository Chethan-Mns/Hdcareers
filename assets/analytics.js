(() => {
  const GA4_ID = "G-0QQR0MNHJR";
  const CLARITY_ID = "yrcbz82zju";
  const OPT_OUT_KEY = "hd_analytics_optout";

  function optedOut() {
    try { return localStorage.getItem(OPT_OUT_KEY) === "1"; }
    catch { return false; }
  }

  if (optedOut()) {
    window.hdTrack = function(){};
    return;
  }

  function normalizedPath() {
    const path = window.location.pathname || "/";
    return path === "/index.html" ? "/" : path;
  }

  if (/^G-[A-Z0-9]+$/i.test(GA4_ID)) {
    const s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(GA4_ID);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function(){ dataLayer.push(arguments); };
    gtag("js", new Date());
    gtag("config", GA4_ID, {
      anonymize_ip: true,
      page_location: window.location.origin + normalizedPath() + window.location.search,
      page_title: document.title
    });
  }

  window.hdTrack = function(eventName, params = {}) {
    if (!window.gtag || !eventName) return;
    const clean = {
      page_path: normalizedPath(),
      page_title: document.title,
      transport_type: "beacon",
      ...params
    };
    window.gtag("event", eventName, clean);
  };

  function socialChannel(href) {
    const value = String(href || "").toLowerCase();
    if (value.includes("whatsapp.com")) return "whatsapp";
    if (value.includes("t.me/") || value.includes("/telegram.html")) return "telegram";
    if (value.includes("instagram.com")) return "instagram";
    return "";
  }

  document.addEventListener("click", event => {
    const target = event.target && event.target.closest ? event.target.closest("[data-hd-track],a,button") : null;
    if (!target) return;

    const declared = target.getAttribute && target.getAttribute("data-hd-track");
    if (declared) {
      const params = {};
      if (target.tagName === "A") {
        params.link_url = target.href || "";
        params.link_text = (target.textContent || "").trim().slice(0, 120);
      }
      window.hdTrack(declared, params);
      return;
    }

    if (target.tagName !== "A") return;
    const channel = socialChannel(target.href);
    if (channel) {
      window.hdTrack("social_click", {
        social_channel: channel,
        link_url: target.href,
        link_text: (target.textContent || "").trim().slice(0, 120)
      });
      return;
    }

    try {
      const url = new URL(target.href, window.location.href);
      if (url.origin === window.location.origin && url.pathname.startsWith("/jobs/")) {
        window.hdTrack("job_open", {
          link_url: url.href,
          link_text: (target.textContent || "").trim().slice(0, 120)
        });
      }
    } catch {}
  }, true);

  if (/^[a-z0-9]+$/i.test(CLARITY_ID) && CLARITY_ID.length >= 6) {
    (function(c,l,a,r,i,t,y){
      c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
      t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
      y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    })(window, document, "clarity", "script", CLARITY_ID);
  }
})();
