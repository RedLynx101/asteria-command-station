const TAB_ORDER = ["operations", "desk", "fsm", "vision", "debug"];
const DEFAULT_TAB = "operations";
const POLL_INTERVAL_MS = 5000;
const LEASE_RENEW_INTERVAL_MS = 20000;
const LEASE_EXPIRY_BUFFER_MS = 8000;
const HOLDER = {
  holder_id: "local-gui",
  holder_label: "Local GUI",
  holder_kind: "human",
};
const LEASE_GATED_ACTIONS = new Set([
  "run_fsm",
  "unload_fsm",
  "send_text",
  "send_speech",
  "stop_all",
  "capture_image",
  "move",
  "sideways",
  "turn",
  "say",
  "kick",
]);
const AUDIO_MANIFEST = {
  click: "/gui/assets/audio/tab.wav",
  success: "/gui/assets/audio/receive.wav",
  send: "/gui/assets/audio/send.wav",
  warning: "/gui/assets/audio/error.wav",
  alert: "/gui/assets/audio/stop.wav",
};
const SETTINGS_STORAGE = {
  stopAllUnloadsFsm: "asteria.stopAllUnloadsFsm",
  continuousDirectControl: "asteria.continuousDirectControl",
};

const elements = {
  tabButtons: [...document.querySelectorAll(".tab-button")],
  tabPanels: [...document.querySelectorAll(".tab-panel")],
  collapseToggles: [...document.querySelectorAll(".collapse-toggle")],
  actionButtons: [...document.querySelectorAll("[data-action]")],
  tabJumpButtons: [...document.querySelectorAll("[data-tab-jump]")],
  summaryRuntime: document.getElementById("summary-runtime"),
  summaryLease: document.getElementById("summary-lease"),
  summaryHost: document.getElementById("summary-host"),
  summaryBattery: document.getElementById("summary-battery"),
  summaryFsm: document.getElementById("summary-fsm"),
  summaryLastAction: document.getElementById("summary-last-action"),
  latestFeedbackTitle: document.getElementById("latest-feedback-title"),
  latestFeedbackBody: document.getElementById("latest-feedback-body"),
  feedbackTags: document.getElementById("feedback-tags"),
  connectionStatePill: document.getElementById("connection-state-pill"),
  connectionGlance: document.getElementById("connection-glance"),
  connectionProfileSelect: document.getElementById("connection-profile-select"),
  robotHostInput: document.getElementById("robot-host-input"),
  connectionFallbacksInput: document.getElementById("connection-fallbacks-input"),
  moveDistanceInput: document.getElementById("move-distance-input"),
  sidewaysDistanceInput: document.getElementById("sideways-distance-input"),
  turnAngleInput: document.getElementById("turn-angle-input"),
  continuousDirectToggle: document.getElementById("continuous-direct-toggle"),
  sayTextInput: document.getElementById("say-text-input"),
  operationsMetrics: document.getElementById("operations-metrics"),
  operationsImage: document.getElementById("operations-latest-image"),
  operationsImageEmpty: document.getElementById("operations-empty-image"),
  latestResultKind: document.getElementById("latest-result-kind"),
  latestResultCard: document.getElementById("latest-result-card"),
  latestResultTitle: document.getElementById("latest-result-title"),
  latestResultMessage: document.getElementById("latest-result-message"),
  latestResultLinks: document.getElementById("latest-result-links"),
  deskInput: document.getElementById("desk-input"),
  openPromptCount: document.getElementById("open-prompt-count"),
  activityCount: document.getElementById("activity-count"),
  unresolvedPrompts: document.getElementById("unresolved-prompts"),
  recentActivity: document.getElementById("recent-activity"),
  fsmNameInput: document.getElementById("fsm-name-input"),
  fsmEditor: document.getElementById("fsm-editor"),
  fsmEditorStatus: document.getElementById("fsm-editor-status"),
  fsmFileList: document.getElementById("fsm-file-list"),
  fsmSummary: document.getElementById("fsm-summary"),
  fsmEventInput: document.getElementById("fsm-event-input"),
  visionImage: document.getElementById("vision-image"),
  visionImageEmpty: document.getElementById("vision-empty-image"),
  visionTelemetry: document.getElementById("vision-telemetry"),
  commandLog: document.getElementById("command-log"),
  debugDiagnostics: document.getElementById("debug-diagnostics"),
  debugCommandLog: document.getElementById("debug-command-log"),
  debugStatusJson: document.getElementById("debug-status-json"),
  debugStopFsmCheckbox: document.getElementById("debug-stop-fsm-checkbox"),
  debugStopFsmNote: document.getElementById("debug-stop-fsm-note"),
  miniCardTemplate: document.getElementById("mini-card-template"),
};

const state = {
  activeTab: DEFAULT_TAB,
  pollTimer: null,
  status: null,
  selectedFsm: null,
  editorDirty: false,
  lastRenderedFsm: null,
  audio: {},
  leaseKeepaliveId: null,
  leaseRenewInFlight: null,
  stopAllUnloadsFsm: true,
  continuousDirectControl: false,
  activeContinuousControl: null,
  suppressActionClick: new Set(),
};

function setupAudio() {
  for (const [name, path] of Object.entries(AUDIO_MANIFEST)) {
    const audio = new Audio(path);
    audio.preload = "auto";
    state.audio[name] = audio;
  }
}

function playCue(name) {
  const audio = state.audio[name];
  if (!audio) {
    return;
  }
  audio.currentTime = 0;
  audio.play().catch(() => {});
}

function readStoredBoolean(key, fallbackValue) {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw == null) {
      return fallbackValue;
    }
    return raw === "true";
  } catch {
    return fallbackValue;
  }
}

