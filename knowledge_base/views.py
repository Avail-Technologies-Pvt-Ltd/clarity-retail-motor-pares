from django.shortcuts import render

import json
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from enventory.models import Stock, Batch
from .models import CarModel, Compatibility, CompatibilityType, CarTransmission, CarMake
from pos.models import CartItem

from django.db.models.functions import Concat
from django.db.models import Q, CharField, Value as V

import locale
locale.setlocale(locale.LC_ALL, '') 



def compatability_manipulation_page(request):
	return render(request, 'knowledge_base/compatability_manipulation_page.html')



def add_to_cart_from_look_up(request):
	stock_ids_and_quantities = json.loads(request.POST.get('stock_ids_and_quantities', '[]'))
	for item in stock_ids_and_quantities:
		if int(item['quantity']) > 0: #quantity is at leats 1, add to cart

			print('RRRRRRRRRRRR')
			try:
				stock_id = int(item['id'])
				quantity = int(item['quantity'])
			except Exception as e:
				message = e
				print(f"Error {e}")
				continue

			stock = Stock.objects.get(id=stock_id)


			# creating a cart item
			#   check if the same stock exist
			stock_cart_item_already_exist = CartItem.objects.filter(stock=stock, user=request.user)
			if stock_cart_item_already_exist:
				old_item = stock_cart_item_already_exist[0]
				current_cart_item = old_item

				current_cart_item.unit_price = float(current_cart_item.unit_price) + float(stock.selling_price)
				current_cart_item.VAT = float(current_cart_item.VAT) + float(stock.selling_price * stock.product.vat_code.percentage/100) * quantity
				current_cart_item.quantity = float(current_cart_item.quantity) + float(quantity)

			else:
				new_cart_item = CartItem()
				new_cart_item.stock = stock
				new_cart_item.unit_price = stock.selling_price
				new_cart_item.VAT = (stock.selling_price * stock.product.vat_code.percentage/100) * quantity
				new_cart_item.quantity = quantity
				new_cart_item.buying_unit_price = stock.avarage_unit_cost
				new_cart_item.user = request.user
				new_cart_item.used_baches_data = ""
				new_cart_item.used_baches_quantities_data = ""
				# new_cart_item.save()

				current_cart_item = new_cart_item

			
			batch_ids = []

			#collecting all batch ids that can be used
			available_for_sale_batches = Batch.objects.filter(status=True, stock=stock, total_units__gte=0)
			for batch in available_for_sale_batches:
				batch_ids.append(batch.id)

			requared_quntity = quantity
			#check if there are enogh products
			total_units_available_for_sale = 0
			for batch in available_for_sale_batches:
				total_units_available_for_sale += batch.total_units

			if total_units_available_for_sale >= requared_quntity:
				print(f"available enough......................... {total_units_available_for_sale}")
				#altering batches quntities and deactivating empty ones
				actively_requred_quantity = requared_quntity
				still_needed = True
				for batch in available_for_sale_batches:
					if still_needed:
						pass
					else:
						break

					if batch.total_units - actively_requred_quantity >= 0:
						batch.total_units = batch.total_units - actively_requred_quantity
						batch.save()
						still_needed = False
						current_cart_item.used_baches_data += f"{batch.id},"
						current_cart_item.used_baches_quantities_data += f"{actively_requred_quantity},"
					else:
						actively_requred_quantity -= batch.total_units
						available_in_batch = batch.total_units
						batch.total_units = 0
						# batch.status = False
						batch.save()
						current_cart_item.used_baches_data += f"{batch.id},"
						current_cart_item.used_baches_quantities_data += f"{available_in_batch},"

				current_cart_item.save()


			else:
				pass

	message = "Added all selected products to cart"
	return JsonResponse({"success": True, "custome_status":"", "message":message})




