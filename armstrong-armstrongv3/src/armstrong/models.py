# # src/armstrong/models.py
# # This file defines the complete data contracts for the entire financial planning crew.
# # It uses a separate InitialClientData model to prevent the first agent from hallucinating,
# # and includes all intermediate and final Pydantic models required for the full workflow.

# from pydantic import BaseModel, Field
# from typing import List, Dict, Any, Optional

# # =====================================================================================
# # SECTION 1: INTERMEDIATE MODELS FOR MULTI-STEP "ASSEMBLY LINE" TASKS
# # =====================================================================================

# class ChildTimelineProfile(BaseModel):
#     child_identifier: str
#     child_current_age: int
#     ug_years_to_goal: int
#     ug_horizon_classification: str
#     pg_years_to_goal: Optional[int] = None
#     pg_horizon_classification: Optional[str] = None

# class TimelineCalculations(BaseModel):
#     """The output from the TimelineCalculatorAgent (Agent 2a)."""
#     current_client_age: int
#     years_to_retirement: int
#     retirement_horizon_classification: str
#     children_timelines: List[ChildTimelineProfile]

# class RiskCalculations(BaseModel):
#     """The output from the RiskCalculatorAgent (Agent 2b)."""
#     equity_exposure_status: str
#     risk_appetite: str

# class ClientProfileCalculations(BaseModel):
#     current_client_age: Optional[int] = None
#     years_to_retirement: Optional[int] = None
#     retirement_horizon_classification: Optional[str] = None
#     equity_exposure_status: Optional[str] = None
#     risk_appetite: Optional[str] = None
#     children_education_profiles_calculations: List[ChildTimelineProfile] = Field(default_factory=list)

# class FinancialGoal(BaseModel):
#     """Represents a single, fully defined financial goal. Used by Goal agents."""
#     goal_name: str
#     goal_type: str
#     target_year: int
#     time_remaining_years: int
#     estimated_current_cost_input: Optional[float] = None
#     assumed_inflation_rate_pa_for_fv: Optional[float] = None
#     estimated_future_cost_string: Optional[str] = None

# class GoalCalculationOutput(BaseModel):
#     """The intermediate output from the GoalCalculatorAgent."""
#     calculated_goals: List[FinancialGoal]


# # =====================================================================================
# # SECTION 2: FINAL AUGMENTATION MODELS
# # =====================================================================================

# class ClientProfile(BaseModel):
#     current_client_age: Optional[int] = None
#     years_to_retirement: Optional[int] = None
#     retirement_horizon_classification: Optional[str] = None
#     equity_exposure_status: Optional[str] = None
#     risk_appetite: Optional[str] = None

# class AssetClassificationSummary(BaseModel):
#     """Summary of assets classified into predefined buckets."""
#     liquid_assets: float = Field(default=0.0)
#     retirement_assets: float = Field(default=0.0)
#     fixed_assets: float = Field(default=0.0)

# class IndividualAssetProportion(BaseModel):
#     """Value and proportion of a single original asset category."""
#     asset_category: str
#     value: float
#     proportion_percentage: float

# class AssetLiabilityAnalysis(BaseModel):
#     """The complete analysis of assets and liabilities."""
#     total_asset_value_numeric: float
#     total_liabilities_value_numeric: float
#     net_worth_numeric: float
#     asset_classification_summary: AssetClassificationSummary
#     asset_bucket_proportions: Dict[str, float]
#     individual_asset_proportions: List[IndividualAssetProportion]

# class RetirementPlanAssumptions(BaseModel):
#     """Assumptions made during retirement planning."""
#     client_current_annual_expenses_assumed: float
#     expense_replacement_ratio_in_retirement_assumed_percent: float
#     years_to_retirement_used: int
#     retirement_duration_years_assumed: int
#     pre_retirement_inflation_rate_pa_assumed_percent: float
#     post_retirement_inflation_rate_pa_assumed_percent: float
#     post_retirement_expected_investment_return_rate_pa_assumed_percent: float
#     expected_annual_growth_rate_pa_on_existing_assets_percent: float
#     expected_annual_investment_return_rate_pa_on_new_savings_percent: float

# class StepUpSavingsProjection(BaseModel):
#     """Details of the step-up savings projection."""
#     chosen_annual_step_up_percentage: float
#     projected_corpus_with_step_up: str
#     notes_on_step_up_feasibility: str

