from flask import Blueprint, request, jsonify
from database.models import (
    Message,
    Order,
    Product,
    PaymentMethod,
    AdminNotification,
    db,
)
from utils.responses import success_response, error_response
from middleware.admin_required import admin_required
from services.email_service import send_email
from datetime import datetime
import json
import base64

# Import socketio for real-time emits
from app import socketio

bp = Blueprint("messages", __name__, url_prefix="/api/messages")


@bp.route("", methods=["POST"])
def create_message():
    """Customer sends a chat message"""
    data = request.json or {}
    email = data.get("email", "").strip()
    name = data.get("name", "Guest").strip()
    message = data.get("message", "").strip()
    message_type = data.get("message_type", "text")
    order_id = data.get("order_id", "").strip() or None

    if not email or not message:
        return error_response("Email and message are required", 400)

    msg = Message(
        customer_email=email,
        customer_name=name,
        message=message,
        message_type=message_type,
        order_id=order_id,
        status="new",
    )
    db.session.add(msg)
    db.session.commit()

    # Emit real-time notification to admin via SocketIO
    try:
        socketio.emit('new_user_message', {
            'email': email,
            'name': name,
            'message': message,
            'message_type': message_type,
            'order_id': order_id,
            'timestamp': msg.created_at.isoformat(),
            'id': msg.id
        }, room='admin')
        print(f"[SOCKETIO] Emitted new_user_message to admin for {email}")
    except Exception as e:
        print(f"[SOCKETIO] Error emitting admin notification: {e}")

    # Notify admin of new message via email
    send_email(
        "support@caliclear.shop",
        f"New message from {name}",
        f"Customer {name} ({email}) sent a message:\n\n{message}",
    )

    return success_response(message="Message sent", data={"id": msg.id})


@bp.route("/proof", methods=["POST"])
def upload_payment_proof():
    """Customer uploads payment proof (screenshot + transaction ID)"""
    data = request.json or {}
    email = data.get("email", "").strip()
    name = data.get("name", "Guest").strip()
    order_id = data.get("order_id", "").strip()
    transaction_id = data.get("transaction_id", "").strip()
    screenshot_base64 = data.get("screenshot", "").strip()
    note = data.get("note", "").strip()

    if not email or not order_id:
        return error_response("Email and order_id are required", 400)

    # Verify order exists
    order = Order.query.get(order_id)
    if not order:
        return error_response("Order not found", 404)

    # Build proof message
    proof_parts = [f"📄 Payment Proof for Order #{order_id}"]
    if transaction_id:
        proof_parts.append(f"Transaction ID: {transaction_id}")
    if note:
        proof_parts.append(f"Note: {note}")
    if screenshot_base64:
        proof_parts.append("Screenshot: [attached]")

    proof_text = "\n".join(proof_parts)

    # Create message with proof
    msg = Message(
        customer_email=email,
        customer_name=name,
        message=proof_text,
        message_type="proof",
        order_id=order_id,
        status="new",
        screenshot_data=screenshot_base64 if screenshot_base64 else None,
    )
    db.session.add(msg)

    # Update order payment status
    order.payment_status = "pending"
    order.transaction_ref = transaction_id or order.transaction_ref
    if screenshot_base64:
        order.screenshot_path = "attached"  # Mark as attached, full data in Message

    db.session.commit()

    # Bot auto-reply acknowledging proof
    bot_ack = Message(
        customer_email=email,
        customer_name="Bot",
        message=f"✅ Payment proof received for Order #{order_id}!\n\nOur team will verify your payment shortly. You'll be notified once confirmed.",
        message_type="bot",
        order_id=order_id,
        status="replied",
        replied_at=datetime.utcnow(),
    )
    db.session.add(bot_ack)
    db.session.commit()

    # Notify admin
    send_email(
        "support@caliclear.shop",
        f"Payment proof submitted - Order #{order_id}",
        f"{name} ({email}) submitted payment proof for Order #{order_id}.\nTransaction ID: {transaction_id or 'N/A'}\n\nPlease verify in admin dashboard.",
    )

    # Create admin notification for proof upload
    admin_notif = AdminNotification(
        notification_type="proof_upload",
        title=f"Payment Proof - Order #{order_id}",
        body=f"{name} ({email}) submitted payment proof.\nTransaction ID: {transaction_id or 'N/A'}",
        order_id=order_id,
    )
    db.session.add(admin_notif)
    db.session.commit()

    return success_response(message="Payment proof uploaded", data={"id": msg.id})


