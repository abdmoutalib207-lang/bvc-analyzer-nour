"""Bounded, issuer-specific extraction of primary business disclosures.

A recognized table may publish a labelled automatic reading, never a score
input. Unknown layouts remain candidates; failed sources retain dated history.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date,datetime,timezone
from decimal import Decimal
import hashlib,json,re,subprocess,tempfile,unicodedata
from pathlib import Path
from urllib.parse import urlsplit,unquote,urljoin,parse_qs,urlunsplit
from html.parser import HTMLParser
from .official_sources import fetch as fetch_page

VERSION='nour-sector-ingestion-v1'

def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')

def safe_url(url,hosts):
    try:p=urlsplit(url)
    except ValueError:return False
    return p.scheme=='https' and p.port in (None,443) and p.hostname in hosts and not p.username and not p.password and (p.path.lower().endswith('.pdf') or (p.hostname in ('tgcc.ma','www.tgcc.ma') and p.path=='/' and set(parse_qs(p.query))=={'jet_download'} and re.fullmatch('[a-f0-9]{40}',parse_qs(p.query)['jet_download'][0])))

def discovered_url(href,base,hosts):
    url=urljoin(base,href)
    try:
        p=urlsplit(url)
        # Some official pages still print HTTP links; request the same approved
        # host/path over HTTPS, never follow an insecure transport.
        if p.scheme=='http' and p.hostname in hosts and p.port in (None,80) and not p.username and not p.password:
            url=urlunsplit(('https',p.hostname,p.path,p.query,''))
    except ValueError:return None
    return url if safe_url(url,hosts) else None

class DiscoveryLinks(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.context='';self.current=None;self.links=[]
    def handle_data(self,text):self.context=(self.context+' '+text)[-500:]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.current=dict(attrs).get('href')
    def handle_endtag(self,tag):
        if tag=='a':
            if self.current:self.links.append((self.current,' '.join(self.context.split())))
            self.context='';self.current=None

def amount(text,style):
    text=re.sub(r'\s','',text)
    if style=='integer':
        if not re.fullmatch(r'\d+(?:[.]\d{3})*',text):raise ValueError('ambiguous_integer')
        return int(text.replace('.',''))
    if not re.fullmatch(r'\d+(?:[.,]\d+)?',text):raise ValueError('ambiguous_decimal')
    return float(Decimal(text.replace(',','.')))

def extract(profile,pages,url,digest,observed):
    """Only fixed unit/column contracts; one match per field, no fuzzy guessing."""
    head=plain(' '.join(pages[:2]))
    if not re.search(profile['issuer_pattern'],head):raise ValueError('issuer_not_confirmed')
    cover=plain(pages[0])
    pattern=(r'(?:au|resultats au)\s*30\s+juin\s+(20\d{2})' if profile['period_kind']=='semester'
             else r'(?:annuel|annuelle)\s+(20\d{2})')
    years={int(m) for m in re.findall(pattern,cover)}
    if len(years)!=1:raise ValueError('period_not_unique')
    year=years.pop();suffix='06-30' if profile['period_kind']=='semester' else '12-31'
    if f'{year}-{suffix}'>observed[:10]:raise ValueError('future_period')
    document='sha256:'+digest;rows=[];candidates=[]
    for spec in profile['fields']:
        hits=[]
        for n,page in enumerate(pages,1):
            for m in re.finditer(spec['pattern'],page,re.I|re.M):hits.append((n,m))
        if len(hits)!=1:
            candidates.append(dict(field=spec['id'],reason='layout_not_unique',matches=len(hits),url=url,document_hash=document));continue
        page,m=hits[0]
        header=None
        if 'previous' in m.groupdict():
            headers=list(re.finditer(profile['comparison_header_pattern'],pages[page-1][:m.start()],re.I))
            header=headers[-1][0] if headers else None
            expected=profile['comparison_header_template'].format(year=year,previous=year-1)
            if header is None or not re.fullmatch(expected,header,re.I):
                candidates.append(dict(field=spec['id'],reason='column_period_order_unverified',url=url,document_hash=document));continue
        for column,offset in [('value',0),('previous',-1)]:
            if column not in m.groupdict() or m[column] is None:continue
            value=amount(m[column],spec.get('number_style','decimal'))
            if not spec.get('min',0)<=value<=spec.get('max',1e15):
                candidates.append(dict(field=spec['id'],reason='outside_profile_bounds',url=url,document_hash=document));continue
            end=f'{year+offset}-{suffix}'
            rows.append(dict(id=f'{spec["id"]}-{end}',label=spec['label'],value=value,unit=spec['unit'],
                category=spec['category'],scope=profile['scope'],period_start=f'{year+offset}-01-01',period_end=end,
                period_kind=profile['period_kind'],available_from=observed[:10],document=digest,page=page,printed_page='Voir page PDF',
                definition=spec['definition'],currency=spec.get('currency'),metal=spec.get('metal'),
                quantity_basis=spec.get('quantity_basis'),approximate=spec.get('approximate',False),
                note=spec.get('note',''),column_header=header,evidence_excerpt=' '.join(m[0].split())[:300]))
    # Identity between container totals is an independent acceptance contract.
    for relation in profile.get('sum_checks',[]):
        selected={r['id'].rsplit('-',3)[0]:r for r in rows if r['period_end']==f'{year}-{suffix}'}
        names=[relation['total']]+relation['parts']
        if all(n in selected for n in names) and selected[names[0]]['value']!=sum(selected[n]['value'] for n in names[1:]):
            bad={selected[n]['id'] for n in names};rows=[r for r in rows if r['id'] not in bad]
            candidates.append(dict(field=relation['total'],reason='component_sum_mismatch',url=url,document_hash=document))
    reviewed=digest in profile.get('visually_reviewed_hashes',[])
    return rows,dict(title=profile['title'],url=url,document_hash=document,
        review_status='selected_pages_visually_checked' if reviewed else 'automatic_text_extraction',
        observed_at=observed),candidates

def pdf_pages(path):
    result=subprocess.run(['pdftotext','-layout',str(path),'-'],capture_output=True,text=True,timeout=35,check=True)
    pages=result.stdout.split('\f')
    if sum(len(p.strip()) for p in pages)<100:raise ValueError('pdf_requires_ocr')
    return pages

def download(url,profile,cache):
    if not safe_url(url,profile['hosts']):raise ValueError('unapproved_url')
    cache.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(url.encode()).hexdigest();target=cache/(key+'.pdf');tag=cache/(key+'.etag')
    # At most one bounded HTTPS response; validate redirects before accepting.
    with tempfile.NamedTemporaryFile(dir=cache,suffix='.pdf',delete=False) as f:temp=Path(f.name)
    temp_tag=Path(str(temp)+'.etag')
    try:
        cmd=['curl','-fL','--silent','--show-error','--proto','=https','--proto-redir','=https',
             '--max-time','50','--max-filesize','52428800','--etag-save',str(temp_tag),
             '--write-out','%{http_code} %{url_effective}','-o',str(temp)]
        if target.exists() and tag.exists():cmd+=['--etag-compare',str(tag)]
        r=subprocess.run(cmd+[url],capture_output=True,text=True,timeout=55,check=True)
        code,effective=r.stdout.split(' ',1)
        if not safe_url(effective.strip(),profile['hosts']):raise ValueError('redirect_not_approved')
        if code=='304' and target.exists():return target
        if temp.read_bytes()[:5]!=b'%PDF-':raise ValueError('not_pdf')
        temp.replace(target)
        if temp_tag.exists():temp_tag.replace(tag)
        return target
    finally:
        temp.unlink(missing_ok=True);temp_tag.unlink(missing_ok=True)

def collect(config,previous,discovered,cache,now=None,fetch=download,page_fetch=fetch_page):
    observed=now or datetime.now(timezone.utc).isoformat();out=deepcopy(previous or {})
    out.update(version=VERSION,checked_at=observed);out.setdefault('catalogues',{});out['health']={};out['candidates']=[];out.setdefault('incidents',{})
    def issuer(profile):
        urls=list(profile['seeds']);titles={};page_failures=[]
        origins=['https://'+h for h in profile['hosts']]
        for page in profile.get('discovery_pages',[]):
            try:
                body,final,_=page_fetch(page,origins,timeout=12)
                parser=DiscoveryLinks();parser.feed(body.decode('utf-8','replace'))
                for href,title in parser.links:
                    url=discovered_url(href,final,profile['hosts'])
                    if url and re.search(profile['link_title_pattern'],plain(title)):
                        urls.append(url);titles[url]=title
            except (ValueError,OSError):page_failures.append(dict(url=page,reason='discovery_unavailable'))
        for d in discovered.get('documents',[]):
            url=d.get('url','')
            if (profile['symbol'] in d.get('tickers',[]) and safe_url(url,profile['hosts'])
                    and re.search(profile['url_pattern'],unquote(url),re.I)):urls.append(url)
        def rank(u):
            years=re.findall(r'20\d{2}',titles.get(u,'') or unquote(u));short=re.findall(r'(?:S1_|S2_)(\d{2})',u,re.I)
            return max([int(v) for v in years]+[2000+int(v) for v in short]+[0])
        urls=sorted(set(urls),key=lambda u:(rank(u),u),reverse=True)[:config.get('max_documents_per_issuer',2)]
        results=[];failures=page_failures;seen_digests=set()
        for url in urls:
            try:
                path=fetch(url,profile,cache);digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if digest in seen_digests:continue
                seen_digests.add(digest)
                rows,doc,candidates=extract(profile,pdf_pages(path),url,digest,observed)
                results.append((digest,rows,doc,candidates))
            except (ValueError,OSError,subprocess.SubprocessError):
                failures.append(dict(url=url,reason='source_or_contract_unavailable'))
        return profile,results,failures
    with ThreadPoolExecutor(max_workers=3) as pool:
        for profile,results,failures in pool.map(issuer,config['profiles']):
            symbol=profile['symbol'];old=out['catalogues'].get(symbol)
            catalogue=deepcopy(old) if old else dict(schema_version='nour-business-disclosures-v1',symbol=symbol,
                available_from=observed[:10],reviewed_on=observed[:10],validation_status='automatic_text_extraction',documents={},records=[],
                reservations=profile.get('reservations',[]))
            index={r['id']:r for r in catalogue['records']}
            for digest,rows,doc,candidates in results:
                catalogue['documents'][digest]=doc
                for row in rows:
                    prior=index.get(row['id'])
                    if prior and (prior['value'],prior['unit'])==(row['value'],row['unit']):
                        continue  # Preserve first availability and original proof for an identical fact.
                    if prior and prior['document']!=digest and (prior['value'],prior['unit'])!=(row['value'],row['unit']):
                        out['candidates'].append(dict(symbol=symbol,field=row['id'],reason='published_value_conflict',previous_value=prior['value'],proposed_value=row['value'],unit=row['unit'],period_end=row['period_end'],page=row['page'],url=doc['url'],document_hash=doc['document_hash']));continue
                    index[row['id']]=row
                out['candidates'] += [dict(symbol=symbol,**c) for c in candidates]
            catalogue['records']=list(index.values())
            if catalogue['records']:out['catalogues'][symbol]=catalogue
            out['health'][symbol]=dict(status='partial' if failures else 'needs_review' if any(c.get('symbol')==symbol for c in out['candidates']) else 'checked',failures=failures,
                retained_previous=bool(old and failures),records=len(catalogue['records']),checked_at=observed,
                automatic_for_score=False)
            if symbol in out['catalogues']:
                out['catalogues'][symbol]['collection_status']=out['health'][symbol]['status']
            for incident in failures+[c for c in out['candidates'] if c.get('symbol')==symbol]:
                key=hashlib.sha256((symbol+'|'+incident['url']+'|'+incident['reason']).encode()).hexdigest()
                prior=out['incidents'].get(key,{**incident,'symbol':symbol,'first_seen':observed,'occurrences':0})
                out['incidents'][key]={**prior,'last_seen':observed,'occurrences':prior['occurrences']+1}
    return out
