from django.contrib import admin
from .models import (
    HomePage,
    Logo,
    Favicon,
    ErrorImage,
    ImageOne,
    ImageTwo,
    ImageThree,
    ImageFour,
    Background,
)


class SingleInstanceInline(admin.TabularInline):
    """
    Base class for single-instance inlines.
    """
    extra = 0
    max_num = 1
    can_delete = True


class LogoInline(SingleInstanceInline):
    model = Logo


class FaviconInline(SingleInstanceInline):
    model = Favicon


class ErrorImageInline(SingleInstanceInline):
    model = ErrorImage


class ImageOneInline(SingleInstanceInline):
    model = ImageOne


class ImageTwoInline(SingleInstanceInline):
    model = ImageTwo


class ImageThreeInline(SingleInstanceInline):
    model = ImageThree


class ImageFourInline(SingleInstanceInline):
    model = ImageFour


class BackgroundInline(SingleInstanceInline):
    model = Background


@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
    """
    Admin interface for the HomePage model.
    """
    list_display = ("website_title", "updated_at")
    search_fields = ("website_title",)
    inlines = [
        LogoInline,
        FaviconInline,
        ErrorImageInline,
        ImageOneInline,
        ImageTwoInline,
        ImageThreeInline,
        ImageFourInline,
        BackgroundInline,
    ]

    def has_add_permission(self, request):
        """
        Allow adding only one instance of HomePage.
        """
        if HomePage.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """
        Disallow deletion of the HomePage instance.
        """
        return False
