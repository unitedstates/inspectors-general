#!/usr/bin/env python

from utils import utils, inspector
from bs4 import BeautifulSoup
from datetime import datetime

# options:
#   component: limit to a specific component. See COMPONENTS dict at bottom.


def run(options):
  component = options.get('component', None)
  if component:
    components = [component]
  else:
    components = COMPONENTS.keys()

  for component in components:
    print "## Fetching reports for component %s" % component
    url = url_for(options, component)
    body = utils.download(url)

    doc = BeautifulSoup(body)

    results = doc.select("table.contentpaneopen table[border=1] tr")
    # accept only trs that look like body tr's (no 'align' attribute)
    #   note: HTML is very inconsistent. cannot rely on thead or tbody
    results = filter(lambda x: x.get('align', None) is None, results)

    count = 0
    for result in results:
      # print result.select("td")[2].select("p a")[0].text
      # report = report_from(result)
      # inspector.save_report(report)
      count += 1
    print "## Fetched %i reports for component %s\n\n" % (count, component)

def url_for(options, component):
  base = "http://www.oig.dhs.gov/index.php?option=com_content&view=article"
  return "%s&id=%s&Itemid=%s" % (base, COMPONENTS[component][0], COMPONENTS[component][1])


# Component handle, with associated ID and itemID query string params
#   Note: I believe only the ID is needed.
# Not every component is an agency. Some of these will be collapsed into 'dhs'
#   for a report's 'agency' field.
# Some additional info on DHS components: https://www.dhs.gov/department-components
COMPONENTS = {
  'secret_service': (58, 49),
  'coast_guard': (19, 48),
  'uscis': (20, 47),
  'tsa': (22, 46),
  'ice': (24, 44),
  'fema': (25, 38),
  'cbp': (26, 37),
  'dhs_other': (59, 50),
  'dhs_mgmt': (23, 45),
  'dhs_cigie': (168, 150), # Council of the Inspectors General on Integrity and Efficiency
}

# 'Oversight areas' as organized by DHS. This is unused now, but
# could be used to run over the lists and associate a category with
# reports previously identified when running over each component.
# values are associated IT and itemID query strinhg params.
#   Note: I believe only the ID is needed.
AREAS = {
  'Border Security': (60, 30),
  'Counterterrorism': (61, 31),
  'Cybersecurity': (62, 32),
  'Disaster Preparedness, Response, Recovery': (63, 33),
  'Immigration': (64, 34),
  'Management': (33, 51),
  'Transportation Security': (66, 35),
}

utils.run(run)