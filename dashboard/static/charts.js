import {el,date,table,details} from './api.js';
export function renderChart(root,samples,{label,unit=''}){
  const valid=samples.filter(s=>Number.isFinite(s.value));
  if(valid.length<2){root.append(el('p','At least two recorded samples are needed for this chart.','subtle'));return;}
  const min=Math.min(...valid.map(s=>s.value)),max=Math.max(...valid.map(s=>s.value)),span=max-min||1;
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 600 140');svg.setAttribute('role','img');svg.setAttribute('aria-label',`${label}: ${valid.length} samples, ${min}–${max} ${unit}`);svg.classList.add('chart');
  const line=document.createElementNS(ns,'line');for(const [a,v]of Object.entries({x1:0,x2:600,y1:130,y2:130}))line.setAttribute(a,v);svg.append(line);
  const curve=document.createElementNS(ns,'polyline');curve.setAttribute('points',valid.map((s,i)=>`${i/(valid.length-1)*596+2},${125-(s.value-min)/span*110}`).join(' '));svg.append(curve);root.append(svg,el('small',`${date(valid[0].ts)} → ${date(valid.at(-1).ts)} · ${min}–${max} ${unit}`));
  const d=el('details');d.append(el('summary','Accessible sample table'),table(['Time',label],valid.map(s=>[date(s.ts),`${s.value} ${unit}`])));root.append(d);
}
