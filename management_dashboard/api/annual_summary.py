from __future__ import annotations

import frappe
from frappe import _
from typing import Any, Dict, List, Optional, Tuple
import json


class Period:
	start_date: str
	end_date: str
	label: str


def _require_management_role():
	"""Require Management or System Manager role."""
	if frappe.session.user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)
	
	if "Management" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
		frappe.throw("You are not permitted to access this dashboard.", frappe.PermissionError)


def _log_dashboard_view(year: int, company: Optional[str], filters: Dict[str, Any]):
	"""Log dashboard view for audit trail."""
	try:
		if frappe.db.exists("DocType", "Dashboard View Log"):
			frappe.get_doc({
				"doctype": "Dashboard View Log",
				"user": frappe.session.user,
				"year": year,
				"company": company,
				"filters": json.dumps(filters),
			}).insert(ignore_permissions=True)
	except Exception:
		pass


def _get_user_companies() -> List[str]:
	"""Get companies from User Defaults for Management users."""
	companies = []
	try:
		# Get from User Defaults
		default_company = frappe.defaults.get_user_default("Company")
		if default_company:
			companies.append(default_company)
		
		# Also get from User Permissions if available
		user_perms = frappe.get_all(
			"User Permission",
			filters={"user": frappe.session.user, "allow": "Company"},
			fields=["for_value"]
		)
		for perm in user_perms:
			if perm.get("for_value") and perm.get("for_value") not in companies:
				companies.append(perm.get("for_value"))
	except Exception:
		pass
	return companies


def _get_default_company() -> Optional[str]:
	"""Get default company from user defaults or first available."""
	try:
		companies = _get_user_companies()
		if companies:
			return companies[0]
		return frappe.defaults.get_user_default("Company") or frappe.db.get_value("Company", {}, "name")
	except Exception:
		return None


def _get_period(year: Optional[int] = None) -> Period:
	"""Get calendar year period (01/01 to 31/12)."""
	if not year:
		year = frappe.utils.now_datetime().year
	
	period = Period()
	period.start_date = f"{year}-01-01"
	period.end_date = f"{year}-12-31"
	period.label = str(year)
	return period


