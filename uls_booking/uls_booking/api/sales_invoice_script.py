from __future__ import unicode_literals
import frappe
from frappe.utils import getdate
import logging
from frappe import _

# Constants and configuration
SETTINGS = None
DEFINITION = None

def initialize_constants(sales_invoice_definition):
    """Initialize global constants once to avoid repeated lookups"""
    global SETTINGS, DEFINITION
    if DEFINITION is None:
        DEFINITION = frappe.get_doc("Sales Invoice Definition", sales_invoice_definition)
    if SETTINGS is None:
        SETTINGS = frappe.get_doc("Manifest Setting Definition")

@frappe.whitelist()
def get_shipment_numbers_and_sales_invoices(start_date, end_date, station=None, billing_type=None, 
                                          icris_number=None, customer=None, import__export=None,
                                          date_type=None, manifest_file_type=None, gateway=None):
    """
    Get shipment numbers based on filters
    Optimized by:
    - Using parameterized queries
    - Dynamic condition building
    - Reduced database calls
    """
    filters = {
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

    date_field = "date_shipped" if date_type == 'Shipped Date' else "import_date"
    base_query = f"""
        SELECT shipment_number
        FROM `tabShipment Number`
        WHERE {date_field} BETWEEN %(start_date)s AND %(end_date)s
    """

    conditions = []
    for field, value in filters.items():
        if value and field not in ['start_date', 'end_date']:
            conditions.append(f"{field} = %({field})s")

    if conditions:
        base_query += " AND " + " AND ".join(conditions)

    try:
        results = frappe.db.sql(base_query, filters, as_list=True)
        return [row[0] for row in results]
    except Exception as e:
        logging.error(f"Error fetching shipment numbers: {str(e)}")
        return []

@frappe.whitelist()
def generate_single_invoice(parent_id=None, login_username=None, shipment_number=None, 
                          sales_invoice_definition=None, end_date=None):
    """
    Generate a single sales invoice with optimized:
    - Database queries
    - Error handling
    - Logging
    - Code organization
    """
    try:
        initialize_constants(sales_invoice_definition)
        logs = []
        sales_invoice = frappe.new_doc("Sales Invoice")
        
        # Set basic invoice properties
        set_basic_invoice_properties(sales_invoice, shipment_number, sales_invoice_definition, end_date)
        
        # Determine invoice type and set customer
        determine_invoice_type_and_customer(sales_invoice, logs)
        
        # Check for existing invoices
        if check_existing_invoices(sales_invoice, shipment_number, logs, parent_id, login_username):
            return {"status": "exists", "logs": logs}
        
        # Create the invoice
        create_invoice_with_logging(sales_invoice, shipment_number, parent_id, login_username, logs)
        
        return {"status": "success", "invoice": sales_invoice.name}
        
    except Exception as e:
        handle_generation_error(e, sales_invoice, shipment_number, parent_id, login_username, logs)
        return {"status": "error", "message": str(e)}

def set_basic_invoice_properties(sales_invoice, shipment_number, sales_invoice_definition, end_date):
    """Set basic properties for the sales invoice"""
    sales_invoice.custom_sales_invoice_definition = sales_invoice_definition
    sales_invoice.posting_date = getdate(end_date)
    sales_invoice.set_posting_time = 1
    
    # Map fields from linked documents
    for child_record in DEFINITION.sales_invoice_definition:
        value = frappe.db.get_value(
            child_record.ref_doctype, 
            {'shipment_number': shipment_number}, 
            child_record.field_name
        )
        if value and (not child_record.is_link or frappe.db.exists(child_record.linked_doctype, value)):
            sales_invoice.set(child_record.sales_invoice_field_name, value)

def determine_invoice_type_and_customer(sales_invoice, logs):
    """Determine invoice type and set appropriate customer"""
    is_export = sales_invoice.custom_shipper_country.upper() == DEFINITION.origin_country.upper()
    imp_exp = "Export" if is_export else "Import"
    
    # Get ICRIS number based on export/import status
    icris_number = (
        sales_invoice.custom_shipper_number if is_export 
        else sales_invoice.custom_consignee_number
    ) or DEFINITION.unassigned_icris_number
    
    try:
        icris_account = frappe.get_doc("ICRIS Account", icris_number)
        if icris_account.shipper_name:
            sales_invoice.customer = icris_account.shipper_name
    except frappe.DoesNotExistError:
        logs.append(f"No ICRIS Account Found {icris_number}")
        if DEFINITION.unassigned_icris_number:
            icris_account = frappe.get_doc("ICRIS Account", DEFINITION.unassigned_icris_number)
    
    # Set default company customer if no customer found
    if not sales_invoice.customer:
        company = DEFINITION.default_company
        default_customer = frappe.db.get_value("Company", company, "custom_default_customer")
        sales_invoice.customer = default_customer
    
    # Set weight
    weights = [
        frappe.db.get_value("R202000", {'shipment_number': sales_invoice.custom_shipment_number}, "custom_expanded_shipment_weight"),
        frappe.db.get_value("R201000", {'shipment_number': sales_invoice.custom_shipment_number}, "custom_minimum_bill_weight")
    ]
    sales_invoice.custom_shipment_weight = max(float(w or 0) for w in weights)
    sales_invoice.currency = frappe.db.get_value("Customer", sales_invoice.customer, "default_currency")
    
    # Determine invoice type
    determine_invoice_type(sales_invoice)

def determine_invoice_type(sales_invoice):
    """Determine if invoice is freight or compensation"""
    if not sales_invoice.custom_shipment_number:
        sales_invoice.custom_freight_invoices = True
        sales_invoice.custom_compensation_invoices = False
        return
    
    third_party_ind = frappe.db.get_value(
        "R200000",
        {"shipment_number": sales_invoice.custom_shipment_number},
        "IFNULL(third_party_indicator_code, 0)"
    )
    
    shipment_info = frappe.db.get_value(
        "Shipment Number",
        sales_invoice.custom_shipment_number,
        ["billing_term", "import__export"],
        as_dict=True
    )
    
    if not shipment_info:
        return
        
    billing_term = (shipment_info.billing_term or "").strip().upper()
    import_export = (shipment_info.import__export or "").strip().upper()
    
    if import_export == "EXPORT":
        if billing_term == "F/C" or (third_party_ind and third_party_ind != "0"):
            set_compensation_invoice(sales_invoice)
        else:
            set_freight_invoice(sales_invoice)
    elif import_export == "IMPORT":
        if billing_term in ["P/P", "F/D"]:
            set_compensation_invoice(sales_invoice)
        else:
            set_freight_invoice(sales_invoice)

def set_compensation_invoice(sales_invoice):
    sales_invoice.custom_compensation_invoices = True
    sales_invoice.custom_freight_invoices = False

def set_freight_invoice(sales_invoice):
    sales_invoice.custom_compensation_invoices = False
    sales_invoice.custom_freight_invoices = True

def check_existing_invoices(sales_invoice, shipment_number, logs, parent_id, login_username):
    """Check for existing invoices and create logs if found"""
    invoice_type = "freight" if sales_invoice.custom_freight_invoices else "compensation"
    existing_invoice = frappe.db.get_value(
        "Sales Invoice",
        {
            "custom_shipment_number": shipment_number,
            f"custom_{invoice_type}_invoices": 1
        },
        "name"
    )
    
    if not existing_invoice:
        return False
        
    logs.append("Invoice already exists")
    update_invoice_log(
        shipment_number,
        existing_invoice,
        "\n".join(logs),
        "Already Created",
        parent_id,
        login_username
    )
    return True

def create_invoice_with_logging(sales_invoice, shipment_number, parent_id, login_username, logs):
    """Create invoice with proper logging"""
    # Add a dummy item (required by Frappe)
    dummy_item = frappe.db.get_list("Item", filters={"disabled": 0}, limit=1)
    if dummy_item:
        sales_invoice.append("items", {
            "item_code": dummy_item[0].name,
            "qty": 1,
            "rate": 0
        })
    
    sales_invoice.insert()
    
    # Update log
    log_status = "Created" if frappe.db.exists("Sales Invoice", sales_invoice.name) else "Failed"
    log_message = "Sales Invoice Created Successfully" if log_status == "Created" else "Sales Invoice creation failed"
    
    update_invoice_log(
        shipment_number,
        sales_invoice.name,
        log_message,
        log_status,
        parent_id,
        login_username
    )

def update_invoice_log(shipment_number, invoice_name, message, status, parent_id, login_username):
    """Create or update invoice log"""
    log_filters = {"shipment_number": shipment_number}
    log_exists = frappe.db.exists("Sales Invoice Logs", log_filters)
    
    if log_exists:
        log_doc = frappe.get_doc("Sales Invoice Logs", log_filters)
    else:
        log_doc = frappe.new_doc("Sales Invoice Logs")
    
    log_doc.update({
        "shipment_number": shipment_number,
        "sales_invoice": invoice_name,
        "logs": message,
        "sales_invoice_status": status,
        "created_byfrom_utility": login_username,
        "parent_idfrom_utility": parent_id
    })
    
    # Set ICRIS number if available
    if invoice_name:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        is_export = invoice.custom_shipper_country.upper() == DEFINITION.origin_country.upper()
        icris_number = invoice.custom_shipper_number if is_export else invoice.custom_consignee_number
        if icris_number and frappe.db.exists("ICRIS Account", icris_number):
            log_doc.icris_number = icris_number
    
    if not log_doc.name:
        log_doc.insert(ignore_permissions=True)
    else:
        log_doc.save(ignore_permissions=True)

def handle_generation_error(error, sales_invoice, shipment_number, parent_id, login_username, logs):
    """Handle errors during invoice generation"""
    error_message = f"Error processing Sales Invoice: {str(error)}"
    logging.error(error_message)
    
    if sales_invoice and getattr(sales_invoice, "name", None):
        error_message = f"Error while processing Sales Invoice {sales_invoice.name}: {str(error)}"
    
    logs.append(error_message)
    
    update_invoice_log(
        shipment_number,
        sales_invoice.name if sales_invoice else None,
        "\n".join(logs),
        "Failed",
        parent_id,
        login_username
    )

@frappe.whitelist()
def get_sales_invoice_logs(shipment_number):
    """Get logs for a sales invoice"""
    log_data = frappe.db.get_value(
        "Sales Invoice Logs",
        {"shipment_number": shipment_number},
        ["sales_invoice", "logs", "sales_invoice_status"],
        as_dict=True
    )
    
    if log_data:
        return {
            "sales_invoice_name": log_data.sales_invoice,
            "logs": log_data.logs,
            "sales_invoice_status": log_data.sales_invoice_status
        }
    return {"message": "No logs found"}