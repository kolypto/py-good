from __future__ import division
import six
from datetime import date, time, datetime, tzinfo, timedelta


from .base import ValidatorBase
from .. import Invalid
from ..schema.util import get_type_name


class FixedOffset(tzinfo):
    """ Fixed timezone initialized with a constant offset.

    This is only used to simulate '%z' in Python2.

    :param offset: Fixed offset, given as `timedelta` or in the "+HHMM" formatted string
    :type offset: timedelta|str
    :param name: Optional timezone name. If not provided -- is formatted as "+HHMM"
    :type name: str|None
    """

    ZERO = timedelta(0)

    @classmethod
    def parse_z(cls, offset):
        """ Parse %z offset into `timedelta` """
        assert len(offset) == 5, 'Invalid offset string format, must be "+HHMM"'
        return timedelta(hours=int(offset[:3]), minutes=int(offset[0] + offset[3:]))

    @classmethod
    def format_z(cls, offset):
        """ Format `timedelta` into %z """
        sec = offset.total_seconds()
        return '{s}{h:02d}{m:02d}'.format(s='-' if sec<0 else '+', h=abs(int(sec/3600)), m=int((sec%3600)/60))

    def __init__(self, offset, name=None):
        super(FixedOffset, self).__init__()

        # Parse
        if isinstance(offset, six.string_types):
            offset = self.parse_z(offset)

        # Create
        self._offset = offset
        self._name = name or self.format_z(self._offset)

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return self._name

    def dst(self, dt):
        return self.ZERO

    def __repr__(self):
        return self._name


