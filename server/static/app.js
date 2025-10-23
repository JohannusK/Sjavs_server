const state = {
  host: "127.0.0.1",
  port: 8000,
  token: null,
  playerId: null,
  pollTimer: null,
  stateTimer: null,
  hand: [],
  phase: "init",
  trumpSuit: null,
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
  optimisticCards: {},
  latestPlayers: [],
  latestTableSlots: [],
};

const joinSection = document.getElementById("join-section");
const gameSection = document.getElementById("game-section");
const joinForm = document.getElementById("join-form");
const hostInput = document.getElementById("host-input");
const portInput = document.getElementById("port-input");
const nameInput = document.getElementById("name-input");
const playerLabel = document.getElementById("player-label");
const scoreboard = document.getElementById("scoreboard");
const trumpDisplay = document.getElementById("trump-display");
const playersList = document.getElementById("players-list");
const tableCards = document.getElementById("table-cards");
const updatesLog = document.getElementById("updates-log");
const commandForm = document.getElementById("command-form");
const commandInput = document.getElementById("command-input");
const botsButton = document.getElementById("bots-button");
const actionButtons = document.getElementById("action-buttons");
const cardButtons = document.getElementById("card-buttons");
const meldActions = document.getElementById("meld-actions");
const meldInfo = document.getElementById("meld-info");
const meldButtons = document.getElementById("meld-buttons");
const dealActions = document.getElementById("deal-actions");
const splitSelect = document.getElementById("split-select");
const splitButton = document.getElementById("split-button");
const bankaButton = document.getElementById("banka-button");

populateSplitSelect();

const QUICK_ACTIONS = [
  { label: "Show Hand", command: "show" },
  { label: "List Players", command: "list players" },
];

const SUIT_SYMBOLS = {
  C: "♣",
  D: "♦",
  H: "♥",
  S: "♠",
};

function baseUrl() {
  return `http://${state.host}:${state.port}`;
}

async function joinTable(event) {
  event.preventDefault();
  const name = nameInput.value.trim();
  state.host = hostInput.value.trim() || "127.0.0.1";
  state.port = parseInt(portInput.value, 10) || 8000;

  try {
    const response = await fetch(`${baseUrl()}/join`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      const detail = await response.json();
      appendUpdate(`Join failed: ${detail.detail || response.statusText}`);
      return;
    }
    const data = await response.json();
    state.token = data.token;
    state.playerId = data.player_id;
    playerLabel.textContent = `Player ${data.player_id} (${name || "Guest"})`;
    appendUpdate(data.message);
    joinSection.classList.add("hidden");
    gameSection.classList.remove("hidden");
    startPolling();
  } catch (error) {
    appendUpdate(`Join failed: ${error}`);
  }
}

function startPolling() {
  stopPolling();
  state.pollTimer = setInterval(fetchUpdates, 1000);
  state.stateTimer = setInterval(fetchState, 2000);
  fetchUpdates();
  fetchState();
  renderQuickActions();
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
}

