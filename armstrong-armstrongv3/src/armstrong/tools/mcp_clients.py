import os
import sys
import asyncio
import json
import re
from crewai.tools import tool
from typing import Dict, Any, Optional, List, Union
from mcp import ClientSession, StdioServerParameters, types as mcp_types
from mcp.client.stdio import stdio_client

MODULE_LEVEL_SERVER_SCRIPT_NAME = "mcp_server_tools.py" 

######################################################### General Tool #########################################################

@tool("FinancialAnalysisMCPTool")
def financial_analysis_mcp_tool(operation_name: str, arguments: Dict[str, Any]) -> str:
    """
    Accesses a Client Profiler MCP server to perform calculations.
    ... (rest of your detailed docstring - ensure it's accurate!) ...
    """

    
    server_script_to_use = MODULE_LEVEL_SERVER_SCRIPT_NAME

    async def _run_mcp_async(op_name: str, args_dict: Dict[str, Any]) -> str:
        current_tool_file_dir = os.path.dirname(os.path.abspath(__file__))
        script_to_run_final = os.path.join(current_tool_file_dir, server_script_to_use) 

        if not os.path.exists(script_to_run_final):
            script_to_run_from_cwd = os.path.join(os.getcwd(), "src", "armstrong", "tools", server_script_to_use)
            if os.path.exists(script_to_run_from_cwd):
                script_to_run_final = script_to_run_from_cwd
                print(f"MCP Client: Using server script relative to CWD/src/armstrong/tools: {script_to_run_final}", file=sys.stderr, flush=True)
            else:
                script_one_level_up = os.path.join(os.path.dirname(current_tool_file_dir), server_script_to_use)
                if os.path.exists(script_one_level_up):
                     script_to_run_final = script_one_level_up
                     print(f"MCP Client: Using server script one level up: {script_to_run_final}", file=sys.stderr, flush=True)
                else:
                    error_msg = f"TOOL_ERROR:SERVER_SCRIPT_NOT_FOUND. Primary: '{script_to_run_final}', CWD attempt: '{script_to_run_from_cwd}', One level up: '{script_one_level_up}'"
                    print(error_msg, file=sys.stderr, flush=True)
                    return error_msg
        
        python_executable = sys.executable
        server_params = StdioServerParameters(command=python_executable, args=[script_to_run_final])
        
        print(f"MCP Client: Attempting to run server: {python_executable} {script_to_run_final}", flush=True)

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                print("MCP Client: stdio_client connected.", flush=True)
                async with ClientSession(read_stream, write_stream) as session:
                    print("MCP Client: ClientSession created. Initializing...", flush=True)
                    await session.initialize()                       
                    print(f"MCP Client: Session initialized. Calling MCP Server tool (operation): '{op_name}' with args: {args_dict}", flush=True)
                    
                    try:
                        serializable_args = json.loads(json.dumps(args_dict, default=str))
                    except TypeError as te:
                        error_msg = f"TOOL_ERROR:ARGUMENT_SERIALIZATION_FAILED for operation '{op_name}': {te}. Args: {args_dict}"
                        print(f"MCP Client: {error_msg}", flush=True, file=sys.stderr)
                        return error_msg

                    result: mcp_types.CallToolResult = await session.call_tool(name=op_name, arguments=serializable_args)
                    print(f"MCP Client: Raw Tool call result object: {result}", flush=True)

                    if result.isError:
                        err_text = "UnknownErrorFromServer"
                        if result.content and isinstance(result.content[0], mcp_types.TextContent):
                            err_text = result.content[0].text
                        elif hasattr(result, 'error') and result.error and isinstance(result.error, dict) and 'message' in result.error:
                            err_text = f"Code: {result.error.get('code', 'N/A')}, Message: {result.error['message']}"
                            if result.error.get('data'):
                                err_text += f", Data: {result.error['data']}"
                        
                        print(f"MCP Client: MCP_SERVER_ERROR for '{op_name}': {err_text}", flush=True, file=sys.stderr)
                        return f"MCP_SERVER_ERROR:{err_text}"

                    if result.content:
                        first_content_item = result.content[0]
                        if isinstance(first_content_item, mcp_types.TextContent):
                            return first_content_item.text
                        elif isinstance(first_content_item, mcp_types.StructuredContent):
                            return json.dumps(first_content_item.data)
                        else:
                            return str(first_content_item) 
                    return "TOOL_INFO:MCP_CALL_SUCCESS_NO_CONTENT"
        except Exception as e: 
            import traceback
            error_details = traceback.format_exc()
            error_msg = f"TOOL_ERROR:UNEXPECTED_CLIENT_FAILURE during '{op_name}': {type(e).__name__}: {str(e)}"
            print(f"MCP Client: {error_msg}\nDetails:\n{error_details}", flush=True, file=sys.stderr)
            return error_msg

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError: 
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        print("MCP Client Tool: Detected running asyncio event loop. Using nest_asyncio.", file=sys.stderr, flush=True)
        try:
            import nest_asyncio
            nest_asyncio.apply() # Apply it only once if possible, or ensure it's safe to call multiple times
            return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
        except ImportError:
            return "TOOL_ERROR:ASYNCIO_LOOP_ISSUE: nest_asyncio not installed for running loop."
        except Exception as e_nest_run:
            return f"TOOL_ERROR:NESTED_ASYNCIO_RUN_ERROR: {type(e_nest_run).__name__}: {str(e_nest_run)}"
    else:
        try:
            return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
        except Exception as e_direct_run:
            return f"TOOL_ERROR:DIRECT_ASYNCIO_RUN_ERROR: {type(e_direct_run).__name__}: {str(e_direct_run)}"
######################################################### General Tool Done #########################################################







################################################# Tool for Agent 3 : ClientProfilerAgent #################################################
# @tool("ClientProfilerTool")
# def client_profiler_tool(operation_name: str, arguments: Dict[str, Any]) -> str:
#     """
#     Accesses a Financial Analysis MCP server to perform specific calculations related to client profiling.
#     You MUST provide an 'operation_name' and an 'arguments' dictionary.
#     The MCP server will execute the corresponding Python function for the given 'operation_name'.

#     --- AVAILABLE OPERATIONS FOR CLIENT PROFILING ---

#     1.  operation_name: "calculate_current_age"
#         Description: Calculates the current age of an individual or entity as of a specific date.
#     # In custom_tool.py, within the ClientProfilerTool description for calculate_current_age
#     Required arguments dictionary: {
#                                 "date_of_birth": "string (YYYY-MM-DD format, e.g., '1985-07-25')",
#                                 "current_date": "string (YYYY-MM-DD format, e.g., '2023-04-05')" # Changed as_of_date
#                             }
#         Returns: String with calculated age and explanation. Example: "Calculated age based on DOB 1985-07-25 and as_of_date 2023-04-05: 37"

#     2.  operation_name: "calculate_duration_in_years"
#         Description: Calculates duration in years between a start point and an end point (e.g., age or year).
#                     Useful for: years to retirement, years to child's education goal.
#         Required arguments dictionary: {
#                                     "start_year": "number (int or float, e.g., current age 37)",
#                                     "end_year": "number (int or float, e.g., retirement age 55)",
#                                     "duration_description": "string (e.g., 'years to client retirement', 'years to Kahira UG education')"
#                                 }
#         Returns: String with calculated duration and explanation. Example: "Calculated duration for years to client retirement (from 37 to 55): 18 years"

