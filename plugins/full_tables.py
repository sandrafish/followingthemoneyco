from datasette import hookimpl


@hookimpl
async def extra_template_vars(template, datasette):
    if template != "index.html":
        return {}

    all_dbs = []
    for name, db in datasette.databases.items():
        if name.startswith("_"):
            continue
        table_names = await db.table_names()
        all_dbs.append({
            "name": name,
            "tables": [{"name": t} for t in table_names],
        })

    return {"all_databases_with_tables": all_dbs}
