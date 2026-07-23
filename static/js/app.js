/* ==========================================================================
   Semantic Text Similarity Web App - JavaScript Controller
   Features: AJAX Comparison, Dark Mode, Character Counter, Example Loader,
             Sentence Swapping, Clipboard Copy, Keyboard Shortcuts
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
    
    const exampleSelect = document.getElementById('exampleSelect');
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
        const currentTheme = document.body.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    });

    function setTheme(theme) {
        document.body.setAttribute('data-theme', theme);
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
       3. Example Selector & Sentence Swap
       -------------------------------------------------------------------------- */
    exampleSelect.addEventListener('change', (e) => {
        const selectedId = e.target.value;
        if (examplePairs[selectedId]) {
            sentenceAInput.value = examplePairs[selectedId].a;
            sentenceBInput.value = examplePairs[selectedId].b;
            updateCharCounts();
            hideError();
            resultsSection.classList.add('hidden');
        }
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

        resultsSection.classList.remove('hidden');
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function setLoading(isLoading) {
        if (isLoading) {
            compareBtn.disabled = true;
            loadingSpinner.classList.remove('hidden');
            compareBtn.querySelector('.btn-text').textContent = "Processing Embeddings...";
        } else {
            compareBtn.disabled = false;
            loadingSpinner.classList.add('hidden');
            compareBtn.querySelector('.btn-text').textContent = "Compare Sentences";
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
});
