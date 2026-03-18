/* global vis */
frappe.pages["network-topology"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Карта Мережі",
		single_column: true,
	});

	// Load vis-network via CDN
	frappe.require("https://unpkg.com/vis-network/standalone/umd/vis-network.min.js", function () {
		// Vis.js needs font awesome specifically for the canvas rendering
		frappe.require(
			"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
			function () {
				// We need to wait a tiny bit to ensure FA fonts are actually loaded by browser before vis.js draws on canvas
				document.fonts.ready.then(function () {
					init_topology(page);
				});
			}
		);
	});
};

function init_topology(page) {
	let $container = $(`
		<div class="topology-container" style="display: flex; height: calc(100vh - 180px); gap: 15px;">
			<div id="vis-network-map" style="flex: 1; border: 1px solid #d1d8dd; border-radius: 4px; background: #f8f9fa;"></div>
			<div id="topology-sidebar" style="width: 300px; display: none; padding: 15px; border: 1px solid #d1d8dd; border-radius: 4px; background: white; box-shadow: -2px 0 5px rgba(0,0,0,0.05);">
				<h4 id="side-title" style="margin-top: 0;">Asset</h4>
				<hr>
				<div id="side-content" style="line-height: 1.6; font-size: 14px;"></div>
				<button id="btn-open-asset" class="btn btn-primary btn-sm mt-3 w-100">Відкрити картку</button>
			</div>
		</div>
	`).appendTo(page.main);

	let map_container = $container.find("#vis-network-map")[0];
	let $sidebar = $container.find("#topology-sidebar");

	frappe.call({
		method: "orange_inventory.orange_inventory.page.network_topology.network_topology.get_topology_data",
		callback: function (r) {
			if (r.message) {
				var nodes = new vis.DataSet(r.message.nodes);
				var edges = new vis.DataSet(r.message.edges);

				let hide_discovered = false;

				var nodesView = new vis.DataView(nodes, {
					filter: function (node) {
						if (
							hide_discovered &&
							node.label &&
							node.label.startsWith("Discovered-")
						) {
							return false;
						}
						return true;
					},
				});

				var edgesView = new vis.DataView(edges, {
					filter: function (edge) {
						if (hide_discovered) {
							let fromNode = nodes.get(edge.from);
							let toNode = nodes.get(edge.to);
							if (
								fromNode &&
								fromNode.label &&
								fromNode.label.startsWith("Discovered-")
							)
								return false;
							if (toNode && toNode.label && toNode.label.startsWith("Discovered-"))
								return false;
						}
						return true;
					},
				});

				var data = {
					nodes: nodesView,
					edges: edgesView,
				};

				let filter_field = page.add_field({
					fieldname: "hide_discovered",
					label: "Приховати Discovered",
					fieldtype: "Check",
					change: function () {
						hide_discovered = filter_field.get_value();
						nodesView.refresh();
						edgesView.refresh();
					},
				});

				var options = {
					physics: {
						stabilization: {
							iterations: 200, // run a bit of stabilization initially
						},
						barnesHut: {
							gravitationalConstant: -2000,
							springConstant: 0.04,
							springLength: 95,
						},
					},
					edges: {
						smooth: {
							type: "continuous",
						},
					},
					interaction: {
						tooltipDelay: 200,
						hideEdgesOnDrag: true,
						hover: true,
					},
				};

				var network = new vis.Network(map_container, data, options);

				network.on("click", function (params) {
					if (params.nodes.length > 0) {
						let nodeId = params.nodes[0];
						let nodeData = nodes.get(nodeId);

						$sidebar.show();
						$sidebar.find("#side-title").text(nodeData.label);
						$sidebar.find("#side-content").html(nodeData.title);

						$sidebar
							.find("#btn-open-asset")
							.off("click")
							.on("click", function () {
								frappe.set_route("Form", "oiAsset", nodeId);
							});
					} else {
						$sidebar.hide();
					}
				});

				page.add_inner_button("Стабілізувати", function () {
					network.physics.options.enabled = true;
					network.stabilize();
				});

				page.add_inner_button("Оновити", function () {
					frappe.set_route("network-topology");
					setTimeout(() => location.reload(), 100);
				});
			} else {
				frappe.msgprint("Немає даних для побудови графа.");
			}
		},
	});
}
