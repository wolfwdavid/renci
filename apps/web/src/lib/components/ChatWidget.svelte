<script lang="ts">
  let messages: Array<{role: string, text: string}> = $state([]);
  let input = $state('');
  let isLoading = $state(false);
  let isOpen = $state(false);
  let chatContainer: HTMLElement;

  const API_URL = 'https://renci-api-408375733910.us-central1.run.app';

  async function sendMessage() {
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    input = '';
    messages = [...messages, { role: 'user', text: userMsg }];
    isLoading = true;

    // Scroll to bottom
    setTimeout(() => {
      if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 50);

    try {
      const res = await fetch(`${API_URL}/webhooks/email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_address: 'demo@renci.app',
          body: userMsg,
          subject: 'Renci Chat',
        }),
      });

      const data = await res.json();
      messages = [...messages, { role: 'agent', text: data.response || 'Sorry, something went wrong.' }];
    } catch {
      messages = [...messages, { role: 'agent', text: 'Connection error. The agent may be waking up — try again in a moment.' }];
    }

    isLoading = false;
    setTimeout(() => {
      if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 50);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function toggleChat() {
    isOpen = !isOpen;
    if (isOpen && messages.length === 0) {
      messages = [{ role: 'agent', text: "Hi! I'm Renci 仁慈. Type \"Hi\" to start registering your business, or ask me anything.\n\n你好！我是仁慈。输入\"Hi\"开始注册你的店，或者问我任何问题。" }];
    }
  }
</script>

<!-- Floating button -->
{#if !isOpen}
  <button
    onclick={toggleChat}
    class="fixed bottom-6 right-6 z-50 w-14 h-14 bg-red-600 hover:bg-red-500 rounded-full shadow-lg shadow-red-600/30 flex items-center justify-center transition-all hover:scale-105 cursor-pointer"
    aria-label="Open chat"
  >
    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  </button>
{/if}

<!-- Chat panel -->
{#if isOpen}
  <div class="fixed bottom-6 right-6 z-50 w-[380px] max-h-[560px] bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 bg-zinc-900 border-b border-zinc-800">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-xs font-bold text-white">R</div>
        <div>
          <p class="text-sm font-medium text-white">Renci Live Agent</p>
          <div class="flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
            <p class="text-xs text-zinc-500">Gemini 2.5 Flash</p>
          </div>
        </div>
      </div>
      <button onclick={toggleChat} class="text-zinc-500 hover:text-white transition-colors cursor-pointer" aria-label="Close chat">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Messages -->
    <div bind:this={chatContainer} class="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px] max-h-[400px]">
      {#each messages as msg}
        <div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
          <div class="max-w-[85%] px-3.5 py-2.5 rounded-2xl text-sm whitespace-pre-line leading-relaxed {msg.role === 'user' ? 'bg-red-600 text-white rounded-br-md' : 'bg-zinc-800 text-zinc-200 rounded-bl-md'}">
            {msg.text}
          </div>
        </div>
      {/each}

      {#if isLoading}
        <div class="flex justify-start">
          <div class="px-4 py-3 rounded-2xl rounded-bl-md bg-zinc-800">
            <div class="flex gap-1">
              <div class="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" style="animation-delay: 0ms"></div>
              <div class="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" style="animation-delay: 150ms"></div>
              <div class="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" style="animation-delay: 300ms"></div>
            </div>
          </div>
        </div>
      {/if}
    </div>

    <!-- Input -->
    <div class="px-3 py-3 border-t border-zinc-800 bg-zinc-900">
      <div class="flex gap-2">
        <input
          type="text"
          bind:value={input}
          onkeydown={handleKeydown}
          placeholder="Message Renci... 给仁慈发消息..."
          disabled={isLoading}
          class="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-zinc-500 outline-none focus:border-red-600 transition-colors disabled:opacity-50"
        />
        <button
          onclick={sendMessage}
          disabled={isLoading || !input.trim()}
          class="px-3.5 py-2.5 bg-red-600 hover:bg-red-500 disabled:bg-zinc-700 rounded-xl transition-colors cursor-pointer disabled:cursor-not-allowed"
          aria-label="Send message"
        >
          <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </div>
  </div>
{/if}
