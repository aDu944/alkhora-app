from frappe import _


def get_data():
	return [
		{
			"module_name": "Management Dashboard",
			"type": "module",
			"label": _("Management Dashboard"),
			"color": "#4F46E5",
			"icon": "octicon octicon-graph",
			"description": _("Annual management KPIs dashboard"),
		}
	]

