import frappe
import unittest
from unittest.mock import patch, MagicMock, call 
from copy import deepcopy 

# Import the functions to be tested
from one_fm.one_fm.page.roster.roster import get_employees_for_roster_view
from one_fm.api.mobile.roster import get_roster_view as get_roster_view_mobile, get_current_user_details as get_current_user_details_mobile_func_rename, get_assigned_projects, get_assigned_sites, get_assigned_shifts

# Dummy DocType class for query builder mocking if it becomes necessary
class MockDocType:
    def __init__(self, name):
        self.name = name
        # Mock attributes that might be accessed by the query builder
        # For example, if the code does `Employee.status`, `status` needs to be a mock.
        # This needs to be comprehensive based on how `build_employee_filters` and `build_employee_schedule_filters` use the DocType object.
        # For simplicity in this example, I'm keeping it minimal. Add more as needed.
        for field_name in ["status", "shift_working", "attendance_by_timesheet", "employee_id", 
                           "employee_name", "custom_is_reliever", "project", "site", "shift", 
                           "department", "custom_operations_role_allocation", "designation", 
                           "relieving_date", "date", "employee"]:
            setattr(self, field_name, MagicMock(name=field_name))


class TestRosterLogic(unittest.TestCase):
    def setUp(self):
        # Common setup for tests, if any
        self.mock_employee_doctype_instance = MockDocType("Employee")
        self.mock_employee_schedule_doctype_instance = MockDocType("Employee Schedule")

        # Define common test data
        self.employee_john_doe = {"name": "EMP001", "employee_name": "John Doe"}
        self.employee_jane_smith = {"name": "EMP002", "employee_name": "Jane Smith"}
        self.employee_alice_brown = {"name": "EMP003", "employee_name": "Alice Brown"} 

        self.schedule_jane_smith = {"name": "EMP002", "employee_name": "Jane Smith", "date": "2024-01-15"}
        self.schedule_alice_brown = {"name": "EMP003", "employee_name": "Alice Brown", "date": "2024-01-16"}

        self.start_date = "2024-01-01"
        self.end_date = "2024-01-31"


    def tearDown(self):
        # Clean up after each test
        # frappe.db.rollback() # Important if real DB operations were made
        pass

    @patch('one_fm.one_fm.page.roster.roster.DocType')
    @patch('frappe.db.sql')
    def test_get_employees_search_john_doe_exists_in_employee_only(self, mock_sql, mock_doctype_constructor):
        # John Doe: Exists in Employee, not in EmployeeSchedule
        
        def doctype_side_effect(doctype_name, *args, **kwargs): # Added *args, **kwargs
            if doctype_name == "Employee":
                return self.mock_employee_doctype_instance
            elif doctype_name == "Employee Schedule":
                return self.mock_employee_schedule_doctype_instance
            raise ValueError(f"Unexpected DocType: {doctype_name}")
        mock_doctype_constructor.side_effect = doctype_side_effect
        
        # This test focuses on the case where 'John Doe' is searched.
        # The modified get_employees_for_roster_view always does a UNION.
        # So, the mock_sql should return what the UNION query for "John Doe" would return.
        # If John Doe is only in Employee table, the UNION (distinct) will return him once.
        mock_sql.return_value = [self.employee_john_doe]

        result = get_employees_for_roster_view(
            start_date=self.start_date, end_date=self.end_date,
            employee_search_name="John Doe"
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "EMP001")
        self.assertEqual(result[0]["employee_name"], "John Doe")
        mock_sql.assert_called_once() 


    @patch('one_fm.one_fm.page.roster.roster.DocType')
    @patch('frappe.db.sql')
    def test_get_employees_search_jane_smith_exists_in_both(self, mock_sql, mock_doctype_constructor):
        # Jane Smith: Exists in Employee and EmployeeSchedule
        def doctype_side_effect(doctype_name, *args, **kwargs):
            if doctype_name == "Employee": return self.mock_employee_doctype_instance
            elif doctype_name == "Employee Schedule": return self.mock_employee_schedule_doctype_instance
            raise ValueError(f"Unexpected DocType: {doctype_name}")
        mock_doctype_constructor.side_effect = doctype_side_effect

        mock_sql.return_value = [self.employee_jane_smith] 

        result = get_employees_for_roster_view(
            start_date=self.start_date, end_date=self.end_date,
            employee_search_name="Jane Smith"
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "EMP002")
        self.assertEqual(result[0]["employee_name"], "Jane Smith")
        mock_sql.assert_called_once()


    @patch('one_fm.one_fm.page.roster.roster.DocType')
    @patch('frappe.db.sql')
    def test_get_employees_no_search_jane_and_alice(self, mock_sql, mock_doctype_constructor):
        # No specific employee search.
        # Jane Smith (EMP002) could be in Employee and EmployeeSchedule.
        # Alice Brown (EMP003) could be in EmployeeSchedule (and possibly Employee for data integrity).
        # The UNION query should return both, distinctly.
        def doctype_side_effect(doctype_name, *args, **kwargs):
            if doctype_name == "Employee": return self.mock_employee_doctype_instance
            elif doctype_name == "Employee Schedule": return self.mock_employee_schedule_doctype_instance
            raise ValueError(f"Unexpected DocType: {doctype_name}")
        mock_doctype_constructor.side_effect = doctype_side_effect

        mock_sql.return_value = [
            self.employee_jane_smith, 
            self.employee_alice_brown 
        ]

        result = get_employees_for_roster_view(
            start_date=self.start_date, end_date=self.end_date
        )
        
        self.assertEqual(len(result), 2)
        result_names = {r["name"] for r in result}
        self.assertIn("EMP002", result_names) 
        self.assertIn("EMP003", result_names) 
        mock_sql.assert_called_once()

    @patch('one_fm.api.mobile.roster.get_current_user_details') # Target the function where it's defined
    @patch('one_fm.api.mobile.roster.get_assigned_projects') 
    @patch('frappe.get_all')
    def test_get_roster_view_mobile_grouping(self, mock_get_all, mock_get_assigned_projects_func, mock_get_current_user_details_func):
        # Setup mocks for mobile get_roster_view
        mock_user_employee_obj = MagicMock()
        mock_user_employee_obj.name = "Test User Employee" # Ensure it has a 'name' attribute
        mock_get_current_user_details_func.return_value = (
            "test_user", 
            ["Operations Manager"], 
            mock_user_employee_obj 
        )
        
        mock_project_obj = MagicMock()
        mock_project_obj.name = "ProjectA"
        mock_get_assigned_projects_func.return_value = [mock_project_obj]

        mock_schedule_data = [
            {"employee": "EmpB", "employee_name": "Employee B", "date": "2024-01-15", "operations_role": "RoleY", "post_abbrv": "P2", "employee_availability": "Working", "shift": "S2"},
            {"employee": "EmpA", "employee_name": "Employee A", "date": "2024-01-15", "operations_role": "RoleX", "post_abbrv": "P1", "employee_availability": "Working", "shift": "S1"},
            {"employee": "EmpC", "employee_name": "Employee C", "date": "2024-01-15", "operations_role": "RoleX", "post_abbrv": "P1", "employee_availability": "Working", "shift": "S1"},
        ]
        # The actual code now sorts, so the mock should return data as if it was sorted for groupby to work correctly
        # Or, we can trust that frappe.get_all with order_by works and provide sorted data to reflect its output.
        # The test is more about whether our Python code correctly processes the (expectedly sorted) data.
        # For itertools.groupby to work correctly, the input list must be sorted by the group key.
        # The fix added `order_by` to `frappe.get_all`. So, `mock_get_all` should return sorted data.
        sorted_mock_schedule_data = sorted(mock_schedule_data, key=lambda x: (x.get('post_abbrv',''), x.get('operations_role','')))
        mock_get_all.return_value = sorted_mock_schedule_data


        result = get_roster_view_mobile(date="2024-01-15", project="ProjectA")

        self.assertEqual(len(result), 2) 
        
        group_p1_rolex = next((g for g in result if g["post"] == "P1" and g.get("operations_role") == "RoleX"), None)
        group_p2_roley = next((g for g in result if g["post"] == "P2" and g.get("operations_role") == "RoleY"), None)

        self.assertIsNotNone(group_p1_rolex, "Group P1/RoleX not found")
        if group_p1_rolex: # Check if found before accessing keys
            self.assertEqual(group_p1_rolex["count"], 2)
            employee_names_p1_rolex = {e["employee_name"] for e in group_p1_rolex["employees"]}
            self.assertIn("Employee A", employee_names_p1_rolex)
            self.assertIn("Employee C", employee_names_p1_rolex)

        self.assertIsNotNone(group_p2_roley, "Group P2/RoleY not found")
        if group_p2_roley: # Check if found
            self.assertEqual(group_p2_roley["count"], 1)
            self.assertEqual(group_p2_roley["employees"][0]["employee_name"], "Employee B")
        
        mock_get_all.assert_called_once_with(
            "Employee Schedule", 
            {'date': '2024-01-15', 'project': ('in', ['ProjectA'])}, 
            ["employee", "employee_name", "date", "operations_role", "post_abbrv", "employee_availability", "shift"],
            order_by="post_abbrv, operations_role"
        )

if __name__ == '__main__':
    unittest.main()
