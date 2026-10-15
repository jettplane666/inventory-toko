import json,sys,os
from playwright.sync_api import sync_playwright
URL='file://'+os.path.abspath(os.path.join(os.path.dirname(__file__),'../tokoku/index.html'))
VP=[(320,568),(360,800),(390,844),(430,932),(768,1024),(1024,768),(1366,768),(1920,1080)]
OWNER=['dash','pos','hist','prod','stock','rep','exp','set']
JS_CHECK='''()=>{const W=innerWidth,out=[],vis=e=>{const s=getComputedStyle(e);if(s.visibility=='hidden'||s.display=='none')return false;for(let p=e;p&&p!=document.body;p=p.parentElement){const c=getComputedStyle(p);if(c.display=='none'||c.visibility=='hidden')return false}return true};
const hid=e=>{const sd=document.querySelector('#side'),ct=document.querySelector('.cart');const nv=document.body.classList.contains('nv'),cv=document.body.classList.contains('cv');
 if(W<=900&&sd.contains(e)&&!nv)return true;if(W<=900&&ct&&ct.contains(e)&&!cv)return true;return false};
const inScroll=e=>{for(let p=e.parentElement;p&&p!=document.body;p=p.parentElement){const o=getComputedStyle(p).overflowX;if((o=='auto'||o=='scroll')&&p.scrollWidth>p.clientWidth)return true}return false};
const res={docOverflow:document.documentElement.scrollWidth>W,off:[],clip:[],small:[]};
document.querySelectorAll('body *').forEach(e=>{if(!vis(e)||hid(e))return;const r=e.getBoundingClientRect();if(r.width==0)return;
 if((r.right>W+1||r.left<-1)&&!inScroll(e)&&e.tagName!='svg'&&!e.closest('svg'))res.off.push(e.tagName+'.'+(e.className||e.id)+' '+Math.round(r.left)+'-'+Math.round(r.right));
 if(['BUTTON','INPUT','SELECT'].includes(e.tagName)&&W<=900&&e.type!='checkbox'&&(r.height<43.5||r.width<43.5)&&e.id!='bcnt')res.small.push(e.tagName+':'+(e.textContent||e.placeholder||e.className).trim().slice(0,18)+' '+Math.round(r.width)+'x'+Math.round(r.height));
 if(!e.classList.contains('bell')&&/^(H2|H3|B|SMALL|LABEL|BUTTON|TD)$/.test(e.tagName)&&e.scrollWidth>e.clientWidth+1&&getComputedStyle(e).overflowX!='auto'&&getComputedStyle(e).textOverflow!='ellipsis'&&getComputedStyle(e).display!='inline')res.clip.push(e.tagName+':'+e.textContent.trim().slice(0,22))});
for(const k of ['off','clip','small'])res[k]=[...new Set(res[k])].slice(0,6);return res}'''
issues={};log=[]
def note(vp,page,kind,d):
    issues.setdefault(f'{vp[0]}x{vp[1]}',[]).append((page,kind,d))
