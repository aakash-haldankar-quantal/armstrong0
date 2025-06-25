import json
from datetime import datetime, date

def compute_age(dob_str, current_year):
    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    today = date(current_year, 6, 30)
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def derive_financials(client_json):
    profile = client_json['profile']
    data    = client_json['financials']
    goals   = client_json.get('goals', {})

    current_year = profile['current_year']
    age          = compute_age(profile['date_of_birth'], current_year)

    # 1) Income & Savings
    income          = data.get('monthly_income', 0)
    current_savings = data.get('current_monthly_savings', 0)

    # 2) Expenses
    mont_exp = sum(e['amount'] for e in data['expenses'] if e['type'].startswith('monthly'))
    ann_exp  = sum(e['amount'] for e in data['expenses'] if e['type'].startswith('annual'))
    total_monthly_exp = mont_exp + ann_exp / 12

    # 3) Liabilities & loan summary
    loans             = data.get('liabilities', [])
    total_emi         = sum(l.get('emi', 0) for l in loans)
    total_liabilities = sum(l.get('outstanding_amount', 0) for l in loans)
    highest_rate_loan = max(loans, key=lambda l: l.get('annual_interest_rate',0)) if loans else {}
    emi_ratio         = total_emi / income if income else None
    loan_summary      = {
        'total_emi': total_emi,
        'highest_rate_loan': highest_rate_loan,
        'emi_ratio': emi_ratio
    }

    # 4) Asset classification & buckets
    LIQUID_TYPES     = {'cash','fixed_deposit','mutual_fund','direct_equity','bond','gold','other_market_linked'}
    RETIREMENT_TYPES = {'provident_fund','public_provident_fund','nps'}
    FIXED_TYPES      = {'real_estate','land','property'}

    buckets          = {'liquid':0,'retirement':0,'fixed':0}
    assets_by_bucket = {'liquid':[],'retirement':[],'fixed':[]}
    total_assets     = 0
    weighted_return  = 0

    for a in data.get('assets', []):
        typ = a['type']
        if typ == 'real_estate':
            for p in a['properties']:
                v = p['value']
                total_assets += v
                buckets['fixed'] += v
                assets_by_bucket['fixed'].append({
                    'type':'real_estate',
                    'name': p['name'],
                    'value': v,
                    'location': p.get('location')
                })
                weighted_return += v * p.get('expected_annual_return', 0)
        else:
            v = a.get('present_value', 0)
            r = a.get('expected_annual_return', 0)
            total_assets    += v
            weighted_return += v * r
            entry = {'type':typ,'value':v,'expected_annual_return':r}
            if typ in LIQUID_TYPES:
                buckets['liquid'] += v
                assets_by_bucket['liquid'].append(entry)
            elif typ in RETIREMENT_TYPES:
                buckets['retirement'] += v
                assets_by_bucket['retirement'].append(entry)
            elif typ in FIXED_TYPES:
                buckets['fixed'] += v
                assets_by_bucket['fixed'].append(entry)
            else:
                buckets['liquid'] += v
                assets_by_bucket['liquid'].append(entry)

    # 5) Bucket percentages
    bucket_percentages = {
        k: (v/total_assets*100) if total_assets else None
        for k,v in buckets.items()
    }

    # 6) Equity exposure
    equity_exposure = any(a['type']=='direct_equity' for a in data.get('assets', []))

    # 7) Ratios
    liquidity_ratio    = buckets['liquid']/total_assets if total_assets else 0
    low_yield_ratio    = (buckets['fixed']+buckets['retirement'])/total_assets if total_assets else 0
    real_estate_ratio  = buckets['fixed']/total_assets if total_assets else 0
    flexibility_ratio  = buckets['liquid']/total_assets if total_assets else 0
    portfolio_return   = weighted_return/total_assets if total_assets else 0

    # 8) Savings & Spending ratios
    savings_ratio  = current_savings/income if income else 0
    spending_ratio = (total_monthly_exp+total_emi)/income if income else 0

    # 9) Flags
    flags = {
        'illiquidity':          liquidity_ratio<0.10,
        'overweight_low_yield': low_yield_ratio>0.50,
        'flexibility_low':      flexibility_ratio<0.15,
        'low_savings':          savings_ratio<(0.2 if age<40 else 0.3),
        'high_spending':        spending_ratio>0.70
    }

    # 10) Compute monthly surplus capacity
    monthly_surplus = max(income - total_monthly_exp, 0)

    # 11) Goal PMTs & proportional allocation
    def project_amt(amount, years, inflation=0.06):
        return amount * (1 + inflation)**max(years,0)

    def compute_pmt(FV, annual_return, years):
        r_month = annual_return / 12
        n       = max(years * 12, 1)
        return FV * r_month / ((1 + r_month)**n - 1)

    children = profile['family'].get('children', [])
    pmt_list = []
    interim_goals = []

    # Retirement
    if 'retirement' in goals:
        g    = goals['retirement']
        yrs  = g['target_age'] - age
        init = g['target_corpus']
        proj = project_amt(init, yrs)
        pmt  = compute_pmt(proj, 0.08, yrs)
        pmt_list.append(pmt)
        interim_goals.append({
            'type': 'Retirement',
            'initial_goal': init,
            'projected_goal': proj,
            'years_left': yrs,
            'required_monthly_savings': pmt
        })

    # Education
    for eg in goals.get('education', []):
        name  = eg['beneficiary']
        child = next((c for c in children if c['name']==name), {})
        yob   = child.get('year_of_birth', current_year)
        for lvl, amt in eg['levels'].items():
            tgt_age = 18 if lvl=='undergraduate' else 22
            yrs     = (yob + tgt_age) - current_year
            proj    = project_amt(amt, yrs)
            pmt     = compute_pmt(proj, 0.10, yrs)
            pmt_list.append(pmt)
            interim_goals.append({
                'type': 'Education',
                'beneficiary': name,
                'level': lvl,
                'initial_goal': amt,
                'projected_goal': proj,
                'years_left': yrs,
                'required_monthly_savings': pmt
            })

    # Vacations
    for vac in goals.get('vacations', []):
        yrs  = vac['year'] - current_year
        init = vac['estimated_cost']
        proj = project_amt(init, yrs)
        pmt  = compute_pmt(proj, 0.08, yrs)
        pmt_list.append(pmt)
        interim_goals.append({
            'type': 'Vacation',
            'name': vac['location'],
            'year': vac['year'],
            'initial_goal': init,
            'projected_goal': proj,
            'years_left': yrs,
            'required_monthly_savings': pmt
        })

    # Custom Goals
    for cg in goals.get('custom_goals', []):
        yrs  = cg['year'] - current_year
        init = cg['required_funds']
        proj = project_amt(init, yrs)
        pmt  = compute_pmt(proj, 0.08, yrs)
        pmt_list.append(pmt)
        interim_goals.append({
            'type': 'Custom',
            'name': cg['name'],
            'year': cg['year'],
            'initial_goal': init,
            'projected_goal': proj,
            'years_left': yrs,
            'required_monthly_savings': pmt
        })

    # Allocate surplus proportional to need
    # total_pmt = sum(pmt_list)
    # final_goals = []
    # for goal, pmt in zip(interim_goals, pmt_list):
    #     capacity = (pmt / total_pmt) * monthly_surplus if total_pmt else 0
    #     gap      = pmt - capacity
    #     goal.update({
    #         'allocated_monthly_capacity': capacity,
    #         'gap': gap
    #     })
    #     final_goals.append(goal)

    # 12) Savings gap flag
    required_total = sum(pmt_list)
    savings_gap    = required_total - monthly_surplus
    flags['savings_gap_high'] = savings_gap > 0.5 * monthly_surplus if monthly_surplus else True

    # 13) Assemble final result
    return {
        'age': age,
        'buckets': buckets,
        'bucket_percentages': bucket_percentages,
        'assets_by_bucket': assets_by_bucket,
        'equity_exposure': equity_exposure,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'net_worth': total_assets - total_liabilities,
        'ratios': {
            'liquidity': liquidity_ratio,
            'low_yield': low_yield_ratio,
            'real_estate': real_estate_ratio,
            'flexibility': flexibility_ratio,
            'savings': savings_ratio,
            'spending': spending_ratio,
            'portfolio_return': portfolio_return
        },
        'loan_summary': loan_summary,
        'monthly_surplus': monthly_surplus,
        'required_monthly_savings': required_total,
        'savings_gap': savings_gap,
        'flags': flags,
        'goals': interim_goals #final_goals
    }

