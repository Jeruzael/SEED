// Astra Evaluation view (B10 I28): stored B10 evidence, observer only.
//
// Execution status and scientific findings are separate concepts and
// are headed separately. Nothing here recomputes metrics, classifies
// runs as better/worse, converts unavailable values to zero, or
// invokes cognition: replay shows recorded stages only. All artifact
// strings are rendered through textContent-based helpers.
import {el, card, table, list, button} from '../api.js';
import {route, value, raw, link} from '../evidence.js';
import {fetchEvaluation, fetchEvaluationChunk, evaluationHref}
  from '../evaluation_support.js';

const cursorHistory = new Map();

function pager(params, nextCursor) {
  const base = {...params};
  delete base.cursor;
  const key = JSON.stringify(base);
  let history = cursorHistory.get(key) || [null];
  const current = params.cursor ?? null;
  const at = history.indexOf(current);
  if (current === null) history = [null];
  else if (at >= 0) history = history.slice(0, at + 1);
  else history = [...history, current].slice(-20);
  cursorHistory.set(key, history);
  const row = el('div', null, 'pagination');
  row.append(link('First page', 'evaluation', base));
  if (history.length > 1) {
    row.append(link('Previous', 'evaluation',
      {...base, cursor: history.at(-2)}));
  }
  if (nextCursor !== null && nextCursor !== undefined) {
    row.append(link('Next', 'evaluation', {...base, cursor: nextCursor}));
  }
  return row;
}

function unavailable(root, error) {
  const panel = card('Evaluation unavailable');
  panel.append(el('p',
    'Evaluation unavailable / no artifact root configured. Other '
    + 'dashboard views are unaffected.', 'notice'));
  root.replaceChildren(panel);
}

function failed(root, error) {
  const panel = card('Evaluation error');
  panel.append(el('p', error.message || 'Evaluation evidence could not '
    + 'be read.', 'notice'));
  root.replaceChildren(panel);
}

function short(text, length = 16) {
  const text2 = String(text ?? 'Unavailable');
  return text2.length > length ? text2.slice(0, length) + '…' : text2;
}

async function renderList(root, signal, params) {
  const query = new URLSearchParams({limit: '20'});
  if (params.cursor) query.set('cursor', params.cursor);
  const data = await fetchEvaluation('evaluation/runs?' + query, signal);
  const panel = card('Published evaluation runs');
  const items = data.items || [];
  if (!items.length && !params.cursor) {
    panel.append(el('p', 'No published evaluation runs.', 'empty'));
  }
  const selected = params.left;
  panel.append(table(
    ['Run', 'Execution', 'Science digest', 'Verification', 'Inspect'],
    items.map(item => {
      const inspect = link('Open', 'evaluation', {run: item.run_id});
      const cell = el('span');
      cell.append(inspect);
      if (selected && selected !== item.run_id) {
        cell.append(document.createTextNode(' · '));
        cell.append(link('Compare', 'evaluation',
          {left: selected, right: item.run_id}));
      } else if (!selected) {
        cell.append(document.createTextNode(' · '));
        cell.append(link('Select to compare', 'evaluation',
          {left: item.run_id}));
      }
      return [short(item.run_id, 12), value(item.status),
              short(item.science_digest, 12), value(item.verification),
              cell];
    }), 'Published evaluation runs'));
  panel.append(pager(params, data.next_cursor));
  root.replaceChildren(panel);
}

async function readStoredJson(runId, name, signal) {
  // Bounded chunk inspection of one receipt-verified stored file.
  let text = '';
  const decoder = new TextDecoder('utf-8', {fatal: true});
  for (let chunk = 0; chunk < 8; chunk++) {
    const data = await fetchEvaluationChunk(
      `evaluation/runs/${runId}/files/${name}?chunk=${chunk}`, signal);
    text += decoder.decode(new Uint8Array(data), {stream: chunk < 7});
    if (data.byteLength < 65536) break;
  }
  const {parseEvidence} = await import('../api.js');
  return parseEvidence(text, 1024 * 1024);
}

