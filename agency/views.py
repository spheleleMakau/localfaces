from django.shortcuts import render
from camp.views import apply


def home(request):
    return render(request, "agency/home.html")


def join(request):
    return apply(request)


def _coming_soon(request, title):
    return render(request, "agency/coming_soon.html", {"title": title})


def models_gallery(request):
    return _coming_soon(request, "Models")


def entertainers_gallery(request):
    return _coming_soon(request, "Content Creators")


def production_gallery(request):
    return _coming_soon(request, "Production")


def founder_portfolio(request):
    return render(request, "agency/founder_portfolio.html")
