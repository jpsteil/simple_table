class DataTablesResponse:
    def __init__(self, fields=None, data_function=None, edit_function=None, page_length=15, sort_sequence=None):
        """
        A dataholder class so we can simply pass data from controller to web page with some defaults

        :param fields: list of DataTablesField objects to display on the page
        :param data_function: the controller function to call to get the data
        :param edit_function: edit function to call to edit a page - Not in use at this time
        :param page_length: default=15 - number of rows to display by default
        :param sort_sequence: list of a list of columns to sort by
        """
        self.fields = fields
        self.data_function = data_function
        self.edit_function = edit_function
        self.page_length = page_length
        self.sort_sequence = sort_sequence if sort_sequence else []


    def script(self):
        js = ('<script type="text/javascript">'
              '    $(document).ready(function() {'
              '        $(\'#datatables_table\').DataTable( {'
              '            dom: "lfrtip", '
              '            processing: true, '
              '            serverSide: true, '
              '            lengthMenu: [  [10, 15, 20, -1], [10, 15, 20, \'All\']  ], '
              '            pageLength: %s, '
              '            pagingType: "numbers", '
              '            ajax: "%s", '
              '            columns: [' % (self.page_length, self.data_url))
        #  add the field values
        for field in self.fields:
            js += ('{'
                   '    "data": "%s", '
                   '    "name": "%s", '
                   '    "visible": %s, '
                   '},' % (field.name, field.name, 'true' if field.visible else 'false'))
        #  add the row buttons
        js += ('{'
               '    data: null,'
               '    render: function ( data, type, row ) {'
               '      var edit_url=\'%s\'; '
               '      edit_url = edit_url.replace("record_id", row.DT_RowId); '
               '      var delete_url=\'%s\'; '
               '      delete_url = delete_url.replace("record_id", row.DT_RowId); '
               '      return edit_url + "&nbsp;" + delete_url '
               '    }, '
               '    orderable: false, '
               '}' % (A(I(_class='fas fa-edit'),
                        _href=self.edit_url if self.edit_url else '#',
                        _class='button is-small'),
                      A(I(_class='fas fa-trash'),
                        _href=self.delete_url if self.delete_url else '#',
                        _class='button is-small',
                        _message='Delete Record')))
        js += '], columnDefs: ['
        for index, field in enumerate(self.fields):
            if not field.visible:
                js += '{"visible": false, "targets": %s},' % index
        js += '{className: "has-text-centered", "targets": %s}' % (index + 1)

        js += ('],'
               'order: ')
        for sort in self.sort_sequence:
            js += '[ %s, "%s" ]' % (sort[0], sort[1])

        js += (','
               '        stateSave: true, '
               '        select: true, '
               '    });'
               '    $(".dataTables_filter input").focus().select();'
               '});'
               '</script>')

        return str(js)

    def table(self):
        _html = DIV()
        if self.create_url and self.create_url != '':
            _a = A('', _href=self.create_url,
                   _class='button', _style='margin-bottom: 1rem;')
            _span = SPAN(_class='icon is-small')
            _span.append(I(_class='fas fa-plus'))
            _a.append(_span)
            _a.append(SPAN('New'))
            _html.append(_a)

        _table = TABLE(_id='datatables_table',
                       _class='compact stripe hover cell-border order-column',
                       _style='padding-top: 1rem;')
        _thead = THEAD()
        _tr = TR()
        for field in self.fields:
            _tr.append(TH(field.label, _class='datatables-header'))
        _tr.append(TH('ACTIONS', _class='datatables-header has-text-centered',
                      _style='color: black; width: 1px; white-space: nowrap;'))
        _thead.append(_tr)
        _table.append(_thead)
        _table.append(TBODY())

        _html.append(_table)
        return str(_html)