class DateTime(ValidatorBase):
    """ Validate that the input is a Python `datetime`.

    Supports the following input values:

    1. `datetime`: passthrough
    2. string: parses the string with any of the specified formats
        (see [strptime()](https://docs.python.org/3.4/library/datetime.html#strftime-and-strptime-behavior))

    ```python
    from datetime import datetime
    from good import Schema, DateTime

    schema = Schema(DateTime('%Y-%m-%d %H:%M:%S'))

    schema('2014-09-06 21:22:23')  #-> datetime.datetime(2014, 9, 6, 21, 22, 23)
    schema(datetime.now())  #-> datetime.datetime(2014, 9, 6, 21, 22, 23)
    schema('2014')
    #-> Invalid: Invalid datetime format, expected DateTime, got 2014.
    ```

    Notes on timezones:

    * If the format does not support timezones, it always returns *naive* `datetime` objects (without `tzinfo`).
    * If timezones are supported by the format (with `%z`/`%Z`),
       it returns an *aware* `datetime` objects (with `tzinfo`).
    * Since Python2 does not always support `%z` -- `DateTime` does this manually.
      Due to the limited nature of this workaround, the support for `%z` only works if it's at the end of the string!

    As a result, '00:00:00' is parsed into a *naive* datetime, and '00:00:00 +0200' results in an *aware* datetime.

    If your application wants different rules, use `localize` and `astz`:

    * `localize` argument is the default timezone to set on *naive* datetimes,
        or a callable which is applied to the input and should return adjusted `datetime`.
    * `astz` argument is the timezone to adjust the *aware* datetime to, or a callable.

    Then the generic recipe is:

    * Set `localize` to the timezone (or a callable) that you expect the user to input the datetime in
    * Set `astz` to the timezone you wish to have in the result.

    This works best with the excellent [pytz](http://pytz.sourceforge.net/) library:

    ```python
    import pytz
    from good import Schema, DateTime

    # Formats: with and without timezone
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S%z'
    ]

    # The used timezones
    UTC = pytz.timezone('UTC')
    Oslo = pytz.timezone('Europe/Oslo')

    ### Example: Use Europe/Oslo by default
    schema = Schema(DateTime(
        formats,
        localize=Oslo
    ))

    schema('2014-01-01 00:00:00')
    #-> datetime.datetime(2014, 1, 1, 0, 0, tzinfo='Europe/Oslo')
    schema('2014-01-01 00:00:00-0100')
    #-> datetime.datetime(2014, 1, 1, 0, 0, tzinfo=-0100)

    ### Example: Use Europe/Oslo by default and convert to an aware UTC
    schema = Schema(DateTime(
        formats,
        localize=Oslo,
        astz=UTC
    ))

    schema('2014-01-01 00:00:00')
    #-> datetime.datetime(2013, 12, 31, 23, 17, tzinfo=<UTC>)
    schema('2014-01-01 00:00:00-0100')
    #-> datetime.datetime(2014, 1, 1, 1, 0, tzinfo=<UTC>)

    ### Example: Use Europe/Oslo by default, convert to a naive UTC
    # This is the recommended way
    schema = Schema(DateTime(
        formats,
        localize=Oslo,
        astz=lambda v: v.astimezone(UTC).replace(tzinfo=None)
    ))

    schema('2014-01-01 00:00:00')
    #-> datetime.datetime(2013, 12, 31, 23, 17)
    schema('2014-01-01 00:00:00-0100')
    #-> datetime.datetime(2014, 1, 1, 1, 0)
    ```

    Note: to save some pain, make sure to *always* work with naive `datetimes` adjusted to UTC!
    Armin Ronacher [explains it here](http://lucumr.pocoo.org/2011/7/15/eppur-si-muove/).

    Summarizing all the above, the validation procedure is a 3-step process:

    1. Parse (only with strings)
    2. If is *naive* -- apply `localize` and make it *aware* (if `localize` is specified)
    3. If is *aware* -- apply `astz` to convert it (if `astz` is specified)

    :param formats: Supported format string, or an iterable of formats to try them all.
    :type formats: str|Iterable[str]
    :param localize: Adjust *naive* `datetimes` to a timezone, making it *aware*.

        A `tzinfo` timezone object,
        or a callable which is applied to a *naive* datetime and should return an adjusted value.

        Only called for *naive* `datetime`s.

    :type localize: datetime.tzinfo|Callable
    :param astz: Adjust *aware* `datetimes` to another timezone.

        A `tzinfo` timezone object,
        or a callable which is applied to an *aware* datetime and should return an adjusted value.

        Only called for *aware* `datetime`s, including those created by `localize`

    :type astz: datetime.tzinfo|Callable
    """

    name = get_type_name(datetime)

    # Test whether Python supports %z
    try:
        datetime.strptime('+0000', '%z')
        python_supports_z = True
    except:
        python_supports_z = False

    def __init__(self, formats, localize=None, astz=None):
        # Ensure a tuple
        self.formats = tuple([formats]
                             if isinstance(formats, six.string_types) else
                             formats)

        # Converters
        if isinstance(localize, tzinfo):
            self.localize = lambda dt: dt.replace(tzinfo=localize)
        else:
            self.localize = localize
        if isinstance(astz, tzinfo):
            self.astz = lambda dt: dt.astimezone(astz)
        else:
            self.astz = astz

        # Test converters
        if self.localize:
            assert isinstance(self.localize(datetime.now()), datetime), 'localize does not return `datetime`'
        if self.astz:
            assert isinstance(self.astz(datetime.now().replace(tzinfo=FixedOffset('+0000'))), datetime), 'astz does not return `datetime`'

    def preprocess(self, dt):
        """ Preprocess the `dt` with `localize()` and `astz()` """
        # Process
        try:  # this block should not raise errors, and if it does -- they should not be wrapped with `Invalid`
            # localize
            if self.localize and dt.tzinfo is None:
                dt = self.localize(dt)

            # astimezone
            if self.astz and dt.tzinfo is not None:
                dt = self.astz(dt)

            # Finish
            return dt
        except Exception as e:
            if isinstance(e, Invalid):
                raise
            six.reraise(RuntimeError, e)

    @classmethod
    def strptime(cls, value, format):
        """ Parse a datetime string using the provided format.

        This also emulates `%z` support on Python 2.

        :param value: Datetime string
        :type value: str
        :param format: Format to use for parsing
        :type format: str
        :rtype: datetime
        :raises ValueError: Invalid format
        :raises TypeError: Invalid input type
        """
        # Simplest case: direct parsing
        if cls.python_supports_z or '%z' not in format:
            return datetime.strptime(value, format)
        else:
            # %z emulation case
            assert format[-2:] == '%z', 'For performance, %z is only supported at the end of the string'

            # Parse
            dt = datetime.strptime(value[:-5], format[:-2])  # cutoff '%z' and '+0000'
            tz = FixedOffset(value[-5:])  # parse %z into tzinfo

            # Localize
            return dt.replace(tzinfo=tz)

    def __call__(self, v):
        # Input types
        if isinstance(v, datetime):
            dt = v
        elif not isinstance(v, (six.string_types, datetime)):
            raise Invalid(_(u'Invalid value type'), provided=get_type_name(type(v)))
        else:
            # Try all formats
            for format in self.formats:
                # Parse
                try:
                    dt = self.strptime(v, format)
                except ValueError:
                    continue
                else:
                    break
            else:
                # Nothing worked
                raise Invalid(_(u'Invalid {name} format').format(name=self.name))

        # Finish
        return self.preprocess(dt)


class Date(DateTime):
    """ Validate that the input is a Python `date`.

    Supports the following input values:

    1. `date`: passthrough
    2. `datetime`: takes the `.date()` part
    2. string: parses (see [`DateTime`](#datetime))

    ```python
    from datetime import date
    from good import Schema, Date

    schema = Schema(Date('%Y-%m-%d'))

    schema('2014-09-06')  #-> datetime.date(2014, 9, 6)
    schema(date(2014, 9, 6))  #-> datetime.date(2014, 9, 6)
    schema('2014')
    #-> Invalid: Invalid date format, expected Date, got 2014.
    ```
    """

    name = get_type_name(date)

    def __call__(self, v):
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        return super(Date, self).__call__(v).date()


class Time(DateTime):
    """ Validate that the input is a Python `time`.

    Supports the following input values:

    1. `time`: passthrough
    2. `datetime`: takes the `.timetz()` part
    2. string: parses (see [`DateTime`](#datetime))

    Since `time` is subject to timezone problems,
    make sure you've read the notes in the relevant section of [`DateTime`](#datetime) docs.
    """

    name = get_type_name(time)

    def __call__(self, v):
        if isinstance(v, time):
            v = datetime.combine(datetime.today(), v)
        return super(Time, self).__call__(v).timetz()





__all__ = ('DateTime', 'Date', 'Time')
