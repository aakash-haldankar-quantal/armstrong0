# src/armstrong/tools/custom_tool.py

import json
import re
from crewai.tools import tool
from typing import Dict, Any, Optional, List, Union
import datetime
import traceback

# Assuming mcp_clients.py and models.py are correctly set up
from .mcp_clients import (client_profiler_tool,
                          asset_liability_analysis_mcp_tool,
                          goal_setting_mcp_tool,)

from ..models import ( # Adjusted import path assuming models.py is in src/armstrong/
    InitialClientData,
    ClientProfileCalculations,
    ClientProfile,
    ChildTimelineProfile,
    FullClientData,
    AssetClassificationSummary,
    IndividualAssetProportion,
    AssetLiabilityAnalysis,
    FinancialGoal,             # Used by ComprehensiveGoalProcessingTool & merge tool
    QuantifiedGoalsOutput,     # If ComprehensiveGoalProcessingTool directly outputs this structure
    RetirementPlan,
    EducationPlan,
    DebtManagementPlan,
    FinancialHealthAudit
)

##############################################################################################################################################################################################
                                                                            # snake case
##############################################################################################################################################################################################
# --- Helper function for snake_case conversion ---
def _to_snake_case(name: str) -> str:
    """Converts a string to snake_case. Handles various common casings."""
    if not name:
        return ""
    # Add underscore before uppercase letters if preceded by a lowercase letter or digit,
    # or if preceded by multiple uppercase letters and followed by a lowercase letter (e.g. HTTPResponse -> http_response)
    s1 = re.sub(r'(?<=[a-z0-9])([A-Z])|(?<=[A-Z])([A-Z][a-z])', r'_\1\2', name)
    # Replace spaces, hyphens, and multiple underscores with a single underscore
    s2 = re.sub(r'[\s\-]+', '_', s1)
    return s2.lower().strip('_')

def _normalize_keys_recursively(data: Any) -> Any:
    """
    Recursively converts all dictionary keys in a nested structure to snake_case.
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_key = _to_snake_case(str(key))
            new_dict[new_key] = _normalize_keys_recursively(value)
        return new_dict
    elif isinstance(data, list):
        return [_normalize_keys_recursively(item) for item in data]
    else:
        return data

def _normalize_asset_specific_keys(assets_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Specifically normalizes common problematic keys within asset dictionaries.
    - Renames 'present_values' (plural, any case) to 'present_value'.
    - Converts asset 'type' string values to snake_case.
    """
    normalized_assets = []
    if not isinstance(assets_list, list): # Should not happen if called after _normalize_keys_recursively
        return assets_list

    for asset_dict_raw in assets_list:
        if not isinstance(asset_dict_raw, dict):
            normalized_assets.append(asset_dict_raw) # Pass through non-dicts
            continue

        # Start with a copy that has already had its keys snake_cased by _normalize_keys_recursively
        asset_dict = asset_dict_raw.copy()

        # Standardize 'present_value' key
        # Check for common variations of the plural/mis-cased key
        potential_value_keys = ['present_values', 'Present_Values', 'Present Values', 'presentvalues']
        for pvk in potential_value_keys:
            if pvk in asset_dict and 'present_value' not in asset_dict:
                asset_dict['present_value'] = asset_dict.pop(pvk)
                break # Found and renamed

        # Normalize the 'type' field's *value* to snake_case if it's a string
        if 'type' in asset_dict and isinstance(asset_dict['type'], str):
            asset_dict['type'] = _to_snake_case(asset_dict['type'])
            # Special case for 'cash_or_cash_at_bank' often extracted with spaces/slashes
            if "cash_or_cash_at_bank" in asset_dict['type'] or "cash at bank" in asset_dict['type'].lower().replace('/',' '):
                asset_dict['type'] = "cash_or_cash_at_bank"

        # Normalize 'description' for 'other_investments' if needed
        if asset_dict.get('type') == 'other_investments' and 'description' in asset_dict and isinstance(asset_dict['description'], str):
            asset_dict['description'] = _to_snake_case(asset_dict['description'])

        normalized_assets.append(asset_dict)
    return normalized_assets

