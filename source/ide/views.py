from django.shortcuts import render
from django.views.generic import TemplateView
from .models import Project, File, Directory
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import Http404

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

        context = {'project': project,'file': last_edited_file}

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
        project = get_object_or_404(Project, pk=project_id)
        file = get_object_or_404(File, pk=file_id)

        context = {'project': project, 'file': file}

        return render(request, self.template_name, context)

    @staticmethod
    def create_folder(request):
        """
        Create a new directory.

        Parameters:
        - request: HttpRequest object representing the request made to the server.

        Returns:
        - HttpResponseRedirect object redirecting to the 'project' URL.
        """
        parent_dir_id = request.POST.get('parent_dir_id')
        dir_name = request.POST.get('item_name')
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, pk=project_id)

        parent_directory = get_object_or_404(Directory, pk=parent_dir_id) if parent_dir_id else None

        directory = Directory.objects.create(project=project, directory_name=dir_name, parent_directory=parent_directory)

        directory.save()

        return HttpResponseRedirect(reverse('project'))

    @staticmethod
    def create_file(request):
        """
        Create a new file.

        Parameters:
        - request: HttpRequest object representing the request made to the server.

        Returns:
        - HttpResponseRedirect object redirecting to the 'project' URL.
        """

        parent_dir_id = request.POST.get('parent_dir_id')
        file_name = request.POST.get('item_name')
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, pk=project_id)

        parent_directory = get_object_or_404(Directory, pk=parent_dir_id) if parent_dir_id else None
        file = File.objects.create(project=project, file_name=file_name)

        if parent_directory:
            parent_directory.files.add(file)

        return HttpResponseRedirect(reverse('project'))

    @staticmethod
    def delete(request):
        """
        Delete a file or directory.

        Parameters:
        - request: HttpRequest object representing the request made to the server.

        Returns:
        - HttpResponseRedirect object redirecting to the 'project' URL.
        """

        item_id = request.POST.get('item_id')

        if item_id:
            try:
                item = get_object_or_404(File, pk=item_id)
            except Http404:
                    item = get_object_or_404(Directory, pk=item_id)
            if item:
                item.delete()

        return HttpResponseRedirect(reverse('project'))

    def save_file(self, request):
        """
        Save changes made to a file.

        Parameters:
        - request: HttpRequest object representing the request made to the server.

        Returns:
        - HttpResponse object containing the rendered template with the context.
        """

        data = request.POST
        contents = data.get('contents')
        file_name = data.get('file_name')
        file_id = data.get('item_id')
        project_id = data.get('project_id')
        selected_theme = data.get('selected_theme')
        selected_syntax = data.get('selected_syntax')
        project = get_object_or_404(Project, pk=project_id)

        if file_id:
            file = get_object_or_404(File, pk=file_id)
            file.contents = contents
            file.file_name = file_name
        else:
            file = File.objects.create(project=project, file_name=file_name, contents=contents)

        if selected_theme:
            project.selected_theme = selected_theme
        if selected_syntax:
            project.selected_syntax = selected_syntax
        project.save()
        file.save()

        context = {'project': project,'file': file}

        return render(request, self.template_name, context)
