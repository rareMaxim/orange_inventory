frappe.pages["agent-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Agent Dashboard",
		single_column: true,
	});

	// Зберігаємо посилання на page для фільтра
	page.selected_group = null;

	// Додаємо фільтр по групі
	page.add_field({
		fieldname: "asset_group",
		label: __("Група"),
		fieldtype: "Link",
		options: "oiAssetGroup",
		change: function () {
			page.selected_group = this.get_value() || null;
			loadDashboard(page);
		},
	});

	// Додаємо кнопку оновлення
	page.set_primary_action(
		__("Оновити"),
		() => {
			loadDashboard(page);
		},
		"refresh"
	);

	// Додаємо посилання
	page.add_inner_button(__("Агенти"), () => {
		frappe.set_route("List", "oiAgent");
	});

	page.add_inner_button(__("Алерти"), () => {
		frappe.set_route("List", "oiAgentAlert", { status: "Активне" });
	});

	page.add_inner_button(__("Правила алертів"), () => {
		frappe.set_route("List", "oiAlertRule");
	});

	page.add_inner_button(__("Групи"), () => {
		frappe.set_route("List", "oiAssetGroup");
	});

	// Контейнер для dashboard
	$(wrapper).find(".layout-main-section").append(`
		<div class="agent-dashboard-container">
			<div class="dashboard-loading">
				<div class="spinner-border text-primary" role="status">
					<span class="sr-only">Loading...</span>
				</div>
				<p>Завантаження даних...</p>
			</div>
			<div class="dashboard-content" style="display: none;"></div>
		</div>
	`);

	// Завантажуємо дані
	loadDashboard(page);

	// Автооновлення кожні 60 секунд
	page.dashboard_interval = setInterval(() => {
		loadDashboard(page, true);
	}, 60000);
};

frappe.pages["agent-dashboard"].on_page_hide = function (wrapper) {
	// Очищаємо інтервал при виході зі сторінки
	const page = wrapper.page;
	if (page && page.dashboard_interval) {
		clearInterval(page.dashboard_interval);
	}
};

function loadDashboard(page, silent = false) {
	const $container = $(page.wrapper).find(".agent-dashboard-container");
	const $loading = $container.find(".dashboard-loading");
	const $content = $container.find(".dashboard-content");

	if (!silent) {
		$loading.show();
		$content.hide();
	}

	const args = {};
	if (page.selected_group) {
		args.asset_group = page.selected_group;
	}

	frappe.call({
		method: "orange_inventory.orange_inventory.dashboard_api.get_dashboard_stats",
		args: args,
		callback: function (r) {
			if (r.message) {
				renderDashboard($content, r.message, page.selected_group);
				$loading.hide();
				$content.show();
			}
		},
		error: function () {
			$loading.html('<p class="text-danger">Помилка завантаження даних</p>');
		},
	});
}

