from __future__ import annotations

import html
import json
import re
from urllib.parse import urlsplit
from pathlib import Path
from extra_apps import builders as extra_builders

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "catalog.json").read_text())
MONETIZATION_PATH = ROOT / "monetization.json"
MONETIZATION = json.loads(MONETIZATION_PATH.read_text()) if MONETIZATION_PATH.exists() else {}
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)

BASE_CSS = """
:root{color-scheme:dark;--bg:#0d1014;--card:#171c22;--line:#2c3540;--text:#f3f6f8;--muted:#9eabb8;--accent:#79dcff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:680px;margin:auto;padding:20px}h1{margin-bottom:4px}.sub{color:var(--muted);margin-bottom:18px}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin:12px 0}input,button,textarea,select{font:inherit}input,textarea,select{width:100%;background:#10151a;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:11px}button{background:var(--accent);color:#051118;border:0;border-radius:10px;padding:11px 14px;font-weight:750;cursor:pointer}.secondary{background:#2a333d;color:var(--text)}.row{display:flex;gap:8px;align-items:center}.row>*{flex:1}.item{display:flex;align-items:center;gap:8px;padding:10px 0;border-bottom:1px solid var(--line)}.item span{flex:1}.big{font-size:3rem;font-weight:800;text-align:center}.small{font-size:.85rem;color:var(--muted)}
"""


def accessible_form_markup(markup: str) -> str:
    """Give static form fields a real label without changing their behavior.

    Builders use short HTML fragments.  This keeps those fragments readable while
    making the generated relationship explicit for assistive technology.  A
    visible label immediately before a field is linked with ``for``; otherwise a
    placeholder is promoted to ``aria-label``.  The source strings remain the
    authority for human-facing wording and IDs/local-storage behavior is untouched.
    """
    markup = re.sub(
        r'<label(?![^>]*\bfor=)([^>]*)>([\s\S]*?)</label>(<(?:input|textarea|select)\b[^>]*\bid="([^"]+)"[^>]*>)',
        lambda match: (
            f'<label{match.group(1)} for="{html.escape(match.group(4), quote=True)}">'
            f'{match.group(2)}</label>{match.group(3)}'
        ),
        markup,
    )
    labelled_ids = set(re.findall(r'<label\b[^>]*\bfor="([^"]+)"', markup))

    def label_from_placeholder(match: re.Match[str]) -> str:
        tag = match.group(0)
        if re.search(r'\b(?:aria-label|aria-labelledby|title)=', tag):
            return tag
        field_id = re.search(r'\bid="([^"]+)"', tag)
        if field_id and field_id.group(1) in labelled_ids:
            return tag
        placeholder = re.search(r'\bplaceholder="([^"]+)"', tag)
        if not placeholder:
            return tag
        return tag[:-1] + f' aria-label="{html.escape(placeholder.group(1), quote=True)}">'

    return re.sub(r'<(?:input|textarea|select)\b[^>]*>', label_from_placeholder, markup)


def shell(app, body, script):
    name = html.escape(app["name"])
    tagline = html.escape(app["tagline"])
    monetization = MONETIZATION.get(app["slug"], {})
    upgrade_url = monetization.get("upgrade_url", "").strip()
    if upgrade_url and (urlsplit(upgrade_url).scheme != "https" or not urlsplit(upgrade_url).netloc):
        raise ValueError(f"Upgrade URL must use HTTPS: {app['slug']}")
    upgrade_label = html.escape(monetization.get("upgrade_label", "Unlock Pro"))
    upgrade = (
        f'<section class="card"><div class="small">Optional upgrade</div><p>Keep the free local-first version, or unlock the paid edition.</p><a href="{html.escape(upgrade_url, quote=True)}" rel="noopener noreferrer"><button>{upgrade_label}</button></a></section>'
        if upgrade_url else ""
    )
    body = accessible_form_markup(body)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0d1014"><link rel="manifest" href="manifest.webmanifest"><title>{name}</title><style>{BASE_CSS}a{{color:inherit;text-decoration:none}}</style></head><body><main><h1>{name}</h1><div class="sub">{tagline}</div>{body}{upgrade}<div class="small">Local-first · no account required</div></main><script>{script}</script></body></html>'''