def get_model_and_compatable_parts(request):
	model_id = request.GET.get('model_id')

	model = CarModel.objects.get(id=int(model_id))

	model_details = {
		'make': model.make.make, 
		'model':  model.model, 
		'year': model.year, 
		'transmission': model.car_transmission.title, 
		'engine_number': model.engine_number,
	}

	compatibilities = Compatibility.objects.filter(car_model=model).order_by('car_part__product__title')

	recommended_parts = []
	altenative_parts = []
	for compatibility in compatibilities:
		if compatibility.compatibility_type.compatibility_type == "RECOMMENDED":
			recommended_parts.append(
				{
					'id': compatibility.car_part.id,
					'product_code': compatibility.car_part.product.product_code,
					'title': compatibility.car_part.product.title,
					'details': compatibility.car_part.product.details,
					'selling_price': locale.format_string('%.2f', compatibility.car_part.selling_price, grouping=True),
					'total_units': locale.format_string('%.0f', compatibility.car_part.total_units, grouping=True),
				}
			)
		else:
			altenative_parts.append(
				{
					'id': compatibility.car_part.id,
					'product_code': compatibility.car_part.product.product_code,
					'title': compatibility.car_part.product.title,
					'details': compatibility.car_part.product.details,
					'selling_price': locale.format_string('%.2f', compatibility.car_part.selling_price, grouping=True),
					'total_units': locale.format_string('%.0f', compatibility.car_part.total_units, grouping=True),
				}
			)

	table_body = ""
	count = 0
	if recommended_parts:
		table_body += f"""
		<tr style="background: green;">
			<td colspan="5">Recommended Parts</td>
		</tr>"""

		for part in recommended_parts:
			count += 1
			table_body += f"""
		<tr>
			<td style="width: 5%; display: none">{ part['id'] }</td>
			<td style="width: 5%;">{ count }</td>
			<td style="width: 45%;">
				<b>{ part['product_code'] }<b><br>
				{ part['title'] }<br>
				<small>{ part['details'] }</small><br>
			</td>
			<td style="text-align: right;">{ part['selling_price']}</td>
			<td style="text-align: right;">{ part['total_units']}</td>
			<td>
				<input class="qty-input form-control" style="width:75px ;text-align: right;" type="number" value="0" min="0" max="{ part['total_units']}">
			</td>
		</tr>"""


	if altenative_parts:
		table_body += f"""
		<tr style="background: yellow;">
			<td colspan="5">Altenative Parts</td>
		</tr>"""

		for part in altenative_parts:
			count += 1
			table_body += f"""
		<tr>
			<td style="width: 5%; display: none">{ part['id'] }</td>
			<td style="width: 5%;">{ count }</td>
			<td style="width: 45%;">
				<b>{ part['product_code'] }<b><br>
				{ part['title'] }<br>
				<small>{ part['details'] }</small><br>
			</td>
			<td style="text-align: right;">{ part['selling_price']}</td>
			<td style="text-align: right;">{ part['total_units']}</td>
			<td>
				<input class="qty-input form-control" style="width:75px ;text-align: right;" type="number" value="0" min="0" max="{ part['total_units']}">
			</td>
		</tr>"""




	return JsonResponse({'details': model_details, 'table_body': table_body})




def get_part_and_compatable_models(request):
	part_id = request.GET.get('part_id')

	part = Stock.objects.get(id=int(part_id))

	part_details = {
		'title': part.product.title,
		'part_code': part.product.product_code,
		'selling_price': round(part.selling_price, 2),
		'details': part.product.details,
	}

	compatibilities = Compatibility.objects.filter(car_part=part)


	recommended_models = []
	altenative_models = []

	for compatibility in compatibilities:
		if compatibility.compatibility_type.compatibility_type == "RECOMMENDED":
			recommended_models.append(f"[{compatibility.car_model.engine_number}] {compatibility.car_model.make} {compatibility.car_model.model} {compatibility.car_model.car_transmission} ({compatibility.car_model.year})")
		else:
			altenative_models.append(f"[{compatibility.car_model.engine_number}] {compatibility.car_model.make} {compatibility.car_model.model} {compatibility.car_model.car_transmission} ({compatibility.car_model.year})")


	table = ""
	count = 0



	if recommended_models:
		table += """
		<tr style="background: green">
			<td colspan="2">Recommended on</td>
		</tr>
		"""
	for model in recommended_models:
		count += 1
		table += f"""
		<tr>
			<td>{ count }</td>
			<td>{ model }</td>
		</tr>
		"""

	if altenative_models:
		table += """
		<tr style="background: orange">
			<td colspan="2">Used as an alternative on</td>
		</tr>
		"""
	for model in altenative_models:
		count += 1
		table += f"""
		<tr>
			<td>{ count }</td>
			<td>{ model }</td>
		</tr>
		"""

	return JsonResponse({'part_details': part_details, 'table': table})




