#!/usr/bin/env python3
"""뉴스레터 HTML을 인스타 4:5(1080x1350) 카드 이미지로 나눈다.
사용법: python3 tools/make_cards.py <decant-daily-news.html> <출력 폴더>
결과: 01.png ~ NN.png (표지·픽 → 카테고리 → 메모 → 검정 아웃트로). 헤더 글꼴은 Noto Sans CJK를 사용."""
import asyncio, pathlib, sys, re
from PIL import Image, ImageDraw, ImageFont
src=pathlib.Path(sys.argv[1]); html=src.read_text()
date=re.search(r'class="?date"?><i>\|</i>([0-9.]+)',html).group(1)
out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'cards'); out.mkdir(parents=True,exist_ok=True)
for f in out.glob('*'): f.unlink()
VW=520; S=1080/VW; PH=1350/S; HEAD=40; BOT=14

from playwright.async_api import async_playwright
async def run():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':VW,'height':900},device_scale_factor=S)
        await pg.goto(src.as_uri()); await pg.evaluate("document.fonts.ready")
        await pg.add_style_tag(content=":root{padding:0!important}")
        info=await pg.evaluate("""()=>{const B=e=>Math.round(e.getBoundingClientRect().bottom+scrollY),T=e=>Math.round(e.getBoundingClientRect().top+scrollY);
          let pts=[];['.mast','.toc','.sec-head','.pick','.item','.note','.memo'].forEach(s=>document.querySelectorAll(s).forEach(e=>pts.push(B(e))));
          const cats=[...document.querySelectorAll('.cat')].map(e=>({t:T(e),b:B(e),en:e.querySelector('.cat-en').textContent,idx:e.querySelector('.cat-idx').textContent}));
          cats.forEach(c=>pts.push(c.t));
          const foot=T(document.querySelector('.foot')), memo=T(document.querySelector('.memo'));
          return {pts:[...new Set(pts)].sort((a,b)=>a-b),cats,foot,memo,H:document.documentElement.scrollHeight}}""")
        await pg.screenshot(path=str(out/'_full.png'),full_page=True)
        await b.close()
    return info
info=asyncio.run(run())
pts,cats,FOOT,H=info['pts'],info['cats'],info['foot'],info['H']
pts=[x for x in pts if x<=FOOT]+[FOOT]
full=Image.open(out/'_full.png'); W=full.width
cuts=[0];cur=0
while cur<FOOT:
    lim=cur+(PH if cur==0 else PH-HEAD-BOT)
    c=[x for x in pts if cur<x<=lim]
    nxt=max(c) if c else min(int(lim),FOOT)
    cuts.append(nxt);cur=nxt
pages=list(zip(cuts,cuts[1:]))
n=len(pages)+1
f=lambda w,s:ImageFont.truetype(PRE+f'Pretendard-{w}.otf' if False else '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',s)
# convert woff2 not loadable by PIL; use Noto CJK
fb=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',24)
fr=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc',24)
def header(cv,i,label):
    d=ImageDraw.Draw(cv); y=int(HEAD*S*0.52)
    d.text((int(18*S),y),'decant.seoul   DAILY NEWS '+date,font=fb,fill=(10,10,10),anchor='lm')
    d.text((1080-int(18*S),y),(label+'   ' if label else '')+f'{i:02d} / {n:02d}',font=fr,fill=(120,120,120),anchor='rm')
    d.line([(int(18*S),int(HEAD*S)-2),(1080-int(18*S),int(HEAD*S)-2)],fill=(10,10,10),width=2)
for i,(a,bb) in enumerate(pages,1):
    cv=Image.new('RGB',(1080,1350),'white')
    crop=full.crop((0,round(a*S),W,round(bb*S)))
    if a==0:
        cv.paste(crop,(0,0))
        d=ImageDraw.Draw(cv); d.text((1080-int(18*S),1350-int(10*S)),f'01 / {n:02d}',font=fr,fill=(140,140,140),anchor='rb')
    else:
        lab=''
        for c in cats:
            if c['t']<a<c['b']: lab=c['en'].upper()
        cv.paste(crop,(0,int(HEAD*S)))
        header(cv,i,lab)
    cv.save(out/f'{i:02d}.png')
# footer slide: black, centered
fc=full.crop((0,round(FOOT*S),W,full.height))
cv=Image.new('RGB',(1080,1350),(10,10,10)); cv.paste(fc,(0,(1350-fc.height)//2))
cv.save(out/f'{n:02d}.png')
(out/'_full.png').unlink()
print(n,[(a,bb) for a,bb in pages])
