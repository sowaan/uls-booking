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
def get_shipment_numbers_and_sales_invoices(start_date, end_date, station=None, billing_type=None, icris_number=None, customer=None, import__export=None,date_type=None,manifest_file_type=None):


    # Prepare the values dictionary to pass into the SQL query
    values = {
        "start_date": start_date,
        "end_date": end_date,
        "station": station,
        "billing_type": billing_type,
        "icris_number": icris_number,
        "customer": customer,
        "import__export": import__export,
        "manifest_file_type":manifest_file_type,
        "date_type":date_type
    }

    # Begin the SQL query


    if date_type == 'Shipped Date' :
        query = """
            SELECT 
                shipment_number
            FROM 
                `tabShipment Number` as sn
            WHERE
                sn.date_shipped BETWEEN %(start_date)s AND %(end_date)s
        """

    else :
        query = """
            SELECT 
                shipment_number
            FROM 
                `tabShipment Number` as sn
            WHERE
                sn.import_date BETWEEN %(start_date)s AND %(end_date)s
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
    if manifest_file_type :
        conditions.append("sn.manifest_file_type = %(manifest_file_type)s")

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
    shipment_numbers = [row[0] for row in results]
    return shipment_numbers



@frappe.whitelist()
def generate_single_invoice(shipment_number, sales_invoice_definition, end_date):
    print("Main Function")
    try:
        logs = []
        sales_invoice = None

        # Check if Sales Invoice Definition exists
        try:
            definition = frappe.get_doc("Sales Invoice Definition", sales_invoice_definition)
        except frappe.DoesNotExistError:
            logs.append("Sales Invoice Definition does not exist")
            return {"message": logs}
        setting = frappe.get_doc("Manifest Setting Definition")
        sales_invoice = frappe.new_doc("Sales Invoice")
        if sales_invoice.custom_shipper_country == definition.origin_country.upper():
            imp_exp = "Export"
            if sales_invoice.custom_shipper_number:
                icris_number = sales_invoice.custom_shipper_number
            else:
                icris_number = definition.unassigned_icris_number

        elif sales_invoice.custom_shipper_country != definition.origin_country.upper():
            imp_exp = "Import"
            if sales_invoice.custom_consignee_number:
                icris_number = sales_invoice.custom_consignee_number
            else:
                icris_number = definition.unassigned_icris_number
            
        if sales_invoice.custom_package_type:
            shipment_type = sales_invoice.custom_package_type
        else:
            shipment_type = sales_invoice.custom_shipment_type
            
        try:
            icris_account = frappe.get_doc("ICRIS Account", icris_number)
        
        except frappe.DoesNotExistError:
            logs.append(f"No icris Account Found {icris_number}")
            print("No icris Account Found")
            if definition.unassigned_icris_number:
                icris_account = frappe.get_doc("ICRIS Account", definition.unassigned_icris_number)




        # Get default customer from company
        company = definition.default_company
        customer = frappe.get_doc("Company", company, fields=["custom_default_customer"])
        # sales_invoice.customer = customer.custom_default_customer
        sales_invoice.set("customer", customer.custom_default_customer)
        sales_invoice.custom_sales_invoice_definition = sales_invoice_definition
        # Populate sales invoice fields
        for child_record in definition.sales_invoice_definition:
            doctype_name = child_record.ref_doctype
            field_name = child_record.field_name
            sales_field_name = child_record.sales_invoice_field_name

            docs = frappe.get_list(doctype_name, filters={'shipment_number': shipment_number}, fields=[field_name])
            if docs:
                sales_invoice.set(sales_field_name, docs[0][field_name])

        export_billing_term = []
        import_billing_term = []
        for term in definition.export_and_import_conditions:
            if term.export_check == 1:
                export_billing_term.append(term.billing_term)

            elif term.export_check == 0:
                import_billing_term.append(term.billing_term)

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
        sales_invoice.currency = frappe.get_value("Customer", sales_invoice.customer, "default_currency")




        if sales_invoice.custom_billing_term in export_billing_term and sales_invoice.custom_shipper_country == definition.origin_country.upper():
            check1 = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
            if not check1:
                logs.append(f"No ICRIS Account Found {icris_number}")
                print("No ICRIS Account Found")
                icris_number = definition.unassigned_icris_number
            if icris_number:
                icris_doc = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
                icris = frappe.get_doc("ICRIS Account",icris_doc[0].name)
                if icris.shipper_name:
                    sales_invoice.customer = icris.shipper_name
                else:
                    logs.append(f"No Customer Found icris number: {icris_number} , shipment number: {shipment_number}")
                    print("No Customer Found")




        elif sales_invoice.custom_billing_term in import_billing_term and sales_invoice.custom_shipper_country != definition.origin_country.upper():
            check = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
            if not check:
                logs.append(f"No ICRIS Account Found {icris_number}")
                print("No ICRIS Account Found Thats Why using Default Icris")
                icris_number = definition.unassigned_icris_number
            if icris_number:
                icris_doc = frappe.get_list("ICRIS Account",
                                    filters = {"name":icris_number})
                icris1 = frappe.get_doc("ICRIS Account",icris_doc[0].name)
                
                if icris1.shipper_name:
                    sales_invoice.customer = icris1.shipper_name
                else:
                    logs.append(f"No Customer Found icris number: {icris_number} , shipment number: {shipment_number}") 
                    print("No Customer Found")



        log_doc = frappe.new_doc("Sales Invoice Logs")
        if sales_invoice.customer != customer.custom_default_customer:
            sales_invoice.custom_freight_invoices = 1
            existing_invoice = frappe.db.sql(
                            """SELECT name FROM `tabSales Invoice`
                            WHERE custom_shipment_number = %s
                            AND custom_freight_invoices = 1
                            FOR UPDATE""",
                            shipment_number,
                            as_dict=True
                        )
            if existing_invoice:
                logs.append(f"Already Present In Sales Invocie")
                log_text = "\n".join(logs)
                log_doc.shipment_number = shipment_number
                log_doc.logs = log_text
                log_doc.icris_number = icris_number
                log_doc.save()
                return
                
            
        if sales_invoice.customer == customer.custom_default_customer:
            sales_invoice.custom_compensation_invoices = 1
            sig = 0
            existing_invoice = frappe.db.sql(
                        """SELECT name FROM `tabSales Invoice`
                        WHERE custom_shipment_number = %s
                        AND custom_compensation_invoices = 1
                        FOR UPDATE""",
                        shipment_number,
                        as_dict=True
                    )

            if existing_invoice:
                logs.append(f"Already Present In Sales Invoice")
                log_text = "\n".join(logs)

                log_doc.shipment_number = shipment_number
                log_doc.logs = log_text
                log_doc.icris_number = icris_number
                log_doc.save()
                return
               
        # Append an item row
        rows = {'item_code': "ICG", 'qty': '1', 'rate': 0}
        sales_invoice.append('items', rows)

        sales_invoice.insert()

    except json.JSONDecodeError:
        message = "Invalid JSON data"
        print(message)
        logging.error(message)

    except Exception as e:
        if sales_invoice and sales_invoice.name:
            print(f"Error while processing Sales Invoice {sales_invoice.name}: {str(e)}")
        else:
            print(f"An error occurred before Sales Invoice was created: {str(e)}")
        
        logging.error(f"An error occurred: {str(e)}")