<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, ApiError } from '../api'
import type { EvidenceDetail } from '../types'

const route = useRoute()
const detail = ref<EvidenceDetail | null>(null)
const error = ref('')
const notFound = ref(false)
const loading = ref(true)
const tab = ref<'exif' | 'qtable' | 'trace' | 'summary'>('exif')
const copied = ref('')
const thumbState = ref<'loading' | 'ok' | 'error'>('loading')

const sizeMb = computed(() => ((detail.value?.byte_size ?? 0) / 1024 / 1024).toFixed(2))

const evidenceId = computed(() => route.params.id as string)

// Manual enrichment state
const showEnrichForm = ref(false)
const enrichMake = ref('')
const enrichModel = ref('')
const enrichLoading = ref(false)
const enrichError = ref('')
const enrichSuccess = ref('')

const hasExifMakeModel = computed(() => {
  const exif = detail.value?.signature.exif
  if (!exif) return false
  const makeField = exif.fields.find(f => f.tag === 'Make')
  const modelField = exif.fields.find(f => f.tag === 'Model')
  return makeField?.value && modelField?.value
})

const hasHighConfidenceMatch = computed(() => {
  if (!detail.value?.matches || detail.value.matches.length === 0) return false
  return detail.value.matches.some(m => m.similarity > 0.80)
})

const tabs = [
  { id: 'exif', label: 'EXIF', icon: 'person' },
  { id: 'qtable', label: 'Tabel Kuantisasi', icon: 'grid' },
  { id: 'trace', label: 'Jejak Edit', icon: 'layers' },
  { id: 'summary', label: 'Ringkasan', icon: 'chart' },
] as const

const verdictClass = computed(() => {
  const label = detail.value?.verdict_label
  if (label === 'kuat') return 'pill-success'
  if (label === 'sedang') return 'pill-warning'
  if (label === 'lemah') return 'pill-danger'
  return 'pill-neutral'
})

const sqBadge = (state: string) =>
  state === 'ok' ? 'pill-success' : state === 'inconsistent' ? 'pill-warning' : 'pill-neutral'

const stateLabel = (state: string) =>
  state === 'ok' ? 'ADA' : state === 'inconsistent' ? 'TIDAK KONSISTEN' : 'HILANG'

async function load() {
  loading.value = true
  error.value = ''
  notFound.value = false
  thumbState.value = 'loading'
  try {
    detail.value = await api.detail(evidenceId.value)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound.value = true
    } else {
      error.value = e instanceof Error ? e.message : 'gagal memuat hasil'
    }
  } finally {
    loading.value = false
  }
}

async function copy(value: string, key: string) {
  await navigator.clipboard.writeText(value).catch(() => {})
  copied.value = key
  setTimeout(() => (copied.value = ''), 1500)
}

async function submitEnrichment() {
  if (!enrichMake.value.trim() || !enrichModel.value.trim()) {
    enrichError.value = 'Merk dan tipe kamera harus diisi'
    return
  }
  
  enrichLoading.value = true
  enrichError.value = ''
  enrichSuccess.value = ''
  
  try {
    const result = await api.enrichEvidence(evidenceId.value, {
      make: enrichMake.value.trim(),
      model: enrichModel.value.trim()
    })
    
    if (result.added) {
      enrichSuccess.value = `Kamera berhasil ditambahkan ke referensi (ID: ${result.reference_id})`
      showEnrichForm.value = false
      enrichMake.value = ''
      enrichModel.value = ''
      // Reload detail to show updated data
      await load()
    } else {
      enrichError.value = result.reason || 'Gagal menambahkan kamera'
    }
  } catch (e) {
    enrichError.value = e instanceof Error ? e.message : 'gagal menambahkan kamera'
  } finally {
    enrichLoading.value = false
  }
}

onMounted(load)
watch(evidenceId, load)
</script>