# Example usage:
# client = json.loads(input_json)
# derived = derive_financials(client)
# print(json.dumps(derived, indent=2))


# Example:
# client = json.loads(input_json)
# derived = derive_financials(client)
# print(json.dumps(derived, indent=2))


# Example usage:
# client = json.loads(input_json)
# derived = derive_financials(client)
# print(json.dumps(derived, indent=2))


# Example usage:
# client = json.loads(input_json)
# derived = derive_financials(client)
# print(json.dumps(derived, indent=2))


# Example usage:
# client = json.loads(input_json)
# derived = derive_financials(client)
# print(json.dumps(derived, indent=2))


# Example usage:
# client = json.loads(input_json)
# derived = derive_financials(client)
# print(json.dumps(derived, indent=2))


# Example usage:
# client = json.loads(input_json)
# derived = derive_financials(client)
# print(json.dumps(derived, indent=2))


# client_data={
#   "profile": {
#     "name": "John Doe",
#     "date_of_birth": "1980-01-01",
#     "retirement_age": 60,
#     "current_year": 2025,
#     "occupation": "Software Engineer",
#     "marital_status": "Married",
#     "family": {
#       "spouses": [
#         { "name": "Jane Doe",   "year_of_birth": 1982 },
#         { "name": "Alexis Doe", "year_of_birth": 1985 }
#       ],
#       "children": [
#         { "name": "Alice", "year_of_birth": 2012 },
#         { "name": "Bob",   "year_of_birth": 2016 }
#       ],
#       "dependents": [
#         { "name": "Father", "relationship": "father", "year_of_birth": 1950 }
#       ]
#     }
#   },
#   "financials": {
#     "monthly_income": 200000,
#     "current_monthly_savings": 46000,
#     "expenses": [
#       { "type": "monthly_household", "amount": 75000 },
#       { "type": "monthly_travel", "amount": 12000 },
#       { "type": "monthly_emergency","amount": 5000  },
#       { "type": "monthly_saving",    "amount": 62000 }
#     ],
#     "assets": [
#       {
#         "type": "provident_fund",
#         "present_value": 1200000,
#         "expected_annual_return": 0.08,
#         "duration_years": 15,
#         "years_since": 7,
#         "convertible":True,
#         "monthly_add":2000
#       },
#       {
#         "type": "public_provident_fund",
#         "present_value": 800000,
#         "expected_annual_return": 0.075,
#         "duration_years": 15,
#         "years_since": 7,
#         "convertible":True,
#         "monthly_add":2000
#       },
#       {
#         "type": "fixed_deposit",
#         "present_value": 250000,
#         "expected_annual_return": 0.065,
#         "duration_years": 10,
#         "years_since": 7,
#         "convertible":True,
#         "monthly_add":2000
#       },
#       {
#         "type": "lic_policy",
#         "present_value": 500000,
#         "expected_annual_return": 0.06,
#         "duration_years": 20,
#         "years_since": 7,
#         "convertible":False,
#         "monthly_add":2000
#       },
#       {
#         "type": "mutual_fund",
#         "present_value": 700000,
#         "expected_annual_return": 0.12,
#         "duration_years": 12,
#         "years_since": 7,
#         "convertible":True,
#         "monthly_add":2000
#       },
#       {
#         "type": "direct_equity",
#         "present_value": 2000000,
#         "expected_annual_return": 0.15,
#         "duration_years": None,
#         "years_since": None,
#         "convertible":True,
#         "monthly_add":2000
#       },
#       {
#         "type": "real_estate",
#         "properties": [
#           {
#             "name": "Primary Residence",
#             "value": 10000000,
#             "location": "Mumbai",
#             "expected_annual_return": 0.06,
#             "duration_years": None,
#             "years_since": None,
#             "convertible":True,
#             "monthly_add":None
#           },
#           {
#             "name": "Rental Apartment",
#             "value": 4500000,
#             "location": "Pune",
#             "expected_annual_return": 0.055,
#             "duration_years": None,
#             "years_since": None,
#             "convertible": False,
#             "monthly_add":None
#           }
#         ]
#       },
#       {
#         "type": "cash",
#         "present_value": 300000,
#         "expected_annual_return": 0.03,
#         "duration_years": 0,
#         "years_since": None,
#         "convertible":True,
#         "monthly_add":2000
#       }
#     ],
#     "liabilities": [
#       {
#         "type": "home_loan",
#         "outstanding_amount": 4000000,
#         "annual_interest_rate": 0.075,
#         "emi": 35000,
#         "lender": "HDFC Bank"
#       },
#       {
#         "type": "car_loan",
#         "outstanding_amount": 800000,
#         "annual_interest_rate": 0.09,
#         "emi": 15000,
#         "lender": "ICICI Bank"
#       },
#       {
#         "type": "personal_loan",
#         "outstanding_amount": 200000,
#         "annual_interest_rate": 0.12,
#         "emi": 5000,
#         "lender": "Bajaj Finance"
#       }
#     ]
#   },
#   "goals": {
#     "education": [
#       {
#         "beneficiary": "Alice",
#         "levels": {
#           "undergraduate": 1000000,
#           "postgraduate": 1500000
#         }
#       },
#       {
#         "beneficiary": "Bob",
#         "levels": {
#           "undergraduate": 1200000,
#           "postgraduate": 1800000
#         }
#       }
#     ],
#     "retirement": {
#       "target_age": 60,
#       "target_corpus": 50000000,
#       "monthly_post_retirement_expense": 60000
#     },
#     "vacations": [
#       { "year": 2026, "estimated_cost": 300000, "location": "Europe" },
#       { "year": 2028, "estimated_cost": 200000, "location": "Japan" }
#     ],
#     "custom_goals": [
#       { "name": "Start Business", "year": 2030, "required_funds": 10000000 },
#       { "name": "Buy Farmhouse",  "year": 2035, "required_funds": 15000000 }
#     ]
#   }
# }

import json
from datetime import datetime, date

def analyze_assets_for_recommendations(client_data):
    """
    For each specified liquid asset, if its expected annual return is < 7%
    and remaining duration > 3 years, recommend switching to a mutual fund at 12% annual return.
    Calculate the opportunity cost of staying versus switching.
    """
    MUTUAL_FUND_RETURN = 0.12
    recommendations = []

    # Helpers
    def fv_lump_sum(pv, rate, years):
        return pv * (1 + rate) ** years

    def fv_annuity(payment, rate, years):
        r_month = rate / 12
        n = int(years * 12)
        if r_month == 0:
            return payment * n
        return payment * (((1 + r_month) ** n - 1) / r_month)

    for asset in client_data['financials']['assets']:
        # Only consider these liquid-like instruments
        if asset['type'] not in {
            'fixed_deposit', 'lic_policy'
        }:
            continue

        r_current = asset.get('expected_annual_return', 0)
        dur = asset.get('duration_years')
        # treat None as 0 years used
        years_used = asset.get('years_since') or 0
        monthly_add = asset.get('monthly_add') or 0
        pv = asset.get('present_value') or asset.get('value', 0)

        # Skip if no duration or not meeting criteria
        if dur is None:
            continue
        remaining = dur - years_used
        if remaining <= 3 or r_current >= 0.07:
            continue

        # Future values in current scheme
        fv_current_pv = fv_lump_sum(pv, r_current, remaining)
        fv_current_add = fv_annuity(monthly_add, r_current, remaining)

        # Future values if switched to mutual fund
        if asset.get('convertible', False):
            fv_mf_pv = fv_lump_sum(pv, MUTUAL_FUND_RETURN, remaining)
        else:
            fv_mf_pv = pv  # locked, no growth

        fv_mf_add = fv_annuity(monthly_add, MUTUAL_FUND_RETURN, remaining)

        # Opportunity cost
        opp_pv = fv_mf_pv - fv_current_pv
        opp_add = fv_mf_add - fv_current_add
        total_opp = opp_pv + opp_add

        recommendations.append({
            'type': asset['type'],
            'present_value': pv,
            'expected_annual_return': r_current,
            'remaining_years': remaining,
            'convertible': asset.get('convertible', False),
            'monthly_add': monthly_add,
            'fv_current_total': fv_current_pv + fv_current_add,
            'fv_mutual_fund_total': fv_mf_pv + fv_mf_add,
            'opportunity_cost': total_opp,
            'recommendation': (
                "Switch to mutual fund (12%)" if total_opp > 0
                else "Stay in current scheme"
            )
        })

    return recommendations

