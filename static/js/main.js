/**
 * PlagiarismAI — Main Frontend Script
 * Handles responsive sidebar, alert dismissal, delete confirmations, and results filtering
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Sidebar Navigation Toggle
    const mobileToggle = document.getElementById('mobileSidebarToggle');
    const sidebar = document.getElementById('appSidebar');

    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && !mobileToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // 2. Alert Dismissal
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 150);
            }
        });
    });

    // 3. Delete Confirmation Dialog Interceptor
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', (e) => {
            const message = form.getAttribute('data-confirm') || "Are you sure you want to proceed with this action?";
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // 4. Similarity Report Results Interactive Filtering & Search
    const matchCards = document.querySelectorAll('.match-card');
    const filterButtons = document.querySelectorAll('.match-filter-btn');
    const searchInput = document.getElementById('matchSearchInput');
    const refSelect = document.getElementById('matchRefSelect');
    const resetBtn = document.getElementById('resetMatchFiltersBtn');
    const jumpRefButtons = document.querySelectorAll('.jump-ref-btn');
    const visibleCounter = document.getElementById('visibleMatchCount');

    if (matchCards.length > 0) {
        let activeFilter = 'all';

        function applyMatchFilters() {
            const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
            const selectedRef = (refSelect ? refSelect.value : 'all');
            let visibleCount = 0;

            matchCards.forEach(card => {
                const score = parseFloat(card.getAttribute('data-score') || '0');
                const cardRef = card.getAttribute('data-ref') || '';
                const cardCategory = (card.getAttribute('data-category') || '').toLowerCase();
                const cardText = card.textContent.toLowerCase();

                // Category filter check
                let matchesCategory = true;
                if (activeFilter === 'high') {
                    matchesCategory = (score >= 80) || cardCategory.includes('exact') || cardCategory.includes('strong');
                } else if (activeFilter === 'moderate') {
                    matchesCategory = (score < 80) || cardCategory.includes('moderate');
                }

                // Reference source check
                let matchesRef = (selectedRef === 'all' || cardRef === selectedRef);

                // Search query check
                let matchesSearch = (!query || cardText.includes(query) || cardRef.toLowerCase().includes(query));

                if (matchesCategory && matchesRef && matchesSearch) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            if (visibleCounter) {
                visibleCounter.textContent = visibleCount;
            }

            // Handle dynamic empty filter message
            let noResultsMsg = document.getElementById('filterNoResultsMsg');
            if (visibleCount === 0) {
                if (!noResultsMsg) {
                    noResultsMsg = document.createElement('div');
                    noResultsMsg.id = 'filterNoResultsMsg';
                    noResultsMsg.className = 'empty-state-panel';
                    noResultsMsg.style.padding = '24px 16px';
                    noResultsMsg.innerHTML = '<p class="empty-desc">No flagged passages match the active filter criteria.</p>';
                    const parent = matchCards[0].parentElement;
                    if (parent) parent.appendChild(noResultsMsg);
                }
            } else if (noResultsMsg) {
                noResultsMsg.remove();
            }
        }

        // Filter button click handlers
        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                activeFilter = btn.getAttribute('data-filter') || 'all';
                applyMatchFilters();
            });
        });

        // Search input debounce handler
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', () => {
                clearTimeout(timeout);
                timeout = setTimeout(applyMatchFilters, 150);
            });
        }

        // Reference selector dropdown handler
        if (refSelect) {
            refSelect.addEventListener('change', applyMatchFilters);
        }

        // Jump/Filter to reference from comparison table
        jumpRefButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetRef = btn.getAttribute('data-ref');
                if (refSelect && targetRef) {
                    refSelect.value = targetRef;
                    applyMatchFilters();

                    const panel = document.getElementById('matchedPassagesPanel');
                    if (panel) {
                        panel.scrollIntoView({ behavior: 'smooth' });
                    }
                }
            });
        });

        // Reset all filters button
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                if (searchInput) searchInput.value = '';
                if (refSelect) refSelect.value = 'all';
                activeFilter = 'all';
                filterButtons.forEach(b => {
                    if (b.getAttribute('data-filter') === 'all') {
                        b.classList.add('active');
                    } else {
                        b.classList.remove('active');
                    }
                });
                applyMatchFilters();
            });
        }
    }
});
