csvParser = (function() {
    return {
        parse: function(file) {
            var deferred = $.Deferred();
            file.text().then(function(text) {
                data = {};
                data[file.name.substr(0, file.name.length-4)] = text;

                deferred.resolve(data);
            });
            return deferred.promise();
        }
    };
})();