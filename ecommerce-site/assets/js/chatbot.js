// Chat widget - supports order-linked messages, quick actions, payment proof
let chatEmail = null;
let chatName = null;
let chatPollInterval = null;
let lastMessageCount = -1; // use -1 to ensure first load is always processed
let firstLoadDone = false;
let socket = null;

function ensureJoinedRoom() {
  // Ensure the user is joined to their chat room
  if (chatEmail && socket && socket.connected) {
    socket.emit('join_chat', { email: chatEmail });
  }
}

function openChatPanel() {
  const panel = document.getElementById('chat-panel');
  const input = document.getElementById('chat-input');
  if (!panel) return;

  if (panel.classList.contains('hidden')) {
    panel.classList.remove('hidden');
  }
  if (input) input.focus();

  // Join chat room if email available
  ensureJoinedRoom();

  // Load chat history initially
  loadChatHistory();

  // Start polling for new messages every 3 seconds
  if (!chatPollInterval) {
    chatPollInterval = setInterval(loadChatHistory, 3000);
  }
}

// Background poller for messages - runs even when chat is closed
// Checks every 10 seconds if user is identified but not actively polling
let backgroundMessagePollInterval = null;
function startBackgroundMessagePoll() {
  if (backgroundMessagePollInterval) return;
  backgroundMessagePollInterval = setInterval(() => {
    if (chatEmail && (!chatPollInterval || chatPollInterval === null)) {
      // User is identified but chat panel not open - quick poll for new messages
      // Only fetch if there's an active order or recent activity
      if (window._chatOrderId || (localStorage.getItem('last_order_id'))) {
        loadChatHistory();
      }
    }
  }, 10000);
}
function stopBackgroundMessagePoll() {
  if (backgroundMessagePollInterval) {
    clearInterval(backgroundMessagePollInterval);
    backgroundMessagePollInterval = null;
  }
}

function notifyAdmin(orderInfo) {
  const title = 'New order request';
  const body = `Product: ${orderInfo.product || 'N/A'}\nPrice: ${orderInfo.price || 'N/A'}\nPayment: ${orderInfo.paymentMethod || 'N/A'}\nUser: ${orderInfo.user || 'Anonymous'}`;
  console.log('[CHAT ADMIN NOTIFY]', body);

  if (window.Notification && Notification.permission === 'granted') {
    new Notification(title, { body });
  } else if (window.Notification && Notification.permission !== 'denied') {
    Notification.requestPermission().then(permission => {
      if (permission === 'granted') {
        new Notification(title, { body });
      }
    });
  }
  if (typeof showToast === 'function') showToast('🔔 Admin notification sent for new order.');
}

function botAutoReplyPlaceholder() {
  appendBotMessage('Thanks for your order 🙌\nPreparing your payment details...');
}

function sendOrderIntent(orderInfo) {
  const structured = `🛒 New Order\nProduct: ${orderInfo.product || 'Unknown'}\nPrice: ${orderInfo.price || '0.00'}\nOrder ID: ${orderInfo.orderId || 'Pending'}\nPayment Method: ${orderInfo.paymentMethod || 'Cash App'}`;
  appendUserMessage(structured);
  notifyAdmin(orderInfo);
  botAutoReplyPlaceholder();
}

function openChatForOrder(orderId, email, name, paymentMethod, productName, price) {
  chatEmail = chatEmail || email || localStorage.getItem('user_email') || 'anonymous@example.com';
  chatName = chatName || name || localStorage.getItem('user_name') || 'Guest';
  localStorage.setItem('user_email', chatEmail);
  localStorage.setItem('user_name', chatName);

  openChatPanel();

  // Ensure we're joined to the chat room for real-time messages
  ensureJoinedRoom();

  if (orderId) window._chatOrderId = orderId;
  const orderInfo = {
    product: productName || 'Items',
    price: price || '0.00',
    orderId: orderId || 'Pending',
    paymentMethod: paymentMethod || 'Cash App',
    user: `${chatName} <${chatEmail}>`
  };

  sendOrderIntent(orderInfo);
  return orderInfo;
}

