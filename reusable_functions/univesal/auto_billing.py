from payments.models import ExpensesType, Expense
from accounts.models import User

from dateutil.relativedelta import relativedelta
from datetime import datetime as datetime_


def auto_bill(request):
    today = datetime_.strptime(str(datetime_.today())[:10],"%Y-%m-%d").date()
    reoccurring_expense_types = ExpensesType.objects.filter(reoccurring=True, active=True).exclude(reoccurring_interval="NONE")
    for expense_type in reoccurring_expense_types:
        last_bill_date = Expense.objects.filter(expense_type=expense_type).order_by('date').last().date if Expense.objects.filter(expense_type=expense_type) else today

        if expense_type.reoccurring_interval == "DAILY":
            for i in range(31):
                scale = relativedelta(days=i)
                new_date = datetime_.strptime(str(last_bill_date + scale)[:10],"%Y-%m-%d").date()
                if (new_date < today):
                    if (str(new_date)[:10] != str(last_bill_date)[:10]):
                        new_bill = Expense()
                        new_bill.expense_type = expense_type
                        new_bill.description = expense_type.description
                        new_bill.date = new_date
                        new_bill.price = expense_type.default_price
                        new_bill.created_by = User.objects.filter(is_superuser=True).first()
                        new_bill.save()
                else:
                    return

        if expense_type.reoccurring_interval == "WEEKLY":
            for i in range(31):
                scale = relativedelta(weeks=i)
                new_date = datetime_.strptime(str(last_bill_date + scale)[:10],"%Y-%m-%d").date()
                if (new_date < today):
                    if (str(new_date)[:10] != str(last_bill_date)[:10]):
                        new_bill = Expense()
                        new_bill.expense_type = expense_type
                        new_bill.description = expense_type.description
                        new_bill.date = new_date
                        new_bill.price = expense_type.default_price
                        new_bill.created_by = User.objects.filter(is_superuser=True).first()
                        new_bill.save()
                else:
                    return

        if expense_type.reoccurring_interval == "MONTHLY":
            for i in range(31):
                scale = relativedelta(months=i)
                new_date = datetime_.strptime(str(last_bill_date + scale)[:10],"%Y-%m-%d").date()
                if (new_date < today):
                    if (str(new_date)[:10] != str(last_bill_date)[:10]):
                        new_bill = Expense()
                        new_bill.expense_type = expense_type
                        new_bill.description = expense_type.description
                        new_bill.date = new_date
                        new_bill.price = expense_type.default_price
                        new_bill.created_by = User.objects.filter(is_superuser=True).first()
                        new_bill.save()
                else:
                    return

        if expense_type.reoccurring_interval == "ANUALY":
            for i in range(31):
                scale = relativedelta(years=i)
                new_date = datetime_.strptime(str(last_bill_date + scale)[:10],"%Y-%m-%d").date()
                if (new_date < today):
                    if (str(new_date)[:10] != str(last_bill_date)[:10]):
                        new_bill = Expense()
                        new_bill.expense_type = expense_type
                        new_bill.description = expense_type.description
                        new_bill.date = new_date
                        new_bill.price = expense_type.default_price
                        new_bill.created_by = User.objects.filter(is_superuser=True).first()
                        new_bill.save()
                else:
                    return


    return 0

