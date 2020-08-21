import json
import pprint
from functools import reduce

from py4web import action, request, redirect, URL, Field
from py4web.utils.form import Form, FormStyleBulma, FormStyleDefault
from py4web.utils.grid import Grid
from pydal.validators import IS_NULL_OR, IS_IN_SET
from .common import db, session, auth, unauthenticated
from .libs.datatables import DataTablesField, DataTablesRequest, DataTablesResponse
from .libs.simple_table import SimpleTable, get_signature, get_storage_value, ActionButton
from py4web.utils.publisher import Publisher, ALLOW_ALL_POLICY  # for ajax_grid

#  exposes services necessary to access the db.thing via ajax
publisher = Publisher(db, policy=ALLOW_ALL_POLICY)


@action('index', method=['POST', 'GET'])
@action('/', method=['POST', 'GET'])
@action.uses(session, db, auth, 'index.html')
def index():

    return dict()


@action('zip_codes', method=['POST', 'GET'])
@action('zip_codes/<action>/<tablename>/<record_id>', method=['POST', 'GET'])
@action.uses(session, db, auth, 'libs/simple_table.html')
def zip_codes(action=None, tablename=None, record_id=None):
    fields = [db.zip_code.id,
              db.zip_code.zip_code,
              db.zip_code.zip_type,
              db.zip_code.state,
              db.zip_code.county,
              db.zip_code.primary_city]

    #  check session to see if we've saved a default value
    user_signature = get_signature()
    search_state = get_storage_value(user_signature, 'search_state', None)
    search_type = get_storage_value(user_signature, 'search_type', None)
    search_filter = get_storage_value(user_signature, 'search_filter', None)

    #  build the search form
    zip_type_requires = IS_NULL_OR(IS_IN_SET([x.zip_type for x in db(db.zip_code.id > 0).select(db.zip_code.zip_type,
                                                                                                orderby=db.zip_code.zip_type,
                                                                                                distinct=True)]))
    zip_state_requires = IS_NULL_OR(IS_IN_SET([x.state for x in db(db.zip_code.id > 0).select(db.zip_code.state,
                                                                                              orderby=db.zip_code.state,
                                                                                              distinct=True)]))
    search_form = Form([Field('state', length=20, requires=zip_state_requires,
                              default=search_state,
                              _title='Filter by State'),
                        Field('zip_type', length=20, requires=zip_type_requires,
                              default=search_type,
                              _title='Select Filter by ZIP Type'),
                        Field('search', length=50, default=search_filter, _placeholder='...search text...',
                              _title='Enter search text and click on Filter')],
                       keep_values=True, formstyle=FormStyleSimpleTable, )

    if search_form.accepted:
        search_state = search_form.vars['state']
        search_type = search_form.vars['zip_type']
        search_filter = search_form.vars['search']

    queries = [(db.zip_code.id > 0)]
    if search_filter:
        queries.append((db.zip_code.zip_code.contains(search_filter)) |
                       (db.zip_code.zip_type.contains(search_filter)) |
                       (db.zip_code.primary_city.contains(search_filter)) |
                       (db.zip_code.county.contains(search_filter)) |
                       (db.zip_code.state.contains(search_filter)))
    if search_state:
        queries.append(db.zip_code.state == search_state)

    if search_type:
        queries.append(db.zip_code.zip_type == search_type)

    orderby = [~db.zip_code.state, db.zip_code.county, db.zip_code.primary_city]

    zip_type_requires = IS_IN_SET([x.zip_type for x in db(db.zip_code.id > 0).select(db.zip_code.zip_type,
                                                                                     orderby=db.zip_code.zip_type,
                                                                                     distinct=True)])
    zip_state_requires = IS_IN_SET([x.state for x in db(db.zip_code.id > 0).select(db.zip_code.state,
                                                                                   orderby=db.zip_code.state,
                                                                                   distinct=True)])
    zip_timezone_requires = IS_IN_SET([x.timezone for x in db(db.zip_code.id > 0).select(db.zip_code.timezone,
                                                                                         distinct=True)])
    requires = {'zip_code.zip_type': zip_type_requires,
                'zip_code.state': zip_state_requires,
                'zip_code.timezone': zip_timezone_requires}

    grid = SimpleTable(queries,
                       fields=fields,
                       search_form=search_form,
                       storage_values=dict(search_state=search_state,
                                           search_type=search_type,
                                           search_filter=search_filter),
                       orderby=orderby,
                       create=True,
                       details=True,
                       editable=True,
                       deletable=True,
                       search_button='Filter',
                       user_signature=user_signature,
                       requires=requires,
                       pre_action_buttons=[ActionButton(URL('copy'), 'Copy',
                                                        icon='fa-copy',
                                                        append_id=True,
                                                        append_signature=True,
                                                        append_page=True),
                                           ActionButton(URL('to_excel'), 'Export',
                                                        icon='fa-file-excel',
                                                        append_id=True,
                                                        append_signature=True,
                                                        append_page=True)])

    return dict(grid=grid)


