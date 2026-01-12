app_name = "management_dashboard"
app_title = "ALKHORA"
app_publisher = "ALKHORA"
app_description = "ALKHORA Company App - Custom ERPNext extensions and workspaces for ALKHORA"
app_email = "support@alkhora.com"
app_license = "MIT"
app_version = "1.0.0"

# ERPNext is required for the doctypes used by the app
required_apps = ["erpnext"]

# App icon
app_icon = "octicon octicon-briefcase"

# Workspaces
workspaces = [
	{
		"module_name": "management_dashboard",
		"type": "module",
		"label": "Management Dashboard",
		"color": "#4F46E5",
		"icon": "octicon octicon-graph",
		"description": "Annual management KPIs dashboard",
	}
]

# Asset hooks - minimal JS file for build system
app_include_css = []
app_include_js = ["public/js/management_dashboard.js"]