def list_app(app):
    key = f"begg:{app['slug']}:items"
    body = '<section class="card"><div class="row"><input id="new" placeholder="Add item"><button onclick="add()">Add</button></div><div id="items"></div></section>'
    script = f'''const K={json.dumps(key)};function loadItems(){{try{{let value=JSON.parse(localStorage.getItem(K)||'[]');return Array.isArray(value)?value.filter(x=>x&&typeof x.text==='string').map(x=>({{text:x.text,done:x.done===true}})):[]}}catch{{return[]}}}}let items=loadItems();function save(){{localStorage.setItem(K,JSON.stringify(items));draw()}}function add(){{let e=document.getElementById('new'),v=e.value.trim();if(!v)return;items.push({{text:v,done:false}});e.value='';save()}}function toggle(i){{items[i].done=!items[i].done;save()}}function del(i){{items.splice(i,1);save()}}function draw(){{document.getElementById('items').innerHTML=items.map((x,i)=>`<div class="item"><input type="checkbox" aria-label="${{x.done?'Mark incomplete: ':'Mark complete: '}}${{esc(x.text)}}" ${{x.done?'checked':''}} onchange="toggle(${{i}})"><span style="${{x.done?'text-decoration:line-through;opacity:.55':''}}">${{esc(x.text)}}</span><button class="secondary" aria-label="Delete ${{esc(x.text)}}" onclick="del(${{i}})">x</button></div>`).join('')}}function esc(s){{return s.replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}draw();'''
    return shell(app, body, script)


def counter_app(app):
    key = f"begg:{app['slug']}:count"
    body = '<section class="card"><div id="count" class="big">0</div><div class="row"><button class="secondary" onclick="change(-1)">-1</button><button onclick="change(1)">+1</button><button class="secondary" onclick="reset()">Reset</button></div></section>'
    script = f'''const K={json.dumps(key)};let n=Number(localStorage.getItem(K)||0);function draw(){{count.textContent=n;localStorage.setItem(K,n)}}function change(x){{n=Math.max(0,n+x);draw()}}function reset(){{n=0;draw()}}draw();'''
    return shell(app, body, script)


def calculator_app(app):
    body = '<section class="card"><label>Income</label><input id="income" type="number" inputmode="decimal" value="0"><br><br><label>Expenses</label><input id="expenses" type="number" inputmode="decimal" value="0"><br><br><button onclick="calc()">Calculate</button><div id="out" class="big">$0.00</div></section>'
    script = "function calc(){let a=Number(income.value||0),b=Number(expenses.value||0);out.textContent=(a-b).toLocaleString(undefined,{style:'currency',currency:'USD'})}"
    return shell(app, body, script)


def timer_app(app):
    mins = 15 if app["slug"] == "clean-15" else 25
    body = f'<section class="card"><div id="clock" class="big">{mins:02d}:00</div><div class="row"><button onclick="start()">Start</button><button class="secondary" onclick="pause()">Pause</button><button class="secondary" onclick="reset()">Reset</button></div></section>'
    script = f'''let base={mins}*60,left=base,t=null;function draw(){{clock.textContent=String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0')}}function start(){{if(t)return;t=setInterval(()=>{{if(left<=0){{pause();return}}left--;draw()}},1000)}}function pause(){{clearInterval(t);t=null}}function reset(){{pause();left=base;draw()}}draw();'''
    return shell(app, body, script)


def randomizer_app(app):
    body = '<section class="card"><textarea id="opts" placeholder="One option per line"></textarea><br><br><button onclick="pick()">Pick one</button><div id="out" class="big" style="font-size:2rem;margin-top:14px">-</div></section>'
    script = "function pick(){let a=opts.value.split(/\\n/).map(x=>x.trim()).filter(Boolean);out.textContent=a.length?a[Math.floor(Math.random()*a.length)]:'Add some options'}"
    return shell(app, body, script)


def tip_app(app):
    body = '<section class="card"><label>Bill</label><input id="bill" type="number" value="40"><br><br><label>Tip %</label><input id="tip" type="number" value="20"><br><br><label>People</label><input id="people" type="number" min="1" value="2"><br><br><button onclick="calc()">Calculate</button><div id="out" class="big" style="font-size:2rem"></div></section>'
    script = "function calc(){let b=Number(bill.value||0),t=Number(tip.value||0)/100,p=Math.max(1,Number(people.value||1)),total=b*(1+t);out.textContent=(total/p).toLocaleString(undefined,{style:'currency',currency:'USD'})+' each';}calc();"
    return shell(app, body, script)


def percent_app(app):
    body = '<section class="card"><label>Starting value</label><input id="a" type="number" value="100"><br><br><label>New value</label><input id="b" type="number" value="125"><br><br><button onclick="calc()">Calculate</button><div id="out" class="big" style="font-size:2rem"></div></section>'
    script = "function calc(){let x=Number(a.value),y=Number(b.value);out.textContent=x===0?'Starting value cannot be 0':(((y-x)/Math.abs(x))*100).toFixed(2)+'%';}calc();"
    return shell(app, body, script)


def scale_app(app):
    body = '<section class="card"><label>Original servings</label><input id="oldS" type="number" value="4"><br><br><label>New servings</label><input id="newS" type="number" value="6"><br><br><label>Original ingredient amount</label><input id="amt" type="number" value="2"><br><br><button onclick="calc()">Scale</button><div id="out" class="big" style="font-size:2rem"></div></section>'
    script = "function calc(){let o=Number(oldS.value),n=Number(newS.value),a=Number(amt.value);out.textContent=o>0?(a*n/o).toFixed(2):'-';}calc();"
    return shell(app, body, script)


