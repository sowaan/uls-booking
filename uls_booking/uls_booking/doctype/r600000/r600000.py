# Copyright (c) 2024, fariz.khanzada@sowaan.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
class R600000(Document):
    def before_save(self):
        if self.package_length and self.package_width and self.package_height :
            self.custom_dws_dim = (float(self.package_length) * float(self.package_width) * float(self.package_height)) / 5000
            time_str = f"{self.dws_hours:02}:{self.dws_minutes:02}:{self.dws_seconds:02}"
            self.time_of_dws = time_str
    # def before_save(self):
    #     # Define helper functions for division outside of the if block
    #     def safe_divide_10(value):
    #         try:
    #             return float(value) / 10
    #         except (ValueError, TypeError):
    #             return 0.0  # Return a default value in case of error

    #     def safe_divide_100(value):
    #         try:
    #             return float(value) / 100
    #         except (ValueError, TypeError):
    #             return 0.0  # Return a default value in case of error

    #     # Check the condition and process accordingly
    #     if self.check == 0:
    #         # Apply the helper functions to each relevant attribute
            
    #         self.package_weight = safe_divide_10(self.package_weight)
    #         self.expanded_package_weight = safe_divide_10(self.expanded_package_weight)
    #         self.custom_pkgkeyrawlen = safe_divide_100(self.custom_pkgkeyrawlen)
    #         self.custom_pkgkeyrawwid = safe_divide_100(self.custom_pkgkeyrawwid)
    #         self.custom_pkgkeyrawhig = safe_divide_100(self.custom_pkgkeyrawhig)
    #         self.custom_pkgbilrawlen = safe_divide_10(self.custom_pkgbilrawlen)
    #         self.custom_pkgbilrawwid = safe_divide_10(self.custom_pkgbilrawwid)
    #         self.custom_pkgbilrawhig = safe_divide_10(self.custom_pkgbilrawhig)
            
    #         # Update the check attribute
    #         self.check = 1