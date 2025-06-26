# src/armstrong/crew.py
# This is the complete, final, and clean implementation of the "Smart Sequential" workflow.
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from typing import List
import os
import litellm
from dotenv import load_dotenv

os.environ["OPEN_API_KEY"]=os.getenv("OPEN_API_KEY")
load_dotenv()
#from crewai import OpenAICrewLLM

# ======================================================================================
# SECTION 1: IMPORTS
# This section imports all necessary Pydantic models and tools.
# ======================================================================================
# from .models import (
#     # The main state model that will be passed between tasks
#     FullClientData,
    
#     # The initial data model for the first task's output
#     InitialClientData,
    
#     # Intermediate models for multi-step "assembly line" tasks
#     TimelineCalculations,
#     RiskCalculations,
#     GoalCalculationOutput,
    
#     # Final data structure models for each analysis section
#     ClientProfile,
#     AssetLiabilityAnalysis,
#     FinancialGoal,
#     RetirementPlan,
#     EducationPlan,
#     DebtManagementPlan,
#     FinancialHealthAudit
# )
# from armstrong.tools.mcp_clients import (
#     client_profiler_tool,
#     asset_liability_analysis_mcp_tool,
#     goal_setting_mcp_tool,
#     financial_analysis_mcp_tool,
# )
# from armstrong.tools.custom_tool import (comprehensive_profile_calculator_tool,
#                                          client_data_merge_tool)

litellm.api_key=os.getenv("OPEN_API_KEY")

from .models import (
    FullClientData,
    InitialClientData,
    ClientProfileCalculations, 
    GoalCalculatorOutput,   
    AssetLiabilityAnalysis,    
    GoalCalculatorOutput,        
    FinancialGoal,  
    ClientProfile,
    AssetLiabilityAnalysis,
    FinancialGoal, 
    RetirementPlan,
    EducationPlan,
    DebtManagementPlan,
    FinancialHealthAudit,
    QuantifiedGoalsOutput,
)

from armstrong.tools.custom_tool import (
    comprehensive_profile_calculator_tool,
    comprehensive_asset_liability_analysis_tool, 
    client_data_merge_tool,
    comprehensive_goal_processing_tool,
    json_snake_case_converter_tool
)

from armstrong.tools.mcp_clients import (
    asset_liability_analysis_mcp_tool, 
    goal_setting_mcp_tool,
    financial_analysis_mcp_tool,
)

# ======================================================================================
# SECTION 2: SETUP
# ======================================================================================

Openai_llm = LLM(model="openai/gpt-4o", api_key=os.getenv("OPEN_API_KEY"))

