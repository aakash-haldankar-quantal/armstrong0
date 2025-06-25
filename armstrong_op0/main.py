#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from crew import ArmstrongOp0

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

from helper_functions import (analyze_assets_for_recommendations, apply_recommendations, derive_financials,
                        analyze_investment_maturities, build_asset_basket,
                        emi_payment_advisor, update_asset_basket_with_surplus_usage,
                        loan_liability_summary, compute_surplus_usage, sort_goals,
                        generate_liquidation_plan, update_asset_basket_sorted,
                        compute_surplus_after_assets, sort_assets_by_liquidity_with_surplus
                        )
import json

client_data={
  "profile": {
    "name": "John Doe",
    "date_of_birth": "1980-01-01",
    "retirement_age": 60,
    "current_year": 2025,
    "occupation": "Software Engineer",
    "marital_status": "Married",
    "family": {
      "spouses": [
        { "name": "Jane Doe",   "year_of_birth": 1982 },
        { "name": "Alexis Doe", "year_of_birth": 1985 }
      ],
      "children": [
        { "name": "Alice", "year_of_birth": 2012 },
        { "name": "Bob",   "year_of_birth": 2016 }
      ],
      "dependents": [
        { "name": "Father", "relationship": "father", "year_of_birth": 1950 }
      ]
    }
  }, 
  "financials": {
    "monthly_income": 200000,
    "current_monthly_savings": 43000,
    "expenses": [
      { "type": "monthly_household", "amount": 75000 },
      { "type": "monthly_travel", "amount": 12000 },
      { "type": "monthly_emergency","amount": 5000  },
      { "type": "monthly_saving",    "amount": 65000 }
    ],
    "assets": [
      {
        "type": "provident_fund",
        "present_value": 1200000,
        "expected_annual_return": 0.08,
        "duration_years": 15,
        "years_since": 7,
        "convertible":True,
        "monthly_add":2000
      },
      {
        "type": "public_provident_fund",
        "present_value": 800000,
        "expected_annual_return": 0.075,
        "duration_years": 15,
        "years_since": 7,
        "convertible":True,
        "monthly_add":2000
      },
      {
        "type": "fixed_deposit",
        "present_value": 250000,
        "expected_annual_return": 0.065,
        "duration_years": 10,
        "years_since": 7,
        "convertible":True,
        "monthly_add":2000
      },
      {
        "type": "lic_policy",
        "present_value": 500000,
        "expected_annual_return": 0.06,
        "duration_years": 20,
        "years_since": 7,
        "convertible":False,
        "monthly_add":2000
      },
      {
        "type": "mutual_fund",
        "present_value": 700000,
        "expected_annual_return": 0.12,
        "duration_years": 12,
        "years_since": 7,
        "convertible":True,
        "monthly_add":2000
      },
      {
        "type": "direct_equity",
        "present_value": 2000000,
        "expected_annual_return": 0.15,
        "duration_years": None,
        "years_since": None,
        "convertible":True,
        "monthly_add":2000
      },
      {
        "type": "real_estate",
        "properties": [
          {
            "name": "Primary Residence",
            "value": 10000000,
            "location": "Mumbai",
            "expected_annual_return": 0.06,
            "duration_years": None,
            "years_since": None,
            "convertible":True,
            "monthly_add":None
          },
          {
            "name": "Rental Apartment",
            "value": 4500000,
            "location": "Pune",
            "expected_annual_return": 0.055,
            "duration_years": None,
            "years_since": None,
            "convertible": False,
            "monthly_add":None
          }
        ]
      },
      {
        "type": "cash",
        "present_value": 300000,
        "expected_annual_return": 0.03,
        "duration_years": 0,
        "years_since": None,
        "convertible":True,
        "monthly_add":2000
      }
    ],
    "liabilities": [
      {
        "type": "home_loan",
        "outstanding_amount": 4000000,
        "annual_interest_rate": 0.075,
        "emi": 35000,
        "lender": "HDFC Bank"
      },
      {
        "type": "car_loan",
        "outstanding_amount": 800000,
        "annual_interest_rate": 0.09,
        "emi": 15000,
        "lender": "ICICI Bank"
      },
      {
        "type": "personal_loan",
        "outstanding_amount": 200000,
        "annual_interest_rate": 0.12,
        "emi": 5000,
        "lender": "Bajaj Finance"
      }
    ]
  },
  "goals": {
    "education": [
      {
        "beneficiary": "Alice",
        "levels": {
          "undergraduate": 1000000,
          "postgraduate": 1500000
        }
      },
      {
        "beneficiary": "Bob",
        "levels": {
          "undergraduate": 1200000,
          "postgraduate": 1800000
        }
      }
    ],
    "retirement": {
      "target_age": 60,
      "target_corpus": 50000000,
      "monthly_post_retirement_expense": 60000
    },
    "vacations": [
      { "year": 2026, "estimated_cost": 300000, "location": "Europe" },
      { "year": 2028, "estimated_cost": 200000, "location": "Japan" }
    ],
    "custom_goals": [
      { "name": "Start Business", "year": 2030, "required_funds": 10000000 },
      { "name": "Buy Farmhouse",  "year": 2035, "required_funds": 15000000 }
    ]
  }
}

