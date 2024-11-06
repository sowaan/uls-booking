import frappe
from datetime import datetime



def execute():
    R200000 = frappe.get_all("R200000",fields =["name","date_shipped"])
    def convert_date(date_input):
            
            try:
                date_object = datetime.strptime(date_input, "%d%b%y")  # e.g., '13JUL20'
                return date_object.strftime("%Y-%m-%d")
            except ValueError:
                pass  # If it fails, try the next format
            try:
                # This will raise a ValueError if the format doesn't match
                datetime.strptime(date_input, "%Y-%m-%d")
                return date_input  # If it matches, return the original input
            except ValueError:
                pass  # If it fails, continue with parsing

            # Try parsing as dmy format without separators
            try:
                date_object = datetime.strptime(date_input, "%d%m%Y")  # e.g., '31102024'
                return date_object.strftime("%Y-%m-%d")
            except ValueError:
                pass  # If it fails, try the next format

            # Try parsing as dmy with month abbreviation
            try:
                date_object = datetime.strptime(date_input, "%d%b%Y")  # e.g., '31OCT2024'
                return date_object.strftime("%Y-%m-%d")
            except ValueError:
                pass  # If it fails, try the next format

            # Try parsing as dmy with hyphens
            try:
                date_object = datetime.strptime(date_input, "%d-%m-%Y")  # e.g., '31-10-2024'
                return date_object.strftime("%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Date format for '{date_input}' is invalid.")
            
            
    for record in R200000:
        
        if record.date_shipped:
            record.date_shipped = convert_date(record.date_shipped)
            frappe.db.set_value("R200000",record.name,"shipped_date",record.date_shipped)
    

            
