(() => {
  const cards = [...document.querySelectorAll('[data-curriculum-card]')];
  const search = document.querySelector('[data-curriculum-search]');
  if (!search) return;
  const grade = document.querySelector('[data-curriculum-grade]');
  const stage = document.querySelector('[data-curriculum-stage]');
  const subject = document.querySelector('[data-curriculum-subject]');
  const query = new URLSearchParams(location.search);
  search.value = (query.get('cq') || '').slice(0,100);
  const valid = (el,v) => [...el.options].some(o=>o.value===v) ? v : '';
  grade.value = valid(grade,query.get('cg') || ''); subject.value = valid(subject,query.get('cs') || '');
  stage.value = valid(stage,query.get('cstage') || '');
  const filter = () => {
    const words = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean); let count=0;
    cards.forEach(card => {
      const match = (!stage.value || card.dataset.stage===stage.value) && (!grade.value || card.dataset.grade===grade.value) && (!subject.value || card.dataset.subject===subject.value) && words.every(w=>card.dataset.search.toLowerCase().includes(w));
      card.hidden=!match;if(match)count++;
    });
    document.querySelector('[data-curriculum-count]').textContent=`${count===66?'전체':'조건에 맞는'} ${count}개 학년·과목 안내`;
    document.querySelector('[data-curriculum-empty]').hidden=count>0;
    const url=new URL(location.href);
    Object.entries({cq:search.value.trim(),cg:grade.value,cs:subject.value,cstage:stage.value}).forEach(([k,v])=>v?url.searchParams.set(k,v):url.searchParams.delete(k));
    history.replaceState(null,'',url.pathname+url.search+url.hash);
  };
  search.addEventListener('input',filter);grade.addEventListener('change',filter);subject.addEventListener('change',filter);
  stage.addEventListener('change',()=>{grade.value='';filter();});
  document.querySelector('[data-curriculum-reset]').addEventListener('click',()=>{search.value='';grade.value='';subject.value='';stage.value='';filter();search.focus();});
  filter();document.documentElement.dataset.curriculumReady='true';
})();
