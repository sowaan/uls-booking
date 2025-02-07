import frappe
from datetime import datetime


def execute():
    manifest = frappe.get_all("Manifest Upload Data", fields=["name", "attach_file", "manifest_modification_process", "opsys_upload_data", "manifest_file_type"])

    
    for doc in manifest:
      
        if doc.attach_file:
            frappe.db.set_value("Manifest Upload Data", doc.name, "manifest_file_type", "ISPS")
        elif doc.manifest_modification_process:
            frappe.db.set_value("Manifest Upload Data", doc.name, "manifest_file_type", "DWS")
        elif doc.opsys_upload_data:
            frappe.db.set_value("Manifest Upload Data", doc.name, "manifest_file_type", "OPSYS")
    
    