async function renderDetail(root, signal, params) {
  const runId = params.run;
  const detail = await fetchEvaluation('evaluation/runs/' + runId, signal);
  const execution = card('Execution');
  execution.append(list([
    ['Run', detail.run_id],
    ['Status', value(detail.status)],
    ['Reason', value(detail.reason)],
    ['Planned transitions', value(detail.counts?.planned_transitions)],
    ['Joined events', value(detail.counts?.joined_events)],
    ['Observed transitions', value(detail.counts?.observed_transitions)],
    ['Skipped attempts', value(detail.counts?.skipped_attempts)],
    ['Artifact verification', value(detail.verification)],
    ['Chunk verification', value(detail.chunk_verification)],
    ['Receipt digest', short(detail.receipt_digest, 24)],
    ['Science digest', short(detail.science_digest, 24)],
  ]));
  const findings = card('Scientific findings');
  findings.append(el('p',
    'Execution status describes run mechanics. Scientific findings are '
    + 'classified per registered question and may be unfavorable; a '
    + 'completed run does not by itself establish a positive result.',
    'subtle'));
  const rows = detail.findings || [];
  if (!rows.length) {
    findings.append(el('p', 'No stored findings for this run.', 'empty'));
  } else {
    findings.append(table(
      ['Question', 'Scientific finding', 'Reason'],
      rows.map(row => [value(row.question), value(row.status),
                       value(row.reason)]),
      'Stored scientific findings'));
  }
  const nav = el('div', null, 'button-row');
  for (const [label, view] of [['Measurements', 'measurements'],
                               ['Replay events', 'events'],
                               ['Curves', 'curve'], ['Files', 'files']]) {
    nav.append(link(label, 'evaluation', {run: runId, view}));
  }
  nav.append(link('All runs', 'evaluation', {}));
  root.replaceChildren(execution, findings, nav);
  if (params.view === 'measurements') {
    root.append(await measurementsPanel(signal, params));
  } else if (params.view === 'events') {
    root.append(await eventsPanel(signal, params));
  } else if (params.view === 'curve') {
    root.append(await curvePanel(signal, params));
  } else if (params.view === 'files') {
    root.append(await filesPanel(signal, params, detail));
  }
}

async function measurementsPanel(signal, params) {
  const query = new URLSearchParams({limit: '20'});
  if (params.cursor) query.set('cursor', params.cursor);
  const data = await fetchEvaluation(
    `evaluation/runs/${params.run}/measurements?` + query, signal);
  const panel = card('Measurements');
  panel.append(el('p',
    'Complete registered inventory, including unavailable rows. '
    + 'Unavailable is never shown as zero.', 'subtle'));
  panel.append(table(
    ['Metric', 'Version', 'State', 'Value', 'Reason'],
    (data.items || []).map(row => [
      value(row.metric), value(row.version), value(row.state),
      row.value === null || row.value === undefined
        ? 'Unavailable' : value(row.value),
      value(row.reason)]),
    'Registered measurements'));
  panel.append(pager(params, data.next_cursor));
  return panel;
}

async function eventsPanel(signal, params) {
  if (params.event) {
    const data = await fetchEvaluation(
      `evaluation/runs/${params.run}/events/${params.event}`, signal);
    const panel = card('Recorded event');
    panel.append(el('p',
      'Recorded replay only; no cognition is invoked.', 'subtle'));
    panel.append(list([
      ['Phase', data.key[0]], ['Subcase', data.key[1]],
      ['Ordinal', String(data.key[2])], ['Stage', data.key[3]],
    ]));
    panel.append(raw(data.body));
    panel.append(link('Back to events', 'evaluation',
      {run: params.run, view: 'events'}));
    return panel;
  }
  const query = new URLSearchParams({limit: '20'});
  if (params.cursor) query.set('cursor', params.cursor);
  const data = await fetchEvaluation(
    `evaluation/runs/${params.run}/events?` + query, signal);
  const panel = card('Replay events');
  panel.append(el('p',
    'Recorded stages, including skipped and unconfirmed attempts. '
    + 'Replay never invokes cognition.', 'subtle'));
  panel.append(table(
    ['Event', 'Selected action', 'Learner update', 'Inspect'],
    (data.items || []).map(item => {
      const keyText = item.key.join(':');
      const action = item.body?.preupdate?.evidence?.selected_action;
      const inspect = link('Open', 'evaluation',
        {run: params.run, view: 'events', event: keyText});
      return [keyText, value(action),
              item.body?.confirmed ? 'Confirmed' : 'Unconfirmed',
              inspect];
    }), 'Recorded replay events'));
  panel.append(pager(params, data.next_cursor));
  return panel;
}