async function fetchUpdates() {
  if (!state.token) return;
  try {
    const response = await fetch(`${baseUrl()}/updates?token=${state.token}`);
    if (!response.ok) {
      if (response.status === 401) {
        appendUpdate("Session expired. Reload to reconnect.");
        stopPolling();
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
    if (!response.ok) return;
    const data = await response.json();
    const previousPhase = state.phase;
    state.phase = data.phase;
    state.trumpSuit = data.trump;
    state.lastWinner = data.last_winner;
    state.highlightUntil = Number(data.highlight_until || 0);
    state.currentTurn = data.current_turn;
    state.recentTrick = data.recent_trick || [];
    state.recentTrickExpire = Number(data.recent_trick_expire || 0);

    updatePhaseState(data, previousPhase);

    renderScoreboard(data.scoreboard);
    renderTrump(data.trump);
    renderPlayers(data.players, data.current_turn);
    renderTableCards(data.table_cards);
    renderTableLayout(data.players, data.table_slots, data.current_turn);
    state.hand = sortHand(data.hand || [], data.trump);
    renderCardButtons();
    maybeRequestMaxMeld(data);
    maybeSendSuit(data);
    renderMeldActions();
    renderDealActions(data);
  } catch (error) {
    appendUpdate(`State error: ${error}`);
  }
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
  updatesLog.textContent = existing.slice(-30).join("\n");
  updatesLog.scrollTop = updatesLog.scrollHeight;
}

function renderScoreboard(board) {
  if (!board) return;
  scoreboard.innerHTML = `
    <span class="team">Vit: <strong>${board.Vit ?? "--"}</strong></span>
    <span class="team">Tit: <strong>${board.Tit ?? "--"}</strong></span>
  `;
}

function renderTrump(trump) {
  if (!trump) {
    trumpDisplay.textContent = "Trump: —";
    return;
  }
  const mapping = {
    C: "♣ Kleyvari",
    D: "♦ Rútari",
    H: "♥ Hjartari",
    S: "♠ Spaðari",
  };
  trumpDisplay.textContent = `Trump: ${mapping[trump] || trump}`;
}

function renderPlayers(players, currentTurn) {
  playersList.innerHTML = "";
  players.forEach((player) => {
    const li = document.createElement("li");
    const nameSpan = document.createElement("span");
    nameSpan.className = "name";
    nameSpan.textContent = `${player.id}: ${player.name}`;
    if (player.id === state.playerId) {
      li.classList.add("me");
    }
    if (player.id === currentTurn) {
      li.classList.add("turn");
    }

    const statusSpan = document.createElement("span");
    statusSpan.className = "status";
    const indicator = document.createElement("span");
    indicator.className = "indicator";
    indicator.textContent = player.ok ? "✔" : "✖";
    indicator.style.color = player.ok ? "#5de05d" : "#ff5c5c";

    const pingSpan = document.createElement("span");
    pingSpan.className = "ping";
    pingSpan.textContent = player.ping !== undefined ? `${player.ping.toFixed(1)}s` : "--";

    statusSpan.append(indicator, pingSpan);
    li.append(nameSpan, statusSpan);
    playersList.appendChild(li);
  });
}

function renderTableCards(cards) {
  tableCards.innerHTML = "";
  if (!cards || !cards.length) {
    if (state.recentTrick && state.recentTrick.length && Date.now() / 1000 < state.recentTrickExpire) {
      state.recentTrick.forEach(({ card }) => {
        const span = document.createElement("span");
        span.className = "card";
        const { text, red } = formatCardEmoji(card);
        span.textContent = text;
        if (red) span.classList.add("red");
        tableCards.appendChild(span);
      });
      return;
    }
    tableCards.textContent = "No cards on the table.";
    return;
  }
  cards.forEach((card) => {
    const span = document.createElement("span");
    span.className = "card";
    const { text, red } = formatCardEmoji(card);
    span.textContent = text;
    if (red) {
      span.classList.add("red");
    }
    tableCards.appendChild(span);
  });
}

function renderQuickActions() {
  actionButtons.innerHTML = "";
  QUICK_ACTIONS.forEach(({ label, command }) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.addEventListener("click", () => sendCommand(command));
    actionButtons.appendChild(btn);
  });
}

function renderCardButtons() {
  cardButtons.innerHTML = "";
  if (!state.hand.length) {
    const note = document.createElement("span");
    note.textContent = "No cards available.";
    cardButtons.appendChild(note);
    return;
  }
  state.hand.forEach((card) => {
    const btn = document.createElement("button");
    btn.type = "button";
    const { text, red } = formatCardEmoji(card);
    btn.textContent = text;
    if (red) {
      btn.classList.add("red");
    }
    btn.addEventListener("click", () => playCard(card));
    cardButtons.appendChild(btn);
  });
}

function playCard(card) {
  if (!card) return;
  sendCommand(`P ${card}`, {
    onResult: (msg) => {
      const normalized = (msg || "").trim();
      if (!normalized || normalized === "OK") {
        state.optimisticCards[state.playerId] = card;
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

  const cardsById = {};
  (tableSlotsData || []).forEach(({ id, card }) => {
    cardsById[id] = card;
    delete state.optimisticCards[id];
  });

  const nowSeconds = Date.now() / 1000;
  if (
    (!tableSlotsData || !tableSlotsData.length || !Object.keys(cardsById).length) &&
    state.recentTrick &&
    state.recentTrick.length &&
    nowSeconds < state.recentTrickExpire
  ) {
    state.recentTrick.forEach(({ id, card }) => {
      cardsById[id] = card;
    });
  }

  Object.keys(state.optimisticCards).forEach((seatKey) => {
    const seat = Number(seatKey);
    if (!cardsById[seat]) {
      cardsById[seat] = state.optimisticCards[seat];
    }
  });

  const positionMap = computeSeatOrder(playersById);
  ["top", "left", "right", "bottom"].forEach((pos) => {
    const seat = positionMap[pos] ?? null;
    const slot = document.querySelector(`.table-slot[data-pos="${pos}"]`);
    if (!slot) return;
    const nameEl = slot.querySelector(".name");
    const cardEl = slot.querySelector(".card");
    const player = seat ? playersById[seat] : null;
    const nameText = player ? player.name : `Seat ${seat}`;
    nameEl.textContent = nameText;
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
    cardEl.textContent = "";
    cardEl.classList.remove("red", "highlight");
    const card = seat ? cardsById[seat] : null;
    if (card) {
      const { text, red } = formatCardEmoji(card);
      cardEl.textContent = text;
      if (red) {
        cardEl.classList.add("red");
      }
      const now = Date.now() / 1000;
      if (player && player.id === state.lastWinner && now < state.highlightUntil) {
        cardEl.classList.add("highlight");
      }
    }
  });
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
  const value = card[0];
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
  if (data.phase === "deal" && previousPhase !== "deal") {
    state.optimisticCards = {};
    state.maxMeldRequested = false;
    state.maxMeldReady = false;
    state.maxMeldValue = null;
    state.maxMeldSuits = "";
    state.pendingSuit = null;
    state.autoSuitSent = false;
  }
  if (data.phase !== "declaration") {
    state.pendingSuit = null;
    state.autoSuitSent = false;
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
      state.pendingSuit = choosePreferredSuit(state.maxMeldSuits);
      state.autoSuitSent = false;
    } else {
      state.pendingSuit = null;
    }
  } else {
    state.maxMeldValue = null;
    state.maxMeldSuits = "";
  }
  appendUpdate(`Max meld: ${trimmed}`);
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

botsButton.addEventListener("click", () => {
  sendCommand("bots");
});

window.addEventListener("beforeunload", () => {
  stopPolling();
});
