from database.db import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    # Relationship to products for category listings and counts
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_id = db.Column(db.Integer)  # Original ID from products.json
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    image_url = db.Column(db.String(200))
    stock = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cart(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # UUID for anonymous cart
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Wishlist(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # UUID for anonymous wishlist
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.String(20), primary_key=True)  # Custom order number
    email = db.Column(db.String(120), nullable=False)
    customer_name = db.Column(db.String(100))  # Full name of customer
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='created')
    shipping_address = db.Column(db.Text)
    city = db.Column(db.String(100))  # City for destination
    zip_code = db.Column(db.String(20))  # ZIP code for destination
    tracking_number = db.Column(db.String(100))
    carrier = db.Column(db.String(50))
    
    # Payment method reference
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_method.id'), nullable=True)
    payment_method_name = db.Column(db.String(50))  # Denormalized for display

    # Legacy MiniPay fields (kept for backward compat)
    minipay_phone = db.Column(db.String(20), default=lambda: os.getenv('MINIPAY_PHONE', 'MINIPAY_WALLET'))
    minipay_qr_data = db.Column(db.Text)  # Base64 QR image
    payment_deadline = db.Column(db.DateTime)
    transaction_ref = db.Column(db.String(100))
    screenshot_path = db.Column(db.String(200))
    payment_status = db.Column(db.String(20), default='none')  # none/pending/verified/rejected
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationship to order items for admin endpoints and detail views
    items = db.relationship('OrderItem', backref='order', lazy=True)
    
    # MiniPay relationship
    confirmations = db.relationship('PaymentConfirmation', backref='order', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Locked price at order time
    # Relationship to product for name/price lookup
    product = db.relationship('Product', lazy=True)

class PaymentConfirmation(db.Model):
    """Customer payment confirmation submissions"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), db.ForeignKey('order.id'), nullable=False)
    amount_sent = db.Column(db.Float)
    transaction_ref = db.Column(db.String(100))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    screenshot_data = db.Column(db.LargeBinary)  # Binary screenshot
    status = db.Column(db.String(20), default='pending')  # pending/verified/rejected

class AdminVerificationToken(db.Model):
    """Stores one-time verification tokens for admin login."""
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    admin_email = db.Column(db.String(120), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Message(db.Model):
    """Customer support messages from chat widget"""
    id = db.Column(db.Integer, primary_key=True)
    customer_email = db.Column(db.String(120), nullable=False, index=True)
    customer_name = db.Column(db.String(100))
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(30), default='text')  # text, order, payment_details, proof, bot, status_update
    order_id = db.Column(db.String(20), db.ForeignKey('order.id'), nullable=True)  # Link to order
    status = db.Column(db.String(20), default='new')  # new, read, replied
    admin_reply = db.Column(db.Text)
    screenshot_data = db.Column(db.Text)  # Base64 screenshot for proof messages
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    replied_at = db.Column(db.DateTime)
    
    # 2. Message Read Receipts
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # 3. Message Editing
    edited_at = db.Column(db.DateTime)
    edited_by = db.Column(db.String(50))  # 'admin' or 'customer'
    original_message = db.Column(db.Text)  # Store original for audit trail
    edit_count = db.Column(db.Integer, default=0)
    
    # 4. File Upload Support
    attachment_type = db.Column(db.String(50))  # pdf, docx, image, invoice, etc
    attachment_path = db.Column(db.String(255))  # Path to uploaded file
    attachment_size = db.Column(db.Integer)  # File size in bytes
    attachment_name = db.Column(db.String(255))  # Original filename
    
    # 10. Message Reactions
    reactions = db.Column(db.Text)  # JSON: {'👍': ['email1', 'email2'], '❤️': ['email3']}
    
    # 14. Conversation Pinning
    is_pinned = db.Column(db.Boolean, default=False)
    pinned_at = db.Column(db.DateTime)
    pinned_by = db.Column(db.String(120))  # Admin email who pinned it
    
    # 15. Message Delete/Archive
    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime)
    
    # Relationships
    attachments = db.relationship('MessageAttachment', backref='message', cascade='all, delete-orphan')


class MessageAttachment(db.Model):
    """File attachments for messages"""
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))  # pdf, docx, jpg, png, etc
    file_size = db.Column(db.Integer)  # bytes
    upload_by = db.Column(db.String(120))  # customer or admin email
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AdminStatus(db.Model):
    """Track admin online status"""
    id = db.Column(db.Integer, primary_key=True)
    admin_email = db.Column(db.String(120), unique=True, nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)


class FAQItem(db.Model):
    """Auto-reply FAQ for common questions"""
    id = db.Column(db.Integer, primary_key=True)
    keywords = db.Column(db.Text, nullable=False)  # comma-separated or JSON list
    response = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # refund, shipping, payment, etc
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=0)  # higher = checked first
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageSearchIndex(db.Model):
    """Search index for messages"""
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False, unique=True)
    search_text = db.Column(db.Text)  # Combined searchable text
    customer_email = db.Column(db.String(120), db.ForeignKey('message.customer_email'))
    order_id = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class PaymentMethod(db.Model):
    """Configurable payment methods (Venmo, Cash App, PayPal, Bank Transfer)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)           # e.g. "Venmo"
    slug = db.Column(db.String(30), unique=True, nullable=False)  # e.g. "venmo"
    icon = db.Column(db.String(10))                           # emoji icon
    account_details = db.Column(db.Text)                       # JSON: display fields for the method
    instructions = db.Column(db.Text)                          # Bot message template
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Middleman(db.Model):
    """Middlemen assigned to payment methods for receiving payments"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)             # Display name e.g. "John D"
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_method.id'), nullable=False)
    account_info = db.Column(db.Text)                            # JSON: cashtag, venmo_user, bank details, etc.
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payment_method = db.relationship('PaymentMethod', backref='middlemen', lazy=True)


class AdminNotification(db.Model):
    """Persistent notifications for the admin panel"""
    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(30), nullable=False)  # new_order, proof_upload, order_completed, payment_verified
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    order_id = db.Column(db.String(20), db.ForeignKey('order.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship('Order', backref='notifications', lazy=True)


class PasswordResetToken(db.Model):
    """One-time password reset tokens"""
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self):
        """Check if token is valid (not expired and not used)."""
        return not self.used and datetime.utcnow() < self.expires_at
