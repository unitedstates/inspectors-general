## Inspectors General

A project to collect reports from the offices of Inspectors General across the federal government.

**Currently**: Write scrapers for the highest priority IG offices, as highlighted in yellow [in this spreadsheet](https://docs.google.com/spreadsheet/ccc?key=0AoQuErjcV2a0dF9jUjRSczQ5WEVqd3RoS3dtLTdGQnc&usp=sharing).

### Using

To run an individual agency scraper, just execute its file directly. For example:

```bash
python inspectors/usps.py
```

This will fetch the latest reports from the [Inspector General for the US Postal Service](http://uspsoig.gov) and write them to disk, along with JSON metadata.

Reports are broken up by agency, and by year. So a USPS IG report from 2013 with a scraper-determined ID of `no-ar-13-010` will create the following files:

```
/data/usps/2013/no-ar-13-010/report.json
/data/usps/2013/no-ar-13-010/report.pdf
/data/usps/2013/no-ar-13-010/report.txt
```

Metadata for a report is at `report.json`. The original report will be saved at `report.pdf` (the extension will match the original, it may not be `.pdf`). The text from the report will be extracted to `report.txt`.


### Contributing a Scraper

The easiest way is to start by copying `scraper.py.template` to `inspectors/[agency].py`, where "[agency]" is the filename-friendly handle of the agency you want to scrape. For example, our scraper for the US Postal Service is [usps.py](https://github.com/unitedstates/inspectors-general/blob/master/inspectors/usps.py).

The template has a suggested workflow and set of methods, but all your task **needs** to do is start execution in a `run` method, and call `inspector.save_report(report)` for every report, where `report` is a dict of details that contains the following required fields:

* `inspector` - The handle you chose for the agency. e.g. "usps"
* `report_id` - A string usable as an ID for the report.
* `title` - Title of report.
* `url` - Link to report.
* `published_on` - Date of publication, in `YYYY-MM-DD` format.
* `year` - Year of publication.
* `file_type` - "pdf", or whatever file extension the report has.

The `report_id` only needs to be unique within that agency, so you can make it up from other fields. It does need to come out the same every time you run the script. In other words, Don't auto-increment a number -- append other fields together if the agency doesn't give you anything.

## Public domain

This project is [dedicated to the public domain](LICENSE). As spelled out in [CONTRIBUTING](CONTRIBUTING.md):

> The project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication][CC0].

> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.

> [CC0]: http://creativecommons.org/publicdomain/zero/1.0/