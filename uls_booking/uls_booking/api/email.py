# Script Type: API

import frappe
import json
from frappe import _



@frappe.whitelist()
def send_multi_email_with_attachment(doc_name, selected_customers):
    # print('helo\n\n\n\n\n\n\n\n\n\n\n\n\nn\n', selected_customers)
    try:
        selected_customers = json.loads(selected_customers)
    except Exception as e:
        return {"status": "error", "message": f"Invalid data format: {str(e)}"}

    if not selected_customers:
        return {"status": "error", "message": "No customers selected."}
    
    if not frappe.db.exists("Sales Invoice PDF", doc_name):
        return {"status": "error", "message": f"Sales Invoice PDF with name {doc_name} does not exist."}

    failed_customers = []
    success_count = 0

    for customer in selected_customers:
        if not frappe.db.exists("Customer", customer):
            failed_customers.append(customer)
            continue
        
        customer_add = frappe.db.get_value("Customer", customer, "customer_primary_address")
        if customer_add:
            email = frappe.db.get_value("Address", customer_add, 'email_id')

        if not customer_add or not email:
            failed_customers.append(customer)
            continue


        try:
            pdf_attachment = frappe.attach_print(
                doctype="Sales Invoice PDF",
                name=doc_name,
                print_format="Sales Tax Invoice",
                # letterhead="My Custom Letterhead",
                lang="en"
            )

            frappe.sendmail(
                recipients=[email],
                subject="Sales Invocie",
                message="Please find the attached document.",
                attachments=[{
                    "fname": pdf_attachment["fname"],
                    "fcontent": pdf_attachment["fcontent"]
                }]
            )

            success_count += 1
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Failed to send invoice to {customer}")
            failed_customers.append(customer)

    if failed_customers:
        return {
            "status": "warning",
            "message": f"Emails sent successfully to {success_count} customers, but failed for {', '.join(failed_customers)}."
        }

    return {"status": "success", "message": f"Emails sent successfully to {success_count} customers!"}



