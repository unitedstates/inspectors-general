#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# - Some documents don't have dates, in that case today's date is used
# - Some forms, marked index are one html document spread across several links,
# I go through all the links so that we get the most descriptive agency name
# - I added language information since there were English and Spanish docs
# - There are html and pdfs for the same docs so all the urls are tracked in urls

import re
from bs4 import BeautifulSoup
from datetime import datetime, date
from utils import utils, inspector

# accumulates information on reports as they're seen
report = {}

base_url = "http://www.justice.gov"

agency_decoder = {
    "Department of Justice":["Department of Justice", "doj"],
    "United States Marshals Service (USMS)": [ "United States Marshals Service", "USMS"],
    "Office of Justice Programs (OJP)": ["Office of Justice Programs", "OJP"],
    "Federal Bureau of Prisons (BOP)": ["Federal Bureau of Prisons", "BOP"],
    "Federal Bureau of Investigation (FBI)": ["Federal Bureau of Investigation", "FBI"],
    "Combined DNA Index System (CODIS)": ["Combined DNA Index System", "CODIS"],
    "Executive Office for U. S. Attorneys (EOUSA)": ["Executive Office for U. S. Attorneys", "EOUSA"],
    "Office of Community Oriented Policing Services (COPS)": ["Office of Community Oriented Policing Services", "COPS"],
    "Intergovernmental Agreements for Detention Space (IGAs)": ["Intergovernmental Agreements for Detention Space", "IGAs"],
    "Drug Enforcement Administration (DEA)": ["Drug Enforcement Administration", "DEA"],
    "Bureau of Alcohol, Tobacco, Firearms and Explosives (ATF)": ["Bureau of Alcohol, Tobacco, Firearms and Explosives", "ATF"],
    "Office on Violence Against Women (OVW)": ["Office on Violence Against Women", "OVW"],
    "Immigration and Naturalization Service (INS) – 1994 to 2003": ["Immigration and Naturalization Service", "INS"],
    "United States Marshals Service (USMS)": ["United States Marshals Service", "USMS"],
  }

not_agency = (
  "Office of Justice Programs (OJP)", "Contracts", "Special Reports",
  "Other DOJ Components and Reports Encompassing More Than One DOJ Component",
  "Equitable Sharing", "Offices, Boards and Divisions (OBDs)"
)

# not all the reports have a convenient date field immediately prior.
# So, we'll just go back in sibling order until we find the h3 we need.
def year_for(blurb):
  h3 = None
  for sibling in blurb.previous_siblings:
    if sibling.name == "h3":
      h3 = sibling
      break
  return int(h3.text)

