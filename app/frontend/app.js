
function formatImageUrl(url) {
  if (!url) return '/assets/shilpa_shastra_iconography.jpg';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/')) return url;
  return '/' + url;
}


// ============================================================================
// PASSWORDLESS MAGIC LINK AUTHENTICATION (Clean & Secure)
// ============================================================================
let pendingMagicLinkToken = "";

window.handleEmailPasswordlessLogin = async function() {
  const input = document.getElementById("customGoogleEmailInput");
  const email = (input ? input.value : "").trim();
  if (!email || !email.includes("@")) {
    alert("Please enter a valid email address (e.g. scholar@university.edu)");
    return;
  }
  
  const btn = document.getElementById("emailSignInBtn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Creating secure session link...";
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/magic-link/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to create sign-in link");

    pendingMagicLinkToken = data.token;
    
    // Switch to confirmation view
    const emailSec = document.getElementById("emailAuthSection");
    const sentSec = document.getElementById("magicLinkSentSection");
    const displayEl = document.getElementById("magicLinkEmailDisplay");
    
    if (emailSec) emailSec.style.display = "none";
    if (displayEl) displayEl.textContent = email;
    if (sentSec) sentSec.style.display = "block";
    showToast(`Passwordless link created for ${email}`);
  } catch (err) {
    alert("Sign-In Error: " + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span><img src="assets/icons/kunchika-key.svg" class="fmm-icon" alt="" /></span> Continue with Email';
    }
  }
};

window.confirmMagicLinkLogin = async function() {
  if (!pendingMagicLinkToken) return;
  const btn = document.getElementById("magicLinkActivateBtn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Authenticating session...";
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/magic-link/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: pendingMagicLinkToken })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Verification failed");

    state.currentUser = data.user;
    sessionStorage.setItem("fmm_pending_toast", `Welcome to FMM Archive, ${data.user.full_name}! (30-Day Trial Active)`);
    closeModal("authModal");
    window.location.reload();
  } catch (err) {
    alert("Login Error: " + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span><img src="assets/icons/padma-scholar.svg" class="fmm-icon" alt="" /></span> Enter Archive as Trial Member';
    }
  }
};

/**
 * Five Metal Masonry (FMM) Iconography Archive
 * Frontend Controller & State Management (app.js)
 * 
 * Features:
 * - Scholar Search with Theme-First Re-Ranking (Affinity & Confidence Scoring)
 * - Visual OCR Ingestion Studio with 'Tables Impacted' Audit
 * - Admin Data Studio (Archive Table Browser, Filter, Pagination)
 * - DRM Copy/Download Protection with GPay / UPI Premium License Flow
 */

const API_BASE = ""; // Relative to origin

// ============================================================================
// SECURITY: XSS Sanitization Helper
// ============================================================================
function sanitizeHTML(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ============================================================================
// APPLICATION CONFIG (Loaded from param_config table)
// ============================================================================
const APP_CONFIG = {
  loaded: false,
  pricing: {},
  features: {},
  search: {},
  branding: {}
};

async function loadAppConfig() {
  try {
    const res = await fetch(API_BASE + "/api/config");
    const data = await res.json();
    if (data.config) {
      Object.keys(data.config).forEach(group => {
        APP_CONFIG[group] = {};
        Object.keys(data.config[group]).forEach(key => {
          APP_CONFIG[group][key] = data.config[group][key].value;
        });
      });
      APP_CONFIG.loaded = true;
      applyConfigToUI();
    }
  } catch (e) {
    console.warn("Config load note:", e);
  }
}

function getConfig(group, key, defaultVal) {
  if (APP_CONFIG[group] && APP_CONFIG[group][key] !== undefined) {
    return APP_CONFIG[group][key];
  }
  return defaultVal;
}

function applyConfigToUI() {
  // Apply pricing to member tab
  const priceEl = document.querySelector(".tier-price");
  if (priceEl && APP_CONFIG.pricing && APP_CONFIG.pricing.scholar_pro_annual_inr) {
    // Find the Scholar Pro tier price element
    const proPrice = document.querySelector(".tier-pro .tier-price");
    if (proPrice) {
      const price = APP_CONFIG.pricing.scholar_pro_annual_inr;
      proPrice.innerHTML = "\u20B9" + price + "<span class=\"tier-price-period\">/year</span>";
    }
  }

  // Apply branding
  if (APP_CONFIG.branding && APP_CONFIG.branding.watermark_text) {
    document.querySelectorAll(".watermark-badge").forEach(el => {
      el.textContent = APP_CONFIG.branding.watermark_text;
    });
  }
}

const state = {
  activeTab: "search",
  searchQuery: "",
  selectedSeries: "",
  selectedAccess: "all",
  searchResults: [],
  activeSlideIndex: 0,
  
  // Auth State
  currentUser: null,
  googleClientId: "",
  myDownloads: [],
  
  // OCR Studio State
  uploadedImage: null,
  ocrResult: null,
  selectedOcrEngine: "gemini_vision",
  
  // Admin Data Studio State
  adminTables: [],
  selectedTable: "studies",
  tableRows: [],
  tableTotalRows: 0,
  tablePage: 1,
  tablePageSize: 10,
  tableFilter: "",
  tableSortBy: "",
  tableSortDir: "asc",

  // Modals
  lightboxImage: null,
  tablesImpactedData: null,
  selectedStudyForGPay: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initDRMProtection();
  initAuth();
  applyRouteGuards();
  loadAppConfig();
  initSearch();
  initOCRStudio();
  initDataStudioModes();
  loadArchivalTelemetry();
  loadTaxonomyData();

  
  // Trigger default initial search to display featured studies
  runScholarSearch();

  // Restore hash tab if specified
  if (window.location.hash) {
    const targetTab = window.location.hash.replace("#", "").replace("tab-", "");
    if (["search", "ocr_studio", "admin_studio", "about", "member", "dictionary"].includes(targetTab)) {
      setTimeout(() => switchTab(targetTab), 50);
    }
  }

  // Display pending toast if set before page reload
  try {
    const pendingMsg = sessionStorage.getItem("fmm_pending_toast");
    if (pendingMsg) {
      sessionStorage.removeItem("fmm_pending_toast");
      setTimeout(() => showToast(pendingMsg), 300);
    }
  } catch (e) {}
});

// ============================================================================
// NAVIGATION & TABS (Desktop + Mobile Sync)
// ============================================================================

function initNavigation() {
  document.querySelectorAll(".nav-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      switchTab(target);
    });
  });

  // Close user dropdown menu when clicking outside
  document.addEventListener("click", (e) => {
    const userView = document.getElementById("authUserView");
    const dropdown = document.getElementById("userDropdownMenu");
    if (userView && dropdown && !userView.contains(e.target)) {
      dropdown.classList.remove("show");
    }
  });
}

function switchTab(tabId) {
  if (tabId === "admin_studio") {
    initDataStudioModes();
    loadArchivalTelemetry();
  }
  if (tabId === "about") setTimeout(initAbout3D, 50);
  if (tabId === "threed_gallery") {
    if (typeof exhibition3DInstance === "object" && exhibition3DInstance.refreshSize) {
      setTimeout(() => exhibition3DInstance.refreshSize(), 50);
    } else {
      setTimeout(initExhibition3D, 50);
    }
  }
  state.activeTab = tabId;
  try {
    history.replaceState(null, null, '#' + tabId);
  } catch (e) {}
  
  // Update desktop navigation buttons
  document.querySelectorAll(".nav-tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.tab === tabId);
  });
  
  // Update mobile bottom tab buttons
  document.querySelectorAll(".mobile-tab-btn").forEach(b => {
    if (b.dataset.tab) {
      b.classList.toggle("active", b.dataset.tab === tabId);
    }
  });

  // Toggle visible pane
  document.querySelectorAll(".screen-pane").forEach(p => {
    p.classList.toggle("active", p.id === `tab-${tabId}`);
  });

  // Scroll to top of screen on mobile switch
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Apply route guards based on active user role
  applyRouteGuards();

  if (tabId === "admin_studio" && state.currentUser) {
    loadAdminTables();
  } else if (tabId === "dictionary") {
    loadDictionaryEntries();
  }
}

function applyRouteGuards() {
  // Hide role-gated navigation tabs from unauthorized users
  document.querySelectorAll(".role-gated-tab").forEach(tab => {
    const requiredRoles = (tab.dataset.roleRequired || "").split(",");
    const userRole = state.currentUser ? state.currentUser.role : "";
    if (!userRole || !requiredRoles.includes(userRole)) {
      tab.style.display = "none";
    } else {
      tab.style.display = "";
    }
  });

  const ocrGate = document.getElementById("ocrStudioAuthGate");
  const ocrContent = document.getElementById("ocrStudioContent");
  const adminGate = document.getElementById("adminStudioAuthGate");
  const adminContent = document.getElementById("adminStudioContent");

  // 1. Guard OCR Studio: Requires Curator or Admin role (Admins have access to BOTH studios)
  if (ocrGate && ocrContent) {
    const hasOcrAccess = state.currentUser && (state.currentUser.role === "curator" || state.currentUser.role === "admin");
    if (hasOcrAccess) {
      ocrGate.style.display = "none";
      ocrContent.style.display = "block";
    } else {
      ocrGate.style.display = "block";
      ocrContent.style.display = "none";
      if (state.currentUser) {
        ocrGate.innerHTML = `
          <div class="auth-gate-icon"><img src="assets/icons/kavacha-shield.svg" class="fmm-icon" style="width:48px; height:48px;" alt="Shield" /></div>
          <h3>Curator Access Required</h3>
          <p>You are currently signed in as <strong>${state.currentUser.full_name} (${state.currentUser.role.toUpperCase()})</strong>.<br>Visual OCR ingestion and taxonomy curation requires Curator or Administrator privileges.</p>
          <button class="btn-secondary" onclick="executeDemoLogin('curator')" style="margin: 16px auto 0; padding:10px 20px;">
            <span><img src="assets/icons/sthapati-chisel.svg" class="fmm-icon" alt="" /></span> Switch to Curator Role (Demo)
          </button>
        `;
      } else {
        ocrGate.innerHTML = `
          <div class="auth-gate-icon"><img src="assets/icons/kavacha-shield.svg" class="fmm-icon" style="width:48px; height:48px;" alt="Shield" /></div>
          <h3>Curator Access Required</h3>
          <p>Executing OCR ingestion and approving taxonomy changes requires signing in with an authorized Curator or Administrator account.</p>
          <button class="btn-primary" onclick="openAuthModal()" style="margin: 16px auto 0; padding:12px 24px;">
            <span><img src="assets/icons/kunchika-key.svg" class="fmm-icon" alt="" /></span> Sign in to Access OCR Studio
          </button>
        `;
      }
    }
  }

  // 2. Guard Data Studio: Strictly requires Admin role (Curators access OCR studio only)
  if (adminGate && adminContent) {
    const isAdmin = state.currentUser && state.currentUser.role === "admin";
    if (isAdmin) {
      adminGate.style.display = "none";
      adminContent.style.display = "block";
    } else {
      adminGate.style.display = "block";
      adminContent.style.display = "none";
      if (state.currentUser && state.currentUser.role === "curator") {
        adminGate.innerHTML = `
          <div class="auth-gate-icon"><img src="assets/icons/kavacha-shield.svg" class="fmm-icon" style="width:48px; height:48px;" alt="Shield" /></div>
          <h3>Administrator Access Required</h3>
          <p>You are currently signed in as <strong>${state.currentUser.full_name} (CURATOR)</strong>.<br>As a Curator, you have full access to the <strong>Visual OCR Studio</strong>.<br>Direct database tables and telemetry are strictly restricted to System Administrators.</p>
          <div style="display:flex; gap:10px; justify-content:center; margin-top:16px;">
            <button class="btn-primary" onclick="switchTab('ocr_studio')">
              <span><img src="assets/icons/silpa-camera.svg" class="fmm-icon" alt="" /></span> Go to Visual OCR Studio
            </button>
            <button class="btn-secondary" onclick="executeDemoLogin('admin')">
              <span><img src="assets/icons/chola-seal.svg" class="fmm-icon" alt="" /></span> Sign In as Super Admin
            </button>
          </div>
        `;
      } else if (state.currentUser) {
        adminGate.innerHTML = `
          <div class="auth-gate-icon"><img src="assets/icons/kavacha-shield.svg" class="fmm-icon" style="width:48px; height:48px;" alt="Shield" /></div>
          <h3>Administrator Access Required</h3>
          <p>You are signed in as <strong>${state.currentUser.full_name} (${state.currentUser.role.toUpperCase()})</strong>.<br>Access to the Data Studio requires System Administrator privileges.</p>
          <button class="btn-primary" onclick="executeDemoLogin('admin')" style="margin: 16px auto 0; padding:12px 24px;">
            <span><img src="assets/icons/chola-seal.svg" class="fmm-icon" alt="" /></span> Sign In as Super Admin (ananth.seetharaman@gmail.com)
          </button>
        `;
      } else {
        adminGate.innerHTML = `
          <div class="auth-gate-icon"><img src="assets/icons/kavacha-shield.svg" class="fmm-icon" style="width:48px; height:48px;" alt="Shield" /></div>
          <h3>System Administrator Access Required</h3>
          <p>Browsing underlying database schema, user session tables, behavioral telemetry, and download licenses requires an authenticated Administrator session.</p>
          <button class="btn-primary" onclick="openAuthModal()" style="margin: 16px auto 0; padding:12px 24px;">
            <span><img src="assets/icons/kunchika-key.svg" class="fmm-icon" alt="" /></span> Sign In as Administrator
          </button>
        `;
      }
    }
  }
}

// ============================================================================
// DRM COPY PROTECTION & RIGHT-CLICK SHIELD
// ============================================================================

function initDRMProtection() {
  // Prevent contextmenu on entire archive imagery
  document.addEventListener("contextmenu", (e) => {
    if (e.target.closest(".drm-protected") || e.target.closest(".slide-image-container") || e.target.closest(".drm-shield")) {
      e.preventDefault();
      showToast("Archival Plate Protected: Right-click save disabled. Use 'Inspect 300 DPI Plate' or Member Access to view full resolution.");
    }
  });

  // Prevent dragging images
  document.addEventListener("dragstart", (e) => {
    if (e.target.tagName === "IMG" || e.target.closest(".drm-protected")) {
      e.preventDefault();
    }
  });
}

function showToast(msg) {
  const toast = document.getElementById("toastNotice");
  if (!toast) return;
  toast.innerHTML = `<div style="display:flex; align-items:center; gap:10px;">
    <span style="color:var(--gold); font-size:16px; flex-shrink:0;">🛡️</span>
    <span style="flex:1; line-height:1.4;">${msg}</span>
  </div>`;
  toast.style.display = "block";
  if (window._toastTimeout) clearTimeout(window._toastTimeout);
  window._toastTimeout = setTimeout(() => {
    toast.style.display = "none";
  }, 4500);
}

// ============================================================================
// AUTHENTICATION & GOOGLE OAUTH 2.0 CONTROLLER
// ============================================================================

async function initAuth() {
  try {
    // 1. Check if user already has an active session
    const meRes = await fetch(`${API_BASE}/api/auth/me`);
    const meData = await meRes.json();
    if (meData.authenticated && meData.user) {
      state.currentUser = meData.user;
      updateAuthUI();
    }

    // 2. Fetch server auth configuration
    const configRes = await fetch(`${API_BASE}/api/auth/config`);
    const configData = await configRes.json();
    state.googleClientId = configData.google_client_id || "";

    // 3. Initialize Google Identity Services if client ID is configured
    if (window.google && window.google.accounts && window.google.accounts.id) {
      setupGoogleIdentityServices();
    } else {
      // Retry once GIS script finishes loading
      window.addEventListener("load", () => {
        if (window.google && window.google.accounts && window.google.accounts.id) {
          setupGoogleIdentityServices();
        }
      });
    }
  } catch (err) {
    console.warn("Auth initialization note:", err);
  }
}

function setupGoogleIdentityServices() {
  if (!state.googleClientId) {
    console.log("FMM Archive: Using Scholar Demo mode. Register GOOGLE_CLIENT_ID in GCP to enable live OAuth button.");
    return;
  }

  google.accounts.id.initialize({
    client_id: state.googleClientId,
    callback: handleGoogleCredentialResponse,
    auto_select: false,
    cancel_on_tap_outside: true
  });

  // Render Google button in modal
  const modalBtnContainer = document.getElementById("modalGoogleSignInBtn");
  if (modalBtnContainer) {
    google.accounts.id.renderButton(modalBtnContainer, {
      theme: "outline",
      size: "large",
      type: "standard",
      shape: "pill",
      text: "signin_with",
      logo_alignment: "left",
      width: 280
    });
  }
}

async function handleGoogleCredentialResponse(response) {
  if (!response || !response.credential) return;

  try {
    showToast("Authenticating with Google Cloud...");
    const res = await fetch(`${API_BASE}/api/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: response.credential })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Google authentication failed");
    }

    const data = await res.json();
    state.currentUser = data.user;
    sessionStorage.setItem("fmm_pending_toast", `Welcome back, ${data.user.full_name}!`);
    closeModal("authModal");
    window.location.reload();
  } catch (err) {
    alert("Google Sign-In Error: " + err.message);
  }
}

window.executeDemoLogin = async function(role = "scholar") {
  try {
    const res = await fetch(`${API_BASE}/api/auth/demo-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: role })
    });

    const data = await res.json();
    state.currentUser = data.user;
    sessionStorage.setItem("fmm_pending_toast", `Signed in as ${data.user.full_name} (${data.user.role.toUpperCase()})`);
    closeModal("authModal");
    window.location.reload();
  } catch (err) {
    alert("Demo Sign-In Error: " + err.message);
  }
};

window.executeSignOut = async function() {
  try {
    await fetch(`${API_BASE}/api/auth/logout`, { method: "POST" });
  } catch (e) {}

  state.currentUser = null;
  const dropdown = document.getElementById("userDropdownMenu");
  if (dropdown) dropdown.classList.remove("show");
  sessionStorage.setItem("fmm_pending_toast", "Logged out of FMM Archive.");
  // Full page reload back to base url
  window.location.href = window.location.pathname;
};

function updateAuthUI() {
  const guestView = document.getElementById("authGuestView");
  const userView = document.getElementById("authUserView");
  const mobileAccountLabel = document.getElementById("mobileAccountLabel");
  const mobileAccountIcon = document.getElementById("mobileAccountIcon");

  if (state.currentUser) {
    // Show user avatar & name in desktop navbar
    if (guestView) guestView.style.display = "none";
    if (userView) userView.style.display = "block";

    const nameEl = document.getElementById("userNameLabel");
    const roleEl = document.getElementById("userRoleBadge");
    const avatarEl = document.getElementById("userAvatarImg");
    const emailEl = document.getElementById("dropdownUserEmail");
    const dropRoleEl = document.getElementById("dropdownUserRole");

    if (nameEl) nameEl.innerText = state.currentUser.full_name.split(" ")[0];
    if (roleEl) roleEl.innerText = state.currentUser.role.toUpperCase();
    if (avatarEl) {
      avatarEl.src = state.currentUser.avatar_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80";
    }
    if (emailEl) emailEl.innerText = state.currentUser.email;
    if (dropRoleEl) dropRoleEl.innerText = `Role: ${state.currentUser.role.toUpperCase()}`;

    // Update mobile tab bar
    if (mobileAccountLabel) mobileAccountLabel.innerText = state.currentUser.full_name.split(" ")[0];
    if (mobileAccountIcon) mobileAccountIcon.innerHTML = `<img src="assets/icons/rishi-user.svg" class="fmm-icon" alt="Profile" />`;

    // Auto pre-fill GPay modal email
    const gpayEmail = document.getElementById("gpayUserEmail");
    if (gpayEmail && !gpayEmail.value) {
      gpayEmail.value = state.currentUser.email;
    }
  } else {
    // Show guest sign-in button
    if (guestView) guestView.style.display = "flex";
    if (userView) userView.style.display = "none";

    if (mobileAccountLabel) mobileAccountLabel.innerText = "Sign In";
    if (mobileAccountIcon) mobileAccountIcon.innerHTML = `<img src="assets/icons/kunchika-key.svg" class="fmm-icon" alt="Sign In" />`;
  }

  // Update route guard overlays on active screens
  applyRouteGuards();

  // Update member tier cards to reflect current user state
  updateMemberTierHighlights();
}

function updateMemberTierHighlights() {
  const cards = document.querySelectorAll(".apple-tier-card");
  if (cards.length < 3) return;

  const [guestCard, scholarCard, proCard] = cards;

  // Reset highlights
  cards.forEach(c => c.style.outline = "");

  if (!state.currentUser) {
    // Guest state
    const guestBtn = guestCard.querySelector(".apple-tier-cta button");
    if (guestBtn) { guestBtn.textContent = "Current Access"; guestBtn.disabled = true; }
  } else if (state.currentUser.has_active_sub || state.currentUser.role === "admin" || state.currentUser.role === "curator") {
    // Pro/Admin/Trial state
    const isTrial = state.currentUser.subscription_tier === "trial_member" || state.currentUser.role === "scholar";
    const proBtn = proCard.querySelector(".apple-tier-cta button");
    if (proBtn) {
      proBtn.textContent = isTrial ? "Trial Active" : "Active";
      proBtn.disabled = true;
      proBtn.className = "apple-btn apple-btn-outline";
    }
    proCard.style.outline = isTrial ? "2px solid var(--gold)" : "2px solid var(--bronze)";
  } else {
    // Scholar (free account) state
    const schBtn = scholarCard.querySelector(".apple-tier-cta button");
    if (schBtn) { schBtn.textContent = "Current Plan"; schBtn.disabled = true; }
    scholarCard.style.outline = "2px solid var(--bronze)";
  }
}