def _build_filters(
	company: str,
	period: Period,
	cost_centers: Optional[List[str]] = None,
	branches: Optional[List[str]] = None,
	projects: Optional[List[str]] = None,
	customer_groups: Optional[List[str]] = None,
	supplier_groups: Optional[List[str]] = None,
	item_groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
	"""Build filters with multi-select support."""
	filters = {
		"company": company,
		"posting_date": ["between", [period.start_date, period.end_date]],
		"docstatus": 1,
	}
	
	if cost_centers:
		filters["cost_center"] = ["in", cost_centers]
	if branches:
		filters["branch"] = ["in", branches]
	if projects:
		filters["project"] = ["in", projects]
	if customer_groups:
		filters["customer_group"] = ["in", customer_groups]
	if supplier_groups:
		filters["supplier_group"] = ["in", supplier_groups]
	if item_groups:
		filters["item_group"] = ["in", item_groups]
	
	return filters


def _sum_doctype_field(
	doctype: str,
	field: str,
	filters: Dict[str, Any],
) -> float:
	"""Get sum of a field from a doctype."""
	try:
		res = frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(`{field}`), 0)
			FROM `tab{doctype}`
			WHERE company = %(company)s
				AND posting_date BETWEEN %(start_date)s AND %(end_date)s
				AND docstatus = 1
			""",
			{
				"company": filters.get("company"),
				"start_date": filters["posting_date"][1][0],
				"end_date": filters["posting_date"][1][1],
			},
		)
		return float(res[0][0] or 0) if res else 0.0
	except Exception:
		return 0.0


def _period_sums(
	doctype: str,
	value_field: str,
	date_field: str,
	filters: Dict[str, Any],
	period_type: str = "monthly",  # monthly, quarterly, weekly
) -> List[Dict[str, Any]]:
	"""Get sums grouped by period (monthly, quarterly, or weekly)."""
	condition_sql = []
	params = {
		"company": filters.get("company"),
		"start_date": filters["posting_date"][1][0],
		"end_date": filters["posting_date"][1][1],
	}
	
	for k, v in filters.items():
		if k in ["company", "posting_date", "docstatus"]:
			continue
		if isinstance(v, list) and len(v) > 1 and v[0] == "in":
			placeholders = ",".join(["%s"] * len(v[1]))
			condition_sql.append(f"`{k}` IN ({placeholders})")
			params[k] = v[1]
		elif isinstance(v, list) and len(v) > 1:
			condition_sql.append(f"`{k}` {v[0]} %({k})s")
			params[k] = v[1]
		else:
			condition_sql.append(f"`{k}` = %({k})s")
			params[k] = v
	
	where = " AND ".join(condition_sql) if condition_sql else "1=1"
	
	if period_type == "quarterly":
		select_date = "CONCAT(YEAR(`{date_field}`), '-Q', QUARTER(`{date_field}`)) AS period"
	elif period_type == "weekly":
		select_date = "CONCAT(YEAR(`{date_field}`), '-W', LPAD(WEEK(`{date_field}`, 1), 2, '0')) AS period"
	else:  # monthly
		date_format = "DATE_FORMAT(`{date_field}`, '%%Y-%%m-01')"
		group_by = "DATE_FORMAT(`{date_field}`, '%%Y-%%m')"
		order_by = "DATE_FORMAT(`{date_field}`, '%%Y-%%m')"
		select_date = "DATE_FORMAT(`{date_field}`, '%%Y-%%m-01') AS period"
	
	try:
		res = frappe.db.sql(
			f"""
			SELECT {select_date.format(date_field=date_field)},
				COALESCE(SUM(`{value_field}`), 0) AS total
			FROM `tab{doctype}`
			WHERE company = %(company)s
				AND `{date_field}` BETWEEN %(start_date)s AND %(end_date)s
				AND docstatus = 1
				AND {where}
			GROUP BY period
			ORDER BY period
			""",
			params,
			as_dict=True,
		)
		return res or []
	except Exception:
		return []


def _get_profit_loss(
	company: str,
	period: Period,
	cost_centers: Optional[List[str]] = None,
	projects: Optional[List[str]] = None,
) -> Dict[str, float]:
	"""Get P&L from GL Entries."""
	conditions = [
		"gle.company = %(company)s",
		"gle.posting_date BETWEEN %(start_date)s AND %(end_date)s",
		"gle.is_cancelled = 0",
	]
	params = {
		"company": company,
		"start_date": period.start_date,
		"end_date": period.end_date,
	}
	
	if cost_centers:
		placeholders = ",".join(["%s"] * len(cost_centers))
		conditions.append(f"gle.cost_center IN ({placeholders})")
		params["cost_centers"] = cost_centers
	
	if projects:
		placeholders = ",".join(["%s"] * len(projects))
		conditions.append(f"gle.project IN ({placeholders})")
		params["projects"] = projects
	
	where_clause = " AND ".join(conditions)
	
	income = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(gle.credit - gle.debit), 0) AS total
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where_clause}
			AND acc.root_type = 'Income'
		""",
		params,
		as_dict=True,
	)
	
	expense = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(gle.debit - gle.credit), 0) AS total
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where_clause}
			AND acc.root_type = 'Expense'
		""",
		params,
		as_dict=True,
	)
	
	income_total = float((income or [{}])[0].get("total") or 0)
	expense_total = float((expense or [{}])[0].get("total") or 0)
	
	return {
		"income": income_total,
		"expense": expense_total,
		"net_profit": income_total - expense_total,
	}


def _get_cash_bank_balances(
	company: str,
	period: Period,
	cost_centers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
	"""Get cash and bank balances."""
	accounts = frappe.get_all(
		"Account",
		filters={
			"company": company,
			"account_type": ["in", ["Cash", "Bank"]],
			"is_group": 0,
		},
		fields=["name", "account_name"],
	)
	
	if not accounts:
		return []
	
	conditions = [
		"gle.company = %(company)s",
		"gle.posting_date <= %(end_date)s",
		"gle.is_cancelled = 0",
	]
	params = {
		"company": company,
		"end_date": period.end_date,
	}
	
	if cost_centers:
		cc_placeholders = ",".join(["%s"] * len(cost_centers))
		conditions.append(f"gle.cost_center IN ({cc_placeholders})")
		params["cost_centers"] = cost_centers
	
	where_clause = " AND ".join(conditions)
	
	by_account = {}
	for a in accounts:
		balance = frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(gle.debit - gle.credit), 0) AS balance
			FROM `tabGL Entry` gle
			WHERE {where_clause}
				AND gle.account = %(account)s
			""",
			{**params, "account": a["name"]},
		)
		by_account[a["name"]] = float((balance or [[0]])[0][0] or 0)
	
	return [
		{
			"account": a["name"],
			"account_name": a["account_name"],
			"balance": float(by_account.get(a["name"], 0)),
		}
		for a in accounts
	]


