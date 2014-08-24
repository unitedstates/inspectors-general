## Inspectors General

A project to collect reports from the [offices of Inspectors General](http://en.wikipedia.org/wiki/Office_of_the_Inspector_General) across the US federal government.

We have **65** inspector general offices scraped, downloaded, and stable. See our [safe list](safe.yml) for details.

#### What's an inspector general?

From [this piece explaining the project](http://sunlightfoundation.com/blog/2014/05/13/why-weve-collected-a-hojillion-inspector-general-reports/):

> Just about every agency in the federal government has an independent unit, usually called the Office of the Inspector General, dedicated to independent oversight. This includes regular audits of the agency's spending, monitoring of active government contractors and investigations into wasteful or corrupt agency practices. They ask tough questions, carry guns, and sue people.

#### How you can help

The most important way you can help is by finding and submitting reports from IGs who do not publish their reports online. There are 9 of them, many from the US government's intelligence community.

* [Architect of the Capitol](http://www.aoc.gov/aoc/oig.cfm)
* [Capitol Police](http://www.uscapitolpolice.gov/oig.php)
* [Central Intelligence Agency](https://www.cia.gov/offices-of-cia/inspector-general)
* [Defense Intelligence Agency](http://www.dia.mil/about/inspector-general/)
* [National Geospatial-Intelligence Agency](https://www1.nga.mil/About/Pages/InspectorGeneral.aspx)
* [National Reconnaissance Office](http://www.nro.gov/offices/oig/cd.html)
* [National Security Agency](http://www.nsa.gov/about/oig/index.shtml)
* [Intelligence Community](http://www.dni.gov/index.php/about/organization/office-of-the-intelligence-community-inspector-general-who-we-are) (ODNI)
* [Special Inspector General for Iraq Reconstruction](http://www.sigir.mil/)

Generally, getting their reports means **filing [Freedom of Information Act](http://en.wikipedia.org/wiki/Freedom_of_Information_Act_(United_States)) requests**, or finding the results of FOIA requests others have already made.

We also need unpublished reports from the other 65 IGs! We're scraping what they publish online, but most IGs do not proactively publish all of their reports.

We don't yet have a formal process for submitting reports &mdash; for now, either [open an issue](https://github.com/unitedstates/inspectors-general/issues/new) and post a link to the file, or email the report to [eric@konklone.com](mailto:eric@konklone.com).

You can also **review our data quality** and find bugs. Visit [oversight.io](https://oversight.io) (still ugly and in-progress) and see what the data looks like in action.

Finally, we **have a [project Slack](https://oversight.slack.com)** - anyone who'd like to help out is welcome to join.

### Scraping IG reports

**Python 3**: This project uses Python 3, and is tested on Python 3.4.0. If you don't have Python 3 installed, check out [pyenv](https://github.com/yyuu/pyenv) and [pyenv-virtualenvwrapper](https://github.com/yyuu/pyenv-virtualenvwrapper) for easily installing and switching between multiple versions of Python.

**Dependencies**:

* To extract PDFs (the most common type of report), you'll need `pdftotext` and `pdfinfo`. On Ubuntu, `apt-get install poppler-utils`. On OS X, `brew install poppler`.
* To extract DOCs, you'll need [`abiword`](http://www.abisource.com/), which you can install via `apt-get` or `brew`.

To run an individual IG scraper, just execute its file directly. For example:

```bash
./inspectors/usps.py
```

This will fetch the current year's reports from the [Inspector General for the US Postal Service](http://uspsoig.gov) and write them to disk, along with JSON metadata.

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
* `--dry_run`: Will scrape sites and write JSON metadata to disk, but won't download full reports or extract text.


### Contributing a Scraper

The easiest way is to start by copying `scraper.py.template` to `inspectors/[inspector].py`, where "[inspector]" is the filename-friendly handle of the IG office you want to scrape. For example, our scraper for the US Postal Service's IG is [usps.py](https://github.com/unitedstates/inspectors-general/blob/master/inspectors/usps.py).

The template has a suggested workflow and set of methods, but all your task **needs** to do is:

* start execution in a `run(options)` method, and
* call `inspector.save_report(report)` for every report

This will automatically save reports to disk in the right place, extract text, and avoid re-downloading files. `options` will be a dict parsed from any included command line flags.

You will also need this line at the bottom:

```python
utils.run(run) if (__name__ == "__main__") else None
```

You should use `inspectors.year_range(options)` to obtain a range of desired years, and to obey that range during scraping. See an example of [creating it](https://github.com/unitedstates/inspectors-general/blob/0b0953060878becc3732962d7622ff48caab54ad/inspectors/opm.py#L22) and [using it](https://github.com/unitedstates/inspectors-general/blob/0b0953060878becc3732962d7622ff48caab54ad/inspectors/opm.py#L37-L38).

Scrapers are welcome to use any command line flags they want, **except** those used by the `igs` runner. Currently, that's `--safe` and `--only`.

Finally, scraper authors are encouraged to note a few things in comments at the top of the scraper:

* The **earliest available year** for reports.
* Any **additional command line options** you've chosen to support, besides `--since` and `--year`.
* Any **notes to pass on to the IG's web team**, about how they can make their website better and more reliable.

#### Report metadata

The `report` object must be a dict that contains the following **required fields**:

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

You can also **include any other fields** you think worth keeping.

The `report_id` only needs to be unique within that IG, so you can make it up from other fields. It does need to come out the same every time you run the script. In other words, **don't auto-increment a number** -- if the IG doesn't give you a unique ID already, append other fields together into a consistent, unique ID.

In some cases, an IG will not give a clear published date for a report. In these cases, we have a few additional options:

* If there are only a couple of reports with missing dates, hardcoding a mapping of report ids to published dates can often work well. See an example [here](https://github.com/unitedstates/inspectors-general/blob/658888d0d50be6429775dc8a92825837d602f836/inspectors/treasury.py#L69-73).
* For the websites of some agencies, the `Last-Modified` header lists the date when the report was added to the website which can be used as the `published_on` date. This option should not be used without significant spot-checking.
* If the website just lists the year the report was added, set the `published_on` to  November 1st of that year and also set `"estimated_date": True` in the report dictionary.

If none of these methods work, open an issue on this repo.

Finally, **err towards errors**: have your scraper choke and die on unexpected input. Better to be forced to discover it that way, then for incomplete or inaccurate data to be silently saved.

## Review process

Suggested instructions for people reviewing new scrapers:

* Verify that the scraper is getting every possible and useful category of report.
* Verify that the scraper is using HTTPS, if it's available.
* Run the scraper for its full archive but without downloading the reports, using `--dry_run` and `--since`.
* Review scraped metadata for a representative sample of years and report types to ensure sanity and quality.
* Keep an eye out for announcements, press releases, and other non-report data.

If the full dry run ran without errors, and the data looks good and complete:

* merge the scraper
* update the *pending* section of `safe.yml` with a *commented-out* line for the scraper.

**Adding to safe.yml**

The only people who should update `safe.yml` with uncommented lines are those who run servers managing complete synced archives of IG data.

Before adding a scraper to `safe.yml`, it's suggested that you allow a *full* download of the archive to complete (which will also test PDF download and metadata/text extraction code).

**Removing from safe.yml**

If a scraper is throwing **persistent** errors, remove it (comment it out) from `safe.yml` and open a ticket to discuss it.

Ephemeral errors (for example, from connection errors, or other erratically reproducible situations) should be reported as issues first, to be discussed.

### Resources

* [Matt Rumsey](https://twitter.com/mattrumsey) kindly [compiled a spreadsheet](https://docs.google.com/spreadsheet/ccc?key=0AoQuErjcV2a0dF9jUjRSczQ5WEVqd3RoS3dtLTdGQnc&usp=sharing) of IG offices. We used this to track activity during the initial scraping phase.

### Public domain

This project is [dedicated to the public domain](LICENSE). As spelled out in [CONTRIBUTING](CONTRIBUTING.md):

> The project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](http://creativecommons.org/publicdomain/zero/1.0/).

> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
