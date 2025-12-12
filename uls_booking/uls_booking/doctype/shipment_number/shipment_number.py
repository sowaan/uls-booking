# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document # type: ignore


class ShipmentNumber(Document):
    def autoname(self):
        # Ensure required field exists
        if not self.shipment_number:
            frappe.throw("Shipment Number must be set before saving.")

        # Generate incremental series per shipment_number prefix
        # Example result: ABC-00001
        series_key = f"{self.shipment_number}-"

        new_name = frappe.model.naming.make_autoname(series_key + ".#####")

        self.name = new_name
