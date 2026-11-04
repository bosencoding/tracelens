<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
</script>

<template>
  <section class="card-hero mx-auto max-w-xl p-6 text-center" data-testid="not-found">
    <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-danger-soft text-danger">
      <AppIcon name="alert" :size="22" />
    </div>
    <h1 class="mt-3 text-headline-md">Halaman tidak ditemukan</h1>
    <p class="mt-2 text-body-sm text-on-surface-variant">
      Alamat <span class="font-mono text-on-surface">{{ route.fullPath }}</span> tidak ada di
      TraceLens. Rute yang tersedia: <span class="font-mono">/</span>,
      <span class="font-mono">/hasil/:id</span>, <span class="font-mono">/laporan/:id</span>.
    </p>
    <RouterLink to="/" class="btn-primary mt-5">Kembali ke unggah</RouterLink>
  </section>
</template>