function writeStoredBoolean(key, value) {
  try {
    window.localStorage.setItem(key, String(Boolean(value)));
  } catch {
    // Ignore storage write failures; the GUI still works with in-memory state.
  }
}

function syncStopSettingUi(status = state.status || {}) {
  if (elements.debugStopFsmCheckbox) {
    elements.debugStopFsmCheckbox.checked = Boolean(state.stopAllUnloadsFsm);
  }
  if (!elements.debugStopFsmNote) {
    return;
  }

  const activeFsm = status?.telemetry?.running_fsm_name || "";
  const activeSuffix = activeFsm ? ` Active FSM: ${activeFsm}.` : "";
  elements.debugStopFsmNote.textContent = state.stopAllUnloadsFsm
    ? `Shell Stop All and the D-pad stop button also unload the current FSM before halting motion.${activeSuffix}`
    : `Shell Stop All and the D-pad stop button only halt motion. The active FSM stays loaded until you unload it separately.${activeSuffix}`;
}

function initPreferences() {
  state.stopAllUnloadsFsm = readStoredBoolean(SETTINGS_STORAGE.stopAllUnloadsFsm, true);
  state.continuousDirectControl = readStoredBoolean(SETTINGS_STORAGE.continuousDirectControl, false);
  syncStopSettingUi();
  if (elements.continuousDirectToggle) {
    elements.continuousDirectToggle.checked = Boolean(state.continuousDirectControl);
  }

  elements.debugStopFsmCheckbox?.addEventListener("change", () => {
    state.stopAllUnloadsFsm = Boolean(elements.debugStopFsmCheckbox?.checked);
    writeStoredBoolean(SETTINGS_STORAGE.stopAllUnloadsFsm, state.stopAllUnloadsFsm);
    syncStopSettingUi();
    playCue("click");
  });

  elements.continuousDirectToggle?.addEventListener("change", () => {
    state.continuousDirectControl = Boolean(elements.continuousDirectToggle?.checked);
    writeStoredBoolean(SETTINGS_STORAGE.continuousDirectControl, state.continuousDirectControl);
    if (!state.continuousDirectControl) {
      stopContinuousControl();
    }
    playCue("click");
  });
}

function normalizeTab(hashValue) {
  const candidate = String(hashValue || "").replace(/^#/, "").trim().toLowerCase();
  return TAB_ORDER.includes(candidate) ? candidate : DEFAULT_TAB;
}

function setActiveTab(nextTab, { pushHash = true, focus = false } = {}) {
  const tab = normalizeTab(nextTab);
  state.activeTab = tab;

  for (const button of elements.tabButtons) {
    const isActive = button.dataset.tab === tab;
    button.setAttribute("aria-selected", String(isActive));
    button.id = `tab-${button.dataset.tab}`;
    button.tabIndex = isActive ? 0 : -1;
    button.classList.toggle("is-active", isActive);
    if (isActive && focus) {
      button.focus();
    }
  }

  for (const panel of elements.tabPanels) {
    const isActive = panel.dataset.panel === tab;
    panel.hidden = !isActive;
    panel.classList.toggle("is-active", isActive);
  }

  if (pushHash) {
    history.replaceState(null, "", `#${tab}`);
  }
}

function initTabs() {
  setActiveTab(normalizeTab(window.location.hash), { pushHash: false });
  window.addEventListener("hashchange", () => {
    setActiveTab(normalizeTab(window.location.hash), { pushHash: false });
  });

  elements.tabButtons.forEach((button, index) => {
    button.addEventListener("click", () => {
      setActiveTab(button.dataset.tab);
      playCue("click");
    });

    button.addEventListener("keydown", (event) => {
      let nextIndex = index;
      if (event.key === "ArrowRight") {
        nextIndex = (index + 1) % elements.tabButtons.length;
      }
      if (event.key === "ArrowLeft") {
        nextIndex = (index - 1 + elements.tabButtons.length) % elements.tabButtons.length;
      }
      if (nextIndex !== index) {
        event.preventDefault();
        setActiveTab(elements.tabButtons[nextIndex].dataset.tab, { focus: true });
        playCue("click");
      }
    });
  });

  elements.tabJumpButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveTab(button.dataset.tabJump);
      playCue("click");
    });
  });
}

function initCollapsibles() {
  elements.collapseToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const target = document.getElementById(toggle.dataset.collapseTarget);
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      target.hidden = expanded;
      playCue("click");
    });
  });
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    ...options,
  });

  const raw = await response.text();
  let payload = {};
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch (error) {
      throw new Error(raw);
    }
  }

  if (!response.ok) {
    throw new Error(payload.error || `${response.status} ${response.statusText}`);
  }

  return payload;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function formatBattery(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return `${Math.round(Number(value))}%`;
}

function formatPose(pose) {
  if (!pose || pose.x == null || pose.y == null || pose.heading == null) {
    return "n/a";
  }
  return `${Number(pose.x).toFixed(1)} / ${Number(pose.y).toFixed(1)} / ${Number(pose.heading).toFixed(1)} deg`;
}

function formatTimestamp(value) {
  if (!value) {
    return "n/a";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    month: "short",
    day: "numeric",
  });
}

function leaseExpiresAtMs(lease = {}) {
  const epoch = Number(lease.expires_at_epoch || 0);
  return Number.isFinite(epoch) ? epoch * 1000 : 0;
}

