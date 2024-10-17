import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue')
    },
    {
      path: '/insights',
      name: 'insights',
      component: () => import('../views/InsightsView.vue')
    },
    {
      path: '/account_open',
      name: 'account_open',
      component: () => import('../views/AccountOpenView.vue')
    },
    {
      path: '/trade_stock',
      name: 'trade_stock',
      component: () => import('../views/TradeStockView.vue')
    },
    {
      path: '/utilities',
      name: 'utilities',
      component: () => import('../views/UtilitiesView.vue')
    }
  ]
})

export default router
