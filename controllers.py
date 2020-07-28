from py4web import action, request, abort, redirect, URL, response, Field
from py4web.utils.grid import Grid
from yatl.helpers import A
from .common import db, session, T, cache, auth, logger, authenticated
from py4web.utils.form import Form, FormStyleBulma
from .libs.simple_table import SimpleTable, get_signature, get_filter_value, set_filter_values
from .settings import SIMPLE_TABLE_ROWS_PER_PAGE


@action('index', method=['POST', 'GET'])
@action('/', method=['POST', 'GET'])
@action.uses(session, db, auth, 'libs/query_table.html')
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
    search_filter = get_filter_value(user_signature, 'search_filter', None)

    #  build the search form
    form = Form([Field('search', length=50, default=search_filter)],
                keep_values=True, formstyle=FormStyleBulma)

    if form.accepted:
        search_filter = form.vars['search']

    queries = [(db.zip_code.id > 0)]
    if search_filter:
        queries.append((db.zip_code.zip_code.contains(search_filter)) |
                       (db.zip_code.primary_city.contains(search_filter)) |
                       (db.zip_code.county.contains(search_filter)) |
                       (db.zip_code.state.contains(search_filter)))

    orderby = [db.zip_code.state, db.zip_code.county, db.zip_code.primary_city]
    grid = SimpleTable(url_path,
                       queries,
                       fields=fields,
                       search_form=form,
                       filter_values=dict(search_filter=search_filter),
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

    if form.accepted:
        redirect(URL('index', vars=dict(user_signature=request.query.get('user_signature'))))

    return dict(form=form)


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

    # grid.labels = {key: key.title() for key in db.thing.fields}
    # grid.renderers['name'] = lambda name: SPAN(name, _class='name')

    return dict(form=grid.make())
