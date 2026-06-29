// --- DOM Elements ---
const conferenceGrid = document.getElementById('conferenceGrid');
const tagFilterContainer = document.getElementById('tagFilterContainer');
const showPastToggle = document.getElementById('showPastToggle');
const showApproxFutureToggle = document.getElementById('showApproxFutureToggle');
const minH5IndexInput = document.getElementById('minH5Index');
const minRatingSelect = document.getElementById('minRating');
const conferenceNameFilterInput = document.getElementById('conferenceNameFilter');
const currentYearSpan = document.getElementById('currentYear');
const themeToggle = document.getElementById('themeToggle');

const messageModal = document.getElementById('messageModal');
const modalTitle = document.getElementById('modalTitle');
const modalMessage = document.getElementById('modalMessage');
const closeModalButton = document.getElementById('closeModalButton');
const loadingState = document.getElementById('loadingState');
const filterToggle = document.getElementById('filterToggle');
const filterControls = document.getElementById('filterControls');

const nextUpEl = document.getElementById('nextUp');
const aoeClockEl = document.getElementById('aoeClock');
const statTrackedEl = document.getElementById('statTracked');
const statWeekEl = document.getElementById('statWeek');

const DAY_MS = 1000 * 60 * 60 * 24;

// --- Theme Management ---
function getThemePreference() {
  const storedTheme = localStorage.getItem('theme');
  if (storedTheme) {
    return storedTheme;
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function setTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  localStorage.setItem('theme', theme);
}

function initTheme() {
  const preferredTheme = getThemePreference();
  setTheme(preferredTheme);

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
      setTheme(e.matches ? 'dark' : 'light');
    }
  });
}

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const isDark = document.documentElement.classList.contains('dark');
    setTheme(isDark ? 'light' : 'dark');
  });
}

// --- Application State ---
let upcomingConferencesData = [];
let archiveConferencesData = null;
let nextUpIntervalId = null;
let nextUpConference = null;

let currentFilterSettings = {
  selectedTags: new Set(["ALL"]),
  showPast: false,
  showApproxFuture: true,
  minH5: null,
  minRating: "",
  nameFilter: ""
};

const ratingOrder = { "A*": 5, "A": 4, "B": 3, "C": 2, "D": 1 };

// --- Utility Functions ---
function showModal(title, msg) {
  if (modalTitle && modalMessage && messageModal && closeModalButton) {
    modalTitle.textContent = title;
    modalMessage.textContent = msg;
    messageModal.classList.add('is-open');
  } else {
    console.error("Modal elements not found. Message:", title, msg);
    alert(`${title}\n${msg}`);
  }
}

if (closeModalButton) {
  closeModalButton.addEventListener('click', () => {
    if (messageModal) messageModal.classList.remove('is-open');
  });
}
if (messageModal) {
  messageModal.addEventListener('click', (e) => {
    if (e.target === messageModal) messageModal.classList.remove('is-open');
  });
}

// --- Urgency: the signature hue-shift, encoded from time remaining ---
const URGENCY_CLASSES = ['is-critical', 'is-soon', 'is-upcoming', 'is-past'];

function urgencyClassFor(timeLeftMs) {
  if (timeLeftMs <= 0) return 'is-past';
  const days = timeLeftMs / DAY_MS;
  if (days < 1) return 'is-critical';
  if (days < 7) return 'is-soon';
  if (days < 30) return 'is-upcoming';
  return ''; // far away → calm "cool" default
}

function applyUrgency(card, deadlineStr) {
  // Only swap the urgency modifier so the entrance animation never restarts.
  card.classList.remove(...URGENCY_CLASSES);
  const u = urgencyClassFor(new Date(deadlineStr).getTime() - Date.now());
  if (u) card.classList.add(u);
}

// progress toward the deadline within a 90-day horizon (fuller = closer)
function proximityPercent(timeLeftMs) {
  const days = timeLeftMs / DAY_MS;
  return Math.max(0, Math.min(1, 1 - days / 90)) * 100;
}