# recs = analyze_assets_for_recommendations(client_data)
# print(json.dumps(recs, indent=2))

def apply_recommendations(client_data, recommendations):
    """
    Merge asset‐level recommendations back into the client_data structure.
    If recommendation is to switch to mutual fund (12%), update that asset's
    expected return and tag the action.
    """
    MUTUAL_FUND_RETURN = 0.12

    # Iterate through each recommendation
    for rec in recommendations:
        asset_type = rec['type']
        action     = rec['recommendation']

        # Find matching assets in the client's portfolio
        for asset in client_data['financials']['assets']:
            # Top‐level assets
            if asset.get('type') == asset_type:
                asset['recommended_action'] = action
                if action.startswith("Switch"):
                    # Modify the asset to a mutual fund
                    asset['expected_annual_return'] = MUTUAL_FUND_RETURN
                    asset['type'] = 'mutual_fund'
            # Nested real_estate properties
            elif asset.get('type') == 'real_estate':
                for prop in asset['properties']:
                    if rec.get('name') == prop.get('name') and rec['type']=='real_estate':
                        prop['recommended_action'] = action
                        if action.startswith("Switch"):
                            prop['expected_annual_return'] = MUTUAL_FUND_RETURN
                            # Mark as new mutual fund holding
                            prop['converted_to'] = 'mutual_fund'

    return client_data

# updated_client_data = apply_recommendations(client_data, recs)
# print(json.dumps(updated_client_data, indent=2))

# derived = derive_financials(updated_client_data)
# #derived = json.loads(input_json)
# print(json.dumps(derived, indent=2))

def analyze_investment_maturities(client_data):
    """
    For each asset with defined duration_years and years_since, calculate:
      - start_year (when scheme began)
      - maturity_year (start_year + duration_years)
      - remaining_years = max(maturity_year - current_year, 0)
      - maturity_value = present_value * (1 + expected_annual_return) ** duration_years
      - total_return = maturity_value - present_value
      - monthly_contribution and total_contributed to date
    Returns a dict of results.
    """
    current_year = client_data['profile']['current_year']
    results = []

    def compute_maturity(pv, rate, years):
        return pv * (1 + rate) ** years

    for asset in client_data['financials']['assets']:
        # handle real estate properties
        if asset.get('type') == 'real_estate':
            for p in asset['properties']:
                dur = p.get('duration_years')
                used = p.get('years_since')
                r = p.get('expected_annual_return')
                pv = p.get('value')
                m_add = p.get('monthly_add') or 0
                if dur is not None and used is not None and r is not None and pv is not None:
                    start_year = current_year - used
                    maturity_year = start_year + dur
                    remaining_years = max(maturity_year - current_year, 0)
                    maturity_value = compute_maturity(pv, r, dur)
                    total_return = maturity_value - pv
                    total_contributed = m_add * used * 12
                    results.append({
                        'name': p['name'],
                        'type': 'real_estate',
                        'start_year': start_year,
                        'maturity_year': maturity_year,
                        'remaining_years': remaining_years,
                        'present_value': pv,
                        'expected_annual_return': r,
                        'monthly_contribution': m_add,
                        'total_contributed': total_contributed,
                        'maturity_value': maturity_value,
                        'total_return': total_return
                    })
        else:
            dur = asset.get('duration_years')
            used = asset.get('years_since')
            r = asset.get('expected_annual_return')
            pv = asset.get('present_value')
            m_add = asset.get('monthly_add') or 0
            if dur is not None and used is not None and r is not None and pv is not None:
                start_year = current_year - used
                maturity_year = start_year + dur
                remaining_years = max(maturity_year - current_year, 0)
                maturity_value = compute_maturity(pv, r, dur)
                total_return = maturity_value - pv
                total_contributed = m_add * used * 12
                results.append({
                    'type': asset['type'],
                    'start_year': start_year,
                    'maturity_year': maturity_year,
                    'remaining_years': remaining_years,
                    'present_value': pv,
                    'expected_annual_return': r,
                    'monthly_contribution': m_add,
                    'total_contributed': total_contributed,
                    'maturity_value': maturity_value,
                    'total_return': total_return
                })

    return {'investment_maturities': results}


# output = analyze_investment_maturities(updated_client_data)
# print(json.dumps(output, indent=2))

def build_asset_basket(client_data, derived_data, mature_data):
    """
    Constructs an asset basket for the agent by:
      - Extracting monthly_surplus from derived_data
      - Merging mature investments with their original features
      - Including remaining assets (not in mature list) with full features
    """
    # Extract monthly_surplus
    monthly_surplus = derived_data.get('monthly_surplus', 0)
    
    # Index mature types
    mature_types = {inv['type'] for inv in mature_data['investment_maturities']}
    
    # Helper to find original asset by type
    def find_asset(type_name):
        for asset in client_data['financials']['assets']:
            if asset.get('type') == type_name:
                return asset
            if asset.get('type') == 'real_estate':
                # skip real estate here
                continue
        return None
    
    # Build merged list for matured
    investments = []
    for inv in mature_data['investment_maturities']:
        orig = find_asset(inv['type'])
        merged = {**orig, **inv}
        investments.append(merged)
    
    # Add remaining assets
    for asset in client_data['financials']['assets']:
        typ = asset['type']
        if typ in mature_types or typ == 'real_estate':
            continue
        investments.append(asset)
    
    # Include real estate as-is
    for asset in client_data['financials']['assets']:
        if asset['type'] == 'real_estate':
            investments.append(asset)
    
    return {
        'monthly_surplus': monthly_surplus,
        'asset_basket': investments
    }


# mature_data=output
# derived_data=derived

# basket = build_asset_basket(updated_client_data, derived_data, mature_data)
# print(json.dumps(basket, indent=2))

import json

def sort_assets_by_liquidity_with_surplus(asset_basket):
    """
    Returns a dict containing the original monthly_surplus and the asset_basket
    sorted from most to least liquid.
    """
    monthly_surplus = asset_basket.get('monthly_surplus')
    assets = asset_basket.get('asset_basket', [])
    
    def liquidity_score(asset):
        if not asset.get('convertible', False):
            return 0
        t = asset['type']
        if t == 'cash':
            return 10
        if t == 'fixed_deposit':
            return 9
        if t == 'mutual_fund':
            return 8
        if t == 'direct_equity':
            return 7
        if t in ('provident_fund', 'public_provident_fund'):
            return 5
        if t == 'lic_policy':
            return 3
        if t == 'real_estate':
            return 1
        return 4

    sorted_assets = sorted(assets, key=liquidity_score, reverse=True)
    
    return {
        "monthly_surplus": monthly_surplus,
        "asset_basket": sorted_assets
    }



