const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const root=path.join(__dirname,'..','dist');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'catalog.json')));
function load(slug,seed=[]){const html=fs.readFileSync(path.join(root,slug,'index.html'),'utf8');const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];const elements={};for(const m of html.matchAll(/id="([^"]+)"/g))elements[m[1]]={value:'',textContent:'',innerHTML:'',style:{}};const storage=new Map(seed);const context={...elements,name:'',status:'',document:{getElementById:id=>elements[id]},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,String(v))},setInterval:()=>1,clearInterval:()=>{},setTimeout:()=>1,clearTimeout:()=>{},Math};vm.createContext(context);vm.runInContext(source,context);return {context,elements,storage};}
function loadRich(slug,seed=[]){const html=fs.readFileSync(path.join(root,slug,'index.html'),'utf8');const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];const node=()=>({value:'',textContent:'',innerHTML:'',style:{},children:[],addEventListener(){},setAttribute(){},append(...items){this.children.push(...items)},replaceChildren(...items){this.children=[...items]},click(){}});const elements={};for(const m of html.matchAll(/id="([^"]+)"/g))elements[m[1]]=node();const storage=new Map(seed);const document={getElementById:id=>elements[id],createElement:()=>node()};const context={...elements,document,localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,String(v))},setInterval:()=>1,clearInterval:()=>{},setTimeout:()=>1,clearTimeout:()=>{},Math,Date,Array,JSON,Blob:function(){},URL:{createObjectURL:()=>'',revokeObjectURL(){}},window:{}};vm.createContext(context);vm.runInContext(source,context);return {context,elements,storage};}
const storefront=fs.readFileSync(path.join(root,'index.html'),'utf8');
assert.doesNotMatch(storefront,/Begg AI(?: Industries)?/i,'storefront must not expose the private parent brand');
function attrs(source){return Object.fromEntries([...source.matchAll(/([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)].map(match=>[match[1].toLowerCase(),match[2]??match[3]??match[4]??'']));}
function assertStaticControlNames(slug,html){
  const markup=html.replace(/<script>[\s\S]*?<\/script>/gi,'');
  const labels=new Set([...markup.matchAll(/<label\b[^>]*\bfor="([^"]+)"[^>]*>/gi)].map(match=>match[1]));
  const failures=[];
  for(const match of markup.matchAll(/<(input)\b([^>]*)>|<(select|textarea|button)\b([^>]*)>([\s\S]*?)<\/\3>/gi)){
    const tag=(match[1]||match[3]).toLowerCase(),properties=attrs(match[2]||match[4]||''),content=(match[5]||'').replace(/<[^>]+>/g,'').trim();
    if('hidden' in properties||properties.type?.toLowerCase()==='hidden')continue;
    const explicit=Boolean(properties['aria-label']?.trim()||properties['aria-labelledby']?.trim()||properties.title?.trim());
    const associated=Boolean(properties.id&&labels.has(properties.id));
    const ownText=tag==='button'&&Boolean(content);
    if(!(explicit||associated||ownText))failures.push(`<${tag}${properties.id?` id="${properties.id}"`:''}>`);
  }
  assert.deepEqual(failures,[],`${slug} has controls without programmatic names`);
}
for(const app of catalog){const html=fs.readFileSync(path.join(root,app.slug,'index.html'),'utf8');assert.doesNotMatch(html,/Begg AI(?: Industries)?/i,`${app.slug} must not expose the private parent brand`);new vm.Script(html.match(/<script>([\s\S]*?)<\/script>/)[1]);assertStaticControlNames(app.slug,html);}
assertStaticControlNames('storefront',storefront);
for(const app of catalog.filter(x=>x.kind==='list')){const html=fs.readFileSync(path.join(root,app.slug,'index.html'),'utf8');assert.match(html,/aria-label="\$\{x\.done\?'Mark incomplete: ':'Mark complete: '\}\$\{esc\(x\.text\)\}"/,`${app.slug} checklist labels must include item text and state`);assert.match(html,/aria-label="Delete \$\{esc\(x\.text\)\}"/,`${app.slug} delete labels must include item text`);}
for(const app of catalog.filter(x=>x.kind==='game_ttt')){const html=fs.readFileSync(path.join(root,app.slug,'index.html'),'utf8');assert.match(html,/aria-label="Cell \$\{i\+1\}: \$\{v\|\|'empty'\}"/,`${app.slug} empty board cells need a cell-specific name`);}
for(const slug of ['future-letter','tiny-museum']){const html=fs.readFileSync(path.join(root,slug,'index.html'),'utf8');assert.match(html,/setAttribute\('aria-label',/,`${slug} dynamic delete controls need item-specific labels`);}
{
  const future=fs.readFileSync(path.join(root,'future-letter','index.html'),'utf8');
  assert.match(future,/Array\.isArray\(value\)\?value\.filter\(x=>x&&typeof x\.text==='string'&&typeof x\.date==='string'\):\[\]/,'future-letter must discard malformed persisted notes');
  const rhythm=fs.readFileSync(path.join(root,'rhythm-lab','index.html'),'utf8');
  assert.match(rhythm,/pattern\.length!==8\|\|!pattern\.every\(x=>typeof x==='boolean'\)/,'rhythm-lab must reject malformed persisted beat schemas');
  const museum=fs.readFileSync(path.join(root,'tiny-museum','index.html'),'utf8');
  assert.match(museum,/Array\.isArray\(value\)\?value\.filter\(x=>x&&typeof x\.title==='string'&&x\.title&&typeof x\.detail==='string'&&typeof x\.date==='string'\):\[\]/,'tiny-museum must discard malformed persisted exhibits');
  for(const [slug,key,badValues] of [
    ['future-letter','begg:future-letter',['{','{}','[null,{"text":3,"date":false}]']],
    ['rhythm-lab','begg:rhythm-lab',['{','{}','[true]','[1,0,1,0,1,0,1,0]']],
    ['tiny-museum','begg:tiny-museum',['{','{}','[null,{"title":3}]']],
  ])for(const bad of badValues)assert.doesNotThrow(()=>loadRich(slug,[[key,bad]]),`${slug} must load with corrupt storage: ${bad}`);
}
for(const app of catalog.filter(x=>x.kind==='habit')){const {elements,storage}=load(app.slug);elements.name.value='Daily walk';elements.name.oninput();assert.equal(JSON.parse([...storage.values()][0]).name,'Daily walk');}
for(const app of catalog.filter(x=>x.kind==='list')){
  const key=`begg:${app.slug}:items`;
  for(const bad of ['{', '{}', 'null', '[null,{"text":7},{"text":"kept","done":"yes"}]']){
    const {context,elements}=load(app.slug,[[key,bad]]);
    assert.doesNotThrow(()=>context.draw(),`${app.slug} must recover from corrupt storage: ${bad}`);
    if(bad.includes('kept'))assert.match(elements.items.innerHTML,/kept/,`${app.slug} should preserve valid text entries`);
  }
}
for(const app of catalog.filter(x=>x.kind==='habit')){
  const key=`begg:${app.slug}:habit`;
  for(const bad of ['{','{}','null','{"name":"Walk","days":[true]}','{"name":3,"days":[false,false,false,false,false,false,false]}']){
    const {context,elements}=load(app.slug,[[key,bad]]);
    assert.doesNotThrow(()=>context.draw(),`${app.slug} must recover from corrupt storage: ${bad}`);
    assert.equal(elements.score.textContent,'0/7 complete');
  }
}
for(const app of catalog.filter(x=>x.kind==='game_tap')){const {context,elements}=load(app.slug);context.hit();context.hit();assert.equal(elements.status.textContent,1);}
for(const app of catalog.filter(x=>x.kind==='game_math')){const {context,elements}=load(app.slug);const initial=elements.q.textContent;context.check();assert.equal(elements.q.textContent,initial);}
{
  const slug='passphrase-maker';
  const html=fs.readFileSync(path.join(root,slug,'index.html'),'utf8');
  const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const n={value:'6'},out={textContent:''};
  const samples=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15];
  let fallback=16;
  const crypto={getRandomValues(array){assert.equal(array.length,1);array[0]=samples.shift()??fallback++;return array;}};
  const context={n,out,crypto,Uint32Array,Math};
  vm.createContext(context);
  vm.runInContext(source,context);
  const dictionarySize=vm.runInContext('words.length',context);
  const uniqueSize=vm.runInContext('new Set(words).size',context);
  assert.equal(dictionarySize,2048,'passphrase dictionary must have 2,048 choices');
  assert.equal(uniqueSize,dictionarySize,'passphrase dictionary entries must be unique');
  assert.ok(Math.log2(dictionarySize)*6>=64,'six-word minimum/default must provide at least 64 bits of selection entropy');
  assert.match(source,/crypto\.getRandomValues\(/,'passphrase selection must use Web Crypto');
  assert.match(source,/do\{crypto\.getRandomValues\(a\)\}while\(a\[0\]>=limit\)/,'passphrase selection must reject samples outside the unbiased range');
  assert.match(source,/return a\[0\]%size/,'passphrase selection may apply modulo only after rejection sampling');
  assert.equal(out.textContent.split('-').length,6,'default passphrase must contain six words');
  assert.equal(new Set(out.textContent.split('-')).size,6,'generated passphrase words must be unique');
  samples.splice(0,samples.length,0xffffffff,0);
  assert.equal(vm.runInContext('randomIndex(1536)',context),0,'rejection sampler must discard an out-of-range uint32 before modulo');
  n.value='2';context.make();assert.equal(out.textContent.split('-').length,6,'word count must clamp to the six-word minimum');
  n.value='99';context.make();assert.equal(out.textContent.split('-').length,8,'word count must clamp to the eight-word maximum');
  n.value='';context.make();assert.equal(out.textContent.split('-').length,6,'blank word count must use the six-word default');
  n.value='6.9';context.make();assert.equal(out.textContent.split('-').length,6,'fractional word counts must be truncated within bounds');
  n.value='invalid';context.make();assert.equal(out.textContent.split('-').length,6,'invalid word counts must use the six-word default');
  assert.match(html,/id="out"[^>]*role="status"[^>]*aria-live="polite"[^>]*aria-atomic="true"/,'generated result must be announced by assistive technology');
  assert.doesNotMatch(source,/localStorage|sessionStorage|fetch\(|XMLHttpRequest|WebSocket/,'passphrase generation must remain local-only and stateless');
  assert.doesNotMatch(html,/Begg AI(?: Industries)?|Begg Synthetic Industries|\bBSI\b/i,'passphrase app must not expose a private parent brand');
}
console.log(`All ${catalog.length} app scripts parse; accessibility, behavior, and hardened passphrase regressions passed.`);
