/* global frappe */

frappe.pages["management_dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Management Dashboard"),
		single_column: true,
	});

	wrapper.classList.add("management-dashboard");
	
	// Check RTL
	const is_rtl = frappe.rtl || (frappe.boot && frappe.boot.lang_info && frappe.boot.lang_info.rtl);
	if (is_rtl) {
		wrapper.classList.add("md-rtl");
	}

	const $root = $(wrapper).find(".layout-main-section");
	
	// Sticky filters key
	const STORAGE_KEY = "management_dashboard_filters";

	// Load saved filters
	function load_saved_filters() {
		try {
			const saved = localStorage.getItem(STORAGE_KEY);
			return saved ? JSON.parse(saved) : {};
		} catch (e) {
			return {};
		}
	}

	// Save filters
	function save_filters(filters) {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
		} catch (e) {
			// Ignore
		}
	}

	const saved_filters = load_saved_filters();
	const current_year = new Date().getFullYear();

	// Filters container
	const $filters = $(`
		<div class="md-filters">
			<div class="md-filter-row-1"></div>
			<div class="md-filter-row-2"></div>
			<div class="md-filter-actions"></div>
		</div>
	`);
	$root.append($filters);

	// Year filter
	const year_control = frappe.ui.form.make_control({
		parent: $filters.find(".md-filter-row-1"),
		df: {
			fieldtype: "Int",
			label: __("Year"),
			fieldname: "year",
			reqd: 1,
			default: saved_filters.year || current_year,
		},
		render_input: true,
	});
	year_control.set_value(saved_filters.year || current_year);

	// Company filter
	const company_control = frappe.ui.form.make_control({
		parent: $filters.find(".md-filter-row-1"),
		df: {
			fieldtype: "Link",
			options: "Company",
			label: __("Company"),
			fieldname: "company",
			default: saved_filters.company,
		},
		render_input: true,
	});
	if (saved_filters.company) {
		company_control.set_value(saved_filters.company);
	}

	// Helper function to create multi-select link control
	function create_multi_link_control(parent, options, label, fieldname, saved_value) {
		const $wrapper = $('<div class="form-group"></div>');
		const $label = $(`<label class="control-label">${label}</label>`);
		const $input_wrapper = $('<div class="control-input-wrapper"></div>');
		const $input = $('<input type="text" class="form-control md-multiselect-link" placeholder="Type to search, comma-separated for multiple">');
		const $hidden = $('<input type="hidden" class="md-multiselect-value">');
		
		$input_wrapper.append($input, $hidden);
		$wrapper.append($label, $input_wrapper);
		parent.append($wrapper);

		let selected_values = Array.isArray(saved_value) ? saved_value : (saved_value ? [saved_value] : []);
		$hidden.val(JSON.stringify(selected_values));

		// Update display
		function update_display() {
			if (selected_values.length) {
				$input.val(selected_values.join(", "));
			} else {
				$input.val("");
			}
		}
		update_display();

		// Autocomplete
		$input.autocomplete({
			source: function(request, response) {
				frappe.db.get_list(options, {
					filters: { name: ["like", "%" + request.term + "%"] },
					limit: 20,
				}).then(results => {
					response(results.map(r => r.name));
				});
			},
			select: function(event, ui) {
				if (selected_values.indexOf(ui.item.value) === -1) {
					selected_values.push(ui.item.value);
					$hidden.val(JSON.stringify(selected_values));
					update_display();
				}
				$input.val("");
				return false;
			},
			minLength: 0,
		});

		// Allow comma-separated input
		$input.on("blur", function() {
			const val = $input.val().trim();
			if (val) {
				const items = val.split(",").map(s => s.trim()).filter(s => s);
				selected_values = Array.from(new Set([...selected_values, ...items]));
				$hidden.val(JSON.stringify(selected_values));
				update_display();
			}
		});

		// Remove on backspace
		$input.on("keydown", function(e) {
			if (e.key === "Backspace" && !$input.val() && selected_values.length) {
				selected_values.pop();
				$hidden.val(JSON.stringify(selected_values));
				update_display();
			}
		});

		return {
			get_value: function() {
				const val = $hidden.val();
				try {
					return JSON.parse(val || "[]");
				} catch {
					return [];
				}
			},
			set_value: function(values) {
				selected_values = Array.isArray(values) ? values : (values ? [values] : []);
				$hidden.val(JSON.stringify(selected_values));
				update_display();
			},
			$input: $input,
		};
	}

	// Cost Center filter (multi-select)
	const cost_center_control = create_multi_link_control(
		$filters.find(".md-filter-row-1"),
		"Cost Center",
		__("Cost Center"),
		"cost_centers",
		saved_filters.cost_centers
	);

	// Branch filter (multi-select)
	const branch_control = create_multi_link_control(
		$filters.find(".md-filter-row-1"),
		"Branch",
		__("Branch"),
		"branches",
		saved_filters.branches
	);

	// Project filter (multi-select)
	const project_control = create_multi_link_control(
		$filters.find(".md-filter-row-2"),
		"Project",
		__("Project"),
		"projects",
		saved_filters.projects
	);

	// Customer Group filter (multi-select)
	const customer_group_control = create_multi_link_control(
		$filters.find(".md-filter-row-2"),
		"Customer Group",
		__("Customer Group"),
		"customer_groups",
		saved_filters.customer_groups
	);

	// Supplier Group filter (multi-select)
	const supplier_group_control = create_multi_link_control(
		$filters.find(".md-filter-row-2"),
		"Supplier Group",
		__("Supplier Group"),
		"supplier_groups",
		saved_filters.supplier_groups
	);

	// Item Group filter (multi-select)
	const item_group_control = create_multi_link_control(
		$filters.find(".md-filter-row-2"),
		"Item Group",
		__("Item Group"),
		"item_groups",
		saved_filters.item_groups
	);

	// Period type toggle (Monthly/Quarterly/Weekly)
	const period_type_control = frappe.ui.form.make_control({
		parent: $filters.find(".md-filter-actions"),
		df: {
			fieldtype: "Select",
			label: __("Period"),
			fieldname: "period_type",
			options: "Monthly\nQuarterly\nWeekly",
			default: saved_filters.period_type || "Monthly",
		},
		render_input: true,
	});
	period_type_control.set_value(saved_filters.period_type || "Monthly");

	// Action buttons
	const $actions = $('<div class="md-action-buttons"></div>');
	$filters.find(".md-filter-actions").append($actions);

	const refresh_btn = page.set_primary_action(__("Refresh"), () => load_data());
	
	// Export buttons
	const export_csv_btn = $('<button class="btn btn-sm btn-secondary">' + __("Export CSV") + '</button>');
	const export_excel_btn = $('<button class="btn btn-sm btn-secondary">' + __("Export Excel") + '</button>');
	const export_pdf_btn = $('<button class="btn btn-sm btn-secondary">' + __("Export PDF") + '</button>');
	const print_btn = $('<button class="btn btn-sm btn-secondary">' + __("Print") + '</button>');
	
	$actions.append(export_csv_btn, export_excel_btn, export_pdf_btn, print_btn);

	// Content containers
	const $kpis = $('<div class="md-kpis"></div>');
	const $charts = $('<div class="md-charts-container"></div>');
	const $breakdowns = $('<div class="md-breakdowns-container"></div>');
	const $tables = $('<div class="md-tables-container"></div>');

	$root.append($kpis, $charts, $breakdowns, $tables);

	let dashboard_data = null;

	function money(v, currency) {
		try {
			return frappe.format(v || 0, { fieldtype: "Currency", options: currency || "" });
		} catch (e) {
			return (v || 0).toLocaleString();
		}
	}

	function format_percent(current, previous) {
		if (!previous || previous === 0) return current > 0 ? "+100%" : "0%";
		const change = ((current - previous) / previous) * 100;
		const sign = change >= 0 ? "+" : "";
		return sign + change.toFixed(1) + "%";
	}

	function set_loading(is_loading) {
		$root.toggleClass("md-loading", !!is_loading);
	}

	function get_filter_values() {
		return {
			year: year_control.get_value(),
			company: company_control.get_value(),
			cost_centers: cost_center_control.get_value() || [],
			branches: branch_control.get_value() || [],
			projects: project_control.get_value() || [],
			customer_groups: customer_group_control.get_value() || [],
			supplier_groups: supplier_group_control.get_value() || [],
			item_groups: item_group_control.get_value() || [],
			period_type: period_type_control.get_value() || "Monthly",
		};
	}

	function render_kpis(data) {
		if (!data || !data.kpis) return;

		const kpis = data.kpis;
		const current_period = data.current_period || {};
		const previous_period = data.previous_period || {};
		const currency = data.presentation_currency || data.company_currency || "";

		const title = `${__("Annual Summary")} — ${frappe.utils.escape_html(current_period.label || "")} vs ${frappe.utils.escape_html(previous_period.label || "")}`;

		// Top KPI cards
		const kpi_cards = [];

		// Sales Invoice (Net)
		const si_net = kpis.sales_invoice_net || {};
		kpi_cards.push(`
			<div class="md-kpi-card" data-drilldown="sales_invoice">
				<div class="md-kpi-label">${__("Sales Invoice (Net)")}</div>
				<div class="md-kpi-value">${money(si_net.current || 0, currency)}</div>
				<div class="md-kpi-comparison">
					<span class="md-kpi-prev">${__("Previous")}: ${money(si_net.previous || 0, currency)}</span>
					<span class="md-kpi-change ${((si_net.current || 0) - (si_net.previous || 0)) < 0 ? 'md-negative-change' : ''}">${format_percent(si_net.current || 0, si_net.previous || 0)}</span>
				</div>
			</div>
		`);

		// Sales Invoice (Gross)
		const si_gross = kpis.sales_invoice_gross || {};
		const si_gross_change = ((si_gross.current || 0) - (si_gross.previous || 0));
		kpi_cards.push(`
			<div class="md-kpi-card" data-drilldown="sales_invoice">
				<div class="md-kpi-label">${__("Sales Invoice (Gross)")}</div>
				<div class="md-kpi-value">${money(si_gross.current || 0, currency)}</div>
				<div class="md-kpi-comparison">
					<span class="md-kpi-prev">${__("Previous")}: ${money(si_gross.previous || 0, currency)}</span>
					<span class="md-kpi-change ${si_gross_change < 0 ? 'md-negative-change' : ''}">${format_percent(si_gross.current || 0, si_gross.previous || 0)}</span>
				</div>
			</div>
		`);

		// Sales Order
		const so = kpis.sales_order || {};
		const so_change = ((so.current || 0) - (so.previous || 0));
		kpi_cards.push(`
			<div class="md-kpi-card" data-drilldown="sales_order">
				<div class="md-kpi-label">${__("Sales Order")}</div>
				<div class="md-kpi-value">${money(so.current || 0, currency)}</div>
				<div class="md-kpi-comparison">
					<span class="md-kpi-prev">${__("Previous")}: ${money(so.previous || 0, currency)}</span>
					<span class="md-kpi-change ${so_change < 0 ? 'md-negative-change' : ''}">${format_percent(so.current || 0, so.previous || 0)}</span>
				</div>
			</div>
		`);

		// Delivery Note
		const dn = kpis.delivery_note || {};
		const dn_change = ((dn.current || 0) - (dn.previous || 0));
		kpi_cards.push(`
			<div class="md-kpi-card" data-drilldown="delivery_note">
				<div class="md-kpi-label">${__("Delivery Note")}</div>
				<div class="md-kpi-value">${money(dn.current || 0, currency)}</div>
				<div class="md-kpi-comparison">
					<span class="md-kpi-prev">${__("Previous")}: ${money(dn.previous || 0, currency)}</span>
					<span class="md-kpi-change ${dn_change < 0 ? 'md-negative-change' : ''}">${format_percent(dn.current || 0, dn.previous || 0)}</span>
				</div>
			</div>
		`);

		// Net Profit
		const profit = kpis.net_profit || {};
		const profit_change = ((profit.current || 0) - (profit.previous || 0));
		kpi_cards.push(`
			<div class="md-kpi-card" data-drilldown="profit_loss">
				<div class="md-kpi-label">${__("Net Profit")}</div>
				<div class="md-kpi-value ${(profit.current || 0) < 0 ? 'md-negative' : ''}">${money(profit.current || 0, currency)}</div>
				<div class="md-kpi-comparison">
					<span class="md-kpi-prev">${__("Previous")}: ${money(profit.previous || 0, currency)}</span>
					<span class="md-kpi-change ${profit_change < 0 ? 'md-negative-change' : ''}">${format_percent(profit.current || 0, profit.previous || 0)}</span>
				</div>
			</div>
		`);

		// AR Outstanding
		kpi_cards.push(`
			<div class="md-kpi-card" data-drilldown="ar">
				<div class="md-kpi-label">${__("AR Outstanding")}</div>
				<div class="md-kpi-value">${money(kpis.ar_outstanding || 0, currency)}</div>
			</div>
		`);

		// AP Outstanding
		kpi_cards.push(`
			<div class="md-kpi-card" data-drilldown="ap">
				<div class="md-kpi-label">${__("AP Outstanding")}</div>
				<div class="md-kpi-value">${money(kpis.ap_outstanding || 0, currency)}</div>
			</div>
		`);

		// Cash Total
		kpi_cards.push(`
			<div class="md-kpi-card" data-drilldown="cash">
				<div class="md-kpi-label">${__("Cash & Bank")}</div>
				<div class="md-kpi-value">${money(kpis.cash_total || 0, currency)}</div>
			</div>
		`);

		$kpis.empty().append(`
			<div class="md-kpis-header">
				<div class="md-kpis-title">${title}</div>
				<div class="md-kpis-subtitle">
					${__("Current Period")}: ${frappe.utils.escape_html(current_period.start_date || "")} → ${frappe.utils.escape_html(current_period.end_date || "")}
				</div>
			</div>
			<div class="md-kpis-grid">${kpi_cards.join("")}</div>
		`);

		// Add drilldown handlers
		$kpis.find(".md-kpi-card").on("click", function() {
			const drilldown = $(this).data("drilldown");
			if (drilldown) {
				handle_drilldown(drilldown, data);
			}
		});
	}

	function render_charts(data) {
		if (!data || !data.trends) return;

		const trends = data.trends;
		const currency = data.presentation_currency || data.company_currency || "";
		const period_type = period_type_control.get_value() || "Monthly";

		$charts.empty();

		// Sales vs Purchases chart
		const sales_data = trends.sales || [];
		const purchases_data = trends.purchases || [];

		const all_periods = Array.from(new Set([...sales_data.map(r => r.period), ...purchases_data.map(r => r.period)])).sort();
		const sales_by_period = Object.fromEntries(sales_data.map(r => [r.period, r.total]));
		const purchases_by_period = Object.fromEntries(purchases_data.map(r => [r.period, r.total]));

		const labels = all_periods.map(p => {
			if (period_type === "Quarterly") return p;
			if (period_type === "Weekly") return p;
			return frappe.datetime.str_to_user(p + "-01");
		});
		const sales_values = all_periods.map(p => sales_by_period[p] || 0);
		const purchases_values = all_periods.map(p => purchases_by_period[p] || 0);

		const $chart_card = $(`
			<div class="md-card">
				<div class="md-card-title">${__("Sales vs Purchases")} (${period_type})</div>
				<div class="md-chart" data-chart="sales_purchases"></div>
			</div>
		`);

		$charts.append($chart_card);

		const $chart_target = $chart_card.find('[data-chart="sales_purchases"]');
		if (!labels.length) {
			$chart_target.html(`<div class="md-empty">${__("No data for the selected period.")}</div>`);
			return;
		}

		if (typeof frappe.Chart === "function") {
			new frappe.Chart($chart_target[0], {
				data: {
					labels,
					datasets: [
						{ name: __("Sales"), chartType: "bar", values: sales_values },
						{ name: __("Purchases"), chartType: "bar", values: purchases_values },
					],
				},
				type: "bar",
				height: 300,
				colors: ["#4F46E5", "#F59E0B"],
				axisOptions: { xIsSeries: 0 },
			});
		}

		// AR Aging chart
		if (data.aging && data.aging.ar) {
			const ar_aging = data.aging.ar;
			const $ar_chart_card = $(`
				<div class="md-card">
					<div class="md-card-title">${__("AR Aging")}</div>
					<div class="md-chart" data-chart="ar_aging"></div>
				</div>
			`);
			$charts.append($ar_chart_card);

			const $ar_chart = $ar_chart_card.find('[data-chart="ar_aging"]');
			if (typeof frappe.Chart === "function") {
				new frappe.Chart($ar_chart[0], {
					data: {
						labels: ["0-30", "31-60", "61-90", "90+"],
						datasets: [
							{
								name: __("Amount"),
								chartType: "bar",
								values: [ar_aging["0_30"] || 0, ar_aging["31_60"] || 0, ar_aging["61_90"] || 0, ar_aging["90_plus"] || 0],
							},
						],
					},
					type: "bar",
					height: 250,
					colors: ["#EF4444"],
				});
			}
		}

		// AP Aging chart
		if (data.aging && data.aging.ap) {
			const ap_aging = data.aging.ap;
			const $ap_chart_card = $(`
				<div class="md-card">
					<div class="md-card-title">${__("AP Aging")}</div>
					<div class="md-chart" data-chart="ap_aging"></div>
				</div>
			`);
			$charts.append($ap_chart_card);

			const $ap_chart = $ap_chart_card.find('[data-chart="ap_aging"]');
			if (typeof frappe.Chart === "function") {
				new frappe.Chart($ap_chart[0], {
					data: {
						labels: ["0-30", "31-60", "61-90", "90+"],
						datasets: [
							{
								name: __("Amount"),
								chartType: "bar",
								values: [ap_aging["0_30"] || 0, ap_aging["31_60"] || 0, ap_aging["61_90"] || 0, ap_aging["90_plus"] || 0],
							},
						],
					},
					type: "bar",
					height: 250,
					colors: ["#3B82F6"],
				});
			}
		}
	}

	function render_breakdowns(data) {
		if (!data || !data.breakdowns) return;

		const breakdowns = data.breakdowns;
		const currency = data.presentation_currency || data.company_currency || "";

		$breakdowns.empty();

		// Cash & Bank
		const cash_bank = breakdowns.cash_bank || [];
		if (cash_bank.length) {
			const $cash_card = $(`
				<div class="md-card">
					<div class="md-card-title">${__("Cash & Bank Balances")}</div>
					<div class="md-list" data-list="cash"></div>
				</div>
			`);
			const $cash_list = $cash_card.find('[data-list="cash"]');
			$cash_list.append(
				cash_bank.map(r => `
					<div class="md-list-row">
						<div class="md-list-main">
							${frappe.utils.escape_html(r.account_name || r.account)}
							<span class="md-badge">${frappe.utils.escape_html(r.account_type || "")}</span>
						</div>
						<div class="md-list-value">${money(r.balance || 0, currency)}</div>
					</div>
				`).join("")
			);
			$breakdowns.append($cash_card);
		}

		// Top Overdue Customers
		const top_overdue = breakdowns.top_overdue_customers || [];
		if (top_overdue.length) {
			const $overdue_card = $(`
				<div class="md-card">
					<div class="md-card-title">${__("Top Overdue Customers")}</div>
					<div class="md-list" data-list="overdue"></div>
				</div>
			`);
			const $overdue_list = $overdue_card.find('[data-list="overdue"]');
			$overdue_list.append(
				top_overdue.map(r => `
					<div class="md-list-row">
						<div class="md-list-main">
							<a class="md-link" href="/app/customer/${encodeURIComponent(r.customer)}">
								${frappe.utils.escape_html(r.customer)}
							</a>
						</div>
						<div class="md-list-value">${money(r.overdue_amount || 0, currency)}</div>
					</div>
				`).join("")
			);
			$breakdowns.append($overdue_card);
		}

		// Top Suppliers
		const top_suppliers = breakdowns.top_suppliers || [];
		if (top_suppliers.length) {
			const $suppliers_card = $(`
				<div class="md-card">
					<div class="md-card-title">${__("Top Suppliers")}</div>
					<div class="md-list" data-list="suppliers"></div>
				</div>
			`);
			const $suppliers_list = $suppliers_card.find('[data-list="suppliers"]');
			$suppliers_list.append(
				top_suppliers.map(r => `
					<div class="md-list-row">
						<div class="md-list-main">
							<a class="md-link" href="/app/supplier/${encodeURIComponent(r.supplier)}">
								${frappe.utils.escape_html(r.supplier)}
							</a>
						</div>
						<div class="md-list-value">${money(r.total || 0, currency)}</div>
					</div>
				`).join("")
			);
			$breakdowns.append($suppliers_card);
		}

		// Customer Health
		if (data.customer_health) {
			const ch = data.customer_health;
			const $ch_card = $(`
				<div class="md-card">
					<div class="md-card-title">${__("Customer Health")}</div>
					<div class="md-kpi-rows" data-panel="customer_health"></div>
				</div>
			`);
			const $ch_rows = $ch_card.find('[data-panel="customer_health"]');
			$ch_rows.append(`
				<div class="md-kpi-row">
					<div class="md-kpi-row-label">${__("New Customers")}</div>
					<div class="md-kpi-row-value">${ch.new_customers || 0}</div>
				</div>
			`);
			$breakdowns.append($ch_card);
		}

		// HR Metrics
		if (data.hr) {
			const hr = data.hr;
			const $hr_card = $(`
				<div class="md-card">
					<div class="md-card-title">${__("HR Metrics")}</div>
					<div class="md-kpi-rows" data-panel="hr"></div>
				</div>
			`);
			const $hr_rows = $hr_card.find('[data-panel="hr"]');
			$hr_rows.append(`
				<div class="md-kpi-row">
					<div class="md-kpi-row-label">${__("Headcount")}</div>
					<div class="md-kpi-row-value">${hr.headcount || 0}</div>
				</div>
				<div class="md-kpi-row">
					<div class="md-kpi-row-label">${__("Payroll Cost")}</div>
					<div class="md-kpi-row-value">${money(hr.payroll_cost || 0, currency)}</div>
				</div>
				<div class="md-kpi-row">
					<div class="md-kpi-row-label">${__("Open Positions")}</div>
					<div class="md-kpi-row-value">${hr.open_positions || 0}</div>
				</div>
			`);
			$breakdowns.append($hr_card);
		}
	}

	function handle_drilldown(type, data) {
		const filters = get_filter_values();
		const period = data.current_period || {};
		
		let list_route = "";
		let list_filters = {};

		switch (type) {
			case "sales_invoice":
				list_route = "/app/sales-invoice";
				list_filters = {
					company: filters.company,
					posting_date: ["between", [period.start_date, period.end_date]],
				};
				break;
			case "sales_order":
				list_route = "/app/sales-order";
				list_filters = {
					company: filters.company,
					transaction_date: ["between", [period.start_date, period.end_date]],
				};
				break;
			case "delivery_note":
				list_route = "/app/delivery-note";
				list_filters = {
					company: filters.company,
					posting_date: ["between", [period.start_date, period.end_date]],
				};
				break;
			case "ar":
				list_route = "/app/sales-invoice";
				list_filters = {
					company: filters.company,
					outstanding_amount: [">", 0],
				};
				break;
			case "ap":
				list_route = "/app/purchase-invoice";
				list_filters = {
					company: filters.company,
					outstanding_amount: [">", 0],
				};
				break;
			case "cash":
				list_route = "/app/account";
				list_filters = {
					company: filters.company,
					account_type: ["in", ["Cash", "Bank"]],
				};
				break;
			case "profit_loss":
				list_route = "/app/account";
				list_filters = {
					company: filters.company,
				};
				break;
		}

		if (list_route) {
			frappe.set_route(list_route, list_filters);
		}
	}

	function export_csv() {
		if (!dashboard_data) return;
		// Simple CSV export of KPIs
		const kpis = dashboard_data.kpis || {};
		const lines = ["KPI,Current,Previous"];
		Object.keys(kpis).forEach(key => {
			const value = kpis[key];
			if (typeof value === "object" && value.current !== undefined) {
				lines.push(`${key},${value.current || 0},${value.previous || 0}`);
			} else {
				lines.push(`${key},${value || 0},`);
			}
		});
		const csv = lines.join("\n");
		const blob = new Blob([csv], { type: "text/csv" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `management_dashboard_${dashboard_data.current_period.year}.csv`;
		a.click();
	}

	function export_excel() {
		// For Excel, we'd need a library like SheetJS
		// For now, redirect to CSV
		export_csv();
		frappe.msgprint({
			message: __("Excel export is currently exported as CSV. Full Excel support coming soon."),
			indicator: "blue",
		});
	}

	function export_pdf() {
		window.print();
	}

	function print_view() {
		window.print();
	}

	// Export handlers
	export_csv_btn.on("click", export_csv);
	export_excel_btn.on("click", export_excel);
	export_pdf_btn.on("click", export_pdf);
	print_btn.on("click", print_view);

	async function load_data() {
		set_loading(true);
		try {
			const filters = get_filter_values();
			save_filters(filters);

			const args = {
				year: filters.year,
				company: filters.company,
				cost_centers: JSON.stringify(filters.cost_centers || []),
				branches: JSON.stringify(filters.branches || []),
				projects: JSON.stringify(filters.projects || []),
				customer_groups: JSON.stringify(filters.customer_groups || []),
				supplier_groups: JSON.stringify(filters.supplier_groups || []),
				item_groups: JSON.stringify(filters.item_groups || []),
				period_type: filters.period_type.toLowerCase(),
			};

			const r = await frappe.call({
				method: "management_dashboard.management_dashboard.api.annual_summary.get_annual_summary",
				args,
				freeze: true,
				freeze_message: __("Loading annual summary…"),
			});

			dashboard_data = r && r.message;
			if (dashboard_data) {
				render_kpis(dashboard_data);
				render_charts(dashboard_data);
				render_breakdowns(dashboard_data);
			}
		} catch (e) {
			console.error(e);
			frappe.msgprint({
				title: __("Management Dashboard"),
				message: __("Could not load dashboard data. Please contact your system administrator."),
				indicator: "red",
			});
		} finally {
			set_loading(false);
		}
	}

	// Initial load
	load_data();

	// Reload on filter changes
	year_control.$input && year_control.$input.on("change", () => load_data());
	company_control.$input && company_control.$input.on("change", () => load_data());
	cost_center_control.$input && cost_center_control.$input.on("blur change", () => load_data());
	branch_control.$input && branch_control.$input.on("blur change", () => load_data());
	project_control.$input && project_control.$input.on("blur change", () => load_data());
	customer_group_control.$input && customer_group_control.$input.on("blur change", () => load_data());
	supplier_group_control.$input && supplier_group_control.$input.on("blur change", () => load_data());
	item_group_control.$input && item_group_control.$input.on("blur change", () => load_data());
	period_type_control.$input && period_type_control.$input.on("change", () => load_data());
};