def _normalize_liabilities_specific_keys(liabilities_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Specifically normalizes keys and structure within the liabilities section.
    Ensures loan 'type' values are snake_case.
    """
    if not isinstance(liabilities_data, dict):
        return liabilities_data

    normalized_liabilities = liabilities_data.copy()
    if 'loans' in normalized_liabilities and isinstance(normalized_liabilities['loans'], list):
        new_loans_list = []
        for loan_dict_raw in normalized_liabilities['loans']:
            if not isinstance(loan_dict_raw, dict):
                new_loans_list.append(loan_dict_raw)
                continue
            
            loan_dict = loan_dict_raw.copy() # Already snake_cased keys by _normalize_keys_recursively

            # Normalize the 'type' field's *value* to snake_case if it's a string
            if 'type' in loan_dict and isinstance(loan_dict['type'], str):
                loan_dict['type'] = _to_snake_case(loan_dict['type'])
            
            new_loans_list.append(loan_dict)
        normalized_liabilities['loans'] = new_loans_list
    return normalized_liabilities


@tool("JsonSnakeCaseConverterTool")
def json_snake_case_converter_tool(json_string_data: str) -> str:
    """
    Converts all keys in a given JSON string to snake_case recursively.
    It also specifically standardizes asset value keys to 'present_value' (from 'present_values')
    and converts asset/loan 'type' string values to snake_case (e.g., "Provident Fund" becomes "provident_fund").
    This tool is crucial for ensuring data consistency before Pydantic validation.

    Args:
        json_string_data (str): A string containing the JSON data to be normalized.

    Returns:
        str: A JSON string with all keys converted to snake_case and specific value normalizations applied.
             Returns a JSON string with an 'error' key if parsing or processing fails.
    """
    print(f"--- [JsonSnakeCaseConverterTool] Received input string: {json_string_data[:500]}... ---")
    try:
        data = json.loads(json_string_data)
    except json.JSONDecodeError as e:
        error_msg = f"JsonSnakeCaseConverterTool_ERROR: Invalid JSON string provided. Details: {e}. Input snippet: {json_string_data[:200]}"
        print(f"--- [JsonSnakeCaseConverterTool] {error_msg} ---")
        return json.dumps({"error": error_msg})

    try:
        # Step 1: Recursively convert all keys to snake_case
        snake_cased_data = _normalize_keys_recursively(data)
        print(f"--- [JsonSnakeCaseConverterTool] After initial snake_case keys: {str(snake_cased_data)[:500]}... ---")


        # Step 2: Specifically normalize asset keys and 'type' values
        if 'assets' in snake_cased_data and isinstance(snake_cased_data['assets'], list):
            snake_cased_data['assets'] = _normalize_asset_specific_keys(snake_cased_data['assets'])
            print(f"--- [JsonSnakeCaseConverterTool] After asset specific normalization: {str(snake_cased_data.get('assets'))[:500]}... ---")

        # Step 3: Specifically normalize liabilities 'type' values
        if 'liabilities' in snake_cased_data and isinstance(snake_cased_data['liabilities'], dict):
            snake_cased_data['liabilities'] = _normalize_liabilities_specific_keys(snake_cased_data['liabilities'])
            print(f"--- [JsonSnakeCaseConverterTool] After liabilities specific normalization: {str(snake_cased_data.get('liabilities'))[:500]}... ---")
        
        # Step 4: Normalize future_plans keys (plan names)
        if 'future_plans' in snake_cased_data and isinstance(snake_cased_data['future_plans'], dict):
            normalized_future_plans = {}
            for plan_name, plan_details in snake_cased_data['future_plans'].items():
                normalized_future_plans[_to_snake_case(plan_name)] = plan_details # plan_details already recursively normalized
            snake_cased_data['future_plans'] = normalized_future_plans
            print(f"--- [JsonSnakeCaseConverterTool] After future_plans key normalization: {str(snake_cased_data.get('future_plans'))[:500]}... ---")


        output_json_string = json.dumps(snake_cased_data, indent=2)
        print(f"--- [JsonSnakeCaseConverterTool] Successfully normalized. Output preview: {output_json_string[:500]}... ---")
        return output_json_string

    except Exception as e:
        import traceback
        error_msg = f"JsonSnakeCaseConverterTool_ERROR: Error during normalization process: {type(e).__name__} - {str(e)}"
        print(f"--- [JsonSnakeCaseConverterTool] {error_msg} ---")
        print(traceback.format_exc()) # For more detailed server-side logs
        return json.dumps({"error": error_msg, "details": traceback.format_exc()})

##############################################################################################################################################################################################

##############################################################################################################################################################################################


@tool("ComprehensiveProfileCalculatorTool")
def comprehensive_profile_calculator_tool(client_data_json: str) -> str:
    """
    A high-level tool that performs a complete client profile analysis.
    It takes client data as a JSON string (expected to match InitialClientData schema with snake_case keys),
    performs all necessary calculations (age, retirement, risk, children's education timelines) by calling
    the 'client_profiler_tool' (MCP tool) for each underlying calculation,
    and returns a structured JSON string representing ClientProfileCalculations.
    All input arguments to MCP operations and keys in the output JSON will use snake_case.
    
    Args:
        client_data_json (str): A required JSON string representing the client data (conforming to InitialClientData).
    """
    try:
        initial_data_dict = json.loads(client_data_json) # This is expected to be InitialClientData structure
        print("--- [ComprehensiveProfileCalculatorTool] Input Data Parsed ---")

        profile_results_dict = {
            "current_client_age": None,
            "years_to_retirement": None,
            "retirement_horizon_classification": None,
            "equity_exposure_status": None,
            "risk_appetite": None,
            "children_education_profiles_calculations": []
        }

        def run_mcp_and_extract(operation_name: str, arguments: Dict[str, Any], expected_key: Optional[str] = None) -> Any:
            print(f"--- [ComprehensiveProfileCalculatorTool] >> Calling MCP: Op='{operation_name}', Args={arguments} ---")
            mcp_response_json_str = client_profiler_tool.run(operation_name=operation_name, arguments=arguments)
            print(f"--- [ComprehensiveProfileCalculatorTool] >> MCP Response for '{operation_name}': '{mcp_response_json_str}' ---")
            try:
                response_data = json.loads(mcp_response_json_str)
                if response_data.get("error"):
                    print(f"--- [ComprehensiveProfileCalculatorTool] >> MCP Error for '{operation_name}': {response_data['error']} ---")
                    return None
                if expected_key:
                    value = response_data.get(expected_key)
                    print(f"--- [ComprehensiveProfileCalculatorTool] >> Extracted '{expected_key}' for '{operation_name}': {value} ---")
                    return value
                else:
                    response_data.pop("error", None)
                    print(f"--- [ComprehensiveProfileCalculatorTool] >> Full data for '{operation_name}': {response_data} ---")
                    return response_data
            except json.JSONDecodeError:
                print(f"--- [ComprehensiveProfileCalculatorTool] >> WARNING: Could not parse JSON response from '{mcp_response_json_str}' for '{operation_name}'. ---")
                return None
            except Exception as e:
                print(f"--- [ComprehensiveProfileCalculatorTool] >> WARNING: Error processing MCP response for '{operation_name}': {e} ---")
                return None

        personal_info = initial_data_dict.get("personal_information", {})
        family_info = initial_data_dict.get("family_information", {})
        assets_list_raw = initial_data_dict.get("assets", [])

        current_year_from_data = personal_info.get("current_year")
        # ... (rest of the calculation logic as already corrected in ComprehensiveProfileCalculatorTool from our previous iterations,
        # ensuring it populates profile_results_dict with snake_case keys matching ClientProfileCalculations) ...
        # Ensure dob_str is fetched as personal_info.get("date_of_birth")
        # Ensure child info keys are matched with snake_case like "first_child_kahira_year_of_birth"

        # Example of populating (ensure all fields of ClientProfileCalculations are covered)
        dob_str = personal_info.get("date_of_birth")
        current_year_str = str(personal_info.get("current_year", datetime.date.today().year))
        current_date_for_tool = f"{current_year_str}-04-05"

        if dob_str:
            age_val = run_mcp_and_extract("calculate_current_age", {"date_of_birth": dob_str, "current_date": current_date_for_tool}, "calculated_age")
            if age_val is not None: profile_results_dict["current_client_age"] = int(age_val)
        
        # ... (continue for years_to_retirement, retirement_horizon_classification, equity_exposure_status, risk_appetite) ...
        # Ensure all these results are placed into profile_results_dict["key_name"]

        # Simulate the rest of the calculations for brevity in this example snippet
        # In your actual code, all the detailed logic from the previous version of this tool for these fields would be here.
        if profile_results_dict["current_client_age"]: # If age was calculated
            ytr_val = run_mcp_and_extract("calculate_duration_in_years", {"start_value": profile_results_dict["current_client_age"], "end_value": int(str(personal_info.get("retirement_age",55))), "duration_description": "desc"},"duration_years")
            if ytr_val is not None: profile_results_dict["years_to_retirement"] = int(ytr_val)

            if profile_results_dict["years_to_retirement"] is not None:
                 ret_horizon_val = run_mcp_and_extract("classify_investment_horizon", {"years_to_goal": profile_results_dict["years_to_retirement"]}, "horizon_classification")
                 if ret_horizon_val: profile_results_dict["retirement_horizon_classification"] = ret_horizon_val
        
        if assets_list_raw:
            equity_val = run_mcp_and_extract("determine_equity_exposure", {"asset_list": assets_list_raw}, "has_equity_exposure")
            if equity_val is not None: profile_results_dict["equity_exposure_status"] = "Yes" if equity_val else "No"
            
            if profile_results_dict["years_to_retirement"] and profile_results_dict["equity_exposure_status"]:
                risk_val = run_mcp_and_extract("assess_client_risk_appetite", {"years_to_retirement": profile_results_dict["years_to_retirement"], "has_equity_exposure": profile_results_dict["equity_exposure_status"]}, "risk_appetite")
                if risk_val: profile_results_dict["risk_appetite"] = risk_val


        # Child profiles calculation logic (ensure it uses snake_case keys from family_info)
        temp_child_profiles = []
        for key, value in family_info.items():
            if "child" in key.lower() and ("year_of_birth" in key.lower() or "yob" in key.lower()):
                child_yob_str = str(value).strip()
                if child_yob_str.isdigit() and len(child_yob_str) == 4:
                    child_yob_val = int(child_yob_str)
                    # ... (robust child_identifier extraction logic here, ensuring it's stripped) ...
                    id_match = re.search(r'child_?(\w+)_?(?:year_of_birth|yob)', key, re.IGNORECASE)
                    if not id_match: id_match = re.search(r'(?:first|second|third)_child_([^_]+)_year_of_birth', key, re.IGNORECASE)
                    if not id_match: id_match = re.search(r'child(?:.*?_)?(.*?)_?(?:year_of_birth|yob)', key, re.IGNORECASE)
                    child_identifier = (id_match.group(1).strip().replace('_', ' ').title() if id_match and id_match.group(1) else f"Child_{len(temp_child_profiles)+1}").strip()

                    child_age_val = run_mcp_and_extract("calculate_current_age", {"date_of_birth": f"{child_yob_val}-01-01", "current_date": current_date_for_tool}, "calculated_age")
                    if child_age_val is None: continue
                    child_current_age_val = int(child_age_val)

                    ug_ytr = run_mcp_and_extract("calculate_duration_in_years", {"start_value": child_current_age_val, "end_value": 18, "duration_description": f"{child_identifier} UG"}, "duration_years")
                    ug_horizon = run_mcp_and_extract("classify_investment_horizon", {"years_to_goal": int(ug_ytr) if ug_ytr is not None else 0}, "horizon_classification") if ug_ytr is not None else None
                    
                    pg_ytr = run_mcp_and_extract("calculate_duration_in_years", {"start_value": child_current_age_val, "end_value": 22, "duration_description": f"{child_identifier} PG"}, "duration_years")
                    pg_horizon = run_mcp_and_extract("classify_investment_horizon", {"years_to_goal": int(pg_ytr) if pg_ytr is not None else 0}, "horizon_classification") if pg_ytr is not None else None

                    temp_child_profiles.append(ChildTimelineProfile(
                        child_identifier=child_identifier,
                        child_current_age=child_current_age_val,
                        ug_years_to_goal=int(ug_ytr) if ug_ytr is not None else 0, # Default to 0 if None to satisfy int type
                        ug_horizon_classification=ug_horizon if ug_horizon else "Unknown", # Default
                        pg_years_to_goal=int(pg_ytr) if pg_ytr is not None else None,
                        pg_horizon_classification=pg_horizon
                    ).model_dump(exclude_none=True)) # model_dump to get dict
        profile_results_dict["children_education_profiles_calculations"] = temp_child_profiles


        # Validate with ClientProfileCalculations before returning
        validated_profile_calcs = ClientProfileCalculations(**profile_results_dict)
        print(f"--- [ComprehensiveProfileCalculatorTool] Completed. Output: {validated_profile_calcs.model_dump_json(indent=2)} ---")
        return validated_profile_calcs.model_dump_json(indent=2)

    except Exception as e:
        error_message = f"COMPREHENSIVE_PROFILE_CALCULATOR_TOOL_ERROR: {type(e).__name__} - {str(e)}"
        print(f"--- [ComprehensiveProfileCalculatorTool] {error_message} ---")
        import traceback
        # Return a JSON string that represents an error, but try to fit ClientProfileCalculations schema with error info
        # Or, adjust your agent to handle a generic error JSON from this tool
        error_payload = {"error": error_message, "details": traceback.format_exc()}
        # Attempt to still roughly fit the schema if possible, or have a dedicated error field in ClientProfileCalculations
        return json.dumps(error_payload)

# @tool("ComprehensiveAssetLiabilityAnalysisTool")
# def comprehensive_asset_liability_analysis_tool(client_data_json: str) -> str:
#     """
#     Orchestrates a complete asset and liability analysis using underlying MCP tool operations.
#     It takes client_data_json (string representation of InitialClientData or FullClientData),
#     performs all necessary calculations (total assets, total liabilities, net worth,
#     asset classification, bucket proportions, individual asset proportions),
#     and returns a single JSON string representing the fully populated AssetLiabilityAnalysis data.
#     All keys in the input for MCP operations and in the output JSON are snake_case.

#     Args:
#         client_data_json (str): JSON string of client data (InitialClientData/FullClientData).
#                                 Expected to have 'assets' (List[Dict]) and 'liabilities' (Dict)
#                                 with snake_case keys.
#     Returns:
#         str: JSON string conforming to the AssetLiabilityAnalysis Pydantic model.
#     """
#     print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] Starting analysis with input: {client_data_json[:200]}... ---")
#     final_analysis_results = {} # Will store parts to build AssetLiabilityAnalysis

#     try:
#         data = json.loads(client_data_json)
#         # Ensure initial data is provided as a dictionary
#         # It could be InitialClientData or FullClientData, we mainly need 'assets' and 'liabilities'
#         assets_raw_list = data.get("assets", [])                 # List[Dict[str, Any]]
#         liabilities_raw_dict = data.get("liabilities", {})       # Dict[str, Dict[str, Any]]

#         # Helper to call AssetLiabilityAnalysisMCPTool and parse its JSON response
#         def run_ala_mcp_and_extract(operation_name: str, arguments: Dict[str, Any], expected_key: Optional[str] = None) -> Any:
#             print(f"--- [ALA Orchestrator] >> Calling MCP: Op='{operation_name}', Args={arguments} ---")
#             # All arguments passed to asset_liability_analysis_mcp_tool must have snake_case keys
#             mcp_response_json_str = asset_liability_analysis_mcp_tool.run(operation_name=operation_name, arguments=arguments)
#             print(f"--- [ALA Orchestrator] >> MCP Response for '{operation_name}': '{mcp_response_json_str}' ---")
            
#             try:
#                 response_data = json.loads(mcp_response_json_str)
#                 if response_data.get("error"):
#                     print(f"--- [ALA Orchestrator] >> MCP Error for '{operation_name}': {response_data['error']} ---")
#                     return None 
                
#                 if expected_key:
#                     value = response_data.get(expected_key)
#                     print(f"--- [ALA Orchestrator] >> Extracted '{expected_key}' for '{operation_name}': {value} ---")
#                     return value
#                 else: 
#                     response_data.pop("error", None)
#                     print(f"--- [ALA Orchestrator] >> Full data for '{operation_name}': {response_data} ---")
#                     return response_data 
#             except json.JSONDecodeError:
#                 print(f"--- [ALA Orchestrator] >> WARNING: Could not parse JSON from '{mcp_response_json_str}' for '{operation_name}'. ---")
#                 return None
#             except Exception as e:
#                 print(f"--- [ALA Orchestrator] >> WARNING: Error processing MCP response for '{operation_name}': {e} ---")
#                 return None

#         # 1. Calculate Total Asset Value
#         # assets_raw_list is already List[Dict], matching items_list for 'calculate_total_value'
#         # Ensure value_key matches what's in your assets_raw_list items, e.g., "present_value"
#         total_assets_data = run_ala_mcp_and_extract(
#             "calculate_total_value",
#             {"items_list": assets_raw_list, "value_key": "present_value", "item_type_description": "total client assets"},
#             "total_value"
#         )
#         total_assets_numeric = float(total_assets_data) if total_assets_data is not None else 0.0
#         final_analysis_results["total_asset_value_numeric"] = total_assets_numeric

#         # 2. Calculate Total Liabilities Value
#         # liabilities_raw_dict needs transformation to List[Dict] for 'calculate_total_value'
#         # Example: {"home_loan": {"outstanding_amount": 100}, "car_loan": {"outstanding_amount": 20}}
#         # -> [{"loan_type": "home_loan", "outstanding_amount": 100}, {"loan_type": "car_loan", "outstanding_amount": 20}]
#         liabilities_items_list = []
#         if isinstance(liabilities_raw_dict, dict):
#             for loan_type_key, details_dict in liabilities_raw_dict.items():
#                 if isinstance(details_dict, dict):
#                     item = {"loan_type": loan_type_key} # Use snake_case for internal consistency
#                     item.update(details_dict) # Add all details like outstanding_amount, interest_rate
#                     liabilities_items_list.append(item)
        
#         total_liabilities_data = run_ala_mcp_and_extract(
#             "calculate_total_value",
#             {"items_list": liabilities_items_list, "value_key": "outstanding_amount", "item_type_description": "total client liabilities"},
#             "total_value"
#         )
#         total_liabilities_numeric = float(total_liabilities_data) if total_liabilities_data is not None else 0.0
#         final_analysis_results["total_liabilities_value_numeric"] = total_liabilities_numeric

#         # 3. Calculate Net Worth
#         net_worth_data = run_ala_mcp_and_extract(
#             "calculate_net_worth",
#             {"total_assets": total_assets_numeric, "total_liabilities": total_liabilities_numeric},
#             "net_worth"
#         )
#         final_analysis_results["net_worth_numeric"] = float(net_worth_data) if net_worth_data is not None else 0.0

#         # 4. Classify Assets and Get Bucket Summary
#         # Define standard classification rules (ensure keys are snake_case if AssetClassificationSummary expects them)
#         # These bucket names MUST match the field names in AssetClassificationSummary (e.g., liquid_assets)
#         classification_rules = {
#             "liquid_assets": ["cash", "bank", "fixed deposit", "mutual fund", "equity", "stocks", "shares", "bond", "gold"],
#             "retirement_assets": ["provident fund", "ppf", "nps", "pension"],
#             "fixed_assets": ["real estate", "property", "land", "flat", "house"]
#         }
#         # The server function 'classify_assets_and_get_bucket_summary' input 'asset_list' uses asset_raw_list
#         # and 'value_key' should be 'present_value'
#         classification_data = run_ala_mcp_and_extract(
#             "classify_assets_and_get_bucket_summary",
#             {"asset_list": assets_raw_list, "classification_rules": classification_rules, "value_key": "present_value"}
#         )
        
#         # bucket_totals will have snake_case keys from classification_rules
#         bucket_totals = classification_data.get("bucket_totals") if classification_data else {}
#         # Ensure AssetClassificationSummary fields are populated correctly
#         summary_dict = {
#             "liquid_assets": bucket_totals.get("liquid_assets", 0.0),
#             "retirement_assets": bucket_totals.get("retirement_assets", 0.0),
#             "fixed_assets": bucket_totals.get("fixed_assets", 0.0)
#         }
#         final_analysis_results["asset_classification_summary"] = summary_dict # This will become AssetClassificationSummary object

#         # 5. Calculate Category Proportions for Asset Buckets
#         # category_values_dict should have snake_case keys matching bucket_totals
#         if bucket_totals and total_assets_numeric > 0:
#             bucket_proportions_data = run_ala_mcp_and_extract(
#                 "calculate_category_proportions",
#                 {"category_values_dict": bucket_totals, "total_value": total_assets_numeric},
#                 "proportions_percentage" # This is Dict[str, float]
#             )
#             final_analysis_results["asset_bucket_proportions"] = bucket_proportions_data if bucket_proportions_data else {}
#         else:
#             final_analysis_results["asset_bucket_proportions"] = {}

#         # 6. Calculate Individual Asset Proportions
#         # asset_name_key and value_key from asset_list_raw (e.g. "asset_name", "present_value")
#         individual_proportions_data = run_ala_mcp_and_extract(
#             "calculate_individual_asset_proportions",
#             {"asset_list": assets_raw_list, "total_asset_value": total_assets_numeric, "asset_name_key": "type", "value_key": "present_value"},
#             "individual_proportions" # This is List[Dict]
#         )
#         # The items in this list should already match IndividualAssetProportion fields (asset_category, value, proportion_percentage)
#         final_analysis_results["individual_asset_proportions"] = individual_proportions_data if individual_proportions_data else []


#         # Validate and return as JSON string for AssetLiabilityAnalysis
#         # Ensure all required fields of AssetLiabilityAnalysis are present in final_analysis_results
#         # If some calculation failed and a required field is missing, this will error or need default
#         try:
#             # Construct the Pydantic model to ensure structure and perform validation
#             # AssetClassificationSummary is nested, so it needs to be an object here
#             if "asset_classification_summary" in final_analysis_results and isinstance(final_analysis_results["asset_classification_summary"], dict):
#                  asc_summary_obj = AssetClassificationSummary(**final_analysis_results["asset_classification_summary"])
#                  final_analysis_results["asset_classification_summary"] = asc_summary_obj.model_dump() # Store as dict for final JSON
            
#             # IndividualAssetProportion list
#             if "individual_asset_proportions" in final_analysis_results and isinstance(final_analysis_results["individual_asset_proportions"], list):
#                 iap_list = [IndividualAssetProportion(**item).model_dump() for item in final_analysis_results["individual_asset_proportions"]]
#                 final_analysis_results["individual_asset_proportions"] = iap_list


#             # Check for required fields before constructing AssetLiabilityAnalysis; provide defaults if critical ones are missing
#             # For example, if total_asset_value_numeric is None (from failed calc), this part needs to handle it.
#             # For this tool, we assume calculations succeeded enough to populate.
#             # The actual AssetLiabilityAnalysis Pydantic model expects these:
#             # - total_asset_value_numeric: float
#             # - total_liabilities_value_numeric: float
#             # - net_worth_numeric: float
#             # - asset_classification_summary: AssetClassificationSummary (needs to be dict for JSON)
#             # - asset_bucket_proportions: Dict[str, float]
#             # - individual_asset_proportions: List[IndividualAssetProportion] (needs to be list of dicts for JSON)

#             # Ensure the nested Pydantic objects are correctly created then dumped for the final string
#             # This intermediate Pydantic validation is good before dumping to JSON
#             analysis_pydantic_obj = AssetLiabilityAnalysis(**final_analysis_results)
#             output_json_str = analysis_pydantic_obj.model_dump_json(indent=2, exclude_none=True)
#             print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] Completed. Output: {output_json_str[:500]}... ---")
#             return output_json_str
#         except Exception as pydantic_error: # Catch Pydantic validation or other errors during assembly
#             error_msg = f"ASSET_LIABILITY_ORCHESTRATOR_PYDANTIC_ERROR: Error assembling AssetLiabilityAnalysis object: {type(pydantic_error).__name__} - {str(pydantic_error)}"
#             print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] {error_msg} ---")
#             import traceback
#             return json.dumps({"error": error_msg, "details": traceback.format_exc(), "partial_results": final_analysis_results})


#     except Exception as e:
#         error_message = f"ASSET_LIABILITY_ORCHESTRATOR_ERROR: {type(e).__name__} - {str(e)}"
#         print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] {error_message} ---")
#         import traceback
#         return json.dumps({"error": error_message, "details": traceback.format_exc()})
@tool("ComprehensiveAssetLiabilityAnalysisTool")
def comprehensive_asset_liability_analysis_tool(client_data_json: str) -> str:
    """
    Orchestrates a complete asset and liability analysis using underlying MCP tool operations.
    It takes client_data_json (string representation of FullClientData, expected to have snake_case keys),
    performs all necessary calculations (total assets, total liabilities, net worth,
    asset classification, bucket proportions, individual asset proportions),
    and returns a single JSON string representing the fully populated AssetLiabilityAnalysis data
    (conforming to the AssetLiabilityAnalysis Pydantic model with snake_case keys).

    Args:
        client_data_json (str): JSON string of client data (typically FullClientData from a previous task).
                                Expected to have 'assets' (List[Dict]) with 'present_value' and 'type' (snake_case) keys,
                                and 'liabilities' (Dict) with a 'loans' (List[Dict]) key,
                                where loan dicts have 'outstanding_amount' and 'type' (snake_case) keys.
    Returns:
        str: JSON string conforming to the AssetLiabilityAnalysis Pydantic model.
             Returns a JSON string with an 'error' key if parsing or processing fails.
    """
    print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] Starting analysis. Input snippet: {client_data_json[:300]}... ---")
    final_analysis_results = {}

    try:
        data = json.loads(client_data_json)
        
        # Ensure data is a dictionary after parsing
        if not isinstance(data, dict):
            error_msg = "ComprehensiveAssetLiabilityAnalysisTool_ERROR: Parsed client_data_json is not a dictionary."
            print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] {error_msg} ---")
            return json.dumps({"error": error_msg, "input_type": str(type(data))})

        assets_raw_list = data.get("assets", [])
        liabilities_section = data.get("liabilities", {}) # This should be {"loans": [...]}
        
        # Ensure assets_raw_list is a list
        if not isinstance(assets_raw_list, list):
            assets_raw_list = []
            print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] WARNING: 'assets' field was not a list, defaulting to empty list. Found: {type(data.get('assets'))} ---")
            
        # Ensure liabilities_section is a dict
        if not isinstance(liabilities_section, dict):
            liabilities_section = {}
            print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] WARNING: 'liabilities' field was not a dict, defaulting to empty dict. Found: {type(data.get('liabilities'))} ---")


        # Helper to call AssetLiabilityAnalysisMCPTool and parse its JSON response
        def run_ala_mcp_and_extract(operation_name: str, arguments: Dict[str, Any], expected_key: Optional[str] = None) -> Any:
            print(f"--- [ALA Orchestrator] >> Calling MCP Tool: '{operation_name}', Args: {str(arguments)[:200]}... ---")
            mcp_response_json_str = asset_liability_analysis_mcp_tool.run(operation_name=operation_name, arguments=arguments)
            print(f"--- [ALA Orchestrator] >> MCP Response for '{operation_name}': '{mcp_response_json_str[:300]}...' ---")
            
            try:
                response_data = json.loads(mcp_response_json_str)
                if response_data.get("error"):
                    print(f"--- [ALA Orchestrator] >> MCP Error for '{operation_name}': {response_data['error']} ---")
                    return None 
                
                if expected_key:
                    value = response_data.get(expected_key)
                    print(f"--- [ALA Orchestrator] >> Extracted '{expected_key}' for '{operation_name}': {value} ---")
                    return value
                else: 
                    response_data.pop("error", None) # Remove error key if present and not the main content
                    print(f"--- [ALA Orchestrator] >> Full data for '{operation_name}': {str(response_data)[:200]}... ---")
                    return response_data 
            except json.JSONDecodeError:
                print(f"--- [ALA Orchestrator] >> WARNING: Could not parse JSON from MCP response '{mcp_response_json_str[:200]}...' for '{operation_name}'. ---")
                return None
            except Exception as e:
                print(f"--- [ALA Orchestrator] >> WARNING: Error processing MCP response for '{operation_name}': {type(e).__name__} - {e} ---")
                return None

        # 1. Calculate Total Asset Value
        print("--- [ComprehensiveAssetLiabilityAnalysisTool] Step 1: Calculating Total Asset Value ---")
        total_assets_data = run_ala_mcp_and_extract(
            "calculate_total_value",
            {"items_list": assets_raw_list, "value_key": "present_value", "item_type_description": "total client assets"},
            "total_value"
        )
        total_assets_numeric = float(total_assets_data) if total_assets_data is not None and isinstance(total_assets_data, (int, float, str)) else 0.0
        final_analysis_results["total_asset_value_numeric"] = total_assets_numeric

        # 2. Calculate Total Liabilities Value - CORRECTED LOGIC
        print("--- [ComprehensiveAssetLiabilityAnalysisTool] Step 2: Calculating Total Liabilities Value ---")
        liabilities_items_list_for_calc = []
        # Get the list of loan dictionaries from the 'loans' key
        actual_loans_list = liabilities_section.get("loans", []) 
        if isinstance(actual_loans_list, list):
            for loan_dict in actual_loans_list:
                if isinstance(loan_dict, dict) and "outstanding_amount" in loan_dict:
                    # The MCP tool 'calculate_total_value' expects a list of dicts.
                    # Each dict must have the 'value_key' (which will be 'outstanding_amount').
                    # We can pass the loan_dict directly if it's structured appropriately.
                    liabilities_items_list_for_calc.append(loan_dict.copy()) 
        else:
            print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] WARNING: 'liabilities.loans' field was not a list, or 'liabilities' section missing/malformed. Defaulting to empty liabilities list. Found: {type(actual_loans_list)} ---")
            
        total_liabilities_data = run_ala_mcp_and_extract(
            "calculate_total_value",
            {"items_list": liabilities_items_list_for_calc, "value_key": "outstanding_amount", "item_type_description": "total client liabilities"},
            "total_value"
        )
        total_liabilities_numeric = float(total_liabilities_data) if total_liabilities_data is not None and isinstance(total_liabilities_data, (int, float, str)) else 0.0
        final_analysis_results["total_liabilities_value_numeric"] = total_liabilities_numeric

        # 3. Calculate Net Worth
        print("--- [ComprehensiveAssetLiabilityAnalysisTool] Step 3: Calculating Net Worth ---")
        net_worth_data = run_ala_mcp_and_extract(
            "calculate_net_worth",
            {"total_assets": total_assets_numeric, "total_liabilities": total_liabilities_numeric},
            "net_worth"
        )
        final_analysis_results["net_worth_numeric"] = float(net_worth_data) if net_worth_data is not None and isinstance(net_worth_data, (int, float, str)) else 0.0

        # 4. Classify Assets and Get Bucket Summary
        print("--- [ComprehensiveAssetLiabilityAnalysisTool] Step 4: Classifying Assets ---")
        classification_rules = {
            "liquid_assets": ["cash", "bank", "fixed_deposit", "mutual_fund", "direct_equity", "stocks", "shares", "bond", "gold", "gold_etf", "crypto"], # Added crypto, gold_etf
            "retirement_assets": ["provident_fund", "public_provident_fund", "ppf", "nps", "pension"],
            "fixed_assets": ["real_estate", "property", "land", "flat", "house", "other_investments_ornamental_gold"] # Added specific 'other' if it's fixed
            # Note: 'other_investments_ornamental_gold' might be debatable, could be liquid if easily sellable, or fixed.
            # The classification keywords should match the snake_cased 'type' or 'description' values from Agent 1's output.
        }
        classification_data = run_ala_mcp_and_extract(
            "classify_assets_and_get_bucket_summary",
            {"asset_list": assets_raw_list, "classification_rules": classification_rules, "value_key": "present_value"}
        )
        
        bucket_totals = classification_data.get("bucket_totals") if isinstance(classification_data, dict) else {}
        final_analysis_results["asset_classification_summary"] = {
            "liquid_assets": float(bucket_totals.get("liquid_assets", 0.0)),
            "retirement_assets": float(bucket_totals.get("retirement_assets", 0.0)),
            "fixed_assets": float(bucket_totals.get("fixed_assets", 0.0))
        }

        # 5. Calculate Category Proportions for Asset Buckets
        print("--- [ComprehensiveAssetLiabilityAnalysisTool] Step 5: Calculating Asset Bucket Proportions ---")
        if bucket_totals and total_assets_numeric > 0:
            bucket_proportions_data = run_ala_mcp_and_extract(
                "calculate_category_proportions",
                {"category_values_dict": bucket_totals, "total_value": total_assets_numeric},
                "proportions_percentage"
            )
            final_analysis_results["asset_bucket_proportions"] = bucket_proportions_data if isinstance(bucket_proportions_data, dict) else {}
        else:
            final_analysis_results["asset_bucket_proportions"] = {}

        # 6. Calculate Individual Asset Proportions
        print("--- [ComprehensiveAssetLiabilityAnalysisTool] Step 6: Calculating Individual Asset Proportions ---")
        # The 'asset_name_key' should be 'type' because JsonSnakeCaseConverterTool now converts asset types to snake_case.
        individual_proportions_data = run_ala_mcp_and_extract(
            "calculate_individual_asset_proportions",
            {"asset_list": assets_raw_list, "total_asset_value": total_assets_numeric, "asset_name_key": "type", "value_key": "present_value"},
            "individual_proportions"
        )
        final_analysis_results["individual_asset_proportions"] = individual_proportions_data if isinstance(individual_proportions_data, list) else []

        # Validate and return as JSON string for AssetLiabilityAnalysis
        print("--- [ComprehensiveAssetLiabilityAnalysisTool] Assembling final Pydantic object ---")
        try:
            # Ensure nested Pydantic models are instantiated correctly before dumping
            if isinstance(final_analysis_results.get("asset_classification_summary"), dict):
                final_analysis_results["asset_classification_summary"] = AssetClassificationSummary(
                    **final_analysis_results["asset_classification_summary"]
                )
            
            if isinstance(final_analysis_results.get("individual_asset_proportions"), list):
                final_analysis_results["individual_asset_proportions"] = [
                    IndividualAssetProportion(**item) for item in final_analysis_results["individual_asset_proportions"]
                ]
            
            # Ensure all required fields have some value (even if 0.0 or empty list/dict)
            # Pydantic will raise error if required fields are missing and not Optional/no default
            required_fields = AssetLiabilityAnalysis.model_fields.keys()
            for req_field in required_fields:
                if req_field not in final_analysis_results:
                    # This indicates a logic error above or unexpected None from MCP calls
                    print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] WARNING: Required field '{req_field}' missing for AssetLiabilityAnalysis. Attempting to use default or will error.")
                    # Depending on Pydantic model, this might still fail if no default and not Optional
            
            analysis_pydantic_obj = AssetLiabilityAnalysis(**final_analysis_results)
            output_json_str = analysis_pydantic_obj.model_dump_json(indent=2, exclude_none=True)
            print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] Completed successfully. Output preview: {output_json_str[:500]}... ---")
            return output_json_str
            
        except Exception as pydantic_error:
            error_msg = f"ASSET_LIABILITY_ORCHESTRATOR_PYDANTIC_ERROR: Error assembling/validating AssetLiabilityAnalysis object: {type(pydantic_error).__name__} - {str(pydantic_error)}"
            print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] {error_msg} ---")
            import traceback
            # Return error JSON, including partial results if helpful for debugging
            return json.dumps({
                "error": error_msg, 
                "details": traceback.format_exc(), 
                "partial_results_before_pydantic": final_analysis_results # Show what was collected
            })

    except json.JSONDecodeError as e_initial_parse:
        error_message = f"ComprehensiveAssetLiabilityAnalysisTool_ERROR: Initial JSONDecodeError for client_data_json: {type(e_initial_parse).__name__} - {str(e_initial_parse)}. Input snippet: {client_data_json[:200]}"
        print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] {error_message} ---")
        return json.dumps({"error": error_message})
        
    except Exception as e_general:
        error_message = f"ComprehensiveAssetLiabilityAnalysisTool_ERROR: General error: {type(e_general).__name__} - {str(e_general)}"
        print(f"--- [ComprehensiveAssetLiabilityAnalysisTool] {error_message} ---")
        import traceback
        return json.dumps({"error": error_message, "details": traceback.format_exc()})
    