# class RetirementPlan(BaseModel):
#     """The complete, calculated retirement plan."""
#     estimated_required_corpus_at_retirement: str
#     projected_fv_of_existing_retirement_assets: str
#     retirement_gap_value: str
#     retirement_goal_feasibility_rating: str
#     required_additional_monthly_sip_no_step_up: str
#     assumptions: RetirementPlanAssumptions
#     step_up_savings_projection: Optional[StepUpSavingsProjection] = None
#     key_recommendations_for_retirement: List[str]

# class EducationPlanAssumptions(BaseModel):
#     """Assumptions made for a single education plan."""
#     assumed_current_annual_cost_base: float
#     cost_base_description: str
#     assumed_annual_inflation_rate_pa_percent: float
#     assumed_course_duration_years: int
#     expected_annual_growth_rate_on_savings_percent: float

# class EducationPlanDetail(BaseModel):
#     """A detailed plan for a single education goal (e.g., UG or PG)."""
#     goal_level: str
#     target_start_age: int
#     years_left_to_start: int
#     determined_education_type: str
#     assumptions: EducationPlanAssumptions
#     projected_future_total_cost_for_duration: str
#     fv_of_existing_dedicated_savings: str
#     additional_total_corpus_needed: str
#     required_additional_monthly_sip_for_this_goal: str
#     funding_and_priority_notes: str

# class EducationPlan(BaseModel):
#     """A comprehensive education plan for one child."""
#     child_identifier: str
#     education_goals_details: List[EducationPlanDetail]

# class DebtOverview(BaseModel):
#     """Details of a single active loan."""
#     loan_type: str
#     outstanding_balance: float
#     interest_rate_pa_percent: float
#     current_emi: float

# class HomeLoanTaxAnalysis(BaseModel):
#     """Analysis of tax benefits from a home loan."""
#     notes_on_tax_impact_of_prepayment: str

# class DebtManagementPlan(BaseModel):
#     """The complete debt management strategy."""
#     debt_overview: List[DebtOverview]
#     prioritized_repayment_strategy: Dict[str, str]
#     liquidity_assessment_for_repayment: Dict[str, str]
#     home_loan_prepayment_analysis_if_applicable: Optional[HomeLoanTaxAnalysis] = None
#     recommended_prepayment_options: Dict[str, str]
#     overall_debt_strategy_recommendations_summary: List[str]

# class FinancialHealthParameter(BaseModel):
#     """Represents a single parameter in the financial health audit table."""
#     parameter_name: str
#     value_and_diagnosis: str
#     remark_actionable: str

# class FinancialHealthAudit(BaseModel):
#     """The complete financial health audit."""
#     key_financial_parameters: List[FinancialHealthParameter]
#     overall_financial_health_summary_paragraph: str

# # =====================================================================================
# # SECTION 3: THE MAIN STATE MODELS
# # =====================================================================================

# class InitialClientData(BaseModel):
#     personal_information: Dict[str, Any] = Field(default_factory=dict)
#     family_information: Dict[str, Any] = Field(default_factory=dict)
#     expenses: Dict[str, Any] = Field(default_factory=dict)
#     assets: List[Dict[str, Any]] = Field(default_factory=list)
#     liabilities: Dict[str, Any] = Field(default_factory=dict)
#     future_plans: Dict[str, Any] = Field(default_factory=dict)
#     miscellaneous: Dict[str, Any] = Field(default_factory=dict)

# class FullClientData(InitialClientData):
#     client_profile: Optional[ClientProfile] = None
#     children_education_profiles_calculations: Optional[List[ChildTimelineProfile]] = Field(default_factory=list)
#     asset_liability_analysis: Optional[AssetLiabilityAnalysis] = None
#     financial_goals: Optional[List[FinancialGoal]] = None
#     retirement_plan: Optional[RetirementPlan] = None
#     education_plans: Optional[List[EducationPlan]] = None
#     debt_management_plan: Optional[DebtManagementPlan] = None
#     financial_health_audit: Optional[FinancialHealthAudit] = None

#     # Helper method to update with profile calculations - makes agent's job easier
#     def update_with_profile_calculations(self, profile_calcs: ClientProfileCalculations):
#         self.client_profile = ClientProfile(
#             current_client_age=profile_calcs.current_client_age,
#             years_to_retirement=profile_calcs.years_to_retirement,
#             retirement_horizon_classification=profile_calcs.retirement_horizon_classification,
#             equity_exposure_status=profile_calcs.equity_exposure_status,
#             risk_appetite=profile_calcs.risk_appetite
#         )
#         self.children_education_profiles_calculations = profile_calcs.children_education_profiles_calculations
#         return self











