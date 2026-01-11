from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import json

import frappe


@dataclass(frozen=True)
class Period:
	start_date: date
	end_date: date
	label: str


def _require_management_role():
	"""Allow Management role and System Manager."""
	if frappe.session.user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)
	if not (frappe.has_role("Management") or frappe.has_role("System Manager")):
		frappe.throw("You are not permitted to access this dashboard.", frappe.PermissionError)


def _log_dashboard_view(year: int, company: Optional[str], filters: Dict[str, Any]):
	"""Log dashboard view for audit trail."""
	try:
		# Check if Dashboard View Log doctype exists, if not, skip logging
		if frappe.db.exists("DocType", "Dashboard View Log"):
			frappe.get_doc({
				"doctype": "Dashboard View Log",
				"user": frappe.session.user,
				"viewed_at": frappe.utils.now(),
				"year": year,
				"company": company,
				"filters": json.dumps(filters),
			}).insert(ignore_permissions=True)
			frappe.db.commit()
	except Exception:
		# Silently fail if doctype doesn't exist yet
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
			fields=["for_value"],
			distinct=True,
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
	today = date.today()
	y = int(year) if year else today.year
	return Period(start_date=date(y, 1, 1), end_date=date(y, 12, 31), label=str(y))


def _build_filters(
	base_filters: Dict[str, Any],
	cost_centers: Optional[List[str]] = None,
	branches: Optional[List[str]] = None,
	projects: Optional[List[str]] = None,
	customer_groups: Optional[List[str]] = None,
	supplier_groups: Optional[List[str]] = None,
	item_groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
	"""Build filters with multi-select support."""
	filters = base_filters.copy()
	
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
	# Item groups need special handling per doctype
	
	return filters


def _sum_doctype_field(
	doctype: str,
	field: str,
	filters: Dict[str, Any],
) -> float:
	"""Sum a field from a doctype with filters."""
	condition_sql = []
	values: Dict[str, Any] = {}
	
	for k, v in filters.items():
		if isinstance(v, (list, tuple)) and len(v) == 2:
			op, val = v
			if op == "in" and isinstance(val, (list, tuple)):
				placeholders = ", ".join([f"%({k}_{i})s" for i in range(len(val))])
				condition_sql.append(f"`{k}` IN ({placeholders})")
				for i, item in enumerate(val):
					values[f"{k}_{i}"] = item
			else:
				condition_sql.append(f"`{k}` {op} %({k})s")
				values[k] = val
		else:
			condition_sql.append(f"`{k}` = %({k})s")
			values[k] = v
	
	where = " AND ".join(condition_sql) if condition_sql else "1=1"
	res = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(`{field}`), 0)
		FROM `tab{doctype}`
		WHERE {where}
		""",
		values=values,
	)
	return float(res[0][0] or 0)


def _period_sums(
	doctype: str,
	value_field: str,
	date_field: str,
	base_filters: Dict[str, Any],
	period_type: str = "monthly",  # monthly, quarterly, weekly
) -> List[Dict[str, Any]]:
	"""Get sums grouped by period (monthly, quarterly, or weekly)."""
	condition_sql = []
	values: Dict[str, Any] = {}
	
	for k, v in base_filters.items():
		if isinstance(v, (list, tuple)) and len(v) == 2:
			op, val = v
			if op == "in" and isinstance(val, (list, tuple)):
				placeholders = ", ".join([f"%({k}_{i})s" for i in range(len(val))])
				condition_sql.append(f"`{k}` IN ({placeholders})")
				for i, item in enumerate(val):
					values[f"{k}_{i}"] = item
			else:
				condition_sql.append(f"`{k}` {op} %({k})s")
				values[k] = val
		else:
			condition_sql.append(f"`{k}` = %({k})s")
			values[k] = v
	
	where = " AND ".join(condition_sql) if condition_sql else "1=1"
	
	if period_type == "quarterly":
		date_format = "QUARTER(`{date_field}`), YEAR(`{date_field}`)"
		group_by = "QUARTER(`{date_field}`), YEAR(`{date_field}`)"
		order_by = "YEAR(`{date_field}`), QUARTER(`{date_field}`)"
		select_date = "CONCAT(YEAR(`{date_field}`), '-Q', QUARTER(`{date_field}`)) AS period"
	elif period_type == "weekly":
		date_format = "YEARWEEK(`{date_field}`, 1)"
		group_by = "YEARWEEK(`{date_field}`, 1)"
		order_by = "YEARWEEK(`{date_field}`, 1)"
		select_date = "CONCAT(YEAR(`{date_field}`), '-W', LPAD(WEEK(`{date_field}`, 1), 2, '0')) AS period"
	else:  # monthly
		date_format = "DATE_FORMAT(`{date_field}`, '%%Y-%%m-01')"
		group_by = "DATE_FORMAT(`{date_field}`, '%%Y-%%m')"
		order_by = "DATE_FORMAT(`{date_field}`, '%%Y-%%m')"
		select_date = "DATE_FORMAT(`{date_field}`, '%%Y-%%m-01') AS period"
	
	rows = frappe.db.sql(
		f"""
		SELECT
			{select_date.format(date_field=date_field)},
			COALESCE(SUM(`{value_field}`), 0) AS total
		FROM `tab{doctype}`
		WHERE {where}
		GROUP BY {group_by.format(date_field=date_field)}
		ORDER BY {order_by.format(date_field=date_field)} ASC
		""",
		values=values,
		as_dict=True,
	)
	return [{"period": str(r["period"]), "total": float(r["total"] or 0)} for r in rows]


def _pnl_from_gl(
	company: str,
	start_date: date,
	end_date: date,
	cost_centers: Optional[List[str]] = None,
	projects: Optional[List[str]] = None,
) -> Dict[str, float]:
	"""Get P&L from GL Entries."""
	conditions = [
		"gle.is_cancelled = 0",
		"gle.company = %(company)s",
		"gle.posting_date BETWEEN %(start_date)s AND %(end_date)s",
	]
	values = {"company": company, "start_date": start_date, "end_date": end_date}
	
	if cost_centers:
		placeholders = ", ".join([f"%(cc_{i})s" for i in range(len(cost_centers))])
		conditions.append(f"gle.cost_center IN ({placeholders})")
		for i, cc in enumerate(cost_centers):
			values[f"cc_{i}"] = cc
	
	if projects:
		placeholders = ", ".join([f"%(prj_{i})s" for i in range(len(projects))])
		conditions.append(f"gle.project IN ({placeholders})")
		for i, prj in enumerate(projects):
			values[f"prj_{i}"] = prj
	
	where_clause = " AND ".join(conditions)
	
	income = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(gle.credit - gle.debit), 0) AS total
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where_clause}
			AND acc.root_type = 'Income'
		""",
		values,
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
		values,
		as_dict=True,
	)
	
	income_total = float((income or [{}])[0].get("total") or 0)
	expense_total = float((expense or [{}])[0].get("total") or 0)
	return {
		"income": income_total,
		"expense": expense_total,
		"net_profit": income_total - expense_total,
	}


