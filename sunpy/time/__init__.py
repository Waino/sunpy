"""Time related functionality"""

import re

import julian
import timerange
from datetime import datetime
from datetime import timedelta
from sunpy.time.timerange import TimeRange
from sunpy.time.julian import *

__all__ = ["parse_time", "day_of_year", "break_time"]
__all__ += julian.__all__
__all__ += timerange.__all__


# Mapping of time format codes to regular expressions.
REGEX = {
    '%Y': '(?P<year>\d{4})',
    '%m': '(?P<month>\d{1,2})',
    '%d': '(?P<day>\d{1,2})',
    '%H': '(?P<hour>\d{1,2})',
    '%M': '(?P<minute>\d{1,2})',
    '%S': '(?P<second>\d{1,2})',
    '%f': '(?P<microsecond>\d+)',
    '%b': '(?P<month_str>[a-zA-Z]+)',
}

TIME_FORMAT_LIST = [
    "%Y-%m-%dT%H:%M:%S.%f",    # Example 2007-05-04T21:08:12.999999
    "%Y/%m/%dT%H:%M:%S.%f",    # Example 2007/05/04T21:08:12.999999
    "%Y-%m-%dT%H:%M:%S.%fZ",   # Example 2007-05-04T21:08:12.999Z
    "%Y-%m-%dT%H:%M:%S",       # Example 2007-05-04T21:08:12
    "%Y/%m/%dT%H:%M:%S",       # Example 2007/05/04T21:08:12
    "%Y%m%dT%H%M%S.%f",        # Example 20070504T210812.999999
    "%Y%m%dT%H%M%S",           # Example 20070504T210812
    "%Y/%m/%d %H:%M:%S",       # Example 2007/05/04 21:08:12
    "%Y/%m/%d %H:%M",          # Example 2007/05/04 21:08
    "%Y/%m/%d %H:%M:%S.%f",    # Example 2007/05/04 21:08:12.999999
    "%Y-%m-%d %H:%M:%S.%f",    # Example 2007-05-04 21:08:12.999999
    "%Y-%m-%d %H:%M:%S",       # Example 2007-05-04 21:08:12
    "%Y-%m-%d %H:%M",          # Example 2007-05-04 21:08
    "%Y-%b-%d %H:%M:%S",       # Example 2007-May-04 21:08:12
    "%Y-%b-%d %H:%M",          # Example 2007-May-04 21:08
    "%Y-%b-%d",                # Example 2007-May-04
    "%Y-%m-%d",                # Example 2007-05-04
    "%Y/%m/%d",                # Example 2007/05/04
    "%d-%b-%Y",                # Example 04-May-2007
    "%Y%m%d_%H%M%S",           # Example 20070504_210812
]


def _group_or_none(match, group, fun):
    try:
        ret = match.group(group)
    except IndexError:
        return None
    else:
        return fun(ret)

def _n_or_eq(a, b):
    return a is None or a == b

def _regex_parse_time(inp, format):
    # Parser for finding out the minute value so we can adjust the string
    # from 24:00:00 to 00:00:00 the next day because strptime does not
    # understand the former.
    for key, value in REGEX.iteritems():
        format = format.replace(key, value)
    match = re.match(format, inp)
    if match is None:
        return None, None
    try:
        hour = match.group("hour")
    except IndexError:
        return inp, timedelta(days=0)
    if match.group("hour") == "24":
        if not all(_n_or_eq(_group_or_none(match, g, int), 00)
            for g in ["minute", "second", "microsecond"]
        ):
            raise ValueError
        from_, to = match.span("hour")
        return inp[:from_] + "00" + inp[to:], timedelta(days=1)
    return inp, timedelta(days=0)


def find_time(string, format):
    """ Return iterator of occurences of date formatted with format
    in string. Currently supported format codes: """
    re_format = format
    for key, value in REGEX.iteritems():
        re_format = re_format.replace(key, value)
    matches = re.finditer(re_format, string)
    for match in matches:
        try:
            matchstr = string[slice(*match.span())]
            dt = datetime.strptime(matchstr, format)
        except ValueError:
            continue
        else:
            yield dt


find_time.__doc__ += ', '.join(REGEX.keys())

def _iter_empty(iter):
    try:
        iter.next()
    except StopIteration:
        return True
    return False


def extract_time(string):
    """ Find subset of string that corresponds to a datetime and return
    its value as a a datetime. If more than one or none is found, raise
    ValueError. """
    matched = None
    bestmatch = None
    for time_format in TIME_FORMAT_LIST:
        found = find_time(string, time_format)
        try:
            match = found.next()
        except StopIteration:
            continue
        else:
            if matched is not None:
                if time_format.startswith(matched):
                    # Already matched is a substring of the one just matched.
                    matched = time_format
                    bestmatch = match
                elif not matched.startswith(time_format):
                    # If just matched is substring of time_format, just ignore
                    # just matched.
                    raise ValueError("Ambiguous string")
            else:
                matched = time_format
                bestmatch = match
            if not _iter_empty(found):
                raise ValueError("Ambiguous string")
    if not matched:
        raise ValueError("Time not found")
    return bestmatch


def parse_time(time_string=None):
    """Given a time string will parse and return a datetime object.
    Similar to the anytim function in IDL.

    .. note:: If no input is given then returns the datetime for the 
    current time.

    Parameters
    ----------
    time_string : string
        Datestring to parse. Defaults to utcnow() if none specified.

    Returns
    -------
    out : datetime
        DateTime corresponding to input date string

    Examples
    --------
    >>> sunpy.time.parse_time('2012/08/01')
    >>> sunpy.time.parse_time('2005-08-04T00:01:02.000Z')

    .. todo:: add ability to parse tai (International Atomic Time seconds since 
    Jan 1, 1958)
    """
    if time_string is None:
        return datetime.now()
    elif isinstance(time_string, datetime):
        return time_string
    elif isinstance(time_string, tuple):
        return datetime(*time_string)
    elif isinstance(time_string, int) or isinstance(time_string, float):
        return datetime(1979, 1, 1) + timedelta(0, time_string)
    else:
        for time_format in TIME_FORMAT_LIST: 
            try:
                try:
                    ts, time_delta = _regex_parse_time(time_string, time_format)
                except TypeError:
                    break
                if ts is None:
                    continue
                return datetime.strptime(ts, time_format) + time_delta
            except ValueError:
                pass
    
        raise ValueError("%s is not a valid time string!" % time_string)
    
def is_time(time):
    """Returns true if the input is a valid date/time representation"""
    if None:
        return False
    elif isinstance(time, datetime):
        return True

    try:
        parse_time(time)
    except ValueError:
        return False
    else:
        return True

def day_of_year(t=None):
    """Returns the day of year."""
    SECONDS_IN_DAY = 60 * 60 * 24.0
    time = parse_time(t)
    time_diff = parse_time(t) - datetime(time.year, 1, 1, 0, 0, 0)
    result = time_diff.days + time_diff.seconds / SECONDS_IN_DAY
    return result

def break_time(t=None):
    """Given a time returns a string. Useful for naming files."""
    #TODO: should be able to handle a time range
    return parse_time(t).strftime("%Y%m%d_%H%M%S")


def get_day(dt):
    """ Return datetime for the beginning of the day of given datetime. """
    return datetime(dt.year, dt.month, dt.day)
