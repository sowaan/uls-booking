import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe import enqueue


class SalesInvoicePDF(Document):

    # ---------------------------------------------------------------------
    # AUTONAME (UNCHANGED)
    # ---------------------------------------------------------------------
    def autoname(self):
        prefix = "AAA"

        if self.invoice_type == "Duty and Taxes Invoices":
            prefix = "D&T"
        elif self.invoice_type == "Compensation Invoices":
            prefix = "COMP"
        elif hasattr(self, "import__export") and self.import__export:
            if self.import__export == "Import":
                prefix = "IFC"
            elif self.import__export == "Export":
                prefix = "EPP"

        station_code = frappe.db.get_value(
            "Station", self.station, "station_code"
        ) if self.station else "0"

        last_name = frappe.db.get_value(
            "Sales Invoice PDF", {}, "name", order_by="creation DESC"
        )

        current_year = datetime.today().strftime("%y")
        current_month = datetime.today().strftime("%m")
        serial = "001"

        if last_name and "-" in last_name:
            parts = last_name.split("-")
            if len(parts) == 3:
                serial_part = parts[-1]
                if serial_part[:2] == current_year:
                    serial = str(int(serial_part[4:]) + 1).zfill(3)

        self.name = f"{prefix}-{station_code}-{current_year}{current_month}{serial}"

    # ---------------------------------------------------------------------
    # BEFORE SAVE (UNCHANGED LOGIC + CHILD MAP ADDED)
    # ---------------------------------------------------------------------
    def before_save(self):
        self.customer_with_sales_invoice = []
        self.total_invoices = 0
        self.all_sales_invoices = ""

        # 🔥 NEW: in-memory map (invoice → child row)
        self._invoice_child_map = {}
        customer_sales_invoices = {}
        invoice_list = []

        conditions = ["docstatus = 1"]
        conditions.append("(custom_sales_invoice_pdf_ref IS NULL OR custom_sales_invoice_pdf_ref = '')")
        values = {}

        date_field_map = {
            "Posting Date": "posting_date",
            "Shipped Date": "custom_date_shipped",
            "Import Date": "custom_import_date",
            "Arrival Date": "custom_arrival_date"
        }

        date_field = date_field_map.get(self.date_type)
        if date_field and self.start_date and self.end_date:
            conditions.append(f"{date_field} BETWEEN %(start_date)s AND %(end_date)s")
            values.update({
                "start_date": self.start_date,
                "end_date": self.end_date
            })

        if self.invoice_type:
            invoice_type_map = {
                "Freight Invoices": "custom_freight_invoices = 1",
                "Duty and Taxes Invoices": "custom_duty_and_taxes_invoice = 1",
                "Compensation Invoices": "custom_compensation_invoices = 1"
            }
            if self.invoice_type in invoice_type_map:
                conditions.append(invoice_type_map[self.invoice_type])

        if self.import__export:
            conditions.append("custom_import__export_si = %(import_export)s")
            values["import_export"] = self.import__export

        if self.customer:
            conditions.append("customer = %(customer)s")
            values["customer"] = self.customer

        if self.station:
            if self.import__export == "Import":
                conditions.append("custom_consignee_city = %(station)s")
                values["station"] = self.station
            elif self.import__export == "Export":
                conditions.append("custom_shipper_city = %(station)s")
                values["station"] = self.station

                
        where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT
                si.name,
                si.customer,
                si.grand_total,
                si.base_grand_total,
                si.total_taxes_and_charges,
                si.base_total_taxes_and_charges
            FROM `tabSales Invoice` si
            {where_clause}
            GROUP BY si.name
        """

        # frappe.msgprint(f"VALUES = {values}")
        # frappe.msgprint(f"CONDITIONS = {conditions}")


        results = frappe.db.sql(query, values, as_dict=True)

        if not results:
            self.total_invoices = 0
            frappe.msgprint("No matching Sales Invoices found.")
            return

        

        for row in results:
            invoice_list.append(row["name"])
            key = row["customer"]

            if key not in customer_sales_invoices:
                customer_sales_invoices[key] = {
                    "customer": row["customer"],
                    "sales_invoices": [],
                    "total_grand_total": 0,
                    "total_base_grand_total": 0,
                    "total_taxes_and_charges": 0,
                    "total_base_taxes_and_charges": 0,
                }

            data = customer_sales_invoices[key]
            data["sales_invoices"].append(row["name"])
            data["total_grand_total"] += row["grand_total"]
            data["total_base_grand_total"] += row["base_grand_total"]
            data["total_taxes_and_charges"] += row["total_taxes_and_charges"]
            data["total_base_taxes_and_charges"] += row["base_total_taxes_and_charges"]

        self.all_sales_invoices = ", ".join(invoice_list)

        # -------------------------------------------------
        # CREATE CHILD ROWS (UNCHANGED + MAP ADDED)
        # -------------------------------------------------
        for idx, (customer, data) in enumerate(customer_sales_invoices.items(), start=1):
            row = {
                "name1": f"{self.name}-{str(idx).zfill(3)}",
                "customer": customer,
                "sales_invoices": ", ".join(data["sales_invoices"]),
                "net_total_in_usd": data["total_grand_total"],
                "net_total_in_pkr": data["total_base_grand_total"],
                "sales_tax_amount_usd": data["total_taxes_and_charges"],
                "sales_tax_amount_pkr": data["total_base_taxes_and_charges"],
                "invoice_date": self.end_date,
                "total_invoices": len(data["sales_invoices"]),
            }

            child = self.append("customer_with_sales_invoice", row)

            # 🔥 MAP INVOICES → CHILD ROW
            for inv in data["sales_invoices"]:
                self._invoice_child_map[inv] = child.name

        self.total_invoices = len(results)

    # ---------------------------------------------------------------------
    # ON SUBMIT (EXTENDED – NO LOGIC REMOVED)
    # ---------------------------------------------------------------------
    def on_submit(self):
        if not self.customer_with_sales_invoice:
            frappe.throw("No customer sales invoices found.")

        # 🔥 BUILD invoice → child map HERE (SAFE)
        invoice_child_map = {}

        for row in self.customer_with_sales_invoice:
            if not row.sales_invoices:
                continue

            invoices = row.sales_invoices.split(",")
            for inv in invoices:
                invoice_child_map[inv.strip()] = row.name

        if self.all_sales_invoices:
            invoices = self.all_sales_invoices.split(",")

            enqueue(
                update_sales_invoice_refs,
                queue="default",
                job_name=f"Update Sales Invoice refs for {self.name}",
                docname=self.name,
                invoices=invoices,
                ref_name=self.name,
                invoice_child_map=invoice_child_map,  # ✅ ALWAYS EXISTS
                cancel=False
            )

    # ---------------------------------------------------------------------
    # ON CANCEL (CLEANUP)
    # ---------------------------------------------------------------------
    def before_cancel(self):
        invoices = self.all_sales_invoices.split(",") if self.all_sales_invoices else []

        enqueue(
            update_sales_invoice_refs,
            queue="default",
            job_name=f"Cleanup Sales Invoice refs for {self.name}",
            docname=self.name,
            invoices=invoices,
            ref_name=None,
            cancel=True
        )


# -------------------------------------------------------------------------
# BACKGROUND JOB (UPDATED – SAFE)
# -------------------------------------------------------------------------
def update_sales_invoice_refs(
    docname,
    invoices,
    ref_name,
    invoice_child_map=None,
    cancel=False
):
    invoice_child_map = invoice_child_map or {}

    for inv in invoices:
        inv = inv.strip()
        if not inv or not frappe.db.exists("Sales Invoice", inv):
            continue

        if cancel:
            values = {
                "custom_sales_invoice_pdf_ref": None,
                "custom_sales_invoice_pdf_child_ref": None
            }
        else:
            values = {
                "custom_sales_invoice_pdf_ref": ref_name
            }
            if inv in invoice_child_map:
                values["custom_sales_invoice_pdf_child_ref"] = invoice_child_map[inv]

        frappe.db.set_value(
            "Sales Invoice",
            inv,
            values,
            update_modified=False
        )
