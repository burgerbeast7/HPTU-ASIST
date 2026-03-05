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

    // Hero button opens chat
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

        // Show PDF indicator
        pdfNameSpan.textContent = file.name;
        pdfIndicator.classList.remove("hidden");
        if (clearPdfBtn) clearPdfBtn.classList.remove("hidden");

        const formData = new FormData();
        formData.append("pdf", file);

        addBotMessage("⏳ Uploading and processing your PDF...");

        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData,
            });

            const result = await response.json();
            if (response.ok) {
                addBotMessage("✅ " + result.message + "\n\nYou can now ask questions about this document!");
            } else {
                addBotMessage("❌ " + (result.error || "Failed to upload PDF."));
                hidePdfIndicator();
            }
        } catch (error) {
            console.error("Upload error:", error);
            addBotMessage("❌ Could not upload the PDF. Please check your connection and try again.");
            hidePdfIndicator();
        }
    });

    // Remove PDF
    if (removePdfButton) {
        removePdfButton.addEventListener("click", clearPdfContext);
    }
    if (clearPdfBtn) {
        clearPdfBtn.addEventListener("click", clearPdfContext);
    }

    async function clearPdfContext() {
        try {
            await fetch("/clear-pdf", { method: "POST" });
        } catch (e) {
            console.error("Clear PDF error:", e);
        }
        hidePdfIndicator();
        pdfFileInput.value = "";
        addBotMessage("📄 PDF context has been cleared. I'll now answer from general HPTU knowledge.");
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

        // Show typing indicator
        const typingEl = showTypingIndicator();
        chatStatus.textContent = "● Typing...";
        chatStatus.style.color = "#f4b400";

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMessage })
            });

            const data = await response.json();

            // Remove typing indicator
            removeTypingIndicator(typingEl);
            chatStatus.textContent = "● Online";
            chatStatus.style.color = "#6fcf97";

            addBotMessage(data.reply);

        } catch (error) {
            console.error("Chat error:", error);
            removeTypingIndicator(typingEl);
            chatStatus.textContent = "● Online";
            chatStatus.style.color = "#6fcf97";
            addBotMessage("❌ Sorry, I couldn't connect to the server. Please check your internet connection and try again.");
        }

        isSending = false;
    }

    sendMessageButton.addEventListener("click", sendMessage);

    // Enter key to send
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

    function addBotMessage(message) {
        const wrapper = document.createElement("div");
        wrapper.className = "bot-message";

        const avatar = document.createElement("div");
        avatar.className = "msg-avatar";
        avatar.innerHTML = '<i class="fas fa-robot"></i>';

        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";
        // Support basic formatting: line breaks
        bubble.innerHTML = message.replace(/\n/g, "<br>");

        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
        chatBody.appendChild(wrapper);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function showTypingIndicator() {
        const wrapper = document.createElement("div");
        wrapper.className = "typing-indicator";
        wrapper.id = "typing-indicator";

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
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
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
    async function loadHptuNotices() {
        var hptuList = document.getElementById("hptu-notices-list");
        if (!hptuList) return;

        try {
            var response = await fetch("/api/hptu-notices");
            var data = await response.json();

            hptuList.innerHTML = "";

            if (!data || data.length === 0) {
                hptuList.innerHTML =
                    '<div class="notice-item">' +
                    '<div class="notice-icon"><i class="fas fa-info-circle"></i></div>' +
                    '<div class="notice-content"><strong>No HPTU notices available. Check back later.</strong></div>' +
                    '</div>';
                return;
            }

            // Show up to 10 latest notices
            var shown = data.slice(0, 10);
            shown.forEach(function (notice) {
                var item = document.createElement("div");
                item.className = "notice-item";

                var linkHtml = "";
                if (notice.link) {
                    linkHtml = ' <a href="' + notice.link + '" target="_blank" rel="noopener" style="color:#0b2c6b; font-weight:600; font-size:12px;"><i class="fas fa-external-link-alt"></i> View PDF</a>';
                }

                item.innerHTML =
                    '<div class="notice-icon"><i class="fas fa-globe" style="color:#0b2c6b;"></i></div>' +
                    '<div class="notice-content">' +
                    "<strong>" + (notice.title || "Notification") + "</strong>" +
                    "<p>" + (notice.date || "") +
                    (notice.last_date ? " | Deadline: " + notice.last_date : "") +
                    linkHtml + "</p>" +
                    "</div>";
                hptuList.appendChild(item);
            });

            // Add "View All" link
            if (data.length > 10) {
                var viewAll = document.createElement("div");
                viewAll.className = "notice-item";
                viewAll.innerHTML =
                    '<div class="notice-icon"><i class="fas fa-arrow-right" style="color:#f4b400;"></i></div>' +
                    '<div class="notice-content">' +
                    '<a href="https://www.himtu.ac.in/notice-board" target="_blank" rel="noopener" style="color:#0b2c6b; font-weight:700;">View all ' + data.length + ' notifications on HPTU website →</a>' +
                    '</div>';
                hptuList.appendChild(viewAll);
            }
        } catch (e) {
            console.error("Failed to load HPTU notices:", e);
            hptuList.innerHTML =
                '<div class="notice-item">' +
                '<div class="notice-icon"><i class="fas fa-exclamation-triangle" style="color:#c0392b;"></i></div>' +
                '<div class="notice-content"><strong>Could not load HPTU notices.</strong><p>Please check back later.</p></div>' +
                '</div>';
        }
    }

    loadHptuNotices();
    loadNotices();

    // ─── Smooth Scroll for Nav Links ────────────
    document.querySelectorAll('nav a[href^="#"]').forEach(function (link) {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute("href"));
            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
            // Close mobile nav
            if (navContent) navContent.classList.remove("active");
        });
    });
});
