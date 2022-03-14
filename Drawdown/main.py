# run at the beginning of the year for an estimate of the upcoming year

from accounts import Account
from investments import Investment, InvestmentType


def sum_accounts():
    total = 0
    for acc in accounts:
        total += acc.balance()
    return total


def move_money(from_investment, to_investment, amount, fees=0):
    from_investment.balance -= amount
    to_investment.balance += amount - fees


current_age = 29
retirement_age = 32
annual_withdrawals = 7100000
RE_allocation = 0.4
bond_allocation = 0
equity_cash_flow = 0.02
bond_cash_flow = 0.025
blended_cash_flow = equity_cash_flow * (1 - bond_allocation) + bond_cash_flow * bond_allocation
equity_appreciation = 0.095 - equity_cash_flow
bond_appreciation = 0.0
blended_appreciation = equity_appreciation * (1 - bond_allocation) + bond_appreciation * bond_allocation

# equities = InvestmentType(cash_flow_rate=equity_cash_flow, price_appreciation=equity_appreciation, liquid=True)
# bonds = InvestmentType(cash_flow_rate=bond_cash_flow, price_appreciation=bond_appreciation, liquid=True)
equities_n_bonds = InvestmentType(cash_flow_rate=blended_cash_flow, price_appreciation=blended_appreciation,
                                  liquid=True)
MF_funds = InvestmentType(cash_flow_rate=0.07, liquid=False)
real_property = InvestmentType(cash_flow_rate=0.05, liquid=False)
waymo_units = InvestmentType(cash_flow_rate=0,liquid=False)

taxable = Account(name="Taxable", investments=[Investment(300000, real_property), Investment(330000, MF_funds),
                                               Investment(0, equities_n_bonds), Investment(0,waymo_units)])
tIRA = Account(name="Traditional IRA", investments=[Investment(650000, equities_n_bonds)])
acc_457b = Account(name="457b", investments=[Investment(170000, equities_n_bonds)])
rIRA = Account(name="Roth", investments=[Investment(50000, MF_funds), Investment(144000, equities_n_bonds)], roth=True,
               roth_basis=96000)
hsa = Account(name="HSA", investments=[Investment(97000, equities_n_bonds)])
# manual account ordering for now. Being lazy putting rIRA there so that you can just move smoothly from basis to gains
accounts = [taxable, acc_457b, tIRA, rIRA, hsa]

my_properties = taxable.investments[0]
private_equity_taxable = taxable.investments[1]
liquid_assets = taxable.investments[2]
waymo = taxable.investments[3]
private_equity_rIRA = rIRA.investments[0]

# unexpected distributions
my_properties.additional_dist = 30000
private_equity_taxable.additional_dist = 60000
private_equity_rIRA.additional_dist = 20000
waymo.additional_dist = 15000


total_dist = 0
for account in accounts:
    for investment in account.investments:
        distribution = investment.grow()
        if account == taxable:
            total_dist += distribution
            move_money(from_investment=investment, to_investment=liquid_assets, amount=distribution)
print(f"Total Cash Flow: ${int(total_dist)}")

# First, real estate has to be made whole to its target allocation. Assuming that we don't want to make more IRA RE
# Challenge here is finding the correct algebra to accommodate the cost of purchasing property while also maintaining
#   the ratio of real to private property. Hard to know how much capital is needed ahead of time to maintain ratio
#   after costs
print("Reinvestment Plan")
targeted_RE_balance = RE_allocation * sum_accounts()
total_RE_balance = my_properties.balance + private_equity_taxable.balance + private_equity_rIRA.balance
if total_RE_balance < targeted_RE_balance:
    RE_needed = targeted_RE_balance - total_RE_balance
    real_to_private_ratio = my_properties.balance / (private_equity_taxable.balance + private_equity_rIRA.balance)
    trans_fees = .25  # closing costs + repair
    prop_needed = (real_to_private_ratio * RE_needed) / (1 + real_to_private_ratio)
    capital_needed = RE_needed + prop_needed * (1 / (1 - trans_fees) - 1)
    prop_purchased = 0
    prop_cost = 0
    if capital_needed < liquid_assets.balance:
        prop_purchased = prop_needed
    else:
        prop_purchased = (liquid_assets.balance - liquid_assets.balance * trans_fees) / (
                1 - (trans_fees - 1) / real_to_private_ratio)
    prop_cost = prop_purchased / (1 - trans_fees)  # how much it cost to buy that property
    move_money(from_investment=liquid_assets, to_investment=my_properties, amount=prop_cost,
               fees=prop_cost * trans_fees)
    print(f"Invest ${int(prop_purchased)} in real property for ${int(prop_cost)}")
    equity_purchased = prop_purchased / real_to_private_ratio
    move_money(from_investment=liquid_assets, to_investment=private_equity_taxable, amount=equity_purchased)
    print(f"Invest ${int(equity_purchased)} in private equity")
else:
    print(f"Suggestion: Liquidate ${total_RE_balance - targeted_RE_balance} of real estate")
# Test that shows it's not quite right. You have to add the trans_fees to the sum_accounts to get the right ratio
# print((my_properties.balance + private_equity_taxable.balance + private_equity_rIRA.balance) / (sum_accounts()+14034))

# Then, need to decide where to pull remaining needed funds from
print("Withdrawal plan")
remaining_need = annual_withdrawals
if liquid_assets.balance > remaining_need:
    liquid_assets.balance -= remaining_need
    remaining_need = 0
    print(f"Enough remaining in liquid assets to cover annual needs: ${int(annual_withdrawals)}")
    print(f"Remaining liquid assets: ${int(liquid_assets.balance)}")
else:
    remaining_need -= liquid_assets.balance
    print(f"Remove ${int(liquid_assets.balance)} from liquid assets")
    liquid_assets.balance = 0

# Roth IRA basis
total_roth_removed = 0
for investment in rIRA.investments:
    removal_amount = min(investment.balance, remaining_need, rIRA.roth_basis - total_roth_removed)
    if removal_amount != 0 and investment.liquid:
        total_roth_removed += removal_amount
        remaining_need -= removal_amount
        move_money(from_investment=investment, to_investment=liquid_assets, amount=removal_amount)
        print(f"Remove ${int(removal_amount)} from {rIRA.name} basis")

# 457 -> Roth IRA gains -> tIRA -> HSA
for account in accounts[1:]:
    for investment in account.investments:
        removal_amount = min(investment.balance, remaining_need)
        if removal_amount != 0 and investment.liquid:
            remaining_need -= removal_amount
            move_money(from_investment=investment, to_investment=liquid_assets, amount=removal_amount)
            print(f"Remove ${int(removal_amount)} from {account.name}")
