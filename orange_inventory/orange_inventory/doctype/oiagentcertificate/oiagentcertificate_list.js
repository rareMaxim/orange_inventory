frappe.listview_settings["oiAgentCertificate"] = {
	onload(listview) {
		listview.page.add_action_item(__("Видалити обрані на агентах"), () => {
			let selected = listview.get_checked_items();
			if (!selected.length) {
				frappe.msgprint(__("Оберіть сертифікати галочками"));
				return;
			}

			// Збираємо сертифікати згруповані по агентах
			let certs_by_agent = {};
			selected.forEach((d) => {
				if (!certs_by_agent[d.agent]) {
					certs_by_agent[d.agent] = [];
				}
				certs_by_agent[d.agent].push({
					name: d.name,
					file_name: d.file_name,
					subject_cn: d.subject_cn,
				});
			});

			let agent_count = Object.keys(certs_by_agent).length;
			frappe.confirm(
				__("Створити команду видалення {0} сертифікат(ів) на {1} агент(ах)?", [
					selected.length,
					agent_count,
				]),
				() => {
					frappe.call({
						method: "orange_inventory.orange_inventory.doctype.oiagentcertificate.oiagentcertificate.create_delete_certs_command",
						args: { certs_by_agent: certs_by_agent },
						freeze: true,
						freeze_message: __("Створюємо команди..."),
						callback(r) {
							if (r.message) {
								let msg = r.message;
								let parts = [];
								if (msg.created && msg.created.length) {
									parts.push(
										"<b>Створено команди:</b><br>" +
											msg.created
												.map(
													(c) =>
														`&bull; <a href="/app/oiagentcommand/${c.command}">${c.agent}</a> (${c.count} серт.)`
												)
												.join("<br>")
									);
								}
								if (msg.skipped && msg.skipped.length) {
									parts.push(
										"<b>Пропущено:</b><br>" +
											msg.skipped
												.map((s) => `&bull; ${s.agent}: ${s.reason}`)
												.join("<br>")
									);
								}
								frappe.msgprint({
									title: __("Результат"),
									indicator:
										msg.created && msg.created.length ? "green" : "orange",
									message: parts.join("<br><br>"),
								});
								listview.clear_checked_items();
							}
						},
					});
				}
			);
		});
	},

	get_indicator(doc) {
		const colors = {
			Дійсний: "blue",
			"Скоро закінчується": "orange",
			Протермінований: "red",
			"Ще не дійсний": "purple",
		};
		return [__(doc.status), colors[doc.status] || "grey", `status,=,${doc.status}`];
	},
};
