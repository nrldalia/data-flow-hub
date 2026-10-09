import React,{useEffect,useRef,useState} from 'react';
import {Pencil,Plus,Trash2} from 'lucide-react';
import RetailerSetup from './RetailerSetup';
const API=import.meta.env.VITE_API_URL||'/api/v1';
const button='inline-flex items-center justify-center gap-2 rounded border border-slate-600 px-3 py-2 text-sm hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed';
function setupStatus(r){
 if(r.pipeline?.some(rule=>rule.operation==='reference'))return 'Reference only';
 if(!r.name||!r.key||!r.senderEmail||!r.stores?.length||!['Cleaning','Transformation','Validation'].every(c=>r.pipeline?.some(rule=>rule.category===c)))return 'Setup incomplete';
 return 'Ready';
}
export default function Client(){
 const [retailers,setRetailers]=useState([]),[selected,setSelected]=useState([]),[editing,setEditing]=useState(undefined),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const allBox=useRef(null);
 async function refresh(){const response=await fetch(`${API}/retailers`);const data=await response.json();if(!response.ok||!data.success)throw new Error(data.error||'Could not load clients.');setRetailers(data.retailers);setSelected([]);}
 useEffect(()=>{refresh().catch(e=>setError(e.message));},[]);
 useEffect(()=>{if(allBox.current)allBox.current.indeterminate=selected.length>0&&selected.length<retailers.length;},[selected,retailers,editing]);
 async function remove(){
  if(!selected.length||!window.confirm(`Delete ${selected.length} selected retailer setup(s) and their uploaded samples? Batch audit history will remain.`))return;
  setBusy(true);setError('');setNotice('');
  try{const response=await fetch(`${API}/retailers/delete`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:selected})});const data=await response.json();if(!response.ok||!data.success)throw new Error(data.error||'Deletion failed.');await refresh();setNotice(`${data.deletedIds.length} retailer setup(s) deleted.`);}catch(e){setError(e.message);}finally{setBusy(false);}
 }
 if(editing!==undefined)return <RetailerSetup key={editing||'new'} initialRetailerId={editing} onBack={()=>{setEditing(undefined);refresh().catch(e=>setError(e.message));}}/>;
 return <div className="space-y-5" data-testid="client-management"><div className="flex flex-wrap justify-between gap-3"><div><h2 className="text-2xl font-bold">Client</h2><p className="text-sm text-slate-400 mt-2">Select Edit to open retailer Setup.</p></div><div className="flex gap-2"><button className={button+' text-rose-300'} disabled={busy||!selected.length} onClick={remove}><Trash2 size={16}/>Delete{selected.length?` (${selected.length})`:''}</button><button className={button+' bg-cyan-600'} disabled={busy} onClick={()=>setEditing(null)}><Plus size={16}/>Add Retailer</button></div></div>{error&&<p role="alert" className="text-rose-300">{error}</p>}{notice&&<p role="status" className="text-emerald-300">{notice}</p>}<div className="rounded-xl bg-[#1e293b] border border-slate-700 overflow-x-auto"><table className="w-full text-sm text-left"><thead className="bg-slate-900 text-slate-400"><tr><th className="p-3 w-12"><input ref={allBox} type="checkbox" aria-label="Select all retailers" disabled={busy||!retailers.length} checked={retailers.length>0&&selected.length===retailers.length} onChange={e=>setSelected(e.target.checked?retailers.map(r=>r.id):[])}/></th><th className="p-3">Retailer Name</th><th className="p-3">Setup Status</th><th className="p-3">Edit</th></tr></thead><tbody>{retailers.map(r=><tr key={r.id} className="border-t border-slate-700"><td className="p-3"><input type="checkbox" aria-label={`Select ${r.name}`} checked={selected.includes(r.id)} disabled={busy} onChange={e=>setSelected(list=>e.target.checked?[...list,r.id]:list.filter(id=>id!==r.id))}/></td><td className="p-3 font-medium">{r.name}</td><td className="p-3"><span title="Ready requires retailer details, at least one store and executable rules in all three components." className={setupStatus(r)==='Ready'?'text-emerald-300':'text-amber-300'}>{setupStatus(r)}</span></td><td className="p-3"><button className={button} disabled={busy} title="Edit retailer setup" aria-label={`Edit ${r.name}`} onClick={()=>setEditing(r.id)}><Pencil size={16}/></button></td></tr>)}</tbody></table>{!retailers.length&&<p className="p-6 text-center text-slate-400">No retailers. Add a retailer to begin setup.</p>}</div></div>;
}
