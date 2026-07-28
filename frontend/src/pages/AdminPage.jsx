import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import * as api from '../api'
import {
  ShieldCheck, Users, FileText, Key, Plus, UserCheck, UserX,
  FlaskConical, Database, RefreshCw, Activity, Server,
  BarChart3, Brains, Zap
} from 'lucide-react'
import { PageHeader, Stat, StatGrid, Loading, Panel } from '../components/ui'

const SCENARIOS = [
  { id: 'healthy',               label: 'Healthy',                desc: 'Baseline business metrics with steady growth.' },
  { id: 'declining_revenue',     label: 'Declining Revenue',      desc: 'Revenue contraction with profit margin compression.' },
  { id: 'high_churn',            label: 'High Churn Crisis',      desc: 'Severe employee turnover and retention failure.' },
  { id: 'forecast_uncertainty',  label: 'Forecast Uncertainty',   desc: 'Predictions become less accurate over time.' },
  { id: 'anomaly_spike',         label: 'Anomaly Spike',          desc: 'Unusual expense spikes and outlier detection.' },
  { id: 'seasonal_variance',     label: 'Seasonal Variance',      desc: 'Seasonal patterns (Q4 bump, Q1 dip).' },
  { id: 'recovery_mode',         label: 'Recovery Mode',          desc: 'Business recovering from previous decline.' },
]

const ROLES = ['admin', 'analyst', 'viewer', 'manager', 'executive']

