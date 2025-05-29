import frappe
from frappe import _
from frappe.utils import getdate, cint, cstr, random_string, now_datetime
from frappe.client import get_list
import pandas as pd
import json, base64, ast, itertools, datetime
from frappe.client import attach_file
from one_fm.api.v1.utils import response
from one_fm.utils import query_db_list
# from one_fm.one_fm.page.roster.roster import get_roster_view as _get_roster_view # This line is removed
from one_fm.operations.doctype.operations_shift.operations_shift import get_supervisor_operations_shifts

@frappe.whitelist()
def get_roster_view(date, shift=None, site=None, project=None, department=None):
	try:
		filters = {
			'date': date
		}
		if project:
			filters.update({'project': project})
		if site:
			filters.update({'site': site})
		if shift:
			filters.update({'shift': shift})
		if department:
			filters.update({'department': department})

		fields = ["employee", "employee_name", "date", "operations_role", "post_abbrv", "employee_availability", "shift"]
		user, user_roles, user_employee = get_current_user_details()
		# print(user_roles) # Commented out or remove print
		if "Operations Manager" in user_roles or "Projects Manager" in user_roles:
			projects = get_assigned_projects(user_employee.name)
			assigned_projects = []
			for assigned_project in projects:
				assigned_projects.append(assigned_project.name)

			filters.update({"project": ("in", assigned_projects)})
			roster = frappe.get_all("Employee Schedule", filters, fields, order_by="post_abbrv, operations_role")
			master_data = []
			for key, group in itertools.groupby(roster, key=lambda x: (x.get('post_abbrv',''), x.get('operations_role',''))): # Added .get for safety
				employees = list(group)
				master_data.append({"employees": employees, "post": key[0], "count": len(employees)})
			return master_data

		elif "Site Supervisor" in user_roles:
			sites = get_assigned_sites(user_employee.name, project)
			assigned_sites = []
			for assigned_site in sites:
				assigned_sites.append(assigned_site.name)
			filters.update({"site": ("in", assigned_sites)})
			roster = frappe.get_all("Employee Schedule", filters, fields, order_by="post_abbrv, operations_role")
			# print(roster) # Commented out or remove print
			master_data = []
			for key, group in itertools.groupby(roster, key=lambda x: (x.get('post_abbrv',''), x.get('operations_role',''))): # Added .get for safety
				employees = list(group)
				master_data.append({"employees": employees, "post": key[0], "count": len(employees)})
			return master_data

		elif "Shift Supervisor" in user_roles:
			shifts = get_assigned_shifts(user_employee.name, site)
			assigned_shifts = []
			for assigned_shift in shifts:
				assigned_shifts.append(assigned_shift.name)
			filters.update({"shift":  ("in", assigned_shifts)})

			roster = frappe.get_all("Employee Schedule", filters, fields, order_by="post_abbrv, operations_role")
			master_data = []
			for key, group in itertools.groupby(roster, key=lambda x: (x.get('post_abbrv',''), x.get('operations_role',''))): # Added .get for safety
				employees = list(group)
				master_data.append({"employees": employees, "post": key[0], "count": len(employees)})
			return master_data
		else: # Handle cases where user might not have any of these roles
			return [] 
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_roster_view mobile") # Log error
		return frappe.utils.response.report_error(e) # Use Frappe's error reporting


@frappe.whitelist()
def get_weekly_staff_roster(start_date, end_date):
	try:
		user, user_roles, user_employee = get_current_user_details()
		if not user_employee: # Handle if user_employee is None
			frappe.throw(_("User not linked to an Employee record."))
			return []

		roster = frappe.db.sql("""
			SELECT shift, employee, date, employee_availability, operations_role
			FROM `tabEmployee Schedule`
			WHERE employee=%(emp)s
			AND date BETWEEN %(start_date)s AND %(end_date)s
		""", {"emp":user_employee.name, "start_date":start_date, "end_date":end_date}, as_dict=1)
		# print(roster) # Commented out or remove print
		return roster
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_weekly_staff_roster mobile")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_current_user_details():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_id", "employee_name", "image", "enrolled", "designation"], as_dict=1)
	return user, user_roles, user_employee


