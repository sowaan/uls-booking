# Script Type: API

import frappe
import json





@frappe.whitelist()
def send_email_with_attachment(doc_name):
    docname = doc_name
    email = frappe.get_value("Customer Shipment Invoice",docname,"email")
    if email:
        recipients = [email]
        subject = "Sales Invoice"
        message = "Please find the attached document."

        
        doctype = "Customer Shipment Invoice"  
        
        print_format = "Sales Tax Invoice" 
        letterhead = "My Custom Letterhead"
        

        try:
            pdf_attachment = frappe.attach_print(
                doctype=doctype,
                name=docname,
                print_format=print_format,
                letterhead=letterhead,
                lang="en"
            )

            frappe.sendmail(
                recipients=recipients,
                subject=subject,
                message=message,
                attachments=[{
                    "fname": pdf_attachment["fname"],
                    "fcontent": pdf_attachment["fcontent"]
                }]
            )

            
            return {"status": "success", "message": "Email sent successfully!"}
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Send Email with Attachment")
            return {"status": "error", "message": str(e)}
    else:
        frappe.throw("Email Not Found")







@frappe.whitelist()
def send_multi_email_with_attachment(doc_name, selected_customers):
    print('helo\n\n\n\n\n\n\n\n\n\n\n\n\nn\n', selected_customers)
    try:
        selected_customers = json.loads(selected_customers)
    except Exception as e:
        return {"status": "error", "message": f"Invalid data format: {str(e)}"}

    if not selected_customers:
        return {"status": "error", "message": "No customers selected."}

    failed_customers = []
    success_count = 0

    for customer in selected_customers:
        # invoice = frappe.get_list(
        #     "Customer Shipment Invoice",
        #     filters={"sales_invoice_pdf": doc_name, "customer": customer},
        #     pluck="name",
        #     limit=1  
        # )
        if not frappe.db.exists("Customer", customer):
            failed_customers.append(customer)
            continue
        
        customer_add = frappe.db.get_value("Customer", customer, "customer_primary_address")
        if customer_add:
            email = frappe.db.get_value("Address", customer_add, 'email_id')

        if not customer_add or not email:
            failed_customers.append(customer)
            continue

        # if not invoice:
        #     failed_customers.append(customer)
        #     continue

        # invoice_name = invoice[0] 
        # email = frappe.get_value("Customer Shipment Invoice", invoice_name, "email")

        # if not email:
        #     failed_customers.append(customer)
        #     continue

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



