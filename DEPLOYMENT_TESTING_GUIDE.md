# Deployment & Testing Guide - 15 Chat Features

## ✅ Pre-Deployment Checklist

### 1. Database Setup
- [ ] Run migrations to create new Message fields
- [ ] Create MessageAttachment table
- [ ] Create AdminStatus table  
- [ ] Create FAQItem table
- [ ] Create MessageSearchIndex table
- [ ] Verify all tables created: `python -c "from backend.database.db import db; db.create_all()"`

### 2. Backend Verification
- [ ] Backend routes updated in `message_routes.py`
- [ ] Socket handlers added in `app.py`
- [ ] Models extended in `models.py`
- [ ] All imports present (datetime, etc.)
- [ ] No syntax errors: `python -m py_compile backend/app.py`

### 3. Frontend Verification
- [ ] `chatbot.js` has all 15 feature functions
- [ ] Socket listeners for new events
- [ ] HTML elements in `footer.html` (typing indicator, status)
- [ ] Admin dashboard has feature buttons in `admin.html`

### 4. Environment Configuration
- [ ] File upload directory exists: `/uploads/messages/`
- [ ] Directory permissions set: `chmod 755 /uploads/messages/`
- [ ] Flask-SocketIO configured with CORS
- [ ] Socket.IO CDN accessible or local copy available

### 5. Testing Setup
- [ ] Test admin account created
- [ ] Test customer account created
- [ ] Backend running on localhost:5000
- [ ] Frontend running on localhost:8000 (or your port)

---

## 🚀 Deployment Steps

### Step 1: Database Migration

```bash
cd backend

# Create migration script
python -c "
from database.db import db
from app import app
with app.app_context():
    db.create_all()
    print('✅ All tables created')
"

# Verify tables
python -c "
import sqlite3
conn = sqlite3.connect('instance/cali_clear.db')
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
tables = cursor.fetchall()
for table in tables:
    print(f'  ✅ {table[0]}')
"
```

### Step 2: Backend Startup

```bash
cd backend

# Install dependencies (if needed)
pip install flask flask-socketio python-socketio python-engineio

# Start Flask app
python app.py

# Expected output:
# * Running on http://127.0.0.1:5000
# * Socket.IO server started
```

### Step 3: Test Socket Connection

```bash
# In browser console
curl -i http://localhost:5000/socket.io/?EIO=4&transport=websocket
# Should return 101 Switching Protocols
```

### Step 4: Admin Dashboard Test

```bash
# Navigate to admin page
http://localhost:8000/admin.html

# Log in with test account
# Check console for Socket connection
# Try sending test message
```

### Step 5: Customer Chat Test

```bash
# Navigate to main site
http://localhost:8000/

# Open chat widget
# Click "Chat with us"
# Verify all UI elements present
```

---

## 🧪 Feature Testing Procedures

### Feature 1: Typing Indicator

**Test Steps:**
1. Open customer chat and admin dashboard side-by-side
2. Type in customer chat input (don't send)
3. Verify "Admin is typing..." doesn't appear (that's from admin)
4. Check browser console: `[CHAT] User typing...` messages

**Expected Result:** ✅ No errors in console, socket event emitted

```javascript
// Console check
socket.emit('typing', { email: 'test@example.com', is_typing: true });
// Check admin receives 'user_typing' event
```

---

### Feature 2: Read Receipts

**Test Steps:**
1. Send message from customer
2. Admin receives and views message
3. Admin clicks checkmark (✓) or auto-reads
4. Verify message shows "✓✓ Read" with timestamp

**Expected Result:** ✅ Message marked as read, timestamp displays

```bash
# API test
curl -X PUT http://localhost:5000/api/messages/1/read
# Response: {"status": "success", "data": {"id": 1, "is_read": true, "read_at": "2024-01-01T12:00:00"}}
```

---

### Feature 3: Edit Messages

**Test Steps:**
1. Admin sends message via chat
2. Admin clicks "✏️ Edit" button
3. Type new text in prompt
4. Message updates with "(edited)" badge
5. Reload page - edit persists

**Expected Result:** ✅ Edit saves to database, displays on refresh

```bash
curl -X PUT http://localhost:5000/api/messages/1/edit \
  -H "Content-Type: application/json" \
  -d '{"new_text": "Updated message"}'
```

---

### Feature 4: File Upload

**Test Steps:**
1. Customer clicks 📎 attachment button
2. Select an image or PDF
3. File uploads with "Uploading..." message
4. File displays in chat with download link
5. Admin sees attachment in dashboard

**Expected Result:** ✅ File saves to `/uploads/messages/`, displays correctly