def ajax_navigate_part(request):
	current_part_id = int(request.POST.get('current_part_id'))
	direction = request.POST.get('direction')

	has_next = True
	has_previous = True

	if direction == 'next':
		next_part = Stock.objects.filter(id__gt=current_part_id).order_by('id').first()
		
		if next_part:

			success = "true"
			part = {
				"id": next_part.id,
				"name": next_part.product.title,
				"product_code": next_part.product.product_code,
				"title": next_part.product.title,
				"details": next_part.product.details,
			}
			message = "Part loaded successfully"
		else:
			success = "false"
			message = "No more parts available in this direction"


	elif direction == 'prev':
		previous_part = Stock.objects.filter(id__lt=current_part_id).order_by('-id').first()
		# has_next = Stock.objects.filter(id__lt=previous_part.id).order_by('-id').first()
		# has_previous = Stock.objects.filter(id__lt=previous_part.id).order_by('-id').last()

		# if has_next:
		# 	has_next = True
		# if has_previous:
		# 	has_previous = True

		if previous_part:
			success = "true"
			part = {
				"id": previous_part.id,
				"name": previous_part.product.title,
				"product_code": previous_part.product.product_code,
				"title": previous_part.product.title,
				"details": previous_part.product.details,
			}
			message = "Part loaded successfully"
		else:
			success = "false"
			message = "No more parts available in this direction"


	if success == "false":
		return JsonResponse({'success': success, 'message': message, 'has_next': has_next, 'has_previous': has_previous })

	else:
		return JsonResponse({'success': success, 'message': message, 'part': part, 'has_next': has_next, 'has_previous': has_previous })





def ajax_add_car_model(request):
	engine_number = request.POST.get('engine_number')
	make = request.POST.get('make')
	model_name = request.POST.get('name')
	year = request.POST.get('year')
	transmission_id = request.POST.get('transmission')

	# check if make already exist and create new if needed ----------------------------------------
	make_exists = CarModel.objects.filter(make__make=make)
	if make_exists:
		make_id = make_exists.first().id

	else:
		# create new make
		new_make = CarMake()
		new_make.make = make
		new_make.save()
		make_id = new_make.id

	car_make = CarMake.objects.get(id=int(make_id))
	car_transmission = CarTransmission.objects.get(id=int(transmission_id))

	# check if model already exist and create new if not   ----------------------------------------
	model_exists = CarModel.objects.filter(engine_number=engine_number, make=car_make, model__iexact=model_name, year=year, car_transmission__id=int(transmission_id))
	if model_exists:
		car_model = model_exists.first()
	else:
		# create new model
		new_model = CarModel()
		new_model.engine_number = engine_number
		new_model.make = car_make
		new_model.model = model_name
		new_model.year = year
		new_model.car_transmission = car_transmission
		new_model.save()
		car_model = new_model

	
	
	succsess = 'true'
	model = {
		'id': car_model.id,
		'name': car_model.model,
		'engine_number': engine_number,
	}


	return JsonResponse({"success": succsess, "model": model})

def ajax_get_transmission_options(request):
	car_transmission_types = CarTransmission.objects.all()
	transmission_options = []

	for transmission_type in car_transmission_types:
		transmission_options.append({
			'value': transmission_type.id,
			'label': f"{transmission_type.title} ({transmission_type.shortcut})",
			})


	return JsonResponse({'options': transmission_options})




def ajax_get_part_compatibility(request):
	part_id = request.GET.get('part_id')
	car_part = Stock.objects.get(id=int(part_id))

	compatibilities = Compatibility.objects.filter(car_part=car_part)


	recommended = []
	alternatives = []

	for compatibility in compatibilities:
		if compatibility.compatibility_type.compatibility_type == "RECOMMENDED":
			recommended.append({
				'id': compatibility.car_model.id,
				'name': f"[{compatibility.car_model.engine_number}] {compatibility.car_model.make} {compatibility.car_model.model} {compatibility.car_model.car_transmission} ({compatibility.car_model.year})",
			})
		elif compatibility.compatibility_type.compatibility_type == "ALTERNATIVE":
			alternatives.append({
				'id': compatibility.car_model.id,
				'name': f"[{compatibility.car_model.engine_number}] {compatibility.car_model.make} {compatibility.car_model.model} {compatibility.car_model.car_transmission} ({compatibility.car_model.year})",
			})


	return JsonResponse({'recommended': recommended, 'alternative': alternatives})


