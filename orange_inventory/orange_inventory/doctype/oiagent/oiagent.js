// Copyright (c) 2026, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiAgent", {
	refresh: function (frm) {
		if (!frm.is_new()) {
			// Додаємо кнопку для оновлення метрик
			frm.add_custom_button(__("Оновити метрики"), function () {
				frm.trigger("load_metrics");
			});

			// Додаємо секцію з графіками якщо її немає
			if (!frm.fields_dict.metrics_html) {
				// Метрики будуть показані в стандартному dashboard
			}

			// Завантажуємо метрики
			frm.trigger("load_metrics");
		}
	},

	load_metrics: function (frm) {
		// Отримуємо поточні метрики
		frappe.call({
			method: "orange_inventory.orange_inventory.dashboard_api.get_agent_current_metrics",
			args: { agent: frm.doc.name },
			callback: function (r) {
				if (r.message) {
					frm.trigger("render_metrics", r.message);
				}
			},
		});

		// Отримуємо історію для графіків
		frappe.call({
			method: "orange_inventory.orange_inventory.dashboard_api.get_agent_history",
			args: { agent: frm.doc.name, hours: 24 },
			callback: function (r) {
				if (r.message && r.message.count > 0) {
					frm.trigger("render_charts", r.message);
				}
			},
		});
	},

	render_metrics: function (frm, metrics) {
		// Показуємо поточні метрики у intro
		let cpu_color =
			metrics.cpu_usage > 90 ? "red" : metrics.cpu_usage > 70 ? "orange" : "green";
		let ram_color =
			metrics.ram_usage > 90 ? "red" : metrics.ram_usage > 70 ? "orange" : "green";

		let html = `
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-md-3">
					<strong>CPU:</strong>
					<span style="color: ${cpu_color}; font-weight: bold;">${metrics.cpu_usage}%</span>
				</div>
				<div class="col-md-3">
					<strong>RAM:</strong>
					<span style="color: ${ram_color}; font-weight: bold;">${metrics.ram_usage}%</span>
				</div>
				<div class="col-md-3">
					<strong>Користувач:</strong> ${metrics.current_user || "-"}
				</div>
				<div class="col-md-3">
					<strong>Uptime:</strong> ${formatUptime(metrics.uptime_seconds)}
				</div>
			</div>
		`;

		// Показуємо диски
		if (metrics.disks && metrics.disks.length > 0) {
			html += '<div class="row"><div class="col-md-12"><strong>Диски:</strong></div></div>';
			html += '<div class="row">';
			metrics.disks.forEach(function (disk) {
				let disk_color =
					disk.used_percent > 90 ? "red" : disk.used_percent > 80 ? "orange" : "green";
				html += `
					<div class="col-md-3" style="margin-top: 5px;">
						<span>${disk.drive || disk.mountpoint || "Disk"}</span>:
						<span style="color: ${disk_color};">${disk.used_percent?.toFixed(1) || 0}%</span>
						<small class="text-muted">(${formatBytes(disk.free_bytes || disk.free || 0)} вільно)</small>
					</div>
				`;
			});
			html += "</div>";
		}

		frm.set_intro(html, "blue");
	},

	render_charts: function (frm, data) {
		// Використовуємо frappe.Chart для рендерингу
		if (!data.labels || data.labels.length < 2) {
			return;
		}

		// Знаходимо або створюємо контейнер для графіків
		let $wrapper = frm.$wrapper.find(".form-dashboard");
		let $chart_area = $wrapper.find(".agent-charts");

		if ($chart_area.length === 0) {
			$chart_area = $(`
				<div class="agent-charts" style="margin: 15px 0; padding: 15px; background: var(--card-bg); border-radius: 8px;">
					<h5 style="margin-bottom: 15px;">Використання ресурсів (24 години)</h5>
					<div id="agent-resource-chart" style="height: 250px;"></div>
				</div>
			`);
			$wrapper.append($chart_area);
		}

		// Рендеримо графік
		new frappe.Chart("#agent-resource-chart", {
			title: "",
			data: {
				labels: data.labels,
				datasets: [
					{
						name: "CPU %",
						values: data.cpu,
						chartType: "line",
					},
					{
						name: "RAM %",
						values: data.ram,
						chartType: "line",
					},
					{
						name: "Disk %",
						values: data.disk,
						chartType: "line",
					},
				],
			},
			type: "line",
			height: 250,
			colors: ["#5e64ff", "#28a745", "#fd7e14"],
			lineOptions: {
				regionFill: 0,
				hideDots: data.labels.length > 50,
			},
			axisOptions: {
				xAxisMode: "tick",
				xIsSeries: true,
			},
			tooltipOptions: {
				formatTooltipX: (d) => d,
				formatTooltipY: (d) => d + "%",
			},
		});
	},
});

// Допоміжні функції
function formatUptime(seconds) {
	if (!seconds) return "-";
	const days = Math.floor(seconds / 86400);
	const hours = Math.floor((seconds % 86400) / 3600);
	const mins = Math.floor((seconds % 3600) / 60);

	if (days > 0) {
		return `${days}д ${hours}г`;
	} else if (hours > 0) {
		return `${hours}г ${mins}хв`;
	} else {
		return `${mins}хв`;
	}
}

function formatBytes(bytes) {
	if (!bytes) return "0 B";
	const k = 1024;
	const sizes = ["B", "KB", "MB", "GB", "TB"];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}
