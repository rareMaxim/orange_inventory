// Copyright (c) 2025, Maxim Sysoev and contributors
// For license information, please see license.txt

frappe.ui.form.on("oiNetworkPort", {
	refresh(frm) {
		// Застосовуємо динамічний фільтр до поля "connection"
		frm.set_query("connection", function () {
			return {
				filters: {
					// Показувати тільки ті порти, які належать обраному "підключеному пристрою"
					asset: frm.doc.connected_asset,
				},
			};
		});
		frm.set_query("connected_asset", function () {
			return {
				filters: {
					// Тепер фільтруємо за полем безпосередньо в Активі. Це набагато швидше і надійніше.
					is_network_device: 1,
				},
			};
		});
	},
	/**
	 * Ця функція спрацьовує, коли користувач змінює значення в полі "Підключений пристрій".
	 */
	connected_asset: function (frm) {
		// Очищуємо поле "Підключений порт", оскільки пристрій змінився
		frm.set_value("connection", null);

		// Одразу оновлюємо фільтри для поля "Підключений порт"
		// Це гарантує, що користувач побачить тільки порти нового обраного пристрою.
		frm.set_query("connection", function () {
			return {
				filters: {
					asset: frm.doc.connected_asset,
				},
			};
		});
	},
});
