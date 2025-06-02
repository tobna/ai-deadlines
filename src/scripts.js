// --- DOM Elements ---
const conferenceGrid = document.getElementById('conferenceGrid');
const tagFilterContainer = document.getElementById('tagFilterContainer');
const showPastToggle = document.getElementById('showPastToggle');
const showApproxFutureToggle = document.getElementById('showApproxFutureToggle');
const minH5IndexInput = document.getElementById('minH5Index');
const minRatingSelect = document.getElementById('minRating');
const conferenceNameFilterInput = document.getElementById('conferenceNameFilter');
const currentYearSpan = document.getElementById('currentYear');

const messageModal = document.getElementById('messageModal');
const modalTitle = document.getElementById('modalTitle');
const modalMessage = document.getElementById('modalMessage');
const closeModalButton = document.getElementById('closeModalButton');

// --- Application State ---
let upcomingConferencesData = [];
let archiveConferencesData = null; 

let currentActiveTagButton = null; 

let currentFilterSettings = {
    selectedTag: null,
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
        messageModal.classList.remove('hidden');
        messageModal.classList.add('opacity-100');
    } else {
        console.error("Modal elements not found. Message:", title, msg);
        alert(`${title}\n${msg}`);
    }
}

if (closeModalButton) {
    closeModalButton.addEventListener('click', () => {
        if (messageModal) {
            messageModal.classList.add('hidden');
            messageModal.classList.remove('opacity-100');
        }
    });
}

// --- Countdown Logic ---
function updateSpecificCountdown(targetDateStr, countdownElementId, label, isApproximate = false) {
    const countdownElement = document.getElementById(countdownElementId);
    if (!countdownElement) return;

    // Assumes targetDateStr from JSON is a UTC string (e.g., "2025-07-15T23:59:59Z")
    const eventDate = new Date(targetDateStr).getTime();
    const now = new Date().getTime(); // User's local time
    const timeLeft = eventDate - now;

    if (timeLeft <= 0) {
        const passedLabel = isApproximate ? `${label} (Approx.) Passed` : `${label} Passed`;
        countdownElement.innerHTML = `
            <div class="ended-banner w-full text-center py-2 px-3 rounded-md text-md font-semibold">
                ${passedLabel}
            </div>`;
        return;
    }

    if (isApproximate) {
        const daysLeft = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
        let approxDaysText;
        if (daysLeft < 0) {
            approxDaysText = "Passed";
        } else if (daysLeft < 10) {
            approxDaysText = "<10 days";
        } else {
            approxDaysText = `~${String(Math.round(daysLeft / 10) * 10)} days`;
        }
        countdownElement.innerHTML = `
            <div class="countdown-label">${label}:</div>
            <div class="text-lg sm:text-xl lg:text-2xl font-bold text-pink-400 text-center p-1 sm:p-2 bg-gray-700 rounded-md shadow">
                ${approxDaysText}
            </div>
        `;
    } else {
        const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
        const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);

        countdownElement.innerHTML = `
            <div class="countdown-label">${label} In:</div>
            <div class="flex justify-around space-x-1 sm:space-x-2">
                <div class="countdown-item text-center p-1 sm:p-2 bg-gray-700 rounded-md shadow">
                    <div class="text-xl sm:text-2xl lg:text-3xl font-bold text-pink-400">${String(days).padStart(2, '0')}</div>
                    <div class="text-xs text-gray-300">Days</div>
                </div>
                <div class="countdown-item text-center p-1 sm:p-2 bg-gray-700 rounded-md shadow">
                    <div class="text-xl sm:text-2xl lg:text-3xl font-bold text-pink-400">${String(hours).padStart(2, '0')}</div>
                    <div class="text-xs text-gray-300">Hours</div>
                </div>
                <div class="countdown-item text-center p-1 sm:p-2 bg-gray-700 rounded-md shadow">
                    <div class="text-xl sm:text-2xl lg:text-3xl font-bold text-pink-400">${String(minutes).padStart(2, '0')}</div>
                    <div class="text-xs text-gray-300">Minutes</div>
                </div>
                <div class="countdown-item text-center p-1 sm:p-2 bg-gray-700 rounded-md shadow">
                    <div class="text-xl sm:text-2xl lg:text-3xl font-bold text-pink-400">${String(seconds).padStart(2, '0')}</div>
                    <div class="text-xs text-gray-300">Seconds</div>
                </div>
            </div>
        `;
    }
}

