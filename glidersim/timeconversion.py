from time import strptime
from calendar import timegm
from datetime import datetime, timedelta
def strptimeToEpoch(datestr, fmt):
    ''' datestr is an ascii string such as 2010 May 01
        and fmt is the format such as %Y %b %d
    '''
    ts = strptime(datestr , fmt)
    return timegm(ts)


def epochToDateTimeStr(seconds,dateformat="%Y%m%d",timeformat="%H:%M"):
    ''' returns a time stamp as datestr, timestr pair, as used in
        the configuration of the glidersim
    '''
    d=datetime.utcfromtimestamp(seconds)
    datestr=d.strftime(dateformat)
    timestr=d.strftime(timeformat)
    return datestr,timestr