def _get_ar_aging(
	company: str,
	as_of_date: str,
	cost_centers: Optional[List[str]] = None,
	projects: Optional[List[str]] = None,
	customer_groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
	"""Get AR aging buckets."""
	conditions = [
		"si.company = %(company)s",
		"si.posting_date <= %(as_of_date)s",
		"si.docstatus = 1",
		"si.outstanding_amount > 0",
	]
	params = {
		"company": company,
		"as_of_date": as_of_date,
	}
	
	if cost_centers:
		cc_placeholders = ",".join(["%s"] * len(cost_centers))
		conditions.append(f"si.cost_center IN ({cc_placeholders})")
		params["cost_centers"] = cost_centers
	
	if projects:
		prj_placeholders = ",".join(["%s"] * len(projects))
		conditions.append(f"si.project IN ({prj_placeholders})")
		params["projects"] = projects
	
	if customer_groups:
		cg_placeholders = ",".join(["%s"] * len(customer_groups))
		conditions.append(f"si.customer_group IN ({cg_placeholders})")
		params["customer_groups"] = customer_groups
	
	where_clause = " AND ".join(conditions)
	
	res = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN DATEDIFF(%(as_of_date)s, si.posting_date) <= 30 THEN si.outstanding_amount ELSE 0 END) AS bucket_0_30,
			SUM(CASE WHEN DATEDIFF(%(as_of_date)s, si.posting_date) BETWEEN 31 AND 60 THEN si.outstanding_amount ELSE 0 END) AS bucket_31_60,
			SUM(CASE WHEN DATEDIFF(%(as_of_date)s, si.posting_date) BETWEEN 61 AND 90 THEN si.outstanding_amount ELSE 0 END) AS bucket_61_90,
			SUM(CASE WHEN DATEDIFF(%(as_of_date)s, si.posting_date) > 90 THEN si.outstanding_amount ELSE 0 END) AS bucket_90_plus,
			SUM(CASE WHEN si.due_date < %(as_of_date)s AND si.outstanding_amount > 0 THEN si.outstanding_amount ELSE 0 END) AS overdue,
			SUM(si.outstanding_amount) AS total
		FROM `tabSales Invoice` si
		WHERE {where_clause}
		""",
		params,
		as_dict=True,
	)
	
	if not res:
		return {
			"0_30": 0.0,
			"31_60": 0.0,
			"61_90": 0.0,
			"90_plus": 0.0,
			"overdue": 0.0,
			"total": 0.0,
		}
	
	r = res[0]
	return {
		"0_30": float(r.get("bucket_0_30") or 0),
		"31_60": float(r.get("bucket_31_60") or 0),
		"61_90": float(r.get("bucket_61_90") or 0),
		"90_plus": float(r.get("bucket_90_plus") or 0),
		"overdue": float(r.get("overdue") or 0),
		"total": float(r.get("total") or 0),
	}


def _get_ap_aging(
	company: str,
	as_of_date: str,
	cost_centers: Optional[List[str]] = None,
	projects: Optional[List[str]] = None,
	supplier_groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
	"""Get AP aging buckets."""
	conditions = [
		"pi.company = %(company)s",
		"pi.posting_date <= %(as_of_date)s",
		"pi.docstatus = 1",
		"pi.outstanding_amount > 0",
	]
	params = {
		"company": company,
		"as_of_date": as_of_date,
	}
	
	if cost_centers:
		cc_placeholders = ",".join(["%s"] * len(cost_centers))
		conditions.append(f"pi.cost_center IN ({cc_placeholders})")
		params["cost_centers"] = cost_centers
	
	if projects:
		prj_placeholders = ",".join(["%s"] * len(projects))
		conditions.append(f"pi.project IN ({prj_placeholders})")
		params["projects"] = projects
	
	if supplier_groups:
		sg_placeholders = ",".join(["%s"] * len(supplier_groups))
		conditions.append(f"pi.supplier_group IN ({sg_placeholders})")
		params["supplier_groups"] = supplier_groups
	
	where_clause = " AND ".join(conditions)
	
	res = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN DATEDIFF(%(as_of_date)s, pi.posting_date) <= 30 THEN pi.outstanding_amount ELSE 0 END) AS bucket_0_30,
			SUM(CASE WHEN DATEDIFF(%(as_of_date)s, pi.posting_date) BETWEEN 31 AND 60 THEN pi.outstanding_amount ELSE 0 END) AS bucket_31_60,
			SUM(CASE WHEN DATEDIFF(%(as_of_date)s, pi.posting_date) BETWEEN 61 AND 90 THEN pi.outstanding_amount ELSE 0 END) AS bucket_61_90,
			SUM(CASE WHEN DATEDIFF(%(as_of_date)s, pi.posting_date) > 90 THEN pi.outstanding_amount ELSE 0 END) AS bucket_90_plus,
			SUM(CASE WHEN pi.due_date < %(as_of_date)s AND pi.outstanding_amount > 0 THEN pi.outstanding_amount ELSE 0 END) AS overdue,
			SUM(pi.outstanding_amount) AS total
		FROM `tabPurchase Invoice` pi
		WHERE {where_clause}
		""",
		params,
		as_dict=True,
	)
	
	if not res:
		return {
			"0_30": 0.0,
			"31_60": 0.0,
			"61_90": 0.0,
			"90_plus": 0.0,
			"overdue": 0.0,
			"total": 0.0,
		}
	
	r = res[0]
	return {
		"0_30": float(r.get("bucket_0_30") or 0),
		"31_60": float(r.get("bucket_31_60") or 0),
		"61_90": float(r.get("bucket_61_90") or 0),
		"90_plus": float(r.get("bucket_90_plus") or 0),
		"overdue": float(r.get("overdue") or 0),
		"total": float(r.get("total") or 0),
	}


