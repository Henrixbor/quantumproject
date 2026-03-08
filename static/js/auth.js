/**
 * Quantum MCP Relayer — Authentication Module
 * Handles signup, login, profile fetching, key management, and auth state.
 */

(function () {
  'use strict';

  var API_BASE = '/api/v1';
  var TOKEN_KEY = 'qmr_token';
  var USER_KEY = 'qmr_user';

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
})();
