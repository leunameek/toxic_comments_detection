<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { dashSocket } from '$lib/ws.svelte';
  import { WS_BASE } from '$lib/config';

  let apiKey = $state('moderator-dev-key-1');
  let connected = $state(false);
  let activeTab = $state<'rooms' | 'events' | 'players'>('events');

  function connect() {
    dashSocket.connect(`${WS_BASE}/dashboard?api_key=${apiKey}`);
    connected = true;
  }

  const eventColors: Record<string, string> = {
    chat: 'text-gray-300',
    kill_feed: 'text-yellow-400',
    round_start: 'text-blue-400',
    round_end: 'text-blue-300',
    match_start: 'text-green-400',
    match_end: 'text-green-300',
    moderation: 'text-red-400',
    player_joined: 'text-purple-400',
    player_left: 'text-gray-500',
  };

  const statusColor: Record<string, string> = {
    ACTIVE: 'text-green-400',
    WARNED: 'text-yellow-400',
    TIMEOUT: 'text-orange-400',
    BANNED: 'text-red-500',
  };

  const actionColor: Record<string, string> = {
    APPROVE: 'bg-green-900/30 text-green-400',
    REVIEW: 'bg-yellow-900/30 text-yellow-400',
    TOXIC_ALERT: 'bg-orange-900/30 text-orange-400',
    BLOCK: 'bg-red-900/30 text-red-400',
  };

  onDestroy(() => dashSocket.disconnect());
</script>

