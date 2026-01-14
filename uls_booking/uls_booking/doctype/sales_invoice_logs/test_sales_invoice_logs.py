# Copyright (c) 2025, Sowaan and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

import unittest
from uls_booking.uls_booking.api.sales_invoice_script import generate_single_invoice


class TestSalesInvoiceLogs(FrappeTestCase):

    def setUp(self):
        frappe.db.rollback()

    def tearDown(self):
        frappe.db.rollback()

    # --------------------------------------------------
    # Helper
    # --------------------------------------------------
    def create_log(self, shipment, date, invoice="SINV-TEST", status="Created"):
        frappe.get_doc({
            "doctype": "Sales Invoice Logs",
            "shipment_number": shipment,
            "manifest_input_date": date,
            "sales_invoice": invoice,
            "sales_invoice_status": status,
            "logs": "Test log"
        }).insert(ignore_permissions=True)

    # --------------------------------------------------
    # TC-01: New shipment → new invoice
    # --------------------------------------------------
    def test_new_shipment_new_date(self):
        result = generate_single_invoice(
            shipment_number="SHP-TEST-001",
            manifest_input_date="2025-01-10",
            sales_invoice_definition="TEST-DEF",
            end_date="2025-01-31",
            login_username="Administrator"
        )

        self.assertEqual(result["sales_invoice_status"], "Created")

    # --------------------------------------------------
    # TC-02: Same shipment + same date → existing
    # --------------------------------------------------
    def test_existing_same_date(self):
        self.create_log("SHP-TEST-002", "2025-01-10", "SINV-001")

        result = generate_single_invoice(
            shipment_number="SHP-TEST-002",
            manifest_input_date="2025-01-10"
        )

        self.assertEqual(result["sales_invoice_status"], "Already Created")
        self.assertEqual(result["sales_invoice_name"], "SINV-001")

    # --------------------------------------------------
    # TC-03: Same shipment + different date → duplicate
    # --------------------------------------------------
    def test_existing_different_date_duplicate(self):
        self.create_log("SHP-TEST-003", "2025-01-10", "SINV-001")

        result = generate_single_invoice(
            shipment_number="SHP-TEST-003",
            manifest_input_date="2025-01-15"
        )

        self.assertEqual(
            result["sales_invoice_status"],
            "Created (Duplicate Shipment)"
        )

    # --------------------------------------------------
    # TC-04: Missing manifest date → failed
    # --------------------------------------------------
    def test_missing_manifest_date(self):
        result = generate_single_invoice(
            shipment_number="SHP-TEST-004"
        )

        self.assertEqual(result["sales_invoice_status"], "Failed")

    # --------------------------------------------------
    # TC-05: Multiple previous dates → duplicate message
    # --------------------------------------------------
    def test_multiple_previous_manifest_dates(self):
        self.create_log("SHP-TEST-005", "2025-01-01")
        self.create_log("SHP-TEST-005", "2025-01-05")

        result = generate_single_invoice(
            shipment_number="SHP-TEST-005",
            manifest_input_date="2025-01-10"
        )

        self.assertIn("2025-01-01", result["logs"])
        self.assertIn("2025-01-05", result["logs"])

    # --------------------------------------------------
    # TC-06: Log created with manifest_input_date
    # --------------------------------------------------
    def test_log_created_with_manifest_date(self):
        shipment = "SHP-TEST-006"
        date = "2025-01-20"

        generate_single_invoice(
            shipment_number=shipment,
            manifest_input_date=date
        )

        log = frappe.db.get_value(
            "Sales Invoice Logs",
            {"shipment_number": shipment, "manifest_input_date": date},
            ["sales_invoice_status"],
            as_dict=True
        )

        self.assertIsNotNone(log)
