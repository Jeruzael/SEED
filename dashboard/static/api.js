export const api = {
  token: null,
  async get(path, signal) {
    const response = await fetch('/api/' + path, {signal, credentials:'same-origin'});
    const data = await response.json();
    if (!response.ok) {const error=new Error(data.error?.message || 'Local service unavailable');error.status=response.status;error.code=data.error?.code;throw error;}
    return data;
  },
  async mutate(path, method, body) {
    const response = await fetch('/api/' + path, {method, credentials:'same-origin',headers:{'Content-Type':'application/json','X-SEED-CSRF':this.token},body:JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || 'Operation failed');
    return data;
  }
};
// Cache success, but allow a later explicit navigation/Refresh after failure.
let bootstrapPromise;
api.bootstrap=function(){
  if(!bootstrapPromise){
    api.token=null;
    bootstrapPromise=Promise.resolve().then(()=>api.get('bootstrap')).then(data=>{
      api.token=data.token;return data;
    }).catch(error=>{bootstrapPromise=undefined;api.token=null;throw error;});
  }
  return bootstrapPromise;
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
export function table(headers,rows,caption='Recorded data'){const wrap=el('div',null,'table-wrap'), t=el('table'),head=el('thead'),tr=el('tr'),body=el('tbody');for(const h of headers){const th=el('th',h);th.setAttribute('scope','col');tr.append(th);}head.append(tr);for(const row of rows){const r=el('tr');for(const value of row){const cell=el('td');cell.append(value instanceof Node?value:document.createTextNode(value??'—'));r.append(cell);}body.append(r);}t.append(el('caption',caption),head,body);wrap.append(t);wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',caption+'; scroll horizontally for all fields');return wrap;}
export function field(label,type='text',value=''){const l=el('label',label),input=el('input');input.type=type;input.value=value;l.append(input);return [l,input];}
export function select(label,options){const l=el('label',label),input=el('select');for(const [value,text] of options){const o=el('option',text);o.value=value;input.append(o);}l.append(input);return [l,input];}
export function empty(root,message){root.append(el('p',message,'empty'));}

// Tokenize outside strings before JSON.parse so signed64 identifiers never round.
export function parseEvidence(text, maxBytes) {
  const encoder=new TextEncoder();
  if(encoder.encode(text).length>maxBytes)throw new Error('Evidence byte limit exceeded');
  let output='',i=0;
  while(i<text.length){
    const start=i,c=text[i];
    if(c==='"'){
      i++;
      while(i<text.length){if(text[i]==='\\'){i+=2;continue;}if(text[i++]==='"')break;}
      output+=text.slice(start,i);
    } else if(c==='-'||(c>='0'&&c<='9')){
      while(i<text.length&&/[0-9eE+.-]/.test(text[i]))i++;
      const token=text.slice(start,i);
      if(!/^-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?$/.test(token))throw new Error('Invalid evidence number');
      if(!token.includes('.')&&!/[eE]/.test(token)){
        const exact=BigInt(token);
        output+=exact>BigInt(Number.MAX_SAFE_INTEGER)||exact<BigInt(Number.MIN_SAFE_INTEGER)?JSON.stringify(exact.toString()):token;
      }else output+=token;
    }else{output+=c;i++;}
  }
  if(encoder.encode(output).length>2*maxBytes)throw new Error('Evidence byte limit exceeded');
  const data=JSON.parse(output);
  function check(value,depth=0){
    if(depth>32)throw new Error('Invalid evidence nesting');
    if(typeof value==='number'&&!Number.isFinite(value))throw new Error('Invalid evidence number');
    if(typeof value==='string'){
      for(let j=0;j<value.length;j++){
        const code=value.charCodeAt(j);
        if(code>=0xd800&&code<=0xdbff){const next=value.charCodeAt(++j);if(!(next>=0xdc00&&next<=0xdfff))throw new Error('Invalid Unicode evidence');}
        else if(code>=0xdc00&&code<=0xdfff)throw new Error('Invalid Unicode evidence');
      }
    }else if(value&&typeof value==='object')for(const [key,child] of Object.entries(value)){check(key,depth+1);check(child,depth+1);}
  }
  check(data);return data;
}

export function evidenceLimit(path){
  const route=path.split('?')[0];
  if(route==='development')return 98304;
  if(route==='self-model')return 40960;
  if(/^memories\/[1-9][0-9]{0,18}$/.test(route))return 32768;
  if(route==='predictions')return 27648;
  if(/^predictions\/[1-9][0-9]{0,18}$/.test(route))return 35840;
  if(route==='decisions')return 53248;
  if(/^decisions\/[1-9][0-9]{0,18}$/.test(route))return 17408;
  if(route==='curiosity/summary')return 16384;
  if(/^semantic-memories\/[1-9][0-9]{0,18}\/history$/.test(route))return 3485696;
  if(/^(world-beliefs|curiosity|semantic-memories|consolidation-runs)$/.test(route))return 1847296;
  if(/^(world-beliefs|curiosity|semantic-memories)\/[1-9][0-9]{0,18}$/.test(route))return 20480;
  throw new Error('Invalid evidence path');
}

api.getEvidence=async function(path,signal,maxBytes=evidenceLimit(path)){
  maxBytes=Math.min(maxBytes,evidenceLimit(path));
  const controller=new AbortController();
  const cancel=()=>controller.abort();
  if(signal?.aborted)controller.abort();else signal?.addEventListener('abort',cancel,{once:true});
  let timedOut=false;
  const timer=setTimeout(()=>{timedOut=true;controller.abort();},10000);
  let reader;
  try{
    const response=await fetch('/api/'+path,{signal:controller.signal,credentials:'same-origin'});
    const limit=response.ok?maxBytes:1024;
    if(Number(response.headers.get('Content-Length'))>limit){await response.body?.cancel();throw new Error('Evidence byte limit exceeded');}
    reader=response.body?.getReader();if(!reader)throw new Error('Missing evidence response');
    const decoder=new TextDecoder('utf-8',{fatal:true});let total=0,text='';
    for(;;){const {value,done}=await reader.read();if(done)break;total+=value.byteLength;if(total>limit){await reader.cancel();throw new Error('Evidence byte limit exceeded');}text+=decoder.decode(value,{stream:true});}
    text+=decoder.decode();
    const data=parseEvidence(text,limit);
    if(!response.ok){const error=new Error(data.error?.message||'Stored evidence unavailable');error.status=response.status;error.code=data.error?.code;throw error;}
    return data;
  }catch(error){if(timedOut){const timeout=new Error('Read timed out after 10 seconds. Retry when ready.');timeout.code='read_timeout';throw timeout;}throw error;}
  finally{reader?.releaseLock();clearTimeout(timer);signal?.removeEventListener('abort',cancel);}
};
