# Eval set toward ≥20 pieces (R7)

Each row needs: photo(s), **user-known dims**, materials brief. IoU trusted only for studio photos.

| # | id | Class | Photo | Dims | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | chair_04 | chair | chairs/chair_04.jpg | catalog in json | in pack |
| 2 | chair_02 | chair | chairs/chair_02.jpg | tape/brief | in pack (IoU untrusted) |
| 3 | case_01 | bookshelf | cases/case_01.jpg | **user 48×12×71 in** | in pack |
| 4 | stool_01 | stool | — | — | oracle only / need photo |
| 5 | — | sideboard/console | *user* | *user* | open |
| 6 | — | table | *user* | *user* | open |
| 7 | — | cabinet+doors | *user* | *user* | open |
| 8 | — | organic / shaped | *user* | *user* | open |
| 9–20 | — | mix | *user* | *user* | open |

Add pieces by dropping `evals/photos/<pack>/<id>.jpg` + `<id>.json` with `source.dims_mm` from the user, then extend `python -m furniture_cad blind --ids …`.