window.openChatForOrder = openChatForOrder;
window.openChatPanel = openChatPanel;
window.sendOrderIntent = sendOrderIntent;
window.sendManualPaymentDetails = sendManualPaymentDetails;
window.notifyAdmin = notifyAdmin;
window.botAutoReplyPlaceholder = botAutoReplyPlaceholder;

function attachQuickChatTriggers() {
  const selectors = ['.buy-now', '.checkout-btn', '#placeOrder', '.btn.checkout', '.chat-open'];
  const buttons = document.querySelectorAll(selectors.join(','));
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      openChatPanel();
      const productEl = btn.closest('.product-card');
      const productName = btn.dataset.productName || productEl?.querySelector('h3')?.textContent || 'Product';
      const productPrice = btn.dataset.productPrice || productEl?.querySelector('.product-price')?.textContent || '0.00';
      sendOrderIntent({ product: productName, price: productPrice, paymentMethod: 'Cash App', user: chatName || 'Guest' });
    });
  });
}

function initChat() {
  const bubble = document.getElementById('chat-bubble');
  const panel = document.getElementById('chat-panel');
  const input = document.getElementById('chat-input');
  const messages = document.getElementById('chat-messages');

  if (!bubble || !panel || !input || !messages) return;

  // Initialize SocketIO connection
  if (typeof io !== 'undefined' && !socket) {
    socket = io({
      reconnectionDelay: 1000,
      reconnection: true,
      reconnectionAttempts: 10,
      transports: ['websocket', 'polling']
    });
    
    socket.on('connect', () => {
      console.log('[CHAT] Socket connected');
      // Join room if we have email
      if (chatEmail) {
        socket.emit('join_chat', { email: chatEmail });
        console.log('[CHAT] Joined room for email:', chatEmail);
      }
    });
    
    socket.on('disconnect', () => {
      console.log('[CHAT] Socket disconnected - will attempt to reconnect');
    });

    socket.on('reconnect', () => {
      console.log('[CHAT] Socket reconnected');
      if (chatEmail) {
        socket.emit('join_chat', { email: chatEmail });
        console.log('[CHAT] Re-joined room after reconnection');
      }
    });
    
    socket.on('joined', (data) => {
      console.log('[CHAT] Joined room successfully:', data);
    });
    
    socket.on('joined_admin', (data) => {
      console.log('[CHAT] Admin join confirmation:', data);
    });
    
    // Listen for new messages from admin - both 'new_message' and 'admin_reply' events
    socket.on('new_message', (data) => {
      console.log('[CHAT] New message received via new_message event:', data);
      handleAdminMessage(data);
    });

    // Also listen for admin_reply event (alternative event name)
    socket.on('admin_reply', (data) => {
      console.log('[CHAT] Admin reply received via admin_reply event:', data);
      handleAdminMessage(data);
    });

    // Handle admin messages
    function handleAdminMessage(data) {
      if (!chatEmail) return;
      
      console.log('[CHAT] Processing admin message for email:', chatEmail);
      
      // Show notification if chat is closed
      const panel = document.getElementById('chat-panel');
      if (panel && panel.classList.contains('hidden')) {
        if (typeof showToast === 'function') {
          showToast('💬 New message from admin!');
        }
        // Request notification permission if not already granted
        if ('Notification' in window && Notification.permission === 'default') {
          Notification.requestPermission();
        }
        // Show browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('Cali Clear Support', {
            body: 'You have a new message from our support team.',
            icon: '/favicon.ico'
          });
        }
      }
      
      // Force reload chat history from database to ensure we get the latest message
      // Reset lastMessageCount to force a full reload on next poll
      lastMessageCount = -1;
      // Immediately load chat history to show the message in real-time
      loadChatHistory();
    }
  } else if (typeof io === 'undefined') {
    console.warn('[CHAT] SocketIO not loaded, real-time features disabled');
  }

