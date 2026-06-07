"use client";
import React, { useState, useEffect, useCallback } from "react";
import { Trash2, Plus, Link, Database, Key, RefreshCw, CheckCircle, XCircle } from "lucide-react";
import { IntegrationsApi, DataSource, Credential, Binding } from "@/app/(presentation-generator)/services/api/integrations";
import { notify } from "@/components/ui/sonner";

type Tab = "sources" | "credentials" | "bindings";

const DATA_SOURCE_TYPES = [
  { value: "rest", label: "REST API" },
  { value: "grafana", label: "Grafana" },
  { value: "prometheus", label: "Prometheus" },
  { value: "d_database", label: "D Database" },
  { value: "custom_http", label: "Custom HTTP" },
];

const CREDENTIAL_TYPES = [
  { value: "api_key", label: "API Key" },
  { value: "bearer", label: "Bearer Token" },
  { value: "basic", label: "Basic Auth" },
];

const DataConnections: React.FC = () => {
  const [tab, setTab] = useState<Tab>("sources");

  // Data Sources
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [dsLoading, setDsLoading] = useState(true);
  const [showDsForm, setShowDsForm] = useState(false);
  const [editingDs, setEditingDs] = useState<DataSource | null>(null);
  const [dsForm, setDsForm] = useState({ type: "rest", name: "", credential_ref: "", base_config_json: "" });

  // Credentials
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [credLoading, setCredLoading] = useState(true);
  const [showCredForm, setShowCredForm] = useState(false);
  const [credForm, setCredForm] = useState({ module: "rest", type: "api_key", label: "", secret_json: "" });

  // Bindings
  const [bindings, setBindings] = useState<Binding[]>([]);
  const [bndLoading, setBndLoading] = useState(true);
  const [showBndForm, setShowBndForm] = useState(false);
  const [bndForm, setBndForm] = useState({ presentation_id: "", datasource_id: "", alias: "", binding_config_json: "" });

  const loadDataSources = useCallback(async () => {
    setDsLoading(true);
    try {
      const data = await IntegrationsApi.listDataSources();
      setDataSources(data);
    } catch {
      // silent
    } finally {
      setDsLoading(false);
    }
  }, []);

  const loadCredentials = useCallback(async () => {
    setCredLoading(true);
    try {
      const data = await IntegrationsApi.listCredentials();
      setCredentials(data);
    } catch {
      // silent
    } finally {
      setCredLoading(false);
    }
  }, []);

  const loadBindings = useCallback(async () => {
    setBndLoading(true);
    try {
      const data = await IntegrationsApi.listBindings();
      setBindings(data);
    } catch {
      // silent
    } finally {
      setBndLoading(false);
    }
  }, []);

  useEffect(() => { loadDataSources(); }, [loadDataSources]);
  useEffect(() => { loadCredentials(); }, [loadCredentials]);
  useEffect(() => { loadBindings(); }, [loadBindings]);

  // ---- Data Source handlers ----
  const handleCreateDs = async () => {
    let baseConfig: Record<string, any> | undefined;
    if (dsForm.base_config_json.trim()) {
      try { baseConfig = JSON.parse(dsForm.base_config_json); } catch {
        notify.warning("Invalid JSON", "Base config must be valid JSON");
        return;
      }
    }
    try {
      await IntegrationsApi.createDataSource({
        type: dsForm.type,
        name: dsForm.name,
        credential_ref: dsForm.credential_ref || undefined,
        base_config: baseConfig,
      });
      notify.success("Data source added");
      setShowDsForm(false);
      setDsForm({ type: "rest", name: "", credential_ref: "", base_config_json: "" });
      loadDataSources();
    } catch (e: any) {
      notify.error("Failed", e?.message || "Could not create data source");
    }
  };

  const handleUpdateDs = async () => {
    if (!editingDs) return;
    let baseConfig: Record<string, any> | null | undefined = undefined;
    if (dsForm.base_config_json.trim()) {
      try { baseConfig = JSON.parse(dsForm.base_config_json); } catch {
        notify.warning("Invalid JSON", "Base config must be valid JSON");
        return;
      }
    }
    try {
      await IntegrationsApi.updateDataSource(editingDs.id, {
        type: dsForm.type,
        name: dsForm.name,
        credential_ref: dsForm.credential_ref || null,
        base_config: baseConfig,
      });
      notify.success("Data source updated");
      setEditingDs(null);
      setShowDsForm(false);
      setDsForm({ type: "rest", name: "", credential_ref: "", base_config_json: "" });
      loadDataSources();
    } catch (e: any) {
      notify.error("Failed", e?.message || "Could not update data source");
    }
  };

  const handleDeleteDs = async (id: string) => {
    try {
      const r = await IntegrationsApi.deleteDataSource(id);
      if (r.success) { notify.success("Data source deleted"); loadDataSources(); }
      else { notify.error("Failed", r.message || "Could not delete"); }
    } catch (e: any) {
      notify.error("Failed", e?.message || "Could not delete");
    }
  };

  const openEditDs = (ds: DataSource) => {
    setEditingDs(ds);
    setDsForm({
      type: ds.type,
      name: ds.name,
      credential_ref: ds.credential_ref || "",
      base_config_json: ds.base_config ? JSON.stringify(ds.base_config, null, 2) : "",
    });
    setShowDsForm(true);
  };

  // ---- Credential handlers ----
  const handleCreateCred = async () => {
    let secret: Record<string, any>;
    try { secret = JSON.parse(credForm.secret_json); } catch {
      notify.warning("Invalid JSON", "Secret must be valid JSON");
      return;
    }
    try {
      await IntegrationsApi.createCredential({
        module: credForm.module,
        type: credForm.type,
        label: credForm.label || undefined,
        secret,
      });
      notify.success("Credential saved (encrypted)");
      setShowCredForm(false);
      setCredForm({ module: "rest", type: "api_key", label: "", secret_json: "" });
      loadCredentials();
    } catch (e: any) {
      notify.error("Failed", e?.message || "Could not save credential");
    }
  };

  const handleDeleteCred = async (id: string) => {
    try {
      const r = await IntegrationsApi.deleteCredential(id);
      if (r.success) { notify.success("Credential deleted"); loadCredentials(); }
      else { notify.error("Failed", r.message || "Could not delete"); }
    } catch (e: any) {
      notify.error("Failed", e?.message || "Could not delete");
    }
  };

  // ---- Binding handlers ----
  const handleCreateBnd = async () => {
    let bindingConfig: Record<string, any> | undefined;
    if (bndForm.binding_config_json.trim()) {
      try { bindingConfig = JSON.parse(bndForm.binding_config_json); } catch {
        notify.warning("Invalid JSON", "Binding config must be valid JSON");
        return;
      }
    }
    try {
      await IntegrationsApi.createBinding({
        presentation_id: bndForm.presentation_id,
        datasource_id: bndForm.datasource_id,
        alias: bndForm.alias || undefined,
        binding_config: bindingConfig,
      });
      notify.success("Binding created");
      setShowBndForm(false);
      setBndForm({ presentation_id: "", datasource_id: "", alias: "", binding_config_json: "" });
      loadBindings();
    } catch (e: any) {
      notify.error("Failed", e?.message || "Could not create binding");
    }
  };

  const handleDeleteBnd = async (id: string) => {
    try {
      const r = await IntegrationsApi.deleteBinding(id);
      if (r.success) { notify.success("Binding deleted"); loadBindings(); }
      else { notify.error("Failed", r.message || "Could not delete"); }
    } catch (e: any) {
      notify.error("Failed", e?.message || "Could not delete");
    }
  };

  // ---- Styles ----
  const tabBtn = (t: Tab, label: string, icon: React.ReactNode) => (
    <button
      onClick={() => setTab(t)}
      className={`flex items-center gap-2 px-4 py-2.5 rounded-[8px] text-sm font-medium transition ${tab === t ? "bg-[#F4F3FF] text-[#5146E5] border border-[#D9D6FE]" : "text-[#6B7280] hover:text-[#374151] border border-transparent"}`}
    >
      {icon}
      {label}
    </button>
  );

  const cardClass = "rounded-[12px] border border-[#EDEEEF] bg-white p-5";
  const inputClass = "w-full rounded-[8px] border border-[#E5E7EB] px-3 py-2 text-sm text-[#1F2937] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#5146E5]/20 focus:border-[#5146E5]";
  const selectClass = "w-full rounded-[8px] border border-[#E5E7EB] px-3 py-2 text-sm text-[#1F2937] bg-white focus:outline-none focus:ring-2 focus:ring-[#5146E5]/20 focus:border-[#5146E5]";
  const btnPrimary = "inline-flex items-center gap-1.5 rounded-[8px] bg-[#5146E5] px-4 py-2 text-sm font-medium text-white hover:bg-[#4338CA] transition disabled:opacity-50";
  const btnSecondary = "inline-flex items-center gap-1.5 rounded-[8px] border border-[#E5E7EB] bg-white px-4 py-2 text-sm font-medium text-[#374151] hover:bg-[#F9FAFB] transition";
  const btnDanger = "p-1.5 rounded-[6px] text-[#9CA3AF] hover:text-[#EF4444] hover:bg-[#FEF2F2] transition";
  const badgeClass = "inline-block rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide";

  return (
    <div className="w-full max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h2 className="font-unbounded text-xl font-normal text-black">Data Connections</h2>
        <p className="mt-1 font-syne text-sm text-[#6B7280]">
          Configure external data sources (REST APIs, Grafana, Prometheus) and manage credentials for live data in presentations.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#EDEEEF] pb-2">
        {tabBtn("sources", "Data Sources", <Database className="w-4 h-4" />)}
        {tabBtn("credentials", "Credentials", <Key className="w-4 h-4" />)}
        {tabBtn("bindings", "Bindings", <Link className="w-4 h-4" />)}
      </div>

      {/* ==================== DATA SOURCES ==================== */}
      {tab === "sources" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-[#6B7280]">{dataSources.length} source{dataSources.length !== 1 ? "s" : ""} configured</p>
            <button onClick={() => { setEditingDs(null); setDsForm({ type: "rest", name: "", credential_ref: "", base_config_json: "" }); setShowDsForm(true); }} className={btnPrimary}>
              <Plus className="w-4 h-4" /> Add Source
            </button>
          </div>

          {showDsForm && (
            <div className={cardClass}>
              <h4 className="font-medium text-sm text-[#1F2937] mb-3">{editingDs ? "Edit Data Source" : "New Data Source"}</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Type</label>
                  <select value={dsForm.type} onChange={e => setDsForm(p => ({ ...p, type: e.target.value }))} className={selectClass}>
                    {DATA_SOURCE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Name</label>
                  <input value={dsForm.name} onChange={e => setDsForm(p => ({ ...p, name: e.target.value }))} placeholder="e.g. Production API" className={inputClass} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Credential ID (optional)</label>
                  <input value={dsForm.credential_ref} onChange={e => setDsForm(p => ({ ...p, credential_ref: e.target.value }))} placeholder="cred-xxxxxxxxxxxx" className={inputClass} />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">
                    {dsForm.type === "grafana" ? "Dashboard UID / Config (JSON)" : "Base Config (JSON, optional)"}
                  </label>
                  <textarea rows={3} value={dsForm.base_config_json} onChange={e => setDsForm(p => ({ ...p, base_config_json: e.target.value }))}
                    placeholder={
                      dsForm.type === "grafana"
                        ? '{"dashboard_uid": "abc123def", "base_url": "https://grafana.example.com"}'
                        : dsForm.type === "rest"
                          ? '{"base_url": "https://api.example.com", "headers": {"X-Custom": "value"}}'
                          : dsForm.type === "prometheus"
                            ? '{"base_url": "https://prometheus.example.com"}'
                            : '{}'
                    }
                    className={`${inputClass} font-mono text-xs`} />
                  {dsForm.type === "grafana" && (
                    <p className="text-[10px] text-[#9CA3AF] mt-1">
                      Grafana data source fetches all panels from the given dashboard. Include <code>dashboard_uid</code> (required) and optionally <code>base_url</code>.
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <button onClick={editingDs ? handleUpdateDs : handleCreateDs} className={btnPrimary}>{editingDs ? "Update" : "Create"}</button>
                <button onClick={() => { setShowDsForm(false); setEditingDs(null); }} className={btnSecondary}>Cancel</button>
              </div>
            </div>
          )}

          {dsLoading ? (
            <div className="flex items-center gap-2 text-sm text-[#9CA3AF]"><RefreshCw className="w-4 h-4 animate-spin" /> Loading...</div>
          ) : dataSources.length === 0 ? (
            <div className={`${cardClass} text-center text-sm text-[#9CA3AF]`}>No data sources configured yet.</div>
          ) : (
            <div className="space-y-2">
              {dataSources.map(ds => (
                <div key={ds.id} className={`${cardClass} flex items-start justify-between`}>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-[#1F2937]">{ds.name}</span>
                      <span className={badgeClass} style={{ background: ds.type === "rest" ? "#DBEAFE" : ds.type === "grafana" ? "#FEF3C7" : "#F3E8FF", color: ds.type === "rest" ? "#1D4ED8" : ds.type === "grafana" ? "#92400E" : "#7C3AED" }}>{ds.type}</span>
                    </div>
                    <div className="text-xs text-[#9CA3AF] font-mono">{ds.id}</div>
                    {ds.base_config && <div className="text-xs text-[#6B7280] font-mono mt-1 max-h-16 overflow-y-auto bg-[#F9FAFB] rounded p-1.5"><pre className="whitespace-pre-wrap">{JSON.stringify(ds.base_config, null, 2)}</pre></div>}
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => openEditDs(ds)} className="p-1.5 rounded-[6px] text-[#9CA3AF] hover:text-[#5146E5] hover:bg-[#F4F3FF] transition" title="Edit"><svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg></button>
                    <button onClick={() => handleDeleteDs(ds.id)} className={btnDanger} title="Delete"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ==================== CREDENTIALS ==================== */}
      {tab === "credentials" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-[#6B7280]">{credentials.length} credential{credentials.length !== 1 ? "s" : ""} stored</p>
            <button onClick={() => { setCredForm({ module: "rest", type: "api_key", label: "", secret_json: "" }); setShowCredForm(true); }} className={btnPrimary}>
              <Plus className="w-4 h-4" /> Add Credential
            </button>
          </div>

          {showCredForm && (
            <div className={cardClass}>
              <h4 className="font-medium text-sm text-[#1F2937] mb-3">New Credential</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Module</label>
                  <select value={credForm.module} onChange={e => setCredForm(p => ({ ...p, module: e.target.value }))} className={selectClass}>
                    {DATA_SOURCE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Type</label>
                  <select value={credForm.type} onChange={e => setCredForm(p => ({ ...p, type: e.target.value }))} className={selectClass}>
                    {CREDENTIAL_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Label (optional)</label>
                  <input value={credForm.label} onChange={e => setCredForm(p => ({ ...p, label: e.target.value }))} placeholder="Production Token" className={inputClass} />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Secret (JSON)</label>
                  <textarea rows={3} value={credForm.secret_json} onChange={e => setCredForm(p => ({ ...p, secret_json: e.target.value }))} placeholder='{"api_key": "sk-xxx"}' className={`${inputClass} font-mono text-xs`} />
                  <p className="text-[10px] text-[#9CA3AF] mt-1">Secrets are encrypted with AES-256-GCM before storage. The raw value is never stored.</p>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <button onClick={handleCreateCred} className={btnPrimary}>Save Credential</button>
                <button onClick={() => setShowCredForm(false)} className={btnSecondary}>Cancel</button>
              </div>
            </div>
          )}

          {credLoading ? (
            <div className="flex items-center gap-2 text-sm text-[#9CA3AF]"><RefreshCw className="w-4 h-4 animate-spin" /> Loading...</div>
          ) : credentials.length === 0 ? (
            <div className={`${cardClass} text-center text-sm text-[#9CA3AF]`}>No credentials stored yet.</div>
          ) : (
            <div className="space-y-2">
              {credentials.map(c => (
                <div key={c.id} className={`${cardClass} flex items-center justify-between`}>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-[#1F2937]">{c.label || c.id}</span>
                      <span className={badgeClass} style={{ background: c.status === "active" ? "#D1FAE5" : "#FEE2E2", color: c.status === "active" ? "#065F46" : "#991B1B" }}>
                        {c.status === "active" ? <CheckCircle className="w-3 h-3 inline mr-0.5" /> : <XCircle className="w-3 h-3 inline mr-0.5" />}
                        {c.status}
                      </span>
                      <span className={badgeClass} style={{ background: "#DBEAFE", color: "#1D4ED8" }}>{c.module}/{c.type}</span>
                    </div>
                    <div className="text-xs text-[#9CA3AF] font-mono">{c.id} &middot; fingerprint: {c.fingerprint}</div>
                  </div>
                  <button onClick={() => handleDeleteCred(c.id)} className={btnDanger} title="Delete"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ==================== BINDINGS ==================== */}
      {tab === "bindings" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-[#6B7280]">{bindings.length} binding{bindings.length !== 1 ? "s" : ""} configured</p>
            <button onClick={() => { setBndForm({ presentation_id: "", datasource_id: "", alias: "", binding_config_json: "" }); setShowBndForm(true); }} className={btnPrimary}>
              <Plus className="w-4 h-4" /> Add Binding
            </button>
          </div>

          {showBndForm && (
            <div className={cardClass}>
              <h4 className="font-medium text-sm text-[#1F2937] mb-3">New Binding</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Presentation ID</label>
                  <input value={bndForm.presentation_id} onChange={e => setBndForm(p => ({ ...p, presentation_id: e.target.value }))} placeholder="UUID of the presentation" className={inputClass} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Data Source ID</label>
                  <select value={bndForm.datasource_id} onChange={e => setBndForm(p => ({ ...p, datasource_id: e.target.value }))} className={selectClass}>
                    <option value="">Select...</option>
                    {dataSources.map(ds => <option key={ds.id} value={ds.id}>{ds.name} ({ds.type})</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Alias (optional)</label>
                  <input value={bndForm.alias} onChange={e => setBndForm(p => ({ ...p, alias: e.target.value }))} placeholder="e.g. sales-data" className={inputClass} />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-[#6B7280] mb-1">Binding Config (JSON, optional)</label>
                  <textarea rows={2} value={bndForm.binding_config_json} onChange={e => setBndForm(p => ({ ...p, binding_config_json: e.target.value }))} placeholder='{"refresh_interval_seconds": 300}' className={`${inputClass} font-mono text-xs`} />
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <button onClick={handleCreateBnd} className={btnPrimary}>Create Binding</button>
                <button onClick={() => setShowBndForm(false)} className={btnSecondary}>Cancel</button>
              </div>
            </div>
          )}

          {bndLoading ? (
            <div className="flex items-center gap-2 text-sm text-[#9CA3AF]"><RefreshCw className="w-4 h-4 animate-spin" /> Loading...</div>
          ) : bindings.length === 0 ? (
            <div className={`${cardClass} text-center text-sm text-[#9CA3AF]`}>No bindings configured yet.</div>
          ) : (
            <div className="space-y-2">
              {bindings.map(b => (
                <div key={b.id} className={`${cardClass} flex items-center justify-between`}>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Link className="w-3.5 h-3.5 text-[#5146E5]" />
                      <span className="font-medium text-sm text-[#1F2937]">{b.alias || b.id}</span>
                      <span className="text-xs text-[#9CA3AF]">Presentation: {b.presentation_id.slice(0, 8)}...</span>
                      <span className="text-xs text-[#9CA3AF]">Source: {b.datasource_id}</span>
                    </div>
                    {b.binding_config && <div className="text-xs text-[#6B7280] font-mono"><pre className="whitespace-pre-wrap">{JSON.stringify(b.binding_config, null, 2)}</pre></div>}
                  </div>
                  <button onClick={() => handleDeleteBnd(b.id)} className={btnDanger} title="Delete"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DataConnections;
