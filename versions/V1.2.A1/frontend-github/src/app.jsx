import BatchLogs from './BatchLogs';
import RetailerSetup from './RetailerSetup';
import React, { useState, useEffect } from 'react';
import { 
  Building2, Database, BarChart3, Settings, Search, 
  Filter, Download, X, Play, RefreshCw, CheckCircle2,
  Mail, Edit2, ShieldAlert, Cpu, Check, FileText
} from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api/v1';
export default function App() {
  const [activeTab, setActiveTab] = useState('Data Streams');
  const [batchFile, setBatchFile] = useState(null);
  const [stores, setStores] = useState([]);
  const [connectionError, setConnectionError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [runs, setRuns] = useState([]);
  const [trim, setTrim] = useState(true);
  const [numericFields, setNumericFields] = useState('');
  const [dateFields, setDateFields] = useState('');
  const [dateFormat, setDateFormat] = useState('%d/%m/%Y');
  const [requiredFields, setRequiredFields] = useState('');
  const [consent, setConsent] = useState(false);
  const [assistance, setAssistance] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiConfigured, setAiConfigured] = useState(false);
  const splitFields = value => value.split(',').map(v => v.trim()).filter(Boolean);
  const refreshRuns = async () => {
    try { const res = await fetch(`${API}/runs`); const data = await res.json(); if (res.ok) setRuns(data.runs); } catch { /* Connection is reported by the store request. */ }
  };
  const loadRun = async (id) => {
    try { const res = await fetch(`${API}/runs/${id}`); const data = await res.json(); if (!res.ok) throw new Error(data.error); setCleanResult(data); setSelectedFile(null); setAssistance(null); setIsModalOpen(true); } catch (e) { setConnectionError(e.message); }
  };
  const requestAssistance = async () => {
    setAiLoading(true);
    try {
      const res = await fetch(`${API}/ai-assist`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({consent,sample:cleanResult.rawSample,issues:cleanResult.issues})});
      const data = await res.json(); if (!res.ok) throw new Error(data.error); setAssistance(data.assistance);
    } catch (e) { setConnectionError(e.message); } finally { setAiLoading(false); }
  };
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  
  // Data Cleansing Modal States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [cleanResult, setCleanResult] = useState(null);

  // Edit Store Modal States
  const [editingStore, setEditingStore] = useState(null);

  // Email Generator Modal States
  const [emailStore, setEmailStore] = useState(null);
  const [emailCopied, setEmailCopied] = useState(false);

  useEffect(() => {
    fetchStores();
    refreshRuns();
    fetch(`${API}/health`).then(r => r.json()).then(d => setAiConfigured(d.aiConfigured)).catch(() => {});
  }, []);

  const fetchStores = async () => {
    try {
      const res = await fetch(`${API}/stores`);
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.error || 'Could not load stores.');
      setStores(data.stores); setConnectionError('');
    } catch (e) { setConnectionError('Backend unavailable. Start the Flask server on port 5000.'); }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0]; if (!file) return;
    setBatchFile(file); setActiveTab('Data Streams'); e.target.value='';
  };
  const runCleaning = async () => {
    if (!selectedFile) return;
    setLoading(true); setCleanResult(null); setAssistance(null); setConnectionError('');
    const formData = new FormData(); formData.append('file',selectedFile);
    formData.append('rules',JSON.stringify({trim,numericFields:splitFields(numericFields),dateFields:splitFields(dateFields),dateFormat,requiredFields:splitFields(requiredFields),flagDuplicates:true}));
    try {
      const res=await fetch(`${API}/upload-and-clean`,{method:'POST',body:formData}); const data=await res.json();
      if(!res.ok || !data.success) throw new Error(data.error || 'Processing failed.');
      setCleanResult(data); refreshRuns(); fetchStores();
    } catch(e) {setConnectionError(e.message || 'Cannot reach the backend.');} finally {setLoading(false);}
  };

  const handleExport = async () => {
    if (!cleanResult?.cleanedSample) return;

    try {
      const res = await fetch(`${API}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          runId: cleanResult.runId,
          fileType: cleanResult.fileType || 'csv'
        })
      });

      if (!res.ok) { const data = await res.json(); throw new Error(data.error || "Export failed"); }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cleaned_dataset.${cleanResult.fileType || 'csv'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Export failed: " + err.message);
    }
  };

  // Edit Store Handlers
  const handleSaveStore = async (e) => {
    e.preventDefault();
    try {
      const res=await fetch(`${API}/stores/${encodeURIComponent(editingStore.store_id)}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(editingStore)});
      const data=await res.json(); if(!res.ok) throw new Error(data.error);
      setEditingStore(null); await fetchStores();
    } catch(e) {setConnectionError(e.message);}
  };

  // Copy Generated Email
  const handleCopyEmail = (text) => {
    navigator.clipboard.writeText(text);
    setEmailCopied(true);
    setTimeout(() => setEmailCopied(false), 2000);
  };

  // Search & Status Filter Logic
  const filteredStores = stores.filter(s => {
    const matchesSearch = 
      (s.store_name || '').toLowerCase().includes(searchQuery.toLowerCase()) || 
      (s.store_id || '').toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesStatus = statusFilter === 'All' || s.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex h-screen bg-[#0f172a] text-slate-100 font-sans overflow-hidden">
      
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-[#1e293b] border-r border-slate-700/50 flex flex-col justify-between p-4 shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-8 px-2">
            <Database className="text-cyan-400 w-6 h-6" />
            <span className="font-bold text-lg tracking-wide text-cyan-400">DataFlow Hub</span>
          </div>

          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 px-2">Modules</div>
          <nav className="space-y-1">
            {[
              { name: 'Retailer Data Setup', icon: Building2 },
              { name: 'Clients', icon: Building2 },
              { name: 'Data Streams', icon: Database },
              { name: 'Quality Analytics', icon: BarChart3 },
              { name: 'Settings', icon: Settings },
            ].map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.name;
              return (
                <button
                  key={item.name}
                  onClick={() => setActiveTab(item.name)}
                  className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.name}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
          <label className="flex items-center justify-center gap-2 cursor-pointer bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold py-2 px-4 rounded-md text-xs transition-colors">
            <Download className="w-4 h-4" />
            Upload Data File
            <input type="file" accept=".csv,.json,.xlsx" onChange={handleFileUpload} className="hidden" />
          </label>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        <header className="h-16 border-b border-slate-800 flex items-center justify-between px-8 bg-[#0f172a] shrink-0">
          <h1 className="text-xl font-bold text-slate-100">DataFlow Hub — Data Operations Suite</h1>
          <span className="text-xs bg-slate-800 text-cyan-400 px-2.5 py-1 rounded-full border border-slate-700">V1.2.A1</span>
        </header>

        <div className="p-8 space-y-6 flex-1">
          {connectionError && <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">{connectionError}</div>}
          
          {activeTab === 'Retailer Data Setup' && <RetailerSetup />}
          {/* TAB 1: CLIENTS MODULE */}
          {activeTab === 'Clients' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold tracking-tight">Client Store Management & Data Quality Tracker</h2>
              </div>

              <div className="grid grid-cols-3 gap-6">
                
                {/* Store Management Table */}
                <div className="col-span-2 bg-[#1e293b] rounded-xl border border-slate-800 p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-slate-200">Client Stores Overview</h3>
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                        <input 
                          type="text" 
                          placeholder="Search Store ID or Name..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="bg-slate-900 border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 w-48"
                        />
                      </div>
                      
                      {/* Filter Dropdown */}
                      <div className="flex items-center gap-1 bg-slate-900 border border-slate-700 rounded-md px-2 py-1">
                        <Filter className="w-3.5 h-3.5 text-slate-400" />
                        <select 
                          value={statusFilter}
                          onChange={(e) => setStatusFilter(e.target.value)}
                          className="bg-transparent text-xs text-slate-300 focus:outline-none cursor-pointer"
                        >
                          <option value="All" className="bg-slate-900">All Statuses</option>
                          <option value="Clean" className="bg-slate-900">Clean</option>
                          <option value="Error" className="bg-slate-900">Error</option>
                          <option value="Pending" className="bg-slate-900">Pending</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/50 text-slate-400 uppercase border-b border-slate-800">
                        <tr>
                          <th className="p-3">Store ID</th>
                          <th className="p-3">Name</th>
                          <th className="p-3">Status</th>
                          <th className="p-3">Missing Fields</th>
                          <th className="p-3">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-300">
                        {filteredStores.length === 0 ? (
                          <tr>
                            <td colSpan="5" className="p-4 text-center text-slate-500">No stores found matching filter.</td>
                          </tr>
                        ) : (
                          filteredStores.map((s) => (
                            <tr key={s.store_id} className="hover:bg-slate-800/30">
                              <td className="p-3 font-medium text-cyan-400">{s.store_id}</td>
                              <td className="p-3">{s.store_name}</td>
                              <td className="p-3">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                  s.status === 'Clean' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                  s.status === 'Error' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                                  'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                }`}>
                                  {s.status}
                                </span>
                              </td>
                              <td className="p-3">{s.missing_fields}</td>
                              <td className="p-3 flex items-center gap-2">
                                <button 
                                  onClick={() => setEditingStore(s)}
                                  className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 text-slate-200 px-2 py-1 rounded text-[11px] border border-slate-700"
                                >
                                  <Edit2 className="w-3 h-3" /> Edit
                                </button>
                                <button 
                                  onClick={() => setEmailStore(s)}
                                  className="flex items-center gap-1 bg-indigo-600/80 hover:bg-indigo-600 text-white px-2 py-1 rounded text-[11px]"
                                >
                                  <Mail className="w-3 h-3" /> Generate Email
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Side Metrics & Processing Insights */}
                <div className="space-y-6">
                  <div className="bg-[#1e293b] rounded-xl border border-slate-800 p-5 space-y-4">
                    <h3 className="font-bold text-slate-200">Data Quality Metrics</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                        <div className="text-2xl font-bold text-emerald-400">{stores.length ? `${((stores.filter(s => s.status === 'Clean').length / stores.length) * 100).toFixed(1)}%` : '—'}</div>
                        <div className="text-[11px] text-slate-400">Stores marked clean</div>
                      </div>
                      <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                        <div className="text-2xl font-bold text-rose-400">
                          {stores.filter(s => s.status === 'Error').length}
                        </div>
                        <div className="text-[11px] text-slate-400">Active Errors</div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-[#1e293b] rounded-xl border border-slate-800 p-5 space-y-3">
                    <h3 className="font-bold text-slate-200">Processing Insights</h3>
                    <div className="space-y-2">
                      {[
                        { title: "Processing runs", desc: `${runs.length} earlier uploads available in Quality Analytics. Retailer/week batches are recorded in Data Streams.`, time: "Current database" },
                      ].map((insight, idx) => (
                        <div key={idx} className="p-3 bg-slate-900/50 rounded-lg border border-slate-800/80 text-xs space-y-1">
                          <div className="font-semibold text-cyan-400">{insight.title}</div>
                          <div className="text-slate-400">{insight.desc}</div>
                          <div className="text-[10px] text-slate-500">{insight.time}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 2: DATA STREAMS MODULE */}
          {activeTab === 'Data Streams' && <BatchLogs incomingFile={batchFile} onFileAccepted={() => setBatchFile(null)} />}

          {/* TAB 3: QUALITY ANALYTICS MODULE */}
          {activeTab === 'Quality Analytics' && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold tracking-tight">Data Quality & Validation Rules</h2>
              <div className="bg-[#1e293b] rounded-xl p-5 space-y-3"><h3 className="font-bold">Measured processing results</h3>
                <p className="text-xs text-slate-400">Issue rows count distinct records failing the configured checks. These checks do not certify business accuracy.</p>
                {runs.length === 0 && <p className="text-sm">Process a file to view quality results.</p>}
                {runs.map(run => <button key={run.id} onClick={() => loadRun(run.id)} className="block w-full text-left p-3 border border-slate-700 rounded text-sm">{run.filename} · {run.outputRows} output rows · {run.changedCells} changed cells · {run.issueRows} issue rows · {run.outputRows ? ((run.outputRows-run.issueRows)/run.outputRows*100).toFixed(1) : 'N/A'}% passing configured checks</button>)}
              </div>
              <div className="bg-[#1e293b] rounded-xl border border-slate-800 p-6 space-y-4">
                <h3 className="font-bold text-slate-200">Available Cleaning Rules</h3>
                <div className="space-y-3">
                  {[
                    { name: "Whitespace Sanitization", rule: "Optional trimming across text fields; originals are preserved." },
                    { name: "Missing Field Normalization", rule: "Flags selected required fields without inventing missing values." },
                    { name: "ISO Date Standardization", rule: "Converts selected date fields using an explicit input format; invalid values are flagged." },
                    { name: "Numeric Revenue Sanitization", rule: "Converts selected numeric fields; invalid text is retained for review." },
                  ].map((r, idx) => (
                    <div key={idx} className="flex items-start gap-3 bg-slate-900/50 p-3 rounded-lg border border-slate-800/80">
                      <ShieldAlert className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-xs font-semibold text-slate-200">{r.name}</div>
                        <div className="text-xs text-slate-400">{r.rule}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: SETTINGS MODULE */}
          {activeTab === 'Settings' && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold tracking-tight">System Settings & API Configurations</h2>
              <div className="bg-[#1e293b] rounded-xl border border-slate-800 p-6 space-y-4 max-w-xl">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400">Backend API Endpoint</label>
                  <input type="text" readOnly value={API} className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-300 font-mono" />
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400">Database Engine</label>
                  <input type="text" readOnly value="SQLite Embedded Database" className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-300 font-mono" />
                </div>
              </div>
            </div>
          )}

        </div>
      </main>

      {/* MODAL 1: EDIT STORE */}
      {editingStore && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="bg-[#1e293b] border border-slate-700 rounded-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-700 pb-3">
              <h3 className="font-bold text-slate-100 flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-cyan-400" /> Edit Store Details
              </h3>
              <button onClick={() => setEditingStore(null)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSaveStore} className="space-y-4">
              {connectionError && <p role="alert" className="text-sm text-rose-300">{connectionError}</p>}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400">Store ID</label>
                <input type="text" disabled value={editingStore.store_id} className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-slate-500" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400">Store Name</label>
                <input 
                  type="text" 
                  value={editingStore.store_name} 
                  onChange={(e) => setEditingStore({ ...editingStore, store_name: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:border-cyan-500 outline-none" 
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400">Status</label>
                <select 
                  value={editingStore.status} 
                  onChange={(e) => setEditingStore({ ...editingStore, status: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:border-cyan-500 outline-none"
                >
                  <option value="Clean">Clean</option>
                  <option value="Pending">Pending</option>
                  <option value="Error">Error</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditingStore(null)} className="px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800 rounded">Cancel</button>
                <button type="submit" className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-4 py-1.5 rounded text-xs">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: GENERATE EMAIL */}
      {emailStore && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="bg-[#1e293b] border border-slate-700 rounded-xl w-full max-w-lg p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-700 pb-3">
              <h3 className="font-bold text-slate-100 flex items-center gap-2">
                <Mail className="w-4 h-4 text-indigo-400" /> Client Data Audit Notification
              </h3>
              <button onClick={() => setEmailStore(null)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400">Automated Draft Message</label>
              <textarea 
                readOnly 
                rows="8"
                value={`Subject: Action Required: Data Quality Audit for ${emailStore.store_name} (${emailStore.store_id})\n\nDear Store Manager,\n\nOur DataFlow Hub automated compliance engine detected ${emailStore.missing_fields} missing or unformatted fields in your latest data payload.\n\nPlease update your store record to maintain synchronized client reporting.\n\nBest regards,\nData Operations Team`}
                className="w-full bg-slate-950 border border-slate-800 rounded p-3 text-xs text-slate-300 font-mono leading-relaxed outline-none"
              />
            </div>

            <div className="flex justify-between items-center pt-2">
              <span className="text-xs text-slate-400">Recipient: confirm the actual client email before sending</span>
              <button 
                onClick={() => handleCopyEmail(`Subject: Action Required: Data Quality Audit for ${emailStore.store_name} (${emailStore.store_id})\n\nDear Store Manager,\n\nOur DataFlow Hub automated compliance engine detected ${emailStore.missing_fields} missing or unformatted fields in your latest data payload.\n\nPlease update your store record to maintain synchronized client reporting.\n\nBest regards,\nData Operations Team`)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-1.5 rounded text-xs flex items-center gap-1.5"
              >
                {emailCopied ? <Check className="w-3.5 h-3.5" /> : <Mail className="w-3.5 h-3.5" />}
                {emailCopied ? 'Copied to Clipboard!' : 'Copy Draft Email'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: DATA CLEANSING TRACE MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="bg-[#1e293b] border border-slate-700 rounded-xl w-full max-w-4xl shadow-2xl flex flex-col max-h-[90vh]">
            
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <h3 className="font-bold text-slate-100 flex items-center gap-2">
                <RefreshCw className={`w-4 h-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
                Data Cleansing Configuration & Trace Preview
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6 flex-1">
              {connectionError && <p role="alert" className="text-rose-300 text-sm">{connectionError}</p>}
              {selectedFile && !loading && <div className="space-y-3 text-sm">
                <p className="text-cyan-300">Selected: {selectedFile.name}. Configure rules, then run processing.</p>
                <label className="flex gap-2"><input type="checkbox" checked={trim} onChange={e => setTrim(e.target.checked)} /> Trim whitespace · duplicates are flagged and retained</label>
                <div className="grid grid-cols-2 gap-3">
                  <label>Numeric fields (comma-separated)<input className="block w-full bg-slate-950 p-2 rounded" value={numericFields} onChange={e => setNumericFields(e.target.value)} placeholder="sales, quantity" /></label>
                  <label>Required fields<input className="block w-full bg-slate-950 p-2 rounded" value={requiredFields} onChange={e => setRequiredFields(e.target.value)} placeholder="store_id, sku" /></label>
                  <label>Date fields<input className="block w-full bg-slate-950 p-2 rounded" value={dateFields} onChange={e => setDateFields(e.target.value)} placeholder="date" /></label>
                  <label>Input date format<input className="block w-full bg-slate-950 p-2 rounded" value={dateFormat} onChange={e => setDateFormat(e.target.value)} /></label>
                </div><p className="text-xs text-slate-400">Use exact source headers. Invalid values are retained and flagged; missing business values are never invented.</p>
              </div>}
              {cleanResult && <div className="space-y-3 text-sm">
                <p>{cleanResult.totalRows} input rows · {cleanResult.outputRows} output rows · {cleanResult.changedCells} changed cells · {cleanResult.issueRows} rows require review</p>
                <a className="text-cyan-300 underline" href={`${API}/runs/${cleanResult.runId}/audit`}>Download original file, rules and audit evidence</a>

              </div>}
              {loading ? (
                <div className="py-12 flex flex-col items-center justify-center space-y-3">
                  <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
                  <p className="text-sm text-slate-400">Processing every row and saving transformation evidence...</p>
                </div>
              ) : cleanResult ? (
                <>
                  <CleaningLog result={cleanResult} />
                  <DataPreview title="Original data (up to 25 rows)" rows={cleanResult.rawSample} />
                  <DataPreview title="Cleaned data (up to 25 rows)" rows={cleanResult.cleanedSample} />
                </>
              ) : null}
            </div>

            <div className="p-4 border-t border-slate-700 bg-slate-900/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Processing actions:</span>
                <button onClick={runCleaning} disabled={!selectedFile || loading} className="disabled:opacity-40 bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-xs font-semibold px-3 py-1.5 rounded-md flex items-center gap-1.5">
                  <Play className="w-3.5 h-3.5" /> Run Full-Dataset Cleaning
                </button>
              </div>

              {cleanResult && (
                <button 
                  onClick={handleExport}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs px-4 py-2 rounded-md flex items-center gap-2 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Export Cleaned Dataset (.{cleanResult.fileType?.toUpperCase() || 'CSV'})
                </button>
              )}
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
function DataPreview({title,rows=[]}) {
 const cols=[...new Set(rows.flatMap(r=>Object.keys(r)))];
 return <section><h3 className="font-bold mb-2">{title}</h3><div className="overflow-auto max-h-80"><table className="w-full text-xs text-left"><thead><tr>{cols.map(c=><th className="p-2 border border-slate-700" key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{cols.map(c=><td className="p-2 border border-slate-700" key={c}>{String(r[c]??'')}</td>)}</tr>)}</tbody></table></div></section>;
}
function CleaningLog({result}) {
 const [page,setPage]=useState(0);
 useEffect(()=>setPage(0),[result.runId]);
 const rows=[...(result.transformationTrace||[]).map(t=>({...t,status:'Changed'})),...(result.issues||[]).map(i=>({...i,status:'Review',action:i.issue}))].sort((a,b)=>a.row-b.row);
 const pages=Math.max(1,Math.ceil(rows.length/25));
 return <section className="space-y-3"><h3 className="font-bold">Cleaning log</h3><div className="flex gap-4"><a className="text-cyan-300 underline" href={`${API}/runs/${result.runId}/log`}>Export full log CSV</a><a className="text-cyan-300 underline" target="_blank" rel="noreferrer" href={`${API}/runs/${result.runId}/print`}>Print full log</a></div><div className="overflow-auto"><table className="w-full text-xs text-left"><thead><tr>{['Row','Field','Status','Before','After','Action / detection'].map(c=><th key={c} className="p-2 border border-slate-700">{c}</th>)}</tr></thead><tbody>{rows.slice(page*25,page*25+25).map((r,i)=><tr key={i}>{[r.row,r.field,r.status,r.before??'',r.after??'',r.action].map((v,j)=><td key={j} className="p-2 border border-slate-700">{String(v)}</td>)}</tr>)}</tbody></table>{!rows.length&&<p className="p-3">No changes or issues detected.</p>}</div><div className="flex items-center gap-4"><button disabled={page===0} onClick={()=>setPage(p=>p-1)} className="disabled:opacity-40">Previous</button><span>Entries {rows.length?page*25+1:0}–{Math.min(rows.length,page*25+25)} of {rows.length} · 25 per page</span><button disabled={page>=pages-1} onClick={()=>setPage(p=>p+1)} className="disabled:opacity-40">Next</button></div></section>;
}
