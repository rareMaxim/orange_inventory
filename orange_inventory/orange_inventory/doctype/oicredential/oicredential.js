frappe.ui.form.on("oiCredential", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button("Показати пароль", () => {
			// 1) просимо причину
			frappe.prompt(
				[
					{
						fieldname: "reason",
						fieldtype: "Small Text",
						label: "Причина перегляду",
						reqd: 1,
						description: "Опишіть підставу/контекст доступу",
					},
				],
				async (values) => {
					// 2) тягнемо секрет із сервера
					const r = await frappe.call({
						method: "orange_inventory.api.reveal_secret",
						args: { credential: frm.doc.name, reason: values.reason },
						freeze: true,
						freeze_message: "Отримання секрету...",
					});

					const secret = r.message || "";
					if (!secret) {
						frappe.msgprint(__("Порожній секрет або доступ заборонено."));
						return;
					}

					// 3) діалог із копіюванням
					const d = new frappe.ui.Dialog({
						title: "Секрет",
						fields: [
							{
								fieldname: "secret_html",
								fieldtype: "HTML",
							},
						],
						primary_action_label: "Копіювати",
						primary_action: () => {
							safeCopyToClipboard(secret)
								.then(() => {
									frappe.show_alert({
										message: "Скопійовано в буфер обміну",
										indicator: "green",
									});
									d.hide();
									wipeSecret();
								})
								.catch(() => {
									frappe.msgprint(
										__("Не вдалось скопіювати. Спробуйте вручну.")
									);
								});
						},
						secondary_action_label: "Закрити",
						secondary_action: () => {
							d.hide();
							wipeSecret();
						},
					});

					// Вставляємо безпечний HTML (без зайвих атрибутів)
					const esc = frappe.utils.escape_html(secret);
					d.fields_dict.secret_html.$wrapper.html(`
            <div style="display:grid; gap:8px">
              <div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
                          font-size:13px; padding:8px 10px; border:1px solid var(--border-color, #e5e7eb);
                          border-radius:6px; background:#fff; word-break:break-all;">
                ${esc}
              </div>
              <div class="text-muted" style="font-size:11px;">Пароль не зберігається у формі та зникне після закриття діалогу.</div>
            </div>
          `);

					// Очищення секрету при закритті будь-яким способом
					d.$wrapper.on("hidden.bs.modal", () => wipeSecret());
					d.show();

					// локальна утиліта очищення
					function wipeSecret() {
						try {
							d.fields_dict.secret_html.$wrapper.empty();
						} catch (e) {
							console.log("wipeSecret");
						}
					}
				},
				"Підтвердження",
				"Показати"
			);
		}).addClass("btn-primary");
	},
});

/** Копіювання з запасним сценарієм */
async function safeCopyToClipboard(text) {
	if (navigator.clipboard && navigator.clipboard.writeText) {
		await navigator.clipboard.writeText(text);
		return;
	}
}
