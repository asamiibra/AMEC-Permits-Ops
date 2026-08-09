DEFAULT_BUSINESS_CASE = {
    "applications_per_month": 25, "manual_data_entry_minutes": 75,
    "upload_minutes": 40, "status_check_minutes": 20, "return_rate": 0.35,
    "average_submission_cycles": 1.6, "rework_hours_per_return": 5,
    "delay_days_per_return": 6, "loaded_hourly_rate_qar": 180,
    "optional_project_day_value_qar": 0,
}


def calculate_business_case(values: dict) -> dict:
    v = {**DEFAULT_BUSINESS_CASE, **values}
    applications_year = float(v["applications_per_month"]) * 12
    minutes_per_application = sum(float(v[key]) for key in ("manual_data_entry_minutes", "upload_minutes", "status_check_minutes"))
    manual_hours = applications_year * minutes_per_application / 60
    returned_cases = applications_year * float(v["return_rate"])
    rework_hours = returned_cases * float(v["rework_hours_per_return"])
    labour_cost = (manual_hours + rework_hours) * float(v["loaded_hourly_rate_qar"])
    delay_exposure = returned_cases * float(v["delay_days_per_return"]) * float(v.get("optional_project_day_value_qar", 0))
    return {"applications_per_year": applications_year, "manual_hours_per_application": minutes_per_application / 60,
            "annual_manual_hours": manual_hours, "estimated_annual_returned_cases": returned_cases,
            "estimated_rework_hours": rework_hours, "indicative_labour_cost_qar": labour_cost,
            "illustrative_delay_exposure_qar": delay_exposure, **v}
