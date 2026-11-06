<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, ApiError } from '../api'
import type { Evidence, ReferenceStats } from '../types'

interface QueueItem {
  file: File
  status: 'pending' | 'uploading' | 'success' | 'failed'
  evidenceId?: string
  error?: string
  thumbnailUrl?: string
}

const router = useRouter()
const items = ref<Evidence[]>([])
const error = ref('')
const busy = ref(false)
const dragging = ref(false)
const loading = ref(true)
const limitMb = ref<number | null>(null)
const brokenThumbs = ref<Set<string>>(new Set())
const queue = ref<QueueItem[]>([])
const referenceStats = ref<ReferenceStats | null>(null)

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
const queueCount = computed(() => queue.value.length)
const queueSuccess = computed(() => queue.value.filter(q => q.status === 'success').length)
const queueFailed = computed(() => queue.value.filter(q => q.status === 'failed').length)
const lastUploadedId = computed(() => {
  const success = queue.value.filter(q => q.status === 'success' && q.evidenceId)
  return success.length > 0 ? success[success.length - 1].evidenceId : null
})

async function refresh() {
  try {
    const [list, settings, stats] = await Promise.all([
      api.list(),
      api.settings(),
      api.getReferenceStats(),
    ])
    items.value = list
    limitMb.value = settings.max_upload_mb
    referenceStats.value = stats
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

function addFiles(fileList: FileList | File[]) {
  error.value = ''
  const files = Array.from(fileList)
  
  if (queue.value.length + files.length > 50) {
    error.value = `Maksimal 50 berkas per batch. Saat ini ${queue.value.length} berkas dalam antrian.`
    return
  }
  
  for (const file of files) {
    const problem = clientCheck(file)
    if (problem) {
      queue.value.push({
        file,
        status: 'failed',
        error: problem,
      })
      continue
    }
    
    // Create thumbnail preview
    const thumbnailUrl = URL.createObjectURL(file)
    queue.value.push({
      file,
      status: 'pending',
      thumbnailUrl,
    })
  }
}

function removeFromQueue(index: number) {
  const item = queue.value[index]
  if (item.thumbnailUrl) {
    URL.revokeObjectURL(item.thumbnailUrl)
  }
  queue.value.splice(index, 1)
}

function clearQueue() {
  for (const item of queue.value) {
    if (item.thumbnailUrl) {
      URL.revokeObjectURL(item.thumbnailUrl)
    }
  }
  queue.value = []
}

async function uploadAll() {
  if (queue.value.length === 0) return
  
  error.value = ''
  busy.value = true
  
  const pendingItems = queue.value.filter(q => q.status === 'pending')
  const files = pendingItems.map(q => q.file)
  
  try {
    // Mark all as uploading
    for (const item of pendingItems) {
      item.status = 'uploading'
    }
    
    const results = await api.batchUpload(files)
    
    // Map results back to queue items
    for (const result of results) {
      const queueItem = pendingItems.find(q => q.file.name === result.filename)
      if (queueItem) {
        if (result.status === 'success') {
          queueItem.status = 'success'
          queueItem.evidenceId = result.id
        } else {
          queueItem.status = 'failed'
          queueItem.error = result.error
        }
      }
    }
    
    // Refresh the evidence list
    await refresh()
  } catch (e) {
    error.value =
      e instanceof ApiError ? `${e.message} (kode ${e.code})` : 'unggahan gagal, coba lagi.'
    // Mark all uploading as failed
    for (const item of pendingItems) {
      if (item.status === 'uploading') {
        item.status = 'failed'
        item.error = 'gagal mengunggah'
      }
    }
  } finally {
    busy.value = false
  }
}

function onPick(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    addFiles(input.files)
  }
  input.value = ''
}

function onDrop(event: DragEvent) {
  dragging.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    addFiles(event.dataTransfer.files)
  }
}

