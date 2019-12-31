xlsxParser = (function() {
    NodeList.prototype.filter = Array.prototype.filter;

    //TODO: NodeList.prototype.select = Array.prototype.map ?
    //TODO: NodeList.prototype.map = Array.prototype.map ?
    NodeList.prototype.select = function(ev) {
        var res = [];
        for(var i=0;i<this.length;i++) {
            res.push(ev(this[i]));
        }
        return res;
    };

    function extractFiles(file) {
        var deferred = $.Deferred();

        zip.createReader(new zip.BlobReader(file), function(reader) {
            reader.getEntries(function(entries) {
                async.reduce(entries, {}, function(memo, entry, done) {
                    if(
                        entry.filename.match(/^xl\/worksheets\/.*?\.xml$/)
                        || entry.filename == 'xl/sharedStrings.xml'
                        || entry.filename == 'xl/workbook.xml'
                        || entry.filename == 'xl/styles.xml') {
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
        var parser = new DOMParser();
        var strings = parser.parseFromString(files['sharedStrings.xml'], 'text/xml')
                            .childNodes[0]
                            .childNodes.select(n=>n.textContent);

        // OpenXML format IDs for dates. https://github.com/closedxml/closedxml/wiki/NumberFormatId-Lookup-Table
        // Times are not considered. Maybe later
        var dateStyles = {
            14: true,
            15: true,
            16: true,
            17: true,
            22: true,
            30: true
        };
        var styleXml = parser.parseFromString(files['styles.xml'], 'text/xml')
                             .childNodes[0];
        // Custom formats
        var numfmtsNodes = styleXml.childNodes.filter(n=>n.nodeName=='numFmts');
        if(numfmtsNodes.length > 0) {
            var customFormats = numfmtsNodes[0].childNodes.select(n=>({
                "code": n.attributes.formatCode.value,
                "id": parseInt(n.attributes.numFmtId.value)
            }));
            // If the format contains unescaped m, d or y, consider it a date format. Add the id to the dictionary
            for(var i = 0; i < customFormats.length; i++) {
                var fmt = customFormats[i];
                if(fmt.code.match(/(?<!\\)[mdy]/) !== null) {
                    dateStyles[fmt.id] = true;
                }
            }
        }

        // each element is referred by Excel sheets as an ordinal. If it's true, then the ordinal stands for a date format
        var areDates = styleXml.childNodes.filter(n=>n.nodeName=='cellXfs')[0]
                                          .childNodes
                                          .select(n=>dateStyles.hasOwnProperty(parseInt(n.attributes.numFmtId.value)));


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

        var re = new RegExp(/^([A-Z]+)(.*)$/);

        var Cell = function(cell) {
            cell = cell.match(re);
            this.row = parseInt(cell[2]);
            this.column = colToInt(cell[1]);
        };

        var sheets = $(files['workbook.xml']).find('sheet').map(
            (k, s)=>[s.attributes.name.nodeValue, s.attributes['r:Id'].nodeValue.substring(3)]
        );
        allData = {};
        
        for(var sheetId = 0; sheetId < sheets.length; sheetId += 2) {
            var sheet = parser.parseFromString(files['sheet' + sheets[sheetId + 1] + '.xml'], 'text/xml'),
                sheetName = sheets[sheetId],
                data = [];

            var d = sheet.childNodes[0]
                         .childNodes.filter(n=>n.nodeName=='dimension')[0].attributes.ref.value.split(':');
            if(d.length != 2) {
                continue;
            }
            d = d.map(v=>new Cell(v));

            var cols = d[1].column - d[0].column + 1,
                rows = d[1].row - d[0].row + 1;

            for(var rid = 0; rid < rows; rid++) {
                var _row = [];
                for(var cid=0; cid < cols; cid++) {
                    _row.push('');
                }
                data.push(_row);
            }

            var sheetData = sheet.childNodes[0].childNodes.filter(n=>n.nodeName=='sheetData')[0];
            var rows = sheetData.childNodes;
            totalRows = sheetData.childElementCount;
            for(var rIndex = 0; rIndex < totalRows; rIndex++) {
                var row = rows[rIndex];
                var cells = row.childNodes;
                var totalCells = row.childElementCount;
                for(var cIndex = 0; cIndex < totalCells; cIndex ++) {
                    var $cell = cells[cIndex];
                    var cell = new Cell($cell.attributes.r.value),
                        type = $cell.attributes.t,
                        value = $cell.childNodes.filter(n=>n.nodeName=='v'),
                        numtype = $cell.attributes.s;

                    if (value.length) {
                        value = value[0].textContent;
                    }
                    else {
                        value = '';
                    }

                    if (type && type.value == 's') {
                        value = strings[parseInt(value)];
                    }
                    else if (numtype && parseInt(numtype.value) < areDates.length && areDates[parseInt(numtype.value)] && value !== '') {
                        // Excel starts counting days since 1900-01-01. And that date is the FIRST day.
                        value = parseInt(value);
                        if(!isNaN(value)) {
                            // 1900-01-01
                            var dt = new Date(1900, 0, 1);
                            // setDate(1) will keep it unchanged, so this would be completely compatible with Excel
                            // date, unlike adding days to already that 1 date. But this still has to fix the leap year
                            // bug
                            dt.setDate(parseInt(value));
                            value = dt.toISOString().split('T')[0];
                        }
                        else {
                            value = '';
                        }
                    }

                    data[cell.row - d[0].row][cell.column - d[0].column] = value;
                }
            }

            // Clean up empty rows at the end, and scan for max row length
            var maxColPosition = 0;
            var haveRowsBelow = false;
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
                    haveRowsBelow = true;
                }
                else if(!haveRowsBelow) {
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