@action('grid', method=['POST', 'GET'])
@action.uses(session, db, auth, 'grid.html')
def grid():
    fields = ['id',
              'zip_code',
              'zip_type',
              'state',
              'county',
              'primary_city']

    grid = Grid(db.zip_code,
                fields=fields,
                create=True,
                editable=True,
                deletable=True,
                limit=14)

    grid.labels = {x: x.replace('_', ' ').upper() for x in fields}

    return dict(form=grid.make())


@unauthenticated
@action('datatables', method=['GET', 'POST'])
@action.uses(session, db, auth, 'datatables.html')
def datatables():
    """
    display a page with a datatables.net grid on it

    :return:
    """
    dt = DataTablesResponse(fields=[DataTablesField(name='DT_RowId', visible=False),
                                    DataTablesField(name='zip_code'),
                                    DataTablesField(name='zip_type'),
                                    DataTablesField(name='state'),
                                    DataTablesField(name='county'),
                                    DataTablesField(name='primary_city')],
                            data_url=URL('datatables_data'),
                            create_url=URL('zip_code/0'),
                            edit_url=URL('zip_code/record_id'),
                            delete_url=URL('zip_code/delete/record_id'),
                            sort_sequence=[[1, 'asc']])
    dt.script()
    return dict(dt=dt)


@unauthenticated
@action('datatables_data', method=['GET', 'POST'])
@action.uses(session, db, auth)
def datatables_data():
    """
    datatables.net makes an ajax call to this method to get the data

    :return:
    """
    dtr = DataTablesRequest(dict(request.query.decode()))
    dtr.order(db, 'zip_code')

    queries = [(db.zip_code.id > 0)]
    if dtr.search_value and dtr.search_value != '':
        queries.append((db.zip_code.primary_city.contains(dtr.search_value)) |
                       (db.zip_code.zip_code.contains(dtr.search_value)) |
                       (db.zip_code.zip_type.contains(dtr.search_value)) |
                       (db.zip_code.state.contains(dtr.search_value)) |
                       (db.zip_code.county.contains(dtr.search_value)))

    query = reduce(lambda a, b: (a & b), queries)
    record_count = db(db.zip_code.id > 0).count()
    filtered_count = db(query).count()

    data = [dict(DT_RowId=z.id,
                 zip_code=z.zip_code,
                 zip_type=z.zip_type,
                 state=z.state,
                 county=z.county,
                 primary_city=z.primary_city) for z in db(query).select(orderby=dtr.dal_orderby,
                                                                        limitby=[dtr.start, dtr.start + dtr.length])]

    return json.dumps(dict(data=data, recordsTotal=record_count, recordsFiltered=filtered_count))


@action('zip_code/<zip_code_id>', method=['GET', 'POST'])
@action.uses(session, db, auth, 'libs/edit.html')
def zip_code(zip_code_id):
    db.zip_code.id.readable = False
    db.zip_code.id.writable = False

    db.zip_code.zip_type.requires = IS_IN_SET(
        [x.zip_type for x in db(db.zip_code.id > 0).select(db.zip_code.zip_type, distinct=True)])
    db.zip_code.state.requires = IS_IN_SET(
        [x.state for x in db(db.zip_code.id > 0).select(db.zip_code.state, distinct=True)])
    db.zip_code.timezone.requires = IS_IN_SET(
        [x.timezone for x in db(db.zip_code.id > 0).select(db.zip_code.timezone, distinct=True)])

    form = Form(db.zip_code, record=zip_code_id, formstyle=FormStyleSimpleTable)

    if form.accepted:
        redirect(URL('datatables'))

    return dict(form=form, id=zip_code_id)


@action('zip_code/delete/<zip_code_id>', method=['GET', 'POST'])
@action.uses(session, db, auth, 'simple_table.html')
def zip_code_delete(zip_code_id):
    result = db(db.zip_code.id == zip_code_id).delete()
    redirect(URL('datatables'))


# exposed as /examples/ajaxgrid
@action("ajax_grid")
@action.uses("ajax_grid.html")
def ajax_grid():
    return dict(grid=publisher.grid(db.zip_code))


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


