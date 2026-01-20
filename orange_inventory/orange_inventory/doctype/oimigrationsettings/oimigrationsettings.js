// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiMigrationSettings", {
	refresh(frm) {
		// Оновлюємо статус при завантаженні
		frm.trigger("refresh_status_btn");

		// Додаємо кнопку очищення логу
		frm.add_custom_button(__("Очистити лог"), () => {
			frm.call("clear_log").then(() => {
				frm.refresh();
				frappe.show_alert({ message: __("Лог очищено"), indicator: "green" });
			});
		});

		// Кнопка для перегляду Employee Mapping
		frm.add_custom_button(
			__("Employee Mapping"),
			() => {
				frappe.set_route("List", "oiEmployeeMapping");
			},
			__("Переглянути")
		);

		// Кнопка для перегляду Organization Mapping
		frm.add_custom_button(
			__("Organization Mapping"),
			() => {
				frappe.set_route("List", "oiOrganizationMapping");
			},
			__("Переглянути")
		);

		// Кнопка для перегляду незамаплених співробітників
		frm.add_custom_button(
			__("Незамаплені Employee"),
			() => {
				show_unmapped_employees_dialog(frm);
			},
			__("Переглянути")
		);

		// Кнопка для перегляду незамаплених організацій
		frm.add_custom_button(
			__("Незамаплені Organization"),
			() => {
				show_unmapped_organizations_dialog(frm);
			},
			__("Переглянути")
		);
	},

	refresh_status_btn(frm) {
		frm.call("refresh_status").then(() => {
			frm.refresh_fields();
		});
	},

	auto_populate_employee_btn(frm) {
		frappe.confirm(
			__("Автоматично створити Employee Mapping на основі імен співробітників?"),
			() => {
				frappe.show_progress(__("Автозаповнення..."), 50, 100);
				frm.call("auto_populate_employee_mapping").then((r) => {
					frappe.hide_progress();
					frm.refresh();

					const result = r.message || {};
					frappe.msgprint({
						title: __("Результат"),
						message: `Створено: ${result.created || 0}<br>Пропущено: ${
							result.skipped || 0
						}`,
						indicator: result.created > 0 ? "green" : "orange",
					});
				});
			}
		);
	},

	auto_populate_organization_btn(frm) {
		frappe.confirm(
			__("Автоматично створити Organization Mapping на основі назв організацій?"),
			() => {
				frappe.show_progress(__("Автозаповнення..."), 50, 100);
				frm.call("auto_populate_organization_mapping").then((r) => {
					frappe.hide_progress();
					frm.refresh();

					const result = r.message || {};
					frappe.msgprint({
						title: __("Результат"),
						message: `Створено: ${result.created || 0}<br>Пропущено: ${
							result.skipped || 0
						}`,
						indicator: result.created > 0 ? "green" : "orange",
					});
				});
			}
		);
	},

	migrate_employee_btn(frm) {
		frappe.confirm(
			__(
				"<strong>УВАГА!</strong> Ця операція замінить всі посилання на oiEmployee на hromsEmployee в базі даних.<br><br>Переконайтесь, що:<br>- Зроблено backup<br>- Всі mapping записи перевірені<br><br>Продовжити?"
			),
			() => {
				frappe.show_progress(__("Міграція Employee..."), 30, 100);
				frm.call("migrate_employee_references").then((r) => {
					frappe.hide_progress();
					frm.refresh();

					const result = r.message || {};
					frappe.msgprint({
						title: __("Міграція завершена"),
						message: `Оновлено записів: ${result.updated || 0}`,
						indicator: "green",
					});
				});
			}
		);
	},

	migrate_organization_btn(frm) {
		frappe.confirm(
			__(
				"<strong>УВАГА!</strong> Ця операція замінить всі посилання на oiOrganization на hromsOrgStructure в базі даних.<br><br>Переконайтесь, що:<br>- Зроблено backup<br>- Всі mapping записи перевірені<br><br>Продовжити?"
			),
			() => {
				frappe.show_progress(__("Міграція Organization..."), 30, 100);
				frm.call("migrate_organization_references").then((r) => {
					frappe.hide_progress();
					frm.refresh();

					const result = r.message || {};
					frappe.msgprint({
						title: __("Міграція завершена"),
						message: `Оновлено записів: ${result.updated || 0}`,
						indicator: "green",
					});
				});
			}
		);
	},
});

