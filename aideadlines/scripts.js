/* ============================================================
   AI Conference Deadlines — Main Script
   ============================================================ */

// --- Constants ---
const TIERS = { 'A*': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4 };
const TIER_COLORS = ['#d4a017', '#0d9488', '#3a6fb8', '#9a6a40', '#5a5a64'];
const RATING_OPTIONS = ['All', 'A*', 'A', 'B', 'C', 'D'];
const DAY = 86400000;

function tierColor(rating) {
  const idx = TIERS[rating];
  return idx != null ? TIER_COLORS[idx] : null;
}

function pad2(n) { return String(Math.floor(n)).padStart(2, '0'); }

function urgencyOf(msLeft) {
  const days = msLeft / DAY;
  if (days < 7)  return 'urgent';
  if (days < 30) return 'soon';
  return 'normal';
}

// --- Application State ---
const state = {
  upcoming: [],
  archive: null,
  filter: {
    q: '',
    tags: [],        // empty = all
    minRating: 'C',
    showPast: false,
    showEstimated: true,
  },
  timers: new Map(), // confId → intervalId
};

// --- Theme Management ---
function getThemePref() {
  const stored = localStorage.getItem('theme');
  if (stored) return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  localStorage.setItem('theme', theme);
  // Update sun/moon icon visibility
  const sunIcon  = document.getElementById('sunIcon');
  const moonIcon = document.getElementById('moonIcon');
  if (sunIcon)  sunIcon.style.display  = theme === 'dark' ? 'block' : 'none';
  if (moonIcon) moonIcon.style.display = theme === 'dark' ? 'none'  : 'block';
}

// --- Filtering ---
function applyFilter(list) {
  const f = state.filter;
  const now = Date.now();
  return list.filter(conf => {
    const deadline = conf.deadline ? new Date(conf.deadline).getTime() : null;
    const isPast = !conf.isApproximateDeadline && deadline && deadline < now;
    if (!f.showPast && isPast) return false;
    if (conf.isApproximateDeadline && deadline && deadline < now) return false;
    if (!f.showEstimated && conf.isApproximateDeadline) return false;

    if (f.minRating !== 'All') {
      const ct = TIERS[conf.rating];
      if (ct == null) return false;
      const minT = TIERS[f.minRating] ?? 99;
      if (ct > minT) return false;
    }

    if (f.tags.length) {
      const ct = conf.tags || [];
      if (!f.tags.some(tag => ct.includes(tag))) return false;
    }

    if (f.q) {
      const q = f.q.toLowerCase();
      const hay = ((conf.shortname || '') + ' ' + (conf.title || '')).toLowerCase();
      if (!hay.includes(q)) return false;
    }

    return true;
  });
}

function sortConferences(list) {
  return list.slice().sort((a, b) => {
    const aDeadline = a.deadline ? new Date(a.deadline).getTime() : Infinity;
    const bDeadline = b.deadline ? new Date(b.deadline).getTime() : Infinity;
    return aDeadline - bDeadline;
  });
}

function getConferenceList() {
  let base = [...state.upcoming];
  if (state.filter.showPast && state.archive) base = base.concat(state.archive);
  return sortConferences(applyFilter(base));
}

function allConferences() {
  let base = [...state.upcoming];
  if (state.archive) base = base.concat(state.archive);
  return base;
}

// --- Card Rendering ---
function parseAcronymYear(conf) {
  const shortname = conf.shortname || conf.title || '';
  const m = shortname.match(/^(.*?)\s+(\d{4})$/);
  if (m) return { acronym: m[1], year: m[2] };
  // fallback: year from deadline
  const yr = conf.deadline ? new Date(conf.deadline).getFullYear() : '';
  return { acronym: shortname, year: yr };
}

function formatDeadlineFull(isoStr, timezone) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const opts = { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' };
  if (timezone) opts.timeZone = timezone;
  try {
    return d.toLocaleString('en-US', opts);
  } catch {
    return d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });
  }
}

function formatDateShort(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr.includes('T') ? isoStr : isoStr + 'T00:00:00Z');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}