def fuel_app(app):
    body = '<section class="card"><label>Distance (miles)</label><input id="miles" type="number" value="100"><br><br><label>Vehicle MPG</label><input id="mpg" type="number" value="25"><br><br><label>Fuel price / gallon</label><input id="price" type="number" step="0.01" value="3.00"><br><br><button onclick="calc()">Estimate</button><div id="out" class="big" style="font-size:1.8rem"></div></section>'
    script = "function calc(){let d=Number(miles.value),m=Number(mpg.value),p=Number(price.value);if(m<=0){out.textContent='-';return}let g=d/m;out.textContent=g.toFixed(2)+' gal · '+(g*p).toLocaleString(undefined,{style:'currency',currency:'USD'});}calc();"
    return shell(app, body, script)


def savings_app(app):
    body = '<section class="card"><label>Goal amount</label><input id="goal" type="number" value="1000"><br><br><label>Months</label><input id="months" type="number" min="1" value="6"><br><br><button onclick="calc()">Plan</button><div id="out" class="big" style="font-size:1.7rem"></div><div class="small">Simple target only; no investment assumptions.</div></section>'
    script = "function money(v){return v.toLocaleString(undefined,{style:'currency',currency:'USD'})}function calc(){let g=Math.max(0,Number(goal.value)),m=Math.max(1,Number(months.value));out.textContent=money(g/m)+'/month · '+money(g/(m*4.345))+'/week';}calc();"
    return shell(app, body, script)


def loan_app(app):
    body = '<section class="card"><label>Loan amount</label><input id="principal" type="number" value="10000"><br><br><label>Annual rate %</label><input id="rate" type="number" step="0.01" value="8"><br><br><label>Term (months)</label><input id="months" type="number" value="36"><br><br><button onclick="calc()">Estimate</button><div id="out" class="big" style="font-size:1.8rem"></div><div class="small">Estimate only; fees and lender terms can change actual payments.</div></section>'
    script = "function calc(){let P=Number(principal.value),n=Math.max(1,Number(months.value)),r=Number(rate.value)/1200;let pay=r===0?P/n:P*r/(1-Math.pow(1+r,-n));out.textContent=pay.toLocaleString(undefined,{style:'currency',currency:'USD'})+'/mo';}calc();"
    return shell(app, body, script)


def date_diff_app(app):
    body = '<section class="card"><label>Start date</label><input id="start" type="date"><br><br><label>End date</label><input id="end" type="date"><br><br><button onclick="calc()">Count days</button><div id="out" class="big" style="font-size:2rem">-</div></section>'
    script = "function calc(){if(!start.value||!end.value){out.textContent='-';return}let a=new Date(start.value+'T00:00:00'),b=new Date(end.value+'T00:00:00');out.textContent=Math.round(Math.abs(b-a)/86400000)+' days';}"
    return shell(app, body, script)


def countdown_app(app):
    body = '<section class="card"><label>Target date</label><input id="target" type="date"><br><br><button onclick="calc()">Count down</button><div id="out" class="big" style="font-size:2rem">-</div></section>'
    script = "function calc(){if(!target.value){out.textContent='-';return}let t=new Date(target.value+'T00:00:00'),now=new Date();now.setHours(0,0,0,0);let d=Math.ceil((t-now)/86400000);out.textContent=d===0?'Today':d>0?d+' days left':Math.abs(d)+' days ago';}calc();"
    return shell(app, body, script)


def text_stats_app(app):
    body = '<section class="card"><textarea id="txt" placeholder="Type or paste text" oninput="calc()"></textarea><div id="out" class="big" style="font-size:1.5rem;text-align:left"></div></section>'
    script = "function calc(){let s=txt.value,words=(s.trim().match(/\\S+/g)||[]).length,chars=s.length,lines=s?s.split(/\\n/).length:0,mins=Math.max(0.1,words/225);out.textContent=words+' words · '+chars+' characters · '+lines+' lines · '+mins.toFixed(1)+' min read';}calc();"
    return shell(app, body, script)


def text_case_app(app):
    body = '<section class="card"><textarea id="txt" placeholder="Type or paste text"></textarea><div class="row" style="flex-wrap:wrap;margin-top:10px"><button onclick="go(\'upper\')">UPPER</button><button onclick="go(\'lower\')">lower</button><button onclick="go(\'title\')">Title</button><button onclick="go(\'sentence\')">Sentence</button></div></section>'
    script = "function go(m){let s=txt.value;if(m==='upper')s=s.toUpperCase();if(m==='lower')s=s.toLowerCase();if(m==='title')s=s.toLowerCase().replace(/\\b\\w/g,c=>c.toUpperCase());if(m==='sentence')s=s.toLowerCase().replace(/(^|[.!?]\\s+)\\w/g,c=>c.toUpperCase());txt.value=s;}"
    return shell(app, body, script)


