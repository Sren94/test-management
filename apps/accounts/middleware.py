from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """While `must_change_password` is True, the user can only change the password or log out."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.must_change_password:
            change_url = reverse("accounts:password_change")
            allowed = (change_url, reverse("accounts:logout"), settings.STATIC_URL)
            if not request.path.startswith(allowed):
                return redirect(change_url)
        return self.get_response(request)