recs = analyze_assets_for_recommendations(client_data)
#print(json.dumps(recs, indent=2))

updated_client_data = apply_recommendations(client_data, recs)
#print(json.dumps(updated_client_data, indent=2))

derived = derive_financials(updated_client_data)
#print(json.dumps(derived, indent=2))

mature_data = analyze_investment_maturities(updated_client_data)
#print(json.dumps(mature_data, indent=2))

derived_data=derived

basket = build_asset_basket(updated_client_data, derived_data, mature_data)
#print(json.dumps(basket, indent=2))
basket=sort_assets_by_liquidity_with_surplus(basket)

recommendation = emi_payment_advisor(updated_client_data, derived_data)
#print(recommendation)

loan_detail=loan_liability_summary(updated_client_data)
#print(loan_detail)

if recommendation['assets_used']==0:
    updated_asset_basket=update_asset_basket_with_surplus_usage(recommendation, basket)
    #print(updated_asset_basket)
    
    surplus_usage=compute_surplus_usage(recommendation, loan_detail)
    #print(surplus_usage)
    
    assets=updated_asset_basket

else:
    liquidation_plan=generate_liquidation_plan(recommendation, basket, loan_detail)
    #print(liquidation_plan)
    
    updated_basket = update_asset_basket_sorted(basket, liquidation_plan)
    #print(updated_basket)
    
    surplus_available=compute_surplus_after_assets(recommendation, loan_detail)
    #print([surplus_available])
    
    assets=updated_basket

def run():
    """
    Run the crew.
    """
    inputs = {
        "client_data": client_data,
        'recommended_action': recommendation, 
        'recs': recs,
        'asset': basket,
        'derived_data':derived_data,
        'loan_detail':loan_detail,
        'liquidation_plan':liquidation_plan,
        'updated_asset':assets,
        'surplus_data':surplus_available
    }
    
    try:
        #ArmstrongOp0().crew().kickoff(inputs=inputs)
        armstrong=ArmstrongOp0()
        crew=armstrong.crew()
        crew_result=crew.kickoff(inputs=inputs)
        
        #client_investments_analyzer_agent_task_op=armstrong.client_investments_analyzer_agent_task()
        #client_investmensts_explainer_task_op=armstrong.client_investmensts_explainer_task()
        
        return crew_result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

output=run()
# import json
# print(output)

# for task_out in output.tasks_output:
#     if task_out.name == "client_financial_planner_task":
#         print(task_out.raw)
        # or, if you want JSON:
        #print(json.loads(task_out.raw))

# def train():
#     """
#     Train the crew for a given number of iterations.
#     """
#     inputs = {
#         "client_data": client_data,
#         'recommended_action': recommended_action
#     }
#     try:
#         ArmstrongOp0().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

#     except Exception as e:
#         raise Exception(f"An error occurred while training the crew: {e}")

# def replay():
#     """
#     Replay the crew execution from a specific task.
#     """
#     try:
#         ArmstrongOp0().crew().replay(task_id=sys.argv[1])

#     except Exception as e:
#         raise Exception(f"An error occurred while replaying the crew: {e}")

# def test():
#     """
#     Test the crew execution and returns the results.
#     """
#     inputs = {
#         "topic": "AI LLMs",
#         "current_year": str(datetime.now().year)
#     }
    
#     try:
#         ArmstrongOp0().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

#     except Exception as e:
#         raise Exception(f"An error occurred while testing the crew: {e}")
