#!/usr/bin/env python

import datetime
import logging
import re

from utils import utils, inspector

"""
This file is different in that it doesn't scrape an IG's list of public documents, but rather scrapes the largest public 
repository of otherwise-secret IG reports that were obtained under FOIA -- governmentattic.org.

This has the advantage of being a repeatable process that will sweep in PDFs that are otherwise collected
only via manual processes, thanks to the FOIA efforts of the people that run governmentattic.org

As you might expect, IG reports that can only be obtained via FOIA can be more interesting
and juicy than the ones the government chooses to publish online itself.

Not all of GovAttic's documents are IG reports. By default, this script pulls in only IG reports, but there is a flag,
IG_REPORTS_ONLY, which can simply be set to False to start pulling in all GovernmentAttic documents.
Additionally, it ignores IG reports that don't map to an IG that oversight.garden already keeps track of.

FYI, the Internet Archive backed up governmentattic.org in 2014:
https://archive.org/details/governmentattic.org?sort=-publicdate

-Luke Rosiak
"""


IG_REPORTS_ONLY = True


# <oig_url>
archive = 1930
#govattic page structure isn't based on year

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
# GovernmentAttic's website seems to be hand-coded HTML with no CSS classes, but seems to be updated in a consistent enough way.

#Landing page where GovAttic breaks government agencies down into several groups
CATEGORIES_URL = 'http://www.governmentattic.org/DocumentsCat.html'

#The below maps GovAttic's agency descriptors with inspectors-general's slugs.
#It takes the format: ga_category,ga_agency,ig_short,ig_url,ig_slug
#A GovAttic record will be ignored if it doesn't map to an IG that is in this repo. 
#This mapping was hand-coded based on this file:
#https://raw.githubusercontent.com/konklone/oversight.garden/master/config/inspectors.json