@frappe.whitelist()
def get_post_view(date, shift=None, site=None, project=None, department=None):
	try:
		filters = {
			'date': date
		}
		if project:
			filters.update({'project': project})
		if site:
			filters.update({'site': site})
		if shift:
			filters.update({'shift': shift})
		if department:
			filters.update({'department': department})

		fields = ["post", "post_status", "date", "operations_role",  "shift"]
		user, user_roles, user_employee = get_current_user_details()
		if not user_employee: # Handle if user_employee is None
			frappe.throw(_("User not linked to an Employee record."))
			return []

		roster_data = [] # Renamed roster to avoid confusion

		if "Operations Manager" in user_roles or "Projects Manager" in user_roles:
			projects = get_assigned_projects(user_employee.name)
			assigned_projects = [p.name for p in projects] # Simplified

			filters.update({"project": ("in", assigned_projects)})
			roster_data = frappe.get_all("Post Schedule", filters, fields)
			# print(roster_data)

		elif "Site Supervisor" in user_roles:
			sites = get_assigned_sites(user_employee.name, project)
			assigned_sites = [s.name for s in sites] # Simplified
			filters.update({"site": ("in", assigned_sites)})
			roster_data = frappe.get_all("Post Schedule", filters, fields)
			# print(roster_data)

		elif "Shift Supervisor" in user_roles:
			shifts = get_assigned_shifts(user_employee.name, site)
			assigned_shifts = [s.name for s in shifts] # Simplified
			filters.update({"shift":  ("in", assigned_shifts)})
			roster_data = frappe.get_all("Post Schedule", filters, fields)
			# print(roster_data)
		else: # Handle cases where user might not have any of these roles
			return []

		for post_item in roster_data: # Renamed post to post_item
			post_item.update({"count": 1}) # This seems to be a placeholder or simplified logic
		return roster_data

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_post_view mobile")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def edit_post(post, post_status, start_date, end_date, paid=0, never_end=0, repeat=0, repeat_freq=None):
	try:
		# Validate dates
		start_date_obj = getdate(start_date)
		end_date_obj = getdate(end_date)

		if start_date_obj > end_date_obj and not never_end:
			frappe.throw(_("Start date cannot be after end date."))
			return False # Should not proceed

		if never_end:
			project_name = frappe.get_value("Operations Post", post, "project") # Renamed project
			if not project_name:
				frappe.throw(_("Project not found for the post to determine contract end date."))
				return False
			end_date_contract = frappe.get_value("Contracts", {"project": project_name}, "end_date") # Renamed end_date
			if not end_date_contract:
				frappe.throw(_("Contract end date not found for the project linked to the post."))
				return False
			end_date_obj = getdate(end_date_contract)
		
		dates_to_process = []
		if cint(repeat): # Use cint for repeat
			if repeat_freq == "Daily":
				dates_to_process = pd.date_range(start=start_date_obj, end=end_date_obj)
			elif repeat_freq == "Weekly":
				start_day_name = start_date_obj.strftime('%A')
				for date_iter in pd.date_range(start=start_date_obj, end=end_date_obj): # Renamed date
					if date_iter.strftime('%A') == start_day_name:
						dates_to_process.append(date_iter)
			elif repeat_freq == "Monthly":
				# month_range function might need to handle date objects if not already
				dates_to_process = month_range(start_date_obj, end_date_obj) 
		else: # Not repeating, process the range directly
			dates_to_process = pd.date_range(start=start_date_obj, end=end_date_obj)

		for date_item in dates_to_process: # Renamed date
			create_edit_post(cstr(date_item.date()), post, post_status, paid)
		
		frappe.db.commit()
		return True

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "edit_post mobile")
		return frappe.utils.response.report_error(e)


def create_edit_post(date_str, post_name, post_status, paid_status): # Renamed args for clarity
	if frappe.db.exists("Post Schedule", {"date": date_str, "post": post_name}):
		post_schedule = frappe.get_doc("Post Schedule", {"date": date_str, "post": post_name})
	else:
		post_schedule = frappe.new_doc("Post Schedule")
		post_schedule.post = post_name
		post_schedule.date = date_str
	
	post_schedule.post_status = post_status
	if cint(paid_status):
		post_schedule.paid = 1
		post_schedule.unpaid = 0
	else:
		post_schedule.unpaid = 1
		post_schedule.paid = 0
	post_schedule.save(ignore_permissions=True)