function formatLease(lease = {}) {
  if (!lease.holder_id) {
    return "Unclaimed";
  }
  const expiresMs = leaseExpiresAtMs(lease);
  const ttlSeconds = expiresMs > 0 ? Math.max(0, Math.ceil((expiresMs - Date.now()) / 1000)) : 0;
  const ttlText = ttlSeconds > 0 ? ` (${ttlSeconds}s)` : "";
  return `${lease.holder_label || lease.holder_id}${ttlText}`;
}

function isLocalGuiLease(lease = {}) {
  return lease.holder_id === HOLDER.holder_id && lease.holder_kind === HOLDER.holder_kind;
}

function hasUsableLocalLease(lease = {}) {
  return isLocalGuiLease(lease) && leaseExpiresAtMs(lease) > Date.now() + LEASE_EXPIRY_BUFFER_MS;
}

function stopLeaseKeepalive() {
  if (state.leaseKeepaliveId) {
    clearInterval(state.leaseKeepaliveId);
    state.leaseKeepaliveId = null;
  }
}

async function requestLease({ force = false } = {}) {
  const response = await fetchJson("/api/lease/claim", {
    method: "POST",
    body: JSON.stringify({
      ...HOLDER,
      force,
    }),
  });
  if (state.status) {
    state.status = { ...state.status, lease: response.lease || state.status.lease };
  }
  return response;
}

async function renewLease({ force = false, refresh = false } = {}) {
  if (state.leaseRenewInFlight) {
    return state.leaseRenewInFlight;
  }

  state.leaseRenewInFlight = (async () => {
    const response = await requestLease({ force });
    syncLeaseKeepalive(response.lease || {});
    if (refresh) {
      await pollStatus();
    }
    return response;
  })();

  try {
    return await state.leaseRenewInFlight;
  } finally {
    state.leaseRenewInFlight = null;
  }
}

async function releaseLease() {
  const response = await fetchJson("/api/lease/release", {
    method: "POST",
    body: JSON.stringify({
      holder_id: HOLDER.holder_id,
    }),
  });
  stopLeaseKeepalive();
  if (state.status) {
    state.status = { ...state.status, lease: response.lease || {} };
  }
  await pollStatus();
  return response;
}

function syncLeaseKeepalive(lease = {}) {
  if (!isLocalGuiLease(lease) || leaseExpiresAtMs(lease) <= Date.now()) {
    stopLeaseKeepalive();
    return;
  }

  if (state.leaseKeepaliveId) {
    return;
  }

  state.leaseKeepaliveId = setInterval(async () => {
    try {
      await renewLease({ force: false, refresh: false });
    } catch (error) {
      console.error(error);
      stopLeaseKeepalive();
    }
  }, LEASE_RENEW_INTERVAL_MS);
}

async function ensureLeaseForAction(action) {
  if (!LEASE_GATED_ACTIONS.has(action)) {
    return { ok: true };
  }
  if (hasUsableLocalLease(state.status?.lease || {})) {
    return { ok: true };
  }
  return renewLease({ force: false, refresh: true });
}

function statusRuntimeLabel(status) {
  return status?.telemetry?.connected ? "Connected" : "Idle";
}

function latestImage(status) {
  return status?.latest_image || {};
}

function latestResultKind(lastResult = {}) {
  if (lastResult.warning) {
    return "warning";
  }
  if (lastResult.ok === true) {
    return "success";
  }
  if (lastResult.ok === false) {
    return "error";
  }
  return "info";
}

function valueBox(label, value, severity = "") {
  const node = document.createElement("div");
  node.className = "metric-box";
  if (severity) {
    node.dataset.severity = severity;
  }
  const labelNode = document.createElement("div");
  labelNode.className = "metric-label";
  labelNode.textContent = label;
  const valueNode = document.createElement("div");
  valueNode.className = "metric-value";
  valueNode.textContent = value;
  node.replaceChildren(labelNode, valueNode);
  return node;
}

function miniCard(item, kind = "default") {
  const node = elements.miniCardTemplate.content.firstElementChild.cloneNode(true);
  node.dataset.kind = kind;
  node.querySelector(".mini-title").textContent = item.title || "Untitled";
  node.querySelector(".mini-meta").textContent = item.meta || "";
  node.querySelector(".mini-body").textContent = item.body || "";
  if (item.note) {
    const note = document.createElement("p");
    note.className = "mini-note";
    note.textContent = item.note;
    node.appendChild(note);
  }
  if (item.retryPromptId) {
    const actionRow = document.createElement("div");
    actionRow.className = "mini-actions";
    const retryButton = document.createElement("button");
    retryButton.type = "button";
    retryButton.className = "btn small";
    retryButton.textContent = "Retry Forward";
    retryButton.dataset.promptRetry = item.retryPromptId;
    actionRow.appendChild(retryButton);
    node.appendChild(actionRow);
  }
  return node;
}

function promptForwardState(prompt = {}) {
  if (prompt.status === "resolved") {
    return {
      kind: "ok",
      note: prompt.response ? `Resolved by ${prompt.resolved_label || "Unknown"} at ${formatTimestamp(prompt.resolved_at)}.` : `Resolved by ${prompt.resolved_label || "Unknown"}.`,
      retryPromptId: "",
    };
  }

  if (prompt.forward_status === "sent") {
    return {
      kind: "success",
      note: `Forwarded to OpenClaw${prompt.forwarded_at ? ` at ${formatTimestamp(prompt.forwarded_at)}` : ""}${prompt.bridge_session_key ? ` via ${prompt.bridge_session_key}` : ""}.`,
      retryPromptId: "",
    };
  }

  if (prompt.forward_status === "failed") {
    return {
      kind: "warn",
      note: prompt.forward_error ? `Forward failed: ${prompt.forward_error}` : "Forward failed before OpenClaw acknowledged the prompt.",
      retryPromptId: prompt.id || "",
    };
  }

  if (prompt.forward_status === "retrying") {
    return {
      kind: "pending",
      note: `Retrying direct forward${prompt.bridge_session_key ? ` to ${prompt.bridge_session_key}` : ""}.`,
      retryPromptId: "",
    };
  }

  return {
    kind: "pending",
    note: prompt.forward_error || "Stored locally. OpenClaw will only see this immediately if the direct bridge is enabled.",
    retryPromptId: "",
  };
}

