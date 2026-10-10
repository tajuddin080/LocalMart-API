"use strict";

const API_BASE = window.location.origin;
const state = {
  warehouses: [],
  location: "",
  products: [],
  user: null,
  cart: null,
  accountTab: "login",
  productRequest: 0,
  busy: false,
};

const palette = [
  ["#e8eee2", "#50744f"],
  ["#f7ead7", "#bf8150"],
  ["#e6edf0", "#557889"],
  ["#f1e7eb", "#9b6676"],
  ["#ece9dd", "#82754a"],
  ["#e4eee8", "#59806b"],
];

const elements = {
  location: document.querySelector("#location-select"),
  search: document.querySelector("#product-search"),
  grid: document.querySelector("#product-grid"),
  resultCount: document.querySelector("#result-count"),
  catalogSubtitle: document.querySelector("#catalog-subtitle"),
  catalogEmpty: document.querySelector("#catalog-empty"),
  emptyTitle: document.querySelector("#empty-title"),
  emptyMessage: document.querySelector("#empty-message"),
  cartPanel: document.querySelector("#cart-panel"),
  cartContent: document.querySelector("#cart-content"),
  cartItemCount: document.querySelector("#cart-item-count"),
  cartTotal: document.querySelector("#cart-total"),
  checkout: document.querySelector("#checkout-button"),
  accountButton: document.querySelector("#account-button"),
  accountLabel: document.querySelector("#account-label"),
  accountAvatar: document.querySelector("#account-avatar"),
  accountDialog: document.querySelector("#account-dialog"),
  accountPanel: document.querySelector("#account-panel"),
  ordersDialog: document.querySelector("#orders-dialog"),
  ordersContent: document.querySelector("#orders-content"),
  toastRegion: document.querySelector("#toast-region"),
  refresh: document.querySelector("#refresh-button"),
};

const currency = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

function formatMoney(value) {
  const amount = Number(value);
  return currency.format(Number.isFinite(amount) ? amount : 0);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function productArt(product, index, compact = false) {
  const [background, accent] = palette[index % palette.length];
  const label = String(product.PNAME || "Product").trim().slice(0, 1).toUpperCase();
  const icon = `<svg viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M12 19.5h24l-2 19H14l-2-19Z" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M17 20v-5a7 7 0 0 1 14 0v5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
    <path d="M19 28c2.4-2.5 7.6-2.5 10 0" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
    <circle cx="24" cy="26" r="1.5" fill="currentColor"/>
  </svg>`;
  const classes = compact ? "cart-item-art" : "product-illustration";
  return `<span class="${classes}" style="--product-bg:${background};--product-accent:${accent}" aria-label="${escapeHtml(label)}">${icon}</span>`;
}

async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    throw new Error(`Could not reach the LocalMart API at ${API_BASE}. Make sure the FastAPI server is running. (${error.message})`);
  }

  const text = await response.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    const detail = body && typeof body === "object" ? body.detail : null;
    const message = Array.isArray(detail)
      ? detail.map((issue) => `${issue.loc?.at(-1) || "Field"}: ${issue.msg}`).join("; ")
      : typeof detail === "string"
        ? detail
        : `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return body;
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast${type === "error" ? " error" : ""}`;
  toast.textContent = message;
  elements.toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), 5000);
}

function setBusy(isBusy) {
  state.busy = isBusy;
  elements.checkout.disabled = isBusy || !state.user || !state.cart?.ITEMS?.length;
  elements.refresh.disabled = isBusy;
}

function selectedLocation() {
  return state.location;
}

function renderWarehouses() {
  const locations = [...new Set(state.warehouses.map((warehouse) => warehouse.LOCATION).filter(Boolean))];
  elements.location.replaceChildren();
  if (!locations.length) {
    const option = new Option("No locations available", "");
    elements.location.add(option);
    elements.location.disabled = true;
    return;
  }

  elements.location.disabled = false;
  for (const location of locations) {
    elements.location.add(new Option(location, location));
  }
  if (!locations.includes(state.location)) state.location = locations[0];
  elements.location.value = state.location;
}