GOVATTIC_MAPPING = """Department of Defense Documents,Department of Defense (DoD),Department of Defense,http://www.dodig.mil/,dod
Department of Defense Documents,Office of the Inspector General (OIG),Department of Defense,http://www.dodig.mil/,dod
Department of Defense Documents,Defense Commissary Agency (DeCA),Department of Defense,http://www.dodig.mil/,dod
Department of Defense Documents,Defense Intelligence Agency (DIA),Defense Intelligence Agency,http://www.dia.mil/About/OfficeoftheInspectorGeneral.aspx,dia
Department of Defense Documents,Defense Threat Reduction Agency (DTRA),Department of Defense,http://www.dodig.mil/,dod
Department of Defense Documents,National,Department of Defense,http://www.dodig.mil/,dod
Department of Defense Documents,United States Air Force,Air Force,http://www.af.mil/InspectorGeneralComplaints.aspx,airforce
Department of Defense Documents,United States Army,Army,https://www.daig.pentagon.mil/,army
Department of Defense Documents,United States Navy,Navy,http://www.secnav.navy.mil/ig/Pages/Home.aspx,navy
Department of Justice Documents,Department of Justice (DOJ),Department of Justice,https://oig.justice.gov/,doj
Department of Justice Documents,Office of the Inspector General,Department of Justice,https://oig.justice.gov/,doj
Executive Branch Departments A-M,Department of Agriculture (USDA),Department of Agriculture,http://www.usda.gov/oig/,agriculture
Executive Branch Departments A-M,Department of Commerce (DOC),Department of Commerce,https://www.oig.doc.gov/Pages/default.aspx,commerce
Executive Branch Departments A-M,Department of Education (ED),Department of Education,https://www2.ed.gov/about/offices/list/oig/index.html,education
Executive Branch Departments A-M,Department of Energy (DOE),Department of Energy,http://energy.gov/ig/office-inspector-general,energy
Executive Branch Departments A-M,Department of Heath and Human Services (DHHS),Department of Health and Human Services,http://oig.hhs.gov/,hhs
Executive Branch Departments A-M,Department of Homeland Security (DHS),Department of Homeland Security,https://www.oig.dhs.gov/,dhs
Executive Branch Departments A-M,United States Secret Service (USSS),Department of Defense,http://www.dodig.mil/,dod
Executive Branch Departments A-M,Department of Housing and Urban Development (HUD),Department of Housing and Urban Development,https://www.hudoig.gov/,hud
Executive Branch Departments A-M,Department of the Interior (DOI),Department of the Interior,https://www.doioig.gov/,interior
Executive Branch Departments A-M,Department of Labor (DOL),Department of Labor,https://www.oig.dol.gov/,labor
Executive Branch Departments N-Z,Department of State,Department of State,https://oig.state.gov/,state
Executive Branch Departments N-Z,Department of Transportation (DOT),Department of Transportation,https://www.oig.dot.gov/,dot
Executive Branch Departments N-Z,Federal Aviation Administration (FAA),Department of Transportation,https://www.oig.dot.gov/,dot
Executive Branch Departments N-Z,Department of the Treasury,Department of the Treasury,http://www.treasury.gov/about/organizational-structure/ig/,treasury
Executive Branch Departments N-Z,Bureau of Engraving and Printing (BEP),Department of the Treasury,http://www.treasury.gov/about/organizational-structure/ig/,treasury
Executive Branch Departments N-Z,Treasury Inspector General for Tax Administration (TIGTA),Treasury IG for Tax Administration,https://www.treasury.gov/tigta/,tigta
Executive Branch Departments N-Z,Department of Veterans Affairs (VA),Department of Veterans Affairs,http://www.va.gov/oig,va
White House Offices,Office of the Director of National Intelligence (ODNI),,,
Legislative Agencies,Architect of the Capitol (AOC),Architect of the Capitol,http://www.aoc.gov/oig/office-inspector-general,architect
Legislative Agencies,Government Accountability Office (GAO),Government Accountability Office,http://www.gao.gov/about/workforce/ig.html,gao
Legislative Agencies,Library of Congress (LOC),Library of Congress,https://www.loc.gov/about/office-of-the-inspector-general/,loc
Independent Federal Agencies A-M,The,,,
Independent Federal Agencies A-M,Central Intelligence Agency (CIA),Central Intelligence Agency,https://www.cia.gov/offices-of-cia/inspector-general,cia
Independent Federal Agencies A-M,Commodity Futures Trading Commission (CFTC),Commodity Futures Trading Commission,http://www.cftc.gov/About/OfficeoftheInspectorGeneral/index.htm,cftc
Independent Federal Agencies A-M,Consumer Product Safety Commission (CPSC),Consumer Product Safety Commission,https://www.cpsc.gov/en/About-CPSC/Inspector-General/,cpsc
Independent Federal Agencies A-M,Corporation for National and Community Service (CNCS),Corporation for National and Community Service,http://www.cncsoig.gov/,cncs
Independent Federal Agencies A-M,Council of Inspectors General on Integrity and Efficiency (CIGIE),Council of Inspectors General on Integrity and Efficiency (CIGIE),https://www.ignet.gov/,cigie
Independent Federal Agencies A-M,The Denali Commission,Denali Commission,http://oig.denali.gov/,denali
Independent Federal Agencies A-M,Environmental Protection Agency (EPA),Environmental Protection Agency,http://www.epa.gov/oig,epa
Independent Federal Agencies A-M,Equal Employment Opportunity Commission (EEOC),Equal Employment Opportunity Commission,https://oig.eeoc.gov/,eeoc
Independent Federal Agencies A-M,Export-Import Bank of the United States (Ex-Im Bank),Export-Import Bank,http://www.exim.gov/about/oig,exim
Independent Federal Agencies A-M,Federal Communications Commission (FCC),Federal Communications Commission,https://www.fcc.gov/office-inspector-general,fcc
Independent Federal Agencies A-M,Federal Deposit Insurance Corporation (FDIC),Federal Deposit Insurance Corporation,https://www.fdicig.gov/,fdic
Independent Federal Agencies A-M,Federal Election Commission,Federal Election Commission,http://www.fec.gov/fecig/fecig.shtml,fec
Independent Federal Agencies A-M,Federal Housing Finance Agency (FHFA),Federal Housing Finance Agency,http://fhfaoig.gov/,fhfa
Independent Federal Agencies A-M,Federal Labor Relations Authority (FLRA),Federal Labor Relations Authority,https://www.flra.gov/OIG,flra
Independent Federal Agencies A-M,Federal Reserve System,Federal Reserve/CFPB,https://oig.federalreserve.gov/,fed
Independent Federal Agencies A-M,Federal Trade Commission (FTC),Federal Trade Commission,https://www.ftc.gov/about-ftc/office-inspector-general,ftc
Independent Federal Agencies A-M,General Services Administration (GSA),General Services Administration,https://www.gsaig.gov/,gsa
Independent Federal Agencies N-Z,National Archives and Records Administration (NARA),National Archives,https://www.archives.gov/oig/,archives
Independent Federal Agencies N-Z,National Aeronautics and Space Administration (NASA),NASA,https://oig.nasa.gov/,nasa
Independent Federal Agencies N-Z,National Credit Union Administration (NCUA),National Credit Union Administration,http://www.ncua.gov/about/Leadership/Pages/page_oig.aspx,ncua
Independent Federal Agencies N-Z,National Endowment for the Humanities (NEH),National Endowment for the Humanities,http://www.neh.gov/about/oig,neh
Independent Federal Agencies N-Z,National Labor Relations Board (NLRB),National Labor Relations Board,https://www.nlrb.gov/who-we-are/inspector-general,nlrb
Independent Federal Agencies N-Z,National Railroad Passenger Corporation (AMTRAK),Amtrak,https://www.amtrakoig.gov/,amtrak
Independent Federal Agencies N-Z,National Science Foundation (NSF),National Science Foundation,https://www.nsf.gov/oig/,nsf
Independent Federal Agencies N-Z,Nuclear Regulatory Commission (NRC),Nuclear Regulatory Commission,http://www.nrc.gov/insp-gen.html,nrc
Independent Federal Agencies N-Z,Office of Personnel Management (OPM),Office of Personnel Management,https://www.opm.gov/our-inspector-general/,opm
Independent Federal Agencies N-Z,Office of the Special Inspector General for Afghanistan,Special IG for Afghanistan Reconstruction,https://www.sigar.mil/,sigar
Independent Federal Agencies N-Z,Office of the Special Inspector General for Iraq Reconstruction (SIGIR),Special IG for Iraq Reconstruction,http://www.sigir.mil/,sigir
Independent Federal Agencies N-Z,Overseas Private Investment Corporation (OPIC),,,
Independent Federal Agencies N-Z,The Peace Corps,Peace Corps,http://www.peacecorps.gov/about/inspgen/,peacecorps
Independent Federal Agencies N-Z,The Railroad Retirement Board,Railroad Retirement Board,http://www.rrb.gov/oig/,rrb
Independent Federal Agencies N-Z,Securities and Exchange Commission (SEC),Securities and Exchange Commission,http://www.sec.gov/oig,sec
Independent Federal Agencies N-Z,Special Inspector General for the Troubled Asset Relief Program (SIGTARP),Special IG for TARP,https://www.sigtarp.gov/Pages/home.aspx,sigtarp
Independent Federal Agencies N-Z,Small Business Administration (SBA),Small Business Administration,https://www.sba.gov/office-of-inspector-general,sba
Independent Federal Agencies N-Z,Social Security Administration (SSA),Social Security Administration,http://oig.ssa.gov,ssa
Independent Federal Agencies N-Z,Tennessee Valley Authority (TVA),Tennessee Valley Authority,http://oig.tva.gov/,tva
Independent Federal Agencies N-Z,US Agency for International Development (USAID),U.S. Agency for International Development,https://oig.usaid.gov/,usaid
Independent Federal Agencies N-Z,US Postal Service (USPS),U.S. Postal Service,https://uspsoig.gov/,usps
Government Corporations,Legal Services Corporation,Legal Services Corporation,https://www.oig.lsc.gov/,lsc
Government Corporations,Corporation for National and Community Service (CNCS),Corporation for National and Community Service,http://www.cncsoig.gov/,cncs
Government Corporations,Pension Benefit Guaranty Corporation (PBGC),Pension Benefit Guaranty Corporation,http://oig.pbgc.gov/,pbgc
State Records / Miscellaneous Records / Interagency Records,Records of State/CITY Agencies,,,
State Records / Miscellaneous Records / Interagency Records,Miscellaneous Records,,,
State Records / Miscellaneous Records / Interagency Records,Smithsonian Institution (SI),Smithsonian Institute,http://www.si.edu/OIG,smithsonian"""