#     3.  operation_name: "classify_investment_horizon"
#         Description: Classifies investment horizon (Short-Term, Medium-Term, Long-Term)
#                     based on years to a goal. Logic: >5 years = Long-Term; 3-5 years = Medium-Term; <3 years = Short-Term.
#         Required arguments dictionary: {
#                                     "years_to_goal": "number (int or float, e.g., 18)"
#                                 }
#         Returns: String with horizon classification and explanation. Example: "Investment horizon for goal (18 years) is classified as: Long-Term"

#     4.  operation_name: "determine_equity_exposure"
#         Description: Determines if there is equity exposure in a given list of assets.
#                     Looks for keywords like 'equity', 'stock', 'shares', 'equity mf', 'equitymf'
#                     in asset names or types within the list.
#         Required arguments dictionary: {
#                                     "asset_list": "list of asset dictionaries. Each dictionary should have a key (e.g., 'asset_name', 'type', 'category') with a string value describing the asset. Example: [{'asset_name': 'Infosys Shares', 'value': 50000}, {'type': 'Bank FD', 'value': 100000}]"
#                                 }
#         Returns: String "Result: Yes. Explanation: ..." or "Result: No. Explanation: ...".

#     5.  operation_name: "assess_client_risk_appetite"
#         Description: Assesses client's risk appetite based on years to retirement and equity exposure status.
#                     Logic: If YTR < 5: (Equity=Yes -> Medium, Equity=No -> Low). If YTR >= 5: (Equity=Yes -> Medium to High, Equity=No -> Medium).
#         Required arguments dictionary: {
#                                     "years_to_retirement": "number (int or float, e.g., 18)",
#                                     "equity_exposure_status": "string ('Yes' or 'No', case-insensitive)"
#                                 }
#         Returns: String with risk appetite classification and explanation. Example: "Client risk appetite based on 18 years to retirement and Yes equity exposure is: Medium to High"

#     --- END OF AVAILABLE OPERATIONS ---

#     Ensure argument names and their value types/formats match exactly as specified for the chosen 'operation_name'.
#     The tool will return a string which is the direct output from the corresponding server function,
#     or an error message starting with 'MCP_SERVER_ERROR:' or 'TOOL_ERROR:'.
#     """
    
#     server_script_to_use = MODULE_LEVEL_SERVER_SCRIPT_NAME

#     async def _run_mcp_async(op_name: str, args_dict: Dict[str, Any]) -> str:
#         current_tool_file_dir = os.path.dirname(os.path.abspath(__file__))
#         script_to_run_final = os.path.join(current_tool_file_dir, server_script_to_use) 

#         if not os.path.exists(script_to_run_final):
#             script_to_run_from_cwd = os.path.join(os.getcwd(), "src", "armstrong", "tools", server_script_to_use)
#             if os.path.exists(script_to_run_from_cwd):
#                 script_to_run_final = script_to_run_from_cwd
#                 print(f"MCP Client: Using server script relative to CWD/src/armstrong/tools: {script_to_run_final}", file=sys.stderr, flush=True)
#             else:
#                 script_one_level_up = os.path.join(os.path.dirname(current_tool_file_dir), server_script_to_use)
#                 if os.path.exists(script_one_level_up):
#                      script_to_run_final = script_one_level_up
#                      print(f"MCP Client: Using server script one level up: {script_to_run_final}", file=sys.stderr, flush=True)
#                 else:
#                     error_msg = f"TOOL_ERROR:SERVER_SCRIPT_NOT_FOUND. Primary: '{script_to_run_final}', CWD attempt: '{script_to_run_from_cwd}', One level up: '{script_one_level_up}'"
#                     print(error_msg, file=sys.stderr, flush=True)
#                     return error_msg
        
#         python_executable = sys.executable
#         server_params = StdioServerParameters(command=python_executable, args=[script_to_run_final])
        
#         print(f"MCP Client: Attempting to run server: {python_executable} {script_to_run_final}", flush=True)

#         try:
#             async with stdio_client(server_params) as (read_stream, write_stream):
#                 print("MCP Client: stdio_client connected.", flush=True)
#                 async with ClientSession(read_stream, write_stream) as session:
#                     print("MCP Client: ClientSession created. Initializing...", flush=True)
#                     await session.initialize()                       
#                     print(f"MCP Client: Session initialized. Calling MCP Server tool (operation): '{op_name}' with args: {args_dict}", flush=True)
                    
#                     try:
#                         serializable_args = json.loads(json.dumps(args_dict, default=str))
#                     except TypeError as te:
#                         error_msg = f"TOOL_ERROR:ARGUMENT_SERIALIZATION_FAILED for operation '{op_name}': {te}. Args: {args_dict}"
#                         print(f"MCP Client: {error_msg}", flush=True, file=sys.stderr)
#                         return error_msg

#                     result: mcp_types.CallToolResult = await session.call_tool(name=op_name, arguments=serializable_args)
#                     print(f"MCP Client: Raw Tool call result object: {result}", flush=True)

#                     if result.isError:
#                         err_text = "UnknownErrorFromServer"
#                         if result.content and isinstance(result.content[0], mcp_types.TextContent):
#                             err_text = result.content[0].text
#                         elif hasattr(result, 'error') and result.error and isinstance(result.error, dict) and 'message' in result.error:
#                             err_text = f"Code: {result.error.get('code', 'N/A')}, Message: {result.error['message']}"
#                             if result.error.get('data'):
#                                 err_text += f", Data: {result.error['data']}"
                        
#                         print(f"MCP Client: MCP_SERVER_ERROR for '{op_name}': {err_text}", flush=True, file=sys.stderr)
#                         return f"MCP_SERVER_ERROR:{err_text}"

#                     if result.content:
#                         first_content_item = result.content[0]
#                         if isinstance(first_content_item, mcp_types.TextContent):
#                             return first_content_item.text
#                         elif isinstance(first_content_item, mcp_types.StructuredContent):
#                             return json.dumps(first_content_item.data)
#                         else:
#                             return str(first_content_item) 
#                     return "TOOL_INFO:MCP_CALL_SUCCESS_NO_CONTENT"
#         except Exception as e: 
#             import traceback
#             error_details = traceback.format_exc()
#             error_msg = f"TOOL_ERROR:UNEXPECTED_CLIENT_FAILURE during '{op_name}': {type(e).__name__}: {str(e)}"
#             print(f"MCP Client: {error_msg}\nDetails:\n{error_details}", flush=True, file=sys.stderr)
#             return error_msg

#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError: 
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)

#     if loop.is_running():
#         print("MCP Client Tool: Detected running asyncio event loop. Using nest_asyncio.", file=sys.stderr, flush=True)
#         try:
#             import nest_asyncio
#             nest_asyncio.apply() # Apply it only once if possible, or ensure it's safe to call multiple times
#             return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
#         except ImportError:
#             return "TOOL_ERROR:ASYNCIO_LOOP_ISSUE: nest_asyncio not installed for running loop."
#         except Exception as e_nest_run:
#             return f"TOOL_ERROR:NESTED_ASYNCIO_RUN_ERROR: {type(e_nest_run).__name__}: {str(e_nest_run)}"
#     else:
#         try:
#             return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
#         except Exception as e_direct_run:
#             return f"TOOL_ERROR:DIRECT_ASYNCIO_RUN_ERROR: {type(e_direct_run).__name__}: {str(e_direct_run)}"