@bp.route("/quick-action", methods=["POST"])
def quick_action():
    """Handle quick action buttons from chat"""
    data = request.json or {}
    email = data.get("email", "").strip()
    name = data.get("name", "Guest").strip()
    action = data.get("action", "").strip()
    order_id = data.get("order_id", "").strip() or None

    if not email or not action:
        return error_response("Email and action are required", 400)

    responses = {
        "confirm_order": "✅ Order confirmed! We'll process it right away.",
        "i_have_paid": "💰 Got it! Please upload your payment proof so we can verify.",
        "cancel_order": "❌ Order cancellation requested. Our team will process this shortly.",
        "talk_to_agent": "🧑‍💼 An agent will be with you shortly. Please describe your issue.",
        "track_order": None,  # Dynamic
    }

    # Handle order-specific actions
    if order_id and action in ("confirm_order", "cancel_order"):
        order = Order.query.get(order_id)
        if order and order.email == email:
            if action == "cancel_order":
                order.status = "cancelled"
                db.session.commit()
            elif action == "confirm_order":
                order.payment_status = "pending"
                db.session.commit()

    # Track order action
    if action == "track_order" and order_id:
        order = Order.query.get(order_id)
        if order:
            status_map = {
                "created": "📋 Order placed - awaiting payment",
                "pending_payment": "⏳ Order placed - pending payment instructions",
                "payment_instructions_sent": "☎️ Payment details sent - awaiting payment",
                "paid": "💰 Payment received - preparing order",
                "packed": "📦 Order packed",
                "processing": "⚙️ Processing your order",
                "shipped": "🚚 Order shipped",
                "delivered": "✅ Delivered",
                "cancelled": "❌ Cancelled",
            }
            track_msg = f"📦 Order #{order_id}\nStatus: {status_map.get(order.status, order.status)}"
            if order.tracking_number:
                track_msg += (
                    f"\nTracking: {order.tracking_number} ({order.carrier or ''})"
                )
            responses["track_order"] = track_msg
        else:
            responses["track_order"] = "Order not found."

    bot_reply = responses.get(action, "Sorry, I didn't understand that action.")

    # Save user action message
    action_labels = {
        "confirm_order": "✅ Confirmed Order",
        "i_have_paid": "💰 I Have Paid",
        "cancel_order": "❌ Cancel Order",
        "talk_to_agent": "🧑‍💼 Talk to Agent",
        "track_order": "📦 Track Order",
    }
    user_msg = Message(
        customer_email=email,
        customer_name=name,
        message=action_labels.get(action, action),
        message_type="quick_action",
        order_id=order_id,
        status="new",
    )
    db.session.add(user_msg)
    db.session.commit()

    # Save bot response
    bot_msg = Message(
        customer_email=email,
        customer_name="Bot",
        message=bot_reply,
        message_type="bot",
        order_id=order_id,
        status="replied",
        replied_at=datetime.utcnow(),
    )
    db.session.add(bot_msg)
    db.session.commit()

    return success_response(data={"reply": bot_reply})


@bp.route("/thread", methods=["GET"])
def get_thread():
    """Get conversation thread for a customer"""
    email = request.args.get("email", "").strip()
    order_id = request.args.get("order_id", "").strip()

    if not email:
        return error_response("Email is required", 400)

    query = Message.query.filter_by(customer_email=email)
    if order_id:
        query = query.filter(
            db.or_(Message.order_id == order_id, Message.order_id.is_(None))
        )

    messages = query.order_by(Message.created_at.asc()).all()

    return success_response(
        data=[
            {
                "id": m.id,
                "customer_email": m.customer_email,
                "customer_name": m.customer_name,
                "message": m.message,
                "message_type": getattr(m, "message_type", "text") or "text",
                "order_id": getattr(m, "order_id", None),
                "admin_reply": m.admin_reply,
                "status": m.status,
                "has_screenshot": bool(getattr(m, "screenshot_data", None)),
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "replied_at": m.replied_at.isoformat() if m.replied_at else None,
            }
            for m in messages
        ]
    )


