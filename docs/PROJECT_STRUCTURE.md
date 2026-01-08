# Budget Management System - Project Structure

## Directory Structure

```
MAIN_PROJECT/
├── src/                          # Main application source code
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application entry point
│   ├── database.py              # Database configuration and connection
│   ├── models.py                # SQLAlchemy database models
│   ├── schemas.py               # Pydantic schemas for API
│   ├── config.py                # Application configuration and constants
│   ├── chatbot.py               # AI chatbot functionality
│   ├── ui.py                    # UI helper functions
│   ├── excel_template_export.py # Excel export utilities
│   ├── utils_cache.py           # Caching utilities
│   ├── utils_taluka.py          # Taluka-specific utilities
│   └── routers/                 # API and UI route handlers
│       ├── __init__.py
│       ├── auth.py              # Authentication routes
│       ├── admin.py             # Admin panel routes
│       ├── messages.py          # Message handling routes
│       ├── api_assistant.py     # AI assistant API routes
│       ├── Budget_post_details.py # Budget post details API
│       ├── post_status.py       # Post status API
│       ├── post_expenses.py     # Post expenses API
│       ├── unit_expenditure.py  # Unit expenditure API
│       ├── ui_budget_details.py # Budget details UI routes
│       ├── ui_post_status.py    # Post status UI routes
│       ├── ui_post_expenses.py  # Post expenses UI routes
│       ├── ui_unit_expenditure.py # Unit expenditure UI routes
│       ├── ui_abstract.py       # District abstract UI routes
│       ├── ui_category_info.py  # Category info UI routes
│       ├── ui_budget_summary.py # Budget summary UI routes
│       └── ui_taluka_selection.py # Taluka selection UI routes
├── templates/                   # Jinja2 HTML templates
│   ├── base.html               # Base template with navigation
│   ├── login.html              # Login page
│   ├── admin_*.html            # Admin templates
│   ├── budget_*.html           # Budget-related templates
│   ├── post_*.html             # Post-related templates
│   ├── unit_*.html             # Unit expenditure templates
│   ├── district_*.html         # District abstract templates
│   └── category_*.html         # Category info templates
├── static/                     # Static files (CSS, images, JS)
│   ├── gom_logo.png           # Government logo
│   └── login.css              # Login page styles
├── excel_templates/           # Excel template files
│   ├── Budget*.xls           # Budget template files
│   └── original_template.xlsx # Original Excel template
├── deployment/               # Production deployment files
│   ├── gunicorn.conf.py     # Gunicorn configuration
│   ├── logging.conf         # Production logging config
│   ├── start.sh             # Linux/Unix startup script
│   └── start.bat            # Windows startup script
├── docs/                    # Documentation files
│   ├── README.md           # Main documentation
│   ├── README_DEPLOYMENT.md # Deployment instructions
│   └── PROJECT_STRUCTURE.md # This file
├── venv/                   # Python virtual environment
├── __pycache__/           # Python cache files
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── .gitignore            # Git ignore rules
└── DATAINSERTION.txt     # Data insertion notes

## Key Changes Made

### 1. Source Code Organization
- All application code moved to `src/` directory
- Proper Python package structure with `__init__.py` files
- Clean separation between application logic and configuration

### 2. Import Path Updates
- All imports updated to use `src.` prefix
- Consistent import structure across all modules
- Proper relative imports within the src package

### 3. Deployment Organization
- Production configuration files in `deployment/` folder
- Startup scripts updated to reference new structure
- Clean separation of development and production concerns

### 4. Documentation Structure
- All documentation consolidated in `docs/` folder
- Deployment instructions separated from main README
- Project structure documentation added

## Running the Application

### Development Mode
```bash
# From project root
python main.py
```

### Production Mode
```bash
# Linux/Unix
./deployment/start.sh

# Windows
deployment/start.bat
```

## Benefits of New Structure

1. **Clean Architecture**: Clear separation of concerns
2. **Scalability**: Easy to add new modules and features
3. **Maintainability**: Better organization for team development
4. **Production Ready**: Proper deployment configuration
5. **Professional**: Industry-standard project structure

All existing functionality remains intact with improved organization.
