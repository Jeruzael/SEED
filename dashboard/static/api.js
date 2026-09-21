export const api = {
  token: null,
  async get(path, signal) {
    const response = await fetch('/api/' + path, {signal, credentials:'same-origin'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || 'Local service unavailable');
    return data;
  },
  async mutate(path, method, body) {
    const response = await fetch('/api/' + path, {method, credentials:'same-origin',headers:{'Content-Type':'application/json','X-SEED-CSRF':this.token},body:JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || 'Operation failed');
    return data;
  }
};
export function el(tag, value, className='') {const n=document.createElement(tag);if(value!==undefined&&value!==null)n.textContent=String(value);n.className=className;return n;}
export const date = value => typeof value==='number' ? new Date(value*1000).toLocaleString() : 'Unavailable';
export const num = value => typeof value==='number' ? value.toLocaleString() : '—';
export function duration(value){if(typeof value!=='number')return 'Unavailable';if(value<60)return `${Math.floor(value)}s`;if(value<3600)return `${Math.floor(value/60)}m`;if(value<86400)return `${(value/3600).toFixed(1)}h`;return `${Math.floor(value/86400)} days`;}
export function bytes(n){if(typeof n!=='number')return '—';for(const u of ['B','KiB','MiB','GiB']){if(n<1024||u==='GiB')return `${n.toFixed(u==='B'?0:1)} ${u}`;n/=1024;}}
export function card(title){const n=el('section',null,'card');if(title)n.append(el('h2',title));return n;}
export function details(title,data){const n=el('details');n.append(el('summary',title),el('pre',JSON.stringify(data,null,2)));return n;}
export function list(pairs){const n=el('dl',null,'data-list');for(const [a,b] of pairs)n.append(el('dt',a),el('dd',b??'Unavailable','mono'));return n;}
export function metric(label,value,hint){const n=card();n.classList.add('metric');n.append(el('div',label,'section-label'),el('div',value,'value'),el('small',hint));return n;}
export function button(label,fn,primary=false){const n=el('button',label,primary?'primary':'');n.type='button';n.addEventListener('click',async()=>{try{n.disabled=true;await fn();}catch(e){showError(e.message);}finally{n.disabled=false;}});return n;}
export function showError(message){const n=document.querySelector('#notice');n.hidden=false;n.textContent=message;}
export function table(headers,rows){const wrap=el('div',null,'table-wrap'), t=el('table'),head=el('thead'),tr=el('tr'),body=el('tbody');for(const h of headers)tr.append(el('th',h));head.append(tr);for(const row of rows){const r=el('tr');for(const value of row){const cell=el('td');cell.append(value instanceof Node?value:document.createTextNode(value??'—'));r.append(cell);}body.append(r);}t.append(head,body);wrap.append(t);return wrap;}
export function field(label,type='text',value=''){const l=el('label',label),input=el('input');input.type=type;input.value=value;l.append(input);return [l,input];}
export function select(label,options){const l=el('label',label),input=el('select');for(const [value,text] of options){const o=el('option',text);o.value=value;input.append(o);}l.append(input);return [l,input];}
export function empty(root,message){root.append(el('p',message,'empty'));}
