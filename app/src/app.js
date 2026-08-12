const DATA_URL = "./data/app-data.json?v=20260812-year-jobs-v1";
const API_BASE = "/api";
const PLACEHOLDER = "./assets/model-placeholder.svg";

const state = {
  data: null,
  view: "collection",
  query: "",
  season: "1980",
  manufacturer: "all",
  owned: "all",
  status: "all",
  selectedModelId: "",
  selectedCollectionRow: "",
  collectionSort: null,
  jobs: [],
  jobsLoaded: false,
  jobsError: "",
  selectedJobId: "",
  selectedJobLog: "",
  jobSeason: "1981",
  jobPhotoLimit: "250",
  jobFullCatalog: true,
  adminToken: localStorage.getItem("f1-admin-token") || "",
};

const statusLabels = {
  green: "Ve vitríně",
  white: "Mimo vitrínu",
  yellow: "Chybí",
  red: "NO MODEL",
};

let pendingCollectionScroll = null;
let queryRenderTimer = null;

const views = [
  ["collection", "Sbírka"],
  ["dashboard", "Přehled"],
  ["season", "Roky"],
  ["catalog", "Katalog"],
  ["candidates", "Kandidáti"],
  ["jobs", "Úlohy"],
];

const collectionSortableColumns = [
  { index: 0, key: "standing" },
  { index: 1, key: "number" },
  { index: 2, key: "model" },
  { index: 3, key: "driver" },
  { index: 7, key: "pc" },
  { index: 8, key: "vnv" },
];

const app = document.querySelector("#app");

function formatNumber(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value ?? "");
  return new Intl.NumberFormat("cs-CZ").format(numeric);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function compact(parts) {
  return parts.filter(Boolean).join(" ");
}