function getUrgencyBadge(conference) {
  const timeLeft = new Date(conference.deadline).getTime() - Date.now();
  if (timeLeft <= 0) return '';
  const days = timeLeft / DAY_MS;
  if (days < 1) return '<span class="urgency-badge">Less than 24h</span>';
  if (days < 7) return '<span class="urgency-badge">Due this week</span>';
  if (days < 30) return '<span class="urgency-badge">Due this month</span>';
  return '';
}

// --- Countdown rendering ---
function pad(n) { return String(n).padStart(2, '0'); }

function breakdown(timeLeftMs) {
  return {
    days: Math.floor(timeLeftMs / DAY_MS),
    hours: Math.floor((timeLeftMs % DAY_MS) / (1000 * 60 * 60)),
    minutes: Math.floor((timeLeftMs % (1000 * 60 * 60)) / (1000 * 60)),
    seconds: Math.floor((timeLeftMs % (1000 * 60)) / 1000)
  };
}

function updateSpecificCountdown(targetDateStr, countdownElementId, label, isApproximate = false) {
  const el = document.getElementById(countdownElementId);
  if (!el) return;

  const timeLeft = new Date(targetDateStr).getTime() - Date.now();

  if (timeLeft <= 0) {
    const passedLabel = isApproximate ? `${label} (est.) passed` : `${label} passed`;
    el.innerHTML = `<div class="ended-banner">${passedLabel}</div>`;
    return;
  }

  if (isApproximate) {
    const daysLeft = Math.floor(timeLeft / DAY_MS);
    let approxText;
    if (daysLeft < 10) approxText = '< 10 days';
    else approxText = `~${Math.round(daysLeft / 10) * 10} days`;
    el.innerHTML = `
      <div class="cd-label">${label}</div>
      <div class="cd-approx">${approxText}</div>`;
    return;
  }

  const { days, hours, minutes, seconds } = breakdown(timeLeft);
  const pct = proximityPercent(timeLeft).toFixed(1);
  el.innerHTML = `
    <div class="cd-label">${label} · in</div>
    <div class="cd-meter"><span style="width:${pct}%"></span></div>
    <div class="cd-grid">
      <div class="cd-cell"><span class="cd-num">${pad(days)}</span><span class="cd-unit">days</span></div>
      <div class="cd-cell"><span class="cd-num">${pad(hours)}</span><span class="cd-unit">hrs</span></div>
      <div class="cd-cell"><span class="cd-num">${pad(minutes)}</span><span class="cd-unit">min</span></div>
      <div class="cd-cell"><span class="cd-num">${pad(seconds)}</span><span class="cd-unit">sec</span></div>
    </div>`;
}

function updateSmallCountdown(targetDateStr, countdownElementId, label) {
  const el = document.getElementById(countdownElementId);
  if (!el) return;

  const timeLeft = new Date(targetDateStr).getTime() - Date.now();
  if (timeLeft <= 0) {
    el.innerHTML = `<div class="ended-banner">${label} passed</div>`;
    return;
  }

  const { days, hours, minutes } = breakdown(timeLeft);
  el.innerHTML = `
    <div class="cd-abstract">
      <span>${label} in</span>
      <span class="vals">
        <span class="chip">${pad(days)}d</span>
        <span class="chip">${pad(hours)}h</span>
        <span class="chip">${pad(minutes)}m</span>
      </span>
    </div>`;
}

// --- Format Date Helper ---
function formatDate(dateString, formattingOptions = {}) {
  if (!dateString) return 'N/A';

  const date = new Date(
    (dateString.includes('T') || dateString.endsWith('Z'))
      ? dateString
      : dateString + 'T00:00:00Z'
  );

  let effectiveOptions = {};
  effectiveOptions.timeZone = formattingOptions.displayTimezoneIana || 'UTC';
  // "Etc/GMT+12" is the IANA spelling of Anywhere-on-Earth (UTC−12); show it as AoE.
  const isAoE = effectiveOptions.timeZone === 'Etc/GMT+12';

  if (formattingOptions.monthYearOnly) {
    effectiveOptions.year = 'numeric';
    effectiveOptions.month = 'short';
  } else {
    effectiveOptions.year = 'numeric';
    effectiveOptions.month = 'short';
    effectiveOptions.day = 'numeric';
    if (formattingOptions.includeTime) {
      effectiveOptions.hour = '2-digit';
      effectiveOptions.minute = '2-digit';
      if (formattingOptions.includeTimezoneName) {
        effectiveOptions.timeZoneName = 'short';
      }
    }
  }
  let out = date.toLocaleDateString(undefined, effectiveOptions);
  if (isAoE && effectiveOptions.timeZoneName) out = out.replace(/GMT[+-]12/, 'AoE');
  return out;
}

