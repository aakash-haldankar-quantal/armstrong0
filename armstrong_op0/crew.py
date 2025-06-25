from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os                                                                                                                                                                                                          
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
load_dotenv()

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

llm = LLM(
model="openai/gpt-4",
temperature=0.1,
api_key=os.getenv("OPEN_API_KEY")
)

@CrewBase
class ArmstrongOp0():
    """ArmstrongOp0 crew"""

    agents: List[BaseAgent]
    tasks: List[Task]
    
    

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def client_investments_analyzer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['client_investments_analyzer_agent'], # type: ignore[index]
            verbose=True,
            llm=llm
        )
    
    @agent
    def client_investmensts_explainer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['client_investmensts_explainer_agent'], # type: ignore[index]
            verbose=True,
            llm=llm
        )
    
    # @agent
    # def liquidity_sorter_agent(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['liquidity_sorter_agent'], # type: ignore[index]
    #         verbose=True,
    #         llm=llm
    #     )
    
    @agent
    def client_analysis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['client_analysis_agent'], # type: ignore[index]
            verbose=True,
            llm=llm
        )
    
    @agent
    def loan_liquidation_plan_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['loan_liquidation_plan_agent'], # type: ignore[index]
            verbose=True,
            llm=llm
        )
    
    @agent
    def client_financial_planner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['client_financial_planner_agent'], # type: ignore[index]
            verbose=True,
            llm=llm
        )
    
    @task
    def client_investments_analyzer_agent_task(self) -> Task:
        return Task(
            config=self.tasks_config['client_investments_analyzer_agent_task'], # type: ignore[index]
        )
    
    @task
    def client_investmensts_explainer_task(self) -> Task:
        return Task(
            config=self.tasks_config['client_investmensts_explainer_task'], # type: ignore[index]
        )
    
    @task
    def client_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['client_analysis_task'], # type: ignore[index]
        )
    
    @task
    def loan_liquidation_plan_task(self) -> Task:
        return Task(
            config=self.tasks_config['loan_liquidation_plan_task'], # type: ignore[index]
        )
    
    @task
    def client_financial_planner_task(self) -> Task:
        return Task(
            config=self.tasks_config['client_financial_planner_task'], # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ArmstrongOp0 crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
