#!/usr/bin/env python

from utils import utils, inspector
from pyquery import PyQuery as pq

source = pq("http://www.fec.gov/fecig/fecig.shtml")

base_url = "http://www.fec.gov/fecig/"


def run(options):
	links=[]

	content = source('ul')
	for i, c in enumerate(content.items()):
		if i in [5, 7, 8]:
			list_items = c('li').items()
			for li in list_items:
				raw_text = li.text()
				title = raw_text.split(' - ')[0].strip()

				lin = li('a')
				linktext = lin.attr('href')
				link = ''

				if '.pdf' in linktext:
					if 'http' in linktext or 'www' in linktext:
						link = linktext
					else:
						link = base_url + linktext
				if link:
					links.append({'title': title, 'url': link })

#
def report_from(li):
	# process the li, and return a dict with these fields:
	# file_type: 'pdf'
	# inspector: 'fec'
	# inspector_url: 'http://www.fec.gov/fecig/fecig.shtml'
	# agency: 'fec'
	# agency_name: 'Federal Election Commission'
	# title: [you're already getting this]
	# url: [you're already getting this]
	# report_id: [probably the URL of the report]

	# optional:
	# published_on: [left blank]
	# year: [left blank]
	# type: ['audit', 'semiannual', 'report']

	pass

utils.run(run)