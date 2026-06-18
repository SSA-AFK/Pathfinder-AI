const STORAGE_PREFIX = 'journey_'

export function getItem(key) {
  try { return JSON.parse(localStorage.getItem(STORAGE_PREFIX + key)) } catch { return null }
}
export function setItem(key, value) {
  try { localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value)) } catch {}
}
export function removeItem(key) {
  try { localStorage.removeItem(STORAGE_PREFIX + key) } catch {}
}

export function getHistory() { return getItem('history') || [] }
export function addHistory(entry) {
  let h = getHistory()
  // 去重：相同 product+persona 的记录只保留最新一条
  h = h.filter(e => !(e.product === entry.product && e.persona === entry.persona))
  h.unshift(entry)
  if (h.length > 20) h = h.slice(0, 20)
  setItem('history', h)
  return h
}
export function clearHistory() { removeItem('history') }

export function getApiKey() { return getItem('apikey') || '' }
export function setApiKey(key) { setItem('apikey', key) }
export function removeApiKey() { removeItem('apikey') }
