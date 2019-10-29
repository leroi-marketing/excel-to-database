var isAdvancedUpload = function() {
    var div = document.createElement('div');
    return (('draggable' in div) || ('ondragstart' in div && 'ondrop' in div)) && 'FormData' in window && 'FileReader' in window;
}();


$("document").ready(function() {
    var $form = $('form');

    if (isAdvancedUpload) {
        $form.addClass('has-advanced-upload');
    }

    if (isAdvancedUpload) {
        // Inject a custom xhr object for jQuery AJAX functionality
        // Basically this attaches progress events that help us build a progress bar to help with larger uploads
        function GetXhr(uploadProgressBar, downloadProgressBar) {
            return function() {
                var xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener(
                    "progress",
                    function(evt) {
                        if (evt.lengthComputable) {
                            var percentComplete = Math.round(evt.loaded / evt.total * 100);
                            uploadProgressBar.setProgress(percentComplete);
                        }
                    },
                    false
                );
                xhr.addEventListener(
                    "progress",
                    function(evt) {
                        if (evt.lengthComputable) {
                            var percentComplete = Math.round(evt.loaded / evt.total * 100);
                            downloadProgressBar.setProgress(percentComplete);
                        }
                    },
                    false
                );
                return xhr;
            }
        }

        // Progress Bar object creator.
        function GetProgressBar() {
            el = $('<div class="row" style="padding-bottom: 20px;"><div class="col-12">\
                    <div class="progress"><div class="progress-bar progress-bar-striped progress-bar-animated" \
                    role="progressbar" \
                    aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style="width: 75%"></div></div>\
                    </div></div>');
            return {
                dom: el,
                setProgress: function(progress) {
                    el.find(".progress-bar")
                        .attr("aria-valuenow", progress)
                        .css("width", progress + "%");
                }
            }
        }

        // attach DOM events
        $("#resetbtn").on('click', function() {
            window.location.reload();
        });
        $("#submitbtn").on('click', function() {
            var selected = $("#sheet_selectors input.sheet_selector:checked");
            if(selected.length == 0) {
                $("#error_div .error").html('<span class="message">Please select at least one sheet to upload.</span>');
            }
            else {
                pbar = GetProgressBar();
                $form.after(pbar.dom);
                pbar.setProgress(0);
                $("#error_div .error").html("");
                $("#success_div .success").html("");
                $("#submitbtn, #resetbtn").hide();
                var payload = {};
                // Build payload from selected checkboxes
                selected.each(function(index, cb) {
                    $cb = $(cb);
                    payload[$cb.data('sheetName')] = $cb.data('data');
                });
                // Send data to the server
                $.ajax({
                    xhr: GetXhr(pbar, pbar),
                    type: 'POST',
                    url: "/submit",
                    data: JSON.stringify(payload),
                    contentType: 'application/json',
                    success: function(msg) {
                        if(msg.error) {
                            $("#submitbtn, #resetbtn").show();
                            $("#error_div .error").html('<span class="message">Upload failed</span>');
                        }
                        else {
                            $("#success_div .success").html('<span class="message">Upload successful</span>');
                        }
                    },
                    error: function() {
                        $("#error_div .error").html('<span class="message">Upload failed: internal server error</span>');
                        $("#submitbtn, #resetbtn").show();
                    },
                    complete: function() {
                        pbar.dom.remove();
                    }
                });
            }
        });

        // This is called when data is decoded from a picked spreadsheet
        function HandleData(data) {
            // Basically manipulate some DOM, create checkboxes for each sheet, attach data to the DOM.
            $("#submitbtn, #resetbtn").show();
            $("#excel, #excel + label").hide();
            $("div.container > div.row > div").removeClass("col-md-8").addClass("col-md-12");
            var titleDom = $(".card-body h1").text("Choose sheets to upload");

            var newRowDim = $('<div class="row">');
            titleDom.after(newRowDim);

            var colDim = $('<div class="col-12" id="sheet_selectors">');
            newRowDim.append(colDim);

            var id = 0;
            for(var sheetName in data) {
                if(data.hasOwnProperty(sheetName)) {
                    id += 1;
                    var cb = $('<input type="checkbox" class="sheet_selector" id="cb' + id + '"/>')
                    colDim.append(cb);
                    cb.after('<label for="cb' + id + '"></label><br/>');
                    cb.next("label").text(sheetName + ' (' + data[sheetName].length + ' rows)');

                    cb.data("sheetName", sheetName);
                    cb.data("data", data[sheetName]);
                }
            }

            newRowDim.after($('<div class="row"><div id="error_div" class="col-12"><em class="error"></em></div></div>'));
            newRowDim.after($('<div class="row"><div id="success_div" class="col-12"><em class="success"></em></div></div>'));
        }

        // Process excel file that was picked in the web frontend
        function ProcessExcel(file) {
            xlsxParser.parse(file).then(function(data) {
                HandleData(data);
            }, function(err) {
                console.log('error', err);
            });
        }

        $form.on('drag dragstart dragend dragover dragenter dragleave drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
        })
        .on('dragover dragenter', function() {
            $form.addClass('is-dragover');
        })
        .on('dragleave dragend drop', function() {
            $form.removeClass('is-dragover');
        })
        .on('drop', function(e) {
            var droppedFiles = e.originalEvent.dataTransfer.files;
            ProcessExcel(droppedFiles[0]);
        });

        $("#excel").on("change", function(e) {
            files = e.target.files;
            ProcessExcel(files[0]);
        });
    }
});
