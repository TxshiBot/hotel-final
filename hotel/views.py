from django.shortcuts import render, redirect
from django.db import connection

def Dashboard(request):
    return render(request, 'dashboard.html')

