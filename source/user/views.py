import os
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse_lazy
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.template.loader import render_to_string
from social_django.utils import psa
from django.urls import reverse
from social_django.models import UserSocialAuth
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.views.generic import TemplateView, View
from .models import ActivityLog, CustomUser
from django.conf import settings
import stripe
from .models import Subscription

stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionView(LoginRequiredMixin, TemplateView):
    """Handle subscription page where user can update their subscriptions."""
    template_name = 'subscription.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'subscription': Subscription.objects.filter(user=self.request.user).first(),
            'plan_choices': Subscription.PLAN_CHOICES,
        })
        return context

    def post(self, request, *args, **kwargs):
        """Handle plan change."""
        plan = request.POST.get('plan')
        if plan not in dict(Subscription.PLAN_CHOICES):
            return HttpResponseForbidden("Invalid plan.")

        subscription = Subscription.objects.filter(user=request.user).first()
        if not subscription:
            messages.error(request, "No subscription found.")
            return redirect('settings')

        if subscription.plan_name == plan:
            messages.info(request, "You are already subscribed to this plan.")
            return redirect('settings')

        subscription.plan_name = plan
        if plan == 'free':
            subscription.stripe_subscription_id = None
            subscription.expires_at = None
            subscription.save()
            messages.success(request, "Your plan has been changed to Free.")
        else:
            stripe_subscription = self.update_stripe_subscription(subscription, plan)
            subscription.stripe_subscription_id = stripe_subscription.id
            subscription.save()
            messages.success(request, f"Your plan has been changed to {subscription.get_plan_name_display()}.")

        return redirect('settings')

    @staticmethod
    def update_stripe_subscription(subscription, plan):
        """Helper function to update Stripe subscription."""
        price_id = settings.STRIPE_PRICE_IDS.get(plan)

        # Ensure the customer exists
        if not subscription.stripe_customer_id:
            # Create a new Stripe customer if one doesn't exist
            customer = stripe.Customer.create(email=subscription.user.email)
            subscription.stripe_customer_id = customer.id
            subscription.save()
        else:
            customer = stripe.Customer.retrieve(subscription.stripe_customer_id)

        if subscription.stripe_subscription_id:
            # Update the existing subscription
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            stripe_subscription.items = [{
                'id': stripe_subscription.items.data[0].id,
                'price': price_id
            }]
            stripe_subscription.save()
        else:
            # Create a new subscription if one doesn't exist
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
            )

        return stripe_subscription


