<template>
  <n-card size="small" :bordered="true" class="stage-card" :class="{ 'stage-flash': isFlashing }" :style="{ borderLeftColor: barColor }">
    <!-- Header: index + phase + score + sparkline -->
    <template #header>
      <div class="stage-card-header">
        <div class="stage-card-header-left">
          <n-tag :bordered="false" size="tiny" :color="{ color: barColor, textColor: '#FFF' }">{{ index }}</n-tag>
          <span class="stage-phase">{{ stage.phase }}</span>
          <n-tag size="small" :bordered="false" :color="{ color: barColor + '20', textColor: barColor }">
            {{ localScore }}/10
          </n-tag>
          <span v-if="refining" class="stage-refining-spin">
            <n-spin size="tiny" />
          </span>
        </div>
        <!-- SVG 情绪曲线缩略图 -->
        <svg v-if="allScores && allScores.length > 1" class="sparkline" :viewBox="`0 0 ${sparkWidth} ${sparkHeight}`" width="80" height="28">
          <polyline
            :points="sparkPoints"
            fill="none"
            :stroke="barColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            opacity="0.6"
          />
          <polyline
            :points="sparkPoints"
            fill="url(#sparkGrad)"
            stroke="none"
            opacity="0.15"
          />
          <circle
            :cx="sparkDotX"
            :cy="sparkDotY"
            r="3"
            :fill="barColor"
            stroke="#fff"
            stroke-width="1.5"
          />
          <defs>
            <linearGradient :id="gradId" x1="0" x2="0" y1="1" y2="0">
              <stop offset="0%" :stop-color="barColor" stop-opacity="0" />
              <stop offset="100%" :stop-color="barColor" stop-opacity="0.4" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </template>

    <!-- Behavior (read-only) -->
    <div class="stage-field">
      <span class="field-label">行为</span>
      <span :class="['field-value', { 'field-highlight': highlightFields?.includes('behavior') }]">{{ stage.behavior }}</span>
    </div>

    <!-- Emotion: slider (editable) or bar (read-only) -->
    <div v-if="editable" class="stage-slider">
      <div class="slider-header">
        <span class="field-label">情绪评分</span>
      </div>
      <n-slider v-model:value="localScore" :min="1" :max="10" :step="1"
        @update:value="onSliderChange"
        :disabled="refining"
      />
      <div class="slider-range-labels">
        <span class="emotion-low">😞 1</span>
        <span>5</span>
        <span class="emotion-high">😊 10</span>
      </div>
    </div>
    <div v-else class="stage-emotion-bar">
      <span class="field-label">情绪评分</span>
      <div class="emotion-bar">
        <div class="emotion-bar-fill" :style="{ width: (localScore / 10) * 100 + '%', background: barColor }" />
      </div>
      <span class="emotion-bar-text">{{ localScore }}/10</span>
    </div>

    <!-- Pain point (editable vs read-only) -->
    <div class="stage-field">
      <span class="field-label pain-label">痛点</span>
      <template v-if="editable">
        <n-input
          v-model:value="localPainPoint"
          type="textarea"
          size="small"
          :autosize="{ minRows: 1, maxRows: 3 }"
          :disabled="refining"
          :class="{ 'field-highlight': highlightFields?.includes('pain_point') }"
          placeholder="编辑痛点..."
          @blur="onPainPointBlur"
        />
      </template>
      <span v-else :class="['field-value pain-value', { 'field-highlight': highlightFields?.includes('pain_point') }]">{{ stage.pain_point }}</span>
    </div>

    <!-- Opportunity (read-only) -->
    <div class="stage-field">
      <span class="field-label opp-label">机会点</span>
      <span :class="['field-value', { 'field-highlight': highlightFields?.includes('opportunity') }]">{{ stage.opportunity }}</span>
    </div>
  </n-card>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  stage: { type: Object, required: true },
  index: { type: Number, required: true },
  editable: { type: Boolean, default: false },
  highlightFields: { type: Array, default: () => [] },
  refining: { type: Boolean, default: false },
  allScores: { type: Array, default: () => [] },  // 所有阶段的情绪分数
})

const emit = defineEmits(['refine'])

