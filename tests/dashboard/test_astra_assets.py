"""No browser dependency: exercise shared ES modules with the available Node runtime."""
from pathlib import Path
import shutil
import subprocess
import pytest

STATIC=Path(__file__).resolve().parents[2]/'dashboard/static'


def javascript(source):
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable; browser acceptance covers shared client behavior')
    result=subprocess.run([node,'--input-type=module','-e',source],cwd=STATIC,text=True,capture_output=True)
    assert result.returncode==0,result.stderr


def test_lossless_evidence_parser():
    javascript(r'''
import assert from 'node:assert/strict';
import {parseEvidence} from './api.js';
const data=parseEvidence('{"id":9223372036854775807,"text":"escaped \\"9223372036854775807\\"","zero":0,"no":false,"f":0.5}'.replaceAll('\\\\"','\\"'),1024);
assert.equal(data.id,'9223372036854775807');assert.equal(data.zero,0);assert.equal(data.no,false);assert.equal(data.f,.5);
assert.equal(data.text,'escaped "9223372036854775807"');
for(const bad of ['{"n":1e999}','{"n":01}','{"n":NaN}','{"n":1,}','{"x":"\\ud800"}'])assert.throws(()=>parseEvidence(bad,1024));
assert.throws(()=>parseEvidence('{"x":"'+ 'a'.repeat(40)+'"}',10));
''')


def test_hash_routes_keep_exact_ids_and_reject_invalid_links():
    javascript('''
import assert from 'node:assert/strict';
import {parseRoute} from './evidence.js';
assert.equal(parseRoute('#predictions?transition=9223372036854775807').params.transition,'9223372036854775807');
assert.equal(parseRoute('#main').skip,true);
assert.equal(parseRoute('#unknown').page,'overview');
for(const hash of ['#predictions?transition=01','#predictions?before=0','#predictions?before=9223372036854775808','#curiosity?limit=20&limit=50','#world-model?belief=1&signal=battery_pct','#self-model?x=1','#semantic-memory?tab=runs&signal=battery_pct','#development?'+ 'x'.repeat(1024)])assert.equal(parseRoute(hash).invalid,true,hash);
assert.equal(parseRoute('#world-model?after=0&limit=100').invalid,undefined);
''')


def test_evidence_stream_caps_errors_and_abort():
    javascript('''
import assert from 'node:assert/strict';
import {api} from './api.js';
let cancelled=false;
globalThis.fetch=async()=>new Response(new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('x'.repeat(40)));},cancel(){cancelled=true;}}));
await assert.rejects(api.getEvidence('predictions',undefined,20),/limit/);assert.ok(cancelled);
globalThis.fetch=async()=>new Response('{"error":{"code":"evidence_read_unavailable","message":"Busy"}}',{status:503});
await assert.rejects(api.getEvidence('predictions'),e=>e.status===503&&e.code==='evidence_read_unavailable');
await assert.rejects(api.getEvidence('https://example.com'),/path/);
globalThis.fetch=async()=>new Response(new Uint8Array([255]));
await assert.rejects(api.getEvidence('predictions'),/encoded|UTF|encoding/i);
''')


def test_overview_development_failure_is_independent():
    text=(STATIC/'views/overview.js').read_text()
    assert 'developmentError' in text
    assert 'Development counts unavailable' in text
    assert 'highest learned values' not in (STATIC/'views/learning.js').read_text()
    assert "'0.0000'" not in (STATIC/'views/learning.js').read_text()
    assert 'Legacy concepts from reflection windows' in (STATIC/'views/concepts.js').read_text()
    assert 'episode' in (STATIC/'views/memory.js').read_text()


@pytest.mark.parametrize('module,renderer', [('development','renderDevelopment'),('predictions','renderPredictions'),
    ('world_model','renderWorldModel'),('curiosity','renderCuriosity'),('semantic_memory','renderSemanticMemory'),
    ('self_model','renderSelfModel'),('decisions','renderDecisions')])
def test_astra_view_modules_are_registered_and_read_only(module,renderer):
    path=STATIC/'views'/f'{module}.js'
    assert path.is_file()
    source=path.read_text()
    assert f'function {renderer}' in source
    assert renderer in (STATIC/'app.js').read_text()
    for forbidden in ('innerHTML','eval(','EventSource','setInterval','api.mutate','localStorage','sessionStorage'):
        assert forbidden not in source
    javascript(f"import {{ {renderer} }} from './views/{module}.js';if(typeof {renderer} !=='function')throw Error('Renderer missing');")


def test_prediction_detail_uses_envelope_identity():
    source=(STATIC/'views/predictions.js').read_text()
    assert 'transition_id:data.transition_id' in source.split('correlation')[0] or 'const transition={...data.transition,transition_id:data.transition_id}' in source


