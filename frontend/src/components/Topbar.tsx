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
}

export function Topbar({ activities, onSearch, search, onOpenMobileNav, title, days, onDaysChange, onRefresh, showRange, mobileOpen }: TopbarProps) {
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const matches = search.trim()
    ? modules.filter((item) => item.label.toLowerCase().includes(search.trim().toLowerCase()))
    : []

  return (
    <header className="topbar" onKeyDown={(event) => {
      if (event.key === 'Escape') { setNotificationsOpen(false); setAccountOpen(false); setSearchOpen(false) }
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
              aria-label="Search navigation or pipeline executions"
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
              <span className="search-hint search-hint-bottom">On Overview, search also filters pipeline executions.</span>
              <button className="close-results" onClick={() => setSearchOpen(false)}>Close</button>
            </div>
          )}
        </div>
        <span className="environment-badge" title="No live system health connection"><span /> Demo environment</span>
        {showRange && <label className="range-select">
          <Clock3 size={15} aria-hidden="true" />
          <select aria-label="Chart date range" value={days} onChange={(event) => onDaysChange(Number(event.target.value))}>
            <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option>
          </select>
          <ChevronDown size={13} aria-hidden="true" />
        </label>}
        <button className="icon-button refresh-button" aria-label="Refresh demo data" title="Refresh demo data" onClick={onRefresh}><RefreshCw size={17} /></button>
        <div className="popover-anchor">
          <button aria-expanded={notificationsOpen} aria-label="Notifications" className="icon-button notification-button" onClick={() => { setNotificationsOpen(!notificationsOpen); setAccountOpen(false) }}>
            <Bell size={18} /><span className="notification-dot" />
          </button>
          {notificationsOpen && <div className="topbar-popover notification-popover">
            <div className="popover-heading"><strong>Recent activity</strong><span>DEMO FEED</span></div>
            {activities.map((activity) => <div className="popover-activity" key={activity.id}><span className={`activity-dot activity-dot-${activity.tone}`} /><div><strong>{activity.title}</strong><span>{activity.time}</span></div></div>)}
          </div>}
        </div>
        <div className="popover-anchor">
          <button aria-expanded={accountOpen} aria-label="Account menu" className="account-button" onClick={() => { setAccountOpen(!accountOpen); setNotificationsOpen(false) }}>
            <span className="user-avatar">TN</span><span className="account-name">Thandi Ndlovu</span><ChevronDown size={14} />
          </button>
          {accountOpen && <div className="topbar-popover account-popover">
            <strong>Thandi Ndlovu</strong><span>Administrator · Demo workspace</span>
            <span className="popover-note">Authentication is not configured.</span>
            <Link to="/settings" onClick={() => setAccountOpen(false)}>Workspace settings</Link>
          </div>}
        </div>
      </div>
    </header>
  )
}