// --- SVG icons (small, instrument-style) ---
const ICON_PIN = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.145l.002-.001L10 18.43l-5.192-5.192a6.875 6.875 0 010-9.719l.001-.001c2.7-2.7 7.075-2.7 9.774 0l.001.001a6.875 6.875 0 010 9.719L10 18.43zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd" /></svg>`;
const ICON_CAL = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.75 3A2.25 2.25 0 003.5 5.25v9.5A2.25 2.25 0 005.75 17h8.5A2.25 2.25 0 0016.5 14.75v-9.5A2.25 2.25 0 0014.25 3h-8.5zM5 5.25c0-.414.336-.75.75-.75h8.5c.414 0 .75.336.75.75v9.5c0 .414-.336.75-.75.75h-8.5a.75.75 0 01-.75-.75v-9.5z" clip-rule="evenodd" /><path d="M7 8.5h2v2H7v-2zm0 3h2v2H7v-2zm4-3h2v2h-2v-2z" /></svg>`;

// --- Create Conference Cards ---
function createConferenceCard(conference, index = 0) {
  const card = document.createElement('div');
  card.id = `card-${conference.id}`;
  card.className = 'conf-card' + (conference.isApproximateDeadline ? ' is-approx' : '');
  card.style.animationDelay = `${Math.min(index, 12) * 45}ms`;
  card.tabIndex = 0;

  const isApprox = conference.isApproximateDeadline || false;
  const approxDateFormatting = { monthYearOnly: true, displayTimezoneIana: conference.timezone || 'UTC' };
  const preciseDeadlineFormat = { includeTime: true, includeTimezoneName: true, displayTimezoneIana: conference.timezone || 'UTC' };
  const conferenceDayFormat = { displayTimezoneIana: conference.timezone || 'UTC' };

  // eyebrow: CORE rating + h5-index
  let eyebrowParts = [];
  if (conference.rating) {
    const top = ratingOrder[conference.rating] >= ratingOrder['A'];
    eyebrowParts.push(`<span class="conf-rank${top ? ' rank-top' : ''}">CORE&nbsp;<b>${conference.rating}</b></span>`);
  }
  if (conference.h5Index !== undefined) {
    eyebrowParts.push(`<span class="conf-rank">h5&nbsp;<b>${conference.h5Index}</b></span>`);
  }
  const eyebrowHTML = eyebrowParts.length
    ? `<div class="conf-eyebrow">${eyebrowParts.join('')}</div>` : '';

  // title: shortname prominent, full title as a quiet mono subtitle
  let titleHTML = '';
  const shortname = conference.shortname;
  const fullTitle = conference.title;
  if (shortname && fullTitle) {
    titleHTML = `<h2 class="conf-title">${shortname}<span class="full">${fullTitle}</span></h2>`;
  } else if (fullTitle) {
    titleHTML = `<h2 class="conf-title">${fullTitle}</h2>`;
  } else if (shortname) {
    titleHTML = `<h2 class="conf-title">${shortname}</h2>`;
  }

  // meta: location + conference dates
  let conferenceDateText;
  if (isApprox) {
    conferenceDateText = `~${formatDate(conference.conferenceStartDate, approxDateFormatting)}`;
  } else {
    conferenceDateText = formatDate(conference.conferenceStartDate, conferenceDayFormat);
    if (conference.conferenceEndDate && conference.conferenceEndDate !== conference.conferenceStartDate) {
      conferenceDateText += ` – ${formatDate(conference.conferenceEndDate, conferenceDayFormat)}`;
    }
  }
  let metaRows = '';
  if (conference.location) {
    metaRows += `<div class="conf-meta-row">${ICON_PIN}<span>${conference.location}</span></div>`;
  }
  if (conference.conferenceStartDate) {
    metaRows += `<div class="conf-meta-row">${ICON_CAL}<span>${conferenceDateText}</span></div>`;
  }
  const metaHTML = metaRows ? `<div class="conf-meta">${metaRows}</div>` : '';

  // tags + urgency badge
  let tagsHTML = '';
  const urgencyBadge = isApprox ? '' : getUrgencyBadge(conference);
  if ((conference.tags && conference.tags.length) || urgencyBadge) {
    tagsHTML = '<div class="conf-tags">';
    (conference.tags || []).forEach(tag => { tagsHTML += `<span class="conf-tag">${tag}</span>`; });
    tagsHTML += urgencyBadge;
    tagsHTML += '</div>';
  }

  const noteHTML = conference.note ? `<p class="conf-note">${conference.note}</p>` : '';

  // ---- foot: countdown + deadline line + abstract + CTA ----
  const deadlineLabel = isApprox ? 'Est. paper deadline' : 'Paper deadline';
  const mainDeadlineFmt = isApprox ? approxDateFormatting : preciseDeadlineFormat;
  const mainDeadlineText = (isApprox ? '~' : '') + formatDate(conference.deadline, mainDeadlineFmt);
  const deadlineLineHTML =
    `<p class="deadline-date-text">Deadline: <b>${mainDeadlineText}${isApprox ? ' (est.)' : ''}</b></p>`;

  let abstractHTML = '';
  if (conference.abstractDeadline) {
    const abstractFmt = isApprox ? approxDateFormatting : preciseDeadlineFormat;
    const abstractText = (isApprox ? '~' : '') + formatDate(conference.abstractDeadline, abstractFmt);
    abstractHTML = `
      <div id="countdown-abstract-${conference.id}" class="deadline-section"></div>
      <p class="deadline-date-text">Abstract: <b>${abstractText}${isApprox ? ' (est.)' : ''}</b></p>`;
  }

  let ctaHTML;
  if (isApprox) {
    ctaHTML = `<span class="conf-cta disabled">Estimated — no site yet</span>`;
  } else if (!conference.website) {
    ctaHTML = `<span class="conf-cta disabled">Site not available</span>`;
  } else {
    ctaHTML = `<a href="${conference.website}" target="_blank" rel="noopener noreferrer" class="conf-cta">Visit site <span class="arrow">→</span></a>`;
  }

  card.innerHTML = `
    <div>
      ${eyebrowHTML}
      ${titleHTML}
      ${metaHTML}
      ${tagsHTML}
      ${noteHTML}
    </div>
    <div class="conf-foot">
      <div id="countdown-deadline-${conference.id}" class="deadline-section"></div>
      ${deadlineLineHTML}
      ${abstractHTML}
      ${ctaHTML}
    </div>`;
  conferenceGrid.appendChild(card);

  if (!isApprox) applyUrgency(card, conference.deadline);

  updateSpecificCountdown(conference.deadline, `countdown-deadline-${conference.id}`, deadlineLabel, isApprox);
  if (conference.abstractDeadline && !isApprox) {
    updateSmallCountdown(conference.abstractDeadline, `countdown-abstract-${conference.id}`, 'Abstract');
  }

  if (!isApprox) {
    const intervalId = setInterval(() => {
      applyUrgency(card, conference.deadline);
      updateSpecificCountdown(conference.deadline, `countdown-deadline-${conference.id}`, deadlineLabel, false);
      if (conference.abstractDeadline) {
        updateSmallCountdown(conference.abstractDeadline, `countdown-abstract-${conference.id}`, 'Abstract');
      }
    }, 1000);
    card.dataset.intervalId = intervalId;
  }
}