@frappe.whitelist()
def get_annual_summary(
	year: Optional[int] = None,
	company: Optional[str] = None,
	cost_centers: Optional[str] = None,  # JSON string or list
	branches: Optional[str] = None,
	projects: Optional[str] = None,
	customer_groups: Optional[str] = None,
	supplier_groups: Optional[str] = None,
	item_groups: Optional[str] = None,
	period_type: str = "monthly",  # monthly, quarterly, weekly
	currency: Optional[str] = None,  # company or presentation
) -> Dict[str, Any]:
	"""
	Get annual summary data for management dashboard.
	
	- Shows current year and comparison with previous year
	- Restricted to role: Management or System Manager
	- Calendar year: 01/01 to 31/12
	"""
	_require_management_role()
	
	# Parse filter parameters
	def parse_filter(val):
		if isinstance(val, str):
			try:
				return json.loads(val) if val.startswith("[") else [val] if val else None
			except:
				return [val] if val else None
		return val if isinstance(val, list) else None
	
	cost_centers_list = parse_filter(cost_centers)
	branches_list = parse_filter(branches)
	projects_list = parse_filter(projects)
	customer_groups_list = parse_filter(customer_groups)
	supplier_groups_list = parse_filter(supplier_groups)
	item_groups_list = parse_filter(item_groups)
	
	# Get company - restrict to user's companies for Management role
	if company:
		user_companies = _get_user_companies()
		if user_companies and company not in user_companies:
			frappe.throw("You are not permitted to access this company.", frappe.PermissionError)
	
	company = company or _get_default_company()
	if not company:
		frappe.throw("No Company found/configured.")
	
	# Get periods: current year and previous year
	current_year = year or frappe.utils.now_datetime().year
	prev_year = current_year - 1
	
	current_period = _get_period(current_year)
	prev_period = _get_period(prev_year)
	
	# Build filters
	current_filters = _build_filters(
		company,
		current_period,
		cost_centers_list,
		branches_list,
		projects_list,
		customer_groups_list,
		supplier_groups_list,
		item_groups_list,
	)
	
	prev_filters = _build_filters(
		company,
		prev_period,
		cost_centers_list,
		branches_list,
		projects_list,
		customer_groups_list,
		supplier_groups_list,
		item_groups_list,
	)
	
	# Get company currency and presentation currency
	company_currency = frappe.db.get_value("Company", company, "default_currency") or "USD"
	presentation_currency = currency or company_currency
	
	# Get Sales Invoice totals
	sales_net_current = _sum_doctype_field("Sales Invoice", "net_total", current_filters)
	sales_net_prev = _sum_doctype_field("Sales Invoice", "net_total", prev_filters)
	sales_gross_current = _sum_doctype_field("Sales Invoice", "grand_total", current_filters)
	sales_gross_prev = _sum_doctype_field("Sales Invoice", "grand_total", prev_filters)
	
	# Get Purchase Invoice totals
	purchases_current = _sum_doctype_field("Purchase Invoice", "net_total", current_filters)
	purchases_prev = _sum_doctype_field("Purchase Invoice", "net_total", prev_filters)
	
	# Get Profit & Loss
	pl_current = _get_profit_loss(company, current_period, cost_centers_list, projects_list)
	pl_prev = _get_profit_loss(company, prev_period, cost_centers_list, projects_list)
	
	# Get Cash & Bank balances
	cash_bank = _get_cash_bank_balances(company, current_period, cost_centers_list)
	cash_total = sum(c.get("balance", 0) for c in cash_bank)
	
	# Get AR Aging
	ar_aging = _get_ar_aging(company, current_period.end_date, cost_centers_list, projects_list, customer_groups_list)
	
	# Get AP Aging
	ap_aging = _get_ap_aging(company, current_period.end_date, cost_centers_list, projects_list, supplier_groups_list)
	
	# Get customer metrics
	new_customers = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT si.customer) AS count
		FROM `tabSales Invoice` si
		LEFT JOIN (
			SELECT DISTINCT customer
			FROM `tabSales Invoice`
			WHERE posting_date < %(start_date)s
				AND docstatus = 1
		) prev_cust ON si.customer = prev_cust.customer
		WHERE si.company = %(company)s
			AND si.posting_date BETWEEN %(start_date)s AND %(end_date)s
			AND si.docstatus = 1
			AND prev_cust.customer IS NULL
		""",
		{
			"company": company,
			"start_date": current_period.start_date,
			"end_date": current_period.end_date,
		},
		as_dict=True,
	)
	new_customers_count = new_customers[0].get("count", 0) if new_customers else 0
	
	# Get top customers
	top_customers = frappe.db.sql(
		"""
		SELECT customer, SUM(net_total) AS total
		FROM `tabSales Invoice`
		WHERE company = %(company)s
			AND posting_date BETWEEN %(start_date)s AND %(end_date)s
			AND docstatus = 1
		GROUP BY customer
		ORDER BY total DESC
		LIMIT 10
		""",
		{
			"company": company,
			"start_date": current_period.start_date,
			"end_date": current_period.end_date,
		},
		as_dict=True,
	)
	
	# Get top suppliers
	top_suppliers = frappe.db.sql(
		"""
		SELECT supplier, SUM(net_total) AS total
		FROM `tabPurchase Invoice`
		WHERE company = %(company)s
			AND posting_date BETWEEN %(start_date)s AND %(end_date)s
			AND docstatus = 1
		GROUP BY supplier
		ORDER BY total DESC
		LIMIT 10
		""",
		{
			"company": company,
			"start_date": current_period.start_date,
			"end_date": current_period.end_date,
		},
		as_dict=True,
	)
	
	# Get top overdue customers
	top_overdue_customers = frappe.db.sql(
		"""
		SELECT customer, SUM(outstanding_amount) AS overdue_amount
		FROM `tabSales Invoice`
		WHERE company = %(company)s
			AND due_date < %(as_of_date)s
			AND outstanding_amount > 0
			AND docstatus = 1
		GROUP BY customer
		ORDER BY overdue_amount DESC
		LIMIT 10
		""",
		{
			"company": company,
			"as_of_date": current_period.end_date,
		},
		as_dict=True,
	)
	
	# Get HR metrics (if HRMS is installed)
	headcount = 0
	payroll_cost = 0.0
	if frappe.db.exists("DocType", "Employee"):
		headcount = frappe.db.count("Employee", {"company": company, "status": "Active"})
	
	# Open positions (Job Opening)
	open_positions = frappe.db.count("Job Opening", {"status": "Open", "company": company}) if frappe.db.exists("DocType", "Job Opening") else 0
	
	# Calculate growth percentages
	def calc_growth(current, previous):
		if previous == 0:
			return 100.0 if current > 0 else 0.0
		return ((current - previous) / previous) * 100
	
	# Log the dashboard view
	_log_dashboard_view(
		current_year,
		company,
		{
			"cost_centers": cost_centers_list,
			"branches": branches_list,
			"projects": projects_list,
			"customer_groups": customer_groups_list,
			"supplier_groups": supplier_groups_list,
			"item_groups": item_groups_list,
		},
	)
	
	return {
		"year": current_year,
		"previous_year": prev_year,
		"company": company,
		"company_currency": company_currency,
		"presentation_currency": presentation_currency,
		"period": {
			"current": {
				"start_date": current_period.start_date,
				"end_date": current_period.end_date,
				"label": current_period.label,
			},
			"previous": {
				"start_date": prev_period.start_date,
				"end_date": prev_period.end_date,
				"label": prev_period.label,
			},
		},
		"sales": {
			"net": {
				"current": sales_net_current,
				"previous": sales_net_prev,
				"growth": calc_growth(sales_net_current, sales_net_prev),
			},
			"gross": {
				"current": sales_gross_current,
				"previous": sales_gross_prev,
				"growth": calc_growth(sales_gross_current, sales_gross_prev),
			},
		},
		"purchases": {
			"current": purchases_current,
			"previous": purchases_prev,
			"growth": calc_growth(purchases_current, purchases_prev),
		},
		"profit_loss": {
			"current": {
				"income": pl_current["income"],
				"expense": pl_current["expense"],
				"net_profit": pl_current["net_profit"],
			},
			"previous": {
				"income": pl_prev["income"],
				"expense": pl_prev["expense"],
				"net_profit": pl_prev["net_profit"],
			},
			"growth": calc_growth(pl_current["net_profit"], pl_prev["net_profit"]),
		},
		"cash_bank": {
			"accounts": cash_bank,
			"total": cash_total,
		},
		"ar_aging": ar_aging,
		"ap_aging": ap_aging,
		"customers": {
			"new_count": new_customers_count,
			"top_customers": [{"customer": r["customer"], "total": float(r.get("total", 0))} for r in top_customers],
			"top_overdue_customers": [{"customer": r["customer"], "overdue_amount": float(r.get("overdue_amount", 0))} for r in top_overdue_customers],
		},
		"suppliers": {
			"top_suppliers": [{"supplier": r["supplier"], "total": float(r.get("total", 0))} for r in top_suppliers],
		},
		"hr": {
			"headcount": headcount,
			"payroll_cost": payroll_cost,
			"open_positions": open_positions,
		},
		"top_overdue": [{"customer": r["customer"], "overdue_amount": float(r.get("overdue_amount", 0))} for r in top_overdue_customers[:5]],
		"top_customers_list": [{"customer": r["customer"], "total": float(r.get("total", 0))} for r in top_customers[:5]],
		"top_suppliers_list": [{"supplier": r["supplier"], "total": float(r.get("total", 0))} for r in top_suppliers[:5]],
		"open_positions": open_positions,
	}
