import { Bell, ChevronDown, Clock3, Menu, RefreshCw, Search, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { modules } from '../data/navigation'
import type { DashboardSnapshot } from '../types/dashboard'

interface TopbarProps {
  activities: DashboardSnapshot['activities']
  onSearch: (value: string) => void
  search: string
  onOpenMobileNav: () => void
  title: string
  days: number
  onDaysChange: (days: number) => void
  onRefresh: () => void
  showRange: boolean
  mobileOpen: boolean
  apiConnected: boolean
  mode: 'api' | 'csv' | 'demo' | 'unavailable'
}

export function Topbar({ activities, onSearch, search, onOpenMobileNav, title, days, onDaysChange, onRefresh, showRange, mobileOpen, apiConnected, mode }: TopbarProps) {
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const matches = search.trim()
    ? modules.filter((item) => item.label.toLowerCase().includes(search.trim().toLowerCase()))
    : []

  return (
    <header className="topbar" onKeyDown={(event) => {
      if (event.key === 'Escape') { setNotificationsOpen(false); setSearchOpen(false) }
    }}>
      <div className="breadcrumb-area">
        <button id="mobile-nav-trigger" className="mobile-nav-trigger icon-button" aria-label="Open navigation" aria-expanded={mobileOpen} aria-controls="main-sidebar" onClick={onOpenMobileNav}><Menu size={19} /></button>
        <div className="breadcrumb"><span>Workspace</span><span className="breadcrumb-separator">/</span><strong>{title}</strong></div>
      </div>
      <div className="topbar-actions">
        <div className="search-wrap" onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setSearchOpen(false)
        }}>
          <label className="global-search">
            <Search size={16} aria-hidden="true" />
            <input
              aria-label={mode === 'csv' ? 'Search navigation or programmes' : 'Search navigation or pipeline executions'}
              onChange={(event) => { onSearch(event.target.value); setSearchOpen(true) }}
              onFocus={() => setSearchOpen(true)}
              onKeyDown={(event) => { if (event.key === 'Escape') setSearchOpen(false) }}
              placeholder="Search..."
              value={search}
            />
            {search && <button aria-label="Clear search" className="clear-search" onClick={() => { onSearch(''); setSearchOpen(false) }} type="button"><X size={14} /></button>}
          </label>
          {searchOpen && search.trim() && (
            <div className="search-results">
              <span className="search-hint">NAVIGATION</span>
              {matches.length ? matches.map((item) => (
                <Link key={item.path} to={item.path} onClick={() => { onSearch(''); setSearchOpen(false) }}>
                  <item.icon size={15} /> <span>{item.label}</span><span className="search-result-group">{item.group}</span>
                </Link>
              )) : <p>No matching pages</p>}
              <span className="search-hint search-hint-bottom">{mode === 'csv' ? 'On Overview, search also filters programmes.' : 'On Overview, search also filters pipeline executions.'}</span>
              <button className="close-results" onClick={() => setSearchOpen(false)}>Close</button>
            </div>
          )}
        </div>
        <span className={`environment-badge${apiConnected && mode !== 'csv' ? ' environment-badge-connected' : ''}`} title={mode === 'csv' ? 'CSV data stays in this browser' : apiConnected ? 'API database readiness check passed' : mode === 'unavailable' ? 'API data unavailable' : 'Showing synthetic preview data'}><span /> {mode === 'csv' ? 'Browser CSV' : apiConnected ? 'API connected' : mode === 'unavailable' ? 'API unavailable' : 'Demo preview'}</span>
        {showRange && <label className="range-select">
          <Clock3 size={15} aria-hidden="true" />
          <select aria-label="Chart date range" value={days} onChange={(event) => onDaysChange(Number(event.target.value))}>
            <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
          </select>
          <ChevronDown size={13} aria-hidden="true" />
        </label>}
        <button className="icon-button refresh-button" aria-label={mode === 'csv' ? 'Refresh public data' : mode === 'demo' ? 'Refresh demo data' : 'Refresh API data'} title={mode === 'csv' ? 'Refresh public data' : mode === 'demo' ? 'Refresh demo data' : 'Refresh API data'} onClick={onRefresh}><RefreshCw size={17} /></button>
        <div className="popover-anchor">
          <button aria-expanded={notificationsOpen} aria-label="Notifications" className="icon-button notification-button" onClick={() => setNotificationsOpen(!notificationsOpen)}>
            <Bell size={18} />
          </button>
          {notificationsOpen && <div className="topbar-popover notification-popover">
            <div className="popover-heading"><strong>Recent activity</strong><span>{mode === 'csv' ? 'NO EVENTS' : mode === 'demo' ? 'DEMO FEED' : 'API DATA'}</span></div>
            {activities.length ? activities.map((activity) => <div className="popover-activity" key={activity.id}><span className={`activity-dot activity-dot-${activity.tone}`} /><div><strong>{activity.title}</strong><span>{activity.time}</span></div></div>) : <p className="popover-empty">No activity recorded yet.</p>}
          </div>}
        </div>
      </div>
    </header>
  )
}