async function loadWarehouses() {
  const warehouses = await apiRequest("/warehouses");
  state.warehouses = Array.isArray(warehouses) ? warehouses : [];
  renderWarehouses();
  await loadProducts();
}

async function loadProducts() {
  const requestId = ++state.productRequest;
  const location = selectedLocation();
  elements.grid.setAttribute("aria-busy", "true");
  elements.grid.replaceChildren();
  elements.catalogEmpty.classList.add("hidden");

  if (!location) {
    state.products = [];
    renderProducts();
    return;
  }

  elements.resultCount.textContent = "Finding local stock…";
  try {
    const query = new URLSearchParams({ Location: location });
    const products = await apiRequest(`/product?${query.toString()}`);
    if (requestId !== state.productRequest) return;
    state.products = Array.isArray(products) ? products : [];
    renderProducts();
    elements.catalogSubtitle.textContent = `Available from warehouses serving ${location}.`;
  } catch (error) {
    if (requestId !== state.productRequest) return;
    state.products = [];
    renderProducts();
    elements.emptyTitle.textContent = "We couldn't load the local shelf";
    elements.emptyMessage.textContent = error.message;
    showToast(error.message, "error");
  } finally {
    if (requestId === state.productRequest) elements.grid.setAttribute("aria-busy", "false");
  }
}

function renderProducts() {
  const query = elements.search.value.trim().toLowerCase();
  const available = state.products.filter((product) => Number(product.PQUANTITY) > 0);
  const filtered = available.filter((product) => {
    const searchable = `${product.PNAME || ""} ${product.PID || ""} ${product.WID || ""}`.toLowerCase();
    return searchable.includes(query);
  });

  elements.grid.replaceChildren();
  elements.resultCount.textContent = query
    ? `${filtered.length} ${filtered.length === 1 ? "match" : "matches"}`
    : `${filtered.length} ${filtered.length === 1 ? "good find" : "good finds"}`;

  filtered.forEach((product, index) => {
    const [background] = palette[index % palette.length];
    const card = document.createElement("article");
    card.className = "product-card";
    card.innerHTML = `
      <div class="product-art" style="--product-bg:${background}">
        ${productArt(product, index)}
        <span class="product-warehouse">${escapeHtml(product.WID || "Local stock")}</span>
      </div>
      <div class="product-info">
        <h3 class="product-name">${escapeHtml(product.PNAME || "Untitled product")}</h3>
        <p class="product-id">${escapeHtml(product.PID || "")}</p>
        <div class="product-buy-row">
          <div>
            <div class="product-price">${formatMoney(product.PPRICE)}</div>
            <div class="product-stock">${Number(product.PQUANTITY)} in stock</div>
          </div>
          <button class="add-button" type="button" aria-label="Add ${escapeHtml(product.PNAME || "product")} to basket" data-product-id="${escapeHtml(product.PID)}">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
              <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>`;
    card.querySelector(".add-button").addEventListener("click", () => addToCart(product));
    elements.grid.append(card);
  });

  elements.catalogEmpty.classList.toggle("hidden", filtered.length > 0);
  if (!filtered.length) {
    if (query) {
      elements.emptyTitle.textContent = "No matches just yet";
      elements.emptyMessage.textContent = "Try another name or product ID.";
    } else if (!available.length && state.products.length) {
      elements.emptyTitle.textContent = "All sold out for now";
      elements.emptyMessage.textContent = "There isn't any in-stock inventory at this location.";
    } else if (!state.products.length) {
      elements.emptyTitle.textContent = "Nothing on this shelf yet";
      elements.emptyMessage.textContent = "Try another location or check back later.";
    }
  }
}

