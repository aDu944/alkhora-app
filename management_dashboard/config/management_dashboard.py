from frappe import _


def get_data():
	return [
		{
			"label": _("Dashboard"),
			"items": [
				{"type": "page", "name": "management_dashboard", "label": _("Management Dashboard")},
			],
		}
	]