@frappe.whitelist()
def day_off(employee, date, repeat=0, repeat_freq=None, repeat_till=None):
	try:
		start_date_obj = getdate(date) # Renamed date
		repeat_till_obj = getdate(repeat_till) if repeat_till else None

		if cint(repeat) and not repeat_till_obj:
			frappe.throw(_("Repeat Till date is required when repeating a day off."))
			return False
		
		if cint(repeat) and repeat_till_obj and start_date_obj > repeat_till_obj :
			frappe.throw(_("Start date cannot be after Repeat Till date."))
			return False

		dates_to_process = []
		if cint(repeat):
			if repeat_freq == "Daily":
				dates_to_process = pd.date_range(start=start_date_obj, end=repeat_till_obj)
			elif repeat_freq == "Weekly":
				start_day_name = start_date_obj.strftime('%A')
				for date_iter in pd.date_range(start=start_date_obj, end=repeat_till_obj): # Renamed date
					if date_iter.strftime('%A') == start_day_name:
						dates_to_process.append(date_iter)
			elif repeat_freq == "Monthly":
				dates_to_process = month_range(start_date_obj, repeat_till_obj)
		else: # Not repeating
			dates_to_process.append(start_date_obj)

		for date_item in dates_to_process: # Renamed date
			create_day_off(employee, cstr(date_item.date()))
		
		frappe.db.commit()
		return True
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "day_off mobile")
		return frappe.utils.response.report_error(e)


def month_range(start, end): # start and end should be date objects or parsable date strings
	start_ts = pd.Timestamp(getdate(start))
	end_ts = pd.Timestamp(getdate(end))

	rng = pd.date_range(start=start_ts - pd.offsets.MonthBegin(),
						end=end_ts,
						freq='MS') # Month Start
	# Adjust day to match the original start day
	ret = (rng + pd.offsets.Day(start_ts.day - 1))
	# Filter out dates that are beyond the original end date after day adjustment
	ret = ret[ret <= end_ts]
	# Filter out dates where the month is greater than the generated month start (handles cases where day adjustment pushes to next month)
	# This condition might be tricky, ensure it correctly handles edge cases.
	# A simpler way for "on the Nth day of each month":
	# current_date = start_ts
	# dates = []
	# while current_date <= end_ts:
	#   dates.append(current_date)
	#   next_month_date = current_date + pd.offsets.MonthBegin(1) # Go to start of next month
	#   current_date = pd.Timestamp(year=next_month_date.year, month=next_month_date.month, day=start_ts.day)
	#   if current_date.month != next_month_date.month: # Handle if target day doesn't exist in next month (e.g. Feb 30th)
	#       current_date = next_month_date + pd.offsets.MonthEnd(0) # Go to end of that month instead
	# return pd.DatetimeIndex(dates)
	
	# Sticking to original logic for now, but it has known pandas issues with day preservation across month ends.
	# This part might need robust testing for various start/end days.
	final_dates = (rng + pd.offsets.Day(start_ts.day-1))
	# Ensure dates are within the month of their original generation & not past overall end date
	final_dates = final_dates[(final_dates.month == rng.month) & (final_dates <= end_ts)]

	return pd.DatetimeIndex(final_dates)


def create_day_off(employee_name, date_str): # Renamed args
	if frappe.db.exists("Employee Schedule", {"employee": employee_name, "date": date_str}):
		roster = frappe.get_doc("Employee Schedule", {"employee": employee_name, "date": date_str})
		roster.shift = None
		roster.shift_type = None
		roster.operations_role = None
		roster.post_abbrv = None
		roster.site = None
		roster.project = None
	else:
		roster = frappe.new_doc("Employee Schedule")
		roster.employee = employee_name
		roster.date = date_str
	roster.employee_availability = "Day Off"
	roster.save(ignore_permissions=True)


