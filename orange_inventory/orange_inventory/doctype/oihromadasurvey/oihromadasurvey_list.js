frappe.listview_settings["oiHromadaSurvey"] = {
	onload(listview) {
		const defaultPeriod = () => {
			const now = new Date();
			const y = now.getFullYear();
			const q = Math.floor(now.getMonth() / 3); // 1..4
			return `${y}-Q${q}`;
		};

		listview.page.add_menu_item(__("Recompute Analytics for All Groups"), () => {
			frappe.call({
				method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.recompute_all_groups",
				args: { background: 1 },
				freeze: true,
				freeze_message: __("Recomputing analytics…"),
				callback: (r) => {
					if (r.message && r.message.status === "queued") {
						frappe.show_alert({
							message: __("Analytics recompute queued"),
							indicator: "green",
						});
					} else {
						frappe.show_alert({
							message: __("Analytics recompute started"),
							indicator: "blue",
						});
					}
				},
			});
		});
		listview.page.add_menu_item(__("Export All Templates (ZIP)"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Експорт шаблонів (ZIP)"),
				fields: [
					{
						fieldtype: "Data",
						fieldname: "period",
						label: __("Період"),
						default: defaultPeriod(),
						reqd: 1,
					},
				],
				primary_action_label: __("Згенерувати ZIP"),
				primary_action: async (values) => {
					d.hide();
					const r = await frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.export_all_org_templates",
						args: { period: values.period },
						freeze: true,
						freeze_message: __("Генеруємо ZIP…"),
					});
					const url = r.message && r.message.file_url;
					url
						? window.open(url, "_blank")
						: frappe.msgprint(__("Не вдалося отримати ZIP"));
				},
			});
			d.show();
		});
		listview.page.add_menu_item(__("Export Excel Template…"), () => {
			const d = new frappe.ui.Dialog({
				title: __("Виберіть розпорядника"),
				fields: [
					{
						fieldtype: "Link",
						fieldname: "org",
						label: __("Розпорядник"),
						options: "oiOrganization",
						reqd: 1,
					},
					{
						fieldtype: "Data",
						fieldname: "period",
						label: __("Період (напр. 2025-Q3)"),
						default: defaultPeriod(),
						reqd: 1,
					},
				],
				primary_action_label: __("Згенерувати"),
				primary_action: async (values) => {
					d.hide();
					const r = await frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.export_org_template",
						args: values,
						freeze: true,
						freeze_message: __("Генеруємо шаблон…"),
					});
					const url = r.message && r.message.file_url;
					if (url) {
						frappe.show_alert({
							message: __("Шаблон збережено. Відкриваємо…"),
							indicator: "green",
						});
						window.open(url, "_blank");
					} else {
						frappe.msgprint(__("Не вдалося отримати посилання на файл"));
					}
				},
			});
			d.show();
		});
	},
};