function formatConfDates(conf) {
  if (!conf.conferenceStartDate) return '';
  const isApprox = conf.isApproximateDeadline;
  const opts = isApprox
    ? { year: 'numeric', month: 'short', timeZone: 'UTC' }
    : { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' };
  const start = new Date(conf.conferenceStartDate + (conf.conferenceStartDate.includes('T') ? '' : 'T00:00:00Z'));
  let str = (isApprox ? '~' : '') + start.toLocaleDateString('en-US', opts);
  if (conf.conferenceEndDate && conf.conferenceEndDate !== conf.conferenceStartDate) {
    const end = new Date(conf.conferenceEndDate + (conf.conferenceEndDate.includes('T') ? '' : 'T00:00:00Z'));
    str += ' — ' + (isApprox ? '~' : '') + end.toLocaleDateString('en-US', opts);
  }
  return str;
}

function countdownTilesHTML(ms, color) {
  const days = Math.floor(ms / DAY);
  const hrs  = Math.floor((ms % DAY) / 3600000);
  const mins = Math.floor((ms % 3600000) / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  const tiles = [
    { v: pad2(days), u: 'days' },
    { v: pad2(hrs),  u: 'hrs'  },
    { v: pad2(mins), u: 'min'  },
    { v: pad2(secs), u: 'sec'  },
  ];
  return tiles.map(t =>
    `<div class="count-tile" style="color:${color}">
       <div class="count-value">${t.v}</div>
       <div class="count-unit">${t.u}</div>
     </div>`
  ).join('');
}

function updateCountdown(conf, cardEl) {
  const tilesEl    = cardEl.querySelector('.countdown-tiles');
  const chipEl     = cardEl.querySelector('.urgency-chip');
  const abstractEl = cardEl.querySelector('.abstract-countdown');

  const now        = Date.now();
  const deadline   = new Date(conf.deadline).getTime();
  const ms         = Math.max(0, deadline - now);
  const u          = urgencyOf(ms);
  const urgColors  = { urgent: 'var(--urgent)', soon: 'var(--soon)', normal: 'var(--normal)' };
  const color      = urgColors[u];

  if (tilesEl) {
    tilesEl.innerHTML = countdownTilesHTML(ms, color);
  }

  if (chipEl) {
    const labels = { urgent: '<7d', soon: '<30d', normal: 'later' };
    chipEl.style.color = color;
    chipEl.querySelector('.urgency-dot').style.background = color;
    chipEl.querySelector('.urgency-label').textContent = labels[u];
  }

  // Abstract countdown
  if (abstractEl && conf.abstractDeadline) {
    const abDeadline = new Date(conf.abstractDeadline).getTime();
    const abMs = Math.max(0, abDeadline - now);
    if (abMs > 0) {
      const abDays = Math.floor(abMs / DAY);
      const abHrs  = Math.floor((abMs % DAY) / 3600000);
      const abMins = Math.floor((abMs % 3600000) / 60000);
      abstractEl.textContent = `${abDays}d ${pad2(abHrs)}h ${pad2(abMins)}m`;
    } else {
      // Abstract deadline passed — update the whole row
      const row = cardEl.querySelector('.abstract-row');
      if (row) {
        row.innerHTML = `
          <span class="abstract-status passed">✓</span>
          <span class="abstract-text">Abstract passed</span>
          <span class="abstract-date">${formatDateShort(conf.abstractDeadline)}</span>`;
      }
    }
  }
}

function createCard(conf) {
  const now = Date.now();
  const deadline = conf.deadline ? new Date(conf.deadline).getTime() : null;
  const isApprox = conf.isApproximateDeadline || false;
  const isPast = !isApprox && deadline && deadline < now;

  const { acronym, year } = parseAcronymYear(conf);
  const tc = tierColor(conf.rating);
  const hairlineColor = tc || 'var(--text-dim)';
  const hairlineOpacity = tc ? '0.95' : '0.35';

  // Urgency for live countdowns
  const ms = deadline ? Math.max(0, deadline - now) : 0;
  const u = (isApprox || isPast) ? 'normal' : urgencyOf(ms);
  const urgColors = { urgent: 'var(--urgent)', soon: 'var(--soon)', normal: 'var(--normal)' };
  const urgColor = urgColors[u];
  const urgLabels = { urgent: '<7d', soon: '<30d', normal: 'later' };

  // Build hairline style
  const hairlineStyle = `background:${hairlineColor};opacity:${hairlineOpacity};`;

  // Ribbon
  const ribbonHTML = conf.rating && tc
    ? `<div class="card-ribbon" style="background:${tc}">${conf.rating}</div>`
    : '';

  // Badges
  let badges = '';
  if (isApprox) badges += `<span class="card-badge estimated">estimated</span>`;
  if (isPast)   badges += `<span class="card-badge closed">closed</span>`;

  // Meta row
  let metaHTML = '';
  const confDates = formatConfDates(conf);
  if (conf.location) {
    metaHTML += `<span class="meta-item">
      <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 11s4-3.5 4-7a4 4 0 10-8 0c0 3.5 4 7 4 7z"/><circle cx="6" cy="4" r="1.4"/></svg>
      ${conf.location}</span>`;
  }
  if (confDates) {
    metaHTML += `<span class="meta-item">
      <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1.5" y="2.5" width="9" height="8" rx="1"/><path d="M1.5 5h9M4 1.5v2M8 1.5v2"/></svg>
      ${confDates}</span>`;
  }
  if (conf.h5Index != null) {
    metaHTML += `<span class="meta-item"><span class="h5-label">h5</span>${conf.h5Index}</span>`;
  }

  // Tags
  const tagsHTML = (conf.tags && conf.tags.length)
    ? `<div class="card-tags">${conf.tags.map(t => `<span class="conf-tag">${t}</span>`).join('')}</div>`
    : '';

  // Note
  const noteHTML = conf.note
    ? `<div class="card-note">${escHtml(conf.note)}</div>`
    : '';

  // Countdown / deadline section
  let countdownContent = '';
  let urgencyChipHTML = '';

  if (isPast) {
    const daysAgo = Math.round((now - deadline) / DAY);
    const pastDateStr = new Date(deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    countdownContent = `<div class="past-deadline">
      <span class="past-date">${pastDateStr}</span>
      <span class="past-ago"> · ${daysAgo} day${daysAgo !== 1 ? 's' : ''} ago</span>
    </div>`;
  } else if (isApprox) {
    const rawDays = deadline ? Math.max(0, Math.floor((deadline - now) / DAY)) : 0;
    const displayDays = rawDays < 10 ? rawDays : Math.round(rawDays / 10) * 10;
    countdownContent = `<div class="approx-countdown">
      <span class="approx-tilde">~</span>
      <span class="approx-days">${displayDays}</span>
      <span class="approx-unit">days</span>
    </div>`;
  } else {
    urgencyChipHTML = `<span class="urgency-chip" style="color:${urgColor}">
      <span class="urgency-dot" style="background:${urgColor}"></span>
      <span class="urgency-label">${urgLabels[u]}</span>
    </span>`;
    countdownContent = `<div class="countdown-tiles">${countdownTilesHTML(ms, urgColor)}</div>`;
  }

  const deadlineLabelText = isPast ? 'Submission closed'
    : isApprox ? 'Submission in (estimated)'
    : 'Submission closes in';

  let deadlineDateHTML = '';
  if (!isPast && conf.deadline) {
    const dateStr = isApprox
      ? `~ ${new Date(conf.deadline).toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' })} · estimated from past trends`
      : formatDeadlineFull(conf.deadline, conf.timezone);
    deadlineDateHTML = `<div class="deadline-date">${dateStr}</div>`;
  }

  // Abstract row
  let abstractHTML = '';
  if (conf.abstractDeadline) {
    const abDeadline = new Date(conf.abstractDeadline).getTime();
    const abPast = abDeadline < now;
    const abDateStr = formatDateShort(conf.abstractDeadline);

    if (abPast) {
      abstractHTML = `<div class="abstract-row">
        <span class="abstract-status passed">✓</span>
        <span class="abstract-text">Abstract passed</span>
        <span class="abstract-date">${abDateStr}</span>
      </div>`;
    } else {
      const abMs = abDeadline - now;
      const abDays = Math.floor(abMs / DAY);
      const abHrs  = Math.floor((abMs % DAY) / 3600000);
      const abMins = Math.floor((abMs % 3600000) / 60000);
      abstractHTML = `<div class="abstract-row">
        <span class="abstract-status pending"></span>
        <span class="abstract-text">Abstract in</span>
        <span class="abstract-countdown">${abDays}d ${pad2(abHrs)}h ${pad2(abMins)}m</span>
        <span class="abstract-date">${abDateStr}</span>
      </div>`;
    }
  }

  // Visit link
  let visitHTML = '';
  if (conf.website && !isApprox) {
    visitHTML = `<a href="${escHtml(conf.website)}" class="visit-link" target="_blank" rel="noopener noreferrer">
      Visit site
      <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M2 6h7M5.5 2.5L9 6l-3.5 3.5"/></svg>
    </a>`;
  }

  const article = document.createElement('article');
  article.className = `conf-card${isApprox ? ' is-approx' : ''}${isPast ? ' is-past' : ''}`;
  article.id = `card-${conf.id}`;
  article.innerHTML = `
    <div class="card-hairline" style="${hairlineStyle}"></div>
    ${ribbonHTML}
    <div class="card-head">
      <div class="card-acronym-row">
        <span class="card-acronym">${escHtml(acronym)}</span>
        <span class="card-year">${year}</span>
        ${badges}
      </div>
      <div class="card-name">${escHtml(conf.title || '')}</div>
    </div>
    ${metaHTML ? `<div class="card-meta">${metaHTML}</div>` : ''}
    ${tagsHTML}
    ${noteHTML}
    <div class="card-deadline">
      <div class="deadline-header">
        <span class="deadline-label">${deadlineLabelText}</span>
        ${urgencyChipHTML}
      </div>
      ${countdownContent}
      ${deadlineDateHTML}
    </div>
    ${abstractHTML}
    ${visitHTML}
  `;

  return article;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// --- Rendering ---
function clearTimers() {
  state.timers.forEach(id => clearInterval(id));
  state.timers.clear();
}

function render() {
  const grid = document.getElementById('conferenceGrid');
  if (!grid) return;

  clearTimers();
  grid.innerHTML = '';

  const confs = getConferenceList();
  updateCounts(confs.length);

  const scrollBtn = document.getElementById('scrollToNowBtn');

  if (confs.length === 0) {
    grid.innerHTML = `<div class="empty-state">No conferences match. Try adjusting your filters.</div>`;
    if (scrollBtn) scrollBtn.hidden = true;
    return;
  }

  const now = Date.now();

  // Find where past conferences start (past ones have earlier deadlines, so they come first in ascending sort)
  let dividerInserted = false;
  let hasPast = false;

  confs.forEach((conf, i) => {
    const deadline = conf.deadline ? new Date(conf.deadline).getTime() : null;
    const isPast = !conf.isApproximateDeadline && deadline && deadline < now;

    // Insert divider at the boundary: first future conference after past ones
    if (!dividerInserted && !isPast && i > 0) {
      const prevDeadline = confs[i - 1].deadline ? new Date(confs[i - 1].deadline).getTime() : null;
      const prevIsPast = !confs[i - 1].isApproximateDeadline && prevDeadline && prevDeadline < now;
      if (prevIsPast) {
        const divider = document.createElement('div');
        divider.id = 'now-divider';
        divider.className = 'now-divider';
        divider.textContent = 'Now';
        grid.appendChild(divider);
        dividerInserted = true;
      }
    }

    if (isPast) hasPast = true;

    const card = createCard(conf);
    grid.appendChild(card);

    if (!conf.isApproximateDeadline && !isPast && deadline) {
      const id = setInterval(() => updateCountdown(conf, card), 1000);
      state.timers.set(conf.id, id);
    }
  });

  // Show/hide the jump button
  if (scrollBtn) {
    scrollBtn.hidden = !hasPast;
  }
}

function updateCounts(filtered) {
  const total = allConferences().length;
  const el = document.getElementById('filteredCount');
  const totalEl = document.getElementById('totalCount');
  if (el) el.textContent = filtered;
  if (totalEl) totalEl.textContent = ` / ${total}`;


  // Also update sheet counts
  const sf = document.getElementById('sheetFilteredCount');
  const st = document.getElementById('sheetTotalCount');
  if (sf) sf.textContent = filtered;
  if (st) st.textContent = total;
}

// --- Filter UI ---
function buildRatingSegments(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = RATING_OPTIONS.map(opt => {
    const active = opt === state.filter.minRating;
    return `<button class="segment-btn${active ? ' active' : ''}" data-rating="${opt}">${opt}</button>`;
  }).join('');
  el.querySelectorAll('.segment-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.filter.minRating = btn.dataset.rating;
      syncFiltersToUI();
      render();
    });
  });
}

function buildTagChips(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;

  const allTags = new Set();
  const all = [...state.upcoming, ...(state.archive || [])];
  all.forEach(c => (c.tags || []).forEach(t => allTags.add(t)));
  const tags = Array.from(allTags).sort();

  const allActive = state.filter.tags.length === 0;
  el.innerHTML = `<button class="chip-btn${allActive ? ' active' : ''}" data-tag="ALL">All</button>` +
    tags.map(t => {
      const active = state.filter.tags.includes(t);
      return `<button class="chip-btn${active ? ' active' : ''}" data-tag="${t}">${t}</button>`;
    }).join('');

  el.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tag = btn.dataset.tag;
      if (tag === 'ALL') {
        state.filter.tags = [];
      } else {
        if (state.filter.tags.includes(tag)) {
          state.filter.tags = state.filter.tags.filter(x => x !== tag);
        } else {
          state.filter.tags = [...state.filter.tags, tag];
        }
        if (state.filter.tags.length === 0) state.filter.tags = [];
      }
      syncFiltersToUI();
      render();
    });
  });
}