function setImage(imgElement, emptyElement, url) {
  const hasUrl = Boolean(url);
  imgElement.src = hasUrl ? url : "";
  imgElement.hidden = !hasUrl;
  emptyElement.hidden = hasUrl;
}

function artifactUrl(pathValue) {
  if (!pathValue || !state.status?.paths?.asteria_root) {
    return "";
  }
  const asteriaRoot = String(state.status.paths.asteria_root).replace(/\\/g, "/");
  const normalized = String(pathValue).replace(/\\/g, "/");
  const prefix = `${asteriaRoot}/`;
  if (!normalized.toLowerCase().startsWith(prefix.toLowerCase())) {
    return "";
  }
  const relative = normalized.slice(prefix.length);
  return relative.startsWith("artifacts/") ? `/${relative}` : "";
}

function compactPath(pathValue) {
  if (!pathValue) {
    return "n/a";
  }

  const normalized = String(pathValue).replace(/\\/g, "/");
  const repoRoot = String(state.status?.paths?.repo_root || "").replace(/\\/g, "/");
  if (repoRoot) {
    const prefix = `${repoRoot}/`;
    if (normalized.toLowerCase().startsWith(prefix.toLowerCase())) {
      return normalized.slice(prefix.length);
    }
  }

  const segments = normalized.split("/").filter(Boolean);
  if (!segments.length) {
    return normalized;
  }
  return segments.slice(-3).join("/");
}

function renderSummary(status) {
  const telemetry = status?.telemetry || {};
  const lease = status?.lease || {};
  const connection = status?.connection || {};
  const lastResult = status?.last_result || {};
  const image = latestImage(status);

  elements.summaryRuntime.textContent = statusRuntimeLabel(status);
  elements.summaryLease.textContent = formatLease(lease);
  elements.summaryHost.textContent = connection.resolved_host || telemetry.host || "n/a";
  elements.summaryBattery.textContent = formatBattery(telemetry.battery_pct);
  elements.summaryFsm.textContent = telemetry.running_fsm_name
    ? `${telemetry.running_fsm_name}${telemetry.running_fsm_active ? " (running)" : ""}`
    : "Idle";
  elements.summaryLastAction.textContent = lastResult.message || lastResult.error || "Waiting";
  elements.connectionStatePill.textContent = statusRuntimeLabel(status);

  let title = "Ready for operator input";
  let body = "Asteria is waiting for the next daemon status refresh.";
  if (lastResult.error) {
    title = "Recent action needs attention";
    body = lastResult.error;
  } else if (lastResult.message) {
    title = lastResult.message;
    body = telemetry.connected
      ? `Robot session is active on ${telemetry.host || connection.resolved_host || "the selected host"}.`
      : "Daemon is reachable, but the robot is not connected yet.";
  } else if (telemetry.connected) {
    title = "Robot ready for operator input";
    body = `Connected to ${telemetry.host || connection.resolved_host || "the selected host"} with ${connection.connected_runtime_mode || "current"} runtime mode.`;
  }

  const tags = [];
  tags.push(connection.active_profile ? `Profile: ${connection.active_profile}` : "Profile: n/a");
  tags.push(lease.holder_id ? `Lease: ${lease.holder_label || lease.holder_id}` : "Lease: unclaimed");
  if (connection.supports_fsm_runtime === false) {
    tags.push("FSM runtime unavailable");
  }
  if (image.captured_at) {
    tags.push(`Image: ${formatTimestamp(image.captured_at)}`);
  }

  elements.latestFeedbackTitle.textContent = title;
  elements.latestFeedbackBody.textContent = body;
  elements.feedbackTags.replaceChildren(
    ...tags.map((tag) => {
      const chip = document.createElement("span");
      chip.className = "pill accent";
      chip.textContent = tag;
      return chip;
    }),
  );
}

function renderConnection(status) {
  const connection = status?.connection || {};
  const profileSelect = elements.connectionProfileSelect;
  const profiles = safeArray(connection.profiles);

  if (document.activeElement !== profileSelect) {
    profileSelect.innerHTML = "";
    profiles.forEach((profile) => {
      const option = document.createElement("option");
      option.value = profile;
      option.textContent = profile;
      if (profile === connection.active_profile) {
        option.selected = true;
      }
      profileSelect.appendChild(option);
    });
  }

  if (document.activeElement !== elements.robotHostInput) {
    elements.robotHostInput.value = connection.override_target_input || "";
  }

  if (document.activeElement !== elements.connectionFallbacksInput) {
    elements.connectionFallbacksInput.value = safeArray(connection.fallback_hosts).join(", ");
  }

  const glanceEntries = [
    ["Profile target", connection.profile_robot_id ? `${connection.profile_robot_id} (${connection.profile_robot_host || "n/a"})` : connection.profile_robot_host || "n/a"],
    ["Resolved target", connection.resolved_host || "n/a"],
    ["Source", connection.target_source || "n/a"],
    ["Fallbacks", safeArray(connection.fallback_hosts).length ? safeArray(connection.fallback_hosts).join(", ") : "192.168.4.1 only"],
  ];

  elements.connectionGlance.replaceChildren(...glanceEntries.map(([label, value]) => valueBox(label, value)));
}

