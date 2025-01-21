from django.contrib import admin
from .models import Favicon, Logo, Background, HomePage, ErrorImage, ImageOne


# Inline admin classes
class FaviconInline(admin.StackedInline):
    """Inline admin for the Favicon model."""
    model = Favicon


class LogoInline(admin.StackedInline):
    """Inline admin for the Logo model."""
    model = Logo


class ErrorImageInline(admin.StackedInline):
    """Inline admin for the ErrorImage model."""
    model = ErrorImage


class ImageOneInline(admin.StackedInline):
    """Inline admin for the ImageOne model."""
    model = ImageOne


class BackgroundInline(admin.StackedInline):
    """Inline admin for the Background model."""
    model = Background


# Admin class for the HomePage model
class HomePageAdmin(admin.ModelAdmin):
    """Admin interface for the HomePage model with inlines."""
    list_display = ('website_title', 'page_title', 'updated_at')
    search_fields = ('website_title', 'page_title')
    inlines = [FaviconInline, LogoInline, ErrorImageInline, ImageOneInline, BackgroundInline]

    ordering = ('-updated_at',)
    list_filter = ('updated_at',)


# Register HomePage model with its admin class
admin.site.register(HomePage, HomePageAdmin)
