
# This Python file uses the following encoding: utf-8
# Recovery docs have their own system for ids. 
# Annual reports before 2006 are not included because of broken links and unique formatting 
# Still need a plan for "indexed" forms
import re
from bs4 import BeautifulSoup
from datetime import datetime, date
from utils import utils, inspector

report = {}
source_links = {}
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

base_url = "http://www.justice.gov"
not_agency = ("Office of Justice Programs (OJP)", "Contracts", "Special Reports", "Other DOJ Components and Reports Encompassing More Than One DOJ Component","Equitable Sharing", "Offices, Boards and Divisions (OBDs)")
index_links = ["http://www.justice.gov/oig/reports/2012/s1209.htm"]


def extract_info(content, directory):
  print "\n\n\nStarting loop for--- ", directory
  if directory in not_agency:
    agency = "doj"
    agency_name = "Department of Justice"
  elif directory[:11] == "Immigration":
    agency = "ins"
    agency_name = "Immigration and Naturalization Service"
  else:
    agency = agency_decoder[directory][1]
    agency_name = agency_decoder[directory][0]
  
  for c in content:
    blurbs = c.find_all("p")
  
  for b in blurbs:
    print "starting blurb loop--\n", b, "\n\n"
    # date
    x = b.previous_sibling
    y = b.previous_sibling.previous_sibling
    print b
    try:
      if y['class'] == ['date']:
        date_string = y.string
      print date, 0
    except:
      date_string = None

    try:
      if x['class'] == ['date']:
        date_string = x.string
        print date, .5
    except:
      pass

    if date_string == None:
      try:
        date = b.string
        date = re.sub(r'\([^)]*\)', '', date)
        date = re.sub(r'\[(.*?)\]', '', date)
        date_chopped = date.rsplit(',')
        date = date_chopped[-1]
        date_string = date.strip()
        date_string = date_string.replace("  ", " ")
        print date, 1
        date = date.strip()
        if date.isdigit():
          date_string = date_chopped[-2] + "," + date_chopped[-1]
          print date_string, "re-combined"
        if "," not in date_string:
          date_string = date_string.replace(" ", " 1, ")
        print date_string, "------86"
      except:
        date_string = None
        print date, 2

    # going through each link in a paragraph
    for l in b.find_all("a"):
      try:
        date = datetime.strptime(date_string, "%B %d, %Y")
      except:
        print "\n\n", "GOING ODD", "\n\n"
        info = odd_link(b, date, l, directory)
        real_title = info["real_title"]
        date_string = info["date_string"]
        if date_string != "ignore":
          print date_string, b, "\n\n", directory
          date = datetime.strptime(date_string, "%B %d, %Y")

      print date, "WHY U NO WORK"
      if date_string != "ignore":
        year = datetime.strftime(date, "%Y")
        published_on = datetime.strftime(date, "%Y-%m-%d")
      
      string_title = b.string
      if b.string == None:
        string_title = b.contents
        if "<a href=" in str(string_title):
          string_title = b.contents[0]

      #for l in b.find_all("a"):
      link = l.get("href")
      if link != None:
        # title
        title = l.string
        if title == "HTML" or title == "PDF":
          title = string_title
        if title == None:
          #this doesn't work
          if str(b) == '<p><a href="/oig/press/2012/2012_09_25.pdf">Report on Activities Under Section 702 of the <em>FISA Amendments Act of 2008</em></a></p>':
            title = "Report on Activities Under Section 702 of the FISA Amendments Act of 2008"
        
        if "real_title" in locals():
          title = real_title

        if "[" in title[-5:]:
          title = title.replace("[", '')
        title = title.strip()

        # formating links consistently
        if link[:1] != "/":
          link = "/" + link 
        # id
        doc_id = str(link)[1:-4]
        if link[:11] == "oig/reports":
          doc_id = doc_id[16:]

        #these docs are one report where the page has a table of contents with links to content 
        if "/index" in link:
          index_links.append(link)
          indexed = True
        else:
          indexed = False

        # there may be a better way to do this but I am just taking out all the things that are not the id
        url_extras = ( "/final", "/fullpdf", "/ins_response", "oig/special/", "USMS/", "plus/", "oig/grants/", "oig/reports/", "EOUSA/", "BOP/", "ATF/", "COPS/", "FBI/", "OJP/", "INS/", "DEA/", "OBD", "/analysis", "/report", "/PDF_list", "/full_report", "/full", "_redacted", "oig", "r-", "/response", "/listpdf", "/memo", "/fullreport", "/Final", "/extradition")
        for n in url_extras:
          if n in doc_id:
            doc_id = doc_id.replace(n, "")

        if doc_id[:1] == "/":
          doc_id = doc_id[1:]

        if "/" in doc_id:
          if doc_id[4:5] == "/":
            if doc_id[:2] == "19" or doc_id[:2] == "20":
              doc_id = doc_id[5:]
        
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
        # file_type
        file_type = find_file_type(link)

        if file_type != "ignore":
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
              "type": "report",
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


