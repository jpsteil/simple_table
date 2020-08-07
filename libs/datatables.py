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
