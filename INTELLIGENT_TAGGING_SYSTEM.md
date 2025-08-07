# Intelligent Tagging System

## Overview

The EmotionAI API has been completely redesigned to focus on intelligent user knowledge management through semantic tagging. This system replaces the crisis detection approach with a comprehensive tagging system that builds personalized user profiles and enables intelligent content discovery.

## Key Features

### 🏷️ Semantic Tag Extraction
- **LLM-Powered Analysis**: Uses OpenAI GPT-4o-mini to extract meaningful tags from all user content
- **Multi-Category Tagging**: Categorizes tags into emotional, behavioral, contextual, coping, physical, social, and temporal groups
- **Confidence Scoring**: Each tag extraction includes confidence scores for reliability assessment
- **Context-Aware**: Considers user history and context for more accurate tagging

### 🧠 User Knowledge Profiles
- **Aggregated Insights**: Builds comprehensive user profiles from accumulated tag data
- **Behavioral Pattern Detection**: Identifies patterns in user behavior and emotional states
- **Preference Learning**: Learns user preferences for coping strategies and interventions
- **Trend Analysis**: Tracks changes in user patterns over time

### 🔍 Intelligent Content Discovery
- **Similarity Search**: Finds similar past experiences based on semantic tag matching
- **Effective Strategy Identification**: Discovers which coping strategies worked well in similar situations
- **Temporal Pattern Analysis**: Identifies time-based patterns in user behavior
- **Personalized Recommendations**: Provides contextually relevant suggestions

### 📊 Enhanced Personalization
- **Tag-Based Context Building**: Uses historical tags to build rich context for agent interactions
- **Dynamic Adaptation**: Agent responses adapt based on user's evolving tag patterns
- **Proactive Insights**: System proactively identifies trends and provides insights

## System Architecture

### Database Schema Updates

#### Enhanced Models with Tagging Support

**MessageModel** - Chat messages with semantic tags
```sql
- tags (JSONB): Extracted semantic tags
- tag_confidence (FLOAT): Confidence in tag extraction
- processed_for_tags (BOOLEAN): Processing status
- GIN indexes for fast tag-based queries
```

**EmotionalRecordModel** - Emotional records with context tags
```sql
- tags (JSONB): Emotional and situational tags
- tag_confidence (FLOAT): Tag extraction confidence
- processed_for_tags (BOOLEAN): Processing status
```

**BreathingSessionModel** - Breathing sessions with activity tags
```sql
- tags (JSONB): Session context and effectiveness tags
- tag_confidence (FLOAT): Confidence score
- processed_for_tags (BOOLEAN): Processing status
```

#### New Models for Knowledge Management

**UserProfileModel** - Aggregated user insights
```sql
- frequent_tags (JSONB): Most common user tags with frequencies
- tag_categories (JSONB): Categorized tag groupings
- tag_trends (JSONB): Tag usage trends over time
- personality_insights (JSONB): LLM-generated personality insights
- behavioral_patterns (JSONB): Detected behavioral patterns
- preferences (JSONB): User preferences for activities/strategies
```

**TagSemanticModel** - Tag relationships and similarities
```sql
- tag (STRING): Primary tag
- category (STRING): Tag category (emotional, behavioral, etc.)
- similar_tags (JSONB): Related tags with similarity scores
- synonyms (JSONB): Synonym tags
- related_concepts (JSONB): Related concepts from LLM analysis
```

### Service Architecture

#### Core Services

**ITaggingService** - Semantic tag extraction interface
- `extract_tags_from_message()`: Extract tags from chat messages
- `extract_tags_from_emotional_record()`: Process emotional records
- `extract_tags_from_breathing_session()`: Analyze breathing sessions
- `categorize_tags()`: Group tags by semantic categories
- `find_similar_tags()`: Discover related tags

**OpenAITaggingService** - OpenAI-powered implementation
- Uses specialized system prompts for different content types
- Implements fallback strategies for API failures
- Provides structured JSON responses with categories and insights

**IUserKnowledgeService** - User profile management interface
- `update_user_profile_with_tags()`: Update profiles with new tag data
- `get_personalization_context()`: Build context for agent interactions
- `generate_user_insights()`: Create new insights from patterns
- `get_wellness_recommendations()`: Provide personalized suggestions
- `analyze_behavioral_patterns()`: Detect behavior patterns