const localScore = ref(props.stage.emotion_score || 5)
const localPainPoint = ref(props.stage.pain_point || '')
const isFlashing = ref(false)
const refineTimer = ref(null)

// Sync when stage changes externally
watch(() => props.stage.emotion_score, (v) => { localScore.value = v || 5 })
watch(() => props.stage.pain_point, (v) => { localPainPoint.value = v || '' })

// Color calculations
const cardBg = computed(() => {
  const s = localScore.value
  const t = (s - 1) / 9
  const r = Math.round(220 + (22 - 220) * t)
  const g = Math.round(38 + (163 - 38) * t)
  const b = Math.round(38 + (74 - 38) * t)
  return `rgba(${r},${g},${b},0.07)`
})

const barColor = computed(() => {
  const s = localScore.value
  return s >= 8 ? '#16A34A' : s >= 5 ? '#D97706' : '#DC2626'
})

// ─── SVG 缩略图参数 ───
const sparkWidth = 80
const sparkHeight = 28
const padX = 4
const padY = 5

const gradId = computed(() => 'sparkGrad-' + props.index)

const sparkPoints = computed(() => {
  if (!props.allScores?.length) return ''
  const xs = props.allScores.map((_, i) => {
    const x = padX + (i / Math.max(props.allScores.length - 1, 1)) * (sparkWidth - padX * 2)
    return Math.round(x * 10) / 10
  })
  const maxH = sparkHeight - padY * 2
  const ys = props.allScores.map(s => {
    const y = padY + ((10 - (s || 5)) / 9) * maxH
    return Math.round(y * 10) / 10
  })
  return xs.map((x, i) => `${x},${ys[i]}`).join(' ')
})

const sparkDotX = computed(() => {
  if (!props.allScores?.length) return 0
  return padX + ((props.index - 1) / Math.max(props.allScores.length - 1, 1)) * (sparkWidth - padX * 2)
})

const sparkDotY = computed(() => {
  const maxH = sparkHeight - padY * 2
  return padY + ((10 - localScore.value) / 9) * maxH
})

// Flash on highlight
watch(() => props.highlightFields, (fields) => {
  if (fields && fields.length) {
    isFlashing.value = true
    setTimeout(() => { isFlashing.value = false }, 2000)
  }
})

function triggerRefine() {
  if (!props.editable || props.refining) return
  if (refineTimer.value) clearTimeout(refineTimer.value)
  refineTimer.value = setTimeout(() => {
    emit('refine', {
      index: props.index - 1,
      new_emotion_score: localScore.value,
      new_pain_point: localPainPoint.value,
    })
  }, 500)
}

function onSliderChange() { triggerRefine() }
function onPainPointBlur() { triggerRefine() }

onBeforeUnmount(() => {
  if (refineTimer.value) clearTimeout(refineTimer.value)
})
</script>

<style scoped>
.stage-card {
  margin-bottom: 8px;
  border-left: 3px solid var(--border);
  transition: border-left-color 0.4s ease, box-shadow 0.4s ease;
}
.stage-card :deep(.n-card-header) {
  padding: 12px 16px 0;
}
.stage-card :deep(.n-card__content) {
  padding: 8px 16px 12px;
}
.stage-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.stage-card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stage-phase {
  font-weight: 600;
  font-size: 15px;
  color: var(--text);
}
.stage-refining-spin { margin-left: 4px; }
.stage-field { margin: 6px 0; }
.field-label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 2px;
  font-weight: 600;
}
.field-value { font-size: 13px; color: var(--text); line-height: 1.5; }
.pain-label { color: var(--amber); }
.pain-value { color: var(--amber); }
.opp-label { color: var(--teal); }
.stage-slider { margin: 8px 0; }
.slider-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px; }
.slider-range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}
.stage-emotion-bar { margin: 8px 0; }
.emotion-bar {
  height: 6px;
  border-radius: 3px;
  background: #E2E8F0;
  margin-top: 4px;
  overflow: hidden;
}
.emotion-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}
.emotion-bar-text { font-size: 12px; color: var(--text-secondary); }

.sparkline {
  flex-shrink: 0;
  margin-left: 12px;
  overflow: visible;
}
</style>
