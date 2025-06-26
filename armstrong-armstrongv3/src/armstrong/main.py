#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from armstrong.crew import Armstrong
import fitz

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from dotenv import load_dotenv
load_dotenv()

# input_sheet = """

# #### Personal Information
# - **Name:** Rohit Bagwe
# - **Date of Birth:** 1985-07-25
# - **Year of Birth:** 1985
# - **Retirement Age:** 55
# - **Current Year:** 2023

# #### Family Information
# - **Spouse Year of Birth:** 1985
# - **First Child - Kahira Year of Birth:** 2018
# - **Second Child - Ahira Year of Birth:** 2019
# - **Third Child - Hira Year of Birth:** 2020

# #### Expenses
# - **Household Expenses (Monthly):** 60,000

# #### Assets
# - **Provident Fund (PF):** Present Values not specified
# - **Public Provident Fund (PPF):** Present Values not specified
# - **Fixed Deposit (FD):** Present Value: 100,000
# - **Direct Equity (Company Stocks):** Present Value: 18,081,260
# - **Real Estate:**
#   - Residential House: 10,000,000
#   - Flat: 3,000,000
#   - Flat 2: 15,000,000
# - **Cash or Cash at Bank:** 200,000

# #### Liabilities
# - **Home Loan:**
#   - Outstanding Amount: 6,500,000
#   - Interest Rate: 0.085
#   - EMI Amount: 59,500
# - **Car Loan:**
#   - Outstanding Amount: 700,000
#   - Interest Rate: 0.085
#   - EMI Amount: 11,100
# - **Personal Loan:**
#   - Outstanding Amount: 0
#   - Interest Rate: 0
#   - EMI Amount: 0

# #### Future Plans
# - **First Child - Kahira:**
#   - Expected Current Cost for Undergraduate (UG): 4,000,000
#   - Expected Current Cost for Postgraduate (PG): 5,000,000

# #### Miscellaneous
# - **Miscellaneous Expenditure/Vacation Current Cost:** Not specified

# """

os.environ["OPEN_API_KEY"]=os.getenv("OPEN_API_KEY")

input_sheet = """

### Summary of 'Input Sheet'

#### Personal Information
- **Name:** Jallaluddin Khan
- **Date of Birth:** 1994-11-17
- **Year of Birth:** 1994
- **Retirement Age:** 45
- **Year of Birth - Spouse:** 1993
- **Current Year:** 2023

# #### Family Information
# - **first Child - Naveen , Year of Birth:** 2019
# - **second Child - Hiren , Year of Birth:** 2020

#### Expenses
- **Household Expenses (Monthly):** 110,000.00

#### Assets
- **Provident Fund (PF):**
  - Present Values: 628,729.00
  - Monthly Contribution: 25,800.00
- **Public Provident Fund (PPF):**
  - Present Values: 451,600.00
  - Monthly Contribution: 3,600.00
- **Fixed Deposit (FD):**
  - Present Values: 300,000.00
- **Direct Equity:**
  - Present Values: 26,936.00
- **Mutual Funds:**
  - Present Values: 525,794.00
- **Cash or Cash at Bank:** 277,800.00
- **Gold ETF:** 2,500.00
- **Crypto:** 50,000.00
- **Other Investments (Ornamental Gold):** 250,000.00

#### Liabilities
- **Car Loan:**
  - Outstanding Amount: 213,000.00
  - Interest Rate: 0.12
  - EMI Amount: 17,800.00
  - Tenure: 12 months, ending in 2024
- **Personal Loan:**
  - Outstanding Amount: 467,150.00
  - Interest Rate: 0.10
  - EMI Amount: 24,500.00
  - Tenure: 19 months, ending in 2025

  ### Financial Goals

#### Assets
- **Emergency Funds**
  - Time: 1 year
  - Amount Required (Today): 600,000
  - Amount Available (Today): 600,000

#### Future Plans
- **Coast Retirement**
  - Time: 10 years
  - Amount Required (Today): 38,000,000
  # #### Future Plans
# - **First Child - Naveen:**
#   - Expected Current Cost for Undergraduate (UG): 4,000,000
#   - Expected Current Cost for Postgraduate (PG): 5,000,000

- **Sibling Wedding**
  - Time: 5 years
  - Amount Required (Today): 1,500,000

- **Higher Education**
  - Time: 3 years
  - Amount Required (Today): 10,000,000

- **Home Loan Down Payment**
  - Time: 10 years
  - Amount Required (Today): 5,000,000

- **Vacations**
  - Time: 1 year
  - Amount Required (Today): 500,000

- **Car**
  - Time: 4 years
  - Amount Required (Today): 4,500,000
  - Amount Available (Today): 0

- **Electronic Gadget / Clothes**
  - Time: 1 year
  - Amount Required (Today): 200,000
  - Amount Available (Today): 0

- **Car 2**
  - Time: 10 years
  - Amount Required (Today): 10,000,000
  - Amount Available (Today): 0

- **Car 3**
  - Time: 12 years
  - Amount Required (Today): 50,000,000
  - Amount Available (Today): 0


"""

