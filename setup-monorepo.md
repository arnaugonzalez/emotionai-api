# EmotionAI Monorepo Setup Guide

## Recommended Directory Structure:

```
emotionai/
├── backend/                  # Your current API project
│   ├── src/
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── ...
├── frontend/                 # Flutter app
│   ├── lib/
│   ├── pubspec.yaml
│   └── ...
├── shared/                   # Shared documentation and configs
│   ├── docs/
│   ├── API_CONTRACTS.md
│   └── README.md
├── .vscode/                  # Shared VSCode settings
│   ├── settings.json
│   ├── tasks.json
│   └── extensions.json
└── README.md
```

## Setup Commands:

```bash
# Create the monorepo structure
mkdir emotionai
cd emotionai

# Move your existing projects
mv /path/to/emotionai-api backend
mv /path/to/emotionai-app frontend

# Create shared directory
mkdir shared
mkdir .vscode
```

## Root-level Configuration Files:

### .vscode/settings.json:
```json
{
    "python.defaultInterpreterPath": "./backend/venv/bin/python",
    "dart.flutterSdkPath": null,
    "files.associations": {
        "*.py": "python",
        "*.dart": "dart"
    },
    "search.exclude": {
        "**/node_modules": true,
        "**/build": true,
        "**/.dart_tool": true,
        "**/__pycache__": true,
        "**/venv": true
    }
}
```

### .vscode/tasks.json:
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Backend: Start Services",
            "type": "shell",
            "command": "docker-compose up -d",
            "options": {
                "cwd": "${workspaceFolder}/backend"
            }
        },
        {
            "label": "Backend: Create Test Data",
            "type": "shell", 
            "command": "docker-compose exec api python create_test_data.py",
            "options": {
                "cwd": "${workspaceFolder}/backend"
            }
        },
        {
            "label": "Frontend: Run App",
            "type": "shell",
            "command": "flutter run",
            "options": {
                "cwd": "${workspaceFolder}/frontend"
            }
        },
        {
            "label": "Full Stack: Start All",
            "dependsOrder": "sequence",
            "dependsOn": [
                "Backend: Start Services",
                "Frontend: Run App"
            ]
        }
    ]
}
```