```javascript
// Frontend test
const file = new File(['test'], 'test.txt', {type: 'text/plain'});
uploadAttachment(1, file);
// Check Network tab for POST request
```

---

### Feature 5: Admin Status

**Test Steps:**
1. Open admin dashboard
2. Click "🟢 Online" button
3. Button toggles to "⚪ Offline"
4. Open customer chat - status updates
5. Toggle back to online

**Expected Result:** ✅ Status change broadcasts, color updates

```javascript
// Check console
socket.emit('admin_status_changed', { is_online: false });
// Customer should see status change in real-time
```

---

### Feature 6: Auto FAQ

**Test Steps:**
1. Admin dashboard → FAQ button (❓)
2. Add FAQ: keywords="refund", response="Please contact support"
3. Customer sends "How to refund?" message
4. Bot auto-responds with FAQ response
5. Verify FAQ check matched

**Expected Result:** ✅ Auto-response triggers for matching keywords

```bash
curl -X POST http://localhost:5000/api/messages/faq/check \
  -H "Content-Type: application/json" \
  -d '{"message": "How to refund?"}'
# Response: {"status": "success", "data": {"matched": true, "response": "Please contact support"}}
```

---

### Feature 7: Message Search

**Test Steps:**
1. Admin dashboard → search box
2. Type search term (e.g., "order")
3. Conversation list updates with matches
4. Click conversation to view
5. Search results highlight

**Expected Result:** ✅ Search finds all matching messages

```bash
curl "http://localhost:5000/api/messages/search?q=order&limit=20"
# Response: {"status": "success", "data": [...matching messages...]}
```

---

### Feature 8: Pagination

**Test Steps:**
1. Send 100+ messages to a customer
2. Open chat - first 50 load
3. Scroll to top
4. More messages auto-load
5. Check message count incrementally

**Expected Result:** ✅ Pagination loads efficiently in batches

```bash
curl "http://localhost:5000/api/messages/thread-paginated?email=test@example.com&limit=50&offset=0"
# Response includes: total_count, messages[], offset
```

---

### Feature 9: Unread Badge

**Test Steps:**
1. Admin dashboard → messages section
2. Send message from customer
3. Badge shows "X unread messages"
4. Admin clicks "Mark Read"
5. Badge updates to 0

**Expected Result:** ✅ Unread count updates accurately

```bash
curl http://localhost:5000/api/messages/unread-count
# Response: {"status": "success", "data": {"unread_count": 5}}
```

---

### Feature 10: Message Reactions

**Test Steps:**
1. Admin sends message
2. Customer sees 👍, ❤️ buttons
3. Click 👍 to react
4. Badge shows "👍 1"
5. Click again to add more reactions
6. Hover shows "user@email.com"

**Expected Result:** ✅ Reactions display with user list

```bash
curl -X POST http://localhost:5000/api/messages/1/reaction \
  -H "Content-Type: application/json" \
  -d '{"emoji": "👍", "email": "user@example.com"}'
# Response: {"status": "success", "data": {"reactions": {"👍": ["user@example.com"]}}}
```

---

### Feature 11: AI Suggestions

**Test Steps:**
1. Admin selects a message
2. Click for suggestions (or in quick actions)
3. See list of suggested responses
4. Click to copy/use suggestion
5. Verify suggestion matches FAQ

**Expected Result:** ✅ Suggestions display relevant templates

```bash
curl http://localhost:5000/api/messages/1/suggestions
# Response: {"status": "success", "data": ["Suggestion 1", "Suggestion 2"]}
```

---

### Feature 12: Delivery Tracking

**Test Steps:**
1. Place order in shop
2. Open chat for that order
3. Admin updates tracking in order
4. Chat displays tracking number
5. Click to track (external link)

**Expected Result:** ✅ Tracking info displays and updates

```bash
curl http://localhost:5000/api/messages/order/123/tracking
# Response: {"status": "success", "data": {"carrier": "FedEx", "tracking_number": "1Z999..."}}
```

---

### Feature 13: Attachments

**Test Steps:**
1. Upload image/PDF via 📎 button
2. File displays with thumbnail/preview
3. Download link works
4. File metadata shows (name, size)
5. Persist on page reload

**Expected Result:** ✅ Attachments save and display correctly

**Check:** `/uploads/messages/` directory contains uploaded files

---

### Feature 14: Message Pinning

**Test Steps:**
1. Admin right-clicks or selects message
2. Click "📌 Pin" button
3. Message marked as pinned
4. View pinned messages (📌 button)
5. See list of all pinned

**Expected Result:** ✅ Pinned messages accessible from sidebar

