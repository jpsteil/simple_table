"""
This file defines the database models
"""

from .common import db, Field
from pydal.validators import *


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
                                                   zero='..')),
                      filter_out=lambda x: '%s %s' % (x.first_name, x.last_name) if x else ''),
                Field('company', 'reference company',
                      requires=IS_NULL_OR(IS_IN_DB(db, 'company.id',
                                                   '%(name)s',
                                                   zero='..'))),
                Field('department', 'reference department',
                      requires=IS_NULL_OR(IS_IN_DB(db, 'department.id',
                                                   '%(name)s',
                                                   zero='..'))),
                Field.Virtual('fullname', lambda x: f'{x.employee.first_name} {x.employee.last_name}'),
                Field('hired', 'date', requires=IS_NULL_OR(IS_DATE())),
                Field('active', 'boolean', default=False))

db.commit()
