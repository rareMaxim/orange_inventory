# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import fmt_money


class oiAssetAcceptance(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from orange_inventory.orange_inventory.doctype.oiasset_acceptance_item.oiasset_acceptance_item import oiAssetAcceptanceItem

        amended_from: DF.Link | None
        asset_owner: DF.Link
        basis_doc_no: DF.Data
        category_totals: DF.TextEditor | None
        counterparty: DF.Link
        document_type: DF.Literal["\u0420\u0456\u0448\u0435\u043d\u043d\u044f",
                                  "\u041d\u0430\u043a\u0430\u0437", "\u0414\u043e\u0433\u043e\u0432\u0456\u0440"]
        items: DF.Table[oiAssetAcceptanceItem]
        posting_date: DF.Date
        title: DF.SmallText
        total_amount: DF.Currency
        total_quantity: DF.Int
    # end: auto-generated types
