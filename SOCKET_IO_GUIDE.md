# Socket.IO & Real-Time Communication Guide

## 🔌 Socket Events Reference

### Emitted BY Customer → TO Admin

#### 1. User Typing
```javascript
socket.emit('typing', {
  email: 'customer@example.com',
  is_typing: true
})

// After 3 seconds: auto-sends
socket.emit('typing', {
  email: 'customer@example.com',
  is_typing: false
})
```

#### 2. Join Chat Room
```javascript
socket.emit('join_chat', {
  email: 'customer@example.com'
})
```

#### 3. Send Message
```javascript
socket.emit('send_message', {
  email: 'customer@example.com',
  name: 'John Doe',
  message: 'Hello admin',
  message_type: 'text'
})
```

---

### Emitted BY Admin → TO Customer

#### 1. New Message
```javascript
socket.emit('new_message', {
  id: 123,
  email: 'customer@example.com',
  admin_reply: 'Hello! How can I help?',
  message_type: 'text'
})
```

#### 2. Admin Status Changed
```javascript
socket.emit('admin_online_status', {
  is_online: true,
  admin_email: 'admin@cali-clear.com'
})
```

#### 3. Message Edited
```javascript
socket.emit('message_edited', {
  message_id: 123,
  new_text: 'Updated message text',
  edited_at: '2024-01-01T12:00:00'
})
```

#### 4. Typing Indicator
```javascript
socket.emit('user_typing', {
  email: 'customer@example.com',
  is_typing: true
})
```

#### 5. Message Sent Confirmation
```javascript
socket.emit('message_sent', {
  message_id: 123,
  status: 'delivered'
})
```

---

## 🎧 Socket Listeners (Customer Side)

```javascript
// Listen for new messages from admin
socket.on('new_message', (data) => {
  console.log('New message:', data);
  handleAdminMessage(data);
});

// Listen for admin replies
socket.on('admin_reply', (data) => {
  console.log('Admin replied:', data);
  handleAdminMessage(data);
});

// Listen for typing indicator
socket.on('user_typing', (data) => {
  if (data.is_typing) {
    showTypingIndicator();
  } else {
    hideTypingIndicator();
  }
});

// Listen for admin online status
socket.on('admin_online_status', (data) => {
  updateAdminStatusBadge(data.is_online);
});

// Listen for edited messages
socket.on('message_edited', (data) => {
  updateMessageInUI(data.message_id, data.new_text);
});

// Listen for message confirmation
socket.on('message_sent', (data) => {
  markMessageAsDelivered(data.message_id);
});

// Listen for joined notification
socket.on('joined', (data) => {
  console.log('Joined chat room:', data);
});

// Listen for joined_admin notification
socket.on('joined_admin', (data) => {
  console.log('Admin joined:', data);
});
```

---

## 🎧 Socket Listeners (Admin Side)

```javascript
// Listen for new customer messages
adminSocket.on('new_message', (data) => {
  addToConversationList(data.email, data);
  updateConversationPreview(data);
});

// Listen for customer typing
adminSocket.on('user_typing', (data) => {
  if (data.email === currentConversationEmail) {
    showTypingIndicator();
  }
});

// Listen for message reactions
adminSocket.on('reactions_updated', (data) => {
  updateReactionDisplay(data.message_id, data.reactions);
});

// Listen for message deleted
adminSocket.on('message_deleted', (data) => {
  removeMessageFromUI(data.message_id);
});

// Listen for message archived
adminSocket.on('message_archived', (data) => {
  updateMessageStatus(data.message_id, 'archived');
});
```

---

## 📊 Message Flow Diagrams

### Scenario 1: Customer Sends Message

```
Customer Types Message
        ↓
[ Socket.emit('typing') ]
        ↓
Admin Receives 'user_typing' ← Shows "typing..."
        ↓
Customer Sends Message
        ↓
[ socket.emit('send_message') ]
        ↓
Backend: save to DB + emit 'message_sent'
        ↓
[ socket.emit('new_message', {admin_reply}) ]
        ↓
Admin Receives 'new_message' ← Shows in chat
Customer Receives 'message_sent' ← Removes "Sending..."
        ↓
SUCCESS ✅
```

### Scenario 2: Admin Replies

```
Admin Types Reply
        ↓
[ PUT /api/messages/:id ]
        ↓
Backend: save reply + emit 'admin_reply'
        ↓
[ socket.emit('admin_reply', {message}) ]
        ↓
Customer Receives 'admin_reply' ← Shows reply
        ↓
Backend: sets reply_at timestamp
        ↓
SUCCESS ✅
```

### Scenario 3: Message Reaction

```
Customer Clicks Emoji
        ↓
[ POST /api/messages/:id/reaction ]
        ↓
Backend: save reaction + emit 'reactions_updated'
        ↓
[ socket.emit('reactions_updated', {reactions}) ]
        ↓
Admin Receives → Updates reaction count
Customer Receives → Shows reaction
        ↓
SUCCESS ✅
```

### Scenario 4: Admin Status Change

```
Admin Clicks Status Button
        ↓
toggleAdminStatus() called
        ↓
[ socket.emit('admin_status_changed', {is_online}) ]
        ↓
Backend: update AdminStatus table
        ↓
[ socket.emit('admin_online_status', {is_online}) ]
        ↓
ALL Customers Receive → Badge updates
        ↓
SUCCESS ✅
```

---

## 🔄 Real-Time Sync Flow

### Complete Message Lifecycle

