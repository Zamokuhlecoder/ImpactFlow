import { Component, type ErrorInfo, type ReactNode } from 'react'

export class ChartErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unable to render dashboard charts', error, info)
  }

  render() {
    if (this.state.failed) {
      return <div className="panel chart-error" role="alert"><strong>Dashboard charts could not be loaded.</strong><p>Reload the page to try again.</p><button className="button button-small" onClick={() => window.location.reload()}>Reload page</button></div>
    }
    return this.props.children
  }
}