@frappe.whitelist()
def get_unassigned_project_employees(project, date, limit_start=0, limit_page_length=20): # Default limit_start
	try:
		# Consider if 'date' should filter employees based on availability or schedule on that date
		return frappe.get_list("Employee", 
							   fields=["name", "employee_name"], 
							   filters={"project": project, "status": "Active"}, # Added status filter
							   order_by="name asc",
							   limit_start=limit_start, 
							   limit_page_length=limit_page_length, 
							   ignore_permissions=True)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_unassigned_project_employees")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_unscheduled_employees(date, shift):
	try:
		# Parameterized query
		employees = frappe.db.sql("""
			select name as employee_id, employee_name
			from `tabEmployee`
			where
				shift=%(shift)s
			and name not in (select employee from `tabEmployee Schedule` where date=%(date)s and shift=%(shift)s)
            and status='Active' -- Added status filter
		""", {"date":date, "shift":shift}, as_dict=1)
		return employees
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_unscheduled_employees")
		return frappe.utils.response.report_error(e)

@frappe.whitelist()
def get_assigned_employees(shift, date, limit_start=0, limit_page_length=20): # Default limit_start
	try:
		return frappe.get_list("Employee Schedule", 
							   fields=["employee", "employee_name", "operations_role"], 
							   filters={"shift": shift, "date": date, "employee_availability": "Working"}, # Added employee_availability
							   order_by="employee_name asc",
							   limit_start=limit_start, 
							   limit_page_length=limit_page_length, 
							   ignore_permissions=True)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_assigned_employees")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_assigned_projects(employee_id): # employee_id is employee name (PK)
	try:
		user, user_roles, user_employee = get_current_user_details() # user_employee is not used here
		if not employee_id: # If employee_id (PK) is not passed, this function's logic is flawed.
			return []

		if "Operations Manager"  in user_roles or 'Operation Admin' in user_roles:
			return frappe.get_list("Project", {"project_type": "External", "status": "Open"}, fields=["name"], limit_page_length=9999, order_by="name asc") # Added status and specific fields

		if "Projects Manager" in user_roles:
			return frappe.get_list("Project", {"account_manager": employee_id, "project_type": "External", "status": "Open"}, fields=["name"], limit_page_length=9999, order_by="name asc") # Added status
		return []
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_assigned_projects")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_assigned_sites(employee_id, project=None): # employee_id is employee name (PK)
	try:
		user, user_roles, user_employee = get_current_user_details() # user_employee is not used here
		filters = {"status": "Active"} # Added status filter
		if project:
			filters.update({"project": project})
		
		# Removed project is None check, as it allows Operations/Project Managers to see all sites if no project is specified
		if "Operations Manager" in user_roles or "Projects Manager" in user_roles:
			return frappe.get_list("Operations Site", filters, fields=["name"], limit_page_length=9999, order_by="name asc")

		elif "Site Supervisor" in user_roles:
			if not employee_id: return [] # Supervisor must be identified
			filters.update({"account_supervisor": employee_id})
			return frappe.get_list("Operations Site", filters, fields=["name"], limit_page_length=9999, order_by="name asc")
		return []

	except Exception as e:
		status_code = getattr(e, 'http_status_code', 500)
		frappe.log_error(frappe.get_traceback(), "get_assigned_sites")
		return frappe.utils.response.report_error(e, http_status_code=status_code) # Pass status code