@tool("ClientProfilerTool")
def client_profiler_tool(operation_name: str, arguments: Dict[str, Any]) -> str:
    """
    Accesses a Client Profiler MCP server to perform calculations related to client profiling.
    The server functions now return JSON strings. You MUST provide an 'operation_name' and an 'arguments' dictionary.

    --- AVAILABLE OPERATIONS FOR CLIENT PROFILING ---

    1.  operation_name: "calculate_current_age"
        Description: Calculates the current age of an individual.
        Required arguments dictionary (all keys MUST be snake_case): {
                                "date_of_birth": "string (YYYY-MM-DD format, e.g., '1985-07-25')",
                                "current_date": "string (YYYY-MM-DD format, e.g., '2023-04-05')"
                            }
        Returns: A JSON string.
                 Example success: '{"calculated_age": 37, "date_of_birth_used": "1985-07-25", "current_date_used": "2023-04-05"}'
                 Example error:   '{"error": "Invalid date format..."}'

    2.  operation_name: "calculate_duration_in_years"
        Description: Calculates duration in years between a start and an end value (age or year).
        Required arguments dictionary (all keys MUST be snake_case): {
                                    "start_value": "number (int or float, e.g., current age 37)",
                                    "end_value": "number (int or float, e.g., retirement age 55)",
                                    "duration_description": "string (e.g., 'years to client retirement')"
                                }
        Returns: A JSON string.
                 Example success: '{"duration_years": 18, "start_value_used": 37, "end_value_used": 55, "description": "years to client retirement"}'
                 Example error:   '{"error": "Invalid input for duration calculation..."}'

    3.  operation_name: "classify_investment_horizon"
        Description: Classifies investment horizon based on years to a goal.
                     Logic: >5 years = Long-Term; 3-5 years = Medium-Term; <3 years = Short-Term.
        Required arguments dictionary (all keys MUST be snake_case): {
                                    "years_to_goal": "number (int or float, e.g., 18)"
                                }
        Returns: A JSON string.
                 Example success: '{"horizon_classification": "Long-Term", "years_to_goal_used": 18}'
                 Example error:   '{"error": "Invalid input for horizon classification..."}'

    4.  operation_name: "determine_equity_exposure"
        Description: Determines if there is equity exposure in a given list of assets.
                     Checks for keywords in asset names/types.
        Required arguments dictionary (all keys MUST be snake_case): {
                                    "asset_list": "List[Dict[str, Any]]. Typically, each dict has 'asset_name' and other relevant keys. Example: [{'asset_name': 'Infosys Shares'}, {'asset_name': 'Bank FD'}]"
                                }
        Returns: A JSON string.
                 Example success: '{"has_equity_exposure": true, "reason": "Equity exposure found..."}'
                 Example no equity: '{"has_equity_exposure": false, "reason": "No direct equity identified..."}'

    5.  operation_name: "assess_client_risk_appetite"
        Description: Assesses client's risk appetite based on years to retirement and equity exposure.
                     Logic: YTR < 5: (Equity=Yes -> Medium, Equity=No -> Low). YTR >= 5: (Equity=Yes -> Medium to High, Equity=No -> Medium).
        Required arguments dictionary (all keys MUST be snake_case): {
                                    "years_to_retirement": "number (int or float, e.g., 18)",
                                    "has_equity_exposure": "boolean (true or false) or string ('Yes' or 'No', case-insensitive)"
                                }
        Returns: A JSON string.
                 Example success: '{"risk_appetite": "Medium to High", "reasoning_inputs": {"years_to_retirement_used": 18, "has_equity_exposure_used": true}}'
                 Example error:   '{"error": "Invalid input for risk appetite assessment..."}'

    --- END OF AVAILABLE OPERATIONS ---

    Ensure argument names (keys in the 'arguments' dictionary) are exactly as specified (snake_case) and their value types/formats match.
    The tool will return a JSON string from the server, which will either contain the result or an error object.
    """
    
    # The _run_mcp_async function is generic and does not need to change
    # as long as the server returns a string (which our JSON string is).
    # Python variable names like op_name, args_dict are already snake_case.
    
    server_script_to_use = MODULE_LEVEL_SERVER_SCRIPT_NAME # This should point to mcp_server_tools.py

    async def _run_mcp_async(op_name_internal: str, args_dict_internal: Dict[str, Any]) -> str:
        current_tool_file_dir = os.path.dirname(os.path.abspath(__file__))
        # script_to_run_final should correctly resolve to your mcp_server_tools.py
        script_to_run_final = os.path.join(current_tool_file_dir, server_script_to_use) 

        if not os.path.exists(script_to_run_final):
            # Attempt to find it from the project root structure typical in CrewAI
            project_root = os.path.abspath(os.path.join(current_tool_file_dir, "..", "..")) # Go up two levels from src/armstrong/tools to armstrong/
            script_in_src_tools = os.path.join(project_root, "src", "armstrong", "tools", server_script_to_use)
            
            if os.path.exists(script_in_src_tools):
                script_to_run_final = script_in_src_tools
                print(f"MCP Client: Using server script from assumed project structure: {script_to_run_final}", file=sys.stderr, flush=True)
            else:
                # Fallback to original logic if the above doesn't work
                script_to_run_from_cwd = os.path.join(os.getcwd(), "src", "armstrong", "tools", server_script_to_use)
                if os.path.exists(script_to_run_from_cwd):
                    script_to_run_final = script_to_run_from_cwd
                    print(f"MCP Client: Using server script relative to CWD/src/armstrong/tools: {script_to_run_final}", file=sys.stderr, flush=True)
                else:
                    script_one_level_up = os.path.join(os.path.dirname(current_tool_file_dir), server_script_to_use)
                    if os.path.exists(script_one_level_up):
                        script_to_run_final = script_one_level_up
                        print(f"MCP Client: Using server script one level up: {script_to_run_final}", file=sys.stderr, flush=True)
                    else:
                        error_msg = f"TOOL_ERROR:SERVER_SCRIPT_NOT_FOUND. Primary attempt: '{os.path.join(current_tool_file_dir, server_script_to_use)}', Proj root attempt: '{script_in_src_tools}', One level up: '{script_one_level_up}'"
                        print(error_msg, file=sys.stderr, flush=True)
                        return error_msg
        
        python_executable = sys.executable
        # Make sure server_params uses the final resolved script_to_run_final
        server_params = StdioServerParameters(command=python_executable, args=[script_to_run_final])
        
        print(f"MCP Client: Attempting to run server: {python_executable} {script_to_run_final} for operation '{op_name_internal}'", flush=True)

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                # print("MCP Client: stdio_client connected.", flush=True) # less verbose
                async with ClientSession(read_stream, write_stream) as session:
                    # print("MCP Client: ClientSession created. Initializing...", flush=True) # less verbose
                    await session.initialize()                       
                    # print(f"MCP Client: Session initialized. Calling MCP Server tool (operation): '{op_name_internal}' with args: {args_dict_internal}", flush=True) # less verbose
                    
                    try:
                        # Ensure arguments are serializable, especially complex ones like asset_list
                        serializable_args = json.loads(json.dumps(args_dict_internal, default=str))
                    except TypeError as te:
                        error_msg = f"TOOL_ERROR:ARGUMENT_SERIALIZATION_FAILED for operation '{op_name_internal}': {te}. Args: {args_dict_internal}"
                        print(f"MCP Client: {error_msg}", flush=True, file=sys.stderr)
                        return error_msg

                    result: mcp_types.CallToolResult = await session.call_tool(name=op_name_internal, arguments=serializable_args)
                    # print(f"MCP Client: Raw Tool call result object for '{op_name_internal}': {result}", flush=True) # less verbose

                    if result.isError:
                        err_text = "UnknownErrorFromServer"
                        if result.content and isinstance(result.content[0], mcp_types.TextContent):
                            err_text = result.content[0].text
                        elif hasattr(result, 'error') and result.error and isinstance(result.error, dict) and 'message' in result.error: # Corrected mcp_types.Error to dict
                            err_text = f"Code: {result.error.get('code', 'N/A')}, Message: {result.error['message']}"
                            if result.error.get('data'):
                                err_text += f", Data: {result.error['data']}"
                        
                        print(f"MCP Client: MCP_SERVER_ERROR for '{op_name_internal}': {err_text}", flush=True, file=sys.stderr)
                        # Return the error as a JSON string, consistent with successful returns
                        return json.dumps({"error": f"MCP_SERVER_ERROR:{err_text}"})


                    if result.content:
                        first_content_item = result.content[0]
                        if isinstance(first_content_item, mcp_types.TextContent):
                            # The server now directly returns a JSON string. So, first_content_item.text IS the JSON string.
                            return first_content_item.text
                        elif isinstance(first_content_item, mcp_types.StructuredContent):
                            # This case might not be hit if server always returns TextContent (JSON string)
                            return json.dumps(first_content_item.data) 
                        else:
                            # Fallback, should ideally not happen if server returns JSON string
                            return json.dumps({"error": f"Unexpected content type from server: {type(first_content_item)}", "content_str": str(first_content_item)})
                    return json.dumps({"info": "MCP_CALL_SUCCESS_NO_CONTENT"}) # Return info as JSON
        except Exception as e: 
            import traceback
            error_details = traceback.format_exc()
            error_msg = f"TOOL_ERROR:UNEXPECTED_CLIENT_FAILURE during '{op_name_internal}': {type(e).__name__}: {str(e)}"
            print(f"MCP Client: {error_msg}\nDetails:\n{error_details}", flush=True, file=sys.stderr)
            return json.dumps({"error": error_msg}) # Return error as JSON

    # Synchronous wrapper for asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError: 
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Using op_name and arguments passed to the main client_profiler_tool function
    if loop.is_running():
        # print("MCP Client Tool: Detected running asyncio event loop. Using nest_asyncio.", file=sys.stderr, flush=True) # less verbose
        try:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
        except ImportError:
            return json.dumps({"error": "TOOL_ERROR:ASYNCIO_LOOP_ISSUE: nest_asyncio not installed."}) # Return error as JSON
        except Exception as e_nest_run:
            return json.dumps({"error": f"TOOL_ERROR:NESTED_ASYNCIO_RUN_ERROR: {type(e_nest_run).__name__}: {str(e_nest_run)}"}) # Return error as JSON
    else:
        try:
            return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
        except Exception as e_direct_run:
            return json.dumps({"error": f"TOOL_ERROR:DIRECT_ASYNCIO_RUN_ERROR: {type(e_direct_run).__name__}: {str(e_direct_run)}"})


