import frappe
from frappe.model.document import Document
from datetime import datetime

class SalesInvoicePDF(Document):
    def autoname(self):
        prefix = "AAA"
        station = "0"
        serial = '00001'

        if hasattr(self, 'import__export') and self.import__export:
            if self.import__export == "Import":
                prefix = "IFC"
            elif self.import__export == "Export":
                prefix = "EPP"

        if hasattr(self, 'station') and self.station:
            station_map = {
                "karachi": "1",
                "lahore": "2",
                "islamabad": "3",
                "sialkot": "4",
                "faisalabad": "5",
                "peshawar": "6"
            }
            station = station_map.get(self.station.lower(), "0")

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
                            serial = str(int(serial) + 1).zfill(5)

        self.name = f"{prefix}-{station}-{current_year}{current_month}{serial}"


    def before_save(self):
        self.customer_with_sales_invoice = []
        values = {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "station": self.station,
            "icris_number": self.icris_number,
            "billing_type": self.billing_type,
        }

        if self.customer:
            values["customer"] = self.customer

        query = """
            SELECT 
                si.name,
                si.custom_shipment_number,
                si.customer,
                si.grand_total,
                si.base_grand_total,
                si.total_taxes_and_charges,
                si.base_total_taxes_and_charges,
                si.plc_conversion_rate
            FROM 
                `tabSales Invoice` as si
            LEFT JOIN
                `tabShipment Number` as sn ON si.custom_shipment_number = sn.name
            LEFT JOIN
                `tabCustomer` as c ON si.customer = c.name
            WHERE
                sn.date_shipped BETWEEN %(start_date)s AND %(end_date)s
                AND si.docstatus = 1
                AND si.custom_freight_invoices = 1
        """

        conditions = []

        if "customer" in values:
            query += " AND si.customer = %(customer)s"
        if self.station:
            conditions.append("sn.station = %(station)s")
        if self.icris_number:
            conditions.append("sn.icris_number = %(icris_number)s")
        if self.billing_type:
            conditions.append("c.custom_billing_type = %(billing_type)s")
        if self.import__export:
            values["import__export"] = self.import__export
            conditions.append("sn.import__export = %(import__export)s")

        if conditions:
            query += " AND " + " AND ".join(conditions)
            
        results = frappe.db.sql(query, values, as_dict=True)
        customer_sales_invoices = {}

        for row in results:
            customer = row["customer"]
            sales_invoice_name = row["name"]
            conversion_rate = row["plc_conversion_rate"]
            
            if customer not in customer_sales_invoices:
                customer_sales_invoices[customer] = {
                    "sales_invoices": [],
                    "total_grand_total": 0,
                    "total_base_grand_total": 0,
                    "total_taxes_and_charges": 0,
                    "total_base_taxes_and_charges": 0,
                    "email": None,
                    "plc_conversion_rate": 0
                }

            customer_sales_invoices[customer]["sales_invoices"].append(sales_invoice_name)
            customer_sales_invoices[customer]["total_grand_total"] += row["grand_total"]
            customer_sales_invoices[customer]["total_base_grand_total"] += row["base_grand_total"]
            customer_sales_invoices[customer]["total_taxes_and_charges"] += row["total_taxes_and_charges"]
            customer_sales_invoices[customer]["total_base_taxes_and_charges"] += row["base_total_taxes_and_charges"]
            customer_sales_invoices[customer]["plc_conversion_rate"] = conversion_rate

        for customer, data in customer_sales_invoices.items():
            email = None
            customer_doc = frappe.get_doc("Customer", customer)
            
            if customer_doc.customer_primary_address:
                address_doc = frappe.get_doc("Address", customer_doc.customer_primary_address)
                if hasattr(address_doc, "email_id"):
                    email = address_doc.email_id

            sales_invoices = ', '.join(data["sales_invoices"]) 
            email = email if email else "" 
            
            row = {
                "customer": customer,
                "sales_invoices": sales_invoices,
                "email": email,
                "net_total_in_usd": data["total_grand_total"],
                "net_total_in_pkr": data["total_grand_total"] * data["plc_conversion_rate"],
                "sales_tax_amount_usd": data["total_taxes_and_charges"],
                "sales_tax_amount_pkr": data["total_taxes_and_charges"] * data["plc_conversion_rate"],
                "invoice_date": self.end_date,
                "station": self.station,
            }
            self.append("customer_with_sales_invoice", row)

        self.total_invoices = len(results)

    def before_submit(self):
        for customer in self.customer_with_sales_invoice:
            new_doc = frappe.new_doc("Customer Shipment Invoice")
            new_doc.sales_invoice_pdf = self.name
            new_doc.customer = customer.customer
            new_doc.sales_invoices = customer.sales_invoices
            new_doc.start_date = self.start_date
            new_doc.end_date = self.end_date
            new_doc.billing_type = self.billing_type
            new_doc.icris_number = self.icris_number
            new_doc.station = self.station
            new_doc.email = customer.email
            new_doc.insert()
            new_doc.save()

            customer.invoice = new_doc.name
