# XDR Authentication Implementation Summary

## Overview
JWT-based authentication has been successfully implemented for the XDR system. Only verified users can now access the dashboard and protected pages.

## What Was Implemented

### 1. **Security Module** (`src/security.py`)
- JWT token generation and verification
- Bcrypt-based password hashing and verification
- Token expiration management (24-hour tokens)
- Secret key configuration (should be changed in production)

### 2. **User Model** (`src/models.py`)
New `User` table with fields:
- `username` (unique, indexed)
- `email` (unique, indexed)
- `hashed_password` (using bcrypt)
- `full_name` (optional)
- `is_active` (default: True)
- `role` (admin, analyst, or viewer)
- `created_at` (timestamp)

### 3. **Authentication Endpoints** (`src/main.py`)

#### POST `/api/auth/register`
- Register a new user account
- Validates unique username and email
- Returns user details (201 Created)
- Example:
  ```bash
  curl -X POST http://127.0.0.1:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{
      "username": "analyst1",
      "email": "analyst1@xdr.local",
      "password": "SecurePass123",
      "full_name": "Security Analyst"
    }'
  ```

#### POST `/api/auth/login`
- Authenticate user with username and password
- Returns JWT access token (24-hour expiration)
- Returns: `{"access_token": "...", "token_type": "bearer", "expires_in": 86400}`
- Example:
  ```bash
  curl -X POST http://127.0.0.1:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "username": "admin",
      "password": "password123"
    }'
  ```

#### GET `/api/auth/me`
- Get current authenticated user info
- Requires valid JWT token in cookie
- Returns user details with role and email

#### POST `/api/auth/logout`
- Logout endpoint (token invalidated client-side)
- Returns success message

### 4. **Login Page** (`src/static/login.html`)
- Modern, responsive login/registration UI
- Features:
  - Login form with username and password
  - Registration form with email validation
  - Toggle between login and registration
  - Error and success messages
  - Demo credentials displayed
  - Automatic redirect to dashboard if already logged in
  - Client-side JS handling for auth flow

### 5. **Protected Dashboard**
- Dashboard now requires authentication
- Redirects unauthenticated users to `/login`
- User menu in top-right corner showing:
  - Current username
  - User role
  - Logout button
- All view pages (`/view/alerts`, `/view/iocs`, `/view/reports`) also protected

### 6. **Dashboard Updates**
- Added user menu UI in header
- Logout functionality in JavaScript
- Load and display current user info
- Auto-redirect if already authenticated

### 7. **Database Initialization**
- Default admin user created on first run:
  - Username: `admin`
  - Password: `password123`
  - Role: `admin`
  - Email: `admin@xdr.local`

## Authentication Flow

### Login Flow
1. User visits `http://localhost:8000/dashboard`
2. If no auth token → Redirected to `/login`
3. User enters credentials on login page
4. Frontend sends POST to `/api/auth/login`
5. Backend validates and returns JWT token
6. Frontend sets token as `auth_token` cookie
7. Frontend redirects to `/dashboard`
8. Dashboard verifies token and loads

### Registration Flow
1. User clicks "Sign Up" on login page
2. Fills in registration form
3. Frontend sends POST to `/api/auth/register`
4. Backend validates and creates user
5. Success message shown, switches back to login
6. User can now login with new credentials

## Security Features

✅ **Password Security**
- Bcrypt hashing with salt
- Passwords never stored in plaintext
- Strong password validation (min 6 chars)

✅ **Token Security**
- JWT with HS256 algorithm
- 24-hour expiration tokens
- Tokens stored in httpOnly cookies on frontend
- Invalid tokens blocked from accessing protected routes

✅ **Account Security**
- Unique usernames and emails enforced
- Active/inactive user status support
- Role-based system (admin, analyst, viewer)

✅ **Protected Routes**
- /dashboard - requires auth
- /view/alerts - requires auth
- /view/iocs - requires auth
- /view/reports - requires auth
- /api/auth/me - requires auth

## Default Credentials

**For testing:**
```
Username: admin
Password: password123
```

**Note:** Change these credentials in production!

## Configuration

### Environment Variables (for production)
Create `.env` file with:
```
SECRET_KEY=your-super-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Database
- SQLite by default (`xdr.db`)
- User table with proper indexes
- Automatic initialization on startup

## Dependencies Added

```
python-jose[cryptography]>=3.3,<4.0    # JWT handling
bcrypt>=4.0,<5.0                        # Password hashing
python-multipart>=0.0.6,<1.0            # Form parsing
```

## Testing the System

### 1. Start the server:
```bash
cd /home/asmit/Desktop/XDR
source .venv/bin/activate
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Access the application:
- Dashboard: http://127.0.0.1:8000/dashboard
- Login Page: http://127.0.0.1:8000/login
- API Docs: http://127.0.0.1:8000/docs
- API Health: http://127.0.0.1:8000/health

### 3. Test login with default credentials:
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'
```

### 4. Register a new user:
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@xdr.local",
    "password": "StrongPass123",
    "full_name": "New User"
  }'
```

## Files Modified/Created

### Created:
- `src/security.py` - JWT and password utilities
- `src/static/login.html` - Login/registration UI

### Modified:
- `src/models.py` - Added User model
- `src/schemas.py` - Added auth schemas (UserLogin, UserRegister, Token, etc.)
- `src/main.py` - Added auth endpoints and middleware
- `src/database.py` - Create default admin user on init
- `src/static/dashboard.html` - Added user menu
- `src/static/dashboard.css` - User menu styles
- `src/static/dashboard.js` - User menu and logout logic
- `requirements.txt` - Added auth dependencies

## Next Steps / Future Improvements

1. **Role-Based Access Control (RBAC)**
   - Implement permission checks for endpoints
   - Different access levels per role

2. **Enhanced Security**
   - Rate limiting on login endpoint
   - Account lockout after N failed attempts
   - Email verification
   - Password reset functionality
   - 2FA/MFA support

3. **API Security**
   - OAuth2 integration
   - API key support for service-to-service auth
   - CORS configuration

4. **Session Management**
   - Refresh tokens
   - Token revocation/blacklist
   - Session tracking

5. **Production Hardening**
   - HTTPS/TLS enforcement
   - Secure cookie flags
   - Password complexity requirements
   - Audit logging

## Deployment Notes

For production, ensure:
1. Change `SECRET_KEY` in `src/security.py`
2. Use PostgreSQL instead of SQLite
3. Enable HTTPS
4. Set secure cookie flags
5. Configure CORS properly
6. Use environment variables for sensitive config
7. Implement rate limiting
8. Set up monitoring and alerting

## Support

For issues or questions, refer to:
- FastAPI docs: https://fastapi.tiangolo.com/
- JWT docs: https://tools.ietf.org/html/rfc7519
- bcrypt docs: https://en.wikipedia.org/wiki/Bcrypt
