from functools import reduce

from yatl.helpers import DIV, TABLE, TBODY, TR, TD, TH, A, SPAN, I, THEAD, P, TAG, INPUT, SCRIPT, XML
from pydal.objects import FieldVirtual
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


def get_storage_value(user_signature, filter_name, default_value=None):
    storage_value = default_value
    if user_signature and user_signature in request.cookies:
        cookie = json.loads(request.get_cookie(user_signature,
                                               default={},
                                               secret=settings.SESSION_SECRET_KEY))
        storage_value = cookie.get(filter_name, default_value)

    return storage_value


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
                 storage_values=None,
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
            self.use_tablename = False
            for field in self.fields:
                if not isinstance(field, FieldVirtual):
                    if not self.tablename:
                        self.tablename = field.table
                    if field.table != self.tablename:
                        self.use_tablename = True  # tablename is included in 'row' - need it to retrieve fields

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

            if self.left:
                self.total_number_of_rows = len(db(self.query).select(db[self.tablename].id, **parms))
            else:
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

    def decode_orderby(self, sort_order):
        """
        sort_order can be an int, string, list of strings, pydal fields or list of pydal fields

        need to determine which it is and then return a dict containing the string representation of the
        orderby and the pydal expression to be used in the query

        :param sort_order:
        :return: dict(orderby_string=<order by string>, orderby_expression=<pydal orderby expression>)
        """
        orderby_expression = None
        orderby_string = None
        if sort_order:
            #  can be an int or a PyDAL field
            try:
                index = int(sort_order)
                #  if we get here, this is a sort request from the table
                #  if it is in the saved order by then reverse the direction
                if (request.query.get('sort_dir') and request.query.get('sort_dir') == 'desc') or index < 0:
                    orderby_expression = [~self.fields[abs(index)]]
                else:
                    orderby_expression = [self.fields[index]]
            except:
                #  this could be:
                #  a string
                #  a list of strings
                #  a list of dal fields or a single pydal field, treat the same
                if isinstance(sort_order, str):
                    #  a string
                    tablename, fieldname = sort_order.split('.')
                    orderby_expression = [db[tablename][fieldname]]
                else:
                    sort_type = 'dal_field'
                    for x in sort_order:
                        if isinstance(x, str):
                            sort_type = 'str'

                    if sort_type == 'dal_field':
                        #  a list of dal fields
                        orderby_expression = sort_order
                    else:
                        #  a list of strings
                        orderby_expression = []
                        for x in sort_order:
                            tablename, fieldname = x.replace('~', '').split('.')
                            if '~' in x:
                                orderby_expression.append(~db[tablename][fieldname])
                            else:
                                orderby_expression.append(db[tablename][fieldname])
        else:
            for field in self.fields:
                if field not in self.hidden_fields and (field.name != 'id' or field.name == 'id' and self.show_id):
                    orderby_expression = field

        if orderby_expression:
            try:
                orderby_string = []
                for x in orderby_expression:
                    if ' DESC' in str(x):
                        orderby_string.append('~' + str(x).replace('"', '').replace(' DESC', '').replace('`', ''))
                    else:
                        orderby_string.append('%s.%s' % (x.tablename, x.name))
            except:
                orderby_string = orderby_expression

        return dict(orderby_string=orderby_string, orderby_expression=orderby_expression)

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

    def render_action_button(self, url, button_text, icon, size='small'):
        if self.include_action_button_text:
            _a = A(_href=url, _class='button is-%s' % size, _title=button_text)
            _span = SPAN(_class='icon is-%s' % size)
            _span.append(I(_class='fas %s' % icon))
            _a.append(_span)
            _a.append(SPAN(button_text))
        else:
            _a = A(I(_class='fas %s' % icon),
                   _href=url,
                   _class='button is-%s' % size,
                   _title=button_text)

        return _a

    def render_search_form(self):
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

        return _sf

    def render_table_header(self):
        _thead = THEAD()
        for index, field in enumerate(self.fields):
            if field.name not in [x.name for x in self.hidden_fields] and (
                    field.name != 'id' or (field.name == 'id' and self.show_id)):
                try:
                    heading = self.headings[index]
                except:
                    if field.table == self.tablename:
                        heading = field.label
                    else:
                        heading = str(field.table)
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

        return _thead

    def render_field(self, row, field):
        """
        Render a field

        if only 1 table in the query, the no table name needed when getting the row value - however, if there
        are multiple tables in the query (self.use_tablename == True) then we need to use the tablename as well
        when accessing the value in the row object

        the row object sent in can take
        :param row:
        :param field:
        :return:
        """
        if self.use_tablename:
            field_value = row[field.tablename][field.name]
        else:
            field_value = row[field.name]
        if field.type == 'date':
            _td = TD(XML("<script>\ndocument.write("
                       "moment(\"%s\").format('L'));\n</script>" % field_value) \
                       if row and field and field_value else '',
                     _class='has-text-centered')
        elif field.type == 'boolean':
            #  True/False - only show on True, blank for False
            if row and field and field_value:
                _td = TD(_class='has-text-centered')
                _span = SPAN(_class='icon is-small')
                _span.append(I(_class='fas fa-check-circle'))
                _td.append(_span)
            else:
                _td = TD(XML('&nbsp;'))
        else:
            _td = TD(field_value if row and field and field_value else '')

        return _td

    def render_table_body(self):
        _tbody = TBODY()
        for row in self.rows:
            #  find the row id - there may be nested tables....
            if self.use_tablename:
                row_id = row[self.tablename]['id']
            else:
                row_id = row['id']

            _tr = TR()
            #  add all the fields to the row
            for field in self.fields:
                if field.name not in [x.name for x in self.hidden_fields] and \
                        (field.name != 'id' or (field.name == 'id' and self.show_id)):
                    _tr.append(self.render_field(row, field))

            _td = None

            #  add the action buttons
            if (self.details and self.details != '') or \
                    (self.editable and self.editable != '') or \
                    (self.deletable and self.deletable != ''):
                _td = TD(_class='center', _style='text-align: center; white-space: nowrap;')
                if self.details and self.details != '':
                    if isinstance(self.details, str):
                        details_url = self.details
                    else:
                        details_url = URL(self.endpoint) + '/details/%s' % self.tablename
                    details_url += '/%s?user_signature=%s&page=%s' % (row_id,
                                                                      self.user_signature,
                                                                      self.current_page_number)
                    _td.append(self.render_action_button(details_url, 'Details', 'fa-id-card'))

                if self.editable and self.editable != '':
                    if isinstance(self.editable, str):
                        edit_url = self.editable
                    else:
                        edit_url = URL(self.endpoint) + '/edit/%s' % self.tablename
                    edit_url += '/%s?user_signature=%s&page=%s' % (row_id,
                                                                   self.user_signature,
                                                                   self.current_page_number)
                    _td.append(self.render_action_button(edit_url, 'Edit', 'fa-edit'))

                if self.deletable and self.deletable != '':
                    if isinstance(self.deletable, str):
                        delete_url = self.deletable
                    else:
                        delete_url = URL(self.endpoint) + '/delete/%s' % self.tablename
                    delete_url += '/%s?user_signature=%s' % (row_id, self.user_signature)
                    _td.append(self.render_action_button(delete_url, 'Delete', 'fa-trash'))
                _tr.append(_td)
            _tbody.append(_tr)

        return _tbody

    def render_table_pager(self):
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

        return _pager

    def render_table(self):
        _html = DIV(_class='field')
        _top_div = DIV(_style='padding-bottom: 1rem;')

        #  build the New button if needed
        if self.create and self.create != '':
            if isinstance(self.create, str):
                create_url = self.create
            else:
                create_url = create_url = URL(self.endpoint) + '/new/%s/0' % self.tablename

            _top_div.append(self.render_action_button(create_url, 'New', 'fa-plus', size='normal'))

        #  build the search form if provided
        if self.search_form:
            _top_div.append(self.render_search_form())

        _html.append(_top_div)

        _table = TABLE(_class='table is-bordered is-striped is-hoverable is-fullwidth')

        # build the header
        _table.append(self.render_table_header())

        #  include moment.js to present dates in the proper locale
        _html.append(XML('<script src="https://momentjs.com/downloads/moment.js"></script>'))

        #  build the rows
        _table.append(self.render_table_body())

        #  add the table to the html
        _html.append(_table)

        #  add the row counter information
        _row_count = DIV(_class='is-pulled-left')
        _row_count.append(
            P('Displaying rows %s thru %s of %s' % (self.page_start + 1 if self.number_of_pages > 1 else 1,
                                                    self.page_end if self.page_end < self.total_number_of_rows else
                                                    self.total_number_of_rows,
                                                    self.total_number_of_rows)))
        _html.append(_row_count)

        #  build the pager
        if self.number_of_pages > 1:
            _html.append(self.render_table_pager())

        if self.deletable:
            _html.append((XML("""
                <script type="text/javascript">
                $('.confirmation').on('click', function () {
                    return confirm($(this).attr('message') +' - Are you sure?');
                });
                </script>
            """)))

        return XML(_html)

    def render(self):
        """
        build the query table

        :return: html representation of the table or the py4web Form object
        """
        if self.action == 'select':
            return self.render_table()
        elif self.action in ['new', 'details', 'edit']:
            return self.form


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
