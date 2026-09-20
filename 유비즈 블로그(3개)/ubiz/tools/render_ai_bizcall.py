"""Render UBIZ's photographic image series. Font files are never exported."""
from pathlib import Path
import argparse
import json
import math
import os
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageChops

S = 2000
NAVY = '#00142E'
MINT = '#32F4BB'
WHITE = '#FFFFFF'
BRAND = '유비즈 기업통신전담센터'
CONTACT = '1661-7372 · u-biz.co.kr'
TITLE = ['사무실 전화를', '스마트폰으로']
FONT_PATH = os.environ.get('UBIZ_FONT', '/usr/share/fonts/truetype/nanum/NanumSquareB.ttf')
SOURCES = {
    '4405372': ('Vasyl Vovk', 'https://www.pexels.com/photo/modern-laptop-and-smartphone-on-table-in-office-4405372/'),
    '7657480': ('Cup of Couple', 'https://www.pexels.com/photo/a-person-writing-on-a-notebook-at-a-desk-with-a-blank-smartphone-7657480/'),
    '10376213': ('RDNE Stock project', 'https://www.pexels.com/photo/hands-of-man-working-on-laptop-and-smart-phone-10376213/'),
    '6170640': ('RDNE Stock project', 'https://www.pexels.com/photo/a-person-making-a-phone-call-6170640/'),
    '5951328': ('Arina Krasnikova', 'https://www.pexels.com/photo/a-person-holding-smartphone-5951328/'),
    '5186349': ('Nataliya Vaitkevich', 'https://www.pexels.com/photo/a-desk-workspace-5186349/'),
}


def font(size):
    return ImageFont.truetype(FONT_PATH, round(size))


def fit_font(text, max_width, size, extra=0):
    while font(size).getlength(text) + extra * 2 > max_width:
        size -= 1
    return font(size)


def ink(draw, position, text, f, fill=WHITE, thick=0):
    x, y = position
    box = f.getbbox(text, stroke_width=thick)
    width = box[2] - box[0]
    draw.text((x-width/2-box[0], y-box[1]), text, font=f, fill=fill,
              stroke_width=thick, stroke_fill=fill)


def centered_text_layer(text, size, max_width=1750, outer=0):
    f = fit_font(text, max_width, size, extra=outer+5)
    bbox = f.getbbox(text)
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pad = outer + 32
    canvas = Image.new('RGBA', (w+pad*2, h+pad*2+24))
    d = ImageDraw.Draw(canvas)
    xy = (pad-bbox[0], pad-bbox[1])
    if outer:
        shadow = Image.new('RGBA', canvas.size)
        sd = ImageDraw.Draw(shadow)
        sd.text((xy[0],xy[1]+12), text, font=f, fill=(0,6,20,140),
                stroke_width=outer+3, stroke_fill=(0,6,20,140))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
        d = ImageDraw.Draw(canvas)
        d.text(xy, text, font=f, fill=NAVY, stroke_width=outer, stroke_fill=NAVY)
    d.text(xy, text, font=f, fill=WHITE, stroke_width=3, stroke_fill=WHITE)
    return canvas


def grade(image, dark=0.0):
    im = ImageOps.exif_transpose(image).convert('RGB')
    im = ImageEnhance.Color(im).enhance(.82)
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = Image.blend(im, Image.new('RGB', im.size, '#152C41'), .045)
    if dark:
        im = Image.blend(im, Image.new('RGB', im.size, '#000A19'), dark)
    return im


def photo(root, pid, dims=(S,S), centering=(.5,.5), dark=0):
    im = Image.open(root / (str(pid)+'.jpg'))
    if str(pid) == '7657480':
        # Replace only the stock photograph's green-screen area with a blank,
        # dark surface. Do not invent or simulate the product's actual app UI.
        im = im.convert('RGB')
        r,g,b = im.split()
        a = ImageChops.subtract(g,r).point(lambda x: 255 if x > 38 else 0)
        c = ImageChops.subtract(g,b).point(lambda x: 255 if x > 23 else 0)
        m = ImageChops.darker(a,c).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.6))
        lum = g.point(lambda x: round(10+x*.045))
        surface = Image.merge('RGB',(lum,lum.point(lambda x:x+3),lum.point(lambda x:x+7)))
        im = Image.composite(surface,im,m)
    im = grade(im,dark)
    im = ImageOps.fit(im,dims,method=Image.Resampling.LANCZOS,centering=centering)
    return im.convert('RGBA')


def edge_shade(im, power=.24):
    mask = Image.new('L',(1,S))
    p = mask.load()
    for y in range(S):
        a = max(0,1-y/(S*.21))**1.5
        b = max(0,1-(S-1-y)/(S*.19))**1.5
        p[0,y] = int(max(a,b)*255*power)
    tint = Image.new('RGBA', im.size, NAVY)
    tint.putalpha(mask.resize(im.size))
    im.alpha_composite(tint)


def rounded_line(d, pts, fill, width):
    d.line(pts, fill=fill, width=width, joint='curve')
    r=width/2
    for x,y in (pts[0],pts[-1]):
        d.ellipse((x-r,y-r,x+r,y+r),fill=fill)


