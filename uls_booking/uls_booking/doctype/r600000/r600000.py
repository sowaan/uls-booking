# Copyright (c) 2024, fariz.khanzada@sowaan.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
class R600000(Document):
    pass
    # def before_save(self):
    #     if not self.name:
    #         if self.package_length and self.package_width and self.package_height :
    #             self.package_length = float(self.package_length) / 10
    #             self.package_width = float(self.package_width) / 10
    #             self.package_height = float(self.package_height) / 10
    #             self.dws_dim = (float(self.package_length) * float(self.package_width) * float(self.package_height)) / 5000
    #             time_str = f"{self.dws_hours:02}:{self.dws_minutes:02}:{self.dws_seconds:02}"

    #             self.time_of_dws = time_str
    #             if self.dws_actual_weight:
    #                 self.dws_actual_weight = float(self.dws_actual_weight) / 10
   