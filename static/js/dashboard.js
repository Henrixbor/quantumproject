/**
 * Quantum MCP Relayer — Dashboard Logic
 * Handles profile loading, usage stats, playground, key management, and billing.
 */

(function () {
  'use strict';

  /* ====================================================================
     Guard: redirect to auth if not logged in
     ==================================================================== */
  Auth.guardDashboard();

  /* ====================================================================
     State
     ==================================================================== */

  var userProfile = null;
  var activePlaygroundTab = 'portfolio';

  var TIER_LIMITS = {
    free: 10,
    starter: 100,
    pro: 1000,
    business: 10000
  };

  var TIER_COLORS = {
    free: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
    starter: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    pro: 'bg-violet-500/15 text-violet-400 border-violet-500/30',
    business: 'bg-amber-500/15 text-amber-400 border-amber-500/30'
  };

  var PAYLOADS = {
    portfolio: {
      url: '/api/v1/portfolio/optimize',
      data: {
        assets: [
          { symbol: 'AAPL', expected_return: 0.12, volatility: 0.22 },
          { symbol: 'GOOGL', expected_return: 0.15, volatility: 0.28 },
          { symbol: 'BTC', expected_return: 0.45, volatility: 0.65 },
          { symbol: 'ETH', expected_return: 0.38, volatility: 0.58 }
        ],
        risk_tolerance: 0.6,
        min_allocation: 0.05,
        max_allocation: 0.60
      }
    },
    route: {
      url: '/api/v1/route/optimize',
      data: {
        locations: [
          { name: 'San Francisco', lat: 37.7749, lon: -122.4194 },
          { name: 'Los Angeles', lat: 34.0522, lon: -118.2437 },
          { name: 'Seattle', lat: 47.6062, lon: -122.3321 },
          { name: 'Portland', lat: 45.5155, lon: -122.6789 },
          { name: 'Las Vegas', lat: 36.1699, lon: -115.1398 }
        ],
        return_to_start: true
      }
    },
    schedule: {
      url: '/api/v1/schedule/optimize',
      data: {
        participants: [
          { name: 'Alice', available_slots: ['Mon 9:00-11:00', 'Tue 14:00-16:00', 'Wed 10:00-12:00'], priority: 2.0, preferences: ['Mon 9:00-11:00'] },
          { name: 'Bob', available_slots: ['Mon 9:00-11:00', 'Wed 10:00-12:00', 'Thu 13:00-15:00'], priority: 1.5, preferences: ['Wed 10:00-12:00'] },
          { name: 'Carol', available_slots: ['Tue 14:00-16:00', 'Wed 10:00-12:00', 'Thu 13:00-15:00'], priority: 1.0, preferences: [] }
        ],
        duration_minutes: 60,
        num_meetings: 1
      }
    }
  };

  /* ====================================================================
     Profile Loading
     ==================================================================== */

  async function loadProfile() {
    try {
      userProfile = await Auth.getProfile();
      if (!userProfile) return;
      renderProfile();
      renderUsage();
      renderUpgrade();
      renderRecentJobs();
    } catch (err) {
      showToast('Failed to load profile: ' + err.message, 'error');
    }
  }

  function renderProfile() {
    var emailEl = document.getElementById('user-email');
    var keyEl = document.getElementById('masked-key');
    var tierBadge = document.getElementById('tier-badge');

    if (emailEl) emailEl.textContent = userProfile.email || userProfile.user?.email || '';

    var maskedKey = userProfile.masked_api_key || userProfile.user?.masked_api_key || 'qmr_****...****';
    if (keyEl) keyEl.textContent = maskedKey;

    var tier = (userProfile.tier || userProfile.user?.tier || 'free').toLowerCase();
    if (tierBadge) {
      tierBadge.textContent = tier.charAt(0).toUpperCase() + tier.slice(1);
      tierBadge.className = 'inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ' + (TIER_COLORS[tier] || TIER_COLORS.free);
    }
  }

  function renderUsage() {
    var tier = (userProfile.tier || userProfile.user?.tier || 'free').toLowerCase();
    var usage = userProfile.usage || userProfile.user?.usage || 0;
    var limit = TIER_LIMITS[tier] || 10;
    var pct = Math.min((usage / limit) * 100, 100);

    var usageText = document.getElementById('usage-text');
    var usageBar = document.getElementById('usage-bar-fill');
    var usagePct = document.getElementById('usage-pct');

    if (usageText) usageText.textContent = usage + ' / ' + limit + ' jobs';
    if (usageBar) {
      usageBar.style.width = pct + '%';
      if (pct >= 90) {
        usageBar.className = 'h-full rounded-full transition-all duration-700 ease-out bg-red-500';
      } else if (pct >= 70) {
        usageBar.className = 'h-full rounded-full transition-all duration-700 ease-out bg-amber-500';
      } else {
        usageBar.className = 'h-full rounded-full transition-all duration-700 ease-out bg-gradient-to-r from-violet-500 to-cyan-500';
      }
    }
    if (usagePct) usagePct.textContent = Math.round(pct) + '%';
  }

  function renderUpgrade() {
    var tier = (userProfile.tier || userProfile.user?.tier || 'free').toLowerCase();
    var container = document.getElementById('upgrade-section');
    if (!container) return;

    var tiers = [
      { id: 'starter', name: 'Starter', price: '$29', jobs: '100', features: ['100 jobs/mo', 'Email support', 'API key management'] },
      { id: 'pro', name: 'Pro', price: '$99', jobs: '1,000', features: ['1,000 jobs/mo', 'Priority support', 'Webhooks & analytics', '99.9% SLA'], popular: true },
      { id: 'business', name: 'Business', price: '$499', jobs: '10,000', features: ['10,000 jobs/mo', 'Dedicated support', 'Custom integrations', '99.99% SLA'] }
    ];

    var currentIdx = ['free', 'starter', 'pro', 'business'].indexOf(tier);
    var available = tiers.filter(function (_, i) { return i >= currentIdx; });

    if (available.length === 0 || tier === 'business') {
      container.innerHTML = '<div class="text-center py-6 text-gray-500"><p>You are on the highest tier. Thank you for your support.</p></div>';
      return;
    }

    var checkSvg = '<svg class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>';

    var html = '<div class="grid sm:grid-cols-' + Math.min(available.length, 3) + ' gap-4">';
    available.forEach(function (t) {
      var isCurrent = t.id === tier;
      var borderClass = t.popular ? 'border-violet-500/50' : 'border-gray-700';
      html += '<div class="bg-quantum-dark border ' + borderClass + ' rounded-xl p-5 relative">';
      if (t.popular) html += '<div class="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-violet-600 text-white text-xs font-semibold px-3 py-0.5 rounded-full">Popular</div>';
      html += '<h4 class="font-semibold text-lg mb-1">' + t.name + '</h4>';
      html += '<div class="mb-3"><span class="text-2xl font-bold">' + t.price + '</span><span class="text-gray-500 text-sm">/mo</span></div>';
      html += '<ul class="space-y-2 text-sm text-gray-400 mb-4">';
      t.features.forEach(function (f) { html += '<li class="flex items-start gap-2">' + checkSvg + '<span>' + f + '</span></li>'; });
      html += '</ul>';
      if (isCurrent) {
        html += '<div class="text-center py-2 text-sm text-gray-500 font-medium">Current Plan</div>';
      } else {
        html += '<button onclick="handleUpgrade(\'' + t.id + '\')" class="w-full py-2 rounded-lg ' + (t.popular ? 'bg-violet-600 text-white hover:bg-violet-500' : 'border border-gray-600 text-gray-300 hover:border-gray-400 hover:text-white') + ' font-medium transition-colors text-sm">Upgrade to ' + t.name + '</button>';
      }
      html += '</div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  function renderRecentJobs() {
    var container = document.getElementById('recent-jobs');
    if (!container) return;

    var jobs = userProfile.recent_jobs || userProfile.user?.recent_jobs || [];

    if (!jobs.length) {
      container.innerHTML = '<div class="text-center py-8 text-gray-500"><svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0l-3-3m3 3l3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"/></svg><p>No jobs yet. Run your first query below.</p></div>';
      return;
    }

    var toolIcons = {
      portfolio: '<span class="w-2 h-2 rounded-full bg-violet-400 shrink-0"></span>',
      route: '<span class="w-2 h-2 rounded-full bg-cyan-400 shrink-0"></span>',
      schedule: '<span class="w-2 h-2 rounded-full bg-pink-400 shrink-0"></span>'
    };

    var toolLabels = {
      portfolio: 'Portfolio',
      route: 'Route',
      schedule: 'Scheduler'
    };

    var html = '<div class="divide-y divide-gray-800">';
    jobs.slice(0, 10).forEach(function (job) {
      var tool = (job.tool || 'portfolio').toLowerCase();
      var status = job.status || 'success';
      var statusClass = status === 'success' ? 'text-emerald-400' : status === 'error' ? 'text-red-400' : 'text-amber-400';
      var statusIcon = status === 'success' ? '<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>' : '<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/>';
      var ts = job.timestamp ? new Date(job.timestamp).toLocaleString() : '';

      html += '<div class="flex items-center gap-3 py-3 text-sm">';
      html += (toolIcons[tool] || toolIcons.portfolio);
      html += '<span class="text-gray-300 font-medium min-w-[70px]">' + (toolLabels[tool] || tool) + '</span>';
      html += '<span class="text-gray-500 flex-1 truncate">' + ts + '</span>';
      html += '<span class="' + statusClass + ' flex items-center gap-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' + statusIcon + '</svg>' + status + '</span>';
      html += '</div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  /* ====================================================================
     API Key Management
     ==================================================================== */

  var copyKeyBtn = document.getElementById('copy-key-btn');
  if (copyKeyBtn) {
    copyKeyBtn.addEventListener('click', function () {
      var key = document.getElementById('masked-key').textContent;
      navigator.clipboard.writeText(key).then(function () {
        showToast('Key copied to clipboard', 'success');
      });
    });
  }

  var regenKeyBtn = document.getElementById('regen-key-btn');
  if (regenKeyBtn) {
    regenKeyBtn.addEventListener('click', function () {
      showRegenModal();
    });
  }

  function showRegenModal() {
    var overlay = document.getElementById('regen-modal');
    if (overlay) {
      overlay.style.display = 'flex';
      document.getElementById('regen-confirm-btn').focus();
    }
  }

  function hideRegenModal() {
    var overlay = document.getElementById('regen-modal');
    if (overlay) overlay.style.display = 'none';
  }

  var regenCancel = document.getElementById('regen-cancel-btn');
  if (regenCancel) regenCancel.addEventListener('click', hideRegenModal);

  var regenConfirm = document.getElementById('regen-confirm-btn');
  if (regenConfirm) {
    regenConfirm.addEventListener('click', async function () {
      regenConfirm.disabled = true;
      regenConfirm.innerHTML = '<span class="spinner" aria-hidden="true"></span> Regenerating...';

      try {
        var data = await Auth.regenerateKey();
        hideRegenModal();

        if (data.api_key) {
          showNewKeyModal(data.api_key);
        }
        loadProfile();
      } catch (err) {
        showToast('Failed to regenerate key: ' + err.message, 'error');
      } finally {
        regenConfirm.disabled = false;
        regenConfirm.textContent = 'Regenerate Key';
      }
    });
  }

  function showNewKeyModal(key) {
    var modal = document.getElementById('new-key-modal');
    var display = document.getElementById('new-key-display');
    if (modal && display) {
      display.textContent = key;
      modal.style.display = 'flex';
    }
  }

  var copyNewKey = document.getElementById('copy-new-key');
  if (copyNewKey) {
    copyNewKey.addEventListener('click', function () {
      var key = document.getElementById('new-key-display').textContent;
      navigator.clipboard.writeText(key).then(function () {
        copyNewKey.textContent = 'Copied!';
        setTimeout(function () { copyNewKey.textContent = 'Copy New Key'; }, 2000);
      });
    });
  }

  var closeNewKey = document.getElementById('close-new-key');
  if (closeNewKey) {
    closeNewKey.addEventListener('click', function () {
      document.getElementById('new-key-modal').style.display = 'none';
    });
  }

  /* ====================================================================
     Upgrade / Billing
     ==================================================================== */

  window.handleUpgrade = async function (tier) {
    try {
      showToast('Creating checkout session...', 'info');
      var data = await Auth.createCheckout(tier);
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err) {
      showToast('Failed to create checkout: ' + err.message, 'error');
    }
  };

  /* ====================================================================
     Dashboard Playground
     ==================================================================== */

  var playgroundTabs = document.getElementById('dash-playground-tabs');
  var playgroundRequest = document.getElementById('dash-request');
  var playgroundResult = document.getElementById('dash-result');
  var playgroundRunBtn = document.getElementById('dash-run-btn');
  var playgroundEndpoint = document.getElementById('dash-endpoint');

  function setPlaygroundTab(tab) {
    activePlaygroundTab = tab;
    var payload = PAYLOADS[tab];

    if (playgroundTabs) {
      playgroundTabs.querySelectorAll('[role="tab"]').forEach(function (btn) {
        var selected = btn.dataset.tab === tab;
        btn.setAttribute('aria-selected', String(selected));
      });
    }

    if (playgroundRequest) {
      playgroundRequest.textContent = JSON.stringify(payload.data, null, 2);
    }

    if (playgroundEndpoint) {
      playgroundEndpoint.textContent = payload.url;
    }

    if (playgroundResult) {
      playgroundResult.innerHTML = '<div class="text-gray-500 text-sm py-8 text-center">Click "Run" to execute this query with your API key.</div>';
    }
  }

  if (playgroundTabs) {
    playgroundTabs.addEventListener('click', function (e) {
      var tab = e.target.closest('[role="tab"]');
      if (tab) setPlaygroundTab(tab.dataset.tab);
    });
  }

  if (playgroundRunBtn) {
    playgroundRunBtn.addEventListener('click', async function () {
      var payload = PAYLOADS[activePlaygroundTab];
      var body;

      try {
        body = JSON.parse(playgroundRequest.textContent);
      } catch (_err) {
        playgroundResult.innerHTML = '<div class="text-red-400 text-sm py-4">Invalid JSON in request body.</div>';
        return;
      }

      playgroundRunBtn.disabled = true;
      playgroundRunBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span>';
      playgroundResult.innerHTML = '<div class="flex items-center justify-center py-8"><span class="spinner text-violet-400" aria-hidden="true"></span><span class="ml-3 text-gray-400 text-sm">Running quantum optimization...</span></div>';

      var apiKey = '';
      if (userProfile) {
        apiKey = userProfile.api_key || userProfile.user?.api_key || userProfile.masked_api_key || '';
      }

      try {
        var headers = { 'Content-Type': 'application/json' };
        if (apiKey) headers['X-API-Key'] = apiKey;

        var res = await fetch(payload.url, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(body)
        });

        var data = await res.json();

        if (res.ok) {
          renderFormattedResult(activePlaygroundTab, data);
          loadProfile();
        } else {
          playgroundResult.innerHTML = '<div class="text-red-400 text-sm py-4"><strong>Error ' + res.status + ':</strong> ' + (data.detail || JSON.stringify(data)) + '</div>';
        }
      } catch (err) {
        playgroundResult.innerHTML = '<div class="text-red-400 text-sm py-4">Network error: ' + err.message + '</div>';
      } finally {
        playgroundRunBtn.disabled = false;
        playgroundRunBtn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"/></svg> Run';
      }
    });
  }

  /* ====================================================================
     Formatted Result Renderers
     ==================================================================== */

  function renderFormattedResult(tool, data) {
    if (!playgroundResult) return;

    switch (tool) {
      case 'portfolio':
        renderPortfolioResult(data);
        break;
      case 'route':
        renderRouteResult(data);
        break;
      case 'schedule':
        renderScheduleResult(data);
        break;
      default:
        playgroundResult.innerHTML = '<pre class="text-sm text-emerald-400 whitespace-pre-wrap">' + escapeHtml(JSON.stringify(data, null, 2)) + '</pre>';
    }
  }

  function renderPortfolioResult(data) {
    var allocations = data.allocations || {};
    var colors = ['#8b5cf6', '#06b6d4', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#6366f1', '#14b8a6'];

    var html = '<div class="space-y-4">';

    // Metric cards
    html += '<div class="grid grid-cols-3 gap-3">';
    html += metricCard('Sharpe Ratio', formatNum(data.sharpe_ratio), 'text-emerald-400', true);
    html += metricCard('Expected Return', formatPct(data.expected_return), 'text-violet-400');
    html += metricCard('Volatility', formatPct(data.volatility), 'text-amber-400');
    html += '</div>';

    // Allocation bars
    html += '<div class="space-y-3 mt-2">';
    html += '<h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Allocations</h4>';

    var entries = Object.entries(allocations);
    var maxAlloc = Math.max.apply(null, entries.map(function (e) { return e[1]; }));

    entries.forEach(function (entry, i) {
      var symbol = entry[0];
      var weight = entry[1];
      var pct = maxAlloc > 0 ? (weight / maxAlloc) * 100 : 0;
      var color = colors[i % colors.length];

      html += '<div class="flex items-center gap-3">';
      html += '<span class="text-sm font-mono text-gray-300 w-14 shrink-0">' + escapeHtml(symbol) + '</span>';
      html += '<div class="flex-1 bg-gray-800 rounded-full h-6 overflow-hidden relative">';
      html += '<div class="h-full rounded-full transition-all duration-500" style="width:' + pct + '%; background:' + color + ';"></div>';
      html += '<span class="absolute inset-y-0 right-2 flex items-center text-xs font-mono text-gray-300">' + formatPct(weight) + '</span>';
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';

    // Method info
    if (data.method || data.qubit_count) {
      html += '<div class="flex items-center gap-4 mt-2 pt-3 border-t border-gray-800 text-xs text-gray-500">';
      if (data.method) html += '<span>Method: <span class="text-gray-400 font-mono">' + escapeHtml(data.method) + '</span></span>';
      if (data.qubit_count) html += '<span>Qubits: <span class="text-gray-400">' + data.qubit_count + '</span></span>';
      html += '</div>';
    }

    html += '</div>';
    playgroundResult.innerHTML = html;
  }

  function renderRouteResult(data) {
    var route = data.route || data.optimal_route || [];
    var totalDist = data.total_distance_km || data.total_distance || 0;
    var legs = data.legs || [];

    var html = '<div class="space-y-4">';

    // Total distance card
    html += '<div class="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-4 text-center">';
    html += '<div class="text-2xl font-bold text-cyan-400">' + formatNum(totalDist) + ' km</div>';
    html += '<div class="text-xs text-gray-400 mt-1">Total Route Distance</div>';
    html += '</div>';

    // Route steps
    html += '<div class="space-y-0">';
    route.forEach(function (stop, i) {
      var name = typeof stop === 'string' ? stop : (stop.name || stop.location || ('Stop ' + (i + 1)));
      var isLast = i === route.length - 1;
      var legDist = legs[i] ? legs[i].distance_km || legs[i].distance : null;

      html += '<div class="flex items-start gap-3">';
      // Step indicator
      html += '<div class="flex flex-col items-center">';
      html += '<div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ' + (i === 0 ? 'bg-cyan-500 text-white' : isLast ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'bg-gray-800 text-gray-300 border border-gray-700') + '">' + (i + 1) + '</div>';
      if (!isLast) html += '<div class="w-0.5 h-8 bg-gray-700 my-1"></div>';
      html += '</div>';
      // Stop info
      html += '<div class="pt-1.5 flex-1">';
      html += '<span class="text-sm font-medium text-gray-200">' + escapeHtml(name) + '</span>';
      if (legDist !== null && !isLast) {
        html += '<span class="ml-2 text-xs text-gray-500">' + formatNum(legDist) + ' km to next</span>';
      }
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';

    // Method info
    if (data.method || data.qubit_count) {
      html += '<div class="flex items-center gap-4 mt-2 pt-3 border-t border-gray-800 text-xs text-gray-500">';
      if (data.method) html += '<span>Method: <span class="text-gray-400 font-mono">' + escapeHtml(data.method) + '</span></span>';
      if (data.qubit_count) html += '<span>Qubits: <span class="text-gray-400">' + data.qubit_count + '</span></span>';
      html += '</div>';
    }

    html += '</div>';
    playgroundResult.innerHTML = html;
  }

  function renderScheduleResult(data) {
    var meetings = data.meetings || data.scheduled_meetings || data.schedule || [];
    if (!Array.isArray(meetings)) meetings = [meetings];

    var html = '<div class="space-y-4">';

    // Summary
    if (data.satisfaction_score !== undefined) {
      html += '<div class="bg-pink-500/10 border border-pink-500/20 rounded-lg p-4 text-center">';
      html += '<div class="text-2xl font-bold text-pink-400">' + formatPct(data.satisfaction_score) + '</div>';
      html += '<div class="text-xs text-gray-400 mt-1">Satisfaction Score</div>';
      html += '</div>';
    }

    // Meeting slots
    meetings.forEach(function (meeting, idx) {
      var slot = meeting.slot || meeting.time_slot || meeting.time || 'TBD';
      var attendees = meeting.attendees || meeting.participants || [];

      html += '<div class="bg-gray-800/50 border border-gray-700 rounded-lg p-4">';
      html += '<div class="flex items-center gap-2 mb-3">';
      html += '<svg class="w-4 h-4 text-pink-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
      html += '<span class="text-sm font-semibold text-gray-200">' + escapeHtml(String(slot)) + '</span>';
      if (meetings.length > 1) html += '<span class="text-xs text-gray-500 ml-auto">Meeting ' + (idx + 1) + '</span>';
      html += '</div>';

      // Attendee avatars
      if (attendees.length) {
        html += '<div class="flex flex-wrap gap-2">';
        attendees.forEach(function (person) {
          var name = typeof person === 'string' ? person : (person.name || 'Unknown');
          var initials = name.split(' ').map(function (w) { return w[0]; }).join('').toUpperCase().slice(0, 2);
          var avatarColors = ['bg-violet-500', 'bg-cyan-500', 'bg-pink-500', 'bg-amber-500', 'bg-emerald-500'];
          var colorIdx = name.charCodeAt(0) % avatarColors.length;

          html += '<div class="flex items-center gap-2 bg-gray-900/50 rounded-full pl-1 pr-3 py-1">';
          html += '<div class="w-6 h-6 rounded-full ' + avatarColors[colorIdx] + ' flex items-center justify-center text-[10px] font-bold text-white">' + initials + '</div>';
          html += '<span class="text-xs text-gray-300">' + escapeHtml(name) + '</span>';
          html += '</div>';
        });
        html += '</div>';
      }
      html += '</div>';
    });

    // Method info
    if (data.method || data.qubit_count) {
      html += '<div class="flex items-center gap-4 mt-2 pt-3 border-t border-gray-800 text-xs text-gray-500">';
      if (data.method) html += '<span>Method: <span class="text-gray-400 font-mono">' + escapeHtml(data.method) + '</span></span>';
      if (data.qubit_count) html += '<span>Qubits: <span class="text-gray-400">' + data.qubit_count + '</span></span>';
      html += '</div>';
    }

    html += '</div>';
    playgroundResult.innerHTML = html;
  }

  /* ====================================================================
     Helpers
     ==================================================================== */

  function metricCard(label, value, colorClass, highlight) {
    var border = highlight ? 'border-emerald-500/20' : 'border-gray-800';
    return '<div class="bg-gray-900/50 border ' + border + ' rounded-lg p-3 text-center">' +
      '<div class="text-lg font-bold ' + colorClass + '">' + value + '</div>' +
      '<div class="text-[11px] text-gray-500 mt-0.5">' + label + '</div></div>';
  }

  function formatNum(n) {
    if (n === undefined || n === null) return '--';
    return Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function formatPct(n) {
    if (n === undefined || n === null) return '--';
    return (Number(n) * 100).toFixed(1) + '%';
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  /* ====================================================================
     Toast Notifications
     ==================================================================== */

  function showToast(message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;

    var toast = document.createElement('div');
    var bgClass = type === 'error' ? 'bg-red-500/15 border-red-500/30 text-red-300' :
                  type === 'success' ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300' :
                  'bg-blue-500/15 border-blue-500/30 text-blue-300';

    toast.className = 'flex items-center gap-2 px-4 py-3 rounded-lg border text-sm ' + bgClass + ' transform translate-x-full transition-transform duration-300';
    toast.textContent = message;
    container.appendChild(toast);

    requestAnimationFrame(function () {
      toast.classList.remove('translate-x-full');
      toast.classList.add('translate-x-0');
    });

    setTimeout(function () {
      toast.classList.remove('translate-x-0');
      toast.classList.add('translate-x-full');
      setTimeout(function () { toast.remove(); }, 300);
    }, 4000);
  }

  /* ====================================================================
     Logout
     ==================================================================== */

  var logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function (e) {
      e.preventDefault();
      Auth.logout();
    });
  }

  /* ====================================================================
     Nav link active state
     ==================================================================== */

  var navLinks = document.querySelectorAll('[data-nav]');
  var sections = document.querySelectorAll('[data-section]');

  navLinks.forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      var target = link.dataset.nav;
      sections.forEach(function (s) {
        s.style.display = s.dataset.section === target ? '' : 'none';
      });
      navLinks.forEach(function (l) {
        l.classList.toggle('text-white', l.dataset.nav === target);
        l.classList.toggle('border-b-2', l.dataset.nav === target);
        l.classList.toggle('border-violet-500', l.dataset.nav === target);
        l.classList.toggle('text-gray-400', l.dataset.nav !== target);
      });
    });
  });

  /* ====================================================================
     Init
     ==================================================================== */
  setPlaygroundTab('portfolio');
  loadProfile();

})();
