// Small deterministic DOM surface for exercising real rendering helpers without packages.
export class Element {
  constructor(tag='div'){this.tagName=tag;this.children=[];this.attributes={};this.listeners={};this._text='';this.className='';this.hidden=false;this.dataset={};this.value='';this.classList={add:(...names)=>{this.className+=' '+names.join(' ');},toggle:(name,on)=>{const names=new Set(this.className.split(' '));const yes=on??!names.has(name);yes?names.add(name):names.delete(name);this.className=[...names].join(' ');return yes;},contains:name=>this.className.split(' ').includes(name)};}
  set textContent(text){this._text=String(text);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent??String(c)).join(' ');}
  append(...nodes){this.children.push(...nodes);}
  prepend(...nodes){this.children.unshift(...nodes);}
  replaceChildren(...nodes){this._text='';this.children=nodes;}
  setAttribute(key,value){this.attributes[key]=String(value);}
  getAttribute(key){return this.attributes[key]??null;}
  removeAttribute(key){delete this.attributes[key];}
  addEventListener(name,fn){this.listeners[name]=fn;}
  focus(){document.activeElement=this;}
  contains(node){return node===this||this.children.some(c=>c instanceof Element&&c.contains(node));}
  querySelectorAll(selector){const found=[];for(const child of this.children){if(!(child instanceof Element))continue;if(child.tagName===selector||selector==='*'||selector==='[aria-current=page]'&&child.attributes['aria-current']==='page')found.push(child);found.push(...child.querySelectorAll(selector));}return found;}
  querySelector(selector){return this.querySelectorAll(selector)[0]??null;}
  get hash(){return this.href?.startsWith('#')?this.href:'';}
}
export function installDOM(){
 const ids=new Map();for(const id of ['navigation','sidebar','menu','theme','page-title','breadcrumb','page-description','content','notice','connection','last-updated','refresh','main']){const el=new Element();el.id=id;ids.set(id,el);}
 const eyebrow=new Element(),skip=new Element('a'),body=new Element('body');ids.get('sidebar').append(ids.get('navigation'));
 globalThis.Node=Element;globalThis.document={title:'SEED — Local observatory',body,activeElement:body,createElement:tag=>new Element(tag),createTextNode:text=>({textContent:String(text)}),querySelector:selector=>selector==='.eyebrow'?eyebrow:selector==='.skip'?skip:ids.get(selector.slice(1))??null,addEventListener:(name,fn)=>{document[name]=fn;}};
 return {ids,eyebrow,skip,body};
}
