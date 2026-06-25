import frappe


def execute():
	"""
	1. Drop 6 unused custom columns from tabSales Invoice to fix MySQL error 1118
	   (Row size too large, max 65535 bytes for COMPACT row format).
	2. Convert the table to ROW_FORMAT=DYNAMIC so variable-length columns (VARCHAR)
	   can overflow to off-page storage, permanently preventing this error from
	   recurring as ERPNext or custom fields grow.
	3. Delete the 7 corresponding Custom Field documents so Frappe does not
	   re-create them on subsequent migrations.

	Section Break / layout fields have no DB column, so custom_sales_invoice_log
	is skipped in the DROP but still deleted from tabCustom Field.
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

	# Build a single ALTER TABLE that both drops unused columns and switches to
	# ROW_FORMAT=DYNAMIC. Doing this in one statement means MySQL evaluates the
	# final row size under DYNAMIC rules (VARCHAR overflow off-page), which is
	# far under the 65535 limit.
	alter_parts = [f"DROP COLUMN `{col}`" for col in columns_present]
	alter_parts.append("ROW_FORMAT=DYNAMIC")

	frappe.db.sql(f"ALTER TABLE `tabSales Invoice` {', '.join(alter_parts)}")
	frappe.db.commit()

	for fieldname in CUSTOM_FIELD_RECORDS_TO_DELETE:
		if frappe.db.exists("Custom Field", f"Sales Invoice-{fieldname}"):
			frappe.db.delete("Custom Field", {"name": f"Sales Invoice-{fieldname}"})

	frappe.db.commit()
