"""Totals page data: top races and top committees by money raised and spent.

Datasette calls extra_template_vars for custom pages under templates/pages/,
which is how pages/totals.html gets its charts. The queries are full-table
aggregates, so results are cached in memory after the first request -- the
database only changes on redeploy, which restarts the process.
"""

from datasette import hookimpl

DB = "camp_fin_2026"
TOP_COMMITTEES = 20

# Regent and state Board of Education races raise little next to the four
# statewide offices, so they are left out of the statewide chart.
STATEWIDE_SKIP = ("CU_District", "Bd. Ed.")

_cache = {}


def money(n):
    """Compact dollar label: $7.4M, $985K, $412."""
    n = float(n or 0)
    a = abs(n)
    if a >= 1_000_000:
        return f"${n / 1_000_000:,.1f}M"
    if a >= 1_000:
        return f"${n / 1_000:,.0f}K"
    return f"${n:,.0f}"


def party_bucket(party):
    """Fold the long tail of parties into D / R / Other.

    Only Democratic and Republican get their conventional colors; everything
    else shares a neutral swatch and relies on its direct label. Colorado has
    real third-party candidates (7 Libertarians statewide), so Other is a
    genuine bucket rather than a catch-all for bad data.
    """
    raw = (party or "").strip()
    p = raw.lower()
    if p.startswith("democrat"):
        return "d", "D", "Democratic"
    if p.startswith("republican"):
        return "r", "R", "Republican"
    return "o", (raw[:1].upper() or "?"), (raw or "Other")


def _pct(value, scale):
    if not scale or value <= 0:
        return 0.0
    return round(min(value / scale, 1.0) * 100, 2)


async def candidate_chart(db, *, table, race_col, amount_col, title, subtitle,
                          top, party_from=None, skip_prefixes=()):
    """Top races, each broken out by candidate.

    All bars share one scale (the largest single candidate total in the chart)
    so a bar in one race is directly comparable to a bar in another.
    """
    if party_from:
        # house_exp has no Party column; borrow it from house_cont, where every
        # (district, candidate) pair in house_exp is present.
        sql = f'''
            select e."{race_col}" as race, e.candidate_name as name,
                   c."Party" as party, sum(e."{amount_col}") as total
            from "{table}" e
            left join (select distinct "{race_col}", candidate_name, "Party"
                       from "{party_from}") c
              on c."{race_col}" = e."{race_col}"
             and c.candidate_name = e.candidate_name
            group by 1, 2, 3
        '''
    else:
        sql = f'''
            select "{race_col}" as race, candidate_name as name,
                   "Party" as party, sum("{amount_col}") as total
            from "{table}"
            group by 1, 2, 3
        '''

    races = {}
    for row in (await db.execute(sql)).rows:
        race = row["race"] or "(not stated)"
        if any(race.startswith(prefix) for prefix in skip_prefixes):
            continue
        entry = races.setdefault(race, {"race": race, "total": 0.0, "items": []})
        total = float(row["total"] or 0)
        cls, mark, label = party_bucket(row["party"])
        entry["total"] += total
        entry["items"].append({
            "name": row["name"] or "(not stated)",
            "total": total,
            "total_fmt": money(total),
            "party_cls": cls,
            "party_mark": mark,
            "party_label": label,
        })

    top = sorted(races.values(), key=lambda r: r["total"], reverse=True)[:top]
    scale = max((i["total"] for r in top for i in r["items"]), default=0)

    for race in top:
        race["items"] = [i for i in race["items"] if i["total"] > 0]
        race["items"].sort(key=lambda i: i["total"], reverse=True)
        race["total_fmt"] = money(race["total"])
        for item in race["items"]:
            item["pct"] = _pct(item["total"], scale)
            item["tooltip"] = (
                f'{item["name"]} ({item["party_label"]}) — '
                f'{race["race"]}: {item["total_fmt"]}'
            )

    seen, legend = set(), []
    for race in top:
        for item in race["items"]:
            if item["party_cls"] not in seen:
                seen.add(item["party_cls"])
                legend.append({
                    "cls": item["party_cls"],
                    "label": "Other parties" if item["party_cls"] == "o"
                             else item["party_label"],
                })
    legend.sort(key=lambda x: {"d": 0, "r": 1, "o": 2}[x["cls"]])

    return {
        "kind": "grouped",
        "title": title,
        "subtitle": subtitle,
        "scale_fmt": money(scale),
        "legend": legend if len(legend) > 1 else [],
        "groups": top,
        "table": table,
        "empty": not top,
    }