################################################# Tool for Agent 3 : ClientProfilerAgent Done #################################################










################################################# Tool for Agent 4 : AssetLiabilityAnalyzerAgent #################################################
# @tool("AssetLiabilityAnalysisMCPTool")
# def asset_liability_analysis_mcp_tool(operation_name: str, arguments: Dict[str, Any]) -> str:
#     """
#     Accesses a Financial Analysis MCP server to perform calculations related to client assets and liabilities.
#     You MUST provide an 'operation_name' and an 'arguments' dictionary.
#     The MCP server will execute the corresponding Python function for the given 'operation_name'.

#     --- AVAILABLE OPERATIONS FOR ASSET & LIABILITY ANALYSIS ---

#     1.  operation_name: "calculate_total_value"
#         Description: Calculates the sum of values from a list of items (e.g., assets or liabilities).
#                      Each item in 'items_list' must be a dictionary.
#         Required arguments dictionary: {
#                                     "items_list": "list of dictionaries (e.g., client's assets or liabilities list)",
#                                     "value_key": "string, the key in each item dictionary holding the numerical value (e.g., 'Present Value' for assets, 'Outstanding Amount' for liabilities). Default: 'Present Value'",
#                                     "item_type_description": "string, describes what is being summed (e.g., 'client assets', 'client liabilities'). Default: 'items'"
#                                    }
#         Returns: String with the total calculated value and explanation. Example: "Total value of client assets calculated: 46381260.0. Details: [Direct Equity (Company Stocks): 18081260.0; ...]"

#     2.  operation_name: "calculate_net_worth"
#         Description: Calculates net worth (Total Assets - Total Liabilities).
#         Required arguments dictionary: {
#                                     "total_assets": "number or string_number (e.g., 46381260.0 or '46,381,260')",
#                                     "total_liabilities": "number or string_number (e.g., 7200000.0 or '7,200,000')"
#                                    }
#         Returns: String with calculated net worth and explanation. Example: "Net worth calculated (Assets: 46381260.0 - Liabilities: 7200000.0): 39181260.0"

#     3.  operation_name: "classify_assets_and_get_bucket_summary"
#         Description: Classifies a list of assets into predefined buckets (e.g., Liquid, Retirement, Fixed)
#                      based on keywords in asset names/types. Also calculates total value per bucket.
#         Required arguments dictionary: {
#                                     "asset_list": "list of asset dictionaries, e.g., [{'asset_name': 'Savings', 'Present Value': 10000}, ...]",
#                                     "classification_rules": "dictionary, where keys are bucket names (strings) and values are lists of keywords (strings).
#                                                              Example: {
#                                                                  \"Liquid Assets\": [\"cash\", \"bank\", \"fixed deposit\", \"mutual fund\", \"equity\", \"stocks\", \"shares\", \"bond\", \"gold\"],
#                                                                  \"Retirement Assets\": [\"provident fund\", \"ppf\", \"nps\", \"pension\"],
#                                                                  \"Fixed Assets\": [\"real estate\", \"property\", \"land\", \"flat\", \"house\"]
#                                                              }",
#                                     "value_key": "string, key in asset dicts for value. Default: 'Present Value'"
#                                    }
#         Returns: JSON string containing 'classified_assets' (dict of lists of full asset dicts), 'bucket_totals' (dict of floats),
#                  'unclassified_assets' (list), and a 'summary_message'.

#     4.  operation_name: "calculate_category_proportions"
#         Description: Calculates the percentage proportion of each provided category relative to a total value.
#                      Typically used for proportions of asset *classification buckets* (e.g. Liquid, Fixed, Retirement).
#         Required arguments dictionary: {
#                                     "category_values": "dictionary, keys are category names (strings, e.g., 'Liquid Assets'), values are their numerical totals (numbers or string_numbers). Example: {\"Liquid Assets\": 18381260.0, \"Fixed Assets\": 28000000.0}",
#                                     "total_value": "number or string_number (e.g., total asset value 46381260.0)"
#                                    }
#         Returns: JSON string containing 'proportions' (dict of category: percentage) and 'calculation_details'.
#                  Example: '{\"proportions\": {\"Liquid Assets\": 39.63, \"Fixed Assets\": 60.37}, ...}'