// --- Format Date Helper ---
function formatDate(dateString, formattingOptions = {}) {
    if (!dateString) return 'N/A';
    
    // Create a Date object. Assumes dateString is ISO 8601 UTC (ends with Z) or includes offset.
    // For date-only strings (conference start/end), append 'T00:00:00Z' to treat as UTC start of day.
    const date = new Date(
        (dateString.includes('T') || dateString.endsWith('Z')) 
        ? dateString 
        : dateString + 'T00:00:00Z' 
    );

    let effectiveOptions = {};

    // Determine the timezone for display.
    // If displayTimezoneIana is provided, use it. Otherwise, default to UTC for display.
    effectiveOptions.timeZone = formattingOptions.displayTimezoneIana || 'UTC';

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
    return date.toLocaleDateString(undefined, effectiveOptions);
}


// --- Create Conference Cards ---
function createConferenceCard(conference) {
    const card = document.createElement('div');
    card.id = `card-${conference.id}`;
    card.className = 'card-gradient p-6 rounded-xl shadow-2xl flex flex-col justify-between transform hover:scale-105 transition-transform duration-300';
    
    const isApprox = conference.isApproximateDeadline || false;
    const approxDateFormatting = { monthYearOnly: true, displayTimezoneIana: conference.timezone || 'UTC' };
    const preciseDeadlineFormat = { includeTime: true, includeTimezoneName: true, displayTimezoneIana: conference.timezone || 'UTC' }; 
    const conferenceDayFormat = { displayTimezoneIana: conference.timezone || 'UTC' }; // Display conference days in its timezone or UTC

    let metaInfoHTML = '<div class="conference-meta-info">';
    let hasMeta = false;
    if (conference.rating) {
        metaInfoHTML += `<span><span class="label">Rating:</span> ${conference.rating}</span>`;
        hasMeta = true;
    }
    if (conference.h5Index !== undefined) {
        metaInfoHTML += `<span><span class="label">h5-index:</span> ${conference.h5Index}</span>`;
        hasMeta = true;
    }
    metaInfoHTML += '</div>';
    if (!hasMeta) metaInfoHTML = '';

    let placeInfo = '';
    if (conference.location) {
        placeInfo = `<p class="text-sm text-gray-400 mt-1 mb-2">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 inline-block mr-1 align-text-bottom">
                            <path fill-rule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.145l.002-.001L10 18.43l-5.192-5.192a6.875 6.875 0 010-9.719l.001-.001c2.7-2.7 7.075-2.7 9.774 0l.001.001a6.875 6.875 0 010 9.719L10 18.43zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd" />
                        </svg>
                        ${conference.location}
                    </p>`;
    }

    let conferenceDateText;
    const confStartFormat = isApprox ? approxDateFormatting : conferenceDayFormat;
    if (isApprox) {
        conferenceDateText = `Dates: ~${formatDate(conference.conferenceStartDate, confStartFormat)}`;
    } else {
        conferenceDateText = `Dates: ${formatDate(conference.conferenceStartDate, confStartFormat)}`;
        if (conference.conferenceEndDate && conference.conferenceEndDate !== conference.conferenceStartDate) {
            const confEndFormat = isApprox ? approxDateFormatting : conferenceDayFormat;
            conferenceDateText += ` - ${isApprox ? '~' : ''}${formatDate(conference.conferenceEndDate, confEndFormat)}`;
        }
    }

    const conferenceDatesHTML = `
        <p class="text-sm text-gray-400 mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 inline-block mr-1 align-text-bottom">
                <path fill-rule="evenodd" d="M5.75 3A2.25 2.25 0 003.5 5.25v9.5A2.25 2.25 0 005.75 17h8.5A2.25 2.25 0 0016.5 14.75v-9.5A2.25 2.25 0 0014.25 3h-8.5zM5 5.25c0-.414.336-.75.75-.75h8.5c.414 0 .75.336.75.75v9.5c0 .414-.336.75-.75.75h-8.5a.75.75 0 01-.75-.75v-9.5z" clip-rule="evenodd" />
                <path fill-rule="evenodd" d="M10 7a.75.75 0 01.75.75v2.5h2.5a.75.75 0 010 1.5h-2.5v2.5a.75.75 0 01-1.5 0v-2.5h-2.5a.75.75 0 010-1.5h2.5v-2.5A.75.75 0 0110 7zM5 1a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5H5.75A.75.75 0 015 1zm8.5 0a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5a.75.75 0 01-.75-.75z" clip-rule="evenodd" />
            </svg>
            ${conferenceDateText}
        </p>`;

    let noteInfo = '';
    if (conference.note) {
        noteInfo = `<p class="text-gray-300 text-sm mt-2 mb-1 leading-relaxed">${conference.note}</p>`;
    }

    let tagsHTML = '';
    if (conference.tags && conference.tags.length > 0) {
        tagsHTML = '<div class="mt-3 mb-2 flex flex-wrap">';
        conference.tags.forEach(tag => {
            tagsHTML += `<span class="conference-tag">${tag}</span>`;
        });
        tagsHTML += '</div>';
    }

    const mainDeadlineCountdownHTML = `<div id="countdown-deadline-${conference.id}" class="deadline-section"></div>`;
    const deadlineLabelText = isApprox ? "Approx. Full Paper Submission" : "Full Paper Submission";
    const deadlineDateTextSuffix = isApprox ? " (Approx.)" : "";
    
    const mainDeadlineFormatOptions = isApprox 
        ? approxDateFormatting 
        : preciseDeadlineFormat; 
    const mainDeadlineText = isApprox 
        ? `~${formatDate(conference.deadline, mainDeadlineFormatOptions)}`
        : formatDate(conference.deadline, mainDeadlineFormatOptions);
    const mainDeadlineTextHTML = `<p class="deadline-date-text">Deadline: ${mainDeadlineText}${deadlineDateTextSuffix}</p>`;
    
    let abstractDeadlineTextHTML = '';
    if (conference.abstractDeadline) {
        const abstractFormatOptions = isApprox ? approxDateFormatting : preciseDeadlineFormat;
        const abstractDateText = isApprox 
            ? `~${formatDate(conference.abstractDeadline, abstractFormatOptions)}`
            : formatDate(conference.abstractDeadline, abstractFormatOptions);
        const abstractSuffix = isApprox ? " (Approx.)" : "";
        abstractDeadlineTextHTML = `<div class="mt-2 pt-2 border-t border-gray-700"> 
                                        <p class="deadline-date-text text-sm">Abstract Deadline: ${abstractDateText}${abstractSuffix}</p>
                                   </div>`;
    }
    
    let websiteLinkHTML;
    if (isApprox) {
        websiteLinkHTML = `
        <a href="#" 
           class="block w-full mt-4 bg-gray-500 text-gray-300 font-semibold text-center py-3 px-4 rounded-lg cursor-not-allowed opacity-70 shadow-md">
            Visit Conference Site
        </a>`;
    } else if (!conference.website) { 
        websiteLinkHTML = `
        <a href="#" 
           class="block w-full mt-4 bg-gray-400 text-gray-200 font-semibold text-center py-3 px-4 rounded-lg cursor-not-allowed opacity-60 shadow-md">
            Site Not Available
        </a>`;
    } else { 
        websiteLinkHTML = `
        <a href="${conference.website}" target="_blank" rel="noopener noreferrer"
           class="block w-full mt-4 bg-pink-500 hover:bg-pink-600 text-white font-semibold text-center py-3 px-4 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg">
            Visit Conference Site
        </a>`;
    }

    card.innerHTML = `
        <div>
            <h2 class="text-2xl font-semibold text-white mb-1">${conference.title} (${conference.shortname || ''})</h2>
            ${metaInfoHTML}
            ${placeInfo}
            ${conferenceDatesHTML}
            ${noteInfo}
            ${tagsHTML}
        </div>
        <div>
            ${mainDeadlineCountdownHTML}
            ${mainDeadlineTextHTML}
            ${abstractDeadlineTextHTML} 
            ${websiteLinkHTML}
        </div>
    `;
    conferenceGrid.appendChild(card);

    updateSpecificCountdown(conference.deadline, `countdown-deadline-${conference.id}`, deadlineLabelText, isApprox);
    if (!isApprox) {
        const intervalId = setInterval(() => updateSpecificCountdown(conference.deadline, `countdown-deadline-${conference.id}`, deadlineLabelText, false), 1000);
        card.dataset.intervalId = intervalId; 
    }
}

