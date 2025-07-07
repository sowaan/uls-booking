from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import getdate
from frappe import get_cached_value, _
import json
import re
from datetime import datetime
import logging


@frappe.whitelist()
def get_shipment_numbers_and_sales_invoices(start_date, end_date, station=None, billing_type=None, icris_number=None, customer=None, import__export=None, date_type=None, manifest_file_type=None, gateway=None):
    values = {
        "start_date": start_date,
        "end_date": end_date,
        "station": station,
        "billing_type": billing_type,
        "icris_number": icris_number,
        "customer": customer,
        "import__export": import__export,
        "manifest_file_type": manifest_file_type,
        "gateway": gateway
    }

    date_field = "sn.date_shipped" if date_type == "Shipped Date" else "sn.import_date"

    base_query = f"""
        SELECT shipment_number
        FROM `tabShipment Number` AS sn
        WHERE {date_field} BETWEEN %(start_date)s AND %(end_date)s
    """

    filters = {
        "station": "sn.station = %(station)s",
        "billing_type": "sn.billing_type = %(billing_type)s",
        "icris_number": "sn.icris_number = %(icris_number)s",
        "customer": "sn.customer = %(customer)s",
        "import__export": "sn.import__export = %(import__export)s",
        "manifest_file_type": "sn.manifest_file_type = %(manifest_file_type)s",
        "gateway": "sn.gateway = %(gateway)s"
    }

    conditions = [sql for key, sql in filters.items() if values.get(key)]
    if conditions:
        base_query += " AND " + " AND ".join(conditions)

    try:
        results = frappe.db.sql(base_query, values)
        return [row[0] for row in results]
    except Exception as e:
        frappe.log_error(str(e), "get_shipment_numbers_and_sales_invoices")
        return []





