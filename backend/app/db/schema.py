import sqlite3

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS stocks (
        code        TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        market      TEXT NOT NULL,
        industry    TEXT,
        total_share REAL,
        float_share REAL,
        list_date   TEXT,
        updated_at  TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quotes (
        code          TEXT PRIMARY KEY,
        name          TEXT,
        price         REAL,
        open          REAL,
        high          REAL,
        low           REAL,
        last_close    REAL,
        change_amt    REAL,
        change_pct    REAL,
        volume        REAL,
        amount        REAL,
        turnover_pct  REAL,
        pe_ttm        REAL,
        pe_static     REAL,
        pb            REAL,
        mcap_yi       REAL,
        float_mcap_yi REAL,
        limit_up      REAL,
        limit_down    REAL,
        vol_ratio     REAL,
        amplitude_pct REAL,
        updated_at    TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS klines (
        code      TEXT NOT NULL,
        category  INTEGER NOT NULL,
        datetime  TEXT NOT NULL,
        open      REAL,
        close     REAL,
        high      REAL,
        low       REAL,
        volume    REAL,
        amount    REAL,
        PRIMARY KEY (code, category, datetime)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_klines_code_cat ON klines(code, category)",
    """
    CREATE TABLE IF NOT EXISTS reports (
        info_code         TEXT PRIMARY KEY,
        code              TEXT NOT NULL,
        title             TEXT NOT NULL,
        publish_date      TEXT,
        org_name          TEXT,
        rating            TEXT,
        industry          TEXT,
        predict_this_eps  REAL,
        predict_next_eps  REAL,
        predict_next2_eps REAL,
        pdf_path          TEXT,
        created_at        TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_reports_code ON reports(code, publish_date DESC)",
    """
    CREATE TABLE IF NOT EXISTS ths_hot (
        date         TEXT NOT NULL,
        code         TEXT NOT NULL,
        name         TEXT,
        reason       TEXT,
        change_pct   REAL,
        turnover_pct REAL,
        close_price  REAL,
        volume       REAL,
        amount       REAL,
        big_net      REAL,
        market       TEXT,
        PRIMARY KEY (date, code)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ths_hot_date ON ths_hot(date)",
    """
    CREATE TABLE IF NOT EXISTS north_flow (
        date   TEXT NOT NULL,
        time   TEXT NOT NULL,
        hgt_yi REAL,
        sgt_yi REAL,
        PRIMARY KEY (date, time)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS news (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        code       TEXT,
        source     TEXT NOT NULL,
        title      TEXT NOT NULL,
        content    TEXT,
        url        TEXT,
        pub_time   TEXT,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_news_code ON news(code, pub_time DESC)",
    """
    CREATE TABLE IF NOT EXISTS analyst_forecasts (
        code          TEXT NOT NULL,
        year          TEXT NOT NULL,
        analyst_count INTEGER,
        eps_min       REAL,
        eps_mean      REAL,
        eps_max       REAL,
        industry_avg  REAL,
        updated_at    TEXT NOT NULL,
        PRIMARY KEY (code, year)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name  TEXT NOT NULL,
        status     TEXT NOT NULL,
        detail     TEXT,
        started_at TEXT NOT NULL,
        ended_at   TEXT
    )
    """,
    # === 全A扫描结果 ===
    """
    CREATE TABLE IF NOT EXISTS scan_sessions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at    TEXT NOT NULL,
        ended_at      TEXT,
        total_scanned INTEGER DEFAULT 0,
        results_count INTEGER DEFAULT 0,
        scan_time_sec REAL DEFAULT 0,
        status        TEXT DEFAULT 'running'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scan_items (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id      INTEGER NOT NULL,
        code            TEXT NOT NULL,
        name            TEXT NOT NULL,
        price           REAL,
        change_pct      REAL,
        mcap            REAL,
        turnover_pct    REAL,
        pe_ttm          REAL,
        pb              REAL,
        signal_count    INTEGER DEFAULT 0,
        avg_confidence  REAL,
        composite_score REAL,
        tech_score      REAL,
        strategies      TEXT,
        tech_signals    TEXT,
        top_reason      TEXT,
        created_at      TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES scan_sessions(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_scan_items_session ON scan_items(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_scan_items_code ON scan_items(code)",
    "CREATE INDEX IF NOT EXISTS idx_scan_items_score ON scan_items(composite_score DESC)",
    # === 每日推荐 ===
    """
    CREATE TABLE IF NOT EXISTS daily_picks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT NOT NULL,
        code        TEXT NOT NULL,
        name        TEXT NOT NULL,
        level       TEXT,
        price       REAL,
        stop_loss   REAL,
        target      REAL,
        confidence  REAL,
        reason      TEXT,
        risk        TEXT,
        strategy    TEXT,
        created_at  TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_daily_picks_date ON daily_picks(date)",
    "CREATE INDEX IF NOT EXISTS idx_daily_picks_code ON daily_picks(code)",
    # === 策略信号 ===
    """
    CREATE TABLE IF NOT EXISTS signal_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT NOT NULL,
        code        TEXT NOT NULL,
        name        TEXT NOT NULL,
        strategy    TEXT NOT NULL,
        confidence  REAL,
        price       REAL,
        stop_loss   REAL,
        target      REAL,
        reason      TEXT,
        created_at  TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_signal_log_date ON signal_log(date)",
    "CREATE INDEX IF NOT EXISTS idx_signal_log_strategy ON signal_log(strategy, date)",
    # === 模拟交易 ===
    """
    CREATE TABLE IF NOT EXISTS trade_reports (
        date            TEXT PRIMARY KEY,
        initial_capital REAL,
        cash            REAL,
        position_value  REAL,
        total_value     REAL,
        total_profit    REAL,
        total_profit_pct REAL,
        today_pnl       REAL,
        position_count  INTEGER,
        trade_count     INTEGER,
        buy_count       INTEGER,
        sell_count      INTEGER,
        buy_amount      REAL,
        sell_amount     REAL,
        report_json     TEXT,
        created_at      TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trade_orders (
        order_id    TEXT PRIMARY KEY,
        date        TEXT NOT NULL,
        code        TEXT NOT NULL,
        name        TEXT,
        direction   TEXT,
        price       REAL,
        volume      INTEGER,
        amount      REAL,
        status      TEXT,
        strategy    TEXT,
        reason      TEXT,
        created_at  TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_trade_orders_date ON trade_orders(date)",
    # === 键值存储(引擎状态等) ===
    """
    CREATE TABLE IF NOT EXISTS kv_store (
        key        TEXT PRIMARY KEY,
        value      TEXT,
        updated_at TEXT
    )
    """,
]


def create_tables(conn: sqlite3.Connection):
    for sql in TABLES:
        conn.execute(sql)