function normalize(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

function firstUrl(urls) {
  return Array.isArray(urls) && urls.length ? urls[0] : "";
}

function matchesQuery(value, query) {
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  if (!tokens.length) return true;
  const haystack = normalize(value);
  return tokens.every((token) => haystack.includes(token));
}

function localPhotoKey(model) {
  return `f1-model-photos:${model.id}`;
}

function getPhotos(model) {
  const local = JSON.parse(localStorage.getItem(localPhotoKey(model)) || "[]");
  return Array.from(new Set([...local, model.mainPhoto, ...(model.thumbnails || []), ...(model.photoUrls || [])].filter(Boolean)));
}

function savePhoto(model, url) {
  const photos = JSON.parse(localStorage.getItem(localPhotoKey(model)) || "[]");
  if (url && !photos.includes(url)) {
    photos.unshift(url);
    localStorage.setItem(localPhotoKey(model), JSON.stringify(photos.slice(0, 8)));
  }
}

function parseHash() {
  const hash = location.hash.replace(/^#\/?/, "");
  const [view, id] = hash.split("/");
  if (views.some(([key]) => key === view)) {
    state.view = view;
    if (id?.startsWith("row-")) {
      state.selectedCollectionRow = decodeURIComponent(id.replace(/^row-/, ""));
      state.selectedModelId = "";
    } else if (id) {
      state.selectedModelId = decodeURIComponent(id);
      state.selectedCollectionRow = "";
    }
  }
  if (view === "model" && id) {
    state.view = "catalog";
    state.selectedModelId = decodeURIComponent(id);
    state.selectedCollectionRow = "";
  }
}

function setHash(view, id = "") {
  const nextHash = id ? `#/${view}/${encodeURIComponent(id)}` : `#/${view}`;
  if (location.hash === nextHash) {
    render();
    return;
  }
  if (id) {
    location.hash = nextHash;
    return;
  }
  location.hash = nextHash;
}

function captureCollectionScroll() {
  const tableWrap = document.querySelector(".collection-table")?.closest(".table-wrap");
  return {
    top: tableWrap?.scrollTop || 0,
    left: tableWrap?.scrollLeft || 0,
    windowX: window.scrollX,
    windowY: window.scrollY,
  };
}

function restoreCollectionScroll() {
  if (!pendingCollectionScroll) return;
  const position = pendingCollectionScroll;
  pendingCollectionScroll = null;
  requestAnimationFrame(() => {
    const tableWrap = document.querySelector(".collection-table")?.closest(".table-wrap");
    if (tableWrap) {
      tableWrap.scrollTop = position.top;
      tableWrap.scrollLeft = position.left;
    }
    window.scrollTo(position.windowX, position.windowY);
  });
}

function captureActiveFilter() {
  const field = document.activeElement;
  if (!field?.dataset?.filter) return null;
  return {
    key: field.dataset.filter,
    start: typeof field.selectionStart === "number" ? field.selectionStart : null,
    end: typeof field.selectionEnd === "number" ? field.selectionEnd : null,
  };
}

function restoreActiveFilter(activeFilter) {
  if (!activeFilter) return;
  requestAnimationFrame(() => {
    const field = document.querySelector(`[data-filter="${activeFilter.key}"]`);
    if (!field) return;
    field.focus({ preventScroll: true });
    if (typeof field.setSelectionRange === "function" && activeFilter.start !== null && activeFilter.end !== null) {
      field.setSelectionRange(activeFilter.start, activeFilter.end);
    }
  });
}

function filteredModels(limit = 5000) {
  const q = normalize(state.query);
  const rows = state.data.models.filter((model) => {
    if (state.season !== "all" && model.season !== state.season) return false;
    if (state.manufacturer !== "all" && model.manufacturer !== state.manufacturer) return false;
    if (state.owned === "owned" && !model.owned) return false;
    if (state.owned === "missing" && model.owned) return false;
    if (state.status !== "all" && model.colorStatus !== state.status) return false;
    return matchesQuery(
      compact([
        model.catalogNumber,
        model.manufacturer,
        model.constructor,
        model.chassis,
        model.driver,
        model.event,
        model.rawTitle,
      ]),
      q,
    );
  });
  return rows.slice(0, limit);
}

function findModelByCatalog(manufacturer, catalogNumber) {
  const manufacturerKey = normalize(manufacturer);
  const codeKey = normalize(catalogNumber).replace(/[^a-z0-9]/g, "");
  const codeAliases = new Set([codeKey]);
  if (manufacturerKey === "spark" && /^s\d+$/.test(codeKey)) {
    codeAliases.add(`spk${codeKey.slice(1)}`);
  }
  if (manufacturerKey === "spark" && /^spk\d+$/.test(codeKey)) {
    codeAliases.add(`s${codeKey.slice(3)}`);
  }
  return state.data.models.find((model) => {
    const modelCode = normalize(model.catalogNumber).replace(/[^a-z0-9]/g, "");
    return codeAliases.has(modelCode) && (!manufacturerKey || normalize(model.manufacturer) === manufacturerKey);
  });
}

function currentModel() {
  if (state.selectedModelId) {
    return state.data.models.find((model) => model.id === state.selectedModelId) || null;
  }
  const selectedCollectionItem = currentCollectionItem();
  if (selectedCollectionItem) {
    if (selectedCollectionItem.catalogNumber) {
      return findModelByCatalog(selectedCollectionItem.manufacturer, selectedCollectionItem.catalogNumber) || null;
    }
    return null;
  }
  if (state.view === "collection") {
    const item = filteredCollectionItems(1)[0];
    if (item?.catalogNumber) {
      return findModelByCatalog(item.manufacturer, item.catalogNumber) || null;
    }
  }
  return filteredModels(1)[0] || state.data.models[0] || null;
}

function currentCollectionItem() {
  if (!state.selectedCollectionRow) return null;
  return state.data.collectionItems.find((item) => String(item.sourceRow) === String(state.selectedCollectionRow)) || null;
}

function currentDetail() {
  const collectionItem = currentCollectionItem();
  const model = currentModel();
  if (model) return { model, collectionItem };
  if (!collectionItem) return { model: null, collectionItem: null };
  return {
    collectionItem,
    model: {
      id: collectionItem.id,
      title: compact([collectionItem.season, collectionItem.car, collectionItem.chassis]),
      manufacturer: collectionItem.manufacturer,
      catalogNumber: collectionItem.catalogNumber || "není",
      colorStatus: collectionRowStatus(collectionItem),
      mainPhoto: collectionItem.mainPhoto || "",
      thumbnails: collectionItem.thumbnails || [],
      photoUrls: collectionItem.photoUrls || [],
      originalPhotoUrl: collectionItem.originalPhotoUrl || collectionItem.mainPhoto || "",
      season: collectionItem.season,
      driver: collectionItem.driver,
      collectionDriver: collectionItem.driver,
      constructor: collectionItem.car,
      collectionCar: collectionItem.car,
      chassis: collectionItem.chassis,
      collectionChassis: collectionItem.chassis,
      carNumber: collectionItem.carNumber,
      event: collectionItem.extra,
      collectionQuantity: collectionItem.quantity,
      matchStatus: collectionItem.displayLabel || statusLabels[collectionRowStatus(collectionItem)],
      sourceUrls: [collectionItem.photoSourcePageUrl].filter(Boolean),
    },
  };
}

function collectionRowStatus(item) {
  return item.displayStatus || (item.v > 0 ? "green" : item.quantity > 0 || item.nv > 0 ? "white" : item.catalogNumber === "NO MODEL" ? "red" : "yellow");
}

function standingWithPoints(item) {
  const standing = item.driverStanding || "—";
  const points = item.driverPoints ? `${item.driverPoints} b.` : "0 b.";
  return `${standing} / ${points}`;
}

function displayLocation(item) {
  if (item.v > 0) return "V";
  if (item.nv > 0) return "NV";
  return "";
}

function detailSummary(model, collectionItem) {
  const season = model.season || collectionItem?.season || "";
  const car = compact([model.collectionCar || model.constructor, model.collectionChassis || model.chassis]);
  const driver = model.driver || model.collectionDriver || collectionItem?.driver || "";
  const number = model.carNumber || collectionItem?.carNumber || "";
  const event = model.event || collectionItem?.extra || "";
  const main = compact([season, car, driver, number ? `#${number}` : ""]);
  return event ? `${main}; ${season}, ${event}` : main;
}

function detailSources(model, collectionItem) {
  const urls = [
    ...(model.sourceUrls || []),
    model.photoSourcePageUrl,
    collectionItem?.photoSourcePageUrl,
  ].filter(Boolean);
  return Array.from(new Set(urls));
}

const textSorter = new Intl.Collator("cs", { numeric: true, sensitivity: "base" });

function collectionSortEnabled() {
  return state.season !== "all";
}

function numericSortValue(value) {
  const normalized = String(value ?? "").replace(",", ".").match(/-?\d+(\.\d+)?/);
  return normalized ? Number(normalized[0]) : Number.POSITIVE_INFINITY;
}

function collectionSortValue(item, key) {
  if (key === "standing") return numericSortValue(item.driverStanding);
  if (key === "number") return numericSortValue(item.carNumber);
  if (key === "model") return compact([item.season, item.car, item.chassis, item.team]);
  if (key === "driver") return item.driver || "";
  if (key === "pc") return Number(item.quantity) || 0;
  if (key === "vnv") return displayLocation(item);
  return item.sourceRow;
}

function compareCollectionItems(left, right) {
  if (!collectionSortEnabled() || !state.collectionSort) return Number(left.sourceRow) - Number(right.sourceRow);
  const { key, direction } = state.collectionSort;
  const a = collectionSortValue(left, key);
  const b = collectionSortValue(right, key);
  const directionMultiplier = direction === "desc" ? -1 : 1;
  if (typeof a === "number" && typeof b === "number") {
    const aMissing = !Number.isFinite(a);
    const bMissing = !Number.isFinite(b);
    if (aMissing !== bMissing) return aMissing ? 1 : -1;
    const result = a - b;
    return result ? result * directionMultiplier : Number(left.sourceRow) - Number(right.sourceRow);
  }
  const result = textSorter.compare(String(a), String(b));
  return result ? result * directionMultiplier : Number(left.sourceRow) - Number(right.sourceRow);
}

function sortHeader(label, key) {
  if (!collectionSortEnabled()) return escapeHtml(label);
  const active = state.collectionSort?.key === key;
  const direction = active ? state.collectionSort.direction : "";
  const mark = direction === "asc" ? "↑" : direction === "desc" ? "↓" : "↕";
  return `<button class="sort-header ${active ? "active" : ""}" type="button" data-sort-column="${escapeHtml(key)}">${escapeHtml(label)} <span>${mark}</span></button>`;
}

function nextCollectionSort(key) {
  if (!state.collectionSort || state.collectionSort.key !== key) {
    state.collectionSort = { key, direction: "asc" };
  } else if (state.collectionSort.direction === "asc") {
    state.collectionSort = { key, direction: "desc" };
  } else {
    state.collectionSort = null;
  }
}

function decorateCollectionSortHeaders() {
  if (!collectionSortEnabled()) return;
  const headers = document.querySelectorAll(".collection-table thead th");
  collectionSortableColumns.forEach(({ index, key }) => {
    const header = headers[index];
    if (!header) return;
    const label = header.textContent.trim();
    const active = state.collectionSort?.key === key;
    const direction = active ? state.collectionSort.direction : "";
    const mark = direction === "asc" ? "↑" : direction === "desc" ? "↓" : "↕";
    header.innerHTML = `<button class="sort-header ${active ? "active" : ""}" type="button" data-sort-column="${escapeHtml(key)}">${escapeHtml(label)} <span>${mark}</span></button>`;
  });
}

function filteredCollectionItems(limit = 5000) {
  const q = normalize(state.query);
  const rows = state.data.collectionItems.filter((item) => {
    const rowStatus = collectionRowStatus(item);
    if (state.season !== "all" && item.season !== state.season) return false;
    if (state.manufacturer !== "all" && item.manufacturer !== state.manufacturer) return false;
    if (state.owned === "owned" && !item.owned) return false;
    if (state.owned === "missing" && item.owned) return false;
    if (state.status !== "all" && rowStatus !== state.status) return false;
    return matchesQuery(Object.values(item).join(" "), q);
  });
  return rows.sort(compareCollectionItems).slice(0, limit);
}

function statCard(label, value, sub = "") {
  return `
    <section class="stat-card">
      <span>${escapeHtml(label)}</span>
      <strong>${formatNumber(value)}</strong>
      ${sub ? `<small>${escapeHtml(sub)}</small>` : ""}
    </section>
  `;
}

function renderTopbar() {
  return `
    <header class="topbar">
      <nav class="tabs" aria-label="Hlavní zobrazení">
        ${views
          .map(
            ([key, label]) => `
              <button class="tab ${state.view === key ? "active" : ""}" data-view="${key}">
                ${label}
              </button>
            `,
          )
          .join("")}
      </nav>
      <div class="top-actions">
        <button class="ghost-button" data-action="refresh">Obnovit data</button>
      </div>
    </header>
  `;
}

function renderStatusMetrics() {
  const rows = filteredCollectionItems(5000);
  const ownedPieces = rows.reduce((sum, item) => sum + item.quantity, 0);
  const vPieces = rows.reduce((sum, item) => sum + item.v, 0);
  const nvPieces = rows.reduce((sum, item) => sum + item.nv, 0);
  return `
    <div class="status-metrics" aria-label="Souhrn sbírky">
      <span><strong>${formatNumber(rows.length)}</strong> řádků</span>
      <span><strong>${formatNumber(ownedPieces)}</strong> kusů</span>
      <span><strong>${formatNumber(vPieces)}</strong> V</span>
      <span><strong>${formatNumber(nvPieces)}</strong> NV</span>
    </div>
  `;
}

function renderFilters() {
  const seasons = ["all", ...state.data.seasons].map(
    (year) => `<option value="${year}" ${state.season === year ? "selected" : ""}>${year === "all" ? "Všechny roky" : year}</option>`,
  );
  const manufacturers = ["all", ...state.data.manufacturers.map((item) => item.name)].map(
    (name) => `<option value="${escapeHtml(name)}" ${state.manufacturer === name ? "selected" : ""}>${name === "all" ? "Všichni výrobci" : escapeHtml(name)}</option>`,
  );
  return `
    <section class="filter-bar">
      <div class="filter-stack">
        <div class="field">
          <label for="search">Hledat</label>
          <input id="search" data-filter="query" value="${escapeHtml(state.query)}" placeholder="kód, jezdec, tým, šasi..." />
        </div>
        <div class="field">
          <label for="season">Rok</label>
          <select id="season" data-filter="season">${seasons.join("")}</select>
        </div>
        <div class="field">
          <label for="manufacturer">Výrobce</label>
          <select id="manufacturer" data-filter="manufacturer">${manufacturers.join("")}</select>
        </div>
        <div class="field">
          <label for="owned">Sbírka</label>
          <select id="owned" data-filter="owned">
            <option value="all" ${state.owned === "all" ? "selected" : ""}>Vše</option>
            <option value="owned" ${state.owned === "owned" ? "selected" : ""}>Vlastněné</option>
            <option value="missing" ${state.owned === "missing" ? "selected" : ""}>Chybí</option>
          </select>
        </div>
        <div class="field">
          <label for="status">Stav</label>
          <select id="status" data-filter="status">
            <option value="all" ${state.status === "all" ? "selected" : ""}>Všechny stavy</option>
            <option value="green" ${state.status === "green" ? "selected" : ""}>Vlastněno</option>
            <option value="white" ${state.status === "white" ? "selected" : ""}>Jiný / možná shoda</option>
            <option value="yellow" ${state.status === "yellow" ? "selected" : ""}>Chybí ve sbírce</option>
            <option value="red" ${state.status === "red" ? "selected" : ""}>NO MODEL</option>
          </select>
        </div>
        ${renderStatusMetrics()}
        <button class="primary-button" data-action="clearFilters">Vyčistit</button>
      </div>
    </section>
  `;
}

function renderDashboard() {
  const summary = state.data.summary;
  const top = state.data.manufacturers.slice(0, 16);
  const max = Math.max(...top.map((item) => item.count), 1);
  const visible = filteredModels(5000);
  const owned = visible.filter((model) => model.owned).length;
  return `
    <div class="main-stack">
      <section class="stats-grid">
        ${statCard("Master katalog", summary.masterModels, "jen modely s katalogovým číslem")}
        ${statCard("Kandidáti", summary.candidates, "čekají na ověření")}
        ${statCard("Sbírka", summary.ownedCollectionRows, "vlastněné řádky")}
        ${statCard("Filtrované vlastněné", owned, `${visible.length} modelů ve filtru`)}
      </section>
      <section class="panel">
        <div class="panel-header">
          <div class="panel-title">
            <strong>Výrobci v Master Catalogu</strong>
            <span>Počítají se pouze záznamy s výrobcem a katalogovým číslem</span>
          </div>
        </div>
        <div class="bar-list">
          ${top
            .map(
              (item) => `
                <div class="bar-row">
                  <strong>${escapeHtml(item.name || "Neznámý")}</strong>
                  <div class="bar-track"><div class="bar-fill" style="width:${(item.count / max) * 100}%"></div></div>
                  <span>${formatNumber(item.count)}</span>
                </div>
              `,
            )
            .join("")}
        </div>
      </section>
      ${renderCatalogPanel("Rychlý katalog", 80)}
    </div>
  `;
}

function renderCatalogPanel(title = "Master Catalog", limit = 500) {
  const rows = filteredModels(limit);
  return `
    <section class="panel">
      <div class="panel-header">
        <div class="panel-title">
          <strong>${escapeHtml(title)}</strong>
          <span>${formatNumber(rows.length)} zobrazených modelů</span>
        </div>
        <div class="panel-tools">
          <span class="pill blue">${escapeHtml(state.season === "all" ? "všechny roky" : state.season)}</span>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Výrobce</th>
              <th>Kód</th>
              <th>Událost</th>
              <th>Stav</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (model) => `
                  <tr class="clickable-row row-status-${model.colorStatus}" data-model-id="${escapeHtml(model.id)}">
                    <td>
                      <div class="cell-main">
                        <strong>${escapeHtml(compact([model.season, model.constructor, model.chassis]))}</strong>
                        <span>${escapeHtml(compact([model.driver, model.carNumber ? "#" + model.carNumber : ""]))}</span>
                      </div>
                    </td>
                    <td>${escapeHtml(model.manufacturer)}</td>
                    <td><strong>${escapeHtml(model.catalogNumber)}</strong></td>
                    <td>${escapeHtml(model.event)}</td>
                    <td><span class="pill ${model.colorStatus}">${statusLabels[model.colorStatus]}</span></td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
      ${rows.length === limit ? `<p class="notice">Zobrazeno prvních ${formatNumber(limit)} řádků podle aktuálního filtru.</p>` : ""}
    </section>
  `;
}

function renderSeason() {
  if (state.season === "1980") {
    return renderPilotSeason();
  }
  return `
    <div class="main-stack">
      <section class="stats-grid">
        ${statCard("Rok", state.season === "all" ? "Vše" : state.season)}
        ${statCard("Modely ve filtru", filteredModels(5000).length)}
        ${statCard("Vlastněné", filteredModels(5000).filter((model) => model.owned).length)}
        ${statCard("Kandidáti", state.data.candidates.filter((item) => state.season === "all" || item.season === state.season).length)}
      </section>
      ${renderCatalogPanel("Roční tabulka modelů", 700)}
    </div>
  `;
}

function renderPilotSeason() {
  const rows = state.data.pilot1980.seasonRows.filter((row) => {
    const q = normalize(state.query);
    return matchesQuery(Object.values(row).join(" "), q);
  });
  return `
    <div class="main-stack">
      <section class="stats-grid">
        ${statCard("1980 řádků", rows.length, "pilotní season view")}
        ${statCard("MODEL FOUND", rows.filter((row) => row["Model Status"] === "MODEL FOUND").length)}
        ${statCard("NO MODEL", rows.filter((row) => row["Catalog Nr."] === "NO MODEL").length)}
        ${statCard("OWNED", rows.filter((row) => row["Collection Status"] === "OWNED").length)}
      </section>
      <section class="panel">
        <div class="panel-header">
          <div class="panel-title">
            <strong>1980 Driver Order</strong>
            <span>Pořadí podle šampionátu, modely z Master Indexu a stav sbírky</span>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Pořadí</th>
                <th>Jezdec / tým</th>
                <th>Auto</th>
                <th>Katalog</th>
                <th>Stav</th>
              </tr>
            </thead>
            <tbody>
              ${rows
                .map((row) => {
                  const model = findModelByCatalog(row["Manufacturer"], row["Catalog Nr."]);
                  const color = deriveSeasonColor(row);
                  return `
                    <tr class="${model ? "clickable-row" : ""} row-status-${color}" ${model ? `data-model-id="${escapeHtml(model.id)}"` : ""}>
                      <td><strong>${escapeHtml(row["Wiki Order"])}</strong><br><span class="small-note">${escapeHtml(row["Points"])} bodů</span></td>
                      <td><div class="cell-main"><strong>${escapeHtml(row["Driver"])}</strong><span>${escapeHtml(row["Team / Entrant"])}</span></div></td>
                      <td><div class="cell-main"><strong>${escapeHtml(compact([row["Constructor"], row["Season Chassis"]]))}</strong><span>${escapeHtml(row["Season Car No."] ? "#" + row["Season Car No."] : "")}</span></div></td>
                      <td><strong>${escapeHtml(row["Catalog Nr."])}</strong><br><span class="small-note">${escapeHtml(row["Manufacturer"])}</span></td>
                      <td><span class="pill ${color}">${escapeHtml(row["Collection Status"] || row["Model Status"])}</span></td>
                    </tr>
                  `;
                })
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `;
}

function deriveSeasonColor(row) {
  if (row["Catalog Nr."] === "NO MODEL") return "red";
  if (row["Collection Status"] === "OWNED") return "green";
  if (row["Collection Status"] === "OTHER MODEL OWNED") return "white";
  return "yellow";
}

function renderCollection() {
  const rows = filteredCollectionItems(900);
  return `
    <div class="main-stack">
      <section class="panel">
        <div class="table-wrap">
          <table class="collection-table">
            <colgroup>
              <col class="col-standing" />
              <col class="col-number" />
              <col class="col-model" />
              <col class="col-driver" />
              <col class="col-event" />
              <col class="col-maker" />
              <col class="col-code" />
              <col class="col-pc" />
              <col class="col-vnv" />
            </colgroup>
            <thead>
              <tr>
                <th>Pořadí</th>
                <th>Č.</th>
                <th>Model</th>
                <th>Jezdec</th>
                <th>VC / detail</th>
                <th>Výrobce</th>
                <th>Kód</th>
                <th>PC</th>
                <th>V/NV</th>
              </tr>
            </thead>
            <tbody>
              ${rows
                .map((item) => {
                  const model = item.catalogNumber ? findModelByCatalog(item.manufacturer, item.catalogNumber) : null;
                  const rowStatus = collectionRowStatus(item);
                  const detail = item.extra || model?.event || "";
                  const selected = String(state.selectedCollectionRow) === String(item.sourceRow);
                  return `
                    <tr class="clickable-row row-status-${rowStatus} ${selected ? "selected-row" : ""}" data-clickable-row="collection" data-collection-row="${escapeHtml(item.sourceRow)}" ${model ? `data-model-id="${escapeHtml(model.id)}"` : ""}>
                      <td><strong>${escapeHtml(standingWithPoints(item))}</strong></td>
                      <td><strong>${escapeHtml(item.carNumber)}</strong></td>
                      <td title="${escapeHtml(compact([item.season, item.car, item.chassis, item.team]))}"><strong>${escapeHtml(compact([item.season, item.car, item.chassis]))}</strong><span class="team-inline">· ${escapeHtml(item.team)}</span></td>
                      <td>${escapeHtml(item.driver)}</td>
                      <td>${escapeHtml(detail)}</td>
                      <td>${escapeHtml(item.manufacturer)}</td>
                      <td><strong>${escapeHtml(item.catalogNumber)}</strong></td>
                      <td>${formatNumber(item.quantity)}</td>
                      <td>${escapeHtml(displayLocation(item))}</td>
                    </tr>
                  `;
                })
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `;
}

function renderCandidates() {
  const q = normalize(state.query);
  const rows = state.data.candidates
    .filter((item) => {
      if (state.season !== "all" && item.season !== state.season) return false;
      if (state.manufacturer !== "all" && item.manufacturer !== state.manufacturer) return false;
      return matchesQuery(Object.values(item).join(" "), q);
    })
    .slice(0, 700);
  return `
    <div class="main-stack">
      <section class="stats-grid">
        ${statCard("Kandidáti", rows.length)}
        ${statCard("Bez kódu", rows.filter((item) => !item.catalogNumber).length)}
        ${statCard("Bez výrobce", rows.filter((item) => !item.manufacturer).length)}
        ${statCard("Zdroje", new Set(rows.map((item) => item.sourceName)).size)}
      </section>
      <section class="panel">
        <div class="panel-header">
          <div class="panel-title">
            <strong>Verification Queue</strong>
            <span>Záznamy mimo Master Catalog podle pravidla „bez katalogového čísla není model“</span>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Kandidát</th>
                <th>Výrobce</th>
                <th>Důvod</th>
                <th>Zdroj</th>
              </tr>
            </thead>
            <tbody>
              ${rows
                .map(
                  (item) => `
                    <tr>
                      <td><div class="cell-main"><strong>${escapeHtml(compact([item.season, item.constructor, item.chassis]))}</strong><span>${escapeHtml(item.rawTitle || item.event)}</span></div></td>
                      <td>${escapeHtml(item.manufacturer || "Neurčeno")}</td>
                      <td><span class="pill yellow">${escapeHtml(item.reason)}</span></td>
                      <td>${firstUrl(item.sourceUrls) ? `<a href="${escapeHtml(firstUrl(item.sourceUrls))}" target="_blank" rel="noreferrer">otevřít</a>` : ""}</td>
                    </tr>
                  `,
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `;
}

function renderDetail() {
  const { model, collectionItem } = currentDetail();
  if (!model) {
    return `<aside class="detail"><div class="detail-empty">Žádný model k zobrazení</div></aside>`;
  }
  const photos = getPhotos(model);
  const hasPhoto = photos.length > 0;
  const photo = photos[0] || "";
  const originalPhoto = model.originalPhotoUrl || photo;
  const sources = detailSources(model, collectionItem);
  return `
    <aside class="detail">
      <div class="photo-stage ${photos.length > 1 ? "has-thumbs" : ""}">
        ${
          hasPhoto
            ? `<button class="photo-main" data-original-photo="${escapeHtml(originalPhoto)}" title="Dvojklik otevře původní velikost">
                <img src="${escapeHtml(photo)}" alt="${escapeHtml(model.title)}" onerror="this.closest('.photo-main').classList.add('broken-photo')" />
              </button>`
            : `<div class="photo-missing">
                <strong>Fotka modelu chybí</strong>
                <span>${escapeHtml(model.manufacturer)} · ${escapeHtml(model.catalogNumber)}</span>
              </div>`
        }
        ${
          photos.length > 1
            ? `<div class="thumbnail-strip">
                ${photos
                  .slice(0, 8)
                  .map(
                    (url, index) => `
                      <button class="thumbnail ${index === 0 ? "active" : ""}" data-thumbnail-url="${escapeHtml(url)}">
                        <img src="${escapeHtml(url)}" alt="Náhled ${index + 1}" onerror="this.closest('button').classList.add('broken')" />
                      </button>
                    `,
                  )
                  .join("")}
              </div>`
            : ""
        }
      </div>
      <div class="detail-body">
        <div class="detail-summary row-status-${escapeHtml(model.colorStatus)}">
          <strong>${escapeHtml(detailSummary(model, collectionItem))}</strong>
          <span>${escapeHtml(model.manufacturer)} · ${escapeHtml(model.catalogNumber)}</span>
        </div>
        <div>
          <span class="pill ${model.colorStatus}">${statusLabels[model.colorStatus]}</span>
        </div>
        <div class="meta-grid compact-meta-grid">
          ${meta("Výrobce", model.manufacturer)}
          ${meta("Kód", model.catalogNumber)}
          ${meta("Kusy", model.collectionQuantity || collectionItem?.quantity)}
          ${meta("V/NV", collectionItem ? displayLocation(collectionItem) : "")}
        </div>
        <div class="meta-grid legacy-detail-grid">
          ${meta("Rok", model.season)}
          ${meta("Jezdec", model.driver || model.collectionDriver || collectionItem?.driver)}
          ${meta("Tým / auto", compact([model.constructor, model.collectionCar, collectionItem?.team]))}
          ${meta("Šasi", model.chassis || model.collectionChassis || collectionItem?.chassis)}
          ${meta("Číslo", model.carNumber || collectionItem?.carNumber)}
          ${meta("Událost", model.event || collectionItem?.extra)}
          ${meta("Kusů ve sbírce", model.collectionQuantity || collectionItem?.quantity)}
          ${meta("Shoda", model.matchStatus)}
        </div>
        <form class="photo-editor" data-photo-form="${escapeHtml(model.id)}">
          <strong>Fotky modelu</strong>
          <div class="photo-editor-row">
            <input name="photoUrl" placeholder="https://..." />
            <button class="primary-button" type="submit">Přidat</button>
          </div>
          <span class="small-note">${photos.length ? `${photos.length} uložených fotek` : "Fotka zatím není uložená"} · hlavní fotka + thumbnaily se později budou ukládat do databáze</span>
        </form>
        <div class="source-list">
          <strong>Zdroje</strong>
          <div class="source-scroll">
            ${
              sources.length
                ? sources.map((url) => `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(url)}</a>`).join("")
                : `<span class="source-empty">Bez ověřeného zdroje</span>`
            }
          </div>
        </div>
      </div>
    </aside>
  `;
}

function meta(label, value) {
  return `
    <div class="meta">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "—")}</strong>
    </div>
  `;
}

function jobStatusLabel(status) {
  return {
    queued: "Čeká",
    running: "Běží",
    done: "Hotovo",
    failed: "Chyba",
  }[status] || status || "Neznámé";
}

function jobStatusColor(status) {
  if (status === "done") return "green";
  if (status === "failed") return "red";
  if (status === "running") return "blue";
  return "yellow";
}

function renderJobs() {
  const selected = state.jobs.find((job) => job.id === state.selectedJobId) || state.jobs[0] || null;
  const defaultSeason = state.jobSeason || (state.season !== "all" ? state.season : "1981");
  return `
    <div class="main-stack">
      <section class="panel">
        <div class="panel-header">
          <div class="panel-title">
            <strong>Doplnit ročník</strong>
            <span>Nejprve nezávislý katalog, fotky a zdroje; sbírka se porovnává až nakonec.</span>
          </div>
          <div class="panel-tools">
            <button class="ghost-button" data-action="refreshJobs">Obnovit úlohy</button>
          </div>
        </div>
        <div class="job-form">
          <div class="field">
            <label for="jobSeason">Rok</label>
            <input id="jobSeason" data-job-field="jobSeason" value="${escapeHtml(defaultSeason)}" inputmode="numeric" />
          </div>
          <div class="field">
            <label for="jobPhotoLimit">Limit fotek</label>
            <input id="jobPhotoLimit" data-job-field="jobPhotoLimit" value="${escapeHtml(state.jobPhotoLimit)}" inputmode="numeric" />
          </div>
          <label class="check-field">
            <input type="checkbox" data-job-field="jobFullCatalog" ${state.jobFullCatalog ? "checked" : ""} />
            <span>Kompletní sběr katalogu ze zdrojů</span>
          </label>
          <div class="field token-field">
            <label for="adminToken">Admin token</label>
            <input id="adminToken" data-job-field="adminToken" value="${escapeHtml(state.adminToken)}" type="password" autocomplete="off" />
          </div>
          <button class="primary-button" data-action="startYearJob">Spustit ročník</button>
        </div>
        ${state.jobsError ? `<p class="notice error">${escapeHtml(state.jobsError)}</p>` : ""}
      </section>
      <section class="panel">
        <div class="panel-header">
          <div class="panel-title">
            <strong>Poslední úlohy</strong>
            <span>${state.jobsLoaded ? `${formatNumber(state.jobs.length)} běhů` : "Načítám..."}</span>
          </div>
        </div>
        <div class="job-list">
          ${
            state.jobs.length
              ? state.jobs
                  .map(
                    (job) => `
                      <button class="job-card ${selected?.id === job.id ? "active" : ""}" data-job-id="${escapeHtml(job.id)}">
                        <span class="pill ${jobStatusColor(job.status)}">${escapeHtml(jobStatusLabel(job.status))}</span>
                        <strong>${escapeHtml(job.season)} · ${escapeHtml(job.step || "")}</strong>
                        <small>${escapeHtml(job.createdAt || "")}</small>
                        ${
                          job.summary && Object.keys(job.summary).length
                            ? `<small>${formatNumber(job.summary.models || 0)} modelů · ${formatNumber(job.summary.modelsWithPhoto || 0)} s fotkou</small>`
                            : ""
                        }
                      </button>
                    `,
                  )
                  .join("")
              : `<p class="notice">Zatím není uložená žádná úloha.</p>`
          }
        </div>
      </section>
      ${
        selected
          ? `<section class="panel">
              <div class="panel-header">
                <div class="panel-title">
                  <strong>Log úlohy ${escapeHtml(selected.id)}</strong>
                  <span>${escapeHtml(selected.error || selected.step || "")}</span>
                </div>
                <div class="panel-tools">
                  <button class="ghost-button" data-job-log="${escapeHtml(selected.id)}">Načíst log</button>
                </div>
              </div>
              <pre class="job-log">${escapeHtml(state.selectedJobLog || "Vyber log nebo obnov úlohy.")}</pre>
            </section>`
          : ""
      }
    </div>
  `;
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  if (state.adminToken) headers["X-Admin-Token"] = state.adminToken;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(typeof payload === "string" ? payload : payload.error || `API chyba ${response.status}`);
  }
  return payload;
}

async function loadJobs() {
  try {
    state.jobsError = "";
    const payload = await apiFetch("/jobs");
    state.jobs = payload.jobs || [];
    state.jobsLoaded = true;
    if (!state.selectedJobId && state.jobs.length) state.selectedJobId = state.jobs[0].id;
    render();
  } catch (error) {
    state.jobsError = error.message;
    state.jobsLoaded = true;
    render();
  }
}

async function loadJobLog(jobId) {
  try {
    state.jobsError = "";
    state.selectedJobId = jobId;
    state.selectedJobLog = await apiFetch(`/jobs/${encodeURIComponent(jobId)}/log`);
    render();
  } catch (error) {
    state.jobsError = error.message;
    render();
  }
}

async function startYearJob() {
  try {
    state.jobsError = "";
    localStorage.setItem("f1-admin-token", state.adminToken);
    const payload = await apiFetch("/jobs/start", {
      method: "POST",
      body: JSON.stringify({
        season: state.jobSeason,
        photoLimit: Number(state.jobPhotoLimit || 250),
        fullCatalog: state.jobFullCatalog,
      }),
    });
    state.selectedJobId = payload.job.id;
    state.selectedJobLog = "Úloha spuštěna. Log se začne plnit po prvních krocích.";
    await loadJobs();
  } catch (error) {
    state.jobsError = error.message;
    render();
  }
}

function renderMain() {
  if (state.view === "dashboard") return renderDashboard();
  if (state.view === "season") return renderSeason();
  if (state.view === "collection") return renderCollection();
  if (state.view === "candidates") return renderCandidates();
  if (state.view === "jobs") return renderJobs();
  return `<div class="main-stack">${renderCatalogPanel("Master Catalog", 900)}</div>`;
}

function render() {
  const activeFilter = captureActiveFilter();
  parseHash();
  app.innerHTML = `
    ${renderTopbar()}
    ${renderFilters()}
    <div class="layout">
      ${renderDetail()}
      ${renderMain()}
    </div>
  `;
  wireEvents();
  restoreActiveFilter(activeFilter);
  restoreCollectionScroll();
}

function wireEvents() {
  decorateCollectionSortHeaders();
  if (state.view === "jobs" && !state.jobsLoaded) {
    loadJobs();
  }
  document.querySelectorAll("[data-sort-column]").forEach((button) => {
    button.addEventListener("click", () => {
      pendingCollectionScroll = { top: 0, left: 0, windowX: window.scrollX, windowY: window.scrollY };
      nextCollectionSort(button.dataset.sortColumn);
      render();
    });
  });
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setHash(button.dataset.view));
  });
  document.querySelectorAll("[data-filter]").forEach((field) => {
    field.addEventListener("input", () => {
      const key = field.dataset.filter;
      state[key] = field.value;
      if (key === "query") {
        clearTimeout(queryRenderTimer);
        queryRenderTimer = setTimeout(() => {
          queryRenderTimer = null;
          render();
        }, 220);
        return;
      }
      clearTimeout(queryRenderTimer);
      queryRenderTimer = null;
      if (key !== "query") {
        state.selectedModelId = "";
        state.selectedCollectionRow = "";
      }
      if (key === "season") {
        state.collectionSort = null;
      }
      render();
    });
  });
  document.querySelectorAll(".collection-table tbody").forEach((tbody) => {
    tbody.addEventListener("click", (event) => {
      const row = event.target.closest("[data-clickable-row='collection']");
      if (!row) return;
      pendingCollectionScroll = captureCollectionScroll();
      state.selectedCollectionRow = row.dataset.collectionRow;
      state.selectedModelId = "";
      setHash("collection", `row-${state.selectedCollectionRow}`);
    });
  });
  document.querySelectorAll("[data-model-id]:not([data-collection-row])").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedCollectionRow = "";
      state.selectedModelId = row.dataset.modelId;
      setHash(state.view, state.selectedModelId);
      render();
    });
  });
  document.querySelectorAll("[data-thumbnail-url]").forEach((button) => {
    button.addEventListener("click", () => {
      const img = document.querySelector(".photo-main img");
      if (img) img.src = button.dataset.thumbnailUrl;
      document.querySelectorAll(".thumbnail").forEach((thumb) => thumb.classList.remove("active"));
      button.classList.add("active");
    });
  });
  document.querySelectorAll("[data-original-photo]").forEach((button) => {
    button.addEventListener("dblclick", () => {
      const url = button.dataset.originalPhoto;
      if (url && url !== PLACEHOLDER) window.open(url, "_blank", "noopener,noreferrer");
    });
  });
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.action === "clearFilters") {
        clearTimeout(queryRenderTimer);
        queryRenderTimer = null;
        state.query = "";
        state.season = "1980";
        state.manufacturer = "all";
        state.owned = "all";
        state.status = "all";
        state.selectedModelId = "";
        state.selectedCollectionRow = "";
        state.collectionSort = null;
        setHash(state.view);
        render();
      }
      if (button.dataset.action === "refresh") {
        location.reload();
      }
      if (button.dataset.action === "refreshJobs") {
        state.jobsLoaded = false;
        loadJobs();
      }
      if (button.dataset.action === "startYearJob") {
        startYearJob();
      }
    });
  });
  document.querySelectorAll("[data-job-field]").forEach((field) => {
    field.addEventListener("input", () => {
      const key = field.dataset.jobField;
      state[key] = field.type === "checkbox" ? field.checked : field.value;
      if (key === "adminToken") localStorage.setItem("f1-admin-token", state.adminToken);
    });
    field.addEventListener("change", () => {
      const key = field.dataset.jobField;
      state[key] = field.type === "checkbox" ? field.checked : field.value;
      if (key === "adminToken") localStorage.setItem("f1-admin-token", state.adminToken);
    });
  });
  document.querySelectorAll("[data-job-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedJobId = button.dataset.jobId;
      state.selectedJobLog = "";
      render();
    });
  });
  document.querySelectorAll("[data-job-log]").forEach((button) => {
    button.addEventListener("click", () => loadJobLog(button.dataset.jobLog));
  });
  document.querySelectorAll("[data-photo-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const model = state.data.models.find((item) => item.id === form.dataset.photoForm);
      const input = form.querySelector("input[name='photoUrl']");
      savePhoto(model, input.value.trim());
      input.value = "";
      render();
    });
  });
}

async function boot() {
  const response = await fetch(DATA_URL);
  state.data = await response.json();
  if (!location.hash) location.hash = "#/collection";
  window.addEventListener("hashchange", render);
  render();
}

boot().catch((error) => {
  app.innerHTML = `<main class="loading-panel"><strong>Data se nepodařilo načíst</strong><span>${escapeHtml(error.message)}</span></main>`;
});