// Restore identity from localStorage
chatEmail = chatEmail || localStorage.getItem('user_email') || null;
chatName = chatName || localStorage.getItem('user_name') || null;

// If we have email and socket is connected/connecting, join room immediately
if (chatEmail && socket) {
  if (socket.connected) {
    socket.emit('join_chat', { email: chatEmail });
  } else {
    // Wait for connection then join
    socket.once('connect', () => {
      socket.emit('join_chat', { email: chatEmail });
    });
  }
}

// Remove any existing listeners (avoid duplicates)
bubble.replaceWith(bubble.cloneNode(true));
const newBubble = document.getElementById('chat-bubble');
  const closeButton = document.getElementById('chat-close');

  newBubble.addEventListener('click', () => {
    const isHidden = panel.classList.contains('hidden');
    panel.classList.toggle('hidden');

    if (isHidden) {
      // Opening chat
      if (!chatEmail) {
        chatEmail = prompt('Please enter your email:') || 'anonymous@example.com';
        chatName = prompt('What is your name?') || 'Guest';
        localStorage.setItem('user_email', chatEmail);
        localStorage.setItem('user_name', chatName);
      }
      // Join chat room if socket is connected
      if (socket && chatEmail) {
        socket.emit('join_chat', { email: chatEmail });
      }
      openChatPanel();
    }
  });

  if (closeButton) {
    closeButton.addEventListener('click', () => {
      panel.classList.add('hidden');
    });
  }

  input.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const text = e.target.value.trim();
    if (!text) return;

    if (!chatEmail) {
      chatEmail = prompt('Please enter your email:') || 'anonymous@example.com';
      chatName = prompt('What is your name?') || 'Guest';
      localStorage.setItem('user_email', chatEmail);
      localStorage.setItem('user_name', chatName);
      if (socket && chatEmail) {
        socket.emit('join_chat', { email: chatEmail });
      }
    }

    // Always show message immediately
    appendUserMessage(text);

    // Send to backend
    if (socket) {
      socket.emit('send_message', { email: chatEmail, name: chatName, message: text });
    } else {
      // REST API fallback
      fetch('/api/messages/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: chatEmail, name: chatName, message: text, message_type: 'text' })
      }).then(r => r.json()).then(j => {
        if (j && j.status !== 'success') console.error('[CHAT] Failed:', j.message);
      }).catch(e => console.error('[CHAT] Error sending:', e));
    }
    e.target.value = '';
  });

  // Attach quick triggers to common checkout/buy buttons
  attachQuickChatTriggers();
}