// Функція для екранування HTML атрибутів
function escapeAttr(str) {
	if (!str) return "";
	return String(str)
		.replace(/&/g, "&amp;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
}

// Функція для екранування HTML контенту
function escapeHtml(str) {
	if (!str) return "";
	return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function show_unmapped_employees_dialog(frm) {
	frappe
		.call({
			method: "run_doc_method",
			args: {
				dt: frm.doc.doctype,
				dn: frm.doc.name,
				method: "get_unmapped_employees",
			},
			freeze: true,
			freeze_message: __("Завантаження..."),
		})
		.then((r) => {
			const data = r.message || [];

			if (data.length === 0) {
				frappe.msgprint({
					title: __("Результат"),
					message: __("Всі співробітники замаплені!"),
					indicator: "green",
				});
				return;
			}

			let html = `
			<div style="max-height: 400px; overflow-y: auto;">
				<table class="table table-bordered table-sm" id="unmapped-employees-table">
					<thead style="position: sticky; top: 0; background: #f5f5f5;">
						<tr>
							<th>oiEmployee</th>
							<th>ПІБ</th>
							<th>Організація</th>
							<th>Можливий збіг (hromsEmployee)</th>
							<th>Дія</th>
						</tr>
					</thead>
					<tbody>
		`;

			data.forEach((emp, idx) => {
				const match = emp.possible_match;
				const matchHtml = match
					? `<span style="color: green;">${escapeHtml(
							match.full_name
					  )}</span><br><small>${escapeHtml(match.name)}</small>`
					: `<span style="color: orange;">Не знайдено</span>`;

				const actionBtn = match
					? `<button class="btn btn-xs btn-success btn-map-employee" data-old="${escapeAttr(
							emp.name
					  )}" data-new="${escapeAttr(match.name)}">Замапити</button>`
					: `<button class="btn btn-xs btn-primary btn-select-employee" data-old="${escapeAttr(
							emp.name
					  )}" data-oldname="${escapeAttr(emp.full_name)}">Вибрати</button>`;

				html += `
				<tr>
					<td><a href="/app/oiemployee/${escapeAttr(emp.name)}">${escapeHtml(emp.name)}</a></td>
					<td>${escapeHtml(emp.full_name) || "-"}</td>
					<td>${escapeHtml(emp.organization) || "-"}</td>
					<td>${matchHtml}</td>
					<td>${actionBtn}</td>
				</tr>
			`;
			});

			html += `
					</tbody>
				</table>
			</div>
		`;

			const d = new frappe.ui.Dialog({
				title: __(`Незамаплені співробітники (${data.length})`),
				size: "extra-large",
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "content",
						options: html,
					},
				],
			});

			// Зберігаємо посилання на діалог та форму
			window._migration_dialog = d;
			window._migration_frm = frm;

			// Підключаємо обробники подій через делегування
			d.$wrapper.on("click", ".btn-map-employee", function () {
				const oldEmp = $(this).data("old");
				const newEmp = $(this).data("new");
				createEmployeeMapping(oldEmp, newEmp);
			});

			d.$wrapper.on("click", ".btn-select-employee", function () {
				const oldEmp = $(this).data("old");
				const oldName = $(this).data("oldname");
				selectEmployeeMapping(oldEmp, oldName);
			});

			d.show();
		});
}