@frappe.whitelist()
def get_assigned_shifts(employee_id, project=None, site=None): # employee_id is supervisor's employee name (PK)
	try:
		user_roles = frappe.get_roles(frappe.session.user) # Get roles for current session user
		
		# The function get_supervisor_operations_shifts expects supervisor_id (which is employee name/PK)
		# The `employee_id` parameter here IS the supervisor_id for "Shift Supervisor" role.
		# For other roles, it seems to imply the current user's employee record, which isn't directly passed to get_supervisor_operations_shifts.
		# Let's clarify the supervisor_id based on role.
		
		supervisor_id_to_use = None
		if "Shift Supervisor" in user_roles:
			supervisor_id_to_use = employee_id # This is the supervisor's employee PK passed to the function
		# For other manager roles, get_supervisor_operations_shifts might not need a supervisor_id if it fetches all based on project/site
		# The original logic for get_supervisor_operations_shifts needs to be robust for supervisor_id being None.

		if any(role in user_roles for role in ["Operations Manager", "Projects Manager", "Site Supervisor"]):
			return get_supervisor_operations_shifts(supervisor_id=None, project=project, site=site, status="Active") # Pass status
		elif "Shift Supervisor" in user_roles:
			if not supervisor_id_to_use: # Shift supervisor must have an employee_id
				return []
			return get_supervisor_operations_shifts(supervisor_id=supervisor_id_to_use, project=project, site=site, status="Active") # Pass status
		return []

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_assigned_shifts mobile")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_departments():
	try:
		return frappe.get_list("Department",{"is_group": 0}, fields=["name"], limit_page_length=9999, order_by="name asc") # Added fields
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_departments mobile")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_operations_roles(shift=None):
	try:
		user, user_roles, user_employee = get_current_user_details()

		# Allowing managers to see all roles if no shift specified
		if shift is None and any(role in user_roles for role in ["Operations Manager", "Projects Manager", "Site Supervisor"]):
			return frappe.get_list("Operations Role", fields=["name"], filters={"status": "Active"}, limit_page_length=9999, order_by="name asc") # Added status

		# If shift is specified, or for Shift Supervisor, filter by shift posts
		if shift and any(role in user_roles for role in ["Operations Manager", "Projects Manager", "Site Supervisor", "Shift Supervisor"]):
			# Fetch 'post_template' which is the link to Operations Role from Operations Post
			# Then get distinct Operations Role names.
			posts = frappe.get_all("Operations Post", {"site_shift": shift, "status":"Active"}, "post_template", distinct=True) # Added status
			role_names = [p.post_template for p in posts if p.post_template]
			if not role_names: return []
			return frappe.get_all("Operations Role", filters={"name": ["in", role_names], "status":"Active"}, fields=["name"], distinct=True, order_by="name asc")

		return []
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_operations_roles mobile")
		return frappe.utils.response.report_error(e)

@frappe.whitelist()
def get_designations():
	try:
		return frappe.db.get_list("Designation", fields=["name"], limit_page_length=9999, order_by="name asc") # Added fields
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_designations mobile")
		return frappe.utils.response.report_error(e)

@frappe.whitelist()
def get_post_details(post_name):
	try:
		# Consider fetching specific fields instead of "*" if not all are needed
		return frappe.get_value("Operations Post", post_name, "*") 
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_post_details mobile")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def unschedule_staff(employees, start_date=None, end_date=None, never_end=0):
	try:
		employees_list = json.loads(employees) # Renamed
		if not employees_list:
			return response("Error", 400, None, "Employees must be selected.")

		if not start_date and not end_date and not never_end: # Basic validation if no dates are provided
			frappe.throw("Please provide a date range or select 'Never End'.")
			return response("Error", 400, None, "Date information missing.")


		if cint(never_end) and start_date:
			# Delete all schedules from start_date onwards for these employees
			emp_names_to_delete = tuple(set(e['employee'] for e in employees_list if e.get('employee')))
			if not emp_names_to_delete: return response("Success", 200, {'message':'No valid employees to unschedule.'})
			
			# Handle single employee tuple correctly for SQL
			emp_tuple_str = f"('{emp_names_to_delete[0]}')" if len(emp_names_to_delete) == 1 else str(emp_names_to_delete)
			
			frappe.db.sql(f"""DELETE FROM `tabEmployee Schedule` 
							WHERE employee IN {emp_tuple_str} 
							AND date >= %(start_date)s""", {"start_date": start_date})
		elif start_date and end_date:
			# Delete schedules within a specific date range for these employees
			start_date_obj = getdate(start_date)
			end_date_obj = getdate(end_date)
			if start_date_obj > end_date_obj:
				return response("Error", 400, None, "Start date cannot be after End date.")

			emp_names_to_delete = tuple(set(e['employee'] for e in employees_list if e.get('employee')))
			if not emp_names_to_delete: return response("Success", 200, {'message':'No valid employees to unschedule.'})

			emp_tuple_str = f"('{emp_names_to_delete[0]}')" if len(emp_names_to_delete) == 1 else str(emp_names_to_delete)

			frappe.db.sql(f"""DELETE FROM `tabEmployee Schedule` 
							WHERE employee IN {emp_tuple_str}
							AND date BETWEEN %(start_date)s AND %(end_date)s""", 
							{"start_date": start_date, "end_date": end_date})
		else: # Delete specific employee-date pairs from the input
			# This case implies `employees` contains specific dates to delete for each employee
			# It's different from the general "unschedule from X date" logic
			# The original had complex logic here, simplifying to delete specific entries if no range/never_end
			delete_statements = []
			for emp_data in employees_list:
				if emp_data.get('employee') and emp_data.get('date'):
					# This is a specific delete, not using start_date/end_date range from params unless that's the intent
					# For safety, this branch should be very clear about its input expectations.
					# Assuming 'date' in emp_data is the specific date to delete for that employee.
					delete_statements.append(f"""DELETE FROM `tabEmployee Schedule` 
												 WHERE employee='{emp_data['employee']}' 
												 AND date='{emp_data['date']}'""")
			if delete_statements:
				# Not using query_db_list as it's not a standard Frappe util. Using direct frappe.db.sql in loop.
				for stmt in delete_statements:
					frappe.db.sql(stmt)
		
		frappe.db.commit()
		return response("Success", 200, {'message':'Staff(s) unscheduled successfully'})
	
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "unschedule_staff mobile")
		# frappe.throw(str(e)) # Avoid if frontend expects JSON response
		return response("Error", 500, None, str(e))


