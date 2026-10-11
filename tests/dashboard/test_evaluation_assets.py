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
// Scientific identifiers stay exact strings, never coerced numbers.
const big = parseEvaluationRoute('#evaluation?run=' + 'a'.repeat(32) + '&event=measured:default:9223372036854775807:update');
assert.equal(big.invalid, undefined);
assert.equal(big.params.event, 'measured:default:9223372036854775807:update');
const aboveSafe = parseEvaluationRoute('#evaluation?run=' + 'a'.repeat(32) + '&event=measured:default:9007199254740993:update');
assert.equal(aboveSafe.invalid, undefined);
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
  '#evaluation?left=' + 'a'.repeat(32),                // compare needs both
  '#evaluation?event=measured:default:9223372036854775808:update', // > int64
  '#evaluation?event=measured:default:01:update',      // leading zero
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
