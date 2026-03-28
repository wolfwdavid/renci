<script lang="ts">
  import DefaultTemplate from '$lib/templates/DefaultTemplate.svelte';

  let { data } = $props();
</script>

<svelte:head>
  <title>{data.business.name} {data.business.name_zh ? `| ${data.business.name_zh}` : ''}</title>
  <meta name="description" content={data.business.description_en || `${data.business.name} — ${data.business.address}`} />
</svelte:head>

<DefaultTemplate business={data.business} />