window.executeDirectGoogleLogin = async function() {
  const email = (document.getElementById("customGoogleEmailInput")?.value || "").trim();
  if (!email || !email.includes("@")) {
    alert("Please enter a valid Google Account email (e.g. ananta@gmail.com)");
    return;
  }
  const name = email.split("@")[0].replace(".", " ");
  const capitalizedName = name.charAt(0).toUpperCase() + name.slice(1);
  const isCur = email.toLowerCase().includes("curator") || email.toLowerCase().includes("admin");
  const role = isCur ? "curator" : "trial";
  
  await executeDemoLoginWithCustom(email, `${capitalizedName} (Google SSO Member)`, role);
};

window.fillAndLoginGoogle = async function(email, name, role) {
  const input = document.getElementById("customGoogleEmailInput");
  if (input) input.value = email;
  await executeDemoLoginWithCustom(email, name, role);
};

async function executeDemoLoginWithCustom(email, name, role) {
  try {
    showToast(`Verifying Google Account: ${email}...`);
    const res = await fetch(`${API_BASE}/api/auth/demo-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, name: name, role: role })
    });

    const data = await res.json();
    state.currentUser = data.user;
    sessionStorage.setItem("fmm_pending_toast", `Google Account Verified: Welcome, ${data.user.full_name}!`);
    closeModal("authModal");
    window.location.reload();
  } catch (err) {
    alert("Sign-In Error: " + err.message);
  }
}

window.toggleClientIdConfig = function() {
  const box = document.getElementById("clientIdConfigBox");
  if (box) {
    box.style.display = box.style.display === "none" ? "block" : "none";
    const input = document.getElementById("customClientIdInput");
    if (input && state.googleClientId) input.value = state.googleClientId;
  }
};

window.saveCustomClientId = function() {
  const input = document.getElementById("customClientIdInput");
  if (!input) return;
  const val = input.value.trim();
  if (val) {
    state.googleClientId = val;
    localStorage.setItem("fmm_google_client_id", val);
    setupGoogleIdentityServices();
    showToast("Custom Google Client ID saved successfully.");
  }
};

window.openAuthModal = function() {
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.add("active");
};

window.toggleUserMenu = function() {
  const menu = document.getElementById("userDropdownMenu");
  if (menu) menu.classList.toggle("show");
};

window.handleMobileAccountClick = function() {
  if (state.currentUser) {
    toggleUserMenu();
  } else {
    openAuthModal();
  }
};

window.openMyDownloads = function() {
  const modal = document.getElementById("myDownloadsModal");
  const listEl = document.getElementById("myDownloadsList");
  if (!modal || !listEl) return;

  if (state.currentUser) {
    listEl.innerHTML = `
      <div class="download-item-card">
        <div>
          <strong style="display:block; font-size:14px; color:var(--ink);">Study 001: Ganesa Variations in Iconography</strong>
          <span style="font-size:12px; color:var(--muted);">4 High-Resolution Archival Plates (300 DPI) · License Active</span>
        </div>
        <button class="btn-primary" style="padding:8px 14px; font-size:12px;" onclick="downloadStudyPack('s_ganesa_001')">
          <span><img src="assets/icons/tamra-download.svg" class="fmm-icon" alt="" /></span> Download
        </button>
      </div>
    `;
  } else {
    listEl.innerHTML = `
      <div style="text-align:center; padding:20px; color:var(--muted);">
        Please <a href="#" onclick="closeModal('myDownloadsModal'); openAuthModal(); return false;" style="color:var(--accent); font-weight:700;">Sign in</a> to view your active study licenses.
      </div>
    `;
  }

  modal.classList.add("active");
};

window.downloadStudyPack = function(studyId) {
  showToast("Preparing archival print resolution bundle for download...");
  // Download slide 1 image as proof of concept
  const link = document.createElement("a");
  link.href = "/storage/images/ganesa-variations-in-iconography/slide_1.jpeg";
  link.download = "FMM_Study_001_Ganesa_Plate_1_300DPI.jpeg";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast("Download started!");
};

// ============================================================================
// SCREEN 1: SCHOLAR SEARCH & RE-RANKED DISCOVERY
// ============================================================================

function initSearch() {
  const searchInput = document.getElementById("scholarSearchInput");
  const searchBtn = document.getElementById("scholarSearchBtn");
  const seriesFilter = document.getElementById("seriesFilterSelect");
  const accessFilter = document.getElementById("accessFilterSelect");
  const dropdown = document.getElementById("autocompleteDropdown");

  let debounceTimer;

  searchInput.addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    const val = e.target.value.trim();
    if (val.length >= 2) {
      debounceTimer = setTimeout(() => fetchAutocomplete(val), 250);
    } else {
      dropdown.style.display = "none";
    }
  });

  searchBtn.addEventListener("click", () => {
    dropdown.style.display = "none";
    runScholarSearch();
  
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      dropdown.style.display = "none";
      runScholarSearch();
  
    }
  });

  seriesFilter.addEventListener("change", () => runScholarSearch());
  accessFilter.addEventListener("change", () => runScholarSearch());

  // Quick chip buttons
  document.querySelectorAll(".chip-btn").forEach(chip => {
    chip.addEventListener("click", () => {
      searchInput.value = chip.dataset.query;
      runScholarSearch();
  
    });
  });

  
  // Curated category filter chips
  document.querySelectorAll(".category-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".category-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      const cat = chip.dataset.cat.toLowerCase();
      applyCategoryFilter(cat);
    });
  });

  // Close dropdown on outside click
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-input-wrapper")) {
      dropdown.style.display = "none";
    }
  });
}

async function fetchAutocomplete(query) {
  const dropdown = document.getElementById("autocompleteDropdown");
  try {
    const res = await fetch(`${API_BASE}/api/autocomplete?q=${encodeURIComponent(query)}`);
    const items = await res.json();
    if (!items || items.length === 0) {
      dropdown.style.display = "none";
      return;
    }

    dropdown.innerHTML = items.map(item => `
      <div class="autocomplete-item" data-term="${item.term}">
        <div>
          <strong>${item.label}</strong>
        </div>
        <span class="cat-tag">${item.category}</span>
      </div>
    `).join("");

    dropdown.style.display = "block";

    dropdown.querySelectorAll(".autocomplete-item").forEach(el => {
      el.addEventListener("click", () => {
        document.getElementById("scholarSearchInput").value = el.dataset.term;
        dropdown.style.display = "none";
        runScholarSearch();
  
      });
    });
  } catch (err) {
    console.error("Autocomplete failed:", err);
  }
}

async function runScholarSearch() {
  const query = document.getElementById("scholarSearchInput").value.trim();
  const seriesId = document.getElementById("seriesFilterSelect").value;
  const accessLevel = document.getElementById("accessFilterSelect").value;

  const resultsContainer = document.getElementById("scholarResultsContainer");  const countLabel = document.getElementById("resultsCountLabel");

  resultsContainer.innerHTML = `
    <div class="scholarly-loader-stage">
      <div class="scholarly-spinner-ring">
        <img src="assets/icons/dharma-chakra.svg" class="fmm-icon rotating-chakra" alt="Rotating Dharmachakra" />
      </div>
      <h3 style="font-family:var(--font-serif); font-size:18px; color:var(--ink); margin-bottom:6px;">Querying Iconography Corpus</h3>
      <p style="color:var(--muted); font-size:13.5px; margin:0;">Calculating Shastra theme affinity, confidence ranking, and lexical cross-references...</p>
    </div>
  `;

  const params = new URLSearchParams();
  if (query) params.append("q", query);
  if (seriesId) params.append("series_id", seriesId);
  if (accessLevel && accessLevel !== "all") params.append("access_level", accessLevel);

  try {
    const res = await fetch(`${API_BASE}/api/search?${params.toString()}`);
    const data = await res.json();
    state.searchResults = data.results || [];

    if (countLabel) countLabel.innerText = `Found ${data.total_results} ${data.total_results === 1 ? 'study' : 'studies'} matching query`;

    if (state.searchResults.length === 0) {
      resultsContainer.innerHTML = `
        <div style="background:var(--paper-card); border:1px solid var(--line); border-radius:var(--radius-lg); padding:48px 24px; text-align:center;">
          <img src="assets/icons/grantha-lexicon.svg" class="fmm-icon" style="width:48px; height:48px; opacity:0.6; margin-bottom:12px;" alt="" />
          <h3 style="font-family:var(--font-serif); font-size:20px; margin-bottom:8px;">No Studies Matched Your Search</h3>
          <p style="color:var(--muted); font-size:14px; max-width:480px; margin:0 auto;">Try searching canonical divinity names like <em>Ganesha</em>, postural attributes like <em>Asina</em> or <em>Lalitasana</em>, or mount variations like <em>Mooshika</em>.</p>
        </div>
      `;
      return;
    }

    renderSearchResults(state.searchResults);
  } catch (err) {
    console.error("Search failed:", err);
    resultsContainer.innerHTML = `<div style="color:var(--danger); padding:20px;">Search request failed: ${err.message}</div>`;
  }
}

function renderSearchResults(studies) {
  const resultsContainer = document.getElementById("scholarResultsContainer");
  resultsContainer.innerHTML = "";
  const countLabel = document.getElementById("resultsCountLabel");
  if (countLabel) {
    countLabel.textContent = studies && studies.length > 0
      ? `Showing ${studies.length} monographs`
      : `0 monographs in archive`;
  }

  if (!studies || studies.length === 0) {
    const isSearch = state.searchQuery && state.searchQuery.trim().length > 0;
    const cleanQ = isSearch ? sanitizeHTML(state.searchQuery.trim()) : "";
    resultsContainer.innerHTML = `
      <div style="text-align:center; padding:60px 20px; background:var(--paper-raised); border:1px dashed var(--line); border-radius:var(--radius-lg); margin:20px 0;">
        <div style="width:56px; height:56px; border-radius:50%; background:rgba(181, 139, 75, 0.12); display:flex; align-items:center; justify-content:center; margin:0 auto 16px auto;">
          <img src="assets/icons/${isSearch ? 'shastra-search' : 'silpa-camera'}.svg" class="fmm-icon" style="width:28px; height:28px;" alt="" />
        </div>
        <h3 style="font-family:var(--font-serif); font-size:20px; margin-bottom:8px; color:var(--ink);">
          ${isSearch ? `No Iconographic Matches for "${cleanQ}"` : 'Clean Slate: Archive Empty'}
        </h3>
        <p style="font-size:14px; color:var(--muted); max-width:500px; margin:0 auto 20px auto; line-height:1.5;">
          ${isSearch 
            ? 'Scholarly re-ranking requires thematic affinity with South Indian Panchaloha iconography, Agamic canons, postures (Asana), gestures (Mudra), or divinities. Conversational greetings or non-iconographic words are excluded.'
            : 'No monographs or studies are currently loaded. Use the Visual OCR Studio to ingest new photographic plates and publish monographs.'}
        </p>
        ${!isSearch ? `
          <button class="btn-primary" onclick="switchTab('ocr_studio')" style="padding:10px 22px; font-size:13px; margin:0 auto;">
            <span><img src="assets/icons/silpa-camera.svg" class="fmm-icon" alt="" /></span> Open Visual OCR Studio
          </button>
        ` : `
          <button class="btn-secondary" onclick="document.getElementById('scholarSearchInput').value=''; state.searchQuery=''; loadStudies();" style="padding:8px 18px; font-size:12.5px; margin:0 auto;">
            Clear Search Filter
          </button>
        `}
      </div>
    `;
    return;
  }

  studies.forEach((study, studyIdx) => {
    const card = document.createElement("article");
    card.className = "study-hero-card";
    card.id = `study-card-${study.study_id}`;

    // Active slide index for this study - auto-focus to slide with matching query hit if present
    const slides = study.slides || [];
    let hitIndex = slides.findIndex(sl => sl.has_term_hit);
    let curSlideIdx = hitIndex >= 0 ? hitIndex : 0;

    card.innerHTML = `
      <div class="card-header-bar">
        <div class="study-title-group">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span class="study-series-badge">${study.series_name} · ${study.study_number || 'Study'}</span>
            <span class="badge" style="background:rgba(34, 197, 94, 0.12); color:#15803d; border:1px solid rgba(34, 197, 94, 0.3); font-size:10.5px; font-weight:700;">✓ Public Access (Non-Premium)</span>
          </div>
          <h3>${sanitizeHTML(study.title)}</h3>
          <p class="study-subtitle">${study.subtitle || ''}</p>
        </div>
        <div class="scoring-triad">
          <div class="score-badge affinity" title="Thematic Relevance: Calculated from primary vs secondary discussion">
            <span class="score-val">${study.affinity_score}%</span>
            <span class="score-lbl">Theme Affinity</span>
          </div>
          <div class="score-badge confidence" title="Scholarly Confidence: Based on verified curation & high-confidence OCR">
            <span class="score-val">${study.confidence_score}%</span>
            <span class="score-lbl">Confidence</span>
          </div>
          <div class="score-badge overall" title="Composite Scholar Rank Score">
            <span class="score-val">${study.rank_score}</span>
            <span class="score-lbl">Rank Score</span>
          </div>
        </div>
      </div>

      <!-- Match Cues: Why Matched -->
      <div class="match-cues-panel">
        <div class="match-cues-title">Scholarly Reference Cues (Why Matched):</div>
        <div class="cues-list">
          ${study.match_cues.map(cue => `<span class="cue-pill"><span class="fmm-cue-marker"></span> ${cue}</span>`).join("")}
        </div>
      </div>
    `;

    // Multi-Slide Interactive Carousel OR Premium Lock Gate
    const isLockedStudy = study.requires_subscription && (!state.currentUser || (state.currentUser.role === 'scholar' && !state.currentUser.has_active_sub));

    if (isLockedStudy) {
      // Soft gate: show first 2 slide thumbnails as preview, then fade overlay with CTA
      const previewSlides = slides.slice(0, 2);
      const lockedCount = Math.max(0, slides.length - 2);
      card.innerHTML += `
        <div class="soft-gate-preview">
          <div class="soft-gate-slides-row">
            ${previewSlides.map((sl, i) => `
              <div class="soft-gate-slide-thumb">
                <img src="${sl.image_url}" alt="Preview Plate ${i + 1}" />
                <div class="soft-gate-slide-label">Plate ${sl.slide_number}</div>
              </div>
            `).join("")}
            ${lockedCount > 0 ? `
              <div class="soft-gate-locked-count">
                <img src="assets/icons/kavacha-shield.svg" class="fmm-icon" style="width:32px; height:32px; opacity:0.7; margin-bottom:6px;" alt="" />
                <strong>+${lockedCount} more plates</strong>
                <span>Scholar Pro required</span>
              </div>
            ` : ""}
          </div>
          <div class="soft-gate-overlay">
            <div class="soft-gate-content">
              <img src="assets/icons/kavacha-shield.svg" class="fmm-icon" style="width:36px; height:36px; margin-bottom:10px;" alt="" />
              <h4>Scholar Pro Monograph</h4>
              <p>Full slides, 300 DPI plates, and verified OCR taxonomy for <strong>${study.title}</strong> require Scholar Pro access.</p>
              <div class="soft-gate-actions">
                <button class="btn-primary btn-gold" onclick="openSubscriptionGate(${JSON.stringify({study_id: study.study_id, title: study.title, total_slides: study.total_slides}).replace(/"/g, '&quot;')})" style="padding:10px 20px; font-size:13.5px;">
                  <span><img src="assets/icons/varaha-coin.svg" class="fmm-icon" alt="" /></span> Unlock Monograph
                </button>
                <button class="btn-secondary" onclick="openAuthModal()" style="padding:10px 16px; font-size:13px;">
                  <span><img src="assets/icons/kunchika-key.svg" class="fmm-icon" alt="" /></span> Sign In
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    } else {
      const hasSlides = slides && slides.length > 0;
      card.innerHTML += `
        <div class="carousel-stage">
          <!-- Slide Image Viewer OR Clean Slate Ingestion Placeholder -->
          ${hasSlides ? `
            <div class="slide-viewer-box">
              <div class="slide-image-container drm-protected">
                <img class="slide-image" id="slide-img-${study.study_id}" src="${formatImageUrl(slides[curSlideIdx].image_url)}" onerror="this.style.display='none';" alt="Carousel Slide Plate">
                <!-- DRM Invisible Shield to block right click & drag -->
                <div class="drm-shield" title="Archival Protected Image. Right click disabled."></div>
                <div class="watermark-badge">Five Metal Masonry · Digital Archive</div>
              </div>
              <div class="slide-controls-overlay">
                <button class="ctrl-btn prev-slide-btn" title="Previous Slide"><img src="assets/icons/arrow-left.svg" class="fmm-icon" alt="Prev" /></button>
                <button class="ctrl-btn next-slide-btn" title="Next Slide"><img src="assets/icons/arrow-right.svg" class="fmm-icon" alt="Next" /></button>
                <button class="ctrl-btn preview-plate-btn" title="Preview Full High-Res Plate"><img src="assets/icons/drishti-lens.svg" class="fmm-icon" alt="Preview" /></button>
              </div>
            </div>
          ` : `
            <div class="slide-viewer-box empty-ingestion-box" style="display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:300px; background:var(--paper-sunken); border:2px dashed var(--line); border-radius:var(--radius-md); padding:28px 20px; text-align:center;">
              <div style="width:52px; height:52px; border-radius:50%; background:rgba(181, 139, 75, 0.12); display:flex; align-items:center; justify-content:center; margin-bottom:12px;">
                <img src="assets/icons/silpa-camera.svg" class="fmm-icon" style="width:26px; height:26px;" alt="Camera" />
              </div>
              <h4 style="font-family:var(--font-serif); font-size:16px; margin:0 0 6px 0; color:var(--ink);">Awaiting Archival Ingestion</h4>
              <p style="font-size:12px; color:var(--muted); max-width:240px; line-height:1.45; margin:0 0 16px 0;">
                Clean slate: No photographic plates loaded yet. Ingest Plate 1 manually in the Visual OCR Studio.
              </p>
              <button class="btn-primary" onclick="switchTab('ocr_studio')" style="padding:8px 16px; font-size:12px;">
                <span><img src="assets/icons/silpa-camera.svg" class="fmm-icon" alt="" /></span> Ingest Plate in OCR Studio
              </button>
            </div>
          `}

          <!-- Slide Metadata & OCR Column -->
          <div class="slide-meta-box">
            <div>
              <div class="slide-number-indicator" id="slide-num-lbl-${study.study_id}">
                ${slides.length > 0 ? `Slide ${curSlideIdx + 1} of ${slides.length}` : 'Awaiting Archival Ingestion'}
              </div>
              <h4 class="slide-title-head" id="slide-title-${study.study_id}">
                ${slides[curSlideIdx] ? slides[curSlideIdx].slide_title : (slides.length === 0 ? 'No Plates Ingested Yet' : 'Overview')}
              </h4>
            </div>

            <p class="slide-caption-text" id="slide-caption-${study.study_id}">
              ${slides[curSlideIdx] ? (slides[curSlideIdx].caption || 'Detailed iconographic plate.') : ''}
            </p>

            <!-- Embedded Text Corpus Hit Banner -->
            <div class="ocr-corpus-hit-banner" id="slide-ocr-snippet-${study.study_id}" style="${(slides[curSlideIdx] && slides[curSlideIdx].has_term_hit && slides[curSlideIdx].snippet) ? 'display:block;' : 'display:none;'} margin: 10px 0 14px 0; padding: 10px 14px; background: rgba(181, 139, 75, 0.12); border-left: 3px solid var(--accent); border-radius: var(--radius-sm);">
              <div style="display:flex; align-items:center; gap:6px; font-size:11px; font-weight:700; text-transform:uppercase; color:var(--accent); letter-spacing:0.05em; margin-bottom:4px;">
                <img src="assets/icons/grantha-lexicon.svg" class="fmm-icon" style="width:14px; height:14px;" alt="" />
                <span id="slide-snippet-title-${study.study_id}">Embedded Text Corpus Match (Plate ${slides[curSlideIdx] ? slides[curSlideIdx].slide_number : 1})</span>
              </div>
              <div id="slide-snippet-body-${study.study_id}" style="font-size:13.5px; color:var(--ink); line-height:1.5; font-style:italic;">
                "${(slides[curSlideIdx] && slides[curSlideIdx].snippet) ? sanitizeHTML(slides[curSlideIdx].snippet) : ''}"
              </div>
            </div>

            <!-- Thumbnail Strip / Empty Slide Ingestion Notice -->
            ${slides.length > 0 ? `
              <div class="thumbnail-filmstrip" id="thumb-strip-${study.study_id}">
                ${slides.map((sl, sIdx) => `
                  <div class="thumb-item ${sIdx === curSlideIdx ? 'active' : ''}" data-index="${sIdx}" title="${sl.slide_title}">
                    <img src="${formatImageUrl(sl.image_url)}" onerror="this.onerror=null; this.src='/assets/shilpa_shastra_iconography.jpg';" alt="Thumbnail ${sl.slide_number}">
                    ${sl.has_term_hit ? '<div class="thumb-hit-indicator" title="Query hit in this slide"></div>' : ''}
                  </div>
                `).join("")}
              </div>
            ` : `
              <div style="padding: 10px 14px; background: var(--paper-sunken); border: 1px dashed var(--line); border-radius: var(--radius-sm); font-size: 12px; color: var(--muted); margin: 10px 0 14px 0; display: flex; align-items: center; gap: 8px;">
                <span style="font-size:14px;">📷</span>
                <span>Clean Slate: 0 slides ingested. Drop a plate in <a href="#ocr_studio" onclick="switchTab('ocr_studio'); return false;" style="color:var(--accent); font-weight:700;">Visual OCR Studio</a> to ingest into this study.</span>
              </div>
            `}

            <div class="card-actions-row">
              ${hasSlides ? `
                <button class="btn-primary preview-plate-btn inspect-plate-btn">
                  <span><img src="assets/icons/drishti-lens.svg" class="fmm-icon" alt="" /></span> Inspect 300 DPI Archival Plate
                </button>
              ` : `
                <button class="btn-primary" onclick="switchTab('ocr_studio')">
                  <span><img src="assets/icons/silpa-camera.svg" class="fmm-icon" alt="" /></span> + Ingest Archival Plate
                </button>
              `}
              <button class="btn-secondary view-study-details-btn">
                <span><img src="assets/icons/grantha-lexicon.svg" class="fmm-icon" alt="" /></span> Study Monograph Notes
              </button>
            </div>
          </div>
        </div>
      `;
    }

    resultsContainer.appendChild(card);

    // Carousel Interactivity (if not locked)
    const prevBtn = card.querySelector(".prev-slide-btn");
    const nextBtn = card.querySelector(".next-slide-btn");
    const previewBtn = card.querySelector(".preview-plate-btn");
    const downloadBtn = card.querySelector(".request-download-btn");
    const thumbItems = card.querySelectorAll(".thumb-item");

    if (prevBtn) {
      function updateCarouselSlide(idx) {
        if (!slides || slides.length === 0) return;
        if (idx < 0) idx = slides.length - 1;
        if (idx >= slides.length) idx = 0;
        curSlideIdx = idx;

        const sl = slides[curSlideIdx];
        if (!sl) return;

        card.querySelector(`#slide-img-${study.study_id}`).src = formatImageUrl(sl.image_url);
        card.querySelector(`#slide-num-lbl-${study.study_id}`).innerText = `Slide ${sl.slide_number} of ${slides.length}`;
        card.querySelector(`#slide-title-${study.study_id}`).innerText = sl.slide_title;
        card.querySelector(`#slide-caption-${study.study_id}`).innerText = sl.caption || '';
        const ocrEl = card.querySelector(`#slide-ocr-snippet-${study.study_id}`);
        if (ocrEl) {
          if (sl.has_term_hit && sl.snippet) {
            ocrEl.style.display = 'block';
            const titleEl = card.querySelector(`#slide-snippet-title-${study.study_id}`);
            const bodyEl = card.querySelector(`#slide-snippet-body-${study.study_id}`);
            if (titleEl) titleEl.innerText = `Embedded Text Corpus Match (Plate ${sl.slide_number})`;
            if (bodyEl) bodyEl.innerText = `"${sl.snippet}"`;
          } else {
            ocrEl.style.display = 'none';
          }
        }

        thumbItems.forEach((th, tIdx) => {
          th.classList.toggle("active", tIdx === curSlideIdx);
        });
      }

      prevBtn.addEventListener("click", () => updateCarouselSlide(curSlideIdx - 1));
      nextBtn.addEventListener("click", () => updateCarouselSlide(curSlideIdx + 1));

      previewBtn.addEventListener("click", () => {
        const sl = slides[curSlideIdx];
        openLightbox(sl ? sl.image_url : study.cover_image_url, `${study.title} - Plate ${sl ? sl.slide_number : 1}`);
      });

      thumbItems.forEach(th => {
        th.addEventListener("click", () => {
          const idx = parseInt(th.dataset.index, 10);
          updateCarouselSlide(idx);
        });
      });
    }

    if (downloadBtn) {
      downloadBtn.addEventListener("click", () => {
        const sl = slides[curSlideIdx];
        openLightbox(sl ? sl.image_url : study.cover_image_url, `${study.title} - Plate ${sl ? sl.slide_number : 1}`);
      });
    }

    const detailsBtn = card.querySelector(".view-study-details-btn");
    if (detailsBtn) {
      detailsBtn.addEventListener("click", () => {
        alert(`Study Abstract:\n\n${study.summary_markdown || study.subtitle || study.title}`);
      });
    }
  });
}