def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return full_text

# Usage
pdf_path = "C:/Users/Aakash/Projects/Armstrong/armstrong-v3/armstrong-armstrongv3/armstrong-armstrongv3/General_Logic_Framework.pdf"
Logic_Framework = extract_pdf_text(pdf_path)

# def run():
#     """
#     Run the crew.
#     """
#     inputs = {
#         # 'topic': 'AI LLMs',
#         # 'current_year': str(datetime.now().year),
#         'input_sheet': input_sheet,
#         'framework_logic_content': Logic_Framework
#     }
    
#     try:
#         Armstrong().crew().kickoff(inputs=inputs)
#     except Exception as e:
#         raise Exception(f"An error occurred while running the crew: {e}")



# def run():
#     """
#     Run the crew.
#     """
#     inputs = {
#         'input_sheet': input_sheet,
#         'framework_logic_content': Logic_Framework
#     }
    
#     armstrong_crew_instance = Armstrong().crew() # Get the crew instance

#     try:
#         print("\n--- STARTING CREW EXECUTION ---\n")
#         crew_result = armstrong_crew_instance.kickoff(inputs=inputs)
#         print("\n--- CREW EXECUTION FINISHED ---\n")

#         # --- DEBUGGING: Inspecting Task Outputs ---
#         if crew_result and hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
#             print("\n\n======= DETAILED TASK OUTPUTS (from main.py) =======")
#             for i, task_output_obj in enumerate(crew_result.tasks_output):
#                 task_name = armstrong_crew_instance.tasks[i].description[:50] + "..." # Get task description
#                 agent_name = armstrong_crew_instance.tasks[i].agent.role if armstrong_crew_instance.tasks[i].agent else "Unknown Agent"

#                 print(f"\n----- Task {i+1}: {task_name} -----")
#                 print(f"----- Agent: {agent_name} -----")

#                 # Raw output string from the agent (what it actually said)
#                 print("\n  --- Agent's Raw Output String ---")
#                 print(task_output_obj.raw) # This is crucial for JSONDecodeError

#                 #Exported output (what CrewAI passes as context if output_pydantic is used)
#                 #This should be a clean JSON string representation of the Pydantic model instance
#                 print("\n  --- Exported Output (Context for Next Task / Pydantic Validated) ---")
#                 if task_output_obj.exported_output:
#                     print(task_output_obj.exported_output)
#                     # Try to parse and pretty print for readability
#                     try:
#                         parsed_exported_output = json.loads(task_output_obj.exported_output)
#                         print("\n  --- (Pretty Printed Exported Output) ---")
#                         print(json.dumps(parsed_exported_output, indent=2))
#                     except json.JSONDecodeError as e:
#                         print(f"    Error: Could not parse exported_output as JSON: {e}")
#                     except TypeError as e: # If exported_output is not a string
#                         print(f"    Info: exported_output is not a string (type: {type(task_output_obj.exported_output)}), cannot parse as JSON directly.") 
#         else:
#           print("    No exported_output available (task might have failed or not used output_pydantic).")
                
