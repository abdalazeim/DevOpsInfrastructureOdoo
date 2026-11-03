"""Transport module API views (CRUD + business operations).

These views follow the Master Template conventions:
- Unified response envelope (``api_response`` / ``api_error``).
- Permission decorators from core.
- Pagination via ``paginate_queryset``.
- Service layer for business logic; views stay thin.
"""

from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.exceptions import AppError, exception_to_response
from apps.core.utils.http import (
    api_error,
    api_response,
    api_response_paginated,
    parse_json_body,
    paginate_queryset,
)

from ..repositories import TransportRepository
from ..serializers import (
    serialize_customer,
    serialize_customer_list,
    serialize_vehicle,
    serialize_vehicle_list,
    serialize_driver,
    serialize_driver_list,
    serialize_route,
    serialize_route_list,
    serialize_good,
    serialize_good_list,
    serialize_shipment,
    serialize_shipment_list,
    serialize_trip,
    serialize_trip_list,
    serialize_payment,
    serialize_payment_list,
    serialize_expense,
    serialize_expense_list,
    serialize_transport_meta,
    serialize_transport_dashboard,
    serialize_transport_reports,
    serialize_transport_reports_top,
)
from ..services import ShipmentService, TripService

repository = TransportRepository()
shipment_service = ShipmentService()
trip_service = TripService()


# ──────────────────────────────────────────────────────────────────────
# Meta / reference data (for Flutter dropdowns)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def transport_meta(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    return api_response(serialize_transport_meta(), message="بيانات المرجعية")


# ──────────────────────────────────────────────────────────────────────
# Customers (list only)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_customers(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    customers = repository.list_customers(search=search)
    return api_response(
        serialize_customer_list(customers), message="تم تحميل قائمة العملاء"
    )


# ──────────────────────────────────────────────────────────────────────
# Vehicles (list only)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_vehicles(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    vehicles = repository.list_vehicles(search=search)
    return api_response(
        serialize_vehicle_list(vehicles), message="تم تحميل قائمة المركبات"
    )


# ──────────────────────────────────────────────────────────────────────
# Drivers (list only)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_drivers(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    drivers = repository.list_drivers(search=search)
    return api_response(
        serialize_driver_list(drivers), message="تم تحميل قائمة السائقين"
    )


# ──────────────────────────────────────────────────────────────────────
# Routes (list only)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_routes(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    routes = repository.list_routes(search=search)
    return api_response(
        serialize_route_list(routes), message="تم تحميل قائمة المسارات"
    )


# ──────────────────────────────────────────────────────────────────────
# Payments (list only)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_payments(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    payments = repository.list_payments(search=search)
    page_obj, meta = paginate_queryset(payments, request)
    return api_response_paginated(
        serialize_payment_list(list(page_obj)), meta, message="تم تحميل قائمة المدفوعات"
    )


# ──────────────────────────────────────────────────────────────────────
# Expenses (list only)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_expenses(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    expenses = repository.list_expenses(search=search)
    page_obj, meta = paginate_queryset(expenses, request)
    return api_response_paginated(
        serialize_expense_list(list(page_obj)), meta, message="تم تحميل قائمة المصروفات"
    )


# ──────────────────────────────────────────────────────────────────────
# Goods (full CRUD)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_goods(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    goods = repository.list_goods(search=search)
    page_obj, meta = paginate_queryset(goods, request)
    return api_response_paginated(
        serialize_good_list(list(page_obj)), meta, message="تم تحميل قائمة البضائع"
    )