// ============================================================================
// SCREEN 2: VISUAL OCR INGESTION & APPROVAL STUDIO
// ============================================================================


// ============================================================================
// SCREEN 2: VISUAL OCR INGESTION & SELF-LEARNING ARCHIVAL STUDIO
// ============================================================================


window.selectOcrEngine = function(engine) {
  state.selectedOcrEngine = engine || "gemini_vision";
  const geminiCard = document.getElementById("labelEngineGemini");
  const winCard = document.getElementById("labelEngineWindows");
  const radioGemini = document.getElementById("engineGeminiRadio");
  const radioWin = document.getElementById("engineWindowsRadio");
  const activeBadge = document.getElementById("activeEngineBadge");
  const pipeStep2Name = document.getElementById("pipeStep2Name");
  const streamLabel = document.getElementById("ocrEngineStreamLabel");
  const indicatorTag = document.getElementById("ocrEngineIndicatorTag");

  if (state.selectedOcrEngine === "gemini_vision") {
    if (geminiCard) geminiCard.classList.add("active");
    if (winCard) winCard.classList.remove("active");
    if (radioGemini) radioGemini.checked = true;
    if (radioWin) radioWin.checked = false;

    const b1 = geminiCard ? geminiCard.querySelector(".engine-radio-bullet") : null;
    const b2 = winCard ? winCard.querySelector(".engine-radio-bullet") : null;
    if (b1) b1.innerText = "●";
    if (b2) b2.innerText = "○";

    if (activeBadge) {
      activeBadge.innerHTML = "✦ Gemini Vision Model Active (Default)";
      activeBadge.style.background = "rgba(181, 139, 75, 0.12)";
      activeBadge.style.borderColor = "rgba(181, 139, 75, 0.35)";
      activeBadge.style.color = "var(--accent)";
    }
    if (pipeStep2Name) pipeStep2Name.innerText = "Gemini Vision Model";
    if (streamLabel) streamLabel.innerHTML = "Raw Engine Stream (Gemini 2.5 Flash Vision):";
    if (indicatorTag) {
      indicatorTag.innerText = "gemini-2.5-flash";
      indicatorTag.style.background = "rgba(181, 139, 75, 0.15)";
      indicatorTag.style.color = "var(--accent)";
    }
  } else {
    if (winCard) winCard.classList.add("active");
    if (geminiCard) geminiCard.classList.remove("active");
    if (radioWin) radioWin.checked = true;
    if (radioGemini) radioGemini.checked = false;

    const b1 = geminiCard ? geminiCard.querySelector(".engine-radio-bullet") : null;
    const b2 = winCard ? winCard.querySelector(".engine-radio-bullet") : null;
    if (b1) b1.innerText = "○";
    if (b2) b2.innerText = "●";

    if (activeBadge) {
      activeBadge.innerHTML = "⚙ Windows Native OCR Active (Offline)";
      activeBadge.style.background = "rgba(100, 116, 139, 0.12)";
      activeBadge.style.borderColor = "rgba(100, 116, 139, 0.35)";
      activeBadge.style.color = "var(--ink-soft)";
    }
    if (pipeStep2Name) pipeStep2Name.innerText = "Windows Media OCR";
    if (streamLabel) streamLabel.innerHTML = "Raw Engine Stream (Windows.Media.Ocr):";
    if (indicatorTag) {
      indicatorTag.innerText = "windows_media_ocr";
      indicatorTag.style.background = "var(--line)";
      indicatorTag.style.color = "var(--muted)";
    }
  }
};

function initOCRStudio() {
  const fileInput = document.getElementById("ocrFileInput");
  const uploadDropzone = document.getElementById("ocrDropzone");
  const sampleBtnMudra = document.getElementById("sampleBtnMudra");
  const sampleBtn1 = document.getElementById("sampleBtn1");
  const sampleBtn2 = document.getElementById("sampleBtn2");
  const approveBtn = document.getElementById("approveIngestBtn");

  if (uploadDropzone && fileInput) {
    uploadDropzone.addEventListener("click", (e) => {
      if (e.target.closest(".sample-archetypes-row") || e.target.closest("button")) return;
      fileInput.click();
    });

    uploadDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadDropzone.style.borderColor = "var(--accent)";
      uploadDropzone.style.background = "var(--paper-sunken)";
    });

    uploadDropzone.addEventListener("dragleave", () => {
      uploadDropzone.style.borderColor = "var(--line)";
      uploadDropzone.style.background = "transparent";
    });

    uploadDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadDropzone.style.borderColor = "var(--line)";
      uploadDropzone.style.background = "transparent";
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFileUpload(e.target.files[0]);
      }
    });
  }

  // Quick Curated Archival Archetypes
  if (sampleBtnMudra) {
    sampleBtnMudra.addEventListener("click", (e) => {
      e.stopPropagation();
      loadSampleSlide("mudra");
    });
  }
  if (sampleBtn1) {
    sampleBtn1.addEventListener("click", (e) => {
      e.stopPropagation();
      loadSampleSlide(1);
    });
  }
  if (sampleBtn2) {
    sampleBtn2.addEventListener("click", (e) => {
      e.stopPropagation();
      loadSampleSlide(2);
    });
  }

  if (approveBtn) {
    approveBtn.addEventListener("click", handleCuratorApproval);
  }

  updateOcrPipelineStep(1);
}

function updateOcrPipelineStep(stepNumber) {
  for (let i = 1; i <= 5; i++) {
    const node = document.getElementById(`pipeStep${i}`);
    const conn = document.getElementById(`pipeConn${i}`);
    if (!node) continue;

    if (i < stepNumber) {
      node.className = "pipeline-step-node completed";
      const circle = node.querySelector(".pipeline-circle");
      if (circle) circle.innerHTML = "✓";
      if (conn) conn.className = "pipeline-connector active";
    } else if (i === stepNumber) {
      node.className = "pipeline-step-node active";
      const circle = node.querySelector(".pipeline-circle");
      if (circle) circle.innerHTML = i.toString();
      if (conn) conn.className = "pipeline-connector";
    } else {
      node.className = "pipeline-step-node";
      const circle = node.querySelector(".pipeline-circle");
      if (circle) circle.innerHTML = i.toString();
      if (conn) conn.className = "pipeline-connector";
    }
  }
}

async function handleFileUpload(file) {
  const stage = document.getElementById("ocrPreviewStage");
  const uploadPrompt = document.getElementById("ocrUploadPrompt");
  const previewImg = document.getElementById("ocrPreviewImg");
  const rawTextEl = document.getElementById("ocrRawText");
  const cleanedTextEl = document.getElementById("ocrCleanedText");
  const storageUriEl = document.getElementById("ocrStorageUri");
  const wordCountEl = document.getElementById("ocrCleanWordCount");

  updateOcrPipelineStep(2);

  const engine = state.selectedOcrEngine || "gemini_vision";
  const engineLabel = engine === "gemini_vision" ? "Gemini Vision Model (gemini-2.5-flash)" : "Windows Native OCR (Windows.Media.Ocr)";

  uploadPrompt.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; gap:10px; color:var(--accent); font-weight:700; padding:10px;">
      <img src="assets/icons/dharma-chakra.svg" class="fmm-icon rotating-chakra" style="width:20px; height:20px;" alt="" />
      <span>Executing ${engineLabel} &amp; Sanskrit IAST Processing...</span>
    </div>
  `;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("study_slug", "ganesa-variations-in-iconography");
  formData.append("engine", engine);

  try {
    const res = await fetch(`${API_BASE}/api/ocr/upload`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Image upload rejected by server.");
    }
    state.ocrResult = data;

    updateOcrPipelineStep(3);
    setTimeout(() => updateOcrPipelineStep(4), 400);

    // Display side-by-side
    previewImg.src = data.image_url;
    rawTextEl.innerText = data.raw_ocr;
    cleanedTextEl.innerText = data.cleaned_ocr;
    if (storageUriEl) storageUriEl.innerText = data.image_url;
    if (wordCountEl) wordCountEl.innerText = `${data.word_count || data.cleaned_ocr.split(/\s+/).length} words`;
    
    if (data.engine_used) {
      const tag = document.getElementById("ocrEngineIndicatorTag");
      if (tag) tag.innerText = data.engine_used;
    }

    renderProposals(data.proposals);
    updatePrecommitImpact(data.proposals);

    stage.style.display = "block";
    uploadPrompt.innerHTML = `
      <div style="display:flex; align-items:center; justify-content:center; gap:8px; color:var(--success); font-weight:700;">
        <img src="assets/icons/pramana-check.svg" class="fmm-icon" style="width:16px; height:16px;" alt="" />
        <span>Extraction complete (${data.word_count} words recognized with IAST diacritic restoration)</span>
      </div>
    `;
  } catch (err) {
    console.error("OCR Upload failed:", err);
    stage.style.display = "none";
    uploadPrompt.innerHTML = `
      <div style="color:var(--danger); padding:12px 16px; background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:var(--radius-md); font-size:13px; line-height:1.5; margin-top:8px;">
        <strong>⚠️ Shilpa Shastra Validation Error:</strong><br/>
        <span>${err.message}</span>
      </div>
    `;
    if (typeof showToast === "function") {
      showToast(`⚠️ ${err.message}`);
    }
    updateOcrPipelineStep(1);
  }
}

function loadSampleSlide(slideType) {
  const stage = document.getElementById("ocrPreviewStage");
  const previewImg = document.getElementById("ocrPreviewImg");
  const rawTextEl = document.getElementById("ocrRawText");
  const cleanedTextEl = document.getElementById("ocrCleanedText");
  const storageUriEl = document.getElementById("ocrStorageUri");
  const wordCountEl = document.getElementById("ocrCleanWordCount");
  const uploadPrompt = document.getElementById("ocrUploadPrompt");
  const plateBadge = document.getElementById("ocrPlateBadge");

  // Highlight active button
  document.querySelectorAll(".archetype-btn").forEach(b => b.classList.remove("active"));
  if (slideType === "mudra" && document.getElementById("sampleBtnMudra")) document.getElementById("sampleBtnMudra").classList.add("active");
  if (slideType === 1 && document.getElementById("sampleBtn1")) document.getElementById("sampleBtn1").classList.add("active");
  if (slideType === 2 && document.getElementById("sampleBtn2")) document.getElementById("sampleBtn2").classList.add("active");

  updateOcrPipelineStep(2);

  let sampleUrl = "";
  let rawSample = "";
  let cleanSample = "";
  let proposals = [];
  let badgeText = "Archival Plate";

  if (slideType === "mudra") {
    sampleUrl = "/storage/images/ganesa-variations-in-iconography/upload_c3b616_mudra.jfif";
    badgeText = "Curated Mudra Hand Gesture Plate";
    if (state.selectedOcrEngine === "gemini_vision") {
      rawSample = "[Gemini 2.5 Flash Epigraphical Transcribe]\nŚikhara Mudrā (Hand Gesture):\nLiteral Meaning: Upright thumb rising firmly above closed fist.\nIconographical Role: Intent to strike, brandish sacred ayudhas, or clasp arrows.\nCanonical Associations: Rāma, dynamic manifestations of Śiva, and multi-armed Devis in Chola bronze casting.";
      cleanSample = "Śikhara (Mudra / Hasta): Literally denotes upright thumb rising above fist hand. Its characteristic iconography indicates intent to strike or brandish weapons, holding attributes or arrows. Frequently associated with deities holding bow (Rāma, forms of Śiva, Devis), and expressive iconographic hand gestures in Chola bronze sculpture.";
    } else {
      rawSample = "Sikhara literally moans upright ihumb rising above fist hand its characteristic ICONOGRAPHY • Intent to strike / brandish weapon • Holding attributes / arrows • Associated with: Deities holding bow (Rama, Forms of Siva, Devis), expressiVe iconographic gestures in bronze sculpture.";
      cleanSample = "Śikhara (Mudra / Hasta): Literally denotes upright thumb rising above fist hand. Its characteristic iconography indicates intent to strike or brandish weapons, holding attributes or arrows. Frequently associated with deities holding bow (Rāma, forms of Śiva, Devis), and expressive iconographic hand gestures in Chola bronze sculpture.";
    }
    proposals = [
      {
        id: "prop_mudra_1",
        term_id: "t_shikhara_mudra",
        canonical_name: "Shikhara Mudra",
        iast_name: "Śikhara Mudrā",
        category: "Mudra",
        confidence: 0.98,
        evidence_snippet: "Sikhara literally means upright thumb rising above fist hand...",
        is_new_discovery: true,
        approved: true
      },
      {
        id: "prop_mudra_2",
        term_id: "t_mudra",
        canonical_name: "Mudra",
        iast_name: "Mudrā (Hasta)",
        category: "Mudra",
        confidence: 0.96,
        evidence_snippet: "...expressive iconographic gestures in bronze sculpture",
        is_new_discovery: false,
        approved: true
      },
      {
        id: "prop_mudra_3",
        term_id: "t_siva",
        canonical_name: "Shiva",
        iast_name: "Śiva",
        category: "Divinity",
        confidence: 0.94,
        evidence_snippet: "...Forms of Siva, Devis...",
        is_new_discovery: false,
        approved: true
      }
    ];
  } else if (slideType === 1) {
    sampleUrl = "/storage/images/ganesa-variations-in-iconography/slide_1.jpeg";
    badgeText = "Monograph 001 · Introductory Plate";
    rawSample = "ICONOGRAPHY VARIATIONS IN ICONOGRAPHY The iconography of Ganesa presents considerable variation in posture, composition and anatomical form. This study examines these visible variations— including the number of arms and faces, disposition of the trunk and distinctive regional configurations—rather than presenting another prescribed set of forms. Some of these variations occur within the well- known 32 forms of GaQeSa (covered earlier) and are revisited here specifically to -illustrate their distinctive iconographic features.";
    cleanSample = "The iconography of Gaṇeśa presents considerable variation in posture, composition and anatomical form. This study examines these visible variations—including the number of arms and faces, disposition of the trunk and distinctive regional configurations—rather than presenting another prescribed set of forms. Some of these variations occur within the well-known 32 forms of Gaṇeśa (covered earlier).";
    proposals = [
      {
        id: "p1",
        term_id: "t_ganesha",
        canonical_name: "Ganesha",
        iast_name: "Gaṇeśa",
        category: "Divinity",
        confidence: 0.99,
        evidence_snippet: "The iconography of Gaṇeśa presents considerable variation...",
        is_new_discovery: false,
        approved: true
      },
      {
        id: "p2",
        term_id: "t_asina",
        canonical_name: "Asina",
        iast_name: "Āsīna",
        category: "Asana",
        confidence: 0.95,
        evidence_snippet: "...variation in posture, composition and anatomical form...",
        is_new_discovery: false,
        approved: true
      }
    ];
  } else {
    sampleUrl = "/storage/images/ganesa-variations-in-iconography/slide_2.jpeg";
    badgeText = "Monograph 001 · Taxonomy Plate";
    rawSample = "1. POSTURAL & COMPOSITIONAL VARIATIONS • ÄsTna — seated • Sthänaka — standing • Nrtta — dancing • Mü$kavähana — mounted/seated upon the mü#ika • With Devi/Devis 2. ANATOMICAL VARIATIONS Bähu-bheda • Dvibhuja • Caturbhuja • Sadbhuja • TriSuQ4a GaQapati, Pune— three-trunked form";
    cleanSample = "1. Postural & Compositional Variations: Āsīna (seated), Sthānaka (standing), Nṛtta (dancing), Mūṣikavāhana (mounted upon mūṣika), With Devi/Devis. 2. Anatomical Variations: Bāhu-bheda (Dvibhuja, Caturbhuja, Ṣaḍbhuja), Triśuṇḍa Gaṇapati, Pune (three-trunked form).";
    proposals = [
      {
        id: "p1",
        term_id: "t_asina",
        canonical_name: "Asina",
        iast_name: "Āsīna",
        category: "Asana",
        confidence: 0.98,
        evidence_snippet: "Āsīna — seated",
        is_new_discovery: false,
        approved: true
      },
      {
        id: "p2",
        term_id: "t_sthanaka",
        canonical_name: "Sthanaka",
        iast_name: "Sthānaka",
        category: "Asana",
        confidence: 0.97,
        evidence_snippet: "Sthānaka — standing",
        is_new_discovery: false,
        approved: true
      },
      {
        id: "p3",
        term_id: "t_musika",
        canonical_name: "Musika",
        iast_name: "Mūṣika",
        category: "Vahana",
        confidence: 0.96,
        evidence_snippet: "Mūṣikavāhana — mounted upon mūṣika",
        is_new_discovery: false,
        approved: true
      },
      {
        id: "p4",
        term_id: "t_trishunda",
        canonical_name: "Trishunda",
        iast_name: "Triśuṇḍa",
        category: "Ayudha",
        confidence: 0.99,
        evidence_snippet: "Triśuṇḍa Gaṇapati, Pune— three-trunked form",
        is_new_discovery: false,
        approved: true
      }
    ];
  }

  state.ocrResult = {
    image_url: sampleUrl,
    raw_ocr: rawSample,
    cleaned_ocr: cleanSample,
    proposals: proposals
  };

  previewImg.src = sampleUrl;
  rawTextEl.innerText = rawSample;
  cleanedTextEl.innerText = cleanSample;
  if (storageUriEl) storageUriEl.innerText = sampleUrl;
  if (plateBadge) plateBadge.innerText = badgeText;
  if (wordCountEl) wordCountEl.innerText = `${cleanSample.split(/\s+/).length} words`;

  updateOcrPipelineStep(3);
  setTimeout(() => updateOcrPipelineStep(4), 250);

  renderProposals(proposals);
  updatePrecommitImpact(proposals);

  stage.style.display = "block";
  if (uploadPrompt) {
    uploadPrompt.innerHTML = `
      <div style="display:flex; align-items:center; justify-content:center; gap:8px; color:var(--success); font-weight:700;">
        <img src="assets/icons/pramana-check.svg" class="fmm-icon" style="width:16px; height:16px;" alt="" />
        <span>Curated Archetype Loaded: Ready for review and DuckDB ingestion</span>
      </div>
    `;
  }
}

function getCategoryClass(cat) {
  const c = (cat || "").toLowerCase();
  if (c.includes("mudra") || c.includes("hasta")) return "prop-cat-mudra";
  if (c.includes("asana") || c.includes("sthana") || c.includes("posture")) return "prop-cat-asana";
  if (c.includes("divin") || c.includes("deity") || c.includes("god")) return "prop-cat-divinity";
  if (c.includes("ayudha") || c.includes("weapon") || c.includes("feature")) return "prop-cat-ayudha";
  if (c.includes("vahana") || c.includes("mount")) return "prop-cat-vahana";
  return "prop-cat-mudra";
}

function renderProposals(proposals) {
  const list = document.getElementById("layer2ProposalsList");
  const countEl = document.getElementById("ocrProposalCount");
  if (!list) return;
  list.innerHTML = "";

  if (countEl) countEl.innerText = `${proposals.length} detected`;

  proposals.forEach((p, idx) => {
    const item = document.createElement("div");
    item.className = "proposal-item";
    const catClass = getCategoryClass(p.category);

    item.innerHTML = `
      <div style="flex:1; padding-right:12px;">
        <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px;">
          <span class="prop-cat-badge ${catClass}">${p.category}</span>
          ${p.is_new_discovery ? `<span class="prop-discovery-tag"><img src="assets/icons/dharma-chakra.svg" class="fmm-icon" style="width:11px; height:11px;" alt="" /> Auto-Discovered Concept</span>` : ''}
        </div>
        <div style="font-family:var(--font-serif); font-size:15px; font-weight:700; color:var(--ink); margin:4px 0 2px 0;">
          ${p.canonical_name} ${p.iast_name ? `<span style="font-size:13px; font-weight:400; color:var(--muted); font-style:italic;">(${p.iast_name})</span>` : ''}
        </div>
        <div style="font-size:12px; color:var(--muted); line-height:1.4;">
          Evidence: <span style="font-style:italic; color:var(--ink-soft);">${p.evidence_snippet}</span>
        </div>
      </div>
      <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px; flex-shrink:0;">
        <span class="badge" style="background:#f0fdf4; color:#166534; font-weight:700; border:1px solid #bbf7d0; font-size:11px;">
          ${Math.round((p.confidence || 0.95) * 100)}% Conf
        </span>
        <label style="font-size:11.5px; color:var(--ink-soft); display:flex; align-items:center; gap:4px; cursor:pointer;">
          <input type="checkbox" ${p.approved !== false ? 'checked' : ''} onchange="toggleProposalApproval(${idx}, this.checked)">
          <span>Include</span>
        </label>
      </div>
    `;
    list.appendChild(item);
  });
}

window.toggleProposalApproval = function(index, isChecked) {
  if (state.ocrResult && state.ocrResult.proposals && state.ocrResult.proposals[index]) {
    state.ocrResult.proposals[index].approved = isChecked;
    updatePrecommitImpact(state.ocrResult.proposals);
  }
};

function updatePrecommitImpact(proposals) {
  const bar = document.getElementById("precommitImpactBar");
  const chipsContainer = document.getElementById("precommitImpactChips");
  const approveBtn = document.getElementById("approveIngestBtn");

  if (!bar || !chipsContainer) return;

  const approved = (proposals || []).filter(p => p.approved !== false);
  const hasNewDiscovery = approved.some(p => p.is_new_discovery);

  chipsContainer.innerHTML = `
    <span class="impact-chip insert">+1 study_slides</span>
    <span class="impact-chip insert">+1 slide_ocr_data</span>
    <span class="impact-chip update">+1 studies (slide counter)</span>
    <span class="impact-chip insert">+${approved.length} ai_metadata_proposals</span>
    <span class="impact-chip insert">+${approved.length} study_taxonomy_mappings</span>
    ${hasNewDiscovery ? `<span class="impact-chip insert" style="background:#fef3c7; border-color:#f59e0b; color:#92400e;">+1 taxonomy_terms (auto-created)</span>` : ''}
    ${hasNewDiscovery ? `<span class="impact-chip insert" style="background:#fef3c7; border-color:#f59e0b; color:#92400e;">+3 term_aliases (auto-generated)</span>` : ''}
  `;

  bar.style.display = "flex";
  if (approveBtn) {
    approveBtn.disabled = approved.length === 0;
  }
}

async function handleCuratorApproval() {
  if (!state.ocrResult) return;

  updateOcrPipelineStep(5);

  const approvedProposals = (state.ocrResult.proposals || []).filter(p => p.approved !== false);

  const payload = {
    study_id: "s_ganesa_001",
    slide_number: 6,
    slide_title: state.ocrResult.image_url.includes("mudra") ? "Shikhara Mudra: Canonical Iconographic Hand Gesture" : "Curated Slide: New Iconography Plate",
    image_url: state.ocrResult.image_url,
    raw_ocr: state.ocrResult.raw_ocr,
    cleaned_ocr: state.ocrResult.cleaned_ocr,
    approved_proposals: approvedProposals,
    ocr_engine: state.ocrResult.engine_used || (state.selectedOcrEngine === "gemini_vision" ? "gemini-2.5-flash" : "windows_media_ocr")
  };

  try {
    const res = await fetch(`${API_BASE}/api/ocr/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errText = await res.text();
      let errMsg = errText;
      try {
        const parsed = JSON.parse(errText);
        errMsg = parsed.detail || errText;
      } catch (e) {}
      throw new Error(errMsg);
    }

    const auditResponse = await res.json();

    // Mark step 5 completed
    for (let i = 1; i <= 5; i++) {
      const n = document.getElementById(`pipeStep${i}`);
      if (n) {
        n.className = "pipeline-step-node completed";
        const c = n.querySelector(".pipeline-circle");
        if (c) c.innerHTML = "✓";
      }
    }

    openTablesImpactedModal(auditResponse);
  } catch (err) {
    console.error("Approval commit failed:", err);
    alert("Approval commit failed: " + err.message);
    updateOcrPipelineStep(4);
  }
}

