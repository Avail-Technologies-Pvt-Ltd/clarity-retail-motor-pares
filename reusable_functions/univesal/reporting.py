
def group_money_portions_by_payment_methods(money_portions_query, portion_type):
    if portion_type == "ReceiptMoneyPortion":
        receiptmoneyportions = money_portions_query
        portion_currencies = {}

        for receiptmoneyportion in receiptmoneyportions:
            current_key = receiptmoneyportion.payment_method.id
            payment_method = receiptmoneyportion.payment_method

            if current_key not in portion_currencies:
                # Add new entry if key doesn't exist
                shortcut = f'{payment_method.shortcut}'
                amount_paid = f'{receiptmoneyportion.amount_paid}'
                value = f'{receiptmoneyportion.rated_amount}'
                portion_currencies[current_key] = [shortcut, amount_paid, value]
            else:
                # Alter existing entry if key exists
                existing_shortcut, existing_amount, existing_value = portion_currencies[current_key]
                shortcut = f'{payment_method.shortcut}'
                amount_paid = f'{ float(receiptmoneyportion.amount_paid) + float(existing_amount)}'
                value = f'{ float(receiptmoneyportion.rated_amount) + float(existing_value)}'
                portion_currencies[current_key] = [shortcut, amount_paid, value]

        return portion_currencies


def group_money_portions_into_dict(receiptmoneyportions, refundreturnoutmoneyportions, invoicemoneyportions, expensemoneyportions, refundreturninnmoneyportions):
    #   income totals
    income_currencies = {} #{id:['shortcut','amount','value']}

    for receiptmoneyportion in receiptmoneyportions:
        current_key = receiptmoneyportion.payment_method.id
        payment_method = receiptmoneyportion.payment_method

        if current_key not in income_currencies:
            # Add new entry if key doesn't exist
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{receiptmoneyportion.amount_paid}'
            value = f'{receiptmoneyportion.rated_value}'
            income_currencies[current_key] = [shortcut, amount_paid, value]
        else:
            # Alter existing entry if key exists
            existing_shortcut, existing_amount, existing_value = income_currencies[current_key]
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{ float(receiptmoneyportion.amount_paid) + float(existing_amount)}'
            value = f'{ float(receiptmoneyportion.rated_value) + float(existing_value)}'
            income_currencies[current_key] = [shortcut, amount_paid, value]
    

    
    for refundreturnoutmoneyportion in refundreturnoutmoneyportions:
        # print(refundreturnoutmoneyportion.created_at)
        current_key = refundreturnoutmoneyportion.payment_method.id
        payment_method = refundreturnoutmoneyportion.payment_method

        if current_key not in income_currencies:
            # Add new entry if key doesn't exist
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{refundreturnoutmoneyportion.amount_paid}'
            value = f'{refundreturnoutmoneyportion.rated_amount}'
            income_currencies[current_key] = [shortcut, amount_paid, value]
        else:
            # Alter existing entry if key exists
            existing_shortcut, existing_amount, existing_value = income_currencies[current_key]
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{ float(refundreturnoutmoneyportion.amount_paid) + float(existing_amount)}'
            value = f'{ float(refundreturnoutmoneyportion.rated_value) + float(existing_value)}'
            income_currencies[current_key] = [shortcut, amount_paid, value]




    expenses_currencies = {} #{id:['shortcut','amount','value']}
    


    for invoicemoneyportion in invoicemoneyportions:
        current_key = invoicemoneyportion.payment_method.id
        payment_method = invoicemoneyportion.payment_method

        if current_key not in expenses_currencies:
            # Add new entry if key doesn't exist
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{invoicemoneyportion.amount_paid}'
            value = f'{invoicemoneyportion.rated_value}'
            expenses_currencies[current_key] = [shortcut, amount_paid, value]
        else:
            # Alter existing entry if key exists
            existing_shortcut, existing_amount, existing_value = expenses_currencies[current_key]
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{ float(invoicemoneyportion.amount_paid) + float(existing_amount)}'
            value = f'{ float(invoicemoneyportion.rated_value) + float(existing_value)}'
            expenses_currencies[current_key] = [shortcut, amount_paid, value]


    for expensemoneyportion in expensemoneyportions:
        current_key = expensemoneyportion.payment_method.id
        payment_method = expensemoneyportion.payment_method

        if current_key not in expenses_currencies:
            # Add new entry if key doesn't exist
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{expensemoneyportion.amount_paid}'
            value = f'{expensemoneyportion.rated_value}'
            expenses_currencies[current_key] = [shortcut, amount_paid, value]
        else:
            # Alter existing entry if key exists
            existing_shortcut, existing_amount, existing_value = expenses_currencies[current_key]
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{ float(expensemoneyportion.amount_paid) + float(existing_amount)}'
            value = f'{ float(expensemoneyportion.rated_value) + float(existing_value)}'
            expenses_currencies[current_key] = [shortcut, amount_paid, value]


    
    for refundreturninnmoneyportion in refundreturninnmoneyportions:
        current_key = refundreturninnmoneyportion.payment_method.id
        payment_method = refundreturninnmoneyportion.payment_method

        if current_key not in expenses_currencies:
            # Add new entry if key doesn't exist
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{refundreturninnmoneyportion.amount_paid}'
            value = f'{refundreturninnmoneyportion.rated_value}'
            expenses_currencies[current_key] = [shortcut, amount_paid, value]
        else:
            # Alter existing entry if key exists
            existing_shortcut, existing_amount, existing_value = expenses_currencies[current_key]
            shortcut = f'{payment_method.shortcut}'
            amount_paid = f'{ float(refundreturninnmoneyportion.amount_paid) + float(existing_amount)}'
            value = f'{ float(refundreturninnmoneyportion.rated_value) + float(existing_value)}'
            expenses_currencies[current_key] = [shortcut, amount_paid, value]


    # print("EXPENSES")
    # print(expenses_currencies)

    return income_currencies, expenses_currencies


def calculate_net(income, expenses):
    unique_keys = list(set(income.keys()).union(set(expenses.keys())))
    income_currencies = {}
    expenses_currencies = {}
    totals_dict = {}

    # print(unique_keys)
    for key in unique_keys:
        # print(key)
        currency_shortcut = "None"
        try:
            currency_shortcut = income[key][0]
            income_currency_amount_paid_ = round(float(income[key][1]), 2)
            income_currency_rated_value_ = round(float(income[key][2]), 2)
            income_currencies[key] = [income[key][0], income[key][1], income[key][2]]
        except:
            income_currency_amount_paid_ = 0
            income_currency_rated_value_ = 0
            income_currencies[key] = [currency_shortcut, 0, 0]


        try:
            currency_shortcut = expenses[key][0]
            expenses_currency_amount_paid_ = round(float(expenses[key][1]), 2)
            expenses_currency_rated_value_ = round(float(expenses[key][2]), 2)
            expenses_currencies[key] = [expenses[key][0], expenses[key][1], expenses[key][2]]

        except:
            expenses_currency_amount_paid_ = 0
            expenses_currency_rated_value_ = 0
            expenses_currencies[key] = [currency_shortcut, 0, 0]


        balanced_amount_paid = round(float(income_currency_amount_paid_) - float(expenses_currency_amount_paid_), 2)
        balanced_rated_value = round(float(income_currency_rated_value_) - float(expenses_currency_rated_value_), 2)
        totals_dict[key] = [currency_shortcut, balanced_amount_paid, balanced_rated_value]

    return income_currencies, expenses_currencies, totals_dict