from __future__ import annotations
import argparse
import fitz
import json
import re
import shutil
import hashlib
import unicodedata
from pathlib import Path
from collections import defaultdict

parser = argparse.ArgumentParser(description="Extract the complete HUST eater PDF into source-preserving structured data")
parser.add_argument("pdf", type=Path, help="Input PDF")
parser.add_argument("--output", "-o", type=Path, required=True, help="Output data directory; it will be replaced")
args = parser.parse_args()
PDF = args.pdf.expanduser().resolve()
OUT = args.output.expanduser().resolve()
if not PDF.is_file():
    parser.error(f"PDF does not exist: {PDF}")
if OUT.exists():
    shutil.rmtree(OUT)
(OUT/'pages').mkdir(parents=True)
(OUT/'media').mkdir(parents=True)
(OUT/'source').mkdir(parents=True)
shutil.copy2(PDF, OUT/'source'/'HUSTer的干饭修养.pdf')

def rgb_int_to_hex(c:int)->str:
    return f'#{c:06x}'

def natural_key(s: str):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', s)]

def make_id(prefix: str, text: str, index: int) -> str:
    norm = unicodedata.normalize('NFKC', text).strip().lower()
    digest = hashlib.sha1(norm.encode('utf-8')).hexdigest()[:10]
    return f'{prefix}-{index:03d}-{digest}'

CAPTION_RE = re.compile(r'(美团信息|菜单|范围|外观|照片|分布图|截图)$')
CHAPTER_RE = re.compile(r'^第([一二三四五])章\s*(.+)$')
SECTION_RE = re.compile(r'^(\d+\.\d+)\s+(.+)$')
ENTRY_RE = re.compile(r'^（\s*(\d+)\s*）\s*(.*)$')
RED = 0xEE0000

doc = fitz.open(PDF)
all_lines = []
page_images = defaultdict(list)
page_records = []
media_manifest = []

