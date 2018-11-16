from math import ceil, floor, trunc

import pendulum as pendulum
from prettytable import PrettyTable

from qq.exceptions import FilterError
from qq.utils import to_num, to_int, to_float, humanize, dehumanize, ordinal
from qq.replacements import apply_char_replacements, print_replacements_table


FILTERS = {
    # Data conversion
    'num': (to_num, 0, "<column_name>|num", "str", "num", "Convert to integer or float."),
    'number': (to_num, 0, "<column_name>|number", "str", "num", "Convert to integer or float."),
    'int': (to_int, 0, "<column_name>|int", "str", "int", "Convert to integer."),
    'float': (to_float, 0, "<column_name>|float", "str", "float", "Convert to float."),
    'str': (lambda s: str(s), 0, "<column_name>|str", "any", "str", "Convert to string."),

    # Human
    'humanize': (lambda s, u: humanize(to_num(s), u, show_value=False), 1,
                 "<column_name>|humanize|<unit>", "num", "str", "Format number to human string."),
    'dehumanize': (dehumanize, 0, "<column_name>|dehumanize", "str", "num", "Convert from human string to number."),
    'ordinal': (lambda s: ordinal(to_int(s)), 0, "<column_name>|ordinal", "num", "str", "Convert number to ordinal string."),

    # String manipulation
    'lower': (lambda s: s.lower(), 0, "<column_name>|lower", "str", "str", "Convert string to lowercase."),
    'upper': (lambda s: s.upper(), 0, "<column_name>|upper", "str", "str", "Convert string to uppercase."),
    'capitalize': (lambda s: s.capitalize(), 0, "<column_name>|capitalize", "str", "str", "Capitalize string."),
    'ljust': (lambda s, w: s.ljust(to_int(w)), 1, "<column_name>|ljust|<width>", "str", "str", "Left justify string in <width> spaces."),
    'rjust': (lambda s, w: s.rjust(to_int(w)), 1, "<column_name>|rjust|<width>", "str", "str", "Right justify string in <width> spaces."),
    'swapcase': (lambda s: s.swapcase(s), 0, "<column_name>|swapcase", "str", "str", "Swap string case."),
    'replace': (lambda s, x, y: s.replace(x, y), 2, "<column_name>|replace|<from>|<to>", "str", "str", "Replace sub-string <from> with <to>."),
    'title': (lambda s: s.title(), 0, "<column_name>|title", "str", "str", "Convert string to title case."),
    'zfill': (lambda s, w: s.zfill(to_int(w)), 1, "<column_name>|zfill|<width>", "str", "str", "Zero fill string to <width> size."),
    'length': (lambda s: len(s), 0, "<column_name>|length", "str", "str", "Return the length of the string."),
    'reverse': (lambda s: ''.join(reversed(s)), 0, "<column_name>|reverse", "str", "str", "Reverse the characters in the string."),
    'prefix': (lambda s, p: ''.join([p, s]), 1, "<column_name>|prefix|<prefix>", "str", "str", "Prefix the string with <prefix>."),
    'suffix': (lambda s, x: ''.join([s, x]), 1, "<column_name>|suffix|<suffix>", "str", "str", "Suffix the string with <suffix>."),
    'substr': (lambda s, x, y: s[x:y], 2, "<column_name>|substr|<start>|<end>", "str", "str", "Return a sub-string."),
    # TODO: regex

    # Data formatting
    'format': (lambda x, fmt: format(x, fmt), 1, "<column_name>|format|<format>", "str", "str", "Format data using Python's `format(<format>)` function."),
    # TODO: locale

    # (Simple) maths (intermediate values are numbers and inputs are auto converted to numbers)
    'add': (lambda s, o: to_num(s) + to_num(o), 1, "<column_name>|add|<value>", "num", "num", "Add <value> to number."),
    'sub': (lambda s, o: to_num(s) - to_num(o), 1, "<column_name>|sub|<value>", "num", "num", "Subtract <value> from number."),
    'mult': (lambda s, o: to_num(s) * to_num(o), 1, "<column_name>|mult|<value>", "num", "num", "Multiply number by <value>."),
    'div': (lambda s, o: to_num(s) / to_num(o), 1, "<column_name>|div|<value>", "num", "num", "Divide number by <value>."),
    'abs': (lambda x: abs(to_num(x)), 0, "<column_name>|abs", "num", "num", "Take the absolute value of a number."),
    'round': (lambda x, d: round(to_num(x), to_int(d)), 1, "<column_name>|round|<digits>", "num", "num", "Round number to <digits> digits."),
    'ceil': (lambda x: ceil(to_num(x)), 0, "<column_name>|ceil", "num", "num", "Return the ceiling value of a number."),
    'floor': (lambda x: floor(to_num(x)), 0, "<column_name>|floor", "num", "num", "Return the floor value of a number."),
    'trunc': (lambda x: trunc(to_num(x)), 0, "<column_name>|trunc", "num", "num", "Return the number truncated."),

    # Datetime filters (intermediate values are pendulum datetimes)
    'datetime': (lambda s: pendulum.parse(s), 0, "<column_name>|datetime", "str", "datetime", "Parse a datetime string."),
    'datetime_tz': (lambda s, tz: pendulum.parse(s, tz=tz), 1, "<column_name>|datetime_tz|<tz>", "str", "datetime", "Prase a datetime string with the specified <tz> timezone."),
    'tz': (lambda dt, tz: pendulum.timezone(tz).convert(dt), 1, "<column_name>|tz|<tz>", "datetime", "datetime", "Convert a datetime to a new <tz> timezone."),
    'iso8601': (lambda dt: dt.to_iso8601_string(), 0, "<column_name>|iso8601", "datetime", "str", "Convert a datetime to an ISO8601 string representation."),
    'utc': (lambda dt: pendulum.timezone('UTC').convert(dt), 0, "<column_name>|utc", "datetime", "datetime", "Convert a datetime to UTC."),
    'strftime': (lambda dt, fmt: dt.strftime(fmt), 1, "<column_name>|strftime|<format>", "datetime", "str", "Format a datetime using `strftime(<format>)`."),

    # Column manipulation
    # TODO: merge
    # TODO: split
}


