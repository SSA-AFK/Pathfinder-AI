<template>
  <div class="result-workspace">
    <!-- V2 结果 -->
    <div v-if="showV2" class="panel-card">
      <div class="result-header">
        <h3 class="result-title">V2 · 链式生成</h3>
        <n-space>
          <n-tag v-if="v2Cached" type="warning" size="small">⚡ 缓存 · 节省 ${{ v2SavedCost.toFixed(2) }}</n-tag>
          <n-button v-if="canUndo" size="tiny" text @click="$emit('undo')">↩ 回退</n-button>
        </n-space>
      </div>

      <div v-if="v2Data.summary" class="summary-card">{{ v2Data.summary }}</div>

      <div class="stage-list">
        <div v-for="(s, i) in v2Data.stages" :key="i" class="stage-item">
          <StageCard
            :stage="s" :index="i + 1" :editable="true"
            :highlight-fields="highlights[i] || []"
            :refining="refining === i"
            :all-scores="v2AllScores"
            @refine="(p) => $emit('refine', p)"
          />
        </div>
      </div>

      <div v-if="v2Mermaid" class="chart-panel">
        <MermaidChart :code="v2Mermaid" />
      </div>
    </div>

    <!-- V1 结果 -->
    <div v-if="showV1" class="panel-card">
      <div class="result-header">
        <h3 class="result-title">V1 · 单次调用</h3>
        <n-tag v-if="v1Cached" type="warning" size="small">⚡ 缓存 · 节省 ${{ v1SavedCost.toFixed(2) }}</n-tag>
      </div>

      <div class="stage-list">
        <div v-for="(s, i) in v1Data.stages" :key="i" class="stage-item">
          <StageCard
            :stage="s" :index="i + 1" :editable="false"
            :highlight-fields="(highlights || {})[i] || []"
            :all-scores="v1AllScores"
            @refine="(p) => $emit('v1refine', p)"
          />
        </div>
      </div>

      <div v-if="v1Mermaid" class="chart-panel">
        <MermaidChart :code="v1Mermaid" />
      </div>
    </div>

    <!-- 对比总结 -->
    <CompareSummary v-if="showV1 && showV2 && v1Data && v2Data" :v1="v1Data" :v2="v2Data" :time="totalTime" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StageCard from '../StageCard.vue'
import MermaidChart from '../MermaidChart.vue'
import CompareSummary from './CompareSummary.vue'

defineEmits(['refine', 'v1refine', 'undo'])

const props = defineProps({
  showV1: Boolean,
  showV2: Boolean,
  v1Data: Object,
  v2Data: Object,
  v1Cached: Boolean,
  v1SavedCost: Number,
  v2Cached: Boolean,
  v2SavedCost: Number,
  v1Mermaid: String,
  v2Mermaid: String,
  highlights: Object,
  refining: Number,
  canUndo: Boolean,
  totalTime: [String, Number],
  resultsReady: Boolean,
})

const v1AllScores = computed(() => props.v1Data?.stages?.map(s => s.emotion_score || 5) || [])
const v2AllScores = computed(() => props.v2Data?.stages?.map(s => s.emotion_score || 5) || [])
</script>

<style scoped>
.result-workspace { }
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.result-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}
</style>
