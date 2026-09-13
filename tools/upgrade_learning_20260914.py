"""Bounded, repeatable post-hub upgrade. Does not publish or regenerate local pages.

Inputs are authored HTML/JSON plus verified official assets. Existing target HTML
comes from the pinned clean baseline. Refuse unknown edits on repeat execution.
Run with the local bs4 dependency path recorded in the handoff.
"""
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, unquote
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
import hashlib, html, json, re, shutil, subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tools/data/learning-upgrade'
REPORT = ROOT / 'tools/reports/learning-upgrade'
CACHE = Path('C:/Users/1992k/Desktop/CodexData/tmp/coaching8-official-20260914')
BASE = '6840db69e'
ORIGIN = 'https://xn--zj4b74v1taq8c.com'
DATE = '2026-09-14'
ASSET = '/assets/official-learning-20260914/'
STYLE = '/assets/learning-upgrade.css?v=20260914-2'
NEW = '학습코칭/index.html'
CORE = ['index.html', '학습가이드/index.html', '상담문의/index.html']

def git_file(rel):
    return subprocess.check_output(['git','show',f'{BASE}:{rel}'],cwd=ROOT).decode('utf-8-sig')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def esc(value):
    return html.escape(str(value), quote=True)

def soup_of(text):
    return BeautifulSoup(text, 'html.parser')

def fragment(text):
    return soup_of(text)

def url_for(rel):
    return ORIGIN + '/' + rel.removesuffix('index.html')

def add_fragment(parent, text):
    parent.append(fragment(text))

def schema_graph(soup):
    graph=[]
    for s in soup.select('script[type="application/ld+json"]'):
        obj=json.loads(s.string or s.get_text())
        graph.extend(obj.get('@graph',[obj]))
    return graph

def page_questions(soup):
    result=[]
    for item in soup.select('details[data-learning-faq],details.faq-item,#hub-faq-list details'):
        summary=item.find('summary')
        if summary and item.find('p'):
            result.append({'@type':'Question','name':summary.get_text(' ',strip=True),
                'acceptedAnswer':{'@type':'Answer','text':' '.join(p.get_text(' ',strip=True) for p in item.find_all('p'))}})
    return result

def update_metadata(soup, title, description, canonical):
    soup.title.string=title
    for key,val in [('description',description),('twitter:title',title),('twitter:description',description),
                    ('og:title',title),('og:description',description),('og:url',canonical)]:
        attr='property' if key.startswith('og:') else 'name'
        m=soup.find('meta',attrs={attr:key})
        if not m:
            m=soup.new_tag('meta',attrs={attr:key}); soup.head.append(m)
        m['content']=val
    soup.select_one('link[rel="canonical"]')['href']=canonical

def schema_update(soup, rel):
    canonical=url_for(rel)
    graph=schema_graph(soup)
    questions=page_questions(soup)
    graph=[n for n in graph if n.get('@type')!='FAQPage']
    title=soup.title.get_text()
    description=soup.select_one('meta[name="description"]')['content']
    main_sections=[]
    for section in soup.main.select('section[id]'):
        h=section.find(['h2','h1'])
        if h:
            main_sections.append({'@type':'WebPageElement','@id':canonical+'#'+section['id'],
                'name':h.get_text(' ',strip=True),'url':canonical+'#'+section['id']})
    for n in graph:
        types=n.get('@type',[])
        types=[types] if isinstance(types,str) else types
        if any(t in types for t in ['WebPage','CollectionPage','Article']):
            n['dateModified']=DATE
            if 'Article' not in types:
                n['name']=title; n['description']=description
                n['hasPart']=main_sections
                n['about']=[{'@type':'Thing','name':soup.h1.get_text(' ',strip=True)}]
            n.setdefault('mentions',[])
            if isinstance(n['mentions'],dict): n['mentions']=[n['mentions']]
            n['mentions'] += [{'@type':'WebPage','@id':ORIGIN+'/학습코칭/#webpage','url':ORIGIN+'/학습코칭/','name':'4C 코칭과 AI 학습 안내'}] if rel!=NEW else []
    if questions:
        graph.append({'@type':'FAQPage','@id':canonical+'#faq','url':canonical,
            'isPartOf':{'@id':canonical+'#webpage'},'mainEntity':questions})
    for old in soup.select('script[type="application/ld+json"]'): old.decompose()
    script=soup.new_tag('script',type='application/ld+json')
    script.string=json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    soup.head.append(script)

