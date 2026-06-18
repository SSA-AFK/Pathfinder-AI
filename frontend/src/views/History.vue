<template>
  <div class="history-page">
    <h2 class="history-title">生成历史</h2>
    <n-button v-if="items.length" size="small" @click="clearAll" type="error" ghost class="history-clear-btn">清空全部</n-button>

    <!-- Stats -->
    <div class="stats-row" v-if="items.length">
      <div class="stat-card">
        <span class="stat-value">{{ items.length }}</span>
        <span class="stat-label">总生成数</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ v2Percent }}%</span>
        <span class="stat-label">V2 占比</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ latestTime }}</span>
        <span class="stat-label">最近生成</span>
      </div>
    </div>

    <!-- Empty -->
    <n-empty v-if="!items.length" description="暂无生成记录" style="margin-top:80px;">
      <template #extra>
        <n-button type="primary" @click="$router.push('/')">前往生成器</n-button>
      </template>
    </n-empty>

    <!-- Table -->
    <n-data-table v-else :columns="columns" :data="items" :bordered="false" :single-line="false" />

    <!-- Detail modal -->
    <n-modal v-model:show="showDetail" title="旅程详情" :style="{ maxWidth: '680px' }" preset="card" size="huge">
      <template #header-extra>
        <n-tag :type="detailRecord?.mode === 'v2' ? 'info' : detailRecord?.mode === 'compare' ? 'warning' : 'default'" size="small">
          {{ detailRecord?.mode === 'compare' ? 'V1+V2 对比' : detailRecord?.mode === 'v2' ? 'V2 深度' : 'V1 快速' }}
        </n-tag>
      </template>
      <div v-if="detailRecord" class="detail-body">
        <div class="detail-meta">
          <span><strong>产品：</strong>{{ detailRecord.product }}</span>
          <span><strong>画像：</strong>{{ detailRecord.persona }}</span>
          <span><strong>时间：</strong>{{ detailRecord.time }}</span>
        </div>
        <p v-if="detailRecord.summary" class="detail-summary">{{ detailRecord.summary }}</p>
        <div class="detail-stages">
          <div
            v-for="(s, i) in (detailRecord.stages || [])"
            :key="i"
            class="detail-stage-card"
          >
            <div class="dsc-header">
              <span class="dsc-phase">{{ s.phase }}</span>
              <span class="dsc-score" :class="scoreClass(s.emotion_score)">
                {{ s.emotion_score }}/10
              </span>
            </div>
            <p class="dsc-behavior">{{ s.behavior }}</p>
            <div class="dsc-footer">
              <span class="dsc-label">痛点</span>
              <p class="dsc-value">{{ s.pain_point }}</p>
              <span class="dsc-label" style="margin-top:6px;">机会点</span>
              <p class="dsc-value">{{ s.opportunity }}</p>
            </div>
          </div>
        </div>
      </div>
      <n-empty v-else description="暂无详细数据" />
      <template #footer>
        <n-space>
          <n-button @click="refillFromDetail" type="primary" size="small">回填到生成器并重新生成</n-button>
          <n-button @click="showDetail = false" size="small">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useJourneyStore } from '../stores/journey.js'
import { getHistory, clearHistory } from '../composables/useStorage.js'
import { h } from 'vue'

const router = useRouter()
const store = useJourneyStore()
const items = ref(getHistory())

const showDetail = ref(false)
const detailRecord = ref(null)

const v2Percent = computed(() => {
  if (!items.value.length) return 0
  const v2Count = items.value.filter(i => i.mode === 'v2' || i.mode === 'compare').length
  return Math.round((v2Count / items.value.length) * 100)
})

const latestTime = computed(() => {
  return items.value.length ? items.value[0].time?.split(' ')[1] || '-' : '-'
})

function scoreClass(score) {
  if (score >= 8) return 'score-high'
  if (score >= 5) return 'score-mid'
  return 'score-low'
}

const columns = [
  { title: '产品', key: 'product', ellipsis: { tooltip: true }, width: 140 },
  { title: '画像', key: 'persona', ellipsis: { tooltip: true }, width: 200 },
  {
    title: '模式', key: 'mode', width: 90,
    render: (row) => {
      const label = row.mode === 'compare' ? '对比' : row.mode === 'v2' ? 'V2 深度' : 'V1 快速'
      const type = row.mode === 'compare' ? 'warning' : row.mode === 'v2' ? 'info' : 'default'
      return h('span', { class: ['n-tag', `n-tag--${type}-type`, 'n-tag--small-type'] }, label)
    },
  },
  { title: '阶段数', key: 'stagesCount', width: 80 },
  { title: '时间', key: 'time', width: 170 },
  {
    title: '操作', key: 'actions', width: 180,
    render: (row) => {
      return h('div', { style: { display: 'flex', gap: '8px' } }, [
        h('button', {
          onClick: () => viewDetail(row),
          style: { color: 'var(--brand)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px' },
        }, '查看详情'),
        h('button', {
          onClick: () => refill(row),
          style: { color: '#6B7280', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px' },
        }, '回填'),
      ])
    },
  },
]

function viewDetail(row) {
  detailRecord.value = row
  showDetail.value = true
}

function refill(row) {
  store.product = row.product || ''
  store.persona = row.persona || ''
  if (row.mode) store.strategy = row.mode
  router.push('/')
}

function refillFromDetail() {
  if (detailRecord.value) refill(detailRecord.value)
}

function clearAll() {
  clearHistory()
  items.value = []
}
</script>
