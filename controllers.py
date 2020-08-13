import json
import pprint
from functools import reduce

from py4web import action, request, redirect, URL, Field
from py4web.utils.form import Form, FormStyleBulma
from py4web.utils.grid import Grid
from .common import db, session, auth, unauthenticated
from .libs.datatables import DataTablesField, DataTablesRequest, DataTablesResponse
from .libs.simple_table import SimpleTable, get_signature, get_storage_value


@action('index', method=['POST', 'GET'])
@action('/', method=['POST', 'GET'])
@action.uses(session, db, auth, 'libs/simple_table.html')
def index():
    url_path = 'index'

    fields = [db.zip_code.id,
              db.zip_code.zip_code,
              db.zip_code.zip_type,
              db.zip_code.state,
              db.zip_code.county,
              db.zip_code.primary_city]

    #  check session to see if we've saved a default value
    user_signature = get_signature()
    search_filter = get_storage_value(user_signature, 'search_filter', None)

    #  build the search form
    search_form = Form([Field('search', length=50, default=search_filter)],
                       keep_values=True, formstyle=FormStyleBulma)

    if search_form.accepted:
        search_filter = search_form.vars['search']

    queries = [(db.zip_code.id > 0)]
    if search_filter:
        queries.append((db.zip_code.zip_code.contains(search_filter)) |
                       (db.zip_code.zip_type.contains(search_filter)) |
                       (db.zip_code.primary_city.contains(search_filter)) |
                       (db.zip_code.county.contains(search_filter)) |
                       (db.zip_code.state.contains(search_filter)))

    orderby = [~db.zip_code.state, db.zip_code.county, db.zip_code.primary_city]

    grid = SimpleTable(url_path,
                       queries,
                       fields=fields,
                       search_form=search_form,
                       storage_values=dict(search_filter=search_filter),
                       orderby=orderby,
                       create_url=URL('zip_code/0', vars=dict(user_signature=user_signature)),
                       edit_url=URL('zip_code'),
                       delete_url=URL('zip_code/delete'),
                       user_signature=user_signature)

    return dict(grid=grid)


@action('zip_code/<zip_code_id>', method=['GET', 'POST'])
@action.uses(session, db, auth, 'libs/edit.html')
def zip_code(zip_code_id):
    form = Form(db.zip_code, record=zip_code_id, formstyle=FormStyleBulma)

    print(request.query.__dict__)

    if form.accepted:
        page = request.query.get('page', 1)
        redirect(URL('index', vars=dict(user_signature=request.query.get('user_signature'),
                                        page=page)))

    return dict(form=form)


@action('zip_code/delete/<zip_code_id>', method=['GET', 'POST'])
@action.uses(session, db, auth, 'simple_table.html')
def zip_code_delete(zip_code_id):
    result = db(db.zip_code.id == zip_code_id).delete()
    redirect(URL('index', vars=dict(user_signature=request.query.get('user_signature'))))


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
                            edit_url=URL('zip_code_dt/record_id'),
                            delete_url=URL('zip_code_dt/delete/record_id'),
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


@action('zip_code_dt/<zip_code_id>', method=['GET', 'POST'])
@action.uses(session, db, auth, 'libs/edit.html')
def zip_code_dt(zip_code_id):
    form = Form(db.zip_code, record=zip_code_id, formstyle=FormStyleBulma)

    if form.accepted:
        redirect(URL('datatables'))

    return dict(form=form)


@action('zip_code_dt/delete/<zip_code_id>', method=['GET', 'POST'])
@action.uses(session, db, auth, 'simple_table.html')
def zip_code_dt_delete(zip_code_id):
    result = db(db.zip_code.id == zip_code_id).delete()
    redirect(URL('datatables'))
