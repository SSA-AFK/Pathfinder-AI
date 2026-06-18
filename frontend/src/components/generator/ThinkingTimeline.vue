<template>
  <div v-if="visible" class="thinking-timeline">
    <n-card title="AI 思考过程" size="small" :bordered="true">
      <template #header-extra>
        <n-tag v-if="!allDone" type="warning" size="tiny">Streaming</n-tag>
        <n-tag v-else type="success" size="tiny">已完成</n-tag>
      </template>

      <n-timeline>
        <n-timeline-item
          v-for="step in steps"
          :key="step.id"
          :type="step.status === 'active' ? 'info' : step.status === 'done' ? 'success' : 'default'"
          :title="step.title"
          :content="step.content"
          :time="step.status === 'active' ? '处理中...' : step.status === 'done' ? '完成' : ''"
        />
      </n-timeline>

      <n-skeleton v-if="!allDone && events.length === 0" text :repeat="3" />
    </n-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  events: { type: Array, default: () => [] },
  allDone: { type: Boolean, default: false },
})

const stepNames = [
  { id: 1, title: '阶段拆解', label: '识别用户体验阶段' },
  { id: 2, title: '行为与痛点分析', label: '逐阶段分析用户行为与痛点' },
  { id: 3, title: '情绪曲线绘制', label: '评估情绪评分与机会点' },
  { id: 4, title: '汇总成图', label: '生成摘要与 Mermaid 图表' },
]

const steps = computed(() => {
  const last = props.events.length > 0 ? props.events[props.events.length - 1] : null
  const lastStep = last ? (last.step || 0) : 0

  return stepNames.map(s => {
    let status = 'pending'
    if (s.id < lastStep) status = 'done'
    else if (s.id === lastStep && !props.allDone) status = 'active'
    else if (s.id === lastStep && props.allDone) status = 'done'
    else status = 'pending'

    // Find matching event content
    const ev = props.events.find(e => e.step === s.id)
    const content = ev ? ev.content : s.label

    return { ...s, status, content }
  })
})
</script>

<style scoped>
.thinking-timeline {
  margin-bottom: 20px;
}
</style>