def odd_link(b, date, l, directory):
  print date, "hello", b
  print directory, 

  try:
    link = l.get("href")
    if link[-4:] == ".gov":
      return {"date_string":"ignore", "real_title":"ignore"}
  except:
    pass
  #check for missing commas
  try:
    print "trying"
    date_string = datetime.strptime(date, "%B %d %Y")
    date_string = datetime.strftime(date_string, "%B %d, %Y")
    t = str(b)
    print date_string
    return{"date_string": date_string, "real_title": t}
  except:
    pass
  # for when there are line breaks in title
  try:
    print "Starting date in p search, odd"
    date = str(b)[4:-4]
    print date, "string version"
    date = re.sub(r'\([^)]*\)', '', date)
    date = re.sub(r'\[(.*?)\]', '', date)
    print date, "Cleaner date"
    date = date.replace(" [", "")
    date = date.replace("[", "")
    date_chopped = date.rsplit(',')
    print "date chunks ----  ", date_chopped
    date = date_chopped[-1]
    date_string = date
    t = str(b)
    date = date.strip()
    if date.isdigit():
      date_string = date_chopped[-2] + "," + date_chopped[-1]
      print date_string, "re-combined"
    test = datetime.strptime(date_string, "%B %d, %Y")
    print test
    return{"date_string": date_string, "real_title": t}

  except:
    pass

  if "Released Publicly" in date:
    date =  date[18:].strip()
    date = date.replace(" ", " 1, ")
    t = str(b)
    t = t[4:-4]
    return{"date_string": date, "real_title": t}
  if "(Unclassified Summary)" in date:
    date = str(b)
    date = date[4:-4]
    date = re.sub(r'\([^)]*\)', '', date)
    date = re.sub(r'\[(.*?)\]', '', date)
    date = date.rsplit(',')
    date = date[-1]
    if "\r\n " in date:
      date = re.sub(r'\r\n ', '', date)
      date = date.strip()
      date = date.replace(" ", " 1, ")
    t = str(b)
    t = t[4:-4]
    t = re.sub(r'\[(.*?)\]', '', t)
    return{"date_string": date, "real_title": t}
  if "Revised" in date:
    date = date[7:] 
    date = date.strip()
    date_string = date.replace(" ", " 1, ")
    real_title = str(b)
    return{"date_string": date_string, "real_title": real_title}

  if "<i>" in str(b):
    text = str(b)[3:-4]
    text = text.replace("<i>", "")
    text = text.replace("</i>", "")
    title = text.replace("<br/>", "")
    title = title.replace("\r\n", "")
    date = re.sub(r'\([^)]*\)', '', title)
    date = re.sub(r'\[[^)]*\]', '', date)
    print " 334 ---", date
    date = date.rsplit(',')
    date_string = date[-1]
    date_string = date_string.strip()

    if "," not in date_string:
      date_string = date_string.replace(" ", " 1, ")

    return{"date_string": date_string, "real_title": title}
  if date.strip() == "Alleged Deception of Congress: The Congressional Task Force on Immigration Reform's Fact-Finding Visit to the Miami District of INS in June 1995":
    return{"date_string": "June 1, 1996", "real_title": "Alleged Deception of Congress: The Congressional Task Force on Immigration Reform's Fact-Finding Visit to the Miami District of INS in June 1995"}
  if date == "Audit Report GR-30-00-001":
    return{"date_string": "November 1, 2000", "real_title":"McMechen, West Virginia Police Department, Audit Report GR-30-00-001"}
  # no date, one other entry, giving it the same date
  if date == "Georgia's Department of Corrections":
   return{"date_string": "November 1, 2000", "real_title":"United States Marshals Service Cost Proposal for the Intergovernmental Service Agreement for Detention Facilities with the City of Atlanta, Georgia’s Department of Corrections"}
  # Intergovernmental Agreements for Detention Space External Reports don't always have dates, not even on the douments, using today
  if directory == "Intergovernmental Agreements for Detention Space (IGAs)":
    real_title = str(b)
    date_string = datetime.now()
    date_string = datetime.strftime(date_string, "%B %d, %Y")
    return{"date_string": date_string, "real_title": real_title}
  print date, "mad it this far"
  if date != None:
    date = date.strip
    # case 1, date is wrong because it is in the paragraph and completely written out
    try:
        date =  b.string
        date_string = date_format(date)
        title = b.string
        print "tried"
    except:
      # these are lists of links that are different variants of the same report in a list
      # case where there is a list in a paragraph tag
      listy = b.parent.parent
      text = str(listy.previous_sibling)
      if "<!--" in text: 
        print "found comment"
        title = re.search(r"^.*?(?=<!--)", text)
        title = title.group(0)
        title =  str(title)[3:]
      else:
        title = text  

      # case where there is a paragraph above a list
      print text, "----- text"
      if len(text) < 4:
        listy = b.parent.parent
        text = listy.previous_sibling.previous_sibling
        title = str(text)[3:-4]

      print "title===== ", title
      date = re.sub(r'\([^)]*\)', '', title)
      date = re.sub(r'\[[^)]*\]', '', date)
      date = date.rsplit(',')
      print "chunks === ", date
      date_string = date[-1]
      date_string = date_string.strip()
      if "," not in date_string:
        date_string = date_string.replace(" ", " 1, ")

  else:
    print "date = None", b

  #I don't know why this doesn't work on the first passs for the first item on the page, dealing with it here
  try:
    print "427"
    date_string.strip()
    date = datetime.strptime(date_string, "%B %d, %Y")
  except:
    y = b.previous_sibling.previous_sibling
    print b, "\n"
    print y, "y"
    print "\n"
    date_string = y.string
    print "work damn you!"

  info = {"real_title":title, "date_string": date_string, }
  return(info)

def get_content(url):
  page = utils.download(url)
  page = BeautifulSoup(page)
  content = page.select(".content-left")
  return content

def find_pages():
  starting_point = "http://www.justice.gov/oig/reports/"
  content = get_content(starting_point)
  for c in content:
    links = c.find_all("a")
    for l in links:
      name = l.string 
      link = base_url + l.get("href")
      source_links[link] = name

def run():
  find_pages()
  for l in source_links.keys():
    content = get_content(l)
    extract_info(content, source_links[l])

  ## for debugging I am using a test file
  # f = open("inspectors/USDOJ_OIG_Special Report.html","r")
  # data = f.read()
  # page = BeautifulSoup(data)
  # content = page.select(".content-left")
  # extract_info(content, "Special Reports")
  
  for key in report.keys():
    inspector.save_report(report[key])

run()