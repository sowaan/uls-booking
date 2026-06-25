import frappe


def execute():
	"""
	Drop unused custom columns from tabSales Invoice to fix MySQL row-size-too-large error
	during migration (OperationalError 1118).

	Section Break / layout fields have no DB column, so only the six Data/Link/Check
	fields are dropped here. All seven Custom Field documents are deleted so Frappe
	does not re-create them on the next migrate.
	"""

	COLUMNS_TO_DROP = [
		"custom_inserted",
		"custom_booking",
		"custom_duty_and_taxes_template",
		"custom_type",
		"custom_dt_vendor",
		"custom_invoice_logs",
	]

	CUSTOM_FIELD_RECORDS_TO_DELETE = COLUMNS_TO_DROP + ["custom_sales_invoice_log"]

	existing_columns = {
		row[0]
		for row in frappe.db.sql(
			"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
			"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tabSales Invoice'"
		)
	}

	columns_present = [col for col in COLUMNS_TO_DROP if col in existing_columns]

	if columns_present:
		drop_clause = ", ".join(f"DROP COLUMN `{col}`" for col in columns_present)
		frappe.db.sql(f"ALTER TABLE `tabSales Invoice` {drop_clause}")
		frappe.db.commit()

	for fieldname in CUSTOM_FIELD_RECORDS_TO_DELETE:
		if frappe.db.exists("Custom Field", f"Sales Invoice-{fieldname}"):
			frappe.db.delete("Custom Field", {"name": f"Sales Invoice-{fieldname}"})

	frappe.db.commit()
