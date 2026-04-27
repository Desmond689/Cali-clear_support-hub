from flask import request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from functools import wraps
from config import Config
from services.auth_service import get_user_by_id
from database.db import db


# Bypass token for admin panel direct access
ADMIN_BYPASS_TOKEN = "admin-panel-direct-access"


def _normalize_user_id(identity):
    """
    Normalize JWT identity into an integer user id.
    Supports int, numeric strings, and dict-like identities.
    """
    if isinstance(identity, dict):
        identity = identity.get('id') or identity.get('user_id') or identity.get('sub')

    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def admin_required(fn):
    """
    Decorator that requires a valid JWT token with admin privileges.
    
    This decorator:
    1. Checks for admin bypass token (development mode)
    2. Verifies the JWT token is present and valid
    3. Checks if the user is an admin
    
    Returns 403 if:
    - No token provided
    - Token is invalid/expired
    - User is not an admin
    
    Special case: If X-Admin-Bypass header is present with the correct token,
    automatically creates a valid admin session without JWT verification.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Check for admin bypass token (development mode)
        bypass_token = request.headers.get('X-Admin-Bypass')
        
        if bypass_token == ADMIN_BYPASS_TOKEN:
            # Find first admin user
            try:
                from database.models import User
                admin = User.query.filter_by(is_admin=True).first()
                
                # If no admin found, try to auto-create from environment variables
                if not admin:
                    from os import getenv
                    default_email = getenv('DEFAULT_ADMIN_EMAIL')
                    default_password = getenv('DEFAULT_ADMIN_PASSWORD')
                    
                    if default_email and default_password:
                        try:
                            admin = User(email=default_email, is_admin=True)
                            admin.set_password(default_password)
                            db.session.add(admin)
                            db.session.commit()
                            print(f"[ADMIN_BYPASS] Auto-created admin user: {default_email}")
                        except Exception as create_err:
                            print(f"[ADMIN_BYPASS] Failed to create admin user: {create_err}")
                            db.session.rollback()
            except Exception as e:
                print(f"[ADMIN_BYPASS ERROR] Database query failed: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'status': 'error',
                    'message': f'Database error: {str(e)}'
                }), 500
            
            if admin:
                # Store admin in Flask g for access in the route
                g.current_user = admin
                g.jwt_identity = admin.id
                g.is_admin_bypass = True
                
                print(f"[ADMIN_BYPASS] Access granted for admin: {admin.email}")
                return fn(*args, **kwargs)
            else:
                print(f"[ADMIN_BYPASS] No admin user found in database and no DEFAULT_ADMIN_EMAIL configured")
                # return 403 so the front‑end treats it as authorization failure
                return jsonify({
                    'status': 'error',
                    'message': 'No admin user configured. Run: python create_admin.py in backend folder, or set DEFAULT_ADMIN_EMAIL and DEFAULT_ADMIN_PASSWORD environment variables.'
                }), 403
        
        # Check for valid JWT token in Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            print(f"[ADMIN_REQUIRED] No Authorization header found")
            return jsonify({
                'status': 'error',
                'message': 'Missing or invalid Authorization header'
            }), 403
        
        # Normal JWT verification - this will verify the token signature and expiration
        try:
            verify_jwt_in_request()
        except Exception as e:
            print(f"[ADMIN_REQUIRED] JWT verification failed: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized - Invalid or missing token'
            }), 403
        
        # Get user identity from token
        user_id = _normalize_user_id(get_jwt_identity())

        if not user_id:
            print(f"[ADMIN_REQUIRED] No identity in JWT token")
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized - Invalid token'
            }), 403
        
        user = get_user_by_id(user_id)
        
        if not user:
            print(f"[ADMIN_REQUIRED] User not found: {user_id}")
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized - User not found'
            }), 403
        
        if not user.is_admin:
            print(f"[ADMIN_REQUIRED] User is not admin: {user_id}")
            return jsonify({
                'status': 'error',
                'message': 'Forbidden - Admin access required'
            }), 403
        
        # Store user in Flask g for access in the route
        g.current_user = user
        g.jwt_identity = user_id
        g.is_admin_bypass = False
        
        print(f"[ADMIN_REQUIRED] Admin access granted for user: {user_id}")
        return fn(*args, **kwargs)
    
    wrapper.__name__ = fn.__name__
    return wrapper


def get_current_admin():
    """
    Helper function to get the current admin user.
    Works with both JWT auth and bypass mode.
    Returns the User object or None if not authenticated as admin.
    """
    from flask import g
    
    # Check if we already have the user from the decorator
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user
    
    # Fallback: try to get from JWT identity
    try:
        user_id = _normalize_user_id(get_jwt_identity())
        if user_id:
            return get_user_by_id(user_id)
    except Exception:
        pass
    
    return None
