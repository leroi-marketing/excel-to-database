Dim MyBuffer() As String
Dim MyCurrentIndex As Long
Dim MyMaxIndex As Long

' https://codereview.stackexchange.com/questions/67596/a-lightning-fast-stringbuilder

Private Sub Class_Initialize()

    MyCurrentIndex = 0
    MyMaxIndex = 16
    ReDim MyBuffer(1 To MyMaxIndex)

End Sub

'Appends the given Text to this StringBuilder
Public Sub Append(Text As String)

    MyCurrentIndex = MyCurrentIndex + 1

    If MyCurrentIndex > MyMaxIndex Then
        MyMaxIndex = 2 * MyMaxIndex
        ReDim Preserve MyBuffer(1 To MyMaxIndex)
    End If
    MyBuffer(MyCurrentIndex) = Text

End Sub

'Returns the text in this StringBuilder
'Optional Parameter: Separator (default vbNullString) used in joining components
Public Function ToString(Optional Separator As String = vbNullString) As String

    If MyCurrentIndex > 0 Then
        ReDim Preserve MyBuffer(1 To MyCurrentIndex)
        MyMaxIndex = MyCurrentIndex
        ToString = Join(MyBuffer, Separator)
    End If

End Function

