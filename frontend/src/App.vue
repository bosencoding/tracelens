<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import AppIcon from './components/AppIcon.vue'

const route = useRoute()
const currentId = computed(() => (route.params.id as string) || '')
</script>

<template>
  <div class="flex min-h-screen flex-col bg-surface">
    <header class="no-print sticky top-0 z-40 border-b border-outline-variant bg-surface-lowest">
      <div class="mx-auto flex h-16 max-w-shell items-center justify-between gap-4 px-4 md:px-8">
        <RouterLink to="/" class="flex min-w-0 items-center gap-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-control bg-primary text-on-primary">
            <AppIcon name="fingerprint" :size="20" />
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-headline-sm tracking-tight">TraceLens</span>
              <span class="pill-neutral font-mono">#CAS-2025-089</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-1.5 w-1.5 rounded-full bg-success" />
              <span class="font-mono text-code-sm uppercase tracking-[0.08em] text-success">
                ENGINE: JPEG-SIGNATURE v2
              </span>
            </div>
          </div>
        </RouterLink>

        <nav class="flex items-center gap-1">
          <RouterLink
            to="/"
            class="flex items-center gap-2 rounded-control px-3 py-2 text-body-sm font-semibold transition"
            :class="
              route.name === 'upload'
                ? 'bg-surface-container-low text-primary'
                : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
            "
          >
            <AppIcon name="folder" :size="16" /> Unggah
          </RouterLink>
          <RouterLink
            v-if="currentId"
            :to="`/hasil/${currentId}`"
            class="flex items-center gap-2 rounded-control px-3 py-2 text-body-sm font-semibold transition"
            :class="
              route.name === 'result'
                ? 'bg-surface-container-low text-primary'
                : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
            "
          >
            <AppIcon name="scan" :size="16" /> Hasil
          </RouterLink>
          <RouterLink
            to="/pengaturan"
            class="flex items-center gap-2 rounded-control px-3 py-2 text-body-sm font-semibold transition"
            :class="
              route.name === 'settings'
                ? 'bg-surface-container-low text-primary'
                : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
            "
          >
            <AppIcon name="gear" :size="16" /> Pengaturan
          </RouterLink>
          <RouterLink
            v-if="currentId"
            :to="`/laporan/${currentId}`"
            class="flex items-center gap-2 rounded-control px-3 py-2 text-body-sm font-semibold transition"
            :class="
              route.name === 'report'
                ? 'bg-surface-container-low text-primary'
                : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
            "
          >
            <AppIcon name="doc" :size="16" /> Laporan
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto w-full max-w-shell flex-1 px-4 pb-16 pt-6 md:px-8">
      <RouterView />
    </main>

    <footer
      class="no-print border-t border-outline-variant bg-surface-lowest py-2 text-center font-mono text-code-sm text-on-surface-variant"
    >
      DATA SINTETIS — gambar contoh dibuat dengan Pillow; bukan identifikasi kamera nyata
    </footer>
  </div>
</template>

<style>
@media print {
  .no-print {
    display: none !important;
  }
  body {
    background: #ffffff !important;
  }
  main {
    max-width: none !important;
    padding: 0 !important;
  }
  .print-card {
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
  }
  .print-avoid-break {
    break-inside: avoid;
  }
}
</style>