@bp.route("", methods=["GET"])
@admin_required
def get_messages():
    """Admin gets all customer messages"""
    order_id = request.args.get("order_id", "").strip()

    query = Message.query
    if order_id:
        query = query.filter_by(order_id=order_id)

    messages = query.order_by(Message.created_at.desc()).all()
    return success_response(
        data=[
            {
                "id": m.id,
                "customer_email": m.customer_email,
                "customer_name": m.customer_name,
                "message": m.message,
                "message_type": getattr(m, "message_type", "text") or "text",
                "order_id": getattr(m, "order_id", None),
                "status": m.status,
                "admin_reply": m.admin_reply,
                "has_screenshot": bool(getattr(m, "screenshot_data", None)),
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "replied_at": m.replied_at.isoformat() if m.replied_at else None,
            }
            for m in messages
        ]
    )


@bp.route("/<int:msg_id>", methods=["PUT"])
@admin_required
def reply_message(msg_id):
    """Admin replies to a customer message"""
    msg = Message.query.get(msg_id)
    if not msg:
        return error_response("Message not found", 404)

    data = request.json or {}
    reply = data.get("reply", "").strip()

    if not reply:
        return error_response("Reply text is required", 400)

    msg.admin_reply = reply
    msg.status = "replied"
    msg.replied_at = datetime.utcnow()
    db.session.commit()

    # Emit real-time notification to user via SocketIO
    # Use both event names for compatibility
    reply_data = {
        'sender': 'admin',
        'message': reply,
        'admin_reply': reply,
        'timestamp': msg.replied_at.isoformat(),
        'replied_at': msg.replied_at.isoformat()
    }
    
    # Emit to the customer's room
    print(f"[SOCKETIO] Emitting admin reply to room {msg.customer_email}: {reply}")
    socketio.emit('new_message', reply_data, room=msg.customer_email)
    socketio.emit('admin_reply', reply_data, room=msg.customer_email)

    # Send reply email to customer (best-effort, don't fail on email error)
    try:
        body = (
            f'Hello {msg.customer_name},\n\nWe received your message: "{msg.message}"\n\n'
            f"Our response:\n{reply}\n\nThank you for contacting us!"
        )
        send_email(
            msg.customer_email,
            "Reply to your message - Cali Clear Support",
            body,
        )
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Failed to send reply email: {e}")

    return success_response(message="Reply sent to customer")