def navigation(soup):
    soup.body['class']=list(dict.fromkeys(soup.body.get('class',[])+['learning-upgraded']))
    soup.head.append(soup.new_tag('link',rel='stylesheet',href=STYLE))
    nav=soup.select_one('.nav-links')
    if nav:
        anchor=soup.new_tag('a',href='/학습코칭/'); anchor.string='학습코칭·AI'
        first=nav.find('a')
        if first: first.insert_after(anchor)
        else: nav.append(anchor)
    for span in soup.select('.footer-meta span'):
        if '콘텐츠 최종 점검' in span.get_text(): span.string='콘텐츠 최종 점검 '+DATE

def add_guide(soup):
    ids=['consultation-start','diagnosis','by-grade','planner','relearning','exam-plan','feedback','guide-answers']
    for section,sid in zip(soup.main.select(':scope > section.section'),ids): section['id']=sid
    hero=soup.select_one('.page-hero')
    hero.insert_after(fragment('<nav class="lu-quick" aria-label="학습가이드 목차">'+''.join(
        f'<a href="#{sid}">{label}</a>' for sid,label in [('diagnosis','현재 수준'),('by-grade','학년별 기준'),('planner','플래너'),('relearning','오답 복습'),('exam-plan','시험 준비'),('feedback','피드백')])+'</nav>'))
    add_fragment(soup.select_one('#diagnosis .section-panel'),'<a class="lu-text-link" href="/학습코칭/#four-c">진단이 교재·지도·상담으로 이어지는 4C 안내 →</a>')
    add_fragment(soup.select_one('#planner .section-panel'),'<a class="lu-text-link" href="/학습코칭/#daily-learning">공식 계획·학습·생활 관리 설명 보기 →</a>')
    add_fragment(soup.select_one('#relearning .section-panel'),'<a class="lu-text-link" href="/학습코칭/#ai-programs">AI 분석 자료를 복습에 활용할 때 확인할 점 →</a>')
    add_fragment(soup.main,'<section class="lu-section lu-tint" id="guide-next"><p class="lu-kicker">학습 방법에서 실제 상담으로</p><h2>필요한 도움을 정리했다면,<br>학년·과목에 맞는 안내를 찾아보세요.</h2><p>위 점검 항목은 학습 상태를 파악하기 위한 일반 기준입니다. 교재·학습량·AI 프로그램과 소통 방식은 학생의 상태와 센터 운영에 따라 달라집니다.</p><div class="lu-actions"><a class="lu-button" href="/과목별학원/">학년·과목별 지역 안내</a><a class="lu-button" href="/전국학원/">고등 영어·수학·영수 안내</a><a class="lu-button lu-primary" href="/상담문의/#consult-form">상담 메모로 정리하기</a></div></section>')