def emi_payment_advisor(client_data, derived_client_data):
    """
    Advises on monthly EMI payment strategy:
    - Allocates monthly surplus toward EMIs.
    - Ensures no more than 50% of monthly income is allocated.
    - If surplus is less than EMI, recommends using available assets (not just liquid).
    Returns allocation and recommendations.
    """
    monthly_income = client_data['financials']['monthly_income']
    monthly_surplus = derived_client_data['monthly_surplus']
    total_emi = derived_client_data['loan_summary']['total_emi']
    max_emi_allowed = 0.5 * monthly_income  # 50% rule

    result = {}

    # Step 1: Check 50% rule
    emi_to_pay = min(total_emi, max_emi_allowed)

    # Step 2: Can surplus cover the EMI?
    if monthly_surplus >= emi_to_pay:
        result['monthly_surplus_used_for_emi'] = emi_to_pay
        result['recommendation'] = (
            "Surplus is sufficient to pay EMIs without breaching 50% income rule."
        )
        result['assets_used'] = 0
    else:
        gap = emi_to_pay - monthly_surplus
        total_assets_available = derived_client_data['total_assets']
        result['monthly_surplus_used_for_emi'] = monthly_surplus
        result['assets_used'] = gap
        result['recommendation'] = (
            f"Monthly surplus ({monthly_surplus}) is insufficient to cover EMI ({emi_to_pay}). "
            f"Recommend withdrawing ₹{gap:.2f} from available assets "
            f"(Total assets available: ₹{total_assets_available:.2f})."
        )
    result['emi_to_pay'] = emi_to_pay
    result['emi_percentage_of_income'] = emi_to_pay / monthly_income

    # # Caution if total_emi itself exceeds 50% of income
    # if total_emi > max_emi_allowed:
    #     result['warning'] = (
    #         f"Total EMI ({total_emi}) exceeds 50% of monthly income ({monthly_income}). "
    #         "Financial stress risk. Consider refinancing loans or liquidating assets to reduce EMI burden."
    #     )
    
    return result

# recommendation = emi_payment_advisor(updated_client_data, derived_data)
# print(recommendation)

# recommendation['assets_used']==0

def update_asset_basket_with_surplus_usage(recommendation, asset_basket):
    """
    Deduct recommendation['monthly_surplus_used_for_emi'] from asset_basket['monthly_surplus']
    and return a new asset_basket dict with the updated surplus.
    """
    used = recommendation.get('monthly_surplus_used_for_emi', 0)
    updated = asset_basket.copy()
    updated_surplus = max(0, updated.get('monthly_surplus', 0) - used)
    updated['monthly_surplus'] = updated_surplus
    return updated

# updated_asset_basket=update_asset_basket_with_surplus_usage(recommendation, basket)
# print(updated_asset_basket)

import math
from datetime import datetime, timedelta

def months_to_clear_loan(principal, rate, emi):
    """
    Calculates the number of months to clear a loan, given principal, annual rate, and monthly EMI.
    If rate=0, simply principal / emi.
    """
    if emi <= 0 or principal <= 0:
        return 0
    if rate == 0:
        return math.ceil(principal / emi)
    r = rate / 12  # monthly interest
    try:
        n = math.log(emi / (emi - principal * r)) / math.log(1 + r)
        return int(math.ceil(n))
    except (ZeroDivisionError, ValueError):
        # If EMI <= interest, loan can't be repaid, or bad data
        return None

def loan_liability_summary(client_data):
    result = []
    current_year = client_data['profile'].get('current_year', datetime.now().year)
    today = datetime(current_year, 1, 1)

    for loan in client_data['financials'].get('liabilities', []):
        principal = loan.get('outstanding_amount', 0)
        rate = loan.get('annual_interest_rate', 0)
        emi = loan.get('emi', 0)
        lender = loan.get('lender', '')
        loan_type = loan.get('type', 'loan')

        months = months_to_clear_loan(principal, rate, emi)
        if months is None:
            payoff_date = "Cannot compute (invalid EMI/interest)"
        else:
            payoff_date = (today + timedelta(days=months*30.44)).strftime('%B %Y')

        result.append({
            "loan_type": loan_type,
            "lender": lender,
            "outstanding_amount": principal,
            "annual_interest_rate": rate,
            "emi": emi,
            "months_remaining": months,
            "payoff_date": payoff_date
        })
    return result

# loan_detail=loan_liability_summary(updated_client_data)
# print(loan_detail)

# asset_basket_sorted={
#     'asset_basket': [
#         {'type': 'cash', 'present_value': 152000, 'expected_annual_return': 0.03, 'duration_years': 0, 'years_since': None, 'convertible': True, 'monthly_add': 0},
#         {'type': 'fixed_deposit', 'present_value': 0, 'expected_annual_return': 0, 'duration_years': 0, 'years_since': 0, 'convertible': None, 'monthly_add': 0, 'start_year': 0, 'maturity_year': 0, 'remaining_years': 0, 'monthly_contribution': 0, 'total_contributed': 0, 'maturity_value': 0, 'total_return': 0},
#         {'type': 'mutual_fund', 'present_value': 700000, 'expected_annual_return': 0.12, 'duration_years': 12, 'years_since': 7, 'convertible': True, 'monthly_add': 2000, 'start_year': 2018, 'maturity_year': 2030, 'remaining_years': 5, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 2727183.194782886, 'total_return': 2027183.1947828862},
#         {'type': 'direct_equity', 'present_value': 2000000, 'expected_annual_return': 0.15, 'duration_years': None, 'years_since': None, 'convertible': True, 'monthly_add': 2000},
#         {'type': 'provident_fund', 'present_value': 1200000, 'expected_annual_return': 0.08, 'duration_years': 15, 'years_since': 7, 'convertible': True, 'monthly_add': 2000, 'start_year': 2018, 'maturity_year': 2033, 'remaining_years': 8, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 3806602.937037926, 'total_return': 2606602.937037926},
#         {'type': 'public_provident_fund', 'present_value': 800000, 'expected_annual_return': 0.075, 'duration_years': 15, 'years_since': 7, 'convertible': True, 'monthly_add': 2000, 'start_year': 2018, 'maturity_year': 2033, 'remaining_years': 8, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 2367101.8822475923, 'total_return': 1567101.8822475923},
#         {'type': 'lic_policy', 'present_value': 500000, 'expected_annual_return': 0.06, 'duration_years': 20, 'years_since': 7, 'convertible': False, 'monthly_add': 2000, 'recommended_action': 'Stay in current scheme', 'start_year': 2018, 'maturity_year': 2038, 'remaining_years': 13, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 1603567.736106424, 'total_return': 1103567.736106424},
#         {'type': 'real_estate', 'properties': [
#             {'name': 'Primary Residence', 'value': 10000000, 'location': 'Mumbai', 'expected_annual_return': 0.06, 'duration_years': None, 'years_since': None, 'convertible': True, 'monthly_add': None},
#             {'name': 'Rental Apartment', 'value': 4500000, 'location': 'Pune', 'expected_annual_return': 0.055, 'duration_years': None, 'years_since': None, 'convertible': False, 'monthly_add': None}
#         ]}
#     ]
# }

def compute_surplus_usage(recommendation, loan_detail):
    """
    Given a monthly_surplus_used_for_emi and a list of loans with their EMIs and months_remaining,
    returns a breakdown of:
      - which months each EMI total applies
      - how much of the surplus is used vs. unused in that period
      - from what month the unused portion becomes available
    """
    ms = recommendation['monthly_surplus_used_for_emi']
    # sort loans by payoff ascending
    loans = sorted(loan_detail, key=lambda x: x['months_remaining'])
    # unpack
    personal = loans[0]
    car      = loans[1]
    home     = loans[2]

    # define segments
    segs = []
    # Segment 1: months 1 → personal payoff
    segs.append({
      "start": 1,
      "end": personal['months_remaining'],
      "emi_total": personal['emi'] + car['emi'] + home['emi']
    })
    # Segment 2: just after personal → car payoff
    segs.append({
      "start": personal['months_remaining'] + 1,
      "end": car['months_remaining'],
      "emi_total": car['emi'] + home['emi']
    })
    # Segment 3: after car → home payoff
    segs.append({
      "start": car['months_remaining'] + 1,
      "end": home['months_remaining'],
      "emi_total": home['emi']
    })

    utilization = []
    surplus_available = {}

    for seg in segs:
        used = min(ms, seg['emi_total'])
        unused = max(ms - seg['emi_total'], 0)
        utilization.append({
            "months": [seg['start'], seg['end']],
            "emi_total": seg['emi_total'],
            "surplus_used": used,
            "surplus_unused": unused
        })
        # record when unused surplus becomes available
        if unused > 0:
            surplus_available[seg['start']] = unused

    return {
      "monthly_surplus_utilization": utilization,
      "surplus_available_from": surplus_available
    }

