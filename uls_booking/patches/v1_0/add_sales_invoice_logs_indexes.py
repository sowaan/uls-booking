import frappe # type: ignore

def execute():
    indexes = frappe.db.sql("""
        SHOW INDEX
        FROM `tabSales Invoice Logs`
        WHERE Key_name = 'idx_shipment_manifest_status'
    """, as_dict=True)

    if not indexes:
        frappe.db.sql("""
            ALTER TABLE `tabSales Invoice Logs`
            ADD INDEX `idx_shipment_manifest_status`
            (`shipment_number`, `manifest_input_date`, `sales_invoice_status`)
        """)

