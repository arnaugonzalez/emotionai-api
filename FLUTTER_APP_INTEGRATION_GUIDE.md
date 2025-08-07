# EmotionAI Flutter App Integration Guide

## 🚀 Backend Changes & Frontend Integration Requirements

This document outlines the backend changes that have been implemented and the corresponding updates required in the Flutter app to support the new intelligent tagging system, enhanced data models, and improved user experience.

---

## 📊 Database Schema Enhancements

### 🏷️ **Intelligent Tagging System**
All major entities now support semantic tagging:

```json
{
  "tags": ["stress_relief", "work_anxiety", "breathing_helped"],
  "tag_confidence": 0.85,
  "processed_for_tags": true
}
```

**Flutter Requirements:**
- Display tags as chips/badges in UI
- Color-code tags by category (emotional, behavioral, contextual)
- Implement tag-based filtering and search
- Show tag confidence levels in analytics

### 👤 **Enhanced User Model**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "Alex",
  "last_name": "Johnson",
  "agent_personality_data": {
    "preferred_agent_type": "therapist",
    "communication_style": "supportive"
  },
  "user_profile_data": {
    "timezone": "America/New_York",
    "language": "en",
    "experience_level": "intermediate"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "last_login_at": "2024-01-01T12:00:00Z"
}
```

**Flutter Requirements:**
- Update user profile UI to include agent preferences
- Add timezone and language settings
- Display experience level in onboarding/settings

---

## 🫁 Enhanced Breathing Sessions

### **New Fields Added:**
```json
{
  "pattern_name": "4-7-8 Breathing",
  "duration_minutes": 10,
  "effectiveness_rating": 4,
  "session_data": {
    "inhale_duration": 4,
    "hold_duration": 7,
    "exhale_duration": 8,
    "cycles_completed": 8
  },
  "tags": ["relaxation", "sleep_preparation"],
  "tag_confidence": 0.9,
  "started_at": "2024-01-01T10:00:00Z",
  "completed_at": "2024-01-01T10:10:00Z"
}
```

**Flutter Requirements:**
- ✅ **Upgrade Session Tracking**: Track start/end times separately
- ✅ **Enhanced Analytics**: Show detailed session metrics (cycles, timing)
- ✅ **Tag Display**: Show auto-generated tags for each session
- ✅ **Effectiveness Rating**: Replace simple rating with 1-5 effectiveness scale
- ✅ **Session Insights**: Display patterns and recommendations based on tags

---

## 😊 Enhanced Emotional Records

### **New Structure:**
```json
{
  "emotion": "anxious",
  "intensity": 7,
  "triggers": ["work_deadline", "presentation"],
  "notes": "Big presentation tomorrow. Feeling nervous.",
  "context_data": {
    "location": "office",
    "weather": "sunny",
    "energy_level": 7
  },
  "tags": ["work_stress", "presentation_anxiety"],
  "recorded_at": "2024-01-01T15:30:00Z"
}
```

**Flutter Requirements:**
- ✅ **Triggers Array**: Allow multiple trigger selection
- ✅ **Context Capture**: Add location, weather, energy level inputs
- ✅ **Tag Visualization**: Show suggested and auto-generated tags
- ✅ **Enhanced Timeline**: Group records by tags and patterns

---

## 👤 User Profile & Analytics

### **New User Profile Structure:**
```json
{
  "frequent_tags": {
    "stress_relief": 15,
    "work_stress": 12,
    "breathing_exercises": 10
  },
  "tag_categories": {
    "emotional": ["anxiety_relief", "stress_relief"],
    "behavioral": ["breathing_exercises", "meditation"],
    "contextual": ["work_stress", "family_support"]
  },
  "personality_insights": {
    "stress_triggers": ["work_deadlines", "public_speaking"],
    "coping_mechanisms": ["breathing_exercises", "nature_walks"],
    "improvement_areas": ["time_management", "sleep_hygiene"]
  },
  "behavioral_patterns": {
    "breathing_session_preferences": {
      "preferred_duration": "10-15 minutes",
      "most_effective_pattern": "4-7-8 breathing"
    }
  }
}
```

**Flutter Requirements:**
- ✅ **Analytics Dashboard**: Create comprehensive insights screen
- ✅ **Tag Clouds**: Visual representation of frequent tags
- ✅ **Pattern Recognition**: Display behavioral patterns and trends
- ✅ **Personalized Recommendations**: Show AI-generated insights
- ✅ **Progress Tracking**: Visualize improvement metrics

---

## 🎯 Required Flutter App Changes

### 🚨 **Priority 1: Critical Updates**

#### 1. **Data Model Updates**
```dart
// Update existing models
class BreathingSession {
  final String id;
  final String patternName;
  final int durationMinutes;
  final int? effectivenessRating; // Changed from rating
  final Map<String, dynamic>? sessionData; // New field
  final List<String> tags; // New field
  final double? tagConfidence; // New field
  final DateTime startedAt;
  final DateTime? completedAt;
}

