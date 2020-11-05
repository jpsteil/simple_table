from functools import reduce
from urllib.parse import unquote_plus

from pydal.objects import Field

from py4web import request
from py4web.utils.form import Form, FormStyleBulma


class GridSearch:
    def __init__(self, search_queries, queries=None):
        self.search_queries = search_queries
        self.queries = queries

        field_names = []
        field_requires = dict()
        for field in self.search_queries:
            field_name = 'sq_' + field[0].replace(' ', '_').lower()
            field_names.append(field_name)
            if len(field) > 2:
                field_requires[field_name] = field[2]

        field_values = dict()
        for field in field_names:
            if field in request.query:
                field_values[field] = unquote_plus(request.query[field])

        form_fields = []
        for field in field_names:
            label = field.replace('sq_', '').replace('_', ' ').title()
            placeholder = field.replace('sq_', '').replace('_', ' ').capitalize()
            form_fields.append(Field(field,
                                     length=50,
                                     default=field_values[field] if field in field_values else None,
                                     _placeholder=placeholder,
                                     label=label,
                                     requires=field_requires[field] if field in field_requires else None,
                                     _title=placeholder))

        self.search_form = Form(form_fields,
                                keep_values=True,
                                formstyle=FormStyleBulma,
                                form_name='search_form')

        if self.search_form.accepted:
            for field in field_names:
                field_values[field] = self.search_form.vars[field]

        if not self.queries:
            self.queries = []
        for sq in self.search_queries:
            field_name = 'sq_' + sq[0].replace(' ', '_').lower()
            if field_name in field_values and field_values[field_name]:
                self.queries.append(sq[1](field_values[field_name]))

        self.query = reduce(lambda a, b: (a & b), self.queries)
