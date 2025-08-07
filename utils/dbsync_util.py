import json

import psycopg2
from django.conf import settings
from django.db import models
from inflection import pluralize, singularize

from account.models import DBSyncModelColumn
from utils.log_util import AppLogger

_model_registry_built = False

app_label = "dbsync"

TYPE_MAP = {
    "integer": models.IntegerField,
    "int": models.IntegerField,
    "bigint": models.BigIntegerField,
    "smallint": models.SmallIntegerField,
    "serial": models.AutoField,
    "bigserial": models.BigAutoField,

    "numeric": lambda precision, scale: models.DecimalField(max_digits=precision or 20, decimal_places=scale or 6),
    "decimal": lambda precision, scale: models.DecimalField(max_digits=precision or 20, decimal_places=scale or 6),
    "real": models.FloatField,
    "double precision": models.FloatField,

    "character varying": lambda max_length: models.CharField(max_length=max_length or 255),
    "varchar": lambda max_length: models.CharField(max_length=max_length or 255),
    "character": lambda max_length: models.CharField(max_length=max_length or 255),
    "char": lambda max_length: models.CharField(max_length=max_length or 255),
    "text": models.TextField,

    "boolean": models.BooleanField,
    "bool": models.BooleanField,

    "date": models.DateField,
    "time": models.TimeField,
    "time without time zone": models.TimeField,
    "timestamp": models.DateTimeField,
    "timestamp without time zone": models.DateTimeField,
    "timestamp with time zone": models.DateTimeField,

    # "json": models.JSONField,
    # "jsonb": models.JSONField,

    "uuid": models.UUIDField,
    "inet": models.GenericIPAddressField,
    "bytea": models.BinaryField,
}

__models = {}

__many_to_many_fields = {}
__foreign_fields = {}
__model_fields = {}
__field_model_mapping = {}

__excluded_fields = []


class ExternalDBManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().using("external")

    def db(self):
        return self.using('external')


def to_camel_case(name):
    return ''.join(part.capitalize() for part in name.split('_'))


def is_m2m_join_table(table_def):
    fk_count = 0
    non_fk_cols = []

    for col_name, col_def in table_def["columns"].items():
        if col_def.get("foreign_key"):
            fk_count += 1
        elif col_name != "id":
            non_fk_cols.append(col_name)

    return fk_count == 2 and not non_fk_cols


def get_base_model_name(table):
    return table


def make_str_method(name):
    def _str(self):

        value_list = list(DBSyncModelColumn.objects.filter(model=name, repr_order__isnull=False).order_by("repr_order").values_list("name", flat=True))
        if not value_list:
            if hasattr(settings, "MODEL_STRING_VALUE_MAPS"):
                name_maps = getattr(settings, "MODEL_STRING_VALUE_MAPS")
                if name in name_maps:
                    value_list = name_maps[name]

        values = []
        for field in value_list:
            if callable(field):
                return field(self)
            elif hasattr(self, field):
                values.append(str(getattr(self, field)))

        if not values and hasattr(self, "id"):
            values.append("{}: {}".format(name, str(getattr(self, "id"))))

        if not values:
            values.append(f"<{name} object>")

        return " ".join(values)

    return _str