function renderCart() {
  const items = state.cart?.ITEMS || [];
  const totalQuantity = items.reduce((total, item) => total + Number(item.PQUANTITY || 0), 0);
  elements.cartItemCount.textContent = `${totalQuantity} ${totalQuantity === 1 ? "item" : "items"}`;
  document.querySelector("#mobile-cart-count").textContent = String(totalQuantity);
  elements.cartTotal.textContent = formatMoney(state.cart?.TOTAL_AMOUNT || 0);
  elements.cartContent.replaceChildren();

  if (!state.user) {
    elements.cartContent.innerHTML = `
      <div class="cart-empty">
        <span class="cart-empty-art" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M3 4h2l2.1 11.3a2 2 0 0 0 2 1.7h8.4a2 2 0 0 0 1.9-1.5L21 9H6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="10" cy="20" r="1" fill="currentColor"/><circle cx="18" cy="20" r="1" fill="currentColor"/>
          </svg>
        </span>
        <h3>Your basket starts here</h3>
        <p>Sign in to save your basket and make it yours.</p>
        <button class="cart-sign-in" type="button">Sign in or create account</button>
      </div>`;
    elements.cartContent.querySelector(".cart-sign-in").addEventListener("click", openAccountDialog);
    setBusy(state.busy);
    return;
  }

  if (!items.length) {
    elements.cartContent.innerHTML = `
      <div class="cart-empty">
        <span class="cart-empty-art" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M3 4h2l2.1 11.3a2 2 0 0 0 2 1.7h8.4a2 2 0 0 0 1.9-1.5L21 9H6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="10" cy="20" r="1" fill="currentColor"/><circle cx="18" cy="20" r="1" fill="currentColor"/>
          </svg>
        </span>
        <h3>A little room for something good</h3>
        <p>Tap the plus on anything you like and it’ll show up here.</p>
      </div>`;
    setBusy(state.busy);
    return;
  }

  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "cart-item";
    row.innerHTML = `
      ${productArt(item, index, true)}
      <div>
        <p class="cart-item-name">${escapeHtml(item.PNAME || "Untitled product")}</p>
        <p class="cart-item-price">${formatMoney(item.PPRICE)} each</p>
        <div class="cart-item-controls" aria-label="Quantity controls">
          <button class="quantity-button" type="button" aria-label="Decrease quantity of ${escapeHtml(item.PNAME)}" data-action="decrease">−</button>
          <span class="quantity-value">${Number(item.PQUANTITY)}</span>
          <button class="quantity-button" type="button" aria-label="Increase quantity of ${escapeHtml(item.PNAME)}" data-action="increase">+</button>
          <button class="remove-item" type="button" aria-label="Remove ${escapeHtml(item.PNAME)} from basket">Remove</button>
        </div>
      </div>
      <span class="line-total">${formatMoney(item.LINE_TOTAL)}</span>`;
    row.querySelector('[data-action="decrease"]').addEventListener("click", () => updateCartQuantity(item, Number(item.PQUANTITY) - 1));
    row.querySelector('[data-action="increase"]').addEventListener("click", () => updateCartQuantity(item, Number(item.PQUANTITY) + 1));
    row.querySelector(".remove-item").addEventListener("click", () => removeFromCart(item));
    elements.cartContent.append(row);
  });
  setBusy(state.busy);
}

function updateAccountHeader() {
  if (state.user) {
    const name = state.user.UID || state.user.UEMAIL || "Customer";
    elements.accountLabel.textContent = name;
    elements.accountAvatar.textContent = name.slice(0, 1).toUpperCase();
  } else {
    elements.accountLabel.textContent = "Sign in";
    elements.accountAvatar.textContent = "G";
  }
}

async function loadCart() {
  if (!state.user) {
    state.cart = null;
    renderCart();
    return;
  }
  state.cart = await apiRequest(`/cart/${encodeURIComponent(state.user.UID)}`);
  renderCart();
}