# src/armstrong/models.py
# This file defines the complete data contracts for the entire financial planning crew.
# All field names are in snake_case for consistency and Pythonic style.

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

# =====================================================================================
# SECTION 1: INTERMEDIATE MODELS FOR TOOL OUTPUTS / SPECIALIZED AGENT TASKS
# =====================================================================================

class ChildTimelineProfile(BaseModel):
    """Holds the calculated timeline data for a single child's education."""
    child_identifier: str
    child_current_age: int
    ug_years_to_goal: int
    ug_horizon_classification: str
    pg_years_to_goal: Optional[int] = None
    pg_horizon_classification: Optional[str] = None

class ClientProfileCalculations(BaseModel):
    """
    The specific output from the `ComprehensiveProfileCalculatorTool`.
    This data will be used to populate parts of `FullClientData`.
    """
    current_client_age: Optional[int] = None
    years_to_retirement: Optional[int] = None
    retirement_horizon_classification: Optional[str] = None
    equity_exposure_status: Optional[str] = None
    risk_appetite: Optional[str] = None
    children_education_profiles_calculations: List[ChildTimelineProfile] = Field(default_factory=list)

class FinancialGoal(BaseModel):
    """Represents a single, fully defined financial goal."""
    goal_name: str
    goal_type: str
    target_year: int
    time_remaining_years: int # This was missing from your snippet but used by the tool
    estimated_current_cost_input: Optional[float] = None
    assumed_inflation_rate_pa_for_fv: Optional[float] = None
    estimated_future_cost_string: Optional[str] = None
    priority: Optional[str] = Field(None, description="Priority of the goal, e.g., Critical, Important, Aspirational.")
    feasibility_notes: Optional[str] = Field(None, description="Notes on the feasibility of achieving this goal.")

class GoalCalculatorOutput(BaseModel): # Renamed from GoalCalculationOutput if you prefer
    """The intermediate output from the GoalCalculatorAgent's specialized task."""
    calculated_goals: List[FinancialGoal] = Field(default_factory=list)

class QuantifiedGoalsOutput(BaseModel):
    quantified_financial_goals: List[FinancialGoal] = Field(default_factory=list)

# =====================================================================================
# SECTION 2: MODELS FOR FullClientData SECTIONS
# =====================================================================================

class ClientProfile(BaseModel):
    """The client's core profile information within FullClientData."""
    current_client_age: Optional[int] = None
    years_to_retirement: Optional[int] = None
    retirement_horizon_classification: Optional[str] = None
    equity_exposure_status: Optional[str] = None
    risk_appetite: Optional[str] = None

class AssetClassificationSummary(BaseModel):
    """Summary of assets classified into predefined buckets."""
    liquid_assets: float = Field(default=0.0) # Changed to snake_case
    retirement_assets: float = Field(default=0.0) # Changed to snake_case
    fixed_assets: float = Field(default=0.0) # Changed to snake_case

class IndividualAssetProportion(BaseModel):
    """Value and proportion of a single original asset category."""
    asset_category: str
    value: float
    proportion_percentage: float

class AssetLiabilityAnalysis(BaseModel):
    """The complete analysis of assets and liabilities section in FullClientData."""
    total_asset_value_numeric: float
    total_liabilities_value_numeric: float
    net_worth_numeric: float
    asset_classification_summary: AssetClassificationSummary # This will now use the snake_case version
    asset_bucket_proportions: Dict[str, float] # Keys should be snake_case e.g. "liquid_assets"
    individual_asset_proportions: List[IndividualAssetProportion]

class RetirementPlanAssumptions(BaseModel):
    """Assumptions made during retirement planning."""
    client_current_annual_expenses_assumed: float
    expense_replacement_ratio_in_retirement_assumed_percent: float
    years_to_retirement_used: int
    retirement_duration_years_assumed: int
    pre_retirement_inflation_rate_pa_assumed_percent: float
    post_retirement_inflation_rate_pa_assumed_percent: float
    post_retirement_expected_investment_return_rate_pa_assumed_percent: float
    expected_annual_growth_rate_pa_on_existing_assets_percent: float
    expected_annual_investment_return_rate_pa_on_new_savings_percent: float

class StepUpSavingsProjection(BaseModel):
    """Details of the step-up savings projection."""
    chosen_annual_step_up_percentage: float
    projected_corpus_with_step_up: str
    notes_on_step_up_feasibility: str

