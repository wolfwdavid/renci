<script lang="ts">
  let demoMessages: Array<{role: string, text: string}> = $state([]);
  let demoStep = $state(0);
  let isTyping = $state(false);

  const conversation = [
    { role: 'user', text: 'Hi' },
    { role: 'agent', text: 'Welcome to Renci! I help small businesses build their online presence for free.\n\nWhat is the name of your business?\n你的店叫什么名字？' },
    { role: 'user', text: "Wong's Bakery 黄记饼家" },
    { role: 'agent', text: "Got it: Wong\'s Bakery 黄记饼家\n\nWhat kind of business? Reply:\n1=Restaurant  2=Bakery  3=Grocery\n4=Salon  5=Laundry  6=Retail  7=Other" },
    { role: 'user', text: '2' },
    { role: 'agent', text: 'What is your address?\n你的地址是什么？' },
    { role: 'user', text: '65 Mott St' },
    { role: 'agent', text: '65 Mott Street, New York, NY 10013\n\nCorrect? (Y/N)' },
    { role: 'user', text: 'Y' },
    { role: 'agent', text: 'What email?\n你的电邮是什么？' },
    { role: 'user', text: 'wong@gmail.com' },
    { role: 'agent', text: "You're all set! Your website is live:\nrenci.app/wongs-bakery\n\nText me anytime to update it!\n随时发短信给我来更新！" },
    { role: 'user', text: 'Update hours Mon-Sat 7am-6pm' },
    { role: 'agent', text: 'Hours updated!\n  Mon: 7:00-18:00\n  Tue: 7:00-18:00\n  Wed: 7:00-18:00\n  Thu: 7:00-18:00\n  Fri: 7:00-18:00\n  Sat: 7:00-18:00' },
    { role: 'user', text: 'How much PPP funding did bakeries in my area get?' },
    { role: 'agent', text: 'In zip 10013: 3 bakeries received PPP loans totaling $60,300. Average loan: $20,100. All 3 loans were forgiven (100%).' },
  ];

  async function advanceDemo() {
    if (demoStep >= conversation.length || isTyping) return;
    const msg = conversation[demoStep];
    if (msg.role === 'user') {
      demoMessages = [...demoMessages, msg];
      demoStep++;
      // Auto-advance to agent response after short delay
      isTyping = true;
      await new Promise(r => setTimeout(r, 800));
      if (demoStep < conversation.length) {
        demoMessages = [...demoMessages, conversation[demoStep]];
        demoStep++;
      }
      isTyping = false;
    }
  }

  function resetDemo() {
    demoMessages = [];
    demoStep = 0;
    isTyping = false;
  }

  // PPP data for the visualization
  const pppData = [
    { industry: 'Restaurants', loans: 8, total: 841000, pct: 55 },
    { industry: 'Bakeries', loans: 3, total: 60300, pct: 4 },
    { industry: 'Grocery', loans: 2, total: 143000, pct: 9 },
    { industry: 'Salons/Barbers', loans: 3, total: 29700, pct: 2 },
    { industry: 'Retail/Other', loans: 14, total: 452600, pct: 30 },
  ];
</script>

<svelte:head>
  <title>Renci 仁慈 — AI Agent for Chinatown Small Businesses</title>
  <meta name="description" content="An AI-powered SMS agent helping Manhattan Chinatown's mom-and-pop shops build websites, manage social media, and access civic data — powered by Gemini on Google Cloud." />
</svelte:head>

