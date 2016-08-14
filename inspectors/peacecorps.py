#!/usr/bin/env python

import datetime
import logging
import os
import urllib

from utils import utils, inspector, admin

# https://www.peacecorps.gov/about/inspector-general/
archive = 1989

# options:
#   standard since/year options for a year range to fetch from.
#
# Notes for IG's web team:
#

REPORTS_URL = "https://www.peacecorps.gov/about/inspector-general/reports/?page=%d"

REPORT_PUBLISHED_MAPPING = {
  "Death_Inquiry_and_Assessment_of_Medical_Care_in_Peace_Corps_Morocco": datetime.datetime(2010,2,1),
  "Burkina_Faso_Medical_Supply_Management_Advisory_Report": datetime.datetime(2013, 3, 14),
  "PCIG_Final_MAR_Certification_of_Volunteer_Payments": datetime.datetime(2013, 9, 24),
  "MAR_Cost_Savings_Opportunity_on_Value_Added_Tax": datetime.datetime(2013, 2, 13),
  "Management_Advisory_Report-Peace_Corps_Drug_Free_Workplace_Program": datetime.datetime(2012, 8, 16),
  "PCIG_2014_Peace_Corps_OIG_Peer_Review_Final": datetime.datetime(2014, 3, 27),
  "MAR_Sierra_Leone": datetime.datetime(2013, 3, 14),
  "Capstone_Report_2012_Medical_Inventory_Issues_Final": datetime.datetime(2013, 8, 26),
  "PCIG_Capstone_Report_Billing_and_Collection_Process": datetime.datetime(2014, 9, 30),
  "PC_Morocco_Assessment_of_Medical_Care": datetime.datetime(2010, 2, 1),
  "PCIG_New_Country_Entries_Lessons_Learned_Final_Report": datetime.datetime(2014, 9, 30),
  "PC_Recurring_Issues_OIG_Post_Audits_Evaluations_FYs_2009-2011": datetime.datetime(2012, 4, 1),
  "PC_Vanuatu_SR_Advice_and_Assistance": datetime.datetime(2010, 5, 12),
  "PC_Gambia_SR_Grant_Activities": datetime.datetime(2010, 5, 14),
  "PC_Ecuador_Special_Review_IG1005SR": datetime.datetime(2010, 9, 1),
  "PCIG_Agency_Policies_Related_to_Volunteer_Sexual_Assault_Allegations": datetime.datetime(2014, 11, 21),
  "PCIG_Investigative_Review_of_a_Volunteer_Death_in_Peace_Corps_China": datetime.datetime(2014, 11, 1),
  "PCIG_Agency_Response_to_the_China_Investigative_Review_Nov_2014": datetime.datetime(2015, 1, 23),
  "PCIG_MAR_Peace_Corps_Cloud_Computing_Pilot_Program": datetime.datetime(2015, 3, 17),
  "MAR_Peace_Corps_Volunteer_Health_Care_Administration_Contract": datetime.datetime(2015, 3, 31),
  "Management_Implication_Report_Peace_Corps_Paraguays_Inappropriate_Use_of_Cooperative_Agreements_to_Obligate_the_Government": datetime.datetime(2010, 3, 15),
  "MAR_Mitigating_a_Potential_Electrica_Safety_Hazard_Redacted_2": datetime.datetime(2011, 5, 17),
  "Safety_and_security_weaknesses_in PC_Cameroon": datetime.datetime(2012, 7, 31),
  "Peace_Corps_Gambia_Grant_Activities": datetime.datetime(2010, 5, 14),
  "OIG_Investigations_have_Disclosed_Improper_Vehicle_Disposal_Practices_and_Vehicle_Sales_that_do_not_generate_Fair_Market_Returns": datetime.datetime(2010, 3, 30),
  "management-performance-challenges-fy2015": datetime.datetime(2015, 12, 3),
  "Healthcare_Benefits_Administration_Contract_Audit": datetime.datetime(2016, 1, 21),
  "Kyrgyz_Republic_Audit_Final_Report": datetime.datetime(2016, 1, 15),
  "PCIG_Cameroon_Final_Audit_Report": datetime.datetime(2015, 1, 14),
  "PCIG_Final_Follow-up_Audit_Report_of_the_Peace_Corps_Safety_and_Security_Program": datetime.datetime(2015, 3, 12),
  "Final_Audit_Report_Guyana-2015": datetime.datetime(2015, 8, 5),
  "PCIG_Nepal_Final_Audit": datetime.datetime(2015, 2, 5),
  "Madagascar_Final_Audit": datetime.datetime(2015, 4, 30),
  "Vanuatu_Audit_Report_Final": datetime.datetime(2015, 9, 29),
  "PCIG_Armenia_Final_Audit_Report": datetime.datetime(2014, 2, 20),
  "PCIG_Dominican_Republic_Final_Audit_Report": datetime.datetime(2014, 9, 30),
  "PCIG_The_Gambia_Final_Audit_Report": datetime.datetime(2014, 9, 15),
  "PCIG_Macedonia_Final_Audit_Report": datetime.datetime(2013, 12, 3),
  "PCIG_Final_Audit_Report_Applicant_Screening_Process": datetime.datetime(2014, 6, 10),
  "PCIG_Final_Audit_Report_Peace_Corps_Overseas_Staffing": datetime.datetime(2013, 11, 21),
  "PCIG_Final_Report_on_the_Review_of_PC_Management_of_Grants": datetime.datetime(2013, 3, 28),
  "PCIG_Jamaica_Final_Audit_Report": datetime.datetime(2013, 7, 3),
  "PC_Malawi_Final_Audit_Report_IG1302A": datetime.datetime(2013, 2, 27),
  "PC_Final_Audit_Report_The_Peace_Corps_50th_Anniversary_Program_IG1301A": datetime.datetime(2012, 10, 25),
  "PCIG_South_Africa_Final_Audit_Report": datetime.datetime(2013, 3, 18),
  "PCIG_Zambia_Final_Audit_Report": datetime.datetime(2013, 9, 27),
  "PC_Costa_Rica_Final_Audit_Report_IG1203A": datetime.datetime(2012, 3, 9),
  "PC_Final_Audit_Report_Jordan_IG1207": datetime.datetime(2012, 9, 25),
  "PC_Lesotho_Final_Audit_Report_IG1205A": datetime.datetime(2012, 6, 29),
  "PC_Limited_Scope_Audit_of_Peace_Corps_China": datetime.datetime(2012, 8, 1),
  "PC_Mali_Final_Audit_Report_IG1204A": datetime.datetime(2012, 3, 22),
  "PC_Final_Audit_Report_Mid-Atlantic_RRO_IG1201A": datetime.datetime(2011, 10, 11),
  "PC_Final_Audit_Report_Budget_Formulation_Process_IG1202A": datetime.datetime(2012, 2, 14),
  "PC_Final_Audit_Report-PC-Tonga-IG1208A": datetime.datetime(2012, 9, 28),
  "PC_Albania_Final_Audit_Report_IG1107A": datetime.datetime(2011, 6, 21),
  "PC_Belize_Final_Audit_Report_IG1104A": datetime.datetime(2011, 3, 1),
  "PC_Ethiopia_Final_Audit_Report_IG1102A": datetime.datetime(2011, 2, 1),
  "PC_Mexico_Final_Audit_Report_IG1101A": datetime.datetime(2011, 2, 9),
  "PC_Mozambique_Final_Audit_Report_IG1105A": datetime.datetime(2011, 3, 31),
  "PC_Panama_Final_Audit_Report_IG1109A": datetime.datetime(2011, 9, 15),
  "PC_Rwanda_Final_Audit_Report_IG1108A": datetime.datetime(2011, 9, 12),
  "PC_Togo_Final_Audit_Report_IG1103A": datetime.datetime(2011, 3, 3),
  "PC_Ukraine_Final_Audit_Report_IG1106A": datetime.datetime(2011, 3, 31),
  "PC_Burkina_Faso_Final_Audit_Report_IG1001A": datetime.datetime(2009, 10, 1),
  "PC_Cape_Verde_Final_Audit_Report_IG1003A": datetime.datetime(2009, 12, 1),
  "PC_Kenya_Final_Audit_Report_IG1012A": datetime.datetime(2010, 9, 1),
  "PC_Moldova_Final_Audit_Report_IG1011A": datetime.datetime(2010, 8, 1),
  "PC_Mongolia_Final_Audit_Report_IG1007A": datetime.datetime(2010, 2, 1),
  "PC_OCIO_Final_Audit_Report_IG1005A": datetime.datetime(2010, 1, 1),
  "PC_Paraguay_Final_Audit_Report_IG1010A": datetime.datetime(2010, 8, 1),
  "PC_Process_for_Soliciting_Awarding_and_Administering_Contracts_IG1006A": datetime.datetime(2010, 3, 1),
  "PC_Suriname_Final_Audit_Report_IG1006A": datetime.datetime(2010, 5, 1),
  "PC_Tanzania_Final_Audit_Report_IG1004A": datetime.datetime(2010, 1, 1),
  "PC_Safety_and_Security_Final_Audit_Report_IG1008A": datetime.datetime(2010, 4, 1),
  "PC_Guatemala_Final_Audit_Report_IG0904A": datetime.datetime(2009, 1, 1),
  "PC_Guinea_Final_Audit_Report_IG0909A": datetime.datetime(2009, 3, 1),
  "PC_Morocco_Final_Audit Report_IG0910A": datetime.datetime(2009, 7, 1),
  "PC_Nicaragua_Audit_Report_IG0912A": datetime.datetime(2009, 7, 1),
  "PC_Purchase_Card_Final_Audit_Report_IG0908A": datetime.datetime(2009, 3, 1),
  "PC_Samoa_Final_Audit_Report_IG0906A": datetime.datetime(2009, 3, 1),
  "PC_Senegal_FollowUp_Audit_Report_IG0911FUA": datetime.datetime(2009, 7, 1),
  "PC_Swaziland_Final_Audit_Report_IG0901A": datetime.datetime(2008, 11, 1),
  "PC_Uganda_FollowUp_Audit_Report_IG0907FUA": datetime.datetime(2009, 3, 1),
  "PC_Armenia_FollowUp_Audit_Report_IG-08-01": datetime.datetime(2007, 10, 1),
  "PC_Azerbaijan_Final_Audit_Report_IG-08-09-A": datetime.datetime(2008, 3, 1),
  "PC_Botswana_Final_Audit_Report_IG-08-16-A": datetime.datetime(2008, 9, 1),
  "PC_China_FollowUP_Audit_Report_IG-08-06": datetime.datetime(2008, 3, 1),
  "PC_EC_Final_Audit_Report_IG-08-03-A": datetime.datetime(2007, 12, 1),
  "PC_ElSalvador_Final_Audit_Report_IG-08-14-A": datetime.datetime(2008, 9, 1),
  "PC_Fiji_FInal_Audit_Report_IG08-04-A": datetime.datetime(2008, 1, 1),
  "PC_Georgia_Final_Audit_Report_IG-08-05-A": datetime.datetime(2008, 1, 1),
  "PC_Kazakhstan_Final_Audit_Report_IG-08-02-A": datetime.datetime(2007, 10, 1),
  "PC_Peru_Final_Audit_Report_IG-08-07-A": datetime.datetime(2008, 3, 1),
  "PC_Philippines_Final_Audit_Report_IG-08-10-A": datetime.datetime(2008, 7, 1),
  "PC_South_Africa_FollowUp_Audit_Report_7-15-08": datetime.datetime(2008, 7, 1),
  "PC_Vanuatu_FollowUp_Audit_Report_IG-08-15": datetime.datetime(2008, 9, 1),
  "PC_Cameroon_Final_Audit_Report_IG-07-15-A": datetime.datetime(2007, 8, 1),
  "PC_China_Final_Audit_Report_IG-07-07-A": datetime.datetime(2007, 3, 1),
  "PC_Honduras_FollowUp_Audit_Report": datetime.datetime(2007, 6, 1),
  "PC_Jordan_Final_Audit_Report_IG-07-17-A": datetime.datetime(2007, 9, 1),
  "PC_Niger_Final_Audit_Report_IG-07-13-A": datetime.datetime(2007, 7, 1),
  "PC_Panama_FollowUp_Audit_Report": datetime.datetime(2007, 6, 1),
  "PC_Senegal_Final_Audit_Report_IG-07-18-A": datetime.datetime(2007, 9, 1),
  "PC_SSN_FollowUp_Report": datetime.datetime(2007, 6, 1),
  "PC_Thailand_Final_Audit_Report_IG-07-19-A": datetime.datetime(2007, 9, 1),
  "PC_Uganda_FollowUp_Audit_Report_0703": datetime.datetime(2006, 12, 1),
  "PC_Zambia_FollowUp_Audit_Report_0704": datetime.datetime(2006, 1, 1),
  "PC_Zambia_Final_Audit_Report_IG-07-16-A": datetime.datetime(2007, 9, 1),
  "PC-Benin-Final-Eval_Sep-3-2015": datetime.datetime(2015, 9, 4),
  "Guatemala_Final_Evaluation_Report": datetime.datetime(2015, 5, 13),
  "Lesotho_Final_Evaluation_Report": datetime.datetime(2015, 3, 31),
  "Nepal_Final_Report": datetime.datetime(2015, 12, 1),
  "PCIG_Sierra_Leone_Final_Evaluation": datetime.datetime(2015, 1, 30),
  "PCIG_Armenia_Final_Evalation_Report": datetime.datetime(2014, 8, 19),
  "PCIG_Ecuador_Final_Evaluation_Report": datetime.datetime(2014, 5, 21),
  "PCIG_Mexico_Final_Evaluation_Report": datetime.datetime(2014, 6, 13),
  "PCIG_Final_Program_Evaluation_of_Peace_Corps_SARRR_Training": datetime.datetime(2013, 11, 21),
  "PCIG_Final_Program_Evaluation_Volunteer_Sexual_Assault_Policy": datetime.datetime(2013, 11, 21),
  "PCIG_Philippines_Final_Evaluation_Report": datetime.datetime(2014, 9, 16),
  "PCIG_Final_Evaluation_Report_Training_Peace_Corps_Overseas_Staff": datetime.datetime(2014, 9, 30),
  "PCIG_Colombia_Evaluation_Report": datetime.datetime(2013, 4, 29),
  "PCIG_Malawi_Evaluation_Report": datetime.datetime(2013, 3, 22),
  "PCIG_Moldova_Final_Evaluation_Report": datetime.datetime(2013, 9, 16),
  "PCIG_Namibia_Final_Evaluation_Report": datetime.datetime(2013, 3, 15),
  "PC_China_Final_Evaluation_Report_IG1204E": datetime.datetime(2012, 5, 24),
  "PC_Fiji_Final_Evaluation_Report_IG1201E": datetime.datetime(2011, 11, 30),
  "Final_Report_Review_of_the_Peace_Corps_Implementation_of_Guidelines_Related_to_Volunteer_Victims_of_Rape_and_Sexual_Assault": datetime.datetime(2012, 9, 27),
  "PC_Final_Evaluation_Report_on_Impacts_of_the_Five_Year_Rule_IG1205E": datetime.datetime(2012, 6, 20),
  "PC_Indonesia_Final_Evaluations_IG1207E": datetime.datetime(2012, 9, 19),
  "PC_Kyrgyz_Republic_Final_Evaluation_ Report_IG1202E": datetime.datetime(2011, 12, 6),
  "PC_Peru_Final_Evaluation_Report_IG1203E": datetime.datetime(2011, 3, 26),
  "PC_Uganda_Final_Evaluation_IG1206E": datetime.datetime(2012, 7, 6),
  "PC_Cambodia_Final_Evaluation_Report_IG1104E": datetime.datetime(2011, 5, 5),
  "PC_Ethiopia_Final_Program_Evaluation_Report_IG1102E": datetime.datetime(2011, 1, 14),
  "PC_Jamaica_Final_Evaluation_Report_IG1103E": datetime.datetime(2011, 2, 28),
  "PC_Liberia_Final_Evaluation_Report_IG1107E": datetime.datetime(2011, 9, 8),
  "PC_Romania_Final_Eval_Report_IG1105E": datetime.datetime(2011, 6, 30),
  "PC_Swaziland_Final_Evaluation_Report_IG1106E": datetime.datetime(2011, 8, 19),
  "PC_VDS_Follow-up_Final_Program_Evaluation_IG1101E": datetime.datetime(2010, 12, 1),
  "PC_Morocco_Final_Program_Evaluation_Report_IG1006E": datetime.datetime(2010, 2, 1),
  "PC_Suriname_Final_Program_Evaluation_Report_IG1009E": datetime.datetime(2010, 7, 1),
  "PC_Togo_Final_Program_Evaluation_IG1010E": datetime.datetime(2010, 9, 1),
  "PC_Turkmenistan_Final_Program_Evaluation_Report_IG1002E": datetime.datetime(2009, 11, 1),
  "PC_Belize_Final_Program_Evaluation_Report_IG0914E": datetime.datetime(2009, 8, 1),
  "PC_Dominican_Republic_Program_Evaluation_Report_IG0903E": datetime.datetime(2008, 12, 1),
  "PC_Ghana_Final_Program_Evaluation_Report_IG0913E": datetime.datetime(2009, 7, 1),
  "PC_Guyana_Final_Program_Evaluation_Report_IG0905E": datetime.datetime(2009, 2, 1),
  "PC_Jordan_Final_Program_Evaluation_Report_IG0915E": datetime.datetime(2009, 9, 1),
  "PC_Nicaragua_Program_Evaluation_Report_IG0902E": datetime.datetime(2008, 12, 1),
  "PC_Albania_Final_Evaluation_Report_IG-08-12-E": datetime.datetime(2008, 8, 1),
  "PC_Medical_Clearance_System_Report_IG-08-08-E": datetime.datetime(2008, 3, 1),
  "PCIG_Safety_and_Security_Final_Evaluation_Report_2008": datetime.datetime(2008, 8, 1),
  "PC_Azerbaijan_Final_Evaluation_Report_IG-07-11-E": datetime.datetime(2007, 7, 1),
  "PC_Cameroon_Final_Evaluation_Report_IG-07-01-E": datetime.datetime(2006, 10, 1),
  "PC_EC_Final_Evaluation_Report_IG-07-12-E": datetime.datetime(2007, 7, 1),
  "PC_Ecuador_Final_Evaludation_Report_IG-0704AE": datetime.datetime(2007, 1, 1),
  "PC_Guinea_Final_Evaluation_Report_IG-07-14-E": datetime.datetime(2007, 8, 1),
  "PC_ProgramStudyReport11": datetime.datetime(2007, 1, 1),
  "PC_South_Africa_Final_Evaluation-Report-IG-0702EA": datetime.datetime(2006, 10, 1),
  "Management_Advisory_Report-FOIA": datetime.datetime(2016, 3, 10),
  "Final_Report_Follow_Up_Evaluation_of_Issues_in_2010_PC_Morocco_Assessment_of_Medical_Care": datetime.datetime(2016, 3, 1),
  "PCIG_Buller_Peace_Corps_IG_Statement_02_03": datetime.datetime(2015, 2, 3),
  "PCIG_Buller_Peace_Corps_IG_Statement_9_10": datetime.datetime(2014, 9, 10),
  "PCIG_Kathy_A_Buller_Testimony_PC_OIG_Jan-15-2014_Strengthen_OIG_Oversight": datetime.datetime(2014, 1, 15),
  "buller_testimony_sfac_10_06_11": datetime.datetime(2011, 10, 6),
  "IGAccess.JGlennLtr.072315": datetime.datetime(2015, 7, 23),
  "CIGIE_Letter_to_HSGAC_HOGR_8-3-15": datetime.datetime(2015, 8, 3),
  "PCIG_FY_2016_OIG_Annual_Plan": datetime.datetime(2015, 9, 1),
  "PCIG_FY_2016-18_OIG_Strategic_Plan": datetime.datetime(2015, 8, 1),
  "Strategic_Plan_FY_17-19_for_web": datetime.datetime(2016, 8, 1),
  "Peace_Corps_Rwanda_-_Final_Evaluation_Report_IG-16-02-E": datetime.datetime(2016, 8, 11),
  "Senegal_Final_Audit_Report_IG-16-04-A_xFYq3ir": datetime.datetime(2016, 7, 26),
  "Indonesia_Final_Audit_Report_IG-16-03-A_Cz1wEbX": datetime.datetime(2016, 7, 17),
  "Safety_and_security_weaknesses_in_PCCameroon_NEW": datetime.datetime(2016, 7, 31),
}

