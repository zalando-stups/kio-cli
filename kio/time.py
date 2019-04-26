import datetime
import re

TIME_UNITS = {
    's': 'seconds',
    'm': 'minutes',
    'h': 'hours',
    'd': 'days',
    'w': 'weeks',
}

TIME_PATTERN = \
    re.compile(r"""
    (?x)
    ^
    (?:
        (?P<magnitude> [+-]? \d+ )
        (?P<unit> [smhdw] )
    |
        (?P<isodate> \d{4} - \d{2} - \d{2} (?: [ ] \d{2} : \d{2} : \d{2} (?: \. \d+)? ) )
    )
    $
    """
               )


def normalize_time(s, default=None, past=False):
    """
    If a time delta of the form /[+-]?\\d+[smdh]/ is given, returns an ISO date string representing the
    current time offset by that delta. If an ISO date string is given, returns it unaltered. If another
    string is given and a default is specified, returns the result of normalizing the default. Assumes
    all ISO strings omit the "T" between date and time.

    >>> normalize_time('2014-06-25 16:02:52').strftime('%Y-%m-%d %H:%M:%S')
    '2014-06-25 16:02:52'
    >>> normalize_time(None, default='2014-06-25 16:02:52').strftime('%Y-%m-%d %H:%M:%S')
    '2014-06-25 16:02:52'
    >>> normalize_time('-2h').strftime('%Y-%m-%d %H:%M:%S') \
            == (datetime.datetime.utcnow() - datetime.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    True
    >>> normalize_time('foo', '-2h').strftime('%Y-%m-%d %H:%M:%S') \
            == normalize_time('-2h').strftime('%Y-%m-%d %H:%M:%S')
    True
    """

    matcher = TIME_PATTERN.search(s or '')
    if matcher:
        if matcher.group('isodate'):
            return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
        else:
            delta = datetime.timedelta(**{TIME_UNITS[matcher.group('unit')]: int(matcher.group('magnitude'))})
            if past:
                return datetime.datetime.utcnow() - delta
            else:
                return datetime.datetime.utcnow() + delta
    elif default:
        return normalize_time(default)
    else:
        raise ValueError(s)
