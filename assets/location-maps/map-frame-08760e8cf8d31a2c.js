(() => {
  'use strict';
  const config = document.currentScript.dataset;
  const root = document.getElementById(config.mapRoot);
  const status = document.getElementById('map-status');
  // This isolated map has no navigation actions. Keep map attribution visible.
  window.open = () => null;
  document.addEventListener('click', event => {
    if (event.target.closest && event.target.closest('a')) {
      event.preventDefault(); event.stopImmediatePropagation();
    }
  }, true);
  let map, ready = false;
  const tidy = () => {
    root.querySelectorAll('.cont,.wrap_controllers,.wrap_btn_roadview,.btn_big_map').forEach(n => n.remove());
    root.querySelectorAll('a[href]').forEach(n => { n.removeAttribute('href'); n.removeAttribute('target'); n.removeAttribute('onclick'); });
    root.querySelectorAll('img[alt*="새창"]').forEach(n => n.alt = 'Kakao 지도');
    if (root.querySelector('.wrap_map')) {
      if (!ready) { ready = true; status.hidden = true; root.removeAttribute('aria-busy'); }
      const instance = window.daum?.roughmap?.instances[config.timestamp];
      if (!map && instance?.jsMap) {
        map = instance.jsMap; map.setZoomable(false);
        if (window.matchMedia('(pointer: coarse)').matches) map.setDraggable(false);
      }
    }
  };
  new MutationObserver(tidy).observe(root, {childList: true, subtree: true});
  let attempts = 0;
  const boot = () => {
    if (!window.daum?.roughmap?.Lander) {
      if (++attempts < 100) setTimeout(boot, 100);
      return;
    }
    daum.roughmap.url_protocal = 'https:';
    daum.roughmap.URL_KEY_DATA_LOAD_PRE = 'https://t1.kakaocdn.net/roughmap/';
    new daum.roughmap.Lander({timestamp: config.timestamp, key: config.key,
      mapWidth: String(Math.max(240, document.documentElement.clientWidth)), mapHeight: '360'}).render();
  };
  boot();
  setTimeout(() => { if (!ready) status.textContent = '지도를 불러오지 못했습니다. 위의 지도 이미지와 주소를 확인해 주세요.'; }, 15000);
  let resizeTimer;
  addEventListener('resize', () => {
    clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (map) { const center = map.getCenter(); map.relayout(); map.setCenter(center); } }, 120);
  });
})();