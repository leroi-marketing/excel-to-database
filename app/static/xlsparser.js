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
            (k, s)=>[s.attributes.name.nodeValue, s.attributes.sheetid.nodeValue]
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
                    value = $cell.find('v').text();

                if (type == 's') value = strings.find('si t').eq(parseInt(value)).text();

                data[cell.row - d[0].row][cell.column - d[0].column] = value;
            });
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
