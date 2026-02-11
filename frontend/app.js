/**
 * ScoutMate - Evidence-First Founder Application
 * Handles sidebar, categories, resources, authentication, and results
 */

// ========================================
// Configuration & State
// ========================================

// API Configuration - auto-detect production vs development
const API_BASE = (() => {
    const hostname = window.location.hostname;
    // Development - localhost uses same origin (backend running locally)
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return '';
    }
    // Production - all deployed domains use Render backend
    return 'https://scoutmate-api-9gik.onrender.com';
})();

let adminPassword = null;
let categories = [];
let resources = [];
let currentResourceType = 'book';
let currentQuery = '';
let conversationHistory = []; // NEW: History state

// Caches for fast loading
let categoriesCache = null;
let booksCache = null;
let articlesCache = null;

// ========================================
// DOM Elements
// ========================================
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebar-overlay');
const menuBtn = document.getElementById('menu-btn');
const closeSidebarBtn = document.getElementById('close-sidebar-btn');

const historyList = document.getElementById('history-list'); // NEW
const clearHistoryBtn = document.getElementById('clear-history-btn'); // NEW


// Custom Dropdown Elements
const customCategorySelect = document.getElementById('custom-category-select');
const selectTrigger = document.getElementById('select-trigger');
const selectOptions = document.getElementById('select-options');
const categorySelectValue = document.getElementById('category-select-value');

const resourceSearch = document.getElementById('resource-search');
const resourceList = document.getElementById('resource-list');
const addResourceBtn = document.getElementById('add-resource-btn');
const booksTab = document.getElementById('books-tab');
const articlesTab = document.getElementById('articles-tab');

const queryInput = document.getElementById('query-input');
const analyzeBtn = document.getElementById('analyze-btn');

const mainPage = document.getElementById('main-page');
const resultsPage = document.getElementById('results-page');
const backBtn = document.getElementById('back-btn');
const scenarioText = document.getElementById('scenario-text');
const evidenceSummary = document.getElementById('evidence-summary');
const timingStats = document.getElementById('timing-stats'); // NEW
const questionsHeader = document.getElementById('questions-header');
const questionsList = document.getElementById('questions-list');

// Model Dropdown Elements
const customModelSelect = document.getElementById('custom-model-select');
const modelSelectTrigger = document.getElementById('model-select-trigger');
const modelSelectOptions = document.getElementById('model-select-options');
const modelSelectValue = document.getElementById('model-select-value');

const loadingOverlay = document.getElementById('loading-overlay');

// Modals
const adminModal = document.getElementById('admin-modal');
const adminPasswordInput = document.getElementById('admin-password-input');
const adminError = document.getElementById('admin-error');
const adminCancelBtn = document.getElementById('admin-cancel-btn');
const adminSubmitBtn = document.getElementById('admin-submit-btn');



const addResourceModal = document.getElementById('add-resource-modal');
const addResourceTitle = document.getElementById('add-resource-title');
const newResourceTitle = document.getElementById('new-resource-title');
const newResourceAuthor = document.getElementById('new-resource-author');
const newResourceUrl = document.getElementById('new-resource-url');
const addResourceCancelBtn = document.getElementById('add-resource-cancel-btn');
const addResourceSubmitBtn = document.getElementById('add-resource-submit-btn');



// Callback for admin auth
let adminAuthCallback = null;

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', init);

function init() {
    // Load all cached data in one call
    loadCachedData();

    // Load history
    loadHistoryInternal(); // NEW

    // Start keep-alive ping every 10 minutes to prevent Render shutdown
    startKeepAlive();

    // Sidebar events
    menuBtn.addEventListener('click', openSidebar);
    closeSidebarBtn.addEventListener('click', closeSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);

    // History events
    clearHistoryBtn.addEventListener('click', clearHistory); // NEW



    // Category events


    // Custom Dropdown Events
    selectTrigger.addEventListener('click', toggleDropdown);
    modelSelectTrigger.addEventListener('click', toggleModelDropdown);
    document.addEventListener('click', closeDropdownOnClickOutside);

    // Resource events
    resourceSearch.addEventListener('input', filterResources);
    addResourceBtn.addEventListener('click', () => requireAdmin(showAddResourceModal));
    booksTab.addEventListener('click', () => switchResourceTab('book'));
    articlesTab.addEventListener('click', () => switchResourceTab('article'));

    // Query events
    queryInput.addEventListener('input', handleQueryInput);
    analyzeBtn.addEventListener('click', handleAnalyze);

    // Results events
    backBtn.addEventListener('click', showMainPage);

    // Admin modal events
    adminCancelBtn.addEventListener('click', hideAdminModal);
    adminSubmitBtn.addEventListener('click', handleAdminSubmit);
    adminPasswordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAdminSubmit();
    });

    // Add category modal events


    // Add resource modal events
    addResourceCancelBtn.addEventListener('click', hideAddResourceModal);
    addResourceSubmitBtn.addEventListener('click', handleAddResource);

    // Set random placeholder
    setRandomPlaceholder();
}

