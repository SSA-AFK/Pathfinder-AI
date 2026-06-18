import { ref } from 'vue'

const API_BASE = window.location.origin

export function useApi() {
  const loading = ref(false)
  const error = ref(null)

  async function post(endpoint, body) {
    loading.value = true
    error.value = null
    try {
      const resp = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${resp.status}`)
      }
      return await resp.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * SSE 流式消费：读取 POST 响应的 text/event-stream，每收到一个事件回调 onEvent。
   * 支持两种事件格式：
   *   {"step": N, "content": "...?", "data": {...}} ?????
   *   {"type": "done"|"error", ...} ???????
   * 返回完整的 done 结果（如果正常结束），或抛出错误。
   */
  async function postStream(endpoint, body, onEvent) {
    loading.value = true
    error.value = null
    let finalResult = null
    try {
      const resp = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${resp.status}`)
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              onEvent(event)
              if (event.type === 'done') finalResult = event.result
              if (event.type === 'error') throw new Error(event.message)
            } catch (e) {
              if (e.message && !e.message.startsWith('{') && e.message !== 'Unexpected') throw e
            }
          }
        }
      }
      return finalResult
    } catch (e) {
      if (typeof e.message === 'string' && !e.message.includes('JSON') && !e.message.startsWith('Unexpected')) {
        error.value = e.message
        throw e
      }
      error.value = String(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function postWithProgress(endpoint, body, onProgress) {
    loading.value = true
    error.value = null
    try {
      const resp = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${resp.status}`)
      }
      const data = await resp.json()
      if (data.traces && onProgress) {
        for (const trace of data.traces) {
          onProgress(trace)
        }
      }
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { loading, error, post, postStream, postWithProgress }
}