def add_contact(soup):
    block='<section class="lu-section lu-tint" id="program-questions"><p class="lu-kicker">프로그램과 지점 정보 함께 확인</p><h2>상담할 때 이런 질문을 남겨보세요.</h2><div class="lu-grid lu-three"><article class="lu-card"><h3>처음과 다음 진단</h3><p>처음 살핀 어려움을 이후 수업에서 어떻게 다시 확인하나요? 완료한 분량 외에 이해 정도를 확인할 기록도 있나요?</p><a href="/학습코칭/#four-c">4C 과정 이해하기 →</a></article><article class="lu-card"><h3>AI 도구의 활용</h3><p>학생 학년에서 사용할 수 있는 프로그램은 무엇인가요? 화면의 결과를 교재 공부와 복습으로 어떻게 연결하나요?</p><a href="/학습코칭/#ai-programs">공식 프로그램 대상 보기 →</a></article><article class="lu-card"><h3>방문할 지점의 운영</h3><p>정확한 지점명과 주소, 개설 과목과 학년, 시간표와 교습비를 확인하세요. 동네 페이지가 곧 그 동네의 별도 센터를 뜻하지는 않습니다.</p><a href="/과목별학원/">학년·과목의 지역 안내 찾기 →</a></article></div></section>'
    soup.select_one('#consult-form').insert_before(fragment(block))

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    topics=json.loads((ROOT/'tools/data/hub-guides/subject-copy.json').read_text(encoding='utf-8'))
    briefs=json.loads((DATA/'hub-briefs.json').read_text(encoding='utf-8'))
    assert len(topics)==len(briefs)==26
    targets=CORE+list(topics)+[NEW]
    manifest_path=CACHE/'manifest.json' if (CACHE/'manifest.json').exists() else DATA/'sources.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    previous=json.loads((REPORT/'generation.json').read_text(encoding='utf-8')) if (REPORT/'generation.json').exists() else {'outputs':{}}
    build_date=previous.get('build_date',format_datetime(datetime.now(timezone(timedelta(hours=9)))))
    baselines={rel:git_file(rel) for rel in targets if rel!=NEW}
    for rel in targets:
        p=ROOT/rel
        if p.exists():
            allowed=[previous['outputs'].get(rel)]
            if rel in baselines: allowed += [sha(baselines[rel].encode()),sha(subprocess.check_output(['git','show',f'{BASE}:{rel}'],cwd=ROOT))]
            # Git checkout may use CRLF while the repository stores LF.
            if sha(p.read_bytes()) not in allowed and p.read_text(encoding='utf-8-sig')!=baselines.get(rel):
                raise RuntimeError('Unrecognized edit; preserve and review: '+rel)
    selected=['brand-learning.png','learning-space.png','four-c.png','learning-planner.png','ai-english.png','ai-math.png']
    vids={'brand':('59Tna9pZWrk','와와 브랜드 소개'), 'director':('f_skFu40U04','와와 원장 인터뷰'), 'study':('UIXUaBZdNXU','은평점 시험기간 공부법')}
    assets={x['file']:x for x in manifest['images']}
    videos={x['id']:x for x in manifest['videos']}
    selected += [videos[v[0]]['thumbnail_file'] for v in vids.values()]
    dest=ROOT/ASSET.lstrip('/'); dest.mkdir(parents=True,exist_ok=True)
    for file in selected:
        source=CACHE/file if (CACHE/file).exists() else dest/file
        expected=assets[file]['sha256'] if file in assets else next(v['thumbnail_sha256'] for v in videos.values() if v['thumbnail_file']==file)
        assert sha(source.read_bytes()).lower()==expected.lower(), 'Source asset changed: '+file
        if source.resolve()!= (dest/file).resolve(): shutil.copy2(source,dest/file)
    if manifest_path.resolve()!=(DATA/'sources.json').resolve(): shutil.copy2(manifest_path,DATA/'sources.json')
    def render(text):
        def img(m):
            key,alt,loading=m.groups(); info=assets[key+'.png']
            if key=='brand-learning': alt='와와 공식 자료의 영어 Daily Checkup 학습 점검 예시'
            if key=='ai-english': alt='와와 공식 초등 AI 영어 말하기 학습 화면 예시'
            extra=' fetchpriority="high"' if loading=='eager' else ''
            return f'<img src="{ASSET}{info["file"]}" width="{info["width"]}" height="{info["height"]}" alt="{esc(alt)}" loading="{loading}" decoding="async"{extra}>'
        text=re.sub(r'\{\{image:([^:]+):([^:]+):(lazy|eager)\}\}',img,text)
        def vid(m):
            vid,title=vids[m[1]]; info=videos[vid]
            return f'<a class="lu-video" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener noreferrer" aria-label="{title} · YouTube에서 새 창으로 보기"><img src="{ASSET}{info["thumbnail_file"]}" width="480" height="360" alt="{title} 공식 영상 썸네일" loading="lazy" decoding="async"><span>{title}<small>▶ YouTube에서 보기 · 새 창</small></span></a>'
        return re.sub(r'\{\{video:(\w+)\}\}',vid,text)
    output={}; details=[]
    for rel in targets:
        soup=soup_of(baselines.get(rel,baselines['index.html']))
        canonical=url_for(rel)
        fixed=(soup.title.get_text(),soup.h1.get_text(),soup.select_one('link[rel="canonical"]')['href'],soup.select_one('meta[property="og:url"]')['content'])
        old_images=[str(i) for i in soup.main.select('img')]
        navigation(soup)
        if rel=='index.html':
            soup.main.clear(); add_fragment(soup.main,render((DATA/'home.html').read_text(encoding='utf-8')))
            update_metadata(soup,'코칭센터 | 와와 4C 학습코칭·AI 영어·수학 안내','와와 4C 학습코칭과 AI 영어·수학·국어·독서 프로그램을 살펴보세요. 학년·과목별 지역 학원 안내와 진단·플래너·오답 복습·상담 준비를 연결합니다.',canonical)
        elif rel==NEW:
            soup.main.clear(); add_fragment(soup.main,render((DATA/'coaching.html').read_text(encoding='utf-8')))
            soup.body['class']=['core-page','core-coaching','learning-upgraded']
            for node in soup.select('[href],[src]'):
                for attr in ['href','src']:
                    value=node.get(attr,'')
                    if value and not value.startswith(('/','#','http:','https:','tel:','sms:','data:')): node[attr]=urljoin('/',value)
            for a in soup.select('.nav-links a'):
                a.attrs.pop('class',None)
                if a.get('href')=='/학습코칭/': a['class']='active'; a['aria-current']='page'
            update_metadata(soup,'와와 4C 코칭·AI 학습 안내 | 진단에서 복습까지','와와 공식 4C 학습관리, 플래너와 오답 복습, AI 영어·수학·국어·독서의 대상 학년과 활용 질문을 설명합니다. 공식 이미지·영상과 상담 확인 사항을 함께 살펴보세요.',canonical)
            graph=[{'@type':'WebPage','@id':canonical+'#webpage','url':canonical,'name':soup.title.get_text(),'isPartOf':{'@id':ORIGIN+'/#website'},'publisher':{'@id':ORIGIN+'/#organization'},'inLanguage':'ko-KR'},
                {'@type':'BreadcrumbList','@id':canonical+'#breadcrumb','itemListElement':[{'@type':'ListItem','position':1,'name':'홈','item':ORIGIN+'/'},{'@type':'ListItem','position':2,'name':'학습코칭·AI','item':canonical}]}]
            for old in soup.select('script[type="application/ld+json"]'): old.decompose()
            script=soup.new_tag('script',type='application/ld+json'); script.string=json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False); soup.head.append(script)
            soup.main.insert(0,fragment('<nav class="lu-section" style="padding-top:20px;padding-bottom:0" aria-label="현재 위치"><a href="/">홈</a> <span aria-hidden="true"> / </span><span>학습코칭·AI</span></nav>'))
        elif rel=='학습가이드/index.html': add_guide(soup)
        elif rel=='상담문의/index.html': add_contact(soup)
        else:
            key=Path(rel).parent.name; b=briefs[key]
            jumps=soup.select_one('.hub-guide-jumps')
            directory=soup.select_one('#hub-directory')
            jumps.insert_after(directory.extract())
            brief=f'<section class="lu-section lu-hub-brief" id="hub-coaching-connection" data-learning-upgrade="brief"><p class="lu-kicker">{esc(topics[rel]["label"])} · 코칭과 연결해서 보기</p><h2>{esc(b[0])}</h2><p>{esc(b[1])}</p><p>{esc(b[2])}</p><div class="lu-actions"><a class="lu-button" href="/학습코칭/#{b[3]}">{esc(b[4])} →</a><a class="lu-text-link" href="/학습가이드/#{b[5]}">{esc(b[6])} →</a></div></section>'
            directory.insert_after(fragment(brief))
            add_fragment(jumps.select_one('.hub-wrap'),'<a href="#hub-coaching-connection">코칭·AI 연결</a>')
            for script in soup.select('script[src]'):
                if 'directory.js' in script['src']: script['src']='/assets/directory-learning-v2.js?v=20260914-2'
            if rel=='과목별학원/index.html':
                grid=directory.select_one('.category-grid')
                assert grid and len(grid.select(':scope > a'))==21
                group_names=['학습 유형으로 찾기','고등 학년별 안내','중등 학년별 안내','초등 학년별 안내']
                groups=[[],[],[],[]]
                for a in list(grid.select(':scope > a')):
                    path=unquote(a['href']); idx=1 if re.search('고[12]',path) else 2 if re.search('중[123]',path) else 3 if re.search('초[3456]',path) else 0
                    groups[idx].append(a.extract())
                for label,items in zip(group_names,groups):
                    section=soup.new_tag('section',attrs={'class':'lu-hub-group'}); h=soup.new_tag('h3'); h.string=label; section.append(h)
                    sub=soup.new_tag('div',attrs={'class':'category-grid'})
                    for a in items: sub.append(a)
                    section.append(sub); grid.insert_before(section)
                grid.decompose()
            assert fixed==(soup.title.get_text(),soup.h1.get_text(),soup.select_one('link[rel="canonical"]')['href'],soup.select_one('meta[property="og:url"]')['content'])
            assert old_images==[str(i) for i in soup.main.select('img')], 'Preserve hub images and order'
        schema_update(soup,rel)
        text=str(soup)
        assert '{{' not in text, 'Unresolved content placeholder'
        p=ROOT/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8',newline='\n')
        output[rel]=sha(p.read_bytes()); details.append({'path':rel,'url':canonical,'title':soup.title.get_text(),'faq':len(page_questions(soup))})
    ns='http://www.sitemaps.org/schemas/sitemap/0.9'; ET.register_namespace('',ns)
    sm=ET.fromstring(git_file('sitemap.xml')); changed_urls={unquote(url_for(p)) for p in targets}
    for node in sm:
        loc=node.find('{'+ns+'}loc')
        if unquote(loc.text) in changed_urls:
            last=node.find('{'+ns+'}lastmod')
            if last is None: last=ET.SubElement(node,'{'+ns+'}lastmod')
            last.text=DATE
    url=ET.SubElement(sm,'{'+ns+'}url'); ET.SubElement(url,'{'+ns+'}loc').text=url_for(NEW); ET.SubElement(url,'{'+ns+'}lastmod').text=DATE
    ET.indent(sm); ET.ElementTree(sm).write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    ET.register_namespace('atom','http://www.w3.org/2005/Atom')
    rss=ET.fromstring(git_file('rss.xml')); channel=rss.find('channel'); channel.find('lastBuildDate').text=build_date
    for item in channel.findall('item'):
        match=next((d for d in details if unquote(d['url'])==unquote(item.findtext('link',''))),None)
        if match:
            item.find('title').text=match['title']
            page=soup_of((ROOT/match['path']).read_text(encoding='utf-8'))
            if item.find('description') is not None: item.find('description').text=page.select_one('meta[name="description"]')['content']
    new=soup_of((ROOT/NEW).read_text(encoding='utf-8')); item=ET.Element('item')
    for tag,value in [('title',new.title.get_text()),('link',url_for(NEW)),('guid',url_for(NEW)),('description',new.select_one('meta[name="description"]')['content']),('pubDate',build_date)]: ET.SubElement(item,tag).text=value
    channel.insert(list(channel).index(channel.find('item')),item)
    ET.indent(rss); ET.ElementTree(rss).write(ROOT/'rss.xml',encoding='utf-8',xml_declaration=True)
    (REPORT/'generation.json').write_text(json.dumps({'baseline':BASE,'date':DATE,'build_date':build_date,'outputs':output,'pages':details,'assets':selected,'deployment':'not requested; local only'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'pages':len(output),'new':NEW,'hubs':len(topics),'assets':len(selected),'sitemap':len(sm),'rss':len(channel.findall('item'))},ensure_ascii=False))

if __name__=='__main__': main()
