from sqlalchemy import URL, make_url


def generate_url(
    drivername: str,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str,
) -> str:
    """
    Generate a SQL connection string given connection and authentication details.

    See also:
    - https://alembic.sqlalchemy.org/en/latest/tutorial.html#escaping-characters-in-ini-files
    - https://docs.sqlalchemy.org/en/13/core/engines.html#sqlalchemy.engine.url.URL
    """

    sqlalchemy_url = URL.create(drivername, username, password, host, port, database)
    stringified_sqlalchemy_url = sqlalchemy_url.render_as_string(hide_password=False)

    # assert make_url round trip
    assert make_url(stringified_sqlalchemy_url) == sqlalchemy_url

    # print(
    #     f"The correctly escaped string that can be passed "
    #     f"to SQLAlchemy make_url() and create_engine() is:"
    #     f"\n\n     {stringified_sqlalchemy_url!r}\n"
    # )

    return stringified_sqlalchemy_url

    percent_replaced_url = stringified_sqlalchemy_url.replace("%", "%%")

    # assert percent-interpolated plus make_url round trip
    assert make_url(percent_replaced_url % {}) == sqlalchemy_url

    # print(
    #     f"The SQLAlchemy URL that can be placed in a ConfigParser "
    #     f"file such as alembic.ini is:\n\n      "
    #     f"sqlalchemy.url = {percent_replaced_url}\n"
    # )

    return percent_replaced_url