################################################# Tool for Agent 5 : GoalSettingMCPTool #################################################
# Helper function (ensure this is defined or imported correctly)
def _parse_value_flexible(value: Any) -> Optional[Union[int, float, str]]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned_value = value.replace(',', '').strip()
        if not cleaned_value or "not specified" in cleaned_value.lower() or "n/a" in cleaned_value.lower():
            return None
        try:
            return int(cleaned_value)
        except ValueError:
            try:
                return float(cleaned_value)
            except ValueError:
                return cleaned_value # Return as string if not number or specific non-value strings
    return str(value) 



@tool("ComprehensiveGoalProcessingTool")
def comprehensive_goal_processing_tool(client_data_json: str, default_inflation_rate_pa: float = 0.06) -> str:
    """
    Identifies client financial goals (Retirement, Education UG/PG for each child, and other
    goals from 'future_plans' in client_data_json), calculates their timelines (target_year,
    time_remaining_years), and projects their future costs if current_cost_input is available.
    Inputs ('client_data_json') and outputs (JSON string) use snake_case keys.

    Args:
        client_data_json (str): JSON string of client data (typically FullClientData after snake_case normalization).
                                Must contain 'personal_information', 'client_profile', and 'future_plans'.
                                'children_education_profiles_calculations' is optional.
        default_inflation_rate_pa (float): Default annual inflation rate (decimal, e.g., 0.06)
                                           to use for future cost projections if not specified per goal.
    Returns:
        str: JSON string: '{"quantified_financial_goals": [List of FinancialGoal objects as dicts]}'
             or '{"error": "message", "details": "..."}' if processing fails.
    """
    print(f"--- [ComprehensiveGoalProcessingTool] Starting. Default Inflation: {default_inflation_rate_pa}. Input JSON snippet: {client_data_json[:300]}... ---")
    processed_goals_list = []

    def run_goal_mcp_and_extract(operation_name: str, arguments: Dict[str, Any], expected_key: Optional[str] = None) -> Any:
        print(f"--- [CGPT - MCP Call] Op: '{operation_name}', Args: {str(arguments)[:150]}... ---")
        # Ensure all numeric args for MCP tool are actual numbers, not strings from _parse_value_flexible if it returned a string
        parsed_args = {}
        for k, v in arguments.items():
            if k in ["current_cost", "number_of_years", "inflation_rate_pa", "start_value", "end_value"]: # Keys expecting numbers
                num_v = _parse_value_flexible(v)
                if isinstance(num_v, (int,float)):
                    parsed_args[k] = num_v
                elif num_v is not None: # If it parsed to a string that wasn't 'None'
                     print(f"--- [CGPT - MCP Call] WARNING: Arg '{k}' for op '{operation_name}' is non-numeric string '{v}', MCP call might fail or be inaccurate.")
                     parsed_args[k] = v # Pass as is, MCP tool might handle or error
                else: # v was None or unparsable
                    parsed_args[k] = None # Or skip/error based on MCP tool requirements
            else:
                parsed_args[k] = v
        
        # Filter out None arguments unless explicitly allowed by MCP tool
        final_mcp_args = {k:v for k,v in parsed_args.items() if v is not None}

        mcp_response_json_str = goal_setting_mcp_tool.run(operation_name=operation_name, arguments=final_mcp_args)
        print(f"--- [CGPT - MCP Response] Op: '{operation_name}', Raw Resp: '{mcp_response_json_str[:200]}...' ---")
        try:
            response_data = json.loads(mcp_response_json_str)
            if response_data.get("error"):
                print(f"--- [CGPT - MCP Error] Op: '{operation_name}', Error: {response_data['error']} ---")
                return None
            if expected_key:
                return response_data.get(expected_key)
            return response_data
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"--- [CGPT - MCP Parse/Attr Error] Op: '{operation_name}', Error: {e}, Resp: '{mcp_response_json_str}' ---")
            return None
        except Exception as e_gen:
            print(f"--- [CGPT - MCP General Error] Op: '{operation_name}', Error: {e_gen}, Resp: '{mcp_response_json_str}' ---")
            return None

    try:
        data = json.loads(client_data_json)
        personal_info = data.get("personal_information", {})
        client_profile_data = data.get("client_profile", {})
        # children_education_profiles_data = data.get("children_education_profiles_calculations", []) # Not used for Harish as no children
        future_plans_data = data.get("future_plans", {})

        current_year_from_misc = data.get("miscellaneous", {}).get("current_year")
        current_year_from_personal = personal_info.get("current_year")

        if current_year_from_misc is not None:
             current_year_val = _parse_value_flexible(current_year_from_misc)
        elif current_year_from_personal is not None:
             current_year_val = _parse_value_flexible(current_year_from_personal)
        else:
            current_year_val = datetime.date.today().year
        
        current_year = int(current_year_val) if isinstance(current_year_val, (int, float)) else datetime.date.today().year
        print(f"--- [ComprehensiveGoalProcessingTool] Using Current Year: {current_year} ---")

        # 1. Retirement Goal
        print("--- [ComprehensiveGoalProcessingTool] Processing Retirement Goal ---")
        years_to_retirement_from_profile_raw = client_profile_data.get("years_to_retirement")
        years_to_retirement_from_profile = int(_parse_value_flexible(years_to_retirement_from_profile_raw)) if years_to_retirement_from_profile_raw is not None else None

        # Check if a retirement goal is explicitly in future_plans
        retirement_goal_from_future_plans = None
        for plan_name_key, plan_details_dict in future_plans_data.items():
            if "retirement" in plan_name_key.lower():
                retirement_goal_from_future_plans = plan_details_dict
                # Use the name from future_plans if available, otherwise default
                goal_name_ret = str(plan_name_key) # Already snake_cased by JsonSnakeCaseConverterTool
                print(f"--- [ComprehensiveGoalProcessingTool] Found explicit retirement goal in future_plans: '{goal_name_ret}' ---")
                break
        
        if retirement_goal_from_future_plans and isinstance(retirement_goal_from_future_plans, dict):
            time_left_ret_raw = _parse_value_flexible(retirement_goal_from_future_plans.get("time_years")) # Key might be 'time' or 'time_years'
            if time_left_ret_raw is None: # Fallback if 'time_years' isn't there, check for 'time'
                 time_left_ret_raw = _parse_value_flexible(retirement_goal_from_future_plans.get("time"))

            cost_now_ret_raw = _parse_value_flexible(retirement_goal_from_future_plans.get("amount_required_today"))
            
            time_left_ret = int(time_left_ret_raw) if isinstance(time_left_ret_raw, (int, float)) else years_to_retirement_from_profile
            cost_now_ret = float(cost_now_ret_raw) if isinstance(cost_now_ret_raw, (int, float)) else None
            
            if time_left_ret is not None:
                target_year_ret = current_year + time_left_ret
                fv_string_ret = None
                if cost_now_ret is not None:
                    fv_data_ret = run_goal_mcp_and_extract(
                        "project_future_cost",
                        {"current_cost": cost_now_ret, "number_of_years": time_left_ret, "inflation_rate_pa": default_inflation_rate_pa},
                        "formatted_string" # Or "projected_future_cost"
                    )
                    if fv_data_ret: fv_string_ret = str(fv_data_ret)

                processed_goals_list.append({
                    "goal_name": goal_name_ret if retirement_goal_from_future_plans else "Client Retirement",
                    "goal_type": "Retirement",
                    "target_year": target_year_ret,
                    "time_remaining_years": time_left_ret,
                    "estimated_current_cost_input": cost_now_ret,
                    "assumed_inflation_rate_pa_for_fv": default_inflation_rate_pa if cost_now_ret else None,
                    "estimated_future_cost_string": fv_string_ret,
                })
            else:
                 print(f"--- [ComprehensiveGoalProcessingTool] Could not determine time_left_ret for retirement. Skipping explicit future_plans retirement goal. ---")

        elif years_to_retirement_from_profile is not None : # Default retirement goal if not in future_plans
            processed_goals_list.append({
                "goal_name": "Client Retirement", "goal_type": "Retirement",
                "target_year": current_year + years_to_retirement_from_profile,
                "time_remaining_years": years_to_retirement_from_profile,
                "estimated_current_cost_input": None, # No current cost given for default retirement
                "assumed_inflation_rate_pa_for_fv": None,
                "estimated_future_cost_string": None, # Calculated by RetirementPlannerAgent
            })
        else:
            print("--- [ComprehensiveGoalProcessingTool] No explicit retirement goal in future_plans AND years_to_retirement not in profile. Cannot create default retirement goal. ---")


        # 2. Other Stated Goals from `future_plans`
        print("--- [ComprehensiveGoalProcessingTool] Processing Other Stated Goals from future_plans ---")
        # future_plans_data is now expected to be snake_cased by JsonSnakeCaseConverterTool
        # e.g., {"coast_retirement": {...}, "sibling_wedding": {...}}
        # OR {"assets": {"emergency_funds": ...}, "coast_retirement": ...} from Harish's original data
        
        # Handle the nested "assets" structure for emergency_funds if present
        assets_in_future_plans = future_plans_data.get("assets", {})
        if isinstance(assets_in_future_plans, dict):
            for goal_name_snake_case, goal_detail_dict in assets_in_future_plans.items():
                 if isinstance(goal_detail_dict, dict):
                    print(f"--- [ComprehensiveGoalProcessingTool] Processing other goal from future_plans.assets: {goal_name_snake_case} ---")
                    # goal_name_snake_case is already snake_case from converter tool if it was a key
                    
                    time_left_raw = _parse_value_flexible(goal_detail_dict.get("time_years"))
                    if time_left_raw is None: time_left_raw = _parse_value_flexible(goal_detail_dict.get("time"))
                    
                    cost_now_raw = _parse_value_flexible(goal_detail_dict.get("amount_required_today"))
                    # inflation_raw = _parse_value_flexible(goal_detail_dict.get("goal_inflation", default_inflation_rate_pa))

                    time_left = int(time_left_raw) if isinstance(time_left_raw, (int, float)) else None
                    cost_now = float(cost_now_raw) if isinstance(cost_now_raw, (int, float)) else None
                    # inflation_other = float(inflation_raw) if isinstance(inflation_raw, (int,float)) else default_inflation_rate_pa

                    if time_left is not None:
                        actual_target_year = current_year + time_left
                        fv_string_other = None
                        if cost_now is not None:
                            # Using default_inflation_rate_pa for these simpler goals unless specified otherwise in data
                            fv_data_other = run_goal_mcp_and_extract(
                                "project_future_cost",
                                {"current_cost": cost_now, "number_of_years": time_left, "inflation_rate_pa": default_inflation_rate_pa},
                                "formatted_string"
                            )
                            if fv_data_other: fv_string_other = str(fv_data_other)
                        
                        processed_goals_list.append({
                            "goal_name": goal_name_snake_case.replace('_', ' ').title(), # Prettify for display later
                            "goal_type": "Other_" + goal_name_snake_case, # Use snake_case for type consistency
                            "target_year": actual_target_year,
                            "time_remaining_years": time_left,
                            "estimated_current_cost_input": cost_now,
                            "assumed_inflation_rate_pa_for_fv": default_inflation_rate_pa if cost_now else None,
                            "estimated_future_cost_string": fv_string_other,
                        })
                    else:
                        print(f"--- [ComprehensiveGoalProcessingTool] Skipping '{goal_name_snake_case}' (from future_plans.assets) due to missing time_left. ---")


        # Process other direct keys in future_plans_data (excluding 'assets' if handled above)
        for goal_name_snake_case, goal_detail_dict in future_plans_data.items():
            if goal_name_snake_case == "assets": continue # Already processed
            if "retirement" in goal_name_snake_case: continue # Already processed

            if isinstance(goal_detail_dict, dict):
                print(f"--- [ComprehensiveGoalProcessingTool] Processing other goal from future_plans: {goal_name_snake_case} ---")

                time_left_raw = _parse_value_flexible(goal_detail_dict.get("time_years"))
                if time_left_raw is None: time_left_raw = _parse_value_flexible(goal_detail_dict.get("time")) # Fallback
                
                cost_now_raw = _parse_value_flexible(goal_detail_dict.get("amount_required_today"))
                # inflation_raw = _parse_value_flexible(goal_detail_dict.get("goal_inflation", default_inflation_rate_pa))

                time_left = int(time_left_raw) if isinstance(time_left_raw, (int, float)) else None
                cost_now = float(cost_now_raw) if isinstance(cost_now_raw, (int, float)) else None
                # inflation_other = float(inflation_raw) if isinstance(inflation_raw, (int,float)) else default_inflation_rate_pa

                if time_left is not None:
                    actual_target_year = current_year + time_left
                    fv_string_other = None
                    if cost_now is not None:
                        fv_data_other = run_goal_mcp_and_extract(
                            "project_future_cost",
                            {"current_cost": cost_now, "number_of_years": time_left, "inflation_rate_pa": default_inflation_rate_pa}, # Using default inflation here
                            "formatted_string"
                        )
                        if fv_data_other: fv_string_other = str(fv_data_other)
                    
                    processed_goals_list.append({
                        "goal_name": goal_name_snake_case.replace('_', ' ').title(),
                        "goal_type": "Other_" + goal_name_snake_case,
                        "target_year": actual_target_year,
                        "time_remaining_years": time_left,
                        "estimated_current_cost_input": cost_now,
                        "assumed_inflation_rate_pa_for_fv": default_inflation_rate_pa if cost_now else None,
                        "estimated_future_cost_string": fv_string_other,
                    })
                else:
                    print(f"--- [ComprehensiveGoalProcessingTool] Skipping '{goal_name_snake_case}' (from future_plans) due to missing time_left. ---")

        # Convert to FinancialGoal Pydantic models for validation and consistent structure
        final_goal_objects_as_dicts = []
        for goal_dict_raw in processed_goals_list:
            # Ensure all required fields for FinancialGoal are present or provide defaults
            # FinancialGoal model requires: goal_name, goal_type, target_year, time_remaining_years
            goal_dict = goal_dict_raw.copy() # Work with a copy
            goal_dict.setdefault("estimated_current_cost_input", None)
            goal_dict.setdefault("assumed_inflation_rate_pa_for_fv", None)
            goal_dict.setdefault("estimated_future_cost_string", None)
            goal_dict.setdefault("priority", None)
            goal_dict.setdefault("feasibility_notes", None)

            if not all(k in goal_dict and goal_dict[k] is not None for k in ["goal_name", "goal_type", "target_year", "time_remaining_years"]):
                print(f"--- [ComprehensiveGoalProcessingTool] WARNING: Skipping goal due to missing core fields before Pydantic: {goal_dict.get('goal_name')}. Data: {goal_dict} ---")
                continue
            try:
                validated_goal = FinancialGoal(**goal_dict)
                final_goal_objects_as_dicts.append(validated_goal.model_dump(exclude_none=True))
            except Exception as e_pydantic:
                print(f"--- [ComprehensiveGoalProcessingTool] ERROR: Pydantic validation failed for goal '{goal_dict.get('goal_name')}': {e_pydantic}. Data: {goal_dict} ---")
        
        # Sort goals (example: by target_year, then by a predefined type priority)
        def sort_key(goal_item): # goal_item is now a dict
            type_priority_map = {"Retirement": 1, "Education_UG": 2, "Education_PG": 3} # Example
            return (goal_item.get("target_year", float('inf')), 
                    type_priority_map.get(goal_item.get("goal_type"), 99))

        final_goal_objects_as_dicts.sort(key=sort_key)

        output_payload = {"quantified_financial_goals": final_goal_objects_as_dicts}
        output_json_str = json.dumps(output_payload, indent=2)
        print(f"--- [ComprehensiveGoalProcessingTool] Completed. Output preview: {output_json_str[:500]}... ---")
        return output_json_str

    except json.JSONDecodeError as e_initial_parse:
        error_message = f"COMPREHENSIVE_GOAL_PROCESSING_TOOL_ERROR: Initial JSONDecodeError for client_data_json: {type(e_initial_parse).__name__} - {str(e_initial_parse)}. Input: {client_data_json[:200]}..."
        print(f"--- [ComprehensiveGoalProcessingTool] {error_message} ---")
        # import traceback # Already imported if this is in the same file as the tool decorator
        return json.dumps({"error": error_message, "details": "Traceback omitted for brevity in error JSON, check logs."})
    except Exception as e_general:
        error_message = f"COMPREHENSIVE_GOAL_PROCESSING_TOOL_ERROR: General error: {type(e_general).__name__} - {str(e_general)}"
        print(f"--- [ComprehensiveGoalProcessingTool] {error_message} ---")
        import traceback # Ensure traceback is imported for this block
        return json.dumps({"error": error_message, "details": traceback.format_exc()})
