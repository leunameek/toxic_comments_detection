<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { WS_BASE } from '$lib/config';
  import { generateUserId, getSession, saveSession } from '$lib/config';
  import { gameSocket } from '$lib/ws.svelte';
  import type { MatchType } from '$lib/types';

  type Mode = 'game' | null;
  let selectedMode = $state<Mode>(null);

  let username  = $state(getSession().username || '');
  let joinCode  = $state('');
  let matchType = $state<MatchType>('5v5');
  let team      = $state<'A' | 'B'>('A');
  let apiKey    = $state(getSession().apiKey || 'player-dev-key-1');
  let creating  = $state(false);
  let joining   = $state(false);
  let error     = $state('');

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
    const iv = setInterval(() => {
      if (gameSocket.room)  { clearInterval(iv); creating = false; goto(`/room/${gameSocket.room.code}`); }
      if (gameSocket.error) { clearInterval(iv); creating = false; error = gameSocket.error; }
    }, 100);
  }

  function joinRoom() {
    if (!username.trim()) { error = 'Elige un nombre de usuario'; return; }
    if (!joinCode.trim())  { error = 'Ingresa el código de sala'; return; }
    error = '';
    joining = true;
    const userId = ensureUserId();
    const teamParam = matchType === '1v1' ? '' : `&team=${team}`;
    const url = `${WS_BASE}/room/${joinCode.toUpperCase()}?user_id=${userId}&username=${encodeURIComponent(username)}${teamParam}&api_key=${apiKey}`;
    gameSocket.connect(url, matchType === '1v1' ? 'B' : team, userId);
    const iv = setInterval(() => {
      if (gameSocket.room)  { clearInterval(iv); joining = false; goto(`/room/${joinCode.toUpperCase()}`); }
      if (gameSocket.error) { clearInterval(iv); joining = false; error = gameSocket.error; }
    }, 100);
  }

  const HOW_IT_WORKS = [
    { icon: 'fa-comment',              color: 'text-blue-400',   title: 'Mensaje enviado',      desc: 'Un jugador escribe un mensaje en el chat durante la partida.' },
    { icon: 'fa-microchip',            color: 'text-indigo-400', title: 'Análisis SVM + TF-IDF', desc: 'El modelo vectoriza el texto y calcula una puntuación de toxicidad en menos de 10ms.' },
    { icon: 'fa-gauge-high',           color: 'text-orange-400', title: 'Puntuación asignada',  desc: 'Cada mensaje recibe un score entre 0% y 100% que determina su nivel de riesgo.' },
    { icon: 'fa-shield-halved',        color: 'text-red-400',    title: 'Acción automática',    desc: 'El sistema acumula strikes y aplica advertencias, silencios, expulsiones o baneos.' },
  ];

  const SCORE_LEVELS = [
    { range: '0 – 40%',  action: 'APPROVE',     label: 'Aprobado',     cls: 'bg-green-900/30 text-green-400 border-green-800/40' },
    { range: '40 – 50%', action: 'REVIEW',      label: 'Revisión',     cls: 'bg-yellow-900/30 text-yellow-400 border-yellow-800/40' },
    { range: '50 – 90%', action: 'TOXIC ALERT', label: 'Alerta',       cls: 'bg-orange-900/30 text-orange-400 border-orange-800/40' },
    { range: '90 – 100%',action: 'BLOCK',       label: 'Bloqueado',    cls: 'bg-red-900/30 text-red-400 border-red-800/40' },
  ];
</script>

<svelte:head>
  <title>ToxicTag — Detección de Toxicidad</title>
</svelte:head>