async function curvePanel(signal, params) {
  const panel = card('Learning curve');
  panel.append(el('p',
    'Precomputed stored bins only; missing measurements are not '
    + 'interpolated.', 'subtle'));
  if (!params.series) {
    const index = await readStoredJson(params.run, 'index.json', signal);
    const names = Object.keys(index.curves || {}).sort();
    if (!names.length) {
      panel.append(el('p', 'No stored curve series.', 'empty'));
      return panel;
    }
    const items = el('ul');
    for (const name of names.slice(0, 20)) {
      const item = el('li');
      item.append(link(name, 'evaluation',
        {run: params.run, view: 'curve', series: name,
         metric: 'prediction.numeric-mae'}));
      items.append(item);
    }
    panel.append(items);
    return panel;
  }
  const query = new URLSearchParams(
    {metric: params.metric || 'prediction.numeric-mae',
     series: params.series});
  const data = await fetchEvaluation(
    `evaluation/runs/${params.run}/curve?` + query, signal);
  const points = (data.points || []).slice(0, 200);
  panel.append(table(
    ['Bin start (ordinal)', 'Stored value'],
    points.map(point => [String(point[0]),
                          point[1] === null ? 'Unavailable'
                                            : value(point[1])]),
    'Stored curve points for ' + params.series
    + ' (data alternative for the plotted series)'));
  return panel;
}

async function filesPanel(signal, params, detail) {
  const panel = card('Artifact files');
  if (!params.file) {
    const items = el('ul');
    for (const name of detail.receipt_files || []) {
      const item = el('li');
      item.append(link(name, 'evaluation',
        {run: params.run, view: 'files', file: name, chunk: '0'}));
      items.append(item);
    }
    panel.append(items);
    return panel;
  }
  const chunk = Number(params.chunk || '0');
  const data = await fetchEvaluationChunk(
    `evaluation/runs/${params.run}/files/${params.file}?chunk=${chunk}`,
    signal);
  panel.append(list([
    ['File', params.file], ['Chunk', String(chunk)],
    ['Bytes', String(data.byteLength)],
  ]));
  let preview;
  try {
    preview = new TextDecoder('utf-8', {fatal: true})
      .decode(new Uint8Array(data)).slice(0, 2000);
  } catch {
    preview = [...new Uint8Array(data).slice(0, 256)]
      .map(byte => byte.toString(16).padStart(2, '0')).join(' ');
  }
  const pre = el('pre', preview);
  panel.append(pre);
  if (data.byteLength === 65536) {
    panel.append(link('Next chunk', 'evaluation',
      {run: params.run, view: 'files', file: params.file,
       chunk: String(chunk + 1)}));
  }
  return panel;
}

