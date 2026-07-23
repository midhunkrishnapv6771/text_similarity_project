/* ==========================================================================
   Semantic Text Similarity Web App - JavaScript Controller
   Features: AJAX Comparison, Dark Mode, Character Counter, Preset Chips,
             Sentence Swapping, Clipboard Copy, Keyboard Shortcuts, Vector SVG,
             Secure Dataset CSV Upload & Batch Processing
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements - Theme & Single Mode
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

    // DOM Elements - Navigation Tabs & CSV Upload
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

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        if (themeIcon) {
            themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }

    /* --------------------------------------------------------------------------
       2. Character Counters
       -------------------------------------------------------------------------- */
    function updateCharCounts() {
        if (charCountA && sentenceAInput) charCountA.textContent = `${sentenceAInput.value.length} chars`;
        if (charCountB && sentenceBInput) charCountB.textContent = `${sentenceBInput.value.length} chars`;
    }

    if (sentenceAInput) sentenceAInput.addEventListener('input', updateCharCounts);
    if (sentenceBInput) sentenceBInput.addEventListener('input', updateCharCounts);
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
                if (resultsSection) resultsSection.classList.add('hidden');
            }
        });
    });

    if (swapBtn) {
        swapBtn.addEventListener('click', () => {
            const temp = sentenceAInput.value;
            sentenceAInput.value = sentenceBInput.value;
            sentenceBInput.value = temp;
            updateCharCounts();
        });
    }

    /* --------------------------------------------------------------------------
       4. Mode Navigation Tabs Switching
       -------------------------------------------------------------------------- */
    if (tabSingleMode && tabBatchMode) {
        tabSingleMode.addEventListener('click', (e) => {
            e.preventDefault();
            tabSingleMode.classList.add('active');
            tabBatchMode.classList.remove('active');
            if (compareForm) compareForm.classList.remove('hidden');
            if (uploadForm) uploadForm.classList.add('hidden');
            if (batchResultsSection) batchResultsSection.classList.add('hidden');
            hideError();
        });

        tabBatchMode.addEventListener('click', (e) => {
            e.preventDefault();
            tabBatchMode.classList.add('active');
            tabSingleMode.classList.remove('active');
            if (uploadForm) uploadForm.classList.remove('hidden');
            if (compareForm) compareForm.classList.add('hidden');
            if (resultsSection) resultsSection.classList.add('hidden');
            hideError();
        });
    }

    /* --------------------------------------------------------------------------
       5. Keyboard Shortcut: Ctrl + Enter / Cmd + Enter
       -------------------------------------------------------------------------- */
    [sentenceAInput, sentenceBInput].forEach(textarea => {
        if (textarea) {
            textarea.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    e.preventDefault();
                    if (compareForm) compareForm.dispatchEvent(new Event('submit', { cancelable: true }));
                }
            });
        }
    });

    /* --------------------------------------------------------------------------
       6. Single Pair Form Submission
       -------------------------------------------------------------------------- */
    if (compareForm) {
        compareForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideError();

            const sentA = sentenceAInput.value.trim();
            const sentB = sentenceBInput.value.trim();
            const checkedRadio = document.querySelector('input[name="model"]:checked');
            const selectedModel = checkedRadio ? checkedRadio.value : 'local';

            if (!sentA || !sentB) {
                showError("Both Sentence A and Sentence B are required. Please enter text into both input areas.");
                return;
            }

            setLoadingSingle(true);

            try {
                const response = await fetch('/compare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        sentence_a: sentA,
                        sentence_b: sentB,
                        model: selectedModel
                    })
                });

                let data;
                try {
                    data = await response.json();
                } catch (jsonErr) {
                    if (!response.ok) {
                        throw new Error(`Server Error (${response.status} ${response.statusText}): The server crashed or ran out of memory (512MB limit on Render). Please switch to 'Google Gemini API' mode.`);
                    }
                    throw new Error("Server returned invalid non-JSON response.");
                }

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Failed to calculate semantic similarity.");
                }

                renderSingleResults(data);

            } catch (err) {
                showError(err.message);
                if (resultsSection) resultsSection.classList.add('hidden');
            } finally {
                setLoadingSingle(false);
            }
        });
    }

    function renderSingleResults(data) {
        if (!resultsSection) return;
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

    function setLoadingSingle(isLoading) {
        if (!compareBtn) return;
        if (isLoading) {
            compareBtn.disabled = true;
            if (loadingSpinner) loadingSpinner.classList.remove('hidden');
            const textSpan = compareBtn.querySelector('.btn-text');
            if (textSpan) textSpan.textContent = "Computing Embeddings...";
        } else {
            compareBtn.disabled = false;
            if (loadingSpinner) loadingSpinner.classList.add('hidden');
            const textSpan = compareBtn.querySelector('.btn-text');
            if (textSpan) textSpan.textContent = "Compute Vector Similarity";
        }
    }

    /* --------------------------------------------------------------------------
       7. CSV Dataset File Upload Handlers & Submission
       -------------------------------------------------------------------------- */
    if (browseFileBtn && datasetFileInput) {
        browseFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            datasetFileInput.click();
        });

        if (uploadDropzone) {
            uploadDropzone.addEventListener('click', () => {
                datasetFileInput.click();
            });

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
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    datasetFileInput.files = files;
                    showSelectedFile(files[0].name);
                }
            });
        }

        datasetFileInput.addEventListener('change', () => {
            if (datasetFileInput.files.length > 0) {
                showSelectedFile(datasetFileInput.files[0].name);
            }
        });
    }

    function showSelectedFile(name) {
        if (selectedFileName) {
            selectedFileName.textContent = `Selected: ${name}`;
            selectedFileName.classList.remove('hidden');
        }
    }

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

            const checkedRadio = document.querySelector('input[name="upload_model"]:checked');
            const selectedModel = checkedRadio ? checkedRadio.value : 'local';

            const formData = new FormData();
            formData.append('dataset_file', file);
            formData.append('model', selectedModel);

            setLoadingUpload(true);

            try {
                const response = await fetch('/upload_dataset', {
                    method: 'POST',
                    body: formData
                });

                let data;
                try {
                    data = await response.json();
                } catch (jsonErr) {
                    if (!response.ok) {
                        throw new Error(`Server Error (${response.status} ${response.statusText}): The server crashed or ran out of memory (512MB limit on Render). Please switch to 'Gemini API Batch' mode.`);
                    }
                    throw new Error("Server returned invalid non-JSON response.");
                }

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Batch processing failed.");
                }

                renderBatchResults(data);

            } catch (err) {
                showError(err.message);
                if (batchResultsSection) batchResultsSection.classList.add('hidden');
            } finally {
                setLoadingUpload(false);
            }
        });
    }

    function setLoadingUpload(isLoading) {
        if (!uploadBtn) return;
        if (isLoading) {
            uploadBtn.disabled = true;
            if (uploadSpinner) uploadSpinner.classList.remove('hidden');
            const textSpan = uploadBtn.querySelector('.btn-text');
            if (textSpan) textSpan.textContent = "Processing Batch...";
        } else {
            uploadBtn.disabled = false;
            if (uploadSpinner) uploadSpinner.classList.add('hidden');
            const textSpan = uploadBtn.querySelector('.btn-text');
            if (textSpan) textSpan.textContent = "Process Dataset Batch";
        }
    }

    let latestBatchResults = [];
    const downloadFullCsvBtn = document.getElementById('downloadFullCsvBtn');
    const previewCount = document.getElementById('previewCount');

    function renderBatchResults(data) {
        if (!batchResultsSection) return;
        latestBatchResults = data.results || [];
        
        batchCount.textContent = data.total_processed;
        if (previewCount) {
            previewCount.textContent = Math.min(50, data.total_processed);
        }
        batchAvgLatency.textContent = `${data.avg_latency_ms} ms / pair avg (${data.execution_mode})`;
        
        const now = new Date();
        batchTimestamp.textContent = `Processed at ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

        const displayRows = data.preview_results || (data.results ? data.results.slice(0, 50) : []);
        batchTableBody.innerHTML = '';
        displayRows.forEach(row => {
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

    if (downloadFullCsvBtn) {
        downloadFullCsvBtn.addEventListener('click', () => {
            if (!latestBatchResults || latestBatchResults.length === 0) {
                showError("No dataset results available to download.");
                return;
            }

            // Generate CSV Header & Rows
            let csvContent = "id,sentence_a,sentence_b,similarity_score,similarity_pct,predicted\n";
            latestBatchResults.forEach(r => {
                const sa = `"${r.sentence_a.replace(/"/g, '""')}"`;
                const sb = `"${r.sentence_b.replace(/"/g, '""')}"`;
                csvContent += `${r.id},${sa},${sb},${r.score},${r.similarity_pct},${r.predicted}\n`;
            });

            // Trigger Browser File Download
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.setAttribute('href', url);
            link.setAttribute('download', `evaluated_sts_dataset_${Date.now()}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        });
    }


    /* --------------------------------------------------------------------------
       8. General Helper Functions
       -------------------------------------------------------------------------- */
    function showError(msg) {
        if (errorMessage && errorAlert) {
            errorMessage.textContent = msg;
            errorAlert.classList.remove('hidden');
        }
    }

    function hideError() {
        if (errorAlert) {
            errorAlert.classList.add('hidden');
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /* --------------------------------------------------------------------------
       9. Copy Result Button
       -------------------------------------------------------------------------- */
    if (copyResultBtn) {
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
    }
});
