# testing.py
from custom_tool import financial_analysis_mcp_tool # This now refers to the Tool object

if __name__ == "__main__":
    print("Testing calculate_age_difference...")
    result1_args = {"current_age": 30, "target_age_for_goal": 50}
    # Call the .run() method of the Tool object, passing arguments as keyword arguments
    # or as a single dictionary if the tool's run method expects that.
    # For tools decorated with @tool, it expects keyword arguments matching the Pydantic model.
    output1 = financial_analysis_mcp_tool.run(
        operation_name="calculate_age_difference", 
        arguments=result1_args
    )
    print(f"Input: operation_name='calculate_age_difference', arguments={result1_args}")
    print(f"Output: {output1}") 
    print("-" * 30)

    print("Testing project_goal_future_value...")
    result2_args = {"present_value": 100000.0, "annual_inflation_rate": 0.05, "number_of_years": 10}
    output2 = financial_analysis_mcp_tool.run(
        operation_name="project_goal_future_value", 
        arguments=result2_args
    )
    print(f"Input: operation_name='project_goal_future_value', arguments={result2_args}")
    print(f"Output: {output2}") 
    print("-" * 30)

    print("Testing calculate_child_current_age...")
    result3_args = {"child_dob_str": "2010-05-15", "current_date_str": "2024-07-28"}
    output3 = financial_analysis_mcp_tool.run(
        operation_name="calculate_child_current_age", 
        arguments=result3_args
    )
    print(f"Input: operation_name='calculate_child_current_age', arguments={result3_args}")
    print(f"Output: {output3}") 
    print("-" * 30)

    print("Testing non-existent tool...")
    result4_args = {"some_arg": 1}
    output4 = financial_analysis_mcp_tool.run(
        operation_name="non_existent_tool_on_server", 
        arguments=result4_args
    )
    print(f"Input: operation_name='non_existent_tool_on_server', arguments={result4_args}")
    print(f"Output: {output4}") 
    print("-" * 30)

    print("Testing with incorrect arguments...")
    result5_args = {"current_age_WRONG_NAME": 30, "target_age_for_goal": 50}
    output5 = financial_analysis_mcp_tool.run(
        operation_name="calculate_age_difference", 
        arguments=result5_args
    )
    print(f"Input: operation_name='calculate_age_difference', arguments={result5_args}")
    print(f"Output: {output5}")
    print("-" * 30)