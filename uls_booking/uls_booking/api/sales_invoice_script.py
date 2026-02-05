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
from frappe.utils import getdate
import logging

@frappe.whitelist()
def get_shipment_numbers_and_sales_invoices(
    start_date,
    end_date,
    station=None,
    billing_type=None,
    icris_number=None,
    customer=None,
    import__export=None,
    date_type=None,
    manifest_file_type=None,
    gateway=None
):
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
        SELECT
            sn.shipment_number,
            sn.manifest_input_date
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
        results = frappe.db.sql(base_query, values, as_dict=True)
        return results
    except Exception as e:
        frappe.log_error(str(e), "get_shipment_numbers_and_sales_invoices")
        return []





import frappe
from frappe.utils.data import getdate
import logging

# Caches
_customer_cache = {}
_ref_doc_cache = {}
_weight_cache = {}

# ----------------- Helper Functions -----------------

def get_definition_children(definition_name):
    """Fetch child definitions and organize by ref_doctype using SQL."""
    children = frappe.db.sql("""
        SELECT ref_doctype, field_name, sales_invoice_field_name, linked_doctype, is_link
        FROM `tabSales Invoice def`
        WHERE parent=%s
    """, definition_name, as_dict=True)

    ref_doc_map = {}
    for child in children:
        ref_doc_map.setdefault(child['ref_doctype'], []).append(child)
    return ref_doc_map


def apply_reference_docs_to_invoice(si, shipment_number, ref_doc_map):
    """Map reference docs to Sales Invoice fields, skipping 'name'."""
    shipment_cache = _ref_doc_cache.get(shipment_number, {})
    if not shipment_cache:
        return

    for ref_doctype, child_list in ref_doc_map.items():
        ref_doc = shipment_cache.get(ref_doctype)
        if not ref_doc:
            continue

        for child in child_list:
            field_name = child["field_name"]
            if field_name == "name":
                continue
            value = ref_doc.get(field_name)
            if value:
                if child["is_link"]:
                    if frappe.db.exists(child["linked_doctype"], value):
                        si.set(child["sales_invoice_field_name"], value)
                else:
                    si.set(child["sales_invoice_field_name"], value)


def get_reference_docs(shipment_numbers, ref_doc_map, manifest_input_date=None):
    global _ref_doc_cache

    for ref_doctype, child_list in ref_doc_map.items():
        try:
            field_names = [
                child["field_name"]
                for child in child_list
                if child["field_name"] != "name"
            ]

            if not field_names:
                continue

            fields_sql = ", ".join(f"`{f}`" for f in field_names)

            query = f"""
                SELECT shipment_number, {fields_sql}
                FROM `tab{ref_doctype}`
                WHERE shipment_number = %s
                  AND manifest_input_date = %s
            """

            frappe.logger("invoice").info(
                f"[REF DOC QUERY] Doctype={ref_doctype} | Shipment={shipment_numbers[0]}"
            )

            rows = frappe.db.sql(
                query,
                (shipment_numbers[0], manifest_input_date),
                as_dict=True
            )

            for row in rows:
                shipment = row["shipment_number"]
                _ref_doc_cache.setdefault(shipment, {})[ref_doctype] = row

        except Exception:
            # 🔴 THIS IS THE MONEY LOG
            frappe.log_error(
                title="Reference Doc SQL Failed",
                message=(
                    f"Doctype: {ref_doctype}\n"
                    f"Shipment: {shipment_numbers[0]}\n"
                    f"Query:\n{query}"
                ),
            )
            raise

