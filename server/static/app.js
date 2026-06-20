const state = {
  host: "127.0.0.1",
  port: 8000,
  lobbyId: null,
  lobbyName: "",
  token: null,
  playerId: null,
  joinedExistingLobby: false,
  pollTimer: null,
  stateTimer: null,
  browserTimer: null,
  browserLobbies: [],
  hand: [],
  phase: "init",
  trumpSuit: null,
  playableCards: [],
  roundScore: { Vit: 0, Tit: 0 },
  lastWinner: null,
  highlightUntil: 0,
  currentTurn: 0,
  maxMeldValue: null,
  maxMeldSuits: "",
  maxMeldRequested: false,
  maxMeldReady: false,
  pendingSuit: null,
  autoSuitSent: false,
  recentTrick: [],
  recentTrickExpire: 0,
  recentTrickKey: "",
  recentTrickSeenAt: 0,
  clearingTrickKey: "",
  optimisticCards: {},
  latestPlayers: [],
  latestTableSlots: [],
  seatCards: {},
  scheduledCards: {},
  cardClearTimers: {},
  tableAnimationUntil: 0,
  playableRevealAt: 0,
  playableLayoutKey: "",
  playableRevealTimer: null,
  playableButtonStates: {},
  meldCandidateCards: [],
  teamFaces: { Vit: null, Tit: null },
  lastRoundWinnerTeam: null,
  lastRoundResultKey: 0,
  lastRoundResultKind: null,
  seenCelebrationKey: "",
  seenMatchCelebrationKey: "",
  celebrationTimer: null,
  trickCount: 0,
  lastTrickWinningCard: null,
  lastTrickSignature: "",
};

const WIN_FACES = ["😁", "😎", "🤩", "🎉", "✨", "😸", "🥳", "🕺", "🙌", "😺"];
const LOSE_FACES = ["😵", "😞", "😬", "🙈", "😿", "😕", "🥲", "😣", "😩", "😶"];

const joinSection = document.getElementById("join-section");
const welcomeStage = document.getElementById("welcome-stage");
const welcomeCopy = document.getElementById("welcome-copy");
const lobbySection = document.getElementById("lobby-section");
const gameSection = document.getElementById("game-section");
const joinForm = document.getElementById("join-form");
const joinGrid = document.querySelector(".join-grid");
const hostInput = document.getElementById("host-input");
const portInput = document.getElementById("port-input");
const nameInput = document.getElementById("name-input");
const lobbyNameInput = document.getElementById("lobby-name-input");
const browserActions = document.getElementById("browser-actions");
const browserPanel = document.getElementById("browser-panel");
const refreshLobbiesButton = document.getElementById("refresh-lobbies-button");
const lobbyBrowserList = document.getElementById("lobby-browser-list");
const lobbyTitle = document.getElementById("lobby-title");
const lobbySubtitle = document.getElementById("lobby-subtitle");
const lobbySeats = document.getElementById("lobby-seats");
const lobbyUpdates = document.getElementById("lobby-updates");
const lobbyChatForm = document.getElementById("lobby-chat-form");
const lobbyChatInput = document.getElementById("lobby-chat-input");
const lobbyLeaveButton = document.getElementById("lobby-leave-button");
const lobbyBotSelect = document.getElementById("lobby-bot-select");
const lobbyBotsButton = document.getElementById("lobby-bots-button");
const lobbyStartButton = document.getElementById("lobby-start-button");
const playerLabel = document.getElementById("player-label");
const scoreboard = document.getElementById("scoreboard");
const trumpDisplay = document.getElementById("trump-display");
const gameExitButton = document.getElementById("game-exit-button");
const celebrationOverlay = document.getElementById("celebration-overlay");
const roundScore = document.getElementById("round-score");
const tableCards = document.getElementById("table-cards");
const playedCardsLayer = document.getElementById("played-cards-layer");
const updatesLog = document.getElementById("updates-log");
const commandForm = document.getElementById("command-form");
const commandInput = document.getElementById("command-input");
const historyBody = document.getElementById("history-body");
const cardButtons = document.getElementById("card-buttons");
const meldActions = document.getElementById("meld-actions");
const meldInfo = document.getElementById("meld-info");
const meldButtons = document.getElementById("meld-buttons");
const dealActions = document.getElementById("deal-actions");
const splitSelect = document.getElementById("split-select");
const splitButton = document.getElementById("split-button");
const bankaButton = document.getElementById("banka-button");

populateSplitSelect();

const SUIT_SYMBOLS = {
  C: "♣",
  D: "♦",
  H: "♥",
  S: "♠",
};

const TABLE_CARD_POSITIONS = {
  top: { x: 50, y: 33 },
  left: { x: 35, y: 50 },
  right: { x: 65, y: 50 },
  bottom: { x: 50, y: 67 },
};

const PERMANENT_TRUMPS = ["QC", "QS", "JC", "JS", "JH", "JD"];

function baseUrl() {
  return `http://${state.host}:${state.port}`;
}

function fallbackPlayerName() {
  const names = ["Guest", "Dealer", "Spade", "Trump", "Joker", "North", "East", "West", "South", "Ace"];
  const suffix = Math.floor(100 + Math.random() * 900);
  return `${names[Math.floor(Math.random() * names.length)]} ${suffix}`;
}

function fallbackLobbyName() {
  const names = ["Harbor Table", "Moon Table", "North Table", "King's Table", "Lantern Table", "Fjord Table"];
  return names[Math.floor(Math.random() * names.length)];
}

async function joinTable(event) {
  event.preventDefault();
  if (state.token) {
    appendUpdate("Leave your current room before creating another table.");
    return;
  }
  const name = nameInput.value.trim() || fallbackPlayerName();
  const lobbyName = lobbyNameInput.value.trim() || fallbackLobbyName();
  nameInput.value = name;
  lobbyNameInput.value = lobbyName;
  state.host = hostInput.value.trim() || "127.0.0.1";
  state.port = parseInt(portInput.value, 10) || 8000;

  try {
    const response = await fetch(`${baseUrl()}/lobbies`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: lobbyName }),
    });
    if (!response.ok) {
      const detail = await response.json();
      appendUpdate(`Create failed: ${detail.detail || response.statusText}`);
      return;
    }
    const data = await response.json();
    await joinLobby(data.lobby_id, name, false);
  } catch (error) {
    appendUpdate(`Join failed: ${error}`);
  }
}

async function joinLobby(lobbyId, nameOverride = null, joinedExisting = true) {
  if (state.token) {
    appendUpdate("Leave your current room before joining another table.");
    return;
  }
  const name = (nameOverride ?? nameInput.value).trim() || fallbackPlayerName();
  nameInput.value = name;
  state.host = hostInput.value.trim() || "127.0.0.1";
  state.port = parseInt(portInput.value, 10) || 8000;
  try {
    const response = await fetch(`${baseUrl()}/join`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, lobby_id: lobbyId }),
    });
    if (!response.ok) {
      const detail = await response.json();
      appendUpdate(`Join failed: ${detail.detail || response.statusText}`);
      return;
    }
    const data = await response.json();
    state.lobbyId = data.lobby_id;
    state.lobbyName = data.lobby_name;
    state.token = data.token;
    state.playerId = data.player_id;
    state.joinedExistingLobby = joinedExisting;
    playerLabel.textContent = `Player ${data.player_id} (${name || "Guest"})`;
    appendUpdate(data.message);
    joinSection.classList.add("hidden");
    lobbySection.classList.toggle("hidden", joinedExisting);
    gameSection.classList.toggle("hidden", !joinedExisting);
    startPolling();
  } catch (error) {
    appendUpdate(`Join failed: ${error}`);
  }
}