function goToLastUploaded() {
  if (lastUploadedId.value) {
    void router.push(`/hasil/${lastUploadedId.value}`)
  }
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

function refreshIfVisible() {
  if (document.visibilityState === 'visible' && !busy.value) void refresh()
}

onMounted(() => {
  void refresh()
  window.addEventListener('focus', refreshIfVisible)
  document.addEventListener('visibilitychange', refreshIfVisible)
})
onUnmounted(() => {
  window.removeEventListener('focus', refreshIfVisible)
  document.removeEventListener('visibilitychange', refreshIfVisible)
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <section class="card-hero p-5 md:p-7">
      <span class="kicker text-[10px]">LANGKAH 1 — MASUKKAN BUKTI</span>
      <h1 class="mt-1 text-headline-xl-mobile tracking-tight md:text-headline-xl">
        Baca signature JPEG
      </h1>
      <p class="mt-2 max-w-2xl text-body-md text-on-surface-variant">
        Satu atau lebih berkas JPEG membawa EXIF, dua tabel kuantisasi, dan jejak pipeline encoder. TraceLens
        membaca apa adanya dari byte berkas lalu membandingkannya dengan profil referensi
        contoh.
      </p>

      <!-- Reference Stats -->
      <div v-if="referenceStats" class="mt-4 flex items-center gap-4 text-body-sm text-on-surface-variant">
        <div class="flex items-center gap-1.5">
          <AppIcon name="camera" :size="16" class="text-primary" />
          <span class="font-semibold text-on-surface">{{ referenceStats.total_cameras }}</span>
          <span>kamera</span>
        </div>
        <div class="h-4 w-px bg-outline-variant" />
        <div class="flex items-center gap-1.5">
          <span class="font-semibold text-on-surface">{{ referenceStats.total_brands }}</span>
          <span>brand</span>
        </div>
        <div class="h-4 w-px bg-outline-variant" />
        <div class="flex items-center gap-1.5">
          <AppIcon name="bolt" :size="14" class="text-warning" />
          <span class="font-semibold text-on-surface">{{ referenceStats.auto_added_count }}</span>
          <span>auto-added</span>
        </div>
      </div>

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
          multiple
          class="sr-only"
          data-testid="file-input"
          @change="onPick"
        />
        <AppIcon name="folder" :size="26" class="text-primary" />
        <span class="text-body-md font-semibold">
          {{ busy ? 'Mengunggah…' : 'Tarik JPEG ke sini atau klik untuk memilih' }}
        </span>
        <span class="font-mono text-code-sm text-on-surface-variant">
          .jpg / .jpeg · maksimal {{ limitMb ?? '…' }} MB · hingga 50 berkas
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

    <!-- Batch Queue -->
    <section v-if="queueCount > 0" class="card overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant px-4 py-3">
        <div>
          <span class="kicker text-[10px]">ANTRIAN UNGGAH</span>
          <p class="text-body-md font-semibold">
            {{ queueCount }} berkas dipilih
            <span v-if="queueSuccess > 0" class="text-success">· {{ queueSuccess }} berhasil</span>
            <span v-if="queueFailed > 0" class="text-danger">· {{ queueFailed }} gagal</span>
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="!busy && queueSuccess === 0 && queueFailed === 0"
            type="button"
            class="btn-secondary h-9 px-3 text-danger"
            @click="clearQueue"
          >
            <AppIcon name="close" :size="15" />
            Hapus semua
          </button>
          <button
            v-if="!busy && queueCount > 0"
            type="button"
            class="btn-primary h-9 px-4"
            :disabled="queue.filter(q => q.status === 'pending').length === 0"
            @click="uploadAll"
          >
            <AppIcon v-if="busy" name="spinner" :size="15" class="animate-spin" />
            <AppIcon v-else name="upload" :size="15" />
            Unggah {{ queue.filter(q => q.status === 'pending').length }} berkas
          </button>
          <button
            v-if="busy"
            type="button"
            class="btn-primary h-9 px-4"
            disabled
          >
            <AppIcon name="spinner" :size="15" class="animate-spin" />
            Mengunggah...
          </button>
          <button
            v-if="!busy && queueSuccess > 0"
            type="button"
            class="btn-secondary h-9 px-4"
            @click="goToLastUploaded"
          >
            <AppIcon name="arrow" :size="15" />
            Lihat hasil
          </button>
        </div>
      </div>

      <ul class="max-h-96 overflow-y-auto">
        <li
          v-for="(item, index) in queue"
          :key="index"
          class="flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/60 px-4 py-3 last:border-0"
        >
          <div class="flex min-w-0 flex-1 items-center gap-3">
            <img
              v-if="item.thumbnailUrl"
              :src="item.thumbnailUrl"
              alt=""
              class="h-10 w-10 shrink-0 rounded border border-outline-variant object-cover"
            />
            <div class="min-w-0 flex-1">
              <p class="truncate text-body-sm font-semibold">{{ item.file.name }}</p>
              <p class="font-mono text-code-sm text-on-surface-variant">
                {{ fmtSize(item.file.size) }}
              </p>
              <p v-if="item.error" class="mt-1 text-code-sm text-danger">
                {{ item.error }}
              </p>
              <p v-if="item.evidenceId" class="mt-1 font-mono text-code-sm text-success">
                ID: {{ item.evidenceId }}
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span
              v-if="item.status === 'pending'"
              class="pill-neutral font-mono uppercase"
            >
              menunggu
            </span>
            <span
              v-else-if="item.status === 'uploading'"
              class="pill-neutral font-mono uppercase"
            >
              <AppIcon name="spinner" :size="12" class="animate-spin" />
              mengunggah
            </span>
            <span
              v-else-if="item.status === 'success'"
              class="pill-success font-mono uppercase"
            >
              berhasil
            </span>
            <span
              v-else-if="item.status === 'failed'"
              class="pill-danger font-mono uppercase"
            >
              gagal
            </span>
            <button
              v-if="!busy && item.status !== 'uploading'"
              type="button"
              class="btn-secondary h-9 px-3 text-danger"
              :title="`Hapus ${item.file.name}`"
              @click="removeFromQueue(index)"
            >
              <AppIcon name="close" :size="15" />
            </button>
          </div>
        </li>
      </ul>
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
              v-if="!brokenThumbs.has(item.id)"
              :src="api.thumbnailUrl(item.id)"
              alt=""
              loading="lazy"
              class="h-10 w-10 shrink-0 rounded border border-outline-variant object-cover"
              :data-thumb="item.id"
              @error="brokenThumbs.add(item.id)"
            />
            <div
              v-else
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-outline-variant bg-surface-container-low text-outline"
              role="img"
              aria-label="pratinjau tidak tersedia"
              :data-thumb-missing="item.id"
            >
              <AppIcon name="image-off" :size="16" />
            </div>
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
