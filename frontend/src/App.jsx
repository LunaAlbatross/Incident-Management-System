import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertTriangle, CheckCircle, Clock, Server, Zap, Shield, Activity, ChevronRight, X } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const STATE_CONFIG = {
  OPEN:          { color: 'text-red-600',    bg: 'bg-red-100',    border: 'border-red-200',    dot: 'bg-red-500',    pulse: true  },
  INVESTIGATING: { color: 'text-amber-600',  bg: 'bg-amber-100',  border: 'border-amber-200',  dot: 'bg-amber-500',  pulse: false },
  RESOLVED:      { color: 'text-emerald-600',bg: 'bg-emerald-100',border: 'border-emerald-200',dot: 'bg-emerald-500',pulse: false },
  CLOSED:        { color: 'text-slate-600',  bg: 'bg-slate-100',  border: 'border-slate-200',  dot: 'bg-slate-500',  pulse: false },
};

function StatBadge({ count, label, colorClass, icon: Icon }) {
  return (
    <div className="px-4 py-2 bg-white border border-slate-200 rounded-xl flex items-center gap-3 shadow-sm">
      <div className={`p-2 rounded-lg ${colorClass.bg} ${colorClass.text}`}>
        <Icon size={16} />
      </div>
      <div className="flex flex-col pr-2">
        <span className="text-lg font-black text-slate-800 leading-none">{count}</span>
        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mt-0.5">{label}</span>
      </div>
    </div>
  );
}

