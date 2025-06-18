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
def get_shipment_numbers_and_sales_invoices(start_date, end_date, station=None, billing_type=None, icris_number=None, customer=None, import__export=None,date_type=None,manifest_file_type=None,gateway=None):


    # Prepare the values dictionary to pass into the SQL query
    values = {
        "import__export": import__export,
        "start_date": start_date,
        "end_date": end_date,
        "station": station,
        "billing_type": billing_type,
        "icris_number": icris_number,
        "customer": customer,
        "manifest_file_type":manifest_file_type,
        "date_type":date_type,
        "gateway":gateway
    }
    # print("Values for SQL query:", values)

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
    if gateway:
        conditions.append("sn.gateway = %(gateway)s")

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
def generate_single_invoice(parent_id=None, login_username=None, shipment_number=None, sales_invoice_definition=None, end_date=None):
    print("Main Function")
    try:
        logs = []
        sales_invoice = None

        

        try:
            definition = frappe.get_doc("Sales Invoice Definition", sales_invoice_definition)
        except frappe.DoesNotExistError:
            logs.append("Sales Invoice Definition does not exist")
            return {"message": logs}
        setting = frappe.get_doc("Manifest Setting Definition")
        sales_invoice = frappe.new_doc("Sales Invoice")
        
        


        # print('hello')
        



        company = definition.default_company
        customer = frappe.db.get_value("Company", company, ["custom_default_customer"], as_dict=True)
        sales_invoice.set("customer", customer.custom_default_customer)
        
        # frappe.throw(_("Customer: {0}").format(customer.custom_default_customer))
        sales_invoice.custom_sales_invoice_definition = sales_invoice_definition
        
        for child_record in definition.sales_invoice_definition:
            doctype_name = child_record.ref_doctype
            field_name = child_record.field_name
            sales_field_name = child_record.sales_invoice_field_name
            is_linked = child_record.is_link

            value = frappe.db.get_value(doctype_name, {'shipment_number': shipment_number}, field_name)
            if value:
                if is_linked:
                    print('link')
                    if frappe.db.exists(child_record.linked_doctype, value):
                        sales_invoice.set(sales_field_name, value)
                        print('linkset')
                    else:
                        print('link not set')
                else:
                    sales_invoice.set(sales_field_name, value)
        # print(sales_invoice.custom_shipper_country)
        # print(sales_invoice.custom_shipper_country)
        # print(sales_invoice.custom_shipper_number)
        # print(sales_invoice.custom_consignee_number)
      

        
        if sales_invoice.custom_shipper_country.upper() == definition.origin_country.upper():
            imp_exp = "Export"
            if sales_invoice.custom_shipper_number:
                icris_number = sales_invoice.custom_shipper_number
            else:
                icris_number = definition.unassigned_icris_number

        elif sales_invoice.custom_shipper_country.upper() != definition.origin_country.upper():
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
            # print("No icris Account Found")
            if definition.unassigned_icris_number:
                icris_account = frappe.get_doc("ICRIS Account", definition.unassigned_icris_number)

        
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

        


        if sales_invoice.custom_shipment_number:
            # Get third party indicator from R200000
            third_party_ind_list = frappe.db.sql("""
                SELECT IFNULL(third_party_indicator_code, 0)
                FROM `tabR200000` 
                WHERE shipment_number = %s
            """, sales_invoice.custom_shipment_number, as_dict=False)

            if third_party_ind_list:
                third_party_ind = third_party_ind_list[0][0]
                sales_invoice.set('custom_third_party_indicator_code', third_party_ind)
            else:
                third_party_ind = None

            shipment_info = frappe.db.get_value(
                "Shipment Number",
                sales_invoice.custom_shipment_number,
                ["billing_term", "import__export"],
                as_dict=True
            )

            billing_term = shipment_info.billing_term.strip().upper() if shipment_info and shipment_info.billing_term else ""
            import_export_type = shipment_info.import__export.strip().upper() if shipment_info and shipment_info.import__export else ""

           

            if import_export_type == "EXPORT":
                if billing_term == "F/C":
                    sales_invoice.set('custom_compensation_invoices', True)
                    sales_invoice.set('custom_freight_invoices', False)
                elif third_party_ind and third_party_ind != "0":
                    sales_invoice.set('custom_compensation_invoices', True)
                    sales_invoice.set('custom_freight_invoices', False)
                else:
                    sales_invoice.set('custom_compensation_invoices', False)
                    sales_invoice.set('custom_freight_invoices', True)

            elif import_export_type == "IMPORT":
                if billing_term in ["P/P", "F/D"]:
                    sales_invoice.set('custom_compensation_invoices', True)
                    sales_invoice.set('custom_freight_invoices', False)
                else:
                    sales_invoice.set('custom_compensation_invoices', False)
                    sales_invoice.set('custom_freight_invoices', True)
        else:
            sales_invoice.set('custom_compensation_invoices', False)
            sales_invoice.set('custom_freight_invoices', True)



        
        
        is_export = sales_invoice.custom_shipper_country.upper() == definition.origin_country.upper()


        if login_username and frappe.db.exists('User', login_username):
            sales_invoice.set("custom_created_byfrom_billing_tool", login_username)
        if parent_id:
            sales_invoice.set("custom_parent_idfrom_billing_tool", parent_id)

        if sales_invoice.custom_freight_invoices:
            if is_export:
                # print('hello1')
                check1 = frappe.get_list("ICRIS Account",
                                        filters = {"name":icris_number})
                if not check1:
                    logs.append(f"No ICRIS Account Found {icris_number}")
                    # print("No ICRIS Account Found")
                    icris_number = definition.unassigned_icris_number
                if icris_number:
                    icris_doc = frappe.get_list("ICRIS Account",
                                        filters = {"name":icris_number})
                    icris = frappe.get_doc("ICRIS Account",icris_doc[0].name)
                    if icris.shipper_name:
                        sales_invoice.set("customer", icris.shipper_name)
                        # sales_invoice.customer = icris.shipper_name
                    else:
                        logs.append(f"No Customer Found icris number: {icris_number} , shipment number: {shipment_number}")
                        # print("No Customer Found")

            else:
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
                        sales_invoice.set("customer", icris1.shipper_name)
                        # sales_invoice.customer = icris1.shipper_name
                    else:
                        logs.append(f"No Customer Found icris number: {icris_number} , shipment number: {shipment_number}")
                        print("No Customer Found")
           
        
        log_list = frappe.get_list("Sales Invoice Logs",filters ={"shipment_number":shipment_number})

        if log_list:
            log_doc = frappe.get_doc("Sales Invoice Logs",log_list[0].name)
        else:
            log_doc = frappe.new_doc("Sales Invoice Logs")
        
        if sales_invoice.custom_freight_invoices:
            existing_invoice = frappe.db.sql(
                            """SELECT name FROM `tabSales Invoice`
                            WHERE custom_shipment_number = %s
                            AND custom_freight_invoices = 1
                            FOR UPDATE""",
                            shipment_number,
                            as_dict=True
                        )
            if existing_invoice:
                # print("Already Present In Sales Invoice fright")
                logs.append(f"Already Present In Sales Invoice")
                if logs:
                    # log_text = logs[0] + "\n" + "\n".join(logs[1:])
                    log_text = logs[0] if len(logs) == 1 else logs[0] + "\n" + "\n".join(logs[1:])
                else:
                    log_text = ""
                
                log_doc.logs =  log_text


                log_doc.set("shipment_number" , shipment_number)
                log_doc.set("sales_invoice_status" , 'Already Created')
                log_doc.set("created_byfrom_utility" , login_username)
                log_doc.set("parent_idfrom_utility" , parent_id)
                if existing_invoice[0]["name"]:
                    log_doc.set("sales_invoice" , existing_invoice[0]["name"])
                
                log_doc.save()
                return
                
        
        if sales_invoice.custom_compensation_invoices:
            existing_invoice = frappe.db.sql(
                        """SELECT name FROM `tabSales Invoice`
                        WHERE custom_shipment_number = %s
                        AND custom_compensation_invoices = 1
                        FOR UPDATE""",
                        shipment_number,
                        as_dict=True
                    )

            if existing_invoice:
                # print("Already Present In Sales Invoice comapnsation")
                logs.append(f"Already Present In Sales Invoice")
                if logs:
                    log_text = logs[0] if len(logs) == 1 else logs[0] + "\n" + "\n".join(logs[1:])
                else:
                    log_text = ""
                
                log_doc.logs = log_text
                log_doc.set("shipment_number" , shipment_number)
                log_doc.set("sales_invoice_status" , 'Already Created')
                log_doc.set("created_byfrom_utility" , login_username)
                log_doc.set("parent_idfrom_utility" , parent_id)
                if existing_invoice[0]["name"]:
                    log_doc.set("sales_invoice" , existing_invoice[0]["name"])
                log_doc.save()
                return
               
       
    
        itm_list = frappe.db.get_list("Item",
                        filters={
                            'disabled' : ['!=',1] 
                        }
                    )
        rows = {'item_code': itm_list[0].name, 'qty': '1', 'rate': 0}
        sales_invoice.append('items', rows)

        
        
        
        # print('hello')

        sales_invoice.insert()
        print(sales_invoice.custom_shipper_country)
        print(sales_invoice.custom_shipper_country)
        print(sales_invoice.custom_shipper_number)
        print(sales_invoice.custom_consignee_number)
        
        if frappe.db.exists("Sales Invoice", sales_invoice.name):
            log_filters = {'shipment_number': sales_invoice.custom_shipment_number}
            log_exists = frappe.db.exists("Sales Invoice Logs", log_filters)
            
            if not log_exists:
                # Create new log
                log_doc = frappe.new_doc('Sales Invoice Logs')
                log_doc.update({
                    'shipment_number': sales_invoice.custom_shipment_number,
                    'sales_invoice': sales_invoice.name,
                    'logs': "Sales Invoice Created Successfully"
                })
                
                im_ex = frappe.db.get_value('Shipment Number', 
                                        sales_invoice.custom_shipment_number, 
                                        'import__export')
                icris_field = 'custom_shipper_number' if im_ex == 'Export' else 'custom_consignee_number'
                icris_number = sales_invoice.get(icris_field)
                
                if icris_number and frappe.db.exists("ICRIS Account", icris_number):
                    log_doc.icris_number = icris_number
                log_doc.set("created_byfrom_utility", login_username)
                log_doc.set("parent_idfrom_utility", parent_id)
                log_doc.set("sales_invoice_status", 'Created')
                    
                # log_doc.insert()
            else:
                log_doc = frappe.get_doc("Sales Invoice Logs", log_filters)
                log_doc.update({
                    'sales_invoice': sales_invoice.name,
                    'logs': "Sales Invoice Created Successfully"
                })
                
                if icris_number and frappe.db.exists("ICRIS Account", icris_number):
                    log_doc.icris_number = icris_number
                log_doc.set("created_byfrom_utility", login_username)
                log_doc.set("parent_idfrom_utility", parent_id)
                log_doc.set("sales_invoice_status", 'Created')

                    
                # log_doc.save()
        else:
            if frappe.db.exists("Sales Invoice Logs", {'shipment_number': shipment_number}):
                log_doc = frappe.get_doc("Sales Invoice Logs", {'shipment_number': shipment_number})
            else:
                log_doc = frappe.new_doc('Sales Invoice Logs')
            log_doc.update({
                'shipment_number': shipment_number,
                'created_byfrom_utility': login_username,
                'parent_idfrom_utility': parent_id,
                'sales_invoice_status': 'Failed'
            })
            if not log_doc.logs:
                log_doc.logs = "Sales Invoice not created"
        if not log_doc.name:
            log_doc.insert(ignore_permissions=True)
        else:
            log_doc.save()
            
        #     print('hello')

    except json.JSONDecodeError:
        message = "Invalid JSON data"
        print(message)
        logging.error(message)

    except Exception as e:
        if sales_invoice and sales_invoice.name:
            print(f"Error while processing Sales Invoice {sales_invoice.name}: {str(e)}")
            log_doc = frappe.get_doc("Sales Invoice Logs", {'shipment_number': shipment_number}) if frappe.db.exists("Sales Invoice Logs", {'shipment_number': shipment_number}) else frappe.new_doc("Sales Invoice Logs")
            log_doc.set("shipment_number", shipment_number)
            log_doc.logs = f"Error while processing Sales Invoice : {str(e)}"
            log_doc.set("sales_invoice_status", 'Failed')
            icris = sales_invoice.custom_shipper_number if sales_invoice.custom_shipper_country.upper() == definition.origin_country.upper() else sales_invoice.custom_consignee_number
            if icris and frappe.db.exists("ICRIS Account", icris):
                log_doc.icris_number = icris
            if frappe.db.exists("User", login_username):
                log_doc.set("created_byfrom_utility", login_username)
            log_doc.set("parent_idfrom_utility", parent_id)
            log_doc.save(ignore_permissions=True)
        else:
            print(f"An error occurred before Sales Invoice was created: {str(e)}")
            log_doc = frappe.get_doc("Sales Invoice Logs", {'shipment_number': shipment_number}) if frappe.db.exists("Sales Invoice Logs", {'shipment_number': shipment_number}) else frappe.new_doc("Sales Invoice Logs")
            log_doc.set("shipment_number", shipment_number)
            log_doc.logs = f"Error before Sales Invoice creation: {str(e)}"
            log_doc.set("sales_invoice_status", 'Failed')
            icris = sales_invoice.custom_shipper_number if sales_invoice.custom_shipper_country.upper() == definition.origin_country.upper() else sales_invoice.custom_consignee_number
            if icris and frappe.db.exists("ICRIS Account", icris):
                log_doc.icris_number = icris
            if frappe.db.exists("User", login_username):
                log_doc.set("created_byfrom_utility", login_username)
            log_doc.set("parent_idfrom_utility", parent_id)
            log_doc.save(ignore_permissions=True)

        logging.error(f"An error occurred: {str(e)}")


@frappe.whitelist()
def get_sales_invoice_logs(shipment_number):
    log_lsit = frappe.db.get_value("Sales Invoice Logs", {"shipment_number":shipment_number}, ['sales_invoice', 'logs'], as_dict=True)
    if log_lsit:
        return {"sales_invoice_name": log_lsit.sales_invoice , "logs" : log_lsit.logs}
    else:
        return "No Logs Found"