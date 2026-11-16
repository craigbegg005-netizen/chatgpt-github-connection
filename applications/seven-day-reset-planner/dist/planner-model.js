(function(root){
'use strict';
const themes=['Clear the clutter','Reconnect with yourself','Restore your energy','Focus on what matters','Make space for joy','Recalibrate','Reflect and begin again'];
const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const date=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&!Number.isNaN(Date.parse(s))&&new Date(s).toISOString().slice(0,10)===s;
function empty(){return {version:2,showReset:false,days:{},challenges:[]}}
function validate(s){
 if(!obj(s)||s.version!==2||typeof s.showReset!=='boolean'||!obj(s.days)||!Array.isArray(s.challenges))throw Error('Not a supported planner backup.');
 if(Object.keys(s.days).length>30000||s.challenges.length>1000)throw Error('Backup is too large.');
 for(const [d,v] of Object.entries(s.days)){if(!date(d)||!obj(v)||Object.entries(v).some(([k,x])=>!['priorities','schedule','reflection'].includes(k)||typeof x!=='string'||x.length>50000))throw Error('Invalid daily entry.');}
 const ids=new Set();for(const c of s.challenges){
 if(!obj(c)||typeof c.id!=='string'||!/^c[\w-]+$/.test(c.id)||ids.has(c.id)||typeof c.name!=='string'||!c.name.trim()||c.name.length>120||typeof c.goal!=='string'||c.goal.length>2000||!['guided','custom'].includes(c.kind)||!Number.isInteger(c.duration)||c.duration<1||c.duration>365||!Number.isInteger(c.day)||c.day<1||c.day>c.duration||!['active','paused','completed'].includes(c.status)||!date(c.started)||!Array.isArray(c.tasks)||c.tasks.length<1||c.tasks.length>20||c.tasks.some(t=>typeof t!=='string'||!t.trim()||t.length>200)||!obj(c.checks))throw Error('Invalid challenge.');
 ids.add(c.id);for(const [k,v] of Object.entries(c.checks)){const m=/^(\d+):(\d+)$/.exec(k);if(!m||+m[1]<1||+m[1]>c.duration||+m[2]>=c.tasks.length||typeof v!=='boolean')throw Error('Invalid progress.');}
 }return s;
}
function create(s,{id,name,goal,duration,tasks,kind,started}){const c={id,name:name.trim(),goal:goal.trim(),duration, tasks:tasks.map(t=>t.trim()).filter(Boolean),kind,started,day:1,status:'active',checks:{}};validate({...s,challenges:[...s.challenges,c]});s.challenges.push(c);return c;}
function transition(c,action){if(action==='pause'&&c.status==='active')c.status='paused';else if(action==='resume'&&c.status==='paused')c.status='active';else if(action==='next'&&c.status==='active')c.day=Math.min(c.duration,c.day+1);else if(action==='complete'&&c.status==='active'&&c.day===c.duration)c.status='completed';}
function merge(current,incoming){validate(current);validate(incoming);const s=JSON.parse(JSON.stringify(current));for(const [d,v] of Object.entries(incoming.days))if(!Object.hasOwn(s.days,d))s.days[d]=v;const ids=new Set(s.challenges.map(c=>c.id));for(const c of incoming.challenges)if(!ids.has(c.id))s.challenges.push(c);return validate(s);}
function mergeLegacy(currentRaw,incomingRaw){
 const parse=raw=>{const v=JSON.parse(raw||'{}');if(!obj(v)||Object.entries(v).some(([k,x])=>!(/^(week_(intention|release|space|feeling|of)|priority_[123]|d[1-7]_(intention|priorities|choice|schedule|habit_(water|movement|pause)|review_[012]))$/).test(k)||!['string','boolean'].includes(typeof x)))throw Error('Original worksheet data could not be merged safely.');return v;};
 const current=parse(currentRaw),incoming=parse(incomingRaw);return JSON.stringify({...incoming,...current});
}
const api={empty,validate,create,transition,merge,mergeLegacy,themes,date};if(typeof module!=='undefined')module.exports=api;else root.PlannerModel=api;
})(typeof window==='undefined'?{}:window);
