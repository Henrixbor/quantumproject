/**
 * Quantum MCP Relayer — Dashboard Logic
 * Handles profile loading, skeleton states, usage stats, playground,
 * key management, billing, onboarding, and enhanced result visualization.
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
     Skeleton Loading States
     ==================================================================== */

  function showSkeletonLoading() {
    // API Key skeleton
    var maskedKey = document.getElementById('masked-key');
    if (maskedKey) {
      maskedKey.innerHTML = '<div class="skeleton skeleton-text" style="width:200px;height:1rem;display:inline-block"></div>';
    }

    // Usage skeleton
    var usageText = document.getElementById('usage-text');
    if (usageText) {
      usageText.innerHTML = '<span class="skeleton skeleton-text-sm" style="width:80px;display:inline-block;height:0.875rem"></span>';
    }

    // Recent jobs skeleton
    var recentJobs = document.getElementById('recent-jobs');
    if (recentJobs) {
      var skeletonHtml = '<div class="space-y-3">';
      for (var i = 0; i < 3; i++) {
        skeletonHtml += '<div class="flex items-center gap-3 py-3">';
        skeletonHtml += '<div class="skeleton skeleton-circle" style="width:8px;height:8px"></div>';
        skeletonHtml += '<div class="skeleton skeleton-text-sm" style="width:60px;height:0.75rem"></div>';
        skeletonHtml += '<div class="skeleton skeleton-text-sm flex-1" style="height:0.75rem"></div>';
        skeletonHtml += '<div class="skeleton skeleton-text-sm" style="width:50px;height:0.75rem"></div>';
        skeletonHtml += '</div>';
      }
      skeletonHtml += '</div>';
      recentJobs.innerHTML = skeletonHtml;
    }

    // Upgrade section skeleton
    var upgradeSection = document.getElementById('upgrade-section');
    if (upgradeSection) {
      var upgradeSkeleton = '<div class="grid sm:grid-cols-3 gap-4">';
      for (var j = 0; j < 3; j++) {
        upgradeSkeleton += '<div class="skeleton-card"><div class="skeleton skeleton-text" style="width:60%"></div>';
        upgradeSkeleton += '<div class="skeleton skeleton-bar" style="margin:1rem 0"></div>';
        upgradeSkeleton += '<div class="skeleton skeleton-text-sm" style="width:80%"></div>';
        upgradeSkeleton += '<div class="skeleton skeleton-text-sm" style="width:70%"></div></div>';
      }
      upgradeSkeleton += '</div>';
      upgradeSection.innerHTML = upgradeSkeleton;
    }
  }

  /* ====================================================================
     Profile Loading
     ==================================================================== */

  async function loadProfile() {
    showSkeletonLoading();

    try {
      userProfile = await Auth.getProfile();
      if (!userProfile) return;
      renderProfile();
      renderUsage();
      renderUpgrade();
      renderRecentJobs();

      // Show onboarding for new users
      if (Auth.isNewUser()) {
        showOnboarding();
        Auth.markOnboarded();
      }
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
      container.innerHTML = '<div class="text-center py-6 text-gray-400"><p>You are on the highest tier. Thank you for your support.</p></div>';
      return;
    }

    var checkSvg = '<svg class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>';

    var html = '<div class="grid sm:grid-cols-' + Math.min(available.length, 3) + ' gap-4">';
    available.forEach(function (t) {
      var isCurrent = t.id === tier;
      var borderClass = t.popular ? 'border-violet-500/50' : 'border-gray-700';
      html += '<div class="bg-quantum-dark border ' + borderClass + ' rounded-xl p-5 relative transition-all duration-200 hover:border-violet-500/30 hover:-translate-y-0.5">';
      if (t.popular) html += '<div class="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-violet-600 text-white text-xs font-semibold px-3 py-0.5 rounded-full">Popular</div>';
      html += '<h4 class="font-semibold text-lg mb-1">' + t.name + '</h4>';
      html += '<div class="mb-3"><span class="text-2xl font-bold">' + t.price + '</span><span class="text-gray-400 text-sm">/mo</span></div>';
      html += '<ul class="space-y-2 text-sm text-gray-400 mb-4">';
      t.features.forEach(function (f) { html += '<li class="flex items-start gap-2">' + checkSvg + '<span>' + f + '</span></li>'; });
      html += '</ul>';
      if (isCurrent) {
        html += '<div class="text-center py-2 text-sm text-gray-400 font-medium">Current Plan</div>';
      } else {
        html += '<button onclick="handleUpgrade(\'' + t.id + '\')" class="w-full py-2 rounded-lg ' + (t.popular ? 'bg-violet-600 text-white hover:bg-violet-500' : 'border border-gray-600 text-gray-300 hover:border-gray-400 hover:text-white') + ' font-medium transition-all duration-200 text-sm active:scale-95">Upgrade to ' + t.name + '</button>';
      }
      html += '</div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  /* ====================================================================
     Empty State for Recent Jobs
     ==================================================================== */

  function renderRecentJobs() {
    var container = document.getElementById('recent-jobs');
    if (!container) return;

    var jobs = userProfile.recent_jobs || userProfile.user?.recent_jobs || [];

    if (!jobs.length) {
      container.innerHTML =
        '<div class="empty-state">' +
          '<svg class="empty-state-icon" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">' +
            '<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"/>' +
          '</svg>' +
          '<div class="empty-state-title">No optimization jobs yet</div>' +
          '<div class="empty-state-desc">Run your first quantum optimization query using the playground below. Your job history will appear here.</div>' +
          '<a href="#" class="empty-state-cta" onclick="document.getElementById(\'dash-request\').scrollIntoView({behavior:\'smooth\'});return false;">' +
            '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"/></svg>' +
            'Run your first query' +
          '</a>' +
        '</div>';
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

      html += '<div class="flex items-center gap-3 py-3 text-sm hover:bg-gray-800/30 rounded px-2 -mx-2 transition-colors">';
      html += (toolIcons[tool] || toolIcons.portfolio);
      html += '<span class="text-gray-300 font-medium min-w-[70px]">' + (toolLabels[tool] || tool) + '</span>';
      html += '<span class="text-gray-400 flex-1 truncate">' + ts + '</span>';
      html += '<span class="' + statusClass + ' flex items-center gap-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' + statusIcon + '</svg>' + status + '</span>';
      html += '</div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  /* ====================================================================
     API Key Management with copy tooltip feedback
     ==================================================================== */

  var copyKeyBtn = document.getElementById('copy-key-btn');
  if (copyKeyBtn) {
    copyKeyBtn.style.position = 'relative';
    copyKeyBtn.addEventListener('click', function () {
      var key = document.getElementById('masked-key').textContent;
      navigator.clipboard.writeText(key).then(function () {
        // Show tooltip
        var tooltip = document.createElement('div');
        tooltip.className = 'copy-tooltip';
        tooltip.textContent = 'Copied!';
        copyKeyBtn.appendChild(tooltip);
        requestAnimationFrame(function () { tooltip.classList.add('visible'); });

        showToast('API key copied to clipboard', 'success');

        setTimeout(function () {
          tooltip.classList.remove('visible');
          setTimeout(function () { tooltip.remove(); }, 200);
        }, 1500);
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
      regenConfirm.innerHTML = '<span class="spinner" role="status" aria-label="Loading"></span> Regenerating...';

      try {
        var data = await Auth.regenerateKey();
        hideRegenModal();

        if (data.api_key) {
          showNewKeyModal(data.api_key);
          showToast('API key regenerated successfully', 'success');
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
    copyNewKey.style.position = 'relative';
    copyNewKey.addEventListener('click', function () {
      var key = document.getElementById('new-key-display').textContent;
      navigator.clipboard.writeText(key).then(function () {
        // Tooltip feedback
        var tooltip = document.createElement('div');
        tooltip.className = 'copy-tooltip';
        tooltip.textContent = 'Copied!';
        copyNewKey.appendChild(tooltip);
        requestAnimationFrame(function () { tooltip.classList.add('visible'); });

        copyNewKey.textContent = 'Copied!';
        showToast('New API key copied to clipboard', 'success');

        setTimeout(function () {
          copyNewKey.textContent = 'Copy New Key';
          tooltip.remove();
        }, 2000);
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
     Dashboard Playground with smooth tab transitions
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
      playgroundRequest.classList.add('tab-panel-transition');
      playgroundRequest.textContent = JSON.stringify(payload.data, null, 2);
      setTimeout(function () { playgroundRequest.classList.remove('tab-panel-transition'); }, 250);
    }

    if (playgroundEndpoint) {
      playgroundEndpoint.textContent = payload.url;
    }

    if (playgroundResult) {
      playgroundResult.innerHTML =
        '<div class="empty-state" style="padding:2rem 1rem;min-height:auto">' +
          '<svg class="empty-state-icon" style="width:40px;height:40px" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">' +
            '<path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"/>' +
          '</svg>' +
          '<div class="empty-state-desc" style="margin-bottom:0">Click "Run" to execute this query with your API key.</div>' +
        '</div>';
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
        showToast('Invalid JSON in request body', 'error');
        return;
      }

      playgroundRunBtn.disabled = true;
      playgroundRunBtn.innerHTML = '<span class="spinner" role="status" aria-label="Loading"></span>';

      // Skeleton loading state
      var loadingHtml = '<div class="space-y-3 py-4">';
      loadingHtml += '<div class="skeleton skeleton-bar" style="width:90%"></div>';
      loadingHtml += '<div class="grid grid-cols-3 gap-3 mt-3">';
      for (var i = 0; i < 3; i++) {
        loadingHtml += '<div class="skeleton" style="height:3.5rem;border-radius:0.5rem"></div>';
      }
      loadingHtml += '</div>';
      loadingHtml += '<div class="skeleton skeleton-text" style="width:70%;margin-top:1rem"></div>';
      loadingHtml += '<div class="skeleton skeleton-text" style="width:85%"></div>';
      loadingHtml += '<div class="skeleton skeleton-text" style="width:60%"></div>';
      loadingHtml += '</div>';
      playgroundResult.innerHTML = loadingHtml;

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
          showToast('Quantum optimization complete', 'success');
          loadProfile();
        } else {
          playgroundResult.innerHTML = '<div class="text-red-400 text-sm py-4"><strong>Error ' + res.status + ':</strong> ' + (data.detail || JSON.stringify(data)) + '</div>';
          showToast('API error: ' + (data.detail || 'Request failed'), 'error');
        }
      } catch (err) {
        playgroundResult.innerHTML = '<div class="text-red-400 text-sm py-4">Network error: ' + err.message + '</div>';
        showToast('Network error: Could not reach the API', 'error');
      } finally {
        playgroundRunBtn.disabled = false;
        playgroundRunBtn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"/></svg> Run';
      }
    });
  }

  /* ====================================================================
     Enhanced Formatted Result Renderers
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

  /* ---- Portfolio: Donut chart + bars ---- */
  function renderPortfolioResult(data) {
    var allocations = data.allocations || {};
    var colors = ['#6C5CE7', '#00CEC9', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#0984E3', '#14b8a6'];

    var html = '<div class="space-y-4 tab-panel-transition">';

    // Metric cards
    html += '<div class="grid grid-cols-3 gap-3">';
    html += metricCard('Sharpe Ratio', formatNum(data.sharpe_ratio), 'text-emerald-400', true);
    html += metricCard('Expected Return', formatPct(data.expected_return), 'text-violet-400');
    html += metricCard('Volatility', formatPct(data.volatility), 'text-amber-400');
    html += '</div>';

    // Donut Chart + Allocation bars side by side
    var entries = Object.entries(allocations);
    var total = entries.reduce(function (sum, e) { return sum + e[1]; }, 0);

    html += '<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">';

    // Donut chart (SVG)
    html += '<div class="flex items-center justify-center">';
    html += '<div class="donut-chart">';
    html += '<svg viewBox="0 0 36 36">';

    var offset = 0;
    entries.forEach(function (entry, i) {
      var pctVal = total > 0 ? (entry[1] / total) * 100 : 0;
      var dashArray = pctVal + ' ' + (100 - pctVal);
      html += '<circle cx="18" cy="18" r="15.9155" fill="none" stroke="' + colors[i % colors.length] + '" stroke-width="3" stroke-dasharray="' + dashArray + '" stroke-dashoffset="-' + offset + '" style="transition:stroke-dasharray 0.5s ease"/>';
      offset += pctVal;
    });

    html += '</svg>';
    html += '<div class="donut-center"><span class="value">' + entries.length + '</span><span class="label">Assets</span></div>';
    html += '</div></div>';

    // Legend + bars
    html += '<div class="space-y-2">';
    html += '<h4 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Allocations</h4>';

    var maxAlloc = Math.max.apply(null, entries.map(function (e) { return e[1]; }));
    entries.forEach(function (entry, i) {
      var symbol = entry[0];
      var weight = entry[1];
      var pct = maxAlloc > 0 ? (weight / maxAlloc) * 100 : 0;
      var color = colors[i % colors.length];

      html += '<div class="flex items-center gap-2">';
      html += '<span class="w-2.5 h-2.5 rounded-full shrink-0" style="background:' + color + '"></span>';
      html += '<span class="text-xs font-mono text-gray-300 w-12 shrink-0">' + escapeHtml(symbol) + '</span>';
      html += '<div class="flex-1 bg-gray-800 rounded-full h-5 overflow-hidden relative">';
      html += '<div class="h-full rounded-full" style="width:' + pct + '%; background:' + color + '; transition: width 0.6s ease-out;"></div>';
      html += '<span class="absolute inset-y-0 right-2 flex items-center text-[11px] font-mono text-gray-300">' + formatPct(weight) + '</span>';
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';

    html += '</div>'; // close grid

    // Method info
    if (data.method || data.qubit_count) {
      html += '<div class="flex items-center gap-4 mt-2 pt-3 border-t border-gray-800 text-xs text-gray-400">';
      if (data.method) html += '<span>Method: <span class="text-gray-400 font-mono">' + escapeHtml(data.method) + '</span></span>';
      if (data.qubit_count) html += '<span>Qubits: <span class="text-gray-400">' + data.qubit_count + '</span></span>';
      html += '</div>';
    }

    html += '</div>';
    playgroundResult.innerHTML = html;
  }

  /* ---- Route: Numbered journey ---- */
  function renderRouteResult(data) {
    var route = data.route || data.optimal_route || [];
    var totalDist = data.total_distance_km || data.total_distance || 0;
    var legs = data.legs || [];

    var html = '<div class="space-y-4 tab-panel-transition">';

    // Total distance card
    html += '<div class="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-cyan-500/20 rounded-lg p-4 text-center">';
    html += '<div class="text-3xl font-bold" style="background:linear-gradient(135deg,#0984E3,#00CEC9);-webkit-background-clip:text;-webkit-text-fill-color:transparent">' + formatNum(totalDist) + ' km</div>';
    html += '<div class="text-xs text-gray-400 mt-1">Total Route Distance</div>';
    html += '</div>';

    // Route journey with connected steps
    html += '<div class="route-journey">';
    route.forEach(function (stop, i) {
      var name = typeof stop === 'string' ? stop : (stop.name || stop.location || ('Stop ' + (i + 1)));
      var isLast = i === route.length - 1;
      var isFirst = i === 0;
      var legDist = legs[i] ? legs[i].distance_km || legs[i].distance : null;

      html += '<div class="flex items-start gap-3 pb-1" style="animation: tabFadeIn 0.3s ease-out ' + (i * 0.08) + 's both">';
      // Step indicator
      html += '<div class="flex flex-col items-center" style="min-width:36px">';
      if (isFirst) {
        html += '<div class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold bg-gradient-to-br from-blue-500 to-cyan-500 text-white shadow-lg shadow-cyan-500/20">' + (i + 1) + '</div>';
      } else if (isLast) {
        html += '<div class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold bg-cyan-500/15 text-cyan-400 border-2 border-cyan-500/40">';
        html += '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"/></svg>';
        html += '</div>';
      } else {
        html += '<div class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold bg-gray-800 text-gray-300 border border-gray-700">' + (i + 1) + '</div>';
      }
      if (!isLast) html += '<div class="w-0.5 h-6 bg-gradient-to-b from-blue-500/40 to-cyan-500/20 my-1"></div>';
      html += '</div>';
      // Stop info
      html += '<div class="pt-2 flex-1">';
      html += '<span class="text-sm font-medium text-gray-200">' + escapeHtml(name) + '</span>';
      if (legDist !== null && !isLast) {
        html += '<span class="ml-2 text-xs text-gray-400 bg-gray-800/50 px-2 py-0.5 rounded-full">' + formatNum(legDist) + ' km</span>';
      }
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';

    // Method info
    if (data.method || data.qubit_count) {
      html += '<div class="flex items-center gap-4 mt-2 pt-3 border-t border-gray-800 text-xs text-gray-400">';
      if (data.method) html += '<span>Method: <span class="text-gray-400 font-mono">' + escapeHtml(data.method) + '</span></span>';
      if (data.qubit_count) html += '<span>Qubits: <span class="text-gray-400">' + data.qubit_count + '</span></span>';
      html += '</div>';
    }

    html += '</div>';
    playgroundResult.innerHTML = html;
  }

  /* ---- Schedule: Calendar-like view ---- */
  function renderScheduleResult(data) {
    var meetings = data.meetings || data.scheduled_meetings || data.schedule || [];
    if (!Array.isArray(meetings)) meetings = [meetings];

    var html = '<div class="space-y-4 tab-panel-transition">';

    // Summary
    if (data.satisfaction_score !== undefined) {
      html += '<div class="bg-gradient-to-r from-pink-500/10 to-violet-500/10 border border-pink-500/20 rounded-lg p-4 text-center">';
      html += '<div class="text-3xl font-bold" style="background:linear-gradient(135deg,#ec4899,#6C5CE7);-webkit-background-clip:text;-webkit-text-fill-color:transparent">' + formatPct(data.satisfaction_score) + '</div>';
      html += '<div class="text-xs text-gray-400 mt-1">Satisfaction Score</div>';
      html += '</div>';
    }

    // Calendar-like day grid
    var days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
    var timeSlots = ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00'];

    // Collect all scheduled slots
    var scheduledSlots = {};
    meetings.forEach(function (meeting) {
      var slot = meeting.slot || meeting.time_slot || meeting.time || '';
      scheduledSlots[slot] = meeting.attendees || meeting.participants || [];
    });

    html += '<div class="overflow-x-auto">';
    html += '<div class="schedule-grid" style="grid-template-columns: 50px repeat(5, 1fr); min-width: 340px;">';

    // Header row
    html += '<div class="schedule-day"></div>';
    days.forEach(function (day) {
      html += '<div class="schedule-day">' + day + '</div>';
    });

    // Time rows
    timeSlots.forEach(function (time) {
      html += '<div class="text-[10px] text-gray-400 py-1 text-right pr-2" style="display:flex;align-items:center;justify-content:flex-end">' + time + '</div>';
      days.forEach(function (day) {
        var slotKey = day + ' ' + time + '-' + nextTime(time);
        var isScheduled = !!scheduledSlots[slotKey];
        var isAvailable = isSlotAvailable(data, day, time);

        var cls = 'schedule-slot';
        if (isScheduled) cls += ' highlight';
        else if (isAvailable) cls += ' active';

        html += '<div class="' + cls + '">';
        if (isScheduled) {
          html += '<svg class="w-3 h-3 mx-auto" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>';
        }
        html += '</div>';
      });
    });

    html += '</div></div>';

    // Meeting slots detail
    meetings.forEach(function (meeting, idx) {
      var slot = meeting.slot || meeting.time_slot || meeting.time || 'TBD';
      var attendees = meeting.attendees || meeting.participants || [];

      html += '<div class="bg-gray-800/50 border border-gray-700 rounded-lg p-4">';
      html += '<div class="flex items-center gap-2 mb-3">';
      html += '<svg class="w-4 h-4 text-pink-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
      html += '<span class="text-sm font-semibold text-gray-200">' + escapeHtml(String(slot)) + '</span>';
      if (meetings.length > 1) html += '<span class="text-xs text-gray-400 ml-auto">Meeting ' + (idx + 1) + '</span>';
      html += '</div>';

      // Attendee avatars
      if (attendees.length) {
        html += '<div class="flex flex-wrap gap-2">';
        attendees.forEach(function (person) {
          var name = typeof person === 'string' ? person : (person.name || 'Unknown');
          var initials = name.split(' ').map(function (w) { return w[0]; }).join('').toUpperCase().slice(0, 2);
          var avatarColors = ['bg-violet-500', 'bg-cyan-500', 'bg-pink-500', 'bg-amber-500', 'bg-emerald-500'];
          var colorIdx = name.charCodeAt(0) % avatarColors.length;

          html += '<div class="flex items-center gap-2 bg-gray-900/50 rounded-full pl-1 pr-3 py-1 transition-transform hover:scale-105">';
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
      html += '<div class="flex items-center gap-4 mt-2 pt-3 border-t border-gray-800 text-xs text-gray-400">';
      if (data.method) html += '<span>Method: <span class="text-gray-400 font-mono">' + escapeHtml(data.method) + '</span></span>';
      if (data.qubit_count) html += '<span>Qubits: <span class="text-gray-400">' + data.qubit_count + '</span></span>';
      html += '</div>';
    }

    html += '</div>';
    playgroundResult.innerHTML = html;
  }

  function nextTime(time) {
    var hour = parseInt(time.split(':')[0]) + 1;
    return (hour < 10 ? '0' : '') + hour + ':00';
  }

  function isSlotAvailable(data, day, time) {
    var participants = [];
    if (data && data.participants) participants = data.participants;
    var slotKey = day + ' ' + time;
    return participants.some(function (p) {
      return (p.available_slots || []).some(function (s) { return s.indexOf(slotKey) === 0; });
    });
  }

  /* ====================================================================
     Helpers
     ==================================================================== */

  function metricCard(label, value, colorClass, highlight) {
    var border = highlight ? 'border-emerald-500/20' : 'border-gray-800';
    return '<div class="bg-gray-900/50 border ' + border + ' rounded-lg p-3 text-center transition-transform hover:scale-105">' +
      '<div class="text-lg font-bold ' + colorClass + '">' + value + '</div>' +
      '<div class="text-[11px] text-gray-400 mt-0.5">' + label + '</div></div>';
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
     Onboarding Quick Start Overlay
     ==================================================================== */

  function showOnboarding() {
    var maskedKey = userProfile ? (userProfile.masked_api_key || userProfile.user?.masked_api_key || 'qmr_****...****') : 'qmr_****...****';

    var overlay = document.createElement('div');
    overlay.className = 'onboarding-overlay';
    overlay.id = 'onboarding-overlay';
    overlay.innerHTML =
      '<div class="onboarding-card">' +
        '<button class="onboarding-close" id="onboarding-close" aria-label="Close quick start guide">' +
          '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>' +
        '</button>' +
        '<h2 class="text-xl font-bold mb-1">Welcome to Quantum MCP</h2>' +
        '<p class="text-gray-400 text-sm mb-4">Here is everything you need to get started with quantum optimization.</p>' +

        '<div class="onboarding-step">' +
          '<div class="onboarding-step-number">1</div>' +
          '<div class="onboarding-step-content">' +
            '<h4>Your API Key</h4>' +
            '<p>Your key is <code class="text-xs font-mono text-emerald-400 bg-gray-800/50 px-1.5 py-0.5 rounded">' + escapeHtml(maskedKey) + '</code>. Use it in the <code class="text-xs text-violet-400">X-API-Key</code> header or your MCP config.</p>' +
          '</div>' +
        '</div>' +

        '<div class="onboarding-step">' +
          '<div class="onboarding-step-number">2</div>' +
          '<div class="onboarding-step-content">' +
            '<h4>Try the Playground</h4>' +
            '<p>Scroll down to the playground section, pick a tool, edit the JSON, and click Run to see quantum optimization in action.</p>' +
          '</div>' +
        '</div>' +

        '<div class="onboarding-step">' +
          '<div class="onboarding-step-number">3</div>' +
          '<div class="onboarding-step-content">' +
            '<h4>Read the Docs</h4>' +
            '<p>Check out the <a href="/" class="text-violet-400 hover:text-violet-300 underline">documentation page</a> for MCP config, cURL examples, and SDK code samples.</p>' +
          '</div>' +
        '</div>' +

        '<button id="onboarding-dismiss" class="w-full mt-4 py-3 rounded-lg bg-violet-600 text-white font-semibold hover:bg-violet-500 transition-colors active:scale-95" style="transition: transform 0.15s ease, background 0.2s ease">' +
          'Got it, let me explore!' +
        '</button>' +
      '</div>';

    document.body.appendChild(overlay);

    // Close handlers
    document.getElementById('onboarding-close').addEventListener('click', closeOnboarding);
    document.getElementById('onboarding-dismiss').addEventListener('click', closeOnboarding);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeOnboarding();
    });
  }

  function closeOnboarding() {
    var overlay = document.getElementById('onboarding-overlay');
    if (overlay) {
      overlay.style.opacity = '0';
      overlay.style.transition = 'opacity 0.3s ease';
      setTimeout(function () { overlay.remove(); }, 300);
    }
  }

  /* ====================================================================
     Logout
     ==================================================================== */

  var logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function (e) {
      e.preventDefault();
      showToast('Logging out...', 'info');
      setTimeout(function () { Auth.logout(); }, 500);
    });
  }

  /* ====================================================================
     Mobile dashboard nav toggle
     ==================================================================== */

  var dashNavToggle = document.getElementById('dash-nav-toggle');
  var dashMobileNav = document.getElementById('dash-mobile-nav');

  if (dashNavToggle && dashMobileNav) {
    dashNavToggle.addEventListener('click', function () {
      var expanded = dashNavToggle.getAttribute('aria-expanded') === 'true';
      dashNavToggle.setAttribute('aria-expanded', String(!expanded));
      dashMobileNav.classList.toggle('open');
    });

    // Close mobile nav when a link is clicked
    dashMobileNav.querySelectorAll('a[data-nav]').forEach(function (link) {
      link.addEventListener('click', function () {
        dashMobileNav.classList.remove('open');
        dashNavToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ====================================================================
     Nav link active state with highlight + breadcrumb update
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
        if (!l.dataset.nav) return;
        l.classList.toggle('text-white', l.dataset.nav === target);
        l.classList.toggle('border-b-2', l.dataset.nav === target);
        l.classList.toggle('border-violet-500', l.dataset.nav === target);
        l.classList.toggle('text-gray-400', l.dataset.nav !== target);
      });

      // Update breadcrumb
      var breadcrumbLabels = { overview: 'Dashboard', keys: 'API Keys', usage: 'Usage' };
      var breadcrumbEl = document.getElementById('breadcrumb-current');
      if (breadcrumbEl) {
        breadcrumbEl.textContent = breadcrumbLabels[target] || 'Dashboard';
      }
    });
  });

  /* ====================================================================
     Init
     ==================================================================== */
  setPlaygroundTab('portfolio');
  loadProfile();

})();