async function fetchLobbies() {
  if (state.token) return;
  state.host = hostInput.value.trim() || "127.0.0.1";
  state.port = parseInt(portInput.value, 10) || 8000;
  try {
    const response = await fetch(`${baseUrl()}/lobbies`);
    if (!response.ok) {
      appendUpdate(`Lobby list failed: ${response.statusText}`);
      return;
    }
    const data = await response.json();
    state.browserLobbies = data.lobbies || [];
    renderLobbyBrowser();
  } catch (error) {
    appendUpdate(`Lobby list failed: ${error}`);
  }
}

async function leaveLobby() {
  if (!state.token) return;
  try {
    const response = await fetch(`${baseUrl()}/leave`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: state.token }),
    });
    if (!response.ok) {
      const detail = await response.json();
      appendUpdate(`Leave failed: ${detail.detail || response.statusText}`);
      return;
    }
    resetClientSession();
  } catch (error) {
    appendUpdate(`Leave failed: ${error}`);
  }
}

function startPolling() {
  stopPolling();
  state.pollTimer = setInterval(fetchUpdates, 700);
  state.stateTimer = setInterval(fetchState, 560);
  fetchUpdates();
  fetchState();
  renderMeldActions();
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  if (state.stateTimer) {
    clearInterval(state.stateTimer);
    state.stateTimer = null;
  }
  if (state.browserTimer) {
    clearInterval(state.browserTimer);
    state.browserTimer = null;
  }
}

function startBrowserPolling() {
  if (state.browserTimer) {
    clearInterval(state.browserTimer);
  }
  state.browserTimer = setInterval(fetchLobbies, 2500);
  fetchLobbies();
}

function resetClientSession() {
  stopPolling();
  state.lobbyId = null;
  state.lobbyName = "";
  state.token = null;
  state.playerId = null;
  state.joinedExistingLobby = false;
  state.browserLobbies = [];
  state.hand = [];
  state.phase = "init";
  state.trumpSuit = null;
  state.playableCards = [];
  state.roundScore = { Vit: 0, Tit: 0 };
  state.lastWinner = null;
  state.highlightUntil = 0;
  state.currentTurn = 0;
  state.maxMeldValue = null;
  state.maxMeldSuits = "";
  state.maxMeldRequested = false;
  state.maxMeldReady = false;
  state.pendingSuit = null;
  state.autoSuitSent = false;
  state.recentTrick = [];
  state.recentTrickExpire = 0;
  state.recentTrickKey = "";
  state.recentTrickSeenAt = 0;
  state.clearingTrickKey = "";
  state.optimisticCards = {};
  state.latestPlayers = [];
  state.latestTableSlots = [];
  state.seatCards = {};
  state.scheduledCards = {};
  Object.values(state.cardClearTimers).forEach((timerId) => clearTimeout(timerId));
  state.cardClearTimers = {};
  state.tableAnimationUntil = 0;
  state.playableRevealAt = 0;
  state.playableLayoutKey = "";
  if (state.playableRevealTimer) {
    clearTimeout(state.playableRevealTimer);
    state.playableRevealTimer = null;
  }
  state.playableButtonStates = {};
  state.teamFaces = { Vit: null, Tit: null };
  state.lastRoundWinnerTeam = null;
  state.lastRoundResultKey = 0;
  state.lastRoundResultKind = null;
  state.seenCelebrationKey = "";
  state.seenMatchCelebrationKey = "";
  if (state.celebrationTimer) {
    clearTimeout(state.celebrationTimer);
    state.celebrationTimer = null;
  }
  if (celebrationOverlay) {
    celebrationOverlay.className = "hidden";
    celebrationOverlay.innerHTML = "";
  }
  state.trickCount = 0;
  state.lastTrickWinningCard = null;
  state.lastTrickSignature = "";
  playedCardsLayer.innerHTML = "";
  tableCards.innerHTML = "";
  cardButtons.innerHTML = "";
  updatesLog.textContent = "";
  if (lobbyUpdates) {
    lobbyUpdates.textContent = "";
  }
  renderScreen("init");
  renderLobbyBrowser();
  startBrowserPolling();
}

async function fetchUpdates() {
  if (!state.token) return;
  try {
    const response = await fetch(`${baseUrl()}/updates?token=${state.token}`);
    if (!response.ok) {
      if (response.status === 401 || response.status === 410) {
        appendUpdate("Session expired. Returning to the lobby browser.");
        resetClientSession();
      }
      return;
    }
    const data = await response.json();
    const message = data.message;
    if (message && message !== "No new updates.") {
      appendUpdate(message);
      if (message.includes("Received 8 cards.")) {
        sendCommand("show");
      }
    }
  } catch (error) {
    appendUpdate(`Update error: ${error}`);
  }
}

async function fetchState() {
  if (!state.token) return;
  try {
    const response = await fetch(`${baseUrl()}/state?token=${state.token}`);
    if (!response.ok) {
      if (response.status === 401 || response.status === 410) {
        appendUpdate("Session expired. Returning to the lobby browser.");
        resetClientSession();
      }
      return;
    }
    const data = await response.json();
    const previousPhase = state.phase;
    state.playerId = data.player_id;
    state.lobbyId = data.lobby_id;
    state.lobbyName = data.lobby_name;
    state.phase = data.phase;
    state.trumpSuit = data.trump;
    state.playableCards = data.playable_cards || [];
    state.roundScore = data.round_score || { Vit: 0, Tit: 0 };
    state.lastRoundWinnerTeam = data.last_round_winner_team || null;
    state.lastRoundResultKey = Number(data.last_round_result_key || 0);
    state.lastRoundResultKind = data.last_round_result_kind || null;
    state.trickCount = Number(data.trick_count || 0);
    state.lastWinner = data.last_winner;
    state.lastTrickWinningCard = data.last_trick_winning_card || null;
    state.highlightUntil = Number(data.highlight_until || 0);
    state.currentTurn = data.current_turn;
    state.recentTrick = data.recent_trick || [];
    state.recentTrickExpire = Number(data.recent_trick_expire || 0);
    state.lastTrickSignature = recentTrickKey(state.recentTrick);
    updateRecentTrickTiming(state.recentTrick);

    updatePhaseState(data, previousPhase);
    renderScreen(data.phase);
    renderLobby(data);

    renderScoreboard(data.scoreboard);
    renderRoundHistory(data.round_history || []);
    renderRoundScore(state.roundScore);
    renderPlayers(data.players, data.current_turn);
    const me = (data.players || []).find((player) => player.id === state.playerId);
    playerLabel.textContent = me
      ? `Player ${state.playerId} (${me.name})`
      : `Player ${state.playerId}`;
    renderTableCards(data.table_cards);
    renderTableLayout(data.players, data.table_slots, data.current_turn);
    renderTrump(data.trump);
    state.hand = sortHand(data.hand || [], data.trump);
    schedulePlayableReveal(data);
    renderCardButtons();
    maybeRequestMaxMeld(data);
    maybeSendSuit(data);
    renderMeldActions();
    renderDealActions(data);
    maybeShowMatchCelebration(data.scoreboard, data.phase);
    maybeShowRoundCelebration();
  } catch (error) {
    appendUpdate(`State error: ${error}`);
  }
}

