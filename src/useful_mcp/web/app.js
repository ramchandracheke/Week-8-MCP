const loginPanel = document.querySelector("#login-panel");
const chatPanel = document.querySelector("#chat-panel");
const loginForm = document.querySelector("#login-form");
const chatForm = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message");
const conversation = document.querySelector("#conversation");
const suggestions = document.querySelector("#suggestions");
const loginError = document.querySelector("#login-error");
const toast = document.querySelector("#toast");
let csrfToken = "";
let history = [];
let busy = false;

async function api(path, body = null) {
  const options = { method: body === null ? "GET" : "POST", headers: {} };
  if (body !== null) {
    options.headers["Content-Type"] = "application/json";
    options.headers["X-CSRF-Token"] = csrfToken;
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

function setSignedIn(signedIn) {
  loginPanel.hidden = signedIn;
  chatPanel.hidden = !signedIn;
  if (signedIn) messageInput.focus();
}

function addMessage(role, content, pending = false) {
  const node = document.createElement("div");
  node.className = `message ${role}${pending ? " pending" : ""}`;
  node.textContent = content;
  conversation.append(node);
  node.scrollIntoView({ block: "nearest", behavior: "smooth" });
  return node;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 3500);
}

async function refreshSession() {
  try {
    const session = await api("/api/session");
    csrfToken = session.csrf_token;
    setSignedIn(session.authenticated);
  } catch (error) {
    loginPanel.hidden = false;
    loginError.textContent = error.message;
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.textContent = "";
  const form = new FormData(loginForm);
  try {
    const result = await api("/api/login", {
      username: form.get("username"),
      password: form.get("password"),
    });
    csrfToken = result.csrf_token;
    loginForm.reset();
    setSignedIn(true);
  } catch (error) {
    loginError.textContent = error.message;
  }
});

document.querySelector("#logout-button").addEventListener("click", async () => {
  try {
    await api("/api/logout", {});
    history = [];
    conversation.replaceChildren();
    setSignedIn(false);
    await refreshSession();
  } catch (error) {
    showToast(error.message);
  }
});

async function sendMessage(text) {
  if (busy || !text.trim()) return;
  busy = true;
  suggestions.hidden = true;
  document.querySelector(".send-button").disabled = true;
  messageInput.value = "";
  history.push({ role: "user", content: text.trim() });
  addMessage("user", text.trim());
  const pending = addMessage("assistant", "Thinking…", true);
  try {
    const result = await api("/api/chat", { messages: history.slice(-16) });
    pending.classList.remove("pending");
    pending.textContent = result.answer;
    history.push({ role: "assistant", content: result.answer });
  } catch (error) {
    pending.remove();
    history.pop();
    showToast(error.message);
  } finally {
    busy = false;
    document.querySelector(".send-button").disabled = false;
    messageInput.focus();
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(messageInput.value);
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

suggestions.addEventListener("click", (event) => {
  const button = event.target.closest("[data-prompt]");
  if (button) sendMessage(button.dataset.prompt);
});

refreshSession();
