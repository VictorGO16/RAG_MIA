from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

# from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect
from profiles.models import CustomUser, Company, Profile


# Create your views here.
def home(request, *args, **kwargs):
    return render(request, "index.html", {})


def login_view(request, *args, **kwargs):
    if request.method == "POST":
        mail = request.POST.get("mail")
        password = request.POST.get("password")
        user = authenticate(request, username=mail, password=password)
        if user is not None:
            login(request, user)
            return redirect("user-profile")
        else:
            messages.warning(request, "Las credenciales ingresadas no son válidas.")
            return redirect("login")
    user = request.user
    if user.is_authenticated:
        return redirect("user-profile")
    return render(request, "authentication/login.html", {})


def register_view(request, *args, **kwargs):
    if request.method == "POST":
        mail = request.POST.get("mail")
        password = request.POST.get("password")
        company_id = request.POST.get("company")
        user = authenticate(request, username=mail, password=password)
        if user is not None:
            messages.warning(
                request, "El correo ingresado ya ha sido registrado previamente."
            )
            return redirect("register")
        else:
            user = CustomUser.objects.create_user(mail, mail, password)
            company = Company.objects.get(id=company_id)
            profile = Profile(user=user, company=company)
            profile.save()
            return redirect("login")
    companies = Company.objects.all()
    return render(request, "authentication/register.html", {"companies": companies})


def user_profile(request, *args, **kwargs):
    user = request.user
    if not user.is_authenticated:
        messages.warning(
            request,
            "Para acceder a su perfil, primero debe estar autenticado en la plataforma. Por favor ingrese sus credenciales.",
        )
        return redirect("login")
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        about = request.POST.get("about")
        experience = request.POST.get("experience")
        education = request.POST.get("education")
        hobbies = request.POST.get("hobbies")
        languages = request.POST.get("languages")
        linkedin = request.POST.get("linkedin")
        profile = Profile.objects.get(user=user)
        profile.name = name
        profile.phone = phone
        profile.address = address
        profile.about = about
        profile.experience = experience
        profile.education = education
        profile.hobbies = hobbies
        profile.languages = languages
        profile.linkedin = linkedin
        profile.save()
        messages.success(request, "Su perfil ha sido actualizado exitosamente.")
        return redirect("user-profile")
    profile = Profile.objects.filter(user=user).get()
    return render(
        request,
        "user_profile.html",
        {
            "name": profile.name,
            "phone": profile.phone,
            "address": profile.address,
            "about": profile.about,
            "experience": profile.experience,
            "education": profile.education,
            "hobbies": profile.hobbies,
            "languages": profile.languages,
            "linkedin": profile.linkedin,
        }
    )