@frappe.whitelist()
def generate_single_invoice(parent_id=None, login_username=None, shipment_number=None, sales_invoice_definition=None, end_date=None):
    log = frappe.db.get_value(
        "Sales Invoice Logs",
        {"shipment_number": shipment_number},
        ['sales_invoice', 'logs', 'sales_invoice_status'],
        as_dict=True
    )
    try:
        if not shipment_number:
            return
        print("Processing Invoice")
        sales_invoice = frappe.new_doc("Sales Invoice")
        logs = []
        
        if check_type(shipment_number, logs):
            sales_invoice.custom_compensation_invoices = True
            sales_invoice.custom_freight_invoices = False
        else:
            sales_invoice.custom_compensation_invoices = False
            sales_invoice.custom_freight_invoices = True

        invoice_type = "custom_compensation_invoices" if sales_invoice.custom_compensation_invoices else "custom_freight_invoices"
        if log_existing_invoice(invoice_type, shipment_number, logs, login_username, parent_id):
            return {
                "sales_invoice_name": log.sales_invoice,
                "logs": log.logs,
                "sales_invoice_status": log.sales_invoice_status
            } if log else "No Logs Found"

        definition = frappe.db.get_value(
            "Sales Invoice Definition",
            sales_invoice_definition,
            ["default_company", "origin_country", "unassigned_icris_number"],
            as_dict=True
        )
        if not definition:
            logs.append("Sales Invoice Definition does not exist")
            print("Sales Invoice Definition does not exist")
            return {
                "sales_invoice_name": log.sales_invoice,
                "logs": log.logs,
                "sales_invoice_status": log.sales_invoice_status
            } if log else "No Logs Found"

        definition_children = frappe.get_all(
            "Sales Invoice def",
            filters={"parent": sales_invoice_definition},
            fields=["ref_doctype", "field_name", "sales_invoice_field_name", "linked_doctype", "is_link"]
        )
        if not definition_children:
            logs.append("No child definitions found for this Sales Invoice Definition")
            print("No child definitions found for this Sales Invoice Definition")
            return {
                "sales_invoice_name": log.sales_invoice,
                "logs": log.logs,
                "sales_invoice_status": log.sales_invoice_status
            } if log else "No Logs Found"

        
        company = definition.default_company

        
        sales_invoice.custom_sales_invoice_definition = sales_invoice_definition
        unassign = definition.unassigned_icris_number

        ref_doc_map = {}
        for child in definition_children:
            ref_doc_map.setdefault(child.ref_doctype, []).append(child)

        for ref_doctype, child_list in ref_doc_map.items():
            field_names = list(set(child["field_name"] for child in child_list))
            if not field_names:
                continue

            ref_doc_data = frappe.get_all(
                ref_doctype,
                filters={"shipment_number": shipment_number},
                fields=field_names,
                limit_page_length=1
            )

            if not ref_doc_data:
                continue

            ref_doc_row = ref_doc_data[0]

            for child in child_list:
                value = ref_doc_row.get(child["field_name"])
                if not value:
                    continue

                if child["is_link"]:
                    if frappe.db.exists(child["linked_doctype"], value):
                        sales_invoice.set(child["sales_invoice_field_name"], value)
                else:
                    sales_invoice.set(child["sales_invoice_field_name"], value)
        
        shipper_country = (sales_invoice.custom_shipper_country or "").upper()
        origin_country = (definition.origin_country or "").upper()

        icris_number = (
            sales_invoice.custom_shipper_number if shipper_country == origin_country
            else sales_invoice.custom_consignee_number
        ) or unassign

        sales_invoice.posting_date = getdate(end_date)
        sales_invoice.set_posting_time = 1
        weight1 = frappe.db.get_value("R202000", {"shipment_number": shipment_number}, "custom_expanded_shipment_weight") or 0.0
        weight2 = frappe.db.get_value("R201000", {"shipment_number": shipment_number}, "custom_minimum_bill_weight") or 0.0
        sales_invoice.custom_shipment_weight = max(float(weight1), float(weight2))

        
        try:
            if login_username and frappe.get_cached_value('User', login_username, 'name'):
                sales_invoice.custom_created_byfrom_billing_tool = login_username
        except frappe.DoesNotExistError:
            pass

        sales_invoice.custom_parent_idfrom_billing_tool = parent_id if parent_id else None
        
        if sales_invoice.custom_freight_invoices:
            cust = get_frt_cust(icris_number, unassign, shipment_number, logs)
        elif sales_invoice.custom_compensation_invoices:
            cust = get_cached_value("Company", company, "custom_default_customer")
        

        if cust:
            sales_invoice.set("customer", cust)
        else:
            sales_invoice.customer = get_cached_value("Company", company, "custom_default_customer")
        
        sales_invoice.currency = frappe.db.get_value("Customer", sales_invoice.customer, "default_currency")

        item_code = frappe.db.get_value("Item", {"disabled": 0}, "name")
        if item_code:
            sales_invoice.append("items", {
                "item_code": item_code,
                "qty": 1,
                "rate": 0
            })
        # print("insert")
        sales_invoice.insert()
        # print("after insert")

        log_filters = {'shipment_number': shipment_number}
        log_doc = frappe.get_doc("Sales Invoice Logs", log_filters) if frappe.db.exists("Sales Invoice Logs", log_filters) else frappe.new_doc("Sales Invoice Logs")
        if frappe.db.exists("Sales Invoice", sales_invoice.name):
            log_doc.update({
                'shipment_number': shipment_number,
                'sales_invoice': sales_invoice.name,
                'logs': "Sales Invoice Created Successfully",
                'created_byfrom_utility': login_username,
                'parent_idfrom_utility': parent_id,
                'sales_invoice_status': 'Created'
            })
            if sales_invoice.custom_import__export_si:
                imp_exp = (sales_invoice.custom_import__export_si or "").strip().upper()
            icris_field = 'custom_shipper_number' if imp_exp == 'EXPORT' else 'custom_consignee_number'
            icris_number = sales_invoice.get(icris_field)

            if icris_number:
                if frappe.db.exists("ICRIS Account", icris_number):
                    log_doc.icris_number = icris_number
        else:
            log_doc.update({
            'shipment_number': shipment_number,
            'created_byfrom_utility': login_username,
            'parent_idfrom_utility': parent_id,
            'sales_invoice_status': 'Failed',
            'logs': log_doc.logs or "Sales Invoice not created"
        })
        log_doc.insert(ignore_permissions=True) if not log_doc.name else log_doc.save()
    
    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        logging.error(f"An error occurred: {error_msg}")

        shipper_country = (sales_invoice.custom_shipper_country or "").strip().upper() if sales_invoice else ""
        origin_country = (definition.origin_country or "").strip().upper() if definition else ""

        icris_field = 'custom_shipper_number' if shipper_country == origin_country else 'custom_consignee_number'
        icris_number = getattr(sales_invoice, icris_field, None) if sales_invoice else None

        log_filters = {'shipment_number': shipment_number}
        log_doc = frappe.get_doc("Sales Invoice Logs", log_filters) if frappe.db.exists("Sales Invoice Logs", log_filters) else frappe.new_doc("Sales Invoice Logs")
        log_messages = [f"Error while processing Sales Invoice: {error_msg}"]

        try:
            if login_username:
                user = frappe.get_cached_value("User", login_username, "name")
                log_doc.created_byfrom_utility = user
        except frappe.DoesNotExistError:
            log_messages.append(f"User '{login_username}' not found")

        log_doc.update({
            'shipment_number': shipment_number,
            'sales_invoice_status': 'Failed',
            'logs': "\n".join(log_messages),
            'parent_idfrom_utility': parent_id
        })

        

        if icris_number and frappe.db.exists("ICRIS Account", icris_number):
            log_doc.icris_number = icris_number

        log_doc.save(ignore_permissions=True)
    return {
        "sales_invoice_name": log.sales_invoice,
        "logs": log.logs,
        "sales_invoice_status": log.sales_invoice_status
    } if log else "No Logs Found"