#     5.  operation_name: "calculate_individual_asset_proportions"
#         Description: Calculates the percentage proportion of each *individual original asset* relative to the total asset value.
#                      Useful for detailed pie chart data.
#         Required arguments dictionary: {
#                                     "asset_list": "list of the original asset dictionaries, e.g., [{'asset_name': 'Direct Equity', 'Present Value': '18,081,260'}, ...]",
#                                     "total_asset_value": "number or string_number (e.g., total asset value 46381260.0)",
#                                     "asset_name_key": "string, key in asset dicts for asset name/category. Default: 'asset_name'",
#                                     "value_key": "string, key in asset dicts for asset value. Default: 'Present Value'"
#                                    }
#         Returns: JSON string of a list of dicts, each with 'asset_category', 'value', 'proportion_percentage'.
#                  Example: '[{\"asset_category\": \"Direct Equity\", \"value\": 18081260.0, \"proportion_percentage\": 39.0}]'


#     --- END OF AVAILABLE OPERATIONS ---

#     Ensure argument names and their value types/formats match exactly.
#     The tool will return a string (often JSON formatted for complex results) from the server function,
#     or an error message if issues occur.
#     """
    
#     server_script_to_use = MODULE_LEVEL_SERVER_SCRIPT_NAME

#     async def _run_mcp_async(op_name: str, args_dict: Dict[str, Any]) -> str:
#         current_tool_file_dir = os.path.dirname(os.path.abspath(__file__))
#         script_to_run_final = os.path.join(current_tool_file_dir, server_script_to_use) 

#         if not os.path.exists(script_to_run_final):
#             script_to_run_from_cwd = os.path.join(os.getcwd(), "src", "armstrong", "tools", server_script_to_use)
#             if os.path.exists(script_to_run_from_cwd):
#                 script_to_run_final = script_to_run_from_cwd
#                 print(f"MCP Client: Using server script relative to CWD/src/armstrong/tools: {script_to_run_final}", file=sys.stderr, flush=True)
#             else:
#                 script_one_level_up = os.path.join(os.path.dirname(current_tool_file_dir), server_script_to_use)
#                 if os.path.exists(script_one_level_up):
#                      script_to_run_final = script_one_level_up
#                      print(f"MCP Client: Using server script one level up: {script_to_run_final}", file=sys.stderr, flush=True)
#                 else:
#                     error_msg = f"TOOL_ERROR:SERVER_SCRIPT_NOT_FOUND. Primary: '{script_to_run_final}', CWD attempt: '{script_to_run_from_cwd}', One level up: '{script_one_level_up}'"
#                     print(error_msg, file=sys.stderr, flush=True)
#                     return error_msg
        
#         python_executable = sys.executable
#         server_params = StdioServerParameters(command=python_executable, args=[script_to_run_final])
        
#         print(f"MCP Client: Attempting to run server: {python_executable} {script_to_run_final}", flush=True)

#         try:
#             async with stdio_client(server_params) as (read_stream, write_stream):
#                 print("MCP Client: stdio_client connected.", flush=True)
#                 async with ClientSession(read_stream, write_stream) as session:
#                     print("MCP Client: ClientSession created. Initializing...", flush=True)
#                     await session.initialize()                       
#                     print(f"MCP Client: Session initialized. Calling MCP Server tool (operation): '{op_name}' with args: {args_dict}", flush=True)
                    
#                     try:
#                         serializable_args = json.loads(json.dumps(args_dict, default=str))
#                     except TypeError as te:
#                         error_msg = f"TOOL_ERROR:ARGUMENT_SERIALIZATION_FAILED for operation '{op_name}': {te}. Args: {args_dict}"
#                         print(f"MCP Client: {error_msg}", flush=True, file=sys.stderr)
#                         return error_msg

#                     result: mcp_types.CallToolResult = await session.call_tool(name=op_name, arguments=serializable_args)
#                     print(f"MCP Client: Raw Tool call result object: {result}", flush=True)

#                     if result.isError:
#                         err_text = "UnknownErrorFromServer"
#                         if result.content and isinstance(result.content[0], mcp_types.TextContent):
#                             err_text = result.content[0].text
#                         elif hasattr(result, 'error') and result.error and isinstance(result.error, dict) and 'message' in result.error:
#                             err_text = f"Code: {result.error.get('code', 'N/A')}, Message: {result.error['message']}"
#                             if result.error.get('data'):
#                                 err_text += f", Data: {result.error['data']}"
                        
#                         print(f"MCP Client: MCP_SERVER_ERROR for '{op_name}': {err_text}", flush=True, file=sys.stderr)
#                         return f"MCP_SERVER_ERROR:{err_text}"

#                     if result.content:
#                         first_content_item = result.content[0]
#                         if isinstance(first_content_item, mcp_types.TextContent):
#                             return first_content_item.text
#                         elif isinstance(first_content_item, mcp_types.StructuredContent):
#                             return json.dumps(first_content_item.data)
#                         else:
#                             return str(first_content_item) 
#                     return "TOOL_INFO:MCP_CALL_SUCCESS_NO_CONTENT"
#         except Exception as e: 
#             import traceback
#             error_details = traceback.format_exc()
#             error_msg = f"TOOL_ERROR:UNEXPECTED_CLIENT_FAILURE during '{op_name}': {type(e).__name__}: {str(e)}"
#             print(f"MCP Client: {error_msg}\nDetails:\n{error_details}", flush=True, file=sys.stderr)
#             return error_msg

#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError: 
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)

#     if loop.is_running():
#         print("MCP Client Tool: Detected running asyncio event loop. Using nest_asyncio.", file=sys.stderr, flush=True)
#         try:
#             import nest_asyncio
#             nest_asyncio.apply() # Apply it only once if possible, or ensure it's safe to call multiple times
#             return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
#         except ImportError:
#             return "TOOL_ERROR:ASYNCIO_LOOP_ISSUE: nest_asyncio not installed for running loop."
#         except Exception as e_nest_run:
#             return f"TOOL_ERROR:NESTED_ASYNCIO_RUN_ERROR: {type(e_nest_run).__name__}: {str(e_nest_run)}"
#     else:
#         try:
#             return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
#         except Exception as e_direct_run:
#             return f"TOOL_ERROR:DIRECT_ASYNCIO_RUN_ERROR: {type(e_direct_run).__name__}: {str(e_direct_run)}"


