import glob,re,sys
import os as _os
TOOLS=_os.path.dirname(_os.path.abspath(__file__)); DATA=_os.path.join(TOOLS,'data'); ROOT=_os.path.dirname(TOOLS)
REPO=ROOT
LOADER='<!-- Yandex.RTB -->\n<script>window.yaContextCb=window.yaContextCb||[]</script>\n<script src="https://yandex.ru/ads/system/context.js" async></script>\n<!-- /Yandex.RTB -->\n'
CSS='<style>.adslot{min-height:90px}.adslot:empty{display:none}</style>\n'
BLOCK=('<section class="adslot" aria-label="Реклама"><!-- Yandex.RTB R-A-20355368-1 --><div id="yandex_rtb_R-A-20355368-1"></div>'
 '<script>window.yaContextCb.push(()=>{Ya.Context.AdvManager.render({"blockId":"R-A-20355368-1","renderTo":"yandex_rtb_R-A-20355368-1"})})</script></section>\n')
def clean(s):
    s=re.sub(r'<!-- Yandex.RTB -->.*?<!-- /Yandex.RTB -->\n?','',s,flags=re.S)
    s=re.sub(r'<style>\.adslot\{[^<]*</style>\n?','',s)
    s=re.sub(r'<section class="adslot".*?</section>\n?','',s,flags=re.S)
    return s
def add(s,anchor):
    s=clean(s); assert s.count(anchor)>=1, anchor
    s=s.replace('</head>',LOADER+CSS+'</head>',1)
    return s.replace(anchor,BLOCK+anchor,1)
REMOVE=len(sys.argv)>1 and sys.argv[1]=='--remove'
if REMOVE:
    add=lambda s,a: clean(s)
pages={f:'<section class="method">' for f in ['climate','ecology','housing','new-moscow','parks','social','sport','transport']}
pages['index']='<nav class="wrap alld"'
for f,a in pages.items():
    p=f'{REPO}/{f}.html'; s=open(p,encoding='utf-8').read(); open(p,'w',encoding='utf-8').write(add(s,a))
for p in glob.glob(f'{REPO}/rayon/**/index.html',recursive=True)+glob.glob(f'{REPO}/reyting/**/index.html',recursive=True):
    s=open(p,encoding='utf-8').read(); open(p,'w',encoding='utf-8').write(add(s,'<p class="foot">'))
print('ok')
