import { ref, nextTick } from 'vue'
import mermaid from 'mermaid'

mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' })

export function useMermaid() {
  const svg = ref('')
  const error = ref(null)

  async function render(code) {
    error.value = null
    svg.value = ''
    if (!code) return ''
    const id = 'mermaid-' + Math.random().toString(36).slice(2, 10)
    try {
      const { svg: result } = await mermaid.render(id, code)
      svg.value = result
      return result
    } catch (e) {
      error.value = e.message || '图表渲染失败'
      return ''
    }
  }

  function sanitizeCode(code) {
    if (!code) return ''
    return code
      .replace(/\\\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
  }

  return { svg, error, render, sanitizeCode }
}
