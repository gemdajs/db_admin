import traceback

from django.utils import timezone


class AppLogger:

    @staticmethod
    def print(*args):
        print("DEBUG::[{}]".format(timezone.now()), *args)

    @staticmethod
    def report(e=None, error=None):
        traceback.print_exc()
        if e:
            pass
        if error:
            AppLogger.print(error)