async def committee_chart(db, *, table, amount_col, title, subtitle, split_type):
    """Straight ranked committees -- no race to group by."""
    sql = f'''
        select committee as name, committee_type as ctype,
               sum("{amount_col}") as total
        from "{table}"
        group by 1, 2
        order by total desc
        limit {TOP_COMMITTEES}
    '''
    rows = list((await db.execute(sql)).rows)
    scale = max((float(r["total"] or 0) for r in rows), default=0)

    # A 527 and an IEC of the same name are different committees and must not
    # be merged -- the site's own guidance for reading this table.
    types = []
    for r in rows:
        if r["ctype"] and r["ctype"] not in types:
            types.append(r["ctype"])
    type_cls = {t: f"c{i + 1}" for i, t in enumerate(sorted(types))}

    items = []
    for r in rows:
        total = float(r["total"] or 0)
        ctype = r["ctype"] or "(not stated)"
        items.append({
            "name": r["name"] or "(not stated)",
            "total": total,
            "total_fmt": money(total),
            "type_label": ctype,
            "type_cls": type_cls.get(r["ctype"], "c1") if split_type else "c1",
            "pct": _pct(total, scale),
            "tooltip": f'{r["name"]} — {ctype}: {money(total)}',
        })

    legend = []
    if split_type and len(types) > 1:
        legend = [{"cls": type_cls[t], "label": t} for t in sorted(types)]

    return {
        "kind": "ranked",
        "title": title,
        "subtitle": subtitle,
        "scale_fmt": money(scale),
        "legend": legend,
        "items": items,
        "table": table,
        "empty": not items,
    }


async def build_charts(datasette):
    db = datasette.get_database(DB)
    charts = []

    candidates = [
        ("Statewide candidates", "Office", "state_cont", "state_exp", None,
         20, STATEWIDE_SKIP),
        ("State House", "District", "house_cont", "house_exp", "house_cont",
         15, ()),
        ("State Senate", "District", "senate_cont", "senate_exp", None,
         15, ()),
    ]
    for label, race_col, cont, exp, party_from, top, skip in candidates:
        span = "Races" if skip else f"Top {top} races"
        charts.append(await candidate_chart(
            db, table=cont, race_col=race_col, amount_col="contribution_amount",
            title=f"{label} — contributions", top=top, skip_prefixes=skip,
            subtitle=f"{span} by money raised, broken out by candidate",
        ))
        charts.append(await candidate_chart(
            db, table=exp, race_col=race_col, amount_col="expenditure_amount",
            title=f"{label} — expenditures", top=top, skip_prefixes=skip,
            subtitle=f"{span} by money spent, broken out by candidate",
            party_from=party_from,
        ))

    # Super PACs are left out until the 527 / IEC classification is settled --
    # a 527 and an IEC of the same name are different committees, and merging
    # them would double count.
    committees = [
        ("Issue committees", "issue_comm_cont", "issue_comm_exp", False),
    ]
    for label, cont, exp, split_type in committees:
        charts.append(await committee_chart(
            db, table=cont, amount_col="contribution_amount",
            title=f"{label} — contributions",
            subtitle=f"Top {TOP_COMMITTEES} committees by money raised",
            split_type=split_type,
        ))
        charts.append(await committee_chart(
            db, table=exp, amount_col="expenditure_amount",
            title=f"{label} — expenditures",
            subtitle=f"Top {TOP_COMMITTEES} committees by money spent",
            split_type=split_type,
        ))

    return charts


@hookimpl
def extra_template_vars(template, datasette):
    if template != "pages/totals.html":
        return {}

    async def inner():
        if "charts" not in _cache:
            _cache["charts"] = await build_charts(datasette)
        return {"charts": _cache["charts"], "db_name": DB}

    return inner
