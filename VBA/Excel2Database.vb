Option Explicit

Private Const host = "http://localhost:5000"
Private Const token = ""

Public Sub submit_data()

    Dim payload         As String
    Dim response        As String
    Dim data            As String
    Dim lastCol         As Integer
    Dim lastRow         As Long
    Dim builder         As StringBuilder
    Dim i, j            As Integer
    
    With ActiveSheet
        lastCol = .Cells(1, columns.Count).End(xlToLeft).Column
        lastRow = Cells.Find(What:="*", After:=Range("A1"), LookIn:=xlValues, LookAt _
        :=xlPart, SearchOrder:=xlByRows, SearchDirection:=xlPrevious, MatchCase:= _
        False, SearchFormat:=False).Row
    End With
    
    Set builder = New StringBuilder
    
    For i = 1 To lastRow
        For j = 1 To lastCol
             builder.Append ActiveSheet.Cells(i, j)
             If Not (j = lastCol) Then builder.Append ("\t")
        Next j
        If Not (i = lastRow) Then builder.Append ("\n")
    Next i
    
    payload = _
    "{" & _
        """name"":""" & ActiveSheet.name & """," & _
        """token"":""" & token & """," & _
        """columns"":" & lastCol & "," & _
        """data"":""" & builder.ToString & """" & _
    "}"
    
    response = request(host, "submit", payload)
    MsgBox response

End Sub


Private Function request(host As String, endpoint As String, Optional payload As String = "") As String

    Const SXH_OPTION_IGNORE_SERVER_SSL_CERT_ERROR_FLAGS = 2
    Const SXH_SERVER_CERT_IGNORE_UNKNOWN_CA = 256
    Const SXH_SERVER_CERT_IGNORE_CERT_CN_INVALID = 4096
    Const WAIT_TIMEOUT = 60

    With CreateObject("MSXML2.ServerXMLHTTP")
        .Open IIf(payload = vbNullString, "GET", "POST"), host & "/" & endpoint, False
        .setOption SXH_OPTION_IGNORE_SERVER_SSL_CERT_ERROR_FLAGS, SXH_SERVER_CERT_IGNORE_CERT_CN_INVALID + SXH_SERVER_CERT_IGNORE_UNKNOWN_CA
        .setRequestHeader "Content-Type", "application/json"
        .Send payload
        .waitForResponse (WAIT_TIMEOUT)
        request = .responsetext
        .Abort
    End With
    
End Function

Public Function regExp(pattern As String, Text As String) As String
    
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


