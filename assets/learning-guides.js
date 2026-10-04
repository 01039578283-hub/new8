/* Progressive enhancement: all guide links and blank record files exist in HTML. */
(() => {
  'use strict';
  const controls = document.querySelector('[data-guide-controls]');
  if (controls) {
    const search = document.getElementById('guide-search');
    const grade = document.getElementById('guide-grade');
    const buttons = [...document.querySelectorAll('[data-category-filter]')];
    const cards = [...document.querySelectorAll('[data-guide-card]')];
    const sections = [...document.querySelectorAll('[data-guide-category]')];
    const count = document.querySelector('[data-guide-count]');
    const empty = document.querySelector('[data-guide-empty]');
    let category = 'all';
    const normalize = text => text.normalize('NFC').toLocaleLowerCase('ko').replace(/\s+/g, '');
    const update = (sync = true) => {
      const tokens = search.value.trim().split(/\s+/).filter(Boolean).map(normalize);
      let visible = 0;
      for (const card of cards) {
        const text = normalize(card.dataset.search);
        const match = (category === 'all' || card.dataset.category === category) &&
          (grade.value === 'all' || card.dataset.grades.split(' ').includes(grade.value)) &&
          tokens.every(token => text.includes(token));
        card.hidden = !match;
        if (match) visible++;
      }
      for (const section of sections) {
        const rows = [...section.querySelectorAll('[data-guide-card]')];
        const total = rows.filter(row => !row.hidden).length;
        section.hidden = total === 0;
        section.querySelector('.lg-kicker').textContent = `${total}편의 가이드 · 주제 전체 ${rows.length}편`;
      }
      buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.categoryFilter === category)));
      count.textContent = `현재 조건 ${visible}편 / 전체 ${cards.length}편`;
      empty.hidden = visible !== 0;
      if (sync) {
        const url = new URL(location.href);
        for (const [key, value] of [['q',search.value.trim()],['grade',grade.value],['topic',category]]) {
          if (!value || value === 'all') url.searchParams.delete(key);
          else url.searchParams.set(key, value);
        }
        history.replaceState(null, '', url);
      }
    };
    const restore = () => {
      const params = new URLSearchParams(location.search);
      search.value = params.get('q') || '';
      grade.value = [...grade.options].some(o => o.value === params.get('grade')) ? params.get('grade') : 'all';
      category = buttons.some(b => b.dataset.categoryFilter === params.get('topic')) ? params.get('topic') : 'all';
      update(false);
    };
    search.addEventListener('input', () => update());
    grade.addEventListener('change', () => update());
    buttons.forEach(button => button.addEventListener('click', () => {category = button.dataset.categoryFilter; update();}));
    document.querySelector('[data-filter-reset]').addEventListener('click', () => {
      search.value = ''; grade.value = 'all'; category = 'all'; update(); search.focus();
    });
    window.addEventListener('popstate', restore);
    controls.hidden = false;
    restore();
  }
  const record = document.querySelector('[data-record-title]');
  if (record) {
    const fields = [...record.querySelectorAll('[data-record-field]')];
    const status = record.querySelector('[data-record-status]');
    const download = record.querySelector('[data-record-download]');
    const print = record.querySelector('[data-record-print]');
    download.disabled = false;
    print.disabled = false;
    download.addEventListener('click', () => {
      const rows = [record.dataset.recordTitle + ' · 학습 기록', '코칭센터 학습가이드', document.querySelector('link[rel=canonical]').href, ''];
      fields.forEach(field => rows.push(field.dataset.label + ':', field.value || '(미작성)', ''));
      const blob = new Blob(['\uFEFF' + rows.join('\r\n') + '\r\n'], {type:'text/plain;charset=utf-8'});
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = href;
      anchor.download = record.dataset.recordTitle.replace(/[\\/:*?"<>|]/g,'') + '-학습기록.txt';
      document.body.append(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(href), 30000);
      status.textContent = '작성한 내용의 TXT 다운로드를 요청했습니다. 내려받은 파일을 확인해 주세요.';
    });
    const preparePrint = () => fields.forEach(field => {
      let value = field.parentElement.querySelector('.lg-print-value');
      if (!value) { value = document.createElement('div'); value.className = 'lg-print-value'; field.after(value); }
      value.textContent = field.value || ' '; // Print long entries without a clipped textarea.
    });
    window.addEventListener('beforeprint', preparePrint);
    window.addEventListener('afterprint', () => document.body.classList.remove('lg-print-record'));
    print.addEventListener('click', () => {
      preparePrint(); document.body.classList.add('lg-print-record'); window.print();
    });
  }
})();