**ISimilaritySearchService** - Content discovery interface
- `find_similar_content()`: Locate similar past experiences
- `find_similar_emotional_patterns()`: Match emotional states
- `find_effective_coping_strategies()`: Identify successful interventions
- `calculate_tag_similarity()`: Compute tag similarity scores
- `cluster_user_experiences()`: Group related experiences

### Updated Use Cases

**AgentChatUseCase** - Redesigned for intelligent tagging
1. **Tag Extraction**: Extract semantic tags from user messages
2. **Context Building**: Build rich context using user knowledge and similar experiences
3. **Agent Interaction**: Process with enhanced personalized context
4. **Knowledge Update**: Update user profile with new insights
5. **Event Publishing**: Publish tagging and profile update events

## Benefits of the New System

### For Users
- **More Personalized Responses**: Agent responses are tailored to individual patterns and preferences
- **Better Understanding**: System learns from past interactions to provide more relevant help
- **Proactive Insights**: Receive insights about patterns and trends in their mental health journey
- **Contextual Recommendations**: Get suggestions based on what actually worked before

### For Future Development
- **Scalable Knowledge Base**: Tag-based system scales naturally with user data growth
- **Analytics Foundation**: Rich tagging data enables powerful analytics and insights
- **Recommendation Engine**: Tag patterns enable sophisticated recommendation algorithms
- **Research Insights**: Anonymized tag patterns can provide mental health research insights

### For System Architecture
- **PostgreSQL Optimization**: JSONB and GIN indexes provide excellent performance for tag queries
- **Clean Separation**: Clear interfaces between tagging, knowledge management, and similarity search
- **Event-Driven**: Tag processing and profile updates are event-driven for scalability
- **Extensible**: Easy to add new tag categories or processing algorithms

## Implementation Status

### ✅ Completed Components
- Database schema with JSONB tagging support
- Service interfaces for tagging, knowledge management, and similarity search
- OpenAI-powered tagging service implementation
- Updated agent chat use case with intelligent context building
- Domain events for tag processing and profile updates
- Exception handling for new service types

### 🔄 Ready for Implementation
- Service implementations for user knowledge and similarity search
- Repository implementations for new database models
- Container configuration for dependency injection
- Alembic migrations for database schema updates

### 🚀 Future Enhancements
- Machine learning models for improved tag similarity
- Advanced clustering algorithms for experience grouping
- Real-time tag processing pipelines
- Analytics dashboards for user insights
- Mobile app integration for tag-based features

## Database Choice Evaluation

**Decision: PostgreSQL with JSONB** ✅

**Rationale:**
- **JSONB Performance**: Native JSON support with indexing capabilities
- **GIN Indexes**: Excellent performance for tag-based queries
- **ACID Compliance**: Maintains data consistency for user profiles
- **Relational Benefits**: Still maintains relational integrity for core entities
- **Mature Ecosystem**: Well-established tooling and optimization techniques

**Advantages over NoSQL:**
- **Complex Queries**: Can perform complex joins between tagged data and user entities
- **Consistency Guarantees**: ACID transactions ensure data integrity
- **Proven Scalability**: PostgreSQL scales well for this use case size
- **Tool Compatibility**: Works with existing SQL-based tools and ORMs

## Migration Guide

### Environment Variables
Update your `.env` file:
```bash
# Remove this line:
# ANTHROPIC_API_KEY=your_anthropic_key

# Ensure this is set:
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_LLM_MODEL=gpt-4o-mini
```

### Database Migration
Run the new migration to add tagging support:
```bash
python manage_db.py new-migration "add_intelligent_tagging_system"
python manage_db.py migrate
```

### Container Updates
The dependency injection container will need updates to wire the new services (implementation pending based on your specific container setup).

## Usage Examples

### Tag Extraction
```python
# Extract tags from user message
tag_result = await tagging_service.extract_tags_from_message(
    content="I'm feeling anxious about my work presentation tomorrow",
    user_context=user_context
)
# Results in tags like: ["work_anxiety", "presentation_stress", "anticipatory_worry"]
```

### Context Building
```python
# Build intelligent context for agent
context = await use_case._build_intelligent_context(user, request, tag_result)
# Includes: similar experiences, effective strategies, behavioral patterns, trends
```

### Similarity Search
```python
# Find similar past experiences
similar = await similarity_service.find_similar_content(
    user_id=user.id,
    reference_tags=["work_anxiety", "presentation_stress"],
    content_types=["message", "emotional_record"],
    limit=5
)
```

This intelligent tagging system transforms the EmotionAI API into a truly personalized mental health companion that learns from each interaction and provides increasingly relevant support over time.