@tool("AssetLiabilityAnalysisMCPTool")
def asset_liability_analysis_mcp_tool(operation_name: str, arguments: Dict[str, Any]) -> str:
    """
    Accesses a Financial Analysis MCP server to perform calculations related to client assets and liabilities.
    The server functions now return JSON strings. You MUST provide an 'operation_name' and a 'arguments' dictionary.
    All argument keys in the 'arguments' dictionary passed to an operation_name MUST be in snake_case.

    --- AVAILABLE OPERATIONS FOR ASSET & LIABILITY ANALYSIS ---

    1.  operation_name: "calculate_total_value"
        Description: Calculates sum of values from a list of item dictionaries (assets or liabilities).
        Required arguments dictionary (keys must be snake_case): {
                                    "items_list": "List[Dict[str, Any]] (e.g., client's assets or liabilities list, where items contain snake_case keys like 'asset_name', 'present_value', or 'loan_type', 'outstanding_amount')",
                                    "value_key": "string, the snake_case key in each item dictionary holding the numerical value (e.g., 'present_value' for assets, 'outstanding_amount' for liabilities). Default: 'present_value'",
                                    "item_type_description": "string, describes what is being summed (e.g., 'total client assets'). Default: 'items'"
                                   }
        Returns: JSON string.
                 Example success: '{"total_value": 46381260.0, "item_type_processed": "total client assets", "value_key_used": "present_value", "calculation_details": ["Fixed Deposit (FD): 100000.0", "..."]}'
                 Example error:   '{"error": "items_list must be a list."}'

    2.  operation_name: "calculate_net_worth"
        Description: Calculates net worth (Total Assets - Total Liabilities).
        Required arguments dictionary (keys must be snake_case): {
                                    "total_assets": "number or string_number (e.g., 46381260.0)",
                                    "total_liabilities": "number or string_number (e.g., 7200000.0)"
                                   }
        Returns: JSON string.
                 Example success: '{"net_worth": 39181260.0, "total_assets_used": 46381260.0, "total_liabilities_used": 7200000.0}'
                 Example error:   '{"error": "Inputs must be numbers..."}'

    3.  operation_name: "classify_assets_and_get_bucket_summary"
        Description: Classifies assets into predefined buckets and calculates total value per bucket.
        Required arguments dictionary (keys must be snake_case): {
                                    "asset_list": "List[Dict[str, Any]], e.g., [{'asset_name': 'Savings', 'present_value': 10000}, ...]. Ensure snake_case keys within asset dicts.",
                                    "classification_rules": "Dict[str, List[str]], where keys are bucket names (snake_case, e.g., 'liquid_assets') and values are lists of keywords.
                                                             Example: {
                                                                 \"liquid_assets\": [\"cash\", \"bank\", \"fixed deposit\", ...],
                                                                 \"retirement_assets\": [\"provident fund\", \"ppf\", ...],
                                                                 \"fixed_assets\": [\"real estate\", \"property\", ...]
                                                             }",
                                    "value_key": "string, snake_case key in asset dicts for value. Default: 'present_value'"
                                   }
        Returns: JSON string.
                 Example success: '{"bucket_totals": {"liquid_assets": 18381260.0, "fixed_assets": 28000000.0, ...}, "classified_assets_details": {...}, "unclassified_assets_count": 0, "summary_message": "Assets classified..."}'
                 Example error:   '{"error": "asset_list must be a list."}'

    4.  operation_name: "calculate_category_proportions"
        Description: Calculates percentage proportion of each category (e.g., asset buckets) relative to a total.
        Required arguments dictionary (keys must be snake_case): {
                                    "category_values_dict": "Dict[str, Union[int, float, str]], keys are snake_case category names (e.g., 'liquid_assets'), values are their numerical totals. Example: {\"liquid_assets\": 18381260.0, \"fixed_assets\": 28000000.0}",
                                    "total_value": "number or string_number (e.g., total asset value 46381260.0)"
                                   }
        Returns: JSON string.
                 Example success: '{"proportions_percentage": {"liquid_assets": 39.63, "fixed_assets": 60.37}, "total_value_used": 46381260.0}'
                 Example error:   '{"error": "total_value must be a number."}'

    5.  operation_name: "calculate_individual_asset_proportions"
        Description: Calculates percentage proportion of each individual original asset.
        Required arguments dictionary (keys must be snake_case): {
                                    "asset_list": "List[Dict[str, Any]] of original asset dicts, e.g., [{'asset_name': 'Direct Equity', 'present_value': '18081260'}, ...]. Ensure snake_case keys like 'asset_name', 'present_value'.",
                                    "total_asset_value": "number or string_number (e.g., total asset value 46381260.0)",
                                    "asset_name_key": "string, snake_case key in asset dicts for asset name/category. Default: 'asset_name'",
                                    "value_key": "string, snake_case key in asset dicts for asset value. Default: 'present_value'"
                                   }
        Returns: JSON string.
                 Example success: '{"individual_proportions": [{"asset_category": "Direct Equity", "value": 18081260.0, "proportion_percentage": 39.0}, ...], "total_asset_value_used": 46381260.0}'
                 Example error:   '{"error": "total_asset_value must be a number."}'

    --- END OF AVAILABLE OPERATIONS ---

    Ensure argument names (keys in the 'arguments' dictionary) are exactly as specified (snake_case) and their value types/formats match.
    The tool will return a JSON string from the server, which will either contain the result or an error object like '{"error": "message"}'.
    """
    
    server_script_to_use = MODULE_LEVEL_SERVER_SCRIPT_NAME

    async def _run_mcp_async(op_name_internal: str, args_dict_internal: Dict[str, Any]) -> str:
        current_tool_file_dir = os.path.dirname(os.path.abspath(__file__))
        script_to_run_final = os.path.join(current_tool_file_dir, server_script_to_use) 

        if not os.path.exists(script_to_run_final):
            project_root = os.path.abspath(os.path.join(current_tool_file_dir, "..", ".."))
            script_in_src_tools = os.path.join(project_root, "src", "armstrong", "tools", server_script_to_use)
            if os.path.exists(script_in_src_tools):
                script_to_run_final = script_in_src_tools
                print(f"MCP Client: Using server script from assumed project structure: {script_to_run_final}", file=sys.stderr, flush=True)
            else:
                # Fallback logic (as before)
                script_to_run_from_cwd = os.path.join(os.getcwd(), "src", "armstrong", "tools", server_script_to_use)
                if os.path.exists(script_to_run_from_cwd): script_to_run_final = script_to_run_from_cwd
                else:
                    script_one_level_up = os.path.join(os.path.dirname(current_tool_file_dir), server_script_to_use)
                    if os.path.exists(script_one_level_up): script_to_run_final = script_one_level_up
                    else:
                        error_msg = f"TOOL_ERROR:SERVER_SCRIPT_NOT_FOUND. Attempts: '{os.path.join(current_tool_file_dir, server_script_to_use)}', '{script_in_src_tools}', '{script_to_run_from_cwd}', '{script_one_level_up}'"
                        print(error_msg, file=sys.stderr, flush=True)
                        return json.dumps({"error": error_msg})
        
        python_executable = sys.executable
        server_params = StdioServerParameters(command=python_executable, args=[script_to_run_final])
        
        print(f"MCP Client: Attempting to run server: {python_executable} {script_to_run_final} for op '{op_name_internal}'", flush=True)

        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()                       
                    try:
                        serializable_args = json.loads(json.dumps(args_dict_internal, default=str))
                    except TypeError as te:
                        error_msg = f"TOOL_ERROR:ARGUMENT_SERIALIZATION_FAILED for op '{op_name_internal}': {te}. Args: {args_dict_internal}"
                        print(f"MCP Client: {error_msg}", flush=True, file=sys.stderr)
                        return json.dumps({"error": error_msg})

                    result: mcp_types.CallToolResult = await session.call_tool(name=op_name_internal, arguments=serializable_args)

                    if result.isError:
                        err_text = "UnknownErrorFromServer"
                        if result.content and isinstance(result.content[0], mcp_types.TextContent):
                            err_text = result.content[0].text
                        elif hasattr(result, 'error') and result.error and isinstance(result.error, dict):
                            err_msg_detail = result.error.get('message', 'No message')
                            err_data = result.error.get('data', None)
                            err_text = f"Code: {result.error.get('code', 'N/A')}, Message: {err_msg_detail}"
                            if err_data: err_text += f", Data: {json.dumps(err_data, default=str)}" # Serialize data part if complex
                        print(f"MCP Client: MCP_SERVER_ERROR for '{op_name_internal}': {err_text}", flush=True, file=sys.stderr)
                        return json.dumps({"error": f"MCP_SERVER_ERROR: {err_text}"}) # Return error as JSON string

                    if result.content:
                        first_content_item = result.content[0]
                        if isinstance(first_content_item, mcp_types.TextContent):
                            return first_content_item.text # This IS the JSON string from the server
                        elif isinstance(first_content_item, mcp_types.StructuredContent):
                            return json.dumps(first_content_item.data) # Should not be hit if server returns text
                        else:
                            return json.dumps({"error": f"Unexpected content type: {type(first_content_item)}", "content_str": str(first_content_item)})
                    return json.dumps({"info": "MCP_CALL_SUCCESS_NO_CONTENT"})
        except Exception as e: 
            import traceback
            error_details = traceback.format_exc()
            error_msg = f"TOOL_ERROR:UNEXPECTED_CLIENT_FAILURE during '{op_name_internal}': {type(e).__name__}: {str(e)}"
            print(f"MCP Client: {error_msg}\nDetails:\n{error_details}", flush=True, file=sys.stderr)
            return json.dumps({"error": error_msg})

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError: 
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        try:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
        except ImportError:
            return json.dumps({"error":"TOOL_ERROR:ASYNCIO_LOOP_ISSUE: nest_asyncio not installed."})
        except Exception as e_nest_run:
            return json.dumps({"error":f"TOOL_ERROR:NESTED_ASYNCIO_RUN_ERROR: {type(e_nest_run).__name__}: {str(e_nest_run)}"})
    else:
        try:
            return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
        except Exception as e_direct_run:
            return json.dumps({"error":f"TOOL_ERROR:DIRECT_ASYNCIO_RUN_ERROR: {type(e_direct_run).__name__}: {str(e_direct_run)}"})