<div class="min-h-screen bg-zinc-950 text-white">
  <!-- Nav -->
  <nav class="fixed top-0 w-full z-50 bg-zinc-950/80 backdrop-blur-xl border-b border-white/5">
    <div class="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-red-600 flex items-center justify-center font-bold text-sm">R</div>
        <span class="text-lg font-semibold tracking-tight">Renci <span class="text-red-400 font-normal">仁慈</span></span>
      </div>
      <div class="hidden md:flex gap-8 text-sm text-zinc-400">
        <a href="#demo" class="hover:text-white transition-colors">Demo</a>
        <a href="#features" class="hover:text-white transition-colors">Features</a>
        <a href="#data" class="hover:text-white transition-colors">PPP Data</a>
        <a href="#architecture" class="hover:text-white transition-colors">Architecture</a>
      </div>
    </div>
  </nav>

  <!-- Hero -->
  <header class="pt-32 pb-20 px-6 relative overflow-hidden">
    <!-- Gradient orb background -->
    <div class="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-red-600/20 rounded-full blur-[120px] pointer-events-none"></div>
    <div class="absolute top-40 left-1/4 w-[300px] h-[300px] bg-amber-500/10 rounded-full blur-[100px] pointer-events-none"></div>

    <div class="max-w-6xl mx-auto relative">
      <div class="text-center mb-6">
        <span class="inline-block px-3 py-1 rounded-full text-xs font-medium bg-red-600/10 text-red-400 border border-red-600/20 mb-6">
          NYC Build With AI Hackathon — Build for Everyone
        </span>
      </div>

      <h1 class="text-5xl md:text-7xl font-bold text-center leading-[1.1] mb-6 tracking-tight">
        Chinatown's businesses<br/>
        <span class="bg-gradient-to-r from-red-400 via-amber-300 to-red-400 bg-clip-text text-transparent">deserve to be seen.</span>
      </h1>

      <p class="text-xl text-zinc-400 text-center max-w-2xl mx-auto mb-4">
        An AI agent that helps mom-and-pop shops build their digital presence — via SMS, voice, and photo. Powered by Gemini on Google Cloud.
      </p>
      <p class="text-lg text-zinc-500 text-center mb-12">
        给华埠的小店建网站，发短信、打电话、拍照就行。
      </p>

      <div class="flex justify-center gap-4 mb-16">
        <a href="#demo" class="px-6 py-3 bg-red-600 hover:bg-red-500 rounded-lg font-medium transition-colors">
          Try the Demo
        </a>
        <a href="#architecture" class="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg font-medium border border-zinc-700 transition-colors">
          View Architecture
        </a>
      </div>

      <!-- Capability pills -->
      <div class="flex flex-wrap justify-center gap-3 text-sm">
        <div class="px-4 py-2 rounded-full bg-zinc-900 border border-zinc-800 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-green-400"></span> See — Photo & Menu Analysis
        </div>
        <div class="px-4 py-2 rounded-full bg-zinc-900 border border-zinc-800 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-blue-400"></span> Hear — Voice via Gemini Live API
        </div>
        <div class="px-4 py-2 rounded-full bg-zinc-900 border border-zinc-800 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-amber-400"></span> Speak — Bilingual EN/ZH
        </div>
      </div>
    </div>
  </header>

  <!-- Interactive SMS Demo -->
  <section id="demo" class="py-24 px-6">
    <div class="max-w-6xl mx-auto">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold mb-4">See it in action</h2>
        <p class="text-zinc-400">Click through a real registration flow — from first text to live website.</p>
      </div>

      <div class="max-w-sm mx-auto">
        <!-- Phone frame -->
        <div class="bg-zinc-900 rounded-[2.5rem] p-2 border border-zinc-800 shadow-2xl shadow-red-600/5">
          <div class="bg-zinc-950 rounded-[2rem] overflow-hidden">
            <!-- Phone header -->
            <div class="bg-zinc-900 px-6 py-3 flex items-center gap-3 border-b border-zinc-800">
              <div class="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-xs font-bold">R</div>
              <div>
                <p class="text-sm font-medium">Renci Agent</p>
                <p class="text-xs text-zinc-500">SMS &middot; Gemini 2.5</p>
              </div>
            </div>

            <!-- Messages -->
            <div class="h-[420px] overflow-y-auto p-4 space-y-3 scroll-smooth" id="demo-messages">
              {#if demoMessages.length === 0}
                <div class="text-center text-zinc-600 text-sm mt-20">
                  <p>Tap the button below to start</p>
                  <p class="text-zinc-700 mt-1">点击下面的按钮开始</p>
                </div>
              {/if}

              {#each demoMessages as msg}
                <div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
                  <div class="max-w-[85%] px-4 py-2.5 rounded-2xl text-sm whitespace-pre-line {msg.role === 'user' ? 'bg-red-600 text-white rounded-br-md' : 'bg-zinc-800 text-zinc-200 rounded-bl-md'}">
                    {msg.text}
                  </div>
                </div>
              {/each}

              {#if isTyping}
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

            <!-- Action button -->
            <div class="px-4 py-3 border-t border-zinc-800">
              {#if demoStep < conversation.length}
                <button
                  onclick={advanceDemo}
                  disabled={isTyping}
                  class="w-full py-2.5 rounded-xl text-sm font-medium transition-all
                    {isTyping ? 'bg-zinc-800 text-zinc-500 cursor-wait' : 'bg-red-600 hover:bg-red-500 text-white cursor-pointer'}"
                >
                  {#if isTyping}
                    Renci is typing...
                  {:else}
                    Send: "{conversation[demoStep].text}"
                  {/if}
                </button>
              {:else}
                <button onclick={resetDemo} class="w-full py-2.5 rounded-xl text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 cursor-pointer">
                  Restart Demo
                </button>
              {/if}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Features -->
  <section id="features" class="py-24 px-6 bg-zinc-900/50">
    <div class="max-w-6xl mx-auto">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold mb-4">What Renci does 仁慈能做什么</h2>
        <p class="text-zinc-400">An AI agent — not a chatbot. Renci takes action.</p>
      </div>

      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        <!-- Feature cards -->
        <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-colors">
          <div class="w-10 h-10 rounded-xl bg-red-600/10 flex items-center justify-center mb-4">
            <span class="text-red-400 text-lg">SMS</span>
          </div>
          <h3 class="font-semibold text-lg mb-2">SMS Registration</h3>
          <p class="text-zinc-400 text-sm">Text us to register. 5 messages and your website is live. No app download, no email signup forms.</p>
          <p class="text-zinc-600 text-xs mt-2">发短信注册，5条信息网站就上线</p>
        </div>

        <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-colors">
          <div class="w-10 h-10 rounded-xl bg-amber-600/10 flex items-center justify-center mb-4">
            <span class="text-amber-400 text-lg">AI</span>
          </div>
          <h3 class="font-semibold text-lg mb-2">Gemini-Powered Agent</h3>
          <p class="text-zinc-400 text-sm">Understands natural language in English and Chinese. Uses tool-calling to execute real actions — not just replies.</p>
          <p class="text-zinc-600 text-xs mt-2">理解中英文，执行真实操作</p>
        </div>

        <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-colors">
          <div class="w-10 h-10 rounded-xl bg-green-600/10 flex items-center justify-center mb-4">
            <span class="text-green-400 text-lg">WEB</span>
          </div>
          <h3 class="font-semibold text-lg mb-2">Instant Websites</h3>
          <p class="text-zinc-400 text-sm">Beautiful, mobile-first business websites generated automatically. Bilingual. Updated in real-time via SMS.</p>
          <p class="text-zinc-600 text-xs mt-2">自动生成双语网站，短信实时更新</p>
        </div>

        <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-colors">
          <div class="w-10 h-10 rounded-xl bg-blue-600/10 flex items-center justify-center mb-4">
            <span class="text-blue-400 text-lg">IMG</span>
          </div>
          <h3 class="font-semibold text-lg mb-2">Photo Analysis</h3>
          <p class="text-zinc-400 text-sm">Send a photo of your menu — Gemini Vision extracts items and prices. Send a storefront photo for your website hero.</p>
          <p class="text-zinc-600 text-xs mt-2">拍菜单照片，AI自动提取菜品价格</p>
        </div>

        <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-colors">
          <div class="w-10 h-10 rounded-xl bg-purple-600/10 flex items-center justify-center mb-4">
            <span class="text-purple-400 text-lg">PPP</span>
          </div>
          <h3 class="font-semibold text-lg mb-2">PPP Loan Insights</h3>
          <p class="text-zinc-400 text-sm">Access COVID-era PPP loan data for your neighborhood. See how much businesses like yours received and forgiveness rates.</p>
          <p class="text-zinc-600 text-xs mt-2">查看你附近商家的PPP贷款数据</p>
        </div>

        <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-colors">
          <div class="w-10 h-10 rounded-xl bg-pink-600/10 flex items-center justify-center mb-4">
            <span class="text-pink-400 text-lg">ZH</span>
          </div>
          <h3 class="font-semibold text-lg mb-2">Bilingual by Default</h3>
          <p class="text-zinc-400 text-sm">Write in English or Chinese — Renci detects your language and responds accordingly. Simplified and Traditional supported.</p>
          <p class="text-zinc-600 text-xs mt-2">中英双语，简繁体都支持</p>
        </div>
      </div>
    </div>
  </section>

  <!-- PPP Data Visualization -->
  <section id="data" class="py-24 px-6">
    <div class="max-w-6xl mx-auto">
      <div class="text-center mb-16">
        <span class="inline-block px-3 py-1 rounded-full text-xs font-medium bg-purple-600/10 text-purple-400 border border-purple-600/20 mb-4">
          Build for Everyone — SBA PPP Loan Data
        </span>
        <h2 class="text-3xl md:text-4xl font-bold mb-4">Chinatown PPP Loans at a Glance</h2>
        <p class="text-zinc-400">Real data from the SBA Paycheck Protection Program for zip codes 10002 & 10013.</p>
      </div>

      <!-- Stats row -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center">
          <p class="text-3xl font-bold text-red-400">30</p>
          <p class="text-zinc-500 text-sm mt-1">Businesses</p>
        </div>
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center">
          <p class="text-3xl font-bold text-amber-400">$1.5M</p>
          <p class="text-zinc-500 text-sm mt-1">Total Loans</p>
        </div>
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center">
          <p class="text-3xl font-bold text-green-400">97%</p>
          <p class="text-zinc-500 text-sm mt-1">Forgiven</p>
        </div>
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center">
          <p class="text-3xl font-bold text-blue-400">224</p>
          <p class="text-zinc-500 text-sm mt-1">Jobs Supported</p>
        </div>
      </div>

      <!-- Industry breakdown bars -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 md:p-8">
        <h3 class="font-semibold text-lg mb-6">PPP Loans by Industry</h3>
        <div class="space-y-4">
          {#each pppData as row}
            <div>
              <div class="flex justify-between text-sm mb-1.5">
                <span class="text-zinc-300">{row.industry}</span>
                <span class="text-zinc-500">{row.loans} loans &middot; ${(row.total / 1000).toFixed(0)}K</span>
              </div>
              <div class="h-3 bg-zinc-800 rounded-full overflow-hidden">
                <div class="h-full rounded-full bg-gradient-to-r from-red-600 to-amber-500 transition-all duration-1000" style="width: {row.pct}%"></div>
              </div>
            </div>
          {/each}
        </div>
        <p class="text-zinc-600 text-xs mt-6">Source: SBA Paycheck Protection Program FOIA Data &middot; Filtered for Manhattan Chinatown (10002, 10013)</p>
      </div>
    </div>
  </section>

  <!-- Architecture -->
  <section id="architecture" class="py-24 px-6 bg-zinc-900/50">
    <div class="max-w-6xl mx-auto">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold mb-4">Architecture</h2>
        <p class="text-zinc-400">Built on Google Cloud with Gemini 2.5 Flash and the Agent Development Kit.</p>
      </div>

      <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 md:p-8 font-mono text-sm overflow-x-auto">
        <pre class="text-zinc-400 leading-relaxed"><span class="text-red-400">Owner</span> ──SMS/MMS/Voice──&gt; <span class="text-amber-400">Twilio</span> ──webhook──&gt; <span class="text-green-400">Cloud Run (FastAPI)</span>
                                                    │
                                              <span class="text-blue-400">SMS Router</span>
                                            ┌───────┴────────┐
                                            v                v
                                     <span class="text-purple-400">Registration</span>     <span class="text-red-400">Gemini Agent</span>
                                       (6-step)       (ADK + Tool Use)
                                            │                │
                                            v          ┌─────┼─────┐
                                       <span class="text-amber-400">Firestore</span>     │     │     │
                                                  <span class="text-green-400">Tools</span>  <span class="text-blue-400">PPP</span>  <span class="text-purple-400">Vision</span>
                                                    │     │     │
                                               <span class="text-amber-400">Firestore</span> <span class="text-amber-400">CSV</span>  <span class="text-amber-400">GCS</span>
                                                    │
                                                    v
                                          <span class="text-green-400">Cloud Run (SvelteKit)</span>
                                           renci.app/[business]</pre>
      </div>

      <div class="grid md:grid-cols-3 gap-4 mt-8">
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <p class="text-xs text-zinc-500 mb-1">AI MODEL</p>
          <p class="font-medium">Gemini 2.5 Flash</p>
          <p class="text-zinc-500 text-sm">via Google GenAI SDK</p>
        </div>
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <p class="text-xs text-zinc-500 mb-1">AGENT FRAMEWORK</p>
          <p class="font-medium">Google ADK</p>
          <p class="text-zinc-500 text-sm">9 custom tools</p>
        </div>
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <p class="text-xs text-zinc-500 mb-1">INFRASTRUCTURE</p>
          <p class="font-medium">Google Cloud</p>
          <p class="text-zinc-500 text-sm">Cloud Run + Firestore + GCS</p>
        </div>
      </div>
    </div>
  </section>

  <!-- The Problem -->
  <section class="py-24 px-6">
    <div class="max-w-4xl mx-auto text-center">
      <h2 class="text-3xl md:text-4xl font-bold mb-8">The Problem 问题</h2>
      <div class="grid md:grid-cols-2 gap-8 text-left">
        <div class="bg-zinc-900 border border-red-600/20 rounded-2xl p-6">
          <p class="text-4xl font-bold text-red-400 mb-2">-47%</p>
          <p class="text-zinc-300 font-medium mb-2">Chinatown businesses lost since 2000</p>
          <p class="text-zinc-500 text-sm">Manhattan's Chinatown has seen nearly half its small businesses close. Those remaining struggle without digital presence.</p>
        </div>
        <div class="bg-zinc-900 border border-amber-600/20 rounded-2xl p-6">
          <p class="text-4xl font-bold text-amber-400 mb-2">73%</p>
          <p class="text-zinc-300 font-medium mb-2">Have no website</p>
          <p class="text-zinc-500 text-sm">Most Chinatown shops have zero online presence. No website, no Google listing, no social media. Invisible to anyone searching online.</p>
        </div>
      </div>
      <p class="text-zinc-400 mt-10 text-lg max-w-2xl mx-auto">
        These owners work 12-hour days. They don't have time to learn website builders. But they all have a phone. <strong class="text-white">Renci meets them where they are.</strong>
      </p>
    </div>
  </section>

  <!-- Footer -->
  <footer class="py-12 px-6 border-t border-zinc-800">
    <div class="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
      <div class="flex items-center gap-2">
        <div class="w-6 h-6 rounded bg-red-600 flex items-center justify-center font-bold text-xs">R</div>
        <span class="text-sm text-zinc-400">Renci 仁慈 — Helping Chinatown thrive online.</span>
      </div>
      <div class="text-sm text-zinc-600">
        NYC Build With AI Hackathon 2026 &middot; Build for Everyone
      </div>
    </div>
  </footer>
</div>
