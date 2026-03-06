/* ═══════════════════════════════════════════
   HPTU AI ASSISTANT — Professional JS v3.0
   ═══════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

    // ═══════ DOM REFS ═══════
    const chatContainer = document.getElementById('chatContainer');
    const chatBody = document.getElementById('chatBody');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('send-message');
    const voiceBtn = document.getElementById('voice-btn');
    const pdfUpload = document.getElementById('pdfUpload');
    const pdfIndicator = document.getElementById('pdfIndicator');
    const pdfFileName = document.getElementById('pdfFileName');
    const chatToggle = document.getElementById('chatToggle');
    const splashScreen = document.getElementById('splashScreen');
    const themeToggle = document.getElementById('themeToggle');
    const navToggle = document.getElementById('navToggle');
    const navContent = document.getElementById('navContent');
    const backToTop = document.getElementById('backToTop');

    let uploadedPdf = null;

    // ═══════ SPLASH SCREEN ═══════
    setTimeout(() => {
        if (splashScreen) {
            splashScreen.classList.add('fade-out');
            setTimeout(() => { splashScreen.style.display = 'none'; }, 600);
        }
    }, 2800);

    // ═══════ DARK MODE ═══════
    function initTheme() {
        const saved = localStorage.getItem('hptu-theme');
        if (saved === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
        }
    }

    initTheme();

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('hptu-theme', next);
        });
    }

    // ═══════ MOBILE NAV ═══════
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            navContent.classList.toggle('active');
        });
    }

    // Close nav on link click (mobile)
    document.querySelectorAll('.nav-content a').forEach(link => {
        link.addEventListener('click', () => {
            navContent.classList.remove('active');
        });
    });

    // ═══════ SCROLL REVEAL ═══════
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.reveal, .reveal-stagger').forEach(el => {
        revealObserver.observe(el);
    });

    // ═══════ BACK TO TOP ═══════
    window.addEventListener('scroll', () => {
        if (window.scrollY > 500) {
            backToTop.classList.add('visible');
        } else {
            backToTop.classList.remove('visible');
        }
    });

    if (backToTop) {
        backToTop.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // ═══════ SMOOTH SCROLL FOR NAV ═══════
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ═══════ COUNTER ANIMATION ═══════
    function animateCounter(el, target) {
        const dur = 1200;
        const start = 0;
        const startTime = performance.now();
        function update(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / dur, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.floor(eased * target);
            if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
    }

    // ═══════ CHAT TOGGLE ═══════
    window.openChat = function () {
        chatContainer.style.display = 'flex';
        chatToggle.classList.add('active');
        chatToggle.innerHTML = '<i class="fas fa-times"></i>';
        userInput.focus();
        chatBody.scrollTop = chatBody.scrollHeight;
    };

    window.closeChat = function () {
        chatContainer.style.display = 'none';
        chatToggle.classList.remove('active');
        chatToggle.innerHTML = '<i class="fas fa-comments"></i>';
    };

    window.clearChat = function () {
        chatBody.innerHTML = '';
        addBotMessage("Chat cleared! How can I help you?");
    };

    chatToggle.addEventListener('click', () => {
        if (chatContainer.style.display === 'flex') {
            closeChat();
        } else {
            openChat();
        }
    });

    // ═══════ VOICE INPUT ═══════
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-IN';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        voiceBtn.addEventListener('click', () => {
            if (voiceBtn.classList.contains('listening')) {
                recognition.stop();
                return;
            }
            voiceBtn.classList.add('listening');
            recognition.start();
        });

        recognition.addEventListener('result', (e) => {
            const transcript = e.results[0][0].transcript;
            userInput.value = transcript;
            voiceBtn.classList.remove('listening');
            sendMessage();
        });

        recognition.addEventListener('end', () => {
            voiceBtn.classList.remove('listening');
        });

        recognition.addEventListener('error', () => {
            voiceBtn.classList.remove('listening');
        });
    } else {
        voiceBtn.style.display = 'none';
    }

    // ═══════ PDF UPLOAD ═══════
    pdfUpload.addEventListener('change', function () {
        const file = this.files[0];
        if (file && file.type === 'application/pdf') {
            uploadedPdf = file;
            pdfFileName.textContent = file.name;
            pdfIndicator.classList.remove('hidden');
        }
    });

    window.removePdf = function () {
        uploadedPdf = null;
        pdfUpload.value = '';
        pdfIndicator.classList.add('hidden');
    };

    // ═══════ SEND MESSAGE ═══════
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function sendMessage() {
        const text = userInput.value.trim();
        if (!text && !uploadedPdf) return;

        addUserMessage(text || 'Uploaded a PDF for analysis');
        userInput.value = '';
        showTypingIndicator();

        if (uploadedPdf) {
            const formData = new FormData();
            formData.append('pdf', uploadedPdf);
            if (text) formData.append('question', text);

            fetch('/upload', { method: 'POST', body: formData })
                .then(r => r.json())
                .then(data => {
                    removeTypingIndicator();
                    addBotMessage(data.message || data.error || 'Could not process the PDF.');
                })
                .catch(() => {
                    removeTypingIndicator();
                    addBotMessage('Sorry, there was an error processing your PDF.');
                });

            removePdf();
        } else {
            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            })
                .then(r => r.json())
                .then(data => {
                    removeTypingIndicator();
                    addBotMessage(data.reply || 'Sorry, I could not process your request.');
                })
                .catch(() => {
                    removeTypingIndicator();
                    addBotMessage('Sorry, there was a connection error. Please try again.');
                });
        }
    }

    // ═══════ MESSAGE HELPERS ═══════
    function addUserMessage(text) {
        const div = document.createElement('div');
        div.className = 'user-message';
        div.innerHTML = '<div class="user-bubble">' + escapeHtml(text) + '</div>';
        chatBody.appendChild(div);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function addBotMessage(text) {
        const div = document.createElement('div');
        div.className = 'bot-message';
        div.innerHTML =
            '<div class="msg-avatar"><img src="https://media.9curry.com/uploads/organization/image/2794/hptu-logo.png" alt="HPTU"></div>' +
            '<div class="msg-bubble">' + formatBotMessage(text) + '</div>';
        chatBody.appendChild(div);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function showTypingIndicator() {
        const div = document.createElement('div');
        div.className = 'typing-indicator';
        div.id = 'typingIndicator';
        div.innerHTML =
            '<div class="msg-avatar"><img src="https://media.9curry.com/uploads/organization/image/2794/hptu-logo.png" alt="HPTU"></div>' +
            '<div class="typing-dots"><span></span><span></span><span></span></div>';
        chatBody.appendChild(div);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function removeTypingIndicator() {
        const ti = document.getElementById('typingIndicator');
        if (ti) ti.remove();
    }

    function escapeHtml(text) {
        const el = document.createElement('div');
        el.textContent = text;
        return el.innerHTML;
    }

    // ═══════ BOT MESSAGE FORMATTER ═══════
    function formatBotMessage(text) {
        if (!text) return '';

        // Escape HTML first
        let formatted = escapeHtml(text);

        // Headings (### > ## > #)
        formatted = formatted.replace(/^### (.+)$/gm, '<strong class="chat-heading" style="font-size:13px;">$1</strong>');
        formatted = formatted.replace(/^## (.+)$/gm, '<strong class="chat-heading">$1</strong>');
        formatted = formatted.replace(/^# (.+)$/gm, '<strong class="chat-heading" style="font-size:15px;">$1</strong>');

        // Horizontal rules
        formatted = formatted.replace(/^---$/gm, '<hr class="chat-divider">');

        // Bold
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Italic
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Links — URLs
        formatted = formatted.replace(
            /(?<!\()((https?:\/\/)[^\s<]+)/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1 <i class="fas fa-external-link-alt"></i></a>'
        );

        // Numbered lists
        formatted = formatted.replace(/^\d+\.\s+(.+)$/gm, '<span style="display:block;padding-left:16px;margin:2px 0;">• $1</span>');

        // Bullet lists
        formatted = formatted.replace(/^[-*]\s+(.+)$/gm, '<span style="display:block;padding-left:16px;margin:2px 0;">• $1</span>');

        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    // ═══════ LOAD NOTICES ═══════
    function loadHptuNotices() {
        fetch('/api/hptu-notices')
            .then(r => r.json())
            .then(data => {
                const notices = data.notices || [];
                window.hptuNoticesData = notices;
                document.getElementById('statNotices').textContent = notices.length;
                animateCounter(document.getElementById('statNotices'), notices.length);
                renderHptuNotices('all');
            })
            .catch(() => {
                document.getElementById('hptuNoticesList').innerHTML =
                    '<div class="empty-placeholder"><i class="fas fa-exclamation-circle"></i><p>Could not load notices</p></div>';
            });
    }

    function renderHptuNotices(filter) {
        const container = document.getElementById('hptuNoticesList');
        const notices = window.hptuNoticesData || [];

        let filtered = notices;
        if (filter && filter !== 'all') {
            filtered = notices.filter(n => {
                const title = (n.title || '').toLowerCase();
                const cat = (n.category || '').toLowerCase();
                return title.includes(filter) || cat.includes(filter);
            });
        }

        if (filtered.length === 0) {
            container.innerHTML = '<div class="empty-placeholder"><i class="fas fa-inbox"></i><p>No notices found</p></div>';
            return;
        }

        container.innerHTML = filtered.slice(0, 20).map(n => {
            const category = n.category || 'general';
            const badgeClass = 'badge-' + category.toLowerCase().replace(/\s+/g, '-');
            const date = n.date || '';
            const link = n.link || '#';
            const title = n.title || 'Untitled Notice';
            const aiTag = n.ai_categorized
                ? '<span class="ai-scanned-badge"><i class="fas fa-brain"></i> AI</span>'
                : '';

            return '<div class="notice-item">' +
                '<div class="notice-icon"><i class="fas fa-file-alt"></i></div>' +
                '<div class="notice-content">' +
                '<strong>' + escapeHtml(title) +
                '<span class="notice-category-badge ' + badgeClass + '">' + escapeHtml(category) + '</span>' +
                aiTag + '</strong>' +
                '<p><i class="fas fa-calendar-alt" style="margin-right:4px;"></i>' + escapeHtml(date) +
                (link !== '#' ? ' &mdash; <a href="' + encodeURI(link) + '" target="_blank" rel="noopener noreferrer">View <i class="fas fa-external-link-alt" style="font-size:9px;"></i></a>' : '') +
                '</p></div></div>';
        }).join('');
    }

    function loadNotices() {
        fetch('/api/notices')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('noticesList');
                const notices = data.notices || [];

                if (notices.length === 0) {
                    container.innerHTML = '<div class="empty-placeholder"><i class="fas fa-inbox"></i><p>No announcements yet</p></div>';
                    return;
                }

                container.innerHTML = notices.map(n => {
                    return '<div class="notice-item">' +
                        '<div class="notice-icon"><i class="fas fa-bullhorn"></i></div>' +
                        '<div class="notice-content">' +
                        '<strong>' + escapeHtml(n.title || 'Announcement') + '</strong>' +
                        '<p>' + escapeHtml(n.content || '') + '</p>' +
                        '</div></div>';
                }).join('');
            })
            .catch(() => {
                document.getElementById('noticesList').innerHTML =
                    '<div class="empty-placeholder"><i class="fas fa-exclamation-circle"></i><p>Could not load announcements</p></div>';
            });
    }

    // ═══════ NOTICE FILTERS ═══════
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            renderHptuNotices(this.getAttribute('data-filter'));
        });
    });

    // ═══════ LOAD SYLLABUS ═══════
    function loadSyllabus() {
        fetch('/api/syllabus')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('syllabusGrid');
                const items = data.syllabus || [];

                animateCounter(document.getElementById('statSyllabus'), items.length);

                if (items.length === 0) {
                    container.innerHTML = '<div class="empty-placeholder"><i class="fas fa-book-open"></i><p>No syllabus data</p></div>';
                    return;
                }

                container.innerHTML = items.map(s => {
                    const title = s.title || s.name || 'Syllabus Document';
                    const program = s.program || '';
                    const link = s.link || s.url || '#';

                    return '<div class="syllabus-card">' +
                        '<div class="syllabus-icon"><i class="fas fa-book"></i></div>' +
                        '<div class="syllabus-info">' +
                        '<h4>' + escapeHtml(title) + '</h4>' +
                        (program ? '<span class="syllabus-program">' + escapeHtml(program) + '</span>' : '') +
                        (link !== '#' ? '<a class="syllabus-download" href="' + encodeURI(link) + '" target="_blank" rel="noopener noreferrer"><i class="fas fa-download"></i> Download</a>' : '') +
                        '</div></div>';
                }).join('');
            })
            .catch(() => {
                document.getElementById('syllabusGrid').innerHTML =
                    '<div class="empty-placeholder"><i class="fas fa-exclamation-circle"></i><p>Could not load syllabus</p></div>';
            });
    }

    // ═══════ LOAD FEES ═══════
    function loadFees() {
        fetch('/api/fees')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('feesContainer');
                const items = data.fees || [];

                if (items.length === 0) {
                    container.innerHTML = '<div class="empty-placeholder"><i class="fas fa-rupee-sign"></i><p>No fee data</p></div>';
                    return;
                }

                container.innerHTML = items.map(f => {
                    const title = f.title || f.name || 'Fee Document';
                    const amount = f.amount || '';
                    const link = f.link || f.url || '#';
                    const desc = f.description || '';

                    return '<div class="fee-card">' +
                        '<div class="fee-icon"><i class="fas fa-rupee-sign"></i></div>' +
                        '<div class="fee-info">' +
                        '<h4>' + escapeHtml(title) + '</h4>' +
                        (desc ? '<p>' + escapeHtml(desc) + '</p>' : '') +
                        (amount ? '<span class="fee-amount">' + escapeHtml(amount) + '</span>' : '') +
                        (link !== '#' ? '<a class="fee-download" href="' + encodeURI(link) + '" target="_blank" rel="noopener noreferrer"><i class="fas fa-download"></i> Download</a>' : '') +
                        '</div></div>';
                }).join('');
            })
            .catch(() => {
                document.getElementById('feesContainer').innerHTML =
                    '<div class="empty-placeholder"><i class="fas fa-exclamation-circle"></i><p>Could not load fee data</p></div>';
            });
    }

    // ═══════ LOAD SCRAPER STATUS ═══════
    function loadScraperStatus() {
        fetch('/api/scraper-status')
            .then(r => r.json())
            .then(data => {
                if (data.total_pdfs) {
                    animateCounter(document.getElementById('statPdfs'), data.total_pdfs);
                }
                if (data.last_run) {
                    const d = new Date(data.last_run);
                    document.getElementById('statUpdated').textContent = d.toLocaleDateString('en-IN', {
                        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                    });
                }
            })
            .catch(() => {});
    }

    // ═══════ INIT ═══════
    loadHptuNotices();
    loadNotices();
    loadSyllabus();
    loadFees();
    loadScraperStatus();

    // Auto-refresh every 5 minutes
    setInterval(() => {
        loadHptuNotices();
        loadNotices();
        loadScraperStatus();
    }, 300000);
});
