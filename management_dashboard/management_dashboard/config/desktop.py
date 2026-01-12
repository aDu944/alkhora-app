from frappe import _


def get_data():
	return [
		{
			"module_name": "Management Dashboard",
			"color": "#4F46E5",
			"icon": "octicon octicon-graph",
			"type": "module",
			"label": _("Management Dashboard"),
			"link": "page/management_dashboard",
		}
	]
