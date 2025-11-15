import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Invoice No"), "fieldname": "invoice_no", "fieldtype": "Data", "width": 150},
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
        {"label": _("Account No"), "fieldname": "account_no", "fieldtype": "Data", "width": 150},
        {"label": _("Shipper Name"), "fieldname": "shipper_name", "fieldtype": "Data", "width": 200},
        {"label": _("N.T.N No"), "fieldname": "ntn_no", "fieldtype": "Data", "width": 120},
        {"label": _("GST Territory/Station"), "fieldname": "gst_station", "fieldtype": "Data", "width": 180},
        {"label": _("Weight"), "fieldname": "weight", "fieldtype": "Float", "width": 100},
        {"label": _("No Of Ship"), "fieldname": "no_of_ship", "fieldtype": "Int", "width": 100},
        {"label": _("Discount"), "fieldname": "discount", "fieldtype": "Currency", "width": 120},
        {"label": _("Fuel Surcharges"), "fieldname": "fuel_surcharge", "fieldtype": "Currency", "width": 120},
        {"label": _("Shipping Bill Charges"), "fieldname": "shipping_bill_charges", "fieldtype": "Currency", "width": 150},
        {"label": _("Total Other Charges"), "fieldname": "other_charges", "fieldtype": "Currency", "width": 150},
        {"label": _("Total Peak Charges"), "fieldname": "peak_charges", "fieldtype": "Currency", "width": 130},
        {"label": _("Insurance"), "fieldname": "insurance", "fieldtype": "Currency", "width": 120},
        {"label": _("Total Amount"), "fieldname": "total_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Sales Tax"), "fieldname": "sales_tax", "fieldtype": "Currency", "width": 120},
        {"label": _("Net Billing"), "fieldname": "net_billing", "fieldtype": "Currency", "width": 130},
    ]


def get_data(filters):
    data = []

    # Map date_type to actual field
    date_field_map = {
        "Posting Date": "posting_date",
        "Shipped Date": "end_date",
        "Import Date": "import_date",
        "Arrival Date": "arrival_date",
    }

    conditions = []
    values = {}

    if filters.get("customer"):
        conditions.append("sip.customer = %(customer)s")
        values["customer"] = filters.get("customer")

    if filters.get("icris_number"):
        conditions.append("sip.icris_number = %(icris_number)s")
        values["icris_number"] = filters.get("icris_number")

    if filters.get("import_export"):
        conditions.append("sip.import__export = %(import_export)s")
        values["import_export"] = filters.get("import_export")

    if filters.get("date_type") and filters.get("start_date") and filters.get("end_date"):
        field = date_field_map.get(filters["date_type"])
        if field:
            conditions.append(f"sip.{field} BETWEEN %(start_date)s AND %(end_date)s")
            values["start_date"] = filters["start_date"]
            values["end_date"] = filters["end_date"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Step 1: Fetch filtered Sales Invoice PDF docs
    pdf_docs = frappe.db.sql(
        f"""
        SELECT
            sip.name,
            sip.end_date,
            sip.icris_number,
            sip.import__export
        FROM `tabSales Invoice PDF` sip
        WHERE {where_clause}
        """,
        values,
        as_dict=True,
    )

    if not pdf_docs:
        return data

    pdf_names = [pdf.name for pdf in pdf_docs]

    # Step 2: Fetch all children in one query
    children = frappe.db.sql(
		"""
		SELECT
			cws.parent,
			cws.name1,
			cws.customer AS shipper_name,
			cws.sales_invoices
		FROM `tabCustomer With Sales Invoice` cws
		WHERE cws.parent IN %(pdf_names)s
		""",
		{"pdf_names": pdf_names},
		as_dict=True,
	)


    # Step 3: Fetch Customer tax IDs once
    customers = list(set(child["shipper_name"] for child in children))
    customer_tax = frappe.db.get_all(
        "Customer",
        filters={"name": ["in", customers]},
        fields=["name", "tax_id"],
        as_dict=True,
    )
    tax_map = {c.name: c.tax_id for c in customer_tax}

    # Step 4: Fetch first Sales Invoice discount/GST only
    all_si_names = []
    for child in children:
        if child["sales_invoices"]:
            first_si = child["sales_invoices"].split(",")[0].strip()
            all_si_names.append(first_si)
    si_map = {}
    if all_si_names:
        sis = frappe.db.get_all(
            "Sales Invoice",
            filters={"name": ["in", all_si_names]},
            fields=["name", "additional_discount_amount", "sales_taxes_and_charges_template"],
            as_dict=True,
        )
        si_map = {si.name: si for si in sis}

    # Step 5: Build final data
    pdf_map = {pdf["name"]: pdf for pdf in pdf_docs}
    for child in children:
        pdf = pdf_map[child["parent"]]
        ntn_no = tax_map.get(child["shipper_name"])
        discount = 0
        gst_station = ""
        if child["sales_invoices"]:
            first_si = child["sales_invoices"].split(",")[0].strip()
            si = si_map.get(first_si)
            if si:
                discount = si.get("additional_discount_amount") or 0
                gst_station = si.get("sales_taxes_and_charges_template") or ""

        data.append({
            "invoice_no": child["name1"],
            "date": pdf["end_date"],
            "account_no": pdf["icris_number"],
            "shipper_name": child["shipper_name"],
            "ntn_no": ntn_no,
            "gst_station": gst_station,
            "weight": 0,
            "no_of_ship": 0,
            "discount": discount,
            "fuel_surcharge": 0,
            "shipping_bill_charges": 0,
            "other_charges": 0,
            "peak_charges": 0,
            "insurance": 0,
            "total_amount": 0,
            "sales_tax": 0,
            "net_billing": 0
        })

    return data