def test_request_deadline_and_navigation_abort_are_distinct():
    javascript('''
import assert from 'node:assert/strict';
import {api} from './api.js';
let deadline;
const originalSet=globalThis.setTimeout,originalClear=globalThis.clearTimeout;
globalThis.setTimeout=(fn,ms)=>{assert.equal(ms,10000);deadline=fn;return 1;};globalThis.clearTimeout=()=>{};
globalThis.fetch=async(_,{signal})=>await new Promise((resolve,reject)=>{signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')),{once:true});});
const pending=api.getEvidence('predictions');deadline();await assert.rejects(pending,e=>e.code==='read_timeout');
const controller=new AbortController(),next=api.getEvidence('predictions',controller.signal);controller.abort();await assert.rejects(next,e=>e.name==='AbortError'&&!e.code?.startsWith?.('read_'));
globalThis.setTimeout=originalSet;globalThis.clearTimeout=originalClear;
''')


def test_bootstrap_failure_can_retry_then_success_is_cached():
    javascript('''
import assert from 'node:assert/strict';import {api} from './api.js';
let attempts=0;api.token='stale';api.get=async()=>{if(++attempts===1)throw Error('Transient');return {token:'fresh'};};
await assert.rejects(api.bootstrap(),/Transient/);assert.equal(api.token,null);
const [a,b]=await Promise.all([api.bootstrap(),api.bootstrap()]);assert.equal(a.token,'fresh');assert.equal(b.token,'fresh');assert.equal(api.token,'fresh');
await api.bootstrap();assert.equal(attempts,2);
''')


def test_overview_renders_exact_degraded_fields_without_hiding_other_sources():
    javascript('''
import assert from 'node:assert/strict';import {Element,installDOM} from '../../tests/dashboard/astra_dom.mjs';import {api} from './api.js';import {renderOverview} from './views/overview.js';
installDOM();const root=new Element();let calls=[];
const sources={status:{identity:{name:'Fixture identity'},concepts:7,last_state:{battery_pct:80,load_ratio:.2},runtime:{activity:'Reading'},fresh:true,lifecycle:'AWAKE'},storage:{database_bytes:1024,budget_bytes:2048,percent_used:50},health:{database:'readable',process:{state:'fixture'},error_count:0}};
api.get=async path=>{calls.push(path);if(path==='development'){const e=Error('Busy');e.status=503;e.code='development_read_unavailable';throw e;}return sources[path];};
await renderOverview(root,new AbortController().signal);
for(const text of ['Fixture identity','Current activity','Battery','Compute load','Memory & storage','System health','Learned concepts','Retained development counts unavailable: bounded count read could not complete.','Lifecycle record unavailable.','Known contexts','Learning updates','Wake records','Owner interactions'])assert.ok(root.textContent.includes(text),text);
const dev=root.children.at(-1);assert.equal(dev.querySelectorAll('dd').length,4);assert.ok(dev.querySelectorAll('dd').every(x=>x.textContent==='Unavailable'));assert.equal(calls.filter(x=>x==='development').length,1);
api.get=async path=>{if(path==='development')throw Error('Other service failure');return sources[path];};await renderOverview(root,new AbortController().signal);assert.ok(!root.textContent.includes('bounded count read could not complete'));assert.ok(root.textContent.includes('Other service failure'));
''')


def test_evidence_tables_have_caption_scoped_headers_and_scroll_region():
    javascript('''
import assert from 'node:assert/strict';import {installDOM} from '../../tests/dashboard/astra_dom.mjs';import {table} from './api.js';
installDOM();const region=table(['Signal','Value'],[['battery_pct',0]],'World beliefs');
assert.equal(region.tabIndex,0);assert.ok(region.getAttribute('aria-label').includes('World beliefs'));assert.equal(region.querySelector('caption').textContent,'World beliefs');assert.ok(region.querySelectorAll('th').every(th=>th.getAttribute('scope')==='col'));
assert.ok(table(['Old view'],[['still works']]).querySelector('table'));
''')


def test_shell_focus_identity_disclosure_and_placeholder_contracts():
    javascript('''
import assert from 'node:assert/strict';import {installDOM} from '../../tests/dashboard/astra_dom.mjs';import {api} from './api.js';
const {ids,eyebrow,body}=installDOM(),events={};globalThis.window={addEventListener:(name,fn)=>events[name]=fn};globalThis.location={hash:'#development'};globalThis.localStorage={getItem:()=>null,setItem:()=>{}};document.documentElement={dataset:{}};
const mobile={matches:true,addEventListener:(name,fn)=>{mobile.change=fn;}};globalThis.matchMedia=()=>mobile;globalThis.setInterval=()=>0;
// Keep reads pending: navigation/focus/identity must not depend on a late response.
api.get=async()=>new Promise(()=>{});api.bootstrap=async()=>new Promise(()=>{});
await import('./app.js');assert.equal(document.activeElement,body,'initial load stole focus');
assert.equal(document.title,'SEED — Astra / Development');assert.equal(eyebrow.textContent,'ASTRA · DEVELOPMENT EVIDENCE');assert.equal(ids.get('breadcrumb').textContent,'Astra / Development');
location.hash='#predictions';events.hashchange();assert.equal(document.activeElement,ids.get('page-title'));document.activeElement=body;
location.hash='#predictions?transition=1';events.hashchange();assert.equal(document.activeElement,ids.get('page-title'),'same-page detail must focus heading');
ids.get('refresh').focus();ids.get('refresh').onclick();assert.equal(document.activeElement,ids.get('refresh'),'Refresh stole focus');
location.hash='#overview';events.hashchange();assert.equal(document.title,'SEED — Local observatory');assert.equal(eyebrow.textContent,'SITUATED EXPERIENTIAL EMERGENT DEVELOPMENT');
ids.get('menu').onclick();assert.equal(ids.get('sidebar').inert,false);let prevented=false;document.keydown({key:'Tab',preventDefault:()=>prevented=true});assert.equal(prevented,false,'disclosure must not trap Tab');document.keydown({key:'Escape',preventDefault:()=>{}});assert.equal(ids.get('sidebar').inert,true);assert.equal(document.activeElement,ids.get('menu'));mobile.matches=false;mobile.change();assert.equal(ids.get('sidebar').inert,false);
''')
    app=(STATIC/'app.js').read_text()
    assert 'Operator controls will appear' not in app
    assert 'Not implemented in this dashboard. B9 adds observation only.' in app