function renderDashboard($container, stats, selectedGroup = null) {
	const { agents, alerts, resources, problem_agents } = stats;
	const groupTitle = selectedGroup ? ` — ${selectedGroup}` : "";

	$container.html(`
		<!-- Статистика агентів -->
		<div class="row mb-4">
			<div class="col-12">
				<h5 class="text-muted mb-3">Агенти${groupTitle}</h5>
			</div>
			<div class="col-md-3 col-sm-6 mb-3">
				${renderStatCard("Всього агентів", agents.total, "blue", "fa-server")}
			</div>
			<div class="col-md-3 col-sm-6 mb-3">
				${renderStatCard("Онлайн", agents.online, "green", "fa-check-circle")}
			</div>
			<div class="col-md-3 col-sm-6 mb-3">
				${renderStatCard("Офлайн", agents.offline, "red", "fa-times-circle")}
			</div>
			<div class="col-md-3 col-sm-6 mb-3">
				${renderStatCard("Неактивних", agents.inactive, "gray", "fa-pause-circle")}
			</div>
		</div>

		<!-- Статистика алертів -->
		<div class="row mb-4">
			<div class="col-12">
				<h5 class="text-muted mb-3">Активні алерти</h5>
			</div>
			<div class="col-md-3 col-sm-6 mb-3">
				${renderStatCard(
					"Всього активних",
					alerts.active_total,
					alerts.active_total > 0 ? "orange" : "green",
					"fa-bell"
				)}
			</div>
			<div class="col-md-3 col-sm-6 mb-3">
				${renderStatCard(
					"Critical",
					alerts.critical,
					alerts.critical > 0 ? "red" : "gray",
					"fa-exclamation-triangle"
				)}
			</div>
			<div class="col-md-3 col-sm-6 mb-3">
				${renderStatCard(
					"Warning",
					alerts.warning,
					alerts.warning > 0 ? "yellow" : "gray",
					"fa-exclamation-circle"
				)}
			</div>
			<div class="col-md-3 col-sm-6 mb-3">
				${renderStatCard("Вирішено (24г)", alerts.resolved_24h, "green", "fa-check")}
			</div>
		</div>

		<!-- Використання ресурсів -->
		<div class="row mb-4">
			<div class="col-12">
				<h5 class="text-muted mb-3">Середнє використання ресурсів</h5>
			</div>
			<div class="col-md-4 mb-3">
				${renderProgressCard("CPU", resources.avg_cpu, resources.high_cpu_count)}
			</div>
			<div class="col-md-4 mb-3">
				${renderProgressCard("RAM", resources.avg_ram, resources.high_ram_count)}
			</div>
			<div class="col-md-4 mb-3">
				${renderProgressCard("Disk", resources.avg_disk, resources.high_disk_count)}
			</div>
		</div>

		<!-- Алерти по типах -->
		${
			Object.keys(alerts.by_type).length > 0
				? `
		<div class="row mb-4">
			<div class="col-12">
				<h5 class="text-muted mb-3">Алерти по типах</h5>
				<div class="card">
					<div class="card-body">
						${renderAlertsByType(alerts.by_type)}
					</div>
				</div>
			</div>
		</div>
		`
				: ""
		}

		<!-- Проблемні агенти -->
		${
			problem_agents.length > 0
				? `
		<div class="row mb-4">
			<div class="col-12">
				<h5 class="text-muted mb-3">Проблемні агенти</h5>
				<div class="card">
					<div class="card-body p-0">
						<table class="table table-hover mb-0">
							<thead class="thead-light">
								<tr>
									<th>Агент</th>
									<th>Статус</th>
									<th>Останній зв'язок</th>
									<th class="text-center">Алерти</th>
									<th></th>
								</tr>
							</thead>
							<tbody>
								${problem_agents
									.map(
										(agent) => `
									<tr class="${agent.has_critical ? "table-danger" : "table-warning"}">
										<td>
											<strong>${agent.hostname || agent.name}</strong>
										</td>
										<td>
											<span class="badge badge-${getStatusColor(agent.status)}">${agent.status}</span>
										</td>
										<td>${agent.last_seen ? frappe.datetime.prettyDate(agent.last_seen) : "-"}</td>
										<td class="text-center">
											<span class="badge badge-${agent.has_critical ? "danger" : "warning"}">${agent.alert_count}</span>
										</td>
										<td class="text-right">
											<a href="/app/oiagent/${agent.name}" class="btn btn-xs btn-default">
												<i class="fa fa-eye"></i>
											</a>
										</td>
									</tr>
								`
									)
									.join("")}
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
		`
				: `
		<div class="row mb-4">
			<div class="col-12">
				<div class="alert alert-success">
					<i class="fa fa-check-circle"></i> Всі агенти працюють нормально. Немає активних проблем.
				</div>
			</div>
		</div>
		`
		}

		<div class="text-muted text-right">
			<small>Останнє оновлення: ${frappe.datetime.now_datetime()}</small>
		</div>
	`);
}

function renderStatCard(title, value, color, icon) {
	const colorMap = {
		blue: "#5e64ff",
		green: "#28a745",
		red: "#dc3545",
		orange: "#fd7e14",
		yellow: "#ffc107",
		gray: "#6c757d",
	};

	return `
		<div class="card stat-card" style="border-left: 4px solid ${colorMap[color] || colorMap.blue};">
			<div class="card-body py-3">
				<div class="d-flex justify-content-between align-items-center">
					<div>
						<h3 class="mb-0" style="color: ${colorMap[color] || colorMap.blue};">${value}</h3>
						<small class="text-muted">${title}</small>
					</div>
					<div>
						<i class="fa ${icon} fa-2x" style="color: ${colorMap[color] || colorMap.blue}; opacity: 0.3;"></i>
					</div>
				</div>
			</div>
		</div>
	`;
}

function renderProgressCard(title, value, highCount) {
	const color = value > 90 ? "#dc3545" : value > 70 ? "#ffc107" : "#28a745";

	return `
		<div class="card">
			<div class="card-body">
				<div class="d-flex justify-content-between mb-2">
					<span>${title}</span>
					<span style="color: ${color}; font-weight: bold;">${value}%</span>
				</div>
				<div class="progress" style="height: 8px;">
					<div class="progress-bar" role="progressbar"
						style="width: ${value}%; background-color: ${color};"
						aria-valuenow="${value}" aria-valuemin="0" aria-valuemax="100">
					</div>
				</div>
				${
					highCount > 0
						? `
					<small class="text-danger mt-1 d-block">
						<i class="fa fa-exclamation-triangle"></i> ${highCount} агентів з високим використанням
					</small>
				`
						: ""
				}
			</div>
		</div>
	`;
}

function renderAlertsByType(byType) {
	return Object.entries(byType)
		.map(
			([type, count]) => `
		<span class="badge badge-secondary mr-2 mb-1" style="font-size: 0.9em;">
			${type}: <strong>${count}</strong>
		</span>
	`
		)
		.join("");
}

function getStatusColor(status) {
	const colors = {
		Активний: "success",
		Неактивний: "secondary",
		Офлайн: "danger",
	};
	return colors[status] || "secondary";
}