def habit_app(app):
    key = f"begg:{app['slug']}:habit"
    body = '<section class="card"><input id="name" placeholder="Habit name"><div id="days" class="row" style="margin-top:12px;flex-wrap:wrap"></div><div id="score" class="small" style="margin-top:10px"></div><button class="secondary" onclick="reset()" style="margin-top:10px">Reset week</button></section>'
    script = f'''const K={json.dumps(key)},fresh=()=>({{name:'',days:Array(7).fill(false)}});function loadHabit(){{try{{let value=JSON.parse(localStorage.getItem(K)||'null');return value&&typeof value.name==='string'&&Array.isArray(value.days)&&value.days.length===7&&value.days.every(x=>typeof x==='boolean')?value:fresh()}}catch{{return fresh()}}}}let st=loadHabit();document.getElementById('name').value=st.name;document.getElementById('name').oninput=()=>{{st.name=document.getElementById('name').value;save()}};function save(){{localStorage.setItem(K,JSON.stringify(st));draw()}}function toggle(i){{st.days[i]=!st.days[i];save()}}function reset(){{st.days=Array(7).fill(false);save()}}function draw(){{let labels=['M','T','W','T','F','S','S'];days.innerHTML=labels.map((x,i)=>`<button class="${{st.days[i]?'':'secondary'}}" onclick="toggle(${{i}})">${{x}}</button>`).join('');score.textContent=st.days.filter(Boolean).length+'/7 complete'}}draw();'''
    return shell(app, body, script)


def split_app(app):
    body = '<section class="card"><label>Total</label><input id="total" type="number" value="80"><br><br><label>People</label><input id="people" type="number" min="1" value="4"><br><br><button onclick="calc()">Split</button><div id="out" class="big" style="font-size:2rem"></div></section>'
    script = "function calc(){let t=Number(total.value),p=Math.max(1,Number(people.value));out.textContent=(t/p).toLocaleString(undefined,{style:'currency',currency:'USD'})+' each';}calc();"
    return shell(app, body, script)


def passphrase_app(app):
    body = '<section class="card"><label>Words</label><input id="n" type="number" min="6" max="8" value="6"><br><br><button onclick="make()">Generate locally</button><div id="out" class="big" role="status" aria-live="polite" aria-atomic="true" style="font-size:1.3rem;word-break:break-word"></div><div class="small">Generated in your browser using cryptographic randomness.</div></section>'
    # 64 x 32 distinct, readable compounds provide 2,048 choices (11 bits per
    # word) without shipping a dependency or making a network request. Generic
    # rejection sampling keeps every entry equally likely for any list length.
    script = "const starts=['alpine','amber','april','aqua','arctic','autumn','blue','brave','breezy','bright','bronze','calm','cedar','cherry','copper','coral','crisp','crystal','dawn','deep','eager','early','ember','fair','fern','fresh','gentle','golden','grand','green','happy','hazel','hidden','ivory','jade','keen','kind','light','lively','lucky','lunar','maple','merry','misty','moon','noble','north','ocean','olive','orange','pine','plum','quiet','rapid','red','river','rosy','royal','silver','soft','solar','sunny','swift','velvet'],ends=['anchor','badger','basket','beacon','bird','cabin','cactus','canyon','castle','cloud','comet','dolphin','falcon','field','forest','garden','harbor','lantern','meadow','mountain','oak','panda','pepper','planet','puzzle','rocket','sparrow','stone','summit','trail','willow','window'],words=starts.flatMap(a=>ends.map(b=>a+b));function randomIndex(size){const range=0x100000000,limit=Math.floor(range/size)*size,a=new Uint32Array(1);do{crypto.getRandomValues(a)}while(a[0]>=limit);return a[0]%size}function pick(){return words[randomIndex(words.length)]}function make(){let k=Math.max(6,Math.min(8,Math.trunc(Number(n.value))||6)),a=[];while(a.length<k){let word=pick();if(!a.includes(word))a.push(word)}out.textContent=a.join('-');}make();"
    return shell(app, body, script)


def unit_app(app):
    body = '<section class="card"><label>Value</label><input id="value" type="number" value="1"><br><br><label>Conversion</label><select id="mode"><option value="mi-km">Miles to km</option><option value="km-mi">Km to miles</option><option value="lb-kg">Pounds to kg</option><option value="kg-lb">Kg to pounds</option><option value="f-c">F to C</option><option value="c-f">C to F</option></select><br><br><button onclick="calc()">Convert</button><div id="out" class="big" style="font-size:2rem"></div></section>'
    script = "function calc(){let v=Number(value.value),m=mode.value,r,u;if(m==='mi-km'){r=v*1.609344;u=' km'}if(m==='km-mi'){r=v/1.609344;u=' mi'}if(m==='lb-kg'){r=v*0.45359237;u=' kg'}if(m==='kg-lb'){r=v/0.45359237;u=' lb'}if(m==='f-c'){r=(v-32)*5/9;u=' C'}if(m==='c-f'){r=v*9/5+32;u=' F'}out.textContent=r.toFixed(2)+u;}calc();"
    return shell(app, body, script)


