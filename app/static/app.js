const API_BASE = "";
let currentThreadId = null;
let models = {};

async function fetchThreads() {
  const res = await fetch(`${API_BASE}/threads`);
  const threads = await res.json();
  const list = document.getElementById("thread-list");
  list.innerHTML = "";
  threads.forEach((t) => {
    const el = document.createElement("div");
    el.className = "thread-item";
    el.textContent = `${t.id}: ${t.title}`;
    el.onclick = () => selectThread(t.id, t.title);
    list.appendChild(el);
  });
}

async function createThread(e) {
  e.preventDefault();
  const title = document.getElementById("thread-title").value.trim();
  const system_prompt = document.getElementById("thread-system").value.trim();
  if (!title) return alert("Title required");
  const res = await fetch(`${API_BASE}/threads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, system_prompt }),
  });
  if (!res.ok) return alert("Error creating thread");
  document.getElementById("thread-title").value = "";
  document.getElementById("thread-system").value = "";
  await fetchThreads();
}

async function selectThread(id, title) {
  currentThreadId = id;
  document.getElementById("thread-title-display").textContent =
    `${title} (#${id})`;
  await loadThreadDetails();
}

async function loadThreadDetails() {
  if (!currentThreadId) return;
  const res = await fetch(`${API_BASE}/threads/${currentThreadId}`);
  if (!res.ok) return alert("Failed to load thread");
  const thread = await res.json();
  const msgContainer = document.getElementById("messages");
  msgContainer.innerHTML = "";
  (thread.messages || []).forEach((m) => {
    const mEl = document.createElement("div");
    mEl.className = "message " + (m.sender === "agent" ? "agent" : "user");
    const modelInfo = m.model_used
      ? ` <small class="model-used">(${m.model_used})</small>`
      : "";
    mEl.innerHTML = `<strong>${m.sender}:</strong> ${m.content}${modelInfo}`;
    msgContainer.appendChild(mEl);
  });
}

async function fetchModels() {
  const res = await fetch(`${API_BASE}/threads/available-models`);
  if (!res.ok) return;
  models = await res.json();
  const sel = document.getElementById("model-select");
  sel.innerHTML = "";
  Object.keys(models).forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  });
}

async function sendMessage(e) {
  e.preventDefault();
  if (!currentThreadId) return alert("Select a thread first");
  const input = document.getElementById("message-input");
  const content = input.value.trim();
  if (!content) return;
  const model = document.getElementById("model-select").value;
  const payload = { sender: "web_user", content, model };
  const res = await fetch(`${API_BASE}/threads/${currentThreadId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.text();
    return alert("Error sending message: " + err);
  }
  input.value = "";
  await loadThreadDetails();
}

async function fetchSummaries() {
  if (!currentThreadId) return alert("Select a thread first");
  const res = await fetch(`${API_BASE}/threads/${currentThreadId}/summaries`);
  if (!res.ok) return alert("Failed to get summaries");
  const sums = await res.json();
  const container = document.getElementById("summary-list");
  container.innerHTML = "";
  sums.forEach((s) => {
    const el = document.createElement("div");
    el.className = "summary";
    const time = document.createElement("small");
    time.textContent = new Date(s.created_at).toLocaleString();
    const pre = document.createElement("pre");
    // Render structured summary_data (fall back to entire object if not present)
    const data = s.summary_data !== undefined ? s.summary_data : s;
    try {
      pre.textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      pre.textContent = String(data);
    }
    el.appendChild(time);
    el.appendChild(pre);
    container.appendChild(el);
  });
  document.getElementById("summaries").classList.remove("hidden");
  const btn = document.getElementById("summaries-btn");
  if (btn) btn.textContent = "Hide Summaries";
}

async function toggleSummaries() {
  if (!currentThreadId) return alert("Select a thread first");
  const container = document.getElementById("summaries");
  const btn = document.getElementById("summaries-btn");
  if (!container.classList.contains("hidden")) {
    container.classList.add("hidden");
    if (btn) btn.textContent = "Show Summaries";
    return;
  }
  // Show and populate summaries
  await fetchSummaries();
}

window.addEventListener("load", async () => {
  document
    .getElementById("create-thread-form")
    .addEventListener("submit", createThread);
  document
    .getElementById("message-form")
    .addEventListener("submit", sendMessage);
  document
    .getElementById("summaries-btn")
    .addEventListener("click", toggleSummaries);
  document
    .getElementById("edit-prompt-btn")
    .addEventListener("click", updateSystemPrompt);
  document
    .getElementById("delete-thread-btn")
    .addEventListener("click", deleteThread);
  await fetchModels();
  await fetchThreads();
});

async function updateSystemPrompt() {
  if (!currentThreadId) return alert("Select a thread first");
  const res = await fetch(`${API_BASE}/threads/${currentThreadId}`);
  if (!res.ok) return alert("Failed to load thread");
  const thread = await res.json();
  const newPrompt = prompt("Edit system prompt:", thread.system_prompt || "");
  if (newPrompt === null) return; // cancelled

  const p = await fetch(`${API_BASE}/threads/${currentThreadId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ system_prompt: newPrompt }),
  });
  if (!p.ok) {
    const err = await p.text();
    return alert("Failed to update thread: " + err);
  }
  await loadThreadDetails();
  await fetchThreads();
  alert("System prompt updated");
}

async function deleteThread() {
  if (!currentThreadId) return alert("Select a thread first");
  if (
    !confirm(
      "Delete this thread and all messages/summaries? This cannot be undone.",
    )
  )
    return;
  const res = await fetch(`${API_BASE}/threads/${currentThreadId}`, {
    method: "DELETE",
  });
  if (res.status === 204 || res.ok) {
    currentThreadId = null;
    document.getElementById("thread-title-display").textContent =
      "Select a thread";
    document.getElementById("messages").innerHTML = "";
    document.getElementById("summary-list").innerHTML = "";
    document.getElementById("summaries").classList.add("hidden");
    const btn = document.getElementById("summaries-btn");
    if (btn) btn.textContent = "Show Summaries";
    await fetchThreads();
    alert("Thread deleted");
    return;
  }
  const err = await res.text();
  alert("Failed to delete thread: " + err);
}