################################################# Tool for Agent 4 : AssetLiabilityAnalyzerAgent Done #################################################












################################################# Tool for Agent 5 : GoalSettingMCPTool #################################################
# @tool("GoalSettingMCPTool")
# def goal_setting_mcp_tool(operation_name: str, arguments: Dict[str, Any]) -> str:
#     """
#     Accesses a Financial Analysis MCP server to perform calculations related to defining and projecting financial goals.
#     You MUST provide an 'operation_name' and an 'arguments' dictionary.
#     The MCP server will execute the corresponding Python function for the given 'operation_name'.

#     --- AVAILABLE OPERATIONS FOR GOAL SETTING ---

#     1.  operation_name: "calculate_duration_in_years"
#         Description: Calculates duration in years between a start event value (e.g., current age or year)
#                      and an end event value (e.g., retirement age or goal year).
#                      Use this to determine:
#                      - Time Remaining for Retirement: (pass current_age as 'start_year', retirement_age as 'end_year')
#                      - Time Remaining for Education: (pass child's_current_age as 'start_year', education_start_age as 'end_year')
#                      - Or, general duration between two years: (pass current_year as 'start_year', target_event_year as 'end_year')
#         Required arguments dictionary: {
#                                     "start_year": "number (int or float, e.g., current_client_age 37 or current_year 2023)", # CHANGED from start_point
#                                     "end_year": "number (int or float, e.g., client_retirement_age 55 or education_goal_target_year 2036)",   # CHANGED from end_point
#                                     "duration_description": "string (e.g., 'years to client retirement', 'time remaining for Kahira UG goal')"
#                                    }
#         Returns: String with calculated duration and explanation. Example: "Calculated duration for years to client retirement (from 37 to 55): 18 years"

#     2.  operation_name: "project_future_cost"
#         Description: Projects the future cost of a goal, adjusting for a given annual inflation rate over a number of years.
#                      Formula: Future Cost = Current Cost * (1 + Inflation Rate)^Years.
#         Required arguments dictionary: {
#                                     "current_cost": "number or string_number (e.g., 4000000 or '4,000,000')",
#                                     "inflation_rate_pa": "float or string_float (decimal format, e.g., 0.06 for 6%)",
#                                     "number_of_years": "integer or string_integer (e.g., 13)"
#                                    }
#         Returns: String with projected future cost and explanation. Example: "Projected future cost for current cost 4000000.00 at 6.0% annual inflation over 13 years: 8532345.12"

#     --- END OF AVAILABLE OPERATIONS ---

#     Ensure argument names and their value types/formats match exactly as specified for the chosen 'operation_name'.
#     The tool will return a string which is the direct output from the corresponding server function,
#     or an error message if issues occur.
#     """
    
#     server_script_to_use = MODULE_LEVEL_SERVER_SCRIPT_NAME

#     async def _run_mcp_async(op_name: str, args_dict: Dict[str, Any]) -> str:
#         current_tool_file_dir = os.path.dirname(os.path.abspath(__file__))
#         script_to_run_final = os.path.join(current_tool_file_dir, server_script_to_use) 

#         if not os.path.exists(script_to_run_final):
#             script_to_run_from_cwd = os.path.join(os.getcwd(), "src", "armstrong", "tools", server_script_to_use)
#             if os.path.exists(script_to_run_from_cwd):
#                 script_to_run_final = script_to_run_from_cwd
#                 print(f"MCP Client: Using server script relative to CWD/src/armstrong/tools: {script_to_run_final}", file=sys.stderr, flush=True)
#             else:
#                 script_one_level_up = os.path.join(os.path.dirname(current_tool_file_dir), server_script_to_use)
#                 if os.path.exists(script_one_level_up):
#                      script_to_run_final = script_one_level_up
#                      print(f"MCP Client: Using server script one level up: {script_to_run_final}", file=sys.stderr, flush=True)
#                 else:
#                     error_msg = f"TOOL_ERROR:SERVER_SCRIPT_NOT_FOUND. Primary: '{script_to_run_final}', CWD attempt: '{script_to_run_from_cwd}', One level up: '{script_one_level_up}'"
#                     print(error_msg, file=sys.stderr, flush=True)
#                     return error_msg
        
#         python_executable = sys.executable
#         server_params = StdioServerParameters(command=python_executable, args=[script_to_run_final])
        
#         print(f"MCP Client: Attempting to run server: {python_executable} {script_to_run_final}", flush=True)

#         try:
#             async with stdio_client(server_params) as (read_stream, write_stream):
#                 print("MCP Client: stdio_client connected.", flush=True)
#                 async with ClientSession(read_stream, write_stream) as session:
#                     print("MCP Client: ClientSession created. Initializing...", flush=True)
#                     await session.initialize()                       
#                     print(f"MCP Client: Session initialized. Calling MCP Server tool (operation): '{op_name}' with args: {args_dict}", flush=True)
                    
#                     try:
#                         serializable_args = json.loads(json.dumps(args_dict, default=str))
#                     except TypeError as te:
#                         error_msg = f"TOOL_ERROR:ARGUMENT_SERIALIZATION_FAILED for operation '{op_name}': {te}. Args: {args_dict}"
#                         print(f"MCP Client: {error_msg}", flush=True, file=sys.stderr)
#                         return error_msg

#                     result: mcp_types.CallToolResult = await session.call_tool(name=op_name, arguments=serializable_args)
#                     print(f"MCP Client: Raw Tool call result object: {result}", flush=True)

#                     if result.isError:
#                         err_text = "UnknownErrorFromServer"
#                         if result.content and isinstance(result.content[0], mcp_types.TextContent):
#                             err_text = result.content[0].text
#                         elif hasattr(result, 'error') and result.error and isinstance(result.error, dict) and 'message' in result.error:
#                             err_text = f"Code: {result.error.get('code', 'N/A')}, Message: {result.error['message']}"
#                             if result.error.get('data'):
#                                 err_text += f", Data: {result.error['data']}"
                        
#                         print(f"MCP Client: MCP_SERVER_ERROR for '{op_name}': {err_text}", flush=True, file=sys.stderr)
#                         return f"MCP_SERVER_ERROR:{err_text}"