class SettingsView(LoginRequiredMixin, TemplateView):
    """Handle settings page where user can update their details and preferences."""
    template_name = 'settings.html'
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        """Render settings form with user details and preferences."""

        try:
            github_account = request.user.social_auth.get(provider='github')
        except UserSocialAuth.DoesNotExist:
            github_account = None

        subscription = Subscription.objects.filter(user=self.request.user).first()

        # Calculate the current folder size
        current_folder_size = self.get_folder_size(request.user.project_dir)  # In MB

        # Get the folder size limit (assuming it's a model field for user)
        storage_limit = subscription.storage_limit

        # Calculate remaining space
        remaining_size = storage_limit - current_folder_size

        context = {
            'subscription': Subscription.objects.filter(user=self.request.user).first(),
            'needs_password': not bool(request.user.password),
            'github_account': github_account,
            'enabled_notifications': ActivityLog.objects.filter(user=request.user, notification_enabled=True),
            'new_follower': ActivityLog.objects.filter(user=request.user, activity_type='new_follower', notification_enabled=True).first(),
            'task': ActivityLog.objects.filter(user=request.user, activity_type='task', notification_enabled=True).first(),
            'new_message': ActivityLog.objects.filter(user=request.user, activity_type='new_message', notification_enabled=True).first(),
            'project': ActivityLog.objects.filter(user=request.user, activity_type='project', notification_enabled=True).first(),
            'current_folder_size': current_folder_size,
            'remaining_size': remaining_size,
            'user_storage_limit': storage_limit
        }

        return self.render_to_response(context)

    @staticmethod
    def get_folder_size(folder_path):
        """Calculate the total size of files in a folder."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                file_path = os.path.join(dirpath, f)
                total_size += os.path.getsize(file_path)
        return total_size / (1024 * 1024)  # Return size in MB

    def post(self, request, *args, **kwargs):
        """
        Handle actions such as updating user information, notifications, or account.
        """
        action_map = {
            'update_user_info': self.update_user_info,
            'update_password': self.update_password,
            'update_notifications': self.update_notifications,
            'link_github': self.link_github,
            'unlink_github': self.unlink_github,
            'storage_limit': self.storage_limit,
            'update_docker_settings': self.update_docker_settings,
            'delete_account': self.delete_account,
        }
        action = next((key for key in action_map if key in request.POST), None)
        if action:
            return action_map[action](request)
        return HttpResponse("Invalid action", status=400)

    @staticmethod
    def update_user_info(request):
        """Update user profile information."""
        user = request.user
        profile_picture = request.FILES.get('profile_picture', None)
        if profile_picture:
            fs = FileSystemStorage()
            filename = fs.save(profile_picture.name, profile_picture)
            user.profile_picture = fs.url(filename)

        username = request.POST.get('username')
        email = request.POST.get('email')
        bio = request.POST.get('bio')

        if username:
            user.username = username
        if email:
            user.email = email
        if bio is not None:
            user.bio = bio

        user.save()
        messages.success(request, "Your profile has been updated.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def update_password(request):
        """Update the user's password."""
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_new_password')

        # Check if the user has a password set (if no password is set, allow them to update)
        if request.user.password != '' and not request.user.check_password(current_password):
            messages.error(request, "Incorrect current password.")
            return redirect('settings', username=request.user.username)

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('settings', username=request.user.username)

        user = request.user
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Keep user logged in after password change
        messages.success(request, "Your password has been updated.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def update_notifications(request):
        """Update notification preferences."""

        notification_map = {
            'new_follower': 'new_follower_notifications',
            'new_message': 'message_notifications',
            'task_created': 'task_notifications',
            'task_updated': 'task_notifications',
            'task_deleted': 'task_notifications',
            'project_created': 'project_notifications',
            'project_updated': 'project_notifications',
            'project_deleted': 'project_notifications',
            'collaborator_added': 'project_notifications',
        }

        user = request.user
        for activity_type, post_key in notification_map.items():
            ActivityLog.objects.filter(user=user, activity_type=activity_type).update(
                notification_enabled=post_key in request.POST
            )

        return redirect('settings', username=user.username)

    @staticmethod
    def clear_notifications(request):
        """Delete all notifications for the user."""
        ActivityLog.objects.filter(user=request.user).delete()
        messages.success(request, "All notifications and user activity has been deleted.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def link_github(request):
        """Handle linking the user's GitHub account."""
        user = request.user
        if user.is_authenticated:
            # Check if the user already has a linked GitHub account
            if user.social_auth.filter(provider='github').exists():
                messages.info(request, "Your GitHub account is already linked.")
            else:
                # You can trigger the GitHub login if the account is not linked
                messages.info(request, "You will now be redirected to link your GitHub account.")
                return redirect('social:begin', args=['github'])
        else:
            messages.error(request, "You must be logged in to link your GitHub account.")

        return redirect('settings', username=request.user.username)

    @staticmethod
    def unlink_github(request):
        """Handle unlinking the user's GitHub account."""
        user = request.user
        if user.is_authenticated:
            try:
                # Check if the user has a linked GitHub account
                github_account = user.social_auth.get(provider='github')
                github_account.delete()
                messages.success(request, "GitHub account unlinked successfully.")
            except UserSocialAuth.DoesNotExist:
                messages.info(request, "No linked GitHub account found.")
        else:
            messages.error(request, "You must be logged in to unlink your GitHub account.")

        return redirect('settings', username=request.user.username)

    @staticmethod
    def storage_limit(request):
        """Update storage limit for the user (admin only)."""
        user = request.user
        if not user.is_admin:
            messages.error(request, "You do not have permission to update storage limit")
            return redirect('settings', username=request.user.username)

        user.user_storage_limit = request.POST.get('user_storage_limit', user.user_storage_limit)

        user.save()
        messages.success(request, "Storage limit updated successfully.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def update_docker_settings(request):
        """Update Docker-related settings for the user (admin only)."""
        user = request.user
        if not user.is_admin:
            messages.error(request, "You do not have permission to update Docker settings.")
            return redirect('settings', username=request.user.username)

        user.default_mem_limit = request.POST.get('default_mem_limit', user.default_mem_limit)
        user.default_memswap_limit = request.POST.get('default_memswap_limit', user.default_memswap_limit)
        user.default_cpus = request.POST.get('default_cpus', user.default_cpus)
        user.default_cpu_shares = request.POST.get('default_cpu_shares', user.default_cpu_shares)

        user.save()
        messages.success(request, "Docker settings updated successfully.")
        return redirect('settings', username=request.user.username)

    @staticmethod
    def delete_account(request):
        """Delete the user's account."""
        password = request.POST.get('password')
        if not request.user.check_password(password):
            messages.error(request, "Incorrect password.")
            return redirect('settings', username=request.user.username)

        request.user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect('home')


class LoginView(View):
    """Handle user login."""
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('settings' if not user.password else 'profile', username=user.username)

        messages.error(request, 'Invalid username or password')
        return redirect('login')


class RegisterView(View):
    """Handle user registration."""
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken')
        elif CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
        else:
            user = CustomUser.objects.create_user(username=username, email=email, password=password, is_active=False)
            self.send_verification_email(user, request)
            messages.success(request, 'Registration successful! Please check your email to verify your account.')
            return redirect('login')

        return redirect('register')

    @staticmethod
    def send_verification_email(user, request):
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = request.build_absolute_uri(reverse('verify_email', kwargs={'uidb64': uid, 'token': token}))

        send_mail(
            "Verify Your Email Address",
            render_to_string('email_verification.html', {'user': user, 'verification_url': verification_url}),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )


class VerifyEmailView(View):
    """Handle email verification and activation."""

    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            messages.error(request, "Invalid verification link.")
            return redirect('login')

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, "Your email has been verified! You can now log in.")
        else:
            self.send_verification_email(user, request)
            messages.warning(request, "Verification link expired. A new email has been sent.")

        return redirect('login')

    @staticmethod
    def send_verification_email(user, request):
        RegisterView.send_verification_email(user, request)


class GithubAuthView(View):
    """Handle GitHub authentication."""
    provider = 'github'

    def get(self, request):
        return redirect('social:begin', self.provider)


class GithubCompleteRedirectView(View):
    """Handle GitHub authentication redirect."""

    def get(self, request):
        user = request.user
        if user.is_authenticated and user.social_auth.filter(provider='github').exists():
            messages.success(request, 'GitHub account successfully linked!')
        return redirect('home')


class LogoutView(View):
    """Handle user logout."""

    def post(self, request):
        logout(request)
        return redirect('home')


class PasswordResetView(View):
    """Handle password reset."""
    template_name = 'reset_password.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()

        if user:
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(
                reverse_lazy('password_reset_confirm',
                             kwargs={'uidb64': urlsafe_base64_encode(force_bytes(user.pk)), 'token': token})
            )
            send_mail(
                'Password Reset Request',
                render_to_string('password_reset_email.html', {'user': user, 'reset_link': reset_link}),
                settings.DEFAULT_FROM_EMAIL,
                [email]
            )
            messages.success(request, 'Password reset link has been sent to your email.')
        else:
            messages.error(request, 'No user found with that email address.')

        return redirect('reset_password')


class ForgotUsernameView(View):
    """Handle forgot username process."""
    template_name = 'reset_username.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()

        if user:
            send_mail(
                'Forgot Username Request',
                render_to_string('username_reset_email.html', {'username': user.username}),
                settings.DEFAULT_FROM_EMAIL,
                [email]
            )
            messages.success(request, 'Your username has been sent to your email.')
        else:
            messages.error(request, 'No user found with that email address.')

        return redirect('reset_username')
