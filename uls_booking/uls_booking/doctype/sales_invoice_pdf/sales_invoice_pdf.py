import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe import enqueue

class SalesInvoicePDF(Document):
    def autoname(self):
        prefix = "AAA"
        station = "0"
        serial = '001'

        if self.invoice_type == "Duty and Taxes Invoices":
            prefix = "D&T"
        elif self.invoice_type == "Compensation Invoices":
            prefix = "COMP"
        elif hasattr(self, 'import__export') and self.import__export:
            if self.import__export == "Import":
                prefix = "IFC"
            elif self.import__export == "Export":
                prefix = "EPP"

        station_code = frappe.db.get_value("Station", self.station, "station_code") if hasattr(self, 'station') and self.station else "0"
        # if hasattr(self, 'station') and self.station:
        #     station_map = {
        #         "karachi": "1",
        #         "lahore": "2",
        #         "islamabad": "3",
        #         "sialkot": "4",
        #         "faisalabad": "5",
        #         "peshawar": "6"
        #     }
        #     station = station_map.get(self.station.lower(), "0") if self.station else "0"

        last_invoice_name = frappe.db.get_value("Sales Invoice PDF", {}, "name", order_by="creation DESC")
        current_year = datetime.today().strftime("%y")
        current_month = datetime.today().strftime("%m")

        if last_invoice_name:
            if "-" in last_invoice_name:
                parts = last_invoice_name.split("-")
                if len(parts) == 3:
                    serial_with_dates = parts[-1]
                    pre_year = serial_with_dates[:2]
                    if pre_year == current_year:
                        serial = serial_with_dates[4:]
                        if serial.isdigit():
                            serial = str(int(serial) + 1).zfill(3)

        self.name = f"{prefix}-{station_code}-{current_year}{current_month}{serial}"


    def before_save(self):
        self.customer_with_sales_invoice = []
        self.total_invoices = 0
        self.all_sales_invoices = ""

        conditions = ["docstatus = 1"]
        conditions.append("(custom_sales_invoice_pdf_ref IS NULL OR custom_sales_invoice_pdf_ref = '')")
        values = {}

        # Map for date filtering
        date_field_map = {
            "Posting Date": "posting_date",
            "Shipped Date": "custom_date_shipped",
            "Import Date": "custom_import_date",
            "Arrival Date": "custom_arrival_date"
        }
        date_field = date_field_map.get(self.date_type)
        if date_field:
            if self.start_date and self.end_date:
                conditions.append(f"{date_field} BETWEEN %(start_date)s AND %(end_date)s")
                values["start_date"] = self.start_date
                values["end_date"] = self.end_date
            elif self.start_date:
                conditions.append(f"{date_field} >= %(start_date)s")
                values["start_date"] = self.start_date
            elif self.end_date:
                conditions.append(f"{date_field} <= %(end_date)s")
                values["end_date"] = self.end_date

        # Invoice type condition
        if self.invoice_type:
            invoice_type_map = {
                "Freight Invoices": "custom_freight_invoices = 1",
                "Duty and Taxes Invoices": "custom_duty_and_taxes_invoice = 1",
                "Compensation Invoices": "custom_compensation_invoices = 1"
            }
            condition = invoice_type_map.get(self.invoice_type)
            if condition:
                conditions.append(condition)

        # Filter by customer if provided
        if self.customer:
            conditions.append("customer = %(customer)s")
            values["customer"] = self.customer

        # Build where clause
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        peak_code = frappe.db.get_single_value("Manifest Setting Definition", "peak_charges")
        values["peak_code"] = peak_code

        # Base query
        query = f"""
            SELECT 
                si.name,
                si.posting_date,
                si.custom_date_shipped,
                si.custom_import_date,
                si.custom_shipment_number,
                si.customer,
                si.grand_total,
                si.base_grand_total,
                si.total_taxes_and_charges,
                si.base_total_taxes_and_charges,
                si.plc_conversion_rate,
                sn.station,
                MAX(
                    CASE 
                        WHEN sii.item_code = %(peak_code)s AND sii.amount > 0 THEN 1
                        ELSE 0 
                    END
                ) AS item_status
            FROM (
                SELECT * FROM `tabSales Invoice`
                {where_clause}
            ) AS si
            LEFT JOIN `tabShipment Number` sn ON si.custom_shipment_number = sn.name
            LEFT JOIN `tabCustomer` c ON si.customer = c.name
            LEFT JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        """

        outer_conditions = []

        if self.station:
            outer_conditions.append("sn.station = %(station)s")
            values["station"] = self.station

        if self.invoice_type != "Duty and Taxes Invoices":
            if self.icris_number:
                outer_conditions.append("sn.icris_number = %(icris_number)s")
                values["icris_number"] = self.icris_number
            if self.billing_type:
                outer_conditions.append("c.custom_billing_type = %(billing_type)s")
                values["billing_type"] = self.billing_type
            if self.import__export:
                outer_conditions.append("sn.import__export = %(import__export)s")
                values["import__export"] = self.import__export

        if self.billing_type and self.billing_type == "Single":
            if self.tracking_number:
                outer_conditions.append("custom_tracking_number = %(tracking_number)s")
                values["tracking_number"] = self.tracking_number.strip()
        
            if self.shipment_number:
                outer_conditions.append("custom_shipment_number = %(shipment_number)s")
                values["shipment_number"] = self.shipment_number.strip()

        if outer_conditions:
            query += " WHERE " + " AND ".join(outer_conditions)

        query += " GROUP BY si.name"

        print(f"\n\nFinal Query: \n\n{query}\n\n")
        # Execute query
        results = frappe.db.sql(query, values, as_dict=True)

        if not results:
            frappe.msgprint("No matching Sales Invoices found.")
            return

        # Group results by Customer + Import/Export
        customer_sales_invoices = {}
        invoice_list = []

        for row in results:
            invoice_list.append(row["name"])
            station = row.get("station", "")
            customer = row["customer"]
            sales_invoice_name = row["name"]
            conversion_rate = row.get("plc_conversion_rate") or 1

            # Get Import/Export type from Shipment Number
            import_export = frappe.db.get_value("Shipment Number", row.get("custom_shipment_number"), "import__export") or "Unknown"

            # Create group key by Customer + Import/Export
            customer_key = f"{customer}__{import_export}"

            if self.billing_type and self.billing_type == "Single":
                customer_key = f"{customer}__{sales_invoice_name}"

            if customer_key not in customer_sales_invoices:
                customer_sales_invoices[customer_key] = {
                    "customer": customer,
                    "import_export": import_export,
                    "sales_invoices": [],
                    "total_grand_total": 0,
                    "total_base_grand_total": 0,
                    "total_taxes_and_charges": 0,
                    "total_base_taxes_and_charges": 0,
                    "email": None,
                    "plc_conversion_rate": 0,
                    "station": None,
                    "is_peak": 0
                }

            data = customer_sales_invoices[customer_key]
            data["sales_invoices"].append(sales_invoice_name)
            data["total_grand_total"] += row["grand_total"]
            data["total_base_grand_total"] += row["base_grand_total"]
            data["total_taxes_and_charges"] += row["total_taxes_and_charges"]
            data["total_base_taxes_and_charges"] += row["base_total_taxes_and_charges"]
            data["plc_conversion_rate"] = conversion_rate
            data["station"] = station
            if row.get("item_status") == 1:
                data["is_peak"] = 1

        self.all_sales_invoices = ", ".join(invoice_list)

        # Create child table rows
        for idx, (key, data) in enumerate(customer_sales_invoices.items(), start=1):
            customer = data["customer"]
            import_export = data["import_export"]
            email = ""

            try:
                if not customer:
                    continue
                customer_doc = frappe.db.get_value("Customer", customer, ["name", "customer_primary_address"], as_dict=True)
                if customer_doc:
                    if customer_doc.customer_primary_address:
                        pri_address_doc_mail = frappe.db.get_value("Address", customer_doc.customer_primary_address, "email_id")
                        email = pri_address_doc_mail if pri_address_doc_mail else None
                    if not email:
                        linked_address = frappe.db.get_value(
                            "Dynamic Link",
                            {
                                "link_doctype": "Customer",
                                "link_name": customer_doc.name,
                                "parenttype": "Address"
                            },
                            "parent"
                        )
                        if linked_address:
                            address_doc_mail = frappe.db.get_value("Address", linked_address, "email_id")
                            email = address_doc_mail if address_doc_mail else ""
            except Exception:
                email = ""

            email = email if email else ""

            row = {
                "name1": f"{self.name}-{str(idx).zfill(3)}",
                "customer": customer,
                "importexport": import_export,
                "sales_invoices": ', '.join(data["sales_invoices"]),
                "email": email,
                "net_total_in_usd": data["total_grand_total"],
                "net_total_in_pkr": data["total_base_grand_total"],
                "sales_tax_amount_usd": data["total_taxes_and_charges"],
                "sales_tax_amount_pkr": data["total_base_taxes_and_charges"],
                "invoice_date": self.end_date,
                "station": data["station"],
                "total_invoices": len(data["sales_invoices"]),
                "is_peak": data["is_peak"]
            }
            self.append("customer_with_sales_invoice", row)

        self.total_invoices = len(results)

    
    def on_submit(self):
        if not self.customer_with_sales_invoice:
            frappe.throw("No customer sales invoices found. Please check your filters and try again.")

        if self.all_sales_invoices:
            invoices = self.all_sales_invoices.split(",")
            enqueue(
                update_sales_invoice_refs,
                queue="default",
                job_name=f"Update Sales Invoice refs for {self.name}",
                docname=self.name,
                invoices=invoices,
                ref_name=self.name,
                cancel=False
            )
            frappe.msgprint("Sales Invoice references are being updated in the background.", alert=True)

    def before_cancel(self):
        if not hasattr(self, "ignore_linked_doctypes"):
            self.ignore_linked_doctypes = []
        self.ignore_linked_doctypes.append("Sales Invoice")
        if self.all_sales_invoices:
            invoices = self.all_sales_invoices.split(",")
            enqueue(
                update_sales_invoice_refs,
                queue="default",
                job_name=f"Cleanup + Cancel {self.name}",
                docname=self.name,
                invoices=invoices,
                ref_name=None,
                cancel=True
            )
            


def update_sales_invoice_refs(docname, invoices, ref_name, cancel=False):
    """Background job to update Sales Invoice references"""
    for inv in invoices:
        inv = inv.strip()
        if not inv:
            continue

        if not frappe.db.exists("Sales Invoice", inv):
            continue

        if cancel:
            frappe.db.set_value("Sales Invoice", inv, "custom_sales_invoice_pdf_ref", None)
        else:
            frappe.db.set_value("Sales Invoice", inv, "custom_sales_invoice_pdf_ref", ref_name)


# def update_sales_invoice_refs(docname, invoices, ref_name, cancel=False):
#     """Background job to update/remove Sales Invoice references"""

#     for inv in invoices:
#         inv = inv.strip()
#         if not inv:
#             continue

#         if not frappe.db.exists("Sales Invoice", inv):
#             continue

#         if cancel:
#             frappe.db.set_value("Sales Invoice", inv, "custom_sales_invoice_pdf_ref", None)
#         else:
#             frappe.db.set_value("Sales Invoice", inv, "custom_sales_invoice_pdf_ref", ref_name)
        
    

    # if cancel:
    #     doc = frappe.get_doc("Sales Invoice PDF", docname)
    #     if doc.docstatus == 1:
    #         doc.cancel()

