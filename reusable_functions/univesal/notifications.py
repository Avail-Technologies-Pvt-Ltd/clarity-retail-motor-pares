from enventory.models import Stock, Notification, Batch

from datetime import datetime as datetime_

from django.http import JsonResponse

import locale
locale.setlocale(locale.LC_ALL, '') 




def batch_expiration_notification(request):
    batches = Batch.objects.filter(total_units__gte=1)
    last_notification = Notification.objects.filter(notification_type="expiring").order_by('created_at').last()
    today = str(datetime_.today().date())[:10]
    if last_notification != None:
        if str(last_notification.created_at)[:10] == today:
            pass #the check has been run for today
        else:
            for batch in batches:
                print('..............................................')
                print(int(str(batch.expiration_days_left)[:-14]))
                expiration_days_left = int(str(batch.expiration_days_left)[:-14])
                if expiration_days_left > 0:
                    new_notification = Notification()
                    new_notification.header = f"{ batch.stock.product.title } expiring!"
                    new_notification.notification_type = "expiring"
                    new_notification.detail = f"""Please note that your ({ batch.stock.product.product_code.upper() }) { batch.stock.product.title } { batch.stock.product.details } is expiring. \nNumber of units at risk: { locale.format_string('%.0f', batch.total_units, grouping=True)}. \nNumber of days left { str(batch.expiration_days_left)[:-9] }."""
                    new_notification.save()
                elif expiration_days_left == 0:
                    new_notification = Notification()
                    new_notification.header = f"{ batch.stock.product.title } expired!"
                    new_notification.notification_type = "expired"
                    new_notification.detail = f"""Please note that your ({ batch.stock.product.product_code.upper() }) { batch.stock.product.title } { batch.stock.product.details } has expired. \nNumber of units at risk: { locale.format_string('%.0f', batch.total_units, grouping=True)}. \nNumber of days left { str(batch.expiration_days_left)[:-9] }."""
                    new_notification.save()

    return JsonResponse({})



def stock_quantity_notification(stock_id):
    stock = Stock.objects.get(id=int(stock_id))
    available_units = stock.total_units
    reorder_quantity = stock.reorder_quantity
    if available_units <= reorder_quantity:
        new_notification = Notification()
        new_notification.header = f"({ stock.product.product_code.upper() }) { stock.product.title } stock is running out!"
        new_notification.notification_type = "reorder"
        new_notification.detail = f"Your ({ stock.product.product_code.upper() }) { stock.product.title } { stock.product.details } is running out. Total units left: { locale.format_string('%.0f', available_units, grouping=True) }."
        new_notification.save()

    return 0


def delete_notifications_by_type(notification_type):
    reorder_notifications = Notification.objects.filter(notification_type=notification_type)
    custome_status = ""
    message = "Already empty!"
    try:
        for notification in reorder_notifications:
            notification.delete()
            custome_status = ""
            message = "All reorder notifications have been deleted succesefully "
    except Exception as e:
        message = f"{ e }"
        custome_status = "Error"

    return custome_status, message