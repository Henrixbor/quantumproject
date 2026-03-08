/**
 * Quantum MCP Relayer — Interactive Playground
 * Handles tabbed API demos, form submission, scroll reveal, and waitlist.
 */

(function () {
  'use strict';

  /* ====================================================================
     Pre-filled payloads for each API endpoint
     ==================================================================== */

  const PAYLOADS = {
    portfolio: {
      url: '/api/v1/portfolio/optimize',
      label: 'Portfolio Optimizer',
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
      label: 'Route Optimizer',
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
      label: 'Meeting Scheduler',
      data: {
        participants: [
          {
            name: 'Alice',
            available_slots: ['Mon 9:00-11:00', 'Tue 14:00-16:00', 'Wed 10:00-12:00'],
            priority: 2.0,
            preferences: ['Mon 9:00-11:00']
          },
          {
            name: 'Bob',
            available_slots: ['Mon 9:00-11:00', 'Wed 10:00-12:00', 'Thu 13:00-15:00'],
            priority: 1.5,
            preferences: ['Wed 10:00-12:00']
          },
          {
            name: 'Carol',
            available_slots: ['Tue 14:00-16:00', 'Wed 10:00-12:00', 'Thu 13:00-15:00'],
            priority: 1.0,
            preferences: []
          }
        ],
        duration_minutes: 60,
        num_meetings: 1
      }
    }
  };

  /* ====================================================================
     DOM references
     ==================================================================== */

  const tabList = document.getElementById('playground-tabs');
  const requestArea = document.getElementById('request-body');
  const responseArea = document.getElementById('response-body');
  const runBtn = document.getElementById('run-btn');
  const endpointLabel = document.getElementById('endpoint-label');
  const methodLabel = document.getElementById('method-label');

  let activeTab = 'portfolio';

  /* ====================================================================
     Tab Management
     ==================================================================== */

  function setActiveTab(tabName) {
    activeTab = tabName;
    const payload = PAYLOADS[tabName];

    // Update tab ARIA states
    tabList.querySelectorAll('[role="tab"]').forEach(function (btn) {
      var selected = btn.dataset.tab === tabName;
      btn.setAttribute('aria-selected', String(selected));
    });

    // Show corresponding panel
    document.querySelectorAll('[role="tabpanel"]').forEach(function (panel) {
      panel.hidden = panel.id !== 'panel-' + tabName;
    });

    // Update request body
    if (requestArea) {
      requestArea.textContent = JSON.stringify(payload.data, null, 2);
    }

    // Update endpoint labels
    if (endpointLabel) {
      endpointLabel.textContent = payload.url;
    }
    if (methodLabel) {
      methodLabel.textContent = 'POST';
    }

    // Clear previous response
    if (responseArea) {
      responseArea.textContent = '// Click "Run Query" to see the response';
      responseArea.classList.remove('text-red-400', 'text-emerald-400');
      responseArea.classList.add('text-gray-500');
    }
  }

  // Bind tab clicks
  if (tabList) {
    tabList.addEventListener('click', function (e) {
      var tab = e.target.closest('[role="tab"]');
      if (tab) {
        setActiveTab(tab.dataset.tab);
      }
    });

    // Keyboard navigation for tabs (arrow keys)
    tabList.addEventListener('keydown', function (e) {
      var tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));
      var idx = tabs.indexOf(document.activeElement);
      if (idx === -1) return;

      var newIdx = idx;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        newIdx = (idx + 1) % tabs.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        newIdx = (idx - 1 + tabs.length) % tabs.length;
      } else if (e.key === 'Home') {
        e.preventDefault();
        newIdx = 0;
      } else if (e.key === 'End') {
        e.preventDefault();
        newIdx = tabs.length - 1;
      }

      if (newIdx !== idx) {
        tabs[newIdx].focus();
        setActiveTab(tabs[newIdx].dataset.tab);
      }
    });
  }

  /* ====================================================================
     Run Query
     ==================================================================== */

  if (runBtn) {
    runBtn.addEventListener('click', async function () {
      var payload = PAYLOADS[activeTab];
      var body;

      try {
        body = JSON.parse(requestArea.textContent);
      } catch (_err) {
        responseArea.textContent = '// Error: invalid JSON in request body';
        responseArea.classList.add('text-red-400');
        return;
      }

      // Loading state
      runBtn.disabled = true;
      runBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Running\u2026';
      responseArea.textContent = '// Sending request to quantum backend\u2026';
      responseArea.classList.remove('text-red-400', 'text-emerald-400');
      responseArea.classList.add('text-gray-500');

      try {
        var res = await fetch(payload.url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });

        var data = await res.json();

        if (res.ok) {
          responseArea.textContent = JSON.stringify(data, null, 2);
          responseArea.classList.remove('text-gray-500', 'text-red-400');
          responseArea.classList.add('text-emerald-400');
        } else {
          responseArea.textContent = '// Error ' + res.status + '\n' + JSON.stringify(data, null, 2);
          responseArea.classList.remove('text-gray-500', 'text-emerald-400');
          responseArea.classList.add('text-red-400');
        }
      } catch (err) {
        responseArea.textContent = '// Network error: ' + err.message + '\n// Make sure the API server is running on this host.';
        responseArea.classList.remove('text-gray-500', 'text-emerald-400');
        responseArea.classList.add('text-red-400');
      } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = '\u25B6 Run Query';
      }
    });
  }

  /* ====================================================================
     Waitlist Form
     ==================================================================== */

  var waitlistForm = document.getElementById('waitlist-form');
  var waitlistMsg = document.getElementById('waitlist-msg');

  if (waitlistForm) {
    waitlistForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      var emailInput = waitlistForm.querySelector('input[type="email"]');
      var email = emailInput.value.trim();
      if (!email) return;

      var submitBtn = waitlistForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span>';

      try {
        var res = await fetch('/api/v1/waitlist', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email })
        });

        var data = await res.json();

        if (res.ok) {
          waitlistMsg.textContent = data.message || 'You\'re on the list! We\'ll be in touch.';
          waitlistMsg.className = 'mt-3 text-sm text-emerald-400';
          emailInput.value = '';
        } else {
          waitlistMsg.textContent = data.detail || 'Something went wrong. Please try again.';
          waitlistMsg.className = 'mt-3 text-sm text-red-400';
        }
      } catch (_err) {
        waitlistMsg.textContent = 'Network error. Please try again.';
        waitlistMsg.className = 'mt-3 text-sm text-red-400';
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Join Waitlist';
      }
    });
  }

  /* ====================================================================
     Copy Buttons for Code Blocks
     ==================================================================== */

  document.querySelectorAll('.copy-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var block = btn.closest('.code-block');
      var code = block.querySelector('code');
      if (!code) return;
      navigator.clipboard.writeText(code.textContent).then(function () {
        var original = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(function () { btn.textContent = original; }, 1500);
      });
    });
  });

  /* ====================================================================
     Scroll Reveal (IntersectionObserver)
     ==================================================================== */

  var reveals = document.querySelectorAll('.reveal');
  if (reveals.length && 'IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    reveals.forEach(function (el) { observer.observe(el); });
  } else {
    // Fallback: show everything
    reveals.forEach(function (el) { el.classList.add('visible'); });
  }

  /* ====================================================================
     Mobile Nav Toggle
     ==================================================================== */

  var navToggle = document.getElementById('nav-toggle');
  var mobileNav = document.getElementById('mobile-nav');

  if (navToggle && mobileNav) {
    navToggle.addEventListener('click', function () {
      var expanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', String(!expanded));
      mobileNav.classList.toggle('open');
    });
  }

  /* ====================================================================
     Active nav highlight on scroll
     ==================================================================== */

  var sections = document.querySelectorAll('section[id]');
  var navLinks = document.querySelectorAll('nav a[href^="#"]');

  if (sections.length && navLinks.length && 'IntersectionObserver' in window) {
    var navObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          navLinks.forEach(function (link) {
            link.classList.toggle('text-violet-400',
              link.getAttribute('href') === '#' + entry.target.id);
          });
        }
      });
    }, { threshold: 0.3 });

    sections.forEach(function (s) { navObserver.observe(s); });
  }

  /* ====================================================================
     Init — set first tab active
     ==================================================================== */
  setActiveTab('portfolio');

})();
