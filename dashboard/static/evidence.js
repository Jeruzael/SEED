import {api,el,card,list,details,button,table,select,date} from './api.js';
export const ASTRA=new Set(['development','predictions','world-model','curiosity','semantic-memory','self-model','decisions']);
export const SIGNALS=['battery_pct','load_ratio','disk_free_pct','network_reachable'];
export const ACTIONS=['observe','reflect','consolidate','rest'];
export function id(value,zero=false){const text=String(value);if(!/^(0|[1-9][0-9]{0,18})$/.test(text)||BigInt(text)>(2n**63n-1n)||(!zero&&text==='0'))throw new Error('Invalid evidence ID');return text;}
const pages=new Set(['overview','activity','environment','memory','concepts','learning','interaction','commands','automation','settings',...ASTRA]);
export function parseRoute(hash){
  if(hash==='#main')return {skip:true};
  const [raw,query='',...extra]=hash.replace(/^#/,'').split('?'),page=pages.has(raw)?raw:'overview';
  try{
    if(new TextEncoder().encode(hash).length>1024||extra.length)throw Error();
    const params={},search=new URLSearchParams(query);
    for(const [key,value] of search){if(Object.hasOwn(params,key))throw Error();params[key]=value;}
    const detail={predictions:'transition','world-model':'belief',curiosity:'transition','semantic-memory':'semantic',decisions:'transition',memory:'episode'}[page];
    let allowed=[];
    if(detail&&Object.hasOwn(params,detail))allowed=page==='semantic-memory'?[detail,'history_before','limit']:[detail];
    else if(['predictions','curiosity','decisions'].includes(page))allowed=['before','limit'];
    else if(page==='world-model')allowed=['signal','scope','scope_value','after','limit'];
    else if(page==='semantic-memory')allowed=params.tab==='runs'?['tab','before','limit']:['tab','signal','scope','status','after','limit'];
    for(const [key,value] of Object.entries(params)){
      if(!allowed.includes(key))throw Error();
      if(['before','after','transition','belief','semantic','episode','history_before'].includes(key))id(value,['after','history_before'].includes(key)||key==='before'&&!['predictions','decisions'].includes(page));
      else if(key==='limit'){id(value);if(BigInt(value)>BigInt(['predictions','decisions'].includes(page)?50:100))throw Error();}
      else if(key==='signal'&&!SIGNALS.includes(value))throw Error();
      else if(key==='scope'&&!['global','action'].includes(value))throw Error();
      else if(key==='scope_value'&&!['',...ACTIONS].includes(value))throw Error();
      else if(key==='status'&&!['active','weakened','source_unavailable'].includes(value))throw Error();
      else if(key==='tab'&&!['memories','runs'].includes(value))throw Error();
    }
    return {page,params};
  }catch{return {page,params:{},invalid:true};}
}
export function route(){const result=parseRoute(location.hash);if(result.invalid)throw new Error('Invalid view link');return result;}
export function href(page,params={}){const query=new URLSearchParams(Object.entries(params).filter(([,v])=>v!==undefined&&v!==null));return '#'+page+(query.size?'?'+query:'');}
export function link(label,page,params={}){const a=el('a',label,'evidence-link');a.href=href(page,params);return a;}
export function value(v){return v===null||v===undefined?'Unavailable':typeof v==='boolean'?(v?'Yes':'No'):String(v);}
export function stamp(v){if(typeof v!=='number'||!Number.isFinite(v))return value(v);const formatted=date(v);return v>Date.now()/1000?formatted+' · future timestamp / clock difference':formatted;}
export function badge(label){return el('span',label||'Unavailable','badge '+(/corrupt|error|failed/i.test(label)?'error':/unavailable|legacy|missing|stale/i.test(label)?'warning':''));}
export function raw(data){return details('Formatted stored fields; large integers are displayed as decimal strings',data);}
export function pairs(data,keys){return list(keys.map(key=>[key.replaceAll('_',' '),value(data?.[key])]));}
export function times(data,keys){return list(keys.map(key=>[key.replaceAll('_',' '),stamp(data?.[key])]));}
export function state(root,data){
  if(!data||typeof data!=='object'||Array.isArray(data))throw Error('Invalid evidence response');
  const label=data.read_status==='corrupt'?'Corrupt stored evidence':data.status==='error'?'Stored evidence error':data.available===false?(data.reason||'Legacy / unavailable'):null;
  if(label){root.append(badge(label),el('p',data.read_reason||data.reason||'This source is unavailable.'));return false;}return true;
}
export function listItems(data,max=100){if(!Array.isArray(data.items)||data.items.length>max)throw Error('Invalid evidence list bounds');return data.items;}
export async function read(path,signal){const data=await api.getEvidence(path,signal);if(signal?.aborted)throw new DOMException('Navigation cancelled','AbortError');return data;}
export function readTime(root){root.append(el('small','Read at '+new Date().toLocaleString(),'read-time'));}
export function report(root,error,retry){if(error.name==='AbortError')return;root.replaceChildren(badge('Service unavailable'),el('p',error.message));if(retry)root.append(button('Retry',retry));}
export function filterBar(page,params,definitions){
  const form=el('form',null,'toolbar'),controls=[];
  for(const [key,label,options] of [...definitions,['limit','Page size',[['20','20'],['50','50']]]]){
    const opts=[...options];if(key==='limit'&&params.limit&&!opts.some(([v])=>v===params.limit))opts.push([params.limit,params.limit]);
    const [labelNode,control]=select(label,opts);control.value=params[key]??(key==='limit'?'20':'');form.append(labelNode);controls.push([key,control]);
  }
  const apply=el('button','Apply filters');apply.type='submit';form.append(apply);
  form.addEventListener('submit',event=>{event.preventDefault();const next={};if(params.tab)next.tab=params.tab;for(const [key,control] of controls)if(control.value)next[key]=control.value;if(next.scope==='global')delete next.scope_value;location.hash=href(page,next);});return form;
}
const cursorHistory=new Map();
export function clearCursors(page){for(const key of cursorHistory.keys())if(!key.startsWith(page+'|'))cursorHistory.delete(key);}
export function pager(page,params,next,descending=true,cursor=descending?'before':'after'){
  const base={...params};delete base[cursor];const key=page+'|'+new URLSearchParams(base);let history=cursorHistory.get(key)||[];
  const current=params[cursor]??null,existing=history.indexOf(current);
  if(existing>=0)history=history.slice(0,existing+1);else history=[...history,current].slice(-20);
  cursorHistory.clear();cursorHistory.set(key,history);
  const row=el('div',null,'pagination');row.append(link('First page',page,base));
  if(history.length>1)row.append(link(descending?'Newer':'Previous',page,{...base,[cursor]:history.at(-2)}));
  if(next!==null&&next!==undefined)row.append(link(descending?'Older':'Next',page,{...base,[cursor]:id(next,true)}));return row;
}
export function correlation(root,data){
  const row=el('div',null,'button-row');
  for(const [key,page,param,label] of [['transition_id','predictions','transition','Prediction / outcome'],['episode_id','memory','episode','Episode'],['source_belief_id','world-model','belief','Source belief'],['source_first_transition_id','predictions','transition','First source transition'],['source_last_transition_id','predictions','transition','Last source transition']]){
    if(data[key]!=null){try{row.append(link(label+' #'+id(data[key]),page,{[param]:id(data[key])}));}catch{/* Invalid record identifiers are never linked. */}}
  }
  if(row.childNodes.length)root.append(row);
}
export function detailPane(root,signal){
  let controller;
  signal.addEventListener('abort',()=>controller?.abort(),{once:true});
  const open=async(path,render)=>{
    controller?.abort();controller=new AbortController();const current=controller;
    root.replaceChildren(el('p','Reading stored detail…'));root.setAttribute('aria-busy','true');
    try{const data=await read(path,current.signal);if(signal.aborted||controller!==current)return;root.replaceChildren();render(root,data);root.tabIndex=-1;root.focus();readTime(root);}
    catch(error){if(!signal.aborted&&controller===current)report(root,error,()=>open(path,render));}
    finally{if(controller===current)root.setAttribute('aria-busy','false');}
  };
  return open;
}