def get_latest_by_manifest(doctype, shipment_number, fields, manifest_input_date):
    """
    Fetch latest row for a shipment up to a given manifest_input_date
    """
    if isinstance(fields, str):
        fields = [fields]

    frappe.logger("invoice").info(
        f"""
        get_latest_by_manifest DEBUG
        doctype={doctype}
        shipment_number={shipment_number}
        manifest_input_date={manifest_input_date}
        type={type(manifest_input_date)}
        """
    )
    rows = frappe.db.sql(
        f"""
        SELECT {", ".join(fields)}
        FROM `tab{doctype}`
        WHERE shipment_number = %s
          AND (%s IS NULL OR manifest_input_date = %s)
        ORDER BY manifest_input_date DESC
        LIMIT 1
        """,
        (shipment_number, manifest_input_date, manifest_input_date),
        as_dict=True,
    )
    
    return rows[0] if rows else None

def to_float(val):
    try:
        return float(val) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0

def get_shipment_weight(shipment_number, manifest_input_date):
    r202 = get_latest_by_manifest(
        "R202000",
        shipment_number,
        ["custom_expanded_shipment_weight"],
        manifest_input_date,
    )

    r201 = get_latest_by_manifest(
        "R201000",
        shipment_number,
        ["custom_minimum_bill_weight"],
        manifest_input_date,
    )

    weight1 = to_float(
        r202.get("custom_expanded_shipment_weight") if r202 else 0
    )

    weight2 = to_float(
        r201.get("custom_minimum_bill_weight") if r201 else 0
    )

    return max(weight1, weight2)


def get_shipment_weights(shipment_numbers, manifest_input_date):
    global _weight_cache

    for shipment in shipment_numbers:
        r202 = get_latest_by_manifest(
            "R202000",
            shipment,
            ["custom_expanded_shipment_weight"],
            manifest_input_date,
        )

        r201 = get_latest_by_manifest(
            "R201000",
            shipment,
            ["custom_minimum_bill_weight"],
            manifest_input_date,
        )

        _weight_cache.setdefault(shipment, {})["weight1"] = float(
            r202.get("custom_expanded_shipment_weight", 0) if r202 else 0
        )
        _weight_cache.setdefault(shipment, {})["weight2"] = float(
            r201.get("custom_minimum_bill_weight", 0) if r201 else 0
        )

# def get_shipment_weights(shipment_numbers):
#     """Fetch weights from R202000 and R201000 using SQL."""
#     global _weight_cache

#     rows_202 = frappe.db.sql("""
#         SELECT shipment_number, custom_expanded_shipment_weight
#         FROM `tabR202000`
#         WHERE shipment_number IN ({0})
#     """.format(", ".join(["%s"]*len(shipment_numbers))), shipment_numbers, as_dict=True)

#     rows_201 = frappe.db.sql("""
#         SELECT shipment_number, custom_minimum_bill_weight
#         FROM `tabR201000`
#         WHERE shipment_number IN ({0})
#     """.format(", ".join(["%s"]*len(shipment_numbers))), shipment_numbers, as_dict=True)

#     for w in rows_202:
#         _weight_cache.setdefault(w["shipment_number"], {})["weight1"] = float(w.get("custom_expanded_shipment_weight") or 0)

#     for w in rows_201:
#         _weight_cache.setdefault(w["shipment_number"], {})["weight2"] = float(w.get("custom_minimum_bill_weight") or 0)


def get_customer(icris_number, default_customer):
    """Fetch customer with caching using SQL."""
    global _customer_cache
    if icris_number in _customer_cache:
        return _customer_cache[icris_number]

    exists = frappe.db.sql("""SELECT 1 FROM `tabCustomer` WHERE name=%s""", icris_number)
    customer = icris_number if exists else default_customer
    _customer_cache[icris_number] = customer
    return customer


# ----------------- Main Function -----------------
def insert_sales_invoice_log(
    shipment_number,
    manifest_input_date,
    sales_invoice,
    status,
    logs
):
    frappe.get_doc({
        "doctype": "Sales Invoice Logs",
        "shipment_number": shipment_number,
        "manifest_input_date": manifest_input_date,
        "sales_invoice": sales_invoice,
        "sales_invoice_status": status,
        "logs": logs
    }).insert(ignore_permissions=True)

    frappe.db.commit()

