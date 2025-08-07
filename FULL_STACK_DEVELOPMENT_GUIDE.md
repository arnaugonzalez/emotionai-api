# 🚀 EmotionAI Full-Stack Development Guide

## Working with Both API and Flutter App in Cursor Agent Mode

This guide shows you how to efficiently work with both the EmotionAI API (backend) and Flutter app (frontend) simultaneously in Cursor's Agent mode.

---

## 🎯 Quick Start (Recommended)

### Option 1: Multi-Root Workspace

1. **Open the workspace file:**
   ```bash
   cursor emotionai-workspace.code-workspace
   ```

2. **Start development environment:**
   ```bash
   # On macOS/Linux
   ./dev-scripts.sh setup

   # On Windows
   .\dev-scripts.ps1 setup
   ```

3. **You're ready!** Both projects are now accessible in Cursor with:
   - ✅ Cross-project search and navigation
   - ✅ Unified Agent mode across both codebases
   - ✅ Shared tasks and debugging
   - ✅ Coordinated development workflow

---

## 🏗️ Setup Options

### Option 1: Multi-Root Workspace (Best for existing separate projects)

**Pros:**
- ✅ Keep existing project structures
- ✅ Independent git repositories
- ✅ Easy to set up
- ✅ Full Cursor Agent support across both projects

**Setup:**
```bash
# 1. Use the provided workspace file
cursor emotionai-workspace.code-workspace

# 2. Adjust paths in the workspace file if needed
# 3. Install recommended extensions when prompted
```

### Option 2: Monorepo Structure (Best for new projects or restructuring)

**Pros:**
- ✅ Single repository for everything
- ✅ Shared tooling and CI/CD
- ✅ Easier dependency management
- ✅ Better for large teams

**Setup:**
```bash
# Follow the guide in setup-monorepo.md
mkdir emotionai-monorepo
# Move projects as described in the guide
```

### Option 3: Side-by-Side Directories (Simple approach)

**Pros:**
- ✅ Very simple setup
- ✅ Works with any IDE/editor
- ✅ Flexible project organization

**Setup:**
```bash
# Just organize your folders like this:
projects/
├── emotionai-api/
└── emotionai-app/

# Then open the parent directory in Cursor
cursor projects/
```

---

## 🛠️ Development Workflow

### Daily Development Routine

1. **Start your development session:**
   ```bash
   # Quick setup (backend + test data)
   ./dev-scripts.sh setup
   
   # Or step by step:
   ./dev-scripts.sh start    # Start backend
   ./dev-scripts.sh data     # Create test data
   ./dev-scripts.sh flutter  # Start Flutter app
   ```

2. **Use Cursor Agent across both projects:**
   - Press `Ctrl+Shift+P` → "Cursor: Chat with AI"
   - Reference files from both projects: `@backend/src/main.py` and `@frontend/lib/main.dart`
   - Ask for cross-project changes: "Update the API endpoint in the backend and the corresponding call in the Flutter app"

3. **Make coordinated changes:**
   ```
   Agent Prompt Examples:
   
   "Add a new field 'mood_rating' to the emotional record model in the backend 
   and update the Flutter UI to capture this field"
   
   "Update the breathing session API to include tags, then modify the Flutter 
   app to display these tags as chips"
   
   "Fix the authentication flow in both the FastAPI backend and Flutter frontend"
   ```

### Useful Development Commands

```bash
# Backend operations
docker-compose up -d                    # Start backend services
docker-compose exec api python create_test_data.py  # Add test data
docker-compose logs api --tail=50       # View API logs
docker-compose restart api              # Restart API after code changes

# Flutter operations  
flutter run                             # Start Flutter app
flutter pub get                         # Install dependencies
flutter clean && flutter pub get       # Clean rebuild

# Combined operations
./dev-scripts.sh status                 # Check all services
./dev-scripts.sh stop                   # Stop all backend services
```

---

## 🤖 Cursor Agent Mode Tips

### Best Practices for Cross-Project Development

1. **Use descriptive file references:**
   ```
   ❌ "Update the model"
   ✅ "Update the EmotionalRecord model in @backend/src/infrastructure/database/models.py 
       and the corresponding Dart model in @frontend/lib/models/emotional_record.dart"
   ```

2. **Leverage workspace-wide search:**
   - `Ctrl+Shift+F` searches across both projects
   - Use patterns like `class.*Record` to find related files