@api_login_required
@api_permission_required("transport_manage")
def create_good(request):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        good = repository.create_good(user=request.user, data=data)
        return api_response(
            serialize_good(good), message="تم إضافة البضاعة بنجاح", status=201
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_view")
def get_good(request, good_id):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    try:
        good = repository.get_good_by_id(good_id)
        if not good:
            return api_error("البضاعة غير موجودة", status=404)
        return api_response(serialize_good(good))
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def update_good(request, good_id):
    if request.method not in ("PUT", "PATCH"):
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        good = repository.get_good_by_id(good_id)
        if not good:
            return api_error("البضاعة غير موجودة", status=404)
        good = repository.update_good(good, data=data)
        return api_response(serialize_good(good), message="تم تحديث البضاعة بنجاح")
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def delete_good(request, good_id):
    if request.method != "DELETE":
        return api_error("Method not allowed", status=405)
    try:
        good = repository.get_good_by_id(good_id)
        if not good:
            return api_error("البضاعة غير موجودة", status=404)
        repository.delete_good(good)
        return api_response(message="تم حذف البضاعة بنجاح")
    except AppError as exc:
        return exception_to_response(exc)


# ──────────────────────────────────────────────────────────────────────
# Shipments (full CRUD + business operations)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_shipments(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    status = request.GET.get("status")
    drafts = request.GET.get("drafts", "false").lower() == "true"
    shipments = repository.list_shipments(
        search=search, status=status, drafts=drafts
    )
    page_obj, meta = paginate_queryset(shipments, request)
    return api_response_paginated(
        serialize_shipment_list(list(page_obj)),
        meta,
        message="تم تحميل قائمة الشحنات",
    )


@api_login_required
@api_permission_required("transport_manage")
def create_shipment(request):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        shipment = shipment_service.create(request, user=request.user, data=data)
        return api_response(
            serialize_shipment(shipment),
            message="تم إنشاء الشحنة بنجاح",
            status=201,
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_view")
def get_shipment(request, shipment_id):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    try:
        shipment = repository.get_shipment_by_id(shipment_id)
        if not shipment:
            return api_error("الشحنة غير موجودة", status=404)
        return api_response(serialize_shipment(shipment))
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def update_shipment(request, shipment_id):
    if request.method not in ("PUT", "PATCH"):
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        shipment = shipment_service.update(
            shipment_id, request, user=request.user, data=data
        )
        return api_response(
            serialize_shipment(shipment), message="تم تحديث الشحنة بنجاح"
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def delete_shipment(request, shipment_id):
    if request.method != "DELETE":
        return api_error("Method not allowed", status=405)
    try:
        shipment_service.delete(shipment_id, request, user=request.user)
        return api_response(message="تم حذف الشحنة بنجاح")
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def advance_shipment(request, shipment_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    try:
        shipment = shipment_service.advance(shipment_id, request, user=request.user)
        return api_response(
            serialize_shipment(shipment), message="تم تحديث حالة الشحنة"
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def shipment_exception(request, shipment_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        shipment = shipment_service.exception(
            shipment_id, request, user=request.user, data=data
        )
        return api_response(
            serialize_shipment(shipment), message="تم تسجيل استثناء الشحنة"
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def shipment_pod(request, shipment_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        shipment = shipment_service.pod(
            shipment_id, request, user=request.user, data=data
        )
        return api_response(
            serialize_shipment(shipment), message="تم حفظ إثبات التسليم"
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def shipment_unload(request, shipment_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    try:
        shipment = shipment_service.unload(shipment_id, request, user=request.user)
        return api_response(
            serialize_shipment(shipment), message="تم تفريغ الشحنة"
        )
    except AppError as exc:
        return exception_to_response(exc)


# ──────────────────────────────────────────────────────────────────────
# Drafts
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_manage")
def save_draft(request):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        draft = shipment_service.save_draft(request, user=request.user, data=data)
        return api_response(
            serialize_shipment(draft),
            message="تم حفظ المسودة بنجاح",
            status=201,
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def submit_draft(request, draft_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    try:
        draft = shipment_service.submit_draft(draft_id, request, user=request.user)
        return api_response(
            serialize_shipment(draft), message="تم إرسال المسودة بنجاح"
        )
    except AppError as exc:
        return exception_to_response(exc)


# ──────────────────────────────────────────────────────────────────────
# Trips (full CRUD + business operations)
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def list_trips(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    search = (request.GET.get("q") or "").strip()
    status = request.GET.get("status")
    trips = repository.list_trips(search=search, status=status)
    page_obj, meta = paginate_queryset(trips, request)
    return api_response_paginated(
        serialize_trip_list(list(page_obj)), meta, message="تم تحميل قائمة الرحلات"
    )


@api_login_required
@api_permission_required("transport_manage")
def create_trip(request):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        trip = trip_service.create(request, user=request.user, data=data)
        return api_response(
            serialize_trip(trip), message="تم إنشاء الرحلة بنجاح", status=201
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_view")
def get_trip(request, trip_id):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    try:
        trip = repository.get_trip_by_id(trip_id)
        if not trip:
            return api_error("الرحلة غير موجودة", status=404)
        return api_response(serialize_trip(trip))
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def update_trip(request, trip_id):
    if request.method not in ("PUT", "PATCH"):
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        trip = trip_service.update(trip_id, request, user=request.user, data=data)
        return api_response(serialize_trip(trip), message="تم تحديث الرحلة بنجاح")
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def delete_trip(request, trip_id):
    if request.method != "DELETE":
        return api_error("Method not allowed", status=405)
    try:
        trip_service.delete(trip_id, request, user=request.user)
        return api_response(message="تم حذف الرحلة بنجاح")
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def advance_trip(request, trip_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    try:
        trip = trip_service.advance(trip_id, request, user=request.user)
        return api_response(
            serialize_trip(trip), message="تم تحديث حالة الرحلة"
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def close_trip(request, trip_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    try:
        trip = trip_service.close(trip_id, request, user=request.user)
        return api_response(
            serialize_trip(trip), message="تم إغلاق الرحلة"
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def reopen_trip(request, trip_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    try:
        trip = trip_service.reopen(trip_id, request, user=request.user)
        return api_response(
            serialize_trip(trip), message="تم إعادة فتح الرحلة"
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def link_shipments_to_trip(request, trip_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        trip = trip_service.link_shipments(
            trip_id, request, user=request.user, data=data
        )
        return api_response(
            serialize_trip(trip), message="تم ربط الشحنات بالرحلة"
        )
    except AppError as exc:
        return exception_to_response(exc)


@api_login_required
@api_permission_required("transport_manage")
def load_trip(request, trip_id):
    if request.method != "POST":
        return api_error("Method not allowed", status=405)
    data, err = parse_json_body(request)
    if err:
        return err
    try:
        trip = trip_service.load(trip_id, request, user=request.user, data=data)
        return api_response(
            serialize_trip(trip), message="تم تحميل الشحنات على الرحلة"
        )
    except AppError as exc:
        return exception_to_response(exc)


# ──────────────────────────────────────────────────────────────────────
# Dashboard / reports
# ──────────────────────────────────────────────────────────────────────

@api_login_required
@api_permission_required("transport_view")
def transport_dashboard(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    stats = repository.dashboard_stats()
    return api_response(
        serialize_transport_dashboard(stats), message="إحصائيات وحدة النقل"
    )


@api_login_required
@api_permission_required("transport_view")
def transport_reports(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    report_data = repository.transport_reports()
    return api_response(
        serialize_transport_reports(report_data), message="تقارير النقل"
    )


@api_login_required
@api_permission_required("transport_view")
def transport_reports_top(request):
    if request.method != "GET":
        return api_error("Method not allowed", status=405)
    top_data = repository.transport_reports_top()
    return api_response(
        serialize_transport_reports_top(top_data), message="أعلى التقارير"
    )