@frappe.whitelist()
def generate_single_invoice(parent_id=None, login_username=None, 
                            shipment_number=None, 
                            sales_invoice_definition=None, 
                            end_date=None, manifest_input_date=None):
    import time
    start_total = time.time()

    sales_invoice_name = None
    manifest_input_date = getdate(manifest_input_date) if manifest_input_date else None


    # frappe.log_error(
    #     title="generate_single_invoice",
    #     message=f"called with shipment_number={shipment_number}, manifest_input_date={manifest_input_date}"
    # )

    if not shipment_number:
        return "Shipment number missing"

    # if not manifest_input_date:
    #     return {
    #         "sales_invoice_name": None,
    #         "logs": "Manifest input date missing",
    #         "sales_invoice_status": "Failed"
    #     }
    logs = []
    
    # Step 1: Check if invoice already exists using SQL
    # ------------------------------------------------------------------
    # STEP 1: Fetch ALL logs for this shipment (any date)
    # ------------------------------------------------------------------
    invoice_logs = frappe.db.sql("""
        SELECT
            sales_invoice,
            logs,
            sales_invoice_status,
            manifest_input_date
        FROM `tabSales Invoice Logs`
        WHERE shipment_number = %s
            and sales_invoice_status IN ('Created', 'Created (Duplicate Shipment)')
        ORDER BY creation DESC
    """, shipment_number, as_dict=True)

   
    # ------------------------------------------------------------------
    # STEP 2: If same manifest_input_date exists → RETURN EXISTING
    # ------------------------------------------------------------------
    for log in invoice_logs:
        if  not manifest_input_date or log.get("manifest_input_date") == manifest_input_date:
            return {
                "sales_invoice_name": log.get("sales_invoice"),
                "logs->": log.get("logs"),
                "sales_invoice_status": "Already Created"
            }

    # ------------------------------------------------------------------
    # STEP 3: Decide if this is a DUPLICATE shipment
    # ------------------------------------------------------------------
    is_duplicate_shipment = bool(invoice_logs)

    previous_manifest_dates = list(
        {
            l.get("manifest_input_date")
            for l in invoice_logs
            if l.get("manifest_input_date")
        }
    )

    # Step 2: Determine invoice type
    is_compensation = check_type(shipment_number, logs, manifest_input_date)

    # Step 3: Fetch definition using SQL
    definition = frappe.db.sql("""
        SELECT default_company, origin_country, unassigned_icris_number
        FROM `tabSales Invoice Definition`
        WHERE name=%s
    """, sales_invoice_definition, as_dict=True)[0]

    # Step 4: Fetch child definitions
    ref_doc_map = get_definition_children(sales_invoice_definition)

    # Step 5: Fetch reference docs
    get_reference_docs([shipment_number], ref_doc_map, manifest_input_date)

    # Step 6: Create Sales Invoice doc
    si = frappe.new_doc("Sales Invoice")
    si.custom_compensation_invoices = is_compensation
    si.custom_freight_invoices = not is_compensation
    si.custom_sales_invoice_definition = sales_invoice_definition
    si.custom_created_byfrom_billing_tool = login_username
    si.custom_parent_idfrom_billing_tool = parent_id

    # Map fields from reference docs
    apply_reference_docs_to_invoice(si, shipment_number, ref_doc_map)

    # Step 7: ICRIS logic
    shipper_country = (si.custom_shipper_country or "").upper()
    origin_country = (definition["origin_country"] or "").upper()

    
    is_export = shipper_country == origin_country
    unassign = definition["unassigned_icris_number"]

    if not is_export and not si.custom_consignee_number:
        ship_icris = str(shipment_number)[:6]
        exists = frappe.db.sql("""SELECT 1 FROM `tabICRIS Account` WHERE name=%s""", ship_icris)
        si.custom_consignee_number = ship_icris if exists else unassign

    if is_export and not si.custom_shipper_number:
        si.custom_shipper_number = unassign

    # icris_number = si.custom_shipper_number if is_export else si.custom_consignee_number

    # Step 8: Fetch weights
    # get_shipment_weights(shipment_number, manifest_input_date)
    # weight1 = _weight_cache.get(shipment_number, {}).get("weight1", 0)
    # weight2 = _weight_cache.get(shipment_number, {}).get("weight2", 0)
    # si.custom_shipment_weight = max(weight1, weight2)
    si.custom_shipment_weight = get_shipment_weight(
            shipment_number,
            manifest_input_date
        )
    # Step 9: Customer & Currency using SQL
    default_customer = frappe.db.sql("""
        SELECT custom_default_customer
        FROM `tabCompany`
        WHERE name=%s
    """, definition["default_company"])[0][0]

    customer = frappe.db.get_value(
            "Shipment Number",
            {
                "shipment_number": shipment_number,
                "manifest_input_date": manifest_input_date
            },
            "customer",
            order_by="modified desc"
        ) or default_customer


    si.customer = customer
    si.currency = frappe.db.sql("""SELECT default_currency FROM `tabCustomer` WHERE name=%s""", customer)[0][0]

    # Step 10: Add dummy item
    item_code = frappe.db.sql("""SELECT name FROM `tabItem` WHERE disabled=0 LIMIT 1""")
    if item_code:
        si.append("items", {"item_code": item_code[0][0], "qty": 1, "rate": 0})

    # Step 11: Insert invoice and log using Frappe Doc API
    try:
        si.posting_date = getdate(end_date)
        si.set_posting_time = 1
        si.insert(ignore_permissions=True)
        # si.submit()

        sales_invoice_name = si.name


        # Create or update log
        # insert_sales_invoice_log(
        #     shipment_number=shipment_number,
        #     manifest_input_date=manifest_input_date,
        #     sales_invoice=sales_invoice_name,
        #     status="Created",
        #     logs="Sales Invoice created successfully."
        # )

    except Exception as e:
        logging.error(f"Error creating invoice {shipment_number}: {e}")

        # Create failure log
        log_doc = frappe.get_doc({
            "doctype": "Sales Invoice Logs",
            "shipment_number": shipment_number,
            "logs": f"Failed: {frappe.get_traceback()}",
            "sales_invoice_status": "Failed",
            "manifest_input_date": manifest_input_date,
            "created_byfrom_utility": login_username,
            "parent_idfrom_utility": parent_id
        })
        log_doc.insert(ignore_permissions=True)
        frappe.log_error(
            "Generate Single Invoice failure",
            frappe.get_traceback()
            
        )        
        return {
            "sales_invoice_name": None,
            "logs": str(e),
            "sales_invoice_status": "Failed"
        }        

    # ------------------------------------------------------------------
    # STEP 5: PREPARE LOG MESSAGE
    # ------------------------------------------------------------------
    if is_duplicate_shipment:
        status = "Created (Duplicate Shipment)"
        formatted_dates = [
            d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
            for d in previous_manifest_dates
        ]

        final_log_message = (
            f"Duplicate invoice created for shipment {shipment_number}. "
            f"Previous manifest date(s): {', '.join(formatted_dates)}"
        )

    else:
        status = "Created"
        final_log_message = "Sales Invoice created successfully."

    # ------------------------------------------------------------------
    # STEP 6: INSERT LOG RECORD
    # ------------------------------------------------------------------
    frappe.get_doc({
        "doctype": "Sales Invoice Logs",
        "shipment_number": shipment_number,
        "manifest_input_date": manifest_input_date,
        "sales_invoice": sales_invoice_name,
        "sales_invoice_status": status,
        "logs": final_log_message
    }).insert(ignore_permissions=True)

    frappe.db.commit()

    # ------------------------------------------------------------------
    # STEP 7: RETURN RESPONSE
    # ------------------------------------------------------------------
    return {
        "sales_invoice_name": sales_invoice_name,
        "logs": final_log_message,
        "sales_invoice_status": "Created" # send created for both duplicate created and new created
    }

