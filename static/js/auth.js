/**
 * Quantum MCP Relayer — Authentication Module
 * Handles signup, login, profile fetching, key management, auth state, and toast notifications.
 */

(function () {
  'use strict';

  var API_BASE = '/api/v1';
  var TOKEN_KEY = 'qmr_token';
  var USER_KEY = 'qmr_user';
  var ONBOARDING_KEY = 'qmr_onboarded';

  /* ====================================================================
     Toast Notification System (shared across all pages)
     ==================================================================== */

  function ensureToastContainer() {
    var container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      container.setAttribute('aria-live', 'polite');
      container.setAttribute('role', 'status');
      document.body.appendChild(container);
    }
    return container;
  }

  var TOAST_ICONS = {
    success: '<svg class="toast-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
    error: '<svg class="toast-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/></svg>',
    info: '<svg class="toast-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"/></svg>',
    warning: '<svg class="toast-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>'
  };

  function showToast(message, type) {
    type = type || 'info';
    var container = ensureToastContainer();

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.innerHTML =
      (TOAST_ICONS[type] || TOAST_ICONS.info) +
      '<span class="toast-message">' + escapeHtml(message) + '</span>' +
      '<button class="toast-dismiss" aria-label="Dismiss notification">&times;</button>' +
      '<div class="toast-progress"></div>';

    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        toast.classList.add('visible');
      });
    });

    // Dismiss handler
    toast.querySelector('.toast-dismiss').addEventListener('click', function () {
      dismissToast(toast);
    });

    // Auto-dismiss after 5s
    var timeout = setTimeout(function () {
      dismissToast(toast);
    }, 5000);

    toast._timeout = timeout;
  }

  function dismissToast(toast) {
    if (toast._dismissed) return;
    toast._dismissed = true;
    clearTimeout(toast._timeout);
    toast.classList.remove('visible');
    toast.classList.add('removing');
    setTimeout(function () { toast.remove(); }, 350);
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  /* ====================================================================
     Core Auth Functions
     ==================================================================== */

  var Auth = {
    getToken: function () {
      return localStorage.getItem(TOKEN_KEY);
    },

    setToken: function (token) {
      localStorage.setItem(TOKEN_KEY, token);
    },

    getUser: function () {
      try {
        return JSON.parse(localStorage.getItem(USER_KEY));
      } catch (_e) {
        return null;
      }
    },

    setUser: function (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    },

    isLoggedIn: function () {
      return !!this.getToken();
    },

    isNewUser: function () {
      return !localStorage.getItem(ONBOARDING_KEY);
    },

    markOnboarded: function () {
      localStorage.setItem(ONBOARDING_KEY, 'true');
    },

    logout: function () {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      window.location.href = '/';
    },

    signup: async function (email, password) {
      var res = await fetch(API_BASE + '/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password })
      });
      var data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || 'Signup failed');
      }
      return data;
    },

    login: async function (email, password) {
      var res = await fetch(API_BASE + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password })
      });
      var data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || 'Login failed');
      }
      return data;
    },

    getProfile: async function () {
      var token = this.getToken();
      if (!token) throw new Error('Not authenticated');
      var res = await fetch(API_BASE + '/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      var data = await res.json();
      if (!res.ok) {
        if (res.status === 401) {
          this.logout();
          return;
        }
        throw new Error(data.detail || 'Failed to fetch profile');
      }
      this.setUser(data);
      return data;
    },

    regenerateKey: async function () {
      var token = this.getToken();
      if (!token) throw new Error('Not authenticated');
      var res = await fetch(API_BASE + '/auth/regenerate-key', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      var data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to regenerate key');
      }
      return data;
    },

    createCheckout: async function (tier) {
      var token = this.getToken();
      if (!token) throw new Error('Not authenticated');
      var res = await fetch(API_BASE + '/billing/create-checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ tier: tier })
      });
      var data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create checkout');
      }
      return data;
    },

    guardDashboard: function () {
      if (!this.isLoggedIn()) {
        window.location.href = '/auth.html';
      }
    },

    guardAuth: function () {
      if (this.isLoggedIn()) {
        window.location.href = '/dashboard.html';
      }
    }
  };

  /* ====================================================================
     Update nav on landing page based on auth state
     ==================================================================== */

  function updateNavForAuth() {
    if (!Auth.isLoggedIn()) return;

    var navLinks = document.querySelectorAll('nav a[href="/auth.html"], nav a[href="#waitlist"]');
    navLinks.forEach(function (link) {
      if (link.textContent.trim() === 'Get Started' || link.textContent.trim() === 'Log In') {
        link.href = '/dashboard.html';
        link.textContent = 'Dashboard';
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateNavForAuth);
  } else {
    updateNavForAuth();
  }

  window.Auth = Auth;
  window.showToast = showToast;
})();
