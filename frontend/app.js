/**
 * ScoutMate - Evidence-First Founder Application
 * Handles sidebar, categories, resources, authentication, and results
 */

// ========================================
// Configuration & State
// ========================================

// API Configuration - auto-detect production vs development
const API_BASE = (() => {
    if (window.location.hostname === 'scoutmate.in' || window.location.hostname === 'www.scoutmate.in') {
        // Update this after Render deploys
        return 'https://scoutmate-api.onrender.com';
    }
    return '';
})();

let adminPassword = null;
let categories = [];
let resources = [];
let currentResourceType = 'book';
let currentQuery = '';

// ========================================
// DOM Elements
// ========================================
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebar-overlay');
const menuBtn = document.getElementById('menu-btn');
const closeSidebarBtn = document.getElementById('close-sidebar-btn');
const refreshBtn = document.getElementById('refresh-btn');

const categorySearch = document.getElementById('category-search');
const categoryList = document.getElementById('category-list');
const addCategoryBtn = document.getElementById('add-category-btn');
const categorySelect = document.getElementById('category-select');

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
const questionsHeader = document.getElementById('questions-header');
const questionsList = document.getElementById('questions-list');

const loadingOverlay = document.getElementById('loading-overlay');

// Modals
const adminModal = document.getElementById('admin-modal');
const adminPasswordInput = document.getElementById('admin-password-input');
const adminError = document.getElementById('admin-error');
const adminCancelBtn = document.getElementById('admin-cancel-btn');
const adminSubmitBtn = document.getElementById('admin-submit-btn');

const addCategoryModal = document.getElementById('add-category-modal');
const newCategoryName = document.getElementById('new-category-name');
const newCategoryDesc = document.getElementById('new-category-desc');
const addCategoryCancelBtn = document.getElementById('add-category-cancel-btn');
const addCategorySubmitBtn = document.getElementById('add-category-submit-btn');

const addResourceModal = document.getElementById('add-resource-modal');
const addResourceTitle = document.getElementById('add-resource-title');
const newResourceTitle = document.getElementById('new-resource-title');
const newResourceAuthor = document.getElementById('new-resource-author');
const newResourceUrl = document.getElementById('new-resource-url');
const addResourceCancelBtn = document.getElementById('add-resource-cancel-btn');
const addResourceSubmitBtn = document.getElementById('add-resource-submit-btn');

const refreshModal = document.getElementById('refresh-modal');
const refreshStatus = document.getElementById('refresh-status');
const forceRefreshCheckbox = document.getElementById('force-refresh-checkbox');

// Callback for admin auth
let adminAuthCallback = null;

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', init);

function init() {
    // Load initial data
    loadCategories();
    loadResources();

    // Sidebar events
    menuBtn.addEventListener('click', openSidebar);
    closeSidebarBtn.addEventListener('click', closeSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);

    // Refresh button
    refreshBtn.addEventListener('click', handleRefresh);

    // Category events
    categorySearch.addEventListener('input', filterCategories);
    addCategoryBtn.addEventListener('click', () => requireAdmin(showAddCategoryModal));

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
    addCategoryCancelBtn.addEventListener('click', hideAddCategoryModal);
    addCategorySubmitBtn.addEventListener('click', handleAddCategory);

    // Add resource modal events
    addResourceCancelBtn.addEventListener('click', hideAddResourceModal);
    addResourceSubmitBtn.addEventListener('click', handleAddResource);
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
// Category Functions
// ========================================
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/categories`);
        const data = await response.json();
        if (data.success) {
            categories = data.categories;
            renderCategoryList();
            renderCategorySelect();
        }
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

function renderCategoryList() {
    const searchTerm = categorySearch.value.toLowerCase();
    const filtered = categories.filter(c =>
        c.name.toLowerCase().includes(searchTerm)
    );

    categoryList.innerHTML = filtered.map(cat => `
        <li data-id="${cat.id}">
            <span class="item-name">${escapeHtml(cat.name)}</span>
            <button class="delete-btn" onclick="deleteCategory('${cat.id}')" title="Delete">🗑</button>
        </li>
    `).join('');
}

function renderCategorySelect() {
    categorySelect.innerHTML = '<option value="">Select a category</option>' +
        categories.map(cat => `<option value="${cat.id}">${escapeHtml(cat.name)}</option>`).join('');
}

function filterCategories() {
    renderCategoryList();
}

function showAddCategoryModal() {
    newCategoryName.value = '';
    newCategoryDesc.value = '';
    addCategoryModal.classList.remove('hidden');
    newCategoryName.focus();
}

function hideAddCategoryModal() {
    addCategoryModal.classList.add('hidden');
}

async function handleAddCategory() {
    const name = newCategoryName.value.trim();
    const description = newCategoryDesc.value.trim();

    if (!name) {
        alert('Please enter a category name');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/categories`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                description: description || null,
                admin_password: adminPassword
            })
        });

        if (response.ok) {
            hideAddCategoryModal();
            loadCategories();
        } else {
            const error = await response.json();
            alert(error.detail || 'Failed to add category');
        }
    } catch (error) {
        alert('Failed to add category: ' + error.message);
    }
}

