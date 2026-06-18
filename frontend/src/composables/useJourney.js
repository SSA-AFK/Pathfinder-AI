import { useJourneyStore } from '../stores/journey.js'
import { useApi } from './useApi.js'
import { addHistory } from './useStorage.js'

function sanitizeMermaid(code) {
  if (!code) return ''
  return code.replace(/\\\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\"/g, '"')
}

export function useJourney() {
  const store = useJourneyStore()
  const { post, postStream } = useApi()

  async function doGenerate() {
    if (!store.product || !store.persona) {
      store.errorMsg = '请填写产品名称和用户画像'
      return
    }
    store.reset()
    store.loading = true

    const start = Date.now()
    try {
      if (store.strategy === 'v1') {
        store.loadingStep = 3
        const data = await post('/api/v1/generate', { product: store.product, persona: store.persona })
        store.v1Data = data
        store.v1Cached = data?.cached || false
        store.v1SavedCost = data?.saved_cost || 0
        store.v1Time = ((Date.now() - start) / 1000).toFixed(1)
        store.v1Mermaid = sanitizeMermaid(data?.mermaid_code)
        store.resultsReady = true
        store.loadingStep = 4
        addHistory({
          product: store.product, persona: store.persona,
          mode: 'v1', time: new Date().toLocaleString('zh-CN'),
          stagesCount: data?.stages?.length || 0,
          stages: data?.stages || [],
          summary: data?.summary || '',
          mermaid_code: data?.mermaid_code || store.v1Mermaid || '',
        })
      } else if (store.strategy === 'v2') {
        store.showThinking = true
        store.loadingStep = 1
        await postStream('/api/v2/generate', { product: store.product, persona: store.persona }, (event) => {
          if (event.content) {
            store.v2RawEvents = [...store.v2RawEvents, event]
            // Update loading step based on stream progress
            if (event.step === 2) store.loadingStep = 2
            if (event.step === 3) store.loadingStep = 3
          } else if (event.type === 'done') {
            store.v2Done = true
            store.loadingStep = 4
            store.v2Data = event.result
            store.v2Cached = event.cached || false
            store.v2SavedCost = event.saved_cost || 0
            store.v2Time = ((Date.now() - start) / 1000).toFixed(1)
            store.v2Mermaid = sanitizeMermaid(event.result?.mermaid_code)
            store.resultsReady = true
            addHistory({
              product: store.product, persona: store.persona,
              mode: 'v2', time: new Date().toLocaleString('zh-CN'),
              stagesCount: event.result?.stages?.length || 0,
              stages: event.result?.stages || [],
              summary: event.result?.summary || '',
              mermaid_code: event.result?.mermaid_code || '',
            })
          }
        })
      } else {
        store.showThinking = true
        store.loadingStep = 1
        const v1Promise = post('/api/v1/generate', { product: store.product, persona: store.persona })
        const v2Promise = postStream('/api/v2/generate', { product: store.product, persona: store.persona }, (event) => {
          if (event.content) {
            store.v2RawEvents = [...store.v2RawEvents, event]
            if (event.step === 2) store.loadingStep = Math.max(store.loadingStep, 2)
            if (event.step === 3) store.loadingStep = Math.max(store.loadingStep, 3)
          } else if (event.type === 'done') {
            store.v2Done = true
            store.loadingStep = 4
            store.v2Data = event.result
            store.v2Cached = event.cached || false
            store.v2SavedCost = event.saved_cost || 0
            store.v2Mermaid = sanitizeMermaid(event.result?.mermaid_code)
          }
        })
        const [d1] = await Promise.all([v1Promise, v2Promise])
        store.v1Data = d1
        store.v1Cached = d1?.cached || false
        store.v1SavedCost = d1?.saved_cost || 0
        store.v1Mermaid = sanitizeMermaid(d1?.mermaid_code)
        store.totalTime = ((Date.now() - start) / 1000).toFixed(1)
        store.resultsReady = true
        addHistory({
          product: store.product, persona: store.persona,
          mode: 'compare', time: new Date().toLocaleString('zh-CN'),
          stagesCount: (d1?.stages?.length || 0) + '+' + (store.v2Data?.stages?.length || '?'),
          stages: d1?.stages || [],
          summary: d1?.summary || '',
          mermaid_code: d1?.mermaid_code || '',
        })
      }
    } catch (e) {
      store.errorMsg = e.message || '生成失败'
    } finally {
      store.loading = false
    }
  }

  async function handleRefine({ index, new_emotion_score, new_pain_point }) {
    const curr = store.v2Data
    if (!curr?.stages) return
    if (store.refiningIndex >= 0) return // already refining

    // 保存旧数据用于 diff
    const oldStages = JSON.parse(JSON.stringify(curr.stages))
    const snapshot = {
      stages: oldStages,
      summary: curr.summary || '',
      mermaid_code: store.v2Mermaid,
    }
    store.pushVersionHistory(snapshot.stages, snapshot.summary, snapshot.mermaid_code)

    store.refiningIndex = index
    try {
      const data = await post('/api/v2/refine', {
        product: store.product, persona: store.persona,
        stages: curr.stages, modified_index: index,
        modified_emotion_score: new_emotion_score,
        modified_pain_point: new_pain_point,
      })
      // 计算差异
      const newStages = data?.stages || []
      const highlights = {}
      for (let i = 0; i < Math.min(oldStages.length, newStages.length); i++) {
        const changed = []
        if (oldStages[i].emotion_score !== newStages[i].emotion_score) changed.push('emotion_score')
        if (oldStages[i].pain_point !== newStages[i].pain_point) changed.push('pain_point')
        if (oldStages[i].opportunity !== newStages[i].opportunity) changed.push('opportunity')
        if (oldStages[i].behavior !== newStages[i].behavior) changed.push('behavior')
        if (changed.length) highlights[i] = changed
      }
      store.setDiffHighlights(highlights)

      store.v2Data = data
      store.v2Mermaid = sanitizeMermaid(data?.mermaid_code || '')
      return { ok: true }
    } catch (e) {
      store.refineErrorByStage = { ...store.refineErrorByStage, [index]: e.message }
      return { ok: false, error: e.message }
    } finally {
      store.refiningIndex = -1
    }
  }

  async function handleV1Refine({ index, new_emotion_score, new_pain_point }) {
    const stages = [...store.v1Data.stages]
    stages[index] = { ...stages[index], emotion_score: new_emotion_score, pain_point: new_pain_point }
    store.v1Data = { ...store.v1Data, stages }
  }

  function handleUndo() {
    const prev = store.popVersionHistory()
    if (!prev) return false
    store.v2Data = { ...store.v2Data, stages: prev.stages, summary: prev.summary }
    store.v2Mermaid = prev.mermaid_code
    return true
  }

  function buildMarkdown() {
    const stages = store.v2Data?.stages || store.v1Data?.stages || []
    const now = new Date().toLocaleString('zh-CN')
    let md = `# 用户旅程地图\n\n> **产品**：${store.product}  \n> **画像**：${store.persona}  \n> **时间**：${now}\n\n---\n\n## 旅程阶段\n\n| # | 阶段 | 行为 | 情绪 | 痛点 | 机会点 |\n|---|---|---|---|---|---|\n`
    stages.forEach((s, i) => {
      md += `| ${i + 1} | **${s.phase}** | ${s.behavior} | ${s.emotion_score}/10 | ${s.pain_point} | ${s.opportunity} |\n`
    })
    const mc = store.v2Mermaid || store.v1Mermaid
    if (mc) md += `\n## 情绪曲线\n\n\`\`\`mermaid\n${mc}\n\`\`\`\n`
    md += `\n---\n*由 JourneyMap AI 自动生成 · ${now}*\n`
    return md
  }

  function exportMD() {
    const blob = new Blob(['\uFEFF' + buildMarkdown()], { type: 'text/markdown;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `journey-${store.product || 'export'}-${Date.now()}.md`
    a.click()
    return true
  }

  async function exportPNG() {
    const { default: html2canvas } = await import('html2canvas')
    const el = document.getElementById('export-area')
    if (!el) throw new Error('未找到截图区域')
    const canvas = await html2canvas(el, { backgroundColor: '#F8FAFC', scale: 2, useCORS: true, logging: false })
    const barH = 36
    const nc = document.createElement('canvas')
    nc.width = canvas.width
    nc.height = canvas.height + barH
    const nctx = nc.getContext('2d')
    nctx.fillStyle = '#1E293B'
    nctx.fillRect(0, canvas.height, nc.width, barH)
    nctx.drawImage(canvas, 0, 0)
    nctx.fillStyle = '#F8FAFC'
    nctx.font = '12px "DM Sans", sans-serif'
    nctx.textAlign = 'center'
    nctx.fillText(`产品: ${store.product} | 画像: ${store.persona} | ${new Date().toLocaleString('zh-CN')}`, nc.width / 2, canvas.height + 24)
    nc.toBlob((blob) => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `journey-${store.product || 'export'}-${Date.now()}.png`
      a.click()
    }, 'image/png')
    return true
  }

  return {
    store,
    doGenerate, handleRefine, handleV1Refine, handleUndo,
    buildMarkdown, exportMD, exportPNG,
  }
}
