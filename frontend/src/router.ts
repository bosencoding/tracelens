import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'upload', component: () => import('./views/UploadView.vue') },
    { path: '/hasil/:id', name: 'result', component: () => import('./views/ResultView.vue') },
    { path: '/laporan/:id', name: 'report', component: () => import('./views/ReportView.vue') },
    { path: '/referensi', name: 'reference', component: () => import('./views/ReferenceView.vue') },
    { path: '/pengaturan', name: 'settings', component: () => import('./views/SettingsView.vue') },
    { path: '/:pathMatch(.*)*', name: 'missing', component: () => import('./views/NotFoundView.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