class EmotionalRecord {
  final String id;
  final String emotion;
  final int intensity;
  final List<String> triggers; // Changed from single trigger
  final Map<String, dynamic>? contextData; // New field
  final List<String> tags; // New field
  final DateTime recordedAt; // Separate from created_at
}
```

#### 2. **API Integration Updates**
```dart
// Update API calls to handle new fields
class ApiService {
  Future<List<BreathingSession>> getBreathingSessions() async {
    // Handle new fields: tags, session_data, effectiveness_rating
  }
  
  Future<UserProfile> getUserProfile() async {
    // Handle personality_insights, behavioral_patterns
  }
}
```

### 🔄 **Priority 2: UI Enhancements**

#### 1. **Tag System UI Components**
```dart
// Create reusable tag components
class TagChip extends StatelessWidget {
  final String tag;
  final TagCategory category;
  final double? confidence;
}

class TagFilter extends StatefulWidget {
  final List<String> availableTags;
  final Function(List<String>) onTagsSelected;
}
```

#### 2. **Enhanced Session Recording**
```dart
// Update breathing session UI
class BreathingSessionScreen {
  // Add session metrics tracking
  // Show real-time tag suggestions
  // Display effectiveness rating instead of simple rating
}
```

#### 3. **Analytics Dashboard**
```dart
class AnalyticsDashboard extends StatelessWidget {
  // Tag frequency charts
  // Behavioral pattern insights
  // Personalized recommendations
  // Progress tracking visualizations
}
```

### 📱 **Priority 3: New Features**

#### 1. **Smart Insights Screen**
- Display AI-generated personality insights
- Show stress triggers and coping mechanisms
- Provide personalized recommendations
- Track improvement areas

#### 2. **Enhanced Filtering & Search**
- Tag-based filtering for all data views
- Semantic search using tag relationships
- Context-aware data grouping

#### 3. **Improved Onboarding**
- Collect agent personality preferences
- Set timezone and language preferences
- Explain intelligent tagging system

---

## 🔧 Technical Implementation Notes

### **Database Connection Testing**
Use the test data we've created to validate your app:

```json
{
  "email": "test@emotionai.com",
  "password": "testpass123"
}
```

This test user includes:
- 5 breathing sessions with varied patterns and effectiveness ratings
- 8 emotional records with triggers, context, and tags
- Complete user profile with insights and behavioral patterns
- Tag semantic relationships for smart suggestions

### **API Endpoints to Test**
```bash
# Test with real data
GET /api/data/emotional_records/
GET /api/data/breathing_sessions/
GET /api/users/profile/
GET /api/data/user_analytics/

# New endpoints for tags
GET /api/tags/frequent?user_id={id}
GET /api/tags/categories
GET /api/analytics/insights?user_id={id}
```

### **Migration Strategy**
1. **Phase 1**: Update data models and API calls
2. **Phase 2**: Add tag display and basic filtering
3. **Phase 3**: Implement analytics dashboard
4. **Phase 4**: Add smart insights and recommendations

---

## 🎨 UI/UX Recommendations

### **Tag Visualization**
- Use color-coded chips for different tag categories:
  - 🟦 **Emotional**: Blue (anxiety_relief, stress_relief)
  - 🟩 **Behavioral**: Green (breathing_exercises, meditation)
  - 🟨 **Contextual**: Yellow (work_stress, family_support)
  - 🟪 **Environmental**: Purple (outdoor_activity, nature_therapy)

### **Analytics Visualizations**
- **Tag Clouds**: Show frequent tags with size indicating frequency
- **Pattern Charts**: Line charts showing emotional/behavioral trends
- **Heatmaps**: Activity patterns by day/time
- **Progress Indicators**: Show improvement in specific areas

### **Smart Recommendations**
```dart
class SmartRecommendation {
  final String title;
  final String description;
  final List<String> basedOnTags;
  final String actionType; // breathing, journaling, etc.
  final int confidence;
}
```

---

## 🧪 Testing Checklist

### **Data Integration Tests**
- [ ] Breathing sessions load with new fields
- [ ] Emotional records display triggers and context
- [ ] Tags appear correctly across all views
- [ ] User profile shows insights and patterns

### **UI Component Tests**
- [ ] Tag chips render with correct colors
- [ ] Filtering works with tag selection
- [ ] Navigation between tagged content works
- [ ] Analytics dashboard displays correctly

### **API Integration Tests**
- [ ] All endpoints return expected data structure
- [ ] Error handling for missing fields
- [ ] Offline data caching includes new fields
- [ ] Sync process handles schema changes

---

## 🚀 Next Steps

1. **Review this document** with the Flutter development team
2. **Update data models** to match new backend schema
3. **Test API integration** with the provided test user
4. **Implement UI changes** in phases as outlined
5. **Validate against test data** to ensure compatibility

## 📞 Support

For questions about the backend changes or integration issues:
- **Database Schema**: Check `src/infrastructure/database/models.py`
- **API Endpoints**: Check `src/presentation/api/routers/`
- **Test Data**: Use `create_test_data.py` to generate sample data
- **DTOs**: Check `src/application/dtos/chat_dtos.py` for API contracts

---

*Last Updated: January 2024*  
*Backend Version: 2.0.0 with Intelligent Tagging System*