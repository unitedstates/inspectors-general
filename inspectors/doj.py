
# Recovery docs have their own system for ids. 
# Annual reports before 2006 are not included because of broken links and unique formatting 
# Still need a plan for "indexed" forms

from bs4 import BeautifulSoup
import urllib
import urllib2
#from utils import utils, inspector

report = {}
source_links = {}
base_url = "http://www.justice.gov"
not_agency = ("Office of Justice Programs (OJP)", "Contracts", "Special Reports", "Other DOJ Components and Reports Encompassing More Than One DOJ Component","Equitable Sharing",)
index_links = ["http://www.justice.gov/oig/reports/2012/s1209.htm"]


def extract_info(content, directory):
	if directory in not_agency:
		directory = "Department of Justice"

	for c in content:
		blurbs = c.find_all("p")
	
	for b in blurbs:
		### not working because the divs are above the paragraphs
		try:
			dates = b.find_all(attrs={ "class" : "date" })
			for d in dates:
				print "Found a date"
		except:
			pass
		
		string_title = b.string
		if b.string == None:
			string_title = b.contents
			if "<a href=" in str(string_title):
				string_title = b.contents[0]

		
		for l in b.find_all("a"):
			link = l.get("href")
			if link != None:
				# title
				title = l.string
				if title == "HTML" or title == "PDF":
					title = string_title
				if title == None:
					#this is the only one that doesn't work
					if str(b) == '<p><a href="/oig/press/2012/2012_09_25.pdf">Report on Activities Under Section 702 of the <em>FISA Amendments Act of 2008</em></a></p>':
						title = "Report on Activities Under Section 702 of the FISA Amendments Act of 2008"
				
				if title[-2:] == " [":
					title = title[:-2]

				# formating links consistently
				if link[:1] != "/":
					link = "/" + link 
				# id
				doc_id = str(link)[1:-4]
				if link[:11] == "oig/reports":
					doc_id = doc_id[16:]

				# there may be a better way to do this but I am just taking out all the things that are not the id
				url_extras = ( "/final", "/press", "/fullpdf", "/ins_response", "oig/special/", "USMS/", "plus/", "oig/grants/", "oig/reports/", "EOUSA/", "BOP/", "ATF/", "COPS/", "FBI/", "OJP/", "INS/", "DEA/", "OBD", "Final/", "full/", "/analysis", "/report", "/PDF_list", "/exec", "/full_report", "/full", "_redacted", "oig", "r-summary", "/response", "/listpdf", "/memo", "/fullreport", "/Final", "/extradition")
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

				# url
				if link[:5] == "/oig/":
					url = base_url + link
				else:
					url = base_url + "/oig/reports" + link
				# file_type
				if url[-3:] == "pdf":
					file_type = "pdf"
				elif url[-3:] == "htm":
					file_type = "html"
				elif url[-4:] == "html":
					file_type = "html"
				else:
					# these include a few navigation links	
					file_type = "ignore"
				
				#these docs are one report where the page has a table of contents with links to content
				if "/index" in url:
					index_links.append(url)
					file_type = "ignore"

				### want to go with the most descriptive of the two names for agency
				#still need date
				if file_type != "ignore":
					if report.has_key(doc_id):
						if report[doc_id]["file_type"] == "html":
							html_url = report[doc_id]["URL"]
							report[doc_id] = {"inspector": "doj", "inspector_url": "http://www.justice.gov/oig/reports/", "agency_name": directory, "URL": url,  "title": title, "file_type": file_type, "html_url": html_url }
						else:
							if file_type == "html":
								report[doc_id].update({"html_url" : url})
								print report[doc_id]
					else:
						report[doc_id] = {"inspector": "doj", "inspector_url": "http://www.justice.gov/oig/reports/", "agency_name": directory, "URL": url,  "title": title, "file_type": file_type }	

						

def get_content(url):
	page = urllib2.urlopen(url).read()
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
	return report

run()

#print report
