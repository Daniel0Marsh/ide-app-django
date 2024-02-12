from django.shortcuts import render
from django.views.generic import TemplateView
from .models import Project, File, Directory
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse


class IdeView(TemplateView):
    """
    A view handling the Integrated Development Environment (IDE) operations.

    Methods:
        get(self, request): Handles GET requests.
        post(self, request): Handles POST requests.
        open_file(self, request): Opens the selected file.
        create_folder(self, request): Creates a new directory.
        create_file(self, request): Creates a new file.
        delete(self, request): Deletes a file or directory.
        save_file(self, request): Saves changes made to a file.
    """

    template_name = 'ide.html'

    def get(self, request):
        """
        Handles GET requests.

        Retrieves the latest project and its last edited file,
        then renders the Integrated Development Environment (IDE) template with the context.

        :param request: HttpRequest object representing the request made to the server.
        :return: HttpResponse object containing the rendered template with the context.
        """
        project = Project.objects.first()
        last_edited_file = File.objects.filter(project=project).order_by('-pk').first()

        context = {
            'project': project,
            'file': last_edited_file,
        }

        return render(request, self.template_name, context)

    def post(self, request):
        """
        Handles POST requests.

        Determines the action based on the POST request and delegates to the appropriate method.

        :param request: HttpRequest object representing the POST request made to the server.
        :return: HttpResponse object returned by the delegated method.
        """
        post_handlers = {
            'delete': self.delete,
            'save_file': self.save_file,
            'rename_file': self.save_file,
            'create_dir': self.create_folder,
            'create_file': self.create_file,
            'open_file': self.open_file
        }

        action = next((key for key in post_handlers if key in request.POST), None)

        if action:
            return post_handlers[action](request)

    def open_file(self, request):
        """
        Opens the selected file.

        :param request: HttpRequest object representing the request made to the server.
        :return: HttpResponse object containing the rendered template with the context.
        """
        project_id = request.POST.get('project_id')
        file_id = request.POST.get('open_file')

        # Get the project object based on the provided project_id
        project = get_object_or_404(Project, pk=project_id)
        file = get_object_or_404(File, pk=file_id)

        context = {
            'project': project,
            'file': file,
        }

        return render(request, self.template_name, context)

    @staticmethod
    def create_folder(request):
        """
        Creates a new directory.

        :param request: HttpRequest object representing the request made to the server.
        :return: HttpResponseRedirect object redirecting to the 'project' URL.
        """
        parent_dir = request.POST.get('parent_dir')
        dir_name = request.POST.get('item_name')
        project_id = request.POST.get('project_id')

        if not parent_dir:
            parent_dir = None

        # Get the project object based on the provided project_id
        project = get_object_or_404(Project, pk=project_id)

        directory = Directory.objects.create(
            project=project,
            directory_name=dir_name,
            parent_directory=parent_dir
        )

        # Save the dir object
        directory.save()

        return HttpResponseRedirect(reverse('project'))

    @staticmethod
    def create_file(request):
        """
        Creates a new file.

        :param request: HttpRequest object representing the request made to the server.
        :return: HttpResponseRedirect object redirecting to the 'project' URL.
        """
        parent_dir_id = request.POST.get('parent_dir_id')
        file_name = request.POST.get('item_name')
        project_id = request.POST.get('project_id')

        if not parent_dir_id:
            parent_directory = None
        else:
            parent_directory = Directory.objects.get(pk=parent_dir_id)

        # Get the project object based on the provided project_id
        project = get_object_or_404(Project, pk=project_id)

        # Create a new file object
        file = File.objects.create(
            project=project,
            file_name=file_name,
        )

        # Associate the file with the correct directory if parent_directory is provided
        if parent_directory:
            parent_directory.files.add(file)

        return HttpResponseRedirect(reverse('project'))

    @staticmethod
    def delete(request):
        """
        Deletes a file or directory.

        :param request: HttpRequest object representing the request made to the server.
        :return: HttpResponseRedirect object redirecting to the 'project' URL.
        """
        item_id = request.POST.get('item_id')

        # Check if item_id is not empty
        if item_id is not None and item_id != '':
            try:
                item = get_object_or_404(File, pk=item_id)
            except:
                item = get_object_or_404(Directory, pk=item_id)
            if item:
                item.delete()

        # Redirect to the project page regardless of whether the file was deleted or not
        return HttpResponseRedirect(reverse('project'))

    def save_file(self, request):
        """
        Saves changes made to a file.

        :param request: HttpRequest object representing the request made to the server.
        :return: HttpResponse object containing the rendered template with the context.
        """
        contents = request.POST.get('contents')
        file_name = request.POST.get('file_name')
        file_id = request.POST.get('item_id')
        project_id = request.POST.get('project_id')
        selected_theme = request.POST.get('selected_theme')
        selected_syntax = request.POST.get('selected_syntax')

        # Get the project object based on the provided project_id
        project = get_object_or_404(Project, pk=project_id)

        # If file_id is provided, try to get the file object, else create a new file object
        if file_id:
            file = get_object_or_404(File, pk=file_id)
            file.contents = contents
            file.file_name = file_name
        else:
            # Create a new file object
            file = File.objects.create(
                project=project,
                file_name=file_name,
                contents=contents
            )

        if selected_theme:
            project.selected_theme = selected_theme
        if selected_syntax:
            project.selected_syntax = selected_syntax
        project.save()
        file.save()

        context = {
            'project': project,
            'file': file,
        }

        return render(request, self.template_name, context)