def extract_info(content, directory, year):
  # goes through each agency or content bucket
  if directory in not_agency:
    agency = "doj"
    agency_name = "Department of Justice"
  elif directory[:11] == "Immigration":
    agency = "ins"
    agency_name = "Immigration and Naturalization Service"
  else:
    agency = agency_decoder[directory][1]
    agency_name = agency_decoder[directory][0]

  candidates = content[-1].find_all("p")
  print "Found %i candidate reports on \"%s\"" % (len(candidates), directory)
  blurbs = []

  # if we're limiting to a specific year, find only the <p>'s
  # following the <h3> with the year in it
  if year:
    for blurb in candidates:
      report_year = year_for(blurb)
      if report_year == year:
        blurbs.append(blurb)
    print "Preparing to fetch %i reports for %i" % (len(blurbs), year)
  else:
    blurbs = candidates
    print "Preparing to fetch %i reports for all years" % len(blurbs)

  for b in blurbs:
    # date
    # finding new dates that are just above the old ones

    # this is the format of the newest entries and the easiest to get
    x = b.previous_sibling
    y = b.previous_sibling.previous_sibling
    try:
      if y['class'] == ['date']:
        date_string = y.string
      else:
        date_string = None
    except:
       date_string = None

    # finding older dates that are at the end of the text
    if date_string == None:
      try:
        date_string = b.get_text()
      except:
        date_string = None

    if date_string is not None:
      # get rid of extra stuff that is not the date
      date_text = re.sub(r'\([^)]*\)', '', date_string)
      date_text = re.sub(r'\[(.*?)\]', '', date_text)
      # chop up the string, the last part should be the date
      date_chopped = date_text.rsplit(',')
      day = date_chopped[-1]
      # cleaning
      date_string = day.strip()
      date_string = date_string.replace("  ", " ")
      day = day.strip()

      # this is a date written out with a comma
      if day.isdigit():
        date_string = date_chopped[-2] + "," + date_chopped[-1]

    # check for missing commas
    try:
      date_string = datetime.strptime(date_string, "%B %d %Y")
      date_string = datetime.strftime(date_string, "%B %d, %Y")
    except ValueError:
      pass

    # for dates without a day
    if date_string is not None:
      date_string = date_string.strip()
      if "," not in date_string:
        date_test = date_string.replace(" ", " 1, ")
        try:
          d = datetime.strptime(date_test, "%B %d, %Y")
          date_string = date_test
        except ValueError:
          pass

    # going through each link in a paragraph
    for l in b.find_all("a"):
      # most cases pass this test
      try:
        date = datetime.strptime(date_string, "%B %d, %Y")
      # these ones got to a coding purgatory called odd_link
      except ValueError:
        info = odd_link(b, date_string, l, directory, )
        # this should give better titles than "pdf" or "Press Release"
        real_title = info["real_title"]
        date_string = info["date_string"]
        # these are links to things that are not reports
        if real_title == "ignore" and date_string == "ignore":
          break
        if "," not in date_string:
          date_string = date_string.strip()
          date_string = date_string.replace(" ", " 1, ")
          date = datetime.strptime(date_string, "%B %d, %Y")

      year = datetime.strftime(date, "%Y")
      published_on = datetime.strftime(date, "%Y-%m-%d")

      # trying to get the most descriptive title
      # I go from the best methods to fall back and override exceptions
      try:
        string_title = b.text
      except:
        string_title = b.string

      if string_title == None:
        string_title = b.contents
        if "<a href=" in str(string_title):
          string_title = b.contents[0]

      link = l.get("href")
      if link != None:
        # title
        try:
          title = l.text
        except:
          title = l.string
        if title == "HTML" or title == "PDF":
          title = string_title

        # in some cases the title is a heading a few elements up this gets passed in odd link
        if "real_title" in locals():
          if real_title != None:
            title = real_title

        if title == 'id="content" name="content">':
          title =  b.string
          if title == None:
            title = b.text

        try:
          title = title.strip()
          title = title.replace('\n', "")
          title = title.replace('\r', "")
        except:
          pass

        file_type = find_file_type(link)
        if file_type == "ignore":
          break

        if title == None:
          title = b.string

        # formating links consistently
        if link[:1] != "/":
          link = "/" + link
        # id
        doc_id = str(link)[1:-4]
        if link[:11] == "oig/reports":
          doc_id = doc_id[16:]

        #these docs are one report where the page has a table of contents with links to content
        if "/index" in link:
          indexed = True
        else:
          indexed = False

        # creating ids
        # there may be a better way to do this but I am just taking out all the things that are not the id
        url_extras = ( "/final", "/fullpdf", "/ins_response", "oig/special/", "USMS/", "plus/", "oig/grants/", "oig/reports/", "EOUSA/", "BOP/", "ATF/", "COPS/", "FBI/", "OJP/", "INS/", "DEA/", "OBD", "/analysis", "/report", "/PDF_list", "/full_report", "/full", "_redacted", "oig", "r-", "/response", "/listpdf", "/memo", "/fullreport", "/Final", "/extradition", "/oig", "/grants", "/index")
        for n in url_extras:
          if n in doc_id:
            doc_id = doc_id.replace(n, "")

        if doc_id[:1] == "/":
          doc_id = doc_id[1:]

        if "/" in doc_id:
          if doc_id[4:5] == "/":
            if doc_id[:2] == "19" or doc_id[:2] == "20":
              doc_id = doc_id[5:]

        # some weird issues I hard coded
        special_cases = {"a0118/au0118":"a0118", "a0207/0207":"a0207",  }
        if doc_id in special_cases.keys():
          doc_id = special_cases[doc_id]

        if "spanish" in link:
          language = "Spanish"
        else:
          language = "English"

        # url
        if link[:5] == "/oig/":
          url = base_url + link
        else:
          url = base_url + "/oig/reports" + link

        if report.has_key(doc_id):
          if file_type == "pdf":
            # current and previous file pdf
            if report[doc_id]["file_type"] == "pdf":
              report[doc_id]["categories"].append(directory)
            # current file a pdf, old file html
            else:
              report[doc_id]["file_type"] = "pdf"
              report[doc_id]["url"] = url
              report[doc_id]["categories"].append(directory)
          else:
            # current file html old file pdf OR both files html
            report[doc_id]["categories"].append(directory)

          # add url if new
          for n in report[doc_id]["urls"]:
            if n.has_key(url):
              old_url = True
          if not "old_url" in locals():
            report[doc_id]["urls"].append({
              "url":url,
              "file_type": file_type,
              "indexed": indexed,
              })

          # finding the most descriptive name for cross-listed docs
          if report[doc_id]["agency"] == "doj" and agency != "doj":
            report[doc_id]["agency"] = agency
            report[doc_id]["agency_name"] = agency_name

        # Adding new document
        else:
          report[doc_id] = {
            "report_id": doc_id,
            "inspector": "doj",
            "inspector_url": "http://www.justice.gov/oig/reports/",
            "agency": agency,
            "agency_name": agency_name,
            "url": url,
            "title": title,
            "file_type": file_type,
            "categories": [directory,],
            "urls": [{
                "url":url,
                "file_type": file_type,
                "indexed": indexed,
              }],
            "published_on": published_on,
            "year": year,
            # perhaps elaborate on this later
            "type": type_for(title),
            "language": language,
            }


