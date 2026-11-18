const SESSION_KEY = 'impactflow-demo-signed-out'

export function isDemoSessionActive(storage: Pick<Storage, 'getItem'>): boolean {
  return storage.getItem(SESSION_KEY) !== 'true'
}

export function setDemoSessionActive(storage: Pick<Storage, 'setItem' | 'removeItem'>, active: boolean): void {
  if (active) storage.removeItem(SESSION_KEY)
  else storage.setItem(SESSION_KEY, 'true')
}

export { SESSION_KEY }
