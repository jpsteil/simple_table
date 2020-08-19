from functools import reduce

from yatl.helpers import DIV, TABLE, TR, TD, TH, A, SPAN, I, THEAD, P, TAG, INPUT, SCRIPT, XML
from pydal.validators import IS_NULL_OR, IS_IN_SET
from py4web import request, URL, response, redirect
from py4web.utils.form import Form, FormStyleDefault
from .. import settings
from ..models import db
import uuid
import json

NAV = TAG.nav
HEADER = TAG.header
FIGURE = TAG.figure


def get_signature():
    """
    if 'user_signature' specified in the query_parms, retrieve it and use that signature.  else,
    create a new one

    :return: user signature uuid
    """
    return request.query.get('user_signature', uuid.uuid4())


def get_filter_value(user_signature, filter_name, default_value=None):
    filter_value = default_value
    if user_signature and user_signature in request.cookies:
        cookie = json.loads(request.get_cookie(user_signature,
                                               default={},
                                               secret=settings.SESSION_SECRET_KEY))
        filter_value = cookie.get(filter_name, default_value)

    return filter_value


def set_storage_values(user_signature, values_dict):
    #  default the timeout to 1 hour - override by setting SIMPLE_TABLE_SIGNATURE_MAX_AGE in settings
    try:
        max_age = settings.SIMPLE_TABLE_SIGNATURE_MAX_AGE
    except:
        max_age = 3600
    response.set_cookie(str(user_signature),
                        json.dumps(values_dict),
                        secret=settings.SESSION_SECRET_KEY,
                        max_age=max_age)


