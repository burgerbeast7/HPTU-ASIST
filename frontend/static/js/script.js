document.addEventListener("DOMContentLoaded", function () {
    const chatBody = document.getElementById("chat-body");
    const userInput = document.getElementById("user-input");
    const sendMessageButton = document.getElementById("send-message");
    const toggleChatButton = document.getElementById("toggle-chat");
    const closeChatButton = document.getElementById("close-chat");
    const chatContainer = document.getElementById("chat-container");
    const chatIcon = document.getElementById("chat-icon");
    const pdfFileInput = document.getElementById("pdfFile");
    const pdfIndicator = document.getElementById("pdf-indicator");
    const pdfNameSpan = document.getElementById("pdf-name");
    const removePdfButton = document.getElementById("remove-pdf");
    const clearPdfBtn = document.getElementById("clear-pdf-btn");
    const navToggle = document.getElementById("nav-toggle");
    const navContent = document.querySelector(".nav-content");
    const heroCta = document.getElementById("open-chat-hero");
    const chatStatus = document.getElementById("chat-status");

    let isSending = false;

    // ─── Toggle Chat ────────────────────────────
    function openChat() {
        chatContainer.style.display = "flex";
        toggleChatButton.classList.add("active");
        chatIcon.className = "fas fa-times";
        userInput.focus();
    }

    function closeChat() {
        chatContainer.style.display = "none";
        toggleChatButton.classList.remove("active");
        chatIcon.className = "fas fa-comments";
    }

    toggleChatButton.addEventListener("click", function () {
        if (chatContainer.style.display === "flex") {
            closeChat();
        } else {
            openChat();
        }
    });

    closeChatButton.addEventListener("click", closeChat);

    if (heroCta) {
        heroCta.addEventListener("click", openChat);
    }

    // ─── Mobile Nav Toggle ──────────────────────
    if (navToggle && navContent) {
        navToggle.addEventListener("click", function () {
            navContent.classList.toggle("active");
        });
    }

    // ─── PDF Upload ─────────────────────────────
    pdfFileInput.addEventListener("change", async function () {
        const file = pdfFileInput.files[0];
        if (!file) return;

        if (file.type !== "application/pdf") {
            addBotMessage("⚠️ Only PDF files are allowed. Please select a .pdf file.");
            pdfFileInput.value = "";
            return;
        }

        pdfNameSpan.textContent = file.name;
        pdfIndicator.classList.remove("hidden");
        if (clearPdfBtn) clearPdfBtn.classList.remove("hidden");

        const formData = new FormData();
        formData.append("pdf", file);

        addBotMessage("⏳ Uploading and processing your PDF...");

        try {
            const response = await fetch("/upload", { method: "POST", body: formData });
            const result = await response.json();
            if (response.ok) {
                addBotMessage("✅ " + result.message + "\n\nYou can now ask questions about this document!");
            } else {
                addBotMessage("❌ " + (result.error || "Failed to upload PDF."));
                hidePdfIndicator();
            }
        } catch (error) {
            console.error("Upload error:", error);
            addBotMessage("❌ Could not upload the PDF. Please check your connection.");
            hidePdfIndicator();
        }
    });

    if (removePdfButton) removePdfButton.addEventListener("click", clearPdfContext);
    if (clearPdfBtn) clearPdfBtn.addEventListener("click", clearPdfContext);

    async function clearPdfContext() {
        try { await fetch("/clear-pdf", { method: "POST" }); } catch (e) {}
        hidePdfIndicator();
        pdfFileInput.value = "";
        addBotMessage("📄 PDF context cleared. I'll answer from real-time HPTU data now.");
    }

    function hidePdfIndicator() {
        pdfIndicator.classList.add("hidden");
        if (clearPdfBtn) clearPdfBtn.classList.add("hidden");
    }

    // ─── Send Message ───────────────────────────
    async function sendMessage() {
        const userMessage = userInput.value.trim();
        if (!userMessage || isSending) return;

        isSending = true;
        addUserMessage(userMessage);
        userInput.value = "";

        const typingEl = showTypingIndicator();
        chatStatus.textContent = "● Thinking...";
        chatStatus.style.color = "#f4b400";

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMessage })
            });

            const data = await response.json();
            removeTypingIndicator(typingEl);
            chatStatus.textContent = "● Online — Real-time Data";
            chatStatus.style.color = "#6fcf97";
            addBotMessage(data.reply);
        } catch (error) {
            console.error("Chat error:", error);
            removeTypingIndicator(typingEl);
            chatStatus.textContent = "● Online — Real-time Data";
            chatStatus.style.color = "#6fcf97";
            addBotMessage("❌ Sorry, I couldn't connect. Please try again.");
        }

        isSending = false;
    }

    sendMessageButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // ─── Message Helpers ────────────────────────
    function addUserMessage(message) {
        const wrapper = document.createElement("div");
        wrapper.className = "user-message";
        const bubble = document.createElement("div");
        bubble.className = "user-bubble";
        bubble.textContent = message;
        wrapper.appendChild(bubble);
        chatBody.appendChild(wrapper);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function formatBotMessage(text) {
        // Escape HTML first to prevent XSS
        let msg = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Markdown links: [text](url)
        msg = msg.replace(
            /\[([^\]]+)\]\(((https?:\/\/)[^\s)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener noreferrer">$1 <i class="fas fa-external-link-alt"></i></a>'
        );

        // Angle-bracket links: <url>
        msg = msg.replace(
            /&lt;(https?:\/\/[^\s&]+)&gt;/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1 <i class="fas fa-external-link-alt"></i></a>'
        );

        // Bare URLs that are NOT already inside an href="..."
        msg = msg.replace(
            /(?<!["=])(https?:\/\/[^\s<"'\)]+)/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1 <i class="fas fa-external-link-alt"></i></a>'
        );

        // Bold: **text** or __text__
        msg = msg.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        msg = msg.replace(/__(.+?)__/g, "<strong>$1</strong>");

        // Italic: *text* or _text_ (not inside words)
        msg = msg.replace(/(?<![\w])\*([^*]+?)\*(?![\w])/g, "<em>$1</em>");

        // Headings: ### text
        msg = msg.replace(/^### (.+)$/gm, '<strong class="chat-heading">$1</strong>');
        msg = msg.replace(/^## (.+)$/gm, '<strong class="chat-heading">$1</strong>');

        // Bullet lists: lines starting with - or •
        msg = msg.replace(/^[\-•] (.+)$/gm, '&bull; $1');

        // Numbered lists: 1. text
        msg = msg.replace(/^(\d+)\. (.+)$/gm, '<strong>$1.</strong> $2');

        // Horizontal separators: --- or ═══
        msg = msg.replace(/^[-═]{3,}$/gm, '<hr class="chat-divider">');

        // Newlines to <br>
        msg = msg.replace(/\n/g, "<br>");

        return msg;
    }

    function addBotMessage(message) {
        const wrapper = document.createElement("div");
        wrapper.className = "bot-message";
        const avatar = document.createElement("div");
        avatar.className = "msg-avatar";
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";
        bubble.innerHTML = formatBotMessage(message);
        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        chatBody.appendChild(wrapper);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function showTypingIndicator() {
        const wrapper = document.createElement("div");
        wrapper.className = "typing-indicator";
        const avatar = document.createElement("div");
        avatar.className = "msg-avatar";
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
        const dots = document.createElement("div");
        dots.className = "typing-dots";
        dots.innerHTML = "<span></span><span></span><span></span>";
        wrapper.appendChild(avatar);
        wrapper.appendChild(dots);
        chatBody.appendChild(wrapper);
        chatBody.scrollTop = chatBody.scrollHeight;
        return wrapper;
    }

    function removeTypingIndicator(el) {
        if (el && el.parentNode) el.parentNode.removeChild(el);
    }

    // ─── Load Scraper Status ────────────────────
    async function loadScraperStatus() {
        try {
            const response = await fetch("/api/scraper-status");
            const data = await response.json();
            var el;

            el = document.getElementById("stat-notices");
            if (el) el.textContent = data.notices_count || "0";

            el = document.getElementById("stat-pdfs");
            if (el) el.textContent = data.pdfs_scanned || "0";

            el = document.getElementById("stat-syllabus");
            if (el) el.textContent = data.syllabus_count || "0";

            el = document.getElementById("stat-updated");
            if (el) el.textContent = data.last_run || "Never";

            // Update badge
            var badge = document.getElementById("auto-update-badge");
            if (badge) {
                if (data.status === "success") {
                    badge.innerHTML = '<i class="fas fa-check-circle"></i> Data synced';
                    badge.style.color = "#6fcf97";
                } else if (data.status === "running") {
                    badge.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Updating...';
                    badge.style.color = "#f4b400";
                }
            }
        } catch (e) {
            console.error("Status load error:", e);
        }
    }

    // ─── Load Notices ───────────────────────────
    async function loadNotices() {
        try {
            const response = await fetch("/api/notices");
            const data = await response.json();
            const noticesList = document.getElementById("notices-list");
            if (!noticesList) return;

            noticesList.innerHTML = "";
            const entries = Object.values(data);
            if (entries.length === 0) {
                noticesList.innerHTML = '<div class="notice-item"><div class="notice-icon"><i class="fas fa-info-circle"></i></div><div class="notice-content"><strong>No announcements at the moment.</strong></div></div>';
                return;
            }

            entries.forEach(function (notice) {
                const item = document.createElement("div");
                item.className = "notice-item";
                item.innerHTML =
                    '<div class="notice-icon"><i class="fas fa-bell"></i></div>' +
                    '<div class="notice-content">' +
                    "<strong>" + (notice.title || "Notice") + "</strong>" +
                    "<p>" + (notice.date || "") + (notice.description ? " — " + notice.description : "") + "</p>" +
                    "</div>";
                noticesList.appendChild(item);
            });
        } catch (e) {
            console.error("Failed to load notices:", e);
        }
    }

    // ─── Load HPTU Official Notices ─────────────
    var allHptuNotices = [];

    async function loadHptuNotices() {
        var hptuList = document.getElementById("hptu-notices-list");
        if (!hptuList) return;

        try {
            var response = await fetch("/api/hptu-notices");
            var data = await response.json();
            allHptuNotices = data || [];
            renderHptuNotices("all");
        } catch (e) {
            console.error("Failed to load HPTU notices:", e);
            hptuList.innerHTML =
                '<div class="notice-item">' +
                '<div class="notice-icon"><i class="fas fa-exclamation-triangle" style="color:#c0392b;"></i></div>' +
                '<div class="notice-content"><strong>Could not load notifications.</strong><p>Please check back later.</p></div>' +
                '</div>';
        }
    }

    function renderHptuNotices(filter) {
        var hptuList = document.getElementById("hptu-notices-list");
        if (!hptuList) return;

        hptuList.innerHTML = "";

        var filtered = allHptuNotices;
        if (filter && filter !== "all") {
            filtered = allHptuNotices.filter(function(n) {
                return (n.category || "general") === filter;
            });
        }

        if (filtered.length === 0) {
            hptuList.innerHTML =
                '<div class="notice-item">' +
                '<div class="notice-icon"><i class="fas fa-info-circle"></i></div>' +
                '<div class="notice-content"><strong>No notifications found for this category.</strong></div>' +
                '</div>';
            return;
        }

        filtered.forEach(function (notice) {
            var item = document.createElement("div");
            item.className = "notice-item";
            item.setAttribute("data-category", notice.category || "general");

            var categoryBadge = "";
            var catColors = {
                examination: "#c0392b",
                admission: "#27ae60",
                fees: "#d4a200",
                syllabus: "#7c3aed",
                recruitment: "#e67e22",
                general: "#0b2c6b"
            };
            var cat = notice.category || "general";
            categoryBadge = '<span style="background:' + (catColors[cat] || "#0b2c6b") +
                '; color:#fff; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:600; margin-left:8px;">' +
                cat.charAt(0).toUpperCase() + cat.slice(1) + '</span>';

            var linkHtml = "";
            if (notice.link) {
                linkHtml = ' <a href="' + notice.link + '" target="_blank" rel="noopener" style="color:#0b2c6b; font-weight:600; font-size:12px;"><i class="fas fa-external-link-alt"></i> View</a>';
            }

            var pdfBadge = "";
            if (notice.pdf_text) {
                pdfBadge = ' <span style="background:#e6f7ef; color:#27ae60; padding:2px 6px; border-radius:8px; font-size:10px;"><i class="fas fa-check"></i> AI Scanned</span>';
            }

            item.innerHTML =
                '<div class="notice-icon"><i class="fas fa-globe" style="color:#0b2c6b;"></i></div>' +
                '<div class="notice-content">' +
                "<strong>" + (notice.title || "Notification") + "</strong>" + categoryBadge + pdfBadge +
                "<p>" + (notice.date || "") +
                (notice.last_date ? " | Deadline: " + notice.last_date : "") +
                linkHtml + "</p>" +
                "</div>";
            hptuList.appendChild(item);
        });

        // View all link
        if (allHptuNotices.length > 0) {
            var viewAll = document.createElement("div");
            viewAll.className = "notice-item";
            viewAll.innerHTML =
                '<div class="notice-icon"><i class="fas fa-arrow-right" style="color:#f4b400;"></i></div>' +
                '<div class="notice-content">' +
                '<a href="https://www.himtu.ac.in/notice-board" target="_blank" rel="noopener" style="color:#0b2c6b; font-weight:700;">View all notifications on HPTU website →</a>' +
                '</div>';
            hptuList.appendChild(viewAll);
        }
    }

    // ─── Notice Filter Tabs ─────────────────────
    document.querySelectorAll(".filter-btn").forEach(function(btn) {
        btn.addEventListener("click", function() {
            document.querySelectorAll(".filter-btn").forEach(function(b) { b.classList.remove("active"); });
            this.classList.add("active");
            renderHptuNotices(this.getAttribute("data-filter"));
        });
    });

    // ─── Load Syllabus ──────────────────────────
    async function loadSyllabus() {
        var syllabusList = document.getElementById("syllabus-list");
        if (!syllabusList) return;

        try {
            var response = await fetch("/api/syllabus");
            var data = await response.json();

            syllabusList.innerHTML = "";

            if (!data || data.length === 0) {
                syllabusList.innerHTML =
                    '<div class="syllabus-item empty-placeholder">' +
                    '<i class="fas fa-book" style="font-size:32px; color:#ccc; margin-bottom:10px;"></i>' +
                    '<p style="color:#888;">Syllabus data will appear here after auto-scraping from HPTU website.</p>' +
                    '<p style="color:#aaa; font-size:12px;">Visit <a href="https://www.himtu.ac.in" target="_blank" style="color:#0b2c6b;">himtu.ac.in</a> for the latest syllabus.</p>' +
                    '</div>';
                return;
            }

            data.forEach(function(item) {
                var card = document.createElement("div");
                card.className = "syllabus-card";

                var linkHtml = "";
                if (item.link) {
                    linkHtml = '<a href="' + item.link + '" target="_blank" rel="noopener" class="syllabus-download"><i class="fas fa-download"></i> Download</a>';
                }

                card.innerHTML =
                    '<div class="syllabus-icon"><i class="fas fa-book"></i></div>' +
                    '<div class="syllabus-info">' +
                    '<h4>' + (item.title || "Syllabus") + '</h4>' +
                    '<span class="syllabus-program">' + (item.program || "General") + '</span>' +
                    linkHtml +
                    '</div>';
                syllabusList.appendChild(card);
            });
        } catch (e) {
            console.error("Failed to load syllabus:", e);
        }
    }

    // ─── Load Fees ──────────────────────────────
    async function loadFees() {
        var feesList = document.getElementById("fees-list");
        if (!feesList) return;

        try {
            var response = await fetch("/api/fees");
            var data = await response.json();

            feesList.innerHTML = "";

            if (!data || data.length === 0) {
                feesList.innerHTML =
                    '<div class="fee-item empty-placeholder">' +
                    '<i class="fas fa-rupee-sign" style="font-size:32px; color:#ccc; margin-bottom:10px;"></i>' +
                    '<p style="color:#888;">Fee structure data will appear here after auto-scraping from HPTU website.</p>' +
                    '<p style="color:#aaa; font-size:12px;">Visit <a href="https://www.himtu.ac.in" target="_blank" style="color:#0b2c6b;">himtu.ac.in</a> for current fee details.</p>' +
                    '</div>';
                return;
            }

            data.forEach(function(item) {
                var card = document.createElement("div");
                card.className = "fee-card";

                var content = "";
                if (item.description) {
                    content = '<p>' + item.description + '</p>';
                } else if (item.title) {
                    content = '<h4>' + item.title + '</h4>';
                    if (item.link) {
                        content += '<a href="' + item.link + '" target="_blank" rel="noopener" style="color:#0b2c6b; font-size:12px;"><i class="fas fa-external-link-alt"></i> View Details</a>';
                    }
                }

                card.innerHTML =
                    '<div class="fee-icon"><i class="fas fa-rupee-sign"></i></div>' +
                    '<div class="fee-info">' + content + '</div>';
                feesList.appendChild(card);
            });
        } catch (e) {
            console.error("Failed to load fees:", e);
        }
    }

    // ─── Initialize all data loads ──────────────
    loadHptuNotices();
    loadNotices();
    loadSyllabus();
    loadFees();
    loadScraperStatus();

    // Auto-refresh data every 5 minutes
    setInterval(function() {
        loadHptuNotices();
        loadScraperStatus();
    }, 300000);

    // ─── Smooth Scroll ──────────────────────────
    document.querySelectorAll('nav a[href^="#"]').forEach(function (link) {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute("href"));
            if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
            if (navContent) navContent.classList.remove("active");
        });
    });
});
