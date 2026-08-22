const API_BASE = "http://127.0.0.1:8100";
const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 20000; // give up waiting after 20s, something's wrong

const form = document.getElementById("scanForm");
const input = document.getElementById("attendeeInput");
const button = document.getElementById("scanButton");
const ring = document.getElementById("statusRing");
const glyph = document.getElementById("statusGlyph");
const message = document.getElementById("statusMessage");
const detail = document.getElementById("statusDetail");
const recentList = document.getElementById("recentList");

const recentActivity = [];
let pollTimer = null;

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const attendeeId = input.value.trim().toUpperCase();
  if (!attendeeId) return;

  stopPolling();
  button.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/checkin/${encodeURIComponent(attendeeId)}`, {
      method: "POST",
    });

    if (res.status === 202) {
      // Accepted, job published -- this is the pending state the async
      // pivot introduced. We don't know the outcome yet; poll for it.
      setPending(attendeeId);
      pollForResolution(attendeeId);
      return;
    }

    if (res.status === 409) {
      const body = await res.json();
      setDuplicate(attendeeId, body.detail);
      button.disabled = false;
      return;
    }

    const body = await res.json().catch(() => ({}));
    setError(attendeeId, body.detail || "Unexpected error starting check-in.");
    button.disabled = false;
  } catch (err) {
    setError(attendeeId, "Couldn't reach the check-in service.");
    button.disabled = false;
  }
});

function pollForResolution(attendeeId) {
  const startedAt = Date.now();
  let timeoutNoticeShown = false;

  pollTimer = setInterval(async () => {
    if (!timeoutNoticeShown && Date.now() - startedAt > POLL_TIMEOUT_MS) {
      timeoutNoticeShown = true;
      setStillPending(attendeeId);
      button.disabled = false;
    }

    try {
      const res = await fetch(`${API_BASE}/status/${encodeURIComponent(attendeeId)}`);
      const data = await res.json();

      if (data.status === "checked_in") {
        stopPolling();
        setSuccess(attendeeId);
        button.disabled = false;
      } else if (data.status === "failed") {
        stopPolling();
        setError(attendeeId, "Badge printing failed -- please see staff.");
        button.disabled = false;
      }
      // still "pending" -> keep polling silently
    } catch (err) {
      // transient network hiccup while polling -- keep trying until timeout
    }
  }, POLL_INTERVAL_MS);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function setPending(attendeeId) {
  ring.dataset.state = "pending";
  glyph.textContent = initials(attendeeId);
  message.textContent = "Printing your badge…";
  detail.textContent = `${attendeeId} — hang tight, this only takes a moment.`;
  addRecent(attendeeId, "pending", "printing");
}

function setStillPending(attendeeId) {
  ring.dataset.state = "pending";
  glyph.textContent = initials(attendeeId);
  message.textContent = "Still printing your badge";
  detail.textContent = `${attendeeId} is still pending. You can continue with another scan.`;
  updateRecent(attendeeId, "pending", "still printing");
}

function setSuccess(attendeeId) {
  ring.dataset.state = "success";
  glyph.textContent = "✓";
  message.textContent = "Welcome!";
  detail.textContent = `${attendeeId} is checked in.`;
  updateRecent(attendeeId, "success", "checked in");
}

function setError(attendeeId, reason) {
  ring.dataset.state = "error";
  glyph.textContent = "!";
  message.textContent = "Something went wrong";
  detail.textContent = reason;
  updateRecent(attendeeId, "error", "failed");
}

function setDuplicate(attendeeId, reason) {
  ring.dataset.state = "error";
  glyph.textContent = "!";
  message.textContent = "Already checked in";
  detail.textContent = reason;
  addRecent(attendeeId, "error", "duplicate");
}

function initials(attendeeId) {
  return attendeeId.replace(/[^A-Z0-9]/g, "").slice(-2) || "?";
}

function addRecent(attendeeId, tagClass, tagText) {
  recentActivity.unshift({ attendeeId, tagClass, tagText });
  if (recentActivity.length > 6) recentActivity.pop();
  renderRecent();
}

function updateRecent(attendeeId, tagClass, tagText) {
  const entry = recentActivity.find((r) => r.attendeeId === attendeeId);
  if (entry) {
    entry.tagClass = tagClass;
    entry.tagText = tagText;
  } else {
    addRecent(attendeeId, tagClass, tagText);
    return;
  }
  renderRecent();
}

function renderRecent() {
  recentList.innerHTML = recentActivity
    .map(
      (r) => `
        <li class="recent-item">
          <span>${escapeHtml(r.attendeeId)}</span>
          <span class="tag ${r.tagClass}">${escapeHtml(r.tagText)}</span>
        </li>
      `
    )
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}