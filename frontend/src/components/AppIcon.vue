<script setup lang="ts">
const paths: Record<string, string> = {
  fingerprint:
    'M12 4a8 8 0 0 0-8 8v2m16-2a8 8 0 0 0-8-8m0 4a4 4 0 0 0-4 4v4m8-4a4 4 0 0 1 4 4v1M9 20a10 10 0 0 1-.6-3.4M15 20c.3-1.2.4-2.4.4-3.6M12 12v5',
  camera: 'M4 8h3l1.5-2h7L17 8h3v11H4z M12 16.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  verified: 'M4 12.5 9 17.5 20 6.5',
  check: 'M5 12.5 10 17.5 19 7',
  alert: 'M12 4 2.5 20h19L12 4z M12 10v5 M12 18v.5',
  copy: 'M9 9h9v11H9z M6 15H4V4h11v2',
  arrow: 'M5 12h13 M13 6l6 6-6 6',
  folder: 'M3 6h6l2 2h10v11H3z',
  scan: 'M4 8V4h4 M20 8V4h-4 M4 16v4h4 M20 16v4h-4 M8 12h8',
  shield: 'M12 3.5 20 6v6c0 4.5-3.4 7.4-8 8.5-4.6-1.1-8-4-8-8.5V6z',
  download: 'M12 4v10 M8 11l4 4 4-4 M5 19h14',
  lock: 'M7 11V8a5 5 0 0 1 10 0v3 M5 11h14v9H5z',
  person: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 20c0-3.3 3.6-5.5 8-5.5s8 2.2 8 5.5',
  grid: 'M4 4h16v16H4z M4 12h16 M12 4v16',
  terminal: 'M4 5h16v14H4z M7 10l3 2.5-3 2.5 M13 15h4',
  wave: 'M2 12h3l2-6 3 12 3-9 2 3h7',
  layers: 'M12 3 3 8l9 5 9-5-9-5z M3 13l9 5 9-5',
  doc: 'M6 3h8l4 4v14H6z M14 3v5h4 M9 13h6 M9 17h6',
  chart: 'M4 20V4 M4 20h16 M8 16v-5 M13 16V8 M18 16v-8',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M16 16l4 4',
  refresh: 'M20 12a8 8 0 1 1-3-6.2 M20 4v5h-5',
  plus: 'M12 5v14 M5 12h14',
  close: 'M6 6l12 12 M18 6 6 18',
  center: 'M12 3v4 M12 17v4 M3 12h4 M17 12h4 M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  bolt: 'M13 3 5 14h6l-1 7 8-11h-6z',
  eye: 'M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6S2 12 2 12z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
}

defineProps<{ name: string; size?: number; strokeWidth?: number }>()
</script>

<template>
  <svg
    :width="size ?? 18"
    :height="size ?? 18"
    viewBox="0 0 24 24"
    fill="none"
    :stroke-width="strokeWidth ?? 1.7"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    class="shrink-0"
  >
    <path :d="paths[name] ?? paths.scan" />
  </svg>
</template>
