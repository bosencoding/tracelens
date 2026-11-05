<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, ApiError } from '../api'
import type { Evidence } from '../types'

const router = useRouter()
const items = ref<Evidence[]>([])
const error = ref('')
const busy = ref(false)
const dragging = ref(false)
const loading = ref(true)
const limitMb = ref<number | null>(null)

const fmtSize = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(2)} MB` : `${Math.round(bytes / 1024)} KB`
const fmtDate = (iso: string) =>
  new Intl.DateTimeFormat('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Jakarta',
  }).format(new Date(iso))

const verdictClass = (label: string) =>
  label === 'kuat'
    ? 'pill-success'
    : label === 'sedang'
      ? 'pill-warning'
      : label === 'lemah'
        ? 'pill-danger'
        : 'pill-neutral'

const total = computed(() => items.value.length)

async function refresh() {
  try {
    const [list, settings] = await Promise.all([api.list(), api.settings()])
    items.value = list
    limitMb.value = settings.max_upload_mb
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'gagal memuat riwayat'
  } finally {
    loading.value = false
  }
}

function clientCheck(file: File): string | null {
  const okExt = /\.(jpe?g)$/i.test(file.name)
  const okType = ['image/jpeg', 'image/jpg'].includes(file.type)
  if (!okExt || !okType) return `"${file.name}" bukan JPEG. Hanya .jpg/.jpeg yang diterima.`
  if (limitMb.value !== null && file.size > limitMb.value * 1024 * 1024) {
    return `"${file.name}" ${fmtSize(file.size)} melebihi batas ${limitMb.value} MB.`
  }
  if (file.size === 0) return `"${file.name}" kosong.`
  return null
}

async function upload(file: File) {
  error.value = ''
  const problem = clientCheck(file)
  if (problem) {
    error.value = problem
    return
  }
  busy.value = true
  try {
    const detail = await api.upload(file)
    await router.push(`/hasil/${detail.id}`)
  } catch (e) {
    error.value =
      e instanceof ApiError ? `${e.message} (kode ${e.code})` : 'unggahan gagal, coba lagi.'
  } finally {
    busy.value = false
  }
}

function onPick(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) void upload(file)
  input.value = ''
}

function onDrop(event: DragEvent) {
  dragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) void upload(file)
}

async function remove(id: string) {
  error.value = ''
  try {
    await api.remove(id)
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'gagal menghapus'
  }
}

onMounted(refresh)
</script>

<template>
  <div class="flex flex-col gap-6">
    <section class="card-hero p-5 md:p-7">
      <span class="kicker text-[10px]">LANGKAH 1 — MASUKKAN BUKTI</span>
      <h1 class="mt-1 text-headline-xl-mobile tracking-tight md:text-headline-xl">
        Baca signature JPEG
      </h1>
      <p class="mt-2 max-w-2xl text-body-md text-on-surface-variant">
        Satu berkas JPEG membawa EXIF, dua tabel kuantisasi, dan jejak pipeline encoder. TraceLens
        membaca apa adanya dari byte berkas lalu membandingkannya dengan tiga profil referensi
        contoh.
      </p>

      <label
        class="mt-5 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-card border-2 border-dashed px-6 py-10 text-center transition"
        :class="
          dragging
            ? 'border-primary bg-surface-container-low'
            : 'border-outline-variant bg-surface-container-low/40 hover:border-primary/60'
        "
        data-testid="dropzone"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
      >
        <input
          type="file"
          accept=".jpg,.jpeg,image/jpeg"
          class="sr-only"
          data-testid="file-input"
          @change="onPick"
        />
        <AppIcon name="folder" :size="26" class="text-primary" />
        <span class="text-body-md font-semibold">
          {{ busy ? 'Membaca signature…' : 'Tarik JPEG ke sini atau klik untuk memilih' }}
        </span>
        <span class="font-mono text-code-sm text-on-surface-variant">
          .jpg / .jpeg · maksimal {{ limitMb ?? '…' }} MB · satu berkas
        </span>
        <span class="btn-primary pointer-events-none mt-2">Pilih berkas JPEG</span>
      </label>

      <p
        v-if="error"
        class="mt-3 rounded-control border border-danger-line bg-danger-soft px-3 py-2 text-body-sm text-danger"
        data-testid="upload-error"
      >
        {{ error }}
      </p>
    </section>

    <section class="card overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant px-4 py-3">
        <div>
          <span class="kicker text-[10px]">RIWAYAT BUKTI</span>
          <p class="text-body-md font-semibold">Daftar tersimpan</p>
        </div>
        <span class="pill-neutral font-mono">{{ total }} BERKAS</span>
      </div>

      <p v-if="loading" class="px-4 py-6 text-body-sm text-on-surface-variant">Memuat…</p>
      <p v-else-if="!total" class="px-4 py-6 text-body-sm text-on-surface-variant">
        Belum ada berkas. Jalankan <span class="font-mono">uv run python -m app.seed</span> untuk
        memuat 7 contoh sintetis.
      </p>

      <ul v-else>
        <li
          v-for="item in items"
          :key="item.id"
          class="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/60 px-4 py-3 last:border-0"
          :data-evidence="item.id"
        >
          <div class="flex min-w-0 flex-1 items-center gap-3">
            <img
              :src="api.thumbnailUrl(item.id)"
              alt=""
              loading="lazy"
              class="h-10 w-10 shrink-0 rounded border border-outline-variant object-cover"
              :data-thumb="item.id"
              @error="($event.target as HTMLImageElement).style.visibility = 'hidden'"
            />
            <div class="min-w-0">
              <RouterLink
                :to="`/hasil/${item.id}`"
                class="font-mono text-label-md font-semibold text-primary hover:underline"
              >
                {{ item.id }}
              </RouterLink>
            <p class="truncate text-body-sm">{{ item.filename }}</p>
              <p class="font-mono text-code-sm text-on-surface-variant">
                {{ fmtSize(item.byte_size) }} · {{ item.width }}×{{ item.height }} ·
                {{ fmtDate(item.uploaded_at) }}
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span :class="verdictClass(item.verdict_label)" class="font-mono uppercase">
              {{ item.verdict_label }}
            </span>
            <span class="font-mono text-label-sm tabular">
              {{ (item.confidence * 100).toFixed(1) }}%
            </span>
            <RouterLink :to="`/hasil/${item.id}`" class="btn-secondary h-9 px-3">
              <AppIcon name="arrow" :size="15" />
            </RouterLink>
            <button
              type="button"
              class="btn-secondary h-9 px-3 text-danger"
              :title="`Hapus ${item.id}`"
              :data-delete="item.id"
              @click="remove(item.id)"
            >
              <AppIcon name="close" :size="15" />
            </button>
          </div>
        </li>
      </ul>
    </section>

    <section class="card p-4">
      <span class="kicker text-[10px]">BATASAN METODE</span>
      <p class="mt-1 text-body-sm text-on-surface-variant">
        Tabel kuantisasi menandai pipeline encoder dengan andal; model kamera hanya bisa disebut
        bila cocok dengan tabel referensi. EXIF dapat dipalsukan dan tidak membuktikan asal berkas.
        Semua profil referensi di aplikasi ini adalah contoh sintetis, bukan data vendor nyata.
      </p>
    </section>
  </div>
</template>