// --- Populate Tag Filter ---
function populateTagFilter(sourceConferences) {
    if (!tagFilterContainer) return;
    const allTags = new Set();
    sourceConferences.forEach(conf => {
        if (conf.tags) {
            conf.tags.forEach(tag => allTags.add(tag));
        }
    });

    tagFilterContainer.innerHTML = ''; 
    let initialActiveButton = null;

    const allButton = document.createElement('button');
    allButton.textContent = 'All Conferences';
    allButton.className = 'tag-button'; 
    allButton.addEventListener('click', () => {
        currentFilterSettings.selectedTag = null;
        setActiveTagButton(allButton);
        applyAllFilters();
    });
    tagFilterContainer.appendChild(allButton);
    if (!currentFilterSettings.selectedTag) {
        initialActiveButton = allButton;
    }

    Array.from(allTags).sort().forEach(tag => {
        const button = document.createElement('button');
        button.textContent = tag;
        button.className = 'tag-button';
        if (tag === currentFilterSettings.selectedTag) {
            initialActiveButton = button;
        }
        button.addEventListener('click', () => {
            currentFilterSettings.selectedTag = tag;
            setActiveTagButton(button);
            applyAllFilters();
        });
        tagFilterContainer.appendChild(button);
    });
    
    setActiveTagButton(initialActiveButton || allButton); 
}

