import json
import logging
import socket

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import Printer
from .print_client import (
    test_printer,
    print_text,
    print_document,
)


logger = logging.getLogger(__name__)


# ============================================================
# HELPER
# ============================================================

def json_body(request):
    """
    Safely decode JSON request body.
    """

    try:
        return json.loads(
            request.body.decode("utf-8")
        )

    except (json.JSONDecodeError, UnicodeDecodeError):

        return None


# ============================================================
# LIST
# ============================================================

@require_GET
def printer_list(request):

    printers = Printer.objects.all()

    return JsonResponse({

        "status": "success",

        "printers": [

            {
                "id": printer.id,
                "name": printer.name,
                "display_name": printer.display_name,
                "server_ip": printer.server_ip,
                "server_port": printer.server_port,
                "enabled": printer.enabled,
                "is_default": printer.is_default,
            }

            for printer in printers

        ],
    })


# ============================================================
# ADD
# ============================================================

@require_POST
def printer_add(request):

    data = json_body(request)

    if data is None:

        return JsonResponse({

            "status": "error",
            "message": "Invalid JSON.",

        }, status=400)

    name = str(
        data.get(
            "name",
            "",
        )
    ).strip()

    display_name = str(
        data.get(
            "display_name",
            "",
        )
    ).strip()

    server_ip = str(
        data.get(
            "server_ip",
            "",
        )
    ).strip()

    server_port = data.get(
        "server_port",
        9101,
    )

    enabled = bool(
        data.get(
            "enabled",
            True,
        )
    )

    is_default = bool(
        data.get(
            "is_default",
            False,
        )
    )

    if not name:

        return JsonResponse({

            "status": "error",
            "message": "Printer name is required.",

        }, status=400)

    if not server_ip:

        return JsonResponse({

            "status": "error",
            "message": "Server IP address is required.",

        }, status=400)

    try:

        server_port = int(
            server_port
        )

    except (TypeError, ValueError):

        return JsonResponse({

            "status": "error",
            "message": "Server port must be a number.",

        }, status=400)

    if not 1 <= server_port <= 65535:

        return JsonResponse({

            "status": "error",
            "message": "Invalid server port.",

        }, status=400)

    if Printer.objects.filter(
        name=name
    ).exists():

        return JsonResponse({

            "status": "error",

            "message": (
                f"Printer '{name}' already exists."
            ),

        }, status=400)

    # --------------------------------------------------------
    # If this is being made default, remove default from others
    # --------------------------------------------------------

    if is_default:

        Printer.objects.update(
            is_default=False
        )

    printer = Printer.objects.create(

        name=name,

        display_name=display_name,

        server_ip=server_ip,

        server_port=server_port,

        enabled=enabled,

        is_default=is_default,
    )

    return JsonResponse({

        "status": "success",

        "message": "Printer added successfully.",

        "printer": {

            "id": printer.id,

            "name": printer.name,

            "display_name": printer.display_name,

            "server_ip": printer.server_ip,

            "server_port": printer.server_port,

            "enabled": printer.enabled,

            "is_default": printer.is_default,

        },
    })


# ============================================================
# UPDATE
# ============================================================

@require_POST
def printer_update(
    request,
    printer_id,
):

    printer = get_object_or_404(
        Printer,
        id=printer_id,
    )

    data = json_body(request)

    if data is None:

        return JsonResponse({

            "status": "error",
            "message": "Invalid JSON.",

        }, status=400)

    name = str(
        data.get(
            "name",
            printer.name,
        )
    ).strip()

    display_name = str(
        data.get(
            "display_name",
            printer.display_name,
        )
    ).strip()

    server_ip = str(
        data.get(
            "server_ip",
            printer.server_ip,
        )
    ).strip()

    server_port = data.get(
        "server_port",
        printer.server_port,
    )

    enabled = bool(
        data.get(
            "enabled",
            printer.enabled,
        )
    )

    is_default = bool(
        data.get(
            "is_default",
            printer.is_default,
        )
    )

    if not name:

        return JsonResponse({

            "status": "error",
            "message": "Printer name is required.",

        }, status=400)

    if not server_ip:

        return JsonResponse({

            "status": "error",
            "message": "Server IP address is required.",

        }, status=400)

    if Printer.objects.exclude(
        id=printer.id
    ).filter(
        name=name
    ).exists():

        return JsonResponse({

            "status": "error",

            "message": (
                "Another printer already uses that name."
            ),

        }, status=400)

    try:

        server_port = int(
            server_port
        )

    except (TypeError, ValueError):

        return JsonResponse({

            "status": "error",
            "message": "Server port must be a number.",

        }, status=400)

    if not 1 <= server_port <= 65535:

        return JsonResponse({

            "status": "error",
            "message": "Invalid server port.",

        }, status=400)

    # --------------------------------------------------------
    # If this printer becomes default, remove default from
    # all other printers.
    # --------------------------------------------------------

    if is_default:

        Printer.objects.exclude(
            id=printer.id
        ).update(
            is_default=False
        )

    printer.name = name
    printer.display_name = display_name
    printer.server_ip = server_ip
    printer.server_port = server_port
    printer.enabled = enabled
    printer.is_default = is_default

    printer.save()

    return JsonResponse({

        "status": "success",

        "message": "Printer updated successfully.",

    })


# ============================================================
# DELETE
# ============================================================

