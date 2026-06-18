<template>
  <div class="sider-root">
    <!-- Logo 区 -->
    <div class="sider-logo">
      <span class="logo-name">JourneyMap</span>
      <n-tag type="info" size="small" :bordered="false">AI 驱动</n-tag>
    </div>

    <!-- 导航 -->
    <div class="sider-nav">
      <n-button text :type="$route.path === '/' ? 'primary' : 'default'" @click="$router.push('/')">
        <template #icon>✨</template>
        生成器
      </n-button>
      <n-button text :type="$route.path === '/history' ? 'primary' : 'default'" @click="$router.push('/history')">
        <template #icon>📋</template>
        历史记录
      </n-button>
    </div>

    <n-divider style="margin:0;" />

    <!-- 输入区（中部可滚） -->
    <div class="sider-form">
      <h2 class="form-title">用户旅程地图</h2>
      <p class="form-desc">输入产品与目标画像，AI 自动生成完整旅程地图</p>

      <n-space vertical size="medium" style="margin-top:20px;">
        <n-form-item label="产品名称" :show-feedback="false">
          <n-input v-model:value="store.product" placeholder="如：Airbnb、多邻国、Notion" size="large" :disabled="store.loading" />
        </n-form-item>
        <n-form-item label="目标用户画像" :show-feedback="false">
          <n-input v-model:value="store.persona" type="textarea" placeholder="如：25-35岁都市白领，追求高效协作" size="large" :autosize="{ minRows: 2, maxRows: 3 }" :disabled="store.loading" />
        </n-form-item>
        <n-form-item label="生成策略" :show-feedback="false">
          <n-select v-model:value="store.strategy" :options="strategyOptions" size="large" :disabled="store.loading" />
        </n-form-item>
      </n-space>
    </div>

    <!-- 底部固定：按钮 + 快捷示例 -->
    <div class="sider-footer">
      <n-button type="primary" block size="large" :loading="store.loading" @click="doGenerate" class="generate-btn">
        {{ store.loading ? store.loadingButtonText : '开始生成旅程地图' }}
      </n-button>

      <n-divider style="margin:12px 0;">快捷示例</n-divider>
      <n-space>
        <n-button v-for="ex in examples" :key="ex.label" size="small" :disabled="store.loading" @click="applyExample(ex)">
          {{ ex.label }}
        </n-button>
      </n-space>
    </div>
  </div>
</template>

<script setup>
import { useJourneyStore } from '../../stores/journey.js'
import { useJourney } from '../../composables/useJourney.js'

const store = useJourneyStore()
const { doGenerate } = useJourney()

const strategyOptions = [
  { label: 'V1 + V2 对比', value: 'compare' },
  { label: 'V1 单次调用（快速）', value: 'v1' },
  { label: 'V2 链式生成（深度）', value: 'v2' },
]

const examples = [
  { label: '🛌 潮汐睡眠', product: '潮汐睡眠', persona: '经常失眠的互联网从业者，28岁' },
  { label: '🦜 多邻国', product: '多邻国', persona: '零基础想学西班牙语的上班族' },
  { label: '📝 Notion', product: 'Notion', persona: '自由职业者，管理多个项目' },
]

function applyExample(ex) {
  store.product = ex.product
  store.persona = ex.persona
  doGenerate()
}
</script>

<style scoped>
.sider-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sider-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 24px 16px;
}
.logo-name {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 22px;
  font-weight: 800;
  color: var(--brand);
}
.sider-nav {
  display: flex;
  gap: 0;
  padding: 0 16px 12px;
}
.sider-form {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 0;
}
.form-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 4px 0;
}
.form-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}
.sider-footer {
  padding: 16px 24px 24px;
  flex-shrink: 0;
}
.generate-btn {
  height: 44px;
  font-size: 15px;
  font-weight: 700;
}
</style>