# surplus_usage=compute_surplus_usage(recommendation, loan_detail)
# print(surplus_usage)

import math

# def generate_liquidation_plan(recommendation, sorted_asset_basket, liabilities_detail):
#     """
#     Hard-coded waterfall allocation:
#     1. Fully liquidate cash to cover the EMI shortfall for as many months as possible.
#     2. Then partially liquidate the fixed_deposit to fill the remaining car_loan gap.
#     3. Any leftover from that FD is earmarked for mutual funds.
#     4. Loan payoff schedule is passed through unchanged.
#     """

#     # 1) Extract parameters
#     monthly_gap = recommendation['assets_used']       # e.g. 7000
#     assets = sorted_asset_basket['asset_basket']
#     loans = liabilities_detail

#     # 2) Allocate Cash
#     cash = next(a for a in assets if a['type']=='cash')
#     cash_pv = cash['present_value']                   # 300000
#     # months cash can fund the gap
#     months_covered_cash = cash_pv // monthly_gap      # 42
#     plan_cash = {
#         "asset_type": "cash",
#         "amount_used": cash_pv,
#         "loans_funded": ["personal_loan", "car_loan"],
#         "months_funded": [1, int(months_covered_cash)]
#     }

#     # 3) Allocate Fixed Deposit next
#     fd = next(a for a in assets if a['type']=='fixed_deposit')
#     fd_pv = fd['present_value']                       # 250000
#     # As per your example, use only 50,000 of FD
#     fd_used = 50000
#     # Car loan payoff in 69 months, and we start FD at month 43
#     plan_fd = {
#         "asset_type": "fixed_deposit",
#         "amount_used": fd_used,
#         "loans_funded": ["car_loan"],
#         "months_funded": [int(months_covered_cash) + 1, 69]
#     }

#     # 4) Build loan clearance schedule
#     loan_clearance_schedule = [
#         {
#             "loan_type": ld["loan_type"],
#             "payoff_month": ld["months_remaining"],
#             "payoff_date": ld["payoff_date"]
#         }
#         for ld in loans
#     ]

#     # 5) Surplus Asset Allocation (remaining FD)
#     leftover_fd = fd_pv - fd_used                     # 200000
#     surplus_asset_allocation = [
#         {
#             "asset_type": "fixed_deposit",
#             "amount": leftover_fd,
#             "recommended_action": "Invest in mutual fund"
#         }
#     ]

#     # 6) Advice text
#     advice = (
#         "You will need to liquidate cash and part of fixed deposit to fund EMI gaps "
#         "until car and personal loans are paid off. After that, monthly surplus should "
#         "be sufficient for remaining EMIs. Invest remaining FD value for long-term growth."
#     )

#     # 7) Assemble and return
#     return {
#         "asset_liquidation_plan": [plan_cash, plan_fd],
#         "loan_clearance_schedule": loan_clearance_schedule,
#         "surplus_asset_allocation": surplus_asset_allocation,
#         "advice": advice
#     }

# # Example usage:
# recommendation = {
#     'monthly_surplus_used_for_emi': 48000.0,
#     'assets_used': 7000.0,
#     'recommendation': 'Monthly surplus (48000.0) is insufficient to cover EMI (55000). '
#                       'Recommend withdrawing ₹7000.00 from available assets (Total assets available: ₹20250000.00).',
#     'emi_to_pay': 55000,
#     'emi_percentage_of_income': 0.275
# }

# liabilities_detail = [
#     {'loan_type': 'home_loan', 'lender': 'HDFC Bank',
#      'outstanding_amount': 4000000, 'annual_interest_rate': 0.075,
#      'emi': 35000, 'months_remaining': 202, 'payoff_date': 'November 2041'},
#     {'loan_type': 'car_loan', 'lender': 'ICICI Bank',
#      'outstanding_amount': 800000, 'annual_interest_rate': 0.09,
#      'emi': 15000, 'months_remaining': 69, 'payoff_date': 'October 2030'},
#     {'loan_type': 'personal_loan', 'lender': 'Bajaj Finance',
#      'outstanding_amount': 200000, 'annual_interest_rate': 0.12,
#      'emi': 5000, 'months_remaining': 52, 'payoff_date': 'May 2029'}
# ]

# asset_basket_sorted = {
#     'monthly_surplus': 46000.0,
#     'asset_basket': [
#         {'type': 'cash', 'present_value': 300000, 'expected_annual_return': 0.03, 'duration_years': 0, 'years_since': None, 'convertible': True, 'monthly_add': 2000},
#         {'type': 'fixed_deposit', 'present_value': 250000, 'expected_annual_return': 0.065, 'duration_years': 10, 'years_since': 7, 'convertible': True, 'monthly_add': 2000, 'start_year': 2018, 'maturity_year': 2028, 'remaining_years': 3, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 469284.36631733977, 'total_return': 219284.36631733977},
#         {'type': 'mutual_fund', 'present_value': 700000, 'expected_annual_return': 0.12, 'duration_years': 12, 'years_since': 7, 'convertible': True, 'monthly_add': 2000, 'start_year': 2018, 'maturity_year': 2030, 'remaining_years': 5, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 2727183.194782886, 'total_return': 2027183.1947828862},
#         {'type': 'direct_equity', 'present_value': 2000000, 'expected_annual_return': 0.15, 'duration_years': None, 'years_since': None, 'convertible': True, 'monthly_add': 2000},
#         {'type': 'provident_fund', 'present_value': 1200000, 'expected_annual_return': 0.08, 'duration_years': 15, 'years_since': 7, 'convertible': True, 'monthly_add': 2000, 'start_year': 2018, 'maturity_year': 2033, 'remaining_years': 8, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 3806602.937037926, 'total_return': 2606602.937037926},
#         {'type': 'public_provident_fund', 'present_value': 800000, 'expected_annual_return': 0.075, 'duration_years': 15, 'years_since': 7, 'convertible': True, 'monthly_add': 2000, 'start_year': 2018, 'maturity_year': 2033, 'remaining_years': 8, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 2367101.8822475923, 'total_return': 1567101.8822475923},
#         {'type': 'lic_policy', 'present_value': 500000, 'expected_annual_return': 0.06, 'duration_years': 20, 'years_since': 7, 'convertible': False, 'monthly_add': 2000, 'recommended_action': 'Stay in current scheme', 'start_year': 2018, 'maturity_year': 2038, 'remaining_years': 13, 'monthly_contribution': 2000, 'total_contributed': 168000, 'maturity_value': 1603567.736106424, 'total_return': 1103567.736106424},
#         {'type': 'real_estate', 'properties': [
#             {'name': 'Primary Residence', 'value': 10000000, 'location': 'Mumbai', 'expected_annual_return': 0.06, 'duration_years': None, 'years_since': None, 'convertible': True, 'monthly_add': None},
#             {'name': 'Rental Apartment', 'value': 4500000, 'location': 'Pune', 'expected_annual_return': 0.055, 'duration_years': None, 'years_since': None, 'convertible': False, 'monthly_add': None}
#         ]}
#     ]
# }

# plan = generate_liquidation_plan(recommendation, sorted_asset_basket, loan_detail)
# print(json.dumps(plan, indent=2))

# import math

# def generate_liquidation_plan(recommendation, sorted_asset_basket, liabilities_detail):
#     """
#     1. Computes the per-month EMI gap segments:
#          • Segment1 (1 → personal_loan payoff): all EMIs active
#          • Segment2 (after personal_loan → car_loan payoff): car+home
#          • Segment3 (after car_loan → home_loan payoff): home only (gap zero)
#     2. Total GAP = gap1*seg1_months + gap2*seg2_months
#     3. Iterate assets in sorted order, skipping zero-value and non-convertible:
#          • Liquidate up to remaining_gap from each asset
#          • Record which segments/loans it funds
#     4. Any leftover of the last asset → invest
#     5. Return JSON structure.
#     """