#                     if result.content:
#                         first_content_item = result.content[0]
#                         if isinstance(first_content_item, mcp_types.TextContent):
#                             return first_content_item.text
#                         elif isinstance(first_content_item, mcp_types.StructuredContent):
#                             return json.dumps(first_content_item.data)
#                         else:
#                             return str(first_content_item) 
#                     return "TOOL_INFO:MCP_CALL_SUCCESS_NO_CONTENT"
#         except Exception as e: 
#             import traceback
#             error_details = traceback.format_exc()
#             error_msg = f"TOOL_ERROR:UNEXPECTED_CLIENT_FAILURE during '{op_name}': {type(e).__name__}: {str(e)}"
#             print(f"MCP Client: {error_msg}\nDetails:\n{error_details}", flush=True, file=sys.stderr)
#             return error_msg

#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError: 
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)

#     if loop.is_running():
#         print("MCP Client Tool: Detected running asyncio event loop. Using nest_asyncio.", file=sys.stderr, flush=True)
#         try:
#             import nest_asyncio
#             nest_asyncio.apply() # Apply it only once if possible, or ensure it's safe to call multiple times
#             return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
#         except ImportError:
#             return "TOOL_ERROR:ASYNCIO_LOOP_ISSUE: nest_asyncio not installed for running loop."
#         except Exception as e_nest_run:
#             return f"TOOL_ERROR:NESTED_ASYNCIO_RUN_ERROR: {type(e_nest_run).__name__}: {str(e_nest_run)}"
#     else:
#         try:
#             return loop.run_until_complete(_run_mcp_async(operation_name, arguments))
#         except Exception as e_direct_run:
#             return f"TOOL_ERROR:DIRECT_ASYNCIO_RUN_ERROR: {type(e_direct_run).__name__}: {str(e_direct_run)}"





@tool("GoalSettingMCPTool")
def goal_setting_mcp_tool(operation_name: str, arguments: Dict[str, Any]) -> str:
    """
    Accesses a Financial Analysis MCP server to perform calculations related to defining and projecting financial goals.
    The server functions now return JSON strings. You MUST provide an 'operation_name' and an 'arguments' dictionary.
    All argument keys in the 'arguments' dictionary passed to an operation_name MUST be in snake_case.

    --- AVAILABLE OPERATIONS FOR GOAL SETTING ---

    1.  operation_name: "calculate_duration_in_years"
        Description: Calculates duration in years between a start value (age/year) and an end value (age/year).
                     Use this to determine:
                     - Time Remaining for Retirement: (pass current_client_age as 'start_value', retirement_age as 'end_value')
                     - Time Remaining for Education: (pass child_current_age as 'start_value', education_start_age as 'end_value')
                     - Or, general duration between two years: (pass current_year as 'start_value', target_event_year as 'end_value')
        Required arguments dictionary (keys must be snake_case): {
                                    "start_value": "number (int or float, e.g., current_client_age 37 or current_year 2023)",
                                    "end_value": "number (int or float, e.g., client_retirement_age 55 or education_goal_target_year 2036)",
                                    "duration_description": "string (e.g., 'years to client retirement')"
                                   }
        Returns: A JSON string.
                 Example success: '{"duration_years": 18, "start_value_used": 37, "end_value_used": 55, "description": "years to client retirement"}'
                 Example error:   '{"error": "Invalid input for duration calculation..."}'

    2.  operation_name: "project_future_cost"
        Description: Projects the future cost of a goal, adjusting for inflation.
        Required arguments dictionary (keys must be snake_case): {
                                    "current_cost": "number or string_number (e.g., 4000000 or '4,000,000')",
                                    "inflation_rate_pa": "float or string_float (decimal format, e.g., 0.06 for 6%)",
                                    "number_of_years": "integer or string_integer (e.g., 13)"
                                   }
        Returns: A JSON string.
                 Example success: '{"projected_future_cost": 8532345.12, "current_cost_used": 4000000.0, "inflation_rate_pa_used": 0.06, "number_of_years_used": 13, "formatted_string": "Projected future cost..."}'
                 Example error:   '{"error": "Invalid input..."}'

    --- END OF AVAILABLE OPERATIONS ---

    Ensure argument names (keys in the 'arguments' dictionary) are exactly as specified (snake_case) and their value types/formats match.
    The tool will return a JSON string from the server, which will either contain the result or an error object like '{"error": "message"}'.
    """
    
    # The generic _run_mcp_async function (as defined in your mcp_clients.py for other tools) goes here.
    # Ensure it's robust and returns JSON strings for errors too.
    # For brevity, I'm omitting the copy-paste of _run_mcp_async here.
    # It's the same one used by client_profiler_tool and asset_liability_analysis_mcp_tool.
    
    server_script_to_use = MODULE_LEVEL_SERVER_SCRIPT_NAME

    async def _run_mcp_async_internal(op_name_internal: str, args_dict_internal: Dict[str, Any]) -> str: # Renamed to avoid conflict
        # ... (Exact same _run_mcp_async logic as in your other MCP client tools)
        # Ensure it returns JSON strings for errors, e.g., json.dumps({"error": "message"})
        current_tool_file_dir = os.path.dirname(os.path.abspath(__file__))
        script_to_run_final = os.path.join(current_tool_file_dir, server_script_to_use) 

        # ... (rest of the _run_mcp_async logic from your previous asset_liability_analysis_mcp_tool)
        # Make sure all error returns within _run_mcp_async_internal are json.dumps({"error": ...})

        # This is a placeholder for the actual robust path finding and execution logic
        if not os.path.exists(script_to_run_final):
            return json.dumps({"error": f"Server script not found at {script_to_run_final}"})
            
        python_executable = sys.executable
        server_params = StdioServerParameters(command=python_executable, args=[script_to_run_final])
        
        print(f"MCP Client (GoalSetting): Attempting to run server for op '{op_name_internal}'", flush=True)
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()                       
                    serializable_args = json.loads(json.dumps(args_dict_internal, default=str))
                    result: mcp_types.CallToolResult = await session.call_tool(name=op_name_internal, arguments=serializable_args)
                    if result.isError:
                        # ... error handling returning json.dumps({error...})
                        err_text = "UnknownErrorFromServer"
                        if result.content and isinstance(result.content[0], mcp_types.TextContent): err_text = result.content[0].text
                        return json.dumps({"error": f"MCP_SERVER_ERROR: {err_text}"})
                    if result.content and isinstance(result.content[0], mcp_types.TextContent):
                        return result.content[0].text
                    return json.dumps({"info": "MCP_CALL_SUCCESS_NO_CONTENT"})
        except Exception as e:
            return json.dumps({"error": f"TOOL_ERROR:UNEXPECTED_CLIENT_FAILURE: {type(e).__name__} - {str(e)}"})

    # Synchronous wrapper for asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError: 
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        try:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(_run_mcp_async_internal(operation_name, arguments))
        except ImportError:
            return json.dumps({"error":"TOOL_ERROR:ASYNCIO_LOOP_ISSUE: nest_asyncio not installed."})
        except Exception as e_nest_run:
            return json.dumps({"error":f"TOOL_ERROR:NESTED_ASYNCIO_RUN_ERROR: {type(e_nest_run).__name__}: {str(e_nest_run)}"})
    else:
        try:
            return loop.run_until_complete(_run_mcp_async_internal(operation_name, arguments))
        except Exception as e_direct_run:
            return json.dumps({"error":f"TOOL_ERROR:DIRECT_ASYNCIO_RUN_ERROR: {type(e_direct_run).__name__}: {str(e_direct_run)}"})
################################################# Tool for Agent 5 : GoalSettingMCPTool Done #################################################