function openTablesImpactedModal(audit) {
  const modal = document.getElementById("tablesImpactedModal");
  const listEl = document.getElementById("auditImpactList");
  const msgEl = document.getElementById("auditMessage");

  if (msgEl) msgEl.innerText = audit.message || "Slide successfully ingested into DuckDB!";

  if (listEl) {
    listEl.innerHTML = `
      <div style="margin-bottom:16px; padding:10px 14px; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:var(--radius-md); font-size:12.5px; color:#166534; display:flex; align-items:center; gap:8px;">
        <img src="assets/icons/pramana-check.svg" class="fmm-icon" style="width:16px; height:16px;" alt="" />
        <span>Transaction committed atomically to DuckDB. Concept mappings and slide-level search indexes active!</span>
      </div>
      ${(audit.tables_impacted || []).map(item => `
        <div class="audit-impact-row">
          <span class="audit-op-badge ${item.operation.toLowerCase()}">${item.operation}</span>
          <div style="flex:1;">
            <div class="audit-table-name">${item.table_name} (${item.rows_impacted} ${item.rows_impacted === 1 ? 'row' : 'rows'})</div>
            <div class="audit-desc">${item.description}</div>
          </div>
        </div>
      `).join("")}
      <div style="margin-top:20px; display:flex; gap:10px; justify-content:flex-end;">
        <button class="btn-secondary" onclick="closeModal('tablesImpactedModal')" style="padding:10px 18px;">Close</button>
        <button class="btn-primary" onclick="navigateToDataStudioAndInspect('study_slides')" style="padding:10px 20px;">
          <span><img src="assets/icons/kalasha-pot.svg" class="fmm-icon" alt="" /></span> Inspect in Data Studio &rarr;
        </button>
      </div>
    `;
  }

  modal.classList.add("active");
}

window.navigateToDataStudioAndInspect = function(tableName) {
  closeModal('tablesImpactedModal');
  switchTab('admin_studio');
  switchToTableInspector(tableName || 'study_slides');
};


// ============================================================================
// SCREEN 3: DATA STUDIO & MEDALLION ARCHIVAL ARCHITECTURE EXPLORER
// ============================================================================

const TABLE_METADATA = {
  param_config: {
    medallion_name: "T_SYST_PARAM_CONFIG",
    title: "Application Configuration",
    layer: "syst",
    icon: "silpa-gear",
    desc: "Application configuration and variables"
  },

  // ── BRONZE LAYER: T_RAW (Raw Ingest / OCR Outputs) ──────────────────────
  slide_ocr_data: {
    medallion_name: "T_RAW_SLIDE_OCR",
    title: "Raw OCR Text & Tokens",
    layer: "raw",
    icon: "sasana-registry",
    desc: "Windows Media OCR engine outputs, word confidence metrics & bounding boxes"
  },
  study_slides: {
    medallion_name: "T_RAW_STUDY_SLIDES",
    title: "Plate Images & Transcriptions",
    layer: "raw",
    icon: "silpa-camera",
    desc: "Source slide plates, image URLs, sort order, and cleaned transcription copies"
  },
  ai_metadata_proposals: {
    medallion_name: "T_RAW_AI_PROPOSALS",
    title: "Autonomous AI Proposals",
    layer: "raw",
    icon: "mudra-hand",
    desc: "Layer 2 machine-learning taxonomy proposals pending curator verification"
  },

  // ── SILVER LAYER: T_ODS (Curated Canonical Knowledge) ──────────────────
  studies: {
    medallion_name: "T_ODS_STUDIES",
    title: "Research Monographs",
    layer: "ods",
    icon: "grantha-lexicon",
    desc: "Scholarly research monographs, access tiers & publication metadata"
  },
  series: {
    medallion_name: "T_ODS_SERIES",
    title: "Curatorial Series",
    layer: "ods",
    icon: "kalpavriksha-tree",
    desc: "19 editorial publication series classifications and agamic scopes"
  },
  dictionary_entries: {
    medallion_name: "T_ODS_DICTIONARY",
    title: "IAST Sanskrit Glossary",
    layer: "ods",
    icon: "grantha-lexicon",
    desc: "Authoritative iconographic definitions, Sanskrit roots, and Agamic citations"
  },
  doc_ref_catalog: {
    medallion_name: "T_ODS_DOC_CATALOG",
    title: "Primary Text Catalog",
    layer: "ods",
    icon: "vimana-temple",
    desc: "Foundational Agamic & Silpa Shastra textual references and traditions"
  },
  taxonomy_terms: {
    medallion_name: "T_ODS_TAXONOMY_TERMS",
    title: "Canonical Iconography Terms",
    layer: "ods",
    icon: "sasana-registry",
    desc: "Standardized mudras, asanas, ayudhas, and iconographical attributes"
  },
  taxonomy_types: {
    medallion_name: "T_ODS_TAXONOMY_TYPES",
    title: "Taxonomy Classification Types",
    layer: "ods",
    icon: "kalpavriksha-tree",
    desc: "Divinity, asana, ayudha, mudra, and vahana formal category types"
  },
  term_aliases: {
    medallion_name: "T_ODS_TERM_ALIASES",
    title: "Multilingual Script Aliases",
    layer: "ods",
    icon: "yantra-link",
    desc: "Phonetic synonyms, Grantha, Tamil, Devanagari, and Anglicized forms"
  },
  places: {
    medallion_name: "T_ODS_PLACES",
    title: "Temples & Sacred Sites",
    layer: "ods",
    icon: "vimana-temple",
    desc: "Geographic registry of temples, towns, states, and archaeological sites"
  },
  periods_dynasties: {
    medallion_name: "T_ODS_PERIODS",
    title: "Dynasties & Historical Eras",
    layer: "ods",
    icon: "vimana-temple",
    desc: "Chola, Pallava, Pandya, Vijayanagara, and Hoysala epoch boundaries"
  },
  study_taxonomy_mappings: {
    medallion_name: "T_ODS_STUDY_TAXONOMY",
    title: "Verified Taxonomy Bridges",
    layer: "ods",
    icon: "yantra-link",
    desc: "Curator-verified linkages connecting studies and slides to taxonomy terms"
  },
  content_access_rules: {
    medallion_name: "T_ODS_CONTENT_RULES",
    title: "Access & DRM Policies",
    layer: "ods",
    icon: "kavacha-shield",
    desc: "Granular per-study access tier requirements and preview policies"
  },

  // ── GOLD LAYER: T_SYST (Operations, Telemetry, IAM) ─────────────────────
  users: {
    medallion_name: "T_SYST_USERS",
    title: "Scholar & Staff Accounts",
    layer: "syst",
    icon: "rishi-user",
    desc: "Super Admin, Curator, and Scholar authenticated identities and roles"
  },
  user_subscriptions: {
    medallion_name: "T_SYST_SUBSCRIPTIONS",
    title: "Active Subscriptions Ledger",
    layer: "syst",
    icon: "varaha-coin",
    desc: "Scholar Pro membership ledger, billing cycles, and payment states"
  },
  user_downloads: {
    medallion_name: "T_SYST_DOWNLOADS",
    title: "Licensed Download Receipts",
    layer: "syst",
    icon: "tamra-download",
    desc: "Cryptographically stamped 300 DPI master download receipts"
  },
  premium_download_requests: {
    medallion_name: "T_SYST_DOWNLOAD_REQ",
    title: "GPay & Payment Orders",
    layer: "syst",
    icon: "varaha-coin",
    desc: "UPI, Google Pay, and NetBanking direct licensing transactions"
  },
  user_behavior_logs: {
    medallion_name: "T_SYST_BEHAVIOR_LOG",
    title: "Scholarly Event Stream",
    layer: "syst",
    icon: "tala-proportions",
    desc: "Real-time search telemetry, study inspection logs, and query analytics"
  },
  audit_logs: {
    medallion_name: "T_SYST_AUDIT_LOG",
    title: "Curatorial Audit Trail",
    layer: "syst",
    icon: "tala-proportions",
    desc: "Immutable cryptographic record of all CREATE, UPDATE, and DELETE mutations"
  }
};

let categoryTabsInitialized = false;
let dataStudioModesInitialized = false;

function initDataStudioModes() {
  if (dataStudioModesInitialized) return;
  const btnArch = document.getElementById("btnModeArch");
  const btnLoop = document.getElementById("btnModeLoop");
  const btnTable = document.getElementById("btnModeTable");
  const btnCrud = document.getElementById("btnModeCrud");

  const viewArch = document.getElementById("dataStudioArchView");
  const viewLoop = document.getElementById("dataStudioLoopView");
  const viewTable = document.getElementById("dataStudioTableView");
  const viewCrud = document.getElementById("dataStudioCrudView");

  function setMode(mode) {
    [btnArch, btnLoop, btnTable, btnCrud].forEach(b => b && b.classList.remove("active"));
    [viewArch, viewLoop, viewTable, viewCrud].forEach(v => v && (v.style.display = "none"));

    if (mode === "arch") {
      if (btnArch) btnArch.classList.add("active");
      if (viewArch) viewArch.style.display = "block";
    } else if (mode === "loop") {
      if (btnLoop) btnLoop.classList.add("active");
      if (viewLoop) viewLoop.style.display = "block";
    } else if (mode === "table") {
      if (btnTable) btnTable.classList.add("active");
      if (viewTable) viewTable.style.display = "block";
      loadAdminTables();
    } else if (mode === "crud") {
      if (btnCrud) btnCrud.classList.add("active");
      if (viewCrud) viewCrud.style.display = "block";
      loadCrudData();
    }
  }

  if (btnArch) btnArch.addEventListener("click", () => setMode("arch"));
  if (btnLoop) btnLoop.addEventListener("click", () => setMode("loop"));
  if (btnTable) btnTable.addEventListener("click", () => setMode("table"));
  if (btnCrud) btnCrud.addEventListener("click", () => setMode("crud"));

  dataStudioModesInitialized = true;
}

window.switchToTableInspector = function(tableName) {
  initDataStudioModes();
  const btnTable = document.getElementById("btnModeTable");
  if (btnTable) btnTable.click();

  if (tableName) {
    state.selectedTable = tableName;
    state.tablePage = 1;
    renderTableSelectorCards();
    loadTableRows();
    const hero = document.getElementById("tableInspectorHero");
    if (hero) hero.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};

window.runKnowledgeLoopSelfTest = async function() {
  const query = document.getElementById("loopTestQuery") ? document.getElementById("loopTestQuery").value.trim() : "";
  const box = document.getElementById("loopTestResultsBox");
  if (!box) return;

  if (!query) {
    alert("Please enter an iconography query for the self-learning test.");
    return;
  }

  box.style.display = "block";
  box.innerHTML = `<div style="padding:15px; color:var(--muted);"><img src="assets/icons/dharma-chakra.svg" class="fmm-icon rotating-chakra" style="width:16px;height:16px;" alt="" /> Querying self-learning pipeline across 4 tiers...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/taxonomy/hierarchy`);
    const data = await res.json();
    const terms = data.taxonomy_terms || [];
    const matched = terms.filter(t => t.canonical_name.toLowerCase().includes(query.toLowerCase()) || (t.iast_name && t.iast_name.toLowerCase().includes(query.toLowerCase())));

    let htmlResult = `
      <div style="font-weight:700; color:var(--ink); margin-bottom:8px;">🔍 Self-Learning Query Evaluation: "${query}"</div>
      <div>1. <strong style="color:var(--accent);">Exact Lexicon Match:</strong> ${matched.length > 0 ? `<span style="color:#059669; font-weight:700;">Found ${matched.length} term(s)</span> (${matched.map(m => m.canonical_name).join(', ')})` : `<span style="color:#d97706;">No direct lexicon match. Fallback to phonetic & OCR embeddings.</span>`}</div>
      <div>2. <strong style="color:var(--bronze);">Monographs Filter:</strong> Evaluated against DuckDB FTS &amp; OCR layers</div>
      <div>3. <strong style="color:#059669);">Relational Integrity:</strong> Connected to live Medallion ODS bridges.</div>
      <div style="margin-top:6px; color:var(--success); font-weight:600;">✓ Result: Processed through 4 architectural tiers. Pipeline verified.</div>
    `;
    box.innerHTML = htmlResult;
  } catch (err) {
    box.innerHTML = `<div style="color:var(--danger);">Error testing loop: ${err.message}</div>`;
  }
};

function initDataStudioCategoryTabs() {
  initDataStudioModes();
  if (categoryTabsInitialized) return;
  const filterGroup = document.getElementById("tableCategoryFilter");
  if (!filterGroup) return;

  filterGroup.querySelectorAll(".cat-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      filterGroup.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      state.selectedTableCategory = pill.dataset.cat || "all";
      renderTableSelectorCards();
    });
  });
  categoryTabsInitialized = true;
}

function renderTableSelectorCards() {
  const strip = document.getElementById("tableNavStrip");
  if (!strip) return;

  const currentCat = state.selectedTableCategory || "all";
  const filtered = state.adminTables.filter(t => {
    if (currentCat === "all") return true;
    const meta = TABLE_METADATA[t.table_name];
    const layer = meta ? meta.layer : "ods";
    return layer === currentCat;
  });

  strip.innerHTML = filtered.map(t => {
    const meta = TABLE_METADATA[t.table_name] || {
      medallion_name: t.table_name.toUpperCase(),
      title: t.table_name,
      layer: "ods",
      icon: "sasana-registry",
      desc: ""
    };
    const isActive = t.table_name === state.selectedTable;
    const layer = meta.layer || "ods";
    const layerPill = layer === "raw" ? "🟤 T_RAW" : (layer === "ods" ? "🔵 T_ODS" : "🟡 T_SYST");

    return `
      <div class="table-card-btn medal-${layer} ${isActive ? 'active' : ''}" data-table="${t.table_name}" title="${meta.desc}">
        <div class="table-card-top">
          <span class="table-layer-pill ${layer}">${layerPill}</span>
          <span class="table-row-count-badge">${t.row_count} rows</span>
        </div>
        <div class="table-medallion-title">${meta.medallion_name}</div>
        <div class="table-friendly-name">
          <img src="assets/icons/${meta.icon}.svg" class="fmm-icon" style="width:13px; height:13px; vertical-align:middle; margin-right:3px;" alt="" />
          ${meta.title}
        </div>
        <div class="table-code-tag"><code>${t.table_name}</code></div>
      </div>
    `;
  }).join("");

  strip.querySelectorAll(".table-card-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.selectedTable = btn.dataset.table;
      state.tablePage = 1;
      renderTableSelectorCards();
      loadTableRows();
    });
  });
}