@bp.route("/admin/verify-payment/<order_id>", methods=["POST"])
@admin_required
def admin_verify_payment(order_id):
    """Admin verifies/rejects payment for an order"""
    order = Order.query.get(order_id)
    if not order:
        return error_response("Order not found", 404)

    data = request.json or {}
    action = data.get("action", "").strip()  # 'verify' or 'reject'
    admin_note = data.get("note", "").strip()

    if action == "verify":
        # decrement stock now that payment is confirmed
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product and product.stock is not None:
                product.stock = max(0, product.stock - item.quantity)

        order.payment_status = "verified"
        order.status = "paid"
        bot_msg_text = f"✅ Payment verified for Order #{order_id}!\n\nYour order is now being processed. Thank you!"
    elif action == "reject":
        order.payment_status = "rejected"
        order.status = "payment_rejected"
        bot_msg_text = f"❌ Payment could not be verified for Order #{order_id}.\n\n"
        if admin_note:
            bot_msg_text += f"Reason: {admin_note}\n\n"
        bot_msg_text += "Please re-upload your payment proof or contact support."
    else:
        return error_response('Invalid action. Use "verify" or "reject"', 400)

    db.session.commit()

    # Send notification message to customer chat
    bot_msg = Message(
        customer_email=order.email,
        customer_name="Bot",
        message=bot_msg_text,
        message_type="status_update",
        order_id=order_id,
        status="replied",
        replied_at=datetime.utcnow(),
    )
    db.session.add(bot_msg)
    db.session.commit()

    # Emit real-time status update to customer via SocketIO
    print(f"[SOCKETIO] Emitting payment status update to {order.email}: {action}")
    socketio.emit('new_message', {
        'sender': 'bot',
        'message': bot_msg_text,
        'message_type': 'status_update',
        'timestamp': bot_msg.replied_at.isoformat()
    }, room=order.email)

    # Email notification
    send_email(
        order.email,
        f"Payment {'Verified' if action == 'verify' else 'Rejected'} - Order #{order_id}",
        bot_msg_text,
    )

    # Create admin notification for payment verification
    notif_type = "payment_verified" if action == "verify" else "payment_rejected"
    admin_notif = AdminNotification(
        notification_type=notif_type,
        title=f"Payment {'Verified' if action == 'verify' else 'Rejected'} - Order #{order_id}",
        body=f"Order #{order_id} payment {action}d. {f'Reason: {admin_note}' if admin_note else ''}",
        order_id=order_id,
    )
    db.session.add(admin_notif)
    db.session.commit()

    return success_response({"message": f"Payment {action}d", "order_id": order_id})


@bp.route("/admin/send-payment-instructions", methods=["POST"])
@admin_required
def send_payment_instructions():
    """Admin sends manual payment instructions into the chat.

    This endpoint supports the human-in-the-loop flow where the bot does not expose
    payment details automatically.
    """
    data = request.json or {}
    order_id = data.get("order_id", "").strip()
    message_body = (data.get("message") or "").strip()

    if not order_id or not message_body:
        return error_response("order_id and message are required", 400)

    order = Order.query.get(order_id)
    if not order:
        return error_response("Order not found", 404)

    instr_msg = Message(
        customer_email=order.email,
        customer_name="Bot",
        message=message_body,
        message_type="payment_details",
        order_id=order_id,
        status="replied",
        replied_at=datetime.utcnow(),
    )
    db.session.add(instr_msg)

    # Optionally update order status to 'payment_instructions_sent'
    order.payment_status = "pending"
    order.status = "payment_instructions_sent"
    db.session.commit()

    # Emit real-time payment instructions to customer via SocketIO
    print(f"[SOCKETIO] Emitting payment instructions to {order.email}")
    socketio.emit('new_message', {
        'sender': 'bot',
        'message': message_body,
        'message_type': 'payment_details',
        'timestamp': instr_msg.replied_at.isoformat()
    }, room=order.email)

    # Notify customer by email (optional)
    send_email(
        order.email,
        f"Payment Instructions for Order #{order_id}",
        f"Hi {order.customer_name or order.email},\n\n{message_body}\n\nPlease upload proof in chat once payment is made.",
    )

    return success_response(
        {"message": "Payment instructions sent", "order_id": order_id}
    )


@bp.route("/<int:msg_id>/screenshot", methods=["GET"])
@admin_required
def get_screenshot(msg_id):
    """Admin retrieves payment proof screenshot by message ID"""
    msg = Message.query.get(msg_id)
    if not msg:
        return error_response("Message not found", 404)

    screenshot = getattr(msg, "screenshot_data", None)
    if not screenshot:
        return error_response("No screenshot attached", 404)

    return jsonify(
        {
            "status": "success",
            "screenshot_data": screenshot,
            "message_type": msg.message_type,
            "order_id": msg.order_id,
        }
    )


@bp.route("/proof-image/<int:msg_id>", methods=["GET"])
def get_proof_image(msg_id):
    """Get proof screenshot as a viewable data URL (no admin required for customer view)"""
    msg = Message.query.get(msg_id)
    if not msg:
        return error_response("Message not found", 404)

    screenshot = getattr(msg, "screenshot_data", None)
    if not screenshot:
        return error_response("No screenshot attached", 404)

    return jsonify({"status": "success", "screenshot_data": screenshot})
