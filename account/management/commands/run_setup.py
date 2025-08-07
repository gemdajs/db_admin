from django.core.management import call_command
from django.core.management.base import BaseCommand

from account.models import DBSyncUser
from utils.log_util import AppLogger


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("-u", "--username", required=False)
        parser.add_argument("-e", "--email", required=False)
        parser.add_argument("-p", "--password", required=False)
        parser.add_argument("-f", "--first_name", required=False)
        parser.add_argument("-l", "--last_name", required=False)

    def handle(self, *args, **options):
        username = options.get("username")
        email = options.get("email")
        password = options.get("password")
        first_name = options.get("first_name")
        last_name = options.get("last_name")

        call_command("makemigrations", "account")
        call_command("migrate")

        try:
            if username and email and password and first_name and last_name:
                user = DBSyncUser.objects.create_superuser(
                    username,
                    email,
                    password,
                    first_name=first_name,
                    last_name=last_name,
                )

                if user:
                    AppLogger.print("User: {} created successfully".format(user))
                else:
                    AppLogger.print("Unable to create user")
            else:
                AppLogger.print("User details incomplete, create user skipped")

        except Exception as e:
            AppLogger.report(e)
