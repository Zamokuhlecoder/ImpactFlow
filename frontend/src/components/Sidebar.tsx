import { ChevronDown, ChevronLeft, ChevronsUpDown, Hexagon, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { navigationGroups } from '../data/navigation'

interface SidebarProps {
  collapsed: boolean
  mobileOpen: boolean
  onToggleCollapse: () => void
  onCloseMobile: () => void
}

export function Sidebar({ collapsed, mobileOpen, onToggleCollapse, onCloseMobile }: SidebarProps) {
  const [closedGroups, setClosedGroups] = useState<string[]>([])
  const showLabels = !collapsed || mobileOpen

  function toggleGroup(group: string) {
    setClosedGroups((current) => current.includes(group) ? current.filter((item) => item !== group) : [...current, group])
  }

  return (
    <>
      {mobileOpen && <button className="mobile-backdrop" aria-label="Close navigation overlay" onClick={onCloseMobile} />}
      <aside id="main-sidebar" className={`sidebar${collapsed ? ' sidebar-collapsed' : ''}${mobileOpen ? ' sidebar-mobile-open' : ''}`} aria-label="Sidebar" onKeyDown={(event) => { if (event.key === 'Escape' && mobileOpen) onCloseMobile() }}>
        <div className="brand-row">
          <div className="brand-mark" aria-hidden="true"><Hexagon size={24} strokeWidth={2.2} /><span>i</span></div>
          {showLabels && <div className="brand-text"><span className="brand-name">impact<span>flow</span></span><span className="brand-caption">DATA INTELLIGENCE</span></div>}
          <button className="sidebar-close mobile-only" aria-label="Close navigation" onClick={onCloseMobile}><X size={18} /></button>
          <button className="sidebar-collapse desktop-only" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={onToggleCollapse}>
            <ChevronLeft size={16} className={collapsed ? 'chevron-flipped' : ''} />
          </button>
        </div>

        {showLabels && <div className="organisation-card"><span className="organisation-avatar">IDF</span><span className="organisation-copy"><strong>Impact Development</strong><span>Foundation</span></span><ChevronsUpDown size={14} aria-hidden="true" /></div>}

        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigationGroups.map((group) => {
            const open = !closedGroups.includes(group.label)
            return (
              <section className="nav-group" key={group.label}>
                {showLabels && <button className="nav-group-toggle" aria-expanded={open} onClick={() => toggleGroup(group.label)}><span>{group.label}</span><ChevronDown size={13} className={open ? '' : 'group-closed'} /></button>}
                {(open || !showLabels) && group.items.map(({ label, icon: Icon, path }) => (
                  <NavLink
                    className={({ isActive }) => `nav-item${isActive ? ' nav-item-active' : ''}`}
                    end
                    key={path}
                    onClick={onCloseMobile}
                    to={path}
                    title={!showLabels ? label : undefined}
                    aria-label={label}
                  >
                    <Icon size={17} strokeWidth={1.7} />
                    {showLabels && <span>{label}</span>}
                  </NavLink>
                ))}
              </section>
            )
          })}
        </nav>
        <div className="sidebar-footer">
          <span className="user-avatar">TN</span>
          {showLabels && <div className="sidebar-user"><strong>Thandi Ndlovu</strong><span>Demo workspace</span></div>}
          {showLabels && <NavLink to="/settings" className="sidebar-settings" aria-label="Open workspace settings" onClick={onCloseMobile}><ChevronsUpDown size={15} /></NavLink>}
        </div>
      </aside>
    </>
  )
}
