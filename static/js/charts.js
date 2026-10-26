/**
 * PlagiarismAI - Dashboard Chart Visualizations
 */

function initSimilarityChart(data) {
    const ctx = document.getElementById('similarityDistributionChart');
    if (!ctx) return;

    const low = data.low || 0;
    const moderate = data.moderate || 0;
    const elevated = data.elevated || data.high_intermediate || 0;
    const high = data.high || data.very_high || 0;

    const total = low + moderate + elevated + high;

    if (total === 0) {
        const container = ctx.parentElement;
        container.innerHTML = `
            <div style="text-align: center; padding: 40px 20px; color: #94a3b8;">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 8px; opacity: 0.6;">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <p style="font-size: 13.5px; font-weight: 500;">No document analyses recorded yet.</p>
                <p style="font-size: 12px; margin-top: 4px;">Run an analysis to visualize similarity distributions.</p>
            </div>
        `;
        return;
    }

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [
                'Low (<10%)',
                'Moderate (10–30%)',
                'Elevated (30–60%)',
                'High (≥60%)'
            ],
            datasets: [{
                data: [low, moderate, elevated, high],
                backgroundColor: [
                    '#10b981', // Green
                    '#3b82f6', // Blue
                    '#f59e0b', // Amber
                    '#ef4444'  // Rose Red
                ],
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 14,
                        font: {
                            family: "'Inter', sans-serif",
                            size: 11.5
                        },
                        color: '#475569'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const value = context.raw || 0;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return ` ${context.label}: ${value} analysis (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '68%'
        }
    });
}


function initFormatBreakdownChart(data) {
    const ctx = document.getElementById('formatBreakdownChart');
    if (!ctx) return;

    const pdf = data.pdf || 0;
    const docx = data.docx || 0;
    const txt = data.txt || 0;
    const total = pdf + docx + txt;

    if (total === 0) {
        const container = ctx.parentElement;
        container.innerHTML = `
            <div style="text-align: center; padding: 40px 20px; color: #94a3b8;">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 8px; opacity: 0.6;">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <p style="font-size: 13.5px; font-weight: 500;">No documents in library yet.</p>
                <p style="font-size: 12px; margin-top: 4px;">Upload PDF, Word, or TXT documents to populate breakdown.</p>
            </div>
        `;
        return;
    }

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['PDF (.pdf)', 'Word (.docx)', 'Text (.txt)'],
            datasets: [{
                label: 'Document Count',
                data: [pdf, docx, txt],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.85)',   // PDF red
                    'rgba(37, 99, 235, 0.85)',   // Word blue
                    'rgba(100, 116, 139, 0.85)'  // Text slate
                ],
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return ` ${context.raw} document(s)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: { family: "'Inter', sans-serif", size: 11 }
                    },
                    grid: { color: '#f1f5f9' }
                },
                x: {
                    ticks: {
                        font: { family: "'Inter', sans-serif", size: 12 }
                    },
                    grid: { display: false }
                }
            }
        }
    });
}
