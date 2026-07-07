#auth.py
# handles all login and user management
#YAML---> simplifies the file format uesd to store configurtion data in human readable way
# auth.py
# handles all login and user management
# ── Now backed by MySQL instead of a flat users.yaml file ──

import os
import yaml
from yaml.loader import SafeLoader
import streamlit as st
import streamlit_authenticator as stauth
import mysql.connector
from mysql.connector import errorcode

OLD_YAML_FILE = "users.yaml"   # only used for one-time migration if it exists

COOKIE_CONFIG = {
    "expiry_days": 30,
    "key": "study_planner_key",
    "name": "study_planner_cookie",
}


def _get_mysql_settings():
    """
    Reads MySQL connection details from .streamlit/secrets.toml:

        [mysql]
        host = "localhost"
        port = 3306
        user = "root"
        password = "your-password"
        database = "studyplanner_project"

    Falls back to sensible local defaults if secrets aren't set, so the
    app doesn't crash outright — but you should set real secrets for
    anything beyond local testing.
    """
    try:
        cfg = st.secrets["mysql"]
        return {
            "host": cfg.get("host", "localhost"),
            "port": int(cfg.get("port", 3306)),
            "user": cfg.get("user", "root"),
            "password": cfg.get("password", ""),
            "database": cfg.get("database", "study_planner"),
        }
    except Exception:
        return {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "study_planner",
        }


def _get_connection():
    """
    Opens a MySQL connection, creating the database and table on first
    run if they don't exist yet.
    """
    settings = _get_mysql_settings()

    conn = mysql.connector.connect(
        host=settings["host"],
        port=settings["port"],
        user=settings["user"],
        password=settings["password"],
    )
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{settings['database']}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    conn.commit()
    cursor.close()
    conn.close()

    conn = mysql.connector.connect(
        host=settings["host"],
        port=settings["port"],
        user=settings["user"],
        password=settings["password"],
        database=settings["database"],
    )
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(100) PRIMARY KEY,
            name     VARCHAR(150) NOT NULL,
            email    VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()
    return conn


def _migrate_from_yaml_if_needed(conn):
    """
    One-time migration: if an old users.yaml exists and the users table
    is empty, copy those accounts over. Safe to leave in permanently —
    it's a no-op once the table has rows or the yaml file is gone.
    """
    if not os.path.exists(OLD_YAML_FILE):
        return

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    existing = cursor.fetchone()[0]
    if existing > 0:
        cursor.close()
        return

    with open(OLD_YAML_FILE) as f:
        old_config = yaml.load(f, Loader=SafeLoader)

    old_users = old_config.get("credentials", {}).get("usernames", {})
    for username, info in old_users.items():
        cursor.execute(
            "INSERT IGNORE INTO users (username, name, email, password) VALUES (%s, %s, %s, %s)",
            (username, info.get("name", username), info.get("email", ""), info.get("password", ""))
        )
    conn.commit()
    cursor.close()


def _ensure_default_admin(conn):
    """Create the default admin/admin123 account only if the table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute(
            "INSERT INTO users (username, name, email, password) VALUES (%s, %s, %s, %s)",
            ("admin", "Admin_User", "admin@email.com", stauth.Hasher.hash("admin123"))
        )
        conn.commit()
    cursor.close()


def load_config():
    """
    Build the credentials dict that streamlit_authenticator expects,
    sourced from the MySQL database instead of a yaml file.
    """
    conn = _get_connection()
    _migrate_from_yaml_if_needed(conn)
    _ensure_default_admin(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT username, name, email, password FROM users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    usernames = {
        username: {"name": name, "email": email, "password": password}
        for username, name, email, password in rows
    }

    return {
        "credentials": {"usernames": usernames},
        "cookie": COOKIE_CONFIG,
    }


def create_authenticator(config):
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"]
    )
    return authenticator


def register_user(config, name, username, email, password):
    """
    Add a new user directly to the MySQL database.
    Returns (success: bool, message: str)
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False, "Username already exists!"

    cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False, "Email already registered!"

    hashed_password = stauth.Hasher.hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, name, email, password) VALUES (%s, %s, %s, %s)",
            (username, name, email, hashed_password)
        )
        conn.commit()
        return True, "Account created successfully!"
    except mysql.connector.Error as err:
        return False, f"Database error: {err}"
    finally:
        cursor.close()
        conn.close()