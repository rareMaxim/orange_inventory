frappe.pages["solution-assets"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Активи за Рішенням",
		single_column: true,
	});

	wrapper.solution_assets_page = new SolutionAssetsPage(page);
};

frappe.pages["solution-assets"].on_page_show = function (wrapper) {
	// Перевіряємо, чи є рішення в URL
	const urlParams = new URLSearchParams(window.location.search);
	const decision = urlParams.get("decision");
	if (decision && wrapper.solution_assets_page) {
		wrapper.solution_assets_page.decision_field.set_value(decision);
	}
};

class SolutionAssetsPage {
	constructor(page) {
		this.page = page;
		this.make();
	}

	make() {
		this.make_filters();
		this.make_results_area();
	}

	make_filters() {
		// Поле вибору рішення
		this.decision_field = this.page.add_field({
			fieldname: "decision",
			label: __("Рішення"),
			fieldtype: "Link",
			options: "oiBasisDoc",
			change: () => {
				this.load_assets();
			},
		});
	}

	make_results_area() {
		// Контейнер для результатів
		this.results_wrapper = $(`
			<div class="solution-assets-results" style="margin-top: 20px;">
				<div class="text-muted text-center" style="padding: 40px;">
					${__("Виберіть рішення для перегляду активів")}
				</div>
			</div>
		`).appendTo(this.page.body);
	}

	load_assets() {
		const decision = this.decision_field.get_value();
		if (!decision) {
			this.results_wrapper.html(`
				<div class="text-muted text-center" style="padding: 40px;">
					${__("Виберіть рішення для перегляду активів")}
				</div>
			`);
			return;
		}

		this.results_wrapper.html(`
			<div class="text-center" style="padding: 40px;">
				<div class="spinner-border text-primary" role="status"></div>
				<div class="mt-2">${__("Завантаження...")}</div>
			</div>
		`);

		frappe.call({
			method: "orange_inventory.orange_inventory.page.solution_assets.solution_assets.get_assets_by_decision",
			args: { decision: decision },
			callback: (r) => {
				if (r.message) {
					this.render_results(r.message);
				}
			},
			error: () => {
				this.results_wrapper.html(`
					<div class="text-danger text-center" style="padding: 40px;">
						${__("Помилка завантаження даних")}
					</div>
				`);
			},
		});
	}

