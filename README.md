# ALKHORA Company App

Custom ERPNext/Frappe application for ALKHORA company, providing specialized workspaces, dashboards, and business intelligence tools.

## Overview

This app serves as the foundation for ALKHORA's custom ERPNext extensions. It is designed to be modular and extensible, allowing new workspaces and features to be added over time.

## Current Workspaces

### 1. Management Dashboard
Comprehensive annual management dashboard with:
- Financial KPIs (Sales, Purchases, Profit, AR/AP)
- Customer health metrics
- Purchasing analytics
- HR metrics
- Custom filters and period analysis
- Export capabilities (CSV, Excel, PDF)
- RTL/Arabic support

## Installation

```bash
# Install the app
bench get-app management_dashboard /path/to/this/repo/management_dashboard

# Install on your site
bench --site <site-name> install-app management_dashboard
```

## Adding New Workspaces

To add a new workspace to this app:

1. **Create the workspace module:**
   ```bash
   bench --site <site-name> new-module "Workspace Name"
   ```

2. **Add workspace configuration** in `hooks.py`:
   ```python
   workspaces = [
       # ... existing workspaces
       {
           "name": "Your Workspace",
           "label": "Your Workspace",
           "icon": "octicon octicon-icon-name",
           "description": "Description",
           "category": "Category",
       },
   ]
   ```

3. **Create workspace pages/reports/doctypes** in the appropriate directories:
   - Pages: `management_dashboard/page/workspace_name/`
   - Reports: `management_dashboard/report/workspace_name/`
   - Doctypes: `management_dashboard/doctype/workspace_name/`
   - APIs: `management_dashboard/api/workspace_name/`

4. **Update modules.txt** to include the new module

5. **Update desktop configuration** in `management_dashboard/config/desktop.py`

## App Structure

```
management_dashboard/
├── management_dashboard/          # Main app package
│   ├── api/                       # API endpoints
│   │   └── management_dashboard/  # Management Dashboard APIs
│   ├── config/                    # App configuration
│   ├── doctype/                   # Custom doctypes
│   ├── page/                      # Custom pages
│   │   └── management_dashboard/  # Management Dashboard pages
│   ├── hooks.py                   # App hooks and configuration
│   └── modules.txt                # App modules
├── setup.py                       # Package setup
├── pyproject.toml                 # Project configuration
└── README.md                      # This file
```

## Development

### Adding New Features

1. **API Endpoints:** Add to `management_dashboard/api/`
2. **Pages:** Add to `management_dashboard/page/`
3. **Doctypes:** Use `bench new-doctype` or create manually in `management_dashboard/doctype/`
4. **Reports:** Add to `management_dashboard/report/`

### Versioning

The app follows semantic versioning:
- Major version: Breaking changes
- Minor version: New features/workspaces
- Patch version: Bug fixes

## License

MIT License - See `license.txt` for details

## Support

For support and feature requests, contact: support@alkhora.co

## Changelog

### Version 1.0.0 (Current)
- Initial release
- Management Dashboard workspace
- Comprehensive KPI analytics
- Multi-currency support
- RTL/Arabic support
- Export capabilities