async function renderCompare(root, signal, params) {
  const query = new URLSearchParams(
    {left: params.left, right: params.right});
  if (params.metric) query.set('metric', params.metric);
  const data = await fetchEvaluation('evaluation/compare?' + query, signal);
  // Compatibility: eligibility from definitions and provenance only.
  // (Responses without an eligibility field use the legacy boolean.)
  const eligibility = data.eligibility
    ?? (data.compatible ? 'compatible' : 'incompatible');
  const compat = card('Compatibility');
  if (eligibility === 'compatible') {
    compat.append(el('p',
      'Compatible for descriptive comparison of the stored results. '
      + 'Compatibility is not a scientific verdict: the UI does not '
      + 'rank the runs.'));
  } else if (eligibility === 'incompatible') {
    compat.append(el('p',
      'Incompatible for automatic comparison: the dimensions below '
      + 'differ. Side-by-side descriptive inspection only; the UI '
      + 'does not rank the runs.', 'notice'));
  } else {
    compat.append(el('p',
      'Compatibility not established from the stored evidence: the '
      + 'dimensions below could not be verified. Side-by-side '
      + 'descriptive inspection only; the UI does not rank the '
      + 'runs.', 'notice'));
  }
  const statusText = entry => {
    const status = entry.status
      ?? (entry.match ? 'match' : entry.match === false
          ? 'differs' : 'not_established');
    return status === 'match' ? 'Match'
      : status === 'differs' ? 'Differs' : 'Not established';
  };
  const dimensions = data.dimensions || {};
  compat.append(table(
    ['Dimension', 'Left', 'Right', 'Status'],
    Object.entries(dimensions).map(([name, entry]) => [
      name,
      entry.left !== null && typeof entry.left === 'object'
        ? short(JSON.stringify(entry.left), 24) : value(entry.left),
      entry.right !== null && typeof entry.right === 'object'
        ? short(JSON.stringify(entry.right), 24) : value(entry.right),
      statusText(entry)]),
    'Comparison compatibility dimensions'));
  if ((data.plan_fields || []).length) {
    compat.append(el('p',
      'Differing frozen-plan fields: ' + data.plan_fields.join(', '),
      'subtle'));
  }
  // Scientific identity: provenance only, never an eligibility rule.
  const identity = card('Scientific identity');
  const digest = data.scientific_identity?.science_digest || {};
  identity.append(list([
    ['Left science digest', short(digest.left, 24)],
    ['Right science digest', short(digest.right, 24)],
    ['Scientific identity', digest.equal === null
      || digest.equal === undefined ? 'Not established'
      : digest.equal ? 'Equal' : 'Different results'],
  ]));
  identity.append(el('p',
    'Science digests identify the recorded scientific content. '
    + 'Different results are expected between comparable runs and '
    + 'do not by themselves make runs incompatible.', 'subtle'));
  // Scientific results: stored values and findings, never ranked.
  const results = card('Scientific results');
  if (data.metric) {
    const metric = data.metric;
    if (metric.state === 'paired') {
      results.append(raw({metric: metric.id,
                          identity: metric.identity,
                          left: metric.left, right: metric.right}));
    } else if (metric.state === 'ambiguous') {
      results.append(el('p',
        'Metric ' + metric.id + ' has more than one registered '
        + 'measurement per run, so no single value is selected: '
        + [...(metric.candidates?.left || []),
           ...(metric.candidates?.right || [])]
            .filter((v, i, a) => a.indexOf(v) === i).join(', '),
        'notice'));
    } else if (metric.state === 'unavailable') {
      results.append(el('p',
        'Metric ' + metric.id + ' is unavailable for: '
        + (metric.missing || []).join(', ') + '. Unavailable values '
        + 'are never shown as zero.', 'notice'));
    } else {
      results.append(el('p',
        'Metric ' + metric.id + ' could not be paired across the '
        + 'runs (' + metric.state.replaceAll('_', ' ') + '), so no '
        + 'values are presented as a comparison.', 'notice'));
    }
  }
  for (const side of ['left', 'right']) {
    const rows = data.findings?.[side] || [];
    if (rows.length) {
      results.append(table(
        ['Question', 'Scientific finding', 'Reason'],
        rows.map(row => [value(row.question), value(row.status),
                         value(row.reason)]),
        'Stored scientific findings (' + side + ' run)'));
    }
  }
  root.replaceChildren(compat, identity, results);
}

export async function renderEvaluation(root, signal) {
  const {params} = route();
  try {
    if (params.left && params.right) {
      await renderCompare(root, signal, params);
    } else if (params.run) {
      await renderDetail(root, signal, params);
    } else {
      await renderList(root, signal, params);
    }
  } catch (error) {
    if (error.name === 'AbortError' || signal.aborted) throw error;
    if (error.code === 'evaluation_unavailable' || error.status === 503) {
      unavailable(root, error);
    } else {
      failed(root, error);
    }
  }
  return () => {};
}