	render_results(data) {
		if (!data.assets || data.assets.length === 0) {
			this.results_wrapper.html(`
				<div class="text-muted text-center" style="padding: 40px;">
					${__("Немає активів за цим рішенням")}
				</div>
			`);
			return;
		}

		// Групування активів по власнику
		const grouped = this.group_by_owner(data.assets);

		// Інформація про рішення
		let decision_info = `
			<div class="card mb-4">
				<div class="card-header">
					<strong>${__("Рішення")}: ${data.decision_info.full_title || data.decision_info.title}</strong>
				</div>
				<div class="card-body">
					<div class="row">
						<div class="col-md-4">
							<strong>${__("Номер")}:</strong> ${data.decision_info.decision_number}
						</div>
						<div class="col-md-4">
							<strong>${__("Дата")}:</strong> ${frappe.datetime.str_to_user(data.decision_info.decision_date)}
						</div>
						<div class="col-md-4">
							<strong>${__("Всього активів")}:</strong> ${data.assets.length}
						</div>
					</div>
				</div>
			</div>
		`;

		// Таблиці активів згруповані по власнику
		let assets_tables = "";
		for (const [ownerKey, ownerData] of Object.entries(grouped)) {
			const ownerName = ownerData.owner_name || __("Без власника");
			const ownerLink = ownerData.owner_id
				? `<a href="/app/oiorganization/${ownerData.owner_id}">${ownerName}</a>`
				: ownerName;

			assets_tables += `
				<div class="card mb-4">
					<div class="card-header d-flex justify-content-between align-items-center">
						<div>
							<strong>${ownerLink}</strong>
							<span class="text-muted ml-2">(${ownerData.assets.length} ${__("активів")})</span>
						</div>
						<div>
							<span class="badge badge-primary">${__("Кількість")}: ${ownerData.total_quantity}</span>
							<span class="badge badge-success ml-1">${__("Вартість")}: ${frappe.format(ownerData.total_value, {
				fieldtype: "Currency",
			})}</span>
						</div>
					</div>
					<div class="card-body p-0">
						<table class="table table-bordered table-hover mb-0">
							<thead class="thead-light">
								<tr>
									<th style="width: 30px;"></th>
									<th>${__("Назва")}</th>
									<th>${__("Серійний номер")}</th>
									<th>${__("Інвентарний номер")}</th>
									<th>${__("Статус")}</th>
									<th>${__("Кількість")}</th>
									<th>${__("Вартість")}</th>
								</tr>
							</thead>
							<tbody>
								${ownerData.assets
									.map(
										(asset) => `
									<tr class="asset-row" data-asset="${asset.name}">
										<td class="text-center">
											<button class="btn btn-xs btn-default toggle-history" data-asset="${asset.name}" title="${__(
											"Історія передачі"
										)}">
												<i class="fa fa-chevron-right"></i>
											</button>
										</td>
										<td>
											<a href="/app/oiasset/${asset.name}">${asset.asset_name}</a>
										</td>
										<td>${asset.serial_no || "-"}</td>
										<td>${asset.inventory_no || "-"}</td>
										<td>
											<span class="badge ${this.get_status_class(asset.status)}">${asset.status}</span>
										</td>
										<td class="text-right">${asset.quantity}</td>
										<td class="text-right">${frappe.format(asset.total, { fieldtype: "Currency" })}</td>
									</tr>
									<tr class="history-row d-none" data-asset="${asset.name}">
										<td colspan="7" class="p-0">
											<div class="history-content p-3 bg-light">
												${this.render_movement_history(asset.movement_history)}
											</div>
										</td>
									</tr>
								`
									)
									.join("")}
							</tbody>
						</table>
					</div>
				</div>
			`;
		}

		// Загальний підсумок
		let summary = `
			<div class="card mt-4">
				<div class="card-header">
					<strong>${__("Загальний підсумок")}</strong>
				</div>
				<div class="card-body">
					<div class="row">
						<div class="col-md-3">
							<strong>${__("Загальна кількість")}:</strong> ${data.summary.total_quantity}
						</div>
						<div class="col-md-3">
							<strong>${__("Загальна вартість")}:</strong> ${frappe.format(data.summary.total_value, {
			fieldtype: "Currency",
		})}
						</div>
						<div class="col-md-3">
							<strong>${__("Власників")}:</strong> ${Object.keys(grouped).length}
						</div>
						<div class="col-md-3">
							<strong>${__("Статуси")}:</strong>
							${Object.entries(data.summary.status_counts)
								.map(
									([status, count]) =>
										`<span class="badge ${this.get_status_class(
											status
										)} mr-1">${status}: ${count}</span>`
								)
								.join("")}
						</div>
					</div>
				</div>
			</div>
		`;

		this.results_wrapper.html(decision_info + assets_tables + summary);

		// Обробник кліку для розгортання історії
		this.results_wrapper.find(".toggle-history").on("click", function (e) {
			e.stopPropagation();
			const assetName = $(this).data("asset");
			const historyRow = $(`.history-row[data-asset="${assetName}"]`);
			const icon = $(this).find("i");

			historyRow.toggleClass("d-none");
			icon.toggleClass("fa-chevron-right fa-chevron-down");
		});
	}

	group_by_owner(assets) {
		const grouped = {};

		for (const asset of assets) {
			const ownerKey = asset.current_owner || "_no_owner";
			if (!grouped[ownerKey]) {
				grouped[ownerKey] = {
					owner_id: asset.current_owner,
					owner_name: asset.current_owner_name,
					assets: [],
					total_quantity: 0,
					total_value: 0,
				};
			}
			grouped[ownerKey].assets.push(asset);
			grouped[ownerKey].total_quantity += asset.quantity || 0;
			grouped[ownerKey].total_value += asset.total || 0;
		}

		// Сортування: спочатку з власником, потім без
		const sorted = {};
		const keys = Object.keys(grouped).sort((a, b) => {
			if (a === "_no_owner") return 1;
			if (b === "_no_owner") return -1;
			return (grouped[a].owner_name || "").localeCompare(grouped[b].owner_name || "");
		});

		for (const key of keys) {
			sorted[key] = grouped[key];
		}

		return sorted;
	}

	render_movement_history(history) {
		if (!history || history.length === 0) {
			return `<div class="text-muted">${__("Немає історії передачі")}</div>`;
		}

		return `
			<table class="table table-sm table-bordered mb-0">
				<thead>
					<tr>
						<th>${__("Дата")}</th>
						<th>${__("Тип руху")}</th>
						<th>${__("Звідки")}</th>
						<th>${__("Куди")}</th>
						<th>${__("Підстава")}</th>
					</tr>
				</thead>
				<tbody>
					${history
						.map(
							(m) => `
						<tr>
							<td>${frappe.datetime.str_to_user(m.date)}</td>
							<td>${m.movement_type}</td>
							<td>${m.from_source_name || "-"}</td>
							<td>${m.to_organization_name || "-"}</td>
							<td>
								${
									m.reference_appendix
										? `<a href="/app/oibasisdoc/${m.reference_appendix}">${
												m.reference_appendix_title || m.reference_appendix
										  }</a>`
										: "-"
								}
							</td>
						</tr>
					`
						)
						.join("")}
				</tbody>
			</table>
		`;
	}

	get_status_class(status) {
		const status_map = {
			"На складі": "badge-info",
			"В експлуатації": "badge-success",
			Передано: "badge-warning",
			"Очікує прийняття": "badge-secondary",
			Списується: "badge-danger",
			Списано: "badge-dark",
		};
		return status_map[status] || "badge-secondary";
	}
}
