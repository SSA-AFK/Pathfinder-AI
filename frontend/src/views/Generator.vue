<template>
  <div id="export-area" class="result-area">
    <!-- Error -->
    <n-alert v-if="store.errorMsg" type="error" closable @close="store.errorMsg = ''" class="result-error">
      <template #header>生成失败</template>
      {{ store.errorMsg }}
    </n-alert>

    <!-- Export bar (top-right of result area) -->
    <div v-if="store.resultsReady" class="export-bar">
      <n-space>
        <n-button size="small" text @click="handleExportMD">📄 导出 MD</n-button>
        <n-button size="small" text @click="handleExportPNG">🖼️ 导出图片</n-button>
      </n-space>
    </div>

    <!-- Empty state -->
    <div v-if="!store.resultsReady && !store.loading && !store.v2RawEvents.length" class="empty-state">
      <div class="empty-icon">✨</div>
      <h2 class="empty-title">配置左侧参数，开始绘制用户旅程</h2>
      <p class="empty-desc">支持 V1 快速预览、V2 链式深度生成和对比模式</p>
    </div>

    <!-- Loading skeleton -->
    <n-skeleton v-if="store.loading && !store.v2RawEvents.length && (store.strategy === 'v2' || store.strategy === 'compare')" text :repeat="4" style="margin-bottom:20px;" />

    <!-- Thinking timeline -->
    <ThinkingTimeline
      :visible="store.showThinking"
      :events="store.v2RawEvents"
      :all-done="store.v2Done || !store.loading"
    />

    <!-- V1 skeleton -->
    <n-skeleton v-if="store.loading && store.strategy === 'v1' && !store.v1Data" text :repeat="4" style="margin-bottom:12px;" />

    <!-- Results -->
    <ResultWorkspace
      :show-v1="store.strategy !== 'v2' && !!store.v1Data"
      :show-v2="store.strategy !== 'v1' && !!store.v2Data && (store.v2Done || store.strategy === 'v2' || !store.loading)"
      :v1-data="store.v1Data"
      :v2-data="store.v2Data"
      :v1-cached="store.v1Cached"
      :v1-saved-cost="store.v1SavedCost"
      :v2-cached="store.v2Cached"
      :v2-saved-cost="store.v2SavedCost"
      :v1-mermaid="store.v1Mermaid"
      :v2-mermaid="store.v2Mermaid"
      :highlights="store.diffHighlights"
      :refining="store.refiningIndex"
      :can-undo="store.versionHistory.length > 0"
      :total-time="store.totalTime"
      :results-ready="store.resultsReady"
      @refine="onRefine"
      @v1refine="onV1Refine"
      @undo="undo"
    />
  </div>
</template>

<script setup>
import { useJourney } from '../composables/useJourney.js'
import { useJourneyStore } from '../stores/journey.js'
import { useMessage } from 'naive-ui'
import ThinkingTimeline from '../components/generator/ThinkingTimeline.vue'
import ResultWorkspace from '../components/generator/ResultWorkspace.vue'

const store = useJourneyStore()
const { handleRefine, handleV1Refine, handleUndo, exportMD, exportPNG } = useJourney()
const message = useMessage()

async function onRefine(payload) {
  const result = await handleRefine(payload)
  if (result?.ok) message.success('纠偏完成')
  else if (result?.error) message.error('纠偏失败: ' + result.error)
}

function onV1Refine(payload) {
  handleV1Refine(payload)
  message.info('已本地修改 V1 阶段')
}

function undo() {
  if (handleUndo()) message.info('已回退到上一版')
}

function handleExportMD() {
  if (exportMD()) message.success('Markdown 已下载')
}

async function handleExportPNG() {
  try {
    await exportPNG()
    message.success('截图已下载')
  } catch (e) {
    message.error('截图失败')
  }
}
</script>
