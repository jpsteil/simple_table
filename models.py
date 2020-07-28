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

db.commit()