@CrewBase
class Armstrong():
    """Armstrong crew orchestrating a smart sequential financial planning process."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # ======================================================================================
    # SECTION 3: AGENT DEFINITIONS
    # Each agent is defined here with its specific role, goal, and tools.
    # ======================================================================================

    @agent
    def data_extractor(self) -> Agent:
        return Agent(config=self.agents_config['data_extractor'], 
                     verbose=True, 
                     llm=Openai_llm,
                     tools=[json_snake_case_converter_tool]
                     )

    @agent
    def ClientProfilerAgent(self) -> Agent:
        return Agent(
            config=self.agents_config['ClientProfilerAgent'],
            verbose=True,
            llm=Openai_llm,
            tools=[comprehensive_profile_calculator_tool,
                   client_data_merge_tool]
        )

    @agent
    def AssetLiabilityAnalyzerAgent(self) -> Agent:
        return Agent(config=self.agents_config['AssetLiabilityAnalyzerAgent'], 
                     verbose=True, 
                     llm=Openai_llm, 
                     tools=[comprehensive_asset_liability_analysis_tool,
                            client_data_merge_tool])

    @agent
    def goal_quantification_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['goal_quantification_agent'],
            tools=[
                comprehensive_goal_processing_tool,
                goal_setting_mcp_tool # If it needs to make individual calls for fuzzy "other" goals
            ],
            llm=Openai_llm,
            verbose=True
        )

    @agent
    def goal_strategy_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['goal_strategy_agent'],
            tools=[
                client_data_merge_tool,
                # financial_analysis_mcp_tool # If it needs to calculate SIPs for feasibility
            ],
            llm=Openai_llm,
            verbose=True
        )

    @agent
    def RetirementPlannerAgent(self) -> Agent:
        return Agent(config=self.agents_config['RetirementPlannerAgent'], verbose=True, llm=Openai_llm, tools=[financial_analysis_mcp_tool])

    @agent
    def EducationPlannerAgent(self) -> Agent:
        return Agent(config=self.agents_config['EducationPlannerAgent'], verbose=True, llm=Openai_llm, tools=[financial_analysis_mcp_tool])

    @agent
    def DebtManagerAgent(self) -> Agent:
        return Agent(config=self.agents_config['DebtManagerAgent'], verbose=True, llm=Openai_llm, tools=[financial_analysis_mcp_tool])

    @agent
    def FinancialHealthAuditorAgent(self) -> Agent:
        return Agent(config=self.agents_config['FinancialHealthAuditorAgent'], verbose=True, llm=Openai_llm, tools=[financial_analysis_mcp_tool])

    @agent
    def ReportGeneratorAgent(self) -> Agent:
        return Agent(config=self.agents_config['ReportGeneratorAgent'], verbose=True, llm=Openai_llm)

    # ======================================================================================
    # SECTION 4: TASK DEFINITIONS
    # Each task is assigned an agent and has a Pydantic output contract to ensure
    # the reliable passing of state through the sequential process.
    # ======================================================================================

    @task
    def data_extraction_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_extraction_task'],
            agent=self.data_extractor(),
            output_pydantic=InitialClientData,
            output_file="outputs/data_extraction_task.json" 
        )

    # We are back to ONE profiling task.
    @task
    def client_profiling_task(self) -> Task:
        return Task(
            config=self.tasks_config['client_profiling_task'],
            agent=self.ClientProfilerAgent(),
            context=[self.data_extraction_task()],
            output_pydantic=FullClientData,
            output_file="outputs/client_profiling_task.json" 
        )
    
    @task
    def asset_liability_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['asset_liability_analysis_task'],
            agent=self.AssetLiabilityAnalyzerAgent(),
            context=[self.client_profiling_task()],
            output_pydantic=FullClientData,
            output_file="outputs/asset_liability_analysis_task.json"
        )

    @task
    def goal_quantification_task(self) -> Task:
        return Task(
            config=self.tasks_config['goal_quantification_task'],
            agent=self.goal_quantification_agent(),
            context=[self.asset_liability_analysis_task()], # Needs FullClientData up to ALA
            output_pydantic=QuantifiedGoalsOutput # This task outputs the list of quantified goals
        )

    @task
    def goal_strategy_and_integration_task(self) -> Task:
        return Task(
            config=self.tasks_config['goal_strategy_and_integration_task'],
            agent=self.goal_strategy_agent(),
            context=[
                self.asset_liability_analysis_task(), # Provides the base FullClientData (up to ALA)
                self.goal_quantification_task()       # Provides QuantifiedGoalsOutput
            ],
            output_pydantic=FullClientData # This task integrates goals into FullClientData
        )

    @task
    def retirement_planning_task(self) -> Task:
        return Task(
            config=self.tasks_config['retirement_planning_task'],
            agent=self.RetirementPlannerAgent(),
            context=[self.goal_strategy_and_integration_task()],
            output_pydantic=FullClientData
        )

    @task
    def education_planning_task(self) -> Task:
        return Task(
            config=self.tasks_config['education_planning_task'],
            agent=self.EducationPlannerAgent(),
            context=[self.retirement_planning_task()],
            output_pydantic=FullClientData
        )

    @task
    def debt_management_task(self) -> Task:
        return Task(
            config=self.tasks_config['debt_management_task'],
            agent=self.DebtManagerAgent(),
            context=[self.education_planning_task()],
            output_pydantic=FullClientData
        )

    @task
    def financial_health_audit_task(self) -> Task:
        return Task(
            config=self.tasks_config['financial_health_audit_task'],
            agent=self.FinancialHealthAuditorAgent(),
            context=[self.debt_management_task()],
            output_pydantic=FullClientData
        )

    @task
    def report_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config['report_generation_task'],
            agent=self.ReportGeneratorAgent(),
            context=[self.financial_health_audit_task()],
            output_file='final_financial_plan_report.md'  
        )

    # ======================================================================================
    # SECTION 5: CREW DEFINITION
    # This defines the exact sequential order of the "Assembly Line".
    # ======================================================================================
    @crew
    def crew(self) -> Crew:
        """Defines the sequential assembly line for financial planning."""
        return Crew(
            agents=self.agents,
            tasks=[
                self.data_extraction_task(),
                self.client_profiling_task(),
                self.asset_liability_analysis_task(),
                self.goal_quantification_task(),           
                self.goal_strategy_and_integration_task(), 
                self.retirement_planning_task(),
                self.education_planning_task(),
                self.debt_management_task(),
                self.financial_health_audit_task(),
                self.report_generation_task()
            ],
            process=Process.sequential,
            memory=False,
            verbose=True
        )
    