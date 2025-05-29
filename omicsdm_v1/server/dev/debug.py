from flask_sqlalchemy import get_debug_queries


def sql_debug(response):
    """
    based on
    https://gist.github.com/debashisdeb/7d6640d8cd6d3b9fb2c51695d6cda882
    """
    queries = list(get_debug_queries())
    query_str = ""
    total_duration = 0
    for query in queries:
        duration = query.duration * 1000

        try:
            stmt = query.statement % query.parameters
        except Exception:
            # handler for the case when query.parameters is a list
            stmt = ""
            for e in query.parameters:
                stmt += f"{query.statement % e}\n"

        query_str += f"{stmt}\nDuration: {duration:.2f}ms\n\n"
        total_duration += duration

    print("=" * 80)
    print(f"SQL: {len(queries)} Queries executed in {total_duration:.2f}ms")
    print("=" * 80)
    print(query_str.rstrip("\n"))
    print("=" * 80 + "\n")

    return response
