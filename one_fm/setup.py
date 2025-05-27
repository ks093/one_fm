import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import (
	make_property_setter, delete_property_setter
)
from one_fm.custom.workflow.workflow import (
	get_workflow_json_file, create_workflow, delete_workflow
)
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule, delete_assignment_rule
)
# Custom field imports
from one_fm.custom.custom_field.supplier_group import get_supplier_group_custom_fields
from one_fm.custom.custom_field.additional_salary import get_additional_salary_custom_fields
from one_fm.custom.custom_field.assignment_rule import get_assignment_rule_custom_fields
from one_fm.custom.property_setter.assignment_rule import get_assignment_rule_properties

def after_install():
	create_custom_fields(get_custom_fields())
	add_property_setter(get_field_properties())
	create_workflows()
	create_assignment_rules()

def before_uninstall():
	delete_custom_fields(get_custom_fields())
	remove_property_setter(get_field_properties())
	delete_workflows()
	delete_assignment_rules()

def get_custom_fields():
	"""ONEFM specific custom fields that need to be added to the masters in ERPNext"""
	custom_fields = get_additional_salary_custom_fields()
	custom_fields.update(get_supplier_group_custom_fields())
	custom_fields.update(get_assignment_rule_custom_fields())
	return custom_fields

def add_property_setter(property_setters):
	for property in property_setters():
		make_property_setter(
			doctype=property.get("doctype"),
			field_name=property.get("fieldname"),
			property=property.get("property"),
			value=property.get("value"),
			property_type=property.get("property_type"),
			for_doctype=property.get("doctype_or_field"),
			validate_fields_for_doctype=False
		)

def get_field_properties():
	"""ONEFM specific field properties that need to be added to the masters in ERPNext"""
	field_properties = get_assignment_rule_properties()
	return field_properties

def create_workflows():
	create_workflow(get_workflow_json_file("erf.json"))

def create_assignment_rules():
	create_assignment_rule(get_assignment_rule_json_file("roster_post_action_site_supervisor.json"))

def delete_custom_fields(custom_fields: dict):
	"""
	:param custom_fields: a dict like `{'Salary Slip': [{fieldname: 'loans', ...}]}`
	"""
	for doctype, fields in custom_fields.items():
		frappe.db.delete(
			"Custom Field",
			{
				"fieldname": ("in", [field["fieldname"] for field in fields]),
				"dt": doctype,
			},
		)

		frappe.clear_cache(doctype=doctype)

def remove_property_setter(property_setters):
	for property in property_setters():
		property_name = property.get("property")
		doctype = property.get("doc_type")
		field_name = property.get("field_name")
		row_name = property.get("row_name")

		if property_name:
			core_delete_property_setter(
				doc_type=doctype,
				property=property_name,
				field_name=field_name,
				row_name=row_name
			)

			frappe.clear_cache(doctype=doctype)

def delete_workflows():
	delete_workflow(get_workflow_json_file("erf.json"))

def delete_assignment_rules():
	delete_assignment_rule(get_assignment_rule_json_file("roster_post_action_site_supervisor.json"))
