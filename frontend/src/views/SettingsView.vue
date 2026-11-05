<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { api, ApiError } from '../api'
import type { AppSettings } from '../types'

const settings = ref<AppSettings | null>(null)
const draft = ref<number | null>(null)
const loading = ref(true)
const saving = ref(false)
const status = ref<{ kind: 'ok' | 'error'; text: string } | null>(null)

const dirty = computed(() => draft.value !== null && draft.value !== settings.value?.max_upload_mb)
const valid = computed(
  () => draft.value !== null && Number.isInteger(draft.value) && draft.value >= 1 && draft.value <= 500,
)

async function load() {
  loading.value = true
  try {
    settings.value = await api.settings()
    draft.value = settings.value.max_upload_mb
  } catch (e) {
    status.value = { kind: 'error', text: e instanceof Error ? e.message : 'gagal memuat pengaturan' }
  } finally {
    loading.value = false
  }
}

async function save() {
  status.value = null
  if (draft.value === null || !valid.value) {
    status.value = { kind: 'error', text: 'Batas unggahan harus bilangan bulat 1–500 MB.' }
    return
  }
  saving.value = true
  try {
    settings.value = await api.updateSettings(draft.value)
    draft.value = settings.value.max_upload_mb
    status.value = { kind: 'ok', text: `Tersimpan. Batas unggahan aktif ${settings.value.max_upload_mb} MB.` }
  } catch (e) {
    status.value = {
      kind: 'error',
      text:
        e instanceof ApiError
          ? `${e.message} (kode ${e.code})`
          : e instanceof Error
            ? e.message
            : 'gagal menyimpan',
    }
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-6">
    <header>
      <span class="kicker text-[10px]">PENGATURAN RUNTIME</span>
      <h1 class="mt-1 text-headline-xl-mobile tracking-tight md:text-headline-xl">Pengaturan</h1>
      <p class="mt-2 max-w-2xl text-body-md text-on-surface-variant">
        Nilai di halaman ini tersimpan di database dan langsung dipakai API, tanpa restart.
        <span class="font-mono">MAX_UPLOAD_MB</span> di env hanya menjadi nilai awal saat database
        belum punya baris pengaturan.
      </p>
    </header>

    <p v-if="loading" class="card p-6 text-body-sm text-on-surface-variant">Memuat pengaturan…</p>

    <template v-else>
      <section class="card p-5">
        <div class="flex items-start justify-between gap-3">
          <div>
            <span class="kicker text-[10px]">BATAS UNGGAHAN</span>
            <p class="text-body-md font-semibold">Ukuran maksimum satu berkas JPEG</p>
          </div>
          <span class="pill-neutral font-mono text-code-sm">1–500 MB</span>
        </div>

        <div class="mt-4 flex flex-wrap items-end gap-3">
          <label class="flex flex-col gap-1">
            <span class="kicker text-[10px]">MB</span>
            <input
              v-model.number="draft"
              type="number"
              min="1"
              max="500"
              step="1"
              class="h-11 w-32 rounded-control border border-outline-variant bg-surface-container-low px-3 font-mono text-label-md tabular text-on-surface focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              data-testid="max-upload-input"
              @keyup.enter="save"
            />
          </label>
          <button
            type="button"
            class="btn-primary"
            :disabled="saving || !dirty || !valid"
            data-testid="save-settings"
            @click="save"
          >
            <AppIcon name="check" :size="17" />
            {{ saving ? 'Menyimpan…' : 'Simpan' }}
          </button>
          <button type="button" class="btn-secondary" :disabled="saving || !dirty" @click="draft = settings?.max_upload_mb ?? null">
            <AppIcon name="refresh" :size="16" /> Batalkan
          </button>
        </div>

        <p
          v-if="status"
          class="mt-3 rounded-control border px-3 py-2 text-body-sm"
          :class="
            status.kind === 'ok'
              ? 'border-success-line bg-success-soft text-success'
              : 'border-danger-line bg-danger-soft text-danger'
          "
          :role="status.kind === 'error' ? 'alert' : 'status'"
          data-testid="settings-status"
        >
          {{ status.text }}
        </p>
        <p v-else class="mt-3 font-mono text-code-sm text-on-surface-variant">
          Aktif sekarang: {{ settings?.max_upload_mb }} MB. Unggahan lebih besar dari ini ditolak
          server dengan kode 413.
        </p>
      </section>

      <section class="card p-5" data-testid="settings-info">
        <span class="kicker text-[10px]">INFO RUNTIME (BACA-SAJA)</span>
        <dl class="mt-3 divide-y divide-outline-variant/60">
          <div class="flex flex-wrap items-center justify-between gap-2 py-2">
            <dt class="text-body-sm text-on-surface-variant">Berkas database</dt>
            <dd class="break-all font-mono text-label-md tabular">{{ settings?.db_file }}</dd>
          </div>
          <div v-if="settings?.db_path" class="flex flex-wrap items-center justify-between gap-2 py-2">
            <dt class="text-body-sm text-on-surface-variant">Path lengkap (loopback)</dt>
            <dd class="break-all font-mono text-label-md tabular">{{ settings?.db_path }}</dd>
          </div>
          <div v-else class="py-2">
            <p class="text-code-sm text-on-surface-variant">
              Path lengkap hanya dikirim ke pemanggil dari mesin ini; dari jaringan hanya nama
              berkas.
            </p>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-2 py-2">
            <dt class="text-body-sm text-on-surface-variant">Jumlah evidence</dt>
            <dd class="font-mono text-label-md tabular">{{ settings?.evidence_count }}</dd>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-2 py-2">
            <dt class="text-body-sm text-on-surface-variant">Versi aplikasi</dt>
            <dd class="font-mono text-label-md tabular">{{ settings?.app_version }}</dd>
          </div>
        </dl>
      </section>

      <section class="card border-warning-line bg-warning-soft p-4">
        <div class="flex items-start gap-3">
          <AppIcon name="shield" :size="18" class="mt-0.5 text-[#B45309]" />
          <p class="text-code-sm text-on-surface">
            Aplikasi ini tidak memakai autentikasi. Perubahan pengaturan hanya diterima dari
            loopback (mesin ini) atau origin CORS yang diizinkan; permintaan lain ditolak 403.
            Siapa pun di jaringan tetap bisa membaca pengaturan lewat GET.
          </p>
        </div>
      </section>
    </template>
  </div>
</template>
