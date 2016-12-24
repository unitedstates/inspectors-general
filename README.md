## Inspectors General

A project to collect reports from the [offices of Inspectors General](https://en.wikipedia.org/wiki/Office_of_the_Inspector_General) across the US federal government.

For more information about the project, read:

* [Opening up government reports through teamwork and open data](https://sunlightfoundation.com/blog/2014/11/07/opengov-voices-opening-up-government-reports-through-teamwork-and-open-data/)
* [Why we've collected a hojillion inspector general reports](http://sunlightfoundation.com/blog/2014/05/13/why-weve-collected-a-hojillion-inspector-general-reports/)


#### What's an inspector general?

From [one of the above pieces](https://sunlightfoundation.com/blog/2014/05/13/why-weve-collected-a-hojillion-inspector-general-reports/):

> Just about every agency in the federal government has an independent unit, usually called the Office of the Inspector General, dedicated to independent oversight. This includes regular audits of the agency's spending, monitoring of active government contractors and investigations into wasteful or corrupt agency practices. They ask tough questions, carry guns, and sue people.

#### How you can help

The initial round of writing scrapers for all 65 federal IGs has come to a close. However, there are two important areas we need help in:

* **Keeping the scrapers working**. They're scrapers: they break. Check the [Oversight.garden dashboard](https://oversight.garden/dashboard) for scrapers in need of attention, or check the [issues list](https://github.com/unitedstates/inspectors-general/issues) for other tasks.

Ask [@konklone](https://twitter.com/konklone) for an invitation to the [project Slack](https://oversight.slack.com) if you want to talk with teammates and get involved.

* Just as importantly, **sending in reports we can't scrape.**

There are 9 IGs who do not publish reports online, many from the US government's intelligence community.

* [Architect of the Capitol](http://www.aoc.gov/aoc/oig.cfm)
* [Capitol Police](http://www.uscapitolpolice.gov/oig.php)
* [Central Intelligence Agency](https://www.cia.gov/offices-of-cia/inspector-general)
* [Defense Intelligence Agency](http://www.dia.mil/About/OfficeoftheInspectorGeneral.aspx)
* [National Geospatial-Intelligence Agency](https://www.nga.mil/About/Pages/InspectorGeneral.aspx)
* [National Reconnaissance Office](http://www.nro.gov/offices/oig/cd.html)
* [National Security Agency](http://www.nsa.gov/about/oig/index.shtml)
* [Intelligence Community](http://www.dni.gov/index.php/about/organization/office-of-the-intelligence-community-inspector-general-who-we-are) (ODNI)

Generally, getting their reports means **filing [Freedom of Information Act](https://en.wikipedia.org/wiki/Freedom_of_Information_Act_(United_States)) requests**, or finding the results of FOIA requests others have already made.

We also need unpublished reports from the other 65 IGs! We're scraping what they publish online, but most IGs do not proactively publish all of their reports.

#### Submitting IG reports

We don't yet have a formal process for submitting reports &mdash; for now, either [open an issue](https://github.com/unitedstates/inspectors-general/issues/new) and post a link to the file, or email the report to [eric@konklone.com](mailto:eric@konklone.com).

### Scraping IG reports

**Python 3**: This project uses Python 3, and is tested on Python 3.4.0. If you don't have Python 3 installed, check out [pyenv](https://github.com/yyuu/pyenv) and [pyenv-virtualenvwrapper](https://github.com/yyuu/pyenv-virtualenvwrapper) for easily installing and switching between multiple versions of Python.

**Dependencies**:

* To extract PDFs (the most common type of report), you'll need `pdftotext`, `pdfinfo`, and `qpdf`. On Ubuntu, `apt-get install poppler-utils qpdf`. On OS X, `brew install poppler qpdf`.
* To extract DOCs, you'll need [`abiword`](http://www.abisource.com/), which you can install via `apt-get` or `brew`.
* Install all the PIP dependencies by running `pip install -r requirements.txt`

To run an individual IG scraper, just execute its file directly. For example:

```bash
./inspectors/usps.py
```

This will fetch the current year's reports from the [Inspector General for the US Postal Service](https://uspsoig.gov) and write them to disk, along with JSON metadata.

If you want to go back further, use `--since` or `--year` to specify a year or range:

```bash
./inspectors/usps.py --since=2009
```

If you want to run multiple IG scrapers in a row, use the `igs` script:

```bash
./igs
```

By default, the `igs` script runs all scrapers. It takes the following arguments:

* `--safe`: Limit scrapers to those declared in `safe.yml`. The idea is for "safe" scrapers to be appropriate for clients who wish to fully automate their report pipeline, without human intervention when new IGs are added, in a stable way.
* `--only`: Limit scrapers to a comma-separated list of names. For example, `--only=opm,epa` will run `inspectors/opm.py` and `inspectors/epa.py` in turn.
* `--data-directory`: The directory path to store the output files. Defaults to `data` in the current working directory.

#### Using the data

Reports are broken up by IG and by year. So a USPS IG report from 2013 with a scraper-determined ID of `no-ar-13-010` will create the following files:

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
* `--dry_run`: Will scrape sites and write JSON metadata to disk, but won't download full reports or extract text.


#### Report metadata

Every `report` has an accompanying JSON file with metadata. That JSON file is an object with the following **required fields**:

* `inspector` - The handle you chose for the IG. e.g. "usps"
* `inspector_url` - The IG's primary website URL.
* `agency` - The handle of the agency the report relates to. This can be the same value as `inspector`, but it may differ -- some IGs monitor multiple agencies.
* `agency_name` - The full text name of an agency, e.g. "United States Postal Service"
* `report_id` - A string usable as an ID for the report.
* `title` - Title of report.
* `published_on` - Date of publication, in `YYYY-MM-DD` format.

Additionally, some information about report URLs is **required**. However, not all report contents are released: some are sensitive or classified, or require a FOIA request to obtain. Use these fields to handle report URLs:

* `url` - URL to the report itself. Required unless `unreleased` is `True`.
* `landing_url` - URL to some kind of landing page for the report.
* `unreleased` - Set to `True` if the report's contents are not fully released.

If `unreleased` is `True`, then `url` is *optional* and `landing_url` is *required*.

The JSON file may have arbitrary additional fields the scraper author thought worth keeping.

The `report_id` must be unique within that IG, and should be stable and idempotent.

### Bulk data and backup

This project's chief maintainer, [Eric Mill](https://twitter.com/konklone), runs a copy of this project on a server that automatically backs up the downloaded bulk data.

Data is backed up to the [Internet Archive](https://archive.org).

To back up individual reports as items in the collection, run the `backup` script:

```bash
./backup
```

This goes through all reports in `data/` for which a report has been released (in other words, where `unreleased` is not `true`), and uploads their metadata and report data to the Internet Archive.

For example, the `treasury` IG's 2014 report `OIG-14-023` report can be found at:

> https://archive.org/details/us-inspectors-general.treasury-2014-OIG-14-023

To generate bulk data, the following command is run from the project's output `data/` directory.

```bash
zip -r ../us-inspectors-general.bulk.zip * -x "*.done"
cd ..
./backup --bulk=us-inspectors-general.bulk.zip
```

Both zipping and uploading take a long time -- this is a several-hour process at minimum.

The process zips up the contents of the  `data/` directory, while excluding any `.done` files that track the status of individual file backups. The zip file is placed up one directory, so that it doesn't interfere with the automatic directory examination of `data/` that many scripts employ.

Then the file is uploaded to the Internet Archive as part of the collection, to be a convenient bulk mirror of the entire thing.

[TBD: Proper collection landing page, and bulk data link.]

### Resources

* [Matt Rumsey](https://twitter.com/mattrumsey) kindly [compiled a spreadsheet](https://docs.google.com/spreadsheet/ccc?key=0AoQuErjcV2a0dF9jUjRSczQ5WEVqd3RoS3dtLTdGQnc&usp=sharing) of IG offices. We used this to track activity during the initial scraping phase.

### Public domain

This project is [dedicated to the public domain](LICENSE). As spelled out in [CONTRIBUTING](CONTRIBUTING.md):

> The project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).

> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