################################################# Tool for Agent 5 : GoalSettingMCPTool Done #################################################








########################################################################################################################################################################################
                                                                       # Merge Tool
########################################################################################################################################################################################

# @tool("ClientDataMergeTool")
# def client_data_merge_tool(initial_client_data_json: str,
#                            client_profile_calculations_json: Optional[str] = None,
#                            asset_liability_analysis_json: Optional[str] = None,
#                            financial_goals_json: Optional[str] = None,
#                            retirement_plan_json: Optional[str] = None,
#                            education_plans_json: Optional[str] = None,
#                            debt_management_plan_json: Optional[str] = None,
#                            financial_health_audit_json: Optional[str] = None
#                            ) -> str:
#     """
#     Merges various analysis JSON strings into a single, comprehensive FullClientData JSON string.
#     It starts with initial_client_data_json (which should represent the current state of FullClientData)
#     and progressively adds other analysis parts provided as arguments.
#     All input JSON strings and output FJSON string keys must be snake_case.

#     Args:
#         initial_client_data_json (str): JSON string for the base FullClientData (often from previous agent's output).
#         client_profile_calculations_json (Optional[str]): JSON string for ClientProfileCalculations.
#         asset_liability_analysis_json (Optional[str]): JSON string for AssetLiabilityAnalysis.
#         financial_goals_json (Optional[str]): JSON string for a list of FinancialGoal objects.
#         retirement_plan_json (Optional[str]): JSON string for RetirementPlan.
#         education_plans_json (Optional[str]): JSON string for a list of EducationPlan objects.
#         debt_management_plan_json (Optional[str]): JSON string for DebtManagementPlan.
#         financial_health_audit_json (Optional[str]): JSON string for FinancialHealthAudit.

