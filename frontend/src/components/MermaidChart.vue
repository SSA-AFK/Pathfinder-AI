<template>
  <div class="mermaid-chart">
    <div class="chart-header">
      <span class="chart-title">📈 情绪曲线</span>
      <n-space>
        <n-button size="tiny" text @click="copyCode">
          <template #icon>📋</template>
          复制源码
        </n-button>
        <n-button size="tiny" text @click="showCode = !showCode">
          {{ showCode ? '隐藏代码' : '查看源码' }}
        </n-button>
      </n-space>
    </div>

    <!-- Error state -->
    <n-alert v-if="renderError" type="warning" style="margin-bottom:12px;">
      图表渲染失败，请检查 Mermaid 语法。您仍然可以查看和复制源码。
    </n-alert>

    <!-- Rendered chart -->
    <div ref="chartEl" class="chart-area" />

    <!-- Source code (collapsible) -->
    <n-code v-if="showCode" :code="code" language="markdown" class="chart-code" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import mermaid from 'mermaid'

mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' })

const props = defineProps({ code: { type: String, default: '' } })
const chartEl = ref(null)
const showCode = ref(false)
const renderError = ref(false)
const message = useMessage()

async function render() {
  await nextTick()
  if (!chartEl.value || !props.code) return
  const id = 'mermaid-' + Math.random().toString(36).slice(2)
  chartEl.value.innerHTML = ''
  renderError.value = false
  try {
    const { svg } = await mermaid.render(id, props.code)
    chartEl.value.innerHTML = svg
  } catch {
    renderError.value = true
    chartEl.value.innerHTML = ''
  }
}

function copyCode() {
  try {
    navigator.clipboard.writeText(props.code)
    message.success('Mermaid 源码已复制')
  } catch {
    message.warning('复制失败，请手动选择')
  }
}

watch(() => props.code, render)
onMounted(() => { if (props.code) render() })
</script>

<style scoped>
.mermaid-chart { }
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}
.chart-area {
  display: flex;
  justify-content: center;
  overflow-x: auto;
}
.chart-code {
  margin-top: 12px;
}
</style>
