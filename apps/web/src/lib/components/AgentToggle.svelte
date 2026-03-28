<script lang="ts">
  let isActive = $state(false);
  let isLoading = $state(true);

  const API_URL = 'https://renci-api-408375733910.us-central1.run.app';

  async function fetchStatus() {
    try {
      const res = await fetch(`${API_URL}/agent/status`);
      const data = await res.json();
      isActive = data.active;
    } catch {
      isActive = false;
    }
    isLoading = false;
  }

  async function toggle() {
    isLoading = true;
    try {
      const res = await fetch(`${API_URL}/agent/toggle`, { method: 'POST' });
      const data = await res.json();
      isActive = data.active;
    } catch {
      // keep current state
    }
    isLoading = false;
  }

  $effect(() => {
    fetchStatus();
  });
</script>

<div class="fixed top-20 right-6 z-40">
  <button
    onclick={toggle}
    disabled={isLoading}
    class="flex items-center gap-3 px-4 py-2.5 rounded-xl border transition-all shadow-lg backdrop-blur-xl cursor-pointer disabled:cursor-wait
      {isActive ? 'bg-green-950/80 border-green-700/50 hover:bg-green-900/80' : 'bg-zinc-900/80 border-zinc-700/50 hover:bg-zinc-800/80'}"
  >
    <div class="relative">
      <div class="w-10 h-5 rounded-full transition-colors {isActive ? 'bg-green-600' : 'bg-zinc-600'}">
        <div class="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform {isActive ? 'translate-x-5' : 'translate-x-0.5'}"></div>
      </div>
    </div>
    <div class="text-left">
      <p class="text-xs font-medium {isActive ? 'text-green-400' : 'text-zinc-400'}">
        {#if isLoading}
          ...
        {:else if isActive}
          Live Agent ON
        {:else}
          Live Agent OFF
        {/if}
      </p>
      <p class="text-[10px] text-zinc-500">SMS gateway only</p>
    </div>
  </button>
</div>
