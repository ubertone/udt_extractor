#!/usr/bin/env python3
# -*- coding: UTF_8 -*-
from dateutil.parser import parse


def date_parse(date_str):
	if str(date_str[0:4]).isdigit():
		# Ex : 2019-12-09
		return parse(date_str, yearfirst=True, dayfirst=False)
	else:
		# Ex : 09-12-2019
		return parse(date_str, dayfirst=True, yearfirst=False)
