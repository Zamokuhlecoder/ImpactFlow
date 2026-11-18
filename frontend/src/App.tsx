import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import { isDemoSessionActive, SESSION_KEY, setDemoSessionActive } from './demoSession'

export default function App() {
  const [session, setSession] = useState(() => {
    try {
      return { active: isDemoSessionActive(window.localStorage), storageError: false }
    } catch {
      return { active: true, storageError: true }
    }
  })

  useEffect(() => {
    function syncSession(event: StorageEvent) {
      if (event.key === SESSION_KEY || event.key === null) {
        setSession({ active: event.key === null || event.newValue !== 'true', storageError: false })
      }
    }
    window.addEventListener('storage', syncSession)
    return () => window.removeEventListener('storage', syncSession)
  }, [])

  function changeSession(active: boolean) {
    try {
      setDemoSessionActive(window.localStorage, active)
      setSession({ active, storageError: false })
    } catch {
      setSession({ active, storageError: true })
    }
  }

  return (
    <>
      {session.storageError && <div className="session-storage-warning" role="alert">Browser storage is unavailable. The demo session may not persist after a reload.</div>}
      {session.active ? <Routes>
        <Route element={<Dashboard onSignOut={() => changeSession(false)} />} path="*" />
      </Routes> : <main className="demo-welcome">
        <section className="demo-welcome-card">
          <div className="eyebrow"><span className="eyebrow-line" /> IMPACTFLOW / LOCAL WORKSPACE</div>
          <h1>See the bigger picture<span className="heading-period">.</span></h1>
          <p>Continue as the demo user to explore synthetic programme data and the shared ingestion workspace.</p>
          <button className="button button-primary" onClick={() => changeSession(true)} type="button">Continue as demo user</button>
          <p className="demo-welcome-note">This is a browser-only demo identity, not a secure sign-in. The API remains accessible without authentication. Use synthetic data locally only.</p>
        </section>
      </main>}
    </>
  )
}
