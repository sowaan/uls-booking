# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_columns(filters):
    base_columns = [
        {
            "label": _("Invoice ID"),
            "fieldname": "invoice_id",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 150
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Document Status"),
            "fieldname": "stat",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Booking Date"),
            "fieldname": "booking_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Date Shipped"),
            "fieldname": "date_shipped",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Import Date"),
            "fieldname": "import_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Territory"),
            "fieldname": "territory",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Shipment Number"),
            "fieldname": "shipment_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Tracking Number"),
            "fieldname": "tracking_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Account No"),
            "fieldname": "account_no",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 120
        },
        {
            "label": _("Customer Group"),
            "fieldname": "customer_grp",
            "fieldtype": "Link",
            "options": "Customer Group",
            "width": 120
        },
        {
            "label": _("Billing type"),
            "fieldname": "billing_type",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Shipper Number"),
            "fieldname": "shipper_number",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Shipper Name"),
            "fieldname": "shipper_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Consignee Number"),
            "fieldname": "consignee_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Consignee Name"),
            "fieldname": "consignee_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Tax ID"),
            "fieldname": "tax_id",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Service Type"),
            "fieldname": "service_type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Shipment Type"),
            "fieldname": "shipment_type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Package Type"),
            "fieldname": "package_type",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Zone"),
            "fieldname": "zone",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Consignee Country"),
            "fieldname": "consignee_country",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Import / Export"),
            "fieldname": "import_export",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Shipment Weight"),
            "fieldname": "shipment_weight",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Billing Term"),
            "fieldname": "billing_term",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Data",
            "width": 80
        },
        {
            "label": _("Exchange Rate"),
            "fieldname": "exchange_rate",
            "fieldtype": "Data",
            "width": 80
        }
        # ,
        # {
        #     "label": _("Freight Charges"),
        #     "fieldname": "freight_charges",
        #     "fieldtype": "Float",
        #     "width": 100
        # },
        # {
        #     "label": _("SBC"),
        #     "fieldname": "sbc",
        #     "fieldtype": "Float",
        #     "width": 80
        # },
        # {
        #     "label": _("FSC"),
        #     "fieldname": "fsc",
        #     "fieldtype": "Float",
        #     "width": 80
        # },
        # {
        #     "label": _("Peak"),
        #     "fieldname": "peak",
        #     "fieldtype": "Float",
        #     "width": 80
        # }
    ]

    item_columns = []
    conditions, message = get_conditions(filters)
    if message:
        frappe.msgprint(_(message))
    
    items = frappe.db.sql("""
        SELECT DISTINCT sii.item_code, sii.item_name
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        WHERE si.custom_freight_invoices = 1 {conditions}
    """.format(conditions=conditions), filters, as_dict=1)
    
    for item in items:
        if item.item_name == "Freight Charges":
            item_columns.append({
            "label": _(item.item_name),
            "fieldname": custom_scrub(item.item_code),
            "fieldtype": "Float",
            "width": 135
            })
        else:
            item_columns.append({
                "label": _(item.item_code),
                "fieldname": custom_scrub(item.item_code),
                "fieldtype": "Float",
                "width": 100
            })
    
    return base_columns + item_columns + remaining_columns()


def get_data(filters):


    conditions, message = get_conditions(filters)
    data = frappe.db.sql("""
        
        SELECT 
            si.name as invoice_id,
            si.posting_date as posting_date,
            CASE si.docstatus WHEN 0 THEN 'Draft' WHEN 1 THEN 'Submitted' ELSE 'Cancelled' END as stat,
            CASE 
                WHEN UPPER(si.custom_consignee_country) IN ('PAKISTAN', 'PAK', 'PK') THEN 'Import'
                ELSE 'Export'
            END AS import_export,
            si.custom_booking_date as booking_date,
            si.custom_date_shipped as date_shipped,
            si.custom_tracking_number as tracking_number,
            si.custom_shipper_name as shipper_name,
            si.custom_import_date as import_date,
            si.territory as territory,
            si.custom_shipment_number as shipment_number,
            si.custom_account_no as account_no,
            cust.customer_group as customer_grp,
            si.customer,
            si.custom_billing_type as billing_type,
            si.custom_shipper_number as shipper_number,
            si.custom_consignee_name as consignee_name,
            si.custom_consignee_number as consignee_number,
            cust.tax_id as tax_id,
            si.custom_service_type as service_type,
            si.custom_shipment_type as shipment_type,
            si.custom_package_type as package_type,
            si.custom_zone as zone,
            si.custom_consignee_country as consignee_country,
            si.custom_shipment_weight as shipment_weight,
            si.custom_billing_term as billing_term,
            si.currency,
            si.conversion_rate as exchange_rate,
            si.custom_freight_charges as freight_charges,
            si.custom_total_surcharges_incl_fuel as total_surcharges_incl_fuel,
            si.custom_total_surcharges_excl_fuel as total_surcharges_excl_fuel,
            si.custom_selling_percentage as selling_percentage,
            si.custom_amount_after_discount as amount_after_discount,
            si.net_total,
            si.base_net_total,
            si.total_taxes_and_charges,
            si.grand_total,
            si.base_grand_total
        FROM 
            `tabSales Invoice` si
        JOIN
            `tabCustomer` cust ON si.customer = cust.name
        WHERE 
            si.custom_freight_invoices = 1 {conditions}
        ORDER BY 
            si.posting_date
    """.format(conditions=conditions), filters, as_dict=1)

    for row in data:
        invoice_id = row.get("invoice_id")
        items = frappe.db.sql("""
            SELECT 
                item_code,
                amount
            FROM
                `tabSales Invoice Item`
            WHERE 
                parent = %s
        """, (invoice_id,), as_dict=1)
        for item in items:
            row[custom_scrub(item.item_code)] = item.amount
        
        tax_data = frappe.db.sql("""
            SELECT
                base_tax_amount_after_discount_amount as tax_amount
            FROM
                `tabSales Taxes and Charges`
            WHERE
                parent = %s
        """, (invoice_id,), as_dict=1)
        
        if tax_data and tax_data[0].get("tax_amount"):
            row["tax_amount_after_disc_amount"] = tax_data[0]["tax_amount"]
            
    
    return data