function loadHistoryInternal() {
    const saved = localStorage.getItem('scoutmate_history');
    if (saved) {
        try {
            conversationHistory = JSON.parse(saved);
            renderHistory();
        } catch (e) {
            console.error('Failed to parse history', e);
            conversationHistory = [];
        }
    }
}

function setRandomPlaceholder() {
    const placeholders = [
        "e.g. \"I have a great product but I'm struggling to find my first 100 customers\"",
        "e.g. \"My co-founder wants to raise money, but I want to stay profitable and grow slowly\"",
        "e.g. \"Users are signing up for the free tier but dropping off when asked to pay\""
    ];

    // Pick one randomly
    const randomPlaceholder = placeholders[Math.floor(Math.random() * placeholders.length)];
    queryInput.placeholder = randomPlaceholder;
}


// ========================================
// Sidebar Functions
// ========================================
function openSidebar() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('active');
}

function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
}

// ========================================
// Data Loading & Keep-Alive
// ========================================
async function loadCachedData() {
    try {
        let data = null;

        // Try embedded data first (instant)
        if (typeof RESOURCES_DATA !== 'undefined') {
            console.log('Loading resources from embedded data');
            data = RESOURCES_DATA;
        } else {
            // Fallback to API
            console.log('Loading resources from API');
            const response = await fetch(`${API_BASE}/cached-data`);
            data = await response.json();
        }

        if (data) {
            // Store in caches
            categoriesCache = data.categories || [];
            booksCache = data.books || [];
            articlesCache = data.articles || [];

            // Set current data
            categories = categoriesCache;

            // Ensure "Other" category exists
            if (!categories.find(c => c.id === 'other')) {
                categories.push({
                    id: 'other',
                    name: 'Other / Not Listed',
                    description: 'Anything else not covered above'
                });
            }

            resources = currentResourceType === 'book' ? booksCache : articlesCache;

            // Render

            renderCategorySelect();
            renderResourceList();
        }
    } catch (error) {
        console.error('Failed to load cached data:', error);
        // Fallback to individual loads
        loadCategories();
        loadResources();
    }
}

function startKeepAlive() {
    // Ping server every 10 minutes to prevent Render free tier shutdown
    const TEN_MINUTES = 10 * 60 * 1000;
    setInterval(() => {
        fetch(`${API_BASE}/ping`).catch(() => { });
    }, TEN_MINUTES);
}

