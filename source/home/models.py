from django.db import models


class HomePage(models.Model):
    """
    Model representing the home page.
    """

    website_title = models.CharField(max_length=100, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """
        String representation of the home page.
        """
        return self.website_title or "Untitled Home Page"

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"


class Logo(models.Model):
    """
    Model representing an image uploaded for the home page.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the home page image.
        """
        return self.image.name


class Favicon(models.Model):
    """
    Model representing the favicon for the home page.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    favicon = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the favicon.
        """
        return self.favicon.name


class ErrorImage(models.Model):
    """
    Model representing an image for the home page.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    error_image = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the image.
        """
        return self.error_image.name


class ImageOne(models.Model):
    """
    Model representing an image for the home page.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    image_one = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the image.
        """
        return self.image_one.name


class ImageTwo(models.Model):
    """
    Model representing an image for the home page.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    image_two = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the image.
        """
        return self.image_two.name


class ImageThree(models.Model):
    """
    Model representing an image for the home page.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    image_three = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the image.
        """
        return self.image_three.name


class ImageFour(models.Model):
    """
    Model representing an image for the home page.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    image_four = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the image.
        """
        return self.image_four.name


class Background(models.Model):
    """
    Model representing the background video for the home page.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    video = models.FileField(upload_to='')

    def __str__(self):
        """
        String representation of the background video.
        """
        return self.video.name
