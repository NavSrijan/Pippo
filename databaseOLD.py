import datetime
import os
from collections import Counter, OrderedDict

import discord
import psycopg2
import psycopg2.extras

from functions import load, utc_to_ist

creds = {'username': os.environ['database_username'], 'password': os.environ['database_password']}

def _is_connected(func):

    def wrapper(self, *args, **kwargs):
        if self.cursor.closed is True:
            # print("Connecting.")
            self.connect()
        else:
            # print("Already connected.")
            pass
        result = func(self, *args, **kwargs)
        self.conn.commit()
        return result

    return wrapper

class Database():
    database_name = "pippobot_db"

    def __init__(self, tableName):
        self.username = creds['username']
        self.password = creds['password']
        self.tableName = tableName
        self.connect()

    def connect(self):
        self.conn = psycopg2.connect(host=os.environ['db_host'],
                                     database=self.database_name,
                                     user=self.username,
                                     password=self.password)
        self.cursor = self.conn.cursor(
            cursor_factory=psycopg2.extras.DictCursor)
        return self.cursor

    def closeConnection(self):
        self.conn.commit()
        self.conn.close()

    @_is_connected
    def view_all(self):
        query = f"select * from {self.tableName};"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return result

    @_is_connected
    def view_query(self, query, values=()):
        self.cursor.execute(query, values)
        result = self.cursor.fetchall()
        return result

    @_is_connected
    def view_where(self, where: tuple):
        query = f"select * from {self.tableName} where {where[0]}=%s;"
        self.cursor.execute(query, (where[1], ))
        result = self.cursor.fetchall()
        return result

class Servers(Database):
    """
    CREATE TABLE "servers" (
	"server_id" BIGINT NOT NULL,
	"prefix" TEXT,
	PRIMARY KEY ("server_id")
    );
    """

    def __init__(self):
        tableName = "servers"
        super().__init__(tableName)

    @_is_connected
    def prefix_add(self, server_id, prefix):
        """Add a server's prefix to database"""
        sql = """UPDATE {}
        SET prefix= %s
        WHERE server_id=%s;
        """.format(self.tableName)

        self.cursor.execute(sql, (prefix, server_id))

        if self.cursor.statusmessage == "UPDATE 1":
            pass
        else:
            self.insert_new_entry(server_id, prefix)

    @_is_connected
    def fetch_prefix(self, server_id):
        """Fetch a server's prefix from database"""
        sql = "SELECT prefix FROM {} WHERE server_id=%s;".format(self.tableName)
        res = self.view_query(sql, values=(server_id, ))
        if len(res) != 0:
            return res[0]
        else:
            return "."

    @_is_connected
    def insert_new_entry(self, server_id, prefix):
        sql = """INSERT INTO {} (server_id, prefix) VALUES (%s, %s);""".format(self.tableName)
        self.cursor.execute(sql, (server_id, prefix))

class Greetings(Database):
    """
CREATE TABLE "greetings" (
	"user_id" BIGINT NOT NULL,
	"gm" BOOLEAN NOT NULL,
	"ga" BOOLEAN NOT NULL,
	"ge" BOOLEAN NOT NULL,
	"gn" BOOLEAN NOT NULL,
	PRIMARY KEY ("user_id")
);
    """
    def __init__(self):
        tableName = "greetings"
        super().__init__(tableName)

    @_is_connected
    def insert(self, user_id, gm=False, ga=False, ge=False, gn=False):
        query = f"INSERT INTO {self.tableName} (user_id, gm, ga, ge, gn) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET gm=%s, ga=%s, ge=%s, gn=%s;"
        self.cursor.execute(query, (user_id, gm, ga, ge, gn, gm, ga, ge, gn))

    @_is_connected
    def get_users(self, cmd):
        query = f"SELECT * FROM {self.tableName} WHERE {cmd}=true;"
        res = self.view_query(query)
        return res

class Analytics(Database):
    """CREATE TABLE analytics (
   id SERIAL PRIMARY KEY,
   command TEXT NOT NULL,
   server_id BIGINT NOT NULL,
   user_id BIGINT NOT NULL,
   time_of_command TIMESTAMP NOT NULL
);"""
    def __init__(self):
        tableName = "analytics"
        super().__init__(tableName)

    @_is_connected
    async def insert_command(self, command, server_id, user_id):
        sql = """INSERT INTO {} (command, server_id, user_id, time_of_command) VALUES (%s, %s, %s, %s);""".format(self.tableName)
        self.cursor.execute(sql, (command, server_id, user_id, datetime.datetime.now()))

class BollywoodHangmanDB(Database):
    """CREATE TABLE "bollywood_points" (
        "user_id" BIGINT NOT NULL,
        "points" INT,
        "rounds" INT,
        PRIMARY KEY ("user_id")
    );"""

    def __init__(self):
        tableName = "bollywood_points"
        super().__init__(tableName)

    @_is_connected
    def insert_new_entry(self, user_id, points, rounds):
        sql = """INSERT INTO {} (user_id, points, rounds) VALUES (%s, %s, %s);""".format(
            self.tableName)
        self.cursor.execute(sql, (user_id, points, rounds))

    @_is_connected
    def update_score(self, user_id, points, rounds):
        sql = """UPDATE {}
        SET points = points+ %s,
        rounds = rounds + %s
        WHERE user_id=%s;
        """.format(self.tableName)

        self.cursor.execute(sql, (points, rounds, user_id))

        if self.cursor.statusmessage == "UPDATE 1":
            pass
        else:
            self.insert_new_entry(user_id, points, rounds)

class PlotsterDB(Database):
    """CREATE TABLE "plotster_points" (
        "user_id" BIGINT NOT NULL,
        "points" INT,
        "rounds" INT,
        PRIMARY KEY ("user_id")
    );"""

    def __init__(self):
        tableName = "plotster_points"
        super().__init__(tableName)

    @_is_connected
    def insert_new_entry(self, user_id, points, rounds):
        sql = """INSERT INTO {} (user_id, points, rounds) VALUES (%s, %s, %s);""".format(
            self.tableName)
        self.cursor.execute(sql, (user_id, points, rounds))

    @_is_connected
    def update_score(self, user_id, points, rounds):
        sql = """UPDATE {}
        SET points = points+ %s,
        rounds = rounds + %s
        WHERE user_id=%s;
        """.format(self.tableName)

        self.cursor.execute(sql, (points, rounds, user_id))

        if self.cursor.statusmessage == "UPDATE 1":
            pass
        else:
            self.insert_new_entry(user_id, points, rounds)
