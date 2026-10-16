(() => {
  'use strict';
  document.querySelectorAll('.kk-hub-select').forEach(select => {
    const section = select.closest('.kk-directions');
    const content = section.querySelector('.kk-hub-content');
    let request = 0, selected = select.value;
    select.addEventListener('change', async () => {
      const option = select.selectedOptions[0], token = ++request;
      try {
        const response = await fetch(option.dataset.content, {credentials: 'same-origin'});
        if (!response.ok) throw new Error('map content unavailable');
        const data = await response.json();
        if (token !== request) return;
        content.innerHTML = data.html;
        section.querySelector('.kk-selected-name').textContent = option.textContent;
        selected = select.value;
      } catch (_) { if (token === request) select.value = selected; }
    });
  });
})();