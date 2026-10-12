"""I27/I28: bounded Astra Evaluation client, routes and view assets.

Exercises the shared ES modules with the available Node runtime, the
same way the B9 Astra asset tests do; actual browser acceptance is
recorded separately by I29.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

STATIC = Path(__file__).resolve().parents[2] / 'dashboard/static'


def javascript(source):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable; browser acceptance covers shared '
                    'client behavior')
    result = subprocess.run([node, '--input-type=module', '-e', source],
                            cwd=STATIC, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_evaluation_routes_and_lossless_ids():
    javascript(r'''
import assert from 'node:assert/strict';
import {parseEvaluationRoute} from './evaluation_support.js';
import {parseRoute} from './evidence.js';
// Registered selectors parse; run list is the default.
assert.deepEqual(parseEvaluationRoute('#evaluation').params, {});
assert.equal(parseEvaluationRoute('#evaluation?run=' + 'a'.repeat(32)).params.run, 'a'.repeat(32));
// Registered event keys parse: the ordinal domain is 1..2048.
// (Signed-64 scientific source IDs stay exact strings in event
// bodies -- see the parseEvidence tests -- but they are not event
// ordinals; M-03 aligned this grammar with the server's.)
const validEvent = parseEvaluationRoute('#evaluation?run=' + 'a'.repeat(32) + '&event=measured:default:2048:update');
assert.equal(validEvent.invalid, undefined);
assert.equal(validEvent.params.event, 'measured:default:2048:update');
const firstEvent = parseEvaluationRoute('#evaluation?run=' + 'a'.repeat(32) + '&event=measured:default:1:update');
assert.equal(firstEvent.invalid, undefined);
// The shell route delegates to the strict evaluation parser.
assert.equal(parseRoute('#evaluation?run=' + 'a'.repeat(32)).page, 'evaluation');
assert.equal(parseRoute('#evaluation?run=' + 'a'.repeat(32)).invalid, undefined);
for (const bad of [
  '#evaluation?run=' + 'A'.repeat(32),                 // uppercase ID
  '#evaluation?run=' + 'a'.repeat(31),                 // short ID
  '#evaluation?run=../../etc',                        // path-like ID
  '#evaluation?cursor=' + 'A'.repeat(513),             // oversized cursor
  '#evaluation?run=' + 'a'.repeat(32) + '&run=' + 'b'.repeat(32),  // duplicate
  '#evaluation?bogus=1',                               // unknown selector
  '#evaluation?right=' + 'b'.repeat(32),               // right requires left
  '#evaluation?event=measured:default:9223372036854775808:update', // > int64
  '#evaluation?event=measured:default:9223372036854775807:update', // int64 max: a source ID, not an ordinal
  '#evaluation?event=measured:default:9007199254740993:update', // above-safe source ID, not an ordinal
  '#evaluation?event=measured:default:0:update',       // ordinal starts at 1
  '#evaluation?event=measured:default:2049:update',    // ordinal ceiling is 2048
  '#evaluation?event=measured:default:01:update',      // leading zero
  '#evaluation?event=bogus:default:1:update',          // unregistered phase
  '#evaluation?event=measured:bogus:1:update',         // unregistered subcase
  '#evaluation?event=measured:default:1:bogus',        // unregistered stage
  '#evaluation?chunk=-1',
  '#evaluation?file=../secret',
  '#other?run=' + 'a'.repeat(32),
]) assert.equal(parseEvaluationRoute(bad).invalid, true, bad);
''')


def test_evaluation_client_cancel_and_timeout():
    javascript(r'''
import assert from 'node:assert/strict';
import {fetchEvaluation, EVALUATION_TIMEOUT_MS} from './evaluation_support.js';
assert.equal(EVALUATION_TIMEOUT_MS, 2000);
// Slow server: the 2 s client deadline (shortened here via options)
// aborts and cleans up instead of hanging. The mock honors the abort
// signal the way real fetch does.
globalThis.fetch = (url, opts) => new Promise((resolve, reject) => {
  opts.signal.addEventListener('abort', () => reject(new DOMException('x', 'AbortError')));
});
await assert.rejects(fetchEvaluation('evaluation/runs', undefined, {timeoutMs: 50}), /timed out/i);
// Oversized streamed response is rejected and the stream canceled.
let cancelled = false;
globalThis.fetch = async () => new Response(new ReadableStream({
  start(c) { c.enqueue(new TextEncoder().encode('x'.repeat(4096))); },
  cancel() { cancelled = true; }
}));
await assert.rejects(fetchEvaluation('evaluation/runs', undefined, {maxBytes: 1024}), /limit/);
assert.ok(cancelled);
// Canceled navigation: caller abort surfaces as AbortError, and a late
// response cannot be mistaken for data.
const controller = new AbortController();
globalThis.fetch = async (url, opts) => new Promise((resolve, reject) => {
  opts.signal.addEventListener('abort', () => reject(new DOMException('x', 'AbortError')));
  setTimeout(() => resolve(new Response('{"available":true,"items":[]}')), 30);
});
const pending = fetchEvaluation('evaluation/runs', controller.signal);
controller.abort();
await assert.rejects(pending, e => e.name === 'AbortError');
// Malformed UTF-8 is fatal, never lossy-decoded.
globalThis.fetch = async () => new Response(new Uint8Array([255, 254]));
await assert.rejects(fetchEvaluation('evaluation/runs'), /encoded|UTF|encoding/i);
// Error bodies are capped at 1024 bytes; a normal error body surfaces
// its typed code, an oversized one degrades to a bounded generic error.
globalThis.fetch = async () => new Response(
  JSON.stringify({error: {code: 'evaluation_unavailable', message: 'No root'}}),
  {status: 503});
await assert.rejects(fetchEvaluation('evaluation/runs'),
  e => e.status === 503 && e.code === 'evaluation_unavailable');
globalThis.fetch = async () => new Response(
  JSON.stringify({error: {code: 'evaluation_unavailable', message: 'x'.repeat(5000)}}),
  {status: 503});
await assert.rejects(fetchEvaluation('evaluation/runs'),
  e => e.status === 503 && e.message.length <= 1024);
// Lossless signed-64 values survive the client parser as exact strings.
globalThis.fetch = async () => new Response('{"id":9223372036854775807,"n":9007199254740993}');
const data = await fetchEvaluation('evaluation/runs');
assert.equal(data.id, '9223372036854775807');
assert.equal(data.n, '9007199254740993');
''')


def _mock_fetch(routes):
    """JS prelude: route globalThis.fetch by URL substring to JSON bodies."""
    lines = ["globalThis.fetch = async (url) => {"]
    for needle, payload in routes:
        lines.append(
            f"  if (String(url).includes({needle!r})) "
            f"return new Response({payload!r});")
    lines.append("  return new Response('{\"error\":{\"code\":\"not_found\","
                 "\"message\":\"missing\"}}', {status: 404});")
    lines.append("};")
    return '\n'.join(lines)


def test_negative_findings_visible_on_completed_run():
    detail = ('{"run_id":"' + 'a' * 32 + '","status":"COMPLETED",'
              '"reason":null,"science_digest":"' + 'e' * 64 + '",'
              '"counts":{"planned_transitions":2,"joined_events":2,'
              '"observed_transitions":2,"skipped_attempts":1},'
              '"measurements":[],"verification":"VERIFIED",'
              '"chunk_verification":"VERIFIED",'
              '"receipt_digest":"' + 'f' * 64 + '",'
              '"receipt_files":["manifest.json","metrics.json"],'
              '"findings":[{"question":"prediction","status":"NEGATIVE",'
              '"reason":"PREREGISTERED_RULE","execution":"COMPLETED"},'
              '{"question":"world","status":"NOT_EVALUATED",'
              '"reason":"DESCRIPTIVE_ONLY","execution":"COMPLETED"}]}')
    javascript(r'''
import assert from 'node:assert/strict';
import {Element, installDOM} from '../../tests/dashboard/astra_dom.mjs';
installDOM();
''' + _mock_fetch([('evaluation/runs/' + 'a' * 32, detail)]) + r'''
globalThis.location = {hash: '#evaluation?run=' + 'a'.repeat(32)};
const {renderEvaluation} = await import('./views/evaluation.js');
const root = new Element();
await renderEvaluation(root, new AbortController().signal);
const text = root.textContent;
// Execution and findings are separate, both prominent.
assert.ok(text.includes('Execution'), text);
assert.ok(text.includes('Scientific findings'), text);
assert.ok(text.includes('COMPLETED'));
assert.ok(text.includes('NEGATIVE'), 'unfavorable finding must stay visible');
assert.ok(text.includes('NOT_EVALUATED'));
assert.ok(!/scientific[^.]*\bPASS\b/i.test(text), 'no universal scientific PASS');
''')


def test_comparison_blocks_incompatibility():
    compare = ('{"left":"' + 'a' * 32 + '","right":"' + 'b' * 32 + '",'
               '"compatible":false,"dimensions":{'
               '"experiment":{"left":{"id":"x","version":1},'
               '"right":{"id":"x","version":2},"match":false},'
               '"plan_digest":{"left":"p1","right":"p2","match":false},'
               '"science_digest":{"left":"s1","right":"s2","match":false}},'
               '"metric":null}')
    javascript(r'''
import assert from 'node:assert/strict';
import {Element, installDOM} from '../../tests/dashboard/astra_dom.mjs';
installDOM();
''' + _mock_fetch([('evaluation/compare', compare)]) + r'''
globalThis.location = {hash: '#evaluation?left=' + 'a'.repeat(32) + '&right=' + 'b'.repeat(32)};
const {renderEvaluation} = await import('./views/evaluation.js');
const root = new Element();
await renderEvaluation(root, new AbortController().signal);
const text = root.textContent;
assert.ok(text.includes('Incompatible'), text);
assert.ok(text.includes('experiment'), 'exact differing dimensions are named');
assert.ok(text.includes('plan_digest'));
assert.ok(!/better|worse|equivalent/i.test(text), 'no automatic verdict');
''')


def test_comparison_separates_eligibility_from_identity():
    """MAJOR-2: compatible runs with different science digests show
    eligibility, scientific identity and stored results as three
    separate concepts, with no ranking language."""
    compare = ('{"left":"' + 'a' * 32 + '","right":"' + 'b' * 32 + '",'
               '"compatible":true,"eligibility":"compatible",'
               '"reasons":[],"dimensions":{'
               '"experiment":{"left":{"id":"x","version":1},'
               '"right":{"id":"x","version":1},"match":true,'
               '"status":"match"},'
               '"plan_digest":{"left":"p1","right":"p1","match":true,'
               '"status":"match"}},'
               '"plan_fields":[],'
               '"scientific_identity":{"science_digest":{"left":"s1",'
               '"right":"s2","equal":false}},'
               '"findings":{"left":[{"question":"prediction",'
               '"status":"NEGATIVE","reason":"R"}],'
               '"right":[{"question":"prediction","status":"NEGATIVE",'
               '"reason":"R"}]},'
               '"metric":{"id":"prediction.numeric-mae",'
               '"state":"paired",'
               '"identity":"member-0:prediction.numeric-mae:all:whole",'
               '"left":{"value":0.0},"right":{"value":0.5}}}')
    javascript(r'''
import assert from 'node:assert/strict';
import {Element, installDOM} from '../../tests/dashboard/astra_dom.mjs';
installDOM();
''' + _mock_fetch([('evaluation/compare', compare)]) + r'''
globalThis.location = {hash: '#evaluation?left=' + 'a'.repeat(32) + '&right=' + 'b'.repeat(32)};
const {renderEvaluation} = await import('./views/evaluation.js');
const root = new Element();
await renderEvaluation(root, new AbortController().signal);
const text = root.textContent;
assert.ok(text.includes('Compatibility'), text);
assert.ok(text.includes('Compatible for descriptive comparison'), text);
assert.ok(text.includes('Scientific identity'), text);
assert.ok(text.includes('Different results'), text);
assert.ok(text.includes('Scientific results'), text);
assert.ok(text.includes('NEGATIVE'), 'stored findings stay visible');
assert.ok(!/better|worse|equivalent/i.test(text), 'no automatic verdict');
''')


def test_evaluation_dom_and_chart_caps():
    rows = ','.join(
        '{"identity":"m%d","metric":"prediction.numeric-mae","version":1,'
        '"member":"member-0","state":"MEASURED","value":0.5,"reason":null}'
        % i for i in range(20))
    page = ('{"available":true,"items":[' + rows + '],"next_cursor":null}')
    javascript(r'''
import assert from 'node:assert/strict';
import {Element, installDOM} from '../../tests/dashboard/astra_dom.mjs';
installDOM();
''' + _mock_fetch([('measurements', page)]) + r'''
globalThis.location = {hash: '#evaluation?run=' + 'a'.repeat(32) + '&view=measurements'};
const {renderEvaluation} = await import('./views/evaluation.js');
const root = new Element();
await renderEvaluation(root, new AbortController().signal);
const elements = root.querySelectorAll('*');
assert.ok(elements.length <= 1500, 'DOM cap: ' + elements.length);
const rowsRendered = root.querySelectorAll('tr').length;
assert.ok(rowsRendered <= 21, 'table rows cap (20 + header): ' + rowsRendered);
''')


def test_escaped_hostile_artifact_strings():
    hostile = ('{"available":true,"items":[{"run_id":"' + 'a' * 32 + '",'
               '"digest":"d","science_digest":"s","status":'
               '"<img src=x onerror=alert(1)>","verification":"VERIFIED"}],'
               '"next_cursor":null}')
    javascript(r'''
import assert from 'node:assert/strict';
import {Element, installDOM} from '../../tests/dashboard/astra_dom.mjs';
installDOM();
''' + _mock_fetch([('evaluation/runs?', hostile),
                   ('evaluation/runs', hostile)]) + r'''
globalThis.location = {hash: '#evaluation'};
const {renderEvaluation} = await import('./views/evaluation.js');
const root = new Element();
await renderEvaluation(root, new AbortController().signal);
// The hostile string is text, never an element: no img node exists and
// the literal text is present verbatim.
assert.equal(root.querySelectorAll('img').length, 0);
assert.ok(root.textContent.includes('<img src=x onerror=alert(1)>'));
const source = await import('node:fs').then(fs => fs.readFileSync('./views/evaluation.js', 'utf8'));
assert.ok(!source.includes('innerHTML'), 'view must not use innerHTML');
assert.ok(!source.includes('eval('), 'view must not use eval');
''')