function renderOperations(status) {
  const telemetry = status?.telemetry || {};
  const connection = status?.connection || {};
  const image = latestImage(status);
  const lastResult = status?.last_result || {};
  const kind = latestResultKind(lastResult);

  renderConnection(status);

  const metricEntries = [
    ["Connected", telemetry.connected ? "Yes" : "No", telemetry.connected ? "success" : "warning"],
    ["Runtime mode", connection.connected_runtime_mode || "idle"],
    ["Pose", formatPose(telemetry.pose)],
    ["FSM support", connection.supports_fsm_runtime === false ? "Disabled" : "Available"],
    ["Safe move", status?.safe_limits?.max_move_mm != null ? `${status.safe_limits.max_move_mm} mm` : "n/a"],
    ["Safe turn", status?.safe_limits?.max_turn_deg != null ? `${status.safe_limits.max_turn_deg} deg` : "n/a"],
  ];
  elements.operationsMetrics.replaceChildren(...metricEntries.map(([label, value, severity]) => valueBox(label, value, severity)));

  setImage(elements.operationsImage, elements.operationsImageEmpty, image.url || "");

  elements.latestResultKind.textContent = kind.toUpperCase();
  elements.latestResultCard.className = `result-card result-${kind}`;
  elements.latestResultTitle.textContent = lastResult.message || lastResult.error || "No recent action";

  const resultDetails = [];
  if (lastResult.error) {
    resultDetails.push(lastResult.error);
  } else {
    resultDetails.push(lastResult.message || "Commands, safety notices, and generated file links will appear here.");
  }
  if (lastResult.warning) {
    resultDetails.push(lastResult.warning);
  }
  if (lastResult.generated_exists === true) {
    resultDetails.push("Generated Python is available.");
  }
  if (lastResult.generated_exists === false) {
    resultDetails.push("FSM source exists but has not been compiled yet.");
  }
  if (image.captured_at) {
    resultDetails.push(`Latest image: ${formatTimestamp(image.captured_at)}.`);
  }
  elements.latestResultMessage.textContent = resultDetails.join(" ");

  const links = [];
  const generatedUrl = artifactUrl(lastResult.generated_py);
  if (generatedUrl) {
    links.push({ label: "Generated FSM", href: generatedUrl });
  }
  const imageUrl = artifactUrl(lastResult.image_path) || image.url || "";
  if (imageUrl) {
    links.push({ label: "Latest image", href: imageUrl });
  }

  elements.latestResultLinks.replaceChildren(
    ...links.map((link) => {
      const anchor = document.createElement("a");
      anchor.href = link.href;
      anchor.textContent = link.label;
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      return anchor;
    }),
  );
}

function renderDesk(status) {
  const prompts = safeArray(status?.prompts)
    .slice()
    .sort((left, right) => {
      const leftResolved = left.status === "resolved";
      const rightResolved = right.status === "resolved";
      if (leftResolved !== rightResolved) {
        return leftResolved ? 1 : -1;
      }
      return String(right.submitted_at || "").localeCompare(String(left.submitted_at || ""));
    });
  const activities = safeArray(status?.activities).slice().reverse();
  const openCount = prompts.filter((item) => item.status !== "resolved").length;

  elements.openPromptCount.textContent = `${openCount} open`;
  elements.activityCount.textContent = `${activities.length} events`;

  if (!prompts.length) {
    elements.unresolvedPrompts.replaceChildren(miniCard({
      title: "No prompts yet",
      meta: "desk",
      body: "Operator prompts and agent responses will appear here.",
    }, "empty"));
  } else {
    elements.unresolvedPrompts.replaceChildren(
      ...prompts.map((prompt) => {
        const forward = promptForwardState(prompt);
        return miniCard({
          title: prompt.status === "resolved" ? "Resolved prompt" : "Open prompt",
          meta: `${prompt.submitted_label || "Unknown"} | ${formatTimestamp(prompt.submitted_at)} | ${prompt.status || "pending"}`,
          body: prompt.response ? `${prompt.text || ""}\n\nResponse: ${prompt.response}` : prompt.text || "",
          note: forward.note,
          retryPromptId: forward.retryPromptId,
        }, forward.kind);
      }),
    );
  }

  if (!activities.length) {
    elements.recentActivity.replaceChildren(miniCard({
      title: "No activity yet",
      meta: "activity",
      body: "Commands, prompts, and lease changes will show up here.",
    }, "empty"));
    return;
  }

  elements.recentActivity.replaceChildren(
    ...activities.map((item) => miniCard({
      title: item.title || "Activity",
      meta: `${item.actor_label || "Unknown"} | ${formatTimestamp(item.timestamp)} | ${item.kind || "event"}`,
      body: item.detail || `${item.related_action || "event"} recorded`,
    }, item.status || "info")),
  );
}