export default function AdminPage() {
  const { user, hasPage } = useAuth()

  const [users, setUsers]       = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [rolesData, setRolesData] = useState({})
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState('users')

  // User creation form
  const [showForm, setShowForm]   = useState(false)
  const [newUser, setNewUser]     = useState({ username: '', password: 'REDACTED', full_name: '', role: 'viewer' })
  const [formError, setFormError] = useState('')
  const [formLoading, setFormLoading] = useState(false)

  // Scenario switcher
  const [activeScenario, setActiveScenario] = useState(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)
  const [scenarioMsg, setScenarioMsg]   = useState('')

  // Database info
  const [dbInfo, setDbInfo] = useState({})

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [u, a, r] = await Promise.allSettled([
        api.listUsers(),
        api.getAuditLog(150),
        api.listRoles(),
      ])
      if (u.status === 'fulfilled') setUsers(u.value.data?.users || u.value.data || [])
      if (a.status === 'fulfilled') setAuditLogs(a.value.data?.logs || a.value.data || [])
      if (r.status === 'fulfilled') setRolesData(r.value.data?.roles || {})
    } catch (err) {
      console.error('Failed to fetch admin data:', err)
    }
    setLoading(false)
  }, [])

  const fetchScenario = useCallback(async () => {
    try {
      const r = await api.getCurrentScenario()
      setActiveScenario(r.data?.current_scenario || 'healthy')
    } catch { /* ok */ }
  }, [])

  const fetchDbInfo = useCallback(async () => {
    try {
      const r = await api.getDatabaseInfo()
      setDbInfo(r.data || {})
    } catch { /* ok */ }
  }, [])

  useEffect(() => { 
    fetchData(); 
    fetchScenario();
    fetchDbInfo();
  }, [fetchData, fetchScenario, fetchDbInfo])

  const createUser = async (e) => {
    e.preventDefault(); setFormError(''); setFormLoading(true)
    try {
      await api.register(newUser.username, newUser.password, newUser.role)
      setShowForm(false)
      setNewUser({ username: '', password: 'REDACTED', full_name: '', role: 'viewer' })
      fetchData()
    } catch (err) { setFormError(err.response?.data?.detail || 'Failed to create user') }
    setFormLoading(false)
  }

  const toggleStatus = async (id, active) => {
    try { await api.updateUser(id, { is_active: !active }); fetchData() } catch { /* */ }
  }

  const changeRole = async (id, role) => {
    try { await api.updateUser(id, { role }); fetchData() } catch { /* */ }
  }

  const switchScenario = async (id) => {
    if (scenarioLoading) return
    setScenarioLoading(true); setScenarioMsg('')
    try {
      await api.switchScenario(id)
      setActiveScenario(id)
      setScenarioMsg(`✓ Switched to "${SCENARIOS.find(s => s.id === id)?.label}" — KPI data refreshed.`)
      fetchData() // Refresh data after scenario switch
    } catch (err) {
      setScenarioMsg(`✗ ${err.response?.data?.detail || 'Scenario switch failed'}`)
    }
    setScenarioLoading(false)
  }

  if (!hasPage('admin')) return <div className="text-center" style={{ padding: 60 }}>Access denied</div>
  if (loading) return <Loading />

  const active = users.filter(u => u.is_active !== false).length

  return (
    <div>
      <PageHeader icon={ShieldCheck} accent="var(--p-risk)" title="Administration"
        subtitle="Users, roles, audit trail, scenarios & database" />

      <StatGrid>
        <Stat label="Users" value={users.length} icon={Users} accent="var(--p-risk)" />
        <Stat label="Active" value={active} icon={UserCheck} accent="var(--ok)" />
        <Stat label="Disabled" value={users.length - active} icon={UserX} accent="var(--bad)" />
        <Stat label="Roles" value={new Set(users.map(u => u.role)).size} icon={Key} accent="var(--accent)" />
      </StatGrid>

      <div className="tab-bar" style={{ marginTop: 18 }}>
        <button className={tab === 'users'     ? 'active' : ''} onClick={() => setTab('users')}    ><Users     size={14} /> Users</button>
        <button className={tab === 'audit'     ? 'active' : ''} onClick={() => setTab('audit')}    ><FileText  size={14} /> Audit log</button>
        <button className={tab === 'roles'     ? 'active' : ''} onClick={() => setTab('roles')}    ><Key       size={14} /> Roles</button>
        <button className={tab === 'scenarios' ? 'active' : ''} onClick={() => setTab('scenarios')}><FlaskConical size={14} /> Scenarios</button>
        <button className={tab === 'database'  ? 'active' : ''} onClick={() => setTab('database')} ><Database  size={14} /> Database</button>
      </div>

      {/* ── Users ── */}
      {tab === 'users' && (
        <Panel title="User management" icon={Users}
          actions={<button className="btn btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : <><Plus size={14} /> New user</>}
          </button>}>

          {showForm && (
            <form onSubmit={createUser} style={{ background: 'var(--bg-2)', padding: 18, borderRadius: 'var(--r)', marginBottom: 18 }}>
              {formError && <div className="alert alert-danger" style={{ marginBottom: 12 }}>{formError}</div>}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 12 }}>
                <div className="form-group"><label className="form-label">Username</label>
                  <input className="form-input" value={newUser.username} onChange={e => setNewUser({ ...newUser, username: e.target.value })} required /></div>
                <div className="form-group"><label className="form-label">Full name</label>
                  <input className="form-input" value={newUser.full_name} onChange={e => setNewUser({ ...newUser, full_name: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Password</label>
                  <input className="form-input" type="password" value={newUser.password} onChange={e => setNewUser({ ...newUser, password: e.target.value })} required /></div>
                <div className="form-group"><label className="form-label">Role</label>
                  <select className="form-input" value={newUser.role} onChange={e => setNewUser({ ...newUser, role: e.target.value })}>
                    {ROLES.map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
                  </select></div>
              </div>
              <div style={{ marginTop: 12 }}>
                <button type="submit" className="btn btn-primary" disabled={formLoading}>
                  {formLoading ? 'Creating...' : 'Create user'}
                </button>
              </div>
            </form>
          )}

          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Full name</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>{u.full_name || '-'}</td>
                    <td>
                      <select className="form-input" style={{ padding: 4, fontSize: 12 }} value={u.role} onChange={e => changeRole(u.id, e.target.value)}>
                        {ROLES.map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
                      </select>
                    </td>
                    <td>
                      <span className={`badge ${u.is_active !== false ? 'badge-success' : 'badge-danger'}`}>
                        {u.is_active !== false ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td>
                      <button className="btn btn-sm" onClick={() => toggleStatus(u.id, u.is_active !== false)}>
                        {u.is_active !== false ? 'Disable' : 'Enable'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* ── Audit log ── */}
      {tab === 'audit' && (
        <Panel title="Audit log" icon={FileText}>
          <div style={{ maxHeight: 400, overflowY: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: 12 }}>{new Date(log.timestamp).toLocaleString()}</td>
                    <td>{log.username || '-'}</td>
                    <td>{log.action}</td>
                    <td style={{ fontSize: 12 }}>{log.details || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* ── Roles ── */}
      {tab === 'roles' && (
        <Panel title="Role permissions" icon={Key}>
          <div style={{ display: 'grid', gap: 12 }}>
            {ROLES.map(role => (
              <div key={role} style={{ 
                padding: 12, 
                background: 'var(--bg-2)', 
                borderRadius: 'var(--r)',
                border: '1px solid var(--line)'
              }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{role.charAt(0).toUpperCase() + role.slice(1)}</div>
                <div style={{ fontSize: 12, color: 'var(--dim)' }}>
                  {role === 'admin' && 'Full system access including user management'}
                  {role === 'executive' && 'High-level business intelligence access'}
                  {role === 'manager' && 'Team-level analytics and reporting'}
                  {role === 'analyst' && 'Data analysis and reporting tools'}
                  {role === 'viewer' && 'Read-only access to dashboards'}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {/* ── Scenarios ── */}
      {tab === 'scenarios' && (
        <Panel title="Data scenarios" icon={FlaskConical}
          subtitle="Switch between different business scenarios for testing and simulation">
          
          {scenarioMsg && (
            <div className={`alert ${scenarioMsg.startsWith('✓') ? 'alert-success' : 'alert-danger'}`} style={{ marginBottom: 12 }}>
              {scenarioMsg}
            </div>
          )}

          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--dim)', marginBottom: 8 }}>
              Current scenario: <strong>{SCENARIOS.find(s => s.id === activeScenario)?.label || 'Unknown'}</strong>
            </div>
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            {SCENARIOS.map(scenario => (
              <div key={scenario.id} style={{
                padding: 12,
                background: activeScenario === scenario.id ? 'var(--bg-3)' : 'var(--bg-2)',
                borderRadius: 'var(--r)',
                border: activeScenario === scenario.id ? '2px solid var(--accent)' : '1px solid var(--line)',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }} onClick={() => switchScenario(scenario.id)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <BarChart3 size={16} />
                  <div style={{ fontWeight: 600 }}>{scenario.label}</div>
                  {activeScenario === scenario.id && (
                    <span className="badge badge-success" style={{ marginLeft: 'auto' }}>Active</span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: 'var(--dim)', marginTop: 4 }}>{scenario.desc}</div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-2)', borderRadius: 'var(--r)' }}>
            <div style={{ fontSize: 11, color: 'var(--dim)' }}>
              <strong>Tip:</strong> Use different scenarios to test AgentKit's MCP tools with various business conditions. 
              Each scenario generates realistic KPI data patterns for finance, people, forecasting, and anomaly detection.
            </div>
          </div>
        </Panel>
      )}

      {/* ── Database ── */}
      {tab === 'database' && (
        <Panel title="Database information" icon={Database}>
          <div style={{ display: 'grid', gap: 12 }}>
            <div style={{ padding: 12, background: 'var(--bg-2)', borderRadius: 'var(--r)' }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Connection Status</div>
              <div style={{ fontSize: 12, color: 'var(--dim)' }}>
                {dbInfo.connected ? (
                  <span className="badge badge-success">Connected</span>
                ) : (
                  <span className="badge badge-danger">Disconnected</span>
                )}
              </div>
            </div>

            <div style={{ padding: 12, background: 'var(--bg-2)', borderRadius: 'var(--r)' }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Database Statistics</div>
              <div style={{ fontSize: 12, color: 'var(--dim)' }}>
                <div>Total KPI records: {dbInfo.total_records || 'N/A'}</div>
                <div>Categories: {dbInfo.categories || 'N/A'}</div>
                <div>Metric types: {dbInfo.metric_types || 'N/A'}</div>
                <div>Date range: {dbInfo.date_range || 'N/A'}</div>
              </div>
            </div>

            <div style={{ padding: 12, background: 'var(--bg-2)', borderRadius: 'var(--r)' }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>MCP Tool Data Access</div>
              <div style={{ fontSize: 12, color: 'var(--dim)' }}>
                <div>Finance KPIs: {dbInfo.finance_available ? '✓ Available' : '✗ Not available'}</div>
                <div>People KPIs: {dbInfo.people_available ? '✓ Available' : '✗ Not available'}</div>
                <div>Forecasting data: {dbInfo.forecast_available ? '✓ Available' : '✗ Not available'}</div>
                <div>Anomaly detection: {dbInfo.anomaly_available ? '✓ Available' : '✗ Not available'}</div>
              </div>
            </div>
          </div>
        </Panel>
      )}
    </div>
  )
}