def test_development_responsive_grid_contract():
    css=(STATIC/'styles.css').read_text()
    assert '.development-grid{grid-template-columns:repeat(3,minmax(0,1fr))}' in css
    assert '@media(max-width:1120px){.development-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}' in css
    assert '@media(max-width:760px){.development-grid{grid-template-columns:1fr}}' in css


def test_bootstrap_deadline_clears_pending_attempt_and_allows_explicit_retry():
    javascript('''
import assert from 'node:assert/strict';import {api} from './api.js';
let deadline,attempts=0,cleared=0;globalThis.setTimeout=(fn,ms)=>{assert.equal(ms,10000);deadline=fn;return 1;};globalThis.clearTimeout=()=>cleared++;
api.token='stale';api.get=async(_path,signal)=>{attempts++;if(attempts>1)return {token:'recovered'};return new Promise((resolve,reject)=>signal?.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')),{once:true}));};
const pending=api.bootstrap();assert.equal(api.bootstrap(),pending);await Promise.resolve();assert.equal(typeof deadline,'function','bootstrap must have a bounded deadline');deadline();
await assert.rejects(pending,e=>e.code==='read_timeout');assert.equal(api.token,null);assert.equal(cleared,1);
await api.bootstrap();await api.bootstrap();assert.equal(api.token,'recovered');assert.equal(attempts,2);assert.equal(cleared,2);
''')


def test_evidence_timestamps_validate_clocks_and_expose_timezone_utc_epoch():
    javascript('''
import assert from 'node:assert/strict';import {installDOM} from '../../tests/dashboard/astra_dom.mjs';import {stamp,times} from './evidence.js';installDOM();
for(const v of [null,undefined,-1,1e20,Infinity,'1700000000']){const n=stamp(v);assert.ok(n.textContent.includes('Timestamp unavailable'));assert.ok(!n.textContent.includes('Invalid Date'));}
const valid=stamp(1700000000);assert.ok(valid.textContent.includes('2023-11-14T22:13:20.000Z'));assert.ok(valid.textContent.includes('1700000000'));assert.ok(valid.querySelector('details'));assert.ok(valid.textContent.includes(Intl.DateTimeFormat().resolvedOptions().timeZone));
assert.ok(stamp(Date.now()/1000+1000).textContent.includes('Ahead of dashboard clock'));assert.ok(!stamp(0).textContent.includes('Timestamp unavailable'));
const reversed=times({started_at:2,completed_at:1},['started_at','completed_at']);assert.ok(reversed.textContent.includes('Clock order inconsistent'));assert.ok(reversed.textContent.includes('1970-01-01T00:00:02.000Z'));
''')


def test_prediction_list_exposes_exact_episode_and_legacy_reward():
    javascript('''
import assert from 'node:assert/strict';import {Element,installDOM} from '../../tests/dashboard/astra_dom.mjs';import {api} from './api.js';import {renderPredictions} from './views/predictions.js';installDOM();globalThis.location={hash:'#predictions?limit=50'};
api.getEvidence=async()=>({available:true,items:Array.from({length:50},(_,i)=>({available:true,transition_id:i+1,episode_id:'9007199254740993',action:'observe',legacy_reward:0,completed_at:1700000000,prediction_present:false,evaluation_present:false})),next_cursor:null});
const root=new Element();await renderPredictions(root,new AbortController().signal);
assert.ok(root.querySelectorAll('th').some(n=>n.textContent==='Episode'));assert.ok(root.querySelectorAll('th').some(n=>n.textContent==='Legacy reward'));
assert.equal(root.querySelectorAll('a').filter(n=>n.href==='#memory?episode=9007199254740993').length,50);
assert.ok(root.querySelectorAll('td').some(n=>n.textContent==='0'));assert.ok(root.querySelectorAll('*').length<=1000,'50-row prediction page exceeds approved render ceiling');
''')