def find_file_type(url):
  if url[-3:] == "pdf":
    file_type = "pdf"
  elif url[-3:] == "htm":
    file_type = "html"
  elif url[-4:] == "html":
    file_type = "html"
  else:
    # these include a few navigation links
    file_type = "ignore"
  return file_type

def date_format(date):
  date = str(date)
  date = re.sub(r'\([^)]*\)', '', date)
  date = re.sub(r'\[(.*?)\]', '', date)
  date = date.rsplit(',')
  date = str(date[-2]).strip() + ", " + str(date[-1]).strip()
  date_string = date
  return date_string

# said purgatory for odd links
def odd_link(b, date, l, directory):
  text = b.get_text()
  # not links to docs
  try:
    link = l.get("href")
  except:
    pass

  # these are not documents
  if "link" in locals():
    if link[-4:] == ".gov":
      return {"date_string":"ignore", "real_title":"ignore"}
    elif link[-5:] == ".gov/":
      return {"date_string":"ignore", "real_title":"ignore"}
  text = b.get_text()

  #section for documents without dates:
  if date != None:
    if date.strip() == "Alleged Deception of Congress: The Congressional Task Force on Immigration Reform's Fact-Finding Visit to the Miami District of INS in June 1995":
      return{"date_string": "June 1, 1996", "real_title": "Alleged Deception of Congress: The Congressional Task Force on Immigration Reform's Fact-Finding Visit to the Miami District of INS in June 1995"}
    if date == "Audit Report GR-30-00-001":
      return{"date_string": "November 1, 2000", "real_title":"McMechen, West Virginia Police Department, Audit Report GR-30-00-001"}
    # no date, one other entry, giving it the same date
    if date == "Georgia's Department of Corrections":
      return{"date_string": "November 1, 2000", "real_title":"United States Marshals Service Cost Proposal for the Intergovernmental Service Agreement for Detention Facilities with the City of Atlanta, Georgia’s Department of Corrections"}
    # confirmed no dates for these
    no_dates = ("Audit Report GR-40-99-014", "Audit Report GR-40-99-011", "Evaluation and Inspections Report I-2000-021", "Evaluation and Inspections Report I-2000-018", "Audit Report 99-03")
    if date.strip() in no_dates:
      date_string = datetime.now()
      date_string = datetime.strftime(date_string, "%B %d, %Y")
      return{"date_string": date_string, "real_title": text}
    # Intergovernmental Agreements for Detention Space External Reports don't always have dates, not even on the documents, using today
    if directory == "Intergovernmental Agreements for Detention Space (IGAs)":
      date_string = datetime.now()
      date_string = datetime.strftime(date_string, "%B %d, %Y")
      return{"date_string": date_string, "real_title": text}

  # need to get rid of this to process
  if "Released Publicly" in text:
    date = text
    date = re.sub(r'\([^)]*\)', '', date)
    date = re.sub(r'\[(.*?)\]', '', date)
    date = date.replace("Released Publicly", '')
    date_chopped = date.rsplit(',')
    day = date_chopped[-1]
    date = day.strip()
    if day.isdigit():
        date_string = date_chopped[-2] + "," + date_chopped[-1]
    if "," not in date:
      date = date.strip()
      date = date.replace(" ", " 1, ")
    return{"date_string": date, "real_title": text}

  if "Revised" in text:
    date = text
    date = re.sub(r'\([^)]*\)', '', date)
    date = re.sub(r'\[(.*?)\]', '', date)
    date = date.replace("Revised", '')
    date_chopped = date.rsplit(',')
    day = date_chopped[-1]
    date = day.strip()
    if day.isdigit():
        date_string = date_chopped[-2] + "," + date_chopped[-1]
    if "," not in date:
      date = date.strip()
      date = date.replace(" ", " 1, ")
    return{"date_string": date, "real_title": text}

  if date != None:
    date = date.strip
    # case 1, date is wrong because it is in the paragraph and completely written out
    try:
        date =  b.string
        date_string = date_format(date)
        title = b.string
    except:
      # these are lists of links that are different variants of the same report in a list
      # case where there is a list in a paragraph tag
      listy = b.parent.parent
      text = str(listy.previous_sibling)
      title = text

      # case where there is a paragraph above a list
      if len(text) < 4:
        listy = b.parent.parent
        text = listy.previous_sibling.previous_sibling
        title = str(text)[3:-4]
      date = re.sub(r'\([^)]*\)', '', title)
      date = re.sub(r'\[[^)]*\]', '', date)
      date = date.rsplit(',')
      date_string = date[-1]
      date_string = date_string.strip()
      if "," not in date_string:
        date_string = date_string.replace(" ", " 1, ")

  info = {"real_title":title, "date_string": date_string, }
  return(info)

# adding types bases on the USPS
def type_for(original_type):
  original = original_type.lower()
  if "audit" in original:
    return "audit"
  elif "testimony" in original:
    return "testimony"
  elif "press release" in original:
    return "press"
  elif "research" in original:
    return "research"
  elif "sarc" in original:
    return "interactive"
  elif "report to congress" in original:
    return "congress"
  else:
    return "unknown"

def get_content(url):
  page = utils.download(url)
  page = BeautifulSoup(page)
  content = page.select(".content-left")
  return content


def run(options):

  # provide a specific year, or 'all' -- no year means current year
  year = options.get('year', datetime.now().year)
  if year == "all":
    year = None
  else:
    year = int(year)


  # Hit the main landing page, get links to each component's landing page.
  starting_point = "http://www.justice.gov/oig/reports/"
  content = get_content(starting_point)
  source_links = {}
  for c in content:
    links = c.find_all("a")
    for l in links:
      name = l.string
      link = base_url + l.get("href")
      source_links[link] = name

  # For each component's landing page, run the processor ove rit
  keys = source_links.keys()
  keys.sort()
  for link in keys:
    content = get_content(link)
    extract_info(content, source_links[link], year)

  for key in report.keys():
    inspector.save_report(report[key])

utils.run(run)