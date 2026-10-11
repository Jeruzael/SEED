// Bounded Astra Evaluation client and strict route parsing (B10 I27).
//
// The Evaluation client is deliberately separate from the general
// evidence client: a 2-second deadline, a 1 MiB streamed response cap,
// a 1,024-byte error cap, fatal UTF-8 decoding and lossless signed-64
// parsing via parseEvidence. No polling, no caching, no mutation.
import {parseEvidence} from './api.js';

export const EVALUATION_TIMEOUT_MS = 2000;
export const EVALUATION_MAX_BYTES = 1024 * 1024;
export const EVALUATION_ERROR_MAX_BYTES = 1024;
export const EVALUATION_CHUNK_MAX_BYTES = 64 * 1024;

const RUN_ID = /^[0-9a-f]{32}$/;
const NAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/;
const TOKEN = /^[A-Za-z0-9_-]{1,64}$/;
const CURSOR = /^[A-Za-z0-9_=-]+$/;
const DIGITS = /^[0-9]{1,10}$/;
const VIEWS = ['runs', 'measurements', 'events', 'curve', 'compare', 'files'];

export function parseEvaluationRoute(hash) {
  const raw = String(hash).replace(/^#/, '');
  const [page, query = '', ...extra] = raw.split('?');
  if (page !== 'evaluation' || extra.length) return {params: {}, invalid: true};
  try {
    if (new TextEncoder().encode(hash).length > 2048) throw Error();
    const params = {}, search = new URLSearchParams(query);
    for (const [key, value] of search) {
      if (Object.hasOwn(params, key)) throw Error();
      params[key] = value;
    }
    const allowed = ['run', 'cursor', 'metric', 'series', 'left', 'right',
                     'file', 'chunk', 'event', 'view'];
    for (const [key, value] of Object.entries(params)) {
      if (!allowed.includes(key)) throw Error();
      if (key === 'run' || key === 'left' || key === 'right') {
        if (!RUN_ID.test(value)) throw Error();
      } else if (key === 'cursor') {
        if (new TextEncoder().encode(value).length > 512 || !CURSOR.test(value)) throw Error();
      } else if (key === 'metric' || key === 'series' || key === 'file') {
        if (!NAME.test(value)) throw Error();
      } else if (key === 'chunk') {
        if (!DIGITS.test(value)) throw Error();
      } else if (key === 'view') {
        if (!VIEWS.includes(value)) throw Error();
      } else if (key === 'event') {
        const parts = value.split(':');
        if (parts.length !== 4) throw Error();
        const [phase, subcase, ordinal, stage] = parts;
        if (!TOKEN.test(phase) || !TOKEN.test(subcase) || !TOKEN.test(stage)) throw Error();
        // The ordinal is an exact signed-64 decimal string; it is
        // validated as text and never coerced to a JS number.
        if (!/^(0|[1-9][0-9]{0,18})$/.test(ordinal)
            || BigInt(ordinal) > 2n ** 63n - 1n) throw Error();
      }
    }
    // 'left' alone is compare-selection state; 'right' requires 'left'.
    if (params.right !== undefined && params.left === undefined) throw Error();
    return {params};
  } catch { return {params: {}, invalid: true}; }
}

export function evaluationHref(params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null));
  return '#evaluation' + (query.size ? '?' + query : '');
}

async function readBounded(response, limit) {
  if (Number(response.headers.get('Content-Length')) > limit) {
    await response.body?.cancel();
    throw new Error('Evaluation response byte limit exceeded');
  }
  const reader = response.body?.getReader();
  if (!reader) throw new Error('Missing evaluation response');
  const decoder = new TextDecoder('utf-8', {fatal: true});
  let total = 0, text = '';
  try {
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > limit) {
        await reader.cancel();
        throw new Error('Evaluation response byte limit exceeded');
      }
      text += decoder.decode(value, {stream: true});
    }
    text += decoder.decode();
    return text;
  } finally { reader.releaseLock(); }
}

export async function fetchEvaluation(path, signal, options = {}) {
  const timeoutMs = options.timeoutMs ?? EVALUATION_TIMEOUT_MS;
  const maxBytes = options.maxBytes ?? EVALUATION_MAX_BYTES;
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (signal?.aborted) controller.abort();
  else signal?.addEventListener('abort', cancel, {once: true});
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    const response = await fetch('/api/' + path,
      {signal: controller.signal, credentials: 'same-origin'});
    const limit = response.ok ? maxBytes : EVALUATION_ERROR_MAX_BYTES;
    let text;
    try {
      text = await readBounded(response, limit);
    } catch (readError) {
      if (!response.ok) {
        // An oversized error body is never parsed; surface a bounded
        // generic error with the status preserved.
        const error = new Error('Evaluation error response too large');
        error.status = response.status;
        throw error;
      }
      throw readError;
    }
    const data = parseEvidence(text, limit);
    if (!response.ok) {
      const error = new Error(
        String(data.error?.message || 'Evaluation unavailable').slice(0, 1024));
      error.status = response.status;
      error.code = data.error?.code;
      throw error;
    }
    return data;
  } catch (error) {
    if (timedOut) {
      const timeout = new Error(
        `Evaluation read timed out after ${timeoutMs} ms. Retry when ready.`);
      timeout.code = 'read_timeout';
      throw timeout;
    }
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}

export async function fetchEvaluationChunk(path, signal, options = {}) {
  const timeoutMs = options.timeoutMs ?? EVALUATION_TIMEOUT_MS;
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (signal?.aborted) controller.abort();
  else signal?.addEventListener('abort', cancel, {once: true});
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    const response = await fetch('/api/' + path,
      {signal: controller.signal, credentials: 'same-origin'});
    if (!response.ok) throw new Error('Artifact chunk unavailable');
    if (Number(response.headers.get('Content-Length')) > EVALUATION_CHUNK_MAX_BYTES) {
      await response.body?.cancel();
      throw new Error('Evaluation chunk byte limit exceeded');
    }
    const data = await response.arrayBuffer();
    if (data.byteLength > EVALUATION_CHUNK_MAX_BYTES) {
      throw new Error('Evaluation chunk byte limit exceeded');
    }
    return data;
  } catch (error) {
    if (timedOut) {
      const timeout = new Error(
        `Evaluation read timed out after ${timeoutMs} ms. Retry when ready.`);
      timeout.code = 'read_timeout';
      throw timeout;
    }
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}
