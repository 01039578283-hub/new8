/* Client-side filtering only. Every destination is a real, crawlable anchor. */
(() => {
  'use strict';
  const form = document.querySelector('.bd-search');
  if (!form) return;
  const query = form.querySelector('#center-search');
  const region = form.querySelector('#region-select');
  const cards = [...document.querySelectorAll('.bd-center-card')];
  const groups = [...document.querySelectorAll('.bd-region-group')];
  const status = document.querySelector('#center-result');
  const empty = document.querySelector('.bd-empty');
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko-KR');
  const index = cards.map(card => ({card, text: normalize(card.dataset.search), compact:normalize(card.dataset.search).replace(/\s/g,'')}));
  function filter() {
    const terms = normalize(query.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    index.forEach(({card,text,compact}) => {
      const show = (!region.value || card.dataset.region === region.value) && terms.every(term => text.includes(term) || compact.includes(term));
      card.hidden = !show;
      if (show) count++;
    });
    groups.forEach(group => { group.hidden = !group.querySelector('.bd-center-card:not([hidden])'); });
    status.textContent = (terms.length || region.value ? '검색 결과 ' : '전체 ') + count + '개 지점';
    empty.hidden = count > 0;
  }
  form.addEventListener('submit', event => { event.preventDefault(); filter(); });
  query.addEventListener('input', filter);
  region.addEventListener('change', filter);
  form.addEventListener('reset', () => { requestAnimationFrame(() => { query.value=''; region.value=''; filter(); query.focus(); }); });
  filter();
})();