class SimpleTable:
    def __init__(self,
                 queries,
                 search_form=None,
                 filter_values=None,
                 fields=None,
                 show_id=False,
                 orderby=None,
                 left=None,
                 headings=None,
                 per_page=settings.SIMPLE_TABLE_ROWS_PER_PAGE,
                 create=False,
                 details=False,
                 editable=False,
                 deletable=False,
                 include_action_button_text=False,
                 search_button=None,
                 requires=None,
                 user_signature=None):
        """
        SimpleTable is a searchable/sortable/pageable grid

        :param queries: list of queries used to filter the data
        :param search_form: py4web FORM to be included as the search form
        :param storage_values: values to save between requests
        :param fields: list of fields to display on the list page, if blank, glean tablename from first query
        :              and use all fields of that table
        :param show_id: show the record id field on list page - default = False
        :param orderby: pydal orderby field or list of fields
        :param left: if joining other tables, specify the pydal left expression here
        :param headings: list of headings to be used for list page - if not provided use the field label
        :param per_page: # of rows to display per page - gets default from app settings
        :param create: URL to redirect to for creating records - set to False to not display the button
        :param editable: URL to redirect to for editing records - set to False to not display the button
        :param deletable: URL to redirect to for deleting records - set to False to not display the button
        :param include_action_button_text: include text on action buttons - default = False
        :param search_button: text to appear on the search/filter button
        :param requires: dict of fields and their 'requires' parm for building edit pages - dict key should be
                         tablename.fieldname
        :param user_signature: id of the cookie containing saved values
        """
        self.query_parms = request.params
        self.endpoint = request.route.call.__name__

        self.search_form = search_form

        self.query = reduce(lambda a, b: (a & b), queries)

        self.fields = []
        if fields:
            if isinstance(fields, list):
                self.fields = fields
            else:
                self.fields = [fields]
        else:
            q = self.query
            while q.second != 0:
                q = q.first

            self.fields = [db[q.first.table][x] for x in q.first.table.fields()]

        self.show_id = show_id
        self.hidden_fields = [field for field in self.fields if not field.readable]
        self.left = left

        if 'action' in request.url_args:
            self.action = request.url_args['action']
            self.tablename = request.url_args['tablename']
            self.record_id = request.url_args['record_id']
            self.requires = requires
            self.readonly_fields = [field for field in self.fields if not field.writable]
            if request.url_args['action'] in ['new', 'details', 'edit']:
                readonly = True if request.url_args['action'] == 'details' else False
                for field in self.readonly_fields:
                    db[self.tablename][field.name].writable = False

                for field in self.hidden_fields:
                    db[self.tablename][field.name].readable = False
                    db[self.tablename][field.name].writable = False

                if requires:
                    for field in self.requires:
                        tablename, fieldname = field.split('.')
                        db[tablename][fieldname].requires = self.requires[field]

                if not self.show_id:
                    #  if not show id, find the 'id' field and set readable/writable to False
                    for field in db[self.tablename]:
                        if field.type == 'id':
                            db[self.tablename][field.name].readable = False
                            db[self.tablename][field.name].writable = False

                self.form = Form(db[self.tablename], record=self.record_id, readonly=readonly,
                                 formstyle=FormStyleSimpleTable)
                if self.form.accepted:
                    page = request.query.get('page', 1)
                    redirect(URL(self.endpoint, vars=dict(user_signature=request.query.get('user_signature'),
                                                          page=page)))

            if request.url_args['action'] == 'delete':
                db(db[self.tablename].id == self.record_id).delete()
                redirect(URL(self.endpoint, vars=dict(user_signature=request.query.get('user_signature'))))

        else:
            self.action = 'select'
            self.orderby = orderby

            self.tablename = None
            for field in self.fields:
                self.tablename = field.table
                break

            self.headings = []
            if headings:
                if isinstance(headings, list):
                    self.headings = headings
                else:
                    self.headings = [headings]

            self.per_page = per_page
            sig_page_number = json.loads(request.query.get(user_signature, '{}')).get('page', 1)
            current_page_number = request.query.get('page', sig_page_number)
            self.current_page_number = current_page_number if isinstance(current_page_number, int) \
                else int(current_page_number)

            self.create = create
            self.details = details
            self.editable = editable
            self.deletable = deletable

            self.search_button = search_button

            parms = dict()
            #  try getting sort order from the request
            sort_order = request.query.get('sort')
            if not sort_order:
                #  see if there is a stored orderby
                sort_order = get_storage_value(user_signature, 'orderby')
                if not sort_order:
                    #  use sort order passed in
                    sort_order = self.orderby

            orderby = self.decode_orderby(sort_order)
            parms['orderby'] = orderby['orderby_expression']
            storage_values['orderby'] = orderby['orderby_string']
            if orderby['orderby_string'] != get_storage_value(user_signature, 'orderby'):
                #  user clicked on a header to change sort order - reset page to 1
                self.current_page_number = 1

            if self.left:
                parms['left'] = self.left

            self.total_number_of_rows = db(self.query).count()

            #  if at a high page number and then filter causes less records to be displayed, reset to page 1
            if (self.current_page_number - 1) * per_page > self.total_number_of_rows:
                self.current_page_number = 1

            if self.total_number_of_rows > self.per_page:
                self.page_start = self.per_page * (self.current_page_number - 1)
                self.page_end = self.page_start + self.per_page
                parms['limitby'] = (self.page_start, self.page_end)
            else:
                self.page_start = 0
                if self.total_number_of_rows > 1:
                    self.page_start = 1
                self.page_end = self.total_number_of_rows

            if self.fields:
                self.rows = db(self.query).select(*self.fields, **parms)
            else:
                self.rows = db(self.query).select(**parms)

            self.number_of_pages = self.total_number_of_rows // self.per_page
            if self.total_number_of_rows % self.per_page > 0:
                self.number_of_pages += 1

            self.include_action_button_text = include_action_button_text
            self.user_signature = user_signature
            storage_values['page'] = self.current_page_number

            set_storage_values(user_signature, storage_values)
            self.storage_values = storage_values

    def iter_pages(self, left_edge=1, right_edge=1, left_current=1, right_current=2):
        """
        generator used to determine which page numbers should be shown on the SimpleTable pager

        :param left_edge: # of pages to show on the left
        :param right_edge: # of pages to show on the right
        :param left_current: # of pages to add to the left of current page
        :param right_current: # of fpages to add to the right of current page
        """
        current = 1
        last_blank = False
        while current <= self.number_of_pages:
            #  current page
            if current == self.current_page_number:
                last_blank = False
                yield current

            #  left edge
            elif current <= left_edge:
                last_blank = False
                yield current

            #  right edge
            elif current > self.number_of_pages - right_edge:
                last_blank = False
                yield current

            #  left of current
            elif self.current_page_number - left_current <= current < self.current_page_number:
                last_blank = False
                yield current

            #  right of current
            elif self.current_page_number < current <= self.current_page_number + right_current:
                last_blank = False
                yield current
            else:
                if not last_blank:
                    yield None
                    last_blank = True

            current += 1

    def __repr__(self):
        """
        build the query table

        :return: html representation of the table
        """
        if self.action == 'select':
            _html = DIV(_class='field')
            _top_div = DIV(_style='padding-bottom: 1rem;')
            if self.create and self.create != '':
                #  build the New button
                if isinstance(self.create, str):
                    create_url = self.create
                else:
                    create_url = create_url = URL(self.endpoint) + '/new/%s/0' % self.tablename
                _a = A('', _href=create_url,
                       _class='button')
                _span = SPAN(_class='icon is-small')
                _span.append(I(_class='fas fa-plus'))
                _a.append(_span)
                _a.append(SPAN('New'))
                _top_div.append(_a)

            #  build the search form if provided
            if self.search_form:
                _sf = DIV(_class='is-pulled-right', _style='padding-bottom: 1rem;')
                _sf.append(self.search_form.custom['begin'])
                _tr = TR()
                for field in self.search_form.table:
                    _td = TD(_style='padding-right: .5rem;')
                    if field.type == 'boolean':
                        _td.append(self.search_form.custom['widgets'][field.name])
                        _td.append(field.label)
                    else:
                        _td.append(self.search_form.custom['widgets'][field.name])
                    if field.name in self.search_form.custom['errors'] and self.search_form.custom['errors'][
                        field.name]:
                        _td.append(DIV(self.search_form.custom['errors'][field.name], _style="color:#ff0000"))
                    _tr.append(_td)
                if self.search_button:
                    _tr.append(TD(INPUT(_class='button', _type='submit', _value=self.search_button)))
                else:
                    _tr.append(TD(self.search_form.custom['submit']))
                _sf.append(TABLE(_tr))
                for hidden_widget in self.search_form.custom['hidden_widgets'].keys():
                    _sf.append(self.search_form.custom['hidden_widgets'][hidden_widget])

                _sf.append(self.search_form.custom['end'])
                _top_div.append(_sf)

            _html.append(_top_div)

            _table = TABLE(_class='table is-bordered is-striped is-hoverable is-fullwidth')

            # build the header
            _thead = THEAD()
            for index, field in enumerate(self.fields):
                if field.name not in [x.name for x in self.hidden_fields] and (
                        field.name != 'id' or (field.name == 'id' and self.show_id)):
                    try:
                        heading = self.headings[index]
                    except:
                        heading = field.label
                    #  add the sort order query parm
                    sort_query_parms = dict(self.query_parms)
                    sort_query_parms['sort'] = index
                    current_sort_dir = 'asc'

                    if '%s.%s' % (field.tablename, field.name) in self.storage_values['orderby']:
                        sort_query_parms['sort'] = -index
                        _h = A(heading.replace('_', ' ').upper(),
                               _href=URL(self.endpoint, vars=sort_query_parms))
                        _h.append(SPAN(I(_class='fas fa-sort-up'), _class='is-pulled-right'))
                    elif '~%s.%s' % (field.tablename, field.name) in self.storage_values['orderby']:
                        _h = A(heading.replace('_', ' ').upper(),
                               _href=URL(self.endpoint, vars=sort_query_parms))
                        _h.append(SPAN(I(_class='fas fa-sort-down'), _class='is-pulled-right'))
                    else:
                        _h = A(heading.replace('_', ' ').upper(),
                               _href=URL(self.endpoint, vars=sort_query_parms))

                    if 'sort_dir' in sort_query_parms:
                        current_sort_dir = sort_query_parms['sort_dir']
                        del sort_query_parms['sort_dir']
                    if index == int(request.query.get('sort', 0)) and current_sort_dir == 'asc':
                        sort_query_parms['sort_dir'] = 'desc'

                    _th = TH()
                    _th.append(_h)

                    _thead.append(_th)

            if self.editable or self.deletable:
                _thead.append(TH('ACTIONS', _style='text-align: center; width: 1px; white-space: nowrap;'))

            _table.append(_thead)

            #  build the rows
            _html.append(XML('<script src="https://momentjs.com/downloads/moment.js"></script>'))

            for row in self.rows:
                _tr = TR()
                for field in self.fields:
                    if field.name not in [x.name for x in self.hidden_fields] and \
                            (field.name != 'id' or (field.name == 'id' and self.show_id)):
                        if field.type == 'date':
                            _tr.append(
                                TD(XML("<script>\ndocument.write("
                                       "moment(\"%s\").format('L'));\n</script>" % row[field.name]) \
                                       if row and field and field.name in row and row[field.name] else '',
                                   _class='has-text-centered'))
                        elif field.type == 'boolean':
                            #  True/False - only show on True, blank for False
                            if row and field and field.name in row and row[field.name]:
                                _td = TD(_class='has-text-centered')
                                _span = SPAN(_class='icon is-small')
                                _span.append(I(_class='fas fa-check-circle'))
                                _td.append(_span)
                                _tr.append(_td)
                            else:
                                _tr.append(TD(XML('&nbsp;')))
                        else:
                            _tr.append(
                                TD(row[field.name] if row and field and field.name in row and row[field.name] else ''))

                _td = None
                if (self.details and self.details != '') or \
                        (self.editable and self.editable != '') or \
                        (self.deletable and self.deletable != ''):
                    _td = TD(_class='center', _style='text-align: center; white-space: nowrap;')
                    if self.details and self.details != '':
                        if isinstance(self.details, str):
                            details_url = self.details
                        else:
                            details_url = URL(self.endpoint) + '/details/%s' % self.tablename
                        if self.include_action_button_text:
                            _a = A(_href=details_url + '/%s?user_signature=%s&page=%s' % (row.id,
                                                                                       self.user_signature,
                                                                                       self.current_page_number),
                                   _class='button is-small')
                            _span = SPAN(_class='icon is-small')
                            _span.append(I(_class='fas fa-id-card'))
                            _a.append(_span)
                            _a.append(SPAN('Details'))
                        else:
                            _a = A(I(_class='fas fa-id-card'),
                                   _href=details_url + '/%s?user_signature=%s&page=%s' % (row.id,
                                                                                          self.user_signature,
                                                                                          self.current_page_number),
                                   _class='button is-small')
                        _td.append(_a)
                    if self.editable and self.editable != '':
                        if isinstance(self.editable, str):
                            edit_url = self.editable
                        else:
                            edit_url = URL(self.endpoint) + '/edit/%s' % self.tablename
                        if self.include_action_button_text:
                            _a = A(_href=edit_url + '/%s?user_signature=%s&page=%s' % (row.id,
                                                                                       self.user_signature,
                                                                                       self.current_page_number),
                                   _class='button is-small')
                            _span = SPAN(_class='icon is-small')
                            _span.append(I(_class='fas fa-edit'))
                            _a.append(_span)
                            _a.append(SPAN('Edit'))
                        else:
                            _a = A(I(_class='fas fa-edit'),
                                   _href=edit_url + '/%s?user_signature=%s&page=%s' % (row.id,
                                                                                       self.user_signature,
                                                                                       self.current_page_number),
                                   _class='button is-small')
                        _td.append(_a)
                    if self.deletable and self.deletable != '':
                        if isinstance(self.deletable, str):
                            delete_url = self.deletable
                        else:
                            delete_url = URL(self.endpoint) + '/delete/%s' % self.tablename
                        if self.include_action_button_text:
                            _a = A(_href=delete_url + '/%s?user_signature=%s' % (row.id, self.user_signature),
                                   _class='confirmation button is-small',
                                   _message='You have asked to delete row %s' % str(row.id))
                            _span = SPAN(_class='icon is-small action-button-image')
                            _span.append(I(_class='fas fa-trash'))
                            _a.append(_span)
                            _a.append(SPAN('Delete'))
                        else:
                            _a = A(I(_class='fas fa-trash'),
                                   _href=delete_url + '/%s?user_signature=%s' % (row.id, self.user_signature),
                                   _class='confirmation button is-small',
                                   _message='You have asked to delete row %s' % str(row.id))
                        _td.append(_a)
                    _tr.append(_td)
                _table.append(_tr)

            _html.append(_table)

            _row_count = DIV(_class='is-pulled-left')
            _row_count.append(
                P('Displaying rows %s thru %s of %s' % (self.page_start + 1 if self.number_of_pages > 1 else 1,
                                                        self.page_end if self.page_end < self.total_number_of_rows else
                                                        self.total_number_of_rows,
                                                        self.total_number_of_rows)))
            _html.append(_row_count)

            #  build the pager
            _pager = DIV(_class='is-pulled-right')
            for page_number in self.iter_pages():
                if page_number:
                    pager_query_parms = dict(self.query_parms)
                    pager_query_parms['page'] = page_number
                    pager_query_parms['user_signature'] = self.user_signature
                    if self.current_page_number == page_number:
                        _pager.append(A(page_number, _class='button is-primary is-small',
                                        _href=URL(self.endpoint, vars=pager_query_parms)))
                    else:
                        _pager.append(A(page_number, _class='button is-small',
                                        _href=URL(self.endpoint, vars=pager_query_parms)))
                else:
                    _pager.append('...')

            if self.number_of_pages > 1:
                _html.append(_pager)

            if self.deletable:
                _html.append((XML("""
                    <script type="text/javascript">
                    $('.confirmation').on('click', function () {
                        return confirm($(this).attr('message') +' - Are you sure?');
                    });
                    </script>
                """)))
        elif self.action in ['new', 'details', 'edit']:
            _html = DIV(_class='card')
            _card_content = DIV(_class='card-content')
            _media = DIV(_class='media')
            _media_left = DIV(_class='media-left')
            _figure = FIGURE(_class='image is-48x48')
            if self.action in ['new', 'edit']:
                icon = 'fa-edit'
                if self.action == 'new':
                    icon = 'fa-plus'
                ttl = '%s %s' % (self.action, self.tablename.replace('_', ' '))
            else:
                icon = 'fa-id-card'
                ttl = '%s Details' % self.tablename
            _figure.append(I(_class="fas %s fa-2x" % icon))
            _media_left.append(_figure)
            _media.append(_media_left)
            _title = P(ttl.title(), _class='title is-4')
            _media_content = DIV(_class='media-content')
            _media_content.append(_title)
            _media.append(_media_content)
            _card_content.append(_media)

            _form_content = DIV(_class='content')
            _form_content.append(XML(self.form))
            _card_content.append(_form_content)
            _html.append(_card_content)

        return str(_html)


def FormStyleSimpleTable(table, vars, errors, readonly, deletable):
    classes = {
        "outer": "field",
        "inner": "control",
        "label": "label is-uppercase",
        "info": "help",
        "error": "help is-danger py4web-validation-error",
        "submit": "button is-success",
        "input": "input",
        "input[type=text]": "input",
        "input[type=date]": "input",
        "input[type=time]": "input",
        "input[type=datetime-local]": "input",
        "input[type=radio]": "radio",
        "input[type=checkbox]": "checkbox",
        "input[type=submit]": "button",
        "input[type=password]": "password",
        "input[type=file]": "file",
        "select": "control select",
        "textarea": "textarea",
    }
    return FormStyleDefault(table, vars, errors, readonly, deletable, classes)