#           if task_output_obj.error:
#             print(f"\n  --- Task Error ---")
#             print(task_output_obj.error)
#             print("----- End of Task Output -----")
#             print("====================================================\n\n")

#         #Print the final result of the crew (usually the output of the last task)
#         if crew_result:
#             print("\n\n=== FINAL CREW RESULT (from main.py) ===\n\n")
#             # Depending on how CrewAI structures the final result, you might use .raw or another attribute
#             if hasattr(crew_result, 'raw') and crew_result.raw:
#                  print(crew_result.raw)
#             elif hasattr(crew_result, 'exported_output') and crew_result.exported_output: # if last task had pydantic
#                  print(crew_result.exported_output)
#             else:
#                 print(crew_result) # Fallback to printing the whole object

#     except Exception as e:
#         import traceback
#         print(f"\n\n!!! AN EXCEPTION OCCURRED DURING CREW KICKOFF in main.py !!!")
#         print(f"Error Type: {type(e).__name__}")
#         print(f"Error Message: {e}")
#         print("Traceback:")
#         traceback.print_exc()
#         # Re-raise if you want the script to exit with an error code
#         # raise Exception(f"An error occurred while running the crew: {e}")

def run():
    """
    Run the crew.
    """
    inputs = {
        'input_sheet': input_sheet,
        'framework_logic_content': Logic_Framework
    }
    
    armstrong_crew_instance = Armstrong().crew()  # Get the crew instance

    try:
        print("\n--- STARTING CREW EXECUTION ---\n")
        crew_result = armstrong_crew_instance.kickoff(inputs=inputs)
        print("\n--- CREW EXECUTION FINISHED ---\n")

        # --- DEBUGGING: Inspecting Task Outputs ---
        if crew_result and getattr(crew_result, 'tasks_output', None):
            print("\n\n======= DETAILED TASK OUTPUTS (from main.py) =======")
            for i, task_output_obj in enumerate(crew_result.tasks_output):
                task = armstrong_crew_instance.tasks[i]
                task_name  = task.description[:50] + "..."
                agent_name = task.agent.role if task.agent else "Unknown Agent"

                print(f"\n----- Task {i+1}: {task_name} -----")
                print(f"Agent: {agent_name}\n")

                # 1) Raw
                print("  --- Raw Output ---")
                print(task_output_obj.raw)

                # 2) Structured JSON
                print("\n  --- JSON‐Structured Output (if available) ---")
                if getattr(task_output_obj, 'output_json', None):
                    raw_json = task_output_obj.output_json
                    print(raw_json)
                    try:
                        parsed = json.loads(raw_json)
                        print(json.dumps(parsed, indent=2))
                    except Exception as e:
                        print(f"    (Could not parse JSON: {e})")

                elif getattr(task_output_obj, 'output_pydantic', None):
                    print(task_output_obj.output_pydantic.json())

                else:
                    print("    (no structured output; falling back to raw above)")

                # 3) Any error
                if getattr(task_output_obj, 'error', None):
                    print("\n  --- Task Error ---")
                    print(task_output_obj.error)

                print("----- End of Task Output -----")
            print("\n====================================================\n")

        else:
            print("No task outputs to display (crew_result.tasks_output is empty or missing).")

        # --- Print final result ---
        if crew_result:
            print("\n\n=== FINAL CREW RESULT ===\n")
            if getattr(crew_result, 'output_json', None):
                print(crew_result.output_json)
            elif getattr(crew_result, 'output_pydantic', None):
                print(crew_result.output_pydantic.json())
            elif getattr(crew_result, 'raw', None):
                print(crew_result.raw)
            else:
                print(crew_result)
            print("\nReport should have been saved to output/ directory if specified in the last task.")
        else:
            print("Crew execution did not produce a result object.")

    except Exception as e:
        import traceback
        print(f"\n\n!!! AN EXCEPTION OCCURRED DURING CREW KICKOFF in main.py !!!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    run()