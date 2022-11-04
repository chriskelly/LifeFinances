
class Income:
    def __init__(self,income_obj:dict,previous_income):
        self.previous_income = previous_income
        self.duration = income_obj['Duration']
        self.income_qt = income_obj['Starting Income'] / 4
        
    def start_year(self):
        """Returns the index for the date_ls"""
        if not self.previous_income:
            return 0
        else:
            return self.previous_income.start_year() + self.previous_income.duration/.25
        
        
        
def generate_incomes(incomes:list[dict]):
    income_objs = [Income(incomes[0],previous_income=None)]
    for i in range(1,len(incomes)):
        income_objs.append(Income(incomes[i],previous_income=income_objs[-1]))
    return income_objs