def build_dynamic_models():
    global _model_registry_built, __models, __many_to_many_fields, __foreign_fields, __model_fields, __field_model_mapping

    if _model_registry_built:
        return __models, __foreign_fields, __many_to_many_fields, __model_fields, __field_model_mapping

    schema = introspect_postgres_schema()
    m2m_tables = {}

    column_ids = []

    for table_name, table_def in schema["tables"].items():

        model_name = get_base_model_name(table_name)
        if is_m2m_join_table(table_def):
            m2m_tables[model_name] = table_def

        attrs = {
            "__module__": f"{app_label}.models",
            "objects": ExternalDBManager(),
            "Meta": type('Meta', (), {
                'db_table': table_name,
                'app_label': app_label,
                'managed': False,
                'default_manager_name': 'objects',
                "verbose_name_plural": pluralize(table_name.replace("_", " ").title()),
                "verbose_name": singularize(table_name).replace("_", " ").title(),
            })
        }

        if model_name not in __model_fields:
            __model_fields[model_name] = []

        order = 0

        for col_name, col_def in table_def["columns"].items():
            foreign_key = col_def.get("foreign_key")

            col_type = col_def["type"]
            max_length = col_def.get("max_length")
            precision = col_def.get("precision")
            scale = col_def.get("scale")
            model_field = TYPE_MAP.get(col_type)

            is_searchable = False

            if callable(model_field):
                if "char" in col_type or "varchar" in col_type:
                    field = model_field(max_length)
                    is_searchable = True
                elif col_type in ["numeric", "decimal"]:
                    field = model_field(precision, scale)
                else:
                    field = model_field()
            elif model_field:
                field = model_field()
            else:
                is_searchable = True
                field = models.TextField()
            try:
                rec, is_created = DBSyncModelColumn.objects.get_or_create(
                    model=model_name,
                    name=col_name,
                    defaults={
                        "in_searchable_list": is_searchable,
                        "in_list_filter_list": False,
                        "in_list_display_list": True,
                        "in_autocomplete_list": foreign_key is not None,
                        "is_foreign_key": foreign_key is not None,
                        "order": order
                    }
                )

                if (rec.order != order and order > 0 and not is_created) or (foreign_key and not rec.is_foreign_key) or (not foreign_key and rec.is_foreign_key):
                    rec.is_foreign_key = foreign_key is not None
                    rec.description = col_type
                    rec.order = order
                    rec.save(update_fields=["order", "is_foreign_key", "description"])

                order += 1

                column_ids.append(rec.id)
            except Exception as e:
                pass

            if foreign_key:
                continue  # Skip foreign keys in the first pass

            field.null = col_def.get("nullable", True)
            field.blank = col_def.get("nullable", True)
            if col_name == "id":
                field.primary_key = True

            attrs[col_name] = field
            __model_fields[model_name].append(col_name)

        attrs['__str__'] = make_str_method(model_name)
        __models[model_name] = type(to_camel_case(model_name), (models.Model,), attrs)
    try:
        DBSyncModelColumn.objects.exclude(pk__in=column_ids).delete()
    except Exception:
        pass

    # Second pass: Add relationships
    for table_name, table_def in schema["tables"].items():
        model_name = get_base_model_name(table_name)
        model = __models.get(model_name)

        for col_name, col_def in table_def["columns"].items():
            fk = col_def.get("foreign_key")
            if not fk:
                continue

            target_table = get_base_model_name(fk["table"])
            target_model = __models.get(target_table)
            field_name = col_name[:-3] if col_name.endswith("_id") else col_name

            if not target_model:
                continue

            if hasattr(model, field_name):
                continue

            field = models.ForeignKey(
                target_model,
                on_delete=models.CASCADE,
                db_column=col_name,
                null=col_def.get("nullable", True),
                related_name="+"
            )

            model.add_to_class(field_name, field)

            if model_name not in __foreign_fields:
                __foreign_fields[model_name] = []
            if field_name not in __foreign_fields[model_name]:
                __foreign_fields[model_name].append(field_name)

            __model_fields[model_name].append(field_name)
            __field_model_mapping[f"{model_name}:{field_name}"] = target_table

    # Handle many-to-many relationships
    for m2m_table, table_def in m2m_tables.items():
        fks = [col for col, defn in table_def["columns"].items() if defn.get("foreign_key")]

        if len(fks) != 2:
            continue

        fk_defs = [table_def["columns"][fk]["foreign_key"] for fk in fks]
        table_a, table_b = get_base_model_name(fk_defs[0]["table"]), get_base_model_name(fk_defs[1]["table"])

        model_a = __models.get(table_a)
        model_b = __models.get(table_b)
        through_model = __models.get(m2m_table)

        if not all([model_a, model_b, through_model]):
            continue

        field_name = table_b
        if hasattr(model_a, field_name):
            field_name = f"{field_name}_m2m"

        source_field = fks[0][:-3] if fks[0].endswith('_id') else fks[0]
        target_field = fks[1][:-3] if fks[1].endswith('_id') else fks[1]

        m2m_field = models.ManyToManyField(
            model_b,
            through=through_model,
            related_name="+",
            through_fields=(source_field, target_field)
        )

        if table_a not in __many_to_many_fields:
            __many_to_many_fields[table_a] = []
        if field_name not in __many_to_many_fields[table_a]:
            __many_to_many_fields[table_a].append(field_name)

        model_a.add_to_class(field_name, m2m_field)
        __field_model_mapping[f"{table_a}:{field_name}"] = table_b

    _model_registry_built = True

    return __models, __foreign_fields, __many_to_many_fields, __model_fields, __field_model_mapping


def introspect_postgres_schema():
    database = settings.DATABASES.get("external")
    conn = psycopg2.connect(
        dbname=database.get("NAME"),
        user=database.get("USER"),
        password=database.get("PASSWORD"),
        host=database.get("HOST"),
        port=database.get("PORT"),
    )
    cur = conn.cursor()

    cur.execute("SELECT " + "table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = [row[0] for row in cur.fetchall()]

    schema = {"tables": {}}

    for table in tables:
        cur.execute(
            "SELECT " + f"column_name, data_type, is_nullable, column_default FROM "
                        f"information_schema.columns WHERE table_name = '{table}';"
        )
        columns = {}
        for col in cur.fetchall():
            col_name, col_type, is_nullable, default = col
            columns[col_name] = {
                "type": col_type,
                "nullable": is_nullable == 'YES',
                "default": default
            }

        # Foreign key constraints
        cur.execute(
            "SELECT " + f"kcu.column_name, ccu.table_name AS foreign_table, ccu.column_name AS foreign_column"
                        f" FROM information_schema.table_constraints AS tc JOIN information_schema.key_column_usage"
                        f" AS kcu ON tc.constraint_name = kcu.constraint_name "
                        f"JOIN information_schema.constraint_column_usage AS ccu ON "
                        f"ccu.constraint_name = tc.constraint_name WHERE tc.constraint_type = 'FOREIGN KEY' "
                        f"AND tc.table_name='{table}';"
        )

        relations = {}
        for col_name, foreign_table, foreign_column in cur.fetchall():
            columns[col_name]["foreign_key"] = {
                "table": foreign_table,
                "column": foreign_column
            }
            relations[foreign_table] = {
                "type": "many-to-one",
                "target": foreign_table,
                "foreign_key": col_name
            }

        schema["tables"][table] = {
            "columns": columns,
            "relations": relations
        }

    cur.close()
    conn.close()

    return schema

app_models = build_dynamic_models()
