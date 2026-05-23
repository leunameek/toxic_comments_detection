<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { WS_BASE } from '$lib/config';
  import { generateUserId, getSession, saveSession } from '$lib/config';
  import { gameSocket } from '$lib/ws.svelte';
  import type { MatchType } from '$lib/types';

  let username = $state(getSession().username || '');
  let joinCode = $state('');
  let matchType = $state<MatchType>('1v1');
  let team = $state<'A' | 'B'>('A');
  let apiKey = $state(getSession().apiKey || 'player-dev-key-1');
  let creating = $state(false);
  let joining = $state(false);
  let error = $state('');

  function ensureUserId() {
    let { userId } = getSession();
    if (!userId) userId = generateUserId();
    saveSession(userId, username, apiKey);
    return userId;
  }

  function createRoom() {
    if (!username.trim()) { error = 'Elige un nombre de usuario'; return; }
    error = '';
    creating = true;

    const userId = ensureUserId();
    const url = `${WS_BASE}/room/new?user_id=${userId}&username=${encodeURIComponent(username)}&match_type=${matchType}&api_key=${apiKey}`;

    gameSocket.connect(url, 'A', userId);

    // Wait for room_created event to get the code
    const interval = setInterval(() => {
      if (gameSocket.room) {
        clearInterval(interval);
        creating = false;
        goto(`/room/${gameSocket.room.code}`);
      }
      if (gameSocket.error) {
        clearInterval(interval);
        creating = false;
        error = gameSocket.error;
      }
    }, 100);
  }

  function joinRoom() {
    if (!username.trim()) { error = 'Elige un nombre de usuario'; return; }
    if (!joinCode.trim()) { error = 'Ingresa el código de sala'; return; }
    error = '';
    joining = true;

    const userId = ensureUserId();
    const assignedTeam = matchType === '1v1' ? '' : `&team=${team}`;
    const url = `${WS_BASE}/room/${joinCode.toUpperCase()}?user_id=${userId}&username=${encodeURIComponent(username)}${assignedTeam}&api_key=${apiKey}`;

    gameSocket.connect(url, matchType === '1v1' ? 'B' : team, userId);

    const interval = setInterval(() => {
      if (gameSocket.room) {
        clearInterval(interval);
        joining = false;
        goto(`/room/${joinCode.toUpperCase()}`);
      }
      if (gameSocket.error) {
        clearInterval(interval);
        joining = false;
        error = gameSocket.error;
      }
    }, 100);
  }
</script>

<main class="min-h-screen flex items-center justify-center p-4">
  <div class="w-full max-w-md space-y-6">

    <!-- Header -->
    <div class="text-center space-y-1">
      <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-white">
        ToxicTag <span class="text-blue-500">5v5</span>
      </h1>
      <p class="text-gray-500 text-sm">Detección de toxicidad en chats de videojuegos</p>
    </div>

    <!-- Kick / ban notice from redirect -->
    {#if $page.url.searchParams.get('reason') === 'kicked'}
      <div class="bg-orange-950 border border-orange-700 rounded-lg p-3 text-center">
        <p class="text-orange-400 font-bold text-sm"><i class="fa-solid fa-person-walking-arrow-right mr-1"></i>Fuiste expulsado</p>
        <p class="text-orange-300 text-xs mt-0.5">Tu comportamiento en el chat resultó en una expulsión.</p>
      </div>
    {:else if $page.url.searchParams.get('reason') === 'banned'}
      <div class="bg-red-950 border border-red-800 rounded-lg p-3 text-center">
        <p class="text-red-400 font-bold text-sm"><i class="fa-solid fa-ban mr-1"></i>Cuenta baneada</p>
        <p class="text-red-300 text-xs mt-0.5">Has sido baneado permanentemente.</p>
      </div>
    {/if}

    <!-- Card -->
    <div class="bg-[#12121e] border border-[#1e1e35] rounded-xl p-4 sm:p-6 space-y-5">

      <!-- Username -->
      <div class="space-y-1">
        <label class="text-xs font-medium text-gray-400 uppercase tracking-wider">Nombre de jugador</label>
        <input
          bind:value={username}
          type="text"
          placeholder="ej. SnipeMaster"
          maxlength="20"
          class="w-full bg-[#0a0a0f] border border-[#1e1e35] rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 text-sm"
        />
      </div>

      <!-- Match type -->
      <div class="space-y-1">
        <label class="text-xs font-medium text-gray-400 uppercase tracking-wider">Tipo de partida</label>
        <div class="grid grid-cols-3 gap-2">
          {#each ['1v1', '2v2', '5v5'] as type}
            <button
              onclick={() => matchType = type as MatchType}
              class="py-2 rounded-lg text-sm font-medium border transition-colors {matchType === type
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-[#0a0a0f] border-[#1e1e35] text-gray-400 hover:border-gray-500'}"
            >
              {type}
            </button>
          {/each}
        </div>
      </div>

      <!-- Team selector (hidden for 1v1) -->
      {#if matchType !== '1v1'}
        <div class="space-y-1">
          <label class="text-xs font-medium text-gray-400 uppercase tracking-wider">Equipo (al unirse)</label>
          <div class="grid grid-cols-2 gap-2">
            <button
              onclick={() => team = 'A'}
              class="py-2 rounded-lg text-sm font-medium border transition-colors {team === 'A'
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-[#0a0a0f] border-[#1e1e35] text-gray-400 hover:border-blue-800'}"
            >
              Equipo A
            </button>
            <button
              onclick={() => team = 'B'}
              class="py-2 rounded-lg text-sm font-medium border transition-colors {team === 'B'
                ? 'bg-red-600 border-red-500 text-white'
                : 'bg-[#0a0a0f] border-[#1e1e35] text-gray-400 hover:border-red-800'}"
            >
              Equipo B
            </button>
          </div>
        </div>
      {/if}

      <!-- Divider -->
      <div class="border-t border-[#1e1e35]"></div>

      <!-- Create room -->
      <button
        onclick={createRoom}
        disabled={creating}
        class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
      >
        {creating ? 'Creando sala...' : 'Crear sala'}
      </button>

      <!-- Join room -->
      <div class="space-y-2">
        <div class="flex gap-2">
          <input
            bind:value={joinCode}
            type="text"
            placeholder="Código de sala"
            maxlength="6"
            class="flex-1 bg-[#0a0a0f] border border-[#1e1e35] rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 text-sm uppercase tracking-widest"
          />
          <button
            onclick={joinRoom}
            disabled={joining}
            class="bg-[#1e1e35] hover:bg-[#2a2a4e] disabled:opacity-50 text-white font-semibold px-4 rounded-lg transition-colors text-sm"
          >
            {joining ? '...' : 'Unirse'}
          </button>
        </div>
      </div>

      {#if gameSocket.errorCode === 'BANNED'}
        <div class="bg-red-950 border border-red-800 rounded-lg p-3 text-center space-y-1">
          <p class="text-red-400 font-bold text-sm"><i class="fa-solid fa-ban mr-1"></i>Cuenta baneada</p>
          <p class="text-red-300 text-xs">Has sido baneado permanentemente y no puedes volver a jugar.</p>
        </div>
      {:else if error}
        <p class="text-red-400 text-xs text-center">{error}</p>
      {/if}
    </div>

    <!-- Dashboard link -->
    <p class="text-center text-xs text-gray-600">
      ¿Eres moderador? <a href="/dashboard" class="text-blue-500 hover:underline">Ir al dashboard <i class="fa-solid fa-arrow-right"></i></a>
    </p>
  </div>
</main>