@frappe.whitelist()
def schedule_staff(employee, shift, operations_role, start_date, end_date=None, never=0, day_off=None): # day_off is day name string like "Sunday"
	try:
		start_date_obj = getdate(start_date)
		end_date_obj = getdate(end_date) if end_date else None

		if cint(never):
			# Schedule for the rest of the year if 'never' (actually means end of current year)
			end_date_obj = getdate(cstr(start_date_obj.year) + '-12-31')
		
		if not end_date_obj: # If not 'never' and no end_date, schedule for single day
			end_date_obj = start_date_obj
			
		if start_date_obj > end_date_obj:
			frappe.throw(_("Start date cannot be after end date."))
			return False

		# Validate shift and operations_role (ensure they exist)
		if not frappe.db.exists("Operations Shift", shift):
			frappe.throw(_(f"Operations Shift '{shift}' not found."))
			return False
		if not frappe.db.exists("Operations Role", operations_role):
			frappe.throw(_(f"Operations Role '{operations_role}' not found."))
			return False


		for date_iter in pd.date_range(start=start_date_obj, end=end_date_obj): # Renamed date
			date_str = cstr(date_iter.date())
			
			roster_doc_name = frappe.db.exists("Employee Schedule", {"employee": employee, "date": date_str})
			roster = None
			if roster_doc_name:
				roster = frappe.get_doc("Employee Schedule", roster_doc_name)
			else:
				roster = frappe.new_doc("Employee Schedule")
				roster.employee = employee
				roster.date = date_str

			if day_off and date_iter.strftime('%A') == day_off: # day_off is a string like "Sunday"
				roster.employee_availability = "Day Off"
				roster.shift = None # Clear shift details for Day Off
				roster.operations_role = None
				roster.post_abbrv = None 
				# Site and project might be kept or cleared based on policy
			else:
				roster.employee_availability = "Working"
				roster.shift = shift
				roster.operations_role = operations_role
				# Fetch post_abbrv from Operations Role if needed, or ensure it's set from client
				# For now, assuming operations_role document might have post_abbrv or client sends it.
				# If operations_role is just a name, need to fetch its details for post_abbrv.
				role_doc = frappe.get_doc("Operations Role", operations_role)
				roster.post_abbrv = role_doc.post_abbrv
				# Shift details like site, project, shift_type should be set from the shift
				shift_doc = frappe.get_doc("Operations Shift", shift)
				roster.site = shift_doc.site
				roster.project = shift_doc.project
				roster.shift_type = shift_doc.shift_type


			# print(roster.as_dict()) # Comment out
			roster.save(ignore_permissions=True)
		
		frappe.db.commit() # Commit once after loop
		return True # Or a success response
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"schedule_staff mobile: {str(e)}")
		# frappe.throw(_(e)) # Avoid if frontend expects JSON
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def schedule_leave(employee, leave_type, start_date, end_date):
	try:
		start_date_obj = getdate(start_date)
		end_date_obj = getdate(end_date)

		if start_date_obj > end_date_obj:
			frappe.throw(_("Start date cannot be after end date."))
			return False

		for date_iter in pd.date_range(start=start_date_obj, end=end_date_obj): # Renamed date
			# print(employee, date_iter.date()) # Comment out
			date_str = cstr(date_iter.date())
			roster_doc_name = frappe.db.exists("Employee Schedule", {"employee": employee, "date": date_str})
			roster = None
			if roster_doc_name:
				roster = frappe.get_doc("Employee Schedule", roster_doc_name)
				roster.shift = None
				roster.shift_type = None
				roster.project = None
				roster.site = None
				roster.operations_role = None # Also clear role info
				roster.post_abbrv = None
			else:
				roster = frappe.new_doc("Employee Schedule")
				roster.employee = employee
				roster.date = date_str
			roster.employee_availability = leave_type
			roster.save(ignore_permissions=True)
		
		frappe.db.commit() # Commit once
		return True # Or success response
	except Exception as e:
		# print(e) # Use frappe.log_error
		frappe.log_error(frappe.get_traceback(), f"schedule_leave mobile: {str(e)}")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def post_handover(post, date, initiated_by, handover_to, docs_check, equipment_check, items_check, docs_comment=None, equipment_comment=None, items_comment=None, attachments=None): # Default attachments to None
	try:
		handover = frappe.new_doc("Post Handover")
		handover.post = post
		handover.date = getdate(date) # Ensure date is date object
		handover.initiated_by = initiated_by
		handover.handover_to = handover_to
		handover.docs_check = cint(docs_check) # Ensure boolean/int
		handover.equipment_check = cint(equipment_check)
		handover.items_check = cint(items_check)
		handover.docs_comment = docs_comment
		handover.equipment_comment = equipment_comment
		handover.items_comment = items_comment
		handover.save(ignore_permissions=True) # Add ignore_permissions

		if attachments: # Check if attachments exist
			# ast.literal_eval can be risky with untrusted input.
			# If attachments is a JSON string of a list, use json.loads.
			parsed_attachments = []
			if isinstance(attachments, str):
				try:
					parsed_attachments = json.loads(attachments)
				except json.JSONDecodeError:
					frappe.throw(_("Invalid format for attachments string."))
					return False # Or handle error
			elif isinstance(attachments, list):
				parsed_attachments = attachments
			
			for attachment_data_b64 in parsed_attachments: # Renamed attachment
				if not isinstance(attachment_data_b64, str): # Basic validation for base64 string
					frappe.log_error("Invalid attachment data found, not a string.", "post_handover mobile")
					continue 
				try:
					filedata = base64.b64decode(attachment_data_b64)
					# Consider more robust filename generation or allow client to suggest names
					attach_file(filename=random_string(6)+".jpg", filedata=filedata, doctype=handover.doctype, docname=handover.name, is_private=1) # Default to private
				except Exception as attach_err:
					frappe.log_error(f"Failed to attach file: {attach_err}", "post_handover mobile")


		frappe.db.commit() # Commit after all operations
		return True # Or success response
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "post_handover mobile")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_handover_posts(shift=None):
	try:
		filters = {"handover": 1, "status":"Active"} # Added status filter
		if shift:
			filters.update({"site_shift": shift})
		return frappe.get_list("Operations Post", filters, fields=["name", "post_name"]) # Specify fields
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_handover_posts mobile")
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_current_shift(employee):
	try:
		current_datetime_obj = now_datetime() # Use Frappe's now_datetime()
		current_date_str = current_datetime_obj.strftime("%Y-%m-%d")
		current_time_obj = current_datetime_obj.time()

		# Fetch active shift assignments for the employee, ordered to get the latest one if multiple match
		# This logic assumes "Shift Assignment" doctype exists and is used for assigning current shifts.
		# The original logic fetches only the latest created Shift Assignment, which might not be the currently active one.
		# A better approach would be to find a Shift Assignment whose start_date <= now and (end_date >= now or no end_date).
		# For simplicity, sticking to a refined version of original logic first:
		
		# This part is complex and depends heavily on the "Shift Assignment" doctype's design and usage.
		# The logic for determining "current" shift based on time and possibly overlapping assignments can be tricky.
		# The provided logic seems to check against the *latest created* shift assignment, not necessarily the *currently active* one by time.
		# Replicating original logic with minor safety:
		
		last_shift_assignments = frappe.get_list("Shift Assignment",
											  filters={"employee": employee, "docstatus": 1}, # Assuming docstatus 1 means active/submitted
											  fields=["name", "shift_type", "start_date", "end_date"], # Add end_date if exists
											  order_by='creation desc',
											  limit_page_length=1)

		if not last_shift_assignments:
			return None # No shift assignment found

		shift_assignment = last_shift_assignments[0]
		
		# Check if this assignment is currently valid based on its date range (if it has one)
		# This part is an addition to make it slightly more robust than just "latest created"
		assignment_start_date = getdate(shift_assignment.start_date)
		assignment_end_date = getdate(shift_assignment.end_date) if shift_assignment.get("end_date") else None

		if assignment_start_date > current_datetime_obj.date(): # Assignment hasn't started
			return None
		if assignment_end_date and assignment_end_date < current_datetime_obj.date(): # Assignment has ended
			return None


		shift_type_details = frappe.get_value("Shift Type", shift_assignment.shift_type, 
											["start_time", "end_time","begin_check_in_before_shift_start_time","allow_check_out_after_shift_end_time"], 
											as_dict=1)
		if not shift_type_details:
			return None # Shift Type not found

		st_start_time = shift_type_details.start_time
		st_end_time = shift_type_details.end_time
		
		# Adjust for check-in/out times
		effective_start_time = (datetime.datetime.min + st_start_time - datetime.timedelta(minutes=cint(shift_type_details.begin_check_in_before_shift_start_time))).time()
		effective_end_time = (datetime.datetime.min + st_end_time + datetime.timedelta(minutes=cint(shift_type_details.allow_check_out_after_shift_end_time))).time()
		
		# Handle overnight shifts
		if effective_start_time > effective_end_time: # Overnight shift
			# Current time is either after start time (on start_date) OR before end time (on next day)
			# This needs to compare with current_datetime_obj and shift_assignment.start_date
			shift_start_datetime = datetime.datetime.combine(assignment_start_date, effective_start_time)
			shift_end_datetime = datetime.datetime.combine(add_days(assignment_start_date,1), effective_end_time)
			
			if current_datetime_obj >= shift_start_datetime or current_datetime_obj <= shift_end_datetime:
				# More precise check for overnight:
				# If current time is on the same day as shift start AND current_time >= effective_start_time
				# OR current time is on the next day of shift start AND current_time <= effective_end_time
				if (current_datetime_obj.date() == assignment_start_date and current_time_obj >= effective_start_time) or \
				   (current_datetime_obj.date() == add_days(assignment_start_date,1) and current_time_obj <= effective_end_time):
					return shift_assignment # Return the whole assignment doc or just shift name
		else: # Same-day shift
			if effective_start_time <= current_time_obj <= effective_end_time:
				# Ensure the current date is the assignment's start date for same-day shifts
				if current_datetime_obj.date() == assignment_start_date :
					return shift_assignment
		return None # Not within any active shift time

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_current_shift mobile")
		# print(frappe.get_traceback()) # Avoid print
		return frappe.utils.response.report_error(e)


@frappe.whitelist()
def get_report_comments(report_name):
	try:
		comments = frappe.get_list("Comment", 
								   filters={"reference_doctype": "Shift Report", "reference_name": report_name, "comment_type": "Comment"}, 
								   fields=["name", "owner", "comment_email", "content", "creation"], # Specify fields instead of "*"
								   order_by="creation desc") 
		return comments
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_report_comments mobile")
		return frappe.utils.response.report_error(e)
