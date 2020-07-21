import csv
import io


def sniff_delimiter(text: str, candidates=",;|\t", default=','):
    stream = io.StringIO(text)
    max_c_count = 0
    max_c = default
    for c in candidates:
        stream.seek(0)
        reader = csv.reader(stream, delimiter=c)
        try:
            row_length = len(next(reader))
            for row in reader:
                if len(row) != row_length:
                    raise Exception("Row length differs")
        except:
            continue
        if max_c_count < row_length:
            max_c_count = row_length
            max_c = c
    return max_c


if __name__=="__main__":
    assert sniff_delimiter("""c1|c2|c3
a ;b ;c;|d|e
""") == '|'
    assert sniff_delimiter("""c1c2|c3
a b c|d|e
""") == ','
