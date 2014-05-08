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
  * (and others)
* [Office of Personnel Management (OPM)](https://www.opm.gov/our-inspector-general/reports/)
* [Environmental Protection Agency (EPA)](http://www.epa.gov/oig/reports.html)
* [Department of Justice](http://www.justice.gov/oig/reports/)
  * Federal Bureau of Investigation (FBI)
  * United States Marshals Service (USMS)
  * Drug Enforcement Administration (DEA)
  * Bureau of Alcohol, Tobacco, Firearms and Explosives (ATF)
  * (and others)

Thanks to [Matt Rumsey](https://twitter.com/mattrumsey) for [compiling a spreadsheet](https://docs.google.com/spreadsheet/ccc?key=0AoQuErjcV2a0dF9jUjRSczQ5WEVqd3RoS3dtLTdGQnc&usp=sharing) of IG offices.

### Using

**Setup**: You'll need to have `pdftotext` installed. On Ubuntu, `apt-get install poppler-utils`. On Macs, install it via MacPorts with `port install poppler`, or via Homebrew with `brew install poppler`.

To run an individual IG scraper, just execute its file directly. For example:

```bash
./inspectors/usps.py
```

This will fetch the current year's reports from the [Inspector General for the US Postal Service](http://uspsoig.gov) and write them to disk, along with JSON metadata.

If you want to go back further, use `--since` or `--year` to specify a year or range:

```bash
./inspectors/usps.py --since=2009
```

Reports are broken up by IG, and by year. So a USPS IG report from 2013 with a scraper-determined ID of `no-ar-13-010` will create the following files:

```
/data/usps/2013/no-ar-13-010/report.json
/data/usps/2013/no-ar-13-010/report.pdf
/data/usps/2013/no-ar-13-010/report.txt
```

Metadata for a report is at `report.json`. The original report will be saved at `report.pdf` (the extension will match the original, it may not be `.pdf`). The text from the report will be extracted to `report.txt`.

#### Common options

Every scraper will accept the following options:

* `--year`: A `YYYY` year, only fetch reports from this year.
* `--since`: A `YYYY` year, only fetch reports from this year onwards.
* `--debug`: Print extra output to STDOUT. (Can be quite verbose when downloading.)


### Contributing a Scraper

The easiest way is to start by copying `scraper.py.template` to `inspectors/[inspector].py`, where "[inspector]" is the filename-friendly handle of the IG office you want to scrape. For example, our scraper for the US Postal Service's IG is [usps.py](https://github.com/unitedstates/inspectors-general/blob/master/inspectors/usps.py)

The template has a suggested workflow and set of methods, but all your task **needs** to do is:

* start execution in a `run(options)` method, and
* call `inspector.save_report(report)` for every report

This will automatically save reports to disk in the right place, extract text, and avoid re-downloading files. `options` will be a dict parsed from any included command line flags.

It's *encouraged* to use `inspectors.year_range(options)` to obtain a range of desired years, and to obey that range during scraping. See an example of [creating it](https://github.com/unitedstates/inspectors-general/blob/0b0953060878becc3732962d7622ff48caab54ad/inspectors/opm.py#L22) and [using it](https://github.com/unitedstates/inspectors-general/blob/0b0953060878becc3732962d7622ff48caab54ad/inspectors/opm.py#L37-L38).

#### Report metadata

The `report` object must be a dict that contains the following **required fields**:

* `inspector` - The handle you chose for the IG. e.g. "usps"
* `inspector_url` - The IG's primary website URL.
* `agency` - The handle of the agency the report relates to. This can be the same value as `inspector`, but it may differ -- some IGs monitor multiple agencies.
* `agency_name` - The full text name of an agency, e.g. "United States Postal Service"
* `report_id` - A string usable as an ID for the report.
* `title` - Title of report.
* `url` - Link to report.
* `published_on` - Date of publication, in `YYYY-MM-DD` format.

You can **include any other fields** you think worth keeping.

The `report_id` only needs to be unique within that IG, so you can make it up from other fields. It does need to come out the same every time you run the script. In other words, **don't auto-increment a number** -- if the IG doesn't give you a unique ID already, append other fields together into a consistent, unique ID.

Finally, **err towards errors**: have your scraper choke and die on unexpected input. Better to be forced to discover it that way, then for incomplete or inaccurate data to be silently saved.

## Public domain

This project is [dedicated to the public domain](LICENSE). As spelled out in [CONTRIBUTING](CONTRIBUTING.md):

> The project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](http://creativecommons.org/publicdomain/zero/1.0/).

> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
