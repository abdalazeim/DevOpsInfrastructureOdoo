from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            next_url = request.POST.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("dashboard:index")
        error = "The username or password is incorrect."
    return render(request, "pages/login.html", {"error": error, "next": request.GET.get("next", "")})


@require_POST
def logout_page(request):
    logout(request)
    return redirect("login")


def index(request):
    return redirect("dashboard:index")


def example_page(request):
    """Demonstrates the modular template architecture (layouts/components/partials)."""
    context = {
        "page_title": "Example Page",
        "page_subtitle": "Reusable template layout example",
        "breadcrumbs": [
            {"label": "Home", "url": "/"},
            {"label": "Example Page"},
        ],
        "nav_sections": [
            {
                "title": "Overview",
                "items": [
                    {
                        "label": "Dashboard",
                        "icon": "fa-th-large",
                        "id": "nav-example-dashboard",
                        "onclick": "alert('Dashboard')",
                        "active": True,
                    },
                    {
                        "label": "Modules",
                        "icon": "fa-cubes",
                        "id": "nav-example-modules",
                        "onclick": "alert('Modules')",
                    },
                ],
            },
            {
                "title": "Settings",
                "items": [
                    {
                        "label": "General Settings",
                        "icon": "fa-cog",
                        "id": "nav-example-settings",
                        "onclick": "alert('Settings')",
                    },
                ],
            },
        ],
        "profile_menu": [
            {"label": "Profile", "icon": "fa-user", "onclick": "alert('Profile')"},
        ],
    }
    return render(request, "pages/example_page.html", context)