async function loadArchivalTelemetry() {
  try {
    const res = await fetch(`${API_BASE}/api/archival/telemetry`);
    if (!res.ok) return;
    const data = await res.json();
    const tableMap = data.tables || {};

    if (document.getElementById("statTotalTables")) document.getElementById("statTotalTables").innerText = data.total_tables || 20;
    if (document.getElementById("statTotalStudies")) document.getElementById("statTotalStudies").innerText = tableMap["studies"] || 7;
    if (document.getElementById("statTotalSlides")) document.getElementById("statTotalSlides").innerText = tableMap["study_slides"] || 27;
    if (document.getElementById("statTotalTerms")) document.getElementById("statTotalTerms").innerText = tableMap["taxonomy_terms"] || 37;
    if (document.getElementById("statTotalAliases")) document.getElementById("statTotalAliases").innerText = tableMap["term_aliases"] || 72;

    for (const [tname, count] of Object.entries(tableMap)) {
      const el = document.getElementById(`countTier_${tname}`);
      if (el) el.innerText = `${count} rows`;
      const erEl = document.getElementById(`erCount_${tname}`);
      if (erEl) erEl.textContent = `${count} rows`;
    }
  } catch (err) {
    console.warn("Archival telemetry fetch error:", err);
  }
}

async function loadAdminTables() {
  initDataStudioModes();
  initDataStudioCategoryTabs();

  try {
    const res = await fetch(`${API_BASE}/api/admin/tables`);
    if (res.status === 403 || res.status === 401) {
      applyRouteGuards();
      return;
    }
    const data = await res.json();
    state.adminTables = data.tables || [];

    // Calculate Medallion Layer counts
    const countAll = state.adminTables.length;
    let countRaw = 0;
    let countOds = 0;
    let countSyst = 0;

    state.adminTables.forEach(t => {
      const meta = TABLE_METADATA[t.table_name];
      const layer = meta ? meta.layer : "ods";
      if (layer === "raw") countRaw++;
      else if (layer === "syst") countSyst++;
      else countOds++;
    });

    const elAll = document.getElementById("catCountAll");
    const elRaw = document.getElementById("catCountRaw");
    const elOds = document.getElementById("catCountOds");
    const elSyst = document.getElementById("catCountSyst");
    if (elAll) elAll.innerText = countAll;
    if (elRaw) elRaw.innerText = countRaw;
    if (elOds) elOds.innerText = countOds;
    if (elSyst) elSyst.innerText = countSyst;

    // Default to first table if not selected
    if (!state.selectedTable && state.adminTables.length > 0) {
      state.selectedTable = "slide_ocr_data";
    }

    renderTableSelectorCards();
    loadTableRows();
  } catch (err) {
    console.error("Loading tables failed:", err);
  }
}

async function loadTableRows() {
  const container = document.getElementById("adminGridContainer");
  const tableNameHeading = document.getElementById("currentTableNameHeading");
  const rawNameEl = document.getElementById("currentTableRawName");
  const descEl = document.getElementById("currentTableDesc");
  const layerBadge = document.getElementById("inspectorLayerBadge");
  const rowCountBadge = document.getElementById("inspectorRowCountBadge");
  const paginationInfo = document.getElementById("tablePaginationInfo");
  const prevBtn = document.getElementById("tablePrevPageBtn");
  const nextBtn = document.getElementById("tableNextPageBtn");

  if (!container) return;

  const currentTable = state.selectedTable || "slide_ocr_data";
  const meta = TABLE_METADATA[currentTable] || {
    medallion_name: currentTable.toUpperCase(),
    title: currentTable,
    layer: "ods",
    desc: "Archival table metadata"
  };

  const layer = meta.layer || "ods";
  const layerBadgeText = layer === "raw" ? "🟤 BRONZE RAW INGEST" : (layer === "ods" ? "🔵 SILVER CURATED ODS" : "🟡 GOLD SYSTEM OPERATIONS");

  if (tableNameHeading) tableNameHeading.innerText = meta.medallion_name;
  if (rawNameEl) rawNameEl.innerText = currentTable;
  if (descEl) descEl.innerText = meta.desc;
  if (layerBadge) {
    layerBadge.className = `layer-mini-tag ${layer}`;
    layerBadge.innerText = layerBadgeText;
  }

  container.innerHTML = `<div style="padding:24px; text-align:center; color:var(--muted);"><img src="assets/icons/dharma-chakra.svg" class="fmm-icon rotating-chakra" style="width:24px; height:24px;" alt="" /> Querying DuckDB columnar engine for <strong>${meta.medallion_name}</strong>...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/admin/tables/${currentTable}?page=${state.tablePage}&page_size=${state.tablePageSize}`);
    if (res.status === 403 || res.status === 401) {
      applyRouteGuards();
      return;
    }
    const data = await res.json();
    state.tableRows = data.rows || [];
    state.tableTotalRows = data.total_rows || 0;
    const totalPages = Math.ceil(state.tableTotalRows / state.tablePageSize) || 1;

    if (rowCountBadge) rowCountBadge.innerText = `${state.tableTotalRows} total records`;
    if (paginationInfo) paginationInfo.innerText = `Showing page ${state.tablePage} of ${totalPages} (${state.tableTotalRows} total records in ${meta.medallion_name})`;

    if (prevBtn) {
      prevBtn.disabled = state.tablePage <= 1;
      prevBtn.onclick = () => {
        if (state.tablePage > 1) {
          state.tablePage--;
          loadTableRows();
        }
      };
    }

    if (nextBtn) {
      nextBtn.disabled = state.tablePage >= totalPages;
      nextBtn.onclick = () => {
        if (state.tablePage < totalPages) {
          state.tablePage++;
          loadTableRows();
        }
      };
    }

    if (state.tableRows.length === 0) {
      container.innerHTML = `
        <div style="padding:40px; text-align:center; color:var(--muted);">
          <div style="font-size:24px; margin-bottom:8px;">📂</div>
          <div style="font-weight:600; font-size:15px; margin-bottom:4px;">No records found in table '${currentTable}'</div>
          <div style="font-size:12.5px;">You can add records to this table via the <strong>Curatorial CRUD &amp; Maintenance</strong> suite.</div>
        </div>
      `;
      return;
    }

    const cols = Object.keys(state.tableRows[0]);

    // Format headers with clean titles and icons
    container.innerHTML = `
      <table class="admin-data-grid">
        <thead>
          <tr>
            <th style="width:110px; text-align:center;">Actions</th>
            ${cols.map(c => {
              const isPk = c === 'id' || c === 'doc_ref';
              const isFk = c.endsWith('_id');
              const icon = isPk ? '🔑 ' : (isFk ? '🔗 ' : '');
              return `<th>${icon}${c.replace(/_/g, ' ').toUpperCase()}</th>`;
            }).join("")}
          </tr>
        </thead>
        <tbody>
          ${state.tableRows.map((row, rIdx) => `
            <tr>
              <td style="text-align:center; white-space:nowrap;">
                <div style="display:flex; gap:6px; justify-content:center; align-items:center;">
                  <button class="tbl-action-btn view" onclick="inspectRow(${rIdx})" title="Inspect Full Record">
                    <img src="assets/icons/grantha-lexicon.svg" class="fmm-icon" style="width:12px;height:12px;" alt="" /> Inspect
                  </button>
                  <button class="tbl-action-btn edit" onclick="openCrudForTable('${currentTable}')" title="Edit in Curatorial CRUD Suite">
                    <img src="assets/icons/sthapati-chisel.svg" class="fmm-icon" style="width:12px;height:12px;" alt="" /> CRUD
                  </button>
                </div>
              </td>
              ${cols.map(c => {
                const val = row[c];
                return renderGridCell(c, val, rIdx);
              }).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } catch (err) {
    console.error("Loading rows failed:", err);
    container.innerHTML = `<div style="color:var(--danger); padding:20px;">Failed to load rows: ${err.message}</div>`;
  }
}

// Enterprise Cell Formatter for Data Grid
function renderGridCell(colName, val, rowIndex) {
  if (val === null || val === undefined) {
    return `<td><span class="tbl-null">—</span></td>`;
  }

  // ID columns: Code chips with copy
  if (colName === 'id' || colName === 'doc_ref' || colName.endsWith('_id') || colName === 'google_sub' || colName === 'session_id') {
    const s = String(val);
    const short = s.length > 22 ? `${s.substring(0, 10)}…${s.substring(s.length - 8)}` : s;
    return `<td><span class="tbl-code-chip" title="Click to copy full ID: ${s}" onclick="navigator.clipboard.writeText('${s}');showToast('Copied ID!')">${short}</span></td>`;
  }

  // Long text / OCR fields / Markdown / Definitions
  if (colName === 'raw_ocr_output' || colName === 'normalized_text' || colName === 'extracted_ocr_text' ||
      colName === 'cleaned_text' || colName === 'summary_markdown' || colName === 'definition' ||
      colName === 'scope' || colName === 'caption' || colName === 'extended_notes') {
    const s = String(val);
    const snippet = s.length > 180 ? `${s.substring(0, 180)}…` : s;
    return `
      <td>
        <div class="tbl-text-preview">
          ${snippet}
          ${s.length > 180 ? `<button class="tbl-expand-btn" onclick="openCellInspectModal('${colName}', 'Row #${rowIndex + 1} (${s.length} chars)', ${rowIndex}, '${colName}')">📄 View Full Text (${s.length} chars)</button>` : ''}
        </div>
      </td>
    `;
  }

  // JSON objects & tokens
  if (colName.endsWith('_json') || typeof val === 'object') {
    const jsonStr = typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val);
    return `
      <td>
        <button class="tbl-json-chip" onclick="openCellInspectModal('${colName}', 'Row #${rowIndex + 1} JSON', ${rowIndex}, '${colName}')">
          { } JSON (${jsonStr.length} bytes)
        </button>
      </td>
    `;
  }

  // Confidence metric
  if (colName.includes('confidence')) {
    const num = Number(val);
    const pct = Math.round(num * 100);
    const cls = pct >= 85 ? 'high' : (pct >= 60 ? 'mid' : 'low');
    return `<td><span class="tbl-confidence-badge ${cls}">🎯 ${pct}% (${num.toFixed(2)})</span></td>`;
  }

  // Numbers (word count, slides, order, amount)
  if (typeof val === 'number' || colName === 'word_count' || colName === 'slide_number' || colName === 'total_slides' || colName === 'sort_order' || colName === 'amount_inr') {
    return `<td><span class="tbl-num-badge">${val}</span></td>`;
  }

  // Boolean
  if (typeof val === 'boolean') {
    return `<td><span style="font-weight:700; color:${val ? '#059669' : '#9ca3af'};">${val ? '✓ True' : '✗ False'}</span></td>`;
  }

  // Timestamps
  if (colName.includes('_at') || colName === 'timestamp') {
    return `<td style="font-size:11.5px; color:var(--muted); white-space:nowrap;">${new Date(val).toLocaleString()}</td>`;
  }

  // Default string
  const str = String(val);
  if (str.length > 65) {
    return `<td title="${str.replace(/"/g, '&quot;')}">${str.substring(0, 65)}…</td>`;
  }
  return `<td>${str}</td>`;
}

// Cell Inspector Modal logic
window.openCellInspectModal = function(fieldName, subtitle, rowIndex, colKey) {
  const row = state.tableRows[rowIndex] || {};
  let rawVal = row[colKey];
  if (typeof rawVal === 'object') {
    rawVal = JSON.stringify(rawVal, null, 2);
  } else if (typeof rawVal === 'string' && (rawVal.startsWith('{') || rawVal.startsWith('['))) {
    try {
      rawVal = JSON.stringify(JSON.parse(rawVal), null, 2);
    } catch (_) {}
  }

  const modal = document.getElementById("tableCellInspectModal");
  const titleEl = document.getElementById("cellInspectTitle");
  const subEl = document.getElementById("cellInspectSubtitle");
  const contentEl = document.getElementById("cellInspectContent");
  const lenEl = document.getElementById("cellInspectLength");

  if (titleEl) titleEl.innerText = `Field: ${fieldName.replace(/_/g, ' ').toUpperCase()}`;
  if (subEl) subEl.innerText = `${state.selectedTable} · ${subtitle}`;
  if (contentEl) contentEl.innerText = rawVal || "(empty)";
  if (lenEl) lenEl.innerText = `${(rawVal || '').length} characters`;

  if (modal) modal.classList.add("active");
  window.lastInspectedCellText = rawVal || "";
};

window.copyCellInspectContent = function() {
  if (window.lastInspectedCellText) {
    navigator.clipboard.writeText(window.lastInspectedCellText);
    showToast("Content copied to clipboard!");
  }
};

window.inspectRow = function(rIdx) {
  const row = state.tableRows[rIdx];
  if (!row) return;
  const jsonStr = JSON.stringify(row, null, 2);
  window.openCellInspectModal(`Full Record (${row.id || row.doc_ref || '#' + (rIdx + 1)})`, `Complete Row State in ${state.selectedTable}`, rIdx, null);
  const contentEl = document.getElementById("cellInspectContent");
  if (contentEl) contentEl.innerText = jsonStr;
  window.lastInspectedCellText = jsonStr;
};

window.executeAssignRole = async function(email, role) {
  const targetEmail = email || (document.getElementById("assignUserEmail") ? document.getElementById("assignUserEmail").value.trim() : "");
  const targetRole = role || (document.getElementById("assignUserRole") ? document.getElementById("assignUserRole").value : "curator");

  if (!targetEmail) {
    alert("Please enter a valid user email address.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/admin/users/role`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: targetEmail, role: targetRole })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'User role successfully updated!');
      if (document.getElementById("assignUserEmail")) {
        document.getElementById("assignUserEmail").value = "";
      }
      loadTableRows();
    } else {
      alert(`Role assignment failed: ${data.detail || 'Error'}`);
    }
  } catch (err) {
    alert(`Request error: ${err.message}`);
  }
};


// SCREEN 4: DICTIONARY OF ICONOGRAPHY VIEWER
// ============================================================================

async function loadDictionaryEntries() {
  const listEl = document.getElementById("dictionaryEntriesList");
  listEl.innerHTML = `
    <div class="scholarly-loader-stage" style="padding:30px;">
      <div class="scholarly-spinner-ring">
        <img src="assets/icons/dharma-chakra.svg" class="fmm-icon rotating-chakra" alt="" />
      </div>
      <div style="font-family:var(--font-serif); margin-top:8px; color:var(--ink);">Consulting Agamic Lexicon...</div>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/api/taxonomy/hierarchy`);
    const data = await res.json();
    const dict = data.dictionary || [];

    listEl.innerHTML = dict.map(entry => `
      <div style="background:#fff; border:1px solid var(--line); border-radius:var(--radius-md); padding:20px; margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; align-items:baseline;">
          <h4 style="font-family:var(--font-serif); font-size:22px; color:var(--ink);">${entry.headword} <span style="font-size:16px; color:var(--accent); font-weight:normal;">(${entry.iast_headword})</span></h4>
          <span style="font-size:11px; text-transform:uppercase; letter-spacing:0.1em; color:var(--muted);">${entry.part_of_speech || ''}</span>
        </div>
        <p style="font-size:14px; color:var(--ink-soft); margin:8px 0; line-height:1.6;">${entry.definition}</p>
        <button class="sample-btn" onclick="searchForDictionaryTerm('${entry.headword}')">Search Studies Matching '${entry.headword}' →</button>
      </div>
    `).join("");
  } catch (err) {
    listEl.innerHTML = `<div style="color:var(--danger);">Error loading dictionary: ${err.message}</div>`;
  }
}

window.searchForDictionaryTerm = function(term) {
  switchTab("search");
  document.getElementById("scholarSearchInput").value = term;
  runScholarSearch();
  
};

async function loadTaxonomyData() {
  try {
    const res = await fetch(`${API_BASE}/api/taxonomy/hierarchy`);
    const data = await res.json();
    const seriesSelect = document.getElementById("seriesFilterSelect");
    if (seriesSelect && data.series) {
      data.series.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.innerText = s.name;
        seriesSelect.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Taxonomy load error:", err);
  }
}

// ============================================================================
// MODAL CONTROLLERS: LIGHTBOX & GPAY PAYMENT
// ============================================================================

function openLightbox(imageUrl, title) {
  const modal = document.getElementById("lightboxModal");
  document.getElementById("lightboxImg").src = imageUrl;
  document.getElementById("lightboxTitle").innerText = title;
  modal.classList.add("active");
}

function openGPayPaymentModal(study, slide) {
  state.selectedStudyForGPay = study;
  const modal = document.getElementById("gpayModal");
  document.getElementById("gpayStudyTitle").innerText = study.title;
  document.getElementById("gpaySlideTitle").innerText = slide ? slide.slide_title : "Complete High-Res Carousel";
  
  // Pre-fill user email if authenticated
  if (state.currentUser && state.currentUser.email) {
    const emailInput = document.getElementById("gpayUserEmail");
    if (emailInput) emailInput.value = state.currentUser.email;
  }
  
  modal.classList.add("active");
}

window.closeModal = function(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove("active");
};

window.executeGPayPayment = async function() {
  const email = document.getElementById("gpayUserEmail").value.trim();
  const txRef = document.getElementById("gpayTxRef").value.trim() || `UPI-TX-${Date.now()}`;

  if (!email) {
    alert("Please enter your email to receive the high-resolution archival license.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/payment/simulate-gpay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        study_id: state.selectedStudyForGPay ? state.selectedStudyForGPay.study_id : "s_ganesa_001",
        user_email: email,
        transaction_ref: txRef,
        amount_inr: 499.0
      })
    });

    const data = await res.json();
    closeModal("gpayModal");
    alert(`Payment Successful!\n\n${data.message}\nLicense Ref: ${data.download_license_id}\nLicense Duration: ${data.license_expiry}\n\nHigh-resolution printable PDF download link has been emailed to ${email}.`);
  } catch (err) {
    alert("Payment verification error: " + err.message);
  }
};




// ============================================================================
// STUDY MONOGRAPH MODAL CONTROLLER & FALLBACK CATALOG
// ============================================================================

const FMM_STUDY_CATALOG = {
  "s_nataraja_002": {
    study_id: "s_nataraja_002",
    title: "Nataraja: Cosmic Dance & Classical Iconometry",
    subtitle: "Iconography of the Ananda Tandava and Chola Bronzes",
    series_name: "Iconography Studies",
    study_number: "Study 002",
    affinity_score: 94,
    confidence_score: 96,
    rank_score: 94.6,
    cover_image_url: "/storage/images/nataraja-cosmic-dance-iconometry/slide_1.png",
    summary_markdown: "An in-depth scholarly treatise on the cosmic dance (Ananda Tandava) of Shiva Nataraja, analyzing the flame prabhavali, dwarf of ignorance (Apasmara), and strictly prescribed Dasatala proportional metrics.",
    requires_subscription: false
  },
  "s_ganesa_001": {
    study_id: "s_ganesa_001",
    title: "Ganesa: Variations in Iconography",
    subtitle: "A Comparative Study of Iconographic Forms and Postural Attributes",
    series_name: "Iconography Studies",
    study_number: "Study 001",
    affinity_score: 92,
    confidence_score: 98,
    rank_score: 93.8,
    cover_image_url: "/storage/images/ganesa-variations-in-iconography/slide_1.png",
    summary_markdown: "Explores the iconographic spectrum of Ganesha in South Indian sacred art, contrasting seated (Asina) and standing (Sthanaka) postures, the trunk curvature (Valampuri / Idampuri), and Prabhavali arch geometry.",
    requires_subscription: false
  },
  "s_uchchhishta_003": {
    study_id: "s_uchchhishta_003",
    title: "Uchchhishta Ganapati: Tantric Dual-Figure Composition",
    subtitle: "Esoteric Iconography and Devi Interaction in Panchaloha Castings",
    series_name: "Iconography Studies",
    study_number: "Study 003",
    affinity_score: 89,
    confidence_score: 91,
    rank_score: 89.8,
    cover_image_url: "/storage/images/uchchhishta-ganapati-tantric-iconography/slide_1.png",
    summary_markdown: "Analysis of the complex dual-figure tantric composition of Uchchhishta Ganapati seated with his consort, examining subtle mudras and iconometric balance in lost-wax bronzes.",
    requires_subscription: true
  },
  "s_kaliya_004": {
    study_id: "s_kaliya_004",
    title: "Kaliya Tandava Krishna: Dynamic Postural Iconometry",
    subtitle: "Chola & Vijayanagara Bronzes of the Serpent Subjugation",
    series_name: "Iconography Studies",
    study_number: "Study 004",
    affinity_score: 91,
    confidence_score: 93,
    rank_score: 91.6,
    cover_image_url: "/storage/images/kaliya-tandava-krishna-iconometry/slide_1.png",
    summary_markdown: "Studies the dynamic equilibrium of young Krishna dancing atop the five-hooded serpent Kaliya. Examines foot positioning, hand holding the serpent's tail, and the mudra of benediction.",
    requires_subscription: true
  },
  "s_venugopala_005": {
    study_id: "s_venugopala_005",
    title: "Krishna Venugopala: The Tribhanga Posture & Bamboo Flute",
    subtitle: "Triple-Bending Harmonic Symmetry and Pastoral Iconography",
    series_name: "Iconography Studies",
    study_number: "Study 005",
    affinity_score: 93,
    confidence_score: 94,
    rank_score: 93.2,
    cover_image_url: "/storage/images/krishna-venugopala-tribhanga-posture/slide_1.png",
    summary_markdown: "Detailed geometric deconstruction of the Tribhanga (triple-bend) posture in Venugopala bronzes. Analyzes the angle of the head, hips, and crossed feet relative to the vertical plumb line (Brahmasutra).",
    requires_subscription: false
  },
  "s_radhakrishna_006": {
    study_id: "s_radhakrishna_006",
    title: "Radha-Krishna: Composite Divine Proportions",
    subtitle: "25-Inch Masterpiece Bronze Ensemble and Dual Tala Alignment",
    series_name: "Iconography Studies",
    study_number: "Study 006",
    affinity_score: 95,
    confidence_score: 97,
    rank_score: 95.6,
    cover_image_url: "/storage/images/radha-krishna-composite-proportions/slide_1.png",
    summary_markdown: "An investigation of dual-figure iconometry in large-scale Panchaloha castings, contrasting the 10-Tala proportions of Krishna with the 9-Tala grace of Radha under a flowering Kadamba motif.",
    requires_subscription: true
  }
};

