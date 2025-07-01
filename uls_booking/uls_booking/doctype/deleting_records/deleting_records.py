# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DeletingRecords(Document):
	pass

@frappe.whitelist()
def delete_sales_invoice_links(docname):
    # Clear sales_invoice where it is "set"
    frappe.db.sql("""
        UPDATE `tabSales Invoice Logs`
        SET sales_invoice = ''
        WHERE sales_invoice IS NOT NULL AND sales_invoice != ''
    """)

    # Delete all rows from Dispute Invoice Number child table
    frappe.db.sql("DELETE FROM `tabDispute Invoice Number`")

    return "Sales Invoice fields cleared and all Dispute Invoice Number records deleted (via SQL)."
