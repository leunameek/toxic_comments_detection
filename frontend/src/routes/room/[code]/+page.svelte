<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { onDestroy } from 'svelte';
  import { gameSocket } from '$lib/ws.svelte';
  import { getSession } from '$lib/config';

  const code = $page.params.code;
  const { username, userId } = getSession();

  let chatInput = $state('');
  let chatEl = $state<HTMLDivElement | null>(null);
  let rejoining = $state(false);

  // Permanent ban: always redirect
  $effect(() => {
    if (gameSocket.errorCode === 'BANNED') {
      goto('/?reason=banned');
    }
  });

  function tryRejoin() {
    rejoining = true;
    gameSocket.reconnect();
    // Give the socket time to connect; rejoining flag clears on connect/error
    setTimeout(() => { rejoining = false; }, 4000);
  }

  // Action color map
  const actionColor: Record<string, string> = {
    APPROVE: 'text-gray-300',
    REVIEW: 'text-yellow-400',
    TOXIC_ALERT: 'text-orange-400',
    BLOCK: 'text-red-500',
  };

  const modColor: Record<string, string> = {
    WARN: 'text-yellow-400',
    TIMEOUT: 'text-orange-400',
    KICK: 'text-red-400',
    BAN: 'text-red-600 font-bold',
  };

  function sendChat() {
    const text = chatInput.trim();
    if (!text || !gameSocket.connected) return;
    gameSocket.sendChat(text);
    chatInput = '';
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  }

  // Auto-scroll chat to bottom
  $effect(() => {
    gameSocket.messages; // reactive dep
    if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
  });

  onDestroy(() => gameSocket.disconnect());
</script>