def preprocess_filters(filter_args):
    """
    Check and organize filters
    :param filter_args:
    :return:
    """
    filters = {}
    if filter_args:
        for filter_combo in filter_args:
            parts = filter_combo.split('|')
            if len(parts) < 2:
                raise FilterError(f"Invalid filter combo: {filter_combo}")
            col = parts[0]
            if col in filters:
                raise FilterError(f"Multiple filters for column: {col}")
            filters[col] = [apply_char_replacements(param) for param in parts[1:]]

    return filters


def print_filter_list_table():
    """
    Print out a nice table of filters w/docs
    :return:
    """
    table = PrettyTable(('Filter', 'Num. Params', 'Syntax**', 'In type*', 'Out type', 'Description'))
    table.align = 'l'
    for func_name in sorted(FILTERS.keys()):
        values = FILTERS[func_name]
        table.add_row([func_name] + list(values[1:]))
    print(table)
    print("* Most filters that take numeric inputs will automatically apply the `num` filter to the column data prior to filtering.\n"
          "  Filters can be chained together using the pipe (|) character. For example, `c1|num|add|1|human`\n"
          "  The type of the data after the last filter has run will be the type that is added to the database.\n")
    print("""** To represent special characters in filters, you can use these replacement sequences:""")
    print_replacements_table()


def apply_filters(filters, colnames, row):
    """
    Process data based on filter chains
    :param filters:
    :param colnames:
    :param row:
    :return:
    """
    if filters:
        new_row = []
        for col, data in zip(colnames, row):
            if col in filters:
                params = filters[col][:]
                while params:
                    filter_name = params.pop(0)
                    if filter_name not in FILTERS:
                        raise FilterError(f"Error: Invalid filter name: {filter_name}")

                    func, num_params = FILTERS[filter_name][:2]
                    func_args = [params.pop(0) for _ in range(num_params)]
                    data = func(data, *func_args)

            new_row.append(data)
        return new_row

    return row