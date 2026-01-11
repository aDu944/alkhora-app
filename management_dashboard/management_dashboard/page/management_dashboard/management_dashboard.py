import frappe


def get_context(context):
	# Desk Page context is typically not required; UI is built in JS.
	context.no_cache = 1

