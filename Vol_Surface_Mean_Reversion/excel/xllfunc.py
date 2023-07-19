from collections.abc import Iterable
from DateFunc import PythonDate2ExcelOrdinal
from datetime import date

COUNT = 0

def RunXll(excel, funcName, *args):
    global COUNT
    args = list(args)
    # date to serial conversion
    for i, arg in enumerate(args):
        if isinstance(arg, Iterable) and isinstance(arg[0], date):
            args[i] = PythonDate2ExcelOrdinal(arg);
        elif isinstance(arg, date):
            args[i] = PythonDate2ExcelOrdinal(arg);
    
    if len(args) == 0:
        res = excel.Run(funcName, *args)
    elif args[0] is None:
        res = excel.Run(funcName, "PytObj_" + str(COUNT), *(args[1:]))
        COUNT += 1
    else:
        res = excel.Run(funcName, *args)
    return res# -*- coding: utf-8 -*-