#store this as tuples above for ease of editing, but turn it into a dict for use.
GOVATTIC_MAPPING_DICT = {}
for line in GOVATTIC_MAPPING.splitlines():
  (ga_category,ga_agency,ig_short,ig_url,ig_slug) = line.strip().split(',')
  GOVATTIC_MAPPING_DICT[(ga_category,ga_agency)] = (ig_short,ig_url,ig_slug)

def remove_linebreaks(s):
  #lots of weird tabs, etc. inside HTML strings. would replace all at once, but since utils.beautifulsoup_from_url
  #is taking the html straight to soup, we'll do it individually for the fields we need
  return inspector.sanitize(s.replace('\n','').replace('\t','').replace('\r',''))

def run(options):
  year_range = inspector.year_range(options, archive)

  #loop through sections (Executive Branch Departments A-M, etc)
  category_doc = utils.beautifulsoup_from_url(CATEGORIES_URL)
  category_links = category_doc.findAll('a')
  for category_link in category_links:
    #these are the detail pages with lots of PDFs. they are grouped according to agency name
    category_name = remove_linebreaks(category_link.text).strip()
    doc = utils.beautifulsoup_from_url(category_link['href'])
    agency = ''
    for result in doc.findAll('p'):
      if result.font and result.font.get('color')=="#993333": 
        #this is an agency name
        agency = remove_linebreaks(result.font.text).strip()
      else:
        #this is a report from that agency
        report = report_from(result, category_name, agency, year_range)
        if report:
          inspector.save_report(report)
        

