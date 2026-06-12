# API
def days_from_now(request):
	days = request.GET.get('days')
	today = datetime_.today().date()
	new_date = today + relativedelta(days=int(days))
	return JsonResponse({'new_date': new_date})

# DIRECT PYTHON CALL
def days_from_now_python(days):
	today = datetime_.today().date()
	new_date = today + relativedelta(days=int(days))
	return new_date
