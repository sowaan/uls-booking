import frappe # type: ignore

def execute():
    frappe.db.sql("""
        ALTER TABLE `tabSales Invoice Logs`
        ADD INDEX `idx_shipment_manifest_status`
        (`shipment_number`, `manifest_input_date`, `sales_invoice_status`)
    """)