function syncToggle(btnId, trackInBtn, value) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.dataset.active = String(value);
  btn.setAttribute('aria-pressed', String(value));
  const track = btn.querySelector('.toggle-track');
  if (track) track.classList.toggle('active', value);
}

function syncFiltersToUI() {
  // Rating segments
  ['ratingSegments', 'mobileRatingSegments'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.querySelectorAll('.segment-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.rating === state.filter.minRating);
    });
  });

  // Tag chips
  ['tagChips', 'mobileTagChips'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const allActive = state.filter.tags.length === 0;
    el.querySelectorAll('.chip-btn').forEach(btn => {
      const tag = btn.dataset.tag;
      btn.classList.toggle('active', tag === 'ALL' ? allActive : state.filter.tags.includes(tag));
    });
  });

  // Toggles
  syncToggle('pastToggle', '.toggle-track', state.filter.showPast);
  syncToggle('estimatedToggle', '.toggle-track', state.filter.showEstimated);
  syncToggle('mobilePastToggle', '.toggle-track', state.filter.showPast);
  syncToggle('mobileEstimatedToggle', '.toggle-track', state.filter.showEstimated);

  // Mobile filter badge
  updateFilterBadge();
}

function updateFilterBadge() {
  const count =
    state.filter.tags.length +
    (state.filter.minRating !== 'All' ? 1 : 0) +
    (state.filter.showPast ? 1 : 0) +
    (!state.filter.showEstimated ? 1 : 0);

  const badge = document.getElementById('filterBadge');
  if (badge) {
    badge.textContent = count;
    badge.hidden = count === 0;
  }
}