<div class="h-screen flex flex-col overflow-hidden">

  <!-- Top bar -->
  <header class="bg-[#12121e] border-b border-[#1e1e35] px-3 sm:px-4 py-2 flex items-center justify-between shrink-0 gap-2">
    <div class="flex items-center gap-2 sm:gap-3 min-w-0">
      <button onclick={() => goto('/')} class="text-gray-500 hover:text-white text-xs shrink-0">
        <i class="fa-solid fa-arrow-left mr-1"></i><span class="hidden sm:inline">Salir</span>
      </button>
      <span class="text-gray-600 hidden sm:inline">|</span>
      <span class="font-mono text-blue-400 font-bold tracking-widest text-sm">{code}</span>
      <span class="text-xs text-gray-600 hidden sm:inline">{gameSocket.room?.match_type ?? ''}</span>
    </div>

    <!-- Score -->
    {#if gameSocket.room && gameSocket.room.status !== 'WAITING'}
      <div class="flex items-center gap-2 sm:gap-3 text-sm font-bold shrink-0">
        <span class="text-blue-400">{gameSocket.room.score_a}</span>
        <span class="text-gray-600">:</span>
        <span class="text-red-400">{gameSocket.room.score_b}</span>
        {#if gameSocket.room.current_round > 0}
          <span class="text-xs text-gray-500 font-normal hidden sm:inline">
            {#if gameSocket.room.is_sudden_death}<i class="fa-solid fa-bolt mr-1"></i>MUERTE SÚBITA{:else}Ronda {gameSocket.room.current_round}{/if}
          </span>
        {/if}
      </div>
    {/if}

    <div class="flex items-center gap-1.5 shrink-0">
      <div class="w-2 h-2 rounded-full {gameSocket.connected ? 'bg-green-500' : 'bg-red-500'}"></div>
      <span class="text-xs text-gray-500 hidden sm:inline">{gameSocket.connected ? 'Conectado' : 'Desconectado'}</span>
    </div>
  </header>

  <!-- Mobile teams bar (hidden on md+) -->
  {#if gameSocket.room}
    <div class="md:hidden bg-[#0d0d1a] border-b border-[#1e1e35] px-3 py-2 flex gap-3 shrink-0">
      <div class="flex-1 min-w-0">
        <p class="text-[10px] font-bold text-blue-400 uppercase tracking-wider mb-1">Equipo A</p>
        <div class="flex flex-wrap gap-1">
          {#each gameSocket.room.team_a as uid}
            <span class="text-[10px] bg-blue-900/30 border border-blue-900/50 rounded px-1.5 py-0.5 text-white truncate max-w-[90px]">
              {gameSocket.room.usernames[uid] ?? uid}{uid === userId ? ' ★' : ''}
            </span>
          {/each}
        </div>
      </div>
      <div class="w-px bg-[#1e1e35] shrink-0"></div>
      <div class="flex-1 min-w-0">
        <p class="text-[10px] font-bold text-red-400 uppercase tracking-wider mb-1">Equipo B</p>
        <div class="flex flex-wrap gap-1">
          {#each gameSocket.room.team_b as uid}
            <span class="text-[10px] bg-red-900/30 border border-red-900/50 rounded px-1.5 py-0.5 text-white truncate max-w-[90px]">
              {gameSocket.room.usernames[uid] ?? uid}{uid === userId ? ' ★' : ''}
            </span>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  <!-- Disconnected / kicked overlay -->
  {#if !gameSocket.connected && !gameSocket.matchOver}
    <div class="fixed inset-0 z-40 bg-black/80 flex items-center justify-center p-4">
      <div class="bg-[#12121e] border rounded-xl p-6 max-w-sm w-full text-center space-y-4
        {gameSocket.kicked || gameSocket.errorCode === 'KICKED' ? 'border-red-800/60' : 'border-[#1e1e35]'}">

        {#if gameSocket.kicked || gameSocket.errorCode === 'KICKED'}
          <div class="w-12 h-12 bg-red-900/40 rounded-full flex items-center justify-center mx-auto">
            <i class="fa-solid fa-person-walking-arrow-right text-red-400 text-xl"></i>
          </div>
          <div>
            <p class="text-white font-bold">Fuiste expulsado</p>
            <p class="text-gray-500 text-sm mt-1">
              {gameSocket.errorCode === 'KICKED'
                ? 'Aún estás sancionado. Espera a que un moderador levante la sanción e inténtalo de nuevo.'
                : 'Un moderador te ha expulsado de la sala.'}
            </p>
          </div>
        {:else}
          <div class="w-12 h-12 bg-[#1e1e35] rounded-full flex items-center justify-center mx-auto">
            <i class="fa-solid fa-plug-circle-xmark text-gray-400 text-xl"></i>
          </div>
          <div>
            <p class="text-white font-bold">Desconectado</p>
            <p class="text-gray-500 text-sm mt-1">Perdiste la conexión con la sala.</p>
          </div>
        {/if}

        <div class="flex flex-col gap-2">
          <button
            onclick={tryRejoin}
            disabled={rejoining}
            class="w-full bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-white text-sm font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {#if rejoining}
              <span class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              Reconectando…
            {:else}
              <i class="fa-solid fa-rotate-right"></i>
              {gameSocket.kicked || gameSocket.errorCode === 'KICKED' ? 'Intentar reingresar' : 'Reconectar'}
            {/if}
          </button>
          <button onclick={() => goto('/')} class="w-full text-gray-600 hover:text-gray-400 text-sm py-2 transition-colors">
            Salir al inicio
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Match over overlay -->
  {#if gameSocket.matchOver}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
      <div class="text-center space-y-4">
        <p class="text-5xl sm:text-6xl">
          {#if gameSocket.matchWinner === gameSocket.room?.my_team}
            <i class="fa-solid fa-trophy text-yellow-400"></i>
          {:else}
            <i class="fa-solid fa-skull text-gray-400"></i>
          {/if}
        </p>
        <h2 class="text-2xl sm:text-3xl font-bold {gameSocket.matchWinner === 'A' ? 'text-blue-400' : 'text-red-400'}">
          {gameSocket.matchWinner === gameSocket.room?.my_team ? '¡Victoria!' : 'Derrota'}
        </h2>
        <p class="text-gray-400 text-sm sm:text-base">
          Equipo A {gameSocket.room?.score_a} — {gameSocket.room?.score_b} Equipo B
        </p>
        <button
          onclick={() => goto('/')}
          class="mt-4 bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-semibold"
        >
          Volver al inicio
        </button>
      </div>
    </div>
  {/if}

  <div class="flex flex-1 overflow-hidden">

    <!-- Team A sidebar (desktop only) -->
    <aside class="hidden md:flex w-32 lg:w-40 bg-[#0d0d1a] border-r border-[#1e1e35] p-3 flex-col gap-2 shrink-0 overflow-y-auto">
      <p class="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1">Equipo A</p>
      {#if gameSocket.room}
        {#each gameSocket.room.team_a as uid}
          <div class="bg-[#12121e] rounded-lg p-2 border border-blue-900/30">
            <p class="text-xs text-white font-medium truncate">
              {gameSocket.room.usernames[uid] ?? uid}
            </p>
            {#if uid === userId}
              <span class="text-[10px] text-blue-400">tú</span>
            {/if}
          </div>
        {/each}
      {/if}
    </aside>

    <!-- Main: kill feed + chat -->
    <main class="flex-1 flex flex-col overflow-hidden min-w-0">

      <!-- Kill feed -->
      <div class="h-24 sm:h-32 md:h-36 bg-[#0a0a0f] border-b border-[#1e1e35] overflow-y-auto p-2 sm:p-3 space-y-1 shrink-0">
        {#if gameSocket.killFeed.length === 0}
          <p class="text-gray-700 text-xs text-center pt-2 sm:pt-4">El kill feed aparecerá aquí cuando empiece la partida</p>
        {/if}
        {#each gameSocket.killFeed as entry}
          <p class="text-xs text-yellow-300/80 font-mono">
            <span class="text-gray-600">[R{entry.round}]</span> {entry.text}
          </p>
        {/each}
      </div>

      <!-- Chat messages -->
      <div bind:this={chatEl} class="flex-1 overflow-y-auto p-2 sm:p-3 space-y-2">
        {#if gameSocket.room?.status === 'WAITING'}
          <div class="flex flex-col items-center justify-center h-full gap-2 text-center">
            <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p class="text-gray-500 text-sm">Esperando jugadores…</p>
            <p class="text-blue-400 font-mono font-bold tracking-widest">{code}</p>
            <p class="text-gray-600 text-xs">Comparte este código para invitar</p>
          </div>
        {/if}

        {#each gameSocket.messages as msg}
          <div class="flex gap-2 {msg.user_id === userId ? 'flex-row-reverse' : ''}">
            <div class="max-w-[85%] sm:max-w-[75%] space-y-0.5">
              <div class="flex items-center gap-1 {msg.user_id === userId ? 'justify-end' : ''}">
                <span class="text-[11px] text-gray-500 truncate max-w-[100px]">{msg.user_id}</span>
                <span class="text-[10px] {actionColor[msg.action] ?? 'text-gray-400'} shrink-0"><i class="fa-solid fa-circle mr-0.5"></i>{msg.action}</span>
              </div>
              <div class="bg-[#12121e] border {msg.action === 'APPROVE' ? 'border-[#1e1e35]' : msg.action === 'REVIEW' ? 'border-yellow-800' : 'border-red-900'} rounded-lg px-3 py-1.5 text-sm text-white break-words">
                {msg.text}
              </div>
              {#if msg.auto_action}
                <p class="text-[10px] {modColor[msg.auto_action]} {msg.user_id === userId ? 'text-right' : ''}">
                  <i class="fa-solid fa-triangle-exclamation mr-1"></i>{msg.auto_action}
                </p>
              {/if}
            </div>
          </div>
        {/each}
      </div>

      <!-- Chat input -->
      <div class="p-2 sm:p-3 border-t border-[#1e1e35] bg-[#12121e] shrink-0">
        {#if gameSocket.timedOut}
          <div class="flex items-center justify-center gap-2 py-1">
            <i class="fa-solid fa-clock text-orange-400 text-sm"></i>
            <p class="text-orange-400 text-sm font-medium">Estás en timeout — no puedes enviar mensajes</p>
          </div>
        {:else if gameSocket.room?.status === 'IN_PROGRESS' || gameSocket.room?.status === 'WAITING'}
          <div class="flex gap-2">
            <input
              bind:value={chatInput}
              onkeydown={handleKey}
              type="text"
              placeholder="Escribe un mensaje…"
              maxlength="500"
              disabled={!gameSocket.connected}
              class="flex-1 bg-[#0a0a0f] border border-[#1e1e35] rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 text-sm disabled:opacity-40"
            />
            <button
              onclick={sendChat}
              disabled={!chatInput.trim() || !gameSocket.connected}
              aria-label="Enviar mensaje"
              class="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white px-4 rounded-lg text-sm font-semibold transition-colors shrink-0"
            >
              <i class="fa-solid fa-paper-plane"></i>
            </button>
          </div>
        {:else if gameSocket.room?.status === 'FINISHED'}
          <p class="text-center text-gray-600 text-sm">Partida terminada</p>
        {/if}
      </div>
    </main>

    <!-- Team B sidebar (desktop only) -->
    <aside class="hidden md:flex w-32 lg:w-40 bg-[#0d0d1a] border-l border-[#1e1e35] p-3 flex-col gap-2 shrink-0 overflow-y-auto">
      <p class="text-xs font-bold text-red-400 uppercase tracking-wider mb-1">Equipo B</p>
      {#if gameSocket.room}
        {#each gameSocket.room.team_b as uid}
          <div class="bg-[#12121e] rounded-lg p-2 border border-red-900/30">
            <p class="text-xs text-white font-medium truncate">
              {gameSocket.room.usernames[uid] ?? uid}
            </p>
            {#if uid === userId}
              <span class="text-[10px] text-red-400">tú</span>
            {/if}
          </div>
        {/each}
      {/if}

      <!-- Round history -->
      {#if gameSocket.room && gameSocket.room.rounds.length > 0}
        <div class="mt-4 space-y-1">
          <p class="text-[10px] text-gray-600 uppercase tracking-wider">Rondas</p>
          {#each gameSocket.room.rounds as r}
            <div class="flex justify-between text-[11px]">
              <span class="text-gray-600">R{r.round}{#if r.is_sudden_death}<i class="fa-solid fa-bolt ml-0.5 text-yellow-400"></i>{/if}</span>
              <span class="{r.winner === 'A' ? 'text-blue-400' : 'text-red-400'}">{r.score_a}:{r.score_b}</span>
            </div>
          {/each}
        </div>
      {/if}
    </aside>
  </div>
</div>
