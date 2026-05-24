<script lang="ts">
  import { onDestroy } from 'svelte';
  import { dashSocket } from '$lib/ws.svelte';
  import { WS_BASE } from '$lib/config';
  import type { ModerationAction } from '$lib/types';

  let apiKey    = $state('moderator-dev-key-1');
  let activeTab = $state<'rooms' | 'feed' | 'players'>('feed');
  let confirmBan= $state<string | null>(null); // user_id awaiting ban confirmation

  function connect() {
    dashSocket.connect(`${WS_BASE}/dashboard?api_key=${apiKey}`);
  }

  function modAction(userId: string, action: ModerationAction) {
    if (action === 'BAN') { confirmBan = userId; return; }
    dashSocket.sendModAction(userId, action);
  }

  function confirmBanAction() {
    if (confirmBan) { dashSocket.sendModAction(confirmBan, 'BAN'); confirmBan = null; }
  }

  // ── Event display helpers ──────────────────────────────────────────────────

  const ACTION_CLS: Record<string, string> = {
    APPROVE:     'bg-green-900/40 text-green-400 border-green-800/50',
    REVIEW:      'bg-yellow-900/40 text-yellow-400 border-yellow-800/50',
    TOXIC_ALERT: 'bg-orange-900/40 text-orange-400 border-orange-800/50',
    BLOCK:       'bg-red-900/40 text-red-500 border-red-800/50',
  };

  const MOD_CLS: Record<string, string> = {
    WARN:    'text-yellow-400',
    TIMEOUT: 'text-orange-400',
    KICK:    'text-red-400',
    BAN:     'text-red-600',
  };

  const STATUS_CLS: Record<string, string> = {
    ACTIVE:  'bg-green-900/40 text-green-400 border-green-800/40',
    WARNED:  'bg-yellow-900/40 text-yellow-400 border-yellow-800/40',
    TIMEOUT: 'bg-orange-900/40 text-orange-400 border-orange-800/40',
    BANNED:  'bg-red-900/40 text-red-400 border-red-800/40',
  };

  const ROOM_STATUS_DOT: Record<string, string> = {
    WAITING:     'bg-yellow-500',
    IN_PROGRESS: 'bg-green-500',
    FINISHED:    'bg-gray-600',
  };

  function fmt(date: Date): string {
    return date.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function strikeColor(n: number): string {
    if (n >= 8) return 'bg-red-600';
    if (n >= 5) return 'bg-orange-500';
    if (n >= 3) return 'bg-yellow-500';
    return 'bg-green-600';
  }

  function toxColor(score: number): string {
    if (score > 0.6) return 'text-red-400';
    if (score > 0.3) return 'text-yellow-400';
    return 'text-green-400';
  }

  onDestroy(() => dashSocket.disconnect());
</script>

<!-- Ban confirmation modal -->
{#if confirmBan}
  <div class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
    <div class="bg-[#12121e] border border-red-800/60 rounded-xl p-6 max-w-sm w-full space-y-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-red-900/50 rounded-lg flex items-center justify-center">
          <i class="fa-solid fa-ban text-red-400"></i>
        </div>
        <div>
          <p class="text-white font-bold text-sm">Confirmar baneo permanente</p>
          <p class="text-gray-500 text-xs font-mono mt-0.5">{confirmBan}</p>
        </div>
      </div>
      <p class="text-gray-400 text-xs leading-relaxed">
        Esta acción es irreversible. El jugador será expulsado inmediatamente y no podrá volver a conectarse.
      </p>
      <div class="flex gap-2">
        <button onclick={() => confirmBan = null} class="flex-1 bg-[#1e1e35] hover:bg-[#2a2a45] text-gray-400 text-sm font-semibold py-2 rounded-lg transition-colors">
          Cancelar
        </button>
        <button onclick={confirmBanAction} class="flex-1 bg-red-700 hover:bg-red-600 text-white text-sm font-semibold py-2 rounded-lg transition-colors">
          <i class="fa-solid fa-ban mr-1.5"></i>Banear
        </button>
      </div>
    </div>
  </div>
{/if}

<div class="h-screen flex flex-col overflow-hidden bg-[#0a0a0f]">

  <!-- ── Header ── -->
  <header class="bg-[#0d0d1a] border-b border-[#1e1e35] px-4 py-2.5 flex items-center justify-between shrink-0 gap-3">
    <div class="flex items-center gap-3 min-w-0">
      <a href="/" class="text-gray-600 hover:text-white text-xs transition-colors shrink-0">
        <i class="fa-solid fa-arrow-left mr-1"></i><span class="hidden sm:inline">Inicio</span>
      </a>
      <span class="text-[#1e1e35] hidden sm:inline">|</span>
      <div class="flex items-center gap-2 min-w-0">
        <img src="/faviconToxicTag.png" alt="ToxicTag" class="w-5 h-5 object-contain shrink-0" />
        <h1 class="text-sm font-bold text-white truncate">Dashboard de Moderación</h1>
      </div>
    </div>

    <!-- Stats bar (visible when connected) -->
    {#if dashSocket.connected}
      <div class="hidden md:flex items-center gap-4 text-xs">
        <div class="flex items-center gap-1.5 text-gray-400">
          <i class="fa-solid fa-door-open text-blue-400"></i>
          <span><strong class="text-white">{dashSocket.rooms.length}</strong> salas</span>
        </div>
        <div class="flex items-center gap-1.5 text-gray-400">
          <i class="fa-solid fa-users text-indigo-400"></i>
          <span><strong class="text-white">{Object.keys(dashSocket.players).length}</strong> jugadores</span>
        </div>
        <div class="flex items-center gap-1.5 text-gray-400">
          <i class="fa-solid fa-bolt text-yellow-400"></i>
          <span><strong class="text-white">{dashSocket.events.length}</strong> eventos</span>
        </div>
      </div>
    {/if}

    <!-- Connection -->
    <div class="flex items-center gap-2 shrink-0">
      {#if !dashSocket.connected}
        <input
          bind:value={apiKey}
          type="text"
          placeholder="API Key"
          class="bg-[#0a0a0f] border border-[#1e1e35] rounded-lg px-2.5 py-1.5 text-xs text-white w-36 sm:w-48 focus:outline-none focus:border-purple-600 transition-colors"
        />
        <button
          onclick={connect}
          class="bg-purple-700 hover:bg-purple-600 text-white text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors"
        >
          <i class="fa-solid fa-plug mr-1"></i>Conectar
        </button>
      {:else}
        <div class="flex items-center gap-1.5">
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
          <span class="text-xs text-green-400 font-medium">En vivo</span>
        </div>
      {/if}
    </div>
  </header>

  <!-- Mobile tab bar -->
  <div class="md:hidden bg-[#0d0d1a] border-b border-[#1e1e35] flex shrink-0">
    {#each [['rooms','fa-door-open',`Salas (${dashSocket.rooms.length})`], ['feed','fa-bolt','Feed'], ['players','fa-users',`Jugadores (${Object.keys(dashSocket.players).length})`]] as [tab, icon, label]}
      <button
        onclick={() => activeTab = tab as typeof activeTab}
        class="flex-1 py-2 text-xs font-bold uppercase tracking-wider transition-colors flex items-center justify-center gap-1.5
          {activeTab === tab ? 'text-purple-400 border-b-2 border-purple-400' : 'text-gray-600 hover:text-gray-400'}"
      >
        <i class="fa-solid {icon}"></i>{label}
      </button>
    {/each}
  </div>

  <!-- ── Body ── -->
  <div class="flex flex-1 overflow-hidden">

    <!-- ── Left: Rooms ── -->
    <aside class="{activeTab === 'rooms' ? 'flex' : 'hidden'} md:flex w-full md:w-52 bg-[#0d0d1a] border-r border-[#1e1e35] flex-col shrink-0">
      <div class="px-3 py-2.5 border-b border-[#1e1e35] shrink-0">
        <p class="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-1.5">
          <i class="fa-solid fa-door-open text-blue-400"></i> Salas activas
          <span class="ml-auto bg-[#1e1e35] text-gray-400 rounded px-1.5 py-px text-[10px]">{dashSocket.rooms.length}</span>
        </p>
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-2">
        {#if dashSocket.rooms.length === 0}
          <div class="flex flex-col items-center gap-2 mt-8 text-gray-700">
            <i class="fa-solid fa-door-open text-2xl"></i>
            <p class="text-xs text-center">Sin salas activas</p>
          </div>
        {/if}

        {#each dashSocket.rooms as room}
          <div class="bg-[#12121e] border border-[#1e1e35] rounded-xl p-3 space-y-2.5 hover:border-[#2a2a4e] transition-colors">
            <!-- Code + status -->
            <div class="flex items-center justify-between">
              <span class="font-mono font-black text-blue-400 text-base tracking-widest">{room.code}</span>
              <div class="flex items-center gap-1">
                <div class="w-1.5 h-1.5 rounded-full {ROOM_STATUS_DOT[room.status] ?? 'bg-gray-600'}"></div>
                <span class="text-[9px] text-gray-600 uppercase">{room.match_type}</span>
              </div>
            </div>

            <!-- Scoreboard -->
            <div class="flex items-center justify-center gap-3">
              <div class="text-center">
                <p class="text-[9px] text-blue-500 font-bold uppercase">A</p>
                <p class="text-2xl font-black text-blue-400 leading-none tabular-nums">{room.score_a}</p>
              </div>
              <div class="text-center">
                <p class="text-[10px] text-gray-600">R{room.current_round}</p>
              </div>
              <div class="text-center">
                <p class="text-[9px] text-red-500 font-bold uppercase">B</p>
                <p class="text-2xl font-black text-red-400 leading-none tabular-nums">{room.score_b}</p>
              </div>
            </div>

            <!-- Footer -->
            <div class="flex items-center justify-between text-[10px] text-gray-600">
              <span><i class="fa-solid fa-user mr-1"></i>{room.players_online}</span>
              <span class="{room.status === 'IN_PROGRESS' ? 'text-green-600' : room.status === 'WAITING' ? 'text-yellow-600' : 'text-gray-600'}">
                {room.status === 'IN_PROGRESS' ? 'En curso' : room.status === 'WAITING' ? 'Esperando' : 'Finalizada'}
              </span>
            </div>
          </div>
        {/each}
      </div>
    </aside>

    <!-- ── Center: Event feed ── -->
    <main class="{activeTab === 'feed' ? 'flex' : 'hidden'} md:flex flex-1 flex-col overflow-hidden min-w-0">
      <div class="px-4 py-2.5 border-b border-[#1e1e35] shrink-0 flex items-center justify-between">
        <p class="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-1.5">
          <i class="fa-solid fa-bolt text-yellow-400"></i> Feed en tiempo real
        </p>
        {#if dashSocket.events.length > 0}
          <span class="text-[10px] text-gray-600">{dashSocket.events.length} eventos</span>
        {/if}
      </div>

      <div class="flex-1 overflow-y-auto p-3 flex flex-col-reverse gap-1">

        {#if dashSocket.events.length === 0 && dashSocket.connected}
          <div class="flex flex-col items-center gap-2 m-auto text-gray-700">
            <i class="fa-solid fa-satellite-dish text-3xl animate-pulse"></i>
            <p class="text-xs">Esperando eventos…</p>
          </div>
        {/if}

        {#if !dashSocket.connected}
          <div class="flex flex-col items-center gap-2 m-auto text-gray-700">
            <i class="fa-solid fa-plug-circle-xmark text-3xl"></i>
            <p class="text-xs">Conecta con tu API key para ver el feed</p>
          </div>
        {/if}

        {#each dashSocket.events as ev}
          <div class="flex items-start gap-2 text-xs py-1.5 px-2 rounded-lg hover:bg-[#12121e] transition-colors group">
            <!-- Time + room -->
            <div class="flex flex-col items-end shrink-0 gap-0.5 pt-px">
              <span class="text-[10px] text-gray-700 font-mono tabular-nums">{fmt(ev.timestamp)}</span>
              {#if ev.room && ev.room !== '—'}
                <span class="text-[9px] font-mono text-blue-700 bg-blue-900/20 px-1 rounded">{ev.room}</span>
              {/if}
            </div>

            <!-- Event content -->
            <div class="flex-1 min-w-0">

              {#if ev.type === 'chat'}
                <div class="space-y-1">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="inline-flex items-center gap-1 px-1.5 py-px rounded border text-[10px] font-bold {ACTION_CLS[ev.payload.action as string] ?? ''}">
                      {ev.payload.action}
                    </span>
                    <span class="text-gray-400 font-semibold">{ev.payload.user_id}</span>
                    <span class="text-gray-300 truncate">"{ev.payload.text}"</span>
                    <span class="text-gray-600 font-mono text-[10px] shrink-0">{((ev.payload.score as number) * 100).toFixed(0)}%</span>
                  </div>
                  {#if (ev.payload.top_features as string[])?.length}
                    <div class="flex flex-wrap gap-1 pl-0.5">
                      {#each ev.payload.top_features as string[] as f}
                        <span class="bg-red-900/30 border border-red-800/40 text-red-300 text-[10px] px-1.5 py-px rounded font-mono">{f}</span>
                      {/each}
                    </div>
                  {/if}
                </div>

              {:else if ev.type === 'moderation'}
                <div class="flex items-center gap-1.5 flex-wrap">
                  <i class="fa-solid fa-gavel text-orange-400 shrink-0"></i>
                  <span class="text-gray-300 font-semibold">{ev.payload.user_id}</span>
                  <span class="font-bold {MOD_CLS[ev.payload.action as string] ?? 'text-gray-400'}">{ev.payload.action}</span>
                  <span class="text-gray-600">·</span>
                  <span class="text-gray-500">{ev.payload.strikes} strike{(ev.payload.strikes as number) !== 1 ? 's' : ''}</span>
                  {#if ev.payload.reason}
                    <span class="text-gray-600 truncate">— {ev.payload.reason}</span>
                  {/if}
                </div>

              {:else if ev.type === 'kill_feed'}
                <div class="flex items-center gap-1.5 text-yellow-400/80">
                  <i class="fa-solid fa-skull text-[10px] shrink-0"></i>
                  <span class="truncate">{ev.payload.text}</span>
                </div>

              {:else if ev.type === 'round_start'}
                <div class="flex items-center gap-1.5">
                  <i class="fa-solid fa-play text-blue-400 text-[10px] shrink-0"></i>
                  <span class="text-blue-300 font-semibold">Ronda {ev.payload.round}</span>
                  {#if ev.payload.is_sudden_death}
                    <span class="text-red-400 text-[10px] font-bold bg-red-900/30 border border-red-800/40 px-1.5 py-px rounded">MUERTE SÚBITA</span>
                  {/if}
                </div>

              {:else if ev.type === 'round_end'}
                <div class="flex items-center gap-1.5">
                  <i class="fa-solid fa-flag-checkered text-blue-300 text-[10px] shrink-0"></i>
                  <span class="text-gray-300">Ronda {ev.payload.round} —</span>
                  <span class="font-bold text-blue-400">{ev.payload.score_a}</span>
                  <span class="text-gray-600">:</span>
                  <span class="font-bold text-red-400">{ev.payload.score_b}</span>
                  <span class="text-gray-500">Equipo {ev.payload.winner} gana</span>
                </div>

              {:else if ev.type === 'match_start'}
                <div class="flex items-center gap-1.5">
                  <i class="fa-solid fa-circle-play text-green-400 text-[10px] shrink-0"></i>
                  <span class="text-green-300 font-semibold">Partida iniciada</span>
                  <span class="text-gray-500">·</span>
                  <span class="text-blue-400">{(ev.payload.team_a as string[])?.join(', ')}</span>
                  <span class="text-gray-600">vs</span>
                  <span class="text-red-400">{(ev.payload.team_b as string[])?.join(', ')}</span>
                </div>

              {:else if ev.type === 'match_end'}
                <div class="flex items-center gap-1.5">
                  <i class="fa-solid fa-trophy text-yellow-400 text-[10px] shrink-0"></i>
                  <span class="text-yellow-300 font-bold">Partida terminada</span>
                  <span class="text-gray-500">—</span>
                  <span class="font-bold {ev.payload.winner === 'A' ? 'text-blue-400' : 'text-red-400'}">
                    Equipo {ev.payload.winner}
                  </span>
                  <span class="text-gray-400">{ev.payload.score_a}:{ev.payload.score_b}</span>
                </div>

              {:else if ev.type === 'player_joined'}
                <div class="flex items-center gap-1.5 text-purple-400">
                  <i class="fa-solid fa-right-to-bracket text-[10px] shrink-0"></i>
                  <span class="font-semibold">{ev.payload.username ?? ev.payload.user_id}</span>
                  <span class="text-gray-500">se unió al Equipo {ev.payload.team}</span>
                </div>

              {:else if ev.type === 'player_left'}
                <div class="flex items-center gap-1.5 text-gray-500">
                  <i class="fa-solid fa-right-from-bracket text-[10px] shrink-0"></i>
                  <span>{ev.payload.user_id} abandonó la sala</span>
                </div>

              {:else}
                <div class="flex items-center gap-1.5 text-gray-600">
                  <span class="text-gray-700 font-mono">{ev.type}</span>
                  <span class="truncate">{JSON.stringify(ev.payload).slice(0, 80)}</span>
                </div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </main>

    <!-- ── Right: Players ── -->
    <aside class="{activeTab === 'players' ? 'flex' : 'hidden'} md:flex w-full md:w-72 bg-[#0d0d1a] border-l border-[#1e1e35] flex-col shrink-0">
      <div class="px-3 py-2.5 border-b border-[#1e1e35] shrink-0">
        <p class="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-1.5">
          <i class="fa-solid fa-users text-indigo-400"></i> Jugadores
          <span class="ml-auto bg-[#1e1e35] text-gray-400 rounded px-1.5 py-px text-[10px]">{Object.keys(dashSocket.players).length}</span>
        </p>
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-2">
        {#if Object.keys(dashSocket.players).length === 0 && dashSocket.connected}
          <div class="flex flex-col items-center gap-2 mt-8 text-gray-700">
            <i class="fa-solid fa-users text-2xl"></i>
            <p class="text-xs text-center">Sin jugadores activos</p>
          </div>
        {/if}

        {#each Object.values(dashSocket.players) as player: import('$lib/types').PlayerState}
          <div class="bg-[#12121e] border border-[#1e1e35] rounded-xl p-3 space-y-3 hover:border-[#2a2a4e] transition-colors">

            <!-- Name + status -->
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="text-white text-sm font-bold truncate leading-tight">{player.username}</p>
                <p class="text-gray-600 text-[10px] font-mono truncate">{player.user_id}</p>
              </div>
              <span class="text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0 {STATUS_CLS[player.status] ?? 'text-gray-400'}">
                {player.status}
              </span>
            </div>

            <!-- Strikes bar -->
            <div class="space-y-1">
              <div class="flex justify-between text-[10px]">
                <span class="text-gray-600 flex items-center gap-1"><i class="fa-solid fa-bolt"></i> Strikes</span>
                <span class="font-bold tabular-nums {player.strikes >= 8 ? 'text-red-400' : player.strikes >= 5 ? 'text-orange-400' : player.strikes >= 3 ? 'text-yellow-400' : 'text-gray-500'}">
                  {player.strikes} / 8
                </span>
              </div>
              <div class="h-1.5 bg-[#0a0a0f] rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500 {strikeColor(player.strikes)}"
                  style="width:{Math.min((player.strikes / 8) * 100, 100)}%"
                ></div>
              </div>
            </div>

            <!-- Stats -->
            <div class="grid grid-cols-3 gap-1 text-center">
              <div class="bg-[#0a0a0f] rounded-lg py-1.5">
                <p class="text-[9px] text-gray-600 uppercase">Msgs</p>
                <p class="text-white text-sm font-bold">{player.total_messages}</p>
              </div>
              <div class="bg-[#0a0a0f] rounded-lg py-1.5">
                <p class="text-[9px] text-gray-600 uppercase">Tóxicos</p>
                <p class="text-orange-400 text-sm font-bold">{player.toxic_messages}</p>
              </div>
              <div class="bg-[#0a0a0f] rounded-lg py-1.5">
                <p class="text-[9px] text-gray-600 uppercase">Score</p>
                <p class="text-sm font-bold {toxColor(player.toxicity_score)}">{(player.toxicity_score * 100).toFixed(0)}%</p>
              </div>
            </div>

            <!-- Toxicity bar -->
            <div class="h-1 bg-[#0a0a0f] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                style="width:{Math.min(player.toxicity_score * 100, 100)}%; background:linear-gradient(to right,#22c55e,#eab308 40%,#f97316 60%,#ef4444 80%)"
              ></div>
            </div>

            <!-- Pardon button — only when player is penalised -->
            {#if dashSocket.connected && player.status !== 'ACTIVE'}
              <button
                onclick={() => dashSocket.sendModAction(player.user_id, 'PARDON', 'Perdón manual del moderador')}
                class="w-full py-1.5 rounded-lg text-[10px] font-bold transition-colors bg-green-900/30 hover:bg-green-900/50 text-green-400 border border-green-700/40 flex items-center justify-center gap-1.5"
                title="Revertir sanción y restaurar acceso"
              >
                <i class="fa-solid fa-rotate-left"></i> Revertir sanción
              </button>
            {/if}

            <!-- Mod action buttons -->
            {#if dashSocket.connected && player.status !== 'BANNED'}
              <div class="grid grid-cols-4 gap-1">
                <button
                  onclick={() => modAction(player.user_id, 'WARN')}
                  class="py-1.5 rounded-lg text-[10px] font-bold transition-colors bg-yellow-900/30 hover:bg-yellow-900/50 text-yellow-400 border border-yellow-800/40"
                  title="Advertir"
                ><i class="fa-solid fa-triangle-exclamation"></i></button>
                <button
                  onclick={() => modAction(player.user_id, 'TIMEOUT')}
                  class="py-1.5 rounded-lg text-[10px] font-bold transition-colors bg-orange-900/30 hover:bg-orange-900/50 text-orange-400 border border-orange-800/40"
                  title="Timeout (5 min)"
                ><i class="fa-solid fa-clock"></i></button>
                <button
                  onclick={() => modAction(player.user_id, 'KICK')}
                  class="py-1.5 rounded-lg text-[10px] font-bold transition-colors bg-red-900/30 hover:bg-red-900/50 text-red-400 border border-red-800/40"
                  title="Expulsar de la sala"
                ><i class="fa-solid fa-person-walking-arrow-right"></i></button>
                <button
                  onclick={() => modAction(player.user_id, 'BAN')}
                  class="py-1.5 rounded-lg text-[10px] font-bold transition-colors bg-red-950/60 hover:bg-red-900/60 text-red-600 border border-red-900/60"
                  title="Banear permanentemente"
                ><i class="fa-solid fa-ban"></i></button>
              </div>
            {/if}

          </div>
        {/each}
      </div>
    </aside>

  </div>
</div>
