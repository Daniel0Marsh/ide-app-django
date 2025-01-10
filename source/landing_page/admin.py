from django.contrib import admin
from .models import Favicon, Logo, Background, HomePage, ImageOne


class FaviconInline(admin.StackedInline):
    model = Favicon


class ImageOneInline(admin.StackedInline):
    model = ImageOne


class LogoImageInline(admin.StackedInline):
    model = Logo


class BackgroundVideoInline(admin.StackedInline):
    model = Background


class HomePageAdmin(admin.ModelAdmin):
    inlines = [FaviconInline, LogoImageInline, ImageOneInline, BackgroundVideoInline]


admin.site.register(HomePage, HomePageAdmin)
