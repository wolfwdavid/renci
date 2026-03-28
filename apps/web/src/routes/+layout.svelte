<script lang="ts">
	import '../app.css';
	import ChatWidget from '$lib/components/ChatWidget.svelte';
	import AgentToggle from '$lib/components/AgentToggle.svelte';

	let { children } = $props();
</script>

{@render children()}
<AgentToggle />
<ChatWidget />