for pno, page in enumerate(doc, start=1):
    page_dict = page.get_text('dict', sort=True)
    raw_lines = []
    for block in page_dict['blocks']:
        if block.get('type') != 0:
            continue
        for line in block.get('lines', []):
            spans = []
            for sp in line.get('spans', []):
                t = sp.get('text', '')
                if not t:
                    continue
                color = int(sp.get('color', 0))
                spans.append({
                    'text': t,
                    'bbox': [round(v, 3) for v in sp['bbox']],
                    'font': sp.get('font'),
                    'size': round(float(sp.get('size', 0)), 3),
                    'color': rgb_int_to_hex(color),
                    'bold': 'Bold' in (sp.get('font') or ''),
                    'highlighted_recommendation': color == RED,
                })
            if spans:
                raw_lines.append({'bbox':[round(v,3) for v in line['bbox']], 'spans':spans})

    # Word often stores a numbered heading and its title as separate text lines
    # at the same vertical position. Merge such fragments by visual baseline.
    visual_groups = []
    for rl in sorted(raw_lines, key=lambda x:(x['bbox'][1], x['bbox'][0])):
        placed = False
        cy=(rl['bbox'][1]+rl['bbox'][3])/2
        for g in reversed(visual_groups[-5:]):
            gcy=(g['bbox'][1]+g['bbox'][3])/2
            if abs(cy-gcy) <= 2.5:
                g['spans'].extend(rl['spans'])
                g['bbox']=[min(g['bbox'][0],rl['bbox'][0]),min(g['bbox'][1],rl['bbox'][1]),max(g['bbox'][2],rl['bbox'][2]),max(g['bbox'][3],rl['bbox'][3])]
                placed=True
                break
        if not placed:
            visual_groups.append({'bbox':rl['bbox'][:], 'spans':rl['spans'][:]})

    lines = []
    for vg in sorted(visual_groups, key=lambda x:(x['bbox'][1],x['bbox'][0])):
        spans=sorted(vg['spans'], key=lambda x:x['bbox'][0])
        chunks=[]; red_texts=[]; prev_x=None
        for sp in spans:
            if prev_x is not None and sp['bbox'][0]-prev_x > 3.0:
                chunks.append(' ')
            chunks.append(sp['text'])
            prev_x=sp['bbox'][2]
            if sp['highlighted_recommendation']:
                red_texts.append(sp['text'])
        text=''.join(chunks).strip()
        if not text:
            continue
        red_segments=[]
        current_segment=''
        segment_start=None
        nonempty=[i for i,sp in enumerate(spans) if sp['text'].strip()]
        first_nonempty=nonempty[0] if nonempty else 0
        last_nonempty=nonempty[-1] if nonempty else len(spans)-1
        for i,sp in enumerate(spans):
            if sp['highlighted_recommendation']:
                if segment_start is None:
                    segment_start=i
                current_segment += sp['text']
            elif current_segment:
                red_segments.append({'text':current_segment.strip(),'at_line_start':segment_start==first_nonempty,'at_line_end':(i-1)==last_nonempty})
                current_segment=''; segment_start=None
        if current_segment:
            red_segments.append({'text':current_segment.strip(),'at_line_start':segment_start==first_nonempty,'at_line_end':True})
        rec={'page':pno,'text':text,'bbox':[round(v,3) for v in vg['bbox']], 'spans':spans,'red_texts':red_texts,'red_segments':red_segments,'max_size':max(sp['size'] for sp in spans),'order':len(all_lines)}
        lines.append(rec); all_lines.append(rec)

    # Extract every placed image to editable PNG.
    infos = page.get_image_info(xrefs=True)
    for idx, info in enumerate(infos, start=1):
        xref = int(info['xref'])
        pix = fitz.Pixmap(doc, xref)
        if pix.alpha or pix.n > 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        filename = f'p{pno:03d}_img{idx:02d}.png'
        target = OUT/'media'/filename
        pix.save(target)
        bbox = [round(v, 3) for v in info['bbox']]
        # nearest short line below image as caption; fallback nearest line overall.
        below = [l for l in lines if l['bbox'][1] >= bbox[3]-2 and l['bbox'][1] <= bbox[3]+45]
        caption = ''
        if below:
            caption = min(below, key=lambda l: l['bbox'][1]-bbox[3])['text']
        elif lines:
            caption = min(lines, key=lambda l: abs(((l['bbox'][1]+l['bbox'][3])/2)-bbox[3]))['text']
        media_id = f'media-p{pno:03d}-{idx:02d}'
        m = {
            'id': media_id,
            'page': pno,
            'order_on_page': idx,
            'file': f'media/{filename}',
            'xref': xref,
            'bbox': bbox,
            'pixel_width': int(info['width']),
            'pixel_height': int(info['height']),
            'caption': caption,
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'editable': True,
            'source': 'embedded_pdf_image',
        }
        page_images[pno].append(m)
        media_manifest.append(m)
    plain = '\n'.join(l['text'] for l in lines)
    md_lines = []
    for l in lines:
        chunks=[]
        for sp in l['spans']:
            txt=sp['text']
            if sp['highlighted_recommendation']:
                txt=f'<mark class="recommendation">{txt}</mark>'
            chunks.append(txt)
        md_lines.append(''.join(chunks).strip())
    page_obj = {
        'schema_version': '1.0',
        'page_number': pno,
        'width_points': round(page.rect.width, 3),
        'height_points': round(page.rect.height, 3),
        'plain_text': plain,
        'lines': lines,
        'images': page_images[pno],
    }
    (OUT/'pages'/f'page_{pno:03d}.json').write_text(json.dumps(page_obj, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT/'pages'/f'page_{pno:03d}.md').write_text(f'# 第 {pno} 页\n\n'+'\n\n'.join(md_lines)+'\n', encoding='utf-8')
    page_records.append({'page':pno,'json':f'pages/page_{pno:03d}.json','markdown':f'pages/page_{pno:03d}.md','images':[m['id'] for m in page_images[pno]]})

# Detect chapters/sections/entries from pages 4 onward.
chapters=[]; sections=[]; entries=[]
current_chapter=None; current_section=None; current_entry=None
chapter_num_map={'一':1,'二':2,'三':3,'四':4,'五':5}

for line in all_lines:
    if line['page'] < 4:
        continue
    t = re.sub(r'\s+', ' ', line['text']).strip()
    cm = CHAPTER_RE.match(t)
    if cm and line.get('max_size', 0) >= 15:
        current_entry=None
        num=chapter_num_map[cm.group(1)]
        current_chapter={
            'id':f'chapter-{num}', 'number':num, 'title':cm.group(2).strip(),
            'heading':t, 'source_page':line['page'], 'intro_lines':[], 'section_ids':[]
        }
        chapters.append(current_chapter); current_section=None
        continue
    sm=SECTION_RE.match(t)
    if sm and current_chapter and line.get('max_size', 0) >= 13:
        current_entry=None
        sec_id=f'section-{sm.group(1).replace(".","-")}'
        current_section={
            'id':sec_id,'number':sm.group(1),'title':sm.group(2).strip(),'heading':t,
            'chapter_id':current_chapter['id'],'source_page':line['page'],'intro_lines':[], 'entry_ids':[]
        }
        sections.append(current_section); current_chapter['section_ids'].append(sec_id)
        continue
    em=ENTRY_RE.match(t)
    if em and current_chapter and current_section:
        ordinal=int(em.group(1)); heading=em.group(2).strip()
        # Split category only on the first full-width colon.
        if '：' in heading:
            name, category = heading.split('：',1)
        else:
            name, category = heading, ''
        name=name.strip(' ：:；;')
        category=category.strip(' ：:；;')
        entry_id=make_id(f'e{current_chapter["number"]}-{current_section["number"].replace(".","-")}',name,ordinal)
        current_entry={
            'id':entry_id,'ordinal':ordinal,'name':name,'category':category,'heading':heading,
            'chapter_id':current_chapter['id'],'section_id':current_section['id'],
            'chapter_title':current_chapter['title'],'section_title':current_section['title'],
            'source_pages':[line['page']], 'source_line_orders':[line['order']],
            'body_lines':[], 'captions':[], 'highlighted_text':[], 'highlight_segments':[], 'media_ids':[],
        }
        entries.append(current_entry); current_section['entry_ids'].append(entry_id)
        continue
    target = current_entry or current_section or current_chapter
    if not target:
        continue
    if current_entry:
        if line['page'] not in current_entry['source_pages']:
            current_entry['source_pages'].append(line['page'])
        current_entry['source_line_orders'].append(line['order'])
        if CAPTION_RE.search(t) and len(t) <= 45:
            current_entry['captions'].append(t)
        else:
            current_entry['body_lines'].append(t)
        current_entry['highlighted_text'].extend(x.strip() for x in line['red_texts'] if x.strip())
        for seg in line.get('red_segments', []):
            if seg.get('text'):
                current_entry['highlight_segments'].append({**seg, 'line_order':line['order'], 'page':line['page']})
    else:
        target['intro_lines'].append(t)

# Assign images to active entry based on reading order and page placement.
entries_by_page=defaultdict(list)
for e in entries:
    for p in e['source_pages']:
        entries_by_page[p].append(e)
for pno, imgs in page_images.items():
    # Entry markers/body line order on this page; choose latest entry line whose y starts before image center.
    candidates=[]
    for e in entries_by_page.get(pno,[]):
        entry_lines=[l for l in all_lines if l['page']==pno and l['order'] in set(e['source_line_orders'])]
        if entry_lines:
            ys=[l['bbox'][1] for l in entry_lines]
            candidates.append((e,min(ys),max(ys)))
    for img in imgs:
        cy=(img['bbox'][1]+img['bbox'][3])/2
        before=[(e,y0,y1) for e,y0,y1 in candidates if y0<=cy]
        if before:
            e=max(before,key=lambda x:x[1])[0]
            e['media_ids'].append(img['id'])
            img['entry_id']=e['id']
        elif candidates:
            e=min(candidates,key=lambda x:x[1])[0]
            e['media_ids'].append(img['id'])
            img['entry_id']=e['id']

# Infer structured fields while retaining exact source text.
def uniq(seq):
    out=[]; seen=set()
    for x in seq:
        x=x.strip()
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out

def split_highlights(texts):
    pieces=[]
    for t in texts:
        for x in re.split(r'[、，,；;。！？!？\n]+',t):
            x=x.strip(' ：:（）()“”"')
            if x and len(x)<=40:
                pieces.append(x)
    return uniq(pieces)

for e in entries:
    desc='\n'.join(e.pop('body_lines')).strip()
    e['description']=desc
    e['highlighted_text']=uniq(e['highlighted_text'])
    merged_segments=[]
    for seg in e.pop('highlight_segments', []):
        txt=seg['text'].strip()
        if not txt:
            continue
        if merged_segments and merged_segments[-1]['at_line_end'] and seg['at_line_start'] and seg['line_order']==merged_segments[-1]['line_order']+1:
            merged_segments[-1]['text'] += txt
            merged_segments[-1]['at_line_end'] = seg['at_line_end']
            merged_segments[-1]['line_order'] = seg['line_order']
        else:
            merged_segments.append(dict(seg))
    e['highlighted_segments']=[x['text'] for x in merged_segments]
    e['recommended_items']=split_highlights(e['highlighted_segments'])
    text=e['heading']+'\n'+desc
    if re.search(r'没去过|还没吃过|没有去过|没敢去|本人没有|自己没有|我自己还没|一直还没',text):
        visit='not_visited_by_author'
    elif re.search(r'去过|吃过|点了|带我去|体验了|每次去|来过',text):
        visit='visited_by_author'
    else:
        visit='unspecified'
    e['author_visit_status']=visit
    e['venue_type']={1:'campus_dining',2:'restaurant',3:'breakfast',4:'restaurant',5:'night_market'}.get(int(e['chapter_id'].split('-')[1]),'food')
    e['meal_periods']=(['breakfast'] if e['venue_type']=='breakfast' else ['late_day'] if e['venue_type']=='night_market' else ['lunch','dinner'])
    e['spice_notes']=uniq(re.findall(r'[^。！？\n]{0,20}(?:辣|清淡)[^。！？\n]{0,20}',text))[:8]
    e['price_notes']=uniq(re.findall(r'[^。！？\n]{0,20}(?:人均|块钱|便宜|实惠|贵|性价比)[^。！？\n]{0,24}',text))[:8]
    tags=[e['chapter_title'],e['section_title'],e['venue_type']]
    if '辣' in text: tags.append('辣度提示')
    if '清淡' in text: tags.append('清淡')
    if '便宜' in text or '实惠' in text or '性价比' in text: tags.append('性价比')
    if visit=='not_visited_by_author': tags.append('外部推荐')
    if e['highlighted_text']: tags.append('原文标红推荐')
    e['tags']=uniq(tags)
    e['source_pages']=sorted(set(e['source_pages']))
    e['source']={'document':'HUSTer的干饭修养','author':'许少','pdf_pages':e['source_pages']}
    e['user_editable']=True
    e['extensions']={}
    e.pop('source_line_orders',None)

# Attach exact media metadata to manifest after assignment.
(OUT/'media'/'manifest.json').write_text(json.dumps({'schema_version':'1.0','items':media_manifest},ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'entities.jsonl').open('w',encoding='utf-8') as f:
    for e in entries:
        f.write(json.dumps(e,ensure_ascii=False)+'\n')

catalog={
 'schema_version':'1.0',
 'dataset_id':'huster-food-guide-2026',
 'title':'HUSTer 的干饭修养',
 'subtitle':'HUST 求学七年的干饭经验',
 'content_author':'许少',
 'source_pdf_metadata':doc.metadata,
 'source_pdf_pages':len(doc),
 'extraction':{
    'method':'PyMuPDF layout-aware extraction',
    'red_text_semantics':'The source explains that red text marks author recommendations.',
    'yellow_background_semantics':'The source legend says yellow background plus red is especially recommended; the only yellow rectangle detected is in the legend itself.',
    'raw_page_records_included':True,
    'all_embedded_images_extracted':True,
 },
 'counts':{'chapters':len(chapters),'sections':len(sections),'entries':len(entries),'images':len(media_manifest)},
 'chapters':chapters,
 'sections':sections,
 'page_index':page_records,
 'entity_file':'entities.jsonl',
 'media_manifest':'media/manifest.json',
 'source_pdf':'source/HUSTer的干饭修养.pdf',
 'package':{
    'name':'hust_helper',
    'module':'hust_helper.tools.hust_eater',
    'version':'0.1.0',
    'base_data_immutable':True,
    'user_overlay_supported':True,
 },
}
def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

page_files = sorted((OUT/'pages').glob('*'))
media_files = sorted((OUT/'media').glob('*.png'))
integrity = {
    'schema_version':'1.0',
    'source_pdf':{
        'file':'source/HUSTer的干饭修养.pdf',
        'sha256':file_sha256(OUT/'source'/'HUSTer的干饭修养.pdf'),
        'bytes':(OUT/'source'/'HUSTer的干饭修养.pdf').stat().st_size,
    },
    'entities':{
        'file':'entities.jsonl',
        'sha256':file_sha256(OUT/'entities.jsonl'),
        'records':len(entries),
    },
    'pages':{
        'json_files':len(list((OUT/'pages').glob('*.json'))),
        'markdown_files':len(list((OUT/'pages').glob('*.md'))),
        'combined_sha256':hashlib.sha256(b''.join(path.read_bytes() for path in page_files)).hexdigest(),
    },
    'media':{
        'png_files':len(media_files),
        'combined_sha256':hashlib.sha256(b''.join(path.read_bytes() for path in media_files)).hexdigest(),
    },
}
(OUT/'integrity.json').write_text(json.dumps(integrity,ensure_ascii=False,indent=2),encoding='utf-8')
catalog['integrity_file']='integrity.json'
(OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# HUSTer 饮食指南数据\n\n本目录包含对《HUSTer 的干饭修养——HUST 求学七年的干饭经验》的版面感知提取结果。\n\n- `catalog.json`: 章节、分区、条目索引和提取元数据。\n- `entities.jsonl`: 可扩展、可编辑的结构化条目。\n- `pages/`: 49 页逐页 JSON 与 Markdown，保留全文、坐标、字体颜色和标红推荐信息。\n- `media/`: PDF 中全部嵌入图片的 PNG 副本及清单。\n- `source/`: 原始 PDF，用于追溯和重新提取。\n- `integrity.json`: 源 PDF、实体、页面和媒体完整性摘要。\n\n代码许可与内容版权分离；请保留原作者许少及原始来源信息。\n''',encoding='utf-8')
print(json.dumps(catalog['counts'],ensure_ascii=False,indent=2))
print('first entries')
for e in entries[:8]:
    print(e['name'], e['section_title'], e['source_pages'], e['recommended_items'][:5], e['media_ids'])
print('last entries')
for e in entries[-8:]:
    print(e['name'], e['section_title'], e['source_pages'])