def check_type(shipment, logs, manifest_input_date=None):
    # Defensive: ensure logs is always a list
    if not isinstance(logs, list):
        logs = []
    
    imp_exp = "Export"  # Default assumption

    try:
        # -------------------------------
        # Fetch third party indicator
        # -------------------------------
        r200 = get_latest_by_manifest(
            "R200000",
            shipment,
            ["third_party_indicator_code"],
            manifest_input_date,
        )

        third_party_code = r200["third_party_indicator_code"] if r200 else "0"

        if third_party_code is None:
            logs.append(f"No R200000 found for shipment {shipment}")
            third_party_code = "0"

        # -------------------------------
        # Fetch shipment master data
        # -------------------------------
        shipment_info = get_latest_by_manifest(
                "Shipment Number",
                shipment,
                ["billing_term", "import__export"],
                manifest_input_date,
            )


        if not shipment_info:
            logs.append(f"No Shipment Number found for {shipment}")
            return False

        billing_term = (shipment_info.billing_term or "").strip().upper()
        imp_exp = (shipment_info.import__export or "").strip().upper()

        # -------------------------------
        # Business rules
        # -------------------------------
        if imp_exp == "EXPORT":
            return billing_term == "F/C" or third_party_code != "0"

        if imp_exp == "IMPORT":
            return billing_term in {"P/P", "F/D"}

        # Unknown import/export type
        logs.append(
            f"Unknown import/export value '{shipment_info.import__export}' for shipment {shipment}"
        )
        return False

    except Exception as e:
        # Absolute safety net
        logs.append(
            f"Error determining invoice type for shipment {shipment}: {str(e)}"
        )
        frappe.log_error(
            "check_type failure",
            frappe.get_traceback()
            
        )
        return False