3. **Coordinate API changes:**
   ```
   Agent Prompt Template:
   "I need to add a new field 'tags' to emotional records:
   1. Update the database model in the backend
   2. Update the API endpoints to handle tags
   3. Update the Flutter model and UI to display tags
   4. Update the test data to include sample tags"
   ```

4. **Use the integration guide:**
   - Reference `FLUTTER_APP_INTEGRATION_GUIDE.md` for API changes
   - Keep both projects in sync with schema changes

### Agent Mode Workflow Examples

**Example 1: Adding a new feature**
```
Prompt: "I want to add a 'favorite breathing patterns' feature:

Backend changes needed:
- Add a favorites field to the user model
- Create API endpoints to manage favorites
- Update the breathing patterns response to include favorite status

Frontend changes needed:
- Add a heart icon to breathing pattern cards
- Implement tap-to-favorite functionality  
- Filter to show only favorite patterns
- Update the user preferences screen

Please implement this across both projects."
```

**Example 2: Fixing a bug across projects**
```
Prompt: "The emotional record timestamps are inconsistent between backend and frontend:
- Backend stores in UTC but frontend displays in local time incorrectly
- Check @backend/src/infrastructure/database/models.py EmotionalRecordModel
- Check @frontend/lib/services/api_service.dart timestamp parsing
- Fix the timezone handling in both projects"
```

---

## 📁 Project Structure in Cursor

When using the workspace, your Cursor sidebar will show:

```
EMOTIONAI WORKSPACE
├── 📁 EmotionAI API (Backend)
│   ├── 📁 src/
│   │   ├── 📁 application/
│   │   ├── 📁 domain/
│   │   ├── 📁 infrastructure/
│   │   └── 📁 presentation/
│   ├── 📄 docker-compose.yml
│   ├── 📄 create_schema.py
│   └── 📄 create_test_data.py
└── 📁 EmotionAI App (Flutter)
    ├── 📁 lib/
    │   ├── 📁 models/
    │   ├── 📁 services/
    │   ├── 📁 screens/
    │   └── 📁 widgets/
    ├── 📁 test/
    └── 📄 pubspec.yaml
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

**Issue: "Cannot find Flutter project"**
```bash
# Check the path in your workspace file
# Update FRONTEND_DIR in dev-scripts
```

**Issue: "Backend services not responding"**
```bash
# Check Docker status
docker-compose ps
docker-compose logs api

# Restart services
./dev-scripts.sh stop
./dev-scripts.sh start
```

**Issue: "Agent mode not seeing both projects"**
```bash
# Make sure you opened the workspace file, not individual folders
cursor emotionai-workspace.code-workspace

# Verify both folders are visible in the sidebar
```

**Issue: "Test data not loading"**
```bash
# Recreate test data
./dev-scripts.sh data

# Or manually:
docker-compose exec api python create_test_data.py
```

---

## 🎯 Advanced Tips

### Custom Cursor Configuration

Add to your workspace settings:
```json
{
    "cursor.aiMode": "enabled",
    "cursor.contextWindow": "large",
    "files.associations": {
        "*.py": "python",
        "*.dart": "dart",
        "docker-compose*.yml": "yaml"
    },
    "search.followSymlinks": false,
    "search.useGlobalIgnoreFiles": true
}
```

### Keyboard Shortcuts for Full-Stack Development

- `Ctrl+Shift+P` → "Cursor: Chat with AI" (Agent mode)
- `Ctrl+P` → Quick file search across both projects  
- `Ctrl+Shift+F` → Global search across both projects
- `Ctrl+Shift+E` → Focus on Explorer (switch between projects)
- `Ctrl+`` → Terminal (run dev scripts)

### Integration Testing Workflow

1. Start backend: `./dev-scripts.sh start`
2. Create test data: `./dev-scripts.sh data`
3. Run Flutter in one terminal: `./dev-scripts.sh flutter`
4. Use Cursor Agent to make coordinated changes
5. Test changes in real-time

---

## 📞 Need Help?

- **API Documentation**: Check the OpenAPI docs at http://localhost:8000/docs
- **Flutter Integration**: Review `FLUTTER_APP_INTEGRATION_GUIDE.md`
- **Test Data**: Use credentials `test@emotionai.com` / `testpass123`
- **Development Scripts**: Run `./dev-scripts.sh` for help menu

---

**Happy Full-Stack Development with Cursor! 🚀**