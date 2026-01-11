app_name = "management_dashboard"
app_title = "ALKHORA"
app_publisher = "ALKHORA"
app_description = "ALKHORA Company App - Custom ERPNext extensions and workspaces for ALKHORA"
app_email = "support@alkhora.co"
app_license = "MIT"
app_version = "1.0.0"

# ERPNext is required for the doctypes used by the app.
required_apps = ["erpnext"]

# App icon
app_icon = "octicon octicon-briefcase"

# Workspaces
from management_dashboard.management_dashboard.config.desktop import get_data as get_workspace_data

workspaces = get_workspace_data()