<div class="h-screen flex flex-col overflow-hidden">

  <!-- Header -->
  <header class="bg-[#12121e] border-b border-[#1e1e35] px-3 sm:px-4 py-2 flex items-center justify-between shrink-0 gap-2">
    <div class="flex items-center gap-2 sm:gap-3 min-w-0">
      <a href="/" class="text-gray-500 hover:text-white text-xs shrink-0"><i class="fa-solid fa-arrow-left mr-1"></i><span class="hidden sm:inline">Inicio</span></a>
      <span class="text-gray-600 hidden sm:inline">|</span>
      <h1 class="text-sm font-bold text-white truncate">Dashboard de Moderación</h1>
    </div>
    <div class="flex items-center gap-2 shrink-0">
      {#if !dashSocket.connected}
        <input
          bind:value={apiKey}
          type="text"
          placeholder="API Key"
          class="bg-[#0a0a0f] border border-[#1e1e35] rounded px-2 py-1 text-xs text-white w-32 sm:w-48"
        />
        <button
          onclick={connect}
          class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded font-semibold"
        >
          Conectar
        </button>
      {:else}
        <div class="w-2 h-2 rounded-full bg-green-500"></div>
        <span class="text-xs text-green-400">En vivo</span>
      {/if}
    </div>
  </header>

  <!-- Mobile tab bar (hidden on md+) -->
  <div class="md:hidden bg-[#0d0d1a] border-b border-[#1e1e35] flex shrink-0">
    <button
      onclick={() => activeTab = 'rooms'}
      class="flex-1 py-2 text-xs font-bold uppercase tracking-wider transition-colors {activeTab === 'rooms' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-500 hover:text-gray-300'}"
    >
      Salas ({dashSocket.rooms.length})
    </button>
    <button
      onclick={() => activeTab = 'events'}
      class="flex-1 py-2 text-xs font-bold uppercase tracking-wider transition-colors {activeTab === 'events' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-500 hover:text-gray-300'}"
    >
      Feed
    </button>
    <button
      onclick={() => activeTab = 'players'}
      class="flex-1 py-2 text-xs font-bold uppercase tracking-wider transition-colors {activeTab === 'players' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-500 hover:text-gray-300'}"
    >
      Jugadores ({Object.keys(dashSocket.players).length})
    </button>
  </div>

  <div class="flex flex-1 overflow-hidden">

    <!-- Left: Active rooms -->
    <aside class="{activeTab === 'rooms' ? 'flex' : 'hidden'} md:flex w-full md:w-56 bg-[#0d0d1a] border-r border-[#1e1e35] flex-col shrink-0">
      <p class="text-xs font-bold text-gray-400 uppercase tracking-wider p-3 border-b border-[#1e1e35] hidden md:block">
        Salas activas ({dashSocket.rooms.length})
      </p>
      <div class="flex-1 overflow-y-auto p-2 space-y-2">
        {#if dashSocket.rooms.length === 0}
          <p class="text-gray-600 text-xs text-center mt-4">Sin salas activas</p>
        {/if}
        {#each dashSocket.rooms as room}
          <div class="bg-[#12121e] border border-[#1e1e35] rounded-lg p-2.5 space-y-1.5">
            <div class="flex justify-between items-center">
              <span class="font-mono text-blue-400 text-xs font-bold">{room.code}</span>
              <span class="text-[10px] text-gray-500">{room.match_type}</span>
            </div>
            <div class="flex items-center justify-between text-sm font-bold">
              <span class="text-blue-400">{room.score_a}</span>
              <span class="text-gray-600 text-xs">R{room.current_round}</span>
              <span class="text-red-400">{room.score_b}</span>
            </div>
            <div class="text-[10px] text-gray-500">
              {room.players_online} jugador{room.players_online !== 1 ? 'es' : ''} online
            </div>
          </div>
        {/each}
      </div>
    </aside>

    <!-- Center: Live event feed -->
    <main class="{activeTab === 'events' ? 'flex' : 'hidden'} md:flex flex-1 flex-col overflow-hidden min-w-0">
      <p class="text-xs font-bold text-gray-400 uppercase tracking-wider p-3 border-b border-[#1e1e35] shrink-0">
        Feed en tiempo real
      </p>
      <div class="flex-1 overflow-y-auto p-2 sm:p-3 space-y-1.5 flex flex-col-reverse">
        {#each dashSocket.events as event}
          <div class="flex items-start gap-1.5 sm:gap-2 text-xs font-mono">
            <span class="text-gray-700 shrink-0 w-10 sm:w-14 truncate">{event.room}</span>
            <span class="{eventColors[event.type] ?? 'text-gray-400'} shrink-0 w-20 sm:w-24 truncate">{event.type}</span>

            {#if event.type === 'chat'}
              <div class="flex flex-col gap-0.5 min-w-0 flex-1">
                <div class="flex items-center gap-1.5 min-w-0">
                  <span class="{actionColor[(event.payload.action as string)] ?? ''} px-1.5 rounded text-[10px] shrink-0">
                    {event.payload.action}
                  </span>
                  <span class="text-white truncate">{event.payload.user_id}: {event.payload.text}</span>
                  {#if event.payload.score !== undefined}
                    <span class="text-gray-600 shrink-0">{(event.payload.score as number).toFixed(2)}</span>
                  {/if}
                </div>
                {#if (event.payload.top_features as string[])?.length}
                  <div class="flex flex-wrap gap-1 pl-1">
                    {#each event.payload.top_features as string[] as feature}
                      <span class="bg-red-900/40 border border-red-800/50 text-red-300 text-[10px] px-1.5 py-px rounded font-sans">
                        {feature}
                      </span>
                    {/each}
                  </div>
                {/if}
              </div>

            {:else if event.type === 'kill_feed'}
              <span class="text-yellow-300/70 truncate">{event.payload.text}</span>

            {:else if event.type === 'moderation'}
              <span class="text-red-400 shrink-0 truncate max-w-[80px]">{event.payload.user_id}</span>
              <span class="text-orange-400 shrink-0">{event.payload.action}</span>
              <span class="text-gray-500 shrink-0">x{event.payload.strikes}</span>

            {:else if event.type === 'round_end'}
              <span class="text-blue-300">
                {event.payload.score_a}:{event.payload.score_b}
                {#if event.payload.winner === 'A'}<i class="fa-solid fa-arrow-left mr-1"></i>Equipo A{:else}Equipo B <i class="fa-solid fa-arrow-right ml-1"></i>{/if}
              </span>

            {:else if event.type === 'match_end'}
              <span class="text-green-300 font-bold">
                Ganador: Equipo {event.payload.winner} | {event.payload.score_a}:{event.payload.score_b}
              </span>

            {:else}
              <span class="text-gray-500 truncate">{JSON.stringify(event.payload).slice(0, 80)}</span>
            {/if}
          </div>
        {/each}
        {#if dashSocket.events.length === 0 && dashSocket.connected}
          <p class="text-gray-700 text-xs text-center">Esperando eventos…</p>
        {/if}
      </div>
    </main>

    <!-- Right: Player monitor -->
    <aside class="{activeTab === 'players' ? 'flex' : 'hidden'} md:flex w-full md:w-64 bg-[#0d0d1a] border-l border-[#1e1e35] flex-col shrink-0">
      <p class="text-xs font-bold text-gray-400 uppercase tracking-wider p-3 border-b border-[#1e1e35] hidden md:block">
        Jugadores ({Object.keys(dashSocket.players).length})
      </p>
      <div class="flex-1 overflow-y-auto p-2 space-y-2">
        {#each Object.values(dashSocket.players) as player}
          <div class="bg-[#12121e] border border-[#1e1e35] rounded-lg p-2.5 space-y-2">
            <div class="flex justify-between items-start">
              <div class="min-w-0 flex-1">
                <p class="text-white text-xs font-semibold truncate">{player.username}</p>
                <p class="text-gray-600 text-[10px] font-mono truncate">{player.user_id}</p>
              </div>
              <span class="text-[10px] {statusColor[player.status] ?? 'text-gray-400'} font-bold shrink-0 ml-2">
                {player.status}
              </span>
            </div>

            <!-- Strike bar -->
            <div class="space-y-0.5">
              <div class="flex justify-between text-[10px] text-gray-500">
                <span>Strikes</span>
                <span class="{player.strikes >= 8 ? 'text-red-500' : player.strikes >= 5 ? 'text-orange-400' : player.strikes >= 3 ? 'text-yellow-400' : 'text-gray-400'} font-bold">
                  {player.strikes}
                </span>
              </div>
              <div class="h-1 bg-[#0a0a0f] rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500 {player.strikes >= 8 ? 'bg-red-600' : player.strikes >= 5 ? 'bg-orange-500' : player.strikes >= 3 ? 'bg-yellow-500' : 'bg-green-600'}"
                  style="width: {Math.min((player.strikes / 8) * 100, 100)}%"
                ></div>
              </div>
            </div>

            <!-- Stats row -->
            <div class="grid grid-cols-3 gap-1 text-center text-[10px]">
              <div>
                <p class="text-gray-600">Msgs</p>
                <p class="text-white font-medium">{player.total_messages}</p>
              </div>
              <div>
                <p class="text-gray-600">Tóxicos</p>
                <p class="text-orange-400 font-medium">{player.toxic_messages}</p>
              </div>
              <div>
                <p class="text-gray-600">Score</p>
                <p class="{player.toxicity_score > 0.6 ? 'text-red-400' : player.toxicity_score > 0.3 ? 'text-yellow-400' : 'text-green-400'} font-medium">
                  {player.toxicity_score.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        {/each}
        {#if Object.keys(dashSocket.players).length === 0 && dashSocket.connected}
          <p class="text-gray-700 text-xs text-center mt-4">Sin jugadores activos</p>
        {/if}
      </div>
    </aside>
  </div>
</div>
