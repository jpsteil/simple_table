## SIMPLE TABLE
The simple_table application is a proof-of-concept / playground to analyze different web grids in py4web. The sample application includes samples using simple_table, the py4web HTML grid and a datatables.net implementation.

Run live sample [here](http://pythonbench.com/simple_table).

py4web HTML Grid Examples

### ZIP Code database
Simple CRUD over 40,000 record table. Highlight basic implementation of simple_table.

* Click column heads for sorting - click again for DESC
* Pagination control
* Filter Form - you supply and control filtering
* Action Buttons - with or without text
* Full CRUD with Delete Confirmation
* Companies
* Companies CRUD - code table for use with Employees

### Departments
Departments CRUD code table for use with Employees

### Employees
Employees CRUD - Shows LEFT OUTER JOINs to bring in foreign key descriptive fields.

* Filter dropdowns from alternate tables
* Search filter over concatenated table fields
* Auto date formatting based on browser locale
* Display boolean fields with font-awesome checkbox
* LEFT JOIN to control display of foreign keys

### Datatables.net Grid Examples
Datatables.net ZIP Code CRUD

### Model / Database
The following model is used within the application. It is delivered as a SQLite database.
```
db.define_table('zip_code',
        Field('id', 'id', readable=False),
        Field('zip_code', length=5, required=True, unique=True,
              requires=[IS_NOT_EMPTY(),
                        IS_NOT_IN_DB(db, 'zip_code.zip_code')]),
        Field('zip_type'),
        Field('primary_city'),
        Field('state'),
        Field('county'),
        Field('timezone'),
        Field('area_code'),
        Field('latitude', 'decimal(5,2)'),
        Field('longitude', 'decimal(5,2)'),
        format='%(zip_code)s')

db.executesql('CREATE INDEX IF NOT EXISTS zip_code__idx ON zip_code (zip_code);')
db.executesql('CREATE INDEX IF NOT EXISTS zip_code_2__idx ON zip_code (zip_code, county, primary_city);')

db.define_table('company',
                Field('name', length=50))

db.define_table('department',
                Field('name', length=50))

db.define_table('employee',
                Field('first_name', length=50),
                Field('last_name', length=50),
                Field('company_name', length=50),
                Field('address', length=50),
                Field('city', length=50),
                Field('county', length=50),
                Field('state', length=50),
                Field('zip_code', length=50),
                Field('phone_1', length=50),
                Field('phone_2', length=50),
                Field('email', length=50),
                Field('web', length=50),
                Field('supervisor', 'reference employee',
                      requires=IS_NULL_OR(IS_IN_DB(db, 'employee.id',
                                                   '%(last_name)s, %(first_name)s',
                                                   zero='..'))),
                Field('company', 'reference company',
                      requires=IS_NULL_OR(IS_IN_DB(db, 'company.id',
                                                   '%(name)s',
                                                   zero='..'))),
                Field('department', 'reference department',
                      requires=IS_NULL_OR(IS_IN_DB(db, 'department.id',
                                                   '%(name)s',
                                                   zero='..'))),
                Field('hired', 'date', requires=IS_NULL_OR(IS_DATE())))
```
