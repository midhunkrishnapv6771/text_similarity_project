/* ==========================================================================
   Semantic Text Similarity Web App - JavaScript Controller
   Features: AJAX Comparison, Dark Mode, Character Counter, Preset Chips,
             Sentence Swapping, Clipboard Copy, Keyboard Shortcuts, Vector SVG
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = themeToggleBtn.querySelector('.theme-icon');
    
    const compareForm = document.getElementById('compareForm');
    const sentenceAInput = document.getElementById('sentenceA');
    const sentenceBInput = document.getElementById('sentenceB');
    const charCountA = document.getElementById('charCountA');
    const charCountB = document.getElementById('charCountB');
    
    const swapBtn = document.getElementById('swapBtn');
    const compareBtn = document.getElementById('compareBtn');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    
    const resultsSection = document.getElementById('resultsSection');
    const scorePct = document.getElementById('scorePct');
    const scoreProgressBar = document.getElementById('scoreProgressBar');
    const predictionBadge = document.getElementById('predictionBadge');
    const executionModeTag = document.getElementById('executionModeTag');
    const latencyTag = document.getElementById('latencyTag');
    const copyResultBtn = document.getElementById('copyResultBtn');
    const svgScoreText = document.getElementById('svgScoreText');
    const resultTimestamp = document.getElementById('resultTimestamp');

    // Preset Example Pairs
    const examplePairs = {
        "1": {
            a: "A plane is taking off from the airport runway.",
            b: "An airplane is ascending into the sky from the tarmac."
        },
        "2": {
            a: "A chef is chopping fresh vegetables in a busy kitchen.",
            b: "A cook is preparing food for dinner on the stove."
        },
        "3": {
            a: "A young boy is playing soccer in the park.",
            b: "A woman is reading a book under a shady tree."
        },
        "4": {
            a: "The stock market experienced a significant surge in trading volume today.",
            b: "Financial indices rallied sharply as investor sentiment turned bullish."
        }
    };

    /* --------------------------------------------------------------------------
       1. Theme Toggle (Light / Dark Mode)
       -------------------------------------------------------------------------- */
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    themeToggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    });

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }

    /* --------------------------------------------------------------------------
       2. Character Counters
       -------------------------------------------------------------------------- */
    function updateCharCounts() {
        charCountA.textContent = `${sentenceAInput.value.length} chars`;
        charCountB.textContent = `${sentenceBInput.value.length} chars`;
    }

    sentenceAInput.addEventListener('input', updateCharCounts);
    sentenceBInput.addEventListener('input', updateCharCounts);
    updateCharCounts();

    /* --------------------------------------------------------------------------
       3. Preset Chips & Sentence Swap
       -------------------------------------------------------------------------- */
    document.querySelectorAll('.chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const presetId = btn.getAttribute('data-preset');
            if (examplePairs[presetId]) {
                sentenceAInput.value = examplePairs[presetId].a;
                sentenceBInput.value = examplePairs[presetId].b;
                updateCharCounts();
                hideError();
                resultsSection.classList.add('hidden');
            }
        });
    });

    swapBtn.addEventListener('click', () => {
        const temp = sentenceAInput.value;
        sentenceAInput.value = sentenceBInput.value;
        sentenceBInput.value = temp;
        updateCharCounts();
    });

    /* --------------------------------------------------------------------------
       4. Keyboard Shortcut: Ctrl + Enter / Cmd + Enter
       -------------------------------------------------------------------------- */
    [sentenceAInput, sentenceBInput].forEach(textarea => {
        textarea.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                compareForm.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        });
    });

    /* --------------------------------------------------------------------------
       5. AJAX Form Submission & Evaluation
       -------------------------------------------------------------------------- */
    compareForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError();

        const sentA = sentenceAInput.value.trim();
        const sentB = sentenceBInput.value.trim();
        const selectedModel = document.querySelector('input[name="model"]:checked').value;

        if (!sentA || !sentB) {
            showError("Both Sentence A and Sentence B are required. Please enter text into both input areas.");
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('/compare', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    sentence_a: sentA,
                    sentence_b: sentB,
                    model: selectedModel
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Failed to calculate semantic similarity.");
            }

            renderResults(data);

        } catch (err) {
            showError(err.message);
            resultsSection.classList.add('hidden');
        } finally {
            setLoading(false);
        }
    });

    /* --------------------------------------------------------------------------
       6. Render Results & UI Helpers
       -------------------------------------------------------------------------- */
    function renderResults(data) {
        scorePct.textContent = data.similarity_pct;
        
        const scoreVal = data.score * 100;
        scoreProgressBar.style.width = `${Math.min(100, Math.max(0, scoreVal))}%`;

        predictionBadge.textContent = data.predicted.toUpperCase();
        if (data.predicted === "Similar") {
            predictionBadge.className = "badge badge-similar";
        } else {
            predictionBadge.className = "badge badge-not-similar";
        }

        executionModeTag.textContent = data.execution_mode;
        latencyTag.textContent = `${data.latency_ms} ms`;
        
        if (svgScoreText) {
            svgScoreText.textContent = `Score: ${data.score.toFixed(4)}`;
        }

        if (resultTimestamp) {
            const now = new Date();
            resultTimestamp.textContent = `Evaluated at ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
        }

        resultsSection.classList.remove('hidden');
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function setLoading(isLoading) {
        if (isLoading) {
            compareBtn.disabled = true;
            loadingSpinner.classList.remove('hidden');
            compareBtn.querySelector('.btn-text').textContent = "Computing Embeddings...";
        } else {
            compareBtn.disabled = false;
            loadingSpinner.classList.add('hidden');
            compareBtn.querySelector('.btn-text').textContent = "Compute Vector Similarity";
        }
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorAlert.classList.remove('hidden');
    }

    function hideError() {
        errorAlert.classList.add('hidden');
    }

    /* --------------------------------------------------------------------------
       7. Copy Result Button
       -------------------------------------------------------------------------- */
    copyResultBtn.addEventListener('click', () => {
        const textToCopy = `Semantic Similarity Evaluation:\n` +
                           `Score: ${scorePct.textContent}\n` +
                           `Prediction: ${predictionBadge.textContent}\n` +
                           `Execution Mode: ${executionModeTag.textContent}\n` +
                           `Latency: ${latencyTag.textContent}\n` +
                           `Sentence A: "${sentenceAInput.value.trim()}"\n` +
                           `Sentence B: "${sentenceBInput.value.trim()}"`;
                           
        navigator.clipboard.writeText(textToCopy).then(() => {
            const originalText = copyResultBtn.textContent;
            copyResultBtn.textContent = "✅ Copied!";
            setTimeout(() => {
                copyResultBtn.textContent = originalText;
            }, 2000);
        }).catch(err => {
            console.error("Clipboard copy failed:", err);
        });
    });

    /* --------------------------------------------------------------------------
       8. Tab Navigation & Secure CSV File Upload
       -------------------------------------------------------------------------- */
    const tabSingleMode = document.getElementById('tabSingleMode');
    const tabBatchMode = document.getElementById('tabBatchMode');
    const uploadForm = document.getElementById('uploadForm');

    const uploadDropzone = document.getElementById('uploadDropzone');
    const browseFileBtn = document.getElementById('browseFileBtn');
    const datasetFileInput = document.getElementById('datasetFileInput');
    const selectedFileName = document.getElementById('selectedFileName');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadSpinner = document.getElementById('uploadSpinner');

    const batchResultsSection = document.getElementById('batchResultsSection');
    const batchCount = document.getElementById('batchCount');
    const batchTimestamp = document.getElementById('batchTimestamp');
    const batchAvgLatency = document.getElementById('batchAvgLatency');
    const batchTableBody = document.getElementById('batchTableBody');

    if (tabSingleMode && tabBatchMode) {
        tabSingleMode.addEventListener('click', () => {
            tabSingleMode.classList.add('active');
            tabBatchMode.classList.remove('active');
            compareForm.classList.remove('hidden');
            uploadForm.classList.add('hidden');
            batchResultsSection.classList.add('hidden');
            hideError();
        });

        tabBatchMode.addEventListener('click', () => {
            tabBatchMode.classList.add('active');
            tabSingleMode.classList.remove('active');
            uploadForm.classList.remove('hidden');
            compareForm.classList.add('hidden');
            resultsSection.classList.add('hidden');
            hideError();
        });
    }

    if (browseFileBtn && datasetFileInput) {
        browseFileBtn.addEventListener('click', () => datasetFileInput.click());
        uploadDropzone.addEventListener('click', (e) => {
            if (e.target !== browseFileBtn) datasetFileInput.click();
        });

        datasetFileInput.addEventListener('change', () => {
            if (datasetFileInput.files.length > 0) {
                selectedFileName.textContent = `Selected: ${datasetFileInput.files[0].name}`;
                selectedFileName.classList.remove('hidden');
            }
        });

        // Drag and drop handlers
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadDropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                uploadDropzone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadDropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                uploadDropzone.classList.remove('dragover');
            }, false);
        });

        uploadDropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                datasetFileInput.files = files;
                selectedFileName.textContent = `Selected: ${files[0].name}`;
                selectedFileName.classList.remove('hidden');
            }
        });
    }

    /* --------------------------------------------------------------------------
       9. Batch CSV Upload Submission
       -------------------------------------------------------------------------- */
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideError();

            if (!datasetFileInput.files || datasetFileInput.files.length === 0) {
                showError("Please select or drag a valid .CSV dataset file to process.");
                return;
            }

            const file = datasetFileInput.files[0];
            if (!file.name.toLowerCase().endsWith('.csv')) {
                showError("Security Restriction: Only authentic .CSV dataset files are allowed.");
                return;
            }

            const selectedModel = document.querySelector('input[name="upload_model"]:checked').value;
            const formData = new FormData();
            formData.append('dataset_file', file);
            formData.append('model', selectedModel);

            uploadBtn.disabled = true;
            uploadSpinner.classList.remove('hidden');

            try {
                const response = await fetch('/upload_dataset', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Batch processing failed.");
                }

                renderBatchResults(data);

            } catch (err) {
                showError(err.message);
                batchResultsSection.classList.add('hidden');
            } finally {
                uploadBtn.disabled = false;
                uploadSpinner.classList.add('hidden');
            }
        });
    }

    function renderBatchResults(data) {
        batchCount.textContent = data.total_processed;
        batchAvgLatency.textContent = `${data.avg_latency_ms} ms / pair avg (${data.execution_mode})`;
        
        const now = new Date();
        batchTimestamp.textContent = `Processed at ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

        batchTableBody.innerHTML = '';
        data.results.forEach(row => {
            const tr = document.createElement('tr');
            const isSimilar = row.predicted === 'Similar';
            const badgeClass = isSimilar ? 'badge-similar' : 'badge-not-similar';
            
            tr.innerHTML = `
                <td><strong>${row.id}</strong></td>
                <td>${escapeHtml(row.sentence_a)}</td>
                <td>${escapeHtml(row.sentence_b)}</td>
                <td><strong style="color: var(--accent-blue); font-family: 'JetBrains Mono', monospace;">${row.similarity_pct}</strong></td>
                <td><span class="badge ${badgeClass}" style="font-size: 0.8rem; padding: 2px 8px;">${row.predicted.toUpperCase()}</span></td>
            `;
            batchTableBody.appendChild(tr);
        });

        batchResultsSection.classList.remove('hidden');
        batchResultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});

});