def get_conditions(filters):
    msg = None
    conditions = ""
    doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
    date_type = filters.get("date_type")

    date_field_map = {
        "Posting Date": "si.posting_date",
        "Shipped Date": "si.custom_date_shipped",
        "Import Date": "si.custom_import_date"
    }

    date_field = date_field_map.get(date_type)

    if date_field:
        conditions += f" AND {date_field} IS NOT NULL"
        if filters.get("from_date"):
            conditions += f" AND {date_field} >= %(from_date)s"
        if filters.get("to_date"):
            conditions += f" AND {date_field} <= %(to_date)s"

    if filters.get("name"):
        conditions += " AND si.name = %(name)s"
    if filters.get("customer"):
        conditions += " AND si.customer = %(customer)s"

    if filters.get("shipment_number"):
        conditions += " AND si.custom_shipment_number = %(shipment_number)s"
    if filters.get("tracking_number"):
        conditions += " AND si.custom_tracking_number = %(tracking_number)s"
    if filters.get("billing_type"):
        conditions += " AND si.custom_billing_type = %(billing_type)s"
    if filters.get("shipper_number"):
        conditions += " AND si.custom_shipper_number = %(shipper_number)s"
    if filters.get("consignee_number"):
        conditions += " AND si.custom_consignee_number = %(consignee_number)s"

    if filters.get("customer_group"):
        cus_grp = filters["customer_group"]
        customers_from_grps = frappe.db.get_all(
            "Customer",
            filters={"customer_group": cus_grp},
            pluck="name"
        )
        if customers_from_grps:
            conditions += " AND si.customer IN %(customer_group_customers)s"
            filters["customer_group_customers"] = tuple(customers_from_grps)
        else:
            conditions += " AND 1=0"
            msg = (f"No customers found for the selected customer group: {cus_grp}")

    check_docstatus = filters.get("docstatus")
    if check_docstatus:
        conditions += f" AND si.docstatus = {doc_status[check_docstatus]}"
        
    if filters.get("import_export"):
        if filters["import_export"] == "Import":
            conditions += " AND UPPER(si.custom_consignee_country) IN ('PAKISTAN', 'PAK', 'PK')"
        elif filters["import_export"] == "Export":
            conditions += " AND UPPER(si.custom_consignee_country) NOT IN ('PAKISTAN', 'PAK', 'PK')"

    if filters.get("billing_term"):
        filters["billing_term"] = filters["billing_term"].upper()
        conditions += " AND UPPER(si.custom_billing_term) = %(billing_term)s"

    return conditions, msg


def remaining_columns():
    return [
        {
            "label": _("Total Surcharges INCL Fuel"),
            "fieldname": "total_surcharges_incl_fuel",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": _("Total Surcharges EXCL Fuel"),
            "fieldname": "total_surcharges_excl_fuel",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": _("Selling Percentage"),
            "fieldname": "selling_percentage",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Amount After Discount"),
            "fieldname": "amount_after_discount",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": _("Net Total"),
            "fieldname": "net_total",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Net Total (Company Currency)"),
            "fieldname": "base_net_total",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": _("Total Taxes and Charges"),
            "fieldname": "total_taxes_and_charges",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": _("Tax Amount After Discount Amount (Company Currency)"),
            "fieldname": "tax_amount_after_disc_amount",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": _("Grand Total"),
            "fieldname": "grand_total",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Grand Total (Company Currency)"),
            "fieldname": "base_grand_total",
            "fieldtype": "Float",
            "width": 150
        }
        ]


def custom_scrub(txt=None):
    if not txt:
        return None
    return txt.lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('&','_')