#     Returns:
#         str: A JSON string representing the fully assembled/updated FullClientData object.
#     """
#     print("--- [ClientDataMergeTool] Starting merge ---")
#     current_full_data_dict = {}
#     try:
#         # Load the base data (current state of FullClientData)
#         current_full_data_dict = json.loads(initial_client_data_json)
#         # Create a FullClientData object from it to work with Pydantic models conveniently
#         # This also validates the incoming 'current state'
#         full_data_obj = FullClientData(**current_full_data_dict)

#         # Merge Client Profile Calculations
#         if client_profile_calculations_json and client_profile_calculations_json.strip():
#             print("--- [ClientDataMergeTool] Merging Client Profile Calculations ---")
#             profile_calcs_dict = json.loads(client_profile_calculations_json)
#             if not profile_calcs_dict.get("error"):
#                 full_data_obj.client_profile = ClientProfile(
#                     current_client_age=profile_calcs_dict.get("current_client_age"),
#                     years_to_retirement=profile_calcs_dict.get("years_to_retirement"),
#                     retirement_horizon_classification=profile_calcs_dict.get("retirement_horizon_classification"),
#                     equity_exposure_status=profile_calcs_dict.get("equity_exposure_status"),
#                     risk_appetite=profile_calcs_dict.get("risk_appetite")
#                 )
#                 children_calcs_list = profile_calcs_dict.get("children_education_profiles_calculations", [])
#                 full_data_obj.children_education_profiles_calculations = [
#                     ChildTimelineProfile(**child_data) for child_data in children_calcs_list
#                 ]
#             else:
#                 print(f"--- [ClientDataMergeTool] Error in client_profile_calculations_json: {profile_calcs_dict.get('error')}. Skipping profile merge. ---")
        
