import React, { useState, useEffect } from 'react';
import { 
  Building2, Database, BarChart3, Settings, Search, 
  Filter, Download, X, Play, RefreshCw, CheckCircle2,
  Mail, Edit2, ShieldAlert, Cpu, Check, FileText
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('Clients');
  const [stores, setStores] = useState([]);
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
  }, []);

  const fetchStores = async () => {
    try {
      const res = await fetch('http://127.0.0.1:5000/api/v1/stores');
      const data = await res.json();
      if (data.success) setStores(data.stores);
    } catch (e) {
      // Fallback mock dataset if backend is offline
      setStores([
        { store_id: 'STR-001', store_name: 'Metro Electronics Subang', region: 'Central', status: 'Clean', missing_fields: 0 },
        { store_id: 'STR-002', store_name: 'Apex Groceries Petaling', region: 'Central', status: 'Error', missing_fields: 4 },
        { store_id: 'STR-003', store_name: 'Vanguard Retail Klang', region: 'Central', status: 'Pending', missing_fields: 2 },
      ]);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    setIsModalOpen(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://127.0.0.1:5000/api/v1/upload-and-clean', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        setCleanResult(data);
      } else {
        alert("Cleaning failed: " + data.error);
      }
    } catch (err) {
      alert("Failed to connect to backend server.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!cleanResult?.cleanedSample) return;

    try {
      const res = await fetch('http://127.0.0.1:5000/api/v1/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data: cleanResult.cleanedSample,
          fileType: cleanResult.fileType || 'csv'
        })
      });

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cleaned_dataset.${cleanResult.fileType || 'csv'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert("Export failed: " + err.message);
    }
  };

  // Edit Store Handlers
  const handleSaveStore = (e) => {
    e.preventDefault();
    setStores(stores.map(s => s.store_id === editingStore.store_id ? editingStore : s));
    setEditingStore(null);
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
            Upload File for AI Clean
            <input type="file" accept=".csv,.json" onChange={handleFileUpload} className="hidden" />
          </label>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        <header className="h-16 border-b border-slate-800 flex items-center justify-between px-8 bg-[#0f172a] shrink-0">
          <h1 className="text-xl font-bold text-slate-100">DataFlow Hub — Data Operations Suite</h1>
          <span className="text-xs bg-slate-800 text-cyan-400 px-2.5 py-1 rounded-full border border-slate-700">v1.0.0</span>
        </header>

        <div className="p-8 space-y-6 flex-1">
          
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

                {/* Side Metrics & AI Insights */}
                <div className="space-y-6">
                  <div className="bg-[#1e293b] rounded-xl border border-slate-800 p-5 space-y-4">
                    <h3 className="font-bold text-slate-200">Data Quality Metrics</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                        <div className="text-2xl font-bold text-emerald-400">98.5%</div>
                        <div className="text-[11px] text-slate-400">Clean Records</div>
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
                    <h3 className="font-bold text-slate-200">AI Insights</h3>
                    <div className="space-y-2">
                      {[
                        { title: "Validation Engine", desc: "Missing audit timestamps auto-sanitized to N/A.", time: "2 hrs ago" },
                        { title: "Anomaly Detection", desc: "Detected 4 retail records with missing store emails.", time: "5 hrs ago" }
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
          {activeTab === 'Data Streams' && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold tracking-tight">Active Data Streams & Ingestion Architecture</h2>
              <div className="bg-[#1e293b] rounded-xl border border-slate-800 p-6 space-y-6">
                <p className="text-sm text-slate-300">
                  DataFlow Hub ingests unstructured raw retail payloads from API endpoints, direct JSON streams, and batch CSV uploads.
                </p>

                <div className="grid grid-cols-3 gap-6">
                  <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800 space-y-2">
                    <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
                      <Database className="w-4 h-4" /> 1. Ingestion Layer
                    </div>
                    <p className="text-xs text-slate-400">Accepts CSV or raw JSON client payloads via Flask REST API endpoints.</p>
                  </div>

                  <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800 space-y-2">
                    <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
                      <Cpu className="w-4 h-4" /> 2. AI Processing Engine
                    </div>
                    <p className="text-xs text-slate-400">Uses Gemini 3.6 Flash structured JSON output schemas for standardization and trace logs.</p>
                  </div>

                  <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800 space-y-2">
                    <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
                      <FileText className="w-4 h-4" /> 3. Export & Persistence
                    </div>
                    <p className="text-xs text-slate-400">Stores audit traces into SQLite and delivers dynamic clean CSV/JSON downloads.</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: QUALITY ANALYTICS MODULE */}
          {activeTab === 'Quality Analytics' && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold tracking-tight">Data Quality & Validation Rules</h2>
              <div className="bg-[#1e293b] rounded-xl border border-slate-800 p-6 space-y-4">
                <h3 className="font-bold text-slate-200">Active Cleaning Rules Engine</h3>
                <div className="space-y-3">
                  {[
                    { name: "Whitespace Sanitization", rule: "Strips leading/trailing unescaped spaces from all store text properties." },
                    { name: "Missing Field Normalization", rule: "Replaces null, empty, or undefined properties with standard 'N/A' flags." },
                    { name: "ISO Date Standardization", rule: "Converts custom audit date inputs to YYYY-MM-DD format." },
                    { name: "Numeric Revenue Sanitization", rule: "Strips currency symbols ($) and formats revenue values cleanly." },
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
                  <input type="text" readOnly value="http://127.0.0.1:5000/api/v1" className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-300 font-mono" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-400">AI Model Pipeline</label>
                  <input type="text" readOnly value="gemini-3.6-flash (JSON Output Mode)" className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-300 font-mono" />
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
              <span className="text-xs text-slate-400">Recipient: {emailStore.store_id}@client-network.com</span>
              <button 
                onClick={() => handleCopyEmail(`Subject: Action Required: Data Quality Audit for ${emailStore.store_name}\n\nDear Store Manager,\n\nOur DataFlow Hub automated compliance engine detected ${emailStore.missing_fields} missing fields.`)}
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
              {loading ? (
                <div className="py-12 flex flex-col items-center justify-center space-y-3">
                  <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
                  <p className="text-sm text-slate-400">Gemini AI is analyzing and transforming your payload...</p>
                </div>
              ) : cleanResult ? (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-400">Raw Client Payload (JSON Sample)</label>
                      <pre className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-amber-300 border border-slate-800 h-40 overflow-y-auto">
                        {JSON.stringify(cleanResult.rawSample || cleanResult.cleanedSample, null, 2)}
                      </pre>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-400">Processed Output</label>
                      <pre className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-emerald-400 border border-slate-800 h-40 overflow-y-auto">
                        {JSON.stringify(cleanResult.cleanedSample, null, 2)}
                      </pre>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-400">Transformation Trace</label>
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1 max-h-32 overflow-y-auto">
                      {(cleanResult.transformationTrace || []).map((trace, idx) => (
                        <div key={idx} className="text-xs text-slate-300 font-mono flex items-center gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span>{trace.action} on <strong className="text-cyan-300">{trace.field}</strong></span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : null}
            </div>

            <div className="p-4 border-t border-slate-700 bg-slate-900/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">AI Feature Triggers:</span>
                <button className="bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-xs font-semibold px-3 py-1.5 rounded-md flex items-center gap-1.5">
                  <Play className="w-3.5 h-3.5" /> Run Automated Cleansing
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