// --- Featured "Next Deadline" ticker ---
function pickNextDeadline() {
  const now = Date.now();
  return upcomingConferencesData
    .filter(c => !c.isApproximateDeadline && c.deadline && new Date(c.deadline).getTime() > now)
    .sort((a, b) => new Date(a.deadline) - new Date(b.deadline))[0] || null;
}

function renderNextUp() {
  if (!nextUpEl) return;
  nextUpConference = pickNextDeadline();

  if (!nextUpConference) {
    nextUpEl.classList.remove('is-soon', 'is-critical');
    nextUpEl.innerHTML = `
      <div class="next-up-top">
        <span class="next-up-label"><span class="led" aria-hidden="true"></span> Next deadline</span>
      </div>
      <p class="next-up-empty">No upcoming confirmed deadlines right now. Enable “Show estimated” to see what's coming.</p>`;
    return;
  }

  const c = nextUpConference;
  const name = c.shortname || c.title || 'Conference';
  const when = formatDate(c.deadline, { includeTime: true, includeTimezoneName: true, displayTimezoneIana: c.timezone || 'UTC' });
  nextUpEl.innerHTML = `
    <div class="next-up-top">
      <span class="next-up-label"><span class="led" aria-hidden="true"></span> Next deadline</span>
    </div>
    <div class="next-up-name">${name}</div>
    <div class="next-up-sub">Paper submission · ${when}</div>
    <div class="next-up-clock" id="nextUpClock"></div>`;
  updateNextUp();
}