// --- Event Listeners ---
function setupEventListeners() {
  document.getElementById('currentYear').textContent = new Date().getFullYear();

  // Theme toggle
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const isDark = document.documentElement.classList.contains('dark');
      applyTheme(isDark ? 'light' : 'dark');
    });
  }

  // System theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (!localStorage.getItem('theme')) applyTheme(e.matches ? 'dark' : 'light');
  });

  // Jump-to-now button
  const scrollToNowBtn = document.getElementById('scrollToNowBtn');
  if (scrollToNowBtn) {
    scrollToNowBtn.addEventListener('click', () => {
      const divider = document.getElementById('now-divider');
      if (divider) divider.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }

  // Search
  const searchInput = document.getElementById('searchInput');
  const searchClear = document.getElementById('searchClear');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      state.filter.q = searchInput.value;
      if (searchClear) searchClear.hidden = !searchInput.value;
      render();
    });
    // Ctrl/Cmd+F focuses search
    document.addEventListener('keydown', e => {
      if (e.key === 'f' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        searchInput.focus();
      }
    });
  }
  if (searchClear) {
    searchClear.addEventListener('click', () => {
      searchInput.value = '';
      state.filter.q = '';
      searchClear.hidden = true;
      searchInput.focus();
      render();
    });
  }

  // Past toggle (desktop)
  const pastToggle = document.getElementById('pastToggle');
  if (pastToggle) {
    pastToggle.addEventListener('click', () => {
      state.filter.showPast = !state.filter.showPast;
      if (state.filter.showPast && state.archive === null) {
        loadArchiveAndRender();
        return;
      }
      syncFiltersToUI();
      render();
    });
  }

  // Estimated toggle (desktop)
  const estToggle = document.getElementById('estimatedToggle');
  if (estToggle) {
    estToggle.addEventListener('click', () => {
      state.filter.showEstimated = !state.filter.showEstimated;
      syncFiltersToUI();
      render();
    });
  }

  // Mobile filter button
  const mobileBtn = document.getElementById('mobileFilterBtn');
  const filterSheet = document.getElementById('filterSheet');
  if (mobileBtn && filterSheet) {
    mobileBtn.addEventListener('click', () => {
      const isOpen = !filterSheet.hidden;
      filterSheet.hidden = isOpen;
      mobileBtn.classList.toggle('open', !isOpen);
      mobileBtn.setAttribute('aria-expanded', String(!isOpen));
    });
  }

  // Mobile toggles
  const mobilePastToggle = document.getElementById('mobilePastToggle');
  if (mobilePastToggle) {
    mobilePastToggle.addEventListener('click', () => {
      state.filter.showPast = !state.filter.showPast;
      if (state.filter.showPast && state.archive === null) {
        loadArchiveAndRender();
        return;
      }
      syncFiltersToUI();
      render();
    });
  }
  const mobileEstToggle = document.getElementById('mobileEstimatedToggle');
  if (mobileEstToggle) {
    mobileEstToggle.addEventListener('click', () => {
      state.filter.showEstimated = !state.filter.showEstimated;
      syncFiltersToUI();
      render();
    });
  }

  // Reset filters
  const resetBtn = document.getElementById('resetFilters');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      state.filter.q = '';
      state.filter.tags = [];
      state.filter.minRating = 'All';
      state.filter.showPast = false;
      state.filter.showEstimated = true;
      const searchInput = document.getElementById('searchInput');
      if (searchInput) searchInput.value = '';
      const searchClear = document.getElementById('searchClear');
      if (searchClear) searchClear.hidden = true;
      syncFiltersToUI();
      buildTagChips('tagChips');
      buildTagChips('mobileTagChips');
      buildRatingSegments('ratingSegments');
      buildRatingSegments('mobileRatingSegments');
      render();
    });
  }
}

// --- Data Loading ---
async function loadInitialData() {
  const loadingEl = document.getElementById('loadingState');
  try {
    const res = await fetch('data/conferences.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.upcoming = await res.json();

    if (loadingEl) loadingEl.hidden = true;

    buildRatingSegments('ratingSegments');
    buildRatingSegments('mobileRatingSegments');
    buildTagChips('tagChips');
    buildTagChips('mobileTagChips');
    syncFiltersToUI();
    render();
  } catch (err) {
    console.error('Failed to load conferences:', err);
    if (loadingEl) {
      loadingEl.innerHTML = '<p style="color:var(--urgent);padding:40px;text-align:center">Failed to load conference data. Please refresh and try again.</p>';
    }
  }
}

async function loadArchiveAndRender() {
  if (state.archive !== null) { syncFiltersToUI(); render(); return; }
  try {
    const res = await fetch('data/conferences_archive.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.archive = await res.json();
  } catch (err) {
    console.error('Failed to load archive:', err);
    state.archive = [];
  }
  syncFiltersToUI();
  render();
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
  applyTheme(getThemePref());
  setupEventListeners();
  loadInitialData();
});
