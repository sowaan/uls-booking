# Copyright (c) 2024, Sowaan and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ShipmentNumberFileReference(Document):
    # def before_save(self):
    #     if self.shipment_numbers:
    #         # Split the string by commas and count the number of elements
    #         shipment_numbers_list = self.shipment_numbers.split(', ')
    #         self.custom_total_shipment_numbers = len(shipment_numbers_list)  # Assuming you want to store the count in a field named 'shipment_count'
    #     else:
    #         self.custom_total_shipment_numbers = 0  # Set to 0 if there are no shipment numbers
    pass