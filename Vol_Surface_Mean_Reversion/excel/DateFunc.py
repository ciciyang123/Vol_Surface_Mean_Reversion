from collections.abc import Iterable
from datetime import date

def Date2ExcelOrdinal(year,month,day):
    offset = 693594
    current = date(year,month,day)
    n = current.toordinal()
    return n - offset

def ExcelOrdinal2Date(serial):
    offset = 693594
    if isinstance(serial, Iterable):
        if not (isinstance(serial[0], int) or isinstance(serial[0], float)):
            raise TypeError("`serial` should be of type `int`")
        
        res = []
        for iSerial in serial:         
            n = int(iSerial + offset)
            res.append(date.fromordinal(n))
        return res
    else:
        if not (isinstance(serial, int) or isinstance(serial, float)):
            raise TypeError("`serial` should be of type `int`")
        n = int(serial + offset)
        return date.fromordinal(n)


def PythonDate2ExcelOrdinal(pythonDate):
    if isinstance(pythonDate, Iterable):
        if not isinstance(pythonDate[0], date):
            raise TypeError("`pythonDate` should be of type `datetime`")
        
        res = []
        for iDate in pythonDate:         
            res.append(Date2ExcelOrdinal(iDate.year, iDate.month, iDate.day))
        return res
    else:
        if not isinstance(pythonDate, date):
            raise TypeError("`pythonDate` should be of type `datetime`")
        return Date2ExcelOrdinal(pythonDate.year, pythonDate.month, pythonDate.day) 
# -*- coding: utf-8 -*-

