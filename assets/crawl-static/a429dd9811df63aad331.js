/* Original images are fetched only after a visible image is selected. */
(() => {
  let dialog, image, scroller, status, lastFocus, originalWidth, scale = 1;
  function resize(next) {
    scale = Math.max(.1, Math.min(3, next));
    image.style.width = `${Math.round(originalWidth * scale)}px`;
    status.textContent = `${Math.round(scale * 100)}% · 글씨가 작으면 확대하고 좌우·위아래로 움직여 보세요.`;
  }
  function create() {
    dialog = document.createElement('dialog');
    dialog.className = 'crawl-image-dialog';
    dialog.setAttribute('aria-labelledby', 'crawl-zoom-title');
    dialog.innerHTML = '<div class="crawl-image-toolbar"><strong id="crawl-zoom-title"></strong><button type="button" data-action="fit">화면 맞춤</button><button type="button" data-action="original">원본 크기</button><button type="button" data-action="plus" aria-label="이미지 더 확대">＋</button><button type="button" data-action="minus" aria-label="이미지 축소">－</button><a target="_blank" rel="noopener">원본 열기</a><button type="button" data-action="close">닫기</button></div><p class="crawl-image-status" role="status">원본 이미지를 불러오는 중입니다.</p><div class="crawl-image-scroll" tabindex="0" aria-label="확대 이미지, 스크롤하여 전체 내용 보기"><img alt=""></div>';
    document.body.append(dialog);
    image = dialog.querySelector('img'); scroller = dialog.querySelector('.crawl-image-scroll'); status = dialog.querySelector('[role="status"]');
    dialog.addEventListener('click', event => {
      const action = event.target.closest('[data-action]')?.dataset.action;
      if (action === 'close') dialog.close();
      if (action === 'original') resize(1);
      if (action === 'fit') resize(Math.min(1, (scroller.clientWidth - 16) / originalWidth));
      if (action === 'plus') resize(scale * 1.25);
      if (action === 'minus') resize(scale / 1.25);
    });
    dialog.addEventListener('close', () => { image.removeAttribute('src'); document.documentElement.style.overflow = ''; lastFocus?.focus(); });
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-crawl-zoom]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || !('HTMLDialogElement' in window)) return;
    event.preventDefault(); if (!dialog) create(); lastFocus = link;
    dialog.querySelector('strong').textContent = link.dataset.crawlZoom;
    dialog.querySelector('a').href = link.href;
    image.alt = `${link.dataset.crawlZoom} 확대 원본`;
    originalWidth = Number(link.dataset.originalWidth) || 918;
    status.textContent = '원본 이미지를 불러오는 중입니다.';
    dialog.showModal(); document.documentElement.style.overflow = 'hidden'; resize(1);
    image.onload = () => { originalWidth = image.naturalWidth; resize(1); scroller.scrollLeft = 0; scroller.scrollTop = Number(link.dataset.cropY) || 0; };
    image.onerror = () => { status.textContent = '원본을 불러오지 못했습니다. 원본 열기로 다시 확인해 주세요.'; };
    image.src = link.href;
  });
})();