REPORT_TYPE_MAP = {
  'Plan': 'other',
  'Special Review': 'other',
  'Audit': 'audit',
  'None': 'other',
  'Evaluation': 'evaluation',
  'Annual Report': 'semiannual_report',
  'Letter': 'other',
  'Testimony': 'testimony',
  'Management Advisory': 'other'
}

# Several consecutive reports appear twice on pages 4 and 5 at time of writing
doubled_reports = {
  "PCIG_Final_Program_Evaluation_of_Peace_Corps_SARRR_Training": 0,
  "PCIG_South_Africa_Final_Audit_Report": 0,
  "PCIG_Moldova_Final_Evaluation_Report": 0,
  "PC_Final_Audit_Report_Jordan_IG1207": 0,
  "PC_Ethiopia_Final_Program_Evaluation_Report_IG1102E": 0,
  "PC_Ethiopia_Final_Audit_Report_IG1102A": 0,
  "PC_Fiji_Final_Evaluation_Report_IG1201E": 0,
}

def run(options):
  year_range = inspector.year_range(options, archive)

  # Pull the reports
  page = 1
  while True:
    doc = utils.beautifulsoup_from_url(REPORTS_URL % page)
    results = doc.select(".teaser")
    if not results:
      raise inspector.NoReportsFoundError("Peace Corps")
    for result in results:
      report = report_from(result, year_range)
      if report:
        inspector.save_report(report)
    if doc.select(".pager__link--next"):
      page += 1
    else:
      break

