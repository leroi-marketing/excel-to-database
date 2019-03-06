Option Explicit

Private Const host = "https://host:5000"
Private Const token = "password"

Public Sub query_data()

    Dim response        As String
    Dim json            As Object
    Dim columns         As Integer
    Dim data()          As String
    Dim ws              As Worksheet

    response = request(host, "query")
    
    columns = regExp("""columns"":""([^""]*)""", response)
    data = Split(regExp("""data"":""([^""]*)""", response), vbTab)

    ActiveWorkbook.Sheets.Add after:=Worksheets(Worksheets.Count)
    Set ws = Worksheets(Worksheets.Count)
    write_data ws, columns, data
    format_header ws, columns

End Sub

Public Sub submit_data()

    Dim payload         As String
    Dim response        As String
    Dim data            As String
    Dim lastCol         As Integer
    Dim lastRow         As Integer
    Dim i, j            As Integer
    
    With ActiveSheet
        lastCol = .Cells(1, columns.Count).End(xlToLeft).Column
        lastRow = .Cells(Rows.Count, "A").End(xlUp).Row
    End With
    
    For i = 1 To lastRow
        For j = 1 To lastCol
             data = data & ActiveSheet.Cells(i, j)
             If Not (i = lastRow And j = lastCol) Then data = data & "\t"
        Next j
    Next i
    
    payload = _
    "{" & _
        """name"":""" & ActiveSheet.name & """," & _
        """token"":""" & token & """," & _
        """columns"":" & lastCol & "," & _
        """data"":""" & data & """" & _
    "}"
    
    response = request(host, "submit", payload)
    MsgBox (response)

End Sub


Private Function request(host As String, endpoint As String, Optional payload As String = "") As String

    Const SXH_OPTION_IGNORE_SERVER_SSL_CERT_ERROR_FLAGS = 2
    Const SXH_SERVER_CERT_IGNORE_UNKNOWN_CA = 256
    Const SXH_SERVER_CERT_IGNORE_CERT_CN_INVALID = 4096

    With CreateObject("MSXML2.ServerXMLHTTP")
        .Open IIf(payload = vbNullString, "GET", "POST"), host & "/" & endpoint, False
        .setOption SXH_OPTION_IGNORE_SERVER_SSL_CERT_ERROR_FLAGS, SXH_SERVER_CERT_IGNORE_CERT_CN_INVALID + SXH_SERVER_CERT_IGNORE_UNKNOWN_CA
        .setRequestHeader "Content-Type", "application/json"
        .Send payload
        request = .responsetext
        .Abort
    End With
    
End Function

Public Function regExp(pattern As String, text As String) As String
    
    Dim regExpObj          As Object
    Dim reMatches          As Object

    Set regExpObj = CreateObject("vbscript.regexp")
    With regExpObj
        .MultiLine = False
        .Global = False
        .IgnoreCase = False
        .pattern = pattern
    End With

    If reMatches.Count > 0 Then
        regExp = reMatches(0)
    Else
        regExp = vbNullString
    End If

End Function

Private Sub write_data(ws As Worksheet, columns As Integer, data() As String)

    Dim i, j            As Integer
    Dim entry           As Variant

    With ws
        .Cells.Delete

        i = 1: j = 1
        For Each entry In data
            .Cells(i, j).Value = entry
            j = j + 1
            If j = columns + 1 Then j = 1: i = i + 1
        Next entry

    End With

End Sub

Private Sub format_header(ws As Worksheet, columns As Integer)

    With ws
        With .Range(.Cells(1, 1), .Cells(1, columns))
            .Interior.Color = RGB(200, 200, 200)
            .Font.Bold = True
            .AutoFilter
            .EntireColumn.AutoFit
        End With

        .Range("A2").Select
        ActiveWindow.FreezePanes = True
    End With

End Sub
