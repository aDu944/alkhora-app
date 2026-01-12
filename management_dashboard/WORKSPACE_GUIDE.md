# Adding New Workspaces to ALKHORA App

This guide explains how to add new workspaces/modules to the ALKHORA app.

## What is a Workspace?

A workspace is a self-contained module within the ALKHORA app that provides specific functionality. Each workspace can have:
- Custom pages
- API endpoints
- Custom doctypes
- Reports
- Desktop shortcuts
- Permissions and roles

## Step-by-Step Guide

### 1. Plan Your Workspace

Decide on:
- **Name:** Short, descriptive name (e.g., "inventory_tracker", "project_management")
- **Label:** Display name (e.g., "Inventory Tracker", "Project Management")
- **Icon:** Octicon icon name (see https://octicons.github.com/)
- **Category:** Grouping category (e.g., "Operations", "Analytics", "Finance")

### 2. Create Workspace Structure

Create the necessary directories:

```bash
# From your app directory
mkdir -p management_dashboard/page/your_workspace_name
mkdir -p management_dashboard/api/your_workspace_name
mkdir -p management_dashboard/doctype/your_workspace_name  # If needed
mkdir -p management_dashboard/report/your_workspace_name   # If needed
```

### 3. Update hooks.py

Add your workspace to the `workspaces` list in `management_dashboard/hooks.py`:

```python
workspaces = [
    {
        "name": "Management Dashboard",
        "label": "Management Dashboard",
        "icon": "octicon octicon-graph",
        "description": "Annual management KPIs and analytics",
        "category": "Analytics",
    },
    {
        "name": "Your Workspace Name",
        "label": "Your Workspace Label",
        "icon": "octicon octicon-icon-name",
        "description": "Description of what this workspace does",
        "category": "Category Name",
    },
]
```

### 4. Create Desktop Configuration

Add desktop shortcuts in `management_dashboard/config/desktop.py` or create a new config file:

```python
# management_dashboard/config/your_workspace.py
from frappe import _

def get_data():
    return [
        {
            "label": _("Your Workspace"),
            "items": [
                {"type": "page", "name": "your_workspace_page", "label": _("Your Workspace Page")},
                # Add more items as needed
            ],
        }
    ]
```

Then import it in `hooks.py`:

```python
# In hooks.py, add to desktop_icons or similar hook
desktop_icons = [
    "Management Dashboard",
    "Your Workspace Name",
]
```

### 5. Update modules.txt

Add your module name to `management_dashboard/modules.txt`:

```
Management Dashboard
Your Workspace Name

```

### 6. Create Pages

Create your workspace pages in `management_dashboard/page/your_workspace_name/`:

**your_workspace_name.json:**
```json
{
  "doctype": "Page",
  "name": "your_workspace_name",
  "module": "Management Dashboard",
  "title": "Your Workspace",
  "icon": "octicon octicon-icon-name",
  "standard": "Yes",
  "roles": [
    {
      "role": "System Manager"
    }
  ]
}
```

**your_workspace_name.js:**
```javascript
frappe.pages["your_workspace_name"].on_page_load = function(wrapper) {
    // Your page implementation
};
```

### 7. Create API Endpoints (if needed)

Create API files in `management_dashboard/api/your_workspace_name/`:

```python
# management_dashboard/api/your_workspace_name/your_api.py
import frappe

@frappe.whitelist()
def get_workspace_data():
    """Your API endpoint"""
    return {"data": "your data"}
```

### 8. Create Custom Doctypes (if needed)

Use bench CLI or create manually:

```bash
bench --site <site-name> new-doctype "Your DocType"
```

Or create JSON files in `management_dashboard/doctype/your_doctype_name/`

### 9. Update Permissions

Define roles and permissions for your workspace in doctypes and pages.

### 10. Test and Deploy

1. Restart bench: `bench restart`
2. Clear cache: `bench --site <site-name> clear-cache`
3. Migrate: `bench --site <site-name> migrate`
4. Test your workspace functionality

## Example: Adding an "Inventory Tracker" Workspace

```python
# 1. Add to hooks.py workspaces
{
    "name": "Inventory Tracker",
    "label": "Inventory Tracker",
    "icon": "octicon octicon-package",
    "description": "Real-time inventory tracking and alerts",
    "category": "Operations",
}

# 2. Create directories
mkdir -p management_dashboard/page/inventory_tracker
mkdir -p management_dashboard/api/inventory_tracker

# 3. Create page files (inventory_tracker.json, inventory_tracker.js, inventory_tracker.css)
# 4. Create API files if needed
# 5. Update modules.txt
# 6. Update desktop config
# 7. Test
```

## Best Practices

1. **Naming:** Use snake_case for directory/file names, Title Case for labels
2. **Organization:** Keep workspace code in dedicated directories
3. **Documentation:** Document your workspace in README or comments
4. **Permissions:** Always define appropriate roles and permissions
5. **Testing:** Test thoroughly before deploying to production
6. **Version Control:** Commit workspace additions as separate, logical commits

## Workspace Categories

Suggested categories for organizing workspaces:
- **Analytics:** Dashboards, reports, KPIs
- **Operations:** Inventory, production, logistics
- **Finance:** Accounting, billing, payments
- **Sales:** CRM, sales tracking, customer management
- **HR:** Employee management, payroll, attendance
- **Projects:** Project management, task tracking
- **Settings:** Configuration, administration

## Need Help?

Refer to:
- Frappe Framework Documentation: https://frappeframework.com/docs
- ERPNext Documentation: https://docs.erpnext.com
- ALKHORA App README.md
