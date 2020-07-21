# Changelog

## 2.5 (beta-1) (2020-07-21)

- Add option to upload CSV directly
- Add snowflake connector
- Optimize some data
- Pin new dependencies
- Add Dockerfile

## 2.4 (2020-02-03)

- Fix Firefox compatibility
- Add configuration aids for running as systemd service, running on gunicorn behind AWS ELB that provides SSL

## 2.3 (2019-12-16)

- Fix handling of empty sheets

## 2.2 (2019-12-11)

- Update CoreUI, fix version, fix symlink creation in documentation
- Add MIT License
- Add Changelog

## 2.1 (2019-11-28)

- Bring back endpoint for VBA data source, plus fixes
- Fix redshift upload
- Fix date parsing from Excel by reading actual styles.xml
- Fix column trimming by early algorithm cut-off

## 2.0 (2019-10-30)

- Add a proper flask front-end for logging in and uploading files
- Add a JS-based Excel parser to extract data on the client side
- Convert old service endpoint to accept JSON from AJAX requests from front-end

## 1.0 (2019-10-30)

- Legacy release tag
