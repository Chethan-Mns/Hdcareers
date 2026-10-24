/* Employer logo presentation only. Assets and owner approvals are never changed. */
(function () {
  'use strict';
  const SELECTOR = '.company-logo,.hdj3-logo,.hd-logo-summary';
  const SAMPLE = 64;

  function initials(img) {
    const host = img.closest(SELECTOR) || img.parentElement;
    if (!host) return;
    const mark = String(img.dataset.mark || img.alt || 'HD').trim().slice(0, 3) || 'HD';
    const color = /^#[0-9a-f]{6}$/i.test(img.dataset.color || '') ? img.dataset.color : '#0b6fe8';
    const span = document.createElement('span');
    span.className = 'hd-logo-initials';
    span.textContent = mark;
    span.style.color = color;
    host.classList.remove('hd-logo-dark');
    img.replaceWith(span);
  }

  function adapt(img) {
    if (!img || img.dataset.hdLogoChecked === '1' || !img.complete || !img.naturalWidth || !img.naturalHeight) return;
    img.dataset.hdLogoChecked = '1';
    const host = img.closest(SELECTOR) || img.parentElement;
    if (!host) return;
    const ratio = img.naturalWidth / img.naturalHeight;
    // Long lettering is unreadable inside a 56-64px square: use the existing initials.
    if (ratio >= 3.15) { initials(img); return; }
    let bbox = null, white = 0, visible = 0;
    try {
      const source = new URL(img.currentSrc || img.src, location.href);
      // Never sample a remote image: this also avoids cross-origin canvas warnings.
      if (source.origin !== location.origin) return;
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = SAMPLE;
      const ctx = canvas.getContext('2d', {willReadFrequently: true});
      if (!ctx) return;
      const w = Math.min(SAMPLE, SAMPLE * ratio), h = Math.min(SAMPLE, SAMPLE / ratio);
      ctx.drawImage(img, (SAMPLE - w) / 2, (SAMPLE - h) / 2, w, h);
      const pixels = ctx.getImageData(0, 0, SAMPLE, SAMPLE).data;
      // If the file has an opaque white background, exclude that padding from
      // the visible-mark geometry and brightness calculation.
      let opaqueWhiteCorners = 0;
      for (const k of [0, SAMPLE - 1, SAMPLE * (SAMPLE - 1), SAMPLE * SAMPLE - 1]) {
        const i = k * 4;
        if (pixels[i + 3] > 240 && pixels[i] > 241 && pixels[i + 1] > 241 && pixels[i + 2] > 241) opaqueWhiteCorners++;
      }
      const whitePadding = opaqueWhiteCorners === 4;
      let minX = SAMPLE, minY = SAMPLE, maxX = -1, maxY = -1;
      for (let y = 0; y < SAMPLE; y++) for (let x = 0; x < SAMPLE; x++) {
        const i = (y * SAMPLE + x) * 4;
        const a = pixels[i + 3];
        if (a < 56) continue;
        const r = pixels[i], g = pixels[i + 1], b = pixels[i + 2];
        if (whitePadding && r > 240 && g > 240 && b > 240) continue;
        visible++;
        if (r > 214 && g > 214 && b > 214) white++;
        minX = Math.min(minX, x); maxX = Math.max(maxX, x);
        minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      }
      if (visible < 9) return;
      const bw = maxX - minX + 1, bh = maxY - minY + 1;
      bbox = {width: bw, height: bh};
      if (bw / Math.max(1, bh) >= 3.15) { initials(img); return; }
      // White lettering on transparent/light pixels needs a dark navy backdrop.
      if (!whitePadding && white / visible > 0.74 && visible < SAMPLE * SAMPLE * 0.86) {
        host.classList.add('hd-logo-dark');
      }
      const fill = Math.max(bw, bh) / SAMPLE;
      const initial = /scale\(\s*([0-9.]+)\s*\)/.exec(img.style.transform || '');
      const previous = initial ? Number(initial[1]) : 1;
      const zoom = Math.max(previous, Math.min(1.85, Math.max(1, 0.9 / Math.max(fill, 0.1))));
      if (zoom > 1.015) {
        img.style.transform = 'scale(' + zoom.toFixed(2) + ')';
        img.style.transformOrigin = 'center';
      }
    } catch (_error) {
      // Failed/tainted images still work with the normal image/error fallback.
      if (ratio >= 3.15) initials(img);
    }
  }

  window.hdEnhanceLogo = adapt;
  function ready() {
    document.querySelectorAll('img[data-hd-employer-logo]').forEach(function (img) {
      if (img.complete && img.naturalWidth) adapt(img);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready, {once: true});
  else ready();
})();