function defaultFsmSource(name) {
  const cleanName = String(name || "asteria_demo").trim() || "asteria_demo";
  const className = cleanName
    .split(/[^A-Za-z0-9]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join("") || "AsteriaDemo";
  return [
    "from aim_fsm import *",
    "",
    "",
    `class ${className}(StateMachineProgram):`,
    " $setup{",
    ` Say(\"${cleanName} ready\") =C=> Forward(120) =C=> Turn(90) =C=> Say(\"${cleanName} complete\")`,
    " }",
    "",
  ].join("\n");
}

function ensureSelectedFsm(status) {
  const files = safeArray(status?.fsm_files);
  if (!state.selectedFsm && files[0]) {
    state.selectedFsm = files[0].name;
  }
  return files.find((item) => item.name === state.selectedFsm) || files[0] || null;
}

function selectFsm(name) {
  state.selectedFsm = name;
  state.editorDirty = false;
  state.lastRenderedFsm = null;
  renderFSM(state.status || {});
}

function renderFSM(status) {
  const files = safeArray(status?.fsm_files);
  const selected = ensureSelectedFsm(status);

  elements.fsmFileList.replaceChildren(
    ...files.map((file) => {
      const button = document.createElement("button");
      button.className = `btn fsm-file-button${selected?.name === file.name ? " is-active" : ""}`;
      button.type = "button";
      button.textContent = file.name || "FSM";
      button.addEventListener("click", () => {
        selectFsm(file.name);
        playCue("click");
      });
      return button;
    }),
  );

  if (selected) {
    elements.fsmNameInput.value = selected.name || elements.fsmNameInput.value;
    const shouldHydrateEditor = !state.editorDirty || state.lastRenderedFsm !== selected.name;
    if (shouldHydrateEditor && document.activeElement !== elements.fsmEditor) {
      elements.fsmEditor.value = selected.content || defaultFsmSource(selected.name);
    }
    state.lastRenderedFsm = selected.name;
    elements.fsmEditorStatus.textContent = state.editorDirty
      ? "Draft changed"
      : selected.generated_exists ? "Compiled" : "Source only";

    elements.fsmSummary.replaceChildren(
      valueBox("Selected FSM", selected.name || "n/a"),
      valueBox("Generated file", compactPath(selected.generated_py)),
      valueBox("Compiled", selected.generated_exists ? "Yes" : "No"),
      valueBox("Runtime state", status?.telemetry?.running_fsm_name ? (status.telemetry.running_fsm_active ? "Running" : "Loaded") : "Idle"),
    );
    return;
  }

  if (!elements.fsmEditor.value) {
    elements.fsmEditor.value = defaultFsmSource(elements.fsmNameInput.value);
  }
  elements.fsmEditorStatus.textContent = state.editorDirty ? "Draft changed" : "No FSM selected";
  elements.fsmSummary.replaceChildren(
    valueBox("Selected FSM", "n/a"),
    valueBox("Generated file", "n/a"),
    valueBox("Compiled", "No"),
    valueBox("Runtime state", "Idle"),
  );
}

function renderVision(status) {
  const telemetry = status?.telemetry || {};
  const image = latestImage(status);
  setImage(elements.visionImage, elements.visionImageEmpty, image.url || "");

  const snapshot = [
    ["Battery", formatBattery(telemetry.battery_pct)],
    ["Pose", formatPose(telemetry.pose)],
    ["Host", telemetry.host || status?.connection?.resolved_host || "n/a"],
    ["Lease", status?.lease?.holder_label || "Unclaimed"],
    ["Last capture", image.captured_at ? formatTimestamp(image.captured_at) : "n/a"],
    ["Last error", telemetry.last_error || "None"],
  ];
  elements.visionTelemetry.replaceChildren(...snapshot.map(([label, value]) => valueBox(label, value)));

  const commands = safeArray(status?.recent_commands).slice().reverse();
  if (!commands.length) {
    elements.commandLog.replaceChildren(miniCard({
      title: "No recent commands",
      meta: "vision",
      body: "Recent command traffic will appear here after the daemon receives actions.",
    }, "empty"));
    return;
  }

  elements.commandLog.replaceChildren(
    ...commands.map((entry) => miniCard({
      title: entry.action || "command",
      meta: formatTimestamp(entry.timestamp),
      body: JSON.stringify(entry.payload || {}, null, 2),
    }, "info")),
  );
}

function renderDebug(status) {
  const diagnostics = status?.connection?.diagnostics || { timestamp: null, items: [] };
  elements.debugDiagnostics.textContent = JSON.stringify(diagnostics, null, 2);
  elements.debugCommandLog.textContent = JSON.stringify(safeArray(status?.recent_commands), null, 2);
  elements.debugStatusJson.textContent = JSON.stringify(status || {}, null, 2);
  syncStopSettingUi(status);
}

function renderAll(status) {
  const payload = status || {};
  renderSummary(payload);
  renderOperations(payload);
  renderDesk(payload);
  renderFSM(payload);
  renderVision(payload);
  renderDebug(payload);
  syncLeaseKeepalive(payload.lease || {});
}

function renderStatus(status) {
  state.status = status || {};
  renderAll(state.status);
}

function clientError(message) {
  const nextStatus = {
    ...(state.status || {}),
    last_result: {
      ok: false,
      error: message,
      message,
      timestamp: new Date().toISOString(),
    },
  };
  renderStatus(nextStatus);
}

async function pollStatus() {
  const payload = await fetchJson("/api/status");
  renderStatus(payload);
  return payload;
}

async function sendAction(action, payload = {}, options = {}) {
  const leaseRequired = options.leaseRequired ?? LEASE_GATED_ACTIONS.has(action);
  if (leaseRequired) {
    const leaseResult = await ensureLeaseForAction(action);
    if (leaseResult?.ok === false) {
      renderStatus({
        ...(state.status || {}),
        ...(leaseResult.status || {}),
        lease: leaseResult.lease || state.status?.lease || {},
        last_result: {
          ok: false,
          error: leaseResult.error || "control lease unavailable",
          message: leaseResult.error || "control lease unavailable",
          timestamp: new Date().toISOString(),
        },
      });
      playCue("warning");
      return leaseResult;
    }
  }

  const response = await fetchJson("/api/command", {
    method: "POST",
    body: JSON.stringify({
      action,
      ...HOLDER,
      ...payload,
    }),
  });

  renderStatus(response);
  playCue(response.ok === false || response.warning ? "warning" : (action === "stop_all" ? "alert" : "success"));

  if (options.refreshAfter) {
    await pollStatus();
  }

  return response;
}

function continuousControlPayload(action) {
  switch (action) {
    case "moveForward":
      return { action: "drive_at", payload: { angle_deg: 0, speed_pct: 55 } };
    case "moveBackward":
      return { action: "drive_at", payload: { angle_deg: 180, speed_pct: 55 } };
    case "strafeLeft":
      return { action: "drive_at", payload: { angle_deg: -90, speed_pct: 52 } };
    case "strafeRight":
      return { action: "drive_at", payload: { angle_deg: 90, speed_pct: 52 } };
    case "turnLeft":
      return { action: "turn_at", payload: { turn_rate_pct: -40 } };
    case "turnRight":
      return { action: "turn_at", payload: { turn_rate_pct: 40 } };
    default:
      return null;
  }
}

async function startContinuousControl(button) {
  const control = continuousControlPayload(button?.dataset?.action);
  if (!control) {
    return null;
  }
  state.activeContinuousControl = {
    action: button.dataset.action,
    pointerId: button.dataset.pointerId || "",
  };
  button.classList.add("is-active");
  return sendAction(control.action, control.payload);
}

async function stopContinuousControl() {
  if (!state.activeContinuousControl) {
    return null;
  }
  const activeAction = state.activeContinuousControl.action;
  state.activeContinuousControl = null;
  document.querySelectorAll("[data-hold-control].is-active").forEach((button) => {
    button.classList.remove("is-active");
    delete button.dataset.pointerId;
  });
  const response = await sendAction("stop_all", { stop_fsm: false });
  state.suppressActionClick.add(activeAction);
  window.setTimeout(() => state.suppressActionClick.delete(activeAction), 250);
  return response;
}

function normalizedFsmName() {
  const raw = String(elements.fsmNameInput.value || state.selectedFsm || "asteria_demo").trim();
  const cleaned = raw.replace(/[^A-Za-z0-9_]+/g, "_").replace(/^_+|_+$/g, "");
  return cleaned || "asteria_demo";
}

function currentFsmName() {
  const name = normalizedFsmName();
  elements.fsmNameInput.value = name;
  return name;
}

function parseFallbackHosts() {
  return elements.connectionFallbacksInput.value
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function getConnectionPayload() {
  const payload = {
    profile: elements.connectionProfileSelect.value || "",
    robot_target: elements.robotHostInput.value.trim(),
    fallback_hosts: parseFallbackHosts(),
  };
  return payload;
}

async function saveCurrentFsm() {
  const name = currentFsmName();
  const response = await sendAction("create_fsm", {
    name,
    content: elements.fsmEditor.value,
  });
  state.editorDirty = false;
  state.selectedFsm = response.name || name;
  state.lastRenderedFsm = null;
  renderFSM(state.status || response);
  return response;
}

async function compileCurrentFsm() {
  const saved = await saveCurrentFsm();
  const name = saved.name || currentFsmName();
  const response = await sendAction("compile_fsm", { name });
  state.selectedFsm = name;
  return response;
}

const actionHandlers = {
  async claimLease() {
    const response = await renewLease({ force: true, refresh: true });
    playCue(response.ok === false ? "warning" : "success");
    return response;
  },
  async releaseLease() {
    const response = await releaseLease();
    playCue(response.ok === false ? "warning" : "success");
    return response;
  },
  async refreshStatus() {
    playCue("click");
    return pollStatus();
  },
  async stopAll() {
    return sendAction("stop_all", {
      stop_fsm: state.stopAllUnloadsFsm,
    });
  },
  async disconnect() {
    return sendAction("disconnect", {}, { leaseRequired: false });
  },
  async applyConnection() {
    return sendAction("set_connection_config", getConnectionPayload(), { leaseRequired: false });
  },
  async saveProfileTarget() {
    const robotTarget = elements.robotHostInput.value.trim();
    if (!robotTarget) {
      throw new Error("Robot target is required");
    }
    return sendAction("save_profile_robot_target", {
      profile: elements.connectionProfileSelect.value || "",
      robot_target: robotTarget,
    }, { leaseRequired: false });
  },
  async clearOverride() {
    return sendAction("set_connection_config", {
      profile: elements.connectionProfileSelect.value || "",
      clear_override: true,
      fallback_hosts: parseFallbackHosts(),
    }, { leaseRequired: false });
  },
  async connect() {
    return sendAction("connect", {}, { leaseRequired: false });
  },
  async reconnect() {
    return sendAction("reconnect", {}, { leaseRequired: false });
  },
  async diagnoseConnection() {
    return sendAction("diagnose_connection", {
      host: elements.robotHostInput.value.trim(),
    }, { leaseRequired: false });
  },
  async moveForward() {
    return sendAction("move", {
      distance_mm: Number(elements.moveDistanceInput.value || 150),
      angle_deg: 0,
    });
  },
  async moveBackward() {
    return sendAction("move", {
      distance_mm: -Number(elements.moveDistanceInput.value || 150),
      angle_deg: 0,
    });
  },
  async turnLeft() {
    return sendAction("turn", {
      angle_deg: -Number(elements.turnAngleInput.value || 45),
    });
  },
  async turnRight() {
    return sendAction("turn", {
      angle_deg: Number(elements.turnAngleInput.value || 45),
    });
  },
  async strafeLeft() {
    return sendAction("sideways", {
      distance_mm: -Number(elements.sidewaysDistanceInput.value || 120),
    });
  },
  async strafeRight() {
    return sendAction("sideways", {
      distance_mm: Number(elements.sidewaysDistanceInput.value || 120),
    });
  },
  async kickSoft() {
    return sendAction("kick", { style: "soft" });
  },
  async kickMedium() {
    return sendAction("kick", { style: "medium" });
  },
  async kickHard() {
    return sendAction("kick", { style: "hard" });
  },
  async captureImage() {
    return sendAction("capture_image", {}, { refreshAfter: true });
  },
  async sendSay() {
    const text = elements.sayTextInput.value.trim();
    if (!text) {
      throw new Error("Display text is required");
    }
    return sendAction("say", { text });
  },
  async sendPrompt() {
    const text = elements.deskInput.value.trim();
    if (!text) {
      throw new Error("Prompt text is required");
    }
    const response = await sendAction("submit_prompt", { text }, { leaseRequired: false });
    elements.deskInput.value = "";
    return response;
  },
  async logNote() {
    const message = elements.deskInput.value.trim();
    if (!message) {
      throw new Error("Note text is required");
    }
    const response = await sendAction("log_note", {
      title: "Operator note",
      message,
      level: "info",
    }, { leaseRequired: false });
    elements.deskInput.value = "";
    return response;
  },
  async newTemplate() {
    state.selectedFsm = null;
    state.lastRenderedFsm = null;
    state.editorDirty = true;
    elements.fsmEditor.value = defaultFsmSource(currentFsmName());
    renderFSM(state.status || {});
    playCue("click");
    return { ok: true };
  },
  async saveFsm() {
    return saveCurrentFsm();
  },
  async compileFsm() {
    return compileCurrentFsm();
  },
  async runFsm() {
    const compiled = await compileCurrentFsm();
    const module = compiled.name || currentFsmName();
    return sendAction("run_fsm", { module });
  },
  async unloadFsm() {
    return sendAction("unload_fsm");
  },
  async sendFsmText() {
    const message = elements.fsmEventInput.value.trim();
    if (!message) {
      throw new Error("FSM text is required");
    }
    return sendAction("send_text", { message });
  },
  async sendFsmSpeech() {
    const message = elements.fsmEventInput.value.trim();
    if (!message) {
      throw new Error("FSM speech is required");
    }
    return sendAction("send_speech", { message });
  },
};

function initActions() {
  elements.actionButtons.forEach((button) => {
    button.addEventListener("pointerdown", async (event) => {
      if (!state.continuousDirectControl || !button.dataset.holdControl) {
        return;
      }
      event.preventDefault();
      button.dataset.pointerId = String(event.pointerId);
      button.setPointerCapture?.(event.pointerId);
      try {
        await startContinuousControl(button);
      } catch (error) {
        console.error(error);
        clientError(error instanceof Error ? error.message : String(error));
        playCue("warning");
      }
    });

    const releaseContinuous = async (event) => {
      if (!state.continuousDirectControl || !button.dataset.holdControl || !state.activeContinuousControl) {
        return;
      }
      const pointerId = String(event.pointerId ?? "");
      if (button.dataset.pointerId && pointerId && button.dataset.pointerId !== pointerId) {
        return;
      }
      event.preventDefault();
      try {
        await stopContinuousControl();
      } catch (error) {
        console.error(error);
        clientError(error instanceof Error ? error.message : String(error));
        playCue("warning");
      }
    };

    button.addEventListener("pointerup", releaseContinuous);
    button.addEventListener("pointercancel", releaseContinuous);

    button.addEventListener("click", async (event) => {
      if (state.suppressActionClick.has(button.dataset.action)) {
        event.preventDefault();
        return;
      }
      if (state.continuousDirectControl && button.dataset.holdControl) {
        event.preventDefault();
        return;
      }
      const handler = actionHandlers[button.dataset.action];
      if (!handler) {
        return;
      }
      try {
        await handler();
      } catch (error) {
        console.error(error);
        clientError(error instanceof Error ? error.message : String(error));
        playCue("warning");
      }
    });
  });

  window.addEventListener("pointerup", async () => {
    if (!state.activeContinuousControl) {
      return;
    }
    try {
      await stopContinuousControl();
    } catch (error) {
      console.error(error);
      clientError(error instanceof Error ? error.message : String(error));
      playCue("warning");
    }
  });

  elements.fsmEditor.addEventListener("input", () => {
    state.editorDirty = true;
    elements.fsmEditorStatus.textContent = "Draft changed";
  });

  elements.fsmNameInput.addEventListener("change", () => {
    elements.fsmNameInput.value = normalizedFsmName();
  });

  elements.deskInput.addEventListener("keydown", async (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      await actionHandlers.sendPrompt();
    }
  });

  elements.unresolvedPrompts.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const promptId = target.dataset.promptRetry;
    if (!promptId) {
      return;
    }
    playCue("click");
    await sendAction("retry_prompt_forward", { prompt_id: promptId }, { leaseRequired: false });
  });

  elements.sayTextInput.addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      await actionHandlers.sendSay();
    }
  });

  elements.fsmEventInput.addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      await actionHandlers.sendFsmText();
    }
  });
}

function startPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
  }
  pollStatus().catch((error) => {
    console.error(error);
    clientError(error instanceof Error ? error.message : String(error));
  });
  state.pollTimer = setInterval(async () => {
    try {
      await pollStatus();
    } catch (error) {
      console.error(error);
      clientError(error instanceof Error ? error.message : String(error));
      stopLeaseKeepalive();
    }
  }, POLL_INTERVAL_MS);
}

function init() {
  setupAudio();
  initPreferences();
  initTabs();
  initCollapsibles();
  initActions();
  startPolling();
  window.addEventListener("beforeunload", () => {
    stopLeaseKeepalive();
  });
}

init();