function setActiveTagButton(buttonToActivate) {
    if (currentActiveTagButton) { 
        currentActiveTagButton.classList.remove('active');
    }
    if (buttonToActivate){
        buttonToActivate.classList.add('active');
        currentActiveTagButton = buttonToActivate;
    } else {
        const allConfButton = Array.from(tagFilterContainer.children).find(btn => btn.textContent === 'All Conferences');
        if (allConfButton) {
            allConfButton.classList.add('active');
            currentActiveTagButton = allConfButton;
        } else {
            currentActiveTagButton = null; 
        }
    }
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
        currentFilterSettings.selectedTag,
        currentFilterSettings.showPast, 
        currentFilterSettings.showApproxFuture,
        currentFilterSettings.minH5,
        currentFilterSettings.minRating,
        currentFilterSettings.nameFilter
    );
}

function renderConferences(
    sourceConferenceData, 
    selectedTag, 
    shouldShowPast, 
    shouldShowApproxFuture,
    minH5,
    minRatingVal,
    nameFilterVal
) {
    if (!conferenceGrid) return;
    
    Array.from(conferenceGrid.children).forEach(card => {
        const intervalId = card.dataset.intervalId;
        if (intervalId) {
            clearInterval(Number(intervalId));
        }
    });
    conferenceGrid.innerHTML = ''; 

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

    if (selectedTag) {
        filteredConferences = filteredConferences.filter(conf => conf.tags && conf.tags.includes(selectedTag));
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
        conferenceGrid.innerHTML = `<p class="text-gray-400 col-span-full text-center">No conferences match the current filters.</p>`;
        return;
    }
    filteredConferences.forEach(createConferenceCard);
}

// --- Data Loading ---
async function loadInitialData() {
    try {
        const response = await fetch('data/conferences.json');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status} for upcoming conferences`);
        upcomingConferencesData = await response.json();
        applyAllFilters(); 
    } catch (error) {
        console.error("Failed to load upcoming conferences:", error);
        showModal("Error", "Could not load upcoming conference data. Please check data/conferences.json.");
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
            showModal("Error", "Could not load past conference data. Please check data/conferences_archive.json.");
        }
    }
    applyAllFilters(); 
}


// --- Event Listeners Setup ---
function setupEventListeners() {
    if (currentYearSpan) {
        currentYearSpan.textContent = new Date().getFullYear();
    }

    document.addEventListener('keydown', function(event) {
        // Check if the 'f' key is pressed along with Ctrl (for Windows/Linux) or Command (for macOS)
        if (event.key === 'f' && (event.ctrlKey || event.metaKey)) {
            // Prevent the browser's default "Find" action
            event.preventDefault();

            // Focus the conference name filter input field
            if (conferenceNameFilterInput) {
                conferenceNameFilterInput.focus();
            }
        }
    });

    if (showPastToggle) {
        showPastToggle.addEventListener('change', function() {
            currentFilterSettings.showPast = this.checked;
            loadArchiveDataIfNeededAndRender(); 
        });
    }
    if (showApproxFutureToggle) {
        showApproxFutureToggle.addEventListener('change', function() {
            currentFilterSettings.showApproxFuture = this.checked;
            applyAllFilters();
        });
    }
    if (minH5IndexInput) {
        minH5IndexInput.addEventListener('input', function() {
            currentFilterSettings.minH5 = this.value === '' ? null : parseInt(this.value, 10);
            if (isNaN(currentFilterSettings.minH5)) currentFilterSettings.minH5 = null;
            applyAllFilters();
        });
    }
    if (minRatingSelect) {
        minRatingSelect.addEventListener('change', function() {
            currentFilterSettings.minRating = this.value;
            applyAllFilters();
        });
    }
    if (conferenceNameFilterInput) {
        conferenceNameFilterInput.addEventListener('input', function() {
            currentFilterSettings.nameFilter = this.value;
            applyAllFilters();
        });
    }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    if (showPastToggle) currentFilterSettings.showPast = showPastToggle.checked;
    if (showApproxFutureToggle) currentFilterSettings.showApproxFuture = showApproxFutureToggle.checked;
    if (minH5IndexInput) {
         currentFilterSettings.minH5 = minH5IndexInput.value === '' ? null : parseInt(minH5IndexInput.value, 10);
         if (isNaN(currentFilterSettings.minH5)) currentFilterSettings.minH5 = null;
    }
    if (minRatingSelect) currentFilterSettings.minRating = minRatingSelect.value;
    if (conferenceNameFilterInput) currentFilterSettings.nameFilter = conferenceNameFilterInput.value;
    
    setupEventListeners();
    loadInitialData(); 
});