// ========================================
// Category Functions
// ========================================
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/categories`);
        const data = await response.json();
        if (data.success) {
            categories = data.categories;

            // Ensure "Other" category exists
            if (!categories.find(c => c.id === 'other')) {
                categories.push({
                    id: 'other',
                    name: 'Other / Not Listed',
                    description: 'Anything else not covered above'
                });
            }

            renderCategorySelect();
        }
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}



function renderCategorySelect() {
    // Populate custom dropdown options
    selectOptions.innerHTML = categories.map(cat => `
        <div class="option" data-value="${cat.id}" onclick="selectCategory('${cat.id}')">
            ${escapeHtml(cat.name)}
        </div>
    `).join('');

    // Reset selection if needed
    categorySelectValue.value = '';
    selectTrigger.querySelector('span').textContent = 'Select Category';
    selectTrigger.classList.remove('active');
}
window.renderCategorySelect = renderCategorySelect;

function toggleDropdown(e) {
    e.stopPropagation();
    selectOptions.classList.toggle('hidden');
    selectTrigger.classList.toggle('active');
}

function selectCategory(id) {
    const category = categories.find(c => c.id === id);
    if (!category) return;

    categorySelectValue.value = id;
    selectTrigger.querySelector('span').textContent = category.name;
    selectOptions.classList.add('hidden');
    selectTrigger.classList.add('active');

    // Visual feedback for selection state in dropdown
    const options = selectOptions.querySelectorAll('.option');
    options.forEach(opt => {
        if (opt.dataset.value === id) {
            opt.classList.add('selected');
        } else {
            opt.classList.remove('selected');
        }
    });

    // Update button state
    if (typeof updateAnalyzeButtonState === 'function') {
        updateAnalyzeButtonState();
    }
}

function closeDropdownOnClickOutside(e) {
    // Category Dropdown
    if (!customCategorySelect.contains(e.target)) {
        selectOptions.classList.add('hidden');
        if (!categorySelectValue.value) {
            selectTrigger.classList.remove('active');
        }
    }

    // Model Dropdown
    if (!customModelSelect.contains(e.target)) {
        modelSelectOptions.classList.add('hidden');
        if (!modelSelectValue.value) {
            modelSelectTrigger.classList.remove('active');
        }
    }
}

// Model Dropdown Functions
function toggleModelDropdown(e) {
    e.stopPropagation();
    modelSelectOptions.classList.toggle('hidden');
    modelSelectTrigger.classList.toggle('active');

    // Close other dropdown
    selectOptions.classList.add('hidden');
}

function selectModel(id) {
    const models = [
        { id: 'claude-haiku-4-5', name: 'Claude Haiku 4.5 (Fast)' },
        { id: 'claude-sonnet-4-5', name: 'Claude Sonnet 4.5 (Smart)' }
    ];

    const model = models.find(m => m.id === id);
    if (!model) return;

    modelSelectValue.value = id;
    modelSelectTrigger.querySelector('span').textContent = model.name;
    modelSelectOptions.classList.add('hidden');
    modelSelectTrigger.classList.add('active');

    // Visual feedback
    const options = modelSelectOptions.querySelectorAll('.option');
    options.forEach(opt => {
        if (opt.dataset.value === id) {
            opt.classList.add('selected');
        } else {
            opt.classList.remove('selected');
        }
    });
}
window.selectModel = selectModel;





// ========================================
// Resource Functions
// ========================================
async function loadResources() {
    try {
        const response = await fetch(`${API_BASE}/resources?resource_type=${currentResourceType}`);
        const data = await response.json();
        if (data.success) {
            resources = data.resources;
            renderResourceList();
        }
    } catch (error) {
        console.error('Failed to load resources:', error);
    }
}

function renderResourceList() {
    const searchTerm = resourceSearch.value.toLowerCase();
    const filtered = resources.filter(r =>
        r.title.toLowerCase().includes(searchTerm) ||
        r.author.toLowerCase().includes(searchTerm)
    );

    resourceList.innerHTML = filtered.map(res => `
        <li data-source="${escapeHtml(res.source_file)}">
            <span class="item-name">${escapeHtml(res.title)}</span>
            <button class="delete-btn" onclick="deleteResource('${escapeHtml(res.source_file)}', '${currentResourceType}')" title="Delete">🗑</button>
        </li>
    `).join('');
}

function filterResources() {
    renderResourceList();
}

function switchResourceTab(type) {
    currentResourceType = type;

    if (type === 'book') {
        booksTab.classList.add('active');
        articlesTab.classList.remove('active');
        resourceSearch.placeholder = 'Search books...';
        addResourceBtn.textContent = '+ Add Book';
        // Use cache if available
        resources = booksCache || [];
    } else {
        booksTab.classList.remove('active');
        articlesTab.classList.add('active');
        resourceSearch.placeholder = 'Search articles...';
        addResourceBtn.textContent = '+ Add Article';
        // Use cache if available
        resources = articlesCache || [];
    }

    // Only call API if cache is empty
    if (resources.length === 0) {
        loadResources();
    } else {
        renderResourceList();
    }
}

function showAddResourceModal() {
    newResourceTitle.value = '';
    newResourceAuthor.value = '';
    newResourceUrl.value = '';

    if (currentResourceType === 'book') {
        addResourceTitle.textContent = '📚 Add New Book';
        newResourceUrl.classList.add('hidden');
    } else {
        addResourceTitle.textContent = '📄 Add New Article';
        newResourceUrl.classList.remove('hidden');
    }

    addResourceModal.classList.remove('hidden');
    newResourceTitle.focus();
}

function hideAddResourceModal() {
    addResourceModal.classList.add('hidden');
}

async function handleAddResource() {
    // Note: The backend doesn't have an endpoint to "add" resources manually
    // Resources are added by placing files in the resources folder and refreshing
    // This modal is informational
    alert('To add resources, place files in the resources/books or resources/articles folder and click "Refresh Database".');
    hideAddResourceModal();
}

async function deleteResource(sourceFile, resourceType) {
    requireAdmin(async () => {
        if (!confirm('Are you sure you want to delete this resource?')) return;

        try {
            const response = await fetch(`${API_BASE}/resources/${encodeURIComponent(sourceFile)}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    resource_type: resourceType,
                    admin_password: adminPassword
                })
            });

            if (response.ok) {
                loadResources();
            } else {
                const error = await response.json();
                alert(error.detail || 'Failed to delete resource');
            }
        } catch (error) {
            alert('Failed to delete resource: ' + error.message);
        }
    });
}