def ajax_get_part_details(request):
	part_id = request.GET.get('part_id')

	part = Stock.objects.get(id=int(part_id)).product

	title = part.title
	product_code = part.product_code
	details = part.details

	return JsonResponse({'title': title, 'product_code': product_code, 'details': details})



def ajax_save_compatibility(request):
	part_id = request.POST.get('part_id')
	recommended_model_ids = json.loads(request.POST.get('recommended_models', '[]'))
	alternative_model_ids = json.loads(request.POST.get('alternative_models', '[]'))

	part = Stock.objects.get(id=int(part_id))

	# clear all compatibilities linked to this part
	compatibilities_linked = Compatibility.objects.filter(car_part=part)
	for compatibility in compatibilities_linked:
		compatibility.delete()

	#create recommended compatibility
	for model_id in recommended_model_ids:
		compatibility_type = CompatibilityType.objects.filter(compatibility_type="RECOMMENDED")
		if compatibility_type:
			compatibility_type = compatibility_type.first()
		else:
			compatibility_type = CompatibilityType()
			compatibility_type.compatibility_type = "RECOMMENDED"
			compatibility_type.is_compatible = True
			compatibility_type.save()

		model = CarModel.objects.get(id=int(model_id))
		compatibility = Compatibility()
		compatibility.car_part = part
		compatibility.car_model = model
		compatibility.compatibility_type = compatibility_type
		compatibility.save()


	#create alternative compatibility
	for model_id in alternative_model_ids:
		compatibility_type = CompatibilityType.objects.filter(compatibility_type="ALTERNATIVE").first()
		if compatibility_type:
			pass
		else:
			compatibility_type = CompatibilityType()
			compatibility_type.compatibility_type = "ALTERNATIVE"
			compatibility_type.is_compatible = True
			compatibility_type.save()

		model = CarModel.objects.get(id=int(model_id))
		compatibility = Compatibility()
		compatibility.car_part = part
		compatibility.car_model = model
		compatibility.compatibility_type = compatibility_type
		compatibility.save()


	message = "Seved successfully!"
	success = "true"

	return JsonResponse({'message': message, 'success': success,})



def ajax_search_models_1(request):
	# search key
	search_text = request.GET.get('search_text')
	car_models = CarModel.objects.filter(Q(make__make__icontains=search_text) | Q(model__icontains=search_text) | Q(engine_number__icontains=search_text))[:10]

	
	car_model_options = [
		f"<option value='{ car_model.id }'> [{car_model.engine_number}] {car_model.make} {car_model.model} {car_model.car_transmission} ({car_model.year}) </option>" for car_model in car_models
	]

	title_option = [
		f"<option value='0' selected>Select Car Model</option>"
	]

	car_model_options = title_option + car_model_options

	return JsonResponse({'options':car_model_options})




def ajax_search_models(request):
	search_text = request.GET.get('search_text')

	# stock
	models = CarModel.objects.filter(Q(make__make__icontains=search_text) | Q(model__icontains=search_text))[:10]
	 
	model_options = []

	for model in models:
		name = f"[{model.engine_number}] {model.make} {model.model} {model.car_transmission} ({model.year})"
		model_options.append({'id': model.id, 'name': name})


	return JsonResponse({'results': model_options})




def ajax_get_parts(request):
	search_text = request.GET.get('search_text')
	print('--------------------------------------------->>>')
	# print(search_text)

	# const mockParts = [
	#	 { id: '1', name: 'Engine', description: 'Power source of the vehicle' },
	#	 { id: '2', name: 'Transmission', description: 'Transfers power to wheels' },
	#	 { id: '3', name: 'Brakes', description: 'Slows or stops the vehicle' },
	#	 { id: '4', name: 'Suspension', description: 'Provides smooth ride' },
	#	 { id: '5', name: 'Exhaust System', description: 'Directs exhaust gases' },
	#	 { id: '6', name: 'Electrical System', description: 'Powers accessories' }
	# ];


	# stock
	parts = Stock.objects.filter(Q(product__title__icontains=search_text) | Q(product__product_code__icontains=search_text) | Q(product__details__icontains=search_text, deleted=False, status=True))[:10]
	 
	part_options = []

	for part in parts:
		name = f'({ part.product.product_code }){ part.product.title }'
		part_options.append({'id': int(part.id), 'name': name, 'description': part.product.details})


	print(part_options)
	return JsonResponse({'results': part_options})