function updateNextUp() {
  if (!nextUpConference || !nextUpEl) return;
  const timeLeft = new Date(nextUpConference.deadline).getTime() - Date.now();

  if (timeLeft <= 0) { renderNextUp(); return; }

  const u = urgencyClassFor(timeLeft);
  nextUpEl.classList.toggle('is-soon', u === 'is-soon' || u === 'is-upcoming');
  nextUpEl.classList.toggle('is-critical', u === 'is-critical');

  const clock = document.getElementById('nextUpClock');
  if (!clock) return;
  const { days, hours, minutes, seconds } = breakdown(timeLeft);
  clock.innerHTML = `
    <div class="nu-cell"><span class="v">${pad(days)}</span><span class="u">days</span></div>
    <div class="nu-cell"><span class="v">${pad(hours)}</span><span class="u">hrs</span></div>
    <div class="nu-cell"><span class="v">${pad(minutes)}</span><span class="u">min</span></div>
    <div class="nu-cell"><span class="v">${pad(seconds)}</span><span class="u">sec</span></div>`;
}

// --- Live "Anywhere on Earth" clock ---
function updateAoeClock() {
  if (!aoeClockEl) return;
  aoeClockEl.textContent = new Date().toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    timeZone: 'Etc/GMT+12', hour12: false
  });
}

// --- Hero stats ---
function updateHeroStats() {
  if (statTrackedEl) statTrackedEl.textContent = upcomingConferencesData.length;
  if (statWeekEl) {
    const now = Date.now();
    const count = upcomingConferencesData.filter(c => {
      if (c.isApproximateDeadline || !c.deadline) return false;
      const t = new Date(c.deadline).getTime() - now;
      return t > 0 && t < 7 * DAY_MS;
    }).length;
    statWeekEl.textContent = count;
  }
}

// --- Populate Tag Filter ---
function populateTagFilter(sourceConferences) {
  if (!tagFilterContainer) return;
  const allTags = new Set();
  sourceConferences.forEach(conf => {
    if (conf.tags) conf.tags.forEach(tag => allTags.add(tag));
  });

  tagFilterContainer.innerHTML = '';

  const allButton = document.createElement('button');
  allButton.textContent = 'All Conferences';
  allButton.className = 'tag-button';
  allButton.addEventListener('click', () => {
    currentFilterSettings.selectedTags.clear();
    currentFilterSettings.selectedTags.add("ALL");
    setActiveTagButtons();
    applyAllFilters();
  });
  tagFilterContainer.appendChild(allButton);

  Array.from(allTags).sort().forEach(tag => {
    const button = document.createElement('button');
    button.textContent = tag;
    button.className = 'tag-button';
    button.addEventListener('click', () => {
      currentFilterSettings.selectedTags.delete("ALL");
      if (currentFilterSettings.selectedTags.has(tag)) {
        currentFilterSettings.selectedTags.delete(tag);
      } else {
        currentFilterSettings.selectedTags.add(tag);
      }
      if (currentFilterSettings.selectedTags.size === 0) {
        currentFilterSettings.selectedTags.add("ALL");
      }
      setActiveTagButtons();
      applyAllFilters();
    });
    tagFilterContainer.appendChild(button);
  });

  setActiveTagButtons();
}

