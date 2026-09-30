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
