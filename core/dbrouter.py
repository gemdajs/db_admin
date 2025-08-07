
class ExternalDBRouter:
    """
    Routes database operations for specific models or apps to a different database.
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'dbsync':  # or check model name
            return 'external'

        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'dbsync':
            return 'external'

        return None

    def allow_relation(self, obj1, obj2, **hints):
        db_list = ('default', 'external')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True

        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'dbsync':
            return db == 'external'

        return db == 'default'