async function deleteCategory(categoryId) {
    requireAdmin(async () => {
        if (!confirm('Are you sure you want to delete this category?')) return;

        try {
            const response = await fetch(`${API_BASE}/categories/${categoryId}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ admin_password: adminPassword })
            });

            if (response.ok) {
                loadCategories();
            } else {
                const error = await response.json();
                alert(error.detail || 'Failed to delete category');
            }
        } catch (error) {
            alert('Failed to delete category: ' + error.message);
        }
    });
}

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
    } else {
        booksTab.classList.remove('active');
        articlesTab.classList.add('active');
        resourceSearch.placeholder = 'Search articles...';
        addResourceBtn.textContent = '+ Add Article';
    }

    loadResources();
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
async function handleRefresh() {
    closeSidebar();
    refreshStatus.textContent = 'Scanning for new resources...';
    refreshModal.classList.remove('hidden');

    try {
        const force = forceRefreshCheckbox.checked;
        const response = await fetch(`${API_BASE}/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force })
        });

        const data = await response.json();

        if (data.success) {
            refreshStatus.textContent = `Done! Processed ${data.books_processed} books and ${data.articles_processed} articles.`;
            setTimeout(() => {
                refreshModal.classList.add('hidden');
                loadResources();
            }, 2000);
        } else {
            refreshStatus.textContent = `Error: ${data.message || 'Refresh failed'}`;
            setTimeout(() => {
                refreshModal.classList.add('hidden');
            }, 3000);
        }
    } catch (error) {
        refreshStatus.textContent = `Error: ${error.message}`;
        setTimeout(() => {
            refreshModal.classList.add('hidden');
        }, 3000);
    }
}

// ========================================
// Query & Analyze
// ========================================
function handleQueryInput() {
    const hasText = queryInput.value.trim().length > 0;
    analyzeBtn.disabled = !hasText;
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
            body: JSON.stringify({ query })
        });

        const data = await response.json();
        loadingOverlay.classList.add('hidden');

        if (data.success) {
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

    questionsHeader.textContent = `DECOMPOSED QUESTIONS (${parsed.questions.length})`;

    questionsList.innerHTML = parsed.questions.map((q, i) => `
        <div class="question-item">
            <div class="question-header" onclick="toggleQuestion(this.parentElement)">
                <span class="question-number">${String(i + 1).padStart(2, '0')}</span>
                <span class="question-text">${escapeHtml(q.title)}</span>
                <span class="question-toggle">▼</span>
            </div>
            <div class="question-content">
                ${q.answer ? `<div class="answer-block"><strong>Answer:</strong> ${formatMarkdown(q.answer)}</div>` : ''}
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

            // Parse answer
            const answerMatch = questionBody.match(/\*\*Answer\*\*:?\s*(.+?)(?=\n\s*Evidence:|$)/is);
            if (answerMatch) {
                question.answer = answerMatch[1].trim();
            }

            // Extract evidence section
            const evidenceParts = questionBody.split(/Evidence:/i);
            const evidenceSection = evidenceParts[1] || '';

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

        // Check if this line starts a new quote (starts with - ")
        if (line.match(/^-\s*"/)) {
            // Save previous quote if exists
            if (currentQuote && currentSource) {
                evidence.push({
                    quote: currentQuote,
                    source: formatSourceText(currentSource),
                    confidence: currentConfidence
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
            confidence: currentConfidence
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
