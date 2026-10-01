import {el,card,table} from '../api.js';
import {read,state,raw,pairs,times,correlation,readTime,value,badge,link,id} from '../evidence.js';
function envelope(root,label,item,sources){
 if(!item||typeof item!=='object'||!Object.hasOwn(item,'value')||!sources[item.source])throw Error('Invalid self-model envelope');
 const section=card(label),source=sources[item.source];section.append(badge(item.status),pairs(item,['reason','source']));
 if(item.value!==null&&typeof item.value==='object')section.append(raw(item.value));else section.append(el('p',value(item.value),'mono'));
 section.append(pairs(source,['table','timestamp_kind','ttl_seconds']),times(source,['source_observed_at']),raw({source_ids:source.ids}));
 if(source.table==='transitions'&&source.ids?.length){const links=el('details');links.append(el('summary','Source transitions'));for(const sourceId of source.ids){try{const exact=id(sourceId);links.append(link('Transition #'+exact,'predictions',{transition:exact}));}catch{/* Invalid identifiers remain unlinked. */}}section.append(links);}
 if(source.table==='consolidation_runs'&&source.ids?.length)section.append(link('Open Consolidation runs','semantic-memory',{tab:'runs'}));
 root.append(section);
}
export function selfModelDetail(root,data){
 if(!state(root,data))return;const snapshot=data.snapshot;if(!snapshot?.sources||!snapshot.capabilities||!snapshot.memory)throw Error('Invalid self-model snapshot');
 root.append(pairs(snapshot,['model','model_version','source_transition_id','source_event_id','source_session_id']),times(snapshot,['measured_at']),times(data,['read_at']),el('p','Each status and TTL is supplied by B7. Snapshot-reported schema and counts describe that snapshot, including exact / at_least relations.','notice'));correlation(root,{transition_id:snapshot.source_transition_id});
 const sections=el('div',null,'source-grid');root.append(sections);
 for(const [name,item] of Object.entries(snapshot.observations))envelope(sections,'Observation: '+name,item,snapshot.sources);
 const catalog=card('Supported sensor catalog and resource references');catalog.append(raw(snapshot.capabilities.sensors),raw(snapshot.resources));sections.append(catalog);
 for(const [name,item] of Object.entries(snapshot.capabilities.actions))envelope(sections,'Action catalog: '+name,item,snapshot.sources);
 for(const [name,item] of Object.entries(snapshot.capabilities.unsupported))envelope(sections,'Unsupported: '+name,item,snapshot.sources);
 envelope(sections,'Last selected action',snapshot.last_selected_action,snapshot.sources);
 for(const [name,item] of Object.entries(snapshot.prediction_performance))envelope(sections,'Prediction performance snapshot: '+name,item,snapshot.sources);
 for(const [name,item] of Object.entries(snapshot.memory))envelope(sections,'Memory / storage: '+name,item,snapshot.sources);
 envelope(sections,'Recent failures and limitations',snapshot.recent_failures,snapshot.sources);
}
export async function renderSelfModel(root,signal){const panel=card('Stored Self Model');root.replaceChildren(panel);selfModelDetail(panel,await read('self-model',signal));readTime(panel);}
