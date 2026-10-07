import React, {useEffect, useRef, useState} from 'react';
import {ArrowDown, ArrowUp, Plus, Save, Trash2, Upload, SlidersHorizontal, Building2} from 'lucide-react';

const API=import.meta.env.VITE_API_URL || '/api/v1';
const categories=['Cleaning','Transformation','Validation'];
const empty=()=>({name:'',key:'',serviceType:'SM',senderEmail:'',retailerEmail:'',stores:[],pipeline:[],sectionOrder:[...categories]});
const input='w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-400';
const button='inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed';
const primary=button+' bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400 border-cyan-500';
const card='rounded-xl border border-slate-700 bg-[#1e293b] p-5 space-y-4';
const operations={Cleaning:{trim:'Trim whitespace',uppercase:'Uppercase text',lowercase:'Lowercase text',replace:'Replace text'},Transformation:{numeric:'Convert to number',date:'Standardise date',rename:'Rename column'},Validation:{required:'Required value',range:'Numeric range',pattern:'Text pattern',unique:'Unique values'}};
async function api(path,options={}) {
 const response=await fetch(`${API}${path}`,options);
 const data=await response.json();
 if(!response.ok || !data.success) throw new Error(data.error || 'Request failed.');
 return data;
}
const json=body=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function Field({label,children}) {return <label className="block space-y-1.5 text-sm text-slate-300"><span>{label}</span>{children}</label>;}
function Rows({title,rows=[]}) {
 const fields=[...new Set(rows.flatMap(r=>Object.keys(r)))];
 return <div className="space-y-2 min-w-0"><h4 className="font-medium text-sm text-slate-200">{title}</h4><div className="overflow-auto max-h-80 rounded-lg border border-slate-700"><table className="w-full text-left text-xs"><thead className="bg-slate-900 sticky top-0"><tr><th className="p-2">#</th>{fields.map(f=><th className="p-2 whitespace-nowrap" key={f}>{f}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i} className="border-t border-slate-700"><td className="p-2 text-slate-500">{i+1}</td>{fields.map(f=><td key={f} className="p-2 whitespace-pre-wrap min-w-24">{String(r[f]??'')}</td>)}</tr>)}</tbody></table>{!rows.length&&<p className="p-3 text-sm text-slate-400">No sample rows.</p>}</div></div>;
}
function Issues({issues=[]}) {
 return issues.length ? <div className="overflow-auto max-h-48"><table className="w-full text-xs text-left"><thead><tr><th className="p-2">Row</th><th className="p-2">Field</th><th className="p-2">Detection</th></tr></thead><tbody>{issues.slice(0,100).map((i,n)=><tr key={n} className="border-t border-slate-700 text-amber-300"><td className="p-2">{i.row}</td><td className="p-2">{i.field}</td><td className="p-2">{i.issue}</td></tr>)}</tbody></table>{issues.length>100&&<p className="text-xs">Showing the first 100 of {issues.length} detections.</p>}</div> : <p className="text-xs text-emerald-300">No issues detected by these rules.</p>;
}
function StepPreview({step}) {
 if(!step) return <p className="text-sm text-slate-400">Upload a sample and complete the rule settings to see this preview.</p>;
 return <div className="space-y-3"><div className="grid grid-cols-1 xl:grid-cols-2 gap-3"><Rows title="Before" rows={step.before}/><Rows title="After" rows={step.after}/></div><Issues issues={step.issues}/></div>;
}
function RuleSettings({rule,onChange,fields}) {
 const update=(key,value)=>onChange({...rule,[key]:value});
 return <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
  <Field label="Field"><input aria-label={`Field for ${rule.name}`} list={`fields-${rule.id}`} className={input} value={rule.field||''} onChange={e=>update('field',e.target.value)}/><datalist id={`fields-${rule.id}`}>{fields.map(f=><option key={f} value={f}/>)}</datalist></Field>
  {rule.operation==='rename'&&<Field label="New column name"><input className={input} value={rule.target||''} onChange={e=>update('target',e.target.value)}/></Field>}
  {rule.operation==='replace'&&<><Field label="Find text"><input className={input} value={rule.find||''} onChange={e=>update('find',e.target.value)}/></Field><Field label="Replace with"><input className={input} value={rule.replacement||''} onChange={e=>update('replacement',e.target.value)}/></Field></>}
  {rule.operation==='date'&&<Field label="Input date format"><input className={input} value={rule.dateFormat||''} placeholder="%d/%m/%Y" onChange={e=>update('dateFormat',e.target.value)}/><span className="text-xs text-slate-400">Example: %d/%m/%Y converts 07/10/2026 to 2026-10-07.</span></Field>}
  {rule.operation==='range'&&<><Field label="Minimum"><input type="number" step="any" className={input} value={rule.min??''} onChange={e=>update('min',e.target.value)}/></Field><Field label="Maximum"><input type="number" step="any" className={input} value={rule.max??''} onChange={e=>update('max',e.target.value)}/></Field></>}
  {rule.operation==='pattern'&&<Field label="Text pattern"><input className={input} value={rule.pattern||''} placeholder="SKU-*" onChange={e=>update('pattern',e.target.value)}/><span className="text-xs text-slate-400">* matches any text; ? matches one character. All other characters match literally.</span></Field>}
 </div>;
}
export default function RetailerSetup() {
 const [retailers,setRetailers]=useState([]),[catalog,setCatalog]=useState([]),[config,setConfig]=useState(empty),[view,setView]=useState('setup');
 const [sample,setSample]=useState(null),[previewState,setPreviewState]=useState(null),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [busy,setBusy]=useState(false),[previewBusy,setPreviewBusy]=useState(false),[dirty,setDirty]=useState(false),[newRule,setNewRule]=useState(null);
 const sampleRequest=useRef(0);
 const order=config.sectionOrder||categories;
 const pipeline=order.flatMap(category=>config.pipeline.filter(r=>r.category===category));
 const signature=JSON.stringify({id:config.id,sample:sample,pipeline});
 const preview=previewState?.signature===signature?previewState.data:null;
 const fields=[...new Set([...(sample?.columns||[]),...pipeline.filter(r=>r.operation==='rename').map(r=>r.target).filter(Boolean)])];
 const change=patch=>{setConfig(c=>({...c,...patch}));setDirty(true);setNotice('');};
 const loadSample=async(id)=>{const serial=++sampleRequest.current;setSample(null);setPreviewState(null);if(!id)return;try{const data=await api(`/retailers/${id}/sample`);if(serial===sampleRequest.current)setSample(data.sample);}catch(e){if(serial===sampleRequest.current)setError(e.message);}};
 useEffect(()=>{let alive=true;Promise.all([api('/retailers'),api('/rule-definitions')]).then(([a,b])=>{if(!alive)return;setRetailers(a.retailers);setCatalog(b.rules);if(a.retailers.length){setConfig(a.retailers[0]);loadSample(a.retailers[0].id);}}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[]);
 useEffect(()=>{
  if(!config.id||!sample){setPreviewBusy(false);return;}
  const controller=new AbortController();setPreviewBusy(true);
  const timer=setTimeout(()=>{api(`/retailers/${config.id}/preview`,{...json({pipeline}),signal:controller.signal}).then(data=>{setPreviewState({signature,data});setError('');}).catch(e=>{if(e.name!=='AbortError'){setPreviewState(null);setError(e.message);}}).finally(()=>{if(!controller.signal.aborted)setPreviewBusy(false);});},350);
  return()=>{clearTimeout(timer);controller.abort();};
 },[signature]);
 async function save() {
  setBusy(true);setError('');
  try {
   const data=await api(config.id?`/retailers/${config.id}`:'/retailers',{...json({...config,pipeline}),method:config.id?'PUT':'POST'});
   setConfig(data.retailer);setRetailers(list=>[...list.filter(r=>r.id!==data.retailer.id),data.retailer]);setDirty(false);setNotice('Retailer setup and ordered rules saved.');return data.retailer;
  }catch(e){setError(e.message);return null;}finally{setBusy(false);}
 }
 function selectRetailer(id) {
  if(dirty && !window.confirm('Discard unsaved changes and switch retailer?'))return;
  setConfig(retailers.find(r=>r.id===id)||empty());setDirty(false);setError('');setNotice('');setView('setup');setNewRule(null);loadSample(id);
 }
 async function upload(file) {
  if(!file)return;
  if(file.size>=1000000){setError('Sample must be smaller than 1 MB (1,000,000 bytes).');return;}
  let retailer=config;if(!config.id||dirty){retailer=await save();if(!retailer)return;}
  setBusy(true);setError('');
  const data=new FormData();data.append('file',file);
  try{const result=await api(`/retailers/${retailer.id}/sample`,{method:'POST',body:data});setSample(result.sample);setNotice('Sample uploaded. Previews use all sample rows and display up to 25.');}catch(e){setError(e.message);}finally{setBusy(false);}
 }
 function addRule(id,category) {
  if(id==='new'){setNewRule({category,operation:Object.keys(operations[category])[0],name:'',field:fields[0]||'',id:'new'});return;}
  const def=catalog.find(r=>r.id===id);if(!def)return;
  change({pipeline:[...config.pipeline,{id:crypto.randomUUID(),name:def.name,category:def.category,operation:def.operation,field:fields[0]||'',dateFormat:'%d/%m/%Y',...def.defaults}]});
 }
 function updateRule(rule){change({pipeline:config.pipeline.map(r=>r.id===rule.id?rule:r)});}
 function moveRule(rule,direction) {
  const group=config.pipeline.filter(r=>r.category===rule.category);const index=group.findIndex(r=>r.id===rule.id);const target=index+direction;
  if(target<0||target>=group.length)return;[group[index],group[target]]=[group[target],group[index]];
  change({pipeline:order.flatMap(category=>category===rule.category?group:config.pipeline.filter(r=>r.category===category))});
 }
 function moveSection(index,direction) {
  const list=[...order];const target=index+direction;if(target<0||target>=list.length)return;
  [list[index],list[target]]=[list[target],list[index]];change({sectionOrder:list});
 }
 async function createRule() {
  setBusy(true);setError('');
  try {
   const {name,operation,category,...defaults}=newRule;
   const data=await api('/rule-definitions',json({name,operation,category,defaults}));
   setCatalog(list=>[...list,data.rule]);change({pipeline:[...config.pipeline,{...data.rule.defaults,id:crypto.randomUUID(),name:data.rule.name,operation:data.rule.operation,category:data.rule.category}]});setNewRule(null);
  }catch(e){setError(e.message);}finally{setBusy(false);}
 }
 async function downloadExample() {
  setBusy(true);setError('');
  try {const response=await fetch(`${API}/retailers/${config.id}/example.csv`,json({pipeline}));if(!response.ok)throw new Error((await response.json()).error);const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=`${config.key}_final_example.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){setError(e.message);}finally{setBusy(false);}
 }
 return <div className="space-y-6" data-testid="retailer-setup">
  <div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-2xl font-bold flex items-center gap-2"><Building2 className="text-cyan-400"/>Retailer Data Setup</h2><p className="text-sm text-slate-400 mt-2">Set up retailer details, store records and an ordered data configuration.</p></div><div className="flex gap-2"><button disabled={busy} className={button} onClick={()=>selectRetailer('')}><Plus size={16}/>New Retailer</button><button disabled={busy} className={primary} onClick={save}><Save size={16}/>{busy?'Working…':'Save Configuration'}</button></div></div>
  <div className="flex flex-wrap items-center gap-3"><label className="text-sm">Retailer<select aria-label="Select retailer" className={input+' mt-1 min-w-64'} value={config.id||''} disabled={busy} onChange={e=>selectRetailer(e.target.value)}><option value="">New retailer</option>{retailers.map(r=><option key={r.id} value={r.id}>{r.name} · {r.key}</option>)}</select></label><span className="text-xs text-slate-400">{dirty?'Unsaved changes':config.id?'Saved configuration':'New configuration'}</span></div>
  <div className="flex gap-2 border-b border-slate-700 pb-3"><button className={view==='setup'?primary:button} onClick={()=>setView('setup')}>Retailer Details</button><button className={view==='rules'?primary:button} onClick={()=>setView('rules')}><SlidersHorizontal size={16}/>Rules Configure</button></div>
  {error&&<div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-rose-200 text-sm">{error}</div>}
  {notice&&<div role="status" className="text-emerald-300 text-sm">{notice}</div>}
  {view==='setup'&&<>
   <section className={card}><h3 className="font-semibold">Retailer Information</h3><div className="grid md:grid-cols-2 gap-4">
    <Field label="Retailer Name *"><input className={input} required maxLength={120} value={config.name} onChange={e=>change({name:e.target.value})}/></Field>
    <Field label="Retailer Key *"><input className={input} required maxLength={64} placeholder="RETAILER_001" value={config.key} onChange={e=>change({key:e.target.value})}/><span className="text-xs text-slate-400">Unique key using letters, numbers, underscores or hyphens.</span></Field>
    <Field label="Service Type *"><select className={input} value={config.serviceType} onChange={e=>change({serviceType:e.target.value})}><option value="SM">SM — Supermarket</option><option value="HM">HM — Hypermarket</option><option value="MM">MM — Minimarket</option></select></Field>
    <Field label="Sender Email (internal) *"><input type="email" className={input} required value={config.senderEmail} onChange={e=>change({senderEmail:e.target.value})}/></Field>
    <Field label="Retailer Email (optional)"><input type="email" className={input} value={config.retailerEmail} onChange={e=>change({retailerEmail:e.target.value})}/><span className="text-xs text-slate-400">Contact for late data delivery alerts when enabled.</span></Field>
   </div></section>
   <section className={card}><div className="flex items-center justify-between"><h3 className="font-semibold">Store Table Management</h3><button className={button} onClick={()=>change({stores:[...config.stores,{key:'',name:''}]})}><Plus size={16}/>Add Store</button></div><div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-slate-400"><tr><th className="p-2">Store Key</th><th className="p-2">Store Name</th><th className="p-2">Actions</th></tr></thead><tbody>{config.stores.map((store,i)=><tr key={i}><td className="p-2"><input aria-label={`Store key ${i+1}`} className={input} value={store.key} onChange={e=>change({stores:config.stores.map((s,n)=>n===i?{...s,key:e.target.value}:s)})}/></td><td className="p-2"><input aria-label={`Store name ${i+1}`} className={input} value={store.name} onChange={e=>change({stores:config.stores.map((s,n)=>n===i?{...s,name:e.target.value}:s)})}/></td><td className="p-2"><button aria-label={`Remove store ${i+1}`} className={button} onClick={()=>change({stores:config.stores.filter((_,n)=>n!==i)})}><Trash2 size={16}/></button></td></tr>)}</tbody></table>{!config.stores.length&&<p className="text-sm text-slate-400 py-4">No stores yet. Add store keys and names for this retailer.</p>}</div></section>
   <div className="flex justify-end"><button className={primary} onClick={()=>setView('rules')}><SlidersHorizontal size={16}/>Rules Configure →</button></div>
  </>}
  <section className={card}><div className="flex flex-wrap justify-between gap-3"><div><h3 className="font-semibold">Upload Sample Data</h3><p className="text-sm text-slate-400 mt-1">CSV, Excel (.xlsx) or JSON · smaller than 1 MB · sample is saved per retailer.</p></div><label className={button+' cursor-pointer'}><Upload size={16}/>Choose Sample<input aria-label="Upload sample data" type="file" accept=".csv,.xlsx,.json" className="hidden" disabled={busy} onChange={e=>{upload(e.target.files[0]);e.target.value='';}}/></label></div>{sample?<><p className="text-sm text-cyan-300">{sample.filename} · {sample.totalRows} rows · {sample.byteSize.toLocaleString()} bytes</p><details><summary className="cursor-pointer text-sm text-slate-300">Preview original sample</summary><div className="pt-3"><Rows title="Original sample (first 25 rows)" rows={sample.rows}/></div></details></>:<p className="text-sm text-slate-400">Complete the required retailer details, then upload a sample to preview rules.</p>}</section>
  {view==='rules'&&<>
   <p className="text-sm text-slate-400">Execution follows the section and rule sequence shown below. Move sections or rules with the arrows. Previews recalculate after each change.</p>
   {order.map((category,sectionIndex)=>{const group=pipeline.filter(r=>r.category===category);return <section key={category} className={card}><div className="flex flex-wrap justify-between gap-3"><h3 className="font-semibold">{sectionIndex+1}. {category} Rules</h3><div className="flex gap-2"><button aria-label={`Move ${category} section up`} disabled={sectionIndex===0} className={button} onClick={()=>moveSection(sectionIndex,-1)}><ArrowUp size={16}/></button><button aria-label={`Move ${category} section down`} disabled={sectionIndex===order.length-1} className={button} onClick={()=>moveSection(sectionIndex,1)}><ArrowDown size={16}/></button></div></div>
    <select aria-label={`Add ${category} rule`} className={input} value="" onChange={e=>addRule(e.target.value,category)}><option value="">Select a rule to add…</option>{catalog.filter(r=>r.category===category).map(r=><option key={r.id} value={r.id}>{r.name}</option>)}<option value="new">＋ Add New Rules…</option></select>
    {group.map((rule,index)=><article key={rule.id} className="rounded-lg border border-slate-600 bg-slate-900/50 p-4 space-y-3"><div className="flex justify-between gap-3"><h4 className="font-medium text-cyan-300">Step {pipeline.findIndex(r=>r.id===rule.id)+1}: {rule.name}</h4><div className="flex gap-1"><button aria-label={`Move ${rule.name} up`} disabled={index===0} className={button} onClick={()=>moveRule(rule,-1)}><ArrowUp size={14}/></button><button aria-label={`Move ${rule.name} down`} disabled={index===group.length-1} className={button} onClick={()=>moveRule(rule,1)}><ArrowDown size={14}/></button><button aria-label={`Remove ${rule.name}`} className={button} onClick={()=>change({pipeline:config.pipeline.filter(r=>r.id!==rule.id)})}><Trash2 size={14}/></button></div></div><RuleSettings rule={rule} onChange={updateRule} fields={fields}/><details><summary className="cursor-pointer text-sm">Preview this rule {preview?.steps.find(s=>s.id===rule.id)?`· ${preview.steps.find(s=>s.id===rule.id).changedCells} changes`:''}</summary><div className="pt-3"><StepPreview step={preview?.steps.find(s=>s.id===rule.id)}/></div></details></article>)}
    {!group.length&&<p className="text-sm text-slate-400">No {category.toLowerCase()} rules configured.</p>}
    <details><summary className="text-sm cursor-pointer">Preview {category.toLowerCase()} section</summary><div className="pt-3"><StepPreview step={preview?.sections.find(s=>s.category===category)||(preview&&group.length===0?{before:preview.sections.filter(s=>order.indexOf(s.category)<sectionIndex).at(-1)?.after||preview.original,after:preview.sections.filter(s=>order.indexOf(s.category)<sectionIndex).at(-1)?.after||preview.original,issues:[]}:null)}/></div></details>
   </section>;})}
   {newRule&&<section className={card+' border-cyan-500/50'}><h3 className="font-semibold">Add New {newRule.category} Rule</h3><p className="text-sm text-slate-400">Create a reusable named rule using an available operation. Its saved settings will appear in the dropdown.</p><div className="grid md:grid-cols-2 gap-3"><Field label="Rule name"><input className={input} value={newRule.name} onChange={e=>setNewRule(r=>({...r,name:e.target.value}))}/></Field><Field label="Operation"><select className={input} value={newRule.operation} onChange={e=>setNewRule(r=>({...r,operation:e.target.value,dateFormat:'%d/%m/%Y'}))}>{Object.entries(operations[newRule.category]).map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></Field></div><RuleSettings rule={newRule} onChange={setNewRule} fields={fields}/><div className="flex gap-2"><button className={primary} disabled={busy||!newRule.name.trim()} onClick={createRule}>Save New Rule and Add</button><button className={button} onClick={()=>setNewRule(null)}>Cancel</button></div></section>}
   <section className={card+' border-cyan-500/40'}><div className="flex flex-wrap justify-between gap-3"><h3 className="text-lg font-semibold">Preview Final Example</h3><button disabled={!preview||busy||previewBusy} className={button} onClick={downloadExample}>Export Final Example CSV</button></div>{previewBusy&&<p role="status" className="text-cyan-300 text-sm">Applying rules in sequence…</p>}{preview?<><p className="text-sm text-slate-400">{preview.totalRows} rows processed · {preview.changedCells} changes · {preview.issueRows} rows flagged · showing up to 25 rows. Validation detections remain attached to the step where they occurred.</p><Rows title="Final output" rows={preview.final}/><Issues issues={preview.issues}/></>:<p className="text-sm text-slate-400">Upload a sample and complete the rule settings to preview the final output.</p>}</section>
   <div className="flex justify-end"><button disabled={busy} className={primary} onClick={save}><Save size={16}/>Save Configuration</button></div>
  </>}
 </div>;
}
