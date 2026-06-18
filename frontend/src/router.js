import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'generator',
    component: () => import('./views/Generator.vue'),
    meta: { title: '用户旅程地图生成器' },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('./views/History.vue'),
    meta: { title: '历史记录' },
  },
]

const router = createRouter({
  history: createWebHistory('/'),
  routes,
})

export default router