with sync_playwright() as p:
    b=p.chromium.launch()
    for vp in VP:
        for role,cred in [('owner',('owner@tokoku.demo','Owner123!')),('kasir',('kasir@tokoku.demo','Kasir123!'))]:
            ctx=b.new_context(viewport={'width':vp[0],'height':vp[1]},has_touch=vp[0]<900,is_mobile=vp[0]<900,device_scale_factor=1)
            pg=ctx.new_page();pg.route('**/unpkg.com/**',lambda r:r.abort());errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
            pg.goto(URL);pg.wait_for_timeout(150)
            r=pg.evaluate(JS_CHECK)
            if r['docOverflow'] or r['off']:note(vp,'login','overflow',r)
            pg.fill('#em',cred[0]);pg.fill('#pw',cred[1]);pg.click('#login button.btn');pg.wait_for_timeout(100)
            pages=OWNER if role=='owner' else ['dash','pos','hist','prod','stock']
            for pn in pages:
                pg.evaluate(f"go('{pn}')");pg.wait_for_timeout(60)
                if pn=='pos':pg.evaluate("add('p0');add('p6');add('p3')")
                r=pg.evaluate(JS_CHECK)
                if pn=='pos':   # periksa juga keranjang terbuka (HP)
                    if vp[0]<=900:pg.evaluate("cartOpen(1)");r2=pg.evaluate(JS_CHECK);pg.evaluate("cartOpen(0)")
                    else:r2={'docOverflow':False,'off':[],'clip':[],'small':[]}
                    for k in ('off','clip','small'):r[k]=sorted(set(r[k]+r2[k]))[:6]
                    r['docOverflow']=r['docOverflow'] or r2['docOverflow']
                if r['docOverflow'] or r['off'] or r['clip'] or r['small']:note(vp,f'{role}:{pn}','layout',{k:v for k,v in r.items() if v})
                if vp in [(360,800),(768,1024),(1366,768)] and role=='owner' and pn in('dash','pos','rep'):pg.screenshot(path=os.path.join(os.path.dirname(__file__),f'shots/{pn}_{vp[0]}.png'))
            if errs:note(vp,role,'JS error',errs[:2])
            if role=='owner':
                # --- interaksi
                pg.evaluate("go('dash')")
                if vp[0]<=900:
                    pg.click('.burger');pg.wait_for_timeout(300);bx=pg.evaluate("[document.querySelector('#side').getBoundingClientRect().left,document.querySelector('#side').getBoundingClientRect().right,document.body.classList.contains('nv'),getComputedStyle(document.querySelector('#ov')).opacity]")
                    ok1=bx[2] and bx[0]>=-1 and bx[1]<=vp[0]+1
                    pg.mouse.click(vp[0]-5,vp[1]//2);pg.wait_for_timeout(300);ok2=not pg.evaluate("document.body.classList.contains('nv')")
                    pg.click('.burger');pg.wait_for_timeout(300);pg.click('.sx');pg.wait_for_timeout(300);ok3=not pg.evaluate("document.body.classList.contains('nv')")
                    pg.click('.burger');pg.wait_for_timeout(300);pg.click('#nav button:nth-child(3)');pg.wait_for_timeout(300);ok4=not pg.evaluate("document.body.classList.contains('nv')")
                    if not(ok1 and ok2 and ok3 and ok4):note(vp,'drawer','FAIL',[ok1,ok2,ok3,ok4,bx])
                    # alur POS di HP: keranjang -> bayar
                    pg.evaluate("go('pos');cart=[];st.cash='';st.pay='Tunai';add('p7');add('p7');add('p4')");pg.wait_for_timeout(100)
                    cb=pg.inner_text('#cb');pg.click('.cbar .btn');pg.wait_for_timeout(350)
                    pg.fill('#cash','50000');pg.wait_for_timeout(50);msg=pg.inner_text('#chg');dis=pg.evaluate("document.querySelector('#pbtn').disabled");pg.fill('#cash','100000');m1=pg.inner_text('#chg')
                    pg.fill('#cash','98000');m2=pg.inner_text('#chg');pg.fill('#cash','150000');m3=pg.inner_text('#chg');dis3=pg.evaluate("document.querySelector('#pbtn').disabled")
                    foc=pg.evaluate("(()=>{const e=document.querySelector('#cash');e.focus();e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect(),b=document.querySelector('#pbtn').getBoundingClientRect();return [r.top>=0&&r.bottom<=innerHeight,b.height>=44]})()")
                    if not('3 item' in cb or '4 item' in cb) or 'Kurang' not in msg or not dis or m1!='Rp2.000' or m2!='Uang pas' or 'Rp52.000' not in m3 or dis3 or not all(foc):note(vp,'pos-mobile','FAIL',[cb,msg,dis,m2,m3,dis3,foc])
                    pg.click('#pbtn');pg.wait_for_timeout(200)
                    bm=pg.evaluate("(()=>{const r=document.querySelector('#mbox').getBoundingClientRect();return [r.left>=-1,r.right<=innerWidth+1,r.top>=-1,r.bottom<=innerHeight+1,document.body.classList.contains('cv')]})()")
                    if not all(bm[:4]) or bm[4]:note(vp,'modal-struk','FAIL',bm)
                    pg.evaluate("cm();go('prod');pform()");pg.wait_for_timeout(200)
                    bm=pg.evaluate("(()=>{const m=document.querySelector('#mbox'),r=m.getBoundingClientRect(),s=m.querySelector('.btn');const sr=s.getBoundingClientRect();return [r.left>=-1,r.right<=innerWidth+1,r.bottom<=innerHeight+1,m.scrollHeight>m.clientHeight,sr.height>=44,document.documentElement.scrollWidth<=innerWidth]})()")
                    if not(bm[0] and bm[1] and bm[2] and bm[4] and bm[5]):note(vp,'modal-form','FAIL',bm)
                else:
                    pg.evaluate("go('pos');cart=[];st.cash='';add('p7');add('p7');add('p4');st.cash='100000';drawCart()");pg.wait_for_timeout(100)
                    sticky=pg.evaluate("(()=>{const r=document.querySelector('.cart').getBoundingClientRect();return [r.right<=innerWidth+1,getComputedStyle(document.querySelector('.cbar')).display=='none',getComputedStyle(document.querySelector('.burger')).display=='none']})()")
                    if not all(sticky):note(vp,'pos-desktop','FAIL',sticky)
            ctx.close()
    b.close()
tot=sum(len(v) for v in issues.values())
for k in [f'{w}x{h}' for w,h in VP]:
    v=issues.get(k,[]);print(('OK   ' if not v else 'ISU  ')+k+('' if not v else f'  ({len(v)} masalah)'))
    seen=set()
    for it in v:
        key=json.dumps(it[1:],ensure_ascii=False)
        if key in seen:continue
        seen.add(key);print('     ',json.dumps(it,ensure_ascii=False)[:230])
print('\nTotal masalah:',tot)