async function addToCart(product) {
  if (!state.user) {
    state.accountTab = "login";
    openAccountDialog();
    showToast("Sign in or create an account before adding items.", "error");
    return;
  }
  if (state.busy) return;
  setBusy(true);
  try {
    state.cart = await apiRequest(`/cart/${encodeURIComponent(state.user.UID)}/items`, {
      method: "POST",
      body: JSON.stringify({ PID: product.PID, PQUANTITY: 1 }),
    });
    renderCart();
    showToast(`${product.PNAME} added to your basket.`);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(false);
    renderCart();
  }
}

async function updateCartQuantity(item, quantity) {
  if (!state.user || state.busy) return;
  if (quantity < 1) {
    await removeFromCart(item);
    return;
  }
  state.busy = true;
  renderCart();
  try {
    state.cart = await apiRequest(`/cart/${encodeURIComponent(state.user.UID)}/items/${encodeURIComponent(item.PID)}`, {
      method: "PUT",
      body: JSON.stringify({ PQUANTITY: quantity }),
    });
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    state.busy = false;
    renderCart();
  }
}

async function removeFromCart(item) {
  if (!state.user || state.busy) return;
  state.busy = true;
  renderCart();
  try {
    state.cart = await apiRequest(`/cart/${encodeURIComponent(state.user.UID)}/items/${encodeURIComponent(item.PID)}`, {
      method: "DELETE",
    });
    showToast(`${item.PNAME} removed from your basket.`);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    state.busy = false;
    renderCart();
  }
}

function openAccountDialog() {
  renderAccountDialog();
  elements.accountDialog.showModal();
}

function renderAccountDialog() {
  if (state.user) {
    elements.accountPanel.innerHTML = `
      <div class="account-summary">
        <strong>${escapeHtml(state.user.UID)}</strong>
        <p>${escapeHtml(state.user.UEMAIL)}${state.user.LOCATION ? ` · ${escapeHtml(state.user.LOCATION)}` : ""}</p>
      </div>
      <p class="account-caution">This demo verifies your password but does not create a secure session. Your user ID is only an identifier, not authentication.</p>
      <button class="secondary-button" id="sign-out-button" type="button">Sign out on this device</button>`;
    elements.accountPanel.querySelector("#sign-out-button").addEventListener("click", signOut);
    return;
  }

  const isLogin = state.accountTab === "login";
  const locations = [...new Set(state.warehouses.map((warehouse) => warehouse.LOCATION).filter(Boolean))];
  elements.accountPanel.innerHTML = `
    <div class="dialog-tabs" role="tablist" aria-label="Account options">
      <button class="dialog-tab" type="button" role="tab" aria-selected="${isLogin}" data-tab="login">Sign in</button>
      <button class="dialog-tab" type="button" role="tab" aria-selected="${!isLogin}" data-tab="register">Create account</button>
    </div>
    ${isLogin ? `
      <form class="form-stack" id="login-form">
        <label class="form-field">Email address
          <input name="email" type="email" autocomplete="email" required maxlength="254" placeholder="you@example.com" />
        </label>
        <label class="form-field">Password
          <input name="password" type="password" autocomplete="current-password" required minlength="8" maxlength="128" placeholder="At least 8 characters" />
        </label>
        <p class="form-error" id="account-error" role="alert"></p>
        <button class="form-submit" type="submit">Sign in <span aria-hidden="true">→</span></button>
      </form>` : `
      <form class="form-stack" id="register-form">
        <label class="form-field">Customer ID
          <input name="uid" type="text" autocomplete="username" required maxlength="50" placeholder="For example, C101" />
        </label>
        <label class="form-field">Email address
          <input name="email" type="email" autocomplete="email" required maxlength="254" placeholder="you@example.com" />
        </label>
        <label class="form-field">Password
          <input name="password" type="password" autocomplete="new-password" required minlength="8" maxlength="128" placeholder="At least 8 characters" />
        </label>
        <p class="form-hint">Choose a location with a nearby warehouse so the shop and checkout can find local stock.</p>
        <p class="form-error" id="account-error" role="alert"></p>
        <button class="form-submit" type="submit" ${locations.length ? "" : "disabled"}>Create customer account <span aria-hidden="true">→</span></button>
      </form>`}`;

  elements.accountPanel.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.accountTab = button.dataset.tab;
      renderAccountDialog();
    });
  });

  const loginForm = elements.accountPanel.querySelector("#login-form");
  if (loginForm) loginForm.addEventListener("submit", submitLogin);
  const registerForm = elements.accountPanel.querySelector("#register-form");
  if (registerForm) registerForm.addEventListener("submit", submitRegistration);
}