// ─── Load chat history ───
async function loadChatHistory() {
  if (!chatEmail) return;

  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  try {
    const orderId = window._chatOrderId || '';
    let url = `/api/messages/thread?email=${encodeURIComponent(chatEmail)}`;
    if (orderId) url += `&order_id=${encodeURIComponent(orderId)}`;

    const res = await fetch(url);
    const json = await res.json();

    if (json.status !== 'success') return;

    const thread = json.data || [];
    console.log('[CHAT] loadChatHistory thread length', thread.length, 'orderId', window._chatOrderId);

    // If there are no backend messages yet, show a placeholder and keep quick actions.
    if (thread.length === 0 && window._chatOrderId) {
      messages.innerHTML = `
        <div class="chat-message chat-message-user">
          <div class="chat-bubble-message">🛒 Order request sent - awaiting manual payment details from admin.</div>
          <div class="time">${formatChatTime(new Date().toISOString())}</div>
        </div>
        <div class="chat-message chat-message-bot">
          <div class="chat-bubble-message">🤖 Thanks for your order! Admin will post bank/payment instructions here shortly.</div>
          <div class="time">${formatChatTime(new Date().toISOString())}</div>
        </div>
        <div class="chat-message chat-message-status">
          <div class="chat-bubble-message">⏳ Status: Pending payment instructions</div>
          <div class="time">${formatChatTime(new Date().toISOString())}</div>
        </div>
      `;

      const activeOrder = window._chatOrderId;
      if (activeOrder && !document.getElementById(`quick-actions-chat-${activeOrder}`)) {
        messages.innerHTML += renderQuickActions(activeOrder);
      }
      messages.scrollTop = messages.scrollHeight;
      firstLoadDone = true;
      lastMessageCount = 0;
      return;
    }

    if (thread.length === lastMessageCount && firstLoadDone) {
      return; // No new messages after initial load
    }
    firstLoadDone = true;
    lastMessageCount = thread.length;

    let html = '';
    thread.forEach(msg => {
      const isBot = msg.customer_name === 'Bot' || msg.message_type === 'bot' || msg.message_type === 'payment_details' || msg.message_type === 'status_update';
      const isAdmin = msg.admin_reply;

      if (isBot) {
        html += renderBotMessage(msg);
      } else {
        html += renderUserMessage(msg);
      }

      if (isAdmin && !isBot) {
        html += renderAdminReply(msg);
      }
    });

    // Check if there's an active order and add quick actions
    const activeOrder = findActiveOrder(thread);
    if (activeOrder && !document.getElementById(`quick-actions-chat-${activeOrder}`)) {
      html += renderQuickActions(activeOrder);
    }

    messages.innerHTML = html;
    messages.scrollTop = messages.scrollHeight;
  } catch (err) {
    console.error('Error loading chat history:', err);
  }
}

// ─── Render functions ───
function renderUserMessage(msg) {
  const text = escapeHtml(msg.message);
  const time = formatChatTime(msg.created_at);

  // Special styling for order messages
  if (msg.message_type === 'order') {
    return `<div class="chat-message chat-message-user">
      <div class="chat-bubble-message">${text}</div>
      <div class="time">${time}</div>
    </div>`;
  }

  // Proof messages
  if (msg.message_type === 'proof') {
    let proofContent = text;
    if (msg.has_screenshot) {
      proofContent += '<br><span style="font-size:11px;color:#ffcc80;">📸 Screenshot attached</span>';
    }
    return `<div class="chat-message chat-message-user">
      <div class="chat-bubble-message" style="background:#e65100;">${proofContent}</div>
      <div class="time">${time}</div>
    </div>`;
  }

  // Quick action messages
  if (msg.message_type === 'quick_action') {
    return `<div class="chat-message chat-message-user">
      <div class="chat-bubble-message">${text}</div>
      <div class="time">${time}</div>
    </div>`;
  }

  // Regular user messages
  return `<div class="chat-message chat-message-user">
    <div class="chat-bubble-message">${text}</div>
    <div class="time">${time}</div>
  </div>`;
}

function renderBotMessage(msg) {
  const text = escapeHtml(msg.message).replace(/\n/g, '<br>');
  const time = formatChatTime(msg.replied_at || msg.created_at);
  const type = msg.message_type;

  let bg = '#333';
  let color = '#ddd';
  let border = 'none';
  let icon = '';

  if (type === 'payment_details') {
    bg = '#1a237e';
    color = '#e8eaf6';
    border = '1px solid #3949ab';
    icon = '💳 ';
  } else if (type === 'status_update') {
    bg = '#1b5e20';
    color = '#c8e6c9';
    border = '1px solid #388e3c';
    icon = '🔔 ';
  } else if (type === 'bot') {
    bg = '#2a2a2a';
    color = '#ccc';
    icon = '🤖 ';
  }

  const wrapperClass = `chat-message ${type === 'status_update' ? 'chat-message-status' : 'chat-message-bot'}`;
  return `<div class="${wrapperClass}">
    <div class="chat-bubble-message" style="background:${bg};color:${color};border:${border};">${icon}${text}</div>
    <div class="time">${time}</div>
  </div>`;
}