function show_unmapped_organizations_dialog(frm) {
	frappe
		.call({
			method: "run_doc_method",
			args: {
				dt: frm.doc.doctype,
				dn: frm.doc.name,
				method: "get_unmapped_organizations",
			},
			freeze: true,
			freeze_message: __("Завантаження..."),
		})
		.then((r) => {
			const data = r.message || [];

			if (data.length === 0) {
				frappe.msgprint({
					title: __("Результат"),
					message: __("Всі організації замаплені!"),
					indicator: "green",
				});
				return;
			}

			let html = `
			<div style="max-height: 400px; overflow-y: auto;">
				<table class="table table-bordered table-sm" id="unmapped-organizations-table">
					<thead style="position: sticky; top: 0; background: #f5f5f5;">
						<tr>
							<th>oiOrganization</th>
							<th>Назва</th>
							<th>ЄДРПОУ</th>
							<th>Можливий збіг (hromsOrgStructure)</th>
							<th>Дія</th>
						</tr>
					</thead>
					<tbody>
		`;

			data.forEach((org) => {
				const match = org.possible_match;
				const matchHtml = match
					? `<span style="color: green;">${escapeHtml(
							match.department_name
					  )}</span><br><small>${escapeHtml(match.name)}</small>`
					: `<span style="color: orange;">Не знайдено</span>`;

				const actionBtn = match
					? `<button class="btn btn-xs btn-success btn-map-org" data-old="${escapeAttr(
							org.name
					  )}" data-new="${escapeAttr(match.name)}">Замапити</button>`
					: `<button class="btn btn-xs btn-primary btn-select-org" data-old="${escapeAttr(
							org.name
					  )}" data-oldname="${escapeAttr(org.organization_name)}">Вибрати</button>`;

				html += `
				<tr>
					<td><a href="/app/oiorganization/${escapeAttr(org.name)}">${escapeHtml(org.name)}</a></td>
					<td>${escapeHtml(org.organization_name) || "-"}</td>
					<td>${escapeHtml(org.tax_code) || "-"}</td>
					<td>${matchHtml}</td>
					<td>${actionBtn}</td>
				</tr>
			`;
			});

			html += `
					</tbody>
				</table>
			</div>
		`;

			const d = new frappe.ui.Dialog({
				title: __(`Незамаплені організації (${data.length})`),
				size: "extra-large",
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "content",
						options: html,
					},
				],
			});

			window._migration_dialog = d;
			window._migration_frm = frm;

			// Підключаємо обробники подій через делегування
			d.$wrapper.on("click", ".btn-map-org", function () {
				const oldOrg = $(this).data("old");
				const newOrg = $(this).data("new");
				createOrganizationMapping(oldOrg, newOrg);
			});

			d.$wrapper.on("click", ".btn-select-org", function () {
				const oldOrg = $(this).data("old");
				const oldName = $(this).data("oldname");
				selectOrganizationMapping(oldOrg, oldName);
			});

			d.show();
		});
}

// Функції для створення mapping
function createEmployeeMapping(oldEmployee, newEmployee) {
	const frm = window._migration_frm;
	frm.call("create_employee_mapping", {
		old_employee: oldEmployee,
		new_employee: newEmployee,
	}).then(() => {
		frappe.show_alert({ message: __("Mapping створено"), indicator: "green" });
		window._migration_dialog.hide();
		frm.refresh();
	});
}

function createOrganizationMapping(oldOrg, newOrg) {
	const frm = window._migration_frm;
	frm.call("create_organization_mapping", {
		old_organization: oldOrg,
		new_organization: newOrg,
	}).then(() => {
		frappe.show_alert({ message: __("Mapping створено"), indicator: "green" });
		window._migration_dialog.hide();
		frm.refresh();
	});
}

function selectEmployeeMapping(oldEmployee, oldName) {
	const frm = window._migration_frm;

	const selectDialog = new frappe.ui.Dialog({
		title: __("Вибрати hromsEmployee для: ") + oldName,
		fields: [
			{
				fieldtype: "Link",
				fieldname: "new_employee",
				label: __("hromsEmployee"),
				options: "hromsEmployee",
				reqd: 1,
			},
		],
		primary_action_label: __("Замапити"),
		primary_action: (values) => {
			selectDialog.hide();
			frm.call("create_employee_mapping", {
				old_employee: oldEmployee,
				new_employee: values.new_employee,
			}).then(() => {
				frappe.show_alert({ message: __("Mapping створено"), indicator: "green" });
				window._migration_dialog.hide();
				frm.refresh();
			});
		},
	});

	selectDialog.show();
}

function selectOrganizationMapping(oldOrg, oldName) {
	const frm = window._migration_frm;

	const selectDialog = new frappe.ui.Dialog({
		title: __("Вибрати hromsOrgStructure для: ") + oldName,
		fields: [
			{
				fieldtype: "Link",
				fieldname: "new_organization",
				label: __("hromsOrgStructure"),
				options: "hromsOrgStructure",
				reqd: 1,
			},
		],
		primary_action_label: __("Замапити"),
		primary_action: (values) => {
			selectDialog.hide();
			frm.call("create_organization_mapping", {
				old_organization: oldOrg,
				new_organization: values.new_organization,
			}).then(() => {
				frappe.show_alert({ message: __("Mapping створено"), indicator: "green" });
				window._migration_dialog.hide();
				frm.refresh();
			});
		},
	});

	selectDialog.show();
}
