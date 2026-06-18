import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useJourneyStore = defineStore('journey', () => {
  // ── Input ──
  const product = ref('')
  const persona = ref('')
  const strategy = ref('compare')

  // ── Loading ──
  const loading = ref(false)
  const loadingStep = ref(0)          // 0=idle, 1=分解阶段, 2=分析痛点, 3=绘制曲线, 4=汇总
  const errorMsg = ref('')
  const resultsReady = ref(false)
  const showThinking = ref(false)
  const v2Done = ref(false)

  // ── V1 ──
  const v1Data = ref(null)
  const v1Time = ref(0)
  const v1Cached = ref(false)
  const v1SavedCost = ref(0)
  const v1Mermaid = ref('')

  // ── V2 ──
  const v2Data = ref(null)
  const v2Time = ref(0)
  const v2Cached = ref(false)
  const v2SavedCost = ref(0)
  const v2Mermaid = ref('')
  const v2RawEvents = ref([])

  // ── Compare ──
  const totalTime = ref(0)

  // ── Refine ──
  const versionHistory = ref([])
  const diffHighlights = ref({})   // { stageIndex: ['emotion_score','pain_point',...] }
  const refiningIndex = ref(-1)     // -1 = idle, else stage index being refined
  const refineErrorByStage = ref({})

  // ── Computed ──
  const loadingButtonText = computed(() => {
    if (!loading.value) return '开始生成旅程地图'
    const labels = {
      0: '连接中...',
      1: '正在分解阶段(1/4)',
      2: '正在挖掘痛点(2/4)',
      3: '正在绘制情绪(3/4)',
      4: '生成完毕(4/4)',
    }
    return labels[loadingStep.value] || '生成中...'
  })

  const exportStages = computed(() => {
    if (strategy.value === 'v1') return v1Data.value?.stages || []
    return v2Data.value?.stages || []
  })

  const exportMermaid = computed(() => {
    if (strategy.value === 'v1') return v1Mermaid.value
    return v2Mermaid.value
  })

  // ── Actions ──
  function reset() {
    resultsReady.value = false
    errorMsg.value = ''
    showThinking.value = false
    v2Done.value = false
    loadingStep.value = 0
    v1Data.value = null
    v2Data.value = null
    v1Time.value = 0
    v2Time.value = 0
    totalTime.value = 0
    v2RawEvents.value = []
    v1Cached.value = false
    v1SavedCost.value = 0
    v2Cached.value = false
    v2SavedCost.value = 0
    v1Mermaid.value = ''
    v2Mermaid.value = ''
    versionHistory.value = []
    diffHighlights.value = {}
    refiningIndex.value = -1
    refineErrorByStage.value = {}
  }

  function pushVersionHistory(stages, summary, mermaid) {
    versionHistory.value = [{ stages, summary, mermaid_code: mermaid }, ...versionHistory.value].slice(0, 10)
  }

  function popVersionHistory() {
    return versionHistory.value.shift()
  }

  function setDiffHighlights(highlights) {
    diffHighlights.value = { ...highlights }
    // 2 秒后自动清除
    setTimeout(() => { diffHighlights.value = {} }, 2200)
  }

  return {
    product, persona, strategy,
    loading, loadingStep, errorMsg, resultsReady, showThinking, v2Done,
    v1Data, v1Time, v1Cached, v1SavedCost, v1Mermaid,
    v2Data, v2Time, v2Cached, v2SavedCost, v2Mermaid, v2RawEvents,
    totalTime, versionHistory, diffHighlights, refiningIndex, refineErrorByStage,
    loadingButtonText, exportStages, exportMermaid,
    reset, pushVersionHistory, popVersionHistory, setDiffHighlights,
  }
})