function renderAdminReply(msg) {
  const text = escapeHtml(msg.admin_reply);
  const time = formatChatTime(msg.replied_at);
  return `<div class="chat-message chat-message-admin" style="text-align:right;margin:8px 0;">
    <div style="background:#4caf50;color:#fff;padding:10px 14px;border-radius:12px 12px 0 12px;display:inline-block;max-width:75%;word-wrap:break-word;font-size:13px;text-align:left;">
      <span style="font-size:11px;color:rgba(255,255,255,0.7);display:block;margin-bottom:4px;">🧑‍💼 Admin</span>
      ${text}
    </div>
    <div style="font-size:11px;color:#666;margin-top:3px;text-align:right;">${time}</div>
  </div>`;
}

function renderQuickActions(orderId) {
  return `<div id="quick-actions-chat-${orderId}" style="
    display:flex;flex-wrap:wrap;gap:6px;margin:12px 0;padding:12px;
    background:#2a2a2a;border-radius:10px;justify-content:center;
  ">
    <button onclick="chatQuickAction('i_have_paid','${orderId}')" style="
      background:#4caf50;color:#fff;border:none;padding:7px 12px;
      border-radius:20px;cursor:pointer;font-size:12px;font-family:Poppins;
    ">💰 I Have Paid</button>
    <button onclick="chatQuickAction('track_order','${orderId}')" style="
      background:#2196f3;color:#fff;border:none;padding:7px 12px;
      border-radius:20px;cursor:pointer;font-size:12px;font-family:Poppins;
    ">📦 Track</button>
    <button onclick="chatQuickAction('cancel_order','${orderId}')" style="
      background:#f44336;color:#fff;border:none;padding:7px 12px;
      border-radius:20px;cursor:pointer;font-size:12px;font-family:Poppins;
    ">❌ Cancel</button>
    <button onclick="chatQuickAction('talk_to_agent','${orderId}')" style="
      background:#9c27b0;color:#fff;border:none;padding:7px 12px;
      border-radius:20px;cursor:pointer;font-size:12px;font-family:Poppins;
    ">🧑‍💼 Agent</button>
  </div>`;
}

// ─── Quick actions from chat ───
async function chatQuickAction(action, orderId) {
  if (!chatEmail) return;

  try {
    const r = await fetch('/api/messages/quick-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: chatEmail,
        name: chatName || 'Guest',
        action,
        order_id: orderId
      })
    });
    const d = await r.json();
    lastMessageCount = 0; // Force refresh
    await loadChatHistory();

    if (action === 'i_have_paid') {
      setTimeout(() => showProofForm(orderId), 400);
    }
  } catch (e) {
    console.error('Quick action error:', e);
  }
}

function sendManualPaymentDetails(orderId, details) {
  const text = details || prompt('Enter payment details (bank/Venmo/Cash App/PayPal):');
  if (!text || !chatEmail) return;

  const message = `💳 Payment Details:\n${text}\nSend proof after payment ✅`;

  appendUserMessage(message);
  loadChatHistory();

  // Optional backend send: if endpoint exists
  fetch('/api/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: chatEmail,
      name: chatName || 'Guest',
      order_id: orderId || window._chatOrderId || null,
      message,
      message_type: 'payment_details'
    })
  }).catch(err => console.error('sendManualPaymentDetails error:', err));

  if (typeof showToast === 'function') showToast('Manual payment details sent to customer');
}

window.sendManualPaymentDetails = sendManualPaymentDetails;