#     # Inputs
#     monthly_surplus = recommendation['monthly_surplus_used_for_emi']
#     emi_to_pay      = recommendation['emi_to_pay']
#     monthly_gap     = max(emi_to_pay - monthly_surplus, 0)

#     # Sort loans by remaining months (earliest payoff first)
#     loans = sorted(liabilities_detail, key=lambda x: x['months_remaining'])
#     p_loan, c_loan, h_loan = loans

#     # Segment definitions
#     seg1_months = p_loan['months_remaining']
#     seg2_months = c_loan['months_remaining'] - seg1_months

#     # EMI sums for each segment
#     gap1 = max(p_loan['emi'] + c_loan['emi'] + h_loan['emi'] - monthly_surplus, 0)
#     gap2 = max(c_loan['emi'] + h_loan['emi'] - monthly_surplus, 0)

#     # Total gap amount needed
#     total_gap = seg1_months * gap1 + seg2_months * gap2

#     remaining_gap = total_gap
#     plan = []
#     leftover_asset_info = None  # To track the last asset used and its leftover
#     current_month = 1  # Tracking start month for each allocation

#     for asset in sorted_asset_basket['asset_basket']:
#         if remaining_gap <= 0:
#             break
#         # Skip zero or non-convertible or real_estate container
#         if not asset.get('convertible', True) or asset.get('type') == 'real_estate':
#             continue
#         pv = asset.get('present_value', 0)
#         if pv <= 0:
#             continue

#         used = min(pv, remaining_gap)
#         remaining_gap -= used

#         # Determine which months this asset funds
#         months_funded_start = current_month
#         if used > 0:
#             if used >= seg1_months * gap1:
#                 # Covers all of segment 1 and possibly more
#                 seg1_covered = seg1_months
#                 used_left = used - seg1_months * gap1
#                 seg2_covered = min(seg2_months, int(used_left // gap2) if gap2 > 0 else 0)
#             else:
#                 # Only partial segment 1 is covered
#                 seg1_covered = int(used // gap1) if gap1 > 0 else 0
#                 seg2_covered = 0
#             # months_funded: [start_month, end_month]
#             months_funded_end = months_funded_start + seg1_covered + seg2_covered - 1
#             if months_funded_end < months_funded_start:
#                 months_funded_end = months_funded_start  # Avoid invalid range
#         else:
#             seg1_covered = seg2_covered = 0
#             months_funded_end = months_funded_start

#         # Update for next allocation
#         current_month += seg1_covered + seg2_covered

#         # Loans funded
#         loans_funded = []
#         if seg1_covered > 0:
#             loans_funded = [p_loan['loan_type'], c_loan['loan_type'], h_loan['loan_type']]
#         if seg2_covered > 0:
#             loans_funded = [c_loan['loan_type'], h_loan['loan_type']]

#         plan.append({
#             "asset_type": asset['type'],
#             "amount_used": used,
#             "loans_funded": loans_funded,
#             "months_funded": [months_funded_start, months_funded_end]
#         })

#         # Track the leftover for surplus allocation
#         if used < pv:
#             leftover_asset_info = {
#                 "asset_type": asset['type'],
#                 "amount": round(pv - used, 2),
#                 "recommended_action": "Invest leftover in mutual fund"
#             }
#         else:
#             leftover_asset_info = None  # No leftover in this asset

#     # Loan clearance schedule pass-through
#     clearance = [
#         {"loan_type": l["loan_type"], "payoff_month": l["months_remaining"], "payoff_date": l["payoff_date"]}
#         for l in loans
#     ]

#     # Surplus allocation: Only mention last asset actually used
#     surplus_asset_allocation = []
#     if leftover_asset_info:
#         surplus_asset_allocation.append(leftover_asset_info)

#     advice = (
#         f"Liquidated {float(total_gap):,} across {len(plan)} asset(s) to meet the EMI shortfall. "
#         "Once the shortest-term loans are paid, your monthly surplus covers the rest. "
#         "Reinvest any leftover capital for growth."
#     )

#     return {
#         "asset_liquidation_plan": plan,
#         "loan_clearance_schedule": clearance,
#         "surplus_asset_allocation": surplus_asset_allocation,
#         "advice": advice
#     }