#         # Merge Asset Liability Analysis
#         if asset_liability_analysis_json and asset_liability_analysis_json.strip():
#             print("--- [ClientDataMergeTool] Merging Asset Liability Analysis ---")
#             ala_dict = json.loads(asset_liability_analysis_json)
#             if not ala_dict.get("error"): # Check if the analysis tool itself reported an error
#                 full_data_obj.asset_liability_analysis = AssetLiabilityAnalysis(**ala_dict)
#             else:
#                 print(f"--- [ClientDataMergeTool] Error in asset_liability_analysis_json: {ala_dict.get('error')}. Skipping ALA merge. ---")

#         # Merge Financial Goals
#         if financial_goals_json and financial_goals_json.strip():
#             print("--- [ClientDataMergeTool] Merging Financial Goals ---")
#             goals_list_of_dicts = json.loads(financial_goals_json)
#             if isinstance(goals_list_of_dicts, list): # Ensure it's a list before iterating
#                 full_data_obj.financial_goals = [FinancialGoal(**goal_data) for goal_data in goals_list_of_dicts]
#             else: # Handle if financial_goals_json was not a list of goals (e.g., an error object itself)
#                 print(f"--- [ClientDataMergeTool] Financial goals JSON was not a list: {goals_list_of_dicts}. Skipping financial goals merge. ---")
#                 if isinstance(goals_list_of_dicts, dict) and goals_list_of_dicts.get("error"):
#                      print(f"--- [ClientDataMergeTool] Error in financial_goals_json: {goals_list_of_dicts.get('error')}. Skipping goals merge. ---")