function maybeShowMatchCelebration(board, phase) {
  if (!celebrationOverlay || phase !== "end" || !board) return;
  const winners = Object.entries(board)
    .filter(([, score]) => Number(score) <= 0)
    .map(([team]) => team);
  if (!winners.length) return;
  const winnerTeam = winners[0];
  const myTeam = teamForPlayer(state.playerId || 1);
  const celebrationKey = `match|${state.lastRoundResultKey}|${winnerTeam}|${myTeam}`;
  if (state.seenMatchCelebrationKey === celebrationKey) return;
  state.seenMatchCelebrationKey = celebrationKey;
  if (state.celebrationTimer) {
    clearTimeout(state.celebrationTimer);
  }
  if (myTeam === winnerTeam) {
    celebrationOverlay.className = "celebration-overlay match-win";
    celebrationOverlay.innerHTML = `
      <div class="firework firework-a"></div>
      <div class="firework firework-b"></div>
      <div class="firework firework-c"></div>
      <div class="firework firework-d"></div>
      <div class="firework firework-e"></div>
      <div class="firework firework-f"></div>
      <div class="card-rain rain-a">🂡</div>
      <div class="card-rain rain-b">🂮</div>
      <div class="card-rain rain-c">🃁</div>
      <div class="card-rain rain-d">🃍</div>
      <div class="celebration-banner match-banner">${winnerTeam} Wins The Rubber</div>
    `;
  } else {
    celebrationOverlay.className = "celebration-overlay match-loss";
    celebrationOverlay.innerHTML = `
      <div class="loss-cloud">☁️</div>
      <div class="sad-emoji giant-sad">😭</div>
      <div class="celebration-banner loss-banner">${winnerTeam} Got There First</div>
    `;
  }
  state.celebrationTimer = setTimeout(() => {
    celebrationOverlay.className = "hidden";
    celebrationOverlay.innerHTML = "";
    state.celebrationTimer = null;
  }, 4000);
}

function maybeShowRoundCelebration() {
  if (!celebrationOverlay) return;
  const winnerTeam = state.lastRoundWinnerTeam;
  const kind = state.lastRoundResultKind;
  if (!winnerTeam || kind !== "declarer_sweep") return;
  const myTeam = teamForPlayer(state.playerId || 1);
  const celebrationKey = `${state.lastRoundResultKey}|${winnerTeam}|${kind}|${myTeam}`;
  if (state.seenCelebrationKey === celebrationKey) return;
  state.seenCelebrationKey = celebrationKey;
  if (state.celebrationTimer) {
    clearTimeout(state.celebrationTimer);
  }
  if (myTeam === winnerTeam) {
    celebrationOverlay.className = "celebration-overlay fireworks";
    celebrationOverlay.innerHTML = `
      <div class="firework firework-a"></div>
      <div class="firework firework-b"></div>
      <div class="firework firework-c"></div>
      <div class="firework firework-d"></div>
      <div class="celebration-banner">Perfect Round</div>
    `;
  } else {
    celebrationOverlay.className = "celebration-overlay sad-loss";
    celebrationOverlay.innerHTML = `<div class="sad-emoji">😭</div>`;
  }
  state.celebrationTimer = setTimeout(() => {
    celebrationOverlay.className = "hidden";
    celebrationOverlay.innerHTML = "";
    state.celebrationTimer = null;
  }, 3000);
}