```
1. CUSTOMER CREATES
   User types message
   → Optimistic UI: message appears immediately
   → Socket.emit('send_message')

2. BACKEND RECEIVES
   → Validates message
   → Saves to database
   → Emits 'message_sent' + 'new_message'

3. CUSTOMER CONFIRMS
   Receives 'message_sent'
   → Changes status from "Sending..." to "✓"

4. ADMIN NOTIFIES
   Receives 'new_message'
   → Shows in conversation list
   → Desktop notification (if allowed)
   → Sound alert (if enabled)

5. ADMIN READS
   Admin opens message
   → Backend: sets is_read=true
   → Emits 'message_read' event

6. CUSTOMER SEES
   Receives 'message_read'
   → Shows "✓✓ Read" with timestamp

7. ADMIN REACTS
   Admin clicks emoji
   → POST /api/messages/:id/reaction
   → Backend emits 'reactions_updated'

8. CUSTOMER SEES
   Receives 'reactions_updated'
   → Shows emoji count

9. ADMIN REPLIES
   Admin sends reply
   → PUT /api/messages/:id
   → Backend emits 'admin_reply'

10. CUSTOMER GETS
    Receives 'admin_reply'
    → Shows in chat
    → Notification alert
    → Message count updates
```

---

## ⚙️ Socket Connection Setup

### Customer Side
```javascript
// Connect to Socket.IO
socket = io('http://localhost:5000', {
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: 5,
  transports: ['websocket', 'polling']
});

// On connect
socket.on('connect', () => {
  console.log('✅ Socket connected:', socket.id);
  
  // Join chat room
  socket.emit('join_chat', { email: chatEmail });
});

// On disconnect
socket.on('disconnect', () => {
  console.log('❌ Socket disconnected');
  // Polling fallback activates automatically
});

// On error
socket.on('error', (error) => {
  console.error('Socket error:', error);
  // Polling fallback activates automatically
});
```

### Admin Side
```javascript
// Connect to Socket.IO
let adminSocket = io('http://localhost:5000', {
  auth: {
    token: adminJWT
  },
  reconnection: true,
  transports: ['websocket', 'polling']
});

// On connect
adminSocket.on('connect', () => {
  console.log('✅ Admin socket connected:', adminSocket.id);
  
  // Join admin room
  adminSocket.emit('join_admin', { 
    email: 'admin@cali-clear.com' 
  });
  
  // Update admin status
  adminSocket.emit('admin_status', { is_online: true });
});

// Listen for new messages
adminSocket.on('new_message', (data) => {
  console.log('📨 New message from:', data.email);
});
```

---

## 🔄 Fallback Polling System

### When Socket.IO Fails

```javascript
// Active Polling (Chat Open)
setInterval(() => {
  fetch('/api/messages/thread')
    .then(r => r.json())
    .then(data => {
      if (data.length > lastMessageCount) {
        // New messages found
        loadChatHistory();
      }
    });
}, 2000); // Every 2 seconds

// Background Polling (Chat Closed)
setInterval(() => {
  if (chatEmail && !chatPollInterval) {
    fetch('/api/messages/thread')
      .then(r => r.json())
      .then(data => {
        if (data.length > lastMessageCount) {
          // New messages - show notification
          showNotification('New message');
        }
      });
  }
}, 5000); // Every 5 seconds
```

---

## 🛡️ Security in Socket Events

### Authentication
```javascript
// Each socket event should verify user
@socketio.on('send_message')
def handle_message(data):
    email = data.get('email')
    
    # Verify email matches session
    if not verify_user_email(email):
        return {'status': 'error', 'message': 'Unauthorized'}
    
    # Process message
    return save_message(email, data['message'])
```

### Rate Limiting
```javascript
// Prevent spam
const messageRateLimit = {};

socket.on('send_message', (data) => {
    const email = data.email;
    const now = Date.now();
    
    if (messageRateLimit[email] && 
        now - messageRateLimit[email] < 1000) {
        // Too fast - ignore
        return;
    }
    
    messageRateLimit[email] = now;
    // Process message
});
```

---

## 📊 Event Statistics

### Typical Chat Session

```
User opens chat
  ↓
1-2 Socket connections
↓
Sends 5-10 messages
  ↓
20-30 events per message:
  • typing (1-3 events)
  • send_message (1 event)
  • message_sent (1 event)
  • new_message (if admin replies)
  • message_edited (if edited)
  • reaction (if reacted)
  • admin_online_status (1 per status change)

Total: 50-100 events per typical conversation
```

---

## 🔍 Debugging Socket Events

### Enable Debug Mode
```javascript
// Browser console
localStorage.debug = '*';

// Or in code
socket.on('*', (event, ...args) => {
  console.log('[SOCKET]', event, args);
});
```

### Monitor All Events
```bash
# Terminal - watch socket logs
tail -f /var/log/flask/socket.log
```

### Test Socket Manually
```javascript
// Browser console
socket.emit('send_message', {
  email: 'test@example.com',
  message: 'Test message'
});

// Listen for response
socket.on('message_sent', (data) => {
  console.log('✅ Message sent:', data);
});
```

---

## 🚀 Production Considerations

### Scalability
- Use Redis for Socket.IO scaling across multiple servers
- Implement message queuing (RabbitMQ, Redis)
- Load balance Socket.IO connections

### Reliability
- Enable Socket.IO persistence
- Implement reconnection logic
- Monitor connection health

### Performance
- Limit events per second
- Batch multiple updates
- Use compression for large messages

### Security
- Validate all socket data
- Implement JWT authentication
- Use TLS/SSL for socket connections
- Rate limit per IP/user

---

**Socket.IO provides real-time communication. REST API provides fallback. Together they ensure 100% message delivery!**