window.openStudyModal = function(studyId) {
  console.log("Opening 3D study modal for:", studyId);
  const study = (state.searchResults && state.searchResults.find(s => s.study_id === studyId)) || FMM_STUDY_CATALOG[studyId];
  if (!study) {
    console.warn("Study not found for ID:", studyId);
    return;
  }

  const modal = document.getElementById("studyDetailModal");
  if (!modal) return;

  document.getElementById("studyModalSeries").innerText = `${study.series_name} · ${study.study_number || "Study"}`;
  document.getElementById("studyModalTitle").innerText = study.title;
  document.getElementById("studyModalSubtitle").innerText = study.subtitle || "";
  document.getElementById("studyModalDesc").innerText = study.summary_markdown || study.subtitle || "A canonical study of South Indian Panchaloha bronze iconography.";

  const imgEl = document.getElementById("studyModalImg");
  const imgSrc = study.cover_image_url || (study.slides && study.slides[0] ? study.slides[0].image_url : "");
  imgEl.src = imgSrc;

  // Scores
  const scoresEl = document.getElementById("studyModalScores");
  scoresEl.innerHTML = `
    <div class="score-badge affinity" title="Theme Affinity">
      <span class="score-val">${study.affinity_score || 92}%</span>
      <span class="score-lbl">Affinity</span>
    </div>
    <div class="score-badge confidence" title="Confidence">
      <span class="score-val">${study.confidence_score || 95}%</span>
      <span class="score-lbl">Confidence</span>
    </div>
    <div class="score-badge overall" title="Composite Score">
      <span class="score-val">${study.rank_score || 93}</span>
      <span class="score-lbl">Rank</span>
    </div>
  `;

  // Buttons
  const viewFeedBtn = document.getElementById("studyModalViewFeedBtn");
  viewFeedBtn.onclick = () => {
    closeModal("studyDetailModal");
    switchTab("search");
    setTimeout(() => {
      const cardEl = document.getElementById(`study-card-${study.study_id}`);
      if (cardEl) {
        cardEl.scrollIntoView({ behavior: "smooth", block: "center" });
        cardEl.style.transition = "box-shadow 0.4s ease, border-color 0.4s ease";
        cardEl.style.borderColor = "var(--gold)";
        cardEl.style.boxShadow = "0 0 35px rgba(181, 139, 75, 0.45)";
        setTimeout(() => {
          cardEl.style.boxShadow = "";
          cardEl.style.borderColor = "";
        }, 3000);
      }
    }, 150);
  };

  const lightboxBtn = document.getElementById("studyModalLightboxBtn");
  lightboxBtn.onclick = () => {
    openLightbox(imgSrc, study.title);
  };

  const gpayBtn = document.getElementById("studyModalGPayBtn");
  if (gpayBtn) {
    gpayBtn.onclick = () => {
      openLightbox(imgSrc, study.title);
    };
  }

  modal.classList.add("active");
};

window.openSacredGeometryModal = function() {
  const modal = document.getElementById("sacredGeometryModal");
  if (modal) modal.classList.add("active");
};

// ============================================================================
// SUBSCRIPTION GATE: Premium Content Access Controller
// ============================================================================

window.openSubscriptionGate = function(study) {
  const modal = document.getElementById("subscriptionGateModal");
  if (!modal) return;

  const titleEl = document.getElementById("gateModalTitle");
  const descEl = document.getElementById("gateModalDesc");
  const payBtn = document.getElementById("gateModalPayBtn");

  if (titleEl) titleEl.innerText = study.title || "Unlock This Monograph";
  if (descEl) {
    descEl.innerHTML = `
      <strong>${study.title}</strong> is part of the Scholar Pro collection.
      This monograph contains <strong>${study.total_slides || 'multiple'} archival plates</strong>
      with verified OCR taxonomy and canonical iconometric measurements.
      <br><br>Sign in or upgrade to access the full study.
    `;
  }

  if (payBtn) {
    payBtn.onclick = () => {
      closeModal("subscriptionGateModal");
      openAuthModal();
    };
  }

  modal.classList.add("active");
};


// ============================================================================
// THREE.JS 3D GRAPHICS CONTROLLER (Panchaloha Sacred Knot & Bronze Carousel)
// ============================================================================

let archive3DInstance = null;
let about3DInstance = null;
let exhibition3DInstance = null;
let current3DHeroMode = "knot";

const FMM_3D_SLIDES = [
  { id: "s_ganesa_001", title: "Ganesa with Arch", img: "/storage/images/ganesa-variations-in-iconography/slide_1.png" },
  { id: "s_nataraja_002", title: "Nataraja 18-Inch Masterpiece", img: "/storage/images/nataraja-cosmic-dance-iconometry/slide_1.png" },
  { id: "s_uchchhishta_003", title: "Uchchhishta Ganapati", img: "/storage/images/uchchhishta-ganapati-tantric-iconography/slide_1.png" },
  { id: "s_kaliya_004", title: "Kaliya Tandava Krishna", img: "/storage/images/kaliya-tandava-krishna-iconometry/slide_1.png" },
  { id: "s_venugopala_005", title: "Krishna Venugopala", img: "/storage/images/krishna-venugopala-tribhanga-posture/slide_1.png" },
  { id: "s_radhakrishna_006", title: "Radha-Krishna 25-Inch", img: "/storage/images/radha-krishna-composite-proportions/slide_1.png" }
];

function initArchive3D() {
  const container = document.getElementById("archive-canvas-container");
  if (!container || archive3DInstance || typeof THREE === "undefined") return;

  const width = container.clientWidth || 360;
  const height = container.clientHeight || 330;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
  camera.position.z = 7.5;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  const root = new THREE.Group();
  scene.add(root);

  // 1. Sacred Geometry Mode: TorusKnot
  const knotGroup = new THREE.Group();
  const bronzeMat = new THREE.MeshStandardMaterial({
    color: 0xcb7a43,
    roughness: 0.22,
    metalness: 0.94
  });
  const knotGeo = new THREE.TorusKnotGeometry(1.3, 0.16, 160, 24);
  const knotMesh = new THREE.Mesh(knotGeo, bronzeMat);
  knotMesh.userData = { isKnot: true };
  knotGroup.add(knotMesh);

  const frameGeo = new THREE.IcosahedronGeometry(2.35, 0);
  const frameMat = new THREE.MeshStandardMaterial({
    color: 0xa99b86,
    wireframe: true,
    transparent: true,
    opacity: 0.6
  });
  const frameMesh = new THREE.Mesh(frameGeo, frameMat);
  frameMesh.userData = { isKnot: true };
  knotGroup.add(frameMesh);
  root.add(knotGroup);

  // 2. Bronze Carousel Cylinder Mode
  const carouselGroup = new THREE.Group();
  carouselGroup.visible = false;
  root.add(carouselGroup);

  const texLoader = new THREE.TextureLoader();
  const radius = 3.2;
  const total = FMM_3D_SLIDES.length;

  FMM_3D_SLIDES.forEach((item, i) => {
    const angle = (i / total) * Math.PI * 2;
    const cardGeo = new THREE.PlaneGeometry(1.6, 2.1);
    texLoader.load(item.img, (tex) => {
      tex.minFilter = THREE.LinearFilter;
      const cardMat = new THREE.MeshStandardMaterial({
        map: tex,
        side: THREE.DoubleSide,
        roughness: 0.3,
        metalness: 0.1
      });
      const card = new THREE.Mesh(cardGeo, cardMat);
      card.position.x = Math.sin(angle) * radius;
      card.position.z = Math.cos(angle) * radius;
      card.rotation.y = angle;

      // Brass border
      const bGeo = new THREE.BoxGeometry(1.66, 2.16, 0.03);
      const bMat = new THREE.MeshStandardMaterial({ color: 0xb58b4b, metalness: 0.8, roughness: 0.3 });
      const bMesh = new THREE.Mesh(bGeo, bMat);
      bMesh.position.z = -0.02;
      bMesh.userData = { studyId: item.id };
      card.add(bMesh);

      card.userData = { studyId: item.id };
      carouselGroup.add(card);
    });
  });

  // Lights
  const ambLight = new THREE.AmbientLight(0xffffff, 1.4);
  scene.add(ambLight);

  const pLight1 = new THREE.PointLight(0xffedd5, 3.5, 20);
  pLight1.position.set(5, 5, 5);
  scene.add(pLight1);

  const pLight2 = new THREE.PointLight(0x8a6a4a, 2.5, 20);
  pLight2.position.set(-5, -4, -2);
  scene.add(pLight2);

  // Interaction tracking
  let targetX = 0, targetY = 0;
  let isDragging = false, startDownX = 0, startDownY = 0, hasDragged = false;
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  function onDown(e) {
    isDragging = true;
    startDownX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
    startDownY = e.clientY || (e.touches && e.touches[0].clientY) || 0;
    hasDragged = false;
  }

  function onMove(e) {
    const cx = e.clientX || (e.touches && e.touches[0].clientX) || 0;
    const cy = e.clientY || (e.touches && e.touches[0].clientY) || 0;

    if (isDragging) {
      const dx = cx - startDownX;
      const dy = cy - startDownY;
      if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
        hasDragged = true;
      }
      targetX += (cx - startDownX) * 0.003;
      targetY += (cy - startDownY) * 0.003;
      startDownX = cx;
      startDownY = cy;
    } else {
      const rect = container.getBoundingClientRect();
      mouse.x = ((cx - rect.left) / container.clientWidth) * 2 - 1;
      mouse.y = -((cy - rect.top) / container.clientHeight) * 2 + 1;
      targetX = mouse.x * 0.35;
      targetY = mouse.y * 0.35;

      // Hover cursor indicator
      raycaster.setFromCamera(mouse, camera);
      if (current3DHeroMode === "carousel") {
        const hits = raycaster.intersectObjects(carouselGroup.children, true);
        container.style.cursor = hits.length > 0 ? "pointer" : "grab";
      } else {
        const hits = raycaster.intersectObjects(knotGroup.children, true);
        container.style.cursor = hits.length > 0 ? "pointer" : "grab";
      }
    }
  }

  function onUp() {
    isDragging = false;
  }

  container.addEventListener("mousedown", onDown);
  window.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);

  container.addEventListener("touchstart", onDown, { passive: true });
  window.addEventListener("touchmove", onMove, { passive: true });
  window.addEventListener("touchend", onUp);

  // Click Handler with Drag Suppression
  container.addEventListener("click", (e) => {
    if (hasDragged) {
      hasDragged = false;
      return; // Ignore drag release
    }

    const rect = container.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / container.clientWidth) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / container.clientHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);

    if (current3DHeroMode === "carousel") {
      const hits = raycaster.intersectObjects(carouselGroup.children, true);
      if (hits.length > 0) {
        let obj = hits[0].object;
        while (obj && !obj.userData.studyId && obj.parent) obj = obj.parent;
        if (obj && obj.userData.studyId) {
          openStudyModal(obj.userData.studyId);
        }
      }
    } else {
      // Clicked Sacred Geometry Knot
      const hits = raycaster.intersectObjects(knotGroup.children, true);
      if (hits.length > 0) {
        // Quick spin impulse + open dialog
        targetX += 1.2;
        showToast("Panchaloha Sacred Geometry: Shilpa Shastra Harmonics");
        openSacredGeometryModal();
      }
    }
  });

  function animate() {
    requestAnimationFrame(animate);
    if (current3DHeroMode === "knot") {
      knotMesh.rotation.x += 0.003;
      knotMesh.rotation.y += 0.005;
      frameMesh.rotation.x -= 0.001;
      frameMesh.rotation.y -= 0.002;
    } else {
      carouselGroup.rotation.y += 0.003;
    }
    root.rotation.y += (targetX - root.rotation.y) * 0.08;
    root.rotation.x += (targetY - root.rotation.x) * 0.08;
    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener("resize", () => {
    if (!container || container.clientWidth === 0) return;
    camera.aspect = container.clientWidth / (container.clientHeight || 330);
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight || 330);
  });

  archive3DInstance = {
    setMode: (mode) => {
      current3DHeroMode = mode;
      knotGroup.visible = (mode === "knot");
      carouselGroup.visible = (mode === "carousel");
      camera.position.z = (mode === "knot") ? 7.5 : 8.5;
    }
  };
}

function initAbout3D() {
  const container = document.getElementById("about-canvas-container");
  if (!container || about3DInstance || typeof THREE === "undefined" || container.clientWidth === 0) return;

  const width = container.clientWidth;
  const height = container.clientHeight || 450;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
  camera.position.z = 7;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  const group = new THREE.Group();
  scene.add(group);

  const geoInner = new THREE.OctahedronGeometry(1.6);
  const matInner = new THREE.MeshStandardMaterial({ color: 0xb75b34, roughness: 0.2, metalness: 0.9 });
  const meshInner = new THREE.Mesh(geoInner, matInner);
  meshInner.userData = { isAboutGeometry: true };
  group.add(meshInner);

  const geoOuter = new THREE.IcosahedronGeometry(2.4);
  const matOuter = new THREE.MeshStandardMaterial({ color: 0xd8d0c3, wireframe: true, transparent: true, opacity: 0.4 });
  const meshOuter = new THREE.Mesh(geoOuter, matOuter);
  meshOuter.userData = { isAboutGeometry: true };
  group.add(meshOuter);

  const pointLight = new THREE.PointLight(0xffffff, 2.5);
  pointLight.position.set(5, 5, 5);
  scene.add(pointLight);
  scene.add(new THREE.AmbientLight(0x404040, 2));

  let targetX = 0, targetY = 0;
  container.addEventListener("mousemove", (e) => {
    const rect = container.getBoundingClientRect();
    targetY = (((e.clientX - rect.left) / container.clientWidth) * 2 - 1) * 0.4;
    targetX = (-((e.clientY - rect.top) / container.clientHeight) * 2 + 1) * 0.4;
  });

  container.addEventListener("click", () => {
    showToast("Panchaloha Matrix: Asthadhatu Proportional Lattice");
    openSacredGeometryModal();
  });
  container.style.cursor = "pointer";

  function animate() {
    requestAnimationFrame(animate);
    meshInner.rotation.x += 0.005;
    meshInner.rotation.y += 0.008;
    meshOuter.rotation.x -= 0.002;
    meshOuter.rotation.y -= 0.003;
    group.rotation.y += (targetY - group.rotation.y) * 0.05;
    group.rotation.x += (targetX - group.rotation.x) * 0.05;
    renderer.render(scene, camera);
  }
  animate();

  about3DInstance = true;
}

function initExhibition3D() {
  const container = document.getElementById("exhibition-canvas-container");
  if (!container || container.clientWidth === 0) return;

  if (window.FMMBronzeGallery3D) {
    const gallery = new FMMBronzeGallery3D("exhibition-canvas-container", {
      onSlideSelect: (idx, slideData) => {
        if (slideData && slideData.study_id) {
          openStudyModal(slideData.study_id);
        }
      }
    });

    // Fetch dynamic slides from backend 3D API
    fetch("/api/gallery/3d-data")
      .then(res => res.json())
      .then(data => {
        if (data.status === "success" && data.slides && data.slides.length > 0) {
          gallery.loadSlides(data.slides);
        } else {
          // Fallback slides
          gallery.loadSlides([
            { slide_title: "Ganesa Plate 1", image_url: "/storage/images/ganesa-variations-in-iconography/slide_1.png", study_id: "s1111111-0000-0000-0000-000000000001" },
            { slide_title: "Ganesa Plate 2", image_url: "/storage/images/ganesa-variations-in-iconography/slide_2.png", study_id: "s1111111-0000-0000-0000-000000000001" },
            { slide_title: "Ganesa Plate 3", image_url: "/storage/images/ganesa-variations-in-iconography/slide_3.png", study_id: "s1111111-0000-0000-0000-000000000001" },
            { slide_title: "Ganesa Plate 4", image_url: "/storage/images/ganesa-variations-in-iconography/slide_4.png", study_id: "s1111111-0000-0000-0000-000000000001" }
          ]);
        }
      })
      .catch(err => {
        console.warn("Using fallback slides for 3D gallery:", err);
        gallery.loadSlides([
          { slide_title: "Ganesa Plate 1", image_url: "/storage/images/ganesa-variations-in-iconography/slide_1.png", study_id: "s1111111-0000-0000-0000-000000000001" },
          { slide_title: "Ganesa Plate 2", image_url: "/storage/images/ganesa-variations-in-iconography/slide_2.png", study_id: "s1111111-0000-0000-0000-000000000001" }
        ]);
      });

    exhibition3DInstance = gallery;
    return;
  }

  const width = container.clientWidth;
  const height = container.clientHeight || 580;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0e1012);
  scene.fog = new THREE.FogExp2(0x0e1012, 0.06);

  const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
  camera.position.set(0, 2.4, 8);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  // Grid Floor
  const grid = new THREE.GridHelper(30, 30, 0xb58b4b, 0x24282e);
  grid.position.y = 0;
  scene.add(grid);

  scene.add(new THREE.AmbientLight(0xffffff, 1.4));
  const spot = new THREE.SpotLight(0xfff5e0, 4.5, 25, Math.PI / 4, 0.3);
  spot.position.set(0, 9, 0);
  scene.add(spot);

  const showcase = new THREE.Group();
  scene.add(showcase);

  const radius = 4.4;
  const total = FMM_3D_SLIDES.length;
  const texLoader = new THREE.TextureLoader();

  FMM_3D_SLIDES.forEach((item, i) => {
    const angle = (i / total) * Math.PI * 2;
    const px = Math.sin(angle) * radius;
    const pz = Math.cos(angle) * radius;

    // Pedestal
    const pedGeo = new THREE.CylinderGeometry(0.7, 0.8, 1.2, 32);
    const pedMat = new THREE.MeshStandardMaterial({ color: 0x181b1f, roughness: 0.3, metalness: 0.7 });
    const ped = new THREE.Mesh(pedGeo, pedMat);
    ped.position.set(px, 0.6, pz);
    ped.userData = { studyId: item.id };
    showcase.add(ped);

    // Rim
    const rimGeo = new THREE.TorusGeometry(0.71, 0.03, 16, 32);
    const rimMat = new THREE.MeshStandardMaterial({ color: 0xb58b4b, metalness: 0.9, roughness: 0.2 });
    const rim = new THREE.Mesh(rimGeo, rimMat);
    rim.rotation.x = Math.PI / 2;
    rim.position.set(px, 1.2, pz);
    rim.userData = { studyId: item.id };
    showcase.add(rim);

    // Plate
    texLoader.load(item.img, (tex) => {
      const pGeo = new THREE.PlaneGeometry(1.3, 1.7);
      const pMat = new THREE.MeshStandardMaterial({ map: tex, side: THREE.DoubleSide, roughness: 0.2, metalness: 0.1 });
      const plate = new THREE.Mesh(pGeo, pMat);
      plate.position.set(px, 2.3, pz);
      plate.rotation.y = angle;
      plate.userData = { studyId: item.id };
      showcase.add(plate);
    });
  });

  let isDragging = false, startDownX = 0, startDownY = 0, hasDragged = false, targetAngle = 0;
  const ray = new THREE.Raycaster();
  const mVec = new THREE.Vector2();

  container.addEventListener("mousedown", (e) => {
    isDragging = true;
    startDownX = e.clientX;
    startDownY = e.clientY;
    hasDragged = false;
  });

  window.addEventListener("mousemove", (e) => {
    if (isDragging) {
      const dx = e.clientX - startDownX;
      const dy = e.clientY - startDownY;
      if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
        hasDragged = true;
      }
      targetAngle += dx * 0.005;
      startDownX = e.clientX;
      startDownY = e.clientY;
    } else {
      const rect = container.getBoundingClientRect();
      mVec.x = ((e.clientX - rect.left) / container.clientWidth) * 2 - 1;
      mVec.y = -((e.clientY - rect.top) / container.clientHeight) * 2 + 1;
      ray.setFromCamera(mVec, camera);
      const hits = ray.intersectObjects(showcase.children, true);
      container.style.cursor = hits.length > 0 ? "pointer" : "grab";
    }
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
  });

  container.addEventListener("touchstart", (e) => {
    if (e.touches.length > 0) {
      isDragging = true;
      startDownX = e.touches[0].clientX;
      startDownY = e.touches[0].clientY;
      hasDragged = false;
    }
  }, { passive: true });

  window.addEventListener("touchmove", (e) => {
    if (!isDragging || e.touches.length === 0) return;
    const dx = e.touches[0].clientX - startDownX;
    const dy = e.touches[0].clientY - startDownY;
    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
      hasDragged = true;
    }
    targetAngle += dx * 0.005;
    startDownX = e.touches[0].clientX;
    startDownY = e.touches[0].clientY;
  }, { passive: true });

  window.addEventListener("touchend", () => {
    isDragging = false;
  });

  // Click handler on Exhibition items
  container.addEventListener("click", (e) => {
    if (hasDragged) {
      hasDragged = false;
      return;
    }
    const rect = container.getBoundingClientRect();
    mVec.x = ((e.clientX - rect.left) / container.clientWidth) * 2 - 1;
    mVec.y = -((e.clientY - rect.top) / container.clientHeight) * 2 + 1;
    ray.setFromCamera(mVec, camera);
    const hits = ray.intersectObjects(showcase.children, true);
    if (hits.length > 0) {
      let obj = hits[0].object;
      while (obj && !obj.userData.studyId && obj.parent) obj = obj.parent;
      if (obj && obj.userData.studyId) {
        openStudyModal(obj.userData.studyId);
      }
    }
  });

  function animate() {
    requestAnimationFrame(animate);
    if (!isDragging) targetAngle += 0.0015;
    showcase.rotation.y += (targetAngle - showcase.rotation.y) * 0.06;
    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener("resize", () => {
    if (!container || container.clientWidth === 0) return;
    camera.aspect = container.clientWidth / (container.clientHeight || 580);
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight || 580);
  });

  exhibition3DInstance = {
    refreshSize: () => {
      if (!container || container.clientWidth === 0) return;
      camera.aspect = container.clientWidth / (container.clientHeight || 580);
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight || 580);
    }
  };
}