```bash
curl http://localhost:5000/api/messages/pinned
# Response: {"status": "success", "data": [...pinned messages...]}
```

---

### Feature 15: Archive/Delete

**Test Steps:**
1. Select message
2. Click "🗑️ Delete" button
3. Confirm deletion
4. Message disappears from view
5. Verify in database (soft-deleted)
6. Admin can "restore" if needed

**Expected Result:** ✅ Soft-delete preserves data

```bash
curl -X DELETE http://localhost:5000/api/messages/1
# Response: {"status": "success", "message": "Message archived"}
```

---

## 📊 Integration Testing

### Full Chat Flow Test

```javascript
// 1. Customer opens chat
openChatPanel();

// 2. Customer types (typing indicator fires)
sendTypingIndicator();

// 3. Customer sends message
// Message appears immediately (optimistic UI)
// Socket.IO sends message
// Or REST API fallback sends

// 4. Admin sees new message in real-time
// Typing indicator clears
// Message displays in conversation

// 5. Admin can:
// - Read (✓✓)
// - Reply
// - Edit (✓✓ with "(edited)" badge)
// - React 👍 ❤️
// - Pin 📌
// - Delete 🗑️
// - Upload attachment 📎

// 6. Customer sees everything in real-time
// All features sync across client/server/admin
```

---

## 🔍 Debug Mode Checklist

### Enable Debug Logging

```python
# backend/app.py
import logging
logging.basicConfig(level=logging.DEBUG)

@socketio.on('send_message')
def handle_send_message(data):
    print(f'[DEBUG] Message received: {data}')
    # ... rest of handler
```

### Check Socket Connection

```javascript
// Browser console
console.log(socket?.connected); // true/false
console.log(socket?.id);         // Socket ID
console.log(socket?.listeners);  // All listeners
```

### Monitor Network Requests

- Open DevTools → Network tab
- Filter by "api" or "socket.io"
- Check request/response headers
- Verify no 403/401 errors
- Check response payload structure

### Database Query Verification

```python
# In Python shell
from backend.database.models import Message, MessageAttachment, AdminStatus, FAQItem
from backend.database.db import db

# Count messages
print(f"Total messages: {Message.query.count()}")

# Check for new fields
msg = Message.query.first()
print(f"is_read: {msg.is_read}")
print(f"is_pinned: {msg.is_pinned}")
print(f"reactions: {msg.reactions}")

# Check attachment count
print(f"Total attachments: {MessageAttachment.query.count()}")
```

---

## 🚨 Troubleshooting

### Socket.IO Not Connecting

**Problem:** `Socket.IO not loaded from CDN`
**Solution:**
```html
<!-- Add local fallback -->
<script src="socket.io.js"></script>
<!-- Or check CDN is accessible -->
```

### File Upload 413 Error

**Problem:** `413 Payload Too Large`
**Solution:**
```python
# backend/app.py
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
```

### CORS Errors

**Problem:** `Cross-Origin Request Blocked`
**Solution:**
```python
socketio = SocketIO(app, cors_allowed_origins=['http://localhost:8000', 'https://yourdomain.com'])
```

### Messages Not Sending

**Problem:** No message delivery
**Checklist:**
- Socket.IO connected? `console.log(socket.connected)`
- API endpoint correct? Check `/api/messages` (no trailing slash)
- JWT token valid? Check auth headers
- Database writable? Check permissions

---

## 📈 Performance Testing

### Load Test: 1000 Messages

```bash
# Send 1000 messages
for i in {1..1000}; do
  curl -X POST http://localhost:5000/api/messages \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"test$i@example.com\", \"message\": \"Test $i\"}"
done

# Measure time: ~15-30 seconds for 1000 messages
```

### Connection Limit Test

```bash
# Open 10 chat panels simultaneously
# Each should get own Socket.IO connection
# Verify no connection pooling issues
```

### File Upload Stress Test

```bash
# Upload 10MB file
# Should complete in <5 seconds on good network
# Verify multipart form upload works
```

---

## ✨ Post-Deployment

1. **Monitor** - Check logs for errors daily
2. **Backup** - Daily database backups
3. **Updates** - Keep Socket.IO and libraries updated
4. **Analytics** - Track feature usage
5. **Feedback** - Collect user feedback
6. **Optimize** - Optimize based on real usage

---

## 🎯 Production Checklist

- [ ] SSL/TLS enabled for Socket.IO
- [ ] Environment variables configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] File upload directory secured
- [ ] Database backups automated
- [ ] Error logging configured
- [ ] Admin panel secured with MFA
- [ ] GDPR compliance (data deletion)
- [ ] Load balancer configured

---

**All 15 features ready for production deployment!** 🚀