def tap_game(app):
    body = '<section class="card"><div id="status" class="big">0</div><button id="tap" style="width:100%;height:180px;font-size:2rem" onclick="hit()">START</button><div id="time" class="small"></div></section>'
    script = "let score=0,left=10,t=null,live=false;function hit(){if(!live){live=true;score=0;document.getElementById('status').textContent=score;left=10;tap.textContent='TAP';t=setInterval(()=>{left--;time.textContent=left+'s';if(left<=0){clearInterval(t);live=false;tap.textContent='AGAIN';time.textContent='Final score: '+score}},1000)}else{score++;document.getElementById('status').textContent=score}}"
    return shell(app, body, script)


def number_game(app):
    body = '<section class="card"><div class="small">Tap the target</div><div id="target" class="big">-</div><div id="buttons" class="row" style="flex-wrap:wrap"></div><div id="score" class="small">score: 0</div></section>'
    script = "let s=0,tg=0;function round(){tg=1+Math.floor(Math.random()*9);target.textContent=tg;let a=[1,2,3,4,5,6,7,8,9].sort(()=>Math.random()-.5);buttons.innerHTML=a.map(n=>`<button onclick=\"go(${n})\">${n}</button>`).join('')}function go(n){if(n===tg)s++;else s=Math.max(0,s-1);score.textContent='score: '+s;round()}round();"
    return shell(app, body, script)


def memory_game(app):
    body = '<section class="card"><div id="grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px"></div><br><button class="secondary" onclick="reset()">New game</button></section>'
    script = "let vals=[],open=[],matched=[];function reset(){vals=['A','B','C','D','A','B','C','D'].sort(()=>Math.random()-.5);open=[];matched=[];draw()}function draw(){grid.innerHTML=vals.map((v,i)=>`<button style=\"height:70px\" onclick=\"flip(${i})\">${matched.includes(i)||open.includes(i)?v:'?'}</button>`).join('')}function flip(i){if(matched.includes(i)||open.includes(i)||open.length>=2)return;open.push(i);draw();if(open.length===2){let[a,b]=open;if(vals[a]===vals[b]){matched.push(a,b);open=[];draw()}else setTimeout(()=>{open=[];draw()},600)}}reset();"
    return shell(app, body, script)


def word_game(app):
    body = '<section class="card"><div id="scramble" class="big" style="font-size:2rem"></div><input id="guess" placeholder="Your guess"><br><br><div class="row"><button onclick="check()">Check</button><button class="secondary" onclick="next()">Skip</button></div><div id="msg" class="small" style="margin-top:10px"></div></section>'
    script = "const words=['garden','coffee','window','planet','basket','summer','pillow','market'];let word='';function next(){word=words[Math.floor(Math.random()*words.length)];scramble.textContent=word.split('').sort(()=>Math.random()-.5).join('').toUpperCase();guess.value='';msg.textContent=''}function check(){if(guess.value.trim().toLowerCase()===word){msg.textContent='Correct!';setTimeout(next,500)}else msg.textContent='Try again'}next();"
    return shell(app, body, script)


def reaction_game(app):
    body = '<section class="card"><div id="box" style="height:220px;border-radius:14px;background:#303944;display:flex;align-items:center;justify-content:center;font-size:1.5rem;font-weight:800" onclick="tap()">Tap to start</div><div id="msg" class="small" style="margin-top:10px"></div></section>'
    script = "let ready=false,start=0,t=null,active=false;function tap(){if(!active){active=true;ready=false;box.style.background='#6a4b23';box.textContent='Wait...';t=setTimeout(()=>{ready=true;start=performance.now();box.style.background='#2f8b57';box.textContent='TAP!'},800+Math.random()*2200);return}if(!ready){clearTimeout(t);active=false;box.style.background='#303944';box.textContent='Too soon - tap to retry';msg.textContent='';return}let ms=Math.round(performance.now()-start);active=false;ready=false;box.style.background='#303944';box.textContent='Tap to go again';msg.textContent=ms+' ms';}"
    return shell(app, body, script)


def rps_game(app):
    body = '<section class="card"><div class="row"><button onclick="play(0)">Rock</button><button onclick="play(1)">Paper</button><button onclick="play(2)">Scissors</button></div><div id="out" class="big" style="font-size:1.7rem;margin-top:16px"></div><div id="score" class="small"></div></section>'
    script = "let w=0,l=0,d=0,n=['Rock','Paper','Scissors'];function play(x){let c=Math.floor(Math.random()*3),r=x===c?0:((x-c+3)%3===1?1:-1);if(r===1)w++;else if(r===-1)l++;else d++;out.textContent='You: '+n[x]+' · Device: '+n[c]+' · '+(r===1?'Win':r===-1?'Loss':'Draw');score.textContent='W '+w+' · L '+l+' · D '+d;}"
    return shell(app, body, script)


