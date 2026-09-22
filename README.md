# followingthemoneyco
Once again, TRACER data could use some reogranization, so i'm doing it for the 2026 cycle. Maybe someday they'll fix it.

# The website
You can find it at [followingthemoneyco.com](https://followingthemoneyco.com/). The main page offers general information on how to use the data. It's based on bulk data for contributions, expenditures and loans with files cleaned of random characters using BBEdit and csvclean in the command line, then analyzed with Python/Pandas in Jupyter notebooks. This enables matching of committee IDs with the offices candidates are running for, which the bulk data doesn't do.

# The database
`camp_fin_2026.db` is about 52 MB, so only the gzipped copy
(`camp_fin_2026.db.gz`, under 10 MB) is committed — the raw `.db` is
gitignored. No tables are dropped; it's the same database, just compressed.

| File | Purpose |
|---|---|
| `compress-db.sh` | Rebuilds `camp_fin_2026.db.gz` from your local `.db` |
| `build.sh` | Deploy-time step: installs deps, decompresses, verifies every table |
| `railway.json` | Points Railway at `build.sh` and the datasette start command |
| `serve.sh` | Local preview; decompresses the `.db` first if it's missing |

After a data refresh:

```bash
./compress-db.sh
git add camp_fin_2026.db.gz
git commit -m "Data through $(date +%Y-%m-%d)" && git push
```
