from __future__ import annotations

from typing import Any, cast

from django.db.models import Field
from modeltranslation.manager import MultilingualQuerySet, rewrite_lookup_key


def patch_multilingual_queryset_update() -> None:
    """Make django-modeltranslation work with Django 6's QuerySet._update signature."""
    if getattr(MultilingualQuerySet, "_compat_patched", False):
        return

    def _update(self, values: list[tuple[Field, type[Any] | None, Any]], returning_fields=None):
        field_names_to_update = {field.name for field, *_ in values}

        translation_values: list[tuple[Field, type[Any] | None, Any]] = []
        for field, model, value in values:
            translation_field_name = rewrite_lookup_key(self.model, field.name)
            if translation_field_name not in field_names_to_update:
                translatable_field = cast(Field, self.model._meta.get_field(translation_field_name))
                translation_values.append((translatable_field, model, value))

        values += translation_values
        try:
            return super(MultilingualQuerySet, self)._update(values, returning_fields=returning_fields)
        except TypeError:
            return super(MultilingualQuerySet, self)._update(values)

    MultilingualQuerySet._update = _update
    MultilingualQuerySet._compat_patched = True


patch_multilingual_queryset_update()