def ttt_game(app):
    body = '<section class="card"><div id="board" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px"></div><div id="msg" class="small" style="margin:10px 0"></div><button class="secondary" onclick="reset()">New game</button></section>'
    script = "let b=Array(9).fill(''),turn='X',over=false;const wins=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];function draw(){board.innerHTML=b.map((v,i)=>`<button aria-label=\"Cell ${i+1}: ${v||'empty'}\" style=\"height:80px;font-size:2rem\" onclick=\"go(${i})\">${v}</button>`).join('');if(!over)msg.textContent='Turn: '+turn}function go(i){if(over||b[i])return;b[i]=turn;let win=wins.some(a=>a.every(j=>b[j]===turn));if(win){over=true;msg.textContent=turn+' wins!'}else if(b.every(Boolean)){over=true;msg.textContent='Draw'}else turn=turn==='X'?'O':'X';draw()}function reset(){b=Array(9).fill('');turn='X';over=false;msg.textContent='';draw()}reset();"
    return shell(app, body, script)


def math_game(app):
    body = '<section class="card"><div id="q" class="big" style="font-size:2rem"></div><input id="ans" type="number" placeholder="Answer"><br><br><button onclick="check()">Check</button><div id="score" class="small"></div></section>'
    script = "let a,b,op,correct,s=0;function next(){a=1+Math.floor(Math.random()*20);b=1+Math.floor(Math.random()*20);op=Math.random()<.5?'+':'-';correct=op==='+'?a+b:a-b;q.textContent=a+' '+op+' '+b;ans.value='';score.textContent='score: '+s}function check(){if(!ans.value.trim())return;if(Number(ans.value)===correct)s++;else s=Math.max(0,s-1);next()}next();"
    return shell(app, body, script)


def color_game(app):
    body = '<section class="card"><div id="word" class="big"></div><div class="row"><button onclick="answer(true)">MATCH</button><button class="secondary" onclick="answer(false)">NO MATCH</button></div><div id="score" class="small"></div></section>'
    script = "const c=[['RED','#ef5350'],['BLUE','#42a5f5'],['GREEN','#66bb6a'],['YELLOW','#ffee58']];let truth=false,s=0;function next(){let a=Math.floor(Math.random()*c.length),b=Math.random()<.5?a:Math.floor(Math.random()*c.length);truth=a===b;word.textContent=c[a][0];word.style.color=c[b][1];score.textContent='score: '+s}function answer(v){s+=v===truth?1:-1;s=Math.max(0,s);next()}next();"
    return shell(app, body, script)


def whack_game(app):
    body = '<section class="card"><div id="arena" style="height:260px;position:relative;border:1px solid #2c3540;border-radius:12px"><button id="dot" style="position:absolute;width:58px;height:58px;border-radius:50%" onclick="hit()">O</button></div><div id="score" class="small" style="margin-top:10px"></div><button class="secondary" onclick="start()" style="margin-top:10px">Start 15s</button></section>'
    script = "let s=0,left=0,t=null;function move(){dot.style.left=Math.floor(Math.random()*Math.max(1,arena.clientWidth-60))+'px';dot.style.top=Math.floor(Math.random()*200)+'px'}function hit(){if(left>0){s++;move();draw()}}function draw(){score.textContent='score: '+s+' · '+left+'s'}function start(){clearInterval(t);s=0;left=15;move();draw();t=setInterval(()=>{left--;draw();if(left<=0)clearInterval(t)},1000)}move();draw();"
    return shell(app, body, script)


def highlow_game(app):
    body = '<section class="card"><div class="small">Current number</div><div id="cur" class="big"></div><div class="row"><button onclick="guess(1)">Higher</button><button class="secondary" onclick="guess(-1)">Lower</button></div><div id="msg" class="small" style="margin-top:10px"></div></section>'
    script = "let c=1+Math.floor(Math.random()*13),s=0;function draw(){cur.textContent=c;msg.textContent='score: '+s}function guess(dir){let n=1+Math.floor(Math.random()*13),ok=dir===1?n>c:n<c;if(n===c){msg.textContent='Same number - no score change'}else{s=ok?s+1:0;msg.textContent=(ok?'Correct! ':'Miss. ')+'Next was '+n+' · score '+s}c=n;cur.textContent=c}draw();"
    return shell(app, body, script)


