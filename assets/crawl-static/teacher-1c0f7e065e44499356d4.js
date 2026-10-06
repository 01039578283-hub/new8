(() => {
  'use strict';
  const search = document.querySelector('[data-teacher-search]');
  if (!search) return;
  const region = document.querySelector('[data-teacher-region]');
  const cards = Array.from(document.querySelectorAll('[data-teacher-card]'));
  const groups = Array.from(document.querySelectorAll('[data-teacher-group]'));
  const count = document.querySelector('[data-teacher-count]');
  const empty = document.querySelector('[data-teacher-empty]');
  const reset = document.querySelector('[data-teacher-reset]');
  const hub = document.body.classList.contains('td-hub-page');
  const initial = new URL(window.location.href);
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko-KR').trim();
  search.value = initial.searchParams.get('q') || '';
  if (region && Array.from(region.options).some(option => option.value === initial.searchParams.get('region'))) {
    region.value = initial.searchParams.get('region');
  }
  const update = (persist = true) => {
    const tokens = normalize(search.value).split(/\s+/u).filter(Boolean);
    let shown = 0;
    cards.forEach(card => {
      const visible = (!region || !region.value || card.dataset.region === region.value) &&
        tokens.every(token => normalize(card.dataset.search).includes(token));
      card.hidden = !visible;
      if (visible) shown++;
      card.querySelectorAll('[data-teacher-branch-link]').forEach(link => {
        const url = new URL(link.dataset.teacherBranchLink, window.location.origin);
        if (search.value.trim()) url.searchParams.set('q', search.value.trim());
        link.href = url.pathname.replace(/\+/g, '%2B') + url.search;
      });
    });
    groups.forEach(group => { group.hidden = !group.querySelector('[data-teacher-card]:not([hidden])'); });
    count.textContent = hub ? `현재 조건 ${shown}개 지점 / 전체 ${cards.length}개 지점` : `현재 조건 ${shown}개 소개 / 전체 ${cards.length}개 소개`;
    empty.hidden = shown !== 0;
    if (persist) {
      const url = new URL(window.location.href);
      search.value.trim() ? url.searchParams.set('q', search.value.trim()) : url.searchParams.delete('q');
      region && region.value ? url.searchParams.set('region', region.value) : url.searchParams.delete('region');
      window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
  };
  search.addEventListener('input', () => update());
  if (region) region.addEventListener('change', () => update());
  reset.addEventListener('click', () => { search.value = ''; if (region) region.value = ''; update(); search.focus(); });
  window.addEventListener('popstate', () => {
    const url = new URL(window.location.href);
    search.value = url.searchParams.get('q') || '';
    if (region) region.value = Array.from(region.options).some(option => option.value === url.searchParams.get('region')) ? url.searchParams.get('region') : '';
    update(false);
  });
  // A direct introduction anchor always reveals its card before navigation.
  if (!hub && initial.hash) {
    const target = document.getElementById(decodeURIComponent(initial.hash.slice(1)));
    if (target && target.matches('[data-teacher-card]')) search.value = '';
  }
  update(false);
})();
