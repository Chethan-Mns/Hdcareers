(()=> {
  const scriptEl=document.currentScript||document.querySelector('script[src*="public-header.js"]');
  if(!scriptEl||document.querySelector('[data-hd-public-header-ready="true"]'))return;
  const root=new URL('../',scriptEl.src);
  const href=(path='')=>new URL(path,root).href;
  const path=location.pathname.replace(/\/+$/,'')||'/';
  const section=path.includes('/insights')?'insights':path.includes('/resources/')||path.endsWith('/career-resources.html')?'resources':path.endsWith('/editorial-policy.html')?'policy':path.endsWith('/about.html')?'about':path.endsWith('/contact.html')?'contact':'jobs';
  const items=[
    ['jobs','Jobs','index.html#jobs'],
    ['insights','Insights','insights.html'],
    ['resources','Career Resources','career-resources.html'],
    ['policy','Verification Policy','editorial-policy.html'],
    ['about','About','about.html'],
    ['contact','Contact','contact.html']
  ];
  const navLinks=items.map(([key,label,url])=>`<a class="${key===section?'is-active':''}" ${key===section?'aria-current="page"':''} href="${href(url)}">${label}</a>`).join('');
  const oldHeader=document.querySelector('header');
  if(!oldHeader)return;
  const previous=oldHeader.previousElementSibling;
  if(previous&&previous.tagName==='DIV'&&/(Daily job alerts|Fresh job updates)/i.test(previous.textContent||''))previous.remove();
  const alertsUrl='https://whatsapp.com/channel/0029VbAxOna7NoZvhuKX362z';
  const header=document.createElement('header');
  header.className='hd-public-header';
  header.dataset.hdPublicHeaderReady='true';
  header.innerHTML=`<div class="hd-public-inner">
    <a class="hd-public-brand" href="${href('index.html')}" aria-label="HD Careers home">
      <img src="${href('assets/hd-careers-logo.png')}" alt="HD Careers">
      <span class="hd-public-brand-copy"><span class="hd-public-brand-title">HD Careers</span><span class="hd-public-brand-tagline">Jobs • Insights • Career resources</span></span>
    </a>
    <nav class="hd-public-nav" aria-label="Primary navigation">${navLinks}</nav>
    <a class="hd-public-alerts" href="${alertsUrl}" target="_blank" rel="noopener">Job alerts</a>
    <button class="hd-public-menu-btn" type="button" aria-label="Open navigation" aria-expanded="false" aria-controls="hdPublicMobile"><span></span><span></span><span></span></button>
  </div>
  <nav id="hdPublicMobile" class="hd-public-mobile" aria-label="Mobile navigation"><div class="hd-public-mobile-inner">${navLinks}<a class="hd-public-mobile-alerts" href="${alertsUrl}" target="_blank" rel="noopener">WhatsApp Job Alerts</a></div></nav>`;
  oldHeader.replaceWith(header);
  const btn=header.querySelector('.hd-public-menu-btn');
  const mobile=header.querySelector('.hd-public-mobile');
  const close=()=>{mobile.classList.remove('is-open');btn.setAttribute('aria-expanded','false');btn.setAttribute('aria-label','Open navigation')};
  btn.addEventListener('click',()=>{const open=!mobile.classList.contains('is-open');mobile.classList.toggle('is-open',open);btn.setAttribute('aria-expanded',String(open));btn.setAttribute('aria-label',open?'Close navigation':'Open navigation')});
  mobile.addEventListener('click',e=>{if(e.target.closest('a'))close()});
  document.addEventListener('click',e=>{if(!header.contains(e.target))close()});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
  addEventListener('resize',()=>{if(innerWidth>900)close()},{passive:true});
})();