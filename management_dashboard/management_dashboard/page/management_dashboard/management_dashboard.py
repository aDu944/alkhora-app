import frappe
from frappe import _


def get_context(context):
	"""Context for Management Dashboard page."""
	context.no_cache = 1
	context.show_sidebar = False
	
	# Get user's default company
	company = frappe.defaults.get_user_default("Company")
	if not company:
		companies = frappe.get_all("Company", limit=1)
		if companies:
			company = companies[0].name
	
	context.company = company
	context.current_year = frappe.utils.now_datetime().year
