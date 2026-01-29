// Copyright (c) 2026, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.listview_settings["oiAgentRelease"] = {
	onload: function (listview) {
		listview.page.add_inner_button(__("Зібрати нову версію"), function () {
			frappe.confirm(__("Зібрати нову версію агента з поточного коду?"), function () {
				frappe.call({
					method: "orange_inventory.build_agent.api_build_and_release",
					freeze: true,
					freeze_message: __("Збирання агента..."),
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.msgprint({
								title: __("Успішно!"),
								indicator: "green",
								message: __(
									"Реліз {0} створено.<br>Розмір: {1} MB<br>Checksum: {2}",
									[
										r.message.release,
										(r.message.size / 1024 / 1024).toFixed(2),
										r.message.checksum.substring(0, 16) + "...",
									]
								),
							});
							listview.refresh();
						} else {
							frappe.msgprint({
								title: __("Помилка"),
								indicator: "red",
								message: r.message.error || __("Невідома помилка"),
							});
						}
					},
				});
			});
		});
	},

	get_indicator: function (doc) {
		if (doc.is_latest) {
			return [__("Актуальна"), "green", "is_latest,=,1"];
		}
		return [__("Архів"), "gray", "is_latest,=,0"];
	},
};
