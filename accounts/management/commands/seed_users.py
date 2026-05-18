from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create dummy users for testing and development'

    def handle(self, *args, **options):
        """Create dummy users if they don't exist"""
        users_created = 0

        # Admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@proctoring.local',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            admin.role = 'admin'
            admin.save()
            users_created += 1
            self.stdout.write(self.style.SUCCESS('✓ Created admin user (admin / admin123)'))
        else:
            self.stdout.write(self.style.WARNING('• Admin user already exists'))

        # Interviewer user
        if not User.objects.filter(username='interviewer').exists():
            interviewer = User.objects.create_user(
                username='interviewer',
                email='interviewer@proctoring.local',
                password='interviewer123',
                first_name='John',
                last_name='Interviewer',
                is_staff=True,
                is_active=True
            )
            interviewer.role = 'interviewer'
            interviewer.save()
            users_created += 1
            self.stdout.write(self.style.SUCCESS('✓ Created interviewer user (interviewer / interviewer123)'))
        else:
            self.stdout.write(self.style.WARNING('• Interviewer user already exists'))

        # Candidate user
        if not User.objects.filter(username='candidate').exists():
            candidate = User.objects.create_user(
                username='candidate',
                email='candidate@proctoring.local',
                password='candidate123',
                first_name='Jane',
                last_name='Candidate',
                is_active=True
            )
            candidate.role = 'candidate'
            candidate.save()
            users_created += 1
            self.stdout.write(self.style.SUCCESS('✓ Created candidate user (candidate / candidate123)'))
        else:
            self.stdout.write(self.style.WARNING('• Candidate user already exists'))

        if users_created > 0:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully created {users_created} user(s)'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  All users already exist'))