function IncidentCard({ inc, isSelected, onClick }) {
  const cfg = STATE_CONFIG[inc.state] || STATE_CONFIG.CLOSED;
  return (
    <div
      onClick={onClick}
      className={`relative p-4 cursor-pointer transition-all duration-200 border-b border-slate-100 group
        ${isSelected
          ? 'bg-blue-50/50'
          : 'bg-white hover:bg-slate-50'
        }`}
    >
      {isSelected && (
        <div className={`absolute left-0 top-0 bottom-0 w-1 ${cfg.dot}`} />
      )}
      <div className="flex justify-between items-start mb-2 pl-2">
        <span className="font-bold text-sm text-slate-800 flex items-center gap-2">
          <Server size={14} className={cfg.color} />
          {inc.component_id}
        </span>
        <span className={`flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-bold uppercase rounded-lg ${cfg.bg} ${cfg.color}`}>
          {cfg.pulse && (
            <span className="relative flex h-1.5 w-1.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-75`}/>
              <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${cfg.dot}`}/>
            </span>
          )}
          {inc.state}
        </span>
      </div>
      <div className="text-xs text-slate-500 flex items-center gap-1.5 pl-2 font-medium">
        <Clock size={12} />
        {new Date(inc.created_at).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' })}
        <span className="ml-1 opacity-60 font-normal">{new Date(inc.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  );
}

function App() {
  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [rawSignals, setRawSignals] = useState([]);
  const [rcaForm, setRcaForm] = useState({ 
    root_cause_category: 'Database', 
    fix_applied: '', 
    prevention_steps: '',
    incident_start: '',
    incident_end: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const fetchIncidents = async () => {
    try {
      const res = await axios.get(`${API_BASE}/incidents`);
      const severityMap = { P0: 1, P1: 2, P2: 3, P3: 4 };
      const sorted = res.data.sort((a, b) => {
        if (severityMap[a.severity] !== severityMap[b.severity]) {
          return severityMap[a.severity] - severityMap[b.severity];
        }
        return new Date(b.created_at) - new Date(a.created_at);
      });
      setIncidents(sorted);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSignals = async (id) => {
    try {
      const res = await axios.get(`${API_BASE}/incidents/${id}/signals`);
      setRawSignals(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 5000);
    return () => clearInterval(interval);
  }, []);

  const getLocalISOString = (date) => {
    if (!date) return '';
    const tzOffset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - tzOffset).toISOString().slice(0, 16);
  };

  useEffect(() => {
    if (selectedIncident) {
      fetchSignals(selectedIncident.id);
      setRcaForm({
        root_cause_category: 'Database',
        fix_applied: '',
        prevention_steps: '',
        incident_start: getLocalISOString(new Date(selectedIncident.created_at)),
        incident_end: getLocalISOString(new Date())
      });
    } else {
      setRawSignals([]);
    }
  }, [selectedIncident]);

  const handleStateChange = async (id, newState) => {
    try {
      await axios.put(`${API_BASE}/incidents/${id}/state?state=${newState}`);
      fetchIncidents();
      if (selectedIncident?.id === id) {
        setSelectedIncident(prev => ({ ...prev, state: newState }));
      }
    } catch (e) {
      showToast(e.response?.data?.detail || 'Error changing state');
    }
  };

  const submitRCA = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await axios.post(`${API_BASE}/incidents/${selectedIncident.id}/rca`, rcaForm);
      await handleStateChange(selectedIncident.id, 'CLOSED');
      showToast('Incident sealed successfully', 'success');
      setRcaForm({ root_cause_category: 'Database', fix_applied: '', prevention_steps: '', incident_start: '', incident_end: '' });
      setSelectedIncident(null);
    } catch (e) {
      showToast(e.response?.data?.detail || 'Error submitting RCA');
    } finally {
      setIsSubmitting(false);
    }
  };

  const counts = {
    OPEN:          incidents.filter(i => i.state === 'OPEN').length,
    INVESTIGATING: incidents.filter(i => i.state === 'INVESTIGATING').length,
    RESOLVED:      incidents.filter(i => i.state === 'RESOLVED').length,
    CLOSED:        incidents.filter(i => i.state === 'CLOSED').length,
  };

  const cfg = selectedIncident ? (STATE_CONFIG[selectedIncident.state] || STATE_CONFIG.CLOSED) : null;

  return (
    <div className="h-screen flex flex-col font-sans bg-[#f5f7fa]">
      {/* Toast Notification */}
      {toast && (
        <div className={`fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-lg border shadow-lg bg-white
          ${toast.type === 'success' ? 'border-emerald-200 text-emerald-700' : 'border-red-200 text-red-700'}`}>
          {toast.type === 'success' ? <CheckCircle size={18} className="text-emerald-500" /> : <AlertTriangle size={18} className="text-red-500" />}
          <span className="text-sm font-bold">{toast.msg}</span>
          <button onClick={() => setToast(null)} className="ml-2 hover:opacity-70"><X size={16} /></button>
        </div>
      )}

      {/* Top Header */}
      <header className="h-20 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0 z-20 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="bg-blue-600 text-white p-2 rounded-xl shadow-sm shadow-blue-600/30">
            <Shield size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-800 tracking-tight leading-none">IMS</h1>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Incident Management System</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <StatBadge count={counts.OPEN} label="Open" colorClass={{bg: 'bg-red-100', text: 'text-red-600'}} icon={AlertTriangle} />
          <StatBadge count={counts.INVESTIGATING} label="Investigating" colorClass={{bg: 'bg-amber-100', text: 'text-amber-600'}} icon={Zap} />
          <StatBadge count={counts.RESOLVED} label="Resolved" colorClass={{bg: 'bg-emerald-100', text: 'text-emerald-600'}} icon={CheckCircle} />
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex gap-6 p-6 overflow-hidden max-w-[1400px] mx-auto w-full">
        {/* Incident Stream (Sidebar List) */}
        <div className="phoenix-card w-[380px] flex-shrink-0 flex flex-col h-full overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center z-10">
            <h3 className="font-bold text-slate-800 flex items-center gap-2">
              <Activity size={18} className="text-blue-500" />
              Signal Stream
            </h3>
            <span className="bg-slate-200 text-slate-700 px-2.5 py-0.5 rounded-md text-xs font-bold">{incidents.length} NODES</span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {incidents.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3 p-8">
                <Activity size={32} className="opacity-50" />
                <p className="text-sm font-semibold">No active incidents</p>
              </div>
            ) : (
              incidents.map(inc => (
                <IncidentCard key={inc.id} inc={inc} isSelected={selectedIncident?.id === inc.id} onClick={() => setSelectedIncident(inc)} />
              ))
            )}
          </div>
        </div>

        {/* Incident Details Panel */}
        <div className="flex-1 phoenix-card overflow-y-auto relative">
          {selectedIncident ? (
            <div className="p-8">
              {/* Detail Header */}
              <div className="flex items-start justify-between mb-8 pb-6 border-b border-slate-200">
                <div>
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-slate-500 font-bold text-xs uppercase tracking-wider">ID: {selectedIncident.id}</span>
                    <span className={`px-2.5 py-1 text-[10px] font-bold uppercase rounded-lg border
                      ${selectedIncident.severity === 'P0' ? 'bg-red-50 text-red-700 border-red-200' : 
                        selectedIncident.severity === 'P1' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                        'bg-blue-50 text-blue-700 border-blue-200'}`}>
                      SEV: {selectedIncident.severity}
                    </span>
                  </div>
                  <h2 className="text-3xl font-black text-slate-800 flex items-center gap-3">
                    <Server size={28} className={cfg.color} />
                    {selectedIncident.component_id}
                  </h2>
                  <p className="text-sm font-semibold text-slate-500 mt-2 flex items-center gap-2">
                    <Clock size={16} /> Detection Time: {new Date(selectedIncident.created_at).toLocaleString()}
                  </p>
                </div>
                <span className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm uppercase tracking-wide border ${cfg.bg} ${cfg.color} ${cfg.border}`}>
                  {cfg.pulse && (
                    <span className="relative flex h-2 w-2">
                      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-75`}/>
                      <span className={`relative inline-flex rounded-full h-2 w-2 ${cfg.dot}`}/>
                    </span>
                  )}
                  {selectedIncident.state}
                </span>
              </div>

              {/* Actions */}
              <div className="flex gap-4 mb-8">
                <button
                  onClick={() => handleStateChange(selectedIncident.id, 'INVESTIGATING')}
                  disabled={selectedIncident.state !== 'OPEN'}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-amber-50 text-amber-700 font-bold text-sm border border-amber-200 hover:bg-amber-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Zap size={16} /> Mark Investigating
                </button>
                <button
                  onClick={() => handleStateChange(selectedIncident.id, 'RESOLVED')}
                  disabled={selectedIncident.state === 'RESOLVED' || selectedIncident.state === 'CLOSED'}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-50 text-emerald-700 font-bold text-sm border border-emerald-200 hover:bg-emerald-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <CheckCircle size={16} /> Mark Resolved
                </button>
              </div>

              {/* RCA Card */}
              {selectedIncident.state === 'RESOLVED' && (
                <div className="mb-8 p-6 bg-emerald-50/50 border border-emerald-200 rounded-xl">
                  <h3 className="text-lg font-black text-emerald-800 mb-6 flex items-center gap-2">
                    <Shield size={20} className="text-emerald-600" /> Root Cause Analysis
                  </h3>
                  <form onSubmit={submitRCA} className="space-y-5">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      <div>
                        <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wide mb-2">Incident Start</label>
                        <input 
                          type="datetime-local" required value={rcaForm.incident_start} onChange={e => setRcaForm({ ...rcaForm, incident_start: e.target.value })}
                          className="phoenix-input border-emerald-200 focus:border-emerald-500 focus:ring-emerald-500/20"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wide mb-2">Incident Resolved</label>
                        <input 
                          type="datetime-local" required value={rcaForm.incident_end} onChange={e => setRcaForm({ ...rcaForm, incident_end: e.target.value })}
                          className="phoenix-input border-emerald-200 focus:border-emerald-500 focus:ring-emerald-500/20"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wide mb-2">Failure Vector</label>
                      <select
                        value={rcaForm.root_cause_category} onChange={e => setRcaForm({ ...rcaForm, root_cause_category: e.target.value })}
                        className="phoenix-input border-emerald-200 focus:border-emerald-500 focus:ring-emerald-500/20"
                      >
                        <option>Database</option><option>Network</option><option>Application Logic</option>
                        <option>Infrastructure</option><option>Third-party</option><option>Human Error</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                      <div>
                        <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wide mb-2">Correction Executed</label>
                        <textarea
                          required value={rcaForm.fix_applied} onChange={e => setRcaForm({ ...rcaForm, fix_applied: e.target.value })} rows={3}
                          className="phoenix-input resize-none border-emerald-200 focus:border-emerald-500 focus:ring-emerald-500/20" placeholder="Describe the fix..."
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wide mb-2">Preventative Protocol</label>
                        <textarea
                          required value={rcaForm.prevention_steps} onChange={e => setRcaForm({ ...rcaForm, prevention_steps: e.target.value })} rows={3}
                          className="phoenix-input resize-none border-emerald-200 focus:border-emerald-500 focus:ring-emerald-500/20" placeholder="How to block future occurrences..."
                        />
                      </div>
                    </div>
                    <button
                      type="submit" disabled={isSubmitting}
                      className="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2 mt-2"
                    >
                      {isSubmitting ? 'Submitting...' : 'Seal Incident Record'}
                    </button>
                  </form>
                </div>
              )}

              {/* Audit Logs */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
                  <Activity size={18} className="text-slate-500" />
                  <h3 className="text-sm font-bold text-slate-800">Raw Telemetry (Audit Log)</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-white text-xs text-slate-400 uppercase font-bold tracking-wider border-b border-slate-100">
                      <tr>
                        <th className="px-6 py-3">Timestamp</th>
                        <th className="px-6 py-3">Severity</th>
                        <th className="px-6 py-3">Data Payload</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {rawSignals.length === 0 ? (
                        <tr><td colSpan="3" className="px-6 py-8 text-center text-slate-400 font-medium text-xs uppercase tracking-widest">No telemetry found</td></tr>
                      ) : (
                        rawSignals.map(sig => (
                          <tr key={sig.id} className="hover:bg-slate-50 transition-colors">
                            <td className="px-6 py-3 whitespace-nowrap text-slate-600 font-medium text-xs">
                              {new Date(sig.timestamp).toLocaleString()}
                            </td>
                            <td className="px-6 py-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border
                                ${sig.severity === 'P0' ? 'bg-red-50 border-red-200 text-red-700' : 
                                  sig.severity === 'P1' ? 'bg-amber-50 border-amber-200 text-amber-700' :
                                  'bg-blue-50 border-blue-200 text-blue-700'}`}>
                                {sig.severity}
                              </span>
                            </td>
                            <td className="px-6 py-3 font-mono text-[10px] text-slate-500 truncate max-w-md">
                              {JSON.stringify(sig.payload)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {selectedIncident.state === 'CLOSED' && (
                <div className="mt-8 p-10 bg-slate-50 rounded-xl border border-slate-200 flex flex-col items-center justify-center text-center">
                  <div className="w-16 h-16 bg-white border border-slate-200 rounded-full flex items-center justify-center mb-4 shadow-sm">
                    <CheckCircle size={32} className="text-slate-400" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-800 mb-1">Incident Sealed</h3>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">RCA Protocol Complete</p>
                  <p className="bg-white px-5 py-2.5 rounded-lg border border-slate-200 font-bold text-sm text-slate-600 shadow-sm">
                    MTTR: <span className="text-blue-600">{selectedIncident.mttr_seconds ? (selectedIncident.mttr_seconds / 60).toFixed(1) + ' MINS' : 'N/A'}</span>
                  </p>
                </div>
              )}

            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center h-full">
              <div className="text-center">
                <Activity size={48} className="text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-slate-800">Awaiting Selection</h3>
                <p className="text-sm font-semibold text-slate-500 mt-1">Select an incident from the signal stream.</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
