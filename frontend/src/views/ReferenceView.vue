<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../api'
import type { ReferenceCamera } from '../types'

const cameras = ref<ReferenceCamera[]>([])
const loading = ref(true)
const error = ref('')
const search = ref('')
const expandedId = ref<string | null>(null)

const filtered = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return cameras.value
  return cameras.value.filter(
    (c) =>
      c.make.toLowerCase().includes(q) ||
      c.model.toLowerCase().includes(q) ||
      c.label.toLowerCase().includes(q)
  )
})

function toggle(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

// Normalize table values to 0-255 range for color
function normalizeValue(value: number, table: number[]) {
  const max = Math.max(...table, 1)
  return Math.floor((value / max) * 255)
}

// Generate color based on value (low=light, high=dark)
function getColor(value: number, table: number[]) {
  const normalized = normalizeValue(value, table)
  const intensity = Math.floor(255 - normalized * 0.7)
  return `rgb(${intensity}, ${intensity}, ${intensity + 10})`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.referenceCameras()
    cameras.value = data.cameras
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'gagal memuat data'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-6">
    <!-- Header -->
    <section class="card flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div class="flex min-w-0 items-center gap-2">
        <AppIcon name="grid" :size="20" class="text-primary" />
        <h1 class="text-title-md font-semibold">Tabel Kuantisasi Referensi</h1>
        <span class="font-mono text-label-sm tabular text-outline">({{ cameras.length }} kamera)</span>
      </div>
      <RouterLink to="/" class="btn-secondary text-label-sm">Kembali ke unggah</RouterLink>
    </section>

    <!-- Search -->
    <section v-if="!loading && !error" class="card px-4 py-3">
      <div class="flex items-center gap-3">
        <AppIcon name="search" :size="18" class="text-outline" />
        <input
          v-model="search"
          type="text"
          placeholder="Cari berdasarkan merek atau model..."
          class="flex-1 bg-transparent text-body-sm outline-none"
        />
        <span v-if="search" class="font-mono text-label-sm text-outline">
          {{ filtered.length }} dari {{ cameras.length }}
        </span>
      </div>
    </section>

    <!-- Loading -->
    <div v-if="loading" class="card p-8 text-center text-body-md text-on-surface-variant">
      Memuat tabel kuantisasi…
    </div>

    <!-- Error -->
    <div v-else-if="error" class="card border-danger-line bg-danger-soft p-6 text-body-sm text-danger">
      {{ error }}
    </div>

    <!-- Camera list -->
    <section v-else class="flex flex-col gap-3">
      <div v-if="filtered.length === 0" class="card p-8 text-center text-body-md text-on-surface-variant">
        Tidak ada kamera yang cocok dengan pencarian.
      </div>

      <div v-for="camera in filtered" :key="camera.id">
        <!-- Camera row -->
        <button
          @click="toggle(camera.id)"
          class="card w-full cursor-pointer px-4 py-3 text-left transition-colors hover:bg-surface-variant"
        >
          <div class="flex items-center gap-4">
            <!-- Mini heatmap preview -->
            <div class="flex gap-1">
              <div class="grid shrink-0 grid-cols-8 gap-px">
                <div
                  v-for="(v, i) in camera.luma_table.slice(0, 64)"
                  :key="i"
                  class="h-1.5 w-1.5"
                  :style="{ backgroundColor: getColor(v, camera.luma_table) }"
                />
              </div>
            </div>

            <!-- Camera info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-label-md">{{ camera.make }}</span>
                <span class="text-outline">•</span>
                <span class="truncate text-body-sm">{{ camera.model }}</span>
              </div>
              <div class="mt-1 flex items-center gap-2 text-body-sm text-on-surface-variant">
                <span class="font-mono tabular">{{ camera.subsampling }}</span>
                <span v-if="camera.note" class="truncate">— {{ camera.note }}</span>
              </div>
            </div>

            <!-- Expand indicator -->
            <AppIcon
              :name="expandedId === camera.id ? 'expand-less' : 'expand-more'"
              :size="20"
              class="text-outline"
            />
          </div>
        </button>

        <!-- Expanded tables -->
        <div v-if="expandedId === camera.id" class="card mt-1 p-6">
          <div class="grid gap-6 md:grid-cols-2">
            <!-- Luma table -->
            <div>
              <h3 class="mb-3 font-semibold text-label-md">Tabel Luma (Y)</h3>
              <div class="grid grid-cols-8 gap-px rounded border border-outline-variant bg-surface-variant p-1">
                <div
                  v-for="(v, i) in camera.luma_table"
                  :key="i"
                  class="aspect-square flex items-center justify-center font-mono text-label-xs tabular"
                  :style="{ backgroundColor: getColor(v, camera.luma_table) }"
                  :title="`${v}`"
                >
                  {{ v }}
                </div>
              </div>
              <p class="mt-2 text-body-xs text-on-surface-variant">
                Min: {{ Math.min(...camera.luma_table) }} • Max: {{ Math.max(...camera.luma_table) }}
              </p>
            </div>

            <!-- Chroma table -->
            <div>
              <h3 class="mb-3 font-semibold text-label-md">Tabel Kroma (Cb/Cr)</h3>
              <div class="grid grid-cols-8 gap-px rounded border border-outline-variant bg-surface-variant p-1">
                <div
                  v-for="(v, i) in camera.chroma_table"
                  :key="i"
                  class="aspect-square flex items-center justify-center font-mono text-label-xs tabular"
                  :style="{ backgroundColor: getColor(v, camera.chroma_table) }"
                  :title="`${v}`"
                >
                  {{ v }}
                </div>
              </div>
              <p class="mt-2 text-body-xs text-on-surface-variant">
                Min: {{ Math.min(...camera.chroma_table) }} • Max: {{ Math.max(...camera.chroma_table) }}
              </p>
            </div>
          </div>

          <!-- ID and note -->
          <div class="mt-4 flex items-center gap-2 text-body-xs text-on-surface-variant">
            <span class="font-mono">ID: {{ camera.id }}</span>
            <span v-if="camera.label">• {{ camera.label }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>