function setActiveTagButtons() {
  const buttons = Array.from(tagFilterContainer.children);
  buttons.forEach(btn => {
    const tag = btn.textContent;
    if (tag === "All Conferences") {
      btn.classList.toggle('active', currentFilterSettings.selectedTags.has("ALL"));
    } else {
      btn.classList.toggle('active', currentFilterSettings.selectedTags.has(tag));
    }
  });
}

// --- Main Filtering and Rendering Logic ---
function applyAllFilters() {
  let baseData = [...upcomingConferencesData];
  if (currentFilterSettings.showPast && archiveConferencesData) {
    baseData = [...upcomingConferencesData, ...archiveConferencesData];
  }

  populateTagFilter(baseData);

  renderConferences(
    baseData,
    currentFilterSettings.selectedTags,
    currentFilterSettings.showPast,
    currentFilterSettings.showApproxFuture,
    currentFilterSettings.minH5,
    currentFilterSettings.minRating,
    currentFilterSettings.nameFilter
  );
}

function renderConferences(
  sourceConferenceData,
  selectedTags,
  shouldShowPast,
  shouldShowApproxFuture,
  minH5,
  minRatingVal,
  nameFilterVal
) {
  if (!conferenceGrid) return;

  Array.from(conferenceGrid.children).forEach(card => {
    const intervalId = card.dataset.intervalId;
    if (intervalId) clearInterval(Number(intervalId));
  });
  conferenceGrid.innerHTML = '';

  if (loadingState) loadingState.style.display = 'none';

  let filteredConferences = [...sourceConferenceData];
  const now = new Date();

  if (nameFilterVal) {
    const lowerCaseFilter = nameFilterVal.toLowerCase().trim();
    if (lowerCaseFilter) {
      filteredConferences = filteredConferences.filter(conf =>
        (conf.title && conf.title.toLowerCase().includes(lowerCaseFilter)) ||
        (conf.shortname && conf.shortname.toLowerCase().includes(lowerCaseFilter))
      );
    }
  }

  if (!shouldShowApproxFuture) {
    filteredConferences = filteredConferences.filter(conf => {
      const eventEndDateStr = conf.conferenceEndDate || conf.deadline || conf.conferenceStartDate;
      let isConsideredFuture = true;
      if (eventEndDateStr) {
        const eventEndDate = new Date(eventEndDateStr.includes('T') ? eventEndDateStr : eventEndDateStr + 'T23:59:59Z');
        isConsideredFuture = eventEndDate >= now;
      }
      return !(isConsideredFuture && conf.isApproximateDeadline);
    });
  }

  if (minH5 !== null && minH5 !== '') {
    const h5Threshold = parseInt(minH5, 10);
    if (!isNaN(h5Threshold)) {
      filteredConferences = filteredConferences.filter(conf =>
        conf.h5Index !== undefined && conf.h5Index >= h5Threshold
      );
    }
  }

  if (minRatingVal && ratingOrder[minRatingVal]) {
    const minRatingNumeric = ratingOrder[minRatingVal];
    filteredConferences = filteredConferences.filter(conf =>
      conf.rating && ratingOrder[conf.rating] && ratingOrder[conf.rating] >= minRatingNumeric
    );
  }

  if (!currentFilterSettings.selectedTags.has("ALL")) {
    filteredConferences = filteredConferences.filter(conf =>
      conf.tags && conf.tags.some(t => currentFilterSettings.selectedTags.has(t))
    );
  }

  const nowTimestamp = now.getTime();
  filteredConferences.sort((a, b) => {
    const deadlineA = new Date(a.deadline).getTime();
    const deadlineB = new Date(b.deadline).getTime();
    const aIsPastDeadline = deadlineA < nowTimestamp;
    const bIsPastDeadline = deadlineB < nowTimestamp;
    if (aIsPastDeadline && !bIsPastDeadline) return 1;
    if (!aIsPastDeadline && bIsPastDeadline) return -1;
    return deadlineA - deadlineB;
  });

  if (filteredConferences.length === 0) {
    conferenceGrid.innerHTML = `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <h3>Nothing matches those filters</h3>
        <p>Widen the rating, clear the search, or turn on “Show estimated”.</p>
      </div>`;
    return;
  }
  filteredConferences.forEach((conf, i) => createConferenceCard(conf, i));
}