def frame(im, hero=False):
    d=ImageDraw.Draw(im)
    m=120
    h=170 if hero else 145
    v=285 if hero else 190
    line=10 if hero else 6
    radius=17 if hero else 11
    for left in (True, False):
        x=m if left else S-m
        x2=x+(h if left else -h)
        for top in (True,False):
            y=m if top else S-m
            y2=y+(v if top else -v)
            rounded_line(d,[(x,y2),(x,y),(x2,y)],WHITE,line)
            dot=WHITE if hero else MINT
            d.ellipse((x2-radius,y-radius,x2+radius,y+radius),fill=dot)


def pill(im, text, y, size, min_width=0, height=100):
    d=ImageDraw.Draw(im)
    f=font(size)
    width=max(round(f.getlength(text))+104,min_width)
    x=(S-width)//2
    shadow=Image.new('RGBA',im.size)
    sd=ImageDraw.Draw(shadow)
    sd.rounded_rectangle((x,y+5,x+width,y+height+5),height//2,fill=(0,9,26,70))
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((x,y,x+width,y+height),height//2,fill=NAVY)
    bbox=f.getbbox(text)
    ty=y+(height-(bbox[3]-bbox[1]))/2
    ink(d,(S/2,ty),text,f,WHITE,thick=1)


def branding(im, hero=False):
    frame(im,hero)
    pill(im,BRAND,88,65 if hero else 54,min_width=830 if hero else 740,height=110 if hero else 98)
    pill(im,CONTACT,1830 if hero else 1815,61 if hero else 54,
         min_width=810 if hero else 750,height=102)


def make_hero(root):
    im=photo(root,5951328,(S,S),(.5,.56),.03)
    overlay=Image.new('RGBA',im.size,NAVY)
    a=Image.new('L',(1,S));p=a.load()
    for y in range(S):
        p[0,y]=round(255*(.12+.18*math.exp(-((y-1040)/490)**2)))
    overlay.putalpha(a.resize(im.size));im.alpha_composite(overlay)
    edge_shade(im,.28)
    branding(im,True)
    d=ImageDraw.Draw(im)
    chip=(475,478,1525,677)
    d.rounded_rectangle((chip[0]+3,chip[1]+9,chip[2]+3,chip[3]+9),radius=16,fill=(0,9,26,145))
    d.rounded_rectangle(chip,radius=14,fill=MINT,outline=NAVY,width=13)
    f=fit_font('U+ AI 비즈콜',920,139)
    b=f.getbbox('U+ AI 비즈콜')
    ink(d,(S/2,chip[1]+(chip[3]-chip[1]-(b[3]-b[1]))/2),'U+ AI 비즈콜',f,NAVY,thick=4)
    for text, y in zip(TITLE,(735,998)):
        layer=centered_text_layer(text,256,1780,outer=21)
        im.alpha_composite(layer,((S-layer.width)//2,y))
    return im


def save(im, root, name):
    im=im.convert('RGB')
    im.save(root / (name+'.png'), optimize=True, dpi=(150,150))
    jpeg=root.parent/'jpg';jpeg.mkdir(exist_ok=True)
    im.save(jpeg/(name+'.jpg'),quality=94,subsampling=0,optimize=True,dpi=(150,150))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--photos',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    out=args.output; imgs=out/'images';imgs.mkdir(parents=True,exist_ok=True)
    save(make_hero(args.photos),imgs,'00_thumbnail')
    specs=[
        ('01_office_phone_smartphone',6170640,(.5,.60)),
        ('02_company_number_call',5951328,(.5,.57)),
        ('03_dnd_mode',4405372,(.95,.5)),
        ('04_ai_support',7657480,(.50,.58)),
        ('05_company_managed_number',10376213,(.5,.5)),
        ('06_contact',5186349,(.5,.5)),
    ]
    for name,pid,center in specs:
        im=photo(args.photos,pid,centering=center)
        edge_shade(im,.22);branding(im);save(im,imgs,name)
    names=['00_thumbnail']+[s[0] for s in specs]
    sheet=Image.new('RGB',(1800,1010),'#EDF1F5')
    draw=ImageDraw.Draw(sheet)
    draw.text((24,15),'UBIZ | AI BIZCALL | 2000 x 2000 px',font=font(26),fill=NAVY)
    for j,name in enumerate(names):
        image=Image.open(imgs/(name+'.png')).resize((428,428),Image.Resampling.LANCZOS)
        x=16+(j%4)*447;y=64+(j//4)*470
        sheet.paste(image,(x,y))
        draw.text((x+4,y+434),name[:2],font=font(26),fill=NAVY)
    sheet.save(out/'preview.jpg',quality=92)
    note='사진은 서비스 이해를 돕기 위한 스톡 이미지입니다. 유비즈 실제 고객 현장, AI 비즈콜 실제 앱 화면 또는 제공 단말 모델을 나타내지 않습니다.\n원고 상품 설명은 이번 이미지 작업에서 새로 검증하거나 변경하지 않았습니다.\n사진 라이선스: https://www.pexels.com/license/\n\n'
    for pid,(author,url) in SOURCES.items():
        note+=f'{pid} | {author} | {url}\n'
    (out/'PHOTO_SOURCES.txt').write_text(note,encoding='utf-8')
    manifest={'size_px':[S,S],'brand':BRAND,'phone':'1661-7372','site':'u-biz.co.kr','palette':{'navy':NAVY,'mint':MINT,'white':WHITE},'body_text':'brand and contact only','photos_are_illustrative':True,'files':names}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Rendered {len(names)} images to {out}')

if __name__=='__main__':
    main()
