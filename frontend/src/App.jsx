import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Activity, Wind, CalendarDays, Clock3, RefreshCw, AlertCircle, ArrowUpRight, Moon, Sun } from 'lucide-react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './App.css'
import './dark.css'

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000' })
const fmt = (value, digits = 0) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits })
const localTime = (value) => value ? new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value)) : '—'

function App() {
  const [date, setDate] = useState('2026-01-15')
  const [cutoff, setCutoff] = useState(12)
  const [data, setData] = useState({ summary: null, generation: [], accuracy: null, history: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [darkMode, setDarkMode] = useState(() => window.localStorage.getItem('windsight-theme') === 'dark')

  useEffect(() => {
    window.localStorage.setItem('windsight-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    setData({ summary: null, generation: [], accuracy: null, history: [] })
    const params = { delivery_date: date, cutoff_hour: cutoff }
    Promise.all([
      api.get('/api/dashboard', { params }), api.get('/api/generation', { params }),
      api.get('/api/accuracy', { params }), api.get('/api/forecast-history', { params }),
    ]).then(([summary, generation, accuracy, history]) => {
      if (active) setData({ summary: summary.data, generation: generation.data.data, accuracy: accuracy.data, history: history.data.data })
    }).catch((err) => { if (active) setError(err.response?.data?.detail || 'Could not reach the Windsight API. Check that the backend is running.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [date, cutoff, refresh])

  const selectedHistory = useMemo(() => data.history.filter((row) => row.selected), [data.history])
  const metric = data.accuracy

  return <main className={`shell${darkMode ? ' theme-dark' : ''}`}>
    <header className="topbar">
      <a className="brand" href="#top"><span className="brand-mark"><Wind size={21} /></span><span>Windsight<span className="brand-dot">.</span></span></a>
      <div className="top-meta"><span className="live-dot" /> GB WIND · DAY-AHEAD PROCUREMENT</div>
      <button className="theme-toggle" type="button" onClick={() => setDarkMode((current) => !current)} aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'} title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>{darkMode ? <Sun size={17} /> : <Moon size={17} />}<span>{darkMode ? 'Light mode' : 'Dark mode'}</span></button>
    </header>
    <section className="intro" id="top">
      <div><div className="eyebrow">PERFORMANCE OVERVIEW <span> / </span> JANUARY 2026</div><h1>Forecast accuracy</h1><p>Compare the day-ahead wind forecast with metered generation.</p></div>
      <div className="filters">
        <label><CalendarDays size={16} /><span>Delivery date</span><input aria-label="Delivery date" type="date" value={date} onChange={(e) => setDate(e.target.value)} min="2026-01-01" max="2026-01-31" /></label>
        <label><Clock3 size={16} /><span>Decision cutoff</span><select aria-label="Decision cutoff" value={cutoff} onChange={(e) => setCutoff(Number(e.target.value))}>{Array.from({ length: 24 }, (_, hour) => <option key={hour} value={hour}>{String(hour).padStart(2, '0')}:00 UK</option>)}</select></label>
      </div>
    </section>
    {error && <div className="error-banner"><AlertCircle size={18} /><span>{error}</span><button onClick={() => setRefresh((value) => value + 1)} aria-label="Retry"><RefreshCw size={16} /></button></div>}
    <section className="stat-grid" aria-label="Daily summary">
      <Stat title="Forecast generation" value={data.summary?.forecast_generation_mw} unit="MW avg" icon={<Wind />} tone="blue" loading={loading} />
      <Stat title="Actual generation" value={data.summary?.actual_generation_mw} unit="MW avg" icon={<Activity />} tone="green" loading={loading} />
      <Stat title="Forecast error" value={data.summary?.forecast_error_mw} unit="MW avg" icon={<ArrowUpRight />} tone="amber" loading={loading} />
      <Stat title="WAPE" value={data.summary?.wape_percent} unit="%" icon={<Activity />} tone="violet" loading={loading} percent />
    </section>
    <section className="panel chart-panel">
      <div className="panel-head"><div><div className="eyebrow">HOURLY PERFORMANCE</div><h2>Forecast vs actual</h2><p>Aligned hourly generation · MW</p></div><div className="chart-note"><span className="green-dot" /> {date}</div></div>
      <div className="chart-wrap">{loading ? <div className="loading">Loading generation data…</div> : <ResponsiveContainer width="100%" height="100%"><LineChart data={data.generation} margin={{ top: 12, right: 18, left: 4, bottom: 4 }}>
        <CartesianGrid stroke={darkMode ? '#2b3a43' : '#e8edf1'} vertical={false} /><XAxis dataKey="startTime" tickFormatter={(v) => new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(v))} tickLine={false} axisLine={false} tick={{ fill: darkMode ? '#9aaab2' : '#81909c', fontSize: 11 }} interval={2} /><YAxis tickFormatter={(v) => `${Math.round(v / 1000)}k`} tickLine={false} axisLine={false} tick={{ fill: darkMode ? '#9aaab2' : '#81909c', fontSize: 11 }} width={42} /><Tooltip labelFormatter={localTime} formatter={(v, name) => [`${fmt(v)} MW`, name]} contentStyle={{ background: darkMode ? '#1a272e' : '#fff', color: darkMode ? '#e2e9ec' : '#20313d', border: `1px solid ${darkMode ? '#354750' : '#e4e9ed'}`, borderRadius: 10, boxShadow: '0 8px 24px #112a4012' }} /><Legend iconType="circle" wrapperStyle={{ paddingTop: 14, fontSize: 12, color: darkMode ? '#c0cbd0' : '#53656f' }} /><Line name="Forecast" dataKey="forecast" stroke="#4286c5" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls={false} /><Line name="Actual" dataKey="actual" stroke="#45a887" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} connectNulls={false} />
      </LineChart></ResponsiveContainer>}</div>
      <div className="chart-foot"><span>Delivery time · UK local</span><span>{data.summary?.valid_interval_count ?? 0} valid intervals</span></div>
    </section>
    <section className="lower-grid">
      <div className="panel accuracy-panel"><div className="panel-head compact"><div><div className="eyebrow">ERROR PROFILE</div><h2>Accuracy metrics</h2></div><span className="pill">{metric?.valid_interval_count ?? 0} matched</span></div>
        <div className="metric-grid"><Metric label="MAE" value={metric?.mae} unit="MW" hint="Average absolute error" /><Metric label="RMSE" value={metric?.rmse} unit="MW" hint="Weights larger errors" /><Metric label="Bias" value={metric?.bias} unit="MW" hint="+ over · − under forecast" /><Metric label="WAPE" value={metric?.wape} unit="%" hint="Error vs actual generation" percent /></div>
        <div className="data-quality">Missing intervals <strong>{metric?.missing_interval_count ?? '—'}</strong><span>of {metric?.total_interval_count ?? '—'} considered</span></div>
      </div>
      <div className="panel history-panel"><div className="panel-head compact"><div><div className="eyebrow">PUBLICATION AUDIT</div><h2>Selected forecasts</h2></div><span className="pill">{selectedHistory.length} selected</span></div>
        <div className="table-scroll history-scroll"><table><thead><tr><th>Published (UK)</th><th>Delivery</th><th>Forecast</th><th>Status</th></tr></thead><tbody>{data.history.length ? data.history.map((row) => <tr key={`${row.startTime}-${row.publishTime}`}><td>{localTime(row.publishTime)}</td><td>{localTime(row.startTime)}</td><td>{fmt(row.forecast)} <small>MW</small></td><td>{row.selected ? <span className="selected-badge">Selected</span> : <span className="later-badge">Revision</span>}</td></tr>) : <tr><td colSpan="4" className="empty">{loading ? 'Loading…' : 'No publication history'}</td></tr>}</tbody></table></div>
      </div>
    </section>
    <section className="panel detail-panel"><div className="panel-head compact"><div><div className="eyebrow">INTERVAL BREAKDOWN</div><h2>Hourly generation detail</h2></div><span className="unit-tag">MW</span></div>
      <div className="table-scroll"><table><thead><tr><th>Delivery interval (UK)</th><th>Forecast</th><th>Actual</th><th>Error</th></tr></thead><tbody>{loading ? <tr><td colSpan="4" className="empty">Loading interval data…</td></tr> : data.generation.length ? data.generation.map((row) => <tr key={row.startTime}><td>{localTime(row.startTime)}</td><td>{fmt(row.forecast)}</td><td>{fmt(row.actual)}</td><td className={row.error == null ? '' : row.error > 0 ? 'error-positive' : 'error-negative'}>{fmt(row.error)}</td></tr>) : <tr><td colSpan="4" className="empty">No intervals for this date.</td></tr>}</tbody></table></div>
    </section>
    <footer><span>WINDSIGHT <span className="brand-dot">·</span> GB WIND GENERATION</span><span>Source: Elexon FUELHH actuals · WINDFOR forecasts</span></footer>
  </main>
}

function Stat({ title, value, unit, icon, tone, loading, percent }) { return <article className={`stat-card ${tone}`}><div className="stat-top"><span>{title}</span><span className="stat-icon">{icon}</span></div><div className="stat-value">{loading ? <i className="skeleton" /> : fmt(value, 1)}<span>{unit}</span></div><div className="stat-caption">{percent ? 'Weighted absolute percentage error' : 'Daily mean across valid intervals'}</div></article> }
function Metric({ label, value, unit, hint, percent }) { return <div className="metric"><div className="metric-top"><span>{label}</span><small>{unit}</small></div><strong>{fmt(value, percent ? 2 : 1)}<small>{percent ? '%' : ''}</small></strong><p>{hint}</p></div> }

export default App