#         # Merge Retirement Plan
#         if retirement_plan_json and retirement_plan_json.strip():
#             print("--- [ClientDataMergeTool] Merging Retirement Plan ---")
#             rp_dict = json.loads(retirement_plan_json)
#             if not rp_dict.get("error"):
#                 full_data_obj.retirement_plan = RetirementPlan(**rp_dict)
#             else:
#                  print(f"--- [ClientDataMergeTool] Error in retirement_plan_json: {rp_dict.get('error')}. Skipping retirement plan merge. ---")

#         # Merge Education Plans
#         if education_plans_json and education_plans_json.strip():
#             print("--- [ClientDataMergeTool] Merging Education Plans ---")
#             edu_list_of_dicts = json.loads(education_plans_json)
#             if isinstance(edu_list_of_dicts, list):
#                 full_data_obj.education_plans = [EducationPlan(**edu_data) for edu_data in edu_list_of_dicts]
#             else:
#                 print(f"--- [ClientDataMergeTool] Education plans JSON was not a list: {edu_list_of_dicts}. Skipping education plans merge. ---")
#                 if isinstance(edu_list_of_dicts, dict) and edu_list_of_dicts.get("error"):
#                      print(f"--- [ClientDataMergeTool] Error in education_plans_json: {edu_list_of_dicts.get('error')}. Skipping education plans merge. ---")


#         # Merge Debt Management Plan
#         if debt_management_plan_json and debt_management_plan_json.strip():
#             print("--- [ClientDataMergeTool] Merging Debt Management Plan ---")
#             dmp_dict = json.loads(debt_management_plan_json)
#             if not dmp_dict.get("error"):
#                 full_data_obj.debt_management_plan = DebtManagementPlan(**dmp_dict)
#             else:
#                 print(f"--- [ClientDataMergeTool] Error in debt_management_plan_json: {dmp_dict.get('error')}. Skipping DMP merge. ---")
            
#         # Merge Financial Health Audit
#         if financial_health_audit_json and financial_health_audit_json.strip():
#             print("--- [ClientDataMergeTool] Merging Financial Health Audit ---")
#             fha_dict = json.loads(financial_health_audit_json)
#             if not fha_dict.get("error"):
#                 full_data_obj.financial_health_audit = FinancialHealthAudit(**fha_dict)
#             else:
#                 print(f"--- [ClientDataMergeTool] Error in financial_health_audit_json: {fha_dict.get('error')}. Skipping FHA merge. ---")

#         merged_json = full_data_obj.model_dump_json(indent=2, exclude_none=True) # exclude_none helps keep output clean
#         print(f"--- [ClientDataMergeTool] Merge complete. Output preview: {merged_json[:500]}... ---")
#         return merged_json

#     except json.JSONDecodeError as e:
#         error_msg = f"MERGE_TOOL_JSON_ERROR: Failed to parse input JSON. Initial_data: '{initial_client_data_json[:100]}...'. Error: {type(e).__name__} - {str(e)}"
#         print(f"--- [ClientDataMergeTool] {error_msg} ---")
#         # Return original data if base parsing fails, or a structured error
#         if current_full_data_dict: # If initial_client_data_json was parsed
#             current_full_data_dict["merge_tool_error"] = error_msg
#             return json.dumps(current_full_data_dict)
#         return json.dumps({"error_in_merge_tool": error_msg, "details": traceback.format_exc()})
#     except Exception as e: # Catch other Pydantic validation errors or unexpected errors
#         error_msg = f"MERGE_TOOL_UNEXPECTED_ERROR: {type(e).__name__} - {str(e)}"
#         print(f"--- [ClientDataMergeTool] {error_msg} ---")
#         import traceback
#         # Return original data if base parsing fails, or a structured error
#         if current_full_data_dict:
#             current_full_data_dict["merge_tool_error"] = error_msg
#             return json.dumps(current_full_data_dict)
#         return json.dumps({"error_in_merge_tool": error_msg, "details": traceback.format_exc()})
    