// ========================================
// Admin Authentication
// ========================================
function showAdminModal(callback) {
    adminAuthCallback = callback;
    adminPasswordInput.value = '';
    adminError.classList.add('hidden');
    adminModal.classList.remove('hidden');
    adminPasswordInput.focus();
}

function hideAdminModal() {
    adminModal.classList.add('hidden');
    adminAuthCallback = null;
}

async function handleAdminSubmit() {
    const password = adminPasswordInput.value;

    if (!password) {
        adminError.textContent = 'Please enter a password';
        adminError.classList.remove('hidden');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/verify-admin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ admin_password: password })
        });

        const data = await response.json();

        if (data.success) {
            adminPassword = password;
            hideAdminModal();
            if (adminAuthCallback) {
                adminAuthCallback();
            }
        } else {
            adminError.textContent = 'Invalid password';
            adminError.classList.remove('hidden');
        }
    } catch (error) {
        adminError.textContent = 'Verification failed';
        adminError.classList.remove('hidden');
    }
}

function requireAdmin(callback) {
    if (adminPassword) {
        callback();
    } else {
        showAdminModal(callback);
    }
}

// ========================================
// Refresh Database
// ========================================


// ========================================
// Query & Analyze
// ========================================
function updateAnalyzeButtonState() {
    const hasText = queryInput.value.trim().length > 0;
    const hasCategory = categorySelectValue.value !== '';
    analyzeBtn.disabled = !(hasText && hasCategory);
}

function handleQueryInput() {
    updateAnalyzeButtonState();
}

async function handleAnalyze() {
    const query = queryInput.value.trim();
    if (!query) return;

    currentQuery = query;
    loadingOverlay.classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                category_id: categorySelectValue.value,
                model: modelSelectValue.value
            })
        });

        const data = await response.json();
        loadingOverlay.classList.add('hidden');

        if (data.success) {
            addToHistory(currentQuery, data.full_response, data.timing_data); // NEW: Save to history with timing
            showResults(data);
        } else {
            alert(data.error || 'Analysis failed');
        }
    } catch (error) {
        loadingOverlay.classList.add('hidden');
        alert('Analysis failed: ' + error.message);
    }
}