<div class="min-h-screen flex flex-col">

  <!-- ── Nav ── -->
  <nav class="bg-[#0d0d1a] border-b border-[#1e1e35] px-6 py-3 flex items-center justify-between">
    <div class="flex items-center gap-2.5">
      <img src="/faviconToxicTag.png" alt="ToxicTag" class="w-7 h-7 object-contain" />
      <span class="font-bold text-white text-sm tracking-tight">ToxicTag</span>
    </div>
    <div class="flex items-center gap-4 text-xs">
      <a href="/playground" class="text-gray-400 hover:text-indigo-400 transition-colors">
        <i class="fa-solid fa-flask mr-1"></i>Playground
      </a>
      <a href="/dashboard" class="text-gray-400 hover:text-purple-400 transition-colors">
        <i class="fa-solid fa-chart-line mr-1"></i>Dashboard
      </a>
    </div>
  </nav>

  <main class="flex-1 max-w-3xl w-full mx-auto px-4 py-10 space-y-14">

    <!-- ── Hero ── -->
    <section class="text-center space-y-4">
      <img src="/ToxicTagLogo.png" alt="ToxicTag" class="w-40 h-40 object-contain mx-auto" />
      <div class="inline-flex items-center gap-2 px-3 py-1 bg-blue-900/30 border border-blue-800/40 rounded-full text-blue-400 text-xs font-semibold">
        <i class="fa-solid fa-microchip"></i> Modelo SVM + TF-IDF · Universidad Militar Nueva Granada
      </div>
      <h1 class="text-4xl sm:text-5xl font-black text-white leading-tight tracking-tight">
        Detección de toxicidad<br>
        <span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">en chats de videojuegos</span>
      </h1>
      <p class="text-gray-400 text-base max-w-xl mx-auto leading-relaxed">
        Un sistema de inteligencia artificial que analiza mensajes de chat en tiempo real,
        clasifica su nivel de toxicidad y aplica acciones de moderación automáticas.
      </p>
    </section>

    <!-- ── How it works ── -->
    <section class="space-y-6">
      <h2 class="text-xs font-bold text-gray-500 uppercase tracking-widest text-center">Cómo funciona</h2>

      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {#each HOW_IT_WORKS as step, i}
          <div class="bg-[#12121e] border border-[#1e1e35] rounded-xl p-4 space-y-3">
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-bold text-gray-600 tabular-nums">0{i + 1}</span>
              <i class="fa-solid {step.icon} {step.color}"></i>
            </div>
            <p class="text-white text-xs font-bold leading-snug">{step.title}</p>
            <p class="text-gray-500 text-[11px] leading-relaxed">{step.desc}</p>
          </div>
        {/each}
      </div>

      <!-- Score scale -->
      <div class="bg-[#12121e] border border-[#1e1e35] rounded-xl p-4 space-y-3">
        <p class="text-xs font-bold text-gray-500 uppercase tracking-widest">Escala de puntuación</p>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {#each SCORE_LEVELS as level}
            <div class="flex flex-col gap-1.5">
              <span class="text-[10px] text-gray-600 font-mono">{level.range}</span>
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-bold {level.cls}">
                {level.label}
              </span>
            </div>
          {/each}
        </div>
        <p class="text-[11px] text-gray-600 leading-relaxed">
          Los strikes se acumulan solo si el score supera el 60%. Mensajes con score entre 50–60% generan una alerta pero
          reinician el contador. A partir de 8 strikes acumulados el jugador es baneado permanentemente.
        </p>
      </div>
    </section>

    <!-- ── Notices from redirects ── -->
    {#if $page.url.searchParams.get('reason') === 'kicked'}
      <div class="bg-orange-950 border border-orange-700 rounded-xl p-4 text-center space-y-1">
        <p class="text-orange-400 font-bold text-sm"><i class="fa-solid fa-person-walking-arrow-right mr-1.5"></i>Fuiste expulsado</p>
        <p class="text-orange-300 text-xs">Tu comportamiento en el chat resultó en una expulsión.</p>
      </div>
    {:else if $page.url.searchParams.get('reason') === 'banned'}
      <div class="bg-red-950 border border-red-800 rounded-xl p-4 text-center space-y-1">
        <p class="text-red-400 font-bold text-sm"><i class="fa-solid fa-ban mr-1.5"></i>Cuenta baneada</p>
        <p class="text-red-300 text-xs">Has sido baneado permanentemente.</p>
      </div>
    {/if}

    {#if gameSocket.errorCode === 'BANNED'}
      <div class="bg-red-950 border border-red-800 rounded-xl p-4 text-center space-y-1">
        <p class="text-red-400 font-bold text-sm"><i class="fa-solid fa-ban mr-1.5"></i>Cuenta baneada</p>
        <p class="text-red-300 text-xs">Has sido baneado permanentemente y no puedes volver a jugar.</p>
      </div>
    {/if}

    <!-- ── Mode selector ── -->
    <section class="space-y-6">
      <h2 class="text-xs font-bold text-gray-500 uppercase tracking-widest text-center">Elige tu modo</h2>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">

        <!-- Game -->
        <button
          onclick={() => selectedMode = selectedMode === 'game' ? null : 'game'}
          class="text-left bg-[#12121e] border rounded-xl p-5 space-y-3 transition-all duration-200 hover:border-blue-700/60 hover:bg-[#14142a]
            {selectedMode === 'game' ? 'border-blue-600/70 ring-1 ring-blue-700/40' : 'border-[#1e1e35]'}"
        >
          <div class="w-9 h-9 bg-blue-900/50 border border-blue-800/50 rounded-lg flex items-center justify-center">
            <i class="fa-solid fa-gamepad text-blue-400"></i>
          </div>
          <div>
            <p class="text-white font-bold text-sm">Partida</p>
            <p class="text-gray-500 text-xs mt-0.5 leading-relaxed">
              Crea o únete a una sala de juego. El chat es analizado en tiempo real durante la partida.
            </p>
          </div>
          <p class="text-blue-500 text-xs font-semibold">
            {selectedMode === 'game' ? 'Ocultar opciones' : 'Configurar partida'}
            <i class="fa-solid fa-chevron-{selectedMode === 'game' ? 'up' : 'down'} ml-1"></i>
          </p>
        </button>

        <!-- Playground -->
        <a
          href="/playground"
          class="text-left bg-[#12121e] border border-[#1e1e35] rounded-xl p-5 space-y-3 transition-all duration-200 hover:border-indigo-700/60 hover:bg-[#12121e]"
        >
          <div class="w-9 h-9 bg-indigo-900/50 border border-indigo-800/50 rounded-lg flex items-center justify-center">
            <i class="fa-solid fa-flask text-indigo-400"></i>
          </div>
          <div>
            <p class="text-white font-bold text-sm">Playground</p>
            <p class="text-gray-500 text-xs mt-0.5 leading-relaxed">
              Prueba el modelo con tus propios mensajes. Sin penalizaciones, con la explicación completa del modelo.
            </p>
          </div>
          <p class="text-indigo-400 text-xs font-semibold">
            Abrir playground <i class="fa-solid fa-arrow-right ml-1"></i>
          </p>
        </a>

        <!-- Moderator -->
        <a
          href="/dashboard"
          class="text-left bg-[#12121e] border border-[#1e1e35] rounded-xl p-5 space-y-3 transition-all duration-200 hover:border-purple-700/60 hover:bg-[#12121e]"
        >
          <div class="w-9 h-9 bg-purple-900/50 border border-purple-800/50 rounded-lg flex items-center justify-center">
            <i class="fa-solid fa-shield-halved text-purple-400"></i>
          </div>
          <div>
            <p class="text-white font-bold text-sm">Moderador</p>
            <p class="text-gray-500 text-xs mt-0.5 leading-relaxed">
              Accede al dashboard en tiempo real. Supervisa salas, jugadores y aplica acciones de moderación.
            </p>
          </div>
          <p class="text-purple-400 text-xs font-semibold">
            Ir al dashboard <i class="fa-solid fa-arrow-right ml-1"></i>
          </p>
        </a>
      </div>

      <!-- Game setup (expands inline) -->
      {#if selectedMode === 'game'}
        <div class="bg-[#12121e] border border-blue-700/40 rounded-xl p-5 space-y-5">

          <!-- Username -->
          <div class="space-y-1.5">
            <label for="username-input" class="text-xs font-bold text-gray-400 uppercase tracking-wider">
              Nombre de jugador
            </label>
            <input
              id="username-input"
              bind:value={username}
              type="text"
              placeholder="ej. SnipeMaster"
              maxlength="20"
              class="w-full bg-[#0a0a0f] border border-[#1e1e35] rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 text-sm transition-colors"
            />
          </div>

          <!-- Match type -->
          <div class="space-y-1.5">
            <p class="text-xs font-bold text-gray-400 uppercase tracking-wider">Tipo de partida</p>
            <div class="grid grid-cols-3 gap-2">
              {#each ['1v1', '2v2', '5v5'] as type}
                <button
                  onclick={() => matchType = type as MatchType}
                  class="py-2 rounded-lg text-sm font-medium border transition-colors {matchType === type
                    ? 'bg-blue-600 border-blue-500 text-white'
                    : 'bg-[#0a0a0f] border-[#1e1e35] text-gray-400 hover:border-gray-500'}"
                >{type}</button>
              {/each}
            </div>
          </div>

          <!-- Team (hidden for 1v1) -->
          {#if matchType !== '1v1'}
            <div class="space-y-1.5">
              <p class="text-xs font-bold text-gray-400 uppercase tracking-wider">Equipo (al unirse)</p>
              <div class="grid grid-cols-2 gap-2">
                <button
                  onclick={() => team = 'A'}
                  class="py-2 rounded-lg text-sm font-medium border transition-colors {team === 'A'
                    ? 'bg-blue-600 border-blue-500 text-white'
                    : 'bg-[#0a0a0f] border-[#1e1e35] text-gray-400 hover:border-blue-800'}"
                >Equipo A</button>
                <button
                  onclick={() => team = 'B'}
                  class="py-2 rounded-lg text-sm font-medium border transition-colors {team === 'B'
                    ? 'bg-red-600 border-red-500 text-white'
                    : 'bg-[#0a0a0f] border-[#1e1e35] text-gray-400 hover:border-red-800'}"
                >Equipo B</button>
              </div>
            </div>
          {/if}

          <div class="border-t border-[#1e1e35]"></div>

          <!-- Create -->
          <button
            onclick={createRoom}
            disabled={creating}
            class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
          >
            {#if creating}Creando sala…{:else}<i class="fa-solid fa-plus mr-1.5"></i>Crear sala{/if}
          </button>

          <!-- Join -->
          <div class="flex gap-2">
            <input
              bind:value={joinCode}
              type="text"
              placeholder="Código de sala"
              maxlength="6"
              class="flex-1 bg-[#0a0a0f] border border-[#1e1e35] rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 text-sm uppercase tracking-widest transition-colors"
            />
            <button
              onclick={joinRoom}
              disabled={joining}
              class="bg-[#1e1e35] hover:bg-[#2a2a4e] disabled:opacity-50 text-white font-semibold px-4 rounded-lg transition-colors text-sm"
            >
              {joining ? '…' : 'Unirse'}
            </button>
          </div>

          {#if error}
            <p class="text-red-400 text-xs"><i class="fa-solid fa-circle-exclamation mr-1"></i>{error}</p>
          {/if}
        </div>
      {/if}
    </section>

  </main>

  <!-- ── Footer ── -->
  <footer class="border-t border-[#1e1e35] px-6 py-4 text-center text-[11px] text-gray-700">
    Proyecto de IA · Ingeniería Multimedia · Universidad Militar Nueva Granada · 2026
  </footer>

</div>