@tool("ClientDataMergeTool")
def client_data_merge_tool(initial_client_data_json: str,
                           client_profile_calculations_json: Optional[str] = None,
                           asset_liability_analysis_json: Optional[str] = None,
                           financial_goals_json: Optional[str] = None, # This should be a JSON string of a LIST of FinancialGoal dicts
                           retirement_plan_json: Optional[str] = None,
                           education_plans_json: Optional[str] = None, # This should be a JSON string of a LIST of EducationPlan dicts
                           debt_management_plan_json: Optional[str] = None,
                           financial_health_audit_json: Optional[str] = None
                           ) -> str:
    """
    Merges various analysis JSON strings into a single, comprehensive FullClientData JSON string.
    It starts with initial_client_data_json (which should represent the current state of FullClientData)
    and progressively adds other analysis parts provided as arguments.
    All input JSON strings are expected to contain snake_case keys, and the output JSON string
    will also have snake_case keys, conforming to the FullClientData Pydantic model.

    Args:
        initial_client_data_json (str): JSON string for the base FullClientData. This is required.
        client_profile_calculations_json (Optional[str]): JSON string for ClientProfileCalculations.
        asset_liability_analysis_json (Optional[str]): JSON string for AssetLiabilityAnalysis.
        financial_goals_json (Optional[str]): JSON string representing a LIST of FinancialGoal objects (e.g., '[{...}, {...}]').
        retirement_plan_json (Optional[str]): JSON string for RetirementPlan.
        education_plans_json (Optional[str]): JSON string representing a LIST of EducationPlan objects (e.g., '[{...}, {...}]').
        debt_management_plan_json (Optional[str]): JSON string for DebtManagementPlan.
        financial_health_audit_json (Optional[str]): JSON string for FinancialHealthAudit.

    Returns:
        str: A JSON string representing the fully assembled/updated FullClientData Pydantic object.
             Returns a JSON string with an 'error_in_merge_tool' key if a critical error occurs.
    """
    print(f"--- [ClientDataMergeTool] Starting merge. Input initial_client_data_json snippet: {initial_client_data_json[:200]}... ---")
    
    # Attempt to load the initial base data. If this fails, we can't proceed.
    try:
        base_data_dict = json.loads(initial_client_data_json)
        # Initialize FullClientData object from the base data. This also validates the base structure.
        full_data_obj = FullClientData(**base_data_dict)
    except json.JSONDecodeError as e:
        error_msg = f"CRITICAL_MERGE_TOOL_ERROR: Failed to parse 'initial_client_data_json'. Details: {type(e).__name__} - {str(e)}. Input snippet: {initial_client_data_json[:200]}"
        print(f"--- [ClientDataMergeTool] {error_msg} ---")
        return json.dumps({"error_in_merge_tool": error_msg, "details": traceback.format_exc()})
    except Exception as e_pydantic_base: # Catch Pydantic validation errors for base data
        error_msg = f"CRITICAL_MERGE_TOOL_ERROR: Failed to initialize FullClientData from 'initial_client_data_json'. Pydantic Error: {type(e_pydantic_base).__name__} - {str(e_pydantic_base)}."
        print(f"--- [ClientDataMergeTool] {error_msg} ---")
        return json.dumps({"error_in_merge_tool": error_msg, "details": traceback.format_exc()})

    # Helper function to safely parse and assign a section
    def _safe_parse_and_assign(json_str: Optional[str], attribute_name: str, target_model: Any, is_list: bool = False):
        if json_str and json_str.strip() and json_str.lower() != 'null':
            print(f"--- [ClientDataMergeTool] Attempting to merge '{attribute_name}' ---")
            try:
                data_dict_or_list = json.loads(json_str)
                if isinstance(data_dict_or_list, dict) and data_dict_or_list.get("error"):
                    print(f"--- [ClientDataMergeTool] Info: '{attribute_name}' JSON contained an error key: {data_dict_or_list['error']}. Skipping merge for this section. ---")
                    # Optionally, you could store this error in the full_data_obj if it has an error field
                    # For now, we just skip merging this erroneous section.
                    return

                if is_list:
                    if isinstance(data_dict_or_list, list):
                        setattr(full_data_obj, attribute_name, [target_model(**item) for item in data_dict_or_list])
                        print(f"--- [ClientDataMergeTool] Successfully merged list for '{attribute_name}' ---")
                    else:
                        print(f"--- [ClientDataMergeTool] WARNING: Expected a list for '{attribute_name}' but got {type(data_dict_or_list)}. Skipping merge. Data: {str(data_dict_or_list)[:100]} ---")
                else: # Is a single object
                    if isinstance(data_dict_or_list, dict):
                        setattr(full_data_obj, attribute_name, target_model(**data_dict_or_list))
                        print(f"--- [ClientDataMergeTool] Successfully merged object for '{attribute_name}' ---")
                    else:
                        print(f"--- [ClientDataMergeTool] WARNING: Expected a dictionary for '{attribute_name}' but got {type(data_dict_or_list)}. Skipping merge. Data: {str(data_dict_or_list)[:100]} ---")
            
            except json.JSONDecodeError as e:
                print(f"--- [ClientDataMergeTool] JSON_PARSE_ERROR for '{attribute_name}': {type(e).__name__} - {str(e)}. Skipping merge for this section. JSON string snippet: {json_str[:100]}... ---")
            except Exception as e_pydantic: # Catches Pydantic validation errors for the specific section
                print(f"--- [ClientDataMergeTool] PYDANTIC_VALIDATION_ERROR for '{attribute_name}': {type(e_pydantic).__name__} - {str(e_pydantic)}. Skipping merge. Data: {str(data_dict_or_list)[:100]}... ---")
        else:
            print(f"--- [ClientDataMergeTool] Info: No data or 'null' string provided for '{attribute_name}'. Skipping. ---")

    # Merge Client Profile Calculations
    # Note: client_profile_calculations_json is for ClientProfileCalculations, which then populates two fields in FullClientData
    if client_profile_calculations_json and client_profile_calculations_json.strip() and client_profile_calculations_json.lower() != 'null':
        print("--- [ClientDataMergeTool] Attempting to merge 'client_profile_calculations' ---")
        try:
            profile_calcs_dict = json.loads(client_profile_calculations_json)
            if not profile_calcs_dict.get("error"):
                # Populate client_profile (which is a ClientProfile object)
                full_data_obj.client_profile = ClientProfile(
                    current_client_age=profile_calcs_dict.get("current_client_age"),
                    years_to_retirement=profile_calcs_dict.get("years_to_retirement"),
                    retirement_horizon_classification=profile_calcs_dict.get("retirement_horizon_classification"),
                    equity_exposure_status=profile_calcs_dict.get("equity_exposure_status"),
                    risk_appetite=profile_calcs_dict.get("risk_appetite")
                )
                # Populate children_education_profiles_calculations (which is a List[ChildTimelineProfile])
                children_calcs_list = profile_calcs_dict.get("children_education_profiles_calculations", [])
                if isinstance(children_calcs_list, list):
                    full_data_obj.children_education_profiles_calculations = [
                        ChildTimelineProfile(**child_data) for child_data in children_calcs_list
                    ]
                else:
                    print(f"--- [ClientDataMergeTool] WARNING: 'children_education_profiles_calculations' within client_profile_calculations_json was not a list. Skipping. ---")
                print(f"--- [ClientDataMergeTool] Successfully merged 'client_profile' and 'children_education_profiles_calculations' ---")
            else:
                print(f"--- [ClientDataMergeTool] Info: 'client_profile_calculations_json' contained an error key: {profile_calcs_dict['error']}. Skipping its merge. ---")
        except json.JSONDecodeError as e:
            print(f"--- [ClientDataMergeTool] JSON_PARSE_ERROR for 'client_profile_calculations_json': {type(e).__name__} - {str(e)}. Skipping. JSON: {client_profile_calculations_json[:100]}... ---")
        except Exception as e_pydantic:
            print(f"--- [ClientDataMergeTool] PYDANTIC_VALIDATION_ERROR for 'client_profile_calculations': {type(e_pydantic).__name__} - {str(e_pydantic)}. Skipping. ---")
            
    # Merge other sections using the helper
    _safe_parse_and_assign(asset_liability_analysis_json, "asset_liability_analysis", AssetLiabilityAnalysis)
    _safe_parse_and_assign(financial_goals_json, "financial_goals", FinancialGoal, is_list=True)
    _safe_parse_and_assign(retirement_plan_json, "retirement_plan", RetirementPlan)
    _safe_parse_and_assign(education_plans_json, "education_plans", EducationPlan, is_list=True)
    _safe_parse_and_assign(debt_management_plan_json, "debt_management_plan", DebtManagementPlan)
    _safe_parse_and_assign(financial_health_audit_json, "financial_health_audit", FinancialHealthAudit)

    try:
        merged_json_output = full_data_obj.model_dump_json(indent=2, exclude_none=True)
        print(f"--- [ClientDataMergeTool] Merge process complete. Final output preview: {merged_json_output[:500]}... ---")
        return merged_json_output
    except Exception as e_dump: # Should be rare if Pydantic instantiation succeeded
        error_msg = f"MERGE_TOOL_FINAL_DUMP_ERROR: Error dumping final FullClientData object: {type(e_dump).__name__} - {str(e_dump)}"
        print(f"--- [ClientDataMergeTool] {error_msg} ---")
        return json.dumps({"error_in_merge_tool": error_msg, "details": traceback.format_exc()})

