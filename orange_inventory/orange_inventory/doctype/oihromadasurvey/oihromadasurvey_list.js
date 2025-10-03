frappe.listview_settings["oiHromadaSurvey"] = {
	onload(listview) {
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
	},
};