function setFormError(message) {
  const error = elements.accountPanel.querySelector("#account-error");
  if (error) error.textContent = message;
}

async function submitLogin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const submit = form.querySelector('[type="submit"]');
  const formData = new FormData(form);
  submit.disabled = true;
  submit.textContent = "Signing in…";
  setFormError("");
  try {
    const user = await apiRequest("/login", {
      method: "POST",
      body: JSON.stringify({
        Uemail: formData.get("email"),
        Upword: formData.get("password"),
      }),
    });
    await beginCustomerSession(user);
  } catch (error) {
    setFormError(error.message);
    submit.disabled = false;
    submit.innerHTML = 'Sign in <span aria-hidden="true">→</span>';
  }
}

async function submitRegistration(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const submit = form.querySelector('[type="submit"]');
  const formData = new FormData(form);
  submit.disabled = true;
  submit.textContent = "Creating your account…";
  setFormError("");

  try {
    const user = await apiRequest("/adduser", {
      method: "POST",
      body: JSON.stringify({
        UID: String(formData.get("uid")).trim(),
        UEMAIL: String(formData.get("email")).trim(),
        UPWORD: formData.get("password"),
        LOCATION: selectedLocation(),
      }),
    });
    await beginCustomerSession(user);
    showToast("Welcome to LocalMart. Your account is ready.");
  } catch (error) {
    setFormError(error.message);
    submit.disabled = false;
    submit.innerHTML = 'Create customer account <span aria-hidden="true">→</span>';
  }
}

async function beginCustomerSession(user) {
  state.user = user;
  updateAccountHeader();
  const hasMatchingWarehouse = state.warehouses.some((warehouse) => warehouse.LOCATION === user.LOCATION);
  if (user.LOCATION && hasMatchingWarehouse) {
    state.location = user.LOCATION;
    elements.location.value = user.LOCATION;
    await loadProducts();
    elements.location.disabled = true;
  } else {
    state.products = [];
    state.location = user.LOCATION || state.location;
    if (user.LOCATION) {
      elements.location.add(new Option(`${user.LOCATION} (no warehouse found)`, user.LOCATION));
      elements.location.value = user.LOCATION;
    }
    elements.location.disabled = true;
    renderProducts();
    elements.catalogSubtitle.textContent = "No warehouse matches your saved account location.";
    elements.emptyTitle.textContent = "Your account needs a local warehouse";
    elements.emptyMessage.textContent = "Ask the project administrator to add a warehouse at your saved location.";
  }
  try {
    await loadCart();
  } catch (error) {
    showToast(`Signed in, but your basket couldn't be loaded: ${error.message}`, "error");
  }
  elements.accountDialog.close();
  if (!hasMatchingWarehouse) {
    showToast(`Your account location (${user.LOCATION}) has no matching warehouse. Checkout needs an exact location match.`, "error");
  }
}

function signOut() {
  state.user = null;
  state.cart = null;
  updateAccountHeader();
  renderWarehouses();
  elements.location.disabled = !state.warehouses.length;
  renderCart();
  elements.accountDialog.close();
  loadProducts().catch((error) => showToast(error.message, "error"));
  showToast("You have signed out on this device.");
}

function readableDate(value) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

