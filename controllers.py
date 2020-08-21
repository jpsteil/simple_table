import json
import pprint
from functools import reduce

from py4web import action, request, redirect, URL, Field
from py4web.utils.form import Form, FormStyleBulma, FormStyleDefault
from py4web.utils.grid import Grid
from pydal.validators import IS_NULL_OR, IS_IN_SET
from .common import db, session, auth, unauthenticated
from .libs.datatables import DataTablesField, DataTablesRequest, DataTablesResponse
from .libs.simple_table import SimpleTable, get_signature, get_storage_value
from py4web.utils.publisher import Publisher, ALLOW_ALL_POLICY  # for ajax_grid

#  exposes services necessary to access the db.thing via ajax
publisher = Publisher(db, policy=ALLOW_ALL_POLICY)


@action('index', method=['POST', 'GET'])
@action('index/<action>/<tablename>/<record_id>', method=['POST', 'GET'])
@action('/', method=['POST', 'GET'])
@action.uses(session, db, auth, 'libs/simple_table.html')
def index(action=None, tablename=None, record_id=None):
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
                       include_action_button_text=True)

    return dict(grid=grid)


@action('grid', method=['POST', 'GET'])
@action.uses(session, db, auth, 'index.html')
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
#/////////////////////////////////////////////////////////////////////////
#EMPLOYEE
#Datatables edit facility - Based on Example 3 from https://github.com/KasperOlesen/DataTable-AltEditor
#/////////////////////////////////////////////////////////////////////////
#This returns the
@unauthenticated
@action('employee', method=['GET'])
@action.uses(session, db, auth, 'employee.html')
def employee():
    """
    display a page with a datatables.net with AltEditor on it
    The datatable will get data from employee_data, see employee.html
    :return:
    """
    return dict()

@unauthenticated
@action('employee_data', method=['GET'])
@action.uses(session, db, auth)
def employee_data():
    """
    :return:
    return data in JSON format: e.g.:
    [{"id":1, "name":"Tigerrrr Nixon", "position":"System Architect", "office":"Edinburgh", "extension":"5421", "startDate":"2011/04/25", "salary":"Tiger Nixon"},
    {"id":2, "name":"Garrett Winters", "position":"Accountant", "office":"Tokyo", "extension":"8422", "startDate":"2011/07/25", "salary":"Garrett Winters"}]

    """
    queries = [(db.employee.id > 0)]
    query = reduce(lambda a, b: (a & b), queries)

    data = [dict(id=z.id,
                 name=z.name,
                 position=z.position,
                 office=z.office,
                 extension=z.extension,
                 startDate=z.startDate,
                 salary=z.salary,
                 ) for z in db(query).select()]

    return json.dumps(data)

#EDIT
@action('employee/<employee_id>', method=['PUT', 'POST', 'GET'])
@action.uses(session, db, auth, 'employee.html')
def employee(employee_id):
    """
    This handles Ajax Put and Post requests. See lines 107 and 127 of employee.html
    Create/PUT:
    url: 'employee/0',
    type: 'PUT',

    Edit/POST:
    url: 'employee/'+rowdata.id,
    type: 'POST',
    :return:
    This function must return one compelte row of the new or edited row in JSON format for the table to update itself via Ajax.
    e.g.: {"id":10, "name":"Name modified by server", "position":"Modified position", "office":"", "extension":"", "startDate":"", "salary":""}
    """
    if request.method == 'GET':
        if int(employee_id) > 0:
            z = db(db.employee.id == int(employee_id)).select().first()
            data = dict(id=z.id,
                         name=z.name,
                         position=z.position,
                         office=z.office,
                         extension=z.extension,
                         startDate=z.startDate,
                         salary=z.salary,
                         )
            return json.dumps(data)

    if request.method == 'PUT':
        #if employee_id == 0:
        #Create new
        #Do other specific error checking here.
        newid = db.employee.insert(name=request.forms.get('name'), position=request.forms.get('position'), office=request.forms.get('office'),
                           extension=request.forms.get('extension'), startDate=request.forms.get('startdate'), salary=request.forms.get('salary'))
        z = db(db.employee.id == int(newid)).select().first()
        data = dict(id=z.id,
                     name=z.name,
                     position=z.position,
                     office=z.office,
                     extension=z.extension,
                     startDate=z.startDate,
                     salary=z.salary)
        return json.dumps(data)
        #return """[{"id": 3, "name": "Ass", "position": "ret", "office": "london", "extension": "1", "startDate": null, "salary": "100000"}]"""

    if request.method == 'POST':
        if int(employee_id) > 0:
            z = db(db.employee.id == int(employee_id)).select().first()
            z.update_record(name=request.forms.get('name'), position=request.forms.get('position'), office=request.forms.get('office'),
                               extension=request.forms.get('extension'), startDate=request.forms.get('startdate'), salary=request.forms.get('salary'))
            z = db(db.employee.id == int(employee_id)).select().first()
            data = [dict(id=z.id,
                         name=z.name,
                         position=z.position,
                         office=z.office,
                         extension=z.extension,
                         startDate=z.startDate,
                         salary=z.salary)]
            return json.dumps(data)


#/////////////////////////////////////////////////////////////////////////
#DELETE
@action('employee/delete/<employee_id>', method=['DELETE','GET', 'POST'])
@action.uses(session, db, auth, 'employee.html')
def employee_delete(employee_id):
    """
    This handles delete requests
    url: 'employee/delete/' + rowdata.id,
    type: 'DELETE',
    :return:
    Dont need to return anything
    """
    result = db(db.employee.id == employee_id).delete()
    return dict()
#/////////////////////////////////////////////////////////////////////////
