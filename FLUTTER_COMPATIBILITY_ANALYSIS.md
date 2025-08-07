# Flutter App Compatibility Analysis

## Backend API Changes Summary

The EmotionAI API has been completely restructured with Clean Architecture. Use this information to analyze your Flutter app for required updates.

## New API Structure

### Base URL & Environment
- **Development**: `http://localhost:8000`
- **Health Check**: `GET /health/` (use this to verify backend is running)

### Authentication Endpoints
```
POST /auth/register
POST /auth/login  
POST /auth/logout
GET /auth/me
```

**Request/Response Format:**
```json
// Registration Request
{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe",
  "date_of_birth": "1990-01-01T00:00:00Z" // Optional
}

// Login Request  
{
  "email": "user@example.com",
  "password": "securepassword"
}

// Auth Response
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "email": "user@example.com", 
    "first_name": "John",
    "last_name": "Doe",
    "is_verified": true
  }
}
```

### Chat/Agent Endpoints
```
POST /api/v1/chat
GET /api/v1/agents
GET /api/v1/agents/{agent_type}/status
DELETE /api/v1/agents/{agent_type}/memory
GET /api/v1/conversations
```

**Chat Request/Response:**
```json
// Chat Request
{
  "agent_type": "therapy" | "wellness",
  "message": "User message here",
  "context": {} // Optional additional context
}

// Chat Response
{
  "message": "Agent response",
  "agent_type": "therapy",
  "conversation_id": "uuid",
  "crisis_detected": false,
  "crisis_resources": null,
  "suggestions": ["suggestion1", "suggestion2"],
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Available Agent Types
```json
{
  "agents": [
    {
      "type": "therapy",
      "name": "Therapy Agent",
      "description": "Provides therapeutic conversations and emotional support",
      "capabilities": ["emotional_support", "coping_strategies", "crisis_detection"]
    },
    {
      "type": "wellness", 
      "name": "Wellness Agent",
      "description": "Focuses on mindfulness, breathing exercises, and general wellness",
      "capabilities": ["mindfulness", "breathing_exercises", "wellness_tips"]
    }
  ]
}
```

## Authentication Changes

### Headers Required
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Token Management
- **Token Expiry**: 30 minutes (1800 seconds)
- **Refresh**: Need to re-login when token expires
- **Storage**: Store JWT securely in Flutter (secure_storage package)

## Breaking Changes from Old API

### 1. **Endpoint Paths Changed**
- Old: `/agents/chat` → New: `/api/v1/chat`
- Old: `/users/register` → New: `/auth/register` 
- Old: `/users/login` → New: `/auth/login`

### 2. **Response Structure Changes**
- All responses now have consistent error format
- Success responses may have additional metadata
- Agent responses include `conversation_id` and `timestamp`

### 3. **Authentication Method**
- Now uses JWT Bearer tokens (was it different before?)
- Tokens expire after 30 minutes
- No more session-based auth

## New Features Available

### 1. **Crisis Detection**
```json
{
  "crisis_detected": true,
  "crisis_severity": "high" | "medium" | "low", 
  "crisis_resources": {
    "hotline": "988",
    "message": "If you're in crisis, please call...",
    "resources": ["url1", "url2"]
  }
}
```

### 2. **Agent Status Monitoring**
```json
{
  "agent_type": "therapy",
  "status": "active" | "idle" | "error",
  "last_interaction": "2024-01-01T00:00:00Z",
  "memory_items": 15,
  "response_time_ms": 250
}
```

### 3. **Conversation History**
```json
[
  {
    "id": "conversation_uuid",
    "agent_type": "therapy",
    "title": "Conversation Title",
    "created_at": "2024-01-01T00:00:00Z",
    "last_message_at": "2024-01-01T01:00:00Z", 
    "message_count": 10,
    "is_active": true
  }
]
```

### 4. **Enhanced Error Handling**
```json
{
  "error": "validation_error" | "application_error" | "internal_server_error",
  "message": "Human readable message",
  "details": {} // Additional error context
}
```

## Health & Monitoring

### Health Check Endpoints
- `GET /health/` - Basic health check
- `GET /health/detailed` - Component health status
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

## Database Schema Changes

### User Model Updates
```json
{
  "id": "uuid",
  "email": "string",
  "first_name": "string", 
  "last_name": "string",
  "date_of_birth": "datetime", // Optional
  "is_active": "boolean",
  "is_verified": "boolean",
  "agent_personality_data": {}, // New: agent customization
  "user_profile_data": {}, // New: user preferences
  "created_at": "datetime",
  "updated_at": "datetime",
  "last_login_at": "datetime"
}
```

### Conversation Structure
```json
{
  "id": "uuid",
  "user_id": "uuid", 
  "agent_type": "string",
  "title": "string",
  "context_data": {},
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime",
  "last_message_at": "datetime"
}
```

## Flutter App Analysis Questions

### Use this checklist to analyze your Flutter app:

#### 1. **API Client Updates Needed?**
- [ ] Update base URLs to new endpoint structure
- [ ] Update authentication headers (Bearer token)
- [ ] Handle new response formats
- [ ] Add error handling for new error structure

#### 2. **Authentication Flow Changes?**
- [ ] Update login/register UI for new request format
- [ ] Implement JWT token storage and refresh
- [ ] Update logout functionality
- [ ] Handle token expiration (30 min)

#### 3. **Chat Interface Updates?**
- [ ] Update chat request format (agent_type + message)
- [ ] Handle new response fields (conversation_id, timestamp)
- [ ] Implement crisis detection UI/alerts
- [ ] Add agent selection interface
- [ ] Display conversation history

#### 4. **New Features to Implement?**
- [ ] Crisis detection alerts and resources
- [ ] Agent status indicators
- [ ] Conversation history screen
- [ ] Agent memory management (clear memory option)
- [ ] Enhanced error messages

#### 5. **Data Models to Update?**
- [ ] User model (new fields)
- [ ] Chat message model (new fields)
- [ ] Conversation model (new structure)
- [ ] Agent model (capabilities, status)

#### 6. **Performance & UX Improvements?**
- [ ] Implement response time monitoring
- [ ] Add loading states for longer operations
- [ ] Handle network errors gracefully
- [ ] Add retry mechanisms for failed requests

## Backward Compatibility

### ⚠️ Breaking Changes That Require Flutter Updates:
1. **Endpoint URLs changed** - Must update API client
2. **Authentication method** - JWT vs previous method
3. **Response formats** - May need model updates
4. **Error handling** - New error structure

### ✅ Safe Changes (Likely No Flutter Updates Needed):
1. Internal architecture changes (Clean Architecture)
2. Database optimizations
3. Health monitoring endpoints
4. Enhanced logging

## Testing Recommendations

1. **Test against new backend** with old Flutter app first
2. **Update API client** incrementally
3. **Test authentication flow** thoroughly
4. **Verify all existing features** still work
5. **Test error scenarios** (network failures, token expiry)

## Migration Priority

### High Priority (App Won't Work Without These):
1. Update API endpoint URLs
2. Fix authentication (JWT tokens)
3. Update request/response models

### Medium Priority (Enhanced Functionality):
1. Implement crisis detection UI
2. Add conversation history
3. Agent selection interface

### Low Priority (Nice to Have):
1. Health monitoring integration
2. Performance metrics display
3. Advanced error handling UI

Use this information to audit your Flutter app and determine what needs updating! 