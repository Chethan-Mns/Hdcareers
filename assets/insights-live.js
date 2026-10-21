(() => {
  'use strict';
  const nodes = document.querySelectorAll('.metric strong');
  if (nodes.length < 4) return;
  const prefix = location.pathname.includes('/insights/') ? '../' : '';
  fetch(prefix + 'data/insights-summary.json', { cache: 'no-store', credentials: 'omit' })
    .then(response => { if (!response.ok) throw Error('Dashboard feed unavailable'); return response.json(); })
    .then(data => {
      if (!Number.isInteger(data.active) || !Array.isArray(data.locations)) return;
      [data.active, data.employers, data.freshers, data.experienced].forEach((value, i) => {
        if (Number.isInteger(value)) nodes[i].textContent = String(value);
      });
      const sections = [...document.querySelectorAll('.section-title')];
      const heading = sections.find(el => el.textContent.trim() === 'Top location tags');
      const card = heading && heading.closest('.card');
      if (card && data.locations.length) {
        card.querySelectorAll('.rank').forEach(el => el.remove());
        const peak = Math.max(1, data.locations[0].count);
        for (const item of data.locations) {
          const row = document.createElement('div'); row.className = 'rank';
          const label = document.createElement('div'); label.className = 'rank-label'; label.textContent = String(item.label);
          const bar = document.createElement('div'); bar.className = 'bar';
          const fill = document.createElement('i'); fill.style.width = Math.max(8, Math.round(item.count / peak * 100)) + '%';
          bar.appendChild(fill);
          const number = document.createElement('div'); number.className = 'rank-value'; number.textContent = String(item.count);
          row.append(label, bar, number);
          card.appendChild(row);
        }
      }
      const note = document.getElementById('insightsLiveStatus');
      if (note) note.textContent = 'Live dataset · Verified through ' + data.verifiedThrough;
    }).catch(() => {
      const note = document.getElementById('insightsLiveStatus');
      if (note) note.textContent = 'Showing last published snapshot';
    });
})();