def check_type(shipment, logs):
    third_party_code = frappe.db.get_value(
        "R200000",
        {"shipment_number": shipment},
        "third_party_indicator_code"
    )

    if third_party_code is None:
        logs.append(f"No R200000 found for shipment {shipment}")
        third_party_code = "0"

    shipment_info = frappe.db.get_value(
        "Shipment Number",
        shipment,
        ["billing_term", "import__export"],
        as_dict=True
    )

    if not shipment_info:
        logs.append(f"No Shipment Number found for {shipment}")
        return False

    billing_term = (shipment_info.billing_term or "").strip().upper()
    imp_exp = (shipment_info.import__export or "").strip().upper()

    if imp_exp == "EXPORT":
        return billing_term == "F/C" or third_party_code != "0"

    if imp_exp == "IMPORT":
        return billing_term in {"P/P", "F/D"}

    return False


def log_existing_invoice(invoice_type_field, ship, logs, login_username, parent_id):
    invoice_name = frappe.db.get_value(
        "Sales Invoice",
        {
            "custom_shipment_number": ship,
            invoice_type_field: 1
        },
        "name"
    )

    if invoice_name:
        log_name = frappe.db.get_value("Sales Invoice Logs", {"shipment_number": ship}, "name")
        log_doc = frappe.get_doc("Sales Invoice Logs", log_name) if log_name else frappe.new_doc("Sales Invoice Logs")
        logs.append("Already Present In Sales Invoice")
        log_doc.update({
            "logs": "\n".join(logs),
            "shipment_number": ship,
            "sales_invoice_status": "Already Created",
            "created_byfrom_utility": login_username,
            "parent_idfrom_utility": parent_id,
            "sales_invoice": invoice_name
        })
        log_doc.save()
        return True
    return False



def get_frt_cust(icris_number, unassign, shipment_number, logs):
    """
    Determine customer from:
    1. ICRIS Account (original)
    2. R300000 → alternate_tracking_number_1 → Customer
    3. Unassigned ICRIS Account
    """

    shipper_name = frappe.db.get_value("ICRIS Account", icris_number, "shipper_name")
    if shipper_name:
        return shipper_name

    logs.append(f"No shipper_name in ICRIS Account: {icris_number}, checking R300000...")

    alt_track_r3 = frappe.db.get_value("R300000", {"shipment_number": shipment_number}, "alternate_tracking_number_1")
    if alt_track_r3:
        cust_name = frappe.db.get_value(
            "Customer",
            {"disabled": 0, "custom_import_account_no": alt_track_r3},
            "name"
        )
        if cust_name:
            return cust_name

    shipper_name = frappe.db.get_value("ICRIS Account", unassign, "shipper_name")
    if shipper_name:
        logs.append(f"Customer not found from R300000.So using ICRIS Account: {unassign}")
        return shipper_name

    return None



@frappe.whitelist()
def get_sales_invoice_logs(shipment_number):
    log = frappe.db.get_value(
        "Sales Invoice Logs",
        {"shipment_number": shipment_number},
        ['sales_invoice', 'logs', 'sales_invoice_status'],
        as_dict=True
    )
    return {
        "sales_invoice_name": log.sales_invoice,
        "logs": log.logs,
        "sales_invoice_status": log.sales_invoice_status
    } if log else "No Logs Found"