// ========================================
// Results Display
// ========================================
function showResults(data) {
    scenarioText.textContent = currentQuery;

    // Parse the full response to extract summary and questions
    const parsed = parseResponse(data.full_response || '');

    // Render summary with markdown formatting
    evidenceSummary.innerHTML = formatMarkdown(parsed.summary) || 'Analysis complete. See questions below.';

    // Render Timing Stats if available
    if (data.timing_data) {
        const t = data.timing_data;
        timingStats.innerHTML = `
            <div class="timing-item">
                <span class="timing-label">TOTAL TIME</span>
                <span class="timing-value">${t.total_time.toFixed(2)}s</span>
            </div>
            <div class="timing-divider"></div>
            <div class="timing-item">
                <span class="timing-label">RETRIEVAL (QDRANT)</span>
                <span class="timing-value">${t.search_time.toFixed(2)}s</span>
            </div>
            <div class="timing-item">
                <span class="timing-label">GENERATION (LLM)</span>
                <span class="timing-value">${t.llm_time.toFixed(2)}s</span>
            </div>
        `;
        timingStats.classList.remove('hidden');
    } else {
        timingStats.classList.add('hidden');
    }

    questionsHeader.textContent = `DECOMPOSED QUESTIONS (${parsed.questions.length})`;

    questionsList.innerHTML = parsed.questions.map((q, i) => `
        <div class="question-item">
            <div class="question-header" onclick="toggleQuestion(this.parentElement)">
                <span class="question-number">${String(i + 1).padStart(2, '0')}</span>
                <span class="question-text">${escapeHtml(q.title)}</span>
                <span class="question-toggle">▼</span>
            </div>
            <div class="question-content">
                ${q.answer ? `<div class="answer-block"><span class="answer-label">Answer:</span> ${formatMarkdown(q.answer)}</div>` : ''}
                ${q.evidence.length > 0 ? `
                    <div class="evidence-section">
                        <span class="evidence-label">EVIDENCE:</span>
                        ${q.evidence.map(ev => `
                            <div class="quote-card">
                                <p class="quote-text">"${escapeHtml(ev.quote)}"</p>
                                <p class="quote-source">— ${escapeHtml(ev.source)}</p>
                                ${ev.confidence ? `<p class="quote-confidence ${getConfidenceClass(ev.confidence)}">Confidence: ${formatConfidence(ev.confidence)}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');

    mainPage.classList.add('hidden');
    resultsPage.classList.remove('hidden');
}

function toggleQuestion(element) {
    element.classList.toggle('open');
}

function showMainPage() {
    resultsPage.classList.add('hidden');
    mainPage.classList.remove('hidden');
}

// ========================================
// Response Parsing
// ========================================
function parseResponse(text) {
    const result = {
        summary: '',
        questions: []
    };

    if (!text) return result;

    // Split by ## headers
    const sections = text.split(/(?=^##\s)/gm);

    for (const section of sections) {
        const trimmed = section.trim();
        if (!trimmed) continue;

        // Check for SUMMARY section
        if (trimmed.match(/^##\s*SUMMARY/i)) {
            const summaryContent = trimmed.replace(/^##\s*SUMMARY\s*/i, '').trim();
            result.summary = summaryContent;
            continue;
        }

        // Check for QUESTION sections
        const questionMatch = trimmed.match(/^##\s*QUESTION\s*\d*:?\s*(.+?)(?:\n|$)/i);
        if (questionMatch) {
            const questionTitle = questionMatch[1].trim();
            const questionBody = trimmed.replace(/^##\s*QUESTION\s*\d*:?\s*.+?\n/i, '').trim();

            const question = {
                title: questionTitle || 'Question',
                answer: '',
                evidence: []
            };

            // Parse answer - look for Answer marker and stop at Evidence marker
            // Flexible regex to handle: **Answer**: or **Answer** or Answer:
            // Stop at Evidence section (case insensitive, flexible format)
            const answerMatch = questionBody.match(/(?:\*\*Answer\*\*:?|Answer:)\s*(.+?)(?=\n\s*(?:\*\*|##)?\s*Evidence|Evidence:|$)/is);
            if (answerMatch) {
                question.answer = answerMatch[1].trim();
            }

            // Extract evidence section
            // split by "Evidence" identifier, handling various formats
            const evidenceParts = questionBody.split(/\n\s*(?:\*\*|##)?\s*Evidence:?/i);
            const evidenceSection = evidenceParts.length > 1 ? evidenceParts.slice(1).join('\n') : '';

            // Parse evidence using line-by-line approach
            question.evidence = parseEvidenceSection(evidenceSection);

            result.questions.push(question);
        }
    }

    // Fallback if no structured content found
    if (!result.summary && result.questions.length === 0) {
        result.summary = text;
    }

    return result;
}

// Parse evidence section line by line for more robust extraction
function parseEvidenceSection(evidenceText) {
    const evidence = [];
    if (!evidenceText) return evidence;

    // Split into lines
    const lines = evidenceText.split('\n');

    let currentQuote = '';
    let currentSource = '';
    let currentConfidence = null;
    let inQuote = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Check if this line starts a new quote (dash quote OR just quote)
        const quoteMatch = line.match(/^(-\s*)?"/);
        if (quoteMatch) {
            // Save previous quote if exists
            if (currentQuote && currentSource) {
                evidence.push({
                    quote: currentQuote,
                    source: formatSourceText(currentSource),
                    confidence: currentConfidence || 'Medium'
                });
            }

            // Reset for new quote
            currentQuote = '';
            currentSource = '';
            currentConfidence = null;
            inQuote = true;

            // Extract quote from this line - might continue on next lines
            const quoteStart = line.indexOf('"') + 1;
            const quoteEnd = line.lastIndexOf('"');

            if (quoteEnd > quoteStart) {
                // Quote ends on same line
                currentQuote = line.substring(quoteStart, quoteEnd);
                inQuote = false;

                // Check for source on same line after quote
                const afterQuote = line.substring(quoteEnd + 1);
                const sourceMatch = afterQuote.match(/[—–-]\s*(Book|Article):?\s*(.+)/i);
                if (sourceMatch) {
                    currentSource = sourceMatch[1] + ': ' + sourceMatch[2].trim();
                }
            } else {
                // Quote continues on next lines
                currentQuote = line.substring(quoteStart);
            }
        }
        // Check for source line - flexible to handle encoding issues
        // Matches any line containing Book: or Article: with content after
        else if (line.match(/(Book|Article):/i) && !line.startsWith('-')) {
            const sourceMatch = line.match(/(Book|Article):?\s*(.+)/i);
            if (sourceMatch) {
                currentSource = sourceMatch[1] + ': ' + sourceMatch[2].trim();
            }
        }
        // Check for confidence line - anywhere in line
        else if (line.match(/Confidence:\s*(High|Medium|Low)/i)) {
            const confMatch = line.match(/Confidence:\s*(High|Medium|Low)/i);
            if (confMatch) {
                currentConfidence = confMatch[1].trim();
            }
        }
        // Continue reading quote if we're in the middle of one
        else if (inQuote && line) {
            if (line.includes('"')) {
                // Quote ends on this line
                const quoteEnd = line.indexOf('"');
                currentQuote += ' ' + line.substring(0, quoteEnd);
                inQuote = false;

                // Check for source after quote
                const afterQuote = line.substring(quoteEnd + 1);
                const sourceMatch = afterQuote.match(/[—–-]\s*(Book|Article):?\s*(.+)/i);
                if (sourceMatch) {
                    currentSource = sourceMatch[1] + ': ' + sourceMatch[2].trim();
                }
            } else {
                currentQuote += ' ' + line;
            }
        }
    }

    // Don't forget the last quote
    if (currentQuote && currentSource) {
        evidence.push({
            quote: currentQuote,
            source: formatSourceText(currentSource),
            confidence: currentConfidence || 'Medium'
        });
    }

    // Fallback: if no quotes found, try simple regex extraction
    if (evidence.length === 0) {
        const simplePattern = /"([^"]{20,})"/g;
        let match;
        while ((match = simplePattern.exec(evidenceText)) !== null) {
            // Look for source after this quote - flexible pattern
            const afterQuote = evidenceText.substring(match.index + match[0].length, match.index + match[0].length + 300);
            const sourceMatch = afterQuote.match(/(Book|Article):?\s*([^\n]+)/i);
            const confMatch = afterQuote.match(/Confidence:\s*(High|Medium|Low)/i);

            evidence.push({
                quote: match[1].trim(),
                source: sourceMatch ? formatSourceText(sourceMatch[1] + ': ' + sourceMatch[2].trim()) : 'Source',
                confidence: confMatch ? confMatch[1].trim() : null
            });
        }
    }


    return evidence;
}

// Format source text - clean up underscores and normalize
function formatSourceText(source) {
    if (!source) return 'Unknown Source';

    // Replace underscores with spaces in book/article titles
    return source
        .replace(/_/g, ' ')           // Replace underscores with spaces
        .replace(/\s+/g, ' ')         // Normalize multiple spaces
        .trim();
}

// Format basic markdown to HTML
function formatMarkdown(text) {
    if (!text) return '';

    return text
        // Ensure newlines before bullets
        .replace(/([^\n])\n(- |\d+\.|[a-z]\))/g, '$1\n\n$2')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
}

// ========================================
// Utilities
// ========================================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format confidence value - only accepts High/Medium/Low text values
function formatConfidence(value) {
    if (!value) return '';

    // Only return valid confidence levels
    const normalized = String(value).trim();
    if (/^(High|Medium|Low)$/i.test(normalized)) {
        // Capitalize first letter
        return normalized.charAt(0).toUpperCase() + normalized.slice(1).toLowerCase();
    }

    return '';
}

// Get CSS class for confidence level
function getConfidenceClass(value) {
    if (!value) return '';

    const normalized = String(value).trim().toLowerCase();
    if (normalized === 'high') return 'confidence-high';
    if (normalized === 'medium') return 'confidence-medium';
    if (normalized === 'low') return 'confidence-low';

    return '';
}

// Make functions available globally for onclick handlers
window.deleteCategory = deleteCategory;
window.deleteResource = deleteResource;
window.toggleQuestion = toggleQuestion;
window.selectCategory = selectCategory;
window.toggleDropdown = toggleDropdown;

// ========================================
// History Functions (NEW)
// ========================================
function loadHistory() {
    const saved = localStorage.getItem('scoutmate_history');
    if (saved) {
        try {
            conversationHistory = JSON.parse(saved);
        } catch (e) {
            console.error('Failed to parse history', e);
            conversationHistory = [];
        }
    }
    renderHistoryList();
}

function saveHistory() {
    localStorage.setItem('scoutmate_history', JSON.stringify(conversationHistory));
    renderHistory();
}

function addToHistory(query, response, timingData = null) {
    if (!query) return;

    const item = {
        id: Date.now().toString(),
        query,
        response,
        timing_data: timingData, // Save timing data
        timestamp: new Date().toISOString()
    };

    // Add to beginning
    conversationHistory.unshift(item);

    // Limit to 5 items (as per user request)
    if (conversationHistory.length > 5) {
        conversationHistory.pop();
    }

    // Save
    saveHistory();

    // Render
    renderHistory();
}

function renderHistory() {
    historyList.innerHTML = '';

    if (conversationHistory.length === 0) {
        historyList.innerHTML = '<li class="empty-state" style="border:none; background:none; color:var(--text-muted); padding:10px; text-align:center; font-size:12px;">No history yet</li>';
        return;
    }

    conversationHistory.forEach(item => {
        const li = document.createElement('li');
        li.title = item.query;
        li.dataset.id = item.id; // Add dataset ID for selection

        // click handler for the list item
        li.addEventListener('click', () => loadHistoryItem(item.id));

        const span = document.createElement('span');
        span.className = 'item-name';
        span.style.whiteSpace = 'nowrap';
        span.style.overflow = 'hidden';
        span.style.textOverflow = 'ellipsis';
        span.textContent = item.query;
        li.appendChild(span);

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.title = 'Delete';
        deleteBtn.textContent = '🗑';

        // click handler for the delete button
        deleteBtn.addEventListener('click', (e) => deleteHistoryItem(item.id, e));

        li.appendChild(deleteBtn);
        historyList.appendChild(li);
    });
}

function loadHistoryItem(id) {
    // Loose comparison just in case id types mismatch (string vs number)
    const item = conversationHistory.find(h => h.id == id);
    if (!item) return;

    currentQuery = item.query;
    queryInput.value = item.query;

    // Show results with saved data
    showResults({
        success: true,
        full_response: item.response,
        timing_data: item.timing_data // Pass saved timing data
    });

    if (window.innerWidth <= 768) {
        closeSidebar();
    }
}

function deleteHistoryItem(id, event) {
    event.stopPropagation();
    if (!confirm('Remove this conversation from history?')) return;

    // Loose comparison filter
    conversationHistory = conversationHistory.filter(h => h.id != id);
    saveHistory();
}

function clearHistory() {
    if (!conversationHistory.length) return;
    if (!confirm('Clear all conversation history?')) return;
    conversationHistory = [];
    saveHistory();
}
