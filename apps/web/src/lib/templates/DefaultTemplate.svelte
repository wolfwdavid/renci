<script lang="ts">
  interface Business {
    name: string;
    name_zh?: string;
    business_type: string;
    address: string;
    phone: string;
    email: string;
    description_en?: string;
    description_zh?: string;
    hours: Record<string, string>;
    menu_items?: Array<{ name: string; name_zh?: string; price: number; category?: string }>;
    photos?: string[];
    tier?: string;
  }

  let { business }: { business: Business } = $props();

  const dayOrder = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  const dayLabels: Record<string, string> = {
    monday: 'Mon', tuesday: 'Tue', wednesday: 'Wed',
    thursday: 'Thu', friday: 'Fri', saturday: 'Sat', sunday: 'Sun'
  };

  function sortedHours(hours: Record<string, string>) {
    return dayOrder
      .filter(d => hours[d])
      .map(d => ({ day: dayLabels[d] || d, time: hours[d] }));
  }
</script>

<div class="min-h-screen bg-white">
  <!-- Header -->
  <header class="bg-[#D4382C] text-white py-12 px-6">
    <div class="max-w-2xl mx-auto text-center">
      <h1 class="text-3xl md:text-4xl font-bold">
        {business.name}
      </h1>
      {#if business.name_zh}
        <p class="text-xl mt-2 text-white/80">{business.name_zh}</p>
      {/if}
      <p class="mt-4 text-white/70 capitalize">{business.business_type}</p>
    </div>
  </header>

  <main class="max-w-2xl mx-auto px-6 py-10">
    <!-- Description -->
    {#if business.description_en || business.description_zh}
      <section class="mb-10">
        {#if business.description_en}
          <p class="text-gray-700 text-lg">{business.description_en}</p>
        {/if}
        {#if business.description_zh}
          <p class="text-gray-500 mt-2">{business.description_zh}</p>
        {/if}
      </section>
    {/if}

    <!-- Contact & Address -->
    <section class="mb-10">
      <h2 class="text-xl font-semibold mb-4">Contact 联系方式</h2>
      <div class="space-y-2 text-gray-600">
        <p>📍 {business.address}</p>
        {#if business.phone}
          <p>📞 <a href="tel:{business.phone}" class="text-[#D4382C] hover:underline">{business.phone}</a></p>
        {/if}
        {#if business.email}
          <p>📧 <a href="mailto:{business.email}" class="text-[#D4382C] hover:underline">{business.email}</a></p>
        {/if}
      </div>
    </section>

    <!-- Hours -->
    {#if Object.keys(business.hours).length > 0}
      <section class="mb-10">
        <h2 class="text-xl font-semibold mb-4">Hours 营业时间</h2>
        <div class="grid grid-cols-2 gap-1 text-sm">
          {#each sortedHours(business.hours) as { day, time }}
            <span class="text-gray-500">{day}</span>
            <span class="text-gray-700">{time}</span>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Menu -->
    {#if business.menu_items && business.menu_items.length > 0}
      <section class="mb-10">
        <h2 class="text-xl font-semibold mb-4">Menu 菜单</h2>
        <div class="space-y-3">
          {#each business.menu_items as item}
            <div class="flex justify-between items-baseline border-b border-gray-100 pb-2">
              <div>
                <span class="text-gray-800">{item.name}</span>
                {#if item.name_zh}
                  <span class="text-gray-400 text-sm ml-2">{item.name_zh}</span>
                {/if}
              </div>
              {#if item.price > 0}
                <span class="text-gray-600 font-medium">${item.price.toFixed(2)}</span>
              {/if}
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Photos -->
    {#if business.photos && business.photos.length > 0}
      <section class="mb-10">
        <h2 class="text-xl font-semibold mb-4">Photos 照片</h2>
        <div class="grid grid-cols-2 gap-3">
          {#each business.photos as photo}
            <img src={photo} alt={business.name} class="rounded-lg w-full h-48 object-cover" />
          {/each}
        </div>
      </section>
    {/if}

    <!-- Ad Banner (free tier only) -->
    {#if business.tier === 'free'}
      <div class="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-sm text-gray-400 mb-10">
        Ad space — support local businesses
      </div>
    {/if}
  </main>

  <!-- Footer -->
  <footer class="py-8 text-center text-gray-300 text-xs border-t">
    {#if business.tier === 'free'}
      <p>Powered by <a href="/" class="text-[#D4382C] hover:underline">Renci</a></p>
    {/if}
  </footer>
</div>
