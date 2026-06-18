<template>
  <n-layout style="height:100vh; overflow:hidden;">
    <n-layout has-sider style="height:100vh;">
      <n-layout-sider width="420" :collapsed-width="420" content-style="background:var(--sidebar-bg); border-right:1px solid var(--border); height:100vh; overflow:hidden;">
        <slot name="sider" />
      </n-layout-sider>
      <n-layout-content content-style="background:var(--bg); height:100vh;">
        <slot />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>