class RetirementPlan(BaseModel):
    """The complete, calculated retirement plan section in FullClientData."""
    estimated_required_corpus_at_retirement: str
    projected_fv_of_existing_retirement_assets: str
    retirement_gap_value: str
    retirement_goal_feasibility_rating: str
    required_additional_monthly_sip_no_step_up: str
    assumptions: RetirementPlanAssumptions
    step_up_savings_projection: Optional[StepUpSavingsProjection] = None
    key_recommendations_for_retirement: List[str]

class EducationPlanAssumptions(BaseModel):
    """Assumptions made for a single education plan."""
    assumed_current_annual_cost_base: float
    cost_base_description: str
    assumed_annual_inflation_rate_pa_percent: float
    assumed_course_duration_years: int
    expected_annual_growth_rate_on_savings_percent: float

class EducationPlanDetail(BaseModel):
    """A detailed plan for a single education goal (e.g., UG or PG)."""
    goal_level: str
    target_start_age: int
    years_left_to_start: int
    determined_education_type: str
    assumptions: EducationPlanAssumptions
    projected_future_total_cost_for_duration: str
    fv_of_existing_dedicated_savings: str
    additional_total_corpus_needed: str
    required_additional_monthly_sip_for_this_goal: str
    funding_and_priority_notes: str

class EducationPlan(BaseModel):
    """A comprehensive education plan for one child section in FullClientData."""
    child_identifier: str
    education_goals_details: List[EducationPlanDetail]

class DebtOverview(BaseModel):
    """Details of a single active loan."""
    loan_type: str
    outstanding_balance: float
    interest_rate_pa_percent: float
    current_emi: float

class HomeLoanTaxAnalysis(BaseModel):
    """Analysis of tax benefits from a home loan."""
    notes_on_tax_impact_of_prepayment: str

class DebtManagementPlan(BaseModel):
    """The complete debt management strategy section in FullClientData."""
    debt_overview: List[DebtOverview]
    prioritized_repayment_strategy: Dict[str, str]
    liquidity_assessment_for_repayment: Dict[str, str]
    home_loan_prepayment_analysis_if_applicable: Optional[HomeLoanTaxAnalysis] = None
    recommended_prepayment_options: Dict[str, str]
    overall_debt_strategy_recommendations_summary: List[str]

class FinancialHealthParameter(BaseModel):
    """Represents a single parameter in the financial health audit table."""
    parameter_name: str
    value_and_diagnosis: str
    remark_actionable: str

class FinancialHealthAudit(BaseModel):
    """The complete financial health audit section in FullClientData."""
    key_financial_parameters: List[FinancialHealthParameter]
    overall_financial_health_summary_paragraph: str

# =====================================================================================
# SECTION 3: THE MAIN STATE MODELS
# =====================================================================================

class InitialClientData(BaseModel):
    """
    Represents raw data extracted from the input sheet by the first agent.
    All field names MUST be snake_case.
    Internal dictionary keys (e.g. within personal_information) MUST also be snake_case.
    """
    personal_information: Dict[str, Any] = Field(default_factory=dict)
    family_information: Dict[str, Any] = Field(default_factory=dict)
    expenses: Dict[str, Any] = Field(default_factory=dict)
    assets: List[Dict[str, Any]] = Field(default_factory=list) # Each dict: {"asset_name": "...", "present_value": ...}
    liabilities: Dict[str, Any] = Field(default_factory=dict)  # e.g. {"home_loan": {"outstanding_amount": ...}}
    future_plans: Dict[str, Any] = Field(default_factory=dict)
    miscellaneous: Dict[str, Any] = Field(default_factory=dict)

class FullClientData(InitialClientData):
    """
    The main state model that is passed between all specialist agents and progressively augmented.
    It inherits all snake_case fields from InitialClientData.
    All new analytical fields added here are also snake_case and Optional.
    """
    client_profile: Optional[ClientProfile] = None
    children_education_profiles_calculations: Optional[List[ChildTimelineProfile]] = Field(default_factory=list)
    
    asset_liability_analysis: Optional[AssetLiabilityAnalysis] = None
    financial_goals: Optional[List[FinancialGoal]] = None
    retirement_plan: Optional[RetirementPlan] = None
    education_plans: Optional[List[EducationPlan]] = None
    debt_management_plan: Optional[DebtManagementPlan] = None
    financial_health_audit: Optional[FinancialHealthAudit] = None

    # Removed the helper method `update_with_profile_calculations` as the
    # `ClientDataMergeTool` will handle merging from JSON strings into Pydantic objects.
    # Keeping Pydantic models as pure data structures is generally cleaner.

