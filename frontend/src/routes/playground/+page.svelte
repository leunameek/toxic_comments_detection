<script lang="ts">
  import { API_BASE } from '$lib/config';
  import type { PlaygroundResult, ToxicAction } from '$lib/types';

  let text = $state('');
  let loading = $state(false);
  let error = $state('');
  let result = $state<PlaygroundResult | null>(null);
  let history = $state<Array<{ text: string; result: PlaygroundResult }>>([]);

  const ACTION_COLOR: Record<ToxicAction, string> = {
    APPROVE:     'bg-green-900/30 text-green-400 border-green-800/50',
    REVIEW:      'bg-yellow-900/30 text-yellow-400 border-yellow-800/50',
    TOXIC_ALERT: 'bg-orange-900/30 text-orange-400 border-orange-800/50',
    BLOCK:       'bg-red-900/30 text-red-400 border-red-800/50',
  };

  const ACTION_ICON: Record<ToxicAction, string> = {
    APPROVE:     'fa-circle-check',
    REVIEW:      'fa-magnifying-glass',
    TOXIC_ALERT: 'fa-triangle-exclamation',
    BLOCK:       'fa-ban',
  };

  const ACTION_LABEL: Record<ToxicAction, string> = {
    APPROVE:     'Aprobado',
    REVIEW:      'Revisión',
    TOXIC_ALERT: 'Alerta tóxico',
    BLOCK:       'Bloqueado',
  };

  const BANNER: Record<ToxicAction, { cls: string; icon: string; txt: string }> = {
    APPROVE:     { cls: 'bg-green-900/20 border-green-800/40 text-green-300',   icon: 'fa-circle-check',         txt: 'En una sesión real este mensaje se entregaría normalmente.' },
    REVIEW:      { cls: 'bg-yellow-900/20 border-yellow-800/40 text-yellow-300', icon: 'fa-magnifying-glass',     txt: 'En una sesión real este mensaje quedaría en cola de revisión humana.' },
    TOXIC_ALERT: { cls: 'bg-orange-900/20 border-orange-800/40 text-orange-300', icon: 'fa-triangle-exclamation', txt: 'En una sesión real esto activaría una alerta y posiblemente un strike automático.' },
    BLOCK:       { cls: 'bg-red-900/20 border-red-800/40 text-red-300',         icon: 'fa-ban',                  txt: 'En una sesión real este mensaje sería bloqueado y el usuario recibiría strikes inmediatos.' },
  };

  const LANG: Record<string, string> = {
    es: 'Español', en: 'English', pt: 'Português',
    fr: 'Français', de: 'Deutsch', it: 'Italiano',
  };

  function scoreColor(score: number): string {
    if (score < 0.40) return '#22c55e';
    if (score < 0.50) return '#eab308';
    if (score < 0.90) return '#f97316';
    return '#ef4444';
  }

  function highlight(cleaned: string, features: string[], color: string): string {
    let html = cleaned
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const sorted = [...features].sort((a, b) => b.length - a.length);
    for (const f of sorted) {
      const safe = f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      html = html.replace(
        new RegExp(safe, 'gi'),
        `<mark style="color:${color};background:${color}22;border-radius:3px;padding:0 2px;font-weight:700">$&</mark>`
      );
    }
    return html;
  }

  function chipAlpha(i: number): string {
    return Math.round(Math.max(0.15, 1 - i * 0.14) * 0x33).toString(16).padStart(2, '0');
  }

  async function analyze() {
    if (!text.trim()) return;
    loading = true;
    error = '';
    try {
      const res = await fetch(`${API_BASE}/playground/classify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) { error = data.detail ?? 'Error al analizar.'; return; }
      result = data;
      history = [{ text, result: data }, ...history].slice(0, 60);
    } catch {
      error = 'No se pudo conectar con el servidor.';
    } finally {
      loading = false;
    }
  }

  function restore(item: { text: string; result: PlaygroundResult }) {
    text = item.text;
    result = item.result;
    error = '';
  }
</script>

<svelte:head>
  <title>Playground — Toxic Chat Detector</title>
</svelte:head>

<div class="h-screen flex flex-col overflow-hidden">

  <!-- Header -->
  <header class="bg-[#12121e] border-b border-[#1e1e35] px-4 py-2.5 flex items-center gap-3 shrink-0">
    <a href="/" class="text-gray-500 hover:text-white text-xs transition-colors">
      <i class="fa-solid fa-arrow-left mr-1"></i>Inicio
    </a>
    <span class="text-[#1e1e35]">|</span>
    <h1 class="text-sm font-bold text-white">Playground</h1>
    <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-indigo-900/40 border border-indigo-700/40 text-indigo-400 rounded-full">
      Sin penalizaciones
    </span>
  </header>

  <div class="flex flex-1 overflow-hidden">

    <!-- Main column -->
    <main class="flex-1 overflow-y-auto p-4 space-y-4 min-w-0">

      <!-- Input card -->
      <div class="bg-[#12121e] border border-[#1e1e35] rounded-xl p-4 space-y-3">
        <p class="text-xs font-bold text-gray-400 uppercase tracking-wider">Mensaje a analizar</p>

        <textarea
          bind:value={text}
          placeholder="Escribe cualquier mensaje y el modelo te dirá si es tóxico y por qué…"
          maxlength="500"
          rows="3"
          onkeydown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) analyze(); }}
          class="w-full bg-[#0a0a0f] border border-[#1e1e35] rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 text-sm resize-none transition-colors"
        ></textarea>

        <div class="flex items-center justify-between">
          <span class="text-[10px] text-gray-600">Ctrl+Enter para analizar</span>
          <span class="text-[10px] {text.length > 450 ? 'text-orange-400' : 'text-gray-600'} font-mono">
            {text.length} / 500
          </span>
        </div>

        <div class="flex items-center gap-2">
          <button
            onclick={analyze}
            disabled={loading || !text.trim()}
            class="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            {#if loading}
              <i class="fa-solid fa-spinner fa-spin mr-1.5"></i>Analizando…
            {:else}
              <i class="fa-solid fa-magnifying-glass mr-1.5"></i>Analizar
            {/if}
          </button>
          <button
            onclick={() => { text = ''; result = null; error = ''; }}
            class="bg-[#1e1e35] hover:bg-[#2a2a45] text-gray-400 hover:text-white text-sm px-3 py-2 rounded-lg transition-colors"
          >
            Limpiar
          </button>
        </div>

        {#if error}
          <p class="text-red-400 text-xs">
            <i class="fa-solid fa-circle-exclamation mr-1"></i>{error}
          </p>
        {/if}
      </div>

      <!-- Result card -->
      {#if result}
        {@const color = scoreColor(result.score)}
        {@const pct = Math.round(result.score * 100)}

        <div class="bg-[#12121e] border border-[#1e1e35] rounded-xl p-4 space-y-4">

          <!-- Score bar -->
          <div class="bg-[#0a0a0f] rounded-lg p-4 space-y-3">
            <div class="flex items-end justify-between">
              <span class="text-xs font-bold text-gray-500 uppercase tracking-wider">Puntuación de toxicidad</span>
              <span class="text-3xl font-black tabular-nums transition-colors" style="color:{color}">{pct}%</span>
            </div>

            <div class="h-2.5 bg-[#1e1e35] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-700"
                style="width:{pct}%; background:linear-gradient(to right, #22c55e 0%, #eab308 38%, #f97316 52%, #ef4444 88%)"
              ></div>
            </div>

            <div class="relative h-5 text-[10px] text-gray-600 select-none">
              <span class="absolute left-0">0%</span>
              <span class="absolute -translate-x-1/2 text-yellow-700" style="left:40%">40% REVIEW</span>
              <span class="absolute -translate-x-1/2 text-orange-700" style="left:50%">50% ALERT</span>
              <span class="absolute -translate-x-full text-red-700" style="left:90%">90% BLOCK</span>
            </div>
          </div>

          <!-- Action pill + meta chips -->
          <div class="flex flex-wrap items-center gap-2">
            <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-bold {ACTION_COLOR[result.action]}">
              <i class="fa-solid {ACTION_ICON[result.action]}"></i>
              {ACTION_LABEL[result.action]}
            </span>
            <span class="text-xs px-2.5 py-1.5 bg-[#0a0a0f] border border-[#1e1e35] rounded-lg text-gray-400">
              Veredicto: <strong style="color:{color}">{result.label_text}</strong>
            </span>
            <span class="text-xs px-2.5 py-1.5 bg-[#0a0a0f] border border-[#1e1e35] rounded-lg text-gray-400">
              <i class="fa-solid fa-bolt mr-1"></i><strong class="text-white">{result.processing_ms.toFixed(1)}ms</strong>
            </span>
            <span class="text-xs px-2.5 py-1.5 bg-[#0a0a0f] border border-[#1e1e35] rounded-lg text-gray-400">
              <i class="fa-solid fa-globe mr-1"></i><strong class="text-white">{LANG[result.language] ?? result.language.toUpperCase()}</strong>
            </span>
          </div>

          <!-- Why section -->
          <div class="bg-[#0a0a0f] border border-[#1e1e35] rounded-lg p-4 space-y-4">
            <p class="text-xs font-bold text-gray-500 uppercase tracking-wider">¿Por qué esta decisión?</p>

            <div class="space-y-1.5">
              <p class="text-[10px] text-gray-600 uppercase tracking-wider">Texto procesado por el modelo</p>
              <div class="text-sm leading-relaxed text-gray-200 bg-[#12121e] rounded-md px-3 py-2 border border-[#1e1e35] min-h-8">
                {#if result.cleaned_text}
                  {@html highlight(result.cleaned_text, result.top_features, color)}
                {:else}
                  <span class="text-gray-600 italic">Vacío tras limpiar</span>
                {/if}
              </div>
            </div>

            <div class="space-y-1.5">
              <p class="text-[10px] text-gray-600 uppercase tracking-wider">Términos que influyeron en la decisión</p>
              {#if result.top_features.length}
                <div class="flex flex-wrap gap-1.5">
                  {#each result.top_features as feature, i}
                    <span
                      class="px-2 py-0.5 rounded text-xs font-bold font-mono border"
                      style="background:{color}{chipAlpha(i)};color:{color};border-color:{color}44"
                      title="Término #{i + 1} más influyente"
                    >{feature}</span>
                  {/each}
                </div>
              {:else}
                <p class="text-xs text-gray-600">Sin términos decisivos identificados.</p>
              {/if}
            </div>
          </div>

          <!-- Context banner -->
          <div class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border text-xs {BANNER[result.action].cls}">
            <i class="fa-solid {BANNER[result.action].icon} shrink-0"></i>
            {BANNER[result.action].txt}
          </div>

        </div>
      {/if}
    </main>

    <!-- History sidebar -->
    <aside class="hidden md:flex w-60 bg-[#0d0d1a] border-l border-[#1e1e35] flex-col shrink-0">
      <div class="flex items-center justify-between p-3 border-b border-[#1e1e35]">
        <p class="text-xs font-bold text-gray-400 uppercase tracking-wider">Historial</p>
        {#if history.length}
          <button
            onclick={() => history = []}
            class="text-[10px] text-gray-600 hover:text-gray-400 underline underline-offset-2"
          >Borrar</button>
        {/if}
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        {#if !history.length}
          <p class="text-gray-700 text-xs text-center mt-6 leading-relaxed">
            Sin análisis aún.<br>¡Prueba un mensaje!
          </p>
        {/if}
        {#each history as item}
          {@const c = scoreColor(item.result.score)}
          <button
            onclick={() => restore(item)}
            class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[#12121e] border border-transparent hover:border-[#1e1e35] transition-colors text-left"
          >
            <div class="w-2 h-2 rounded-full shrink-0" style="background:{c}"></div>
            <span class="flex-1 text-xs text-gray-300 truncate">{item.text}</span>
            <span class="text-[10px] text-gray-600 font-mono shrink-0">{Math.round(item.result.score * 100)}%</span>
          </button>
        {/each}
      </div>
    </aside>

  </div>
</div>
