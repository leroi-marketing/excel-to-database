xlsxParser = (function() {
    function extractFiles(file) {
        var deferred = $.Deferred();

        zip.createReader(new zip.BlobReader(file), function(reader) {
            reader.getEntries(function(entries) {
                async.reduce(entries, {}, function(memo, entry, done) {
                    if(
                        entry.filename.match(/^xl\/worksheets\/.*?\.xml$/)
                        || entry.filename == 'xl/sharedStrings.xml'
                        || entry.filename == 'xl/workbook.xml') {
                        fname = entry.filename;
                        entry.getData(new zip.TextWriter(), function(data) {
                            memo[fname.split('/').pop()] = data;
                            done(null, memo);
                        });
                    }
                    else {
                        return done(null, memo);
                    }
                }, function(err, files) {
                    if (err) deferred.reject(err);
                    else deferred.resolve(files);
                });
            });
        }, function(error) { deferred.reject(error); });

        return deferred.promise();
    }

    function extractData(files) {
        var strings = $(files['sharedStrings.xml']);

        var colToInt = function(col) {
            var letters = ["", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"];
            var col = $.trim(col).split('');
            var n = 0;
            for (var i = 0; i < col.length; i++) {
                n *= 26;
                n += letters.indexOf(col[i]);
            }
            return n;
        };

        var Cell = function(cell) {
            cell = cell.split(/([0-9]+)/);
            this.row = parseInt(cell[1]);
            this.column = colToInt(cell[0]);
        };

        var sheets = $(files['workbook.xml']).find('sheet').map(
            (k, s)=>[s.attributes.name.nodeValue, s.attributes['r:Id'].nodeValue.substring(3)]
        );
        allData = {};
        for(var sheetId = 0; sheetId < sheets.length; sheetId += 2) {
            var sheet = $(files['sheet' + sheets[sheetId + 1] + '.xml']),
                sheetName = sheets[sheetId],
                data = [];

            var d = sheet.find('dimension').attr('ref').split(':');
            d = _.map(d, function(v) { return new Cell(v); });

            var cols = d[1].column - d[0].column + 1,
                rows = d[1].row - d[0].row + 1;

            _(rows).times(function() {
                var _row = [];
                _(cols).times(function() { _row.push(''); });
                data.push(_row);
            });

            sheet.find('sheetData row c').each(function(i, c) {
                var $cell = $(c),
                    cell = new Cell($cell.attr('r')),
                    type = $cell.attr('t'),
                    value = $cell.find('v').text(),
                    numtype = $cell.attr('s');

                if (type == 's') {
                    value = strings.find('si t').eq(parseInt(value)).text();
                }
                else if (numtype == '4' && value !== '') {
                    // Excel starts counting days since 1900-01-01. And that date is the FIRST day. So actually,
                    // in zero-based indexes, this is like Excel counting days since 1899-12-31.
                    // Except, someone who wrote an early version of Excel, incorrectly considered 1900 as a leap year
                    // therefore counting one extra day ever since February 28, 1900. This bug still exists due to
                    // backwards compatibility.
                    // Thus, count 1 day less because of the leap year bug.
                    value = parseInt(value);
                    if(!isNaN(value)) {
                        // 1900-01-01
                        var dt = new Date(1900, 0, 1);
                        // setDate(1) will keep it unchanged, so this would be completely compatible with Excel date,
                        // unlike adding days to already that 1 date. But this still has to fix the leap year bug
                        dt.setDate(parseInt(value) - 1);
                        value = dt.toISOString().split('T')[0];
                    }
                    else {
                        value = '';
                    }
                }

                data[cell.row - d[0].row][cell.column - d[0].column] = value;
            });
            // Clean up empty rows at the end, and scan for max row length
            maxColPosition = 0;
            for(var i = data.length - 1; i>=0; i--) {
                var row = data[i];
                var isEmpty = true;
                for(var j = row.length - 1; j>=0; j--) {
                    if(row[j] !== '') {
                        isEmpty = false;
                        if(j > maxColPosition) {
                            maxColPosition = j;
                        }
                        break;
                    }
                }
                if(!isEmpty) {
                    break;
                }
                else {
                    data.pop();
                }
            }
            // Shorten rows
            for(var i = data.length - 1; i>=0; i--) {
                data[i] = data[i].slice(0, maxColPosition + 1);
            }
            // Commit the data to the result
            allData[sheetName] = data;
        }
        return allData;
    }

    return {
        parse: function(file) {
            return extractFiles(file).pipe(function(files) {
                return extractData(files);
            });
        }
    }
})();