def generate_liquidation_plan(recommendation, sorted_asset_basket, liabilities_detail):
    """
    Extended: Also outputs monthly surplus used and unused in each period.
    """

    # Inputs
    monthly_surplus = recommendation['monthly_surplus_used_for_emi']
    emi_to_pay      = recommendation['emi_to_pay']
    monthly_gap     = max(emi_to_pay - monthly_surplus, 0)

    # Sort loans by remaining months (earliest payoff first)
    loans = sorted(liabilities_detail, key=lambda x: x['months_remaining'])
    p_loan, c_loan, h_loan = loans

    # Segment definitions
    seg1_months = p_loan['months_remaining']
    seg2_months = c_loan['months_remaining'] - seg1_months

    # EMI sums for each segment
    gap1 = max(p_loan['emi'] + c_loan['emi'] + h_loan['emi'] - monthly_surplus, 0)
    gap2 = max(c_loan['emi'] + h_loan['emi'] - monthly_surplus, 0)

    # For monthly surplus utilization
    monthly_surplus_utilization = []

    # Segment 1: all loans active (months 1 to seg1_months)
    total_emi_seg1 = p_loan['emi'] + c_loan['emi'] + h_loan['emi']
    used_surplus_seg1 = min(monthly_surplus, total_emi_seg1)
    unused_surplus_seg1 = max(monthly_surplus - total_emi_seg1, 0)
    monthly_surplus_utilization.append({
        "months": [1, seg1_months],
        "emi_total": total_emi_seg1,
        "surplus_used": used_surplus_seg1,
        "surplus_unused": unused_surplus_seg1
    })

    # Segment 2: only car + home loan active (months seg1_months+1 to c_loan['months_remaining'])
    if seg2_months > 0:
        total_emi_seg2 = c_loan['emi'] + h_loan['emi']
        used_surplus_seg2 = min(monthly_surplus, total_emi_seg2)
        unused_surplus_seg2 = max(monthly_surplus - total_emi_seg2, 0)
        monthly_surplus_utilization.append({
            "months": [seg1_months+1, c_loan['months_remaining']],
            "emi_total": total_emi_seg2,
            "surplus_used": used_surplus_seg2,
            "surplus_unused": unused_surplus_seg2
        })

    # Segment 3: only home loan active (months c_loan['months_remaining']+1 to h_loan['months_remaining'])
    if h_loan['months_remaining'] > c_loan['months_remaining']:
        total_emi_seg3 = h_loan['emi']
        used_surplus_seg3 = min(monthly_surplus, total_emi_seg3)
        unused_surplus_seg3 = max(monthly_surplus - total_emi_seg3, 0)
        monthly_surplus_utilization.append({
            "months": [c_loan['months_remaining']+1, h_loan['months_remaining']],
            "emi_total": total_emi_seg3,
            "surplus_used": used_surplus_seg3,
            "surplus_unused": unused_surplus_seg3
        })

    # -- (Existing code for asset liquidation plan) --
    total_gap = seg1_months * gap1 + seg2_months * gap2
    remaining_gap = total_gap
    plan = []
    leftover_asset_info = None
    current_month = 1

    for asset in sorted_asset_basket['asset_basket']:
        if remaining_gap <= 0:
            break
        if not asset.get('convertible', True) or asset.get('type') == 'real_estate':
            continue
        pv = asset.get('present_value', 0)
        if pv <= 0:
            continue

        used = min(pv, remaining_gap)
        remaining_gap -= used

        months_funded_start = current_month
        if used > 0:
            if used >= seg1_months * gap1:
                seg1_covered = seg1_months
                used_left = used - seg1_months * gap1
                seg2_covered = min(seg2_months, int(used_left // gap2) if gap2 > 0 else 0)
            else:
                seg1_covered = int(used // gap1) if gap1 > 0 else 0
                seg2_covered = 0
            months_funded_end = months_funded_start + seg1_covered + seg2_covered - 1
            if months_funded_end < months_funded_start:
                months_funded_end = months_funded_start
        else:
            seg1_covered = seg2_covered = 0
            months_funded_end = months_funded_start

        current_month += seg1_covered + seg2_covered

        loans_funded = []
        if seg1_covered > 0:
            loans_funded = [p_loan['loan_type'], c_loan['loan_type'], h_loan['loan_type']]
        if seg2_covered > 0:
            loans_funded = [c_loan['loan_type'], h_loan['loan_type']]

        plan.append({
            "asset_type": asset['type'],
            "amount_used": used,
            "loans_funded": loans_funded,
            "months_funded": [months_funded_start, months_funded_end]
        })

        if used < pv:
            leftover_asset_info = {
                "asset_type": asset['type'],
                "amount": round(pv - used, 2),
                "recommended_action": "Invest leftover in mutual fund"
            }
        else:
            leftover_asset_info = None

    clearance = [
        {"loan_type": l["loan_type"], "payoff_month": l["months_remaining"], "payoff_date": l["payoff_date"]}
        for l in loans
    ]
    surplus_asset_allocation = []
    if leftover_asset_info:
        surplus_asset_allocation.append(leftover_asset_info)

    advice = (
        f"Liquidated {float(total_gap):,} across {len(plan)} asset(s) to meet the EMI shortfall. "
        "Once the shortest-term loans are paid, your monthly surplus covers the rest. "
        "Reinvest any leftover capital for growth."
    )

    return {
        "asset_liquidation_plan": plan,
        "loan_clearance_schedule": clearance,
        "surplus_asset_allocation": surplus_asset_allocation,
        "monthly_surplus_utilization": monthly_surplus_utilization,
        "advice": advice
    }

# liquidation_plan=generate_liquidation_plan(recommendation, asset_basket_sorted, loan_detail)
# print(liquidation_plan)

def update_asset_basket_sorted(asset_basket_sorted, liquidation_plan):
    """
    Update asset_basket_sorted:
      - Depletes (zeroes out) assets used in liquidation_plan.
      - If surplus_asset_allocation is present, transfer that amount to cash (add or update cash asset).
      - If the surplus comes from a depleted asset, zero it in the basket.
    Returns updated asset basket, no monthly_surplus.
    """
    import copy
    updated_basket = copy.deepcopy(asset_basket_sorted)
    basket = updated_basket['asset_basket']

    # Build lookup for asset index by type (skipping real_estate for mapping)
    asset_type_to_idx = {a['type']: idx for idx, a in enumerate(basket) if a['type'] != 'real_estate'}

    # 1. Deplete assets used in liquidation plan
    depleted_assets = set()
    for used in liquidation_plan['asset_liquidation_plan']:
        atype = used['asset_type']
        amt_used = used['amount_used']
        idx = asset_type_to_idx.get(atype, None)
        if idx is not None:
            pv = basket[idx].get('present_value', 0)
            # If the asset is fully used (all value liquidated OR present_value - amt_used <= 1e-2)
            if abs(pv - amt_used) < 1e-2 or amt_used >= pv:
                # Zero-out all numeric fields
                for k in basket[idx]:
                    if isinstance(basket[idx][k], (int, float)):
                        basket[idx][k] = 0
                basket[idx]['present_value'] = 0
                depleted_assets.add(atype)
            else:
                # Only partial use, reduce present_value
                basket[idx]['present_value'] = pv - amt_used

    # 2. Add surplus to cash, and if from a depleted asset, keep only in cash
    if liquidation_plan['surplus_asset_allocation']:
        surplus = liquidation_plan['surplus_asset_allocation'][0]
        surplus_amt = surplus['amount']
        surplus_asset_type = surplus['asset_type']
        cash_idx = asset_type_to_idx.get('cash', None)
        if cash_idx is not None:
            basket[cash_idx]['present_value'] = surplus_amt
            basket[cash_idx]['expected_annual_return'] = 0.03
            basket[cash_idx]['convertible'] = True
            basket[cash_idx]['duration_years'] = 0
            basket[cash_idx]['monthly_add'] = 0
        else:
            # If cash section is missing, insert at the top
            basket.insert(0, {
                'type': 'cash',
                'present_value': surplus_amt,
                'expected_annual_return': 0.03,
                'duration_years': 0,
                'years_since': None,
                'convertible': True,
                'monthly_add': 0
            })

        # If the surplus asset was depleted, ensure its present_value is 0 (do not double count)
        idx_surplus = asset_type_to_idx.get(surplus_asset_type, None)
        if idx_surplus is not None and basket[idx_surplus]['present_value'] != 0:
            for k in basket[idx_surplus]:
                if isinstance(basket[idx_surplus][k], (int, float)):
                    basket[idx_surplus][k] = 0
            basket[idx_surplus]['present_value'] = 0

    # Remove monthly_surplus if present
    updated_basket.pop('monthly_surplus', None)

    return updated_basket

# updated_basket = update_asset_basket_sorted(asset_basket_sorted, liquidation_plan)
# print(updated_basket)

def compute_surplus_after_assets(recommendation, loan_detail):
    """
    Given:
      - recommendation['monthly_surplus_used_for_emi']: the portion of surplus actually used each month
      - recommendation['assets_used']: one-time lump sum from assets to cover the remainder of the EMI shortfall
      - loan_detail: list of loans with 'emi' and 'months_remaining'
    Returns:
      {
        "monthly_surplus_utilization": [...],
        "surplus_available_from": {...}
      }
    """
    # 1) effective monthly surplus now in use
    ms = recommendation['monthly_surplus_used_for_emi']

    # 2) sort loans by payoff ascending
    loans = sorted(loan_detail, key=lambda x: x['months_remaining'])
    p, c, h = loans

    # 3) segment lengths
    seg1 = p['months_remaining']
    seg2 = c['months_remaining'] - seg1
    seg3 = h['months_remaining'] - c['months_remaining']

    # 4) EMIs in each segment
    emi1 = p['emi'] + c['emi'] + h['emi']
    emi2 = c['emi'] + h['emi']
    emi3 = h['emi']

    # 5) build utilization
    util = []
    avail = {}

    segments = [
        (1, seg1, emi1),
        (seg1+1, seg1+seg2, emi2),
        (seg1+seg2+1, h['months_remaining'], emi3),
    ]

    for start, end, emi_total in segments:
        if end < start:
            continue
        used   = min(ms, emi_total)
        unused = max(0, ms - used)
        util.append({
            "months": [start, end],
            "emi_total": emi_total,
            "surplus_used": used,
            "surplus_unused": unused
        })
        if unused > 0:
            avail[str(start)] = unused

    return {
        "monthly_surplus_utilization": util,
        "surplus_available_from": avail
    }

# surplus_available=compute_surplus_after_assets(recommendation, loan_detail)
# print([surplus_available])

# cashflows=[{'monthly_surplus_utilization': [{'months': [1, 52],
#    'emi_total': 55000,
#    'surplus_used': 46000.0,
#    'surplus_unused': 0},
#   {'months': [53, 69],
#    'emi_total': 50000,
#    'surplus_used': 46000.0,
#    'surplus_unused': 0},
#   {'months': [70, 202],
#    'emi_total': 35000,
#    'surplus_used': 35000,
#    'surplus_unused': 11000.0}],
#  'surplus_available_from': {'70': 11000.0}}]

from typing import List, Dict

# current_monthly=3000
# total_needed=4000

def _calculate_with_future_cashflows(
                                     current_monthly: float,
                                     total_needed: float,
                                     cashflows: list[dict]) -> float:
    """
    Calculate how many months (possibly fractional) it will take to accumulate
    `total_needed`, starting at `current_monthly` per month, and then at certain
    future months getting an extra recurring boost defined by:
      cashflows = [
        {
          'monthly_surplus_utilization': [ ... ],      # ignored here
          'surplus_available_from': {'70': 11000.0, ...}
        },
        ...
      ]
    For each entry in surplus_available_from, at the beginning of that month the
    monthly_amount increases by the given value.
    Returns the (possibly fractional) month count to reach or exceed total_needed.
    """

    # 1) Extract boost events from the new structure
    boosts = []
    for block in cashflows:
        for month_str, extra in block.get('surplus_available_from', {}).items():
            try:
                m = int(month_str)
            except ValueError:
                continue
            if extra and m > 0:
                boosts.append({"month": m, "additional_monthly_amount": extra})

    accumulated    = 0.0
    month_count    = 0
    monthly_amount = current_monthly

    # Simulate month by month, up to a 20-year cap (240 months)
    while accumulated < total_needed and month_count < 240:
        month_count += 1

        # Apply any boost at the start of this month
        for b in boosts:
            if b["month"] == month_count:
                monthly_amount += b["additional_monthly_amount"]

        # If this month's full contribution meets or exceeds the target,
        # return a fractional month count
        # if accumulated + monthly_amount >= total_needed:
        #     needed   = total_needed - accumulated
        #     fraction = needed / monthly_amount
        #     return (month_count - 1) + fraction

        accumulated += monthly_amount

    # If we exit without hitting total_needed exactly, return the month count
    return month_count



# o=_calculate_with_future_cashflows(current_monthly, total_needed, cashflows)

def sort_goals(derived_client_data, goal_preferences=None):
    """
    Sorts the goals section based on client preference or a standard priority logic.

    Args:
        derived_client_data: dict containing 'goals' as a list of goal dicts.
        goal_preferences: optional list of goal IDs (see format below).

    Returns:
        List of goals sorted by client preference or recommended logic.
    """

    goals = derived_client_data.get("goals", [])

    # Attach unique IDs for mapping preferences (if needed)
    def goal_id(g):
        # Examples: "Education-Alice-undergraduate", "Retirement", "Custom-Start Business"
        if g["type"].lower() == "education":
            return f"Education-{g.get('beneficiary','')}-{g.get('level','')}"
        elif g["type"].lower() == "retirement":
            return "Retirement"
        elif g["type"].lower() == "vacation":
            return f"Vacation-{g.get('name','')}-{g.get('year','')}"
        elif g["type"].lower() == "custom":
            return f"Custom-{g.get('name','')}"
        else:
            return str(g)

    for g in goals:
        g["_goal_id"] = goal_id(g)

    # If client has a preferred order, use that
    if goal_preferences:
        # Make a mapping of ID to order index
        order_map = {k: i for i, k in enumerate(goal_preferences)}
        goals_sorted = sorted(
            goals,
            key=lambda g: order_map.get(g["_goal_id"], 999)
        )
        for g in goals_sorted:
            g.pop("_goal_id", None)
        return goals_sorted

    # Otherwise, sort according to business rules
    def priority_key(g):
        t = g["type"].lower()
        # 1. Undergraduate Education
        if t == "education" and g.get("level", "").lower() == "undergraduate":
            return (1, g.get("years_left", 99), 0)
        # 2. Retirement
        if t == "retirement":
            return (2, g.get("years_left", 99), 1)
        # 3. Postgraduate Education
        if t == "education" and g.get("level", "").lower() == "postgraduate":
            return (3, g.get("years_left", 99), 2)
        # 4. Others, by years_left
        # (Vacation, Custom, etc.)
        return (4, g.get("years_left", 99), 3 if t == "vacation" else 4)

    goals_sorted = sorted(goals, key=priority_key)
    for g in goals_sorted:
        g.pop("_goal_id", None)
    return goals_sorted


# result = sort_goals(derived)
# for goal in result:
#     print(goal)


# def allocate_funds_to_goals(
#     goals,                # List of goals (sorted)
#     assets,               # Assets dict (as per example)
#     future_cashflows,     # From your output above
#     monthly_income,       # e.g. 200000
#     allocation_ratio=0.75 # 75% of available monthly income can be used
# ):
#     """
#     Allocates available liquid assets and future surplus cashflows to the client's goals in an optimized fashion.
#     Returns a funding plan per goal with source breakdown.
#     """
#     import copy

#     # Sort goals (reusing your logic)
#     def goal_priority(g):
#         t = g["type"].lower()
#         if t == "education" and g.get("level", "").lower() == "undergraduate":
#             return (1, g.get("years_left", 99), 0)
#         if t == "retirement":
#             return (2, g.get("years_left", 99), 1)
#         if t == "education" and g.get("level", "").lower() == "postgraduate":
#             return (3, g.get("years_left", 99), 2)
#         return (4, g.get("years_left", 99), 3 if t == "vacation" else 4)
#     goals_sorted = sorted(goals, key=goal_priority)

#     # Step 1: Extract liquid asset pools (skip real estate, LIC etc.)
#     liquid_assets = []
#     for asset in assets["asset_basket"]:
#         if asset["type"] in ["cash", "fixed_deposit", "mutual_fund", "direct_equity", "public_provident_fund", "provident_fund"]:
#             if asset.get("present_value", 0) > 0:
#                 liquid_assets.append({
#                     "type": asset["type"],
#                     "available": asset["present_value"]
#                 })

#     # Step 2: Build a month-wise available cashflow timeline
#     # Get future monthly surplus changes
#     monthly_timeline = {}
#     for period in future_cashflows['monthly_surplus_utilization']:
#         start, end = period['months']
#         for m in range(start, end+1):
#             # Only 75% is allocatable to goals
#             surplus_used = period['surplus_unused'] if period['surplus_unused'] > 0 else 0
#             # If full surplus gets used for EMIs, only use actual unused
#             monthly_timeline[m] = allocation_ratio * (period['surplus_unused'] + period['surplus_used'] if surplus_used == 0 else surplus_used)
#     # After all EMIs end, client can save up to allocation_ratio * monthly_income
#     last_month = max(monthly_timeline) if monthly_timeline else 1
#     for m in range(last_month+1, last_month+121):  # Plan for 10 more years
#         monthly_timeline[m] = allocation_ratio * monthly_income

#     # Step 3: Allocate assets and future cashflows to goals
#     goal_plans = []
#     current_assets = copy.deepcopy(liquid_assets)
#     used_assets = {}
#     available_month = 1
#     for goal in goals_sorted:
#         goal_cost = goal.get('projected_goal', goal.get('initial_goal', 0))
#         required = goal_cost
#         allocation = []
#         # Use available assets first (waterfall)
#         for asset in current_assets:
#             if required <= 0:
#                 break
#             amt = min(asset["available"], required)
#             if amt > 0:
#                 allocation.append({
#                     "source": asset["type"],
#                     "amount": amt,
#                     "funding_month": available_month
#                 })
#                 used_assets.setdefault(asset["type"], 0)
#                 used_assets[asset["type"]] += amt
#                 asset["available"] -= amt
#                 required -= amt
#         # If still needed, roll forward using monthly cashflow
#         month = available_month
#         monthly_needed = 0
#         if required > 0:
#             plan_months = []
#             while required > 0 and month < last_month+121:
#                 alloc = monthly_timeline.get(month, allocation_ratio * monthly_income)
#                 use = min(alloc, required)
#                 if use > 0:
#                     allocation.append({
#                         "source": "future_surplus",
#                         "amount": use,
#                         "funding_month": month
#                     })
#                     required -= use
#                 month += 1
#             funding_end_month = month - 1
#         else:
#             funding_end_month = available_month
#         # Save allocation plan for this goal
#         goal_plans.append({
#             "goal": {
#                 "type": goal["type"],
#                 "name": goal.get("name", goal.get("beneficiary", "")),
#                 "level": goal.get("level", ""),
#                 "target": goal_cost,
#                 "years_left": goal.get("years_left", None)
#             },
#             "allocated": allocation,
#             "funding_complete_month": funding_end_month,
#             "fully_funded": required <= 0
#         })
#         # Move forward for next goal (do not re-use asset or cashflow already spent)
#         available_month = max(funding_end_month, available_month)
#         # Remove depleted assets
#         current_assets = [a for a in current_assets if a["available"] > 0]

#     return goal_plans

# # ---------------------------
# result = allocate_funds_to_goals(
#     result,
#     updated_basket,
#     liquidation_plan,
#     monthly_income=200000,
#     allocation_ratio=0.75
# )
# for plan in result:
#     print(plan)
# # ---------------------------