class DataTablesRequest:
    def __init__(self, get_vars):
        """
        the data request coming from a datatables.net ajax call

        :param get_vars: vars supplied by datatables.net
        """
        self.draw = None
        self.start = 0
        self.length = 15
        self.search_value = None
        self.search_regex = None
        self.columns = dict()
        self.orderby = dict()
        self.dal_orderby = []

        self.get_vars = get_vars

        self.parse()

    def parse(self):
        """
        parse all the args we need from datatables.net into instance variables

        :return:
        """
        for x in self.get_vars:
            value = self.get_vars[x]
            if x == 'start':
                self.start = int(value)
            elif x == 'draw':
                self.draw = value
            elif x == 'length':
                self.length = int(value)
            elif x == 'search[value]':
                self.search_value = value
            elif x == 'search[regex]':
                self.search_regex = value
            elif x[:7] == 'columns':
                column = dict()

                #  get start and end positions of attributes
                column_number_start = x.find('[')
                column_number_end = x.find(']', column_number_start)
                column_attribute_start = column_number_end + 2
                column_attribute_end = x.find(']', column_attribute_start)
                column_sub_attribute_start = x.find('[', column_attribute_end)

                column_number = int(x[column_number_start + 1:column_number_end])

                if column_number in self.columns:
                    column = self.columns[column_number]

                #  get the attribute name and value
                column_attribute = x[column_attribute_start: column_attribute_end]
                column_sub_attribute = ''
                if column_sub_attribute_start and column_sub_attribute_start > 0:
                    column_sub_attribute = x[column_sub_attribute_start + 1: -1]

                column['column_number'] = column_number
                if column_sub_attribute:
                    column_attribute += f'_{column_sub_attribute}'

                column[column_attribute] = value

                self.columns[column_number] = column
            elif x[:5] == 'order':
                orderby = dict()

                #  get start and end positions of attributes
                orderby_number_start = x.find('[')
                orderby_number_end = x.find(']', orderby_number_start)
                orderby_attribute_start = orderby_number_end + 2
                orderby_attribute_end = x.find(']', orderby_attribute_start)
                orderby_sub_attribute_start = x.find('[', orderby_attribute_end)

                orderby_number = int(x[orderby_number_start + 1:orderby_number_end])

                if orderby_number in self.orderby:
                    orderby = self.orderby[orderby_number]

                #  get the attribute name and value
                orderby_attribute = x[orderby_attribute_start: orderby_attribute_end]
                orderby_sub_attribute = ''
                if orderby_sub_attribute_start and orderby_sub_attribute_start > 0:
                    orderby_sub_attribute = x[orderby_sub_attribute_start + 1: -1]
                value = self.get_vars[x]

                orderby['orderby_number'] = orderby_number
                if orderby_sub_attribute:
                    orderby_attribute += f'_{orderby_sub_attribute}'

                if orderby_attribute == 'column':
                    orderby[orderby_attribute] = int(value)
                else:
                    orderby[orderby_attribute] = value

                self.orderby[orderby_number] = orderby

        return

    def order(self, db, table_name):
        """
        build a dal orderby clause

        at this time it only supports orderby for 1 table

        :param db: dal reference
        :param table_name: name of the table the colums are in
        :return:
        """
        self.dal_orderby = []
        if self.orderby and table_name:
            for ob in self.orderby:
                column = self.columns[self.orderby[ob]['column']]
                if self.orderby[ob]['dir'] == 'desc':
                    self.dal_orderby.append(~db[table_name][column['name']])
                else:
                    self.dal_orderby.append(db[table_name][column['name']])

        return


class DataTablesField:
    def __init__(self, name, label=None,
                 sort_sequence=None, visible=True, editable=False,
                 hide_edit=False, control_type=None, options=None):
        """
        a dataholder class holding all the info we need on a field

        :param name: the name
        :param label: the label
        :param sort_sequence: the sort sequence
        :param visible: visible or not
        :param editable: is it editable - future
        :param hide_edit: hide this field on an edit - future
        :param control_type: type of control to use for the edit page
        :param options: misc options - future
        """
        self.name = name
        self.label = label if label else name.upper().replace('_', ' ')
        self.sort_sequence = sort_sequence
        self.visible = visible
        self.editable = editable
        self.hide_edit = hide_edit
        self.control_type = control_type
        self.options = options