def report_from(result, year_range):
  link = result.find("a")
  report_url = urllib.parse.unquote(link.get('href'))
  report_filename = report_url.split("/")[-1]
  report_id, _ = os.path.splitext(report_filename)
  report_id = urllib.parse.unquote(report_id)
  title = link.text

  report_type = None
  tag_text = None
  if "Semiannual Report to Congress" in title:
    report_type = "semiannual_report"
  else:
    for tag in result.select(".ul--tags li"):
      tag_text = tag.text.strip()
      if tag_text in REPORT_TYPE_MAP:
        report_type = REPORT_TYPE_MAP[tag_text]
        break
  if not report_type:
    raise Exception("Unrecognized report type %s" % tag_text)

  published_on = None
  if report_id in REPORT_PUBLISHED_MAPPING:
    published_on = REPORT_PUBLISHED_MAPPING[report_id]
  if not published_on:
    try:
      published_on_text = title.split("-")[-1].strip()
      published_on_text = published_on_text.replace("Sept.", "September")
      published_on = datetime.datetime.strptime(published_on_text, '%B %d, %Y')
    except ValueError:
      pass
  if not published_on:
    admin.log_no_date("peacecorps", report_id, title, report_url)
    return

  if report_id in doubled_reports:
    if doubled_reports[report_id] == 0:
      doubled_reports[report_id] += 1
    else:
      return

  if published_on.year not in year_range:
    logging.debug("[%s] Skipping, not in requested range." % report_url)
    return

  report = {
    'inspector': 'peacecorps',
    'inspector_url': 'https://www.peacecorps.gov/about/inspectors-general/',
    'agency': 'peacecorps',
    'agency_name': 'Peace Corps',
    'type': report_type,
    'report_id': report_id,
    'url': report_url,
    'title': title,
    'published_on': datetime.datetime.strftime(published_on, "%Y-%m-%d"),
  }
  return report

utils.run(run) if (__name__ == "__main__") else None
