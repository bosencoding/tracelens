<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import AppIcon from './components/AppIcon.vue'

const route = useRoute()
const currentId = computed(() => (route.params.id as string) || '')

// Mobile menu state
const isMenuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)

function toggleMenu() {
  isMenuOpen.value = !isMenuOpen.value
}

function closeMenu() {
  isMenuOpen.value = false
}

function handleEscKey(event: KeyboardEvent) {
  if (event.key === 'Escape' && isMenuOpen.value) {
    closeMenu()
  }
}

function handleClickOutside(event: MouseEvent) {
  if (isMenuOpen.value && menuRef.value && !menuRef.value.contains(event.target as Node)) {
    closeMenu()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscKey)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscKey)
  document.removeEventListener('click', handleClickOutside)
})
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
              <span class="pill-neutral font-mono hidden sm:inline">#CAS-2025-089</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-1.5 w-1.5 rounded-full bg-success" />
              <span class="font-mono text-code-sm uppercase tracking-[0.08em] text-success hidden sm:inline">
                ENGINE: JPEG-SIGNATURE v2
              </span>
            </div>
          </div>
        </RouterLink>

        <!-- Desktop navigation -->
        <nav class="hidden md:flex items-center gap-1">
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
            to="/referensi"
            class="flex items-center gap-2 rounded-control px-3 py-2 text-body-sm font-semibold transition"
            :class="
              route.name === 'reference'
                ? 'bg-surface-container-low text-primary'
                : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
            "
          >
            <AppIcon name="grid" :size="16" /> Referensi
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

        <!-- Mobile hamburger button -->
        <button
          class="md:hidden flex items-center justify-center w-10 h-10 rounded-control text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface transition"
          @click.stop="toggleMenu"
          aria-label="Toggle menu"
        >
          <AppIcon :name="isMenuOpen ? 'close' : 'menu'" :size="24" />
        </button>
      </div>
    </header>

    <!-- Mobile side menu overlay -->
    <Transition name="fade">
      <div
        v-if="isMenuOpen"
        class="md:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
        @click="closeMenu"
      />
    </Transition>

    <!-- Mobile side menu -->
    <Transition name="slide">
      <div
        v-if="isMenuOpen"
        ref="menuRef"
        class="md:hidden fixed left-0 top-0 z-50 h-full w-72 bg-surface-lowest shadow-2xl"
      >
        <div class="flex flex-col h-full">
          <!-- Menu header -->
          <div class="flex items-center justify-between p-4 border-b border-outline-variant">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-control bg-primary text-on-primary">
                <AppIcon name="fingerprint" :size="20" />
              </div>
              <span class="text-headline-sm tracking-tight">TraceLens</span>
            </div>
            <button
              class="flex items-center justify-center w-10 h-10 rounded-control text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface transition"
              @click="closeMenu"
              aria-label="Close menu"
            >
              <AppIcon name="close" :size="24" />
            </button>
          </div>

          <!-- Menu items -->
          <nav class="flex-1 overflow-y-auto p-4">
            <div class="flex flex-col gap-2">
              <RouterLink
                to="/"
                class="flex items-center gap-3 rounded-control px-4 py-3 text-body-md font-semibold transition"
                :class="
                  route.name === 'upload'
                    ? 'bg-surface-container-low text-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
                "
                @click="closeMenu"
              >
                <AppIcon name="folder" :size="20" /> Unggah
              </RouterLink>
              <RouterLink
                v-if="currentId"
                :to="`/hasil/${currentId}`"
                class="flex items-center gap-3 rounded-control px-4 py-3 text-body-md font-semibold transition"
                :class="
                  route.name === 'result'
                    ? 'bg-surface-container-low text-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
                "
                @click="closeMenu"
              >
                <AppIcon name="scan" :size="20" /> Hasil
              </RouterLink>
              <RouterLink
                to="/referensi"
                class="flex items-center gap-3 rounded-control px-4 py-3 text-body-md font-semibold transition"
                :class="
                  route.name === 'reference'
                    ? 'bg-surface-container-low text-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
                "
                @click="closeMenu"
              >
                <AppIcon name="grid" :size="20" /> Referensi
              </RouterLink>
              <RouterLink
                to="/pengaturan"
                class="flex items-center gap-3 rounded-control px-4 py-3 text-body-md font-semibold transition"
                :class="
                  route.name === 'settings'
                    ? 'bg-surface-container-low text-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
                "
                @click="closeMenu"
              >
                <AppIcon name="gear" :size="20" /> Pengaturan
              </RouterLink>
              <RouterLink
                v-if="currentId"
                :to="`/laporan/${currentId}`"
                class="flex items-center gap-3 rounded-control px-4 py-3 text-body-md font-semibold transition"
                :class="
                  route.name === 'report'
                    ? 'bg-surface-container-low text-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-low/60 hover:text-on-surface'
                "
                @click="closeMenu"
              >
                <AppIcon name="doc" :size="20" /> Laporan
              </RouterLink>
            </div>
          </nav>

          <!-- Menu footer -->
          <div class="p-4 border-t border-outline-variant">
            <div class="flex items-center gap-1.5">
              <span class="h-1.5 w-1.5 rounded-full bg-success" />
              <span class="font-mono text-code-sm uppercase tracking-[0.08em] text-success">
                ENGINE: JPEG-SIGNATURE v2
              </span>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <main class="mx-auto w-full max-w-shell flex-1 px-4 pb-16 pt-6 md:px-8">
      <RouterView />
    </main>

    <footer
      class="no-print border-t border-outline-variant bg-surface-lowest py-2 text-center font-mono text-code-sm text-on-surface-variant"
    >
      (c) Hany Andriyanto - 2026
    </footer>
  </div>
</template>

<style>
/* Mobile menu transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 250ms ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 250ms ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}

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
