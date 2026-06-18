<template>
  <div v-if="v1 && v2" class="panel-card">
    <h3 class="compare-title">📊 V1 vs V2 量化对比</h3>
    <n-grid cols="3" x-gap="12">
      <n-gi>
        <n-statistic label="V1 阶段数" :value="v1.stages?.length || 0" />
      </n-gi>
      <n-gi>
        <n-statistic label="V2 阶段数" :value="v2.stages?.length || 0" />
      </n-gi>
      <n-gi>
        <n-statistic label="总耗时" :value="time ? time + 's' : '-'" />
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup>
defineProps({
  v1: Object,
  v2: Object,
  time: [String, Number],
})
</script>

<style scoped>
.compare-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 16px 0;
}
</style>
