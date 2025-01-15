from django.db import models


class HomePage(models.Model):
    """
    Model representing the home page.

    Attributes:
        page_title (str): The title of the home page.
        page_description (str): The description of the home page.
        updated_at (datetime): The date and time when the home page was last updated.
    """

    website_title = models.CharField(max_length=100, blank=True, null=True)
    page_title = models.CharField(max_length=100, blank=True, null=True)
    page_heading = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """
        String representation of the home page.

        Returns:
            str: The title of the home page.
        """
        return self.page_title or "Untitled Home Page"

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"


class Logo(models.Model):
    """
    Model representing images uploaded for the home page.

    Attributes:
        home_page (HomePage): The home page associated with the image.
        image (ImageField): The uploaded image.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the home page image.

        Returns:
            str: The filename of the image.
        """
        return self.image.name


class Favicon(models.Model):
    """
    Model representing the favicon for the home page.

    Attributes:
        home_page (HomePage): The home page associated with the favicon.
        favicon (ImageField): The uploaded favicon image.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    favicon = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the favicon.

        Returns:
            str: The filename of the favicon.
        """
        return self.favicon.name


class ImageOne(models.Model):
    """
    Model representing an image for the home page.

    Attributes:
        home_page (HomePage): The home page associated with the image_one.
        image_one (ImageOne): The uploaded image_one image.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    image_one = models.ImageField(upload_to='')

    def __str__(self):
        """
        String representation of the image_one.

        Returns:
            str: The filename of the image_one.
        """
        return self.image_one.name


class Background(models.Model):
    """
    Model representing the background video for the home page.

    Attributes:
        home_page (HomePage): The home page associated with the background video.
        video (FileField): The uploaded background video file.
    """

    home_page = models.OneToOneField(HomePage, on_delete=models.CASCADE)
    video = models.FileField(upload_to='')

    def __str__(self):
        """
        String representation of the background video.

        Returns:
            str: The filename of the video.
        """
        return self.video.name