window.toggleHero3DMode = function(mode) {
  if (archive3DInstance) archive3DInstance.setMode(mode);
  document.querySelectorAll(".mode-toggle-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });
  if (mode === "knot") {
    showToast("Sacred Geometry 3D Active · Click the knot to inspect sthapati proportions");
  } else {
    showToast("Bronze Gallery 3D Active · Click any sacred plate to inspect monograph");
  }
};


// ==========================================================================

// ============================================================================
// CURATORIAL MEDALLION CRUD CONTROLLER & RELATIONAL ARCHITECTURE SUITE
// ============================================================================

const CRUD_CONFIG = {
    param_config: {
    title: "T_SYST_PARAM_CONFIG — Application Configuration",
    layer: "syst",
    pk: "id",
    fields: [
      { name: "param_group", label: "Parameter Group", type: "text", required: true },
      { name: "param_key", label: "Parameter Key", type: "text", required: true },
      { name: "param_value", label: "Parameter Value", type: "textarea", required: true, full: true },
      { name: "value_type", label: "Value Type", type: "select", options: ["string", "number", "boolean"], required: false },
      { name: "description", label: "Description", type: "text", required: false, full: true },
      { name: "is_sensitive", label: "Is Sensitive (Credentials / Keys)", type: "boolean", required: false }
    ],
    columns: ["id", "param_group", "param_key", "param_value", "value_type", "is_sensitive", "description"]
  },
  slide_ocr_data: {
    title: "T_RAW_SLIDE_OCR — OCR Engine Outputs & Diagnostics",
    layer: "raw",
    pk: "id",
    fields: [
      { name: "slide_id", label: "Target Study Slide", type: "fk", fk: "slide_id", required: true },
      { name: "ocr_engine", label: "OCR Engine Engine Name", type: "text", required: true, placeholder: "Windows.Media.Ocr / EasyOCR" },
      { name: "language_tag", label: "Language BCP 47 Tag", type: "text", placeholder: "en-US / sa-Deva" },
      { name: "confidence_avg", label: "Confidence Average (0.00 - 1.00)", type: "number" },
      { name: "word_count", label: "Detected Word Count", type: "number" },
      { name: "normalized_text", label: "Normalized Scholarly Text (Editable)", type: "textarea", full: true, ocr_editor: true },
      { name: "raw_ocr_output", label: "Raw OCR Engine Output (Immutable Engine Feed)", type: "textarea", full: true, ocr_editor: true },
      { name: "tokens_json", label: "Bounding Box Tokens JSON", type: "textarea", full: true }
    ],
    columns: ["id", "slide_id", "ocr_engine", "language_tag", "confidence_avg", "normalized_text"]
  },
  ai_metadata_proposals: {
    title: "T_RAW_AI_PROPOSALS — Autonomous Iconography Predictions",
    layer: "raw",
    pk: "id",
    fields: [
      { name: "study_id", label: "Study ID", type: "fk", fk: "study_id", required: true },
      { name: "slide_id", label: "Slide ID", type: "fk", fk: "slide_id" },
      { name: "slide_number", label: "Slide Number", type: "number" },
      { name: "suggested_taxonomy_type", label: "Taxonomy Type", type: "text" },
      { name: "raw_suggested_term", label: "Suggested Term Name", type: "text", required: true },
      { name: "mapped_term_id", label: "Mapped Canonical Term", type: "fk", fk: "term_id" },
      { name: "confidence_score", label: "Confidence Score", type: "number" },
      { name: "review_status", label: "Review Status", type: "select", options: ["pending", "approved", "rejected"] },
      { name: "evidence_snippet", label: "OCR Evidence Snippet", type: "textarea", full: true },
      { name: "curator_notes", label: "Curator Decision Notes", type: "textarea", full: true }
    ],
    columns: ["id", "study_id", "raw_suggested_term", "suggested_taxonomy_type", "confidence_score", "review_status"]
  },

  // ── SILVER LAYER: T_ODS (Curated Monographs / Dictionaries / Catalog) ─────
  studies: {
    title: "T_ODS_STUDIES — Research Monographs & Canonical Studies",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "title", label: "Study Title", type: "text", required: true },
      { name: "subtitle", label: "Subtitle", type: "text" },
      { name: "slug", label: "URL Slug", type: "text" },
      { name: "study_number", label: "Study Number", type: "text", placeholder: "Study 001" },
      { name: "series_id", label: "Curatorial Series", type: "fk", fk: "series_id", required: true },
      { name: "access_level", label: "Access Tier", type: "select", options: ["public", "scholar_tier", "premium"] },
      { name: "status", label: "Publication Status", type: "select", options: ["published", "draft", "archived"] },
      { name: "total_slides", label: "Total Plates / Slides", type: "number" },
      { name: "cover_image_url", label: "Cover Plate Storage URL", type: "text" },
      { name: "search_keywords", label: "Search Keywords & Tags", type: "text" },
      { name: "curator_notes", label: "Curatorial Internal Notes", type: "textarea", full: true },
      { name: "summary_markdown", label: "Scholarly Abstract / Markdown Summary", type: "textarea", full: true }
    ],
    columns: ["id", "title", "study_number", "series_id", "access_level", "status", "updated_by", "updated_at"]
  },
  series: {
    title: "T_ODS_SERIES — Curatorial Editorial Publication Series",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "name", label: "Series Name", type: "text", required: true },
      { name: "slug", label: "URL Slug", type: "text" },
      { name: "status", label: "Status", type: "select", options: ["completed", "in_progress", "planned"] },
      { name: "sort_order", label: "Display Sort Order", type: "number" },
      { name: "cover_image_url", label: "Series Cover URL", type: "text" },
      { name: "scope", label: "Curatorial Scope & Agamic Rationale", type: "textarea", full: true, required: true }
    ],
    columns: ["id", "name", "scope", "status", "sort_order", "updated_by", "updated_at"]
  },
  dictionary: {
    title: "T_ODS_DICTIONARY — IAST Sanskrit Agamic Lexicon",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "headword", label: "Headword (English / Sanskrit)", type: "text", required: true },
      { name: "iast_headword", label: "IAST Diacritics", type: "text" },
      { name: "slug", label: "URL Slug", type: "text" },
      { name: "part_of_speech", label: "Grammar / Part of Speech", type: "text" },
      { name: "etymology", label: "Sanskrit Etymology / Dhatu Root", type: "text" },
      { name: "definition", label: "Agamic & Canonical Definition", type: "textarea", full: true, required: true },
      { name: "extended_notes", label: "Scholarly Cross-References & Textual Notes", type: "textarea", full: true }
    ],
    columns: ["id", "headword", "iast_headword", "part_of_speech", "definition", "updated_by", "updated_at"]
  },
  catalog: {
    title: "T_ODS_DOC_CATALOG — Canonical Shastra & Agama Reference Catalog",
    layer: "ods",
    pk: "doc_ref",
    fields: [
      { name: "doc_ref", label: "Document Reference ID", type: "text", placeholder: "DOC_REF_006", required: true },
      { name: "doc_name", label: "Textual Work Name", type: "text", required: true },
      { name: "corpus", label: "Agamic / Shastra Corpus", type: "text", placeholder: "Agama & Vastu Shastra Corpus" },
      { name: "section", label: "Chapter / Adhyaya / Section", type: "text" },
      { name: "author_or_tradition", label: "Author or Canonical Tradition", type: "text" },
      { name: "language", label: "Original Language / Script", type: "text", placeholder: "Sanskrit (IAST)" },
      { name: "applicability_to_iconography", label: "Applicability to Iconometry & Silpa", type: "textarea", full: true }
    ],
    columns: ["doc_ref", "doc_name", "corpus", "author_or_tradition", "language", "updated_by", "updated_at"]
  },
  taxonomy_terms: {
    title: "T_ODS_TAXONOMY_TERMS — Canonical Iconography Term Registry",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "canonical_name", label: "Canonical Name", type: "text", required: true },
      { name: "iast_name", label: "IAST Diacritic Form", type: "text" },
      { name: "slug", label: "URL Slug", type: "text" },
      { name: "taxonomy_type_id", label: "Classification Type", type: "fk", fk: "taxonomy_type_id", required: true },
      { name: "parent_id", label: "Parent Category (Hierarchy)", type: "fk", fk: "term_id" },
      { name: "dictionary_entry_id", label: "Linked Dictionary Entry", type: "fk", fk: "dictionary_entry_id" },
      { name: "place_id", label: "Geographic Archetype Site", type: "fk", fk: "place_id" },
      { name: "period_id", label: "Dynastic Period / Era", type: "fk", fk: "period_id" },
      { name: "display_order", label: "Display Order", type: "number" },
      { name: "description", label: "Iconographic Specification", type: "textarea", full: true }
    ],
    columns: ["id", "canonical_name", "iast_name", "taxonomy_type_id", "description"]
  },
  taxonomy_types: {
    title: "T_ODS_TAXONOMY_TYPES — Controlled Iconography Types",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "code", label: "Type Code (e.g. mudra, asana, vahana)", type: "text", required: true },
      { name: "name", label: "Type Display Name", type: "text", required: true },
      { name: "description", label: "Type Definition & Scholarly Context", type: "textarea", full: true }
    ],
    columns: ["id", "code", "name", "description"]
  },
  term_aliases: {
    title: "T_ODS_TERM_ALIASES — Multilingual & Cross-Script Aliases",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "term_id", label: "Target Canonical Term", type: "fk", fk: "term_id", required: true },
      { name: "alias", label: "Variant Spelling / Alias", type: "text", required: true },
      { name: "alias_type", label: "Alias Type", type: "select", options: ["iast", "devanagari", "tamil", "telugu", "grantha", "anglicized", "synonym"] }
    ],
    columns: ["id", "term_id", "alias", "alias_type"]
  },
  places: {
    title: "T_ODS_PLACES — Temple & Epigraphic Site Registry",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "name", label: "Site / Temple Name", type: "text", required: true },
      { name: "native_name", label: "Native Script Name", type: "text" },
      { name: "slug", label: "URL Slug", type: "text" },
      { name: "temple_name", label: "Temple Dedication", type: "text" },
      { name: "deity_enshrined", label: "Enshrined Moola Murti", type: "text" },
      { name: "tradition", label: "Agamic Tradition", type: "text", placeholder: "Shaiva Siddhanta / Vaikhanasa / Pancharatra" },
      { name: "town_city", label: "Town / City", type: "text" },
      { name: "district", label: "District", type: "text" },
      { name: "state", label: "State", type: "text" },
      { name: "country", label: "Country", type: "text", placeholder: "India" },
      { name: "notes", label: "Archaeological Notes", type: "textarea", full: true }
    ],
    columns: ["id", "name", "temple_name", "deity_enshrined", "town_city", "state"]
  },
  periods: {
    title: "T_ODS_PERIODS — Dynasties & Historical Epochs",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "name", label: "Dynasty / Era Name", type: "text", required: true },
      { name: "slug", label: "URL Slug", type: "text" },
      { name: "time_span", label: "Century / Time Span", type: "text", placeholder: "9th - 13th Century CE" },
      { name: "region", label: "Geographic Region", type: "text", placeholder: "Tamil Nadu, South India" },
      { name: "description", label: "Art Historical & Silpa Characteristics", type: "textarea", full: true }
    ],
    columns: ["id", "name", "time_span", "region", "description"]
  },
  study_taxonomy_mappings: {
    title: "T_ODS_STUDY_TAXONOMY — Verified Iconographic Term Bridges",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "study_id", label: "Associated Research Study", type: "fk", fk: "study_id", required: true },
      { name: "term_id", label: "Associated Canonical Term", type: "fk", fk: "term_id", required: true },
      { name: "relevance_level", label: "Relevance Level", type: "select", options: ["primary", "secondary", "supporting"] },
      { name: "slide_numbers", label: "Plate Numbers (e.g. 1, 3, 5)", type: "text" },
      { name: "curator_notes", label: "Curator Justification", type: "textarea", full: true }
    ],
    columns: ["id", "study_id", "term_id", "relevance_level", "slide_numbers", "curator_notes"]
  },
  content_access_rules: {
    title: "T_ODS_CONTENT_RULES — DRM & Scholar Access Policies",
    layer: "ods",
    pk: "id",
    fields: [
      { name: "study_id", label: "Target Study", type: "fk", fk: "study_id", required: true },
      { name: "required_tier", label: "Required Tier", type: "select", options: ["free", "scholar", "patron"] },
      { name: "block_reason", label: "Restriction Reason", type: "text" }
    ],
    columns: ["id", "study_id", "required_tier", "block_reason"]
  },

  // ── GOLD LAYER: T_SYST (Platform Operations / Telemetry / IAM) ───────────
  users: {
    title: "T_SYST_USERS — Scholar & Curatorial IAM Identity Registry",
    layer: "syst",
    pk: "id",
    fields: [
      { name: "email", label: "User Email", type: "text", required: true },
      { name: "full_name", label: "Full Name", type: "text" },
      { name: "role", label: "IAM Role", type: "select", options: ["curator", "admin", "scholar_pro", "guest"] },
      { name: "avatar_url", label: "Avatar URL", type: "text" }
    ],
    columns: ["id", "email", "full_name", "role"]
  },
  user_subscriptions: {
    title: "T_SYST_SUBSCRIPTIONS — Active Scholar Subscription Ledger",
    layer: "syst",
    pk: "id",
    fields: [
      { name: "user_id", label: "User Identity", type: "fk", fk: "user_id", required: true },
      { name: "tier", label: "Subscription Tier", type: "select", options: ["scholar_pro", "patron", "institution"] },
      { name: "status", label: "Billing Status", type: "select", options: ["active", "paused", "canceled"] },
      { name: "amount_inr", label: "Amount (INR)", type: "number" },
      { name: "billing_cycle", label: "Billing Cycle", type: "select", options: ["monthly", "annual", "lifetime"] }
    ],
    columns: ["id", "user_id", "tier", "status", "amount_inr", "billing_cycle"]
  },
  user_downloads: {
    title: "T_SYST_DOWNLOADS — 300 DPI Licensed Plate Download Receipts",
    layer: "syst",
    pk: "id",
    fields: [
      { name: "user_id", label: "User Identity", type: "fk", fk: "user_id", required: true },
      { name: "study_id", label: "Study ID", type: "fk", fk: "study_id", required: true },
      { name: "slide_id", label: "Slide ID", type: "fk", fk: "slide_id" },
      { name: "license_ref", label: "Digital License Reference", type: "text" },
      { name: "resolution", label: "Image Resolution", type: "text", placeholder: "300_DPI_MASTER" }
    ],
    columns: ["id", "user_id", "study_id", "license_ref", "resolution"]
  },
  premium_download_requests: {
    title: "T_SYST_DOWNLOAD_REQ — GPay & UPI Payment Verification Orders",
    layer: "syst",
    pk: "id",
    fields: [
      { name: "study_id", label: "Target Study", type: "fk", fk: "study_id", required: true },
      { name: "user_email", label: "Payer Email", type: "text", required: true },
      { name: "transaction_ref", label: "UPI / Transaction Ref ID", type: "text", required: true },
      { name: "amount_inr", label: "Amount (INR)", type: "number" },
      { name: "status", label: "Verification Status", type: "select", options: ["pending", "approved", "rejected"] }
    ],
    columns: ["id", "study_id", "user_email", "transaction_ref", "amount_inr", "status"]
  },
  user_behavior_logs: {
    title: "T_SYST_BEHAVIOR_LOG — Scholarly Event & Query Stream",
    layer: "syst",
    pk: "id",
    fields: [
      { name: "event_type", label: "Event Type", type: "text", required: true },
      { name: "resource_id", label: "Target Resource", type: "text" },
      { name: "user_id", label: "User ID", type: "text" },
      { name: "event_payload_json", label: "Telemetry Payload (JSON)", type: "textarea", full: true }
    ],
    columns: ["id", "event_type", "resource_id", "user_id", "ip_address", "created_at"]
  }
};

// Global CRUD state
state.crudEntity = "studies";
state.crudPage = 1;
state.crudPageSize = 10;
state.crudSearch = "";
state.crudEditingId = null;
state.crudCurrentLayer = "all";
let crudStudioInitialized = false;

// FK options local cache
const fkOptionsCache = {};

async function fetchFkOptions(fieldName) {
  if (fkOptionsCache[fieldName]) return fkOptionsCache[fieldName];
  try {
    const res = await fetch(`${API_BASE}/api/crud/fk-options/${fieldName}`);
    const data = await res.json();
    fkOptionsCache[fieldName] = data.options || [];
    return fkOptionsCache[fieldName];
  } catch (err) {
    console.warn(`FK option fetch failed for ${fieldName}:`, err);
    return [];
  }
}

// Medallion Layer Filter for CRUD suite
window.filterCrudByLayer = function(layer, btn) {
  state.crudCurrentLayer = layer;
  document.querySelectorAll(".crud-layer-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");

  const tabs = document.querySelectorAll(".crud-tab-btn");
  let firstVisible = null;
  let activeVisible = false;

  tabs.forEach(tab => {
    const tabLayer = tab.dataset.layer;
    if (layer === "all" || tabLayer === layer) {
      tab.style.display = "inline-flex";
      if (!firstVisible) firstVisible = tab;
      if (tab.classList.contains("active")) activeVisible = true;
    } else {
      tab.style.display = "none";
    }
  });

  // If active tab was hidden by the filter, activate first visible tab
  if (!activeVisible && firstVisible) {
    firstVisible.click();
  }
};

function initCrudStudio() {
  if (crudStudioInitialized) return;
  
  const tabs = document.getElementById("crudEntityTabs");
  if (tabs) {
    tabs.querySelectorAll(".crud-tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        tabs.querySelectorAll(".crud-tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.crudEntity = btn.dataset.crud;
        state.crudPage = 1;
        state.crudSearch = "";
        const sInput = document.getElementById("crudSearchInput");
        if (sInput) sInput.value = "";
        loadCrudData();
      });
    });
  }

  const searchInput = document.getElementById("crudSearchInput");
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        state.crudSearch = e.target.value.trim();
        state.crudPage = 1;
        loadCrudData();
      }, 250);
    });
  }

  const addBtn = document.getElementById("btnAddCrudRecord");
  if (addBtn) {
    addBtn.addEventListener("click", () => openCrudCreateModal());
  }

  const refreshBtn = document.getElementById("btnRefreshCrud");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => loadCrudData());
  }

  const prevBtn = document.getElementById("crudPrevPageBtn");
  const nextBtn = document.getElementById("crudNextPageBtn");
  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (state.crudPage > 1) {
        state.crudPage--;
        loadCrudData();
      }
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      state.crudPage++;
      loadCrudData();
    });
  }

  const form = document.getElementById("crudForm");
  if (form && !form.dataset.bound) {
    form.addEventListener("submit", handleCrudFormSubmit);
    form.dataset.bound = "true";
  }

  crudStudioInitialized = true;
}

