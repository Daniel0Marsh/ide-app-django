from django.contrib import admin
from .models import Favicon, Logo, Background, HomePage, ImageOne


class FaviconInline(admin.StackedInline):
    """Inline admin for the Favicon model."""
    model = Favicon


class ImageOneInline(admin.StackedInline):
    """Inline admin for the ImageOne model."""
    model = ImageOne


class LogoImageInline(admin.StackedInline):
    """Inline admin for the Logo model."""
    model = Logo


class BackgroundVideoInline(admin.StackedInline):
    """Inline admin for the Background model."""
    model = Background


class HomePageAdmin(admin.ModelAdmin):
    """Admin interface for the HomePage model with inlines."""
    inlines = [FaviconInline, LogoImageInline, ImageOneInline, BackgroundVideoInline]


admin.site.register(HomePage, HomePageAdmin)