<template>
  <div v-if="loading" class="card p-8 text-body-md text-on-surface-variant">Membaca signature…</div>

  <section
    v-else-if="notFound"
    class="card-hero mx-auto max-w-lg p-6 text-center"
    data-testid="not-found"
  >
    <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-danger-soft text-danger">
      <AppIcon name="alert" :size="22" />
    </div>
    <h1 class="mt-3 text-headline-md">Bukti tidak ditemukan</h1>
    <p class="mt-2 text-body-sm text-on-surface-variant">
      Tidak ada bukti dengan id <span class="font-mono">{{ evidenceId }}</span> di basis data ini.
    </p>
    <RouterLink to="/" class="btn-primary mt-5">Kembali ke unggah</RouterLink>
  </section>

  <div v-else-if="error" class="card border-danger-line bg-danger-soft p-6 text-body-sm text-danger">
    {{ error }}
  </div>

  <div v-else-if="detail" class="flex flex-col gap-6">
    <section class="card flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div class="flex min-w-0 flex-wrap items-center gap-2">
        <AppIcon name="fingerprint" :size="17" class="text-primary" />
        <span class="font-mono text-label-md font-semibold">{{ detail.id }}</span>
        <span class="text-outline">•</span>
        <span class="truncate text-body-sm">{{ detail.filename }}</span>
        <span class="text-outline">•</span>
        <span class="font-mono text-label-sm tabular">
          {{ detail.width }}×{{ detail.height }}
        </span>
      </div>
      <RouterLink :to="`/laporan/${detail.id}`" class="btn-secondary h-9">
        <AppIcon name="doc" :size="15" /> Laporan
      </RouterLink>
    </section>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <section class="card overflow-hidden" data-testid="evidence-thumb">
        <div class="relative aspect-[4/3] w-full bg-surface-container-low">
          <img
            v-show="thumbState !== 'error'"
            :src="api.thumbnailUrl(detail.id)"
            :alt="`Pratinjau ${detail.filename}`"
            loading="lazy"
            class="h-full w-full object-cover"
            data-testid="evidence-thumb-img"
            @load="thumbState = 'ok'"
            @error="thumbState = 'error'"
          />
          <div
            v-if="thumbState === 'loading'"
            class="absolute inset-0 flex items-center justify-center font-mono text-code-sm text-on-surface-variant"
          >
            memuat pratinjau…
          </div>
          <div
            v-else-if="thumbState === 'error'"
            class="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-surface-container-low text-center"
            data-testid="thumb-error"
          >
            <AppIcon name="alert" :size="18" class="text-danger" />
            <span class="text-code-sm text-on-surface-variant">pratinjau tidak tersedia</span>
          </div>
        </div>
        <div class="flex flex-col gap-1 p-3">
          <p class="truncate text-body-sm font-semibold" :title="detail.filename">{{ detail.filename }}</p>
          <p class="font-mono text-code-sm text-on-surface-variant">
            <span class="tabular">{{ detail.width }}×{{ detail.height }}</span> ·
            <span class="tabular">{{ sizeMb }} MB</span> ·
            <span class="tabular">{{ detail.signature.encoder.subsampling }}</span>
          </p>
          <a
            :href="api.imageUrl(detail.id)"
            target="_blank"
            rel="noopener"
            class="mt-1 inline-flex items-center gap-1 text-body-sm font-semibold text-primary hover:underline"
            data-testid="full-size-link"
          >
            <AppIcon name="eye" :size="15" /> Lihat ukuran penuh
          </a>
        </div>
      </section>

      <section class="card-hero p-5 md:p-6">
        <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <span class="kicker text-[10px]">VERDICT SIGNATURE</span>
          <p class="mt-1 text-headline-lg tracking-tight">{{ detail.camera_guess }}</p>
          <p class="mt-1 text-body-sm text-on-surface-variant">{{ detail.verdict_text }}</p>
        </div>
        <div class="text-right">
          <span :class="verdictClass" class="font-mono uppercase">{{ detail.verdict_label }}</span>
          <p class="mt-1 font-mono text-headline-md tabular" data-testid="confidence">
            {{ (detail.confidence * 100).toFixed(1) }}%
          </p>
          <p class="kicker text-[10px]">CONFIDENCE</p>
        </div>
      </div>

      <div class="mt-4">
        <div class="metric-bar">
          <div
            class="h-full rounded-pill transition-all duration-500"
            :class="
              detail.verdict_label === 'kuat'
                ? 'bg-success'
                : detail.verdict_label === 'sedang'
                  ? 'bg-warning'
                  : 'bg-danger'
            "
            :style="{ width: `${Math.min(100, detail.confidence * 100)}%` }"
          />
        </div>
        <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-code-sm text-on-surface-variant">
          <span>ENCODER: {{ detail.encoder_guess }}</span>
          <span>SUBSAMPLING: {{ detail.signature.encoder.subsampling }}</span>
          <span>{{ detail.signature.encoder.app_markers.join(' · ') || 'tanpa penanda APP' }}</span>
        </div>
      </div>
      </section>
    </div>

    <section class="card overflow-hidden">
      <div class="flex flex-wrap gap-1 border-b border-outline-variant px-3 pt-2">
        <button
          v-for="item in tabs"
          :key="item.id"
          type="button"
          class="flex items-center gap-2 rounded-t-control px-3 py-2 text-body-sm font-semibold transition"
          :class="
            tab === item.id
              ? 'border-b-2 border-primary bg-surface-container-low text-primary'
              : 'text-on-surface-variant hover:text-on-surface'
          "
          :data-result-tab="item.id"
          @click="tab = item.id"
        >
          <AppIcon :name="item.icon" :size="16" />
          {{ item.label }}
        </button>
      </div>

      <div v-if="tab === 'exif'" class="p-4" data-panel="exif">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="kicker text-[10px]">TAG EXIF YANG TERBACA</span>
          <span class="pill-neutral font-mono text-code-sm">
            {{ detail.signature.exif.fields.filter((f) => f.state === 'ok').length }}/{{
              detail.signature.exif.fields.length
            }}
            ADA
          </span>
        </div>
        <dl class="mt-3 divide-y divide-outline-variant/60">
          <div
            v-for="field in detail.signature.exif.fields"
            :key="field.tag"
            class="flex flex-wrap items-center justify-between gap-2 py-2"
            :data-exif-tag="field.tag"
          >
            <dt class="text-body-sm text-on-surface-variant">{{ field.tag }}</dt>
            <dd class="flex items-center gap-2">
              <span class="font-mono text-label-md">{{ field.value ?? '—' }}</span>
              <span :class="sqBadge(field.state)" class="font-mono text-code-sm">
                {{ stateLabel(field.state) }}
              </span>
            </dd>
          </div>
        </dl>
        <p class="mt-3 rounded-control bg-surface-container-low px-3 py-2 text-code-sm text-on-surface-variant">
          Thumbnail tertanam: {{ detail.signature.exif.has_thumbnail ? 'ada' : 'tidak ada' }} ·
          MakerNote: {{ detail.signature.exif.makernote_present ? 'ada' : 'tidak ada' }} · EXIF
          dapat dipalsukan, jadi bobotnya 45%.
        </p>
        
        <!-- Manual Enrichment Form -->
        <div v-if="!hasExifMakeModel && !hasHighConfidenceMatch" class="mt-4 rounded-control border border-warning bg-warning/10 p-4">
          <div class="flex items-start gap-3">
            <AppIcon name="alert" :size="20" class="mt-0.5 text-warning flex-shrink-0" />
            <div class="flex-1">
              <p class="text-body-sm font-semibold text-warning">EXIF Make/Model tidak ditemukan</p>
              <p class="mt-1 text-code-sm text-on-surface-variant">
                Kamera tidak terdeteksi otomatis. Masukkan merk dan tipe kamera secara manual untuk menambahkan ke referensi.
              </p>
              
              <button
                v-if="!showEnrichForm"
                type="button"
                class="btn-secondary mt-3 h-9"
                @click="showEnrichForm = true"
              >
                <AppIcon name="edit" :size="15" />
                Input Manual
              </button>
              
              <form v-else @submit.prevent="submitEnrichment" class="mt-3 space-y-3">
                <div>
                  <label for="enrich-make" class="block text-body-sm font-semibold mb-1">
                    Merk Kamera <span class="text-danger">*</span>
                  </label>
                  <input
                    id="enrich-make"
                    v-model="enrichMake"
                    type="text"
                    required
                    maxlength="100"
                    placeholder="Contoh: Canon, Nikon, Sony"
                    class="input-field w-full"
                    :disabled="enrichLoading"
                  />
                </div>
                <div>
                  <label for="enrich-model" class="block text-body-sm font-semibold mb-1">
                    Tipe Kamera <span class="text-danger">*</span>
                  </label>
                  <input
                    id="enrich-model"
                    v-model="enrichModel"
                    type="text"
                    required
                    maxlength="100"
                    placeholder="Contoh: EOS R5, Z8, A7 IV"
                    class="input-field w-full"
                    :disabled="enrichLoading"
                  />
                </div>
                
                <div v-if="enrichError" class="rounded-control bg-danger/10 border border-danger px-3 py-2 text-code-sm text-danger">
                  {{ enrichError }}
                </div>
                
                <div v-if="enrichSuccess" class="rounded-control bg-success/10 border border-success px-3 py-2 text-code-sm text-success">
                  {{ enrichSuccess }}
                </div>
                
                <div class="flex gap-2">
                  <button
                    type="submit"
                    class="btn-primary h-9"
                    :disabled="enrichLoading"
                  >
                    <AppIcon v-if="enrichLoading" name="spinner" :size="15" class="animate-spin" />
                    <AppIcon v-else name="check" :size="15" />
                    {{ enrichLoading ? 'Menyimpan...' : 'Simpan ke Referensi' }}
                  </button>
                  <button
                    type="button"
                    class="btn-secondary h-9"
                    @click="showEnrichForm = false; enrichError = ''; enrichSuccess = ''"
                    :disabled="enrichLoading"
                  >
                    Batal
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="tab === 'qtable'" class="p-4" data-panel="qtable">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="kicker text-[10px]">DUA TABEL KUANTISASI — 64 NILAI MASING-MASING</span>
          <span class="font-mono text-code-sm text-on-surface-variant">dari GET /signature</span>
        </div>
        <div class="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div
            v-for="key in (['luma', 'chroma'] as const)"
            :key="key"
            class="rounded-card border border-outline-variant p-3"
          >
            <div class="flex items-center justify-between">
              <span class="text-body-sm font-semibold">
                {{ key === 'luma' ? 'Luma (tabel 0)' : 'Kroma (tabel 1)' }}
              </span>
              <span class="pill-neutral font-mono text-code-sm">
                μ {{ (detail.signature.qtable[key].reduce((a, b) => a + b, 0) / 64).toFixed(2) }}
              </span>
            </div>
            <div class="mt-2 grid grid-cols-8 gap-1">
              <span
                v-for="(value, index) in detail.signature.qtable[key]"
                :key="index"
                class="flex aspect-square items-center justify-center rounded bg-surface-container-low font-mono text-code-sm tabular"
                :data-qtable="`${key}-${index}`"
              >
                {{ value }}
              </span>
            </div>
          </div>
        </div>
        <div class="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-card bg-surface-container-low px-3 py-2">
          <div class="min-w-0">
            <span class="kicker text-[10px]">FINGERPRINT TABEL (SHA-256)</span>
            <p class="break-all font-mono text-label-md tabular" data-testid="fingerprint">
              {{ detail.signature.fingerprint_hex }}
            </p>
          </div>
          <button
            type="button"
            class="btn-secondary h-9"
            @click="copy(detail.signature.fingerprint_hex, 'fp')"
          >
            <AppIcon :name="copied === 'fp' ? 'check' : 'copy'" :size="15" />
            {{ copied === 'fp' ? 'Tersalin' : 'Salin' }}
          </button>
        </div>
      </div>

      <div v-else-if="tab === 'trace'" class="flex flex-col gap-3 p-4" data-panel="trace">
        <div
          v-for="trace in detail.signature.edit_traces"
          :key="trace.key"
          class="rounded-card border p-3"
          :class="trace.detected ? 'border-danger-line bg-danger-soft' : 'border-outline-variant'"
          :data-trace="trace.key"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-body-sm font-semibold">{{ trace.label }}</span>
            <span :class="trace.detected ? 'pill-danger' : 'pill-success'" class="font-mono uppercase">
              {{ trace.detected ? 'TERINDIKASI' : 'BERSIH' }}
            </span>
          </div>
          <p class="mt-1 text-body-sm text-on-surface-variant">{{ trace.detail }}</p>
        </div>
      </div>

      <div v-else class="p-4" data-panel="summary">
        <span class="kicker text-[10px]">SKOR PER KOMPONEN</span>
        <div class="mt-3 flex flex-col gap-3">
          <div
            v-for="component in detail.signature.components"
            :key="component.key"
            class="rounded-card border border-outline-variant p-3"
            :data-component="component.key"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="text-body-sm font-semibold">{{ component.label }}</span>
              <span class="font-mono text-label-sm tabular">
                {{ component.score.toFixed(3) }} × {{ component.weight.toFixed(2) }} =
                {{ component.contribution.toFixed(3) }}
              </span>
            </div>
            <div class="metric-bar mt-2">
              <div
                class="h-full rounded-pill bg-primary"
                :style="{ width: `${component.score * 100}%` }"
              />
            </div>
            <p class="mt-2 text-code-sm text-on-surface-variant">{{ component.reason }}</p>
          </div>
        </div>

        <div class="mt-4">
          <span class="kicker text-[10px]">KANDIDAT TERATAS</span>
          <ul class="mt-2 flex flex-col gap-2">
            <li
              v-for="match in detail.matches"
              :key="match.reference_id"
              class="flex flex-wrap items-center justify-between gap-2 rounded-control bg-surface-container-low px-3 py-2"
              :data-match="match.rank"
            >
              <div class="min-w-0">
                <p class="text-body-sm font-semibold">{{ match.label }}</p>
                <p class="font-mono text-code-sm text-on-surface-variant">
                  {{ match.reference_id }} · {{ match.encoder }} · {{ match.explanation }}
                </p>
              </div>
              <span class="font-mono text-label-md tabular">
                {{ (match.similarity * 100).toFixed(1) }}%
              </span>
            </li>
          </ul>
        </div>

        <p class="mt-4 text-code-sm text-on-surface-variant">
          Confidence = 0.45·EXIF + 0.35·kemiripan tabel + 0.20·encoder. Ambang: ≥0.75 kuat, ≥0.55
          sedang, ≥0.45 lemah, di bawahnya tidak dapat dipastikan.
        </p>
      </div>
    </section>

    <div class="flex flex-col gap-2 sm:flex-row">
      <RouterLink :to="`/laporan/${detail.id}`" class="btn-primary sm:flex-1">
        <AppIcon name="doc" :size="18" /> Lihat laporan siap cetak
      </RouterLink>
      <RouterLink to="/" class="btn-secondary sm:flex-1">
        <AppIcon name="plus" :size="16" /> Unggah berkas lain
      </RouterLink>
    </div>
  </div>
</template>
