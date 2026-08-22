// ---------------------------------------------------------------------------
// LIVE DATA LAYER -- wired to the real sync service as of Day 4/5.
// Backend must be running: uvicorn sync_service:app --port 8000
// ---------------------------------------------------------------------------
const API_BASE = "http://127.0.0.1:8000";

async function fetchStock(sku) {
  const res = await fetch(`${API_BASE}/api/stock/${encodeURIComponent(sku)}`);
  if (res.status === 404) {
    return { sku: sku.toUpperCase(), found: false };
  }
  const data = await res.json();
  return { ...data, found: true };
}

async function searchStock(query) {
  const res = await fetch(`${API_BASE}/api/stock/search?q=${encodeURIComponent(query)}`);
  return res.json(); // array, possibly empty
}

async function fetchSyncStatus() {
  const res = await fetch(`${API_BASE}/api/sync-status`);
  return res.json();
}
// ---------------------------------------------------------------------------

const form = document.getElementById("lookupForm");
const input = document.getElementById("skuInput");
const resultArea = document.getElementById("resultArea");
const recentList = document.getElementById("recentList");
const syncUpdated = document.getElementById("syncUpdated");

const recentLookups = [];

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = input.value.trim();
  if (!query) return;

  resultArea.innerHTML = `<p class="result-empty">Checking ${escapeHtml(query)}...</p>`;

  // Try as an exact SKU first -- fastest path, matches how staff actually
  // scan a barcode.
  const exact = await fetchStock(query);
  if (exact.found) {
    renderResult(exact);
    addToRecent(exact);
    return;
  }

  // Not a known SKU -- fall back to name search.
  const matches = await searchStock(query);
  if (matches.length === 1) {
    // Single unambiguous match -- just show it, no need to make them click.
    const result = { ...matches[0], found: true };
    renderResult(result);
    addToRecent(result);
  } else if (matches.length > 1) {
    renderSearchResults(query, matches);
  } else {
    renderResult(exact); // the original "not found" card
    addToRecent(exact);
  }
});

function renderSearchResults(query, matches) {
  resultArea.innerHTML = `
    <div class="search-results">
      <p class="search-results-label">${matches.length} products match "${escapeHtml(query)}"</p>
      ${matches
        .map(
          (item) => `
        <button type="button" class="search-result-item" data-sku="${escapeHtml(item.sku)}">
          <span>${escapeHtml(item.name)}</span>
          <span class="search-result-sku">${escapeHtml(item.sku)}</span>
        </button>
      `
        )
        .join("")}
    </div>
  `;

  resultArea.querySelectorAll(".search-result-item").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const sku = btn.dataset.sku;
      const result = await fetchStock(sku);
      renderResult(result);
      addToRecent(result);
    });
  });
}

function renderResult(data) {
  if (!data.found) {
    resultArea.innerHTML = `
      <div class="result-card out-of-stock">
        <div>
          <div class="result-sku">${escapeHtml(data.sku)}</div>
          <div class="result-status out-of-stock-text">SKU not found</div>
        </div>
      </div>
    `;
    return;
  }

  const inStock = data.count > 0;
  const cardClass = inStock ? "in-stock" : "out-of-stock";
  const statusClass = inStock ? "in-stock-text" : "out-of-stock-text";
  const statusText = inStock ? "In stock" : "Out of stock";

  resultArea.innerHTML = `
    <div class="result-card ${cardClass}">
      <div>
        <div class="result-sku">${escapeHtml(data.sku)} &middot; ${escapeHtml(data.name)}</div>
        <div class="result-status ${statusClass}">${statusText}</div>
      </div>
      <div style="text-align:right">
        <div class="result-count">${data.count}</div>
        <div class="result-count-label">units</div>
      </div>
    </div>
  `;
}

function addToRecent(data) {
  recentLookups.unshift(data);
  if (recentLookups.length > 6) recentLookups.pop();

  recentList.innerHTML = recentLookups
    .map((item) => {
      const inStock = item.found && item.count > 0;
      const tagClass = !item.found ? "out-of-stock" : inStock ? "in-stock" : "out-of-stock";
      const tagText = !item.found ? "not found" : inStock ? "in stock" : "out of stock";
      return `
        <li class="recent-item">
          <span>${escapeHtml(item.sku)}</span>
          <span class="tag ${tagClass}">${tagText}</span>
        </li>
      `;
    })
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// Sync indicator -- reads the real /api/sync-status endpoint, so this
// reflects the backend's actual mode ("polling" pre-pivot, "webhook" now)
// rather than being purely decorative.
const syncIndicator = document.getElementById("syncIndicator");
const syncLabel = document.getElementById("syncLabel");

async function refreshSyncIndicator() {
  try {
    const status = await fetchSyncStatus();
    syncIndicator.dataset.mode = status.mode;
    syncLabel.textContent =
      status.mode === "webhook" ? "Webhook \u00b7 live" : "Polling \u00b7 every 5 min";

    if (status.last_updated) {
      const d = new Date(status.last_updated);
      const h = String(d.getHours()).padStart(2, "0");
      const m = String(d.getMinutes()).padStart(2, "0");
      syncUpdated.textContent = `last synced ${h}:${m}`;
    } else {
      syncUpdated.textContent = "no sync yet";
    }
  } catch (err) {
    syncUpdated.textContent = "backend unreachable";
  }
}

refreshSyncIndicator();
setInterval(refreshSyncIndicator, 5000);