def _cash_bank_balances(
	company: str,
	end_date: date,
	cost_centers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
	"""Get cash and bank balances."""
	accounts = frappe.get_all(
		"Account",
		filters={
			"company": company,
			"is_group": 0,
			"account_type": ["in", ["Cash", "Bank"]],
			"disabled": 0,
		},
		fields=["name", "account_name", "account_type"],
		order_by="account_name asc",
	)
	if not accounts:
		return []
	
	names = [a["name"] for a in accounts]
	placeholders = ", ".join(["%s"] * len(names))
	
	conditions = [
		"gle.is_cancelled = 0",
		"gle.company = %s",
		"gle.posting_date <= %s",
		f"gle.account IN ({placeholders})",
	]
	values = [company, end_date] + names
	
	if cost_centers:
		cc_placeholders = ", ".join(["%s"] * len(cost_centers))
		conditions.append(f"gle.cost_center IN ({cc_placeholders})")
		values.extend(cost_centers)
	
	where_clause = " AND ".join(conditions)
	
	rows = frappe.db.sql(
		f"""
		SELECT gle.account, COALESCE(SUM(gle.debit - gle.credit), 0) AS balance
		FROM `tabGL Entry` gle
		WHERE {where_clause}
		GROUP BY gle.account
		""",
		tuple(values),
		as_dict=True,
	)
	
	by_account = {r["account"]: float(r["balance"] or 0) for r in rows}
	return [
		{
			"account": a["name"],
			"account_name": a["account_name"],
			"account_type": a["account_type"],
			"balance": float(by_account.get(a["name"], 0)),
		}
		for a in accounts
	]


def _get_ar_aging(
	company: str,
	end_date: date,
	cost_centers: Optional[List[str]] = None,
	projects: Optional[List[str]] = None,
	customer_groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
	"""Get AR aging buckets."""
	conditions = [
		"si.docstatus = 1",
		"si.company = %(company)s",
		"si.posting_date <= %(end_date)s",
		"si.outstanding_amount > 0",
	]
	values = {"company": company, "end_date": end_date}
	
	if cost_centers:
		cc_placeholders = ", ".join([f"%(cc_{i})s" for i in range(len(cost_centers))])
		conditions.append(f"si.cost_center IN ({cc_placeholders})")
		for i, cc in enumerate(cost_centers):
			values[f"cc_{i}"] = cc
	
	if projects:
		prj_placeholders = ", ".join([f"%(prj_{i})s" for i in range(len(projects))])
		conditions.append(f"si.project IN ({prj_placeholders})")
		for i, prj in enumerate(projects):
			values[f"prj_{i}"] = prj
	
	if customer_groups:
		cg_placeholders = ", ".join([f"%(cg_{i})s" for i in range(len(customer_groups))])
		conditions.append(f"si.customer_group IN ({cg_placeholders})")
		for i, cg in enumerate(customer_groups):
			values[f"cg_{i}"] = cg
	
	where_clause = " AND ".join(conditions)
	
	rows = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN DATEDIFF(%(end_date)s, si.posting_date) <= 30 THEN si.outstanding_amount ELSE 0 END) AS bucket_0_30,
			SUM(CASE WHEN DATEDIFF(%(end_date)s, si.posting_date) > 30 AND DATEDIFF(%(end_date)s, si.posting_date) <= 60 THEN si.outstanding_amount ELSE 0 END) AS bucket_31_60,
			SUM(CASE WHEN DATEDIFF(%(end_date)s, si.posting_date) > 60 AND DATEDIFF(%(end_date)s, si.posting_date) <= 90 THEN si.outstanding_amount ELSE 0 END) AS bucket_61_90,
			SUM(CASE WHEN DATEDIFF(%(end_date)s, si.posting_date) > 90 THEN si.outstanding_amount ELSE 0 END) AS bucket_90_plus,
			SUM(CASE WHEN DATEDIFF(%(end_date)s, si.due_date) > 0 THEN si.outstanding_amount ELSE 0 END) AS overdue,
			SUM(si.outstanding_amount) AS total
		FROM `tabSales Invoice` si
		WHERE {where_clause}
		""",
		values,
		as_dict=True,
	)
	
	if rows:
		r = rows[0]
		return {
			"0_30": float(r.get("bucket_0_30") or 0),
			"31_60": float(r.get("bucket_31_60") or 0),
			"61_90": float(r.get("bucket_61_90") or 0),
			"90_plus": float(r.get("bucket_90_plus") or 0),
			"overdue": float(r.get("overdue") or 0),
			"total": float(r.get("total") or 0),
		}
	return {"0_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0, "overdue": 0, "total": 0}


def _get_ap_aging(
	company: str,
	end_date: date,
	cost_centers: Optional[List[str]] = None,
	projects: Optional[List[str]] = None,
	supplier_groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
	"""Get AP aging buckets."""
	conditions = [
		"pi.docstatus = 1",
		"pi.company = %(company)s",
		"pi.posting_date <= %(end_date)s",
		"pi.outstanding_amount > 0",
	]
	values = {"company": company, "end_date": end_date}
	
	if cost_centers:
		cc_placeholders = ", ".join([f"%(cc_{i})s" for i in range(len(cost_centers))])
		conditions.append(f"pi.cost_center IN ({cc_placeholders})")
		for i, cc in enumerate(cost_centers):
			values[f"cc_{i}"] = cc
	
	if projects:
		prj_placeholders = ", ".join([f"%(prj_{i})s" for i in range(len(projects))])
		conditions.append(f"pi.project IN ({prj_placeholders})")
		for i, prj in enumerate(projects):
			values[f"prj_{i}"] = prj
	
	if supplier_groups:
		sg_placeholders = ", ".join([f"%(sg_{i})s" for i in range(len(supplier_groups))])
		conditions.append(f"pi.supplier_group IN ({sg_placeholders})")
		for i, sg in enumerate(supplier_groups):
			values[f"sg_{i}"] = sg
	
	where_clause = " AND ".join(conditions)
	
	rows = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN DATEDIFF(%(end_date)s, pi.posting_date) <= 30 THEN pi.outstanding_amount ELSE 0 END) AS bucket_0_30,
			SUM(CASE WHEN DATEDIFF(%(end_date)s, pi.posting_date) > 30 AND DATEDIFF(%(end_date)s, pi.posting_date) <= 60 THEN pi.outstanding_amount ELSE 0 END) AS bucket_31_60,
			SUM(CASE WHEN DATEDIFF(%(end_date)s, pi.posting_date) > 60 AND DATEDIFF(%(end_date)s, pi.posting_date) <= 90 THEN pi.outstanding_amount ELSE 0 END) AS bucket_61_90,
			SUM(CASE WHEN DATEDIFF(%(end_date)s, pi.posting_date) > 90 THEN pi.outstanding_amount ELSE 0 END) AS bucket_90_plus,
			SUM(CASE WHEN DATEDIFF(%(end_date)s, pi.due_date) > 0 THEN pi.outstanding_amount ELSE 0 END) AS overdue,
			SUM(pi.outstanding_amount) AS total
		FROM `tabPurchase Invoice` pi
		WHERE {where_clause}
		""",
		values,
		as_dict=True,
	)
	
	if rows:
		r = rows[0]
		return {
			"0_30": float(r.get("bucket_0_30") or 0),
			"31_60": float(r.get("bucket_31_60") or 0),
			"61_90": float(r.get("bucket_61_90") or 0),
			"90_plus": float(r.get("bucket_90_plus") or 0),
			"overdue": float(r.get("overdue") or 0),
			"total": float(r.get("total") or 0),
		}
	return {"0_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0, "overdue": 0, "total": 0}


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
	Return annual KPI summary for the management dashboard.
	
	- Restricted to role: Management or System Manager
	- Calendar year: 01/01 to 31/12
	- Shows current year and comparison with previous year
	"""
	_require_management_role()
	
	# Parse filter lists
	def parse_list(val):
		if not val:
			return None
		if isinstance(val, str):
			try:
				return json.loads(val) if val.startswith("[") else [val] if val else None
			except:
				return [val] if val else None
		return val if isinstance(val, list) else None
	
	cost_centers_list = parse_list(cost_centers)
	branches_list = parse_list(branches)
	projects_list = parse_list(projects)
	customer_groups_list = parse_list(customer_groups)
	supplier_groups_list = parse_list(supplier_groups)
	item_groups_list = parse_list(item_groups)
	
	# Get company - restrict to user's companies for Management role
	if not frappe.has_role("System Manager"):
		user_companies = _get_user_companies()
		if company and company not in user_companies:
			frappe.throw("You are not permitted to access this company.", frappe.PermissionError)
		if not company and user_companies:
			company = user_companies[0]
	
	company = company or _get_default_company()
	if not company:
		frappe.throw("No Company found/configured.")
	
	# Get periods: current year and previous year
	today = date.today()
	current_year = int(year) if year else today.year
	prev_year = current_year - 1
	
	current_period = _get_period(current_year)
	prev_period = _get_period(prev_year)
	
	# Build filters
	def build_date_filters(period: Period):
		return {"posting_date": ["between", [period.start_date, period.end_date]]}
	
	current_filters = build_date_filters(current_period)
	prev_filters = build_date_filters(prev_period)
	
	# Base filters with company and docstatus
	base_current = {"docstatus": 1, "company": company, **current_filters}
	base_prev = {"docstatus": 1, "company": company, **prev_filters}
	
	# Apply additional filters
	current_filters_full = _build_filters(
		base_current,
		cost_centers_list,
		branches_list,
		projects_list,
		customer_groups_list,
		supplier_groups_list,
		item_groups_list,
	)
	prev_filters_full = _build_filters(
		base_prev,
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
	
	# === REVENUE METRICS ===
	# Sales Invoice (Gross and Net)
	sales_invoice_gross_current = _sum_doctype_field("Sales Invoice", "grand_total", current_filters_full)
	sales_invoice_net_current = _sum_doctype_field("Sales Invoice", "base_grand_total", current_filters_full)
	sales_invoice_gross_prev = _sum_doctype_field("Sales Invoice", "grand_total", prev_filters_full)
	sales_invoice_net_prev = _sum_doctype_field("Sales Invoice", "base_grand_total", prev_filters_full)
	
	# Sales Order
	sales_order_current = _sum_doctype_field("Sales Order", "base_grand_total", current_filters_full)
	sales_order_prev = _sum_doctype_field("Sales Order", "base_grand_total", prev_filters_full)
	
	# Delivery Note
	delivery_note_current = _sum_doctype_field("Delivery Note", "base_grand_total", current_filters_full)
	delivery_note_prev = _sum_doctype_field("Delivery Note", "base_grand_total", prev_filters_full)
	
	# Paid Sales Invoices
	paid_si_filters_current = {**current_filters_full, "outstanding_amount": 0}
	paid_si_filters_prev = {**prev_filters_full, "outstanding_amount": 0}
	paid_sales_invoice_current = _sum_doctype_field("Sales Invoice", "base_grand_total", paid_si_filters_current)
	paid_sales_invoice_prev = _sum_doctype_field("Sales Invoice", "base_grand_total", paid_si_filters_prev)
	
	# Pending Sales Invoices
	pending_si_filters_current = {**current_filters_full, "outstanding_amount": [">", 0]}
	pending_si_filters_prev = {**prev_filters_full, "outstanding_amount": [">", 0]}
	pending_sales_invoice_current = _sum_doctype_field("Sales Invoice", "base_grand_total", pending_si_filters_current)
	pending_sales_invoice_prev = _sum_doctype_field("Sales Invoice", "base_grand_total", pending_si_filters_prev)
	
	# === PURCHASES ===
	purchases_current = _sum_doctype_field("Purchase Invoice", "base_grand_total", current_filters_full)
	purchases_prev = _sum_doctype_field("Purchase Invoice", "base_grand_total", prev_filters_full)
	
	# === AR/AP ===
	# AR Outstanding (all time, not just period)
	ar_filters = {"docstatus": 1, "company": company, "outstanding_amount": [">", 0]}
	if cost_centers_list:
		ar_filters["cost_center"] = ["in", cost_centers_list]
	if projects_list:
		ar_filters["project"] = ["in", projects_list]
	if customer_groups_list:
		ar_filters["customer_group"] = ["in", customer_groups_list]
	
	ar_outstanding = _sum_doctype_field("Sales Invoice", "outstanding_amount", ar_filters)
	ar_aging = _get_ar_aging(company, current_period.end_date, cost_centers_list, projects_list, customer_groups_list)
	
	# AP Outstanding
	ap_filters = {"docstatus": 1, "company": company, "outstanding_amount": [">", 0]}
	if cost_centers_list:
		ap_filters["cost_center"] = ["in", cost_centers_list]
	if projects_list:
		ap_filters["project"] = ["in", projects_list]
	if supplier_groups_list:
		ap_filters["supplier_group"] = ["in", supplier_groups_list]
	
	ap_outstanding = _sum_doctype_field("Purchase Invoice", "outstanding_amount", ap_filters)
	ap_aging = _get_ap_aging(company, current_period.end_date, cost_centers_list, projects_list, supplier_groups_list)
	
	# === P&L ===
	pnl_current = _pnl_from_gl(company, current_period.start_date, current_period.end_date, cost_centers_list, projects_list)
	pnl_prev = _pnl_from_gl(company, prev_period.start_date, prev_period.end_date, cost_centers_list, projects_list)
	
	# === CASH & BANK ===
	cash_bank = _cash_bank_balances(company, current_period.end_date, cost_centers_list)
	cash_total = sum(c.get("balance", 0) for c in cash_bank)
	
	# === TRENDS ===
	sales_trends = _period_sums("Sales Invoice", "base_grand_total", "posting_date", current_filters_full, period_type)
	purchases_trends = _period_sums("Purchase Invoice", "base_grand_total", "posting_date", current_filters_full, period_type)
	
	# === CUSTOMER HEALTH ===
	# New customers (first invoice in period)
	new_customers = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT si.customer) AS count
		FROM `tabSales Invoice` si
		LEFT JOIN (
			SELECT DISTINCT customer
			FROM `tabSales Invoice`
			WHERE docstatus = 1
				AND company = %(company)s
				AND posting_date < %(start_date)s
		) prev_cust ON si.customer = prev_cust.customer
		WHERE si.docstatus = 1
			AND si.company = %(company)s
			AND si.posting_date BETWEEN %(start_date)s AND %(end_date)s
			AND prev_cust.customer IS NULL
		""",
		{"company": company, "start_date": current_period.start_date, "end_date": current_period.end_date},
		as_dict=True,
	)
	new_customers_count = new_customers[0].get("count", 0) if new_customers else 0
	
	# Top overdue customers
	top_overdue_customers = frappe.db.sql(
		"""
		SELECT si.customer, SUM(si.outstanding_amount) AS overdue_amount
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
			AND si.company = %(company)s
			AND si.outstanding_amount > 0
			AND DATEDIFF(%(end_date)s, si.due_date) > 0
		GROUP BY si.customer
		ORDER BY overdue_amount DESC
		LIMIT 10
		""",
		{"company": company, "end_date": current_period.end_date},
		as_dict=True,
	)
	
	# === PURCHASING METRICS ===
	# Top suppliers
	top_suppliers = frappe.db.sql(
		"""
		SELECT pi.supplier, SUM(pi.base_grand_total) AS total
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1
			AND pi.company = %(company)s
			AND pi.posting_date BETWEEN %(start_date)s AND %(end_date)s
		GROUP BY pi.supplier
		ORDER BY total DESC
		LIMIT 10
		""",
		{"company": company, "start_date": current_period.start_date, "end_date": current_period.end_date},
		as_dict=True,
	)
	
	# === HR METRICS ===
	# Headcount (Employee count as of end date)
	headcount = frappe.db.count("Employee", {"status": "Active", "company": company})
	
	# Payroll cost (from Salary Slip)
	payroll_filters = {"docstatus": 1, "company": company, **current_filters}
	payroll_cost = _sum_doctype_field("Salary Slip", "base_gross_pay", payroll_filters) if frappe.db.exists("DocType", "Salary Slip") else 0
	
	# Open positions (Job Opening)
	open_positions = frappe.db.count("Job Opening", {"status": "Open", "company": company}) if frappe.db.exists("DocType", "Job Opening") else 0
	
	# Log audit trail
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
			"period_type": period_type,
		},
	)
	
	return {
		"company": company,
		"company_currency": company_currency,
		"presentation_currency": presentation_currency,
		"current_period": {
			"year": current_year,
			"label": current_period.label,
			"start_date": str(current_period.start_date),
			"end_date": str(current_period.end_date),
		},
		"previous_period": {
			"year": prev_year,
			"label": prev_period.label,
			"start_date": str(prev_period.start_date),
			"end_date": str(prev_period.end_date),
		},
		"kpis": {
			# Revenue metrics
			"sales_invoice_gross": {"current": sales_invoice_gross_current, "previous": sales_invoice_gross_prev},
			"sales_invoice_net": {"current": sales_invoice_net_current, "previous": sales_invoice_net_prev},
			"sales_order": {"current": sales_order_current, "previous": sales_order_prev},
			"delivery_note": {"current": delivery_note_current, "previous": delivery_note_prev},
			"paid_sales_invoice": {"current": paid_sales_invoice_current, "previous": paid_sales_invoice_prev},
			"pending_sales_invoice": {"current": pending_sales_invoice_current, "previous": pending_sales_invoice_prev},
			# Purchases
			"purchases": {"current": purchases_current, "previous": purchases_prev},
			# P&L
			"income": {"current": pnl_current["income"], "previous": pnl_prev["income"]},
			"expense": {"current": pnl_current["expense"], "previous": pnl_prev["expense"]},
			"net_profit": {"current": pnl_current["net_profit"], "previous": pnl_prev["net_profit"]},
			# AR/AP
			"ar_outstanding": ar_outstanding,
			"ap_outstanding": ap_outstanding,
			"cash_total": cash_total,
		},
		"aging": {
			"ar": ar_aging,
			"ap": ap_aging,
		},
		"trends": {
			"sales": sales_trends,
			"purchases": purchases_trends,
		},
		"breakdowns": {
			"cash_bank": cash_bank,
			"top_overdue_customers": [{"customer": r["customer"], "overdue_amount": float(r.get("overdue_amount", 0))} for r in top_overdue_customers],
			"top_suppliers": [{"supplier": r["supplier"], "total": float(r.get("total", 0))} for r in top_suppliers],
		},
		"customer_health": {
			"new_customers": new_customers_count,
			"top_overdue": [{"customer": r["customer"], "overdue_amount": float(r.get("overdue_amount", 0))} for r in top_overdue_customers[:5]],
		},
		"hr": {
			"headcount": headcount,
			"payroll_cost": payroll_cost,
			"open_positions": open_positions,
		},
	}