// ─── Proof upload form ───
function showProofForm(orderId) {
  const messages = document.getElementById('chat-messages');
  if (!messages || document.getElementById(`proof-form-${orderId}`)) return;

  const html = `
    <div id="proof-form-${orderId}" style="
      background:#1a1a2e;padding:16px;border-radius:10px;margin:10px 0;
      border:1px solid #333;
    ">
      <div style="font-weight:600;margin-bottom:12px;color:#ff6f61;font-size:14px;">📄 Upload Payment Proof</div>
      <input type="text" id="proof-txn-${orderId}" placeholder="Transaction ID" style="
        width:100%;padding:10px;background:#2a2a2a;border:1px solid #444;border-radius:6px;
        color:#fff;font-size:13px;margin:0 0 8px;box-sizing:border-box;font-family:Poppins;
      ">
      <input type="file" id="proof-file-${orderId}" accept="image/*" style="
        width:100%;padding:8px;background:#2a2a2a;border:1px solid #444;border-radius:6px;
        color:#fff;font-size:12px;margin:0 0 8px;box-sizing:border-box;font-family:Poppins;
      ">
      <input type="text" id="proof-note-${orderId}" placeholder="Note (optional)" style="
        width:100%;padding:10px;background:#2a2a2a;border:1px solid #444;border-radius:6px;
        color:#fff;font-size:13px;margin:0 0 10px;box-sizing:border-box;font-family:Poppins;
      ">
      <button onclick="chatSubmitProof('${orderId}')" style="
        background:#ff6f61;color:#fff;border:none;padding:10px;
        border-radius:8px;cursor:pointer;font-size:14px;font-family:Poppins;
        font-weight:600;width:100%;
      ">Submit Proof</button>
    </div>
  `;

  messages.innerHTML += html;
  messages.scrollTop = messages.scrollHeight;
}

async function chatSubmitProof(orderId) {
  const txnId = document.getElementById(`proof-txn-${orderId}`)?.value || '';
  const note = document.getElementById(`proof-note-${orderId}`)?.value || '';
  const fileInput = document.getElementById(`proof-file-${orderId}`);

  let screenshotBase64 = '';
  if (fileInput && fileInput.files[0]) {
    screenshotBase64 = await new Promise(resolve => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(fileInput.files[0]);
    });
  }

  try {
    const r = await fetch('/api/messages/proof', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: chatEmail,
        name: chatName || 'Guest',
        order_id: orderId,
        transaction_id: txnId,
        screenshot: screenshotBase64,
        note
      })
    });

    if (r.ok) {
      const form = document.getElementById(`proof-form-${orderId}`);
      if (form) form.remove();
      lastMessageCount = 0;
      await loadChatHistory();
    }
  } catch (e) {
    console.error('Proof upload error:', e);
  }
}

// ─── Helpers ───
function findActiveOrder(thread) {
  // Find the most recent order ID from order-type messages
  for (let i = thread.length - 1; i >= 0; i--) {
    if (thread[i].order_id && thread[i].message_type === 'order') {
      return thread[i].order_id;
    }
  }
  // Fallback to localStorage
  return localStorage.getItem('last_order_id') || null;
}

function appendUserMessage(text) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;
  messages.insertAdjacentHTML('beforeend', `
    <div class="chat-message chat-message-user">
      <div class="chat-bubble-message">${escapeHtml(text)}</div>
      <div class="time">${formatChatTime(new Date().toISOString())}</div>
    </div>`);
  messages.scrollTop = messages.scrollHeight;
}

function appendBotMessage(text) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;
  messages.insertAdjacentHTML('beforeend', `
    <div class="chat-message chat-message-bot">
      <div class="chat-bubble-message">🤖 ${escapeHtml(text)}</div>
      <div class="time">${formatChatTime(new Date().toISOString())}</div>
    </div>`);
  messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function formatChatTime(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const hours = String(date.getHours()).padStart(2, '0');
  const mins = String(date.getMinutes()).padStart(2, '0');
  return `${hours}:${mins}`;
}

// Expose globally
window.chatQuickAction = chatQuickAction;
window.chatSubmitProof = chatSubmitProof;
window.loadChatHistory = loadChatHistory;

// Initialize - only once via DOMContentLoaded
document.addEventListener('DOMContentLoaded', initChat);

// Start background polling for message updates (catches any missed real-time messages)
startBackgroundMessagePoll();
