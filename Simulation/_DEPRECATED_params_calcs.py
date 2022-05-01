def sum_yearly_budget(monthly_list,yearly_list):
    return sum([12*n for n in monthly_list])+sum(yearly_list)