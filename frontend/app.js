/* ==========================================================================
   E-Commerce Customer Support - Frontend Application Logic
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatMessages = document.getElementById("chat-messages");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const clearChatBtn = document.getElementById("clear-chat-btn");
  const typingIndicator = document.getElementById("typing-indicator");
  const headerNewChatBtn = document.getElementById("header-new-chat-btn");
  const sidebarNewChatBtn = document.getElementById("sidebar-new-chat-btn");

  // State
  let isProcessing = false;

  // Format Timestamp HH:MM AM/PM
  function getCurrentTimestamp() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // Auto-resize textarea
  function adjustTextareaHeight() {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 120) + "px";
  }

  // Update send button state
  function updateSendButtonState() {
    const text = userInput.value.strip ? userInput.value.trim() : userInput.value;
    sendBtn.disabled = !text || isProcessing;
  }

  // Scroll to bottom
  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Remove welcome banner if visible
  function removeWelcomeBanner() {
    const banner = document.querySelector(".welcome-banner");
    if (banner) {
      banner.style.display = "none";
    }
  }

  // Determine Agent Badge Name
  function getAgentBadge(intent) {
    if (["order_tracking", "order_status", "order_details"].includes(intent)) {
      return "Order Agent";
    } else if (intent === "policy_inquiry") {
      return "Policy Agent";
    } else if (intent === "customer_complaint") {
      return "Complaint Agent";
    }
    return "Support Agent";
  }

  // Render User or Agent Message Bubble
  function appendMessage(role, text, metadata = {}) {
    removeWelcomeBanner();

    const row = document.createElement("div");
    row.className = `message-row ${role === "user" ? "message-user" : "message-agent"}`;

    const avatar = document.createElement("div");
    avatar.className = `avatar ${role === "user" ? "avatar-user" : "avatar-agent"}`;
    avatar.textContent = role === "user" ? "👤" : "🤖";

    const content = document.createElement("div");
    content.className = "message-content";

    // Header (Badge + Timestamp)
    const header = document.createElement("div");
    header.className = "message-header";

    if (role === "agent") {
      const badge = document.createElement("span");
      badge.className = "agent-badge";
      badge.textContent = getAgentBadge(metadata.intent);
      header.appendChild(badge);
    }

    const time = document.createElement("span");
    time.className = "timestamp";
    time.textContent = getCurrentTimestamp();
    header.appendChild(time);

    content.appendChild(header);

    // Text Bubble
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    content.appendChild(bubble);

    // Structured Cards (Order Table, Policy Section, Handoff Ticket)
    if (role === "agent") {
      // 1. Policy Section Badge
      if (metadata.policy_section) {
        const policyBadge = document.createElement("div");
        policyBadge.className = "handoff-badge";
        policyBadge.style.backgroundColor = "#e0e7ff";
        policyBadge.style.color = "#3730a3";
        policyBadge.innerHTML = `📜 Section: ${metadata.policy_section}`;
        content.appendChild(policyBadge);
      }

      // 2. Human Handoff Escalation Card
      if (metadata.handoff_summary) {
        const handoffCard = document.createElement("div");
        handoffCard.className = "handoff-card";

        const badge = document.createElement("div");
        badge.className = "handoff-badge";
        badge.innerHTML = `⚠️ Escalation Status: Pending Human Agent Review`;
        handoffCard.appendChild(badge);

        const summaryPre = document.createElement("pre");
        summaryPre.style.whiteSpace = "pre-wrap";
        summaryPre.style.fontFamily = "inherit";
        summaryPre.style.fontSize = "12px";
        summaryPre.style.color = "#92400e";
        summaryPre.textContent = metadata.handoff_summary;
        handoffCard.appendChild(summaryPre);

        content.appendChild(handoffCard);
      }

      // 3. Formatted Order Summary Card
      if (metadata.formatted_details) {
        const orderCard = document.createElement("div");
        orderCard.className = "order-card";

        const cardHeader = document.createElement("div");
        cardHeader.className = "order-card-header";

        const title = document.createElement("span");
        title.className = "order-card-title";
        title.textContent = metadata.order_id ? `Order Details: ${metadata.order_id}` : "Order Summary";
        cardHeader.appendChild(title);

        orderCard.appendChild(cardHeader);

        const detailsPre = document.createElement("pre");
        detailsPre.style.whiteSpace = "pre-wrap";
        detailsPre.style.fontFamily = "monospace";
        detailsPre.style.fontSize = "12px";
        detailsPre.style.color = "#0f172a";
        detailsPre.textContent = metadata.formatted_details;
        orderCard.appendChild(detailsPre);

        content.appendChild(orderCard);
      }
    }

    row.appendChild(avatar);
    row.appendChild(content);

    chatMessages.appendChild(row);
    scrollToBottom();
  }

  // Show / Hide Typing Indicator
  function setTyping(show) {
    if (show) {
      typingIndicator.classList.remove("hidden");
    } else {
      typingIndicator.classList.add("hidden");
    }
    scrollToBottom();
  }

  // Send Customer Message to Backend API
  async function handleSendMessage(customText = null) {
    const text = customText ? customText.trim() : userInput.value.trim();
    if (!text || isProcessing) return;

    isProcessing = true;
    updateSendButtonState();

    if (!customText) {
      userInput.value = "";
      adjustTextareaHeight();
    }

    // Append User Message
    appendMessage("user", text);

    // Show Typing Indicator
    setTyping(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      setTyping(false);

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();

      // Append Agent Response
      appendMessage("agent", data.agent_response || "I have received your message.", {
        intent: data.intent,
        order_id: data.order_id,
        formatted_details: data.formatted_details,
        policy_section: data.policy_section,
        handoff_summary: data.handoff_summary,
        escalation_details: data.escalation_details,
      });

    } catch (error) {
      setTyping(false);
      console.error("API Error:", error);
      appendMessage(
        "agent",
        "I'm sorry, I'm currently unable to connect to the backend server. Please check your network connection or make sure the backend server is running.",
        { intent: "unknown" }
      );
    } finally {
      isProcessing = false;
      updateSendButtonState();
      userInput.focus();
    }
  }

  // Clear Conversation
  function clearChat() {
    chatMessages.innerHTML = `
      <div class="welcome-banner">
        <div class="welcome-icon">💬</div>
        <h2>Welcome to E-Commerce Support</h2>
        <p>How can I assist you today? Ask about your order status, store policies, or log a complaint for human support review.</p>
        <div class="sample-queries">
          <button class="chip-query" data-query="Where is my order ORD-1001?">Where is my order ORD-1001?</button>
          <button class="chip-query" data-query="What is your return policy?">What is your return policy?</button>
          <button class="chip-query" data-query="My order ORD-1005 is delayed">Order ORD-1005 status</button>
        </div>
      </div>
    `;
    bindChipButtons();
  }

  // Bind Quick Action & Chip Query Buttons
  function bindChipButtons() {
    document.querySelectorAll("[data-query]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const query = btn.getAttribute("data-query");
        if (query) {
          handleSendMessage(query);
        }
      });
    });
  }

  // Event Listeners
  userInput.addEventListener("input", () => {
    adjustTextareaHeight();
    updateSendButtonState();
  });

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  sendBtn.addEventListener("click", () => handleSendMessage());
  clearChatBtn.addEventListener("click", clearChat);
  headerNewChatBtn.addEventListener("click", clearChat);
  sidebarNewChatBtn.addEventListener("click", clearChat);

  // Initial setup
  bindChipButtons();
  userInput.focus();
});