// --- Data Loading ---
async function loadInitialData() {
  try {
    const response = await fetch('data/conferences.json');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status} for upcoming conferences`);
    upcomingConferencesData = await response.json();
    updateHeroStats();
    renderNextUp();
    applyAllFilters();
  } catch (error) {
    console.error("Failed to load upcoming conferences:", error);
    showModal("Couldn't load deadlines", "The conference data didn't load. Check your connection and refresh, or report it on GitHub.");
  }
}

async function loadArchiveDataIfNeededAndRender() {
  if (currentFilterSettings.showPast && archiveConferencesData === null) {
    try {
      const response = await fetch('data/conferences_archive.json');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status} for archive conferences`);
      archiveConferencesData = await response.json();
    } catch (error) {
      console.error("Failed to load archive conferences:", error);
      archiveConferencesData = [];
      showModal("Couldn't load the archive", "Past conference data didn't load. Check your connection and refresh.");
    }
  }
  applyAllFilters();
}

// --- Event Listeners Setup ---
function setupEventListeners() {
  if (currentYearSpan) currentYearSpan.textContent = new Date().getFullYear();

  if (filterToggle && filterControls) {
    filterToggle.addEventListener('click', () => {
      const isExpanded = filterToggle.getAttribute('aria-expanded') === 'true';
      filterToggle.setAttribute('aria-expanded', !isExpanded);
      filterControls.classList.toggle('open');
    });
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'f' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      if (conferenceNameFilterInput) conferenceNameFilterInput.focus();
    }
    if (event.key === 'Escape' && messageModal) messageModal.classList.remove('is-open');
  });

  if (showPastToggle) {
    showPastToggle.addEventListener('change', function () {
      currentFilterSettings.showPast = this.checked;
      this.setAttribute('aria-checked', this.checked);
      loadArchiveDataIfNeededAndRender();
    });
  }
  if (showApproxFutureToggle) {
    showApproxFutureToggle.addEventListener('change', function () {
      currentFilterSettings.showApproxFuture = this.checked;
      this.setAttribute('aria-checked', this.checked);
      applyAllFilters();
    });
  }
  if (minH5IndexInput) {
    minH5IndexInput.addEventListener('input', function () {
      currentFilterSettings.minH5 = this.value === '' ? null : parseInt(this.value, 10);
      if (isNaN(currentFilterSettings.minH5)) currentFilterSettings.minH5 = null;
      applyAllFilters();
    });
  }
  if (minRatingSelect) {
    minRatingSelect.addEventListener('change', function () {
      currentFilterSettings.minRating = this.value;
      applyAllFilters();
    });
  }
  if (conferenceNameFilterInput) {
    conferenceNameFilterInput.addEventListener('input', function () {
      currentFilterSettings.nameFilter = this.value;
      applyAllFilters();
    });
  }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  initTheme();

  if (showPastToggle) {
    currentFilterSettings.showPast = showPastToggle.checked;
    showPastToggle.setAttribute('aria-checked', showPastToggle.checked);
  }
  if (showApproxFutureToggle) {
    currentFilterSettings.showApproxFuture = showApproxFutureToggle.checked;
    showApproxFutureToggle.setAttribute('aria-checked', showApproxFutureToggle.checked);
  }
  if (minH5IndexInput) {
    currentFilterSettings.minH5 = minH5IndexInput.value === '' ? null : parseInt(minH5IndexInput.value, 10);
    if (isNaN(currentFilterSettings.minH5)) currentFilterSettings.minH5 = null;
  }
  if (minRatingSelect) currentFilterSettings.minRating = minRatingSelect.value;
  if (conferenceNameFilterInput) currentFilterSettings.nameFilter = conferenceNameFilterInput.value;

  updateAoeClock();
  setInterval(updateAoeClock, 1000);
  nextUpIntervalId = setInterval(updateNextUp, 1000);

  setupEventListeners();
  loadInitialData();
});
