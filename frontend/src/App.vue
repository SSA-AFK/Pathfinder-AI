<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <AppShell>
        <template #sider>
          <InputPanel />
        </template>
        <router-view />
      </AppShell>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import AppShell from './components/AppShell.vue'
import InputPanel from './components/generator/InputPanel.vue'

const themeOverrides = {
  common: {
    primaryColor: '#4F46E5',
    primaryColorHover: '#4338CA',
    borderRadius: '8px',
    fontFamily: "'DM Sans', system-ui, -apple-system, sans-serif",
  },
  Button: {
    borderRadiusMedium: '8px',
    fontWeight: '600',
  },
  Input: {
    borderRadius: '8px',
    heightLarge: '40px',
  },
  Card: {
    borderRadius: '12px',
  },
  Tag: {
    borderRadius: '6px',
  },
  Slider: {
    borderRadius: '4px',
  },
  DataTable: {
    borderRadius: '12px',
  },
}
</script>