def sequence_game(app):
    body = '<section class="card"><div id="grid" style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px"></div><div id="msg" class="small" style="margin:10px 0"></div><button class="secondary" onclick="start()">Start / Restart</button></section>'
    script = "let seq=[],pos=0,locked=true;function draw(){grid.innerHTML=[0,1,2,3].map(i=>`<button id=\"b${i}\" style=\"height:90px\" onclick=\"tap(${i})\">${i+1}</button>`).join('')}function flash(i){let e=document.getElementById('b'+i),old=e.style.opacity;e.style.opacity=.25;setTimeout(()=>e.style.opacity=old||'1',250)}async function show(){locked=true;msg.textContent='Watch';for(let i of seq){await new Promise(r=>setTimeout(r,400));flash(i)}pos=0;locked=false;msg.textContent='Your turn'}function start(){seq=[];next()}function next(){seq.push(Math.floor(Math.random()*4));show()}function tap(i){if(locked)return;flash(i);if(i!==seq[pos]){locked=true;msg.textContent='Miss - reached '+(seq.length-1);return}pos++;if(pos===seq.length){msg.textContent='Good!';setTimeout(next,500)}}draw();"
    return shell(app, body, script)


def hangman_game(app):
    body = '<section class="card"><div id="word" class="big" style="font-size:2rem;letter-spacing:.2em"></div><input id="guess" maxlength="1" placeholder="Letter"><br><br><button onclick="go()">Guess</button><div id="msg" class="small" style="margin-top:10px"></div><button class="secondary" onclick="newGame()" style="margin-top:10px">New word</button></section>'
    script = "const words=['garden','planet','window','coffee','basket','summer','pillow','rocket'];let w='',seen=new Set(),miss=0;function draw(){word.textContent=[...w].map(c=>seen.has(c)?c:'_').join(' ');msg.textContent='misses: '+miss+'/6';if([...w].every(c=>seen.has(c)))msg.textContent='You got it!'}function go(){let c=guess.value.toLowerCase();guess.value='';if(!/^[a-z]$/.test(c)||seen.has(c))return;seen.add(c);if(!w.includes(c))miss++;if(miss>=6){word.textContent=w;msg.textContent='Out of guesses'}else draw()}function newGame(){w=words[Math.floor(Math.random()*words.length)];seen=new Set();miss=0;draw()}newGame();"
    return shell(app, body, script)


def snake_game(app):
    body = '<section class="card"><canvas id="cv" width="300" height="300" style="width:100%;max-width:300px;display:block;margin:auto;background:#10151a;border:1px solid #2c3540"></canvas><div class="row" style="margin-top:10px"><button onclick="turn(0,-1)">Up</button><button onclick="turn(-1,0)">Left</button><button onclick="turn(1,0)">Right</button><button onclick="turn(0,1)">Down</button></div><div id="msg" class="small" style="margin-top:10px"></div><button class="secondary" onclick="reset()" style="margin-top:10px">Restart</button></section>'
    script = "const ctx=cv.getContext('2d'),N=15,S=20;let snake,dx,dy,food,t,score;function foodNew(){food={x:Math.floor(Math.random()*N),y:Math.floor(Math.random()*N)}}function reset(){snake=[{x:7,y:7}];dx=1;dy=0;score=0;foodNew();clearInterval(t);t=setInterval(step,140);draw()}function turn(x,y){if(x===-dx&&y===-dy)return;dx=x;dy=y}function step(){let h={x:snake[0].x+dx,y:snake[0].y+dy};if(h.x<0||h.y<0||h.x>=N||h.y>=N||snake.some(p=>p.x===h.x&&p.y===h.y)){clearInterval(t);msg.textContent='Game over · score '+score;return}snake.unshift(h);if(h.x===food.x&&h.y===food.y){score++;foodNew()}else snake.pop();draw()}function draw(){ctx.clearRect(0,0,300,300);ctx.fillStyle='#79dcff';snake.forEach(p=>ctx.fillRect(p.x*S+1,p.y*S+1,S-2,S-2));ctx.fillStyle='#ffc766';ctx.fillRect(food.x*S+3,food.y*S+3,S-6,S-6);msg.textContent='score: '+score}document.addEventListener('keydown',e=>{if(e.key==='ArrowUp')turn(0,-1);if(e.key==='ArrowDown')turn(0,1);if(e.key==='ArrowLeft')turn(-1,0);if(e.key==='ArrowRight')turn(1,0)});reset();"
    return shell(app, body, script)


BUILDERS = {
    "list": list_app,
    "counter": counter_app,
    "calculator": calculator_app,
    "timer": timer_app,
    "randomizer": randomizer_app,
    "tip": tip_app,
    "percent": percent_app,
    "scale": scale_app,
    "fuel": fuel_app,
    "savings": savings_app,
    "loan": loan_app,
    "date_diff": date_diff_app,
    "countdown": countdown_app,
    "text_stats": text_stats_app,
    "text_case": text_case_app,
    "habit": habit_app,
    "split": split_app,
    "passphrase": passphrase_app,
    "unit": unit_app,
    "game_tap": tap_game,
    "game_number": number_game,
    "game_memory": memory_game,
    "game_word": word_game,
    "game_reaction": reaction_game,
    "game_rps": rps_game,
    "game_ttt": ttt_game,
    "game_math": math_game,
    "game_color": color_game,
    "game_whack": whack_game,
    "game_highlow": highlow_game,
    "game_sequence": sequence_game,
    "game_hangman": hangman_game,
    "game_snake": snake_game,
}

