import frappe


def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are mandatory")

    return get_columns(), get_data(filters)


# ---------------------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------------------
def get_columns():
    return [
        {"label": "Invoice Number", "fieldname": "invoice_number"},
        {"label": "Date", "fieldname": "pdf_end_date", "fieldtype": "Date"},
        {"label": "Customer Account No", "fieldname": "customer_account_no"},
        {"label": "NTN No", "fieldname": "ntn_no"},
        {"label": "Shipper Name", "fieldname": "custom_shipper_name"},
        {"label": "GST Territory / Station", "fieldname": "taxes_and_charges"},
        {"label": "No of Shipments", "fieldname": "no_shipment", "fieldtype": "Int"},
        {"label": "Total Weight", "fieldname": "weight", "fieldtype": "Float"},
        {"label": "Discount", "fieldname": "discount", "fieldtype": "Currency"},
        {"label": "Insurance", "fieldname": "insurance", "fieldtype": "Currency"},
        {"label": "Fuel Surcharges", "fieldname": "fuel_surcharges", "fieldtype": "Currency"},
        {"label": "Shipping Bill Charges", "fieldname": "shipping_bill_charges", "fieldtype": "Currency"},
        {"label": "Other Charges", "fieldname": "total_other_charges", "fieldtype": "Currency"},
        {"label": "Peak Charges", "fieldname": "total_peak_charges", "fieldtype": "Currency"},
        {"label": "Total Amount (Net)", "fieldname": "total_amount", "fieldtype": "Currency"},
        {"label": "Sales Tax", "fieldname": "sales_tax", "fieldtype": "Currency"},
        {"label": "Net Billing", "fieldname": "net_billing", "fieldtype": "Currency"},
    ]


# ---------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------
def get_data(filters):

    values = {
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
        "customer": filters.get("customer"),
    }

    query = """
    SELECT
    cws.name1 AS invoice_number,
    sip.end_date AS pdf_end_date,

    cust.custom_import_account_no AS customer_account_no,
    cust.tax_id AS ntn_no,
    cust.customer_name AS custom_shipper_name,

    COALESCE(inv.no_shipment, 0) AS no_shipment,
    COALESCE(inv.weight, 0) AS weight,
    COALESCE(inv.discount, 0) AS discount,
    COALESCE(inv.total_amount, 0) AS total_amount,
    COALESCE(inv.sales_tax, 0) AS sales_tax,
    COALESCE(inv.net_billing, 0) AS net_billing,

    COALESCE(itm.insurance, 0) AS insurance,
    COALESCE(itm.fuel_surcharges, 0) AS fuel_surcharges,
    COALESCE(itm.shipping_bill_charges, 0) AS shipping_bill_charges,
    COALESCE(itm.total_other_charges, 0) AS total_other_charges,
    COALESCE(itm.total_peak_charges, 0) AS total_peak_charges

FROM `tabSales Invoice PDF table` cws

INNER JOIN `tabSales Invoice PDF` sip
    ON sip.name = cws.parent
    AND sip.docstatus = 1
    AND cws.name1 IS NOT NULL
    AND cws.name1 <> ''
    AND sip.end_date BETWEEN %(from_date)s AND %(to_date)s

LEFT JOIN `tabCustomer` cust
    ON cust.name = cws.customer

/* ================= INVOICE LEVEL (LEFT JOIN!) ================= */
LEFT JOIN (
    SELECT
        si.custom_sales_invoice_pdf_child_ref AS pdf_child,
        COUNT(si.name) AS no_shipment,
        SUM(si.custom_shipment_weight) AS weight,
        SUM(si.base_discount_amount) AS discount,
        SUM(si.base_net_total) AS total_amount,
        SUM(si.total_taxes_and_charges) AS sales_tax,
        SUM(si.grand_total) AS net_billing
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
    GROUP BY si.custom_sales_invoice_pdf_child_ref
) inv
    ON inv.pdf_child = cws.name

/* ================= ITEM LEVEL (LEFT JOIN!) ================= */
LEFT JOIN (
    SELECT
        si.custom_sales_invoice_pdf_child_ref AS pdf_child,

        SUM(CASE WHEN it.report_item = 'INSURANCE' THEN sii.base_net_amount ELSE 0 END) AS insurance,
        SUM(CASE WHEN it.report_item = 'Fuel Surcharges' THEN sii.base_net_amount ELSE 0 END) AS fuel_surcharges,
        SUM(CASE WHEN it.report_item = 'SBC' THEN sii.base_net_amount ELSE 0 END) AS shipping_bill_charges,
        SUM(CASE WHEN it.report_item = 'OTHER CHARGES' THEN sii.base_net_amount ELSE 0 END) AS total_other_charges,
        SUM(CASE WHEN it.report_item = 'PEAK SURCHARGE' THEN sii.base_net_amount ELSE 0 END) AS total_peak_charges

    FROM `tabSales Invoice` si
    JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
    JOIN `tabItem` it ON it.name = sii.item_code
    WHERE si.docstatus = 1
    GROUP BY si.custom_sales_invoice_pdf_child_ref
) itm
    ON itm.pdf_child = cws.name

ORDER BY sip.end_date DESC, cws.name1;


    """

    return frappe.db.sql(query, values=values, as_dict=True)