def log_existing_invoice(invoice_type_fields, shipment_number, logs, login_username, parent_id):
    """
    Efficiently log already existing invoices.
    Creates or updates logs for shipments **only if invoice exists**.
    Returns True if any invoice found.
    """
    invoice_found = False

    #Single SQL query to check if any invoice exists for the shipment
    invoice_query = f"""
        SELECT name
        FROM `tabSales Invoice`
        WHERE custom_shipment_number = %s
          AND docstatus != 2
          AND ({' OR '.join(f'`{f}` = 1' for f in invoice_type_fields)})
        LIMIT 1
    """
    invoice = frappe.db.sql(invoice_query, (shipment_number,), as_dict=True)

    if not invoice:
        return False  #No invoice exists, do not create log

    invoice_found = True
    invoice_name = invoice[0]["name"]

    #Check if a log already exists
    log_query = "SELECT name FROM `tabSales Invoice Logs` WHERE shipment_number = %s LIMIT 1"
    log_result = frappe.db.sql(log_query, (shipment_number,), as_dict=True)

    log_message = "Already Present In Sales Invoice"

    if not log_result:
        #Insert a new log
        frappe.db.sql("""
            INSERT INTO `tabSales Invoice Logs`
                (name, creation, modified, owner, docstatus, shipment_number,
                 sales_invoice, sales_invoice_status, custom_created_byfrom_billing_tool,
                 custom_parent_idfrom_billing_tool, logs)
            VALUES (%s, NOW(), NOW(), %s, 0, %s, %s, 'Already Created', %s, %s, %s)
        """, (
            frappe.generate_hash(length=10),
            login_username,
            shipment_number,
            invoice_name,
            login_username,
            parent_id,
            log_message
        ))
    else:
        #Update existing log
        frappe.db.sql("""
            UPDATE `tabSales Invoice Logs`
            SET logs = %s,
                sales_invoice_status = 'Already Created',
                custom_created_byfrom_billing_tool = %s,
                parent_idfrom_utility = %s,
                sales_invoice = %s,
                modified = NOW()
            WHERE name = %s
        """, (
            log_message,
            login_username,
            parent_id,
            invoice_name,
            log_result[0]["name"]
        ))

    return invoice_found

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