async function openOrdersDialog() {
  if (!state.user) {
    state.accountTab = "login";
    openAccountDialog();
    showToast("Sign in to view your order history.", "error");
    return;
  }
  elements.ordersContent.innerHTML = '<div class="orders-empty"><span class="orders-empty-icon" aria-hidden="true">↻</span><h3>Finding your orders…</h3></div>';
  elements.ordersDialog.showModal();
  try {
    const orders = await apiRequest(`/orders/${encodeURIComponent(state.user.UID)}?limit=20&offset=0`);
    renderOrders(Array.isArray(orders) ? orders : []);
  } catch (error) {
    elements.ordersContent.innerHTML = `<div class="orders-empty"><span class="orders-empty-icon" aria-hidden="true">!</span><h3>We couldn't load your orders</h3><p>${escapeHtml(error.message)}</p></div>`;
  }
}

function renderOrders(orders) {
  if (!orders.length) {
    elements.ordersContent.innerHTML = `
      <div class="orders-empty">
        <span class="orders-empty-icon" aria-hidden="true">✳</span>
        <h3>No orders just yet</h3>
        <p>Your next good find is waiting. Once you place an order, it’ll show up here.</p>
      </div>`;
    return;
  }

  elements.ordersContent.innerHTML = orders.map((order) => `
    <details class="order-card">
      <summary>
        <div>
          <div class="order-heading">Order #${escapeHtml(order.OID)}</div>
          <div class="order-date">${escapeHtml(readableDate(order.CREATED_AT))} · ${escapeHtml(order.LOCATION || "")}</div>
        </div>
        <span class="order-status">${escapeHtml(order.STATUS || "placed")}</span>
      </summary>
      <div class="order-total">Order total <strong>${formatMoney(order.TOTAL_AMOUNT)}</strong></div>
      <ul class="order-lines">
        ${(order.ITEMS || []).map((item) => `<li><span>${escapeHtml(item.PNAME)} × ${Number(item.PQUANTITY)}</span><span>${formatMoney(item.LINE_TOTAL)}</span></li>`).join("")}
      </ul>
    </details>`).join("");
}

async function checkout() {
  if (!state.user) {
    state.accountTab = "login";
    openAccountDialog();
    return;
  }
  if (!state.cart?.ITEMS?.length || state.busy) return;
  state.busy = true;
  renderCart();
  try {
    const order = await apiRequest("/checkout", {
      method: "POST",
      body: JSON.stringify({ UID: state.user.UID }),
    });
    state.cart = {
      UID: state.user.UID,
      ITEMS: [],
      TOTAL_AMOUNT: 0,
    };
    renderCart();
    showToast(`Order #${order.OID} placed — ${formatMoney(order.TOTAL_AMOUNT)}. Your basket is ready for something new.`);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    state.busy = false;
    renderCart();
  }
}

document.querySelectorAll("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});
for (const dialog of [elements.accountDialog, elements.ordersDialog]) {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
}
elements.accountButton.addEventListener("click", openAccountDialog);
document.querySelector("#orders-button").addEventListener("click", openOrdersDialog);
document.querySelector("#mobile-cart-button").addEventListener("click", () => elements.cartPanel.scrollIntoView({ behavior: "smooth", block: "start" }));
elements.search.addEventListener("input", renderProducts);
elements.location.addEventListener("change", async () => {
  state.location = elements.location.value;
  await loadProducts();
});
elements.refresh.addEventListener("click", async () => {
  try {
    await loadWarehouses();
  } catch (error) {
    showToast(error.message, "error");
  }
});
elements.checkout.addEventListener("click", checkout);
document.addEventListener("keydown", (event) => {
  if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
    event.preventDefault();
    elements.search.focus();
  }
});

renderCart();
loadWarehouses().catch((error) => {
  elements.resultCount.textContent = "API unavailable";
  elements.emptyTitle.textContent = "The local shelves are taking a break";
  elements.emptyMessage.textContent = error.message;
  elements.catalogEmpty.classList.remove("hidden");
  elements.grid.setAttribute("aria-busy", "false");
  showToast(error.message, "error");
});
