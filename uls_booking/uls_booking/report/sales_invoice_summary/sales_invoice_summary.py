import frappe
from frappe.utils import getdate

def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are mandatory")

    if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
        frappe.throw("<b>From Date</b> cannot be later than <b>To Date</b>.")

    return get_columns(), get_data(filters)


# ---------------------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------------------
def get_columns():
    return [
        {"label": "Invoice Number", "fieldname": "invoice_number"},
        {"label": "Date", "fieldname": "pdf_end_date", "fieldtype": "Date"},
        {"label": "Account No", "fieldname": "customer_account_no"},        
        {"label": "Shipper Name", "fieldname": "custom_shipper_name"},
        {"label": "NTN No", "fieldname": "ntn_no"},        
        {"label": "Station", "fieldname": "station"},
        {"label": "Import / Export", "fieldname": "import_export"},
        {"label": "Total Weight", "fieldname": "weight", "fieldtype": "Float"},
        {"label": "No of Shipments", "fieldname": "no_shipment", "fieldtype": "Int"},
        {"label": "Freight (Tariff Amount)", "fieldname": "freight", "fieldtype": "Currency"},
        {"label": "Discount", "fieldname": "discount", "fieldtype": "Currency"},
        {"label": "Net Amount", "fieldname": "net_amount", "fieldtype": "Currency"},
        {"label": "Fuel Surcharges", "fieldname": "fuel_surcharges", "fieldtype": "Currency"},
        {"label": "Shipping Bill Charges", "fieldname": "shipping_bill_charges", "fieldtype": "Currency"},
        {"label": "Total Other Charges", "fieldname": "total_other_charges", "fieldtype": "Currency"},
        {"label": "Total Peak Charges", "fieldname": "total_peak_charges", "fieldtype": "Currency"}, 
        {"label": "Insurance", "fieldname": "insurance", "fieldtype": "Currency"}, 
        {"label": "Total Amount", "fieldname": "total_amount", "fieldtype": "Currency"}, 
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

    sip.station AS station,
    sip.import__export AS import_export,

    cust.custom_import_account_no AS customer_account_no,
    cust.tax_id AS ntn_no,
    cust.customer_name AS custom_shipper_name,

    COALESCE(inv.no_shipment, 0) AS no_shipment,
    COALESCE(inv.weight, 0) AS weight,
    COALESCE(inv.discount, 0) AS discount,

    /* ================= NET AMOUNT ================= */
    (COALESCE(itm.freight, 0) - COALESCE(inv.discount, 0)) AS net_amount,

    /* ================= TOTAL AMOUNT ================= */
    (
        (COALESCE(itm.freight, 0) - COALESCE(inv.discount, 0))
      + COALESCE(itm.fuel_surcharges, 0)
      + COALESCE(itm.shipping_bill_charges, 0)
      + COALESCE(itm.total_other_charges, 0)
      + COALESCE(itm.total_peak_charges, 0)
      + COALESCE(itm.insurance, 0)
    ) AS total_amount,

    /* ================= NET BILLING ================= */
    (
        (
            (COALESCE(itm.freight, 0) - COALESCE(inv.discount, 0))
          + COALESCE(itm.fuel_surcharges, 0)
          + COALESCE(itm.shipping_bill_charges, 0)
          + COALESCE(itm.total_other_charges, 0)
          + COALESCE(itm.total_peak_charges, 0)
          + COALESCE(itm.insurance, 0)
        )
      + COALESCE(inv.sales_tax, 0)
    ) AS net_billing,

    COALESCE(inv.sales_tax, 0) AS sales_tax,

    /* ================= BREAKDOWN ================= */
    COALESCE(itm.freight, 0) AS freight,
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

    /* ================= INVOICE LEVEL (BOUND TO PDF DATE) ================= */
    LEFT JOIN (
        SELECT
            si.custom_sales_invoice_pdf_child_ref AS pdf_child,
            COUNT(si.name) AS no_shipment,
            SUM(si.custom_shipment_weight) AS weight,
            SUM(si.base_discount_amount) AS discount,
            SUM(si.base_net_total) AS total_amount,
            SUM(si.base_total_taxes_and_charges) AS sales_tax,
            SUM(si.base_grand_total) AS net_billing
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice PDF table` cws2
            ON cws2.name = si.custom_sales_invoice_pdf_child_ref
        INNER JOIN `tabSales Invoice PDF` sip2
            ON sip2.name = cws2.parent
            AND sip2.docstatus = 1
            AND sip2.end_date BETWEEN %(from_date)s AND %(to_date)s
        WHERE si.docstatus = 1
        GROUP BY si.custom_sales_invoice_pdf_child_ref
    ) inv
        ON inv.pdf_child = cws.name

    /* ================= ITEM LEVEL (BOUND TO PDF DATE) ================= */
    LEFT JOIN (
        SELECT
            si.custom_sales_invoice_pdf_child_ref AS pdf_child,
            
            SUM(CASE WHEN it.custom_report_item = 'Freight'
            THEN sii.base_rate ELSE 0 END) AS freight,

            SUM(CASE WHEN it.custom_report_item = 'INSURANCE'
                THEN sii.base_rate ELSE 0 END) AS insurance,

            SUM(CASE WHEN it.custom_report_item = 'Fuel Surcharges'
                THEN sii.base_rate ELSE 0 END) AS fuel_surcharges,

            SUM(CASE WHEN it.custom_report_item = 'SBC'
                THEN sii.base_rate ELSE 0 END) AS shipping_bill_charges,

            SUM(CASE WHEN it.custom_report_item = 'OTHER CHARGES'
                THEN sii.base_rate ELSE 0 END) AS total_other_charges,

            SUM(CASE WHEN it.custom_report_item = 'PEAK SURCHARGE'
                THEN sii.base_rate ELSE 0 END) AS total_peak_charges

        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        JOIN `tabItem` it ON it.name = sii.item_code
        INNER JOIN `tabSales Invoice PDF table` cws2
            ON cws2.name = si.custom_sales_invoice_pdf_child_ref
        INNER JOIN `tabSales Invoice PDF` sip2
            ON sip2.name = cws2.parent
            AND sip2.docstatus = 1
            AND sip2.end_date BETWEEN %(from_date)s AND %(to_date)s
        WHERE si.docstatus = 1
        GROUP BY si.custom_sales_invoice_pdf_child_ref
    ) itm
        ON itm.pdf_child = cws.name

    ORDER BY sip.end_date DESC, cws.name1
    """

    return frappe.db.sql(query, values=values, as_dict=True)
