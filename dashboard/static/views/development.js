import {el,card,button,table} from '../api.js';
import {read,state,listItems,raw,pairs,times,readTime,link,stamp,value,report,badge} from '../evidence.js';
let countsLoaded=false;
export async function renderDevelopment(root,signal){
 root.replaceChildren(el('p','A mosaic of separately recorded evidence. Cards do not describe one atomic current state.','notice'));
 const grid=el('div',null,'source-grid');root.append(grid);
 const sources=[['Latest transition / prediction / evaluation','predictions?limit=1','predictions'],['World Model','world-beliefs?limit=20','world-model'],['Recent Curiosity','curiosity?limit=1','curiosity'],['Latest consolidation','consolidation-runs?limit=1','semantic-memory'],['Stored Self Model','self-model','self-model'],['Latest stored decision','decisions?limit=1','decisions']];
 const cards=sources.map(([title])=>{const c=card(title);c.append(el('p','Reading stored evidence…'));grid.append(c);return c;});
 const results=await Promise.allSettled(sources.map(([,path])=>read(path,signal)));if(signal.aborted)return;
 root.dataset.allFailed=String(results.every(r=>r.status==='rejected'));
 for(let i=0;i<results.length;i++){
  const c=cards[i],result=results[i],[title,,page]=sources[i];c.replaceChildren(el('h2',title));
  if(result.status==='rejected'){report(c,result.reason);c.prepend(el('h2',title));continue;}
  const data=result.value;if(!state(c,data)){c.append(link('Open '+title,page));readTime(c);continue;}
  if(page==='self-model'){
   const p=data.snapshot;if(!p)throw Error('Invalid self-model response');c.append(times(p,['measured_at']),pairs(p,['source_transition_id']),raw({observation_statuses:Object.fromEntries(Object.entries(p.observations).map(([k,v])=>[k,{status:v.status,reason:v.reason}])),memory:p.memory,sources:p.sources}),link('Open Self Model',page));
  }else{
   const items=listItems(data,page==='world-model'?20:1),item=items[0];
   if(page==='world-model'){
    const valid=items.filter(r=>r.read_status!=='corrupt'),clocks=valid.map(r=>r.updated_at).filter(v=>typeof v==='number');
    c.append(pairs({slots:items.length,valid:valid.length,corrupt:items.length-valid.length,has_next_page:data.next_cursor!==null},['slots','valid','corrupt','has_next_page']),el('p','This page only; not total model size.'),times({earliest_record_update:clocks.length?Math.min(...clocks):null,latest_record_update:clocks.length?Math.max(...clocks):null},['earliest_record_update','latest_record_update']),link('Open World Model',page));
   }else if(!item)c.append(el('p',page==='semantic-memory'?'No run recorded; semantic memory may still exist.':'No retained record.','empty'),link('Open '+title,page,page==='semantic-memory'?{tab:'runs'}:{}));
   else{
    state(c,item);
    if(page==='predictions')c.append(pairs(item,['transition_id','action']),times(item,['completed_at']),badge(item.available===false?'Unavailable':item.prediction_present?'Prediction present':'Prediction absent'),badge(item.available===false?'Unavailable':item.evaluation_present?'Evaluation present':'Evaluation absent'),el('p','Contents checked on opening.'),link('Inspect transition',page,{transition:item.transition_id}));
    if(page==='curiosity')c.append(pairs(item,['transition_id','status','level','score','reflection_eligible','reflection_claimed','reflection_completed','suppression_reason','failure_reason']),times(item,['created_at']),link('Inspect assessment',page,{transition:item.transition_id}));
    if(page==='semantic-memory')c.append(pairs(item,['id','provenance','status']),times(item,['started_at','completed_at']),raw(item.result),link('Inspect runs',page,{tab:'runs'}));
    if(page==='decisions')c.append(pairs(item,['transition_id','decision_id','selected_action','selection_mode','policy_basis']),times(item,['selected_at','created_at']),link('Inspect decision',page,{transition:item.transition_id}));
   }
  }
  readTime(c);
 }
 const retained=card('Legacy retained development counts');grid.append(retained);const load=async()=>{countsLoaded=true;retained.replaceChildren(el('h2','Legacy retained development counts'),el('p','Reading exact retained counts…'));try{const data=await read('development',signal);retained.replaceChildren(el('h2','Legacy retained development counts'),pairs(data,['observations','owner_interactions','wake_records','sleep_stop_records','known_contexts','learning_updates','concepts']),el('p',data.scope),table(['Lifecycle event','Recorded','Note'],data.timeline.map(row=>[row.event,stamp(row.ts),row.read_status==='corrupt'?'Corrupt stored note':value(row.note)])));readTime(retained);}catch(error){if(!signal.aborted){report(retained,error,load);retained.prepend(el('h2','Legacy retained development counts'));}}};
 if(countsLoaded)await load();else retained.append(badge('Not loaded'),button('Load retained counts',load));
}