BUILDERS.update(extra_builders(shell))

unknown = sorted({app["kind"] for app in CATALOG} - set(BUILDERS))
if unknown:
    raise SystemExit(f"No builder for: {unknown}")

for app in CATALOG:
    folder = DIST / app["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    page = BUILDERS[app["kind"]](app)
    (folder / "index.html").write_text(page)
    manifest = {
        "name": app["name"],
        "short_name": app["name"][:12],
        "start_url": "./",
        "display": "standalone",
        "background_color": "#0d1014",
        "theme_color": "#0d1014",
    }
    (folder / "manifest.webmanifest").write_text(json.dumps(manifest))

(DIST / "catalog.json").write_text(json.dumps(CATALOG, indent=2))

def category(app):
    kind = app["kind"]
    if kind.startswith("game_"):
        return "Games"
    if kind in {"tip", "percent", "scale", "fuel", "savings", "loan", "split", "unit", "calculator", "date_diff", "countdown"}:
        return "Calculators"
    return "Everyday"


cards = []
for app in CATALOG:
    m = MONETIZATION.get(app["slug"], {})
    paid = bool(m.get("upgrade_url", "").strip())
    badge = " · upgrade available" if paid else ""
    name = html.escape(app["name"])
    tagline = html.escape(app["tagline"])
    cards.append(f'<a class="card" data-category="{category(app)}" data-search="{html.escape((app["name"] + " " + app["tagline"]).lower(), quote=True)}" href="./{html.escape(app["slug"], quote=True)}/"><strong>{name}</strong><span class="small">{category(app)}</span><div class="small" style="margin-top:6px">{tagline}{badge}</div></a>')
store = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>App Factory</title><meta name="description" content="{len(CATALOG)} standalone apps and games."><link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 64 64%27%3E%3Crect width=%2764%27 height=%2764%27 rx=%2714%27 fill=%27%230d1014%27/%3E%3Cpath d=%27M16 46V18h16a9 9 0 0 1 3 17 9 9 0 0 1-3 11Z%27 fill=%27none%27 stroke=%27%2379dcff%27 stroke-width=%276%27/%3E%3C/svg%3E"><style>{BASE_CSS}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}}a{{color:inherit;text-decoration:none}}.card strong{{display:block;font-size:1.1rem}}.card .small{{display:block}}.tools{{position:sticky;top:0;background:var(--bg);padding:10px 0 14px;z-index:1}}.filters{{display:flex;gap:6px;overflow-x:auto;padding-top:10px}}.filters button{{white-space:nowrap;background:#2a333d;color:white}}.filters button[aria-pressed=true]{{background:var(--accent);color:#051118}}.card[hidden]{{display:none}}</style></head><body><main><h1>App Factory</h1><div class="sub">{len(CATALOG)} standalone tools and games</div><div class="tools"><label for="search">Find an app</label><input id="search" type="search" placeholder="Search by name or use"><div class="filters" role="group" aria-label="App categories"><button type="button" data-filter="All" aria-pressed="true">All</button><button type="button" data-filter="Everyday" aria-pressed="false">Everyday</button><button type="button" data-filter="Calculators" aria-pressed="false">Calculators</button><button type="button" data-filter="Games" aria-pressed="false">Games</button></div></div><p id="count" class="small" role="status">{len(CATALOG)} apps</p><section class="grid" id="apps">{''.join(cards)}</section><p id="empty" hidden>No matching apps. Try another search.</p><p class="small">Free to use. Payment buttons appear only when a paid edition is available.</p></main><script>const search=document.getElementById('search'),cards=[...document.querySelectorAll('#apps a')],buttons=[...document.querySelectorAll('[data-filter]')],count=document.getElementById('count'),empty=document.getElementById('empty');let filter='All';function update(){{const q=search.value.trim().toLowerCase();let n=0;for(const card of cards){{const visible=(filter==='All'||card.dataset.category===filter)&&card.dataset.search.includes(q);card.hidden=!visible;if(visible)n++}}count.textContent=n+' '+(n===1?'app':'apps');empty.hidden=n!==0}}search.addEventListener('input',update);for(const button of buttons)button.addEventListener('click',()=>{{filter=button.dataset.filter;for(const item of buttons)item.setAttribute('aria-pressed',String(item===button));update()}});</script></body></html>'''
(DIST / "index.html").write_text(store)
print(f"Generated {len(CATALOG)} standalone apps plus storefront into {DIST}")
