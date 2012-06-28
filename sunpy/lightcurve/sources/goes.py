# -*- coding: utf-8 -*-
"""Provides programs to process and analyze GOES data."""
from __future__ import absolute_import

import datetime
import matplotlib
import sunpy
from sunpy.lightcurve import LightCurve
from pandas.io.parsers import read_csv
from matplotlib import pyplot as plt  

class GOESLightCurve(LightCurve):
    """GOES light curve definition
    
    Examples
    --------
    >>> import sunpy
    >>> goes = sunpy.lightcurve.GOESLightCurve()
    >>> goes = sunpy.lightcurve.GOESLightCurve('2012/06/01', '2012/06/05')
    >>> 
    >>> goes.show()
    
    References
    ----------
    | http://www.ngdc.noaa.gov/goes/sem
    | http://www.ngdc.noaa.gov/goes/sem/getData/goes15
    """
    def __init__(self, *args, **kwargs):
        LightCurve.__init__(self, *args, **kwargs)

    def show(self, title="GOES Xray Flux", **kwargs):
        """Plots GOES light curve is the usual manner"""
        fig = plt.figure()
        ax = fig.add_subplot(111)
        dates = matplotlib.dates.date2num(self.data.index)
        
        ax.plot_date(dates, self.data['A_FLUX'], '-', 
                     label='0.5--4.0 $\AA$', color='blue', lw=2)
        ax.plot_date(dates, self.data['B_FLUX'], '-', 
                     label='1.0--8.0 $\AA$', color='red', lw=2)
        
        ax.set_yscale("log")
        ax.set_ylim(1e-9, 1e-2)
        ax.set_title(title)
        ax.set_ylabel('Watts m$^{-2}$')
        ax.set_xlabel(datetime.datetime.isoformat(self.data.index[0])[0:10])
        
        ax2 = ax.twinx()
        ax2.set_yscale("log")
        ax2.set_ylim(1e-9, 1e-2)
        ax2.set_yticks((1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2))
        ax2.set_yticklabels((' ','A','B','C','M','X',' '))
        
        ax.yaxis.grid(True, 'major')
        ax.xaxis.grid(False, 'major')
        ax.legend()
        
        # @todo: display better tick labels for date range (e.g. 06/01 - 06/05)
        formatter = matplotlib.dates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(formatter)
        
        ax.fmt_xdata = matplotlib.dates.DateFormatter('%H:%M')
        fig.autofmt_xdate()
        fig.show()
        
    def _get_default_uri(self):
        """Retrieve XRS 2s data from yesterday (most recent data available using
        SEM API) if no other data is specified"""
        today = datetime.datetime.today()
        yesterday = today - datetime.timedelta(days=1)
        
        return self._get_url_for_date_range(yesterday, today)
    
    def _get_url_for_date_range(self, *args, **kwargs):
        """Returns a URL to the GOES data for the specified date.
        
        Parameters
        ----------
        args : TimeRange, datetimes, date strings
            Date range should be specified using either a TimeRange, or start
            and end dates at datetime instances or date strings.
        satellite_number : int
            GOES satellite number (default = 15)
        data_type : string
            Data type to return for the particular GOES satellite. Supported
            types depend on the satellite number specified. (default = xrs_2s) 
        """
        # TimeRange
        if len(args) == 1 and type(args[0]) is sunpy.time.TimeRange:
            start = args[0].start()
            end = args[0].end()
        elif len(args) == 2:
            # Start & End date
            start = sunpy.time.parse_time(args[0])
            end = sunpy.time.parse_time(args[1])
            
        # GOES query parameters
        params = {
            "satellite_number": 15,
            "data_type": "xrs_2s"
        }
        params.update(kwargs)
        
        base_url = 'http://www.ngdc.noaa.gov/goes/sem/getData/goes%d/%s.csv'
        query_str = "?fromDate=%s&toDate=%s&file=true" 
        
        url = (base_url + query_str) % (params['satellite_number'], 
                                        params['data_type'],
                                        start.strftime("%Y%m%d"), 
                                        end.strftime("%Y%m%d"))
        
        return url
    
    def _parse_csv(self, filepath):
        """Parses an GOES CSV"""
        fp = open(filepath, 'rb')
        
        # @todo: check for:
        # "No-Data-Found for the time period requested..." error
        return "", read_csv(fp, sep=",", index_col=0, parse_dates=True)