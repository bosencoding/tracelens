<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api, ApiError } from '../api'
import type { EvidenceDetail } from '../types'

const route = useRoute()
const detail = ref<EvidenceDetail | null>(null)
const loading = ref(true)
const notFound = ref(false)
const error = ref('')

const evidenceId = computed(() => route.params.id as string)
const wib = (iso: string) =>
  new Intl.DateTimeFormat('id-ID', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Jakarta',
  }).format(new Date(iso))

const detected = computed(() => detail.value?.signature.edit_traces.filter((t) => t.detected) ?? [])

function printDoc() {
  window.print()
}

async function load() {
  loading.value = true
  error.value = ''
  notFound.value = false
  try {
    detail.value = await api.detail(evidenceId.value)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound.value = true
    else error.value = e instanceof Error ? e.message : 'gagal memuat laporan'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(evidenceId, load)
</script>

<template>
  <div v-if="loading" class="card p-8 text-body-md text-on-surface-variant">Menyusun laporan…</div>

  <section v-else-if="notFound" class="card-hero p-6 text-center" data-testid="not-found">
    <h1 class="text-headline-md">Laporan tidak tersedia</h1>
    <p class="mt-2 text-body-sm text-on-surface-variant">
      Bukti <span class="font-mono">{{ evidenceId }}</span> tidak ada, jadi tidak ada yang bisa
      dilaporkan.
    </p>
    <RouterLink to="/" class="btn-primary mt-5">Kembali ke unggah</RouterLink>
  </section>

  <div v-else-if="error" class="card border-danger-line bg-danger-soft p-6 text-body-sm text-danger">
    {{ error }}
  </div>

  <article v-else-if="detail" class="card-hero print-card p-5 md:p-8">
    <header class="no-print mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant pb-3">
      <span class="kicker text-[10px]">PRATINJAU CETAK</span>
      <button type="button" class="btn-primary h-10" data-testid="print" @click="printDoc()">
        <AppIcon name="download" :size="16" /> Cetak / Simpan PDF
      </button>
    </header>

    <div class="flex flex-wrap items-start justify-between gap-4 border-b border-outline-variant pb-4">
      <div>
        <p class="kicker text-[10px]">REPUBLIK INDONESIA · DOKUMEN RINGKAS</p>
        <h1 class="mt-1 text-headline-lg tracking-tight">
          LAPORAN IDENTIFIKASI SIGNATURE JPEG
        </h1>
        <p class="mt-1 font-mono text-label-sm text-on-surface-variant">
          Nomor: TL/{{ detail.id }} · Kasus #CAS-2025-089
        </p>
      </div>
      <div class="text-right">
        <span class="pill-neutral font-mono uppercase">{{ detail.verdict_label }}</span>
        <p class="mt-1 font-mono text-headline-md tabular">
          {{ (detail.confidence * 100).toFixed(1) }}%
        </p>
        <p class="kicker text-[10px]">CONFIDENCE</p>
      </div>
    </div>

    <section class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div class="rounded-card border border-outline-variant p-3 print-avoid-break">
        <span class="kicker text-[10px]">IDENTITAS BERKAS</span>
        <dl class="mt-1 flex flex-col gap-1 text-body-sm">
          <div class="flex justify-between gap-2">
            <dt class="text-on-surface-variant">Nama</dt>
            <dd class="truncate text-right">{{ detail.filename }}</dd>
          </div>
          <div class="flex justify-between gap-2">
            <dt class="text-on-surface-variant">Ukuran</dt>
            <dd class="font-mono tabular">{{ (detail.byte_size / 1024).toFixed(0) }} KB</dd>
          </div>
          <div class="flex justify-between gap-2">
            <dt class="text-on-surface-variant">Dimensi</dt>
            <dd class="font-mono tabular">{{ detail.width }}×{{ detail.height }}</dd>
          </div>
          <div class="flex justify-between gap-2">
            <dt class="text-on-surface-variant">Diunggah</dt>
            <dd class="font-mono tabular">{{ wib(detail.uploaded_at) }} WIB</dd>
          </div>
        </dl>
        <p class="mt-2 break-all font-mono text-code-sm text-on-surface-variant">
          SHA-256: {{ detail.sha256 }}
        </p>
      </div>

      <div class="rounded-card border border-outline-variant p-3 print-avoid-break">
        <span class="kicker text-[10px]">HASIL</span>
        <p class="mt-1 text-body-md font-semibold">{{ detail.camera_guess }}</p>
        <p class="text-body-sm text-on-surface-variant">{{ detail.verdict_text }}</p>
        <dl class="mt-2 flex flex-col gap-1 font-mono text-code-sm">
          <div class="flex justify-between gap-2">
            <dt class="text-on-surface-variant">Encoder</dt>
            <dd>{{ detail.encoder_guess }}</dd>
          </div>
          <div class="flex justify-between gap-2">
            <dt class="text-on-surface-variant">Subsampling</dt>
            <dd>{{ detail.signature.encoder.subsampling }}</dd>
          </div>
          <div class="flex justify-between gap-2">
            <dt class="text-on-surface-variant">Fingerprint</dt>
            <dd class="truncate">{{ detail.signature.fingerprint_hex.slice(0, 24) }}…</dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="mt-4">
      <span class="kicker text-[10px]">TEMUAN</span>
      <ul class="mt-2 flex flex-col gap-2">
        <li
          v-for="component in detail.signature.components"
          :key="component.key"
          class="rounded-control bg-surface-container-low px-3 py-2 print-avoid-break"
        >
          <p class="text-body-sm font-semibold">
            {{ component.label }} — {{ component.score.toFixed(2) }}
          </p>
          <p class="text-code-sm text-on-surface-variant">{{ component.reason }}</p>
        </li>
        <li
          v-for="trace in detected"
          :key="trace.key"
          class="rounded-control border border-danger-line px-3 py-2 print-avoid-break"
        >
          <p class="text-body-sm font-semibold text-danger">Terindikasi: {{ trace.label }}</p>
          <p class="text-code-sm text-on-surface-variant">{{ trace.detail }}</p>
        </li>
      </ul>
    </section>

    <section class="mt-4">
      <span class="kicker text-[10px]">KANDIDAT</span>
      <table class="mt-2 w-full text-left text-body-sm">
        <thead>
          <tr class="border-b border-outline-variant">
            <th class="py-1 font-normal text-on-surface-variant">#</th>
            <th class="py-1 font-normal text-on-surface-variant">Referensi</th>
            <th class="py-1 text-right font-normal text-on-surface-variant">Kemiripan</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="match in detail.matches" :key="match.reference_id" class="border-b border-outline-variant/60">
            <td class="py-1 font-mono">{{ match.rank }}</td>
            <td class="py-1">{{ match.label }}</td>
            <td class="py-1 text-right font-mono tabular">{{ (match.similarity * 100).toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="mt-5 rounded-card border border-warning-line bg-warning-soft p-3 print-avoid-break" data-testid="disclaimer">
      <span class="kicker text-[10px] text-[#B45309]">DISCLAIMER & BATASAN METODE</span>
      <p class="mt-1 text-code-sm text-on-surface">
        Seluruh berkas contoh pada aplikasi ini dibuat secara sintetis dengan Pillow; tidak ada
        gambar maupun profil kamera nyata. Kesimpulan dihitung dari EXIF, dua tabel kuantisasi, dan
        fingerprint encoder. Tabel kuantisasi menandai pipeline encoder dengan andal, tetapi model
        kamera hanya dapat disebut bila cocok dengan tabel referensi. EXIF dapat dipalsukan dan
        tidak membuktikan asal berkas. Laporan ini bukan hasil pemeriksaan forensik atas alat bukti
        nyata dan tidak dapat dipakai sebagai keterangan ahli.
      </p>
    </section>
  </article>
</template>
