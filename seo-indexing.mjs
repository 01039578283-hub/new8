/** Restore only individually reviewed pages; never remove all noindex tags. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const root = path.dirname(fileURLToPath(import.meta.url));
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'seo-indexing.json'), 'utf8'));
const scriptPattern = /(<script\b[^>]*type=["']application\/ld\+json["'][^>]*>)([\s\S]*?)(<\/script>)/gi;
const escape = value => value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');
const hasType = (node, type) => [node['@type']].flat().includes(type);
function visit(node, fn) {
  if (!node || typeof node !== 'object') return;
  if (!Array.isArray(node)) fn(node);
  for (const value of Object.values(node)) visit(value, fn);
}

export function transform(html, p) {
  const canonical = html.match(/<link\b(?=[^>]*rel=["']canonical["'])(?=[^>]*href=["']([^"']+))[^>]*>/i)?.[1];
  if (canonical !== p.canonical || new URL(canonical).origin !== manifest.origin) throw Error(`Canonical mismatch: ${p.path}`);
  // The older recovery rule below intentionally protects exact availability
  // wording. A reviewed section rewrite uses a stricter whole-page fingerprint
  // instead: it must still be one of these same 50 individually approved pages.
  if (html.includes('data-section-refinement="20260923-2"')) {
    const review=p.sectionRefinementReview;
    const tracker='<script defer src="https://wawa-visit-collector.clean-peach-8202.chatgpt.site/tracker.js" data-site="wawa-09" crossorigin="anonymous" referrerpolicy="no-referrer"></script>';
    const fingerprint=createHash('sha256').update(html.replace(tracker,''),'utf8').digest('hex');
    if (!review || review.version!=='20260923-2' || fingerprint!==review.sourceSha256) throw Error(`Refined page changed; re-audit required: ${p.path}`);
    const robots=[...html.matchAll(/<meta\b(?=[^>]*name=["']robots["'])[^>]*>/gi)];
    if (robots.length!==1 || /\bnoindex\b/i.test(robots[0][0])) throw Error(`Reviewed indexability changed: ${p.path}`);
    const visible=html.split('</head>')[1];
    if (!review.requiredFacts.every(s=>visible?.includes(escape(s)))) throw Error(`Reviewed center facts missing: ${p.path}`);
    // Keep the actual new modification date and matching visible FAQ/schema.
    return {html,changed:false};
  }
  const beforeTitle = html.match(/<title>[\s\S]*?<\/title>/i)?.[0];
  const beforeImages = [...html.matchAll(/<img\b[^>]*>/gi)].map(m => m[0]);
  const gs = `${p.grade} ${p.subject}`;
  const intro = `${p.center}의 제공 자료에는 ${gs} 수업이 가능 범위로 기재돼 있습니다. ` +
    (p.conditional ? '초등 저학년은 첫 상담에서 정해진 학습 과정을 스스로 수행할 수 있는지 확인한 뒤 수용 여부를 결정합니다.' : '현재 모집 여부와 수업 시간은 등록 전에 센터에 확인해 주세요.');
  const body = p.conditional
    ? `${p.center}의 ${gs} 수업은 첫 상담에서 학생의 자기주도 학습 가능 여부를 확인한 뒤 수용 여부를 결정합니다. 방문 전 상담 가능한 시간을 문의하세요.`
    : `${gs}은 ${p.center}의 수업 가능 범위입니다. 수업 가능 학년과 현재 모집 상황은 다를 수 있으므로 시작 시점과 시간표는 상담에서 확인하세요.`;
  const card = p.conditional
    ? `${gs} 수업은 첫 상담에서 학습 과정을 스스로 수행할 수 있는지 확인한 뒤 수용 여부를 결정합니다.`
    : `제공된 ${p.center} 자료에 ${gs}이 수업 가능 학년·과목으로 기재돼 있습니다. 현재 모집 여부와 시간표는 별도로 확인해 주세요.`;
  const faq = `네. 제공된 ${p.center} 자료의 대상 범위에 ${gs}이 포함됩니다. ` +
    (p.conditional ? '다만 초등 저학년은 첫 상담에서 학습 과정을 스스로 수행할 수 있는지 확인한 뒤 수용 여부를 결정합니다.' : `${p.locality}에서 통학할 때는 현재 모집 여부와 가능한 수업 시간을 상담에서 함께 확인해 주세요.`);
  const replacements = [
    [`센터 자료에는 ${gs} 가능 여부가 표시되지 않았습니다. 제공 여부를 추정하지 말고 상담에서 대상 학년과 과목부터 확인하세요.`, intro],
    [`확보한 센터 정보만으로는 ${gs} 과정 제공을 확인할 수 없습니다. 가능하다고 전제하지 말고 상담할 때 학년·과목 범위를 먼저 물어보세요.`, intro],
    [`현재 자료에서는 ${gs} 수업 가능 여부가 확인되지 않습니다. 등록을 검토하기 전에 센터에 대상 학년과 운영 과목을 직접 확인해야 합니다.`, intro],
    [`센터 자료에서 ${gs} 과정의 제공 여부를 확인할 수 없습니다. 상담 전에 대상 학년·과목을 먼저 문의하고 가능하다는 전제 없이 비교하세요.`, body],
    [`${gs} 과정은 확보된 센터 정보의 가능 범위에 나타나지 않습니다. 운영 여부와 등록 가능한 시점을 센터에 직접 물어봐야 합니다.`, body],
    [`현재 정보에는 ${gs} 과정 제공 여부가 비어 있습니다. 학년과 과목이 모두 가능한지 확인한 뒤 상담 일정을 정하세요.`, body],
    [`확인된 센터 정보만으로는 ${p.grade} 가능 여부가 확인되지 않아 상담이 필요합니다.`, card],
    [`센터 자료에서 ${gs} 과정의 운영 여부를 찾을 수 없습니다. 제공한다고 전제하지 말고 ${p.locality} 상담에서 대상 학년과 과목을 먼저 물어봐야 합니다.`, faq],
  ];
  let next = html;
  for (const [before, after] of replacements) next = next.replaceAll(before, after);
  const visible = next.split('</head>')[1];
  for (const text of [intro, body, card, faq]) if (!visible?.includes(text)) throw Error(`Availability copy changed; review required: ${p.path}`);
  if (replacements.some(([before]) => next.includes(before))) throw Error(`Stale availability: ${p.path}`);
  let robotCount = 0;
  next = next.replace(/<meta\b(?=[^>]*name=["']robots["'])[^>]*>/gi, tag => {
    robotCount++;
    return tag.replace(/\bnoindex\b/gi, 'index');
  });
  if (robotCount !== 1 || /<meta\b[^>]*noindex[^>]*>/i.test(next)) throw Error(`Unexpected robots directive: ${p.path}`);
  next = next.replace(/<meta\b[^>]*>/gi, tag => {
    const field = tag.match(/(?:name|property)=["']([^"']+)["']/i)?.[1];
    if (!['description', 'og:description', 'twitter:description'].includes(field)) return tag;
    return tag.replace(/content=(["'])[\s\S]*?\1/i, `content="${escape(p.description)}"`);
  });
  next = next.replace(scriptPattern, (block, open, raw, close) => {
    const graph = JSON.parse(raw), before = JSON.stringify(graph);
    visit(graph, n => {
      if (['WebPage', 'Article', 'Service'].some(type => hasType(n, type))) n.description = p.description;
      if (hasType(n, 'Article') || hasType(n, 'WebPage')) n.dateModified = manifest.modifiedAt;
      if (hasType(n, 'Service') && n.audience?.audienceType === `${gs} 수업 가능 여부 상담 확인`) {
        n.audience.audienceType = p.conditional ? `${gs} 상담 후 수용 여부 확인` : `${gs} 학습 대상`;
      }
    });
    return before === JSON.stringify(graph) ? block : open + JSON.stringify(graph) + close;
  });
  next = next.replace(/(<span>최근 내용 정리<\/span>)<time[^>]*>[\s\S]*?<\/time>/g,
    `$1<time datetime="${manifest.modifiedAt}">${manifest.modifiedAt.slice(0, 10).replaceAll('-', '.')}</time>`);
  if (next.match(/<title>[\s\S]*?<\/title>/i)?.[0] !== beforeTitle ||
      JSON.stringify([...next.matchAll(/<img\b[^>]*>/gi)].map(m => m[0])) !== JSON.stringify(beforeImages)) throw Error(`Title or image changed: ${p.path}`);
  return {html: next, changed: next !== html};
}

export function run({outputRoot = root, check = false} = {}) {
  const pending = [], failures = [];
  for (const p of manifest.pages) {
    const file = path.resolve(outputRoot, p.path);
    if (!file.startsWith(path.resolve(outputRoot) + path.sep)) throw Error('Invalid allowlist path');
    try { const result = transform(fs.readFileSync(file, 'utf8'), p); if (result.changed) pending.push({file, ...result}); }
    catch (error) { failures.push({path: p.path, error: error.message}); }
  }
  const sitemapFile = path.join(outputRoot, 'sitemap.xml');
  const sitemap = fs.readFileSync(sitemapFile, 'utf8');
  if (!sitemap.includes('</urlset>')) throw Error('Unexpected sitemap format');
  const missing = manifest.pages.filter(p => !sitemap.includes(`<loc>${p.canonical}</loc>`));
  const entries = missing.map(p => `  <url>\n    <loc>${p.canonical}</loc>\n    <lastmod>${manifest.modifiedAt.slice(0, 10)}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>\n`).join('');
  if (failures.length) throw Error(JSON.stringify(failures));
  if (!check) {
    for (const p of pending) fs.writeFileSync(p.file, p.html, 'utf8');
    if (missing.length) fs.writeFileSync(sitemapFile, sitemap.replace('</urlset>', entries + '</urlset>'), 'utf8');
  }
  const result = {mode: check ? 'check' : 'applied', verifiedPages: manifest.pages.length, changedPages: pending.length, sitemapAdded: missing.length};
  console.log(JSON.stringify(result));
  return result;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = run({check: process.argv.includes('--check'), outputRoot: path.resolve(root, process.argv.find(v => v.startsWith('--root='))?.slice(7) || '.')});
  if (process.argv.includes('--check') && (result.changedPages || result.sitemapAdded)) process.exitCode = 1;
}