@require_POST
def printer_delete(
    request,
    printer_id,
):

    printer = get_object_or_404(
        Printer,
        id=printer_id,
    )

    name = printer.name

    printer.delete()

    return JsonResponse({

        "status": "success",

        "message": (
            f"Printer '{name}' deleted."
        ),

    })


# ============================================================
# TEST PRINT
# ============================================================

@require_POST
def printer_test(
    request,
    printer_id,
):

    printer = get_object_or_404(
        Printer,
        id=printer_id,
    )

    if not printer.enabled:

        return JsonResponse({

            "status": "error",
            "message": "Printer is disabled.",

        }, status=400)

    data = json_body(request)

    if data is None:

        return JsonResponse({

            "status": "error",
            "message": "Invalid JSON.",

        }, status=400)

    logo_data = data.get(
        "logo_data"
    )

    print(logo_data)

    logger.info(
        "Testing printer '%s' via %s:%s",
        printer.name,
        printer.server_ip,
        printer.server_port,
    )

    result = test_printer(
        printer,
        logo_data=logo_data,
    )

    if result.get(
        "status"
    ) == "success":

        return JsonResponse({

            "status": "success",

            "message": result.get(
                "message",
                "Test print sent successfully.",
            ),

            "printer": printer.name,

        })

    return JsonResponse({

        "status": "error",

        "message": result.get(
            "message",
            "Test print failed.",
        ),

    }, status=502)


# ============================================================
# TEXT PRINT
# ============================================================

@require_POST
def printer_print_text(
    request,
    printer_id,
):

    printer = get_object_or_404(
        Printer,
        id=printer_id,
    )

    if not printer.enabled:

        return JsonResponse({

            "status": "error",
            "message": "Printer is disabled.",

        }, status=400)

    data = json_body(request)

    if data is None:

        return JsonResponse({

            "status": "error",
            "message": "Invalid JSON.",

        }, status=400)

    text = str(
        data.get(
            "text",
            "",
        )
    )

    if not text.strip():

        return JsonResponse({

            "status": "error",
            "message": "Text is required.",

        }, status=400)

    result = print_text(
        printer,
        text,
    )

    if result.get(
        "status"
    ) == "success":

        return JsonResponse(
            result
        )

    return JsonResponse(
        result,
        status=502,
    )


# ============================================================
# DOCUMENT PRINT
# ============================================================

@require_POST
def printer_print_document(
    request,
    printer_id,
):
    """
    Print a generic dynamic document.

    The Django application describes WHAT should be printed.
    The Windows Print Server decides HOW to render it.
    """

    printer = get_object_or_404(
        Printer,
        id=printer_id,
    )

    if not printer.enabled:

        return JsonResponse({

            "status": "error",
            "message": "Printer is disabled.",

        }, status=400)

    data = json_body(request)

    if data is None:

        return JsonResponse({

            "status": "error",
            "message": "Invalid JSON.",

        }, status=400)

    # --------------------------------------------------------
    # Accept either:
    #
    # {
    #     "document": {...}
    # }
    #
    # or the document directly.
    # --------------------------------------------------------

    document = data.get(
        "document",
        data,
    )

    if not isinstance(
        document,
        dict,
    ):

        return JsonResponse({

            "status": "error",
            "message": "Document must be an object.",

        }, status=400)

    if document.get(
        "type"
    ) != "document":

        return JsonResponse({

            "status": "error",

            "message": (
                "Invalid document type. "
                "Expected 'document'."
            ),

        }, status=400)

    content = document.get(
        "content"
    )

    if not isinstance(
        content,
        list,
    ):

        return JsonResponse({

            "status": "error",
            "message": "Document content must be a list.",

        }, status=400)

    if not content:

        return JsonResponse({

            "status": "error",
            "message": "Document contains no printable content.",

        }, status=400)

    # --------------------------------------------------------
    # Always use the printer selected by Django.
    #
    # This prevents a client from secretly changing the
    # configured printer by modifying printer_name.
    # --------------------------------------------------------

    document = dict(
        document
    )

    document["printer_name"] = printer.name

    logger.info(
        "Printing document on '%s' via %s:%s",
        printer.name,
        printer.server_ip,
        printer.server_port,
    )

    result = print_document(
        printer,
        document,
    )

    if result.get(
        "status"
    ) == "success":

        return JsonResponse(
            result
        )

    return JsonResponse(
        result,
        status=502,
    )


# ============================================================
# DEFAULT
# ============================================================

@require_POST
def printer_set_default(
    request,
    printer_id,
):

    printer = get_object_or_404(
        Printer,
        id=printer_id,
    )

    Printer.objects.exclude(
        id=printer.id
    ).update(
        is_default=False
    )

    printer.is_default = True

    printer.save()

    return JsonResponse({

        "status": "success",

        "message": (
            f"'{printer.name}' is now "
            "the default printer."
        ),

    })


# ============================================================
# HEALTH CHECK
# ============================================================

@require_GET
def printer_health(
    request,
    printer_id,
):

    printer = get_object_or_404(
        Printer,
        id=printer_id,
    )

    try:

        with socket.create_connection(

            (
                printer.server_ip,
                printer.server_port,
            ),

            timeout=3,

        ):

            return JsonResponse({

                "status": "success",

                "online": True,

                "message": (
                    "Print server is reachable."
                ),

            })

    except Exception as e:

        return JsonResponse({

            "status": "error",

            "online": False,

            "message": str(e),

        })