async function sendCommand(command, options = {}) {
  if (!state.token) return;
  const { silent = false, onResult } = options;
  try {
    const response = await fetch(`${baseUrl()}/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: state.token, command }),
    });
    if (!response.ok) {
      const detail = await response.json();
      const message = detail.detail || response.statusText;
      appendUpdate(`Command failed: ${message}`);
      if (onResult) onResult(null, message);
      return;
    }
    const data = await response.json();
    const msg = data.message ?? "";
    if (msg && msg.trim() && !silent) {
      appendUpdate(msg);
    }
    if (onResult) onResult(msg.trim(), null);
  } catch (error) {
    appendUpdate(`Command error: ${error}`);
    if (onResult) onResult(null, error);
  }
}

function appendUpdate(text) {
  if (!text) return;
  const trimmed = text.trim();
  if (!trimmed) return;
  const existing = updatesLog.textContent.split("\n").filter(Boolean);
  existing.push(trimmed);
  const nextText = existing.slice(-30).join("\n");
  updatesLog.textContent = nextText;
  updatesLog.scrollTop = updatesLog.scrollHeight;
  if (lobbyUpdates) {
    lobbyUpdates.textContent = nextText;
    lobbyUpdates.scrollTop = lobbyUpdates.scrollHeight;
  }
}

function setSectionVisible(element, visible, displayValue = "") {
  if (!element) return;
  element.hidden = !visible;
  element.classList.toggle("hidden", !visible);
  element.style.display = visible ? displayValue : "none";
}

function renderScreen(phase) {
  const inLobby = phase === "lobby" || phase === "init";
  const showBrowser = !state.token;
  const showLobby = state.token && inLobby && !state.joinedExistingLobby;
  const showGame = state.token && (!inLobby || state.joinedExistingLobby);
  setSectionVisible(joinSection, showBrowser);
  if (welcomeStage) {
    setSectionVisible(welcomeStage, showBrowser);
  }
  if (welcomeCopy) {
    setSectionVisible(welcomeCopy, showBrowser, "flex");
  }
  if (joinForm) {
    setSectionVisible(joinForm, showBrowser);
  }
  if (joinGrid) {
    setSectionVisible(joinGrid, showBrowser, "grid");
  }
  if (browserActions) {
    setSectionVisible(browserActions, showBrowser, "grid");
  }
  if (browserPanel) {
    setSectionVisible(browserPanel, showBrowser, "grid");
  }
  setSectionVisible(lobbySection, showLobby);
  setSectionVisible(gameSection, showGame, "grid");
  if (gameExitButton) {
    gameExitButton.classList.toggle("hidden", phase !== "end");
  }
}

function renderLobby(data) {
  if (!lobbySection || data.phase !== "lobby" || state.joinedExistingLobby) return;
  const players = Array.isArray(data.players) ? data.players : [];
  lobbyTitle.textContent = `${data.lobby_name || state.lobbyName || "Lobby"} ${players.length}/${data.max_players}`;
  if (data.can_start) {
    lobbySubtitle.textContent = state.playerId === data.host_id
      ? "All seats are filled. Start the round when ready."
      : "All seats are filled. Waiting for the host.";
  } else {
    lobbySubtitle.textContent = `${Math.max(0, data.max_players - players.length)} open seat(s).`;
  }
  const byId = new Map(players.map((player) => [player.id, player]));
  lobbySeats.innerHTML = "";
  for (let seat = 1; seat <= data.max_players; seat += 1) {
    const player = byId.get(seat);
    const seatCard = document.createElement("div");
    seatCard.className = `lobby-seat${player ? " occupied" : ""}${seat === data.host_id ? " host" : ""}`;
    seatCard.innerHTML = player
      ? `<span class="lobby-seat-id">Seat ${seat}</span><strong>${player.name}</strong><span class="lobby-seat-status">${player.ok ? "Ready" : "Quiet"}</span>`
      : `<span class="lobby-seat-id">Seat ${seat}</span><strong>Open Seat</strong><span class="lobby-seat-status">Waiting</span>`;
    lobbySeats.appendChild(seatCard);
  }
  lobbyBotsButton.disabled = players.length >= data.max_players;
  lobbyStartButton.disabled = !(data.can_start && state.playerId === data.host_id);
}

function renderLobbyBrowser() {
  if (!lobbyBrowserList) return;
  if (!state.browserLobbies.length) {
    lobbyBrowserList.innerHTML = `<div class="browser-empty">No open tables yet.</div>`;
    return;
  }
  lobbyBrowserList.innerHTML = "";
  state.browserLobbies.forEach((lobby) => {
    const card = document.createElement("div");
    card.className = "browser-lobby-card";
    const status = lobby.phase === "lobby" || lobby.phase === "init" ? "Waiting Room" : "In Game";
    card.innerHTML = `
      <div class="browser-lobby-meta">
        <strong>${lobby.name}</strong>
        <span>${status}</span>
      </div>
      <div class="browser-lobby-meta">
        <span>${lobby.player_count}/${lobby.max_players} seated</span>
        <button type="button" ${lobby.can_join ? "" : "disabled"}>Join</button>
      </div>
    `;
    const button = card.querySelector("button");
    if (button) {
      button.addEventListener("click", () => joinLobby(lobby.lobby_id, null, true));
    }
    lobbyBrowserList.appendChild(card);
  });
}

function renderScoreboard(board) {
  if (!board) return;
  scoreboard.innerHTML = `
    <span class="team">
      <span class="team-name">Vit</span>
      <strong>${board.Vit ?? "--"}</strong>
    </span>
    <span class="team">
      <span class="team-name">Tit</span>
      <strong>${board.Tit ?? "--"}</strong>
    </span>
  `;
}

function renderRoundScore(board) {
  if (!roundScore) return;
  const vit = board?.Vit ?? 0;
  const tit = board?.Tit ?? 0;
  roundScore.innerHTML = `
    <span>Round</span>
    <strong>Vit ${vit}</strong>
    <strong>Tit ${tit}</strong>
  `;
}

function renderRoundHistory(history) {
  if (!historyBody) return;
  const rows = Array.isArray(history) ? history : [];
  if (!rows.length) {
    historyBody.innerHTML = `<tr><td colspan="5" class="history-empty">No rounds yet.</td></tr>`;
    return;
  }
  historyBody.innerHTML = rows
    .map(
      (row) => {
        const vit = Number(row.vit ?? 0);
        const tit = Number(row.tit ?? 0);
        const margin = Math.abs(vit - tit);
        const tone = margin >= 60 ? "blowout" : margin >= 30 ? "strong" : margin >= 10 ? "edge" : "tight";
        const vitClass = vit > tit ? `round-win ${tone}` : vit < tit ? "round-loss" : "round-draw";
        const titClass = tit > vit ? `round-win ${tone}` : tit < vit ? "round-loss" : "round-draw";
        return `
        <tr>
          <td>${row.round ?? ""}</td>
          <td class="${vitClass}">${vit}</td>
          <td class="${titClass}">${tit}</td>
          <td>${row.game_vit ?? ""}</td>
          <td>${row.game_tit ?? ""}</td>
        </tr>
      `;
      },
    )
    .join("");
}

function renderTrump(trump) {
  const leadSuit = currentLeadSuit();
  if (!trump) {
    trumpDisplay.textContent = `Trump: —  Lead: ${leadSuit ? formatSuitBadge(leadSuit) : "—"}`;
    return;
  }
  const mapping = {
    C: "♣ Kleyvari",
    D: "♦ Rútari",
    H: "♥ Hjartari",
    S: "♠ Spaðari",
  };
  trumpDisplay.textContent = `Trump: ${mapping[trump] || trump}  Lead: ${leadSuit ? formatSuitBadge(leadSuit) : "—"}`;
}

function renderPlayers(players, currentTurn) {
  players = Array.isArray(players) ? players : [];
  state.latestPlayers = players;
}

function renderTableCards(cards) {
  tableCards.innerHTML = "";
  const message = document.createElement("span");
  message.className = "table-message";
  const now = Date.now() / 1000;
  const recentKey = recentTrickKey(state.recentTrick);
  const collectingPreviousTrick =
    state.recentTrick &&
    state.recentTrick.length &&
    now < state.recentTrickExpire &&
    recentKey !== state.clearingTrickKey;
  if (collectingPreviousTrick) {
    message.textContent = "Collecting trick...";
    tableCards.appendChild(message);
    return;
  }
  if (!cards || !cards.length) {
    message.textContent = "No cards on the table.";
    tableCards.appendChild(message);
    return;
  }
  message.textContent = `Trick in progress (${cards.length}/4)`;
  tableCards.appendChild(message);
  renderWinningCardBadge();
}

function updateRecentTrickTiming(recentTrick) {
  const key = recentTrickKey(recentTrick);
  if (!key) {
    state.recentTrickKey = "";
    state.recentTrickSeenAt = 0;
    state.clearingTrickKey = "";
    return;
  }
  if (key !== state.recentTrickKey) {
    state.recentTrickKey = key;
    state.recentTrickSeenAt = 0;
    state.clearingTrickKey = "";
  }
  const wallNow = Date.now() / 1000;
  if (
    state.clearingTrickKey &&
    key === state.clearingTrickKey &&
    wallNow >= state.recentTrickExpire
  ) {
    state.clearingTrickKey = "";
    state.recentTrickSeenAt = 0;
  }
}

function recentTrickKey(recentTrick) {
  if (!Array.isArray(recentTrick) || !recentTrick.length) return "";
  return recentTrick
    .map(({ id, card }) => `${id}:${card}`)
    .join("|");
}

function renderCardButtons() {
  cardButtons.innerHTML = "";
  if (!state.hand.length) {
    const note = document.createElement("span");
    note.textContent = "No cards available.";
    cardButtons.appendChild(note);
    return;
  }
  const playable = new Set(state.playableCards || []);
  const meldCandidates = new Set(state.meldCandidateCards || []);
  const isMyTurn = state.currentTurn === state.playerId;
  const tableSettled = isTableSettledForPlayableReveal();
  const playableReady = performance.now() >= state.playableRevealAt && tableSettled;
  if (isMyTurn && playable.size && !playableReady && !state.playableRevealTimer) {
    state.playableRevealTimer = setTimeout(tryRevealPlayableCards, 40);
  }
  const { trumps, others } = partitionHand(state.hand, state.trumpSuit);
  const orderedCards = [...trumps, ...others];
  orderedCards.forEach((card, index) => {
    if (index === trumps.length && trumps.length && others.length) {
      const divider = document.createElement("span");
      divider.className = "hand-divider";
      divider.setAttribute("aria-hidden", "true");
      cardButtons.appendChild(divider);
    }
    const btn = document.createElement("button");
    btn.type = "button";
    const { text, red } = formatCardEmoji(card);
    btn.textContent = text;
    if (red) {
      btn.classList.add("red");
    }
    const canPlay = isMyTurn && playable.has(card) && playableReady;
    const isMeldCandidate = state.phase === "declaration" && meldCandidates.has(card);
    btn.classList.toggle("playable", canPlay);
    btn.classList.toggle("meld-candidate", isMeldCandidate);
    const wasPlayable = Boolean(state.playableButtonStates[card]);
    if (canPlay && !wasPlayable) {
      btn.classList.add("lift-in");
    }
    state.playableButtonStates[card] = canPlay;
    btn.disabled = !(isMyTurn && playable.has(card) && playableReady);
    btn.addEventListener("click", () => playCard(card));
    cardButtons.appendChild(btn);
  });
  Object.keys(state.playableButtonStates).forEach((card) => {
    if (!state.hand.includes(card)) {
      delete state.playableButtonStates[card];
    }
  });
}

function partitionHand(hand, trump) {
  const trumps = [];
  const others = [];
  hand.forEach((card) => {
    if (isTrumpCard(card.toUpperCase(), (trump || "").toUpperCase())) {
      trumps.push(card);
    } else {
      others.push(card);
    }
  });
  return { trumps, others };
}

function schedulePlayableReveal(data) {
  if (data.phase !== "first_card" && data.phase !== "play") {
    state.playableRevealAt = Number.POSITIVE_INFINITY;
    state.playableButtonStates = {};
    if (state.playableRevealTimer) {
      clearTimeout(state.playableRevealTimer);
      state.playableRevealTimer = null;
    }
    return;
  }
  const tableSignature = [
    data.phase || "",
    data.current_turn ?? 0,
    (data.table_slots || []).map(({ id, card }) => `${id}:${card}`).join("|"),
    (data.playable_cards || []).join(","),
  ].join("|");
  if (tableSignature === state.playableLayoutKey) return;
  state.playableLayoutKey = tableSignature;
  const isMyTurn = (data.current_turn ?? 0) === state.playerId;
  const hasPlayableCards = Array.isArray(data.playable_cards) && data.playable_cards.length > 0;
  if (!isMyTurn || !hasPlayableCards) {
    state.playableRevealAt = Number.POSITIVE_INFINITY;
    state.playableButtonStates = {};
    if (state.playableRevealTimer) {
      clearTimeout(state.playableRevealTimer);
      state.playableRevealTimer = null;
    }
    return;
  }
  const tableCardCount = Array.isArray(data.table_slots) ? data.table_slots.length : 0;
  const fallbackDelay = tableCardCount > 0 ? (tableCardCount - 1) * 260 + 280 : 180;
  const revealAt = Math.max(performance.now() + fallbackDelay, state.tableAnimationUntil);
  state.playableRevealAt = revealAt;
  state.playableButtonStates = {};
  if (state.playableRevealTimer) {
    clearTimeout(state.playableRevealTimer);
  }
  state.playableRevealTimer = setTimeout(tryRevealPlayableCards, Math.max(10, Math.ceil(revealAt - performance.now()) + 10));
}

function tryRevealPlayableCards() {
  const now = performance.now();
  if (!isTableSettledForPlayableReveal(now)) {
    const waitFor = Math.max(20, Math.ceil(state.tableAnimationUntil - now) + 20);
    state.playableRevealTimer = setTimeout(tryRevealPlayableCards, waitFor);
    return;
  }
  state.playableRevealTimer = null;
  renderCardButtons();
}

function isTableSettledForPlayableReveal(now = performance.now()) {
  const hasPendingCards = Object.values(state.scheduledCards).some(Boolean);
  if (hasPendingCards) return false;
  if (now < state.tableAnimationUntil) return false;
  const wallNow = Date.now() / 1000;
  const recentKey = recentTrickKey(state.recentTrick);
  const collectingRecentTrick =
    Array.isArray(state.recentTrick) &&
    state.recentTrick.length &&
    wallNow < state.recentTrickExpire &&
    recentKey !== state.clearingTrickKey;
  if (collectingRecentTrick) return false;
  if (state.clearingTrickKey && wallNow >= state.recentTrickExpire) {
    state.clearingTrickKey = "";
    state.recentTrickSeenAt = 0;
  }
  if (state.clearingTrickKey) return false;
  if (
    playedCardsLayer.querySelector(
      ".played-card.slide-out, .played-card.fly-to-winner, .played-card.trick-clearing",
    )
  ) {
    return false;
  }
  const visibleCards = playedCardsLayer.querySelectorAll(".played-card").length;
  const liveCards = Array.isArray(state.latestTableSlots) ? state.latestTableSlots.length : 0;
  if (visibleCards > liveCards) return false;
  return true;
}

function playCard(card) {
  if (!card) return;
  sendCommand(`P ${card}`, {
    onResult: (msg) => {
      const normalized = (msg || "").trim();
      if (!normalized || normalized === "OK") {
        state.optimisticCards[state.playerId] = card;
        state.playableCards = [];
        state.playableButtonStates = {};
        const idx = state.hand.indexOf(card);
        if (idx !== -1) {
          state.hand.splice(idx, 1);
        }
        renderCardButtons();
        renderTableLayout(state.latestPlayers || [], state.latestTableSlots || [], state.currentTurn);
      }
    },
  });
}

function renderTableLayout(players, tableSlotsData, currentTurn) {
  players = Array.isArray(players) ? players : [];
  tableSlotsData = tableSlotsData || [];
  state.latestPlayers = players;
  state.latestTableSlots = tableSlotsData;

  const playersById = {};
  players.forEach((p) => {
    playersById[p.id] = p;
  });

  const positionMap = computeSeatOrder(playersById);
  const now = Date.now() / 1000;
  const recentKey = recentTrickKey(state.recentTrick);
  const hasRecentTrick =
    Array.isArray(state.recentTrick) &&
    state.recentTrick.length &&
    now < state.recentTrickExpire &&
    recentKey !== state.clearingTrickKey;
  const hasLiveCards = tableSlotsData.length > 0 && !hasRecentTrick;

  if (hasLiveCards) {
    tableSlotsData.forEach(({ id, card }, index) => {
      schedulePlayedCard(id, card, positionForSeat(positionMap, id), index);
      delete state.optimisticCards[id];
    });
  }

  if (hasRecentTrick) {
    state.optimisticCards = {};
    state.lastTrickSignature = recentKey;
    state.recentTrick.forEach(({ id, card }, index) => {
      schedulePlayedCard(id, card, positionForSeat(positionMap, id), index);
    });

    const allRecentCardsVisible = state.recentTrick.every(
      ({ id, card }) => state.seatCards[String(id)] === card,
    );
    if (allRecentCardsVisible && !state.recentTrickSeenAt) {
      state.recentTrickSeenAt = performance.now();
    }

    const holdSeconds = state.recentTrickSeenAt
      ? (performance.now() - state.recentTrickSeenAt) / 1000
      : 0;
    if (allRecentCardsVisible && holdSeconds >= 2) {
      collectTrickToWinner(state.recentTrick, positionMap);
      state.clearingTrickKey = recentKey;
      state.optimisticCards = {};
      state.scheduledCards = {};
    }
  }

  if (!hasLiveCards && !hasRecentTrick && !state.clearingTrickKey) {
    clearTableCards(positionMap);
    state.optimisticCards = {};
    state.scheduledCards = {};
  }

  if (
    state.clearingTrickKey &&
    now >= state.recentTrickExpire &&
    !playedCardsLayer.querySelector(".played-card")
  ) {
    state.clearingTrickKey = "";
    state.recentTrickSeenAt = 0;
  }

  ["top", "left", "right", "bottom"].forEach((pos) => {
    const seat = positionMap[pos] ?? null;
    const slot = document.querySelector(`.table-slot[data-pos="${pos}"]`);
    if (!slot) return;
    const nameEl = slot.querySelector(".name");
    let resultEl = slot.querySelector(".seat-result");
    let indicatorEl = slot.querySelector(".seat-indicator");
    if (!indicatorEl) {
      indicatorEl = document.createElement("span");
      indicatorEl.className = "seat-indicator";
      slot.insertBefore(indicatorEl, nameEl);
    }
    if (!resultEl) {
      resultEl = document.createElement("span");
      resultEl.className = "seat-result";
      slot.appendChild(resultEl);
    }
    const player = seat ? playersById[seat] : null;
    const nameText = player ? player.name : `Seat ${seat}`;
    nameEl.textContent = nameText;
    indicatorEl.classList.toggle("offline", Boolean(player && !player.ok));
    indicatorEl.classList.toggle("empty", !player);
    indicatorEl.title = player
      ? `${player.ok ? "Connected" : "Waiting for update"}${typeof player.ping === "number" ? ` (${player.ping.toFixed(1)}s)` : ""}`
      : "Empty seat";
    if (player && player.id === currentTurn) {
      nameEl.classList.add("turn");
    } else {
      nameEl.classList.remove("turn");
    }
    if (player && player.id === state.playerId) {
      nameEl.classList.add("me");
    } else {
      nameEl.classList.remove("me");
    }
    const team = player ? teamForPlayer(player.id) : null;
    const winnerTeam = state.trickCount >= 1 ? null : (state.lastRoundWinnerTeam || null);
    const loserTeam = winnerTeam ? (winnerTeam === "Vit" ? "Tit" : "Vit") : null;
    if (winnerTeam) {
      state.teamFaces[winnerTeam] = pickFace(WIN_FACES, state.lastRoundResultKey + "|win|" + winnerTeam);
    }
    if (loserTeam) {
      state.teamFaces[loserTeam] = pickFace(LOSE_FACES, state.lastRoundResultKey + "|lose|" + loserTeam);
    }
    resultEl.textContent = team && state.teamFaces[team] && winnerTeam ? state.teamFaces[team] : "";
    resultEl.classList.toggle("winner", team === winnerTeam);
    resultEl.classList.toggle("loser", team === loserTeam);
    const highlight = Boolean(player && player.id === state.lastWinner && now < state.highlightUntil);
    updateSeatHighlight(seat, highlight);
  });

  renderWinningCardBadge();
}

function schedulePlayedCard(seat, card, pos, orderIndex) {
  if (!seat || !card) return;
  const seatKey = String(seat);
  if (state.seatCards[seatKey] === card || state.scheduledCards[seatKey] === card) return;
  state.scheduledCards[seatKey] = card;
  const delay = Math.max(0, orderIndex) * 260;
  state.tableAnimationUntil = Math.max(state.tableAnimationUntil, performance.now() + delay + 260);
  setTimeout(() => {
    if (state.scheduledCards[seatKey] !== card) return;
    state.scheduledCards[seatKey] = "";
    setSeatCard(seat, card, pos);
  }, delay);
}

function collectTrickToWinner(trickCards, positionMap) {
  state.tableAnimationUntil = Math.max(state.tableAnimationUntil, performance.now() + 380);
  const winnerPos = positionForSeat(positionMap, state.lastWinner);
  trickCards.forEach(({ id, card }) => {
    const pos = positionForSeat(positionMap, id);
    setSeatCard(id, card, pos, { flyTo: winnerPos });
  });
}

function clearTableCards(positionMap) {
  if (Object.values(state.seatCards).some(Boolean)) {
    state.tableAnimationUntil = Math.max(state.tableAnimationUntil, performance.now() + 320);
  }
  Object.entries(state.seatCards).forEach(([seatKey, card]) => {
    if (!card) return;
    const seat = Number(seatKey);
    const pos = positionForSeat(positionMap, seat);
    setSeatCard(seat, null, pos);
  });
}

function updateSeatHighlight(seat, highlight) {
  if (!seat) return;
  const cardEl = getPlayedCardElement(String(seat), null, false);
  if (!cardEl) return;
  cardEl.classList.toggle("highlight", highlight);
}

function renderWinningCardBadge() {
  const cardsWithEls = Array.from(playedCardsLayer.querySelectorAll(".played-card"));
  cardsWithEls.forEach((cardEl) => {
    cardEl.classList.remove("winning-card", "last-winning-card");
  });

  const liveWinner = currentWinningPlay();
  if (liveWinner && state.currentTurn === state.playerId) {
    cardsWithEls.forEach((cardEl) => {
      if (
        cardEl.dataset.seat === String(liveWinner.id) &&
        cardEl.textContent === formatCardEmoji(liveWinner.card).text
      ) {
        cardEl.classList.add("winning-card");
      }
    });
    return;
  }

  const winningCard = state.lastTrickWinningCard;
  if (!winningCard || !state.lastWinner) return;
  cardsWithEls.forEach((cardEl) => {
    if (
      cardEl.dataset.seat === String(state.lastWinner) &&
      cardEl.textContent === formatCardEmoji(winningCard).text
    ) {
      cardEl.classList.add("last-winning-card");
    }
  });
}

function currentLeadSuit() {
  const first = (state.latestTableSlots || [])[0];
  if (!first || !first.card || first.card.length < 2) return null;
  return first.card[1].toUpperCase();
}

function formatSuitBadge(suit) {
  const upper = suit.toUpperCase();
  const labels = {
    C: "♣",
    D: "♦",
    H: "♥",
    S: "♠",
  };
  return labels[upper] || upper;
}

function currentWinningPlay() {
  const slots = Array.isArray(state.latestTableSlots) ? state.latestTableSlots : [];
  const trump = (state.trumpSuit || "").toUpperCase();
  if (!slots.length || !trump) return null;
  const leadCard = slots[0].card;
  const leadSuit = leadCard[1].toUpperCase();
  let best = slots[0];

  for (let index = 1; index < slots.length; index += 1) {
    const candidate = slots[index];
    if (compareCards(candidate.card, best.card, leadSuit, trump) > 0) {
      best = candidate;
    }
  }
  return best;
}

function compareCards(leftCard, rightCard, leadSuit, trump) {
  const leftStrength = cardStrength(leftCard, leadSuit, trump);
  const rightStrength = cardStrength(rightCard, leadSuit, trump);
  if (leftStrength[0] !== rightStrength[0]) {
    return leftStrength[0] - rightStrength[0];
  }
  return leftStrength[1] - rightStrength[1];
}

function cardStrength(card, leadSuit, trump) {
  if (!card || card.length < 2) return [0, 0];
  const upper = card.toUpperCase();
  const suit = upper[1];
  if (PERMANENT_TRUMPS.includes(upper)) {
    return [3, PERMANENT_TRUMPS.length - PERMANENT_TRUMPS.indexOf(upper)];
  }
  if (isTrumpCard(upper, trump)) {
    return [2, cardValueRank(upper[0])];
  }
  if (suit === leadSuit) {
    return [1, cardValueRank(upper[0])];
  }
  return [0, cardValueRank(upper[0])];
}

function isTrumpCard(card, trump) {
  return card[1] === trump || PERMANENT_TRUMPS.includes(card);
}

function cardValueRank(value) {
  if (value === "A") return 14;
  const mapping = { K: 13, Q: 12, J: 11, T: 10, 9: 9, 8: 8, 7: 7 };
  return mapping[value] || 0;
}

function teamForPlayer(playerId) {
  return playerId % 2 === 1 ? "Vit" : "Tit";
}

function pickFace(pool, seed) {
  if (!pool.length) return "";
  const text = String(seed || "");
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return pool[hash % pool.length];
}

function setSeatCard(seat, card, pos, options = {}) {
  const seatKey = seat ? String(seat) : pos;
  const previousCard = state.seatCards[seatKey] || "";
  const { highlight = false, clearing = false, flyTo = null } = options;
  const cardEl = getPlayedCardElement(seatKey, pos, Boolean(card || previousCard));
  if (!cardEl) return;

  if (state.cardClearTimers[seatKey]) {
    clearTimeout(state.cardClearTimers[seatKey]);
    state.cardClearTimers[seatKey] = null;
  }

  cardEl.classList.remove(
    "red",
    "highlight",
    "slide-in",
    "slide-out",
    "trick-clearing",
    "from-top",
    "from-left",
    "from-right",
    "from-bottom",
    "to-top",
    "to-left",
    "to-right",
    "to-bottom",
    "fly-to-winner",
  );
  cardEl.style.removeProperty("--fly-x");
  cardEl.style.removeProperty("--fly-y");

  if (flyTo && card) {
    setFlyTarget(cardEl, pos, flyTo);
    cardEl.classList.add("slide-out", "fly-to-winner");
    state.tableAnimationUntil = Math.max(state.tableAnimationUntil, performance.now() + 380);
    state.seatCards[seatKey] = "";
    state.cardClearTimers[seatKey] = setTimeout(() => {
      if (!state.seatCards[seatKey]) {
        cardEl.remove();
      }
    }, 360);
    return;
  }

  if (!card) {
    if (previousCard) {
      cardEl.classList.add("slide-out", `to-${pos}`);
      state.tableAnimationUntil = Math.max(state.tableAnimationUntil, performance.now() + 320);
      state.cardClearTimers[seatKey] = setTimeout(() => {
        if (!state.seatCards[seatKey]) {
          cardEl.remove();
        }
      }, 300);
    } else {
      cardEl.remove();
    }
    state.seatCards[seatKey] = "";
    return;
  }

  const { text, red } = formatCardEmoji(card);
  if (previousCard !== card) {
    cardEl.textContent = text;
    cardEl.classList.add("slide-in", `from-${pos}`);
  } else {
    cardEl.textContent = text;
  }
  if (red) {
    cardEl.classList.add("red");
  }
  if (highlight) {
    cardEl.classList.add("highlight");
  }
  if (clearing) {
    cardEl.classList.add("trick-clearing");
  }
  state.seatCards[seatKey] = card;
}

function getPlayedCardElement(seatKey, pos, create = true) {
  let cardEl = playedCardsLayer.querySelector(`[data-seat="${seatKey}"]`);
  if (!cardEl && create) {
    cardEl = document.createElement("div");
    cardEl.className = "card played-card";
    cardEl.dataset.seat = seatKey;
    playedCardsLayer.appendChild(cardEl);
  }
  if (cardEl && pos) {
    cardEl.dataset.pos = pos;
  }
  return cardEl;
}

function positionForSeat(positionMap, seat) {
  if (!seat) return "top";
  return Object.entries(positionMap).find(([, mappedSeat]) => mappedSeat === seat)?.[0] || "top";
}

function setFlyTarget(cardEl, fromPos, toPos) {
  const layerRect = playedCardsLayer.getBoundingClientRect();
  const from = TABLE_CARD_POSITIONS[fromPos] || TABLE_CARD_POSITIONS.top;
  const to = TABLE_CARD_POSITIONS[toPos] || TABLE_CARD_POSITIONS.top;
  const dx = ((to.x - from.x) / 100) * layerRect.width;
  const dy = ((to.y - from.y) / 100) * layerRect.height;
  cardEl.style.setProperty("--fly-x", `${dx}px`);
  cardEl.style.setProperty("--fly-y", `${dy}px`);
}

function computeSeatOrder(playersById) {
  const seats = [1, 2, 3, 4];
  let start = state.playerId && playersById[state.playerId] ? state.playerId : null;
  if (!start) {
    for (const seat of seats) {
      if (playersById[seat]) {
        start = seat;
        break;
      }
    }
  }
  if (!start) start = state.playerId || 1;

  const result = { top: null, left: null, right: null, bottom: null };
  seats.forEach((seat) => {
    const offset = ((seat - start) % 4 + 4) % 4;
    if (offset === 0) result.bottom = seat;
    else if (offset === 1) result.left = seat;
    else if (offset === 2) result.top = seat;
    else result.right = seat;
  });

  if (result.top === null) result.top = ((start + 1) % 4) + 1;
  if (result.left === null) result.left = (start % 4) + 1;
  if (result.right === null) result.right = ((start + 2) % 4) + 1;
  if (result.bottom === null) result.bottom = start;

  return result;
}

function formatCardEmoji(card) {
  if (!card || card.length < 2) return { text: card, red: false };
  const value = card[0].toUpperCase();
  const suit = card[1].toUpperCase();
  const baseMap = {
    S: 0x1f0a0,
    H: 0x1f0b0,
    D: 0x1f0c0,
    C: 0x1f0d0,
  };
  const valueMap = {
    A: 0x1,
    K: 0xe,
    Q: 0xd,
    J: 0xb,
    T: 0xa,
    9: 0x9,
    8: 0x8,
    7: 0x7,
  };
  const base = baseMap[suit];
  const offset = valueMap[value];
  const red = suit === "H" || suit === "D";
  if (base && offset !== undefined) {
    return { text: String.fromCodePoint(base + offset), red };
  }
  return { text: `${value}${cardSuitToSymbol(suit)}`, red };
}

function sortHand(hand, trump) {
  if (!hand || !hand.length) return [];
  const valueOrder = ["A", "K", "Q", "J", "T", "9", "8", "7"];
  const baseSuitOrder = ["S", "H", "D", "C"];
  const normalizedTrump = trump ? trump.toUpperCase() : null;
  const suitOrder = normalizedTrump
    ? [normalizedTrump, ...baseSuitOrder.filter((s) => s !== normalizedTrump)]
    : baseSuitOrder;

  return [...hand].sort((a, b) => {
    const upperA = a.toUpperCase();
    const upperB = b.toUpperCase();
    const isTrumpA = normalizedTrump ? isTrumpCard(upperA, normalizedTrump) : false;
    const isTrumpB = normalizedTrump ? isTrumpCard(upperB, normalizedTrump) : false;
    if (isTrumpA && isTrumpB) {
      const strengthA = cardStrength(upperA, normalizedTrump, normalizedTrump);
      const strengthB = cardStrength(upperB, normalizedTrump, normalizedTrump);
      if (strengthA[0] !== strengthB[0]) {
        return strengthB[0] - strengthA[0];
      }
      if (strengthA[1] !== strengthB[1]) {
        return strengthB[1] - strengthA[1];
      }
    }
    const suitA = a[1].toUpperCase();
    const suitB = b[1].toUpperCase();
    const suitRankA = suitOrder.indexOf(suitA);
    const suitRankB = suitOrder.indexOf(suitB);
    if (suitRankA !== suitRankB) {
      return suitRankA - suitRankB;
    }
    const valueRankA = valueOrder.indexOf(a[0].toUpperCase());
    const valueRankB = valueOrder.indexOf(b[0].toUpperCase());
    return valueRankA - valueRankB;
  });
}


function updatePhaseState(data, previousPhase) {
  if (data.phase === "lobby" && previousPhase !== "lobby") {
    state.hand = [];
    state.playableCards = [];
    state.playableButtonStates = {};
    state.meldCandidateCards = [];
    state.pendingSuit = null;
    state.autoSuitSent = false;
  }
  if (data.phase === "deal" && previousPhase !== "deal") {
    state.optimisticCards = {};
    state.maxMeldRequested = false;
    state.maxMeldReady = false;
    state.maxMeldValue = null;
    state.maxMeldSuits = "";
    state.pendingSuit = null;
    state.autoSuitSent = false;
    state.teamFaces = { Vit: null, Tit: null };
    state.lastTrickWinningCard = null;
    state.lastTrickSignature = "";
    state.playableButtonStates = {};
    state.meldCandidateCards = [];
  }
  if (data.phase !== "declaration") {
    state.pendingSuit = null;
    state.autoSuitSent = false;
    state.meldCandidateCards = [];
  }
}

function maybeRequestMaxMeld(data) {
  if (state.maxMeldRequested || state.phase !== "declaration") return;
  if (state.currentTurn !== state.playerId) return;
  if (!state.hand || state.hand.length < 5) return;
  if (!state.latestPlayers || state.latestPlayers.length < 4) return;
  state.maxMeldRequested = true;
  state.maxMeldReady = false;
  renderMeldActions();
  sendCommand("maxmeld", {
    silent: true,
    onResult: (msg, err) => {
      if (err) {
        state.maxMeldRequested = false;
        state.maxMeldReady = false;
        renderMeldActions();
        return;
      }
      if (msg) {
        handleMaxMeldResponse(msg);
      }
    },
  });
}

function handleMaxMeldResponse(message) {
  const trimmed = (message || "").trim();
  if (!trimmed) return;
  state.maxMeldReady = true;
  const match = trimmed.match(/^(\d+)([A-Za-z]*)/);
  if (match) {
    state.maxMeldValue = parseInt(match[1], 10);
    state.maxMeldSuits = (match[2] || "").toUpperCase();
    if (state.maxMeldValue >= 5) {
      const suggestedSuit = choosePreferredSuit(state.maxMeldSuits);
      state.pendingSuit = null;
      state.meldCandidateCards = computeMeldCandidateCards(state.hand, suggestedSuit);
      state.autoSuitSent = false;
    } else {
      state.pendingSuit = null;
      state.meldCandidateCards = [];
    }
  } else {
    state.maxMeldValue = null;
    state.maxMeldSuits = "";
    state.meldCandidateCards = [];
  }
  appendUpdate(`Max meld: ${trimmed}`);
  renderCardButtons();
  renderMeldActions();
}

function renderMeldActions() {
  if (!meldActions || !meldButtons || !meldInfo) return;
  meldButtons.innerHTML = "";
  if (state.phase !== "declaration") {
    meldActions.classList.add("hidden");
    meldInfo.textContent = "";
    return;
  }

  meldActions.classList.remove("hidden");

  let showPassButton = true;
  if (!state.maxMeldRequested) {
    meldInfo.textContent = "Awaiting cards...";
  } else if (!state.maxMeldReady) {
    meldInfo.textContent = "Calculating meld...";
  } else if (state.pendingSuit && !state.autoSuitSent) {
    meldInfo.textContent = `Declared ${state.maxMeldValue} ${formatSuitSymbols(state.maxMeldSuits)} – waiting for confirmation.`;
    showPassButton = false;
  } else if (state.maxMeldValue != null && state.maxMeldValue >= 5) {
    meldInfo.textContent = `Best meld: ${state.maxMeldValue} ${formatSuitSymbols(state.maxMeldSuits)}`;
    const declareBtn = document.createElement("button");
    declareBtn.textContent = `Declare ${state.maxMeldValue}${state.maxMeldSuits ? " " + formatSuitSymbols(state.maxMeldSuits) : ""}`;
    declareBtn.disabled = state.currentTurn !== state.playerId;
    declareBtn.addEventListener("click", handleDeclareBest);
    meldButtons.appendChild(declareBtn);
  } else {
    meldInfo.textContent = "No meld of 5 or more.";
  }

  if (showPassButton) {
    const passBtn = document.createElement("button");
    passBtn.textContent = "Pass Meld";
    passBtn.disabled = state.currentTurn !== state.playerId;
    passBtn.addEventListener("click", handlePassMeld);
    meldButtons.appendChild(passBtn);
  }
}

function handleDeclareBest() {
  if (!state.maxMeldReady || state.maxMeldValue == null || state.maxMeldValue < 5) return;
  if (state.currentTurn !== state.playerId) return;
  const suit = choosePreferredSuit(state.maxMeldSuits);
  if (!suit) return;
  state.pendingSuit = suit;
  state.autoSuitSent = false;
  sendCommand(`M ${state.maxMeldValue}`);
  renderMeldActions();
}

function handlePassMeld() {
  if (state.currentTurn !== state.playerId) return;
  state.pendingSuit = null;
  state.autoSuitSent = false;
  sendCommand("M 0");
  renderMeldActions();
}

function choosePreferredSuit(suits) {
  if (!suits) return null;
  const upper = suits.toUpperCase();
  if (upper.includes("C")) return "C";
  return upper[0] || null;
}

function computeMeldCandidateCards(hand, suit) {
  if (!Array.isArray(hand) || !hand.length || !suit) return [];
  const upperSuit = suit.toUpperCase();
  return hand.filter((card) => {
    const upper = card.toUpperCase();
    return PERMANENT_TRUMPS.includes(upper) || upper[1] === upperSuit;
  });
}

function formatSuitSymbols(suits) {
  if (!suits) return "";
  return Array.from(suits.toUpperCase())
    .map(cardSuitToSymbol)
    .join(" ");
}

function cardSuitToSymbol(letter) {
  return SUIT_SYMBOLS[letter.toUpperCase()] || letter;
}

function maybeSendSuit(data) {
  if (!state.pendingSuit) return;
  if (state.phase !== "declaration") return;
  if (data.trump) return;
  if (state.currentTurn !== state.playerId) return;
  if (state.autoSuitSent) return;
  const suit = state.pendingSuit.toUpperCase();
  state.autoSuitSent = true;
  state.pendingSuit = null;
  sendCommand(`S ${suit}`);
  renderMeldActions();
}

function renderDealActions(data) {
  if (!dealActions) return;
  if (data.phase === "deal" && data.current_turn === state.playerId) {
    dealActions.classList.remove("hidden");
  } else {
    dealActions.classList.add("hidden");
  }
}

function populateSplitSelect() {
  if (!splitSelect) return;
  splitSelect.innerHTML = "";
  for (let i = 10; i <= 22; i += 1) {
    const option = document.createElement("option");
    option.value = i;
    option.textContent = i;
    if (i === 16) option.selected = true;
    splitSelect.appendChild(option);
  }
}

joinForm.addEventListener("submit", joinTable);
refreshLobbiesButton.addEventListener("click", fetchLobbies);

commandForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const command = commandInput.value.trim();
  if (!command) return;
  sendCommand(command);
  commandInput.value = "";
});

splitButton.addEventListener("click", () => {
  const value = splitSelect.value || "16";
  sendCommand(`split ${value}`);
});

bankaButton.addEventListener("click", () => {
  sendCommand("banka");
});

lobbyBotsButton.addEventListener("click", () => {
  const difficulty = lobbyBotSelect?.value || "hard";
  sendCommand(`bots ${difficulty}`);
});

lobbyStartButton.addEventListener("click", () => {
  sendCommand("start");
});

if (lobbyChatForm) {
  lobbyChatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = lobbyChatInput.value.trim();
    if (!message) return;
    sendCommand(`say ${message}`);
    lobbyChatInput.value = "";
  });
}

if (gameExitButton) {
  gameExitButton.addEventListener("click", () => {
    leaveLobby();
  });
}

lobbyLeaveButton.addEventListener("click", () => {
  leaveLobby();
});

startBrowserPolling();

window.addEventListener("beforeunload", () => {
  stopPolling();
});
