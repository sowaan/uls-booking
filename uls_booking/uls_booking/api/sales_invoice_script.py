from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import getdate
import json
import re
from datetime import datetime
from frappe import _
import logging



@frappe.whitelist()
def get_shipment_numbers_and_sales_invoices(start_date, end_date, station=None, billing_type=None, icris_number=None, customer=None, import__export=None):


    # Prepare the values dictionary to pass into the SQL query
    values = {
        "start_date": start_date,
        "end_date": end_date,
        "station": station,
        "billing_type": billing_type,
        "icris_number": icris_number,
        "customer": customer,
        "import__export": import__export
    }

    # Begin the SQL query
    query = """
        SELECT 
            shipment_number
        FROM 
            `tabShipment Number` as sn
        WHERE
            sn.date_shipped BETWEEN %(start_date)s AND %(end_date)s
    """

    # Initialize a list for conditions
    conditions = []

    # Add conditions dynamically based on provided values
    if station:
        conditions.append("sn.station = %(station)s")
    if billing_type:
        conditions.append("sn.billing_type = %(billing_type)s")
    if icris_number:
        conditions.append("sn.icris_number = %(icris_number)s")
    if import__export:
        conditions.append("sn.import__export = %(import__export)s")
    if customer:
        conditions.append("sn.customer = %(customer)s")

    # If there are additional conditions, join them to the query
    if conditions:
        query += " AND " + " AND ".join(conditions)

    # Log the query for debugging purposes (optional)
    print("Executing query:", query)
    print("With values:", values)

    # Execute the query with the provided values
    try:
        results = frappe.db.sql(query, values)
    except Exception as e:
        print("Error executing query:", e)
        return []

    # Extract shipment numbers from results
    shipment_numbers = [row[0] for row in results]
    print(shipment_numbers)
    # Return the shipment numbers
    return shipment_numbers



@frappe.whitelist()
def generate_single_invoice(shipment_number, sales_invoice_definition, end_date):
    print("Main Function")
    try:
        logs = []
        sales_invoice = None  # Ensure it's defined at the start

        # Check if Sales Invoice Definition exists
        try:
            definition = frappe.get_doc("Sales Invoice Definition", sales_invoice_definition)
        except frappe.DoesNotExistError:
            logs.append("Sales Invoice Definition does not exist")
            return {"message": logs}

        # Check if invoice already exists
        existing_invoice = frappe.db.sql(
            """SELECT name FROM `tabSales Invoice`
               WHERE custom_shipment_number = %s
               FOR UPDATE""",
            shipment_number,
            as_dict=True
        )
        if existing_invoice:
            frappe.throw("Present In Sales Invoice")

        # Get settings
        setting = frappe.get_doc("Manifest Setting Definition")

        # ✅ Assign the sales_invoice variable early to avoid reference issues
        sales_invoice = frappe.new_doc("Sales Invoice")

        # Get default customer from company
        company = definition.default_company
        customer = frappe.get_doc("Company", company, fields=["custom_default_customer"])
        sales_invoice.customer = customer.custom_default_customer
        sales_invoice.custom_sales_invoice_definition = sales_invoice_definition
        # Populate sales invoice fields
        for child_record in definition.sales_invoice_definition:
            doctype_name = child_record.ref_doctype
            field_name = child_record.field_name
            sales_field_name = child_record.sales_invoice_field_name

            docs = frappe.get_list(doctype_name, filters={'shipment_number': shipment_number}, fields=[field_name])
            if docs:
                sales_invoice.set(sales_field_name, docs[0][field_name])

        # Set posting date
        sales_invoice.posting_date = getdate(end_date)
        sales_invoice.set_posting_time = 1
        weight_frm_R200000 = frappe.get_value(
            "R202000",
            filters={'shipment_number': shipment_number},
            fieldname="custom_expanded_shipment_weight"
        )

        weight_frm_R201000 = frappe.get_value(
            "R201000",
            filters={'shipment_number': shipment_number},
            fieldname="custom_minimum_bill_weight"
        )

        
        weight_frm_R200000 = float(weight_frm_R200000) if weight_frm_R200000 else 0.0
        weight_frm_R201000 = float(weight_frm_R201000) if weight_frm_R201000 else 0.0

        
        selected_weight = max(weight_frm_R200000, weight_frm_R201000)
        sales_invoice.custom_shipment_weight = selected_weight
        # Set currency
        sales_invoice.currency = frappe.get_value("Customer", sales_invoice.customer, "default_currency")

        # Append an item row
        rows = {'item_code': "ICG", 'qty': '1', 'rate': 0}
        sales_invoice.append('items', rows)

        # Insert and save
        # print(sales_invoice.customer)
        sales_invoice.insert()
        # sales_invoice.save()
        # print("saved")
        # frappe.db.commit()

    except json.JSONDecodeError:
        message = "Invalid JSON data"
        print(message)
        logging.error(message)

    except Exception as e:
        # ✅ Check if sales_invoice is assigned before using it
        if sales_invoice and sales_invoice.name:
            print(f"Error while processing Sales Invoice {sales_invoice.name}: {str(e)}")
        else:
            print(f"An error occurred before Sales Invoice was created: {str(e)}")
        
        logging.error(f"An error occurred: {str(e)}")