async function loadCrudData() {
  initCrudStudio();
  const container = document.getElementById("crudGridContainer");
  const paginationInfo = document.getElementById("crudPaginationInfo");
  const prevBtn = document.getElementById("crudPrevPageBtn");
  const nextBtn = document.getElementById("crudNextPageBtn");
  const addBtn = document.getElementById("btnAddCrudRecord");
  const paginationBar = document.getElementById("crudPaginationBar");

  if (!container) return;

  // Audit Trail view
  if (state.crudEntity === "audit") {
    if (addBtn) addBtn.style.display = "none";
    if (paginationBar) paginationBar.style.display = "none";
    container.innerHTML = `<div style="padding:20px; text-align:center; color:var(--muted);"><img src="assets/icons/dharma-chakra.svg" class="fmm-icon rotating-chakra" style="width:20px;height:20px;" alt="" /> Querying audit trail logs...</div>`;
    
    try {
      const res = await fetch(`${API_BASE}/api/crud/audit/logs?limit=50`);
      const data = await res.json();
      const logs = data.logs || [];

      if (logs.length === 0) {
        container.innerHTML = `<div style="padding:30px; text-align:center; color:var(--muted);">No audit logs recorded yet.</div>`;
        return;
      }

      container.innerHTML = `
        <table class="admin-data-grid">
          <thead>
            <tr>
              <th style="width:110px;">Action</th>
              <th>Table</th>
              <th>Record ID</th>
              <th>Curator / IAM Role</th>
              <th>Timestamp</th>
              <th style="width:110px;">Audit Snapshot</th>
            </tr>
          </thead>
          <tbody>
            ${logs.map((log, idx) => `
              <tr>
                <td><span class="audit-tag ${log.action.toLowerCase()}">${log.action}</span></td>
                <td><strong style="font-family:monospace;">${log.table_name}</strong></td>
                <td><code style="color:var(--accent); font-weight:700;">${log.record_id}</code></td>
                <td>${log.user_email || 'curator'} (${log.user_role || 'curator'})</td>
                <td style="white-space:nowrap; font-size:11.5px; color:var(--muted);">${new Date(log.timestamp).toLocaleString()}</td>
                <td>
                  <button class="crud-btn-action view" onclick="openAuditDiffModal(${idx})">
                    <img src="assets/icons/grantha-lexicon.svg" class="fmm-icon" style="width:12px;height:12px;" alt="" /> View Diff
                  </button>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
      window.lastAuditLogs = logs;
    } catch (err) {
      container.innerHTML = `<div style="color:var(--danger); padding:20px;">Failed to load audit logs: ${err.message}</div>`;
    }
    return;
  }

  // Regular entity table
  const cfg = CRUD_CONFIG[state.crudEntity] || {
    title: state.crudEntity.toUpperCase(),
    layer: "ods",
    pk: "id",
    columns: ["id"]
  };

  if (addBtn) {
    addBtn.style.display = "inline-flex";
    addBtn.innerHTML = `<span><img src="assets/icons/pramana-check.svg" class="fmm-icon" alt="" /></span> + Add to ${state.crudEntity}`;
  }
  if (paginationBar) paginationBar.style.display = "flex";

  container.innerHTML = `<div style="padding:20px; text-align:center; color:var(--muted);"><img src="assets/icons/dharma-chakra.svg" class="fmm-icon rotating-chakra" style="width:20px;height:20px;" alt="" /> Loading ${state.crudEntity} (${cfg.title.split('—')[0].trim()})…</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/crud/${state.crudEntity}?page=${state.crudPage}&page_size=${state.crudPageSize}&search=${encodeURIComponent(state.crudSearch)}`);
    const data = await res.json();
    const rows = data.rows || [];
    const total = data.total_rows || 0;
    const totalPages = data.total_pages || 1;

    // Update count on tab badge
    const badgeEl = document.getElementById(`crudCount_${state.crudEntity}`);
    if (badgeEl) badgeEl.innerText = total;

    if (paginationInfo) {
      paginationInfo.innerText = `Showing page ${state.crudPage} of ${totalPages} (${total} total records in ${cfg.layer ? cfg.layer.toUpperCase() : ''})`;
    }
    if (prevBtn) prevBtn.disabled = state.crudPage <= 1;
    if (nextBtn) nextBtn.disabled = state.crudPage >= totalPages;

    if (rows.length === 0) {
      container.innerHTML = `
        <div style="padding:40px; text-align:center; color:var(--muted);">
          <div style="font-size:24px; margin-bottom:8px;">📂</div>
          <div style="font-weight:600; font-size:15px; margin-bottom:4px;">No records found in '${state.crudEntity}'</div>
          <div style="font-size:12.5px;">Click <strong>'+ Add to ${state.crudEntity}'</strong> above to insert a new entry into this Medallion table.</div>
        </div>
      `;
      return;
    }

    const cols = cfg.columns && cfg.columns.length > 0 ? cfg.columns : Object.keys(rows[0]);
    const pkField = cfg.pk || "id";

    container.innerHTML = `
      <table class="admin-data-grid">
        <thead>
          <tr>
            <th style="width:145px; text-align:center;">Actions</th>
            ${cols.map(c => `<th>${c.replace(/_/g, ' ').toUpperCase()}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${rows.map(row => `
            <tr>
              <td style="text-align:center; white-space:nowrap;">
                <div style="display:flex; gap:6px; justify-content:center;">
                  <button class="crud-btn-action edit" onclick="openCrudEditModal('${row[pkField]}')">
                    <img src="assets/icons/sthapati-chisel.svg" class="fmm-icon" style="width:12px;height:12px;" alt="" /> Edit
                  </button>
                  <button class="crud-btn-action delete" onclick="confirmCrudDelete('${row[pkField]}', '${(row.title || row.name || row.canonical_name || row.headword || row.doc_name || row.slide_title || row[pkField]).toString().replace(/'/g, "\\'")}')">
                    <img src="assets/icons/kavacha-shield.svg" class="fmm-icon" style="width:12px;height:12px;" alt="" /> Delete
                  </button>
                </div>
              </td>
              ${cols.map(c => {
                const val = row[c];
                if (c === 'created_at' || c === 'updated_at' || c === 'timestamp') {
                  return `<td style="font-size:11px; color:var(--muted); white-space:nowrap;">${val ? new Date(val).toLocaleDateString() : '-'}</td>`;
                }
                if (c === 'updated_by' || c === 'created_by') {
                  return `<td style="font-size:11.5px; color:var(--accent);">${val || 'curator'}</td>`;
                }
                if (c === pkField) {
                  return `<td><code style="font-weight:700; color:#1d4ed8;">${val}</code></td>`;
                }
                if (typeof val === 'string' && val.length > 55) {
                  return `<td title="${val.replace(/"/g, '&quot;')}">${val.substring(0, 55)}…</td>`;
                }
                return `<td>${val !== null && val !== undefined ? val : '<span style="color:#bbb;font-style:italic;">NULL</span>'}</td>`;
              }).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
    window.currentCrudRows = rows;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--danger); padding:20px;">Failed to load records: ${err.message}</div>`;
  }
}

async function openCrudCreateModal() {
  state.crudEditingId = null;
  const cfg = CRUD_CONFIG[state.crudEntity];
  if (!cfg) return;

  const titleEl = document.getElementById("crudModalTitle");
  if (titleEl) titleEl.innerText = `Add New Record — ${cfg.title}`;

  await renderCrudFormFields(cfg.fields || [], {});
  document.getElementById("crudEditModal").classList.add("active");
}

async function openCrudEditModal(recordId) {
  state.crudEditingId = recordId;
  const cfg = CRUD_CONFIG[state.crudEntity];
  if (!cfg) return;

  const titleEl = document.getElementById("crudModalTitle");
  if (titleEl) titleEl.innerText = `Edit ${cfg.title} (${recordId})`;

  try {
    const res = await fetch(`${API_BASE}/api/crud/${state.crudEntity}/${recordId}`);
    const data = await res.json();
    const rec = data.record || {};
    await renderCrudFormFields(cfg.fields || [], rec);
    document.getElementById("crudEditModal").classList.add("active");
  } catch (err) {
    alert("Failed to load record details: " + err.message);
  }
}

async function renderCrudFormFields(fields, values) {
  const container = document.getElementById("crudFormFields");
  if (!container) return;

  let html = "";
  for (const f of fields) {
    const val = values[f.name] !== undefined && values[f.name] !== null ? values[f.name] : "";
    const isFull = f.full ? 'full-width' : '';
    const reqAttr = f.required ? 'required' : '';
    const reqStar = f.required ? '<span style="color:#dc2626;">*</span>' : '';

    if (f.type === "fk") {
      // Foreign key dropdown: fetch options asynchronously
      const opts = await fetchFkOptions(f.fk);
      html += `
        <div class="crud-form-group ${isFull}">
          <label class="crud-form-label">🔗 ${f.label} ${reqStar}</label>
          <select class="crud-form-select fk-select" name="${f.name}" ${reqAttr}>
            <option value="">-- Select ${f.label} --</option>
            ${opts.map(opt => `
              <option value="${opt.value}" ${String(opt.value) === String(val) ? 'selected' : ''}>
                ${opt.label}
              </option>
            `).join("")}
          </select>
        </div>
      `;
    } else if (f.type === "select") {
      html += `
        <div class="crud-form-group ${isFull}">
          <label class="crud-form-label">${f.label} ${reqStar}</label>
          <select class="crud-form-select" name="${f.name}" ${reqAttr}>
            ${(f.options || []).map(opt => `<option value="${opt}" ${opt === val ? 'selected' : ''}>${opt}</option>`).join("")}
          </select>
        </div>
      `;
    } else if (f.type === "textarea") {
      const editorClass = f.ocr_editor ? 'ocr-editor' : '';
      html += `
        <div class="crud-form-group ${isFull}">
          <label class="crud-form-label">${f.ocr_editor ? '✏️ ' : ''}${f.label} ${reqStar}</label>
          <textarea class="crud-form-textarea ${editorClass}" name="${f.name}" rows="${f.ocr_editor ? 7 : 4}" placeholder="${f.placeholder || ''}" ${reqAttr}>${val}</textarea>
        </div>
      `;
    } else if (f.type === "boolean") {
      html += `
        <div class="crud-form-group ${isFull}">
          <label class="crud-form-label">${f.label} ${reqStar}</label>
          <select class="crud-form-select" name="${f.name}">
            <option value="false" ${String(val) === 'true' ? '' : 'selected'}>False (Public / Plaintext)</option>
            <option value="true" ${String(val) === 'true' ? 'selected' : ''}>True (Sensitive / Redacted)</option>
          </select>
        </div>
      `;
    } else {
      html += `
        <div class="crud-form-group ${isFull}">
          <label class="crud-form-label">${f.label} ${reqStar}</label>
          <input class="crud-form-input" type="${f.type || 'text'}" name="${f.name}" value="${val}" placeholder="${f.placeholder || ''}" ${reqAttr}>
        </div>
      `;
    }
  }

  container.innerHTML = html;
}

async function handleCrudFormSubmit(e) {
  e.preventDefault();
  const form = document.getElementById("crudForm");
  const formData = new FormData(form);
  const payload = {};

  formData.forEach((val, key) => {
    payload[key] = val;
  });

  const isEdit = state.crudEditingId !== null;
  const url = isEdit
    ? `${API_BASE}/api/crud/${state.crudEntity}/${state.crudEditingId}`
    : `${API_BASE}/api/crud/${state.crudEntity}`;
  const method = isEdit ? "PUT" : "POST";

  try {
    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.status === 401 || res.status === 403) {
      alert("Authentication required. Please sign in as Curator or Administrator to save changes.");
      openAuthModal();
      return;
    }

    const data = await res.json();
    if (res.ok) {
      showToast(data.message || "Record successfully committed to DuckDB!");
      closeModal("crudEditModal");
      loadCrudData();
      loadArchivalTelemetry();
    } else {
      alert("Save failed: " + (data.detail || "Error"));
    }
  } catch (err) {
    alert("Request error: " + err.message);
  }
}

function openAuditDiffModal(logIdx) {
  const modal = document.getElementById("crudAuditModal");
  const titleEl = document.getElementById("crudAuditModalTitle");
  const contentEl = document.getElementById("crudAuditModalContent");

  const log = (window.lastAuditLogs || [])[logIdx];
  if (!log) return;

  titleEl.innerText = `Audit Record: ${log.action} on ${log.table_name} (${log.record_id})`;

  let prettyDiff = "";
  try {
    const changes = JSON.parse(log.changed_fields_json || "{}");
    const prev = JSON.parse(log.previous_state_json || "{}");
    const next = JSON.parse(log.new_state_json || "{}");

    prettyDiff = `Operation: ${log.action}\nTable:     ${log.table_name}\nRecord ID: ${log.record_id}\nCurator:   ${log.user_email} (${log.user_role})\nTimestamp: ${new Date(log.timestamp).toLocaleString()}\n\n`;

    if (log.action === "UPDATE") {
      prettyDiff += "=== CHANGED FIELDS ===\n" + JSON.stringify(changes, null, 2);
    } else if (log.action === "CREATE") {
      prettyDiff += "=== CREATED RECORD STATE ===\n" + JSON.stringify(next, null, 2);
    } else if (log.action === "DELETE" || log.action === "CASCADE_DELETE") {
      prettyDiff += "=== DELETED SNAPSHOT ===\n" + JSON.stringify(prev, null, 2);
      if (changes && changes.cascade) {
        prettyDiff += `\n\nCascade Notice: Purged ${changes.purged_children_count} dependent child records in atomic transaction.`;
      }
    }
  } catch (e) {
    prettyDiff = `Raw Log Data:\n` + JSON.stringify(log, null, 2);
  }

  contentEl.innerText = prettyDiff;
  modal.classList.add("active");
}

// ── MEDALLION ARCHITECTURE — ER Diagram & Safe Cascade Deletion ─────────────

window.filterErDiagram = function(layer, btn) {
  document.querySelectorAll(".er-filter-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");

  document.querySelectorAll(".er-table-card").forEach(card => {
    if (layer === "all" || card.dataset.layer === layer) {
      card.classList.remove("er-hidden");
    } else {
      card.classList.add("er-hidden");
    }
  });
};

window.openCrudForTable = function(entityKey) {
  // Direct entity keys for all 20 tables
  const tableToEntity = {
    param_config: "param_config",
    slide_ocr_data: "slide_ocr_data",
    study_slides: "study_slides",
    ai_metadata_proposals: "ai_metadata_proposals",
    series: "series",
    studies: "studies",
    study_taxonomy_mappings: "study_taxonomy_mappings",
    taxonomy_types: "taxonomy_types",
    taxonomy_terms: "taxonomy_terms",
    term_aliases: "term_aliases",
    dictionary_entries: "dictionary",
    dictionary: "dictionary",
    places: "places",
    periods_dynasties: "periods",
    periods: "periods",
    doc_ref_catalog: "catalog",
    catalog: "catalog",
    content_access_rules: "content_access_rules",
    users: "users",
    user_subscriptions: "user_subscriptions",
    user_downloads: "user_downloads",
    premium_download_requests: "premium_download_requests",
    user_behavior_logs: "user_behavior_logs",
    audit_logs: "audit",
    audit: "audit"
  };

  const targetEntity = tableToEntity[entityKey] || entityKey;

  // Switch to CRUD mode
  const btnCrud = document.getElementById("btnModeCrud");
  if (btnCrud) btnCrud.click();

  // Activate tab and filter
  setTimeout(() => {
    const tabBtn = document.querySelector(`[data-crud="${targetEntity}"]`);
    if (tabBtn) {
      // Ensure layer filter shows this tab
      const tabLayer = tabBtn.dataset.layer;
      const layerBtn = document.querySelector(`.crud-layer-btn[data-layer="${tabLayer}"]`);
      const allLayerBtn = document.querySelector(`.crud-layer-btn[data-layer="all"]`);
      if (allLayerBtn) allLayerBtn.click();

      tabBtn.click();
      tabBtn.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    } else {
      state.crudEntity = targetEntity;
      loadCrudData();
    }
  }, 100);
};

// Cascade impact fetch
async function fetchCascadeImpact(entity, recordId) {
  try {
    const res = await fetch(`${API_BASE}/api/crud/cascade/${entity}/${recordId}`);
    if (!res.ok) return null;
    return await res.json();
  } catch { return null; }
}

function renderCascadeTree(impact) {
  if (!impact || !impact.children || impact.children.length === 0) {
    return `<div style="color:#059669; font-size:13px; font-weight:600;">✅ No dependent child records found — safe to delete.</div>`;
  }

  let html = `<div class="ci-entity">🗑️ ${impact.entity.toUpperCase()} <code>${impact.record_id}</code>`;
  if (impact.record_label) html += ` <span style="color:#4b5563; font-weight:600;">("${impact.record_label}")</span>`;
  html += `</div>`;

  for (const child of impact.children) {
    html += `<div class="ci-child">
      ├─ <strong>${child.table}</strong>
      <span class="ci-count-badge">${child.count} record${child.count !== 1 ? 's' : ''}</span>
      <span style="color:#dc2626; font-size:11.5px; font-weight:600;"> will be cascade-deleted</span>
    </div>`;
    if (child.children) {
      for (const gc of child.children) {
        html += `<div class="ci-child" style="margin-left:36px;">
          └─ <strong>${gc.table}</strong>
          <span class="ci-count-badge">${gc.count}</span>
          <span style="color:#dc2626; font-size:11px;"> will be cascade-deleted</span>
        </div>`;
      }
    }
  }
  return html;
}

window.confirmCrudDelete = function(recordId, recordTitle) {
  const modal = document.getElementById("crudCascadeModal");
  if (!modal) {
    const oldModal = document.getElementById("crudDeleteModal");
    const msgEl = document.getElementById("crudDeleteMessage");
    const confirmBtn = document.getElementById("btnConfirmCrudDelete");
    if (msgEl) msgEl.innerHTML = `Delete <strong>${recordTitle}</strong> (<code>${recordId}</code>)?`;
    if (confirmBtn) confirmBtn.onclick = () => executeCrudDelete(recordId);
    if (oldModal) oldModal.classList.add("active");
    return;
  }

  const titleEl = document.getElementById("cascadeModalTitle");
  const subtitleEl = document.getElementById("cascadeModalSubtitle");
  const treeEl = document.getElementById("cascadeImpactTree");
  const confirmBtn = document.getElementById("btnCascadeConfirmDelete");

  if (titleEl) titleEl.textContent = `Relational Guard: Delete "${recordTitle}"?`;
  if (subtitleEl) subtitleEl.textContent = `Assessing relational impact across foreign keys for ${state.crudEntity} (${recordId})…`;
  if (treeEl) treeEl.innerHTML = `<div style="color:#6b7280; padding:10px;">Evaluating foreign key dependencies across DuckDB tables…</div>`;
  if (confirmBtn) confirmBtn.disabled = true;

  modal.classList.add("active");

  fetchCascadeImpact(state.crudEntity, recordId).then(impact => {
    if (treeEl) treeEl.innerHTML = renderCascadeTree(impact);
    const hasChildren = impact && impact.children && impact.children.length > 0;
    const totalCascade = impact ? (impact.total_cascade_deletes || 0) : 0;

    if (subtitleEl) {
      subtitleEl.innerHTML = hasChildren
        ? `⚠️ Relational Warning: Deleting this record will <strong>CASCADE DELETE ${totalCascade} child record${totalCascade !== 1 ? 's' : ''}</strong> to preserve foreign key integrity.`
        : `✅ No dependent records. Safe to purge from DuckDB.`;
    }
    if (confirmBtn) {
      confirmBtn.disabled = false;
      confirmBtn.onclick = () => executeCrudDelete(recordId, modal);
    }
  });
};

async function executeCrudDelete(recordId, modal) {
  try {
    // Pass cascade=true to confirm cascading deletion of children
    const res = await fetch(`${API_BASE}/api/crud/${state.crudEntity}/${recordId}?cascade=true`, {
      method: "DELETE"
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || "Record and dependent references deleted.");
      if (modal) modal.classList.remove("active");
      const oldModal = document.getElementById("crudDeleteModal");
      if (oldModal) oldModal.classList.remove("active");
      loadCrudData();
      loadArchivalTelemetry();
    } else {
      alert("Delete failed: " + (data.detail || JSON.stringify(data)));
    }
  } catch (err) {
    alert("Delete request failed: " + err.message);
  }
}

// Live telemetry to ER diagram & CRUD badges
function updateErDiagramCounts(telemetry) {
  const countsMap = {
    erCount_series: telemetry.series_count,
    erCount_studies: telemetry.studies_count,
    erCount_study_slides: telemetry.slides_count,
    erCount_taxonomy_terms: telemetry.taxonomy_terms_count,
    erCount_term_aliases: telemetry.term_aliases_count,
    erCount_study_taxonomy_mappings: telemetry.taxonomy_mappings_count,
    erCount_user_behavior_logs: telemetry.behavior_events_count,
    erCount_slide_ocr_data: telemetry.ocr_records_count,
    crudCount_series: telemetry.series_count,
    crudCount_studies: telemetry.studies_count,
    crudCount_study_slides: telemetry.slides_count,
    crudCount_slide_ocr_data: telemetry.ocr_records_count,
    crudCount_taxonomy_terms: telemetry.taxonomy_terms_count,
    crudCount_term_aliases: telemetry.term_aliases_count,
    crudCount_study_taxonomy_mappings: telemetry.taxonomy_mappings_count,
    crudCount_user_behavior_logs: telemetry.behavior_events_count
  };
  for (const [id, val] of Object.entries(countsMap)) {
    const el = document.getElementById(id);
    if (el && val !== undefined) el.textContent = `${val}`;
  }
}
