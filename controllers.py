import json
from functools import reduce
from yatl.helpers import SPAN, I, XML

from py4web import action, request, redirect, URL, Field
from py4web.utils.form import Form, FormStyleBulma, FormStyleDefault
from pydal.validators import IS_NULL_OR, IS_IN_SET
from .common import db, session, auth, unauthenticated, GRID_DEFAULTS
from .libs.datatables import DataTablesField, DataTablesRequest, DataTablesResponse
from .libs.grid_helpers import GridSearch, GridSearchQuery
from py4web.utils.grid import Grid


@action("index", method=["POST", "GET"])
@action.uses(
    "index.html",
    session,
    db,
    auth,
)
def index():
    return dict()


@action("zip_codes", method=["POST", "GET"])
@action("zip_codes/<path:path>", method=["POST", "GET"])
@action.uses(
    "grid.html",
    session,
    db,
    auth,
)
def zip_codes(path=None):
    fields = [
        db.zip_code.id,
        db.zip_code.zip_code,
        db.zip_code.zip_type,
        db.zip_code.state,
        db.zip_code.county,
        db.zip_code.primary_city,
    ]

    #  build the search form
    zip_type_requires = IS_NULL_OR(
        IS_IN_SET(
            [
                x.zip_type
                for x in db(db.zip_code.id > 0).select(
                    db.zip_code.zip_type, orderby=db.zip_code.zip_type, distinct=True
                )
            ]
        )
    )
    zip_state_requires = IS_NULL_OR(
        IS_IN_SET(
            [
                x.state
                for x in db(db.zip_code.id > 0).select(
                    db.zip_code.state, orderby=db.zip_code.state, distinct=True
                )
            ]
        )
    )
    queries = [(db.zip_code.id > 0)]

    orderby = [~db.zip_code.state, db.zip_code.county, db.zip_code.primary_city]

    search_queries = [
        GridSearchQuery(
            "Search by State", lambda val: db.zip_code.state == val, zip_state_requires
        ),
        GridSearchQuery(
            "Search by Type", lambda val: db.zip_code.zip_type == val, zip_type_requires
        ),
        GridSearchQuery(
            "Search by Name",
            lambda val: db.zip_code.zip_code.contains(val)
            | db.zip_code.zip_type.contains(val)
            | db.zip_code.primary_city.contains(val)
            | db.zip_code.county.contains(val)
            | db.zip_code.state.contains(val),
        ),
    ]

    search = GridSearch(search_queries, queries)

    zip_type_requires = IS_IN_SET(
        [
            x.zip_type
            for x in db(db.zip_code.id > 0).select(
                db.zip_code.zip_type, orderby=db.zip_code.zip_type, distinct=True
            )
        ]
    )
    zip_state_requires = IS_IN_SET(
        [
            x.state
            for x in db(db.zip_code.id > 0).select(
                db.zip_code.state, orderby=db.zip_code.state, distinct=True
            )
        ]
    )
    zip_timezone_requires = IS_IN_SET(
        [
            x.timezone
            for x in db(db.zip_code.id > 0).select(db.zip_code.timezone, distinct=True)
        ]
    )

    grid = Grid(
        path,
        search.query,
        fields=fields,
        search_form=search.search_form,
        orderby=orderby,
        create=True,
        details=True,
        editable=True,
        deletable=True,
        **GRID_DEFAULTS
    )

    return dict(grid=grid)


@unauthenticated
@action("datatables", method=["GET", "POST"])
@action.uses(
    "datatables.html",
    session,
    db,
    auth,
)
def datatables():
    """
    display a page with a datatables.net grid on it

    :return:
    """
    dt = DataTablesResponse(
        fields=[
            DataTablesField(name="DT_RowId", visible=False),
            DataTablesField(name="zip_code"),
            DataTablesField(name="zip_type"),
            DataTablesField(name="state"),
            DataTablesField(name="county"),
            DataTablesField(name="primary_city"),
        ],
        data_url=URL("datatables_data"),
        create_url=URL("zip_code/0"),
        edit_url=URL("zip_code/record_id"),
        delete_url=URL("zip_code/delete/record_id"),
        sort_sequence=[[1, "asc"]],
    )
    dt.script()
    return dict(dt=dt)


@action("datatables_data", method=["GET", "POST"])
@action.uses(session, db, auth)
def datatables_data():
    """
    datatables.net makes an ajax call to this method to get the data

    :return:
    """
    dtr = DataTablesRequest(dict(request.query.decode()))
    dtr.order(db, "zip_code")

    queries = [(db.zip_code.id > 0)]
    if dtr.search_value and dtr.search_value != "":
        queries.append(
            (db.zip_code.primary_city.contains(dtr.search_value))
            | (db.zip_code.zip_code.contains(dtr.search_value))
            | (db.zip_code.zip_type.contains(dtr.search_value))
            | (db.zip_code.state.contains(dtr.search_value))
            | (db.zip_code.county.contains(dtr.search_value))
        )

    query = reduce(lambda a, b: (a & b), queries)
    record_count = db(db.zip_code.id > 0).count()
    filtered_count = db(query).count()

    data = [
        dict(
            DT_RowId=z.id,
            zip_code=z.zip_code,
            zip_type=z.zip_type,
            state=z.state,
            county=z.county,
            primary_city=z.primary_city,
        )
        for z in db(query).select(
            orderby=dtr.dal_orderby, limitby=[dtr.start, dtr.start + dtr.length]
        )
    ]

    return json.dumps(
        dict(data=data, recordsTotal=record_count, recordsFiltered=filtered_count)
    )


