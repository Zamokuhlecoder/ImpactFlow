import { ArrowDownRight, ArrowUpRight } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { animate, useMotionValue, useMotionValueEvent, useReducedMotion } from 'framer-motion'
import { useEffect, useState } from 'react'

interface KpiCardProps {
  label: string
  value: number
  suffix?: string
  description: string
  change: number
  icon: LucideIcon
  index: number
}

export function KpiCard({ label, value, suffix = '', description, change, icon: Icon, index }: KpiCardProps) {
  const reduceMotion = useReducedMotion()
  const motionValue = useMotionValue(reduceMotion ? value : 0)
  const [displayValue, setDisplayValue] = useState(reduceMotion ? value : 0)
  const decimals = suffix === '%' ? 1 : 0

  useMotionValueEvent(motionValue, 'change', setDisplayValue)

  useEffect(() => {
    if (reduceMotion) {
      motionValue.set(value)
      return
    }
    const controls = animate(motionValue, value, { duration: 0.7, ease: 'easeOut' })
    return () => controls.stop()
  }, [motionValue, reduceMotion, value])

  return (
    <article className="kpi-card entrance-card" style={{ animationDelay: `${index * 45}ms` }}>
      <div className="kpi-top"><span className="kpi-label">{label}</span><span className="kpi-icon"><Icon size={16} strokeWidth={1.8} /></span></div>
      <div className="kpi-value" aria-label={`${new Intl.NumberFormat('en-ZA', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value)}${suffix}`}>
        <span aria-hidden="true">{new Intl.NumberFormat('en-ZA', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(displayValue)}{suffix}</span>
      </div>
      <div className="kpi-bottom">
        <p className="kpi-description"><span className={`kpi-change${change < 0 ? ' kpi-change-negative' : ''}`}>{change < 0 ? <ArrowDownRight size={12} /> : <ArrowUpRight size={12} />}{change > 0 ? '+' : ''}{change.toFixed(1)}%</span> {description}</p>
        <svg className="sparkline" viewBox="0 0 64 24" fill="none" aria-hidden="true"><path d="M1 21 L11 16 L20 18 L29 10 L38 13 L47 6 L55 9 L63 2" transform={change < 0 ? 'translate(0 24) scale(1 -1)' : undefined} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </div>
    </article>
  )
}
