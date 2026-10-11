import {api,el,showError} from './api.js';
import {ASTRA,parseRoute,link,href,clearCursors} from './evidence.js';
import {renderOverview} from './views/overview.js';import {renderActivity} from './views/activity.js';import {renderEnvironment} from './views/environment.js';import {renderMemory} from './views/memory.js';import {renderConcepts} from './views/concepts.js';import {renderLearning} from './views/learning.js';
const sections=[['overview','◉','Overview','A window into a developing system.'],['activity','≋','Live Activity','Follow the record from perception to memory.'],['environment','⌁','Environment','The MacBook, as SEED observes it.'],['memory','▤','Memory','Browse recorded experiences.'],['concepts','◇','Concepts','Legacy concepts from reflection windows; B6 records are in Semantic Memory.'],['learning','↗','Learning','Contextual learned values; frozen selection evidence is in Decisions.'],['development','◒','Development','Stored evidence from B1–B8. Each source has its own scope and clock.'],['predictions','↝','Predictions','Stored forecasts and their post-action evaluations.'],['world-model','◎','World Model','Descriptive environmental statistics, not causal laws.'],['curiosity','✧','Curiosity','Bounded computational salience, not subjective curiosity.'],['semantic-memory','◇','Semantic Memory','Descriptive B6 knowledge and recorded revisions.'],['self-model','◈','Self Model','Recorded capabilities and limits, not personality or consciousness.'],['decisions','⑂','Decisions','Frozen B8 selection evidence, separate from current learned values.'],['evaluation','⬡','Evaluation','Stored B10 evaluation artifacts, observed read-only; execution and findings shown separately.'],['interaction','○','Interaction','Owner observations, with clear provenance.'],['commands','⌘','Commands','Explicit actions within a small, safe boundary.'],['automation','◷','Automation','Owner-controlled routines. Always visible.'],['settings','⚙','Settings','Configure the local environment.']];
const renderers={overview:renderOverview,activity:renderActivity,environment:renderEnvironment,memory:renderMemory,concepts:renderConcepts,learning:renderLearning};
const modules={development:['development','renderDevelopment'],predictions:['predictions','renderPredictions'],'world-model':['world_model','renderWorldModel'],curiosity:['curiosity','renderCuriosity'],'semantic-memory':['semantic_memory','renderSemanticMemory'],'self-model':['self_model','renderSelfModel'],decisions:['decisions','renderDecisions']};
let abort,cleanup,current,generation=0;
const nav=document.querySelector('#navigation'),sidebar=document.querySelector('#sidebar'),menu=document.querySelector('#menu'),mobile=matchMedia('(max-width:760px)');
for(const [id,icon,name] of sections){if(id==='interaction'||id==='development')nav.append(el('div',id==='development'?'DEVELOPMENT':'OPERATE','nav-label'));const a=el('a');a.href='#'+id;const mark=el('span',icon,'nav-icon');mark.setAttribute('aria-hidden','true');a.append(mark,el('span',name));nav.append(a);}
function theme(value){if(value==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=value;localStorage.setItem('seed-theme',value);document.querySelector('#theme').textContent='Theme: '+value;}
theme(localStorage.getItem('seed-theme')||'system');document.querySelector('#theme').onclick=()=>{const all=['system','dark','light'];theme(all[(all.indexOf(localStorage.getItem('seed-theme'))+1)%3]);};
function menuState(open,restore=false){document.body.classList.toggle('menu-open',open);menu.setAttribute('aria-expanded',String(open));sidebar.inert=mobile.matches&&!open;if(open)nav.querySelector('[aria-current=page]')?.focus();else if(restore)menu.focus();}
menu.onclick=()=>menuState(!document.body.classList.contains('menu-open'));mobile.addEventListener('change',()=>menuState(false));menuState(false);
document.addEventListener('keydown',event=>{if(!mobile.matches||!document.body.classList.contains('menu-open'))return;if(event.key==='Escape'){event.preventDefault();menuState(false,true);}});
document.addEventListener('click',event=>{if(mobile.matches&&document.body.classList.contains('menu-open')&&!sidebar.contains(event.target)&&!menu.contains(event.target))menuState(false);});
async function render({focusHeading=false}={}){
  const parsed=parseRoute(location.hash);if(parsed.skip){document.querySelector('#main').focus();return;}
  abort?.abort();cleanup?.();cleanup=undefined;abort=new AbortController();const controller=abort,version=++generation;
  current=parsed.page;clearCursors(current);const section=sections.find(x=>x[0]===current);
  const astra=ASTRA.has(current);
  document.title=astra?'SEED — Astra / '+section[2]:'SEED — Local observatory';
  document.querySelector('.eyebrow').textContent=astra?'ASTRA · DEVELOPMENT EVIDENCE':'SITUATED EXPERIENTIAL EMERGENT DEVELOPMENT';
  document.querySelector('#page-title').textContent=section[2];document.querySelector('#breadcrumb').textContent=(astra?'Astra / ':'')+section[2];document.querySelector('#page-description').textContent=section[3];
  for(const a of nav.querySelectorAll('a')){if(a.hash==='#'+current)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');}
  menuState(false);const container=document.querySelector('#content'),root=el('div',null,'view-root');container.replaceChildren(root);container.setAttribute('aria-busy','true');root.append(el('p','Reading stored state…','subtle'));document.querySelector('#notice').hidden=true;
  if(focusHeading){const heading=document.querySelector('#page-title');heading.tabIndex=-1;heading.focus();}
  try{
    if(parsed.invalid){root.replaceChildren(el('p','Invalid view link','notice'),link('First page',current));return;}
    await api.bootstrap();
    if(controller.signal.aborted)return;
    let renderer=renderers[current];
    if(modules[current]){const [file,name]=modules[current];renderer=(await import('./views/'+file+'.js'))[name];}
    const returned=renderer?await renderer(root,controller.signal):undefined;
    const ceiling=current==='predictions'?1000:current==='semantic-memory'?2000:1500;
    if(ASTRA.has(current)&&root.querySelectorAll('*').length>ceiling){returned?.();throw new Error('Invalid evidence response: render limit exceeded');}
    if(controller.signal.aborted||version!==generation){returned?.();return;}cleanup=returned;
    if(!renderer)root.replaceChildren(el('p','Not implemented in this dashboard. B9 adds observation only.','notice'));
    if(ASTRA.has(current))document.querySelector('#connection').textContent=root.dataset.allFailed==='true'?'Service unavailable':'Stored evidence · local service reachable';
    else{
      const s=await api.get('status',controller.signal);if(controller.signal.aborted||version!==generation)return;
      document.querySelector('#connection').textContent=s.fresh?'● Core connected':s.data_state==='ready'?'◌ Reading stored state':'○ Data unavailable';
      if(s.compatibility==='legacy')showError('Legacy core connected. Memory and learning values are available; live activity and decision provenance require the telemetry upgrade.');
    }
    document.querySelector('#last-updated').textContent='Read at '+new Date().toLocaleTimeString();
  }catch(error){if(!controller.signal.aborted&&version===generation){showError(error.message);root.replaceChildren(el('p','The current data could not be loaded. Use Refresh to retry.','empty'));document.querySelector('#connection').textContent='Service unavailable';}}
  finally{if(!controller.signal.aborted&&version===generation)container.setAttribute('aria-busy','false');}
}
document.querySelector('.skip').addEventListener('click',event=>{event.preventDefault();document.querySelector('#main').focus();});
window.addEventListener('hashchange',()=>render({focusHeading:true}));document.querySelector('#refresh').onclick=()=>{const route=parseRoute(location.hash);if(route.page==='predictions'&&!route.invalid&&route.params.before){delete route.params.before;history.replaceState(null,'',href(route.page,route.params));}return render();};render();
setInterval(()=>{if(!document.hidden&&!document.querySelector('input:focus,textarea:focus,select:focus,details[open]')&&current==='overview')render();},10000);