# extract a dict of details that are ready for inspector.save_report().
def report_from(result, category_name, agency, year_range):

  #ignore if it's not in our agency string->slug mapping or if it's in our mapping and has null instead of a slug.
  #that means it doesn't come from an agency whose IG we track; it may be a document from a
  #local government, etc.
  if (category_name,agency) not in GOVATTIC_MAPPING_DICT or GOVATTIC_MAPPING_DICT[(category_name,agency)][-1]=='':
    return
  (ig_short,ig_url,ig_slug) = GOVATTIC_MAPPING_DICT[(category_name,agency)]

  a = result.find('a')
  if not a:
    if result.p and result.p.font and result.p.font.find('a'):
      a = result.p.font.find('a')
  if not a: 
    #there's no link, so this must just be some explanatory text, such as the footer
    return
  report_url = a['href']

  #these will be stored in folders with documents scraped by the official IG scrapers, so
  #use the governmentattic url as slug to assure no conflict.
  report_id = inspector.slugify(report_url.replace('http://www.',''))

  title = remove_linebreaks(a.text).strip()
  text = remove_linebreaks(result.text)
  r = re.compile('\[(?:.*\s-?|)(\d{2})-+(\w{3,12})-+(\d{4})')
  datematch = r.search(text)
  published_on = None
  datestring = None
  if datematch:
    datestring = '-'.join(datematch.groups()) #'01-Mar-2015
    datestring = datestring.replace("-Sept-", "-Sep-")
    try:
      published_on = datetime.datetime.strptime(datestring, '%d-%b-%Y')
    except:    
      published_on = None    
    if not published_on:    
      try:
        published_on = datetime.datetime.strptime(datestring, '%d-%B-%Y')
      except:
        published_on = None
  if not published_on:
    inspector.log_no_date(report_id, title, report_url)
    return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  #ignore documents that are interesting FOIAs but are not IG reports.
  #if you want to scrape IG and agency documents, set IG_REPORTS_ONLY=False
  if IG_REPORTS_ONLY and 'OIG' not in title and 'inspector general' not in title.lower():
    logging.debug("[%s] Skipping, not an IG report." % title)
    return

  report = {
    'inspector': ig_slug,     # Store these with their natively-scraped counterparts, not in a govattic-specific place
    'inspector_url': ig_url,  
    'agency': ig_slug,        # Agency and IG slug will be the same
    'agency_name': ig_short,  # Take short name of the IG as the agency name. I think this should work.
    'report_id': report_id,  
    'url': report_url,  
    'title': title,  
    'type': 'FOIA - GovernmentAttic.org', # Type of report (default to 'other')
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d") #date published to GovAttic, not released by IG  
  }

  return report

utils.run(run) if (__name__ == "__main__") else None