@action("zip_code/<zip_code_id>", method=["GET", "POST"])
@action.uses(
    "edit.html",
    session,
    db,
    auth,
)
def zip_code(zip_code_id):
    db.zip_code.id.readable = False
    db.zip_code.id.writable = False

    db.zip_code.zip_type.requires = IS_IN_SET(
        [
            x.zip_type
            for x in db(db.zip_code.id > 0).select(db.zip_code.zip_type, distinct=True)
        ]
    )
    db.zip_code.state.requires = IS_IN_SET(
        [
            x.state
            for x in db(db.zip_code.id > 0).select(db.zip_code.state, distinct=True)
        ]
    )
    db.zip_code.timezone.requires = IS_IN_SET(
        [
            x.timezone
            for x in db(db.zip_code.id > 0).select(db.zip_code.timezone, distinct=True)
        ]
    )

    form = Form(db.zip_code, record=zip_code_id, formstyle=FormStyleBulma)

    if form.accepted:
        redirect(URL("datatables"))

    return dict(form=form, id=zip_code_id)


@action("zip_code/delete/<zip_code_id>", method=["GET", "POST"])
@action.uses(
    "grid.html",
    session,
    db,
    auth,
)
def zip_code_delete(zip_code_id):
    result = db(db.zip_code.id == zip_code_id).delete()
    redirect(URL("datatables"))


def FormStyleGrid(table, vars, errors, readonly, deletable):
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


@action("companies", method=["POST", "GET"])
@action("companies/<path:path>", method=["POST", "GET"])
@action.uses(
    "grid.html",
    session,
    db,
    auth,
)
def companies(path=None):
    queries = [(db.company.id > 0)]
    orderby = [db.company.name]
    search_queries = [
        GridSearchQuery("Search by Name", lambda val: db.company.name.contains(val))
    ]
    search = GridSearch(search_queries, queries)
    grid = Grid(
        path,
        search.query,
        search_form=search.search_form,
        orderby=orderby,
        create=True,
        details=True,
        editable=True,
        deletable=True,
        **GRID_DEFAULTS
    )

    return dict(grid=grid)


@action("departments", method=["POST", "GET"])
@action("departments/<path:path>", method=["POST", "GET"])
@action.uses(
    "grid.html",
    session,
    db,
    auth,
)
def departments(path=None):
    queries = [(db.department.id > 0)]
    orderby = [db.department.name]

    search_queries = [
        GridSearchQuery("Search by Name", lambda val: db.department.name.contains(val))
    ]
    search = GridSearch(search_queries, queries)

    grid = Grid(
        path,
        search.query,
        search_form=search.search_form,
        orderby=orderby,
        create=True,
        details=True,
        editable=True,
        deletable=True,
        **GRID_DEFAULTS
    )

    return dict(grid=grid)


@action("employees", method=["POST", "GET"])
@action("employees/<path:path>", method=["POST", "GET"])
@action.uses(
    "grid.html",
    session,
    db,
    auth,
)
def employees(path=None):
    queries = [(db.employee.id > 0)]
    orderby = [db.employee.last_name, db.employee.first_name]

    search_queries = [
        GridSearchQuery(
            "Search by Company",
            lambda val: db.company.id == val,
            db.employee.company.requires,
        ),
        GridSearchQuery(
            "Search by Department",
            lambda val: db.department.id == val,
            db.employee.department.requires,
        ),
        GridSearchQuery(
            "Search by Name",
            lambda val: "first_name || ' ' || last_Name LIKE '%%%s%%'" % val,
        ),
    ]
    search = GridSearch(search_queries, queries)

    fields = [
        db.employee.id,
        db.employee.first_name,
        db.employee.last_name,
        db.company.name,
        db.department.name,
        db.employee.hired,
        db.employee.supervisor,
        db.employee.active,
    ]

    grid = Grid(
        path,
        search.query,
        search_form=search.search_form,
        field_id=db.employee.id,
        fields=fields,
        left=[
            db.company.on(db.employee.company == db.company.id),
            db.department.on(db.employee.department == db.department.id),
        ],
        orderby=orderby,
        create=True,
        details=True,
        editable=True,
        deletable=True,
        **GRID_DEFAULTS
    )

    grid.formatters_by_type["boolean"] = (
        lambda value: SPAN(I(_class="fas fa-check-circle")) if value else ""
    )
    grid.formatters_by_type["date"] = lambda value: XML(
        '<script>document.write((new Date(%s,%s,%s)).toLocaleDateString({month: "2-digit", day: "2-digit", year: "numeric"}).split(",")[0])</script>'
        % (
            value.year,
            value.month,
            value.day,
        )
    )
    return dict(grid=grid)
