import frappe


def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are mandatory")

    return get_columns(), get_data(filters)


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
        {"label": "Total Amount", "fieldname": "total_amount", "fieldtype": "Currency"},
        {"label": "Sales Tax", "fieldname": "sales_tax", "fieldtype": "Currency"},
        {"label": "Net Billing", "fieldname": "net_billing", "fieldtype": "Currency"},
    ]


def get_data(filters):

    values = {
        "customer": filters.get("customer"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
    }

    query = """
    SELECT
        agg.name1 AS invoice_number,
        sip.end_date AS pdf_end_date,

        cust.custom_import_account_no AS customer_account_no,
        cust.tax_id AS ntn_no,
        cust.customer_name AS custom_shipper_name,

        agg.taxes_and_charges,
        agg.no_shipment,
        agg.weight,
        agg.discount,
        agg.insurance,
        agg.fuel_surcharges,
        agg.shipping_bill_charges,
        agg.total_other_charges,
        agg.total_peak_charges,
        agg.total_amount,
        agg.sales_tax,
        agg.net_billing

    FROM
        `tabSales Invoice PDF` sip

    INNER JOIN
        `tabSales Invoice PDF table` cws
            ON cws.parent = sip.name

    /* 🔥 SINGLE SOURCE OF TRUTH — ONE ROW PER name1 🔥 */
    INNER JOIN (
        SELECT
            cws_inner.name1,

            MAX(si.taxes_and_charges) AS taxes_and_charges,
            MAX(cws_inner.total_invoices) AS no_shipment,

            SUM(si.custom_shipment_weight) AS weight,
            SUM(si.base_discount_amount) AS discount,
            SUM(si.base_net_total) AS total_amount,
            SUM(si.total_taxes_and_charges) AS sales_tax,
            SUM(si.grand_total) AS net_billing,

            SUM(CASE WHEN sii.item_name LIKE '%%Insurance%%' THEN sii.base_net_amount ELSE 0 END) AS insurance,
            SUM(CASE WHEN sii.item_name LIKE '%%Fuel%%' THEN sii.base_net_amount ELSE 0 END) AS fuel_surcharges,
            SUM(CASE WHEN sii.item_name LIKE '%%Shipping%%' THEN sii.base_net_amount ELSE 0 END) AS shipping_bill_charges,
            SUM(CASE WHEN sii.item_name LIKE '%%Other%%' THEN sii.base_net_amount ELSE 0 END) AS total_other_charges,
            SUM(CASE WHEN sii.item_name LIKE '%%Peak%%' THEN sii.base_net_amount ELSE 0 END) AS total_peak_charges

        FROM
            `tabSales Invoice PDF table` cws_inner

        INNER JOIN
            `tabSales Invoice` si              
                ON FIND_IN_SET(si.name, REPLACE(cws_inner.sales_invoices, ' ', ''))

                AND si.docstatus = 1

        LEFT JOIN
            `tabSales Invoice Item` sii
                ON sii.parent = si.name

        GROUP BY
            cws_inner.name1
    ) agg
        ON agg.name1 = cws.name1

    LEFT JOIN
        `tabCustomer` cust
            ON cust.name = cws.customer

    WHERE
        sip.docstatus = 1
        AND (%(customer)s IS NULL OR cws.customer = %(customer)s)
        AND sip.end_date BETWEEN %(from_date)s AND %(to_date)s

    ORDER BY
        sip.end_date DESC
    """

    return frappe.db.sql(query, values=values, as_dict=True)
