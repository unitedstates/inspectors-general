## Inspectors General

A project to collect reports from the offices of Inspectors General across the federal government.

**Done so far**:

* [US Postal Service](http://www.uspsoig.gov/)
* [Department of Homeland Security](http://www.oig.dhs.gov/), which includes:
  * Secret Service
  * Federal Emergency Management Service (FEMA)
  * Transportation Security Administration (TSA)
  * Immigration and Customs Enforcement (ICE)
  * Customs and Border Protection (CBP)
  * Citizenship and Immigration Services (CIS)
  * Coast Guard

Currently writing scrapers for the highest priority IG offices, as highlighted in yellow [in this spreadsheet](https://docs.google.com/spreadsheet/ccc?key=0AoQuErjcV2a0dF9jUjRSczQ5WEVqd3RoS3dtLTdGQnc&usp=sharing).

### Using

**Setup**: You'll need to have `pdftotext` installed. On Ubuntu, `apt-get install poppler-utils`. On Macs, install it via MacpPorts with `port install poppler`, or via Homebrew with `brew install poppler`.

To run an individual IG scraper, just execute its file directly. For example:

```bash
python inspectors/usps.py
```

This will fetch the latest reports from the [Inspector General for the US Postal Service](http://uspsoig.gov) and write them to disk, along with JSON metadata.

Reports are broken up by IG, and by year. So a USPS IG report from 2013 with a scraper-determined ID of `no-ar-13-010` will create the following files:

```
/data/usps/2013/no-ar-13-010/report.json
/data/usps/2013/no-ar-13-010/report.pdf
/data/usps/2013/no-ar-13-010/report.txt
```

Metadata for a report is at `report.json`. The original report will be saved at `report.pdf` (the extension will match the original, it may not be `.pdf`). The text from the report will be extracted to `report.txt`.


### Contributing a Scraper

The easiest way is to start by copying `scraper.py.template` to `inspectors/[inspector].py`, where "[inspector]" is the filename-friendly handle of the IG office you want to scrape. For example, our scraper for the US Postal Service's IG is [usps.py](https://github.com/unitedstates/inspectors-general/blob/master/inspectors/usps.py).

The template has a suggested workflow and set of methods, but all your task **needs** to do is:

* start execution in a `run` method, and
* call `inspector.save_report(report)` for every report

This will save that report to disk in the right place.

The `report` object must be a dict that contains the following required fields:

* `inspector` - The handle you chose for the IG. e.g. "usps"
* `inspector_url` - The IG's primary website URL.
* `agency` - The handle of the agency the report relates to. This can be the same value as `inspector`, but it may differ -- some IGs monitor multiple agencies.
* `agency_name` - The full text name of an agency, e.g. "United States Postal Service"
* `report_id` - A string usable as an ID for the report.
* `title` - Title of report.
* `url` - Link to report.
* `published_on` - Date of publication, in `YYYY-MM-DD` format.
* `year` - Year of publication.
* `type` - "report" or some other description. There's not yet a standard set of values for this field.
* `file_type` - "pdf", or whatever file extension the report has.

The `report_id` only needs to be unique within that IG, so you can make it up from other fields.

It does need to come out the same every time you run the script. In other words, **don't auto-increment a number** -- if the IG doesn't give you a unique ID already, append other fields together into a consistent, unique ID.

## Public domain

This project is [dedicated to the public domain](LICENSE). As spelled out in [CONTRIBUTING](CONTRIBUTING.md):

> The project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](http://creativecommons.org/publicdomain/zero/1.0/).

> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