@action('companies', method=['POST', 'GET'])
@action('companies/<action>/<tablename>/<record_id>', method=['POST', 'GET'])
@action.uses(session, db, auth, 'libs/simple_table.html')
def companies(action=None, tablename=None, record_id=None):
    #  check session to see if we've saved a default value
    user_signature = get_signature()
    search_filter = get_storage_value(user_signature, 'search_filter', None)

    search_form = Form([Field('search', length=50, default=search_filter, _placeholder='...search text...',
                              _title='Enter search text and click on Filter')],
                       keep_values=True, formstyle=FormStyleSimpleTable, )

    if search_form.accepted:
        search_filter = search_form.vars['search']

    queries = [(db.company.id > 0)]
    if search_filter:
        queries.append(db.company.name.contains(search_filter))

    orderby = [db.company.name]

    grid = SimpleTable(queries,
                       search_form=search_form,
                       storage_values=dict(search_filter=search_filter),
                       orderby=orderby,
                       create=True,
                       details=True,
                       editable=True,
                       deletable=True,
                       search_button='Filter',
                       user_signature=user_signature,
                       include_action_button_text=True)

    return dict(grid=grid)


@action('departments', method=['POST', 'GET'])
@action('departments/<action>/<tablename>/<record_id>', method=['POST', 'GET'])
@action.uses(session, db, auth, 'libs/simple_table.html')
def departments(action=None, tablename=None, record_id=None):
    #  check session to see if we've saved a default value
    user_signature = get_signature()
    search_filter = get_storage_value(user_signature, 'search_filter', None)

    search_form = Form([Field('search', length=50, default=search_filter, _placeholder='...search text...',
                              _title='Enter search text and click on Filter')],
                       keep_values=True, formstyle=FormStyleSimpleTable, )

    if search_form.accepted:
        search_filter = search_form.vars['search']

    queries = [(db.department.id > 0)]
    if search_filter:
        queries.append(db.department.name.contains(search_filter))

    orderby = [db.department.name]

    grid = SimpleTable(queries,
                       search_form=search_form,
                       storage_values=dict(search_filter=search_filter),
                       orderby=orderby,
                       create=True,
                       details=True,
                       editable=True,
                       deletable=True,
                       search_button='Filter',
                       user_signature=user_signature,
                       include_action_button_text=True)

    return dict(grid=grid)


@action('employees', method=['POST', 'GET'])
@action('employees/<action>/<tablename>/<record_id>', method=['POST', 'GET'])
@action.uses(session, db, auth, 'libs/simple_table.html')
def employees(action=None, tablename=None, record_id=None):
    #  check session to see if we've saved a default value
    user_signature = get_signature()
    company_filter = get_storage_value(user_signature, 'company_filter', None)
    department_filter = get_storage_value(user_signature, 'department_filter', None)
    search_filter = get_storage_value(user_signature, 'search_filter', None)

    x = db.employee(347)

    search_form = Form([Field('company', 'reference company',
                              requires=db.employee.company.requires,
                              default=company_filter,
                              _title='Filter by Company'),
                        Field('department', 'reference department',
                              requires=db.employee.department.requires,
                              default=department_filter,
                              _title='Filter by Department'),
                        Field('search', length=50, default=search_filter, _placeholder='...search text...',
                              _title='Enter search text and click on Filter')],
                       keep_values=True, formstyle=FormStyleSimpleTable, )

    if search_form.accepted:
        company_filter = search_form.vars['company']
        department_filter = search_form.vars['department']
        search_filter = search_form.vars['search']

    queries = [(db.employee.id > 0)]
    if search_filter:
        queries.append("first_name || ' ' || last_Name LIKE '%%%s%%'" % search_filter)
    if company_filter:
        queries.append(db.company.id == company_filter)
    if department_filter:
        queries.append(db.department.id == department_filter)

    orderby = [db.employee.last_name, db.employee.first_name]

    fields = [db.employee.id,
              db.employee.first_name,
              db.employee.last_name,
              db.company.name,
              db.department.name,
              db.employee.hired,
              db.employee.supervisor,
              db.employee.active]

    grid = SimpleTable(queries,
                       search_form=search_form,
                       fields=fields,
                       left=[db.company.on(db.employee.company==db.company.id),
                             db.department.on(db.employee.department==db.department.id)],
                       storage_values=dict(company_filter=company_filter,
                                           department_filter=department_filter,
                                           search_filter=search_filter),
                       orderby=orderby,
                       create=True,
                       details=True,
                       editable=True,
                       deletable=True,
                       search_button='Filter',
                       user_signature=user_signature,
                       include_action_button_text=True)

    return dict(grid=grid)
