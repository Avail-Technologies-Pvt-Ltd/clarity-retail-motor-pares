from django.http import JsonResponse
from django.shortcuts import HttpResponseRedirect






#--------------------------------------------------------------------
#DECORATORS
#--------------------------------------------------------------------


def role_validator(allowed_roles):
    def decorator(fn):
        def wrapper(request, *args, **kwargs):
            print(f"'''''''''''''''''''''''''''''''''{request}")
            user = request.user
            roles = user.roles

            is_allowed = False
            for allowed_role in allowed_roles:
                if allowed_role in roles:
                    is_allowed = True

            if is_allowed == False:
                # message.warning(request, "Faild! You are not authorised to perform this action.")
                # print(f">>>>>>>>>>>>>>> {request.META['HTTP_REFERER']}")
                # return redirect(request.META['HTTP_REFERER'])
                return JsonResponse({'custome_status': "Error", 'error_type': "Authorisation", 'message': "You don't have permission to perform this action. Please contact your administrator for assistance."})
            else:
                return fn(request, *args, **kwargs)
        return wrapper
    return decorator

#--------------------------------------------------------------------
#/DECORATORS
#--------------------------------------------------------------------