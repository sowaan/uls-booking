import frappe
import json
from frappe import _
from frappe.utils.pdf import get_pdf


def scrub(txt=None):
    if txt is None:
        return ""
    return txt.replace(' ', '_').lower()



@frappe.whitelist()
def send_multi_email_with_attachment(doc_name, selected_customers):
    
    try:
        selected_customers = json.loads(selected_customers)
    except Exception as e:
        return {"status": "error", "message": f"Invalid data format: {str(e)}"}

    if not selected_customers:
        return {"status": "error", "message": "No customers selected."}
    
    if not frappe.db.exists("Sales Invoice PDF", doc_name):
        return {"status": "error", "message": f"Sales Invoice PDF with name {doc_name} does not exist."}

    original_doc = frappe.get_doc("Sales Invoice PDF", doc_name)
    failed_customers = []
    success_count = 0

    for row in original_doc.customer_with_sales_invoice:
        if row.customer not in selected_customers:
            continue

        # Get customer email
        # customer_add = frappe.db.get_value("Customer", row.customer, "customer_primary_address")
        # email = frappe.db.get_value("Address", customer_add, "email_id") if customer_add else None
        email = row.email if row.email else None
        if not email:
            customer_add = frappe.db.get_value("Customer", row.customer, "customer_primary_address")
            email = frappe.db.get_value("Address", customer_add, "email_id") if customer_add else None
        if not email:
            failed_customers.append(row.customer)
            continue

        try:
            single_doc = frappe.copy_doc(original_doc)
            single_doc.customer_with_sales_invoice = [row]

            frappe.flags.ignore_print_permissions = True
            html = frappe.get_print(
                "Sales Invoice PDF",
                single_doc.name,
                print_format="Specific Customer Sales Invoice Tax",
                doc=single_doc
            )
            pdf_data = get_pdf(html)

            filename = f"{scrub(row.customer)}_{row.name1}.pdf"

            frappe.sendmail(
                recipients=[email],
                subject="Sales Invoice",
                message="Please find your sales invoice attached.",
                attachments=[{
                    "fname": filename,
                    "fcontent": pdf_data
                }]
            )

            success_count += 1

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Failed to send invoice to {row.customer}")
            failed_customers.append(row.customer)

    if failed_customers:
        return {
            "status": "warning",
            "message": f"Emails sent to {success_count} customers, but failed for: {', '.join(failed_customers)}."
        }

    return {"status": "success", "message": f"Emails sent successfully to {success_count} customers!"}
